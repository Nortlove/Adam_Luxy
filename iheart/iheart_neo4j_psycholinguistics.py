#!/usr/bin/env python3
"""
iHeartMedia Neo4j Psycholinguistic Advertising Graph Database
=============================================================

This script creates a Neo4j graph database optimized for psycholinguistic
advertising targeting. It models the State-Behavior-Traits (SBT) framework
plus nonconscious analytics dimensions.

Schema Design Philosophy:
- Rich descriptive text stored on nodes (vector embedding ready)
- Psycholinguistic dimensions as separate queryable node types
- Weighted relationships for matching intensity scores
- Temporal structure for time-based optimization

Author: Claude (Anthropic)
Date: 2026-01-26
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# PSYCHOLINGUISTIC TAXONOMY DEFINITIONS
# =============================================================================
# These taxonomies define the State-Behavior-Traits framework for ad targeting

EMOTIONAL_STATES = {
    # Primary emotions with valence and arousal
    "excitement": {"valence": 0.8, "arousal": 0.9, "category": "positive_high"},
    "joy": {"valence": 0.9, "arousal": 0.7, "category": "positive_high"},
    "contentment": {"valence": 0.7, "arousal": 0.3, "category": "positive_low"},
    "serenity": {"valence": 0.6, "arousal": 0.2, "category": "positive_low"},
    "nostalgia": {"valence": 0.5, "arousal": 0.4, "category": "mixed"},
    "curiosity": {"valence": 0.6, "arousal": 0.6, "category": "positive_mid"},
    "anticipation": {"valence": 0.7, "arousal": 0.7, "category": "positive_high"},
    "amusement": {"valence": 0.8, "arousal": 0.6, "category": "positive_mid"},
    "inspiration": {"valence": 0.8, "arousal": 0.7, "category": "positive_high"},
    "empathy": {"valence": 0.5, "arousal": 0.5, "category": "social"},
    "connection": {"valence": 0.7, "arousal": 0.5, "category": "social"},
    "belonging": {"valence": 0.7, "arousal": 0.4, "category": "social"},
    "tension": {"valence": -0.3, "arousal": 0.7, "category": "negative_high"},
    "suspense": {"valence": 0.0, "arousal": 0.8, "category": "mixed"},
    "fear": {"valence": -0.7, "arousal": 0.8, "category": "negative_high"},
    "sadness": {"valence": -0.6, "arousal": 0.3, "category": "negative_low"},
    "anger": {"valence": -0.7, "arousal": 0.8, "category": "negative_high"},
    "outrage": {"valence": -0.8, "arousal": 0.9, "category": "negative_high"},
    "trust": {"valence": 0.6, "arousal": 0.3, "category": "social"},
    "admiration": {"valence": 0.7, "arousal": 0.5, "category": "social"},
}

MINDSETS = {
    # Cognitive states during content consumption
    "learning": {"openness": 0.9, "focus": 0.8, "receptivity": 0.9},
    "entertainment": {"openness": 0.7, "focus": 0.4, "receptivity": 0.6},
    "escapism": {"openness": 0.5, "focus": 0.3, "receptivity": 0.4},
    "information_seeking": {"openness": 0.8, "focus": 0.9, "receptivity": 0.8},
    "social_connection": {"openness": 0.7, "focus": 0.5, "receptivity": 0.7},
    "relaxation": {"openness": 0.6, "focus": 0.2, "receptivity": 0.5},
    "commute_routine": {"openness": 0.5, "focus": 0.3, "receptivity": 0.6},
    "background_listening": {"openness": 0.3, "focus": 0.1, "receptivity": 0.3},
    "active_engagement": {"openness": 0.8, "focus": 0.8, "receptivity": 0.8},
    "critical_thinking": {"openness": 0.9, "focus": 0.9, "receptivity": 0.5},
    "emotional_processing": {"openness": 0.7, "focus": 0.6, "receptivity": 0.7},
    "identity_affirmation": {"openness": 0.4, "focus": 0.7, "receptivity": 0.6},
}

BEHAVIORAL_TENDENCIES = {
    # Behavior patterns associated with content types
    "impulsive_action": {"immediacy": 0.9, "consideration": 0.2},
    "deliberate_consideration": {"immediacy": 0.2, "consideration": 0.9},
    "social_sharing": {"social": 0.9, "private": 0.2},
    "private_consumption": {"social": 0.2, "private": 0.9},
    "brand_loyalty": {"switching": 0.2, "commitment": 0.9},
    "variety_seeking": {"switching": 0.9, "commitment": 0.3},
    "price_sensitivity": {"value_focus": 0.9, "premium_acceptance": 0.2},
    "premium_acceptance": {"value_focus": 0.3, "premium_acceptance": 0.9},
    "early_adoption": {"innovation": 0.9, "tradition": 0.2},
    "late_majority": {"innovation": 0.3, "tradition": 0.7},
    "opinion_leadership": {"influence": 0.9, "follower": 0.2},
    "conformity": {"influence": 0.2, "follower": 0.8},
    "information_gathering": {"research": 0.9, "impulse": 0.2},
    "experience_seeking": {"novelty": 0.8, "familiarity": 0.3},
}

URGES = {
    # Action impulses content can trigger
    "purchase_intent": {"conversion_potential": 0.9},
    "brand_discovery": {"conversion_potential": 0.4},
    "share_content": {"virality_potential": 0.8},
    "learn_more": {"engagement_depth": 0.7},
    "connect_socially": {"community_building": 0.8},
    "self_improvement": {"aspiration_level": 0.8},
    "entertainment_continuation": {"retention": 0.7},
    "escape_reality": {"immersion_need": 0.8},
    "validate_beliefs": {"confirmation_seeking": 0.7},
    "challenge_assumptions": {"growth_mindset": 0.8},
    "nostalgic_reflection": {"memory_activation": 0.7},
    "fear_response": {"urgency_creation": 0.8},
    "desire_arousal": {"want_activation": 0.9},
    "competitive_drive": {"achievement_motivation": 0.8},
}

PERSONALITY_TRAITS = {
    # Big Five + additional relevant traits
    "openness_high": {"dimension": "openness", "level": "high", "description": "Creative, curious, appreciates art and new experiences"},
    "openness_low": {"dimension": "openness", "level": "low", "description": "Practical, conventional, prefers routine"},
    "conscientiousness_high": {"dimension": "conscientiousness", "level": "high", "description": "Organized, dependable, self-disciplined"},
    "conscientiousness_low": {"dimension": "conscientiousness", "level": "low", "description": "Flexible, spontaneous, less structured"},
    "extraversion_high": {"dimension": "extraversion", "level": "high", "description": "Outgoing, energetic, seeks social stimulation"},
    "extraversion_low": {"dimension": "extraversion", "level": "low", "description": "Reserved, solitary, lower need for social interaction"},
    "agreeableness_high": {"dimension": "agreeableness", "level": "high", "description": "Cooperative, trusting, helpful"},
    "agreeableness_low": {"dimension": "agreeableness", "level": "low", "description": "Competitive, skeptical, challenging"},
    "neuroticism_high": {"dimension": "neuroticism", "level": "high", "description": "Sensitive, nervous, prone to negative emotions"},
    "neuroticism_low": {"dimension": "neuroticism", "level": "low", "description": "Secure, confident, emotionally stable"},
    # Additional advertising-relevant traits
    "need_for_cognition": {"dimension": "cognitive", "level": "high", "description": "Enjoys thinking, appreciates complex arguments"},
    "need_for_affect": {"dimension": "emotional", "level": "high", "description": "Seeks emotional experiences, responsive to emotional appeals"},
    "self_monitoring": {"dimension": "social", "level": "high", "description": "Adapts behavior to social situations, image conscious"},
    "sensation_seeking": {"dimension": "stimulation", "level": "high", "description": "Seeks novel, intense experiences"},
    "materialism": {"dimension": "values", "level": "high", "description": "Values possessions and status symbols"},
    "frugality": {"dimension": "values", "level": "high", "description": "Values resourcefulness and avoiding waste"},
}

COGNITIVE_STYLES = {
    # Information processing patterns
    "analytical": {"processing": "systematic", "depth": "deep", "speed": "slow"},
    "intuitive": {"processing": "holistic", "depth": "surface", "speed": "fast"},
    "visual": {"modality": "visual", "preference": 0.9},
    "auditory": {"modality": "auditory", "preference": 0.9},
    "verbal": {"modality": "verbal", "preference": 0.9},
    "sequential": {"organization": "linear", "structure": 0.9},
    "global": {"organization": "holistic", "structure": 0.3},
    "reflective": {"engagement": "internal", "processing_speed": 0.3},
    "active": {"engagement": "external", "processing_speed": 0.8},
    "concrete": {"abstraction": "low", "example_preference": 0.9},
    "abstract": {"abstraction": "high", "example_preference": 0.4},
}

PERSUASION_TECHNIQUES = {
    # Cialdini's principles + additional techniques
    "reciprocity": {"principle": "give_to_receive", "effectiveness_context": "gift_offers"},
    "commitment_consistency": {"principle": "small_to_large", "effectiveness_context": "brand_loyalty"},
    "social_proof": {"principle": "others_do_it", "effectiveness_context": "testimonials"},
    "authority": {"principle": "expert_endorsement", "effectiveness_context": "professional_products"},
    "liking": {"principle": "similar_attractive", "effectiveness_context": "lifestyle_brands"},
    "scarcity": {"principle": "limited_availability", "effectiveness_context": "urgency_creation"},
    "unity": {"principle": "shared_identity", "effectiveness_context": "community_brands"},
    # Additional persuasion approaches
    "storytelling": {"technique": "narrative_transport", "effectiveness_context": "emotional_products"},
    "humor": {"technique": "entertainment", "effectiveness_context": "low_involvement_products"},
    "fear_appeal": {"technique": "threat_solution", "effectiveness_context": "insurance_health"},
    "aspiration": {"technique": "ideal_self", "effectiveness_context": "luxury_brands"},
    "nostalgia": {"technique": "past_connection", "effectiveness_context": "heritage_brands"},
    "rational_argument": {"technique": "logical_evidence", "effectiveness_context": "high_involvement_products"},
    "emotional_appeal": {"technique": "feeling_evocation", "effectiveness_context": "experiential_products"},
    "comparison": {"technique": "competitive_positioning", "effectiveness_context": "differentiated_products"},
}

TIME_SLOTS = {
    # Radio/podcast listening contexts
    "early_morning": {"hours": "5-7", "context": "wake_up", "attention": 0.5, "mood": "groggy_to_alert"},
    "morning_drive": {"hours": "7-9", "context": "commute", "attention": 0.6, "mood": "focused_stressed"},
    "late_morning": {"hours": "9-12", "context": "work", "attention": 0.7, "mood": "productive"},
    "midday": {"hours": "12-14", "context": "lunch", "attention": 0.5, "mood": "relaxed_break"},
    "afternoon": {"hours": "14-17", "context": "work", "attention": 0.6, "mood": "afternoon_slump"},
    "evening_drive": {"hours": "17-19", "context": "commute", "attention": 0.5, "mood": "tired_relieved"},
    "evening": {"hours": "19-22", "context": "leisure", "attention": 0.7, "mood": "relaxed_entertainment"},
    "late_night": {"hours": "22-1", "context": "wind_down", "attention": 0.4, "mood": "reflective_tired"},
    "overnight": {"hours": "1-5", "context": "sleep_work", "attention": 0.3, "mood": "low_energy"},
    "weekend_morning": {"hours": "8-12", "context": "leisure", "attention": 0.6, "mood": "relaxed_free"},
    "weekend_afternoon": {"hours": "12-18", "context": "activities", "attention": 0.5, "mood": "active_social"},
    "weekend_evening": {"hours": "18-24", "context": "entertainment", "attention": 0.7, "mood": "social_relaxed"},
}

# =============================================================================
# CONTENT-TO-PSYCHOLINGUISTIC MAPPING RULES
# =============================================================================
# These rules infer psycholinguistic dimensions from content descriptions

CONTENT_PSYCHOLINGUISTIC_MAPPINGS = {
    # Format-based mappings
    "formats": {
        "Top 40/CHR": {
            "emotions": [("excitement", 0.8), ("joy", 0.7), ("anticipation", 0.6)],
            "mindsets": [("entertainment", 0.8), ("commute_routine", 0.7)],
            "behaviors": [("social_sharing", 0.7), ("variety_seeking", 0.6)],
            "traits": [("extraversion_high", 0.7), ("openness_high", 0.6)],
            "persuasion": [("social_proof", 0.8), ("liking", 0.7), ("scarcity", 0.6)],
        },
        "Country": {
            "emotions": [("nostalgia", 0.8), ("contentment", 0.7), ("connection", 0.8), ("belonging", 0.7)],
            "mindsets": [("identity_affirmation", 0.8), ("emotional_processing", 0.7)],
            "behaviors": [("brand_loyalty", 0.8), ("conformity", 0.6)],
            "traits": [("agreeableness_high", 0.7), ("conscientiousness_high", 0.6)],
            "persuasion": [("unity", 0.9), ("storytelling", 0.8), ("nostalgia", 0.8)],
        },
        "Urban Contemporary/Hip-Hop": {
            "emotions": [("excitement", 0.8), ("empowerment", 0.7), ("connection", 0.7)],
            "mindsets": [("identity_affirmation", 0.8), ("active_engagement", 0.7)],
            "behaviors": [("opinion_leadership", 0.7), ("early_adoption", 0.7), ("social_sharing", 0.8)],
            "traits": [("extraversion_high", 0.7), ("sensation_seeking", 0.7)],
            "persuasion": [("social_proof", 0.9), ("authority", 0.7), ("aspiration", 0.8)],
        },
        "Alternative Rock": {
            "emotions": [("curiosity", 0.7), ("tension", 0.5), ("connection", 0.6)],
            "mindsets": [("identity_affirmation", 0.7), ("critical_thinking", 0.6)],
            "behaviors": [("early_adoption", 0.7), ("variety_seeking", 0.7)],
            "traits": [("openness_high", 0.8), ("agreeableness_low", 0.5)],
            "persuasion": [("authenticity", 0.9), ("comparison", 0.6)],
        },
        "Active Rock": {
            "emotions": [("excitement", 0.8), ("anger", 0.4), ("empowerment", 0.7)],
            "mindsets": [("active_engagement", 0.8), ("escapism", 0.6)],
            "behaviors": [("brand_loyalty", 0.7), ("experience_seeking", 0.7)],
            "traits": [("sensation_seeking", 0.8), ("extraversion_high", 0.6)],
            "persuasion": [("aspiration", 0.7), ("comparison", 0.6)],
        },
        "Classic Rock": {
            "emotions": [("nostalgia", 0.9), ("contentment", 0.7), ("joy", 0.6)],
            "mindsets": [("relaxation", 0.7), ("emotional_processing", 0.6)],
            "behaviors": [("brand_loyalty", 0.9), ("late_majority", 0.7)],
            "traits": [("conscientiousness_high", 0.6), ("openness_low", 0.5)],
            "persuasion": [("nostalgia", 0.9), ("unity", 0.7), ("authority", 0.6)],
        },
        "News/Talk": {
            "emotions": [("curiosity", 0.8), ("outrage", 0.6), ("trust", 0.5)],
            "mindsets": [("information_seeking", 0.9), ("critical_thinking", 0.8)],
            "behaviors": [("information_gathering", 0.9), ("opinion_leadership", 0.7)],
            "traits": [("need_for_cognition", 0.9), ("conscientiousness_high", 0.7)],
            "persuasion": [("authority", 0.9), ("rational_argument", 0.8), ("fear_appeal", 0.6)],
        },
        "Adult Contemporary": {
            "emotions": [("serenity", 0.7), ("nostalgia", 0.7), ("contentment", 0.8)],
            "mindsets": [("relaxation", 0.8), ("background_listening", 0.7)],
            "behaviors": [("brand_loyalty", 0.7), ("price_sensitivity", 0.5)],
            "traits": [("agreeableness_high", 0.7), ("neuroticism_low", 0.6)],
            "persuasion": [("liking", 0.8), ("emotional_appeal", 0.8), ("storytelling", 0.7)],
        },
    },
    # Keyword-based emotional triggers in descriptions
    "keywords_to_emotions": {
        "energy": [("excitement", 0.8), ("joy", 0.6)],
        "laugh": [("amusement", 0.9), ("joy", 0.7)],
        "comedy": [("amusement", 0.9), ("joy", 0.6)],
        "prank": [("amusement", 0.8), ("anticipation", 0.6)],
        "heartfelt": [("empathy", 0.8), ("connection", 0.7)],
        "warm": [("contentment", 0.7), ("trust", 0.6)],
        "family": [("belonging", 0.8), ("connection", 0.7)],
        "community": [("belonging", 0.8), ("connection", 0.7)],
        "controversy": [("tension", 0.7), ("curiosity", 0.6)],
        "provocative": [("tension", 0.7), ("curiosity", 0.7)],
        "unfiltered": [("trust", 0.6), ("curiosity", 0.6)],
        "candid": [("trust", 0.7), ("curiosity", 0.6)],
        "horror": [("fear", 0.8), ("suspense", 0.8)],
        "dark": [("fear", 0.5), ("curiosity", 0.6)],
        "mystery": [("suspense", 0.8), ("curiosity", 0.8)],
        "true crime": [("suspense", 0.8), ("fear", 0.5), ("curiosity", 0.8)],
        "inspirational": [("inspiration", 0.9), ("admiration", 0.7)],
        "motivational": [("inspiration", 0.8), ("anticipation", 0.6)],
        "nostalgic": [("nostalgia", 0.9)],
        "throwback": [("nostalgia", 0.8), ("joy", 0.5)],
        "celebrity": [("curiosity", 0.7), ("admiration", 0.6)],
        "exclusive": [("anticipation", 0.7), ("curiosity", 0.7)],
        "breaking": [("anticipation", 0.8), ("curiosity", 0.8)],
        "relationship": [("empathy", 0.7), ("connection", 0.6)],
        "advice": [("trust", 0.7), ("curiosity", 0.5)],
        "mental health": [("empathy", 0.8), ("trust", 0.7)],
        "wellness": [("serenity", 0.6), ("inspiration", 0.5)],
        "sports": [("excitement", 0.8), ("anticipation", 0.7)],
        "political": [("outrage", 0.5), ("curiosity", 0.6)],
        "conservative": [("trust", 0.5), ("belonging", 0.5)],
        "progressive": [("curiosity", 0.6), ("inspiration", 0.5)],
    },
    # Show type to mindset mappings
    "show_type_mindsets": {
        "morning_show": [("commute_routine", 0.8), ("entertainment", 0.7), ("active_engagement", 0.6)],
        "countdown": [("entertainment", 0.8), ("anticipation", 0.7)],
        "talk_show": [("information_seeking", 0.7), ("active_engagement", 0.7)],
        "interview": [("curiosity", 0.8), ("learning", 0.6)],
        "advice": [("information_seeking", 0.8), ("emotional_processing", 0.6)],
        "rewatch": [("nostalgia", 0.8), ("entertainment", 0.7), ("social_connection", 0.6)],
        "educational": [("learning", 0.9), ("curiosity", 0.8)],
        "true_crime": [("entertainment", 0.7), ("curiosity", 0.9)],
        "comedy": [("entertainment", 0.9), ("relaxation", 0.6)],
        "sports": [("active_engagement", 0.8), ("entertainment", 0.7)],
        "news": [("information_seeking", 0.9), ("critical_thinking", 0.7)],
    },
}


# =============================================================================
# NEO4J DATABASE CLASS
# =============================================================================

class IHeartPsycholinguisticGraph:
    """
    Neo4j graph database for iHeartMedia psycholinguistic advertising optimization.
    
    This class handles:
    - Schema creation (constraints, indexes)
    - Data loading from iHeart catalog
    - Psycholinguistic taxonomy creation
    - Relationship inference and creation
    - Query utilities for ad targeting
    """
    
    def __init__(self, uri: str, username: str, password: str):
        """Initialize connection to Neo4j database."""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        logger.info(f"Connected to Neo4j at {uri}")
    
    def close(self):
        """Close the database connection."""
        self.driver.close()
        logger.info("Neo4j connection closed")
    
    def execute_query(self, query: str, parameters: dict = None) -> list:
        """Execute a Cypher query and return results."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return list(result)
    
    def execute_write(self, query: str, parameters: dict = None):
        """Execute a write query."""
        with self.driver.session() as session:
            session.run(query, parameters or {})
    
    # =========================================================================
    # SCHEMA CREATION
    # =========================================================================
    
    def create_schema(self):
        """Create all constraints and indexes for the graph."""
        logger.info("Creating schema constraints and indexes...")
        
        # Constraints for uniqueness
        constraints = [
            # Core content nodes
            "CREATE CONSTRAINT station_id IF NOT EXISTS FOR (s:Station) REQUIRE s.call_sign IS UNIQUE",
            "CREATE CONSTRAINT show_id IF NOT EXISTS FOR (s:Show) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT podcast_id IF NOT EXISTS FOR (p:Podcast) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT host_id IF NOT EXISTS FOR (h:Host) REQUIRE h.id IS UNIQUE",
            "CREATE CONSTRAINT segment_id IF NOT EXISTS FOR (s:Segment) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT market_id IF NOT EXISTS FOR (m:Market) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT format_id IF NOT EXISTS FOR (f:Format) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT podcast_network_id IF NOT EXISTS FOR (n:PodcastNetwork) REQUIRE n.name IS UNIQUE",
            
            # Psycholinguistic taxonomy nodes
            "CREATE CONSTRAINT emotional_state_id IF NOT EXISTS FOR (e:EmotionalState) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT mindset_id IF NOT EXISTS FOR (m:Mindset) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT behavioral_tendency_id IF NOT EXISTS FOR (b:BehavioralTendency) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT urge_id IF NOT EXISTS FOR (u:Urge) REQUIRE u.name IS UNIQUE",
            "CREATE CONSTRAINT personality_trait_id IF NOT EXISTS FOR (p:PersonalityTrait) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT cognitive_style_id IF NOT EXISTS FOR (c:CognitiveStyle) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT persuasion_technique_id IF NOT EXISTS FOR (p:PersuasionTechnique) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT time_slot_id IF NOT EXISTS FOR (t:TimeSlot) REQUIRE t.name IS UNIQUE",
        ]
        
        # Indexes for performance
        indexes = [
            # Full-text indexes for semantic search on descriptions
            "CREATE FULLTEXT INDEX station_description IF NOT EXISTS FOR (s:Station) ON EACH [s.description]",
            "CREATE FULLTEXT INDEX show_description IF NOT EXISTS FOR (s:Show) ON EACH [s.description]",
            "CREATE FULLTEXT INDEX podcast_description IF NOT EXISTS FOR (p:Podcast) ON EACH [p.description]",
            "CREATE FULLTEXT INDEX host_description IF NOT EXISTS FOR (h:Host) ON EACH [h.description]",
            "CREATE FULLTEXT INDEX segment_description IF NOT EXISTS FOR (s:Segment) ON EACH [s.description]",
            
            # Regular indexes for common queries
            "CREATE INDEX station_format IF NOT EXISTS FOR (s:Station) ON (s.format)",
            "CREATE INDEX station_market IF NOT EXISTS FOR (s:Station) ON (s.market)",
            "CREATE INDEX show_syndicated IF NOT EXISTS FOR (s:Show) ON (s.syndicated)",
            "CREATE INDEX show_air_time IF NOT EXISTS FOR (s:Show) ON (s.air_time_start)",
            "CREATE INDEX podcast_network IF NOT EXISTS FOR (p:Podcast) ON (p.network)",
            "CREATE INDEX emotional_state_category IF NOT EXISTS FOR (e:EmotionalState) ON (e.category)",
            "CREATE INDEX personality_trait_dimension IF NOT EXISTS FOR (p:PersonalityTrait) ON (p.dimension)",
        ]
        
        for constraint in constraints:
            try:
                self.execute_write(constraint)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Constraint creation warning: {e}")
        
        for index in indexes:
            try:
                self.execute_write(index)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Index creation warning: {e}")
        
        logger.info("Schema creation complete")
    
    # =========================================================================
    # PSYCHOLINGUISTIC TAXONOMY LOADING
    # =========================================================================
    
    def load_psycholinguistic_taxonomy(self):
        """Load all psycholinguistic taxonomy nodes."""
        logger.info("Loading psycholinguistic taxonomy...")
        
        # Emotional States
        for name, props in EMOTIONAL_STATES.items():
            query = """
            MERGE (e:EmotionalState {name: $name})
            SET e.valence = $valence,
                e.arousal = $arousal,
                e.category = $category,
                e.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "valence": props["valence"],
                "arousal": props["arousal"],
                "category": props["category"],
                "description": f"Emotional state: {name.replace('_', ' ').title()}"
            })
        
        # Mindsets
        for name, props in MINDSETS.items():
            query = """
            MERGE (m:Mindset {name: $name})
            SET m.openness = $openness,
                m.focus = $focus,
                m.receptivity = $receptivity,
                m.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "openness": props["openness"],
                "focus": props["focus"],
                "receptivity": props["receptivity"],
                "description": f"Cognitive mindset: {name.replace('_', ' ').title()}"
            })
        
        # Behavioral Tendencies
        for name, props in BEHAVIORAL_TENDENCIES.items():
            query = """
            MERGE (b:BehavioralTendency {name: $name})
            SET b += $props,
                b.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "props": props,
                "description": f"Behavioral tendency: {name.replace('_', ' ').title()}"
            })
        
        # Urges
        for name, props in URGES.items():
            query = """
            MERGE (u:Urge {name: $name})
            SET u += $props,
                u.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "props": props,
                "description": f"Action urge: {name.replace('_', ' ').title()}"
            })
        
        # Personality Traits
        for name, props in PERSONALITY_TRAITS.items():
            query = """
            MERGE (p:PersonalityTrait {name: $name})
            SET p.dimension = $dimension,
                p.level = $level,
                p.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "dimension": props["dimension"],
                "level": props["level"],
                "description": props["description"]
            })
        
        # Cognitive Styles
        for name, props in COGNITIVE_STYLES.items():
            query = """
            MERGE (c:CognitiveStyle {name: $name})
            SET c += $props,
                c.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "props": {k: v for k, v in props.items() if isinstance(v, (int, float, str))},
                "description": f"Cognitive style: {name.replace('_', ' ').title()}"
            })
        
        # Persuasion Techniques
        for name, props in PERSUASION_TECHNIQUES.items():
            query = """
            MERGE (p:PersuasionTechnique {name: $name})
            SET p.principle = $principle,
                p.effectiveness_context = $context,
                p.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "principle": props.get("principle", props.get("technique", "")),
                "context": props["effectiveness_context"],
                "description": f"Persuasion technique: {name.replace('_', ' ').title()}"
            })
        
        # Time Slots
        for name, props in TIME_SLOTS.items():
            query = """
            MERGE (t:TimeSlot {name: $name})
            SET t.hours = $hours,
                t.context = $context,
                t.attention_level = $attention,
                t.typical_mood = $mood,
                t.description = $description
            """
            self.execute_write(query, {
                "name": name,
                "hours": props["hours"],
                "context": props["context"],
                "attention": props["attention"],
                "mood": props["mood"],
                "description": f"Time slot: {name.replace('_', ' ').title()} ({props['hours']})"
            })
        
        logger.info("Psycholinguistic taxonomy loaded")
    
    # =========================================================================
    # IHEART DATA LOADING
    # =========================================================================
    
    def load_iheart_catalog(self, catalog_data: dict):
        """Load the complete iHeart catalog into the graph."""
        logger.info("Loading iHeart catalog...")
        
        # Load network metadata
        self._load_network_metadata(catalog_data.get("metadata", {}))
        
        # Load stations by format category
        for format_category, stations in catalog_data.get("stations", {}).items():
            self._load_stations(format_category, stations)
        
        # Load podcasts by category
        for podcast_category, podcasts in catalog_data.get("podcasts", {}).items():
            self._load_podcasts(podcast_category, podcasts)
        
        # Load annual events
        for event_name, event_data in catalog_data.get("annual_events", {}).items():
            self._load_event(event_name, event_data)
        
        logger.info("iHeart catalog loading complete")
    
    def _load_network_metadata(self, metadata: dict):
        """Load network-level metadata."""
        query = """
        MERGE (n:Network {name: 'iHeartMedia'})
        SET n.source = $source,
            n.last_updated = $last_updated,
            n.total_owned_stations = $total_stations,
            n.markets_served = $markets,
            n.monthly_reach = $reach,
            n.annual_revenue = $revenue,
            n.podcast_network_rank = $podcast_rank,
            n.total_podcasts = $total_podcasts,
            n.monthly_podcast_downloads = $downloads
        """
        self.execute_write(query, {
            "source": metadata.get("source", "iHeartRadio"),
            "last_updated": metadata.get("last_updated", ""),
            "total_stations": metadata.get("total_owned_stations", 0),
            "markets": metadata.get("markets_served", 0),
            "reach": metadata.get("monthly_reach", ""),
            "revenue": metadata.get("annual_revenue", ""),
            "podcast_rank": metadata.get("podcast_network_rank", ""),
            "total_podcasts": metadata.get("total_podcasts", 0),
            "downloads": metadata.get("monthly_podcast_downloads", ""),
        })
    
    def _load_stations(self, format_category: str, stations: list):
        """Load stations and their shows."""
        for station in stations:
            # Create Format node
            format_name = station.get("format", format_category.replace("_", " ").title())
            self.execute_write(
                "MERGE (f:Format {name: $name})",
                {"name": format_name}
            )
            
            # Create Market node
            market = station.get("market", "Unknown")
            self.execute_write(
                "MERGE (m:Market {name: $name})",
                {"name": market}
            )
            
            # Create Station node with full description
            station_query = """
            MERGE (s:Station {call_sign: $call_sign})
            SET s.brand_name = $brand_name,
                s.frequency = $frequency,
                s.market = $market,
                s.format = $format,
                s.format_category = $format_category,
                s.weekly_listeners = $weekly_listeners,
                s.annual_billing = $annual_billing,
                s.description = $description
            WITH s
            MATCH (f:Format {name: $format})
            MERGE (s)-[:HAS_FORMAT]->(f)
            WITH s
            MATCH (m:Market {name: $market})
            MERGE (s)-[:IN_MARKET]->(m)
            WITH s
            MATCH (n:Network {name: 'iHeartMedia'})
            MERGE (n)-[:OWNS]->(s)
            """
            self.execute_write(station_query, {
                "call_sign": station.get("call_sign", ""),
                "brand_name": station.get("brand_name", ""),
                "frequency": station.get("frequency", ""),
                "market": market,
                "format": format_name,
                "format_category": format_category,
                "weekly_listeners": station.get("weekly_listeners", ""),
                "annual_billing": station.get("annual_billing", ""),
                "description": station.get("station_description", ""),
            })
            
            # Load shows for this station
            for show in station.get("shows", []):
                self._load_show(station.get("call_sign"), show, format_name)
            
            # Create psycholinguistic relationships for station
            self._create_station_psycholinguistic_links(station.get("call_sign"), format_name, station.get("station_description", ""))
    
    def _load_show(self, station_call_sign: str, show: dict, station_format: str):
        """Load a show and its components."""
        show_id = f"{station_call_sign}_{show.get('name', '').replace(' ', '_')}"
        
        # Parse air time for time slot matching
        air_time = show.get("air_time", "")
        time_slot = self._parse_time_slot(air_time)
        
        # Create show node
        show_query = """
        MERGE (s:Show {id: $id})
        SET s.name = $name,
            s.air_time = $air_time,
            s.days = $days,
            s.syndicated = $syndicated,
            s.syndicated_stations = $syndicated_stations,
            s.weekly_listeners = $weekly_listeners,
            s.description = $description,
            s.station_format = $station_format
        WITH s
        MATCH (station:Station {call_sign: $station_call_sign})
        MERGE (station)-[:BROADCASTS]->(s)
        """
        self.execute_write(show_query, {
            "id": show_id,
            "name": show.get("name", ""),
            "air_time": air_time,
            "days": show.get("days", ""),
            "syndicated": show.get("syndicated", False),
            "syndicated_stations": show.get("syndicated_stations", 0),
            "weekly_listeners": show.get("weekly_listeners", ""),
            "description": show.get("show_description", ""),
            "station_call_sign": station_call_sign,
            "station_format": station_format,
        })
        
        # Link to time slot
        if time_slot:
            self.execute_write("""
                MATCH (s:Show {id: $show_id})
                MATCH (t:TimeSlot {name: $time_slot})
                MERGE (s)-[:AIRS_DURING]->(t)
            """, {"show_id": show_id, "time_slot": time_slot})
        
        # Load hosts
        hosts = []
        if show.get("host"):
            hosts.append(show["host"])
        hosts.extend(show.get("co_hosts", []))
        if show.get("hosts"):
            hosts.extend(show["hosts"])
        
        for host_name in hosts:
            if host_name:
                self._load_host(show_id, host_name, show.get("show_description", ""))
        
        # Load segments
        for segment in show.get("segments", []):
            self._load_segment(show_id, segment)
        
        # Load topics
        for topic in show.get("topics_covered", []):
            self._load_topic(show_id, topic)
        
        # Create psycholinguistic relationships
        self._create_show_psycholinguistic_links(
            show_id, 
            station_format, 
            show.get("show_description", ""),
            show.get("topics_covered", [])
        )
    
    def _load_host(self, show_id: str, host_name: str, show_description: str):
        """Load a host and link to show."""
        host_id = host_name.replace(" ", "_").replace(".", "").replace("'", "")
        
        query = """
        MERGE (h:Host {id: $id})
        SET h.name = $name
        WITH h
        MATCH (s:Show {id: $show_id})
        MERGE (s)-[:HOSTED_BY]->(h)
        """
        self.execute_write(query, {
            "id": host_id,
            "name": host_name,
            "show_id": show_id,
        })
    
    def _load_segment(self, show_id: str, segment: dict):
        """Load a segment and link to show."""
        segment_id = f"{show_id}_{segment.get('name', '').replace(' ', '_')}"
        
        query = """
        MERGE (seg:Segment {id: $id})
        SET seg.name = $name,
            seg.description = $description
        WITH seg
        MATCH (s:Show {id: $show_id})
        MERGE (s)-[:HAS_SEGMENT]->(seg)
        """
        self.execute_write(query, {
            "id": segment_id,
            "name": segment.get("name", ""),
            "description": segment.get("description", ""),
            "show_id": show_id,
        })
        
        # Create psycholinguistic links for segment
        self._create_segment_psycholinguistic_links(segment_id, segment.get("description", ""))
    
    def _load_topic(self, show_id: str, topic_name: str):
        """Load a topic and link to show."""
        # Normalize topic name
        normalized_topic = topic_name.lower().strip()
        
        query = """
        MERGE (t:Topic {name: $name})
        SET t.display_name = $display_name
        WITH t
        MATCH (s:Show {id: $show_id})
        MERGE (s)-[:COVERS_TOPIC]->(t)
        """
        self.execute_write(query, {
            "name": normalized_topic,
            "display_name": topic_name,
            "show_id": show_id,
        })
    
    def _load_podcasts(self, category: str, podcasts: list):
        """Load podcasts and their components."""
        for podcast in podcasts:
            podcast_id = podcast.get("name", "").replace(" ", "_").replace("'", "")
            network = podcast.get("network", "iHeartPodcasts")
            
            # Create PodcastNetwork node
            self.execute_write(
                "MERGE (n:PodcastNetwork {name: $name})",
                {"name": network}
            )
            
            # Create Podcast node
            podcast_query = """
            MERGE (p:Podcast {id: $id})
            SET p.name = $name,
                p.category = $category,
                p.network = $network,
                p.frequency = $frequency,
                p.episode_length = $episode_length,
                p.total_episodes = $total_episodes,
                p.total_downloads = $total_downloads,
                p.description = $description
            WITH p
            MATCH (n:PodcastNetwork {name: $network})
            MERGE (p)-[:PART_OF_NETWORK]->(n)
            """
            self.execute_write(podcast_query, {
                "id": podcast_id,
                "name": podcast.get("name", ""),
                "category": category,
                "network": network,
                "frequency": podcast.get("frequency", ""),
                "episode_length": podcast.get("episode_length", ""),
                "total_episodes": podcast.get("total_episodes", ""),
                "total_downloads": podcast.get("total_downloads", ""),
                "description": podcast.get("show_description", ""),
            })
            
            # Load hosts
            hosts = []
            if podcast.get("host"):
                hosts.append(podcast["host"])
            hosts.extend(podcast.get("hosts", []))
            hosts.extend(podcast.get("co_hosts", []))
            
            for host_name in hosts:
                if host_name:
                    host_id = host_name.replace(" ", "_").replace(".", "").replace("'", "").replace("(", "").replace(")", "")
                    self.execute_write("""
                        MERGE (h:Host {id: $id})
                        SET h.name = $name
                        WITH h
                        MATCH (p:Podcast {id: $podcast_id})
                        MERGE (p)-[:HOSTED_BY]->(h)
                    """, {"id": host_id, "name": host_name, "podcast_id": podcast_id})
            
            # Load topics
            for topic in podcast.get("topics_covered", []):
                normalized_topic = topic.lower().strip()
                self.execute_write("""
                    MERGE (t:Topic {name: $name})
                    SET t.display_name = $display_name
                    WITH t
                    MATCH (p:Podcast {id: $podcast_id})
                    MERGE (p)-[:COVERS_TOPIC]->(t)
                """, {"name": normalized_topic, "display_name": topic, "podcast_id": podcast_id})
            
            # Create psycholinguistic links
            self._create_podcast_psycholinguistic_links(
                podcast_id,
                category,
                podcast.get("show_description", ""),
                podcast.get("topics_covered", [])
            )
    
    def _load_event(self, event_name: str, event_data: dict):
        """Load an annual event."""
        query = """
        MERGE (e:Event {name: $name})
        SET e.display_name = $display_name,
            e.location = $location,
            e.month = $month,
            e.format = $format,
            e.broadcast = $broadcast,
            e.host = $host,
            e.description = $description
        """
        self.execute_write(query, {
            "name": event_name,
            "display_name": event_name.replace("_", " "),
            "location": event_data.get("location", "") if isinstance(event_data.get("location"), str) else ", ".join(event_data.get("locations", [])),
            "month": event_data.get("month", ""),
            "format": event_data.get("format", ""),
            "broadcast": event_data.get("broadcast", ""),
            "host": event_data.get("host", ""),
            "description": event_data.get("description", ""),
        })
    
    # =========================================================================
    # PSYCHOLINGUISTIC RELATIONSHIP CREATION
    # =========================================================================
    
    def _parse_time_slot(self, air_time: str) -> Optional[str]:
        """Parse air time string to determine time slot."""
        if not air_time:
            return None
        
        air_time_lower = air_time.lower()
        
        # Extract start hour
        hour_match = re.search(r'(\d{1,2}):\d{2}\s*(am|pm)', air_time_lower)
        if hour_match:
            hour = int(hour_match.group(1))
            am_pm = hour_match.group(2)
            
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
            
            # Map to time slots
            if 5 <= hour < 7:
                return "early_morning"
            elif 7 <= hour < 9:
                return "morning_drive"
            elif 9 <= hour < 12:
                return "late_morning"
            elif 12 <= hour < 14:
                return "midday"
            elif 14 <= hour < 17:
                return "afternoon"
            elif 17 <= hour < 19:
                return "evening_drive"
            elif 19 <= hour < 22:
                return "evening"
            elif 22 <= hour or hour < 1:
                return "late_night"
            else:
                return "overnight"
        
        # Check for weekend
        if "weekend" in air_time_lower or "saturday" in air_time_lower or "sunday" in air_time_lower:
            return "weekend_afternoon"
        
        return None
    
    def _extract_keywords_from_text(self, text: str) -> list:
        """Extract relevant keywords from description text."""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in CONTENT_PSYCHOLINGUISTIC_MAPPINGS["keywords_to_emotions"].keys():
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _detect_show_type(self, description: str, name: str) -> list:
        """Detect show type from description and name."""
        text = (description + " " + name).lower()
        detected_types = []
        
        type_keywords = {
            "morning_show": ["morning show", "morning", "wake up"],
            "countdown": ["countdown", "top 40", "top 30", "chart"],
            "talk_show": ["talk show", "talk radio", "discussion"],
            "interview": ["interview", "guest", "conversation with"],
            "advice": ["advice", "help", "counseling", "therapy"],
            "rewatch": ["rewatch", "revisit", "look back"],
            "educational": ["learn", "educational", "how", "explain", "science"],
            "true_crime": ["true crime", "murder", "crime", "investigation", "case"],
            "comedy": ["comedy", "laugh", "funny", "humor", "comedic"],
            "sports": ["sports", "nfl", "nba", "football", "basketball", "game"],
            "news": ["news", "political", "current events", "breaking"],
        }
        
        for show_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    detected_types.append(show_type)
                    break
        
        return detected_types if detected_types else ["entertainment"]
    
    def _create_station_psycholinguistic_links(self, call_sign: str, format_name: str, description: str):
        """Create psycholinguistic relationships for a station based on its format."""
        format_mappings = CONTENT_PSYCHOLINGUISTIC_MAPPINGS["formats"]
        
        # Find matching format
        matched_format = None
        for fmt_key in format_mappings.keys():
            if fmt_key.lower() in format_name.lower() or format_name.lower() in fmt_key.lower():
                matched_format = fmt_key
                break
        
        if not matched_format:
            return
        
        mappings = format_mappings[matched_format]
        
        # Create emotion links
        for emotion, intensity in mappings.get("emotions", []):
            self.execute_write("""
                MATCH (s:Station {call_sign: $call_sign})
                MATCH (e:EmotionalState {name: $emotion})
                MERGE (s)-[r:EVOKES_STATE]->(e)
                SET r.intensity = $intensity, r.source = 'format'
            """, {"call_sign": call_sign, "emotion": emotion, "intensity": intensity})
        
        # Create mindset links
        for mindset, strength in mappings.get("mindsets", []):
            self.execute_write("""
                MATCH (s:Station {call_sign: $call_sign})
                MATCH (m:Mindset {name: $mindset})
                MERGE (s)-[r:CREATES_MINDSET]->(m)
                SET r.strength = $strength, r.source = 'format'
            """, {"call_sign": call_sign, "mindset": mindset, "strength": strength})
        
        # Create behavior links
        for behavior, likelihood in mappings.get("behaviors", []):
            self.execute_write("""
                MATCH (s:Station {call_sign: $call_sign})
                MATCH (b:BehavioralTendency {name: $behavior})
                MERGE (s)-[r:TRIGGERS_BEHAVIOR]->(b)
                SET r.likelihood = $likelihood, r.source = 'format'
            """, {"call_sign": call_sign, "behavior": behavior, "likelihood": likelihood})
        
        # Create trait links
        for trait, correlation in mappings.get("traits", []):
            self.execute_write("""
                MATCH (s:Station {call_sign: $call_sign})
                MATCH (p:PersonalityTrait {name: $trait})
                MERGE (s)-[r:ATTRACTS_TRAIT]->(p)
                SET r.correlation = $correlation, r.source = 'format'
            """, {"call_sign": call_sign, "trait": trait, "correlation": correlation})
        
        # Create persuasion links
        for technique, effectiveness in mappings.get("persuasion", []):
            self.execute_write("""
                MATCH (s:Station {call_sign: $call_sign})
                MATCH (p:PersuasionTechnique {name: $technique})
                MERGE (s)-[r:RECEPTIVE_TO]->(p)
                SET r.effectiveness = $effectiveness, r.source = 'format'
            """, {"call_sign": call_sign, "technique": technique, "effectiveness": effectiveness})
    
    def _create_show_psycholinguistic_links(self, show_id: str, format_name: str, description: str, topics: list):
        """Create psycholinguistic relationships for a show."""
        # Inherit from format
        format_mappings = CONTENT_PSYCHOLINGUISTIC_MAPPINGS["formats"]
        matched_format = None
        for fmt_key in format_mappings.keys():
            if fmt_key.lower() in format_name.lower() or format_name.lower() in fmt_key.lower():
                matched_format = fmt_key
                break
        
        if matched_format:
            mappings = format_mappings[matched_format]
            
            # Create inherited links with slightly lower intensity
            for emotion, intensity in mappings.get("emotions", []):
                self.execute_write("""
                    MATCH (s:Show {id: $show_id})
                    MATCH (e:EmotionalState {name: $emotion})
                    MERGE (s)-[r:EVOKES_STATE]->(e)
                    SET r.intensity = $intensity, r.source = 'format_inheritance'
                """, {"show_id": show_id, "emotion": emotion, "intensity": intensity * 0.9})
            
            for mindset, strength in mappings.get("mindsets", []):
                self.execute_write("""
                    MATCH (s:Show {id: $show_id})
                    MATCH (m:Mindset {name: $mindset})
                    MERGE (s)-[r:CREATES_MINDSET]->(m)
                    SET r.strength = $strength, r.source = 'format_inheritance'
                """, {"show_id": show_id, "mindset": mindset, "strength": strength * 0.9})
            
            for behavior, likelihood in mappings.get("behaviors", []):
                self.execute_write("""
                    MATCH (s:Show {id: $show_id})
                    MATCH (b:BehavioralTendency {name: $behavior})
                    MERGE (s)-[r:TRIGGERS_BEHAVIOR]->(b)
                    SET r.likelihood = $likelihood, r.source = 'format_inheritance'
                """, {"show_id": show_id, "behavior": behavior, "likelihood": likelihood * 0.9})
            
            for trait, correlation in mappings.get("traits", []):
                self.execute_write("""
                    MATCH (s:Show {id: $show_id})
                    MATCH (p:PersonalityTrait {name: $trait})
                    MERGE (s)-[r:ATTRACTS_TRAIT]->(p)
                    SET r.correlation = $correlation, r.source = 'format_inheritance'
                """, {"show_id": show_id, "trait": trait, "correlation": correlation * 0.9})
            
            for technique, effectiveness in mappings.get("persuasion", []):
                self.execute_write("""
                    MATCH (s:Show {id: $show_id})
                    MATCH (p:PersuasionTechnique {name: $technique})
                    MERGE (s)-[r:RECEPTIVE_TO]->(p)
                    SET r.effectiveness = $effectiveness, r.source = 'format_inheritance'
                """, {"show_id": show_id, "technique": technique, "effectiveness": effectiveness * 0.9})
        
        # Extract emotions from description keywords
        keywords = self._extract_keywords_from_text(description)
        keyword_mappings = CONTENT_PSYCHOLINGUISTIC_MAPPINGS["keywords_to_emotions"]
        
        for keyword in keywords:
            if keyword in keyword_mappings:
                for emotion, intensity in keyword_mappings[keyword]:
                    self.execute_write("""
                        MATCH (s:Show {id: $show_id})
                        MATCH (e:EmotionalState {name: $emotion})
                        MERGE (s)-[r:EVOKES_STATE]->(e)
                        ON CREATE SET r.intensity = $intensity, r.source = 'keyword_extraction'
                        ON MATCH SET r.intensity = CASE WHEN r.intensity < $intensity THEN $intensity ELSE r.intensity END
                    """, {"show_id": show_id, "emotion": emotion, "intensity": intensity})
        
        # Detect show type and add mindset links
        show_types = self._detect_show_type(description, show_id)
        show_type_mappings = CONTENT_PSYCHOLINGUISTIC_MAPPINGS["show_type_mindsets"]
        
        for show_type in show_types:
            if show_type in show_type_mappings:
                for mindset, strength in show_type_mappings[show_type]:
                    self.execute_write("""
                        MATCH (s:Show {id: $show_id})
                        MATCH (m:Mindset {name: $mindset})
                        MERGE (s)-[r:CREATES_MINDSET]->(m)
                        ON CREATE SET r.strength = $strength, r.source = 'show_type_detection'
                        ON MATCH SET r.strength = CASE WHEN r.strength < $strength THEN $strength ELSE r.strength END
                    """, {"show_id": show_id, "mindset": mindset, "strength": strength})
    
    def _create_segment_psycholinguistic_links(self, segment_id: str, description: str):
        """Create psycholinguistic relationships for a segment."""
        keywords = self._extract_keywords_from_text(description)
        keyword_mappings = CONTENT_PSYCHOLINGUISTIC_MAPPINGS["keywords_to_emotions"]
        
        for keyword in keywords:
            if keyword in keyword_mappings:
                for emotion, intensity in keyword_mappings[keyword]:
                    self.execute_write("""
                        MATCH (seg:Segment {id: $segment_id})
                        MATCH (e:EmotionalState {name: $emotion})
                        MERGE (seg)-[r:EVOKES_STATE]->(e)
                        SET r.intensity = $intensity, r.source = 'keyword_extraction'
                    """, {"segment_id": segment_id, "emotion": emotion, "intensity": intensity})
    
    def _create_podcast_psycholinguistic_links(self, podcast_id: str, category: str, description: str, topics: list):
        """Create psycholinguistic relationships for a podcast based on its category."""
        # Category-based mappings
        category_mappings = {
            "howstuffworks_educational": {
                "emotions": [("curiosity", 0.9), ("amusement", 0.6)],
                "mindsets": [("learning", 0.9), ("curiosity", 0.8)],
                "behaviors": [("information_gathering", 0.9), ("social_sharing", 0.6)],
                "traits": [("need_for_cognition", 0.9), ("openness_high", 0.8)],
                "persuasion": [("authority", 0.8), ("rational_argument", 0.9)],
            },
            "grim_and_mild": {
                "emotions": [("fear", 0.7), ("curiosity", 0.9), ("suspense", 0.8)],
                "mindsets": [("entertainment", 0.8), ("curiosity", 0.9)],
                "behaviors": [("experience_seeking", 0.8), ("information_gathering", 0.7)],
                "traits": [("openness_high", 0.8), ("sensation_seeking", 0.7)],
                "persuasion": [("storytelling", 0.9), ("fear_appeal", 0.6)],
            },
            "true_crime": {
                "emotions": [("suspense", 0.9), ("fear", 0.6), ("curiosity", 0.9)],
                "mindsets": [("entertainment", 0.8), ("information_seeking", 0.7)],
                "behaviors": [("information_gathering", 0.8), ("social_sharing", 0.7)],
                "traits": [("sensation_seeking", 0.7), ("need_for_cognition", 0.6)],
                "persuasion": [("storytelling", 0.9), ("social_proof", 0.6)],
            },
            "cool_zone_media": {
                "emotions": [("outrage", 0.7), ("curiosity", 0.8), ("amusement", 0.6)],
                "mindsets": [("critical_thinking", 0.9), ("information_seeking", 0.8)],
                "behaviors": [("opinion_leadership", 0.7), ("information_gathering", 0.9)],
                "traits": [("need_for_cognition", 0.9), ("openness_high", 0.8)],
                "persuasion": [("authority", 0.7), ("rational_argument", 0.8)],
            },
            "comedy": {
                "emotions": [("amusement", 0.9), ("joy", 0.8)],
                "mindsets": [("entertainment", 0.9), ("relaxation", 0.7)],
                "behaviors": [("social_sharing", 0.8), ("variety_seeking", 0.6)],
                "traits": [("extraversion_high", 0.6), ("openness_high", 0.7)],
                "persuasion": [("humor", 0.9), ("liking", 0.8)],
            },
            "black_effect_network": {
                "emotions": [("connection", 0.8), ("belonging", 0.8), ("amusement", 0.7)],
                "mindsets": [("identity_affirmation", 0.9), ("social_connection", 0.8)],
                "behaviors": [("opinion_leadership", 0.7), ("social_sharing", 0.8)],
                "traits": [("extraversion_high", 0.7), ("self_monitoring", 0.6)],
                "persuasion": [("unity", 0.9), ("social_proof", 0.8), ("liking", 0.7)],
            },
            "celebrity_hosted": {
                "emotions": [("curiosity", 0.8), ("admiration", 0.7), ("connection", 0.6)],
                "mindsets": [("entertainment", 0.8), ("social_connection", 0.7)],
                "behaviors": [("social_sharing", 0.7), ("brand_loyalty", 0.6)],
                "traits": [("extraversion_high", 0.6), ("need_for_affect", 0.7)],
                "persuasion": [("liking", 0.9), ("authority", 0.7)],
            },
            "pushkin_partnership": {
                "emotions": [("curiosity", 0.9), ("inspiration", 0.7)],
                "mindsets": [("learning", 0.9), ("critical_thinking", 0.8)],
                "behaviors": [("information_gathering", 0.9), ("deliberate_consideration", 0.7)],
                "traits": [("need_for_cognition", 0.9), ("openness_high", 0.8)],
                "persuasion": [("authority", 0.9), ("rational_argument", 0.9), ("storytelling", 0.8)],
            },
            "sports": {
                "emotions": [("excitement", 0.9), ("anticipation", 0.8), ("connection", 0.7)],
                "mindsets": [("active_engagement", 0.8), ("entertainment", 0.8)],
                "behaviors": [("brand_loyalty", 0.8), ("social_sharing", 0.7)],
                "traits": [("extraversion_high", 0.7), ("sensation_seeking", 0.6)],
                "persuasion": [("social_proof", 0.8), ("unity", 0.8)],
            },
            "news_politics": {
                "emotions": [("outrage", 0.6), ("curiosity", 0.7), ("trust", 0.5)],
                "mindsets": [("information_seeking", 0.9), ("critical_thinking", 0.8)],
                "behaviors": [("information_gathering", 0.9), ("opinion_leadership", 0.7)],
                "traits": [("need_for_cognition", 0.8), ("conscientiousness_high", 0.6)],
                "persuasion": [("authority", 0.8), ("rational_argument", 0.7), ("fear_appeal", 0.5)],
            },
        }
        
        mappings = category_mappings.get(category, {})
        
        # Create emotion links
        for emotion, intensity in mappings.get("emotions", []):
            self.execute_write("""
                MATCH (p:Podcast {id: $podcast_id})
                MATCH (e:EmotionalState {name: $emotion})
                MERGE (p)-[r:EVOKES_STATE]->(e)
                SET r.intensity = $intensity, r.source = 'category'
            """, {"podcast_id": podcast_id, "emotion": emotion, "intensity": intensity})
        
        # Create mindset links
        for mindset, strength in mappings.get("mindsets", []):
            self.execute_write("""
                MATCH (p:Podcast {id: $podcast_id})
                MATCH (m:Mindset {name: $mindset})
                MERGE (p)-[r:CREATES_MINDSET]->(m)
                SET r.strength = $strength, r.source = 'category'
            """, {"podcast_id": podcast_id, "mindset": mindset, "strength": strength})
        
        # Create behavior links
        for behavior, likelihood in mappings.get("behaviors", []):
            self.execute_write("""
                MATCH (p:Podcast {id: $podcast_id})
                MATCH (b:BehavioralTendency {name: $behavior})
                MERGE (p)-[r:TRIGGERS_BEHAVIOR]->(b)
                SET r.likelihood = $likelihood, r.source = 'category'
            """, {"podcast_id": podcast_id, "behavior": behavior, "likelihood": likelihood})
        
        # Create trait links
        for trait, correlation in mappings.get("traits", []):
            self.execute_write("""
                MATCH (p:Podcast {id: $podcast_id})
                MATCH (t:PersonalityTrait {name: $trait})
                MERGE (p)-[r:ATTRACTS_TRAIT]->(t)
                SET r.correlation = $correlation, r.source = 'category'
            """, {"podcast_id": podcast_id, "trait": trait, "correlation": correlation})
        
        # Create persuasion links
        for technique, effectiveness in mappings.get("persuasion", []):
            self.execute_write("""
                MATCH (p:Podcast {id: $podcast_id})
                MATCH (pt:PersuasionTechnique {name: $technique})
                MERGE (p)-[r:RECEPTIVE_TO]->(pt)
                SET r.effectiveness = $effectiveness, r.source = 'category'
            """, {"podcast_id": podcast_id, "technique": technique, "effectiveness": effectiveness})
        
        # Extract additional emotions from description
        keywords = self._extract_keywords_from_text(description)
        keyword_mappings = CONTENT_PSYCHOLINGUISTIC_MAPPINGS["keywords_to_emotions"]
        
        for keyword in keywords:
            if keyword in keyword_mappings:
                for emotion, intensity in keyword_mappings[keyword]:
                    self.execute_write("""
                        MATCH (p:Podcast {id: $podcast_id})
                        MATCH (e:EmotionalState {name: $emotion})
                        MERGE (p)-[r:EVOKES_STATE]->(e)
                        ON CREATE SET r.intensity = $intensity, r.source = 'keyword_extraction'
                        ON MATCH SET r.intensity = CASE WHEN r.intensity < $intensity THEN $intensity ELSE r.intensity END
                    """, {"podcast_id": podcast_id, "emotion": emotion, "intensity": intensity})


# =============================================================================
# EXAMPLE QUERIES FOR AD TARGETING
# =============================================================================

EXAMPLE_QUERIES = """
-- =============================================================================
-- EXAMPLE CYPHER QUERIES FOR PSYCHOLINGUISTIC AD TARGETING
-- =============================================================================

