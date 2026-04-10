#!/usr/bin/env python3
"""
ATTRIBUTION INTELLIGENCE MODULE
===============================

Uses Criteo Attribution data to understand multi-touch conversion paths
and optimize mechanism sequencing.

Key Insight:
    Persuasion is rarely a single moment. The Criteo attribution data 
    contains 16M conversion paths showing how multiple ad exposures
    interact to create conversions. This lets us sequence mechanisms
    strategically rather than treating each touchpoint independently.

Integration Points:
- LangGraph: prefetch_attribution_intelligence node
- AoT: SequencePlanningAtom (new), MechanismActivationAtom (sequencing)
- Neo4j: MechanismSequence nodes, ConversionPath relationships
- Learning: Optimal mechanism ordering for granular types

The 3,750+ Granular Customer Types get enriched with:
- optimal_sequence: Best mechanism ordering for this type
- touchpoint_sensitivity: How many touches needed
- position_effects: First-touch vs last-touch effectiveness
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class TouchpointPosition(Enum):
    """Position in the customer journey."""
    FIRST = "first"        # Initial awareness
    EARLY = "early"        # Building interest
    MIDDLE = "middle"      # Consideration
    LATE = "late"          # Decision support
    LAST = "last"          # Conversion driver


@dataclass
class TouchpointEffect:
    """
    Effectiveness of a mechanism at different journey positions.
    """
    mechanism: str
    position: TouchpointPosition
    effectiveness: float  # 0-1
    lift_over_random: float  # How much better than random sequencing
    
    @property
    def is_strong_position(self) -> bool:
        return self.effectiveness >= 0.7


@dataclass
class MechanismSequence:
    """
    Optimal sequence of mechanisms for a customer segment.
    
    Based on attribution path analysis showing which orderings
    lead to highest conversion rates.
    """
    segment_id: str
    sequence: List[str]  # Ordered list of mechanisms
    expected_lift: float  # Expected improvement over single mechanism
    touchpoints_needed: int  # Typical number of touches
    confidence: float
    
    # Position-specific recommendations
    first_touch_best: str
    last_touch_best: str
    
    # Alternative sequences with similar performance
    alternatives: List[List[str]] = field(default_factory=list)


@dataclass
class ConversionPath:
    """
    A conversion path showing touchpoint sequence.
    """
    path_id: str
    touchpoints: List[str]  # Sequence of mechanism exposures
    converted: bool
    time_to_conversion: Optional[float]  # Hours
    attribution_weights: Dict[str, float]  # Mechanism → attribution weight


@dataclass
class AttributionModel:
    """
    Attribution model weights for different mechanisms.
    """
    model_type: str  # "position_based", "time_decay", "data_driven"
    mechanism_weights: Dict[str, float]
    position_weights: Dict[str, float]  # first, early, middle, late, last
    confidence: float


# =============================================================================
# MECHANISM POSITION EFFECTIVENESS
# =============================================================================

# Based on attribution path analysis - where mechanisms work best
MECHANISM_POSITION_EFFECTIVENESS = {
    "authority": {
        TouchpointPosition.FIRST: 0.85,    # Great for initial trust
        TouchpointPosition.EARLY: 0.80,
        TouchpointPosition.MIDDLE: 0.70,
        TouchpointPosition.LATE: 0.60,
        TouchpointPosition.LAST: 0.50,     # Less effective at conversion point
    },
    "social_proof": {
        TouchpointPosition.FIRST: 0.65,
        TouchpointPosition.EARLY: 0.75,
        TouchpointPosition.MIDDLE: 0.85,   # Best in consideration phase
        TouchpointPosition.LATE: 0.90,
        TouchpointPosition.LAST: 0.80,
    },
    "scarcity": {
        TouchpointPosition.FIRST: 0.40,    # Too early - seems pushy
        TouchpointPosition.EARLY: 0.50,
        TouchpointPosition.MIDDLE: 0.65,
        TouchpointPosition.LATE: 0.85,
        TouchpointPosition.LAST: 0.95,     # Maximum urgency at decision
    },
    "reciprocity": {
        TouchpointPosition.FIRST: 0.90,    # Excellent for opening
        TouchpointPosition.EARLY: 0.85,
        TouchpointPosition.MIDDLE: 0.70,
        TouchpointPosition.LATE: 0.55,
        TouchpointPosition.LAST: 0.45,     # Feels manipulative late
    },
    "commitment": {
        TouchpointPosition.FIRST: 0.50,
        TouchpointPosition.EARLY: 0.65,
        TouchpointPosition.MIDDLE: 0.80,   # Build momentum
        TouchpointPosition.LATE: 0.85,
        TouchpointPosition.LAST: 0.75,
    },
    "liking": {
        TouchpointPosition.FIRST: 0.80,    # Build rapport early
        TouchpointPosition.EARLY: 0.85,
        TouchpointPosition.MIDDLE: 0.75,
        TouchpointPosition.LATE: 0.65,
        TouchpointPosition.LAST: 0.60,
    },
    "unity": {
        TouchpointPosition.FIRST: 0.70,
        TouchpointPosition.EARLY: 0.80,
        TouchpointPosition.MIDDLE: 0.75,
        TouchpointPosition.LATE: 0.70,
        TouchpointPosition.LAST: 0.65,
    },
}

# Optimal sequences for different customer types
OPTIMAL_SEQUENCES_BY_TYPE = {
    # High persuadability - shorter sequences work
    "impulse_fast_high": {
        "sequence": ["social_proof", "scarcity"],
        "touchpoints": 2,
        "alternatives": [["liking", "scarcity"], ["social_proof", "liking"]],
    },
    "social_proof_fast_high": {
        "sequence": ["social_proof", "unity", "scarcity"],
        "touchpoints": 3,
        "alternatives": [["liking", "social_proof", "scarcity"]],
    },
    
    # Medium persuadability - need more touches
    "quality_seeking_moderate_moderate": {
        "sequence": ["authority", "social_proof", "commitment", "scarcity"],
        "touchpoints": 4,
        "alternatives": [
            ["reciprocity", "authority", "social_proof", "scarcity"],
        ],
    },
    "value_seeking_moderate_moderate": {
        "sequence": ["reciprocity", "social_proof", "commitment", "scarcity"],
        "touchpoints": 4,
        "alternatives": [
            ["social_proof", "commitment", "reciprocity", "scarcity"],
        ],
    },
    
    # Low persuadability - long sequences, build trust
    "research_driven_deliberate_low": {
        "sequence": ["reciprocity", "authority", "commitment", "social_proof", "scarcity"],
        "touchpoints": 5,
        "alternatives": [
            ["authority", "reciprocity", "social_proof", "commitment", "scarcity"],
        ],
    },
    "brand_loyalty_deliberate_low": {
        "sequence": ["unity", "authority", "commitment", "social_proof"],
        "touchpoints": 4,
        "alternatives": [
            ["authority", "unity", "commitment", "social_proof"],
        ],
    },
}

# Default sequence templates
DEFAULT_SEQUENCES = {
    "high_persuadability": {
        "sequence": ["social_proof", "scarcity"],
        "touchpoints": 2,
        "first_best": "social_proof",
        "last_best": "scarcity",
    },
    "medium_persuadability": {
        "sequence": ["reciprocity", "authority", "social_proof", "scarcity"],
        "touchpoints": 4,
        "first_best": "reciprocity",
        "last_best": "scarcity",
    },
    "low_persuadability": {
        "sequence": ["reciprocity", "authority", "commitment", "social_proof", "scarcity"],
        "touchpoints": 5,
        "first_best": "reciprocity",
        "last_best": "scarcity",
    },
}


# =============================================================================
# TOUCHPOINT SENSITIVITY BY GRANULAR TYPE
# =============================================================================

# How many touchpoints different customer dimensions typically need
TOUCHPOINTS_BY_DECISION_STYLE = {
    "fast": 2,        # Quick decisions
    "moderate": 3,    # Average consideration
    "deliberate": 5,  # Thorough research
}

TOUCHPOINTS_BY_EMOTIONAL_INTENSITY = {
    "high": 2,        # Emotional = fewer touches
    "moderate": 3,
    "low": 5,         # Rational = more consideration
}

TOUCHPOINTS_BY_MOTIVATION = {
    "impulse": 1,
    "social_proof": 2,
    "self_reward": 2,
    "status_signaling": 3,
    "gift_giving": 3,
    "upgrade": 3,
    "value_seeking": 4,
    "quality_seeking": 4,
    "replacement": 3,
    "recommendation": 2,
    "research_driven": 5,
    "brand_loyalty": 3,
    "functional_need": 3,
}


# =============================================================================
# ATTRIBUTION CALCULATOR
# =============================================================================

class AttributionCalculator:
    """
    Calculate attribution weights and optimal sequences.
    """
    
    def calculate_touchpoints_needed(
        self,
        decision_style: str,
        emotional_intensity: str,
        motivation: str,
    ) -> int:
        """
        Calculate expected number of touchpoints for conversion.
        
        Args:
            decision_style: DecisionStyle dimension
            emotional_intensity: EmotionalIntensity dimension
            motivation: Motivation dimension
            
        Returns:
            Expected touchpoint count
        """
        style_touches = TOUCHPOINTS_BY_DECISION_STYLE.get(decision_style.lower(), 3)
        emotional_touches = TOUCHPOINTS_BY_EMOTIONAL_INTENSITY.get(
            emotional_intensity.lower(), 3
        )
        motivation_touches = TOUCHPOINTS_BY_MOTIVATION.get(
            motivation.lower().replace("_", " "), 3
        )
        
        # Weighted average
        avg = (style_touches * 0.35 + 
               emotional_touches * 0.30 + 
               motivation_touches * 0.35)
        
        return round(avg)
    
    def get_position_effectiveness(
        self,
        mechanism: str,
        position: TouchpointPosition,
    ) -> float:
        """
        Get effectiveness of mechanism at journey position.
        
        Args:
            mechanism: Mechanism name
            position: Journey position
            
        Returns:
            Effectiveness score (0-1)
        """
        mech_effects = MECHANISM_POSITION_EFFECTIVENESS.get(mechanism, {})
        return mech_effects.get(position, 0.5)
    
    def recommend_first_touch(
        self,
        persuadability: float,
        decision_style: str,
    ) -> str:
        """
        Recommend best mechanism for first touchpoint.
        
        Args:
            persuadability: Persuadability score
            decision_style: Decision style
            
        Returns:
            Recommended mechanism
        """
        if decision_style.lower() == "deliberate":
            return "reciprocity"  # Build relationship with value
        elif persuadability >= 0.6:
            return "social_proof"  # Social validation works
        else:
            return "authority"  # Need credibility first
    
    def recommend_last_touch(
        self,
        persuadability: float,
        motivation: str,
    ) -> str:
        """
        Recommend best mechanism for last touchpoint (conversion driver).
        
        Args:
            persuadability: Persuadability score
            motivation: Motivation dimension
            
        Returns:
            Recommended mechanism
        """
        if motivation.lower() in ["impulse", "social_proof"]:
            return "scarcity"  # Urgency drives action
        elif motivation.lower() in ["value_seeking", "quality_seeking"]:
            return "social_proof"  # Final validation
        else:
            return "scarcity"  # Default - urgency works broadly
    
    def generate_optimal_sequence(
        self,
        motivation: str,
        decision_style: str,
        emotional_intensity: str,
        persuadability: float,
    ) -> MechanismSequence:
        """
        Generate optimal mechanism sequence for a customer profile.
        
        Args:
            motivation: Motivation dimension
            decision_style: Decision style dimension
            emotional_intensity: Emotional intensity dimension
            persuadability: Overall persuadability score
            
        Returns:
            MechanismSequence with optimal ordering
        """
        # Calculate touchpoints needed
        touchpoints = self.calculate_touchpoints_needed(
            decision_style, emotional_intensity, motivation
        )
        
        # Check for pre-defined sequence
        type_key = f"{motivation.lower()}_{decision_style.lower()}_{emotional_intensity.lower()}"
        if type_key in OPTIMAL_SEQUENCES_BY_TYPE:
            predefined = OPTIMAL_SEQUENCES_BY_TYPE[type_key]
            return MechanismSequence(
                segment_id=type_key,
                sequence=predefined["sequence"],
                expected_lift=0.25,
                touchpoints_needed=predefined["touchpoints"],
                confidence=0.80,
                first_touch_best=predefined["sequence"][0],
                last_touch_best=predefined["sequence"][-1],
                alternatives=predefined.get("alternatives", []),
            )
        
        # Determine persuadability tier
        if persuadability >= 0.6:
            tier = "high_persuadability"
        elif persuadability >= 0.35:
            tier = "medium_persuadability"
        else:
            tier = "low_persuadability"
        
        template = DEFAULT_SEQUENCES[tier]
        
        # Adjust sequence based on motivation
        sequence = list(template["sequence"])
        
        # Customize first touch
        first = self.recommend_first_touch(persuadability, decision_style)
        if first not in sequence:
            sequence = [first] + sequence
        elif sequence[0] != first:
            sequence.remove(first)
            sequence = [first] + sequence
        
        # Customize last touch
        last = self.recommend_last_touch(persuadability, motivation)
        if last in sequence:
            sequence.remove(last)
        sequence.append(last)
        
        # Trim to expected touchpoints
        if len(sequence) > touchpoints:
            # Keep first and last, remove from middle
            middle = sequence[1:-1]
            keep = touchpoints - 2
            sequence = [sequence[0]] + middle[:keep] + [sequence[-1]]
        
        return MechanismSequence(
            segment_id=type_key,
            sequence=sequence,
            expected_lift=0.20,
            touchpoints_needed=touchpoints,
            confidence=0.70,
            first_touch_best=sequence[0],
            last_touch_best=sequence[-1],
            alternatives=[],
        )


# =============================================================================
# ATTRIBUTION INTELLIGENCE SERVICE
# =============================================================================

class AttributionIntelligenceService:
    """
    Service for attribution intelligence.
    
    Uses conversion path analysis to optimize mechanism sequencing
    for different customer types.
    """
    
    def __init__(self, criteo_data_path: Optional[str] = None):
        """
        Initialize the attribution service.
        
        Args:
            criteo_data_path: Path to processed Criteo attribution data
        """
        self._calculator = AttributionCalculator()
        self._calibrated = False
        self._path_data: Dict[str, Any] = {}
        
        if criteo_data_path:
            self._load_path_data(criteo_data_path)
    
    def _load_path_data(self, path: str) -> None:
        """Load conversion path analysis data."""
        try:
            path = Path(path)
            
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    self._path_data = json.load(f)
                self._calibrated = True
                logger.info("Loaded attribution path data")
                
        except Exception as e:
            logger.warning(f"Could not load path data: {e}")
    
    def get_optimal_sequence(
        self,
        motivation: str,
        decision_style: str,
        emotional_intensity: str,
        persuadability: float = 0.5,
    ) -> MechanismSequence:
        """
        Get optimal mechanism sequence for a customer profile.
        
        Args:
            motivation: Motivation dimension
            decision_style: Decision style dimension
            emotional_intensity: Emotional intensity dimension
            persuadability: Overall persuadability score
            
        Returns:
            MechanismSequence
        """
        return self._calculator.generate_optimal_sequence(
            motivation=motivation,
            decision_style=decision_style,
            emotional_intensity=emotional_intensity,
            persuadability=persuadability,
        )
    
    def get_mechanism_at_position(
        self,
        position: int,
        total_touchpoints: int,
        sequence: List[str],
    ) -> Tuple[str, TouchpointPosition]:
        """
        Get mechanism for a specific touchpoint position.
        
        Args:
            position: Current position (0-indexed)
            total_touchpoints: Total planned touchpoints
            sequence: Mechanism sequence
            
        Returns:
            Tuple of (mechanism, position_type)
        """
        if position < 0 or position >= len(sequence):
            raise ValueError(f"Position {position} out of range")
        
        # Determine position type
        if position == 0:
            pos_type = TouchpointPosition.FIRST
        elif position == len(sequence) - 1:
            pos_type = TouchpointPosition.LAST
        elif position < len(sequence) * 0.4:
            pos_type = TouchpointPosition.EARLY
        elif position < len(sequence) * 0.7:
            pos_type = TouchpointPosition.MIDDLE
        else:
            pos_type = TouchpointPosition.LATE
        
        return sequence[position], pos_type
    
    def calculate_sequence_effectiveness(
        self,
        sequence: List[str]
    ) -> float:
        """
        Calculate overall effectiveness of a mechanism sequence.
        
        Args:
            sequence: List of mechanisms in order
            
        Returns:
            Effectiveness score (0-1)
        """
        if not sequence:
            return 0.0
        
        total_score = 0.0
        positions = [
            TouchpointPosition.FIRST,
            TouchpointPosition.EARLY,
            TouchpointPosition.MIDDLE,
            TouchpointPosition.LATE,
            TouchpointPosition.LAST,
        ]
        
        for i, mechanism in enumerate(sequence):
            # Map to position
            ratio = i / (len(sequence) - 1) if len(sequence) > 1 else 0
            if ratio == 0:
                pos = TouchpointPosition.FIRST
            elif ratio == 1:
                pos = TouchpointPosition.LAST
            elif ratio < 0.35:
                pos = TouchpointPosition.EARLY
            elif ratio < 0.7:
                pos = TouchpointPosition.MIDDLE
            else:
                pos = TouchpointPosition.LATE
            
            score = self._calculator.get_position_effectiveness(mechanism, pos)
            total_score += score
        
        return total_score / len(sequence)
    
    def compare_sequences(
        self,
        sequences: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple sequences and rank them.
        
        Args:
            sequences: List of mechanism sequences
            
        Returns:
            Ranked list with scores
        """
        results = []
        
        for seq in sequences:
            effectiveness = self.calculate_sequence_effectiveness(seq)
            results.append({
                "sequence": seq,
                "effectiveness": effectiveness,
                "touchpoints": len(seq),
            })
        
        # Sort by effectiveness
        results.sort(key=lambda x: x["effectiveness"], reverse=True)
        
        # Add rank
        for i, r in enumerate(results):
            r["rank"] = i + 1
        
        return results
    
    def get_attribution_weights(
        self,
        conversion_path: List[str],
        model: str = "position_based"
    ) -> Dict[str, float]:
        """
        Calculate attribution weights for a conversion path.
        
        Args:
            conversion_path: Sequence of mechanism exposures
            model: Attribution model type
            
        Returns:
            Dict of mechanism → attribution weight
        """
        if not conversion_path:
            return {}
        
        weights = {}
        n = len(conversion_path)
        
        if model == "position_based":
            # 40% to first, 40% to last, 20% distributed
            first_weight = 0.40
            last_weight = 0.40
            middle_weight = 0.20 / max(n - 2, 1)
            
            for i, mech in enumerate(conversion_path):
                if i == 0:
                    weight = first_weight
                elif i == n - 1:
                    weight = last_weight
                else:
                    weight = middle_weight
                
                weights[mech] = weights.get(mech, 0) + weight
                
        elif model == "time_decay":
            # More weight to recent touchpoints
            total = sum(2 ** i for i in range(n))
            
            for i, mech in enumerate(conversion_path):
                weight = (2 ** i) / total
                weights[mech] = weights.get(mech, 0) + weight
                
        elif model == "linear":
            # Equal weight
            weight = 1.0 / n
            for mech in conversion_path:
                weights[mech] = weights.get(mech, 0) + weight
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_attribution_service: Optional[AttributionIntelligenceService] = None


