"""
DSP Enrichment Engine — Neo4j Graph Population
=================================================

Persists all DSP knowledge into Neo4j:
    - 50 BehavioralSignal nodes
    - 500+ DSPConstruct nodes
    - 200+ causal/inferential edges
    - Bridge relationships to ADAM's existing theory graph

Node types:
    (:BehavioralSignal) — Observable bidstream signals
    (:DSPConstruct) — Psychological constructs
    (:DSPEdge) — Properties on relationship edges

Relationship types:
    (:BehavioralSignal)-[:INFERS_CONSTRUCT]->(:DSPConstruct)
    (:DSPConstruct)-[:CAUSES|MEDIATES|MODERATES|INHIBITS|SYNERGIZES_WITH|ANTAGONIZES]->(:DSPConstruct)
    (:DSPConstruct)-[:MAPS_TO_NDF]->(:PsychologicalState)
    (:DSPConstruct)-[:CREATES_NEED]->(:PsychologicalNeed)
    (:DSPConstruct)-[:SATISFIED_BY]->(:CognitiveMechanism)
"""

import json
import logging
from typing import Any, Dict, List

from adam.dsp.signal_registry import build_signal_registry
from adam.dsp.construct_registry import build_construct_registry
from adam.dsp.edge_registry import build_edge_registry

logger = logging.getLogger(__name__)


def generate_constraints_cypher() -> List[str]:
    """Generate Cypher constraints for DSP graph nodes."""
    return [
        "CREATE CONSTRAINT dsp_signal_id IF NOT EXISTS FOR (n:BehavioralSignal) REQUIRE n.signal_id IS UNIQUE",
        "CREATE CONSTRAINT dsp_construct_id IF NOT EXISTS FOR (n:DSPConstruct) REQUIRE n.construct_id IS UNIQUE",
        "CREATE INDEX dsp_construct_domain IF NOT EXISTS FOR (n:DSPConstruct) ON (n.domain)",
        "CREATE INDEX dsp_signal_source IF NOT EXISTS FOR (n:BehavioralSignal) ON (n.source)",
    ]


def generate_signal_nodes_cypher() -> List[str]:
    """Generate Cypher MERGE statements for BehavioralSignal nodes."""
    registry = build_signal_registry()
    statements = []

    for sig_id, signal in registry.items():
        # Escape description for Cypher
        desc = signal.description.replace("'", "\\'").replace('"', '\\"')
        name = signal.name.replace("'", "\\'")

        citations_str = "; ".join(signal.citations) if signal.citations else ""

        stmt = (
            f'MERGE (s:BehavioralSignal {{signal_id: "{sig_id}"}}) '
            f'SET s.name = "{name}", '
            f's.source = "{signal.source.value}", '
            f's.reliability = "{signal.reliability.value}", '
            f's.reliability_weight = {signal.reliability.weight}, '
            f's.extraction_method = "{signal.extraction_method[:200]}", '
            f's.latency_budget_ms = {signal.latency_budget_ms}, '
            f's.validated_accuracy = {signal.validated_accuracy or 0.0}, '
            f's.min_observations = {signal.min_observations}, '
            f's.device_specific = "{signal.device_specific.value if signal.device_specific else "all"}", '
            f's.citations = "{citations_str}"'
        )
        statements.append(stmt)

        # Create INFERS_CONSTRUCT relationships
        for construct_id in signal.psychological_construct_ids:
            rel_stmt = (
                f'MATCH (s:BehavioralSignal {{signal_id: "{sig_id}"}}) '
                f'MERGE (c:DSPConstruct {{construct_id: "{construct_id}"}}) '
                f'MERGE (s)-[:INFERS_CONSTRUCT]->(c)'
            )
            statements.append(rel_stmt)

    return statements


