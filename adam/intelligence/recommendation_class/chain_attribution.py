"""Chain-attribution — walk the inferential chain and attribute the
adjudicator's `unexplained` residual to specific theoretical edges on
failing cells.

Retires ``a14_compromises.INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY``.

What this module is, honestly
-----------------------------

- **Ranking signal for theory revision**, not causal identification.
  The attribution dict names which theoretical edges carry the largest
  share of the unexplained residual under a strength-weighted
  accounting; it does not prove those edges are wrong. The Inferential
  Learning Agent consumes the ranking to prioritize HYPOTHESIZE /
  VALIDATE cycles; downstream causal claims are validated by the ILA,
  not asserted here.
- **Strength-weighted**, not uniform. Flat attribution redistributes
  the residual without adding information — that stays flagged as
  pseudo-attribution (orientation A1). Edges with larger stored
  strength claims get proportionally larger shares of residual because
  they're the claims with the biggest stakes if the theory is off.
- **Signed-preserving**. A FAILING cell has negative `unexplained`
  (realized fell short of projected). The attribution keeps the sign
  so the ILA can tell over-projection from under-projection at
  edge granularity.

Frame discipline (orientation A2, A5, A6)
-----------------------------------------

- No invented defaults. Attribution weights come ONLY from edge
  properties already stored in migration 028 (ACTIVATES.strength,
  CREATES_RECEPTIVITY_TO.effectiveness). No tunable constants, no
  Likert-disguised ordinals.
- REQUIRES edges get zero weight. REQUIRES is categorical (a
  prerequisite is either co-active or it is not); it does not carry
  proportional magnitude that the residual could be apportioned
  against.
- Link IDs are deterministic over (source_id, rel_type, target_id).
  The same edge always hashes identically across attribution runs, so
  the ILA can accumulate attribution across cells by link_id.

Scope of this slice
-------------------

- `ChainEdge` — frozen read-projection of an edge in the inferential
  chain reachable from a mechanism.
- `link_id()` — deterministic hash for cross-cell attribution
  aggregation.
- `attribute_residual()` — pure-Python strength-weighted attribution.
- `make_chain_reader()` — factory producing a sync callable suitable
  for injection into the Adjudicator; wraps the InferentialChainGraph
  async traversal.

Not in this slice (named successors):

- Activation-conditional traversal (only edges whose source construct
  was actually active at decision time). Requires decision-time
  activation logging that is not captured today.
- Evidence-count weighting (low evidence_count → higher attribution
  due to uncertainty). Composes naturally with strength weighting but
  adds a second axis; pilot ships strength-only.
- Path-level counterfactual / Shapley attribution. Post-pilot.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional, Sequence, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from adam.intelligence.recommendation_class.inferential_chain import (
        InferentialChainGraph,
    )


# Edge relationship types recognized by chain attribution. Keeping this as a
# module-level Literal avoids stringly-typed drift on rel_type values.
ChainEdgeRelType = Literal[
    "ACTIVATES",
    "CREATES_RECEPTIVITY_TO",
    "REQUIRES",
]


# =============================================================================
# ChainEdge — read projection
# =============================================================================


@dataclass(frozen=True)
class ChainEdge:
    """A theoretical edge reachable from a rec-class's mechanism.

    `strength`:
        For ``ACTIVATES``: the edge's ``strength`` property.
        For ``CREATES_RECEPTIVITY_TO``: the ``effectiveness`` property.
        For ``REQUIRES``: 0.0 (categorical prerequisite — see module
        docstring).

    `evidence_count`: number of adjudication cycles that have updated
        this edge's empirical support. 0 at first traversal; grows as
        the ILA accumulates evidence. Not used in pilot attribution
        (see module docstring "Not in this slice"); exposed here so
        post-pilot evidence-weighted attribution can consume it
        without re-traversal.

    `depth_from_mechanism`: hops back from the mechanism node.
        CREATES_RECEPTIVITY_TO edges have depth 1; ACTIVATES cascades
        chain depth 2, 3, ... upstream. REQUIRES edges (outbound from
        mechanism) have depth 1.
    """

    source_id: str
    target_id: str
    rel_type: ChainEdgeRelType
    strength: float
    evidence_count: int
    depth_from_mechanism: int

    def validate(self) -> None:
        if not self.source_id:
            raise ValueError("ChainEdge.source_id is required")
        if not self.target_id:
            raise ValueError("ChainEdge.target_id is required")
        if self.rel_type not in ("ACTIVATES", "CREATES_RECEPTIVITY_TO", "REQUIRES"):
            raise ValueError(
                f"ChainEdge.rel_type must be ACTIVATES, "
                f"CREATES_RECEPTIVITY_TO, or REQUIRES; got {self.rel_type!r}"
            )
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(
                f"ChainEdge.strength must be in [0, 1]; got {self.strength}"
            )
        if self.evidence_count < 0:
            raise ValueError(
                f"ChainEdge.evidence_count must be >= 0; "
                f"got {self.evidence_count}"
            )
        if self.depth_from_mechanism < 1:
            raise ValueError(
                f"ChainEdge.depth_from_mechanism must be >= 1; "
                f"got {self.depth_from_mechanism}"
            )

    @property
    def link_id(self) -> str:
        """Deterministic link identifier for cross-cell attribution."""
        return compute_link_id(
            self.source_id, self.rel_type, self.target_id,
        )


def compute_link_id(
    source_id: str, rel_type: ChainEdgeRelType, target_id: str,
) -> str:
    """Deterministic SHA-256 prefix over (source, rel_type, target).

    Shared between edge construction and any external consumer that
    needs to match attribution entries to graph edges without holding
    a ChainEdge instance.
    """
    raw = f"{source_id}|{rel_type}|{target_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"link_{digest}"


# =============================================================================
# attribute_residual — pure-Python strength-weighted attribution
# =============================================================================


def attribute_residual(
    chain_edges: Sequence[ChainEdge],
    unexplained_residual: float,
) -> Dict[str, float]:
    """Attribute the signed `unexplained_residual` to chain edges.

    Weighting: ACTIVATES and CREATES_RECEPTIVITY_TO edges weighted by
    their stored strength / effectiveness. REQUIRES edges weighted 0
    (categorical — do not carry proportional blame).

    Edge cases:

    - Empty input → ``{}``.
    - All edges are REQUIRES or all strengths are zero → ``{}``. Flat
      attribution would be dishonest (no differentiation); empty is
      the correct honest response.
    - ``unexplained_residual == 0`` → ``{}``. Nothing to attribute.
    - Edges with strength 0 are skipped (they contribute neither to the
      weight total nor to the attribution dict).

    Returns a dict keyed by ``ChainEdge.link_id``; sum of values
    equals ``unexplained_residual`` modulo float accumulation, and
    preserves sign.
    """
    if not chain_edges:
        return {}
    if unexplained_residual == 0.0:
        return {}

    weights: List[float] = []
    for edge in chain_edges:
        if edge.rel_type == "REQUIRES":
            weights.append(0.0)
            continue
        weights.append(edge.strength)

    total = sum(weights)
    if total <= 0.0:
        return {}

    attribution: Dict[str, float] = {}
    for edge, weight in zip(chain_edges, weights):
        if weight <= 0.0:
            continue
        portion = unexplained_residual * (weight / total)
        # If the same link_id appears more than once (traversal produced
        # the same edge via different paths), sum the portions so the
        # final dict preserves sum==unexplained_residual.
        attribution[edge.link_id] = attribution.get(edge.link_id, 0.0) + portion
    return attribution


# =============================================================================
# make_chain_reader — adjudicator-injection factory
# =============================================================================


ChainReader = Callable[[str], Sequence[ChainEdge]]


def make_chain_reader(
    graph: Optional["InferentialChainGraph"] = None,
    max_depth: int = 2,
    timeout_seconds: float = 2.0,
) -> ChainReader:
    """Return a sync closure that reads chain edges for a mechanism.

    The closure is the shape the Adjudicator accepts for its
    ``chain_reader`` field. Production callers inject the closure
    backed by the singleton graph; tests inject a lambda returning a
    fixed list.

    ``max_depth`` bounds the ACTIVATES cascade depth upstream of the
    CREATES_RECEPTIVITY_TO layer. Depth 2 is the pilot default:
    direct receptivity + one layer of construct activation. Larger
    depths add fan-out without surfacing meaningfully distinct
    attribution claims for most mechanisms.

    ``timeout_seconds`` caps the blocking wait on the async graph
    call. Exceeding the timeout returns an empty list rather than
    blocking adjudication.
    """
    from adam.intelligence.recommendation_class.inferential_chain import (
        get_inferential_chain_graph,
    )

    resolved_graph = graph or get_inferential_chain_graph()

    def _read(mechanism_name: str) -> Sequence[ChainEdge]:
        try:
            return resolved_graph.chain_edges_for_mechanism_sync(
                mechanism_name,
                max_depth=max_depth,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "chain_edges_for_mechanism_sync(%r) failed: %s",
                mechanism_name, exc,
            )
            return []

    return _read


# =============================================================================
# Internal helper — blocking wait with timeout over async coroutine
# =============================================================================


def run_blocking_with_timeout(
    loop: asyncio.AbstractEventLoop,
    coro,
    timeout_seconds: float,
) -> object:
    """Run an async coroutine on ``loop`` from a sync context and wait
    up to ``timeout_seconds`` for the result.

    Used by the chain-edges-for-mechanism sync wrapper. Exposed here
    so the adjudicator's injected closure has a consistent timeout
    policy independent of whatever the graph module's write-path loop
    is doing.
    """
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout_seconds)


__all__ = [
    "ChainEdge",
    "ChainEdgeRelType",
    "ChainReader",
    "attribute_residual",
    "compute_link_id",
    "make_chain_reader",
    "run_blocking_with_timeout",
]
