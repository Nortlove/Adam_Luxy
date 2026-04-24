"""InferentialChainGraph — SCM-native theoretical-edge substrate.

Materializes the inferential chain that makes ADAM an inferential system
rather than a correlational one (ADAM_THEORETICAL_FOUNDATION.md §4.3):

    The graph must store the theoretical edges —
    (UncertaintyIntolerance)-[:CAUSES_NEED_FOR]->(Closure),
    (Closure)-[:SATISFIED_BY]->(Authority),
    (HighCognitiveEngagement)-[:REQUIRES]->(SubstantiveEvidence) —
    as first-class entities, not just the effectiveness edges...

These are theoretical edges grounded in peer-reviewed literature, distinct
from effectiveness edges learned from campaign outcomes. Each edge carries
a `citation` property — the canonical reference anchoring the claim.
Citation-less edges are drift (A6: template-string pattern libraries).

Schema: adam/infrastructure/neo4j/migrations/028_inferential_chain.cypher

This slice ships the SUBSTRATE: schema + upsert helpers. Traversal helpers
(given a buyer's active constructs, find receptive mechanisms) and the
Inferential Learning Agent's HYPOTHESIZE/VALIDATE integration land when the
plant-model adjudicator needs them (weeks 8-9 per pilot plan).

Design commitments:

- Construct nodes and theoretical edges are identified by stable slug-form
  ids/names. Upserts are idempotent.
- Every edge write requires a non-empty `citation` field. Callers attempting
  to write edges without citations hit a ValueError rather than silently
  producing citation-less edges.
- `evidence_count` starts at 0 and is updated by downstream adjudication —
  never by the upsert path. This keeps the theoretical (prior) and
  empirical (posterior) distinct.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from adam.infrastructure.neo4j.client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


# =============================================================================
# SYNC → ASYNC BRIDGE — persistent background loop
# =============================================================================

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
                name="InferentialChainGraph-bg-loop",
            )
            _bg_thread.start()
    return _bg_loop


def _fire_and_forget(coro) -> None:
    loop = _get_bg_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)

    def _on_done(fut):
        exc = fut.exception()
        if exc is not None:
            logger.warning(
                "InferentialChainGraph write failed: %s", exc, exc_info=exc,
            )

    future.add_done_callback(_on_done)


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass(frozen=True)
class PsychologicalConstructUpsert:
    """Identifying + descriptive shape for a PsychologicalConstruct node."""
    construct_id: str  # slug form (e.g., "need_for_closure")
    name: str  # display name
    description: str
    domain: str  # taxonomy domain (see construct_taxonomy.py)
    research_basis: str

    def validate(self) -> None:
        for field_name in (
            "construct_id", "name", "description", "domain", "research_basis",
        ):
            if not getattr(self, field_name):
                raise ValueError(
                    f"PsychologicalConstructUpsert.{field_name} is required"
                )
        if " " in self.construct_id:
            raise ValueError(
                f"construct_id should be slug-form (no spaces); "
                f"got {self.construct_id!r}"
            )


@dataclass(frozen=True)
class ActivatesEdge:
    """Theoretical edge: source PsychologicalConstruct activates target
    PsychologicalConstruct."""
    source_construct_id: str
    target_construct_id: str
    strength: float  # [0, 1]
    citation: str  # non-empty
    context: str = "general"
    notes: str = ""

    def validate(self) -> None:
        if not self.source_construct_id:
            raise ValueError("source_construct_id required")
        if not self.target_construct_id:
            raise ValueError("target_construct_id required")
        if self.source_construct_id == self.target_construct_id:
            raise ValueError(
                f"ACTIVATES cannot be a self-edge "
                f"({self.source_construct_id} -> {self.target_construct_id})"
            )
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"strength {self.strength} outside [0, 1]")
        if not self.citation or not self.citation.strip():
            raise ValueError(
                "ActivatesEdge.citation is required (non-empty string). "
                "Theoretical edges must be grounded in literature; "
                "citation-less edges are drift (orientation A6)."
            )


@dataclass(frozen=True)
class ReceptivityEdge:
    """Theoretical edge: source PsychologicalConstruct creates receptivity
    to target CognitiveMechanism.

    The mechanism_name must match a name on an existing CognitiveMechanism
    node from migration 004 (one of the 9 mechanisms). Examples:
    automatic_evaluation, wanting_liking_dissociation, evolutionary_motive_activation,
    linguistic_framing, mimetic_desire, embodied_cognition, attention_dynamics,
    identity_construction, temporal_construal.
    """
    source_construct_id: str
    mechanism_name: str
    effectiveness: float  # [0, 1]
    citation: str  # non-empty
    context: str = "general"
    notes: str = ""

    def validate(self) -> None:
        if not self.source_construct_id:
            raise ValueError("source_construct_id required")
        if not self.mechanism_name:
            raise ValueError("mechanism_name required")
        if not (0.0 <= self.effectiveness <= 1.0):
            raise ValueError(
                f"effectiveness {self.effectiveness} outside [0, 1]"
            )
        if not self.citation or not self.citation.strip():
            raise ValueError(
                "ReceptivityEdge.citation is required. Theoretical edges "
                "must be grounded in literature."
            )


@dataclass(frozen=True)
class RequiresEdge:
    """Theoretical edge: CognitiveMechanism requires prerequisite
    PsychologicalConstruct to be co-active."""
    mechanism_name: str
    prerequisite_construct_id: str
    citation: str
    notes: str = ""

    def validate(self) -> None:
        if not self.mechanism_name:
            raise ValueError("mechanism_name required")
        if not self.prerequisite_construct_id:
            raise ValueError("prerequisite_construct_id required")
        if not self.citation or not self.citation.strip():
            raise ValueError(
                "RequiresEdge.citation is required."
            )


# =============================================================================
# CYPHER
# =============================================================================

_CYPHER_UPSERT_CONSTRUCT = """
MERGE (c:PsychologicalConstruct {construct_id: $construct_id})
  ON CREATE SET
    c.name = $name,
    c.description = $description,
    c.domain = $domain,
    c.research_basis = $research_basis,
    c.observation_count = 0,
    c.first_seen = datetime()
