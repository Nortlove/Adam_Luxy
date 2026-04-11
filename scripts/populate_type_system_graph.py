#!/usr/bin/env python3
"""
Materialize the full 1.9M+ expanded psychological type system into Neo4j.

Usage:
    python scripts/populate_type_system_graph.py [--phase N] [--uri URI] [--password PWD]

    --phase: Run only phase N (1-5). Default: all phases.
    --batch-size: Batch size for type node creation (default: 5000)
    --dry-run: Print counts without writing to Neo4j

Phases:
    1: Create constraints/indexes + dimension value nodes + appeal nodes
    2: Create 1,920,960 GranularType nodes + dimension edges
    3: Create alignment edges (SUSCEPTIBLE_TO, ALIGNS_WITH_VALUE, etc.)
    4: Create product characteristic nodes and edges
    5: Calibrate alignment edges with corpus data (937M reviews)

Run with nohup for production:
    nohup python3 scripts/populate_type_system_graph.py >> data/type_system_build.log 2>&1 &
"""

import argparse
import itertools
import json
import logging
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("type_system_graph")

# ---------------------------------------------------------------------------
# 7 Type Dimensions (from empirical_psychology_framework.py)
# ---------------------------------------------------------------------------

MOTIVATIONS = [
    "pure_curiosity", "mastery_seeking", "self_expression", "flow_experience",
    "personal_growth", "values_alignment", "goal_achievement", "role_fulfillment",
    "future_self_investment", "guilt_avoidance", "ego_protection",
    "self_esteem_enhancement", "anxiety_reduction", "social_compliance",
    "reward_seeking", "punishment_avoidance", "authority_compliance",
    "sensory_pleasure", "excitement_seeking", "nostalgia_comfort", "escapism",
    "social_enjoyment", "problem_solving", "efficiency_optimization",
    "cost_minimization", "quality_assurance", "risk_mitigation",
    "status_signaling", "belonging_affirmation", "uniqueness_differentiation",
    "social_approval", "altruistic_giving", "relationship_maintenance",
    "immediate_gratification", "delayed_gratification", "scarcity_response",
    "opportunity_cost_awareness",
]

DECISION_STYLES = [
    "gut_instinct", "recognition_based", "affect_driven", "satisficing",
    "heuristic_based", "social_referencing", "authority_deferring", "maximizing",
    "analytical_systematic", "risk_calculating", "deliberative_reflective",
    "consensus_building",
]

REGULATORY_FOCUS = [
    "eager_advancement", "aspiration_driven", "optimistic_exploration",
    "pragmatic_balanced", "situational_adaptive", "vigilant_security",
    "conservative_preservation", "anxious_avoidance",
]

EMOTIONAL_INTENSITY = [
    "high_positive_activation", "high_negative_activation", "mixed_high_arousal",
    "moderate_positive", "moderate_negative", "emotionally_neutral",
    "low_positive_calm", "low_negative_sad", "apathetic_disengaged",
]

COGNITIVE_LOAD = [
    "minimal_cognitive", "moderate_cognitive", "high_cognitive",
]

TEMPORAL_ORIENTATION = [
    "immediate_present", "short_term", "medium_term", "long_term_future",
]

SOCIAL_INFLUENCE = [
    "highly_independent", "informational_seeker", "socially_aware",
    "normatively_driven", "opinion_leader",
]

TOTAL_TYPES = (
    len(MOTIVATIONS) * len(DECISION_STYLES) * len(REGULATORY_FOCUS)
    * len(EMOTIONAL_INTENSITY) * len(COGNITIVE_LOAD)
    * len(TEMPORAL_ORIENTATION) * len(SOCIAL_INFLUENCE)
)

# ---------------------------------------------------------------------------
# Appeal Dimensions (from customer_ad_alignment.py)
# ---------------------------------------------------------------------------

VALUE_PROPOSITIONS = [
    "pleasure_enjoyment", "convenience_ease", "novelty_innovation",
    "knowledge_expertise", "performance_superiority", "transformation",
    "self_expression", "social_responsibility", "reliability_durability",
    "peace_of_mind", "status_prestige", "belonging_connection", "cost_efficiency",
]

LINGUISTIC_STYLES = [
    "emotional", "urgent", "minimalist", "conversational",
    "storytelling", "professional", "technical",
]

EMOTIONAL_APPEALS = [
    "excitement", "pride", "anticipation", "joy", "empowerment",
    "surprise", "contentment", "trust", "fear", "anxiety", "nostalgia",
]

PERSUASION_MECHANISMS = [
    "scarcity", "liking", "social_proof", "authority",
    "reciprocity", "commitment", "unity",
]

PERSUASION_TECHNIQUES = [
    "authority_expertise", "scarcity_exclusivity", "social_proof_numbers",
    "bandwagon", "authority_credentials", "social_proof_expert",
    "social_proof_similarity", "social_proof_testimonials",
    "unity_shared_identity", "novelty_innovation",
]

# ---------------------------------------------------------------------------
# Alignment Matrices (from customer_ad_alignment.py)
# ---------------------------------------------------------------------------

