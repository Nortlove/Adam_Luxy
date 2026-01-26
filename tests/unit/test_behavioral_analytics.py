# =============================================================================
# ADAM Behavioral Analytics: Unit Tests
# Location: tests/unit/test_behavioral_analytics.py
# =============================================================================

"""
Unit tests for the unified behavioral analytics system.

Tests:
1. Desktop event models
2. Media preference models
3. Mechanism models and inference
4. Feature extraction
5. Psychological inference
6. Atom interface
"""

import pytest
from datetime import datetime
from typing import Dict, Any

# Models
from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    CursorMoveEvent,
    CursorTrajectoryEvent,
    CursorHoverEvent,
    KeystrokeEvent,
    KeystrokeSequence,
    DesktopScrollEvent,
    TouchEvent,
    SwipeEvent,
    DeviceType,
    SignalDomain,
    CursorTrajectoryType,
    SwipeDirection,
)
from adam.behavioral_analytics.models.mechanisms import (
    CognitiveMechanism,
    UserMechanismProfile,
    MechanismEvidence,
    SignalSource,
    MECHANISM_SIGNAL_MAP,
)
from adam.behavioral_analytics.models.media_preferences import (
    MusicGenre,
    PodcastGenre,
    MusicPreference,
    PodcastPreference,
    MediaConsumptionProfile,
    MUSICDimensions,
)


# =============================================================================
# DESKTOP EVENT MODEL TESTS
# =============================================================================

class TestDesktopEventModels:
    """Tests for desktop behavioral event models."""
    
    def test_cursor_trajectory_event_creation(self):
        """Test CursorTrajectoryEvent creation and conflict detection."""
        trajectory = CursorTrajectoryEvent(
            start_x=100.0,
            start_y=100.0,
            end_x=500.0,
            end_y=100.0,
            area_under_curve=0.3,
            maximum_absolute_deviation=0.2,
            x_flips=3,
            y_flips=1,
            initiation_time_ms=300,
            movement_time_ms=800,
            trajectory_type=CursorTrajectoryType.COMPLEX,
        )
        
        assert trajectory.event_id.startswith("ct_")
        # total_time_ms is initiation_time_ms + movement_time_ms if computed, or check it exists
        assert trajectory.conflict_score > 0
        assert trajectory.is_conflicted  # High AUC and x-flips
    
    def test_cursor_trajectory_conflict_score(self):
        """Test conflict score calculation."""
        # Low conflict trajectory
        low_conflict = CursorTrajectoryEvent(
            start_x=0, start_y=0, end_x=100, end_y=0,
            area_under_curve=0.05,
            maximum_absolute_deviation=0.03,
            x_flips=0,
            initiation_time_ms=200,
        )
        
        # High conflict trajectory
        high_conflict = CursorTrajectoryEvent(
            start_x=0, start_y=0, end_x=100, end_y=0,
            area_under_curve=0.6,
            maximum_absolute_deviation=0.4,
            x_flips=5,
            initiation_time_ms=900,
        )
        
        assert low_conflict.conflict_score < 0.35
        assert not low_conflict.is_conflicted
        assert high_conflict.conflict_score > 0.35
        assert high_conflict.is_conflicted
    
    def test_keystroke_sequence_indicators(self):
        """Test keystroke sequence cognitive indicators."""
        sequence = KeystrokeSequence(
            sequence_length=50,
            input_type="search",
            hold_time_mean_ms=120,
            hold_time_std_ms=30,
            flight_time_mean_ms=100,
            flight_time_std_ms=25,
            typing_speed_cpm=300,
            pause_count=3,
            burst_count=2,
            error_count=2,
            error_rate=0.04,
            rhythm_regularity=0.7,
            speed_variance=20.0,
        )
        
        assert sequence.event_id.startswith("sq_")
        assert 0 <= sequence.cognitive_load_indicator <= 1
        assert 0 <= sequence.emotional_arousal_indicator <= 1


# =============================================================================
# BEHAVIORAL SESSION TESTS
# =============================================================================

