# =============================================================================
# Psychological Knowledge Graph Population
# Location: adam/intelligence/knowledge_graph/populate_psychological_graph.py
# =============================================================================

"""
Populates Neo4j with psychological research knowledge:
- 9 Cognitive Mechanisms (from Enhancement #13)
- 8 Customer Archetypes (from Enhancement #13)
- 35 Psychological Constructs (from Enhancement #27)
- Mechanism → Archetype effectiveness relationships (Beta priors)
- Construct → Mechanism influence relationships
- Research citations as provenance

This encodes 25 years of psychological research as queryable graph relationships.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# COGNITIVE MECHANISMS (9 mechanisms from Enhancement #13)
# =============================================================================

class CognitiveMechanism(str, Enum):
    """The 9 cognitive mechanisms underlying persuasion."""
    CONSTRUAL_LEVEL = "construal_level"
    REGULATORY_FOCUS = "regulatory_focus"
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING = "wanting_liking"
    MIMETIC_DESIRE = "mimetic_desire"
    ATTENTION_DYNAMICS = "attention_dynamics"
    TEMPORAL_CONSTRUAL = "temporal_construal"
    IDENTITY_CONSTRUCTION = "identity_construction"
    EVOLUTIONARY_MOTIVE = "evolutionary_motive"


MECHANISM_DEFINITIONS = {
    CognitiveMechanism.CONSTRUAL_LEVEL: {
        "name": "Construal Level",
        "description": "Mental abstraction level - concrete vs abstract thinking. Affects how people process information about products and decisions.",
        "research_basis": "Construal Level Theory (Trope & Liberman, 2010)",
        "key_insight": "Psychological distance affects abstraction level; concrete appeals work better for near decisions, abstract for far",
        "applicable_contexts": ["product_evaluation", "future_planning", "comparison_shopping"],
    },
    CognitiveMechanism.REGULATORY_FOCUS: {
        "name": "Regulatory Focus",
        "description": "Promotion (gains/growth) vs Prevention (security/avoiding loss) orientation in goal pursuit.",
        "research_basis": "Regulatory Focus Theory (Higgins, 1997, 1998)",
        "key_insight": "Match message framing to regulatory focus for 'regulatory fit' - increases persuasion and value",
        "applicable_contexts": ["goal_framing", "risk_communication", "product_positioning"],
    },
    CognitiveMechanism.AUTOMATIC_EVALUATION: {
        "name": "Automatic Evaluation",
        "description": "Instant, unconscious positive/negative reactions to stimuli. System 1 processing.",
        "research_basis": "Dual Process Theory (Kahneman, 2011); Implicit Association (Greenwald et al., 1998)",
        "key_insight": "First impressions are automatic and hard to override; affects all subsequent processing",
        "applicable_contexts": ["first_impression", "brand_perception", "ad_exposure"],
    },
    CognitiveMechanism.WANTING_LIKING: {
        "name": "Wanting vs Liking",
        "description": "Dopaminergic 'wanting' (anticipation) vs opioid 'liking' (enjoyment) systems operate independently.",
        "research_basis": "Incentive Salience Theory (Berridge & Robinson, 1998)",
        "key_insight": "People can want what they don't like and like what they don't want; wanting drives action more than liking",
        "applicable_contexts": ["impulse_purchase", "anticipation_building", "reward_framing"],
    },
    CognitiveMechanism.MIMETIC_DESIRE: {
        "name": "Mimetic Desire",
        "description": "Desire is contagious - we want what others want, especially those we admire or identify with.",
        "research_basis": "Mimetic Theory (Girard, 1961); Social Proof (Cialdini, 2009)",
        "key_insight": "The desire itself is borrowed from models; authenticity is less important than the model's desire",
        "applicable_contexts": ["social_proof", "influencer_marketing", "aspirational_positioning"],
    },
    CognitiveMechanism.ATTENTION_DYNAMICS: {
        "name": "Attention Dynamics",
        "description": "How attention is captured, held, and directed affects memory encoding and decision weight.",
        "research_basis": "Attention Economics (Davenport & Beck, 2001); Salience Theory (Bordalo et al., 2012)",
        "key_insight": "What's salient is weighted more heavily; attention is the gateway to all influence",
        "applicable_contexts": ["ad_placement", "message_ordering", "visual_design"],
    },
    CognitiveMechanism.TEMPORAL_CONSTRUAL: {
        "name": "Temporal Construal",
        "description": "How time distance affects mental representation and decision making.",
        "research_basis": "Temporal Discounting (Frederick et al., 2002); Intertemporal Choice (Loewenstein & Prelec, 1992)",
        "key_insight": "Near future = concrete features; far future = abstract benefits; affects value perception",
        "applicable_contexts": ["promotion_timing", "delayed_gratification", "subscription_framing"],
    },
    CognitiveMechanism.IDENTITY_CONSTRUCTION: {
        "name": "Identity Construction",
        "description": "Products and brands are used to construct, signal, and maintain personal identity.",
        "research_basis": "Extended Self Theory (Belk, 1988); Identity-Based Motivation (Oyserman, 2009)",
        "key_insight": "Purchase decisions are identity decisions; 'Who I am' and 'Who I want to be' drive choice",
        "applicable_contexts": ["brand_positioning", "lifestyle_marketing", "self_expression"],
    },
    CognitiveMechanism.EVOLUTIONARY_MOTIVE: {
        "name": "Evolutionary Motive",
        "description": "Deep-seated motives shaped by evolution: status, mating, kin care, affiliation, self-protection.",
        "research_basis": "Evolutionary Consumer Psychology (Saad, 2007); Fundamental Motives Framework (Kenrick et al., 2010)",
        "key_insight": "Surface desires often mask deeper evolutionary motives; tap into fundamental needs",
        "applicable_contexts": ["luxury_positioning", "safety_appeals", "social_belonging"],
    },
}


# =============================================================================
# CUSTOMER ARCHETYPES (8 archetypes from Enhancement #13)
# =============================================================================

class CustomerArchetype(str, Enum):
    """The 8 customer archetypes with distinct mechanism sensitivities."""
    ACHIEVEMENT_DRIVEN = "achievement_driven"
    NOVELTY_SEEKER = "novelty_seeker"
    SOCIAL_CONNECTOR = "social_connector"
    SECURITY_FOCUSED = "security_focused"
    HARMONY_SEEKER = "harmony_seeker"
    ANALYTICAL_THINKER = "analytical_thinker"
    SPONTANEOUS_EXPERIENCER = "spontaneous_experiencer"
    TRADITIONALIST = "traditionalist"


ARCHETYPE_DEFINITIONS = {
    CustomerArchetype.ACHIEVEMENT_DRIVEN: {
        "name": "Achievement-Driven",
        "description": "Motivated by accomplishment, status, and recognition. Values efficiency and results.",
        "core_values": ["success", "recognition", "efficiency", "competence"],
        "communication_style": "Direct, results-focused, time-conscious",
        "decision_drivers": ["ROI", "competitive advantage", "status signaling"],
    },
    CustomerArchetype.NOVELTY_SEEKER: {
        "name": "Novelty Seeker",
        "description": "Drawn to new experiences, innovation, and change. Values excitement and discovery.",
        "core_values": ["innovation", "adventure", "uniqueness", "stimulation"],
        "communication_style": "Creative, bold, experiential",
        "decision_drivers": ["newness", "uniqueness", "excitement potential"],
    },
    CustomerArchetype.SOCIAL_CONNECTOR: {
        "name": "Social Connector",
        "description": "Derives value from relationships and community. Values belonging and social harmony.",
        "core_values": ["relationships", "community", "belonging", "trust"],
        "communication_style": "Warm, inclusive, story-driven",
        "decision_drivers": ["social proof", "community fit", "relationship enhancement"],
    },
    CustomerArchetype.SECURITY_FOCUSED: {
        "name": "Security-Focused",
        "description": "Prioritizes safety, stability, and risk avoidance. Values reliability and protection.",
        "core_values": ["safety", "stability", "reliability", "protection"],
        "communication_style": "Reassuring, detailed, risk-acknowledging",
        "decision_drivers": ["risk mitigation", "guarantees", "track record"],
    },
    CustomerArchetype.HARMONY_SEEKER: {
        "name": "Harmony Seeker",
        "description": "Seeks balance, peace, and simplicity. Values ease and well-being.",
        "core_values": ["balance", "simplicity", "peace", "well-being"],
        "communication_style": "Calm, balanced, stress-free",
        "decision_drivers": ["ease of use", "stress reduction", "life balance"],
    },
    CustomerArchetype.ANALYTICAL_THINKER: {
        "name": "Analytical Thinker",
        "description": "Processes information systematically. Values logic, data, and thorough understanding.",
        "core_values": ["logic", "accuracy", "thoroughness", "understanding"],
        "communication_style": "Detailed, evidence-based, comparative",
        "decision_drivers": ["specifications", "comparisons", "expert reviews"],
    },
    CustomerArchetype.SPONTANEOUS_EXPERIENCER: {
        "name": "Spontaneous Experiencer",
        "description": "Lives in the moment, driven by immediate gratification. Values enjoyment and freedom.",
        "core_values": ["pleasure", "freedom", "spontaneity", "enjoyment"],
        "communication_style": "Fun, immediate, sensory-rich",
        "decision_drivers": ["immediate reward", "pleasure potential", "low friction"],
    },
    CustomerArchetype.TRADITIONALIST: {
        "name": "Traditionalist",
        "description": "Values heritage, consistency, and proven approaches. Prefers familiar and trusted options.",
        "core_values": ["heritage", "consistency", "trust", "familiarity"],
        "communication_style": "Classic, trustworthy, heritage-focused",
        "decision_drivers": ["brand history", "tradition", "proven reliability"],
    },
}


# =============================================================================
# ARCHETYPE → MECHANISM EFFECTIVENESS (Beta priors from Enhancement #13)
# =============================================================================

# Beta distribution parameters (alpha, beta) representing prior effectiveness
# Higher alpha relative to beta = higher expected effectiveness
# alpha/(alpha+beta) = expected mean effectiveness

ARCHETYPE_MECHANISM_PRIORS: Dict[CustomerArchetype, Dict[CognitiveMechanism, Tuple[float, float]]] = {
    CustomerArchetype.ACHIEVEMENT_DRIVEN: {
        CognitiveMechanism.REGULATORY_FOCUS: (6.0, 2.0),       # Strong promotion focus
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.5),  # Status signaling
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.5, 2.5),     # Future achievement
        CognitiveMechanism.CONSTRUAL_LEVEL: (4.0, 3.0),        # Concrete goals
        CognitiveMechanism.AUTOMATIC_EVALUATION: (3.5, 3.0),
        CognitiveMechanism.WANTING_LIKING: (3.5, 3.0),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.0, 3.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 3.0),    # Status motive
    },
    CustomerArchetype.NOVELTY_SEEKER: {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (5.5, 2.0),   # Fast positive response to new
        CognitiveMechanism.WANTING_LIKING: (5.0, 2.5),         # Anticipation of novelty
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.5),  # Unique identity
        CognitiveMechanism.ATTENTION_DYNAMICS: (4.5, 2.5),     # Drawn to novel stimuli
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.5, 3.0),
        CognitiveMechanism.REGULATORY_FOCUS: (4.0, 3.0),       # Promotion focus
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.5, 3.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.5, 3.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0),
    },
    CustomerArchetype.SOCIAL_CONNECTOR: {
        CognitiveMechanism.MIMETIC_DESIRE: (6.5, 1.5),         # Strong social modeling
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.0),  # Social identity
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.5, 2.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.5, 2.5),    # Affiliation motive
        CognitiveMechanism.WANTING_LIKING: (4.0, 3.0),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.5, 3.0),
        CognitiveMechanism.REGULATORY_FOCUS: (3.5, 3.0),
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 3.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.0, 3.5),
    },
    CustomerArchetype.SECURITY_FOCUSED: {
        CognitiveMechanism.REGULATORY_FOCUS: (6.0, 2.0),       # Strong prevention focus
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (5.5, 2.0),     # Long-term thinking
        CognitiveMechanism.CONSTRUAL_LEVEL: (4.5, 2.5),        # Concrete, detailed
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.5, 2.5),    # Self-protection
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.0, 3.0),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.5, 3.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.0, 3.5),
        CognitiveMechanism.WANTING_LIKING: (2.5, 3.5),         # Less impulsive
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.0),
    },
    CustomerArchetype.HARMONY_SEEKER: {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (5.0, 2.0),   # Positive = peaceful
        CognitiveMechanism.MIMETIC_DESIRE: (4.5, 2.5),         # Fits with others
        CognitiveMechanism.WANTING_LIKING: (4.5, 2.5),         # Pleasant experiences
        CognitiveMechanism.REGULATORY_FOCUS: (4.0, 3.0),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.5, 3.0),
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.5, 3.0),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.5, 3.0),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0),
    },
    CustomerArchetype.ANALYTICAL_THINKER: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (5.5, 2.0),        # Detailed, concrete
        CognitiveMechanism.REGULATORY_FOCUS: (5.0, 2.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.5, 2.5),     # Considers future
        CognitiveMechanism.ATTENTION_DYNAMICS: (4.0, 3.0),     # Focused attention
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.5, 3.0),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (3.0, 3.5),   # Less automatic
        CognitiveMechanism.WANTING_LIKING: (3.0, 3.5),         # Less impulsive
        CognitiveMechanism.MIMETIC_DESIRE: (2.5, 3.5),         # Less social influence
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.0, 3.0),
    },
    CustomerArchetype.SPONTANEOUS_EXPERIENCER: {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (6.0, 1.5),   # Fast, intuitive
        CognitiveMechanism.WANTING_LIKING: (5.5, 2.0),         # Immediate pleasure
        CognitiveMechanism.ATTENTION_DYNAMICS: (5.0, 2.5),     # Captured easily
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 3.0),    # Pleasure seeking
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.0, 3.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.5, 3.0),
        CognitiveMechanism.REGULATORY_FOCUS: (3.0, 3.5),
        CognitiveMechanism.CONSTRUAL_LEVEL: (2.5, 3.5),        # Less deliberate
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (2.0, 4.0),     # Present-focused
    },
    CustomerArchetype.TRADITIONALIST: {
        CognitiveMechanism.REGULATORY_FOCUS: (5.5, 2.0),       # Prevention focus
        CognitiveMechanism.MIMETIC_DESIRE: (5.0, 2.5),         # Follow tradition
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.5, 2.5),  # Traditional identity
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.0, 3.0),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.0, 3.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 3.0),
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.5, 3.0),
        CognitiveMechanism.WANTING_LIKING: (3.0, 3.5),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.5),
    },
}


# =============================================================================
# PSYCHOLOGICAL CONSTRUCTS (35 from Enhancement #27)
# =============================================================================

@dataclass
class ConstructDefinition:
    """Definition of a psychological construct."""
    id: str
    name: str
    domain: str
    description: str
    scale_anchors: Tuple[str, str]  # (low_end, high_end)
    research_basis: str
    key_citations: List[str]
    mechanism_influences: Dict[str, float]  # mechanism_id -> influence strength
    related_constructs: Dict[str, float]  # construct_id -> correlation


CONSTRUCT_DEFINITIONS: Dict[str, ConstructDefinition] = {
    # Domain 1: Cognitive Processing
    "cognitive_nfc": ConstructDefinition(
        id="cognitive_nfc",
        name="Need for Cognition",
        domain="cognitive_processing",
        description="Tendency to engage in and enjoy effortful cognitive activities",
        scale_anchors=("Avoids complex thinking", "Enjoys complex thinking"),
        research_basis="Cacioppo & Petty (1982)",
        key_citations=["Cacioppo & Petty (1982)", "Petty & Cacioppo (1983)"],
        mechanism_influences={
            "construal_level": 0.3,  # High NFC -> more abstract processing
            "automatic_evaluation": -0.2,  # Less reliance on automatic
            "attention_dynamics": 0.25,  # More sustained attention
        },
        related_constructs={"info_holistic_analytic": 0.4, "decision_maximizer": 0.35},
    ),
    "cognitive_psp": ConstructDefinition(
        id="cognitive_psp",
        name="Processing Speed Preference",
        domain="cognitive_processing",
        description="Preference for System 1 (fast, intuitive) vs System 2 (slow, deliberate) processing",
        scale_anchors=("Fast/intuitive", "Slow/deliberate"),
        research_basis="Kahneman (2011) Thinking, Fast and Slow",
        key_citations=["Kahneman (2011)", "Stanovich & West (2000)"],
        mechanism_influences={
            "automatic_evaluation": -0.4,  # High PSP = less automatic
            "construal_level": 0.2,
            "attention_dynamics": 0.2,
        },
        related_constructs={"cognitive_nfc": 0.5, "cognitive_hri": -0.45},
    ),
    "cognitive_hri": ConstructDefinition(
        id="cognitive_hri",
        name="Heuristic Reliance Index",
        domain="cognitive_processing",
        description="Reliance on cognitive shortcuts vs systematic processing",
        scale_anchors=("Systematic processing", "Heuristic shortcuts"),
        research_basis="Tversky & Kahneman (1974); Gigerenzer & Gaissmaier (2011)",
        key_citations=["Tversky & Kahneman (1974)", "Gigerenzer & Gaissmaier (2011)"],
        mechanism_influences={
            "automatic_evaluation": 0.4,  # High HRI = more automatic
            "mimetic_desire": 0.25,  # Follows others as shortcut
            "construal_level": -0.2,
        },
        related_constructs={"cognitive_psp": -0.45, "cognitive_nfc": -0.4},
    ),
    
    # Domain 2: Self-Regulatory
    "selfreg_sm": ConstructDefinition(
        id="selfreg_sm",
        name="Self-Monitoring",
        domain="self_regulatory",
        description="Monitoring and controlling self-presentation to fit social situations",
        scale_anchors=("Low self-monitoring", "High self-monitoring"),
        research_basis="Snyder (1974)",
        key_citations=["Snyder (1974)", "Gangestad & Snyder (2000)"],
        mechanism_influences={
            "identity_construction": 0.35,
            "mimetic_desire": 0.3,
            "automatic_evaluation": 0.15,
        },
        related_constructs={"social_sco": 0.4, "social_conformity": 0.35},
    ),
    "selfreg_rf": ConstructDefinition(
        id="selfreg_rf",
        name="Regulatory Focus",
        domain="self_regulatory",
        description="Promotion (gains/growth) vs Prevention (security/loss avoidance) orientation",
        scale_anchors=("Prevention-focused", "Promotion-focused"),
        research_basis="Higgins (1997, 1998)",
        key_citations=["Higgins (1997)", "Higgins (1998)", "Crowe & Higgins (1997)"],
        mechanism_influences={
            "regulatory_focus": 0.5,  # Direct mapping
            "temporal_construal": 0.2,
            "wanting_liking": 0.15,
        },
        related_constructs={"motivation_achievement": 0.4, "uncertainty_at": 0.3},
    ),
    "selfreg_lam": ConstructDefinition(
        id="selfreg_lam",
        name="Locomotion-Assessment Mode",
        domain="self_regulatory",
        description="Preference for action (locomotion) vs evaluation (assessment)",
        scale_anchors=("Assessment-focused", "Locomotion-focused"),
        research_basis="Kruglanski et al. (2000)",
        key_citations=["Kruglanski et al. (2000)", "Avnet & Higgins (2003)"],
        mechanism_influences={
            "automatic_evaluation": 0.2,
            "attention_dynamics": 0.15,
            "wanting_liking": 0.25,
        },
        related_constructs={"decision_maximizer": -0.35, "cognitive_psp": -0.25},
    ),
    
    # Domain 3: Temporal Psychology
    "temporal_orientation": ConstructDefinition(
        id="temporal_orientation",
        name="Temporal Orientation",
        domain="temporal_psychology",
        description="Past, present, or future temporal focus",
        scale_anchors=("Past/present focused", "Future focused"),
        research_basis="Zimbardo & Boyd (1999)",
        key_citations=["Zimbardo & Boyd (1999)", "Zimbardo & Boyd (2008)"],
        mechanism_influences={
            "temporal_construal": 0.45,
            "construal_level": 0.2,
            "regulatory_focus": 0.15,
        },
        related_constructs={"temporal_fsc": 0.5, "temporal_ph": 0.45},
    ),
    "temporal_fsc": ConstructDefinition(
        id="temporal_fsc",
        name="Future Self-Continuity",
        domain="temporal_psychology",
        description="Psychological connection to and concern for future self",
        scale_anchors=("Disconnected from future self", "Connected to future self"),
        research_basis="Ersner-Hershfield (2009)",
        key_citations=["Ersner-Hershfield (2009)", "Ersner-Hershfield et al. (2009)"],
        mechanism_influences={
            "temporal_construal": 0.4,
            "identity_construction": 0.3,
            "regulatory_focus": 0.2,
        },
        related_constructs={"temporal_orientation": 0.5, "temporal_ddr": -0.45},
    ),
    "temporal_ddr": ConstructDefinition(
        id="temporal_ddr",
        name="Delay Discounting Rate",
        domain="temporal_psychology",
        description="Rate at which future rewards are discounted relative to immediate rewards",
        scale_anchors=("Patient (low discounting)", "Impatient (high discounting)"),
        research_basis="Frederick et al. (2002)",
        key_citations=["Frederick et al. (2002)", "Loewenstein & Prelec (1992)"],
        mechanism_influences={
            "temporal_construal": -0.4,
            "wanting_liking": 0.35,
            "automatic_evaluation": 0.25,
        },
        related_constructs={"temporal_fsc": -0.45, "temporal_ph": -0.4},
    ),
    "temporal_ph": ConstructDefinition(
        id="temporal_ph",
        name="Planning Horizon",
        domain="temporal_psychology",
        description="Time horizon for planning and decision making",
        scale_anchors=("Short-term planning", "Long-term planning"),
        research_basis="Lynch et al. (2010)",
        key_citations=["Lynch et al. (2010)", "Zauberman et al. (2009)"],
        mechanism_influences={
            "temporal_construal": 0.4,
            "construal_level": 0.25,
            "regulatory_focus": 0.2,
        },
        related_constructs={"temporal_orientation": 0.45, "temporal_ddr": -0.4},
    ),
    
    # Domain 4: Decision Making
    "decision_maximizer": ConstructDefinition(
        id="decision_maximizer",
        name="Maximizer-Satisficer",
        domain="decision_making",
        description="Optimization (maximizing) vs 'good enough' (satisficing) preference",
        scale_anchors=("Satisficer", "Maximizer"),
        research_basis="Schwartz et al. (2002)",
        key_citations=["Schwartz et al. (2002)", "Schwartz (2004)"],
        mechanism_influences={
            "construal_level": 0.2,
            "attention_dynamics": 0.25,
            "automatic_evaluation": -0.2,
        },
        related_constructs={"cognitive_nfc": 0.35, "decision_regret": 0.4},
    ),
    "decision_regret": ConstructDefinition(
        id="decision_regret",
        name="Regret Anticipation Style",
        domain="decision_making",
        description="Tendency to anticipate and be influenced by potential regret",
        scale_anchors=("Low regret anticipation", "High regret anticipation"),
        research_basis="Zeelenberg (1999)",
        key_citations=["Zeelenberg (1999)", "Zeelenberg & Pieters (2007)"],
        mechanism_influences={
            "regulatory_focus": -0.3,  # Prevention orientation
            "temporal_construal": 0.2,
            "wanting_liking": -0.15,
        },
        related_constructs={"decision_maximizer": 0.4, "uncertainty_nfc": 0.35},
    ),
    "decision_overload": ConstructDefinition(
        id="decision_overload",
        name="Choice Overload Susceptibility",
        domain="decision_making",
        description="Susceptibility to being overwhelmed by too many options",
        scale_anchors=("Choice-resilient", "Choice-overwhelmed"),
        research_basis="Iyengar & Lepper (2000)",
        key_citations=["Iyengar & Lepper (2000)", "Scheibehenne et al. (2010)"],
        mechanism_influences={
            "attention_dynamics": -0.3,
            "automatic_evaluation": 0.25,  # Falls back to heuristics
            "construal_level": -0.2,
        },
        related_constructs={"decision_maximizer": 0.35, "cognitive_hri": 0.3},
    ),
    
    # Domain 5: Social-Cognitive
    "social_sco": ConstructDefinition(
        id="social_sco",
        name="Social Comparison Orientation",
        domain="social_cognitive",
        description="Tendency to compare self to others",
        scale_anchors=("Low social comparison", "High social comparison"),
        research_basis="Festinger (1954)",
        key_citations=["Festinger (1954)", "Gibbons & Buunk (1999)"],
        mechanism_influences={
            "mimetic_desire": 0.4,
            "identity_construction": 0.3,
            "automatic_evaluation": 0.15,
        },
        related_constructs={"social_conformity": 0.4, "selfreg_sm": 0.4},
    ),
    "social_conformity": ConstructDefinition(
        id="social_conformity",
        name="Conformity Susceptibility",
        domain="social_cognitive",
        description="Susceptibility to social influence and conformity pressure",
        scale_anchors=("Independent", "Conformist"),
        research_basis="Cialdini (2009)",
        key_citations=["Cialdini (2009)", "Asch (1951)"],
        mechanism_influences={
            "mimetic_desire": 0.45,
            "automatic_evaluation": 0.2,
            "identity_construction": 0.15,
        },
        related_constructs={"social_sco": 0.4, "social_nfu": -0.5},
    ),
    "social_nfu": ConstructDefinition(
        id="social_nfu",
        name="Need for Uniqueness",
        domain="social_cognitive",
        description="Desire to be distinct from others",
        scale_anchors=("Conformity-seeking", "Uniqueness-seeking"),
        research_basis="Snyder & Fromkin (1977)",
        key_citations=["Snyder & Fromkin (1977)", "Tian et al. (2001)"],
        mechanism_influences={
            "identity_construction": 0.4,
            "mimetic_desire": -0.3,
            "automatic_evaluation": 0.15,
        },
        related_constructs={"social_conformity": -0.5, "social_oli": 0.3},
    ),
    "social_oli": ConstructDefinition(
        id="social_oli",
        name="Opinion Leadership Index",
        domain="social_cognitive",
        description="Tendency to influence others' opinions and decisions",
        scale_anchors=("Opinion follower", "Opinion leader"),
        research_basis="King & Summers (1970)",
        key_citations=["King & Summers (1970)", "Flynn et al. (1996)"],
        mechanism_influences={
            "identity_construction": 0.35,
            "mimetic_desire": 0.2,  # Creates desire in others
            "attention_dynamics": 0.2,
        },
        related_constructs={"social_nfu": 0.3, "motivation_achievement": 0.35},
    ),
    
    # Domain 6: Uncertainty Processing
    "uncertainty_at": ConstructDefinition(
        id="uncertainty_at",
        name="Ambiguity Tolerance",
        domain="uncertainty_processing",
        description="Comfort with ambiguous or uncertain situations",
        scale_anchors=("Ambiguity intolerant", "Ambiguity tolerant"),
        research_basis="Budner (1962)",
        key_citations=["Budner (1962)", "Furnham & Ribchester (1995)"],
        mechanism_influences={
            "regulatory_focus": 0.25,  # Promotion focus tolerates ambiguity
            "automatic_evaluation": 0.15,
            "construal_level": 0.2,
        },
        related_constructs={"uncertainty_nfc": -0.55, "selfreg_rf": 0.3},
    ),
    "uncertainty_nfc": ConstructDefinition(
        id="uncertainty_nfc",
        name="Need for Closure",
        domain="uncertainty_processing",
        description="Desire for definite answers and discomfort with ambiguity",
        scale_anchors=("Open to ambiguity", "Needs closure"),
        research_basis="Kruglanski (1990)",
        key_citations=["Kruglanski (1990)", "Webster & Kruglanski (1994)"],
        mechanism_influences={
            "regulatory_focus": -0.2,  # Prevention focus
            "automatic_evaluation": 0.25,  # Quick closure via heuristics
            "attention_dynamics": -0.15,
        },
        related_constructs={"uncertainty_at": -0.55, "decision_regret": 0.35},
    ),
    
    # Domain 7: Information Processing
    "info_vvs": ConstructDefinition(
        id="info_vvs",
        name="Visualizer-Verbalizer",
        domain="information_processing",
        description="Preference for visual vs verbal information",
        scale_anchors=("Verbalizer", "Visualizer"),
        research_basis="Paivio (1986)",
        key_citations=["Paivio (1986)", "Childers et al. (1985)"],
        mechanism_influences={
            "attention_dynamics": 0.2,
            "automatic_evaluation": 0.15,
        },
        related_constructs={"info_holistic_analytic": 0.25},
    ),
    "info_holistic_analytic": ConstructDefinition(
        id="info_holistic_analytic",
        name="Holistic-Analytic Style",
        domain="information_processing",
        description="Holistic (context-dependent) vs analytic (context-independent) processing",
        scale_anchors=("Analytic", "Holistic"),
        research_basis="Riding & Cheema (1991)",
        key_citations=["Riding & Cheema (1991)", "Nisbett et al. (2001)"],
        mechanism_influences={
            "construal_level": -0.25,  # Analytic = concrete
            "attention_dynamics": 0.2,
            "automatic_evaluation": 0.15,
        },
        related_constructs={"cognitive_nfc": 0.4, "info_field_independence": -0.45},
    ),
    "info_field_independence": ConstructDefinition(
        id="info_field_independence",
        name="Field Independence",
        domain="information_processing",
        description="Ability to separate objects from surrounding context",
        scale_anchors=("Field dependent", "Field independent"),
        research_basis="Witkin & Goodenough (1981)",
        key_citations=["Witkin & Goodenough (1981)", "Witkin et al. (1977)"],
        mechanism_influences={
            "attention_dynamics": 0.25,
            "construal_level": 0.2,
            "automatic_evaluation": -0.15,
        },
        related_constructs={"info_holistic_analytic": -0.45, "cognitive_nfc": 0.35},
    ),
    
    # Domain 8: Motivational Profile
    "motivation_achievement": ConstructDefinition(
        id="motivation_achievement",
        name="Achievement Motivation",
        domain="motivational_profile",
        description="Drive for accomplishment and excellence",
        scale_anchors=("Low achievement drive", "High achievement drive"),
        research_basis="McClelland (1961)",
        key_citations=["McClelland (1961)", "McClelland et al. (1953)"],
        mechanism_influences={
            "regulatory_focus": 0.35,  # Promotion focus
            "identity_construction": 0.3,
            "temporal_construal": 0.2,
        },
        related_constructs={"selfreg_rf": 0.4, "social_oli": 0.35},
    ),
    "motivation_iem": ConstructDefinition(
        id="motivation_iem",
        name="Intrinsic-Extrinsic Balance",
        domain="motivational_profile",
        description="Balance between intrinsic (internal) and extrinsic (external) motivation",
        scale_anchors=("Extrinsic motivation", "Intrinsic motivation"),
        research_basis="Deci & Ryan (1985)",
        key_citations=["Deci & Ryan (1985)", "Ryan & Deci (2000)"],
        mechanism_influences={
            "identity_construction": 0.3,
            "wanting_liking": -0.2,  # Less driven by external rewards
            "mimetic_desire": -0.25,
        },
        related_constructs={"motivation_achievement": 0.3, "social_nfu": 0.35},
    ),
    
    # Domain 9: Emotional Processing
    "emotion_ai": ConstructDefinition(
        id="emotion_ai",
        name="Affect Intensity",
        domain="emotional_processing",
        description="Intensity of emotional responses to stimuli",
        scale_anchors=("Low affect intensity", "High affect intensity"),
        research_basis="Larsen & Diener (1987)",
        key_citations=["Larsen & Diener (1987)", "Larsen (2009)"],
        mechanism_influences={
            "automatic_evaluation": 0.35,
            "wanting_liking": 0.3,
            "attention_dynamics": 0.2,
        },
        related_constructs={"temporal_ddr": 0.3, "selfreg_lam": 0.25},
    ),
    
    # Domain 10: Purchase Psychology
    "purchase_pct": ConstructDefinition(
        id="purchase_pct",
        name="Purchase Confidence Threshold",
        domain="purchase_psychology",
        description="Confidence level required before making purchase decisions",
        scale_anchors=("Low threshold (impulsive)", "High threshold (deliberate)"),
        research_basis="Bennett & Harrell (1975)",
        key_citations=["Bennett & Harrell (1975)", "Laroche et al. (1996)"],
        mechanism_influences={
            "automatic_evaluation": -0.3,
            "construal_level": 0.25,
            "regulatory_focus": -0.2,  # Prevention = higher threshold
        },
        related_constructs={"decision_maximizer": 0.4, "cognitive_nfc": 0.35},
    ),
    
    # Domain 11: Value Orientation
    "value_hub": ConstructDefinition(
        id="value_hub",
        name="Hedonic-Utilitarian Balance",
        domain="value_orientation",
        description="Preference for hedonic (pleasure) vs utilitarian (function) value",
        scale_anchors=("Utilitarian", "Hedonic"),
        research_basis="Hirschman & Holbrook (1982)",
        key_citations=["Hirschman & Holbrook (1982)", "Babin et al. (1994)"],
        mechanism_influences={
            "wanting_liking": 0.35,
            "automatic_evaluation": 0.25,
            "identity_construction": 0.2,
        },
        related_constructs={"emotion_ai": 0.35, "temporal_ddr": 0.3},
    ),
    "value_consciousness": ConstructDefinition(
        id="value_consciousness",
        name="Value Consciousness",
        domain="value_orientation",
        description="Focus on getting best value relative to price paid",
        scale_anchors=("Price-focused", "Value-focused"),
        research_basis="Lichtenstein et al. (1993)",
        key_citations=["Lichtenstein et al. (1993)", "Zeithaml (1988)"],
        mechanism_influences={
            "construal_level": 0.2,
            "regulatory_focus": 0.15,
            "temporal_construal": 0.2,
        },
        related_constructs={"decision_maximizer": 0.3, "cognitive_nfc": 0.25},
    ),
}


# =============================================================================
# NEO4J POPULATION FUNCTIONS
# =============================================================================

class PsychologicalKnowledgeGraphPopulator:
    """Populates Neo4j with psychological research knowledge."""
    
    def __init__(self, driver):
        """Initialize with Neo4j driver."""
        self.driver = driver
    
    async def populate_all(self) -> Dict[str, int]:
        """Populate all psychological knowledge in Neo4j."""
        results = {}
        
        # Create nodes
        results["mechanisms"] = await self._create_mechanism_nodes()
        results["archetypes"] = await self._create_archetype_nodes()
        results["constructs"] = await self._create_construct_nodes()
        
        # Create relationships
        results["archetype_mechanism_rels"] = await self._create_archetype_mechanism_relationships()
        results["construct_mechanism_rels"] = await self._create_construct_mechanism_relationships()
        results["construct_correlations"] = await self._create_construct_correlations()
        
        logger.info(f"Populated psychological knowledge graph: {results}")
        return results
    
    async def _create_mechanism_nodes(self) -> int:
        """Create CognitiveMechanism nodes."""
        query = """
        UNWIND $mechanisms AS mech
        MERGE (m:CognitiveMechanism {id: mech.id})
        SET m.name = mech.name,
            m.description = mech.description,
            m.research_basis = mech.research_basis,
            m.key_insight = mech.key_insight,
            m.applicable_contexts = mech.applicable_contexts,
            m.created_at = datetime(),
            m.source = 'enhancement_13'
        RETURN count(m) as count
        """
        
        mechanisms = []
        for mech_enum, defn in MECHANISM_DEFINITIONS.items():
            mechanisms.append({
                "id": mech_enum.value,
                "name": defn["name"],
                "description": defn["description"],
                "research_basis": defn["research_basis"],
                "key_insight": defn["key_insight"],
                "applicable_contexts": defn["applicable_contexts"],
            })
        
        async with self.driver.session() as session:
            result = await session.run(query, mechanisms=mechanisms)
            record = await result.single()
            return record["count"] if record else 0
    
    async def _create_archetype_nodes(self) -> int:
        """Create CustomerArchetype nodes."""
        query = """
        UNWIND $archetypes AS arch
        MERGE (a:CustomerArchetype {id: arch.id})
        SET a.name = arch.name,
            a.description = arch.description,
            a.core_values = arch.core_values,
            a.communication_style = arch.communication_style,
            a.decision_drivers = arch.decision_drivers,
            a.created_at = datetime(),
            a.source = 'enhancement_13'
        RETURN count(a) as count
        """
        
        archetypes = []
        for arch_enum, defn in ARCHETYPE_DEFINITIONS.items():
            archetypes.append({
                "id": arch_enum.value,
                "name": defn["name"],
                "description": defn["description"],
                "core_values": defn["core_values"],
                "communication_style": defn["communication_style"],
                "decision_drivers": defn["decision_drivers"],
            })
        
        async with self.driver.session() as session:
            result = await session.run(query, archetypes=archetypes)
            record = await result.single()
            return record["count"] if record else 0
    
    async def _create_construct_nodes(self) -> int:
        """Create ExtendedPsychologicalConstruct nodes."""
        query = """
        UNWIND $constructs AS c
        MERGE (pc:ExtendedPsychologicalConstruct {id: c.id})
        SET pc.name = c.name,
            pc.domain = c.domain,
            pc.description = c.description,
            pc.scale_low = c.scale_low,
            pc.scale_high = c.scale_high,
            pc.research_basis = c.research_basis,
            pc.key_citations = c.key_citations,
            pc.created_at = datetime(),
            pc.source = 'enhancement_27'
        RETURN count(pc) as count
        """
        
        constructs = []
        for construct_id, defn in CONSTRUCT_DEFINITIONS.items():
            constructs.append({
                "id": defn.id,
                "name": defn.name,
                "domain": defn.domain,
                "description": defn.description,
                "scale_low": defn.scale_anchors[0],
                "scale_high": defn.scale_anchors[1],
                "research_basis": defn.research_basis,
                "key_citations": defn.key_citations,
            })
        
        async with self.driver.session() as session:
            result = await session.run(query, constructs=constructs)
            record = await result.single()
            return record["count"] if record else 0
    
    async def _create_archetype_mechanism_relationships(self) -> int:
        """Create MECHANISM_EFFECTIVENESS relationships with Beta priors."""
        query = """
        UNWIND $relationships AS rel
        MATCH (a:CustomerArchetype {id: rel.archetype_id})
        MATCH (m:CognitiveMechanism {id: rel.mechanism_id})
        MERGE (a)-[r:MECHANISM_EFFECTIVENESS]->(m)
        SET r.alpha = rel.alpha,
            r.beta = rel.beta,
            r.expected_effectiveness = rel.expected,
            r.sample_size = 0,
            r.successes = 0,
            r.created_at = datetime(),
            r.source = 'enhancement_13_priors'
        RETURN count(r) as count
        """
        
        relationships = []
        for archetype, mechanisms in ARCHETYPE_MECHANISM_PRIORS.items():
            for mechanism, (alpha, beta) in mechanisms.items():
                expected = alpha / (alpha + beta)
                relationships.append({
                    "archetype_id": archetype.value,
                    "mechanism_id": mechanism.value,
                    "alpha": alpha,
                    "beta": beta,
                    "expected": expected,
                })
        
        async with self.driver.session() as session:
            result = await session.run(query, relationships=relationships)
            record = await result.single()
            return record["count"] if record else 0
    
    async def _create_construct_mechanism_relationships(self) -> int:
        """Create INFLUENCES_MECHANISM relationships."""
        query = """
        UNWIND $relationships AS rel
        MATCH (c:ExtendedPsychologicalConstruct {id: rel.construct_id})
        MATCH (m:CognitiveMechanism {id: rel.mechanism_id})
        MERGE (c)-[r:INFLUENCES_MECHANISM]->(m)
        SET r.influence_strength = rel.strength,
            r.direction = CASE WHEN rel.strength >= 0 THEN 'positive' ELSE 'negative' END,
            r.created_at = datetime(),
            r.source = 'enhancement_27'
        RETURN count(r) as count
        """
        
        relationships = []
        for construct_id, defn in CONSTRUCT_DEFINITIONS.items():
            for mechanism_id, strength in defn.mechanism_influences.items():
                relationships.append({
                    "construct_id": construct_id,
                    "mechanism_id": mechanism_id,
                    "strength": strength,
                })
        
        async with self.driver.session() as session:
            result = await session.run(query, relationships=relationships)
            record = await result.single()
            return record["count"] if record else 0
    
    async def _create_construct_correlations(self) -> int:
        """Create CORRELATED_WITH relationships between constructs."""
        query = """
        UNWIND $relationships AS rel
        MATCH (c1:ExtendedPsychologicalConstruct {id: rel.construct1_id})
        MATCH (c2:ExtendedPsychologicalConstruct {id: rel.construct2_id})
        MERGE (c1)-[r:CORRELATED_WITH]->(c2)
        SET r.correlation = rel.correlation,
            r.created_at = datetime(),
            r.source = 'enhancement_27'
        RETURN count(r) as count
        """
        
        relationships = []
        seen = set()
        for construct_id, defn in CONSTRUCT_DEFINITIONS.items():
            for related_id, correlation in defn.related_constructs.items():
                # Avoid duplicates (a->b and b->a)
                pair = tuple(sorted([construct_id, related_id]))
                if pair not in seen and related_id in CONSTRUCT_DEFINITIONS:
                    seen.add(pair)
                    relationships.append({
                        "construct1_id": construct_id,
                        "construct2_id": related_id,
                        "correlation": correlation,
                    })
        
        async with self.driver.session() as session:
            result = await session.run(query, relationships=relationships)
            record = await result.single()
            return record["count"] if record else 0


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def populate_psychological_knowledge_graph(neo4j_driver) -> Dict[str, int]:
    """
    Populate the psychological knowledge graph in Neo4j.
    
    Args:
        neo4j_driver: Async Neo4j driver instance
        
    Returns:
        Dictionary with counts of created entities
    """
    populator = PsychologicalKnowledgeGraphPopulator(neo4j_driver)
    return await populator.populate_all()


def get_mechanism_effectiveness_prior(
    archetype: str, 
    mechanism: str
) -> Optional[Tuple[float, float]]:
    """
    Get the Beta prior for a mechanism's effectiveness with an archetype.
    
    Args:
        archetype: Archetype ID (e.g., 'achievement_driven')
        mechanism: Mechanism ID (e.g., 'regulatory_focus')
        
    Returns:
        Tuple of (alpha, beta) or None if not found
    """
    try:
        arch_enum = CustomerArchetype(archetype)
        mech_enum = CognitiveMechanism(mechanism)
        return ARCHETYPE_MECHANISM_PRIORS.get(arch_enum, {}).get(mech_enum)
    except ValueError:
        return None


def get_construct_mechanism_influence(
    construct: str,
    mechanism: str
) -> Optional[float]:
    """
    Get a construct's influence on a mechanism.
    
    Args:
        construct: Construct ID (e.g., 'cognitive_nfc')
        mechanism: Mechanism ID (e.g., 'construal_level')
        
    Returns:
        Influence strength or None if not found
    """
    if construct in CONSTRUCT_DEFINITIONS:
        return CONSTRUCT_DEFINITIONS[construct].mechanism_influences.get(mechanism)
    return None


# =============================================================================
# CLI SCRIPT
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("PSYCHOLOGICAL KNOWLEDGE GRAPH POPULATION")
    print("=" * 60)
    print(f"\nThis script will create:")
    print(f"  - {len(MECHANISM_DEFINITIONS)} Cognitive Mechanism nodes")
    print(f"  - {len(ARCHETYPE_DEFINITIONS)} Customer Archetype nodes")
    print(f"  - {len(CONSTRUCT_DEFINITIONS)} Psychological Construct nodes")
    
    total_arch_mech = sum(len(m) for m in ARCHETYPE_MECHANISM_PRIORS.values())
    print(f"  - {total_arch_mech} Archetype → Mechanism relationships")
    
    total_const_mech = sum(len(d.mechanism_influences) for d in CONSTRUCT_DEFINITIONS.values())
    print(f"  - {total_const_mech} Construct → Mechanism relationships")
    
    total_correlations = sum(len(d.related_constructs) for d in CONSTRUCT_DEFINITIONS.values()) // 2
    print(f"  - ~{total_correlations} Construct correlation relationships")
    
    print("\nTo run, use:")
    print("  python -m adam.intelligence.knowledge_graph.populate_psychological_graph")
    print("\nOr call populate_psychological_knowledge_graph(driver) from code.")
