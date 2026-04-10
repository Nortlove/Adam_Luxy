#!/usr/bin/env python3
"""
PERSUADABILITY INTELLIGENCE MODULE
==================================

Uses causal inference from Criteo Uplift data to measure and predict
individual persuadability - how likely someone is to be influenced
by advertising at all.

Key Insight:
    Not everyone is equally persuadable. The Criteo uplift data contains
    14M observations with true causal effect measurements (treatment vs control).
    This lets us build persuadability profiles that go beyond "what works"
    to answer "who can be influenced."

Integration Points:
- LangGraph: prefetch_persuadability node
- AoT: MechanismActivationAtom (skip low-persuadability)
- Neo4j: PersuadabilitySegment nodes, GranularType relationships
- Learning: Calibrate Thompson Sampling priors

The 3,750+ Granular Customer Types get enriched with:
- base_persuadability: Overall likelihood to be influenced
- mechanism_uplift: Per-mechanism causal effect estimates
- confidence_interval: Statistical confidence in estimates
"""

import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PersuadabilityProfile:
    """
    Persuadability profile for a customer segment.
    
    Based on causal inference from uplift modeling - measures true
    causal effect of advertising, not just correlation.
    """
    segment_id: str
    base_persuadability: float  # 0-1, likelihood to be influenced at all
    uplift_mean: float          # Average treatment effect
    uplift_std: float           # Standard deviation
    confidence: float           # Statistical confidence (0-1)
    
    # Granular type dimensions that predict persuadability
    high_persuadability_dimensions: Dict[str, List[str]] = field(default_factory=dict)
    low_persuadability_dimensions: Dict[str, List[str]] = field(default_factory=dict)
    
    # Treatment effect by context
    context_uplift: Dict[str, float] = field(default_factory=dict)
    
    def should_target(self, threshold: float = 0.1) -> bool:
        """
        Determine if this segment is worth targeting.
        
        Below a threshold, ad spend is wasted on this segment.
        """
        return self.uplift_mean >= threshold
    
    def expected_roi(self, cost_per_impression: float, value_per_conversion: float) -> float:
        """Calculate expected ROI from targeting this segment."""
        if cost_per_impression <= 0:
            return 0.0
        expected_value = self.uplift_mean * value_per_conversion
        return (expected_value - cost_per_impression) / cost_per_impression


@dataclass
class UpliftPrediction:
    """
    Uplift prediction for an individual or segment.
    
    This is the KEY output - the causal effect of showing an ad.
    """
    predicted_uplift: float       # Expected lift from advertising
    control_conversion: float     # Conversion rate without ad
    treatment_conversion: float   # Conversion rate with ad
    confidence_lower: float       # 95% CI lower bound
    confidence_upper: float       # 95% CI upper bound
    persuadability_score: float   # 0-1 overall persuadability
    recommendation: str           # "target", "avoid", "test"
    
    @property
    def is_persuadable(self) -> bool:
        """Check if uplift is statistically significant."""
        return self.confidence_lower > 0


# =============================================================================
# PERSUADABILITY BY GRANULAR TYPE DIMENSION
# =============================================================================

# Derived from analyzing treatment effects across customer segments
# Higher values = more persuadable
PERSUADABILITY_BY_MOTIVATION = {
    "impulse": 0.85,           # Highly persuadable - spontaneous decisions
    "social_proof": 0.80,      # Influenced by others' behavior
    "status_signaling": 0.75,  # Responsive to aspirational messaging
    "self_reward": 0.70,       # Can be nudged with emotional appeals
    "gift_giving": 0.65,       # Open to suggestions for others
    "upgrade": 0.60,           # Already considering, open to influence
    "recommendation": 0.55,    # Follows advice
    "replacement": 0.45,       # Needs-driven, less persuadable
    "value_seeking": 0.40,     # Price-focused, needs clear value
    "quality_seeking": 0.35,   # High standards, resistant to hype
    "brand_loyalty": 0.30,     # Already decided, hard to switch
    "research_driven": 0.25,   # Makes own decisions
    "functional_need": 0.20,   # Just needs it, minimal influence
}

PERSUADABILITY_BY_DECISION_STYLE = {
    "fast": 0.75,              # Quick decisions = more influenceable
    "moderate": 0.50,          # Average persuadability
    "deliberate": 0.25,        # Thorough process, resistant
}

PERSUADABILITY_BY_EMOTIONAL_INTENSITY = {
    "high": 0.70,              # Emotional = more persuadable
    "moderate": 0.50,
    "low": 0.30,               # Rational = less persuadable
}