def generate_construct_nodes_cypher() -> List[str]:
    """Generate Cypher MERGE statements for DSPConstruct nodes.

    Now stores ALL construct metadata including creative_implications,
    effect_sizes, and dsp_signals — previously dropped during population.
    """
    registry = build_construct_registry()
    statements = []

    for c_id, construct in registry.items():
        name = construct.get("name", c_id).replace("'", "\\'").replace('"', '\\"')
        domain = construct.get("domain", "unknown")
        if hasattr(domain, "value"):
            domain = domain.value
        desc = construct.get("description", "").replace("'", "\\'").replace('"', '\\"')[:300]
        ad_rel = construct.get("advertising_relevance", "").replace("'", "\\'").replace('"', '\\"')[:300]
        confidence = construct.get("confidence", "moderate")
        if hasattr(confidence, "value"):
            confidence = confidence.value
        adam_int = construct.get("adam_integration", "").replace("'", "\\'").replace('"', '\\"')[:200]
        citations = "; ".join(construct.get("citations", []))[:200]

        # Serialize creative_implications as JSON
        ci_dict = construct.get("creative_implications", {})
        ci_json = json.dumps(ci_dict).replace("'", "\\'").replace('"', '\\"') if ci_dict else "{}"

        # Serialize effect_sizes as JSON
        es_list = construct.get("effect_sizes", [])
        es_json = json.dumps([
            {"metric": es.metric, "value": es.value, "context": es.context}
            for es in es_list
        ]).replace("'", "\\'").replace('"', '\\"') if es_list else "[]"

        # Serialize dsp_signals as JSON
        dsp_sigs = construct.get("dsp_signals", [])
        dsp_json = json.dumps(dsp_sigs).replace("'", "\\'").replace('"', '\\"') if dsp_sigs else "[]"

        stmt = (
            f'MERGE (c:DSPConstruct {{construct_id: "{c_id}"}}) '
            f'SET c.name = "{name}", '
            f'c.domain = "{domain}", '
            f'c.description = "{desc}", '
            f'c.advertising_relevance = "{ad_rel}", '
            f'c.confidence = "{confidence}", '
            f'c.adam_integration = "{adam_int}", '
            f'c.citations = "{citations}", '
            f'c.creative_implications = "{ci_json}", '
            f'c.effect_sizes = "{es_json}", '
            f'c.dsp_signals = "{dsp_json}"'
        )
        statements.append(stmt)

    return statements


def generate_edge_cypher() -> List[str]:
    """Generate Cypher MERGE statements for causal/inferential edges.

    Now stores ALL edge metadata including effect_sizes, boundary_conditions,
    creative_implications, temporal_modulation, vulnerability_flags, and more.
    Previously only stored mechanism, reasoning_type, strength, confidence,
    description, and adam_source — dropping 60-70% of construct metadata.
    """
    registry = build_edge_registry()
    statements = []

    for e_id, edge in registry.items():
        source = edge["source"]
        target = edge["target"]
        mechanism = edge["mechanism"]
        if hasattr(mechanism, "value"):
            mechanism = mechanism.value
        reasoning = edge["reasoning_type"]
        if hasattr(reasoning, "value"):
            reasoning = reasoning.value
        desc = edge.get("description", "").replace("'", "\\'").replace('"', '\\"')[:300]
        confidence = edge.get("confidence", "moderate")
        if hasattr(confidence, "value"):
            confidence = confidence.value
        adam_source = edge.get("adam_source", "").replace("'", "\\'")[:200]

        # Compute strength from effect sizes
        effect_sizes = edge.get("effect_sizes", [])
        strength = 0.5
        if effect_sizes:
            strength = abs(effect_sizes[0].value)
            if effect_sizes[0].metric == "odds_ratio":
                strength = min(1.0, effect_sizes[0].value / 6.0)

        # Map reasoning type to Neo4j relationship type
        rel_type = _reasoning_to_rel_type(reasoning)

        # Domain
        domain = edge.get("domain", "unknown")
        if hasattr(domain, "value"):
            domain = domain.value

        # Serialize effect_sizes as JSON
        es_json = json.dumps([
            {"metric": es.metric, "value": es.value, "context": es.context}
            for es in effect_sizes
        ]).replace("'", "\\'").replace('"', '\\"') if effect_sizes else "[]"

        # Serialize boundary_conditions as JSON
        bc_list = edge.get("boundary_conditions", [])
        bc_json = json.dumps(bc_list).replace("'", "\\'").replace('"', '\\"') if bc_list else "[]"

        # Serialize creative_implications as JSON
        ci_dict = edge.get("creative_implications", {})
        ci_json = json.dumps(ci_dict).replace("'", "\\'").replace('"', '\\"') if ci_dict else "{}"

        # Serialize temporal_modulation as JSON
        tm = edge.get("temporal_modulation")
        if tm:
            tm_dict = {
                "type": tm.modulation_type if hasattr(tm, "modulation_type") else str(tm),
                "peak_times": getattr(tm, "peak_times", []),
                "decay_hours": getattr(tm, "decay_hours", 0),
            }
            tm_json = json.dumps(tm_dict).replace("'", "\\'").replace('"', '\\"')
        else:
            tm_json = "{}"

        # Serialize vulnerability_flags as JSON
        vf_list = edge.get("vulnerability_flags", [])
        vf_json = json.dumps([
            vf.value if hasattr(vf, "value") else str(vf) for vf in vf_list
        ]).replace("'", "\\'").replace('"', '\\"') if vf_list else "[]"

        # dsp_operationalization (string)
        dsp_op = edge.get("dsp_operationalization", "").replace("'", "\\'").replace('"', '\\"')[:300]

        # Serialize required_signals as JSON
        rs_list = edge.get("required_signals", [])
        rs_json = json.dumps(rs_list).replace("'", "\\'").replace('"', '\\"') if rs_list else "[]"

        # Direction
        direction = edge.get("direction", "").replace("'", "\\'").replace('"', '\\"')[:200]

        stmt = (
            f'MERGE (src:DSPConstruct {{construct_id: "{source}"}}) '
            f'MERGE (tgt:DSPConstruct {{construct_id: "{target}"}}) '
            f'MERGE (src)-[r:{rel_type} {{edge_id: "{e_id}"}}]->(tgt) '
            f'SET r.mechanism = "{mechanism}", '
            f'r.reasoning_type = "{reasoning}", '
            f'r.strength = {strength:.3f}, '
            f'r.confidence = "{confidence}", '
            f'r.description = "{desc}", '
            f'r.adam_source = "{adam_source}", '
            f'r.domain = "{domain}", '
            f'r.direction = "{direction}", '
            f'r.effect_sizes = "{es_json}", '
            f'r.boundary_conditions = "{bc_json}", '
            f'r.creative_implications = "{ci_json}", '
            f'r.temporal_modulation = "{tm_json}", '
            f'r.vulnerability_flags = "{vf_json}", '
            f'r.dsp_operationalization = "{dsp_op}", '
            f'r.required_signals = "{rs_json}"'
        )
        statements.append(stmt)

    return statements


