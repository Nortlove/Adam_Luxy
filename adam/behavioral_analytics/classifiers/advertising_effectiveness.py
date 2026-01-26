# =============================================================================
# ADAM Advertising Effectiveness Predictor
# Location: adam/behavioral_analytics/classifiers/advertising_effectiveness.py
# =============================================================================

"""
ADVERTISING EFFECTIVENESS PREDICTOR

Predicts advertising effectiveness by applying 25 years of consumer psychology
research to user profiles and ad characteristics.

Capabilities:
1. Predict ad effectiveness for a user-ad combination
2. Recommend optimal message framing based on psychological state
3. Suggest creative elements based on personality
4. Identify interaction effects and moderators
5. Generate optimization recommendations

This classifier integrates:
- Personality → ad response knowledge (Big Five, individual differences)
- Psychological state targeting (regulatory focus, construal level, mood)
- Message appeal effects (fear, humor, narrative, framing)
- Visual design knowledge (color, whitespace, models)
- Media platform effects
- Moderator/interaction effects
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np

from adam.behavioral_analytics.models.advertising_knowledge import (
    AdvertisingKnowledge,
    AdvertisingInteraction,
    EffectivenessPrediction,
    MessageFrameRecommendation,
    CreativeElementRecommendation,
    PredictorCategory,
    AdElement,
    OutcomeMetric,
    RobustnessTier,
    InteractionType,
)

from adam.behavioral_analytics.knowledge.consumer_psychology_seeder import (
    get_consumer_psychology_seeder,
)

logger = logging.getLogger(__name__)


class AdvertisingEffectivenessPredictor:
    """
    Predicts advertising effectiveness using research-validated knowledge.
    
    This predictor applies 25 years of consumer psychology research to
    estimate how effective an ad will be for a specific user, based on:
    - User's personality traits
    - Current psychological state
    - Ad characteristics
    - Context and platform
    """
    
    def __init__(self):
        """Initialize with consumer psychology knowledge."""
        self.seeder = get_consumer_psychology_seeder()
        self._knowledge_cache: Dict[str, AdvertisingKnowledge] = {}
        self._interaction_cache: Dict[str, AdvertisingInteraction] = {}
        
        # Seed knowledge on initialization
        self._seed_knowledge()
    
    def _seed_knowledge(self) -> None:
        """Seed the knowledge base."""
        all_knowledge, all_interactions = self.seeder.seed_all_knowledge()
        
        for k in all_knowledge:
            self._knowledge_cache[k.knowledge_id] = k
        
        for i in all_interactions:
            self._interaction_cache[i.interaction_id] = i
        
        logger.info(
            f"AdvertisingEffectivenessPredictor initialized with "
            f"{len(self._knowledge_cache)} knowledge items and "
            f"{len(self._interaction_cache)} interactions"
        )
    
    async def predict_effectiveness(
        self,
        user_id: str,
        ad_id: str,
        user_profile: Dict[str, Any],
        ad_characteristics: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> EffectivenessPrediction:
        """
        Predict advertising effectiveness for a user-ad combination.
        
        Args:
            user_id: User identifier
            ad_id: Ad identifier
            user_profile: User's psychological profile containing:
                - personality: Dict with Big Five scores (0-1)
                - regulatory_focus: "promotion" or "prevention" with score
                - construal_level: 0-1 (0=concrete, 1=abstract)
                - mood: "positive", "neutral", "negative"
                - need_for_cognition: 0-1
                - demographics: Dict with age, gender, etc.
            ad_characteristics: Ad attributes containing:
                - appeal_type: "fear", "humor", "narrative", "rational", etc.
                - message_frame: "gain", "loss", "mixed"
                - has_celebrity: bool
                - celebrity_fit: 0-1 (if has_celebrity)
                - visual_style: Dict with color, whitespace, etc.
                - media_platform: "tv", "social", "native", etc.
                - video_length: seconds (if video)
            context: Optional context:
                - product_involvement: 0-1
                - product_type: "hedonic", "utilitarian"
                - brand_familiarity: 0-1
        
        Returns:
            EffectivenessPrediction with predicted outcomes and recommendations
        """
        context = context or {}
        
        # Initialize prediction scores
        scores = {
            "ad_attitude": 0.5,
            "brand_attitude": 0.5,
            "purchase_intent": 0.5,
            "engagement": 0.5,
        }
        
        positive_factors = []
        negative_factors = []
        knowledge_used = []
        weights_sum = 0.0
        
        # Apply personality-based knowledge
        personality = user_profile.get("personality", {})
        for trait, value in personality.items():
            matching_knowledge = self.seeder.get_knowledge_for_predictor(trait)
            for k in matching_knowledge:
                if self._matches_profile(k, value):
                    adjustment, weight = self._calculate_adjustment(k, ad_characteristics)
                    self._apply_adjustment(scores, k.outcome_metric, adjustment, weight)
                    knowledge_used.append(k.knowledge_id)
                    weights_sum += weight
                    
                    if adjustment > 0:
                        positive_factors.append(f"{trait}: {k.element_specification}")
                    elif adjustment < 0:
                        negative_factors.append(f"{trait} mismatch: {k.element_specification}")
        
        # Apply psychological state knowledge
        reg_focus = user_profile.get("regulatory_focus", {})
        if reg_focus:
            focus_type = reg_focus.get("type", "neutral")
            focus_knowledge = self.seeder.get_knowledge_for_predictor("regulatory_focus")
            for k in focus_knowledge:
                if k.predictor_value == focus_type:
                    ad_frame = ad_characteristics.get("message_frame", "mixed")
                    if self._check_regulatory_fit(focus_type, ad_frame):
                        adjustment = k.effect_size * 0.5
                        self._apply_adjustment(scores, k.outcome_metric, adjustment, 0.8)
                        positive_factors.append(f"Regulatory fit: {focus_type}×{ad_frame}")
                        knowledge_used.append(k.knowledge_id)
        
        # Apply construal level knowledge
        construal = user_profile.get("construal_level", 0.5)
        ad_abstraction = self._assess_ad_abstraction(ad_characteristics)
        if abs(construal - ad_abstraction) < 0.3:  # Good match
            scores["persuasion"] = scores.get("persuasion", 0.5) + 0.15
            positive_factors.append("Construal-message match")
        
        # Apply appeal type knowledge
        appeal = ad_characteristics.get("appeal_type")
        if appeal:
            appeal_knowledge = self.seeder.get_knowledge_for_predictor(f"{appeal}_appeal")
            for k in appeal_knowledge:
                adjustment, weight = self._calculate_adjustment(k, ad_characteristics)
                self._apply_adjustment(scores, k.outcome_metric, adjustment, weight)
                knowledge_used.append(k.knowledge_id)
                
                if adjustment > 0:
                    positive_factors.append(f"{appeal} appeal effective")
                elif adjustment < 0:
                    negative_factors.append(f"{appeal} appeal concern")
        
        # Apply celebrity endorsement knowledge (if applicable)
        if ad_characteristics.get("has_celebrity"):
            celebrity_fit = ad_characteristics.get("celebrity_fit", 0.5)
            celebrity_interaction = self._get_celebrity_fit_interaction()
            
            if celebrity_interaction:
                if celebrity_fit >= 0.7:  # High fit
                    adjustment = celebrity_interaction.effect_when_moderator_present
                    positive_factors.append(f"High celebrity-product fit (d={adjustment:.2f})")
                else:  # Poor fit
                    adjustment = celebrity_interaction.effect_when_moderator_absent
                    negative_factors.append(f"Poor celebrity-product fit (d={adjustment:.2f})")
                
                # Convert Cohen's d to probability adjustment
                prob_adjustment = self._cohens_d_to_prob(adjustment)
                scores["brand_attitude"] += prob_adjustment
                scores["purchase_intent"] += prob_adjustment * 0.8
        
        # Apply media platform knowledge
        platform = ad_characteristics.get("media_platform")
        if platform:
            platform_knowledge = [
                k for k in self._knowledge_cache.values()
                if k.ad_element == AdElement.MEDIA_PLATFORM
                and k.element_specification == platform
            ]
            for k in platform_knowledge:
                adjustment, weight = self._calculate_adjustment(k, ad_characteristics)
                self._apply_adjustment(scores, k.outcome_metric, adjustment, weight)
                knowledge_used.append(k.knowledge_id)
        
        # Apply interaction effects
        for interaction in self._interaction_cache.values():
            interaction_adjustment = self._evaluate_interaction(
                interaction, user_profile, ad_characteristics, context
            )
            if interaction_adjustment != 0:
                scores["brand_attitude"] += interaction_adjustment
                if interaction_adjustment > 0:
                    positive_factors.append(f"Interaction: {interaction.primary_variable}×{interaction.moderating_variable}")
        
        # Normalize scores to 0-1 range
        for key in scores:
            scores[key] = max(0.0, min(1.0, scores[key]))
        
        # Calculate overall effectiveness
        effectiveness = (
            scores["ad_attitude"] * 0.25 +
            scores["brand_attitude"] * 0.35 +
            scores["purchase_intent"] * 0.30 +
            scores["engagement"] * 0.10
        )
        
        # Calculate prediction confidence based on knowledge quality
        tier1_count = sum(
            1 for kid in knowledge_used
            if self._knowledge_cache.get(kid, {}).robustness_tier == RobustnessTier.TIER_1_META_ANALYZED
        )
        confidence = min(0.9, 0.4 + (tier1_count * 0.05) + (len(knowledge_used) * 0.02))
        
        # Generate optimization suggestions
        suggestions = self._generate_optimization_suggestions(
            user_profile, ad_characteristics, negative_factors
        )
        
        return EffectivenessPrediction(
            user_id=user_id,
            ad_id=ad_id,
            predicted_ad_attitude=scores["ad_attitude"],
            predicted_brand_attitude=scores["brand_attitude"],
            predicted_purchase_intent=scores["purchase_intent"],
            predicted_engagement=scores["engagement"],
            effectiveness_score=effectiveness,
            prediction_confidence=confidence,
            knowledge_items_used=knowledge_used,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            optimization_suggestions=suggestions,
        )
    
    async def recommend_message_frame(
        self,
        user_profile: Dict[str, Any],
        product_context: Optional[Dict[str, Any]] = None,
    ) -> MessageFrameRecommendation:
        """
        Recommend optimal message framing based on psychological profile.
        
        Args:
            user_profile: User's psychological profile
            product_context: Optional product/context information
        
        Returns:
            MessageFrameRecommendation with framing guidance
        """
        product_context = product_context or {}
        
        # Determine regulatory focus alignment
        reg_focus = user_profile.get("regulatory_focus", {})
        focus_type = reg_focus.get("type", "neutral")
        focus_strength = reg_focus.get("strength", 0.5)
        
        # Determine construal level alignment
        construal = user_profile.get("construal_level", 0.5)
        
        # Make framing recommendation
        if focus_type == "promotion" and focus_strength > 0.6:
            recommended_frame = "gain"
            frame_confidence = 0.7 + (focus_strength - 0.6) * 0.5
            regulatory_alignment = "promotion"
            supporting = ["Regulatory fit: promotion focus matches gain framing (Lee & Aaker, 2004)"]
        elif focus_type == "prevention" and focus_strength > 0.6:
            recommended_frame = "loss"
            frame_confidence = 0.7 + (focus_strength - 0.6) * 0.5
            regulatory_alignment = "prevention"
            supporting = ["Regulatory fit: prevention focus matches loss framing"]
        else:
            recommended_frame = "mixed"
            frame_confidence = 0.5
            regulatory_alignment = "neutral"
            supporting = ["Neutral regulatory focus suggests mixed framing"]
        
        # Construal alignment
        if construal > 0.6:
            construal_alignment = "abstract"
            headline_style = "Emphasize 'why' - desirability and outcomes"
            supporting.append("High construal → abstract 'why' messaging")
        elif construal < 0.4:
            construal_alignment = "concrete"
            headline_style = "Emphasize 'how' - feasibility and process"
            supporting.append("Low construal → concrete 'how' messaging")
        else:
            construal_alignment = "adaptive"
            headline_style = "Balanced approach"
        
        # CTA framing
        if recommended_frame == "gain":
            cta_framing = "Focus on benefits gained: 'Get yours now', 'Start enjoying'"
        elif recommended_frame == "loss":
            cta_framing = "Focus on loss prevention: 'Don't miss out', 'Secure your spot'"
        else:
            cta_framing = "Balanced: 'Discover what you've been missing'"
        
        # Body emphasis based on involvement
        involvement = product_context.get("involvement", 0.5)
        if involvement > 0.6:
            body_emphasis = "Strong arguments, detailed attributes (high involvement → central processing)"
        else:
            body_emphasis = "Peripheral cues, visual appeal (low involvement → heuristic processing)"
        
        return MessageFrameRecommendation(
            recommended_frame=recommended_frame,
            frame_confidence=min(1.0, frame_confidence),
            regulatory_focus_alignment=regulatory_alignment,
            construal_level_alignment=construal_alignment,
            supporting_evidence=supporting,
            contraindications=[],
            headline_style=headline_style,
            body_emphasis=body_emphasis,
            cta_framing=cta_framing,
        )
    
    async def recommend_creative_elements(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        product_context: Optional[Dict[str, Any]] = None,
    ) -> CreativeElementRecommendation:
        """
        Recommend creative elements based on user profile.
        
        Args:
            user_id: User identifier
            user_profile: User's psychological profile
            product_context: Optional product/context information
        
        Returns:
            CreativeElementRecommendation with visual and message guidance
        """
        product_context = product_context or {}
        knowledge_applied = []
        
        # Get message frame recommendation
        frame_rec = await self.recommend_message_frame(user_profile, product_context)
        
        # Visual recommendations based on personality
        personality = user_profile.get("personality", {})
        openness = personality.get("openness", 0.5)
        neuroticism = personality.get("neuroticism", 0.5)
        
        # Color palette
        if neuroticism > 0.6:
            color_palette = "Trust-evoking: blues, greens, calm tones (reduces anxiety)"
        elif openness > 0.6:
            color_palette = "Vibrant and novel: unexpected color combinations"
        else:
            color_palette = "Balanced: professional with accent colors"
        
        # Whitespace
        product_type = product_context.get("product_type", "neutral")
        if product_type == "luxury":
            whitespace_level = "high"
        else:
            whitespace_level = "medium"
        
        # Model characteristics
        model_rec = "Moderately attractive models (avoid extreme attractiveness)"
        
        # Language style based on construal
        construal = user_profile.get("construal_level", 0.5)
        if construal < 0.4:
            language_style = "concrete"
        elif construal > 0.6:
            language_style = "abstract"
        else:
            language_style = "balanced"
        
        # Appeal type based on NFC and involvement
        nfc = user_profile.get("need_for_cognition", 0.5)
        involvement = product_context.get("involvement", 0.5)
        
        if nfc > 0.6 and involvement > 0.5:
            appeal_type = "rational"
        elif nfc < 0.4:
            appeal_type = "emotional"
        else:
            appeal_type = "mixed"
        
        # Video length recommendation
        platform = product_context.get("platform", "social")
        video_lengths = {
            "facebook": 15,
            "instagram": 15,
            "youtube": 15,
            "tiktok": 25,
            "social": 15,
        }
        optimal_video_length = video_lengths.get(platform, 15)
        
        # Narrative structure
        if appeal_type == "emotional" or openness > 0.6:
            narrative_structure = "Story-driven with identifiable characters (transportation effect)"
        else:
            narrative_structure = "Problem-solution structure"
        
        # Confidence based on profile completeness
        profile_completeness = sum([
            bool(personality),
            bool(user_profile.get("regulatory_focus")),
            bool(user_profile.get("construal_level")),
            bool(user_profile.get("need_for_cognition")),
        ]) / 4.0
        
        return CreativeElementRecommendation(
            user_id=user_id,
            color_palette=color_palette,
            whitespace_level=whitespace_level,
            model_characteristics=model_rec,
            message_frame=frame_rec,
            language_style=language_style,
            appeal_type=appeal_type,
            optimal_video_length=optimal_video_length,
            narrative_structure=narrative_structure,
            overall_confidence=0.5 + (profile_completeness * 0.4),
            knowledge_items_applied=knowledge_applied,
        )
    
    def _matches_profile(self, knowledge: AdvertisingKnowledge, value: float) -> bool:
        """Check if knowledge applies to profile value."""
        if knowledge.predictor_value == "high" and value >= 0.6:
            return True
        elif knowledge.predictor_value == "low" and value <= 0.4:
            return True
        elif knowledge.predictor_value in ["present", "active"]:
            return True
        return False
    
    def _calculate_adjustment(
        self,
        knowledge: AdvertisingKnowledge,
        ad_characteristics: Dict[str, Any],
    ) -> Tuple[float, float]:
        """
        Calculate score adjustment from knowledge item.
        
        Returns (adjustment, weight) tuple.
        """
        # Base adjustment from effect size
        if knowledge.effect_type in ["correlation", "meta_r"]:
            # Correlation: use directly as adjustment factor
            adjustment = knowledge.effect_size * 0.5
        elif knowledge.effect_type == "cohens_d":
            # Cohen's d: convert to probability
            adjustment = self._cohens_d_to_prob(knowledge.effect_size)
        elif knowledge.effect_type == "beta":
            adjustment = knowledge.effect_size * 0.3
        elif knowledge.effect_type == "percentage":
            adjustment = knowledge.effect_size / 100 * 0.5
        else:
            adjustment = knowledge.effect_size * 0.2
        
        # Apply direction
        if knowledge.outcome_direction == "negative":
            adjustment = -adjustment
        
        # Weight by robustness tier
        tier_weights = {
            RobustnessTier.TIER_1_META_ANALYZED: 1.0,
            RobustnessTier.TIER_2_REPLICATED: 0.7,
            RobustnessTier.TIER_3_SINGLE_STUDY: 0.4,
        }
        weight = tier_weights.get(knowledge.robustness_tier, 0.5)
        
        return adjustment, weight
    
    def _apply_adjustment(
        self,
        scores: Dict[str, float],
        outcome: OutcomeMetric,
        adjustment: float,
        weight: float,
    ) -> None:
        """Apply adjustment to appropriate score."""
        outcome_map = {
            OutcomeMetric.AD_ATTITUDE: "ad_attitude",
            OutcomeMetric.BRAND_ATTITUDE: "brand_attitude",
            OutcomeMetric.PURCHASE_INTENT: "purchase_intent",
            OutcomeMetric.ENGAGEMENT: "engagement",
            OutcomeMetric.PERSUASION: "brand_attitude",  # Map to brand attitude
            OutcomeMetric.CONVERSION: "purchase_intent",
            OutcomeMetric.BRAND_RECALL: "brand_attitude",
            OutcomeMetric.AD_RECALL: "ad_attitude",
        }
        
        key = outcome_map.get(outcome, "brand_attitude")
        scores[key] += adjustment * weight
    
    def _check_regulatory_fit(self, focus_type: str, ad_frame: str) -> bool:
        """Check for regulatory fit between focus and frame."""
        fits = {
            ("promotion", "gain"): True,
            ("prevention", "loss"): True,
        }
        return fits.get((focus_type, ad_frame), False)
    
    def _assess_ad_abstraction(self, ad_characteristics: Dict[str, Any]) -> float:
        """Assess abstraction level of ad (0=concrete, 1=abstract)."""
        # Simple heuristic based on ad features
        abstraction = 0.5
        
        if ad_characteristics.get("message_style") == "abstract":
            abstraction += 0.2
        elif ad_characteristics.get("message_style") == "concrete":
            abstraction -= 0.2
        
        if ad_characteristics.get("appeal_type") == "emotional":
            abstraction += 0.1
        elif ad_characteristics.get("appeal_type") == "rational":
            abstraction -= 0.1
        
        return max(0.0, min(1.0, abstraction))
    
    def _get_celebrity_fit_interaction(self) -> Optional[AdvertisingInteraction]:
        """Get the celebrity-product fit interaction."""
        for i in self._interaction_cache.values():
            if (i.primary_variable == "celebrity_endorsement" and 
                i.moderating_variable == "product_fit"):
                return i
        return None
    
    def _cohens_d_to_prob(self, d: float) -> float:
        """Convert Cohen's d to probability adjustment."""
        # Use the standard conversion
        # P = Φ(d / √2) where Φ is the standard normal CDF
        # Simplified: d=0.2 (small) → ~0.08, d=0.5 (medium) → ~0.19, d=0.8 (large) → ~0.29
        return d * 0.35  # Simplified linear approximation
    
    def _evaluate_interaction(
        self,
        interaction: AdvertisingInteraction,
        user_profile: Dict[str, Any],
        ad_characteristics: Dict[str, Any],
        context: Dict[str, Any],
    ) -> float:
        """Evaluate an interaction effect."""
        # Check if interaction applies
        primary_present = False
        moderator_present = False
        
        # Check primary variable
        if interaction.primary_variable in ad_characteristics:
            primary_present = ad_characteristics[interaction.primary_variable] == interaction.primary_value
        
        # Check moderator
        if interaction.moderating_variable in ad_characteristics:
            moderator_present = ad_characteristics[interaction.moderating_variable] == interaction.moderating_value
        elif interaction.moderating_variable in context:
            moderator_value = context[interaction.moderating_variable]
            if isinstance(moderator_value, (int, float)):
                moderator_present = moderator_value >= 0.6
            else:
                moderator_present = moderator_value == interaction.moderating_value
        
        if not primary_present:
            return 0.0
        
        if moderator_present:
            return self._cohens_d_to_prob(interaction.effect_when_moderator_present)
        else:
            return self._cohens_d_to_prob(interaction.effect_when_moderator_absent)
    
    def _generate_optimization_suggestions(
        self,
        user_profile: Dict[str, Any],
        ad_characteristics: Dict[str, Any],
        negative_factors: List[str],
    ) -> List[str]:
        """Generate optimization suggestions based on analysis."""
        suggestions = []
        
        # Check for regulatory fit issues
        reg_focus = user_profile.get("regulatory_focus", {}).get("type")
        ad_frame = ad_characteristics.get("message_frame")
        if reg_focus and ad_frame:
            if reg_focus == "promotion" and ad_frame == "loss":
                suggestions.append("Consider gain-framed messaging to match promotion focus")
            elif reg_focus == "prevention" and ad_frame == "gain":
                suggestions.append("Consider loss-framed messaging to match prevention focus")
        
        # Check for celebrity fit issues
        if ad_characteristics.get("has_celebrity"):
            fit = ad_characteristics.get("celebrity_fit", 0.5)
            if fit < 0.6:
                suggestions.append("Low celebrity-product fit detected (d=-0.96 for poor fit). Consider different endorser or remove celebrity.")
        
        # Check for construal match
        construal = user_profile.get("construal_level", 0.5)
        ad_abstraction = self._assess_ad_abstraction(ad_characteristics)
        if abs(construal - ad_abstraction) > 0.4:
            if construal > ad_abstraction:
                suggestions.append("User has abstract construal - consider more 'why' messaging")
            else:
                suggestions.append("User has concrete construal - consider more 'how' messaging")
        
        # Check for NFC alignment
        nfc = user_profile.get("need_for_cognition", 0.5)
        appeal = ad_characteristics.get("appeal_type")
        if nfc > 0.6 and appeal == "emotional":
            suggestions.append("High NFC user - ensure strong argument quality despite emotional appeal")
        
        # Platform-specific suggestions
        platform = ad_characteristics.get("media_platform")
        video_length = ad_characteristics.get("video_length")
        if platform and video_length:
            optimal_lengths = {"facebook": 15, "instagram": 15, "youtube": 15, "tiktok": 25}
            optimal = optimal_lengths.get(platform, 15)
            if video_length > optimal * 2:
                suggestions.append(f"Video length ({video_length}s) may be too long for {platform}. Consider {optimal}s.")
        
        return suggestions


# Factory function
_predictor: Optional[AdvertisingEffectivenessPredictor] = None


def get_advertising_effectiveness_predictor() -> AdvertisingEffectivenessPredictor:
    """Get singleton advertising effectiveness predictor."""
    global _predictor
    if _predictor is None:
        _predictor = AdvertisingEffectivenessPredictor()
    return _predictor
