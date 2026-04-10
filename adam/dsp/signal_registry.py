"""
DSP Enrichment Engine — Behavioral Signal Registry
====================================================

42 behavioral signals from the DSP engine + ADAM platform extensions,
organized into 12 categories. Each signal maps observable bidstream
behavior to psychological constructs with academic citation support.

Categories:
    1. Mouse & Cursor Dynamics (Desktop)
    2. Touch Dynamics (Mobile)
    3. Scroll & Navigation Behavior
    4. Temporal Signals
    5. Content Context Signals
    6. Navigation & Decision Process
    7. Dwell Time & Attention
    8. Device & Environmental
    9. Social & Referral Signals
    10. Linguistic Signals
    11. Non-Action Signals
    12. ADAM Platform Extensions (review, purchase, search)
"""

from adam.dsp.models import (
    BehavioralSignal, EffectSize, SignalSource, SignalReliability, DeviceType,
)
from typing import Dict


def build_signal_registry() -> Dict[str, BehavioralSignal]:
    """Build the complete behavioral signal registry."""
    registry: Dict[str, BehavioralSignal] = {}

    # =========================================================================
    # 1. Mouse & Cursor Dynamics (Desktop) — 5 signals
    # =========================================================================

    registry["mouse_max_deviation"] = BehavioralSignal(
        signal_id="mouse_max_deviation",
        name="Cursor Trajectory Maximum Deviation",
        source=SignalSource.MOUSE_CURSOR,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["decision_conflict", "cognitive_load_state", "approach_avoidance"],
        extraction_method="Track cursor path from click origin to target; compute max perpendicular deviation from ideal straight line",
        effect_sizes=[EffectSize("eta_squared", 0.47, context="decision conflict → cursor deviation")],
        device_specific=DeviceType.DESKTOP,
        latency_budget_ms=20,
        validated_accuracy=0.85,
        description="Higher deviation indicates approach-avoidance conflict. η²=0.47 for decision conflict (Freeman & Ambady, 2010).",
        citations=["Freeman & Ambady (2010) MouseTracker", "Kieslich & Henninger (2017)"],
    )

    registry["cursor_velocity_profile"] = BehavioralSignal(
        signal_id="cursor_velocity_profile",
        name="Cursor Velocity Acceleration Profile",
        source=SignalSource.MOUSE_CURSOR,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["decision_dynamics", "commitment_strength", "cognitive_load_state"],
        extraction_method="Compute velocity, acceleration, and jerk profiles of cursor movement; identify hesitation peaks",
        effect_sizes=[EffectSize("r", 0.62, context="initiation time → decision difficulty")],
        device_specific=DeviceType.DESKTOP,
        latency_budget_ms=20,
        validated_accuracy=0.78,
        description="Slow initiation + fast execution = decided but conflicted. Fast initiation = impulsive or confident.",
        citations=["Hehman et al. (2015)", "Stillman et al. (2018)"],
    )

    registry["cursor_hover_duration"] = BehavioralSignal(
        signal_id="cursor_hover_duration",
        name="Cursor Hover Duration Over Elements",
        source=SignalSource.MOUSE_CURSOR,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["attention_allocation", "interest_intensity", "processing_depth"],
        extraction_method="Track hover time over interactive elements (CTAs, images, prices)",
        effect_sizes=[EffectSize("r", 0.45, context="hover duration → purchase intent")],
        device_specific=DeviceType.DESKTOP,
        latency_budget_ms=15,
        validated_accuracy=0.72,
        description="Extended hover indicates deeper processing and interest. Short hover = scanning/peripheral.",
        citations=["Guo & Agichtein (2012)", "Navalpakkam & Churchill (2012)"],
    )

    registry["cursor_tremor_jitter"] = BehavioralSignal(
        signal_id="cursor_tremor_jitter",
        name="Cursor Micro-Tremor and Jitter",
        source=SignalSource.MOUSE_CURSOR,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["anxiety_state", "arousal_level", "stress_state"],
        extraction_method="FFT analysis of cursor micro-movements during static periods",
        effect_sizes=[EffectSize("r", 0.38, context="cursor jitter → arousal")],
        device_specific=DeviceType.DESKTOP,
        latency_budget_ms=30,
        validated_accuracy=0.65,
        description="Increased jitter correlates with arousal and anxiety. Requires 500ms+ static period.",
        citations=["Yamauchi & Xiao (2018)"],
    )

    registry["mouse_area_under_curve"] = BehavioralSignal(
        signal_id="mouse_area_under_curve",
        name="Cursor Trajectory Area Under Curve",
        source=SignalSource.MOUSE_CURSOR,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["decision_conflict", "approach_avoidance", "cognitive_load_state"],
        extraction_method="Compute AUC between actual cursor path and ideal straight line to target",
        effect_sizes=[EffectSize("eta_squared", 0.47, context="decision conflict")],
        device_specific=DeviceType.DESKTOP,
        latency_budget_ms=20,
        validated_accuracy=0.85,
        description="AUC is the gold-standard mouse-tracking measure for decision conflict (Freeman, 2018).",
        citations=["Freeman (2018) Doing Psychological Science by Hand"],
    )

    # =========================================================================
    # 2. Touch Dynamics (Mobile) — 4 signals
    # =========================================================================

    registry["touch_pressure"] = BehavioralSignal(
        signal_id="touch_pressure",
        name="Touch Pressure Intensity",
        source=SignalSource.TOUCH_INTERACTION,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["approach_motivation_bas", "avoidance_motivation_bis", "arousal_level"],
        extraction_method="Read Force Touch / 3D Touch pressure value from touch events",
        effect_sizes=[EffectSize("r", 0.41, context="touch pressure → approach motivation")],
        device_specific=DeviceType.MOBILE,
        latency_budget_ms=10,
        validated_accuracy=0.70,
        description="Harder press = approach motivation / higher arousal. Lighter = avoidance / lower engagement.",
        citations=["Brasel & Gips (2014)", "Shen et al. (2016)"],
    )

    registry["touch_velocity"] = BehavioralSignal(
        signal_id="touch_velocity",
        name="Touch Interaction Velocity",
        source=SignalSource.TOUCH_INTERACTION,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["impulsivity", "processing_mode", "arousal_level"],
        extraction_method="Compute velocity of finger movement across touch events",
        effect_sizes=[EffectSize("r", 0.35, context="touch speed → impulsivity")],
        device_specific=DeviceType.MOBILE,
        latency_budget_ms=10,
        validated_accuracy=0.68,
        description="Fast touch interactions correlate with System 1 processing and impulsivity.",
        citations=["Brasel & Gips (2014)"],
    )

    registry["touchscreen_ownership_effect"] = BehavioralSignal(
        signal_id="touchscreen_ownership_effect",
        name="Touchscreen Endowment Effect",
        source=SignalSource.TOUCH_INTERACTION,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["endowment_effect", "psychological_ownership", "product_valuation"],
        extraction_method="Detect pinch-zoom, rotate, and sustained touch interactions with product images",
        effect_sizes=[EffectSize("cohens_d", 0.58, context="touch → WTP increase")],
        device_specific=DeviceType.MOBILE,
        latency_budget_ms=20,
        validated_accuracy=0.75,
        description="Touching product images on touchscreen increases perceived ownership and WTP by ~15-25%.",
        citations=["Brasel & Gips (2014) JCR", "Shen et al. (2016)"],
    )

    registry["swipe_direction_approach_avoidance"] = BehavioralSignal(
        signal_id="swipe_direction_approach_avoidance",
        name="Swipe Direction Approach/Avoidance",
        source=SignalSource.TOUCH_INTERACTION,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["approach_avoidance", "preference_strength"],
        extraction_method="Track swipe direction (toward body = approach, away = avoidance) on product cards",
        effect_sizes=[EffectSize("r", 0.30, context="swipe direction → preference")],
        device_specific=DeviceType.MOBILE,
        latency_budget_ms=15,
        validated_accuracy=0.62,
        description="Approach-avoidance motor compatibility: pulling toward self = preference, pushing away = rejection.",
        citations=["Chen & Bargh (1999)", "Cacioppo et al. (1993)"],
    )

    # =========================================================================
    # 3. Scroll & Navigation Behavior — 3 signals
    # =========================================================================

    registry["scroll_velocity_pattern"] = BehavioralSignal(
        signal_id="scroll_velocity_pattern",
        name="Scroll Velocity Pattern",
        source=SignalSource.SCROLL_BEHAVIOR,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["engagement_intensity", "processing_mode", "impulsivity"],
        extraction_method="Track scroll position over time; compute velocity, acceleration, and pause patterns",
        effect_sizes=[EffectSize("r", -0.52, context="scroll speed → engagement (inverse)")],
        latency_budget_ms=15,
        validated_accuracy=0.80,
        description="Fast scrolling = scanning/System1. Slow + pauses = engaged reading/System2. Reversal = re-evaluation.",
        citations=["Lagun & Agichtein (2015)", "Buscher et al. (2012)"],
    )

    registry["scroll_depth_engagement"] = BehavioralSignal(
        signal_id="scroll_depth_engagement",
        name="Maximum Scroll Depth",
        source=SignalSource.SCROLL_BEHAVIOR,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["engagement_intensity", "processing_mode", "information_need_state"],
        extraction_method="Track maximum scroll position relative to page height",
        effect_sizes=[EffectSize("r", 0.48, context="scroll depth → engagement")],
        latency_budget_ms=10,
        validated_accuracy=0.82,
        description="Deeper scroll = higher engagement and information need. Shallow = low interest or already decided.",
        citations=["Huang & Bashir (2015)"],
    )

    registry["scroll_reversal_frequency"] = BehavioralSignal(
        signal_id="scroll_reversal_frequency",
        name="Scroll Reversal Frequency",
        source=SignalSource.SCROLL_BEHAVIOR,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["deliberation_depth", "re_evaluation", "confusion_state"],
        extraction_method="Count scroll direction changes per minute",
        effect_sizes=[EffectSize("r", 0.39, context="scroll reversals → deliberation")],
        latency_budget_ms=15,
        validated_accuracy=0.70,
        description="Frequent reversals indicate comparison/re-evaluation behavior or confusion. Endowment re-checking.",
        citations=["Lagun & Agichtein (2015)"],
    )

    # =========================================================================
    # 4. Temporal Signals — 4 signals
    # =========================================================================

    registry["time_of_day_circadian"] = BehavioralSignal(
        signal_id="time_of_day_circadian",
        name="Time of Day — Circadian State",
        source=SignalSource.TEMPORAL_PATTERN,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["circadian_cognitive_capacity", "processing_mode", "decision_quality"],
        extraction_method="Extract local hour from request timestamp; map to circadian capacity curve",
        effect_sizes=[EffectSize("cohens_d", 0.65, context="synchrony effect on persuasion")],
        latency_budget_ms=5,
        validated_accuracy=0.90,
        description="10am peak → analytical processing. 2pm dip → heuristic. 11pm → depleted/vulnerable.",
        citations=["Gunia et al. (2014)", "Bodenhausen (1990)", "Goldstein et al. (2017)"],
    )

    registry["session_duration_fatigue"] = BehavioralSignal(
        signal_id="session_duration_fatigue",
        name="Session Duration — Decision Fatigue",
        source=SignalSource.TEMPORAL_PATTERN,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["decision_fatigue_state", "cognitive_depletion", "default_acceptance"],
        extraction_method="Track session start time and compute elapsed duration",
        effect_sizes=[EffectSize("r", 0.44, context="session length → default acceptance")],
        latency_budget_ms=5,
        validated_accuracy=0.85,
        description="Decision quality degrades with session length. Judges grant 65% parole early AM, <10% before lunch.",
        citations=["Danziger et al. (2011)", "Levav et al. (2010)"],
    )

    registry["day_of_week_mindset"] = BehavioralSignal(
        signal_id="day_of_week_mindset",
        name="Day of Week Mindset",
        source=SignalSource.TEMPORAL_PATTERN,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["hedonic_motivation", "utilitarian_motivation", "temporal_orientation"],
        extraction_method="Extract day from request timestamp",
        effect_sizes=[EffectSize("r", 0.25, context="weekend → hedonic")],
        latency_budget_ms=5,
        validated_accuracy=0.60,
        description="Weekend = hedonic, promotion-focused. Weekday AM = utilitarian, prevention-focused.",
        citations=["Helson (1964) Adaptation Level Theory"],
    )

    registry["late_night_vulnerability"] = BehavioralSignal(
        signal_id="late_night_vulnerability",
        name="Late Night Vulnerability Window",
        source=SignalSource.TEMPORAL_PATTERN,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["sleep_deprivation_state", "impulsivity", "vulnerability_cognitive_depletion"],
        extraction_method="Flag sessions between 11pm-5am local time",
        effect_sizes=[EffectSize("cohens_d", 0.85, context="sleep deprivation → impulsivity")],
        latency_budget_ms=5,
        validated_accuracy=0.92,
        description="11pm-5am: cognitive capacity reduced 30-50%, impulse control impaired. ETHICAL: suppress exploitative ads.",
        citations=["Harrison & Horne (2000)", "Killgore et al. (2006)"],
    )

    # =========================================================================
    # 5. Content Context Signals — 5 signals
    # =========================================================================

    registry["content_sentiment_spillover"] = BehavioralSignal(
        signal_id="content_sentiment_spillover",
        name="Content Sentiment → Affect Spillover",
        source=SignalSource.CONTENT_CONTEXT,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["valence_state", "mood_congruency_state", "affect_transfer"],
        extraction_method="NLP sentiment analysis of surrounding page content",
        effect_sizes=[EffectSize("r", 0.34, context="content mood → ad evaluation")],
        latency_budget_ms=30,
        validated_accuracy=0.75,
        description="Content mood spills over to ad evaluation. Positive content → positive ad attitudes.",
        citations=["Forgas (1995) AIM Model", "De Pelsmacker et al. (2002)"],
    )

    registry["content_arousal_positioning"] = BehavioralSignal(
        signal_id="content_arousal_positioning",
        name="Content Arousal Level",
        source=SignalSource.CONTENT_CONTEXT,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["arousal_level", "optimal_arousal", "processing_capacity"],
        extraction_method="Estimate arousal from content type, topic, and engagement metrics",
        effect_sizes=[EffectSize("r", 0.31, context="content arousal → ad processing")],
        latency_budget_ms=20,
        validated_accuracy=0.68,
        description="High-arousal content reduces analytical processing capacity. Moderate arousal is optimal for persuasion.",
        citations=["Yerkes-Dodson Law", "Thayer (1989)"],
    )

    registry["content_complexity_load"] = BehavioralSignal(
        signal_id="content_complexity_load",
        name="Content Complexity → Cognitive Load",
        source=SignalSource.CONTENT_CONTEXT,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["cognitive_load_state", "processing_capacity", "ad_processing_budget"],
        extraction_method="Flesch-Kincaid readability + word count + visual complexity score",
        effect_sizes=[EffectSize("r", 0.42, context="content complexity → cognitive load")],
        latency_budget_ms=25,
        validated_accuracy=0.72,
        description="Complex content consumes cognitive resources, leaving less for ad processing. Simple ads work better.",
        citations=["Sweller (1988) Cognitive Load Theory"],
    )

    registry["ad_density_attention_destruction"] = BehavioralSignal(
        signal_id="ad_density_attention_destruction",
        name="Ad Density → Attention Destruction",
        source=SignalSource.CONTENT_CONTEXT,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["attention_level", "ad_skepticism", "banner_blindness"],
        extraction_method="Count ad slots per viewport; compute ads-per-screen-area ratio",
        effect_sizes=[EffectSize("r", -0.55, context="ad density → attention per ad")],
        latency_budget_ms=10,
        validated_accuracy=0.88,
        description="Each additional ad reduces attention to every other ad. 3+ ads per screen destroys engagement.",
        citations=["Burke et al. (2005)", "Cho & Cheon (2004)"],
    )

    registry["content_category_frame_activation"] = BehavioralSignal(
        signal_id="content_category_frame_activation",
        name="Content Category Frame Activation",
        source=SignalSource.CONTENT_CONTEXT,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["content_frame_activation", "regulatory_focus_priming", "construal_level"],
        extraction_method="Map page content category to psychological frame (promotion/prevention, abstract/concrete)",
        effect_sizes=[EffectSize("r", 0.38, context="content frame → regulatory focus activation")],
        latency_budget_ms=15,
        validated_accuracy=0.70,
        description="Finance content activates prevention focus. Lifestyle activates promotion. Priming effect ~15min.",
        citations=["Higgins (1997)", "Lee & Aaker (2004)"],
    )

    # =========================================================================
    # 6. Navigation & Decision Process — 6 signals
    # =========================================================================

    registry["navigation_directness"] = BehavioralSignal(
        signal_id="navigation_directness",
        name="Navigation Directness Score",
        source=SignalSource.NAVIGATION_PATTERN,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["decision_confidence", "goal_clarity", "processing_mode"],
        extraction_method="Ratio of direct navigation steps to total steps (back-buttons, meandering, etc.)",
        effect_sizes=[EffectSize("r", 0.40, context="directness → goal clarity")],
        latency_budget_ms=15,
        validated_accuracy=0.72,
        description="Direct navigation = clear goal, prevention focus. Meandering = exploratory, promotion focus.",
        citations=["Moe (2003) JCR"],
    )

    registry["comparison_behavior_intensity"] = BehavioralSignal(
        signal_id="comparison_behavior_intensity",
        name="Cross-Product Comparison Intensity",
        source=SignalSource.NAVIGATION_PATTERN,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["maximizer_satisficer", "choice_overload", "decision_confidence"],
        extraction_method="Track product page views, tab switches, back-and-forth between product pages",
        effect_sizes=[EffectSize("r", 0.45, context="comparison → maximizing tendency")],
        latency_budget_ms=20,
        validated_accuracy=0.70,
        description="Intense comparison = maximizer tendency. Risk of choice overload. Needs simplification, not more options.",
        citations=["Schwartz (2004) Paradox of Choice"],
    )

    registry["cart_abandonment_pattern"] = BehavioralSignal(
        signal_id="cart_abandonment_pattern",
        name="Cart Abandonment Pattern",
        source=SignalSource.NON_ACTION,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["price_sensitivity", "decision_deferral", "psychological_ownership"],
        extraction_method="Track add-to-cart events followed by navigation away without purchase",
        effect_sizes=[EffectSize("r", 0.38, context="cart abandonment → price sensitivity")],
        latency_budget_ms=15,
        validated_accuracy=0.68,
        description="Cart abandonment signals price concern, decision deferral, or friction. But partial endowment established.",
        citations=["Kukar-Kinney & Close (2010)"],
    )

    registry["search_refinement_pattern"] = BehavioralSignal(
        signal_id="search_refinement_pattern",
        name="Search Query Refinement Pattern",
        source=SignalSource.LINGUISTIC_SIGNAL,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["need_for_cognition", "construal_level", "decision_stage"],
        extraction_method="Track search query evolution: broad→specific = narrowing; specific→broad = expanding",
        effect_sizes=[EffectSize("r", 0.35, context="search refinement → funnel stage")],
        latency_budget_ms=20,
        validated_accuracy=0.65,
        description="Broad→specific = moving down funnel. Specific→broad = starting over. Query length indicates engagement.",
        citations=["Broder (2002)", "Rose & Levinson (2004)"],
    )

    registry["back_navigation_frequency"] = BehavioralSignal(
        signal_id="back_navigation_frequency",
        name="Back Navigation Frequency",
        source=SignalSource.NAVIGATION_PATTERN,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["uncertainty_state", "re_evaluation", "decision_conflict"],
        extraction_method="Count back-button presses and page revisits per minute",
        effect_sizes=[EffectSize("r", 0.36, context="back navigation → uncertainty")],
        latency_budget_ms=10,
        validated_accuracy=0.68,
        description="Frequent back-navigation indicates uncertainty, re-evaluation, or unsatisfied information need.",
        citations=["Catledge & Pitkow (1995)"],
    )

    registry["filter_application_order"] = BehavioralSignal(
        signal_id="filter_application_order",
        name="Filter Application Order",
        source=SignalSource.NAVIGATION_PATTERN,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["implicit_priorities", "decision_strategy", "price_sensitivity"],
        extraction_method="Track which filters are applied first (price, ratings, brand, etc.)",
        effect_sizes=[EffectSize("r", 0.30, context="filter order → implicit priorities")],
        latency_budget_ms=15,
        validated_accuracy=0.60,
        description="First filter reveals implicit priority: price-first = price-sensitive, rating-first = quality-focused.",
        citations=["Häubl & Trifts (2000)"],
    )

    # =========================================================================
    # 7. Dwell Time & Attention — 2 signals
    # =========================================================================

    registry["dwell_time_latent_interest"] = BehavioralSignal(
        signal_id="dwell_time_latent_interest",
        name="Dwell Time — Latent Interest",
        source=SignalSource.DWELL_TIME,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["content_engagement", "interest_intensity", "processing_depth"],
        extraction_method="Track time between page load and first navigation away; account for tab switching",
        effect_sizes=[EffectSize("r", 0.52, context="dwell time → engagement")],
        latency_budget_ms=10,
        validated_accuracy=0.80,
        description="Longer dwell = deeper processing. But must distinguish from distraction (check mouse/scroll activity).",
        citations=["Liu et al. (2010)", "Kim et al. (2014)"],
    )

    registry["dwell_time_before_action"] = BehavioralSignal(
        signal_id="dwell_time_before_action",
        name="Dwell Time Before CTA Action",
        source=SignalSource.DWELL_TIME,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["decision_conflict", "processing_depth", "commitment_strength"],
        extraction_method="Track time between CTA visibility and click/dismiss",
        effect_sizes=[EffectSize("r", 0.40, context="pre-action dwell → decision difficulty")],
        latency_budget_ms=15,
        validated_accuracy=0.72,
        description="Long dwell before CTA = high conflict. Quick action = impulsive or pre-decided.",
        citations=["Krajbich et al. (2010)"],
    )

    # =========================================================================
    # 8. Device & Environmental — 3 signals
    # =========================================================================

    registry["device_type_processing_mode"] = BehavioralSignal(
        signal_id="device_type_processing_mode",
        name="Device Type → Processing Mode",
        source=SignalSource.DEVICE_SENSOR,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["processing_mode", "cognitive_load_state", "attention_level"],
        extraction_method="Detect device type from User-Agent or device APIs",
        effect_sizes=[EffectSize("cohens_d", 0.42, context="mobile vs desktop processing")],
        latency_budget_ms=5,
        validated_accuracy=0.75,
        description="Mobile = more System 1, less attention, smaller screen → simpler creative. Desktop = System 2 capable.",
        citations=["Ghose et al. (2019)", "Melumad & Pham (2020)"],
    )

    registry["connection_speed_patience"] = BehavioralSignal(
        signal_id="connection_speed_patience",
        name="Connection Speed → Patience Threshold",
        source=SignalSource.DEVICE_SENSOR,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["patience_threshold", "frustration_tolerance", "loading_abandonment"],
        extraction_method="Measure connection speed from resource timing API",
        effect_sizes=[EffectSize("r", 0.28, context="connection speed → patience")],
        latency_budget_ms=10,
        validated_accuracy=0.60,
        description="Slow connection users habituated to waiting. Fast connection users abandon at 2s+ load time.",
        citations=["Akamai (2017)"],
    )

    registry["dark_mode_state"] = BehavioralSignal(
        signal_id="dark_mode_state",
        name="Dark Mode as Environmental Signal",
        source=SignalSource.DEVICE_SENSOR,
        reliability=SignalReliability.TIER_4_THEORETICAL,
        psychological_construct_ids=["environmental_context", "circadian_state", "arousal_level"],
        extraction_method="Detect prefers-color-scheme: dark media query",
        effect_sizes=[EffectSize("r", 0.20, context="dark mode → evening/low-light context")],
        latency_budget_ms=5,
        validated_accuracy=0.55,
        description="Dark mode correlates with evening usage, lower ambient light. Creative should adapt contrast.",
        citations=["Theoretical — limited direct research"],
    )

    # =========================================================================
    # 9. Social & Referral Signals — 3 signals
    # =========================================================================

    registry["referrer_source_mindset"] = BehavioralSignal(
        signal_id="referrer_source_mindset",
        name="Referrer Source → Mindset Activation",
        source=SignalSource.SOCIAL_REFERRAL,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["goal_directedness", "social_proof_activation", "brand_familiarity"],
        extraction_method="Parse HTTP Referer header; classify as search/social/email/direct/ad",
        effect_sizes=[EffectSize("r", 0.35, context="referrer type → mindset")],
        latency_budget_ms=5,
        validated_accuracy=0.72,
        description="Search = goal-directed. Social = exploratory + social proof active. Direct = habitual. Ad = pre-framed.",
        citations=["Moe (2003)", "Park & Kim (2008)"],
    )

    registry["review_reading_depth"] = BehavioralSignal(
        signal_id="review_reading_depth",
        name="Review Reading Depth & Duration",
        source=SignalSource.SOCIAL_REFERRAL,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["decision_confidence", "social_proof_need", "information_search_mode"],
        extraction_method="Track scroll depth and time spent on review sections of product pages",
        effect_sizes=[EffectSize("r", 0.42, context="review reading → purchase intent")],
        latency_budget_ms=15,
        validated_accuracy=0.70,
        description="Deep review reading = social proof reliant, uncertain, seeking validation. Strong purchase signal.",
        citations=["Mudambi & Schuff (2010)"],
    )

    registry["scarcity_response_sensitivity"] = BehavioralSignal(
        signal_id="scarcity_response_sensitivity",
        name="Scarcity Cue Response Latency",
        source=SignalSource.SOCIAL_REFERRAL,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["loss_aversion", "urgency_susceptibility", "scarcity_perception"],
        extraction_method="Measure behavioral acceleration after scarcity cue exposure (faster clicks, shorter dwell)",
        effect_sizes=[EffectSize("r", 0.33, context="scarcity response → loss aversion")],
        latency_budget_ms=20,
        validated_accuracy=0.62,
        description="Quick response to scarcity cues = high loss aversion. No response = scarcity-immune or skeptical.",
        citations=["Cialdini (2009)", "Aggarwal et al. (2011)"],
    )

    # =========================================================================
    # 10. Linguistic Signals — 4 signals
    # =========================================================================

    registry["search_query_regulatory_focus"] = BehavioralSignal(
        signal_id="search_query_regulatory_focus",
        name="Search Query Regulatory Focus Detection",
        source=SignalSource.LINGUISTIC_SIGNAL,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["promotion_focus", "prevention_focus", "regulatory_fit"],
        extraction_method="NLP classification of search query: gain words (best, top, amazing) vs loss words (safe, reliable, protect)",
        effect_sizes=[EffectSize("odds_ratio", 2.0, context="regulatory fit → persuasion")],
        latency_budget_ms=25,
        validated_accuracy=0.72,
        description="'Best laptop for gaming' = promotion. 'Most reliable laptop' = prevention. Fit doubles persuasion.",
        citations=["Lee & Aaker (2004)", "Cesario et al. (2004)"],
    )

    registry["content_construal_level"] = BehavioralSignal(
        signal_id="content_construal_level",
        name="Content Construal Level Detection",
        source=SignalSource.LINGUISTIC_SIGNAL,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["construal_level", "psychological_distance", "message_match"],
        extraction_method="Analyze content for abstract vs concrete language; compute LIW (Linguistic Inquiry Word) scores",
        effect_sizes=[EffectSize("g", 0.475, context="construal match → persuasion")],
        latency_budget_ms=30,
        validated_accuracy=0.68,
        description="Content with abstract language (why, values) primes abstract construal. Concrete (how, features) primes concrete.",
        citations=["Trope & Liberman (2010)", "Kim et al. (2009)"],
    )

    registry["content_moral_language"] = BehavioralSignal(
        signal_id="content_moral_language",
        name="Content Moral Language Detection",
        source=SignalSource.LINGUISTIC_SIGNAL,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["moral_foundations", "value_activation", "identity_salience"],
        extraction_method="Detect moral foundation language using extended MFD (Moral Foundations Dictionary)",
        effect_sizes=[EffectSize("r", 0.28, context="moral language → value activation")],
        latency_budget_ms=30,
        validated_accuracy=0.60,
        description="Content with care/harm language activates care foundation. Authority language activates authority foundation.",
        citations=["Graham et al. (2009)", "Haidt (2012)"],
    )

    registry["hedging_language_uncertainty"] = BehavioralSignal(
        signal_id="hedging_language_uncertainty",
        name="Hedging Language → Uncertainty State",
        source=SignalSource.LINGUISTIC_SIGNAL,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["uncertainty_state", "ambivalence", "decision_confidence"],
        extraction_method="Detect hedging markers in user-generated text (search queries, reviews): 'maybe', 'not sure', 'kind of'",
        effect_sizes=[EffectSize("r", 0.30, context="hedging → uncertainty")],
        latency_budget_ms=20,
        validated_accuracy=0.62,
        description="Hedging language in search queries reveals uncertainty and need for closure/authority signals.",
        citations=["Hyland (1998)", "Pennebaker et al. (2015)"],
    )

    # =========================================================================
    # 11. Non-Action Signals — 3 signals
    # =========================================================================

    registry["zero_click_search"] = BehavioralSignal(
        signal_id="zero_click_search",
        name="Zero-Click Search (Browsing Without Action)",
        source=SignalSource.NON_ACTION,
        reliability=SignalReliability.TIER_3_EMERGING,
        psychological_construct_ids=["information_satisfaction", "passive_intent", "mind_wandering_state"],
        extraction_method="Detect search result page views without any click-through",
        effect_sizes=[EffectSize("r", 0.25, context="zero-click → passive browsing")],
        latency_budget_ms=10,
        validated_accuracy=0.58,
        description="Zero-click indicates either information satisfied by snippet or mind-wandering/low motivation.",
        citations=["Spink et al. (2001)"],
    )

    registry["form_abandonment_privacy"] = BehavioralSignal(
        signal_id="form_abandonment_privacy",
        name="Form Abandonment at Privacy Fields",
        source=SignalSource.NON_ACTION,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["privacy_sensitivity", "commitment_threshold", "friction_tolerance"],
        extraction_method="Detect form completion that stops at email/phone/address fields",
        effect_sizes=[EffectSize("r", 0.40, context="form abandonment → privacy concern")],
        latency_budget_ms=15,
        validated_accuracy=0.72,
        description="Abandoning at PII fields reveals privacy sensitivity. Progressive disclosure may help.",
        citations=["Acquisti & Grossklags (2005)"],
    )

    registry["wishlist_without_purchase"] = BehavioralSignal(
        signal_id="wishlist_without_purchase",
        name="Wishlist/Save Without Purchase",
        source=SignalSource.NON_ACTION,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["deferred_intent", "aspirational_identity", "price_sensitivity"],
        extraction_method="Track save/wishlist/bookmark actions without subsequent purchase",
        effect_sizes=[EffectSize("r", 0.35, context="wishlist → deferred purchase intent")],
        latency_budget_ms=10,
        validated_accuracy=0.68,
        description="Wishlisting = partial commitment + aspirational self-concept. Strong re-targeting signal with scarcity.",
        citations=["Park et al. (2012)"],
    )

    # =========================================================================
    # 12. ADAM Platform Extensions — 8 additional signals
    # =========================================================================

    registry["review_engagement_depth"] = BehavioralSignal(
        signal_id="review_engagement_depth",
        name="Review Section Engagement Depth",
        source=SignalSource.REVIEW_BEHAVIOR,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["social_proof_need", "decision_confidence", "information_search_mode"],
        extraction_method="Track time and scroll depth in review sections; count reviews read",
        effect_sizes=[EffectSize("r", 0.48, context="review engagement → social proof reliance")],
        latency_budget_ms=15,
        validated_accuracy=0.72,
        description="Deep review engagement signals social proof reliance and uncertainty. ADAM review intelligence informs mechanism selection.",
        citations=["Mudambi & Schuff (2010)", "ADAM ingestion pipeline"],
    )

    registry["helpful_vote_signal"] = BehavioralSignal(
        signal_id="helpful_vote_signal",
        name="Helpful Vote Interaction",
        source=SignalSource.REVIEW_BEHAVIOR,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["review_credibility_need", "community_engagement", "trust_formation"],
        extraction_method="Track helpful vote clicks on reviews",
        effect_sizes=[EffectSize("r", 0.35, context="helpful votes → trust formation")],
        latency_budget_ms=10,
        validated_accuracy=0.65,
        description="Users who vote on review helpfulness show higher trust-formation needs and community orientation.",
        citations=["ADAM helpful vote intelligence pipeline"],
    )

    registry["price_comparison_signal"] = BehavioralSignal(
        signal_id="price_comparison_signal",
        name="Price Comparison Behavior",
        source=SignalSource.SEARCH_PATTERN,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["price_sensitivity", "maximizer_satisficer", "mental_accounting"],
        extraction_method="Detect price filter usage, sort-by-price, and cross-retailer comparison patterns",
        effect_sizes=[EffectSize("r", 0.42, context="price comparison → price sensitivity")],
        latency_budget_ms=15,
        validated_accuracy=0.70,
        description="Active price comparison indicates mental accounting and maximizer tendency. Dollar-off > percent-off for concrete construal.",
        citations=["Schwartz (2004)", "ADAM behavioral analytics"],
    )

    registry["category_exploration_breadth"] = BehavioralSignal(
        signal_id="category_exploration_breadth",
        name="Category Exploration Breadth",
        source=SignalSource.SESSION_ANALYTICS,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["openness", "curiosity_state", "exploration_motivation"],
        extraction_method="Count distinct product categories viewed in session",
        effect_sizes=[EffectSize("r", 0.38, context="category breadth → openness")],
        latency_budget_ms=10,
        validated_accuracy=0.65,
        description="Broad category exploration correlates with openness and curiosity. Narrow = focused/decided.",
        citations=["Moe (2003)", "ADAM cross-category behavior framework"],
    )

    registry["return_visit_pattern"] = BehavioralSignal(
        signal_id="return_visit_pattern",
        name="Return Visit Frequency and Pattern",
        source=SignalSource.SESSION_ANALYTICS,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["brand_familiarity", "consideration_depth", "mere_exposure_effect"],
        extraction_method="Track visit frequency and recency from publisher first-party data",
        effect_sizes=[EffectSize("r", 0.40, context="return visits → brand familiarity")],
        latency_budget_ms=10,
        validated_accuracy=0.72,
        description="Return visits build mere exposure. 3+ visits = strong consideration. Familiarity enables peripheral route.",
        citations=["Zajonc (1968)", "ADAM mere exposure framework"],
    )

    registry["spec_sheet_engagement"] = BehavioralSignal(
        signal_id="spec_sheet_engagement",
        name="Specification/Detail Section Engagement",
        source=SignalSource.SESSION_ANALYTICS,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["need_for_cognition", "processing_mode", "decision_investment"],
        extraction_method="Track time and interaction with product specification/detail sections",
        effect_sizes=[EffectSize("r", 0.45, context="spec engagement → need for cognition")],
        latency_budget_ms=15,
        validated_accuracy=0.70,
        description="Deep spec engagement indicates high need-for-cognition and System 2 processing. Central route optimal.",
        citations=["Petty & Cacioppo (1986)", "ADAM cognitive engagement framework"],
    )

    registry["purchase_history_signal"] = BehavioralSignal(
        signal_id="purchase_history_signal",
        name="Purchase History Pattern",
        source=SignalSource.PURCHASE_HISTORY,
        reliability=SignalReliability.TIER_1_VALIDATED,
        psychological_construct_ids=["brand_loyalty", "risk_tolerance", "price_sensitivity"],
        extraction_method="Analyze purchase frequency, basket size, brand diversity from CRM/loyalty data",
        effect_sizes=[EffectSize("r", 0.55, context="purchase pattern → loyalty/risk profile")],
        latency_budget_ms=20,
        validated_accuracy=0.78,
        description="Purchase history reveals brand loyalty (habit strength), price sensitivity, and risk tolerance.",
        citations=["Ehrenberg (1988)", "ADAM behavioral analytics"],
    )

    registry["social_share_signal"] = BehavioralSignal(
        signal_id="social_share_signal",
        name="Social Sharing Behavior",
        source=SignalSource.SOCIAL_REFERRAL,
        reliability=SignalReliability.TIER_2_REPLICATED,
        psychological_construct_ids=["extraversion", "social_identity", "status_motivation"],
        extraction_method="Track social share button clicks, copy-link actions",
        effect_sizes=[EffectSize("r", 0.38, context="social sharing → extraversion")],
        latency_budget_ms=10,
        validated_accuracy=0.65,
        description="Social sharing indicates extraversion, identity expression motivation, and social proof susceptibility.",
        citations=["Berger & Milkman (2012)", "ADAM social calibration dimension"],
    )

    return registry