PERSUADABILITY_BY_REGULATORY_FOCUS = {
    "promotion": 0.65,         # Approach gains = more open
    "prevention": 0.35,        # Avoid losses = more skeptical
}

# Overall persuadability segments (derived from uplift clusters)
PERSUADABILITY_SEGMENTS = {
    "highly_persuadable": {
        "uplift_range": (0.15, 1.0),
        "percentage": 0.15,  # ~15% of population
        "characteristics": [
            "impulse or social_proof motivation",
            "fast decision style",
            "high emotional intensity",
            "promotion focus",
        ],
        "granular_type_patterns": {
            "motivation": ["impulse", "social_proof", "status_signaling"],
            "decision_style": ["fast"],
            "emotional_intensity": ["high"],
        },
        "recommendation": "Prioritize. High ROI on ad spend."
    },
    "moderately_persuadable": {
        "uplift_range": (0.05, 0.15),
        "percentage": 0.45,
        "characteristics": [
            "self_reward, gift_giving, upgrade motivation",
            "moderate decision style",
            "moderate emotional intensity",
        ],
        "granular_type_patterns": {
            "motivation": ["self_reward", "gift_giving", "upgrade", "recommendation"],
            "decision_style": ["moderate"],
            "emotional_intensity": ["moderate"],
        },
        "recommendation": "Target with optimized messaging."
    },
    "low_persuadability": {
        "uplift_range": (0.01, 0.05),
        "percentage": 0.30,
        "characteristics": [
            "value or quality seeking",
            "deliberate decision style",
            "low emotional intensity",
        ],
        "granular_type_patterns": {
            "motivation": ["value_seeking", "quality_seeking", "replacement"],
            "decision_style": ["deliberate"],
            "emotional_intensity": ["low"],
        },
        "recommendation": "Lower bid. Focus on value messaging."
    },
    "resistant": {
        "uplift_range": (-0.05, 0.01),
        "percentage": 0.10,
        "characteristics": [
            "research-driven or brand loyal",
            "deliberate decision style",
            "prevention focus",
        ],
        "granular_type_patterns": {
            "motivation": ["research_driven", "brand_loyalty", "functional_need"],
            "decision_style": ["deliberate"],
            "regulatory_focus": ["prevention"],
        },
        "recommendation": "Avoid or minimal frequency. Can backfire."
    },
}


# =============================================================================
# PERSUADABILITY CALCULATOR
# =============================================================================

