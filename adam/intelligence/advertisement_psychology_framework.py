#!/usr/bin/env python3
"""
ADVERTISEMENT & BRAND PSYCHOLOGY FRAMEWORK
==========================================

Research-backed framework for analyzing psychological characteristics of
advertisements and brand/product descriptions. Enables measurement of:
1. Persuasion techniques employed
2. Emotional appeals activated
3. Framing strategies used
4. Value proposition types
5. Linguistic style and complexity
6. Target audience signals

This creates the "advertisement side" of the customer-ad matching equation,
allowing for precise alignment scoring between customer psychological profiles
and advertisement characteristics.

Research Sources:
- Persuasion Science (Cialdini, 2021; Petty & Cacioppo, 1986)
- Advertising Effectiveness (Vakratsas & Ambler, 1999)
- Emotional Advertising (Holbrook & Batra, 1987)
- Message Framing (Kahneman & Tversky, 1979)
- Brand Personality (Aaker, 1997)
- Elaboration Likelihood Model (Petty & Cacioppo, 1986)
- Regulatory Focus in Advertising (Lee & Aaker, 2004)
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
from functools import lru_cache


# =============================================================================
# PERSUASION TECHNIQUE DIMENSIONS (Expanded Cialdini + Fogg + Others)
# =============================================================================

@dataclass
class PersuasionTechniqueDimension:
    """
    Persuasion technique framework for advertisement analysis.
    
    Research Foundations:
    - Influence (Cialdini, 2021)
    - Persuasive Technology (Fogg, 2003)
    - Elaboration Likelihood Model (Petty & Cacioppo, 1986)
    """
    
    name: str
    category: str  # cialdini, fogg, rhetorical, cognitive_bias
    intensity_level: str  # subtle, moderate, strong
    ethical_rating: float  # 0-1, higher = more ethical
    effectiveness_context: List[str]  # contexts where most effective
    backfire_risk: float  # 0-1, risk of negative reaction
    
    # Detection patterns
    linguistic_markers: List[str] = field(default_factory=list)
    structural_markers: List[str] = field(default_factory=list)
    visual_markers: List[str] = field(default_factory=list)


PERSUASION_TECHNIQUES = {
    # === CIALDINI PRINCIPLES (Original 6 + Unity) ===
    "reciprocity_gift": PersuasionTechniqueDimension(
        name="reciprocity_gift",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["relationship_building", "loyalty_programs", "first_contact"],
        backfire_risk=0.15,
        linguistic_markers=[
            "free", "gift", "bonus", "complimentary", "on us", "no obligation",
            "yours to keep", "as a thank you", "we're giving you"
        ],
        structural_markers=["free_trial_offer", "gift_with_purchase", "value_add"],
        visual_markers=["gift_icon", "bonus_badge", "free_stamp"]
    ),
    "reciprocity_concession": PersuasionTechniqueDimension(
        name="reciprocity_concession",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.75,
        effectiveness_context=["negotiation", "upsell_downsell", "price_anchoring"],
        backfire_risk=0.25,
        linguistic_markers=[
            "reduced", "we've lowered", "special price", "just for you",
            "we're willing to", "meet you halfway", "compromise"
        ],
        structural_markers=["original_vs_sale_price", "crossed_out_price"],
        visual_markers=["price_slash", "discount_callout"]
    ),
    
    "commitment_small_ask": PersuasionTechniqueDimension(
        name="commitment_small_ask",
        category="cialdini",
        intensity_level="subtle",
        ethical_rating=0.90,
        effectiveness_context=["lead_generation", "funnel_entry", "engagement"],
        backfire_risk=0.10,
        linguistic_markers=[
            "just", "simply", "quick", "takes seconds", "easy first step",
            "start with", "begin by", "all you need to do"
        ],
        structural_markers=["micro_commitment", "quiz_start", "email_only"],
        visual_markers=["simple_form", "single_field", "progress_bar_start"]
    ),
    "commitment_consistency": PersuasionTechniqueDimension(
        name="commitment_consistency",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.80,
        effectiveness_context=["retention", "upselling", "habit_formation"],
        backfire_risk=0.20,
        linguistic_markers=[
            "you've already", "since you", "as someone who", "continuing your",
            "stay consistent", "keep your streak", "don't break"
        ],
        structural_markers=["progress_tracking", "achievement_system", "history_reference"],
        visual_markers=["streak_counter", "progress_bar", "milestone_badge"]
    ),
    
    "social_proof_numbers": PersuasionTechniqueDimension(
        name="social_proof_numbers",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["mass_market", "credibility_building", "trust"],
        backfire_risk=0.15,
        linguistic_markers=[
            "million", "thousands", "% of customers", "most popular",
            "best-selling", "top-rated", "highly rated", "customers love"
        ],
        structural_markers=["customer_count", "download_count", "rating_display"],
        visual_markers=["star_rating", "number_counter", "popularity_badge"]
    ),
    "social_proof_testimonials": PersuasionTechniqueDimension(
        name="social_proof_testimonials",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.80,
        effectiveness_context=["consideration_phase", "trust_building", "doubt_resolution"],
        backfire_risk=0.20,
        linguistic_markers=[
            "says", "according to", "testimonial", "review", "customer story",
            "real people", "verified buyer", "actual customer"
        ],
        structural_markers=["quote_format", "customer_photo", "name_location"],
        visual_markers=["testimonial_card", "customer_headshot", "quote_marks"]
    ),
    "social_proof_expert": PersuasionTechniqueDimension(
        name="social_proof_expert",
        category="cialdini",
        intensity_level="strong",
        ethical_rating=0.85,
        effectiveness_context=["high_involvement", "technical_products", "health_finance"],
        backfire_risk=0.15,
        linguistic_markers=[
            "expert", "specialist", "professional", "certified", "endorsed by",
            "recommended by doctors", "approved by", "trusted by experts"
        ],
        structural_markers=["expert_quote", "certification_logo", "professional_endorsement"],
        visual_markers=["expert_photo", "credential_badge", "certification_seal"]
    ),
    "social_proof_similarity": PersuasionTechniqueDimension(
        name="social_proof_similarity",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["targeted_marketing", "niche_products", "community"],
        backfire_risk=0.15,
        linguistic_markers=[
            "people like you", "customers in your area", "others in your industry",
            "similar to you", "your peers", "people who", "customers who also"
        ],
        structural_markers=["personalized_social_proof", "segment_specific"],
        visual_markers=["relatable_imagery", "demographic_matching"]
    ),
    
    "authority_credentials": PersuasionTechniqueDimension(
        name="authority_credentials",
        category="cialdini",
        intensity_level="strong",
        ethical_rating=0.90,
        effectiveness_context=["professional_services", "health", "finance", "education"],
        backfire_risk=0.10,
        linguistic_markers=[
            "certified", "licensed", "accredited", "award-winning", "PhD",
            "MD", "years of experience", "industry leader", "established"
        ],
        structural_markers=["credential_listing", "award_display", "certification_badges"],
        visual_markers=["diploma", "award_seal", "professional_photo"]
    ),
    "authority_expertise": PersuasionTechniqueDimension(
        name="authority_expertise",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["technical_products", "complex_services", "b2b"],
        backfire_risk=0.15,
        linguistic_markers=[
            "proprietary", "patented", "research-backed", "scientifically proven",
            "data-driven", "evidence-based", "peer-reviewed", "breakthrough"
        ],
        structural_markers=["research_citation", "patent_number", "data_visualization"],
        visual_markers=["lab_imagery", "data_charts", "scientific_diagrams"]
    ),
    
    "liking_attractiveness": PersuasionTechniqueDimension(
        name="liking_attractiveness",
        category="cialdini",
        intensity_level="subtle",
        ethical_rating=0.75,
        effectiveness_context=["consumer_goods", "lifestyle", "fashion"],
        backfire_risk=0.20,
        linguistic_markers=[
            "beautiful", "stunning", "gorgeous", "elegant", "attractive",
            "sophisticated", "stylish", "luxurious", "premium"
        ],
        structural_markers=["aspirational_imagery", "lifestyle_photography"],
        visual_markers=["attractive_models", "aesthetic_design", "luxury_setting"]
    ),
    "liking_similarity": PersuasionTechniqueDimension(
        name="liking_similarity",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["community_building", "brand_affinity", "values_marketing"],
        backfire_risk=0.15,
        linguistic_markers=[
            "like you", "we understand", "we've been there", "just like us",
            "share your values", "one of us", "part of the family"
        ],
        structural_markers=["relatable_stories", "founder_story", "behind_the_scenes"],
        visual_markers=["relatable_people", "authentic_moments", "real_settings"]
    ),
    "liking_compliment": PersuasionTechniqueDimension(
        name="liking_compliment",
        category="cialdini",
        intensity_level="subtle",
        ethical_rating=0.80,
        effectiveness_context=["personalization", "loyalty", "premium_positioning"],
        backfire_risk=0.25,
        linguistic_markers=[
            "you deserve", "because you're special", "for discerning customers",
            "you have great taste", "smart choice", "you know quality"
        ],
        structural_markers=["personalized_message", "vip_treatment"],
        visual_markers=["exclusive_badge", "premium_design"]
    ),
    
    "scarcity_limited_quantity": PersuasionTechniqueDimension(
        name="scarcity_limited_quantity",
        category="cialdini",
        intensity_level="strong",
        ethical_rating=0.65,
        effectiveness_context=["urgency_creation", "exclusivity", "premium"],
        backfire_risk=0.35,
        linguistic_markers=[
            "only X left", "limited stock", "while supplies last", "selling fast",
            "almost gone", "limited edition", "exclusive release", "rare"
        ],
        structural_markers=["inventory_counter", "stock_warning"],
        visual_markers=["low_stock_badge", "countdown_inventory", "scarcity_alert"]
    ),
    "scarcity_limited_time": PersuasionTechniqueDimension(
        name="scarcity_limited_time",
        category="cialdini",
        intensity_level="strong",
        ethical_rating=0.60,
        effectiveness_context=["promotions", "sales", "launch_events"],
        backfire_risk=0.40,
        linguistic_markers=[
            "ends today", "last chance", "expires", "deadline", "hurry",
            "don't miss", "act now", "limited time", "today only"
        ],
        structural_markers=["countdown_timer", "deadline_display", "expiration_notice"],
        visual_markers=["timer", "clock_icon", "urgent_colors"]
    ),
    "scarcity_exclusivity": PersuasionTechniqueDimension(
        name="scarcity_exclusivity",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.75,
        effectiveness_context=["luxury", "membership", "premium_tiers"],
        backfire_risk=0.25,
        linguistic_markers=[
            "exclusive", "members only", "invitation only", "VIP",
            "select few", "not for everyone", "by invitation", "private"
        ],
        structural_markers=["membership_gate", "waitlist", "application_required"],
        visual_markers=["exclusive_badge", "vip_label", "premium_border"]
    ),
    
    "unity_shared_identity": PersuasionTechniqueDimension(
        name="unity_shared_identity",
        category="cialdini",
        intensity_level="strong",
        ethical_rating=0.85,
        effectiveness_context=["community", "movement", "brand_tribes"],
        backfire_risk=0.15,
        linguistic_markers=[
            "we", "us", "our", "together", "community", "family",
            "tribe", "movement", "join us", "be part of"
        ],
        structural_markers=["community_features", "user_generated_content"],
        visual_markers=["group_imagery", "community_photos", "together_moments"]
    ),
    "unity_co_creation": PersuasionTechniqueDimension(
        name="unity_co_creation",
        category="cialdini",
        intensity_level="moderate",
        ethical_rating=0.90,
        effectiveness_context=["product_development", "engagement", "loyalty"],
        backfire_risk=0.10,
        linguistic_markers=[
            "help us", "your input", "you decide", "vote", "choose",
            "customize", "personalize", "make it yours", "created by you"
        ],
        structural_markers=["voting_system", "customization_tool", "feedback_request"],
        visual_markers=["interactive_elements", "user_choice_display"]
    ),
    
    # === COGNITIVE BIAS TECHNIQUES ===
    "anchoring_high": PersuasionTechniqueDimension(
        name="anchoring_high",
        category="cognitive_bias",
        intensity_level="moderate",
        ethical_rating=0.70,
        effectiveness_context=["pricing", "value_perception", "negotiation"],
        backfire_risk=0.30,
        linguistic_markers=[
            "valued at", "worth", "compare at", "originally", "retail price",
            "competitors charge", "normally", "regular price"
        ],
        structural_markers=["price_comparison", "value_calculation", "savings_display"],
        visual_markers=["crossed_price", "comparison_chart", "savings_callout"]
    ),
    "anchoring_decoy": PersuasionTechniqueDimension(
        name="anchoring_decoy",
        category="cognitive_bias",
        intensity_level="moderate",
        ethical_rating=0.65,
        effectiveness_context=["pricing_tiers", "subscription_models", "packages"],
        backfire_risk=0.25,
        linguistic_markers=[
            "most popular", "best value", "recommended", "premium",
            "professional", "enterprise", "basic", "standard"
        ],
        structural_markers=["three_tier_pricing", "highlighted_option", "recommended_badge"],
        visual_markers=["featured_plan", "most_popular_label", "visual_hierarchy"]
    ),
    
    "loss_aversion": PersuasionTechniqueDimension(
        name="loss_aversion",
        category="cognitive_bias",
        intensity_level="strong",
        ethical_rating=0.60,
        effectiveness_context=["retention", "urgency", "fear_appeal"],
        backfire_risk=0.40,
        linguistic_markers=[
            "don't miss", "don't lose", "avoid", "protect", "before it's gone",
            "you'll regret", "miss out", "lose your", "risk losing"
        ],
        structural_markers=["loss_framing", "negative_outcome_preview"],
        visual_markers=["warning_colors", "alert_icon", "loss_imagery"]
    ),
    
    "bandwagon": PersuasionTechniqueDimension(
        name="bandwagon",
        category="cognitive_bias",
        intensity_level="moderate",
        ethical_rating=0.75,
        effectiveness_context=["mass_market", "trends", "social_products"],
        backfire_risk=0.25,
        linguistic_markers=[
            "everyone", "trending", "viral", "popular", "phenomenon",
            "join millions", "don't be left out", "the world is"
        ],
        structural_markers=["trend_indicator", "live_activity_feed"],
        visual_markers=["crowd_imagery", "trend_graph", "popularity_meter"]
    ),
    
    "framing_gain": PersuasionTechniqueDimension(
        name="framing_gain",
        category="cognitive_bias",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["promotion_focus", "aspirational", "positive_positioning"],
        backfire_risk=0.15,
        linguistic_markers=[
            "gain", "achieve", "get", "enjoy", "benefit", "improve",
            "enhance", "boost", "increase", "grow", "unlock"
        ],
        structural_markers=["benefit_listing", "positive_outcomes", "success_stories"],
        visual_markers=["upward_arrows", "positive_imagery", "bright_colors"]
    ),
    "framing_loss": PersuasionTechniqueDimension(
        name="framing_loss",
        category="cognitive_bias",
        intensity_level="strong",
        ethical_rating=0.70,
        effectiveness_context=["prevention_focus", "insurance", "security"],
        backfire_risk=0.30,
        linguistic_markers=[
            "avoid", "prevent", "protect", "stop", "eliminate", "reduce",
            "don't let", "never again", "no more", "end"
        ],
        structural_markers=["problem_solution", "pain_point_focus", "risk_highlight"],
        visual_markers=["warning_imagery", "contrast_before_after", "protection_symbols"]
    ),
    
    # === EMOTIONAL MANIPULATION ===
    "fear_appeal": PersuasionTechniqueDimension(
        name="fear_appeal",
        category="emotional",
        intensity_level="strong",
        ethical_rating=0.50,
        effectiveness_context=["health", "safety", "security", "insurance"],
        backfire_risk=0.45,
        linguistic_markers=[
            "danger", "risk", "threat", "warning", "alarming", "critical",
            "urgent", "emergency", "catastrophic", "devastating"
        ],
        structural_markers=["risk_statistics", "worst_case_scenario"],
        visual_markers=["danger_imagery", "warning_colors", "dramatic_visuals"]
    ),
    "guilt_appeal": PersuasionTechniqueDimension(
        name="guilt_appeal",
        category="emotional",
        intensity_level="strong",
        ethical_rating=0.45,
        effectiveness_context=["charity", "parenting", "health", "environment"],
        backfire_risk=0.50,
        linguistic_markers=[
            "should", "ought", "responsibility", "duty", "can you live with",
            "how can you", "don't you owe", "what kind of"
        ],
        structural_markers=["moral_framing", "obligation_statement"],
        visual_markers=["emotional_imagery", "contrast_imagery", "sad_faces"]
    ),
    "aspiration_appeal": PersuasionTechniqueDimension(
        name="aspiration_appeal",
        category="emotional",
        intensity_level="moderate",
        ethical_rating=0.80,
        effectiveness_context=["luxury", "self_improvement", "lifestyle"],
        backfire_risk=0.20,
        linguistic_markers=[
            "dream", "imagine", "picture yourself", "become", "transform",
            "elevate", "aspire", "reach", "achieve your potential"
        ],
        structural_markers=["transformation_narrative", "future_pacing"],
        visual_markers=["aspirational_lifestyle", "success_imagery", "dream_scenarios"]
    ),
    "nostalgia_appeal": PersuasionTechniqueDimension(
        name="nostalgia_appeal",
        category="emotional",
        intensity_level="moderate",
        ethical_rating=0.85,
        effectiveness_context=["heritage_brands", "comfort_products", "older_demographics"],
        backfire_risk=0.15,
        linguistic_markers=[
            "remember", "classic", "traditional", "the way it used to be",
            "timeless", "heritage", "original", "since", "generations"
        ],
        structural_markers=["historical_reference", "retro_design"],
        visual_markers=["vintage_imagery", "sepia_tones", "retro_styling"]
    ),
    "humor_appeal": PersuasionTechniqueDimension(
        name="humor_appeal",
        category="emotional",
        intensity_level="moderate",
        ethical_rating=0.90,
        effectiveness_context=["brand_awareness", "social_media", "low_involvement"],
        backfire_risk=0.25,
        linguistic_markers=[
            "funny", "hilarious", "laugh", "joke", "witty", "clever",
            "playful", "fun", "entertaining", "amusing"
        ],
        structural_markers=["comedic_structure", "unexpected_twist", "punchline"],
        visual_markers=["playful_imagery", "cartoon_elements", "funny_faces"]
    ),
}


# =============================================================================
# EMOTIONAL APPEAL DIMENSIONS
# =============================================================================

@dataclass
class EmotionalAppealDimension:
    """
    Emotional appeal framework for advertisement analysis.
    
    Research Foundations:
    - Consumption Emotions (Richins, 1997)
    - Advertising Emotions (Holbrook & Batra, 1987)
    - Discrete Emotions Theory (Izard, 1977)
    """
    
    name: str
    valence: float  # -1 to 1, negative to positive
    arousal: float  # 0-1, low to high activation
    dominance: float  # 0-1, feeling of control
    social_function: str  # connection, status, belonging, etc.
    purchase_driver: str  # how this emotion drives purchase
    
    linguistic_markers: List[str] = field(default_factory=list)
    visual_markers: List[str] = field(default_factory=list)


EMOTIONAL_APPEALS = {
    # === POSITIVE HIGH AROUSAL ===
    "excitement": EmotionalAppealDimension(
        name="excitement",
        valence=0.8,
        arousal=0.9,
        dominance=0.6,
        social_function="shared_experience",
        purchase_driver="anticipation_reward",
        linguistic_markers=[
            "exciting", "thrilling", "amazing", "incredible", "wow",
            "unbelievable", "mind-blowing", "spectacular", "explosive"
        ],
        visual_markers=["dynamic_motion", "bright_colors", "action_shots", "energy_imagery"]
    ),
    "joy": EmotionalAppealDimension(
        name="joy",
        valence=0.9,
        arousal=0.7,
        dominance=0.7,
        social_function="celebration",
        purchase_driver="happiness_seeking",
        linguistic_markers=[
            "happy", "joyful", "delightful", "wonderful", "fantastic",
            "celebrate", "enjoy", "love", "pleasure", "bliss"
        ],
        visual_markers=["smiling_faces", "celebration_scenes", "warm_colors", "happiness_imagery"]
    ),
    "surprise": EmotionalAppealDimension(
        name="surprise",
        valence=0.6,
        arousal=0.85,
        dominance=0.3,
        social_function="attention_capture",
        purchase_driver="curiosity_novelty",
        linguistic_markers=[
            "surprising", "unexpected", "shocking", "unbelievable", "discover",
            "reveal", "secret", "hidden", "never before", "breakthrough"
        ],
        visual_markers=["reveal_moments", "unexpected_visuals", "contrast_imagery"]
    ),
    "pride": EmotionalAppealDimension(
        name="pride",
        valence=0.75,
        arousal=0.6,
        dominance=0.9,
        social_function="status_achievement",
        purchase_driver="self_enhancement",
        linguistic_markers=[
            "proud", "accomplished", "achieved", "earned", "deserve",
            "successful", "winner", "champion", "elite", "distinguished"
        ],
        visual_markers=["achievement_imagery", "trophy_moments", "success_scenes"]
    ),
    
    # === POSITIVE LOW AROUSAL ===
    "contentment": EmotionalAppealDimension(
        name="contentment",
        valence=0.7,
        arousal=0.3,
        dominance=0.6,
        social_function="well_being",
        purchase_driver="satisfaction_maintenance",
        linguistic_markers=[
            "satisfied", "content", "comfortable", "peaceful", "relaxed",
            "at ease", "calm", "serene", "tranquil", "balanced"
        ],
        visual_markers=["peaceful_scenes", "relaxation_imagery", "soft_colors", "nature_scenes"]
    ),
    "trust": EmotionalAppealDimension(
        name="trust",
        valence=0.65,
        arousal=0.35,
        dominance=0.5,
        social_function="relationship_security",
        purchase_driver="risk_reduction",
        linguistic_markers=[
            "trust", "reliable", "dependable", "honest", "transparent",
            "authentic", "genuine", "proven", "trusted", "secure"
        ],
        visual_markers=["handshake_imagery", "family_scenes", "institution_imagery", "stability_symbols"]
    ),
    "gratitude": EmotionalAppealDimension(
        name="gratitude",
        valence=0.8,
        arousal=0.4,
        dominance=0.5,
        social_function="reciprocity_bonding",
        purchase_driver="appreciation_reciprocity",
        linguistic_markers=[
            "thank you", "grateful", "appreciate", "thankful", "blessed",
            "honored", "privilege", "gift", "generosity"
        ],
        visual_markers=["giving_receiving", "appreciation_moments", "connection_imagery"]
    ),
    "love": EmotionalAppealDimension(
        name="love",
        valence=0.95,
        arousal=0.5,
        dominance=0.6,
        social_function="deep_connection",
        purchase_driver="relationship_expression",
        linguistic_markers=[
            "love", "adore", "cherish", "treasure", "beloved",
            "devoted", "passionate", "affection", "care", "bond"
        ],
        visual_markers=["couple_imagery", "family_moments", "heart_symbols", "intimate_scenes"]
    ),
    
    # === NEGATIVE (USED STRATEGICALLY) ===
    "fear": EmotionalAppealDimension(
        name="fear",
        valence=-0.7,
        arousal=0.9,
        dominance=0.2,
        social_function="threat_response",
        purchase_driver="protection_seeking",
        linguistic_markers=[
            "danger", "risk", "threat", "scary", "alarming",
            "frightening", "terrifying", "warning", "beware", "protect"
        ],
        visual_markers=["danger_imagery", "dark_colors", "warning_symbols", "threat_visualization"]
    ),
    "anxiety": EmotionalAppealDimension(
        name="anxiety",
        valence=-0.5,
        arousal=0.7,
        dominance=0.2,
        social_function="preparation",
        purchase_driver="uncertainty_reduction",
        linguistic_markers=[
            "worried", "concerned", "anxious", "uncertain", "nervous",
            "stressed", "overwhelmed", "what if", "could happen"
        ],
        visual_markers=["worried_expressions", "uncertain_imagery", "question_marks"]
    ),
    "guilt": EmotionalAppealDimension(
        name="guilt",
        valence=-0.6,
        arousal=0.5,
        dominance=0.3,
        social_function="moral_correction",
        purchase_driver="redemption_seeking",
        linguistic_markers=[
            "should", "guilty", "regret", "sorry", "ashamed",
            "responsible", "fault", "blame", "make up for"
        ],
        visual_markers=["contrast_imagery", "consequence_visuals", "sad_faces"]
    ),
    "envy": EmotionalAppealDimension(
        name="envy",
        valence=-0.3,
        arousal=0.6,
        dominance=0.3,
        social_function="social_comparison",
        purchase_driver="status_acquisition",
        linguistic_markers=[
            "they have", "others enjoy", "you could too", "why not you",
            "don't miss out", "be like them", "join the elite"
        ],
        visual_markers=["aspirational_others", "lifestyle_comparison", "status_symbols"]
    ),
    "frustration": EmotionalAppealDimension(
        name="frustration",
        valence=-0.5,
        arousal=0.7,
        dominance=0.4,
        social_function="problem_recognition",
        purchase_driver="solution_seeking",
        linguistic_markers=[
            "tired of", "frustrated", "annoyed", "fed up", "enough",
            "struggle", "hassle", "problem", "pain", "difficult"
        ],
        visual_markers=["struggle_imagery", "problem_scenarios", "before_contrast"]
    ),
    
    # === COMPLEX/MIXED ===
    "nostalgia": EmotionalAppealDimension(
        name="nostalgia",
        valence=0.5,
        arousal=0.4,
        dominance=0.4,
        social_function="identity_continuity",
        purchase_driver="comfort_familiarity",
        linguistic_markers=[
            "remember", "memories", "classic", "vintage", "retro",
            "the good old days", "childhood", "tradition", "heritage"
        ],
        visual_markers=["vintage_imagery", "sepia_tones", "historical_references", "retro_styling"]
    ),
    "anticipation": EmotionalAppealDimension(
        name="anticipation",
        valence=0.6,
        arousal=0.7,
        dominance=0.4,
        social_function="future_orientation",
        purchase_driver="delayed_gratification",
        linguistic_markers=[
            "coming soon", "get ready", "prepare", "await", "upcoming",
            "launch", "preview", "sneak peek", "first look", "early access"
        ],
        visual_markers=["teaser_imagery", "countdown_elements", "preview_visuals"]
    ),
    "empowerment": EmotionalAppealDimension(
        name="empowerment",
        valence=0.8,
        arousal=0.7,
        dominance=0.95,
        social_function="self_efficacy",
        purchase_driver="control_capability",
        linguistic_markers=[
            "empower", "control", "take charge", "you can", "capable",
            "strength", "power", "confident", "unstoppable", "in control"
        ],
        visual_markers=["power_poses", "achievement_imagery", "strength_symbols"]
    ),
}


# =============================================================================
# VALUE PROPOSITION TYPES
# =============================================================================

@dataclass
class ValuePropositionDimension:
    """
    Value proposition framework for advertisement analysis.
    
    Research Foundations:
    - Consumer Value Theory (Holbrook, 1999)
    - Means-End Chain (Gutman, 1982)
    - Value Proposition Design (Osterwalder, 2014)
    """
    
    name: str
    value_type: str  # functional, emotional, social, epistemic, conditional
    primary_benefit: str
    secondary_benefits: List[str]
    price_sensitivity_fit: str  # low, moderate, high
    target_motivation_fit: List[str]  # which customer motivations align
    
    linguistic_markers: List[str] = field(default_factory=list)


VALUE_PROPOSITIONS = {
    # === FUNCTIONAL VALUE ===
    "performance_superiority": ValuePropositionDimension(
        name="performance_superiority",
        value_type="functional",
        primary_benefit="better_results",
        secondary_benefits=["efficiency", "reliability", "durability"],
        price_sensitivity_fit="low",
        target_motivation_fit=["quality_seeking", "mastery_seeking", "problem_solving"],
        linguistic_markers=[
            "best", "superior", "outperforms", "leading", "advanced",
            "powerful", "fastest", "strongest", "highest rated"
        ]
    ),
    "convenience_ease": ValuePropositionDimension(
        name="convenience_ease",
        value_type="functional",
        primary_benefit="time_effort_saving",
        secondary_benefits=["simplicity", "accessibility", "hassle_free"],
        price_sensitivity_fit="moderate",
        target_motivation_fit=["efficiency_optimization", "immediate_gratification"],
        linguistic_markers=[
            "easy", "simple", "convenient", "effortless", "quick",
            "hassle-free", "seamless", "streamlined", "one-click"
        ]
    ),
    "reliability_durability": ValuePropositionDimension(
        name="reliability_durability",
        value_type="functional",
        primary_benefit="long_term_dependability",
        secondary_benefits=["quality", "warranty", "consistency"],
        price_sensitivity_fit="low",
        target_motivation_fit=["risk_mitigation", "quality_assurance", "conservative_preservation"],
        linguistic_markers=[
            "reliable", "durable", "long-lasting", "built to last",
            "dependable", "sturdy", "robust", "guaranteed", "warranty"
        ]
    ),
    "cost_efficiency": ValuePropositionDimension(
        name="cost_efficiency",
        value_type="functional",
        primary_benefit="money_saving",
        secondary_benefits=["value", "affordability", "roi"],
        price_sensitivity_fit="high",
        target_motivation_fit=["cost_minimization", "value_seeking", "reward_seeking"],
        linguistic_markers=[
            "save", "affordable", "value", "budget", "economical",
            "cost-effective", "cheap", "discount", "deal", "bargain"
        ]
    ),
    
    # === EMOTIONAL VALUE ===
    "pleasure_enjoyment": ValuePropositionDimension(
        name="pleasure_enjoyment",
        value_type="emotional",
        primary_benefit="hedonic_satisfaction",
        secondary_benefits=["fun", "delight", "sensory_pleasure"],
        price_sensitivity_fit="moderate",
        target_motivation_fit=["sensory_pleasure", "excitement_seeking", "self_reward"],
        linguistic_markers=[
            "enjoy", "pleasure", "delight", "indulge", "treat",
            "luxurious", "sensational", "blissful", "heavenly"
        ]
    ),
    "peace_of_mind": ValuePropositionDimension(
        name="peace_of_mind",
        value_type="emotional",
        primary_benefit="anxiety_reduction",
        secondary_benefits=["security", "confidence", "trust"],
        price_sensitivity_fit="low",
        target_motivation_fit=["anxiety_reduction", "risk_mitigation", "vigilant_security"],
        linguistic_markers=[
            "peace of mind", "worry-free", "secure", "protected",
            "safe", "confident", "assured", "relaxed", "stress-free"
        ]
    ),
    "self_expression": ValuePropositionDimension(
        name="self_expression",
        value_type="emotional",
        primary_benefit="identity_expression",
        secondary_benefits=["uniqueness", "creativity", "personalization"],
        price_sensitivity_fit="low",
        target_motivation_fit=["self_expression", "uniqueness_differentiation"],
        linguistic_markers=[
            "express", "unique", "individual", "personal", "custom",
            "signature", "distinctive", "authentic", "you"
        ]
    ),
    "transformation": ValuePropositionDimension(
        name="transformation",
        value_type="emotional",
        primary_benefit="positive_change",
        secondary_benefits=["improvement", "growth", "achievement"],
        price_sensitivity_fit="moderate",
        target_motivation_fit=["personal_growth", "goal_achievement", "aspiration_driven"],
        linguistic_markers=[
            "transform", "change", "become", "achieve", "unlock",
            "discover", "new you", "potential", "journey", "evolve"
        ]
    ),
    
    # === SOCIAL VALUE ===
    "status_prestige": ValuePropositionDimension(
        name="status_prestige",
        value_type="social",
        primary_benefit="social_standing",
        secondary_benefits=["exclusivity", "recognition", "admiration"],
        price_sensitivity_fit="low",
        target_motivation_fit=["status_signaling", "ego_protection", "social_approval"],
        linguistic_markers=[
            "prestigious", "exclusive", "elite", "luxury", "premium",
            "distinguished", "sophisticated", "status", "high-end"
        ]
    ),
    "belonging_connection": ValuePropositionDimension(
        name="belonging_connection",
        value_type="social",
        primary_benefit="social_connection",
        secondary_benefits=["community", "shared_experience", "acceptance"],
        price_sensitivity_fit="moderate",
        target_motivation_fit=["belonging_affirmation", "social_compliance", "unity_shared_identity"],
        linguistic_markers=[
            "community", "together", "join", "belong", "connect",
            "share", "part of", "family", "tribe", "movement"
        ]
    ),
    "social_responsibility": ValuePropositionDimension(
        name="social_responsibility",
        value_type="social",
        primary_benefit="ethical_consumption",
        secondary_benefits=["sustainability", "giving_back", "positive_impact"],
        price_sensitivity_fit="low",
        target_motivation_fit=["values_alignment", "altruistic_giving"],
        linguistic_markers=[
            "sustainable", "ethical", "responsible", "eco-friendly",
            "give back", "impact", "change", "better world", "conscious"
        ]
    ),
    
    # === EPISTEMIC VALUE ===
    "novelty_innovation": ValuePropositionDimension(
        name="novelty_innovation",
        value_type="epistemic",
        primary_benefit="new_experience",
        secondary_benefits=["discovery", "learning", "exploration"],
        price_sensitivity_fit="moderate",
        target_motivation_fit=["pure_curiosity", "excitement_seeking", "optimistic_exploration"],
        linguistic_markers=[
            "new", "innovative", "revolutionary", "first", "breakthrough",
            "cutting-edge", "pioneering", "discover", "explore"
        ]
    ),
    "knowledge_expertise": ValuePropositionDimension(
        name="knowledge_expertise",
        value_type="epistemic",
        primary_benefit="learning_mastery",
        secondary_benefits=["skill_development", "understanding", "competence"],
        price_sensitivity_fit="low",
        target_motivation_fit=["mastery_seeking", "personal_growth", "analytical_systematic"],
        linguistic_markers=[
            "learn", "master", "expert", "professional", "skill",
            "knowledge", "understand", "comprehensive", "in-depth"
        ]
    ),
}


# =============================================================================
# BRAND PERSONALITY DIMENSIONS (Aaker, 1997)
# =============================================================================

@dataclass
class BrandPersonalityDimension:
    """
    Brand personality framework based on Aaker (1997).
    
    Research Foundations:
    - Brand Personality (Aaker, 1997)
    - Brand Archetypes (Mark & Pearson, 2001)
    """
    
    name: str
    primary_trait: str
    facets: List[str]
    tone_of_voice: str
    customer_archetype_fit: List[str]  # which customer archetypes align
    
    linguistic_markers: List[str] = field(default_factory=list)
    visual_style: List[str] = field(default_factory=list)


BRAND_PERSONALITIES = {
    "sincerity": BrandPersonalityDimension(
        name="sincerity",
        primary_trait="genuine",
        facets=["down-to-earth", "honest", "wholesome", "cheerful"],
        tone_of_voice="warm_friendly_authentic",
        customer_archetype_fit=["nurturer", "guardian", "pragmatist"],
        linguistic_markers=[
            "honest", "genuine", "real", "authentic", "true",
            "family", "tradition", "wholesome", "caring", "friendly"
        ],
        visual_style=["warm_colors", "natural_settings", "real_people", "simple_design"]
    ),
    "excitement": BrandPersonalityDimension(
        name="excitement",
        primary_trait="spirited",
        facets=["daring", "spirited", "imaginative", "up-to-date"],
        tone_of_voice="energetic_bold_youthful",
        customer_archetype_fit=["explorer", "creator", "achiever"],
        linguistic_markers=[
            "exciting", "bold", "daring", "adventurous", "fresh",
            "cool", "trendy", "innovative", "dynamic", "edgy"
        ],
        visual_style=["vibrant_colors", "dynamic_imagery", "action_shots", "modern_design"]
    ),
    "competence": BrandPersonalityDimension(
        name="competence",
        primary_trait="reliable",
        facets=["reliable", "intelligent", "successful", "leader"],
        tone_of_voice="professional_confident_authoritative",
        customer_archetype_fit=["analyst", "achiever", "guardian"],
        linguistic_markers=[
            "reliable", "expert", "leader", "proven", "trusted",
            "professional", "quality", "performance", "results", "success"
        ],
        visual_style=["clean_design", "professional_imagery", "data_visualization", "corporate_aesthetic"]
    ),
    "sophistication": BrandPersonalityDimension(
        name="sophistication",
        primary_trait="elegant",
        facets=["upper-class", "charming", "glamorous", "smooth"],
        tone_of_voice="refined_elegant_aspirational",
        customer_archetype_fit=["achiever", "explorer"],
        linguistic_markers=[
            "elegant", "sophisticated", "luxury", "refined", "exquisite",
            "premium", "exclusive", "distinguished", "prestigious", "timeless"
        ],
        visual_style=["luxury_aesthetic", "high_end_imagery", "minimalist_design", "premium_materials"]
    ),
    "ruggedness": BrandPersonalityDimension(
        name="ruggedness",
        primary_trait="tough",
        facets=["outdoorsy", "tough", "strong", "rugged"],
        tone_of_voice="bold_straightforward_masculine",
        customer_archetype_fit=["explorer", "guardian", "pragmatist"],
        linguistic_markers=[
            "tough", "rugged", "strong", "durable", "built",
            "outdoor", "adventure", "powerful", "reliable", "enduring"
        ],
        visual_style=["outdoor_imagery", "natural_settings", "bold_typography", "earthy_colors"]
    ),
}


# =============================================================================
# LINGUISTIC STYLE DIMENSIONS
# =============================================================================

@dataclass
class LinguisticStyleDimension:
    """
    Linguistic style framework for advertisement text analysis.
    """
    
    name: str
    formality_level: float  # 0-1
    complexity_level: float  # 0-1
    emotional_tone: float  # -1 to 1
    directness: float  # 0-1
    cognitive_load_required: str  # minimal, moderate, high
    
    characteristic_markers: List[str] = field(default_factory=list)


LINGUISTIC_STYLES = {
    "conversational": LinguisticStyleDimension(
        name="conversational",
        formality_level=0.2,
        complexity_level=0.3,
        emotional_tone=0.5,
        directness=0.7,
        cognitive_load_required="minimal",
        characteristic_markers=[
            "you", "your", "we", "let's", "here's the thing",
            "honestly", "look", "so", "basically", "right?"
        ]
    ),
    "professional": LinguisticStyleDimension(
        name="professional",
        formality_level=0.8,
        complexity_level=0.6,
        emotional_tone=0.2,
        directness=0.6,
        cognitive_load_required="moderate",
        characteristic_markers=[
            "solutions", "implement", "optimize", "strategic",
            "comprehensive", "leverage", "enterprise", "scalable"
        ]
    ),
    "technical": LinguisticStyleDimension(
        name="technical",
        formality_level=0.7,
        complexity_level=0.9,
        emotional_tone=0.0,
        directness=0.8,
        cognitive_load_required="high",
        characteristic_markers=[
            "specifications", "parameters", "configuration",
            "performance metrics", "integration", "compatibility"
        ]
    ),
    "emotional": LinguisticStyleDimension(
        name="emotional",
        formality_level=0.3,
        complexity_level=0.3,
        emotional_tone=0.8,
        directness=0.5,
        cognitive_load_required="minimal",
        characteristic_markers=[
            "feel", "love", "amazing", "incredible", "heart",
            "passion", "dream", "believe", "imagine", "inspire"
        ]
    ),
    "urgent": LinguisticStyleDimension(
        name="urgent",
        formality_level=0.4,
        complexity_level=0.2,
        emotional_tone=0.3,
        directness=0.95,
        cognitive_load_required="minimal",
        characteristic_markers=[
            "now", "today", "immediately", "hurry", "limited",
            "don't miss", "act fast", "deadline", "last chance"
        ]
    ),
    "storytelling": LinguisticStyleDimension(
        name="storytelling",
        formality_level=0.4,
        complexity_level=0.5,
        emotional_tone=0.6,
        directness=0.3,
        cognitive_load_required="moderate",
        characteristic_markers=[
            "once upon", "imagine", "story", "journey", "began",
            "discovered", "transformed", "realized", "finally"
        ]
    ),
    "minimalist": LinguisticStyleDimension(
        name="minimalist",
        formality_level=0.5,
        complexity_level=0.1,
        emotional_tone=0.3,
        directness=0.9,
        cognitive_load_required="minimal",
        characteristic_markers=[
            "simple", "clean", "pure", "just", "only",
            "essential", "less", "minimal", "basic"
        ]
    ),
}


# =============================================================================
# ADVERTISEMENT ANALYZER
# =============================================================================

class AdvertisementAnalyzer:
    """
    Analyzes advertisements and brand descriptions for psychological characteristics.
    """
    
    def __init__(self):
        self._compiled_patterns: Dict[str, Dict[str, List[re.Pattern]]] = {}
        self._compile_all_patterns()
    
    def _compile_all_patterns(self) -> None:
        """Pre-compile all detection patterns."""
        pattern_sources = {
            "persuasion_technique": {
                name: dim.linguistic_markers
                for name, dim in PERSUASION_TECHNIQUES.items()
            },
            "emotional_appeal": {
                name: dim.linguistic_markers
                for name, dim in EMOTIONAL_APPEALS.items()
            },
            "value_proposition": {
                name: dim.linguistic_markers
                for name, dim in VALUE_PROPOSITIONS.items()
            },
            "brand_personality": {
                name: dim.linguistic_markers
                for name, dim in BRAND_PERSONALITIES.items()
            },
            "linguistic_style": {
                name: dim.characteristic_markers
                for name, dim in LINGUISTIC_STYLES.items()
            },
        }
        
        for category, dimensions in pattern_sources.items():
            self._compiled_patterns[category] = {}
            for dim_name, markers in dimensions.items():
                patterns = []
                for marker in markers:
                    pattern = re.compile(
                        r'\b' + re.escape(marker).replace(r'\ ', r'\s+') + r'\b',
                        re.IGNORECASE
                    )
                    patterns.append(pattern)
                self._compiled_patterns[category][dim_name] = patterns
    
    def analyze_text(self, text: str) -> Dict[str, Dict[str, float]]:
        """
        Analyze advertisement/product text for psychological dimensions.
        
        Args:
            text: Advertisement copy or product description
            
        Returns:
            Dict mapping category → dimension → score (0-1)
        """
        results = {}
        text_lower = text.lower()
        
        for category, dimensions in self._compiled_patterns.items():
            results[category] = {}
            
            for dim_name, patterns in dimensions.items():
                matches = 0
                for pattern in patterns:
                    matches += len(pattern.findall(text_lower))
                
                # Normalize score
                if patterns:
                    score = min(1.0, matches / (len(patterns) * 0.25))
                else:
                    score = 0.0
                    
                results[category][dim_name] = round(score, 3)
        
        return results
    
    def get_dominant_characteristics(
        self,
        text: str,
        threshold: float = 0.15
    ) -> Dict[str, Tuple[str, float]]:
        """
        Get dominant characteristic for each category.
        """
        analysis = self.analyze_text(text)
        dominant = {}
        
        for category, dimensions in analysis.items():
            if dimensions:
                best_dim = max(dimensions.keys(), key=lambda k: dimensions[k])
                best_score = dimensions[best_dim]
                
                if best_score >= threshold:
                    dominant[category] = (best_dim, best_score)
        
        return dominant
    
    def get_top_n_characteristics(
        self,
        text: str,
        n: int = 3,
        threshold: float = 0.1
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get top N characteristics for each category.
        """
        analysis = self.analyze_text(text)
        top_n = {}
        
        for category, dimensions in analysis.items():
            sorted_dims = sorted(
                dimensions.items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_n[category] = [
                (dim, score) for dim, score in sorted_dims[:n]
                if score >= threshold
            ]
        
        return top_n


# =============================================================================
# ADVERTISEMENT PROFILE
# =============================================================================

@dataclass
class AdvertisementProfile:
    """
    Complete psychological profile of an advertisement or brand description.
    """
    
    # Identification
    ad_id: str
    text_analyzed: str
    
    # Persuasion analysis
    primary_persuasion_technique: str
    persuasion_techniques_used: Dict[str, float]
    persuasion_intensity: str  # subtle, moderate, strong
    ethical_score: float  # 0-1
    
    # Emotional analysis
    primary_emotional_appeal: str
    emotional_appeals_used: Dict[str, float]
    emotional_valence: float  # -1 to 1
    emotional_arousal: float  # 0-1
    
    # Value proposition
    primary_value_proposition: str
    value_propositions_used: Dict[str, float]
    value_type: str  # functional, emotional, social, epistemic
    
    # Brand personality
    brand_personality: str
    personality_traits: Dict[str, float]
    
    # Linguistic analysis
    linguistic_style: str
    formality_level: float
    complexity_level: float
    cognitive_load_required: str
    
    # Target audience signals
    target_motivations: List[str]
    target_decision_styles: List[str]
    target_regulatory_focus: str
    
    # Mechanism alignment
    mechanism_emphasis: Dict[str, float]  # which Cialdini mechanisms emphasized
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ad_id": self.ad_id,
            "persuasion": {
                "primary": self.primary_persuasion_technique,
                "all": self.persuasion_techniques_used,
                "intensity": self.persuasion_intensity,
                "ethical_score": self.ethical_score,
            },
            "emotion": {
                "primary": self.primary_emotional_appeal,
                "all": self.emotional_appeals_used,
                "valence": self.emotional_valence,
                "arousal": self.emotional_arousal,
            },
            "value": {
                "primary": self.primary_value_proposition,
                "all": self.value_propositions_used,
                "type": self.value_type,
            },
            "brand": {
                "personality": self.brand_personality,
                "traits": self.personality_traits,
            },
            "linguistic": {
                "style": self.linguistic_style,
                "formality": self.formality_level,
                "complexity": self.complexity_level,
                "cognitive_load": self.cognitive_load_required,
            },
            "target_audience": {
                "motivations": self.target_motivations,
                "decision_styles": self.target_decision_styles,
                "regulatory_focus": self.target_regulatory_focus,
            },
            "mechanisms": self.mechanism_emphasis,
        }


