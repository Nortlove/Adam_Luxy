"""RecommendationClassGraph — Neo4j service for RecommendationClass + claims.

Promotes the RecommendationClass primitive from Python-only data model to
durable Neo4j entity. Mirrors the shadow-write pattern established by
`adam.intelligence.pages.entity_graph.PageEntityGraph`: persistent
background loop, sync and async entry points, fire-and-forget semantics,
swallowed exceptions with observable log callbacks.

Schema: `adam/infrastructure/neo4j/migrations/027_recommendation_class.cypher`

Design commitments (Orientation discipline):

- Class identity is structured (5-tuple), not a string blob. `id` is
  deterministic from the identity, so the same cell always resolves to
  the same node.
- Claim recording is idempotent on `content_hash` — the SHA-256 receipt
  from ProjectedImpact's substantive content. Re-registering the same
  claim is a no-op on the graph.
- The MAKES_CLAIM relationship carries `recorded_at` so the graph-write
  time is captured even when it differs from ProjectedImpact.created_at
  (claim authored at T, committed to graph at T + ε).
- No synthesis or composition in this layer — the graph records
  structured shapes and returns them. Plant-model track-record math
  lands in the weeks 5-7 slice.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from adam.infrastructure.neo4j.client import Neo4jClient, get_neo4j_client
from adam.intelligence.recommendation_class.projected_impact import (
    ProjectedImpact,
    canonical_hash,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SYNC → ASYNC BRIDGE — persistent background loop for fire-and-forget writes
# =============================================================================
# Mirrors the pattern in adam/intelligence/pages/entity_graph.py. A single
# long-lived background loop so the Neo4j AsyncDriver's pool (bound to the
# loop that created it) stays valid across calls.

_bg_loop: Optional[asyncio.AbstractEventLoop] = None
_bg_thread: Optional[threading.Thread] = None
_bg_lock = threading.Lock()


def _get_bg_loop() -> asyncio.AbstractEventLoop:
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            _bg_loop = asyncio.new_event_loop()

            def _run():
                asyncio.set_event_loop(_bg_loop)
                _bg_loop.run_forever()

            _bg_thread = threading.Thread(
                target=_run, daemon=True,
                name="RecommendationClassGraph-bg-loop",
            )
            _bg_thread.start()
    return _bg_loop


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine on the background loop without awaiting its
    result. Exceptions are logged via an attached callback so silent
    shadow-write failures are still observable."""
    loop = _get_bg_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)

    def _on_done(fut):
        exc = fut.exception()
        if exc is not None:
            logger.warning(
                "RecommendationClassGraph write failed: %s", exc, exc_info=exc,
            )

    future.add_done_callback(_on_done)


# =============================================================================
# IDENTITY — deterministic id generation from the 5-tuple
# =============================================================================

_REC_CLASS_ID_PREFIX = "rec_class:"
_CLAIM_ID_PREFIX = "claim:"


@dataclass(frozen=True)
class RecommendationClassIdentity:
    """Cell identity in class-space.

    The tuple (advertiser_id, archetype_id, mechanism, context_posture_band,
    horizon_band) uniquely identifies a RecommendationClass. The `id`
    property is deterministic — same inputs → same id — so upserts
    converge idempotently on the same node.
    """
    advertiser_id: str
    archetype_id: str
    mechanism: str
    context_posture_band: str
    horizon_band: str

    def validate(self) -> None:
        for field_name in (
            "advertiser_id", "archetype_id", "mechanism",
            "context_posture_band", "horizon_band",
        ):
            value = getattr(self, field_name)
            if not value or not isinstance(value, str):
                raise ValueError(
                    f"RecommendationClassIdentity.{field_name} must be a non-empty string"
                )

    @property
    def id(self) -> str:
        """Deterministic id derived from the canonical identity slug."""
        return recommendation_class_id(self)

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def recommendation_class_id(identity: RecommendationClassIdentity) -> str:
    """Produce the canonical RecommendationClass.id from the identity tuple.

    Format: "rec_class:{first 16 hex of SHA-256 over canonical slug}".
    Canonical slug joins the 5 components with "|" to avoid collisions
    from component values that contain ":" or "/".
    """
    slug = "|".join([
        identity.advertiser_id,
        identity.archetype_id,
        identity.mechanism,
        identity.context_posture_band,
        identity.horizon_band,
    ])
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16]
    return f"{_REC_CLASS_ID_PREFIX}{digest}"


