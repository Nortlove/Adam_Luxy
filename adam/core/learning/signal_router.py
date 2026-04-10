#!/usr/bin/env python3
"""
LEARNING SIGNAL ROUTER
======================

Routes learning signals to appropriate components.

Phase 5: Learning Loop Completion
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from adam.core.learning.event_bus import Event, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class LearningSignal:
    """A learning signal to be routed."""
    
    signal_id: str
    signal_type: str  # "outcome", "credit", "mechanism", "bandit"
    component: str
    value: float
    metadata: Dict[str, Any]
    timestamp: datetime
    weight: float = 1.0  # Helpful vote weight


class LearningSignalRouter:
    """
    Routes learning signals to appropriate components.
    
    Subscribes to event bus topics and dispatches to:
    - Meta-learner for Thompson sampling updates
    - Graph service for edge strength updates  
    - Bandit arms for reward updates
    - AoT atoms for individual learning
    """
    
    def __init__(self):
        self._event_bus = None
        self._subscribed = False
        self._signals_routed = 0
        
        # Routing table: signal_type -> handler
        self._handlers: Dict[str, List[callable]] = {
            "outcome": [],
            "credit": [],
            "mechanism": [],
            "bandit": [],
            "graph": [],
        }
    
    async def initialize(self) -> None:
        """Initialize and subscribe to event bus."""
        if self._subscribed:
            return
        
        self._event_bus = await get_event_bus()
        
        # Subscribe to learning-related topics
        await self._event_bus.subscribe("learning.outcome", self._handle_outcome)
        await self._event_bus.subscribe("learning.credit", self._handle_credit)
        await self._event_bus.subscribe("learning.mechanism", self._handle_mechanism)
        await self._event_bus.subscribe("learning.bandit", self._handle_bandit)
        await self._event_bus.subscribe("learning.graph", self._handle_graph)
        
        self._subscribed = True
        logger.info("LearningSignalRouter subscribed to event bus")
    
    def register_handler(
        self,
        signal_type: str,
        handler: callable,
    ) -> None:
        """Register a handler for a signal type."""
        if signal_type not in self._handlers:
            self._handlers[signal_type] = []
        self._handlers[signal_type].append(handler)
    
    async def route_signal(self, signal: LearningSignal) -> int:
        """
        Route a signal to registered handlers.
        
        Returns number of handlers notified.
        """
        handlers = self._handlers.get(signal.signal_type, [])
        notified = 0
        
        for handler in handlers:
            try:
                result = handler(signal)
                if asyncio.iscoroutine(result):
                    await result
                notified += 1
            except Exception as e:
                logger.error(f"Handler error for signal {signal.signal_type}: {e}")
        
        self._signals_routed += 1
        return notified
    
    async def _handle_outcome(self, event: Event) -> None:
        """Handle outcome events."""
        signal = LearningSignal(
            signal_id=event.event_id,
            signal_type="outcome",
            component=event.source,
            value=event.payload.get("outcome_value", 0.0),
            metadata=event.payload,
            timestamp=event.created_at,
            weight=event.weight,
        )
        
        await self.route_signal(signal)
        
        # Also update meta-learner directly
        try:
            meta = get_meta_learner_learning()
            await meta.process_outcome_signal(signal)
        except Exception as e:
            logger.debug(f"Meta-learner update skipped: {e}")
    
    async def _handle_credit(self, event: Event) -> None:
        """Handle credit attribution events."""
        signal = LearningSignal(
            signal_id=event.event_id,
            signal_type="credit",
            component=event.payload.get("component", "unknown"),
            value=event.payload.get("credit_score", 0.0),
            metadata=event.payload,
            timestamp=event.created_at,
            weight=event.weight,
        )
        await self.route_signal(signal)
    
    async def _handle_mechanism(self, event: Event) -> None:
        """Handle mechanism learning events."""
        signal = LearningSignal(
            signal_id=event.event_id,
            signal_type="mechanism",
            component=event.payload.get("mechanism_id", "unknown"),
            value=event.payload.get("effectiveness", 0.0),
            metadata=event.payload,
            timestamp=event.created_at,
            weight=event.weight,
        )
        await self.route_signal(signal)
    
    async def _handle_bandit(self, event: Event) -> None:
        """Handle bandit reward events."""
        signal = LearningSignal(
            signal_id=event.event_id,
            signal_type="bandit",
            component=event.payload.get("arm_id", "unknown"),
            value=event.payload.get("reward", 0.0),
            metadata=event.payload,
            timestamp=event.created_at,
            weight=event.weight,
        )
        await self.route_signal(signal)
    
    async def _handle_graph(self, event: Event) -> None:
        """Handle graph update events."""
        signal = LearningSignal(
            signal_id=event.event_id,
            signal_type="graph",
            component="graph",
            value=event.payload.get("edge_strength_delta", 0.0),
            metadata=event.payload,
            timestamp=event.created_at,
            weight=event.weight,
        )
        await self.route_signal(signal)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "signals_routed": self._signals_routed,
            "subscribed": self._subscribed,
            "handlers": {
                sig_type: len(handlers)
                for sig_type, handlers in self._handlers.items()
                if handlers
            },
        }


# =============================================================================
# SINGLETON
# =============================================================================

_router: Optional[LearningSignalRouter] = None


def get_learning_signal_router() -> LearningSignalRouter:
    """Get singleton learning signal router."""
    global _router
    if _router is None:
        _router = LearningSignalRouter()
    return _router


# =============================================================================
# META-LEARNER LEARNING (Simple version)
# =============================================================================

class MetaLearnerLearning:
    """
    Simple meta-learner that learns from outcomes.
    
    Uses Thompson Sampling with weighted updates.
    """
    
    def __init__(self):
        # Track arm performance: arm_id -> (successes, failures)
        self._arm_stats: Dict[str, tuple] = {}
        self._total_signals = 0
    
    async def process_outcome_signal(self, signal: LearningSignal) -> None:
        """Process an outcome signal for Thompson Sampling update."""
        mechanism = signal.metadata.get("mechanism_used", "default")
        outcome = signal.value
        weight = signal.weight
        
        # Initialize arm if new
        if mechanism not in self._arm_stats:
            self._arm_stats[mechanism] = (1.0, 1.0)  # Beta(1,1) prior
        
        alpha, beta = self._arm_stats[mechanism]
        
        # Weighted update (helpful votes increase impact)
        if outcome >= 0.5:
            alpha += weight
        else:
            beta += weight
        
        self._arm_stats[mechanism] = (alpha, beta)
        self._total_signals += 1
        
        logger.debug(f"Meta-learner updated {mechanism}: α={alpha:.2f}, β={beta:.2f}")
    
    def sample_arm(self, mechanism: str) -> float:
        """Sample from Thompson posterior for mechanism."""
        import random
        
        if mechanism not in self._arm_stats:
            return random.random()  # Uniform prior
        
        alpha, beta = self._arm_stats[mechanism]
        
        # Beta sampling (approximation without numpy)
        # Use simple mean for now
        return alpha / (alpha + beta)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get meta-learner statistics."""
        return {
            "arms": len(self._arm_stats),
            "total_signals": self._total_signals,
            "arm_stats": {
                arm: {"alpha": a, "beta": b, "mean": a/(a+b)}
                for arm, (a, b) in self._arm_stats.items()
            },
        }


_meta_learner: Optional[MetaLearnerLearning] = None


def get_meta_learner_learning() -> MetaLearnerLearning:
    """Get singleton meta-learner."""
    global _meta_learner
    if _meta_learner is None:
        _meta_learner = MetaLearnerLearning()
    return _meta_learner