def create_advertisement_profile(
    text: str,
    ad_id: str = "ad_001"
) -> AdvertisementProfile:
    """
    Create a complete psychological profile for an advertisement.
    """
    analyzer = AdvertisementAnalyzer()
    analysis = analyzer.analyze_text(text)
    dominant = analyzer.get_dominant_characteristics(text)
    
    # Get persuasion analysis
    persuasion_scores = analysis.get("persuasion_technique", {})
    primary_persuasion = max(persuasion_scores.keys(), key=lambda k: persuasion_scores[k]) if persuasion_scores else "none"
    
    # Calculate persuasion intensity
    max_persuasion_score = max(persuasion_scores.values()) if persuasion_scores else 0
    if max_persuasion_score > 0.6:
        persuasion_intensity = "strong"
    elif max_persuasion_score > 0.3:
        persuasion_intensity = "moderate"
    else:
        persuasion_intensity = "subtle"
    
    # Calculate ethical score
    if primary_persuasion in PERSUASION_TECHNIQUES:
        ethical_score = PERSUASION_TECHNIQUES[primary_persuasion].ethical_rating
    else:
        ethical_score = 0.75
    
    # Get emotional analysis
    emotion_scores = analysis.get("emotional_appeal", {})
    primary_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k]) if emotion_scores else "none"
    
    # Calculate emotional dimensions
    emotional_valence = 0.0
    emotional_arousal = 0.0
    if primary_emotion in EMOTIONAL_APPEALS:
        emotional_valence = EMOTIONAL_APPEALS[primary_emotion].valence
        emotional_arousal = EMOTIONAL_APPEALS[primary_emotion].arousal
    
    # Get value proposition
    value_scores = analysis.get("value_proposition", {})
    primary_value = max(value_scores.keys(), key=lambda k: value_scores[k]) if value_scores else "none"
    
    value_type = "functional"
    if primary_value in VALUE_PROPOSITIONS:
        value_type = VALUE_PROPOSITIONS[primary_value].value_type
    
    # Get brand personality
    personality_scores = analysis.get("brand_personality", {})
    brand_personality = max(personality_scores.keys(), key=lambda k: personality_scores[k]) if personality_scores else "none"
    
    # Get linguistic style
    style_scores = analysis.get("linguistic_style", {})
    linguistic_style = max(style_scores.keys(), key=lambda k: style_scores[k]) if style_scores else "conversational"
    
    formality = 0.5
    complexity = 0.5
    cognitive_load = "moderate"
    if linguistic_style in LINGUISTIC_STYLES:
        style = LINGUISTIC_STYLES[linguistic_style]
        formality = style.formality_level
        complexity = style.complexity_level
        cognitive_load = style.cognitive_load_required
    
    # Determine target audience signals
    target_motivations = _infer_target_motivations(primary_persuasion, primary_emotion, primary_value)
    target_decision_styles = _infer_target_decision_styles(persuasion_intensity, complexity, cognitive_load)
    target_regulatory_focus = _infer_target_regulatory_focus(primary_emotion, primary_persuasion)
    
    # Calculate mechanism emphasis (map persuasion techniques to Cialdini mechanisms)
    mechanism_emphasis = _calculate_mechanism_emphasis(persuasion_scores)
    
    return AdvertisementProfile(
        ad_id=ad_id,
        text_analyzed=text[:200] + "..." if len(text) > 200 else text,
        primary_persuasion_technique=primary_persuasion,
        persuasion_techniques_used=persuasion_scores,
        persuasion_intensity=persuasion_intensity,
        ethical_score=ethical_score,
        primary_emotional_appeal=primary_emotion,
        emotional_appeals_used=emotion_scores,
        emotional_valence=emotional_valence,
        emotional_arousal=emotional_arousal,
        primary_value_proposition=primary_value,
        value_propositions_used=value_scores,
        value_type=value_type,
        brand_personality=brand_personality,
        personality_traits=personality_scores,
        linguistic_style=linguistic_style,
        formality_level=formality,
        complexity_level=complexity,
        cognitive_load_required=cognitive_load,
        target_motivations=target_motivations,
        target_decision_styles=target_decision_styles,
        target_regulatory_focus=target_regulatory_focus,
        mechanism_emphasis=mechanism_emphasis,
    )