MOTIVATION_VALUE_ALIGNMENT = {
    "pure_curiosity": {"novelty_innovation": 0.9, "knowledge_expertise": 0.85},
    "mastery_seeking": {"knowledge_expertise": 0.95, "performance_superiority": 0.85, "transformation": 0.7},
    "self_expression": {"self_expression": 0.95, "novelty_innovation": 0.8, "status_prestige": 0.7},
    "flow_experience": {"pleasure_enjoyment": 0.9, "novelty_innovation": 0.8},
    "personal_growth": {"transformation": 0.95, "knowledge_expertise": 0.85, "self_expression": 0.7},
    "values_alignment": {"social_responsibility": 0.95, "reliability_durability": 0.7},
    "goal_achievement": {"transformation": 0.9, "performance_superiority": 0.85},
    "role_fulfillment": {"reliability_durability": 0.8, "peace_of_mind": 0.75},
    "future_self_investment": {"transformation": 0.9, "knowledge_expertise": 0.8, "reliability_durability": 0.7},
    "guilt_avoidance": {"social_responsibility": 0.8, "peace_of_mind": 0.75},
    "ego_protection": {"status_prestige": 0.9, "performance_superiority": 0.8},
    "self_esteem_enhancement": {"self_expression": 0.85, "pleasure_enjoyment": 0.8, "status_prestige": 0.7},
    "anxiety_reduction": {"peace_of_mind": 0.95, "reliability_durability": 0.85},
    "social_compliance": {"belonging_connection": 0.9, "status_prestige": 0.7},
    "reward_seeking": {"cost_efficiency": 0.9, "pleasure_enjoyment": 0.7},
    "punishment_avoidance": {"peace_of_mind": 0.85, "reliability_durability": 0.8},
    "authority_compliance": {"knowledge_expertise": 0.8, "reliability_durability": 0.75},
    "sensory_pleasure": {"pleasure_enjoyment": 0.95, "self_expression": 0.7},
    "excitement_seeking": {"novelty_innovation": 0.95, "pleasure_enjoyment": 0.85},
    "nostalgia_comfort": {"belonging_connection": 0.8, "peace_of_mind": 0.75},
    "escapism": {"pleasure_enjoyment": 0.9, "transformation": 0.7},
    "social_enjoyment": {"belonging_connection": 0.9, "pleasure_enjoyment": 0.8},
    "problem_solving": {"performance_superiority": 0.9, "convenience_ease": 0.85, "cost_efficiency": 0.7},
    "efficiency_optimization": {"convenience_ease": 0.95, "performance_superiority": 0.8, "cost_efficiency": 0.75},
    "cost_minimization": {"cost_efficiency": 0.95, "convenience_ease": 0.7},
    "quality_assurance": {"reliability_durability": 0.95, "performance_superiority": 0.85},
    "risk_mitigation": {"peace_of_mind": 0.95, "reliability_durability": 0.9},
    "status_signaling": {"status_prestige": 0.95, "self_expression": 0.8},
    "belonging_affirmation": {"belonging_connection": 0.95, "social_responsibility": 0.7},
    "uniqueness_differentiation": {"self_expression": 0.95, "novelty_innovation": 0.85, "status_prestige": 0.7},
    "social_approval": {"belonging_connection": 0.85, "status_prestige": 0.8},
    "altruistic_giving": {"social_responsibility": 0.95, "belonging_connection": 0.7},
    "relationship_maintenance": {"belonging_connection": 0.9, "peace_of_mind": 0.7},
    "immediate_gratification": {"pleasure_enjoyment": 0.95, "convenience_ease": 0.85, "novelty_innovation": 0.7},
    "delayed_gratification": {"reliability_durability": 0.85, "transformation": 0.8, "knowledge_expertise": 0.7},
    "scarcity_response": {"cost_efficiency": 0.85, "convenience_ease": 0.7, "novelty_innovation": 0.65},
    "opportunity_cost_awareness": {"cost_efficiency": 0.9, "performance_superiority": 0.75, "reliability_durability": 0.7},
}

DECISION_STYLE_LINGUISTIC_ALIGNMENT = {
    "gut_instinct": {"emotional": 0.9, "urgent": 0.85, "minimalist": 0.8},
    "recognition_based": {"conversational": 0.85, "minimalist": 0.8},
    "affect_driven": {"emotional": 0.95, "storytelling": 0.8},
    "satisficing": {"conversational": 0.85, "minimalist": 0.8},
    "heuristic_based": {"professional": 0.8, "conversational": 0.75},
    "social_referencing": {"conversational": 0.85, "emotional": 0.7},
    "authority_deferring": {"professional": 0.9, "technical": 0.75},
    "maximizing": {"technical": 0.9, "professional": 0.85},
    "analytical_systematic": {"technical": 0.95, "professional": 0.85},
    "risk_calculating": {"technical": 0.85, "professional": 0.8},
    "deliberative_reflective": {"storytelling": 0.8, "professional": 0.75},
    "consensus_building": {"conversational": 0.85, "emotional": 0.7},
}

REGULATORY_EMOTIONAL_ALIGNMENT = {
    "eager_advancement": {"excitement": 0.9, "pride": 0.85, "anticipation": 0.8, "joy": 0.75},
    "aspiration_driven": {"empowerment": 0.9, "pride": 0.85, "anticipation": 0.8},
    "optimistic_exploration": {"excitement": 0.9, "surprise": 0.85, "anticipation": 0.8},
    "pragmatic_balanced": {"contentment": 0.8, "trust": 0.8},
    "situational_adaptive": {"trust": 0.8, "contentment": 0.75},
    "vigilant_security": {"trust": 0.9, "fear": 0.75, "anxiety": 0.7},
    "conservative_preservation": {"trust": 0.9, "nostalgia": 0.8, "contentment": 0.75},
    "anxious_avoidance": {"fear": 0.85, "anxiety": 0.8, "trust": 0.7},
}

MECHANISM_SUSCEPTIBILITY = {
    "gut_instinct": {"scarcity": 0.9, "liking": 0.85, "social_proof": 0.8},
    "recognition_based": {"social_proof": 0.85, "authority": 0.8, "liking": 0.75},
    "affect_driven": {"liking": 0.9, "reciprocity": 0.8, "social_proof": 0.75},
    "satisficing": {"social_proof": 0.85, "authority": 0.75, "reciprocity": 0.7},
    "heuristic_based": {"authority": 0.85, "social_proof": 0.8, "commitment": 0.7},
    "social_referencing": {"social_proof": 0.95, "unity": 0.8, "liking": 0.75},
    "authority_deferring": {"authority": 0.95, "commitment": 0.8, "social_proof": 0.7},
    "maximizing": {"authority": 0.85, "commitment": 0.8, "social_proof": 0.65},
    "analytical_systematic": {"authority": 0.9, "commitment": 0.85, "reciprocity": 0.6},
    "risk_calculating": {"authority": 0.85, "commitment": 0.8, "social_proof": 0.7},
    "deliberative_reflective": {"commitment": 0.85, "authority": 0.8, "reciprocity": 0.75},
    "consensus_building": {"social_proof": 0.9, "unity": 0.85, "authority": 0.7},
}

COGNITIVE_COMPLEXITY_ALIGNMENT = {
    "minimal_cognitive": {
        "conversational": 0.9, "minimalist": 0.95, "urgent": 0.85,
        "technical": 0.2, "professional": 0.4,
    },
    "moderate_cognitive": {
        "conversational": 0.85, "professional": 0.8, "storytelling": 0.8,
        "technical": 0.5, "minimalist": 0.7,
    },
    "high_cognitive": {
        "technical": 0.95, "professional": 0.9, "storytelling": 0.7,
        "minimalist": 0.4, "urgent": 0.3,
    },
}

