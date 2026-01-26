# =============================================================================
# ADAM Behavioral Analytics: Evolutionary Motive Detector
# Location: adam/behavioral_analytics/classifiers/evolutionary_motive_detector.py
# =============================================================================

"""
EVOLUTIONARY MOTIVE DETECTOR

Applies evolutionary psychology to consumer behavior:
1. Life History Strategy - Fast (present) vs Slow (future) orientation
2. Costly Signaling - Consumption as fitness trait signaling
3. Mating Motivation - How activated mating goals affect consumption
4. Status Signaling - Luxury as resource/competence display

Key Insight: Consumers use products to signal fitness-relevant traits
more than fulfilling functional needs.

Reference: Miller (2009) Spent; Nelissen & Meijers (2011)
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.advertising_psychology import (
    EvolutionaryMotiveProfile,
    LifeHistoryStrategy,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SIGNALING TRAITS (Miller's "Central Six")
# =============================================================================

class SignalingTrait(str, Enum):
    """Fitness-relevant traits signaled through consumption."""
    INTELLIGENCE = "intelligence"
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    AGREEABLENESS = "agreeableness"
    STABILITY = "stability"  # Emotional stability
    EXTRAVERSION = "extraversion"


# Product categories → Traits signaled
PRODUCT_SIGNALING_MAP = {
    # Technology products signal intelligence
    "technology": [SignalingTrait.INTELLIGENCE, SignalingTrait.OPENNESS],
    "gadgets": [SignalingTrait.INTELLIGENCE, SignalingTrait.OPENNESS],
    "books": [SignalingTrait.INTELLIGENCE, SignalingTrait.OPENNESS],
    
    # Luxury signals resources/conscientiousness
    "luxury": [SignalingTrait.CONSCIENTIOUSNESS, SignalingTrait.STABILITY],
    "watches": [SignalingTrait.CONSCIENTIOUSNESS, SignalingTrait.STABILITY],
    "jewelry": [SignalingTrait.CONSCIENTIOUSNESS, SignalingTrait.STABILITY],
    
    # Sustainable/ethical signals agreeableness
    "organic": [SignalingTrait.AGREEABLENESS, SignalingTrait.OPENNESS],
    "sustainable": [SignalingTrait.AGREEABLENESS, SignalingTrait.OPENNESS],
    "ethical": [SignalingTrait.AGREEABLENESS, SignalingTrait.CONSCIENTIOUSNESS],
    "charity": [SignalingTrait.AGREEABLENESS],
    
    # Social/party products signal extraversion
    "fashion": [SignalingTrait.EXTRAVERSION, SignalingTrait.OPENNESS],
    "entertainment": [SignalingTrait.EXTRAVERSION, SignalingTrait.OPENNESS],
    "sports": [SignalingTrait.EXTRAVERSION, SignalingTrait.CONSCIENTIOUSNESS],
    
    # Fitness signals all positively
    "fitness": [SignalingTrait.CONSCIENTIOUSNESS, SignalingTrait.STABILITY, SignalingTrait.EXTRAVERSION],
}


# =============================================================================
# LIFE HISTORY LANGUAGE MARKERS
# =============================================================================

# Fast life history markers (present-focus, impulsivity)
FAST_LH_MARKERS = [
    'now', 'today', 'immediately', 'instant', 'quick', 'fast', 'hurry',
    'limited time', 'act now', 'don\'t wait', 'urgent', 'asap',
    'impulse', 'spontaneous', 'exciting', 'thrill', 'adventure',
    'yolo', 'treat yourself', 'deserve', 'indulge', 'splurge',
]

# Slow life history markers (future-focus, investment)
SLOW_LH_MARKERS = [
    'invest', 'investment', 'long-term', 'lasting', 'durable', 'quality',
    'future', 'planning', 'retirement', 'savings', 'compound', 'grow',
    'build', 'foundation', 'legacy', 'generations', 'sustainable',
    'research', 'compare', 'consider', 'evaluate', 'careful',
]


# =============================================================================
# DETECTION RESULT
# =============================================================================

class EvolutionaryMotiveDetection(BaseModel):
    """
    Result of evolutionary motive detection.
    
    Provides life history strategy, signaling analysis, and ad recommendations.
    """
    
    # Life History Strategy
    life_history_strategy: str = Field(default="mixed")
    fast_strategy_score: float = Field(default=0.5, ge=0.0, le=1.0)
    slow_strategy_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Temporal discounting
    temporal_discounting: float = Field(default=0.5, ge=0.0, le=1.0,
        description="High = prefers immediate, Low = prefers delayed")
    
    # Signaling analysis
    primary_signaling_traits: List[str] = Field(default_factory=list)
    signaling_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Mating motivation (if detectable)
    mating_motivation_activated: bool = Field(default=False)
    
    # Evidence
    fast_markers_found: List[str] = Field(default_factory=list)
    slow_markers_found: List[str] = Field(default_factory=list)
    
    # Recommendations
    recommended_framing: str = Field(default="")
    recommended_incentives: List[str] = Field(default_factory=list)
    recommended_copy_style: str = Field(default="")
    gender_specific_framing: Dict[str, str] = Field(default_factory=dict)
    
    # Confidence
    confidence: SignalConfidence = Field(default=SignalConfidence.LOW)
    
    # Timestamp
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_profile(self) -> EvolutionaryMotiveProfile:
        """Convert to EvolutionaryMotiveProfile model."""
        strategy = LifeHistoryStrategy.FAST if self.fast_strategy_score > self.slow_strategy_score + 0.2 else (
            LifeHistoryStrategy.SLOW if self.slow_strategy_score > self.fast_strategy_score + 0.2 else
            LifeHistoryStrategy.MIXED
        )
        return EvolutionaryMotiveProfile(
            life_history_strategy=strategy,
            temporal_discounting=self.temporal_discounting,
            primary_signaling_traits=self.primary_signaling_traits,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "life_history_strategy": self.life_history_strategy,
            "fast_strategy_score": self.fast_strategy_score,
            "slow_strategy_score": self.slow_strategy_score,
            "temporal_discounting": self.temporal_discounting,
            "primary_signaling_traits": self.primary_signaling_traits,
            "signaling_intensity": self.signaling_intensity,
            "mating_motivation_activated": self.mating_motivation_activated,
            "recommended_framing": self.recommended_framing,
            "recommended_incentives": self.recommended_incentives,
            "recommended_copy_style": self.recommended_copy_style,
            "confidence": self.confidence.value,
            "detected_at": self.detected_at.isoformat(),
        }


# =============================================================================
# EVOLUTIONARY MOTIVE DETECTOR
# =============================================================================

class EvolutionaryMotiveDetector:
    """
    Detects evolutionary motives from text and behavioral signals.
    
    Applies:
    - Life History Theory (fast vs slow strategies)
    - Costly Signaling Theory (consumption as fitness display)
    - Mating Motivation effects
    
    Usage:
        detector = EvolutionaryMotiveDetector()
        detection = detector.detect_from_text(
            "I want quality that will last for years"
        )
        # detection.life_history_strategy = "slow"
        # detection.recommended_framing = "investment, long-term value, quality"
    """
    
    def __init__(self):
        self._fast_markers = set(FAST_LH_MARKERS)
        self._slow_markers = set(SLOW_LH_MARKERS)
        self._detection_count = 0
    
    def detect_from_text(
        self,
        text: str,
        min_markers_for_confidence: int = 5,
    ) -> EvolutionaryMotiveDetection:
        """
        Detect life history strategy from text.
        
        Args:
            text: Text to analyze
            min_markers_for_confidence: Minimum markers for HIGH confidence
            
        Returns:
            EvolutionaryMotiveDetection with strategy and recommendations
        """
        if not text:
            return EvolutionaryMotiveDetection()
        
        text_lower = text.lower()
        
        # Find markers
        fast_found = [m for m in self._fast_markers if m in text_lower]
        slow_found = [m for m in self._slow_markers if m in text_lower]
        
        fast_count = len(fast_found)
        slow_count = len(slow_found)
        total = fast_count + slow_count
        
        if total == 0:
            return EvolutionaryMotiveDetection()
        
        # Calculate scores
        fast_ratio = fast_count / max(1, total)
        slow_ratio = slow_count / max(1, total)
        
        # Clamp to [0, 1] range to satisfy Pydantic constraints
        fast_score = max(0.0, min(1.0, 0.5 + (fast_ratio - 0.5) * 1.2))
        slow_score = max(0.0, min(1.0, 0.5 + (slow_ratio - 0.5) * 1.2))
        
        # Determine strategy
        if fast_score > slow_score + 0.2:
            strategy = "fast"
        elif slow_score > fast_score + 0.2:
            strategy = "slow"
        else:
            strategy = "mixed"
        
        # Temporal discounting correlates with fast strategy
        temporal_discounting = fast_score
        
        # Get recommendations
        recommendations = self._get_recommendations(strategy)
        
        confidence = SignalConfidence.HIGH if total >= min_markers_for_confidence else (
            SignalConfidence.MODERATE if total >= 3 else SignalConfidence.LOW
        )
        
        detection = EvolutionaryMotiveDetection(
            life_history_strategy=strategy,
            fast_strategy_score=fast_score,
            slow_strategy_score=slow_score,
            temporal_discounting=temporal_discounting,
            fast_markers_found=fast_found,
            slow_markers_found=slow_found,
            confidence=confidence,
            **recommendations,
        )
        
        self._detection_count += 1
        
        logger.debug(
            f"Evolutionary motive detection: strategy={strategy}, "
            f"fast={fast_score:.2f}, slow={slow_score:.2f}"
        )
        
        return detection
    
    def detect_from_behavioral_signals(
        self,
        impulse_purchase_count: int = 0,
        research_time_minutes: float = 0.0,
        urgency_response_rate: float = 0.5,
        loyalty_program_engagement: float = 0.5,
        discount_seeking_rate: float = 0.5,
    ) -> EvolutionaryMotiveDetection:
        """
        Detect life history strategy from behavioral signals.
        
        Args:
            impulse_purchase_count: Number of impulse purchases
            research_time_minutes: Time spent researching before purchase
            urgency_response_rate: Response rate to urgency cues
            loyalty_program_engagement: Engagement with loyalty programs
            discount_seeking_rate: Rate of seeking discounts
            
        Returns:
            EvolutionaryMotiveDetection
        """
        signals_used = []
        fast_indicators = 0.0
        slow_indicators = 0.0
        total_signals = 0
        
        # Impulse purchases → fast strategy
        if impulse_purchase_count > 0:
            fast_indicators += min(1.0, impulse_purchase_count / 5) * 0.3
            signals_used.append("impulse_purchases")
            total_signals += 1
        
        # Research time → slow strategy
        if research_time_minutes > 0:
            slow_indicators += min(1.0, research_time_minutes / 30) * 0.3
            signals_used.append("research_time")
            total_signals += 1
        
        # Urgency response → fast strategy
        if urgency_response_rate > 0.6:
            fast_indicators += (urgency_response_rate - 0.5) * 0.4
            signals_used.append("urgency_response")
            total_signals += 1
        
        # Loyalty program → slow strategy (delayed rewards)
        if loyalty_program_engagement > 0.5:
            slow_indicators += (loyalty_program_engagement - 0.5) * 0.3
            signals_used.append("loyalty_engagement")
            total_signals += 1
        
        # Heavy discount seeking → can indicate either (but often fast)
        if discount_seeking_rate > 0.7:
            fast_indicators += 0.1
            signals_used.append("discount_seeking")
            total_signals += 1
        
        # Normalize scores
        fast_score = min(1.0, 0.5 + fast_indicators)
        slow_score = min(1.0, 0.5 + slow_indicators)
        
        if fast_score > slow_score + 0.2:
            strategy = "fast"
        elif slow_score > fast_score + 0.2:
            strategy = "slow"
        else:
            strategy = "mixed"
        
        recommendations = self._get_recommendations(strategy)
        confidence = SignalConfidence.MODERATE if total_signals >= 3 else SignalConfidence.LOW
        
        return EvolutionaryMotiveDetection(
            life_history_strategy=strategy,
            fast_strategy_score=fast_score,
            slow_strategy_score=slow_score,
            temporal_discounting=fast_score,
            confidence=confidence,
            **recommendations,
        )
    
    def analyze_signaling(
        self,
        product_categories: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze what traits products signal.
        
        Args:
            product_categories: List of product categories
            
        Returns:
            Dict with signaling analysis
        """
        signaled_traits = {}
        
        for category in product_categories:
            category_lower = category.lower()
            for cat_key, traits in PRODUCT_SIGNALING_MAP.items():
                if cat_key in category_lower:
                    for trait in traits:
                        signaled_traits[trait.value] = signaled_traits.get(trait.value, 0) + 1
        
        # Sort by frequency
        sorted_traits = sorted(signaled_traits.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "traits_signaled": [t for t, c in sorted_traits],
            "trait_counts": dict(sorted_traits),
            "primary_traits": [t for t, c in sorted_traits[:2]],
        }
    
    def get_gender_specific_framing(
        self,
        product_category: str,
        signaling_context: bool = True,
    ) -> Dict[str, str]:
        """
        Get gender-specific framing based on evolutionary psychology.
        
        Note: Use with caution - individual variation is high.
        
        Research basis:
        - Men: Luxury signals resources → attracts mates
        - Women: Luxury signals status → deters rivals
        
        Args:
            product_category: Product category
            signaling_context: Whether signaling context is relevant
            
        Returns:
            Dict with male and female framing suggestions
        """
        if not signaling_context:
            return {}
        
        category_lower = product_category.lower()
        
        # Luxury/status categories
        if any(cat in category_lower for cat in ["luxury", "fashion", "jewelry", "car"]):
            return {
                "male_framing": "Attract attention, display success, make an impression",
                "female_framing": "Express your style, stand out from the crowd, unique elegance",
            }
        
        # Fitness/appearance
        if any(cat in category_lower for cat in ["fitness", "beauty", "health"]):
            return {
                "male_framing": "Build strength, increase performance, competitive edge",
                "female_framing": "Enhance your natural beauty, confidence from within",
            }
        
        return {}
    
    def _get_recommendations(self, strategy: str) -> Dict[str, Any]:
        """Get ad recommendations based on life history strategy."""
        if strategy == "fast":
            return {
                "recommended_framing": "scarcity, urgency, immediate reward",
                "recommended_incentives": [
                    "lottery/sweepstakes",
                    "instant win",
                    "limited time offer",
                    "flash sale",
                ],
                "recommended_copy_style": "Now, today, limited time, don't miss out, instant",
                "gender_specific_framing": {},
            }
        elif strategy == "slow":
            return {
                "recommended_framing": "investment, long-term value, quality",
                "recommended_incentives": [
                    "loyalty programs",
                    "compound benefits",
                    "early access",
                    "exclusive membership",
                ],
                "recommended_copy_style": "Built to last, wise investment, lasting value, quality that endures",
                "gender_specific_framing": {},
            }
        else:
            return {
                "recommended_framing": "balanced immediate and long-term benefits",
                "recommended_incentives": [
                    "flexible options",
                    "try now, commit later",
                ],
                "recommended_copy_style": "Great value today, even better tomorrow",
                "gender_specific_framing": {},
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "detections_performed": self._detection_count,
            "signaling_categories_tracked": len(PRODUCT_SIGNALING_MAP),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_detector: Optional[EvolutionaryMotiveDetector] = None


def get_evolutionary_motive_detector() -> EvolutionaryMotiveDetector:
    """Get singleton evolutionary motive detector."""
    global _detector
    if _detector is None:
        _detector = EvolutionaryMotiveDetector()
    return _detector
