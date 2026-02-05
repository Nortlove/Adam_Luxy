# ADAM Intelligence Components
"""
Intelligence components for ADAM platform.

Core Components:
- EmergenceEngine: Discovers novel psychological constructs
- GraphEdgeService: Leverages graph relationships for intelligence
- CohortDiscovery: Behavioral cohort identification
- CausalDiscovery: Causal relationship inference
- PredictiveProcessing: Predictive intelligence

Phase 6+ Enhancements (Full Intelligence Utilization):
- UnifiedConstructIntegration: All 35 constructs → mechanism selection
- PersuasivePatternExtractor: High-helpful-vote review patterns
- BrandPersuasionAnalyzer: Cialdini principle detection
- HelpfulVoteWeightedLearning: Proper vote weighting (no 30% cap)
- CustomerInfluenceGraph: Review-to-review influence
- FullIntelligenceIntegrator: Unified interface for 100% utilization
"""

# Core Components
from adam.intelligence.emergence_engine import EmergenceEngine
from adam.intelligence.graph_edge_service import GraphEdgeService, get_graph_edge_service
from adam.intelligence.cohort_discovery import CohortDiscoveryService, get_cohort_discovery_service

# Phase 6+ Enhancements
from adam.intelligence.unified_construct_integration import (
    UnifiedConstructIntegration,
    get_unified_construct_integration,
    ConstructProfile,
    MechanismAdjustment,
    CONSTRUCT_MECHANISM_INFLUENCES,
)

from adam.intelligence.persuasive_patterns import (
    PersuasivePatternExtractor,
    get_persuasive_pattern_extractor,
    PersuasiveProfile,
    PersuasiveTemplate,
    PersuasiveElement,
)

from adam.intelligence.brand_persuasion_analyzer import (
    BrandPersuasionAnalyzer,
    get_brand_persuasion_analyzer,
    BrandPersuasionProfile,
    CialdiniPrinciple,
    PersuasionTechnique,
)

from adam.intelligence.helpful_vote_weighting import (
    HelpfulVoteWeighter,
    HelpfulVoteWeightedLearning,
    get_helpful_vote_weighter,
    get_helpful_vote_weighted_learning,
    WeightedSignal,
    WeightingStrategy,
)

from adam.intelligence.customer_influence_graph import (
    CustomerInfluenceGraph,
    get_customer_influence_graph,
    InfluenceNode,
    InfluenceCluster,
)

from adam.intelligence.full_intelligence_integration import (
    FullIntelligenceIntegrator,
    get_full_intelligence_integrator,
    FullIntelligenceProfile,
    IntelligenceDecision,
    get_full_intelligence_decision,
)

__all__ = [
    # Core
    "EmergenceEngine",
    "GraphEdgeService",
    "get_graph_edge_service",
    "CohortDiscoveryService",
    "get_cohort_discovery_service",
    
    # Unified Construct Integration
    "UnifiedConstructIntegration",
    "get_unified_construct_integration",
    "ConstructProfile",
    "MechanismAdjustment",
    "CONSTRUCT_MECHANISM_INFLUENCES",
    
    # Persuasive Patterns
    "PersuasivePatternExtractor",
    "get_persuasive_pattern_extractor",
    "PersuasiveProfile",
    "PersuasiveTemplate",
    "PersuasiveElement",
    
    # Brand Persuasion
    "BrandPersuasionAnalyzer",
    "get_brand_persuasion_analyzer",
    "BrandPersuasionProfile",
    "CialdiniPrinciple",
    "PersuasionTechnique",
    
    # Helpful Vote Weighting
    "HelpfulVoteWeighter",
    "HelpfulVoteWeightedLearning",
    "get_helpful_vote_weighter",
    "get_helpful_vote_weighted_learning",
    "WeightedSignal",
    "WeightingStrategy",
    
    # Customer Influence
    "CustomerInfluenceGraph",
    "get_customer_influence_graph",
    "InfluenceNode",
    "InfluenceCluster",
    
    # Full Integration
    "FullIntelligenceIntegrator",
    "get_full_intelligence_integrator",
    "FullIntelligenceProfile",
    "IntelligenceDecision",
    "get_full_intelligence_decision",
]
