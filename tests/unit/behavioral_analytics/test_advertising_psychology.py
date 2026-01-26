# =============================================================================
# ADAM Tests: Advertising Psychology Classifiers
# Location: tests/unit/behavioral_analytics/test_advertising_psychology.py
# =============================================================================

"""
Unit tests for advertising psychology classifiers.

Tests cover:
- Regulatory Focus Detector (OR = 2-6x CTR when matched)
- Cognitive State Estimator (d = 0.5-0.8)
- Approach-Avoidance Detector (BIS/BAS)
- Temporal Targeting Classifier (g = 0.475)
- Memory Optimizer (150% improvement)
- Moral Foundations Detector (d = 0.3-0.5)
- Evolutionary Motive Detector
- Personality Inferencer LIWC extension
"""

import pytest
from datetime import datetime, timedelta

from adam.behavioral_analytics.classifiers.regulatory_focus_detector import (
    RegulatoryFocusDetector,
    get_regulatory_focus_detector,
)
from adam.behavioral_analytics.classifiers.cognitive_state_estimator import (
    CognitiveStateEstimator,
    get_cognitive_state_estimator,
)
from adam.behavioral_analytics.classifiers.approach_avoidance_detector import (
    ApproachAvoidanceDetector,
    get_approach_avoidance_detector,
)
from adam.behavioral_analytics.classifiers.temporal_targeting import (
    TemporalTargetingClassifier,
    get_temporal_targeting_classifier,
    FunnelStage,
)
from adam.behavioral_analytics.classifiers.memory_optimizer import (
    MemoryOptimizer,
    get_memory_optimizer,
)
from adam.behavioral_analytics.classifiers.moral_foundations_targeting import (
    MoralFoundationsDetector,
    get_moral_foundations_detector,
)
from adam.behavioral_analytics.classifiers.evolutionary_motive_detector import (
    EvolutionaryMotiveDetector,
    get_evolutionary_motive_detector,
)
from adam.behavioral_analytics.classifiers.personality_inferencer import (
    PersonalityInferencer,
    get_personality_inferencer,
    BigFiveProfile,
)


# =============================================================================
# REGULATORY FOCUS DETECTOR TESTS
# =============================================================================