-- 1. Find shows that evoke excitement and reach extraversion-high personality
-- (Good for high-energy product ads like energy drinks, entertainment)
MATCH (s:Show)-[ev:EVOKES_STATE]->(e:EmotionalState {name: 'excitement'})
MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait {name: 'extraversion_high'})
WHERE ev.intensity > 0.7 AND at.correlation > 0.6
RETURN s.name AS show, s.description AS description,
       ev.intensity AS excitement_intensity,
       at.correlation AS extraversion_correlation
ORDER BY ev.intensity * at.correlation DESC
LIMIT 10;

-- 2. Find optimal time slots for nostalgia-based advertising
-- (Good for heritage brands, reunion services, classic products)
MATCH (s:Show)-[r:EVOKES_STATE]->(e:EmotionalState {name: 'nostalgia'})
MATCH (s)-[:AIRS_DURING]->(t:TimeSlot)
WHERE r.intensity > 0.6
RETURN t.name AS time_slot, t.hours AS hours, t.typical_mood AS mood,
       COUNT(s) AS show_count,
       AVG(r.intensity) AS avg_nostalgia_intensity
ORDER BY avg_nostalgia_intensity DESC;

-- 3. Match products to shows based on persuasion technique effectiveness
-- (Find shows receptive to scarcity/urgency messaging)
MATCH (content)-[r:RECEPTIVE_TO]->(p:PersuasionTechnique {name: 'scarcity'})
WHERE r.effectiveness > 0.6
OPTIONAL MATCH (content)-[:EVOKES_STATE]->(e:EmotionalState)
WITH content, r.effectiveness AS scarcity_effectiveness,
     COLLECT(DISTINCT e.name) AS evoked_emotions
