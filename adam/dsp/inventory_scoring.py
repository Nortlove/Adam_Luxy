"""
DSP Enrichment Engine — Inventory Enrichment Scoring Engine
=============================================================

Translates psychological enrichment into CPM premium justification.

Impressions enriched with psychological targeting command premium CPMs
because they convert at higher rates.

Premium range: 1.0x (no enrichment) to 5.0x (maximum enrichment)

Dimensions:
    - Psychological match quality (regulatory fit, construal match, personality)
    - Persuasion optimization (right mechanism for right state)
    - Temporal alignment (circadian, fatigue, session phase)
    - Creative fit (format matches processing mode)
    - Attention probability (viewability, clutter, engagement)
    - Vulnerability clean (no ethical flags)
    - ADAM inferential depth (theory graph chain depth, atom confidence)
"""

from typing import Dict, List

from adam.dsp.models import (
    ImpressionContext,
    PsychologicalStateVector,
    PersuasionStrategy,
    InventoryEnrichmentScore,
    PersuasionRoute,
    DeviceType,
)


class InventoryEnrichmentScoringEngine:
    """
    Translates psychological enrichment into CPM premium justification.
    Extended with ADAM-specific scoring dimensions.
    """

    def score_impression(
        self,
        strategy: PersuasionStrategy,
        state: PsychologicalStateVector,
        ctx: ImpressionContext,
    ) -> InventoryEnrichmentScore:
        """Score an impression for enrichment premium."""

        # Dimension 1: Psychological match quality
        psych_match = self._score_psychological_match(strategy, state)

        # Dimension 2: Persuasion optimization
        persuasion_opt = self._score_persuasion_optimization(strategy, state)

        # Dimension 3: Temporal alignment
        temporal = self._score_temporal_alignment(state, ctx)

        # Dimension 4: Creative fit
        creative_fit = self._score_creative_fit(strategy, state, ctx)

        # Dimension 5: Attention probability
        attention = self._score_attention_probability(state, ctx)

        # Dimension 6: Vulnerability clean
        vuln_clean = 1.0 if not state.protection_mode else 0.3

        # Dimension 7: ADAM inferential depth bonus
        adam_bonus = self._score_adam_enrichment(strategy)

        # Weighted combination -> enrichment multiplier
        weights = {
            "psychological_match": 0.22,
            "persuasion_optimization": 0.18,
            "temporal_alignment": 0.12,
            "creative_fit": 0.12,
            "attention_probability": 0.13,
            "vulnerability_clean": 0.08,
            "adam_enrichment": 0.15,
        }

        composite = (
            weights["psychological_match"] * psych_match
            + weights["persuasion_optimization"] * persuasion_opt
            + weights["temporal_alignment"] * temporal
            + weights["creative_fit"] * creative_fit
            + weights["attention_probability"] * attention
            + weights["vulnerability_clean"] * vuln_clean
            + weights["adam_enrichment"] * adam_bonus
        )

        # Scale to 1.0x - 5.0x multiplier
        enrichment_multiplier = 1.0 + (composite * 4.0)

        score = InventoryEnrichmentScore(
            psychological_match_score=psych_match,
            persuasion_optimization_score=persuasion_opt,
            temporal_alignment_score=temporal,
            creative_fit_score=creative_fit,
            attention_probability=attention,
            vulnerability_clean=vuln_clean,
            enrichment_multiplier=enrichment_multiplier,
            recommended_strategy=strategy,
            reasoning_trace=strategy.reasoning_trace,
            inferential_chain_count=len(strategy.inferential_chains),
            atom_confidence=strategy.confidence if strategy.atom_recommended_mechanisms else 0.0,
            theory_graph_depth=len(strategy.inferential_chains),
        )

        return score

    # =========================================================================
    # Scoring dimension methods
    # =========================================================================

    def _score_psychological_match(
        self, strategy: PersuasionStrategy, state: PsychologicalStateVector,
    ) -> float:
        """Score how well the strategy matches the psychological state."""
        score = 0.0

        # Regulatory fit (highest value -- OR=2.0 to 6.0)
        if strategy.regulatory_fit in ("promotion_gain", "prevention_loss"):
            rf_strength = abs(state.promotion_focus - state.prevention_focus)
            score += 0.4 * rf_strength

        # Construal match (g=0.475)
        if strategy.construal_match != "mixed":
            score += 0.3

        # Personality match (+40-50%)
        if state.personality_confidence > 0.5:
            score += 0.3 * state.personality_confidence

        return min(1.0, score)

    def _score_persuasion_optimization(
        self, strategy: PersuasionStrategy, state: PsychologicalStateVector,
    ) -> float:
        """Score persuasion mechanism optimization."""
        score = 0.5  # baseline

        # Processing route match
        if state.cognitive_load < 0.4 and strategy.persuasion_route == PersuasionRoute.CENTRAL:
            score += 0.25
        elif state.cognitive_load > 0.6 and strategy.persuasion_route == PersuasionRoute.PERIPHERAL:
            score += 0.25
        elif state.cognitive_load > 0.6 and strategy.persuasion_route == PersuasionRoute.EMOTIONAL:
            score += 0.2

        # Social proof match
        if state.social_proof_susceptibility > 0.6 and strategy.social_proof_strength > 0.6:
            score += 0.15

        return min(1.0, score)

    def _score_temporal_alignment(
        self, state: PsychologicalStateVector, ctx: ImpressionContext,
    ) -> float:
        """Score temporal alignment with circadian and session state."""
        score = state.circadian_cognitive_capacity

        if state.circadian_cognitive_capacity > 0.8:
            score = min(1.0, score + 0.1)

        score -= state.decision_fatigue_level * 0.2

        return max(0.0, min(1.0, score))

    def _score_creative_fit(
        self,
        strategy: PersuasionStrategy,
        state: PsychologicalStateVector,
        ctx: ImpressionContext,
    ) -> float:
        """Score creative format fit with processing state."""
        score = 0.5

        if ctx.device_type == DeviceType.MOBILE and strategy.argument_strength == "simple_heuristic":
            score += 0.2
        elif ctx.device_type == DeviceType.DESKTOP and strategy.argument_strength == "strong_detailed":
            score += 0.2

        if ctx.above_fold:
            score += 0.15

        score += ctx.viewability_prediction * 0.15

        return min(1.0, score)

    def _score_attention_probability(
        self, state: PsychologicalStateVector, ctx: ImpressionContext,
    ) -> float:
        """Score the probability this impression will receive attention."""
        base = state.attention_level
        clutter_penalty = min(0.5, ctx.ad_density * 0.15)
        base -= clutter_penalty
        base -= state.mind_wandering_probability * 0.2
        base = max(base, ctx.viewability_prediction * 0.3)
        return max(0.0, min(1.0, base))

    def _score_adam_enrichment(self, strategy: PersuasionStrategy) -> float:
        """Score the additional enrichment from ADAM's inferential intelligence."""
        score = 0.0

        # Inferential chain depth adds value
        chain_count = len(strategy.inferential_chains)
        if chain_count > 0:
            score += min(0.4, chain_count * 0.1)

        # Atom mechanism recommendations add confidence
        if strategy.atom_recommended_mechanisms:
            score += 0.3

        # Higher strategy confidence = higher ADAM enrichment
        if strategy.confidence > 0.7:
            score += 0.2
        elif strategy.confidence > 0.5:
            score += 0.1

        return min(1.0, score)
