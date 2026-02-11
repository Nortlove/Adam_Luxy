# =============================================================================
# ADAM Graph Intelligence — Living Knowledge Graph + Inferential Intelligence
# =============================================================================

"""
Living Knowledge Graph — Neo4j GDS in the Runtime Path.

This module puts REAL graph algorithms in the decisioning pipeline:
  - Node Similarity (Jaccard): Find similar archetypes
  - Louvain Community Detection: Discover psychographic communities
  - PageRank: Identify most influential mechanisms
  - Betweenness Centrality: Find bridge mechanisms
  - Dijkstra Shortest Path: Optimal mechanism-to-outcome paths

INFERENTIAL INTELLIGENCE (NEW):
  - Theory Graph: PsychologicalState/Need/Route nodes with causal edges
  - Reasoning Chain Generator: NDF → State → Need → Mechanism traversal
  - Zero-Shot Transfer: Theory-based recommendations for unseen contexts
  - Construct-Level Learning: Bayesian updates on theoretical link strengths

The graph is LIVING — it evolves based on outcomes:
  - Edge weights update from observed effectiveness
  - Theoretical link strengths update from construct-level learning
  - New edges emerge from discovered patterns (5 novel types)
  - Weak edges decay and are pruned (temporal decay)
  - Graph projections are managed with TTL-based lifecycle

Novel Edge Types:
  - MECHANISM_SYNERGY: Mechanisms that amplify each other
  - ARCHETYPE_MIGRATION: How archetypes evolve over time
  - TEMPORAL_DECAY: Mechanism effectiveness decay (Ebbinghaus curve)
  - OUTCOME_ATTRIBUTION: Multi-touch mechanism-to-outcome attribution
  - COMPETITIVE_DISPLACEMENT: Which mechanisms replace others

Theory Edge Types:
  - CREATES_NEED: PsychologicalState → PsychologicalNeed
  - SATISFIED_BY: PsychologicalNeed → CognitiveMechanism
  - ACTIVATES_ROUTE: PsychologicalState → ProcessingRoute
  - REQUIRES_QUALITY: ProcessingRoute → CognitiveMechanism
  - MODERATES: ContextCondition → PsychologicalNeed
"""

from adam.intelligence.graph.gds_runtime import (
    GDSRuntimeService,
    GraphProjectionManager,
    get_gds_service,
    NOVEL_EDGE_TYPES,
    GDS_QUERIES,
)

# Inferential Intelligence imports
from adam.intelligence.graph.theory_schema import (
    PSYCHOLOGICAL_STATES,
    PSYCHOLOGICAL_NEEDS,
    PROCESSING_ROUTES,
    CONTEXT_CONDITIONS,
    THEORETICAL_LINKS,
    populate_theory_graph,
)

from adam.intelligence.graph.reasoning_chain_generator import (
    generate_chains,
    generate_chains_local,
    get_best_chain,
    InferentialChain,
    CreativeGuidance,
)

from adam.intelligence.graph.zero_shot_transfer import (
    zero_shot_recommend,
    ZeroShotResult,
    ZeroShotRecommendation,
)

__all__ = [
    # GDS Runtime
    "GDSRuntimeService",
    "GraphProjectionManager",
    "get_gds_service",
    "NOVEL_EDGE_TYPES",
    "GDS_QUERIES",
    # Theory Graph
    "PSYCHOLOGICAL_STATES",
    "PSYCHOLOGICAL_NEEDS",
    "PROCESSING_ROUTES",
    "CONTEXT_CONDITIONS",
    "THEORETICAL_LINKS",
    "populate_theory_graph",
    # Reasoning Chains
    "generate_chains",
    "generate_chains_local",
    "get_best_chain",
    "InferentialChain",
    "CreativeGuidance",
    # Zero-Shot Transfer
    "zero_shot_recommend",
    "ZeroShotResult",
    "ZeroShotRecommendation",
]