def generate_ndf_bridge_cypher() -> List[str]:
    """Generate bridge relationships between DSPConstructs and ADAM PsychologicalStates."""
    bridges = [
        ("promotion_focus", "high_approach", "approach_avoidance"),
        ("prevention_focus", "high_avoidance", "approach_avoidance"),
        ("construal_level_state", "long_temporal_horizon", "temporal_horizon"),
        ("social_proof_principle", "high_social_calibration", "social_calibration"),
        ("need_for_closure", "low_uncertainty_tolerance", "uncertainty_tolerance"),
        ("costly_signaling", "high_status_sensitivity", "status_sensitivity"),
        ("system2_processing", "high_cognitive_engagement", "cognitive_engagement"),
        ("emotional_arousal", "high_arousal_seeking", "arousal_seeking"),
    ]
    statements = []
    for dsp_construct, adam_state, ndf_dim in bridges:
        stmt = (
            f'MATCH (dsp:DSPConstruct {{construct_id: "{dsp_construct}"}}) '
            f'MATCH (adam:PsychologicalState {{name: "{adam_state}"}}) '
            f'MERGE (dsp)-[:MAPS_TO_NDF {{ndf_dimension: "{ndf_dim}"}}]->(adam)'
        )
        statements.append(stmt)
    return statements


def populate_dsp_graph(driver, batch_size: int = 100) -> Dict[str, int]:
    """
    Populate Neo4j with the complete DSP knowledge graph.

    Args:
        driver: Neo4j driver instance
        batch_size: Number of statements per transaction

    Returns:
        Dict with counts of nodes and edges created
    """
    counts = {"constraints": 0, "signals": 0, "constructs": 0, "edges": 0, "bridges": 0}

    # Step 1: Create constraints
    constraint_stmts = generate_constraints_cypher()
    with driver.session() as session:
        for stmt in constraint_stmts:
            try:
                session.run(stmt)
                counts["constraints"] += 1
            except Exception as e:
                logger.debug(f"Constraint may already exist: {e}")
    logger.info(f"Created {counts['constraints']} constraints")

    # Step 2: Create BehavioralSignal nodes
    signal_stmts = generate_signal_nodes_cypher()
    _execute_batch(driver, signal_stmts, batch_size)
    counts["signals"] = len([s for s in signal_stmts if "MERGE (s:BehavioralSignal" in s])
    logger.info(f"Created {counts['signals']} BehavioralSignal nodes")

    # Step 3: Create DSPConstruct nodes
    construct_stmts = generate_construct_nodes_cypher()
    _execute_batch(driver, construct_stmts, batch_size)
    counts["constructs"] = len(construct_stmts)
    logger.info(f"Created {counts['constructs']} DSPConstruct nodes")

    # Step 4: Create causal/inferential edges
    edge_stmts = generate_edge_cypher()
    _execute_batch(driver, edge_stmts, batch_size)
    counts["edges"] = len(edge_stmts)
    logger.info(f"Created {counts['edges']} causal/inferential edges")

    # Step 5: Create NDF bridge relationships
    bridge_stmts = generate_ndf_bridge_cypher()
    _execute_batch(driver, bridge_stmts, batch_size)
    counts["bridges"] = len(bridge_stmts)
    logger.info(f"Created {counts['bridges']} NDF bridge relationships")

    # Step 6: Load empirical effectiveness from ingestion (if available)
    try:
        empirical_stmts = generate_empirical_effectiveness_cypher()
        _execute_batch(driver, empirical_stmts, batch_size)
        counts["empirical_edges"] = len(empirical_stmts)
        logger.info(f"Created {counts['empirical_edges']} empirical effectiveness edges from ingestion")
    except Exception as e:
        logger.warning(f"Empirical effectiveness population failed (non-fatal): {e}")
        counts["empirical_edges"] = 0

    # Step 7: Load full alignment matrices (if available)
    try:
        matrix_stmts = generate_alignment_matrix_cypher()
        _execute_batch(driver, matrix_stmts, batch_size)
        counts["alignment_matrix_edges"] = len(matrix_stmts)
        logger.info(f"Created {counts['alignment_matrix_edges']} alignment matrix edges")
    except Exception as e:
        logger.warning(f"Alignment matrix population failed (non-fatal): {e}")
        counts["alignment_matrix_edges"] = 0

    total = sum(counts.values())
    logger.info(f"DSP graph population complete: {total} total operations")
    return counts


