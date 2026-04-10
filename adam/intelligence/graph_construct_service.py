"""
Graph Construct Service — Runtime Interface for ADAM's Construct Graph.

Replaces PsychologicalConstructResolver with a direct-to-graph interface
that provides continuous-valued construct vectors for real-time scoring.

Key capabilities:
1. User construct vector query (edge-tier constructs, <10ms)
2. Ad/Brand construct vector query
3. Peer and ecosystem construct vectors
4. Alignment scoring using Bayesian posteriors
5. PREDICTS edge traversal for mechanism selection

Architecture:
  - Edge-tier constructs: Neo4j query + Redis cache -> continuous vectors
  - Reasoning-tier constructs: Passed to Claude context for atom processing
  - All computation is mathematical on continuous floats (never categorical)

AUTHORITATIVE SOURCE: taxonomy/Construct_Taxonomy_v2_COMPLETE.md
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from adam.intelligence.construct_taxonomy import (
    ALL_DOMAINS,
    Construct,
    EdgeType,
    InferenceTier,
    ScoringSwitch,
    get_all_constructs,
    get_constructs_by_side,
    get_edge_constructs,
    get_reasoning_constructs,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ConstructVector:
    """A scored vector of construct values — the core runtime representation.

    All values are continuous floats. Categories/types are NEVER used
    for computation. This is the fundamental principle of the system.
    """
    scores: dict[str, float] = field(default_factory=dict)
    confidences: dict[str, float] = field(default_factory=dict)
    source: str = "graph"  # "graph", "inference", "prior", "cold_start"
    timestamp: float = 0.0

    @property
    def dimensions(self) -> int:
        """Number of scored constructs."""
        return len(self.scores)

    def get(self, construct_id: str, default: float = 0.5) -> float:
        """Get a single construct score."""
        return self.scores.get(construct_id, default)

    def get_with_confidence(
        self, construct_id: str
    ) -> tuple[float, float]:
        """Get (score, confidence) for a construct."""
        return (
            self.scores.get(construct_id, 0.5),
            self.confidences.get(construct_id, 0.0),
        )

    def subset(self, construct_ids: list[str]) -> ConstructVector:
        """Return a new vector with only the specified constructs."""
        return ConstructVector(
            scores={k: v for k, v in self.scores.items() if k in construct_ids},
            confidences={k: v for k, v in self.confidences.items() if k in construct_ids},
            source=self.source,
            timestamp=self.timestamp,
        )

    def merge(self, other: ConstructVector, prefer_other: bool = True) -> ConstructVector:
        """Merge two vectors, preferring the one with higher confidence or other."""
        merged_scores = dict(self.scores)
        merged_conf = dict(self.confidences)

        for cid, score in other.scores.items():
            if prefer_other or cid not in merged_scores:
                merged_scores[cid] = score
                merged_conf[cid] = other.confidences.get(cid, 0.0)
            else:
                # Keep whichever has higher confidence
                existing_conf = merged_conf.get(cid, 0.0)
                other_conf = other.confidences.get(cid, 0.0)
                if other_conf > existing_conf:
                    merged_scores[cid] = score
                    merged_conf[cid] = other_conf

        return ConstructVector(
            scores=merged_scores,
            confidences=merged_conf,
            source=f"{self.source}+{other.source}",
            timestamp=max(self.timestamp, other.timestamp),
        )


@dataclass
class AlignmentResult:
    """Result of aligning a user vector with an ad/brand vector."""
    overall_score: float = 0.5
    construct_pair_scores: dict[str, float] = field(default_factory=dict)
    top_alignments: list[tuple[str, str, float]] = field(default_factory=list)
    top_misalignments: list[tuple[str, str, float]] = field(default_factory=list)
    mechanism_recommendations: dict[str, float] = field(default_factory=dict)
    edge_type: EdgeType = EdgeType.BRAND_CONVERTED
    computation_time_ms: float = 0.0


# =============================================================================
# GRAPH CONSTRUCT SERVICE
# =============================================================================

class GraphConstructService:
    """
    Runtime service for querying and computing with construct vectors.

    This is the primary interface for atoms and the orchestrator to access
    the construct graph at runtime. All returned data is continuous-valued.
    """

    def __init__(self, neo4j_driver=None, redis_client=None):
        self._driver = neo4j_driver
        self._redis = redis_client
        self._construct_registry = get_all_constructs()
        self._edge_constructs = get_edge_constructs()
        self._reasoning_constructs = get_reasoning_constructs()
        self._user_constructs = get_constructs_by_side(ScoringSwitch.USER_SIDE)
        self._ad_constructs = get_constructs_by_side(ScoringSwitch.AD_SIDE)
        self._shared_constructs = get_constructs_by_side(ScoringSwitch.BOTH)

        # Cache
        self._user_vector_cache: dict[str, ConstructVector] = {}
        self._ad_vector_cache: dict[str, ConstructVector] = {}

    # -------------------------------------------------------------------------
    # USER CONSTRUCT VECTORS
    # -------------------------------------------------------------------------

    def get_user_vector(
        self,
        user_id: str,
        tier: Optional[InferenceTier] = None,
        domain_filter: Optional[list[str]] = None,
    ) -> ConstructVector:
        """
        Get the user's construct vector.

        For edge-tier constructs: queries Neo4j (with Redis cache).
        For reasoning-tier: returns priors + any persisted insights.

        Args:
            user_id: The user identifier.
            tier: Filter to specific tier (None = both).
            domain_filter: Filter to specific domains.

        Returns:
            ConstructVector with continuous scores for all requested constructs.
        """
        start_time = time.monotonic()
        cache_key = f"user:{user_id}:{tier}:{domain_filter}"

        # Check in-memory cache
        if cache_key in self._user_vector_cache:
            return self._user_vector_cache[cache_key]

        # Check Redis cache
        cached = self._check_redis_cache(f"uv:{user_id}")
        if cached is not None:
            self._user_vector_cache[cache_key] = cached
            return cached

        # Query Neo4j for user's construct scores
        vector = self._query_user_constructs(user_id, tier, domain_filter)

        # Cache result
        self._user_vector_cache[cache_key] = vector
        self._set_redis_cache(f"uv:{user_id}", vector, ttl_seconds=300)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        if elapsed_ms > 10:
            logger.warning(
                f"User vector query for {user_id} took {elapsed_ms:.1f}ms "
                f"(exceeds 10ms edge budget)"
            )

        return vector

    def get_user_edge_vector(self, user_id: str) -> ConstructVector:
        """Get only edge-tier constructs for real-time scoring (<10ms)."""
        return self.get_user_vector(user_id, tier=InferenceTier.EDGE)

    def get_user_reasoning_vector(self, user_id: str) -> ConstructVector:
        """Get reasoning-tier constructs for Claude context."""
        return self.get_user_vector(user_id, tier=InferenceTier.REASONING_LAYER)

    # -------------------------------------------------------------------------
    # AD/BRAND CONSTRUCT VECTORS
    # -------------------------------------------------------------------------

    def get_ad_vector(
        self,
        asin: str,
        edge_type: EdgeType = EdgeType.BRAND_CONVERTED,
    ) -> ConstructVector:
        """
        Get the ad/brand construct vector for a product.

        For BRAND_CONVERTED: returns ProductDescription annotations (Domains 29-33).
        For PEER_INFLUENCED: returns aggregated review annotations (Domain 34).
        For ECOSYSTEM_CONVERTED: returns ProductEcosystem annotations (Domain 35).
        """
        cache_key = f"ad:{asin}:{edge_type.value}"
        if cache_key in self._ad_vector_cache:
            return self._ad_vector_cache[cache_key]

        vector = self._query_ad_constructs(asin, edge_type)
        self._ad_vector_cache[cache_key] = vector
        return vector

    # -------------------------------------------------------------------------
    # ALIGNMENT SCORING
    # -------------------------------------------------------------------------

    def compute_alignment(
        self,
        user_vector: ConstructVector,
        ad_vector: ConstructVector,
        edge_type: EdgeType = EdgeType.BRAND_CONVERTED,
    ) -> AlignmentResult:
        """
        Compute alignment between user and ad vectors using PREDICTS posteriors.

        This is pure mathematical computation on continuous values.
        No categorical types or dimensions are used.

        For each (user_construct, ad_construct) pair with PREDICTS edges,
        the alignment contribution = user_score * ad_score * posterior_mean.
        """
        start_time = time.monotonic()
        pair_scores: dict[str, float] = {}
        total_score = 0.0
        total_weight = 0.0

        for user_cid, user_score in user_vector.scores.items():
            if user_score == 0.0:
                continue

            for ad_cid, ad_score in ad_vector.scores.items():
                if ad_score == 0.0:
                    continue

                # Get PREDICTS posterior for this pair
                posterior_mean = self._get_predicts_posterior(
                    user_cid, ad_cid, edge_type
                )

                weight = user_score * ad_score
                contribution = weight * posterior_mean
                pair_key = f"{user_cid}|{ad_cid}"
                pair_scores[pair_key] = contribution
                total_score += contribution
                total_weight += weight

        overall = total_score / total_weight if total_weight > 0 else 0.5

        # Sort for top/bottom alignments
        sorted_pairs = sorted(pair_scores.items(), key=lambda x: x[1], reverse=True)
        top_alignments = [
            (p.split("|")[0], p.split("|")[1], s)
            for p, s in sorted_pairs[:10]
        ]
        top_misalignments = [
            (p.split("|")[0], p.split("|")[1], s)
            for p, s in sorted_pairs[-10:]
        ]

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return AlignmentResult(
            overall_score=overall,
            construct_pair_scores=pair_scores,
            top_alignments=top_alignments,
            top_misalignments=top_misalignments,
            mechanism_recommendations=self._derive_mechanism_recommendations(
                user_vector, ad_vector, pair_scores
            ),
            edge_type=edge_type,
            computation_time_ms=elapsed_ms,
        )

    def compute_multi_pathway_alignment(
        self,
        user_vector: ConstructVector,
        brand_vector: ConstructVector,
        peer_vector: Optional[ConstructVector] = None,
        ecosystem_vector: Optional[ConstructVector] = None,
    ) -> dict[str, AlignmentResult]:
        """
        Compute alignment across all three pathways (brand, peer, ecosystem).

        Returns a dict keyed by edge type name.
        """
        results = {}
        results["brand"] = self.compute_alignment(
            user_vector, brand_vector, EdgeType.BRAND_CONVERTED
        )

        if peer_vector and peer_vector.dimensions > 0:
            results["peer"] = self.compute_alignment(
                user_vector, peer_vector, EdgeType.PEER_INFLUENCED
            )

        if ecosystem_vector and ecosystem_vector.dimensions > 0:
            results["ecosystem"] = self.compute_alignment(
                user_vector, ecosystem_vector, EdgeType.ECOSYSTEM_CONVERTED
            )

        return results

    # -------------------------------------------------------------------------
    # ATOM INTERFACE (backward-compatible with PsychologicalConstructResolver)
    # -------------------------------------------------------------------------

    def to_atom_context(self, user_id: str, asin: Optional[str] = None) -> dict[str, Any]:
        """
        Generate the ad_context dict that atoms expect.

        This provides backward compatibility with PsychologicalConstructResolver
        while delivering the new continuous-vector format.
        """
        user_vec = self.get_user_edge_vector(user_id)
        user_reasoning_vec = self.get_user_reasoning_vector(user_id)

        context: dict[str, Any] = {
            # New continuous-vector format
            "construct_vectors": {
                "user_edge": user_vec.scores,
                "user_reasoning": user_reasoning_vec.scores,
                "user_confidences": user_vec.confidences,
            },
            # Backward-compatible fields
            "graph_type_inference": {},
            "expanded_customer_type": {},
            "dimensional_priors": user_vec.scores,
            "ndf_intelligence": {
                "profile": self._derive_ndf_from_vector(user_vec),
            },
            "graph_mechanism_priors": {},
        }

        if asin:
            brand_vec = self.get_ad_vector(asin, EdgeType.BRAND_CONVERTED)
            peer_vec = self.get_ad_vector(asin, EdgeType.PEER_INFLUENCED)
            eco_vec = self.get_ad_vector(asin, EdgeType.ECOSYSTEM_CONVERTED)

            context["construct_vectors"]["brand"] = brand_vec.scores
            context["construct_vectors"]["peer"] = peer_vec.scores
            context["construct_vectors"]["ecosystem"] = eco_vec.scores

            # Compute alignment
            alignment = self.compute_alignment(user_vec, brand_vec)
            context["construct_alignment"] = {
                "overall": alignment.overall_score,
                "mechanism_recommendations": alignment.mechanism_recommendations,
                "top_alignments": alignment.top_alignments[:5],
            }

        return context

    # -------------------------------------------------------------------------
    # INTERNAL QUERIES
    # -------------------------------------------------------------------------

    def _query_user_constructs(
        self,
        user_id: str,
        tier: Optional[InferenceTier],
        domain_filter: Optional[list[str]],
    ) -> ConstructVector:
        """Query Neo4j for a user's construct scores."""
        if self._driver is None:
            return self._get_prior_vector(ScoringSwitch.USER_SIDE, tier, domain_filter)

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (u:User {user_id: $user_id})-[s:HAS_SCORE]->(c:Construct)
                    WHERE ($tier IS NULL OR c.tier = $tier)
                    AND ($domains IS NULL OR c.domain_id IN $domains)
                    RETURN c.id AS construct_id, s.score AS score, s.confidence AS confidence
                    """,
                    user_id=user_id,
                    tier=tier.value if tier else None,
                    domains=domain_filter,
                )
                scores = {}
                confidences = {}
                for record in result:
                    scores[record["construct_id"]] = record["score"]
                    confidences[record["construct_id"]] = record.get("confidence", 0.5)

                if scores:
                    return ConstructVector(
                        scores=scores, confidences=confidences, source="graph"
                    )
        except Exception as e:
            logger.error(f"Neo4j query failed for user {user_id}: {e}")

        # Fall back to priors if no graph data
        return self._get_prior_vector(ScoringSwitch.USER_SIDE, tier, domain_filter)

    def _query_ad_constructs(
        self, asin: str, edge_type: EdgeType
    ) -> ConstructVector:
        """Query Neo4j for ad/brand construct scores."""
        if self._driver is None:
            return self._get_prior_vector(ScoringSwitch.AD_SIDE, None, None)

        node_type, score_rel = {
            EdgeType.BRAND_CONVERTED: ("ProductDescription", "HAS_BRAND_SCORE"),
            EdgeType.PEER_INFLUENCED: ("Review", "HAS_PEER_SCORE"),
            EdgeType.ECOSYSTEM_CONVERTED: ("ProductEcosystem", "HAS_ECO_SCORE"),
        }.get(edge_type, ("ProductDescription", "HAS_BRAND_SCORE"))

        try:
            with self._driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (pd:{node_type} {{asin: $asin}})-[s:{score_rel}]->(c:Construct)
                    RETURN c.id AS construct_id, s.score AS score, s.confidence AS confidence
                    """,
                    asin=asin,
                )
                scores = {}
                confidences = {}
                for record in result:
                    scores[record["construct_id"]] = record["score"]
                    confidences[record["construct_id"]] = record.get("confidence", 0.5)

                if scores:
                    return ConstructVector(
                        scores=scores, confidences=confidences, source="graph"
                    )
        except Exception as e:
            logger.error(f"Neo4j query failed for {node_type} {asin}: {e}")

        return self._get_prior_vector(ScoringSwitch.AD_SIDE, None, None)

    def _get_prior_vector(
        self,
        side: ScoringSwitch,
        tier: Optional[InferenceTier],
        domain_filter: Optional[list[str]],
    ) -> ConstructVector:
        """Generate a prior vector from construct definitions (cold start)."""
        scores = {}
        confidences = {}

        for cid, construct in self._construct_registry.items():
            if construct.scoring_side != side and construct.scoring_side != ScoringSwitch.BOTH:
                continue
            if tier and construct.tier != tier:
                continue
            if domain_filter and construct.domain_id not in domain_filter:
                continue

            # Use the prior distribution to set the default score
            scores[cid] = construct.prior.alpha / (
                construct.prior.alpha + construct.prior.beta
            )
            confidences[cid] = 0.0  # Zero confidence = pure prior

        return ConstructVector(
            scores=scores, confidences=confidences, source="prior"
        )

    def _get_predicts_posterior(
        self,
        user_cid: str,
        ad_cid: str,
        edge_type: EdgeType,
    ) -> float:
        """Get the PREDICTS edge posterior mean for a construct pair."""
        if self._driver is None:
            return 0.5  # Uniform prior

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (uc:Construct {id: $user_cid})-[p:PREDICTS {edge_type: $edge_type}]->(ac:Construct {id: $ad_cid})
                    RETURN p.posterior_mean AS posterior_mean
                    """,
                    user_cid=user_cid,
                    ad_cid=ad_cid,
                    edge_type=edge_type.value,
                )
                record = result.single()
                if record:
                    return record["posterior_mean"]
        except Exception:
            pass

        return 0.5  # Default: uninformative

    def _derive_mechanism_recommendations(
        self,
        user_vector: ConstructVector,
        ad_vector: ConstructVector,
        pair_scores: dict[str, float],
    ) -> dict[str, float]:
        """Derive mechanism recommendations from construct alignment."""
        # This maps top-scoring construct pairs to the mechanisms they connect to
        recommendations: dict[str, float] = {}
        for pair_key, score in sorted(
            pair_scores.items(), key=lambda x: x[1], reverse=True
        )[:20]:
            user_cid = pair_key.split("|")[0]
            construct = self._construct_registry.get(user_cid)
            if construct and construct.mechanism_connections:
                for mechanism in construct.mechanism_connections:
                    if mechanism not in recommendations:
                        recommendations[mechanism] = 0.0
                    recommendations[mechanism] += score

        # Normalize to 0-1
        if recommendations:
            max_val = max(recommendations.values())
            if max_val > 0:
                recommendations = {
                    k: v / max_val for k, v in recommendations.items()
                }

        return recommendations

    def _derive_ndf_from_vector(self, vector: ConstructVector) -> dict[str, float]:
        """Derive NDF-compatible dict from construct vector (backward compat)."""
        return {
            "uncertainty_tolerance": vector.get("risk_tolerance", 0.5),
            "cognitive_engagement": vector.get("dm_nfc", 0.5),
            "approach_avoidance": vector.get("approach_motivation", 0.5),
            "social_calibration": vector.get("ci_social_proof", 0.5),
            "arousal_seeking": vector.get("ss_experience_seeking", 0.5),
            "status_sensitivity": vector.get("evo_status", 0.5),
            "temporal_horizon": vector.get("tp_future", 0.5),
            "cognitive_velocity": (
                vector.get("dm_system1", 0.5) * 0.5
                + vector.get("dm_impulse_cog", 0.5) * 0.5
            ),
        }

    def _check_redis_cache(self, key: str) -> Optional[ConstructVector]:
        """Check Redis for cached vector."""
        if self._redis is None:
            return None
        try:
            import json
            data = self._redis.get(key)
            if data:
                parsed = json.loads(data)
                return ConstructVector(
                    scores=parsed.get("scores", {}),
                    confidences=parsed.get("confidences", {}),
                    source="cache",
                    timestamp=parsed.get("timestamp", 0.0),
                )
        except Exception:
            pass
        return None

    def _set_redis_cache(
        self, key: str, vector: ConstructVector, ttl_seconds: int = 300
    ) -> None:
        """Cache a vector in Redis."""
        if self._redis is None:
            return
        try:
            import json
            data = json.dumps({
                "scores": vector.scores,
                "confidences": vector.confidences,
                "timestamp": vector.timestamp,
            })
            self._redis.setex(key, ttl_seconds, data)
        except Exception:
            pass

    def clear_caches(self) -> None:
        """Clear all in-memory caches."""
        self._user_vector_cache.clear()
        self._ad_vector_cache.clear()


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_service: Optional[GraphConstructService] = None


def get_graph_construct_service(
    neo4j_driver=None,
    redis_client=None,
) -> GraphConstructService:
    """Get or create the singleton GraphConstructService."""
    global _service
    if _service is None:
        _service = GraphConstructService(neo4j_driver, redis_client)
    return _service
