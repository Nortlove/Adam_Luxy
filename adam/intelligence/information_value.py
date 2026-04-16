"""
Psychological Information Value Bidding
========================================

The most powerful capability in the INFORMATIV system.

Standard bidding: Bid = P(convert) × revenue
Our bidding:      Bid = P(convert) × revenue + information_value

Where information_value = P(signal) × Δ(model_accuracy) × PV(future_impressions)

Every impression that results in ANY behavioral signal (conversion, click,
bounce, dwell time) updates the buyer's psychological profile. That update
has a dollar value because it makes every future impression more accurate.

For a buyer seen twice (wide confidence intervals on all constructs),
the information value is large — we should bid materially above what
pure conversion probability justifies because winning this impression
teaches us things that make future impressions worth significantly more.

For a buyer with 40+ dimensional measurements, information value
approaches zero — bid purely on conversion probability.

This is Bayesian Optimal Experiment Design applied to programmatic bidding.
Nobody else can do this because nobody else has a probabilistic psychological
profile model with calibrated uncertainty on continuous alignment dimensions.

The gradient fields are a direct input: constructs with the highest gradient
magnitude × widest buyer uncertainty = highest information value impressions.
The system becomes more accurate faster than any competitor, not despite the
bids that don't convert, but because of them.

Implementation
--------------
Per-buyer construct uncertainty: Beta(α, β) per alignment dimension.
Expected information gain: KL divergence reduction from one more observation.
Present value of future impressions: session frequency × expected lifetime.
Bid modifier: information_value / baseline_cpm → additive bid adjustment.
"""

from __future__ import annotations

import logging
import math

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observability metrics
# ---------------------------------------------------------------------------
class _IVMetrics:
    """Lightweight metrics for information value computations.

    Tracks distributions of bid premiums, buyer profiles, and computation
    counts without requiring Prometheus (uses simple counters exportable
    via the /metrics endpoint).
    """

    def __init__(self):
        self.computations_total: int = 0
        self.profiles_created: int = 0
        self.profiles_updated: int = 0
        self._premium_sum: float = 0.0
        self._premium_count: int = 0
        self._premium_max: float = 0.0
        self._priority_counts: Dict[str, int] = {
            "none": 0, "low": 0, "medium": 0, "high": 0, "critical": 0,
        }

    def record_computation(self, result: "InformationValueResult") -> None:
        self.computations_total += 1
        premium = result.recommended_bid_premium
        self._premium_sum += premium
        self._premium_count += 1
        self._premium_max = max(self._premium_max, premium)
        self._priority_counts[result.exploration_priority] = (
            self._priority_counts.get(result.exploration_priority, 0) + 1
        )

    def record_profile_created(self) -> None:
        self.profiles_created += 1

    def record_profile_updated(self) -> None:
        self.profiles_updated += 1

    def summary(self) -> Dict[str, Any]:
        avg = self._premium_sum / self._premium_count if self._premium_count else 0.0
        return {
            "iv_computations_total": self.computations_total,
            "iv_avg_bid_premium": round(avg, 4),
            "iv_max_bid_premium": round(self._premium_max, 4),
            "iv_profiles_created": self.profiles_created,
            "iv_profiles_updated": self.profiles_updated,
            "iv_priority_distribution": dict(self._priority_counts),
        }


iv_metrics = _IVMetrics()


# ---------------------------------------------------------------------------
# Per-buyer construct uncertainty profile
# ---------------------------------------------------------------------------

# The alignment dimensions we track uncertainty on.
# Core 7 match the gradient field / BRAND_CONVERTED edge dimensions.
# Extended dimensions capture richer psychological signal from intelligence modules.
UNCERTAINTY_DIMENSIONS = [
    # --- Core edge dimensions (from BRAND_CONVERTED edges) ---
    "regulatory_fit",
    "construal_fit",
    "personality_alignment",
    "emotional_resonance",
    "value_alignment",
    "evolutionary_motive",
    "linguistic_style",
    # --- Extended dimensions (from intelligence modules) ---
    "persuasion_susceptibility",     # per-mechanism receptivity (persuasion_susceptibility.py)
    "cognitive_load_tolerance",      # information processing capacity (cognitive_load.py)
    "narrative_transport",           # story immersion tendency (narrative_identity.py)
    "social_proof_sensitivity",      # herd behavior tendency (signal_credibility.py)
    "loss_aversion_intensity",       # prospect theory asymmetry (regret_anticipation.py)
    "temporal_discounting",          # present vs future bias (temporal_self.py)
    "brand_relationship_depth",      # parasocial brand attachment (relationship_intelligence.py)
    "autonomy_reactance",           # resistance to persuasion pressure (autonomy_reactance.py)
    "information_seeking",          # active vs passive consumption (information_asymmetry.py)
    "mimetic_desire",               # social imitation tendency (mimetic_desire_atom.py)
    "interoceptive_awareness",      # body-signal driven decisions (interoceptive_style.py)
    "cooperative_framing_fit",      # fairness/reciprocity orientation (cooperative_framing.py)
    "decision_entropy",             # choice difficulty/paralysis (decision_entropy.py)
]

