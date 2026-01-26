# =============================================================================
# ADAM Blackboard Unit Tests
# Location: tests/unit/test_blackboard.py
# =============================================================================

"""
BLACKBOARD UNIT TESTS

Tests for the 5-zone blackboard architecture.
"""

import pytest
from datetime import datetime, timezone

from adam.blackboard.models.core import (
    BlackboardZone,
    ComponentRole,
    ZoneAccessMode,
    check_access,
)
from adam.blackboard.models.zone1_context import RequestContext
from adam.blackboard.models.zone2_reasoning import AtomReasoningSpace, AtomType
from adam.blackboard.models.zone5_learning import ComponentSignal, SignalSource


# =============================================================================
# ZONE ACCESS CONTROL TESTS
# =============================================================================

class TestZoneAccessControl:
    """Tests for zone access control matrix."""
    
    def test_request_handler_can_write_zone1(self):
        """Request handler should have write access to Zone 1."""
        assert check_access(
            BlackboardZone.ZONE_1_CONTEXT,
            ComponentRole.REQUEST_HANDLER,
            ZoneAccessMode.WRITE,
        )
    
    def test_atom_cannot_write_zone1(self):
        """Atoms should not be able to write to Zone 1."""
        assert not check_access(
            BlackboardZone.ZONE_1_CONTEXT,
            ComponentRole.ATOM,
            ZoneAccessMode.WRITE,
        )
    
    def test_atom_can_read_zone1(self):
        """Atoms should be able to read Zone 1."""
        assert check_access(
            BlackboardZone.ZONE_1_CONTEXT,
            ComponentRole.ATOM,
            ZoneAccessMode.READ,
        )
    
    def test_atom_can_write_zone2(self):
        """Atoms should be able to write to Zone 2."""
        assert check_access(
            BlackboardZone.ZONE_2_REASONING,
            ComponentRole.ATOM,
            ZoneAccessMode.WRITE,
        )
    
    def test_synthesis_can_read_zone2(self):
        """Synthesis should be able to read Zone 2."""
        assert check_access(
            BlackboardZone.ZONE_2_REASONING,
            ComponentRole.SYNTHESIS,
            ZoneAccessMode.READ,
        )
    
    def test_gradient_bridge_can_read_zone5(self):
        """Gradient bridge should be able to read Zone 5."""
        assert check_access(
            BlackboardZone.ZONE_5_LEARNING,
            ComponentRole.GRADIENT_BRIDGE,
            ZoneAccessMode.READ,
        )


# =============================================================================
# BLACKBOARD SERVICE TESTS
# =============================================================================

class TestBlackboardService:
    """Tests for BlackboardService."""
    
    @pytest.mark.asyncio
    async def test_create_blackboard(self, blackboard, request_id, user_id):
        """Test creating a new blackboard."""
        state = await blackboard.create_blackboard(
            request_id=request_id,
            user_id=user_id,
        )
        
        assert state.request_id == request_id
        assert state.user_id == user_id
        assert state.status == "active"
    
    @pytest.mark.asyncio
    async def test_write_and_read_zone1(self, blackboard, request_id, user_id, request_context_factory):
        """Test writing and reading Zone 1."""
        # Create blackboard first
        await blackboard.create_blackboard(request_id, user_id)
        
        # Create context with required user_intelligence
        context = request_context_factory(request_id=request_id, user_id=user_id)
        
        # Write
        success = await blackboard.write_zone1(
            request_id,
            context,
            role=ComponentRole.REQUEST_HANDLER,
        )
        assert success
        
        # Read
        retrieved = await blackboard.read_zone1(
            request_id,
            role=ComponentRole.ATOM,
        )
        assert retrieved is not None
        assert retrieved.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_write_zone2_atom(self, blackboard, request_id, user_id):
        """Test writing atom reasoning space to Zone 2."""
        await blackboard.create_blackboard(request_id, user_id)
        
        space = AtomReasoningSpace(
            request_id=request_id,
            atom_id="atom_regulatory_focus",
            atom_type=AtomType.REGULATORY_FOCUS,
        )
        space.start()
        
        success = await blackboard.write_zone2_atom(
            request_id,
            "atom_regulatory_focus",
            space,
            role=ComponentRole.ATOM,
        )
        
        assert success
    
    @pytest.mark.asyncio
    async def test_write_zone5_signal(self, blackboard, request_id, user_id):
        """Test writing learning signal to Zone 5."""
        await blackboard.create_blackboard(request_id, user_id)
        
        signal = ComponentSignal(
            source=SignalSource.ATOM,
            source_component_id="atom_regulatory_focus",
            source_component_type="regulatory_focus",
            target_construct="regulatory_focus",
            signal_type="atom_output",
            signal_value=0.7,
            request_id=request_id,
        )
        
        success = await blackboard.write_zone5_signal(
            request_id,
            signal,
            role=ComponentRole.ATOM,
        )
        
        assert success
    
    @pytest.mark.asyncio
    async def test_access_denied_wrong_role(self, blackboard, request_id, user_id, request_context_factory):
        """Test that wrong role gets access denied."""
        await blackboard.create_blackboard(request_id, user_id)
        
        # Create context with required user_intelligence
        context = request_context_factory(request_id=request_id, user_id=user_id)
        
        # Atom cannot write to Zone 1
        success = await blackboard.write_zone1(
            request_id,
            context,
            role=ComponentRole.ATOM,
        )
        
        assert not success
    
    @pytest.mark.asyncio
    async def test_complete_blackboard(self, blackboard, request_id, user_id):
        """Test completing a blackboard."""
        state = await blackboard.create_blackboard(request_id, user_id)
        assert state.status == "active"
        
        await blackboard.complete_blackboard(request_id)
        
        retrieved = await blackboard.get_blackboard(request_id)
        assert retrieved.status == "completed"
