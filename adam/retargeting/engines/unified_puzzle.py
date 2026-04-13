# =============================================================================
# Unified Puzzle Inference
# Location: adam/retargeting/engines/unified_puzzle.py
# =============================================================================

"""
ONE model. ONE inference. ALL signals considered simultaneously.

The previous architecture had isolated components:
  - Impression classifier looked at click/no-click independently
  - Frustration scorer looked at dimension tensions independently
  - Temporal learner looked at time patterns independently
  - Barrier self-report looked at section dwell independently
  - Frequency decay looked at engagement sequence independently

This was wrong. A person is not a collection of independent signals.
They are a single psychological state. All signals are partial views
of that one state. The inference must be JOINT, not marginal.

This module replaces all of that with a single function:

  infer_person(all_available_evidence) → PersonState

PersonState contains:
  - WHY they haven't converted (the actual barrier, considering everything)
  - WHAT to do next (the optimal touch, considering all constraints)
  - WHETHER to continue (considering all evidence for and against)
  - HOW CONFIDENT we are (considering the quality of all evidence)

The key insight: each piece of evidence constrains the space of
possible explanations. Section dwell on safety AND organic returns
AND decreasing click latency AND no reactance — these together tell
a story that none of them tell alone. The story is:

  "This person has negative somatic markers from past car service
   experiences (safety fixation), but they're resolving (decreasing
   latency) and self-motivating (organic returns) with no resistance
   (no reactance). They're 2-3 touches from conversion. The barrier
   is trust, not price. The next touch should be a testimonial from
   someone like them — not evidence, not loss framing. A testimonial
   creates a vicarious positive somatic marker that overwrites the
   negative one. Evidence appeals to cognition, but this person's
   barrier is a FEELING, not a THOUGHT."

No isolated classifier produces that inference. Only the joint
consideration of all evidence together does.
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PersonState:
    """Complete unified understanding of one person.

    This is the SINGLE output of the unified inference.
    Every decision about this person comes from here.
    """

    # ── Identity ──
    user_id: str = ""
    archetype: str = ""  # Attributed or inferred

    # ── The Story (narrative explanation of their state) ──
    narrative: str = ""  # Human-readable explanation of everything we know

    # ── Psychological State ──
    # Not independent dimensions — these are JOINTLY inferred from all evidence
    dominant_barrier: str = ""          # The ACTUAL barrier, all evidence considered
    barrier_confidence: float = 0.0
    barrier_is_somatic: bool = False    # Feeling-based vs thought-based
    barrier_is_cognitive: bool = False
    barrier_is_contextual: bool = False # Life situation, not product issue

    # ── Engagement Trajectory ──
    trajectory: str = ""     # "approaching", "stalled", "retreating", "converting", "dormant"
    trajectory_velocity: float = 0.0  # How fast they're moving (positive = toward conversion)

    # ── Readiness ──
    conversion_probability: float = 0.0
    touches_remaining: float = 5.0
    receptive_now: bool = True      # Are they in a state to receive a touch?

    # ── Response Pattern ──
    response_type: str = ""   # "engager", "builder", "ad_averse", "rejector", "unknown"
    clicks_ads: bool = True   # Do they ever click ads?
    responds_to_organic: bool = False  # Do they self-direct?

    # ── Interaction-Effect Archetype ──
    interaction_archetype: str = ""  # explorer, trusting_loyalist, reliable_cooperator, prevention_planner, anxious_economist, vocal_resistor
    interaction_archetype_confidence: float = 0.0
    suppress: bool = False           # True for anxious_economist, vocal_resistor
    suppress_reason: str = ""

    # ── Optimal Action ──
    recommended_mechanism: str = ""
    mechanism_rationale: str = ""
    prediction_error_level: float = 0.3  # How much to challenge them (0=confirming, 1=disrupting)
    communication_style: str = ""  # "reassuring", "aspirational", "efficient", "peer"
    should_continue: bool = True
    continue_reason: str = ""

    # ── Meta ──
    evidence_quality: float = 0.0  # How much we can trust this inference (0-1)
    sessions_observed: int = 0
    last_updated: float = 0.0

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}


def infer_person(profile: Dict, conversions: List[Dict] = None, context: Dict = None) -> PersonState:
    """The SINGLE unified inference function.

    Takes ALL available evidence and produces ONE coherent understanding
    of this person. No siloed analysis. No independent classifiers.
    Everything considered together.

    Args:
        profile: The StoredSignalProfile data (all sessions accumulated)
        conversions: Any conversion events for this user
        context: Optional page/domain context from the current impression.
            Includes goal_activation data when available.

    Returns:
        PersonState — complete unified understanding
    """
    state = PersonState()
    state.user_id = profile.get("user_id", "")
    state.last_updated = time.time()
    state.sessions_observed = profile.get("total_sessions", 0)

    conversions = conversions or []
    conv_user_ids = {c.get("visitor_id") for c in conversions}
    is_converted = state.user_id in conv_user_ids

    if is_converted:
        state.trajectory = "converted"
        state.conversion_probability = 1.0
        state.should_continue = False
        state.continue_reason = "Already converted"
        state.narrative = "This person has converted. Puzzle solved."
        return state

    if state.sessions_observed == 0:
        state.trajectory = "unknown"
        state.evidence_quality = 0.0
        state.narrative = "No data yet. Waiting for first interaction."
        return state

    # ════════════════════════════════════════════════════════════════
    # GATHER ALL EVIDENCE (nothing computed yet, just collecting)
    # ════════════════════════════════════════════════════════════════

    total_sessions = profile.get("total_sessions", 0)
    ad_sessions = profile.get("ad_attributed_sessions", 0)
    organic_sessions = profile.get("organic_sessions", 0)
    organic_ratio = organic_sessions / max(1, total_sessions)

    section_dwell = profile.get("section_dwell_totals", {})
    safety_dwell = section_dwell.get("section-safety", 0) + section_dwell.get("section-reviews", 0)
    trust_dwell = safety_dwell + section_dwell.get("section-testimonials", 0)
    price_dwell = section_dwell.get("section-pricing", 0)
    action_dwell = section_dwell.get("section-booking", 0)
    fleet_dwell = section_dwell.get("section-fleet", 0)
    social_proof_engagement = section_dwell.get("section-reviews", 0) + section_dwell.get("section-testimonials", 0)
    total_dwell = sum(section_dwell.values())

    touch_outcomes = profile.get("touch_outcomes", [])
    n_clicks = sum(1 for t in touch_outcomes if t)
    n_touches = len(touch_outcomes)

    # Cumulative goal priming from page context history
    # Goals persist and intensify across the retargeting sequence
    cumulative_goals = profile.get("cumulative_goal_priming", {})
    impression_domains = profile.get("impression_domains", [])
    best_crossover_domain = profile.get("best_crossover_domain", "")

    # Current impression context (if available)
    current_goal_activation = {}
    if context and context.get("goal_activation"):
        current_goal_activation = context["goal_activation"]

    click_trajectory = profile.get("click_latency_trajectory", "")
    click_slope = profile.get("click_latency_slope", 0)
    self_reported_barrier = profile.get("self_reported_barrier", "")
    barrier_confidence_raw = profile.get("barrier_self_report_confidence", 0)

    reactance = profile.get("reactance_detected", False)
    reactance_h4 = profile.get("reactance_h4_modifier", 0)

    attributed_archetype = profile.get("attributed_archetype", "")
    touch_positions = profile.get("attributed_touch_positions", [])
    mechanisms_exposed = profile.get("mechanisms_exposed", [])

    devices = profile.get("device_impressions", {})
    desktop_sessions = devices.get("desktop", 0)
    mobile_sessions = devices.get("mobile", 0)

    # ════════════════════════════════════════════════════════════════
    # JOINT INFERENCE (all evidence considered simultaneously)
    # ════════════════════════════════════════════════════════════════

    state.archetype = attributed_archetype

    # ── Step 1: What kind of responder are they? ──
    # This is NOT independent of everything else — it's the first
    # constraint on the space of explanations.

    if n_clicks > 0:
        state.clicks_ads = True
        state.response_type = "engager"
    elif organic_sessions > 0:
        state.clicks_ads = False
        state.responds_to_organic = True
        state.response_type = "builder"  # Building through mere exposure
    elif ad_sessions >= 3 and total_dwell < 5 and organic_sessions == 0:
        state.clicks_ads = False
        state.response_type = "ad_averse"
    elif total_dwell > 15 and n_clicks == 0:
        state.clicks_ads = False
        state.responds_to_organic = True
        state.response_type = "builder"  # Engaging with site but not through ads
    else:
        state.response_type = "unknown"

    # ── Step 1b: Interaction-effect archetype detection ──
    # These are COMBINATIONS of traits that predict conversion better
    # than any single dimension. Discovered from cross-category analysis
    # of 949 moderate airline reviewers.

    # We need proxy estimates of Big Five + regulatory focus from behavioral signals
    # High NFC + deep engagement + FAQ = conscientiousness proxy
    conscientiousness_proxy = 0.5
    if total_dwell > 40: conscientiousness_proxy += 0.15
    if section_dwell.get("section-faq", 0) > 5: conscientiousness_proxy += 0.1
    if len(touch_positions) > 2: conscientiousness_proxy += 0.1
    conscientiousness_proxy = min(0.95, conscientiousness_proxy)

    # Organic returns + broad browsing = openness proxy
    openness_proxy = 0.5
    if organic_sessions > 0: openness_proxy += 0.15
    if len(section_dwell) > 3: openness_proxy += 0.1  # Explored many sections
    openness_proxy = min(0.95, openness_proxy)

    # Quick positive engagement + low friction = agreeableness proxy
    agreeableness_proxy = 0.5
    if n_clicks > 0 and not reactance: agreeableness_proxy += 0.2
    if organic_sessions > 0: agreeableness_proxy += 0.1
    agreeableness_proxy = min(0.95, agreeableness_proxy)

    # Safety/review fixation = prevention focus proxy
    prevention_proxy = 0.5
    if safety_dwell > 15: prevention_proxy += 0.2
    if trust_dwell > 20: prevention_proxy += 0.1
    prevention_proxy = min(0.95, prevention_proxy)

    # Aspiration/fleet browsing = promotion focus proxy
    promotion_proxy = 0.5
    if fleet_dwell > 10: promotion_proxy += 0.15
    if action_dwell > 10 and total_dwell < 30: promotion_proxy += 0.15
    promotion_proxy = min(0.95, promotion_proxy)

    # Neuroticism proxy: reactance + repeated safety checking
    neuroticism_proxy = 0.3
    if reactance: neuroticism_proxy += 0.3
    if safety_dwell > 25: neuroticism_proxy += 0.15
    neuroticism_proxy = min(0.95, neuroticism_proxy)

    # Spending pain proxy: heavy pricing engagement
    spending_pain_proxy = 0.3
    if price_dwell > 15: spending_pain_proxy += 0.3
    if price_dwell > 25: spending_pain_proxy += 0.2
    spending_pain_proxy = min(0.95, spending_pain_proxy)

    # Now detect interaction-effect archetypes
    # Priority order: suppress first (save money), then specific types, then general
    # Each requires BOTH dimensions to be high

    # ── SUPPRESS FIRST (save money) ──

    # Defensive Skeptic (neuroticism HIGH + reactance HIGH) — 0.01x lift (WORST)
    # Discovered in moderate segment: 0.1% conversion rate (N=955)
    if neuroticism_proxy > 0.55 and reactance:
        state.interaction_archetype = "defensive_skeptic"
        state.interaction_archetype_confidence = neuroticism_proxy
        state.suppress = True
        state.suppress_reason = (
            f"Defensive Skeptic: neuroticism={neuroticism_proxy:.2f}, reactance=detected. "
            "0.1% conversion rate in moderate segment (N=955). "
            "The hardest suppress — anxious AND resistant. Every touch makes it worse."
        )

    # Anxious Economist (neuroticism HIGH + spending_pain HIGH) — 0.23x lift
    elif neuroticism_proxy > 0.55 and spending_pain_proxy > 0.55:
        state.interaction_archetype = "anxious_economist"
        state.interaction_archetype_confidence = min(neuroticism_proxy, spending_pain_proxy)
        state.suppress = True
        state.suppress_reason = (
            f"Anxious Economist: neuroticism={neuroticism_proxy:.2f}, "
            f"spending_pain={spending_pain_proxy:.2f}. "
            "0% conversion in luxury car data, 0.23x in airline (N=399). "
            "Ad spend on this profile generates anxiety, not conversion."
        )

    # Vocal Resistor (reactance + deep engagement = fighting back) — 0.36x lift
    elif reactance and total_dwell > 15:
        state.interaction_archetype = "vocal_resistor"
        state.interaction_archetype_confidence = 0.7
        state.suppress = True
        state.suppress_reason = (
            "Vocal Resistor: reactance detected with deep engagement. "
            "0.36x lift in cross-category analysis (N=203). "
            "Advertising triggers resistance. Release immediately."
        )

    # ── TARGET ARCHETYPES (ordered: strongest interaction first) ──

    # The Prevention Planner (conscientiousness HIGH + prevention HIGH)
    # Check BEFORE loyalist because safety-focused planners look agreeable
    elif conscientiousness_proxy > 0.6 and prevention_proxy > 0.65:
        state.interaction_archetype = "prevention_planner"
        state.interaction_archetype_confidence = min(conscientiousness_proxy, prevention_proxy)

    # The Explorer (openness HIGH + promotion HIGH) — 1.91x lift
    elif openness_proxy > 0.6 and promotion_proxy > 0.6 and prevention_proxy < 0.55:
        state.interaction_archetype = "explorer"
        state.interaction_archetype_confidence = min(openness_proxy, promotion_proxy)

    # The Reliable Cooperator (conscientiousness HIGH + agreeableness HIGH + NOT prevention)
    elif conscientiousness_proxy > 0.6 and agreeableness_proxy > 0.6 and prevention_proxy < 0.6:
        state.interaction_archetype = "reliable_cooperator"
        state.interaction_archetype_confidence = min(conscientiousness_proxy, agreeableness_proxy)

    # The Trusting Loyalist (agreeableness HIGH + trust dwell + LOW negativity evidence)
    # Cross-category validated: 3.52x polar, 8.1x in moderate segment
    elif agreeableness_proxy > 0.7 and trust_dwell > 10 and not reactance and prevention_proxy < 0.55:
        state.interaction_archetype = "trusting_loyalist"
        state.interaction_archetype_confidence = agreeableness_proxy

    # The Dependable Loyalist (brand_trust HIGH + conscientiousness HIGH)
    # Subtle archetype from moderate segment: 66.4% conv (N=119), 6.6x lift
    # These are the "quiet converters" — not extreme on any one dim, but
    # the combination of trust + conscientiousness means they follow through.
    elif trust_dwell > 8 and conscientiousness_proxy > 0.6 and neuroticism_proxy < 0.45:
        state.interaction_archetype = "dependable_loyalist"
        state.interaction_archetype_confidence = conscientiousness_proxy

    # The Consensus Seeker (agreeableness MODERATE + social proof engagement)
    # Moderate segment: 33.3% conv (N=39), 3.3x lift
    # Reachable specifically via social proof — testimonials, "others like you"
    elif agreeableness_proxy > 0.5 and social_proof_engagement > 5 and not reactance:
        state.interaction_archetype = "consensus_seeker"
        state.interaction_archetype_confidence = agreeableness_proxy * 0.8

    # ── Step 2: What's the trajectory? ──
    # All signals together paint the trajectory picture.

    approaching_signals = 0
    retreating_signals = 0

    if click_trajectory == "resolving":
        approaching_signals += 2
    elif click_trajectory == "building":
        retreating_signals += 2

    if organic_sessions > 0:
        approaching_signals += 2  # Strong signal — self-directed interest

    if reactance:
        retreating_signals += 3  # Very strong — they're pushing back

    if total_dwell > 30:
        approaching_signals += 1
    elif total_dwell < 5 and total_sessions > 2:
        retreating_signals += 1

    if action_dwell > 10:
        approaching_signals += 2  # Engaging with booking = close

    if len(touch_positions) > 0 and max(touch_positions) >= 3:
        approaching_signals += 1  # Reached later touches

    velocity = (approaching_signals - retreating_signals) / max(1, approaching_signals + retreating_signals)
    state.trajectory_velocity = round(velocity, 3)

    if velocity > 0.3:
        state.trajectory = "approaching"
    elif velocity < -0.3:
        state.trajectory = "retreating"
    elif state.response_type == "ad_averse":
        state.trajectory = "dormant"
    elif total_sessions >= 3 and velocity > -0.1 and velocity < 0.1:
        state.trajectory = "stalled"
    else:
        state.trajectory = "early"

    # ── Step 3: What's the ACTUAL barrier? ──
    # The barrier is inferred from the COMBINATION of section engagement,
    # organic behavior, click patterns, and self-reported barrier.
    # These aren't independent — they constrain each other.

    barrier_evidence = {}

    # Self-reported barrier from section dwell
    if self_reported_barrier and barrier_confidence_raw > 0.3:
        barrier_evidence[self_reported_barrier] = barrier_confidence_raw

    # But consider the TRAJECTORY context:
    # If they're approaching despite a trust barrier, the trust is RESOLVING
    if self_reported_barrier == "trust_deficit" and state.trajectory == "approaching":
        barrier_evidence["trust_deficit"] = barrier_confidence_raw * 0.5  # Discounted
        barrier_evidence["intention_action_gap"] = 0.3  # They might be ready but stuck on action

    # If they spend time on pricing AND booking, the barrier is price not trust
    if price_dwell > 10 and action_dwell > 5:
        barrier_evidence["price_friction"] = min(0.8, price_dwell / 30)

    # If organic returns exist, the barrier is NOT awareness — it's conversion friction
    if organic_sessions > 0:
        barrier_evidence["intention_action_gap"] = max(
            barrier_evidence.get("intention_action_gap", 0), 0.4
        )

    # If reactance, the barrier IS reactance
    if reactance:
        barrier_evidence["reactance_triggered"] = 0.9

    # Select dominant barrier
    if barrier_evidence:
        state.dominant_barrier = max(barrier_evidence, key=barrier_evidence.get)
        state.barrier_confidence = barrier_evidence[state.dominant_barrier]
    else:
        state.dominant_barrier = "unknown"
        state.barrier_confidence = 0.0

    # Is the barrier somatic or cognitive?
    # Somatic: trust_deficit (FEELING of unreliability), quality_uncertainty (FEELING of risk)
    # Cognitive: price_friction (CALCULATION), processing_overload (THINKING too hard)
    # Contextual: intention_action_gap (LIFE context prevents action)
    somatic_barriers = {"trust_deficit", "quality_uncertainty", "emotional_disconnect", "reactance_triggered"}
    cognitive_barriers = {"price_friction", "processing_overload", "motive_mismatch"}
    contextual_barriers = {"intention_action_gap"}

    state.barrier_is_somatic = state.dominant_barrier in somatic_barriers
    state.barrier_is_cognitive = state.dominant_barrier in cognitive_barriers
    state.barrier_is_contextual = state.dominant_barrier in contextual_barriers

    # BUT: Need for Cognition modulates this
    # High-NFC indicators: high scroll depth, many pages, FAQ engagement
    nfc_signals = 0
    if total_dwell > 40: nfc_signals += 1
    if len(touch_positions) > 2: nfc_signals += 1
    if section_dwell.get("section-faq", 0) > 5: nfc_signals += 1
    if section_dwell.get("section-how-it-works", 0) > 5: nfc_signals += 1

    high_nfc = nfc_signals >= 2

    # For high-NFC people, even somatic barriers have a cognitive component
    if high_nfc and state.barrier_is_somatic:
        state.barrier_is_cognitive = True  # BOTH — they need feeling AND thinking

    # ── Step 4: Optimal action (considering everything together) ──

    # INTERACTION ARCHETYPE OVERRIDES — these take priority when detected
    # because they predict conversion 2x better than single-dimension analysis

    if state.suppress:
        state.communication_style = "suppress"
        state.recommended_mechanism = "none"
        state.mechanism_rationale = state.suppress_reason
        state.should_continue = False
        state.continue_reason = state.suppress_reason
        state.conversion_probability = 0.01
        state.touches_remaining = 0

    elif state.interaction_archetype == "explorer":
        state.communication_style = "aspirational_discovery"
        state.recommended_mechanism = "narrative_transportation"
        state.mechanism_rationale = (
            f"Explorer archetype (openness={openness_proxy:.2f}, promotion={promotion_proxy:.2f}). "
            f"2x base conversion rate. Responds to NOVELTY, not trust or evidence. "
            f"Creative: emphasize the experience they haven't tried. "
            f"Short sequence: 2 touches max. Don't over-explain."
        )
        state.prediction_error_level = 0.3
        state.touches_remaining = 2.0

    elif state.interaction_archetype == "trusting_loyalist":
        state.communication_style = "welcoming"
        state.recommended_mechanism = "social_proof_matched"
        state.mechanism_rationale = (
            f"Trusting Loyalist archetype (agreeableness={agreeableness_proxy:.2f}). "
            f"3.52x lift (cross-category validated, N=11,805). "
            f"Gives benefit of the doubt. "
            f"Minimal persuasion needed — just social proof and easy booking. "
            f"2 touches max. Don't over-explain — they already believe you."
        )
        state.prediction_error_level = 0.15
        state.touches_remaining = 1.5

    elif state.interaction_archetype == "reliable_cooperator":
        state.communication_style = "structured_efficient"
        state.recommended_mechanism = "implementation_intention"
        state.mechanism_rationale = (
            f"Reliable Cooperator (conscientiousness={conscientiousness_proxy:.2f}, "
            f"agreeableness={agreeableness_proxy:.2f}). 1.68x base conversion rate. "
            f"Not impulse — PLANNING. Calendar sync, advance booking, scheduling. "
            f"'Book your Tuesday 6am pickup now' — specific, structured, planned."
        )
        state.prediction_error_level = 0.4
        state.touches_remaining = 2.0

    elif state.interaction_archetype == "prevention_planner":
        state.communication_style = "reassuring_preventive"
        state.recommended_mechanism = "anxiety_resolution"
        state.mechanism_rationale = (
            f"Prevention Planner (conscientiousness={conscientiousness_proxy:.2f}, "
            f"prevention={prevention_proxy:.2f}). Largest moderate segment. "
            f"PREVENTION framing: what they AVOID, not what they gain. "
            f"'Never worry about airport pickup again' — not 'experience luxury.' "
            f"This is regulatory fit — match their prevention focus."
        )
        state.prediction_error_level = 0.2
        state.touches_remaining = 3.0

    elif state.interaction_archetype == "dependable_loyalist":
        state.communication_style = "straightforward_reliable"
        state.recommended_mechanism = "evidence_proof"
        state.mechanism_rationale = (
            f"Dependable Loyalist (conscientiousness={conscientiousness_proxy:.2f}, "
            f"trust_dwell={trust_dwell:.0f}s). 66.4% conv in moderate segment (6.6x lift). "
            f"Quiet converters — not extreme on any dimension but the brand_trust × "
            f"conscientiousness combination means they follow through. "
            f"Give them facts, credentials, straightforward booking. 3 touches."
        )
        state.prediction_error_level = 0.25
        state.touches_remaining = 3.0

    elif state.interaction_archetype == "consensus_seeker":
        state.communication_style = "social_validating"
        state.recommended_mechanism = "social_proof_matched"
        state.mechanism_rationale = (
            f"Consensus Seeker (agreeableness={agreeableness_proxy:.2f}, "
            f"social_proof_engagement={social_proof_engagement:.0f}s). "
            f"33.3% conv in moderate segment (3.3x lift). "
            f"Converts specifically via social proof — testimonials, 'others like you chose...', "
            f"peer endorsements. NOT authority or aspiration — they need to see PEOPLE like them."
        )
        state.prediction_error_level = 0.35
        state.touches_remaining = 3.0

    # STANDARD CLASSIFICATION — when no interaction archetype detected
    elif state.response_type == "ad_averse":
        state.communication_style = "awareness_only"
        state.recommended_mechanism = "none"
        state.mechanism_rationale = (
            "This person does not respond to ad-driven engagement. "
            "Continue brand impressions for mere exposure but expect "
            "conversion only through organic discovery."
        )
        state.should_continue = False
        state.continue_reason = "Ad-averse — release to awareness-only pool"

    elif reactance:
        state.communication_style = "respectful_distance"
        state.recommended_mechanism = "autonomy_restoration"
        state.mechanism_rationale = (
            "Reactance detected — they feel pressured. The only mechanism "
            "that helps is validating their autonomy. Back off significantly. "
            "If autonomy_restoration doesn't work, release entirely."
        )
        state.prediction_error_level = 0.05  # Minimal — soothing, not challenging

    elif state.barrier_is_somatic and not high_nfc:
        # Feeling-based barrier for non-analytical person
        # → Testimonial/narrative that creates vicarious positive experience
        state.communication_style = "reassuring"
        state.recommended_mechanism = "narrative_transportation" if trust_dwell > 15 else "social_proof_matched"
        state.mechanism_rationale = (
            f"Barrier is somatic ({state.dominant_barrier}) — a FEELING, not a thought. "
            f"Evidence won't help. They need a vicarious positive experience. "
            f"{'Testimonial' if trust_dwell > 15 else 'Social proof'} from someone "
            f"like them creates a new somatic marker that overwrites the negative one."
        )
        state.prediction_error_level = 0.2 if state.trajectory == "early" else 0.4

    elif state.barrier_is_somatic and high_nfc:
        # Feeling-based barrier but analytical person
        # → Need BOTH testimonial (feeling) AND evidence (thinking)
        state.communication_style = "evidence_backed_reassurance"
        state.recommended_mechanism = "evidence_proof"
        state.mechanism_rationale = (
            f"Barrier is somatic ({state.dominant_barrier}) but high NFC — "
            f"they need BOTH feeling and data. Lead with a testimonial "
            f"(somatic marker) then follow with statistics (cognitive resolution). "
            f"Neither alone is sufficient for this person."
        )
        state.prediction_error_level = 0.35

    elif state.barrier_is_cognitive:
        # Thinking-based barrier → logical resolution
        if state.dominant_barrier == "price_friction":
            state.communication_style = "value_framing"
            state.recommended_mechanism = "loss_framing" if state.trajectory == "approaching" else "claude_argument"
            state.mechanism_rationale = (
                f"Price friction is cognitive — they've done the math and it doesn't work. "
                f"{'Loss framing shows what theyre losing by NOT using the service' if state.trajectory == 'approaching' else 'Rational argument reframes the value equation'}. "
                f"Mental accounting: frame as business expense, not personal luxury."
            )
        else:
            state.communication_style = "simplifying"
            state.recommended_mechanism = "micro_commitment"
            state.mechanism_rationale = (
                f"Processing overload — too much complexity. "
                f"Simplify to the smallest possible next step. "
                f"Don't ask them to commit — ask them to just check."
            )
        state.prediction_error_level = 0.5

    elif state.barrier_is_contextual:
        # Life context barrier → implementation
        state.communication_style = "enabling"
        state.recommended_mechanism = "implementation_intention"
        state.mechanism_rationale = (
            f"The barrier is the gap between wanting and doing. "
            f"They're interested (organic ratio: {organic_ratio:.0%}) but "
            f"haven't found the right moment to act. Create a specific "
            f"if-then plan: 'When [trigger], then [book LUXY]'."
        )
        state.prediction_error_level = 0.6

    else:
        # Unknown barrier, early stage
        state.communication_style = "exploratory"
        state.recommended_mechanism = "social_proof_matched"
        state.mechanism_rationale = (
            f"Insufficient evidence to determine specific barrier. "
            f"Social proof is the safest first touch — it's low reactance, "
            f"creates mild positive somatic markers, and the response will "
            f"reveal whether they're trust-seeking, status-seeking, or action-seeking."
        )
        state.prediction_error_level = 0.15

    # ── Step 5: Conversion probability ──
    # Joint estimate from ALL evidence

    base = 0.05
    if state.trajectory == "approaching": base += 0.15
    if organic_sessions > 0: base += 0.10
    if action_dwell > 10: base += 0.15
    if n_clicks > 0: base += 0.10
    if click_trajectory == "resolving": base += 0.10
    if state.trajectory == "retreating": base -= 0.10
    if reactance: base -= 0.15
    if state.response_type == "ad_averse": base = 0.02

    state.conversion_probability = round(max(0.01, min(0.8, base)), 4)

    # ── Step 6: Touches remaining ──

    if state.conversion_probability > 0.3:
        state.touches_remaining = 1.5
    elif state.conversion_probability > 0.15:
        state.touches_remaining = 3.0
    elif state.trajectory == "approaching":
        state.touches_remaining = 4.0
    elif state.trajectory == "stalled":
        state.touches_remaining = 5.0
    else:
        state.touches_remaining = 6.0

    # ── Step 7: Should we continue? ──

    if not state.should_continue:
        pass  # Already decided (ad_averse or converted)
    elif reactance and state.trajectory == "retreating":
        state.should_continue = False
        state.continue_reason = (
            "Reactance active AND trajectory retreating. "
            "Further touches will damage the brand. Release to dormant."
        )
    elif state.response_type == "ad_averse":
        state.should_continue = False
        state.continue_reason = "Ad-averse — no click-through engagement possible."
    elif total_sessions >= 6 and state.conversion_probability < 0.08:
        state.should_continue = False
        state.continue_reason = (
            f"6+ sessions with <8% conversion probability. "
            f"Expected return below acquisition cost. Release."
        )
    else:
        state.should_continue = True
        state.continue_reason = f"Active — {state.trajectory} trajectory, {state.conversion_probability:.0%} conversion probability"

    # ── Step 8: Evidence quality ──

    state.evidence_quality = min(1.0, total_sessions * 0.15 + n_clicks * 0.1 + (1 if organic_sessions > 0 else 0) * 0.2)

    # ── Step 9: The narrative ──
    # This is the story — the unified understanding of this person

    parts = []

    # Who they are
    if attributed_archetype:
        parts.append(f"Identified as {attributed_archetype}")
    parts.append(f"after {total_sessions} sessions ({ad_sessions} ad-driven, {organic_sessions} organic)")

    # Their trajectory
    trajectory_narratives = {
        "approaching": "and moving toward conversion",
        "stalled": "but stalled — interest exists without momentum",
        "retreating": "and pulling away — engagement declining",
        "dormant": "with no meaningful engagement detected",
        "early": "in early evaluation",
        "converting": "at the point of conversion",
    }
    parts.append(trajectory_narratives.get(state.trajectory, ""))

    # Their barrier
    if state.dominant_barrier and state.dominant_barrier != "unknown":
        barrier_type = "feeling" if state.barrier_is_somatic else "thinking" if state.barrier_is_cognitive else "contextual"
        parts.append(
            f"The barrier is {state.dominant_barrier} — a {barrier_type}-based obstacle"
            f"{' (they need both data and reassurance due to high analytical tendency)' if state.barrier_is_somatic and state.barrier_is_cognitive else ''}"
        )

    # The recommendation
    if state.recommended_mechanism and state.recommended_mechanism != "none":
        parts.append(f"Recommended: {state.recommended_mechanism} ({state.communication_style} style)")

    # The prognosis
    if state.should_continue:
        parts.append(f"Estimated {state.touches_remaining:.0f} touches to conversion ({state.conversion_probability:.0%} probability)")
    else:
        parts.append(f"RELEASE: {state.continue_reason}")

    # ── Context-aware enrichment: cumulative goal priming ──
    # If we have goal priming history across touches, incorporate it into
    # the narrative and mechanism recommendation
    if cumulative_goals:
        # Find the dominant cumulative goal
        dominant_cumulative = max(cumulative_goals, key=cumulative_goals.get)
        cumulative_strength = cumulative_goals[dominant_cumulative]
        if cumulative_strength > 0.3:
            parts.append(
                f"Cumulative goal priming: {dominant_cumulative} "
                f"(strength={cumulative_strength:.2f} across {len(impression_domains)} touches)"
            )
            # If the cumulative goal aligns with the archetype, boost confidence
            try:
                from adam.intelligence.goal_activation import ARCHETYPE_GOAL_FULFILLMENT
                archetype = state.interaction_archetype or profile.get("attributed_archetype", "")
                fulfillment = ARCHETYPE_GOAL_FULFILLMENT.get(archetype, {})
                if dominant_cumulative in fulfillment and fulfillment[dominant_cumulative] > 0.5:
                    state.conversion_probability = min(0.95, state.conversion_probability * 1.15)
                    parts.append(
                        f"Goal-archetype alignment: {dominant_cumulative} fulfills {archetype}"
                    )
            except Exception:
                pass

    # If current impression has goal activation data, add context note
    if current_goal_activation and current_goal_activation.get("dominant_goal"):
        dominant_now = current_goal_activation["dominant_goal"]
        crossover = current_goal_activation.get("crossover_score", 0)
        if crossover > 0.2:
            parts.append(
                f"Current context activates {dominant_now} goal (crossover={crossover:.2f})"
            )

    state.narrative = ". ".join(parts) + "."

    return state


def get_unified_inference():
    """Get the unified inference function."""
    return infer_person
