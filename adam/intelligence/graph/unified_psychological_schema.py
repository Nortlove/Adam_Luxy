# =============================================================================
# Unified Psychological Intelligence - Neo4j Schema
# Location: adam/intelligence/graph/unified_psychological_schema.py
# =============================================================================

"""
Neo4j Schema for Unified Psychological Intelligence

This module defines the graph schema for storing and querying psychological
intelligence from all 3 analysis modules:
1. Flow State - Audio/context-based psychological states
2. Psychological Needs - 33 psychological needs from brand-consumer alignment
3. Psycholinguistic Constructs - 32 constructs with linguistic markers

Schema Design:
- PsychologicalProfile: Central node linking to brand/product
- PsychologicalConstruct: Individual construct measurements
- PsychologicalNeed: Individual need measurements
- FlowStateProfile: Flow state measurements
- Connects to existing Mechanism and Archetype nodes

Graph Relationships:
- (:Brand)-[:HAS_PROFILE]->(:PsychologicalProfile)
- (:PsychologicalProfile)-[:EXHIBITS_CONSTRUCT]->(:PsychologicalConstruct)
- (:PsychologicalProfile)-[:HAS_NEED]->(:PsychologicalNeed)
- (:PsychologicalProfile)-[:HAS_FLOW_STATE]->(:FlowStateProfile)
- (:PsychologicalProfile)-[:PREDICTS_MECHANISM]->(:Mechanism)
- (:PsychologicalProfile)-[:INDICATES_ARCHETYPE]->(:Archetype)

Usage:
    from adam.intelligence.graph.unified_psychological_schema import (
        UnifiedPsychologicalGraphService,
        get_graph_service
    )
    
    service = get_graph_service(neo4j_driver)
    await service.store_profile(unified_profile)
    
    # Query similar profiles
    similar = await service.find_similar_profiles(unified_profile)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

UNIFIED_PSYCHOLOGICAL_SCHEMA = """
// =============================================================================
// UNIFIED PSYCHOLOGICAL INTELLIGENCE SCHEMA
// =============================================================================

// ---------------------------------------------------------------------------
// CONSTRAINTS - Ensure data integrity
// ---------------------------------------------------------------------------

// Psychological Profile Constraints
CREATE CONSTRAINT psychological_profile_id IF NOT EXISTS
FOR (p:PsychologicalProfile) REQUIRE p.profile_id IS UNIQUE;

// Psychological Construct Constraints
CREATE CONSTRAINT psychological_construct_id IF NOT EXISTS
FOR (c:PsychologicalConstruct) REQUIRE c.construct_id IS UNIQUE;

// Psychological Need Constraints  
CREATE CONSTRAINT psychological_need_id IF NOT EXISTS
FOR (n:PsychologicalNeed) REQUIRE n.need_id IS UNIQUE;

// Flow State Profile Constraints
CREATE CONSTRAINT flow_state_profile_id IF NOT EXISTS
FOR (f:FlowStateProfile) REQUIRE f.flow_profile_id IS UNIQUE;

// Brand-Product Constraints
CREATE CONSTRAINT brand_name_unique IF NOT EXISTS
FOR (b:Brand) REQUIRE b.name IS UNIQUE;

// ---------------------------------------------------------------------------
// INDEXES - Optimize query performance
// ---------------------------------------------------------------------------

// Profile lookup indexes
CREATE INDEX profile_brand IF NOT EXISTS
FOR (p:PsychologicalProfile) ON (p.brand_name);

CREATE INDEX profile_product IF NOT EXISTS
FOR (p:PsychologicalProfile) ON (p.product_name);

CREATE INDEX profile_archetype IF NOT EXISTS
FOR (p:PsychologicalProfile) ON (p.primary_archetype);

CREATE INDEX profile_created IF NOT EXISTS
FOR (p:PsychologicalProfile) ON (p.created_at);

// Construct indexes
CREATE INDEX construct_type IF NOT EXISTS
FOR (c:PsychologicalConstruct) ON (c.construct_type);

CREATE INDEX construct_score IF NOT EXISTS
FOR (c:PsychologicalConstruct) ON (c.score);

// Need indexes
CREATE INDEX need_category IF NOT EXISTS
FOR (n:PsychologicalNeed) ON (n.category);

CREATE INDEX need_activation IF NOT EXISTS
FOR (n:PsychologicalNeed) ON (n.activation_strength);

// Flow state indexes
CREATE INDEX flow_arousal IF NOT EXISTS
FOR (f:FlowStateProfile) ON (f.arousal);

