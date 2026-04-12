# =============================================================================
# Per-Person Puzzle Solver
# Location: adam/retargeting/engines/puzzle_solver.py
# =============================================================================

"""
Treats each person as a unique experiment to solve with maximum efficiency.

Core principle: every touch serves two simultaneous purposes:
  1. Move toward conversion (exploitation)
  2. Learn about this person's psychology (exploration)

The system maintains a Bayesian BELIEF STATE over each person's
psychological profile and uses it to select touches that maximize
the JOINT objective of conversion × learning × minimal reactance.

Theoretical foundations:
  - Attachment Theory (Bowlby/Ainsworth): communication style matching
  - Somatic Marker Hypothesis (Damasio): feeling-based barriers
  - Prediction Error (Friston): attention capture through calibrated surprise
  - Optimal Foraging (Charnov): when to let go
  - Hyperbolic Discounting (Laibson): temporal framing shifts
  - Evolutionary Psychology: survival motives as root drivers

Each person has:
  - A belief state (probability distributions, not point estimates)
  - A conversion distance estimate (touches remaining ± uncertainty)
  - A reactance budget (how much more they can tolerate)
  - An optimal next move (mechanism + prediction error gradient + rationale)
"""

import logging
import math
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# BELIEF STATE
# =============================================================================

@dataclass
class AttachmentBelief:
    """Probability distribution over attachment patterns."""
    anxious: float = 0.33    # Seeks reassurance, fears unreliability
    secure: float = 0.34     # Confident, responds to affirmation
    avoidant: float = 0.33   # Wants efficiency, avoids emotional engagement

    def dominant(self) -> str:
        m = max(self.anxious, self.secure, self.avoidant)
        if m == self.anxious: return "anxious"
        if m == self.secure: return "secure"
        return "avoidant"

    def entropy(self) -> float:
        """Shannon entropy — higher = more uncertain about attachment."""
        h = 0.0
        for p in [self.anxious, self.secure, self.avoidant]:
            if p > 0.001:
                h -= p * math.log2(p)
        return h


@dataclass
class EvolutionaryMotiveBelief:
    """Probability distribution over dominant evolutionary motives."""
    self_protection: float = 0.35   # Threat detection, safety-seeking
    status_signaling: float = 0.30  # Mate competition, hierarchy positioning
    energy_conservation: float = 0.20  # Cognitive miserliness, efficiency
    affiliation: float = 0.15       # Belonging, social bonding

    def dominant(self) -> str:
        vals = {
            "self_protection": self.self_protection,
            "status_signaling": self.status_signaling,
            "energy_conservation": self.energy_conservation,
            "affiliation": self.affiliation,
        }
        return max(vals, key=vals.get)


@dataclass
class SomaticState:
    """Somatic marker valence — the body's accumulated feeling about the product."""
    negative_markers: float = 0.5    # Past bad experiences (0=none, 1=strong)
    positive_markers: float = 0.1    # Vicarious positive experiences formed
    resolution_progress: float = 0.0 # How much negative has been overwritten (0-1)

    @property
    def net_valence(self) -> float:
        """Net somatic valence: positive - (negative × (1 - resolution))."""
        remaining_negative = self.negative_markers * (1.0 - self.resolution_progress)
        return self.positive_markers - remaining_negative


