# =============================================================================
# ADAM Universal Learning Interface
# Location: adam/core/learning/universal_learning_interface.py
# =============================================================================

"""
UNIVERSAL LEARNING INTERFACE

This is the contract that EVERY ADAM component must implement to participate
in the system's collective intelligence. Without this interface, a component
is a dead node that takes but never gives back.

The interface enforces:
1. Every component MUST learn from outcomes
2. Every component MUST emit learning signals for others
3. Every component MUST report its contribution to decisions
4. Every component MUST declare what it can learn from

This is not optional. This is what makes ADAM a living system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import uuid
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# LEARNING SIGNAL TYPES
# =============================================================================

class LearningSignalType(str, Enum):
    """
    Complete taxonomy of learning signals in ADAM.
    
    Every signal type represents a distinct form of knowledge that
    can flow between components.
    """
    
    # =========================================================================
    # OUTCOME SIGNALS (What happened)
    # =========================================================================
    OUTCOME_CONVERSION = "outcome_conversion"      # User converted
    OUTCOME_CLICK = "outcome_click"                # User clicked
    OUTCOME_SKIP = "outcome_skip"                  # User skipped/ignored
    OUTCOME_ENGAGEMENT = "outcome_engagement"      # User engaged (time, scroll)
    OUTCOME_REJECTION = "outcome_rejection"        # User rejected/bounced
    
    # =========================================================================
    # ATTRIBUTION SIGNALS (What contributed)
    # =========================================================================
    CREDIT_ASSIGNED = "credit_assigned"            # Credit to component
    MECHANISM_ATTRIBUTED = "mechanism_attributed"  # Credit to mechanism
    ATOM_ATTRIBUTED = "atom_attributed"            # Credit to specific atom
    SIGNAL_ATTRIBUTED = "signal_attributed"        # Credit to input signal
    
    # =========================================================================
    # PRIOR UPDATE SIGNALS (What to believe now)
    # =========================================================================
    PRIOR_UPDATED = "prior_updated"                # Thompson sampling update
    TRAIT_CONFIDENCE_UPDATED = "trait_confidence"  # User trait confidence
    MECHANISM_EFFECTIVENESS_UPDATED = "mechanism_effectiveness"
    STATE_TRANSITION_LEARNED = "state_transition"  # Journey state learning
    
    # =========================================================================
    # SIGNAL QUALITY SIGNALS (How good are inputs)
    # =========================================================================
    SIGNAL_ACCURACY_VALIDATED = "signal_accuracy"  # Signal predicted correctly
    SIGNAL_QUALITY_UPDATED = "signal_quality"      # Signal source quality
    AUDIO_FEATURE_VALIDATED = "audio_feature"      # Audio signal accuracy
    BEHAVIORAL_PATTERN_VALIDATED = "behavioral_pattern"
    
    # =========================================================================
    # CONTENT SIGNALS (What content works)
    # =========================================================================
    COPY_EFFECTIVENESS = "copy_effectiveness"      # Copy template worked
    CREATIVE_MATCHED = "creative_matched"          # Creative matching success
    BRAND_MECHANISM_LEARNED = "brand_mechanism"    # Brand × mechanism
    
    # =========================================================================
    # COMPETITIVE SIGNALS (What beats competitors)
    # =========================================================================
    COMPETITIVE_WIN = "competitive_win"            # Won against competitor
    COMPETITIVE_LOSS = "competitive_loss"          # Lost to competitor
    POSITIONING_EFFECTIVE = "positioning"          # Positioning worked
    
    # =========================================================================
    # EMERGENCE SIGNALS (What the system discovered)
    # =========================================================================
    NOVEL_CONSTRUCT_DISCOVERED = "novel_construct"
    CAUSAL_EDGE_DISCOVERED = "causal_edge"
    THEORY_BOUNDARY_FOUND = "theory_boundary"
    COHORT_SELF_ORGANIZED = "cohort_self_organized"
    PATTERN_EMERGED = "pattern_emerged"
    
    # =========================================================================
    # QUALITY SIGNALS (How well is the system working)
    # =========================================================================
    PREDICTION_VALIDATED = "prediction_validated"
    PREDICTION_FAILED = "prediction_failed"
    CALIBRATION_UPDATED = "calibration"
    DRIFT_DETECTED = "drift_detected"


class LearningSignalPriority(int, Enum):
    """Priority levels for learning signals."""
    LOW = 1          # Background learning, can be batched
    NORMAL = 2       # Standard learning, process in order
    HIGH = 3         # Important learning, prioritize
    CRITICAL = 4     # Must process immediately
    EMERGENCY = 5    # System health at risk


# =============================================================================
# LEARNING SIGNAL MODEL
# =============================================================================

class LearningSignal(BaseModel):
    """
    A learning signal that flows between ADAM components.
    
    This is the fundamental unit of inter-component learning.
    Every outcome, every validation, every discovery creates signals.
    """
    
    # Identity
    signal_id: str = Field(
        default_factory=lambda: f"lsig_{uuid.uuid4().hex[:12]}"
    )
    signal_type: LearningSignalType
    
    # Source
    source_component: str
    source_version: str = "1.0"
    
    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Context
    decision_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # The learning payload - what to learn
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Confidence in this signal
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_count: int = Field(default=1, ge=1)
    
    # Routing
    target_components: List[str] = Field(default_factory=list)
    priority: LearningSignalPriority = LearningSignalPriority.NORMAL
    
    # Provenance
    upstream_signals: List[str] = Field(default_factory=list)
    
    def for_component(self, component_name: str) -> bool:
        """Check if this signal is relevant for a component."""
        if not self.target_components:
            return True  # Broadcast to all
        return component_name in self.target_components


# =============================================================================
# LEARNING CONTRIBUTION MODEL
# =============================================================================

class LearningContribution(BaseModel):
    """
    A component's contribution to a decision.
    
    Used by the Gradient Bridge for credit attribution.
    Every component must be able to report what it contributed.
    """
    
    component_name: str
    decision_id: str
    
    # What the component contributed
    contribution_type: str  # e.g., "mechanism_selection", "state_inference"
    contribution_value: Any
    
    # Confidence in contribution
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence chain
    reasoning_summary: str
    evidence_sources: List[str] = Field(default_factory=list)
    
    # Sub-contributions (for composite components)
    sub_contributions: List["LearningContribution"] = Field(default_factory=list)
    
    # Weight in final decision
    weight: float = Field(default=1.0, ge=0.0)
    
    # Timing
    computation_time_ms: float = Field(default=0.0, ge=0.0)


# =============================================================================
# LEARNING QUALITY METRICS
# =============================================================================

class LearningQualityMetrics(BaseModel):
    """
    Metrics that measure the QUALITY of a component's learning.
    
    This is critical - presence of learning is not enough.
    We must measure whether the learning is EFFECTIVE.
    """
    
    component_name: str
    measurement_period_hours: int = 24
    
    # Learning Volume
    signals_emitted: int = 0
    signals_consumed: int = 0
    outcomes_processed: int = 0
    
    # Learning Effectiveness
    prediction_accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    prediction_accuracy_trend: str = "stable"  # improving, stable, declining
    
    # Attribution Quality
    attribution_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    # What % of decisions can be attributed to this component
    
    # Learning Speed
    convergence_rate: float = Field(default=0.0, ge=0.0)
    # How quickly does learning improve predictions
    
    # Learning Freshness
    last_learning_update: Optional[datetime] = None
    stale_priors_count: int = 0
    
    # Cross-Component Integration
    upstream_dependencies: List[str] = Field(default_factory=list)
    downstream_consumers: List[str] = Field(default_factory=list)
    integration_health: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @property
    def is_healthy(self) -> bool:
        """Is this component's learning healthy?"""
        return (
            self.prediction_accuracy >= 0.5 and
            self.attribution_coverage >= 0.5 and
            self.integration_health >= 0.7 and
            self.prediction_accuracy_trend != "declining"
        )


