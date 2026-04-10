"""
DSP Impression Enrichment Workflow
====================================

LangGraph StateGraph for real-time DSP impression enrichment.

Nodes:
    1. signal_extraction — Parse ImpressionContext, extract behavioral signals
    2. state_inference — Run StateInferenceEngine → PsychologicalStateVector
    3. ndf_bridge — Map state vector to ADAM NDF profile
    4. atom_enrichment — Run ADAM atom subset for inferential enrichment (full mode)
    5. chain_generation — Generate inferential chains from theory graph
    6. strategy_synthesis — Merge DSP + ADAM into PersuasionStrategy
    7. inventory_scoring — Score CPM premium
    8. ethical_boundary — Enforce vulnerability protections

Modes:
    fast (~50ms): signal_extraction → state_inference → ndf_bridge
                  → strategy_synthesis → inventory_scoring → ethical_boundary
    full (~200ms): All nodes including atom_enrichment and chain_generation
"""

import logging
import time
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW STATE
# =============================================================================

class DSPWorkflowState(TypedDict, total=False):
    """State that flows through the DSP impression enrichment workflow."""

    # Input
    impression_context: Dict[str, Any]
    ad_category: str
    mode: str  # "fast" or "full"
    adam_ndf_prior: Optional[Dict[str, float]]

    # Signal extraction
    extracted_signals: Dict[str, float]
    signal_count: int

    # State inference
    psychological_state: Dict[str, Any]
    state_vector_raw: Any  # PsychologicalStateVector object

    # NDF bridge
    ndf_profile: Dict[str, float]
    merged_ndf: Dict[str, float]

    # Atom enrichment (full mode only)
    atom_mechanisms: List[str]
    atom_confidence: float
    atom_output: Dict[str, Any]

    # Chain generation (full mode only)
    inferential_chains: List[Dict[str, Any]]
    chain_count: int

    # Strategy
    strategy: Dict[str, Any]
    strategy_raw: Any  # PersuasionStrategy object

    # Scoring
    enrichment_score: Dict[str, Any]
    enrichment_multiplier: float
    score_raw: Any  # InventoryEnrichmentScore object

    # Ethical
    ethical_check: Dict[str, Any]
    approved: bool

    # Metadata
    reasoning_trace: List[str]
    timing: Dict[str, float]
    errors: List[str]


# =============================================================================
# WORKFLOW NODES
# =============================================================================

