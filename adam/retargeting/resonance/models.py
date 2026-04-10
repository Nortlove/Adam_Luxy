# =============================================================================
# Resonance Engineering — Data Models
# Location: adam/retargeting/resonance/models.py
# =============================================================================

"""
Core data models for the Resonance Engineering system.

PageMindstateVector: 32-dimensional representation of a page's psychological field
ResonanceScore: The computed resonance multiplier for a (buyer, seller, page) triple
ResonanceHypothesis: A testable hypothesis about page × mechanism interaction
ResonanceExperiment: An active experiment testing a hypothesis
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np


# ── The 32 dimensions of a PageMindstateVector ──
# These are in a FIXED ORDER for numpy conversion.

# 20 edge dimensions (same space as bilateral BRAND_CONVERTED edges)
EDGE_DIM_NAMES = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire", "interoceptive_awareness",
    "cooperative_framing_fit", "decision_entropy",
]

# 7 NDF construct activations
NDF_DIM_NAMES = [
    "approach_avoidance", "temporal_horizon", "social_calibration",
    "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
    "arousal_seeking",
]

# 5 environmental scalars
ENV_DIM_NAMES = [
    "emotional_valence", "emotional_arousal", "cognitive_load",
    "publisher_authority", "remaining_bandwidth",
]

ALL_MINDSTATE_DIMS = EDGE_DIM_NAMES + NDF_DIM_NAMES + ENV_DIM_NAMES
MINDSTATE_DIM_COUNT = len(ALL_MINDSTATE_DIMS)  # 32


@dataclass
class PageMindstateVector:
    """32-dimensional representation of a page's psychological field.

    Lives in the same dimensional space as bilateral edges so that
    resonance can be computed as inner products / cosine similarities.

    The 20 edge dimensions are the resonance BRIDGE — they directly
    correspond to the bilateral alignment dimensions on BRAND_CONVERTED edges.
    When a page's edge_dimensions align with a mechanism's optimal field,
    the mechanism is amplified. When they conflict, it's dampened.
    """

    # 20-dim edge dimensions (same space as bilateral edges)
    edge_dimensions: Dict[str, float] = field(default_factory=dict)

    # 7-dim NDF construct activations
    ndf_activations: Dict[str, float] = field(default_factory=dict)

    # Mechanism susceptibility scores (per-mechanism multiplier from NDF sigmoid)
    mechanism_susceptibility: Dict[str, float] = field(default_factory=dict)

    # 5 environmental scalars
    emotional_valence: float = 0.0      # -1 to +1
    emotional_arousal: float = 0.5      # 0-1
    cognitive_load: float = 0.5         # 0-1
    publisher_authority: float = 0.5    # 0-1
    remaining_bandwidth: float = 0.5    # 0-1

    # Metadata
    url_pattern: str = ""
    domain: str = ""
    confidence: float = 0.3
    scoring_tier: str = "unknown"  # full_extraction, taxonomy_category, ndf_fallback, url_heuristic
    timestamp: float = field(default_factory=lambda: __import__('time').time())

    def to_numpy(self) -> np.ndarray:
        """Flatten to 32-dim numpy vector in fixed dimension order."""
        vec = np.zeros(MINDSTATE_DIM_COUNT)

        # Edge dimensions (0-19)
        for i, dim in enumerate(EDGE_DIM_NAMES):
            vec[i] = self.edge_dimensions.get(dim, 0.5)

        # NDF activations (20-26)
        for i, dim in enumerate(NDF_DIM_NAMES):
            vec[20 + i] = self.ndf_activations.get(dim, 0.5)

        # Environmental scalars (27-31)
        vec[27] = self.emotional_valence
        vec[28] = self.emotional_arousal
        vec[29] = self.cognitive_load
        vec[30] = self.publisher_authority
        vec[31] = self.remaining_bandwidth

        return vec

    @classmethod
    def from_numpy(cls, vec: np.ndarray, metadata: Optional[Dict] = None) -> "PageMindstateVector":
        """Reconstruct from numpy vector."""
        metadata = metadata or {}
        edge_dims = {EDGE_DIM_NAMES[i]: float(vec[i]) for i in range(20)}
        ndf_dims = {NDF_DIM_NAMES[i]: float(vec[20 + i]) for i in range(7)}

        return cls(
            edge_dimensions=edge_dims,
            ndf_activations=ndf_dims,
            emotional_valence=float(vec[27]),
            emotional_arousal=float(vec[28]),
            cognitive_load=float(vec[29]),
            publisher_authority=float(vec[30]),
            remaining_bandwidth=float(vec[31]),
            **metadata,
        )

    def cosine_similarity(self, other: "PageMindstateVector") -> float:
        """Compute cosine similarity between two mindstate vectors."""
        a = self.to_numpy()
        b = other.to_numpy()
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


@dataclass
class ResonanceScore:
    """The resonance multiplier for a specific (buyer, seller, page) triple.

    resonance_multiplier > 1.0: page AMPLIFIES the mechanism
    resonance_multiplier = 1.0: page is neutral
    resonance_multiplier < 1.0: page DAMPENS the mechanism
    """

    base_conversion_probability: float
    resonance_multiplier: float  # 0.3 (suppressive) to 3.0 (amplifying)
    effective_probability: float  # base × resonance (clamped to [0, 1])

    # Which page dimensions drove the multiplier
    contributing_dimensions: List[Dict[str, Any]] = field(default_factory=list)

    # Model metadata
    confidence: float = 0.5
    model_stage: str = "A"  # A=theory, B=empirical, C=neural
    model_version: str = "35.0"

    # Mechanism context
    mechanism: str = ""
    barrier: str = ""
    archetype: str = ""


@dataclass
class ResonanceHypothesis:
    """A testable hypothesis about page_mindstate × mechanism interaction.

    Generated by the evolutionary engine (Layer 6) from:
    - Prediction residuals (where the model is wrong)
    - Counterintuitive inversions (test the opposite of theory)
    - Interaction discovery (causal conditional dependencies)
    """

    hypothesis_id: str = field(default_factory=lambda: str(uuid4()))
    hypothesis_type: str = ""  # residual_driven, counterintuitive, interaction_driven, synergy
    statement: str = ""  # Human-readable description

    # The specific prediction
    mechanism: str = ""
    barrier: str = ""
    page_dimension: str = ""
    page_value_range: Tuple[float, float] = (0.0, 1.0)
    predicted_effect: str = ""  # amplifies, suppresses, neutral
    predicted_magnitude: float = 0.0

    # Evidence source
    source: str = ""  # prediction_residual, emergence_detection, causal_discovery, theory_prior
    prior_observations: int = 0
    prior_effect_size: float = 0.0

    # Lifecycle
    status: str = "proposed"  # proposed, testing, validated, rejected, promoted
    created_at: float = field(default_factory=lambda: __import__('time').time())
    impressions_allocated: int = 0
    impressions_observed: int = 0
    observed_effect_size: float = 0.0
    p_value: float = 1.0
    validated_at: Optional[float] = None


@dataclass
class ResonanceExperiment:
    """An active experiment testing a resonance hypothesis.

    Uses sequential analysis with early stopping — doesn't wait for
    fixed sample size. Reuses the ExperimentService infrastructure.
    """

    experiment_id: str = field(default_factory=lambda: str(uuid4()))
    hypothesis_id: str = ""

    # Treatment arms
    control_strategy: str = ""   # Current best placement strategy
    treatment_strategy: str = ""  # Hypothesis-driven placement strategy

    # Allocation
    traffic_fraction: float = 0.05  # 5% of impressions for this cell
    min_observations: int = 50
    max_observations: int = 500

    # Results
    control_conversions: int = 0
    control_impressions: int = 0
    treatment_conversions: int = 0
    treatment_impressions: int = 0

    # Sequential testing
    current_p_value: float = 1.0
    current_effect_size: float = 0.0
    decision: str = "continue"  # continue, stop_winner, stop_futility

    @property
    def control_rate(self) -> float:
        return self.control_conversions / max(self.control_impressions, 1)

    @property
    def treatment_rate(self) -> float:
        return self.treatment_conversions / max(self.treatment_impressions, 1)

    @property
    def lift(self) -> float:
        cr = self.control_rate
        return (self.treatment_rate - cr) / max(cr, 0.001)
