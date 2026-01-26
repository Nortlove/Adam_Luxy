# =============================================================================
# ADAM Psychological Constructs (#27)
# Location: adam/platform/constructs/__init__.py
# =============================================================================

"""
EXTENDED PSYCHOLOGICAL CONSTRUCTS

Enhancement #27 v2: Comprehensive Psychological Intelligence Taxonomy

Implements the 12-domain framework with 35 constructs for precision persuasion:

Domains:
1. Cognitive Processing (NFC, Processing Speed, Heuristic Reliance)
2. Self-Regulatory (Self-Monitoring, Reg Focus, Locomotion-Assessment)
3. Temporal Psychology (Orientation, Future Self-Continuity, Delay Discounting)
4. Decision Making (Maximizer-Satisficer, Regret Anticipation, Choice Overload)
5. Social-Cognitive (Susceptibility to Social Proof, Conformity, Opinion Leadership)
6. Uncertainty Processing (Ambiguity Tolerance, Need for Closure)
7. Information Processing (Visualizer-Verbalizer, Holistic-Analytic)
8. Motivational Profile (Achievement, Power, Affiliation, Intrinsic-Extrinsic)
9. Emotional Processing (Affect Intensity, Emotional Granularity)
10. Purchase Psychology (Confidence Threshold, Return Anxiety)
11. Value Orientation (Individualism-Collectivism, Materialism)
12. Emergent Constructs (Discovered through #04 Atom of Thought)

Usage:
    from adam.platform.constructs import PsychologicalConstructsService
    
    service = PsychologicalConstructsService(neo4j_driver, gradient_bridge)
    profile = await service.get_user_constructs(user_id)
    
    # Access specific constructs
    nfc = profile.cognitive_processing.need_for_cognition
    reg_focus = profile.self_regulatory.regulatory_focus
"""

from adam.platform.constructs.models import (
    # Core profile
    ExtendedPsychologicalProfile,
    ConstructScore,
    ConstructConfidence,
    
    # Domain models
    CognitiveProcessingDomain,
    SelfRegulatoryDomain,
    TemporalPsychologyDomain,
    DecisionMakingDomain,
    SocialCognitiveDomain,
    UncertaintyProcessingDomain,
    InformationProcessingDomain,
    MotivationalProfileDomain,
    EmotionalProcessingDomain,
    PurchasePsychologyDomain,
    ValueOrientationDomain,
    EmergentConstructsDomain,
)
from adam.platform.constructs.service import PsychologicalConstructsService

__all__ = [
    # Service
    "PsychologicalConstructsService",
    
    # Core
    "ExtendedPsychologicalProfile",
    "ConstructScore",
    "ConstructConfidence",
    
    # Domains
    "CognitiveProcessingDomain",
    "SelfRegulatoryDomain",
    "TemporalPsychologyDomain",
    "DecisionMakingDomain",
    "SocialCognitiveDomain",
    "UncertaintyProcessingDomain",
    "InformationProcessingDomain",
    "MotivationalProfileDomain",
    "EmotionalProcessingDomain",
    "PurchasePsychologyDomain",
    "ValueOrientationDomain",
    "EmergentConstructsDomain",
]