SOCIAL_PERSUASION_ALIGNMENT = {
    "highly_independent": {
        "authority_expertise": 0.7, "scarcity_exclusivity": 0.6,
        "social_proof_numbers": 0.2, "bandwagon": 0.1,
    },
    "informational_seeker": {
        "authority_expertise": 0.95, "authority_credentials": 0.9,
        "social_proof_expert": 0.85, "social_proof_numbers": 0.6,
    },
    "socially_aware": {
        "social_proof_numbers": 0.85, "social_proof_similarity": 0.8,
        "social_proof_testimonials": 0.8, "bandwagon": 0.7,
    },
    "normatively_driven": {
        "social_proof_numbers": 0.95, "bandwagon": 0.9,
        "social_proof_similarity": 0.85, "unity_shared_identity": 0.8,
    },
    "opinion_leader": {
        "scarcity_exclusivity": 0.9, "authority_expertise": 0.8,
        "novelty_innovation": 0.85, "social_proof_numbers": 0.4,
    },
}

# ---------------------------------------------------------------------------
# Archetype Mapping (for corpus calibration — Phase 5)
# Maps dominant dimension values to archetypes
# ---------------------------------------------------------------------------

MOTIVATION_ARCHETYPE_MAP = {
    "pure_curiosity": "explorer", "excitement_seeking": "explorer",
    "escapism": "explorer", "flow_experience": "explorer",
    "mastery_seeking": "achiever", "goal_achievement": "achiever",
    "ego_protection": "achiever", "self_esteem_enhancement": "achiever",
    "efficiency_optimization": "achiever", "status_signaling": "achiever",
    "social_enjoyment": "connector", "belonging_affirmation": "connector",
    "social_approval": "connector", "relationship_maintenance": "connector",
    "social_compliance": "connector",
    "risk_mitigation": "guardian", "anxiety_reduction": "guardian",
    "punishment_avoidance": "guardian", "quality_assurance": "guardian",
    "guilt_avoidance": "guardian",
    "problem_solving": "analyst", "cost_minimization": "analyst",
    "opportunity_cost_awareness": "analyst",
    "self_expression": "creator", "uniqueness_differentiation": "creator",
    "sensory_pleasure": "creator",
    "altruistic_giving": "nurturer", "values_alignment": "nurturer",
    "personal_growth": "nurturer", "role_fulfillment": "nurturer",
    "reward_seeking": "pragmatist", "immediate_gratification": "pragmatist",
    "delayed_gratification": "pragmatist", "scarcity_response": "pragmatist",
    "future_self_investment": "pragmatist", "authority_compliance": "pragmatist",
    "nostalgia_comfort": "pragmatist",
}


# ===================================================================
# PHASE 1: Schema + Dimension/Appeal Nodes
# ===================================================================

def phase1_schema_and_nodes(session):
    """Create constraints, indexes, dimension value nodes, and appeal nodes."""
    log.info("=" * 70)
    log.info("PHASE 1: Schema, Constraints, Indexes, Dimension & Appeal Nodes")
    log.info("=" * 70)

    # --- Constraints ---
    constraints = [
        "CREATE CONSTRAINT gt_type_id IF NOT EXISTS FOR (t:GranularType) REQUIRE t.type_id IS UNIQUE",
        "CREATE CONSTRAINT mot_name IF NOT EXISTS FOR (n:Motivation) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT ds_name IF NOT EXISTS FOR (n:DecisionStyle) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT rf_name IF NOT EXISTS FOR (n:RegulatoryFocus) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT ei_name IF NOT EXISTS FOR (n:EmotionalIntensity) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT cl_name IF NOT EXISTS FOR (n:CognitiveLoadTolerance) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT to_name IF NOT EXISTS FOR (n:TemporalOrientation) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT si_name IF NOT EXISTS FOR (n:SocialInfluence) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT vp_name IF NOT EXISTS FOR (n:ValueProposition) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT ls_name IF NOT EXISTS FOR (n:LinguisticStyle) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT ea_name IF NOT EXISTS FOR (n:EmotionalAppeal) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT pm_name IF NOT EXISTS FOR (n:PersuasionMechanism) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT pt_name IF NOT EXISTS FOR (n:PersuasionTechnique) REQUIRE n.name IS UNIQUE",
    ]
    for cypher in constraints:
        try:
            session.run(cypher)
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                pass
            else:
                log.warning(f"Constraint warning: {e}")
    log.info(f"  Created/verified {len(constraints)} constraints")

    # --- Indexes for GranularType lookups ---
    indexes = [
        "CREATE INDEX gt_motivation IF NOT EXISTS FOR (t:GranularType) ON (t.motivation)",
        "CREATE INDEX gt_decision_style IF NOT EXISTS FOR (t:GranularType) ON (t.decision_style)",
        "CREATE INDEX gt_regulatory_focus IF NOT EXISTS FOR (t:GranularType) ON (t.regulatory_focus)",
        "CREATE INDEX gt_emotional_intensity IF NOT EXISTS FOR (t:GranularType) ON (t.emotional_intensity)",
        "CREATE INDEX gt_cognitive_load IF NOT EXISTS FOR (t:GranularType) ON (t.cognitive_load)",
        "CREATE INDEX gt_temporal_orientation IF NOT EXISTS FOR (t:GranularType) ON (t.temporal_orientation)",
        "CREATE INDEX gt_social_influence IF NOT EXISTS FOR (t:GranularType) ON (t.social_influence)",
        # Composite indexes for alignment edge creation
        "CREATE INDEX gt_ds_cl IF NOT EXISTS FOR (t:GranularType) ON (t.decision_style, t.cognitive_load)",
        "CREATE INDEX gt_ds_si IF NOT EXISTS FOR (t:GranularType) ON (t.decision_style, t.social_influence)",
    ]
    for cypher in indexes:
        try:
            session.run(cypher)
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                pass
            else:
                log.warning(f"Index warning: {e}")
    log.info(f"  Created/verified {len(indexes)} indexes")

    # --- Dimension Value Nodes ---
    dim_specs = [
        ("Motivation", MOTIVATIONS),
        ("DecisionStyle", DECISION_STYLES),
        ("RegulatoryFocus", REGULATORY_FOCUS),
        ("EmotionalIntensity", EMOTIONAL_INTENSITY),
        ("CognitiveLoadTolerance", COGNITIVE_LOAD),
        ("TemporalOrientation", TEMPORAL_ORIENTATION),
        ("SocialInfluence", SOCIAL_INFLUENCE),
    ]
    total_dim = 0
    for label, values in dim_specs:
        for v in values:
            session.run(f"MERGE (n:{label} {{name: $name}})", name=v)
        total_dim += len(values)
        log.info(f"  {label}: {len(values)} nodes")

    # --- Appeal Dimension Nodes ---
    appeal_specs = [
        ("ValueProposition", VALUE_PROPOSITIONS),
        ("LinguisticStyle", LINGUISTIC_STYLES),
        ("EmotionalAppeal", EMOTIONAL_APPEALS),
        ("PersuasionMechanism", PERSUASION_MECHANISMS),
        ("PersuasionTechnique", PERSUASION_TECHNIQUES),
    ]
    total_appeal = 0
    for label, values in appeal_specs:
        for v in values:
            session.run(f"MERGE (n:{label} {{name: $name}})", name=v)
        total_appeal += len(values)
        log.info(f"  {label}: {len(values)} nodes")

    log.info(f"  TOTAL: {total_dim} dimension nodes + {total_appeal} appeal nodes = {total_dim + total_appeal}")
    log.info("PHASE 1 COMPLETE")


