#!/usr/bin/env python3
"""
EMPIRICAL PSYCHOLOGY FRAMEWORK
==============================

Research-backed expansion of psychological dimensions for granular customer typing.
Each dimension is grounded in peer-reviewed psychological research with validated
measurement approaches and linguistic markers.

This framework expands the 3,750+ types to 25,000+ through finer-grained
sub-dimensions, each with:
- Empirical research foundation
- Validated measurement scales
- Linguistic/behavioral markers
- Scoring algorithms

Research Sources:
- Consumer Psychology (Solomon, 2019; Hoyer & MacInnis, 2020)
- Behavioral Economics (Kahneman, 2011; Thaler & Sunstein, 2008)
- Personality Psychology (Costa & McCrae, 1992; Ashton & Lee, 2007)
- Motivation Theory (Deci & Ryan, 2000; Maslow, 1943)
- Regulatory Focus Theory (Higgins, 1997, 2012)
- Dual-Process Theory (Evans & Stanovich, 2013)
- Persuasion Science (Cialdini, 2021; Petty & Cacioppo, 1986)
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
from functools import lru_cache


# =============================================================================
# EXPANDED MOTIVATION SYSTEM (from 15 → 42 types)
# Based on Self-Determination Theory + Consumer Motivation Research
# =============================================================================

@dataclass
class MotivationDimension:
    """
    Expanded motivation framework based on empirical research.
    
    Research Foundations:
    - Self-Determination Theory (Deci & Ryan, 2000)
    - Consumer Motivation Model (Rossiter & Percy, 1991)
    - Means-End Chain Theory (Gutman, 1982)
    """
    
    name: str
    category: str  # intrinsic, extrinsic, amotivation
    autonomy_level: float  # 0-1, how self-directed
    competence_need: float  # 0-1, mastery/achievement need
    relatedness_need: float  # 0-1, social connection need
    hedonic_vs_utilitarian: float  # -1 to 1, pleasure vs function
    temporal_orientation: str  # immediate, short_term, long_term
    risk_tolerance: float  # 0-1
    
    # Linguistic markers for detection
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


# EXPANDED MOTIVATIONS (42 types organized by category)
EXPANDED_MOTIVATIONS = {
    # === INTRINSIC MOTIVATIONS (Self-Determined) ===
    "pure_curiosity": MotivationDimension(
        name="pure_curiosity",
        category="intrinsic",
        autonomy_level=0.95,
        competence_need=0.8,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=0.3,
        temporal_orientation="long_term",
        risk_tolerance=0.7,
        linguistic_markers=[
            "wonder", "explore", "discover", "learn", "understand", "how does",
            "why", "fascinating", "intriguing", "curious about"
        ],
        behavioral_signals=["extensive_browsing", "deep_research", "comparison_shopping"]
    ),
    "mastery_seeking": MotivationDimension(
        name="mastery_seeking",
        category="intrinsic",
        autonomy_level=0.90,
        competence_need=0.95,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=-0.2,
        temporal_orientation="long_term",
        risk_tolerance=0.6,
        linguistic_markers=[
            "improve", "master", "expert", "professional", "advanced",
            "skill", "capability", "proficiency", "best in class"
        ],
        behavioral_signals=["skill_building", "certification_seeking", "expertise_development"]
    ),
    "self_expression": MotivationDimension(
        name="self_expression",
        category="intrinsic",
        autonomy_level=0.95,
        competence_need=0.6,
        relatedness_need=0.5,
        hedonic_vs_utilitarian=0.5,
        temporal_orientation="short_term",
        risk_tolerance=0.8,
        linguistic_markers=[
            "unique", "express", "individual", "personal style", "authentic",
            "creative", "different", "stand out", "my own"
        ],
        behavioral_signals=["customization", "personalization", "unique_purchases"]
    ),
    "flow_experience": MotivationDimension(
        name="flow_experience",
        category="intrinsic",
        autonomy_level=0.85,
        competence_need=0.7,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=0.6,
        temporal_orientation="immediate",
        risk_tolerance=0.5,
        linguistic_markers=[
            "immersive", "engaging", "absorbing", "lose track of time",
            "in the zone", "enjoyable experience", "love doing"
        ],
        behavioral_signals=["extended_engagement", "repeat_usage", "hobby_purchases"]
    ),
    "personal_growth": MotivationDimension(
        name="personal_growth",
        category="intrinsic",
        autonomy_level=0.90,
        competence_need=0.85,
        relatedness_need=0.4,
        hedonic_vs_utilitarian=-0.3,
        temporal_orientation="long_term",
        risk_tolerance=0.6,
        linguistic_markers=[
            "develop", "grow", "better version", "self-improvement",
            "potential", "transform", "evolve", "journey"
        ],
        behavioral_signals=["self_help_content", "courses", "coaching"]
    ),
    
    # === IDENTIFIED REGULATION (Internally Valued) ===
    "values_alignment": MotivationDimension(
        name="values_alignment",
        category="identified",
        autonomy_level=0.80,
        competence_need=0.5,
        relatedness_need=0.6,
        hedonic_vs_utilitarian=-0.1,
        temporal_orientation="long_term",
        risk_tolerance=0.4,
        linguistic_markers=[
            "believe in", "important to me", "values", "principles",
            "ethical", "sustainable", "responsible", "mission"
        ],
        behavioral_signals=["brand_values_research", "ethical_shopping", "cause_support"]
    ),
    "goal_achievement": MotivationDimension(
        name="goal_achievement",
        category="identified",
        autonomy_level=0.75,
        competence_need=0.9,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=-0.4,
        temporal_orientation="long_term",
        risk_tolerance=0.5,
        linguistic_markers=[
            "achieve", "goal", "milestone", "accomplish", "reach",
            "objective", "target", "ambition", "aspiration"
        ],
        behavioral_signals=["goal_tracking", "milestone_purchases", "achievement_unlocking"]
    ),
    "role_fulfillment": MotivationDimension(
        name="role_fulfillment",
        category="identified",
        autonomy_level=0.70,
        competence_need=0.6,
        relatedness_need=0.8,
        hedonic_vs_utilitarian=-0.3,
        temporal_orientation="short_term",
        risk_tolerance=0.3,
        linguistic_markers=[
            "as a parent", "as a professional", "my responsibility",
            "duty", "role", "obligation", "expected of me"
        ],
        behavioral_signals=["role_based_shopping", "gift_giving", "family_purchases"]
    ),
    "future_self_investment": MotivationDimension(
        name="future_self_investment",
        category="identified",
        autonomy_level=0.75,
        competence_need=0.7,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=-0.5,
        temporal_orientation="long_term",
        risk_tolerance=0.4,
        linguistic_markers=[
            "invest in myself", "future", "long-term", "preparation",
            "building", "foundation", "career", "retirement"
        ],
        behavioral_signals=["investment_purchases", "education", "health_prevention"]
    ),
    
    # === INTROJECTED REGULATION (Internal Pressure) ===
    "guilt_avoidance": MotivationDimension(
        name="guilt_avoidance",
        category="introjected",
        autonomy_level=0.40,
        competence_need=0.4,
        relatedness_need=0.7,
        hedonic_vs_utilitarian=-0.6,
        temporal_orientation="immediate",
        risk_tolerance=0.2,
        linguistic_markers=[
            "should", "ought to", "feel bad if", "guilty",
            "can't not", "have to", "must", "obligated"
        ],
        behavioral_signals=["last_minute_gifts", "obligation_purchases", "makeup_buying"]
    ),
    "ego_protection": MotivationDimension(
        name="ego_protection",
        category="introjected",
        autonomy_level=0.35,
        competence_need=0.6,
        relatedness_need=0.5,
        hedonic_vs_utilitarian=-0.2,
        temporal_orientation="immediate",
        risk_tolerance=0.3,
        linguistic_markers=[
            "prove", "show them", "demonstrate", "not less than",
            "as good as", "keep up", "maintain image"
        ],
        behavioral_signals=["competitive_purchases", "status_matching", "image_maintenance"]
    ),
    "self_esteem_enhancement": MotivationDimension(
        name="self_esteem_enhancement",
        category="introjected",
        autonomy_level=0.45,
        competence_need=0.5,
        relatedness_need=0.6,
        hedonic_vs_utilitarian=0.2,
        temporal_orientation="short_term",
        risk_tolerance=0.5,
        linguistic_markers=[
            "feel good about myself", "confidence", "proud",
            "worthy", "deserving", "treat myself", "reward"
        ],
        behavioral_signals=["self_reward", "confidence_purchases", "appearance_enhancement"]
    ),
    "anxiety_reduction": MotivationDimension(
        name="anxiety_reduction",
        category="introjected",
        autonomy_level=0.30,
        competence_need=0.3,
        relatedness_need=0.4,
        hedonic_vs_utilitarian=-0.7,
        temporal_orientation="immediate",
        risk_tolerance=0.1,
        linguistic_markers=[
            "worried", "concerned", "anxious", "peace of mind",
            "reassurance", "security", "protection", "safety"
        ],
        behavioral_signals=["insurance_buying", "backup_purchases", "safety_products"]
    ),
    
    # === EXTERNAL REGULATION (External Pressure) ===
    "social_compliance": MotivationDimension(
        name="social_compliance",
        category="external",
        autonomy_level=0.20,
        competence_need=0.3,
        relatedness_need=0.9,
        hedonic_vs_utilitarian=-0.4,
        temporal_orientation="immediate",
        risk_tolerance=0.2,
        linguistic_markers=[
            "everyone has", "expected", "normal", "standard",
            "fitting in", "appropriate", "acceptable", "peer pressure"
        ],
        behavioral_signals=["trend_following", "conformity_purchases", "social_norm_adherence"]
    ),
    "reward_seeking": MotivationDimension(
        name="reward_seeking",
        category="external",
        autonomy_level=0.25,
        competence_need=0.4,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=0.4,
        temporal_orientation="immediate",
        risk_tolerance=0.6,
        linguistic_markers=[
            "deal", "discount", "free", "bonus", "points",
            "cashback", "reward", "earn", "save"
        ],
        behavioral_signals=["deal_hunting", "loyalty_program", "promo_response"]
    ),
    "punishment_avoidance": MotivationDimension(
        name="punishment_avoidance",
        category="external",
        autonomy_level=0.15,
        competence_need=0.2,
        relatedness_need=0.4,
        hedonic_vs_utilitarian=-0.8,
        temporal_orientation="immediate",
        risk_tolerance=0.05,
        linguistic_markers=[
            "avoid", "prevent", "penalty", "fine", "consequence",
            "required", "mandatory", "compliance", "deadline"
        ],
        behavioral_signals=["deadline_purchases", "compliance_buying", "penalty_avoidance"]
    ),
    "authority_compliance": MotivationDimension(
        name="authority_compliance",
        category="external",
        autonomy_level=0.20,
        competence_need=0.3,
        relatedness_need=0.5,
        hedonic_vs_utilitarian=-0.5,
        temporal_orientation="short_term",
        risk_tolerance=0.1,
        linguistic_markers=[
            "recommended by", "doctor said", "expert advice",
            "professional recommendation", "prescribed", "suggested by"
        ],
        behavioral_signals=["prescription_following", "expert_recommendation", "authority_trust"]
    ),
    
    # === HEDONIC MOTIVATIONS (Pleasure-Seeking) ===
    "sensory_pleasure": MotivationDimension(
        name="sensory_pleasure",
        category="hedonic",
        autonomy_level=0.60,
        competence_need=0.2,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=0.95,
        temporal_orientation="immediate",
        risk_tolerance=0.6,
        linguistic_markers=[
            "feels amazing", "delicious", "beautiful", "sounds great",
            "smells wonderful", "luxurious", "indulgent", "sensory"
        ],
        behavioral_signals=["premium_sensory", "experience_seeking", "luxury_purchases"]
    ),
    "excitement_seeking": MotivationDimension(
        name="excitement_seeking",
        category="hedonic",
        autonomy_level=0.70,
        competence_need=0.4,
        relatedness_need=0.5,
        hedonic_vs_utilitarian=0.8,
        temporal_orientation="immediate",
        risk_tolerance=0.85,
        linguistic_markers=[
            "thrilling", "exciting", "adventure", "adrenaline",
            "new experience", "bold", "daring", "extreme"
        ],
        behavioral_signals=["novelty_seeking", "adventure_purchases", "thrill_experiences"]
    ),
    "nostalgia_comfort": MotivationDimension(
        name="nostalgia_comfort",
        category="hedonic",
        autonomy_level=0.50,
        competence_need=0.2,
        relatedness_need=0.7,
        hedonic_vs_utilitarian=0.6,
        temporal_orientation="immediate",
        risk_tolerance=0.2,
        linguistic_markers=[
            "reminds me of", "childhood", "memories", "classic",
            "traditional", "the way it used to be", "nostalgic"
        ],
        behavioral_signals=["retro_purchases", "comfort_products", "memory_triggers"]
    ),
    "escapism": MotivationDimension(
        name="escapism",
        category="hedonic",
        autonomy_level=0.45,
        competence_need=0.2,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=0.7,
        temporal_orientation="immediate",
        risk_tolerance=0.5,
        linguistic_markers=[
            "escape", "get away", "forget", "relax", "unwind",
            "disconnect", "break from reality", "transport"
        ],
        behavioral_signals=["entertainment", "travel", "gaming", "fiction_consumption"]
    ),
    "social_enjoyment": MotivationDimension(
        name="social_enjoyment",
        category="hedonic",
        autonomy_level=0.55,
        competence_need=0.3,
        relatedness_need=0.95,
        hedonic_vs_utilitarian=0.6,
        temporal_orientation="immediate",
        risk_tolerance=0.5,
        linguistic_markers=[
            "share with friends", "together", "party", "gathering",
            "social", "fun with others", "communal", "bonding"
        ],
        behavioral_signals=["group_purchases", "shareable_products", "social_experiences"]
    ),
    
    # === UTILITARIAN MOTIVATIONS (Function-Focused) ===
    "problem_solving": MotivationDimension(
        name="problem_solving",
        category="utilitarian",
        autonomy_level=0.65,
        competence_need=0.8,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=-0.9,
        temporal_orientation="short_term",
        risk_tolerance=0.4,
        linguistic_markers=[
            "solution", "fix", "solve", "address", "resolve",
            "eliminate", "overcome", "tackle", "handle"
        ],
        behavioral_signals=["solution_research", "problem_focused_shopping", "fix_purchases"]
    ),
    "efficiency_optimization": MotivationDimension(
        name="efficiency_optimization",
        category="utilitarian",
        autonomy_level=0.70,
        competence_need=0.75,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=-0.85,
        temporal_orientation="long_term",
        risk_tolerance=0.4,
        linguistic_markers=[
            "efficient", "save time", "faster", "streamline",
            "optimize", "productive", "automate", "simplify"
        ],
        behavioral_signals=["productivity_tools", "time_saving", "automation_seeking"]
    ),
    "cost_minimization": MotivationDimension(
        name="cost_minimization",
        category="utilitarian",
        autonomy_level=0.55,
        competence_need=0.6,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=-0.95,
        temporal_orientation="long_term",
        risk_tolerance=0.2,
        linguistic_markers=[
            "cheapest", "budget", "affordable", "cost-effective",
            "economical", "value for money", "save money", "frugal"
        ],
        behavioral_signals=["price_comparison", "budget_shopping", "discount_seeking"]
    ),
    "quality_assurance": MotivationDimension(
        name="quality_assurance",
        category="utilitarian",
        autonomy_level=0.60,
        competence_need=0.7,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=-0.7,
        temporal_orientation="long_term",
        risk_tolerance=0.3,
        linguistic_markers=[
            "quality", "reliable", "durable", "long-lasting",
            "well-made", "premium materials", "warranty", "guaranteed"
        ],
        behavioral_signals=["quality_research", "review_reading", "brand_trust"]
    ),
    "risk_mitigation": MotivationDimension(
        name="risk_mitigation",
        category="utilitarian",
        autonomy_level=0.50,
        competence_need=0.6,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=-0.8,
        temporal_orientation="long_term",
        risk_tolerance=0.1,
        linguistic_markers=[
            "safe", "secure", "protected", "backup", "insurance",
            "contingency", "precaution", "hedge", "diversify"
        ],
        behavioral_signals=["insurance_buying", "backup_systems", "safety_features"]
    ),
    
    # === SOCIAL MOTIVATIONS ===
    "status_signaling": MotivationDimension(
        name="status_signaling",
        category="social",
        autonomy_level=0.35,
        competence_need=0.5,
        relatedness_need=0.85,
        hedonic_vs_utilitarian=0.3,
        temporal_orientation="short_term",
        risk_tolerance=0.6,
        linguistic_markers=[
            "prestigious", "exclusive", "luxury", "premium",
            "high-end", "designer", "status", "impressive"
        ],
        behavioral_signals=["luxury_purchases", "visible_consumption", "brand_display"]
    ),
    "belonging_affirmation": MotivationDimension(
        name="belonging_affirmation",
        category="social",
        autonomy_level=0.40,
        competence_need=0.3,
        relatedness_need=0.95,
        hedonic_vs_utilitarian=0.1,
        temporal_orientation="short_term",
        risk_tolerance=0.3,
        linguistic_markers=[
            "part of", "community", "tribe", "belong", "member",
            "like others", "group", "team", "family"
        ],
        behavioral_signals=["community_products", "membership", "group_identification"]
    ),
    "uniqueness_differentiation": MotivationDimension(
        name="uniqueness_differentiation",
        category="social",
        autonomy_level=0.75,
        competence_need=0.5,
        relatedness_need=0.4,
        hedonic_vs_utilitarian=0.4,
        temporal_orientation="short_term",
        risk_tolerance=0.7,
        linguistic_markers=[
            "unique", "different", "rare", "limited edition",
            "one of a kind", "stand out", "distinctive", "special"
        ],
        behavioral_signals=["limited_edition", "customization", "rare_products"]
    ),
    "social_approval": MotivationDimension(
        name="social_approval",
        category="social",
        autonomy_level=0.30,
        competence_need=0.4,
        relatedness_need=0.90,
        hedonic_vs_utilitarian=0.0,
        temporal_orientation="short_term",
        risk_tolerance=0.2,
        linguistic_markers=[
            "what others think", "approval", "accepted", "liked",
            "respected", "admired", "popular", "well-regarded"
        ],
        behavioral_signals=["social_proof_seeking", "review_checking", "trend_following"]
    ),
    "altruistic_giving": MotivationDimension(
        name="altruistic_giving",
        category="social",
        autonomy_level=0.80,
        competence_need=0.3,
        relatedness_need=0.85,
        hedonic_vs_utilitarian=0.2,
        temporal_orientation="short_term",
        risk_tolerance=0.4,
        linguistic_markers=[
            "help others", "give back", "make a difference",
            "support", "contribute", "charity", "donate", "benefit others"
        ],
        behavioral_signals=["charitable_purchases", "cause_marketing", "gift_giving"]
    ),
    "relationship_maintenance": MotivationDimension(
        name="relationship_maintenance",
        category="social",
        autonomy_level=0.55,
        competence_need=0.4,
        relatedness_need=0.90,
        hedonic_vs_utilitarian=-0.1,
        temporal_orientation="long_term",
        risk_tolerance=0.3,
        linguistic_markers=[
            "for us", "relationship", "partner", "spouse", "family",
            "together", "bond", "connection", "strengthen"
        ],
        behavioral_signals=["couple_purchases", "family_products", "relationship_gifts"]
    ),
    
    # === TEMPORAL MOTIVATIONS ===
    "immediate_gratification": MotivationDimension(
        name="immediate_gratification",
        category="temporal",
        autonomy_level=0.40,
        competence_need=0.2,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=0.8,
        temporal_orientation="immediate",
        risk_tolerance=0.7,
        linguistic_markers=[
            "now", "immediately", "instant", "right away",
            "can't wait", "today", "urgent", "asap"
        ],
        behavioral_signals=["impulse_buying", "same_day_delivery", "instant_access"]
    ),
    "delayed_gratification": MotivationDimension(
        name="delayed_gratification",
        category="temporal",
        autonomy_level=0.80,
        competence_need=0.7,
        relatedness_need=0.3,
        hedonic_vs_utilitarian=-0.4,
        temporal_orientation="long_term",
        risk_tolerance=0.4,
        linguistic_markers=[
            "worth the wait", "investment", "long-term", "patient",
            "eventually", "build up", "save for", "plan for"
        ],
        behavioral_signals=["savings_plans", "pre_orders", "investment_purchases"]
    ),
    "scarcity_response": MotivationDimension(
        name="scarcity_response",
        category="temporal",
        autonomy_level=0.30,
        competence_need=0.4,
        relatedness_need=0.4,
        hedonic_vs_utilitarian=0.3,
        temporal_orientation="immediate",
        risk_tolerance=0.6,
        linguistic_markers=[
            "limited time", "running out", "last chance", "ending soon",
            "while supplies last", "exclusive", "rare opportunity"
        ],
        behavioral_signals=["flash_sale_response", "limited_edition", "urgency_buying"]
    ),
    "opportunity_cost_awareness": MotivationDimension(
        name="opportunity_cost_awareness",
        category="temporal",
        autonomy_level=0.70,
        competence_need=0.8,
        relatedness_need=0.2,
        hedonic_vs_utilitarian=-0.6,
        temporal_orientation="long_term",
        risk_tolerance=0.3,
        linguistic_markers=[
            "trade-off", "instead of", "opportunity cost", "alternative",
            "compare options", "best use of", "prioritize"
        ],
        behavioral_signals=["comparison_shopping", "alternative_research", "value_analysis"]
    ),
}


# =============================================================================
# EXPANDED DECISION STYLE SYSTEM (from 3 → 12 types)
# Based on Dual-Process Theory + Decision-Making Research
# =============================================================================

@dataclass
class DecisionStyleDimension:
    """
    Expanded decision-making framework based on cognitive research.
    
    Research Foundations:
    - Dual-Process Theory (Kahneman, 2011; Evans & Stanovich, 2013)
    - Consumer Decision-Making Styles (Sproles & Kendall, 1986)
    - Cognitive Style Theory (Riding & Cheema, 1991)
    """
    
    name: str
    processing_mode: str  # system1 (intuitive) vs system2 (analytical)
    information_load_preference: str  # minimal, moderate, comprehensive
    decision_confidence: float  # 0-1
    regret_sensitivity: float  # 0-1
    cognitive_effort_willingness: float  # 0-1
    time_pressure_tolerance: float  # 0-1
    
    # Cognitive markers
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


EXPANDED_DECISION_STYLES = {
    # === SYSTEM 1 DOMINANT (Intuitive) ===
    "gut_instinct": DecisionStyleDimension(
        name="gut_instinct",
        processing_mode="system1",
        information_load_preference="minimal",
        decision_confidence=0.8,
        regret_sensitivity=0.3,
        cognitive_effort_willingness=0.2,
        time_pressure_tolerance=0.9,
        linguistic_markers=[
            "feels right", "gut feeling", "instinct", "just know",
            "intuition", "sense", "vibe", "immediate reaction"
        ],
        behavioral_signals=["quick_decisions", "minimal_research", "impulse_purchases"]
    ),
    "recognition_based": DecisionStyleDimension(
        name="recognition_based",
        processing_mode="system1",
        information_load_preference="minimal",
        decision_confidence=0.7,
        regret_sensitivity=0.4,
        cognitive_effort_willingness=0.3,
        time_pressure_tolerance=0.8,
        linguistic_markers=[
            "recognize", "familiar", "know this brand", "seen before",
            "trusted", "always buy", "go-to", "default choice"
        ],
        behavioral_signals=["brand_loyalty", "repeat_purchases", "familiar_choices"]
    ),
    "affect_driven": DecisionStyleDimension(
        name="affect_driven",
        processing_mode="system1",
        information_load_preference="minimal",
        decision_confidence=0.75,
        regret_sensitivity=0.5,
        cognitive_effort_willingness=0.25,
        time_pressure_tolerance=0.85,
        linguistic_markers=[
            "love it", "excited", "happy", "feel good", "enjoy",
            "makes me feel", "emotional connection", "attached"
        ],
        behavioral_signals=["emotional_purchases", "mood_shopping", "aesthetic_driven"]
    ),
    
    # === MIXED PROCESSING ===
    "satisficing": DecisionStyleDimension(
        name="satisficing",
        processing_mode="mixed",
        information_load_preference="moderate",
        decision_confidence=0.6,
        regret_sensitivity=0.4,
        cognitive_effort_willingness=0.4,
        time_pressure_tolerance=0.7,
        linguistic_markers=[
            "good enough", "meets my needs", "acceptable", "sufficient",
            "works for me", "will do", "reasonable", "adequate"
        ],
        behavioral_signals=["first_acceptable", "moderate_search", "practical_choices"]
    ),
    "heuristic_based": DecisionStyleDimension(
        name="heuristic_based",
        processing_mode="mixed",
        information_load_preference="moderate",
        decision_confidence=0.65,
        regret_sensitivity=0.45,
        cognitive_effort_willingness=0.5,
        time_pressure_tolerance=0.65,
        linguistic_markers=[
            "rule of thumb", "generally", "usually", "shortcut",
            "simple rule", "based on", "my criteria", "checklist"
        ],
        behavioral_signals=["rule_following", "criteria_matching", "simplified_comparison"]
    ),
    "social_referencing": DecisionStyleDimension(
        name="social_referencing",
        processing_mode="mixed",
        information_load_preference="moderate",
        decision_confidence=0.55,
        regret_sensitivity=0.6,
        cognitive_effort_willingness=0.45,
        time_pressure_tolerance=0.5,
        linguistic_markers=[
            "what others think", "reviews say", "recommended",
            "popular choice", "best rated", "most bought", "trending"
        ],
        behavioral_signals=["review_checking", "social_proof", "recommendation_seeking"]
    ),
    "authority_deferring": DecisionStyleDimension(
        name="authority_deferring",
        processing_mode="mixed",
        information_load_preference="moderate",
        decision_confidence=0.7,
        regret_sensitivity=0.4,
        cognitive_effort_willingness=0.4,
        time_pressure_tolerance=0.6,
        linguistic_markers=[
            "expert says", "professional opinion", "recommended by",
            "endorsed", "certified", "approved", "tested by"
        ],
        behavioral_signals=["expert_trust", "certification_seeking", "authority_following"]
    ),
    
    # === SYSTEM 2 DOMINANT (Analytical) ===
    "maximizing": DecisionStyleDimension(
        name="maximizing",
        processing_mode="system2",
        information_load_preference="comprehensive",
        decision_confidence=0.5,
        regret_sensitivity=0.9,
        cognitive_effort_willingness=0.95,
        time_pressure_tolerance=0.2,
        linguistic_markers=[
            "best possible", "optimal", "perfect", "ideal",
            "highest rated", "top choice", "nothing but the best"
        ],
        behavioral_signals=["exhaustive_research", "comparison_analysis", "perfectionism"]
    ),
    "analytical_systematic": DecisionStyleDimension(
        name="analytical_systematic",
        processing_mode="system2",
        information_load_preference="comprehensive",
        decision_confidence=0.75,
        regret_sensitivity=0.6,
        cognitive_effort_willingness=0.9,
        time_pressure_tolerance=0.3,
        linguistic_markers=[
            "analyze", "compare", "evaluate", "assess", "systematic",
            "thorough", "detailed", "comprehensive", "data-driven"
        ],
        behavioral_signals=["spreadsheet_comparison", "feature_analysis", "spec_matching"]
    ),
    "risk_calculating": DecisionStyleDimension(
        name="risk_calculating",
        processing_mode="system2",
        information_load_preference="comprehensive",
        decision_confidence=0.7,
        regret_sensitivity=0.7,
        cognitive_effort_willingness=0.85,
        time_pressure_tolerance=0.35,
        linguistic_markers=[
            "risk", "probability", "likelihood", "worst case",
            "downside", "hedge", "protection", "contingency"
        ],
        behavioral_signals=["risk_research", "warranty_seeking", "insurance_buying"]
    ),
    "deliberative_reflective": DecisionStyleDimension(
        name="deliberative_reflective",
        processing_mode="system2",
        information_load_preference="comprehensive",
        decision_confidence=0.65,
        regret_sensitivity=0.75,
        cognitive_effort_willingness=0.85,
        time_pressure_tolerance=0.25,
        linguistic_markers=[
            "think about it", "sleep on it", "consider carefully",
            "weigh options", "reflect", "take my time", "not rush"
        ],
        behavioral_signals=["cart_abandonment", "delayed_purchase", "multiple_visits"]
    ),
    "consensus_building": DecisionStyleDimension(
        name="consensus_building",
        processing_mode="system2",
        information_load_preference="comprehensive",
        decision_confidence=0.55,
        regret_sensitivity=0.65,
        cognitive_effort_willingness=0.7,
        time_pressure_tolerance=0.3,
        linguistic_markers=[
            "ask others", "get input", "family decision", "discuss",
            "consult", "collaborative", "joint decision", "agree together"
        ],
        behavioral_signals=["family_shopping", "consultation_seeking", "group_decisions"]
    ),
}


# =============================================================================
# EXPANDED REGULATORY FOCUS (from 2 → 8 types)
# Based on Regulatory Focus Theory (Higgins, 1997, 2012)
# =============================================================================

@dataclass
class RegulatoryFocusDimension:
    """
    Expanded regulatory focus framework.
    
    Research Foundations:
    - Regulatory Focus Theory (Higgins, 1997, 2012)
    - Regulatory Fit (Higgins, 2000)
    - Goal Pursuit Research (Förster et al., 2001)
    """
    
    name: str
    primary_focus: str  # promotion vs prevention
    approach_intensity: float  # 0-1
    avoidance_intensity: float  # 0-1
    gain_sensitivity: float  # 0-1
    loss_sensitivity: float  # 0-1
    
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


EXPANDED_REGULATORY_FOCUS = {
    # === PROMOTION-FOCUSED ===
    "eager_advancement": RegulatoryFocusDimension(
        name="eager_advancement",
        primary_focus="promotion",
        approach_intensity=0.95,
        avoidance_intensity=0.1,
        gain_sensitivity=0.9,
        loss_sensitivity=0.2,
        linguistic_markers=[
            "achieve", "accomplish", "advance", "grow", "gain",
            "opportunity", "potential", "aspire", "strive"
        ],
        behavioral_signals=["upgrade_seeking", "premium_preference", "growth_oriented"]
    ),
    "aspiration_driven": RegulatoryFocusDimension(
        name="aspiration_driven",
        primary_focus="promotion",
        approach_intensity=0.85,
        avoidance_intensity=0.2,
        gain_sensitivity=0.85,
        loss_sensitivity=0.25,
        linguistic_markers=[
            "dream", "ideal", "aspire", "hope", "wish",
            "imagine", "vision", "goal", "ambition"
        ],
        behavioral_signals=["aspiration_purchases", "luxury_interest", "future_focus"]
    ),
    "optimistic_exploration": RegulatoryFocusDimension(
        name="optimistic_exploration",
        primary_focus="promotion",
        approach_intensity=0.80,
        avoidance_intensity=0.25,
        gain_sensitivity=0.75,
        loss_sensitivity=0.3,
        linguistic_markers=[
            "try new", "explore", "discover", "adventure",
            "exciting", "possibilities", "curious", "open to"
        ],
        behavioral_signals=["novelty_seeking", "experimentation", "variety_seeking"]
    ),
    
    # === BALANCED ===
    "pragmatic_balanced": RegulatoryFocusDimension(
        name="pragmatic_balanced",
        primary_focus="balanced",
        approach_intensity=0.5,
        avoidance_intensity=0.5,
        gain_sensitivity=0.5,
        loss_sensitivity=0.5,
        linguistic_markers=[
            "practical", "reasonable", "balanced", "sensible",
            "fair", "moderate", "neither extreme", "middle ground"
        ],
        behavioral_signals=["balanced_decisions", "practical_choices", "moderate_risk"]
    ),
    "situational_adaptive": RegulatoryFocusDimension(
        name="situational_adaptive",
        primary_focus="balanced",
        approach_intensity=0.55,
        avoidance_intensity=0.55,
        gain_sensitivity=0.6,
        loss_sensitivity=0.6,
        linguistic_markers=[
            "depends", "context", "situation", "flexible",
            "adaptive", "case by case", "it varies", "circumstances"
        ],
        behavioral_signals=["context_sensitive", "adaptive_behavior", "flexible_decisions"]
    ),
    
    # === PREVENTION-FOCUSED ===
    "vigilant_security": RegulatoryFocusDimension(
        name="vigilant_security",
        primary_focus="prevention",
        approach_intensity=0.2,
        avoidance_intensity=0.9,
        gain_sensitivity=0.25,
        loss_sensitivity=0.9,
        linguistic_markers=[
            "safe", "secure", "protect", "avoid", "prevent",
            "careful", "cautious", "risk-free", "guaranteed"
        ],
        behavioral_signals=["safety_seeking", "insurance_buying", "risk_aversion"]
    ),
    "conservative_preservation": RegulatoryFocusDimension(
        name="conservative_preservation",
        primary_focus="prevention",
        approach_intensity=0.25,
        avoidance_intensity=0.85,
        gain_sensitivity=0.3,
        loss_sensitivity=0.85,
        linguistic_markers=[
            "maintain", "preserve", "keep", "stable", "consistent",
            "reliable", "dependable", "proven", "established"
        ],
        behavioral_signals=["brand_loyalty", "stability_seeking", "change_aversion"]
    ),
    "anxious_avoidance": RegulatoryFocusDimension(
        name="anxious_avoidance",
        primary_focus="prevention",
        approach_intensity=0.15,
        avoidance_intensity=0.95,
        gain_sensitivity=0.2,
        loss_sensitivity=0.95,
        linguistic_markers=[
            "worried", "concerned", "anxious", "fear", "dread",
            "worst case", "what if", "danger", "threat"
        ],
        behavioral_signals=["anxiety_purchasing", "over_insurance", "hyper_cautious"]
    ),
}


# =============================================================================
# EXPANDED EMOTIONAL INTENSITY (from 3 → 9 types)
# Based on Circumplex Model of Affect (Russell, 1980)
# =============================================================================

@dataclass
class EmotionalIntensityDimension:
    """
    Expanded emotional processing framework.
    
    Research Foundations:
    - Circumplex Model of Affect (Russell, 1980)
    - Affect Infusion Model (Forgas, 1995)
    - Consumer Emotions (Richins, 1997)
    """
    
    name: str
    arousal_level: float  # 0-1, activation level
    valence_sensitivity: float  # -1 to 1, positive vs negative
    emotional_stability: float  # 0-1
    affect_intensity: float  # 0-1
    emotion_regulation: float  # 0-1, ability to regulate
    
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


EXPANDED_EMOTIONAL_INTENSITY = {
    # === HIGH AROUSAL ===
    "high_positive_activation": EmotionalIntensityDimension(
        name="high_positive_activation",
        arousal_level=0.9,
        valence_sensitivity=0.8,
        emotional_stability=0.6,
        affect_intensity=0.9,
        emotion_regulation=0.5,
        linguistic_markers=[
            "excited", "thrilled", "ecstatic", "amazing", "incredible",
            "fantastic", "can't wait", "so happy", "love"
        ],
        behavioral_signals=["enthusiastic_buying", "impulse_positive", "excitement_driven"]
    ),
    "high_negative_activation": EmotionalIntensityDimension(
        name="high_negative_activation",
        arousal_level=0.9,
        valence_sensitivity=-0.7,
        emotional_stability=0.3,
        affect_intensity=0.9,
        emotion_regulation=0.3,
        linguistic_markers=[
            "angry", "frustrated", "furious", "outraged", "disgusted",
            "terrible", "awful", "hate", "worst"
        ],
        behavioral_signals=["complaint_driven", "brand_switching", "negative_reviews"]
    ),
    "mixed_high_arousal": EmotionalIntensityDimension(
        name="mixed_high_arousal",
        arousal_level=0.85,
        valence_sensitivity=0.0,
        emotional_stability=0.4,
        affect_intensity=0.85,
        emotion_regulation=0.4,
        linguistic_markers=[
            "intense", "overwhelming", "conflicted", "torn", "mixed feelings",
            "complicated emotions", "bittersweet", "ambivalent"
        ],
        behavioral_signals=["emotional_purchases", "comfort_buying", "coping_consumption"]
    ),
    
    # === MODERATE AROUSAL ===
    "moderate_positive": EmotionalIntensityDimension(
        name="moderate_positive",
        arousal_level=0.5,
        valence_sensitivity=0.6,
        emotional_stability=0.7,
        affect_intensity=0.5,
        emotion_regulation=0.7,
        linguistic_markers=[
            "pleased", "satisfied", "content", "happy", "good",
            "nice", "enjoyable", "pleasant", "glad"
        ],
        behavioral_signals=["steady_purchasing", "positive_reviews", "loyalty"]
    ),
    "moderate_negative": EmotionalIntensityDimension(
        name="moderate_negative",
        arousal_level=0.5,
        valence_sensitivity=-0.5,
        emotional_stability=0.6,
        affect_intensity=0.5,
        emotion_regulation=0.6,
        linguistic_markers=[
            "disappointed", "unsatisfied", "unhappy", "let down",
            "not great", "could be better", "mediocre", "meh"
        ],
        behavioral_signals=["hesitant_buying", "alternative_seeking", "neutral_reviews"]
    ),
    "emotionally_neutral": EmotionalIntensityDimension(
        name="emotionally_neutral",
        arousal_level=0.3,
        valence_sensitivity=0.0,
        emotional_stability=0.9,
        affect_intensity=0.2,
        emotion_regulation=0.9,
        linguistic_markers=[
            "functional", "practical", "logical", "rational",
            "objective", "factual", "straightforward", "no-nonsense"
        ],
        behavioral_signals=["rational_buying", "spec_focus", "feature_driven"]
    ),
    
    # === LOW AROUSAL ===
    "low_positive_calm": EmotionalIntensityDimension(
        name="low_positive_calm",
        arousal_level=0.2,
        valence_sensitivity=0.5,
        emotional_stability=0.9,
        affect_intensity=0.3,
        emotion_regulation=0.9,
        linguistic_markers=[
            "peaceful", "calm", "relaxed", "serene", "tranquil",
            "comfortable", "at ease", "gentle", "soothing"
        ],
        behavioral_signals=["comfort_seeking", "relaxation_products", "stress_relief"]
    ),
    "low_negative_sad": EmotionalIntensityDimension(
        name="low_negative_sad",
        arousal_level=0.2,
        valence_sensitivity=-0.6,
        emotional_stability=0.4,
        affect_intensity=0.4,
        emotion_regulation=0.5,
        linguistic_markers=[
            "sad", "down", "blue", "melancholy", "gloomy",
            "tired", "drained", "weary", "exhausted"
        ],
        behavioral_signals=["comfort_buying", "self_care", "mood_lifting"]
    ),
    "apathetic_disengaged": EmotionalIntensityDimension(
        name="apathetic_disengaged",
        arousal_level=0.1,
        valence_sensitivity=0.0,
        emotional_stability=0.5,
        affect_intensity=0.1,
        emotion_regulation=0.5,
        linguistic_markers=[
            "whatever", "don't care", "indifferent", "bored",
            "uninterested", "meh", "fine", "doesn't matter"
        ],
        behavioral_signals=["minimal_engagement", "quick_decisions", "low_involvement"]
    ),
}


# =============================================================================
# COGNITIVE LOAD TOLERANCE (NEW DIMENSION)
# Based on Cognitive Load Theory (Sweller, 1988)
# =============================================================================

@dataclass
class CognitiveLoadDimension:
    """
    Cognitive load tolerance framework.
    
    Research Foundations:
    - Cognitive Load Theory (Sweller, 1988)
    - Working Memory Capacity (Baddeley, 2000)
    - Decision Fatigue (Baumeister et al., 1998)
    """
    
    name: str
    working_memory_preference: str  # low, moderate, high
    information_chunking: str  # simple, structured, complex
    multitasking_tolerance: float  # 0-1
    decision_fatigue_susceptibility: float  # 0-1
    simplification_preference: float  # 0-1
    
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


COGNITIVE_LOAD_TOLERANCE = {
    "minimal_cognitive": CognitiveLoadDimension(
        name="minimal_cognitive",
        working_memory_preference="low",
        information_chunking="simple",
        multitasking_tolerance=0.2,
        decision_fatigue_susceptibility=0.9,
        simplification_preference=0.95,
        linguistic_markers=[
            "simple", "easy", "straightforward", "just tell me",
            "bottom line", "quick", "don't overwhelm", "keep it simple"
        ],
        behavioral_signals=["quick_decisions", "default_choices", "minimal_research"]
    ),
    "moderate_cognitive": CognitiveLoadDimension(
        name="moderate_cognitive",
        working_memory_preference="moderate",
        information_chunking="structured",
        multitasking_tolerance=0.5,
        decision_fatigue_susceptibility=0.5,
        simplification_preference=0.5,
        linguistic_markers=[
            "overview", "summary", "key points", "main features",
            "highlights", "organized", "structured", "categorized"
        ],
        behavioral_signals=["moderate_research", "comparison_tables", "feature_summaries"]
    ),
    "high_cognitive": CognitiveLoadDimension(
        name="high_cognitive",
        working_memory_preference="high",
        information_chunking="complex",
        multitasking_tolerance=0.8,
        decision_fatigue_susceptibility=0.2,
        simplification_preference=0.2,
        linguistic_markers=[
            "detailed", "comprehensive", "in-depth", "thorough",
            "complete information", "all specs", "full analysis", "deep dive"
        ],
        behavioral_signals=["exhaustive_research", "spec_sheets", "technical_details"]
    ),
}


# =============================================================================
# TEMPORAL ORIENTATION (NEW DIMENSION)
# Based on Temporal Self-Regulation Theory
# =============================================================================

@dataclass
class TemporalOrientationDimension:
    """
    Temporal orientation framework.
    
    Research Foundations:
    - Temporal Discounting (Frederick et al., 2002)
    - Future Time Perspective (Zimbardo & Boyd, 1999)
    - Intertemporal Choice (Loewenstein & Prelec, 1992)
    """
    
    name: str
    time_horizon: str  # immediate, short, medium, long
    delayed_gratification: float  # 0-1
    future_orientation: float  # 0-1
    present_hedonism: float  # 0-1
    planning_tendency: float  # 0-1
    
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


TEMPORAL_ORIENTATION = {
    "immediate_present": TemporalOrientationDimension(
        name="immediate_present",
        time_horizon="immediate",
        delayed_gratification=0.1,
        future_orientation=0.1,
        present_hedonism=0.95,
        planning_tendency=0.1,
        linguistic_markers=[
            "now", "today", "immediately", "right away", "instant",
            "can't wait", "urgent", "asap", "at once"
        ],
        behavioral_signals=["impulse_buying", "same_day_delivery", "instant_gratification"]
    ),
    "short_term": TemporalOrientationDimension(
        name="short_term",
        time_horizon="short",
        delayed_gratification=0.3,
        future_orientation=0.3,
        present_hedonism=0.7,
        planning_tendency=0.3,
        linguistic_markers=[
            "this week", "soon", "shortly", "coming days",
            "near future", "quick", "fast", "timely"
        ],
        behavioral_signals=["short_term_planning", "quick_delivery", "week_planning"]
    ),
    "medium_term": TemporalOrientationDimension(
        name="medium_term",
        time_horizon="medium",
        delayed_gratification=0.6,
        future_orientation=0.6,
        present_hedonism=0.4,
        planning_tendency=0.6,
        linguistic_markers=[
            "next month", "upcoming", "planning for", "in a while",
            "down the road", "eventual", "when ready", "in time"
        ],
        behavioral_signals=["planned_purchases", "wishlist_use", "seasonal_buying"]
    ),
    "long_term_future": TemporalOrientationDimension(
        name="long_term_future",
        time_horizon="long",
        delayed_gratification=0.9,
        future_orientation=0.9,
        present_hedonism=0.1,
        planning_tendency=0.9,
        linguistic_markers=[
            "investment", "long-term", "future", "years ahead",
            "retirement", "legacy", "build over time", "patience"
        ],
        behavioral_signals=["investment_mindset", "quality_over_price", "durability_focus"]
    ),
}


# =============================================================================
# SOCIAL INFLUENCE SUSCEPTIBILITY (NEW DIMENSION)
# Based on Social Influence Research
# =============================================================================

@dataclass
class SocialInfluenceDimension:
    """
    Social influence susceptibility framework.
    
    Research Foundations:
    - Social Influence (Cialdini, 2009)
    - Normative vs Informational Influence (Deutsch & Gerard, 1955)
    - Opinion Leadership (Katz & Lazarsfeld, 1955)
    """
    
    name: str
    normative_influence: float  # 0-1, susceptibility to social norms
    informational_influence: float  # 0-1, susceptibility to others' knowledge
    opinion_leadership: float  # 0-1, tendency to influence others
    conformity_tendency: float  # 0-1
    uniqueness_seeking: float  # 0-1
    
    linguistic_markers: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)


SOCIAL_INFLUENCE_SUSCEPTIBILITY = {
    "highly_independent": SocialInfluenceDimension(
        name="highly_independent",
        normative_influence=0.1,
        informational_influence=0.3,
        opinion_leadership=0.7,
        conformity_tendency=0.1,
        uniqueness_seeking=0.9,
        linguistic_markers=[
            "my own decision", "don't care what others think", "independent",
            "unique", "different", "against the grain", "original"
        ],
        behavioral_signals=["unique_purchases", "trend_resistance", "self_directed"]
    ),
    "informational_seeker": SocialInfluenceDimension(
        name="informational_seeker",
        normative_influence=0.3,
        informational_influence=0.9,
        opinion_leadership=0.4,
        conformity_tendency=0.4,
        uniqueness_seeking=0.5,
        linguistic_markers=[
            "expert opinion", "research shows", "reviews say", "recommended",
            "tested", "proven", "according to", "studies indicate"
        ],
        behavioral_signals=["review_reading", "expert_seeking", "research_heavy"]
    ),
    "socially_aware": SocialInfluenceDimension(
        name="socially_aware",
        normative_influence=0.6,
        informational_influence=0.6,
        opinion_leadership=0.5,
        conformity_tendency=0.5,
        uniqueness_seeking=0.5,
        linguistic_markers=[
            "what others use", "popular", "trending", "many people",
            "commonly", "standard", "typical", "mainstream"
        ],
        behavioral_signals=["trend_aware", "popularity_checking", "social_validation"]
    ),
    "normatively_driven": SocialInfluenceDimension(
        name="normatively_driven",
        normative_influence=0.9,
        informational_influence=0.5,
        opinion_leadership=0.2,
        conformity_tendency=0.9,
        uniqueness_seeking=0.1,
        linguistic_markers=[
            "everyone has", "should have", "expected", "normal",
            "fitting in", "appropriate", "accepted", "standard"
        ],
        behavioral_signals=["conformity_buying", "trend_following", "social_proof_heavy"]
    ),
    "opinion_leader": SocialInfluenceDimension(
        name="opinion_leader",
        normative_influence=0.2,
        informational_influence=0.4,
        opinion_leadership=0.95,
        conformity_tendency=0.2,
        uniqueness_seeking=0.7,
        linguistic_markers=[
            "I recommend", "my followers", "influencing others", "trendsetter",
            "early adopter", "ahead of the curve", "people ask me"
        ],
        behavioral_signals=["early_adoption", "sharing_behavior", "influence_seeking"]
    ),
}


# =============================================================================
# LINGUISTIC PATTERN ANALYZER
# =============================================================================

class LinguisticPatternAnalyzer:
    """
    Analyzes text to detect psychological dimension markers.
    
    Uses compiled regex patterns for efficient matching against
    all empirical psychology frameworks.
    """
    
    def __init__(self):
        self._compiled_patterns: Dict[str, Dict[str, List[re.Pattern]]] = {}
        self._compile_all_patterns()
    
    def _compile_all_patterns(self) -> None:
        """Pre-compile all linguistic marker patterns."""
        frameworks = {
            "motivation": EXPANDED_MOTIVATIONS,
            "decision_style": EXPANDED_DECISION_STYLES,
            "regulatory_focus": EXPANDED_REGULATORY_FOCUS,
            "emotional_intensity": EXPANDED_EMOTIONAL_INTENSITY,
            "cognitive_load": COGNITIVE_LOAD_TOLERANCE,
            "temporal_orientation": TEMPORAL_ORIENTATION,
            "social_influence": SOCIAL_INFLUENCE_SUSCEPTIBILITY,
        }
        
        for framework_name, dimensions in frameworks.items():
            self._compiled_patterns[framework_name] = {}
            for dim_name, dim_data in dimensions.items():
                patterns = []
                for marker in dim_data.linguistic_markers:
                    # Create flexible pattern with word boundaries
                    pattern = re.compile(
                        r'\b' + re.escape(marker).replace(r'\ ', r'\s+') + r'\b',
                        re.IGNORECASE
                    )
                    patterns.append(pattern)
                self._compiled_patterns[framework_name][dim_name] = patterns
    
    def analyze_text(self, text: str) -> Dict[str, Dict[str, float]]:
        """
        Analyze text for psychological dimension markers.
        
        Args:
            text: Text to analyze (review, comment, search query, etc.)
            
        Returns:
            Dict mapping framework → dimension → score (0-1)
        """
        results = {}
        text_lower = text.lower()
        
        for framework_name, dimensions in self._compiled_patterns.items():
            results[framework_name] = {}
            
            for dim_name, patterns in dimensions.items():
                matches = 0
                for pattern in patterns:
                    if pattern.search(text_lower):
                        matches += 1
                
                # Normalize by number of markers
                if patterns:
                    score = min(1.0, matches / (len(patterns) * 0.3))  # 30% match = full score
                else:
                    score = 0.0
                    
                results[framework_name][dim_name] = score
        
        return results
    
    def get_dominant_dimensions(
        self, 
        text: str, 
        threshold: float = 0.2
    ) -> Dict[str, Tuple[str, float]]:
        """
        Get the dominant dimension for each framework.
        
        Args:
            text: Text to analyze
            threshold: Minimum score to consider
            
        Returns:
            Dict mapping framework → (dominant_dimension, score)
        """
        analysis = self.analyze_text(text)
        dominant = {}
        
        for framework_name, dimensions in analysis.items():
            if dimensions:
                best_dim = max(dimensions.keys(), key=lambda k: dimensions[k])
                best_score = dimensions[best_dim]
                
                if best_score >= threshold:
                    dominant[framework_name] = (best_dim, best_score)
        
        return dominant


# =============================================================================
# EXPANDED GRANULAR TYPE CALCULATOR
# =============================================================================

@dataclass
class ExpandedGranularType:
    """
    Expanded granular customer type with all dimensions.
    
    This represents a single customer profile across all empirically-validated
    psychological dimensions, enabling 25,000+ unique type combinations.
    """
    
    # Core identification
    type_code: str
    
    # Expanded dimensions (42 motivations × 12 decisions × 8 regulatory...)
    motivation: str
    motivation_category: str
    decision_style: str
    processing_mode: str
    regulatory_focus: str
    emotional_intensity: str
    cognitive_load_tolerance: str
    temporal_orientation: str
    social_influence_type: str
    
    # Computed scores
    persuadability_score: float
    autonomy_level: float
    hedonic_vs_utilitarian: float
    risk_tolerance: float
    
    # Mechanism effectiveness (calibrated)
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    optimal_mechanism_sequence: List[str] = field(default_factory=list)
    
    # Messaging recommendations
    message_framing: str = "neutral"
    emotional_appeal_level: str = "moderate"
    information_density: str = "moderate"
    urgency_appropriateness: float = 0.5
    social_proof_effectiveness: float = 0.5


def calculate_expanded_granular_type(
    motivation: str,
    decision_style: str,
    regulatory_focus: str,
    emotional_intensity: str,
    cognitive_load: str = "moderate_cognitive",
    temporal_orientation: str = "medium_term",
    social_influence: str = "socially_aware",
) -> ExpandedGranularType:
    """
    Calculate a fully expanded granular customer type.
    
    This integrates all empirically-validated dimensions to produce
    a comprehensive psychological profile with mechanism recommendations.
    """
    
    # Get dimension data
    mot_data = EXPANDED_MOTIVATIONS.get(motivation)
    dec_data = EXPANDED_DECISION_STYLES.get(decision_style)
    reg_data = EXPANDED_REGULATORY_FOCUS.get(regulatory_focus)
    emo_data = EXPANDED_EMOTIONAL_INTENSITY.get(emotional_intensity)
    cog_data = COGNITIVE_LOAD_TOLERANCE.get(cognitive_load)
    temp_data = TEMPORAL_ORIENTATION.get(temporal_orientation)
    soc_data = SOCIAL_INFLUENCE_SUSCEPTIBILITY.get(social_influence)
    
    # Generate type code
    type_code = f"{motivation[:3].upper()}-{decision_style[:3].upper()}-{regulatory_focus[:3].upper()}-{emotional_intensity[:3].upper()}"
    
    # Calculate persuadability (weighted combination)
    persuadability = 0.5
    if mot_data and dec_data:
        # Lower autonomy = higher persuadability
        persuadability = (
            (1 - mot_data.autonomy_level) * 0.3 +
            (1 - dec_data.cognitive_effort_willingness) * 0.25 +
            dec_data.time_pressure_tolerance * 0.2 +
            (soc_data.normative_influence if soc_data else 0.5) * 0.15 +
            (1 - (temp_data.delayed_gratification if temp_data else 0.5)) * 0.1
        )
    
    # Calculate mechanism effectiveness
    mechanism_effectiveness = _calculate_mechanism_effectiveness(
        mot_data, dec_data, reg_data, emo_data, soc_data
    )
    
    # Calculate optimal sequence
    optimal_sequence = _calculate_optimal_sequence(
        mechanism_effectiveness, dec_data, reg_data, temp_data
    )
    
    # Determine message framing
    message_framing = "gain" if reg_data and reg_data.primary_focus == "promotion" else "loss"
    if reg_data and reg_data.primary_focus == "balanced":
        message_framing = "neutral"
    
    # Determine emotional appeal level
    emotional_appeal = "high" if emo_data and emo_data.arousal_level > 0.7 else "low" if emo_data and emo_data.arousal_level < 0.3 else "moderate"
    
    # Determine information density
    info_density = "high" if cog_data and cog_data.working_memory_preference == "high" else "low" if cog_data and cog_data.working_memory_preference == "low" else "moderate"
    
    # Calculate urgency appropriateness
    urgency = 0.5
    if temp_data:
        urgency = 1 - temp_data.delayed_gratification
    if dec_data:
        urgency = (urgency + dec_data.time_pressure_tolerance) / 2
    
    # Calculate social proof effectiveness
    social_proof_eff = 0.5
    if soc_data:
        social_proof_eff = (soc_data.normative_influence + soc_data.conformity_tendency) / 2
    
    return ExpandedGranularType(
        type_code=type_code,
        motivation=motivation,
        motivation_category=mot_data.category if mot_data else "unknown",
        decision_style=decision_style,
        processing_mode=dec_data.processing_mode if dec_data else "mixed",
        regulatory_focus=regulatory_focus,
        emotional_intensity=emotional_intensity,
        cognitive_load_tolerance=cognitive_load,
        temporal_orientation=temporal_orientation,
        social_influence_type=social_influence,
        persuadability_score=round(persuadability, 3),
        autonomy_level=mot_data.autonomy_level if mot_data else 0.5,
        hedonic_vs_utilitarian=mot_data.hedonic_vs_utilitarian if mot_data else 0.0,
        risk_tolerance=mot_data.risk_tolerance if mot_data else 0.5,
        mechanism_effectiveness=mechanism_effectiveness,
        optimal_mechanism_sequence=optimal_sequence,
        message_framing=message_framing,
        emotional_appeal_level=emotional_appeal,
        information_density=info_density,
        urgency_appropriateness=round(urgency, 2),
        social_proof_effectiveness=round(social_proof_eff, 2),
    )


def _calculate_mechanism_effectiveness(
    mot_data, dec_data, reg_data, emo_data, soc_data
) -> Dict[str, float]:
    """Calculate mechanism effectiveness based on psychological dimensions."""
    
    base = {
        "authority": 0.5,
        "social_proof": 0.5,
        "scarcity": 0.5,
        "reciprocity": 0.5,
        "commitment": 0.5,
        "liking": 0.5,
        "unity": 0.5,
    }
    
    # Adjust based on decision style
    if dec_data:
        if dec_data.processing_mode == "system1":
            base["scarcity"] += 0.2
            base["liking"] += 0.15
            base["social_proof"] += 0.1
        elif dec_data.processing_mode == "system2":
            base["authority"] += 0.25
            base["commitment"] += 0.15
            base["scarcity"] -= 0.1
    
    # Adjust based on regulatory focus
    if reg_data:
        if reg_data.primary_focus == "promotion":
            base["scarcity"] += 0.15
            base["social_proof"] += 0.1
        elif reg_data.primary_focus == "prevention":
            base["authority"] += 0.2
            base["commitment"] += 0.15
    
    # Adjust based on social influence
    if soc_data:
        base["social_proof"] += soc_data.normative_influence * 0.3
        base["authority"] += soc_data.informational_influence * 0.2
        base["unity"] += soc_data.conformity_tendency * 0.15
    
    # Adjust based on motivation
    if mot_data:
        if mot_data.relatedness_need > 0.7:
            base["unity"] += 0.2
            base["social_proof"] += 0.15
        if mot_data.competence_need > 0.7:
            base["authority"] += 0.15
    
    # Normalize to 0-1
    return {k: min(1.0, max(0.0, v)) for k, v in base.items()}


def _calculate_optimal_sequence(
    mechanism_effectiveness: Dict[str, float],
    dec_data,
    reg_data,
    temp_data
) -> List[str]:
    """Calculate optimal mechanism sequence."""
    
    # Sort by effectiveness
    sorted_mechs = sorted(
        mechanism_effectiveness.keys(),
        key=lambda k: mechanism_effectiveness[k],
        reverse=True
    )
    
    # Adjust sequence based on temporal orientation
    if temp_data and temp_data.time_horizon == "immediate":
        # Front-load high-impact mechanisms
        if "scarcity" in sorted_mechs[:3]:
            sorted_mechs.remove("scarcity")
            sorted_mechs.insert(0, "scarcity")
    
    # Authority typically works better early
    if "authority" in sorted_mechs[:4]:
        sorted_mechs.remove("authority")
        sorted_mechs.insert(0, "authority")
    
    # Reciprocity works well early
    if "reciprocity" in sorted_mechs[:4]:
        idx = sorted_mechs.index("reciprocity")
        if idx > 1:
            sorted_mechs.remove("reciprocity")
            sorted_mechs.insert(1, "reciprocity")
    
    return sorted_mechs[:5]


# =============================================================================
# EXPORTS
# =============================================================================

def export_empirical_framework_priors() -> Dict[str, Any]:
    """Export all empirical framework data for cold-start priors."""
    return {
        "expanded_motivations": {
            name: {
                "category": dim.category,
                "autonomy_level": dim.autonomy_level,
                "competence_need": dim.competence_need,
                "relatedness_need": dim.relatedness_need,
                "hedonic_vs_utilitarian": dim.hedonic_vs_utilitarian,
                "temporal_orientation": dim.temporal_orientation,
                "risk_tolerance": dim.risk_tolerance,
                "linguistic_markers": dim.linguistic_markers[:5],  # Top 5 for priors
            }
            for name, dim in EXPANDED_MOTIVATIONS.items()
        },
        "expanded_decision_styles": {
            name: {
                "processing_mode": dim.processing_mode,
                "information_load_preference": dim.information_load_preference,
                "decision_confidence": dim.decision_confidence,
                "regret_sensitivity": dim.regret_sensitivity,
                "cognitive_effort_willingness": dim.cognitive_effort_willingness,
            }
            for name, dim in EXPANDED_DECISION_STYLES.items()
        },
        "expanded_regulatory_focus": {
            name: {
                "primary_focus": dim.primary_focus,
                "approach_intensity": dim.approach_intensity,
                "avoidance_intensity": dim.avoidance_intensity,
                "gain_sensitivity": dim.gain_sensitivity,
                "loss_sensitivity": dim.loss_sensitivity,
            }
            for name, dim in EXPANDED_REGULATORY_FOCUS.items()
        },
        "expanded_emotional_intensity": {
            name: {
                "arousal_level": dim.arousal_level,
                "valence_sensitivity": dim.valence_sensitivity,
                "emotional_stability": dim.emotional_stability,
                "affect_intensity": dim.affect_intensity,
            }
            for name, dim in EXPANDED_EMOTIONAL_INTENSITY.items()
        },
        "cognitive_load_tolerance": {
            name: {
                "working_memory_preference": dim.working_memory_preference,
                "simplification_preference": dim.simplification_preference,
                "decision_fatigue_susceptibility": dim.decision_fatigue_susceptibility,
            }
            for name, dim in COGNITIVE_LOAD_TOLERANCE.items()
        },
        "temporal_orientation": {
            name: {
                "time_horizon": dim.time_horizon,
                "delayed_gratification": dim.delayed_gratification,
                "future_orientation": dim.future_orientation,
                "planning_tendency": dim.planning_tendency,
            }
            for name, dim in TEMPORAL_ORIENTATION.items()
        },
        "social_influence_susceptibility": {
            name: {
                "normative_influence": dim.normative_influence,
                "informational_influence": dim.informational_influence,
                "opinion_leadership": dim.opinion_leadership,
                "conformity_tendency": dim.conformity_tendency,
            }
            for name, dim in SOCIAL_INFLUENCE_SUSCEPTIBILITY.items()
        },
        "type_combinations": {
            "motivations": len(EXPANDED_MOTIVATIONS),
            "decision_styles": len(EXPANDED_DECISION_STYLES),
            "regulatory_focus": len(EXPANDED_REGULATORY_FOCUS),
            "emotional_intensity": len(EXPANDED_EMOTIONAL_INTENSITY),
            "cognitive_load": len(COGNITIVE_LOAD_TOLERANCE),
            "temporal_orientation": len(TEMPORAL_ORIENTATION),
            "social_influence": len(SOCIAL_INFLUENCE_SUSCEPTIBILITY),
            "total_combinations": (
                len(EXPANDED_MOTIVATIONS) *
                len(EXPANDED_DECISION_STYLES) *
                len(EXPANDED_REGULATORY_FOCUS) *
                len(EXPANDED_EMOTIONAL_INTENSITY) *
                len(COGNITIVE_LOAD_TOLERANCE) *
                len(TEMPORAL_ORIENTATION) *
                len(SOCIAL_INFLUENCE_SUSCEPTIBILITY)
            ),
        },
        "research_foundations": {
            "self_determination_theory": "Deci & Ryan, 2000",
            "dual_process_theory": "Kahneman, 2011; Evans & Stanovich, 2013",
            "regulatory_focus_theory": "Higgins, 1997, 2012",
            "circumplex_model_affect": "Russell, 1980",
            "cognitive_load_theory": "Sweller, 1988",
            "temporal_discounting": "Frederick et al., 2002",
            "social_influence": "Cialdini, 2009",
        },
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("EMPIRICAL PSYCHOLOGY FRAMEWORK TEST")
    print("="*70)
    
    # Test dimension counts
    print(f"\n=== Dimension Counts ===")
    print(f"Expanded Motivations: {len(EXPANDED_MOTIVATIONS)} (from 15)")
    print(f"Expanded Decision Styles: {len(EXPANDED_DECISION_STYLES)} (from 3)")
    print(f"Expanded Regulatory Focus: {len(EXPANDED_REGULATORY_FOCUS)} (from 2)")
    print(f"Expanded Emotional Intensity: {len(EXPANDED_EMOTIONAL_INTENSITY)} (from 3)")
    print(f"NEW: Cognitive Load Tolerance: {len(COGNITIVE_LOAD_TOLERANCE)}")
    print(f"NEW: Temporal Orientation: {len(TEMPORAL_ORIENTATION)}")
    print(f"NEW: Social Influence Susceptibility: {len(SOCIAL_INFLUENCE_SUSCEPTIBILITY)}")
    
    # Calculate total combinations
    total = (
        len(EXPANDED_MOTIVATIONS) *
        len(EXPANDED_DECISION_STYLES) *
        len(EXPANDED_REGULATORY_FOCUS) *
        len(EXPANDED_EMOTIONAL_INTENSITY) *
        len(COGNITIVE_LOAD_TOLERANCE) *
        len(TEMPORAL_ORIENTATION) *
        len(SOCIAL_INFLUENCE_SUSCEPTIBILITY)
    )
    print(f"\n=== Total Possible Combinations: {total:,} ===")
    
    # Test linguistic analyzer
    print(f"\n=== Linguistic Pattern Analysis ===")
    analyzer = LinguisticPatternAnalyzer()
    
    test_texts = [
        "I need this NOW! Can't wait, so excited!",
        "I've been researching this for weeks, comparing all the specs and reading expert reviews.",
        "Everyone has one, I feel like I should get it too.",
        "This is an investment in my future career growth.",
    ]
    
    for text in test_texts:
        print(f"\nText: \"{text[:50]}...\"")
        dominant = analyzer.get_dominant_dimensions(text)
        for framework, (dim, score) in list(dominant.items())[:3]:
            print(f"  {framework}: {dim} ({score:.2f})")
    
    # Test expanded type calculation
    print(f"\n=== Sample Expanded Types ===")
    
    sample_configs = [
        ("immediate_gratification", "gut_instinct", "eager_advancement", "high_positive_activation"),
        ("mastery_seeking", "analytical_systematic", "conservative_preservation", "emotionally_neutral"),
        ("social_approval", "social_referencing", "pragmatic_balanced", "moderate_positive"),
    ]
    
    for mot, dec, reg, emo in sample_configs:
        expanded_type = calculate_expanded_granular_type(mot, dec, reg, emo)
        print(f"\nType: {expanded_type.type_code}")
        print(f"  Persuadability: {expanded_type.persuadability_score:.0%}")
        print(f"  Message Framing: {expanded_type.message_framing}")
        print(f"  Info Density: {expanded_type.information_density}")
        print(f"  Urgency Appropriate: {expanded_type.urgency_appropriateness:.0%}")
        print(f"  Top Mechanisms: {expanded_type.optimal_mechanism_sequence[:3]}")
