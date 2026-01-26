# =============================================================================
# ADAM In-Memory Blackboard (for demo/testing without Redis)
# Location: adam/blackboard/memory_blackboard.py
# =============================================================================

"""
IN-MEMORY BLACKBOARD SERVICE

A lightweight in-memory implementation of BlackboardService for use when
Redis is not available. Suitable for demos, testing, and single-request
processing.

Note: This does NOT provide persistence or cross-process sharing.
For production, use the Redis-backed BlackboardService.
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

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class InMemoryBlackboardService:
    """
    In-memory implementation of BlackboardService.
    
    Uses Python dictionaries instead of Redis for storage.
    Suitable for single-process demo/testing scenarios.
    """
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
        self._pubsub_channels: Dict[str, asyncio.Queue] = {}
        logger.info("InMemoryBlackboardService initialized (no Redis required)")
    
    # -------------------------------------------------------------------------
    # BLACKBOARD LIFECYCLE
    # -------------------------------------------------------------------------
    
    async def create_blackboard(
        self,
        request_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> BlackboardState:
        """Create a new blackboard for a request."""
        blackboard = BlackboardState(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )
        blackboard.initialize_zones()
        
        # Store in memory
        meta_key = f"adam:blackboard:{request_id}:meta"
        self._storage[meta_key] = blackboard.model_dump()
        
        logger.debug(f"Created in-memory blackboard for request {request_id}")
        return blackboard
    
    async def get_blackboard(self, request_id: str) -> Optional[BlackboardState]:
        """Get blackboard metadata."""
        meta_key = f"adam:blackboard:{request_id}:meta"
        data = self._storage.get(meta_key)
        if data:
            return BlackboardState.model_validate(data)
        return None
    
    async def complete_blackboard(self, request_id: str) -> None:
        """Mark a blackboard as complete."""
        blackboard = await self.get_blackboard(request_id)
        if blackboard:
            blackboard.complete()
            meta_key = f"adam:blackboard:{request_id}:meta"
            self._storage[meta_key] = blackboard.model_dump()
    
    # -------------------------------------------------------------------------
    # ZONE 1: REQUEST CONTEXT
    # -------------------------------------------------------------------------
    
    async def write_zone1(
        self,
        request_id: str,
        context: RequestContext,
        role: ComponentRole = ComponentRole.REQUEST_HANDLER,
    ) -> bool:
        """Write to Zone 1 (Request Context)."""
        if not check_access(BlackboardZone.ZONE_1_CONTEXT, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 1")
            return False
        
        key = f"adam:blackboard:{request_id}:zone1"
        self._storage[key] = context.model_dump()
        return True
    
    async def read_zone1(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> Optional[RequestContext]:
        """Read from Zone 1."""
        if not check_access(BlackboardZone.ZONE_1_CONTEXT, role, ZoneAccessMode.READ):
            logger.warning(f"Access denied: {role} cannot read Zone 1")
            return None
        
        key = f"adam:blackboard:{request_id}:zone1"
        data = self._storage.get(key)
        if data:
            return RequestContext.model_validate(data)
        return None
    
    # -------------------------------------------------------------------------
    # ZONE 2: ATOM REASONING SPACES
    # -------------------------------------------------------------------------
    
    async def write_zone2(
        self,
        request_id: str,
        atom_type: AtomType,
        reasoning: AtomReasoningSpace,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> bool:
        """Write to Zone 2 (Atom Reasoning Space)."""
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 2")
            return False
        
        key = f"adam:blackboard:{request_id}:zone2:{atom_type.value}"
        self._storage[key] = reasoning.model_dump()
        return True
    
    async def write_zone2_atom(
        self,
        request_id: str,
        atom_id: str,
        space: AtomReasoningSpace,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> bool:
        """
        Write to Zone 2 (atom reasoning space).
        
        Each atom writes to its own namespace by atom_id.
        """
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.WRITE):
            logger.warning(f"Access denied: {role} cannot write to Zone 2")
            return False
        
        key = f"adam:blackboard:{request_id}:zone2:{atom_id}"
        self._storage[key] = space.model_dump()
        return True
    
    async def read_zone2_atom(
        self,
        request_id: str,
        atom_id: str,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> Optional[AtomReasoningSpace]:
        """Read a specific atom's reasoning space by atom_id."""
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.READ):
            return None
        
        key = f"adam:blackboard:{request_id}:zone2:{atom_id}"
        data = self._storage.get(key)
        if data:
            return AtomReasoningSpace.model_validate(data)
        return None
    
    async def read_zone2(
        self,
        request_id: str,
        atom_type: AtomType,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> Optional[AtomReasoningSpace]:
        """Read a specific atom's reasoning space."""
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.READ):
            return None
        
        key = f"adam:blackboard:{request_id}:zone2:{atom_type.value}"
        data = self._storage.get(key)
        if data:
            return AtomReasoningSpace.model_validate(data)
        return None
    
    async def read_all_zone2(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.SYNTHESIS,
    ) -> Zone2Aggregate:
        """Read all Zone 2 reasoning spaces."""
        if not check_access(BlackboardZone.ZONE_2_REASONING, role, ZoneAccessMode.READ):
            return Zone2Aggregate()
        
        aggregate = Zone2Aggregate()
        prefix = f"adam:blackboard:{request_id}:zone2:"
        
        for key, data in self._storage.items():
            if key.startswith(prefix):
                atom_type_str = key.replace(prefix, "")
                try:
                    atom_type = AtomType(atom_type_str)
                    reasoning = AtomReasoningSpace.model_validate(data)
                    aggregate.atom_spaces[atom_type] = reasoning
                except (ValueError, Exception):
                    pass
        
        return aggregate
    
    # -------------------------------------------------------------------------
    # ZONE 3: SYNTHESIS WORKSPACE
    # -------------------------------------------------------------------------
    
    async def write_zone3(
        self,
        request_id: str,
        synthesis: SynthesisWorkspace,
        role: ComponentRole = ComponentRole.SYNTHESIS,
    ) -> bool:
        """Write to Zone 3."""
        if not check_access(BlackboardZone.ZONE_3_SYNTHESIS, role, ZoneAccessMode.WRITE):
            return False
        
        key = f"adam:blackboard:{request_id}:zone3"
        self._storage[key] = synthesis.model_dump()
        return True
    
    async def read_zone3(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.META_LEARNER,
    ) -> Optional[SynthesisWorkspace]:
        """Read Zone 3."""
        if not check_access(BlackboardZone.ZONE_3_SYNTHESIS, role, ZoneAccessMode.READ):
            return None
        
        key = f"adam:blackboard:{request_id}:zone3"
        data = self._storage.get(key)
        if data:
            return SynthesisWorkspace.model_validate(data)
        return None
    
    # -------------------------------------------------------------------------
    # ZONE 4: DECISION STATE
    # -------------------------------------------------------------------------
    
    async def write_zone4(
        self,
        request_id: str,
        decision: DecisionState,
        role: ComponentRole = ComponentRole.META_LEARNER,
    ) -> bool:
        """Write to Zone 4."""
        if not check_access(BlackboardZone.ZONE_4_DECISION, role, ZoneAccessMode.WRITE):
            return False
        
        key = f"adam:blackboard:{request_id}:zone4"
        self._storage[key] = decision.model_dump()
        return True
    
    async def read_zone4(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.META_LEARNER,
    ) -> Optional[DecisionState]:
        """Read Zone 4."""
        if not check_access(BlackboardZone.ZONE_4_DECISION, role, ZoneAccessMode.READ):
            return None
        
        key = f"adam:blackboard:{request_id}:zone4"
        data = self._storage.get(key)
        if data:
            return DecisionState.model_validate(data)
        return None
    
    # -------------------------------------------------------------------------
    # ZONE 5: LEARNING SIGNALS
    # -------------------------------------------------------------------------
    
    async def add_learning_signal(
        self,
        request_id: str,
        signal: ComponentSignal,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> bool:
        """Add a learning signal to Zone 5."""
        if not check_access(BlackboardZone.ZONE_5_LEARNING, role, ZoneAccessMode.WRITE):
            return False
        
        key = f"adam:blackboard:{request_id}:zone5:signals"
        signals = self._storage.get(key, [])
        signals.append(signal.model_dump())
        self._storage[key] = signals
        return True
    
    async def write_zone5_signal(
        self,
        request_id: str,
        signal: ComponentSignal,
        role: ComponentRole = ComponentRole.ATOM,
    ) -> bool:
        """
        Write a learning signal to Zone 5.
        
        Alias for add_learning_signal for API compatibility.
        """
        return await self.add_learning_signal(request_id, signal, role)
    
    async def read_zone5(
        self,
        request_id: str,
        role: ComponentRole = ComponentRole.GRADIENT_BRIDGE,
    ) -> Optional[LearningSignalAggregator]:
        """Read Zone 5."""
        if not check_access(BlackboardZone.ZONE_5_LEARNING, role, ZoneAccessMode.READ):
            return None
        
        key = f"adam:blackboard:{request_id}:zone5:signals"
        signals_data = self._storage.get(key, [])
        
        aggregator = LearningSignalAggregator(request_id=request_id)
        for signal_data in signals_data:
            aggregator.signals.append(ComponentSignal.model_validate(signal_data))
        
        return aggregator
    
    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------
    
    def clear(self) -> None:
        """Clear all in-memory storage."""
        self._storage.clear()
        logger.debug("In-memory blackboard storage cleared")
    
    def get_storage_size(self) -> int:
        """Get number of keys in storage."""
        return len(self._storage)


# Singleton instance for demo use
_memory_blackboard: Optional[InMemoryBlackboardService] = None


def get_memory_blackboard() -> InMemoryBlackboardService:
    """Get the singleton in-memory blackboard instance."""
    global _memory_blackboard
    if _memory_blackboard is None:
        _memory_blackboard = InMemoryBlackboardService()
    return _memory_blackboard
