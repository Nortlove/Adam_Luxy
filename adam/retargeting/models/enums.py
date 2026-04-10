# =============================================================================
# Therapeutic Retargeting Engine — Core Enums
# Location: adam/retargeting/models/enums.py
# Spec: Enhancement #33, Section C.1
# =============================================================================

"""
Core enumerations for the Therapeutic Retargeting Engine.

These enums define the vocabulary of the diagnostic retargeting loop:
- ConversionStage: WHERE the user is in the purchase funnel (TTM-derived)
- RuptureType: WHETHER the therapeutic alliance has broken down
- ScaffoldLevel: HOW MUCH support the messaging should provide
- BarrierCategory: WHY the user did not convert
- TherapeuticMechanism: WHAT intervention to deploy
"""

from enum import Enum


class ConversionStage(str, Enum):
    """TTM-derived conversion stages with behavioral signal classifiers.

    Mapped from Prochaska & DiClemente's Transtheoretical Model but adapted
    for purchase behavior. Behavioral signals — NOT self-report — drive
    classification. Stage-mismatched interventions generate resistance
    (Krebs et al., 2010, k=88).
    """

    UNAWARE = "unaware"
    # No brand interaction. Pre-contemplation equivalent.
    # Signal: No pixel fires, no site visits, no ad engagement.
    # Intervention: Consciousness raising only. NO conversion messaging.

    CURIOUS = "curious"
    # Initial brand awareness, low engagement.
    # Signal: Ad impression with >2s dwell OR single site visit <30s.
    # Intervention: Discovery-focused, exploratory content.

    EVALUATING = "evaluating"
    # Active comparison, information seeking.
    # Signal: Multiple page views, pricing page visit, competitor site visits.
    # Intervention: Evidence, comparison, social proof. Central-route arguments.

    INTENDING = "intending"
    # Decision made psychologically, action not taken.
    # Signal: Cart addition, booking start, email signup, return visit >2x.
    # Intervention: Implementation intentions, friction removal, urgency.

    STALLED = "stalled"
    # Was INTENDING but failed to act. The intention-behavior gap.
    # Signal: Cart abandonment, booking abandonment, 48h+ since last
    #         INTENDING signal.
    # Intervention: Ownership reactivation, loss framing, if-then prompts.

    CONVERTED = "converted"
    # Purchase complete.
    # Signal: Conversion pixel fire.
    # Intervention: STOP all retargeting. Switch to retention track.


class RuptureType(str, Enum):
    """Safran & Muran rupture typology adapted for digital.

    From therapeutic alliance research (Eubanks et al., 2018): successful
    rupture resolution (d=.62) produces outcomes AT LEAST as strong as
    frictionless journeys. Detection is the hard part.
    """

    WITHDRAWAL = "withdrawal"
    # Movements AWAY: declining engagement, longer inter-visit gaps,
    # reduced email opens, ad blindness (impressions without clicks).
    # Detection: Engagement velocity < 0.3 x rolling average.
    # Repair: Changed-mechanism creative. Do NOT acknowledge withdrawal
    # explicitly (clinical evidence: self-disclosure ineffective).

    CONFRONTATION = "confrontation"
    # Movements AGAINST: unsubscribe, negative review, social complaint,
    # explicit feedback.
    # Detection: Explicit negative signal.
    # Repair: Transparent acknowledgment + changed approach.

    DECAY = "decay"
    # Gradual disengagement without clear trigger.
    # Detection: Time since last engagement > 2x median for archetype.
    # Repair: Re-engagement with novel content. Reset narrative arc.

    NONE = "none"
    # No rupture detected. Continue current sequence.


class ScaffoldLevel(int, Enum):
    """Wood/Bruner/Ross scaffolding levels mapped to retargeting.

    From Belland et al. (2017), k=144: computer-based scaffolding g=0.46
    (between-subjects). Scaffolding that both fades AND adds new content
    produces strongest effects.
    """

    RECRUITMENT = 1
    # Function: Capture attention, build task commitment
    # Message type: Brand awareness, identity alignment
    # Construal: Abstract (why)
    # Processing: System 1 (fluency, mere exposure)

    SIMPLIFICATION = 2
    # Function: Reduce value proposition to essentials
    # Message type: Core benefit, single differentiator
    # Construal: Abstract -> Concrete transition
    # Processing: System 1 -> 2 bridge (introduce novel claim)

    DIRECTION_MAINTENANCE = 3
    # Function: Keep prospect on conversion path
    # Message type: Reminder, narrative continuation, social proof
    # Construal: Concrete (how)
    # Processing: System 2 (central route arguments survive PK)

    FRUSTRATION_CONTROL = 4
    # Function: Address objections, reduce perceived complexity
    # Message type: Objection handling, risk mitigation, guarantee
    # Construal: Concrete (specifics)
    # Processing: System 2 (coping planning)

    DEMONSTRATION = 5
    # Function: Show product in use via matched testimonial
    # Message type: Vicarious experience, case study
    # Construal: Concrete (vivid scenario)
    # Processing: System 1 (narrative transportation)