def claim_node_id(claim_id: str, content_hash: str) -> str:
    """Produce the canonical ProjectedImpactClaim node id.

    Format: "claim:{claim_id}:{content_hash-prefix}". Retains the human-
    readable claim_id for graph-browser reading while content_hash prefix
    ensures uniqueness across claim_id collisions.
    """
    if not claim_id:
        raise ValueError("claim_id is required for claim_node_id")
    if not content_hash or len(content_hash) < 16:
        raise ValueError("content_hash must be at least 16 hex chars")
    return f"{_CLAIM_ID_PREFIX}{claim_id}:{content_hash[:16]}"


# =============================================================================
# CYPHER
# =============================================================================

_CYPHER_UPSERT_RECOMMENDATION_CLASS = """
MERGE (rc:RecommendationClass {id: $id})
  ON CREATE SET
    rc.advertiser_id = $advertiser_id,
    rc.archetype_id = $archetype_id,
    rc.mechanism = $mechanism,
    rc.context_posture_band = $context_posture_band,
    rc.horizon_band = $horizon_band,
    rc.observation_count = 0,
    rc.first_seen = datetime()
SET
    rc.last_seen = datetime(),
    rc.last_updated = datetime(),
    rc.observation_count = rc.observation_count + 1
RETURN rc.id AS id, rc.observation_count AS observation_count
"""


# Recording a claim is idempotent on content_hash — MERGE on (id, content_hash)
# returns the existing node if this claim has been registered before. This
# protects against double-recording the same pre-registered predicate.
_CYPHER_RECORD_CLAIM = """
MERGE (pc:ProjectedImpactClaim {id: $id})
  ON CREATE SET
    pc.claim_id = $claim_id,
    pc.recommendation_class_id = $recommendation_class_id,
    pc.content_hash = $content_hash,
    pc.substantive_content_json = $substantive_content_json,
    pc.horizon_days = $horizon_days,
    pc.created_at = CASE WHEN $created_at IS NULL THEN datetime()
                         ELSE datetime($created_at) END,
    pc.adjudicated = false,
    pc.first_seen = datetime()
SET
    pc.last_seen = datetime()
WITH pc
MATCH (rc:RecommendationClass {id: $recommendation_class_id})
MERGE (rc)-[r:MAKES_CLAIM]->(pc)
  ON CREATE SET r.recorded_at = datetime()
RETURN pc.id AS id, pc.content_hash AS content_hash
"""


_CYPHER_LOOKUP_CLASS = """
MATCH (rc:RecommendationClass {id: $id})
RETURN rc.id AS id,
       rc.advertiser_id AS advertiser_id,
       rc.archetype_id AS archetype_id,
       rc.mechanism AS mechanism,
       rc.context_posture_band AS context_posture_band,
       rc.horizon_band AS horizon_band,
       rc.observation_count AS observation_count,
       rc.first_seen AS first_seen,
       rc.last_seen AS last_seen
"""


# =============================================================================
# SERVICE
# =============================================================================


