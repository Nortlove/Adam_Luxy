# =============================================================================
# ADAM Nonconscious Analytics - Signal Capture
# =============================================================================

"""
NONCONSCIOUS SIGNAL CAPTURE

Real-time capture of implicit behavioral signals from user interactions.

Design Principles:
- Capture at highest fidelity possible (millisecond resolution)
- Non-blocking, asynchronous processing
- Privacy-preserving (no PII in raw signals)
- Configurable capture depth based on privacy settings
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from adam.signals.nonconscious.models import (
    NonconsciousSignal,
    KinematicSignal,
    ScrollBehaviorSignal,
    KeystrokeSignal,
    TemporalSignal,
    HesitationSignal,
    RhythmicSignal,
    SignalSource,
)

logger = logging.getLogger(__name__)


# =============================================================================
# BASE CAPTURE CLASS
# =============================================================================

class SignalCaptureConfig(BaseModel):
    """Configuration for signal capture."""
    
    # Sampling rates
    mouse_sample_rate_ms: int = Field(default=16, description="~60fps")
    scroll_sample_rate_ms: int = Field(default=50)
    keystroke_buffer_size: int = Field(default=100)
    
    # Thresholds
    hover_threshold_ms: int = Field(default=300)
    pause_threshold_ms: int = Field(default=1000)
    hesitation_threshold_ms: int = Field(default=500)
    
    # Privacy
    anonymize_positions: bool = Field(default=True)
    capture_element_ids: bool = Field(default=True)
    capture_text_content: bool = Field(default=False)


class BaseSignalCapture(ABC):
    """Base class for signal capture implementations."""
    
    def __init__(self, config: SignalCaptureConfig = None):
        self.config = config or SignalCaptureConfig()
    
    @abstractmethod
    async def capture(self, raw_data: Dict[str, Any]) -> Optional[NonconsciousSignal]:
        """Capture and process raw signal data."""
        pass


# =============================================================================
# MOUSE DYNAMICS CAPTURE
# =============================================================================

class MouseDynamicsCapture(BaseSignalCapture):
    """
    Capture mouse movement dynamics.
    
    Research basis:
    - Mouse trajectories reveal cognitive processes (Freeman & Ambady, 2010)
    - Movement dynamics reflect approach-avoidance (Krieglmeyer & Deutsch, 2010)
    - Cursor velocity correlates with decision confidence (Kieslich et al., 2019)
    """
    
    async def capture(self, raw_data: Dict[str, Any]) -> Optional[KinematicSignal]:
        """
        Process raw mouse data into psychological indicators.
        
        Expected raw_data format:
        {
            "user_id": str,
            "session_id": str,
            "positions": [(x, y, timestamp_ms), ...],
            "page_url": str,
            "target_element": str
        }
        """
        user_id = raw_data.get("user_id", "")
        session_id = raw_data.get("session_id", "")
        positions = raw_data.get("positions", [])
        
        if not positions or len(positions) < 2:
            return None
        
        # Calculate movement metrics
        total_distance = 0.0
        velocities = []
        x_flips = 0
        y_flips = 0
        prev_x_dir = 0
        prev_y_dir = 0
        
        for i in range(1, len(positions)):
            x1, y1, t1 = positions[i - 1]
            x2, y2, t2 = positions[i]
            
            # Distance
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx**2 + dy**2)
            total_distance += dist
            
            # Velocity
            dt = max(1, t2 - t1)  # Avoid division by zero
            velocity = dist / dt * 1000  # pixels per second
            velocities.append(velocity)
            
            # Direction changes (x-flips indicate decision conflict)
            if dx != 0:
                x_dir = 1 if dx > 0 else -1
                if prev_x_dir != 0 and x_dir != prev_x_dir:
                    x_flips += 1
                prev_x_dir = x_dir
            
            if dy != 0:
                y_dir = 1 if dy > 0 else -1
                if prev_y_dir != 0 and y_dir != prev_y_dir:
                    y_flips += 1
                prev_y_dir = y_dir
        
        # Calculate derived metrics
        duration_ms = positions[-1][2] - positions[0][2] if len(positions) > 1 else 0
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0
        max_velocity = max(velocities) if velocities else 0
        velocity_variance = self._variance(velocities) if velocities else 0
        
        # Directness ratio (1.0 = perfectly direct, lower = more meandering)
        start_pos = positions[0]
        end_pos = positions[-1]
        straight_line = math.sqrt(
            (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2
        )
        directness = straight_line / total_distance if total_distance > 0 else 1.0
        
        # Calculate psychological indicators
        # High x-flips indicate decisional conflict (Freeman & Ambady, 2010)
        conflict_indicator = min(1.0, x_flips / max(1, len(positions) / 20))
        
        # High velocity variance + low directness = low decisiveness
        decisiveness = (
            (1 - conflict_indicator) * 0.4 +
            directness * 0.3 +
            (1 - min(1.0, velocity_variance / 100000)) * 0.3
        )
        
        return KinematicSignal(
            user_id=user_id,
            session_id=session_id,
            positions=positions,
            total_distance=total_distance,
            duration_ms=duration_ms,
            avg_velocity=avg_velocity,
            max_velocity=max_velocity,
            velocity_variance=velocity_variance,
            directness_ratio=min(1.0, directness),
            x_flips=x_flips,
            y_flips=y_flips,
            decisiveness_score=decisiveness,
            conflict_indicator=conflict_indicator,
            page_url=raw_data.get("page_url"),
            element_id=raw_data.get("target_element"),
        )
    
    def _variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)


# =============================================================================
# SCROLL BEHAVIOR CAPTURE
# =============================================================================

class ScrollBehaviorCapture(BaseSignalCapture):
    """
    Capture scroll behavior for engagement analysis.
    
    Research basis:
    - Scroll depth correlates with content engagement (Huang & Mosier, 2012)
    - Scroll velocity indicates skimming vs reading (Lagun et al., 2014)
    - Reverse scrolling indicates re-processing (Kim et al., 2015)
    """
    
    async def capture(self, raw_data: Dict[str, Any]) -> Optional[ScrollBehaviorSignal]:
        """
        Process scroll events into engagement indicators.
        
        Expected raw_data format:
        {
            "user_id": str,
            "session_id": str,
            "events": [{"scroll_y": int, "timestamp_ms": int, "page_height": int}, ...],
            "page_url": str
        }
        """
        user_id = raw_data.get("user_id", "")
        session_id = raw_data.get("session_id", "")
        events = raw_data.get("events", [])
        
        if not events:
            return None
        
        # Calculate scroll metrics
        total_distance = 0
        max_depth = 0
        velocities = []
        pauses = []
        reverse_count = 0
        
        for i in range(1, len(events)):
            prev = events[i - 1]
            curr = events[i]
            
            dy = curr["scroll_y"] - prev["scroll_y"]
            dt = max(1, curr["timestamp_ms"] - prev["timestamp_ms"])
            
            # Reverse scroll (indicates re-reading)
            if dy < 0:
                reverse_count += 1
            
            total_distance += abs(dy)
            velocity = abs(dy) / dt * 1000  # pixels per second
            velocities.append(velocity)
            
            # Detect pauses (velocity near zero for extended time)
            if velocity < 50 and dt > self.config.pause_threshold_ms:
                pauses.append(dt)
            
            # Max depth
            page_height = curr.get("page_height", 1000)
            depth_percent = (curr["scroll_y"] / max(1, page_height)) * 100
            max_depth = max(max_depth, depth_percent)
        
        # Calculate derived metrics
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0
        velocity_changes = sum(
            1 for i in range(1, len(velocities))
            if abs(velocities[i] - velocities[i-1]) > 500
        )
        
        total_pause_duration = sum(pauses)
        avg_pause_duration = total_pause_duration / len(pauses) if pauses else 0
        
        # Calculate engagement scores
        # More pauses + lower velocity = higher deliberation
        deliberation_score = min(1.0, (
            (len(pauses) / max(1, len(events) / 10)) * 0.4 +
            (1 - min(1.0, avg_velocity / 2000)) * 0.3 +
            (reverse_count / max(1, len(events) / 20)) * 0.3
        ))
        
        # Depth engagement considers max depth and time spent
        depth_engagement = min(1.0, (max_depth / 100) * 0.6 + deliberation_score * 0.4)
        
        # Overall engagement
        engagement_score = (deliberation_score + depth_engagement) / 2
        
        return ScrollBehaviorSignal(
            user_id=user_id,
            session_id=session_id,
            total_scroll_distance=int(total_distance),
            max_depth_percent=min(100.0, max_depth),
            scroll_events=len(events),
            avg_scroll_velocity=avg_velocity,
            velocity_changes=velocity_changes,
            pause_count=len(pauses),
            total_pause_duration_ms=int(total_pause_duration),
            avg_pause_duration_ms=avg_pause_duration,
            reverse_scroll_count=reverse_count,
            engagement_score=engagement_score,
            depth_engagement=depth_engagement,
            deliberation_score=deliberation_score,
            page_url=raw_data.get("page_url"),
        )


# =============================================================================
# KEYSTROKE DYNAMICS CAPTURE
# =============================================================================

class KeystrokeDynamicsCapture(BaseSignalCapture):
    """
    Capture keystroke dynamics for personality and state inference.
    
    Research basis:
    - Keystroke timing correlates with Big Five (Segalin et al., 2017)
    - Typing patterns indicate emotional state (Epp et al., 2011)
    - Correction behavior relates to conscientiousness (Banerjee & Woodard, 2012)
    """
    
    async def capture(self, raw_data: Dict[str, Any]) -> Optional[KeystrokeSignal]:
        """
        Process keystroke events into psychological indicators.
        
        Expected raw_data format:
        {
            "user_id": str,
            "session_id": str,
            "keystrokes": [
                {"key": str, "press_time": int, "release_time": int}, ...
            ],
            "element_id": str
        }
        """
        user_id = raw_data.get("user_id", "")
        session_id = raw_data.get("session_id", "")
        keystrokes = raw_data.get("keystrokes", [])
        
        if not keystrokes or len(keystrokes) < 3:
            return None
        
        # Calculate timing metrics
        dwell_times = []
        flight_times = []
        interkey_latencies = []
        backspace_count = 0
        delete_count = 0
        pauses = []
        
        for i, ks in enumerate(keystrokes):
            # Dwell time (key held down)
            dwell = ks.get("release_time", 0) - ks.get("press_time", 0)
            if 0 < dwell < 2000:  # Filter outliers
                dwell_times.append(dwell)
            
            # Flight time and interkey latency
            if i > 0:
                prev = keystrokes[i - 1]
                flight = ks["press_time"] - prev.get("release_time", prev["press_time"])
                interkey = ks["press_time"] - prev["press_time"]
                
                if 0 < flight < 5000:
                    flight_times.append(flight)
                if 0 < interkey < 5000:
                    interkey_latencies.append(interkey)
                
                # Detect pauses
                if interkey > self.config.pause_threshold_ms:
                    pauses.append(interkey)
            
            # Correction keys
            key = ks.get("key", "").lower()
            if key == "backspace":
                backspace_count += 1
            elif key == "delete":
                delete_count += 1
        
        # Calculate averages
        avg_dwell = sum(dwell_times) / len(dwell_times) if dwell_times else 0
        avg_flight = sum(flight_times) / len(flight_times) if flight_times else 0
        avg_interkey = sum(interkey_latencies) / len(interkey_latencies) if interkey_latencies else 0
        
        # Variance
        dwell_variance = self._variance(dwell_times) if dwell_times else 0
        flight_variance = self._variance(flight_times) if flight_times else 0
        
        # Speed
        total_time = (keystrokes[-1]["press_time"] - keystrokes[0]["press_time"]) / 1000 / 60
        wpm = len(keystrokes) / max(0.01, total_time) / 5  # Rough WPM
        cpm = len(keystrokes) / max(0.01, total_time)
        
        # Correction rate
        total_keys = len(keystrokes)
        correction_rate = (backspace_count + delete_count) / max(1, total_keys)
        
        # Calculate psychological indicators
        # Higher dwell variance indicates inconsistent typing (could be distraction)
        # Higher correction rate could indicate conscientiousness or uncertainty
        deliberation_score = min(1.0, (
            (avg_interkey / 500) * 0.3 +
            (len(pauses) / max(1, total_keys / 10)) * 0.4 +
            correction_rate * 0.3
        ))
        
        # Confidence: consistent timing + few corrections = higher confidence
        confidence_score = 1 - min(1.0, (
            (dwell_variance / 10000) * 0.4 +
            (flight_variance / 50000) * 0.3 +
            correction_rate * 0.3
        ))
        
        # Emotional arousal: high speed + low dwell = higher arousal
        arousal = min(1.0, (wpm / 80) * 0.5 + (1 - avg_dwell / 200) * 0.5)
        
        return KeystrokeSignal(
            user_id=user_id,
            session_id=session_id,
            avg_dwell_time=avg_dwell,
            avg_flight_time=avg_flight,
            avg_interkey_latency=avg_interkey,
            dwell_variance=dwell_variance,
            flight_variance=flight_variance,
            typing_speed_cpm=cpm,
            words_per_minute=wpm,
            backspace_count=backspace_count,
            delete_count=delete_count,
            correction_rate=correction_rate,
            pause_count=len(pauses),
            avg_pause_duration_ms=sum(pauses) / len(pauses) if pauses else 0,
            deliberation_score=deliberation_score,
            confidence_score=confidence_score,
            emotional_arousal=arousal,
            element_id=raw_data.get("element_id"),
        )
    
    def _variance(self, values: List[float]) -> float:
        """Calculate variance."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)