class TestRegulatoryFocusDetector:
    """Tests for regulatory focus detection."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        detector1 = get_regulatory_focus_detector()
        detector2 = get_regulatory_focus_detector()
        assert detector1 is detector2
    
    def test_detect_promotion_focus(self):
        """Test detection of promotion focus from text."""
        detector = RegulatoryFocusDetector()
        
        text = "I want to achieve my goals, advance my career, and gain new opportunities"
        detection = detector.detect_from_text(text)
        
        assert detection.focus_type == "promotion"
        assert detection.promotion_ratio > 0.6
        assert detection.recommended_frame == "gain"
        assert "abstract" in detection.recommended_construal
    
    def test_detect_prevention_focus(self):
        """Test detection of prevention focus from text."""
        detector = RegulatoryFocusDetector()
        
        text = "I need to protect my family, avoid risks, and stay safe and secure"
        detection = detector.detect_from_text(text)
        
        assert detection.focus_type == "prevention"
        assert detection.promotion_ratio < 0.4
        assert detection.recommended_frame == "loss_avoidance"
        assert "concrete" in detection.recommended_construal
    
    def test_neutral_focus(self):
        """Test neutral detection when no clear focus."""
        detector = RegulatoryFocusDetector()
        
        text = "The weather is nice today and I went for a walk"
        detection = detector.detect_from_text(text)
        
        assert detection.focus_type == "neutral"
    
    def test_behavioral_signals(self):
        """Test detection from behavioral signals."""
        detector = RegulatoryFocusDetector()
        
        detection = detector.detect_from_behavioral_signals(
            right_swipe_ratio=0.8,  # High approach
            approach_gestures=5,
            avoidance_gestures=1,
        )
        
        # High right swipe should indicate promotion
        assert detection.promotion_ratio > 0.5


# =============================================================================
# COGNITIVE STATE ESTIMATOR TESTS
# =============================================================================

class TestCognitiveStateEstimator:
    """Tests for cognitive state estimation."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        estimator1 = get_cognitive_state_estimator()
        estimator2 = get_cognitive_state_estimator()
        assert estimator1 is estimator2
    
    def test_peak_hour_detection(self):
        """Test cognitive peak detection at optimal hours."""
        estimator = CognitiveStateEstimator()
        
        # 10 AM is typically a cognitive peak
        estimation = estimator.estimate(hour=10, session_duration_minutes=0)
        
        assert estimation.is_at_cognitive_peak
        assert estimation.cognitive_load < 0.4
        assert estimation.processing_route in ["central", "mixed"]
    
    def test_trough_hour_detection(self):
        """Test cognitive trough detection at suboptimal hours."""
        estimator = CognitiveStateEstimator()
        
        # 3 AM is typically a cognitive trough
        estimation = estimator.estimate(hour=3, session_duration_minutes=0)
        
        assert not estimation.is_at_cognitive_peak
        assert estimation.cognitive_load > 0.6
        assert estimation.processing_route == "peripheral"
    
    def test_session_fatigue(self):
        """Test session fatigue increases load."""
        estimator = CognitiveStateEstimator()
        
        fresh = estimator.estimate(hour=10, session_duration_minutes=0)
        fatigued = estimator.estimate(hour=10, session_duration_minutes=60)
        
        assert fatigued.cognitive_load > fresh.cognitive_load
    
    def test_chronotype_matching(self):
        """Test chronotype synchrony effect."""
        estimator = CognitiveStateEstimator()
        
        # Morning type at 10 AM
        morning_at_peak = estimator.estimate(hour=10, chronotype="morning")
        assert morning_at_peak.synchrony_status == "at_peak"
        
        # Morning type at 8 PM
        morning_off_peak = estimator.estimate(hour=20, chronotype="morning")
        assert morning_off_peak.synchrony_status == "off_peak"


# =============================================================================
# APPROACH-AVOIDANCE DETECTOR TESTS
# =============================================================================

class TestApproachAvoidanceDetector:
    """Tests for BIS/BAS detection."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        detector1 = get_approach_avoidance_detector()
        detector2 = get_approach_avoidance_detector()
        assert detector1 is detector2
    
    def test_detect_bas_dominant(self):
        """Test detection of BAS-dominant orientation."""
        detector = ApproachAvoidanceDetector()
        
        text = "I'm excited and eager to try new adventures and achieve success"
        detection = detector.detect_from_text(text)
        
        assert detection.dominant_system == "BAS"
        assert detection.bas_score > detection.bis_score
        assert "excitement" in detection.recommended_appeals
    
    def test_detect_bis_dominant(self):
        """Test detection of BIS-dominant orientation."""
        detector = ApproachAvoidanceDetector()
        
        text = "I'm worried and need to stay safe, protect myself from risks"
        detection = detector.detect_from_text(text)
        
        assert detection.dominant_system == "BIS"
        assert detection.bis_score > detection.bas_score
        assert "security" in detection.recommended_appeals


# =============================================================================
# TEMPORAL TARGETING TESTS
# =============================================================================

class TestTemporalTargetingClassifier:
    """Tests for temporal targeting and construal level."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        classifier1 = get_temporal_targeting_classifier()
        classifier2 = get_temporal_targeting_classifier()
        assert classifier1 is classifier2
    
    def test_awareness_stage_construal(self):
        """Test high construal for awareness stage."""
        classifier = TemporalTargetingClassifier()
        
        rec = classifier.get_recommendation(funnel_stage="awareness")
        
        assert rec.funnel_stage == FunnelStage.AWARENESS
        assert "high" in rec.construal_level.lower() or "abstract" in rec.construal_level.lower()
        assert "WHY" in rec.message_focus
    
    def test_purchase_stage_construal(self):
        """Test low construal for purchase stage."""
        classifier = TemporalTargetingClassifier()
        
        rec = classifier.get_recommendation(funnel_stage="purchase")
        
        assert rec.funnel_stage == FunnelStage.PURCHASE
        assert "low" in rec.construal_level.lower() or "concrete" in rec.construal_level.lower()
        assert "ACTION" in rec.message_focus or "HOW" in rec.message_focus
    
    def test_weekend_hedonic(self):
        """Test weekend triggers hedonic mode."""
        classifier = TemporalTargetingClassifier()
        
        rec = classifier.get_recommendation(day_of_week=5)  # Saturday
        
        assert rec.is_weekend
        assert rec.shopping_mode == "hedonic"


