"""Client recommendation decisions — persistence + lookup.

Persists the client's acknowledge / decline decisions on the
recommendations produced by the client report composer. Follows the
same node-type vocabulary as the internal /recommendations/{id}/decide
endpoint (Recommendation, UserDecision, Claim, Deviation) so Loop B's
causal-adjudication pipeline consumes both streams uniformly.

Strategic commitments:

  - Every acknowledgment is a learning event. When a client approves a
    recommendation, that's evidence we read the situation correctly and
    our rationale landed. When they decline, it's evidence we didn't —
    either the recommendation was wrong, or our rationale failed to
    communicate why, or there's external context the system lacks.
    Both outcomes feed the teaming loop (HMT Foundation §9.2).

  - Decline creates a Deviation. Same as the internal /decide path:
    a decline is a deviation from our preferred choice, so the causal
    adjudicator schedules an outcome observation at horizon expiry and
    eventually adjudicates user_right vs system_right.

  - Rationale (feedback on decline) is a Claim with status="hypothesis".
    Claims never auto-promote to learnings (Rule 12). The inferential
    adjudicator decides later whether the client's stated reason was
    right.

  - Snapshot-on-decide. The rec doesn't exist in the graph until the
    client acts — recs are composed per-report-render, not persisted
    speculatively. When the client decides, we snapshot the rec at that
    moment as the audit record.

  - Idempotent per (recommendation_id, user_id). If a client clicks
    Approve twice or re-submits, we return the prior decision without
    creating a duplicate.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.api.dashboard.models import (
    ClientDecisionAuditEntry,
    ClientDecisionAuditResponse,
    ClientDecisionAuditSummary,
    ClientRecommendationDecisionRequest,
    ClientRecommendationDecisionResponse,
)
from adam.infrastructure.neo4j.client import get_neo4j_client

logger = logging.getLogger(__name__)


# Expected time-to-signal for a client recommendation outcome. Spending
# / creative adjustments typically show a per-campaign CPA shift in
# days-to-weeks; pick "weeks" as the default horizon class. The causal
# adjudicator will not evaluate before this window elapses.
_DEFAULT_HORIZON_CLASS = "weeks"


@dataclass(frozen=True)
class ExistingDecision:
    """The decision we found already recorded for this (rec_id, user_id).
    Used by the report composer to render idempotent status."""
    decision_id: str
    kind: str  # "acknowledge" | "decline"
    created_at: datetime


# ---------------------------------------------------------------------------
# Cypher
# ---------------------------------------------------------------------------

# Idempotency check — has this user already decided on this rec?
_CYPHER_FIND_EXISTING = """
MATCH (d:UserDecision {
    user_id: $user_id,
    recommendation_id: $recommendation_id
})
RETURN d.id AS decision_id, d.kind AS kind, d.created_at AS created_at
ORDER BY d.created_at DESC
LIMIT 1
"""


# Snapshot the ClientRecommendation the moment the client acts.
# Uses the same `Recommendation` node type as the internal decide flow
# so Loop B's adjudicator doesn't need to special-case client recs;
# differentiated only by the `kind: "client"` property.
_CYPHER_SNAPSHOT_RECOMMENDATION = """
MERGE (r:Recommendation {id: $recommendation_id})
  ON CREATE SET
    r.kind = "client",
    r.user_id = $user_id,
    r.advertiser_id = $advertiser_id,
    r.title = $headline,
    r.summary = $rationale,
    r.preferred_choice = $confirm_label,
    r.projected_impact = $projected_impact,
    r.expected_horizon_class = $horizon_class,
    r.status = $rec_status,
    r.created_at = $created_at,
    r.alternatives_json = "[]",
    r.evidence_json = "{}"
  ON MATCH SET
    r.status = $rec_status,
    r.updated_at = $created_at
