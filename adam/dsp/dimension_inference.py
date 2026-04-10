"""
Dimension Inference Service
============================

Bridges the gap between incoming request data and the 7 psychological dimensions
required by GraphTypeInferenceService.

Input sources (any combination):
    - NDF profile (7 continuous dimensions)
    - Behavioral signals (mouse, scroll, navigation patterns)
    - Archetype detection result
    - Text content (review, ad copy)
    - Product category
    - Session/device context

Output: the 7 expanded type dimensions with confidence scores:
    - motivation (37 values)
    - decision_style (12 values)
    - regulatory_focus (8 values)
    - emotional_intensity (9 values)
    - cognitive_load (3 values)
    - temporal_orientation (4 values)
    - social_influence (5 values)

Handles partial data gracefully — uses population-mode defaults when evidence
is insufficient and increases confidence as more signals arrive.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Output Model
# ============================================================================

@dataclass
class InferredDimensions:
    """All 7 expanded type dimensions with confidence metadata."""
    motivation: str = "quality_assurance"
    decision_style: str = "satisficing"
    regulatory_focus: str = "pragmatic_balanced"
    emotional_intensity: str = "moderate_positive"
    cognitive_load: str = "moderate_cognitive"
    temporal_orientation: str = "medium_term"
    social_influence: str = "socially_aware"

    # Per-dimension confidence (0-1)
    confidence: Dict[str, float] = field(default_factory=lambda: {
        "motivation": 0.2,
        "decision_style": 0.2,
        "regulatory_focus": 0.2,
        "emotional_intensity": 0.2,
        "cognitive_load": 0.2,
        "temporal_orientation": 0.2,
        "social_influence": 0.2,
    })

    # Which evidence sources contributed
    evidence_sources: List[str] = field(default_factory=list)

    @property
    def overall_confidence(self) -> float:
        return sum(self.confidence.values()) / len(self.confidence)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motivation": self.motivation,
            "decision_style": self.decision_style,
            "regulatory_focus": self.regulatory_focus,
            "emotional_intensity": self.emotional_intensity,
            "cognitive_load": self.cognitive_load,
            "temporal_orientation": self.temporal_orientation,
            "social_influence": self.social_influence,
            "confidence": dict(self.confidence),
            "overall_confidence": self.overall_confidence,
            "evidence_sources": self.evidence_sources,
        }


# ============================================================================
# Mapping Tables
# ============================================================================

# Archetype → dominant motivation
ARCHETYPE_MOTIVATION_MAP = {
    "explorer": "pure_curiosity",
    "achiever": "goal_achievement",
    "connector": "belonging_affirmation",
    "guardian": "risk_mitigation",
    "analyst": "efficiency_optimization",
    "creator": "self_expression",
    "nurturer": "altruistic_giving",
    "pragmatist": "cost_minimization",
    "hero": "goal_achievement",
    "caregiver": "altruistic_giving",
    "lover": "social_enjoyment",
    "magician": "personal_growth",
}

# Archetype → regulatory focus
ARCHETYPE_REGULATORY_MAP = {
    "explorer": "optimistic_exploration",
    "achiever": "eager_advancement",
    "connector": "pragmatic_balanced",
    "guardian": "conservative_preservation",
    "analyst": "vigilant_security",
    "creator": "optimistic_exploration",
    "nurturer": "pragmatic_balanced",
    "pragmatist": "pragmatic_balanced",
    "hero": "eager_advancement",
    "caregiver": "conservative_preservation",
    "lover": "aspiration_driven",
    "magician": "aspiration_driven",
}

# Archetype → social influence type
ARCHETYPE_SOCIAL_MAP = {
    "explorer": "informational_seeker",
    "achiever": "opinion_leader",
    "connector": "normatively_driven",
    "guardian": "socially_aware",
    "analyst": "informational_seeker",
    "creator": "highly_independent",
    "nurturer": "socially_aware",
    "pragmatist": "highly_independent",
    "hero": "opinion_leader",
    "caregiver": "normatively_driven",
    "lover": "socially_aware",
    "magician": "informational_seeker",
}

# Category → motivation prior
CATEGORY_MOTIVATION_MAP = {
    "electronics": "mastery_seeking",
    "beauty": "self_expression",
    "health": "risk_mitigation",
    "baby": "risk_mitigation",
    "books": "pure_curiosity",
    "clothing": "self_expression",
    "grocery": "cost_minimization",
    "sports": "personal_growth",
    "home": "quality_assurance",
    "toys": "social_enjoyment",
    "automotive": "efficiency_optimization",
    "software": "problem_solving",
    "pet": "altruistic_giving",
    "office": "efficiency_optimization",
    "tools": "problem_solving",
    "garden": "quality_assurance",
    "music": "sensory_pleasure",
    "movies": "escapism",
    "games": "excitement_seeking",
    "jewelry": "status_signaling",
    "fashion": "self_expression",
    "food": "sensory_pleasure",
    "finance": "risk_mitigation",
    "insurance": "anxiety_reduction",
    "education": "mastery_seeking",
    "travel": "excitement_seeking",
}


# ============================================================================
# Service
# ============================================================================

class DimensionInferenceService:
    """
    Infers the 7 expanded type dimensions from available request data.

    Usage:
        service = DimensionInferenceService()
        dims = service.infer(
            ndf_profile={"approach_avoidance": 0.3, "cognitive_engagement": 0.8, ...},
            archetype="achiever",
            behavioral_signals={"scroll_velocity": 0.2, "time_on_page": 45.0},
            product_category="Electronics",
        )
        # dims.motivation = "mastery_seeking"
        # dims.decision_style = "analytical_systematic"
        # dims.overall_confidence = 0.72
    """

    def __init__(self, population_ndf: Optional[Dict[str, float]] = None):
        """
        Args:
            population_ndf: Population mean NDF values for relative comparisons.
                            If not provided, uses empirical defaults from 937M corpus.
        """
        self._pop_ndf = population_ndf or {
            "approach_avoidance": 0.05,
            "temporal_horizon": 0.10,
            "social_calibration": 0.26,
            "uncertainty_tolerance": 0.08,
            "status_sensitivity": 0.02,
            "cognitive_engagement": 0.05,
            "arousal_seeking": 0.15,
            "cognitive_velocity": 0.10,
        }

    def infer(
        self,
        ndf_profile: Optional[Dict[str, float]] = None,
        archetype: Optional[str] = None,
        behavioral_signals: Optional[Dict[str, float]] = None,
        product_category: Optional[str] = None,
        text: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> InferredDimensions:
        """
        Infer all 7 dimensions from available data sources.

        Each source contributes evidence with different confidence levels.
        Multiple sources are combined with confidence-weighted fusion.
        """
        result = InferredDimensions()
        sources = []

        # --- Source 1: NDF Profile (highest coverage — informs all 7) ---
        if ndf_profile and any(v != 0 for v in ndf_profile.values()):
            self._apply_ndf(result, ndf_profile)
            sources.append("ndf_profile")

        # --- Source 2: Archetype (strong prior for motivation, regulatory, social) ---
        if archetype:
            self._apply_archetype(result, archetype.lower())
            sources.append("archetype")

        # --- Source 3: Behavioral signals (good for cognitive_load, decision_style) ---
        if behavioral_signals:
            self._apply_behavioral(result, behavioral_signals, device_type)
            sources.append("behavioral_signals")

        # --- Source 4: Product category (motivation prior) ---
        if product_category:
            self._apply_category(result, product_category)
            sources.append("product_category")

        # --- Source 5: Text analysis (motivation, emotional_intensity) ---
        if text and len(text) > 20:
            self._apply_text(result, text)
            sources.append("text_analysis")

        result.evidence_sources = sources
        return result

    # ------------------------------------------------------------------
    # NDF → Dimensions
    # ------------------------------------------------------------------

    def _apply_ndf(self, result: InferredDimensions, ndf: Dict[str, float]):
        """Map NDF continuous dimensions to expanded type discrete values."""
        pop = self._pop_ndf

        # --- Decision Style (from cognitive_engagement + arousal_seeking) ---
        cognitive = ndf.get("cognitive_engagement", 0)
        arousal = ndf.get("arousal_seeking", 0)
        uncertainty = ndf.get("uncertainty_tolerance", 0)
        cog_mean = pop.get("cognitive_engagement", 0.05)
        arousal_mean = pop.get("arousal_seeking", 0.15)

        if cognitive > cog_mean * 2.0:
            result.decision_style = "analytical_systematic"
            result.confidence["decision_style"] = 0.75
        elif cognitive > cog_mean * 1.5:
            result.decision_style = "deliberative_reflective"
            result.confidence["decision_style"] = 0.65
        elif arousal > arousal_mean * 2.0:
            result.decision_style = "gut_instinct"
            result.confidence["decision_style"] = 0.7
        elif arousal > arousal_mean * 1.5:
            result.decision_style = "affect_driven"
            result.confidence["decision_style"] = 0.6
        elif uncertainty > 0.3:
            result.decision_style = "risk_calculating"
            result.confidence["decision_style"] = 0.55
        else:
            result.decision_style = "satisficing"
            result.confidence["decision_style"] = 0.45

        # --- Regulatory Focus (from approach_avoidance) ---
        approach = ndf.get("approach_avoidance", 0)
        if approach > 0.3:
            result.regulatory_focus = "eager_advancement"
            result.confidence["regulatory_focus"] = 0.7
        elif approach > 0.15:
            result.regulatory_focus = "aspiration_driven"
            result.confidence["regulatory_focus"] = 0.6
        elif approach > 0.0:
            result.regulatory_focus = "optimistic_exploration"
            result.confidence["regulatory_focus"] = 0.5
        elif approach > -0.1:
            result.regulatory_focus = "pragmatic_balanced"
            result.confidence["regulatory_focus"] = 0.45
        elif approach > -0.2:
            result.regulatory_focus = "situational_adaptive"
            result.confidence["regulatory_focus"] = 0.5
        elif approach > -0.3:
            result.regulatory_focus = "vigilant_security"
            result.confidence["regulatory_focus"] = 0.6
        else:
            result.regulatory_focus = "anxious_avoidance"
            result.confidence["regulatory_focus"] = 0.7

        # --- Emotional Intensity (from arousal_seeking + valence proxy) ---
        if arousal > arousal_mean * 2.0 and approach > 0:
            result.emotional_intensity = "high_positive_activation"
            result.confidence["emotional_intensity"] = 0.7
        elif arousal > arousal_mean * 2.0 and approach < 0:
            result.emotional_intensity = "high_negative_activation"
            result.confidence["emotional_intensity"] = 0.65
        elif arousal > arousal_mean * 1.5:
            result.emotional_intensity = "mixed_high_arousal"
            result.confidence["emotional_intensity"] = 0.55
        elif arousal > arousal_mean * 0.5:
            if approach > 0:
                result.emotional_intensity = "moderate_positive"
            else:
                result.emotional_intensity = "moderate_negative"
            result.confidence["emotional_intensity"] = 0.5
        elif arousal < arousal_mean * 0.3:
            result.emotional_intensity = "apathetic_disengaged"
            result.confidence["emotional_intensity"] = 0.6
        else:
            if approach > 0:
                result.emotional_intensity = "low_positive_calm"
            else:
                result.emotional_intensity = "low_negative_sad"
            result.confidence["emotional_intensity"] = 0.5

        # --- Temporal Orientation (from temporal_horizon) ---
        temporal = ndf.get("temporal_horizon", 0)
        temp_mean = pop.get("temporal_horizon", 0.10)
        if temporal > temp_mean * 3:
            result.temporal_orientation = "long_term_future"
            result.confidence["temporal_orientation"] = 0.7
        elif temporal > temp_mean * 1.5:
            result.temporal_orientation = "medium_term"
            result.confidence["temporal_orientation"] = 0.55
        elif temporal > temp_mean * 0.5:
            result.temporal_orientation = "short_term"
            result.confidence["temporal_orientation"] = 0.5
        else:
            result.temporal_orientation = "immediate_present"
            result.confidence["temporal_orientation"] = 0.6

        # --- Social Influence (from social_calibration) ---
        social = ndf.get("social_calibration", 0)
        social_mean = pop.get("social_calibration", 0.26)
        if social > social_mean * 2.0:
            result.social_influence = "normatively_driven"
            result.confidence["social_influence"] = 0.65
        elif social > social_mean * 1.5:
            result.social_influence = "socially_aware"
            result.confidence["social_influence"] = 0.55
        elif social > social_mean * 0.5:
            result.social_influence = "informational_seeker"
            result.confidence["social_influence"] = 0.5
        elif social < social_mean * 0.3:
            result.social_influence = "highly_independent"
            result.confidence["social_influence"] = 0.6
        else:
            result.social_influence = "opinion_leader"
            result.confidence["social_influence"] = 0.45

        # --- Cognitive Load (from cognitive_engagement + cognitive_velocity) ---
        velocity = ndf.get("cognitive_velocity", 0)
        if cognitive > cog_mean * 1.5 and velocity < 0.2:
            result.cognitive_load = "high_cognitive"
            result.confidence["cognitive_load"] = 0.65
        elif cognitive < cog_mean * 0.5 or velocity > 0.3:
            result.cognitive_load = "minimal_cognitive"
            result.confidence["cognitive_load"] = 0.6
        else:
            result.cognitive_load = "moderate_cognitive"
            result.confidence["cognitive_load"] = 0.45

        # --- Motivation (from NDF composite — lower confidence than archetype) ---
        status = ndf.get("status_sensitivity", 0)
        status_mean = pop.get("status_sensitivity", 0.02)
        if social > social_mean * 1.5:
            result.motivation = "social_approval"
            result.confidence["motivation"] = 0.45
        elif cognitive > cog_mean * 2:
            result.motivation = "mastery_seeking"
            result.confidence["motivation"] = 0.45
        elif status > status_mean * 3:
            result.motivation = "status_signaling"
            result.confidence["motivation"] = 0.5
        elif arousal > arousal_mean * 2:
            result.motivation = "excitement_seeking"
            result.confidence["motivation"] = 0.45
        elif approach < -0.2:
            result.motivation = "anxiety_reduction"
            result.confidence["motivation"] = 0.5
        else:
            result.motivation = "quality_assurance"
            result.confidence["motivation"] = 0.35

    # ------------------------------------------------------------------
    # Archetype → Dimensions (strong prior for 3 dimensions)
    # ------------------------------------------------------------------

    def _apply_archetype(self, result: InferredDimensions, archetype: str):
        """Apply archetype-based priors. Only overrides if higher confidence."""

        # Motivation (archetype is a strong prior — confidence 0.6)
        if archetype in ARCHETYPE_MOTIVATION_MAP:
            arch_conf = 0.6
            if arch_conf > result.confidence.get("motivation", 0):
                result.motivation = ARCHETYPE_MOTIVATION_MAP[archetype]
                result.confidence["motivation"] = arch_conf

        # Regulatory focus (archetype → focus, confidence 0.55)
        if archetype in ARCHETYPE_REGULATORY_MAP:
            arch_conf = 0.55
            if arch_conf > result.confidence.get("regulatory_focus", 0):
                result.regulatory_focus = ARCHETYPE_REGULATORY_MAP[archetype]
                result.confidence["regulatory_focus"] = arch_conf

        # Social influence (archetype → social type, confidence 0.5)
        if archetype in ARCHETYPE_SOCIAL_MAP:
            arch_conf = 0.5
            if arch_conf > result.confidence.get("social_influence", 0):
                result.social_influence = ARCHETYPE_SOCIAL_MAP[archetype]
                result.confidence["social_influence"] = arch_conf

    # ------------------------------------------------------------------
    # Behavioral Signals → Dimensions
    # ------------------------------------------------------------------

    def _apply_behavioral(
        self, result: InferredDimensions,
        signals: Dict[str, float],
        device_type: Optional[str] = None,
    ):
        """Infer dimensions from real-time behavioral signals."""

        # --- Cognitive Load from browsing behavior ---
        scroll_vel = signals.get("scroll_velocity", signals.get("scroll_velocity_pattern", 0))
        time_on_page = signals.get("time_on_page", signals.get("time_on_page_seconds", 0))
        pages_viewed = signals.get("pages_viewed", 0)
        comparison = signals.get("comparison_behavior", 0)

        cog_score = 0.5  # neutral
        if time_on_page > 60 and comparison > 0.5:
            cog_score = 0.9
        elif time_on_page > 30:
            cog_score = 0.7
        elif scroll_vel > 0.7 or time_on_page < 10:
            cog_score = 0.2

        if device_type and device_type.lower() == "mobile":
            cog_score *= 0.85  # mobile users tend toward lower cognitive load

        if cog_score > 0.7:
            new_cl = "high_cognitive"
            cl_conf = 0.7
        elif cog_score < 0.35:
            new_cl = "minimal_cognitive"
            cl_conf = 0.65
        else:
            new_cl = "moderate_cognitive"
            cl_conf = 0.5

        if cl_conf > result.confidence.get("cognitive_load", 0):
            result.cognitive_load = new_cl
            result.confidence["cognitive_load"] = cl_conf

        # --- Decision Style from interaction patterns ---
        click_precision = signals.get("click_precision", 0)
        backspace_freq = signals.get("backspace_frequency", 0)
        nav_directness = signals.get("navigation_directness", 0)

        if comparison > 0.7 and time_on_page > 45:
            new_ds = "maximizing"
            ds_conf = 0.7
        elif comparison > 0.5 and pages_viewed > 5:
            new_ds = "analytical_systematic"
            ds_conf = 0.65
        elif scroll_vel > 0.8 and time_on_page < 15:
            new_ds = "gut_instinct"
            ds_conf = 0.65
        elif nav_directness > 0.7:
            new_ds = "recognition_based"
            ds_conf = 0.55
        else:
            new_ds = None
            ds_conf = 0

        if new_ds and ds_conf > result.confidence.get("decision_style", 0):
            result.decision_style = new_ds
            result.confidence["decision_style"] = ds_conf

        # --- Temporal Orientation from session behavior ---
        session_duration = signals.get("session_duration_seconds", 0)
        if session_duration > 300 and pages_viewed > 10:
            new_to = "long_term_future"
            to_conf = 0.55
        elif session_duration < 30:
            new_to = "immediate_present"
            to_conf = 0.55
        else:
            new_to = None
            to_conf = 0

        if new_to and to_conf > result.confidence.get("temporal_orientation", 0):
            result.temporal_orientation = new_to
            result.confidence["temporal_orientation"] = to_conf

    # ------------------------------------------------------------------
    # Product Category → Motivation
    # ------------------------------------------------------------------

    def _apply_category(self, result: InferredDimensions, category: str):
        """Apply category-conditioned motivation prior."""
        cat_lower = category.lower().replace("_", " ").replace("-", " ")
        for key, motivation in CATEGORY_MOTIVATION_MAP.items():
            if key in cat_lower:
                cat_conf = 0.5
                if cat_conf > result.confidence.get("motivation", 0):
                    result.motivation = motivation
                    result.confidence["motivation"] = cat_conf
                break

    # ------------------------------------------------------------------
    # Text Analysis → Dimensions
    # ------------------------------------------------------------------

    def _apply_text(self, result: InferredDimensions, text: str):
        """Infer dimensions from text using lightweight keyword matching."""
        text_lower = text.lower()

        # --- Motivation from text keywords ---
        motivation_keywords = {
            "pure_curiosity": ["wonder", "explore", "discover", "learn", "curious", "fascinating"],
            "mastery_seeking": ["improve", "master", "expert", "professional", "advanced", "skill"],
            "self_expression": ["express", "unique", "creative", "personal", "style", "identity"],
            "status_signaling": ["luxury", "premium", "exclusive", "prestigious", "elite"],
            "immediate_gratification": ["now", "instant", "immediately", "can't wait", "today"],
            "cost_minimization": ["cheap", "affordable", "budget", "save", "deal", "discount"],
            "risk_mitigation": ["safe", "reliable", "guarantee", "warranty", "trusted"],
            "social_approval": ["popular", "trending", "everyone", "recommended", "best seller"],
            "excitement_seeking": ["exciting", "thrilling", "adventure", "amazing", "incredible"],
            "quality_assurance": ["quality", "durable", "well-made", "premium materials", "reliable"],
        }

        best_mot = None
        best_mot_score = 0
        for mot, keywords in motivation_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_mot_score:
                best_mot_score = score
                best_mot = mot

        if best_mot and best_mot_score >= 2:
            text_conf = min(0.7, 0.4 + best_mot_score * 0.1)
            if text_conf > result.confidence.get("motivation", 0):
                result.motivation = best_mot
                result.confidence["motivation"] = text_conf

        # --- Emotional Intensity from text ---
        high_arousal_words = ["excited", "thrilled", "amazing", "incredible", "love", "fantastic", "wow"]
        low_arousal_words = ["calm", "peaceful", "relaxed", "simple", "practical", "functional"]
        negative_words = ["worried", "afraid", "anxious", "concerned", "risk", "danger"]

        high_count = sum(1 for w in high_arousal_words if w in text_lower)
        low_count = sum(1 for w in low_arousal_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if high_count >= 2:
            new_ei = "high_positive_activation"
            ei_conf = 0.6
        elif neg_count >= 2:
            new_ei = "high_negative_activation"
            ei_conf = 0.55
        elif low_count >= 2:
            new_ei = "low_positive_calm"
            ei_conf = 0.5
        else:
            new_ei = None
            ei_conf = 0

        if new_ei and ei_conf > result.confidence.get("emotional_intensity", 0):
            result.emotional_intensity = new_ei
            result.confidence["emotional_intensity"] = ei_conf


# ============================================================================
# Singleton accessor
# ============================================================================

_instance: Optional[DimensionInferenceService] = None


def get_dimension_inference_service(
    population_ndf: Optional[Dict[str, float]] = None,
) -> DimensionInferenceService:
    """Get or create the DimensionInferenceService singleton."""
    global _instance
    if _instance is None:
        _instance = DimensionInferenceService(population_ndf)
    return _instance
