# =============================================================================
# Spine #6 — DecisionTrace Neo4j long-term archival
# Location: adam/intelligence/decision_trace_neo4j.py
# =============================================================================
"""Neo4j long-term archival for ``DecisionTrace`` records.

Closes the Neo4j half of directive Spine #6 line 248:

    "Long-term archival in Neo4j as DecisionTrace nodes linked to the
     User, the ConversionEdge (when the impression resolves), and the
     Mechanism. Cypher queries for 'show me all decisions for this user
     this week, with do-calculus chain' are first-class."

Sibling to ``adam/intelligence/decision_trace_store.py`` (Redis hot
cache, shipped d9b4d7c). Together they implement the directive's
two-tier storage: Redis serves the demo-loop window with low latency;
Neo4j carries the long-term audit trail and supports cypher analytics
beyond the Redis TTL window.

NODE / EDGE SCHEMA
------------------

    (:DecisionTrace {
        decision_id:        str (UNIQUE, MERGE key),
        user_id:            str,
        chosen_creative_id: str,
        chosen_mechanism:   str,
        chosen_score:       float,
        timestamp:          float (epoch seconds),
        archived_at_ts:     float (epoch seconds),
        payload_json:       str (full Pydantic-serialized trace),
        schema_version:     str,
    })

    (:User {id: str}) -[:MADE_DECISION]-> (:DecisionTrace)
    (:DecisionTrace) -[:USED_MECHANISM]-> (:Mechanism {name: str})

The full payload is stored in ``payload_json`` (Pydantic-serialized).
Scalar fields are duplicated as node properties so cypher can filter
/ sort / aggregate without parsing JSON per row. The duplication is
maintained at archive time; ``payload_json`` remains the source of
truth on read (load_trace_from_neo4j re-parses it via
``DecisionTrace.model_validate_json``).

Idempotency: ``MERGE`` on ``decision_id`` so re-archiving (e.g., the
Redis-to-Neo4j drain task running twice) doesn't duplicate nodes.
``SET`` overwrites scalar properties + payload — last writer wins.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: directive Spine #6 line 248 (:DecisionTrace nodes
    linked to :User and :Mechanism). Cypher MERGE pattern for
    idempotent upsert; duplicated-scalar indexing pattern for
    cypher analytics on serialized payloads.

(b) Tests pin: archive then load via fake async Neo4j driver
    preserves trace; soft-fail on no driver; cypher parameter
    contract pinned (decision_id / user_id / chosen_creative_id /
    chosen_mechanism / chosen_score / timestamp / payload_json /
    archived_at_ts / schema_version); user filter returns only
    that user's traces; idempotent MERGE — re-archive same
    decision_id updates rather than duplicates; missing
    decision_id → load returns None; bad JSON in node → load
    returns None.

(c) calibration_pending=False — schema is declarative, no
    pilot-data-dependent constants. (Index creation is operational,
    flagged in honest tags.)

(d) Honest tags — what is NOT in this slice (named successors):

    * Cypher index migration (CREATE INDEX ON :DecisionTrace(
      decision_id), CREATE INDEX ON :DecisionTrace(user_id),
      CREATE INDEX ON :DecisionTrace(timestamp)) — operational
      migration, not code; should run via the migration framework
      before this writer hits scale.
    * (:ConversionEdge) -[:RESOLVED]-> (:DecisionTrace) edge —
      written by the OutcomeHandler when an impression resolves to
      a conversion. Its own slice (depends on outcome event path).
    * Redis-to-Neo4j drain task (Task 38 or sibling) that ages
      Redis hot cache entries into Neo4j archive before TTL
      expiry — sibling slice; needs producer wiring first.
    * Cascade producer wiring — same sibling slice that closes
      Redis storage's missing producer.
    * Time-window queries via cypher
      (MATCH (u:User {id})-[:MADE_DECISION]->(d:DecisionTrace)
        WHERE d.timestamp >= $cutoff RETURN d ORDER BY d.timestamp DESC)
      are first-class on this schema; the helpers shipped here
      cover decision_id lookup + user-listing.
"""

from __future__ import annotations

import logging
import time
from typing import Any, List, Optional

from adam.intelligence.decision_trace import DecisionTrace

logger = logging.getLogger(__name__)


# =============================================================================
# Schema constants
# =============================================================================

DECISION_TRACE_NODE_LABEL: str = "DecisionTrace"
USER_NODE_LABEL: str = "User"
MECHANISM_NODE_LABEL: str = "Mechanism"

MADE_DECISION_REL: str = "MADE_DECISION"
USED_MECHANISM_REL: str = "USED_MECHANISM"


# =============================================================================
# Cypher (kept module-level so tests can pin the schema)
# =============================================================================


_ARCHIVE_CYPHER: str = (
    f"MERGE (d:{DECISION_TRACE_NODE_LABEL} {{decision_id: $decision_id}}) "
    "SET d.user_id = $user_id, "
    "    d.chosen_creative_id = $chosen_creative_id, "
    "    d.chosen_mechanism = $chosen_mechanism, "
    "    d.chosen_score = $chosen_score, "
    "    d.timestamp = $timestamp_epoch, "
    "    d.payload_json = $payload_json, "
    "    d.archived_at_ts = $archived_at_ts, "
    "    d.schema_version = $schema_version "
    "WITH d "
    f"MERGE (u:{USER_NODE_LABEL} {{id: $user_id}}) "
    f"MERGE (u)-[:{MADE_DECISION_REL}]->(d) "
    "WITH d "
    f"MERGE (m:{MECHANISM_NODE_LABEL} {{name: $chosen_mechanism}}) "
    f"MERGE (d)-[:{USED_MECHANISM_REL}]->(m)"
)