"""


_CYPHER_CREATE_FEEDBACK_CLAIM = """
MERGE (u:DialogueUser {id: $user_id})
CREATE (c:Claim {
    id: $claim_id,
    user_id: $user_id,
    text: $feedback_text,
    elicitation_mode: "freeform",
    domain: "client_recommendation_decline_rationale",
    stated_confidence: null,
    latency_ms: $latency_ms,
    frame: "neutral",
    status: "hypothesis",
    session_id: null,
    mood_index: null,
    recallability: null,
    created_at: $created_at
})
MERGE (u)-[:ASSERTED]->(c)
CREATE (ls:LearningStatus {
    claim_id: $claim_id,
    current: "captured",
    transitioned_at: $created_at,
    reason: "client decline rationale capture"
})
MERGE (c)-[:HAS_STATUS]->(ls)
"""


_CYPHER_CREATE_USER_DECISION = """
MERGE (u:DialogueUser {id: $user_id})
MATCH (r:Recommendation {id: $recommendation_id})
CREATE (d:UserDecision {
    id: $decision_id,
    user_id: $user_id,
    recommendation_id: $recommendation_id,
    kind: $kind,
    chosen_alternative: null,
    rationale_class: null,
    rationale_text: $feedback_text,
    claim_id: $claim_id,
    latency_ms: $latency_ms,
    created_at: $created_at
})
MERGE (u)-[:MADE]->(d)
MERGE (d)-[:ON]->(r)
"""


_CYPHER_CREATE_DEVIATION = """
MATCH (u:DialogueUser {id: $user_id})
MATCH (r:Recommendation {id: $recommendation_id})
CREATE (dev:Deviation {
    id: $deviation_id,
    user_id: $user_id,
    recommendation_id: $recommendation_id,
    system_choice: $system_choice,
    user_choice: "decline",
    stated_rationale: $feedback_text,
    rationale_class: null,
    adjudication_status: "pending",
    adjudication_outcome: null,
    horizon_class: $horizon_class,
    created_at: $created_at
})
MERGE (u)-[:DEVIATED]->(dev)
MERGE (dev)-[:FROM]->(r)
"""


# Audit query — every client-rec UserDecision across all users, joined
# to the Recommendation snapshot, and (where the decision was a decline)
# the Deviation and its Outcome. Powers the Front-end B client-decisions
# audit view so the operator can see what clients have been doing with
# recommendations without running Cypher by hand.
_CYPHER_DECISION_AUDIT = """
MATCH (u:DialogueUser)-[:MADE]->(d:UserDecision)-[:ON]->(r:Recommendation {kind: "client"})
OPTIONAL MATCH (u)-[:DEVIATED]->(dev:Deviation)-[:FROM]->(r)
OPTIONAL MATCH (dev)-[:RESOLVED_AS]->(o:Outcome)
RETURN d.id AS decision_id,
       d.kind AS decision_kind,
       d.created_at AS decided_at,
       d.latency_ms AS latency_ms,
       d.rationale_text AS feedback_text,
       r.id AS rec_id,
       coalesce(r.title, '(untitled)') AS rec_headline,
       r.advertiser_id AS advertiser_id,
       dev.id AS deviation_id,
       dev.adjudication_status AS adjudication_status,
       dev.adjudication_outcome AS adjudication_outcome,
       o.observation AS outcome_observation
ORDER BY d.created_at DESC
LIMIT $limit
"""


# Bulk lookup — given a list of recommendation_ids for this user,
# return each one's most recent decision (kind + timestamp). Used by
# the report composer to render statuses across the list in one query.
_CYPHER_BULK_DECISIONS = """
UNWIND $recommendation_ids AS rec_id
OPTIONAL MATCH (d:UserDecision {user_id: $user_id, recommendation_id: rec_id})
WITH rec_id, d
ORDER BY d.created_at DESC
WITH rec_id, collect(d)[0] AS latest
WHERE latest IS NOT NULL
RETURN rec_id AS recommendation_id,
       latest.id AS decision_id,
       latest.kind AS kind,
       latest.created_at AS created_at
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

async def find_existing_decision(
    user_id: str,
    recommendation_id: str,
) -> Optional[ExistingDecision]:
    """Return the most recent decision for (rec_id, user_id), or None."""
    client = get_neo4j_client()
    if not client.is_connected:
        connected = await client.connect()
        if not connected:
            return None
    async with await client.session() as session:
        result = await session.run(
            _CYPHER_FIND_EXISTING,
            user_id=user_id,
            recommendation_id=recommendation_id,
        )
        record = await result.single()
    if record is None or record.get("decision_id") is None:
        return None
    created_raw = record["created_at"]
    if hasattr(created_raw, "to_native"):
        created = created_raw.to_native()
    else:
        created = datetime.fromisoformat(str(created_raw))
    return ExistingDecision(
        decision_id=record["decision_id"],
        kind=record["kind"],
        created_at=created,
    )


