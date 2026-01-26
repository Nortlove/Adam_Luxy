# =============================================================================
# ADAM User Services Unit Tests
# Location: tests/unit/test_user_services.py
# =============================================================================

"""
USER SERVICES UNIT TESTS

Tests for cold start, signal aggregation, identity, and journey tracking.
"""

import pytest
from datetime import datetime, timezone

from adam.user.cold_start.service import ColdStartContext
from adam.user.cold_start.archetypes import AMAZON_ARCHETYPES
from adam.user.signal_aggregation.processors import (
    RawSignal,
    SignalCategory,
)
from adam.user.identity.models import IdentityType


# =============================================================================
# COLD START TESTS
# =============================================================================

class TestColdStartService:
    """Tests for ColdStartService."""
    
    @pytest.mark.asyncio
    async def test_initialize_new_user(self, cold_start_service, user_id):
        """Test initializing a completely new user."""
        context = ColdStartContext(
            user_id=user_id,
            platform="iheart",
        )
        
        result = await cold_start_service.initialize_user(context)
        
        assert result.user_id == user_id
        assert result.overall_confidence >= 0.3
        assert result.big_five is not None
    
    @pytest.mark.asyncio
    async def test_station_format_prior(self, cold_start_service, user_id):
        """Test that station format provides personality priors."""
        context = ColdStartContext(
            user_id=user_id,
            platform="iheart",
            station_format="CHR",  # Contemporary Hit Radio
        )
        
        result = await cold_start_service.initialize_user(context)
        
        # CHR listeners tend to be more extraverted
        assert result.big_five.extraversion > 0.5
        assert "station:CHR" in result.sources_used
    
    @pytest.mark.asyncio
    async def test_archetype_matching(self, cold_start_service, user_id):
        """Test that archetypes are matched when signals available."""
        context = ColdStartContext(
            user_id=user_id,
            category="Electronics",
            platform="wpp",
        )
        
        result = await cold_start_service.initialize_user(context)
        
        # Should have matched an archetype
        if result.archetype_match:
            assert result.archetype_match.primary_archetype is not None
            assert result.archetype_match.primary_confidence > 0


# =============================================================================
# SIGNAL AGGREGATION TESTS
# =============================================================================

class TestSignalAggregationService:
    """Tests for SignalAggregationService."""
    
    @pytest.mark.asyncio
    async def test_process_audio_signal(
        self, signal_aggregation_service, user_id
    ):
        """Test processing an audio listening signal."""
        signal = RawSignal(
            signal_id="sig_001",
            user_id=user_id,
            session_id="test_session_001",
            category=SignalCategory.AUDIO_LISTENING,
            signal_type="track_listen",  # Use valid signal type
            raw_value={
                "event_type": "track_listen",  # Specify event type for processor
                "duration_seconds": 180,
                "completion_percentage": 95,
                "genre": "pop",
            },
        )
        
        processed = await signal_aggregation_service.process_signal(signal)
        
        assert len(processed) > 0
    
    @pytest.mark.asyncio
    async def test_user_profile_aggregation(
        self, signal_aggregation_service, user_id
    ):
        """Test aggregating multiple signals into profile."""
        # Add multiple signals
        for i in range(5):
            signal = RawSignal(
                signal_id=f"sig_{i}",
                user_id=user_id,
                session_id="test_session_002",
                category=SignalCategory.BEHAVIORAL,
                signal_type="click",
                raw_value={"action": "click", "duration": 10 + i},
            )
            await signal_aggregation_service.process_signal(signal)
        
        profile = await signal_aggregation_service.get_user_profile(user_id)
        
        assert profile.user_id == user_id
        assert profile.signal_counts.get(SignalCategory.BEHAVIORAL.value, 0) >= 5
    
    @pytest.mark.asyncio
    async def test_signal_windowing(
        self, signal_aggregation_service, user_id
    ):
        """Test creating time-windowed signal aggregates."""
        # Add signals
        for i in range(10):
            signal = RawSignal(
                signal_id=f"sig_{i}",
                user_id=user_id,
                session_id="test_session_003",
                category=SignalCategory.BEHAVIORAL,
                signal_type="view",
                raw_value={"value": i * 0.1},
            )
            await signal_aggregation_service.process_signal(signal)
        
        window = await signal_aggregation_service.create_window(
            user_id, window_minutes=30
        )
        
        if window:
            assert window.user_id == user_id
            assert window.signal_count >= 1


# =============================================================================
# IDENTITY RESOLUTION TESTS
# =============================================================================

class TestIdentityResolutionService:
    """Tests for IdentityResolutionService."""
    
    @pytest.mark.asyncio
    async def test_resolve_new_identity(self, identity_service):
        """Test resolving a new identity creates unified record."""
        unified = await identity_service.resolve_identity(
            platform="iheart",
            identity_type=IdentityType.FIRST_PARTY,
            identity_value="iheart_user_123",
        )
        
        assert unified.adam_id.startswith("adam_")
        assert "iheart" in unified.platform_ids
    
    @pytest.mark.asyncio
    async def test_resolve_existing_identity(self, identity_service):
        """Test resolving existing identity returns same record."""
        # First resolution
        unified1 = await identity_service.resolve_identity(
            platform="iheart",
            identity_type=IdentityType.FIRST_PARTY,
            identity_value="iheart_user_456",
        )
        
        # Second resolution should return same
        unified2 = await identity_service.resolve_identity(
            platform="iheart",
            identity_type=IdentityType.FIRST_PARTY,
            identity_value="iheart_user_456",
        )
        
        assert unified1.adam_id == unified2.adam_id
    
    @pytest.mark.asyncio
    async def test_link_identities(self, identity_service):
        """Test linking two platform identities."""
        from adam.user.identity.models import PlatformIdentity
        
        iheart_identity = PlatformIdentity(
            platform="iheart",
            identity_type=IdentityType.FIRST_PARTY,
            identity_value="iheart_user_789",
        )
        
        wpp_identity = PlatformIdentity(
            platform="wpp",
            identity_type=IdentityType.FIRST_PARTY,
            identity_value="wpp_user_789",
        )
        
        unified = await identity_service.link_identities(
            iheart_identity,
            wpp_identity,
        )
        
        assert "iheart" in unified.platform_ids
        assert "wpp" in unified.platform_ids
        assert len(unified.matches) >= 1
    
    @pytest.mark.asyncio
    async def test_get_cross_platform_ids(self, identity_service):
        """Test getting all platform IDs for a user."""
        from adam.user.identity.models import PlatformIdentity
        
        # Create and link identities
        unified = await identity_service.resolve_identity(
            platform="iheart",
            identity_type=IdentityType.FIRST_PARTY,
            identity_value="cross_plat_001",
        )
        
        await identity_service.link_identities(
            PlatformIdentity(
                platform="iheart",
                identity_type=IdentityType.FIRST_PARTY,
                identity_value="cross_plat_001",
            ),
            PlatformIdentity(
                platform="wpp",
                identity_type=IdentityType.FIRST_PARTY,
                identity_value="cross_plat_wpp_001",
            ),
        )
        
        ids = await identity_service.get_cross_platform_ids(unified.adam_id)
        
        assert "iheart" in ids
        assert "wpp" in ids