def _infer_target_motivations(persuasion: str, emotion: str, value: str) -> List[str]:
    """Infer target customer motivations from ad characteristics."""
    motivations = []
    
    # From value proposition
    if value in VALUE_PROPOSITIONS:
        motivations.extend(VALUE_PROPOSITIONS[value].target_motivation_fit)
    
    # From emotional appeal
    emotion_motivation_map = {
        "excitement": ["excitement_seeking", "immediate_gratification"],
        "fear": ["anxiety_reduction", "risk_mitigation"],
        "pride": ["status_signaling", "ego_protection"],
        "trust": ["quality_assurance", "conservative_preservation"],
        "nostalgia": ["nostalgia_comfort", "values_alignment"],
        "envy": ["status_signaling", "social_approval"],
    }
    if emotion in emotion_motivation_map:
        motivations.extend(emotion_motivation_map[emotion])
    
    return list(set(motivations))[:5]


def _infer_target_decision_styles(intensity: str, complexity: float, cognitive_load: str) -> List[str]:
    """Infer target decision styles from ad characteristics."""
    if intensity == "strong" and cognitive_load == "minimal":
        return ["gut_instinct", "affect_driven", "recognition_based"]
    elif cognitive_load == "high":
        return ["analytical_systematic", "maximizing", "deliberative_reflective"]
    else:
        return ["satisficing", "heuristic_based", "social_referencing"]


