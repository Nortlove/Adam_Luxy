# =============================================================================
# Enriched Intervention Record
# Location: adam/retargeting/models/intervention_record.py
# Unified System Evolution Directive, Section 2.1
# =============================================================================

"""
Captures the full inferential content of each retargeting touch —
not just the binary outcome, but the REASONING that led to the touch,
what was deployed, what was observed, what the system inferred, and
what it plans to do next.

This is what separates this system from every regression-based approach.
Each record is a diagnostic event, not a data point.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnrichedInterventionRecord:
    """One touch in a retargeting sequence with full diagnostic content.

    Captures: reasoning → deployment → observation → inference → plan.
    Used by: causal discovery, counterfactual learning, theory validation.
    """

    # ── Identity ──
    user_id: str
    sequence_id: str
    touch_number: int
    timestamp: float = field(default_factory=time.time)
    campaign_id: str = ""

    # ── What was the REASONING that led to this touch? ──
    barrier_diagnosed: str = ""
    barrier_gap: float = 0.0
    propagated_lift_estimate: float = 0.0
    secondary_dimensions_targeted: Dict[str, float] = field(default_factory=dict)
    diagnostic_hypothesis_from_prior_touch: str = "first_touch"
    why_this_mechanism: str = ""

    # ── What was deployed? ──
    mechanism_id: str = ""
    creative_direction: Dict[str, Any] = field(default_factory=dict)
    page_cluster_prescribed: str = ""
    page_cluster_actual: str = ""
    page_mindstate_vector: List[float] = field(default_factory=list)

    # ── Thompson Sampling state at decision time ──
    mechanism_probabilities: Dict[str, float] = field(default_factory=dict)
    bong_posterior_mean: List[float] = field(default_factory=list)
    bong_posterior_entropy: float = 0.0

    # ── What was OBSERVED? ──
    outcome: str = ""
    converted: bool = False

    # ── Processing depth (Enhancement #34, Signal 4) ──
    processing_depth: str = ""              # ProcessingDepth enum value
    processing_depth_weight: float = 1.0    # Power posterior weight (0.05-1.0)
    viewability_seconds: float = 0.0        # Raw viewport time

    # ── Nonconscious Signal Intelligence (Enhancement #34, all signals) ──
    nonconscious_h_modifiers: Dict[str, float] = field(default_factory=dict)
    click_latency_trajectory: str = ""       # Signal 1
    self_reported_barrier: str = ""          # Signal 2
    barrier_override_active: bool = False    # Signal 2
    organic_stage: str = ""                  # Signal 3
    device_mechanism_mismatch: bool = False  # Signal 5
    reactance_detected: bool = False         # Signal 6
    mechanism_override: str = ""             # Composite recommendation

    # ── What did the system INFER from the outcome? ──
    diagnostic_hypotheses: Dict[str, float] = field(default_factory=dict)
    primary_hypothesis: str = ""

    # Pre and post state (from BONG)
    pre_state: List[float] = field(default_factory=list)
    post_state: List[float] = field(default_factory=list)
    shifted_dimensions: List[str] = field(default_factory=list)
    shift_magnitudes: Dict[str, float] = field(default_factory=dict)

    # Resonance outcome
    predicted_resonance: float = 0.0
    actual_engagement: float = 0.0
    resonance_error: float = 0.0

    # Trajectory impact
    trajectory_before: str = ""
    trajectory_after: str = ""

    # ── What is the system's PLAN for the next touch? ──
    next_touch_plan: Dict[str, Any] = field(default_factory=dict)
    sequence_narrative_position: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "user_id": self.user_id,
            "sequence_id": self.sequence_id,
            "touch_number": self.touch_number,
            "timestamp": self.timestamp,
            "campaign_id": self.campaign_id,
            "barrier_diagnosed": self.barrier_diagnosed,
            "barrier_gap": self.barrier_gap,
            "propagated_lift_estimate": self.propagated_lift_estimate,
            "secondary_dimensions_targeted": self.secondary_dimensions_targeted,
            "diagnostic_hypothesis_from_prior_touch": self.diagnostic_hypothesis_from_prior_touch,
            "why_this_mechanism": self.why_this_mechanism,
            "mechanism_id": self.mechanism_id,
            "creative_direction": self.creative_direction,
            "page_cluster_prescribed": self.page_cluster_prescribed,
            "page_cluster_actual": self.page_cluster_actual,
            "mechanism_probabilities": self.mechanism_probabilities,
            "bong_posterior_entropy": self.bong_posterior_entropy,
            "outcome": self.outcome,
            "converted": self.converted,
            "processing_depth": self.processing_depth,
            "processing_depth_weight": self.processing_depth_weight,
            "viewability_seconds": self.viewability_seconds,
            "nonconscious_h_modifiers": self.nonconscious_h_modifiers,
            "click_latency_trajectory": self.click_latency_trajectory,
            "self_reported_barrier": self.self_reported_barrier,
            "barrier_override_active": self.barrier_override_active,
            "organic_stage": self.organic_stage,
            "device_mechanism_mismatch": self.device_mechanism_mismatch,
            "reactance_detected": self.reactance_detected,
            "mechanism_override": self.mechanism_override,
            "diagnostic_hypotheses": self.diagnostic_hypotheses,
            "primary_hypothesis": self.primary_hypothesis,
            "shifted_dimensions": self.shifted_dimensions,
            "shift_magnitudes": self.shift_magnitudes,
            "predicted_resonance": self.predicted_resonance,
            "actual_engagement": self.actual_engagement,
            "resonance_error": self.resonance_error,
            "trajectory_before": self.trajectory_before,
            "trajectory_after": self.trajectory_after,
            "next_touch_plan": self.next_touch_plan,
            "sequence_narrative_position": self.sequence_narrative_position,
        }