RETURN labels(content)[0] AS content_type,
       content.name AS name,
       scarcity_effectiveness,
       evoked_emotions
ORDER BY scarcity_effectiveness DESC
LIMIT 15;

-- 4. Find shows for high-consideration products (need for cognition audience)
-- (Good for financial services, tech products, insurance)
MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait {name: 'need_for_cognition'})
MATCH (s)-[cm:CREATES_MINDSET]->(m:Mindset)
WHERE at.correlation > 0.7 AND cm.strength > 0.6
AND m.name IN ['learning', 'information_seeking', 'critical_thinking']
RETURN s.name AS content,
       labels(s)[0] AS type,
       at.correlation AS cognition_correlation,
       COLLECT(m.name) AS mindsets
ORDER BY at.correlation DESC
LIMIT 20;

-- 5. Find emotional journey opportunities (shows with multiple emotional states)
-- (Good for complex emotional appeals, story-driven ads)
MATCH (s:Show)-[r:EVOKES_STATE]->(e:EmotionalState)
WITH s, COLLECT({emotion: e.name, intensity: r.intensity, category: e.category}) AS emotions
WHERE SIZE(emotions) >= 3
RETURN s.name AS show,
       s.description AS description,
       [em IN emotions | em.emotion + ': ' + toString(em.intensity)] AS emotional_profile,
       SIZE(emotions) AS emotional_complexity
