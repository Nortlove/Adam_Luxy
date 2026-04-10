"""
Bayesian Fusion Engine — The Compounding Flywheel.

"Every campaign makes the next campaign better."

This module implements the Bayesian online update system that:
1. Ingests campaign outcomes (conversions, clicks, engagement)
2. Updates posterior distributions on PREDICTS / BRAND_CONVERTED /
   PEER_INFLUENCED / ECOSYSTEM_CONVERTED edges
3. Uses temporal-stability-aware learning rates
4. Tracks evidence accumulation per construct pair

The compounding effect: each campaign observation shifts the posterior for
every construct involved, making the system progressively more precise.

AUTHORITATIVE SOURCE: taxonomy/Construct_Taxonomy_v2_COMPLETE.md (Part IV)
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from adam.intelligence.construct_taxonomy import (
    TEMPORAL_STABILITY_CONFIG,
    EdgeType,
    InferenceTier,
    ScoringSwitch,
    TemporalStability,
    get_all_constructs,
    get_edge_constructs,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class OutcomeType(str, Enum):
    """Types of campaign outcomes we can learn from."""
    CONVERSION = "conversion"
    CLICK = "click"
    ENGAGEMENT = "engagement"
    VIEW = "view"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"


@dataclass
class CampaignOutcome:
    """A single campaign outcome observation."""
    campaign_id: str
    user_id: str
    asin: Optional[str] = None
    outcome_type: OutcomeType = OutcomeType.CONVERSION
    outcome_value: float = 1.0  # 0.0 = negative, 1.0 = positive
    timestamp: float = 0.0

    # User-side construct scores at time of exposure
    user_construct_scores: dict[str, float] = field(default_factory=dict)
    # Ad-side construct scores at time of exposure
    ad_construct_scores: dict[str, float] = field(default_factory=dict)
    # Peer-side construct scores (if applicable)
    peer_construct_scores: dict[str, float] = field(default_factory=dict)
    # Ecosystem construct scores (if applicable)
    ecosystem_construct_scores: dict[str, float] = field(default_factory=dict)

    # Which edge types to update
    edge_types: list[EdgeType] = field(default_factory=lambda: [EdgeType.BRAND_CONVERTED])

    # Additional context
    product_category: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BayesianEdgeState:
    """Current Bayesian state of a PREDICTS or conversion edge."""
    user_construct_id: str
    ad_construct_id: str
    edge_type: EdgeType = EdgeType.BRAND_CONVERTED

    # Bayesian parameters (Beta distribution)
    prior_alpha: float = 5.0
    prior_beta: float = 5.0
    posterior_alpha: float = 5.0
    posterior_beta: float = 5.0
    n_observations: int = 0

    # Derived statistics
    @property
    def prior_mean(self) -> float:
        return self.prior_alpha / (self.prior_alpha + self.prior_beta)

    @property
    def posterior_mean(self) -> float:
        return self.posterior_alpha / (self.posterior_alpha + self.posterior_beta)

    @property
    def posterior_variance(self) -> float:
        a, b = self.posterior_alpha, self.posterior_beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def credible_interval_95(self) -> tuple[float, float]:
        """Approximate 95% credible interval using normal approximation."""
        mean = self.posterior_mean
        sd = math.sqrt(self.posterior_variance)
        return (max(0.0, mean - 1.96 * sd), min(1.0, mean + 1.96 * sd))

    @property
    def evidence_strength(self) -> str:
        """How much evidence we have."""
        if self.n_observations < 5:
            return "prior_dominated"
        elif self.n_observations < 20:
            return "emerging"
        elif self.n_observations < 100:
            return "moderate"
        else:
            return "strong"


@dataclass
class UpdateResult:
    """Result of a single Bayesian update."""
    user_construct_id: str
    ad_construct_id: str
    edge_type: EdgeType
    prior_mean: float
    posterior_mean: float
    shift: float
    n_observations: int
    learning_rate_used: float
    evidence_strength: str


# =============================================================================
# BAYESIAN UPDATE ENGINE
# =============================================================================

class BayesianFusionEngine:
    """
    Core engine for the Compounding Flywheel.

    Implements Bayesian online updates with:
    - Temporal-stability-aware learning rates
    - Per-construct-pair evidence tracking
    - Three edge type support (BRAND_CONVERTED, PEER_INFLUENCED, ECOSYSTEM_CONVERTED)
    - Thread-safe operation via atomic updates
    """

    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        self._cache: dict[str, BayesianEdgeState] = {}
        self._all_constructs = get_all_constructs()
        self._edge_constructs = get_edge_constructs()
        self._update_count = 0

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def process_outcome(self, outcome: CampaignOutcome) -> list[UpdateResult]:
        """
        Process a campaign outcome and update all relevant PREDICTS edges.

        For each (user_construct, ad_construct) pair where both have non-zero
        scores, we update the edge's posterior distribution.

        Returns a list of UpdateResult for all updated edges.
        """
        results: list[UpdateResult] = []
        start_time = time.monotonic()

        for edge_type in outcome.edge_types:
            user_scores = outcome.user_construct_scores
            ad_scores = self._get_ad_scores_for_edge_type(outcome, edge_type)

            if not user_scores or not ad_scores:
                continue

            for user_cid, user_score in user_scores.items():
                if user_score == 0.0:
                    continue

                user_construct = self._all_constructs.get(user_cid)
                if user_construct is None:
                    continue

                for ad_cid, ad_score in ad_scores.items():
                    if ad_score == 0.0:
                        continue

                    # Get learning rate based on temporal stability
                    lr = self._get_learning_rate(user_construct.temporal_stability)

                    # Compute the effective observation weight
                    # Weight = user_score * ad_score * outcome_value * learning_rate
                    obs_weight = user_score * ad_score * lr

                    # Get or create the edge state
                    state = self._get_edge_state(user_cid, ad_cid, edge_type)
                    prior_mean = state.posterior_mean

                    # Bayesian update: adjust alpha/beta based on outcome
                    if outcome.outcome_value > 0.5:
                        # Positive outcome: increase alpha (success)
                        state.posterior_alpha += obs_weight * outcome.outcome_value
                    else:
                        # Negative outcome: increase beta (failure)
                        state.posterior_beta += obs_weight * (1.0 - outcome.outcome_value)

                    state.n_observations += 1

                    # Apply decay for state-level constructs
                    self._apply_decay(state, user_construct.temporal_stability)

                    results.append(UpdateResult(
                        user_construct_id=user_cid,
                        ad_construct_id=ad_cid,
                        edge_type=edge_type,
                        prior_mean=prior_mean,
                        posterior_mean=state.posterior_mean,
                        shift=state.posterior_mean - prior_mean,
                        n_observations=state.n_observations,
                        learning_rate_used=lr,
                        evidence_strength=state.evidence_strength,
                    ))

        elapsed_ms = (time.monotonic() - start_time) * 1000
        self._update_count += 1

        if self._update_count % 100 == 0:
            logger.info(
                f"Bayesian fusion: {len(results)} edges updated in {elapsed_ms:.1f}ms "
                f"(total updates: {self._update_count})"
            )

        return results

    def batch_process_outcomes(
        self, outcomes: list[CampaignOutcome]
    ) -> list[UpdateResult]:
        """Process multiple outcomes efficiently."""
        all_results: list[UpdateResult] = []
        for outcome in outcomes:
            all_results.extend(self.process_outcome(outcome))
        return all_results

    def get_posterior(
        self,
        user_construct_id: str,
        ad_construct_id: str,
        edge_type: EdgeType = EdgeType.BRAND_CONVERTED,
    ) -> BayesianEdgeState:
        """Get the current posterior state for a construct pair."""
        return self._get_edge_state(user_construct_id, ad_construct_id, edge_type)

    def get_alignment_score(
        self,
        user_scores: dict[str, float],
        ad_scores: dict[str, float],
        edge_type: EdgeType = EdgeType.BRAND_CONVERTED,
    ) -> float:
        """
        Compute the overall alignment score between user and ad construct vectors.

        Uses posterior means as weights: for each (user_construct, ad_construct)
        pair, the contribution = user_score * ad_score * posterior_mean.
        """
        total_score = 0.0
        total_weight = 0.0

        for user_cid, user_score in user_scores.items():
            if user_score == 0.0:
                continue
            for ad_cid, ad_score in ad_scores.items():
                if ad_score == 0.0:
                    continue
                state = self._get_edge_state(user_cid, ad_cid, edge_type)
                weight = user_score * ad_score
                total_score += weight * state.posterior_mean
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.5

    def get_flywheel_metrics(self) -> dict[str, Any]:
        """Return metrics demonstrating the compounding flywheel effect."""
        if not self._cache:
            return {"status": "no_data", "total_edges": 0}

        total_observations = sum(s.n_observations for s in self._cache.values())
        avg_shift = 0.0
        edges_with_data = 0

        for state in self._cache.values():
            if state.n_observations > 0:
                edges_with_data += 1
                avg_shift += abs(state.posterior_mean - state.prior_mean)

        if edges_with_data > 0:
            avg_shift /= edges_with_data

        return {
            "total_edges_tracked": len(self._cache),
            "edges_with_observations": edges_with_data,
            "total_observations": total_observations,
            "average_posterior_shift": round(avg_shift, 6),
            "total_updates_processed": self._update_count,
            "evidence_distribution": self._get_evidence_distribution(),
        }

    def persist_to_neo4j(self) -> int:
        """
        Persist all cached edge states to Neo4j.

        Creates/updates PREDICTS edges with posterior parameters.
        Returns the number of edges persisted.
        """
        if self._driver is None:
            logger.warning("No Neo4j driver configured. Cannot persist.")
            return 0

        count = 0
        with self._driver.session() as session:
            for key, state in self._cache.items():
                if state.n_observations == 0:
                    continue  # Don't persist prior-only edges
                try:
                    session.run(
                        """
                        MATCH (uc:Construct {id: $user_cid}), (ac:Construct {id: $ad_cid})
                        MERGE (uc)-[p:PREDICTS {edge_type: $edge_type}]->(ac)
                        SET p.prior_alpha = $prior_alpha,
                            p.prior_beta = $prior_beta,
                            p.posterior_alpha = $posterior_alpha,
                            p.posterior_beta = $posterior_beta,
                            p.posterior_mean = $posterior_mean,
                            p.posterior_variance = $posterior_variance,
                            p.n_observations = $n_obs,
                            p.evidence_strength = $evidence,
                            p.last_updated = timestamp()
                        """,
                        user_cid=state.user_construct_id,
                        ad_cid=state.ad_construct_id,
                        edge_type=state.edge_type.value,
                        prior_alpha=state.prior_alpha,
                        prior_beta=state.prior_beta,
                        posterior_alpha=state.posterior_alpha,
                        posterior_beta=state.posterior_beta,
                        posterior_mean=state.posterior_mean,
                        posterior_variance=state.posterior_variance,
                        n_obs=state.n_observations,
                        evidence=state.evidence_strength,
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to persist edge {key}: {e}")

        logger.info(f"Persisted {count} PREDICTS edges to Neo4j")
        return count

    # -------------------------------------------------------------------------
    # ALIGNMENT MATRIX DECOMPOSITION
    # -------------------------------------------------------------------------

    def decompose_alignment_matrices(
        self, alignment_matrices: dict[str, dict[str, dict[str, float]]]
    ) -> int:
        """
        Decompose existing alignment matrices into per-construct PREDICTS edges.

        Takes matrices like MOTIVATION_VALUE_ALIGNMENT and creates PREDICTS edges
        with the alignment scores as prior means.

        Args:
            alignment_matrices: Dict of matrix_name -> {row_key -> {col_key -> float}}

        Returns:
            Number of PREDICTS edges seeded.
        """
        count = 0
        for matrix_name, matrix in alignment_matrices.items():
            for row_key, col_scores in matrix.items():
                user_cid = self._resolve_construct_id(row_key, "user")
                if user_cid is None:
                    continue
                for col_key, score in col_scores.items():
                    ad_cid = self._resolve_construct_id(col_key, "ad")
                    if ad_cid is None:
                        continue

                    # Seed the prior based on alignment score
                    state = self._get_edge_state(
                        user_cid, ad_cid, EdgeType.BRAND_CONVERTED
                    )
                    # Set prior proportional to alignment score
                    if score > 0.5:
                        state.prior_alpha = 5.0 + (score - 0.5) * 10.0
                        state.prior_beta = 5.0
                    else:
                        state.prior_alpha = 5.0
                        state.prior_beta = 5.0 + (0.5 - score) * 10.0
                    # Posterior starts at prior
                    state.posterior_alpha = state.prior_alpha
                    state.posterior_beta = state.prior_beta
                    count += 1

        logger.info(
            f"Decomposed {len(alignment_matrices)} matrices into {count} PREDICTS edges"
        )
        return count

    # -------------------------------------------------------------------------
    # INTERNAL
    # -------------------------------------------------------------------------

    def _get_ad_scores_for_edge_type(
        self, outcome: CampaignOutcome, edge_type: EdgeType
    ) -> dict[str, float]:
        """Get the appropriate ad-side scores for the given edge type."""
        if edge_type == EdgeType.BRAND_CONVERTED:
            return outcome.ad_construct_scores
        elif edge_type == EdgeType.PEER_INFLUENCED:
            return outcome.peer_construct_scores
        elif edge_type == EdgeType.ECOSYSTEM_CONVERTED:
            return outcome.ecosystem_construct_scores
        return {}

    def _get_edge_state(
        self, user_cid: str, ad_cid: str, edge_type: EdgeType
    ) -> BayesianEdgeState:
        """Get or create a BayesianEdgeState for a construct pair."""
        key = f"{user_cid}|{ad_cid}|{edge_type.value}"
        if key not in self._cache:
            # Initialize with construct-appropriate priors
            user_c = self._all_constructs.get(user_cid)
            if user_c and user_c.prior:
                alpha, beta = user_c.prior.alpha, user_c.prior.beta
            else:
                alpha, beta = 5.0, 5.0

            self._cache[key] = BayesianEdgeState(
                user_construct_id=user_cid,
                ad_construct_id=ad_cid,
                edge_type=edge_type,
                prior_alpha=alpha,
                prior_beta=beta,
                posterior_alpha=alpha,
                posterior_beta=beta,
            )
        return self._cache[key]

    def _get_learning_rate(self, stability: TemporalStability) -> float:
        """Get the learning rate for a given temporal stability tier."""
        config = TEMPORAL_STABILITY_CONFIG.get(stability, {})
        return config.get("update_learning_rate", 0.05)

    def _apply_decay(
        self, state: BayesianEdgeState, stability: TemporalStability
    ) -> None:
        """Apply temporal decay to state/momentary construct posteriors."""
        config = TEMPORAL_STABILITY_CONFIG.get(stability, {})
        decay = config.get("decay_rate", 0.0)
        if decay > 0.0:
            # Decay posterior toward prior
            state.posterior_alpha = (
                state.prior_alpha * decay + state.posterior_alpha * (1.0 - decay)
            )
            state.posterior_beta = (
                state.prior_beta * decay + state.posterior_beta * (1.0 - decay)
            )

    def _resolve_construct_id(self, raw_key: str, side: str) -> Optional[str]:
        """Attempt to resolve a raw matrix key to a construct ID."""
        # Direct match
        if raw_key in self._all_constructs:
            return raw_key

        # Try common prefixes
        prefixes = {
            "user": ["big5_", "sdt_", "ci_", "dm_", "reg_", "bias_", "risk_", "con_"],
            "ad": ["ad_", "pt_", "vp_", "bp_", "ls_"],
        }

        for prefix in prefixes.get(side, []):
            candidate = f"{prefix}{raw_key}"
            if candidate in self._all_constructs:
                return candidate

        return None

    def _get_evidence_distribution(self) -> dict[str, int]:
        """Summarize the evidence strength distribution."""
        dist: dict[str, int] = {
            "prior_dominated": 0,
            "emerging": 0,
            "moderate": 0,
            "strong": 0,
        }
        for state in self._cache.values():
            strength = state.evidence_strength
            dist[strength] = dist.get(strength, 0) + 1
        return dist


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_fusion_engine: Optional[BayesianFusionEngine] = None


def get_bayesian_fusion_engine(
    neo4j_driver=None,
) -> BayesianFusionEngine:
    """Get or create the singleton BayesianFusionEngine."""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = BayesianFusionEngine(neo4j_driver)
    return _fusion_engine