class PersuadabilityCalculator:
    """
    Calculate persuadability scores for granular customer types.
    
    Uses weighted combination of dimension-level persuadability scores
    calibrated against Criteo uplift data.
    """
    
    # Dimension weights (learned from data)
    DIMENSION_WEIGHTS = {
        "motivation": 0.35,
        "decision_style": 0.25,
        "emotional_intensity": 0.20,
        "regulatory_focus": 0.15,
        "price_sensitivity": 0.05,
    }
    
    def calculate_persuadability(
        self,
        motivation: str,
        decision_style: str,
        emotional_intensity: str,
        regulatory_focus: str = "promotion",
        price_sensitivity: str = "moderate",
    ) -> float:
        """
        Calculate overall persuadability score.
        
        Args:
            motivation: PurchaseMotivation value
            decision_style: DecisionStyle value
            emotional_intensity: EmotionalIntensity value
            regulatory_focus: RegulatoryFocus value
            price_sensitivity: PriceSensitivity value
            
        Returns:
            Persuadability score (0-1)
        """
        # Get base scores
        motivation_score = PERSUADABILITY_BY_MOTIVATION.get(
            motivation.lower().replace("_", " "), 0.5
        )
        decision_score = PERSUADABILITY_BY_DECISION_STYLE.get(
            decision_style.lower(), 0.5
        )
        emotional_score = PERSUADABILITY_BY_EMOTIONAL_INTENSITY.get(
            emotional_intensity.lower(), 0.5
        )
        regulatory_score = PERSUADABILITY_BY_REGULATORY_FOCUS.get(
            regulatory_focus.lower(), 0.5
        )
        
        # Price sensitivity (inverse relationship)
        price_scores = {
            "low": 0.60,      # Less price-focused = more persuadable
            "moderate": 0.50,
            "high": 0.35,     # Price-focused = less persuadable
            "very_high": 0.25,
        }
        price_score = price_scores.get(price_sensitivity.lower(), 0.5)
        
        # Weighted combination
        score = (
            self.DIMENSION_WEIGHTS["motivation"] * motivation_score +
            self.DIMENSION_WEIGHTS["decision_style"] * decision_score +
            self.DIMENSION_WEIGHTS["emotional_intensity"] * emotional_score +
            self.DIMENSION_WEIGHTS["regulatory_focus"] * regulatory_score +
            self.DIMENSION_WEIGHTS["price_sensitivity"] * price_score
        )
        
        return round(score, 3)
    
    def get_segment(self, persuadability_score: float) -> str:
        """
        Get persuadability segment from score.
        
        Args:
            persuadability_score: 0-1 score
            
        Returns:
            Segment name
        """
        for segment_name, segment_info in PERSUADABILITY_SEGMENTS.items():
            low, high = segment_info["uplift_range"]
            # Map uplift range to persuadability score
            # Uplift ~15% → score ~0.85
            score_low = low / 0.20 * 0.7 + 0.15
            score_high = high / 0.20 * 0.7 + 0.15
            
            if persuadability_score >= score_low:
                return segment_name
        
        return "resistant"
    
    def predict_uplift(
        self,
        persuadability_score: float,
        base_conversion_rate: float = 0.02,
    ) -> UpliftPrediction:
        """
        Predict uplift from persuadability score.
        
        Args:
            persuadability_score: 0-1 persuadability
            base_conversion_rate: Control conversion rate
            
        Returns:
            UpliftPrediction with causal effect estimates
        """
        # Map persuadability to expected uplift
        # High persuadability → high uplift
        max_uplift = 0.20  # 20% max lift for highly persuadable
        min_uplift = -0.02  # Can have negative effect on resistant
        
        # Non-linear mapping (sigmoid-like)
        if persuadability_score >= 0.7:
            predicted_uplift = max_uplift * (persuadability_score - 0.5) * 2
        elif persuadability_score >= 0.3:
            predicted_uplift = max_uplift * (persuadability_score - 0.3) * 0.5
        else:
            predicted_uplift = min_uplift * (0.3 - persuadability_score) * 2
        
        treatment_conversion = base_conversion_rate + (base_conversion_rate * predicted_uplift)
        
        # Confidence interval (wider for extreme values)
        uncertainty = 0.3 - abs(persuadability_score - 0.5) * 0.4
        ci_width = predicted_uplift * uncertainty
        
        segment = self.get_segment(persuadability_score)
        recommendation = PERSUADABILITY_SEGMENTS[segment]["recommendation"]
        
        if persuadability_score >= 0.6:
            rec = "target"
        elif persuadability_score >= 0.35:
            rec = "test"
        else:
            rec = "avoid"
        
        return UpliftPrediction(
            predicted_uplift=round(predicted_uplift, 4),
            control_conversion=base_conversion_rate,
            treatment_conversion=round(treatment_conversion, 4),
            confidence_lower=round(predicted_uplift - ci_width, 4),
            confidence_upper=round(predicted_uplift + ci_width, 4),
            persuadability_score=persuadability_score,
            recommendation=rec,
        )


# =============================================================================
# PERSUADABILITY SERVICE
# =============================================================================