# ===================================================================
# PHASE 2: GranularType Nodes + Dimension Edges
# ===================================================================

def _generate_types_chunk(chunk_size=5000):
    """Generator that yields chunks of type dicts."""
    chunk = []
    for combo in itertools.product(
        MOTIVATIONS, DECISION_STYLES, REGULATORY_FOCUS,
        EMOTIONAL_INTENSITY, COGNITIVE_LOAD, TEMPORAL_ORIENTATION,
        SOCIAL_INFLUENCE,
    ):
        mot, ds, rf, ei, cl, to, si = combo
        type_id = f"{mot}|{ds}|{rf}|{ei}|{cl}|{to}|{si}"
        chunk.append({
            "type_id": type_id,
            "motivation": mot,
            "decision_style": ds,
            "regulatory_focus": rf,
            "emotional_intensity": ei,
            "cognitive_load": cl,
            "temporal_orientation": to,
            "social_influence": si,
        })
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def phase2_type_nodes(session, batch_size=5000):
    """Create all 1,920,960 GranularType nodes with dimension edges."""
    log.info("=" * 70)
    log.info(f"PHASE 2: Create {TOTAL_TYPES:,} GranularType nodes + dimension edges")
    log.info("=" * 70)

    # Check existing count
    existing = session.run(
        "MATCH (t:GranularType) RETURN count(t) as cnt"
    ).single()["cnt"]
    if existing >= TOTAL_TYPES:
        log.info(f"  Already have {existing:,} GranularType nodes — skipping Phase 2")
        return
    elif existing > 0:
        log.info(f"  Found {existing:,} existing GranularType nodes — continuing from where we left off")

    # Cypher for batch insert with dimension edges
    create_cypher = """
    UNWIND $batch AS row
    MERGE (t:GranularType {type_id: row.type_id})
    SET t.motivation = row.motivation,
        t.decision_style = row.decision_style,
        t.regulatory_focus = row.regulatory_focus,
        t.emotional_intensity = row.emotional_intensity,
        t.cognitive_load = row.cognitive_load,
        t.temporal_orientation = row.temporal_orientation,
        t.social_influence = row.social_influence
    WITH t, row
    MATCH (m:Motivation {name: row.motivation})
    MERGE (t)-[:HAS_MOTIVATION]->(m)
    WITH t, row
    MATCH (d:DecisionStyle {name: row.decision_style})
    MERGE (t)-[:HAS_DECISION_STYLE]->(d)
    WITH t, row
    MATCH (r:RegulatoryFocus {name: row.regulatory_focus})
    MERGE (t)-[:HAS_REGULATORY_FOCUS]->(r)
    WITH t, row
    MATCH (e:EmotionalIntensity {name: row.emotional_intensity})
    MERGE (t)-[:HAS_EMOTIONAL_INTENSITY]->(e)
    WITH t, row
    MATCH (c:CognitiveLoadTolerance {name: row.cognitive_load})
    MERGE (t)-[:HAS_COGNITIVE_LOAD]->(c)
    WITH t, row
    MATCH (o:TemporalOrientation {name: row.temporal_orientation})
    MERGE (t)-[:HAS_TEMPORAL_ORIENTATION]->(o)
    WITH t, row
    MATCH (s:SocialInfluence {name: row.social_influence})
    MERGE (t)-[:HAS_SOCIAL_INFLUENCE]->(s)
    """

    start = time.time()
    total_created = 0
    batch_num = 0

    for chunk in _generate_types_chunk(batch_size):
        batch_num += 1
        t0 = time.time()
        session.run(create_cypher, batch=chunk)
        elapsed = time.time() - t0
        total_created += len(chunk)

        if batch_num % 10 == 0 or total_created >= TOTAL_TYPES:
            rate = total_created / (time.time() - start)
            remaining = (TOTAL_TYPES - total_created) / rate if rate > 0 else 0
            log.info(
                f"  Batch {batch_num}: {total_created:,}/{TOTAL_TYPES:,} "
                f"({100 * total_created / TOTAL_TYPES:.1f}%) | "
                f"{elapsed:.1f}s/batch | {rate:.0f} types/s | "
                f"ETA: {remaining / 60:.0f}m"
            )

    total_time = time.time() - start
    log.info(f"  Created {total_created:,} type nodes + {total_created * 7:,} dimension edges")
    log.info(f"  Total time: {total_time / 60:.1f} minutes ({total_created / total_time:.0f} types/s)")
    log.info("PHASE 2 COMPLETE")


# ===================================================================
# PHASE 3: Alignment Edges
# ===================================================================