# =============================================================================
# THE UNIVERSAL LEARNING INTERFACE
# =============================================================================

class LearningCapableComponent(ABC):
    """
    THE UNIVERSAL LEARNING INTERFACE
    
    Every ADAM component that:
    - Makes predictions
    - Contributes to decisions
    - Processes signals
    - Generates insights
    
    MUST implement this interface.
    
    Components that don't implement this are dead nodes that
    take from the system but never give back. They prevent
    ADAM from becoming smarter over time.
    """
    
    @property
    @abstractmethod
    def component_name(self) -> str:
        """
        Unique identifier for this component.
        Used in signal routing and attribution.
        """
        pass
    
    @property
    @abstractmethod
    def component_version(self) -> str:
        """Version string for this component."""
        pass
    
    # =========================================================================
    # LEARNING FROM OUTCOMES
    # =========================================================================
    
    @abstractmethod
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """
        Called when an outcome is observed for a decision this component
        contributed to.
        
        The component MUST:
        1. Determine if this outcome is relevant to its domain
        2. Extract learning from the outcome (what worked, what didn't)
        3. Update internal state (caches, priors, models)
        4. Return learning signals for other components
        
        Args:
            decision_id: The decision that led to this outcome
            outcome_type: Type of outcome (conversion, click, skip, etc.)
            outcome_value: Numeric outcome value (1.0 = success, 0.0 = failure)
            context: Additional context about the outcome
            
        Returns:
            List of learning signals to propagate to other components
        """
        pass
    
    # =========================================================================
    # CONSUMING LEARNING SIGNALS
    # =========================================================================
    
    @abstractmethod
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """
        Called when a learning signal from another component is received.
        
        The component MUST:
        1. Check if the signal is relevant to its domain
        2. Update internal state based on the signal
        3. Optionally emit derivative signals
        
        Args:
            signal: The learning signal from another component
            
        Returns:
            Optional list of derivative signals (learning chains)
        """
        pass
    
    @abstractmethod
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        """
        Return the set of signal types this component can consume.
        
        Used by the Learning Signal Router for efficient dispatch.
        Only signals of these types will be delivered to this component.
        """
        pass
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    @abstractmethod
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """
        Called by the Gradient Bridge for credit attribution.
        
        The component MUST:
        1. Look up its contribution to this decision
        2. Return detailed contribution with confidence
        3. Include sub-contributions if composite
        
        Args:
            decision_id: The decision to attribute
            
        Returns:
            This component's contribution to the decision, or None if
            the component didn't contribute
        """
        pass
    
    # =========================================================================
    # QUALITY REPORTING
    # =========================================================================
    
    @abstractmethod
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """
        Return metrics about the quality of this component's learning.
        
        This is how we measure not just presence of learning,
        but EFFECTIVENESS of learning.
        
        Returns:
            Metrics about learning quality
        """
        pass
    
    # =========================================================================
    # PRIOR INJECTION
    # =========================================================================
    
    @abstractmethod
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any]
    ) -> None:
        """
        Inject priors before processing.
        
        This allows accumulated knowledge to inform current processing.
        The component MUST use these priors in its decision-making.
        
        Args:
            user_id: The user these priors are for
            priors: Accumulated priors from the knowledge graph
        """
        pass
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    @abstractmethod
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """
        Validate that this component's learning is healthy.
        
        Returns:
            Tuple of (is_healthy, list of issues if not healthy)
        """
        pass