# Default prior: Beta(2, 2) = uniform-ish, high uncertainty
DEFAULT_ALPHA = 2.0
DEFAULT_BETA = 2.0

# ---------------------------------------------------------------------------
# Archetype-informed dimension priors
# ---------------------------------------------------------------------------
# Each archetype has theoretical expectations on certain dimensions.
# Tighter priors (higher alpha+beta, skewed mean) = we "already know"
# something about this dimension for this type of buyer.
# Wider priors (close to 2,2) = archetype tells us little.
#
# Format: dimension -> (alpha, beta)
#   Beta(4,2) ≈ mean 0.67, moderate confidence (we expect high alignment)
#   Beta(2,4) ≈ mean 0.33, moderate confidence (we expect low alignment)
#   Beta(3,3) ≈ mean 0.50, slightly tighter than default
#   Beta(2,2) = default (omitted, filled automatically)
# ---------------------------------------------------------------------------
_ARCHETYPE_DIMENSION_PRIORS_FALLBACK: Dict[str, Dict[str, Tuple[float, float]]] = {
    "achiever": {
        "regulatory_fit": (5, 2),
        "personality_alignment": (4, 2),
        "value_alignment": (4, 2),
        "construal_fit": (3, 2),
        "temporal_discounting": (2, 4),
        "loss_aversion_intensity": (3, 3),
        "narrative_transport": (2, 2),
        "cooperative_framing_fit": (2, 2),
    },
    "explorer": {
        "narrative_transport": (5, 2),
        "information_seeking": (5, 2),
        "emotional_resonance": (4, 2),
        "construal_fit": (3, 2),
        "mimetic_desire": (2, 3),
        "autonomy_reactance": (4, 2),
    },
    "connector": {
        "social_proof_sensitivity": (5, 2),
        "cooperative_framing_fit": (4, 2),
        "mimetic_desire": (4, 2),
        "brand_relationship_depth": (4, 2),
        "emotional_resonance": (3, 2),
        "autonomy_reactance": (2, 4),
    },
    "guardian": {
        "loss_aversion_intensity": (5, 2),
        "regulatory_fit": (2, 4),
        "autonomy_reactance": (3, 2),
        "cognitive_load_tolerance": (2, 3),
        "decision_entropy": (4, 2),
        "temporal_discounting": (2, 4),
    },
    "analyst": {
        "cognitive_load_tolerance": (5, 2),
        "information_seeking": (5, 2),
        "construal_fit": (3, 2),
        "social_proof_sensitivity": (2, 4),
        "mimetic_desire": (2, 4),
        "emotional_resonance": (2, 3),
    },
    "creator": {
        "narrative_transport": (5, 2),
        "emotional_resonance": (4, 2),
        "autonomy_reactance": (4, 2),
        "interoceptive_awareness": (3, 2),
        "mimetic_desire": (2, 3),
    },
    "nurturer": {
        "cooperative_framing_fit": (5, 2),
        "social_proof_sensitivity": (4, 2),
        "brand_relationship_depth": (4, 2),
        "emotional_resonance": (4, 2),
        "autonomy_reactance": (2, 4),
        "loss_aversion_intensity": (3, 2),
    },
    "pragmatist": {
        "regulatory_fit": (3, 3),
        "construal_fit": (3, 3),
        "personality_alignment": (3, 3),
        "value_alignment": (3, 3),
        "cognitive_load_tolerance": (3, 2),
    },
}

# Mutable reference — replaced by load_graph_dimension_priors() at startup
_ARCHETYPE_DIMENSION_PRIORS: Dict[str, Dict[str, Tuple[float, float]]] = dict(
    _ARCHETYPE_DIMENSION_PRIORS_FALLBACK
)
_DIMENSION_PRIORS_SOURCE: str = "hardcoded_fallback"


