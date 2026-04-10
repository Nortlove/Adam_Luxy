"""
DSP Enrichment Engine — Causal/Inferential Edge Registry
==========================================================

200+ causal edges merged from:
    - DSP engine original (50+ edges)
    - ADAM theory graph THEORETICAL_LINKS (60+ edges)
    - ADAM mechanism synergy/antagonism edges (18 edges)
    - ADAM atom-specific theoretical mappings (50+ edges)
    - ADAM coherence clusters (6 clusters)
    - ADAM 82 framework relationships

Categories:
    A. Decision Architecture (regulatory fit, construal, processing)
    B. Temporal Reasoning (circadian, fatigue, spacing)
    C. Social Influence (social proof, reactance, susceptibility)
    D. Personality → Creative Matching
    E. Evolutionary → Purchase Motivation
    F. Memory & Learning (spacing, mere exposure, peak-end)
    G. Embodied Cognition & Device
    H. Emotional Processing
    I. Contextual Modulation
    J. Vulnerability & Protection
    K. ADAM Theory Graph (NDF → State → Need → Mechanism)
    L. ADAM Mechanism Synergy/Antagonism
    M. ADAM Atom-Specific Mappings (cooperative, motivational, regret, asymmetry)

Each edge includes:
    - Source and target construct IDs
    - Mechanism type and reasoning type
    - Effect sizes with confidence
    - Boundary conditions
    - Creative implications
    - DSP operationalization guidance
"""

from adam.dsp.models import (
    EffectSize,
    ConfidenceLevel,
    ReasoningType,
    MechanismType,
    PsychologicalDomain,
    TemporalModulation,
    VulnerabilityType,
)
from typing import Any, Dict, List, Optional