# =============================================================================
# LEARNING SIGNAL ROUTER
# =============================================================================

class LearningSignalRouter:
    """
    Routes learning signals to appropriate component consumers.
    
    This is the central nervous system of ADAM's learning architecture.
    Every signal flows through here to reach the right destinations.
    """
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.component_registry: Dict[str, LearningCapableComponent] = {}
        self.signal_subscriptions: Dict[LearningSignalType, Set[str]] = {}
        
        # Metrics
        self.signals_routed: int = 0
        self.signals_dropped: int = 0
    
    def register_component(self, component: LearningCapableComponent) -> None:
        """Register a component for signal routing."""
        
        name = component.component_name
        self.component_registry[name] = component
        
        # Register signal subscriptions
        for signal_type in component.get_consumed_signal_types():
            if signal_type not in self.signal_subscriptions:
                self.signal_subscriptions[signal_type] = set()
            self.signal_subscriptions[signal_type].add(name)
        
        logger.info(f"Registered learning component: {name}")
    
    async def route_signal(self, signal: LearningSignal) -> int:
        """
        Route a learning signal to all interested components.
        
        Returns:
            Number of components that received the signal
        """
        
        # Get subscribers for this signal type
        subscribers = self.signal_subscriptions.get(signal.signal_type, set())
        
        # If signal has explicit targets, filter to those
        if signal.target_components:
            subscribers = subscribers.intersection(set(signal.target_components))
        
        delivered_count = 0
        
        for component_name in subscribers:
            component = self.component_registry.get(component_name)
            if component:
                try:
                    derivative_signals = await component.on_learning_signal_received(signal)
                    delivered_count += 1
                    
                    # Route any derivative signals
                    if derivative_signals:
                        for derivative in derivative_signals:
                            await self.route_signal(derivative)
                            
                except Exception as e:
                    logger.error(f"Error delivering signal to {component_name}: {e}")
        
        self.signals_routed += delivered_count
        
        if delivered_count == 0:
            self.signals_dropped += 1
            logger.warning(f"Signal {signal.signal_id} had no consumers")
        
        return delivered_count
    
    async def broadcast_outcome(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """
        Broadcast an outcome to all components for learning.
        
        This is the primary learning trigger - every outcome
        should go through here.
        """
        
        all_signals = []
        
        for component in self.component_registry.values():
            try:
                signals = await component.on_outcome_received(
                    decision_id=decision_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                    context=context
                )
                all_signals.extend(signals)
            except Exception as e:
                logger.error(
                    f"Error processing outcome in {component.component_name}: {e}"
                )
        
        # Route all generated signals
        for signal in all_signals:
            await self.route_signal(signal)
        
        return all_signals
    
    async def get_system_learning_health(self) -> Dict[str, LearningQualityMetrics]:
        """Get learning health for all components."""
        
        health = {}
        for name, component in self.component_registry.items():
            try:
                metrics = await component.get_learning_quality_metrics()
                health[name] = metrics
            except Exception as e:
                logger.error(f"Error getting health for {name}: {e}")
        
        return health


# =============================================================================
# COMPONENT CONTRIBUTION TRACKER
# =============================================================================

class ContributionTracker:
    """
    Tracks which components contributed to which decisions.
    
    This enables credit attribution when outcomes are observed.
    """
    
    def __init__(self, redis_client, ttl_seconds: int = 86400):
        self.redis = redis_client
        self.ttl = ttl_seconds
    
    async def record_contribution(
        self,
        decision_id: str,
        contribution: LearningContribution
    ) -> None:
        """Record a component's contribution to a decision."""
        
        key = f"adam:contribution:{decision_id}:{contribution.component_name}"
        await self.redis.setex(
            key,
            self.ttl,
            contribution.json()
        )
    
    async def get_contributions(
        self,
        decision_id: str
    ) -> List[LearningContribution]:
        """Get all contributions to a decision."""
        
        pattern = f"adam:contribution:{decision_id}:*"
        keys = await self.redis.keys(pattern)
        
        contributions = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                contributions.append(LearningContribution.parse_raw(data))
        
        return contributions