CREATE INDEX flow_valence IF NOT EXISTS
FOR (f:FlowStateProfile) ON (f.valence);

// Full-text search indexes
CREATE FULLTEXT INDEX profile_search IF NOT EXISTS
FOR (p:PsychologicalProfile) ON EACH [p.brand_name, p.product_name];

// ---------------------------------------------------------------------------
// COMPOSITE INDEXES - Multi-property queries
// ---------------------------------------------------------------------------

CREATE INDEX profile_brand_product IF NOT EXISTS
FOR (p:PsychologicalProfile) ON (p.brand_name, p.product_name);

CREATE INDEX construct_profile IF NOT EXISTS
FOR (c:PsychologicalConstruct) ON (c.profile_id, c.construct_type);
"""


# =============================================================================
# CYPHER QUERIES
# =============================================================================

class UnifiedPsychologicalQueries:
    """Cypher queries for unified psychological intelligence operations."""
    
    # =========================================================================
    # PROFILE CRUD
    # =========================================================================
    
    CREATE_PROFILE = """
    CREATE (p:PsychologicalProfile {
        profile_id: $profile_id,
        brand_name: $brand_name,
        product_name: $product_name,
        primary_archetype: $primary_archetype,
        archetype_confidence: $archetype_confidence,
        reviews_analyzed: $reviews_analyzed,
        analysis_time_ms: $analysis_time_ms,
        modules_used: $modules_used,
        created_at: datetime(),
        
        // Flow State Summary
        flow_arousal: $flow_arousal,
        flow_valence: $flow_valence,
        flow_energy: $flow_energy,
        flow_cognitive_load: $flow_cognitive_load,
        ad_receptivity: $ad_receptivity,
        
        // Regulatory Focus Summary
        promotion_focus: $promotion_focus,
        prevention_focus: $prevention_focus,
        
        // Overall Alignment
        alignment_score: $alignment_score
    })
    RETURN p
    """
    
    GET_PROFILE = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    OPTIONAL MATCH (p)-[:EXHIBITS_CONSTRUCT]->(c:PsychologicalConstruct)
    OPTIONAL MATCH (p)-[:HAS_NEED]->(n:PsychologicalNeed)
    OPTIONAL MATCH (p)-[:HAS_FLOW_STATE]->(f:FlowStateProfile)
    RETURN p, 
           collect(DISTINCT c) as constructs,
           collect(DISTINCT n) as needs,
           collect(DISTINCT f) as flow_states
    """
    
    GET_PROFILE_BY_BRAND_PRODUCT = """
    MATCH (p:PsychologicalProfile {
        brand_name: $brand_name,
        product_name: $product_name
    })
    RETURN p
    ORDER BY p.created_at DESC
    LIMIT 1
    """
    
    # =========================================================================
    # CONSTRUCT OPERATIONS
    # =========================================================================
    
    CREATE_CONSTRUCT = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    CREATE (c:PsychologicalConstruct {
        construct_id: $construct_id,
        profile_id: $profile_id,
        construct_type: $construct_type,
        construct_name: $construct_name,
        score: $score,
        confidence: $confidence,
        effect_size: $effect_size,
        ad_recommendation: $ad_recommendation,
        supporting_evidence: $supporting_evidence,
        created_at: datetime()
    })
    CREATE (p)-[:EXHIBITS_CONSTRUCT {
        score: $score,
        confidence: $confidence
    }]->(c)
    RETURN c
    """
    
    GET_CONSTRUCTS_FOR_PROFILE = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
           -[:EXHIBITS_CONSTRUCT]->(c:PsychologicalConstruct)
    RETURN c
    ORDER BY c.score DESC
    """
    
    # =========================================================================
    # NEED OPERATIONS
    # =========================================================================
    
    CREATE_NEED = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    CREATE (n:PsychologicalNeed {
        need_id: $need_id,
        profile_id: $profile_id,
        need_type: $need_type,
        need_name: $need_name,
        category: $category,
        activation_strength: $activation_strength,
        alignment_status: $alignment_status,
        unmet: $unmet,
        recommended_actions: $recommended_actions,
        created_at: datetime()
    })
    CREATE (p)-[:HAS_NEED {
        activation: $activation_strength,
        alignment: $alignment_status
    }]->(n)
    RETURN n
    """
    
    GET_NEEDS_FOR_PROFILE = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
           -[:HAS_NEED]->(n:PsychologicalNeed)
    RETURN n
    ORDER BY n.activation_strength DESC
    """
    
    GET_UNMET_NEEDS = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
           -[:HAS_NEED]->(n:PsychologicalNeed {unmet: true})
    RETURN n
    ORDER BY n.activation_strength DESC
    """
    
    # =========================================================================
    # FLOW STATE OPERATIONS
    # =========================================================================
    
    CREATE_FLOW_STATE = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    CREATE (f:FlowStateProfile {
        flow_profile_id: $flow_profile_id,
        profile_id: $profile_id,
        arousal: $arousal,
        valence: $valence,
        energy: $energy,
        cognitive_load: $cognitive_load,
        nostalgia: $nostalgia,
        social_energy: $social_energy,
        flow_stability: $flow_stability,
        ad_receptivity: $ad_receptivity,
        optimal_formats: $optimal_formats,
        recommended_tone: $recommended_tone,
        created_at: datetime()
    })
    CREATE (p)-[:HAS_FLOW_STATE]->(f)
    RETURN f
    """
    
    # =========================================================================
    # MECHANISM PREDICTION CONNECTIONS
    # =========================================================================
    
    CONNECT_MECHANISM_PREDICTION = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    MATCH (m:Mechanism {name: $mechanism_name})
    MERGE (p)-[r:PREDICTS_MECHANISM]->(m)
    SET r.predicted_effectiveness = $effectiveness,
        r.confidence = $confidence,
        r.source_constructs = $source_constructs,
        r.updated_at = datetime()
    RETURN r
    """
    
    # =========================================================================
    # ARCHETYPE CONNECTIONS
    # =========================================================================
    
    CONNECT_ARCHETYPE = """
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    MATCH (a:Archetype {name: $archetype_name})
    MERGE (p)-[r:INDICATES_ARCHETYPE]->(a)
    SET r.confidence = $confidence,
        r.contributing_constructs = $contributing_constructs,
        r.updated_at = datetime()
    RETURN r
    """
    
    # =========================================================================
    # BRAND CONNECTIONS
    # =========================================================================
    
    CONNECT_TO_BRAND = """
    MERGE (b:Brand {name: $brand_name})
    ON CREATE SET b.created_at = datetime()
    WITH b
    MATCH (p:PsychologicalProfile {profile_id: $profile_id})
    MERGE (b)-[r:HAS_PROFILE]->(p)
    SET r.product_name = $product_name,
        r.created_at = datetime()
    RETURN b, r, p
    """
    
    # =========================================================================
    # SIMILARITY QUERIES
    # =========================================================================
    
    FIND_SIMILAR_PROFILES = """
    MATCH (source:PsychologicalProfile {profile_id: $profile_id})
    MATCH (target:PsychologicalProfile)
    WHERE target.profile_id <> source.profile_id
    
    // Calculate similarity based on key dimensions
    WITH source, target,
         abs(source.flow_arousal - target.flow_arousal) as arousal_diff,
         abs(source.flow_valence - target.flow_valence) as valence_diff,
         abs(source.promotion_focus - target.promotion_focus) as promo_diff,
         abs(source.prevention_focus - target.prevention_focus) as prev_diff
    
    // Calculate overall similarity (1 - average difference)
    WITH source, target,
         1 - ((arousal_diff + valence_diff + promo_diff + prev_diff) / 4) as similarity
    
    WHERE similarity > $min_similarity
    
    RETURN target, similarity
    ORDER BY similarity DESC
    LIMIT $limit
    """
    
    FIND_PROFILES_BY_ARCHETYPE = """
    MATCH (p:PsychologicalProfile)
    WHERE p.primary_archetype = $archetype
      AND p.archetype_confidence >= $min_confidence
    RETURN p
    ORDER BY p.archetype_confidence DESC
    LIMIT $limit
    """
    
    FIND_PROFILES_BY_CONSTRUCT = """
    MATCH (p:PsychologicalProfile)
           -[:EXHIBITS_CONSTRUCT]->(c:PsychologicalConstruct {construct_type: $construct_type})
    WHERE c.score >= $min_score
    RETURN p, c
    ORDER BY c.score DESC
    LIMIT $limit
    """
    
    # =========================================================================
    # LEARNING/ANALYTICS QUERIES
    # =========================================================================
    
    GET_CONSTRUCT_DISTRIBUTION = """
    MATCH (c:PsychologicalConstruct {construct_type: $construct_type})
    RETURN 
        avg(c.score) as avg_score,
        stdev(c.score) as std_score,
        min(c.score) as min_score,
        max(c.score) as max_score,
        count(c) as total_observations
    """
    
    GET_ARCHETYPE_MECHANISM_CORRELATIONS = """
    MATCH (p:PsychologicalProfile)-[pm:PREDICTS_MECHANISM]->(m:Mechanism)
    WHERE p.primary_archetype = $archetype
    RETURN m.name as mechanism, 
           avg(pm.predicted_effectiveness) as avg_effectiveness,
           count(pm) as observations
    ORDER BY avg_effectiveness DESC
    """
    
    GET_NEED_ALIGNMENT_BY_BRAND = """
    MATCH (b:Brand {name: $brand_name})-[:HAS_PROFILE]->(p:PsychologicalProfile)
           -[:HAS_NEED]->(n:PsychologicalNeed)
    RETURN n.category as category,
           avg(n.activation_strength) as avg_activation,
           sum(CASE WHEN n.unmet THEN 1 ELSE 0 END) as unmet_count,
           count(n) as total_needs
    ORDER BY avg_activation DESC
    """


# =============================================================================
# GRAPH SERVICE
# =============================================================================

class UnifiedPsychologicalGraphService:
    """
    Service for storing and querying unified psychological intelligence in Neo4j.
    
    Integrates with the existing ADAM graph infrastructure.
    """
    
    def __init__(self, neo4j_driver=None):
        """
        Initialize the graph service.
        
        Args:
            neo4j_driver: Neo4j driver instance
        """
        self._driver = neo4j_driver
        self._schema_initialized = False
    
    async def initialize_schema(self) -> bool:
        """
        Initialize the Neo4j schema for unified psychological intelligence.
        
        Returns True if successful.
        """
        if self._driver is None:
            logger.warning("No Neo4j driver available - schema not initialized")
            return False
        
        try:
            async with self._driver.session() as session:
                # Split schema into individual statements
                for statement in UNIFIED_PSYCHOLOGICAL_SCHEMA.split(";"):
                    statement = statement.strip()
                    if statement and not statement.startswith("//"):
                        await session.run(statement)
            
            self._schema_initialized = True
            logger.info("Unified psychological intelligence schema initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return False
    
    async def store_profile(
        self,
        profile: 'UnifiedPsychologicalProfile',
    ) -> bool:
        """
        Store a unified psychological profile in Neo4j.
        
        Creates all related nodes and relationships.
        """
        if self._driver is None:
            logger.warning("No Neo4j driver - profile not stored")
            return False
        
        try:
            async with self._driver.session() as session:
                # 1. Create main profile node
                await session.run(
                    UnifiedPsychologicalQueries.CREATE_PROFILE,
                    profile_id=profile.profile_id,
                    brand_name=profile.brand_name,
                    product_name=profile.product_name,
                    primary_archetype=profile.primary_archetype,
                    archetype_confidence=profile.archetype_confidence,
                    reviews_analyzed=profile.reviews_analyzed,
                    analysis_time_ms=profile.analysis_time_ms,
                    modules_used=profile.modules_used,
                    flow_arousal=profile.flow_state.arousal,
                    flow_valence=profile.flow_state.valence,
                    flow_energy=profile.flow_state.energy,
                    flow_cognitive_load=profile.flow_state.cognitive_load,
                    ad_receptivity=profile.flow_state.ad_receptivity_score,
                    promotion_focus=profile.psychological_needs.promotion_focus,
                    prevention_focus=profile.psychological_needs.prevention_focus,
                    alignment_score=profile.psychological_needs.overall_alignment_score,
                )
                
                # 2. Create construct nodes
                for construct_id, score in profile.unified_constructs.items():
                    confidence = profile.psycholinguistic.confidence_scores.get(construct_id, 0.5)
                    await session.run(
                        UnifiedPsychologicalQueries.CREATE_CONSTRUCT,
                        construct_id=f"{profile.profile_id}_{construct_id}",
                        profile_id=profile.profile_id,
                        construct_type=construct_id,
                        construct_name=construct_id.replace("_", " ").title(),
                        score=score,
                        confidence=confidence,
                        effect_size=0.0,  # Could be populated from effect size map
                        ad_recommendation="",
                        supporting_evidence=[],
                    )
                
                # 3. Create need nodes
                for need_id, activation in profile.psychological_needs.primary_needs[:20]:
                    # Determine category from need_id prefix
                    category = need_id.split("_")[0] if "_" in need_id else "general"
                    unmet = need_id in profile.psychological_needs.unmet_needs
                    
                    await session.run(
                        UnifiedPsychologicalQueries.CREATE_NEED,
                        need_id=f"{profile.profile_id}_{need_id}",
                        profile_id=profile.profile_id,
                        need_type=need_id,
                        need_name=need_id.replace("_", " ").title(),
                        category=category,
                        activation_strength=activation,
                        alignment_status="unmet" if unmet else "met",
                        unmet=unmet,
                        recommended_actions=[],
                    )
                
                # 4. Create flow state node
                await session.run(
                    UnifiedPsychologicalQueries.CREATE_FLOW_STATE,
                    flow_profile_id=f"{profile.profile_id}_flow",
                    profile_id=profile.profile_id,
                    arousal=profile.flow_state.arousal,
                    valence=profile.flow_state.valence,
                    energy=profile.flow_state.energy,
                    cognitive_load=profile.flow_state.cognitive_load,
                    nostalgia=profile.flow_state.nostalgia,
                    social_energy=profile.flow_state.social_energy,
                    flow_stability=profile.flow_state.flow_stability,
                    ad_receptivity=profile.flow_state.ad_receptivity_score,
                    optimal_formats=profile.flow_state.optimal_formats,
                    recommended_tone=profile.flow_state.recommended_tone,
                )
                
                # 5. Connect to brand
                await session.run(
                    UnifiedPsychologicalQueries.CONNECT_TO_BRAND,
                    brand_name=profile.brand_name,
                    product_name=profile.product_name,
                    profile_id=profile.profile_id,
                )
                
                # 6. Connect mechanism predictions (if Mechanism nodes exist)
                for mechanism, effectiveness in profile.mechanism_predictions.items():
                    try:
                        await session.run(
                            UnifiedPsychologicalQueries.CONNECT_MECHANISM_PREDICTION,
                            profile_id=profile.profile_id,
                            mechanism_name=mechanism.title(),
                            effectiveness=effectiveness,
                            confidence=0.7,
                            source_constructs=list(profile.unified_constructs.keys())[:5],
                        )
                    except Exception:
                        # Mechanism node may not exist yet
                        pass
                
                logger.info(f"Stored profile {profile.profile_id} in Neo4j")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store profile in Neo4j: {e}")
            return False
    
    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a profile from Neo4j by ID."""
        if self._driver is None:
            return None
        
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    UnifiedPsychologicalQueries.GET_PROFILE,
                    profile_id=profile_id,
                )
                record = await result.single()
                
                if record:
                    return {
                        "profile": dict(record["p"]),
                        "constructs": [dict(c) for c in record["constructs"]],
                        "needs": [dict(n) for n in record["needs"]],
                        "flow_states": [dict(f) for f in record["flow_states"]],
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return None
    
    async def find_similar_profiles(
        self,
        profile_id: str,
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find profiles similar to the given profile."""
        if self._driver is None:
            return []
        
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    UnifiedPsychologicalQueries.FIND_SIMILAR_PROFILES,
                    profile_id=profile_id,
                    min_similarity=min_similarity,
                    limit=limit,
                )
                
                profiles = []
                async for record in result:
                    profiles.append({
                        "profile": dict(record["target"]),
                        "similarity": record["similarity"],
                    })
                
                return profiles
                
        except Exception as e:
            logger.error(f"Failed to find similar profiles: {e}")
            return []
    
    async def get_mechanism_insights(
        self,
        archetype: str,
    ) -> List[Dict[str, Any]]:
        """Get mechanism effectiveness insights for an archetype."""
        if self._driver is None:
            return []
        
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    UnifiedPsychologicalQueries.GET_ARCHETYPE_MECHANISM_CORRELATIONS,
                    archetype=archetype,
                )
                
                insights = []
                async for record in result:
                    insights.append({
                        "mechanism": record["mechanism"],
                        "avg_effectiveness": record["avg_effectiveness"],
                        "observations": record["observations"],
                    })
                
                return insights
                
        except Exception as e:
            logger.error(f"Failed to get mechanism insights: {e}")
            return []


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_graph_service: Optional[UnifiedPsychologicalGraphService] = None


def get_graph_service(neo4j_driver=None) -> UnifiedPsychologicalGraphService:
    """Get the singleton graph service instance."""
    global _graph_service
    if _graph_service is None:
        _graph_service = UnifiedPsychologicalGraphService(neo4j_driver)
    elif neo4j_driver is not None and _graph_service._driver is None:
        _graph_service._driver = neo4j_driver
    return _graph_service


def reset_graph_service() -> None:
    """Reset the singleton (for testing)."""
    global _graph_service
    _graph_service = None