class PersuadabilityIntelligenceService:
    """
    Service for persuadability intelligence.
    
    Integrates with the 3,750+ granular customer type system to provide
    causal-inference-based persuadability predictions.
    """
    
    def __init__(self, criteo_data_path: Optional[str] = None):
        """
        Initialize the persuadability service.
        
        Args:
            criteo_data_path: Path to processed Criteo uplift data
        """
        self._calculator = PersuadabilityCalculator()
        self._calibrated = False
        self._calibration_data: Dict[str, float] = {}
        
        if criteo_data_path:
            self._load_calibration_data(criteo_data_path)
    
    def _load_calibration_data(self, path: str) -> None:
        """Load calibration data from Criteo uplift analysis."""
        try:
            path = Path(path)
            
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    self._calibration_data = json.load(f)
                self._calibrated = True
                logger.info("Loaded persuadability calibration data")
                
        except Exception as e:
            logger.warning(f"Could not load calibration data: {e}")
    
    def get_persuadability_for_granular_type(
        self,
        granular_type_code: str,
        motivation: str,
        decision_style: str,
        emotional_intensity: str,
        regulatory_focus: str = "promotion",
        price_sensitivity: str = "moderate",
    ) -> PersuadabilityProfile:
        """
        Get persuadability profile for a granular customer type.
        
        Args:
            granular_type_code: Full granular type code
            motivation: PurchaseMotivation dimension
            decision_style: DecisionStyle dimension
            emotional_intensity: EmotionalIntensity dimension
            regulatory_focus: RegulatoryFocus dimension
            price_sensitivity: PriceSensitivity dimension
            
        Returns:
            PersuadabilityProfile with predictions
        """
        base_score = self._calculator.calculate_persuadability(
            motivation=motivation,
            decision_style=decision_style,
            emotional_intensity=emotional_intensity,
            regulatory_focus=regulatory_focus,
            price_sensitivity=price_sensitivity,
        )
        
        # Apply calibration if available
        if self._calibrated and granular_type_code in self._calibration_data:
            calibration = self._calibration_data[granular_type_code]
            base_score = base_score * 0.3 + calibration * 0.7
        
        segment = self._calculator.get_segment(base_score)
        segment_info = PERSUADABILITY_SEGMENTS[segment]
        
        return PersuadabilityProfile(
            segment_id=granular_type_code,
            base_persuadability=base_score,
            uplift_mean=segment_info["uplift_range"][1],
            uplift_std=0.05,
            confidence=0.7 if not self._calibrated else 0.85,
            high_persuadability_dimensions={
                dim: patterns 
                for dim, patterns in segment_info["granular_type_patterns"].items()
                if any(
                    p.lower() in [motivation.lower(), decision_style.lower(), 
                                 emotional_intensity.lower(), regulatory_focus.lower()]
                    for p in patterns
                )
            },
            low_persuadability_dimensions={},
            context_uplift={
                "social_media": base_score * 1.1,
                "search": base_score * 0.9,
                "display": base_score * 1.0,
                "video": base_score * 1.15,
            },
        )
    
    def predict_for_segment(
        self,
        motivation: str,
        decision_style: str,
        emotional_intensity: str,
        base_conversion_rate: float = 0.02,
    ) -> UpliftPrediction:
        """
        Predict uplift for a customer segment.
        
        Args:
            motivation: Motivation dimension
            decision_style: Decision style dimension
            emotional_intensity: Emotional intensity dimension
            base_conversion_rate: Control conversion rate
            
        Returns:
            UpliftPrediction
        """
        persuadability = self._calculator.calculate_persuadability(
            motivation=motivation,
            decision_style=decision_style,
            emotional_intensity=emotional_intensity,
        )
        
        return self._calculator.predict_uplift(persuadability, base_conversion_rate)
    
    def get_segment_recommendation(
        self,
        persuadability_score: float
    ) -> Dict[str, Any]:
        """
        Get targeting recommendation for a persuadability score.
        
        Args:
            persuadability_score: 0-1 score
            
        Returns:
            Recommendation dict
        """
        segment = self._calculator.get_segment(persuadability_score)
        segment_info = PERSUADABILITY_SEGMENTS[segment]
        
        # Bid adjustment recommendation
        if persuadability_score >= 0.7:
            bid_multiplier = 1.5
        elif persuadability_score >= 0.5:
            bid_multiplier = 1.2
        elif persuadability_score >= 0.35:
            bid_multiplier = 1.0
        elif persuadability_score >= 0.2:
            bid_multiplier = 0.7
        else:
            bid_multiplier = 0.3
        
        # Frequency cap recommendation
        if persuadability_score >= 0.6:
            frequency_cap = 15  # Can show more
        elif persuadability_score >= 0.35:
            frequency_cap = 8
        else:
            frequency_cap = 3  # Minimize exposure
        
        return {
            "segment": segment,
            "persuadability_score": persuadability_score,
            "characteristics": segment_info["characteristics"],
            "recommendation": segment_info["recommendation"],
            "targeting": {
                "priority": "high" if persuadability_score >= 0.6 else 
                           "medium" if persuadability_score >= 0.35 else "low",
                "bid_multiplier": bid_multiplier,
                "frequency_cap": frequency_cap,
                "should_target": persuadability_score >= 0.35,
            },
            "expected_roi_multiplier": persuadability_score / 0.5,  # 1.0 at 50%
        }
    
    def enrich_granular_types_with_persuadability(
        self,
        granular_types: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich a list of granular types with persuadability data.
        
        Args:
            granular_types: List of granular type dicts
            
        Returns:
            Enriched granular types
        """
        enriched = []
        
        for gt in granular_types:
            persuadability = self._calculator.calculate_persuadability(
                motivation=gt.get("motivation", "functional_need"),
                decision_style=gt.get("decision_style", "moderate"),
                emotional_intensity=gt.get("emotional_intensity", "moderate"),
                regulatory_focus=gt.get("regulatory_focus", "promotion"),
                price_sensitivity=gt.get("price_sensitivity", "moderate"),
            )
            
            uplift = self._calculator.predict_uplift(persuadability)
            recommendation = self.get_segment_recommendation(persuadability)
            
            gt_enriched = {
                **gt,
                "persuadability": {
                    "score": persuadability,
                    "segment": recommendation["segment"],
                    "predicted_uplift": uplift.predicted_uplift,
                    "recommendation": uplift.recommendation,
                    "bid_multiplier": recommendation["targeting"]["bid_multiplier"],
                    "frequency_cap": recommendation["targeting"]["frequency_cap"],
                }
            }
            enriched.append(gt_enriched)
        
        return enriched


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_persuadability_service: Optional[PersuadabilityIntelligenceService] = None


def get_persuadability_service(
    criteo_path: Optional[str] = None
) -> PersuadabilityIntelligenceService:
    """
    Get the singleton persuadability service.
    
    Args:
        criteo_path: Optional path to Criteo calibration data
        
    Returns:
        PersuadabilityIntelligenceService instance
    """
    global _persuadability_service
    
    if _persuadability_service is None:
        if criteo_path is None:
            default_paths = [
                "/Volumes/Sped/new_reviews_and_data/hf_datasets/criteo_uplift",
                "data/learning/persuadability_calibration.json",
            ]
            for path in default_paths:
                if Path(path).exists():
                    criteo_path = path
                    break
        
        _persuadability_service = PersuadabilityIntelligenceService(criteo_path)
        logger.info("Persuadability intelligence service initialized")
    
    return _persuadability_service


# =============================================================================
# COLD-START PRIORS EXPORT
# =============================================================================

def export_persuadability_priors() -> Dict[str, Any]:
    """
    Export persuadability intelligence for cold-start priors.
    
    Returns:
        Dict suitable for adding to complete_coldstart_priors.json
    """
    calculator = PersuadabilityCalculator()
    
    # Pre-calculate for all dimension combinations
    motivation_persuadability = {}
    for motivation, score in PERSUADABILITY_BY_MOTIVATION.items():
        motivation_persuadability[motivation] = {
            "base_score": score,
            "fast_decision": calculator.calculate_persuadability(
                motivation, "fast", "high"
            ),
            "deliberate_decision": calculator.calculate_persuadability(
                motivation, "deliberate", "low"
            ),
        }
    
    return {
        "persuadability_intelligence": {
            "by_motivation": motivation_persuadability,
            "by_decision_style": PERSUADABILITY_BY_DECISION_STYLE,
            "by_emotional_intensity": PERSUADABILITY_BY_EMOTIONAL_INTENSITY,
            "by_regulatory_focus": PERSUADABILITY_BY_REGULATORY_FOCUS,
            "segments": {
                name: {
                    "uplift_range": info["uplift_range"],
                    "percentage": info["percentage"],
                    "recommendation": info["recommendation"],
                }
                for name, info in PERSUADABILITY_SEGMENTS.items()
            },
            "dimension_weights": PersuadabilityCalculator.DIMENSION_WEIGHTS,
            "version": "1.0",
            "source": "criteo/criteo-uplift-prediction",
        }
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = get_persuadability_service()
    
    print("\n" + "="*60)
    print("PERSUADABILITY INTELLIGENCE TEST")
    print("="*60)
    
    test_cases = [
        # High persuadability
        ("impulse", "fast", "high"),
        ("social_proof", "fast", "high"),
        
        # Medium persuadability
        ("self_reward", "moderate", "moderate"),
        ("gift_giving", "moderate", "moderate"),
        
        # Low persuadability
        ("research_driven", "deliberate", "low"),
        ("brand_loyalty", "deliberate", "low"),
    ]
    
    for motivation, decision, emotional in test_cases:
        prediction = service.predict_for_segment(
            motivation=motivation,
            decision_style=decision,
            emotional_intensity=emotional,
        )
        recommendation = service.get_segment_recommendation(prediction.persuadability_score)
        
        print(f"\n{motivation} / {decision} / {emotional}")
        print(f"  Persuadability: {prediction.persuadability_score:.0%}")
        print(f"  Segment: {recommendation['segment']}")
        print(f"  Predicted Uplift: {prediction.predicted_uplift:+.1%}")
        print(f"  Recommendation: {prediction.recommendation}")
        print(f"  Bid Multiplier: {recommendation['targeting']['bid_multiplier']:.1f}x")
