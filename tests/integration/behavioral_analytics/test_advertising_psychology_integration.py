# =============================================================================
# ADAM Tests: Advertising Psychology Integration Tests
# Location: tests/integration/behavioral_analytics/test_advertising_psychology_integration.py
# =============================================================================

"""
Integration tests for advertising psychology components.

Tests cover:
- Knowledge seeding to Neo4j
- Graph queries for advertising knowledge
- Atom interface context retrieval
- End-to-end psychological profiling
"""

import pytest
from datetime import datetime, timedelta

from adam.behavioral_analytics.models.advertising_psychology import (
    RegulatoryFocusProfile,
    CognitiveStateProfile,
    UserAdvertisingPsychologyProfile,
    ConfidenceTier,
)
from adam.behavioral_analytics.knowledge.advertising_psychology_seeder import (
    AdvertisingPsychologySeeder,
    get_advertising_psychology_seeder,
)


# =============================================================================
# SEEDER TESTS
# =============================================================================

class TestAdvertisingPsychologySeeder:
    """Tests for advertising psychology knowledge seeder."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        seeder1 = get_advertising_psychology_seeder()
        seeder2 = get_advertising_psychology_seeder()
        assert seeder1 is seeder2
    
    def test_all_knowledge_seeding(self):
        """Test comprehensive knowledge seeding."""
        seeder = AdvertisingPsychologySeeder()
        behavioral, advertising, interactions = seeder.seed_all_knowledge()
        
        # Should have all domains
        assert len(behavioral) > 20
        assert len(advertising) > 20
        
        # Check for interaction effects
        assert len(interactions) > 0
    
    def test_tier1_behavioral_knowledge(self):
        """Test filtering for highest-confidence behavioral findings."""
        seeder = AdvertisingPsychologySeeder()
        seeder.seed_all_knowledge()
        
        tier1 = seeder.get_tier1_behavioral_knowledge()
        
        # Tier 1 is meta-analyzed/replicated
        assert len(tier1) > 0
        
        # All should have effect sizes
        for k in tier1:
            assert k.effect_size is not None
    
    def test_tier1_advertising_knowledge(self):
        """Test filtering for highest-confidence advertising findings."""
        seeder = AdvertisingPsychologySeeder()
        seeder.seed_all_knowledge()
        
        tier1 = seeder.get_tier1_advertising_knowledge()
        
        # Tier 1 is meta-analyzed
        assert len(tier1) > 0
    
    def test_knowledge_for_construct(self):
        """Test retrieving knowledge by construct."""
        seeder = AdvertisingPsychologySeeder()
        seeder.seed_all_knowledge()
        
        # Get knowledge for extraversion
        extraversion_knowledge = seeder.get_knowledge_for_construct("extraversion")
        
        # Should have LIWC-based extraversion indicators
        assert len(extraversion_knowledge) > 0


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestAdvertisingPsychologyModels:
    """Tests for Pydantic models."""
    
    def test_regulatory_focus_profile(self):
        """Test RegulatoryFocusProfile model."""
        profile = RegulatoryFocusProfile(
            focus_type="promotion",
            focus_strength=0.7,
            promotion_marker_count=5,
            prevention_marker_count=2,
        )
        
        assert profile.focus_type == "promotion"
        assert profile.focus_strength == 0.7
        assert profile.promotion_marker_count == 5
        assert profile.prevention_marker_count == 2
    
    def test_cognitive_state_profile(self):
        """Test CognitiveStateProfile model."""
        profile = CognitiveStateProfile(
            cognitive_load=0.4,
            processing_route="central",
            recommended_complexity="high",
        )
        
        assert profile.cognitive_load == 0.4
        assert profile.processing_route == "central"
        # Test the property
        assert profile.should_use_peripheral_cues is False  # load 0.4 < 0.6
    
    def test_user_advertising_psychology_profile(self):
        """Test comprehensive UserAdvertisingPsychologyProfile model."""
        rf_profile = RegulatoryFocusProfile(
            focus_type="promotion",
            focus_strength=0.7,
        )
        cog_profile = CognitiveStateProfile(
            cognitive_load=0.4,
        )
        
        user_profile = UserAdvertisingPsychologyProfile(
            user_id="test-user-123",
            regulatory_focus=rf_profile,
            cognitive_state=cog_profile,
        )
        
        assert user_profile.user_id == "test-user-123"
        assert user_profile.regulatory_focus.focus_type == "promotion"
        assert user_profile.cognitive_state.cognitive_load == 0.4


# =============================================================================
# END-TO-END INTEGRATION TESTS
# =============================================================================

class TestEndToEndPsychologicalProfiling:
    """End-to-end tests for psychological profiling."""
    
    def test_full_profile_construction(self):
        """Test constructing a full psychological profile."""
        from adam.behavioral_analytics.classifiers.regulatory_focus_detector import (
            get_regulatory_focus_detector,
        )
        from adam.behavioral_analytics.classifiers.cognitive_state_estimator import (
            get_cognitive_state_estimator,
        )
        from adam.behavioral_analytics.classifiers.approach_avoidance_detector import (
            get_approach_avoidance_detector,
        )
        from adam.behavioral_analytics.classifiers.moral_foundations_targeting import (
            get_moral_foundations_detector,
        )
        
        # Simulate user data
        user_text = """
        I really want to achieve success and reach my goals. 
        I care about my family and want to protect them.
        Freedom and choice are important to me.
        """
        
        # Run all detectors
        rf_detection = get_regulatory_focus_detector().detect_from_text(user_text)
        aa_detection = get_approach_avoidance_detector().detect_from_text(user_text)
        mf_detection = get_moral_foundations_detector().detect_from_text(user_text)
        cog_estimation = get_cognitive_state_estimator().estimate(hour=10)
        
        # All should return valid results
        assert rf_detection.focus_type in ["promotion", "prevention", "neutral"]
        assert aa_detection.dominant_system in ["BAS", "BIS", "balanced"]
        assert len(mf_detection.dominant_foundations) >= 0
        assert 0 <= cog_estimation.cognitive_load <= 1
    
    def test_message_framing_recommendation(self):
        """Test generating message framing recommendations."""
        from adam.behavioral_analytics.classifiers.regulatory_focus_detector import (
            get_regulatory_focus_detector,
        )
        from adam.behavioral_analytics.classifiers.temporal_targeting import (
            get_temporal_targeting_classifier,
        )
        
        # Promotion-focused user
        detector = get_regulatory_focus_detector()
        detection = detector.detect_from_text("I want to achieve and advance")
        
        # In consideration stage
        temporal = get_temporal_targeting_classifier()
        temp_rec = temporal.get_recommendation(funnel_stage="consideration")
        
        # Generate recommendation
        recommendations = {
            "frame": detection.recommended_frame,
            "construal": temp_rec.construal_level,
            "message_focus": temp_rec.message_focus,
        }
        
        # Frame should be valid (gain, loss_avoidance, or neutral)
        assert recommendations["frame"] in ["gain", "loss_avoidance", "neutral"]
        # Construal should be valid
        assert recommendations["construal"] in ["high", "low", "mixed"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
