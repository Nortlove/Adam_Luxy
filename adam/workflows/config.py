"""
ADAM Workflow Configuration
===========================

Enterprise-grade configuration for all workflow parameters.

All hardcoded values from workflow nodes are centralized here for:
- Easy tuning and A/B testing
- Environment-specific overrides
- Audit compliance
- Documentation

Usage:
    from adam.workflows.config import get_workflow_config
    config = get_workflow_config()
    boost = config.helpful_vote_boost
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from functools import lru_cache


@dataclass
class MechanismConfig:
    """Configuration for mechanism selection and scoring."""
    
    # Boost factors for mechanism scoring
    helpful_vote_boost: float = 0.3
    competitive_advantage_boost: float = 1.2
    template_validation_boost: float = 1.15
    
    # Selection limits
    counter_strategies_limit: int = 2
    helpful_vote_rankings_limit: int = 3
    mechanism_focus_limit: int = 3
    template_selection_limit: int = 10
    
    # Default mechanism scores by archetype
    default_archetype_mechanisms: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "everyman": {"social_proof": 0.8, "belonging": 0.7, "relatability": 0.6},
        "achiever": {"scarcity": 0.8, "authority": 0.7, "exclusivity": 0.6},
        "explorer": {"curiosity": 0.8, "novelty": 0.7, "freedom": 0.6},
        "connector": {"social_proof": 0.8, "community": 0.7, "reciprocity": 0.6},
        "guardian": {"trust": 0.8, "safety": 0.7, "consistency": 0.6},
        "pragmatist": {"value": 0.8, "efficiency": 0.7, "proof": 0.6},
        "analyst": {"data": 0.8, "logic": 0.7, "comparison": 0.6},
    })


@dataclass
class ArchetypeConfig:
    """Configuration for archetype detection."""
    
    # Confidence thresholds
    high_confidence_threshold: float = 0.7
    deep_detection_min_confidence: float = 0.4
    
    # Text analysis
    min_text_length_for_deep: int = 50
    
    # Category defaults
    category_archetype_defaults: Dict[str, str] = field(default_factory=lambda: {
        "Electronics": "analyst",
        "Books": "explorer",
        "Fashion": "achiever",
        "Food": "connector",
        "Home": "guardian",
        "Sports": "achiever",
        "Toys": "connector",
    })


@dataclass
class IntelligenceConfig:
    """Configuration for intelligence gathering."""
    
    # Query limits
    neo4j_template_query_limit: int = 5
    max_reviews_analyzed: int = 100
    
    # Score thresholds
    high_susceptibility_threshold: float = 0.6
    low_susceptibility_threshold: float = 0.4
    new_mechanism_starting_score: float = 0.5
    
    # Helpful vote thresholds
    helpful_vote_very_high_threshold: int = 100
    helpful_vote_high_threshold: int = 50
    
    # Top N limits
    top_constructs_limit: int = 10
    ad_recommendations_limit: int = 5


@dataclass
class LearningConfig:
    """Configuration for learning and feedback loops."""
    
    # Graph maintenance
    maintenance_trigger_probability: float = 0.01  # 1% of decisions
    
    # Confidence calculation weights
    archetype_confidence_weight: float = 0.3
    mechanism_confidence_weight: float = 0.3
    intelligence_coverage_weight: float = 0.4
    
    # Thompson sampling
    exploration_threshold: float = 0.3
    exploitation_reward_threshold: float = 0.8


@dataclass
class ScoringConfig:
    """Configuration for decision scoring."""
    
    # Data richness weights
    data_richness_weights: Dict[str, float] = field(default_factory=lambda: {
        "graph_context": 0.3,
        "evidence_package": 0.3,
        "session_context": 0.4,
    })
    
    # Novelty
    category_novelty_threshold: float = 0.2
    
    # Default values
    default_cognitive_load: float = 0.5
    
    # Brand personality defaults (Aaker dimensions)
    default_aaker_dimensions: Dict[str, float] = field(default_factory=lambda: {
        "sincerity": 0.5,
        "excitement": 0.5,
        "competence": 0.5,
        "sophistication": 0.5,
        "ruggedness": 0.5,
    })


@dataclass
class WorkflowConfig:
    """Master configuration for all workflow settings."""
    
    mechanism: MechanismConfig = field(default_factory=MechanismConfig)
    archetype: ArchetypeConfig = field(default_factory=ArchetypeConfig)
    intelligence: IntelligenceConfig = field(default_factory=IntelligenceConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    
    # Feature flags
    enable_deep_archetype_detection: bool = True
    enable_competitive_intelligence: bool = True
    enable_helpful_vote_boost: bool = True
    enable_graph_maintenance: bool = True
    enable_bidirectional_feedback: bool = True
    
    # Performance
    prefetch_timeout_ms: int = 5000
    max_parallel_prefetches: int = 4
    
    @classmethod
    def from_env(cls) -> "WorkflowConfig":
        """Create config from environment variables."""
        config = cls()
        
        # Override from environment
        if os.getenv("ADAM_HELPFUL_VOTE_BOOST"):
            config.mechanism.helpful_vote_boost = float(os.getenv("ADAM_HELPFUL_VOTE_BOOST"))
        
        if os.getenv("ADAM_COMPETITIVE_BOOST"):
            config.mechanism.competitive_advantage_boost = float(os.getenv("ADAM_COMPETITIVE_BOOST"))
        
        if os.getenv("ADAM_HIGH_CONFIDENCE_THRESHOLD"):
            config.archetype.high_confidence_threshold = float(os.getenv("ADAM_HIGH_CONFIDENCE_THRESHOLD"))
        
        if os.getenv("ADAM_MAINTENANCE_PROBABILITY"):
            config.learning.maintenance_trigger_probability = float(os.getenv("ADAM_MAINTENANCE_PROBABILITY"))
        
        if os.getenv("ADAM_DISABLE_DEEP_ARCHETYPE"):
            config.enable_deep_archetype_detection = False
        
        if os.getenv("ADAM_DISABLE_COMPETITIVE_INTEL"):
            config.enable_competitive_intelligence = False
        
        if os.getenv("ADAM_PREFETCH_TIMEOUT_MS"):
            config.prefetch_timeout_ms = int(os.getenv("ADAM_PREFETCH_TIMEOUT_MS"))
        
        return config


# Singleton getter
_config: Optional[WorkflowConfig] = None


@lru_cache(maxsize=1)
def get_workflow_config() -> WorkflowConfig:
    """Get singleton workflow configuration."""
    global _config
    if _config is None:
        _config = WorkflowConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset config for testing."""
    global _config
    _config = None
    get_workflow_config.cache_clear()
