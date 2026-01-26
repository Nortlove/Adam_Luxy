# =============================================================================
# ADAM Behavioral Analytics: Temporal Targeting Classifier
# Location: adam/behavioral_analytics/classifiers/temporal_targeting.py
# =============================================================================

"""
TEMPORAL TARGETING CLASSIFIER

Optimizes ad timing and message construal based on:
1. Construal Level Theory (g = 0.475 for matching)
2. Circadian patterns (cognitive peak vs trough)
3. Weekly patterns (weekend hedonic vs weekday utilitarian)
4. Synchrony effect (chronotype × time)

Key Insight: Match message abstraction to psychological distance.
- Far distance (awareness) → Abstract (WHY, benefits)
- Near distance (purchase) → Concrete (HOW, features)

Reference: Trope & Liberman CLT; Yoon et al. (2007)
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.advertising_psychology import (
    ConstrualLevelProfile,
    TemporalPattern,
    ChronotypeProfile,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# FUNNEL STAGE DEFINITIONS
# =============================================================================

class FunnelStage(str, Enum):
    """Marketing funnel stages with psychological distance mapping."""
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    PURCHASE = "purchase"
    POST_PURCHASE = "post_purchase"


# Funnel stage → Construal Level recommendations
FUNNEL_CONSTRUAL_MAP = {
    FunnelStage.AWARENESS: {
        "psychological_distance": "far",
        "construal_level": "high_abstract",
        "message_focus": "WHY - benefits, values, desirability",
        "language": "Transform, achieve, experience, lifestyle",
        "imagery": "Wide shots, aspirational, future self",
        "effect_size": 0.475,  # g from meta-analysis
    },
    FunnelStage.CONSIDERATION: {
        "psychological_distance": "medium",
        "construal_level": "mixed",
        "message_focus": "WHY + HOW balance",
        "language": "Benefits supported by features",
        "imagery": "Mixed wide and detail shots",
        "effect_size": 0.475,
    },
    FunnelStage.DECISION: {
        "psychological_distance": "near",
        "construal_level": "low_concrete",
        "message_focus": "HOW - features, specs, feasibility",
        "language": "Specific, practical, actionable",
        "imagery": "Close-ups, details, product in use",
        "effect_size": 0.475,
    },
    FunnelStage.PURCHASE: {
        "psychological_distance": "very_near",
        "construal_level": "very_low_concrete",
        "message_focus": "ACTION - checkout, delivery, guarantee",
        "language": "Now, today, simple steps",
        "imagery": "Cart, checkout process, delivery",
        "effect_size": 0.475,
    },
    FunnelStage.POST_PURCHASE: {
        "psychological_distance": "past_concrete",
        "construal_level": "low_concrete",
        "message_focus": "Reinforce decision, usage tips",
        "language": "You made a great choice, here's how to use",
        "imagery": "Product in use, satisfied customers",
        "effect_size": 0.30,
    },
}


# =============================================================================
# CIRCADIAN PATTERNS
# =============================================================================

# Cognitive performance by hour (population average)
# 0.0 = peak performance, 1.0 = maximum cognitive load
CIRCADIAN_LOAD = {
    0: 0.65, 1: 0.70, 2: 0.75, 3: 0.80,
    4: 0.85, 5: 0.80, 6: 0.70, 7: 0.55,
    8: 0.45, 9: 0.35, 10: 0.30, 11: 0.28,  # Late morning peak
    12: 0.32, 13: 0.38, 14: 0.40,  # Post-lunch dip
    15: 0.35, 16: 0.28, 17: 0.25,  # Afternoon peak
    18: 0.30, 19: 0.35, 20: 0.40,
    21: 0.50, 22: 0.55, 23: 0.60,
}


# =============================================================================
# TEMPORAL RECOMMENDATION
# =============================================================================

class TemporalRecommendation(BaseModel):
    """
    Temporal targeting recommendation combining all factors.
    """
    
    # Construal level
    funnel_stage: FunnelStage = Field(default=FunnelStage.CONSIDERATION)
    construal_level: str = Field(default="mixed")
    message_focus: str = Field(default="")
    language_style: str = Field(default="")
    imagery_type: str = Field(default="")
    
    # Circadian
    hour_of_day: int = Field(default=12, ge=0, le=23)
    circadian_load: float = Field(default=0.5, ge=0.0, le=1.0)
    is_cognitive_peak: bool = Field(default=False)
    
    # Weekly
    day_of_week: int = Field(default=0, ge=0, le=6)
    is_weekend: bool = Field(default=False)
    shopping_mode: str = Field(default="balanced")  # hedonic, utilitarian, balanced
    
    # Chronotype (if known)
    chronotype: str = Field(default="neutral")
    synchrony_status: str = Field(default="neutral")  # at_peak, off_peak, neutral
    
    # Processing recommendations (ELM)
    recommended_processing: str = Field(default="mixed")  # central, peripheral, mixed
    message_complexity: str = Field(default="moderate")  # high, moderate, low
    
    # Effect sizes
    construal_effect_size: float = Field(default=0.475)
    total_expected_lift: float = Field(default=0.0)
    
    # Confidence
    confidence: SignalConfidence = Field(default=SignalConfidence.MODERATE)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "funnel_stage": self.funnel_stage.value,
            "construal_level": self.construal_level,
            "message_focus": self.message_focus,
            "language_style": self.language_style,
            "imagery_type": self.imagery_type,
            "hour_of_day": self.hour_of_day,
            "circadian_load": self.circadian_load,
            "is_cognitive_peak": self.is_cognitive_peak,
            "day_of_week": self.day_of_week,
            "is_weekend": self.is_weekend,
            "shopping_mode": self.shopping_mode,
            "chronotype": self.chronotype,
            "synchrony_status": self.synchrony_status,
            "recommended_processing": self.recommended_processing,
            "message_complexity": self.message_complexity,
            "construal_effect_size": self.construal_effect_size,
            "total_expected_lift": self.total_expected_lift,
            "confidence": self.confidence.value,
        }


# =============================================================================
# TEMPORAL TARGETING CLASSIFIER
# =============================================================================

class TemporalTargetingClassifier:
    """
    Optimizes ad timing and message construal.
    
    Combines:
    1. Construal Level Theory (g = 0.475)
    2. Circadian patterns
    3. Weekly patterns
    4. Chronotype synchrony
    
    Usage:
        classifier = TemporalTargetingClassifier()
        rec = classifier.get_recommendation(
            funnel_stage="consideration",
            hour=14,
            day_of_week=5,  # Saturday
            chronotype="morning"
        )
    """
    
    def __init__(self):
        self._recommendation_count = 0
    
    def get_recommendation(
        self,
        funnel_stage: str = "consideration",
        hour: Optional[int] = None,
        day_of_week: Optional[int] = None,
        chronotype: str = "neutral",
    ) -> TemporalRecommendation:
        """
        Get temporal targeting recommendation.
        
        Args:
            funnel_stage: Marketing funnel position
            hour: Hour of day (0-23), uses current if None
            day_of_week: Day (0=Monday, 6=Sunday), uses current if None
            chronotype: User chronotype
            
        Returns:
            TemporalRecommendation with all factors combined
        """
        # Get current time if not specified
        now = datetime.now()
        if hour is None:
            hour = now.hour
        if day_of_week is None:
            day_of_week = now.weekday()
        
        # Parse funnel stage
        try:
            stage = FunnelStage(funnel_stage)
        except ValueError:
            stage = FunnelStage.CONSIDERATION
        
        # Get construal recommendations
        construal_recs = FUNNEL_CONSTRUAL_MAP.get(stage, FUNNEL_CONSTRUAL_MAP[FunnelStage.CONSIDERATION])
        
        # Get circadian load
        circadian_load = CIRCADIAN_LOAD.get(hour, 0.5)
        is_peak = circadian_load < 0.35
        
        # Weekly pattern
        is_weekend = day_of_week >= 5
        shopping_mode = "hedonic" if is_weekend else "utilitarian"
        
        # Synchrony effect
        synchrony_status = self._check_synchrony(hour, chronotype)
        
        # Processing route (ELM)
        if circadian_load > 0.5 or synchrony_status == "off_peak":
            recommended_processing = "peripheral"
            message_complexity = "low"
        elif circadian_load < 0.35 and synchrony_status == "at_peak":
            recommended_processing = "central"
            message_complexity = "high"
        else:
            recommended_processing = "mixed"
            message_complexity = "moderate"
        
        # Calculate expected lift
        expected_lift = self._calculate_expected_lift(
            stage=stage,
            is_peak=is_peak,
            synchrony_status=synchrony_status,
            is_weekend=is_weekend,
        )
        
        recommendation = TemporalRecommendation(
            funnel_stage=stage,
            construal_level=construal_recs["construal_level"],
            message_focus=construal_recs["message_focus"],
            language_style=construal_recs["language"],
            imagery_type=construal_recs["imagery"],
            hour_of_day=hour,
            circadian_load=circadian_load,
            is_cognitive_peak=is_peak,
            day_of_week=day_of_week,
            is_weekend=is_weekend,
            shopping_mode=shopping_mode,
            chronotype=chronotype,
            synchrony_status=synchrony_status,
            recommended_processing=recommended_processing,
            message_complexity=message_complexity,
            construal_effect_size=construal_recs["effect_size"],
            total_expected_lift=expected_lift,
            confidence=SignalConfidence.HIGH if chronotype != "neutral" else SignalConfidence.MODERATE,
        )
        
        self._recommendation_count += 1
        
        logger.debug(
            f"Temporal recommendation: stage={stage.value}, "
            f"construal={construal_recs['construal_level']}, "
            f"processing={recommended_processing}"
        )
        
        return recommendation
    
    def get_optimal_times(
        self,
        message_type: str,
        chronotype: str = "neutral",
    ) -> List[int]:
        """
        Get optimal hours for a message type.
        
        Args:
            message_type: "complex_rational", "simple_emotional", or "balanced"
            chronotype: User chronotype
            
        Returns:
            List of recommended hours (0-23)
        """
        if message_type == "complex_rational":
            # Need low cognitive load → peak hours
            if chronotype == "morning":
                return [8, 9, 10, 11]
            elif chronotype == "evening":
                return [18, 19, 20, 21]
            else:
                return [10, 11, 16, 17]
        
        elif message_type == "simple_emotional":
            # Can handle high load → any time, prefer off-peak for emotional
            if chronotype == "morning":
                return [18, 19, 20, 21, 22]
            elif chronotype == "evening":
                return [6, 7, 8, 9, 10]
            else:
                return [12, 13, 14, 19, 20, 21]
        
        else:  # balanced
            # Middle ground
            return [9, 10, 11, 14, 15, 16, 17, 18, 19]
    
    def get_funnel_stage_from_behavior(
        self,
        page_views: int = 0,
        product_views: int = 0,
        add_to_cart: bool = False,
        checkout_started: bool = False,
        previous_purchase: bool = False,
    ) -> FunnelStage:
        """
        Infer funnel stage from behavioral signals.
        
        Args:
            page_views: Total page views in session
            product_views: Product detail views
            add_to_cart: Whether item was added to cart
            checkout_started: Whether checkout was started
            previous_purchase: Whether user has purchased before
            
        Returns:
            Inferred FunnelStage
        """
        if checkout_started:
            return FunnelStage.PURCHASE
        elif add_to_cart:
            return FunnelStage.DECISION
        elif product_views > 2:
            return FunnelStage.DECISION
        elif product_views > 0:
            return FunnelStage.CONSIDERATION
        elif page_views > 0:
            return FunnelStage.AWARENESS
        else:
            return FunnelStage.AWARENESS
    
    def _check_synchrony(self, hour: int, chronotype: str) -> str:
        """Check synchrony status based on chronotype and time."""
        if chronotype == "morning":
            if 8 <= hour <= 11:
                return "at_peak"
            elif 18 <= hour <= 22:
                return "off_peak"
        elif chronotype == "evening":
            if 18 <= hour <= 22:
                return "at_peak"
            elif 6 <= hour <= 10:
                return "off_peak"
        return "neutral"
    
    def _calculate_expected_lift(
        self,
        stage: FunnelStage,
        is_peak: bool,
        synchrony_status: str,
        is_weekend: bool,
    ) -> float:
        """Calculate expected lift from temporal optimization."""
        lift = 0.0
        
        # Construal matching (g = 0.475)
        lift += 0.475 * 0.5  # Assume 50% of max effect for matching
        
        # Synchrony effect (d ≈ 0.4)
        if synchrony_status == "at_peak":
            lift += 0.4 * 0.3
        elif synchrony_status == "off_peak":
            lift -= 0.2 * 0.3
        
        # Weekend hedonic bonus
        if is_weekend:
            lift += 0.22 * 0.3  # 22% spending lift
        
        # Cognitive peak bonus
        if is_peak:
            lift += 0.15
        
        return round(lift, 3)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        return {
            "recommendations_made": self._recommendation_count,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_classifier: Optional[TemporalTargetingClassifier] = None


def get_temporal_targeting_classifier() -> TemporalTargetingClassifier:
    """Get singleton temporal targeting classifier."""
    global _classifier
    if _classifier is None:
        _classifier = TemporalTargetingClassifier()
    return _classifier
