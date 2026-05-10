"""Neo4j persistence for blind_analysis BlindAnalysisBox records.

Q.B/Q.3 Sketch C+ — closes the gap noted in C.1 §6 (the
pre-registration substrate is fully isolated from any caller in
production code paths). Every sealed box gets persisted as a
(:BlindAnalysisBox) node keyed on its deterministic SHA-256
pre_registration_hash. Discovery paths read the box state
(SEALED → AUTHORIZED → UNBLINDED) before persisting causal
edges; every persisted edge carries a `box_hash` property
linking the discovery to its pre-registration.

NODE / SCHEMA
-------------

    (:BlindAnalysisBox {
        hash:                       str (UNIQUE, MERGE key),
        name:                       str,
        decision_statistic:         str,
        decision_threshold:         float,
        parameters_json:            str (serialized BoxParameter list),
        signal_region_json:         str (serialized list of grid points),
        control_region_json:        str (serialized list of grid points),
        notes:                      str,
        state:                      str ("sealed" | "authorized" | "unblinded"),
        sealed_at:                  datetime,
        authorized_at:              datetime | null,
        authorizing_party:          str | null,
        authorization_justification: str | null,
        unblinded_at:               datetime | null,
        post_pilot_methods_json:    str | null,
    })

The `post_pilot_methods_json` property carries the Sketch C+
discipline anchor: the methods that will be added post-pilot are
sealed in the box at deploy time, preventing post-hoc test
design. Discovery against the box during pilot accumulates
observations; persistence of MODERATES edges happens only after
the box transitions to UNBLINDED.

DISCIPLINE (B3-LUXY)
--------------------

Tests pin: round-trip via fake async Neo4j preserves box; soft-
fail on no driver; idempotent MERGE on hash; state-machine
transitions honored (only SEALED → AUTHORIZED, only AUTHORIZED
→ UNBLINDED); reading by hash returns the persisted box;
read-then-state-check supports the discovery-side gating.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.blind_analysis.box import (
    BlindAnalysisBox,
    BoxParameter,
    BoxValidationError,
    UnblindingState,
    sealed_box,
)

logger = logging.getLogger(__name__)


BLIND_ANALYSIS_BOX_NODE_LABEL: str = "BlindAnalysisBox"


# =============================================================================
# Cypher
# =============================================================================


_WRITE_CYPHER: str = (
    f"MERGE (b:{BLIND_ANALYSIS_BOX_NODE_LABEL} {{hash: $hash}}) "
    "SET b.name = $name, "
    "    b.decision_statistic = $decision_statistic, "
    "    b.decision_threshold = $decision_threshold, "
    "    b.parameters_json = $parameters_json, "
    "    b.signal_region_json = $signal_region_json, "
    "    b.control_region_json = $control_region_json, "
    "    b.notes = $notes, "
    "    b.state = $state, "
    "    b.sealed_at = $sealed_at, "
    "    b.post_pilot_methods_json = $post_pilot_methods_json"
)


_READ_CYPHER: str = (
    f"MATCH (b:{BLIND_ANALYSIS_BOX_NODE_LABEL} {{hash: $hash}}) "
    "RETURN b LIMIT 1"
)


_AUTHORIZE_CYPHER: str = (
    f"MATCH (b:{BLIND_ANALYSIS_BOX_NODE_LABEL} {{hash: $hash}}) "
    "WHERE b.state = 'sealed' "
    "SET b.state = 'authorized', "
    "    b.authorized_at = $now, "
    "    b.authorizing_party = $party, "
    "    b.authorization_justification = $justification "
    "RETURN b"
)


_UNBLIND_CYPHER: str = (
    f"MATCH (b:{BLIND_ANALYSIS_BOX_NODE_LABEL} {{hash: $hash}}) "
    "WHERE b.state = 'authorized' "
    "SET b.state = 'unblinded', "
    "    b.unblinded_at = $now "
    "RETURN b"
)


# =============================================================================
# Serialization helpers
# =============================================================================


def _serialize_parameters(parameters: tuple) -> str:
    """Serialize the parameter tuple to JSON for Neo4j storage."""
    return json.dumps([
        {
            "name": p.name,
            "values": list(p.values),
            "description": p.description,
        }
        for p in parameters
    ])


def _serialize_region(region: frozenset) -> str:
    """Serialize a region (frozenset of tuples) to JSON-compatible list."""
    return json.dumps(sorted([list(t) for t in region]))


# =============================================================================
# Persistence API
# =============================================================================


async def write_box_to_neo4j(
    box: BlindAnalysisBox,
    driver: Optional[Any],
    *,
    post_pilot_methods: Optional[Dict[str, Any]] = None,
) -> bool:
    """Persist a sealed box as a (:BlindAnalysisBox) node.

    Idempotent: MERGE on the deterministic SHA-256 hash. Re-writing
    the same box (same hash) overwrites scalar properties; the hash
    itself never changes for a sealed box.

    Args:
        box: the sealed box to persist
        driver: async Neo4j driver; None → soft-fail to False
        post_pilot_methods: optional dict of post-pilot composition
            methods to seal alongside the box (Sketch C+ discipline:
            sealing post-pilot methods at deploy time prevents
            post-hoc test design when pilot data unblinds)

    Returns: True on successful persistence, False on driver
    absence or any cypher exception.
    """
    if driver is None:
        logger.debug("write_box_to_neo4j: no driver (soft-fail to False)")
        return False

    try:
        params = {
            "hash": box.pre_registration_hash,
            "name": box.name,
            "decision_statistic": box.decision_statistic,
            "decision_threshold": float(box.decision_threshold),
            "parameters_json": _serialize_parameters(box.parameters),
            "signal_region_json": _serialize_region(box.signal_region),
            "control_region_json": _serialize_region(box.control_region),
            "notes": box.notes,
            "state": box.state.value,
            "sealed_at": box.sealed_at,
            "post_pilot_methods_json": (
                json.dumps(post_pilot_methods)
                if post_pilot_methods is not None
                else None
            ),
        }
    except Exception as exc:
        logger.warning(
            "write_box_to_neo4j serialization failed for hash=%s: %s",
            getattr(box, "pre_registration_hash", "?"), exc,
        )
        return False

    try:
        async with driver.session() as session:
            await session.run(_WRITE_CYPHER, params)
    except Exception as exc:
        logger.warning(
            "write_box_to_neo4j cypher failed for hash=%s: %s",
            box.pre_registration_hash, exc,
        )
        return False

    return True


@dataclass(frozen=True)
class PersistedBoxRecord:
    """Read-only snapshot of a (:BlindAnalysisBox) node.

    Reconstructing a full BlindAnalysisBox from the node would
    require rebuilding the parameter grid + frozensets; for the
    discovery-side gating use-case the consumer only needs the
    state + hash + decision_threshold, so this record exposes
    those directly. The full payload is in *_json properties
    when needed.
    """
    hash: str
    name: str
    decision_statistic: str
    decision_threshold: float
    state: str
    sealed_at: Optional[datetime]
    authorized_at: Optional[datetime]
    unblinded_at: Optional[datetime]
    notes: str
    post_pilot_methods_json: Optional[str]

    @property
    def is_unblinded(self) -> bool:
        return self.state == UnblindingState.UNBLINDED.value


async def read_box_from_neo4j(
    box_hash: str,
    driver: Optional[Any],
) -> Optional[PersistedBoxRecord]:
    """Read a (:BlindAnalysisBox) node by hash.

    Returns None when:
      * driver is None
      * cypher read fails (logged at WARNING)
      * hash not found
    """
    if driver is None:
        return None

    try:
        async with driver.session() as session:
            result = await session.run(_READ_CYPHER, hash=box_hash)
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "read_box_from_neo4j read failed for hash=%s: %s",
            box_hash, exc,
        )
        return None

    if record is None:
        return None

    node = record.get("b")
    if node is None:
        return None

    def _to_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if hasattr(value, "to_native"):
            return value.to_native()
        if isinstance(value, datetime):
            return value
        return None

    return PersistedBoxRecord(
        hash=str(node.get("hash") or box_hash),
        name=str(node.get("name") or ""),
        decision_statistic=str(node.get("decision_statistic") or ""),
        decision_threshold=float(node.get("decision_threshold") or 0.0),
        state=str(node.get("state") or "sealed"),
        sealed_at=_to_datetime(node.get("sealed_at")),
        authorized_at=_to_datetime(node.get("authorized_at")),
        unblinded_at=_to_datetime(node.get("unblinded_at")),
        notes=str(node.get("notes") or ""),
        post_pilot_methods_json=(
            str(node["post_pilot_methods_json"])
            if node.get("post_pilot_methods_json") is not None
            else None
        ),
    )


async def authorize_box(
    box_hash: str,
    party: str,
    justification: str,
    driver: Optional[Any],
) -> bool:
    """Transition box from SEALED → AUTHORIZED in Neo4j.

    Per directive §G.1: unblinding authorization requires party +
    justification. The cypher's WHERE clause enforces the state
    machine — only sealed boxes can be authorized.

    Returns True on successful transition, False when driver is
    None / box not found / box not in SEALED state / cypher fails.
    """
    if driver is None:
        return False
    if not party or not justification:
        raise BoxValidationError(
            "authorize_box requires both party and justification"
        )
    try:
        async with driver.session() as session:
            result = await session.run(
                _AUTHORIZE_CYPHER,
                hash=box_hash,
                now=datetime.now(timezone.utc),
                party=party,
                justification=justification,
            )
            record = await result.single()
            return record is not None
    except Exception as exc:
        logger.warning(
            "authorize_box failed for hash=%s: %s", box_hash, exc,
        )
        return False


async def mark_unblinded(
    box_hash: str,
    driver: Optional[Any],
) -> bool:
    """Transition box from AUTHORIZED → UNBLINDED in Neo4j.

    The cypher's WHERE clause enforces the state machine — only
    authorized boxes can be unblinded; cannot skip from sealed.

    Returns True on successful transition, False otherwise.
    """
    if driver is None:
        return False
    try:
        async with driver.session() as session:
            result = await session.run(
                _UNBLIND_CYPHER,
                hash=box_hash,
                now=datetime.now(timezone.utc),
            )
            record = await result.single()
            return record is not None
    except Exception as exc:
        logger.warning(
            "mark_unblinded failed for hash=%s: %s", box_hash, exc,
        )
        return False


__all__ = [
    "BLIND_ANALYSIS_BOX_NODE_LABEL",
    "PersistedBoxRecord",
    "write_box_to_neo4j",
    "read_box_from_neo4j",
    "authorize_box",
    "mark_unblinded",
]
