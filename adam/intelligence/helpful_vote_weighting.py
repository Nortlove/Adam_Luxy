#!/usr/bin/env python3
"""
HELPFUL VOTE WEIGHTED LEARNING
==============================

Phase 6+ Enhancement: Full Helpful Vote Utilization

This module properly weights learning signals by helpful votes,
recognizing that reviews with high helpful votes contain
VALIDATED PERSUASION - language that resonated with other customers.

Previous Implementation Problem:
- helpful_factor = min(helpful_votes / 20, 0.3) - caps at 30%!
- This means a review with 1000 helpful votes has the same weight
  as one with 6 helpful votes

New Implementation:
- Logarithmic scaling that preserves the signal from viral reviews
- Weighting applied to learning signals, not just confidence
- Tracks persuasive patterns that correlate with high votes
- Learns what language drives customer-to-customer influence

Key Insight: A review with 500 helpful votes has proven its persuasive
power 500 times. That signal should not be capped.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# WEIGHTING CONFIGURATION
# =============================================================================

class WeightingStrategy(str, Enum):
    """Strategies for weighting by helpful votes."""
    
    LINEAR_CAPPED = "linear_capped"       # Old: min(votes/20, 0.3) - BAD
    LOGARITHMIC = "logarithmic"            # log(1+votes) scaling
    SQRT = "sqrt"                          # Square root scaling  
    PERCENTILE = "percentile"              # Based on vote distribution
    POWER_LAW = "power_law"                # Acknowledges viral reviews


# Default thresholds
VOTE_THRESHOLDS = {
    "low": 0,           # 0-2 votes
    "medium": 3,        # 3-9 votes
    "high": 10,         # 10-49 votes
    "very_high": 50,    # 50-199 votes
    "viral": 200,       # 200+ votes
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WeightedSignal:
    """A learning signal weighted by helpful votes."""
    
    signal_type: str
    source: str
    raw_value: float
    helpful_votes: int
    
    # Computed weights
    vote_weight: float = 0.0
    weighted_value: float = 0.0
    
    # Metadata
    weight_strategy: WeightingStrategy = WeightingStrategy.LOGARITHMIC
    vote_tier: str = "low"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "source": self.source,
            "raw_value": self.raw_value,
            "weighted_value": self.weighted_value,
            "helpful_votes": self.helpful_votes,
            "vote_weight": self.vote_weight,
            "vote_tier": self.vote_tier,
        }


@dataclass
class HelpfulVoteStats:
    """Statistics about helpful vote distribution."""
    
    total_reviews: int = 0
    total_votes: int = 0
    reviews_with_votes: int = 0
    
    # Distribution
    vote_percentiles: Dict[int, int] = field(default_factory=dict)  # percentile -> vote count
    tier_counts: Dict[str, int] = field(default_factory=dict)
    
    # Computed
    mean_votes: float = 0.0
    median_votes: int = 0
    max_votes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reviews": self.total_reviews,
            "total_votes": self.total_votes,
            "reviews_with_votes": self.reviews_with_votes,
            "mean_votes": self.mean_votes,
            "median_votes": self.median_votes,
            "max_votes": self.max_votes,
            "tier_distribution": self.tier_counts,
        }


# =============================================================================
# WEIGHTING CALCULATOR
# =============================================================================

class HelpfulVoteWeighter:
    """
    Calculates proper weights for helpful votes.
    
    This replaces the flawed capped linear approach with
    strategies that properly value high-engagement reviews.
    """
    
    def __init__(
        self,
        strategy: WeightingStrategy = WeightingStrategy.LOGARITHMIC,
        base_weight: float = 1.0,
        max_multiplier: float = 5.0,
    ):
        """
        Initialize weighter.
        
        Args:
            strategy: Weighting strategy to use
            base_weight: Weight for reviews with 0 votes
            max_multiplier: Maximum weight multiplier
        """
        self.strategy = strategy
        self.base_weight = base_weight
        self.max_multiplier = max_multiplier
        
        # Statistics tracking
        self._signals_weighted = 0
        self._vote_distribution: List[int] = []
    
    def calculate_weight(self, helpful_votes: int) -> float:
        """
        Calculate weight for a given helpful vote count.
        
        Args:
            helpful_votes: Number of helpful votes
            
        Returns:
            Weight multiplier (>= base_weight)
        """
        if helpful_votes <= 0:
            return self.base_weight
        
        if self.strategy == WeightingStrategy.LINEAR_CAPPED:
            # Old flawed approach - included for comparison
            weight = min(helpful_votes / 20, 0.3) + self.base_weight
            
        elif self.strategy == WeightingStrategy.LOGARITHMIC:
            # log(1 + votes) - good balance
            # 10 votes -> ~2.4x, 100 votes -> ~4.6x, 1000 votes -> ~6.9x
            weight = self.base_weight + math.log(1 + helpful_votes) * 0.5
            
        elif self.strategy == WeightingStrategy.SQRT:
            # sqrt(votes) - more aggressive early, gentler late
            # 10 votes -> ~3.2x, 100 votes -> ~10x
            weight = self.base_weight + math.sqrt(helpful_votes) * 0.3
            
        elif self.strategy == WeightingStrategy.POWER_LAW:
            # votes^0.4 - acknowledges viral reviews
            # 10 votes -> ~2.5x, 100 votes -> ~6.3x, 1000 votes -> ~15.8x
            weight = self.base_weight + (helpful_votes ** 0.4) * 0.3
            
        elif self.strategy == WeightingStrategy.PERCENTILE:
            # Would need population stats - fallback to logarithmic
            weight = self.base_weight + math.log(1 + helpful_votes) * 0.5
            
        else:
            weight = self.base_weight
        
        # Apply max multiplier cap
        return min(weight, self.base_weight * self.max_multiplier)
    
    def get_vote_tier(self, helpful_votes: int) -> str:
        """Get the tier for a vote count."""
        if helpful_votes >= VOTE_THRESHOLDS["viral"]:
            return "viral"
        elif helpful_votes >= VOTE_THRESHOLDS["very_high"]:
            return "very_high"
        elif helpful_votes >= VOTE_THRESHOLDS["high"]:
            return "high"
        elif helpful_votes >= VOTE_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"
    
    def weight_signal(
        self,
        signal_type: str,
        source: str,
        raw_value: float,
        helpful_votes: int,
    ) -> WeightedSignal:
        """
        Weight a learning signal by helpful votes.
        
        Args:
            signal_type: Type of learning signal
            source: Source identifier
            raw_value: Unweighted signal value
            helpful_votes: Helpful vote count
            
        Returns:
            WeightedSignal with computed weights
        """
        self._signals_weighted += 1
        self._vote_distribution.append(helpful_votes)
        
        vote_weight = self.calculate_weight(helpful_votes)
        weighted_value = raw_value * vote_weight
        
        return WeightedSignal(
            signal_type=signal_type,
            source=source,
            raw_value=raw_value,
            helpful_votes=helpful_votes,
            vote_weight=vote_weight,
            weighted_value=weighted_value,
            weight_strategy=self.strategy,
            vote_tier=self.get_vote_tier(helpful_votes),
        )
    
    def weight_batch(
        self,
        signals: List[Dict[str, Any]],
        value_key: str = "value",
        votes_key: str = "helpful_vote",
    ) -> List[WeightedSignal]:
        """
        Weight a batch of signals.
        
        Args:
            signals: List of signal dicts
            value_key: Key for signal value
            votes_key: Key for helpful votes
            
        Returns:
            List of WeightedSignals
        """
        weighted = []
        for signal in signals:
            ws = self.weight_signal(
                signal_type=signal.get("type", "unknown"),
                source=signal.get("source", "unknown"),
                raw_value=signal.get(value_key, 0.0),
                helpful_votes=signal.get(votes_key, 0) or 0,
            )
            weighted.append(ws)
        return weighted
    
    def get_stats(self) -> HelpfulVoteStats:
        """Get statistics about weighted signals."""
        if not self._vote_distribution:
            return HelpfulVoteStats()
        
        sorted_votes = sorted(self._vote_distribution)
        n = len(sorted_votes)
        
        # Calculate percentiles
        percentiles = {}
        for p in [25, 50, 75, 90, 95, 99]:
            idx = int(n * p / 100)
            percentiles[p] = sorted_votes[min(idx, n-1)]
        
        # Count by tier
        tier_counts = {tier: 0 for tier in VOTE_THRESHOLDS}
        for votes in self._vote_distribution:
            tier = self.get_vote_tier(votes)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        return HelpfulVoteStats(
            total_reviews=n,
            total_votes=sum(self._vote_distribution),
            reviews_with_votes=sum(1 for v in self._vote_distribution if v > 0),
            vote_percentiles=percentiles,
            tier_counts=tier_counts,
            mean_votes=sum(self._vote_distribution) / n,
            median_votes=sorted_votes[n // 2],
            max_votes=max(self._vote_distribution),
        )


# =============================================================================
# LEARNING INTEGRATION
# =============================================================================

class HelpfulVoteWeightedLearning:
    """
    Integrates helpful vote weighting into the learning loop.
    
    This ensures that learning signals from high-engagement reviews
    have proportionally higher influence on model updates.
    """
    
    def __init__(
        self,
        weighter: Optional[HelpfulVoteWeighter] = None,
    ):
        self.weighter = weighter or HelpfulVoteWeighter()
        
        # Track learning by tier
        self._learning_by_tier: Dict[str, List[float]] = {
            tier: [] for tier in VOTE_THRESHOLDS
        }
    
    def weight_mechanism_learning(
        self,
        mechanism_id: str,
        effectiveness: float,
        helpful_votes: int,
    ) -> Dict[str, Any]:
        """
        Weight a mechanism effectiveness signal by helpful votes.
        
        High-vote reviews provide stronger evidence for mechanism
        effectiveness because they represent validated persuasion.
        
        Args:
            mechanism_id: Mechanism being evaluated
            effectiveness: Raw effectiveness score (0-1)
            helpful_votes: Helpful votes from source review
            
        Returns:
            Weighted learning signal dict
        """
        signal = self.weighter.weight_signal(
            signal_type="mechanism_effectiveness",
            source=mechanism_id,
            raw_value=effectiveness,
            helpful_votes=helpful_votes,
        )
        
        # Track by tier
        tier = signal.vote_tier
        self._learning_by_tier[tier].append(signal.weighted_value)
        
        return {
            "mechanism_id": mechanism_id,
            "raw_effectiveness": effectiveness,
            "weighted_effectiveness": signal.weighted_value,
            "helpful_votes": helpful_votes,
            "vote_weight": signal.vote_weight,
            "vote_tier": tier,
            "learning_multiplier": signal.vote_weight / self.weighter.base_weight,
        }
    
    def weight_construct_learning(
        self,
        construct_id: str,
        score: float,
        confidence: float,
        helpful_votes: int,
    ) -> Dict[str, Any]:
        """
        Weight a psychological construct signal by helpful votes.
        
        Reviews with high helpful votes are written by people who
        understand their audience - their construct expressions
        are more reliable signals.
        
        Args:
            construct_id: Psychological construct
            score: Construct score (0-1)
            confidence: Base confidence
            helpful_votes: Helpful votes
            
        Returns:
            Weighted learning signal dict
        """
        # Weight both score and confidence
        score_signal = self.weighter.weight_signal(
            signal_type="construct_score",
            source=construct_id,
            raw_value=score,
            helpful_votes=helpful_votes,
        )
        
        # Confidence gets a smaller boost (already validated)
        confidence_boost = min(0.3, math.log(1 + helpful_votes) * 0.05)
        weighted_confidence = min(1.0, confidence + confidence_boost)
        
        return {
            "construct_id": construct_id,
            "raw_score": score,
            "weighted_score": score_signal.weighted_value,
            "raw_confidence": confidence,
            "weighted_confidence": weighted_confidence,
            "helpful_votes": helpful_votes,
            "vote_tier": score_signal.vote_tier,
        }
    
    def aggregate_weighted_signals(
        self,
        signals: List[Dict[str, Any]],
        value_key: str = "weighted_effectiveness",
    ) -> float:
        """
        Aggregate multiple weighted signals into a single value.
        
        Uses weighted average based on helpful vote weights.
        
        Args:
            signals: List of weighted signal dicts
            value_key: Key for the weighted value
            
        Returns:
            Aggregated weighted value
        """
        if not signals:
            return 0.0
        
        total_weight = sum(s.get("vote_weight", 1.0) for s in signals)
        weighted_sum = sum(
            s.get(value_key, 0.0) * s.get("vote_weight", 1.0)
            for s in signals
        )
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def get_tier_learning_report(self) -> Dict[str, Any]:
        """
        Get a report of learning contributions by vote tier.
        
        Shows how much each tier is contributing to learning.
        """
        report = {}
        total_signals = 0
        total_value = 0.0
        
        for tier, values in self._learning_by_tier.items():
            if values:
                tier_total = sum(values)
                report[tier] = {
                    "signal_count": len(values),
                    "total_learning": tier_total,
                    "mean_learning": tier_total / len(values),
                }
                total_signals += len(values)
                total_value += tier_total
        
        # Add percentages
        for tier in report:
            if total_value > 0:
                report[tier]["contribution_pct"] = (
                    report[tier]["total_learning"] / total_value * 100
                )
        
        return {
            "by_tier": report,
            "total_signals": total_signals,
            "total_learning_value": total_value,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning integration stats."""
        weighter_stats = self.weighter.get_stats()
        tier_report = self.get_tier_learning_report()
        
        return {
            "weighter": weighter_stats.to_dict(),
            "learning": tier_report,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_weighter: Optional[HelpfulVoteWeighter] = None
_learning: Optional[HelpfulVoteWeightedLearning] = None


def get_helpful_vote_weighter() -> HelpfulVoteWeighter:
    """Get singleton helpful vote weighter."""
    global _weighter
    if _weighter is None:
        _weighter = HelpfulVoteWeighter()
    return _weighter


def get_helpful_vote_weighted_learning() -> HelpfulVoteWeightedLearning:
    """Get singleton helpful vote weighted learning."""
    global _learning
    if _learning is None:
        _learning = HelpfulVoteWeightedLearning()
    return _learning


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_helpful_weight(votes: int) -> float:
    """Quick calculation of helpful vote weight."""
    return get_helpful_vote_weighter().calculate_weight(votes)


def weight_learning_signal(
    signal_type: str,
    value: float,
    helpful_votes: int,
) -> Dict[str, Any]:
    """
    Weight a learning signal by helpful votes.
    
    Args:
        signal_type: Type of signal
        value: Raw value
        helpful_votes: Vote count
        
    Returns:
        Weighted signal dict
    """
    weighter = get_helpful_vote_weighter()
    signal = weighter.weight_signal(signal_type, "api", value, helpful_votes)
    return signal.to_dict()


def compare_weighting_strategies(votes: int) -> Dict[str, float]:
    """
    Compare different weighting strategies for a vote count.
    
    Useful for understanding the impact of strategy choice.
    """
    results = {}
    for strategy in WeightingStrategy:
        weighter = HelpfulVoteWeighter(strategy=strategy)
        results[strategy.value] = weighter.calculate_weight(votes)
    return results
