# =============================================================================
# ADAM v3: Meta-Cognitive Reasoning Engine
# Location: src/v3/metacognitive/reasoning.py
# =============================================================================

"""
META-COGNITIVE REASONING ENGINE

"Thinking about thinking" - monitors and optimizes ADAM's own reasoning.

Key capabilities:
- Reasoning quality assessment
- Confidence calibration
- Strategy selection
- Learning from mistakes
- Uncertainty quantification
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import logging
import uuid
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies."""
    FAST_HEURISTIC = "fast_heuristic"       # Quick pattern matching
    DELIBERATE = "deliberate"                # Careful analysis
    BAYESIAN = "bayesian"                    # Probabilistic update
    ANALOGICAL = "analogical"                # Similarity-based
    CAUSAL = "causal"                        # Cause-effect reasoning
    ENSEMBLE = "ensemble"                    # Combine multiple strategies


class ConfidenceLevel(str, Enum):
    """Calibrated confidence levels."""
    VERY_HIGH = "very_high"     # >90% accurate historically
    HIGH = "high"               # 75-90% accurate
    MODERATE = "moderate"       # 50-75% accurate
    LOW = "low"                 # 25-50% accurate
    VERY_LOW = "very_low"       # <25% accurate


class ReasoningTrace(BaseModel):
    """Trace of a reasoning process."""
    
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    decision_id: str
    user_id: Optional[str] = None
    
    # Strategy used
    strategy: ReasoningStrategy
    
    # Input summary
    input_sources: List[str] = Field(default_factory=list)
    input_signals_count: int = 0
    
    # Output
    conclusion: str = ""
    raw_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    calibrated_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    
    # Reasoning steps
    steps: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    
    # Performance
    reasoning_time_ms: float = 0.0
    
    # Validation
    outcome_known: bool = False
    outcome_correct: Optional[bool] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CalibrationBucket(BaseModel):
    """Bucket for confidence calibration."""
    
    confidence_min: float
    confidence_max: float
    predictions: int = 0
    correct_predictions: int = 0
    
    @property
    def accuracy(self) -> float:
        """Actual accuracy in this bucket."""
        if self.predictions == 0:
            return 0.5
        return self.correct_predictions / self.predictions
    
    @property
    def expected_confidence(self) -> float:
        """Expected (claimed) confidence."""
        return (self.confidence_min + self.confidence_max) / 2
    
    @property
    def calibration_error(self) -> float:
        """Difference between claimed and actual accuracy."""
        return self.expected_confidence - self.accuracy


class StrategyPerformance(BaseModel):
    """Performance metrics for a reasoning strategy."""
    
    strategy: ReasoningStrategy
    uses: int = 0
    correct: int = 0
    avg_confidence: float = 0.5
    avg_time_ms: float = 0.0
    
    @property
    def accuracy(self) -> float:
        """Strategy accuracy."""
        if self.uses == 0:
            return 0.5
        return self.correct / self.uses


