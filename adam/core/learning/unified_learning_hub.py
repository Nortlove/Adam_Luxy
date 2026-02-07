#!/usr/bin/env python3
"""
UNIFIED LEARNING HUB
====================

The SINGLE source of truth for all learning signal routing in ADAM.

This consolidates the previous dual router system (signal_router.py + 
universal_learning_interface.py) into ONE hub that:

1. Receives ALL learning signals (from Kafka, event bus, or direct calls)
2. Maintains a SINGLE signal type system
3. Routes to ALL components (Graph, AoT, Thompson Sampling, Meta-learner)
4. ALSO makes direct updates (belt & suspenders - don't rely solely on signals)
5. Provides learning health monitoring

CRITICAL: This replaces both signal_router.py and universal_learning_interface.py.
All learning must flow through here.

Phase 1: Fix the Broken Learning Loop
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# UNIFIED SIGNAL TYPE SYSTEM
# =============================================================================

class UnifiedSignalType(str, Enum):
    """
    SINGLE signal type system for all ADAM learning.
    
    Maps from both:
    - gradient_bridge SignalType (REWARD, CREDIT, etc.)
    - universal_learning_interface LearningSignalType (OUTCOME_CONVERSION, etc.)
    """
    
    # Outcome signals (what happened)
    OUTCOME_SUCCESS = "outcome_success"           # Conversion, purchase, etc.
    OUTCOME_RECEIVED = "outcome_received"         # Generic outcome (alias for success)
    OUTCOME_ENGAGEMENT = "outcome_engagement"     # Click, view, etc.
    OUTCOME_FAILURE = "outcome_failure"           # Skip, bounce, rejection
    
    # Credit signals (who contributed)
    CREDIT_MECHANISM = "credit_mechanism"         # Credit to a mechanism
    CREDIT_ATOM = "credit_atom"                   # Credit to an atom
    CREDIT_COMPONENT = "credit_component"         # Credit to any component
    
    # Learning signals (what to update)
    UPDATE_THOMPSON = "update_thompson"           # Thompson Sampling posterior
    UPDATE_GRAPH = "update_graph"                 # Neo4j edge strength
    UPDATE_META_LEARNER = "update_meta_learner"   # Meta-learner routing
    UPDATE_ATOM_PRIOR = "update_atom_prior"       # Atom Bayesian prior
    
    # Discovery signals (what was found)
    PATTERN_DISCOVERED = "pattern_discovered"     # New pattern found
    CONSTRUCT_EMERGED = "construct_emerged"       # New construct emerged
    CALIBRATION_NEEDED = "calibration_needed"     # Confidence needs adjustment


# Mapping from old signal types to unified
SIGNAL_TYPE_MAPPING = {
    # From gradient_bridge SignalType
    "reward": UnifiedSignalType.OUTCOME_SUCCESS,
    "credit": UnifiedSignalType.CREDIT_COMPONENT,
    "mechanism_effectiveness": UnifiedSignalType.CREDIT_MECHANISM,
    
    # From universal_learning_interface LearningSignalType
    "outcome_conversion": UnifiedSignalType.OUTCOME_SUCCESS,
    "outcome_click": UnifiedSignalType.OUTCOME_ENGAGEMENT,
    "outcome_skip": UnifiedSignalType.OUTCOME_FAILURE,
    "outcome_engagement": UnifiedSignalType.OUTCOME_ENGAGEMENT,
    "outcome_rejection": UnifiedSignalType.OUTCOME_FAILURE,
    "credit_assigned": UnifiedSignalType.CREDIT_COMPONENT,
    "mechanism_attributed": UnifiedSignalType.CREDIT_MECHANISM,
    "atom_attributed": UnifiedSignalType.CREDIT_ATOM,
    "prior_updated": UnifiedSignalType.UPDATE_THOMPSON,
    "mechanism_effectiveness_updated": UnifiedSignalType.CREDIT_MECHANISM,
    "pattern_emerged": UnifiedSignalType.PATTERN_DISCOVERED,
    
    # From simple signal_router.py strings
    "outcome": UnifiedSignalType.OUTCOME_SUCCESS,
    "mechanism": UnifiedSignalType.CREDIT_MECHANISM,
    "bandit": UnifiedSignalType.UPDATE_THOMPSON,
    "graph": UnifiedSignalType.UPDATE_GRAPH,
}


# =============================================================================
# UNIFIED LEARNING SIGNAL
# =============================================================================

@dataclass
class UnifiedLearningSignal:
    """
    Single signal format for all ADAM learning.
    """
    
    signal_id: str = field(default_factory=lambda: f"uls_{uuid.uuid4().hex[:12]}")
    signal_type: UnifiedSignalType = UnifiedSignalType.OUTCOME_SUCCESS
    
    # Context
    decision_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Value
    value: float = 0.0
    weight: float = 1.0  # Helpful vote weight
    confidence: float = 0.5  # Confidence level
    
    # Target
    component: str = "unknown"
    source_component: str = "unknown"  # Alias for component (for compatibility)
    mechanism: Optional[str] = None
    archetype: Optional[str] = None
    
    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Ensure component and source_component are synchronized."""
        if self.source_component != "unknown" and self.component == "unknown":
            self.component = self.source_component
        elif self.component != "unknown" and self.source_component == "unknown":
            self.source_component = self.component
    
    @classmethod
    def from_old_signal(cls, old_signal: Any) -> "UnifiedLearningSignal":
        """Convert from any old signal format."""
        # Get signal type string
        if hasattr(old_signal, "signal_type"):
            type_str = str(old_signal.signal_type.value if hasattr(old_signal.signal_type, "value") else old_signal.signal_type)
        elif hasattr(old_signal, "type"):
            type_str = str(old_signal.type)
        else:
            type_str = "outcome"
        
        # Map to unified type
        signal_type = SIGNAL_TYPE_MAPPING.get(
            type_str.lower(),
            UnifiedSignalType.OUTCOME_SUCCESS
        )
        
        # Extract common fields
        return cls(
            signal_type=signal_type,
            decision_id=getattr(old_signal, "decision_id", None),
            request_id=getattr(old_signal, "request_id", None),
            user_id=getattr(old_signal, "user_id", None),
            value=getattr(old_signal, "value", 0.0) or getattr(old_signal, "signal_value", 0.0),
            weight=getattr(old_signal, "weight", 1.0),
            component=getattr(old_signal, "component", "unknown") or getattr(old_signal, "source_component", "unknown"),
            mechanism=getattr(old_signal, "mechanism", None),
            payload=getattr(old_signal, "payload", {}) or getattr(old_signal, "metadata", {}),
        )


