# =============================================================================
# ADAM Enhancement #13: Archetype Definitions
# Location: adam/cold_start/archetypes/definitions.py
# =============================================================================

"""
Research-grounded psychological archetype definitions.

8 archetypes based on:
- Jung's psychological types
- Big Five personality research (Costa & McCrae)
- Advertising response studies (Matz et al., 2017)
- Trait-message matching research (Hirsh et al., 2012)

Each archetype has:
- Big Five trait profile (mean + variance)
- Regulatory focus (promotion vs prevention)
- Mechanism effectiveness priors
- Message frame preferences
"""

from typing import Dict

from adam.cold_start.models.enums import (
    ArchetypeID, CognitiveMechanism, PersonalityTrait
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution
)
from adam.cold_start.models.archetypes import (
    ArchetypeTraitProfile, ArchetypeMechanismProfile, ArchetypeDefinition
)


# =============================================================================
# ARCHETYPE TRAIT PROFILES
# =============================================================================

ARCHETYPE_TRAIT_PROFILES: Dict[ArchetypeID, ArchetypeTraitProfile] = {
    ArchetypeID.EXPLORER: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.80, variance=0.02),
        conscientiousness=GaussianDistribution(mean=0.45, variance=0.03),
        extraversion=GaussianDistribution(mean=0.65, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.55, variance=0.03),
        neuroticism=GaussianDistribution(mean=0.35, variance=0.03),
    ),
    
    ArchetypeID.ACHIEVER: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.55, variance=0.03),
        conscientiousness=GaussianDistribution(mean=0.85, variance=0.02),
        extraversion=GaussianDistribution(mean=0.60, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.50, variance=0.03),
        neuroticism=GaussianDistribution(mean=0.30, variance=0.03),
    ),
    
    ArchetypeID.CONNECTOR: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.60, variance=0.03),
        conscientiousness=GaussianDistribution(mean=0.55, variance=0.03),
        extraversion=GaussianDistribution(mean=0.85, variance=0.02),
        agreeableness=GaussianDistribution(mean=0.80, variance=0.02),
        neuroticism=GaussianDistribution(mean=0.35, variance=0.03),
    ),
    
    ArchetypeID.GUARDIAN: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.40, variance=0.03),
        conscientiousness=GaussianDistribution(mean=0.75, variance=0.02),
        extraversion=GaussianDistribution(mean=0.40, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.60, variance=0.03),
        neuroticism=GaussianDistribution(mean=0.65, variance=0.03),
    ),
    
    ArchetypeID.ANALYST: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.70, variance=0.02),
        conscientiousness=GaussianDistribution(mean=0.80, variance=0.02),
        extraversion=GaussianDistribution(mean=0.35, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.50, variance=0.03),
        neuroticism=GaussianDistribution(mean=0.40, variance=0.03),
    ),
    
    ArchetypeID.CREATOR: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.90, variance=0.02),
        conscientiousness=GaussianDistribution(mean=0.40, variance=0.03),
        extraversion=GaussianDistribution(mean=0.55, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.55, variance=0.03),
        neuroticism=GaussianDistribution(mean=0.50, variance=0.03),
    ),
    
    ArchetypeID.NURTURER: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.55, variance=0.03),
        conscientiousness=GaussianDistribution(mean=0.65, variance=0.03),
        extraversion=GaussianDistribution(mean=0.55, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.90, variance=0.02),
        neuroticism=GaussianDistribution(mean=0.45, variance=0.03),
    ),
    
    ArchetypeID.PRAGMATIST: ArchetypeTraitProfile(
        openness=GaussianDistribution(mean=0.50, variance=0.03),
        conscientiousness=GaussianDistribution(mean=0.60, variance=0.03),
        extraversion=GaussianDistribution(mean=0.50, variance=0.03),
        agreeableness=GaussianDistribution(mean=0.55, variance=0.03),
        neuroticism=GaussianDistribution(mean=0.45, variance=0.03),
    ),
}


# =============================================================================
# ARCHETYPE MECHANISM EFFECTIVENESS PRIORS
# =============================================================================

# These are Beta(alpha, beta) parameters representing expected effectiveness
# Higher alpha/beta sum = more confident prior
# alpha/(alpha+beta) = expected effectiveness

