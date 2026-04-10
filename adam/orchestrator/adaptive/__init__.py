# =============================================================================
# ADAM Adaptive Graph Orchestration — LangGraph Breakthroughs
# =============================================================================

"""
Novel LangGraph extensions for adaptive, self-modifying computation graphs.

This module contains 6 breakthrough components that extend LangGraph
far beyond its standard capabilities:

Core Components (existing):
  - AdaptiveGraphRewriter: Runtime graph topology modification
  - RuntimeEdgeFactory: Dynamic edge creation based on evidence
  - MetaOrchestrator: Orchestrator-of-orchestrators for workflow selection

Breakthrough Components (new):
  - NeuralAttentionRouter: Attention-based dynamic atom routing
    (atoms emit attention scores that determine downstream activation)
  - EpisodicMemoryStore: Cross-session persistent memory with
    similarity, analogy, and counterfactual retrieval modes
  - SelfImprovementEngine: Recursive self-improvement using UCB1
    bandit over graph configurations with 4 improvement levels

Together these create a computation graph that:
1. Routes dynamically based on evidence (not static DAG)
2. Remembers past decisions and their outcomes
3. Measures its own performance and restructures itself
4. Evolves its architecture over time
"""