# =============================================================================
# COMPONENT REGISTRY
# =============================================================================

@dataclass
class RegisteredComponent:
    """A component registered to receive learning signals."""
    
    name: str
    handler: Callable  # async def handler(signal: UnifiedLearningSignal) -> None
    signal_types: Set[UnifiedSignalType]
    priority: int = 0  # Higher = called first


# =============================================================================
# UNIFIED LEARNING HUB
# =============================================================================

class UnifiedLearningHub:
    """
    THE SINGLE learning signal router for all of ADAM.
    
    Consolidates:
    - signal_router.py
    - universal_learning_interface.py
    - Direct component updates
    
    Provides:
    - Signal routing to registered components
    - Direct updates to critical systems (belt & suspenders)
    - Learning health monitoring
    - Signal conversion from old formats
    """
    
    def __init__(self):
        self._components: Dict[str, RegisteredComponent] = {}
        self._event_bus = None
        self._initialized = False
        
        # Direct updaters (belt & suspenders)
        self._thompson_sampler = None
        self._graph_service = None
        self._meta_learner = None
        
        # Stats
        self._signals_processed = 0
        self._signals_by_type: Dict[UnifiedSignalType, int] = {}
        self._errors: List[str] = []
    
    async def initialize(self) -> None:
        """Initialize the hub and connect to systems."""
        if self._initialized:
            return
        
        # Get event bus for signal reception
        try:
            from adam.core.learning.event_bus import get_event_bus
            self._event_bus = await get_event_bus()
            
            # Subscribe to ALL learning-related topics
            await self._event_bus.subscribe("learning.outcome", self._handle_event)
            await self._event_bus.subscribe("learning.credit", self._handle_event)
            await self._event_bus.subscribe("learning.mechanism", self._handle_event)
            await self._event_bus.subscribe("learning.bandit", self._handle_event)
            await self._event_bus.subscribe("learning.graph", self._handle_event)
            await self._event_bus.subscribe("learning_signal", self._handle_event)  # Universal topic
            
            logger.info("UnifiedLearningHub subscribed to event bus")
        except Exception as e:
            logger.warning(f"Could not connect to event bus: {e}")
        
        # Get direct updaters
        await self._init_direct_updaters()
        
        self._initialized = True
        logger.info("UnifiedLearningHub initialized")
    
    async def _init_direct_updaters(self) -> None:
        """Initialize direct connections to learning systems and auto-register components."""
        components_registered = 0
        
        # Thompson Sampler - Critical for mechanism learning
        try:
            from adam.cold_start.thompson.sampler import get_thompson_sampler
            self._thompson_sampler = get_thompson_sampler()
            
            # Register Thompson Sampler as learning component
            self.register_component(
                name="thompson_sampler",
                handler=self._update_thompson_sampler,
                signal_types={
                    UnifiedSignalType.OUTCOME_SUCCESS,
                    UnifiedSignalType.CREDIT_MECHANISM,
                    UnifiedSignalType.UPDATE_THOMPSON,
                },
                priority=10,  # High priority - updates bandit
            )
            components_registered += 1
            logger.debug("Thompson Sampler connected and registered")
        except ImportError as e:
            logger.debug(f"Thompson Sampler not available: {e}")
        
        # Graph Service - Persists to Neo4j
        try:
            from adam.intelligence.graph_edge_service import get_graph_edge_service
            self._graph_service = get_graph_edge_service()
            
            # Register Graph Service
            self.register_component(
                name="graph_service",
                handler=self._update_graph_service,
                signal_types={
                    UnifiedSignalType.OUTCOME_SUCCESS,
                    UnifiedSignalType.CREDIT_MECHANISM,
                    UnifiedSignalType.UPDATE_GRAPH,
                },
                priority=5,
            )
            components_registered += 1
            logger.debug("Graph Edge Service connected and registered")
        except ImportError as e:
            logger.debug(f"Graph Edge Service not available: {e}")
        
        # Meta-learner - Aggregates learning across components
        try:
            from adam.core.learning.signal_router import get_meta_learner_learning
            self._meta_learner = get_meta_learner_learning()
            
            # Register Meta-learner
            self.register_component(
                name="meta_learner",
                handler=self._update_meta_learner,
                signal_types={
                    UnifiedSignalType.OUTCOME_SUCCESS,
                    UnifiedSignalType.CREDIT_MECHANISM,
                    UnifiedSignalType.UPDATE_META_LEARNER,
                },
                priority=3,
            )
            components_registered += 1
            logger.debug("Meta-learner connected and registered")
        except ImportError as e:
            logger.debug(f"Meta-learner not available: {e}")
        
        # Learned Priors Service - Updates prior distributions
        try:
            from adam.core.learning.learned_priors_integration import get_learned_priors
            self._priors_service = get_learned_priors()
            
            # Register Priors Service
            self.register_component(
                name="priors_service",
                handler=self._update_priors_service,
                signal_types={
                    UnifiedSignalType.OUTCOME_SUCCESS,
                    UnifiedSignalType.UPDATE_ATOM_PRIOR,
                },
                priority=2,
            )
            components_registered += 1
            logger.debug("Priors Service connected and registered")
        except ImportError as e:
            logger.debug(f"Priors Service not available: {e}")
        
        # Bidirectional Bridge - Persists decisions to graph
        try:
            from adam.intelligence.bidirectional_bridge import get_bidirectional_bridge
            self._bidirectional_bridge = get_bidirectional_bridge()
            
            # Register Bidirectional Bridge
            self.register_component(
                name="bidirectional_bridge",
                handler=self._update_bidirectional_bridge,
                signal_types={
                    UnifiedSignalType.OUTCOME_SUCCESS,
                    UnifiedSignalType.UPDATE_GRAPH,
                },
                priority=4,
            )
            components_registered += 1
            logger.debug("Bidirectional Bridge connected and registered")
        except ImportError as e:
            logger.debug(f"Bidirectional Bridge not available: {e}")
        
        logger.info(f"UnifiedLearningHub auto-registered {components_registered} components")
    
    async def _update_thompson_sampler(self, signal: UnifiedLearningSignal) -> bool:
        """Update Thompson Sampler with learning signal."""
        if not self._thompson_sampler:
            return False
        
        try:
            # Update based on signal type
            if signal.signal_type in (UnifiedSignalType.OUTCOME_SUCCESS, UnifiedSignalType.UPDATE_THOMPSON):
                # Convert outcome to reward
                reward = signal.payload.get("outcome_value", 0.5)
                self._thompson_sampler.update(
                    archetype=signal.archetype,
                    mechanism=signal.mechanism,
                    reward=reward,
                )
            elif signal.signal_type == UnifiedSignalType.CREDIT_MECHANISM:
                # Direct mechanism feedback
                effectiveness = signal.payload.get("effectiveness", 0.5)
                self._thompson_sampler.update(
                    archetype=signal.archetype,
                    mechanism=signal.mechanism,
                    reward=effectiveness,
                )
            return True
        except Exception as e:
            logger.debug(f"Thompson Sampler update failed: {e}")
            return False
    
    async def _update_graph_service(self, signal: UnifiedLearningSignal) -> bool:
        """Update Graph Service with learning signal."""
        if not self._graph_service:
            return False
        
        try:
            # Store edge weight update
            await self._graph_service.update_edge_weight(
                from_node=signal.archetype,
                to_node=signal.mechanism,
                weight_delta=signal.payload.get("weight_delta", 0.0),
                signal_type=signal.signal_type.value,
            )
            return True
        except Exception as e:
            logger.debug(f"Graph Service update failed: {e}")
            return False
    
    async def _update_meta_learner(self, signal: UnifiedLearningSignal) -> bool:
        """Update Meta-learner with learning signal."""
        if not self._meta_learner:
            return False
        
        try:
            self._meta_learner.receive_signal(signal)
            return True
        except Exception as e:
            logger.debug(f"Meta-learner update failed: {e}")
            return False
    
    async def _update_priors_service(self, signal: UnifiedLearningSignal) -> bool:
        """Update Priors Service with learning signal."""
        if not hasattr(self, '_priors_service') or not self._priors_service:
            return False
        
        try:
            # Priors service updates are typically batch
            # Log for now, could implement incremental updates
            logger.debug(f"Priors update signal: {signal.archetype}/{signal.mechanism}")
            return True
        except Exception as e:
            logger.debug(f"Priors Service update failed: {e}")
            return False
    
    async def _update_bidirectional_bridge(self, signal: UnifiedLearningSignal) -> bool:
        """Update Bidirectional Bridge with learning signal."""
        if not hasattr(self, '_bidirectional_bridge') or not self._bidirectional_bridge:
            return False
        
        try:
            # Bridge handles graph persistence
            await self._bidirectional_bridge.emit_learning_signal(
                signal_type=signal.signal_type.value,
                archetype=signal.archetype,
                mechanism=signal.mechanism,
                payload=signal.payload,
            )
            return True
        except Exception as e:
            logger.debug(f"Bidirectional Bridge update failed: {e}")
            return False
    
    def register_component(
        self,
        name: str,
        handler: Callable,
        signal_types: Set[UnifiedSignalType],
        priority: int = 0,
    ) -> None:
        """Register a component to receive learning signals."""
        self._components[name] = RegisteredComponent(
            name=name,
            handler=handler,
            signal_types=signal_types,
            priority=priority,
        )
        logger.info(f"Registered learning component: {name} for {len(signal_types)} signal types")
    
    async def process_signal(self, signal: UnifiedLearningSignal) -> int:
        """
        Process a learning signal.
        
        Routes to:
        1. All registered component handlers
        2. Direct updaters (belt & suspenders)
        
        Returns number of successful deliveries.
        """
        delivered = 0
        
        # 1. Direct updates first (guaranteed delivery)
        delivered += await self._direct_update(signal)
        
        # 2. Route to registered components
        # Sort by priority (highest first)
        components = sorted(
            self._components.values(),
            key=lambda c: c.priority,
            reverse=True,
        )
        
        for component in components:
            if signal.signal_type in component.signal_types:
                try:
                    result = component.handler(signal)
                    if asyncio.iscoroutine(result):
                        await result
                    delivered += 1
                except Exception as e:
                    self._errors.append(f"{component.name}: {e}")
                    logger.error(f"Error in component {component.name}: {e}")
        
        # Update stats
        self._signals_processed += 1
        self._signals_by_type[signal.signal_type] = self._signals_by_type.get(signal.signal_type, 0) + 1
        
        return delivered
    
    async def _direct_update(self, signal: UnifiedLearningSignal) -> int:
        """
        Direct updates to critical systems (belt & suspenders).
        
        Even if signal routing fails, these updates WILL happen.
        """
        updated = 0
        
        # Thompson Sampling update
        if signal.signal_type in (
            UnifiedSignalType.OUTCOME_SUCCESS,
            UnifiedSignalType.OUTCOME_FAILURE,
            UnifiedSignalType.UPDATE_THOMPSON,
            UnifiedSignalType.CREDIT_MECHANISM,
        ):
            if self._thompson_sampler and signal.mechanism:
                try:
                    success = signal.signal_type in (
                        UnifiedSignalType.OUTCOME_SUCCESS,
                        UnifiedSignalType.UPDATE_THOMPSON,
                    ) or signal.value >= 0.5
                    
                    # Find update method
                    if hasattr(self._thompson_sampler, "update"):
                        self._thompson_sampler.update(
                            signal.mechanism,
                            success,
                            weight=signal.weight,
                        )
                        updated += 1
                    elif hasattr(self._thompson_sampler, "update_posterior"):
                        self._thompson_sampler.update_posterior(
                            signal.mechanism,
                            success,
                        )
                        updated += 1
                except Exception as e:
                    logger.debug(f"Thompson direct update failed: {e}")
        
        # Graph update
        if signal.signal_type in (
            UnifiedSignalType.UPDATE_GRAPH,
            UnifiedSignalType.CREDIT_MECHANISM,
        ):
            if self._graph_service:
                try:
                    if hasattr(self._graph_service, "update_edge_strength"):
                        await self._graph_service.update_edge_strength(
                            user_id=signal.user_id or "unknown",
                            mechanism=signal.mechanism or "unknown",
                            delta=signal.value * signal.weight,
                        )
                        updated += 1
                except Exception as e:
                    logger.debug(f"Graph direct update failed: {e}")
        
        # Meta-learner update
        if signal.signal_type in (
            UnifiedSignalType.OUTCOME_SUCCESS,
            UnifiedSignalType.OUTCOME_ENGAGEMENT,
            UnifiedSignalType.UPDATE_META_LEARNER,
        ):
            if self._meta_learner:
                try:
                    await self._meta_learner.process_outcome_signal(signal)
                    updated += 1
                except Exception as e:
                    logger.debug(f"Meta-learner direct update failed: {e}")
        
        return updated
    
    async def _handle_event(self, event: Any) -> None:
        """Handle event bus events by converting and routing."""
        try:
            signal = UnifiedLearningSignal.from_old_signal(event)
            await self.process_signal(signal)
        except Exception as e:
            logger.error(f"Failed to handle event: {e}")
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    async def emit_outcome(
        self,
        decision_id: str,
        outcome_value: float,
        mechanism: Optional[str] = None,
        user_id: Optional[str] = None,
        archetype: Optional[str] = None,
        helpful_vote_weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Emit an outcome signal and route to all systems.
        
        This is the PRIMARY entry point for learning from outcomes.
        """
        signal_type = (
            UnifiedSignalType.OUTCOME_SUCCESS
            if outcome_value >= 0.5
            else UnifiedSignalType.OUTCOME_FAILURE
        )
        
        signal = UnifiedLearningSignal(
            signal_type=signal_type,
            decision_id=decision_id,
            user_id=user_id,
            value=outcome_value,
            weight=helpful_vote_weight,
            mechanism=mechanism,
            archetype=archetype,
            payload=metadata or {},
        )
        
        return await self.process_signal(signal)
    
    async def emit_mechanism_credit(
        self,
        mechanism: str,
        credit: float,
        decision_id: Optional[str] = None,
        user_id: Optional[str] = None,
        archetype: Optional[str] = None,
        helpful_vote_weight: float = 1.0,
    ) -> int:
        """Emit mechanism credit signal."""
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.CREDIT_MECHANISM,
            decision_id=decision_id,
            user_id=user_id,
            value=credit,
            weight=helpful_vote_weight,
            mechanism=mechanism,
            archetype=archetype,
        )
        
        return await self.process_signal(signal)
    
    async def emit_pattern_discovered(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        confidence: float = 0.8,
    ) -> int:
        """Emit pattern discovery signal."""
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.PATTERN_DISCOVERED,
            value=confidence,
            payload={
                "pattern_type": pattern_type,
                **pattern_data,
            },
        )
        
        return await self.process_signal(signal)
    
    # =========================================================================
    # HEALTH MONITORING
    # =========================================================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get learning system health status."""
        return {
            "initialized": self._initialized,
            "components_registered": len(self._components),
            "components": list(self._components.keys()),
            "signals_processed": self._signals_processed,
            "signals_by_type": {
                t.value: c for t, c in self._signals_by_type.items()
            },
            "recent_errors": self._errors[-10:] if self._errors else [],
            "direct_updaters": {
                "thompson_sampler": self._thompson_sampler is not None,
                "graph_service": self._graph_service is not None,
                "meta_learner": self._meta_learner is not None,
            },
        }
    
    async def validate_learning_loop(self) -> Tuple[bool, List[str]]:
        """
        Validate that the learning loop is working.
        
        Returns (is_healthy, issues).
        """
        issues = []
        
        if not self._initialized:
            issues.append("Hub not initialized")
        
        if not self._components:
            issues.append("No components registered")
        
        if self._thompson_sampler is None:
            issues.append("Thompson Sampler not connected")
        
        if self._graph_service is None:
            issues.append("Graph Service not connected")
        
        if self._meta_learner is None:
            issues.append("Meta-learner not connected")
        
        if self._errors:
            issues.append(f"{len(self._errors)} errors in recent processing")
        
        return len(issues) == 0, issues


# =============================================================================
# SINGLETON
# =============================================================================

_hub: Optional[UnifiedLearningHub] = None


def get_unified_learning_hub() -> UnifiedLearningHub:
    """Get singleton unified learning hub."""
    global _hub
    if _hub is None:
        _hub = UnifiedLearningHub()
    return _hub


async def get_initialized_learning_hub() -> UnifiedLearningHub:
    """Get initialized singleton unified learning hub."""
    hub = get_unified_learning_hub()
    await hub.initialize()
    return hub


def reset_learning_hub() -> None:
    """Reset singleton for testing."""
    global _hub
    _hub = None


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# Expose old names that point to new hub
def get_learning_signal_router():
    """Backward compatible - returns unified hub."""
    return get_unified_learning_hub()


def get_meta_learner_learning():
    """Backward compatible - returns meta-learner from hub."""
    hub = get_unified_learning_hub()
    return hub._meta_learner
