# =============================================================================
# ADAM Intelligence Prefetch Service
# Location: adam/orchestrator/intelligence_prefetch.py
# =============================================================================

"""
INTELLIGENCE PREFETCH SERVICE

Queries the Neo4j graph and corpus priors to build ad_context — the
psychological intelligence dict that all atoms access via
PsychologicalConstructResolver and DSPDataAccessor.

Without this prefetch, atoms resolve all psychological dimensions to
the 0.5 default. With it, atoms receive:

- graph_type_inference: 1.9M GranularType traversal results
- expanded_customer_type: 7-dimension buyer profile
- dimensional_priors: 430+ corpus-aggregated dimensions
- ndf_intelligence: 8-dimension NDF profile
- graph_mechanism_priors: Empirical mechanism effectiveness from RESPONDS_TO edges
- dsp_graph_intelligence: Category moderation, susceptibility, empirical patterns
- corpus_fusion_intelligence: Corpus-derived priors from 937M reviews

This service is the bridge between the graph and the atoms. It turns
47M bilateral edges into actionable intelligence for 24-29 reasoning modules.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntelligencePrefetchService:
    """
    Pre-fetches psychological intelligence from the Neo4j graph and corpus
    priors, assembling the ad_context dict that atoms consume.

    Designed to run ONCE per request, BEFORE the AtomDAG executes.
    Results are passed as ad_context to AtomInput.
    """

    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        self._graph_intel = None
        self._unified_intel = None
        self._learned_priors = None
        self._prior_extraction_service = None

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    async def prefetch(
        self,
        archetype: str,
        category: Optional[str] = None,
        asin: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        buyer_uncertainty: Optional[Dict[str, Any]] = None,
        gradient_field: Optional[Dict[str, float]] = None,
        latency_budget=None,
    ) -> Dict[str, Any]:
        """
        Build the complete ad_context dict by querying all intelligence sources.

        Returns a dict with keys matching what PsychologicalConstructResolver
        and DSPDataAccessor expect. Every key is optional — atoms degrade
        gracefully when a source is unavailable.

        Args:
            archetype: Buyer archetype (e.g., "achiever").
            category: Product category (e.g., "beauty", "electronics").
            asin: Product ASIN for product-specific intelligence.
            user_profile: User profile snapshot (Big Five, regulatory focus, etc.).
            buyer_uncertainty: Per-dimension uncertainty from bilateral cascade.
            gradient_field: Gradient magnitudes from pre-computed fields.
            latency_budget: Optional LatencyBudget for timeout enforcement.
        """
        start = time.monotonic()
        ad_context: Dict[str, Any] = {}
        sources_populated: List[str] = []
        sources_timed_out: List[str] = []

        # Per-fetch timeout (seconds). If budget provided, use it; otherwise 8s default.
        from adam.config.settings import get_settings
        per_fetch_s = get_settings().latency_budget.per_fetch_timeout_ms / 1000.0

        # Circuit breaker — skip Neo4j fetches when circuit is open
        neo4j_breaker = None
        try:
            from adam.infrastructure.resilience.circuit_breaker import get_circuit_breaker
            neo4j_breaker = get_circuit_breaker("neo4j")
        except Exception:
            pass

        sources_circuit_blocked: List[str] = []

        async def _guarded_fetch(name: str, coro_factory, uses_neo4j: bool = True):
            """Run a fetch with timeout + circuit breaker. Returns result or None.

            IMPORTANT: coro_factory is a callable that CREATES the coroutine
            (e.g., lambda: self._fetch_xxx(args)). The coroutine is only created
            after passing budget/circuit checks, preventing coroutine leaks when
            early-exit conditions are met.
            """
            # Circuit breaker check — fail fast when Neo4j is down
            if uses_neo4j and neo4j_breaker and neo4j_breaker.is_open:
                sources_circuit_blocked.append(name)
                return None

            timeout = per_fetch_s
            if latency_budget is not None:
                # Use remaining budget, capped at per-fetch max
                timeout = min(per_fetch_s, latency_budget.remaining_seconds)
                if timeout < 0.001:
                    sources_timed_out.append(name)
                    return None
            try:
                # Create coroutine only NOW (after passing all early-exit checks)
                result = await asyncio.wait_for(coro_factory(), timeout=timeout)
                # Record success with circuit breaker
                if uses_neo4j and neo4j_breaker and result is not None:
                    await neo4j_breaker._on_success(0.0)
                return result
            except asyncio.TimeoutError:
                sources_timed_out.append(name)
                logger.warning("Prefetch source timed out: %s (%.0fms)", name, timeout * 1000)
                if uses_neo4j and neo4j_breaker:
                    await neo4j_breaker._on_failure(f"{name} timeout")
                return None
            except Exception as e:
                logger.warning("Prefetch source failed: %s — %s", name, e)
                if uses_neo4j and neo4j_breaker:
                    await neo4j_breaker._on_failure(str(e))
                return None

        # 0. Bilateral edge dimensions — the RICHEST source (20+ continuous dims)
        if asin:
            edge_dims = await _guarded_fetch(
                "edge_dimensions",
                lambda: self._fetch_bilateral_edge_dimensions(asin, archetype),
            )
            if edge_dims:
                ad_context["edge_dimensions"] = edge_dims
                sources_populated.append("edge_dimensions")

        # 1. Graph mechanism priors — RESPONDS_TO edges with evidence counts
        graph_mech = await _guarded_fetch(
            "graph_mechanism_priors",
            lambda: self._fetch_mechanism_priors(archetype, category),
        )
        if graph_mech:
            ad_context["graph_mechanism_priors"] = graph_mech
            sources_populated.append("graph_mechanism_priors")

        # 2. Archetype NDF profile — CustomerArchetype node properties
        ndf = await _guarded_fetch(
            "ndf_intelligence",
            lambda: self._fetch_archetype_ndf(archetype),
        )
        if ndf:
            ad_context["ndf_intelligence"] = {"profile": ndf}
            sources_populated.append("ndf_intelligence")

        # 3. Expanded customer type — from archetype properties
        expanded = await _guarded_fetch(
            "expanded_customer_type",
            lambda: self._fetch_expanded_type(archetype, user_profile),
        )
        if expanded:
            ad_context["expanded_customer_type"] = {"type": expanded}
            sources_populated.append("expanded_customer_type")

        # 4. Dimensional priors — from learned priors service (sync, fast)
        dim_priors = self._fetch_dimensional_priors(archetype, category)
        if dim_priors:
            ad_context["dimensional_priors"] = dim_priors
            sources_populated.append("dimensional_priors")

        # 5. DSP graph intelligence — empirical effectiveness, category moderation
        dsp_intel = await _guarded_fetch(
            "dsp_graph_intelligence",
            lambda: self._fetch_dsp_intelligence(archetype, category, graph_mech),
        )
        if dsp_intel:
            ad_context["dsp_graph_intelligence"] = dsp_intel
            sources_populated.append("dsp_graph_intelligence")

        # 6. Graph type inference — GranularType matching
        graph_type = await _guarded_fetch(
            "graph_type_inference",
            lambda: self._fetch_graph_type_inference(archetype, user_profile),
        )
        if graph_type:
            ad_context["graph_type_inference"] = graph_type
            sources_populated.append("graph_type_inference")

        # 7. Corpus fusion intelligence — priors from 937M reviews (sync, fast)
        corpus = self._fetch_corpus_fusion(archetype, category)
        if corpus:
            ad_context["corpus_fusion_intelligence"] = corpus
            sources_populated.append("corpus_fusion_intelligence")

        # 8. Theory graph chains — causal State→Need→Mechanism reasoning (sync, in-memory)
        theory = self._fetch_theory_chains(
            ndf_profile=ad_context.get("ndf_intelligence", {}).get("profile"),
            archetype=archetype,
            category=category,
        )
        if theory:
            ad_context["theory_graph_intelligence"] = theory
            sources_populated.append("theory_graph_intelligence")

        # 9. GDS graph algorithm intelligence (Node Similarity, PageRank, etc.)
        gds_intel = await _guarded_fetch(
            "gds_algorithms",
            lambda: self._fetch_gds_algorithms(archetype),
        )
        if gds_intel:
            ad_context["gds_algorithm_intelligence"] = gds_intel
            sources_populated.append("gds_algorithms")

        # 10. Discovered patterns from brand pattern learner
        patterns = await _guarded_fetch(
            "discovered_patterns",
            lambda: self._fetch_discovered_patterns(archetype),
        )
        if patterns:
            ad_context["discovered_patterns"] = patterns
            sources_populated.append("discovered_patterns")

        # 11. Create shared MechanismEffectivenessRegistry from all sources
        # Atoms access this via: get_mechanism_registry(ad_context)
        try:
            from adam.atoms.core.mechanism_registry import create_mechanism_registry
            registry = create_mechanism_registry(ad_context)
            ad_context["_mechanism_registry"] = registry
            if registry.is_populated:
                sources_populated.append("mechanism_registry")
        except Exception as e:
            logger.debug("Failed to create mechanism registry: %s", e)

        # ── Goal Activation Context ──
        # Provides page/domain goal activation data to atoms so they can
        # reason about the nonconscious goal state the page has primed.
        # This enables atoms to adjust their reasoning based on what goals
        # are already active in the reader's mind.
        if buyer_uncertainty and isinstance(buyer_uncertainty, dict):
            # Buyer uncertainty may carry context from the cascade
            goal_data = buyer_uncertainty.get("goal_activation")
            if goal_data:
                ad_context["goal_activation_context"] = goal_data
                sources_populated.append("goal_activation_context")
        # Also inject cumulative goal priming from user profile if available
        if user_profile and user_profile.get("cumulative_goal_priming"):
            ad_context["cumulative_goal_priming"] = user_profile["cumulative_goal_priming"]
            ad_context["impression_domains"] = user_profile.get("impression_domains", [])
            sources_populated.append("cumulative_goal_priming")

        # Metadata for observability
        elapsed_ms = (time.monotonic() - start) * 1000
        ad_context["_prefetch_meta"] = {
            "sources_populated": sources_populated,
            "sources_count": len(sources_populated),
            "sources_timed_out": sources_timed_out,
            "sources_circuit_blocked": sources_circuit_blocked,
            "elapsed_ms": round(elapsed_ms, 2),
            "archetype": archetype,
            "category": category,
            "asin": asin,
        }

        if len(sources_populated) == 0:
            logger.error(
                "Intelligence prefetch returned 0 sources for archetype=%s category=%s asin=%s. "
                "All atoms will resolve to 0.5 defaults. "
                "Timed out: %s. Circuit blocked: %s.",
                archetype, category, asin,
                sources_timed_out, sources_circuit_blocked,
            )

        # Record Prometheus metrics
        try:
            from adam.infrastructure.prometheus import get_metrics
            metrics = get_metrics()
            metrics.prefetch_latency.observe(elapsed_ms / 1000)
            metrics.prefetch_sources.observe(len(sources_populated))
        except Exception:
            pass

        logger.info(
            "Intelligence prefetch complete: %d sources in %.1fms for %s/%s",
            len(sources_populated), elapsed_ms, archetype, category or "unknown",
        )

        return ad_context

    # =========================================================================
    # INDIVIDUAL INTELLIGENCE FETCHERS
    # =========================================================================

    async def _fetch_bilateral_edge_dimensions(
        self, asin: str, archetype: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Query BRAND_CONVERTED edge aggregates for ALL 43 properties.

        This is the RICHEST source of psychological intelligence — direct
        from 47M bilateral edges with 43 properties each. Returns a
        structured dict with core_dimensions, extended_dimensions,
        match_dimensions, metadata_signals, and mechanism_citations.

        When available, PsychologicalConstructResolver uses these as
        priority 1, bypassing NDF compression entirely.
        """
        driver = await self._get_driver()
        if not driver:
            return None

        try:
            # Filter by archetype when available — gives per-archetype edge profile
            # instead of averaging across all buyer types
            archetype_filter = ""
            params = {"asin": asin}
            if archetype:
                archetype_filter = "AND ar.user_archetype = $archetype "
                params["archetype"] = archetype

            query = f"""
            MATCH (pd:ProductDescription {{asin: $asin}})
                  -[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            WHERE bc.composite_alignment IS NOT NULL {archetype_filter}
            WITH count(bc) AS edge_count,
                 // Core alignment dimensions (7)
                 AVG(bc.regulatory_fit_score) AS avg_reg_fit,
                 AVG(bc.construal_fit_score) AS avg_construal_fit,
                 AVG(bc.personality_brand_alignment) AS avg_personality,
                 AVG(bc.emotional_resonance) AS avg_emotional,
                 AVG(bc.value_alignment) AS avg_value,
                 AVG(bc.evolutionary_motive_match) AS avg_evo,
                 AVG(bc.linguistic_style_matching) AS avg_linguistic,
                 AVG(bc.composite_alignment) AS avg_composite,
                 AVG(bc.persuasion_confidence_multiplier) AS avg_confidence,
                 // Extended psychological dimensions (13)
                 AVG(COALESCE(bc.persuasion_susceptibility, 0.5)) AS avg_persuasion_susceptibility,
                 AVG(COALESCE(bc.cognitive_load_tolerance, 0.5)) AS avg_cognitive_load_tolerance,
                 AVG(COALESCE(bc.narrative_transport, 0.5)) AS avg_narrative_transport,
                 AVG(COALESCE(bc.social_proof_sensitivity, 0.5)) AS avg_social_proof_sensitivity,
                 AVG(COALESCE(bc.loss_aversion_intensity, 0.5)) AS avg_loss_aversion_intensity,
                 AVG(COALESCE(bc.temporal_discounting, 0.5)) AS avg_temporal_discounting,
                 AVG(COALESCE(bc.brand_relationship_depth, 0.5)) AS avg_brand_relationship_depth,
                 AVG(COALESCE(bc.autonomy_reactance, 0.5)) AS avg_autonomy_reactance,
                 AVG(COALESCE(bc.information_seeking, 0.5)) AS avg_information_seeking,
                 AVG(COALESCE(bc.mimetic_desire, 0.5)) AS avg_mimetic_desire,
                 AVG(COALESCE(bc.interoceptive_awareness, 0.5)) AS avg_interoceptive_awareness,
                 AVG(COALESCE(bc.cooperative_framing_fit, 0.5)) AS avg_cooperative_framing_fit,
                 AVG(COALESCE(bc.decision_entropy, 0.5)) AS avg_decision_entropy,
                 // Match dimensions (18 — the full 27 minus the 9 above)
                 AVG(COALESCE(bc.appeal_resonance, 0.5)) AS avg_appeal_resonance,
                 AVG(COALESCE(bc.processing_route_match, 0.5)) AS avg_processing_route_match,
                 AVG(COALESCE(bc.implicit_driver_match, 0.5)) AS avg_implicit_driver_match,
                 AVG(COALESCE(bc.lay_theory_alignment, 0.5)) AS avg_lay_theory_alignment,
                 AVG(COALESCE(bc.identity_signaling_match, 0.5)) AS avg_identity_signaling_match,
                 AVG(COALESCE(bc.full_cosine_alignment, 0.5)) AS avg_full_cosine_alignment,
                 AVG(COALESCE(bc.uniqueness_popularity_fit, 0.5)) AS avg_uniqueness_popularity_fit,
                 AVG(COALESCE(bc.mental_simulation_resonance, 0.5)) AS avg_mental_simulation_resonance,
                 AVG(COALESCE(bc.involvement_weight_modifier, 0.5)) AS avg_involvement_weight_modifier,
                 AVG(COALESCE(bc.negativity_bias_match, 0.5)) AS avg_negativity_bias_match,
                 AVG(COALESCE(bc.reactance_fit, 0.5)) AS avg_reactance_fit,
                 AVG(COALESCE(bc.optimal_distinctiveness_fit, 0.5)) AS avg_optimal_distinctiveness_fit,
                 AVG(COALESCE(bc.brand_trust_fit, 0.5)) AS avg_brand_trust_fit,
                 AVG(COALESCE(bc.self_monitoring_fit, 0.5)) AS avg_self_monitoring_fit,
                 AVG(COALESCE(bc.spending_pain_match, 0.5)) AS avg_spending_pain_match,
                 AVG(COALESCE(bc.disgust_contamination_fit, 0.5)) AS avg_disgust_contamination_fit,
                 AVG(COALESCE(bc.anchor_susceptibility_match, 0.5)) AS avg_anchor_susceptibility_match,
                 AVG(COALESCE(bc.mental_ownership_match, 0.5)) AS avg_mental_ownership_match,
                 // Metadata signals
                 AVG(COALESCE(bc.star_rating, 0)) AS avg_star_rating,
                 AVG(COALESCE(bc.helpful_votes, 0)) AS avg_helpful_votes,
                 AVG(COALESCE(bc.verified_purchase_trust, 0.5)) AS avg_verified_purchase_trust,
                 AVG(COALESCE(bc.review_recency_weight, 0.5)) AS avg_review_recency_weight,
                 STDEV(bc.star_rating) AS std_star_rating,
                 STDEV(bc.composite_alignment) AS std_composite,
                 // Mechanism citation aggregates
                 AVG(COALESCE(bc.mech_social_proof, 0)) AS avg_mech_social_proof,
                 AVG(COALESCE(bc.mech_authority, 0)) AS avg_mech_authority,
                 AVG(COALESCE(bc.mech_scarcity, 0)) AS avg_mech_scarcity,
                 AVG(COALESCE(bc.mech_reciprocity, 0)) AS avg_mech_reciprocity,
                 AVG(COALESCE(bc.mech_commitment, 0)) AS avg_mech_commitment,
                 AVG(COALESCE(bc.mech_liking, 0)) AS avg_mech_liking
            WHERE edge_count >= 5
            RETURN edge_count,
                   avg_reg_fit, avg_construal_fit, avg_personality,
                   avg_emotional, avg_value, avg_evo, avg_linguistic,
                   avg_composite, avg_confidence,
                   avg_persuasion_susceptibility, avg_cognitive_load_tolerance,
                   avg_narrative_transport, avg_social_proof_sensitivity,
                   avg_loss_aversion_intensity, avg_temporal_discounting,
                   avg_brand_relationship_depth, avg_autonomy_reactance,
                   avg_information_seeking, avg_mimetic_desire,
                   avg_interoceptive_awareness, avg_cooperative_framing_fit,
                   avg_decision_entropy,
                   avg_appeal_resonance, avg_processing_route_match,
                   avg_implicit_driver_match, avg_lay_theory_alignment,
                   avg_identity_signaling_match, avg_full_cosine_alignment,
                   avg_uniqueness_popularity_fit, avg_mental_simulation_resonance,
                   avg_involvement_weight_modifier, avg_negativity_bias_match,
                   avg_reactance_fit, avg_optimal_distinctiveness_fit,
                   avg_brand_trust_fit, avg_self_monitoring_fit,
                   avg_spending_pain_match, avg_disgust_contamination_fit,
                   avg_anchor_susceptibility_match, avg_mental_ownership_match,
                   avg_star_rating, avg_helpful_votes,
                   avg_verified_purchase_trust, avg_review_recency_weight,
                   std_star_rating, std_composite,
                   avg_mech_social_proof, avg_mech_authority,
                   avg_mech_scarcity, avg_mech_reciprocity,
                   avg_mech_commitment, avg_mech_liking
            """
            async with driver.session() as session:
                result = await session.run(query, **params)
                record = await result.single()

            if not record or not record.get("edge_count"):
                return None

            edge_count = record.get("edge_count", 0)

            # Build structured result with all 43 properties
            core_dimensions = {
                "regulatory_fit": record.get("avg_reg_fit", 0.5),
                "construal_fit": record.get("avg_construal_fit", 0.5),
                "personality_alignment": record.get("avg_personality", 0.5),
                "emotional_resonance": record.get("avg_emotional", 0.5),
                "value_alignment": record.get("avg_value", 0.5),
                "evolutionary_motive": record.get("avg_evo", 0.5),
                "linguistic_style": record.get("avg_linguistic", 0.5),
                "composite_alignment": record.get("avg_composite", 0.5),
            }

            extended_dimensions = {
                "persuasion_susceptibility": record.get("avg_persuasion_susceptibility", 0.5),
                "cognitive_load_tolerance": record.get("avg_cognitive_load_tolerance", 0.5),
                "narrative_transport": record.get("avg_narrative_transport", 0.5),
                "social_proof_sensitivity": record.get("avg_social_proof_sensitivity", 0.5),
                "loss_aversion_intensity": record.get("avg_loss_aversion_intensity", 0.5),
                "temporal_discounting": record.get("avg_temporal_discounting", 0.5),
                "brand_relationship_depth": record.get("avg_brand_relationship_depth", 0.5),
                "autonomy_reactance": record.get("avg_autonomy_reactance", 0.5),
                "information_seeking": record.get("avg_information_seeking", 0.5),
                "mimetic_desire": record.get("avg_mimetic_desire", 0.5),
                "interoceptive_awareness": record.get("avg_interoceptive_awareness", 0.5),
                "cooperative_framing_fit": record.get("avg_cooperative_framing_fit", 0.5),
                "decision_entropy": record.get("avg_decision_entropy", 0.5),
            }

            match_dimensions = {
                "appeal_resonance": record.get("avg_appeal_resonance", 0.5),
                "processing_route_match": record.get("avg_processing_route_match", 0.5),
                "implicit_driver_match": record.get("avg_implicit_driver_match", 0.5),
                "lay_theory_alignment": record.get("avg_lay_theory_alignment", 0.5),
                "identity_signaling_match": record.get("avg_identity_signaling_match", 0.5),
                "full_cosine_alignment": record.get("avg_full_cosine_alignment", 0.5),
                "uniqueness_popularity_fit": record.get("avg_uniqueness_popularity_fit", 0.5),
                "mental_simulation_resonance": record.get("avg_mental_simulation_resonance", 0.5),
                "involvement_weight_modifier": record.get("avg_involvement_weight_modifier", 0.5),
                "negativity_bias_match": record.get("avg_negativity_bias_match", 0.5),
                "reactance_fit": record.get("avg_reactance_fit", 0.5),
                "optimal_distinctiveness_fit": record.get("avg_optimal_distinctiveness_fit", 0.5),
                "brand_trust_fit": record.get("avg_brand_trust_fit", 0.5),
                "self_monitoring_fit": record.get("avg_self_monitoring_fit", 0.5),
                "spending_pain_match": record.get("avg_spending_pain_match", 0.5),
                "disgust_contamination_fit": record.get("avg_disgust_contamination_fit", 0.5),
                "anchor_susceptibility_match": record.get("avg_anchor_susceptibility_match", 0.5),
                "mental_ownership_match": record.get("avg_mental_ownership_match", 0.5),
            }

            metadata_signals = {
                "star_rating": record.get("avg_star_rating", 0),
                "helpful_votes": record.get("avg_helpful_votes", 0),
                "verified_purchase_trust": record.get("avg_verified_purchase_trust", 0.5),
                "review_recency_weight": record.get("avg_review_recency_weight", 0.5),
                "star_rating_std": record.get("std_star_rating") or 0.0,
                "composite_std": record.get("std_composite") or 0.0,
            }

            mechanism_citations = {
                "social_proof": record.get("avg_mech_social_proof", 0),
                "authority": record.get("avg_mech_authority", 0),
                "scarcity": record.get("avg_mech_scarcity", 0),
                "reciprocity": record.get("avg_mech_reciprocity", 0),
                "commitment": record.get("avg_mech_commitment", 0),
                "liking": record.get("avg_mech_liking", 0),
            }

            # Flat dims dict for backward compat (PsychologicalConstructResolver)
            all_dims = {**core_dimensions, **extended_dimensions}

            logger.info(
                "Bilateral edge dimensions: %d core + %d extended + %d match dims "
                "from %d edges for ASIN %s",
                len([v for v in core_dimensions.values() if v is not None and abs(v - 0.5) > 0.001]),
                len([v for v in extended_dimensions.values() if v is not None and abs(v - 0.5) > 0.001]),
                len([v for v in match_dimensions.values() if v is not None and abs(v - 0.5) > 0.001]),
                edge_count, asin,
            )

            return {
                **all_dims,  # Flat keys for backward compat
                "_structured": {
                    "core_dimensions": core_dimensions,
                    "extended_dimensions": extended_dimensions,
                    "match_dimensions": match_dimensions,
                    "metadata_signals": metadata_signals,
                    "mechanism_citations": mechanism_citations,
                    "edge_count": edge_count,
                },
            }

        except Exception as e:
            logger.warning("Failed to fetch bilateral edge dimensions: %s", e)
            return None

    async def _fetch_mechanism_priors(
        self, archetype: str, category: Optional[str] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Query RESPONDS_TO edges for empirical mechanism effectiveness.

        This replaces the hardcoded _ARCHETYPE_MECHANISM_PRIORS dict in the
        bilateral cascade with live graph data backed by evidence counts.
        """
        driver = await self._get_driver()
        if not driver:
            return None

        try:
            query = """
            MATCH (a:CustomerArchetype {name: $archetype})
                  -[r:RESPONDS_TO]->(m:CognitiveMechanism)
            WHERE r.effectiveness IS NOT NULL
            RETURN m.name AS mechanism,
                   r.effectiveness AS effectiveness,
                   r.sample_size AS sample_size,
                   r.confidence AS confidence
            ORDER BY r.effectiveness DESC
            """
            async with driver.session() as session:
                result = await session.run(query, archetype=archetype)
                records = await result.data()

            if not records:
                return None

            priors = {}
            for rec in records:
                mech = rec["mechanism"]
                eff = rec.get("effectiveness", 0.5)
                sample = rec.get("sample_size", 0)
                conf = rec.get("confidence", 0.3)

                # Weight effectiveness by confidence (evidence-backed)
                # Low-evidence priors (sample < 10) get pulled toward 0.5
                if sample and sample < 10:
                    shrinkage = sample / 10.0
                    eff = 0.5 + (eff - 0.5) * shrinkage

                priors[mech] = eff

            logger.debug(
                "Fetched %d mechanism priors for %s (avg eff=%.3f)",
                len(priors), archetype,
                sum(priors.values()) / len(priors) if priors else 0,
            )
            return priors

        except Exception as e:
            logger.warning("Failed to fetch mechanism priors: %s", e)
            return None

    async def _fetch_archetype_ndf(
        self, archetype: str,
    ) -> Optional[Dict[str, float]]:
        """
        Fetch the NDF profile from the CustomerArchetype node.

        Returns the 7+1 NDF dimensions stored directly on the archetype node.
        """
        driver = await self._get_driver()
        if not driver:
            return None

        try:
            query = """
            MATCH (a:CustomerArchetype {name: $archetype})
            RETURN a.approach_avoidance AS approach_avoidance,
                   a.temporal_horizon AS temporal_horizon,
                   a.social_calibration AS social_calibration,
                   a.uncertainty_tolerance AS uncertainty_tolerance,
                   a.status_sensitivity AS status_sensitivity,
                   a.cognitive_engagement AS cognitive_engagement,
                   a.arousal_seeking AS arousal_seeking
            """
            async with driver.session() as session:
                result = await session.run(query, archetype=archetype)
                record = await result.single()

            if not record:
                return None

            ndf = {}
            for dim in [
                "approach_avoidance", "temporal_horizon", "social_calibration",
                "uncertainty_tolerance", "status_sensitivity",
                "cognitive_engagement", "arousal_seeking",
            ]:
                val = record.get(dim)
                if val is not None:
                    ndf[dim] = float(val)

            return ndf if ndf else None

        except Exception as e:
            logger.warning("Failed to fetch archetype NDF: %s", e)
            return None

    async def _fetch_expanded_type(
        self, archetype: str, user_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build expanded customer type from archetype properties and user profile.

        Maps archetype → regulatory_focus, motivation, decision_style, etc.
        """
        driver = await self._get_driver()
        if not driver:
            return None

        try:
            query = """
            MATCH (a:CustomerArchetype {name: $archetype})
            RETURN a.regulatory_focus AS regulatory_focus,
                   a.openness AS openness,
                   a.conscientiousness AS conscientiousness,
                   a.extraversion AS extraversion,
                   a.agreeableness AS agreeableness,
                   a.neuroticism AS neuroticism,
                   a.proportion AS proportion
            """
            async with driver.session() as session:
                result = await session.run(query, archetype=archetype)
                record = await result.single()

            if not record:
                return None

            expanded = {}
            reg = record.get("regulatory_focus")
            if reg:
                expanded["regulatory_focus"] = reg

            # Map Big Five to expanded type dimensions
            openness = record.get("openness")
            conscientiousness = record.get("conscientiousness")
            extraversion = record.get("extraversion")

            if openness is not None:
                if openness > 0.7:
                    expanded["motivation"] = "pure_curiosity"
                elif openness > 0.5:
                    expanded["motivation"] = "mastery_seeking"

            if conscientiousness is not None:
                if conscientiousness > 0.7:
                    expanded["decision_style"] = "analytical_systematic"
                elif conscientiousness > 0.5:
                    expanded["decision_style"] = "maximizing"
                else:
                    expanded["decision_style"] = "satisficing"

            if extraversion is not None:
                if extraversion > 0.7:
                    expanded["social_influence"] = "opinion_leader"
                elif extraversion > 0.5:
                    expanded["social_influence"] = "socially_aware"
                else:
                    expanded["social_influence"] = "informational_seeker"

            # Override with user profile if available (richer source)
            if user_profile:
                for key in ["regulatory_focus", "motivation", "decision_style",
                            "social_influence", "emotional_intensity",
                            "temporal_orientation", "cognitive_load"]:
                    if key in user_profile:
                        expanded[key] = user_profile[key]

            return expanded if expanded else None

        except Exception as e:
            logger.warning("Failed to fetch expanded type: %s", e)
            return None

    def _fetch_dimensional_priors(
        self, archetype: str, category: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch corpus-derived dimensional priors from the LearnedPriorsService.

        These are the 430+ dimensions derived from 937M reviews, providing
        the deepest source of psychological priors.
        """
        try:
            if self._learned_priors is None:
                from adam.core.learning.learned_priors_integration import (
                    get_learned_priors,
                )
                self._learned_priors = get_learned_priors()

            if self._learned_priors is None:
                return None

            priors = {}

            # Get archetype-specific effectiveness data
            warm_start = getattr(self._learned_priors, "_thompson_warm_start", None)
            if warm_start and archetype in warm_start:
                priors["archetype_effectiveness"] = warm_start[archetype]

            # Get category-specific priors
            if category:
                cat_priors = getattr(self._learned_priors, "_category_priors", None)
                if cat_priors and category in cat_priors:
                    priors["category_priors"] = cat_priors[category]

            # Get global archetype distribution
            global_dist = getattr(self._learned_priors, "_global_archetype_dist", None)
            if global_dist:
                priors["archetype_population_proportion"] = global_dist.get(archetype, 0.125)

            # Get NDF population priors
            ndf_pop = getattr(self._learned_priors, "_ndf_population_priors", None)
            if ndf_pop:
                priors["ndf_population_priors"] = ndf_pop

            return priors if priors else None

        except Exception as e:
            logger.debug("Failed to fetch dimensional priors: %s", e)
            return None

    async def _fetch_dsp_intelligence(
        self,
        archetype: str,
        category: Optional[str] = None,
        mechanism_priors: Optional[Dict[str, float]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build DSP graph intelligence — empirical effectiveness, category
        moderation, and mechanism susceptibility.

        Reuses mechanism_priors from _fetch_mechanism_priors() to avoid
        querying RESPONDS_TO edges twice.

        This populates what DSPDataAccessor looks for in
        ad_context["dsp_graph_intelligence"].
        """
        driver = await self._get_driver()
        if not driver:
            return None

        try:
            dsp_intel: Dict[str, Any] = {"has_dsp": True}

            # Empirical effectiveness — reuse already-fetched mechanism priors
            # instead of querying RESPONDS_TO a second time.
            if mechanism_priors:
                empirical = {}
                for mech, eff in mechanism_priors.items():
                    empirical[mech] = {
                        "success_rate": eff,
                        "sample_size": 0,  # Not available from priors dict
                        "confidence": 0.5,
                    }
                dsp_intel["empirical_effectiveness"] = empirical

            # Mechanism synergies from MECHANISM_SYNERGY edges
            synergy_query = """
            MATCH (m1:CognitiveMechanism)-[s:MECHANISM_SYNERGY]->(m2:CognitiveMechanism)
            WHERE s.synergy_score IS NOT NULL
            RETURN m1.name AS mech1, m2.name AS mech2,
                   s.synergy_score AS synergy_score,
                   s.combined_lift AS combined_lift
            ORDER BY s.synergy_score DESC
            LIMIT 20
            """
            async with driver.session() as session:
                result = await session.run(synergy_query)
                synergy_records = await result.data()

            if synergy_records:
                dsp_intel["mechanism_synergies"] = [
                    {
                        "pair": [r["mech1"], r["mech2"]],
                        "synergy_score": r.get("synergy_score", 0.5),
                        "combined_lift": r.get("combined_lift", 0.0),
                    }
                    for r in synergy_records
                ]

            # Category moderation — must be Dict[str, float] mapping mechanism → delta.
            # DSPDataAccessor.get_all_category_moderation() and CategoryModerationHelper
            # both expect {mechanism_id: float_delta} format.
            if category:
                cat_query = """
                MATCH (pc:ProductCategory {name: $category})
                      -[:HAS_ARCHETYPE]->(a:CustomerArchetype {name: $archetype})
                RETURN pc.dominant_persuasion AS dominant_persuasion,
                       a.mech_authority AS mech_authority,
                       a.mech_social_proof AS mech_social_proof,
                       a.mech_scarcity AS mech_scarcity,
                       a.mech_reciprocity AS mech_reciprocity,
                       a.mech_commitment AS mech_commitment
                """
                async with driver.session() as session:
                    result = await session.run(
                        cat_query, category=category, archetype=archetype,
                    )
                    cat_rec = await result.single()

                if cat_rec:
                    # Build mechanism delta dict: deviation from 0.5 baseline
                    cat_mod: Dict[str, float] = {}
                    dominant = cat_rec.get("dominant_persuasion", "")
                    for mech_key in ["mech_authority", "mech_social_proof", "mech_scarcity",
                                     "mech_reciprocity", "mech_commitment"]:
                        val = cat_rec.get(mech_key)
                        if val is not None:
                            mech_name = mech_key.replace("mech_", "")
                            # Delta from 0.5 baseline: positive = category boosts this mechanism
                            cat_mod[mech_name] = round(float(val) - 0.5, 3)
                    # Boost the dominant mechanism
                    if dominant and dominant in cat_mod:
                        cat_mod[dominant] = max(cat_mod.get(dominant, 0), 0.1)
                    if cat_mod:
                        dsp_intel["category_moderation"] = cat_mod

            # Mechanism susceptibility — how receptive this archetype is to each mechanism.
            # DSPDataAccessor.get_susceptibility() expects Dict[str, float].
            # Reuse mechanism_priors (already from RESPONDS_TO) instead of re-querying.
            if mechanism_priors:
                dsp_intel["mechanism_susceptibility"] = {
                    mech: round(float(eff), 3)
                    for mech, eff in mechanism_priors.items()
                }

            return dsp_intel

        except Exception as e:
            logger.warning("Failed to fetch DSP intelligence: %s", e)
            return None

    async def _fetch_graph_type_inference(
        self, archetype: str, user_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Infer the buyer's GranularType from archetype + profile signals.

        Queries the 1.9M GranularType node space to find the best-matching
        type, then returns its mechanism recommendations and value propositions.
        """
        driver = await self._get_driver()
        if not driver:
            return None

        try:
            # Build dimension filters from what we know.
            # GranularType nodes have dimension properties (motivation, decision_style,
            # regulatory_focus, etc.) but NOT an archetype_mapping property.
            # We filter by known dimensions and find the best match.
            filters = []
            params: Dict[str, Any] = {}

            if user_profile:
                for dim_key in ["regulatory_focus", "decision_style", "motivation",
                                "emotional_intensity", "cognitive_load",
                                "temporal_orientation", "social_influence"]:
                    if dim_key in user_profile and user_profile[dim_key]:
                        filters.append(f"gt.{dim_key} = ${dim_key}")
                        params[dim_key] = user_profile[dim_key]

            if not filters:
                # No filters → can't narrow 1.9M types, skip
                return None

            where_clause = " AND ".join(filters)

            query = f"""
            MATCH (gt:GranularType)
            WHERE {where_clause}
            WITH gt LIMIT 1
            OPTIONAL MATCH (gt)-[s:SUSCEPTIBLE_TO]->(vp:ValueProposition)
            OPTIONAL MATCH (gt)-[r:RESONATES_WITH_APPEAL]->(ea:EmotionalAppeal)
            RETURN gt.type_id AS type_id,
                   gt.motivation AS motivation,
                   gt.decision_style AS decision_style,
                   gt.regulatory_focus AS regulatory_focus,
                   gt.emotional_intensity AS emotional_intensity,
                   gt.cognitive_load AS cognitive_load,
                   gt.temporal_orientation AS temporal_orientation,
                   gt.social_influence AS social_influence,
                   COLLECT(DISTINCT {{name: vp.name, score: s.alignment_score}}) AS value_propositions,
                   COLLECT(DISTINCT {{name: ea.name, score: r.resonance_score}}) AS emotional_appeals
            """
            async with driver.session() as session:
                result = await session.run(query, **params)
                record = await result.single()

            if not record or not record.get("type_id"):
                return None

            # Convert lists to dicts keyed by name for resolver compatibility.
            # PsychologicalConstructResolver expects:
            #   graph_value_propositions: Dict[str, float]
            #   graph_emotional_appeals: Dict[str, float]
            #   graph_style_recommendations: Dict[str, float]
            #   graph_technique_recommendations: Dict[str, float]
            vp_list = [vp for vp in (record.get("value_propositions") or []) if vp.get("name")]
            ea_list = [ea for ea in (record.get("emotional_appeals") or []) if ea.get("name")]

            type_inference = {
                "type_id": record["type_id"],
                "dimensions": {
                    "motivation": record.get("motivation"),
                    "decision_style": record.get("decision_style"),
                    "regulatory_focus": record.get("regulatory_focus"),
                    "emotional_intensity": record.get("emotional_intensity"),
                    "cognitive_load": record.get("cognitive_load"),
                    "temporal_orientation": record.get("temporal_orientation"),
                    "social_influence": record.get("social_influence"),
                },
                # Keys must match what PsychologicalConstructResolver expects
                "graph_value_propositions": {
                    vp["name"]: vp.get("score", 0.5) for vp in vp_list
                },
                "graph_emotional_appeals": {
                    ea["name"]: ea.get("score", 0.5) for ea in ea_list
                },
                "graph_style_recommendations": {},  # Populated when style edges exist
                "graph_technique_recommendations": {},  # Populated when technique edges exist
            }

            return type_inference

        except Exception as e:
            logger.warning("Failed to fetch graph type inference: %s", e)
            return None

    def _fetch_corpus_fusion(
        self, archetype: str, category: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch corpus fusion intelligence — priors from 937M reviews.

        Loads from PriorExtractionService if available.
        """
        try:
            from adam.fusion.prior_extraction import PriorExtractionService

            if self._prior_extraction_service is None:
                self._prior_extraction_service = PriorExtractionService()
            service = self._prior_extraction_service
            priors = service.get_mechanism_priors(
                archetype=archetype,
                category=category or "",
            )

            if priors and hasattr(priors, "mechanism_details"):
                return {
                    "mechanism_priors": {
                        name: {
                            "effect_size": detail.effect_size,
                            "alpha": detail.alpha,
                            "beta": detail.beta,
                            "confidence": detail.confidence.value
                            if hasattr(detail.confidence, "value")
                            else str(detail.confidence),
                        }
                        for name, detail in priors.mechanism_details.items()
                    },
                    "source": "corpus_937M",
                }

            return None

        except Exception as e:
            logger.debug("Failed to fetch corpus fusion: %s", e)
            return None

    def _fetch_theory_chains(
        self,
        ndf_profile: Optional[Dict[str, float]] = None,
        archetype: str = "",
        category: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate theory-backed mechanism recommendations by traversing the
        causal theory graph: State → Need → Mechanism.

        Uses generate_chains_local() which runs entirely in-memory from
        pre-defined theoretical links (Kruglanski, Cialdini, Petty & Cacioppo,
        Kahneman, etc.). No Neo4j call required.

        This provides the "WHY" behind mechanism recommendations — grounded
        in academic psychology, not just correlational patterns from reviews.
        """
        if not ndf_profile:
            return None

        try:
            from adam.intelligence.graph.reasoning_chain_generator import (
                generate_chains_local,
            )

            chains = generate_chains_local(
                ndf_profile=ndf_profile,
                archetype=archetype,
                category=category,
                top_k=5,
            )

            if not chains:
                return None

            # Convert chains to serializable dicts
            chain_data = []
            for chain in chains:
                entry = {
                    "mechanism": getattr(chain, "recommended_mechanism", None),
                    "score": getattr(chain, "mechanism_score", 0.0),
                    "confidence": getattr(chain, "confidence", 0.0),
                    "chain_strength": getattr(chain, "chain_strength", 0.0),
                    "active_states": getattr(chain, "active_states", []),
                    "active_needs": getattr(chain, "active_needs", []),
                    "processing_route": getattr(chain, "processing_route", ""),
                }
                chain_data.append(entry)

            # Build mechanism recommendation scores from theory
            theory_mechanism_scores = {}
            for chain in chain_data:
                mech = chain.get("mechanism")
                if mech:
                    # Take highest score if mechanism appears in multiple chains
                    if mech not in theory_mechanism_scores or chain["score"] > theory_mechanism_scores[mech]:
                        theory_mechanism_scores[mech] = chain["score"]

            return {
                "chains": chain_data,
                "mechanism_scores": theory_mechanism_scores,
                "source": "theory_graph_local",
                "chain_count": len(chain_data),
            }

        except ImportError:
            logger.debug("Theory graph generator not available")
            return None
        except Exception as e:
            logger.debug("Failed to generate theory chains: %s", e)
            return None

    async def _fetch_gds_algorithms(
        self, archetype: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch pre-computed graph algorithm results.

        Runs GDS algorithms (Node Similarity, PageRank, Communities) that
        provide intelligence no Cypher query can produce: collaborative
        filtering, influence propagation, community structure.

        GDS methods are synchronous — run in thread pool to avoid blocking
        the async event loop.
        """
        import asyncio

        try:
            from adam.intelligence.graph.gds_runtime import GDSRuntimeService
            svc = GDSRuntimeService()
            results: Dict[str, Any] = {}
            loop = asyncio.get_event_loop()

            # Similar archetypes (collaborative filtering for audience expansion)
            try:
                similar = await loop.run_in_executor(
                    None, svc.find_similar_archetypes, archetype, 5,
                )
                if similar:
                    results["similar_archetypes"] = similar
            except Exception:
                pass

            # Mechanism influence ranking (global PageRank on mechanism graph)
            try:
                influence = await loop.run_in_executor(
                    None, svc.get_mechanism_influence_ranking,
                )
                if influence:
                    results["mechanism_influence"] = influence
            except Exception:
                pass

            # Psychographic communities (Louvain clustering)
            try:
                communities = await loop.run_in_executor(
                    None, svc.detect_psychographic_communities,
                )
                if communities:
                    results["communities"] = communities
            except Exception:
                pass

            return results if results else None

        except ImportError:
            logger.debug("GDS runtime not available")
            return None
        except Exception as e:
            logger.debug("GDS algorithms failed: %s", e)
            return None

    async def _fetch_discovered_patterns(
        self, archetype: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch discovered brand × archetype patterns from the pattern learner.

        These patterns are discovered from outcome data and stored in Neo4j
        but currently never queried at decision time. This bridges that gap.
        """
        try:
            from adam.intelligence.pattern_discovery.brand_pattern_learner import (
                get_brand_pattern_learner,
            )
            learner = get_brand_pattern_learner()

            # Get patterns relevant to this archetype
            patterns = await learner.get_patterns_for_archetype(archetype)
            if not patterns:
                return None

            # Convert to serializable format
            pattern_data = []
            for p in patterns[:10]:  # Cap at 10 most relevant
                entry = {
                    "pattern_type": getattr(p, "pattern_type", "unknown"),
                    "description": getattr(p, "description", ""),
                    "confidence": getattr(p, "confidence", 0.0),
                    "effect_size": getattr(p, "effect_size", 0.0),
                    "recommendation": getattr(p, "actionable_recommendation", ""),
                }
                if hasattr(p, "pattern_type") and hasattr(p.pattern_type, "value"):
                    entry["pattern_type"] = p.pattern_type.value
                pattern_data.append(entry)

            return {
                "patterns": pattern_data,
                "count": len(pattern_data),
                "source": "brand_pattern_learner",
            }

        except ImportError:
            logger.debug("Brand pattern learner not available")
            return None
        except Exception as e:
            logger.debug("Pattern discovery fetch failed: %s", e)
            return None

    # =========================================================================
    # INFRASTRUCTURE
    # =========================================================================

    async def _get_driver(self):
        """Get Neo4j async driver."""
        if self._driver is not None:
            return self._driver

        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if not client.is_connected:
                if not await client.connect():
                    return None
            self._driver = client.driver
            return self._driver
        except Exception:
            return None


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_prefetch_service: Optional[IntelligencePrefetchService] = None


def get_intelligence_prefetch() -> IntelligencePrefetchService:
    """Get or create the singleton IntelligencePrefetchService."""
    global _prefetch_service
    if _prefetch_service is None:
        _prefetch_service = IntelligencePrefetchService()
    return _prefetch_service