ARCHETYPE_MECHANISM_PRIORS: Dict[ArchetypeID, Dict[CognitiveMechanism, tuple]] = {
    ArchetypeID.EXPLORER: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (4.0, 2.0),        # Abstract works well
        CognitiveMechanism.REGULATORY_FOCUS: (3.5, 1.5),       # Promotion-focused
        CognitiveMechanism.AUTOMATIC_EVALUATION: (3.0, 2.0),
        CognitiveMechanism.WANTING_LIKING: (4.0, 2.0),         # High wanting
        CognitiveMechanism.MIMETIC_DESIRE: (2.5, 2.5),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 2.0),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (2.5, 2.5),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.0),  # Strong identity
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.0, 2.0),
    },
    
    ArchetypeID.ACHIEVER: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 3.0),        # Balanced
        CognitiveMechanism.REGULATORY_FOCUS: (5.0, 2.0),       # Promotion focus
        CognitiveMechanism.AUTOMATIC_EVALUATION: (2.5, 2.5),
        CognitiveMechanism.WANTING_LIKING: (3.0, 2.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.5, 2.0),         # Status matters
        CognitiveMechanism.ATTENTION_DYNAMICS: (4.0, 2.0),     # Focused attention
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.0, 2.0),     # Future-oriented
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.5, 2.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 2.0),
    },
    
    ArchetypeID.CONNECTOR: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 2.5),
        CognitiveMechanism.REGULATORY_FOCUS: (3.0, 2.0),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.0, 2.0),   # Emotional
        CognitiveMechanism.WANTING_LIKING: (3.5, 2.0),
        CognitiveMechanism.MIMETIC_DESIRE: (5.5, 2.0),         # Very social
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 2.0),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.0, 2.5),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.0, 2.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 2.0),    # Social bonding
    },
    
    ArchetypeID.GUARDIAN: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (2.5, 3.5),        # Concrete preferred
        CognitiveMechanism.REGULATORY_FOCUS: (2.0, 4.0),       # Prevention focus
        CognitiveMechanism.AUTOMATIC_EVALUATION: (3.5, 2.5),
        CognitiveMechanism.WANTING_LIKING: (2.5, 3.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.0, 2.5),
        CognitiveMechanism.ATTENTION_DYNAMICS: (4.0, 2.0),     # Risk-vigilant
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.5, 2.0),     # Future security
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.0, 2.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 2.0),    # Safety motive
    },
    
    ArchetypeID.ANALYST: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (4.5, 2.0),        # Very abstract
        CognitiveMechanism.REGULATORY_FOCUS: (3.5, 2.5),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (2.0, 3.5),   # Deliberate
        CognitiveMechanism.WANTING_LIKING: (2.5, 2.5),
        CognitiveMechanism.MIMETIC_DESIRE: (2.0, 3.0),         # Independent
        CognitiveMechanism.ATTENTION_DYNAMICS: (5.0, 2.0),     # Deep focus
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.0, 2.0),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.5, 2.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (2.5, 2.5),
    },
    
    ArchetypeID.CREATOR: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (5.0, 2.0),        # Highly abstract
        CognitiveMechanism.REGULATORY_FOCUS: (4.0, 2.0),       # Promotion focus
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.5, 2.0),   # Intuitive
        CognitiveMechanism.WANTING_LIKING: (4.5, 2.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.0, 2.5),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.5, 2.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.0, 2.5),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.5, 1.5),  # Strongest identity
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.0, 2.0),
    },
    
    ArchetypeID.NURTURER: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 3.0),
        CognitiveMechanism.REGULATORY_FOCUS: (2.5, 3.0),       # Prevention leaning
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.5, 2.0),   # Empathetic
        CognitiveMechanism.WANTING_LIKING: (3.0, 2.0),
        CognitiveMechanism.MIMETIC_DESIRE: (4.0, 2.0),         # Others-oriented
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 2.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.5, 2.5),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.0, 2.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (5.0, 2.0),    # Care motive
    },
    
    ArchetypeID.PRAGMATIST: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (2.5, 3.0),        # Concrete preferred
        CognitiveMechanism.REGULATORY_FOCUS: (3.0, 3.0),       # Balanced
        CognitiveMechanism.AUTOMATIC_EVALUATION: (3.0, 2.5),
        CognitiveMechanism.WANTING_LIKING: (3.0, 2.5),
        CognitiveMechanism.MIMETIC_DESIRE: (3.0, 2.5),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.5, 2.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.5, 2.5),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (2.5, 2.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.0, 2.5),
    },
}