SET
    c.last_updated = datetime(),
    c.name = coalesce(c.name, $name),
    c.description = coalesce(c.description, $description),
    c.domain = coalesce(c.domain, $domain),
    c.research_basis = coalesce(c.research_basis, $research_basis)
RETURN c.construct_id AS construct_id
"""


_CYPHER_UPSERT_ACTIVATES = """
MATCH (src:PsychologicalConstruct {construct_id: $source_construct_id})
MATCH (tgt:PsychologicalConstruct {construct_id: $target_construct_id})
MERGE (src)-[r:ACTIVATES]->(tgt)
  ON CREATE SET
    r.evidence_count = 0,
    r.first_seen = datetime()
SET
    r.strength = $strength,
    r.citation = $citation,
    r.context = $context,
    r.notes = $notes,
    r.last_updated = datetime()
RETURN type(r) AS rel_type
"""


_CYPHER_UPSERT_RECEPTIVITY = """
MATCH (src:PsychologicalConstruct {construct_id: $source_construct_id})
MATCH (m:CognitiveMechanism {name: $mechanism_name})
MERGE (src)-[r:CREATES_RECEPTIVITY_TO]->(m)
  ON CREATE SET
    r.evidence_count = 0,
    r.first_seen = datetime()
SET
    r.effectiveness = $effectiveness,
    r.citation = $citation,
    r.context = $context,
    r.notes = $notes,
    r.last_updated = datetime()
RETURN type(r) AS rel_type
"""


_CYPHER_UPSERT_REQUIRES = """
MATCH (m:CognitiveMechanism {name: $mechanism_name})
MATCH (c:PsychologicalConstruct {construct_id: $prerequisite_construct_id})
MERGE (m)-[r:REQUIRES]->(c)
  ON CREATE SET
    r.first_seen = datetime()
SET
    r.citation = $citation,
    r.notes = $notes,
    r.last_updated = datetime()