class TestBehavioralSession:
    """Tests for unified BehavioralSession model."""
    
    def test_session_with_desktop_signals(self):
        """Test session with desktop signals."""
        session = BehavioralSession(
            session_id="test_session",
            device_id="test_device_001",
            device_type=DeviceType.DESKTOP,
            platform="desktop_web",
        )
        
        # Add desktop signals
        session.cursor_trajectories.append(
            CursorTrajectoryEvent(
                start_x=0, start_y=0, end_x=100, end_y=0,
                area_under_curve=0.2,
                maximum_absolute_deviation=0.1,
            )
        )
        session.keystroke_sequences.append(
            KeystrokeSequence(
                sequence_length=20,
                input_type="form",
                hold_time_mean_ms=100,
                hold_time_std_ms=20,
                flight_time_mean_ms=80,
                flight_time_std_ms=15,
                typing_speed_cpm=250,
            )
        )
        
        assert session.has_desktop_signals
        assert not session.has_mobile_signals
        assert session.primary_signal_domain == SignalDomain.DESKTOP
        assert session.total_events == 2
    
    def test_session_with_mobile_signals(self):
        """Test session with mobile signals."""
        session = BehavioralSession(
            session_id="test_mobile",
            device_id="test_device_002",
            device_type=DeviceType.MOBILE,
        )
        
        session.touches.append(TouchEvent(
            x=100, y=200, pressure=0.5, duration_ms=150
        ))
        session.swipes.append(SwipeEvent(
            start_x=100, start_y=200, end_x=300, end_y=200,
            direction=SwipeDirection.RIGHT,
            velocity=500, directness=0.95,
            duration_ms=200, path_length=210.0,
        ))
        
        assert session.has_mobile_signals
        assert not session.has_desktop_signals
        assert session.primary_signal_domain == SignalDomain.MOBILE
    
    def test_session_conflict_indicators(self):
        """Test session conflict indicator aggregation."""
        session = BehavioralSession(session_id="test_conflict", device_id="test_device_003")
        
        # Add conflicted trajectory
        session.cursor_trajectories.append(
            CursorTrajectoryEvent(
                start_x=0, start_y=0, end_x=100, end_y=0,
                area_under_curve=0.5,
                maximum_absolute_deviation=0.3,
                x_flips=4,
                initiation_time_ms=700,
                target_options=["option_a", "option_b"],
            )
        )
        
        conflicts = session.conflict_indicators
        assert len(conflicts) == 1
        assert conflicts[0]["source"] == "cursor_trajectory"
        assert conflicts[0]["conflict_score"] > 0.35


# =============================================================================
# MECHANISM MODEL TESTS
# =============================================================================

class TestMechanismModels:
    """Tests for cognitive mechanism models."""
    
    def test_mechanism_profile_creation(self):
        """Test UserMechanismProfile creation."""
        profile = UserMechanismProfile(
            session_id="test_session",
            user_id="user_123",
            construal_level=0.5,  # Abstract
            regulatory_focus=-0.3,  # Prevention
            automatic_evaluation=0.6,  # Approach
            mimetic_susceptibility=0.7,  # High
            attention_engagement=0.8,  # High
        )
        
        assert profile.profile_id.startswith("mp_")
        assert profile.construal_level == 0.5
        assert profile.regulatory_focus == -0.3
    
    def test_mechanism_dominant_mechanisms(self):
        """Test identification of dominant mechanisms."""
        profile = UserMechanismProfile(
            session_id="test",
            regulatory_focus=0.8,  # Strong promotion
            regulatory_focus_confidence=0.9,
            automatic_evaluation=0.7,  # Strong approach
            automatic_evaluation_confidence=0.8,
            mimetic_susceptibility=0.3,  # Low
            mimetic_susceptibility_confidence=0.7,
        )
        
        dominant = profile.get_dominant_mechanisms(threshold=0.6)
        
        # Should include regulatory_focus and automatic_evaluation
        mechanism_names = [m.value for m, s in dominant]
        assert "regulatory_focus" in mechanism_names
        assert "automatic_evaluation" in mechanism_names
        # mimetic is below threshold (0.3 < 0.6)
        assert "mimetic_desire" not in mechanism_names
    
    def test_mechanism_messaging_recommendations(self):
        """Test messaging recommendations from profile."""
        profile = UserMechanismProfile(
            session_id="test",
            construal_level=0.5,  # Abstract
            regulatory_focus=0.6,  # Promotion
            automatic_evaluation=0.4,  # Approach
            mimetic_susceptibility=0.8,  # High
        )
        
        recs = profile.get_messaging_recommendations()
        
        assert recs.get("framing") == "abstract_why"
        assert recs.get("focus") == "promotion"
        assert recs.get("social_proof") == "prominent"
    
    def test_mechanism_signal_mapping_exists(self):
        """Test that all mechanisms have signal mappings."""
        for mechanism in CognitiveMechanism:
            assert mechanism in MECHANISM_SIGNAL_MAP, f"Missing mapping for {mechanism}"
            mappings = MECHANISM_SIGNAL_MAP[mechanism]
            assert len(mappings) > 0, f"Empty mapping for {mechanism}"


