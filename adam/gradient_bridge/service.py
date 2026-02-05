# =============================================================================
# ADAM Gradient Bridge Service
# Location: adam/gradient_bridge/service.py
# =============================================================================

"""
GRADIENT BRIDGE SERVICE

Central orchestrator for cross-component learning.

Responsibilities:
1. Receive outcome events
2. Compute credit attribution
3. Extract enriched features
4. Propagate signals to all components
5. Update graph, bandit, meta-learner
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.gradient_bridge.models.credit import (
    OutcomeAttribution,
    OutcomeType,
    ComponentType,
    CreditAssignmentRequest,
)
from adam.gradient_bridge.models.signals import (
    LearningSignal,
    SignalPackage,
    SignalType,
    SignalPriority,
    BanditUpdateSignal,
    GraphUpdateSignal,
)
from adam.gradient_bridge.models.features import (
    EnrichedFeatureVector,
    PsychologicalFeatures,
    ContextFeatures,
    MechanismFeatures,
)
from adam.gradient_bridge.attribution import CreditAttributor
from adam.blackboard.service import BlackboardService
from adam.blackboard.models.core import ComponentRole
from adam.graph_reasoning.bridge import InteractionBridge
from adam.infrastructure.redis import ADAMRedisCache, CacheKeyBuilder
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
from adam.infrastructure.prometheus import get_metrics

# Import helpful vote weighting for proper learning signal weighting
try:
    from adam.intelligence.helpful_vote_weighting import (
        get_helpful_vote_weighter,
        HelpfulVoteWeighter,
    )
    HELPFUL_VOTE_WEIGHTING_AVAILABLE = True
except ImportError:
    HELPFUL_VOTE_WEIGHTING_AVAILABLE = False
    get_helpful_vote_weighter = None
from adam.intelligence.graph_edge_service import (
    get_graph_edge_service,
    GraphEdgeService,
    LearningPathAttribution,
)

logger = logging.getLogger(__name__)


class GradientBridgeService:
    """
    Main service for the Gradient Bridge.
    
    Orchestrates learning signal flow across all ADAM components.
    """
    
    def __init__(
        self,
        blackboard: BlackboardService,
        bridge: InteractionBridge,
        cache: ADAMRedisCache,
        graph_edge_service: Optional[GraphEdgeService] = None,
    ):
        self.blackboard = blackboard
        self.bridge = bridge
        self.cache = cache
        self.attributor = CreditAttributor()
        self.metrics = get_metrics()
        self.graph_edge_service = graph_edge_service or get_graph_edge_service()
    
    async def process_outcome(
        self,
        decision_id: str,
        request_id: str,
        user_id: str,
        outcome_type: OutcomeType,
        outcome_value: float,
        atom_outputs: Optional[Dict[str, Any]] = None,
        mechanism_used: Optional[str] = None,
        execution_path: str = "",
    ) -> SignalPackage:
        """
        Process an outcome and propagate learning signals.
        
        This is the main entry point for learning from outcomes.
        
        The learning flow:
        1. Retrieve atom contributions from cache (enables multi-level credit)
        2. Compute credit attribution using multiple methods (Shapley, etc.)
        3. Extract enriched features for future learning
        4. Generate and propagate signals to all components
        5. Update graph with outcome data
        6. Clean up contribution cache
        """
        start_time = datetime.now(timezone.utc)
        
        # Step 0: Retrieve atom contributions for enhanced attribution
        atom_contributions = []
        try:
            from adam.atoms.core.base import BaseAtom
            atom_contributions = BaseAtom.get_all_contributions(request_id)
            if atom_contributions:
                logger.debug(
                    f"Retrieved {len(atom_contributions)} atom contributions for {request_id}"
                )
        except ImportError:
            logger.debug("BaseAtom not available for contribution retrieval")
        except Exception as e:
            logger.warning(f"Failed to retrieve atom contributions: {e}")
        
        # Step 1: Compute credit attribution
        request = CreditAssignmentRequest(
            decision_id=decision_id,
            request_id=request_id,
            user_id=user_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            atom_outputs=atom_outputs or {},
            mechanism_used=mechanism_used,
            execution_path=execution_path,
        )
        attribution = await self.attributor.compute_attribution(request)
        
        # Step 2: Extract enriched features
        features = await self._extract_features(
            request_id, user_id, atom_outputs or {}
        )
        
        # Step 3: Generate signal package
        package = await self._generate_signals(
            attribution, features, mechanism_used
        )
        
        # Step 4: Propagate signals in parallel
        await self._propagate_signals(package)
        
        # Step 5: Update graph
        await self._update_graph(attribution)
        
        # Step 5b: Persist outcome to graph for learning path completion
        await self.persist_outcome_to_graph(
            decision_id=decision_id,
            outcome_type=outcome_type.value,
            outcome_value=outcome_value,
        )
        
        # Step 5c: Update brand-archetype effectiveness (NEW - Brand Personality Integration)
        await self._update_brand_learning(
            atom_outputs=atom_outputs or {},
            outcome_value=outcome_value,
        )
        
        # Step 5d: Update relationship-mechanism effectiveness (Consumer-Brand Relationship Integration)
        await self._update_relationship_learning(
            atom_outputs=atom_outputs or {},
            outcome_value=outcome_value,
            mechanism_used=mechanism_used,
        )
        
        # Step 6: Cache attribution
        await self._cache_attribution(attribution)
        
        # Record metrics
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        self.metrics.learning_signals.labels(
            signal_type="outcome",
            component="gradient_bridge",
        ).inc()
        
        # Step 7: Clean up atom contribution cache
        try:
            from adam.atoms.core.base import BaseAtom
            BaseAtom.clear_contribution_cache(request_id)
        except Exception:
            pass  # Non-critical cleanup
        
        logger.info(
            f"Processed outcome for decision {decision_id}: "
            f"{outcome_type.value}={outcome_value:.2f}, "
            f"{package.total_signals} signals generated, "
            f"{len(atom_contributions)} atom contributions"
        )
        
        return package
    
    async def _extract_features(
        self,
        request_id: str,
        user_id: str,
        atom_outputs: Dict[str, Any],
    ) -> EnrichedFeatureVector:
        """Extract enriched feature vector from atom outputs."""
        
        vector = EnrichedFeatureVector(
            request_id=request_id,
            user_id=user_id,
        )
        
        # Extract psychological features from atoms
        psych = PsychologicalFeatures()
        
        # Regulatory focus atom
        rf_output = atom_outputs.get("atom_regulatory_focus")
        if rf_output:
            if isinstance(rf_output, dict):
                secondary = rf_output.get("secondary_assessments", {})
                psych.regulatory_promotion = secondary.get("promotion_tendency", 0.5)
                psych.regulatory_prevention = secondary.get("prevention_tendency", 0.5)
                psych.regulatory_confidence = rf_output.get("overall_confidence", 0.5)
            elif hasattr(rf_output, "secondary_assessments"):
                psych.regulatory_promotion = rf_output.secondary_assessments.get("promotion_tendency", 0.5)
                psych.regulatory_prevention = rf_output.secondary_assessments.get("prevention_tendency", 0.5)
                psych.regulatory_confidence = rf_output.overall_confidence
        
        # Construal level atom
        cl_output = atom_outputs.get("atom_construal_level")
        if cl_output:
            if isinstance(cl_output, dict):
                secondary = cl_output.get("secondary_assessments", {})
                psych.construal_abstract = secondary.get("abstract_tendency", 0.5)
                psych.construal_concrete = secondary.get("concrete_tendency", 0.5)
                psych.construal_confidence = cl_output.get("overall_confidence", 0.5)
            elif hasattr(cl_output, "secondary_assessments"):
                psych.construal_abstract = cl_output.secondary_assessments.get("abstract_tendency", 0.5)
                psych.construal_concrete = cl_output.secondary_assessments.get("concrete_tendency", 0.5)
                psych.construal_confidence = cl_output.overall_confidence
        
        vector.psychological = psych
        
        # Build the complete feature vector
        vector.build_features()
        
        return vector
    
    async def _generate_signals(
        self,
        attribution: OutcomeAttribution,
        features: EnrichedFeatureVector,
        mechanism_used: Optional[str],
    ) -> SignalPackage:
        """Generate learning signals for all components."""
        
        package = SignalPackage(
            decision_id=attribution.decision_id,
            request_id=attribution.request_id,
            user_id=attribution.user_id,
            outcome_type=attribution.outcome_type,
            outcome_value=attribution.outcome_value,
        )
        
        # Signal for bandit
        package.add_signal(LearningSignal(
            signal_type=SignalType.REWARD,
            priority=SignalPriority.HIGH,
            source_component=ComponentType.GRAPH,
            target_component=ComponentType.BANDIT,
            signal_value=attribution.outcome_value,
            user_id=attribution.user_id,
            request_id=attribution.request_id,
            decision_id=attribution.decision_id,
            payload={
                "features": features.features,
                "mechanism": mechanism_used,
            },
        ))
        
        # Signal for graph (mechanism effectiveness)
        if mechanism_used:
            package.add_signal(LearningSignal(
                signal_type=SignalType.MECHANISM_EFFECTIVENESS,
                priority=SignalPriority.HIGH,
                source_component=ComponentType.BANDIT,
                target_component=ComponentType.GRAPH,
                signal_value=attribution.outcome_value,
                user_id=attribution.user_id,
                payload={
                    "mechanism_id": mechanism_used,
                    "credit": attribution.mechanism_credits.get(mechanism_used, 0.0),
                },
            ))
        
        # Signal for meta-learner
        package.add_signal(LearningSignal(
            signal_type=SignalType.CREDIT,
            priority=SignalPriority.MEDIUM,
            source_component=ComponentType.GRAPH,
            target_component=ComponentType.META_LEARNER,
            signal_value=attribution.outcome_value,
            user_id=attribution.user_id,
            payload={
                "execution_path": attribution.execution_path,
                "modality": attribution.meta_learner_modality,
            },
        ))
        
        # Signals for each atom
        for atom_credit in attribution.atom_credits:
            package.add_signal(LearningSignal(
                signal_type=SignalType.CREDIT,
                priority=SignalPriority.LOW,
                source_component=ComponentType.GRAPH,
                target_component=ComponentType(f"atom_{atom_credit.atom_type}") if atom_credit.atom_type.startswith("regulatory") or atom_credit.atom_type.startswith("construal") or atom_credit.atom_type.startswith("mechanism") else ComponentType.ATOM_MECHANISM,
                signal_value=atom_credit.credit_score,
                payload={
                    "atom_id": atom_credit.atom_id,
                    "credit_share": atom_credit.credit_share,
                },
            ))
        
        return package
    
    async def _propagate_signals(self, package: SignalPackage) -> None:
        """
        Propagate signals via Kafka AND Unified Learning Hub.
        
        BELT & SUSPENDERS: Signals go to both:
        1. Kafka (for async consumers)
        2. UnifiedLearningHub (for guaranteed direct delivery)
        
        This ensures learning happens even if Kafka is slow or unavailable.
        """
        # 1. Send to Unified Learning Hub (guaranteed delivery)
        try:
            from adam.core.learning.unified_learning_hub import (
                get_unified_learning_hub,
                UnifiedLearningSignal,
            )
            hub = get_unified_learning_hub()
            
            for signal in package.signals:
                unified_signal = UnifiedLearningSignal.from_old_signal(signal)
                
                # Add extra context
                unified_signal.mechanism = signal.payload.get("mechanism") or signal.payload.get("mechanism_id")
                unified_signal.user_id = signal.user_id or package.user_id
                unified_signal.decision_id = signal.decision_id or package.decision_id
                
                await hub.process_signal(unified_signal)
                
            logger.debug(f"Routed {len(package.signals)} signals through UnifiedLearningHub")
        except ImportError:
            logger.debug("UnifiedLearningHub not available")
        except Exception as e:
            logger.warning(f"UnifiedLearningHub routing failed: {e}")
        
        # 2. Send to Kafka (async consumers)
        try:
            producer = await get_kafka_producer()
            if producer:
                for signal in package.signals:
                    await producer.send(
                        ADAMTopics.SIGNALS_LEARNING,
                        value=signal.model_dump(mode="json"),
                        key=signal.target_component.value,
                    )
                    signal.processed = True
                    signal.processed_at = datetime.now(timezone.utc)
                    package.signals_processed += 1
                
                package.fully_processed = True
        except Exception as e:
            logger.error(f"Failed to propagate signals via Kafka: {e}")
    
    async def _update_graph(self, attribution: OutcomeAttribution) -> None:
        """Update Neo4j graph with outcome data."""
        try:
            # Update user-mechanism relationships
            if attribution.primary_mechanism:
                await self.bridge.push_decision_attribution(attribution)
        except Exception as e:
            logger.error(f"Failed to update graph: {e}")
    
    async def _cache_attribution(self, attribution: OutcomeAttribution) -> None:
        """Cache the attribution for lookup."""
        key = f"adam:attribution:{attribution.decision_id}"
        await self.cache.set(
            key,
            attribution,
            ttl=86400,  # 24 hours
        )
    
    async def _update_brand_learning(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
    ) -> None:
        """
        Update brand-archetype effectiveness from outcome.
        
        NEW: Brand Personality Integration
        
        This updates:
        1. Thompson Sampling brand-archetype posteriors
        2. Neo4j brand-archetype effectiveness edges
        
        Enables learning which brand personalities work best with which
        consumer archetypes over time.
        """
        try:
            # Extract brand and archetype from atom outputs
            brand_output = atom_outputs.get("atom_brand_personality")
            personality_output = atom_outputs.get("atom_personality_expression")
            
            brand_id = None
            user_archetype = None
            
            # Get brand_id from brand personality atom
            if brand_output:
                if isinstance(brand_output, dict):
                    secondary = brand_output.get("secondary_assessments", {})
                    brand_id = secondary.get("brand_id")
                elif hasattr(brand_output, "secondary_assessments"):
                    brand_id = brand_output.secondary_assessments.get("brand_id")
            
            # Get user archetype from personality expression atom
            if personality_output:
                if isinstance(personality_output, dict):
                    secondary = personality_output.get("secondary_assessments", {})
                    user_archetype = secondary.get("archetype")
                elif hasattr(personality_output, "secondary_assessments"):
                    user_archetype = personality_output.secondary_assessments.get("archetype")
            
            if not brand_id or not user_archetype:
                logger.debug("No brand_id or user_archetype for brand learning")
                return
            
            # Convert outcome to success (binary or continuous)
            success = outcome_value >= 0.5
            
            # 1. Update Thompson Sampling posteriors
            try:
                from adam.cold_start.thompson.sampler import get_thompson_sampler
                from adam.cold_start.models.enums import ArchetypeID
                
                sampler = get_thompson_sampler()
                
                # Map string archetype to enum
                try:
                    archetype_enum = ArchetypeID(user_archetype.upper())
                except ValueError:
                    archetype_enum = ArchetypeID.ACHIEVER  # Default
                
                sampler.update_brand_archetype_posterior(
                    brand_id=brand_id,
                    archetype=archetype_enum,
                    success=success,
                )
                
                logger.debug(
                    f"Updated Thompson Sampling brand posterior: "
                    f"{brand_id} + {user_archetype} = {'success' if success else 'failure'}"
                )
                
            except ImportError:
                logger.debug("Thompson Sampler not available for brand learning")
            except Exception as e:
                logger.warning(f"Failed to update Thompson Sampling brand posterior: {e}")
            
            # 2. Update Neo4j brand-archetype effectiveness
            try:
                from adam.intelligence.knowledge_graph.brand_graph_builder import (
                    get_brand_graph_builder,
                )
                
                driver = self.bridge.neo4j_driver if hasattr(self.bridge, 'neo4j_driver') else None
                if driver:
                    builder = await get_brand_graph_builder(driver)
                    await builder.update_brand_archetype_effectiveness(
                        brand_id=brand_id,
                        archetype_name=user_archetype,
                        success=float(success),
                    )
                    
                    logger.debug(
                        f"Updated Neo4j brand-archetype effectiveness: "
                        f"{brand_id} + {user_archetype}"
                    )
                    
            except ImportError:
                logger.debug("Brand graph builder not available")
            except Exception as e:
                logger.warning(f"Failed to update Neo4j brand effectiveness: {e}")
            
        except Exception as e:
            logger.error(f"Brand learning update failed: {e}")
    
    async def _update_relationship_learning(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
        mechanism_used: Optional[str] = None,
    ) -> None:
        """
        Update relationship-mechanism effectiveness from outcome.
        
        NEW: Consumer-Brand Relationship Integration
        
        This updates:
        1. Thompson Sampling relationship-mechanism posteriors
        2. Neo4j relationship-mechanism effectiveness edges
        
        Enables learning which psychological mechanisms work best with which
        consumer-brand relationship types over time.
        """
        try:
            # Extract relationship type and mechanism from atom outputs
            relationship_output = atom_outputs.get("atom_relationship_intelligence")
            
            relationship_type = None
            
            # Get relationship_type from relationship intelligence atom
            if relationship_output:
                if isinstance(relationship_output, dict):
                    secondary = relationship_output.get("secondary_assessments", {})
                    relationship_type = secondary.get("primary_relationship_type")
                    if not relationship_type:
                        # Also check inferred_states
                        inferred = relationship_output.get("inferred_states", {})
                        relationship_type = inferred.get("relationship_type")
                elif hasattr(relationship_output, "secondary_assessments"):
                    relationship_type = relationship_output.secondary_assessments.get("primary_relationship_type")
                    if not relationship_type and hasattr(relationship_output, "inferred_states"):
                        relationship_type = relationship_output.inferred_states.get("relationship_type")
            
            if not relationship_type:
                logger.debug("No relationship_type for relationship learning")
                return
            
            # Convert outcome to success (binary or continuous)
            success = outcome_value >= 0.5
            
            # 1. Update Thompson Sampling relationship-mechanism posteriors
            if mechanism_used:
                try:
                    from adam.cold_start.thompson.sampler import get_thompson_sampler
                    from adam.cold_start.models.enums import CognitiveMechanism
                    
                    sampler = get_thompson_sampler()
                    
                    # Try to map mechanism string to enum
                    try:
                        mechanism_enum = CognitiveMechanism(mechanism_used.lower())
                    except ValueError:
                        # Try with uppercase
                        try:
                            mechanism_enum = CognitiveMechanism[mechanism_used.upper()]
                        except KeyError:
                            logger.debug(f"Unknown mechanism {mechanism_used} for relationship learning")
                            mechanism_enum = None
                    
                    if mechanism_enum:
                        sampler.update_relationship_mechanism_posterior(
                            relationship_type=relationship_type,
                            mechanism=mechanism_enum,
                            success=success,
                        )
                        
                        logger.debug(
                            f"Updated Thompson Sampling relationship-mechanism posterior: "
                            f"{relationship_type} + {mechanism_used} = {'success' if success else 'failure'}"
                        )
                    
                except ImportError:
                    logger.debug("Thompson Sampler not available for relationship learning")
                except Exception as e:
                    logger.warning(f"Failed to update Thompson Sampling relationship posterior: {e}")
            
            # 2. Update Neo4j relationship-mechanism effectiveness
            try:
                from adam.intelligence.relationship import RelationshipGraphBuilder
                
                driver = self.bridge.neo4j_driver if hasattr(self.bridge, 'neo4j_driver') else None
                if driver:
                    builder = RelationshipGraphBuilder(driver)
                    
                    # Get relationship_id if available
                    relationship_id = None
                    if relationship_output:
                        if isinstance(relationship_output, dict):
                            relationship_id = relationship_output.get("relationship_evidence", {}).get("relationship_id")
                        elif hasattr(relationship_output, "relationship_evidence") and relationship_output.relationship_evidence:
                            relationship_id = relationship_output.relationship_evidence.relationship_id
                    
                    # Record outcome for learning
                    if relationship_id:
                        await builder.record_outcome(
                            relationship_id=relationship_id,
                            ad_id=f"ad_{datetime.now(timezone.utc).isoformat()}",  # Placeholder
                            success=success,
                            engagement_score=outcome_value,
                            conversion=outcome_value >= 0.7,
                            mechanism=mechanism_used,
                        )
                        
                        logger.debug(
                            f"Updated Neo4j relationship-mechanism effectiveness: "
                            f"{relationship_type} + {mechanism_used}"
                        )
                    
            except ImportError:
                logger.debug("Relationship graph builder not available")
            except Exception as e:
                logger.warning(f"Failed to update Neo4j relationship effectiveness: {e}")
            
        except Exception as e:
            logger.error(f"Relationship learning update failed: {e}")
    
    async def get_attribution(
        self,
        decision_id: str,
    ) -> Optional[OutcomeAttribution]:
        """Get cached attribution for a decision."""
        key = f"adam:attribution:{decision_id}"
        return await self.cache.get(key, OutcomeAttribution)
    
    async def inject_priors(
        self,
        user_id: str,
        mechanism_id: str,
    ) -> Dict[str, float]:
        """
        Get empirical priors for Claude prompts.
        
        Returns historical effectiveness data for mechanism/user.
        """
        priors = {
            "historical_effectiveness": 0.5,
            "trial_count": 0,
            "confidence": 0.3,
        }
        
        try:
            # Query graph for historical data
            context = await self.bridge.query_executor.get_mechanism_history(user_id)
            if context and mechanism_id in context.mechanisms:
                mech = context.mechanisms[mechanism_id]
                priors["historical_effectiveness"] = mech.success_rate
                priors["trial_count"] = mech.trial_count
                priors["confidence"] = min(0.9, mech.trial_count / 50)
        except Exception as e:
            logger.debug(f"Failed to get priors: {e}")
        
        return priors
    
    # =========================================================================
    # GRAPH-BASED LEARNING PATH ATTRIBUTION
    # =========================================================================
    
    async def get_learning_path_attribution(
        self,
        decision_id: str,
    ) -> Optional[LearningPathAttribution]:
        """
        Get graph-based learning path attribution for a decision.
        
        Traverses Neo4j edges:
        - Decision -[:APPLIED_MECHANISM]-> Mechanism
        - Decision -[:HAD_OUTCOME]-> Outcome
        
        Returns detailed attribution with intensity-weighted credits.
        """
        return await self.graph_edge_service.get_learning_path(decision_id)
    
    async def compute_enhanced_attribution(
        self,
        decision_id: str,
        request_id: str,
        user_id: str,
        outcome_value: float,
        fallback_mechanism: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Compute enhanced credit attribution using graph traversal.
        
        This method:
        1. Queries graph for actual decision->mechanism->outcome path
        2. Uses intensity and primacy to weight credits
        3. Falls back to simple attribution if graph unavailable
        
        Returns:
            Dict mapping mechanism names to credit scores
        """
        credits = {}
        
        # Try graph-based attribution first
        learning_path = await self.get_learning_path_attribution(decision_id)
        
        if learning_path and learning_path.attribution_weights:
            # Use graph-derived attribution
            for mechanism, weight in learning_path.attribution_weights.items():
                credits[mechanism] = weight * outcome_value
            
            logger.debug(
                f"Graph-based attribution for {decision_id}: "
                f"{len(credits)} mechanisms credited"
            )
            
        elif fallback_mechanism:
            # Fallback to single mechanism
            credits[fallback_mechanism] = outcome_value
            logger.debug(f"Fallback attribution to {fallback_mechanism}")
        
        return credits
    
    async def persist_decision_to_graph(
        self,
        decision_id: str,
        user_id: str,
        mechanisms_applied: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> bool:
        """
        Persist decision and mechanism edges to Neo4j for future attribution.
        
        Creates:
        - (:AdDecision {decision_id})
        - (:User)-[:MADE_AD_DECISION]->(:AdDecision)
        - (:AdDecision)-[:APPLIED_MECHANISM]->(:CognitiveMechanism)
        
        This enables graph-based attribution when outcomes arrive.
        """
        if not self.bridge or not self.bridge.driver:
            return False
        
        query = """
        // Create or match decision
        MERGE (d:AdDecision {decision_id: $decision_id})
        SET d.created_at = datetime(),
            d.context = $context
        
        // Link to user
        WITH d
        MERGE (u:User {user_id: $user_id})
        MERGE (u)-[:MADE_AD_DECISION {timestamp: datetime()}]->(d)
        
        // Link to mechanisms
        WITH d
        UNWIND $mechanisms AS mech
        MATCH (m:CognitiveMechanism {name: mech.name})
        MERGE (d)-[:APPLIED_MECHANISM {
            intensity: mech.intensity,
            was_primary: mech.is_primary,
            activation_score: mech.score
        }]->(m)
        
        RETURN count(*) AS created
        """
        
        try:
            async with self.bridge.driver.session() as session:
                await session.run(
                    query,
                    decision_id=decision_id,
                    user_id=user_id,
                    mechanisms=[
                        {
                            "name": m.get("name") or m.get("mechanism"),
                            "intensity": m.get("intensity", 1.0),
                            "is_primary": m.get("is_primary", False),
                            "score": m.get("score", 0.5),
                        }
                        for m in mechanisms_applied
                    ],
                    context=context,
                )
                
                logger.debug(f"Persisted decision {decision_id} with {len(mechanisms_applied)} mechanisms")
                return True
                
        except Exception as e:
            logger.warning(f"Failed to persist decision to graph: {e}")
            return False
    
    async def persist_outcome_to_graph(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
    ) -> bool:
        """
        Persist outcome edge to Neo4j for learning path completion.
        
        Creates:
        - (:AdOutcome {value, type})
        - (:AdDecision)-[:HAD_OUTCOME]->(:AdOutcome)
        """
        if not self.bridge or not self.bridge.driver:
            return False
        
        query = """
        MATCH (d:AdDecision {decision_id: $decision_id})
        MERGE (o:AdOutcome {
            outcome_id: $decision_id + '_outcome',
            outcome_type: $outcome_type,
            outcome_value: $outcome_value,
            observed_at: datetime()
        })
        MERGE (d)-[:HAD_OUTCOME {
            outcome_type: $outcome_type,
            outcome_value: $outcome_value,
            observed_at: datetime()
        }]->(o)
        RETURN o.outcome_id AS outcome_id
        """
        
        try:
            async with self.bridge.driver.session() as session:
                result = await session.run(
                    query,
                    decision_id=decision_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                )
                record = await result.single()
                
                if record:
                    logger.debug(f"Persisted outcome for {decision_id}: {outcome_type}={outcome_value}")
                    return True
                    
        except Exception as e:
            logger.warning(f"Failed to persist outcome to graph: {e}")
        
        return False
    
    # =========================================================================
    # REVIEW INTELLIGENCE ATTRIBUTION
    # =========================================================================
    
    async def track_review_intelligence_contribution(
        self,
        decision_id: str,
        customer_intelligence_id: str,
        archetype_used: str,
        mechanism_predictions_used: Dict[str, float],
        language_patterns_used: bool = False,
    ) -> bool:
        """
        Track review intelligence contribution to a decision.
        
        When a decision uses CustomerIntelligence from reviews, we need to
        track this for proper credit attribution when outcomes arrive.
        
        Creates edges:
        - (:AdDecision)-[:USED_CUSTOMER_INTELLIGENCE]->(:CustomerIntelligence)
        - With metadata about what was used (archetype, mechanisms, language)
        """
        if not self.bridge or not self.bridge.driver:
            return False
        
        query = """
        MATCH (d:AdDecision {decision_id: $decision_id})
        MATCH (ci:CustomerIntelligence {product_id: $customer_intelligence_id})
        MERGE (d)-[r:USED_CUSTOMER_INTELLIGENCE]->(ci)
        SET r.archetype_used = $archetype_used,
            r.mechanism_predictions_used = $mechanism_predictions_used,
            r.language_patterns_used = $language_patterns_used,
            r.created_at = datetime()
        RETURN d.decision_id AS decision_id
        """
        
        try:
            async with self.bridge.driver.session() as session:
                result = await session.run(
                    query,
                    decision_id=decision_id,
                    customer_intelligence_id=customer_intelligence_id,
                    archetype_used=archetype_used,
                    mechanism_predictions_used=mechanism_predictions_used,
                    language_patterns_used=language_patterns_used,
                )
                record = await result.single()
                
                if record:
                    logger.debug(
                        f"Tracked review intelligence contribution for {decision_id}: "
                        f"archetype={archetype_used}"
                    )
                    return True
                    
        except Exception as e:
            logger.warning(f"Failed to track review intelligence contribution: {e}")
        
        return False
    
    async def compute_review_intelligence_credit(
        self,
        decision_id: str,
        outcome_value: float,
        helpful_votes: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Compute credit attribution for review intelligence contribution.
        
        When an outcome arrives, query how much the CustomerIntelligence
        influenced the decision and allocate credit accordingly.
        
        ENHANCED: Now includes helpful vote weighting for proper learning signal
        amplification. Reviews with higher helpful votes contribute proportionally
        more to learning (uncapped logarithmic weighting).
        
        Returns:
            Dict with 'review_intelligence_credit', 'archetype_credit', 
            'helpful_vote_weight', and 'weighted_credit'
        """
        if not self.bridge or not self.bridge.driver:
            return {}
        
        # Extended query to also retrieve helpful vote information
        query = """
        MATCH (d:AdDecision {decision_id: $decision_id})
        -[r:USED_CUSTOMER_INTELLIGENCE]->(ci:CustomerIntelligence)
        OPTIONAL MATCH (ci)-[:DERIVED_FROM]->(rev:EnhancedReview)
        RETURN 
            ci.product_id AS product_id,
            ci.dominant_archetype AS archetype,
            ci.archetype_confidence AS confidence,
            r.archetype_used AS archetype_used,
            r.mechanism_predictions_used AS mechanism_predictions,
            avg(rev.helpful_vote) AS avg_helpful_votes,
            count(rev) AS review_count
        """
        
        try:
            async with self.bridge.driver.session() as session:
                result = await session.run(query, decision_id=decision_id)
                record = await result.single()
                
                if not record:
                    return {}
                
                confidence = record.get("confidence", 0.5)
                
                # Get helpful votes - from record, parameter, or default
                avg_helpful = helpful_votes
                if avg_helpful is None:
                    avg_helpful = record.get("avg_helpful_votes") or 0
                
                # Base credit weighted by intelligence confidence
                base_credit = outcome_value * confidence
                
                # Apply helpful vote weighting if available
                vote_weight = 1.0
                if HELPFUL_VOTE_WEIGHTING_AVAILABLE and avg_helpful > 0:
                    try:
                        weighter = get_helpful_vote_weighter()
                        vote_weight = weighter.calculate_weight(int(avg_helpful))
                    except Exception as e:
                        logger.debug(f"Could not apply helpful vote weighting: {e}")
                
                # Weighted credit amplifies learning from validated reviews
                weighted_credit = base_credit * vote_weight
                
                credit_result = {
                    "review_intelligence_credit": base_credit,
                    "product_id": record.get("product_id"),
                    "archetype": record.get("archetype"),
                    "archetype_credit": weighted_credit * 0.3,  # 30% to archetype learning
                    "mechanism_credit": weighted_credit * 0.7,  # 70% to mechanism learning
                    "helpful_vote_weight": vote_weight,
                    "avg_helpful_votes": avg_helpful,
                    "review_count": record.get("review_count", 0),
                    "weighted_credit": weighted_credit,
                }
                
                # Emit learning signal for downstream consumers
                await self._emit_review_credit_signal(decision_id, credit_result)
                
                return credit_result
                    
        except Exception as e:
            logger.warning(f"Failed to compute review intelligence credit: {e}")
        
        return {}
    
    async def _emit_review_credit_signal(
        self,
        decision_id: str,
        credit_result: Dict[str, Any],
    ) -> None:
        """
        Emit a learning signal when review intelligence credit is computed.
        
        This ensures the credit flows to all learning components:
        - Thompson Sampling (via weighted mechanism credit)
        - Graph updates (via archetype credit)
        - Meta-learner (via overall weighted credit)
        """
        if credit_result.get("weighted_credit", 0) <= 0:
            return
        
        try:
            # Normalize weighted credit to [-1, 1] range for signal value
            weighted_credit = credit_result.get("weighted_credit", 0)
            signal_value = min(1.0, max(-1.0, weighted_credit))  # Clamp to valid range
            
            signal = LearningSignal(
                signal_type=SignalType.CREDIT,
                source_component=ComponentType.GRAPH,  # Gradient bridge is part of graph layer
                target_component=ComponentType.META_LEARNER,  # Route to Thompson Sampling
                signal_value=signal_value,
                signal_weight=1.0,  # Raw weight stored in payload for flexible downstream processing
                decision_id=decision_id,
                payload={
                    "credit_type": "review_intelligence",
                    "base_credit": credit_result.get("review_intelligence_credit", 0),
                    "weighted_credit": weighted_credit,
                    "helpful_vote_weight": credit_result.get("helpful_vote_weight", 1.0),
                    "mechanism_credit": credit_result.get("mechanism_credit", 0),
                    "archetype_credit": credit_result.get("archetype_credit", 0),
                    "archetype": credit_result.get("archetype"),
                    "product_id": credit_result.get("product_id"),
                    "review_count": credit_result.get("review_count", 0),
                },
                priority=SignalPriority.HIGH if credit_result.get("helpful_vote_weight", 1) > 2.0 else SignalPriority.MEDIUM,
            )
            
            # Package and publish signal
            package = SignalPackage(
                signals=[signal],
                source_decision_id=decision_id,
                created_at=datetime.now(timezone.utc),
            )
            
            await self._propagate_signals(package)
            
            logger.info(
                f"Emitted review credit signal: decision={decision_id}, "
                f"weighted_credit={credit_result.get('weighted_credit', 0):.3f}, "
                f"vote_weight={credit_result.get('helpful_vote_weight', 1):.2f}"
            )
            
        except Exception as e:
            logger.debug(f"Could not emit review credit signal: {e}")
    
    async def update_review_intelligence_learning(
        self,
        customer_intelligence_id: str,
        outcome_type: str,
        outcome_value: float,
        mechanism_used: str,
    ) -> bool:
        """
        Update CustomerIntelligence with outcome feedback.
        
        This closes the learning loop: when we see that a mechanism
        predicted by review analysis was effective, we update the
        CustomerIntelligence to reinforce that learning.
        """
        if not self.bridge or not self.bridge.driver:
            return False
        
        # Update mechanism prediction confidence based on outcome
        query = """
        MATCH (ci:CustomerIntelligence {product_id: $product_id})
        SET ci.learning_updates = coalesce(ci.learning_updates, 0) + 1,
            ci.last_outcome_type = $outcome_type,
            ci.last_outcome_value = $outcome_value,
            ci.last_mechanism_validated = $mechanism_used,
            ci.updated_at = datetime()
        RETURN ci.product_id AS product_id
        """
        
        try:
            async with self.bridge.driver.session() as session:
                result = await session.run(
                    query,
                    product_id=customer_intelligence_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                    mechanism_used=mechanism_used,
                )
                record = await result.single()
                
                if record:
                    logger.info(
                        f"Updated CustomerIntelligence {customer_intelligence_id} "
                        f"with {outcome_type}={outcome_value}"
                    )
                    return True
                    
        except Exception as e:
            logger.warning(f"Failed to update review intelligence learning: {e}")
        
        return False