"""
Consumer-Brand Relationship Intelligence Module
================================================

This module provides the complete 5-Channel Consumer-Brand Relationship
Detection System for ADAM.

Core Components:
- models: Data models for relationships, signals, and channels
- patterns: Validated language patterns from academic research
- detector: RelationshipDetector service for analyzing text
- graph_builder: Neo4j integration for relationship storage
- atom: RelationshipIntelligenceAtom for AtomDAG integration

Usage:
    from adam.intelligence.relationship import (
        RelationshipDetector,
        get_relationship_detector,
        RelationshipGraphBuilder,
        RelationshipTypeId,
        ObservationChannel,
        ConsumerBrandRelationship,
    )
    
    # Detect relationships from reviews
    detector = get_relationship_detector()
    relationship = detector.analyze_review(
        review_text="I've been a loyal customer for 15 years, would never switch!",
        brand_id="brand_123"
    )
    
    print(f"Primary relationship: {relationship.primary_relationship_type}")
    print(f"Recommended tone: {relationship.get_engagement_tone()}")
"""

from .models import (
    # Enums
    ObservationChannel,
    ChannelRole,
    RelationshipCategory,
    RelationalModel,
    RelationshipTypeId,
    RelationshipStrength,
    LinguisticMarkerType,
    
    # Models
    LanguagePattern,
    RelationshipTypeDefinition,
    RelationshipSignal,
    ConsumerBrandRelationship,
    
    # Mappings
    RELATIONSHIP_MECHANISM_MAP,
    RELATIONSHIP_ARCHETYPE_MAP,
)

from .patterns import (
    ALL_PATTERNS,
    PATTERN_BY_ID,
    PATTERNS_BY_RELATIONSHIP,
)

from .detector import (
    RelationshipDetector,
    get_relationship_detector,
)

from .graph_builder import (
    RelationshipGraphBuilder,
    initialize_relationship_schema as initialize_graph_schema,
)

from .schema import (
    initialize_relationship_schema,
    get_schema_queries,
)

__all__ = [
    # Enums
    'ObservationChannel',
    'ChannelRole',
    'RelationshipCategory',
    'RelationalModel',
    'RelationshipTypeId',
    'RelationshipStrength',
    'LinguisticMarkerType',
    
    # Models
    'LanguagePattern',
    'RelationshipTypeDefinition',
    'RelationshipSignal',
    'ConsumerBrandRelationship',
    
    # Mappings
    'RELATIONSHIP_MECHANISM_MAP',
    'RELATIONSHIP_ARCHETYPE_MAP',
    
    # Patterns
    'ALL_PATTERNS',
    'PATTERN_BY_ID',
    'PATTERNS_BY_RELATIONSHIP',
    
    # Services
    'RelationshipDetector',
    'get_relationship_detector',
    'RelationshipGraphBuilder',
    'initialize_relationship_schema',
    'initialize_graph_schema',
    'get_schema_queries',
]
