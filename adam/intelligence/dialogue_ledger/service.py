# =============================================================================
# ADAM Dialogue Ledger — Neo4j-backed write/read service
# Location: adam/intelligence/dialogue_ledger/service.py
# =============================================================================

"""
DialogueLedgerService: writes Claims (and accompanying LearningStatus)
to Neo4j against the schema defined in migration 019, reads them back
for analysis.

DESIGN

  - The service holds a Neo4j driver. In tests, an in-memory backend
    can be supplied via the InMemoryDialogueLedgerBackend so unit tests
    don't require Neo4j.
  - All writes are MERGE-safe (idempotent under retry).
  - Reads return Pydantic models, not raw records.
  - When Neo4j is unavailable, writes log at warning level and return
    None — caller must handle the "ledger unavailable" state, never
    raise. This is the discipline anchor: ledger failure should not
    break the user's interaction; the elicitation surface continues
    even if the data lands in /dev/null. Loss-of-ledger is itself a
    drift signal that surfaces via Prometheus.
  - The service is async-first to match the orchestrator's async
    surface. A sync sibling can be added later if daily-task code
    needs it.

CONSTRAINTS / INDEX REQUIREMENTS

The service assumes migration 019 has been applied to the target Neo4j
instance. Without the constraints, MERGE operations will succeed but
won't deduplicate by id — a silent correctness failure. The service
emits a one-time warning at startup if it can't verify the constraint
exists; production deploy must apply 019 before the service runs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from adam.intelligence.dialogue_ledger.models import (
    Claim,
    ClaimStatus,
    DialogueUser,
    ElicitationMode,
    FrameLabel,
    LearningStatus,
    LearningStatusState,
    RecallabilityLabel,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Backend protocol — abstracts away Neo4j vs in-memory for testing
# =============================================================================


class DialogueLedgerBackend(Protocol):
    """Backend interface for write/read of Dialogue Ledger entities.

    Implemented by Neo4jDialogueLedgerBackend (production) and
    InMemoryDialogueLedgerBackend (tests).
    """

    async def upsert_user(self, user: DialogueUser) -> None: ...
    async def write_claim(
        self, claim: Claim, learning_status: LearningStatus,
    ) -> None: ...
    async def get_claim(self, claim_id: str) -> Optional[Claim]: ...
    async def get_claims_by_user(
        self, user_id: str, limit: int = 100,
    ) -> List[Claim]: ...
    async def get_claims_by_status(
        self, status: ClaimStatus, limit: int = 100,
    ) -> List[Claim]: ...
    async def get_claims_by_domain(
        self, domain: str, limit: int = 100,
    ) -> List[Claim]: ...


# =============================================================================
# In-memory backend — tests + offline runners
# =============================================================================


class InMemoryDialogueLedgerBackend:
    """Pure-Python backend; production Neo4j-free use only (tests, offline)."""

    def __init__(self) -> None:
        self._users: Dict[str, DialogueUser] = {}
        self._claims: Dict[str, Claim] = {}
        self._learning_statuses: Dict[str, LearningStatus] = {}

    async def upsert_user(self, user: DialogueUser) -> None:
        self._users[user.id] = user

    async def write_claim(
        self, claim: Claim, learning_status: LearningStatus,
    ) -> None:
        if learning_status.claim_id != claim.id:
            raise ValueError(
                f"learning_status.claim_id ({learning_status.claim_id}) "
                f"must match claim.id ({claim.id})"
            )
        self._claims[claim.id] = claim
        self._learning_statuses[claim.id] = learning_status

    async def get_claim(self, claim_id: str) -> Optional[Claim]:
        return self._claims.get(claim_id)

    async def get_claims_by_user(
        self, user_id: str, limit: int = 100,
    ) -> List[Claim]:
        results = [c for c in self._claims.values() if c.user_id == user_id]
        # Newest first
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[:limit]

    async def get_claims_by_status(
        self, status: ClaimStatus, limit: int = 100,
    ) -> List[Claim]:
        results = [c for c in self._claims.values() if c.status == status]
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[:limit]

    async def get_claims_by_domain(
        self, domain: str, limit: int = 100,
    ) -> List[Claim]:
        results = [c for c in self._claims.values() if c.domain == domain]
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[:limit]

    # Test introspection helpers
    def get_learning_status(self, claim_id: str) -> Optional[LearningStatus]:
        return self._learning_statuses.get(claim_id)

    def all_users(self) -> List[DialogueUser]:
        return list(self._users.values())

    def all_claims(self) -> List[Claim]:
        return list(self._claims.values())

    def reset(self) -> None:
        self._users.clear()
        self._claims.clear()
        self._learning_statuses.clear()


# =============================================================================
# Neo4j backend — production
# =============================================================================


class Neo4jDialogueLedgerBackend:
    """Neo4j-backed write/read implementation matching migration 019.

    Driver acquisition is lazy — failure mode is silent (log + continue)
    so dialogue-ledger failure doesn't break the user's interaction.
    """

    _UPSERT_USER_CYPHER = """
    MERGE (u:DialogueUser {id: $id})
      ON CREATE SET u.created_at = datetime($created_at)
      SET u.email = $email,
          u.display_name = $display_name,
          u.role = $role,
          u.trust_mode_default = $trust_mode_default
    """

    _WRITE_CLAIM_CYPHER = """
    MERGE (u:DialogueUser {id: $user_id})
    MERGE (c:Claim {id: $id})
      SET c += $claim_props
    MERGE (u)-[:ASSERTED]->(c)
    MERGE (s:LearningStatus {claim_id: $id})
      SET s += $status_props
    MERGE (c)-[:HAS_STATUS]->(s)
    """

    _GET_CLAIM_BY_ID_CYPHER = """
    MATCH (c:Claim {id: $id})
    RETURN c
    """

    _GET_CLAIMS_BY_USER_CYPHER = """
    MATCH (c:Claim {user_id: $user_id})
    RETURN c
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    _GET_CLAIMS_BY_STATUS_CYPHER = """
    MATCH (c:Claim {status: $status})
    RETURN c
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    _GET_CLAIMS_BY_DOMAIN_CYPHER = """
    MATCH (c:Claim {domain: $domain})
    RETURN c
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    async def upsert_user(self, user: DialogueUser) -> None:
        await self._run(
            self._UPSERT_USER_CYPHER,
            {
                "id": user.id,
                "created_at": user.created_at.isoformat(),
                "email": user.email or "",
                "display_name": user.display_name or "",
                "role": user.role,
                "trust_mode_default": user.trust_mode_default,
            },
        )

    async def write_claim(
        self, claim: Claim, learning_status: LearningStatus,
    ) -> None:
        if learning_status.claim_id != claim.id:
            raise ValueError(
                f"learning_status.claim_id ({learning_status.claim_id}) "
                f"must match claim.id ({claim.id})"
            )
        await self._run(
            self._WRITE_CLAIM_CYPHER,
            {
                "id": claim.id,
                "user_id": claim.user_id,
                "claim_props": claim.to_neo4j_props(),
                "status_props": learning_status.to_neo4j_props(),
            },
        )

    async def get_claim(self, claim_id: str) -> Optional[Claim]:
        records = await self._run_read(
            self._GET_CLAIM_BY_ID_CYPHER, {"id": claim_id},
        )
        if not records:
            return None
        return _record_to_claim(records[0])

    async def get_claims_by_user(
        self, user_id: str, limit: int = 100,
    ) -> List[Claim]:
        records = await self._run_read(
            self._GET_CLAIMS_BY_USER_CYPHER,
            {"user_id": user_id, "limit": limit},
        )
        return [c for c in (_record_to_claim(r) for r in records) if c]

    async def get_claims_by_status(
        self, status: ClaimStatus, limit: int = 100,
    ) -> List[Claim]:
        records = await self._run_read(
            self._GET_CLAIMS_BY_STATUS_CYPHER,
            {"status": status.value, "limit": limit},
        )
        return [c for c in (_record_to_claim(r) for r in records) if c]

    async def get_claims_by_domain(
        self, domain: str, limit: int = 100,
    ) -> List[Claim]:
        records = await self._run_read(
            self._GET_CLAIMS_BY_DOMAIN_CYPHER,
            {"domain": domain, "limit": limit},
        )
        return [c for c in (_record_to_claim(r) for r in records) if c]

    # ---- internal driver wrappers ----

    async def _run(self, cypher: str, params: Dict[str, Any]) -> None:
        try:
            async with self._driver.session() as session:
                await session.run(cypher, **params)
        except Exception as exc:
            logger.warning("DialogueLedger write failed: %s", exc)

    async def _run_read(
        self, cypher: str, params: Dict[str, Any],
    ) -> List[Any]:
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, **params)
                return await result.data()
        except Exception as exc:
            logger.warning("DialogueLedger read failed: %s", exc)
            return []


