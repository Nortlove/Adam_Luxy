# =============================================================================
# ADAM Signal Processors
# Location: adam/user/signal_aggregation/processors.py
# =============================================================================

"""
SIGNAL PROCESSORS

Process raw signals from various sources into psychological features.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# SIGNAL MODELS
# =============================================================================

class SignalCategory(str, Enum):
    """Signal categories."""
    
    # Web behavioral
    BEHAVIORAL = "behavioral"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    
    # Implicit signals
    KINEMATIC = "kinematic"       # Mouse, scroll
    TEMPORAL = "temporal"         # Timing patterns
    
    # Audio platform
    AUDIO_LISTENING = "audio_listening"
    AUDIO_SKIP = "audio_skip"
    AD_INTERACTION = "ad_interaction"
    
    # Content
    CONTENT = "content"


class RawSignal(BaseModel):
    """Raw signal from capture."""
    
    signal_id: str
    user_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: SignalCategory
    signal_type: str
    
    # Raw values
    raw_value: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    source: str = Field(default="unknown")
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)


class ProcessedSignal(BaseModel):
    """Processed signal with psychological features."""
    
    signal_id: str
    user_id: str
    timestamp: datetime
    category: SignalCategory
    signal_type: str
    
    # Extracted features
    features: Dict[str, float] = Field(default_factory=dict)
    
    # Psychological mapping
    psychological_indicators: Dict[str, float] = Field(default_factory=dict)
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class SignalWindow(BaseModel):
    """Aggregated signals over time window."""
    
    window_id: str
    user_id: str
    window_start: datetime
    window_end: datetime
    
    # Aggregated features
    features: Dict[str, float] = Field(default_factory=dict)
    signal_count: int = Field(default=0, ge=0)
    
    # Quality
    completeness: float = Field(ge=0.0, le=1.0, default=0.5)


# =============================================================================
# BASE PROCESSOR
# =============================================================================

class SignalProcessor(ABC):
    """Base class for signal processors."""
    
    category: SignalCategory
    
    @abstractmethod
    async def process(self, raw_signal: RawSignal) -> List[ProcessedSignal]:
        """Process a raw signal into psychological features."""
        pass
    
    def _extract_arousal_indicators(
        self,
        values: Dict[str, Any],
    ) -> Dict[str, float]:
        """Extract arousal indicators from signal values."""
        indicators = {}
        
        # Speed-based arousal
        if "speed" in values or "velocity" in values:
            speed = values.get("speed", values.get("velocity", 0))
            indicators["arousal_from_speed"] = min(1.0, speed / 100)
        
        # Skip-based arousal
        if "skip_rate" in values:
            indicators["arousal_from_skips"] = values["skip_rate"]
        
        return indicators


# =============================================================================
# IHEART SIGNAL PROCESSOR
# =============================================================================

class iHeartSignalProcessor(SignalProcessor):
    """Process signals from iHeart audio platform."""
    
    category = SignalCategory.AUDIO_LISTENING
    
    # Genre → Personality mappings
    GENRE_PERSONALITY = {
        "pop": {"extraversion": 0.65, "openness": 0.50},
        "rock": {"openness": 0.55, "extraversion": 0.55},
        "country": {"agreeableness": 0.60, "conscientiousness": 0.55},
        "hip_hop": {"extraversion": 0.68, "openness": 0.52},
        "classical": {"openness": 0.72, "conscientiousness": 0.60},
        "jazz": {"openness": 0.75, "extraversion": 0.48},
        "electronic": {"openness": 0.65, "extraversion": 0.62},
    }
    
    async def process(self, raw_signal: RawSignal) -> List[ProcessedSignal]:
        """Process iHeart listening signal."""
        signals = []
        values = raw_signal.raw_value
        
        signal_type = values.get("event_type", raw_signal.signal_type)
        
        if signal_type == "track_listen":
            signals.append(self._process_track_listen(raw_signal, values))
        elif signal_type == "skip":
            signals.append(self._process_skip(raw_signal, values))
        elif signal_type == "ad_listen":
            signals.append(self._process_ad_listen(raw_signal, values))
        
        return signals
    
    def _process_track_listen(
        self,
        raw: RawSignal,
        values: Dict[str, Any],
    ) -> ProcessedSignal:
        """Process track listening event."""
        features = {
            "listen_duration": values.get("duration_seconds", 0) / 300,  # Normalize to 5min
            "completion_rate": values.get("completion_percentage", 0) / 100,
            "energy": values.get("track_energy", 0.5),
            "valence": values.get("track_valence", 0.5),
        }
        
        # Extract genre-based personality hints
        psych = {}
        genre = values.get("genre", "").lower()
        if genre in self.GENRE_PERSONALITY:
            psych = self.GENRE_PERSONALITY[genre].copy()
        
        return ProcessedSignal(
            signal_id=f"{raw.signal_id}_track",
            user_id=raw.user_id,
            timestamp=raw.timestamp,
            category=SignalCategory.AUDIO_LISTENING,
            signal_type="track_listen",
            features=features,
            psychological_indicators=psych,
            confidence=0.6 if values.get("completion_percentage", 0) > 80 else 0.4,
        )
    
    def _process_skip(
        self,
        raw: RawSignal,
        values: Dict[str, Any],
    ) -> ProcessedSignal:
        """Process skip event - indicates impatience/arousal."""
        features = {
            "skip_position": values.get("skip_position_percentage", 50) / 100,
            "consecutive_skips": min(1.0, values.get("consecutive_skips", 1) / 5),
        }
        
        # High skip rate indicates high arousal or neuroticism
        psych = {
            "arousal": 0.3 + features["consecutive_skips"] * 0.4,
            "neuroticism_signal": features["consecutive_skips"] * 0.3,
        }
        
        return ProcessedSignal(
            signal_id=f"{raw.signal_id}_skip",
            user_id=raw.user_id,
            timestamp=raw.timestamp,
            category=SignalCategory.AUDIO_SKIP,
            signal_type="skip",
            features=features,
            psychological_indicators=psych,
            confidence=0.7,
        )
    
    def _process_ad_listen(
        self,
        raw: RawSignal,
        values: Dict[str, Any],
    ) -> ProcessedSignal:
        """Process ad listening event."""
        features = {
            "listen_through": 1.0 if values.get("listened_through") else 0.0,
            "listen_percentage": values.get("listen_percentage", 0) / 100,
            "clicked": 1.0 if values.get("clicked") else 0.0,
        }
        
        return ProcessedSignal(
            signal_id=f"{raw.signal_id}_ad",
            user_id=raw.user_id,
            timestamp=raw.timestamp,
            category=SignalCategory.AD_INTERACTION,
            signal_type="ad_listen",
            features=features,
            psychological_indicators={},
            confidence=0.8,
        )


# =============================================================================
# WEB SIGNAL PROCESSOR
# =============================================================================

class WebSignalProcessor(SignalProcessor):
    """Process signals from web behavioral tracking."""
    
    category = SignalCategory.BEHAVIORAL
    
    async def process(self, raw_signal: RawSignal) -> List[ProcessedSignal]:
        """Process web behavioral signal."""
        values = raw_signal.raw_value
        
        features = {}
        psych = {}
        
        # Mouse dynamics
        if "mouse_velocity" in values:
            velocity = values["mouse_velocity"]
            features["mouse_velocity"] = min(1.0, velocity / 1000)
            psych["arousal_from_mouse"] = features["mouse_velocity"] * 0.5
        
        # Scroll behavior
        if "scroll_depth" in values:
            features["scroll_depth"] = values["scroll_depth"] / 100
            # Deep scrolling indicates engagement
            psych["engagement"] = features["scroll_depth"]
        
        # Click patterns
        if "click_rate" in values:
            features["click_rate"] = min(1.0, values["click_rate"] / 10)
        
        # Time on page
        if "time_on_page" in values:
            features["time_on_page"] = min(1.0, values["time_on_page"] / 120)
            psych["attention"] = features["time_on_page"]
        
        return [ProcessedSignal(
            signal_id=f"{raw_signal.signal_id}_web",
            user_id=raw_signal.user_id,
            timestamp=raw_signal.timestamp,
            category=SignalCategory.BEHAVIORAL,
            signal_type="web_behavior",
            features=features,
            psychological_indicators=psych,
            confidence=0.6,
        )]
