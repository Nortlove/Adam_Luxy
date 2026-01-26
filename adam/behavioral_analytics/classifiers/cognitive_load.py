# =============================================================================
# ADAM Behavioral Analytics: Cognitive Load Estimator
# Location: adam/behavioral_analytics/classifiers/cognitive_load.py
# =============================================================================

"""
COGNITIVE LOAD ESTIMATOR

Estimates cognitive load from behavioral signals.

Research Basis:
- Cognitive Load Theory (Sweller, 1988)
- Response time variability studies
- Eye-tracking and scroll behavior research

Indicators:
- Response latency variability (high variability = high load)
- Scroll reversals (re-reading = cognitive effort)
- Hesitation patterns (uncertainty = load)
- Category switching (multitasking = load)
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CognitiveLoadLevel(str, Enum):
    """Cognitive load level."""
    LOW = "low"           # Automatic processing, easy task
    MEDIUM = "medium"     # Moderate effort, engaged
    HIGH = "high"         # Heavy processing, difficulty or overwhelm
    OVERLOAD = "overload"  # Cognitive overload, likely abandonment


class CognitiveLoadEstimator:
    """
    Estimator for cognitive load.
    
    Based on Cognitive Load Theory:
    - Intrinsic load: Task complexity
    - Extraneous load: Poor design/presentation
    - Germane load: Schema building (positive)
    
    We measure behavioral indicators of total load.
    
    Expected Performance:
    - Load estimation correlation with self-report: r=0.5-0.7
    - High load prediction accuracy: 70-80%
    """
    
    # Load indicator weights
    LOAD_INDICATORS = {
        # Response variability (high variance = processing difficulty)
        "response_latency_std": 0.25,
        
        # Scroll behavior (reversals = re-reading = effort)
        "reversal_ratio": 0.20,
        
        # Hesitation (pausing before action = uncertainty)
        "hesitation_count": 0.20,
        "pre_cta_hesitation_ratio": 0.10,
        
        # Navigation complexity
        "category_change_count": 0.10,
        "back_navigation_count": 0.10,
        
        # Time pressure indicators
        "session_duration_normalized": 0.05,
    }
    
    # Thresholds
    HIGH_LOAD_THRESHOLD = 0.7
    MEDIUM_LOAD_THRESHOLD = 0.4
    OVERLOAD_THRESHOLD = 0.85
    
    def __init__(self):
        self._model_version = "1.0.0"
    
    def estimate(
        self,
        features: Dict[str, float],
        task_complexity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Estimate cognitive load from features.
        
        Args:
            features: Behavioral features from session
            task_complexity: Optional intrinsic task complexity (0-1)
            
        Returns:
            Dict with load_score, level, confidence, and breakdown
        """
        indicator_contributions = {}
        weighted_sum = 0.0
        total_weight = 0.0
        features_used = 0
        
        for indicator, weight in self.LOAD_INDICATORS.items():
            if indicator in features:
                value = features[indicator]
                normalized = self._normalize_indicator(indicator, value)
                contribution = weight * normalized
                
                indicator_contributions[indicator] = {
                    "raw_value": value,
                    "normalized": normalized,
                    "weight": weight,
                    "contribution": contribution,
                }
                
                weighted_sum += contribution
                total_weight += weight
                features_used += 1
        
        # Base load score
        if total_weight > 0:
            load_score = weighted_sum / total_weight
        else:
            load_score = 0.5  # Default medium
        
        # Adjust for task complexity if provided
        if task_complexity is not None:
            # High complexity naturally increases load
            complexity_adjustment = (task_complexity - 0.5) * 0.2
            load_score = max(0.0, min(1.0, load_score + complexity_adjustment))
        
        # Classify level
        level = self._classify_level(load_score)
        
        # Compute confidence
        confidence = min(0.9, features_used / 4)
        
        # Recommendations
        recommendations = self._generate_recommendations(load_score, indicator_contributions)
        
        return {
            "load_score": load_score,
            "level": level.value,
            "confidence": confidence,
            "features_used": features_used,
            "indicator_contributions": indicator_contributions,
            "thresholds": {
                "medium": self.MEDIUM_LOAD_THRESHOLD,
                "high": self.HIGH_LOAD_THRESHOLD,
                "overload": self.OVERLOAD_THRESHOLD,
            },
            "recommendations": recommendations,
        }
    
    def _normalize_indicator(self, indicator: str, value: float) -> float:
        """Normalize indicator to 0-1 (higher = more load)."""
        normalizers = {
            "response_latency_std": lambda v: min(1.0, v / 2000),  # 2s std = max load
            "reversal_ratio": lambda v: min(1.0, v * 2),  # 50% reversals = max
            "hesitation_count": lambda v: min(1.0, v / 5),  # 5+ hesitations = max
            "pre_cta_hesitation_ratio": lambda v: v,  # Already 0-1
            "category_change_count": lambda v: min(1.0, v / 10),
            "back_navigation_count": lambda v: min(1.0, v / 5),
            "session_duration_normalized": lambda v: v,  # Already 0-1
        }
        
        normalizer = normalizers.get(indicator, lambda v: min(1.0, v))
        return normalizer(value)
    
    def _classify_level(self, load_score: float) -> CognitiveLoadLevel:
        """Classify cognitive load level."""
        if load_score >= self.OVERLOAD_THRESHOLD:
            return CognitiveLoadLevel.OVERLOAD
        elif load_score >= self.HIGH_LOAD_THRESHOLD:
            return CognitiveLoadLevel.HIGH
        elif load_score >= self.MEDIUM_LOAD_THRESHOLD:
            return CognitiveLoadLevel.MEDIUM
        else:
            return CognitiveLoadLevel.LOW
    
    def _generate_recommendations(
        self,
        load_score: float,
        contributions: Dict[str, Dict],
    ) -> List[str]:
        """Generate recommendations based on load analysis."""
        recommendations = []
        
        if load_score >= self.HIGH_LOAD_THRESHOLD:
            recommendations.append("Consider simplifying the current experience")
        
        if "reversal_ratio" in contributions:
            if contributions["reversal_ratio"]["normalized"] > 0.5:
                recommendations.append("Content may be confusing - consider clearer hierarchy")
        
        if "hesitation_count" in contributions:
            if contributions["hesitation_count"]["normalized"] > 0.6:
                recommendations.append("User showing uncertainty - provide reassurance")
        
        if "back_navigation_count" in contributions:
            if contributions["back_navigation_count"]["normalized"] > 0.5:
                recommendations.append("Navigation may be unclear - simplify path")
        
        return recommendations


# Singleton
_estimator: Optional[CognitiveLoadEstimator] = None


def get_cognitive_load_estimator() -> CognitiveLoadEstimator:
    """Get singleton cognitive load estimator."""
    global _estimator
    if _estimator is None:
        _estimator = CognitiveLoadEstimator()
    return _estimator