async def bulk_decisions_for_user(
    user_id: str,
    recommendation_ids: List[str],
) -> Dict[str, ExistingDecision]:
    """Return {rec_id: ExistingDecision} for every rec the user already
    decided on. Missing ids = no decision yet."""
    if not recommendation_ids:
        return {}
    client = get_neo4j_client()
    if not client.is_connected:
        connected = await client.connect()
        if not connected:
            return {}
    out: Dict[str, ExistingDecision] = {}
    try:
        async with await client.session() as session:
            result = await session.run(
                _CYPHER_BULK_DECISIONS,
                user_id=user_id,
                recommendation_ids=recommendation_ids,
            )
            async for record in result:
                rec_id = record["recommendation_id"]
                created_raw = record["created_at"]
                if hasattr(created_raw, "to_native"):
                    created = created_raw.to_native()
                else:
                    created = datetime.fromisoformat(str(created_raw))
                out[rec_id] = ExistingDecision(
                    decision_id=record["decision_id"],
                    kind=record["kind"],
                    created_at=created,
                )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "bulk_decisions_for_user failed: %s", exc, exc_info=True,
        )
    return out


async def compose_client_decision_audit(
    limit: int = 100,
) -> ClientDecisionAuditResponse:
    """Fetch all client-recommendation decisions across all users,
    joined to their Deviation + Outcome where applicable, and package
    with summary counts.

    Internal-only. Drives the Front-end B client-decisions audit view.
    Returns an empty, zeroed response when Neo4j is unavailable rather
    than raising — the view renders an "unavailable" notice on its own.
    """
    summary = ClientDecisionAuditSummary(
        total_decisions=0,
        acknowledge_count=0,
        decline_count=0,
        declines_with_feedback=0,
        pending_adjudication=0,
        adjudicated_system_right=0,
        adjudicated_user_right=0,
        adjudicated_indeterminate=0,
        acceptance_rate=0.0,
    )
    entries: list[ClientDecisionAuditEntry] = []

    client = get_neo4j_client()
    if not client.is_connected:
        connected = await client.connect()
        if not connected:
            return ClientDecisionAuditResponse(summary=summary, entries=[])

    try:
        async with await client.session() as session:
            result = await session.run(_CYPHER_DECISION_AUDIT, limit=limit)
            async for record in result:
                decided_raw = record["decided_at"]
                if hasattr(decided_raw, "to_native"):
                    decided_at = decided_raw.to_native()
                else:
                    decided_at = datetime.fromisoformat(str(decided_raw))
                entry = ClientDecisionAuditEntry(
                    decision_id=record["decision_id"],
                    decision_kind=record["decision_kind"],
                    decided_at=decided_at,
                    latency_ms=record.get("latency_ms"),
                    feedback_text=record.get("feedback_text"),
                    rec_id=record["rec_id"],
                    rec_headline=record["rec_headline"],
                    advertiser_id=record.get("advertiser_id"),
                    deviation_id=record.get("deviation_id"),
                    adjudication_status=record.get("adjudication_status"),
                    adjudication_outcome=record.get("adjudication_outcome"),
                    outcome_observation=record.get("outcome_observation"),
                )
                entries.append(entry)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "compose_client_decision_audit failed: %s", exc, exc_info=True,
        )
        return ClientDecisionAuditResponse(summary=summary, entries=[])

    # Aggregate the summary from the entries we collected.
    summary.total_decisions = len(entries)
    for e in entries:
        if e.decision_kind == "acknowledge":
            summary.acknowledge_count += 1
        elif e.decision_kind == "decline":
            summary.decline_count += 1
            if e.feedback_text and e.feedback_text.strip():
                summary.declines_with_feedback += 1
            # Adjudication status tallies only meaningful for declines
            # (only declines produce Deviations).
            if e.adjudication_status == "pending":
                summary.pending_adjudication += 1
            elif e.adjudication_status == "adjudicated":
                outcome = e.adjudication_outcome or "indeterminate"
                if outcome == "system_right":
                    summary.adjudicated_system_right += 1
                elif outcome == "user_right":
                    summary.adjudicated_user_right += 1
                else:
                    summary.adjudicated_indeterminate += 1

    if summary.total_decisions > 0:
        summary.acceptance_rate = (
            summary.acknowledge_count / summary.total_decisions
        )

    return ClientDecisionAuditResponse(summary=summary, entries=entries)