def _infer_target_regulatory_focus(emotion: str, persuasion: str) -> str:
    """Infer target regulatory focus from ad characteristics."""
    prevention_signals = ["fear", "anxiety", "guilt", "loss_aversion", "fear_appeal"]
    
    if emotion in prevention_signals or persuasion in prevention_signals:
        return "prevention"
    else:
        return "promotion"


def _calculate_mechanism_emphasis(persuasion_scores: Dict[str, float]) -> Dict[str, float]:
    """Map persuasion techniques to Cialdini mechanisms."""
    mechanism_map = {
        "reciprocity": ["reciprocity_gift", "reciprocity_concession"],
        "commitment": ["commitment_small_ask", "commitment_consistency"],
        "social_proof": ["social_proof_numbers", "social_proof_testimonials", "social_proof_expert", "social_proof_similarity", "bandwagon"],
        "authority": ["authority_credentials", "authority_expertise"],
        "liking": ["liking_attractiveness", "liking_similarity", "liking_compliment", "humor_appeal"],
        "scarcity": ["scarcity_limited_quantity", "scarcity_limited_time", "scarcity_exclusivity"],
        "unity": ["unity_shared_identity", "unity_co_creation"],
    }
    
    mechanisms = {}
    for mechanism, techniques in mechanism_map.items():
        scores = [persuasion_scores.get(t, 0) for t in techniques]
        mechanisms[mechanism] = round(max(scores) if scores else 0, 3)
    
    return mechanisms


