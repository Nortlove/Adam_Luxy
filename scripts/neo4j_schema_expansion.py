#!/usr/bin/env python3
"""
NEO4J SCHEMA EXPANSION FOR DATA INTEGRATION
============================================

Expands the Neo4j schema to support all new data sources:
- Context Intelligence (Domain Mapping)
- Persuadability Intelligence (Criteo Uplift)
- Attribution Intelligence (Criteo Attribution)
- Temporal Psychology (Amazon 2015)
- Cross-Platform Validation (Amazon-Reddit)

This script creates:
1. New node types with appropriate constraints and indexes
2. New relationship types
3. Query templates for each new intelligence source
"""

import argparse
import logging
from typing import Dict, List, Tuple

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# NEW NODE SCHEMAS
# =============================================================================

NEW_NODE_SCHEMAS = {
    # Domain/Context Intelligence
    "Domain": {
        "properties": {
            "name": "string",  # Domain name (e.g., "nytimes.com")
            "category": "string",  # IAB category
            "mindset": "string",  # Inferred mindset
            "attention_level": "string",  # high/medium/low
            "last_updated": "datetime",
        },
        "constraints": [
            ("domain_name_unique", "name", "UNIQUE"),
        ],
        "indexes": [
            ("domain_category_idx", "category"),
            ("domain_mindset_idx", "mindset"),
        ],
    },
    
    "Mindset": {
        "properties": {
            "name": "string",  # e.g., "informed", "entertained", "purchasing"
            "description": "string",
            "attention_level": "string",
            "cognitive_load": "string",
            "purchase_intent": "string",
            "recommended_complexity": "string",
            "optimal_tone": "string",
        },
        "constraints": [
            ("mindset_name_unique", "name", "UNIQUE"),
        ],
        "indexes": [],
    },
    
    # Persuadability Intelligence
    "PersuadabilitySegment": {
        "properties": {
            "name": "string",  # e.g., "highly_persuadable", "resistant"
            "uplift_range_low": "float",
            "uplift_range_high": "float",
            "population_percentage": "float",
            "recommendation": "string",
            "bid_multiplier": "float",
            "frequency_cap": "int",
        },
        "constraints": [
            ("persuadability_segment_unique", "name", "UNIQUE"),
        ],
        "indexes": [],
    },
    
    # Attribution Intelligence
    "MechanismSequence": {
        "properties": {
            "sequence_id": "string",  # e.g., "social_proof->scarcity"
            "sequence": "string[]",  # List of mechanisms
            "touchpoints": "int",
            "expected_lift": "float",
            "confidence": "float",
        },
        "constraints": [
            ("mechanism_sequence_unique", "sequence_id", "UNIQUE"),
        ],
        "indexes": [
            ("mechanism_sequence_touchpoints_idx", "touchpoints"),
        ],
    },
    
    # Temporal Psychology
    "TemporalBaseline": {
        "properties": {
            "category": "string",
            "year": "int",
            "avg_review_length": "float",
            "emotional_intensity_mean": "float",
            "emotional_intensity_std": "float",
            "avg_rating": "float",
            "verified_purchase_ratio": "float",
        },
        "constraints": [
            ("temporal_baseline_unique", "category", "UNIQUE"),
        ],
        "indexes": [
            ("temporal_baseline_year_idx", "year"),
        ],
    },
    
    # Cross-Platform Validation  
    "CrossPlatformPattern": {
        "properties": {
            "pattern_name": "string",
            "consistency_expected": "float",
            "confidence_boost": "float",
            "sample_size": "int",
        },
        "constraints": [
            ("cross_platform_pattern_unique", "pattern_name", "UNIQUE"),
        ],
        "indexes": [],
    },
    
    # Enhanced GranularCustomerType
    "GranularType": {
        "properties": {
            "type_code": "string",  # e.g., "impulse_fast_high_promotion_low_explorer_electronics"
            "motivation": "string",
            "decision_style": "string",
            "regulatory_focus": "string",
            "emotional_intensity": "string",
            "price_sensitivity": "string",
            "archetype": "string",
            "domain": "string",
            
            # New enrichment fields
            "persuadability_score": "float",
            "persuadability_segment": "string",
            "optimal_touchpoints": "int",
            "cross_platform_confidence_boost": "float",
        },
        "constraints": [
            ("granular_type_code_unique", "type_code", "UNIQUE"),
        ],
        "indexes": [
            ("granular_type_motivation_idx", "motivation"),
            ("granular_type_persuadability_idx", "persuadability_score"),
            ("granular_type_domain_idx", "domain"),
        ],
    },
}