@dataclass
class BeliefState:
    """Complete psychological belief state for one person.

    Maintained as probability distributions, not point estimates.
    Updated after every session via Bayesian inference from behavioral signals.
    """
    # Attachment pattern (Bowlby/Ainsworth)
    attachment: AttachmentBelief = field(default_factory=AttachmentBelief)

    # Evolutionary motive (Buss, Kenrick)
    motive: EvolutionaryMotiveBelief = field(default_factory=EvolutionaryMotiveBelief)

    # Somatic markers (Damasio)
    somatic: SomaticState = field(default_factory=SomaticState)

    # Need for Cognition (Cacioppo & Petty)
    need_for_cognition: float = 0.5  # 0=heuristic processor, 1=deep analytical

    # Construal level progression (Trope & Liberman)
    construal_abstract_to_concrete: float = 0.3  # 0=fully abstract, 1=concrete/actionable

    # Prediction error state (Friston)
    pe_accumulated: float = 0.0        # How much their model has been challenged
    pe_tolerance: float = 0.5          # How much challenge they can handle (0-1)

    # Conversion distance
    estimated_touches_remaining: float = 4.0
    distance_uncertainty: float = 2.0  # ± this many touches

    # Reactance budget
    reactance_used: float = 0.0        # 0-1, how much tolerance consumed
    reactance_rate: float = 0.05       # Per-touch reactance accumulation

    # Confidence in the overall belief state
    observation_count: int = 0
    last_updated: float = field(default_factory=time.time)

    def entropy(self) -> float:
        """Overall belief entropy — how uncertain we are about this person."""
        return (
            self.attachment.entropy() * 0.4
            + (1.0 - abs(self.need_for_cognition - 0.5) * 2) * 0.2  # Max entropy at 0.5
            + self.distance_uncertainty / 4.0 * 0.2
            + (1.0 - min(self.observation_count / 5.0, 1.0)) * 0.2  # Decreases with data
        )

    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# BAYESIAN UPDATER — Updates belief state from behavioral signals
# =============================================================================