def _create_edges_by_dimension(session, match_props, target_label, target_name,
                                rel_type, score, extra_props=None,
                                sub_batch_dim=None, sub_batch_values=None):
    """Create edges from GranularType nodes matching dimension props to a target node.
    
    For large match sets (>50K types), use sub_batch_dim/sub_batch_values to split
    the query into smaller transactions by iterating over an additional dimension.
    """
    set_parts = ["r.alignment_score = $score"]
    base_params = {"target_name": target_name, "score": score}
    if extra_props:
        for pk, pv in extra_props.items():
            param_key = f"ep_{pk}"
            set_parts.append(f"r.{pk} = ${param_key}")
            base_params[param_key] = pv
    set_clause = ", ".join(set_parts)

    if sub_batch_dim and sub_batch_values:
        # Sub-batch: iterate over additional dimension to keep transaction sizes manageable
        for sub_val in sub_batch_values:
            where_parts = []
            params = dict(base_params)
            for k, v in match_props.items():
                where_parts.append(f"t.{k} = ${k}")
                params[k] = v
            where_parts.append(f"t.{sub_batch_dim} = $sub_val")
            params["sub_val"] = sub_val
            where_clause = " AND ".join(where_parts)
            cypher = f"""
            MATCH (t:GranularType) WHERE {where_clause}
            MATCH (target:{target_label} {{name: $target_name}})
            MERGE (t)-[r:{rel_type}]->(target)
            SET {set_clause}
            """
            session.run(cypher, **params)
    else:
        where_parts = []
        params = dict(base_params)
        for k, v in match_props.items():
            where_parts.append(f"t.{k} = ${k}")
            params[k] = v
        where_clause = " AND ".join(where_parts)
        cypher = f"""
        MATCH (t:GranularType) WHERE {where_clause}
        MATCH (target:{target_label} {{name: $target_name}})
        MERGE (t)-[r:{rel_type}]->(target)
        SET {set_clause}
        """
        session.run(cypher, **params)


def phase3_alignment_edges(session):
    """Create all alignment edges from GranularType nodes to appeal nodes."""
    log.info("=" * 70)
    log.info("PHASE 3: Create alignment edges (~35M edges)")
    log.info("=" * 70)

    start = time.time()
    edge_count = 0
    query_count = 0

    # --- Check existing edge counts to skip completed sub-phases ---
    existing_av = session.run("MATCH ()-[r:ALIGNS_WITH_VALUE]->() RETURN count(r) as cnt").single()["cnt"]
    existing_rw = session.run("MATCH ()-[r:RESONATES_WITH]->() RETURN count(r) as cnt").single()["cnt"]
    existing_ms = session.run("MATCH ()-[r:MATCHES_STYLE]->() RETURN count(r) as cnt").single()["cnt"]
    # SUSCEPTIBLE_TO includes both mechanism and technique edges
    existing_st = session.run(
        "MATCH (:GranularType)-[r:SUSCEPTIBLE_TO]->() RETURN count(r) as cnt"
    ).single()["cnt"]
    log.info(f"  Existing edges: AV={existing_av:,} RW={existing_rw:,} ST={existing_st:,} MS={existing_ms:,}")

    # --- 3a: ALIGNS_WITH_VALUE (motivation → ValueProposition) ---
    if existing_av >= 4_000_000:
        log.info("  3a: ALIGNS_WITH_VALUE — already done, skipping")
    else:
        log.info("  3a: ALIGNS_WITH_VALUE edges (motivation → ValueProposition)")
        for motivation, alignments in MOTIVATION_VALUE_ALIGNMENT.items():
            for value_prop, score in alignments.items():
                if score < 0.1:
                    continue
                _create_edges_by_dimension(
                    session,
                    match_props={"motivation": motivation},
                    target_label="ValueProposition",
                    target_name=value_prop,
                    rel_type="ALIGNS_WITH_VALUE",
                    score=score,
                    extra_props={"motivation_basis": motivation},
                )
                query_count += 1
                edge_count += TOTAL_TYPES // len(MOTIVATIONS)
        log.info(f"    {query_count} queries, ~{edge_count:,} edges, {time.time() - start:.0f}s elapsed")

    # --- 3b: RESONATES_WITH (regulatory_focus → EmotionalAppeal) ---
    if existing_rw >= 5_000_000:
        log.info("  3b: RESONATES_WITH — already done, skipping")
    else:
        log.info("  3b: RESONATES_WITH edges (regulatory_focus → EmotionalAppeal)")
        t0 = time.time()
        q0 = query_count
        for reg_focus, alignments in REGULATORY_EMOTIONAL_ALIGNMENT.items():
            for appeal, score in alignments.items():
                if score < 0.1:
                    continue
                # Sub-batch by motivation to keep transactions <50K
                _create_edges_by_dimension(
                    session,
                    match_props={"regulatory_focus": reg_focus},
                    target_label="EmotionalAppeal",
                    target_name=appeal,
                    rel_type="RESONATES_WITH",
                    score=score,
                    extra_props={"regulatory_basis": reg_focus},
                    sub_batch_dim="motivation",
                    sub_batch_values=MOTIVATIONS,
                )
                query_count += 1
                edge_count += TOTAL_TYPES // len(REGULATORY_FOCUS)
        log.info(f"    {query_count - q0} queries, ~{(query_count - q0) * (TOTAL_TYPES // len(REGULATORY_FOCUS)):,} edges, {time.time() - t0:.0f}s")

    # --- 3c: SUSCEPTIBLE_TO mechanism (decision_style → PersuasionMechanism) ---
    # Count mechanism-specific edges
    existing_mech = session.run(
        "MATCH (:GranularType)-[r:SUSCEPTIBLE_TO]->(:PersuasionMechanism) RETURN count(r) as cnt"
    ).single()["cnt"]
    if existing_mech >= 5_700_000:
        log.info("  3c: SUSCEPTIBLE_TO mechanism — already done, skipping")
    else:
        log.info("  3c: SUSCEPTIBLE_TO edges (decision_style → PersuasionMechanism)")
        t0 = time.time()
        q0 = query_count
        for ds, alignments in MECHANISM_SUSCEPTIBILITY.items():
            for mechanism, score in alignments.items():
                if score < 0.1:
                    continue
                # Sub-batch by motivation (~4,300 per sub-batch)
                _create_edges_by_dimension(
                    session,
                    match_props={"decision_style": ds},
                    target_label="PersuasionMechanism",
                    target_name=mechanism,
                    rel_type="SUSCEPTIBLE_TO",
                    score=score,
                    extra_props={"decision_basis": ds, "source_matrix": "MECHANISM_SUSCEPTIBILITY"},
                    sub_batch_dim="motivation",
                    sub_batch_values=MOTIVATIONS,
                )
                query_count += 1
                edge_count += TOTAL_TYPES // len(DECISION_STYLES)
        log.info(f"    {query_count - q0} queries, {time.time() - t0:.0f}s")

    # --- 3d: SUSCEPTIBLE_TO technique (social_influence → PersuasionTechnique) ---
    existing_tech = session.run(
        "MATCH (:GranularType)-[r:SUSCEPTIBLE_TO]->(:PersuasionTechnique) RETURN count(r) as cnt"
    ).single()["cnt"]
    if existing_tech >= 7_000_000:
        log.info("  3d: SUSCEPTIBLE_TO technique — already done, skipping")
    else:
        log.info("  3d: SUSCEPTIBLE_TO edges (social_influence → PersuasionTechnique)")
        t0 = time.time()
        q0 = query_count
        for si, alignments in SOCIAL_PERSUASION_ALIGNMENT.items():
            for technique, score in alignments.items():
                if score < 0.1:
                    continue
                # Sub-batch by motivation (~10,300 per sub-batch)
                _create_edges_by_dimension(
                    session,
                    match_props={"social_influence": si},
                    target_label="PersuasionTechnique",
                    target_name=technique,
                    rel_type="SUSCEPTIBLE_TO",
                    score=score,
                    extra_props={"social_basis": si, "source_matrix": "SOCIAL_PERSUASION_ALIGNMENT"},
                    sub_batch_dim="motivation",
                    sub_batch_values=MOTIVATIONS,
                )
                query_count += 1
                edge_count += TOTAL_TYPES // len(SOCIAL_INFLUENCE)
        log.info(f"    {query_count - q0} queries, {time.time() - t0:.0f}s")

    # --- 3e: MATCHES_STYLE (decision_style + cognitive_load → LinguisticStyle) ---
    if existing_ms >= 5_000_000:
        log.info("  3e: MATCHES_STYLE — already done, skipping")
    else:
        log.info("  3e: MATCHES_STYLE edges (decision_style + cognitive_load → LinguisticStyle)")
        t0 = time.time()
        q0 = query_count
        for ds in DECISION_STYLES:
            ds_scores = DECISION_STYLE_LINGUISTIC_ALIGNMENT.get(ds, {})
            for cl in COGNITIVE_LOAD:
                cl_scores = COGNITIVE_COMPLEXITY_ALIGNMENT.get(cl, {})
                all_styles = set(list(ds_scores.keys()) + list(cl_scores.keys()))
                for style in all_styles:
                    ds_val = ds_scores.get(style, 0.0)
                    cl_val = cl_scores.get(style, 0.0)
                    combined = 0.6 * ds_val + 0.4 * cl_val
                    if combined < 0.1:
                        continue
                    # ds + cl already constrains to ~53K types, sub-batch by regulatory_focus
                    _create_edges_by_dimension(
                        session,
                        match_props={"decision_style": ds, "cognitive_load": cl},
                        target_label="LinguisticStyle",
                        target_name=style,
                        rel_type="MATCHES_STYLE",
                        score=round(combined, 3),
                        extra_props={"decision_basis": ds, "cognitive_basis": cl},
                        sub_batch_dim="regulatory_focus",
                        sub_batch_values=REGULATORY_FOCUS,
                    )
                    query_count += 1
                    edge_count += TOTAL_TYPES // (len(DECISION_STYLES) * len(COGNITIVE_LOAD))
        log.info(f"    {query_count - q0} queries, {time.time() - t0:.0f}s")

    total_time = time.time() - start
    log.info(f"  TOTAL: {query_count} queries, ~{edge_count:,} estimated edges")
    log.info(f"  Total time: {total_time / 60:.1f} minutes")
    log.info("PHASE 3 COMPLETE")