# =============================================================================
# NEW RELATIONSHIP SCHEMAS
# =============================================================================

NEW_RELATIONSHIP_SCHEMAS = {
    # Context Intelligence Relationships
    "HAS_MINDSET": {
        "from": "Domain",
        "to": "Mindset",
        "properties": {
            "confidence": "float",
            "mechanism_adjustments": "map",  # {mechanism: adjustment_factor}
        },
    },
    
    "MINDSET_AFFECTS_MECHANISM": {
        "from": "Mindset",
        "to": "Mechanism",
        "properties": {
            "adjustment_factor": "float",  # 0.7 = -30%, 1.3 = +30%
        },
    },
    
    # Persuadability Relationships
    "HAS_PERSUADABILITY": {
        "from": "GranularType",
        "to": "PersuadabilitySegment",
        "properties": {
            "score": "float",
            "predicted_uplift": "float",
            "confidence": "float",
        },
    },
    
    "DIMENSION_PREDICTS_PERSUADABILITY": {
        "from": ["Motivation", "DecisionStyle", "EmotionalIntensity"],
        "to": "PersuadabilitySegment",
        "properties": {
            "contribution": "float",  # Weight in persuadability calculation
        },
    },
    
    # Attribution Relationships
    "OPTIMAL_SEQUENCE_FOR": {
        "from": "MechanismSequence",
        "to": "GranularType",
        "properties": {
            "effectiveness": "float",
            "expected_lift": "float",
        },
    },
    
    "MECHANISM_AT_POSITION": {
        "from": "MechanismSequence",
        "to": "Mechanism",
        "properties": {
            "position": "int",  # 0 = first, -1 = last
            "position_type": "string",  # "first", "early", "middle", "late", "last"
            "effectiveness": "float",
        },
    },
    
    # Temporal Relationships
    "HAS_TEMPORAL_BASELINE": {
        "from": "ProductCategory",
        "to": "TemporalBaseline",
        "properties": {
            "drift_from_baseline": "float",
            "authenticity_threshold": "float",
        },
    },
    
    "EVOLVED_FROM": {
        "from": "TemporalBaseline",
        "to": "TemporalBaseline",
        "properties": {
            "years_elapsed": "int",
            "pattern_drift": "map",  # {pattern_name: drift_amount}
        },
    },
    
    # Cross-Platform Relationships
    "VALIDATED_BY_CROSS_PLATFORM": {
        "from": "GranularType",
        "to": "CrossPlatformPattern",
        "properties": {
            "consistency_score": "float",
            "confidence_boost": "float",
        },
    },
}


# =============================================================================
# CYPHER QUERIES
# =============================================================================

CREATE_CONSTRAINT_TEMPLATE = """
CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
FOR (n:{label})
REQUIRE n.{property} IS {constraint_type}
"""

CREATE_INDEX_TEMPLATE = """
CREATE INDEX {index_name} IF NOT EXISTS
FOR (n:{label})
ON (n.{property})
"""