# =============================================================================
# MEMORY OPTIMIZER TESTS
# =============================================================================

class TestMemoryOptimizer:
    """Tests for memory optimization."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        optimizer1 = get_memory_optimizer()
        optimizer2 = get_memory_optimizer()
        assert optimizer1 is optimizer2
    
    def test_spacing_effect(self):
        """Test optimal gap calculation for spacing effect."""
        optimizer = MemoryOptimizer()
        
        result = optimizer.optimize(retention_goal_days=7)
        
        # 1-week retention should have ~1 day optimal gap
        assert 0.5 <= result.optimal_gap_days <= 2.0
        assert result.spacing_effect_size == "150% improvement"
    
    def test_fatigue_detection(self):
        """Test ad fatigue detection."""
        optimizer = MemoryOptimizer()
        
        # Low exposure - not fatigued
        low = optimizer.optimize(exposures_this_week=1, exposures_total=3)
        assert not low.is_fatigued
        assert low.should_show_ad
        
        # High exposure - fatigued
        high = optimizer.optimize(exposures_this_week=10, exposures_total=30)
        assert high.is_fatigued
        assert not high.should_show_ad
    
    def test_mere_exposure_optimal(self):
        """Test mere exposure optimal range detection."""
        optimizer = MemoryOptimizer()
        
        # Optimal range: 10-20 exposures
        optimal = optimizer.optimize(exposures_total=15)
        assert optimal.mere_exposure_optimal
        
        # Below optimal
        below = optimizer.optimize(exposures_total=5)
        assert not below.mere_exposure_optimal
        
        # Above optimal
        above = optimizer.optimize(exposures_total=25)
        assert not above.mere_exposure_optimal
    
    def test_peak_end_structure(self):
        """Test peak-end rule recommendations."""
        optimizer = MemoryOptimizer()
        
        result = optimizer.optimize(ad_duration_seconds=15)
        
        assert result.peak_position_pct == 67.0  # 2/3 through
        assert result.peak_investment_pct == 70.0  # 70% on peak
        assert result.ending_investment_pct == 20.0  # 20% on ending


# =============================================================================
# MORAL FOUNDATIONS TESTS
# =============================================================================

class TestMoralFoundationsDetector:
    """Tests for moral foundations detection."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        detector1 = get_moral_foundations_detector()
        detector2 = get_moral_foundations_detector()
        assert detector1 is detector2
    
    def test_detect_care_foundation(self):
        """Test detection of care/harm foundation."""
        detector = MoralFoundationsDetector()
        
        text = "I care about protecting children and helping the vulnerable"
        detection = detector.detect_from_text(text)
        
        assert "care_harm" in detection.dominant_foundations
        assert detection.care_harm > 0.5
    
    def test_detect_liberty_foundation(self):
        """Test detection of liberty/oppression foundation."""
        detector = MoralFoundationsDetector()
        
        text = "I value freedom, choice, and independence above all"
        detection = detector.detect_from_text(text)
        
        assert "liberty_oppression" in detection.dominant_foundations
        assert detection.liberty_oppression > 0.5