# ===================================================================
# PHASE 4: Product Characteristics
# ===================================================================

def phase4_product_nodes(session):
    """Create product nodes from corpus data with appeal edges."""
    log.info("=" * 70)
    log.info("PHASE 4: Product Characteristic Nodes")
    log.info("=" * 70)

    priors_path = Path("/Users/chrisnocera/Sites/adam-platform/data/learning/ingestion_merged_priors.json")
    result_dir = Path("/Users/chrisnocera/Sites/adam-platform/data/reingestion_output")

    if not priors_path.exists():
        log.warning(f"  Priors file not found at {priors_path} — skipping Phase 4")
        return

    # Load priors for category-level data
    log.info("  Loading ingestion_merged_priors.json...")
    with open(priors_path) as f:
        priors = json.load(f)

    # --- 4a: Category moderation edges ---
    log.info("  4a: Category moderation edges")
    cat_eff = priors.get("category_effectiveness_matrices", {})
    mod_count = 0
    for category, archetypes in cat_eff.items():
        # Ensure category node exists
        session.run("MERGE (c:ProductCategory {name: $name})", name=category)
        # Compute category-level mechanism effectiveness (average across archetypes)
        mech_totals = {}
        mech_counts = {}
        for arch, mechs in archetypes.items():
            if not isinstance(mechs, dict):
                continue
            for mech, data in mechs.items():
                rate = data.get("rate", data) if isinstance(data, dict) else data
                if isinstance(rate, (int, float)):
                    mech_totals[mech] = mech_totals.get(mech, 0) + rate
                    mech_counts[mech] = mech_counts.get(mech, 0) + 1

        # Compare to global mean and store delta
        global_eff = priors.get("global_effectiveness_matrix", {})
        global_mech_totals = {}
        global_mech_counts = {}
        for arch, mechs in global_eff.items():
            if not isinstance(mechs, dict):
                continue
            for mech, data in mechs.items():
                rate = data.get("rate", data) if isinstance(data, dict) else data
                if isinstance(rate, (int, float)):
                    global_mech_totals[mech] = global_mech_totals.get(mech, 0) + rate
                    global_mech_counts[mech] = global_mech_counts.get(mech, 0) + 1

        for mech in mech_totals:
            cat_avg = mech_totals[mech] / mech_counts[mech] if mech_counts.get(mech) else 0
            global_avg = (global_mech_totals.get(mech, 0) / global_mech_counts.get(mech, 1)
                          if global_mech_counts.get(mech) else 0)
            delta = cat_avg - global_avg
            if abs(delta) > 0.01:
                session.run("""
                    MATCH (c:ProductCategory {name: $category})
                    MATCH (m:PersuasionMechanism {name: $mechanism})
                    MERGE (c)-[r:MODERATES]->(m)
                    SET r.delta = $delta, r.category_avg = $cat_avg, r.global_avg = $global_avg
                """, category=category, mechanism=mech, delta=round(delta, 4),
                     cat_avg=round(cat_avg, 4), global_avg=round(global_avg, 4))
                mod_count += 1
    log.info(f"    Created {mod_count} category moderation edges")

    # --- 4b: Product nodes from result files ---
    log.info("  4b: Product nodes from result files")
    product_count = 0
    appeal_edge_count = 0

    for result_file in sorted(result_dir.glob("*_result.json")):
        if "old_format" in str(result_file):
            continue
        log.info(f"    Loading {result_file.name}...")
        try:
            with open(result_file) as f:
                data = json.load(f)
        except Exception as e:
            log.warning(f"    Failed to load {result_file.name}: {e}")
            continue

        category = data.get("category", result_file.stem.replace("_result", ""))
        ad_profiles = data.get("product_ad_profiles", {})

        if not ad_profiles:
            continue

        # Batch-insert products
        batch = []
        for asin, profile in ad_profiles.items():
            if not isinstance(profile, dict):
                continue
            batch.append({
                "asin": asin,
                "category": category,
                "primary_persuasion": profile.get("primary_persuasion", ""),
                "primary_emotion": profile.get("primary_emotion", ""),
                "primary_value": profile.get("primary_value", ""),
                "linguistic_style": profile.get("linguistic_style", ""),
            })
            if len(batch) >= 2000:
                _insert_product_batch(session, batch)
                product_count += len(batch)
                appeal_edge_count += len(batch) * 2  # approx: category + appeal edges
                batch = []

        if batch:
            _insert_product_batch(session, batch)
            product_count += len(batch)
            appeal_edge_count += len(batch) * 2

    log.info(f"    Created {product_count:,} product nodes, ~{appeal_edge_count:,} appeal edges")
    log.info("PHASE 4 COMPLETE")