class BeliefUpdater:
    """Updates a person's belief state from observed behavioral signals.

    Each session provides evidence that shifts the probability distributions.
    The update rules encode psychological theory, not statistical correlations.
    """

    def update_from_session(
        self,
        belief: BeliefState,
        session_data: Dict,
    ) -> BeliefState:
        """Update belief state from a telemetry session.

        Args:
            belief: Current belief state
            session_data: Signal profile or session payload data

        Returns:
            Updated belief state
        """
        belief.observation_count += 1
        belief.last_updated = time.time()

        # Learning rate decreases as we accumulate more observations
        lr = 1.0 / (1.0 + belief.observation_count * 0.3)

        # ── Attachment pattern update ──

        section_dwell = session_data.get("section_dwell_totals", {})
        safety_dwell = section_dwell.get("section-safety", 0) + section_dwell.get("section-reviews", 0)
        aspirational_dwell = section_dwell.get("section-fleet", 0)
        action_dwell = section_dwell.get("section-booking", 0) + section_dwell.get("section-pricing", 0)
        total_dwell = safety_dwell + aspirational_dwell + action_dwell + 0.01

        if total_dwell > 5.0:
            safety_ratio = safety_dwell / total_dwell
            action_ratio = action_dwell / total_dwell

            # Safety/review focus → anxious attachment evidence
            belief.attachment.anxious += lr * safety_ratio * 0.3
            # Quick action focus → avoidant attachment evidence
            belief.attachment.avoidant += lr * action_ratio * 0.2
            # Balanced browsing → secure attachment evidence
            if safety_ratio < 0.4 and action_ratio < 0.4:
                belief.attachment.secure += lr * 0.15

            # Normalize
            total_att = belief.attachment.anxious + belief.attachment.secure + belief.attachment.avoidant
            if total_att > 0:
                belief.attachment.anxious /= total_att
                belief.attachment.secure /= total_att
                belief.attachment.avoidant /= total_att

        # ── Evolutionary motive update ──

        if safety_dwell > 10:
            belief.motive.self_protection += lr * 0.15
        if aspirational_dwell > 10:
            belief.motive.status_signaling += lr * 0.15
        if action_dwell > 10 and total_dwell < 30:
            belief.motive.energy_conservation += lr * 0.15

        # Normalize motives
        total_mot = (belief.motive.self_protection + belief.motive.status_signaling
                     + belief.motive.energy_conservation + belief.motive.affiliation)
        if total_mot > 0:
            belief.motive.self_protection /= total_mot
            belief.motive.status_signaling /= total_mot
            belief.motive.energy_conservation /= total_mot
            belief.motive.affiliation /= total_mot

        # ── Need for Cognition update ──

        pages_visited = session_data.get("total_page_views", len(session_data.get("pages_visited", [])))
        scroll_depth = session_data.get("scroll_metrics", {}).get("max_depth_pct", 0)

        if pages_visited >= 3 and total_dwell > 30:
            belief.need_for_cognition += lr * 0.1  # Deep engagement = high NFC
        elif pages_visited <= 1 and total_dwell < 15:
            belief.need_for_cognition -= lr * 0.1  # Quick scan = low NFC
        belief.need_for_cognition = max(0.05, min(0.95, belief.need_for_cognition))

        # ── Somatic state update ──

        # Testimonial/review engagement builds positive somatic markers
        testimonial_dwell = section_dwell.get("section-testimonials", 0) + section_dwell.get("section-reviews", 0)
        if testimonial_dwell > 5:
            belief.somatic.positive_markers += lr * min(0.15, testimonial_dwell / 100)
            belief.somatic.resolution_progress += lr * min(0.1, testimonial_dwell / 150)

        # Organic return = internal motivation forming = somatic shift
        is_organic = session_data.get("organic_sessions", 0) > 0 or session_data.get("referral_type") == "direct"
        if is_organic and session_data.get("is_return_visit"):
            belief.somatic.positive_markers += lr * 0.15
            belief.somatic.resolution_progress += lr * 0.10

        belief.somatic.positive_markers = min(1.0, belief.somatic.positive_markers)
        belief.somatic.resolution_progress = min(1.0, belief.somatic.resolution_progress)

        # ── Construal progression ──

        # Booking page engagement = getting concrete
        if action_dwell > 10:
            belief.construal_abstract_to_concrete += lr * 0.15
        belief.construal_abstract_to_concrete = min(0.95, belief.construal_abstract_to_concrete)

        # ── Prediction error state ──

        # Each ad-attributed session means they engaged with a creative
        is_ad = session_data.get("ad_attributed_sessions", 0) > 0 or session_data.get("sapid")
        if is_ad:
            belief.pe_accumulated += lr * 0.1
            # If they came back after seeing an ad, their PE tolerance is adequate
            if session_data.get("is_return_visit"):
                belief.pe_tolerance = min(0.9, belief.pe_tolerance + lr * 0.1)

        # ── Reactance update ──

        if is_ad:
            belief.reactance_used += belief.reactance_rate
            # Adjust rate based on behavior
            if is_organic:
                belief.reactance_rate *= 0.8  # Organic returns reduce reactance rate
            belief.reactance_used = min(1.0, belief.reactance_used)

        # ── Conversion distance update ──

        # As they progress through stages, distance decreases
        if belief.construal_abstract_to_concrete > 0.6:
            belief.estimated_touches_remaining -= lr * 0.5
        if belief.somatic.net_valence > 0:
            belief.estimated_touches_remaining -= lr * 0.3
        if is_organic:
            belief.estimated_touches_remaining -= lr * 0.8

        belief.estimated_touches_remaining = max(0.5, belief.estimated_touches_remaining)
        belief.distance_uncertainty = max(0.5, belief.distance_uncertainty - lr * 0.3)

        return belief

    def update_from_conversion(self, belief: BeliefState) -> BeliefState:
        """Update when conversion occurs — puzzle solved."""
        belief.estimated_touches_remaining = 0.0
        belief.distance_uncertainty = 0.0
        belief.somatic.resolution_progress = 1.0
        belief.construal_abstract_to_concrete = 1.0
        return belief


# =============================================================================
# DIAGNOSTIC TOUCH SELECTOR
# =============================================================================

