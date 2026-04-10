"""
ADAM DSP Inventory Enrichment Engine
====================================

Transforms commodity impression inventory into premium psychologically-optimized
placements by inferring consumer psychological states from observable behavioral
signals and recommending persuasion strategies matched to those states.

Architecture:
    ImpressionContext (DSP input) → PsychologicalStateVector (inferred state)
    → PersuasionStrategy (recommended creative) → InventoryEnrichmentScore (CPM premium)

Integrated with:
    - Neo4j theory graph (500+ constructs, 160+ causal edges)
    - ADAM Atoms of Thought (30-atom DAG for inferential reasoning)
    - LangGraph real-time impression workflow
    - Thompson Sampling / TheoryLearner for online construct-level learning
"""

from adam.dsp.models import (
    # Enums
    ReasoningType,
    ConfidenceLevel,
    PsychologicalDomain,
    MechanismType,
    SignalSource,
    SignalReliability,
    DeviceType,
    ContentCategory,
    FunnelStage,
    SessionPhase,
    CreativeFormat,
    PersuasionRoute,
    EmotionalVehicle,
    VulnerabilityType,
    # Dataclasses
    EffectSize,
    BehavioralSignal,
    TemporalModulation,
    CreativeImplication,
    ImpressionContext,
    PsychologicalStateVector,
    PersuasionStrategy,
    InventoryEnrichmentScore,
)

from adam.dsp.pipeline import DSPEnrichmentPipeline

# Registries (lazy-loaded builders)
from adam.dsp.signal_registry import build_signal_registry
from adam.dsp.construct_registry import build_construct_registry
from adam.dsp.edge_registry import build_edge_registry

# Graph population
from adam.dsp.graph_population import populate_dsp_graph

__all__ = [
    # Enums
    "ReasoningType",
    "ConfidenceLevel",
    "PsychologicalDomain",
    "MechanismType",
    "SignalSource",
    "SignalReliability",
    "DeviceType",
    "ContentCategory",
    "FunnelStage",
    "SessionPhase",
    "CreativeFormat",
    "PersuasionRoute",
    "EmotionalVehicle",
    "VulnerabilityType",
    # Dataclasses
    "EffectSize",
    "BehavioralSignal",
    "TemporalModulation",
    "CreativeImplication",
    "ImpressionContext",
    "PsychologicalStateVector",
    "PersuasionStrategy",
    "InventoryEnrichmentScore",
    # Pipeline
    "DSPEnrichmentPipeline",
    # Registries
    "build_signal_registry",
    "build_construct_registry",
    "build_edge_registry",
    # Graph
    "populate_dsp_graph",
]