ORDER BY emotional_complexity DESC
LIMIT 10;

-- 6. Audience profile matching - find shows for specific psychographic segment
-- (Example: Young, socially-connected early adopters)
MATCH (s)-[t1:ATTRACTS_TRAIT]->(p1:PersonalityTrait {name: 'extraversion_high'})
MATCH (s)-[t2:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency {name: 'early_adoption'})
MATCH (s)-[t3:TRIGGERS_BEHAVIOR]->(b2:BehavioralTendency {name: 'social_sharing'})
WHERE t1.correlation > 0.5 AND t2.likelihood > 0.5 AND t3.likelihood > 0.5
RETURN s.name AS content,
       labels(s)[0] AS type,
       t1.correlation AS extraversion,
       t2.likelihood AS early_adoption,
       t3.likelihood AS social_sharing
ORDER BY t1.correlation + t2.likelihood + t3.likelihood DESC
LIMIT 15;

-- 7. Find cross-promotion opportunities (shows with similar psycholinguistic profiles)
MATCH (s1:Show)-[r1:EVOKES_STATE]->(e:EmotionalState)<-[r2:EVOKES_STATE]-(s2:Show)
WHERE s1.id < s2.id
WITH s1, s2, COLLECT({emotion: e.name, int1: r1.intensity, int2: r2.intensity}) AS shared_emotions
WHERE SIZE(shared_emotions) >= 2
MATCH (s1)-[:ATTRACTS_TRAIT]->(p:PersonalityTrait)<-[:ATTRACTS_TRAIT]-(s2)
WITH s1, s2, shared_emotions, COLLECT(p.name) AS shared_traits
WHERE SIZE(shared_traits) >= 1
RETURN s1.name AS show1, s2.name AS show2,
       [se IN shared_emotions | se.emotion] AS common_emotions,
       shared_traits AS common_traits