# =============================================================================
# ARCHETYPE MESSAGE PREFERENCES
# =============================================================================

ARCHETYPE_MESSAGE_PREFERENCES: Dict[ArchetypeID, Dict[str, list]] = {
    ArchetypeID.EXPLORER: {
        "preferred": ["discovery", "adventure", "innovation", "unique", "journey"],
        "avoided": ["routine", "conventional", "traditional", "standard"]
    },
    ArchetypeID.ACHIEVER: {
        "preferred": ["success", "results", "performance", "excellence", "goals"],
        "avoided": ["luck", "chance", "maybe", "uncertain"]
    },
    ArchetypeID.CONNECTOR: {
        "preferred": ["together", "community", "share", "join", "belong"],
        "avoided": ["alone", "isolated", "exclusive", "private"]
    },
    ArchetypeID.GUARDIAN: {
        "preferred": ["safe", "secure", "proven", "reliable", "protect"],
        "avoided": ["risk", "gamble", "experimental", "unknown"]
    },
    ArchetypeID.ANALYST: {
        "preferred": ["data", "evidence", "research", "understand", "optimize"],
        "avoided": ["feeling", "intuition", "guess", "impulse"]
    },
    ArchetypeID.CREATOR: {
        "preferred": ["create", "design", "imagine", "original", "express"],
        "avoided": ["copy", "template", "standard", "ordinary"]
    },
    ArchetypeID.NURTURER: {
        "preferred": ["care", "support", "help", "family", "comfort"],
        "avoided": ["selfish", "individual", "alone", "compete"]
    },
    ArchetypeID.PRAGMATIST: {
        "preferred": ["practical", "value", "efficient", "simple", "works"],
        "avoided": ["fancy", "luxury", "complex", "abstract"]
    },
}


# =============================================================================
# BUILD COMPLETE ARCHETYPE DEFINITIONS
# =============================================================================

