"""
DSP Enrichment Engine — State Inference Engine
================================================

Transforms observable behavioral signals (ImpressionContext) into a latent
psychological state vector. This is the core inferential step that replaces
cookie-based audience profiles with real-time psychological profiling.

Pipeline:
    1. Extract raw signals from ImpressionContext
    2. Map signals to psychological constructs via BehavioralSignalRegistry
    3. Apply temporal modulation (circadian, session, chronotype)
    4. Fuse multi-signal evidence using precision-weighted integration
    5. Detect vulnerability flags
    6. Output PsychologicalStateVector with confidence estimates
"""

from typing import Dict, List, Tuple

from adam.dsp.models import (
    ImpressionContext,
    PsychologicalStateVector,
    ContentCategory,
    DeviceType,
    FunnelStage,
    VulnerabilityType,
    BehavioralSignal,
)


class StateInferenceEngine:
    """
    Transforms observable behavioral signals (ImpressionContext) into a latent
    PsychologicalStateVector. The inferred state bridges to ADAM's NDF system
    via PsychologicalStateVector.to_ndf_profile().
    """

    def __init__(
        self,
        signal_registry: Dict = None,
        construct_registry: Dict = None,
        edge_registry: Dict = None,
    ):
        self.signals = signal_registry or {}
        self.constructs = construct_registry or {}
        self.edges = edge_registry or {}

    def infer_state(self, ctx: ImpressionContext) -> PsychologicalStateVector:
        """Main inference pipeline: ImpressionContext -> PsychologicalStateVector."""
        state = PsychologicalStateVector()

        # Step 1: Regulatory Focus Inference
        state.promotion_focus, state.prevention_focus = self._infer_regulatory_focus(ctx)

        # Step 2: Cognitive State Inference
        state.cognitive_load = ctx.estimated_cognitive_load
        state.processing_mode = (
            0.7 if ctx.estimated_processing_mode == "system1_dominant"
            else (0.3 if ctx.estimated_processing_mode == "system2_dominant" else 0.5)
        )
        state.attention_level = self._estimate_attention(ctx)
        state.mind_wandering_probability = self._estimate_mind_wandering(ctx)

        # Step 3: Emotional State Inference
        state.valence = ctx.content_sentiment  # spillover assumption
        state.arousal = ctx.content_arousal

        # Step 4: Personality Inference (from behavioral signals)
        (
            state.openness,
            state.conscientiousness,
            state.extraversion,
            state.agreeableness,
            state.neuroticism,
        ) = self._infer_personality(ctx)

        # Step 5: Construal Level & Decision State
        state.construal_level = self._infer_construal_level(ctx)
        state.funnel_stage = self._infer_funnel_stage(ctx)
        state.decision_confidence = self._infer_decision_confidence(ctx)
        state.choice_overload_risk = self._estimate_choice_overload(ctx)

        # Step 6: Temporal & Circadian
        state.chronotype_state = ctx.estimated_chronotype_state
        state.circadian_cognitive_capacity = self._circadian_capacity(ctx.local_hour)
        state.decision_fatigue_level = self._estimate_fatigue(ctx)

        # Step 7: Social & Identity
        state.social_proof_susceptibility = self._estimate_social_proof_susceptibility(ctx)
        state.status_motivation = self._estimate_status_motivation(ctx)
        state.identity_salience = self._estimate_identity_salience(ctx)

        # Step 8: Self-Determination Theory Needs
        state.autonomy_need = self._estimate_autonomy_need(ctx)
        state.competence_need = self._estimate_competence_need(ctx)
        state.relatedness_need = self._estimate_relatedness_need(ctx)

        # Step 9: Approach-Avoidance
        state.approach_motivation_bas = max(0.0, min(1.0, state.promotion_focus * 0.7 + state.arousal * 0.3))
        state.avoidance_motivation_bis = max(0.0, min(1.0, state.prevention_focus * 0.7 + state.neuroticism * 0.3))

        # Step 10: Vulnerability Detection
        state.vulnerability_flags = self._detect_vulnerabilities(ctx)
        state.vulnerability_severity = len(state.vulnerability_flags) / max(1, len(VulnerabilityType))
        state.protection_mode = state.vulnerability_severity > 0.3

        # Step 11: Processing Fluency
        state.processing_fluency = max(0.0, min(1.0,
            0.6 + (0.2 if ctx.connection_speed_mbps > 50 else -0.1)
            - (state.cognitive_load * 0.3)
        ))

        return state

    # =========================================================================
    # Private inference methods
    # =========================================================================

    def _infer_regulatory_focus(self, ctx: ImpressionContext) -> Tuple[float, float]:
        """Infer promotion vs prevention focus from observable signals."""
        promotion_signals = 0.0
        prevention_signals = 0.0

        # Content category frame
        promotion_categories = {
            ContentCategory.ENTERTAINMENT, ContentCategory.LIFESTYLE,
            ContentCategory.FASHION, ContentCategory.TRAVEL,
            ContentCategory.GAMING,
        }
        prevention_categories = {
            ContentCategory.FINANCE, ContentCategory.HEALTH,
            ContentCategory.NEWS, ContentCategory.REAL_ESTATE,
        }
        if ctx.content_category in promotion_categories:
            promotion_signals += 0.3
        elif ctx.content_category in prevention_categories:
            prevention_signals += 0.3

        # Navigation pattern: exploration = promotion, validation = prevention
        if ctx.navigation_directness < 0.4:
            promotion_signals += 0.2
        elif ctx.navigation_directness > 0.7:
            prevention_signals += 0.2

        # Comparison behavior = vigilant = prevention
        if ctx.comparison_behavior > 0.3:
            prevention_signals += 0.15

        # Content sentiment: positive → promotion, negative → prevention
        if ctx.content_sentiment > 0.3:
            promotion_signals += 0.1
        elif ctx.content_sentiment < -0.3:
            prevention_signals += 0.1

        # Category exploration breadth → promotion
        if ctx.category_changes > 3:
            promotion_signals += 0.1

        # Normalize to 0-1
        total = max(promotion_signals + prevention_signals, 0.01)
        return promotion_signals / total, prevention_signals / total

    def _estimate_attention(self, ctx: ImpressionContext) -> float:
        """Estimate current attention level from behavioral signals."""
        attention = 0.7  # baseline

        # Session phase modulation
        if ctx.session_phase == "deep":
            attention -= 0.2
        elif ctx.session_phase == "early":
            attention += 0.1

        # Scroll behavior
        if ctx.scroll_velocity > 800:
            attention -= 0.15
        elif ctx.scroll_velocity < 200 and ctx.time_on_page_seconds > 30:
            attention += 0.15

        # Ad density reduces attention to each ad
        attention -= min(0.3, ctx.ad_density * 0.1)

        # Dark mode in late hours suggests lower attention environment
        if ctx.dark_mode and ctx.local_hour >= 22:
            attention -= 0.1

        return max(0.0, min(1.0, attention))

    def _estimate_mind_wandering(self, ctx: ImpressionContext) -> float:
        """Estimate mind-wandering probability."""
        mw_prob = 0.35  # base rate (30-50% of waking hours)

        if ctx.session_duration_seconds > 1200 and ctx.scroll_velocity > 500:
            mw_prob += 0.2
        if ctx.time_on_page_seconds > 60 and ctx.mouse_velocity < 10:
            mw_prob += 0.15

        return max(0.0, min(1.0, mw_prob))

    def _infer_personality(self, ctx: ImpressionContext) -> Tuple[float, ...]:
        """Rough Big Five inference from behavioral signals. Returns (O, C, E, A, N)."""
        # Openness: content diversity proxy
        o = 0.5 + (0.2 if ctx.category_changes > 3 else -0.1)

        # Conscientiousness: navigation precision
        c = 0.5 + (0.2 if ctx.navigation_directness > 0.6 else -0.1)

        # Extraversion: social content referrer
        e = 0.5 + (0.2 if ctx.referrer_type == "social" else -0.1)

        # Agreeableness: limited signal available
        a = 0.5

        # Neuroticism: back-navigation, comparison intensity
        n = 0.5 + (0.15 if ctx.comparison_behavior > 0.5 else 0.0)

        return tuple(max(0.0, min(1.0, v)) for v in (o, c, e, a, n))

    def _infer_construal_level(self, ctx: ImpressionContext) -> float:
        """Infer construal level (0=concrete, 1=abstract)."""
        cl = 0.5
        funnel = self._infer_funnel_stage(ctx)
        if funnel == FunnelStage.AWARENESS:
            cl += 0.3
        elif funnel in (FunnelStage.PURCHASE, FunnelStage.INTENT):
            cl -= 0.3
        if ctx.comparison_behavior > 0.3:
            cl -= 0.15
        return max(0.0, min(1.0, cl))

    def _infer_funnel_stage(self, ctx: ImpressionContext) -> FunnelStage:
        """Infer funnel stage from navigation signals."""
        if ctx.navigation_directness > 0.8 and ctx.comparison_behavior > 0.5:
            return FunnelStage.PURCHASE
        elif ctx.comparison_behavior > 0.3:
            return FunnelStage.CONSIDERATION
        elif ctx.navigation_directness < 0.4 and ctx.category_changes > 2:
            return FunnelStage.AWARENESS
        return FunnelStage.CONSIDERATION

    def _infer_decision_confidence(self, ctx: ImpressionContext) -> float:
        """Estimate decision confidence from behavioral indicators."""
        conf = 0.5
        if ctx.navigation_directness > 0.7:
            conf += 0.2
        if ctx.backspace_frequency > 0.1:
            conf -= 0.15
        if ctx.scroll_depth > 0.8:
            conf += 0.1
        return max(0.0, min(1.0, conf))

    def _estimate_choice_overload(self, ctx: ImpressionContext) -> float:
        """Estimate choice overload risk."""
        risk = 0.2
        if ctx.comparison_behavior > 0.3:
            risk += 0.2
        if ctx.session_duration_seconds > 900 and ctx.pages_viewed > 10:
            risk += 0.2
        if ctx.category_changes > 5:
            risk += 0.15
        return max(0.0, min(1.0, risk))

    def _circadian_capacity(self, hour: int) -> float:
        """Circadian cognitive capacity curve. Peak = 1.0, trough = 0.3."""
        if 9 <= hour <= 11:
            return 0.95
        elif 14 <= hour <= 17:
            return 0.85
        elif 12 <= hour <= 13:
            return 0.65
        elif 6 <= hour <= 8:
            return 0.70
        elif 18 <= hour <= 21:
            return 0.55
        else:
            return 0.35

    def _estimate_fatigue(self, ctx: ImpressionContext) -> float:
        """Estimate decision fatigue from session metrics."""
        fatigue = 0.0
        fatigue += min(0.4, ctx.session_duration_seconds / 3600)
        fatigue += min(0.3, ctx.pages_viewed / 30)
        if ctx.local_hour >= 22 or ctx.local_hour <= 5:
            fatigue += 0.2
        return max(0.0, min(1.0, fatigue))

    def _estimate_social_proof_susceptibility(self, ctx: ImpressionContext) -> float:
        """Estimate susceptibility to social proof signals."""
        susceptibility = 0.5
        if ctx.referrer_type == "social":
            susceptibility += 0.2
        if ctx.comparison_behavior > 0.3:
            susceptibility += 0.15
        return max(0.0, min(1.0, susceptibility))

    def _estimate_status_motivation(self, ctx: ImpressionContext) -> float:
        """Estimate status/signaling motivation from context."""
        motivation = 0.3
        if ctx.content_category in (ContentCategory.FASHION, ContentCategory.LIFESTYLE):
            motivation += 0.2
        if ctx.referrer_type == "social":
            motivation += 0.15
        return max(0.0, min(1.0, motivation))

    def _estimate_identity_salience(self, ctx: ImpressionContext) -> float:
        """Estimate identity salience from context."""
        salience = 0.3
        if ctx.referrer_type == "social":
            salience += 0.2
        if ctx.subscriber_status:
            salience += 0.15
        return max(0.0, min(1.0, salience))

    def _estimate_autonomy_need(self, ctx: ImpressionContext) -> float:
        """Estimate autonomy need from behavioral signals."""
        need = 0.5
        if ctx.navigation_directness < 0.3:  # exploratory = high autonomy
            need += 0.2
        if ctx.category_changes > 3:
            need += 0.1
        return max(0.0, min(1.0, need))

    def _estimate_competence_need(self, ctx: ImpressionContext) -> float:
        """Estimate competence need from behavioral signals."""
        need = 0.5
        if ctx.comparison_behavior > 0.5:
            need += 0.2
        if ctx.content_complexity > 0.6:
            need += 0.1
        return max(0.0, min(1.0, need))

    def _estimate_relatedness_need(self, ctx: ImpressionContext) -> float:
        """Estimate relatedness need from behavioral signals."""
        need = 0.5
        if ctx.referrer_type == "social":
            need += 0.2
        return max(0.0, min(1.0, need))

    def _detect_vulnerabilities(self, ctx: ImpressionContext) -> List[VulnerabilityType]:
        """Detect vulnerability states requiring protection."""
        flags = []

        # Sleep deprivation: active at 11pm-4am
        if ctx.local_hour >= 23 or ctx.local_hour <= 4:
            flags.append(VulnerabilityType.SLEEP_DEPRIVATION)

        # Cognitive depletion: long session + many pages
        if ctx.session_duration_seconds > 1800 and ctx.pages_viewed > 15:
            flags.append(VulnerabilityType.COGNITIVE_DEPLETION)

        # Emotional distress: negative content + high arousal
        if ctx.content_sentiment < -0.5 and ctx.content_arousal > 0.7:
            flags.append(VulnerabilityType.EMOTIONAL_DISTRESS)

        # Decision fatigue: very long session
        if ctx.session_duration_seconds > 3600 and ctx.pages_viewed > 25:
            flags.append(VulnerabilityType.DECISION_FATIGUE)

        return flags