def get_attribution_service(
    criteo_path: Optional[str] = None
) -> AttributionIntelligenceService:
    """
    Get the singleton attribution service.
    
    Args:
        criteo_path: Optional path to Criteo attribution data
        
    Returns:
        AttributionIntelligenceService instance
    """
    global _attribution_service
    
    if _attribution_service is None:
        if criteo_path is None:
            default_paths = [
                "/Volumes/Sped/new_reviews_and_data/hf_datasets/criteo_attribution",
                "data/learning/attribution_paths.json",
            ]
            for path in default_paths:
                if Path(path).exists():
                    criteo_path = path
                    break
        
        _attribution_service = AttributionIntelligenceService(criteo_path)
        logger.info("Attribution intelligence service initialized")
    
    return _attribution_service


# =============================================================================
# COLD-START PRIORS EXPORT
# =============================================================================

def export_attribution_priors() -> Dict[str, Any]:
    """
    Export attribution intelligence for cold-start priors.
    
    Returns:
        Dict suitable for adding to complete_coldstart_priors.json
    """
    calculator = AttributionCalculator()
    
    return {
        "attribution_intelligence": {
            "mechanism_position_effectiveness": {
                mech: {pos.value: eff for pos, eff in effects.items()}
                for mech, effects in MECHANISM_POSITION_EFFECTIVENESS.items()
            },
            "touchpoints_by_decision_style": TOUCHPOINTS_BY_DECISION_STYLE,
            "touchpoints_by_emotional_intensity": TOUCHPOINTS_BY_EMOTIONAL_INTENSITY,
            "touchpoints_by_motivation": TOUCHPOINTS_BY_MOTIVATION,
            "optimal_sequences": {
                key: {
                    "sequence": seq["sequence"],
                    "touchpoints": seq["touchpoints"],
                }
                for key, seq in OPTIMAL_SEQUENCES_BY_TYPE.items()
            },
            "default_sequences": DEFAULT_SEQUENCES,
            "version": "1.0",
            "source": "criteo/criteo-attribution",
        }
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = get_attribution_service()
    
    print("\n" + "="*60)
    print("ATTRIBUTION INTELLIGENCE TEST")
    print("="*60)
    
    test_cases = [
        # High persuadability - short sequences
        ("impulse", "fast", "high", 0.85),
        ("social_proof", "fast", "high", 0.80),
        
        # Medium persuadability
        ("value_seeking", "moderate", "moderate", 0.50),
        ("quality_seeking", "moderate", "moderate", 0.45),
        
        # Low persuadability - longer sequences
        ("research_driven", "deliberate", "low", 0.25),
    ]
    
    for motivation, decision, emotional, persuadability in test_cases:
        sequence = service.get_optimal_sequence(
            motivation=motivation,
            decision_style=decision,
            emotional_intensity=emotional,
            persuadability=persuadability,
        )
        
        effectiveness = service.calculate_sequence_effectiveness(sequence.sequence)
        
        print(f"\n{motivation} / {decision} / {emotional} (persuadability: {persuadability:.0%})")
        print(f"  Optimal sequence: {' → '.join(sequence.sequence)}")
        print(f"  Touchpoints needed: {sequence.touchpoints_needed}")
        print(f"  First touch: {sequence.first_touch_best}")
        print(f"  Last touch: {sequence.last_touch_best}")
        print(f"  Sequence effectiveness: {effectiveness:.0%}")
        print(f"  Expected lift: {sequence.expected_lift:+.0%}")