def generate_empirical_effectiveness_cypher() -> List[str]:
    """
    Load empirical archetype→mechanism effectiveness from ingestion_merged_priors.json
    and generate EMPIRICALLY_EFFECTIVE edges with real data.
    """
    import json
    from pathlib import Path

    priors_path = Path("data/learning/ingestion_merged_priors.json")
    if not priors_path.exists():
        logger.info("ingestion_merged_priors.json not found, skipping empirical edges")
        return []

    with open(priors_path) as f:
        priors = json.load(f)

    matrix = priors.get("global_effectiveness_matrix", {})
    if not matrix:
        return []

    statements = []
    for archetype, mechanisms in matrix.items():
        arch_id = f"{archetype}_archetype" if not archetype.endswith("_archetype") else archetype
        for mechanism, data in mechanisms.items():
            if isinstance(data, dict):
                rate = data.get("success_rate", 0)
                sample = data.get("sample_size", 0)
                cats = data.get("categories_seen", 0)
            else:
                rate = float(data) if data else 0
                sample = 0
                cats = 0

            if rate > 0 and sample > 10:
                stmt = (
                    f'MERGE (a:DSPConstruct {{construct_id: "{arch_id}"}}) '
                    f'MERGE (m:DSPConstruct {{construct_id: "{mechanism}"}}) '
                    f'MERGE (a)-[r:EMPIRICALLY_EFFECTIVE]->(m) '
                    f'SET r.success_rate = {rate:.4f}, '
                    f'r.sample_size = {sample}, '
                    f'r.categories_seen = {cats}, '
                    f'r.source = "937M_review_ingestion", '
                    f'r.confidence = "ingestion_derived"'
                )
                statements.append(stmt)

    # Also load category-level matrices
    cat_matrices = priors.get("category_effectiveness_matrices", {})
    for category, arch_data in cat_matrices.items():
        if not isinstance(arch_data, dict):
            continue
        cat_id = f"cat_{category.lower()}"
        for archetype, mechanisms in arch_data.items():
            if not isinstance(mechanisms, dict):
                continue
            arch_id = f"{archetype}_archetype" if not archetype.endswith("_archetype") else archetype
            for mechanism, data in mechanisms.items():
                if isinstance(data, dict):
                    rate = data.get("success_rate", 0)
                    sample = data.get("sample_size", 0)
                else:
                    rate = float(data) if data else 0
                    sample = 0

                if rate > 0 and sample > 5:
                    stmt = (
                        f'MERGE (a:DSPConstruct {{construct_id: "{arch_id}"}}) '
                        f'MERGE (m:DSPConstruct {{construct_id: "{mechanism}"}}) '
                        f'MERGE (c:DSPConstruct {{construct_id: "{cat_id}"}}) '
                        f'MERGE (a)-[r:EFFECTIVE_IN_CATEGORY {{category: "{category}"}}]->(m) '
                        f'SET r.success_rate = {rate:.4f}, '
                        f'r.sample_size = {sample}, '
                        f'r.source = "category_ingestion"'
                    )
                    statements.append(stmt)

    logger.info(f"Generated {len(statements)} empirical effectiveness Cypher statements")
    return statements


