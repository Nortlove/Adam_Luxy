"""
Decision Context Cache — Links Decisions to Outcomes
======================================================

When the bilateral cascade makes a creative intelligence decision, the full
context is persisted here (archetype, mechanism_sent, cascade_level, alignment
predictions, buyer_id, edge_dimensions). When a conversion webhook arrives
hours later, the outcome handler retrieves this context so it can credit the
RIGHT archetype, the RIGHT mechanism, and update the RIGHT buyer profile.

Without this link, the learning loop is blind: outcomes arrive but the system
doesn't know what decision produced them.

Storage: In-memory LRU with optional Redis persistence.
TTL: 48 hours (covers the conversion attribution window).
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from adam.config.settings import get_settings

def _decision_ttl():
    return get_settings().cascade.decision_cache_ttl

def _max_decisions():
    return get_settings().cascade.decision_cache_max_size


@dataclass
class DecisionContext:
    """Everything the outcome handler needs to close the learning loop."""

    decision_id: str

    # What was decided
    archetype: str = ""
    mechanism_sent: str = ""
    secondary_mechanism: str = ""
    mechanisms_considered: List[str] = field(default_factory=list)
    cascade_level: int = 1
    evidence_source: str = "archetype_prior"

    # Alignment predictions at decision time
    edge_dimensions: Dict[str, float] = field(default_factory=dict)
    mechanism_scores: Dict[str, float] = field(default_factory=dict)
    framing: str = "mixed"
    ndf_profile: Dict[str, float] = field(default_factory=dict)

    # Context
    segment_id: str = ""
    asin: str = ""
    buyer_id: str = ""
    content_category: str = ""
    product_category: str = ""

    # Gradient intelligence snapshot (for gradient field recomputation)
    gradient_priorities: List[Dict[str, Any]] = field(default_factory=list)

    # Information value snapshot
    information_value: float = 0.0
    buyer_confidence: float = 0.0

    # Page context intelligence at decision time (for outcome learning)
    context_mindset: str = ""
    context_domain: str = ""
    context_decision_style: str = ""     # deliberative, moderate, impulsive
    context_open_channels: List[str] = field(default_factory=list)
    context_closed_channels: List[str] = field(default_factory=list)
    context_activated_needs: Dict[str, float] = field(default_factory=dict)
    context_publisher_authority: float = 0.0
    context_elm_route: str = ""          # central, mixed, peripheral

    # Page edge dimensions at decision time (20-dim, same space as bilateral edges)
    # This is THE page's psychological state — enables causal learning
    page_edge_dimensions: Dict[str, float] = field(default_factory=dict)
    page_edge_scoring_tier: str = ""  # "full_extraction", "taxonomy_category", "ndf_fallback"
    page_confidence: float = 0.0

    # Mechanism portfolio at decision time (for interaction learning)
    mechanism_portfolio: List[Dict[str, Any]] = field(default_factory=list)

    # Therapeutic retargeting context (Enhancement #33)
    # Populated when this decision is a retargeting touch, empty for first-touch.
    barrier_diagnosed: str = ""           # BarrierCategory value
    therapeutic_mechanism: str = ""       # TherapeuticMechanism value
    sequence_id: str = ""                 # Active TherapeuticSequence ID
    touch_position: int = 0              # Position in sequence (1-indexed)
    scaffold_level: int = 0              # ScaffoldLevel (1-5, 0 = not retargeting)
    conversion_stage: str = ""           # ConversionStage at decision time

    # Copy variant tracking (for copy effectiveness learning)
    copy_variant_id: str = ""
    copy_tone: str = ""
    copy_framing: str = ""
    copy_evidence_type: str = ""
    copy_cta_style: str = ""

    # Epistemic status of the reasoning chain that produced this decision.
    # See adam/core/decision_mode.py. Default "grounded" preserves legacy
    # behavior for decisions persisted before this field existed; new code
    # paths MUST populate these explicitly. The outcome handler's learning
    # gate reads these fields to decide whether to update posteriors.
    decision_mode: str = "grounded"
    grounding_evidence: Dict[str, Any] = field(default_factory=lambda: {
        "bilateral_edge_evidence_present": True,
        "atom_run_real": True,
        "theoretical_link_traversed": True,
        "failure_reasons": [],
    })
    missing_links: List[str] = field(default_factory=list)
    refusal_reason: str = ""

    # Timing
    created_at: float = field(default_factory=time.time)

    def to_outcome_metadata(self) -> Dict[str, Any]:
        """Convert to the metadata dict that OutcomeHandler.process_outcome expects.

        This replaces the unreliable metadata that was previously inferred
        from the webhook event. Now every field is the actual value from
        decision time.
        """
        return {
            "source": "stackadapt_pixel",
            "segment_id": self.segment_id,
            "archetype": self.archetype,
            # CRITICAL: mechanism_sent is the ONLY mechanism that should
            # receive Thompson Sampling credit. Previously, all considered
            # mechanisms got credit — systematic overcounting.
            "mechanism_sent": self.mechanism_sent,
            "mechanisms_applied": [self.mechanism_sent],
            "mechanisms_considered": self.mechanisms_considered,
            "secondary_mechanism": self.secondary_mechanism,
            "cascade_level": self.cascade_level,
            "evidence_source": self.evidence_source,
            "alignment_scores": self.edge_dimensions,
            "mechanism_scores": self.mechanism_scores,
            "framing": self.framing,
            "ndf_profile": self.ndf_profile,
            "asin": self.asin,
            "buyer_id": self.buyer_id,
            "product_category": self.product_category,
            "content_category": self.content_category,
            "gradient_priorities": self.gradient_priorities,
            "information_value_at_decision": self.information_value,
            "buyer_confidence_at_decision": self.buyer_confidence,
            "decision_timestamp": self.created_at,
            # Page context for learning (enables learning conditioned on page state)
            "context_mindset": self.context_mindset,
            "context_domain": self.context_domain,
            "context_decision_style": self.context_decision_style,
            "context_open_channels": self.context_open_channels,
            "context_closed_channels": self.context_closed_channels,
            "context_activated_needs": self.context_activated_needs,
            "context_publisher_authority": self.context_publisher_authority,
            "context_elm_route": self.context_elm_route,
            # Page edge dimensions for causal learning (20-dim, same space as bilateral edges)
            "page_edge_dimensions": self.page_edge_dimensions,
            "page_edge_scoring_tier": self.page_edge_scoring_tier,
            "page_confidence": self.page_confidence,
            # Therapeutic retargeting context (Enhancement #33)
            "barrier_diagnosed": self.barrier_diagnosed,
            "therapeutic_mechanism": self.therapeutic_mechanism,
            "sequence_id": self.sequence_id,
            "touch_position": self.touch_position,
            "scaffold_level": self.scaffold_level,
            "conversion_stage": self.conversion_stage,
            # Copy variant tracking
            "copy_variant_id": self.copy_variant_id,
            "copy_tone": self.copy_tone,
            "copy_framing": self.copy_framing,
            "copy_evidence_type": self.copy_evidence_type,
            "copy_cta_style": self.copy_cta_style,
            # Epistemic status — read by the outcome handler's learning gate.
            # Key names match the constants in adam/core/decision_mode.py
            # (DECISION_MODE_METADATA_KEY, GROUNDING_EVIDENCE_METADATA_KEY).
            "decision_mode": self.decision_mode,
            "grounding_evidence": dict(self.grounding_evidence),
            "missing_links": list(self.missing_links),
            "refusal_reason": self.refusal_reason,
        }


class DecisionCache:
    """In-memory LRU cache with TTL for decision contexts.

    Thread-safe via OrderedDict operations. For production at scale,
    this should be backed by Redis (see persist_to_redis / load_from_redis).
    """

    def __init__(self, maxsize: int = None, ttl_seconds: int = None):
        if maxsize is None:
            maxsize = _max_decisions()
        if ttl_seconds is None:
            ttl_seconds = _decision_ttl()
        self._store: OrderedDict[str, DecisionContext] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def persist(self, ctx: DecisionContext) -> None:
        """Store a decision context for later retrieval by outcome handler.

        Writes to both in-memory cache (fast) and Neo4j (durable) so that
        outcomes arriving after an app restart can still find their context.
        """
        key = ctx.decision_id

        # Evict if full
        if key not in self._store and len(self._store) >= self._maxsize:
            self._store.popitem(last=False)

        self._store[key] = ctx
        self._store.move_to_end(key)

        # Async write-through to Neo4j (fire-and-forget)
        self._persist_to_neo4j(ctx)

        logger.debug(
            "Decision persisted: id=%s arch=%s mech=%s level=%d",
            key, ctx.archetype, ctx.mechanism_sent, ctx.cascade_level,
        )

    def _persist_to_neo4j(self, ctx: DecisionContext) -> None:
        """Fire-and-forget Neo4j write for decision context durability."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_persist_to_neo4j(ctx))
        except RuntimeError:
            pass  # No event loop — skip durable write

    async def _async_persist_to_neo4j(self, ctx: DecisionContext) -> None:
        """Write decision context to Neo4j DecisionContext node."""
        try:
            from adam.core.dependencies import get_infrastructure
            import json

            infra = await get_infrastructure()
            driver = getattr(infra, "neo4j_driver", None) if infra else None
            if not driver:
                return

            metadata_json = json.dumps(ctx.to_outcome_metadata(), default=str)

            async with driver.session() as session:
                await session.run(
                    """
                    MERGE (dc:DecisionContext {decision_id: $decision_id})
                    SET dc.archetype = $archetype,
                        dc.mechanism_sent = $mechanism_sent,
                        dc.cascade_level = $cascade_level,
                        dc.buyer_id = $buyer_id,
                        dc.segment_id = $segment_id,
                        dc.metadata_json = $metadata_json,
                        dc.created_at = $created_at
                    """,
                    decision_id=ctx.decision_id,
                    archetype=ctx.archetype,
                    mechanism_sent=ctx.mechanism_sent,
                    cascade_level=ctx.cascade_level,
                    buyer_id=ctx.buyer_id,
                    segment_id=ctx.segment_id,
                    metadata_json=metadata_json,
                    created_at=ctx.created_at,
                )
        except Exception as e:
            logger.debug("Neo4j decision context write failed: %s", e)

    def retrieve(self, decision_id: str) -> Optional[DecisionContext]:
        """Retrieve decision context for outcome attribution.

        Returns None if the decision has expired or was never cached.
        """
        ctx = self._store.get(decision_id)
        if ctx is None:
            self._misses += 1
            return None

        # Check TTL
        if time.time() - ctx.created_at > self._ttl:
            del self._store[decision_id]
            self._misses += 1
            return None

        self._hits += 1
        self._store.move_to_end(decision_id)
        return ctx

    def lookup_by_buyer_segment(self, buyer_id: str, segment_id: str) -> Optional[DecisionContext]:
        """Fallback lookup when decision_id doesn't match.

        Searches for the most recent decision for this buyer + segment combo.
        This handles the case where StackAdapt doesn't echo back our decision_id.
        """
        now = time.time()
        best: Optional[DecisionContext] = None
        for ctx in reversed(self._store.values()):
            if now - ctx.created_at > self._ttl:
                continue
            if ctx.buyer_id == buyer_id and ctx.segment_id == segment_id:
                best = ctx
                break
        if best:
            self._hits += 1
        else:
            self._misses += 1
        return best

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._store),
            "max_size": self._maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
        }


# ── Singleton ──────────────────────────────────────────────────────────────

_cache: Optional[DecisionCache] = None


def get_decision_cache() -> DecisionCache:
    global _cache
    if _cache is None:
        _cache = DecisionCache()
    return _cache
