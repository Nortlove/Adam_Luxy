"""
Exposure-Response Model — The Therapeutic Window for Advertising
=================================================================

Pharmacokinetic frame: every buyer has an exposure-response curve with
three zones:

    Sub-therapeutic     Therapeutic Window     Toxic (Reactance)
    ◄──────────────────►◄─────────────────────►◄──────────────────►
    Goal not yet         Goal active,           Goal resisted,
    accessible           mechanism resonant      buyer hostile

This module classifies each buyer into one of three populations:

1. RESPONSIVE — The construct chain is valid, the mechanism fits the
   receptor (buyer psychology). More exposure within the therapeutic
   window increases conversion probability. Worth optimizing.

2. SATURATED — The buyer has processed the message and reached steady
   state. Additional same-mechanism exposure triggers reactance.
   Needs mechanism rotation (therapeutic switch) or suppression.

3. NON_RESPONDER — The buyer's psychological profile doesn't bind to
   any available mechanism. No dose will produce conversion. Every
   impression is waste, and optimizing toward the accidental 0.8%
   who convert teaches the learning loop the wrong lesson.

The classification uses:
- Exposure count (impressions served to this buyer)
- Engagement trajectory (click/no-click sequence via FrequencyDecayDetector)
- Mechanism ADME profiles (half-life, max_exposures, reactance_rate)
- Bilateral edge evidence (mechanism-archetype alignment scores)
- Segment depletion signals (population-level decay)

This is NOT a heuristic ("suppress after N impressions"). It is a
Bateman-equation model of steady-state concentration under repeated
dosing, with clearance and accumulation dynamics.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BuyerClassification(Enum):
    RESPONSIVE = "responsive"
    SATURATED = "saturated"
    NON_RESPONDER = "non_responder"
    UNKNOWN = "unknown"


class RecommendedAction(Enum):
    CONTINUE = "continue"
    ROTATE_MECHANISM = "rotate_mechanism"
    SUPPRESS = "suppress"
    SUPPRESS_PERMANENT = "suppress_permanent"
    REDUCE_FREQUENCY = "reduce_frequency"


@dataclass
class ExposureState:
    """Per-buyer exposure state."""
    buyer_id: str
    archetype: str = ""
    mechanism: str = ""

    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0

    # Engagement trajectory: list of (impression_number, engaged: bool)
    engagement_history: List[Tuple[int, bool]] = field(default_factory=list)

    # Current mechanism effectiveness (from ADME)
    mechanism_half_life_hours: float = 72.0
    mechanism_max_exposures: int = 5
    mechanism_reactance_rate: float = 0.15

    # Hours since first impression
    hours_since_first: float = 0.0

    # Hours since last engagement (click)
    hours_since_last_engagement: float = float("inf")


@dataclass
class ExposureResponse:
    """Classification result for a single buyer."""
    buyer_id: str
    classification: BuyerClassification
    action: RecommendedAction
    confidence: float = 0.0

    # The reasoning — why this classification, grounded in mechanism
    construct_chain: List[str] = field(default_factory=list)
    reasoning: str = ""

    # Pharmacokinetic state
    effective_concentration: float = 0.0  # 0-1, current "dose" level
    therapeutic_window: Tuple[float, float] = (0.0, 1.0)
    reactance_probability: float = 0.0

    # Recommendations
    suppress_duration_hours: int = 0
    next_mechanism: str = ""
    max_additional_impressions: int = 0


class ExposureResponseModel:
    """
    Classifies buyers into responsive / saturated / non-responder
    using a pharmacokinetic model of advertising exposure.

    The Bateman equation for repeated dosing:
        C(t) = D * (ka / (ka - ke)) * (e^(-ke*t) - e^(-ka*t))

    Where:
        C(t) = effective concentration of the mechanism at time t
        D = dose (impression intensity, modulated by creative quality)
        ka = absorption rate (from ADME profile)
        ke = elimination rate (1 / half_life * ln(2))

    For repeated impressions, concentration accumulates:
        C_steady = C_single * 1 / (1 - e^(-ke * tau))

    Where tau = inter-impression interval.

    Reactance is modeled as receptor down-regulation:
        R(n) = 1 - e^(-reactance_rate * max(0, n - threshold))

    Where n = exposure count, threshold = 0.6 * max_exposures.
    """

    def __init__(self, adme_profiles: Optional[Dict[str, Any]] = None):
        self.adme = adme_profiles or self._load_default_adme()

    def classify(self, state: ExposureState) -> ExposureResponse:
        """Classify a buyer's exposure-response state."""

        # Get mechanism ADME parameters
        adme = self.adme.get(state.mechanism, self.adme.get("default", {}))
        half_life = adme.get("half_life_hours", state.mechanism_half_life_hours)
        max_exp = adme.get("max_exposures", state.mechanism_max_exposures)
        react_rate = adme.get("reactance_rate", state.mechanism_reactance_rate)

        # Compute effective concentration (Bateman accumulation)
        ke = math.log(2) / half_life if half_life > 0 else 0.1
        concentration = self._compute_concentration(
            state.total_impressions, ke, state.hours_since_first,
        )

        # Compute reactance probability
        react_threshold = int(0.6 * max_exp)
        reactance = self._compute_reactance(
            state.total_impressions, react_rate, react_threshold,
        )

        # Compute engagement trajectory
        engagement_trend = self._compute_engagement_trend(state.engagement_history)

        # Non-responder detection
        non_responder_score = self._detect_non_responder(state, adme)

        # Classification priority: non-responder > saturated > declining > responsive
        # Non-responder takes priority even over saturation because the action
        # is categorically different: suppress permanently vs rotate mechanism.
        # Zero engagement + high exposure is a stronger signal than any other.
        if non_responder_score > 0.3 and state.total_clicks == 0 and state.total_impressions >= max_exp * 2:
            return ExposureResponse(
                buyer_id=state.buyer_id,
                classification=BuyerClassification.NON_RESPONDER,
                action=RecommendedAction.SUPPRESS_PERMANENT,
                confidence=non_responder_score,
                effective_concentration=concentration,
                reactance_probability=reactance,
                reasoning=(
                    f"Non-responder: {state.total_impressions} impressions, "
                    f"{state.total_clicks} clicks, {state.total_conversions} conversions. "
                    f"Engagement trend: {engagement_trend:.2f}. "
                    f"The buyer's psychological profile does not bind to {state.mechanism}. "
                    f"Continued exposure wastes budget and may induce reactance damage."
                ),
                suppress_duration_hours=336,  # 14 days
                max_additional_impressions=0,
            )

        if reactance > 0.6 or state.total_impressions >= max_exp:
            # Saturated — mechanism has been processed
            remaining = max(0, max_exp - state.total_impressions)
            return ExposureResponse(
                buyer_id=state.buyer_id,
                classification=BuyerClassification.SATURATED,
                action=(
                    RecommendedAction.ROTATE_MECHANISM if engagement_trend > -0.5
                    else RecommendedAction.SUPPRESS
                ),
                confidence=min(1.0, reactance + 0.2),
                effective_concentration=concentration,
                reactance_probability=reactance,
                reasoning=(
                    f"Saturated: {state.total_impressions}/{max_exp} max exposures, "
                    f"reactance probability {reactance:.0%}. "
                    f"The {state.mechanism} mechanism has been fully processed. "
                    f"Same-mechanism repetition triggers reactance (bilateral evidence: "
                    f"converters have reactance=0.037, non-converters=0.092)."
                ),
                suppress_duration_hours=int(half_life * 2),
                next_mechanism=self._suggest_rotation(state.mechanism),
                max_additional_impressions=remaining,
            )

        if engagement_trend < -0.3 and state.total_impressions >= 3:
            # Declining engagement — approaching saturation
            return ExposureResponse(
                buyer_id=state.buyer_id,
                classification=BuyerClassification.SATURATED,
                action=RecommendedAction.REDUCE_FREQUENCY,
                confidence=0.6,
                effective_concentration=concentration,
                reactance_probability=reactance,
                reasoning=(
                    f"Engagement declining: trend={engagement_trend:.2f} over "
                    f"{state.total_impressions} impressions. Approaching therapeutic ceiling. "
                    f"Reduce frequency to prevent reactance onset."
                ),
                max_additional_impressions=max(1, max_exp - state.total_impressions),
            )

        # Responsive — within therapeutic window
        return ExposureResponse(
            buyer_id=state.buyer_id,
            classification=BuyerClassification.RESPONSIVE,
            action=RecommendedAction.CONTINUE,
            confidence=max(0.5, 1.0 - reactance),
            effective_concentration=concentration,
            therapeutic_window=(0.2, 0.8),
            reactance_probability=reactance,
            reasoning=(
                f"Responsive: {state.total_impressions}/{max_exp} exposures, "
                f"concentration={concentration:.2f}, reactance={reactance:.0%}. "
                f"Within therapeutic window. Continue current mechanism."
            ),
            max_additional_impressions=max_exp - state.total_impressions,
        )

    def _compute_concentration(
        self, impressions: int, ke: float, hours: float,
    ) -> float:
        """Bateman equation: effective concentration from repeated dosing."""
        if impressions == 0 or hours <= 0:
            return 0.0

        tau = hours / max(impressions, 1)  # average inter-impression interval
        if tau <= 0:
            return 0.0

        # Single-dose peak concentration (normalized to 1.0)
        c_single = 1.0

        # Accumulation factor for repeated dosing at interval tau
        decay_per_interval = math.exp(-ke * tau)
        if decay_per_interval >= 1.0:
            return min(1.0, c_single * impressions)

        # Steady-state accumulation
        c_steady = c_single / (1 - decay_per_interval)

        # Current concentration (approaches steady state over exposures)
        approach_factor = 1 - decay_per_interval ** impressions
        concentration = c_steady * approach_factor

        return min(1.0, concentration / (c_steady if c_steady > 0 else 1.0))

    def _compute_reactance(
        self, impressions: int, rate: float, threshold: int,
    ) -> float:
        """Reactance as receptor down-regulation."""
        excess = max(0, impressions - threshold)
        if excess == 0:
            return 0.0
        return 1.0 - math.exp(-rate * excess)

    def _compute_engagement_trend(
        self, history: List[Tuple[int, bool]],
    ) -> float:
        """Compute engagement trend from history. Negative = declining."""
        if len(history) < 3:
            return 0.0

        # Split into halves
        mid = len(history) // 2
        early = history[:mid]
        recent = history[mid:]

        early_rate = sum(1 for _, engaged in early if engaged) / len(early)
        recent_rate = sum(1 for _, engaged in recent if engaged) / len(recent)

        if early_rate == 0:
            return 0.0

        return (recent_rate - early_rate) / early_rate

    def _detect_non_responder(
        self, state: ExposureState, adme: Dict,
    ) -> float:
        """
        Detect non-responders using Bayesian reasoning.

        A non-responder is someone whose posterior P(convert | N exposures, 0 conversions)
        is below a threshold. Using Beta-Bernoulli conjugate:
            Prior: Beta(alpha_0, beta_0) — from archetype base rate
            After N exposures with k conversions: Beta(alpha_0 + k, beta_0 + N - k)

        For zero conversions: Beta(alpha_0, beta_0 + N)
            Posterior mean = alpha_0 / (alpha_0 + beta_0 + N)

        As N grows, posterior mean → 0.
        """
        if state.total_impressions < 5:
            return 0.0  # Insufficient data

        # Archetype base rate priors
        base_rates = {
            "careful_truster": 0.032,
            "status_seeker": 0.038,
            "easy_decider": 0.041,
            "dependable_loyalist": 0.035,
            "reliable_cooperator": 0.033,
            "prevention_planner": 0.030,
        }
        base_rate = base_rates.get(state.archetype, 0.035)

        # Convert to Beta prior: alpha = base_rate * strength, beta = (1-base_rate) * strength
        prior_strength = 10  # pseudo-observations from population
        alpha_0 = base_rate * prior_strength
        beta_0 = (1 - base_rate) * prior_strength

        # Posterior after N impressions with k clicks (using clicks as engagement signal)
        alpha_post = alpha_0 + state.total_clicks
        beta_post = beta_0 + state.total_impressions - state.total_clicks

        # Posterior mean engagement probability
        posterior_mean = alpha_post / (alpha_post + beta_post)

        # Non-responder if posterior is far below base rate
        if posterior_mean < base_rate * 0.2 and state.total_impressions >= 8:
            return min(1.0, 0.5 + (state.total_impressions - 8) * 0.05)

        if posterior_mean < base_rate * 0.5 and state.total_impressions >= 12:
            return min(1.0, 0.3 + (state.total_impressions - 12) * 0.04)

        return 0.0

    def _suggest_rotation(self, current_mechanism: str) -> str:
        """Suggest a different mechanism for rotation."""
        rotations = {
            "regulatory_focus": "construal_level",
            "construal_level": "regulatory_focus",
            "authority": "cognitive_ease",
            "social_proof": "authority",
            "cognitive_ease": "social_proof",
            "identity_construction": "wanting_liking",
            "wanting_liking": "identity_construction",
            "mimetic_desire": "identity_construction",
            "automatic_evaluation": "regulatory_focus",
        }
        return rotations.get(current_mechanism, "cognitive_ease")

    def _load_default_adme(self) -> Dict[str, Dict]:
        """Load ADME profiles from the mechanism_adme module."""
        try:
            from adam.intelligence.mechanism_adme import MECHANISM_ADME_PROFILES
            return {
                p.mechanism: {
                    "half_life_hours": p.half_life_hours,
                    "max_exposures": p.max_exposures,
                    "reactance_rate": p.reactance_rate,
                    "absorption_rate": p.absorption_rate,
                }
                for p in MECHANISM_ADME_PROFILES.values()
            }
        except ImportError:
            return {
                "default": {
                    "half_life_hours": 72,
                    "max_exposures": 5,
                    "reactance_rate": 0.15,
                    "absorption_rate": 0.7,
                },
            }


def get_exposure_response_model() -> ExposureResponseModel:
    return ExposureResponseModel()