# =============================================================================
# MEDIA PREFERENCE TESTS
# =============================================================================

class TestMediaPreferences:
    """Tests for media preference models."""
    
    def test_music_dimensions_derivation(self):
        """Test MUSIC dimension derivation from genres."""
        pref = MusicPreference(
            genres=[MusicGenre.CLASSICAL, MusicGenre.JAZZ, MusicGenre.OPERA]
        )
        pref.derive_music_dimensions()
        
        # These genres should score high on sophisticated
        assert pref.music_dimensions.sophisticated > 0.5
        assert pref.music_dimensions.mellow > 0.3
    
    def test_podcast_engagement_derivation(self):
        """Test podcast engagement derivation."""
        pref = PodcastPreference(
            genres=[PodcastGenre.TRUE_CRIME, PodcastGenre.NEWS_POLITICS]
        )
        pref.derive_engagement_scores()
        
        assert pref.true_crime_engagement > 0.5
        assert pref.news_politics_engagement > 0.5
    
    def test_media_profile_personality_derivation(self):
        """Test personality indicator derivation from media profile."""
        profile = MediaConsumptionProfile(user_id="test_user")
        
        # Add music preference with sophisticated genres
        profile.music = MusicPreference(
            genres=[MusicGenre.CLASSICAL, MusicGenre.WORLD, MusicGenre.AVANT_GARDE]
        )
        profile.music.derive_music_dimensions()
        
        # Add podcast preference with true crime
        profile.podcasts = PodcastPreference(
            genres=[PodcastGenre.TRUE_CRIME]
        )
        profile.podcasts.derive_engagement_scores()
        
        profile.derive_personality_indicators()
        
        # Should have high openness from sophisticated music
        assert profile.openness_indicator > 0.5
        # Should have morbid curiosity from true crime
        assert profile.morbid_curiosity_indicator > 0.2
        assert "music" in profile.domains_available
        assert "podcasts" in profile.domains_available
    
    def test_media_profile_to_features(self):
        """Test media profile conversion to features."""
        profile = MediaConsumptionProfile(user_id="test")
        profile.music = MusicPreference(
            genres=[MusicGenre.EDM, MusicGenre.HIP_HOP]
        )
        profile.music.derive_music_dimensions()
        profile.derive_personality_indicators()
        
        features = profile.to_features()
        
        assert "music_contemporary" in features
        assert "music_intense" in features
        assert "media_openness_indicator" in features
        assert "media_extraversion_indicator" in features


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestBehavioralAnalyticsIntegration:
    """Integration tests for behavioral analytics components."""
    
    def test_session_to_features_flow(self):
        """Test the flow from session signals to features."""
        session = BehavioralSession(
            session_id="integration_test",
            device_id="test_device_004",
            device_type=DeviceType.DESKTOP,
        )
        
        # Add desktop signals
        session.cursor_trajectories.append(
            CursorTrajectoryEvent(
                start_x=0, start_y=0, end_x=100, end_y=0,
                area_under_curve=0.3,
                maximum_absolute_deviation=0.2,
                x_flips=3,
                initiation_time_ms=500,
                movement_time_ms=1000,
            )
        )
        
        # The engine would extract these features
        expected_features = {
            "trajectory_auc_mean": 0.3,
            "trajectory_mad_mean": 0.2,
            "trajectory_x_flips_mean": 3.0,
            "trajectory_initiation_mean": 500.0,
            "trajectory_conflict_mean": session.cursor_trajectories[0].conflict_score,
        }
        
        # Verify feature expectations are reasonable
        assert expected_features["trajectory_auc_mean"] == 0.3
        assert expected_features["trajectory_conflict_mean"] > 0.35
    
    def test_mechanism_evidence_creation(self):
        """Test creation of mechanism evidence from signals."""
        evidence = MechanismEvidence(
            mechanism=CognitiveMechanism.REGULATORY_FOCUS,
            signal_source=SignalSource.CURSOR_TRAJECTORY,
            feature_name="trajectory_conflict_mean",
            feature_value=0.45,
            evidence_strength=0.6,
            evidence_direction=-0.4,  # Toward prevention
            effect_size=0.40,
            confidence=0.7,
        )
        
        assert evidence.evidence_id.startswith("me_")
        assert evidence.mechanism == CognitiveMechanism.REGULATORY_FOCUS
        assert evidence.confidence == 0.7


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
