# =============================================================================
# ADAM Behavioral Analytics: Gradient Bridge Integration
# Location: adam/behavioral_analytics/integration/gradient_bridge_integration.py
# =============================================================================

"""
BEHAVIORAL GRADIENT BRIDGE INTEGRATION

Properly integrates behavioral analytics with the existing Gradient Bridge (#06).

This is NOT a replacement - it EXTENDS the existing GradientBridgeService to:
1. Register behavioral signals as an intelligence source
2. Use existing models (LearningSignal, SignalPackage, OutcomeAttribution)
3. Propagate via Kafka Event Bus
4. Write to Blackboard shared state
5. Update Neo4j graph via InteractionBridge

Architecture Alignment:
- Uses adam.gradient_bridge.models.credit (AtomCredit, OutcomeAttribution)
- Uses adam.gradient_bridge.models.signals (LearningSignal, SignalPackage)
- Uses adam.infrastructure.kafka (ADAMTopics, get_kafka_producer)
- Uses adam.blackboard.service (BlackboardService)
- Uses adam.graph_reasoning.bridge (InteractionBridge)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.gradient_bridge.service import GradientBridgeService
from adam.gradient_bridge.models.credit import (
    AtomCredit,
    ComponentCredit,
    ComponentType,
    OutcomeAttribution,
    OutcomeType,
    AttributionMethod,
    CreditAssignmentRequest,
)
from adam.gradient_bridge.models.signals import (
    LearningSignal,
    SignalPackage,
    SignalType,
    SignalPriority,
)
from adam.gradient_bridge.models.features import (
    EnrichedFeatureVector,
    PsychologicalFeatures,
)
from adam.blackboard.service import BlackboardService
from adam.blackboard.models.core import ComponentRole
from adam.blackboard.models.zone5_learning import (
    ComponentSignal,
    SignalSource as BlackboardSignalSource,
    SignalPriority as BlackboardSignalPriority,
)
from adam.graph_reasoning.bridge import InteractionBridge
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
from adam.infrastructure.redis import ADAMRedisCache
from adam.infrastructure.prometheus import get_metrics

from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    BehavioralOutcome,
    SignalDomain,
)
from adam.behavioral_analytics.models.mechanisms import (
    CognitiveMechanism,
    UserMechanismProfile,
)

logger = logging.getLogger(__name__)


# =============================================================================
# BEHAVIORAL FEATURE EXTRACTOR
# =============================================================================

class BehavioralFeatureExtractor:
    """
    Extracts behavioral features and converts to EnrichedFeatureVector format.
    
    Follows the pattern in GradientBridgeService._extract_features()
    """
    
    # Tier 1 signals - highest predictive value from research
    TIER1_SIGNALS = {
        "pressure_mean": 0.25,
        "response_latency_mean_ms": 0.25,
        "dwell_time_mean_ms": 0.20,
    }
    
    # Tier 2 signals - strong value with context
    TIER2_SIGNALS = {
        "swipe_directness_mean": 0.15,
        "right_swipe_ratio": 0.10,
        "hesitation_count": 0.15,
        "cursor_trajectory_auc_mean": 0.20,
        "keystroke_hold_time_mean_ms": 0.18,
        "scroll_reversal_ratio": 0.12,
    }
    
    @classmethod
    def extract_to_enriched_vector(
        cls,
        session: BehavioralSession,
        request_id: str,
        user_id: str,
        inference: Optional[Dict[str, Any]] = None,
    ) -> EnrichedFeatureVector:
        """
        Extract behavioral features into EnrichedFeatureVector format.
        
        This ensures compatibility with the existing Gradient Bridge.
        """
        vector = EnrichedFeatureVector(
            request_id=request_id,
            user_id=user_id,
        )
        
        # Build psychological features from inference
        psych = PsychologicalFeatures()
        
        if inference:
            # Regulatory focus from mechanism profile
            if "regulatory_focus" in inference:
                rf_value = inference["regulatory_focus"]
                if rf_value > 0:
                    psych.regulatory_promotion = rf_value
                    psych.regulatory_prevention = 0.5 - (rf_value / 2)
                else:
                    psych.regulatory_prevention = abs(rf_value)
                    psych.regulatory_promotion = 0.5 - (abs(rf_value) / 2)
                psych.regulatory_confidence = inference.get("regulatory_focus_confidence", 0.5)
            
            # Construal level from mechanism profile
            if "construal_level" in inference:
                cl_value = inference["construal_level"]
                if cl_value > 0:
                    psych.construal_abstract = cl_value
                    psych.construal_concrete = 0.5 - (cl_value / 2)
                else:
                    psych.construal_concrete = abs(cl_value)
                    psych.construal_abstract = 0.5 - (abs(cl_value) / 2)
                psych.construal_confidence = inference.get("construal_level_confidence", 0.5)
            
            # Cognitive load
            if "cognitive_load" in inference:
                psych.cognitive_load = inference["cognitive_load"]
            
            # Purchase intent
            if "purchase_intent" in inference:
                psych.purchase_intent = inference["purchase_intent"]
        
        vector.psychological = psych
        
        # Add behavioral-specific features
        behavioral_features = cls._extract_session_features(session)
        for key, value in behavioral_features.items():
            vector.features[f"behavioral_{key}"] = value
        
        # Build the complete feature vector
        vector.build_features()
        
        return vector
    
    @classmethod
    def _extract_session_features(cls, session: BehavioralSession) -> Dict[str, float]:
        """Extract raw behavioral features from session."""
        features = {}
        
        # Signal domain
        features["has_mobile_signals"] = 1.0 if session.has_mobile_signals else 0.0
        features["has_desktop_signals"] = 1.0 if session.has_desktop_signals else 0.0
        
        # Touch dynamics (mobile)
        if session.touch_events:
            pressures = [e.get("pressure", 0.5) for e in session.touch_events if "pressure" in e]
            if pressures:
                features["pressure_mean"] = sum(pressures) / len(pressures)
                features["touch_count"] = float(len(session.touch_events))
        
        # Swipe patterns
        if session.swipe_events:
            directness = [
                e.get("directness_ratio", 0.0) for e in session.swipe_events 
                if "directness_ratio" in e
            ]
            if directness:
                features["swipe_directness_mean"] = sum(directness) / len(directness)
            
            right_swipes = sum(1 for e in session.swipe_events if e.get("direction") == "right")
            features["right_swipe_ratio"] = right_swipes / len(session.swipe_events)
        
        # Cursor dynamics (desktop)
        if session.cursor_trajectory_events:
            aucs = []
            movement_times = []
            for traj in session.cursor_trajectory_events:
                if hasattr(traj, "area_under_curve"):
                    aucs.append(traj.area_under_curve)
                if hasattr(traj, "movement_time_ms"):
                    movement_times.append(traj.movement_time_ms)
            
            if aucs:
                features["cursor_trajectory_auc_mean"] = sum(aucs) / len(aucs)
            if movement_times:
                features["cursor_movement_time_mean_ms"] = sum(movement_times) / len(movement_times)
        
        # Keystroke dynamics
        if session.keystroke_sequences:
            hold_times = []
            flight_times = []
            typing_speeds = []
            error_counts = []
            
            for seq in session.keystroke_sequences:
                if hasattr(seq, "avg_hold_time_ms"):
                    hold_times.append(seq.avg_hold_time_ms)
                if hasattr(seq, "avg_flight_time_ms"):
                    flight_times.append(seq.avg_flight_time_ms)
                if hasattr(seq, "typing_speed_cpm"):
                    typing_speeds.append(seq.typing_speed_cpm)
                if hasattr(seq, "error_count"):
                    error_counts.append(seq.error_count)
            
            if hold_times:
                features["keystroke_hold_time_mean_ms"] = sum(hold_times) / len(hold_times)
            if flight_times:
                features["keystroke_flight_time_mean_ms"] = sum(flight_times) / len(flight_times)
            if typing_speeds:
                features["keystroke_typing_speed_cpm"] = sum(typing_speeds) / len(typing_speeds)
            if error_counts:
                features["keystroke_error_count_total"] = float(sum(error_counts))
        
        # Scroll dynamics
        if session.desktop_scroll_events:
            depths = []
            reversal_counts = []
            
            for scroll in session.desktop_scroll_events:
                if hasattr(scroll, "scroll_depth_percent"):
                    depths.append(scroll.scroll_depth_percent)
                if hasattr(scroll, "reversal_count"):
                    reversal_counts.append(scroll.reversal_count)
            
            if depths:
                features["scroll_depth_percent_max"] = max(depths)
                features["scroll_depth_percent_mean"] = sum(depths) / len(depths)
            if reversal_counts:
                total_reversals = sum(reversal_counts)
                features["scroll_reversal_ratio"] = total_reversals / len(session.desktop_scroll_events)
        
        # Session temporal
        if session.duration_ms:
            features["session_duration_ms"] = float(session.duration_ms)
        
        # Hesitation events
        if hasattr(session, "hesitation_events") and session.hesitation_events:
            features["hesitation_count"] = float(len(session.hesitation_events))
        
        # Rage clicks
        if hasattr(session, "rage_click_events") and session.rage_click_events:
            features["rage_click_count"] = float(len(session.rage_click_events))
        
        return features
    
    @classmethod
    def compute_signal_credits(
        cls,
        features: Dict[str, float],
        outcome_value: float,
    ) -> Dict[str, float]:
        """
        Compute credit attribution for behavioral signals.
        
        Higher tier signals get proportionally more credit based on
        research-validated effect sizes.
        """
        credits = {}
        
        # Tier 1 signals
        for signal, weight in cls.TIER1_SIGNALS.items():
            feature_key = f"behavioral_{signal}"
            if feature_key in features:
                # Credit = weight * outcome * normalized_feature_value
                feature_value = features[feature_key]
                
                # Normalize based on signal type
                if "latency" in signal:
                    # Lower latency = higher contribution
                    contribution = max(0, 1 - (feature_value / 3000))
                elif "pressure" in signal:
                    # Direct positive correlation
                    contribution = min(1.0, feature_value)
                else:
                    contribution = min(1.0, feature_value / 1000)  # Normalize to 0-1
                
                credits[signal] = weight * outcome_value * contribution
        
        # Tier 2 signals
        for signal, weight in cls.TIER2_SIGNALS.items():
            feature_key = f"behavioral_{signal}"
            if feature_key in features:
                feature_value = features[feature_key]
                
                if "hesitation" in signal or "reversal" in signal:
                    # Higher values are negative for conversion
                    contribution = max(0, 1 - (feature_value / 5))
                elif "auc" in signal:
                    # Higher AUC = more conflict = negative for conversion
                    contribution = max(0, 1 - feature_value)
                else:
                    contribution = min(1.0, feature_value)
                
                credits[signal] = weight * outcome_value * contribution
        
        return credits


# =============================================================================
# BEHAVIORAL GRADIENT BRIDGE INTEGRATION
# =============================================================================

class BehavioralGradientBridgeIntegration:
    """
    Integrates behavioral analytics with the existing Gradient Bridge.
    
    This class extends the GradientBridgeService functionality rather than
    replacing it. It properly uses:
    
    1. Existing models from adam.gradient_bridge.models
    2. Kafka Event Bus for signal propagation
    3. Blackboard for shared state
    4. Neo4j InteractionBridge for graph updates
    
    Usage:
        integration = get_behavioral_gradient_bridge_integration()
        await integration.process_behavioral_outcome(session, outcome)
    """
    
    def __init__(
        self,
        gradient_bridge: GradientBridgeService,
        blackboard: BlackboardService,
        graph_bridge: InteractionBridge,
        cache: ADAMRedisCache,
    ):
        self.gradient_bridge = gradient_bridge
        self.blackboard = blackboard
        self.graph_bridge = graph_bridge
        self.cache = cache
        self.metrics = get_metrics()
        self.feature_extractor = BehavioralFeatureExtractor()
        
        logger.info("BehavioralGradientBridgeIntegration initialized")
    
    async def process_behavioral_outcome(
        self,
        session: BehavioralSession,
        outcome: BehavioralOutcome,
        mechanism_profile: Optional[UserMechanismProfile] = None,
        inference: Optional[Dict[str, Any]] = None,
    ) -> SignalPackage:
        """
        Process a behavioral outcome through the Gradient Bridge.
        
        This is the main entry point for behavioral learning.
        
        Args:
            session: Behavioral session with signals
            outcome: Outcome to process (conversion, click, etc.)
            mechanism_profile: Optional mechanism profile for credit attribution
            inference: Optional psychological inference
            
        Returns:
            SignalPackage with all generated learning signals
        """
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Extract enriched features
        features = self.feature_extractor.extract_to_enriched_vector(
            session=session,
            request_id=session.session_id,
            user_id=session.user_id or "unknown",
            inference=inference,
        )
        
        # Step 2: Build credit assignment request
        atom_outputs = self._build_atom_outputs(session, mechanism_profile, inference)
        
        request = CreditAssignmentRequest(
            decision_id=outcome.decision_id or f"behavioral_{session.session_id}",
            request_id=session.session_id,
            user_id=session.user_id or "unknown",
            outcome_type=self._map_outcome_type(outcome.outcome_type),
            outcome_value=outcome.outcome_value,
            atom_outputs=atom_outputs,
            mechanism_used=self._get_primary_mechanism(mechanism_profile),
            mechanisms_considered=self._get_all_mechanisms(mechanism_profile),
            execution_path="behavioral",
        )
        
        # Step 3: Process through the EXISTING Gradient Bridge
        signal_package = await self.gradient_bridge.process_outcome(
            decision_id=request.decision_id,
            request_id=request.request_id,
            user_id=request.user_id,
            outcome_type=request.outcome_type,
            outcome_value=request.outcome_value,
            atom_outputs=request.atom_outputs,
            mechanism_used=request.mechanism_used,
            execution_path=request.execution_path,
        )
        
        # Step 4: Add behavioral-specific signals
        behavioral_signals = await self._generate_behavioral_signals(
            session, outcome, features, mechanism_profile
        )
        for signal in behavioral_signals:
            signal_package.add_signal(signal)
        
        # Step 5: Update Blackboard with behavioral context
        await self._update_blackboard(session, outcome, signal_package)
        
        # Step 6: Update Neo4j graph with behavioral patterns
        await self._update_graph(session, outcome, mechanism_profile)
        
        # Step 7: Emit to Kafka for other components
        await self._emit_to_kafka(signal_package)
        
        # Metrics
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        self.metrics.learning_signals.labels(
            signal_type="behavioral_outcome",
            component="behavioral_analytics",
        ).inc()
        
        logger.info(
            f"Behavioral outcome processed: session={session.session_id}, "
            f"outcome={outcome.outcome_type.value}={outcome.outcome_value:.2f}, "
            f"{signal_package.total_signals} signals generated in {duration_ms:.1f}ms"
        )
        
        return signal_package
    
    def _build_atom_outputs(
        self,
        session: BehavioralSession,
        mechanism_profile: Optional[UserMechanismProfile],
        inference: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build atom outputs format expected by Gradient Bridge."""
        outputs = {}
        
        # Behavioral analytics "atom" output
        outputs["atom_behavioral_analytics"] = {
            "atom_type": "behavioral_analytics",
            "overall_confidence": 0.7 if session.has_mobile_signals or session.has_desktop_signals else 0.4,
            "signal_domains": [
                d.value for d in [SignalDomain.MOBILE, SignalDomain.DESKTOP]
                if (d == SignalDomain.MOBILE and session.has_mobile_signals) or
                   (d == SignalDomain.DESKTOP and session.has_desktop_signals)
            ],
            "secondary_assessments": inference or {},
        }
        
        # Mechanism profile as atom output
        if mechanism_profile:
            outputs["atom_mechanism_profile"] = {
                "atom_type": "mechanism_profile",
                "overall_confidence": mechanism_profile.overall_confidence,
                "recommended_mechanisms": [
                    m[0].value for m in mechanism_profile.get_dominant_mechanisms()
                ],
                "mechanism_weights": {
                    mech.value: getattr(mechanism_profile, mech.value)
                    for mech in CognitiveMechanism
                },
            }
        
        return outputs
    
    def _map_outcome_type(self, behavioral_outcome_type) -> OutcomeType:
        """Map behavioral outcome type to Gradient Bridge OutcomeType."""
        mapping = {
            "conversion": OutcomeType.CONVERSION,
            "click": OutcomeType.CLICK,
            "purchase": OutcomeType.CONVERSION,
            "engagement": OutcomeType.ENGAGEMENT,
            "abandonment": OutcomeType.SKIP,
            "bounce": OutcomeType.SKIP,
        }
        return mapping.get(behavioral_outcome_type.value, OutcomeType.ENGAGEMENT)
    
    def _get_primary_mechanism(
        self,
        mechanism_profile: Optional[UserMechanismProfile],
    ) -> Optional[str]:
        """Get primary mechanism from profile."""
        if not mechanism_profile:
            return None
        
        dominant = mechanism_profile.get_dominant_mechanisms(threshold=0.5)
        if dominant:
            return dominant[0][0].value
        return None
    
    def _get_all_mechanisms(
        self,
        mechanism_profile: Optional[UserMechanismProfile],
    ) -> List[str]:
        """Get all active mechanisms from profile."""
        if not mechanism_profile:
            return []
        
        active = []
        for mech in CognitiveMechanism:
            value = getattr(mechanism_profile, mech.value)
            confidence = getattr(mechanism_profile, f"{mech.value}_confidence")
            if abs(value) > 0.3 and confidence > 0.5:
                active.append(mech.value)
        
        return active
    
    async def _generate_behavioral_signals(
        self,
        session: BehavioralSession,
        outcome: BehavioralOutcome,
        features: EnrichedFeatureVector,
        mechanism_profile: Optional[UserMechanismProfile],
    ) -> List[LearningSignal]:
        """Generate behavioral-specific learning signals."""
        signals = []
        
        # Signal for hypothesis engine (behavioral pattern validation)
        signal_credits = self.feature_extractor.compute_signal_credits(
            features.features,
            outcome.outcome_value,
        )
        
        if signal_credits:
            signals.append(LearningSignal(
                signal_type=SignalType.REWARD,
                priority=SignalPriority.MEDIUM,
                source_component=ComponentType.GRAPH,
                target_component=ComponentType.BANDIT,
                signal_value=outcome.outcome_value,
                user_id=session.user_id,
                request_id=session.session_id,
                decision_id=outcome.decision_id,
                payload={
                    "signal_source": "behavioral_analytics",
                    "signal_credits": signal_credits,
                    "signal_domains": [
                        SignalDomain.MOBILE.value if session.has_mobile_signals else None,
                        SignalDomain.DESKTOP.value if session.has_desktop_signals else None,
                    ],
                },
            ))
        
        # Signal for mechanism effectiveness learning
        if mechanism_profile:
            for mech in CognitiveMechanism:
                mech_value = getattr(mechanism_profile, mech.value)
                mech_conf = getattr(mechanism_profile, f"{mech.value}_confidence")
                
                if abs(mech_value) > 0.3 and mech_conf > 0.5:
                    signals.append(LearningSignal(
                        signal_type=SignalType.MECHANISM_EFFECTIVENESS,
                        priority=SignalPriority.HIGH,
                        source_component=ComponentType.GRAPH,
                        target_component=ComponentType.GRAPH,
                        signal_value=outcome.outcome_value * mech_value,
                        user_id=session.user_id,
                        payload={
                            "mechanism_id": mech.value,
                            "mechanism_value": mech_value,
                            "mechanism_confidence": mech_conf,
                            "outcome_positive": outcome.outcome_value > 0.5,
                        },
                    ))
        
        # Signal for profile update
        signals.append(LearningSignal(
            signal_type=SignalType.PROFILE_UPDATE,
            priority=SignalPriority.MEDIUM,
            source_component=ComponentType.GRAPH,
            target_component=ComponentType.GRAPH,
            signal_value=outcome.outcome_value,
            user_id=session.user_id,
            payload={
                "update_type": "behavioral_outcome",
                "session_id": session.session_id,
                "has_mobile_signals": session.has_mobile_signals,
                "has_desktop_signals": session.has_desktop_signals,
            },
        ))
        
        return signals
    
    async def _update_blackboard(
        self,
        session: BehavioralSession,
        outcome: BehavioralOutcome,
        signal_package: SignalPackage,
    ) -> None:
        """Update Blackboard with behavioral outcome context."""
        try:
            # Write to Zone 5: Learning Signals using ComponentSignal
            signal = ComponentSignal(
                source=BlackboardSignalSource.OUTCOME,
                source_component_id="behavioral_analytics",
                source_component_type="behavioral_analytics_engine",
                target_construct="behavioral_outcome",
                target_entity_id=session.session_id,
                signal_type="outcome",
                signal_value=outcome.outcome_value,
                signal_direction="positive" if outcome.outcome_value > 0.5 else "negative",
                user_id=session.user_id,
                request_id=session.session_id,
                decision_id=outcome.decision_id,
                confidence=0.8,
                priority=BlackboardSignalPriority.MEDIUM,
            )
            
            await self.blackboard.write_zone5_signal(
                request_id=session.session_id,
                signal=signal,
                role=ComponentRole.ATOM,  # Behavioral analytics acts as an atom-like component
            )
        except Exception as e:
            logger.error(f"Failed to update Blackboard: {e}")
    
    async def _update_graph(
        self,
        session: BehavioralSession,
        outcome: BehavioralOutcome,
        mechanism_profile: Optional[UserMechanismProfile],
    ) -> None:
        """Update Neo4j graph with behavioral patterns."""
        try:
            # Update user-mechanism relationships via decision attribution
            if mechanism_profile and session.user_id:
                from adam.graph_reasoning.models.reasoning_output import (
                    DecisionAttribution,
                    OutcomeType as GraphOutcomeType,
                )
                
                # Build mechanism attributions from profile
                mechanism_attributions = {}
                for mech in CognitiveMechanism:
                    mech_value = getattr(mechanism_profile, mech.value)
                    mech_conf = getattr(mechanism_profile, f"{mech.value}_confidence")
                    
                    if abs(mech_value) > 0.3 and mech_conf > 0.5:
                        # Contribution is based on mechanism value and confidence
                        contribution = abs(mech_value) * mech_conf
                        mechanism_attributions[mech.value] = contribution
                
                if mechanism_attributions:
                    # Normalize contributions to sum to 1
                    total = sum(mechanism_attributions.values())
                    if total > 0:
                        mechanism_attributions = {
                            k: v / total for k, v in mechanism_attributions.items()
                        }
                    
                    # Create decision attribution for graph update
                    attribution = DecisionAttribution(
                        decision_id=outcome.decision_id or f"behavioral_{session.session_id}",
                        request_id=session.session_id,
                        user_id=session.user_id,
                        outcome=GraphOutcomeType.CONVERSION if outcome.outcome_value > 0.5 else GraphOutcomeType.SKIP,
                        outcome_value=outcome.outcome_value,
                        mechanism_attributions=mechanism_attributions,
                        primary_mechanism=self._get_primary_mechanism(mechanism_profile),
                    )
                    
                    await self.graph_bridge.push_decision_attribution(attribution)
        except Exception as e:
            logger.error(f"Failed to update graph: {e}")
    
    async def _emit_to_kafka(self, signal_package: SignalPackage) -> None:
        """Emit signals to Kafka for other components."""
        try:
            producer = await get_kafka_producer()
            if producer:
                for signal in signal_package.signals:
                    if not signal.processed:
                        await producer.send(
                            ADAMTopics.SIGNALS_LEARNING,
                            value=signal.model_dump(mode="json"),
                            key=signal.target_component.value,
                        )
                        signal.processed = True
                        signal.processed_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Failed to emit to Kafka: {e}")
    
    async def get_mechanism_priors(
        self,
        user_id: str,
        mechanism_id: str,
    ) -> Dict[str, float]:
        """
        Get empirical priors for mechanism effectiveness.
        
        Used by atoms to weight evidence from behavioral signals.
        """
        return await self.gradient_bridge.inject_priors(user_id, mechanism_id)


# =============================================================================
# SINGLETON FACTORY
# =============================================================================

_integration: Optional[BehavioralGradientBridgeIntegration] = None


async def get_behavioral_gradient_bridge_integration(
    gradient_bridge: Optional[GradientBridgeService] = None,
    blackboard: Optional[BlackboardService] = None,
    graph_bridge: Optional[InteractionBridge] = None,
    cache: Optional[ADAMRedisCache] = None,
) -> BehavioralGradientBridgeIntegration:
    """
    Get or create the behavioral gradient bridge integration.
    
    Uses dependency injection for proper architecture integration.
    """
    global _integration
    
    if _integration is None:
        if not all([gradient_bridge, blackboard, graph_bridge, cache]):
            raise ValueError(
                "BehavioralGradientBridgeIntegration requires all dependencies on first init: "
                "gradient_bridge, blackboard, graph_bridge, cache"
            )
        
        _integration = BehavioralGradientBridgeIntegration(
            gradient_bridge=gradient_bridge,
            blackboard=blackboard,
            graph_bridge=graph_bridge,
            cache=cache,
        )
    
    return _integration