class RecommendationClassGraph:
    """Neo4j service for upserting RecommendationClass nodes and recording
    ProjectedImpactClaim nodes linked by MAKES_CLAIM relationships.

    Sync entry points (`*_sync`) are fire-and-forget — schedule on the
    background loop and return immediately. Async entry points block until
    the Neo4j write completes and return the resulting id.

    All methods swallow Neo4j errors and log them (shadow-write safety).
    Callers that need error propagation should use the async entries and
    check for None / empty return values.
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        self._client = client or get_neo4j_client()

    # ── UPSERT CLASS ─────────────────────────────────────────────────────

    def upsert_class_sync(self, identity: RecommendationClassIdentity) -> None:
        """Fire-and-forget class upsert from synchronous code."""
        _fire_and_forget(self.upsert_class(identity))

    async def upsert_class(
        self, identity: RecommendationClassIdentity,
    ) -> Optional[str]:
        """Upsert a RecommendationClass node. Returns the node id on success,
        None on failure (errors logged).

        Idempotent — safe to call multiple times. Each call increments
        observation_count. Schema in migration 027."""
        try:
            identity.validate()
        except ValueError as exc:
            logger.warning("RecommendationClassIdentity validation failed: %s", exc)
            return None

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_UPSERT_RECOMMENDATION_CLASS,
                    id=identity.id,
                    advertiser_id=identity.advertiser_id,
                    archetype_id=identity.archetype_id,
                    mechanism=identity.mechanism,
                    context_posture_band=identity.context_posture_band,
                    horizon_band=identity.horizon_band,
                )
                record = await result.single()
                return record["id"] if record else None
        except Exception as exc:  # noqa: BLE001 — shadow-write must not raise
            logger.warning(
                "RecommendationClass upsert failed for %s: %s",
                identity.id, exc, exc_info=True,
            )
            return None

    # ── RECORD CLAIM ─────────────────────────────────────────────────────

    def record_claim_sync(self, claim: ProjectedImpact) -> None:
        """Fire-and-forget claim recording from synchronous code."""
        _fire_and_forget(self.record_claim(claim))

    async def record_claim(self, claim: ProjectedImpact) -> Optional[str]:
        """Record a pre-registered ProjectedImpact claim. Returns the claim
        node id on success, None on failure.

        The claim's recommendation_class_id must reference an already-upserted
        RecommendationClass. Caller is responsible for upsert sequencing —
        use record_class_and_claim for atomic combined flow.

        Idempotent on content_hash — re-recording the same claim resolves
        to the existing node without duplication."""
        try:
            claim.validate()
        except ValueError as exc:
            logger.warning("ProjectedImpact validation failed: %s", exc)
            return None

        content_hash = claim.content_hash or claim.compute_content_hash()
        node_id = claim_node_id(claim.claim_id, content_hash)

        substantive_json = json.dumps(
            claim.substantive_content(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_RECORD_CLAIM,
                    id=node_id,
                    claim_id=claim.claim_id,
                    recommendation_class_id=claim.recommendation_class_id,
                    content_hash=content_hash,
                    substantive_content_json=substantive_json,
                    horizon_days=claim.horizon_days,
                    created_at=claim.created_at,
                )
                record = await result.single()
                return record["id"] if record else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ProjectedImpactClaim record failed for %s: %s",
                claim.claim_id, exc, exc_info=True,
            )
            return None

    # ── COMBINED UPSERT + RECORD ─────────────────────────────────────────

    async def record_class_and_claim(
        self,
        identity: RecommendationClassIdentity,
        claim: ProjectedImpact,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Upsert the class then record the claim, in order. Returns
        (class_id, claim_id) tuple; either or both may be None on failure."""
        if identity.id != claim.recommendation_class_id:
            logger.warning(
                "record_class_and_claim: identity.id (%s) does not match "
                "claim.recommendation_class_id (%s); refusing to write",
                identity.id, claim.recommendation_class_id,
            )
            return None, None

        class_id = await self.upsert_class(identity)
        if class_id is None:
            return None, None

        claim_id = await self.record_claim(claim)
        return class_id, claim_id

    def record_class_and_claim_sync(
        self,
        identity: RecommendationClassIdentity,
        claim: ProjectedImpact,
    ) -> None:
        """Fire-and-forget variant."""
        _fire_and_forget(self.record_class_and_claim(identity, claim))

    # ── LOOKUP ───────────────────────────────────────────────────────────

    async def lookup_class(
        self, identity: RecommendationClassIdentity,
    ) -> Optional[Dict[str, Any]]:
        """Look up a RecommendationClass node by identity. Returns None if
        the node does not exist or Neo4j is unavailable."""
        try:
            identity.validate()
        except ValueError as exc:
            logger.warning("RecommendationClassIdentity validation failed: %s", exc)
            return None

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(_CYPHER_LOOKUP_CLASS, id=identity.id)
                record = await result.single()
                return dict(record) if record else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "RecommendationClass lookup failed for %s: %s",
                identity.id, exc, exc_info=True,
            )
            return None

    # ── INTERNAL ─────────────────────────────────────────────────────────

    async def _ensure_connected(self) -> bool:
        """Ensure the Neo4j client is connected. Returns False on failure."""
        if self._client.is_connected:
            return True
        connected = await self._client.connect()
        if not connected:
            logger.debug(
                "RecommendationClassGraph write skipped: Neo4j unavailable"
            )
        return connected


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_service: Optional[RecommendationClassGraph] = None


def get_recommendation_class_graph() -> RecommendationClassGraph:
    """Module-level accessor for the singleton RecommendationClassGraph."""
    global _service
    if _service is None:
        _service = RecommendationClassGraph()
    return _service