# =============================================================================
# EVOLUTIONARY MOTIVE TESTS
# =============================================================================

class TestEvolutionaryMotiveDetector:
    """Tests for evolutionary motive detection."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        detector1 = get_evolutionary_motive_detector()
        detector2 = get_evolutionary_motive_detector()
        assert detector1 is detector2
    
    def test_detect_fast_strategy(self):
        """Test detection of fast life history strategy."""
        detector = EvolutionaryMotiveDetector()
        
        text = "I want it now, today, immediately! Don't wait, act now!"
        detection = detector.detect_from_text(text)
        
        assert detection.life_history_strategy == "fast"
        assert detection.fast_strategy_score > detection.slow_strategy_score
    
    def test_detect_slow_strategy(self):
        """Test detection of slow life history strategy."""
        detector = EvolutionaryMotiveDetector()
        
        text = "I invest for the long-term, seeking lasting quality and future growth"
        detection = detector.detect_from_text(text)
        
        assert detection.life_history_strategy == "slow"
        assert detection.slow_strategy_score > detection.fast_strategy_score


# =============================================================================
# PERSONALITY INFERENCER LIWC TESTS
# =============================================================================

class TestPersonalityInferencerLIWC:
    """Tests for LIWC-based personality inference."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        inferencer1 = get_personality_inferencer()
        inferencer2 = get_personality_inferencer()
        assert inferencer1 is inferencer2
    
    def test_liwc_extraversion(self):
        """Test LIWC inference of extraversion from positive emotion."""
        inferencer = PersonalityInferencer()
        
        # Text with lots of positive emotion words
        text = "I love this! It's amazing and wonderful! " * 100  # Repeat for word count
        profile = inferencer.infer_from_text(text)
        
        # Should infer higher extraversion from positive emotion
        assert profile.extraversion >= 0.5
    
    def test_liwc_neuroticism(self):
        """Test LIWC inference of neuroticism from negative emotion."""
        inferencer = PersonalityInferencer()
        
        # Text with negative emotion words
        text = "I'm worried and anxious, afraid and scared. " * 100
        profile = inferencer.infer_from_text(text)
        
        # Should infer higher neuroticism from negative emotion
        assert profile.neuroticism >= 0.5
    
    def test_low_word_count_warning(self):
        """Test low confidence with insufficient text."""
        inferencer = PersonalityInferencer()
        
        # Short text - insufficient for reliable inference
        short_text = "Hello world"
        profile = inferencer.infer_from_text(short_text, min_words=3000)
        
        # Should have low confidence
        assert profile.overall_confidence < 0.5


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestClassifierIntegration:
    """Integration tests for classifier combinations."""
    
    def test_regulatory_focus_with_cognitive_state(self):
        """Test combining regulatory focus with cognitive state."""
        rf_detector = RegulatoryFocusDetector()
        cog_estimator = CognitiveStateEstimator()
        
        # Promotion focus
        rf_detection = rf_detector.detect_from_text("I want to achieve success")
        
        # At cognitive peak
        cog_estimation = cog_estimator.estimate(hour=10)
        
        # Should recommend strong arguments (central route) with gain framing
        assert rf_detection.recommended_frame == "gain"
        assert cog_estimation.processing_route in ["central", "mixed"]
    
    def test_temporal_with_memory(self):
        """Test combining temporal targeting with memory optimization."""
        temporal = TemporalTargetingClassifier()
        memory = MemoryOptimizer()
        
        # Get temporal recommendation
        temp_rec = temporal.get_recommendation(funnel_stage="consideration")
        
        # Get memory optimization
        mem_rec = memory.optimize(
            retention_goal_days=14,
            last_exposure=datetime.now() - timedelta(days=2),
        )
        
        # Both should provide actionable recommendations
        assert temp_rec.construal_level != ""
        assert mem_rec.should_show_ad is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