LIMIT 20;

-- 8. Optimal ad timing - combine time slot mood with show emotional state
MATCH (s:Show)-[:AIRS_DURING]->(t:TimeSlot)
MATCH (s)-[r:EVOKES_STATE]->(e:EmotionalState)
WHERE e.category = 'positive_high' AND r.intensity > 0.7
RETURN t.name AS time_slot, t.hours AS hours,
       t.attention_level AS attention,
       COLLECT(DISTINCT s.name) AS high_energy_shows,
       COUNT(s) AS show_count
ORDER BY t.attention_level DESC;

-- 9. Content-to-urge mapping for conversion optimization
MATCH (content)-[r:EVOKES_STATE]->(e:EmotionalState)
WHERE e.valence > 0.5 AND e.arousal > 0.6
MATCH (content)-[:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency {name: 'impulsive_action'})
RETURN content.name AS content,
       labels(content)[0] AS type,
       e.name AS emotion,
       e.valence AS valence,
       e.arousal AS arousal,
       'High conversion potential' AS recommendation
ORDER BY e.arousal * e.valence DESC
LIMIT 15;

-- 10. Full psycholinguistic profile for a specific show
MATCH (s:Show {name: 'The Bobby Bones Show'})
OPTIONAL MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState)
OPTIONAL MATCH (s)-[cm:CREATES_MINDSET]->(m:Mindset)
OPTIONAL MATCH (s)-[tb:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency)
OPTIONAL MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
OPTIONAL MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique)
OPTIONAL MATCH (s)-[:AIRS_DURING]->(t:TimeSlot)
OPTIONAL MATCH (s)-[:COVERS_TOPIC]->(topic:Topic)
RETURN s.name AS show_name,
       s.description AS description,
       COLLECT(DISTINCT {state: e.name, intensity: ev.intensity}) AS emotional_states,
       COLLECT(DISTINCT {mindset: m.name, strength: cm.strength}) AS mindsets,
       COLLECT(DISTINCT {behavior: b.name, likelihood: tb.likelihood}) AS behaviors,
       COLLECT(DISTINCT {trait: p.name, correlation: at.correlation}) AS personality_traits,
       COLLECT(DISTINCT {technique: pt.name, effectiveness: rt.effectiveness}) AS persuasion_receptivity,
       COLLECT(DISTINCT t.name) AS time_slots,
       COLLECT(DISTINCT topic.display_name) AS topics;

