#!/usr/bin/env python3
"""
OUTCOME HANDLER — Closes the Learning Loop
===========================================

When an outcome arrives (click, conversion, bounce, etc.), this handler:

1. Retrieves the prediction context from the persist step
2. Computes prediction error (predicted_effectiveness vs actual)
3. Updates Thompson Sampling posteriors (Beta distribution update)
4. Updates the meta-orchestrator (which strategy worked)
5. Updates the graph rewriter (which rules helped)
6. Updates Neo4j with outcome attribution edges
7. Updates the ML hybrid extractor ensemble weights
8. Routes learning signals to all 30 atoms via UnifiedLearningHub

This is Phase 4 of the Post-Ingestion Master Plan:
    predict → decide → observe → reason → improve

The system gets STRONGER with every outcome it observes.
"""

import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class OutcomeHandler:
    """
    Processes outcomes and routes learning signals to all system components.
    
    This is the SINGLE entry point for outcome processing. All outcomes
    (from API callbacks, Kafka events, or batch processing) flow through here.
    """
    
    def __init__(self):
        self._outcomes_processed = 0
        self._total_updates = 0
    
    async def process_outcome(
        self,
        decision_id: str,
        outcome_type: str,  # "conversion", "click", "engagement", "bounce", "skip"
        outcome_value: float = 1.0,  # 0-1 scale
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process an outcome and update all learning systems.
        
        Args:
            decision_id: ID of the original decision
            outcome_type: Type of outcome observed
            outcome_value: Outcome value (1.0 = full success, 0.0 = failure)
            metadata: Additional outcome metadata
            
        Returns:
            Summary of all updates performed
        """
        start = time.time()
        metadata = metadata or {}
        
        from adam.config.settings import get_settings
        success_threshold = get_settings().cascade.outcome_success_threshold
        success = outcome_type in ("conversion", "click", "engagement") and outcome_value > success_threshold

        # Track whether decision context was available (from decision cache)
        has_decision_context = metadata.get("decision_context_found", False)
        cascade_level = metadata.get("cascade_level", 0)

        # Extract commonly used fields from metadata
        archetype = metadata.get("archetype", "")
        mechanism_sent = metadata.get("mechanism_sent", "")
        category = metadata.get("product_category", "") or metadata.get("category", "")

        # ── Enhancement #34: Processing Depth ──
        # Classify how deeply the person processed the ad. This determines the
        # observation weight for ALL posterior updates in the pipeline below.
        # UNPROCESSED impressions (< 1s viewport) get weight=0.05, preventing
        # the system from learning wrong lessons from noise.
        processing_depth_weight = 1.0
        processing_depth_str = metadata.get("processing_depth", "")
        try:
            from adam.retargeting.engines.processing_depth import (
                ProcessingDepth,
                classify_processing_depth,
                get_processing_weight,
            )
            if processing_depth_str:
                # Already classified (e.g., by webhook or telemetry pipeline)
                depth = ProcessingDepth(processing_depth_str)
            else:
                # Classify from viewability data in metadata
                viewability_s = metadata.get("viewability_seconds", 0.0)
                clicked = outcome_type in ("click", "conversion")
                video_watched = metadata.get("video_seconds_watched")
                depth = classify_processing_depth(
                    viewability_seconds=viewability_s,
                    clicked=clicked,
                    video_seconds_watched=video_watched,
                )
                processing_depth_str = depth.value
            processing_depth_weight = get_processing_weight(depth)
        except Exception:
            pass  # Default weight=1.0 if processing depth unavailable

        results = {
            "decision_id": decision_id,
            "outcome_type": outcome_type,
            "success": success,
            "decision_context_found": has_decision_context,
            "cascade_level": cascade_level,
            "updates": {},
        }

        results["processing_depth"] = processing_depth_str
        results["processing_depth_weight"] = processing_depth_weight

        # =====================================================================
        # 0. RECORD CAUSAL OBSERVATION
        # Every impression is a micro-experiment. Record the full decision
        # context + outcome so the causal testing engine can discover
        # which page dimensions CAUSE which mechanisms to be effective.
        # =====================================================================
        try:
            from adam.intelligence.causal_learning import record_causal_observation
            causal_obs = record_causal_observation(
                decision_id=decision_id,
                outcome_type=outcome_type,
                outcome_value=outcome_value,
                metadata=metadata,
            )
            if causal_obs:
                results["updates"]["causal_observation"] = {
                    "recorded": True,
                    "has_page_dims": bool(causal_obs.page_edge_dimensions),
                    "mechanism": causal_obs.mechanism_sent,
                }
        except Exception as e:
            logger.debug("Causal observation recording failed: %s", e)

        # =====================================================================
        # 1. UPDATE THOMPSON SAMPLING POSTERIORS
        #
        # CRITICAL FIX: Only credit mechanism_sent (what was actually shown
        # to the buyer), NOT mechanisms_considered (the full exploration set).
        # Previously all considered mechanisms got credit, systematically
        # overcounting evidence in the Beta posteriors.
        #
        # CRITICAL FIX: This is the ONLY place Thompson Sampling is updated.
        # The UnifiedLearningHub's _update_thompson_sampler handler is
        # excluded from OUTCOME_SUCCESS signals to prevent double-counting.
        # =====================================================================
        try:
            results["updates"]["thompson"] = await self._update_thompson(
                decision_id, success, metadata,
                processing_depth_weight=processing_depth_weight,
            )
        except Exception as e:
            logger.warning(f"Thompson update failed: {e}")
            results["updates"]["thompson"] = {"error": str(e)}
        
        # =====================================================================
        # 2. UPDATE META-ORCHESTRATOR (which strategy worked)
        # =====================================================================
        try:
            results["updates"]["meta_orchestrator"] = await self._update_meta_orchestrator(
                decision_id, success, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Meta-orchestrator update failed for {decision_id}: {e}")
            results["updates"]["meta_orchestrator"] = {"error": str(e)}
        
        # =====================================================================
        # 3. UPDATE NEO4J OUTCOME ATTRIBUTION
        # =====================================================================
        try:
            results["updates"]["neo4j"] = await self._update_neo4j_attribution(
                decision_id, outcome_type, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Neo4j attribution update failed for {decision_id}: {e}")
            results["updates"]["neo4j"] = {"error": str(e)}
        
        # =====================================================================
        # 4. UPDATE GRAPH REWRITER (which rules helped)
        # =====================================================================
        try:
            results["updates"]["graph_rewriter"] = await self._update_graph_rewriter(
                decision_id, success, metadata
            )
        except Exception as e:
            logger.warning(f"Graph rewriter update failed for {decision_id}: {e}")
            results["updates"]["graph_rewriter"] = {"error": str(e)}
        
        # =====================================================================
        # 5. ROUTE TO UNIFIED LEARNING HUB (reaches all atoms)
        # =====================================================================
        try:
            results["updates"]["learning_hub"] = await self._route_to_learning_hub(
                decision_id, outcome_type, outcome_value, success, metadata
            )
        except Exception as e:
            logger.warning(f"Learning hub routing failed: {e}")
        
        # =====================================================================
        # 6. UPDATE ML ENSEMBLE WEIGHTS
        # =====================================================================
        try:
            results["updates"]["ml_ensemble"] = await self._update_ml_ensemble(
                decision_id, success, metadata
            )
        except Exception as e:
            logger.warning(f"ML ensemble update failed for {decision_id}: {e}")
            results["updates"]["ml_ensemble"] = {"error": str(e)}
        
        # =====================================================================
        # 7. CONSTRUCT-LEVEL LEARNING (Theory Learner)
        #
        # This is the new inferential intelligence layer. When outcomes arrive,
        # we update the theoretical link strengths — learning which causal
        # theories in the graph are empirically validated by real outcomes.
        #
        # Unlike Thompson Sampling (archetype → mechanism), this learns at
        # the deeper construct level (psychological_state → need → mechanism).
        # =====================================================================
        try:
            results["updates"]["theory_learner"] = await self._update_theory_learner(
                decision_id, success, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Theory learner update failed for {decision_id}: {e}")
            results["updates"]["theory_learner"] = {"error": str(e)}
        
        # =====================================================================
        # 8. DSP IMPRESSION LEARNING
        #
        # When outcomes arrive from DSP impression enrichment, update:
        # - Signal reliability weights (which bidstream signals predict well)
        # - Construct inference accuracy (which constructs predicted outcomes)
        # - Edge strength validation (which causal edges are empirically supported)
        # - Strategy effectiveness (which strategies produced results)
        # =====================================================================
        if metadata.get("source") == "dsp_impression":
            try:
                results["updates"]["dsp_learning"] = await self._update_dsp_learning(
                    decision_id, success, outcome_value, metadata
                )
            except Exception as e:
                logger.warning(f"DSP learning update failed for {decision_id}: {e}")
                results["updates"]["dsp_learning"] = {"error": str(e)}
        
        # =====================================================================
        # 9. COGNITIVE LEARNING SYSTEM (Alignment Matrix Learning)
        #
        # Routes outcomes to the CognitiveLearningSystem which:
        # - Tracks prediction vs outcome for alignment matrices
        # - Discovers correction patterns (motivation-value mismatches, etc.)
        # - Updates alignment matrix edge weights in Neo4j
        # - Feeds Meta-Learner alignment confidence calibration
        # =====================================================================
        try:
            results["updates"]["cognitive_learning"] = await self._update_cognitive_learning(
                decision_id, success, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Cognitive learning update failed for {decision_id}: {e}")
            results["updates"]["cognitive_learning"] = {"error": str(e)}

        # =====================================================================
        # 10. PAGE-CONTEXT-CONDITIONED LEARNING
        #
        # The most powerful learning signal: how does page context modulate
        # mechanism effectiveness? This learns:
        # - "Authority works 80% on deliberative pages, 20% on impulsive"
        # - "Social proof is 40% more effective when page primed conformity"
        # - "Loss aversion backfires when page has closed that channel"
        #
        # This creates the context-awareness that no other system has.
        # =====================================================================
        try:
            results["updates"]["page_context_learning"] = await self._update_page_context_learning(
                decision_id, success, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Page context learning failed for {decision_id}: {e}")
            results["updates"]["page_context_learning"] = {"error": str(e)}

        # =====================================================================
        # 10b. PAGE GRADIENT FIELD ACCUMULATION
        #
        # Accumulates (page_vector, mechanism, barrier, outcome) observations
        # for daily gradient computation. The gradient field tells us:
        # ∂P(conversion)/∂(page_dimension) per (mechanism, barrier) cell —
        # which page dimensions CAUSE mechanism effectiveness.
        # =====================================================================
        page_edge_dims = metadata.get("page_edge_dimensions", {})
        if page_edge_dims and mechanism_sent:
            try:
                from adam.intelligence.page_gradient_fields import get_page_gradient_accumulator
                acc = get_page_gradient_accumulator()
                acc.record_observation(
                    page_dimensions=page_edge_dims,
                    mechanism=mechanism_sent,
                    barrier=metadata.get("barrier_diagnosed", "unknown"),
                    converted=success,
                )
            except Exception as e:
                logger.debug("Page gradient accumulation skipped: %s", e)

        # =====================================================================
        # 11. MECHANISM INTERACTION LEARNING (Portfolio Optimization)
        #
        # Records which mechanisms were co-activated and what the outcome
        # was. Over time this builds the mechanism covariance matrix that
        # enables portfolio optimization: instead of picking one mechanism,
        # the system allocates weights across a portfolio that maximizes
        # expected return while accounting for synergies and antagonisms.
        # =====================================================================
        try:
            results["updates"]["mechanism_interactions"] = await self._update_mechanism_interactions(
                decision_id, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Mechanism interaction update failed for {decision_id}: {e}")
            results["updates"]["mechanism_interactions"] = {"error": str(e)}

        # =====================================================================
        # 11. BUYER UNCERTAINTY PROFILE UPDATE (Information Value Bidding)
        #
        # When an outcome arrives with a buyer_id, update the per-buyer
        # Beta posteriors on each alignment dimension. This narrows uncertainty
        # about this buyer's psychological profile, reducing the information
        # value bid premium for future impressions of this buyer.
        # =====================================================================
        buyer_id = metadata.get("buyer_id", "")
        if buyer_id:
            try:
                results["updates"]["buyer_profile"] = await self._update_buyer_profile(
                    buyer_id, outcome_type, metadata,
                    processing_depth_weight=processing_depth_weight,
                )
            except Exception as e:
                logger.warning(f"Buyer profile update failed for {buyer_id}: {e}")
                results["updates"]["buyer_profile"] = {"error": str(e)}

        # =====================================================================
        # 12. BILATERAL EDGE EVIDENCE UPDATE (Core Asset Self-Improvement)
        #
        # The most critical learning gap: BRAND_CONVERTED edges have 27
        # alignment dimensions computed at ingestion but NEVER updated from
        # live outcomes. This means gradient fields (∂P/∂dimension) go stale
        # and the system's core data asset doesn't compound from experience.
        #
        # This update increments evidence_count on the (archetype, category)
        # cell's aggregate edge statistics and schedules gradient recomputation
        # when enough new evidence accumulates.
        # =====================================================================
        archetype = metadata.get("archetype", "")
        category = metadata.get("product_category", "") or metadata.get("category", "")
        if archetype and category:
            try:
                results["updates"]["bilateral_edge"] = await self._update_bilateral_edge_evidence(
                    archetype, category, success, outcome_value, metadata
                )
            except Exception as e:
                logger.warning(f"Bilateral edge evidence update failed: {e}")
                results["updates"]["bilateral_edge"] = {"error": str(e)}

        # =====================================================================
        # 13. THERAPEUTIC RETARGETING POSTERIOR UPDATE (Enhancement #33)
        #
        # If this outcome is from a retargeting touch (barrier_diagnosed and
        # therapeutic_mechanism present in metadata), update the hierarchical
        # Bayesian posteriors at ALL 5 levels (corpus → category → brand →
        # campaign → sequence). This teaches both the system-wide posteriors
        # (future campaigns benefit) and the campaign-specific posteriors
        # (this sequence improves on the next touch).
        # =====================================================================
        barrier = metadata.get("barrier_diagnosed", "")
        therapeutic_mech = metadata.get("therapeutic_mechanism", "")
        if barrier and therapeutic_mech and archetype:
            try:
                from adam.retargeting.engines.prior_manager import get_prior_manager
                _prior_mgr = get_prior_manager()
                retargeting_context = {
                    "category": category,
                    "brand_id": metadata.get("asin", ""),
                    "campaign_id": metadata.get("segment_id", ""),
                    "sequence_id": metadata.get("sequence_id", ""),
                }
                levels_updated = _prior_mgr.update_all_levels(
                    mechanism=therapeutic_mech,
                    barrier=barrier,
                    archetype=archetype,
                    reward=outcome_value if success else 0.0,
                    context=retargeting_context,
                    weight=processing_depth_weight,
                )
                results["updates"]["therapeutic_posteriors"] = {
                    "levels_updated": levels_updated,
                    "barrier": barrier,
                    "mechanism": therapeutic_mech,
                    "processing_depth_weight": processing_depth_weight,
                }
            except Exception as e:
                logger.debug(f"Therapeutic posterior update skipped: {e}")
                results["updates"]["therapeutic_posteriors"] = {"skipped": str(e)}

        # =====================================================================
        # 13.5 WITHIN-SUBJECT USER POSTERIOR UPDATE (Enhancement #36)
        #
        # When a retargeting touch has user_id + barrier + mechanism, update
        # the per-user posteriors via UserPosteriorManager. This enables:
        # - Per-user mechanism rankings (what works for THIS person)
        # - Design-effect discounting (correlated observations weighted correctly)
        # - Trajectory analysis (warming/cooling/step_change patterns)
        # - 2-4x statistical power over between-subjects designs
        #
        # The design-effect weight from MixedEffectsEstimator is already
        # applied in step 13 via HierarchicalPriorManager.update_all_levels().
        # Here we update the USER-level posteriors that sit outside the
        # population hierarchy.
        # =====================================================================
        user_id = metadata.get("user_id", "")
        if user_id and barrier and therapeutic_mech:
            try:
                from adam.retargeting.engines.repeated_measures import TrajectoryAnalyzer
                from adam.core.dependencies import LearningComponents, Infrastructure

                infra = Infrastructure.get_instance()
                components = LearningComponents.get_instance(infra)
                user_mgr = components.user_posterior_manager

                if user_mgr is not None:
                    reward = outcome_value if success else 0.0
                    brand_id = metadata.get("asin", "")
                    touch_pos = metadata.get("touch_position", 0)

                    # Extract page cluster for user×page interaction tracking
                    page_cluster = metadata.get("page_cluster", "")
                    if not page_cluster:
                        # Derive from page edge dimensions if available
                        page_edge_dims = metadata.get("page_edge_dimensions", {})
                        if page_edge_dims:
                            try:
                                from adam.retargeting.resonance.creative_adapter import CreativeAdapter
                                from adam.retargeting.resonance.mindstate_vector import extract_mindstate_vector
                                ms = extract_mindstate_vector(
                                    page_profile={"edge_dimensions": page_edge_dims},
                                    url=metadata.get("page_url", ""),
                                    domain=metadata.get("context_domain", ""),
                                )
                                page_cluster = CreativeAdapter().classify_page_cluster(ms)
                            except Exception:
                                pass

                    # Update per-user mechanism posterior
                    user_profile = user_mgr.update_user_posterior(
                        user_id=user_id,
                        brand_id=brand_id,
                        mechanism=therapeutic_mech,
                        barrier=barrier,
                        archetype_id=archetype,
                        reward=reward,
                        touch_position=touch_pos,
                        context={"category": category},
                        page_cluster=page_cluster,
                    )

                    user_result = {
                        "updated": True,
                        "user_id": user_id,
                        "mechanisms_tried": len(user_profile.mechanism_posteriors),
                    }

                    # Run trajectory analysis when user has 3+ touches
                    total_touches = sum(
                        p.sample_count
                        for p in user_profile.mechanism_posteriors.values()
                    )
                    if total_touches >= 3:
                        analyzer = TrajectoryAnalyzer()
                        # Collect all outcomes across mechanisms for trajectory
                        all_outcomes = []
                        all_mechs = []
                        for mech_name, posterior in user_profile.mechanism_posteriors.items():
                            all_outcomes.extend(posterior.outcomes)
                            all_mechs.extend([mech_name] * len(posterior.outcomes))
                        if len(all_outcomes) >= 3:
                            traj = analyzer.analyze(
                                outcomes=all_outcomes,
                                mechanisms=all_mechs,
                                user_id=user_id,
                            )
                            user_result["trajectory"] = traj.trajectory_type

                    results["updates"]["user_posteriors"] = user_result
            except Exception as e:
                logger.debug("User posterior update skipped: %s", e)

        # =====================================================================
        # 14. RESONANCE ENGINE LEARNING (Trilateral Resonance)
        #
        # Routes outcomes to the ResonanceLearner which updates the
        # resonance model: page_mindstate × mechanism × barrier → outcome.
        # This is the core of trilateral resonance — the system learns
        # which page psychological fields AMPLIFY which mechanisms for
        # which barriers. Over time, placement decisions become informed
        # by empirical resonance data, not domain-level heuristics.
        #
        # Enhancement #36 integration: Step 13.5 user posterior context
        # flows INTO resonance learning so the resonance model can:
        # - Compute user-residualized page effects (purer page signal)
        # - Weight observations by design-effect (within-subject discount)
        # - Store user trajectory state for hypothesis generation
        # =====================================================================
        page_url = metadata.get("page_url", "") or metadata.get("context_domain", "")
        mechanism_sent = metadata.get("mechanism_sent", "")
        if page_url and mechanism_sent:
            try:
                from adam.retargeting.resonance.resonance_learner import get_resonance_learner
                from adam.retargeting.resonance.mindstate_vector import extract_mindstate_vector

                # Build mindstate from page edge dimensions in decision context
                page_edge_dims = metadata.get("page_edge_dimensions", {})
                if page_edge_dims:
                    mindstate = extract_mindstate_vector(
                        page_profile={"edge_dimensions": page_edge_dims},
                        url=page_url,
                        domain=metadata.get("context_domain", ""),
                    )

                    # Extract user posterior context from step 13.5 results
                    user_updates = results.get("updates", {}).get("user_posteriors", {})
                    user_baseline = 0.5
                    user_traj_state = ""
                    user_mechs_tried = 0
                    de_weight = 1.0
                    if user_updates.get("updated"):
                        user_mechs_tried = user_updates.get("mechanisms_tried", 0)
                        user_traj_state = user_updates.get("trajectory", "")
                        # Compute user baseline from their posteriors
                        try:
                            infra = Infrastructure.get_instance()
                            components = LearningComponents.get_instance(infra)
                            u_mgr = components.user_posterior_manager
                            if u_mgr:
                                u_prof = u_mgr.get_user_profile(
                                    user_id, metadata.get("asin", ""), archetype
                                )
                                if u_prof.total_touches_observed > 0:
                                    user_baseline = (
                                        u_prof.total_reward_sum / u_prof.total_touches_observed
                                    )
                                de_weight = u_prof.design_effect_weight
                        except Exception:
                            pass

                    learner = get_resonance_learner()
                    resonance_result = learner.process_outcome(
                        page_mindstate=mindstate,
                        mechanism=mechanism_sent,
                        barrier=metadata.get("barrier_diagnosed", ""),
                        archetype=archetype,
                        converted=success,
                        engaged=outcome_type in ("click", "engagement"),
                        touch_position=metadata.get("touch_position", 0),
                        context={
                            "category": category,
                            "decision_id": decision_id,
                        },
                        # User context from step 13.5
                        user_id=user_id,
                        user_baseline=user_baseline,
                        user_trajectory_state=user_traj_state,
                        user_mechanisms_tried=user_mechs_tried,
                        design_effect_weight=de_weight,
                    )
                    results["updates"]["resonance_learning"] = resonance_result
            except Exception as e:
                logger.debug("Resonance learning skipped: %s", e)

        # =====================================================================
        # 15. CONVERSION-TRIGGERED PRIORITY CRAWL
        #
        # When a conversion happens on a specific page, that page is
        # high-value intelligence — the system should immediately deep-crawl
        # it, score its psychological state, and find similar pages to
        # target. This is how the system actively seeks resonance conditions
        # rather than passively waiting for them.
        # =====================================================================
        if page_url and success:
            try:
                from adam.intelligence.page_crawl_scheduler import queue_priority_crawl
                crawl_queued = await queue_priority_crawl(
                    url=page_url,
                    priority=outcome_value,
                    reason=f"conversion:{outcome_type}:{mechanism_sent}",
                )
                results["updates"]["priority_crawl"] = {
                    "queued": crawl_queued,
                    "url": page_url,
                }
            except Exception as e:
                logger.debug("Priority crawl queue skipped: %s", e)

        # =====================================================================
        # 16. COPY EFFECTIVENESS LEARNING
        #
        # Tracks which copy variant was served and feeds the outcome back
        # to the CopyEffectivenessLearner. Over time, the learner discovers
        # which (tone, framing, evidence_type, cta_style) combinations work
        # for each (archetype, barrier, page_cluster) context cell.
        # =====================================================================
        if archetype and mechanism_sent:
            try:
                from adam.output.copy_generation.copy_learner import get_copy_learner
                learner = get_copy_learner()

                # Ensure serving is recorded (may not have been recorded at decision time
                # if the decision path didn't go through the copy learner)
                variant_id = metadata.get("copy_variant_id", "")
                if variant_id:
                    learner.record_serving(decision_id, variant_id)

                copy_result = learner.record_outcome(
                    decision_id=decision_id,
                    archetype=archetype,
                    barrier=metadata.get("barrier_diagnosed", ""),
                    converted=success,
                    page_cluster=metadata.get("context_decision_style", ""),
                )
                if copy_result.get("updated"):
                    results["updates"]["copy_learning"] = copy_result
            except Exception as e:
                logger.debug("Copy effectiveness learning skipped: %s", e)

        # =====================================================================
        # 17. CAUSAL DECOMPOSITION + HYPOTHESIS GENERATION
        #
        # This is the CLOSED REASONING LOOP. Every conversion is decomposed
        # into its causal ingredients (which dimensions drove it, which
        # theory chain was active), then hypotheses are generated and
        # tested inferentially. This is how the system understands WHY
        # things work, not just WHAT works.
        #
        # The loop: DECOMPOSE → HYPOTHESIZE → PREDICT → ACT → VALIDATE → COMPOUND
        # =====================================================================
        if mechanism_sent:
            try:
                from adam.intelligence.causal_decomposition import get_causal_decomposition_engine
                from adam.intelligence.inferential_hypothesis_engine import get_inferential_hypothesis_engine
                from adam.intelligence.prediction_engine import get_prediction_engine

                decomp = get_causal_decomposition_engine()
                hyp_engine = get_inferential_hypothesis_engine()
                pred_engine = get_prediction_engine()

                # Phase 2: DECOMPOSE — isolate causal ingredients
                # Phase 2a: TEST existing hypotheses against this outcome
                # Every outcome is a potential test of existing hypotheses
                edge_dims = metadata.get("alignment_scores", {})
                hypotheses_tested = 0
                hypotheses_validated = 0
                for hid in list(hyp_engine._hypotheses.keys()):
                    observation = {
                        "mechanism_sent": mechanism_sent,
                        "converted": success,
                        "edge_dimensions": edge_dims,
                    }
                    result_h = hyp_engine.test_empirically(hid, observation)
                    if result_h and (result_h.supporting_observations + result_h.contradicting_observations) > 0:
                        hypotheses_tested += 1
                    if result_h and result_h.status.value == "validated":
                        hypotheses_validated += 1

                # Phase 2b: DECOMPOSE — isolate causal ingredients
                recipe = decomp.decompose(
                    decision_id=decision_id,
                    metadata=metadata,
                    success=success,
                )

                hypotheses_generated = 0
                predictions_generated = 0
                if recipe and recipe.primary_ingredients:
                    # Phase 3: HYPOTHESIZE — generate transferable hypotheses
                    new_hypotheses = hyp_engine.generate_from_recipe(recipe)
                    hypotheses_generated = len(new_hypotheses)

                    # Phase 4: PREDICT — find opportunities for validated hypotheses
                    for hyp in new_hypotheses:
                        if hyp.is_actionable:
                            preds = pred_engine.generate_predictions(hyp.hypothesis_id)
                            predictions_generated += len(preds)

                    results["updates"]["causal_intelligence"] = {
                        "recipe_ingredients": len(recipe.primary_ingredients),
                        "hypotheses_generated": hypotheses_generated,
                        "hypotheses_tested": hypotheses_tested,
                        "hypotheses_validated": hypotheses_validated,
                        "predictions_generated": predictions_generated,
                        "is_surprising": recipe.is_surprising,
                        "decomposition_confidence": recipe.decomposition_confidence,
                    }

                    if recipe.is_surprising:
                        logger.info(
                            "SURPRISING conversion: %s — %s",
                            decision_id, recipe.surprise_reason,
                        )

            except Exception as e:
                logger.debug("Causal intelligence loop skipped: %s", e)

        # =====================================================================
        # 17b. COUNTERFACTUAL TRACKING
        #
        # For non-conversions: "What WOULD have worked?"
        # For conversions: validate previous counterfactual predictions.
        # Doubles effective learning from failures.
        # =====================================================================
        if mechanism_sent:
            try:
                from adam.intelligence.counterfactual_tracker import get_counterfactual_tracker
                cf_tracker = get_counterfactual_tracker()
                edge_dims = metadata.get("alignment_scores", {})
                cf_results = cf_tracker.generate_counterfactual(
                    decision_id=decision_id,
                    mechanism_used=mechanism_sent,
                    converted=success,
                    edge_dimensions=edge_dims,
                    archetype=archetype,
                )
                if cf_results:
                    results["updates"]["counterfactual"] = {
                        "predictions": len(cf_results),
                        "alternatives": [p.counterfactual_mechanism for p in cf_results],
                    }
            except Exception as e:
                logger.debug("Counterfactual tracking skipped: %s", e)

        # =====================================================================
        # 18. TEST EXISTING PREDICTIONS
        #
        # If this outcome corresponds to an active prediction, validate it.
        # This closes the predict→validate loop.
        # =====================================================================
        prediction_id = metadata.get("prediction_id", "")
        if prediction_id:
            try:
                from adam.intelligence.prediction_engine import get_prediction_engine
                pred_engine = get_prediction_engine()
                pred_result = pred_engine.record_outcome(prediction_id, converted=success)
                if pred_result:
                    results["updates"]["prediction_validation"] = {
                        "prediction_id": prediction_id,
                        "validated": pred_result.prediction_validated,
                        "accuracy": pred_result.accuracy,
                    }
            except Exception as e:
                logger.debug("Prediction validation skipped: %s", e)

        elapsed = (time.time() - start) * 1000
        results["processing_time_ms"] = elapsed

        self._outcomes_processed += 1
        self._total_updates += sum(1 for v in results["updates"].values() if "error" not in str(v))

        logger.info(
            f"Outcome processed: decision={decision_id}, "
            f"type={outcome_type}, success={success}, "
            f"updates={len(results['updates'])}, "
            f"time={elapsed:.0f}ms"
        )

        return results
    
    async def _update_thompson(
        self,
        decision_id: str,
        success: bool,
        metadata: Dict[str, Any],
        processing_depth_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Update Thompson Sampling posteriors with outcome.

        CRITICAL FIX #1: Only credits mechanism_sent (what was actually
        shown), not mechanisms_considered.

        CRITICAL FIX #2: Properly converts string mechanism names to
        CognitiveMechanism enums, and archetype strings to ArchetypeID
        enums. The sampler's update_posterior() expects typed enums.

        CRITICAL FIX #3: This is the ONLY Thompson update path for
        outcomes. The UnifiedLearningHub no longer handles OUTCOME_SUCCESS
        for Thompson, preventing double-counting.

        Enhancement #34: processing_depth_weight scales the Beta posterior
        update. UNPROCESSED impressions (weight=0.05) barely shift the
        posterior, preventing systematic pessimism from noise.
        """
        from adam.cold_start.thompson.sampler import get_thompson_sampler
        from adam.cold_start.models.enums import ArchetypeID, CognitiveMechanism

        sampler = get_thompson_sampler()

        archetype_str = metadata.get("archetype", "")
        cascade_level = metadata.get("cascade_level", 0)

        # ONLY credit the mechanism that was actually sent to the buyer.
        mechanism_sent = metadata.get("mechanism_sent", "")
        if not mechanism_sent:
            mechanisms = metadata.get("mechanisms_applied", [])
            mechanism_sent = mechanisms[0] if mechanisms else ""

        if not archetype_str or not mechanism_sent:
            return {"posteriors_updated": 0, "reason": "missing archetype or mechanism"}

        # Convert string archetype to enum
        # Campaign-specific archetypes → Thompson Sampling archetypes
        _CAMPAIGN_TO_THOMPSON = {
            "careful_truster": "guardian",      # Prevention-focused, safety-seeking
            "status_seeker": "achiever",        # Goal-oriented, status-driven
            "easy_decider": "explorer",         # Action-oriented, low deliberation
            "corporate_executive": "guardian",
            "airport_anxiety": "guardian",
            "special_occasion": "achiever",
            "repeat_loyal": "explorer",
            "first_timer": "explorer",
        }
        # Map campaign archetype to Thompson archetype if needed
        thompson_arch = _CAMPAIGN_TO_THOMPSON.get(archetype_str.lower(), archetype_str.lower())

        archetype_enum: Optional[ArchetypeID] = None
        try:
            archetype_enum = ArchetypeID(thompson_arch)
        except ValueError:
            # Try matching by name
            for member in ArchetypeID:
                if member.value == thompson_arch or member.name.lower() == thompson_arch:
                    archetype_enum = member
                    break
            if archetype_enum is None:
                logger.debug(f"Unknown archetype '{archetype_str}' — skipping Thompson update")
                return {"posteriors_updated": 0, "reason": f"unknown archetype: {archetype_str}"}

        # Convert string mechanism to CognitiveMechanism enum.
        # The bilateral cascade uses Cialdini-style names (social_proof,
        # authority, scarcity) while the sampler uses psychological
        # mechanism names (regulatory_focus, construal_level, etc.).
        # Map between the two naming systems.
        _MECHANISM_MAP = {
            # Cialdini-style → CognitiveMechanism enum
            "social_proof": CognitiveMechanism.MIMETIC_DESIRE,
            "authority": CognitiveMechanism.AUTOMATIC_EVALUATION,
            "scarcity": CognitiveMechanism.ATTENTION_DYNAMICS,
            "loss_aversion": CognitiveMechanism.REGULATORY_FOCUS,
            "reciprocity": CognitiveMechanism.WANTING_LIKING,
            "commitment": CognitiveMechanism.IDENTITY_CONSTRUCTION,
            "liking": CognitiveMechanism.WANTING_LIKING,
            "unity": CognitiveMechanism.IDENTITY_CONSTRUCTION,
            "curiosity": CognitiveMechanism.ATTENTION_DYNAMICS,
            "cognitive_ease": CognitiveMechanism.CONSTRUAL_LEVEL,
            # Direct matches
            "construal_level": CognitiveMechanism.CONSTRUAL_LEVEL,
            "regulatory_focus": CognitiveMechanism.REGULATORY_FOCUS,
            "automatic_evaluation": CognitiveMechanism.AUTOMATIC_EVALUATION,
            "wanting_liking": CognitiveMechanism.WANTING_LIKING,
            "mimetic_desire": CognitiveMechanism.MIMETIC_DESIRE,
            "attention_dynamics": CognitiveMechanism.ATTENTION_DYNAMICS,
            "temporal_construal": CognitiveMechanism.TEMPORAL_CONSTRUAL,
            "identity_construction": CognitiveMechanism.IDENTITY_CONSTRUCTION,
            "evolutionary_motive": CognitiveMechanism.EVOLUTIONARY_MOTIVE,
        }

        mechanism_enum = _MECHANISM_MAP.get(mechanism_sent.lower())
        if mechanism_enum is None:
            try:
                mechanism_enum = CognitiveMechanism(mechanism_sent.lower())
            except ValueError:
                logger.debug(f"Unknown mechanism '{mechanism_sent}' — skipping Thompson update")
                return {"posteriors_updated": 0, "reason": f"unknown mechanism: {mechanism_sent}"}

        try:
            sampler.update_posterior(
                mechanism=mechanism_enum,
                success=success,
                archetype=archetype_enum,
                weight=processing_depth_weight,
            )
            return {
                "posteriors_updated": 1,
                "archetype": archetype_str,
                "mechanism_sent": mechanism_sent,
                "mechanism_enum": mechanism_enum.value,
                "cascade_level": cascade_level,
                "processing_depth_weight": processing_depth_weight,
                "decision_context_found": metadata.get("decision_context_found", False),
            }
        except Exception as e:
            logger.warning(f"Thompson update failed for {archetype_str}/{mechanism_sent}: {e}")
            return {"posteriors_updated": 0, "error": str(e)}
    
    async def _update_meta_orchestrator(
        self,
        decision_id: str,
        success: bool,
        quality_score: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update meta-orchestrator strategy posteriors."""
        from adam.orchestrator.adaptive.meta_orchestrator import (
            get_meta_orchestrator, WorkflowStrategy, ContextSignature,
        )
        
        meta = get_meta_orchestrator()
        strategy_name = metadata.get("meta_strategy", "deep_reasoning")
        
        try:
            strategy = WorkflowStrategy(strategy_name)
        except ValueError:
            strategy = WorkflowStrategy.DEEP_REASONING
        
        context = ContextSignature(
            archetype_known=bool(metadata.get("archetype")),
            brand_awareness=metadata.get("brand_awareness", 0.5),
        )
        
        # Pass alignment confidence if available
        alignment_confidence = metadata.get("alignment_scores", {}).get("overall_alignment", 0.0)

        meta.record_outcome(
            strategy=strategy,
            context=context,
            success=success,
            quality_score=quality_score,
            alignment_confidence=alignment_confidence,
        )
        
        return {"strategy_updated": strategy_name, "alignment_confidence": alignment_confidence}
    
    async def _update_neo4j_attribution(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create outcome attribution edges in Neo4j.

        CRITICAL FIX: Only the mechanism_sent (primary) gets full credit.
        The secondary_mechanism gets reduced credit (0.3x) since it may
        have contributed indirectly. mechanisms_considered get no credit —
        they were explored but not deployed.
        """
        from adam.intelligence.graph.gds_runtime import get_gds_service

        gds = get_gds_service()
        archetype = metadata.get("archetype", "")
        mechanism_sent = metadata.get("mechanism_sent", "")
        secondary = metadata.get("secondary_mechanism", "")
        cascade_level = metadata.get("cascade_level", 0)

        edges_created = 0

        # Primary mechanism gets full credit
        if mechanism_sent:
            success = gds.create_outcome_attribution_edge(
                mechanism=mechanism_sent,
                outcome_type=outcome_type,
                attribution_weight=outcome_value,
                position=0,
                archetype_context=archetype,
            )
            if success:
                edges_created += 1

        # Secondary mechanism gets reduced credit (it influenced framing
        # but wasn't the primary persuasion vector)
        if secondary and secondary != mechanism_sent:
            success = gds.create_outcome_attribution_edge(
                mechanism=secondary,
                outcome_type=outcome_type,
                attribution_weight=outcome_value * 0.3,
                position=1,
                archetype_context=archetype,
            )
            if success:
                edges_created += 1

        # Create synergy edge between primary and secondary if both present
        # and outcome was positive
        if mechanism_sent and secondary and mechanism_sent != secondary and outcome_value > 0.6:
            gds.create_mechanism_synergy_edge(
                mechanism1=mechanism_sent,
                mechanism2=secondary,
                synergy_score=outcome_value,
                combined_lift=outcome_value * 0.5,
                context=archetype,
            )
            edges_created += 1

        return {
            "attribution_edges_created": edges_created,
            "mechanism_sent": mechanism_sent,
            "secondary_mechanism": secondary,
            "cascade_level": cascade_level,
        }
    
    async def _update_graph_rewriter(
        self,
        decision_id: str,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update graph rewriter rule effectiveness."""
        from adam.orchestrator.adaptive.graph_rewriter import get_adaptive_graph_rewriter
        
        rewriter = get_adaptive_graph_rewriter()
        rules_applied = metadata.get("graph_rewrites", {}).get("rules_applied", [])
        
        if rules_applied:
            rewriter.record_outcome(rules_applied, success)
            return {"rules_updated": len(rules_applied)}
        
        return {"rules_updated": 0}
    
    async def _route_to_learning_hub(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route outcome to unified learning hub for all-system updates."""
        from adam.core.learning.unified_learning_hub import (
            get_unified_learning_hub,
            UnifiedLearningSignal,
            UnifiedSignalType,
        )
        
        hub = get_unified_learning_hub()
        
        signal = UnifiedLearningSignal(
            signal_type=(
                UnifiedSignalType.OUTCOME_SUCCESS if success
                else UnifiedSignalType.OUTCOME_FAILURE
            ),
            source_component="outcome_handler",
            archetype=metadata.get("archetype", ""),
            mechanism=metadata.get("mechanisms_applied", ["unknown"])[0] if metadata.get("mechanisms_applied") else "unknown",
            confidence=outcome_value,
            payload={
                "decision_id": decision_id,
                "outcome_type": outcome_type,
                "outcome_value": outcome_value,
                "mechanisms_applied": metadata.get("mechanisms_applied", []),
                "ndf_profile": metadata.get("ndf_profile", {}),
                "alignment_score": metadata.get("alignment_score", 0.0),
                "meta_strategy": metadata.get("meta_strategy", ""),
                "product_category": metadata.get("product_category", ""),
            },
        )
        
        await hub.process_signal(signal)
        
        return {"signal_routed": True}
    
    async def _update_theory_learner(
        self,
        decision_id: str,
        success: bool,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update theoretical link strengths based on outcome.
        
        This is construct-level learning: the system learns which causal
        theories (PsychologicalState → PsychologicalNeed → CognitiveMechanism)
        are empirically validated by real outcomes.
        
        The inferential chains used for the decision are retrieved from the
        metadata (cached at decision time), and each theoretical link in
        each chain gets a Bayesian update.
        """
        from adam.core.learning.theory_learner import get_theory_learner
        
        learner = get_theory_learner()
        
        # Get the inferential chains from metadata
        inferential_chains = metadata.get("inferential_chains", [])
        
        if not inferential_chains:
            # Try to load from Redis cache (chains are cached with atom outputs)
            try:
                from adam.core.container import get_container
                container = get_container()
                cache_key = f"adam:atom_outputs:{decision_id}"
                cached = await container.redis_cache.get(cache_key)
                if cached:
                    mech_output = cached.get("atom_mechanism_activation", {})
                    if isinstance(mech_output, dict):
                        inferential_chains = (
                            mech_output.get("secondary_assessments", {}).get("inferential_chains", [])
                            or mech_output.get("inferential_chains", [])
                        )
            except Exception as e:
                logger.debug(f"Failed to load chains from cache: {e}")
        
        # =====================================================================
        # PRIMARY PATH: Update graph edge strengths from EVERY outcome
        #
        # Previously, this was gated on inferential_chains being present,
        # meaning the theory learner only ran when NDF chains existed.
        # Now we ALWAYS update edge strengths using:
        #   1. Explicit inferential chains (if available — highest quality)
        #   2. Graph-inferred construct activations (new inferential core)
        #   3. Active constructs from DSP intelligence
        #
        # This ensures the graph gets smarter from every decision outcome,
        # not just the subset that had NDF chains.
        # =====================================================================

        result = {}

        if inferential_chains:
            # Best case: explicit NDF inferential chains
            result = learner.process_all_chains_for_decision(
                inferential_chains=inferential_chains,
                decision_id=decision_id,
                success=success,
                outcome_value=outcome_value,
            )
        else:
            # Construct-level learning: update edges from active constructs
            # and mechanisms even without explicit NDF chains
            active_constructs = metadata.get("active_dsp_constructs", [])
            mechanisms_used = metadata.get("mechanisms", [])
            graph_inference = metadata.get("graph_inference", {})

            # Get graph-inferred top constructs
            top_constructs = graph_inference.get("top_constructs", [])
            if top_constructs:
                for tc in top_constructs:
                    cid = tc.get("id", "")
                    if cid and cid not in active_constructs:
                        active_constructs.append(cid)

            if active_constructs and mechanisms_used:
                # Synthesize construct → mechanism chains from the decision
                synthetic_chains = []
                for mechanism in mechanisms_used[:3]:
                    chain_dict = {
                        "recommended_mechanism": mechanism,
                        "mechanism_score": outcome_value,
                        "confidence": 0.5,  # Lower confidence than NDF chains
                        "steps": [
                            {
                                "source": construct,
                                "target": mechanism,
                                "link_type": "construct_to_mechanism",
                                "theoretical_strength": 0.5,
                            }
                            for construct in active_constructs[:5]
                        ],
                        "theoretical_link_keys": [
                            f"{c}→{mechanism}" for c in active_constructs[:5]
                        ],
                    }
                    synthetic_chains.append(chain_dict)

                if synthetic_chains:
                    result = learner.process_all_chains_for_decision(
                        inferential_chains=synthetic_chains,
                        decision_id=decision_id,
                        success=success,
                        outcome_value=outcome_value,
                    )
                    result["chain_source"] = "synthetic_from_constructs"
            else:
                result = {"skipped": True, "reason": "no_constructs_or_mechanisms"}
        
        # Periodically push updates to Neo4j (every 50 outcomes)
        if learner.stats["total_outcomes"] % 50 == 0 and learner.stats["total_outcomes"] > 0:
            try:
                from adam.core.container import get_container
                container = get_container()
                if hasattr(container, '_neo4j_driver') and container._neo4j_driver:
                    with container._neo4j_driver.session() as session:
                        updated = learner.update_neo4j_link_strengths(session)
                        result["neo4j_links_updated"] = updated
            except Exception as e:
                logger.debug(f"Periodic Neo4j update failed: {e}")
        
        # Add theory learner stats
        result["learner_stats"] = learner.stats
        
        return result
    
    async def _update_dsp_learning(
        self,
        decision_id: str,
        success: bool,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update DSP impression learning from outcome.
        
        This covers four learning dimensions:
        1. Signal reliability: which behavioral signals correlated with outcome
        2. Construct accuracy: which inferred constructs predicted correctly
        3. Edge strength: which causal edges were empirically validated
        4. Strategy effectiveness: which persuasion strategies worked
        
        Learning is routed back to the DSP registries and the Neo4j graph.
        """
        updates = {"signal_updates": 0, "construct_updates": 0, "edge_updates": 0}
        
        # Extract DSP-specific metadata
        ndf_profile = metadata.get("ndf_profile", {})
        strategy = metadata.get("strategy", {})
        enrichment_multiplier = metadata.get("enrichment_multiplier", 1.0)
        inferential_chains = metadata.get("inferential_chains", [])
        reasoning_trace = metadata.get("reasoning_trace", [])
        
        # 1. If inferential chains were used, update theory learner with them
        if inferential_chains:
            from adam.core.learning.theory_learner import get_theory_learner
            learner = get_theory_learner()
            chain_result = learner.process_all_chains_for_decision(
                inferential_chains=inferential_chains,
                decision_id=decision_id,
                success=success,
                outcome_value=outcome_value,
            )
            updates["theory_chain_updates"] = chain_result.get("chains_processed", 0)
            updates["edge_updates"] = chain_result.get("links_updated", 0)
        
        # 2. Update Neo4j signal reliability if available
        signal_data = metadata.get("extracted_signals", {})
        if signal_data:
            try:
                from adam.core.container import get_container
                container = get_container()
                if hasattr(container, '_neo4j_driver') and container._neo4j_driver:
                    with container._neo4j_driver.session() as session:
                        for signal_id, signal_val in signal_data.items():
                            # Only update signals that had non-trivial values
                            if signal_val and abs(signal_val) > 0.01:
                                # Bayesian update of signal reliability
                                update = (
                                    f'MATCH (s:BehavioralSignal {{signal_id: "{signal_id}"}}) '
                                    f'SET s.outcome_count = COALESCE(s.outcome_count, 0) + 1, '
                                    f's.success_count = COALESCE(s.success_count, 0) + '
                                    f'CASE WHEN {1 if success else 0} = 1 THEN 1 ELSE 0 END, '
                                    f's.reliability_empirical = toFloat(COALESCE(s.success_count, 0) + 1) / '
                                    f'toFloat(COALESCE(s.outcome_count, 0) + 2)'
                                )
                                session.run(update)
                                updates["signal_updates"] += 1
            except Exception as e:
                logger.debug(f"Signal reliability update failed: {e}")
        
        # 3. Track strategy effectiveness for construct-level learning
        mechanisms_used = strategy.get("mechanism_chain", [])
        if mechanisms_used:
            updates["mechanisms_tracked"] = mechanisms_used
            updates["strategy_outcome"] = "success" if success else "failure"
        
        # 4. Log for aggregate analysis
        logger.info(
            f"DSP learning: decision={decision_id}, success={success}, "
            f"multiplier={enrichment_multiplier:.2f}, "
            f"signals_updated={updates['signal_updates']}, "
            f"edges_updated={updates['edge_updates']}"
        )
        
        return updates

    async def _update_ml_ensemble(
        self,
        decision_id: str,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update ML ensemble weights based on outcome."""
        if not metadata.get("ml_available", False):
            return {"skipped": True}
        
        from adam.ml.hybrid_extractor import get_hybrid_extractor
        
        extractor = get_hybrid_extractor()
        
        # Get prediction from edge dimensions (full 20-dim) or legacy NDF profile
        # Use composite_alignment as the prediction signal — it's the primary
        # quality indicator from bilateral edge evidence.
        alignment_scores = metadata.get("alignment_scores", {})
        if alignment_scores and "composite_alignment" in alignment_scores:
            predicted = alignment_scores["composite_alignment"]
        else:
            # Fallback: use composite from NDF profile if available
            ndf_profile = metadata.get("ndf_profile", {})
            predicted = ndf_profile.get("composite_alignment", 0.5) if ndf_profile else 0.5
        
        extractor.update_weights(
            outcome_success=success,
            rule_prediction=predicted,
            ml_prediction=metadata.get("ml_ndf_agreement", 0.5),
        )
        
        return {"ensemble_updated": True}
    
    async def _update_cognitive_learning(
        self,
        decision_id: str,
        success: bool,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Route outcome to CognitiveLearningSystem for alignment matrix learning.

        This:
        1. Reconstructs the prediction state from metadata
        2. Calls observe_outcome on CognitiveLearningSystem
        3. Periodically consolidates learning (every 100 outcomes)
        4. Returns reasoning chain if pattern was discovered
        """
        from adam.intelligence.cognitive_learning_system import get_cognitive_learning_system

        cls = get_cognitive_learning_system()

        # Reconstruct prediction state from metadata
        alignment_scores = metadata.get("alignment_scores", {})
        expanded_type = metadata.get("expanded_customer_type", {})
        ad_profile = metadata.get("ad_copy_profile", {})

        if not alignment_scores and not expanded_type:
            return {"skipped": True, "reason": "no alignment data in metadata"}

        prediction_state = {
            "customer_profile": {
                "archetype": metadata.get("archetype", "explorer"),
                "expanded_motivation": expanded_type.get("motivation", "problem_solving_mot"),
                "expanded_decision_style": expanded_type.get("decision_style", "ds_satisficing"),
                "regulatory_focus": expanded_type.get("regulatory_focus", "rf_pragmatic_balanced"),
                "social_influence": expanded_type.get("social_influence_type", "si_socially_aware"),
            },
            "ad_profile": {
                "value": {"primary": (ad_profile.get("detected_value_propositions", [""])[0] or "").replace("vp_", "")},
                "linguistic_style": {"primary": ad_profile.get("linguistic_style", "conversational")},
                "persuasion_techniques": ad_profile.get("detected_persuasion_techniques", []),
            },
            "alignment_score": {
                "scores": {
                    "predicted_effectiveness": alignment_scores.get("overall_alignment", 0.5),
                },
                "matrix_scores": alignment_scores.get("matrix_scores", {}),
            },
        }

        # Observe outcome
        result = cls.observe_outcome(
            prediction_state=prediction_state,
            conversion=success if metadata.get("outcome_type") == "conversion" else None,
            engagement=outcome_value if metadata.get("outcome_type") == "engagement" else None,
            sentiment=outcome_value if metadata.get("outcome_type") == "sentiment" else None,
        )

        # Periodically consolidate learning
        update_result = {
            "observed": True,
            "reasoning_chain": result.get("reasoning_chain"),
        }

        if self._outcomes_processed % 100 == 0 and self._outcomes_processed > 0:
            consolidation = cls.consolidate_learning()
            update_result["consolidation"] = consolidation
            if consolidation.get("new_patterns", 0) > 0:
                logger.info(
                    f"Cognitive learning consolidated: {consolidation['new_patterns']} new patterns, "
                    f"{consolidation['total_patterns']} total"
                )

        return update_result

    async def _update_page_context_learning(
        self,
        decision_id: str,
        success: bool,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Learn how page context modulates mechanism effectiveness.

        Tracks outcomes conditioned on:
        - Page decision style (deliberative/impulsive)
        - Whether mechanism was in page's open/closed channels
        - Page ELM route (central/peripheral)
        - Page publisher authority level

        This enables the system to learn:
        'authority works 80% on deliberative pages, 20% on impulsive'
        'scarcity backfires when page has closed that channel'
        """
        mechanism_sent = metadata.get("mechanism_sent", "")
        if not mechanism_sent:
            return {"skipped": True, "reason": "no mechanism_sent"}

        context_decision_style = metadata.get("context_decision_style", "")
        context_elm_route = metadata.get("context_elm_route", "")
        context_open = metadata.get("context_open_channels", [])
        context_closed = metadata.get("context_closed_channels", [])
        context_authority = metadata.get("context_publisher_authority", 0.0)
        context_mindset = metadata.get("context_mindset", "")

        if not context_decision_style and not context_elm_route and not context_mindset:
            return {"skipped": True, "reason": "no page context in metadata"}

        # Track: was the mechanism in an open or closed channel?
        mechanism_was_open = mechanism_sent in context_open
        mechanism_was_closed = mechanism_sent in context_closed

        # Record the observation for learning
        # This uses the MechanismInteractionLearner's category-conditioned
        # learning — we treat page_context as a "category" dimension
        from adam.learning.mechanism_interactions import get_mechanism_interaction_learner
        learner = get_mechanism_interaction_learner()

        # Build a context-enriched mechanism activation dict
        # Include page context variables as pseudo-mechanisms so the
        # interaction learner discovers context×mechanism correlations
        context_activations = {}
        if metadata.get("mechanism_scores"):
            context_activations.update(metadata["mechanism_scores"])

        # Create synthetic context signals that the learner can correlate
        # with outcomes. These become discoverable interactions:
        # "deliberative_page × authority → high success"
        context_key = f"page_{context_decision_style}" if context_decision_style else None
        if context_key:
            context_activations[context_key] = 0.8  # Strong signal

        elm_key = f"elm_{context_elm_route}" if context_elm_route else None
        if elm_key:
            context_activations[elm_key] = 0.8

        if context_activations and len(context_activations) >= 2:
            learner.record_observation(
                mechanism_activations=context_activations,
                outcome_value=outcome_value,
                user_id=metadata.get("buyer_id", "anonymous"),
                decision_id=decision_id,
                category=f"page_context:{context_mindset}" if context_mindset else None,
            )

        # ── Page-Conditioned Mechanism Thompson Sampling ──
        # Update domain×mechanism Beta posteriors in Redis.
        # After 20+ observations per cell, these empirical rates override
        # the word-list-derived mechanism adjustments from page profiling.
        context_domain = metadata.get("context_domain", "")
        if context_domain and mechanism_sent:
            try:
                import redis as _redis
                r = _redis.Redis(host="localhost", port=6379, decode_responses=True)
                ts_key = f"informativ:page:mech_ts:{context_domain}:{mechanism_sent}"
                pipe = r.pipeline()
                if success:
                    pipe.hincrbyfloat(ts_key, "alpha", 1.0)
                else:
                    pipe.hincrbyfloat(ts_key, "beta", 1.0)
                pipe.expire(ts_key, 86400 * 90)  # 90-day TTL
                pipe.execute()

                # Record metric
                try:
                    from adam.infrastructure.prometheus.metrics import get_metrics
                    get_metrics().page_outcome_learning_total.inc()
                except Exception:
                    pass
            except Exception:
                pass

        return {
            "context_decision_style": context_decision_style,
            "context_elm_route": context_elm_route,
            "mechanism_sent": mechanism_sent,
            "mechanism_was_open_channel": mechanism_was_open,
            "mechanism_was_closed_channel": mechanism_was_closed,
            "success": success,
            "page_mechanism_ts_updated": bool(context_domain and mechanism_sent),
            "learning_signal": (
                "STRONG: mechanism aligned with open channel and succeeded"
                if mechanism_was_open and success
                else "WARNING: mechanism was in closed channel"
                if mechanism_was_closed
                else "NEUTRAL: no channel alignment data"
            ),
        }

    async def _update_mechanism_interactions(
        self,
        decision_id: str,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record mechanism co-activation for portfolio optimization learning.

        When multiple mechanisms are considered/scored for a decision,
        the interaction learner tracks their co-activation patterns and
        outcome correlations. Over time, this builds the covariance
        matrix that enables MPT-style portfolio optimization.
        """
        from adam.learning.mechanism_interactions import get_mechanism_interaction_learner

        learner = get_mechanism_interaction_learner()

        # Build mechanism activation dict from the decision's mechanism scores.
        # These are the scores computed by the bilateral cascade at decision time.
        mechanism_scores = metadata.get("mechanism_scores", {})
        if not mechanism_scores:
            return {"skipped": True, "reason": "no mechanism_scores in metadata"}

        # Need at least 2 mechanisms to learn interactions
        if len(mechanism_scores) < 2:
            return {"skipped": True, "reason": "fewer than 2 mechanisms scored"}

        buyer_id = metadata.get("buyer_id", "")
        category = metadata.get("product_category", "") or metadata.get("content_category", "")

        updated_pairs = learner.record_observation(
            mechanism_activations=mechanism_scores,
            outcome_value=outcome_value,
            user_id=buyer_id or "anonymous",
            decision_id=decision_id,
            category=category or None,
        )

        # Periodically flush learned interactions to Neo4j (every 100 observations)
        # Without this, synergy/suppression knowledge is lost on restart.
        buffer_size = len(learner._observation_buffer)
        flushed = False
        if buffer_size > 0 and buffer_size % 100 == 0:
            try:
                # Get all learned interactions (not per-mechanism — iterate the full matrix)
                all_interactions = getattr(learner, "_interactions", {})
                synergy_count = 0
                suppression_count = 0

                if all_interactions:
                    from adam.intelligence.graph.gds_runtime import GDSRuntimeService

                    try:
                        from adam.config.settings import settings
                        gds = GDSRuntimeService(
                            neo4j_uri=getattr(settings, "neo4j_uri", "bolt://localhost:7687"),
                            neo4j_user=getattr(settings, "neo4j_user", "neo4j"),
                            neo4j_password=getattr(settings, "neo4j_password", ""),
                        )
                    except Exception:
                        gds = GDSRuntimeService()

                    for pair_key, interaction in all_interactions.items():
                        strength = getattr(interaction, "interaction_strength", 0)
                        confidence = getattr(interaction, "confidence", 0)
                        if confidence < 0.5:
                            continue
                        pair = pair_key if isinstance(pair_key, tuple) else (pair_key, "unknown")
                        if len(pair) >= 2:
                            gds.create_mechanism_synergy_edge(
                                pair[0], pair[1],
                                synergy_score=strength,
                                combined_lift=abs(strength) - 0.5,
                                context=category or "global",
                            )
                            if strength > 0:
                                synergy_count += 1
                            else:
                                suppression_count += 1

                # Clear buffer to prevent memory leak and stale re-flush
                learner._observation_buffer.clear()
                flushed = True

                if synergy_count or suppression_count:
                    logger.info(
                        "Flushed %d synergies + %d suppressions to Neo4j, buffer cleared (%d obs)",
                        synergy_count, suppression_count, buffer_size,
                    )
            except Exception as e:
                logger.debug("Mechanism interaction flush failed: %s", e)

        return {
            "pairs_updated": len(updated_pairs),
            "total_observations": buffer_size,
            "mechanisms_tracked": len(mechanism_scores),
            "flushed_to_neo4j": flushed,
        }

    async def _update_buyer_profile(
        self,
        buyer_id: str,
        outcome_type: str,
        metadata: Dict[str, Any],
        processing_depth_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Update per-buyer Beta posteriors for information value bidding.

        When an outcome arrives, we update the buyer's uncertainty profile
        on each alignment dimension. This narrows confidence intervals,
        reducing the information value bid premium for future impressions.

        Enhancement #34: processing_depth_weight scales the BONG
        noise_precision so unprocessed impressions produce minimal
        posterior shift on the buyer's uncertainty profile.
        """
        try:
            from adam.api.stackadapt.graph_cache import get_graph_cache
            graph_cache = get_graph_cache()
        except Exception:
            return {"skipped": True, "reason": "graph_cache not available"}

        if not hasattr(graph_cache, "update_buyer_profile"):
            return {"skipped": True, "reason": "buyer profile method not available"}

        # Build edge dimensions from whatever alignment data we have
        edge_dimensions: Dict[str, float] = {}

        # From the outcome metadata alignment scores — all 20 dimensions
        alignment = metadata.get("alignment_scores", {})
        if alignment:
            # Core edge dimensions (from BRAND_CONVERTED edges)
            core_dims = [
                "regulatory_fit", "construal_fit", "personality_alignment",
                "emotional_resonance", "value_alignment", "evolutionary_motive",
                "linguistic_style",
            ]
            # Extended dimensions (from intelligence modules / atom outputs)
            extended_dims = [
                "persuasion_susceptibility", "cognitive_load_tolerance",
                "narrative_transport", "social_proof_sensitivity",
                "loss_aversion_intensity", "temporal_discounting",
                "brand_relationship_depth", "autonomy_reactance",
                "information_seeking", "mimetic_desire",
                "interoceptive_awareness", "cooperative_framing_fit",
                "decision_entropy",
            ]
            for dim in core_dims + extended_dims:
                val = alignment.get(dim) or alignment.get(f"avg_{dim}")
                if val is not None:
                    edge_dimensions[dim] = float(val)

        # Also extract extended dimensions from atom outputs in metadata
        atom_outputs = metadata.get("atom_outputs", {})
        if atom_outputs:
            # Map atom output keys to uncertainty dimensions
            atom_dim_map = {
                "persuasion_susceptibility_score": "persuasion_susceptibility",
                "cognitive_load_score": "cognitive_load_tolerance",
                "narrative_transport_score": "narrative_transport",
                "social_proof_score": "social_proof_sensitivity",
                "loss_aversion_score": "loss_aversion_intensity",
                "temporal_discount_score": "temporal_discounting",
                "brand_relationship_score": "brand_relationship_depth",
                "autonomy_reactance_score": "autonomy_reactance",
                "information_seeking_score": "information_seeking",
                "mimetic_desire_score": "mimetic_desire",
                "interoceptive_score": "interoceptive_awareness",
                "cooperative_framing_score": "cooperative_framing_fit",
                "decision_entropy_score": "decision_entropy",
            }
            for atom_key, dim in atom_dim_map.items():
                if dim not in edge_dimensions:
                    val = atom_outputs.get(atom_key)
                    if val is not None:
                        edge_dimensions[dim] = float(val)

        # If no alignment data in metadata, use outcome_value as a weak signal
        if not edge_dimensions:
            outcome_val = metadata.get("outcome_value", 0.5)
            for dim in ["regulatory_fit", "construal_fit", "personality_alignment",
                        "emotional_resonance", "value_alignment"]:
                edge_dimensions[dim] = float(outcome_val)

        variance_deltas = graph_cache.update_buyer_profile(
            buyer_id=buyer_id,
            edge_dimensions=edge_dimensions,
            signal_type=outcome_type,
            processing_depth_weight=processing_depth_weight,
        )

        profile = graph_cache.get_buyer_profile(buyer_id)
        confidence = profile.aggregate_confidence if profile else 0.0

        return {
            "buyer_id": buyer_id,
            "signal_type": outcome_type,
            "dimensions_updated": len(variance_deltas) if variance_deltas else 0,
            "buyer_confidence": round(confidence, 3),
            "variance_reduction": sum(variance_deltas.values()) if variance_deltas else 0.0,
        }

    async def _update_bilateral_edge_evidence(
        self,
        archetype: str,
        category: str,
        success: bool,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update bilateral edge evidence for the (archetype, category) cell.

        This is the critical learning path that makes the core data asset
        self-improving. On each outcome:

        1. Increment evidence_count on the BayesianPrior node for this cell
        2. Update posterior_mean with Bayesian update
        3. If enough new evidence accumulated, schedule gradient recomputation

        Without this, BRAND_CONVERTED edge dimensions and gradient fields
        are frozen after ingestion and the system never compounds from
        live campaign outcomes.
        """
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if not client.is_connected:
                return {"skipped": True, "reason": "neo4j_unavailable"}

            mechanism = metadata.get("mechanism_sent", "")
            if not mechanism:
                return {"skipped": True, "reason": "no_mechanism_sent"}

            # Bayesian update on the BayesianPrior node for this (archetype, category, mechanism)
            # posterior_mean = (alpha) / (alpha + beta)
            # On success: alpha += 1
            # On failure: beta += 1
            # Use WITH to separate increment from posterior computation,
            # avoiding any ambiguity about evaluation order in SET clauses.
            update_query = """
            MERGE (bp:BayesianPrior {
                archetype: $archetype,
                category: $category,
                mechanism: $mechanism
            })
            ON CREATE SET
                bp.alpha = $init_alpha,
                bp.beta = $init_beta,
                bp.observation_count = 1,
                bp.created_at = datetime(),
                bp.updated_at = datetime()
            ON MATCH SET
                bp.alpha = CASE WHEN $success THEN bp.alpha + 1 ELSE bp.alpha END,
                bp.beta = CASE WHEN $success THEN bp.beta ELSE bp.beta + 1 END,
                bp.observation_count = bp.observation_count + 1,
                bp.updated_at = datetime()
            WITH bp
            SET bp.posterior_mean = bp.alpha / (bp.alpha + bp.beta)
            RETURN bp.observation_count AS obs,
                   bp.posterior_mean AS posterior,
                   bp.alpha AS alpha,
                   bp.beta AS beta
            """

            async with client.driver.session() as session:
                result = await session.run(
                    update_query,
                    archetype=archetype,
                    category=category,
                    mechanism=mechanism,
                    success=success,
                    init_alpha=2.0 if success else 1.0,
                    init_beta=1.0 if success else 2.0,
                )
                record = await result.single()

            if not record:
                return {"skipped": True, "reason": "merge_failed"}

            obs_count = record["obs"]
            posterior = record["posterior"]

            # Also update the RESPONDS_TO edge evidence count
            # Symmetric EMA: outcome signal = 1.0 (success) or 0.0 (failure)
            # blended with 5% learning rate: eff = eff * 0.95 + outcome * 0.05
            responds_to_query = """
            MATCH (a:CustomerArchetype {name: $archetype})
                  -[r:RESPONDS_TO]->(m:CognitiveMechanism {name: $mechanism})
            SET r.sample_size = COALESCE(r.sample_size, 0) + 1,
                r.effectiveness = COALESCE(r.effectiveness, 0.5) * 0.95
                    + (CASE WHEN $success THEN 1.0 ELSE 0.0 END) * 0.05,
                r.confidence = CASE
                    WHEN COALESCE(r.sample_size, 0) + 1 > 50 THEN 0.9
                    WHEN COALESCE(r.sample_size, 0) + 1 > 10 THEN 0.6
                    ELSE 0.3 + (COALESCE(r.sample_size, 0) + 1) / 100.0
                END,
                r.updated_at = datetime()
            RETURN r.effectiveness AS eff, r.sample_size AS samples
            """
            async with client.driver.session() as session:
                result = await session.run(
                    responds_to_query,
                    archetype=archetype,
                    mechanism=mechanism,
                    success=success,
                )
                edge_record = await result.single()

            # Schedule gradient recomputation after enough evidence
            gradient_scheduled = False
            if obs_count > 0 and obs_count % 50 == 0:
                try:
                    from adam.intelligence.gradient_fields import (
                        compute_gradient_field,
                    )
                    import asyncio

                    async def _recompute_gradient():
                        """Background gradient field recomputation."""
                        try:
                            gradient = compute_gradient_field(
                                archetype=archetype,
                                category=category,
                                driver=client.driver,
                            )
                            if gradient and gradient.is_valid:
                                # Update the GraphIntelligenceCache
                                try:
                                    from adam.api.stackadapt.graph_cache import get_graph_cache
                                    cache = get_graph_cache()
                                    cache_key = f"{archetype}:{category}"
                                    with cache._lock:
                                        cache._gradient_fields[cache_key] = gradient
                                    logger.info(
                                        "Gradient recomputed: %s/%s, R²=%.3f, "
                                        "n_edges=%d, top_priorities=%s",
                                        archetype, category,
                                        gradient.r_squared, gradient.n_edges,
                                        [p.dimension for p in gradient.optimization_priorities[:3]]
                                        if hasattr(gradient, 'optimization_priorities') else "N/A",
                                    )
                                except Exception as cache_err:
                                    logger.debug("Gradient cache update failed: %s", cache_err)
                            else:
                                logger.debug(
                                    "Gradient recomputation for %s/%s returned invalid result",
                                    archetype, category,
                                )
                        except Exception as grad_err:
                            logger.debug("Gradient recomputation failed: %s", grad_err)

                    # Fire-and-forget background task
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_recompute_gradient())
                    except RuntimeError:
                        pass  # No running loop — skip background task

                    gradient_scheduled = True
                    logger.info(
                        "Bilateral edge evidence milestone: %s/%s/%s has %d observations, "
                        "posterior=%.3f. Gradient recomputation scheduled.",
                        archetype, category, mechanism, obs_count, posterior,
                    )
                except ImportError:
                    pass

            # Invalidate graph cache for this (archetype, category) cell
            # so subsequent requests see fresh posterior data immediately
            cache_invalidated = False
            try:
                from adam.api.stackadapt.graph_cache import get_graph_cache
                cache = get_graph_cache()
                cache.invalidate(archetype=archetype, category=category)
                cache_invalidated = True
            except Exception as inv_err:
                logger.debug("Graph cache invalidation failed: %s", inv_err)

            return {
                "archetype": archetype,
                "category": category,
                "mechanism": mechanism,
                "success": success,
                "observation_count": obs_count,
                "posterior_mean": round(posterior, 4),
                "responds_to_updated": edge_record is not None,
                "gradient_recompute_scheduled": gradient_scheduled,
                "cache_invalidated": cache_invalidated,
            }

        except Exception as e:
            logger.warning("Bilateral edge evidence update failed: %s", e)
            return {"error": str(e)}

    @property
    def stats(self) -> Dict[str, int]:
        """Get handler statistics."""
        return {
            "outcomes_processed": self._outcomes_processed,
            "total_updates": self._total_updates,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_outcome_handler: Optional[OutcomeHandler] = None


def get_outcome_handler() -> OutcomeHandler:
    """Get or create the singleton outcome handler."""
    global _outcome_handler
    if _outcome_handler is None:
        _outcome_handler = OutcomeHandler()
    return _outcome_handler


async def handle_outcome(
    decision_id: str,
    outcome_type: str,
    outcome_value: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to process an outcome.
    
    This is the RECOMMENDED entry point for outcome processing.
    Call this from API endpoints, Kafka consumers, or batch processors.
    
    Example:
        from adam.core.learning.outcome_handler import handle_outcome
        
        result = await handle_outcome(
            decision_id="dec_123",
            outcome_type="conversion",
            outcome_value=1.0,
            metadata={"archetype": "achiever", "mechanisms_applied": ["authority"]}
        )
    """
    handler = get_outcome_handler()
    return await handler.process_outcome(
        decision_id=decision_id,
        outcome_type=outcome_type,
        outcome_value=outcome_value,
        metadata=metadata,
    )