RETURN type(r) AS rel_type
"""


# =============================================================================
# SERVICE
# =============================================================================

class InferentialChainGraph:
    """Neo4j service for upserting PsychologicalConstruct nodes and the
    theoretical edges forming the inferential chain.

    Shadow-write safety: exceptions swallowed with log callbacks; never
    blocks the primary path. Sync entry points are fire-and-forget.
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        self._client = client or get_neo4j_client()

    # ── UPSERT CONSTRUCT ────────────────────────────────────────────────

    def upsert_construct_sync(
        self, construct: PsychologicalConstructUpsert,
    ) -> None:
        """Fire-and-forget construct upsert."""
        _fire_and_forget(self.upsert_construct(construct))

    async def upsert_construct(
        self, construct: PsychologicalConstructUpsert,
    ) -> Optional[str]:
        """Upsert a PsychologicalConstruct node. Returns construct_id on
        success, None on failure."""
        try:
            construct.validate()
        except ValueError as exc:
            logger.warning("PsychologicalConstruct validation failed: %s", exc)
            return None

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_UPSERT_CONSTRUCT,
                    construct_id=construct.construct_id,
                    name=construct.name,
                    description=construct.description,
                    domain=construct.domain,
                    research_basis=construct.research_basis,
                )
                record = await result.single()
                return record["construct_id"] if record else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "PsychologicalConstruct upsert failed for %s: %s",
                construct.construct_id, exc, exc_info=True,
            )
            return None

    # ── UPSERT ACTIVATES EDGE ───────────────────────────────────────────

    async def upsert_activates(self, edge: ActivatesEdge) -> Optional[str]:
        """Upsert an ACTIVATES edge between two PsychologicalConstruct nodes.
        Both endpoints must already exist (upsert them first)."""
        try:
            edge.validate()
        except ValueError as exc:
            logger.warning("ActivatesEdge validation failed: %s", exc)
            return None

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_UPSERT_ACTIVATES,
                    source_construct_id=edge.source_construct_id,
                    target_construct_id=edge.target_construct_id,
                    strength=edge.strength,
                    citation=edge.citation,
                    context=edge.context,
                    notes=edge.notes,
                )
                record = await result.single()
                return record["rel_type"] if record else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ACTIVATES upsert failed (%s -> %s): %s",
                edge.source_construct_id, edge.target_construct_id,
                exc, exc_info=True,
            )
            return None

    # ── UPSERT RECEPTIVITY EDGE ─────────────────────────────────────────

    async def upsert_receptivity(self, edge: ReceptivityEdge) -> Optional[str]:
        """Upsert a CREATES_RECEPTIVITY_TO edge from PsychologicalConstruct
        to CognitiveMechanism. The mechanism node (from migration 004)
        must already exist."""
        try:
            edge.validate()
        except ValueError as exc:
            logger.warning("ReceptivityEdge validation failed: %s", exc)
            return None

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_UPSERT_RECEPTIVITY,
                    source_construct_id=edge.source_construct_id,
                    mechanism_name=edge.mechanism_name,
                    effectiveness=edge.effectiveness,
                    citation=edge.citation,
                    context=edge.context,
                    notes=edge.notes,
                )
                record = await result.single()
                return record["rel_type"] if record else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "CREATES_RECEPTIVITY_TO upsert failed (%s -> %s): %s",
                edge.source_construct_id, edge.mechanism_name,
                exc, exc_info=True,
            )
            return None

    # ── UPSERT REQUIRES EDGE ────────────────────────────────────────────

    async def upsert_requires(self, edge: RequiresEdge) -> Optional[str]:
        """Upsert a REQUIRES edge from CognitiveMechanism to a prerequisite
        PsychologicalConstruct."""
        try:
            edge.validate()
        except ValueError as exc:
            logger.warning("RequiresEdge validation failed: %s", exc)
            return None

        if not await self._ensure_connected():
            return None

        try:
            async with await self._client.session() as session:
                result = await session.run(
                    _CYPHER_UPSERT_REQUIRES,
                    mechanism_name=edge.mechanism_name,
                    prerequisite_construct_id=edge.prerequisite_construct_id,
                    citation=edge.citation,
                    notes=edge.notes,
                )
                record = await result.single()
                return record["rel_type"] if record else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "REQUIRES upsert failed (%s -> %s): %s",
                edge.mechanism_name, edge.prerequisite_construct_id,
                exc, exc_info=True,
            )
            return None

    # ── INTERNAL ────────────────────────────────────────────────────────

    async def _ensure_connected(self) -> bool:
        if self._client.is_connected:
            return True
        connected = await self._client.connect()
        if not connected:
            logger.debug(
                "InferentialChainGraph write skipped: Neo4j unavailable"
            )
        return connected


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_service: Optional[InferentialChainGraph] = None


def get_inferential_chain_graph() -> InferentialChainGraph:
    """Module-level accessor for the singleton InferentialChainGraph."""
    global _service
    if _service is None:
        _service = InferentialChainGraph()
    return _service