def _insert_product_batch(session, batch):
    """Insert a batch of product nodes with category and appeal edges."""
    session.run("""
        UNWIND $batch AS row
        MERGE (p:Product {asin: row.asin})
        SET p.category = row.category,
            p.primary_persuasion = row.primary_persuasion,
            p.primary_emotion = row.primary_emotion,
            p.primary_value = row.primary_value,
            p.linguistic_style = row.linguistic_style
        WITH p, row
        MATCH (c:ProductCategory {name: row.category})
        MERGE (p)-[:IN_CATEGORY]->(c)
    """, batch=batch)

    # Separate query for appeal edges (not all products have matching appeal nodes)
    session.run("""
        UNWIND $batch AS row
        MATCH (p:Product {asin: row.asin})
        WITH p, row
        WHERE row.primary_persuasion <> ''
        MATCH (pt:PersuasionMechanism {name: row.primary_persuasion})
        MERGE (p)-[:USES_APPEAL]->(pt)
    """, batch=batch)

    session.run("""
        UNWIND $batch AS row
        MATCH (p:Product {asin: row.asin})
        WITH p, row
        WHERE row.primary_emotion <> ''
        MATCH (ea:EmotionalAppeal {name: row.primary_emotion})
        MERGE (p)-[:EVOKES]->(ea)
    """, batch=batch)


# ===================================================================
# PHASE 5: Corpus Calibration
# ===================================================================