# Mechanism → psychological properties
MECHANISM_PROPERTIES = {
    "social_proof_matched": {
        "attachment_fit": {"anxious": 0.8, "secure": 0.6, "avoidant": 0.3},
        "pe_gradient": 0.2,       # Low surprise — confirming
        "somatic_effect": 0.15,   # Builds positive markers through vicarious experience
        "nfc_requirement": 0.3,   # Works for low-NFC (peripheral route)
        "reactance_cost": 0.02,   # Low — feels organic
        "construal_target": 0.3,  # Abstract (aspirational social context)
    },
    "evidence_proof": {
        "attachment_fit": {"anxious": 0.9, "secure": 0.5, "avoidant": 0.2},
        "pe_gradient": 0.4,       # Moderate — challenges assumptions with data
        "somatic_effect": 0.08,   # Mild — data doesn't create strong feelings
        "nfc_requirement": 0.7,   # Needs analytical processing
        "reactance_cost": 0.03,   # Low-moderate
        "construal_target": 0.5,  # Mid-level (specific but not action-demanding)
    },
    "narrative_transportation": {
        "attachment_fit": {"anxious": 0.5, "secure": 0.9, "avoidant": 0.2},
        "pe_gradient": 0.3,       # Moderate — disrupts through story
        "somatic_effect": 0.25,   # High — stories create somatic markers
        "nfc_requirement": 0.4,   # Works for medium NFC
        "reactance_cost": 0.02,   # Low — doesn't feel like advertising
        "construal_target": 0.4,  # Mid-abstract (aspirational narrative)
    },
    "loss_framing": {
        "attachment_fit": {"anxious": 0.3, "secure": 0.5, "avoidant": 0.8},
        "pe_gradient": 0.6,       # High — directly challenges status quo
        "somatic_effect": 0.20,   # Moderate-high — activates loss aversion feeling
        "nfc_requirement": 0.3,   # Works viscerally
        "reactance_cost": 0.08,   # Higher — feels pushy
        "construal_target": 0.6,  # More concrete (loss is specific)
    },
    "implementation_intention": {
        "attachment_fit": {"anxious": 0.3, "secure": 0.6, "avoidant": 0.9},
        "pe_gradient": 0.7,       # High — assumes decision is made
        "somatic_effect": 0.10,   # Low — action-focused, not feeling-focused
        "nfc_requirement": 0.2,   # Minimal processing required
        "reactance_cost": 0.06,   # Moderate — presumes intent
        "construal_target": 0.9,  # Very concrete (specific action)
    },
    "ownership_reactivation": {
        "attachment_fit": {"anxious": 0.4, "secure": 0.7, "avoidant": 0.8},
        "pe_gradient": 0.5,       # Moderate — reframes what they already have
        "somatic_effect": 0.18,   # Endowment effect is a feeling
        "nfc_requirement": 0.3,   # Works heuristically
        "reactance_cost": 0.05,   # Moderate
        "construal_target": 0.8,  # Concrete (your specific reservation)
    },
    "micro_commitment": {
        "attachment_fit": {"anxious": 0.5, "secure": 0.5, "avoidant": 0.9},
        "pe_gradient": 0.3,       # Low — asks for very little
        "somatic_effect": 0.12,   # Creates endowment through small action
        "nfc_requirement": 0.2,   # Minimal
        "reactance_cost": 0.02,   # Very low — non-threatening ask
        "construal_target": 0.7,  # Fairly concrete (specific small action)
    },
    "anxiety_resolution": {
        "attachment_fit": {"anxious": 0.95, "secure": 0.3, "avoidant": 0.2},
        "pe_gradient": 0.2,       # Low — soothing, not challenging
        "somatic_effect": 0.22,   # Directly targets negative somatic markers
        "nfc_requirement": 0.5,   # Moderate — needs to process the reassurance
        "reactance_cost": 0.01,   # Very low — feels supportive
        "construal_target": 0.4,  # Mid (safety is somewhat abstract)
    },
    "claude_argument": {
        "attachment_fit": {"anxious": 0.6, "secure": 0.7, "avoidant": 0.3},
        "pe_gradient": 0.5,       # Moderate-high — structured argument
        "somatic_effect": 0.10,   # Low — intellectual, not visceral
        "nfc_requirement": 0.8,   # High — needs careful processing
        "reactance_cost": 0.04,   # Moderate
        "construal_target": 0.6,  # Mid-concrete
    },
    "autonomy_restoration": {
        "attachment_fit": {"anxious": 0.3, "secure": 0.5, "avoidant": 0.7},
        "pe_gradient": 0.1,       # Very low — validating, not challenging
        "somatic_effect": 0.15,   # Relief from perceived pressure
        "nfc_requirement": 0.3,   # Low
        "reactance_cost": -0.10,  # NEGATIVE — reduces reactance
        "construal_target": 0.3,  # Abstract (autonomy is a principle)
    },
}

