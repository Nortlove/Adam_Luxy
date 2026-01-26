# =============================================================================
# ADAM Behavioral Analytics: Main Engine
# Location: adam/behavioral_analytics/engine.py
# =============================================================================

"""
BEHAVIORAL ANALYTICS ENGINE

The main orchestrator for the behavioral analytics system.

Responsibilities:
1. Session processing - extract features from events
2. Psychological inference - infer states from signals
3. Knowledge application - use validated knowledge
4. Hypothesis testing - test new signal-outcome relationships
5. Learning integration - connect to Gradient Bridge
6. Atom enhancement - provide context to atoms
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging
import uuid

from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    BehavioralOutcome,
    OutcomeType,
    TouchEvent,
    SwipeEvent,
    ScrollEvent,
    PageViewEvent,
    ClickEvent,
    # Desktop events
    CursorMoveEvent,
    CursorTrajectoryEvent,
    CursorHoverEvent,
    KeystrokeEvent,
    KeystrokeSequence,
    DesktopScrollEvent,
    SignalDomain,
)
from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    BehavioralHypothesis,
    KnowledgeValidationEvent,
    KnowledgeTier,
)
from adam.behavioral_analytics.models.mechanisms import (
    CognitiveMechanism,
    SignalSource,
    MechanismEvidence,
    UserMechanismProfile,
    MECHANISM_SIGNAL_MAP,
    MECHANISM_POLARITY,
    MechanismPolarity,
)
from adam.behavioral_analytics.knowledge.research_seeder import (
    get_research_knowledge_seeder,
)
from adam.behavioral_analytics.knowledge.graph_integration import (
    BehavioralKnowledgeGraph,
    get_behavioral_knowledge_graph,
)
from adam.behavioral_analytics.knowledge.hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)
from adam.behavioral_analytics.extensions.multimodal_extension import (
    extract_behavioral_signals,
    BehavioralModalitySignal,
    BehavioralProfileContribution,
)
from adam.behavioral_analytics.extensions.drift_extension import (
    get_behavioral_drift_detector,
)

# Signal Aggregation (#08) integration
from adam.signals.nonconscious import (
    NonconsciousAnalyticsService,
    NonconsciousProfile,
)

# Kafka integration for event emission
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics

logger = logging.getLogger(__name__)


class PsychologicalInference(BaseModel if 'BaseModel' in dir() else object):
    """Result of psychological state inference from behavioral signals."""
    
    def __init__(
        self,
        session_id: str = "",
        user_id: Optional[str] = None,
        # Core inferences
        emotional_arousal: float = 0.5,
        emotional_valence: float = 0.5,
        decision_confidence: float = 0.5,
        cognitive_load: float = 0.5,
        purchase_intent: float = 0.5,
        frustration_level: float = 0.0,
        # Regulatory focus hints
        promotion_focus_score: float = 0.5,
        prevention_focus_score: float = 0.5,
        # System 1/2 mode
        processing_mode: str = "mixed",  # "system1", "system2", "mixed"
        # Confidence
        inference_confidence: float = 0.5,
        signals_used: int = 0,
        # Supporting data
        knowledge_applied: List = None,
        feature_contributions: Dict = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.emotional_arousal = emotional_arousal
        self.emotional_valence = emotional_valence
        self.decision_confidence = decision_confidence
        self.cognitive_load = cognitive_load
        self.purchase_intent = purchase_intent
        self.frustration_level = frustration_level
        self.promotion_focus_score = promotion_focus_score
        self.prevention_focus_score = prevention_focus_score
        self.processing_mode = processing_mode
        self.inference_confidence = inference_confidence
        self.signals_used = signals_used
        self.knowledge_applied = knowledge_applied or []
        self.feature_contributions = feature_contributions or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "emotional_arousal": self.emotional_arousal,
            "emotional_valence": self.emotional_valence,
            "decision_confidence": self.decision_confidence,
            "cognitive_load": self.cognitive_load,
            "purchase_intent": self.purchase_intent,
            "frustration_level": self.frustration_level,
            "promotion_focus_score": self.promotion_focus_score,
            "prevention_focus_score": self.prevention_focus_score,
            "processing_mode": self.processing_mode,
            "inference_confidence": self.inference_confidence,
            "signals_used": self.signals_used,
            "knowledge_applied": self.knowledge_applied,
        }


class BehavioralAnalyticsEngine:
    """
    Main engine for behavioral analytics.
    
    Orchestrates:
    1. Feature extraction from sessions
    2. Psychological state inference
    3. Knowledge graph queries
    4. Hypothesis testing
    5. Learning from outcomes
    6. Integration with atoms
    """
    
    def __init__(
        self,
        neo4j_driver=None,
        gradient_bridge=None,
        nonconscious_service: Optional[NonconsciousAnalyticsService] = None,
    ):
        self._neo4j = neo4j_driver
        self._gradient_bridge = gradient_bridge
        
        # Signal Aggregation (#08) - Use existing nonconscious analytics service
        self._nonconscious_service = nonconscious_service or NonconsciousAnalyticsService()
        
        # Knowledge components
        self._knowledge_seeder = get_research_knowledge_seeder()
        self._graph = get_behavioral_knowledge_graph(neo4j_driver) if neo4j_driver else None
        self._hypothesis_engine = get_hypothesis_engine(self._graph)
        self._drift_detector = get_behavioral_drift_detector()
        
        # Cache for active knowledge
        self._knowledge_cache: Dict[str, List[BehavioralKnowledge]] = {}
        
        # Initialize research knowledge
        self._research_knowledge = self._knowledge_seeder.seed_all_knowledge()
        
        logger.info(
            f"BehavioralAnalyticsEngine initialized with "
            f"{len(self._research_knowledge)} research knowledge items, "
            f"NonconsciousAnalyticsService integrated"
        )
    
    async def initialize(self) -> None:
        """Initialize the engine (async)."""
        if self._graph:
            await self._graph.create_schema()
            
            # Seed research knowledge to graph
            for knowledge in self._research_knowledge:
                await self._graph.store_knowledge(knowledge)
            
            logger.info("Research knowledge seeded to Neo4j")
    
    async def process_session(
        self,
        session: BehavioralSession,
        include_hypothesis_testing: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a behavioral session.
        
        Extracts features, infers psychological states, and
        optionally generates/tests hypotheses.
        
        Args:
            session: The behavioral session to process
            include_hypothesis_testing: Whether to test hypotheses
            
        Returns:
            Processing result with features, inferences, signals
        """
        result = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "is_known_user": session.is_known_user,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Step 1: Extract features
        session.features = self._extract_all_features(session)
        result["features"] = session.features
        result["feature_count"] = len(session.features)
        
        # Step 2: Extract behavioral modality signals
        signals = extract_behavioral_signals(session, self._research_knowledge)
        result["signals"] = [
            {
                "signal_id": s.signal_id,
                "sub_modality": s.sub_modality.value,
                "features": s.features,
                "confidence": s.confidence,
            }
            for s in signals
        ]
        result["signal_count"] = len(signals)
        
        # Step 3: Infer psychological state
        inference = await self.infer_psychological_state(session)
        result["inference"] = inference.to_dict()
        
        # Step 4: Infer mechanism profile (maps signals to 9 cognitive mechanisms)
        mechanism_profile = await self.infer_mechanism_profile(session, inference)
        result["mechanism_profile"] = mechanism_profile.to_dict()
        result["dominant_mechanisms"] = [
            {"mechanism": m.value, "strength": s}
            for m, s in mechanism_profile.get_dominant_mechanisms()
        ]
        result["messaging_recommendations"] = mechanism_profile.get_messaging_recommendations()
        
        # Step 5: Record for drift monitoring
        self._drift_detector.record_session_features(
            session.features,
            session.device_type.value
        )
        
        # Step 6: Hypothesis testing (if enabled)
        if include_hypothesis_testing:
            hypotheses = await self._hypothesis_engine.auto_generate_hypotheses(session)
            result["hypotheses_generated"] = [h.hypothesis_id for h in hypotheses]
        
        # Step 7: Get nonconscious profile from Signal Aggregation (#08)
        nonconscious_profile = await self._get_nonconscious_profile(session)
        if nonconscious_profile:
            result["nonconscious_profile"] = {
                "approach_avoidance": nonconscious_profile.approach_avoidance.net_tendency,
                "cognitive_load": nonconscious_profile.cognitive_load.total_load,
                "processing_fluency": nonconscious_profile.processing_fluency.overall_fluency,
                "emotional_valence": nonconscious_profile.emotional_valence.valence,
                "recommended_mechanisms": nonconscious_profile.recommended_mechanisms,
            }
            # Merge nonconscious insights with inference
            inference = self._merge_nonconscious_insights(inference, nonconscious_profile)
            result["inference"] = inference.to_dict()
        
        # Step 8: Store session in graph (if available)
        if self._graph:
            await self._store_session_to_graph(session, inference, mechanism_profile)
        
        # Step 9: Emit session processed event to Kafka
        await self._emit_session_event(session, inference, mechanism_profile)
        
        logger.info(
            f"Processed session {session.session_id}: "
            f"{result['feature_count']} features, "
            f"{result['signal_count']} signals"
        )
        
        return result
    
    async def _get_nonconscious_profile(
        self,
        session: BehavioralSession,
    ) -> Optional[NonconsciousProfile]:
        """Get nonconscious profile from Signal Aggregation (#08) service."""
        try:
            if session.user_id:
                return await self._nonconscious_service.get_profile(
                    user_id=session.user_id,
                    session_id=session.session_id,
                )
            return None
        except Exception as e:
            logger.warning(f"Failed to get nonconscious profile: {e}")
            return None
    
    def _merge_nonconscious_insights(
        self,
        inference: PsychologicalInference,
        profile: NonconsciousProfile,
    ) -> PsychologicalInference:
        """Merge nonconscious profile insights into psychological inference."""
        # Approach/avoidance maps to regulatory focus
        if hasattr(profile.approach_avoidance, 'net_tendency'):
            tendency = profile.approach_avoidance.net_tendency
            if tendency > 0.1:
                inference.promotion_focus_score = max(
                    inference.promotion_focus_score, 
                    0.5 + tendency * 0.3
                )
            elif tendency < -0.1:
                inference.prevention_focus_score = max(
                    inference.prevention_focus_score,
                    0.5 + abs(tendency) * 0.3
                )
        
        # Cognitive load
        if hasattr(profile.cognitive_load, 'total_load'):
            inference.cognitive_load = max(
                inference.cognitive_load,
                profile.cognitive_load.total_load
            )
        
        # Emotional valence
        if hasattr(profile.emotional_valence, 'valence'):
            inference.emotional_valence = (
                inference.emotional_valence * 0.6 + 
                profile.emotional_valence.valence * 0.4
            )
        
        # Engagement intensity
        if hasattr(profile, 'engagement') and hasattr(profile.engagement, 'overall_engagement'):
            inference.engagement_intensity = profile.engagement.overall_engagement
        
        # Boost confidence when we have nonconscious signals
        inference.overall_confidence = min(1.0, inference.overall_confidence + 0.1)
        
        return inference
    
    async def _emit_session_event(
        self,
        session: BehavioralSession,
        inference: PsychologicalInference,
        mechanism_profile: UserMechanismProfile,
    ) -> None:
        """Emit session processed event to Kafka for downstream consumers."""
        try:
            producer = await get_kafka_producer()
            if producer:
                event = {
                    "event_type": "session_processed",
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "has_mobile_signals": session.has_mobile_signals,
                    "has_desktop_signals": session.has_desktop_signals,
                    "inference_summary": {
                        "cognitive_load": inference.cognitive_load,
                        "purchase_intent": inference.purchase_intent,
                        "emotional_arousal": inference.emotional_arousal,
                    },
                    "dominant_mechanisms": [
                        {"mechanism": m.value, "strength": s}
                        for m, s in mechanism_profile.get_dominant_mechanisms()
                    ],
                }
                
                await producer.send(
                    ADAMTopics.EVENTS_DECISION,
                    value=event,
                    key=session.session_id,
                )
        except Exception as e:
            logger.warning(f"Failed to emit session event: {e}")
    
    async def infer_psychological_state(
        self,
        session: BehavioralSession,
    ) -> PsychologicalInference:
        """
        Infer psychological state from behavioral signals.
        
        Applies research-validated knowledge to map signals to constructs.
        """
        features = session.features
        inference = PsychologicalInference(
            session_id=session.session_id,
            user_id=session.user_id,
        )
        
        signals_used = 0
        knowledge_applied = []
        
        # 1. Emotional Arousal (from touch pressure and accelerometer)
        if "pressure_mean" in features:
            # Apply knowledge: Touch pressure → Emotional arousal (89% accuracy)
            pressure = features["pressure_mean"]
            inference.emotional_arousal = min(1.0, pressure * 1.2)  # Scale
            signals_used += 1
            knowledge_applied.append("touch_pressure_arousal")
        
        if "magnitude_std" in features:
            # Apply knowledge: Accelerometer variance → Emotional arousal
            accel_var = features["magnitude_std"]
            # Combine with existing arousal estimate
            accel_arousal = min(1.0, accel_var * 0.5)
            inference.emotional_arousal = (
                inference.emotional_arousal * 0.6 + accel_arousal * 0.4
            )
            signals_used += 1
            knowledge_applied.append("accelerometer_arousal")
        
        # 2. Decision Confidence (from response latency and swipe directness)
        if "response_latency_mean" in features:
            # Apply knowledge: Response latency → Decision confidence (d=1.72)
            latency = features["response_latency_mean"]
            # 600ms threshold from research
            if latency < 600:
                inference.decision_confidence = 0.8  # High confidence
                inference.processing_mode = "system1"
            elif latency > 2000:
                inference.decision_confidence = 0.3  # Low confidence
                inference.processing_mode = "system2"
            else:
                # Linear interpolation
                inference.decision_confidence = 0.8 - ((latency - 600) / 1400) * 0.5
                inference.processing_mode = "mixed"
            signals_used += 1
            knowledge_applied.append("response_latency_confidence")
        
        if "directness_mean" in features:
            # Apply knowledge: Swipe directness → Decision confidence (r=0.30)
            directness = features["directness_mean"]
            directness_confidence = directness  # Already 0-1 scale
            # Blend with existing
            if inference.decision_confidence != 0.5:
                inference.decision_confidence = (
                    inference.decision_confidence * 0.7 + directness_confidence * 0.3
                )
            else:
                inference.decision_confidence = directness_confidence
            signals_used += 1
            knowledge_applied.append("swipe_directness_confidence")
        
        # 3. Purchase Intent (from dwell time, cart returns, previous purchases)
        purchase_signals = []
        
        if "dwell_time_mean" in features:
            # Apply knowledge: Dwell time → Purchase probability
            dwell = features["dwell_time_mean"]
            # 1.3% per 1% increase, normalized
            dwell_score = min(1.0, dwell / 5000)  # 5s = high intent
            purchase_signals.append(dwell_score)
            knowledge_applied.append("dwell_time_purchase")
        
        if session.cart_events:
            # Apply knowledge: Cart returns increase commitment
            add_count = sum(1 for e in session.cart_events if e.event_type.value == "add_to_cart")
            if add_count > 0:
                purchase_signals.append(min(1.0, add_count * 0.3))
            knowledge_applied.append("cart_behavior_purchase")
        
        if purchase_signals:
            inference.purchase_intent = sum(purchase_signals) / len(purchase_signals)
            signals_used += len(purchase_signals)
        
        # 4. Frustration Level (from rage clicks, hesitation)
        frustration_signals = []
        
        if "rage_click_count" in features:
            # Apply knowledge: Rage clicks → Frustration
            rage_count = features["rage_click_count"]
            frustration_signals.append(min(1.0, rage_count * 0.3))
            knowledge_applied.append("rage_clicks_frustration")
        
        if "hesitation_count" in features:
            hesitation = features["hesitation_count"]
            # High hesitation can indicate frustration OR uncertainty
            if inference.emotional_arousal > 0.6:
                frustration_signals.append(min(1.0, hesitation * 0.2))
        
        if frustration_signals:
            inference.frustration_level = max(frustration_signals)
            signals_used += 1
        
        # 5. Cognitive Load (from response variability, scroll reversals)
        if "response_latency_std" in features:
            latency_std = features["response_latency_std"]
            # High variability = high cognitive load
            inference.cognitive_load = min(1.0, latency_std / 2000)
            signals_used += 1
        
        if "reversal_ratio" in features:
            reversal = features["reversal_ratio"]
            # Reversals indicate re-reading = cognitive effort
            existing_load = inference.cognitive_load
            inference.cognitive_load = max(existing_load, reversal)
            signals_used += 1
        
        # 6. Regulatory Focus Hints (Mobile: swipes)
        if "right_swipe_ratio" in features:
            # Apply knowledge: Right swipe → Approach/promotion focus
            right_ratio = features["right_swipe_ratio"]
            inference.promotion_focus_score = right_ratio
            inference.prevention_focus_score = 1 - right_ratio
            signals_used += 1
            knowledge_applied.append("swipe_direction_focus")
        
        # =====================================================================
        # DESKTOP-SPECIFIC PSYCHOLOGICAL INFERENCE
        # =====================================================================
        
        # 7. Decisional Conflict (from cursor trajectories)
        # Research: AUC/MAD correlate with conflict (d=0.4-1.6)
        if "trajectory_conflict_mean" in features:
            conflict = features["trajectory_conflict_mean"]
            # Conflict inversely affects decision confidence
            conflict_adjustment = 1 - conflict
            if inference.decision_confidence != 0.5:
                # Blend with existing confidence from mobile signals
                inference.decision_confidence = (
                    inference.decision_confidence * 0.6 + conflict_adjustment * 0.4
                )
            else:
                inference.decision_confidence = conflict_adjustment
            signals_used += 1
            knowledge_applied.append("cursor_trajectory_conflict")
        
        # 8. Implicit Attitude from cursor initiation
        # Research: Fast initiation = positive automatic evaluation
        if "trajectory_initiation_mean" in features:
            initiation = features["trajectory_initiation_mean"]
            # <400ms = positive automatic, >800ms = deliberative/negative
            if initiation < 400:
                # Positive automatic evaluation → promotion
                if inference.promotion_focus_score == 0.5:
                    inference.promotion_focus_score = 0.7
                else:
                    inference.promotion_focus_score = min(
                        1.0, inference.promotion_focus_score + 0.15
                    )
                knowledge_applied.append("cursor_initiation_positive")
            elif initiation > 800:
                # Deliberative/negative → prevention
                if inference.prevention_focus_score == 0.5:
                    inference.prevention_focus_score = 0.7
                else:
                    inference.prevention_focus_score = min(
                        1.0, inference.prevention_focus_score + 0.15
                    )
                knowledge_applied.append("cursor_initiation_deliberative")
            signals_used += 1
        
        # 9. Cognitive Load from keystroke patterns
        # Research: Typing rhythm changes indicate cognitive load
        if "keystroke_cognitive_load" in features:
            keystroke_load = features["keystroke_cognitive_load"]
            # Blend with existing load estimate
            if inference.cognitive_load != 0.5:
                inference.cognitive_load = (
                    inference.cognitive_load * 0.5 + keystroke_load * 0.5
                )
            else:
                inference.cognitive_load = keystroke_load
            signals_used += 1
            knowledge_applied.append("keystroke_cognitive_load")
        
        # 10. Emotional Arousal from keystroke patterns
        # Research: Typing speed/variance correlates with arousal
        if "keystroke_arousal_indicator" in features:
            keystroke_arousal = features["keystroke_arousal_indicator"]
            # Blend with existing arousal (from touch/accelerometer)
            if inference.emotional_arousal != 0.5:
                inference.emotional_arousal = (
                    inference.emotional_arousal * 0.6 + keystroke_arousal * 0.4
                )
            else:
                inference.emotional_arousal = keystroke_arousal
            signals_used += 1
            knowledge_applied.append("keystroke_arousal")
        
        # 11. Attention/Engagement from hover patterns
        # Research: Hover duration correlates with attention
        if "hover_duration_mean" in features:
            hover_duration = features["hover_duration_mean"]
            # Long hovers (>1s) indicate deep attention/interest
            if hover_duration > 1000:
                # Increase purchase intent when attention is high
                if inference.purchase_intent != 0.5:
                    inference.purchase_intent = min(
                        1.0, inference.purchase_intent + 0.1
                    )
                knowledge_applied.append("hover_attention_positive")
            signals_used += 1
        
        # 12. Processing Mode from cursor/keystroke patterns
        # Combine desktop signals with existing mobile assessment
        if "trajectory_initiation_mean" in features or "keystroke_seq_pause_count" in features:
            initiation = features.get("trajectory_initiation_mean", 500)
            pauses = features.get("keystroke_seq_pause_count", 0)
            
            # Fast initiation + few pauses = System 1
            # Slow initiation + many pauses = System 2
            if initiation < 400 and pauses < 2:
                if inference.processing_mode == "mixed":
                    inference.processing_mode = "system1"
            elif initiation > 800 or pauses > 5:
                if inference.processing_mode == "mixed":
                    inference.processing_mode = "system2"
        
        # 13. Frustration from cursor patterns
        # Erratic movement + x-flips indicate frustration
        if "trajectory_x_flips_mean" in features:
            x_flips = features["trajectory_x_flips_mean"]
            if x_flips > 3:  # High reversal rate
                frustration_indicator = min(1.0, x_flips / 6)
                inference.frustration_level = max(
                    inference.frustration_level, frustration_indicator
                )
                knowledge_applied.append("cursor_frustration")
                signals_used += 1
        
        # =====================================================================
        # CALCULATE OVERALL CONFIDENCE
        # =====================================================================
        
        inference.signals_used = signals_used
        inference.knowledge_applied = knowledge_applied
        
        # Higher confidence when we have more signal sources
        # Max 0.95 with 15+ signals across domains
        inference.inference_confidence = min(0.95, signals_used / 15)
        
        # Boost confidence when we have both mobile and desktop signals
        if session.has_mobile_signals and session.has_desktop_signals:
            inference.inference_confidence = min(
                0.98, inference.inference_confidence + 0.1
            )
        
        return inference
    
    async def infer_mechanism_profile(
        self,
        session: BehavioralSession,
        psychological_inference: Optional[PsychologicalInference] = None,
    ) -> UserMechanismProfile:
        """
        Infer cognitive mechanism states from all behavioral signals.
        
        This is the CORE method that maps mobile, desktop, and media signals
        to ADAM's 9 cognitive mechanisms. The output is used by atoms for
        mechanism selection and message framing.
        
        Research backing:
        - Each mechanism has validated signal mappings with effect sizes
        - Multiple signals are combined using confidence-weighted averaging
        - Both mobile and desktop signals contribute to mechanism inference
        
        Args:
            session: The behavioral session with extracted features
            psychological_inference: Optional pre-computed psychological state
            
        Returns:
            UserMechanismProfile with all 9 mechanisms and evidence
        """
        features = session.features
        
        # Create profile
        profile = UserMechanismProfile(
            session_id=session.session_id,
            user_id=session.user_id,
        )
        
        # Track domains
        if session.has_mobile_signals:
            profile.signal_domains.append("mobile")
        if session.has_desktop_signals:
            profile.signal_domains.append("desktop")
        
        # Initialize evidence tracking
        evidence_by_mechanism: Dict[str, List[MechanismEvidence]] = {
            m.value: [] for m in CognitiveMechanism
        }
        
        # =====================================================================
        # PROCESS EACH MECHANISM
        # =====================================================================
        
        for mechanism, signal_mappings in MECHANISM_SIGNAL_MAP.items():
            mechanism_evidence = []
            
            for mapping in signal_mappings:
                feature_name = mapping["feature"]
                
                # Check if we have this feature
                if feature_name not in features:
                    continue
                
                feature_value = features[feature_name]
                direction = mapping["direction"]
                effect_size = mapping["effect_size"]
                
                # Apply thresholds if defined
                threshold_high = mapping.get("threshold_high")
                threshold_low = mapping.get("threshold_low")
                
                # Calculate normalized value (0-1)
                if threshold_high and threshold_low:
                    normalized = (feature_value - threshold_low) / (threshold_high - threshold_low)
                    normalized = max(0.0, min(1.0, normalized))
                elif threshold_high:
                    normalized = min(1.0, feature_value / threshold_high)
                elif threshold_low:
                    normalized = min(1.0, threshold_low / feature_value) if feature_value > 0 else 0
                else:
                    # Assume feature is already 0-1 or use reasonable defaults
                    normalized = max(0.0, min(1.0, feature_value))
                
                # Apply inversion if specified
                if mapping.get("invert"):
                    normalized = 1 - normalized
                
                # Calculate evidence strength
                evidence_strength = normalized * effect_size
                evidence_direction = direction * normalized
                
                # Create evidence record
                evidence = MechanismEvidence(
                    mechanism=mechanism,
                    signal_source=mapping["signal"],
                    feature_name=feature_name,
                    feature_value=feature_value,
                    evidence_strength=min(1.0, evidence_strength),
                    evidence_direction=max(-1.0, min(1.0, evidence_direction)),
                    effect_size=effect_size,
                    confidence=min(0.9, effect_size + 0.3),
                )
                
                mechanism_evidence.append(evidence)
                evidence_by_mechanism[mechanism.value].append(evidence)
                
                # Track signal sources
                if mapping["signal"] not in profile.signal_sources_used:
                    profile.signal_sources_used.append(mapping["signal"])
            
            # Combine evidence for this mechanism
            if mechanism_evidence:
                combined_value, combined_confidence = self._combine_mechanism_evidence(
                    mechanism_evidence,
                    MECHANISM_POLARITY[mechanism],
                )
                
                # Set mechanism value
                self._set_mechanism_value(profile, mechanism, combined_value, combined_confidence)
        
        # =====================================================================
        # INCORPORATE PSYCHOLOGICAL INFERENCE (if provided)
        # =====================================================================
        
        if psychological_inference:
            # Use existing inferences to boost mechanism confidence
            
            # Decision confidence → Automatic Evaluation
            if psychological_inference.decision_confidence != 0.5:
                boost = (psychological_inference.decision_confidence - 0.5) * 0.4
                profile.automatic_evaluation = max(-1, min(1, profile.automatic_evaluation + boost))
            
            # Processing mode → Construal Level
            if psychological_inference.processing_mode == "system1":
                profile.construal_level = min(1, profile.construal_level - 0.1)  # More concrete
            elif psychological_inference.processing_mode == "system2":
                profile.construal_level = max(-1, profile.construal_level + 0.1)  # More abstract
            
            # Regulatory focus from inference
            if psychological_inference.promotion_focus_score != 0.5:
                focus_diff = psychological_inference.promotion_focus_score - psychological_inference.prevention_focus_score
                profile.regulatory_focus = max(-1, min(1, profile.regulatory_focus + focus_diff * 0.3))
            
            # Attention from cognitive load (inverse relationship)
            if psychological_inference.cognitive_load != 0.5:
                profile.attention_engagement = 1 - psychological_inference.cognitive_load
        
        # =====================================================================
        # FINALIZE PROFILE
        # =====================================================================
        
        profile.evidence_by_mechanism = evidence_by_mechanism
        profile.total_evidence_count = sum(len(e) for e in evidence_by_mechanism.values())
        
        # Calculate overall confidence
        confidences = [
            profile.construal_level_confidence,
            profile.regulatory_focus_confidence,
            profile.automatic_evaluation_confidence,
            profile.wanting_liking_confidence,
            profile.mimetic_susceptibility_confidence,
            profile.attention_engagement_confidence,
            profile.temporal_orientation_confidence,
            profile.identity_activation_confidence,
            profile.evolutionary_sensitivity_confidence,
        ]
        profile.overall_confidence = sum(confidences) / len(confidences)
        
        # Boost confidence for multi-domain sessions
        if len(profile.signal_domains) > 1:
            profile.overall_confidence = min(0.98, profile.overall_confidence + 0.1)
        
        logger.info(
            f"Inferred mechanism profile for session {session.session_id}: "
            f"{profile.total_evidence_count} evidence items, "
            f"confidence={profile.overall_confidence:.2f}"
        )
        
        return profile
    
    def _combine_mechanism_evidence(
        self,
        evidence_list: List[MechanismEvidence],
        polarity: MechanismPolarity,
    ) -> Tuple[float, float]:
        """
        Combine multiple evidence items into a single mechanism value.
        
        Uses confidence-weighted averaging.
        """
        if not evidence_list:
            return 0.0, 0.5
        
        # Weighted average by effect size
        total_weight = sum(e.effect_size for e in evidence_list)
        
        if total_weight == 0:
            return 0.0, 0.5
        
        if polarity == MechanismPolarity.BIPOLAR:
            # Use evidence direction for bipolar mechanisms
            weighted_sum = sum(e.evidence_direction * e.effect_size for e in evidence_list)
            combined_value = weighted_sum / total_weight
            combined_value = max(-1.0, min(1.0, combined_value))
        else:
            # Use evidence strength for unipolar mechanisms
            weighted_sum = sum(e.evidence_strength * e.effect_size for e in evidence_list)
            combined_value = weighted_sum / total_weight
            combined_value = max(0.0, min(1.0, combined_value))
        
        # Confidence increases with more evidence
        confidence = min(0.9, 0.3 + len(evidence_list) * 0.1 + total_weight * 0.3)
        
        return combined_value, confidence
    
    def _set_mechanism_value(
        self,
        profile: UserMechanismProfile,
        mechanism: CognitiveMechanism,
        value: float,
        confidence: float,
    ) -> None:
        """Set the value and confidence for a mechanism in the profile."""
        if mechanism == CognitiveMechanism.CONSTRUAL_LEVEL:
            profile.construal_level = value
            profile.construal_level_confidence = confidence
        elif mechanism == CognitiveMechanism.REGULATORY_FOCUS:
            profile.regulatory_focus = value
            profile.regulatory_focus_confidence = confidence
        elif mechanism == CognitiveMechanism.AUTOMATIC_EVALUATION:
            profile.automatic_evaluation = value
            profile.automatic_evaluation_confidence = confidence
        elif mechanism == CognitiveMechanism.WANTING_LIKING:
            profile.wanting_liking_gap = value
            profile.wanting_liking_confidence = confidence
        elif mechanism == CognitiveMechanism.MIMETIC_DESIRE:
            profile.mimetic_susceptibility = value
            profile.mimetic_susceptibility_confidence = confidence
        elif mechanism == CognitiveMechanism.ATTENTION_DYNAMICS:
            profile.attention_engagement = value
            profile.attention_engagement_confidence = confidence
        elif mechanism == CognitiveMechanism.TEMPORAL_CONSTRUAL:
            profile.temporal_orientation = value
            profile.temporal_orientation_confidence = confidence
        elif mechanism == CognitiveMechanism.IDENTITY_CONSTRUCTION:
            profile.identity_activation = value
            profile.identity_activation_confidence = confidence
        elif mechanism == CognitiveMechanism.EVOLUTIONARY_ADAPTATIONS:
            profile.evolutionary_sensitivity = value
            profile.evolutionary_sensitivity_confidence = confidence

    async def record_outcome(
        self,
        outcome: BehavioralOutcome,
    ) -> Dict[str, Any]:
        """
        Record an outcome for learning.
        
        Updates hypotheses and validates knowledge.
        """
        result = {
            "outcome_id": outcome.outcome_id,
            "session_id": outcome.session_id,
            "outcome_type": outcome.outcome_type.value,
            "processed": True,
        }
        
        # 1. Update active hypotheses
        active_hypotheses = self._hypothesis_engine.get_hypotheses_by_status(
            "testing"
        )
        
        updated_hypotheses = []
        for hypothesis in active_hypotheses:
            if hypothesis.predicted_outcome == outcome.outcome_type.value:
                # Record observation
                await self._hypothesis_engine.record_observation(
                    hypothesis.hypothesis_id,
                    outcome.context.get("signal_values", {}),
                    outcome.outcome_value,
                    outcome.outcome_value > 0.5  # Positive outcome
                )
                updated_hypotheses.append(hypothesis.hypothesis_id)
        
        result["hypotheses_updated"] = updated_hypotheses
        
        # 2. Check for promotable hypotheses
        promotable = self._hypothesis_engine.get_promotable_hypotheses()
        promoted = []
        for hypothesis in promotable:
            knowledge = await self._hypothesis_engine.promote_hypothesis(
                hypothesis.hypothesis_id
            )
            if knowledge:
                promoted.append(knowledge.knowledge_id)
                logger.info(
                    f"Promoted hypothesis to knowledge: {knowledge.knowledge_id}"
                )
        
        result["hypotheses_promoted"] = promoted
        
        # 3. Record for prediction drift
        if "prediction" in outcome.context:
            self._drift_detector.record_prediction_outcome(
                outcome.outcome_type.value,
                outcome.context["prediction"],
                outcome.outcome_value
            )
        
        # 4. Forward to Gradient Bridge (if available)
        if self._gradient_bridge:
            await self._forward_to_gradient_bridge(outcome)
        
        return result
    
    async def get_knowledge_for_atom(
        self,
        construct: str,
        tier: Optional[KnowledgeTier] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get behavioral knowledge for an atom.
        
        Returns knowledge relevant to the requested construct,
        formatted for atom consumption.
        
        Args:
            construct: Psychological construct (e.g., "decision_confidence")
            tier: Optional tier filter
            
        Returns:
            List of knowledge dicts with signal, effect, and thresholds
        """
        # Check cache
        cache_key = f"{construct}:{tier}"
        if cache_key in self._knowledge_cache:
            return [k.__dict__ for k in self._knowledge_cache[cache_key]]
        
        # Get from seeder (in-memory) or graph
        knowledge_list = self._knowledge_seeder.get_knowledge_for_construct(construct)
        
        if tier:
            knowledge_list = [k for k in knowledge_list if k.tier == tier]
        
        # Cache
        self._knowledge_cache[cache_key] = knowledge_list
        
        return [
            {
                "knowledge_id": k.knowledge_id,
                "signal_name": k.signal_name,
                "feature_name": k.feature_name,
                "effect_size": k.effect_size,
                "effect_type": k.effect_type.value,
                "mapping_direction": k.mapping_direction,
                "threshold_high": k.signal_threshold_high,
                "threshold_low": k.signal_threshold_low,
                "requires_baseline": k.requires_baseline,
                "min_observations": k.min_observations,
                "implementation_notes": k.implementation_notes,
            }
            for k in knowledge_list
        ]
    
    def _extract_all_features(
        self,
        session: BehavioralSession,
    ) -> Dict[str, float]:
        """
        Extract all features from a session across all signal domains.
        
        This is the UNIFIED feature extraction pipeline that processes:
        - Mobile signals (touch, swipe, scroll, sensors)
        - Desktop signals (cursor, keystroke, desktop scroll)
        - Explicit signals (clicks, page views)
        
        All features feed into the same psychological inference system.
        """
        features = {}
        
        # =====================================================================
        # MOBILE SIGNAL FEATURES
        # =====================================================================
        
        # Touch features
        if session.touches:
            mobile_touch = self._extract_touch_features(session.touches)
            features.update(mobile_touch)
            session.mobile_features.update(mobile_touch)
        
        # Swipe features
        if session.swipes:
            mobile_swipe = self._extract_swipe_features(session.swipes)
            features.update(mobile_swipe)
            session.mobile_features.update(mobile_swipe)
        
        # Mobile scroll features
        if session.scrolls:
            mobile_scroll = self._extract_scroll_features(session.scrolls)
            features.update(mobile_scroll)
            session.mobile_features.update(mobile_scroll)
        
        # Sensor features (accelerometer, gyroscope)
        if session.sensor_samples:
            mobile_sensor = self._extract_sensor_features(session.sensor_samples)
            features.update(mobile_sensor)
            session.mobile_features.update(mobile_sensor)
        
        # =====================================================================
        # DESKTOP SIGNAL FEATURES
        # =====================================================================
        
        # Cursor trajectory features (decisional conflict)
        if session.cursor_trajectories:
            desktop_trajectory = self._extract_cursor_trajectory_features(
                session.cursor_trajectories
            )
            features.update(desktop_trajectory)
            session.desktop_features.update(desktop_trajectory)
        
        # Cursor movement features (attention, exploration)
        if session.cursor_moves:
            desktop_cursor = self._extract_cursor_move_features(session.cursor_moves)
            features.update(desktop_cursor)
            session.desktop_features.update(desktop_cursor)
        
        # Cursor hover features (interest, attention)
        if session.cursor_hovers:
            desktop_hover = self._extract_cursor_hover_features(session.cursor_hovers)
            features.update(desktop_hover)
            session.desktop_features.update(desktop_hover)
        
        # Keystroke features (cognitive load, arousal, authentication)
        if session.keystroke_sequences:
            desktop_keystroke = self._extract_keystroke_sequence_features(
                session.keystroke_sequences
            )
            features.update(desktop_keystroke)
            session.desktop_features.update(desktop_keystroke)
        elif session.keystrokes:
            desktop_keystroke = self._extract_keystroke_features(session.keystrokes)
            features.update(desktop_keystroke)
            session.desktop_features.update(desktop_keystroke)
        
        # Desktop scroll features
        if session.desktop_scrolls:
            desktop_scroll = self._extract_desktop_scroll_features(
                session.desktop_scrolls
            )
            features.update(desktop_scroll)
            session.desktop_features.update(desktop_scroll)
        
        # =====================================================================
        # CROSS-DOMAIN FEATURES
        # =====================================================================
        
        # Temporal features (applies to both mobile and desktop)
        features.update(self._extract_temporal_features(session))
        
        # Attention features (hesitations, rage clicks - both domains)
        if session.hesitations or session.rage_clicks:
            features.update(self._extract_attention_features(session))
        
        # Add domain indicator
        features["has_mobile_signals"] = 1.0 if session.has_mobile_signals else 0.0
        features["has_desktop_signals"] = 1.0 if session.has_desktop_signals else 0.0
        features["primary_domain"] = {
            SignalDomain.MOBILE: 1.0,
            SignalDomain.DESKTOP: 2.0,
            SignalDomain.EXPLICIT: 0.0,
            SignalDomain.MEDIA: 3.0,
        }.get(session.primary_signal_domain, 0.0)
        
        return features
    
    def _extract_touch_features(self, touches: List) -> Dict[str, float]:
        """Extract touch dynamics features."""
        pressures = [t.pressure for t in touches]
        durations = [t.duration_ms for t in touches]
        
        return {
            "pressure_mean": sum(pressures) / len(pressures),
            "pressure_std": self._std(pressures),
            "pressure_max": max(pressures),
            "duration_mean": sum(durations) / len(durations) if durations else 0,
            "touch_count": float(len(touches)),
        }
    
    def _extract_swipe_features(self, swipes: List) -> Dict[str, float]:
        """Extract swipe pattern features."""
        velocities = [s.velocity for s in swipes]
        directnesses = [s.directness for s in swipes]
        
        from adam.behavioral_analytics.models.events import SwipeDirection
        right_count = sum(1 for s in swipes if s.direction == SwipeDirection.RIGHT)
        
        return {
            "velocity_mean": sum(velocities) / len(velocities),
            "velocity_std": self._std(velocities),
            "directness_mean": sum(directnesses) / len(directnesses),
            "right_swipe_ratio": right_count / len(swipes),
            "swipe_count": float(len(swipes)),
        }
    
    def _extract_scroll_features(self, scrolls: List) -> Dict[str, float]:
        """Extract scroll behavior features."""
        velocities = [s.velocity for s in scrolls]
        depths = [s.scroll_depth_percent for s in scrolls]
        reversal_count = sum(1 for s in scrolls if s.is_reversal)
        
        return {
            "scroll_velocity_mean": sum(velocities) / len(velocities),
            "max_depth": max(depths),
            "reversal_ratio": reversal_count / len(scrolls),
        }
    
    def _extract_temporal_features(self, session: BehavioralSession) -> Dict[str, float]:
        """Extract temporal pattern features."""
        features = {}
        
        if session.page_views:
            dwell_times = [pv.dwell_time_ms for pv in session.page_views]
            features["dwell_time_mean"] = sum(dwell_times) / len(dwell_times)
        
        if len(session.clicks) >= 2:
            latencies = []
            sorted_clicks = sorted(session.clicks, key=lambda c: c.timestamp)
            for i in range(1, len(sorted_clicks)):
                latency = (sorted_clicks[i].timestamp - sorted_clicks[i-1].timestamp).total_seconds() * 1000
                latencies.append(latency)
            
            if latencies:
                features["response_latency_mean"] = sum(latencies) / len(latencies)
                features["response_latency_std"] = self._std(latencies)
        
        features["session_duration_ms"] = float(session.duration_ms)
        
        return features
    
    def _extract_attention_features(self, session: BehavioralSession) -> Dict[str, float]:
        """Extract attention/frustration features."""
        features = {}
        
        if session.hesitations:
            features["hesitation_count"] = float(len(session.hesitations))
            cta_hesitations = [h for h in session.hesitations if h.element_type == "cta"]
            if cta_hesitations:
                features["pre_cta_hesitation_ratio"] = len(cta_hesitations) / len(session.hesitations)
        
        if session.rage_clicks:
            features["rage_click_count"] = float(len(session.rage_clicks))
        
        return features
    
    def _extract_sensor_features(self, samples: List) -> Dict[str, float]:
        """Extract sensor features."""
        magnitudes = [s.magnitude for s in samples]
        
        return {
            "magnitude_mean": sum(magnitudes) / len(magnitudes),
            "magnitude_std": self._std(magnitudes),
        }
    
    # =========================================================================
    # DESKTOP FEATURE EXTRACTION METHODS
    # =========================================================================
    
    def _extract_cursor_trajectory_features(
        self,
        trajectories: List[CursorTrajectoryEvent],
    ) -> Dict[str, float]:
        """
        Extract cursor trajectory features.
        
        Research:
        - Area Under Curve (AUC) correlates with decisional conflict (d=0.4-1.6)
        - Maximum Absolute Deviation (MAD) indicates attraction to non-chosen option
        - x-flips reveal conflict during decision process
        - Initiation time indicates automatic vs deliberative processing
        
        These are Tier 1 signals with highest predictive value for desktop.
        """
        if not trajectories:
            return {}
        
        aucs = [t.area_under_curve for t in trajectories]
        mads = [t.maximum_absolute_deviation for t in trajectories]
        x_flips = [t.x_flips for t in trajectories]
        initiation_times = [t.initiation_time_ms for t in trajectories]
        movement_times = [t.movement_time_ms for t in trajectories]
        conflict_scores = [t.conflict_score for t in trajectories]
        
        # Count conflicted trajectories (d > 0.4 threshold)
        conflicted_count = sum(1 for t in trajectories if t.is_conflicted)
        
        return {
            # Core trajectory metrics
            "trajectory_auc_mean": sum(aucs) / len(aucs),
            "trajectory_auc_max": max(aucs),
            "trajectory_auc_std": self._std(aucs),
            "trajectory_mad_mean": sum(mads) / len(mads),
            "trajectory_mad_max": max(mads),
            # Direction change metrics
            "trajectory_x_flips_mean": sum(x_flips) / len(x_flips),
            "trajectory_x_flips_max": max(x_flips),
            "trajectory_x_flips_total": sum(x_flips),
            # Timing metrics
            "trajectory_initiation_mean": sum(initiation_times) / len(initiation_times),
            "trajectory_initiation_std": self._std(initiation_times),
            "trajectory_movement_mean": sum(movement_times) / len(movement_times),
            # Conflict metrics (composite)
            "trajectory_conflict_mean": sum(conflict_scores) / len(conflict_scores),
            "trajectory_conflict_max": max(conflict_scores),
            "trajectory_conflicted_ratio": conflicted_count / len(trajectories),
            # Count
            "trajectory_count": float(len(trajectories)),
        }
    
    def _extract_cursor_move_features(
        self,
        moves: List[CursorMoveEvent],
    ) -> Dict[str, float]:
        """
        Extract cursor movement features.
        
        Research:
        - Cursor position correlates with gaze (r=0.84)
        - Movement velocity indicates engagement level
        - Acceleration patterns reveal hesitation/confidence
        """
        if not moves:
            return {}
        
        velocities = [m.velocity for m in moves if m.velocity > 0]
        accelerations = [m.acceleration for m in moves if m.acceleration != 0]
        
        # Calculate path directness from moves
        if len(moves) >= 2:
            # Direct distance from first to last
            direct_dist = (
                (moves[-1].x - moves[0].x) ** 2 +
                (moves[-1].y - moves[0].y) ** 2
            ) ** 0.5
            
            # Actual path distance
            path_dist = 0.0
            for i in range(1, len(moves)):
                path_dist += (
                    (moves[i].x - moves[i-1].x) ** 2 +
                    (moves[i].y - moves[i-1].y) ** 2
                ) ** 0.5
            
            directness = direct_dist / path_dist if path_dist > 0 else 1.0
        else:
            directness = 1.0
        
        features = {
            "cursor_move_count": float(len(moves)),
            "cursor_directness": min(1.0, directness),
        }
        
        if velocities:
            features.update({
                "cursor_velocity_mean": sum(velocities) / len(velocities),
                "cursor_velocity_max": max(velocities),
                "cursor_velocity_std": self._std(velocities),
            })
        
        if accelerations:
            features.update({
                "cursor_acceleration_mean": sum(accelerations) / len(accelerations),
                "cursor_acceleration_std": self._std(accelerations),
            })
        
        return features
    
    def _extract_cursor_hover_features(
        self,
        hovers: List[CursorHoverEvent],
    ) -> Dict[str, float]:
        """
        Extract cursor hover/dwell features.
        
        Research:
        - Hover duration correlates with attention and interest
        - Hover patterns reveal information-seeking behavior
        """
        if not hovers:
            return {}
        
        durations = [h.hover_duration_ms for h in hovers]
        micro_movements = [h.micro_movements for h in hovers]
        
        # Group by element type
        element_hovers = {}
        for hover in hovers:
            elem_type = hover.element_type or "unknown"
            if elem_type not in element_hovers:
                element_hovers[elem_type] = []
            element_hovers[elem_type].append(hover.hover_duration_ms)
        
        features = {
            "hover_count": float(len(hovers)),
            "hover_duration_mean": sum(durations) / len(durations),
            "hover_duration_max": max(durations),
            "hover_duration_total": sum(durations),
            "hover_duration_std": self._std(durations),
            "hover_micro_movements_mean": sum(micro_movements) / len(micro_movements),
        }
        
        # Add element-specific hover durations
        for elem_type, elem_durations in element_hovers.items():
            features[f"hover_{elem_type}_mean"] = sum(elem_durations) / len(elem_durations)
        
        return features
    
    def _extract_keystroke_features(
        self,
        keystrokes: List[KeystrokeEvent],
    ) -> Dict[str, float]:
        """
        Extract keystroke dynamics features from individual keystrokes.
        
        Research:
        - Hold time patterns reveal typing rhythm
        - Flight time reveals fluency
        - Combined patterns enable user authentication (EER < 1%)
        """
        if not keystrokes:
            return {}
        
        hold_times = [k.hold_time_ms for k in keystrokes]
        flight_times = [k.flight_time_ms for k in keystrokes if k.flight_time_ms is not None]
        error_count = sum(1 for k in keystrokes if k.is_error_correction)
        
        features = {
            "keystroke_count": float(len(keystrokes)),
            "keystroke_hold_mean": sum(hold_times) / len(hold_times),
            "keystroke_hold_std": self._std(hold_times),
            "keystroke_error_rate": error_count / len(keystrokes),
        }
        
        if flight_times:
            features.update({
                "keystroke_flight_mean": sum(flight_times) / len(flight_times),
                "keystroke_flight_std": self._std(flight_times),
            })
        
        return features
    
    def _extract_keystroke_sequence_features(
        self,
        sequences: List[KeystrokeSequence],
    ) -> Dict[str, float]:
        """
        Extract keystroke sequence features.
        
        Research:
        - Typing speed changes correlate with emotional arousal
        - Pause patterns indicate cognitive load
        - Rhythm regularity is stable within individuals
        """
        if not sequences:
            return {}
        
        hold_means = [s.hold_time_mean_ms for s in sequences]
        flight_means = [s.flight_time_mean_ms for s in sequences]
        speeds = [s.typing_speed_cpm for s in sequences]
        pauses = [s.pause_count for s in sequences]
        errors = [s.error_rate for s in sequences]
        regularities = [s.rhythm_regularity for s in sequences]
        
        # Compute derived indicators
        cognitive_loads = [s.cognitive_load_indicator for s in sequences]
        arousal_indicators = [s.emotional_arousal_indicator for s in sequences]
        
        return {
            # Core timing
            "keystroke_seq_hold_mean": sum(hold_means) / len(hold_means),
            "keystroke_seq_flight_mean": sum(flight_means) / len(flight_means),
            "keystroke_seq_speed_mean": sum(speeds) / len(speeds),
            "keystroke_seq_speed_std": self._std(speeds),
            # Patterns
            "keystroke_seq_pause_count": sum(pauses),
            "keystroke_seq_error_rate": sum(errors) / len(errors),
            "keystroke_seq_rhythm_regularity": sum(regularities) / len(regularities),
            # Derived psychological indicators
            "keystroke_cognitive_load": sum(cognitive_loads) / len(cognitive_loads),
            "keystroke_arousal_indicator": sum(arousal_indicators) / len(arousal_indicators),
            # Count
            "keystroke_sequence_count": float(len(sequences)),
        }
    
    def _extract_desktop_scroll_features(
        self,
        scrolls: List[DesktopScrollEvent],
    ) -> Dict[str, float]:
        """
        Extract desktop scroll features.
        
        Desktop scrolling differs from mobile due to precision control.
        """
        if not scrolls:
            return {}
        
        velocities = [s.velocity for s in scrolls]
        depths = [s.scroll_depth_percent for s in scrolls]
        reversal_count = sum(1 for s in scrolls if s.is_reversal)
        smooth_count = sum(1 for s in scrolls if s.is_smooth)
        
        # Calculate pause metrics
        pauses = [s for s in scrolls if s.is_pause]
        total_pause_ms = sum(s.pause_duration_ms for s in pauses)
        
        return {
            "desktop_scroll_velocity_mean": sum(velocities) / len(velocities),
            "desktop_scroll_velocity_std": self._std(velocities),
            "desktop_scroll_max_depth": max(depths),
            "desktop_scroll_reversal_ratio": reversal_count / len(scrolls),
            "desktop_scroll_smooth_ratio": smooth_count / len(scrolls),
            "desktop_scroll_pause_count": len(pauses),
            "desktop_scroll_pause_total_ms": float(total_pause_ms),
            "desktop_scroll_count": float(len(scrolls)),
        }
    
    def _std(self, values: List[float]) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    async def _store_session_to_graph(
        self,
        session: BehavioralSession,
        inference: PsychologicalInference,
        mechanism_profile: Optional[UserMechanismProfile] = None,
    ) -> None:
        """Store session, inference, and mechanism profile to Neo4j."""
        # This would use the graph integration
        # Implementation depends on specific graph schema
        # TODO: Store mechanism profile for learning and hypothesis testing
        pass
    
    async def _forward_to_gradient_bridge(
        self,
        outcome: BehavioralOutcome,
    ) -> None:
        """Forward outcome to Gradient Bridge for learning."""
        # This would integrate with existing Gradient Bridge
        # Implementation depends on GradientBridge interface
        pass
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health status."""
        return {
            "status": "healthy",
            "research_knowledge_count": len(self._research_knowledge),
            "drift_health": self._drift_detector.get_behavioral_health(),
            "hypothesis_count": len(self._hypothesis_engine._hypotheses),
        }
    
    # =========================================================================
    # LEARNING CAPABLE COMPONENT INTERFACE
    # =========================================================================
    
    @property
    def component_name(self) -> str:
        """Component name for learning signal routing."""
        return "behavioral_analytics"
    
    @property
    def component_version(self) -> str:
        """Component version."""
        return "1.0"
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[Any]:
        """
        Process an outcome and generate learning signals.
        
        For BehavioralAnalytics, this records observations for hypothesis testing
        and validates signal-outcome relationships.
        """
        signals = []
        
        # Record observation for hypothesis testing
        session_id = context.get("session_id")
        user_id = context.get("user_id")
        
        if session_id and self._hypothesis_engine:
            # Get features that were observed for this session
            features = context.get("features", {})
            
            # Record observations for all active hypotheses
            for hypothesis in self._hypothesis_engine.get_active_hypotheses():
                if hypothesis.signal_name in features:
                    self._hypothesis_engine.record_observation(
                        hypothesis.hypothesis_id,
                        outcome_value,
                        signal_value=features.get(hypothesis.signal_name, 0.0),
                    )
        
        # Emit signal about behavioral outcome
        try:
            from adam.core.learning.universal_learning_interface import (
                LearningSignal,
                LearningSignalType,
            )
            signal = LearningSignal(
                signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                source_component=self.component_name,
                source_version=self.component_version,
                decision_id=decision_id,
                user_id=user_id,
                payload={
                    "session_id": session_id,
                    "outcome_type": outcome_type,
                    "outcome_value": outcome_value,
                },
                confidence=outcome_value,
            )
            signals.append(signal)
        except ImportError:
            pass
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: Any,
    ) -> Optional[List[Any]]:
        """Process incoming learning signals."""
        # BehavioralAnalytics can respond to signals about:
        # - New hypothesis promotions
        # - Drift detections
        # - Knowledge updates
        try:
            from adam.core.learning.universal_learning_interface import (
                LearningSignal,
                LearningSignalType,
            )
            if isinstance(signal, LearningSignal):
                if signal.signal_type == LearningSignalType.NOVEL_CONSTRUCT_DISCOVERED:
                    # A new psychological construct was discovered
                    # Could trigger new hypothesis generation
                    pass
        except ImportError:
            pass
        return None
    
    def get_consumed_signal_types(self) -> set:
        """Return signal types this component consumes."""
        try:
            from adam.core.learning.universal_learning_interface import LearningSignalType
            return {
                LearningSignalType.NOVEL_CONSTRUCT_DISCOVERED,
                LearningSignalType.DRIFT_DETECTED,
            }
        except ImportError:
            return set()
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[Any]:
        """Get this component's contribution to a decision."""
        # BehavioralAnalytics contributes psychological state inference
        # Would need to track contributions per decision
        return None
    
    async def get_learning_quality_metrics(self) -> Any:
        """Get metrics about learning quality."""
        try:
            from adam.core.learning.universal_learning_interface import LearningQualityMetrics
            
            # Get hypothesis validation stats
            active_hypotheses = len(self._hypothesis_engine._hypotheses) if self._hypothesis_engine else 0
            validated_count = sum(
                1 for h in (self._hypothesis_engine._hypotheses.values() if self._hypothesis_engine else [])
                if h.validation_status == "validated"
            ) if self._hypothesis_engine else 0
            
            return LearningQualityMetrics(
                component_name=self.component_name,
                measurement_period_hours=24,
                signals_emitted=active_hypotheses,
                signals_consumed=0,
                outcomes_processed=sum(
                    h.observation_count for h in (self._hypothesis_engine._hypotheses.values() if self._hypothesis_engine else [])
                ) if self._hypothesis_engine else 0,
                prediction_accuracy=validated_count / max(1, active_hypotheses),
                prediction_accuracy_trend="stable",
                attribution_coverage=0.8 if self._hypothesis_engine else 0.0,
            )
        except ImportError:
            return None
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any],
    ) -> None:
        """Inject priors before processing."""
        # Could use priors to initialize mechanism profile
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        # Check research knowledge
        if not self._research_knowledge:
            issues.append("No research knowledge loaded")
        
        # Check hypothesis engine
        if not self._hypothesis_engine:
            issues.append("Hypothesis engine not initialized")
        
        # Check drift detector
        drift_health = self._drift_detector.get_behavioral_health()
        if drift_health.get("status") != "healthy":
            issues.append(f"Drift detector unhealthy: {drift_health}")
        
        return len(issues) == 0, issues
    
    async def get_latest_psychological_state(
        self,
        user_id: str,
    ) -> Optional[Any]:
        """
        Get the latest psychological state inference for a user.
        
        Called by atoms to get nonconscious signal evidence.
        """
        # Would query cache or graph for latest inference
        # For now, return None - would need session cache
        return None
    
    async def match_responder_to_review_profile(
        self,
        inference: PsychologicalInference,
        customer_intelligence: Any,  # CustomerIntelligenceProfile
    ) -> Dict[str, Any]:
        """
        Match a behavioral responder to review-derived customer profiles.
        
        This is a key integration: when we observe a user's behavioral signals,
        we can match them to the psychological profiles of actual customers
        who left reviews, enabling more accurate mechanism selection.
        
        Args:
            inference: Psychological inference from behavioral signals
            customer_intelligence: CustomerIntelligenceProfile from reviews
            
        Returns:
            Match result with archetype, confidence, and mechanism recommendations
        """
        if not customer_intelligence:
            return {"matched": False, "reason": "No customer intelligence provided"}
        
        # Get reviewer archetypes from customer intelligence
        buyer_archetypes = getattr(customer_intelligence, 'buyer_archetypes', {}) or {}
        if not buyer_archetypes:
            return {"matched": False, "reason": "No buyer archetypes in customer intelligence"}
        
        # Build responder profile from inference
        responder_profile = {
            "promotion_focus": inference.promotion_focus_score,
            "prevention_focus": inference.prevention_focus_score,
            "emotional_arousal": inference.emotional_arousal,
            "decision_confidence": inference.decision_confidence,
            "cognitive_load": inference.cognitive_load,
            "processing_mode": inference.processing_mode,
        }
        
        # Match against each archetype
        archetype_matches = {}
        for archetype_name, archetype_prob in buyer_archetypes.items():
            # Get archetype personality traits from customer intelligence
            avg_openness = getattr(customer_intelligence, 'avg_openness', 0.5)
            avg_conscientiousness = getattr(customer_intelligence, 'avg_conscientiousness', 0.5)
            avg_extraversion = getattr(customer_intelligence, 'avg_extraversion', 0.5)
            avg_agreeableness = getattr(customer_intelligence, 'avg_agreeableness', 0.5)
            avg_neuroticism = getattr(customer_intelligence, 'avg_neuroticism', 0.5)
            
            # Calculate match based on behavioral signals
            # Regulatory focus is a strong indicator
            reg_focus = getattr(customer_intelligence, 'regulatory_focus', {})
            review_promotion = reg_focus.get('promotion', 0.5)
            review_prevention = reg_focus.get('prevention', 0.5)
            
            focus_alignment = 1.0 - abs(
                responder_profile["promotion_focus"] - review_promotion
            )
            
            # Processing mode indicates construal level
            # System 1 = concrete, System 2 = abstract
            if responder_profile["processing_mode"] == "system1":
                construal_match = 0.7 if review_promotion > review_prevention else 0.5
            elif responder_profile["processing_mode"] == "system2":
                construal_match = 0.7 if review_prevention > review_promotion else 0.5
            else:
                construal_match = 0.5
            
            # Combine match factors
            match_score = (
                focus_alignment * 0.4 +
                construal_match * 0.3 +
                archetype_prob * 0.3  # Weight by how common this archetype is
            )
            
            archetype_matches[archetype_name] = match_score
        
        # Find best match
        if not archetype_matches:
            return {"matched": False, "reason": "No archetype matches computed"}
        
        best_archetype = max(archetype_matches.keys(), key=lambda a: archetype_matches[a])
        best_score = archetype_matches[best_archetype]
        
        # Get mechanism predictions for this archetype
        mechanism_predictions = getattr(customer_intelligence, 'mechanism_predictions', {}) or {}
        
        # Sort mechanisms by predicted effectiveness
        recommended_mechanisms = sorted(
            mechanism_predictions.keys(),
            key=lambda m: mechanism_predictions.get(m, 0),
            reverse=True,
        )[:3]
        
        return {
            "matched": True,
            "best_archetype": best_archetype,
            "match_score": best_score,
            "all_archetype_matches": archetype_matches,
            "recommended_mechanisms": recommended_mechanisms,
            "mechanism_predictions": mechanism_predictions,
            "responder_profile": responder_profile,
            "inference_confidence": inference.inference_confidence,
        }


# Singleton
_engine: Optional[BehavioralAnalyticsEngine] = None


def get_behavioral_analytics_engine(
    neo4j_driver=None,
    gradient_bridge=None,
) -> BehavioralAnalyticsEngine:
    """Get singleton behavioral analytics engine."""
    global _engine
    if _engine is None:
        _engine = BehavioralAnalyticsEngine(neo4j_driver, gradient_bridge)
    return _engine