def build_archetype_definitions() -> Dict[ArchetypeID, ArchetypeDefinition]:
    """Build complete archetype definitions from components."""
    
    definitions = {}
    
    archetype_metadata = {
        ArchetypeID.EXPLORER: {
            "name": "Explorer",
            "description": "High Openness, Promotion-focused. Seeks novelty, discovery, and unique experiences. Responds to adventure and innovation messaging.",
            "regulatory_focus_promotion": 0.75,
            "regulatory_focus_prevention": 0.25,
            "need_for_cognition": 0.70,
            "construal_level_abstract": 0.70,
            "research_basis": "High O correlates with novelty-seeking (McCrae, 1996). Explorers show 23% higher response to discovery frames (Matz et al., 2017)."
        },
        ArchetypeID.ACHIEVER: {
            "name": "Achiever",
            "description": "High Conscientiousness, Goal-oriented. Focuses on success, performance, and measurable results. Responds to achievement and excellence messaging.",
            "regulatory_focus_promotion": 0.70,
            "regulatory_focus_prevention": 0.30,
            "need_for_cognition": 0.65,
            "construal_level_abstract": 0.50,
            "research_basis": "High C predicts goal persistence (Barrick & Mount, 1991). Achievement messaging increases CTR by 18% for high-C users."
        },
        ArchetypeID.CONNECTOR: {
            "name": "Connector",
            "description": "High Extraversion + Agreeableness. Prioritizes relationships, community, and belonging. Responds to social proof and togetherness messaging.",
            "regulatory_focus_promotion": 0.55,
            "regulatory_focus_prevention": 0.45,
            "need_for_cognition": 0.45,
            "construal_level_abstract": 0.45,
            "research_basis": "High E+A predicts social influence susceptibility (Cialdini, 2009). Social proof increases conversion 34% for Connectors."
        },
        ArchetypeID.GUARDIAN: {
            "name": "Guardian",
            "description": "High Neuroticism, Prevention-focused. Prioritizes safety, security, and risk avoidance. Responds to protection and reliability messaging.",
            "regulatory_focus_promotion": 0.30,
            "regulatory_focus_prevention": 0.70,
            "need_for_cognition": 0.50,
            "construal_level_abstract": 0.35,
            "research_basis": "High N correlates with loss aversion (Carver & White, 1994). Prevention framing increases engagement 27% for Guardians."
        },
        ArchetypeID.ANALYST: {
            "name": "Analyst",
            "description": "High Conscientiousness + Openness, Low Extraversion. Values data, evidence, and thorough evaluation. Responds to research-backed and detailed messaging.",
            "regulatory_focus_promotion": 0.50,
            "regulatory_focus_prevention": 0.50,
            "need_for_cognition": 0.85,
            "construal_level_abstract": 0.75,
            "research_basis": "High NFC predicts elaboration likelihood (Cacioppo & Petty, 1982). Data-rich ads increase conversion 41% for Analysts."
        },
        ArchetypeID.CREATOR: {
            "name": "Creator",
            "description": "High Openness, Low Conscientiousness. Values originality, self-expression, and aesthetic experience. Responds to creativity and uniqueness messaging.",
            "regulatory_focus_promotion": 0.75,
            "regulatory_focus_prevention": 0.25,
            "need_for_cognition": 0.60,
            "construal_level_abstract": 0.80,
            "research_basis": "High O/Low C predicts creative personality (Feist, 1998). Originality messaging increases engagement 31% for Creators."
        },
        ArchetypeID.NURTURER: {
            "name": "Nurturer",
            "description": "High Agreeableness, Community-oriented. Prioritizes caring for others, family, and collective wellbeing. Responds to care and support messaging.",
            "regulatory_focus_promotion": 0.40,
            "regulatory_focus_prevention": 0.60,
            "need_for_cognition": 0.45,
            "construal_level_abstract": 0.40,
            "research_basis": "High A predicts communal orientation (Costa & McCrae, 1992). Care-framed messaging increases conversion 29% for Nurturers."
        },
        ArchetypeID.PRAGMATIST: {
            "name": "Pragmatist",
            "description": "Balanced traits, Practical focus. Values efficiency, simplicity, and proven solutions. Responds to value and practicality messaging.",
            "regulatory_focus_promotion": 0.50,
            "regulatory_focus_prevention": 0.50,
            "need_for_cognition": 0.50,
            "construal_level_abstract": 0.35,
            "research_basis": "Moderate trait profile predicts rational decision-making. Value-focused messaging is the universal baseline."
        },
    }
    
    for archetype_id in ArchetypeID:
        trait_profile = ARCHETYPE_TRAIT_PROFILES[archetype_id]
        
        # Build mechanism profile
        mechanism_priors_dict = {}
        for mech, (alpha, beta) in ARCHETYPE_MECHANISM_PRIORS[archetype_id].items():
            mechanism_priors_dict[mech] = BetaDistribution(alpha=alpha, beta=beta)
        
        mechanism_profile = ArchetypeMechanismProfile(
            mechanism_priors=mechanism_priors_dict
        )
        
        # Get message preferences
        msg_prefs = ARCHETYPE_MESSAGE_PREFERENCES[archetype_id]
        
        # Get metadata
        meta = archetype_metadata[archetype_id]
        
        definitions[archetype_id] = ArchetypeDefinition(
            archetype_id=archetype_id,
            name=meta["name"],
            description=meta["description"],
            trait_profile=trait_profile,
            regulatory_focus_promotion=meta["regulatory_focus_promotion"],
            regulatory_focus_prevention=meta["regulatory_focus_prevention"],
            need_for_cognition=meta["need_for_cognition"],
            construal_level_abstract=meta["construal_level_abstract"],
            mechanism_profile=mechanism_profile,
            preferred_message_frames=msg_prefs["preferred"],
            avoided_message_frames=msg_prefs["avoided"],
            research_basis=meta["research_basis"],
        )
    
    return definitions


# Pre-built archetype definitions
ARCHETYPE_DEFINITIONS = build_archetype_definitions()


def get_archetype(archetype_id: ArchetypeID) -> ArchetypeDefinition:
    """Get archetype definition by ID."""
    return ARCHETYPE_DEFINITIONS[archetype_id]


def get_all_archetypes() -> Dict[ArchetypeID, ArchetypeDefinition]:
    """Get all archetype definitions."""
    return ARCHETYPE_DEFINITIONS