# =============================================================================
# RESPONSE LATENCY CAPTURE
# =============================================================================

class ResponseLatencyCapture(BaseSignalCapture):
    """
    Capture response latencies for attitude accessibility inference.
    
    Research basis:
    - Response time reflects attitude strength (Fazio, 1990)
    - Faster responses indicate stronger attitudes (Bassili, 1996)
    - Latency asymmetry reveals implicit biases (Greenwald et al., 1998)
    """
    
    def __init__(self, config: SignalCaptureConfig = None):
        super().__init__(config)
        # User baselines for normalization
        self._user_baselines: Dict[str, Dict[str, float]] = {}
    
    async def capture(self, raw_data: Dict[str, Any]) -> Optional[TemporalSignal]:
        """
        Process response timing into attitude indicators.
        
        Expected raw_data format:
        {
            "user_id": str,
            "session_id": str,
            "stimulus_shown_ms": int,
            "response_ms": int,
            "stimulus_type": str,
            "response_type": str
        }
        """
        user_id = raw_data.get("user_id", "")
        session_id = raw_data.get("session_id", "")
        
        stimulus_time = raw_data.get("stimulus_shown_ms", 0)
        response_time = raw_data.get("response_ms", 0)
        
        latency = response_time - stimulus_time
        if latency <= 0 or latency > 30000:  # Invalid or too long
            return None
        
        # Get or create user baseline
        baseline = self._get_baseline(user_id)
        
        # Normalize against baseline
        mean = baseline.get("mean", 1000)
        std = baseline.get("std", 500)
        
        z_score = (latency - mean) / max(1, std)
        percentile = self._z_to_percentile(z_score)
        
        # Update baseline
        self._update_baseline(user_id, latency)
        
        # Calculate attitude accessibility
        # Faster responses = more accessible attitudes
        accessibility = 1 - min(1.0, latency / 3000)
        
        return TemporalSignal(
            user_id=user_id,
            session_id=session_id,
            response_latency_ms=latency,
            stimulus_type=raw_data.get("stimulus_type", ""),
            response_type=raw_data.get("response_type", ""),
            latency_percentile=percentile,
            deviation_from_baseline=z_score,
            attitude_accessibility=accessibility,
        )
    
    def _get_baseline(self, user_id: str) -> Dict[str, float]:
        """Get user's response time baseline."""
        return self._user_baselines.get(user_id, {"mean": 1000, "std": 500, "n": 0})
    
    def _update_baseline(self, user_id: str, new_value: float) -> None:
        """Update user's running baseline using Welford's algorithm."""
        if user_id not in self._user_baselines:
            self._user_baselines[user_id] = {"mean": new_value, "std": 500, "n": 1, "m2": 0}
            return
        
        baseline = self._user_baselines[user_id]
        n = baseline["n"] + 1
        delta = new_value - baseline["mean"]
        mean = baseline["mean"] + delta / n
        m2 = baseline.get("m2", 0) + delta * (new_value - mean)
        std = math.sqrt(m2 / n) if n > 1 else 500
        
        self._user_baselines[user_id] = {"mean": mean, "std": std, "n": n, "m2": m2}
    
    def _z_to_percentile(self, z: float) -> float:
        """Convert z-score to percentile using approximation."""
        # Standard normal CDF approximation
        t = 1 / (1 + 0.2316419 * abs(z))
        d = 0.3989422804 * math.exp(-z * z / 2)
        p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
        return 1 - p if z > 0 else p