class BarrierCategory(str, Enum):
    """Top-level barrier categories derived from bilateral alignment gaps.

    Each barrier maps to one or more bilateral alignment dimensions that
    fell below the conversion threshold for a specific archetype. The
    mapping is in DIMENSION_BARRIER_MAP in adam/constants.py.
    """

    TRUST_DEFICIT = "trust_deficit"
    # brand_trust_fit below threshold

    REGULATORY_MISMATCH = "regulatory_mismatch"
    # regulatory_fit_score below threshold (wrong gain/loss framing)

    PROCESSING_OVERLOAD = "processing_overload"
    # processing_route_match below threshold (messaging too complex)

    EMOTIONAL_DISCONNECT = "emotional_disconnect"
    # emotional_resonance below threshold (messaging felt transactional)

    PRICE_FRICTION = "price_friction"
    # anchor_susceptibility_match + spending_pain_match below threshold

    MOTIVE_MISMATCH = "motive_mismatch"
    # evolutionary_motive_match below threshold (wrong need addressed)

    NEGATIVITY_BLOCK = "negativity_block"
    # negativity_bias_match above threshold (negative info weight too high)

    REACTANCE_TRIGGERED = "reactance_triggered"
    # persuasion_reactance_match above threshold (felt pushed)

    IDENTITY_MISALIGNMENT = "identity_misalignment"
    # personality_brand_alignment below threshold

    INTENTION_ACTION_GAP = "intention_action_gap"
    # All alignment scores adequate but no conversion (Gollwitzer gap)


class TherapeuticMechanism(str, Enum):
    """Mechanisms available for barrier resolution.

    Each maps to a research domain from Enhancement #33. The mapping from
    barrier to candidate mechanisms is in BARRIER_MECHANISM_CANDIDATES
    in adam/constants.py.
    """

    EVIDENCE_PROOF = "evidence_proof"                        # Domain 3: Scaffolding
    NARRATIVE_TRANSPORTATION = "narrative_transportation"    # Domain 5: Green & Brock
    SOCIAL_PROOF_MATCHED = "social_proof_matched"            # Domain 12: Bandura
    AUTONOMY_RESTORATION = "autonomy_restoration"            # Domain 8: SDT
    CONSTRUAL_SHIFT = "construal_shift"                      # Domain 9: CLT
    OWNERSHIP_REACTIVATION = "ownership_reactivation"        # Domain 10: Endowment
    IMPLEMENTATION_INTENTION = "implementation_intention"    # Domain 14: Gollwitzer
    MICRO_COMMITMENT = "micro_commitment"                    # Domain 6: FITD
    DISSONANCE_ACTIVATION = "dissonance_activation"          # Domain 11: Festinger
    LOSS_FRAMING = "loss_framing"                            # Domain 10: Loss aversion
    ANXIETY_RESOLUTION = "anxiety_resolution"                # Domain 2: Rupture repair
    FRUSTRATION_CONTROL = "frustration_control"              # Domain 3: Scaffolding
    NOVELTY_DISRUPTION = "novelty_disruption"                # Domain 13: Dual process
    VIVID_SCENARIO = "vivid_scenario"                        # Domain 5: Transportation
    PRICE_ANCHOR = "price_anchor"                            # Domain 9: CLT concrete
    CLAUDE_ARGUMENT = "claude_argument"                      # Domain 16: LLM-generated
    # CLAUDE_ARGUMENT is the most powerful mechanism. Unlike all others which
    # select from pre-existing creative templates, this generates a NOVEL
    # factual argument tailored to the specific barrier x personality x touch
    # history. Exploits Salvi (2024) finding that LLM persuasion derives from
    # factual argument quality, and Bozdag (2025) finding that multi-turn
    # coherence amplifies effectiveness. ~500ms latency (Claude API call).