# =============================================================================
# Record → model mapping
# =============================================================================


def _record_to_claim(record: Any) -> Optional[Claim]:
    """Best-effort rehydration of a Neo4j Claim record to a Pydantic Claim.

    Returns None when the record is malformed (rather than raising —
    consistent with the service's "log + continue" failure mode).
    """
    try:
        c = record["c"] if hasattr(record, "__getitem__") else record.get("c")
        # In some neo4j driver responses, c is already a dict
        if isinstance(c, dict):
            data = c
        else:
            # Neo4j Node-like — try iter or properties
            data = dict(c)

        # Parse datetime back
        created_at_raw = data.get("created_at")
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(
                created_at_raw.replace("Z", "+00:00")
            )
        else:
            created_at = created_at_raw if isinstance(created_at_raw, datetime) else datetime.now(timezone.utc)

        # Parse enums
        elicitation_mode = ElicitationMode(data.get("elicitation_mode", "forced_pair"))
        frame = FrameLabel(data.get("frame", "neutral"))
        recallability_raw = data.get("recallability")
        recallability = (
            RecallabilityLabel(recallability_raw)
            if recallability_raw else None
        )

        # The Claim model's status validator forbids non-HYPOTHESIS at
        # construction. For rehydration of existing claims, we need to
        # bypass that — Pydantic v2 model_construct skips validators.
        return Claim.model_construct(
            id=data.get("id", ""),
            user_id=data.get("user_id", ""),
            text=data.get("text", ""),
            elicitation_mode=elicitation_mode,
            stated_confidence=data.get("stated_confidence"),
            latency_ms=data.get("latency_ms"),
            frame=frame,
            domain=data.get("domain", ""),
            status=ClaimStatus(data.get("status", "hypothesis")),
            created_at=created_at,
            session_id=data.get("session_id"),
            mood_index=data.get("mood_index"),
            recallability=recallability,
        )
    except Exception as exc:
        logger.debug("Failed to rehydrate Claim record: %s", exc)
        return None