# Optimal stopping threshold
RELEASE_THRESHOLD = 0.02  # Below this net value → release to dormant


@dataclass
class TouchRecommendation:
    """A recommended next touch with full reasoning."""
    mechanism: str
    net_value: float
    conversion_probability: float
    information_gain: float
    reactance_cost: float
    pe_gradient: float
    rationale: str
    if_click_prediction: str
    if_no_click_prediction: str
    should_release: bool = False
    release_reason: str = ""


class DiagnosticTouchSelector:
    """Selects the optimal next touch for a person given their belief state.

    Maximizes: α × conversion + β × information - γ × reactance

    Where:
    - conversion = probability this touch leads to conversion
    - information = entropy reduction in belief state
    - reactance = how much this touch depletes the reactance budget
    """

    def __init__(
        self,
        alpha: float = 0.5,   # Weight on conversion
        beta: float = 0.35,   # Weight on information gain
        gamma: float = 0.15,  # Weight on reactance avoidance
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def select(
        self,
        belief: BeliefState,
        candidate_mechanisms: Optional[List[str]] = None,
    ) -> TouchRecommendation:
        """Select the optimal next touch.

        Returns the mechanism with highest net value, or recommends
        releasing the person if all mechanisms have negative net value.
        """
        if candidate_mechanisms is None:
            candidate_mechanisms = list(MECHANISM_PROPERTIES.keys())

        best = None
        best_value = -999.0

        for mech in candidate_mechanisms:
            props = MECHANISM_PROPERTIES.get(mech)
            if not props:
                continue

            # Conversion probability
            conv_prob = self._estimate_conversion(belief, mech, props)

            # Information gain (entropy reduction)
            info_gain = self._estimate_information_gain(belief, mech, props)

            # Reactance cost
            react_cost = props["reactance_cost"]
            if belief.reactance_used > 0.6:
                react_cost *= 2.0  # Reactance compounds when budget is low

            # Net value
            net = (
                self.alpha * conv_prob
                + self.beta * info_gain
                - self.gamma * react_cost
            )

            if net > best_value:
                best_value = net
                best = TouchRecommendation(
                    mechanism=mech,
                    net_value=round(net, 4),
                    conversion_probability=round(conv_prob, 4),
                    information_gain=round(info_gain, 4),
                    reactance_cost=round(react_cost, 4),
                    pe_gradient=props["pe_gradient"],
                    rationale=self._generate_rationale(belief, mech, props, conv_prob, info_gain),
                    if_click_prediction=self._predict_if_click(belief, mech),
                    if_no_click_prediction=self._predict_if_no_click(belief, mech),
                )

        if best is None:
            return TouchRecommendation(
                mechanism="autonomy_restoration",
                net_value=0.0, conversion_probability=0.0,
                information_gain=0.0, reactance_cost=0.0, pe_gradient=0.1,
                rationale="No viable mechanisms — reactance budget exhausted",
                if_click_prediction="Unlikely", if_no_click_prediction="Expected",
                should_release=True, release_reason="All mechanisms have negative net value",
            )

        # Optimal stopping check
        if best.net_value < RELEASE_THRESHOLD:
            best.should_release = True
            best.release_reason = (
                f"Net value {best.net_value:.4f} below threshold {RELEASE_THRESHOLD}. "
                f"Expected return of next touch is less than cost of reaching a new person. "
                f"Move to dormant pool — re-engage only on organic return signal."
            )

        return best

    def _estimate_conversion(
        self, belief: BeliefState, mech: str, props: Dict
    ) -> float:
        """Estimate conversion probability for this mechanism given the belief state."""
        # Base: inversely proportional to estimated remaining touches
        base = 1.0 / max(1.0, belief.estimated_touches_remaining + 1)

        # Attachment fit bonus
        att_fit = props["attachment_fit"].get(belief.attachment.dominant(), 0.5)
        att_bonus = (att_fit - 0.5) * 0.3

        # NFC match
        nfc_diff = abs(belief.need_for_cognition - props["nfc_requirement"])
        nfc_penalty = -nfc_diff * 0.15

        # Somatic readiness (positive valence = closer to conversion)
        somatic_bonus = max(0, belief.somatic.net_valence) * 0.2

        # Construal match (mechanism matches their abstraction level)
        construal_diff = abs(belief.construal_abstract_to_concrete - props["construal_target"])
        construal_penalty = -construal_diff * 0.1

        # PE tolerance check (don't exceed their tolerance)
        if props["pe_gradient"] > belief.pe_tolerance + 0.2:
            pe_penalty = -0.15  # Too challenging — will shut down
        else:
            pe_penalty = 0.0

        return max(0.01, min(0.5, base + att_bonus + nfc_penalty + somatic_bonus + construal_penalty + pe_penalty))

    def _estimate_information_gain(
        self, belief: BeliefState, mech: str, props: Dict
    ) -> float:
        """Estimate how much we'll learn from this person's response."""
        # High entropy = lots to learn
        current_entropy = belief.entropy()

        # Mechanisms that discriminate between hypotheses have high info gain
        att_spread = abs(props["attachment_fit"].get("anxious", 0.5) - props["attachment_fit"].get("avoidant", 0.5))
        discrimination = att_spread * 0.4

        # If we're already confident, less to learn
        confidence_discount = 1.0 - (belief.observation_count / 10.0)
        confidence_discount = max(0.2, confidence_discount)

        return current_entropy * discrimination * confidence_discount

    def _generate_rationale(
        self, belief: BeliefState, mech: str, props: Dict,
        conv_prob: float, info_gain: float,
    ) -> str:
        """Generate human-readable rationale for the recommendation."""
        att = belief.attachment.dominant()
        mot = belief.motive.dominant()
        nfc = "high" if belief.need_for_cognition > 0.6 else "low" if belief.need_for_cognition < 0.4 else "moderate"
        somatic = "positive" if belief.somatic.net_valence > 0 else "negative" if belief.somatic.net_valence < -0.1 else "neutral"

        parts = [
            f"Attachment: {att} (P={getattr(belief.attachment, att):.2f})",
            f"Motive: {mot}",
            f"NFC: {nfc} ({belief.need_for_cognition:.2f})",
            f"Somatic: {somatic} (valence={belief.somatic.net_valence:.2f})",
            f"Construal: {'concrete' if belief.construal_abstract_to_concrete > 0.6 else 'abstract'} ({belief.construal_abstract_to_concrete:.2f})",
            f"Reactance: {belief.reactance_used:.2f}/{1.0:.0f} budget used",
            f"Distance: ~{belief.estimated_touches_remaining:.1f} touches remaining",
            f"→ {mech}: conv={conv_prob:.3f}, info={info_gain:.3f}, PE={props['pe_gradient']:.1f}",
        ]
        return " | ".join(parts)

    def _predict_if_click(self, belief: BeliefState, mech: str) -> str:
        """What we learn if they click."""
        props = MECHANISM_PROPERTIES.get(mech, {})
        att_fit = props.get("attachment_fit", {})
        best_att = max(att_fit, key=att_fit.get) if att_fit else "unknown"
        return (
            f"Click confirms {best_att} attachment pattern. "
            f"PE tolerance adequate (≥{props.get('pe_gradient', 0):.1f}). "
            f"Somatic markers shifting positive. "
            f"Reduce estimated distance by 0.8 touches."
        )

    def _predict_if_no_click(self, belief: BeliefState, mech: str) -> str:
        """What we learn if they don't click."""
        props = MECHANISM_PROPERTIES.get(mech, {})
        att_fit = props.get("attachment_fit", {})
        worst_att = min(att_fit, key=att_fit.get) if att_fit else "unknown"
        return (
            f"No click increases P({worst_att}) attachment. "
            f"PE gradient {props.get('pe_gradient', 0):.1f} may exceed tolerance. "
            f"Consider lower-PE mechanism next. "
            f"If 2+ consecutive non-clicks, increase reactance rate."
        )


# =============================================================================
# PUZZLE SOLVER — Integrates belief state + touch selection
# =============================================================================

class PuzzleSolver:
    """Per-person puzzle solver.

    Maintains belief states in Redis, updates from every session,
    and provides optimal touch recommendations with full reasoning.
    """

    def __init__(self):
        self._updater = BeliefUpdater()
        self._selector = DiagnosticTouchSelector()

    def create_initial_belief(
        self,
        archetype: str = "",
    ) -> BeliefState:
        """Create an initial belief state, optionally conditioned on archetype."""
        belief = BeliefState()

        # If we know the archetype from campaign attribution, condition the prior
        if archetype == "careful_truster":
            belief.attachment.anxious = 0.6
            belief.attachment.secure = 0.2
            belief.attachment.avoidant = 0.2
            belief.motive.self_protection = 0.5
            belief.somatic.negative_markers = 0.6
            belief.need_for_cognition = 0.65
            belief.estimated_touches_remaining = 4.0
        elif archetype == "status_seeker":
            belief.attachment.anxious = 0.15
            belief.attachment.secure = 0.65
            belief.attachment.avoidant = 0.2
            belief.motive.status_signaling = 0.5
            belief.somatic.negative_markers = 0.3
            belief.need_for_cognition = 0.45
            belief.estimated_touches_remaining = 3.0
        elif archetype == "easy_decider":
            belief.attachment.anxious = 0.1
            belief.attachment.secure = 0.2
            belief.attachment.avoidant = 0.7
            belief.motive.energy_conservation = 0.5
            belief.somatic.negative_markers = 0.2
            belief.need_for_cognition = 0.25
            belief.estimated_touches_remaining = 2.0

        return belief

    def update_belief(
        self,
        belief: BeliefState,
        session_data: Dict,
    ) -> BeliefState:
        """Update belief state from a new session."""
        return self._updater.update_from_session(belief, session_data)

    def recommend_next_touch(
        self,
        belief: BeliefState,
        candidate_mechanisms: Optional[List[str]] = None,
    ) -> TouchRecommendation:
        """Get the optimal next touch recommendation."""
        return self._selector.select(belief, candidate_mechanisms)

    def should_release(self, belief: BeliefState) -> Tuple[bool, str]:
        """Should we stop targeting this person?

        Based on Charnov's Marginal Value Theorem: release when
        expected return of next touch < average acquisition cost.
        """
        if belief.reactance_used > 0.85:
            return True, "Reactance budget nearly exhausted (>85%). Further touches risk brand damage."

        if belief.estimated_touches_remaining > 8 and belief.observation_count >= 4:
            return True, (
                f"Estimated {belief.estimated_touches_remaining:.0f} touches remaining after "
                f"{belief.observation_count} observations. Conversion too distant to justify spend."
            )

        if belief.somatic.net_valence < -0.3 and belief.observation_count >= 3:
            return True, (
                "Strong negative somatic markers not resolving. "
                "Likely a life-context mismatch (threat state active). "
                "Move to dormant pool — re-engage only on organic return."
            )

        # Run the selector and check its recommendation
        rec = self._selector.select(belief)
        if rec.should_release:
            return True, rec.release_reason

        return False, "Continue targeting"


def get_puzzle_solver() -> PuzzleSolver:
    """Get a PuzzleSolver instance."""
    return PuzzleSolver()
