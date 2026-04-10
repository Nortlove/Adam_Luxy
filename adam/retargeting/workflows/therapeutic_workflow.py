# =============================================================================
# Therapeutic Retargeting Engine — LangGraph Orchestration Workflow
# Location: adam/retargeting/workflows/therapeutic_workflow.py
# Spec: Enhancement #33, Section F.2
# =============================================================================

"""
LangGraph workflow for the Therapeutic Retargeting Loop.

Nodes:
1. diagnose_barrier — Run barrier diagnostic engine
2. check_rupture — Evaluate if rupture repair is needed
3. check_suppression — Evaluate if sequence should stop
4. select_mechanism — Run Bayesian mechanism selector
5. build_touch — Construct therapeutic touch with creative spec
6. generate_creative — Invoke copy generation with mechanism spec
7. update_priors — Update Bayesian posteriors at all hierarchy levels

Edges:
- diagnose_barrier → check_rupture
- check_rupture → (pause | check_suppression)
- check_suppression → (suppress | select_mechanism)
- select_mechanism → build_touch
- build_touch → generate_creative
- generate_creative → update_priors
- update_priors → END
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)

# LangGraph is an optional dependency — the orchestrator works without it
try:
    from langgraph.graph import StateGraph, END

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False
    logger.debug("LangGraph not installed. Workflow will use direct orchestration.")


class TherapeuticState(TypedDict, total=False):
    """State passed through the LangGraph workflow."""

    # Input
    user_id: str
    brand_id: str
    archetype_id: str
    bilateral_edge: Dict[str, float]
    behavioral_signals: Dict[str, float]
    touch_history: List[Dict]
    context: Dict[str, str]
    brand_name: str

    # Intermediate state
    diagnosis: Optional[Dict[str, Any]]
    rupture: Optional[Dict[str, Any]]
    suppression: Optional[Dict[str, Any]]
    selected_mechanism: Optional[str]
    mechanism_confidence: Optional[float]
    mechanism_rationale: Optional[str]

    # Output
    touch: Optional[Dict[str, Any]]
    creative_spec: Optional[Dict[str, Any]]
    sequence_status: str
    levels_updated: int

    # Control flow
    should_pause: bool
    should_suppress: bool
    error: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

async def diagnose_barrier_node(state: TherapeuticState) -> TherapeuticState:
    """Run barrier diagnostic engine."""
    from adam.retargeting.engines.barrier_diagnostic import (
        ConversionBarrierDiagnosticEngine,
    )

    engine = ConversionBarrierDiagnosticEngine()
    try:
        diagnosis = await engine.diagnose(
            user_id=state["user_id"],
            brand_id=state["brand_id"],
            archetype_id=state["archetype_id"],
            bilateral_edge=state.get("bilateral_edge", {}),
            behavioral_signals=state.get("behavioral_signals", {}),
            touch_history=state.get("touch_history", []),
            context=state.get("context"),
        )
        state["diagnosis"] = diagnosis.model_dump()
    except Exception as e:
        logger.error("Barrier diagnosis failed: %s", e)
        state["error"] = str(e)
        state["diagnosis"] = None

    return state


async def check_rupture_node(state: TherapeuticState) -> TherapeuticState:
    """Evaluate if rupture repair is needed."""
    from adam.retargeting.engines.rupture_detector import RuptureDetector

    detector = RuptureDetector()
    assessment = detector.assess(
        touch_history=state.get("touch_history", []),
        behavioral_signals=state.get("behavioral_signals", {}),
        archetype_id=state.get("archetype_id", ""),
    )

    state["rupture"] = {
        "type": assessment.rupture_type.value,
        "severity": assessment.severity,
        "repair_action": assessment.repair_action,
        "min_pause_hours": assessment.min_pause_hours,
    }

    if assessment.repair_action in ("pause", "suppress"):
        state["should_pause"] = True
        state["sequence_status"] = "paused"

    return state


async def check_suppression_node(state: TherapeuticState) -> TherapeuticState:
    """Evaluate suppression rules."""
    # Suppression is checked by the orchestrator before entering the workflow.
    # This node handles any additional checks.
    if state.get("should_pause") or state.get("should_suppress"):
        return state

    state["should_suppress"] = False
    state["should_pause"] = False
    return state


async def select_mechanism_node(state: TherapeuticState) -> TherapeuticState:
    """Run Bayesian mechanism selection."""
    diag = state.get("diagnosis")
    if not diag:
        state["selected_mechanism"] = "evidence_proof"
        state["mechanism_confidence"] = 0.3
        state["mechanism_rationale"] = "No diagnosis available; defaulting."
        return state

    state["selected_mechanism"] = diag.get("recommended_mechanism", "evidence_proof")
    state["mechanism_confidence"] = diag.get("mechanism_confidence", 0.5)
    state["mechanism_rationale"] = diag.get("mechanism_rationale", "")
    return state


async def build_touch_node(state: TherapeuticState) -> TherapeuticState:
    """Construct therapeutic touch from diagnosis + mechanism."""
    diag = state.get("diagnosis", {})
    state["touch"] = {
        "mechanism": state.get("selected_mechanism", "evidence_proof"),
        "barrier": diag.get("primary_barrier", "intention_action_gap"),
        "scaffold_level": diag.get("recommended_scaffold_level", 2),
        "archetype": state.get("archetype_id", ""),
        "narrative_chapter": len(state.get("touch_history", [])) + 1,
    }
    return state


async def generate_creative_node(state: TherapeuticState) -> TherapeuticState:
    """Generate creative specification.

    In full implementation, this calls CopyGenerationService. For now,
    it builds the creative spec dict that the service would consume.
    """
    touch = state.get("touch", {})
    diag = state.get("diagnosis", {})

    state["creative_spec"] = {
        "mechanism": touch.get("mechanism"),
        "barrier_context": touch.get("barrier"),
        "archetype_id": state.get("archetype_id"),
        "brand_name": state.get("brand_name", ""),
        "scaffold_level": touch.get("scaffold_level"),
        "argument_mode": (
            "claude_generated"
            if touch.get("mechanism") == "claude_argument"
            else "template"
        ),
    }
    return state


async def update_priors_node(state: TherapeuticState) -> TherapeuticState:
    """Update Bayesian posteriors at all hierarchy levels.

    This is a placeholder — actual updates happen in the orchestrator's
    process_outcome_and_get_next() after outcome observation.
    """
    state["levels_updated"] = 0
    state["sequence_status"] = state.get("sequence_status", "active")
    return state


# ---------------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------------

def build_therapeutic_workflow():
    """Build the LangGraph therapeutic retargeting workflow.

    Returns compiled workflow, or None if LangGraph is not available.
    """
    if not _LANGGRAPH_AVAILABLE:
        logger.warning(
            "LangGraph not available. Use TherapeuticSequenceOrchestrator "
            "directly for orchestration."
        )
        return None

    workflow = StateGraph(TherapeuticState)

    # Add nodes
    workflow.add_node("diagnose_barrier", diagnose_barrier_node)
    workflow.add_node("check_rupture", check_rupture_node)
    workflow.add_node("check_suppression", check_suppression_node)
    workflow.add_node("select_mechanism", select_mechanism_node)
    workflow.add_node("build_touch", build_touch_node)
    workflow.add_node("generate_creative", generate_creative_node)
    workflow.add_node("update_priors", update_priors_node)

    # Entry point
    workflow.set_entry_point("diagnose_barrier")

    # Edges
    workflow.add_edge("diagnose_barrier", "check_rupture")

    workflow.add_conditional_edges(
        "check_rupture",
        lambda state: "pause" if state.get("should_pause") else "continue",
        {"pause": END, "continue": "check_suppression"},
    )

    workflow.add_conditional_edges(
        "check_suppression",
        lambda state: "suppress" if state.get("should_suppress") else "continue",
        {"suppress": END, "continue": "select_mechanism"},
    )

    workflow.add_edge("select_mechanism", "build_touch")
    workflow.add_edge("build_touch", "generate_creative")
    workflow.add_edge("generate_creative", "update_priors")
    workflow.add_edge("update_priors", END)

    return workflow.compile()
