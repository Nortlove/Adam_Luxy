# =============================================================================
# ADAM Blackboard Zone 5: Learning Signals
# Location: adam/blackboard/models/zone5_learning.py
# =============================================================================

"""
ZONE 5: LEARNING SIGNALS

Aggregated learning signals for outcome attribution.

Contents:
- Component outputs
- Performance metrics
- Outcome attributions
- Signal routing

Access: Write by all components, read by Gradient Bridge + Meta-Learner.
TTL: 72 hours (for delayed attribution)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# COMPONENT SIGNAL
# =============================================================================

class SignalSource(str, Enum):
    """Sources of learning signals."""
    
    ATOM = "atom"
    SYNTHESIS = "synthesis"
    DECISION = "decision"
    OUTCOME = "outcome"
    META_LEARNER = "meta_learner"


class SignalPriority(str, Enum):
    """Priority for processing signals."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComponentSignal(BaseModel):
    """A learning signal from any component."""
    
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid4().hex[:12]}")
    
    # Source
    source: SignalSource
    source_component_id: str
    source_component_type: str
    
    # Target
    target_construct: str  # What to update (e.g., "mechanism_effectiveness", "trait_confidence")
    target_entity_id: Optional[str] = None  # Specific entity (e.g., mechanism_id)
    
    # Signal content
    signal_type: str  # e.g., "outcome", "confidence_update", "error"
    signal_value: float = Field(ge=-1.0, le=1.0)
    signal_direction: str = Field(default="positive")  # "positive", "negative", "neutral"
    
    # Context
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    decision_id: Optional[str] = None
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Priority
    priority: SignalPriority = Field(default=SignalPriority.MEDIUM)
    
    # Processing
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    processing_result: Optional[str] = None
    
    # Timestamp
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# OUTCOME SIGNAL
# =============================================================================

class OutcomeType(str, Enum):
    """Types of outcomes."""
    
    CONVERSION = "conversion"
    CLICK = "click"
    LISTEN_COMPLETE = "listen_complete"
    LISTEN_PARTIAL = "listen_partial"
    SKIP = "skip"
    NO_ACTION = "no_action"


class OutcomeSignal(BaseModel):
    """Signal from an observed outcome."""
    
    outcome_id: str = Field(default_factory=lambda: f"out_{uuid4().hex[:12]}")
    
    # Decision reference
    decision_id: str
    request_id: str
    user_id: str
    
    # Outcome
    outcome_type: OutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Timing
    decision_at: datetime
    outcome_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    delay_seconds: int = Field(default=0, ge=0)
    
    # Attribution
    attributed_mechanisms: Dict[str, float] = Field(default_factory=dict)
    primary_mechanism_id: Optional[str] = None
    
    # Context
    campaign_id: Optional[str] = None
    creative_id: Optional[str] = None
    
    # Confidence
    attribution_confidence: float = Field(ge=0.0, le=1.0, default=0.8)


# =============================================================================
# PERFORMANCE METRIC
# =============================================================================

class PerformanceMetric(BaseModel):
    """Performance metric for a component."""
    
    metric_id: str = Field(default_factory=lambda: f"met_{uuid4().hex[:8]}")
    
    # Component
    component_type: str
    component_id: str
    
    # Metric
    metric_name: str
    metric_value: float
    metric_unit: str = ""
    
    # Context
    request_id: Optional[str] = None
    
    # Timestamp
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# LEARNING SIGNAL AGGREGATOR (Zone 5)
# =============================================================================

class LearningSignalAggregator(BaseModel):
    """
    Zone 5: Aggregated learning signals.
    
    Collects signals from all components for the Gradient Bridge.
    """
    
    # Identity
    aggregator_id: str = Field(default_factory=lambda: f"z5_{uuid4().hex[:12]}")
    request_id: str
    decision_id: Optional[str] = None
    user_id: str
    
    # Lifecycle
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Component signals
    component_signals: List[ComponentSignal] = Field(default_factory=list)
    
    # Outcome signals
    outcome_signals: List[OutcomeSignal] = Field(default_factory=list)
    
    # Performance metrics
    performance_metrics: List[PerformanceMetric] = Field(default_factory=list)
    
    # Summary
    total_signals: int = Field(default=0, ge=0)
    signals_processed: int = Field(default=0, ge=0)
    signals_pending: int = Field(default=0, ge=0)
    
    # Has outcome
    has_outcome: bool = Field(default=False)
    final_outcome: Optional[OutcomeType] = None
    final_outcome_value: Optional[float] = None
    
    # Corpus Fusion Tracking — records which corpus priors and calibrations
    # were active during this decision, enabling post-hoc analysis of
    # how corpus intelligence affects outcomes.
    corpus_priors_active: Dict[str, float] = Field(
        default_factory=dict,
        description="Mechanism priors from corpus that were active during decision"
    )
    corpus_prior_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Confidence level of the corpus prior used"
    )
    corpus_evidence_count: int = Field(
        default=0, ge=0,
        description="Number of reviews backing the corpus prior"
    )
    corpus_platform_calibration: Dict[str, float] = Field(
        default_factory=dict,
        description="Platform-specific calibration factors active during decision"
    )
    corpus_creative_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Creative pattern constraints from corpus"
    )
    corpus_transfer_sources: List[str] = Field(
        default_factory=list,
        description="Categories used for cross-category transfer"
    )
    
    def add_signal(self, signal: ComponentSignal) -> None:
        """Add a component signal."""
        self.component_signals.append(signal)
        self.total_signals += 1
        self.signals_pending += 1
    
    def add_outcome(self, outcome: OutcomeSignal) -> None:
        """Add an outcome signal."""
        self.outcome_signals.append(outcome)
        self.has_outcome = True
        self.final_outcome = outcome.outcome_type
        self.final_outcome_value = outcome.outcome_value
    
    def add_metric(self, metric: PerformanceMetric) -> None:
        """Add a performance metric."""
        self.performance_metrics.append(metric)
    
    def mark_signal_processed(self, signal_id: str, result: str) -> None:
        """Mark a signal as processed."""
        for signal in self.component_signals:
            if signal.signal_id == signal_id:
                signal.processed = True
                signal.processed_at = datetime.now(timezone.utc)
                signal.processing_result = result
                self.signals_processed += 1
                self.signals_pending -= 1
                break
    
    def get_pending_signals(self) -> List[ComponentSignal]:
        """Get all pending signals."""
        return [s for s in self.component_signals if not s.processed]
    
    def get_signals_by_target(self, target_construct: str) -> List[ComponentSignal]:
        """Get signals for a specific target construct."""
        return [
            s for s in self.component_signals
            if s.target_construct == target_construct
        ]
    
    def get_mechanism_signals(self, mechanism_id: str) -> List[ComponentSignal]:
        """Get signals for a specific mechanism."""
        return [
            s for s in self.component_signals
            if s.target_entity_id == mechanism_id
        ]
