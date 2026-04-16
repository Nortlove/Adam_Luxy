"""
StackAdapt Creative Intelligence Service
==========================================

Engine behind the <50ms creative intelligence endpoint.

Architecture: 5-Level Bilateral Cascade
    Level 1 — Archetype Prior         (< 2ms,  in-memory Thompson posteriors)
    Level 2 — Category Posterior      (2-10ms, BayesianPrior graph nodes)
    Level 3 — Bilateral Edge Intel    (10-30ms, BRAND_CONVERTED edge dimensions)
    Level 4 — Inferential Transfer    (30-100ms, ad-side profile reasoning)
    Level 5 — Full Atom Reasoning     (100-500ms, AoT DAG — future)

The prediction power comes from the edge, not the archetype label.
The edge dimensions ARE the creative intelligence.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from adam.api.stackadapt.bilateral_cascade import (
    CreativeIntelligence,
    run_bilateral_cascade,
)
from adam.api.stackadapt.decision_cache import (
    DecisionContext,
    get_decision_cache,
)
from adam.intelligence.gradient_fields import GradientIntelligence
from adam.constants import (
    EXTERNAL_ARCHETYPES,
    INTERNAL_ARCHETYPES,
    MECHANISMS,
    resolve_archetype,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class CreativeIntelligenceService:
    """
    Pre-loads all required data at init; serves creative intelligence in <50ms.

    The core engine is the bilateral cascade (bilateral_cascade.py).
    This service is the thin adapter between the cascade and the HTTP API.
    """

    def __init__(self):
        self._priors: Optional[Dict[str, Any]] = None
        self._fast_lookup: Optional[Dict[str, Any]] = None
        self._pipeline = None
        self._graph_cache = None
        self._request_count = 0
        self._total_latency_ms = 0.0
        self._initialized = False

    def initialize(self) -> None:
        """Load all data into memory. Call once at server startup."""
        start = time.time()

        priors_path = _PROJECT_ROOT / "data" / "learning" / "ingestion_merged_priors.json"
        if priors_path.exists():
            try:
                with open(priors_path) as f:
                    self._priors = json.load(f)
                logger.info("Loaded ingestion_merged_priors.json (%d keys)", len(self._priors))
            except Exception as e:
                logger.warning("Failed to load priors: %s", e)

        lookup_path = _PROJECT_ROOT / "data" / "effectiveness_index" / "fast_lookup_tables.json"
        if lookup_path.exists():
            try:
                with open(lookup_path) as f:
                    self._fast_lookup = json.load(f)
                logger.info("Loaded fast_lookup_tables.json")
            except Exception as e:
                logger.warning("Failed to load fast lookup: %s", e)

        try:
            from adam.dsp.pipeline import DSPEnrichmentPipeline
            self._pipeline = DSPEnrichmentPipeline()
            logger.info("DSPEnrichmentPipeline initialized")
        except Exception as e:
            logger.warning("DSPEnrichmentPipeline not available: %s", e)

        try:
            from adam.api.stackadapt.graph_cache import get_graph_cache
            self._graph_cache = get_graph_cache()
            logger.info(
                "Graph cache loaded: %s",
                {k: v for k, v in self._graph_cache.get_health().items()
                 if k != "initialized"},
            )
        except Exception as e:
            logger.warning("Graph cache not available: %s", e)

        self._initialized = True
        elapsed = (time.time() - start) * 1000
        logger.info("CreativeIntelligenceService initialized in %.1fms", elapsed)

    @property
    def is_ready(self) -> bool:
        return self._initialized

    @property
    def avg_latency_ms(self) -> float:
        if self._request_count == 0:
            return 0.0
        return self._total_latency_ms / self._request_count

    # =========================================================================
    # Core method — delegates to bilateral cascade
    # =========================================================================

    def get_creative_intelligence(
        self,
        segment_id: str,
        content_category: str = "",
        device_type: str = "desktop",
        page_url: str = "",
        time_of_day: int = 12,
        day_of_week: str = "monday",
        product_category: str = "",
        brand_name: str = "",
        asin: str = "",
        buyer_id: str = "",
        # Additional OpenRTB signals for impression state resolution
        page_title: str = "",
        referrer: str = "",
        page_keywords: Optional[List[str]] = None,
        iab_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Core method: segment_id + context -> creative parameters.

        Runs the 5-level bilateral cascade. Creative parameters are derived
        from BRAND_CONVERTED edge evidence, not lookup tables.
        """
        start = time.perf_counter()

        # Parse archetype from segment_id using the same regex the cascade
        # uses. Must be set early because both _persist_decision and the
        # response formatting need the correctly-resolved archetype.
        from adam.api.stackadapt.bilateral_cascade import _parse_segment_id
        _parsed_arch, _, _parsed_cat = _parse_segment_id(segment_id)
        archetype = resolve_archetype(_parsed_arch)

        # Track placement URL for inventory learning (offline crawler uses this)
        if page_url:
            try:
                from adam.intelligence.page_intelligence import get_inventory_tracker
                get_inventory_tracker().record_placement(page_url)
            except Exception:
                pass

        # Auto-resolve ASIN and brand for known campaign categories
        _CAMPAIGN_DEFAULTS = {
            "luxury_transportation": {
                "asin": "lux_luxy_ride",
                "brand_name": "LUXY Ride",
            },
        }
        resolved_category = product_category or content_category or ""
        if not asin and resolved_category in _CAMPAIGN_DEFAULTS:
            defaults = _CAMPAIGN_DEFAULTS[resolved_category]
            asin = defaults["asin"]
            if not brand_name:
                brand_name = defaults["brand_name"]
        # Also resolve from segment_id if category is embedded
        if not asin:
            from adam.api.stackadapt.bilateral_cascade import _parse_segment_id
            _, _, parsed_cat = _parse_segment_id(segment_id)
            if parsed_cat and parsed_cat in _CAMPAIGN_DEFAULTS:
                defaults = _CAMPAIGN_DEFAULTS[parsed_cat]
                asin = defaults["asin"]
                if not brand_name:
                    brand_name = defaults["brand_name"]

        # Generate decision_id BEFORE the cascade so we can persist context
        decision_id = self._generate_decision_id(segment_id, buyer_id, asin)

        # Run the bilateral cascade — this is where all the intelligence lives
        cascade_result = run_bilateral_cascade(
            segment_id=segment_id,
            graph_cache=self._graph_cache,
            asin=asin or None,
            device_type=device_type,
            time_of_day=time_of_day,
            iab_category=content_category or product_category or None,
            buyer_id=buyer_id or None,
            page_url=page_url or None,
            # Additional OpenRTB signals for impression state resolution
            page_title=page_title,
            referrer=referrer,
            keywords=page_keywords,
            iab_categories=iab_categories,
        )

        # Optional DSP enrichment (adds device/temporal context)
        dsp_info = self._run_dsp_if_available(
            device_type, page_url, time_of_day, day_of_week,
            product_category or content_category,
        )

        # Build copy guidance from cascade result
        copy_guidance = self._build_copy_guidance(cascade_result, brand_name)

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._request_count += 1
        self._total_latency_ms += elapsed_ms

        # ──────────────────────────────────────────────────────────────
        # COUNTERFACTUAL ANALYSIS — what if we'd used a different mechanism?
        # ──────────────────────────────────────────────────────────────
        counterfactual = self._compute_counterfactual(cascade_result, content_category or product_category)

        # Enrich copy guidance with gradient-driven creative directions
        copy_guidance = self._enrich_copy_guidance(copy_guidance, cascade_result)

        # ──────────────────────────────────────────────────────────────
        # PSYCHOLOGICAL ARBITRAGE — where ADAM sees value the market misses
        # ──────────────────────────────────────────────────────────────
        arbitrage_result = self._compute_arbitrage(
            cascade_result, content_category or product_category, buyer_id,
        )

        # ──────────────────────────────────────────────────────────────
        # SESSION STATE ESTIMATION — adapt to where buyer IS RIGHT NOW
        # ──────────────────────────────────────────────────────────────
        session_state = self._update_session_state(buyer_id, cascade_result)

        # ──────────────────────────────────────────────────────────────
        # PERSIST DECISION CONTEXT for the learning loop.
        #
        # When a conversion webhook arrives hours later, the outcome
        # handler retrieves this context to credit the RIGHT archetype,
        # the RIGHT mechanism, and update the RIGHT buyer profile.
        # ──────────────────────────────────────────────────────────────
        self._persist_decision(
            decision_id=decision_id,
            cascade_result=cascade_result,
            segment_id=segment_id,
            asin=asin,
            buyer_id=buyer_id,
            content_category=content_category,
            product_category=product_category,
        )

        # ──────────────────────────────────────────────────────────────
        # REAL-TIME DECISION ENGINE — Fused persuasion optimization
        # Composes ALL signals (page, environmental, causal, drift)
        # into a single optimized persuasion recommendation.
        # ──────────────────────────────────────────────────────────────
        persuasion_decision = None
        try:
            from adam.intelligence.realtime_decision_engine import compute_persuasion_decision
            persuasion_decision = compute_persuasion_decision(
                page_url=page_url, page_title=page_title,
                referrer=referrer, keywords=page_keywords,
                iab_categories=iab_categories,
                device_type=device_type, time_of_day=time_of_day,
                segment_id=segment_id, archetype=cascade_result.evidence_source,
                asin=asin, buyer_id=buyer_id,
                product_category=product_category or content_category,
                brand_name=brand_name,
            )
        except Exception:
            pass

        # Adapt cascade result to API response format
        result = self._format_response(
            cascade_result, copy_guidance, dsp_info, elapsed_ms,
            segment_id=segment_id, asin=asin, brand_name=brand_name,
            decision_id=decision_id,
            counterfactual=counterfactual,
            arbitrage_result=arbitrage_result,
            session_state=session_state,
        )

        # Enrich response with the decision engine output
        if persuasion_decision:
            result["persuasion_intelligence"] = {
                "primary_mechanism": persuasion_decision.primary_mechanism,
                "secondary_mechanism": persuasion_decision.secondary_mechanism,
                "framing": persuasion_decision.framing,
                "tone": persuasion_decision.tone,
                "construal_level": persuasion_decision.construal_level,
                "urgency_level": persuasion_decision.urgency_level,
                "emotional_intensity": persuasion_decision.emotional_intensity,
                "copy_length": persuasion_decision.copy_length,
                "what_to_say": persuasion_decision.what_to_say,
                "what_not_to_say": persuasion_decision.what_not_to_say,
                "page_already_provides": persuasion_decision.page_already_provides,
                "ad_must_address": persuasion_decision.ad_must_address,
                "mechanism_reasoning": persuasion_decision.mechanism_reasoning,
                "page_state_summary": persuasion_decision.page_state_summary,
                "confidence": persuasion_decision.confidence,
                "expected_lift_pct": persuasion_decision.expected_lift_pct,
                "bid_premium_pct": persuasion_decision.bid_premium_pct,
                "evidence_sources": persuasion_decision.evidence_sources,
                "environmental_mods": persuasion_decision.environmental_mods,
                "decision_ms": persuasion_decision.decision_ms,
                "mechanism_scores": persuasion_decision.mechanism_scores,
            }

        return result

    def _format_response(
        self,
        ci: CreativeIntelligence,
        copy_guidance: Dict[str, Any],
        dsp_info: Optional[Dict[str, Any]],
        elapsed_ms: float,
        segment_id: str = "",
        asin: str = "",
        brand_name: str = "",
        decision_id: str = "",
        counterfactual: Optional[Any] = None,
        arbitrage_result: Optional[Any] = None,
        session_state: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Convert CreativeIntelligence dataclass to API response dict."""

        # DSP-derived persuasion route and emotional vehicle
        if dsp_info and dsp_info.get("strategy"):
            strategy = dsp_info["strategy"]
            pr = getattr(strategy, "persuasion_route", None)
            ev = getattr(strategy, "emotional_vehicle", None)
            pr_val = pr.value if hasattr(pr, "value") else str(pr or "mixed")
            ev_val = ev.value if hasattr(ev, "value") else str(ev or "neutral")
            copy_length = getattr(strategy, "copy_length", ci.copy_length)
        else:
            pr_val = "central" if ci.tone == "authoritative" else "peripheral"
            ev_val = "excitement" if ci.urgency_level > 0.5 else "trust"
            copy_length = ci.copy_length

        # Map social_proof_density float to string
        sp_density = "high" if ci.social_proof_density > 0.7 else (
            "moderate" if ci.social_proof_density > 0.4 else "low"
        )
        detail_level = "high" if ci.construal_level == "concrete" else (
            "low" if ci.construal_level == "abstract" else "moderate"
        )

        result: Dict[str, Any] = {
            "creative_parameters": {
                "primary_mechanism": ci.primary_mechanism,
                "secondary_mechanism": ci.secondary_mechanism,
                "framing": ci.framing,
                "construal_level": ci.construal_level,
                "social_proof_density": sp_density,
                "detail_level": detail_level,
                "urgency": "high" if ci.urgency_level > 0.6 else (
                    "low" if ci.urgency_level < 0.3 else "moderate"
                ),
                "tone": ci.tone,
                "headline_strategy": self._headline_strategy(ci.primary_mechanism),
                "cta_style": self._cta_style(ci.primary_mechanism),
                "persuasion_route": pr_val,
                "emotional_vehicle": ev_val,
                "copy_length": copy_length,
            },
            "ndf_profile": self._ndf_from_cascade(ci),
            "copy_guidance": copy_guidance,
            "expected_lift": {
                "ctr_lift_pct": ci.ctr_lift_pct,
                "conversion_lift_pct": ci.conversion_lift_pct,
                "confidence": ci.evidence_source,
                "evidence_source": ci.evidence_source,
                "sample_size": ci.sample_size,
            },
            "mechanism_chain": [
                m for m, _ in sorted(ci.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
            ][:5] if ci.mechanism_scores else [ci.primary_mechanism, ci.secondary_mechanism],
            "reasoning_trace": ci.reasoning,
            "decision_id": decision_id,
            "segment_metadata": {
                "archetype": archetype,  # From _parse_segment_id, resolved
                "segment_id": segment_id,
                "cascade_level": ci.cascade_level,
                "evidence_source": ci.evidence_source,
            },
            "timing_ms": round(elapsed_ms, 2),
        }

        # Synergy guidance (from cascade's antagonism checks)
        synergy_warnings = [r for r in ci.reasoning if r.startswith("Synergy:")]
        if synergy_warnings:
            result["mechanism_guidance"] = {
                "synergies": [],
                "avoid_combinations": synergy_warnings,
            }

        # Gradient intelligence (from Level 3 + gradient field)
        if ci.gradient_intelligence:
            gi = ci.gradient_intelligence
            result["gradient_intelligence"] = {
                "optimization_priorities": [
                    {
                        "dimension": p.dimension,
                        "current": p.current_value,
                        "optimal": p.optimal_value,
                        "gradient": p.gradient,
                        "gap": p.gap,
                        "expected_lift_delta": p.expected_lift_delta,
                        "creative_direction": p.creative_direction,
                    }
                    for p in gi.optimization_priorities
                ],
                "total_expected_lift_delta": gi.total_expected_lift_delta,
                "field_metadata": gi.field_metadata,
            }

        # Information value bidding (from Level 3 + buyer profile)
        if ci.information_value:
            iv = ci.information_value
            result["information_value"] = {
                "information_value": iv.information_value,
                "bid_modifier_pct": iv.bid_modifier_pct,
                "recommended_bid_premium": iv.recommended_bid_premium,
                "exploration_priority": iv.exploration_priority,
                "buyer_confidence": iv.buyer_confidence,
                "buyer_interactions": iv.buyer_interactions,
                "expected_info_gain": iv.expected_info_gain,
                "top_learning_dimensions": dict(
                    sorted(iv.dimension_values.items(), key=lambda x: x[1], reverse=True)[:3]
                ),
                "reasoning": iv.reasoning,
            }

        # Product intelligence (from Level 3+ cascade)
        if ci.edge_count > 0 and ci.cascade_level >= 3:
            result["product_intelligence"] = {
                "asin": asin,
                "edge_count": ci.edge_count,
                "alignment_dimensions": ci.edge_dimensions,
                "intelligence_tier": f"level{ci.cascade_level}_bilateral",
            }
        elif ci.ad_profile and ci.cascade_level >= 4:
            result["product_intelligence"] = {
                "asin": asin,
                "edge_count": 0,
                "alignment_dimensions": None,
                "intelligence_tier": "level4_inferential",
            }

        # Mechanism scores — ranked with confidence values, not just names.
        # This gives StackAdapt visibility into HOW confident each mechanism
        # recommendation is, enabling their own optimization on top of ours.
        if ci.mechanism_scores:
            result["mechanism_scores"] = {
                m: round(s, 4)
                for m, s in sorted(ci.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
            }

        # Context intelligence — page-level psychological profiling.
        # When available, tells StackAdapt what cognitive state the page
        # puts the buyer in, and how mechanism effectiveness shifts.
        if ci.context_intelligence:
            result["context_intelligence"] = ci.context_intelligence

        # Decision probability — the core NDF congruence equation
        if ci.decision_probability:
            dp = ci.decision_probability
            result["decision_probability"] = {
                "purchase_probability": dp.purchase_probability,
                "backfire_risk": dp.backfire_risk,
                "congruent_dimensions": dp.congruent_dimensions,
                "incongruent_dimensions": dp.incongruent_dimensions,
                "dimension_contributions": dp.dimension_contributions,
                "continuous_creative_weights": {
                    "framing_weight": dp.framing_weight,
                    "construal_weight": dp.construal_weight,
                    "urgency_weight": dp.urgency_weight,
                    "social_proof_weight": dp.social_proof_weight,
                    "depth_weight": dp.depth_weight,
                    "arousal_weight": dp.arousal_weight,
                    "status_weight": dp.status_weight,
                },
                "reasoning": dp.reasoning,
            }

        # Category deviation from universal — what's unique about this category.
        if ci.category_deviation:
            result["category_deviation"] = ci.category_deviation

        # Mechanism portfolio — MPT-inspired multi-mechanism optimization.
        # When the interaction learner has sufficient observations, returns
        # weighted portfolio instead of single mechanism recommendation.
        if ci.mechanism_portfolio:
            try:
                from adam.learning.mechanism_interactions import get_mechanism_interaction_learner
                learner = get_mechanism_interaction_learner()
                obs_count = len(learner._observation_buffer)
            except Exception:
                obs_count = 0

            result["mechanism_portfolio"] = {
                "portfolio": ci.mechanism_portfolio,
                "observation_count": obs_count,
            }

        # Counterfactual analysis — what would happen with alternative mechanisms
        if counterfactual and counterfactual.alternatives:
            result["counterfactual"] = {
                "chosen_mechanism": counterfactual.chosen_mechanism,
                "chosen_effectiveness": counterfactual.chosen_effectiveness,
                "alternatives": [
                    {
                        "mechanism": a.mechanism,
                        "expected_effectiveness": a.expected_effectiveness,
                        "delta_vs_chosen": a.delta_vs_chosen,
                        "confidence": a.confidence,
                        "reasoning": a.reasoning,
                    }
                    for a in counterfactual.alternatives
                ],
                "chosen_is_optimal": counterfactual.chosen_is_optimal,
                "best_alternative": counterfactual.best_alternative,
                "evidence_depth": counterfactual.evidence_depth,
                "reasoning": counterfactual.reasoning,
            }

        # Arbitrage intelligence — where ADAM sees value the market misses
        if arbitrage_result and arbitrage_result.arbitrage_score != 1.0:
            result["arbitrage"] = {
                "arbitrage_score": arbitrage_result.arbitrage_score,
                "adam_predicted_effectiveness": arbitrage_result.adam_predicted_effectiveness,
                "market_baseline_effectiveness": arbitrage_result.market_baseline_effectiveness,
                "recommended_bid_multiplier": arbitrage_result.recommended_bid_multiplier,
                "alpha_value": arbitrage_result.alpha_value,
                "confidence": arbitrage_result.confidence,
                "arbitrage_drivers": arbitrage_result.arbitrage_drivers,
                "reasoning": arbitrage_result.reasoning,
            }

        # Session state — adapt creative to where buyer IS RIGHT NOW
        if session_state:
            result["session_state"] = {
                "session_phase": session_state.session_phase,
                "observation_count": session_state.observation_count,
                "session_duration_seconds": round(session_state.session_duration_seconds, 1),
                "ndf_adjustments": session_state.to_ndf_adjustments(),
                "creative_adjustments": session_state.to_creative_adjustments(),
                "decision_readiness": round(session_state.decision_readiness, 3),
            }

        return result

    # =========================================================================
    # Decision persistence — links decisions to future outcomes
    # =========================================================================

    def _generate_decision_id(self, segment_id: str, buyer_id: str, asin: str) -> str:
        """Generate a stable decision ID that can be echoed back in webhooks."""
        raw = f"{segment_id}:{buyer_id}:{asin}:{time.time()}"
        return f"dec_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def _persist_decision(
        self,
        decision_id: str,
        cascade_result: CreativeIntelligence,
        segment_id: str,
        asin: str,
        buyer_id: str,
        content_category: str,
        product_category: str,
    ) -> None:
        """Persist decision context so the outcome handler can close the loop.

        This is the critical link between decision time and outcome time.
        Every field stored here is the ACTUAL value used in the decision,
        not an inference from the webhook event.
        """
        ci = cascade_result
        # Use the same regex-based parser the cascade uses. The previous
        # code (.split("_")[0]) truncated multi-word archetypes like
        # "corporate_executive" to "corporate" — a non-existent archetype.
        # Every LUXY decision context was stored with a wrong archetype,
        # causing the outcome handler to credit the wrong BayesianPrior
        # and RESPONDS_TO cells.
        from adam.api.stackadapt.bilateral_cascade import _parse_segment_id
        parsed_archetype, _, _ = _parse_segment_id(segment_id)
        archetype = resolve_archetype(parsed_archetype)

        # Extract gradient priorities if available
        gradient_priorities = []
        if ci.gradient_intelligence:
            gradient_priorities = [
                {
                    "dimension": p.dimension,
                    "gradient": p.gradient,
                    "gap": p.gap,
                    "expected_lift_delta": p.expected_lift_delta,
                }
                for p in ci.gradient_intelligence.optimization_priorities
            ]

        # Extract information value snapshot
        iv_value = 0.0
        buyer_conf = 0.0
        if ci.information_value:
            iv_value = ci.information_value.information_value
            buyer_conf = ci.information_value.buyer_confidence

        # Extract full page context intelligence for learning loop
        ctx_mindset = ""
        ctx_domain = ""
        ctx_decision_style = ""
        ctx_open_channels: List[str] = []
        ctx_closed_channels: List[str] = []
        ctx_activated_needs: Dict[str, float] = {}
        ctx_publisher_authority = 0.0
        ctx_elm_route = ""
        if ci.context_intelligence:
            ctx_mindset = ci.context_intelligence.get("mindset", "")
            ctx_domain = ci.context_intelligence.get("domain", "")
            ds = ci.context_intelligence.get("primed_decision_style", {})
            if ds:
                ctx_decision_style = ds.get("decision_speed", "")
                ctx_elm_route = ds.get("elm_route", "")
            ctx_open_channels = ci.context_intelligence.get("open_channels", [])
            ctx_closed_channels = ci.context_intelligence.get("closed_channels", [])
            ctx_activated_needs = ci.context_intelligence.get("activated_needs", {})
            ctx_publisher_authority = ci.context_intelligence.get("publisher_authority", 0.0)

        ctx = DecisionContext(
            decision_id=decision_id,
            archetype=archetype,
            mechanism_sent=ci.primary_mechanism,
            secondary_mechanism=ci.secondary_mechanism,
            mechanisms_considered=list(ci.mechanism_scores.keys()) if ci.mechanism_scores else [],
            cascade_level=ci.cascade_level,
            evidence_source=ci.evidence_source,
            edge_dimensions=ci.edge_dimensions or {},
            mechanism_scores=ci.mechanism_scores or {},
            framing=ci.framing,
            ndf_profile={},  # Populated by _ndf_from_cascade at response time
            segment_id=segment_id,
            asin=asin,
            buyer_id=buyer_id,
            content_category=content_category,
            product_category=product_category,
            gradient_priorities=gradient_priorities,
            information_value=iv_value,
            buyer_confidence=buyer_conf,
            context_mindset=ctx_mindset,
            context_domain=ctx_domain,
            context_decision_style=ctx_decision_style,
            context_open_channels=ctx_open_channels,
            context_closed_channels=ctx_closed_channels,
            context_activated_needs=ctx_activated_needs,
            context_publisher_authority=ctx_publisher_authority,
            context_elm_route=ctx_elm_route,
            # Page edge dimensions for causal learning (20-dim)
            page_edge_dimensions=ci.context_intelligence.get("page_edge_dimensions", {}) if ci.context_intelligence else {},
            page_edge_scoring_tier=ci.context_intelligence.get("page_edge_scoring_tier", "") if ci.context_intelligence else "",
            page_confidence=ci.context_intelligence.get("page_confidence", 0.0) if ci.context_intelligence else 0.0,
        )

        cache = get_decision_cache()
        cache.persist(ctx)

    # =========================================================================
    # Helpers — thin adapters, no business logic
    # =========================================================================

    def _compute_counterfactual(
        self,
        ci: CreativeIntelligence,
        category: str,
    ) -> Optional[Any]:
        """Compute counterfactual mechanism analysis."""
        if not ci.mechanism_scores or len(ci.mechanism_scores) < 2:
            return None
        try:
            from adam.intelligence.counterfactual_mechanisms import compute_counterfactual_analysis
            return compute_counterfactual_analysis(
                chosen_mechanism=ci.primary_mechanism,
                mechanism_scores=ci.mechanism_scores,
                edge_dimensions=ci.edge_dimensions or None,
                cascade_level=ci.cascade_level,
                category=category,
            )
        except Exception as e:
            logger.debug("Counterfactual analysis skipped: %s", e)
            return None

    def _enrich_copy_guidance(
        self,
        copy_guidance: Dict[str, Any],
        ci: CreativeIntelligence,
    ) -> Dict[str, Any]:
        """Enrich copy guidance with gradient-driven creative directions and reasoning.

        Instead of hardcoded templates, this adds continuous, evidence-weighted
        creative direction from the gradient field. It tells copywriters not
        just "use authority" but "emphasize authority because regulatory_fit
        has the steepest conversion gradient (+0.34) and is currently 0.15
        below optimal for this archetype×category cell."
        """
        gradient_directions: List[str] = []
        mechanism_reasoning: List[str] = []

        # Gradient-driven creative directions
        if ci.gradient_intelligence:
            for p in ci.gradient_intelligence.optimization_priorities:
                direction = (
                    f"{p.dimension}: gradient={p.gradient:+.3f}, "
                    f"gap={p.gap:+.3f} (current={p.current_value:.2f}, "
                    f"optimal={p.optimal_value:.2f}). "
                    f"{p.creative_direction}"
                )
                gradient_directions.append(direction)

        # Mechanism selection reasoning
        if ci.mechanism_scores:
            ranked = sorted(ci.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
            for mech, score in ranked[:3]:
                reason = f"{mech} ({score:.3f})"
                if mech == ci.primary_mechanism:
                    reason += " ← PRIMARY"
                    # Add evidence source
                    if ci.cascade_level >= 3 and ci.edge_count > 0:
                        reason += f" (from {ci.edge_count} bilateral edges)"
                    elif ci.cascade_level == 2:
                        reason += f" (from category posterior, {ci.sample_size} observations)"
                    else:
                        reason += " (from archetype prior)"
                mechanism_reasoning.append(reason)

        # Context-driven reasoning
        if ci.context_intelligence:
            mindset = ci.context_intelligence.get("mindset", "")
            adjustments = ci.context_intelligence.get("mechanism_adjustments", {})
            boosted = [f"{m}(+{(v-1)*100:.0f}%)" for m, v in adjustments.items() if v > 1.05]
            dampened = [f"{m}({(v-1)*100:.0f}%)" for m, v in adjustments.items() if v < 0.95]
            if boosted:
                mechanism_reasoning.append(f"Context ({mindset}) boosts: {', '.join(boosted)}")
            if dampened:
                mechanism_reasoning.append(f"Context ({mindset}) dampens: {', '.join(dampened)}")

        copy_guidance["gradient_creative_directions"] = gradient_directions
        copy_guidance["mechanism_reasoning"] = mechanism_reasoning
        return copy_guidance

    def _compute_arbitrage(
        self,
        ci: CreativeIntelligence,
        category: str,
        buyer_id: str,
    ) -> Optional[Any]:
        """Compute psychological arbitrage score."""
        try:
            from adam.intelligence.psychological_arbitrage import compute_arbitrage

            buyer_conf = 0.0
            if ci.information_value:
                buyer_conf = ci.information_value.buyer_confidence

            gradient_priorities = None
            if ci.gradient_intelligence:
                gradient_priorities = [
                    {"expected_lift_delta": p.expected_lift_delta}
                    for p in ci.gradient_intelligence.optimization_priorities
                ]

            ctx_mindset = ""
            if ci.context_intelligence:
                ctx_mindset = ci.context_intelligence.get("mindset", "")

            return compute_arbitrage(
                cascade_level=ci.cascade_level,
                mechanism_scores=ci.mechanism_scores or {},
                edge_dimensions=ci.edge_dimensions or None,
                buyer_confidence=buyer_conf,
                category=category,
                context_mindset=ctx_mindset,
                gradient_priorities=gradient_priorities,
            )
        except Exception as e:
            logger.debug("Arbitrage computation skipped: %s", e)
            return None

    def _update_session_state(
        self,
        buyer_id: str,
        ci: CreativeIntelligence,
    ) -> Optional[Any]:
        """Update session state estimation for this buyer."""
        if not buyer_id:
            return None
        try:
            from adam.intelligence.session_state import get_session_tracker

            tracker = get_session_tracker()
            buyer_uncertainty = 0.5
            if ci.information_value:
                buyer_uncertainty = 1.0 - ci.information_value.buyer_confidence

            session = tracker.update(
                buyer_id=buyer_id,
                observation_type="impression",
                buyer_uncertainty=buyer_uncertainty,
            )
            return session
        except Exception as e:
            logger.debug("Session state update skipped: %s", e)
            return None

    def _headline_strategy(self, mechanism: str) -> str:
        _MAP = {
            "social_proof": "peer_validation", "authority": "expert_endorsement",
            "scarcity": "limited_availability", "reciprocity": "value_first",
            "commitment": "small_step_first", "liking": "similarity_appeal",
            "unity": "shared_identity", "cognitive_ease": "simple_benefit",
            "curiosity": "intrigue_hook", "loss_aversion": "risk_avoidance",
        }
        return _MAP.get(mechanism, "benefit_led")

    def _cta_style(self, mechanism: str) -> str:
        _MAP = {
            "social_proof": "community_join", "authority": "professional_recommend",
            "scarcity": "act_now", "reciprocity": "claim_gift",
            "commitment": "start_free", "liking": "discover_more",
            "unity": "join_us", "cognitive_ease": "learn_more",
            "curiosity": "find_out", "loss_aversion": "protect_now",
        }
        return _MAP.get(mechanism, "learn_more")

    def _ndf_from_cascade(self, ci: CreativeIntelligence) -> Dict[str, float]:
        """Derive NDF-compatible profile from cascade evidence.

        CRITICAL FIX: At Level 3+, map edge dimensions DIRECTLY to NDF space
        using continuous values. Previously this mapped categorical framing
        (gain/loss/mixed) back to hardcoded NDF values, losing all the
        precision from the bilateral edges. A reg_fit of 0.92 was getting
        mapped to approach_avoidance=0.7 because framing="gain".

        Now: reg_fit=0.92 → approach_avoidance=0.84 (continuous, preserves signal).
        """
        if ci.edge_dimensions:
            # Level 3+: map edge dimensions CONTINUOUSLY to NDF space
            reg_fit = ci.edge_dimensions.get("regulatory_fit", 0.5)
            construal = ci.edge_dimensions.get("construal_fit", 0.5)
            personality = ci.edge_dimensions.get("personality_alignment", 0.5)
            emotional = ci.edge_dimensions.get("emotional_resonance", 0.5)
            value = ci.edge_dimensions.get("value_alignment", 0.5)
            composite = ci.edge_dimensions.get("composite_alignment", 0.5)
            evo = ci.edge_dimensions.get("evolutionary_motive", 0.5)

            return {
                "approach_avoidance": round(2.0 * reg_fit - 1.0, 3),  # [0,1] → [-1,1]
                "temporal_horizon": round(construal, 3),
                "social_calibration": round(personality, 3),
                "uncertainty_tolerance": round(1.0 - emotional * 0.5, 3),
                "status_sensitivity": round(value, 3),
                "cognitive_engagement": round(construal * 0.6 + (1.0 - emotional) * 0.4, 3),
                "arousal_seeking": round(emotional * 0.7 + evo * 0.3, 3),
                "cognitive_velocity": round(composite, 3),
            }

        # Level 1-2: derive from mechanism profile (less precise)
        scores = ci.mechanism_scores
        return {
            "approach_avoidance": round(scores.get("scarcity", 0.5) - scores.get("loss_aversion", 0.5), 3),
            "temporal_horizon": round(scores.get("curiosity", 0.5) * 0.6 + scores.get("cognitive_ease", 0.5) * 0.4, 3),
            "social_calibration": round(scores.get("social_proof", 0.5), 3),
            "uncertainty_tolerance": round(1.0 - scores.get("commitment", 0.5), 3),
            "status_sensitivity": round(scores.get("authority", 0.5), 3),
            "cognitive_engagement": round(scores.get("cognitive_ease", 0.5), 3),
            "arousal_seeking": round(ci.urgency_level, 3),
            "cognitive_velocity": round(0.5, 3),
        }

    def _build_copy_guidance(
        self, ci: CreativeIntelligence, brand_name: str,
    ) -> Dict[str, Any]:
        """Generate copy guidance from cascade result."""
        brand_ref = brand_name or "this product"
        headlines: List[str] = []
        value_props: List[str] = []
        ctas: List[str] = []
        avoid: List[str] = []

        mech = ci.primary_mechanism

        # Mechanism-specific copy templates
        _TEMPLATES = {
            "social_proof": {
                "headlines": ["Trusted by thousands who made the switch", f"See why customers rate {brand_ref} #1"],
                "props": ["Validated by real purchase decisions, not marketing claims"],
                "ctas": ["See what others chose"],
            },
            "authority": {
                "headlines": [f"The expert-recommended choice", "Backed by research. Chosen by professionals."],
                "props": ["Grounded in evidence, trusted by experts"],
                "ctas": ["Learn from the evidence"],
            },
            "scarcity": {
                "headlines": ["Limited availability — high demand", f"Before it's gone: {brand_ref}"],
                "props": ["Exclusive access while supply lasts"],
                "ctas": ["Secure yours now"],
            },
            "reciprocity": {
                "headlines": ["Something for you — no strings attached", f"Start with a free trial today"],
                "props": ["We give first. You decide after."],
                "ctas": ["Claim your free offer"],
            },
            "liking": {
                "headlines": [f"People like you love {brand_ref}", "Made for your kind of beauty routine"],
                "props": ["Built for people who share your values"],
                "ctas": ["See why it fits"],
            },
            "commitment": {
                "headlines": ["Start small. See the difference.", "Your first step to something better"],
                "props": ["Low commitment, high reward"],
                "ctas": ["Try it free"],
            },
            "curiosity": {
                "headlines": [f"What makes {brand_ref} different?", "The science behind the results"],
                "props": ["Discover what others have been finding out"],
                "ctas": ["Find out now"],
            },
            "loss_aversion": {
                "headlines": ["Don't let this slip away", f"What you're missing without {brand_ref}"],
                "props": ["Protect what matters to you"],
                "ctas": ["Don't miss out"],
            },
            "cognitive_ease": {
                "headlines": [f"Simple. Effective. {brand_ref}.", "The easy choice for better results"],
                "props": ["No complexity, just results"],
                "ctas": ["Learn more"],
            },
            "unity": {
                "headlines": [f"Join the {brand_ref} community", "You're one of us"],
                "props": ["Be part of something bigger"],
                "ctas": ["Join us"],
            },
        }

        tmpl = _TEMPLATES.get(mech, _TEMPLATES["social_proof"])
        headlines.extend(tmpl["headlines"])
        value_props.extend(tmpl["props"])
        ctas.extend(tmpl["ctas"])

        # Framing-based avoidance
        if ci.framing == "loss":
            avoid.extend(["overly positive claims", "aspirational language"])
        else:
            avoid.extend(["fear-based messaging", "negative framing"])

        # Enrich from ad-side profile (Level 3+)
        if ci.ad_profile:
            bp = ci.ad_profile.get("brand_personality", {})
            if bp:
                dominant = max(bp, key=lambda k: float(bp[k] or 0), default=None)
                if dominant:
                    value_props.append(f"Align with brand personality: {dominant}")

            framing = ci.ad_profile.get("framing", {})
            if float(framing.get("gain", 0)) > 0.6:
                value_props.append("Product naturally suited for gain framing")
            elif float(framing.get("loss", 0)) > 0.6:
                value_props.append("Product naturally suited for loss-avoidance framing")

        # Edge-evidence enrichment (Level 3)
        if ci.edge_dimensions:
            composite = ci.edge_dimensions.get("composite_alignment", 0)
            if composite > 0.7:
                value_props.append(f"Strong bilateral alignment ({composite:.0%}) — high-confidence creative")
            elif composite < 0.4:
                value_props.append("Low bilateral alignment — test multiple approaches")

        return {
            "headline_templates": headlines,
            "value_propositions": value_props,
            "cta_templates": ctas,
            "avoid": avoid,
        }

    def _run_dsp_if_available(
        self,
        device_type: str,
        page_url: str,
        time_of_day: int,
        day_of_week: str,
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """Run DSP enrichment pipeline if available."""
        if not self._pipeline:
            return None

        try:
            from adam.dsp.models import ImpressionContext, DeviceType

            dt_map = {
                "desktop": DeviceType.DESKTOP,
                "mobile": DeviceType.MOBILE,
                "tablet": DeviceType.TABLET,
                "connected_tv": DeviceType.CONNECTED_TV,
                "smart_tv": DeviceType.SMART_TV,
            }
            device = dt_map.get(device_type.lower(), DeviceType.DESKTOP)

            dow_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6,
            }
            dow = dow_map.get(day_of_week.lower(), 0)

            ctx = ImpressionContext(
                timestamp=time.time(),
                day_of_week=dow,
                local_hour=time_of_day,
                device_type=device,
                page_url=page_url,
                product_category=category,
            )

            return self._pipeline.enrich_impression(
                ctx=ctx, ad_category=category, mode="fast",
            )
        except Exception as e:
            logger.debug("DSP pipeline fast path skipped: %s", e)
            return None

    # =========================================================================
    # Segment listing
    # =========================================================================

    def list_segments(self) -> List[Dict[str, Any]]:
        """Return all available INFORMATIV segments."""
        segments = []

        for archetype in EXTERNAL_ARCHETYPES:
            segments.append({
                "segment_id": f"informativ_{archetype}",
                "name": f"INFORMATIV {archetype.title()}",
                "archetype": archetype,
                "category": "",
                "description": f"Psychological archetype: {archetype}. Bilateral-evidence segment.",
                "top_mechanisms": self._top_mechanisms_for(archetype),
                "expected_ctr_lift_pct": 30.0,
            })

        categories = self._get_available_categories()
        for cat in categories[:25]:
            for archetype in EXTERNAL_ARCHETYPES:
                segments.append({
                    "segment_id": f"informativ_{cat.lower().replace(' ', '_')}_{archetype}",
                    "name": f"INFORMATIV {cat} — {archetype.title()}",
                    "archetype": archetype,
                    "category": cat,
                    "description": f"Category-specific segment: {archetype} in {cat}.",
                    "top_mechanisms": self._top_mechanisms_for(archetype),
                    "expected_ctr_lift_pct": 35.0,
                })

        return segments

    def _top_mechanisms_for(self, archetype: str) -> List[str]:
        """Quick top-3 mechanisms from priors or cascade priors."""
        from adam.api.stackadapt.bilateral_cascade import _ARCHETYPE_MECHANISM_PRIORS
        priors = _ARCHETYPE_MECHANISM_PRIORS.get(archetype, {})
        ranked = sorted(priors.items(), key=lambda x: x[1], reverse=True)
        return [m for m, _ in ranked[:3]]

    # =========================================================================
    # Health
    # =========================================================================

    def get_health(self) -> Dict[str, Any]:
        health = {
            "status": "healthy" if self._initialized else "not_initialized",
            "registries_loaded": self._pipeline is not None,
            "priors_loaded": self._priors is not None,
            "graph_cache_available": self._graph_cache is not None,
            "segments_available": len(EXTERNAL_ARCHETYPES) + len(self._get_available_categories()) * len(EXTERNAL_ARCHETYPES),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "version": "4.0.0",
        }
        if self._graph_cache:
            health["graph_cache"] = self._graph_cache.get_health()

        # Page intelligence infrastructure stats
        try:
            from adam.intelligence.page_intelligence import (
                get_inventory_tracker, get_page_intelligence_cache,
            )
            health["page_intelligence"] = {
                "inventory": get_inventory_tracker().stats,
                "cache": get_page_intelligence_cache().stats,
            }
        except Exception:
            pass

        return health

    def _get_available_categories(self) -> List[str]:
        """Return categories available in the priors data."""
        if self._priors:
            cats = self._priors.get("category_effectiveness_matrices", {})
            return list(cats.keys())
        return [
            "All_Beauty", "Electronics", "Health_and_Personal_Care",
            "Home_and_Kitchen", "Sports_and_Outdoors", "Clothing_Shoes_and_Jewelry",
            "Toys_and_Games", "Books", "Automotive", "Tools_and_Home_Improvement",
        ]


# ── Singleton ──────────────────────────────────────────────────────────────

_service: Optional[CreativeIntelligenceService] = None


def get_creative_intelligence_service() -> CreativeIntelligenceService:
    global _service
    if _service is None:
        _service = CreativeIntelligenceService()
        _service.initialize()
    return _service