async def load_graph_dimension_priors(neo4j_driver=None) -> bool:
    """
    Replace hardcoded archetype dimension priors with empirical values
    from BayesianPrior nodes in Neo4j.

    Called once at server startup. Returns True if graph priors loaded.
    Falls back to hardcoded values silently if graph unavailable.

    BayesianPrior nodes store per-(archetype, dimension) Beta parameters
    derived from actual BRAND_CONVERTED edge statistics.
    """
    global _ARCHETYPE_DIMENSION_PRIORS, _DIMENSION_PRIORS_SOURCE

    driver = neo4j_driver
    if driver is None:
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if client.is_connected:
                driver = client.driver
        except Exception:
            pass

    if driver is None:
        logger.info("Graph unavailable — using hardcoded dimension priors")
        return False

    try:
        async with driver.session() as session:
            result = await session.run("""
                MATCH (bp:BayesianPrior)
                WHERE bp.archetype IS NOT NULL
                  AND bp.dimension IS NOT NULL
                  AND bp.alpha IS NOT NULL
                  AND bp.beta IS NOT NULL
                RETURN bp.archetype AS archetype,
                       bp.dimension AS dimension,
                       bp.alpha AS alpha,
                       bp.beta AS beta,
                       bp.observation_count AS obs
                ORDER BY bp.archetype
            """)
            records = await result.data()

        if not records:
            logger.info("No BayesianPrior nodes found — using hardcoded dimension priors")
            return False

        graph_priors: Dict[str, Dict[str, Tuple[float, float]]] = {}
        for rec in records:
            arch = rec["archetype"]
            dim = rec["dimension"]
            alpha = float(rec["alpha"])
            beta = float(rec["beta"])
            if arch not in graph_priors:
                graph_priors[arch] = {}
            graph_priors[arch][dim] = (alpha, beta)

        if graph_priors:
            # Merge: graph priors override, fallback fills gaps
            for arch, fallback_dims in _ARCHETYPE_DIMENSION_PRIORS_FALLBACK.items():
                if arch not in graph_priors:
                    graph_priors[arch] = dict(fallback_dims)
                else:
                    for dim, val in fallback_dims.items():
                        if dim not in graph_priors[arch]:
                            graph_priors[arch][dim] = val

            _ARCHETYPE_DIMENSION_PRIORS = graph_priors
            _DIMENSION_PRIORS_SOURCE = "neo4j_bayesian_prior"
            logger.info(
                "Loaded graph-backed dimension priors: %d archetypes, %d dimension entries",
                len(graph_priors),
                sum(len(v) for v in graph_priors.values()),
            )
            return True

    except Exception as e:
        logger.warning("Failed to load graph dimension priors: %s", e)

    return False


