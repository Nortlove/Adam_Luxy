# =============================================================================
# ADAM v3: Advanced Cognitive Intelligence Layers
# Location: src/v3/__init__.py
# =============================================================================

"""
ADAM V3 COGNITIVE INTELLIGENCE

Six advanced cognitive layers for emergent psychological intelligence:

1. Emergence Engine - Discovers novel psychological constructs
2. Causal Discovery - Infers causal relationships from data
3. Temporal Dynamics - Models psychological state evolution
4. Meta-Cognitive Reasoning - "Thinking about thinking"
5. Narrative Session - Manages user journey narratives
6. Mechanism Interactions - Models mechanism synergies/conflicts
"""

from src.v3.emergence.engine import (
    EmergenceEngine,
    EmergentInsight,
    EmergenceType,
    get_emergence_engine,
)

from src.v3.causal.discovery import (
    CausalDiscoveryEngine,
    CausalGraph,
    CausalEdge,
    CausalRelationType,
    get_causal_discovery_engine,
)

from src.v3.temporal.dynamics import (
    TemporalDynamicsEngine,
    StateTrajectory,
    TemporalPhase,
    InterventionWindow,
    get_temporal_dynamics_engine,
)

from src.v3.metacognitive.reasoning import (
    MetaCognitiveEngine,
    ReasoningTrace,
    ReasoningStrategy,
    ConfidenceLevel,
    get_metacognitive_engine,
)

from src.v3.narrative.session import (
    NarrativeSessionEngine,
    NarrativePhase,
    UserSession,
    NarrativeArc,
    get_narrative_session_engine,
)

from src.v3.interactions.mechanism import (
    MechanismInteractionEngine,
    MechanismCombination,
    InteractionType,
    get_mechanism_interaction_engine,
)


__all__ = [
    # Emergence
    "EmergenceEngine",
    "EmergentInsight",
    "EmergenceType",
    "get_emergence_engine",
    
    # Causal
    "CausalDiscoveryEngine",
    "CausalGraph",
    "CausalEdge",
    "CausalRelationType",
    "get_causal_discovery_engine",
    
    # Temporal
    "TemporalDynamicsEngine",
    "StateTrajectory",
    "TemporalPhase",
    "InterventionWindow",
    "get_temporal_dynamics_engine",
    
    # MetaCognitive
    "MetaCognitiveEngine",
    "ReasoningTrace",
    "ReasoningStrategy",
    "ConfidenceLevel",
    "get_metacognitive_engine",
    
    # Narrative
    "NarrativeSessionEngine",
    "NarrativePhase",
    "UserSession",
    "NarrativeArc",
    "get_narrative_session_engine",
    
    # Mechanism Interactions
    "MechanismInteractionEngine",
    "MechanismCombination",
    "InteractionType",
    "get_mechanism_interaction_engine",
]