# Query templates for the new intelligence sources
QUERY_TEMPLATES = {
    "get_context_recommendation": """
        MATCH (d:Domain {name: $domain})-[:HAS_MINDSET]->(m:Mindset)
        OPTIONAL MATCH (m)-[r:MINDSET_AFFECTS_MECHANISM]->(mech:Mechanism)
        RETURN m.name AS mindset, 
               m.attention_level AS attention_level,
               m.recommended_complexity AS complexity,
               m.optimal_tone AS tone,
               collect({mechanism: mech.name, adjustment: r.adjustment_factor}) AS mechanism_adjustments
    """,
    
    "get_persuadability_for_type": """
        MATCH (gt:GranularType {type_code: $type_code})-[:HAS_PERSUADABILITY]->(ps:PersuadabilitySegment)
        RETURN gt.persuadability_score AS score,
               ps.name AS segment,
               ps.recommendation AS recommendation,
               ps.bid_multiplier AS bid_multiplier,
               ps.frequency_cap AS frequency_cap
    """,
    
    "get_optimal_sequence": """
        MATCH (gt:GranularType {type_code: $type_code})<-[:OPTIMAL_SEQUENCE_FOR]-(ms:MechanismSequence)
        OPTIONAL MATCH (ms)-[r:MECHANISM_AT_POSITION]->(mech:Mechanism)
        RETURN ms.sequence AS sequence,
               ms.touchpoints AS touchpoints,
               ms.expected_lift AS expected_lift,
               collect({mechanism: mech.name, position: r.position, effectiveness: r.effectiveness}) AS position_details
        ORDER BY ms.expected_lift DESC
        LIMIT 1
    """,
    
    "get_temporal_baseline": """
        MATCH (pc:ProductCategory {name: $category})-[:HAS_TEMPORAL_BASELINE]->(tb:TemporalBaseline)
        RETURN tb.avg_review_length AS avg_length,
               tb.emotional_intensity_mean AS emotional_mean,
               tb.emotional_intensity_std AS emotional_std,
               tb.avg_rating AS avg_rating,
               tb.verified_purchase_ratio AS verified_ratio
    """,
    
    "get_cross_platform_boost": """
        MATCH (gt:GranularType {type_code: $type_code})-[r:VALIDATED_BY_CROSS_PLATFORM]->(cp:CrossPlatformPattern)
        RETURN sum(r.confidence_boost) AS total_boost,
               collect({pattern: cp.pattern_name, consistency: r.consistency_score}) AS validations
    """,
    
    "get_enriched_granular_type": """
        MATCH (gt:GranularType {type_code: $type_code})
        OPTIONAL MATCH (gt)-[:HAS_PERSUADABILITY]->(ps:PersuadabilitySegment)
        OPTIONAL MATCH (gt)<-[:OPTIMAL_SEQUENCE_FOR]-(ms:MechanismSequence)
        OPTIONAL MATCH (gt)-[cpv:VALIDATED_BY_CROSS_PLATFORM]->(cp:CrossPlatformPattern)
        RETURN gt {.*,
               persuadability_segment: ps.name,
               persuadability_recommendation: ps.recommendation,
               optimal_sequence: ms.sequence,
               optimal_touchpoints: ms.touchpoints,
               cross_platform_boost: sum(cpv.confidence_boost)}
    """,
    
    "find_types_by_persuadability": """
        MATCH (gt:GranularType)-[:HAS_PERSUADABILITY]->(ps:PersuadabilitySegment)
        WHERE gt.persuadability_score >= $min_score
        RETURN gt.type_code AS type_code,
               gt.motivation AS motivation,
               gt.decision_style AS decision_style,
               gt.persuadability_score AS score,
               ps.name AS segment
        ORDER BY gt.persuadability_score DESC
        LIMIT $limit
    """,
    
    "mechanism_effectiveness_with_context": """
        MATCH (gt:GranularType {type_code: $type_code})-[me:EFFECTIVE_FOR]->(mech:Mechanism)
        OPTIONAL MATCH (d:Domain {name: $domain})-[:HAS_MINDSET]->(m:Mindset)-[ma:MINDSET_AFFECTS_MECHANISM]->(mech)
        RETURN mech.name AS mechanism,
               me.effectiveness AS base_effectiveness,
               coalesce(ma.adjustment_factor, 1.0) AS context_adjustment,
               me.effectiveness * coalesce(ma.adjustment_factor, 1.0) AS adjusted_effectiveness
        ORDER BY adjusted_effectiveness DESC
    """,
}


# =============================================================================
# SCHEMA CREATION CLASS
# =============================================================================