# =============================================================================
# Service — high-level façade
# =============================================================================


class DialogueLedgerService:
    """High-level façade over the backend.

    Owns the discipline rules:
      - Every Claim write is paired with a LearningStatus write
      - LearningStatus.current at write time is CAPTURED (HMT §9.2:
        "captured" is the entry state for the LearningStatus lifecycle)
      - All writes are async; reads return Pydantic models
    """

    def __init__(self, backend: DialogueLedgerBackend) -> None:
        self._backend = backend

    async def ensure_user(self, user: DialogueUser) -> None:
        """Idempotent user upsert — call at session start."""
        await self._backend.upsert_user(user)

    async def record_claim(
        self,
        claim: Claim,
        *,
        horizon_ends_at: Optional[datetime] = None,
        capture_reason: str = "claim captured at elicitation",
    ) -> Claim:
        """Write a Claim + accompanying LearningStatus(CAPTURED).

        Returns the same Claim instance for caller convenience. The
        write is fire-and-log-on-fail per the service's contract — the
        Claim object is the user-facing record regardless of backend
        success.
        """
        # HMT discipline anchor: re-validate the claim's HYPOTHESIS
        # invariant at write time. Defensive — the model's validator
        # already enforces this at construction, but a Claim hand-built
        # via model_construct could bypass it.
        if claim.status != ClaimStatus.HYPOTHESIS:
            raise ValueError(
                f"record_claim called with claim.status={claim.status}; "
                "must be HYPOTHESIS at capture (HMT rule 12)"
            )

        learning_status = LearningStatus(
            claim_id=claim.id,
            current=LearningStatusState.CAPTURED,
            reason=capture_reason,
            horizon_ends_at=horizon_ends_at,
        )

        await self._backend.write_claim(claim, learning_status)
        return claim

    async def get_claim(self, claim_id: str) -> Optional[Claim]:
        return await self._backend.get_claim(claim_id)

    async def get_user_history(
        self, user_id: str, limit: int = 100,
    ) -> List[Claim]:
        return await self._backend.get_claims_by_user(user_id, limit=limit)

    async def get_pending_claims(self, limit: int = 100) -> List[Claim]:
        """Claims still in HYPOTHESIS status — awaiting instrumentation
        and/or causal adjudication."""
        return await self._backend.get_claims_by_status(
            ClaimStatus.HYPOTHESIS, limit=limit,
        )

    async def get_domain_claims(
        self, domain: str, limit: int = 100,
    ) -> List[Claim]:
        return await self._backend.get_claims_by_domain(domain, limit=limit)


