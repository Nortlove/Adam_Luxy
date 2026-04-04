# =============================================================================
# ADAM Campaign Orchestrator
# Location: adam/orchestrator/campaign_orchestrator.py
# =============================================================================

"""
Campaign Orchestrator - The Heart of ADAM

This is the unified entry point that coordinates ALL ADAM services to analyze
a campaign and produce intelligent recommendations.

Flow:
1. Initialize context and blackboard
2. Fetch review intelligence (if URL provided)
3. Query Neo4j for mechanism/archetype intelligence
4. Execute AtomDAG for psychological inference
5. Run MetaLearner for mechanism selection
6. Generate recommendations
7. Return results with full reasoning trace

This replaces the mock demo logic with REAL system intelligence.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.orchestrator.models import (
    AtomDAGResult,
    AtomExecutionResult,
    CampaignAnalysisResult,
    DataSourceInfo,
    DataSourceType,
    EvidenceItem,
    GraphQueryResult,
    MechanismSelectionResult,
    ReasoningTrace,
    SegmentRecommendation,
    StationRecommendation,
    ThompsonSamplingTrace,
)
from adam.orchestrator.graph_intelligence import (
    GraphIntelligenceService,
    get_graph_intelligence,
)

logger = logging.getLogger(__name__)


class CampaignOrchestrator:
    """
    Unified orchestrator for campaign analysis.
    
    Coordinates all ADAM services:
    - Review Intelligence (scraping + analysis)
    - Graph Intelligence (Neo4j queries)
    - AtomDAG (reasoning)
    - MetaLearner (mechanism selection)
    - ColdStart (archetype priors)
    - Blackboard (shared state)
    """
    
    def __init__(self):
        """Initialize the orchestrator with all required services."""
        self.graph_intelligence = get_graph_intelligence()
        
        # These will be lazily initialized
        self._review_orchestrator = None
        self._meta_learner = None
        self._cold_start = None
        self._blackboard = None
        self._atom_dag = None
        self._unified_intelligence = None
    
    # =========================================================================
    # SERVICE ACCESSORS (lazy initialization)
    # =========================================================================
    
    def _get_unified_intelligence(self):
        """Get UnifiedIntelligenceService for three-layer Bayesian fusion."""
        if self._unified_intelligence is None:
            try:
                from adam.intelligence.unified_intelligence_service import (
                    get_unified_intelligence_service,
                )
                self._unified_intelligence = get_unified_intelligence_service()
            except ImportError as e:
                logger.warning(f"UnifiedIntelligenceService not available: {e}")
        return self._unified_intelligence

    async def _get_review_orchestrator(self):
        """Get review intelligence orchestrator."""
        if self._review_orchestrator is None:
            try:
                from adam.intelligence.review_orchestrator import get_review_orchestrator
                self._review_orchestrator = get_review_orchestrator()
            except ImportError as e:
                logger.warning(f"Review orchestrator not available: {e}")
        return self._review_orchestrator
    
    async def _get_meta_learner(self):
        """Get meta learner service."""
        if self._meta_learner is None:
            try:
                from adam.meta_learner.service import get_meta_learner
                self._meta_learner = get_meta_learner()
            except ImportError as e:
                logger.warning(f"MetaLearner not available: {e}")
        return self._meta_learner
    
    async def _get_cold_start(self):
        """Get cold start service."""
        if self._cold_start is None:
            try:
                from adam.cold_start.service import get_cold_start_service
                self._cold_start = get_cold_start_service()
            except ImportError as e:
                logger.warning(f"ColdStart not available: {e}")
        return self._cold_start
    
    async def _get_blackboard(self):
        """Get blackboard service."""
        if self._blackboard is None:
            try:
                from adam.blackboard.service import get_blackboard_service
                self._blackboard = get_blackboard_service()
            except ImportError as e:
                logger.warning(f"Blackboard not available: {e}")
        return self._blackboard
    
    # =========================================================================
    # MAIN ANALYSIS METHOD
    # =========================================================================
    
    async def analyze_campaign(
        self,
        brand: str,
        product: str,
        description: str,
        call_to_action: str,
        product_url: Optional[str] = None,
        target_audience: Optional[str] = None,
        return_reasoning: bool = True,
    ) -> CampaignAnalysisResult:
        """
        Analyze a campaign using the full ADAM system.
        
        This is the main entry point that coordinates all services.
        
        Args:
            brand: Brand name
            product: Product/service name
            description: Product description
            call_to_action: Desired action
            product_url: URL for review scraping (optional)
            target_audience: Custom target audience (optional)
            return_reasoning: Whether to include full reasoning trace
            
        Returns:
            CampaignAnalysisResult with recommendations and reasoning
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Starting campaign analysis {request_id} for {brand} - {product}")
        
        # Initialize reasoning trace
        trace = ReasoningTrace(
            trace_id=request_id,
            timestamp=datetime.now(timezone.utc),
        )
        
        components_used = []
        
        # =====================================================================
        # STEP 1: Fetch Review Intelligence (if URL provided)
        # =====================================================================
        customer_intelligence = None
        if product_url:
            customer_intelligence = await self._fetch_review_intelligence(
                product_url=product_url,
                product_name=product,
                brand=brand,
                trace=trace,
            )
            if customer_intelligence and customer_intelligence.reviews_analyzed > 0:
                components_used.append("ReviewIntelligence")
                logger.info(f"Review intelligence: {customer_intelligence.reviews_analyzed} reviews analyzed")
        
        # =====================================================================
        # STEP 2: Determine Primary Archetype
        # =====================================================================
        primary_archetype, archetype_confidence = await self._determine_archetype(
            customer_intelligence=customer_intelligence,
            description=description,
            trace=trace,
        )
        components_used.append("ArchetypeInference")
        logger.info(f"Primary archetype: {primary_archetype} ({archetype_confidence:.0%} confidence)")
        
        # =====================================================================
        # STEP 3: Query Graph for Mechanism Intelligence
        # =====================================================================
        mechanism_intelligence = await self._fetch_mechanism_intelligence(
            archetype=primary_archetype,
            trace=trace,
        )
        components_used.append("GraphIntelligence")
        
        # =====================================================================
        # STEP 3b: Three-Layer Unified Intelligence
        # =====================================================================
        unified_intel = None
        unified_svc = self._get_unified_intelligence()
        if unified_svc:
            try:
                asin = None
                if product_url and "amazon" in product_url.lower():
                    import re
                    m = re.search(r'/dp/([A-Z0-9]{10})', product_url)
                    if m:
                        asin = f"product_{m.group(1)}"
                if asin:
                    unified_intel = unified_svc.fuse_mechanism_recommendation(
                        asin=asin,
                        category="All_Beauty",
                    )
                    if unified_intel and unified_intel.get("layers_used"):
                        components_used.append("UnifiedIntelligence")
                        trace.steps.append(EvidenceItem(
                            source=DataSourceType.GRAPH,
                            description=f"Three-layer fusion: {', '.join(unified_intel['layers_used'])}",
                            confidence=0.8,
                            data={"layers": unified_intel["layers_used"]},
                        ))
            except Exception as e:
                logger.warning(f"Unified intelligence query failed: {e}")

        # =====================================================================
        # STEP 3c: Bilateral Cascade + Information Value (StackAdapt path)
        # =====================================================================
        bilateral_result = None
        buyer_uncertainty_dict = None
        gradient_field_dict = None
        bilateral_result = await self._run_bilateral_cascade(
            asin=asin if unified_svc else None,
            archetype=primary_archetype,
            trace=trace,
        )
        if bilateral_result:
            components_used.append("BilateralCascade")
            # Extract buyer uncertainty and gradient for downstream atoms
            if bilateral_result.get("buyer_uncertainty"):
                buyer_uncertainty_dict = bilateral_result["buyer_uncertainty"]
            if bilateral_result.get("gradient_field"):
                gradient_field_dict = bilateral_result["gradient_field"]

        # =====================================================================
        # STEP 3d: Barrier Prevalence Analysis (Retargeting Intelligence)
        #
        # Uses learned posteriors from the retargeting system to understand
        # which conversion barriers are most common for this archetype.
        # This intelligence feeds into mechanism selection — if 40% of
        # careful_trusters hit trust_deficit, first-touch should preemptively
        # deploy evidence_proof or social_proof_matched.
        # =====================================================================
        barrier_intelligence = None
        try:
            from adam.retargeting.engines.prior_manager import get_prior_manager
            _prior_mgr = get_prior_manager()
            if _prior_mgr is not None:
                barrier_prevalence = _prior_mgr.get_barrier_prevalence(primary_archetype)
                if barrier_prevalence:
                    # Get the top mechanism for each prevalent barrier
                    top_barriers = sorted(
                        barrier_prevalence.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3]

                    barrier_intelligence = {
                        "archetype": primary_archetype,
                        "barrier_prevalence": {
                            k: round(v, 4)
                            for k, v in top_barriers
                            if v > 0.05  # Only barriers affecting >5% of users
                        },
                        "recommended_preemptive_mechanisms": {},
                    }

                    # For each top barrier, get the best mechanism from posteriors
                    for barrier_name, prevalence in top_barriers:
                        if prevalence < 0.05:
                            continue
                        posteriors = _prior_mgr.get_all_posteriors_for_barrier(
                            barrier_name, primary_archetype
                        )
                        if posteriors:
                            best_mech = max(
                                posteriors.items(),
                                key=lambda x: x[1].mean,
                            )
                            barrier_intelligence["recommended_preemptive_mechanisms"][
                                barrier_name
                            ] = {
                                "mechanism": best_mech[0],
                                "posterior_mean": round(best_mech[1].mean, 4),
                                "sample_count": best_mech[1].sample_count,
                            }

                    if barrier_intelligence["barrier_prevalence"]:
                        components_used.append("BarrierIntelligence")
                        trace.steps.append(EvidenceItem(
                            source=DataSourceType.GRAPH,
                            description=(
                                f"Barrier analysis: top barriers for {primary_archetype} — "
                                + ", ".join(
                                    f"{b} ({p:.0%})"
                                    for b, p in barrier_intelligence["barrier_prevalence"].items()
                                )
                            ),
                            confidence=0.7,
                            data=barrier_intelligence,
                        ))
        except Exception as e:
            logger.debug("Barrier intelligence skipped: %s", e)

        # =====================================================================
        # STEP 4: Execute AtomDAG (if available)
        # =====================================================================
        atom_result = await self._execute_atom_dag(
            brand=brand,
            product=product,
            description=description,
            customer_intelligence=customer_intelligence,
            archetype=primary_archetype,
            trace=trace,
            buyer_uncertainty=buyer_uncertainty_dict,
            gradient_field=gradient_field_dict,
            category=getattr(unified_intel, "category", None) if unified_intel else None,
            asin=asin if unified_svc else None,
        )
        if atom_result:
            components_used.append("AtomDAG")
        
        # =====================================================================
        # STEP 5: Select Mechanisms via MetaLearner
        # =====================================================================
        mechanism_selection = await self._select_mechanisms(
            archetype=primary_archetype,
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=customer_intelligence,
            trace=trace,
            unified_intel=unified_intel,
            barrier_intelligence=barrier_intelligence,
        )
        components_used.append("MetaLearner")
        
        # =====================================================================
        # STEP 6: Build Recommendations
        # =====================================================================
        segments = await self._build_segment_recommendations(
            primary_archetype=primary_archetype,
            archetype_confidence=archetype_confidence,
            mechanism_selection=mechanism_selection,
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=customer_intelligence,
            brand=brand,
            product=product,
        )
        
        stations = await self._build_station_recommendations(
            segments=segments,
            primary_archetype=primary_archetype,
        )
        
        # =====================================================================
        # STEP 6b: Get Channel Intelligence (iHeart Integration)
        # =====================================================================
        channel_intelligence = await self._get_channel_recommendations(
            archetype=primary_archetype,
            mechanisms=mechanism_selection.selected_mechanisms if mechanism_selection else [],
            trace=trace,
        )
        if channel_intelligence:
            components_used.append("ChannelIntelligence")
        
        # =====================================================================
        # STEP 7: Extract Customer Language (for copy)
        # =====================================================================
        customer_language = {}
        if customer_intelligence:
            try:
                customer_language = customer_intelligence.get_copy_language()
            except Exception:
                pass
        
        # =====================================================================
        # STEP 8: Build Final Result
        # =====================================================================
        processing_time = (time.time() - start_time) * 1000
        trace.total_processing_time_ms = processing_time
        
        # Get primary mechanism
        primary_mechanism = "authority"
        secondary_mechanisms = []
        if mechanism_selection and mechanism_selection.selected_mechanisms:
            primary_mechanism = mechanism_selection.selected_mechanisms[0]
            secondary_mechanisms = mechanism_selection.selected_mechanisms[1:3]
        
        # Determine tone and frame from archetype
        tone, frame = self._get_tone_and_frame(primary_archetype, customer_intelligence)
        
        # Generate example copy
        example_copy = self._generate_example_copy(
            brand=brand,
            product=product,
            archetype=primary_archetype,
            mechanism=primary_mechanism,
            customer_language=customer_language,
        )
        
        # Calculate overall confidence
        confidence_breakdown = {
            "archetype": archetype_confidence,
            "mechanism": mechanism_selection.mechanism_scores.get(primary_mechanism, 0.5) if mechanism_selection else 0.5,
        }
        if customer_intelligence:
            confidence_breakdown["review_intelligence"] = customer_intelligence.overall_confidence
        
        overall_confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)
        
        result = CampaignAnalysisResult(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            brand=brand,
            product=product,
            description=description,
            call_to_action=call_to_action,
            product_url=product_url,
            customer_segments=segments,
            station_recommendations=stations,
            primary_mechanism=primary_mechanism,
            secondary_mechanisms=secondary_mechanisms,
            recommended_tone=tone,
            recommended_frame=frame,
            example_copy=example_copy,
            customer_language=customer_language,
            overall_confidence=overall_confidence,
            confidence_breakdown=confidence_breakdown,
            reasoning_trace=trace if return_reasoning else None,
            processing_time_ms=processing_time,
            components_used=components_used,
            channel_recommendations=channel_intelligence,
        )
        
        logger.info(
            f"Campaign analysis {request_id} complete: "
            f"{len(segments)} segments, {len(stations)} stations, "
            f"{processing_time:.0f}ms, {overall_confidence:.0%} confidence"
        )
        
        return result
    
    # =========================================================================
    # STEP 1: REVIEW INTELLIGENCE
    # =========================================================================
    
    async def _fetch_review_intelligence(
        self,
        product_url: str,
        product_name: str,
        brand: str,
        trace: ReasoningTrace,
    ):
        """Fetch and analyze reviews from product URL."""
        start_time = time.time()
        
        orchestrator = await self._get_review_orchestrator()
        if not orchestrator:
            trace.warnings.append("Review orchestrator not available")
            return None
        
        try:
            customer_intelligence = await orchestrator.analyze_product(
                product_name=product_name,
                product_url=product_url,
                brand=brand,
                max_reviews=50,
                use_cache=True,
            )
            
            # Record in trace
            trace.data_sources.append(DataSourceInfo(
                source_type=DataSourceType.PRODUCT_REVIEWS,
                source_name=product_url,
                records_retrieved=customer_intelligence.reviews_analyzed,
                query_time_ms=(time.time() - start_time) * 1000,
                success=True,
            ))
            
            trace.review_intelligence_summary = {
                "reviews_analyzed": customer_intelligence.reviews_analyzed,
                "dominant_archetype": customer_intelligence.dominant_archetype,
                "archetype_confidence": customer_intelligence.archetype_confidence,
                "buyer_archetypes": customer_intelligence.buyer_archetypes,
                "mechanism_predictions": customer_intelligence.mechanism_predictions,
                "personality_traits": {
                    "openness": customer_intelligence.avg_openness,
                    "conscientiousness": customer_intelligence.avg_conscientiousness,
                    "extraversion": customer_intelligence.avg_extraversion,
                    "agreeableness": customer_intelligence.avg_agreeableness,
                    "neuroticism": customer_intelligence.avg_neuroticism,
                },
            }
            
            return customer_intelligence
            
        except Exception as e:
            logger.error(f"Error fetching review intelligence: {e}")
            trace.data_sources.append(DataSourceInfo(
                source_type=DataSourceType.PRODUCT_REVIEWS,
                source_name=product_url,
                records_retrieved=0,
                query_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e),
            ))
            trace.warnings.append(f"Review intelligence failed: {e}")
            return None
    
    # =========================================================================
    # STEP 2: ARCHETYPE DETERMINATION
    # =========================================================================
    
    async def _determine_archetype(
        self,
        customer_intelligence,
        description: str,
        trace: ReasoningTrace,
    ) -> tuple:
        """Determine the primary buyer archetype."""
        
        # If we have review intelligence, use its archetype
        if customer_intelligence and customer_intelligence.dominant_archetype:
            archetype = customer_intelligence.dominant_archetype
            confidence = customer_intelligence.archetype_confidence or 0.5
            
            trace.key_decisions.append({
                "decision": "archetype_determination",
                "method": "review_intelligence",
                "result": archetype,
                "confidence": confidence,
                "evidence": "Based on psychological analysis of customer reviews",
            })
            
            return archetype, confidence
        
        # Otherwise, infer from product description
        archetype, confidence = self._infer_archetype_from_description(description)
        
        trace.key_decisions.append({
            "decision": "archetype_determination",
            "method": "description_inference",
            "result": archetype,
            "confidence": confidence,
            "evidence": "Inferred from product description keywords",
        })
        
        return archetype, confidence
    
    def _infer_archetype_from_description(self, description: str) -> tuple:
        """Infer archetype from product description."""
        desc_lower = description.lower()
        
        # Keyword matching for archetype inference
        achiever_keywords = ["premium", "luxury", "elite", "exclusive", "professional", "success", "leader"]
        explorer_keywords = ["new", "innovative", "discover", "adventure", "unique", "first", "revolutionary"]
        guardian_keywords = ["safe", "secure", "protect", "reliable", "trusted", "proven", "family"]
        connector_keywords = ["share", "together", "community", "friends", "social", "connect", "belong"]
        pragmatist_keywords = ["value", "save", "deal", "affordable", "practical", "efficient", "smart"]
        
        scores = {
            "Achiever": sum(1 for k in achiever_keywords if k in desc_lower),
            "Explorer": sum(1 for k in explorer_keywords if k in desc_lower),
            "Guardian": sum(1 for k in guardian_keywords if k in desc_lower),
            "Connector": sum(1 for k in connector_keywords if k in desc_lower),
            "Pragmatist": sum(1 for k in pragmatist_keywords if k in desc_lower),
        }
        
        max_score = max(scores.values())
        if max_score > 0:
            archetype = max(scores, key=scores.get)
            confidence = min(0.7, 0.4 + max_score * 0.1)
        else:
            archetype = "Pragmatist"  # Default
            confidence = 0.4
        
        return archetype, confidence
    
    # =========================================================================
    # STEP 3: GRAPH INTELLIGENCE
    # =========================================================================
    
    async def _fetch_mechanism_intelligence(
        self,
        archetype: str,
        trace: ReasoningTrace,
    ) -> GraphQueryResult:
        """Query graph for mechanism intelligence."""
        start_time = time.time()
        
        result = await self.graph_intelligence.get_mechanism_for_archetype(archetype)
        
        trace.graph_queries.append(result)
        trace.data_sources.append(DataSourceInfo(
            source_type=DataSourceType.NEO4J_GRAPH,
            source_name=f"mechanisms_for_{archetype}",
            records_retrieved=result.nodes_returned,
            query_time_ms=(time.time() - start_time) * 1000,
            success=result.nodes_returned > 0,
        ))
        
        return result
    
    # =========================================================================
    # STEP 3c: BILATERAL CASCADE + INFORMATION VALUE
    # =========================================================================

    async def _run_bilateral_cascade(
        self,
        asin: Optional[str],
        archetype: str,
        trace: ReasoningTrace,
        buyer_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run the bilateral cascade to get gradient fields and information value.

        Returns a dict with bilateral cascade results, buyer_uncertainty, and
        gradient_field for injection into downstream atoms.
        """
        try:
            from adam.api.stackadapt.graph_cache import get_graph_cache
            from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

            graph_cache = get_graph_cache()

            # Build a segment_id from archetype
            segment_id = f"informativ_{archetype}"

            result = run_bilateral_cascade(
                segment_id=segment_id,
                graph_cache=graph_cache,
                asin=asin,
                buyer_id=buyer_id,
            )

            cascade_dict: Dict[str, Any] = {
                "cascade_level": result.cascade_level,
                "primary_mechanism": result.primary_mechanism,
                "secondary_mechanism": result.secondary_mechanism,
                "confidence": result.confidence,
                "edge_count": result.edge_count,
            }

            # Extract buyer uncertainty for atoms
            if result.information_value:
                cascade_dict["information_value"] = {
                    "exploration_priority": result.information_value.exploration_priority,
                    "bid_premium": result.information_value.recommended_bid_premium,
                    "buyer_confidence": result.information_value.buyer_confidence,
                }

            # Extract gradient field for atoms
            if result.gradient_intelligence:
                gf = result.gradient_intelligence
                gradient_dict = {}
                if hasattr(gf, "optimization_priorities"):
                    for p in gf.optimization_priorities:
                        gradient_dict[p.dimension] = p.expected_lift_delta
                cascade_dict["gradient_field"] = gradient_dict

            # Build buyer_uncertainty dict from edge dimensions for atom injection
            if result.edge_dimensions:
                buyer_uncertainty = {}
                for dim, val in result.edge_dimensions.items():
                    buyer_uncertainty[dim] = {
                        "current_value": val,
                        "from_cascade_level": result.cascade_level,
                    }
                cascade_dict["buyer_uncertainty"] = buyer_uncertainty

            trace.steps.append(EvidenceItem(
                source=DataSourceType.GRAPH,
                description=(
                    f"Bilateral cascade L{result.cascade_level}: "
                    f"{result.primary_mechanism} (conf={result.confidence:.2f})"
                ),
                confidence=result.confidence,
                data={"cascade_level": result.cascade_level, "edge_count": result.edge_count},
            ))

            return cascade_dict

        except Exception as e:
            logger.warning(f"Bilateral cascade failed: {e}")
            return None

    # =========================================================================
    # STEP 4: ATOM DAG EXECUTION
    # =========================================================================

    async def _execute_atom_dag(
        self,
        brand: str,
        product: str,
        description: str,
        customer_intelligence,
        archetype: str,
        trace: ReasoningTrace,
        buyer_uncertainty: Optional[Dict[str, Any]] = None,
        gradient_field: Optional[Dict[str, float]] = None,
        category: Optional[str] = None,
        asin: Optional[str] = None,
    ) -> Optional[AtomDAGResult]:
        """
        Execute the AtomDAG for psychological reasoning.

        Attempts to run the REAL AtomDAG with in-memory blackboard.
        Falls back to simulation if infrastructure isn't available.
        """
        start_time = time.time()

        # Try to run the real AtomDAG
        try:
            real_result = await self._execute_real_atom_dag(
                brand=brand,
                product=product,
                description=description,
                customer_intelligence=customer_intelligence,
                archetype=archetype,
                buyer_uncertainty=buyer_uncertainty,
                gradient_field=gradient_field,
                category=category,
                asin=asin,
            )
            if real_result:
                real_result.total_execution_time_ms = (time.time() - start_time) * 1000
                trace.atom_dag_result = real_result
                logger.info(f"AtomDAG executed successfully with {len(real_result.atom_results)} atoms")
                return real_result
        except Exception as e:
            logger.warning(f"Real AtomDAG execution failed, using simulation: {e}")
        
        # Fallback to simulation
        return await self._simulate_atom_dag(
            brand=brand,
            product=product,
            description=description,
            customer_intelligence=customer_intelligence,
            archetype=archetype,
            trace=trace,
            start_time=start_time,
        )
    
    async def _execute_real_atom_dag(
        self,
        brand: str,
        product: str,
        description: str,
        customer_intelligence,
        archetype: str,
        buyer_uncertainty: Optional[Dict[str, Any]] = None,
        gradient_field: Optional[Dict[str, float]] = None,
        category: Optional[str] = None,
        asin: Optional[str] = None,
    ) -> Optional[AtomDAGResult]:
        """
        Execute the real AtomDAG using in-memory blackboard.

        Pre-fetches psychological intelligence from the graph before DAG
        execution, so atoms receive real data instead of 0.5 defaults.

        Returns None if infrastructure isn't available.
        """
        from adam.infrastructure.neo4j.client import get_neo4j_client
        from adam.blackboard.memory_blackboard import get_memory_blackboard
        from adam.graph_reasoning.bridge.interaction_bridge import InteractionBridge
        from adam.atoms.dag import AtomDAG
        from adam.orchestrator.intelligence_prefetch import get_intelligence_prefetch
        from adam.blackboard.models.zone1_context import (
            RequestContext,
            UserIntelligencePackage,
            ContentContext,
        )
        
        # Check Neo4j connection
        neo4j_client = get_neo4j_client()
        if not neo4j_client.is_connected:
            if not await neo4j_client.connect():
                logger.warning("Neo4j not available for AtomDAG")
                return None
        
        # Get blackboard (in-memory for demo)
        blackboard = get_memory_blackboard()
        
        # Create interaction bridge with Neo4j driver (no Redis cache)
        bridge = InteractionBridge(
            neo4j_driver=neo4j_client.driver,
            redis_cache=None,  # Optional - works without Redis
        )
        
        # Create AtomDAG
        atom_dag = AtomDAG(
            blackboard=blackboard,
            bridge=bridge,
        )
        
        # Create request context
        request_id = str(uuid.uuid4())
        user_id = f"demo_user_{int(time.time())}"
        
        # Initialize blackboard
        await blackboard.create_blackboard(
            request_id=request_id,
            user_id=user_id,
        )
        
        # Build user intelligence package
        user_intel = UserIntelligencePackage(
            user_id=user_id,
            is_cold_start=True,
            cold_start_tier="partial",  # We have some context from campaign
            sources_available=["campaign_input", "customer_reviews"] if customer_intelligence else ["campaign_input"],
        )
        
        # Build content context
        content_ctx = ContentContext(
            content_type="campaign",
            content_id=f"campaign_{brand}_{product}".replace(" ", "_").lower(),
        )
        
        # Build full request context
        request_context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
            content_context=content_ctx,
        )
        
        # Pre-fetch psychological intelligence from the graph
        # This is the critical step that feeds atoms with real data instead
        # of 0.5 defaults. Queries RESPONDS_TO edges, CustomerArchetype NDF,
        # GranularType matching, corpus priors, and DSP intelligence.
        ad_context = None
        try:
            prefetch = get_intelligence_prefetch()
            ad_context = await prefetch.prefetch(
                archetype=archetype,
                category=category,
                asin=asin,
                buyer_uncertainty=buyer_uncertainty,
                gradient_field=gradient_field,
            )
            logger.info(
                "Intelligence prefetch populated %d sources for atom DAG",
                ad_context.get("_prefetch_meta", {}).get("sources_count", 0),
            )
        except Exception as e:
            logger.warning("Intelligence prefetch failed (atoms will use defaults): %s", e)

        # Execute DAG with pre-fetched intelligence
        dag_result = await atom_dag.execute(
            request_id=request_id,
            request_context=request_context,
            buyer_uncertainty=buyer_uncertainty,
            gradient_field=gradient_field,
            ad_context=ad_context,
        )
        
        # Convert to our result format
        atom_result = AtomDAGResult(
            execution_order=list(dag_result.atom_results.keys()) if dag_result.atom_results else [],
        )
        
        # Extract atom results
        if dag_result.atom_outputs:
            for atom_id, output in dag_result.atom_outputs.items():
                atom_result.atom_results[atom_id] = AtomExecutionResult(
                    atom_name=atom_id,
                    atom_type=getattr(output, 'atom_type', 'inference'),
                    execution_time_ms=getattr(output, 'execution_time_ms', 0),
                    primary_output=getattr(output, 'primary_output', {}),
                    confidence=getattr(output, 'confidence', 0.5),
                    reasoning=getattr(output, 'reasoning', ''),
                )
        
        # Extract final profile from mechanism activation atom
        mech_output = dag_result.atom_outputs.get("atom_mechanism_activation") if dag_result.atom_outputs else None
        if mech_output:
            atom_result.final_psychological_profile = {
                "archetype": archetype,
                "regulatory_focus": getattr(mech_output, 'regulatory_focus', 'promotion'),
                "construal_level": getattr(mech_output, 'construal_level', 'high'),
                "recommended_mechanisms": dag_result.final_mechanisms or [],
                "mechanism_weights": dag_result.mechanism_weights or {},
            }
        else:
            atom_result.final_psychological_profile = {
                "archetype": archetype,
                "regulatory_focus": "promotion",
                "construal_level": "high",
            }
        
        logger.info(
            f"Real AtomDAG completed: {dag_result.atoms_executed} atoms executed, "
            f"{dag_result.atoms_failed} failed, {dag_result.total_duration_ms:.1f}ms"
        )
        return atom_result
    
    async def _simulate_atom_dag(
        self,
        brand: str,
        product: str,
        description: str,
        customer_intelligence,
        archetype: str,
        trace: ReasoningTrace,
        start_time: float,
    ) -> AtomDAGResult:
        """
        Simulated AtomDAG execution as fallback.
        
        Used when real AtomDAG infrastructure isn't available.
        """
        logger.info("Using simulated AtomDAG (infrastructure fallback)")
        
        atom_result = AtomDAGResult(
            execution_order=[
                "UserStateAtom",
                "RegulatoryFocusAtom",
                "ConstrualLevelAtom",
                "ReviewIntelligenceAtom",
                "PersonalityExpressionAtom",
                "MechanismActivationAtom",
            ],
        )
        
        # Simulate UserStateAtom
        atom_result.atom_results["UserStateAtom"] = AtomExecutionResult(
            atom_name="UserStateAtom",
            atom_type="inference",
            execution_time_ms=5.0,
            primary_output={"archetype": archetype},
            confidence=0.7,
            reasoning="Determined user archetype from product analysis",
        )
        
        # Simulate RegulatoryFocusAtom
        reg_focus = "promotion"
        if archetype in ["Guardian"]:
            reg_focus = "prevention"
        
        atom_result.atom_results["RegulatoryFocusAtom"] = AtomExecutionResult(
            atom_name="RegulatoryFocusAtom",
            atom_type="inference",
            execution_time_ms=3.0,
            primary_output={"regulatory_focus": reg_focus, "strength": 0.65},
            confidence=0.7,
            reasoning=f"Archetype {archetype} typically has {reg_focus} focus",
        )
        
        # Simulate ReviewIntelligenceAtom (if we have review data)
        if customer_intelligence:
            atom_result.atom_results["ReviewIntelligenceAtom"] = AtomExecutionResult(
                atom_name="ReviewIntelligenceAtom",
                atom_type="empirical",
                execution_time_ms=2.0,
                primary_output={
                    "reviews_analyzed": customer_intelligence.reviews_analyzed,
                    "dominant_archetype": customer_intelligence.dominant_archetype,
                    "mechanism_predictions": customer_intelligence.mechanism_predictions,
                },
                confidence=customer_intelligence.overall_confidence or 0.5,
                evidence_items=[
                    EvidenceItem(
                        source="product_reviews",
                        construct="buyer_archetype",
                        value=customer_intelligence.archetype_confidence or 0.5,
                        confidence=customer_intelligence.overall_confidence or 0.5,
                    ),
                ],
                reasoning=f"Analyzed {customer_intelligence.reviews_analyzed} customer reviews",
            )
        
        atom_result.total_execution_time_ms = (time.time() - start_time) * 1000
        
        # Build final outputs
        atom_result.final_psychological_profile = {
            "archetype": archetype,
            "regulatory_focus": reg_focus,
            "construal_level": "high" if archetype in ["Achiever", "Explorer"] else "low",
        }
        
        trace.atom_dag_result = atom_result
        
        return atom_result
    
    # =========================================================================
    # STEP 5: MECHANISM SELECTION
    # =========================================================================
    
    async def _select_mechanisms(
        self,
        archetype: str,
        mechanism_intelligence: GraphQueryResult,
        customer_intelligence,
        trace: ReasoningTrace,
        unified_intel: dict = None,
        barrier_intelligence: dict = None,
    ) -> MechanismSelectionResult:
        """Select optimal mechanisms using MetaLearner, with three-layer fusion."""
        
        result = MechanismSelectionResult()
        
        # Get mechanism scores from graph intelligence
        mechanism_scores = {}
        for mech in mechanism_intelligence.mechanisms:
            score = mech.archetype_effectiveness.get(archetype, 0.5)
            mechanism_scores[mech.mechanism_name.lower().replace(" ", "_")] = score

        # Blend unified three-layer fusion if available (takes priority)
        if unified_intel and unified_intel.get("mechanisms"):
            result.priors_source = "unified_three_layer_fusion"
            for m in unified_intel["mechanisms"]:
                mech_key = m["mechanism"]
                fused = m["fused_score"]
                if mech_key in mechanism_scores:
                    mechanism_scores[mech_key] = mechanism_scores[mech_key] * 0.4 + fused * 0.6
                else:
                    mechanism_scores[mech_key] = fused
            logger.info(
                f"Applied unified three-layer fusion ({len(unified_intel['mechanisms'])} mechanisms, "
                f"layers: {unified_intel.get('layers_used', [])})"
            )
        
        # If we have review intelligence, blend in its predictions
        if customer_intelligence and customer_intelligence.mechanism_predictions:
            result.review_intelligence_applied = True
            if result.priors_source != "unified_three_layer_fusion":
                result.priors_source = "review_intelligence"
            
            for mech, review_score in customer_intelligence.mechanism_predictions.items():
                if mech in mechanism_scores:
                    mechanism_scores[mech] = mechanism_scores[mech] * 0.6 + review_score * 0.4
                else:
                    mechanism_scores[mech] = review_score
        
        # Blend corpus fusion priors (from 1B+ reviews)
        try:
            from adam.fusion.prior_extraction import get_prior_extraction_service
            prior_service = get_prior_extraction_service()
            corpus_prior = prior_service.extract_prior(
                category="",  # Cross-category priors
                archetype=archetype,
            )
            if corpus_prior and corpus_prior.mechanism_priors:
                corpus_applied = 0
                blend_weight = min(0.20, corpus_prior.confidence * 0.25)
                for mech_name, prior_score in corpus_prior.get_mechanism_dict().items():
                    normalized = mech_name.lower().replace(" ", "_").replace("-", "_")
                    if normalized in mechanism_scores:
                        mechanism_scores[normalized] = (
                            (1 - blend_weight) * mechanism_scores[normalized]
                            + blend_weight * prior_score
                        )
                        corpus_applied += 1
                    else:
                        mechanism_scores[normalized] = prior_score
                        corpus_applied += 1
                if corpus_applied > 0:
                    result.priors_source = result.priors_source or "corpus_fusion"
                    logger.debug(
                        f"Corpus fusion: blended {corpus_applied} priors "
                        f"(weight={blend_weight:.2f}) into mechanism selection"
                    )
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Corpus fusion blend failed (non-fatal): {e}")

        # Blend barrier-conditioned mechanism intelligence from retargeting
        # posteriors. If retargeting has learned that evidence_proof is the
        # best mechanism for trust_deficit (which affects 35% of careful_trusters),
        # boost evidence_proof score proportionally.
        if barrier_intelligence and barrier_intelligence.get("recommended_preemptive_mechanisms"):
            barrier_boost_applied = 0
            for barrier_name, rec in barrier_intelligence["recommended_preemptive_mechanisms"].items():
                mech_key = rec["mechanism"]
                prevalence = barrier_intelligence["barrier_prevalence"].get(barrier_name, 0)
                posterior_mean = rec["posterior_mean"]
                # Boost proportional to barrier prevalence × posterior effectiveness
                # Capped at 15% blend weight — retargeting evidence supplements, not overrides
                blend_weight = min(0.15, prevalence * posterior_mean)
                if mech_key in mechanism_scores:
                    mechanism_scores[mech_key] = (
                        (1 - blend_weight) * mechanism_scores[mech_key]
                        + blend_weight * posterior_mean
                    )
                else:
                    mechanism_scores[mech_key] = posterior_mean * 0.6
                barrier_boost_applied += 1

            if barrier_boost_applied > 0:
                logger.info(
                    "Barrier intelligence: boosted %d mechanisms from retargeting posteriors",
                    barrier_boost_applied,
                )

        # Use real Thompson Sampler for mechanism selection
        from adam.cold_start.thompson.sampler import get_thompson_sampler
        thompson = get_thompson_sampler()
        
        sampling_traces = []
        used_real_thompson = False
        
        try:
            # Convert mechanism names to CognitiveMechanism enums where possible
            from adam.cold_start.models.enums import CognitiveMechanism, ArchetypeID
            
            available_mechs = []
            mech_name_map = {}  # enum -> original string name
            for mech_name in mechanism_scores:
                try:
                    cm = CognitiveMechanism(mech_name)
                    available_mechs.append(cm)
                    mech_name_map[cm] = mech_name
                except ValueError:
                    pass
            
            # Resolve archetype enum
            archetype_enum = None
            try:
                archetype_enum = ArchetypeID(archetype)
            except (ValueError, KeyError):
                pass
            
            if available_mechs:
                # Real Thompson Sampling with exploration/exploitation
                top_k = thompson.sample_top_k(
                    k=len(available_mechs),
                    archetype=archetype_enum,
                    available_mechanisms=available_mechs,
                )
                
                for rank_idx, (cm, sampled_value) in enumerate(top_k, 1):
                    mech_name = mech_name_map.get(cm, cm.value)
                    # Get actual posterior parameters
                    posteriors = thompson.posteriors.get(archetype_enum, thompson.population_posteriors) if archetype_enum else thompson.population_posteriors
                    posterior = posteriors.get(cm)
                    alpha = posterior.alpha if posterior else 2.0
                    beta_val = posterior.beta if posterior else 2.0
                    
                    sampling_traces.append(ThompsonSamplingTrace(
                        mechanism=mech_name,
                        prior_alpha=alpha,
                        prior_beta=beta_val,
                        sampled_value=sampled_value,
                        rank=rank_idx,
                    ))
                
                used_real_thompson = True
                logger.info(f"Thompson Sampling: real posteriors used for {len(top_k)} mechanisms")
        except Exception as e:
            logger.warning(f"Real Thompson Sampling failed, falling back: {e}")
        
        if not used_real_thompson:
            # Fallback: use mechanism_scores as pseudo-priors for Thompson Sampling
            import random
            for mech, base_score in mechanism_scores.items():
                alpha = max(1.0, base_score * 10)
                beta_val = max(1.0, (1 - base_score) * 10)
                sampled = random.betavariate(alpha, beta_val)
                sampling_traces.append(ThompsonSamplingTrace(
                    mechanism=mech,
                    prior_alpha=alpha,
                    prior_beta=beta_val,
                    sampled_value=sampled,
                    rank=0,
                ))
            # Sort and assign ranks
            sampling_traces.sort(key=lambda t: t.sampled_value, reverse=True)
            for i, st in enumerate(sampling_traces):
                st.rank = i + 1
        
        result.sampling_traces = sampling_traces
        result.mechanism_scores = mechanism_scores
        result.selected_mechanisms = [st.mechanism for st in sampling_traces[:3]]
        
        trace.mechanism_selection = result
        trace.key_decisions.append({
            "decision": "mechanism_selection",
            "method": "thompson_sampling",
            "result": result.selected_mechanisms,
            "scores": {st.mechanism: st.sampled_value for st in sampling_traces[:5]},
            "review_priors_applied": result.review_intelligence_applied,
        })
        
        return result
    
    # =========================================================================
    # STEP 6: BUILD RECOMMENDATIONS
    # =========================================================================
    
    async def _build_segment_recommendations(
        self,
        primary_archetype: str,
        archetype_confidence: float,
        mechanism_selection: MechanismSelectionResult,
        mechanism_intelligence: GraphQueryResult,
        customer_intelligence,
        brand: str,
        product: str,
    ) -> List[SegmentRecommendation]:
        """Build customer segment recommendations."""
        segments = []
        
        # Get all archetypes from graph
        all_archetypes = await self.graph_intelligence.get_all_archetypes()
        
        # Build segments for top archetypes
        archetypes_to_use = [primary_archetype]
        
        # Add secondary archetypes from review intelligence
        if customer_intelligence and customer_intelligence.buyer_archetypes:
            for arch, prob in sorted(
                customer_intelligence.buyer_archetypes.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                if arch != primary_archetype and prob > 0.15:
                    archetypes_to_use.append(arch)
                if len(archetypes_to_use) >= 3:
                    break
        
        # If we don't have enough, add defaults
        if len(archetypes_to_use) < 2:
            defaults = ["Achiever", "Explorer", "Pragmatist"]
            for d in defaults:
                if d not in archetypes_to_use:
                    archetypes_to_use.append(d)
                if len(archetypes_to_use) >= 3:
                    break
        
        for i, arch_name in enumerate(archetypes_to_use):
            # Find archetype details
            arch_intel = None
            for a in all_archetypes.archetypes:
                if a.archetype_name == arch_name:
                    arch_intel = a
                    break
            
            if not arch_intel:
                continue
            
            # Get mechanisms for this archetype
            arch_mechanisms = await self.graph_intelligence.get_mechanism_for_archetype(arch_name)
            
            primary_mech = "authority"
            secondary_mechs = []
            mech_explanation = "Based on psychological research"
            
            if arch_mechanisms.mechanisms:
                sorted_mechs = sorted(
                    arch_mechanisms.mechanisms,
                    key=lambda m: m.archetype_effectiveness.get(arch_name, 0),
                    reverse=True,
                )
                primary_mech = sorted_mechs[0].mechanism_name.lower().replace(" ", "_")
                secondary_mechs = [
                    m.mechanism_name.lower().replace(" ", "_") 
                    for m in sorted_mechs[1:3]
                ]
                
                effectiveness = sorted_mechs[0].archetype_effectiveness.get(arch_name, 0.5)
                mech_explanation = (
                    f"{sorted_mechs[0].mechanism_name} shows {effectiveness*100:.0f}% effectiveness "
                    f"for {arch_name} archetype based on graph intelligence"
                )
            
            # Determine evidence source
            evidence_source = "graph_inference"
            if customer_intelligence and arch_name == customer_intelligence.dominant_archetype:
                evidence_source = "review_analysis"
            
            # Build match explanation
            if evidence_source == "review_analysis":
                match_explanation = (
                    f"Based on analysis of {customer_intelligence.reviews_analyzed} real customer reviews. "
                    f"{arch_name} buyers represent "
                    f"{customer_intelligence.buyer_archetypes.get(arch_name, 0)*100:.0f}% of satisfied customers."
                )
            else:
                match_explanation = (
                    f"Inferred from product characteristics. {arch_name} archetype "
                    f"matches products with these attributes based on psychological research."
                )
            
            # Get tone and frame
            tone, frame = self._get_tone_and_frame(arch_name, customer_intelligence)
            
            # Generate example hook
            hook = self._generate_example_hook(brand, arch_name, customer_intelligence)
            
            segment = SegmentRecommendation(
                segment_id=f"{arch_name.lower()}_segment",
                segment_name=self._get_segment_name(arch_name),
                archetype=arch_name,
                match_score=archetype_confidence if i == 0 else max(0.4, archetype_confidence - 0.15 * i),
                match_explanation=match_explanation,
                personality_traits=arch_intel.personality_profile if arch_intel else {},
                regulatory_focus={
                    "promotion": 0.6 if arch_intel and arch_intel.regulatory_focus == "promotion" else 0.4,
                    "prevention": 0.6 if arch_intel and arch_intel.regulatory_focus == "prevention" else 0.4,
                },
                primary_mechanism=primary_mech,
                secondary_mechanisms=secondary_mechs,
                mechanism_explanation=mech_explanation,
                recommended_tone=tone,
                recommended_frame=frame,
                example_hook=hook,
                evidence_source=evidence_source,
                confidence=archetype_confidence if i == 0 else max(0.4, archetype_confidence - 0.1 * i),
            )
            
            segments.append(segment)
        
        return segments
    
    async def _build_station_recommendations(
        self,
        segments: List[SegmentRecommendation],
        primary_archetype: str,
    ) -> List[StationRecommendation]:
        """Build station recommendations from Neo4j iHeart data."""
        
        # Map archetypes to target emotions and traits for station matching
        archetype_profiles = {
            "Achiever": {
                "emotions": ["excitement", "anticipation", "inspiration", "admiration"],
                "traits": ["conscientiousness_high", "need_for_cognition"],
                "description": "Achievers seek content that reinforces success and ambition"
            },
            "Explorer": {
                "emotions": ["curiosity", "excitement", "anticipation", "amusement"],
                "traits": ["openness_high", "sensation_seeking"],
                "description": "Explorers seek novel, cutting-edge content"
            },
            "Guardian": {
                "emotions": ["trust", "contentment", "nostalgia", "belonging"],
                "traits": ["conscientiousness_high", "agreeableness_high"],
                "description": "Guardians value reliable, trustworthy content"
            },
            "Connector": {
                "emotions": ["connection", "joy", "belonging", "empathy"],
                "traits": ["extraversion_high", "agreeableness_high"],
                "description": "Connectors seek socially engaging content"
            },
            "Pragmatist": {
                "emotions": ["trust", "contentment", "curiosity"],
                "traits": ["conscientiousness_high", "need_for_cognition"],
                "description": "Pragmatists value informative, practical content"
            },
        }
        
        profile = archetype_profiles.get(primary_archetype, archetype_profiles["Pragmatist"])
        stations = []
        
        try:
            # Query Neo4j for stations matching the archetype's psychological profile
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            
            if client.is_connected or await client.connect():
                driver = client.driver
                async with driver.session(database='neo4j') as session:
                    # Query stations with psycholinguistic matching
                    result = await session.run("""
                        MATCH (st:Station)
                        OPTIONAL MATCH (st)-[ev:EVOKES_STATE]->(e:EmotionalState)
                        WHERE e.name IN $emotions
                        OPTIONAL MATCH (st)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
                        WHERE p.name IN $traits
                        WITH st,
                             COLLECT(DISTINCT {emotion: e.name, intensity: ev.intensity}) as emotions,
                             COLLECT(DISTINCT {trait: p.name, correlation: at.correlation}) as traits,
                             AVG(COALESCE(ev.intensity, 0)) as emotion_score,
                             AVG(COALESCE(at.correlation, 0)) as trait_score
                        WHERE emotion_score > 0 OR trait_score > 0
                        RETURN st.brand_name as name,
                               st.format as format,
                               st.description as description,
                               st.market as market,
                               emotions, traits,
                               (emotion_score * 0.5 + trait_score * 0.5) as match_score
                        ORDER BY match_score DESC
                        LIMIT 5
                    """, emotions=profile["emotions"], traits=profile["traits"])
                    
                    records = [r async for r in result]
                    
                    if records:
                        logger.info(f"Found {len(records)} stations from Neo4j for {primary_archetype}")
                        
                        for r in records:
                            format_name = r['format'] or r['name'] or "Radio Station"
                            station = StationRecommendation(
                                station_format=format_name,
                                station_description=r['description'] or f"{format_name} radio",
                                recommendation_reason=f"{profile['description']}. This station's psycholinguistic profile aligns with {primary_archetype} preferences.",
                                listener_profile_match=r['match_score'] or 0.7,
                                peak_receptivity_score=(r['match_score'] or 0.7) + 0.05,
                                best_dayparts=["Morning Drive", "Evening Drive"],
                                daypart_explanations={
                                    "Morning Drive": f"Peak engagement for {primary_archetype} archetypes during commute.",
                                    "Evening Drive": f"High receptivity as {primary_archetype}s transition from work."
                                },
                                expected_engagement="very high" if (r['match_score'] or 0) > 0.7 else "high",
                                confidence_level=r['match_score'] or 0.7,
                            )
                            stations.append(station)
                    
        except Exception as e:
            logger.warning(f"Neo4j station query failed: {e}, using format-based fallback")
        
        # If Neo4j query failed or returned nothing, use archetype-based format recommendations
        if not stations:
            logger.info(f"Using format-based station recommendations for {primary_archetype}")
            
            # Minimal fallback based on archetype (not hardcoded stations)
            format_recommendations = {
                "Achiever": [("News/Talk", "Achievers value authoritative, informational content")],
                "Explorer": [("CHR/Top 40", "Explorers seek fresh, trending content")],
                "Guardian": [("News/Talk", "Guardians trust reliable information sources")],
                "Connector": [("Hot AC", "Connectors enjoy socially shareable content")],
                "Pragmatist": [("News/Talk", "Pragmatists value practical information")],
            }
            
            for format_name, reason in format_recommendations.get(primary_archetype, format_recommendations["Pragmatist"]):
                station = StationRecommendation(
                    station_format=format_name,
                    station_description=f"{format_name} format",
                    recommendation_reason=reason,
                    listener_profile_match=0.7,
                    peak_receptivity_score=0.75,
                    best_dayparts=["Morning Drive", "Evening Drive"],
                    daypart_explanations={
                        "Morning Drive": "High engagement during commute time.",
                        "Evening Drive": "Receptive during wind-down period."
                    },
                    expected_engagement="high",
                    confidence_level=0.7,
                )
                stations.append(station)
        
        return stations
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_segment_name(self, archetype: str) -> str:
        """Get human-readable segment name."""
        names = {
            "Achiever": "Ambitious Professionals",
            "Explorer": "Curious Discoverers",
            "Guardian": "Security-Focused Protectors",
            "Connector": "Social Connectors",
            "Pragmatist": "Value-Driven Pragmatists",
        }
        return names.get(archetype, f"{archetype} Segment")
    
    def _get_tone_and_frame(self, archetype: str, customer_intelligence) -> tuple:
        """Get recommended tone and framing."""
        tones = {
            "Achiever": ("Confident and aspirational", "gain"),
            "Explorer": ("Exciting and discovery-oriented", "gain"),
            "Guardian": ("Reassuring and trustworthy", "loss-avoidance"),
            "Connector": ("Warm and inclusive", "gain"),
            "Pragmatist": ("Direct and informative", "balanced"),
        }
        
        tone, frame = tones.get(archetype, ("Professional", "balanced"))
        
        # Adjust based on review intelligence regulatory focus
        if customer_intelligence and customer_intelligence.regulatory_focus:
            reg = customer_intelligence.regulatory_focus
            if reg.get("promotion", 0) > reg.get("prevention", 0) + 0.2:
                frame = "gain"
            elif reg.get("prevention", 0) > reg.get("promotion", 0) + 0.2:
                frame = "loss-avoidance"
        
        return tone, frame
    
    def _generate_example_hook(
        self,
        brand: str,
        archetype: str,
        customer_intelligence,
    ) -> str:
        """Generate example ad hook."""
        
        # Try to use customer language from reviews
        if customer_intelligence:
            try:
                lang = customer_intelligence.get_copy_language()
                phrases = lang.get("phrases", [])
                if phrases:
                    return f'"{phrases[0]}" — Join satisfied {brand} customers.'
            except Exception:
                pass
        
        # Fallback to archetype-based hooks
        hooks = {
            "Achiever": f"Elevate your success with {brand}.",
            "Explorer": f"Discover something extraordinary with {brand}.",
            "Guardian": f"Trust {brand} to protect what matters.",
            "Connector": f"Join the {brand} community today.",
            "Pragmatist": f"Smart choice. Real value. {brand}.",
        }
        
        return hooks.get(archetype, f"Experience {brand} today.")
    
    def _generate_example_copy(
        self,
        brand: str,
        product: str,
        archetype: str,
        mechanism: str,
        customer_language: Dict,
    ) -> str:
        """Generate example ad copy."""
        
        # Use customer language if available
        power_words = customer_language.get("power_words", [])
        phrases = customer_language.get("phrases", [])
        
        word = power_words[0] if power_words else "amazing"
        phrase = phrases[0] if phrases else "exactly what you need"
        
        # Generate copy based on archetype and mechanism
        if archetype == "Achiever":
            return (
                f"Leaders choose {brand} {product}. "
                f"Join the professionals who demand {word} results. "
                f"Because success isn't accidental."
            )
        elif archetype == "Explorer":
            return (
                f"Discover the {word} {brand} {product}. "
                f"Customers say it's '{phrase}'. "
                f"Your next adventure starts here."
            )
        elif archetype == "Guardian":
            return (
                f"Trusted by families who value security. "
                f"{brand} {product} delivers {word} protection. "
                f"Because peace of mind is priceless."
            )
        elif archetype == "Connector":
            return (
                f"Your friends are already loving {brand}. "
                f"They call it '{phrase}'. "
                f"Join the community that gets it."
            )
        else:  # Pragmatist
            return (
                f"Smart customers choose {brand} {product}. "
                f"{word.title()} quality, real value. "
                f"See why '{phrase}'."
            )
    
    # =========================================================================
    # CHANNEL INTELLIGENCE (iHeart Integration)
    # =========================================================================
    
    async def _get_channel_recommendations(
        self,
        archetype: str,
        mechanisms: List[str],
        trace: ReasoningTrace,
    ):
        """
        Get channel recommendations from iHeart psycholinguistic data.
        
        Uses Neo4j to find shows/podcasts that:
        1. Evoke emotions aligned with archetype
        2. Attract personality traits of target segment
        3. Are receptive to selected persuasion mechanisms
        """
        from adam.orchestrator.models import (
            ChannelIntelligenceResult,
            ShowMatch,
            EmotionMatch,
            TraitMatch,
            PersuasionMatch,
            TimeSlotMatch,
        )
        
        start_time = time.time()
        
        # Map archetype to target emotions and traits
        archetype_emotions = {
            "Achiever": ["excitement", "anticipation", "inspiration", "admiration"],
            "Explorer": ["curiosity", "excitement", "anticipation", "amusement"],
            "Guardian": ["trust", "contentment", "nostalgia", "belonging"],
            "Connector": ["connection", "joy", "belonging", "empathy"],
            "Pragmatist": ["trust", "contentment", "curiosity"],
        }
        
        archetype_traits = {
            "Achiever": ["conscientiousness_high", "need_for_cognition", "self_monitoring"],
            "Explorer": ["openness_high", "sensation_seeking", "extraversion_high"],
            "Guardian": ["conscientiousness_high", "agreeableness_high"],
            "Connector": ["extraversion_high", "agreeableness_high", "need_for_affect"],
            "Pragmatist": ["conscientiousness_high", "need_for_cognition"],
        }
        
        target_emotions = archetype_emotions.get(archetype, ["trust", "contentment"])
        target_traits = archetype_traits.get(archetype, ["conscientiousness_high"])
        
        # Map mechanisms to persuasion techniques
        mech_to_technique = {
            "authority": ["authority", "rational_argument"],
            "social_proof": ["social_proof", "unity"],
            "scarcity": ["scarcity", "fear_appeal"],
            "reciprocity": ["reciprocity", "liking"],
            "commitment": ["commitment_consistency"],
        }
        
        persuasion_techniques = []
        for mech in mechanisms:
            mech_key = mech.lower().replace(" ", "_")
            techniques = mech_to_technique.get(mech_key, [])
            persuasion_techniques.extend(techniques)
        
        try:
            # Query Neo4j for matching shows
            shows_data = await self.graph_intelligence.get_matching_shows(
                target_emotions=target_emotions,
                target_traits=target_traits,
                persuasion_techniques=persuasion_techniques,
                min_score=0.4,
                limit=15
            )
            
            if not shows_data:
                trace.warnings.append("No channel matches found in Neo4j")
                return None
            
            # Convert to models
            recommended_shows = []
            recommended_podcasts = []
            
            for show in shows_data:
                # Convert emotion matches
                emotions = [
                    EmotionMatch(
                        emotion_name=e.get("name", ""),
                        intensity=e.get("intensity", 0),
                        valence=e.get("valence", 0),
                        arousal=e.get("arousal", 0),
                    )
                    for e in show.get("emotions", [])
                ]
                
                # Convert trait matches
                traits = [
                    TraitMatch(
                        trait_name=t.get("name", ""),
                        correlation=t.get("correlation", 0),
                        dimension=t.get("dimension"),
                    )
                    for t in show.get("traits", [])
                ]
                
                # Convert persuasion matches
                persuasion = [
                    PersuasionMatch(
                        technique_name=p.get("name", ""),
                        effectiveness=p.get("effectiveness", 0),
                        principle=p.get("principle"),
                    )
                    for p in show.get("persuasion", [])
                ]
                
                # Convert time slots
                time_slots = [
                    TimeSlotMatch(
                        slot_name=t.get("name", ""),
                        hours=t.get("hours", ""),
                        attention_level=t.get("attention", 0),
                        typical_mood=t.get("mood"),
                        persuasion_score=0.7,
                        reasoning=f"Good attention level during {t.get('name', 'slot')}",
                    )
                    for t in show.get("time_slots", [])
                ]
                
                # Build match reasoning
                reasoning_parts = []
                if emotions:
                    top_emotions = [e.emotion_name for e in emotions[:3]]
                    reasoning_parts.append(f"Evokes {', '.join(top_emotions)}")
                if traits:
                    top_traits = [t.trait_name for t in traits[:2]]
                    reasoning_parts.append(f"attracts {', '.join(top_traits)}")
                
                match_reasoning = " and ".join(reasoning_parts) if reasoning_parts else "Matches target profile"
                
                # Build synergy explanation
                synergy = f"This show's psycholinguistic profile aligns with {archetype} archetype"
                if mechanisms:
                    synergy += f" and supports {mechanisms[0]} persuasion approach"
                
                show_match = ShowMatch(
                    show_name=show.get("show_name", ""),
                    show_id=show.get("show_id"),
                    show_description=show.get("description", ""),
                    show_type=show.get("show_type", "show"),
                    station_name=show.get("station_name"),
                    station_format=show.get("station_format"),
                    air_time=show.get("air_time"),
                    days=show.get("days"),
                    emotion_score=show.get("emotion_score", 0),
                    trait_score=show.get("trait_score", 0),
                    persuasion_score=show.get("persuasion_score", 0),
                    total_score=show.get("total_score", 0),
                    matched_emotions=emotions,
                    matched_traits=traits,
                    matched_persuasion=persuasion,
                    optimal_time_slots=time_slots,
                    match_reasoning=match_reasoning,
                    synergy_explanation=synergy,
                    selection_confidence=show.get("total_score", 0),
                    evidence_sources=["neo4j_iheart_graph"],
                )
                
                if show.get("show_type") == "podcast":
                    recommended_podcasts.append(show_match)
                else:
                    recommended_shows.append(show_match)
            
            # Sort by score
            recommended_shows.sort(key=lambda s: s.total_score, reverse=True)
            recommended_podcasts.sort(key=lambda s: s.total_score, reverse=True)
            
            # Get optimal time slots across all shows
            all_time_slots = []
            for show in recommended_shows[:5]:
                all_time_slots.extend(show.optimal_time_slots)
            
            # Deduplicate time slots
            seen_slots = set()
            unique_time_slots = []
            for ts in all_time_slots:
                if ts.slot_name not in seen_slots:
                    seen_slots.add(ts.slot_name)
                    unique_time_slots.append(ts)
            
            # Build overall reasoning
            channel_reasoning = (
                f"Selected {len(recommended_shows)} shows and {len(recommended_podcasts)} podcasts "
                f"matching {archetype} archetype's psychological profile. "
                f"Target emotions: {', '.join(target_emotions[:3])}. "
                f"Target traits: {', '.join(target_traits[:2])}."
            )
            
            synergy_analysis = (
                f"Channel selection optimized for {archetype} archetype using "
                f"psycholinguistic matching across emotional states, personality traits, "
                f"and persuasion technique receptivity."
            )
            
            query_time = (time.time() - start_time) * 1000
            
            result = ChannelIntelligenceResult(
                recommended_shows=recommended_shows[:5],
                recommended_podcasts=recommended_podcasts[:5],
                optimal_time_slots=unique_time_slots[:5],
                persuasion_by_channel={
                    "radio_shows": persuasion_techniques[:3],
                    "podcasts": persuasion_techniques[:3],
                },
                channel_selection_reasoning=channel_reasoning,
                synergy_analysis=synergy_analysis,
                query_time_ms=query_time,
                shows_evaluated=len(shows_data),
                selection_method="psycholinguistic_matching",
                confidence_score=0.75 if shows_data else 0.3,
                learning_feedback_enabled=True,
            )
            
            # Record in trace
            trace.data_sources.append(DataSourceInfo(
                source_type=DataSourceType.NEO4J_GRAPH,
                source_name="iheart_psycholinguistic_graph",
                records_retrieved=len(shows_data),
                query_time_ms=query_time,
                success=True,
            ))
            
            trace.key_decisions.append({
                "decision": "channel_selection",
                "method": "psycholinguistic_matching",
                "shows_recommended": len(recommended_shows),
                "podcasts_recommended": len(recommended_podcasts),
                "target_emotions": target_emotions,
                "target_traits": target_traits,
            })
            
            logger.info(
                f"Channel intelligence: {len(recommended_shows)} shows, "
                f"{len(recommended_podcasts)} podcasts in {query_time:.0f}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting channel recommendations: {e}")
            trace.warnings.append(f"Channel intelligence error: {e}")
            return None
    
    # =========================================================================
    # LEARNING: OUTCOME PROCESSING
    # =========================================================================
    
    async def record_outcome(
        self,
        request_id: str,
        outcome_type: str,
        outcome_value: float,
        user_id: Optional[str] = None,
        mechanism_used: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record an outcome and trigger learning across all ADAM systems.
        
        This is the critical feedback loop that makes ADAM learn and improve.
        Called when:
        - User converts (outcome_type="conversion", outcome_value=1.0)
        - User clicks (outcome_type="click", outcome_value=1.0)
        - User engages (outcome_type="engagement", outcome_value=0.0-1.0)
        - User skips (outcome_type="skip", outcome_value=0.0)
        
        Learning Flow:
        1. Retrieve atom contributions from cache
        2. Process through Gradient Bridge (credit attribution)
        3. Update MetaLearner Thompson Sampling posteriors
        4. Persist outcome to Neo4j for long-term learning
        5. Emit learning signals to all components
        
        Args:
            request_id: The request_id from the original analyze_campaign call
            outcome_type: Type of outcome (conversion, click, engagement, skip)
            outcome_value: Value between 0.0 and 1.0
            user_id: Optional user identifier
            mechanism_used: Primary mechanism that was applied
            context: Additional context for learning
        
        Returns:
            Dict with learning status and components updated
        """
        logger.info(f"Recording outcome for {request_id}: {outcome_type}={outcome_value}")
        
        learning_results = {
            "request_id": request_id,
            "outcome_type": outcome_type,
            "outcome_value": outcome_value,
            "components_updated": [],
            "signals_emitted": 0,
            "errors": [],
        }
        
        user_id = user_id or f"user_{request_id}"
        context = context or {}
        
        # =====================================================================
        # STEP 1: Get Atom Contributions
        # =====================================================================
        atom_contributions = []
        try:
            from adam.atoms.core.base import BaseAtom
            atom_contributions = BaseAtom.get_all_contributions(request_id)
            if atom_contributions:
                logger.debug(f"Retrieved {len(atom_contributions)} atom contributions")
                learning_results["atom_contributions"] = len(atom_contributions)
        except Exception as e:
            logger.warning(f"Could not retrieve atom contributions: {e}")
            learning_results["errors"].append(f"Atom contributions: {e}")
        
        # =====================================================================
        # STEP 2: Process through Gradient Bridge
        # =====================================================================
        try:
            gradient_bridge = await self._get_gradient_bridge()
            if gradient_bridge:
                from adam.gradient_bridge.models.credit import OutcomeType
                
                # Map outcome type string to enum (use lowercase values)
                outcome_type_lower = outcome_type.lower()
                signal_package = await gradient_bridge.process_outcome(
                    decision_id=request_id,
                    request_id=request_id,
                    user_id=user_id,
                    outcome_type=OutcomeType(outcome_type_lower),
                    outcome_value=outcome_value,
                    mechanism_used=mechanism_used,
                )
                
                if signal_package:
                    learning_results["signals_emitted"] = len(signal_package.signals)
                    learning_results["components_updated"].append("gradient_bridge")
                    logger.info(f"Gradient Bridge emitted {len(signal_package.signals)} signals")
        except Exception as e:
            logger.warning(f"Gradient Bridge processing failed: {e}")
            learning_results["errors"].append(f"Gradient Bridge: {e}")
        
        # =====================================================================
        # STEP 3: Update MetaLearner Thompson Sampling
        # =====================================================================
        try:
            from adam.meta_learner.service import get_meta_learner
            from adam.meta_learner.models import LearningModality
            
            meta_learner = get_meta_learner()
            
            if meta_learner:
                # Determine which modality was used (default to bandit for conversions)
                modality = LearningModality.REINFORCEMENT_BANDIT
                
                # Update posteriors based on outcome
                await meta_learner.update_from_outcome(
                    decision_id=request_id,
                    modality=modality,
                    reward=outcome_value,
                )
                learning_results["components_updated"].append("meta_learner")
                logger.info(f"MetaLearner posteriors updated for {request_id}")
        except Exception as e:
            logger.warning(f"MetaLearner update failed: {e}")
            learning_results["errors"].append(f"MetaLearner: {e}")
        
        # =====================================================================
        # STEP 4: Persist Outcome to Neo4j
        # =====================================================================
        try:
            await self._persist_outcome_to_neo4j(
                request_id=request_id,
                user_id=user_id,
                outcome_type=outcome_type,
                outcome_value=outcome_value,
                mechanism_used=mechanism_used,
                context=context,
            )
            learning_results["components_updated"].append("neo4j_graph")
            logger.info(f"Outcome persisted to Neo4j for {request_id}")
        except Exception as e:
            logger.warning(f"Neo4j persistence failed: {e}")
            learning_results["errors"].append(f"Neo4j: {e}")
        
        # =====================================================================
        # STEP 5: Clean up contribution cache
        # =====================================================================
        try:
            from adam.atoms.core.base import BaseAtom
            BaseAtom.clear_contribution_cache(request_id)
        except Exception:
            pass  # Non-critical
        
        logger.info(
            f"Learning complete for {request_id}: "
            f"{len(learning_results['components_updated'])} components updated, "
            f"{learning_results['signals_emitted']} signals emitted"
        )
        
        return learning_results
    
    async def _get_gradient_bridge(self):
        """Get or create Gradient Bridge service."""
        try:
            from adam.gradient_bridge.service import GradientBridgeService
            from adam.infrastructure.neo4j.client import get_neo4j_client
            from adam.blackboard.memory_blackboard import get_memory_blackboard
            from adam.graph_reasoning.bridge.interaction_bridge import InteractionBridge
            
            neo4j_client = get_neo4j_client()
            if not neo4j_client.is_connected:
                await neo4j_client.connect()
            
            if not neo4j_client.is_connected:
                return None
            
            # Create minimal Gradient Bridge for demo
            # Note: Full version requires Redis cache
            blackboard = get_memory_blackboard()
            bridge = InteractionBridge(
                neo4j_driver=neo4j_client.driver,
                redis_cache=None,
            )
            
            # For demo, we'll use a simplified approach
            # The full GradientBridgeService requires more infrastructure
            return SimplifiedGradientBridge(neo4j_driver=neo4j_client.driver)
            
        except Exception as e:
            logger.warning(f"Could not create Gradient Bridge: {e}")
            return None
    
    async def _persist_outcome_to_neo4j(
        self,
        request_id: str,
        user_id: str,
        outcome_type: str,
        outcome_value: float,
        mechanism_used: Optional[str],
        context: Dict[str, Any],
    ) -> None:
        """Persist outcome to Neo4j for long-term learning."""
        from adam.infrastructure.neo4j.client import get_neo4j_client
        
        neo4j_client = get_neo4j_client()
        if not neo4j_client.is_connected:
            await neo4j_client.connect()
        
        if not neo4j_client.is_connected:
            raise RuntimeError("Neo4j not connected")
        
        async with neo4j_client.driver.session(database='neo4j') as session:
            # Create outcome node and link to decision context
            await session.run("""
                MERGE (o:AdOutcome {request_id: $request_id})
                SET o.outcome_type = $outcome_type,
                    o.outcome_value = $outcome_value,
                    o.mechanism_used = $mechanism_used,
                    o.user_id = $user_id,
                    o.timestamp = datetime(),
                    o.conversion = CASE WHEN $outcome_value >= 0.5 THEN true ELSE false END
                
                // Link to mechanism if specified
                WITH o
                OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_used})
                WHERE $mechanism_used IS NOT NULL
                FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (o)-[:USED_MECHANISM]->(m)
                    SET m.total_applications = COALESCE(m.total_applications, 0) + 1,
                        m.successful_applications = CASE 
                            WHEN $outcome_value >= 0.5 
                            THEN COALESCE(m.successful_applications, 0) + 1 
                            ELSE m.successful_applications 
                        END,
                        m.effectiveness_rate = CASE 
                            WHEN m.total_applications > 0 
                            THEN toFloat(m.successful_applications) / m.total_applications 
                            ELSE 0.5 
                        END
                )
                
                RETURN o.request_id as id
            """, {
                "request_id": request_id,
                "outcome_type": outcome_type,
                "outcome_value": outcome_value,
                "mechanism_used": mechanism_used,
                "user_id": user_id,
            })


class SimplifiedGradientBridge:
    """
    Simplified Gradient Bridge for demo/testing without full infrastructure.
    
    Provides core learning signal generation without Redis/Kafka dependencies.
    """
    
    def __init__(self, neo4j_driver):
        self.neo4j = neo4j_driver
    
    async def process_outcome(
        self,
        decision_id: str,
        request_id: str,
        user_id: str,
        outcome_type,
        outcome_value: float,
        mechanism_used: Optional[str] = None,
    ):
        """Process outcome and generate learning signals."""
        from adam.gradient_bridge.models.signals import SignalPackage, LearningSignal, SignalType
        from adam.gradient_bridge.models.credit import ComponentType
        
        signals = []
        
        # Generate mechanism effectiveness signal
        if mechanism_used:
            signals.append(LearningSignal(
                signal_type=SignalType.MECHANISM_EFFECTIVENESS,
                source_component=ComponentType.GRAPH,
                target_component=ComponentType.META_LEARNER,
                signal_value=outcome_value,
                request_id=request_id,
                user_id=user_id,
                context={
                    "mechanism_id": mechanism_used,
                    "outcome_type": str(outcome_type),
                },
            ))
        
        # Generate reward signal for bandit
        signals.append(LearningSignal(
            signal_type=SignalType.REWARD,
            source_component=ComponentType.GRAPH,
            target_component=ComponentType.BANDIT,
            signal_value=outcome_value,
            request_id=request_id,
            user_id=user_id,
        ))
        
        return SignalPackage(
            decision_id=decision_id,
            request_id=request_id,
            user_id=user_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            signals=signals,
            total_signals=len(signals),
        )


# =============================================================================
# SINGLETON
# =============================================================================

_orchestrator: Optional[CampaignOrchestrator] = None


def get_campaign_orchestrator() -> CampaignOrchestrator:
    """Get singleton CampaignOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CampaignOrchestrator()
    return _orchestrator
