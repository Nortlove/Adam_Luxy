# =============================================================================
# ADAM Behavioral Analytics Knowledge Module
# =============================================================================

"""
BEHAVIORAL ANALYTICS KNOWLEDGE

Research-validated knowledge for behavioral signal interpretation
and advertising effectiveness prediction.

Includes:
- Behavioral signal → psychological construct mappings (150+ studies)
- Consumer psychology → advertising response knowledge (25 years, 1999-2025)
- Hypothesis generation and testing infrastructure
- Knowledge promotion pipeline
"""

from adam.behavioral_analytics.knowledge.research_seeder import (
    ResearchKnowledgeSeeder,
    get_research_knowledge_seeder,
    create_tier1_knowledge,
    create_tier2_knowledge,
    create_personality_knowledge,
    create_desktop_signal_knowledge,
    create_mechanism_signal_knowledge,
)

from adam.behavioral_analytics.knowledge.consumer_psychology_seeder import (
    ConsumerPsychologySeeder,
    get_consumer_psychology_seeder,
    create_personality_trait_knowledge,
    create_psychological_state_knowledge,
    create_message_appeal_knowledge,
    create_visual_design_knowledge,
    create_media_platform_knowledge,
    create_moderator_interactions,
    create_baseline_effectiveness_knowledge,
)

from adam.behavioral_analytics.knowledge.graph_integration import (
    BehavioralKnowledgeGraph,
)

from adam.behavioral_analytics.knowledge.hypothesis_engine import (
    HypothesisEngine,
)

from adam.behavioral_analytics.knowledge.promoter import (
    KnowledgePromoter,
)

__all__ = [
    # Behavioral research seeder
    "ResearchKnowledgeSeeder",
    "get_research_knowledge_seeder",
    "create_tier1_knowledge",
    "create_tier2_knowledge",
    "create_personality_knowledge",
    "create_desktop_signal_knowledge",
    "create_mechanism_signal_knowledge",
    
    # Consumer psychology seeder
    "ConsumerPsychologySeeder",
    "get_consumer_psychology_seeder",
    "create_personality_trait_knowledge",
    "create_psychological_state_knowledge",
    "create_message_appeal_knowledge",
    "create_visual_design_knowledge",
    "create_media_platform_knowledge",
    "create_moderator_interactions",
    "create_baseline_effectiveness_knowledge",
    
    # Graph integration
    "BehavioralKnowledgeGraph",
    
    # Hypothesis engine
    "HypothesisEngine",
    
    # Knowledge promoter
    "KnowledgePromoter",
]