-- 11. Aggregate emotional intensity by format for media planning
MATCH (station:Station)-[:HAS_FORMAT]->(f:Format)
MATCH (station)-[:BROADCASTS]->(s:Show)-[r:EVOKES_STATE]->(e:EmotionalState)
WITH f.name AS format, e.category AS emotion_category,
     AVG(r.intensity) AS avg_intensity,
     COUNT(DISTINCT s) AS show_count
RETURN format, emotion_category, avg_intensity, show_count
ORDER BY format, avg_intensity DESC;

-- 12. Find podcast networks optimal for specific brand personality
-- (Example: Brand wants to reach analytical, high-cognition audiences)
MATCH (p:Podcast)-[:PART_OF_NETWORK]->(n:PodcastNetwork)
MATCH (p)-[at:ATTRACTS_TRAIT]->(t:PersonalityTrait)
WHERE t.name IN ['need_for_cognition', 'conscientiousness_high', 'openness_high']
WITH n.name AS network, COLLECT(DISTINCT p.name) AS podcasts,
     AVG(at.correlation) AS avg_trait_match,
     COUNT(DISTINCT p) AS podcast_count
WHERE podcast_count >= 2
RETURN network, podcast_count, avg_trait_match,
       podcasts[0..5] AS sample_podcasts
