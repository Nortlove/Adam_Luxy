# =============================================================================
# ADAM Behavioral Analytics: Multimodal Fusion Extension
# Location: adam/behavioral_analytics/extensions/multimodal_extension.py
# =============================================================================

"""
MULTIMODAL FUSION EXTENSION FOR BEHAVIORAL ANALYTICS

Extends the existing Multimodal Fusion (#16) infrastructure with
behavioral-specific modalities for implicit signal integration.

This extends rather than recreates - uses existing:
- ModalitySignal structure
- FusedProfile output
- Cross-modal fusion logic
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from adam.multimodal.models import (
    Modality,
    SignalSource,
    ModalitySignal,
    ModalityWeight,
    FusedProfile,
)
from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    TouchEvent,
    SwipeEvent,
    ScrollEvent,
)
from adam.behavioral_analytics.models.knowledge import BehavioralKnowledge


class BehavioralModality(str, Enum):
    """
    Sub-modalities within the BEHAVIORAL modality.
    
    These extend the existing Modality.BEHAVIORAL with specific
    implicit signal types.
    """
    # Implicit sub-modalities
    TOUCH_DYNAMICS = "touch_dynamics"      # Pressure, duration
    SWIPE_PATTERNS = "swipe_patterns"      # Direction, velocity, directness
    SCROLL_BEHAVIOR = "scroll_behavior"    # Velocity, pauses, depth
    TEMPORAL_PATTERNS = "temporal_patterns"  # Response latency, dwell
    SENSOR_DATA = "sensor_data"            # Accelerometer, gyroscope
    ATTENTION_SIGNALS = "attention_signals"  # Hesitation, rage clicks
    
    # Explicit sub-modalities (already in system, for completeness)
    CLICK_PATTERNS = "click_patterns"
    NAVIGATION_PATTERNS = "navigation_patterns"
    CART_BEHAVIOR = "cart_behavior"
    PURCHASE_HISTORY = "purchase_history"


class BehavioralSignalSource(str, Enum):
    """Sources of behavioral signals."""
    MOBILE_APP = "mobile_app"
    WEB_BROWSER = "web_browser"
    IHEART_APP = "iheart_app"
    PARTNER_SITE = "partner_site"
    SDK_INTEGRATION = "sdk_integration"


class BehavioralModalitySignal(BaseModel):
    """
    A behavioral modality signal.
    
    Extends ModalitySignal with behavioral-specific attributes.
    """
    
    # Base signal fields (compatible with ModalitySignal)
    signal_id: str
    modality: Modality = Modality.BEHAVIORAL  # Always BEHAVIORAL for behavioral signals
    source: BehavioralSignalSource
    user_id: str
    
    # Behavioral-specific
    sub_modality: BehavioralModality
    session_id: str
    
    # Raw data (compatible with ModalitySignal)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Extracted features
    features: Dict[str, float] = Field(default_factory=dict)
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Signal source knowledge (which research backs this?)
    knowledge_ids: List[str] = Field(default_factory=list)
    
    # Timing
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def to_modality_signal(self) -> ModalitySignal:
        """Convert to base ModalitySignal for fusion."""
        return ModalitySignal(
            signal_id=self.signal_id,
            modality=self.modality,
            source=SignalSource.AMAZON_PURCHASE,  # Map to existing, or extend
            user_id=self.user_id,
            raw_data={
                "sub_modality": self.sub_modality.value,
                "session_id": self.session_id,
                **self.raw_data
            },
            features=self.features,
            confidence=self.confidence,
            observed_at=self.observed_at,
        )


class BehavioralModalityWeights(BaseModel):
    """
    Weights for behavioral sub-modalities in fusion.
    
    These weights are learned from outcomes and adjust based on
    signal reliability for different contexts.
    """
    
    # Default weights for sub-modalities
    touch_dynamics: float = 0.20
    swipe_patterns: float = 0.15
    scroll_behavior: float = 0.15
    temporal_patterns: float = 0.25  # Highest - response latency is strong
    sensor_data: float = 0.10
    attention_signals: float = 0.15
    
    # Context adjustments
    # e.g., "checkout" context might increase attention_signals weight
    context_adjustments: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    def get_weight(
        self,
        sub_modality: BehavioralModality,
        context: Optional[str] = None
    ) -> float:
        """Get weight for sub-modality, adjusted for context."""
        base_weight = getattr(self, sub_modality.value.replace("_patterns", "").replace("_dynamics", "").replace("_behavior", "").replace("_data", "").replace("_signals", ""), 0.15)
        
        if context and context in self.context_adjustments:
            adjustment = self.context_adjustments[context].get(sub_modality.value, 0.0)
            return max(0.0, min(1.0, base_weight + adjustment))
        
        return base_weight


class BehavioralProfileContribution(BaseModel):
    """
    Contribution of behavioral signals to fused profile.
    
    Added to FusedProfile.modality_contributions["behavioral"].
    """
    
    # Inferred states from behavioral signals
    emotional_arousal: Optional[float] = None
    decision_confidence: Optional[float] = None
    cognitive_load: Optional[float] = None
    purchase_intent: Optional[float] = None
    frustration_level: Optional[float] = None
    
    # Big Five contributions (requires longitudinal data)
    big_five_contributions: Dict[str, float] = Field(default_factory=dict)
    
    # Regulatory focus hints
    promotion_focus_signals: List[str] = Field(default_factory=list)
    prevention_focus_signals: List[str] = Field(default_factory=list)
    
    # Construal level hints
    construal_signals: List[str] = Field(default_factory=list)
    
    # Sub-modality breakdown
    sub_modality_contributions: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Quality metrics
    signal_count: int = 0
    session_duration_ms: int = 0
    confidence: float = 0.5


def extract_behavioral_signals(
    session: BehavioralSession,
    knowledge: List[BehavioralKnowledge]
) -> List[BehavioralModalitySignal]:
    """
    Extract behavioral modality signals from a session.
    
    Uses research-validated knowledge to guide feature extraction.
    
    Args:
        session: The behavioral session
        knowledge: Available behavioral knowledge for construct mapping
        
    Returns:
        List of behavioral modality signals for fusion
    """
    import uuid
    signals = []
    
    # Touch dynamics signal
    if session.touches:
        touch_features = _extract_touch_features(session.touches)
        
        # Find relevant knowledge
        touch_knowledge = [
            k.knowledge_id for k in knowledge
            if k.signal_name in ["touch_pressure", "touch_duration"]
        ]
        
        signals.append(BehavioralModalitySignal(
            signal_id=f"bs_{uuid.uuid4().hex[:12]}",
            source=BehavioralSignalSource.MOBILE_APP,
            user_id=session.user_id or session.device_id,
            sub_modality=BehavioralModality.TOUCH_DYNAMICS,
            session_id=session.session_id,
            raw_data={"touch_count": len(session.touches)},
            features=touch_features,
            confidence=min(0.9, len(session.touches) / 50),  # More touches = more confidence
            knowledge_ids=touch_knowledge,
        ))
    
    # Swipe patterns signal
    if session.swipes:
        swipe_features = _extract_swipe_features(session.swipes)
        
        swipe_knowledge = [
            k.knowledge_id for k in knowledge
            if k.signal_name in ["swipe_directness", "swipe_direction"]
        ]
        
        signals.append(BehavioralModalitySignal(
            signal_id=f"bs_{uuid.uuid4().hex[:12]}",
            source=BehavioralSignalSource.MOBILE_APP,
            user_id=session.user_id or session.device_id,
            sub_modality=BehavioralModality.SWIPE_PATTERNS,
            session_id=session.session_id,
            raw_data={"swipe_count": len(session.swipes)},
            features=swipe_features,
            confidence=min(0.9, len(session.swipes) / 20),
            knowledge_ids=swipe_knowledge,
        ))
    
    # Scroll behavior signal
    if session.scrolls:
        scroll_features = _extract_scroll_features(session.scrolls)
        
        scroll_knowledge = [
            k.knowledge_id for k in knowledge
            if k.signal_name in ["scroll_velocity"]
        ]
        
        signals.append(BehavioralModalitySignal(
            signal_id=f"bs_{uuid.uuid4().hex[:12]}",
            source=BehavioralSignalSource.MOBILE_APP,
            user_id=session.user_id or session.device_id,
            sub_modality=BehavioralModality.SCROLL_BEHAVIOR,
            session_id=session.session_id,
            raw_data={"scroll_event_count": len(session.scrolls)},
            features=scroll_features,
            confidence=min(0.9, len(session.scrolls) / 30),
            knowledge_ids=scroll_knowledge,
        ))
    
    # Temporal patterns signal
    if session.page_views or session.clicks:
        temporal_features = _extract_temporal_features(session)
        
        temporal_knowledge = [
            k.knowledge_id for k in knowledge
            if k.signal_name in ["response_latency", "dwell_time"]
        ]
        
        signals.append(BehavioralModalitySignal(
            signal_id=f"bs_{uuid.uuid4().hex[:12]}",
            source=BehavioralSignalSource.MOBILE_APP,
            user_id=session.user_id or session.device_id,
            sub_modality=BehavioralModality.TEMPORAL_PATTERNS,
            session_id=session.session_id,
            raw_data={"page_views": len(session.page_views), "clicks": len(session.clicks)},
            features=temporal_features,
            confidence=0.8,
            knowledge_ids=temporal_knowledge,
        ))
    
    # Attention signals (hesitation, rage clicks)
    if session.hesitations or session.rage_clicks:
        attention_features = _extract_attention_features(session)
        
        attention_knowledge = [
            k.knowledge_id for k in knowledge
            if k.signal_name in ["hesitation_pre_cta", "rage_clicks"]
        ]
        
        signals.append(BehavioralModalitySignal(
            signal_id=f"bs_{uuid.uuid4().hex[:12]}",
            source=BehavioralSignalSource.MOBILE_APP,
            user_id=session.user_id or session.device_id,
            sub_modality=BehavioralModality.ATTENTION_SIGNALS,
            session_id=session.session_id,
            raw_data={
                "hesitation_count": len(session.hesitations),
                "rage_click_count": len(session.rage_clicks)
            },
            features=attention_features,
            confidence=0.85,
            knowledge_ids=attention_knowledge,
        ))
    
    # Sensor data signal
    if session.sensor_samples:
        sensor_features = _extract_sensor_features(session.sensor_samples)
        
        sensor_knowledge = [
            k.knowledge_id for k in knowledge
            if k.signal_name in ["accelerometer_variance"]
        ]
        
        signals.append(BehavioralModalitySignal(
            signal_id=f"bs_{uuid.uuid4().hex[:12]}",
            source=BehavioralSignalSource.MOBILE_APP,
            user_id=session.user_id or session.device_id,
            sub_modality=BehavioralModality.SENSOR_DATA,
            session_id=session.session_id,
            raw_data={"sample_count": len(session.sensor_samples)},
            features=sensor_features,
            confidence=min(0.9, len(session.sensor_samples) / 200),
            knowledge_ids=sensor_knowledge,
        ))
    
    return signals


def _extract_touch_features(touches: List[TouchEvent]) -> Dict[str, float]:
    """Extract features from touch events."""
    if not touches:
        return {}
    
    pressures = [t.pressure for t in touches]
    durations = [t.duration_ms for t in touches]
    
    features = {
        "pressure_mean": sum(pressures) / len(pressures),
        "pressure_std": _std(pressures),
        "pressure_max": max(pressures),
        "pressure_min": min(pressures),
        "duration_mean": sum(durations) / len(durations) if durations else 0,
        "duration_std": _std(durations),
        "touch_count": float(len(touches)),
    }
    
    # Touch rate
    if len(touches) >= 2:
        time_span_ms = (touches[-1].timestamp - touches[0].timestamp).total_seconds() * 1000
        if time_span_ms > 0:
            features["touch_rate"] = len(touches) / (time_span_ms / 1000)  # per second
    
    return features


def _extract_swipe_features(swipes: List[SwipeEvent]) -> Dict[str, float]:
    """Extract features from swipe events."""
    if not swipes:
        return {}
    
    velocities = [s.velocity for s in swipes]
    directnesses = [s.directness for s in swipes]
    direction_changes = [s.direction_changes for s in swipes]
    
    # Direction ratios
    from adam.behavioral_analytics.models.events import SwipeDirection
    right_count = sum(1 for s in swipes if s.direction == SwipeDirection.RIGHT)
    up_count = sum(1 for s in swipes if s.direction == SwipeDirection.UP)
    
    features = {
        "velocity_mean": sum(velocities) / len(velocities),
        "velocity_std": _std(velocities),
        "velocity_max": max(velocities),
        "directness_mean": sum(directnesses) / len(directnesses),
        "directness_std": _std(directnesses),
        "direction_changes_mean": sum(direction_changes) / len(direction_changes),
        "right_swipe_ratio": right_count / len(swipes),
        "up_swipe_ratio": up_count / len(swipes),
        "swipe_count": float(len(swipes)),
    }
    
    return features


def _extract_scroll_features(scrolls: List[ScrollEvent]) -> Dict[str, float]:
    """Extract features from scroll events."""
    if not scrolls:
        return {}
    
    velocities = [s.velocity for s in scrolls]
    depths = [s.scroll_depth_percent for s in scrolls]
    pause_count = sum(1 for s in scrolls if s.is_pause)
    reversal_count = sum(1 for s in scrolls if s.is_reversal)
    
    features = {
        "velocity_mean": sum(velocities) / len(velocities),
        "velocity_std": _std(velocities),
        "max_depth": max(depths),
        "pause_ratio": pause_count / len(scrolls),
        "reversal_ratio": reversal_count / len(scrolls),
        "scroll_event_count": float(len(scrolls)),
    }
    
    return features


def _extract_temporal_features(session: BehavioralSession) -> Dict[str, float]:
    """Extract temporal pattern features."""
    features = {}
    
    # Dwell times from page views
    if session.page_views:
        dwell_times = [pv.dwell_time_ms for pv in session.page_views]
        features["dwell_time_mean"] = sum(dwell_times) / len(dwell_times)
        features["dwell_time_std"] = _std(dwell_times)
        features["dwell_time_max"] = max(dwell_times)
    
    # Response latency from clicks
    if len(session.clicks) >= 2:
        latencies = []
        sorted_clicks = sorted(session.clicks, key=lambda c: c.timestamp)
        for i in range(1, len(sorted_clicks)):
            latency = (sorted_clicks[i].timestamp - sorted_clicks[i-1].timestamp).total_seconds() * 1000
            latencies.append(latency)
        
        if latencies:
            features["response_latency_mean"] = sum(latencies) / len(latencies)
            features["response_latency_std"] = _std(latencies)
            features["response_latency_p50"] = sorted(latencies)[len(latencies) // 2]
    
    # Session duration
    features["session_duration_ms"] = float(session.duration_ms)
    
    return features


def _extract_attention_features(session: BehavioralSession) -> Dict[str, float]:
    """Extract attention/frustration features."""
    features = {}
    
    # Hesitation metrics
    if session.hesitations:
        hesitation_times = [h.dwell_time_ms for h in session.hesitations]
        features["hesitation_count"] = float(len(session.hesitations))
        features["hesitation_mean_ms"] = sum(hesitation_times) / len(hesitation_times)
        
        cta_hesitations = [h for h in session.hesitations if h.element_type == "cta"]
        if cta_hesitations:
            features["pre_cta_hesitation_ratio"] = len(cta_hesitations) / len(session.hesitations)
    
    # Rage clicks
    if session.rage_clicks:
        features["rage_click_count"] = float(len(session.rage_clicks))
        features["rage_click_total_clicks"] = float(sum(rc.click_count for rc in session.rage_clicks))
    
    return features


def _extract_sensor_features(samples) -> Dict[str, float]:
    """Extract sensor features from accelerometer/gyroscope samples."""
    if not samples:
        return {}
    
    magnitudes = [s.magnitude for s in samples]
    
    features = {
        "magnitude_mean": sum(magnitudes) / len(magnitudes),
        "magnitude_std": _std(magnitudes),
        "magnitude_max": max(magnitudes),
        "sample_count": float(len(samples)),
    }
    
    # Calculate jerk (rate of change in acceleration)
    if len(samples) >= 2:
        jerks = []
        for i in range(1, len(samples)):
            dt = (samples[i].timestamp - samples[i-1].timestamp).total_seconds()
            if dt > 0:
                jerk = abs(samples[i].magnitude - samples[i-1].magnitude) / dt
                jerks.append(jerk)
        
        if jerks:
            features["jerk_mean"] = sum(jerks) / len(jerks)
            features["jerk_max"] = max(jerks)
    
    return features


def _std(values: List[float]) -> float:
    """Compute standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5
