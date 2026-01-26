# =============================================================================
# ADAM Behavioral Analytics: Cognitive State Estimator
# Location: adam/behavioral_analytics/classifiers/cognitive_state_estimator.py
# =============================================================================

"""
COGNITIVE STATE ESTIMATOR

Estimates real-time cognitive state for message complexity matching.

Based on Cognitive Load Theory (Sweller) and circadian research.
Effect sizes: d = 0.5-0.8 for load-reducing interventions.

Core Principle (Elaboration Likelihood Model):
- High cognitive load → Peripheral route processing → Use heuristic cues
- Low cognitive load → Central route processing → Use strong arguments

Components:
1. Circadian load (time of day)
2. Session fatigue (vigilance decrement)
3. Behavioral indicators (typing speed, scroll patterns)
4. Chronotype matching (synchrony effect)

Reference: Petty & Cacioppo (1986); Yoon et al. (2007)
"""

from typing import Dict, Optional, Any, Tuple
from datetime import datetime, time
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.advertising_psychology import (
    CognitiveStateProfile,
    ChronotypeProfile,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CHRONOTYPE PATTERNS
# =============================================================================

# Based on Yoon et al. (2007); Martin & Marrington (2005)
CHRONOTYPE_PATTERNS = {
    "morning": {
        "peak_hours": [8, 9, 10, 11],
        "off_peak_hours": [18, 19, 20, 21, 22],
        "population_percentage": 0.25,
        "peak_strategy": "Use rational, evidence-based arguments",
        "off_peak_strategy": "Use emotional/peripheral appeals",
    },
    "evening": {
        "peak_hours": [18, 19, 20, 21, 22],
        "off_peak_hours": [6, 7, 8, 9, 10],
        "population_percentage": 0.25,
        "peak_strategy": "Use rational, evidence-based arguments",
        "off_peak_strategy": "Use emotional/peripheral appeals",
    },
    "neutral": {
        "peak_hours": [10, 11, 12, 13, 14, 15, 16, 17],
        "off_peak_hours": [4, 5, 6, 22, 23],
        "population_percentage": 0.50,
        "peak_strategy": "Either approach works",
        "off_peak_strategy": "Prefer simpler messaging",
    },
}

# Circadian cognitive performance pattern (population average)
# Based on Valdez et al., 2012; Schmidt et al., 2007
CIRCADIAN_LOAD_BY_HOUR = {
    0: 0.65,   # Late night - elevated load
    1: 0.70,
    2: 0.75,
    3: 0.80,
    4: 0.85,   # Pre-dawn trough
    5: 0.80,
    6: 0.70,
    7: 0.55,   # Morning rise
    8: 0.45,
    9: 0.35,
    10: 0.30,  # Late morning peak
    11: 0.28,
    12: 0.32,  # Slight post-lunch dip
    13: 0.38,
    14: 0.40,  # Post-lunch dip
    15: 0.35,
    16: 0.28,  # Afternoon peak
    17: 0.25,  # Peak performance
    18: 0.30,
    19: 0.35,
    20: 0.40,
    21: 0.50,
    22: 0.55,
    23: 0.60,
}


# =============================================================================
# ESTIMATION RESULTS
# =============================================================================

class CognitiveStateEstimation(BaseModel):
    """
    Result of cognitive state estimation.
    
    Provides cognitive load level and message complexity recommendations
    based on ELM (Elaboration Likelihood Model).
    """
    
    # Core estimates
    cognitive_load: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Current cognitive load (0=fresh, 1=depleted)")
    
    # Component contributions
    circadian_load: float = Field(default=0.5, ge=0.0, le=1.0)
    fatigue_load: float = Field(default=0.0, ge=0.0, le=1.0)
    behavioral_load: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Timing context
    hour_of_day: int = Field(default=12, ge=0, le=23)
    session_duration_minutes: float = Field(default=0.0, ge=0.0)
    is_at_cognitive_peak: bool = Field(default=False)
    
    # Chronotype info
    chronotype: str = Field(default="neutral")
    synchrony_status: str = Field(default="neutral",
        description="at_peak, off_peak, or neutral")
    
    # Recommendations
    recommended_complexity: str = Field(default="moderate",
        description="high, moderate, or low")
    processing_route: str = Field(default="mixed",
        description="central or peripheral (ELM)")
    
    # Message guidelines
    copy_length: str = Field(default="medium")
    argument_style: str = Field(default="balanced")
    recommended_elements: list = Field(default_factory=list)
    avoid_elements: list = Field(default_factory=list)
    
    # Confidence
    confidence: SignalConfidence = Field(default=SignalConfidence.MODERATE)
    
    # Timestamp
    estimated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_profile(self) -> CognitiveStateProfile:
        """Convert to CognitiveStateProfile model."""
        return CognitiveStateProfile(
            cognitive_load=self.cognitive_load,
            circadian_load=self.circadian_load,
            fatigue_multiplier=1.0 + self.fatigue_load * 0.5,
            behavioral_load=self.behavioral_load,
            recommended_complexity=self.recommended_complexity,
            processing_route=self.processing_route,
            copy_length=self.copy_length,
            argument_style=self.argument_style,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cognitive_load": self.cognitive_load,
            "circadian_load": self.circadian_load,
            "fatigue_load": self.fatigue_load,
            "behavioral_load": self.behavioral_load,
            "hour_of_day": self.hour_of_day,
            "session_duration_minutes": self.session_duration_minutes,
            "is_at_cognitive_peak": self.is_at_cognitive_peak,
            "chronotype": self.chronotype,
            "synchrony_status": self.synchrony_status,
            "recommended_complexity": self.recommended_complexity,
            "processing_route": self.processing_route,
            "copy_length": self.copy_length,
            "argument_style": self.argument_style,
            "recommended_elements": self.recommended_elements,
            "avoid_elements": self.avoid_elements,
            "confidence": self.confidence.value,
            "estimated_at": self.estimated_at.isoformat(),
        }


# =============================================================================
# COGNITIVE STATE ESTIMATOR
# =============================================================================

class CognitiveStateEstimator:
    """
    Estimates cognitive state for message complexity matching.
    
    Combines:
    1. Circadian patterns (population-level or chronotype-matched)
    2. Session fatigue (vigilance decrement over time)
    3. Behavioral signals (real-time indicators)
    
    Output: Recommendations for message complexity based on ELM
    - High load → Peripheral route → Simple messages, heuristic cues
    - Low load → Central route → Complex messages, strong arguments
    
    Usage:
        estimator = CognitiveStateEstimator()
        estimation = estimator.estimate(
            hour=14,
            session_duration_minutes=25.0,
            behavioral_signals={"typing_speed_decrease": True}
        )
        # estimation.processing_route = "peripheral"
        # estimation.recommended_complexity = "low"
    """
    
    def __init__(self):
        self._estimation_count = 0
    
    def estimate(
        self,
        hour: Optional[int] = None,
        session_duration_minutes: float = 0.0,
        chronotype: str = "neutral",
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> CognitiveStateEstimation:
        """
        Estimate current cognitive state.
        
        Args:
            hour: Hour of day (0-23). If None, uses current time.
            session_duration_minutes: Duration of current session
            chronotype: User chronotype ("morning", "evening", "neutral")
            behavioral_signals: Dict of behavioral indicators
            
        Returns:
            CognitiveStateEstimation with load level and recommendations
        """
        if hour is None:
            hour = datetime.now().hour
        
        # 1. Circadian component
        circadian_load = self._calculate_circadian_load(hour)
        
        # 2. Session fatigue component
        fatigue_load = self._calculate_fatigue_load(session_duration_minutes)
        
        # 3. Behavioral indicators
        behavioral_load = self._calculate_behavioral_load(behavioral_signals)
        
        # Combine components (weighted sum, capped at 1.0)
        fatigue_multiplier = 1.0 + fatigue_load * 0.3  # Up to 30% increase
        total_load = min(1.0, circadian_load * fatigue_multiplier + behavioral_load)
        
        # Synchrony effect (chronotype × time)
        synchrony_status, is_at_peak = self._check_synchrony(hour, chronotype)
        
        # Get recommendations
        recommendations = self._get_recommendations(
            total_load, 
            is_at_peak, 
            synchrony_status
        )
        
        estimation = CognitiveStateEstimation(
            cognitive_load=total_load,
            circadian_load=circadian_load,
            fatigue_load=fatigue_load,
            behavioral_load=behavioral_load,
            hour_of_day=hour,
            session_duration_minutes=session_duration_minutes,
            is_at_cognitive_peak=is_at_peak,
            chronotype=chronotype,
            synchrony_status=synchrony_status,
            **recommendations,
        )
        
        self._estimation_count += 1
        
        logger.debug(
            f"Cognitive state: load={total_load:.2f}, "
            f"route={recommendations['processing_route']}, "
            f"complexity={recommendations['recommended_complexity']}"
        )
        
        return estimation
    
    def estimate_from_timestamp(
        self,
        timestamp: datetime,
        session_start: Optional[datetime] = None,
        chronotype: str = "neutral",
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> CognitiveStateEstimation:
        """
        Estimate cognitive state from timestamp.
        
        Args:
            timestamp: Current timestamp
            session_start: When session started (for duration calculation)
            chronotype: User chronotype
            behavioral_signals: Behavioral indicators
            
        Returns:
            CognitiveStateEstimation
        """
        hour = timestamp.hour
        
        if session_start:
            duration = (timestamp - session_start).total_seconds() / 60.0
        else:
            duration = 0.0
        
        return self.estimate(
            hour=hour,
            session_duration_minutes=duration,
            chronotype=chronotype,
            behavioral_signals=behavioral_signals,
        )
    
    def infer_chronotype(
        self,
        activity_times: list[int],
        min_observations: int = 10,
    ) -> Tuple[str, float]:
        """
        Infer chronotype from activity patterns.
        
        Args:
            activity_times: List of hours (0-23) when user is most active
            min_observations: Minimum observations for reliable inference
            
        Returns:
            Tuple of (chronotype, confidence)
        """
        if len(activity_times) < min_observations:
            return "neutral", 0.3
        
        # Count activity in each period
        morning_count = sum(1 for h in activity_times if 6 <= h <= 11)
        evening_count = sum(1 for h in activity_times if 18 <= h <= 23)
        total = len(activity_times)
        
        morning_ratio = morning_count / total
        evening_ratio = evening_count / total
        
        if morning_ratio > 0.4 and morning_ratio > evening_ratio * 1.5:
            chronotype = "morning"
            confidence = min(0.8, 0.5 + morning_ratio)
        elif evening_ratio > 0.4 and evening_ratio > morning_ratio * 1.5:
            chronotype = "evening"
            confidence = min(0.8, 0.5 + evening_ratio)
        else:
            chronotype = "neutral"
            confidence = 0.6
        
        return chronotype, confidence
    
    def get_optimal_times(
        self,
        message_complexity: str,
        chronotype: str = "neutral",
    ) -> list[int]:
        """
        Get optimal hours for a message complexity level.
        
        Args:
            message_complexity: "high", "moderate", or "low"
            chronotype: User chronotype
            
        Returns:
            List of optimal hours (0-23)
        """
        pattern = CHRONOTYPE_PATTERNS.get(chronotype, CHRONOTYPE_PATTERNS["neutral"])
        
        if message_complexity == "high":
            # Need low cognitive load → peak hours
            return pattern["peak_hours"]
        elif message_complexity == "low":
            # Can handle high load → any time, prefer off-peak for emotional
            return pattern["off_peak_hours"]
        else:
            # Moderate → middle hours
            return [h for h in range(8, 21) 
                    if h not in pattern["off_peak_hours"]]
    
    def _calculate_circadian_load(self, hour: int) -> float:
        """
        Calculate circadian cognitive load component.
        
        Based on population-average circadian performance patterns.
        """
        return CIRCADIAN_LOAD_BY_HOUR.get(hour, 0.5)
    
    def _calculate_fatigue_load(self, session_duration_minutes: float) -> float:
        """
        Calculate session fatigue component.
        
        Performance drops 10-30% over 30-minute sessions (vigilance decrement).
        """
        if session_duration_minutes <= 0:
            return 0.0
        
        # Logarithmic fatigue curve
        # 0 min = 0%, 15 min = 10%, 30 min = 20%, 60 min = 35%
        import math
        fatigue = 0.1 * math.log(1 + session_duration_minutes / 10)
        return min(0.5, fatigue)  # Cap at 50%
    
    def _calculate_behavioral_load(
        self,
        signals: Optional[Dict[str, Any]],
    ) -> float:
        """
        Calculate behavioral load from real-time signals.
        
        Indicators:
        - Typing speed decrease → cognitive load
        - Scroll velocity increase → scanning, not reading
        - Tab switches → distraction
        - Backspace frequency → uncertainty
        """
        if not signals:
            return 0.0
        
        load = 0.0
        
        # Typing speed decrease (relative to baseline)
        if signals.get("typing_speed_decrease", False):
            load += 0.15
        
        # Scroll velocity increase (scanning behavior)
        if signals.get("scroll_velocity_increase", False):
            load += 0.10
        
        # High tab switches (distraction)
        if signals.get("tab_switches_high", False):
            load += 0.12
        
        # High backspace frequency (uncertainty/correction)
        if signals.get("backspace_frequency_high", False):
            load += 0.08
        
        # Error rate increase
        if signals.get("error_rate_increase", False):
            load += 0.10
        
        # Cursor hesitation
        if signals.get("cursor_hesitation_high", False):
            load += 0.05
        
        return min(0.4, load)  # Cap behavioral component
    
    def _check_synchrony(
        self,
        hour: int,
        chronotype: str,
    ) -> Tuple[str, bool]:
        """
        Check synchrony status (chronotype × time).
        
        Returns:
            Tuple of (synchrony_status, is_at_peak)
        """
        pattern = CHRONOTYPE_PATTERNS.get(chronotype, CHRONOTYPE_PATTERNS["neutral"])
        
        if hour in pattern["peak_hours"]:
            return "at_peak", True
        elif hour in pattern["off_peak_hours"]:
            return "off_peak", False
        else:
            return "neutral", False
    
    def _get_recommendations(
        self,
        load: float,
        is_at_peak: bool,
        synchrony_status: str,
    ) -> Dict[str, Any]:
        """
        Get message recommendations based on cognitive state.
        
        Uses ELM (Elaboration Likelihood Model):
        - Low load + at peak → Central route (strong arguments)
        - High load or off peak → Peripheral route (heuristic cues)
        """
        if load < 0.35 and is_at_peak:
            # Optimal: use central route
            return {
                "recommended_complexity": "high",
                "processing_route": "central",
                "copy_length": "detailed",
                "argument_style": "rational, evidence-based",
                "recommended_elements": [
                    "strong arguments",
                    "detailed specifications",
                    "comparative information",
                    "expert testimonials",
                    "data and statistics",
                ],
                "avoid_elements": [
                    "purely emotional appeals without substance",
                ],
                "confidence": SignalConfidence.HIGH,
            }
        elif load < 0.5:
            # Moderate: balanced approach
            return {
                "recommended_complexity": "moderate",
                "processing_route": "mixed",
                "copy_length": "medium",
                "argument_style": "balanced rational/emotional",
                "recommended_elements": [
                    "key benefits with supporting facts",
                    "social proof",
                    "clear value proposition",
                ],
                "avoid_elements": [
                    "overly complex arguments",
                    "dense information",
                ],
                "confidence": SignalConfidence.MODERATE,
            }
        else:
            # High load: use peripheral route
            return {
                "recommended_complexity": "low",
                "processing_route": "peripheral",
                "copy_length": "brief",
                "argument_style": "emotional, heuristic cues",
                "recommended_elements": [
                    "social proof",
                    "celebrity/influencer",
                    "attractive imagery",
                    "simple taglines",
                    "emotional appeals",
                    "scarcity cues",
                    "authority badges",
                ],
                "avoid_elements": [
                    "complex arguments",
                    "detailed specifications",
                    "comparative tables",
                    "long-form content",
                ],
                "confidence": SignalConfidence.HIGH if load > 0.65 else SignalConfidence.MODERATE,
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get estimator statistics."""
        return {
            "estimations_performed": self._estimation_count,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_estimator: Optional[CognitiveStateEstimator] = None


def get_cognitive_state_estimator() -> CognitiveStateEstimator:
    """Get singleton cognitive state estimator."""
    global _estimator
    if _estimator is None:
        _estimator = CognitiveStateEstimator()
    return _estimator