# =============================================================================
# COMPOSITE SIGNAL CAPTURE
# =============================================================================

class NonconsciousSignalCapture:
    """
    Unified capture system for all nonconscious signals.
    
    Coordinates multiple capture streams and produces integrated signals.
    """
    
    def __init__(self, config: SignalCaptureConfig = None):
        self.config = config or SignalCaptureConfig()
        
        self.mouse_capture = MouseDynamicsCapture(self.config)
        self.scroll_capture = ScrollBehaviorCapture(self.config)
        self.keystroke_capture = KeystrokeDynamicsCapture(self.config)
        self.latency_capture = ResponseLatencyCapture(self.config)
    
    async def process_event(
        self,
        event_type: str,
        raw_data: Dict[str, Any],
    ) -> Optional[NonconsciousSignal]:
        """
        Process a raw event into the appropriate signal type.
        """
        capture_map = {
            "mouse": self.mouse_capture,
            "scroll": self.scroll_capture,
            "keystroke": self.keystroke_capture,
            "timing": self.latency_capture,
            "response": self.latency_capture,
        }
        
        capture = capture_map.get(event_type.lower())
        if not capture:
            logger.debug(f"Unknown event type: {event_type}")
            return None
        
        try:
            return await capture.capture(raw_data)
        except Exception as e:
            logger.error(f"Error capturing {event_type} signal: {e}")
            return None
    
    async def process_batch(
        self,
        events: List[Dict[str, Any]],
    ) -> List[NonconsciousSignal]:
        """
        Process a batch of events.
        """
        signals = []
        
        for event in events:
            event_type = event.get("type", "")
            signal = await self.process_event(event_type, event.get("data", {}))
            if signal:
                signals.append(signal)
        
        return signals
    
    async def detect_hesitation(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> Optional[HesitationSignal]:
        """
        Detect hesitation patterns from multiple signal sources.
        """
        contributing = []
        hesitation_count = 0
        total_duration = 0
        
        for signal in signals:
            if isinstance(signal, KinematicSignal):
                if signal.conflict_indicator > 0.5:
                    contributing.append(signal.signal_id)
                    hesitation_count += signal.x_flips
            
            elif isinstance(signal, KeystrokeSignal):
                if signal.deliberation_score > 0.6:
                    contributing.append(signal.signal_id)
                    hesitation_count += signal.pause_count
                    total_duration += int(signal.avg_pause_duration_ms * signal.pause_count)
            
            elif isinstance(signal, TemporalSignal):
                if signal.deviation_from_baseline > 1.5:  # 1.5 std above mean
                    contributing.append(signal.signal_id)
                    hesitation_count += 1
                    total_duration += signal.response_latency_ms
        
        if not contributing:
            return None
        
        # Calculate scores
        uncertainty = min(1.0, hesitation_count / 10)
        conflict = sum(
            1 for s in signals
            if isinstance(s, KinematicSignal) and s.conflict_indicator > 0.5
        ) / max(1, len([s for s in signals if isinstance(s, KinematicSignal)]))
        
        return HesitationSignal(
            user_id=user_id,
            session_id=session_id,
            source=SignalSource.TIMING,
            contributing_signals=contributing,
            hesitation_count=hesitation_count,
            total_hesitation_duration_ms=total_duration,
            uncertainty_score=uncertainty,
            conflict_score=conflict,
        )