_LOAD_CYPHER: str = (
    f"MATCH (d:{DECISION_TRACE_NODE_LABEL} {{decision_id: $decision_id}}) "
    "RETURN d.payload_json AS payload_json LIMIT 1"
)

_LIST_FOR_USER_CYPHER: str = (
    f"MATCH (u:{USER_NODE_LABEL} {{id: $user_id}})"
    f"-[:{MADE_DECISION_REL}]->(d:{DECISION_TRACE_NODE_LABEL}) "
    "RETURN d.payload_json AS payload_json "
    "ORDER BY d.timestamp DESC "
    "LIMIT $limit"
)


# =============================================================================
# Archive
# =============================================================================


async def archive_trace_to_neo4j(
    trace: DecisionTrace,
    driver: Optional[Any],
) -> bool:
    """Persist a ``DecisionTrace`` to Neo4j as a :DecisionTrace node.

    Idempotent (MERGE on decision_id). Re-archiving the same trace
    overwrites scalar properties + payload_json — last writer wins.

    Soft-fail discipline:
      * No driver → False, log debug.
      * Cypher exception → False, log warning.
      * Trace serialization exception → False, log warning.
    """
    if driver is None:
        logger.debug(
            "archive_trace_to_neo4j: no driver (soft-fail to False)"
        )
        return False

    try:
        payload_json = trace.model_dump_json()
    except Exception as exc:
        logger.warning(
            "archive_trace_to_neo4j serialization failed for "
            "decision_id=%s: %s", trace.decision_id, exc,
        )
        return False

    timestamp_epoch = trace.timestamp.timestamp()
    archived_at_ts = time.time()

    try:
        async with driver.session() as session:
            await session.run(
                _ARCHIVE_CYPHER,
                decision_id=trace.decision_id,
                user_id=trace.user_id,
                chosen_creative_id=trace.chosen_creative_id,
                chosen_mechanism=trace.chosen_mechanism,
                chosen_score=float(trace.chosen_score),
                timestamp_epoch=float(timestamp_epoch),
                payload_json=payload_json,
                archived_at_ts=float(archived_at_ts),
                schema_version=trace.schema_version,
            )
    except Exception as exc:
        logger.warning(
            "archive_trace_to_neo4j cypher failed for decision_id=%s: %s",
            trace.decision_id, exc,
        )
        return False

    return True


# =============================================================================
# Load
# =============================================================================


async def load_trace_from_neo4j(
    decision_id: str,
    driver: Optional[Any],
) -> Optional[DecisionTrace]:
    """Fetch one ``DecisionTrace`` by decision_id.

    Returns None when:
      * driver is None
      * cypher read fails (logged at WARNING)
      * decision_id not found
      * payload_json fails to parse as DecisionTrace (logged)

    The function never raises — caller surfaces (DR renderer / audit)
    treat None as "not in archive" and degrade gracefully.
    """
    if driver is None:
        return None

    try:
        async with driver.session() as session:
            result = await session.run(
                _LOAD_CYPHER, decision_id=decision_id,
            )
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "load_trace_from_neo4j read failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return None

    if record is None:
        return None

    payload_json = record.get("payload_json")
    if not payload_json:
        return None

    try:
        if isinstance(payload_json, (bytes, bytearray)):
            payload_json = payload_json.decode("utf-8")
        return DecisionTrace.model_validate_json(payload_json)
    except Exception as exc:
        logger.warning(
            "load_trace_from_neo4j parse failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return None


# =============================================================================
# List by user
# =============================================================================


async def list_traces_for_user_from_neo4j(
    user_id: str,
    driver: Optional[Any],
    *,
    limit: int = 100,
) -> List[DecisionTrace]:
    """Fetch the user's archived traces in newest-first order.

    Uses the (:User)-[:MADE_DECISION]->(:DecisionTrace) edge written
    at archive time. ORDER BY d.timestamp DESC; supports limit.

    Returns an empty list on any failure path or when the user has
    no archived traces. Per-record parse failures are silently
    skipped — the function returns the records it could parse.
    """
    if driver is None:
        return []
    if limit <= 0:
        return []

    try:
        async with driver.session() as session:
            result = await session.run(
                _LIST_FOR_USER_CYPHER,
                user_id=user_id, limit=int(limit),
            )
            records = []
            async for r in result:
                records.append(r)
    except Exception as exc:
        logger.warning(
            "list_traces_for_user_from_neo4j read failed for user=%s: %s",
            user_id, exc,
        )
        return []

    traces: List[DecisionTrace] = []
    for r in records:
        payload_json = r.get("payload_json")
        if not payload_json:
            continue
        try:
            if isinstance(payload_json, (bytes, bytearray)):
                payload_json = payload_json.decode("utf-8")
            traces.append(DecisionTrace.model_validate_json(payload_json))
        except Exception as exc:
            logger.debug(
                "list_traces_for_user_from_neo4j skipping unparseable "
                "record for user=%s: %s", user_id, exc,
            )

    return traces