def signal_extraction_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 1: Parse ImpressionContext and extract behavioral signals.
    Validates input and prepares signal dictionary.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])

    try:
        ctx_data = state.get("impression_context", {})

        # Count non-default signals
        signal_count = 0
        extracted = {}
        signal_fields = [
            "scroll_velocity", "scroll_depth", "mouse_velocity", "mouse_max_deviation",
            "click_precision", "touch_pressure", "navigation_directness",
            "comparison_behavior", "backspace_frequency", "time_on_page_seconds",
            "session_duration_seconds", "pages_viewed", "category_changes",
        ]
        for field in signal_fields:
            val = ctx_data.get(field)
            if val is not None and val != 0:
                extracted[field] = val
                signal_count += 1

        # Add derived signals
        extracted["content_sentiment"] = ctx_data.get("content_sentiment", 0.0)
        extracted["content_arousal"] = ctx_data.get("content_arousal", 0.5)
        extracted["content_complexity"] = ctx_data.get("content_complexity", 0.5)
        extracted["local_hour"] = ctx_data.get("local_hour", 12)
        extracted["ad_density"] = ctx_data.get("ad_density", 0.3)

        reasoning.append(f"Signal extraction: {signal_count} behavioral signals extracted from impression.")

    except Exception as e:
        errors.append(f"Signal extraction failed: {e}")
        extracted = {}
        signal_count = 0

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["signal_extraction_ms"] = round(elapsed, 2)

    return {
        **state,
        "extracted_signals": extracted,
        "signal_count": signal_count,
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def state_inference_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 2: Run StateInferenceEngine to produce PsychologicalStateVector.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])

    try:
        from adam.dsp.models import ImpressionContext, DeviceType, ContentCategory, CreativeFormat
        from adam.dsp.state_inference import StateInferenceEngine

        ctx_data = state.get("impression_context", {})

        # Build ImpressionContext from dict
        device_map = {v.value: v for v in DeviceType}
        category_map = {v.value: v for v in ContentCategory}

        ctx = ImpressionContext(
            timestamp=ctx_data.get("timestamp", time.time()),
            day_of_week=ctx_data.get("day_of_week", 0),
            local_hour=ctx_data.get("local_hour", 12),
            device_type=device_map.get(ctx_data.get("device_type", "desktop"), DeviceType.DESKTOP),
            screen_width=ctx_data.get("screen_width", 1920),
            screen_height=ctx_data.get("screen_height", 1080),
            dark_mode=ctx_data.get("dark_mode", False),
            connection_speed_mbps=ctx_data.get("connection_speed_mbps", 50.0),
            content_category=category_map.get(ctx_data.get("content_category", "news"), ContentCategory.NEWS),
            content_sentiment=ctx_data.get("content_sentiment", 0.0),
            content_arousal=ctx_data.get("content_arousal", 0.5),
            content_complexity=ctx_data.get("content_complexity", 0.5),
            ad_density=ctx_data.get("ad_density", 0.3),
            session_duration_seconds=ctx_data.get("session_duration_seconds", 0),
            pages_viewed=ctx_data.get("pages_viewed", 1),
            scroll_depth=ctx_data.get("scroll_depth", 0.0),
            scroll_velocity=ctx_data.get("scroll_velocity", 0.0),
            time_on_page_seconds=ctx_data.get("time_on_page_seconds", 0.0),
            mouse_velocity=ctx_data.get("mouse_velocity", 0.0),
            mouse_max_deviation=ctx_data.get("mouse_max_deviation", 0.0),
            click_precision=ctx_data.get("click_precision", 1.0),
            backspace_frequency=ctx_data.get("backspace_frequency", 0.0),
            touch_pressure=ctx_data.get("touch_pressure", 0.5),
            referrer_type=ctx_data.get("referrer_type", "direct"),
            navigation_directness=ctx_data.get("navigation_directness", 0.5),
            category_changes=ctx_data.get("category_changes", 0),
            comparison_behavior=ctx_data.get("comparison_behavior", 0.0),
            viewability_prediction=ctx_data.get("viewability_prediction", 0.7),
            above_fold=ctx_data.get("above_fold", True),
            product_category=ctx_data.get("product_category", ""),
            brand_name=ctx_data.get("brand_name", ""),
        )

        # Run state inference
        engine = StateInferenceEngine()
        state_vector = engine.infer_state(ctx)

        frame = state_vector.get_dominant_motivational_frame()
        route = state_vector.get_optimal_processing_route()
        reasoning.append(
            f"State inference: regulatory_frame={frame}, route={route}, "
            f"cognitive_load={state_vector.cognitive_load:.2f}, "
            f"attention={state_vector.attention_level:.2f}"
        )

    except Exception as e:
        errors.append(f"State inference failed: {e}")
        state_vector = None
        ctx = None

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["state_inference_ms"] = round(elapsed, 2)

    return {
        **state,
        "psychological_state": state_vector.to_dict() if state_vector else {},
        "state_vector_raw": state_vector,
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def ndf_bridge_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 3: Map PsychologicalStateVector to ADAM NDF profile.
    Merges with prior NDF if available.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])

    try:
        from adam.dsp.ndf_bridge import state_vector_to_ndf, merge_ndf_profiles

        state_vector = state.get("state_vector_raw")
        if state_vector:
            dsp_ndf = state_vector_to_ndf(state_vector)

            adam_prior = state.get("adam_ndf_prior")
            if adam_prior:
                merged = merge_ndf_profiles(dsp_ndf, adam_prior, dsp_weight=0.6)
                reasoning.append(
                    f"NDF bridge: merged DSP inference (60%) with ADAM prior (40%). "
                    f"approach_avoidance={merged.get('approach_avoidance', 0):.2f}"
                )
            else:
                merged = dsp_ndf
                reasoning.append(
                    f"NDF bridge: DSP-only NDF. "
                    f"approach_avoidance={merged.get('approach_avoidance', 0):.2f}"
                )
        else:
            merged = {}
            dsp_ndf = {}

    except Exception as e:
        errors.append(f"NDF bridge failed: {e}")
        dsp_ndf = {}
        merged = {}

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["ndf_bridge_ms"] = round(elapsed, 2)

    return {
        **state,
        "ndf_profile": dsp_ndf,
        "merged_ndf": merged,
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def atom_enrichment_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 4 (full mode only): Run ADAM atom subset for enrichment.
    Uses the NDF profile to get mechanism recommendations from ADAM's
    review-trained intelligence.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])
    mechanisms = []
    confidence = 0.0

    try:
        ndf = state.get("merged_ndf", {})
        if ndf:
            # Try to use ADAM's inferential chain generator
            from adam.intelligence.graph.reasoning_chain_generator import generate_chains_local
            chains = generate_chains_local(
                ndf_profile=ndf,
                context=state.get("impression_context", {}),
                category=state.get("impression_context", {}).get("product_category", ""),
                top_k=5,
            )
            if chains:
                mechanisms = [c.recommended_mechanism for c in chains[:3]]
                confidence = sum(c.confidence for c in chains[:3]) / max(1, len(chains[:3]))
                reasoning.append(
                    f"Atom enrichment: ADAM theory graph recommends {mechanisms}. "
                    f"Confidence: {confidence:.2f}"
                )
            else:
                reasoning.append("Atom enrichment: no chains generated, using DSP-only strategy.")
        else:
            reasoning.append("Atom enrichment: no NDF profile available.")

    except ImportError:
        reasoning.append("Atom enrichment: ADAM chain generator not available.")
    except Exception as e:
        errors.append(f"Atom enrichment failed (non-fatal): {e}")

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["atom_enrichment_ms"] = round(elapsed, 2)

    return {
        **state,
        "atom_mechanisms": mechanisms,
        "atom_confidence": confidence,
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def chain_generation_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 5 (full mode only): Generate inferential chains from theory graph.
    Produces explicit reasoning traces explaining WHY mechanisms work.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])
    chains = []

    try:
        ndf = state.get("merged_ndf", {})
        if ndf:
            from adam.intelligence.graph.reasoning_chain_generator import generate_chains_local
            raw_chains = generate_chains_local(
                ndf_profile=ndf,
                context=state.get("impression_context", {}),
                category=state.get("impression_context", {}).get("product_category", ""),
                top_k=5,
            )
            chains = [c.to_dict() if hasattr(c, "to_dict") else c for c in raw_chains]
            reasoning.append(f"Chain generation: {len(chains)} inferential chains produced.")
    except ImportError:
        reasoning.append("Chain generation: ADAM chain generator not available.")
    except Exception as e:
        errors.append(f"Chain generation failed (non-fatal): {e}")

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["chain_generation_ms"] = round(elapsed, 2)

    return {
        **state,
        "inferential_chains": chains,
        "chain_count": len(chains),
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def strategy_synthesis_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 6: Generate PersuasionStrategy from DSP + ADAM intelligence.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])

    try:
        from adam.dsp.strategy_generation import StrategyGenerationEngine
        from adam.dsp.models import ImpressionContext, DeviceType, ContentCategory

        state_vector = state.get("state_vector_raw")
        ctx_data = state.get("impression_context", {})

        if state_vector:
            # Reconstruct minimal context for strategy engine
            device_map = {v.value: v for v in DeviceType}
            category_map = {v.value: v for v in ContentCategory}
            ctx = ImpressionContext(
                local_hour=ctx_data.get("local_hour", 12),
                device_type=device_map.get(ctx_data.get("device_type", "desktop"), DeviceType.DESKTOP),
                content_category=category_map.get(ctx_data.get("content_category", "news"), ContentCategory.NEWS),
                content_sentiment=ctx_data.get("content_sentiment", 0.0),
                viewability_prediction=ctx_data.get("viewability_prediction", 0.7),
                above_fold=ctx_data.get("above_fold", True),
                ad_density=ctx_data.get("ad_density", 0.3),
            )

            engine = StrategyGenerationEngine()
            strategy = engine.generate_strategy(
                state_vector, ctx,
                atom_mechanisms=state.get("atom_mechanisms"),
                inferential_chains=state.get("inferential_chains"),
            )

            reasoning.append(
                f"Strategy synthesis: frame={strategy.message_frame}, "
                f"route={strategy.persuasion_route.value}, "
                f"confidence={strategy.confidence:.2f}"
            )
        else:
            strategy = None
            reasoning.append("Strategy synthesis: no state vector, skipping.")

    except Exception as e:
        errors.append(f"Strategy synthesis failed: {e}")
        strategy = None

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["strategy_synthesis_ms"] = round(elapsed, 2)

    return {
        **state,
        "strategy": strategy.to_dict() if strategy else {},
        "strategy_raw": strategy,
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def inventory_scoring_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 7: Score CPM premium from psychological enrichment.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])

    try:
        from adam.dsp.inventory_scoring import InventoryEnrichmentScoringEngine
        from adam.dsp.models import ImpressionContext, DeviceType, ContentCategory

        state_vector = state.get("state_vector_raw")
        strategy = state.get("strategy_raw")
        ctx_data = state.get("impression_context", {})

        if state_vector and strategy:
            device_map = {v.value: v for v in DeviceType}
            category_map = {v.value: v for v in ContentCategory}
            ctx = ImpressionContext(
                device_type=device_map.get(ctx_data.get("device_type", "desktop"), DeviceType.DESKTOP),
                content_category=category_map.get(ctx_data.get("content_category", "news"), ContentCategory.NEWS),
                ad_density=ctx_data.get("ad_density", 0.3),
                viewability_prediction=ctx_data.get("viewability_prediction", 0.7),
                above_fold=ctx_data.get("above_fold", True),
            )

            engine = InventoryEnrichmentScoringEngine()
            score = engine.score_impression(strategy, state_vector, ctx)

            reasoning.append(
                f"Inventory scoring: {score.enrichment_multiplier:.2f}x CPM multiplier. "
                f"Enriched CPM: ${score.enriched_cpm:.2f}"
            )
        else:
            score = None
            reasoning.append("Inventory scoring: insufficient data, skipping.")

    except Exception as e:
        errors.append(f"Inventory scoring failed: {e}")
        score = None

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["inventory_scoring_ms"] = round(elapsed, 2)

    return {
        **state,
        "enrichment_score": score.to_dict() if score else {},
        "enrichment_multiplier": score.enrichment_multiplier if score else 1.0,
        "score_raw": score,
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


def ethical_boundary_node(state: DSPWorkflowState) -> DSPWorkflowState:
    """
    Node 8: Enforce ethical constraints and vulnerability protections.
    """
    start = time.time()
    errors = state.get("errors", [])
    reasoning = state.get("reasoning_trace", [])

    try:
        from adam.dsp.ethical_boundary import EthicalBoundaryEngine

        state_vector = state.get("state_vector_raw")
        strategy = state.get("strategy_raw")

        if state_vector and strategy:
            engine = EthicalBoundaryEngine()
            ethical = engine.evaluate(
                state_vector, strategy,
                ad_category=state.get("ad_category", ""),
            )

            if not ethical["approved"]:
                reasoning.append(
                    f"ETHICAL BLOCK: Ad category '{state.get('ad_category', '')}' "
                    f"blocked for vulnerabilities: {ethical['vulnerability_flags']}"
                )
            elif ethical["risk_level"] != "low":
                reasoning.append(
                    f"ETHICAL WARNING: Risk level '{ethical['risk_level']}'. "
                    f"Strategy modified for safety."
                )
            else:
                reasoning.append("Ethical boundary: APPROVED. No vulnerability concerns.")
        else:
            ethical = {"approved": True, "risk_level": "unknown", "audit_trail": []}

    except Exception as e:
        errors.append(f"Ethical boundary check failed: {e}")
        ethical = {"approved": True, "risk_level": "error", "audit_trail": [str(e)]}

    elapsed = (time.time() - start) * 1000
    timing = state.get("timing", {})
    timing["ethical_boundary_ms"] = round(elapsed, 2)
    timing["total_ms"] = sum(v for k, v in timing.items() if k.endswith("_ms") and k != "total_ms")

    return {
        **state,
        "ethical_check": ethical,
        "approved": ethical.get("approved", True),
        "reasoning_trace": reasoning,
        "timing": timing,
        "errors": errors,
    }


# =============================================================================
# ROUTING
# =============================================================================

def should_enrich_with_atoms(state: DSPWorkflowState) -> str:
    """Route to atom enrichment (full mode) or skip to strategy (fast mode)."""
    mode = state.get("mode", "fast")
    if mode == "full":
        return "atom_enrichment"
    return "strategy_synthesis"


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

def build_dsp_impression_workflow() -> StateGraph:
    """
    Build the LangGraph DSP impression enrichment workflow.

    Fast mode (~50ms):
        signal_extraction → state_inference → ndf_bridge → strategy_synthesis
        → inventory_scoring → ethical_boundary

    Full mode (~200ms):
        signal_extraction → state_inference → ndf_bridge → atom_enrichment
        → chain_generation → strategy_synthesis → inventory_scoring → ethical_boundary
    """
    workflow = StateGraph(DSPWorkflowState)

    # Add nodes
    workflow.add_node("signal_extraction", signal_extraction_node)
    workflow.add_node("state_inference", state_inference_node)
    workflow.add_node("ndf_bridge", ndf_bridge_node)
    workflow.add_node("atom_enrichment", atom_enrichment_node)
    workflow.add_node("chain_generation", chain_generation_node)
    workflow.add_node("strategy_synthesis", strategy_synthesis_node)
    workflow.add_node("inventory_scoring", inventory_scoring_node)
    workflow.add_node("ethical_boundary", ethical_boundary_node)

    # Entry point
    workflow.set_entry_point("signal_extraction")

    # Edges — sequential flow
    workflow.add_edge("signal_extraction", "state_inference")
    workflow.add_edge("state_inference", "ndf_bridge")

    # Conditional: fast mode skips atom enrichment + chain generation
    workflow.add_conditional_edges(
        "ndf_bridge",
        should_enrich_with_atoms,
        {
            "atom_enrichment": "atom_enrichment",
            "strategy_synthesis": "strategy_synthesis",
        },
    )

    # Full mode path
    workflow.add_edge("atom_enrichment", "chain_generation")
    workflow.add_edge("chain_generation", "strategy_synthesis")

    # Common path
    workflow.add_edge("strategy_synthesis", "inventory_scoring")
    workflow.add_edge("inventory_scoring", "ethical_boundary")
    workflow.add_edge("ethical_boundary", END)

    return workflow


def compile_dsp_workflow():
    """Compile the DSP impression workflow for execution."""
    workflow = build_dsp_impression_workflow()
    return workflow.compile()


# =============================================================================
# EXECUTOR
# =============================================================================

class DSPImpressionWorkflowExecutor:
    """
    High-level executor for the DSP impression enrichment workflow.

    Usage:
        executor = DSPImpressionWorkflowExecutor()
        result = executor.enrich(impression_context_dict, ad_category="finance", mode="full")
    """

    def __init__(self):
        self._compiled = None

    @property
    def workflow(self):
        if self._compiled is None:
            self._compiled = compile_dsp_workflow()
        return self._compiled

    def enrich(
        self,
        impression_context: Dict[str, Any],
        ad_category: str = "",
        mode: str = "fast",
        adam_ndf_prior: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full DSP enrichment workflow.

        Args:
            impression_context: Dict with all impression signals
            ad_category: Category of the ad being considered
            mode: "fast" (~50ms) or "full" (~200ms with ADAM enrichment)
            adam_ndf_prior: Optional prior NDF from ADAM

        Returns:
            Complete enrichment result with state, strategy, score, ethical check
        """
        initial_state: DSPWorkflowState = {
            "impression_context": impression_context,
            "ad_category": ad_category,
            "mode": mode,
            "adam_ndf_prior": adam_ndf_prior,
            "reasoning_trace": [],
            "timing": {},
            "errors": [],
        }

        # Execute workflow
        result = self.workflow.invoke(initial_state)

        return {
            "state": result.get("psychological_state", {}),
            "ndf_profile": result.get("merged_ndf", {}),
            "strategy": result.get("strategy", {}),
            "enrichment_score": result.get("enrichment_score", {}),
            "enrichment_multiplier": result.get("enrichment_multiplier", 1.0),
            "ethical_check": result.get("ethical_check", {}),
            "approved": result.get("approved", True),
            "inferential_chains": result.get("inferential_chains", []),
            "atom_mechanisms": result.get("atom_mechanisms", []),
            "reasoning_trace": result.get("reasoning_trace", []),
            "timing": result.get("timing", {}),
            "mode": mode,
            "errors": result.get("errors", []),
        }