class MetaCognitiveEngine:
    """
    Monitors and optimizes ADAM's reasoning processes.
    
    Tracks:
    - Reasoning quality across strategies
    - Confidence calibration
    - Strategy effectiveness by context
    - Learning from outcomes
    """
    
    # Calibration buckets (10 buckets from 0-100%)
    CALIBRATION_BUCKETS = 10
    
    def __init__(self):
        # Reasoning traces
        self._traces: Dict[str, ReasoningTrace] = {}
        
        # Calibration
        self._calibration_buckets: List[CalibrationBucket] = [
            CalibrationBucket(
                confidence_min=i / self.CALIBRATION_BUCKETS,
                confidence_max=(i + 1) / self.CALIBRATION_BUCKETS,
            )
            for i in range(self.CALIBRATION_BUCKETS)
        ]
        
        # Strategy performance
        self._strategy_performance: Dict[ReasoningStrategy, StrategyPerformance] = {
            strategy: StrategyPerformance(strategy=strategy)
            for strategy in ReasoningStrategy
        }
        
        # Context-specific performance
        self._context_performance: Dict[str, Dict[ReasoningStrategy, StrategyPerformance]] = defaultdict(
            lambda: {s: StrategyPerformance(strategy=s) for s in ReasoningStrategy}
        )
        
        # Statistics
        self._total_reasonings = 0
        self._outcomes_received = 0
    
    async def trace_reasoning(
        self,
        decision_id: str,
        strategy: ReasoningStrategy,
        input_sources: List[str],
        conclusion: str,
        raw_confidence: float,
        steps: List[str],
        uncertainties: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
        reasoning_time_ms: float = 0.0,
        user_id: Optional[str] = None,
    ) -> ReasoningTrace:
        """
        Record a reasoning trace.
        
        Args:
            decision_id: ID of decision being made
            strategy: Reasoning strategy used
            input_sources: Intelligence sources used
            conclusion: Reasoning conclusion
            raw_confidence: Raw confidence before calibration
            steps: Reasoning steps taken
            uncertainties: Known uncertainties
            assumptions: Assumptions made
            reasoning_time_ms: Time taken
            user_id: User being reasoned about
            
        Returns:
            Completed trace with calibrated confidence
        """
        self._total_reasonings += 1
        
        # Calibrate confidence
        calibrated = self._calibrate_confidence(raw_confidence, strategy)
        confidence_level = self._confidence_to_level(calibrated)
        
        trace = ReasoningTrace(
            decision_id=decision_id,
            user_id=user_id,
            strategy=strategy,
            input_sources=input_sources,
            input_signals_count=len(input_sources),
            conclusion=conclusion,
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            confidence_level=confidence_level,
            steps=steps,
            uncertainties=uncertainties or [],
            assumptions=assumptions or [],
            reasoning_time_ms=reasoning_time_ms,
        )
        
        self._traces[trace.trace_id] = trace
        
        # Update strategy stats (partial - will complete with outcome)
        perf = self._strategy_performance[strategy]
        perf.uses += 1
        perf.avg_time_ms = (
            (perf.avg_time_ms * (perf.uses - 1) + reasoning_time_ms) / perf.uses
        )
        perf.avg_confidence = (
            (perf.avg_confidence * (perf.uses - 1) + calibrated) / perf.uses
        )
        
        return trace
    
    def _calibrate_confidence(
        self,
        raw_confidence: float,
        strategy: ReasoningStrategy
    ) -> float:
        """
        Calibrate raw confidence based on historical accuracy.
        
        Adjusts overconfidence or underconfidence based on
        past performance in this confidence range.
        """
        # Find appropriate bucket
        bucket_idx = min(
            self.CALIBRATION_BUCKETS - 1,
            int(raw_confidence * self.CALIBRATION_BUCKETS)
        )
        bucket = self._calibration_buckets[bucket_idx]
        
        # If we have enough data, adjust
        if bucket.predictions >= 20:
            # Calibration factor
            if bucket.expected_confidence > 0:
                calibration = bucket.accuracy / bucket.expected_confidence
            else:
                calibration = 1.0
            
            calibrated = raw_confidence * calibration
            calibrated = max(0.0, min(1.0, calibrated))
        else:
            # Not enough data, use conservative estimate
            calibrated = raw_confidence * 0.9  # Slight underconfidence
        
        return calibrated
    
    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to calibrated level."""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.25:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW
    
    async def record_outcome(
        self,
        trace_id: str,
        correct: bool
    ) -> None:
        """
        Record the outcome of a reasoning trace.
        
        Args:
            trace_id: ID of trace to update
            correct: Whether reasoning was correct
        """
        if trace_id not in self._traces:
            return
        
        trace = self._traces[trace_id]
        trace.outcome_known = True
        trace.outcome_correct = correct
        self._outcomes_received += 1
        
        # Update calibration bucket
        bucket_idx = min(
            self.CALIBRATION_BUCKETS - 1,
            int(trace.calibrated_confidence * self.CALIBRATION_BUCKETS)
        )
        bucket = self._calibration_buckets[bucket_idx]
        bucket.predictions += 1
        if correct:
            bucket.correct_predictions += 1
        
        # Update strategy performance
        perf = self._strategy_performance[trace.strategy]
        if correct:
            perf.correct += 1
    
    async def select_strategy(
        self,
        context: Dict[str, Any],
        available_time_ms: float = 100.0,
        required_confidence: float = 0.6
    ) -> ReasoningStrategy:
        """
        Select optimal reasoning strategy for context.
        
        Args:
            context: Current decision context
            available_time_ms: Time budget
            required_confidence: Minimum confidence needed
            
        Returns:
            Recommended strategy
        """
        candidates = []
        
        for strategy, perf in self._strategy_performance.items():
            if perf.uses < 10:
                # Not enough data, include as candidate
                candidates.append((strategy, 0.5, perf.avg_time_ms or 50))
                continue
            
            # Check time constraint
            if perf.avg_time_ms > available_time_ms * 1.5:
                continue  # Too slow
            
            # Check confidence constraint
            if perf.avg_confidence < required_confidence * 0.8:
                continue  # Usually too uncertain
            
            candidates.append((strategy, perf.accuracy, perf.avg_time_ms))
        
        if not candidates:
            return ReasoningStrategy.FAST_HEURISTIC
        
        # Score candidates (balance accuracy and speed)
        def score(candidate):
            strategy, accuracy, time_ms = candidate
            time_factor = 1.0 - (time_ms / max(available_time_ms * 2, 1))
            return accuracy * 0.7 + time_factor * 0.3
        
        best = max(candidates, key=score)
        return best[0]
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Get confidence calibration report."""
        buckets_data = []
        total_error = 0.0
        
        for bucket in self._calibration_buckets:
            bucket_data = {
                "range": f"{bucket.confidence_min:.0%}-{bucket.confidence_max:.0%}",
                "predictions": bucket.predictions,
                "accuracy": f"{bucket.accuracy:.1%}",
                "expected": f"{bucket.expected_confidence:.1%}",
                "error": f"{bucket.calibration_error:+.1%}",
            }
            buckets_data.append(bucket_data)
            
            if bucket.predictions > 0:
                total_error += abs(bucket.calibration_error) * bucket.predictions
        
        total_predictions = sum(b.predictions for b in self._calibration_buckets)
        
        return {
            "buckets": buckets_data,
            "total_predictions": total_predictions,
            "average_calibration_error": (
                total_error / max(1, total_predictions)
            ),
            "is_well_calibrated": (
                total_error / max(1, total_predictions) < 0.1
            ),
        }
    
    def get_strategy_report(self) -> Dict[str, Any]:
        """Get strategy performance report."""
        strategies = []
        
        for strategy, perf in self._strategy_performance.items():
            if perf.uses > 0:
                strategies.append({
                    "strategy": strategy.value,
                    "uses": perf.uses,
                    "accuracy": f"{perf.accuracy:.1%}",
                    "avg_confidence": f"{perf.avg_confidence:.1%}",
                    "avg_time_ms": f"{perf.avg_time_ms:.1f}",
                })
        
        return {
            "strategies": strategies,
            "best_accuracy": max(
                (s for s in self._strategy_performance.values() if s.uses >= 10),
                key=lambda s: s.accuracy,
                default=None
            ),
            "fastest": min(
                (s for s in self._strategy_performance.values() if s.uses >= 10),
                key=lambda s: s.avg_time_ms,
                default=None
            ),
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_reasonings": self._total_reasonings,
            "outcomes_received": self._outcomes_received,
            "outcome_rate": self._outcomes_received / max(1, self._total_reasonings),
            "traces_stored": len(self._traces),
        }


# Singleton instance
_engine: Optional[MetaCognitiveEngine] = None


def get_metacognitive_engine() -> MetaCognitiveEngine:
    """Get singleton Meta-Cognitive Engine."""
    global _engine
    if _engine is None:
        _engine = MetaCognitiveEngine()
    return _engine
