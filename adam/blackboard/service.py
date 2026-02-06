# =============================================================================
# ADAM Blackboard Service
# Location: adam/blackboard/service.py
# =============================================================================

"""
BLACKBOARD SERVICE

Core service for managing the 5-zone blackboard architecture.

Features:
- Zone access control
- Redis-backed persistence
- Pub/Sub event layer
- Atomic operations
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from adam.blackboard.models.core import (
    BlackboardState,
    BlackboardZone,
    ZoneAccessMode,
    ComponentRole,
    check_access,
    ZONE_TTLS,
    BlackboardEvent,
    BlackboardEventType,
)
from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
from adam.blackboard.models.zone2_reasoning import AtomReasoningSpace, Zone2Aggregate, AtomType
from adam.blackboard.models.zone3_synthesis import SynthesisWorkspace
from adam.blackboard.models.zone4_decision import DecisionState
from adam.blackboard.models.zone5_learning import LearningSignalAggregator, ComponentSignal
from adam.infrastructure.redis import ADAMRedisCache, CacheKeyBuilder
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
from adam.infrastructure.prometheus import get_metrics

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# =============================================================================
# BLACKBOARD SERVICE
# =============================================================================

class BlackboardService:
    """
    Service for managing the shared state blackboard.
    
    Provides:
    - Zone-aware read/write operations
    - Access control enforcement
    - Event emission
    - Atomic state updates
    """
    
    def __init__(self, redis_cache: ADAMRedisCache):
        self.cache = redis_cache
        self.metrics = get_metrics()
        self._pubsub_channels: Dict[str, asyncio.Queue] = {}
    
    # -------------------------------------------------------------------------
    # BLACKBOARD LIFECYCLE
    # -------------------------------------------------------------------------
    
    async def create_blackboard(
        self,
        request_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> BlackboardState:
        """
        Create a new blackboard for a request.
        
        Initializes all 5 zones with appropriate TTLs.
        """
        blackboard = BlackboardState(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )
        blackboard.initialize_zones()
        
        # Store blackboard metadata
        meta_key = f"adam:blackboard:{request_id}:meta"
        await self.cache.set(
            meta_key,
            blackboard,
            ttl=ZONE_TTLS[BlackboardZone.ZONE_5_LEARNING],  # Longest TTL
        )
        
        # Emit creation event
        await self._emit_event(
            BlackboardEventType.BLACKBOARD_CREATED,
            request_id=request_id,
            blackboard_id=blackboard.blackboard_id,
            source_component="blackboard_service",
        )
        
        logger.debug(f"Created blackboard for request {request_id}")
        return blackboard
    
    async def get_blackboard(self, request_id: str) -> Optional[BlackboardState]:
        """Get blackboard metadata."""
        meta_key = f"adam:blackboard:{request_id}:meta"
        return await self.cache.get(meta_key, BlackboardState)
    
    async def complete_blackboard(self, request_id: str) -> None:
        """Mark a blackboard as complete."""
        blackboard = await self.get_blackboard(request_id)
        if blackboard:
            blackboard.complete()
            meta_key = f"adam:blackboard:{request_id}:meta"
            await self.cache.set(meta_key, blackboard)
            
            await self._emit_event(
                BlackboardEventType.BLACKBOARD_COMPLETED,
                request_id=request_id,
                blackboard_id=blackboard.blackboard_id,
                source_component="blackboard_service",
            )
    
    # -------------------------------------------------------------------------
    # ZONE 1: REQUEST CONTEXT
    # -------------------------------------------------------------------------
    
    async def write_zone1(
        self,
        request_id: str,
        context: RequestContext,
        role: ComponentRole = ComponentRole.REQUEST_HANDLER,
    ) -> bool:
        """
        Write to Zone 1 (request context).
        
        This should only be called once at request ingestion.
        """
        if not check_access(BlackboardZone.ZONE_1_CONTEXT, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 1")
            return False
        
        key = f"adam:blackboard:{request_id}:zone1"
        success = await self.cache.set(
            key,
            context,
            ttl=ZONE_TTLS[BlackboardZone.ZONE_1_CONTEXT],
        )
        
        if success:
            await self._emit_zone_event(
                request_id, BlackboardZone.ZONE_1_CONTEXT, "write"
            )
        
        return success
    
    async def read_zone1(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> Optional[RequestContext]:
        """Read from Zone 1 (request context)."""
        if not check_access(BlackboardZone.ZONE_1_CONTEXT, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 1")
            return None
        
        key = f"adam:blackboard:{request_id}:zone1"
        return await self.cache.get(key, RequestContext)
    
    # -------------------------------------------------------------------------
    # ZONE 2: ATOM REASONING SPACES
    # -------------------------------------------------------------------------
    
    async def write_zone2_atom(
        self,
        request_id: str,
        atom_id: str,
        space: AtomReasoningSpace,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> bool:
        """
        Write to Zone 2 (atom reasoning space).
        
        Each atom writes to its own namespace.
        """
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 2")
            return False
        
        key = f"adam:blackboard:{request_id}:zone2:{atom_id}"
        success = await self.cache.set(
            key,
            space,
            ttl=ZONE_TTLS[BlackboardZone.ZONE_2_REASONING],
        )
        
        if success:
            await self._emit_zone_event(
                request_id, BlackboardZone.ZONE_2_REASONING, "write",
                payload={"atom_id": atom_id}
            )
            
            # If atom completed, emit atom_completed event
            if space.status == "completed":
                await self._emit_event(
                    BlackboardEventType.ATOM_COMPLETED,
                    request_id=request_id,
                    blackboard_id="",
                    source_component=atom_id,
                    source_zone=BlackboardZone.ZONE_2_REASONING,
                    payload={"atom_type": space.atom_type.value},
                )
        
        return success
    
    async def read_zone2_atom(
        self,
        request_id: str,
        atom_id: str,
        role: ComponentRole = ComponentRole.SYNTHESIS,
    ) -> Optional[AtomReasoningSpace]:
        """Read a specific atom's reasoning space."""
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 2")
            return None
        
        key = f"adam:blackboard:{request_id}:zone2:{atom_id}"
        return await self.cache.get(key, AtomReasoningSpace)
    
    async def read_zone2_all_atoms(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.SYNTHESIS,
    ) -> Zone2Aggregate:
        """Read all atom reasoning spaces for aggregation."""
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 2")
            return Zone2Aggregate(request_id=request_id)
        
        aggregate = Zone2Aggregate(request_id=request_id)
        
        # Scan for all atom keys
        pattern = f"adam:blackboard:{request_id}:zone2:*"
        count = await self.cache.count_pattern(pattern)
        
        if count > 0:
            # Get all atom spaces (would use scan in production)
            # For now, iterate known atom types
            for atom_type in AtomType:
                atom_id = f"atom_{atom_type.value}"
                space = await self.read_zone2_atom(request_id, atom_id, role)
                if space:
                    aggregate.update_from_space(space)
        
        return aggregate
    
    async def read_zone2_signals(
        self,
        request_id: str,
        for_atom_type: AtomType,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> List:
        """Read preliminary signals relevant to an atom type."""
        aggregate = await self.read_zone2_all_atoms(request_id, role)
        return aggregate.get_signals_for_atom(for_atom_type)
    
    # -------------------------------------------------------------------------
    # ZONE 3: SYNTHESIS WORKSPACE
    # -------------------------------------------------------------------------
    
    async def write_zone3(
        self,
        request_id: str,
        workspace: SynthesisWorkspace,
        role: ComponentRole = ComponentRole.SYNTHESIS,
    ) -> bool:
        """Write to Zone 3 (synthesis workspace)."""
        if not check_access(BlackboardZone.ZONE_3_SYNTHESIS, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 3")
            return False
        
        key = f"adam:blackboard:{request_id}:zone3"
        success = await self.cache.set(
            key,
            workspace,
            ttl=ZONE_TTLS[BlackboardZone.ZONE_3_SYNTHESIS],
        )
        
        if success:
            await self._emit_zone_event(
                request_id, BlackboardZone.ZONE_3_SYNTHESIS, "write"
            )
            
            if workspace.status == "completed":
                await self._emit_event(
                    BlackboardEventType.SYNTHESIS_COMPLETED,
                    request_id=request_id,
                    blackboard_id="",
                    source_component="synthesis",
                    source_zone=BlackboardZone.ZONE_3_SYNTHESIS,
                )
        
        return success
    
    async def read_zone3(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.DECISION,
    ) -> Optional[SynthesisWorkspace]:
        """Read from Zone 3 (synthesis workspace)."""
        if not check_access(BlackboardZone.ZONE_3_SYNTHESIS, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 3")
            return None
        
        key = f"adam:blackboard:{request_id}:zone3"
        return await self.cache.get(key, SynthesisWorkspace)
    
    # -------------------------------------------------------------------------
    # ZONE 4: DECISION STATE
    # -------------------------------------------------------------------------
    
    async def write_zone4(
        self,
        request_id: str,
        decision: DecisionState,
        role: ComponentRole = ComponentRole.DECISION,
    ) -> bool:
        """Write to Zone 4 (decision state)."""
        if not check_access(BlackboardZone.ZONE_4_DECISION, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 4")
            return False
        
        key = f"adam:blackboard:{request_id}:zone4"
        success = await self.cache.set(
            key,
            decision,
            ttl=ZONE_TTLS[BlackboardZone.ZONE_4_DECISION],
        )
        
        if success:
            await self._emit_zone_event(
                request_id, BlackboardZone.ZONE_4_DECISION, "write"
            )
            
            if decision.status == "decided":
                await self._emit_event(
                    BlackboardEventType.DECISION_MADE,
                    request_id=request_id,
                    blackboard_id="",
                    source_component="decision",
                    source_zone=BlackboardZone.ZONE_4_DECISION,
                    payload={
                        "decision_id": decision.decision_id,
                        "selected_campaign": decision.selected_campaign_id,
                        "primary_mechanism": decision.primary_mechanism,
                    },
                )
        
        return success
    
    async def read_zone4(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.META_LEARNER,
    ) -> Optional[DecisionState]:
        """Read from Zone 4 (decision state)."""
        if not check_access(BlackboardZone.ZONE_4_DECISION, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 4")
            return None
        
        key = f"adam:blackboard:{request_id}:zone4"
        return await self.cache.get(key, DecisionState)
    
    # -------------------------------------------------------------------------
    # ZONE 5: LEARNING SIGNALS
    # -------------------------------------------------------------------------
    
    async def write_zone5_from_unified(
        self,
        signal: "UnifiedLearningSignal",
        role: ComponentRole = ComponentRole.GRADIENT_BRIDGE,
    ) -> bool:
        """
        Write a UnifiedLearningSignal to Zone 5.
        
        Converts from UnifiedLearningSignal format to ComponentSignal for storage.
        This enables the Synergistic Brain Architecture's Zone 5 integration.
        """
        # Convert UnifiedLearningSignal to ComponentSignal
        from adam.blackboard.models import ComponentSignal, SignalType
        
        # Map unified signal type to legacy signal type
        type_mapping = {
            "outcome_success": SignalType.OUTCOME,
            "outcome_failure": SignalType.OUTCOME,
            "outcome_engagement": SignalType.OUTCOME,
            "credit_mechanism": SignalType.CREDIT,
            "credit_atom": SignalType.CREDIT,
            "credit_component": SignalType.CREDIT,
            "pattern_discovered": SignalType.LEARNING,
            "construct_emerged": SignalType.LEARNING,
        }
        
        signal_type_str = signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type)
        legacy_type = type_mapping.get(signal_type_str, SignalType.LEARNING)
        
        component_signal = ComponentSignal(
            signal_id=signal.signal_id,
            signal_type=legacy_type,
            source_component_id=signal.component,
            target_construct=signal.mechanism or "unknown",
            value=signal.value,
            confidence=1.0,
            metadata={
                "archetype": signal.archetype,
                "weight": signal.weight,
                "unified_type": signal_type_str,
                **signal.payload,
            },
        )
        
        # Use request_id from signal or generate one
        request_id = signal.request_id or signal.decision_id or signal.signal_id
        
        return await self.write_zone5_signal(request_id, component_signal, role)
    
    async def write_zone5_signal(
        self,
        request_id: str,
        signal: ComponentSignal,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> bool:
        """Write a learning signal to Zone 5."""
        if not check_access(BlackboardZone.ZONE_5_LEARNING, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 5")
            return False
        
        # Get or create aggregator
        aggregator = await self.read_zone5(request_id, role)
        if aggregator is None:
            aggregator = LearningSignalAggregator(
                request_id=request_id,
                user_id="",  # Will be set from context
            )
        
        aggregator.add_signal(signal)
        
        key = f"adam:blackboard:{request_id}:zone5"
        success = await self.cache.set(
            key,
            aggregator,
            ttl=ZONE_TTLS[BlackboardZone.ZONE_5_LEARNING],
        )
        
        if success:
            await self._emit_event(
                BlackboardEventType.LEARNING_SIGNAL_EMITTED,
                request_id=request_id,
                blackboard_id="",
                source_component=signal.source_component_id,
                source_zone=BlackboardZone.ZONE_5_LEARNING,
                payload={
                    "signal_id": signal.signal_id,
                    "target_construct": signal.target_construct,
                },
            )
        
        return success
    
    async def read_zone5(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.GRADIENT_BRIDGE,
    ) -> Optional[LearningSignalAggregator]:
        """Read from Zone 5 (learning signals)."""
        if not check_access(BlackboardZone.ZONE_5_LEARNING, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 5")
            return None
        
        key = f"adam:blackboard:{request_id}:zone5"
        return await self.cache.get(key, LearningSignalAggregator)
    
    # -------------------------------------------------------------------------
    # EVENT EMISSION
    # -------------------------------------------------------------------------
    
    async def _emit_event(
        self,
        event_type: BlackboardEventType,
        request_id: str,
        blackboard_id: str,
        source_component: str,
        source_zone: Optional[BlackboardZone] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a blackboard event."""
        event = BlackboardEvent(
            event_type=event_type,
            request_id=request_id,
            blackboard_id=blackboard_id,
            source_component=source_component,
            source_zone=source_zone,
            payload=payload or {},
        )
        
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.send(
                    ADAMTopics.EVENTS_DECISION,
                    value=event.model_dump(mode="json"),
                    key=request_id,
                )
        except Exception as e:
            logger.warning(f"Failed to emit blackboard event: {e}")
    
    async def _emit_zone_event(
        self,
        request_id: str,
        zone: BlackboardZone,
        operation: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a zone update event."""
        await self._emit_event(
            BlackboardEventType.ZONE_UPDATED,
            request_id=request_id,
            blackboard_id="",
            source_component="blackboard_service",
            source_zone=zone,
            payload={"operation": operation, **(payload or {})},
        )
    
    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------
    
    async def get_full_state(self, request_id: str) -> Dict[str, Any]:
        """Get the full blackboard state (all zones) for debugging."""
        state = {
            "request_id": request_id,
            "zone1": None,
            "zone2_atoms": {},
            "zone3": None,
            "zone4": None,
            "zone5": None,
        }
        
        # Zone 1
        z1 = await self.read_zone1(request_id, ComponentRole.GRADIENT_BRIDGE)
        if z1:
            state["zone1"] = z1.model_dump(mode="json")
        
        # Zone 2
        z2 = await self.read_zone2_all_atoms(request_id, ComponentRole.GRADIENT_BRIDGE)
        for atom_id, space in z2.atom_spaces.items():
            state["zone2_atoms"][atom_id] = space.model_dump(mode="json")
        
        # Zone 3
        z3 = await self.read_zone3(request_id, ComponentRole.GRADIENT_BRIDGE)
        if z3:
            state["zone3"] = z3.model_dump(mode="json")
        
        # Zone 4
        z4 = await self.read_zone4(request_id, ComponentRole.GRADIENT_BRIDGE)
        if z4:
            state["zone4"] = z4.model_dump(mode="json")
        
        # Zone 5
        z5 = await self.read_zone5(request_id, ComponentRole.GRADIENT_BRIDGE)
        if z5:
            state["zone5"] = z5.model_dump(mode="json")
        
        return state


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[BlackboardService] = None


def get_blackboard_service(redis_cache: Optional[ADAMRedisCache] = None) -> BlackboardService:
    """
    Get singleton BlackboardService instance.
    
    Used by:
    - dag_executor.py for atom coordination
    - campaign_orchestrator.py for campaign management
    - synergy_orchestrator.py for decision flow
    
    Args:
        redis_cache: Optional Redis cache. If not provided, creates one.
        
    Returns:
        BlackboardService singleton instance
    """
    global _service
    if _service is None:
        if redis_cache is None:
            # Create default Redis cache
            redis_cache = ADAMRedisCache()
        _service = BlackboardService(redis_cache=redis_cache)
    return _service