async def record_client_decision(
    user_id: str,
    recommendation_id: str,
    request: ClientRecommendationDecisionRequest,
) -> ClientRecommendationDecisionResponse:
    """Persist a client's acknowledge / decline.

    Returns the existing decision if one was already recorded for this
    (rec_id, user_id) — idempotent so the client can re-click without
    creating duplicates.
    """
    existing = await find_existing_decision(user_id, recommendation_id)
    if existing is not None:
        logger.info(
            "Client decision already recorded: user=%s rec=%s kind=%s",
            user_id, recommendation_id, existing.kind,
        )
        return ClientRecommendationDecisionResponse(
            id=existing.decision_id,
            recommendation_id=recommendation_id,
            kind=existing.kind,  # type: ignore[arg-type]
            created_at=existing.created_at,
            claim_id=None,
            deviation_id=None,
        )

    created_at = datetime.now(timezone.utc)
    decision_id = f"client-decision:{uuid.uuid4()}"
    claim_id: Optional[str] = None
    deviation_id: Optional[str] = None
    rec_status = (
        "acknowledged" if request.kind == "acknowledge" else "declined"
    )

    client = get_neo4j_client()
    if not client.is_connected:
        connected = await client.connect()
        if not connected:
            # Fall back gracefully: return a not-persisted marker.
            logger.warning(
                "Neo4j unavailable for client decision persist",
            )
            return ClientRecommendationDecisionResponse(
                id=decision_id,
                recommendation_id=recommendation_id,
                kind=request.kind,
                created_at=created_at,
                claim_id=None,
                deviation_id=None,
            )

    # Capture whether a feedback claim + deviation will be created so the
    # ids are stable before entering the transaction (ids are emitted in
    # the response even if the downstream query chain aborts).
    will_create_claim = (
        request.kind == "decline"
        and bool((request.feedback_text or "").strip())
    )
    if will_create_claim:
        claim_id = f"claim:{uuid.uuid4()}"
    if request.kind == "decline":
        deviation_id = f"deviation:{uuid.uuid4()}"

    # Atomic transaction wrap (Structural Weakness #2, 2026-04-23 review —
    # closes the non-atomic-write risk). All four node/relationship
    # writes now commit or abort together; a failure mid-chain cannot
    # leave an orphan Recommendation, UserDecision, Claim, or Deviation.
    async def _decision_tx(tx) -> None:
        # 1) Snapshot the Recommendation at decision time.
        await tx.run(
            _CYPHER_SNAPSHOT_RECOMMENDATION,
            recommendation_id=recommendation_id,
            user_id=user_id,
            advertiser_id=request.advertiser_id,
            headline=request.headline,
            rationale=request.rationale,
            confirm_label=request.confirm_label,
            projected_impact=request.projected_impact,
            horizon_class=_DEFAULT_HORIZON_CLASS,
            rec_status=rec_status,
            created_at=created_at,
        )

        # 2) Feedback claim (decline + feedback_text only).
        if will_create_claim:
            await tx.run(
                _CYPHER_CREATE_FEEDBACK_CLAIM,
                user_id=user_id,
                claim_id=claim_id,
                feedback_text=request.feedback_text,
                latency_ms=request.latency_ms,
                created_at=created_at,
            )

        # 3) UserDecision — canonical record.
        await tx.run(
            _CYPHER_CREATE_USER_DECISION,
            user_id=user_id,
            recommendation_id=recommendation_id,
            decision_id=decision_id,
            kind=request.kind,
            feedback_text=request.feedback_text,
            claim_id=claim_id,
            latency_ms=request.latency_ms,
            created_at=created_at,
        )

        # 4) Deviation (decline path) — enters the causal adjudicator.
        if request.kind == "decline":
            await tx.run(
                _CYPHER_CREATE_DEVIATION,
                user_id=user_id,
                recommendation_id=recommendation_id,
                deviation_id=deviation_id,
                system_choice=request.confirm_label,
                feedback_text=request.feedback_text,
                horizon_class=_DEFAULT_HORIZON_CLASS,
                created_at=created_at,
            )

    async with await client.session() as session:
        await session.execute_write(_decision_tx)

    logger.info(
        "Client decision recorded: user=%s rec=%s kind=%s claim=%s deviation=%s",
        user_id, recommendation_id, request.kind, claim_id, deviation_id,
    )

    return ClientRecommendationDecisionResponse(
        id=decision_id,
        recommendation_id=recommendation_id,
        kind=request.kind,
        created_at=created_at,
        claim_id=claim_id,
        deviation_id=deviation_id,
    )