def build_edge_registry() -> Dict[str, Dict[str, Any]]:
    """Build the complete causal/inferential edge registry."""
    edges: Dict[str, Dict[str, Any]] = {}

    def add_edge(
        edge_id: str,
        source: str,
        target: str,
        mechanism: MechanismType,
        reasoning_type: ReasoningType,
        direction: str = "",
        domain: PsychologicalDomain = PsychologicalDomain.DECISION_MAKING,
        description: str = "",
        effect_sizes: List[EffectSize] = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MODERATE,
        boundary_conditions: List[str] = None,
        creative_implications: Dict = None,
        temporal_modulation: TemporalModulation = None,
        vulnerability_flags: List[VulnerabilityType] = None,
        dsp_operationalization: str = "",
        required_signals: List[str] = None,
        citations: List[str] = None,
        adam_source: str = "",
    ):
        edges[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "mechanism": mechanism,
            "reasoning_type": reasoning_type,
            "direction": direction,
            "domain": domain,
            "description": description,
            "effect_sizes": effect_sizes or [],
            "confidence": confidence,
            "boundary_conditions": boundary_conditions or [],
            "creative_implications": creative_implications or {},
            "temporal_modulation": temporal_modulation,
            "vulnerability_flags": vulnerability_flags or [],
            "dsp_operationalization": dsp_operationalization,
            "required_signals": required_signals or [],
            "citations": citations or [],
            "adam_source": adam_source,
        }

    # =========================================================================
    # A. Decision Architecture — highest-value edges for DSP
    # =========================================================================

    add_edge("regulatory_fit_persuasion",
        source="promotion_focus", target="ad_effectiveness",
        mechanism=MechanismType.REGULATORY_FIT,
        reasoning_type=ReasoningType.CAUSAL,
        direction="fit_doubles_persuasion",
        description="Matching message frame to regulatory focus doubles persuasion. OR=2.0-6.0.",
        effect_sizes=[EffectSize("odds_ratio", 2.0, context="regulatory fit meta-analysis")],
        confidence=ConfidenceLevel.META_ANALYTIC,
        creative_implications={
            "promotion_fit": {"copy": "Gain-framed, aspirational", "cta": "Discover, Achieve, Get"},
            "prevention_fit": {"copy": "Loss-framed, security-oriented", "cta": "Protect, Secure, Don't miss"},
        },
        dsp_operationalization="Infer regulatory focus from search query language and content category. Match ad frame.",
        required_signals=["search_query_regulatory_focus", "content_category_frame_activation"],
        citations=["Cesario et al. (2004)", "Lee & Aaker (2004)", "Higgins (1997)"],
    )

    add_edge("construal_level_message_match",
        source="construal_level_state", target="message_effectiveness",
        mechanism=MechanismType.CONSTRUAL_MATCHING,
        reasoning_type=ReasoningType.CAUSAL,
        direction="match_increases_persuasion",
        description="Matching message abstraction to consumer construal level. g=0.475.",
        effect_sizes=[EffectSize("g", 0.475, context="construal match meta-analysis")],
        confidence=ConfidenceLevel.META_ANALYTIC,
        creative_implications={
            "abstract_match": {"copy": "Why-framing, values, benefits", "format": "percent_off"},
            "concrete_match": {"copy": "How-framing, features, specs", "format": "dollar_off"},
        },
        citations=["Trope & Liberman (2010)", "Kim et al. (2009)"],
    )

    add_edge("cognitive_load_processing_shift",
        source="cognitive_load_state", target="processing_mode",
        mechanism=MechanismType.DUAL_PROCESS_SHIFT,
        reasoning_type=ReasoningType.THRESHOLD,
        direction="high_load_shifts_peripheral",
        description="High cognitive load shifts processing from central to peripheral route.",
        effect_sizes=[EffectSize("r", 0.55, context="load → processing mode shift")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Petty & Cacioppo (1986)", "Sweller (1988)"],
    )

    add_edge("processing_fluency_truth_effect",
        source="processing_fluency_truth", target="perceived_truth",
        mechanism=MechanismType.PROCESSING_FLUENCY,
        reasoning_type=ReasoningType.CAUSAL,
        direction="fluency_increases_truth",
        description="Easy-to-process information feels more true and is preferred.",
        effect_sizes=[EffectSize("cohens_d", 0.42, context="fluency → truth judgment")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Reber & Schwarz (1999)", "Alter & Oppenheimer (2009)"],
    )

    add_edge("choice_overload_decision_paralysis",
        source="choice_overload", target="decision_deferral",
        mechanism=MechanismType.CHOICE_OVERLOAD,
        reasoning_type=ReasoningType.THRESHOLD,
        direction="excess_options_paralyze",
        description="Too many options lead to decision paralysis and satisfaction reduction.",
        effect_sizes=[EffectSize("cohens_d", 0.60, context="6 vs 24 jams experiment")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Iyengar & Lepper (2000)", "Schwartz (2004)"],
    )

    add_edge("ad_clutter_attention_destruction",
        source="ad_clutter_load", target="attention_level",
        mechanism=MechanismType.ATTENTION_COMPETITION,
        reasoning_type=ReasoningType.CAUSAL,
        direction="clutter_destroys_attention",
        description="Each additional ad reduces attention to every other ad. r=-0.55.",
        effect_sizes=[EffectSize("r", -0.55, context="ad density → per-ad attention")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Burke et al. (2005)", "Cho & Cheon (2004)"],
    )

    # =========================================================================
    # B. Temporal Reasoning
    # =========================================================================

    add_edge("circadian_persuasion_route",
        source="circadian_cognitive_capacity", target="processing_mode",
        mechanism=MechanismType.CIRCADIAN_MODULATION,
        reasoning_type=ReasoningType.TEMPORAL,
        direction="capacity_determines_route",
        description="Circadian capacity determines whether central or peripheral route is effective.",
        effect_sizes=[EffectSize("cohens_d", 0.65, context="synchrony effect on persuasion")],
        confidence=ConfidenceLevel.REPLICATED,
        temporal_modulation=TemporalModulation(circadian_peak_hours=[9, 10, 11], circadian_trough_hours=[14, 23, 0, 1, 2]),
        citations=["Bodenhausen (1990)", "Gunia et al. (2014)"],
    )

    add_edge("decision_fatigue_default_acceptance",
        source="decision_fatigue_state", target="default_acceptance",
        mechanism=MechanismType.DECISION_FATIGUE,
        reasoning_type=ReasoningType.CAUSAL,
        direction="fatigue_increases_defaults",
        description="Decision fatigue increases acceptance of defaults and simplest option.",
        effect_sizes=[EffectSize("r", 0.44, context="session length → default acceptance")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Danziger et al. (2011)", "Levav et al. (2010)"],
    )

    add_edge("spacing_effect_campaign",
        source="mere_exposure_effect", target="memory_encoding",
        mechanism=MechanismType.SPACING_EFFECT,
        reasoning_type=ReasoningType.TEMPORAL,
        direction="spaced_repetition_150pct_better",
        description="Spaced repetition yields 150% better recall than massed presentation.",
        effect_sizes=[EffectSize("cohens_d", 0.85, context="spacing effect on ad recall")],
        confidence=ConfidenceLevel.META_ANALYTIC,
        citations=["Cepeda et al. (2006)", "Sahni (2015)"],
    )

    add_edge("sleep_deprivation_vulnerability",
        source="sleep_deprivation_state", target="impulse_control",
        mechanism=MechanismType.SLEEP_DEPRIVATION,
        reasoning_type=ReasoningType.CAUSAL,
        direction="deprivation_impairs_control",
        description="Sleep deprivation impairs impulse control and risk assessment. ETHICAL: protect.",
        effect_sizes=[EffectSize("cohens_d", 0.85, context="sleep loss → impulsivity")],
        confidence=ConfidenceLevel.REPLICATED,
        vulnerability_flags=[VulnerabilityType.SLEEP_DEPRIVATION],
        citations=["Harrison & Horne (2000)", "Killgore et al. (2006)"],
    )

    add_edge("mind_wandering_peripheral_window",
        source="mind_wandering_state", target="narrative_effectiveness",
        mechanism=MechanismType.MIND_WANDERING,
        reasoning_type=ReasoningType.CONDITIONAL,
        direction="wandering_opens_peripheral",
        description="Mind-wandering opens window for peripheral and narrative processing.",
        effect_sizes=[EffectSize("r", 0.30, context="mind-wandering → peripheral susceptibility")],
        confidence=ConfidenceLevel.MODERATE,
        citations=["Smallwood & Schooler (2015)"],
    )

    # =========================================================================
    # C. Social Influence
    # =========================================================================

    add_edge("social_proof_dual_channel",
        source="social_proof_principle", target="decision_confidence",
        mechanism=MechanismType.SOCIAL_PROOF,
        reasoning_type=ReasoningType.CAUSAL,
        direction="proof_increases_confidence",
        description="Social proof operates through both informational (what to think) and normative (what to do) channels.",
        effect_sizes=[EffectSize("r", 0.42, context="social proof → conversion")],
        confidence=ConfidenceLevel.META_ANALYTIC,
        citations=["Cialdini (2009)", "Goldstein et al. (2008)"],
    )

    add_edge("reactance_controlling_language",
        source="reactance", target="persuasion_resistance",
        mechanism=MechanismType.REACTANCE,
        reasoning_type=ReasoningType.CAUSAL,
        direction="control_triggers_resistance",
        description="Controlling language ('you must', 'don't miss') triggers reactance. d=-0.40.",
        effect_sizes=[EffectSize("cohens_d", -0.40, context="controlling language → reactance")],
        confidence=ConfidenceLevel.REPLICATED,
        creative_implications={"avoid": ["you must", "don't miss", "act now or else", "limited time only"]},
        citations=["Brehm (1966)", "Quick & Stephenson (2007)"],
    )

    # =========================================================================
    # D. Personality → Creative Matching
    # =========================================================================

    add_edge("big5_ad_creative_matching",
        source="openness", target="creative_preference",
        mechanism=MechanismType.TRAIT_MATCHING,
        reasoning_type=ReasoningType.CAUSAL,
        direction="personality_match_increases_conversion",
        description="Matching creative to Big Five personality yields +40-50% conversion improvement.",
        effect_sizes=[EffectSize("r", 0.35, context="personality-targeted ads, Matz et al. 2017")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Matz et al. (2017) PNAS", "Hirsh et al. (2012)"],
    )

    add_edge("need_for_cognition_argument_depth",
        source="need_for_cognition", target="argument_processing",
        mechanism=MechanismType.ELABORATION_LIKELIHOOD,
        reasoning_type=ReasoningType.MODERATIONAL,
        direction="nfc_moderates_argument_effect",
        description="High NFC consumers elaborate more on argument quality. Low NFC rely on heuristics.",
        effect_sizes=[EffectSize("r", 0.42, context="NFC × argument quality interaction")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Petty & Cacioppo (1986)", "Cacioppo et al. (1996)"],
    )

    # =========================================================================
    # E. Evolutionary → Purchase Motivation
    # =========================================================================

    add_edge("costly_signal_luxury_price",
        source="costly_signaling", target="willingness_to_pay",
        mechanism=MechanismType.COSTLY_SIGNALING,
        reasoning_type=ReasoningType.CAUSAL,
        direction="status_increases_wtp",
        description="Status-motivated consumers willing to pay premium as honest costly signal.",
        effect_sizes=[EffectSize("r", 0.38, context="status motivation → luxury WTP")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Griskevicius et al. (2007)", "Sundie et al. (2011)"],
    )

    add_edge("moral_licensing_indulgence",
        source="moral_licensing", target="indulgence_behavior",
        mechanism=MechanismType.MORAL_LICENSING,
        reasoning_type=ReasoningType.CAUSAL,
        direction="virtue_licenses_indulgence",
        description="Prior virtuous behavior licenses subsequent self-indulgent purchases.",
        effect_sizes=[EffectSize("cohens_d", 0.31, context="moral licensing meta-analysis")],
        confidence=ConfidenceLevel.MODERATE,
        citations=["Blanken et al. (2015)"],
    )

    # =========================================================================
    # F. Memory & Learning
    # =========================================================================

    add_edge("peak_end_video_memory",
        source="peak_end_rule", target="memory_trace",
        mechanism=MechanismType.PEAK_END_RULE,
        reasoning_type=ReasoningType.CAUSAL,
        direction="peak_and_end_determine_memory",
        description="Video ad memory determined by emotional peak and final moments.",
        effect_sizes=[EffectSize("r", 0.48, context="peak-end → ad recall")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Kahneman et al. (1993)", "Do et al. (2008)"],
    )

    add_edge("narrative_transportation_skepticism_bypass",
        source="narrative_transportation_state", target="persuasion_resistance",
        mechanism=MechanismType.NARRATIVE_TRANSPORTATION,
        reasoning_type=ReasoningType.INHIBITORY,
        direction="transportation_reduces_resistance",
        description="Story immersion reduces counterarguing and ad skepticism.",
        effect_sizes=[EffectSize("r", 0.34, context="transportation → reduced counterarguing")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Green & Brock (2000)", "Van Laer et al. (2014)"],
    )

    add_edge("mere_exposure_low_attention",
        source="mere_exposure_effect", target="brand_preference",
        mechanism=MechanismType.MERE_EXPOSURE,
        reasoning_type=ReasoningType.CAUSAL,
        direction="repetition_increases_liking",
        description="Mere exposure increases liking even at low attention. Optimal: 10-20 exposures.",
        effect_sizes=[EffectSize("r", 0.26, context="mere exposure → liking meta-analysis")],
        confidence=ConfidenceLevel.META_ANALYTIC,
        citations=["Zajonc (1968)", "Bornstein (1989)"],
    )

    add_edge("prediction_error_engagement",
        source="prediction_error_state", target="engagement_intensity",
        mechanism=MechanismType.PREDICTION_ERROR,
        reasoning_type=ReasoningType.CAUSAL,
        direction="moderate_pe_maximizes_engagement",
        description="Moderate prediction error maximizes engagement. Too much is aversive.",
        effect_sizes=[EffectSize("r", 0.40, context="surprise → engagement, inverted-U")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Schultz (1997)", "Barto et al. (2013)"],
    )

    # =========================================================================
    # G. Embodied Cognition & Device
    # =========================================================================

    add_edge("touchscreen_ownership_endowment",
        source="endowment_effect", target="willingness_to_pay",
        mechanism=MechanismType.ENDOWMENT_EFFECT,
        reasoning_type=ReasoningType.CAUSAL,
        direction="touch_increases_ownership",
        description="Touching products on touchscreen increases perceived ownership and WTP.",
        effect_sizes=[EffectSize("cohens_d", 0.58, context="touchscreen → WTP increase")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Brasel & Gips (2014)", "Shen et al. (2016)"],
    )

    add_edge("device_processing_mode_shift",
        source="device_processing_mode", target="processing_mode",
        mechanism=MechanismType.DUAL_PROCESS_SHIFT,
        reasoning_type=ReasoningType.CONTEXTUAL_MODERATION,
        direction="mobile_shifts_to_system1",
        description="Mobile device use shifts processing toward System 1.",
        effect_sizes=[EffectSize("cohens_d", 0.42, context="mobile vs desktop processing")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Ghose et al. (2019)", "Melumad & Pham (2020)"],
    )

    # =========================================================================
    # H. Emotional Processing
    # =========================================================================

    add_edge("mood_congruency_spillover",
        source="mood_congruency_state", target="ad_evaluation",
        mechanism=MechanismType.MOOD_CONGRUENCY,
        reasoning_type=ReasoningType.CAUSAL,
        direction="mood_spills_to_ad",
        description="Content-induced mood transfers to ad evaluation.",
        effect_sizes=[EffectSize("r", 0.34, context="mood → ad attitude")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Forgas (1995)", "De Pelsmacker et al. (2002)"],
    )

    add_edge("fear_appeal_efficacy_requirement",
        source="fear_state", target="behavior_change",
        mechanism=MechanismType.FEAR_APPEAL,
        reasoning_type=ReasoningType.CONDITIONAL,
        direction="fear_plus_efficacy_changes_behavior",
        description="Fear appeals only work when paired with self-efficacy and response efficacy.",
        effect_sizes=[EffectSize("r", 0.29, context="fear × efficacy → behavior change")],
        confidence=ConfidenceLevel.META_ANALYTIC,
        boundary_conditions=["Requires self-efficacy. Without efficacy, fear → avoidance/denial."],
        citations=["Witte & Allen (2000)", "Tannenbaum et al. (2015)"],
    )

    # =========================================================================
    # I. Contextual Modulation
    # =========================================================================

    add_edge("content_frame_psychological_activation",
        source="content_frame_activation", target="regulatory_focus_priming",
        mechanism=MechanismType.PRIMING,
        reasoning_type=ReasoningType.CONTEXTUAL_MODERATION,
        direction="content_primes_focus",
        description="Content category activates corresponding regulatory focus. ~15min priming effect.",
        effect_sizes=[EffectSize("r", 0.38, context="content frame → regulatory focus activation")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Higgins (1997)", "Lee & Aaker (2004)"],
    )

    add_edge("scarcity_product_type_interaction",
        source="scarcity_principle", target="purchase_urgency",
        mechanism=MechanismType.SCARCITY,
        reasoning_type=ReasoningType.MODERATIONAL,
        direction="scarcity_moderated_by_type",
        description="Scarcity more effective for hedonic than utilitarian products.",
        effect_sizes=[EffectSize("r", 0.33, context="scarcity × product type")],
        confidence=ConfidenceLevel.REPLICATED,
        citations=["Aggarwal et al. (2011)"],
    )

    # =========================================================================
    # J. Vulnerability & Protection
    # =========================================================================

    add_edge("vulnerability_detection_protection",
        source="vulnerability_cognitive_depletion", target="ethical_override",
        mechanism=MechanismType.ETHICAL_OVERRIDE,
        reasoning_type=ReasoningType.ETHICAL_BOUNDARY,
        direction="vulnerability_triggers_protection",
        description="Detected vulnerability triggers ethical protection protocols.",
        confidence=ConfidenceLevel.HIGH,
        vulnerability_flags=[VulnerabilityType.COGNITIVE_DEPLETION, VulnerabilityType.SLEEP_DEPRIVATION],
        adam_source="EthicalBoundaryEngine",
    )

    add_edge("cognitive_depletion_exploitation_risk",
        source="cognitive_load_state", target="vulnerability_cognitive_depletion",
        mechanism=MechanismType.COGNITIVE_DEPLETION,
        reasoning_type=ReasoningType.THRESHOLD,
        direction="high_load_creates_vulnerability",
        description="Sustained high cognitive load creates exploitation vulnerability.",
        confidence=ConfidenceLevel.REPLICATED,
        vulnerability_flags=[VulnerabilityType.COGNITIVE_DEPLETION],
        citations=["Baumeister et al. (1998)"],
    )

    # =========================================================================
    # K. ADAM Theory Graph — NDF → State → Need → Mechanism
    # =========================================================================

    # CREATES_NEED: State → Need
    creates_need_edges = [
        ("low_uncertainty_tolerance", "need_for_closure", 0.85, "Webster & Kruglanski (1994)"),
        ("low_uncertainty_tolerance", "need_for_safety", 0.70, "Jost et al. (2003)"),
        ("high_cognitive_engagement", "competence_need", 0.65, "Petty & Cacioppo (1986)"),
        ("low_cognitive_engagement", "need_for_closure", 0.80, "Kruglanski (2004)"),
        ("high_social_calibration", "relatedness_need", 0.85, "Cialdini (2009)"),
        ("high_social_calibration", "need_for_belonging", 0.75, "Baumeister & Leary (1995)"),
        ("high_status_sensitivity", "costly_signaling", 0.85, "Griskevicius et al. (2007)"),
        ("high_status_sensitivity", "need_for_uniqueness", 0.70, "Tian et al. (2001)"),
        ("high_approach", "stimulation_value", 0.70, "Carver & White (1994)"),
        ("high_avoidance", "security_value", 0.85, "Gray (1970)"),
        ("high_avoidance", "need_for_closure", 0.80, "Neuberg & Newsom (1993)"),
        ("high_arousal_seeking", "stimulation_value", 0.85, "Zuckerman (1979)"),
        ("low_arousal_seeking", "commitment_consistency_principle", 0.65, "Zuckerman (1979)"),
        ("short_temporal_horizon", "present_bias", 0.85, "Frederick et al. (2002)"),
        ("long_temporal_horizon", "future_self_continuity", 0.65, "Hershfield (2011)"),
        ("low_social_calibration", "autonomy_need", 0.75, "Deci & Ryan (2000)"),
        ("high_uncertainty_tolerance", "stimulation_value", 0.60, "Sorrentino & Short (1986)"),
    ]
    for source, target, strength, citation in creates_need_edges:
        eid = f"creates_need_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.APPROACH_AVOIDANCE,
            reasoning_type=ReasoningType.CREATES_NEED,
            direction=f"{source}_creates_{target}",
            description=f"NDF state {source} creates need {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context=f"theory: {citation}")],
            confidence=ConfidenceLevel.REPLICATED,
            citations=[citation],
            adam_source="theory_schema.py THEORETICAL_LINKS",
        )

    # SATISFIED_BY: Need → Mechanism
    satisfied_by_edges = [
        ("need_for_closure", "authority", 0.80, "Kruglanski (2004)"),
        ("need_for_closure", "social_proof", 0.75, "Cialdini (2009)"),
        ("need_for_closure", "commitment_consistency", 0.70, "Kruglanski & Webster (1996)"),
        ("need_for_safety", "commitment_consistency", 0.75, "Cialdini (2009)"),
        ("need_for_closure", "social_proof", 0.80, "Petty & Cacioppo (1986)"),
        ("relatedness_need", "social_proof", 0.90, "Cialdini (2009)"),
        ("relatedness_need", "mimetic_desire", 0.75, "Girard (1961)"),
        ("need_for_belonging", "unity", 0.85, "Cialdini (2021)"),
        ("costly_signaling", "identity_construction", 0.80, "Griskevicius et al. (2007)"),
        ("costly_signaling", "scarcity", 0.75, "Griskevicius et al. (2007)"),
        ("costly_signaling", "mimetic_desire", 0.70, "Girard (1961)"),
        ("stimulation_value", "attention_dynamics", 0.75, "Zuckerman (1979)"),
        ("stimulation_value", "embodied_cognition", 0.65, "Barsalou (2008)"),
        ("security_value", "commitment_consistency", 0.75, "Cialdini (2009)"),
        ("security_value", "authority", 0.70, "Cialdini (2009)"),
        ("present_bias", "scarcity", 0.80, "Frederick et al. (2002)"),
        ("present_bias", "attention_dynamics", 0.65, "Frederick et al. (2002)"),
        ("future_self_continuity", "identity_construction", 0.85, "Hershfield (2011)"),
        ("autonomy_need", "identity_construction", 0.75, "Deci & Ryan (2000)"),
        ("autonomy_need", "storytelling", 0.70, "Ryan & Deci (2017)"),
        ("competence_need", "authority", 0.65, "Deci & Ryan (2000)"),
        ("commitment_consistency_principle", "commitment_consistency", 0.85, "Cialdini (2009)"),
    ]
    for source, target, strength, citation in satisfied_by_edges:
        eid = f"satisfied_by_{source}__{target}"
        mech = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=source, target=target,
            mechanism=mech,
            reasoning_type=ReasoningType.SATISFIED_BY,
            direction=f"{source}_satisfied_by_{target}",
            description=f"Need {source} is satisfied by mechanism {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context=f"theory: {citation}")],
            confidence=ConfidenceLevel.REPLICATED,
            citations=[citation],
            adam_source="theory_schema.py THEORETICAL_LINKS",
        )

    # =========================================================================
    # L. ADAM Mechanism Synergy/Antagonism
    # =========================================================================

    synergy_pairs = [
        ("authority", "social_proof", 0.7, "Expert social proof combines information and normative channels"),
        ("authority", "commitment_consistency", 0.6, "Authority reduces commitment uncertainty"),
        ("social_proof", "liking", 0.65, "Liked sources provide stronger social proof"),
        ("scarcity", "commitment_consistency", 0.6, "Scarcity strengthens commitment urgency"),
        ("reciprocity", "liking", 0.7, "Reciprocity builds liking; liking enhances reciprocity"),
        ("commitment_consistency", "social_proof", 0.5, "Public commitment + social validation"),
        ("novelty", "authority", 0.5, "Novel claims from authority carry extra weight"),
        ("identity_construction", "mimetic_desire", 1.4, "Identity activated by mimetic social comparison"),
        ("storytelling", "temporal_construal", 1.3, "Narrative framing aligns with temporal perspective"),
        ("automatic_evaluation", "attention_dynamics", 1.3, "Pre-conscious evaluation captures attention"),
        ("wanting_liking", "evolutionary_adaptations", 1.35, "Desire mechanisms amplify evolutionary triggers"),
    ]
    for source, target, strength, desc in synergy_pairs:
        eid = f"synergy_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.MECHANISM_SYNERGY,
            reasoning_type=ReasoningType.SYNERGISTIC,
            direction=f"{source}_synergizes_with_{target}",
            description=desc,
            effect_sizes=[EffectSize("r", strength, context="mechanism synergy")],
            confidence=ConfidenceLevel.FIELD_VALIDATED,
            adam_source="graph_intelligence.py SYNERGIZES_WITH",
        )

    antagonism_pairs = [
        ("scarcity", "reciprocity", 0.4, "Scarcity pressure undermines reciprocity goodwill"),
        ("automatic_evaluation", "identity_construction", 0.7, "Deliberative identity processing overrides automatic"),
        ("evolutionary_adaptations", "automatic_evaluation", 0.75, "Conscious override suppresses evolutionary triggers"),
    ]
    for source, target, strength, desc in antagonism_pairs:
        eid = f"antagonism_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.MECHANISM_INTERFERENCE,
            reasoning_type=ReasoningType.ANTAGONISTIC,
            direction=f"{source}_antagonizes_{target}",
            description=desc,
            effect_sizes=[EffectSize("r", -strength, context="mechanism antagonism")],
            confidence=ConfidenceLevel.FIELD_VALIDATED,
            adam_source="graph_intelligence.py ANTAGONIZES",
        )

    # =========================================================================
    # M. ADAM Atom-Specific Mappings
    # =========================================================================

    # Cooperative Framing → Mechanism boosts
    coop_edges = [
        ("problem_solving", "reciprocity", 0.15), ("problem_solving", "commitment_consistency", 0.10),
        ("identity_enhancement", "identity_construction", 0.20), ("identity_enhancement", "mimetic_desire", 0.10),
        ("community_belonging", "unity", 0.20), ("community_belonging", "social_proof", 0.15),
        ("knowledge_sharing", "authority", 0.15), ("knowledge_sharing", "reciprocity", 0.15),
        ("empathy_alignment", "reciprocity", 0.20), ("empathy_alignment", "unity", 0.15),
    ]
    for source, target, boost in coop_edges:
        eid = f"cooperative_{source}__{target}"
        mech = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=f"cooperative_{source}", target=target,
            mechanism=mech,
            reasoning_type=ReasoningType.COOPERATIVE,
            direction=f"cooperative_{source}_boosts_{target}",
            description=f"Cooperative framing mode {source} boosts {target} by {boost}",
            effect_sizes=[EffectSize("r", boost, context="CooperativeFramingAtom")],
            confidence=ConfidenceLevel.ATOM_INFERRED,
            adam_source="CooperativeFramingAtom",
        )

    # Motivational Conflict → Mechanism adjustments
    conflict_edges = [
        ("approach_dominant", "scarcity", 0.15), ("approach_dominant", "commitment_consistency", 0.15),
        ("avoidance_dominant", "commitment_consistency", 0.20), ("avoidance_dominant", "authority", 0.15),
        ("avoidance_dominant", "social_proof", 0.15),
        ("balanced_conflict", "identity_construction", 0.15), ("balanced_conflict", "social_proof", 0.10),
        ("double_approach", "anchoring", 0.20), ("double_approach", "identity_construction", 0.15),
        ("double_avoidance", "regulatory_focus", 0.20), ("double_avoidance", "commitment_consistency", 0.15),
    ]
    for source, target, boost in conflict_edges:
        eid = f"conflict_{source}__{target}"
        mech = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=f"motivational_conflict_{source}", target=target,
            mechanism=mech,
            reasoning_type=ReasoningType.MODERATIONAL,
            direction=f"conflict_{source}_modulates_{target}",
            description=f"Motivational conflict type {source} modulates {target} by {boost}",
            effect_sizes=[EffectSize("r", boost, context="MotivationalConflictAtom")],
            confidence=ConfidenceLevel.ATOM_INFERRED,
            adam_source="MotivationalConflictAtom",
        )

    # Regret Anticipation → Mechanism adjustments
    regret_edges = [
        ("inaction_dominant", "scarcity", 0.20), ("inaction_dominant", "social_proof", 0.15),
        ("inaction_dominant", "mimetic_desire", 0.15),
        ("action_dominant", "commitment_consistency", 0.20), ("action_dominant", "authority", 0.15),
    ]
    for source, target, boost in regret_edges:
        eid = f"regret_{source}__{target}"
        mech = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=f"regret_anticipation_{source}", target=target,
            mechanism=mech,
            reasoning_type=ReasoningType.MODERATIONAL,
            direction=f"regret_{source}_boosts_{target}",
            description=f"Regret anticipation ({source}) boosts {target} by {boost}",
            effect_sizes=[EffectSize("r", boost, context="RegretAnticipationAtom")],
            confidence=ConfidenceLevel.ATOM_INFERRED,
            adam_source="RegretAnticipationAtom",
        )

    # Information Asymmetry → Mechanism adjustments
    asymmetry_edges = [
        ("search_good", "anchoring", 0.15), ("search_good", "identity_construction", 0.10),
        ("experience_good", "social_proof", 0.20), ("experience_good", "reciprocity", 0.15),
        ("experience_good", "storytelling", 0.10),
        ("credence_good", "authority", 0.25), ("credence_good", "commitment_consistency", 0.15),
    ]
    for source, target, boost in asymmetry_edges:
        eid = f"asymmetry_{source}__{target}"
        mech = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=f"information_asymmetry_{source}", target=target,
            mechanism=mech,
            reasoning_type=ReasoningType.MODERATIONAL,
            direction=f"asymmetry_{source}_boosts_{target}",
            description=f"Information asymmetry type {source} boosts {target} by {boost}",
            effect_sizes=[EffectSize("r", boost, context="InformationAsymmetryAtom")],
            confidence=ConfidenceLevel.ATOM_INFERRED,
            adam_source="InformationAsymmetryAtom",
        )

    # Coherence clusters (implicit synergy groups)
    clusters = {
        "urgency_cluster": ["scarcity", "attention_dynamics", "temporal_construal"],
        "trust_cluster": ["authority", "social_proof", "commitment_consistency"],
        "identity_cluster": ["identity_construction", "mimetic_desire", "embodied_cognition"],
        "patience_cluster": ["commitment_consistency", "authority", "regulatory_focus"],
        "autonomy_cluster": ["identity_construction", "storytelling", "embodied_cognition", "reciprocity"],
        "social_cluster": ["social_proof", "mimetic_desire", "unity"],
    }
    for cluster_name, mechanisms in clusters.items():
        for i, m1 in enumerate(mechanisms):
            for m2 in mechanisms[i + 1:]:
                eid = f"cluster_{cluster_name}_{m1}__{m2}"
                add_edge(eid,
                    source=m1, target=m2,
                    mechanism=MechanismType.MECHANISM_SYNERGY,
                    reasoning_type=ReasoningType.SYNERGISTIC,
                    direction=f"{m1}_coherent_with_{m2}",
                    description=f"Coherence cluster {cluster_name}: {m1} and {m2} reinforce each other",
                    effect_sizes=[EffectSize("r", 0.3, context=f"coherence cluster {cluster_name}")],
                    confidence=ConfidenceLevel.ATOM_INFERRED,
                    adam_source=f"CoherenceOptimizationAtom {cluster_name}",
                )

    # =========================================================================
    # N. ALIGNMENT MATRIX STRUCTURAL EDGES (7 matrices, highest-value cells)
    # =========================================================================

    # N1. MOTIVATION_VALUE_ALIGNMENT: motivation → value proposition
    motivation_value_edges = [
        ("status_signaling_mot", "vp_status_prestige", 0.95), ("belonging_affirmation", "vp_belonging_connection", 0.95),
        ("self_expression", "vp_self_expression", 0.90), ("problem_solving_mot", "vp_convenience_ease", 0.90),
        ("quality_assurance", "vp_reliability_durability", 0.90), ("risk_mitigation", "vp_peace_of_mind", 0.90),
        ("cost_minimization", "vp_cost_efficiency", 0.90), ("excitement_seeking", "vp_novelty_innovation", 0.85),
        ("personal_growth", "vp_transformation", 0.85), ("mastery_seeking", "vp_knowledge_expertise", 0.85),
        ("sensory_pleasure", "vp_pleasure_enjoyment", 0.85), ("efficiency_optimization", "vp_performance_superiority", 0.85),
        ("altruistic_giving", "vp_social_responsibility", 0.85), ("future_self_investment", "vp_transformation", 0.80),
        ("nostalgia_comfort", "vp_belonging_connection", 0.75), ("anxiety_reduction", "vp_peace_of_mind", 0.85),
        ("goal_achievement", "vp_performance_superiority", 0.80), ("social_approval", "vp_status_prestige", 0.80),
        ("uniqueness_differentiation", "vp_self_expression", 0.80), ("immediate_gratification", "vp_pleasure_enjoyment", 0.85),
        ("delayed_gratification", "vp_transformation", 0.75), ("scarcity_response", "vp_novelty_innovation", 0.70),
        ("pure_curiosity", "vp_knowledge_expertise", 0.90), ("escapism", "vp_pleasure_enjoyment", 0.80),
        ("relationship_maintenance", "vp_belonging_connection", 0.85), ("authority_compliance", "vp_reliability_durability", 0.75),
    ]
    for source, target, strength in motivation_value_edges:
        eid = f"aligns_motivation_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.REGULATORY_FIT,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_aligns_with_{target}",
            domain=PsychologicalDomain.CONSUMER_BEHAVIOR,
            description=f"Motivation {source} aligns with value proposition {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context="MOTIVATION_VALUE_ALIGNMENT matrix")],
            confidence=ConfidenceLevel.REPLICATED,
            adam_source="customer_ad_alignment.py MOTIVATION_VALUE_ALIGNMENT",
        )

    # N2. DECISION_STYLE_LINGUISTIC_ALIGNMENT: decision style → linguistic style
    ds_ling_edges = [
        ("ds_gut_instinct", "ls_emotional", 0.85), ("ds_gut_instinct", "ls_minimalist", 0.80),
        ("ds_recognition_based", "ls_conversational", 0.80), ("ds_affect_driven", "ls_emotional", 0.90),
        ("ds_affect_driven", "ls_storytelling", 0.85), ("ds_satisficing", "ls_minimalist", 0.85),
        ("ds_satisficing", "ls_conversational", 0.80), ("ds_heuristic_based", "ls_urgent", 0.80),
        ("ds_social_referencing", "ls_conversational", 0.85), ("ds_authority_deferring", "ls_professional", 0.85),
        ("ds_authority_deferring", "ls_technical", 0.75), ("ds_maximizing", "ls_technical", 0.90),
        ("ds_analytical_systematic", "ls_technical", 0.90), ("ds_analytical_systematic", "ls_professional", 0.85),
        ("ds_risk_calculating", "ls_professional", 0.85), ("ds_risk_calculating", "ls_technical", 0.80),
        ("ds_deliberative_reflective", "ls_storytelling", 0.80), ("ds_deliberative_reflective", "ls_professional", 0.75),
        ("ds_consensus_building", "ls_conversational", 0.85), ("ds_consensus_building", "ls_professional", 0.75),
    ]
    for source, target, strength in ds_ling_edges:
        eid = f"aligns_style_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.ELABORATION_LIKELIHOOD,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_responds_to_{target}",
            domain=PsychologicalDomain.CREATIVE_PSYCHOLOGY,
            description=f"Decision style {source} responds best to {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context="DECISION_STYLE_LINGUISTIC_ALIGNMENT matrix")],
            confidence=ConfidenceLevel.REPLICATED,
            adam_source="customer_ad_alignment.py DECISION_STYLE_LINGUISTIC_ALIGNMENT",
        )

    # N3. REGULATORY_EMOTIONAL_ALIGNMENT: regulatory focus → emotional appeal
    reg_emo_edges = [
        ("rf_eager_advancement", "excitement_state", 0.90), ("rf_eager_advancement", "pride_state", 0.85),
        ("rf_aspiration_driven", "pride_state", 0.85), ("rf_aspiration_driven", "excitement_state", 0.80),
        ("rf_optimistic_exploration", "surprise_state", 0.85), ("rf_optimistic_exploration", "curiosity_state", 0.80),
        ("rf_pragmatic_balanced", "contentment_state", 0.80), ("rf_pragmatic_balanced", "pride_state", 0.70),
        ("rf_vigilant_security", "contentment_state", 0.85), ("rf_vigilant_security", "fear_state", 0.70),
        ("rf_conservative_preservation", "contentment_state", 0.80), ("rf_conservative_preservation", "nostalgia_state", 0.75),
        ("rf_anxious_avoidance", "fear_state", 0.85), ("rf_anxious_avoidance", "anxiety_state", 0.80),
    ]
    for source, target, strength in reg_emo_edges:
        eid = f"aligns_regemo_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.REGULATORY_FIT,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_resonates_with_{target}",
            domain=PsychologicalDomain.AFFECT_REGULATION,
            description=f"Regulatory focus {source} resonates with emotion {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context="REGULATORY_EMOTIONAL_ALIGNMENT matrix")],
            confidence=ConfidenceLevel.REPLICATED,
            adam_source="customer_ad_alignment.py REGULATORY_EMOTIONAL_ALIGNMENT",
        )

    # N4. ARCHETYPE_PERSONALITY_ALIGNMENT: archetype → brand personality
    arch_brand_edges = [
        ("explorer_archetype", "brand_excitement", 0.85), ("explorer_archetype", "brand_ruggedness", 0.70),
        ("achiever_archetype", "brand_competence", 0.90), ("achiever_archetype", "brand_sophistication", 0.70),
        ("connector_archetype", "brand_sincerity", 0.85), ("connector_archetype", "brand_excitement", 0.70),
        ("guardian_archetype", "brand_sincerity", 0.85), ("guardian_archetype", "brand_competence", 0.80),
        ("analyst_archetype", "brand_competence", 0.90), ("analyst_archetype", "brand_sophistication", 0.65),
        ("creator_archetype", "brand_excitement", 0.85), ("creator_archetype", "brand_sophistication", 0.75),
        ("nurturer_archetype", "brand_sincerity", 0.90), ("nurturer_archetype", "brand_competence", 0.65),
        ("pragmatist_archetype", "brand_competence", 0.85), ("pragmatist_archetype", "brand_sincerity", 0.70),
    ]
    for source, target, strength in arch_brand_edges:
        eid = f"aligns_archbrand_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.TRAIT_MATCHING,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_prefers_{target}",
            domain=PsychologicalDomain.BRAND_PSYCHOLOGY,
            description=f"Archetype {source} prefers brand personality {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context="ARCHETYPE_PERSONALITY_ALIGNMENT matrix")],
            confidence=ConfidenceLevel.REPLICATED,
            citations=["Aaker (1997)"],
            adam_source="customer_ad_alignment.py ARCHETYPE_PERSONALITY_ALIGNMENT",
        )

    # N5. MECHANISM_SUSCEPTIBILITY: decision style → mechanism
    mech_suscept_edges = [
        ("ds_gut_instinct", "scarcity", 0.85), ("ds_gut_instinct", "liking", 0.80),
        ("ds_affect_driven", "liking", 0.90), ("ds_affect_driven", "reciprocity", 0.75),
        ("ds_social_referencing", "social_proof", 0.90), ("ds_social_referencing", "unity", 0.80),
        ("ds_authority_deferring", "authority", 0.95), ("ds_authority_deferring", "commitment_consistency", 0.75),
        ("ds_maximizing", "authority", 0.80), ("ds_maximizing", "social_proof", 0.70),
        ("ds_analytical_systematic", "authority", 0.85), ("ds_analytical_systematic", "commitment_consistency", 0.75),
        ("ds_risk_calculating", "authority", 0.80), ("ds_risk_calculating", "commitment_consistency", 0.85),
        ("ds_heuristic_based", "social_proof", 0.85), ("ds_heuristic_based", "scarcity", 0.80),
        ("ds_satisficing", "social_proof", 0.80), ("ds_satisficing", "liking", 0.75),
        ("ds_consensus_building", "social_proof", 0.90), ("ds_consensus_building", "unity", 0.85),
        ("ds_deliberative_reflective", "commitment_consistency", 0.80), ("ds_deliberative_reflective", "authority", 0.75),
        ("ds_recognition_based", "liking", 0.85), ("ds_recognition_based", "social_proof", 0.75),
    ]
    for source, target, strength in mech_suscept_edges:
        eid = f"susceptible_{source}__{target}"
        mech = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=source, target=target,
            mechanism=mech,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_susceptible_to_{target}",
            domain=PsychologicalDomain.DECISION_MAKING,
            description=f"Decision style {source} is susceptible to mechanism {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context="MECHANISM_SUSCEPTIBILITY matrix")],
            confidence=ConfidenceLevel.REPLICATED,
            adam_source="customer_ad_alignment.py MECHANISM_SUSCEPTIBILITY",
        )

    # N6. SOCIAL_PERSUASION_ALIGNMENT: social influence type → persuasion technique
    social_pers_edges = [
        ("si_highly_independent", "pt_authority_expertise", 0.70), ("si_highly_independent", "pt_scarcity_exclusivity", 0.65),
        ("si_informational_seeker", "pt_social_proof_expert", 0.85), ("si_informational_seeker", "pt_authority_expertise", 0.80),
        ("si_socially_aware", "pt_social_proof_similarity", 0.80), ("si_socially_aware", "pt_social_proof_testimonials", 0.80),
        ("si_normatively_driven", "pt_social_proof_numbers", 0.90), ("si_normatively_driven", "pt_bandwagon", 0.90),
        ("si_normatively_driven", "pt_unity_shared_identity", 0.85),
        ("si_opinion_leader", "pt_scarcity_exclusivity", 0.85), ("si_opinion_leader", "pt_unity_co_creation", 0.80),
        ("si_opinion_leader", "pt_social_proof_expert", 0.75),
    ]
    for source, target, strength in social_pers_edges:
        eid = f"social_aligns_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.SOCIAL_PROOF,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_responds_to_{target}",
            domain=PsychologicalDomain.SOCIAL,
            description=f"Social influence type {source} responds to technique {target} (strength={strength})",
            effect_sizes=[EffectSize("r", strength, context="SOCIAL_PERSUASION_ALIGNMENT matrix")],
            confidence=ConfidenceLevel.REPLICATED,
            adam_source="customer_ad_alignment.py SOCIAL_PERSUASION_ALIGNMENT",
        )

    # =========================================================================
    # O. EMPIRICAL EFFECTIVENESS EDGES (from 937M review ingestion)
    # =========================================================================

    # These are loaded dynamically from ingestion_merged_priors.json at graph
    # population time. Here we define the structural pattern and known pairs.
    empirical_edges = [
        ("explorer_archetype", "social_proof", 0.42, 3300000), ("explorer_archetype", "authority", 0.38, 3300000),
        ("explorer_archetype", "scarcity", 0.35, 3300000), ("explorer_archetype", "liking", 0.40, 3300000),
        ("explorer_archetype", "reciprocity", 0.33, 3300000), ("explorer_archetype", "commitment_consistency", 0.30, 3300000),
        ("explorer_archetype", "fomo", 0.28, 3300000),
        ("achiever_archetype", "authority", 0.45, 2800000), ("achiever_archetype", "social_proof", 0.40, 2800000),
        ("achiever_archetype", "commitment_consistency", 0.42, 2800000), ("achiever_archetype", "scarcity", 0.35, 2800000),
        ("achiever_archetype", "reciprocity", 0.32, 2800000), ("achiever_archetype", "liking", 0.30, 2800000),
        ("achiever_archetype", "fomo", 0.25, 2800000),
        ("guardian_archetype", "commitment_consistency", 0.48, 2900000), ("guardian_archetype", "authority", 0.45, 2900000),
        ("guardian_archetype", "social_proof", 0.42, 2900000), ("guardian_archetype", "reciprocity", 0.35, 2900000),
        ("guardian_archetype", "liking", 0.28, 2900000), ("guardian_archetype", "scarcity", 0.25, 2900000),
        ("guardian_archetype", "fomo", 0.20, 2900000),
        ("connector_archetype", "social_proof", 0.50, 1900000), ("connector_archetype", "liking", 0.48, 1900000),
        ("connector_archetype", "unity", 0.45, 1900000), ("connector_archetype", "reciprocity", 0.40, 1900000),
        ("connector_archetype", "commitment_consistency", 0.32, 1900000), ("connector_archetype", "authority", 0.28, 1900000),
        ("connector_archetype", "scarcity", 0.22, 1900000),
        ("analyst_archetype", "authority", 0.50, 577000), ("analyst_archetype", "commitment_consistency", 0.45, 577000),
        ("analyst_archetype", "social_proof", 0.38, 577000), ("analyst_archetype", "reciprocity", 0.30, 577000),
        ("analyst_archetype", "scarcity", 0.25, 577000), ("analyst_archetype", "liking", 0.22, 577000),
        ("pragmatist_archetype", "reciprocity", 0.42, 199000), ("pragmatist_archetype", "social_proof", 0.40, 199000),
        ("pragmatist_archetype", "commitment_consistency", 0.38, 199000), ("pragmatist_archetype", "authority", 0.35, 199000),
        ("pragmatist_archetype", "scarcity", 0.30, 199000), ("pragmatist_archetype", "liking", 0.30, 199000),
    ]
    for arch, mech, rate, sample in empirical_edges:
        eid = f"empirical_{arch}__{mech}"
        mech_enum = getattr(MechanismType, mech.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=arch, target=mech,
            mechanism=mech_enum,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{arch}_empirically_effective_{mech}",
            domain=PsychologicalDomain.CONSUMER_BEHAVIOR,
            description=f"Empirical: {arch} responds to {mech} at rate {rate:.2f} (n={sample:,} reviews from 937M corpus)",
            effect_sizes=[EffectSize("r", rate, context=f"ingestion empirical, n={sample:,}")],
            confidence=ConfidenceLevel.INGESTION_DERIVED,
            adam_source="ingestion_merged_priors.json global_effectiveness_matrix",
        )

    # =========================================================================
    # P. CATEGORY MODERATION EDGES
    # =========================================================================

    # High-value category moderations (where mechanism effectiveness differs
    # significantly from global average). Full matrix loaded at Neo4j time.
    category_mod_edges = [
        # Electronics: authority and social_proof amplified
        ("cat_electronics", "authority", 0.15, "Authority +15% in Electronics (specs, expert reviews)"),
        ("cat_electronics", "social_proof", 0.12, "Social proof +12% in Electronics (ratings, reviews)"),
        ("cat_electronics", "scarcity", -0.05, "Scarcity -5% in Electronics (considered purchase)"),
        # Baby Products: authority and commitment amplified, scarcity dampened
        ("cat_baby_products", "authority", 0.20, "Authority +20% in Baby (safety, pediatrician-endorsed)"),
        ("cat_baby_products", "commitment_consistency", 0.15, "Commitment +15% in Baby (parenting identity)"),
        ("cat_baby_products", "scarcity", -0.20, "Scarcity -20% in Baby (pressure feels exploitative)"),
        # Beauty: social_proof and liking amplified
        ("cat_beauty_and_personal_care", "social_proof", 0.18, "Social proof +18% in Beauty (before/after, reviews)"),
        ("cat_beauty_and_personal_care", "liking", 0.15, "Liking +15% in Beauty (aspiration, attractiveness)"),
        # Books: authority amplified, scarcity dampened
        ("cat_books", "authority", 0.20, "Authority +20% in Books (author expertise, awards)"),
        ("cat_books", "social_proof", 0.15, "Social proof +15% in Books (bestseller lists, reviews)"),
        ("cat_books", "scarcity", -0.15, "Scarcity -15% in Books (always available digitally)"),
        # Health: authority dominant, scarcity ethically constrained
        ("cat_health_and_household", "authority", 0.25, "Authority +25% in Health (clinical studies, doctor-recommended)"),
        ("cat_health_and_household", "scarcity", -0.25, "Scarcity -25% in Health (ethically inappropriate)"),
        # Grocery: reciprocity and social_proof amplified
        ("cat_grocery_and_gourmet_food", "reciprocity", 0.15, "Reciprocity +15% in Grocery (samples, coupons)"),
        ("cat_grocery_and_gourmet_food", "social_proof", 0.10, "Social proof +10% in Grocery (trending, popular)"),
        # Clothing: liking and identity_construction amplified
        ("cat_clothing_shoes_and_jewelry", "liking", 0.20, "Liking +20% in Fashion (attractiveness, aspiration)"),
        ("cat_clothing_shoes_and_jewelry", "scarcity", 0.15, "Scarcity +15% in Fashion (limited editions, seasons)"),
        # Home: commitment and social_proof
        ("cat_home_and_kitchen", "commitment_consistency", 0.12, "Commitment +12% in Home (investment, quality)"),
        ("cat_home_and_kitchen", "social_proof", 0.10, "Social proof +10% in Home (reviews, bestseller)"),
        # Sports: identity_construction and social_proof
        ("cat_sports_and_outdoors", "social_proof", 0.12, "Social proof +12% in Sports (athlete endorsement)"),
        # Toys: social_proof (parent reviews) and authority (safety)
        ("cat_toys_and_games", "social_proof", 0.15, "Social proof +15% in Toys (parent reviews, bestseller)"),
        ("cat_toys_and_games", "authority", 0.12, "Authority +12% in Toys (safety certifications)"),
        # Pet Supplies: authority and commitment
        ("cat_pet_supplies", "authority", 0.18, "Authority +18% in Pet (vet-recommended)"),
        ("cat_pet_supplies", "commitment_consistency", 0.12, "Commitment +12% in Pet (pet parent identity)"),
        # Automotive: authority and commitment
        ("cat_automotive", "authority", 0.20, "Authority +20% in Automotive (expert reviews, safety ratings)"),
        ("cat_automotive", "commitment_consistency", 0.15, "Commitment +15% in Automotive (brand loyalty)"),
    ]
    for cat, mech, delta, desc in category_mod_edges:
        eid = f"catmod_{cat}__{mech}"
        mech_enum = getattr(MechanismType, mech.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=cat, target=mech,
            mechanism=mech_enum,
            reasoning_type=ReasoningType.CONTEXTUAL_MODERATION,
            direction=f"{cat}_moderates_{mech}",
            domain=PsychologicalDomain.CONSUMER_BEHAVIOR,
            description=desc,
            effect_sizes=[EffectSize("r", delta, context="category moderation from ingestion")],
            confidence=ConfidenceLevel.INGESTION_DERIVED,
            adam_source="ingestion_merged_priors.json category_effectiveness_matrices",
        )

    # =========================================================================
    # Q. CROSS-DOMAIN TRANSFER EDGES
    # =========================================================================

    # Categories with similar archetype distributions can transfer mechanism
    # effectiveness knowledge. Similarity from archetype distribution overlap.
    transfer_edges = [
        ("cat_electronics", "cat_cell_phones_and_accessories", 0.92, "Very similar tech consumer profiles"),
        ("cat_electronics", "cat_software", 0.85, "Tech-oriented consumers"),
        ("cat_beauty_and_personal_care", "cat_all_beauty", 0.95, "Nearly identical beauty consumers"),
        ("cat_beauty_and_personal_care", "cat_health_and_personal_care", 0.82, "Overlapping health/beauty"),
        ("cat_books", "cat_kindle_store", 0.90, "Same reading consumers, different format"),
        ("cat_books", "cat_movies_and_tv", 0.72, "Overlapping entertainment consumers"),
        ("cat_cds_and_vinyl", "cat_digital_music", 0.88, "Same music consumers"),
        ("cat_sports_and_outdoors", "cat_patio_lawn_and_garden", 0.70, "Outdoor-oriented consumers"),
        ("cat_home_and_kitchen", "cat_tools_and_home_improvement", 0.78, "Homeowner consumers"),
        ("cat_baby_products", "cat_toys_and_games", 0.75, "Parent consumers"),
        ("cat_clothing_shoes_and_jewelry", "cat_beauty_and_personal_care", 0.68, "Fashion/beauty overlap"),
        ("cat_grocery_and_gourmet_food", "cat_health_and_household", 0.65, "Health-conscious consumers"),
        ("cat_office_products", "cat_industrial_and_scientific", 0.72, "Professional/workplace consumers"),
        ("cat_arts_crafts_and_sewing", "cat_handmade_products", 0.80, "Maker/creator consumers"),
        ("cat_pet_supplies", "cat_health_and_household", 0.55, "Care-oriented consumers"),
        ("cat_automotive", "cat_tools_and_home_improvement", 0.65, "DIY consumers"),
    ]
    for source, target, sim, desc in transfer_edges:
        eid = f"transfer_{source}__{target}"
        add_edge(eid,
            source=source, target=target,
            mechanism=MechanismType.SOCIAL_PROOF,
            reasoning_type=ReasoningType.CAUSAL,
            direction=f"{source}_transfers_to_{target}",
            domain=PsychologicalDomain.CONSUMER_BEHAVIOR,
            description=f"Cross-domain transfer: {desc} (similarity={sim})",
            effect_sizes=[EffectSize("r", sim, context="archetype distribution cosine similarity")],
            confidence=ConfidenceLevel.INGESTION_DERIVED,
            adam_source="ingestion_merged_priors.json category_archetype_distributions",
        )

    # =========================================================================
    # R. TEMPORAL TRAJECTORY EDGES
    # =========================================================================

    temporal_trend_edges = [
        ("social_proof", "increasing", 0.08, "Social proof effectiveness rising with review culture growth"),
        ("authority", "stable", 0.02, "Authority effectiveness stable across time periods"),
        ("scarcity", "decreasing", -0.05, "Scarcity fatigue from overuse in e-commerce"),
        ("commitment_consistency", "stable", 0.01, "Commitment/consistency effectiveness stable"),
        ("reciprocity", "increasing", 0.06, "Reciprocity rising with subscription/loyalty model growth"),
        ("liking", "increasing", 0.10, "Liking effectiveness rising with influencer culture"),
        ("unity", "increasing", 0.12, "Unity/community effectiveness rising with tribalism trends"),
    ]
    for mech, direction, delta, desc in temporal_trend_edges:
        eid = f"temporal_{mech}_{direction}"
        mech_enum = getattr(MechanismType, mech.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=mech, target=f"temporal_{direction}",
            mechanism=mech_enum,
            reasoning_type=ReasoningType.TEMPORAL,
            direction=f"{mech}_trending_{direction}",
            domain=PsychologicalDomain.TEMPORAL_PSYCHOLOGY,
            description=desc,
            effect_sizes=[EffectSize("r", delta, context="temporal trend 2015-2024 Amazon data")],
            confidence=ConfidenceLevel.MODERATE,
            adam_source="Amazon 2015 temporal layer analysis",
        )

    # =========================================================================
    # S. BRAND-CONSUMER RELATIONSHIP → MECHANISM AMPLIFICATION EDGES
    # =========================================================================

    # Each of the 52 relationship types amplifies specific mechanisms.
    # This is from relationship_intelligence.py 52-type taxonomy.
    relationship_mechanism_edges = [
        # Self-Definition
        ("rel_self_identity_core", "identity_construction", 0.30), ("rel_self_identity_core", "storytelling", 0.25),
        ("rel_self_identity_core", "mimetic_desire", 0.20),
        ("rel_self_expression_vehicle", "identity_construction", 0.25), ("rel_self_expression_vehicle", "embodied_cognition", 0.20),
        # Social Signaling
        ("rel_status_marker", "social_proof", 0.25), ("rel_status_marker", "scarcity", 0.30),
        ("rel_status_marker", "authority", 0.20),
        ("rel_social_compliance", "social_proof", 0.25), ("rel_social_compliance", "unity", 0.20),
        # Social Belonging
        ("rel_tribal_badge", "unity", 0.30), ("rel_tribal_badge", "social_proof", 0.25),
        ("rel_tribal_badge", "commitment_consistency", 0.20),
        ("rel_champion_evangelist", "reciprocity", 0.25), ("rel_champion_evangelist", "identity_construction", 0.25),
        ("rel_champion_evangelist", "unity", 0.20),
        # Emotional Bond
        ("rel_committed_partnership", "reciprocity", 0.30), ("rel_committed_partnership", "commitment_consistency", 0.30),
        ("rel_dependency", "commitment_consistency", 0.30), ("rel_dependency", "scarcity", 0.20),
        ("rel_fling", "attention_dynamics", 0.25), ("rel_fling", "scarcity", 0.20),
        ("rel_rescue_savior", "reciprocity", 0.35), ("rel_rescue_savior", "storytelling", 0.25),
        ("rel_rescue_savior", "authority", 0.20),
        # Functional Utility
        ("rel_reliable_tool", "authority", 0.25), ("rel_reliable_tool", "commitment_consistency", 0.25),
        ("rel_best_friend_utility", "reciprocity", 0.25), ("rel_best_friend_utility", "commitment_consistency", 0.20),
        # Guidance/Authority
        ("rel_mentor", "authority", 0.35), ("rel_mentor", "reciprocity", 0.20),
        ("rel_caregiver", "authority", 0.25), ("rel_caregiver", "commitment_consistency", 0.25),
        # Therapeutic/Escape
        ("rel_comfort_companion", "reciprocity", 0.25), ("rel_comfort_companion", "embodied_cognition", 0.20),
        ("rel_escape_artist", "storytelling", 0.30), ("rel_escape_artist", "attention_dynamics", 0.25),
        # Temporal/Nostalgic
        ("rel_childhood_friend", "storytelling", 0.30), ("rel_childhood_friend", "commitment_consistency", 0.25),
        ("rel_seasonal_rekindler", "temporal_construal", 0.25), ("rel_seasonal_rekindler", "commitment_consistency", 0.20),
        # Aspirational
        ("rel_aspirational_icon", "identity_construction", 0.30), ("rel_aspirational_icon", "mimetic_desire", 0.25),
        ("rel_aspirational_icon", "social_proof", 0.20),
        # Acquisition
        ("rel_courtship_dating", "social_proof", 0.25), ("rel_courtship_dating", "reciprocity", 0.20),
        ("rel_courtship_dating", "authority", 0.20),
        # Negative
        ("rel_captive_enslavement", "reciprocity", 0.20), ("rel_captive_enslavement", "commitment_consistency", 0.25),
        # Guilt/Obligation
        ("rel_accountability_captor", "commitment_consistency", 0.30), ("rel_accountability_captor", "scarcity", 0.20),
        ("rel_subscription_conscience", "commitment_consistency", 0.25), ("rel_subscription_conscience", "reciprocity", 0.20),
        # Ritual/Temporal
        ("rel_sacred_practice", "embodied_cognition", 0.30), ("rel_sacred_practice", "commitment_consistency", 0.25),
        ("rel_sacred_practice", "storytelling", 0.20),
        ("rel_temporal_marker", "temporal_construal", 0.25), ("rel_temporal_marker", "identity_construction", 0.25),
        ("rel_temporal_marker", "storytelling", 0.20),
        # Grief/Loss
        ("rel_mourning_bond", "commitment_consistency", 0.25), ("rel_mourning_bond", "storytelling", 0.25),
        ("rel_formula_betrayal", "commitment_consistency", 0.20), ("rel_formula_betrayal", "reciprocity", 0.20),
        # Salvation/Redemption
        ("rel_life_raft", "reciprocity", 0.35), ("rel_life_raft", "authority", 0.25),
        ("rel_life_raft", "storytelling", 0.25),
        ("rel_transformation_agent", "identity_construction", 0.30), ("rel_transformation_agent", "storytelling", 0.30),
        ("rel_transformation_agent", "social_proof", 0.20),
        # Cognitive Dependency
        ("rel_second_brain", "authority", 0.25), ("rel_second_brain", "commitment_consistency", 0.30),
        ("rel_platform_lock_in", "commitment_consistency", 0.35), ("rel_platform_lock_in", "scarcity", 0.20),
        # Tribal/Identity
        ("rel_tribal_signal", "unity", 0.30), ("rel_tribal_signal", "social_proof", 0.25),
        ("rel_tribal_signal", "identity_construction", 0.25),
        ("rel_inherited_legacy", "commitment_consistency", 0.30), ("rel_inherited_legacy", "storytelling", 0.25),
        ("rel_inherited_legacy", "authority", 0.20),
        ("rel_workspace_culture", "unity", 0.25), ("rel_workspace_culture", "authority", 0.20),
        ("rel_workspace_culture", "social_proof", 0.20),
        # Collector/Quest
        ("rel_grail_quest", "scarcity", 0.35), ("rel_grail_quest", "identity_construction", 0.25),
        ("rel_grail_quest", "mimetic_desire", 0.25),
        ("rel_completion_seeker", "commitment_consistency", 0.30), ("rel_completion_seeker", "scarcity", 0.25),
        # Trust/Intimacy
        ("rel_financial_intimate", "authority", 0.30), ("rel_financial_intimate", "commitment_consistency", 0.30),
        ("rel_therapist_provider", "authority", 0.30), ("rel_therapist_provider", "reciprocity", 0.25),
        ("rel_therapist_provider", "commitment_consistency", 0.25),
        # Insider/Complicity
        ("rel_insider_compact", "scarcity", 0.25), ("rel_insider_compact", "unity", 0.25),
        ("rel_insider_compact", "identity_construction", 0.20),
        ("rel_co_creator", "reciprocity", 0.30), ("rel_co_creator", "unity", 0.25),
        ("rel_co_creator", "identity_construction", 0.25),
        # Values/Permission
        ("rel_ethical_validator", "authority", 0.25), ("rel_ethical_validator", "identity_construction", 0.25),
        ("rel_status_arbiter", "scarcity", 0.30), ("rel_status_arbiter", "social_proof", 0.25),
        ("rel_status_arbiter", "identity_construction", 0.20),
        ("rel_competence_validator", "authority", 0.30), ("rel_competence_validator", "social_proof", 0.25),
        # Meta
        ("rel_ironic_aware", "identity_construction", 0.20), ("rel_ironic_aware", "storytelling", 0.20),
    ]
    for source, target, boost in relationship_mechanism_edges:
        eid = f"rel_amplifies_{source}__{target}"
        mech_enum = getattr(MechanismType, target.upper(), MechanismType.SOCIAL_PROOF)
        add_edge(eid,
            source=source, target=target,
            mechanism=mech_enum,
            reasoning_type=ReasoningType.MODERATIONAL,
            direction=f"{source}_amplifies_{target}",
            domain=PsychologicalDomain.BRAND_PSYCHOLOGY,
            description=f"Relationship type {source} amplifies mechanism {target} by {boost}",
            effect_sizes=[EffectSize("r", boost, context="relationship_intelligence.py 52-type taxonomy")],
            confidence=ConfidenceLevel.REPLICATED,
            citations=["Fournier (1998)", "Thomson et al. (2005)"],
            adam_source="relationship_intelligence.py",
        )

    return edges
