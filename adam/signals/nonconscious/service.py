# =============================================================================
# ADAM Nonconscious Analytics - Service Layer
# =============================================================================

"""
NONCONSCIOUS ANALYTICS SERVICE

Central service for capturing, analyzing, and applying nonconscious signals
to personalization and persuasion decisions.

Integration Points:
- Signal Aggregation: Feeds into UserSignalProfile
- Atom of Thought: Provides implicit context for inference
- Blackboard: Writes to Zone 1 (RequestContext) and Zone 2 (AtomReasoningSpace)
- Gradient Bridge: Emits learning signals for mechanism effectiveness
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from prometheus_client import Counter, Histogram, Gauge

from adam.signals.nonconscious.models import (
    NonconsciousSignal,
    NonconsciousProfile,
    ImplicitPreference,
    AutomaticEvaluation,
    ProcessingDepth,
)
from adam.signals.nonconscious.capture import (
    NonconsciousSignalCapture,
    SignalCaptureConfig,
)
from adam.signals.nonconscious.analysis import NonconsciousAnalyzer

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

SIGNALS_CAPTURED = Counter(
    "adam_nonconscious_signals_captured_total",
    "Total nonconscious signals captured",
    ["signal_type"],
)

PROFILES_GENERATED = Counter(
    "adam_nonconscious_profiles_generated_total",
    "Total nonconscious profiles generated",
)

PROFILE_CONFIDENCE = Histogram(
    "adam_nonconscious_profile_confidence",
    "Confidence of generated profiles",
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
)

APPROACH_TENDENCY = Gauge(
    "adam_nonconscious_approach_tendency",
    "Current approach-avoidance tendency",
    ["user_bucket"],
)

COGNITIVE_LOAD = Gauge(
    "adam_nonconscious_cognitive_load",
    "Current cognitive load estimate",
    ["user_bucket"],
)

MECHANISM_RECOMMENDATIONS = Counter(
    "adam_nonconscious_mechanism_recommendations_total",
    "Mechanism recommendations from nonconscious analysis",
    ["mechanism"],
)

ANALYSIS_LATENCY = Histogram(
    "adam_nonconscious_analysis_latency_seconds",
    "Time to analyze nonconscious signals",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
)


# =============================================================================
# NONCONSCIOUS ANALYTICS SERVICE
# =============================================================================

class NonconsciousAnalyticsService:
    """
    Central service for nonconscious analytics.
    
    Responsibilities:
    1. Capture implicit behavioral signals in real-time
    2. Analyze signals to produce psychological profiles
    3. Provide recommendations for persuasion mechanisms
    4. Integrate with ADAM's core processing pipeline
    """
    
    def __init__(
        self,
        capture_config: SignalCaptureConfig = None,
        redis_client = None,
        kafka_producer = None,
    ):
        self.capture = NonconsciousSignalCapture(capture_config)
        self.analyzer = NonconsciousAnalyzer()
        
        self.redis = redis_client
        self.kafka = kafka_producer
        
        # In-memory signal buffer per user
        self._signal_buffers: Dict[str, List[NonconsciousSignal]] = {}
        
        # Profile cache
        self._profile_cache: Dict[str, NonconsciousProfile] = {}
        
        # Implicit preference store
        self._preference_store: Dict[str, Dict[str, ImplicitPreference]] = {}
    
    # =========================================================================
    # SIGNAL CAPTURE
    # =========================================================================
    
    async def process_event(
        self,
        event_type: str,
        raw_data: Dict[str, Any],
    ) -> Optional[NonconsciousSignal]:
        """
        Process a single incoming event.
        
        Called by frontend SDK or signal aggregation service.
        """
        signal = await self.capture.process_event(event_type, raw_data)
        
        if signal:
            user_id = signal.user_id
            
            # Buffer signal
            if user_id not in self._signal_buffers:
                self._signal_buffers[user_id] = []
            self._signal_buffers[user_id].append(signal)
            
            # Limit buffer size
            if len(self._signal_buffers[user_id]) > 1000:
                self._signal_buffers[user_id] = self._signal_buffers[user_id][-500:]
            
            # Metrics
            SIGNALS_CAPTURED.labels(signal_type=type(signal).__name__).inc()
            
            # Persist to Redis if available
            if self.redis:
                await self._persist_signal(signal)
        
        return signal
    
    async def process_batch(
        self,
        events: List[Dict[str, Any]],
    ) -> List[NonconsciousSignal]:
        """
        Process a batch of events.
        """
        signals = []
        
        for event in events:
            signal = await self.process_event(
                event.get("type", ""),
                event.get("data", {}),
            )
            if signal:
                signals.append(signal)
        
        return signals
    
    # =========================================================================
    # PROFILE GENERATION
    # =========================================================================
    
    async def get_profile(
        self,
        user_id: str,
        session_id: str,
        force_refresh: bool = False,
    ) -> Optional[NonconsciousProfile]:
        """
        Get or generate nonconscious profile for user session.
        """
        cache_key = f"{user_id}:{session_id}"
        
        # Check cache
        if not force_refresh and cache_key in self._profile_cache:
            cached = self._profile_cache[cache_key]
            if cached.valid_until and cached.valid_until > datetime.now(timezone.utc):
                return cached
        
        # Generate new profile
        signals = self._signal_buffers.get(user_id, [])
        
        # Filter to session
        session_signals = [s for s in signals if s.session_id == session_id]
        
        if len(session_signals) < 3:
            # Not enough data
            return None
        
        start_time = datetime.now(timezone.utc)
        
        try:
            profile = await self.analyzer.analyze_session(
                session_signals,
                user_id,
                session_id,
            )
            
            # Cache
            self._profile_cache[cache_key] = profile
            
            # Metrics
            PROFILES_GENERATED.inc()
            PROFILE_CONFIDENCE.observe(profile.overall_confidence)
            
            # Track approach tendency for monitoring
            bucket = hash(user_id) % 10
            APPROACH_TENDENCY.labels(user_bucket=str(bucket)).set(
                profile.approach_avoidance.net_tendency
            )
            COGNITIVE_LOAD.labels(user_bucket=str(bucket)).set(
                profile.cognitive_load.total_load
            )
            
            for mechanism in profile.recommended_mechanisms:
                MECHANISM_RECOMMENDATIONS.labels(mechanism=mechanism).inc()
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            ANALYSIS_LATENCY.observe(elapsed)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error generating nonconscious profile: {e}")
            return None
    
    async def get_quick_assessment(
        self,
        user_id: str,
        session_id: str,
        min_signals: int = 3,
    ) -> Dict[str, Any]:
        """
        Get a quick assessment without full profile generation.
        
        Useful for real-time decisions when full analysis is too slow.
        """
        signals = self._signal_buffers.get(user_id, [])
        session_signals = [s for s in signals if s.session_id == session_id]
        
        if len(session_signals) < min_signals:
            return {
                "status": "insufficient_data",
                "signals_collected": len(session_signals),
                "recommended_processing": "central",
            }
        
        # Quick heuristics
        # Check for high conflict/hesitation
        conflict_signals = sum(
            1 for s in session_signals
            if hasattr(s, "conflict_indicator") and s.conflict_indicator > 0.5
        )
        
        # Check for slow responses
        slow_signals = sum(
            1 for s in session_signals
            if hasattr(s, "deviation_from_baseline") and s.deviation_from_baseline > 1.5
        )
        
        # Quick cognitive load estimate
        if slow_signals > len(session_signals) * 0.3:
            processing = ProcessingDepth.PERIPHERAL
        elif conflict_signals > len(session_signals) * 0.2:
            processing = ProcessingDepth.MIXED
        else:
            processing = ProcessingDepth.CENTRAL
        
        return {
            "status": "quick_assessment",
            "signals_collected": len(session_signals),
            "conflict_indicator": conflict_signals / max(1, len(session_signals)),
            "slow_response_indicator": slow_signals / max(1, len(session_signals)),
            "recommended_processing": processing.value,
        }
    
    # =========================================================================
    # IMPLICIT PREFERENCES
    # =========================================================================
    
    async def track_preference_signal(
        self,
        user_id: str,
        target_id: str,
        target_type: str,
        signal: NonconsciousSignal,
    ) -> None:
        """
        Track a signal related to a specific preference target.
        """
        key = f"{user_id}:{target_type}:{target_id}"
        
        if key not in self._preference_store:
            self._preference_store[key] = {
                "signals": [],
                "last_inference": None,
            }
        
        self._preference_store[key]["signals"].append(signal)
    
    async def get_implicit_preference(
        self,
        user_id: str,
        target_id: str,
        target_type: str,
    ) -> Optional[ImplicitPreference]:
        """
        Get inferred implicit preference for a target.
        """
        key = f"{user_id}:{target_type}:{target_id}"
        
        if key not in self._preference_store:
            return None
        
        data = self._preference_store[key]
        signals = data["signals"]
        
        if len(signals) < 2:
            return None
        
        return self.analyzer.preference.infer_preference(
            signals,
            target_id,
            target_type,
            user_id,
        )
    
    # =========================================================================
    # BLACKBOARD INTEGRATION
    # =========================================================================
    
    async def prepare_blackboard_context(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Prepare nonconscious context for Blackboard Zone 1.
        
        This provides implicit context for atom processing.
        """
        profile = await self.get_profile(user_id, session_id)
        
        if not profile:
            quick = await self.get_quick_assessment(user_id, session_id)
            return {
                "nonconscious_available": False,
                "quick_assessment": quick,
            }
        
        return {
            "nonconscious_available": True,
            "approach_avoidance": {
                "net_tendency": profile.approach_avoidance.net_tendency,
                "approach_strength": profile.approach_avoidance.approach_strength,
                "avoidance_strength": profile.approach_avoidance.avoidance_strength,
            },
            "cognitive_load": {
                "total": profile.cognitive_load.total_load,
                "is_overloaded": profile.cognitive_load.is_overloaded,
                "capacity_remaining": profile.cognitive_load.capacity_remaining,
            },
            "processing_fluency": {
                "overall": profile.processing_fluency.overall_fluency,
                "preference_boost": profile.processing_fluency.likely_preference_boost,
            },
            "emotional_valence": {
                "valence": profile.emotional_valence.valence,
                "direction": profile.emotional_valence.valence_direction.value,
                "arousal": profile.emotional_valence.arousal,
            },
            "engagement": {
                "overall": profile.engagement.overall_engagement,
                "trend": profile.engagement.engagement_trend,
            },
            "recommended_processing_route": profile.recommended_processing_route.value,
            "recommended_mechanisms": profile.recommended_mechanisms,
            "mechanism_confidence": profile.mechanism_confidence,
            "profile_confidence": profile.overall_confidence,
        }
    
    # =========================================================================
    # ATOM INTEGRATION
    # =========================================================================
    
    async def get_regulatory_focus_hints(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, float]:
        """
        Get regulatory focus hints for RegulatoryFocusAtom.
        
        Based on approach-avoidance tendency:
        - High approach = promotion focus
        - High avoidance = prevention focus
        """
        profile = await self.get_profile(user_id, session_id)
        
        if not profile:
            return {"promotion_hint": 0.5, "prevention_hint": 0.5}
        
        aa = profile.approach_avoidance
        
        # Map approach-avoidance to regulatory focus
        # Approach motivation → promotion focus
        # Avoidance motivation → prevention focus
        promotion = 0.5 + aa.approach_strength * 0.3 - aa.avoidance_strength * 0.1
        prevention = 0.5 + aa.avoidance_strength * 0.3 - aa.approach_strength * 0.1
        
        return {
            "promotion_hint": min(1.0, max(0.0, promotion)),
            "prevention_hint": min(1.0, max(0.0, prevention)),
            "confidence": aa.confidence,
        }
    
    async def get_construal_level_hints(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, float]:
        """
        Get construal level hints for ConstrualLevelAtom.
        
        Based on cognitive load and processing fluency:
        - High load + low fluency = concrete (low construal)
        - Low load + high fluency = abstract (high construal)
        """
        profile = await self.get_profile(user_id, session_id)
        
        if not profile:
            return {"abstract_hint": 0.5, "concrete_hint": 0.5}
        
        cl = profile.cognitive_load
        pf = profile.processing_fluency
        
        # High load/low fluency → concrete processing
        # Low load/high fluency → abstract processing
        concrete = (cl.total_load * 0.6 + (1 - pf.overall_fluency) * 0.4)
        abstract = ((1 - cl.total_load) * 0.6 + pf.overall_fluency * 0.4)
        
        return {
            "abstract_hint": abstract,
            "concrete_hint": concrete,
            "confidence": (cl.confidence + pf.confidence) / 2,
        }
    
    async def get_mechanism_activation_hints(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get mechanism activation hints for MechanismActivationAtom.
        """
        profile = await self.get_profile(user_id, session_id)
        
        if not profile:
            return {"mechanisms": [], "confidence": {}}
        
        return {
            "mechanisms": profile.recommended_mechanisms,
            "confidence": profile.mechanism_confidence,
            "processing_route": profile.recommended_processing_route.value,
        }
    
    # =========================================================================
    # GRADIENT BRIDGE INTEGRATION
    # =========================================================================
    
    async def emit_learning_signal(
        self,
        user_id: str,
        session_id: str,
        decision_id: str,
        outcome: str,
        outcome_value: float,
        mechanisms_used: List[str],
    ) -> None:
        """
        Emit learning signal for mechanism effectiveness.
        
        Associates outcome with the nonconscious profile that
        informed the decision.
        """
        profile = await self.get_profile(user_id, session_id)
        
        if not profile:
            return
        
        signal = {
            "type": "nonconscious_learning",
            "decision_id": decision_id,
            "user_id": user_id,
            "session_id": session_id,
            "outcome": outcome,
            "outcome_value": outcome_value,
            
            # Profile at time of decision
            "profile_snapshot": {
                "approach_avoidance": profile.approach_avoidance.net_tendency,
                "cognitive_load": profile.cognitive_load.total_load,
                "processing_fluency": profile.processing_fluency.overall_fluency,
                "emotional_valence": profile.emotional_valence.valence,
            },
            
            # What was recommended
            "recommended_mechanisms": profile.recommended_mechanisms,
            
            # What was used
            "mechanisms_used": mechanisms_used,
            
            # For learning
            "recommendation_followed": set(mechanisms_used) & set(profile.recommended_mechanisms),
            "recommendation_ignored": set(profile.recommended_mechanisms) - set(mechanisms_used),
            
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if self.kafka:
            await self.kafka.send(
                "adam.signals.learning",
                signal,
            )
        
        logger.info(f"Emitted nonconscious learning signal for decision {decision_id}")
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    async def _persist_signal(self, signal: NonconsciousSignal) -> None:
        """
        Persist signal to Redis for recovery and analysis.
        """
        if not self.redis:
            return
        
        try:
            key = f"nc:signals:{signal.user_id}:{signal.session_id}"
            await self.redis.zadd(
                key,
                {
                    signal.model_dump_json(): signal.timestamp.timestamp(),
                },
            )
            # Expire after 24 hours
            await self.redis.expire(key, 86400)
        except Exception as e:
            logger.warning(f"Failed to persist signal: {e}")
    
    async def load_signals(
        self,
        user_id: str,
        session_id: str,
    ) -> List[NonconsciousSignal]:
        """
        Load signals from Redis.
        """
        if not self.redis:
            return self._signal_buffers.get(user_id, [])
        
        try:
            key = f"nc:signals:{user_id}:{session_id}"
            raw_signals = await self.redis.zrange(key, 0, -1)
            
            # Would need to deserialize based on signal type
            # Simplified here - in production use a type discriminator
            return self._signal_buffers.get(user_id, [])
        except Exception as e:
            logger.warning(f"Failed to load signals: {e}")
            return self._signal_buffers.get(user_id, [])
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    async def cleanup_old_data(self, max_age_hours: int = 24) -> None:
        """
        Clean up old signals and profiles.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Clean signal buffers
        for user_id in list(self._signal_buffers.keys()):
            self._signal_buffers[user_id] = [
                s for s in self._signal_buffers[user_id]
                if s.timestamp > cutoff
            ]
            if not self._signal_buffers[user_id]:
                del self._signal_buffers[user_id]
        
        # Clean profile cache
        for key in list(self._profile_cache.keys()):
            if self._profile_cache[key].valid_until < datetime.now(timezone.utc):
                del self._profile_cache[key]
        
        logger.info("Cleaned up old nonconscious analytics data")
