"""
DSP Enrichment Engine — Strategy Generation Engine
====================================================

Translates inferred psychological state into optimal persuasion strategy.
Uses edge registry to chain causal mechanisms and generate creative
recommendations with full reasoning trace.

Pipeline:
    1. Determine dominant motivational frame (promotion vs prevention)
    2. Select optimal processing route (central/peripheral/narrative/social)
    3. Match construal level to message framing
    4. Apply personality-creative matching (Big Five → style)
    5. Set temporal optimization parameters
    6. Apply vulnerability protections (ethical boundaries)
    7. Generate reasoning trace for transparency
"""

from typing import Dict, List

from adam.dsp.models import (
    ImpressionContext,
    PsychologicalStateVector,
    PersuasionStrategy,
    PersuasionRoute,
    EmotionalVehicle,
    CreativeFormat,
    DeviceType,
    MechanismType,
    VulnerabilityType,
)


class StrategyGenerationEngine:
    """
    Translates inferred psychological state into optimal persuasion strategy.
    Integrates with ADAM's inferential chains when available.
    """

    def __init__(self, edge_registry: Dict = None, construct_registry: Dict = None):
        self.edges = edge_registry or {}
        self.constructs = construct_registry or {}

    def generate_strategy(
        self,
        state: PsychologicalStateVector,
        ctx: ImpressionContext,
        atom_mechanisms: List[str] = None,
        inferential_chains: List[Dict] = None,
    ) -> PersuasionStrategy:
        """
        Main strategy generation: state + context -> persuasion strategy.

        Args:
            state: Inferred psychological state
            ctx: Original impression context
            atom_mechanisms: Optional mechanism recommendations from ADAM atom DAG
            inferential_chains: Optional inferential chains from ADAM theory graph
        """
        strategy = PersuasionStrategy()
        reasoning = []

        # --- ETHICAL CHECK FIRST ---
        if state.protection_mode:
            strategy = self._apply_vulnerability_protections(strategy, state)
            vuln_names = [v.value for v in state.vulnerability_flags]
            reasoning.append(
                f"VULNERABILITY DETECTED: {vuln_names}. "
                f"Protection mode activated. Suppressing exploitative elements."
            )

        # Step 1: Regulatory Fit — highest-value optimization (OR=2.0-6.0)
        frame = state.get_dominant_motivational_frame()
        if frame == "promotion":
            strategy.message_frame = "gain"
            strategy.regulatory_fit = "promotion_gain"
            reasoning.append("Promotion focus detected -> gain framing. OR=2.0 for fit.")
        elif frame == "prevention":
            strategy.message_frame = "loss"
            strategy.regulatory_fit = "prevention_loss"
            reasoning.append("Prevention focus detected -> loss framing. OR=2.0 for fit.")
        else:
            strategy.message_frame = "mixed"
            strategy.regulatory_fit = "balanced"
            reasoning.append("Balanced regulatory focus -> mixed framing.")

        # Step 2: Processing Route Selection
        route = state.get_optimal_processing_route()
        route_map = {
            "central": PersuasionRoute.CENTRAL,
            "emotional": PersuasionRoute.EMOTIONAL,
            "social": PersuasionRoute.SOCIAL,
            "narrative": PersuasionRoute.NARRATIVE,
            "peripheral": PersuasionRoute.PERIPHERAL,
        }
        strategy.persuasion_route = route_map.get(route, PersuasionRoute.MIXED)
        reasoning.append(
            f"Optimal processing route: {route}. "
            f"Cognitive load={state.cognitive_load:.2f}, attention={state.attention_level:.2f}."
        )

        # Step 3: Construal Level Match (g=0.475)
        if state.construal_level > 0.6:
            strategy.construal_match = "abstract_why"
            strategy.copy_length = "brief"
            reasoning.append("High construal -> abstract why-framing, benefits, percent-off. g=0.475.")
        elif state.construal_level < 0.4:
            strategy.construal_match = "concrete_how"
            strategy.copy_length = "detailed"
            reasoning.append("Low construal -> concrete how-framing, features, dollar-off. g=0.475.")
        else:
            strategy.construal_match = "mixed"
            strategy.copy_length = "medium"

        # Step 4: Personality-Creative Matching
        strategy = self._apply_personality_matching(strategy, state, reasoning)

        # Step 5: Argument Strength
        if state.circadian_cognitive_capacity > 0.7 and state.cognitive_load < 0.5:
            strategy.argument_strength = "strong_detailed"
            reasoning.append("High cognitive capacity -> strong, detailed arguments effective.")
        else:
            strategy.argument_strength = "simple_heuristic"
            reasoning.append("Limited cognitive capacity -> simple heuristics, social proof, defaults.")

        # Step 6: Emotional Vehicle Selection
        strategy.emotional_vehicle = self._select_emotional_vehicle(state)

        # Step 7: Social Proof Configuration
        if state.social_proof_susceptibility > 0.6:
            strategy.social_proof_type = "reviews_and_popularity"
            strategy.social_proof_strength = 0.8
            reasoning.append("High social proof susceptibility -> prominent reviews and popularity signals.")
        elif state.social_proof_susceptibility > 0.4:
            strategy.social_proof_type = "expert_opinion"
            strategy.social_proof_strength = 0.4
        else:
            strategy.social_proof_type = "subtle"
            strategy.social_proof_strength = 0.2

        # Step 8: Temporal Optimization
        strategy.optimal_exposure_duration_ms = 3000 if state.attention_level > 0.6 else 1500
        strategy.frequency_cap_recommendation = 3
        strategy.spacing_recommendation_hours = max(24, 168 * 0.15)
        reasoning.append(
            f"Spacing: {strategy.spacing_recommendation_hours:.0f}h between exposures "
            f"(spacing effect: 150% better than massed)."
        )

        # Step 9: Context Optimization
        if ctx.content_sentiment > 0.3:
            strategy.mood_congruency_strategy = "leverage_positive_mood"
        elif ctx.content_sentiment < -0.3:
            strategy.mood_congruency_strategy = "contrast_or_empathize"
        else:
            strategy.mood_congruency_strategy = "neutral"

        # Step 10: Format Recommendation
        strategy.recommended_formats = self._recommend_formats(state, ctx)

        # Step 11: Counter-indications
        if not state.protection_mode:
            strategy.avoid_elements = self._generate_avoid_list(state)

        # Step 12: ADAM Integration — merge atom mechanisms and inferential chains
        if atom_mechanisms:
            strategy.atom_recommended_mechanisms = atom_mechanisms
            reasoning.append(
                f"ADAM atom DAG recommends: {atom_mechanisms[:3]}. "
                f"Merging with DSP strategy."
            )

        if inferential_chains:
            strategy.inferential_chains = inferential_chains
            reasoning.append(
                f"ADAM theory graph generated {len(inferential_chains)} inferential chains."
            )

        # Set mechanism chain
        strategy.primary_mechanism = MechanismType.REGULATORY_FIT
        strategy.mechanism_chain = [
            MechanismType.REGULATORY_FIT.value,
            MechanismType.CONSTRUAL_FIT.value,
            MechanismType.ELABORATION_LIKELIHOOD.value,
        ]
        if atom_mechanisms:
            strategy.mechanism_chain.extend(atom_mechanisms[:2])

        strategy.reasoning_trace = reasoning
        strategy.confidence = self._calculate_strategy_confidence(state, atom_mechanisms)
        strategy.ndf_profile_used = state.to_ndf_profile()

        return strategy

    # =========================================================================
    # Private helper methods
    # =========================================================================

    def _apply_vulnerability_protections(
        self, strategy: PersuasionStrategy, state: PsychologicalStateVector,
    ) -> PersuasionStrategy:
        """Apply ethical protections when vulnerability detected."""
        strategy.vulnerability_protections = []

        for flag in state.vulnerability_flags:
            if flag == VulnerabilityType.SLEEP_DEPRIVATION:
                strategy.vulnerability_protections.extend([
                    "SUPPRESS: gambling, high-interest credit, impulse luxury",
                    "SUPPRESS: urgency/scarcity pressure tactics",
                    "ALLOW: entertainment, informational, low-stakes",
                ])
            elif flag == VulnerabilityType.COGNITIVE_DEPLETION:
                strategy.vulnerability_protections.extend([
                    "SUPPRESS: complex multi-step funnels, high-pressure upsells",
                    "SIMPLIFY: single clear CTA, easy exit options",
                ])
            elif flag == VulnerabilityType.EMOTIONAL_DISTRESS:
                strategy.vulnerability_protections.extend([
                    "SUPPRESS: fear appeals, guilt messaging, urgency pressure",
                    "PREFER: empathetic tone, supportive messaging",
                ])
            elif flag == VulnerabilityType.DECISION_FATIGUE:
                strategy.vulnerability_protections.extend([
                    "SUPPRESS: complex comparisons, multi-option displays",
                    "PREFER: simple defaults, minimal cognitive demand",
                ])

        strategy.avoid_elements = list(strategy.vulnerability_protections)
        return strategy

    def _apply_personality_matching(
        self,
        strategy: PersuasionStrategy,
        state: PsychologicalStateVector,
        reasoning: list,
    ) -> PersuasionStrategy:
        """Apply Big Five personality matching to creative recommendations."""
        dominant_trait = max(
            [
                ("openness", state.openness),
                ("conscientiousness", state.conscientiousness),
                ("extraversion", state.extraversion),
                ("agreeableness", state.agreeableness),
                ("neuroticism", state.neuroticism),
            ],
            key=lambda x: x[1],
        )

        trait_name, trait_score = dominant_trait
        if trait_score > 0.6:
            creative_map = {
                "openness": {"style": "novel_aesthetic", "color": "warm_diverse"},
                "conscientiousness": {"style": "organized_detailed", "color": "cool_professional"},
                "extraversion": {"style": "social_energetic", "color": "bright_warm"},
                "agreeableness": {"style": "warm_caring", "color": "warm_soft"},
                "neuroticism": {"style": "reassuring_safe", "color": "cool_calming"},
            }
            mapping = creative_map.get(trait_name, {})
            strategy.visual_style = mapping.get("style", "balanced")
            strategy.color_temperature = mapping.get("color", "neutral")
            reasoning.append(
                f"Dominant trait: {trait_name} ({trait_score:.2f}) -> "
                f"{mapping.get('style', 'balanced')} creative. +40-50% conversion."
            )

        return strategy

    def _select_emotional_vehicle(self, state: PsychologicalStateVector) -> EmotionalVehicle:
        """Select optimal emotional vehicle based on state."""
        if state.arousal > 0.7:
            return EmotionalVehicle.EXCITEMENT
        elif state.valence < -0.3:
            return EmotionalVehicle.EMPATHY
        elif state.promotion_focus > state.prevention_focus:
            return EmotionalVehicle.ASPIRATION
        elif state.prevention_focus > state.promotion_focus:
            return EmotionalVehicle.TRUST
        elif state.social_proof_susceptibility > 0.6:
            return EmotionalVehicle.BELONGING
        else:
            return EmotionalVehicle.WARMTH

    def _recommend_formats(
        self, state: PsychologicalStateVector, ctx: ImpressionContext,
    ) -> List[CreativeFormat]:
        """Recommend creative formats based on state and context."""
        formats = []

        if state.attention_level > 0.6 and ctx.device_type != DeviceType.MOBILE:
            formats.append(CreativeFormat.VIDEO)
            formats.append(CreativeFormat.RICH_MEDIA)
        elif state.attention_level > 0.4:
            formats.append(CreativeFormat.NATIVE)
            formats.append(CreativeFormat.DISPLAY_STANDARD)
        else:
            formats.append(CreativeFormat.DISPLAY_STANDARD)

        if ctx.device_type == DeviceType.MOBILE:
            formats.append(CreativeFormat.INTERSTITIAL)

        if state.social_proof_susceptibility > 0.6:
            formats.append(CreativeFormat.SOCIAL_PROOF_OVERLAY)

        return formats

    def _generate_avoid_list(self, state: PsychologicalStateVector) -> List[str]:
        """Generate list of creative elements to avoid."""
        avoid = []

        if state.cognitive_load > 0.7:
            avoid.append("Complex layouts, dense text, multiple CTAs")

        if state.neuroticism > 0.6:
            avoid.append("Fear appeals, risk emphasis, uncertainty messaging")

        if state.decision_fatigue_level > 0.6:
            avoid.append("Multi-step funnels, complex comparisons")

        # Always avoid controlling language (d=-0.40 reactance)
        avoid.append("Controlling language: 'you must', 'don't miss', 'act now or else'")

        return avoid

    def _calculate_strategy_confidence(
        self, state: PsychologicalStateVector, atom_mechanisms: List[str] = None,
    ) -> float:
        """Estimate confidence in the generated strategy."""
        base = 0.5

        # Strong regulatory focus signal
        if abs(state.promotion_focus - state.prevention_focus) > 0.3:
            base += 0.15

        # Low cognitive load = cleaner signal
        if state.cognitive_load < 0.5:
            base += 0.1

        # Personality confidence
        if state.personality_confidence > 0.6:
            base += 0.1

        # ADAM atom reinforcement bonus
        if atom_mechanisms:
            base += 0.1

        return min(0.95, base)