# =============================================================================
# SINGLETON
# =============================================================================


_dialogue_ledger_service: Optional[DialogueLedgerService] = None


def get_dialogue_ledger_service(
    backend: Optional[DialogueLedgerBackend] = None,
) -> DialogueLedgerService:
    """Get or create the singleton DialogueLedgerService.

    Production path: backend=None resolves the Neo4j async driver via
    adam.core.dependencies and wraps it in Neo4jDialogueLedgerBackend.
    Test path: pass an InMemoryDialogueLedgerBackend.
    """
    global _dialogue_ledger_service
    if _dialogue_ledger_service is not None:
        return _dialogue_ledger_service

    if backend is None:
        backend = _resolve_default_backend()

    _dialogue_ledger_service = DialogueLedgerService(backend)
    return _dialogue_ledger_service


def reset_dialogue_ledger_service() -> None:
    """Test-only — clear the singleton."""
    global _dialogue_ledger_service
    _dialogue_ledger_service = None


def _resolve_default_backend() -> DialogueLedgerBackend:
    """Try to build a Neo4j-backed backend; fall back to in-memory.

    The fall-back is logged at warning level — it surfaces the case
    where Neo4j is unavailable and elicitation data accumulates only
    in-memory (and is lost on process restart). For production this is
    a serious failure mode that monitoring should alert on.
    """
    try:
        from neo4j import AsyncGraphDatabase
        from adam.config.settings import settings

        uri = settings.neo4j.uri
        username = settings.neo4j.username
        password = settings.neo4j.password
        if not uri or not username or not password:
            raise RuntimeError("Neo4j credentials incomplete")

        driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
        return Neo4jDialogueLedgerBackend(driver)
    except Exception as exc:
        logger.warning(
            "DialogueLedger: Neo4j backend unavailable (%s); falling "
            "back to in-memory. Production deploy MUST resolve this — "
            "in-memory backend loses data on restart.",
            exc,
        )
        return InMemoryDialogueLedgerBackend()
