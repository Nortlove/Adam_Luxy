"""
DSP Enrichment Engine — Main Pipeline Orchestrator
=====================================================

Complete pipeline: impression bid request -> enriched inventory score.

This is the top-level orchestrator that chains:
    1. Signal extraction (ImpressionContext)
    2. State inference (PsychologicalStateVector)
    3. NDF bridge (ADAM NDF profile)
    4. Strategy generation (PersuasionStrategy)
    5. Inventory scoring (InventoryEnrichmentScore)
    6. Ethical boundary enforcement

Integrates with ADAM's atom DAG and inferential chain system when available.

Latency budget: <100ms for real-time bidding (fast mode)
                 <200ms with atom enrichment (full mode)
"""

import logging
import time
from typing import Any, Dict, List, Optional

from adam.dsp.models import (
    ImpressionContext,
    PsychologicalStateVector,
    PersuasionStrategy,
    InventoryEnrichmentScore,
    MechanismType,
    PsychologicalDomain,
    VulnerabilityType,
    CreativeFormat,
    EmotionalVehicle,
    PersuasionRoute,
)
from adam.dsp.signal_registry import build_signal_registry
from adam.dsp.state_inference import StateInferenceEngine
from adam.dsp.strategy_generation import StrategyGenerationEngine
from adam.dsp.inventory_scoring import InventoryEnrichmentScoringEngine
from adam.dsp.ethical_boundary import EthicalBoundaryEngine
from adam.dsp.ndf_bridge import (
    state_vector_to_ndf,
    merge_ndf_profiles,
    state_vector_to_request_context,
)

logger = logging.getLogger(__name__)


class DSPEnrichmentPipeline:
    """
    Complete pipeline: impression bid request -> enriched inventory score.

    Modes:
        fast: DSP engines only (~50ms) — for strict RTB latency
        full: DSP engines + ADAM atom DAG + inferential chains (~200ms)
    """

    def __init__(
        self,
        construct_registry: Dict = None,
        edge_registry: Dict = None,
    ):
        # Initialize registries
        self.signal_registry = build_signal_registry()
        self.construct_registry = construct_registry or {}
        self.edge_registry = edge_registry or {}

        # Initialize engines
        self.state_engine = StateInferenceEngine(
            self.signal_registry, self.construct_registry, self.edge_registry,
        )
        self.strategy_engine = StrategyGenerationEngine(
            self.edge_registry, self.construct_registry,
        )
        self.scoring_engine = InventoryEnrichmentScoringEngine()
        self.ethical_engine = EthicalBoundaryEngine()

    def enrich_impression(
        self,
        ctx: ImpressionContext,
        ad_category: str = "",
        mode: str = "fast",
        adam_ndf_prior: Optional[Dict[str, float]] = None,
        adam_mechanisms: Optional[List[str]] = None,
        adam_chains: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Full enrichment pipeline for a single impression.

        Args:
            ctx: ImpressionContext with all observable signals
            ad_category: Category of the ad being considered
            mode: "fast" (DSP only) or "full" (DSP + ADAM)
            adam_ndf_prior: Optional NDF profile from ADAM's historical intelligence
            adam_mechanisms: Optional mechanism recommendations from ADAM atom DAG
            adam_chains: Optional inferential chains from ADAM theory graph

        Returns:
            dict with: state, strategy, score, ethical_check, reasoning_trace,
            enrichment_multiplier, approved, ndf_profile, timing_ms
        """
        start_time = time.time()

        # Step 1: Infer psychological state from behavioral signals
        state = self.state_engine.infer_state(ctx)

        # Step 2: Generate NDF profile and merge with ADAM prior if available
        dsp_ndf = state_vector_to_ndf(state)
        if adam_ndf_prior:
            merged_ndf = merge_ndf_profiles(dsp_ndf, adam_ndf_prior, dsp_weight=0.6)
        else:
            merged_ndf = dsp_ndf

        # Use ADAM prior NDF from context if provided
        if ctx.prior_ndf_profile:
            merged_ndf = merge_ndf_profiles(dsp_ndf, ctx.prior_ndf_profile, dsp_weight=0.5)

        # Step 3: Generate optimal persuasion strategy
        strategy = self.strategy_engine.generate_strategy(
            state, ctx,
            atom_mechanisms=adam_mechanisms,
            inferential_chains=adam_chains,
        )

        # Step 4: Score inventory enrichment premium
        score = self.scoring_engine.score_impression(strategy, state, ctx)

        # Step 5: Ethical boundary check
        ethical = self.ethical_engine.evaluate(state, strategy, ad_category)

        # Step 6: Compile full reasoning trace
        reasoning_trace = self._compile_reasoning_trace(
            ctx, state, strategy, score, ethical, merged_ndf,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "state": state,
            "strategy": ethical.get("modified_strategy") or strategy,
            "score": score,
            "ethical_check": ethical,
            "reasoning_trace": reasoning_trace,
            "enrichment_multiplier": score.enrichment_multiplier,
            "approved": ethical["approved"],
            "ndf_profile": merged_ndf,
            "timing_ms": round(elapsed_ms, 2),
            "mode": mode,
        }

    def get_registry_stats(self) -> Dict[str, int]:
        """Return counts for all registries."""
        return {
            "behavioral_signals": len(self.signal_registry),
            "psychological_constructs": len(self.construct_registry),
            "causal_edges": len(self.edge_registry),
            "vulnerability_types": len(VulnerabilityType),
            "mechanism_types": len(MechanismType),
            "psychological_domains": len(PsychologicalDomain),
            "creative_formats": len(CreativeFormat),
            "emotional_vehicles": len(EmotionalVehicle),
            "persuasion_routes": len(PersuasionRoute),
        }

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _compile_reasoning_trace(
        self,
        ctx: ImpressionContext,
        state: PsychologicalStateVector,
        strategy: PersuasionStrategy,
        score: InventoryEnrichmentScore,
        ethical: Dict,
        ndf_profile: Dict[str, float],
    ) -> Dict[str, Any]:
        """Compile the full reasoning trace for transparency."""
        return {
            "impression_signals": {
                "session_phase": ctx.session_phase,
                "estimated_cognitive_load": ctx.estimated_cognitive_load,
                "estimated_processing_mode": ctx.estimated_processing_mode,
                "estimated_chronotype_state": ctx.estimated_chronotype_state,
                "device_type": ctx.device_type.value,
                "content_category": ctx.content_category.value,
            },
            "inferred_state": {
                "regulatory_frame": state.get_dominant_motivational_frame(),
                "processing_route": state.get_optimal_processing_route(),
                "cognitive_load": round(state.cognitive_load, 3),
                "attention_level": round(state.attention_level, 3),
                "construal_level": round(state.construal_level, 3),
                "personality_dominant": max(
                    [
                        ("O", state.openness),
                        ("C", state.conscientiousness),
                        ("E", state.extraversion),
                        ("A", state.agreeableness),
                        ("N", state.neuroticism),
                    ],
                    key=lambda x: x[1],
                )[0],
                "vulnerability_flags": [v.value for v in state.vulnerability_flags],
                "vulnerability_severity": round(state.vulnerability_severity, 3),
            },
            "ndf_profile": {k: round(v, 3) for k, v in ndf_profile.items()},
            "strategy": strategy.to_dict(),
            "enrichment": score.to_dict(),
            "ethical": ethical,
            "mechanism_chain": strategy.mechanism_chain,
            "reasoning": strategy.reasoning_trace,
        }