def phase5_corpus_calibration(session):
    """Calibrate alignment edges with empirical data from 937M review corpus."""
    log.info("=" * 70)
    log.info("PHASE 5: Corpus Calibration of Alignment Edges")
    log.info("=" * 70)

    priors_path = Path("/Users/chrisnocera/Sites/adam-platform/data/learning/ingestion_merged_priors.json")
    if not priors_path.exists():
        log.warning(f"  Priors file not found — skipping Phase 5")
        return

    with open(priors_path) as f:
        priors = json.load(f)

    global_eff = priors.get("global_effectiveness_matrix", {})

    # Build archetype → mechanism effectiveness lookup
    arch_mech_eff = {}  # {archetype: {mechanism: {rate, samples}}}
    for archetype, mechs in global_eff.items():
        if not isinstance(mechs, dict):
            continue
        arch_lower = archetype.lower()
        arch_mech_eff[arch_lower] = {}
        for mech, data in mechs.items():
            if isinstance(data, dict):
                arch_mech_eff[arch_lower][mech] = {
                    "rate": data.get("success_rate", data.get("rate", 0)),
                    "samples": data.get("sample_size", data.get("samples", 0)),
                }
            elif isinstance(data, (int, float)):
                arch_mech_eff[arch_lower][mech] = {"rate": data, "samples": 0}

    log.info(f"  Loaded effectiveness data for {len(arch_mech_eff)} archetypes")

    # For each motivation → archetype mapping, calibrate SUSCEPTIBLE_TO edges
    calibrated = 0
    for motivation, archetype in MOTIVATION_ARCHETYPE_MAP.items():
        eff_data = arch_mech_eff.get(archetype, {})
        if not eff_data:
            continue

        for mechanism, mech_data in eff_data.items():
            rate = mech_data.get("rate", 0)
            samples = mech_data.get("samples", 0)
            if rate <= 0:
                continue

            # Update SUSCEPTIBLE_TO edges for this motivation's types → this mechanism
            result = session.run("""
                MATCH (t:GranularType {motivation: $motivation})-[r:SUSCEPTIBLE_TO]->(m:PersuasionMechanism {name: $mechanism})
                SET r.empirical_validation = $rate,
                    r.empirical_sample_size = $samples,
                    r.dominant_archetype = $archetype,
                    r.calibration_confidence = CASE
                        WHEN abs(r.alignment_score - $rate) < 0.1 THEN 0.9
                        WHEN abs(r.alignment_score - $rate) < 0.2 THEN 0.7
                        ELSE 0.5
                    END,
                    r.theory_empirical_agreement = 1.0 - abs(r.alignment_score - $rate)
                RETURN count(r) as updated
            """, motivation=motivation, mechanism=mechanism, rate=round(rate, 4),
                 samples=samples, archetype=archetype)

            updated = result.single()["updated"]
            calibrated += updated

    log.info(f"  Calibrated {calibrated:,} SUSCEPTIBLE_TO edges with empirical data")

    # Category-level calibration — store as aggregated properties per archetype-mechanism
    cat_eff = priors.get("category_effectiveness_matrices", {})
    cat_calibrated = 0
    for category, archetypes in cat_eff.items():
        for archetype_key, mechs in archetypes.items():
            if not isinstance(mechs, dict):
                continue
            archetype = archetype_key.lower()
            matching_motivations = [
                m for m, a in MOTIVATION_ARCHETYPE_MAP.items() if a == archetype
            ]
            if not matching_motivations:
                continue
            for mechanism, data in mechs.items():
                rate = data.get("success_rate", data.get("rate", data)) if isinstance(data, dict) else data
                samples = data.get("sample_size", data.get("samples", 0)) if isinstance(data, dict) else 0
                if not isinstance(rate, (int, float)) or rate <= 0:
                    continue
                # Sub-batch by motivation to avoid memory issues
                for motivation in matching_motivations:
                    try:
                        session.run("""
                            MATCH (t:GranularType {motivation: $motivation})-[r:SUSCEPTIBLE_TO]->(m:PersuasionMechanism {name: $mechanism})
                            WHERE r.category_calibrations IS NULL OR NOT $category IN r.category_calibrations
                            SET r.category_calibrations = coalesce(r.category_calibrations, []) + [$category],
                                r.category_rates = coalesce(r.category_rates, []) + [$rate]
                        """, motivation=motivation, mechanism=mechanism,
                             category=category, rate=round(rate, 4))
                        cat_calibrated += 1
                    except Exception as e:
                        if "MemoryPool" in str(e):
                            log.warning(f"    Memory limit on {category}/{archetype}/{mechanism}/{motivation} — skipping")
                        else:
                            raise

    log.info(f"  Applied {cat_calibrated:,} category-level calibration queries")
    log.info("PHASE 5 COMPLETE")


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Populate type system graph in Neo4j")
    parser.add_argument("--phase", type=int, default=0, help="Run only this phase (1-5). 0 = all.")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--username", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default="atomofthought", help="Neo4j password")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for type node creation")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing")
    args = parser.parse_args()

    if args.dry_run:
        log.info(f"DRY RUN — Type system dimensions:")
        log.info(f"  Motivations:          {len(MOTIVATIONS)}")
        log.info(f"  Decision Styles:      {len(DECISION_STYLES)}")
        log.info(f"  Regulatory Focus:     {len(REGULATORY_FOCUS)}")
        log.info(f"  Emotional Intensity:  {len(EMOTIONAL_INTENSITY)}")
        log.info(f"  Cognitive Load:       {len(COGNITIVE_LOAD)}")
        log.info(f"  Temporal Orientation: {len(TEMPORAL_ORIENTATION)}")
        log.info(f"  Social Influence:     {len(SOCIAL_INFLUENCE)}")
        log.info(f"  TOTAL TYPES:          {TOTAL_TYPES:,}")
        log.info(f"  Dimension edges:      {TOTAL_TYPES * 7:,}")

        # Count alignment edges
        av_count = sum(len(v) for v in MOTIVATION_VALUE_ALIGNMENT.values())
        re_count = sum(len(v) for v in REGULATORY_EMOTIONAL_ALIGNMENT.values())
        ms_count = sum(len(v) for v in MECHANISM_SUSCEPTIBILITY.values())
        sp_count = sum(len(v) for v in SOCIAL_PERSUASION_ALIGNMENT.values())
        # MATCHES_STYLE
        ms_style = 0
        for ds in DECISION_STYLES:
            ds_s = DECISION_STYLE_LINGUISTIC_ALIGNMENT.get(ds, {})
            for cl in COGNITIVE_LOAD:
                cl_s = COGNITIVE_COMPLEXITY_ALIGNMENT.get(cl, {})
                all_styles = set(list(ds_s.keys()) + list(cl_s.keys()))
                for style in all_styles:
                    combined = 0.6 * ds_s.get(style, 0) + 0.4 * cl_s.get(style, 0)
                    if combined >= 0.1:
                        ms_style += 1

        log.info(f"  ALIGNS_WITH_VALUE:    {av_count} patterns × ~{TOTAL_TYPES // len(MOTIVATIONS):,} types each")
        log.info(f"  RESONATES_WITH:       {re_count} patterns × ~{TOTAL_TYPES // len(REGULATORY_FOCUS):,} types each")
        log.info(f"  SUSCEPTIBLE_TO mech:  {ms_count} patterns × ~{TOTAL_TYPES // len(DECISION_STYLES):,} types each")
        log.info(f"  SUSCEPTIBLE_TO tech:  {sp_count} patterns × ~{TOTAL_TYPES // len(SOCIAL_INFLUENCE):,} types each")
        log.info(f"  MATCHES_STYLE:        {ms_style} patterns × ~{TOTAL_TYPES // (len(DECISION_STYLES) * len(COGNITIVE_LOAD)):,} types each")
        return

    # Connect to Neo4j
    log.info(f"Connecting to Neo4j at {args.uri}...")
    driver = GraphDatabase.driver(args.uri, auth=(args.username, args.password))

    try:
        with driver.session() as session:
            # Verify connection
            cnt = session.run("MATCH (n) RETURN count(n) as cnt").single()["cnt"]
            log.info(f"Connected — {cnt:,} existing nodes in graph")

            phases = {
                1: lambda: phase1_schema_and_nodes(session),
                2: lambda: phase2_type_nodes(session, args.batch_size),
                3: lambda: phase3_alignment_edges(session),
                4: lambda: phase4_product_nodes(session),
                5: lambda: phase5_corpus_calibration(session),
            }

            if args.phase > 0:
                if args.phase in phases:
                    phases[args.phase]()
                else:
                    log.error(f"Unknown phase: {args.phase}")
            else:
                for phase_num in sorted(phases.keys()):
                    phases[phase_num]()

    finally:
        driver.close()

    log.info("=" * 70)
    log.info("ALL PHASES COMPLETE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