ORDER BY avg_trait_match DESC;

-- 13. Semantic search preparation - get all descriptions for vector embedding
MATCH (s:Show)
RETURN 'show' AS type, s.id AS id, s.name AS name, s.description AS description
UNION
MATCH (p:Podcast)
RETURN 'podcast' AS type, p.id AS id, p.name AS name, p.description AS description
UNION
MATCH (station:Station)
RETURN 'station' AS type, station.call_sign AS id, station.brand_name AS name, station.description AS description;
"""


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='Load iHeartMedia catalog into Neo4j with psycholinguistic modeling'
    )
    parser.add_argument('--uri', default='bolt://localhost:7687',
                        help='Neo4j URI (default: bolt://localhost:7687)')
    parser.add_argument('--username', default='neo4j',
                        help='Neo4j username (default: neo4j)')
    parser.add_argument('--password', default=None,
                        help='Neo4j password (required unless --queries-only)')
    parser.add_argument('--catalog', default='iheart_complete_catalog.json',
                        help='Path to iHeart catalog JSON file')
    parser.add_argument('--clear', action='store_true',
                        help='Clear existing data before loading')
    parser.add_argument('--queries-only', action='store_true',
                        help='Only print example queries, do not load data')
    
    args = parser.parse_args()
    
    if args.queries_only:
        print(EXAMPLE_QUERIES)
        return
    
    # Password is required for database operations
    if not args.password:
        print("Error: --password is required for database operations")
        print("Use --queries-only to view example queries without connecting to Neo4j")
        sys.exit(1)
    
    # Load catalog data
    logger.info(f"Loading catalog from {args.catalog}")
    with open(args.catalog, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)
    
    # Initialize graph
    graph = IHeartPsycholinguisticGraph(args.uri, args.username, args.password)
    
    try:
        # Clear existing data if requested
        if args.clear:
            logger.info("Clearing existing data...")
            graph.execute_write("MATCH (n) DETACH DELETE n")
        
        # Create schema
        graph.create_schema()
        
        # Load psycholinguistic taxonomy
        graph.load_psycholinguistic_taxonomy()
        
        # Load iHeart catalog
        graph.load_iheart_catalog(catalog_data)
        
        # Print statistics
        stats_query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, COUNT(n) AS count
        ORDER BY count DESC
        """
        results = graph.execute_query(stats_query)
        
        print("\n" + "="*60)
        print("GRAPH DATABASE STATISTICS")
        print("="*60)
        for record in results:
            print(f"  {record['label']}: {record['count']}")
        
        # Print relationship counts
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS relationship, COUNT(r) AS count
        ORDER BY count DESC
        """
        rel_results = graph.execute_query(rel_query)
        
        print("\nRelationship counts:")
        for record in rel_results:
            print(f"  {record['relationship']}: {record['count']}")
        
        print("\n" + "="*60)
        print("GRAPH DATABASE READY FOR AD TARGETING")
        print("="*60)
        print("\nRun with --queries-only to see example Cypher queries")
        
    finally:
        graph.close()


if __name__ == "__main__":
    main()