@dataclass
class ConstructPosterior:
    """Beta posterior for a single alignment dimension of a buyer.

    The posterior represents our belief about where this buyer sits
    on this dimension (0.0 = low alignment, 1.0 = high alignment).

    Uncertainty = variance of the Beta distribution.
    As we observe more signals, α and β grow, variance shrinks,
    and our profile of this buyer becomes more precise.
    """
    alpha: float = DEFAULT_ALPHA
    beta: float = DEFAULT_BETA

    @property
    def mean(self) -> float:
        """Expected value of the construct for this buyer."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Uncertainty: how spread out our belief is."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    @property
    def observations(self) -> int:
        """Effective number of observations (pseudo-count minus prior)."""
        return max(0, int(self.alpha + self.beta) - int(DEFAULT_ALPHA + DEFAULT_BETA))

    @property
    def confidence(self) -> float:
        """Confidence in our estimate (0.0 = no idea, 1.0 = certain)."""
        # At default prior (2,2): confidence ≈ 0.17
        # At (10, 10): confidence ≈ 0.83
        # At (50, 50): confidence ≈ 0.98
        return 1.0 - min(1.0, 4.0 * self.variance)

    def update(self, observed_value: float, weight: float = 1.0) -> None:
        """Bayesian update with a new observation.

        observed_value: 0.0-1.0, the alignment dimension value from
                        this interaction's BRAND_CONVERTED edge.
        weight: signal strength (conversion=1.0, click=0.3, impression=0.1).
        """
        # Treat observed_value as probability of "success" on this dimension
        self.alpha += observed_value * weight
        self.beta += (1.0 - observed_value) * weight

    def expected_variance_after_observation(self) -> float:
        """Expected posterior variance if we observe one more signal.

        This is the key computation for information value:
        how much does one more observation reduce our uncertainty?

        For Beta(α, β), one observation moves us to approximately
        Beta(α+0.5, β+0.5) on average, so:
        E[Var_posterior] ≈ Var(Beta(α+0.5, β+0.5))
        """
        a = self.alpha + 0.5
        b = self.beta + 0.5
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    def expected_information_gain(self) -> float:
        """Expected KL divergence reduction from one more observation.

        ΔI ≈ current_variance - expected_posterior_variance

        This is proportional to how much we learn from one more signal.
        High when uncertainty is high (early observations teach a lot).
        Low when uncertainty is low (marginal observation teaches little).
        """
        return self.variance - self.expected_variance_after_observation()


@dataclass
class BuyerUncertaintyProfile:
    """Complete uncertainty profile for a buyer across all constructs.

    This is the per-buyer state that enables information value bidding.
    It tracks how certain we are about each alignment dimension for
    this specific buyer.

    Dual representation:
    - `constructs` dict: Independent Beta posteriors per dimension (legacy, backward-compat)
    - `bong_posterior`: Multivariate Gaussian capturing cross-dimension correlations (BONG)

    When BONG is initialized (population priors loaded from Neo4j data), the
    `update_from_edge()` method updates BOTH representations. The `constructs`
    dict continues to serve code that reads per-dimension stats. The BONG
    posterior enables correlated updates and joint information value computation.

    Storage: ~160 bytes (legacy Betas) + ~344 bytes (BONG) = ~504 bytes per buyer.
    For 1M buyers: ~504 MB. Still trivially cacheable.
    """
    # Per-construct posteriors (legacy, backward-compat)
    constructs: Dict[str, ConstructPosterior] = field(default_factory=dict)

    # BONG multivariate Gaussian posterior (captures cross-dimension correlations)
    bong_posterior: Any = field(default=None)

    # Buyer metadata
    buyer_id: str = ""
    total_interactions: int = 0
    total_conversions: int = 0
    last_updated_ts: float = 0.0

    def __post_init__(self):
        # Initialize all dimensions with default priors if not provided
        for dim in UNCERTAINTY_DIMENSIONS:
            if dim not in self.constructs:
                self.constructs[dim] = ConstructPosterior()

        # Initialize BONG posterior if updater available
        if self.bong_posterior is None:
            try:
                from adam.intelligence.bong import get_bong_updater
                updater = get_bong_updater()
                self.bong_posterior = updater.create_individual()
            except Exception:
                pass  # BONG not available — legacy Betas only

    @property
    def aggregate_uncertainty(self) -> float:
        """Average uncertainty across all dimensions.

        Uses BONG entropy when available (captures cross-dimension correlations).
        Falls back to average per-dimension Beta variance.
        """
        if self.bong_posterior is not None:
            try:
                from adam.intelligence.bong import get_bong_updater
                return get_bong_updater().information_value(self.bong_posterior)
            except Exception:
                pass
        if not self.constructs:
            return 1.0
        return sum(c.variance for c in self.constructs.values()) / len(self.constructs)

    @property
    def aggregate_confidence(self) -> float:
        """Average confidence across all dimensions."""
        if not self.constructs:
            return 0.0
        return sum(c.confidence for c in self.constructs.values()) / len(self.constructs)

    @property
    def total_information_gain_available(self) -> float:
        """Total expected information gain from one more observation."""
        return sum(c.expected_information_gain() for c in self.constructs.values())

    def update_from_edge(
        self,
        edge_dimensions: Dict[str, float],
        signal_type: str = "conversion",
        processing_depth_weight: float = 1.0,
    ) -> Dict[str, float]:
        """Update buyer profile from an observed edge (conversion, click, etc.).

        Args:
            edge_dimensions: Alignment dimension values from BRAND_CONVERTED edge
                             or inferred from behavioral signal.
            signal_type: "conversion" (weight=1.0), "click" (0.3),
                         "impression" (0.1), "bounce" (0.05).
            processing_depth_weight: Enhancement #34 processing depth weight
                (0.05-1.0). Scales the signal_type weight so unprocessed
                impressions produce minimal posterior shift.

        Returns:
            Dict of variance reduction per dimension (how much we learned).
        """
        weight_map = {
            "conversion": 1.0,
            "click": 0.3,
            "engagement": 0.2,
            "impression": 0.1,
            "bounce": 0.05,
        }
        weight = weight_map.get(signal_type, 0.1) * processing_depth_weight

        variance_deltas = {}
        for dim, posterior in self.constructs.items():
            if dim in edge_dimensions:
                old_var = posterior.variance
                posterior.update(edge_dimensions[dim], weight=weight)
                variance_deltas[dim] = old_var - posterior.variance

        # Update BONG posterior (correlated multivariate update)
        if self.bong_posterior is not None:
            try:
                from adam.intelligence.bong import get_bong_updater
                updater = get_bong_updater()
                # Build observation vector aligned to BONG dimension order
                obs = np.array([
                    edge_dimensions.get(dim, 0.5)
                    for dim in updater.dimension_names
                ])
                # Build mask for dimensions actually observed
                mask = np.array([
                    dim in edge_dimensions
                    for dim in updater.dimension_names
                ], dtype=float)
                updater.update(
                    self.bong_posterior,
                    observation=obs,
                    noise_precision=weight,
                    observed_mask=mask if mask.sum() < len(mask) else None,
                )
                # Track BONG update for promotion criteria (Phase B wiring)
                try:
                    from adam.intelligence.bong_promotion import get_promotion_tracker
                    get_promotion_tracker().record_update(self.buyer_id)
                except Exception:
                    pass
            except Exception:
                pass  # BONG update failed — legacy Betas still updated above

        self.total_interactions += 1
        if signal_type == "conversion":
            self.total_conversions += 1

        return variance_deltas

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage (Redis, Neo4j, etc.)."""
        data = {
            "buyer_id": self.buyer_id,
            "total_interactions": self.total_interactions,
            "total_conversions": self.total_conversions,
            "constructs": {
                dim: {"alpha": p.alpha, "beta": p.beta}
                for dim, p in self.constructs.items()
            },
        }
        # Include BONG posterior if available
        if self.bong_posterior is not None:
            try:
                from adam.intelligence.bong import get_bong_updater
                import base64
                raw = get_bong_updater().serialize(self.bong_posterior)
                data["bong_posterior_b64"] = base64.b64encode(raw).decode("ascii")
            except Exception:
                pass
        return data

    @classmethod
    def from_archetype_priors(
        cls,
        archetype: str,
        buyer_id: str = "",
    ) -> BuyerUncertaintyProfile:
        """Create a profile with archetype-informed dimension priors.

        Instead of uniform Beta(2,2) on every dimension, each archetype
        starts with tighter priors on dimensions where we have strong
        theoretical expectations from personality research, and wider
        priors where the archetype gives us little guidance.

        This accelerates learning: we spend fewer impressions confirming
        what the archetype already tells us and more impressions
        resolving genuine uncertainty.

        Supported archetypes: achiever, explorer, connector, guardian,
        analyst, creator, nurturer, pragmatist.  Unknown archetypes
        fall back to uniform Beta(2,2).
        """
        # Lazy import to avoid circular dependency
        try:
            from adam.cold_start.service import ColdStartService
            priors = ColdStartService.get_dimension_priors_for_archetype(archetype)
        except (ImportError, AttributeError):
            priors = _ARCHETYPE_DIMENSION_PRIORS.get(archetype.lower(), {})

        constructs = {}
        for dim in UNCERTAINTY_DIMENSIONS:
            if dim in priors:
                a, b = priors[dim]
                constructs[dim] = ConstructPosterior(alpha=a, beta=b)
            else:
                constructs[dim] = ConstructPosterior()

        return cls(
            buyer_id=buyer_id,
            constructs=constructs,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuyerUncertaintyProfile:
        """Deserialize from storage."""
        constructs = {}
        for dim, params in data.get("constructs", {}).items():
            constructs[dim] = ConstructPosterior(
                alpha=params.get("alpha", DEFAULT_ALPHA),
                beta=params.get("beta", DEFAULT_BETA),
            )

        # Restore BONG posterior if serialized
        bong_posterior = None
        bong_b64 = data.get("bong_posterior_b64")
        if bong_b64:
            try:
                import base64
                from adam.intelligence.bong import get_bong_updater
                raw = base64.b64decode(bong_b64)
                bong_posterior = get_bong_updater().deserialize(raw)
            except Exception:
                pass  # BONG deserialization failed — will re-initialize in __post_init__

        return cls(
            buyer_id=data.get("buyer_id", ""),
            total_interactions=data.get("total_interactions", 0),
            total_conversions=data.get("total_conversions", 0),
            constructs=constructs,
            bong_posterior=bong_posterior,
        )


# ---------------------------------------------------------------------------
# Information Value computation
# ---------------------------------------------------------------------------

@dataclass
class InformationValueResult:
    """The output of information value computation.

    This tells the bid engine: how much extra should we bid for this
    impression because of what it will teach us?
    """
    # Core information value (in the same units as conversion value)
    information_value: float = 0.0

    # Components
    expected_info_gain: float = 0.0          # Δ(model_accuracy) in bits
    gradient_weighted_gain: float = 0.0      # info gain weighted by gradient magnitude
    present_value_future: float = 0.0        # PV(future impressions for this buyer)

    # Bid adjustment
    bid_modifier_pct: float = 0.0            # % to add to base bid
    recommended_bid_premium: float = 0.0     # Dollar amount to add to CPM

    # Per-dimension breakdown
    dimension_values: Dict[str, float] = field(default_factory=dict)

    # Enhancement #36: Within-subject mechanism exploration value
    # When a retargeting user has tried only 1 mechanism, we need more touches
    # to build within-user contrasts. This adds bid premium for those users.
    within_subject_power_value: float = 0.0   # Additional IV from mechanism exploration need
    mechanisms_tried: int = 0                  # How many distinct mechanisms this user has tried
    mechanism_power: float = 0.0              # Statistical power of within-user mechanism comparison

    # Buyer state
    buyer_confidence: float = 0.0
    buyer_interactions: int = 0
    exploration_priority: str = "none"       # none | low | medium | high | critical

    # Reasoning
    reasoning: List[str] = field(default_factory=list)


def _get_iv_settings():
    """Load information value settings, with fallback defaults."""
    try:
        from adam.config.settings import get_settings
        return get_settings().information_value
    except Exception:
        return None


def compute_information_value(
    buyer: BuyerUncertaintyProfile,
    gradient_field: Optional[Any] = None,
    base_cpm: float = 3.50,
    avg_session_frequency: float = 2.5,
    expected_buyer_lifetime_days: float = 90.0,
    discount_rate: float = 0.05,
) -> InformationValueResult:
    """Compute the information value of showing one more impression to this buyer.

    This is the core of Psychological Information Value Bidding.

    Bid = P(convert) × revenue + information_value
    information_value = P(signal) × Δ(accuracy) × PV(future_impressions)

    Args:
        buyer: Current uncertainty profile for this buyer.
        gradient_field: Pre-computed gradient for this (archetype, category) cell.
                       Used to weight information gain by dimension importance.
        base_cpm: Baseline CPM for this segment (from CPM_FLOOR_TABLE).
        avg_session_frequency: Average sessions per week for this buyer type.
        expected_buyer_lifetime_days: Expected remaining buyer lifetime.
        discount_rate: Weekly discount rate for future impression value.

    Returns:
        InformationValueResult with bid adjustment and reasoning.
    """
    # Load configurable parameters from settings (if available)
    iv_settings = _get_iv_settings()

    result = InformationValueResult(
        buyer_confidence=buyer.aggregate_confidence,
        buyer_interactions=buyer.total_interactions,
    )

    # --- Step 1: Expected information gain ---
    # Use BONG joint entropy when available (captures dimension correlations).
    # Fall back to sum of per-dimension Beta information gains.
    dimension_gains = {}
    bong_entropy_gain = 0.0
    use_bong = False

    if buyer.bong_posterior is not None:
        try:
            from adam.intelligence.bong import get_bong_updater
            updater = get_bong_updater()
            # BONG information gain: entropy reduction from a hypothetical observation
            # This accounts for correlations — observing trust tells us about emotion
            obs_placeholder = np.full(len(updater.dimension_names), 0.5)
            bong_entropy_gain = updater.information_gain(
                buyer.bong_posterior, obs_placeholder, noise_precision=1.0,
            )
            # Still compute per-dimension gains for gradient weighting
            for dim, posterior in buyer.constructs.items():
                dimension_gains[dim] = posterior.expected_information_gain()
            use_bong = True
        except Exception:
            pass

    if not use_bong:
        for dim, posterior in buyer.constructs.items():
            eig = posterior.expected_information_gain()
            dimension_gains[dim] = eig

    total_eig = bong_entropy_gain if use_bong else sum(dimension_gains.values())
    result.expected_info_gain = total_eig

    if use_bong:
        result.reasoning.append(
            f"BONG joint entropy gain: {bong_entropy_gain:.4f} bits "
            f"(captures cross-dimension correlations)"
        )

    if total_eig < 1e-6:
        result.reasoning.append(
            f"Buyer well-characterized ({buyer.total_interactions} interactions, "
            f"confidence={buyer.aggregate_confidence:.2f}). Information value ≈ 0."
        )
        result.exploration_priority = "none"
        return result

    # --- Step 2: Weight by gradient magnitude (which dimensions matter?) ---
    if gradient_field and hasattr(gradient_field, "gradients"):
        gradient_weighted = 0.0
        for dim, eig in dimension_gains.items():
            grad_magnitude = abs(gradient_field.gradients.get(dim, 0.0))
            weighted = eig * grad_magnitude
            gradient_weighted += weighted
            result.dimension_values[dim] = round(weighted, 6)

        result.gradient_weighted_gain = gradient_weighted

        if gradient_weighted > 0:
            # Find the dimension where learning × gradient is highest
            top_dim = max(result.dimension_values.items(), key=lambda x: x[1])
            result.reasoning.append(
                f"Highest value learning: {top_dim[0]} "
                f"(gradient={gradient_field.gradients.get(top_dim[0], 0):.3f} × "
                f"uncertainty_reduction={dimension_gains.get(top_dim[0], 0):.4f})"
            )
    else:
        # Without gradient, weight all dimensions equally
        gradient_weighted = total_eig
        result.gradient_weighted_gain = gradient_weighted
        for dim, eig in dimension_gains.items():
            result.dimension_values[dim] = round(eig, 6)

    # --- Step 3: Present value of future impressions ---
    # How many future impressions will benefit from what we learn now?
    weeks_remaining = expected_buyer_lifetime_days / 7.0
    impressions_per_week = avg_session_frequency

    # Discounted sum of future impressions × base_cpm
    pv = 0.0
    for week in range(int(weeks_remaining)):
        pv += impressions_per_week * base_cpm / 1000.0 / (1.0 + discount_rate) ** week

    result.present_value_future = round(pv, 4)

    # --- Step 3b: Within-subject mechanism exploration value (Enhancement #36) ---
    # When a user is in a retargeting sequence and has tried fewer than 2
    # mechanisms, there's additional information value from testing a new
    # mechanism — it enables within-subject paired comparisons that are
    # 2-4x more powerful than between-subjects for understanding this person.
    within_subject_value = 0.0
    if hasattr(buyer, '_within_subject_meta'):
        ws_meta = buyer._within_subject_meta
        mechanisms_tried = ws_meta.get("mechanisms_tried", 0)
        mechanism_power = ws_meta.get("mechanism_power", 0.0)
        result.mechanisms_tried = mechanisms_tried
        result.mechanism_power = mechanism_power

        if mechanisms_tried < 2:
            # High value: no within-user contrast possible yet
            within_subject_value = gradient_weighted * 2.0  # 2x multiplier
            result.reasoning.append(
                f"Within-subject exploration: user has tried {mechanisms_tried} "
                f"mechanism(s) — no paired comparison possible. "
                f"Additional IV: ${within_subject_value:.4f}"
            )
        elif mechanism_power < 0.80:
            # Medium value: have contrast but insufficient power
            power_deficit = 0.80 - mechanism_power
            within_subject_value = gradient_weighted * power_deficit * 2.0
            result.reasoning.append(
                f"Within-subject power deficit: power={mechanism_power:.2f} "
                f"(target 0.80). Additional IV: ${within_subject_value:.4f}"
            )

    result.within_subject_power_value = round(within_subject_value, 4)

    # --- Step 4: Information value = gain × present_value ---
    # Scale: gradient_weighted_gain is in variance-reduction units (small numbers)
    # Multiply by PV to get dollar value, with a scaling factor
    # that maps variance reduction to accuracy improvement.
    #
    # Calibration: the factor is normalized by dimension count so that a new
    # buyer's raw premium ≈ base_cpm regardless of how many dimensions we track.
    # With 7 dims: factor=5.0. With 20 dims: factor≈1.75. With N dims: factor=35/N.
    # This ensures the premium drops meaningfully with each interaction rather
    # than sitting at the cap for the first 10+ observations.
    base_factor = iv_settings.accuracy_to_lift_factor if iv_settings else 5.0
    n_dims = len(buyer.constructs) or 1
    # More dimensions = more potential information gain = higher value.
    # Use sqrt scaling: diminishing returns but still increasing with dimensions.
    # Previously divided by n_dims (penalized more dims by 65%) — backwards.
    import math
    accuracy_to_lift_factor = base_factor * math.sqrt(n_dims / 7.0)
    info_value = gradient_weighted * accuracy_to_lift_factor * pv

    # Enhancement #36: Add within-subject mechanism exploration premium
    info_value += within_subject_value * accuracy_to_lift_factor * pv

    result.information_value = round(info_value, 4)

    # --- Step 5: Bid modifier ---
    if base_cpm > 0:
        result.bid_modifier_pct = round(100.0 * info_value / (base_cpm / 1000.0), 2) if base_cpm > 0 else 0.0
        result.recommended_bid_premium = round(info_value * 1000.0, 2)  # Convert to CPM

    # --- Step 6: Exploration priority classification ---
    critical_thresh = iv_settings.critical_interaction_threshold if iv_settings else 2
    high_thresh = iv_settings.high_interaction_threshold if iv_settings else 5
    medium_conf = iv_settings.medium_confidence_threshold if iv_settings else 0.5
    low_conf = iv_settings.low_confidence_threshold if iv_settings else 0.8

    if buyer.total_interactions <= critical_thresh:
        result.exploration_priority = "critical"
    elif buyer.total_interactions <= high_thresh:
        result.exploration_priority = "high"
    elif buyer.aggregate_confidence < medium_conf:
        result.exploration_priority = "medium"
    elif buyer.aggregate_confidence < low_conf:
        result.exploration_priority = "low"
    else:
        result.exploration_priority = "none"

    # Cap bid modifier (configurable, default 100% = don't bid more than 2x)
    max_premium_pct = iv_settings.max_bid_premium_pct if iv_settings else 100.0
    result.bid_modifier_pct = min(max_premium_pct, result.bid_modifier_pct)
    result.recommended_bid_premium = min(base_cpm * max_premium_pct / 100.0, result.recommended_bid_premium)

    result.reasoning.append(
        f"Buyer interactions={buyer.total_interactions}, "
        f"confidence={buyer.aggregate_confidence:.2f}, "
        f"info_gain={total_eig:.4f}, "
        f"gradient_weighted={gradient_weighted:.4f}, "
        f"PV_future=${pv:.2f}, "
        f"info_value=${info_value:.4f}, "
        f"bid_premium=${result.recommended_bid_premium:.2f}/CPM, "
        f"exploration={result.exploration_priority}"
    )

    # Record observability metrics
    iv_metrics.record_computation(result)

    return result


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

def compute_bid_with_information_value(
    base_bid_cpm: float,
    conversion_probability: float,
    expected_revenue: float,
    buyer: BuyerUncertaintyProfile,
    gradient_field: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute the full INFORMATIV bid for a single impression.

    Returns the total bid and its decomposition.

    Total Bid = conversion_value + information_value
    Where:
        conversion_value = P(convert) × revenue
        information_value = P(signal) × Δ(accuracy) × PV(future)
    """
    # Conversion component (what everyone computes)
    conversion_value = conversion_probability * expected_revenue

    # Information component (what only we can compute)
    iv_result = compute_information_value(
        buyer=buyer,
        gradient_field=gradient_field,
        base_cpm=base_bid_cpm,
    )

    total_bid_cpm = base_bid_cpm + iv_result.recommended_bid_premium

    return {
        "total_bid_cpm": round(total_bid_cpm, 2),
        "base_bid_cpm": base_bid_cpm,
        "conversion_component_cpm": base_bid_cpm,
        "information_component_cpm": iv_result.recommended_bid_premium,
        "bid_premium_pct": iv_result.bid_modifier_pct,
        "exploration_priority": iv_result.exploration_priority,
        "buyer_confidence": iv_result.buyer_confidence,
        "buyer_interactions": iv_result.buyer_interactions,
        "top_learning_dimensions": dict(
            sorted(iv_result.dimension_values.items(), key=lambda x: x[1], reverse=True)[:3]
        ),
        "reasoning": iv_result.reasoning,
    }