# =============================================================================
# EXPORTS
# =============================================================================

def export_advertisement_framework_priors() -> Dict[str, Any]:
    """Export advertisement framework data for cold-start priors."""
    return {
        "persuasion_techniques": {
            name: {
                "category": dim.category,
                "intensity_level": dim.intensity_level,
                "ethical_rating": dim.ethical_rating,
                "effectiveness_context": dim.effectiveness_context,
                "backfire_risk": dim.backfire_risk,
                "linguistic_markers": dim.linguistic_markers[:5],
            }
            for name, dim in PERSUASION_TECHNIQUES.items()
        },
        "emotional_appeals": {
            name: {
                "valence": dim.valence,
                "arousal": dim.arousal,
                "dominance": dim.dominance,
                "social_function": dim.social_function,
                "purchase_driver": dim.purchase_driver,
            }
            for name, dim in EMOTIONAL_APPEALS.items()
        },
        "value_propositions": {
            name: {
                "value_type": dim.value_type,
                "primary_benefit": dim.primary_benefit,
                "price_sensitivity_fit": dim.price_sensitivity_fit,
                "target_motivation_fit": dim.target_motivation_fit,
            }
            for name, dim in VALUE_PROPOSITIONS.items()
        },
        "brand_personalities": {
            name: {
                "primary_trait": dim.primary_trait,
                "facets": dim.facets,
                "tone_of_voice": dim.tone_of_voice,
                "customer_archetype_fit": dim.customer_archetype_fit,
            }
            for name, dim in BRAND_PERSONALITIES.items()
        },
        "linguistic_styles": {
            name: {
                "formality_level": dim.formality_level,
                "complexity_level": dim.complexity_level,
                "emotional_tone": dim.emotional_tone,
                "cognitive_load_required": dim.cognitive_load_required,
            }
            for name, dim in LINGUISTIC_STYLES.items()
        },
        "dimension_counts": {
            "persuasion_techniques": len(PERSUASION_TECHNIQUES),
            "emotional_appeals": len(EMOTIONAL_APPEALS),
            "value_propositions": len(VALUE_PROPOSITIONS),
            "brand_personalities": len(BRAND_PERSONALITIES),
            "linguistic_styles": len(LINGUISTIC_STYLES),
        },
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ADVERTISEMENT PSYCHOLOGY FRAMEWORK TEST")
    print("="*70)
    
    # Test dimension counts
    print(f"\n=== Dimension Counts ===")
    print(f"Persuasion Techniques: {len(PERSUASION_TECHNIQUES)}")
    print(f"Emotional Appeals: {len(EMOTIONAL_APPEALS)}")
    print(f"Value Propositions: {len(VALUE_PROPOSITIONS)}")
    print(f"Brand Personalities: {len(BRAND_PERSONALITIES)}")
    print(f"Linguistic Styles: {len(LINGUISTIC_STYLES)}")
    
    # Test advertisement analysis
    print(f"\n=== Sample Advertisement Analysis ===")
    
    test_ads = [
        "LIMITED TIME OFFER! Only 3 left in stock. Join millions of satisfied customers. Don't miss this exclusive deal - ends today!",
        "Transform your life with our scientifically-proven methodology. Trusted by experts worldwide, our comprehensive program helps you achieve your goals.",
        "Feel the luxury. Indulge in pure elegance. Because you deserve the finest things in life. Experience sophistication redefined.",
        "Save 50% today! Best value in the market. Affordable quality for smart shoppers. Don't pay more than you need to.",
    ]
    
    for i, ad in enumerate(test_ads):
        print(f"\nAd #{i+1}: \"{ad[:60]}...\"")
        profile = create_advertisement_profile(ad, f"test_ad_{i+1}")
        print(f"  Persuasion: {profile.primary_persuasion_technique} ({profile.persuasion_intensity})")
        print(f"  Emotion: {profile.primary_emotional_appeal} (valence: {profile.emotional_valence:+.2f})")
        print(f"  Value: {profile.primary_value_proposition} ({profile.value_type})")
        print(f"  Style: {profile.linguistic_style} (formality: {profile.formality_level:.0%})")
        print(f"  Target Focus: {profile.target_regulatory_focus}")
        print(f"  Top Mechanisms: {[k for k, v in sorted(profile.mechanism_emphasis.items(), key=lambda x: x[1], reverse=True)[:3]]}")