class Neo4jSchemaExpansion:
    """
    Manages Neo4j schema expansion for new data sources.
    """
    
    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize the schema expansion manager.
        
        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password
        """
        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        logger.info(f"Connected to Neo4j at {uri}")
    
    def close(self):
        """Close the database connection."""
        self._driver.close()
    
    def create_all_constraints(self) -> List[str]:
        """
        Create all constraints for new node types.
        
        Returns:
            List of created constraint names
        """
        created = []
        
        with self._driver.session() as session:
            for label, schema in NEW_NODE_SCHEMAS.items():
                for constraint_name, property_name, constraint_type in schema.get("constraints", []):
                    try:
                        query = f"""
                            CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                            FOR (n:{label})
                            REQUIRE n.{property_name} IS {constraint_type}
                        """
                        session.run(query)
                        created.append(constraint_name)
                        logger.info(f"Created constraint: {constraint_name}")
                    except Exception as e:
                        logger.warning(f"Could not create constraint {constraint_name}: {e}")
        
        return created
    
    def create_all_indexes(self) -> List[str]:
        """
        Create all indexes for new node types.
        
        Returns:
            List of created index names
        """
        created = []
        
        with self._driver.session() as session:
            for label, schema in NEW_NODE_SCHEMAS.items():
                for index_name, property_name in schema.get("indexes", []):
                    try:
                        query = f"""
                            CREATE INDEX {index_name} IF NOT EXISTS
                            FOR (n:{label})
                            ON (n.{property_name})
                        """
                        session.run(query)
                        created.append(index_name)
                        logger.info(f"Created index: {index_name}")
                    except Exception as e:
                        logger.warning(f"Could not create index {index_name}: {e}")
        
        return created
    
    def create_mindset_nodes(self) -> int:
        """
        Create Mindset nodes from the context intelligence module.
        
        Returns:
            Number of nodes created
        """
        # Import mindset definitions
        from adam.intelligence.context_intelligence import MINDSET_PROFILES
        
        count = 0
        with self._driver.session() as session:
            for name, profile in MINDSET_PROFILES.items():
                query = """
                    MERGE (m:Mindset {name: $name})
                    SET m.description = $description,
                        m.attention_level = $attention_level,
                        m.cognitive_load = $cognitive_load,
                        m.purchase_intent = $purchase_intent,
                        m.recommended_complexity = $recommended_complexity,
                        m.optimal_tone = $optimal_tone
                    RETURN m
                """
                session.run(query, {
                    "name": name,
                    "description": profile.description,
                    "attention_level": profile.attention_level,
                    "cognitive_load": profile.cognitive_load,
                    "purchase_intent": profile.purchase_intent,
                    "recommended_complexity": profile.recommended_complexity,
                    "optimal_tone": profile.optimal_tone,
                })
                count += 1
        
        logger.info(f"Created {count} Mindset nodes")
        return count
    
    def create_persuadability_segments(self) -> int:
        """
        Create PersuadabilitySegment nodes.
        
        Returns:
            Number of nodes created
        """
        from adam.intelligence.persuadability_intelligence import PERSUADABILITY_SEGMENTS
        
        count = 0
        with self._driver.session() as session:
            for name, info in PERSUADABILITY_SEGMENTS.items():
                query = """
                    MERGE (ps:PersuadabilitySegment {name: $name})
                    SET ps.uplift_range_low = $uplift_low,
                        ps.uplift_range_high = $uplift_high,
                        ps.population_percentage = $percentage,
                        ps.recommendation = $recommendation
                    RETURN ps
                """
                session.run(query, {
                    "name": name,
                    "uplift_low": info["uplift_range"][0],
                    "uplift_high": info["uplift_range"][1],
                    "percentage": info["percentage"],
                    "recommendation": info["recommendation"],
                })
                count += 1
        
        logger.info(f"Created {count} PersuadabilitySegment nodes")
        return count
    
    def create_temporal_baselines(self) -> int:
        """
        Create TemporalBaseline nodes.
        
        Returns:
            Number of nodes created
        """
        from adam.intelligence.temporal_psychology import CATEGORY_BASELINES_2015
        
        count = 0
        with self._driver.session() as session:
            for category, baseline in CATEGORY_BASELINES_2015.items():
                query = """
                    MERGE (tb:TemporalBaseline {category: $category})
                    SET tb.year = 2015,
                        tb.avg_review_length = $avg_length,
                        tb.emotional_intensity_mean = $emotional_mean,
                        tb.emotional_intensity_std = $emotional_std,
                        tb.avg_rating = $avg_rating,
                        tb.verified_purchase_ratio = $verified_ratio
                    RETURN tb
                """
                session.run(query, {
                    "category": category,
                    "avg_length": baseline.avg_review_length,
                    "emotional_mean": baseline.emotional_intensity_mean,
                    "emotional_std": baseline.emotional_intensity_std,
                    "avg_rating": baseline.avg_rating,
                    "verified_ratio": baseline.verified_purchase_ratio,
                })
                count += 1
        
        logger.info(f"Created {count} TemporalBaseline nodes")
        return count
    
    def create_mechanism_sequences(self) -> int:
        """
        Create MechanismSequence nodes.
        
        Returns:
            Number of nodes created
        """
        from adam.intelligence.attribution_intelligence import OPTIMAL_SEQUENCES_BY_TYPE
        
        count = 0
        with self._driver.session() as session:
            for type_key, info in OPTIMAL_SEQUENCES_BY_TYPE.items():
                sequence = info["sequence"]
                sequence_id = "->".join(sequence)
                
                query = """
                    MERGE (ms:MechanismSequence {sequence_id: $sequence_id})
                    SET ms.sequence = $sequence,
                        ms.touchpoints = $touchpoints,
                        ms.expected_lift = 0.25,
                        ms.confidence = 0.80
                    RETURN ms
                """
                session.run(query, {
                    "sequence_id": sequence_id,
                    "sequence": sequence,
                    "touchpoints": info["touchpoints"],
                })
                count += 1
        
        logger.info(f"Created {count} MechanismSequence nodes")
        return count
    
    def expand_schema(self) -> Dict[str, int]:
        """
        Run full schema expansion.
        
        Returns:
            Dict of created elements counts
        """
        results = {
            "constraints": len(self.create_all_constraints()),
            "indexes": len(self.create_all_indexes()),
            "mindsets": self.create_mindset_nodes(),
            "persuadability_segments": self.create_persuadability_segments(),
            "temporal_baselines": self.create_temporal_baselines(),
            "mechanism_sequences": self.create_mechanism_sequences(),
        }
        
        logger.info(f"Schema expansion complete: {results}")
        return results
    
    def get_query_template(self, query_name: str) -> str:
        """
        Get a query template by name.
        
        Args:
            query_name: Name of the query template
            
        Returns:
            Cypher query string
        """
        return QUERY_TEMPLATES.get(query_name, "")


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Neo4j Schema Expansion for Data Integration")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--username", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", required=True, help="Neo4j password")
    parser.add_argument("--dry-run", action="store_true", help="Print queries without executing")
    parser.add_argument("--queries-only", action="store_true", help="Print query templates")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.queries_only:
        print("\n" + "="*60)
        print("NEO4J QUERY TEMPLATES FOR DATA INTEGRATION")
        print("="*60)
        for name, query in QUERY_TEMPLATES.items():
            print(f"\n### {name} ###")
            print(query.strip())
        return
    
    if args.dry_run:
        print("\n" + "="*60)
        print("SCHEMA EXPANSION (DRY RUN)")
        print("="*60)
        print("\nNew Node Types:")
        for label, schema in NEW_NODE_SCHEMAS.items():
            print(f"  - {label}: {list(schema['properties'].keys())}")
        print("\nNew Relationships:")
        for rel_type, schema in NEW_RELATIONSHIP_SCHEMAS.items():
            print(f"  - {rel_type}: {schema['from']} -> {schema['to']}")
        return
    
    expander = Neo4jSchemaExpansion(args.uri, args.username, args.password)
    
    try:
        results = expander.expand_schema()
        print("\n" + "="*60)
        print("SCHEMA EXPANSION COMPLETE")
        print("="*60)
        for key, value in results.items():
            print(f"  {key}: {value}")
    finally:
        expander.close()


if __name__ == "__main__":
    main()
