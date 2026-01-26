# =============================================================================
# ADAM Behavioral Analytics: Regulatory Focus Detector
# Location: adam/behavioral_analytics/classifiers/regulatory_focus_detector.py
# =============================================================================

"""
REGULATORY FOCUS DETECTOR

Detects promotion vs prevention focus from language patterns and behavioral signals.

CRITICAL: This is one of the highest-impact targeting variables.
Effect size: OR = 2-6x CTR when ad frame matches regulatory focus.

Reference: Higgins (1997, 1998); Field experiments in search advertising

Regulatory Focus Theory (Higgins):
- Promotion Focus: Goals framed as hopes/aspirations, eager strategies,
  gains/non-gains outcomes, approach orientation
- Prevention Focus: Goals framed as duties/obligations, vigilant strategies,
  losses/non-losses outcomes, avoidance orientation

Message Frame Matching:
- Promotion Focus → Gain-framed messages ("Get X", "Achieve Y")
- Prevention Focus → Loss-avoidance messages ("Don't miss", "Protect from")
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import re

from adam.behavioral_analytics.models.advertising_psychology import (
    RegulatoryFocusProfile,
    LinguisticFeatures,
    PROMOTION_FOCUS_MARKERS,
    PREVENTION_FOCUS_MARKERS,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EXTENDED MARKER LISTS
# =============================================================================

# Extended promotion focus markers (Higgins, 1997, 1998)
PROMOTION_MARKERS_EXTENDED = [
    # Advancement/Achievement
    'achieve', 'gain', 'advance', 'growth', 'accomplish', 'attain', 'earn',
    'win', 'succeed', 'thrive', 'excel', 'prosper', 'flourish', 'progress',
    
    # Aspirational
    'dream', 'aspire', 'ideal', 'hope', 'wish', 'desire', 'yearn', 'envision',
    'imagine', 'aspiration', 'vision', 'possibility', 'potential',
    
    # Opportunity
    'opportunity', 'maximize', 'optimize', 'improve', 'enhance', 'upgrade',
    'boost', 'elevate', 'amplify', 'expand', 'grow',
    
    # Eager strategies
    'eager', 'enthusiastic', 'excited', 'passionate', 'energized', 'inspired',
    'motivated', 'driven', 'ambitious', 'determined',
    
    # Positive outcomes
    'benefit', 'reward', 'bonus', 'prize', 'jackpot', 'treasure', 'fortune',
    
    # Action verbs (approach)
    'pursue', 'seek', 'chase', 'strive', 'aim', 'target', 'reach', 'grab',
]

# Extended prevention focus markers
PREVENTION_MARKERS_EXTENDED = [
    # Safety/Security
    'avoid', 'prevent', 'protect', 'secure', 'safe', 'reliable', 'stable',
    'guard', 'shield', 'defend', 'safeguard', 'insure', 'guarantee',
    
    # Obligation/Duty
    'ought', 'should', 'duty', 'obligation', 'responsibility', 'must',
    'required', 'necessary', 'essential', 'mandatory', 'expected',
    
    # Risk/Loss
    'risk', 'loss', 'danger', 'threat', 'harm', 'damage', 'problem', 'issue',
    'mistake', 'error', 'failure', 'pitfall', 'trap', 'hazard',
    
    # Vigilant strategies
    'careful', 'cautious', 'vigilant', 'watchful', 'alert', 'wary',
    'prudent', 'conservative', 'measured', 'deliberate',
    
    # Prevention verbs
    'stop', 'block', 'eliminate', 'reduce', 'minimize', 'limit',
    'restrict', 'control', 'contain', 'mitigate',
    
    # Negative outcomes to avoid
    'worry', 'concern', 'anxiety', 'fear', 'stress', 'trouble',
]


# =============================================================================
# DETECTION RESULTS
# =============================================================================

class RegulatoryFocusDetection(BaseModel):
    """
    Result of regulatory focus detection.
    
    Includes focus type, strength, confidence, and ad strategy recommendations.
    """
    
    # Core detection
    focus_type: str = Field(default="neutral",
        description="promotion, prevention, or neutral")
    focus_strength: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Strength of focus (0.5 = neutral)")
    confidence: SignalConfidence = Field(default=SignalConfidence.LOW)
    
    # Raw counts
    promotion_marker_count: int = Field(default=0)
    prevention_marker_count: int = Field(default=0)
    total_focus_markers: int = Field(default=0)
    
    # Promotion vs prevention balance
    promotion_ratio: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Ratio of promotion markers to total focus markers")
    
    # Ad strategy recommendations
    recommended_frame: str = Field(default="neutral")
    recommended_language: List[str] = Field(default_factory=list)
    recommended_construal: str = Field(default="mixed")
    recommended_imagery: List[str] = Field(default_factory=list)
    
    # Message templates
    message_templates: List[str] = Field(default_factory=list)
    
    # Evidence
    detected_promotion_words: List[str] = Field(default_factory=list)
    detected_prevention_words: List[str] = Field(default_factory=list)
    
    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_profile(self) -> RegulatoryFocusProfile:
        """Convert to RegulatoryFocusProfile model."""
        return RegulatoryFocusProfile(
            focus_type=self.focus_type,
            focus_strength=self.focus_strength,
            confidence=self.confidence,
            promotion_marker_count=self.promotion_marker_count,
            prevention_marker_count=self.prevention_marker_count,
            recommended_frame=self.recommended_frame,
            recommended_language=self.recommended_language,
            recommended_construal=self.recommended_construal,
            recommended_imagery=self.recommended_imagery,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "focus_type": self.focus_type,
            "focus_strength": self.focus_strength,
            "confidence": self.confidence.value,
            "promotion_marker_count": self.promotion_marker_count,
            "prevention_marker_count": self.prevention_marker_count,
            "promotion_ratio": self.promotion_ratio,
            "recommended_frame": self.recommended_frame,
            "recommended_language": self.recommended_language,
            "recommended_construal": self.recommended_construal,
            "recommended_imagery": self.recommended_imagery,
            "message_templates": self.message_templates,
            "detected_at": self.detected_at.isoformat(),
        }


# =============================================================================
# REGULATORY FOCUS DETECTOR
# =============================================================================

class RegulatoryFocusDetector:
    """
    Detects regulatory focus from text and behavioral signals.
    
    HIGHEST-IMPACT: OR = 2-6x CTR when ad frame matches regulatory focus.
    
    Detection Methods:
    1. Language markers in text (reviews, search queries, messages)
    2. Behavioral signals (approach vs avoidance gestures)
    3. Product category inference (hedonic vs utilitarian)
    
    Usage:
        detector = RegulatoryFocusDetector()
        detection = detector.detect_from_text("I want to achieve my fitness goals")
        # detection.focus_type = "promotion"
        # detection.recommended_frame = "gain"
    """
    
    # Message frame templates
    PROMOTION_FRAME_TEMPLATES = [
        "Achieve {benefit} with {product}",
        "Advance your {goal} today",
        "Gain the {advantage} you deserve",
        "Reach your ideal {outcome}",
        "Maximize your {potential}",
        "Unlock {possibility} now",
        "Experience the {benefit}",
        "Transform your {area} with {product}",
    ]
    
    PREVENTION_FRAME_TEMPLATES = [
        "Protect your {asset} with {product}",
        "Don't risk {negative_outcome}",
        "Secure your {valuable} today",
        "Avoid {problem} with {solution}",
        "Guard against {threat}",
        "Ensure {safety} with {product}",
        "Prevent {issue} before it starts",
        "Keep your {asset} safe from {risk}",
    ]
    
    def __init__(self, use_extended_markers: bool = True):
        """
        Initialize detector.
        
        Args:
            use_extended_markers: Whether to use extended marker lists
        """
        if use_extended_markers:
            self._promotion_markers = set(PROMOTION_MARKERS_EXTENDED)
            self._prevention_markers = set(PREVENTION_MARKERS_EXTENDED)
        else:
            self._promotion_markers = set(PROMOTION_FOCUS_MARKERS)
            self._prevention_markers = set(PREVENTION_FOCUS_MARKERS)
        
        self._detection_count = 0
    
    def detect_from_text(
        self,
        text: str,
        min_markers_for_confidence: int = 5,
    ) -> RegulatoryFocusDetection:
        """
        Detect regulatory focus from text content.
        
        Args:
            text: Text to analyze (reviews, queries, messages)
            min_markers_for_confidence: Minimum markers for HIGH confidence
            
        Returns:
            RegulatoryFocusDetection with focus type and recommendations
        """
        if not text:
            return RegulatoryFocusDetection()
        
        # Tokenize and normalize
        words = self._tokenize(text)
        
        # Count markers
        promotion_words = [w for w in words if w in self._promotion_markers]
        prevention_words = [w for w in words if w in self._prevention_markers]
        
        promotion_count = len(promotion_words)
        prevention_count = len(prevention_words)
        total = promotion_count + prevention_count
        
        # Calculate ratio
        if total == 0:
            return RegulatoryFocusDetection(
                focus_type="neutral",
                focus_strength=0.5,
                confidence=SignalConfidence.LOW,
            )
        
        promotion_ratio = promotion_count / total
        
        # Determine focus type and strength
        focus_type, focus_strength = self._determine_focus(promotion_ratio, total)
        
        # Determine confidence
        confidence = self._determine_confidence(total, min_markers_for_confidence)
        
        # Get recommendations
        recommendations = self._get_recommendations(focus_type)
        
        # Build detection result
        detection = RegulatoryFocusDetection(
            focus_type=focus_type,
            focus_strength=focus_strength,
            confidence=confidence,
            promotion_marker_count=promotion_count,
            prevention_marker_count=prevention_count,
            total_focus_markers=total,
            promotion_ratio=promotion_ratio,
            detected_promotion_words=list(set(promotion_words)),
            detected_prevention_words=list(set(prevention_words)),
            **recommendations,
        )
        
        self._detection_count += 1
        
        logger.debug(
            f"Detected regulatory focus: {focus_type} "
            f"(strength={focus_strength:.2f}, confidence={confidence.value})"
        )
        
        return detection
    
    def detect_from_aggregated_text(
        self,
        texts: List[str],
        weights: Optional[List[float]] = None,
    ) -> RegulatoryFocusDetection:
        """
        Detect regulatory focus from multiple text sources.
        
        More reliable than single text analysis. Use for aggregating
        multiple reviews, queries, or messages from a user.
        
        Args:
            texts: List of text samples
            weights: Optional weights for each text (e.g., recency)
            
        Returns:
            Aggregated RegulatoryFocusDetection
        """
        if not texts:
            return RegulatoryFocusDetection()
        
        if weights is None:
            weights = [1.0] * len(texts)
        
        total_promotion = 0
        total_prevention = 0
        all_promotion_words = []
        all_prevention_words = []
        
        for text, weight in zip(texts, weights):
            words = self._tokenize(text)
            
            promotion_words = [w for w in words if w in self._promotion_markers]
            prevention_words = [w for w in words if w in self._prevention_markers]
            
            total_promotion += len(promotion_words) * weight
            total_prevention += len(prevention_words) * weight
            
            all_promotion_words.extend(promotion_words)
            all_prevention_words.extend(prevention_words)
        
        total = total_promotion + total_prevention
        
        if total == 0:
            return RegulatoryFocusDetection()
        
        promotion_ratio = total_promotion / total
        focus_type, focus_strength = self._determine_focus(promotion_ratio, int(total))
        
        # Higher confidence with more texts
        min_for_high = 3 if len(texts) >= 5 else 5
        confidence = self._determine_confidence(int(total), min_for_high)
        
        recommendations = self._get_recommendations(focus_type)
        
        return RegulatoryFocusDetection(
            focus_type=focus_type,
            focus_strength=focus_strength,
            confidence=confidence,
            promotion_marker_count=int(total_promotion),
            prevention_marker_count=int(total_prevention),
            total_focus_markers=int(total),
            promotion_ratio=promotion_ratio,
            detected_promotion_words=list(set(all_promotion_words)),
            detected_prevention_words=list(set(all_prevention_words)),
            **recommendations,
        )
    
    def detect_from_behavioral_signals(
        self,
        right_swipe_ratio: float = 0.5,
        approach_gestures: int = 0,
        avoidance_gestures: int = 0,
        urgency_response_speed: Optional[float] = None,
    ) -> RegulatoryFocusDetection:
        """
        Detect regulatory focus from behavioral signals.
        
        Based on embodied cognition research:
        - Right/toward movements → approach → promotion
        - Left/away movements → avoidance → prevention
        
        Args:
            right_swipe_ratio: Ratio of right swipes to total (0-1)
            approach_gestures: Count of approach-oriented gestures
            avoidance_gestures: Count of avoidance-oriented gestures
            urgency_response_speed: Response time to urgency cues (ms)
            
        Returns:
            RegulatoryFocusDetection
        """
        # Calculate approach-avoidance balance
        total_gestures = approach_gestures + avoidance_gestures
        
        if total_gestures == 0 and right_swipe_ratio == 0.5:
            return RegulatoryFocusDetection(
                confidence=SignalConfidence.LOW,
            )
        
        # Weight signals
        swipe_weight = 0.4
        gesture_weight = 0.4
        urgency_weight = 0.2
        
        promotion_score = right_swipe_ratio * swipe_weight
        
        if total_gestures > 0:
            gesture_ratio = approach_gestures / total_gestures
            promotion_score += gesture_ratio * gesture_weight
        else:
            promotion_score += 0.5 * gesture_weight
        
        # Fast urgency response → prevention (scarcity sensitivity)
        if urgency_response_speed is not None:
            # Normalize: <500ms = high prevention, >2000ms = low prevention
            urgency_factor = max(0, min(1, (2000 - urgency_response_speed) / 1500))
            prevention_boost = urgency_factor * urgency_weight
            promotion_score -= prevention_boost - (urgency_weight / 2)
        else:
            promotion_score += 0.5 * urgency_weight
        
        # Normalize to 0-1
        promotion_score = max(0, min(1, promotion_score))
        
        focus_type, focus_strength = self._determine_focus(promotion_score, 10)
        
        confidence = SignalConfidence.MODERATE if total_gestures >= 5 else SignalConfidence.LOW
        
        recommendations = self._get_recommendations(focus_type)
        
        return RegulatoryFocusDetection(
            focus_type=focus_type,
            focus_strength=focus_strength,
            confidence=confidence,
            promotion_ratio=promotion_score,
            **recommendations,
        )
    
    def detect_combined(
        self,
        text: Optional[str] = None,
        texts: Optional[List[str]] = None,
        behavioral_signals: Optional[Dict[str, Any]] = None,
        text_weight: float = 0.6,
        behavioral_weight: float = 0.4,
    ) -> RegulatoryFocusDetection:
        """
        Combine text and behavioral signals for robust detection.
        
        Args:
            text: Single text sample
            texts: Multiple text samples
            behavioral_signals: Dict with behavioral signal values
            text_weight: Weight for text-based detection (0-1)
            behavioral_weight: Weight for behavioral detection (0-1)
            
        Returns:
            Combined RegulatoryFocusDetection
        """
        text_detection = None
        behavioral_detection = None
        
        # Text-based detection
        if texts:
            text_detection = self.detect_from_aggregated_text(texts)
        elif text:
            text_detection = self.detect_from_text(text)
        
        # Behavioral detection
        if behavioral_signals:
            behavioral_detection = self.detect_from_behavioral_signals(
                right_swipe_ratio=behavioral_signals.get('right_swipe_ratio', 0.5),
                approach_gestures=behavioral_signals.get('approach_gestures', 0),
                avoidance_gestures=behavioral_signals.get('avoidance_gestures', 0),
                urgency_response_speed=behavioral_signals.get('urgency_response_speed'),
            )
        
        # Combine
        if text_detection and behavioral_detection:
            # Weighted average of promotion ratios
            combined_ratio = (
                text_detection.promotion_ratio * text_weight +
                behavioral_detection.promotion_ratio * behavioral_weight
            )
            
            total_markers = text_detection.total_focus_markers
            focus_type, focus_strength = self._determine_focus(combined_ratio, total_markers)
            
            # Higher confidence for combined
            confidence = SignalConfidence.HIGH if (
                text_detection.confidence != SignalConfidence.LOW and
                behavioral_detection.confidence != SignalConfidence.LOW
            ) else SignalConfidence.MODERATE
            
            recommendations = self._get_recommendations(focus_type)
            
            return RegulatoryFocusDetection(
                focus_type=focus_type,
                focus_strength=focus_strength,
                confidence=confidence,
                promotion_marker_count=text_detection.promotion_marker_count,
                prevention_marker_count=text_detection.prevention_marker_count,
                total_focus_markers=total_markers,
                promotion_ratio=combined_ratio,
                detected_promotion_words=text_detection.detected_promotion_words,
                detected_prevention_words=text_detection.detected_prevention_words,
                **recommendations,
            )
        elif text_detection:
            return text_detection
        elif behavioral_detection:
            return behavioral_detection
        else:
            return RegulatoryFocusDetection()
    
    def get_message_templates(
        self,
        focus_type: str,
        product: str = "product",
        benefit: str = "benefit",
    ) -> List[str]:
        """
        Get message templates matched to regulatory focus.
        
        Args:
            focus_type: "promotion" or "prevention"
            product: Product name for template substitution
            benefit: Benefit for template substitution
            
        Returns:
            List of message template strings
        """
        if focus_type == "promotion":
            templates = self.PROMOTION_FRAME_TEMPLATES
        elif focus_type == "prevention":
            templates = self.PREVENTION_FRAME_TEMPLATES
        else:
            return []
        
        # Simple substitution for examples
        return [
            t.format(
                product=product,
                benefit=benefit,
                goal="goals",
                advantage="advantage",
                outcome="outcome",
                potential="potential",
                possibility="possibilities",
                area="life",
                asset="investment",
                negative_outcome="losing out",
                valuable="future",
                problem="issues",
                solution=product,
                threat="risks",
                safety="security",
                issue="problems",
                risk="uncertainty",
            )
            for t in templates[:4]  # Return top 4
        ]
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and normalize text."""
        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)
        return words
    
    def _determine_focus(
        self,
        promotion_ratio: float,
        total_markers: int,
    ) -> Tuple[str, float]:
        """
        Determine focus type and strength from promotion ratio.
        
        Args:
            promotion_ratio: Ratio of promotion to total markers
            total_markers: Total number of focus markers found
            
        Returns:
            Tuple of (focus_type, focus_strength)
        """
        # Require clear signal
        if promotion_ratio > 0.6:
            focus_type = "promotion"
            # Strength increases with ratio
            focus_strength = 0.5 + (promotion_ratio - 0.5) * 0.8
        elif promotion_ratio < 0.4:
            focus_type = "prevention"
            # Strength increases as ratio decreases
            focus_strength = 0.5 + (0.5 - promotion_ratio) * 0.8
        else:
            focus_type = "neutral"
            focus_strength = 0.5
        
        # Boost strength with more markers (more confident in direction)
        if total_markers >= 10:
            focus_strength = min(1.0, focus_strength * 1.1)
        
        return focus_type, min(1.0, focus_strength)
    
    def _determine_confidence(
        self,
        total_markers: int,
        min_for_high: int = 5,
    ) -> SignalConfidence:
        """Determine confidence based on marker count."""
        if total_markers >= min_for_high:
            return SignalConfidence.HIGH
        elif total_markers >= 3:
            return SignalConfidence.MODERATE
        else:
            return SignalConfidence.LOW
    
    def _get_recommendations(self, focus_type: str) -> Dict[str, Any]:
        """Get ad strategy recommendations for focus type."""
        if focus_type == "promotion":
            return {
                "recommended_frame": "gain",
                "recommended_language": [
                    "achieve", "gain", "advance", "ideal",
                    "opportunity", "maximize", "unlock", "experience"
                ],
                "recommended_construal": "abstract",
                "recommended_imagery": [
                    "aspirational", "success", "achievement",
                    "growth", "possibilities", "transformation"
                ],
                "message_templates": self.PROMOTION_FRAME_TEMPLATES[:4],
            }
        elif focus_type == "prevention":
            return {
                "recommended_frame": "loss_avoidance",
                "recommended_language": [
                    "protect", "secure", "safe", "reliable",
                    "guard", "prevent", "ensure", "guarantee"
                ],
                "recommended_construal": "concrete",
                "recommended_imagery": [
                    "security", "stability", "protection",
                    "safety", "reliability", "trust"
                ],
                "message_templates": self.PREVENTION_FRAME_TEMPLATES[:4],
            }
        else:
            return {
                "recommended_frame": "neutral",
                "recommended_language": [],
                "recommended_construal": "mixed",
                "recommended_imagery": [],
                "message_templates": [],
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "detections_performed": self._detection_count,
            "promotion_markers_count": len(self._promotion_markers),
            "prevention_markers_count": len(self._prevention_markers),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_detector: Optional[RegulatoryFocusDetector] = None


def get_regulatory_focus_detector() -> RegulatoryFocusDetector:
    """Get singleton regulatory focus detector."""
    global _detector
    if _detector is None:
        _detector = RegulatoryFocusDetector()
    return _detector
