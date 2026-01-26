# =============================================================================
# ADAM Behavioral Analytics: Approach-Avoidance Detector
# Location: adam/behavioral_analytics/classifiers/approach_avoidance_detector.py
# =============================================================================

"""
APPROACH-AVOIDANCE DETECTOR

Detects BIS/BAS (Behavioral Inhibition/Activation System) orientation.

More fundamental than regulatory focus - reflects biologically-based
temperament rather than situational state.

Reference: Gray's Reinforcement Sensitivity Theory
BIS correlates with Neuroticism (r ≈ 0.4-0.6)
BAS correlates with Extraversion (r ≈ 0.3-0.5)

Key Insight: BIS-dominant individuals will NOT respond to excitement appeals;
BAS-dominant individuals will IGNORE fear appeals.

Ad Strategy:
- High BAS → excitement, achievement, gain, novelty appeals
- High BIS → security, protection, risk reduction, safety appeals
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.advertising_psychology import (
    ApproachAvoidanceProfile,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# BIS/BAS INDICATORS
# =============================================================================

# Language markers for BAS (approach motivation)
BAS_LANGUAGE_MARKERS = [
    # Positive emotion
    'excited', 'thrilled', 'amazing', 'awesome', 'love', 'great', 'fantastic',
    'wonderful', 'incredible', 'excellent', 'brilliant', 'perfect',
    
    # Achievement
    'achieve', 'win', 'success', 'accomplish', 'earn', 'gain', 'advance',
    'progress', 'improve', 'grow', 'excel', 'thrive',
    
    # Eagerness
    'eager', 'enthusiastic', 'passionate', 'motivated', 'driven', 'ambitious',
    'want', 'desire', 'pursue', 'seek', 'chase',
    
    # Novelty
    'new', 'discover', 'explore', 'adventure', 'exciting', 'fresh', 'innovative',
    
    # Reward sensitivity
    'reward', 'bonus', 'prize', 'benefit', 'opportunity', 'chance',
]

# Language markers for BIS (avoidance motivation)
BIS_LANGUAGE_MARKERS = [
    # Negative emotion
    'worried', 'anxious', 'concerned', 'afraid', 'scared', 'nervous', 'stressed',
    'uncertain', 'doubtful', 'hesitant', 'cautious',
    
    # Safety/Security
    'safe', 'secure', 'protect', 'guard', 'reliable', 'stable', 'dependable',
    'trust', 'careful', 'prudent',
    
    # Risk/Threat
    'risk', 'danger', 'threat', 'harm', 'loss', 'problem', 'issue',
    'avoid', 'prevent', 'stop', 'block', 'eliminate',
    
    # Obligation
    'should', 'must', 'need', 'have to', 'ought', 'required', 'necessary',
    
    # Inhibition
    'but', 'however', 'although', 'unless', 'except', 'might', 'maybe',
    'perhaps', 'possibly', 'probably',
]


# =============================================================================
# DETECTION RESULT
# =============================================================================

class ApproachAvoidanceDetection(BaseModel):
    """
    Result of approach-avoidance detection.
    
    Provides BIS/BAS scores and ad strategy recommendations.
    """
    
    # Core scores (0-1)
    bas_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Behavioral Activation System (approach)")
    bis_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Behavioral Inhibition System (avoidance)")
    
    # Derived
    dominant_system: str = Field(default="balanced",
        description="BAS, BIS, or balanced")
    motivation_type: str = Field(default="balanced",
        description="approach_dominant, avoidance_dominant, or balanced")
    
    # Evidence
    bas_markers_found: List[str] = Field(default_factory=list)
    bis_markers_found: List[str] = Field(default_factory=list)
    behavioral_signals_used: List[str] = Field(default_factory=list)
    
    # Ad strategy recommendations
    recommended_appeals: List[str] = Field(default_factory=list)
    recommended_framing: str = Field(default="")
    avoid_appeals: List[str] = Field(default_factory=list)
    recommended_imagery: List[str] = Field(default_factory=list)
    
    # Confidence
    confidence: SignalConfidence = Field(default=SignalConfidence.LOW)
    
    # Timestamp
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_profile(self) -> ApproachAvoidanceProfile:
        """Convert to ApproachAvoidanceProfile model."""
        return ApproachAvoidanceProfile(
            bas_score=self.bas_score,
            bis_score=self.bis_score,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bas_score": self.bas_score,
            "bis_score": self.bis_score,
            "dominant_system": self.dominant_system,
            "motivation_type": self.motivation_type,
            "bas_markers_found": self.bas_markers_found,
            "bis_markers_found": self.bis_markers_found,
            "recommended_appeals": self.recommended_appeals,
            "recommended_framing": self.recommended_framing,
            "avoid_appeals": self.avoid_appeals,
            "recommended_imagery": self.recommended_imagery,
            "confidence": self.confidence.value,
            "detected_at": self.detected_at.isoformat(),
        }


# =============================================================================
# APPROACH-AVOIDANCE DETECTOR
# =============================================================================

class ApproachAvoidanceDetector:
    """
    Detects BIS/BAS orientation from language and behavioral signals.
    
    BIS/BAS is more fundamental than regulatory focus - it's biologically-based
    temperament rather than situational state.
    
    Usage:
        detector = ApproachAvoidanceDetector()
        detection = detector.detect_from_text("I'm excited to try new things!")
        # detection.dominant_system = "BAS"
        # detection.recommended_appeals = ["excitement", "achievement", "novelty"]
    """
    
    def __init__(self):
        self._bas_markers = set(BAS_LANGUAGE_MARKERS)
        self._bis_markers = set(BIS_LANGUAGE_MARKERS)
        self._detection_count = 0
    
    def detect_from_text(
        self,
        text: str,
        min_markers_for_confidence: int = 5,
    ) -> ApproachAvoidanceDetection:
        """
        Detect BIS/BAS from text content.
        
        Args:
            text: Text to analyze
            min_markers_for_confidence: Minimum markers for HIGH confidence
            
        Returns:
            ApproachAvoidanceDetection with scores and recommendations
        """
        if not text:
            return ApproachAvoidanceDetection()
        
        # Tokenize
        import re
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Count markers
        bas_found = [w for w in words if w in self._bas_markers]
        bis_found = [w for w in words if w in self._bis_markers]
        
        bas_count = len(bas_found)
        bis_count = len(bis_found)
        total = bas_count + bis_count
        
        if total == 0:
            return ApproachAvoidanceDetection()
        
        # Calculate scores using research-validated approach
        # Reference: Gray (1987), Carver & White (1994) BIS/BAS scales
        # Use symmetric transformation centered at 0.5
        bas_ratio = bas_count / max(1, total)
        bis_ratio = bis_count / max(1, total)
        
        # Transform ratios to scores using logistic-like scaling
        # This provides symmetric treatment and bounded output [0,1]
        # Rationale: Effect sizes in BIS/BAS research typically d=0.3-0.5
        # We use 0.8 multiplier for conservative estimation
        bas_score = 0.5 + (bas_ratio - 0.5) * 0.8
        bis_score = 0.5 + (bis_ratio - 0.5) * 0.8
        
        # Ensure bounds
        bas_score = max(0.0, min(1.0, bas_score))
        bis_score = max(0.0, min(1.0, bis_score))
        
        # Determine dominance
        dominant_system, motivation_type = self._determine_dominance(bas_score, bis_score)
        
        # Get recommendations
        recommendations = self._get_recommendations(dominant_system)
        
        # Determine confidence
        confidence = SignalConfidence.HIGH if total >= min_markers_for_confidence else (
            SignalConfidence.MODERATE if total >= 3 else SignalConfidence.LOW
        )
        
        detection = ApproachAvoidanceDetection(
            bas_score=bas_score,
            bis_score=bis_score,
            dominant_system=dominant_system,
            motivation_type=motivation_type,
            bas_markers_found=list(set(bas_found)),
            bis_markers_found=list(set(bis_found)),
            confidence=confidence,
            **recommendations,
        )
        
        self._detection_count += 1
        
        logger.debug(
            f"Approach-avoidance detection: BAS={bas_score:.2f}, BIS={bis_score:.2f}, "
            f"dominant={dominant_system}"
        )
        
        return detection
    
    def detect_from_behavioral_signals(
        self,
        right_swipe_ratio: float = 0.5,
        approach_gestures: int = 0,
        avoidance_gestures: int = 0,
        response_to_urgency: Optional[float] = None,
        risk_taking_score: Optional[float] = None,
    ) -> ApproachAvoidanceDetection:
        """
        Detect BIS/BAS from behavioral signals.
        
        Based on embodied cognition:
        - Right/toward movements → approach → BAS
        - Left/away movements → avoidance → BIS
        - Fast urgency response → BIS (threat sensitivity)
        
        Args:
            right_swipe_ratio: Ratio of right swipes (0-1)
            approach_gestures: Count of approach gestures
            avoidance_gestures: Count of avoidance gestures
            response_to_urgency: Response time to urgency cues (ms)
            risk_taking_score: Risk-taking behavior score (0-1)
            
        Returns:
            ApproachAvoidanceDetection
        """
        # Start with neutral
        bas_score = 0.5
        bis_score = 0.5
        signals_used = []
        
        # Swipe direction
        if right_swipe_ratio != 0.5:
            bas_score += (right_swipe_ratio - 0.5) * 0.4
            bis_score -= (right_swipe_ratio - 0.5) * 0.4
            signals_used.append("swipe_direction")
        
        # Gesture counts
        total_gestures = approach_gestures + avoidance_gestures
        if total_gestures > 0:
            gesture_ratio = approach_gestures / total_gestures
            bas_score += (gesture_ratio - 0.5) * 0.3
            bis_score -= (gesture_ratio - 0.5) * 0.3
            signals_used.append("gesture_pattern")
        
        # Urgency response (fast = high BIS, threat sensitivity)
        if response_to_urgency is not None:
            # Normalize: <500ms = high BIS, >2000ms = low BIS
            urgency_factor = max(0, min(1, (2000 - response_to_urgency) / 1500))
            bis_score += (urgency_factor - 0.5) * 0.2
            signals_used.append("urgency_response")
        
        # Risk taking
        if risk_taking_score is not None:
            bas_score += (risk_taking_score - 0.5) * 0.3
            bis_score -= (risk_taking_score - 0.5) * 0.3
            signals_used.append("risk_taking")
        
        # Clamp scores
        bas_score = max(0.0, min(1.0, bas_score))
        bis_score = max(0.0, min(1.0, bis_score))
        
        dominant_system, motivation_type = self._determine_dominance(bas_score, bis_score)
        recommendations = self._get_recommendations(dominant_system)
        
        confidence = SignalConfidence.MODERATE if len(signals_used) >= 2 else SignalConfidence.LOW
        
        return ApproachAvoidanceDetection(
            bas_score=bas_score,
            bis_score=bis_score,
            dominant_system=dominant_system,
            motivation_type=motivation_type,
            behavioral_signals_used=signals_used,
            confidence=confidence,
            **recommendations,
        )
    
    def detect_combined(
        self,
        text: Optional[str] = None,
        texts: Optional[List[str]] = None,
        behavioral_signals: Optional[Dict[str, Any]] = None,
        text_weight: float = 0.5,
        behavioral_weight: float = 0.5,
    ) -> ApproachAvoidanceDetection:
        """
        Combine text and behavioral signals for robust detection.
        
        Args:
            text: Single text sample
            texts: Multiple text samples
            behavioral_signals: Dict with behavioral signal values
            text_weight: Weight for text detection
            behavioral_weight: Weight for behavioral detection
            
        Returns:
            Combined ApproachAvoidanceDetection
        """
        text_detection = None
        behavioral_detection = None
        
        # Text detection
        if texts:
            combined_text = " ".join(texts)
            text_detection = self.detect_from_text(combined_text)
        elif text:
            text_detection = self.detect_from_text(text)
        
        # Behavioral detection
        if behavioral_signals:
            behavioral_detection = self.detect_from_behavioral_signals(
                right_swipe_ratio=behavioral_signals.get('right_swipe_ratio', 0.5),
                approach_gestures=behavioral_signals.get('approach_gestures', 0),
                avoidance_gestures=behavioral_signals.get('avoidance_gestures', 0),
                response_to_urgency=behavioral_signals.get('urgency_response_speed'),
                risk_taking_score=behavioral_signals.get('risk_taking_score'),
            )
        
        # Combine
        if text_detection and behavioral_detection:
            bas_score = (
                text_detection.bas_score * text_weight +
                behavioral_detection.bas_score * behavioral_weight
            )
            bis_score = (
                text_detection.bis_score * text_weight +
                behavioral_detection.bis_score * behavioral_weight
            )
            
            dominant_system, motivation_type = self._determine_dominance(bas_score, bis_score)
            recommendations = self._get_recommendations(dominant_system)
            
            confidence = SignalConfidence.HIGH if (
                text_detection.confidence != SignalConfidence.LOW and
                behavioral_detection.confidence != SignalConfidence.LOW
            ) else SignalConfidence.MODERATE
            
            return ApproachAvoidanceDetection(
                bas_score=bas_score,
                bis_score=bis_score,
                dominant_system=dominant_system,
                motivation_type=motivation_type,
                bas_markers_found=text_detection.bas_markers_found,
                bis_markers_found=text_detection.bis_markers_found,
                behavioral_signals_used=behavioral_detection.behavioral_signals_used,
                confidence=confidence,
                **recommendations,
            )
        elif text_detection:
            return text_detection
        elif behavioral_detection:
            return behavioral_detection
        else:
            return ApproachAvoidanceDetection()
    
    def _determine_dominance(
        self,
        bas_score: float,
        bis_score: float,
    ) -> Tuple[str, str]:
        """Determine which system is dominant."""
        if bas_score > bis_score + 0.15:
            return "BAS", "approach_dominant"
        elif bis_score > bas_score + 0.15:
            return "BIS", "avoidance_dominant"
        else:
            return "balanced", "balanced"
    
    def _get_recommendations(self, dominant_system: str) -> Dict[str, Any]:
        """Get ad strategy recommendations for dominant system."""
        if dominant_system == "BAS":
            return {
                "recommended_appeals": [
                    "excitement", "achievement", "gain", "novelty",
                    "adventure", "opportunity", "success", "reward"
                ],
                "recommended_framing": "positive outcomes, rewards, opportunities",
                "avoid_appeals": [
                    "fear appeals (will be ignored)",
                    "loss framing (ineffective)",
                    "security messaging (boring)",
                ],
                "recommended_imagery": [
                    "action", "success", "winning", "celebration",
                    "new experiences", "growth"
                ],
            }
        elif dominant_system == "BIS":
            return {
                "recommended_appeals": [
                    "security", "protection", "risk_reduction", "safety",
                    "reliability", "stability", "trust", "peace_of_mind"
                ],
                "recommended_framing": "threat reduction, loss prevention, security",
                "avoid_appeals": [
                    "excitement appeals (increases anxiety)",
                    "risk-taking messaging (creates discomfort)",
                    "novelty emphasis (feels unsafe)",
                ],
                "recommended_imagery": [
                    "calm", "protection", "stability", "shields",
                    "families safe", "secure environments"
                ],
            }
        else:
            return {
                "recommended_appeals": [
                    "balanced approach works",
                    "can emphasize either based on product"
                ],
                "recommended_framing": "balanced positive and protective messaging",
                "avoid_appeals": [],
                "recommended_imagery": ["versatile imagery works"],
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "detections_performed": self._detection_count,
            "bas_markers_count": len(self._bas_markers),
            "bis_markers_count": len(self._bis_markers),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_detector: Optional[ApproachAvoidanceDetector] = None


def get_approach_avoidance_detector() -> ApproachAvoidanceDetector:
    """Get singleton approach-avoidance detector."""
    global _detector
    if _detector is None:
        _detector = ApproachAvoidanceDetector()
    return _detector