def generate_alignment_matrix_cypher() -> List[str]:
    """
    Load the 7 alignment matrices from customer_ad_alignment.py and
    generate edges for every cell with value > 0.3.
    """
    statements = []

    try:
        import adam.intelligence.customer_ad_alignment as caa_module

        # Matrix name → (module-level constant name, relationship type)
        matrix_configs = [
            ("MOTIVATION_VALUE_ALIGNMENT", "ALIGNS_WITH_VALUE"),
            ("DECISION_STYLE_LINGUISTIC_ALIGNMENT", "RESPONDS_TO_STYLE"),
            ("REGULATORY_EMOTIONAL_ALIGNMENT", "RESONATES_WITH_EMOTION"),
            ("ARCHETYPE_PERSONALITY_ALIGNMENT", "PREFERS_PERSONALITY"),
            ("MECHANISM_SUSCEPTIBILITY", "SUSCEPTIBLE_TO"),
            ("COGNITIVE_COMPLEXITY_ALIGNMENT", "MATCHES_COMPLEXITY"),
            ("SOCIAL_PERSUASION_ALIGNMENT", "RESPONDS_TO_TECHNIQUE"),
        ]

        for matrix_name, rel_type in matrix_configs:
            matrix = getattr(caa_module, matrix_name, None)
            if matrix is None or not isinstance(matrix, dict):
                logger.debug(f"Matrix {matrix_name} not found in customer_ad_alignment module")
                continue

            for row_key, col_data in matrix.items():
                if not isinstance(col_data, dict):
                    continue
                for col_key, value in col_data.items():
                    if isinstance(value, (int, float)) and value > 0.3:
                        src_id = row_key.replace(" ", "_").lower()
                        tgt_id = col_key.replace(" ", "_").lower()
                        stmt = (
                            f'MERGE (src:DSPConstruct {{construct_id: "{src_id}"}}) '
                            f'MERGE (tgt:DSPConstruct {{construct_id: "{tgt_id}"}}) '
                            f'MERGE (src)-[r:{rel_type}]->(tgt) '
                            f'SET r.strength = {value:.3f}, '
                            f'r.matrix = "{matrix_name}", '
                            f'r.source = "customer_ad_alignment_research"'
                        )
                        statements.append(stmt)

    except ImportError:
        logger.info("customer_ad_alignment not available, skipping alignment matrix edges")
    except Exception as e:
        logger.warning(f"Alignment matrix generation failed: {e}")

    logger.info(f"Generated {len(statements)} alignment matrix Cypher statements")
    return statements


# =============================================================================
# Helpers
# =============================================================================

def _reasoning_to_rel_type(reasoning: str) -> str:
    """Map reasoning type string to Neo4j relationship type."""
    mapping = {
        "causal": "CAUSES",
        "mediational": "MEDIATES",
        "moderational": "MODERATES",
        "threshold": "CAUSES",
        "bidirectional": "INTERACTS_WITH",
        "temporal": "TEMPORALLY_MODULATES",
        "conditional": "CONDITIONALLY_CAUSES",
        "inhibitory": "INHIBITS",
        "compensatory": "COMPENSATES",
        "synergistic": "SYNERGIZES_WITH",
        "contextual_moderation": "CONTEXTUALLY_MODERATES",
        "temporal_interaction": "TEMPORALLY_INTERACTS",
        "signal_fusion": "FUSES_WITH",
        "precision_weighted": "PRECISION_WEIGHTS",
        "active_inference": "ACTIVELY_INFERS",
        "correlational": "CORRELATES_WITH",
        "ethical_boundary": "ETHICALLY_BOUNDS",
        "creates_need": "CREATES_NEED",
        "satisfied_by": "SATISFIED_BY",
        "activates_route": "ACTIVATES_ROUTE",
        "requires_quality": "REQUIRES_QUALITY",
        "moderates": "MODERATES",
        "antagonistic": "ANTAGONIZES",
        "cooperative": "COOPERATIVELY_BOOSTS",
    }
    return mapping.get(reasoning, "RELATES_TO")


def _execute_batch(driver, statements: List[str], batch_size: int = 100):
    """Execute Cypher statements in batches."""
    for i in range(0, len(statements), batch_size):
        batch = statements[i:i + batch_size]
        with driver.session() as session:
            for stmt in batch:
                try:
                    session.run(stmt)
                except Exception as e:
                    logger.warning(f"Cypher execution failed: {e}")
                    logger.debug(f"Failed statement: {stmt[:200]}")
