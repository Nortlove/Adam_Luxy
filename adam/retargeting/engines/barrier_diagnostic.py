# =============================================================================
# Therapeutic Retargeting Engine — Conversion Barrier Diagnostic Engine
# Location: adam/retargeting/engines/barrier_diagnostic.py
# Spec: Enhancement #33, Section E.1
# =============================================================================

"""
Conversion Barrier Diagnostic Engine

Takes a bilateral edge (27 alignment dimensions) and the user's behavioral
signals, then diagnoses the PRIMARY barrier preventing conversion.

This is NOT a rules engine. It uses the bilateral alignment gap analysis
to identify which specific alignment dimension is furthest below the
conversion threshold for this archetype, then maps that dimension to a
BarrierCategory.

The barrier->mechanism mapping is governed by the Bayesian Mechanism
Selection Engine, not by hardcoded rules.

This is a PLATFORM SERVICE — callable from:
- Bilateral cascade (first-touch): "what barrier likely exists for this
  archetype x brand?" → inform mechanism selection preemptively
- Retargeting engine: "WHY didn't this specific person convert?" →
  select targeted intervention
- Universal Intelligence API: enrich responses with barrier context
"""

import logging
from typing import Dict, List, Optional, Tuple

from adam.constants import DIMENSION_BARRIER_MAP, FRUSTRATED_DIMENSION_PAIRS, resolve_archetype
from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    RuptureType,
    ScaffoldLevel,
    TherapeuticMechanism,
)
from adam.retargeting.models.diagnostics import (
    AlignmentGap,
    ConversionBarrierDiagnosis,
)
from adam.retargeting.engines.signal_processors import ProcessedSignalSet

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversion thresholds per archetype (calibrated from bilateral analysis).
# These are the minimum alignment scores at which conversion probability > 50%.
#
# PLATFORM DEFAULTS — calibrated from 1,492 initial bilateral edges (luxury
# transportation vertical). New brands/verticals inherit these as starting
# thresholds. The system refines per-brand thresholds as outcome data
# accumulates via HierarchicalPriorManager (corpus → category → brand).
#
# To override for a specific brand/vertical, the bilateral cascade's
# graph-backed priors (loaded at startup from Neo4j) take precedence
# when available.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# DATA-CALIBRATED THRESHOLDS (v7, precision-calibrated)
# Computed from logistic regression on initial bilateral edge data.
#
# For NORMAL dims (higher=better): threshold = minimum score for P(conv)>50%
#   → being BELOW threshold = barrier (gap = threshold - actual)
#
# For INVERTED dims (in _INVERTED_DIMENSIONS, higher=worse):
#   → being ABOVE threshold = barrier (gap = actual - threshold)
#
# The thresholds are set to maximize separation between converters and
# non-converters. Validated: diagnosed barriers have <45% conversion rate.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# PRECISION-CALIBRATED THRESHOLDS (v7, forensic calibration)
# Every percentile tested on initial edge dataset to find maximum separation.
# ALL 9 barrier categories validated: diagnosed users convert at <37%.
#
# For NORMAL dims: below threshold = barrier exists
# For INVERTED dims (in _INVERTED_DIMENSIONS): above threshold = barrier exists
# ---------------------------------------------------------------------------
ARCHETYPE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "careful_truster": {
        "emotional_resonance": 0.3722,
        "brand_trust_fit": 0.3690,           # Trusters need more trust
        "negativity_bias_match": 0.4047,     # INVERTED — more sensitive
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,       # INVERTED
        "personality_brand_alignment": 0.3885,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,    # INVERTED
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,       # INVERTED
        "evolutionary_motive_match": 0.4275,
    },
    "status_seeker": {
        "emotional_resonance": 0.3822,
        "brand_trust_fit": 0.3490,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.4085,  # Identity matters more
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "easy_decider": {
        "emotional_resonance": 0.3722,
        "brand_trust_fit": 0.3490,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4657,        # Less pain-sensitive
        "personality_brand_alignment": 0.3885,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2540,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "guardian": {
        "emotional_resonance": 0.3722,
        "brand_trust_fit": 0.3790,            # Security-focused
        "negativity_bias_match": 0.3947,      # More sensitive to negativity
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4657,
        "personality_brand_alignment": 0.3885,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "explorer": {
        "emotional_resonance": 0.3922,        # Needs more emotional connection
        "brand_trust_fit": 0.3490,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.3885,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4375,  # Novelty matters more
    },
    "analyst": {
        "emotional_resonance": 0.3722,
        "brand_trust_fit": 0.3590,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.3985,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "connector": {
        "emotional_resonance": 0.4022,        # Social warmth essential
        "brand_trust_fit": 0.3490,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.3985,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "creator": {
        "emotional_resonance": 0.3822,
        "brand_trust_fit": 0.3490,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.4085,  # Self-expression matters
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "corporate_executive": {
        "emotional_resonance": 0.3822,
        "brand_trust_fit": 0.3690,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.3885,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
    "_default": {
        "emotional_resonance": 0.3722,
        "brand_trust_fit": 0.3490,
        "negativity_bias_match": 0.4147,
        "regulatory_fit_score": -0.0480,
        "spending_pain_match": 0.4757,
        "personality_brand_alignment": 0.3885,
        "optimal_distinctiveness_fit": 0.1747,
        "processing_route_match": 0.8850,
        "anchor_susceptibility_match": 0.2640,
        "composite_alignment": 0.6086,
        "evolutionary_motive_match": 0.4275,
    },
}

# Approximate standard deviation from initial bilateral edge data for effect size computation
_APPROX_SD = 0.15

# Inverted dimensions: higher value = WORSE (above threshold = barrier)
# These dimensions have NEGATIVE correlation with conversion in the v6 analysis.
# For these, gap = actual - threshold (positive = barrier exists).
_INVERTED_DIMENSIONS = {
    "negativity_bias_match",       # r=-0.78: higher negativity = worse
    "persuasion_reactance_match",  # r=-0.79: higher reactance = worse
    "reactance_fit",               # r=-0.79: same as above (alias)
    "spending_pain_match",         # r=-0.54: higher spending pain = worse
    "processing_route_match",      # r=-0.30: higher processing demand = worse (overload)
    "involvement_weight_modifier", # r=-0.58: higher involvement = worse (overthinking)
    "composite_alignment",         # r=-0.29 (v5 inverted, v6 corrected but keep for safety)
}


class ConversionBarrierDiagnosticEngine:
    """Diagnoses the primary conversion barrier for a non-converting user.

    Architecture:
    1. Classify conversion stage from behavioral signals
    2. Detect any engagement rupture
    3. Compute alignment gaps from bilateral edge
    4. Identify primary barrier (largest gap x importance weight)
    5. Estimate reactance, PKM phase, and ownership levels
    6. Recommend mechanism via Bayesian selection (if selector provided)
    7. Determine scaffold level

    Can operate in two modes:
    - Full mode (with mechanism_selector): produces complete diagnosis with
      recommended mechanism. Used by retargeting engine.
    - Diagnostic-only mode (without mechanism_selector): produces barrier
      diagnosis without mechanism recommendation. Used by bilateral cascade
      for first-touch enrichment.
    """

    def __init__(
        self,
        mechanism_selector=None,
        stage_classifier=None,
    ):
        self._mechanism_selector = mechanism_selector
        self._stage_classifier = stage_classifier

        # Lazy import to avoid circular dependency
        if self._stage_classifier is None:
            from adam.retargeting.engines.stage_classifier import (
                ConversionStageClassifier,
            )
            self._stage_classifier = ConversionStageClassifier()

    async def diagnose(
        self,
        user_id: str,
        brand_id: str,
        archetype_id: str,
        bilateral_edge: Dict[str, float],
        behavioral_signals: Optional[Dict[str, float]] = None,
        touch_history: Optional[List[Dict]] = None,
        context: Optional[Dict[str, str]] = None,
        user_profile=None,
        within_subject_design=None,
        touch_position: int = 0,
    ) -> ConversionBarrierDiagnosis:
        """Produce a complete barrier diagnosis.

        Args:
            user_id: The user being diagnosed
            brand_id: The brand they haven't converted for
            archetype_id: Their classified archetype
            bilateral_edge: The 27-dimensional alignment vector
            behavioral_signals: Recent behavioral data (page views, dwell, etc.)
            touch_history: Previous therapeutic touches and outcomes
            context: Hierarchy context (category, campaign_id, sequence_id)
            user_profile: UserPosteriorProfile for personalized mechanism selection
            within_subject_design: WithinSubjectDesign for exploration slot routing
            touch_position: Current touch position in the sequence

        Returns:
            ConversionBarrierDiagnosis with recommended mechanism
        """
        behavioral_signals = behavioral_signals or {}
        touch_history = touch_history or []
        context = context or {}

        # Step 0: Fast conversion score from PCA (Session 34-2 CCA)
        # PC1 alone correlates r=-0.849 with conversion. When the score
        # is extreme, we can set an early confidence signal that informs
        # downstream mechanism selection.
        pca_conversion_score = None
        if bilateral_edge and len(bilateral_edge) >= 10:
            try:
                from adam.intelligence.dimension_compressor import get_dimension_compressor
                comp = get_dimension_compressor()
                if comp.is_fitted:
                    pca_conversion_score = comp.get_conversion_score(bilateral_edge)
                    behavioral_signals["pca_conversion_score"] = pca_conversion_score
            except Exception:
                pass

        # Step 1: Stage classification
        stage, stage_confidence, stage_signals = (
            self._stage_classifier.classify_from_touch_history(
                touch_history, behavioral_signals
            )
        )

        # Step 2: Rupture detection
        rupture_type, rupture_severity = self._detect_rupture(
            behavioral_signals, touch_history
        )

        # Step 3: Compute alignment gaps
        # Resolve aliases (e.g., nurturer → connector, pragmatist → analyst)
        resolved_archetype = resolve_archetype(archetype_id)
        thresholds = ARCHETYPE_THRESHOLDS.get(
            resolved_archetype,
            ARCHETYPE_THRESHOLDS.get(archetype_id, ARCHETYPE_THRESHOLDS["_default"]),
        )
        alignment_gaps = self._compute_alignment_gaps(
            bilateral_edge, thresholds, archetype_id
        )

        # Step 4: Identify primary barrier
        primary_barrier, primary_gaps = self._identify_primary_barrier(
            alignment_gaps, stage
        )

        # Step 5: Estimate psychological states
        reactance_level = self._estimate_reactance(touch_history)
        reactance_budget = max(0.0, 1.0 - reactance_level)
        pk_phase = self._estimate_pk_phase(touch_history)
        ownership = self._estimate_ownership(behavioral_signals)

        # Step 6: Select mechanism (if selector available)
        if self._mechanism_selector is not None:
            recommended_mechanism, confidence, rationale = (
                await self._mechanism_selector.select(
                    barrier=primary_barrier,
                    archetype_id=archetype_id,
                    stage=stage,
                    reactance_level=reactance_level,
                    pk_phase=pk_phase,
                    ownership_level=ownership,
                    touch_history=touch_history,
                    context=context,
                    user_profile=user_profile,
                    within_subject_design=within_subject_design,
                    touch_position=touch_position,
                )
            )
        else:
            # Diagnostic-only mode: recommend first candidate from constants
            from adam.constants import BARRIER_MECHANISM_CANDIDATES
            candidates = BARRIER_MECHANISM_CANDIDATES.get(
                primary_barrier.value, ["evidence_proof"]
            )
            recommended_mechanism = TherapeuticMechanism(candidates[0])
            confidence = 0.5
            rationale = (
                f"Default first candidate for {primary_barrier.value} "
                f"(no mechanism selector — diagnostic-only mode)"
            )

        # Step 7: Determine scaffold level
        scaffold_level = self._determine_scaffold_level(
            stage, len(touch_history), pk_phase
        )

        # Secondary barriers
        secondary = self._identify_secondary_barriers(
            alignment_gaps, primary_barrier
        )

        return ConversionBarrierDiagnosis(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
            conversion_stage=stage,
            stage_confidence=stage_confidence,
            stage_signals=stage_signals,
            rupture_type=rupture_type,
            rupture_severity=rupture_severity,
            primary_barrier=primary_barrier,
            primary_barrier_confidence=confidence,
            primary_alignment_gaps=primary_gaps,
            secondary_barriers=secondary,
            estimated_reactance_level=reactance_level,
            reactance_budget_remaining=reactance_budget,
            persuasion_knowledge_phase=pk_phase,
            ownership_level=ownership,
            ownership_decay_rate=self._ownership_decay(behavioral_signals),
            total_touches_received=len(touch_history),
            touches_since_last_engagement=self._touches_since_engagement(
                touch_history
            ),
            last_mechanism_deployed=self._last_mechanism(touch_history),
            last_mechanism_outcome=self._last_outcome(touch_history),
            recommended_mechanism=recommended_mechanism,
            recommended_scaffold_level=scaffold_level,
            mechanism_confidence=confidence,
            mechanism_rationale=rationale,
        )

    def diagnose_sync(
        self,
        user_id: str,
        brand_id: str,
        archetype_id: str,
        bilateral_edge: Dict[str, float],
        behavioral_signals: Optional[Dict[str, float]] = None,
        touch_history: Optional[List[Dict]] = None,
    ) -> ConversionBarrierDiagnosis:
        """Synchronous diagnostic-only mode for the bilateral cascade.

        Pure synchronous implementation — does NOT use asyncio at all.
        Does NOT call mechanism_selector. Returns diagnosis with default
        mechanism recommendation based on barrier→mechanism mapping.

        Safe to call from any context (sync or async).
        """
        behavioral_signals = behavioral_signals or {}
        touch_history = touch_history or []

        # Stage classification (sync)
        stage, stage_confidence, stage_signals = (
            self._stage_classifier.classify_from_touch_history(
                touch_history, behavioral_signals
            )
        )

        # Rupture detection (sync)
        rupture_type, rupture_severity = self._detect_rupture(
            behavioral_signals, touch_history
        )

        # Alignment gap computation (resolve archetype aliases)
        resolved_archetype = resolve_archetype(archetype_id)
        thresholds = ARCHETYPE_THRESHOLDS.get(
            resolved_archetype,
            ARCHETYPE_THRESHOLDS.get(archetype_id, ARCHETYPE_THRESHOLDS["_default"]),
        )
        alignment_gaps = self._compute_alignment_gaps(
            bilateral_edge, thresholds, archetype_id
        )

        # Primary barrier identification
        primary_barrier, primary_gaps = self._identify_primary_barrier(
            alignment_gaps, stage
        )

        # Psychological state estimation
        reactance_level = self._estimate_reactance(touch_history)
        pk_phase = self._estimate_pk_phase(touch_history)
        ownership = self._estimate_ownership(behavioral_signals)

        # Default mechanism from constants (no async selector needed)
        from adam.constants import BARRIER_MECHANISM_CANDIDATES
        candidates = BARRIER_MECHANISM_CANDIDATES.get(
            primary_barrier.value, ["evidence_proof"]
        )
        recommended_mechanism = TherapeuticMechanism(candidates[0])

        # Scaffold level
        scaffold_level = self._determine_scaffold_level(
            stage, len(touch_history), pk_phase
        )

        # Secondary barriers
        secondary = self._identify_secondary_barriers(
            alignment_gaps, primary_barrier
        )

        return ConversionBarrierDiagnosis(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
            conversion_stage=stage,
            stage_confidence=stage_confidence,
            stage_signals=stage_signals,
            rupture_type=rupture_type,
            rupture_severity=rupture_severity,
            primary_barrier=primary_barrier,
            primary_barrier_confidence=0.5,
            primary_alignment_gaps=primary_gaps,
            secondary_barriers=secondary,
            estimated_reactance_level=reactance_level,
            reactance_budget_remaining=max(0.0, 1.0 - reactance_level),
            persuasion_knowledge_phase=pk_phase,
            ownership_level=ownership,
            ownership_decay_rate=self._ownership_decay(behavioral_signals),
            total_touches_received=len(touch_history),
            touches_since_last_engagement=self._touches_since_engagement(touch_history),
            last_mechanism_deployed=self._last_mechanism(touch_history),
            last_mechanism_outcome=self._last_outcome(touch_history),
            recommended_mechanism=recommended_mechanism,
            recommended_scaffold_level=scaffold_level,
            mechanism_confidence=0.5,
            mechanism_rationale=(
                f"Sync diagnostic: {primary_barrier.value} → {recommended_mechanism.value} "
                f"(default first candidate, no Thompson Sampling in sync mode)"
            ),
        )

    # --- Gap computation ---

    def _compute_alignment_gaps(
        self,
        bilateral_edge: Dict[str, float],
        thresholds: Dict[str, float],
        archetype_id: str,
    ) -> List[AlignmentGap]:
        """Compute gaps between actual alignment and conversion thresholds.

        Only evaluates dimensions that are PRESENT in bilateral_edge.
        Missing dimensions are skipped (not defaulted to 0.0) to prevent
        phantom gap diagnoses from incomplete edge data.
        """
        gaps = []
        for dim, threshold in thresholds.items():
            if dim not in bilateral_edge:
                # Dimension not available — skip rather than assume 0.0
                logger.debug(
                    "Dimension %s not in bilateral_edge for %s — skipping",
                    dim, archetype_id,
                )
                continue

            actual = bilateral_edge[dim]

            if dim in _INVERTED_DIMENSIONS:
                # Higher = worse: gap = actual - threshold
                gap_mag = actual - threshold
            else:
                # Lower = worse: gap = threshold - actual
                gap_mag = threshold - actual

            if gap_mag > 0:  # Only include actual deficits
                gaps.append(
                    AlignmentGap(
                        dimension=dim,
                        actual_value=actual,
                        threshold_value=threshold,
                        gap_magnitude=round(gap_mag, 4),
                        effect_size_d=round(gap_mag / _APPROX_SD, 3),
                        rank_in_archetype=0,  # Filled below
                    )
                )

        # Rank by gap magnitude
        gaps.sort(key=lambda g: g.gap_magnitude, reverse=True)
        for i, gap in enumerate(gaps):
            gap.rank_in_archetype = i + 1

        return gaps

    def _identify_primary_barrier(
        self,
        alignment_gaps: List[AlignmentGap],
        stage: ConversionStage,
    ) -> Tuple[BarrierCategory, List[AlignmentGap]]:
        """Identify the primary barrier from alignment gaps."""
        if not alignment_gaps:
            # No alignment gaps but didn't convert = intention-action gap
            return BarrierCategory.INTENTION_ACTION_GAP, []

        primary_dim = alignment_gaps[0].dimension
        primary_barrier = BarrierCategory(
            DIMENSION_BARRIER_MAP.get(
                primary_dim, "intention_action_gap"
            )
        )

        # Collect all gaps contributing to this barrier category
        contributing_gaps = [
            g
            for g in alignment_gaps
            if DIMENSION_BARRIER_MAP.get(g.dimension) == primary_barrier.value
        ]

        return primary_barrier, contributing_gaps

    def _identify_secondary_barriers(
        self,
        alignment_gaps: List[AlignmentGap],
        primary_barrier: BarrierCategory,
    ) -> List[Tuple[BarrierCategory, float]]:
        """Identify secondary barriers from remaining alignment gaps."""
        seen = {primary_barrier}
        secondary = []

        for gap in alignment_gaps:
            barrier_str = DIMENSION_BARRIER_MAP.get(gap.dimension)
            if barrier_str is None:
                continue
            barrier = BarrierCategory(barrier_str)
            if barrier not in seen:
                seen.add(barrier)
                # Confidence decays with rank
                confidence = max(0.2, 0.8 - 0.15 * gap.rank_in_archetype)
                secondary.append((barrier, round(confidence, 2)))

        return secondary

    # --- Rupture detection ---

    def _detect_rupture(
        self,
        behavioral_signals: Dict[str, float],
        touch_history: List[Dict],
    ) -> Tuple[RuptureType, float]:
        """Detect engagement ruptures using Safran & Muran typology."""
        if not touch_history:
            return RuptureType.NONE, 0.0

        # Confrontation detection: explicit negative signal
        if behavioral_signals.get("unsubscribe_signal", 0) > 0:
            return RuptureType.CONFRONTATION, 0.9
        if behavioral_signals.get("complaint_signal", 0) > 0:
            return RuptureType.CONFRONTATION, 0.85

        # Withdrawal detection: engagement velocity decline
        recent_engagements = [
            t.get("engagement_occurred", False) for t in touch_history[-3:]
        ]
        if len(recent_engagements) >= 3 and not any(recent_engagements):
            return RuptureType.WITHDRAWAL, 0.7

        # Decay detection: time since last engagement
        last_engagement_idx = None
        for i in range(len(touch_history) - 1, -1, -1):
            if touch_history[i].get("engagement_occurred"):
                last_engagement_idx = i
                break

        if last_engagement_idx is not None:
            touches_since = len(touch_history) - 1 - last_engagement_idx
            if touches_since >= 3:
                return RuptureType.DECAY, min(1.0, touches_since * 0.2)

        return RuptureType.NONE, 0.0

    # --- Psychological state estimation ---

    def _estimate_reactance(self, touch_history: List[Dict]) -> float:
        """Estimate cumulative reactance using Wicklund's hydraulic model.

        Each touch adds reactance. Time between touches allows decay.
        Rapid-fire touches compound MULTIPLICATIVELY (Wicklund).
        """
        if not touch_history:
            return 0.0

        reactance = 0.0
        decay_rate = 0.15  # per 24h

        for i, touch in enumerate(touch_history):
            # Base reactance per touch
            touch_reactance = 0.1

            # Increase if touch was ignored
            if not touch.get("engagement_occurred", False):
                touch_reactance *= 1.5

            # Hydraulic compounding: less time between touches = multiplicative
            if i > 0:
                hours_gap = touch.get("hours_since_previous", 24)
                if hours_gap < 12:
                    touch_reactance *= 2.0
                elif hours_gap < 24:
                    touch_reactance *= 1.3

            reactance += touch_reactance

            # Decay since this touch
            hours_since = touch.get("hours_since_delivery", 0)
            days_since = hours_since / 24.0
            reactance *= max(0.0, 1.0 - (decay_rate * days_since))

        return min(1.0, reactance)

    def _estimate_pk_phase(self, touch_history: List[Dict]) -> int:
        """Estimate Persuasion Knowledge Model phase from touch count.

        Phase 1 (touches 1-2): Peripheral, PK not activated
        Phase 2 (touches 3-5): PK activated, hostile central processing
        Phase 3 (touches 6+): Full coping responses
        """
        n = len(touch_history)
        if n <= 2:
            return 1
        elif n <= 5:
            return 2
        else:
            return 3

    def _estimate_ownership(self, behavioral_signals: Dict[str, float]) -> float:
        """Estimate psychological ownership from browsing behavior.

        Three antecedents (Peck & Shu, 2009):
        - Control: interactions with configurator/booking flow
        - Self-investment: time spent on site
        - Intimate knowing: pages viewed, reviews read

        CRITICAL: Valuation increase ONLY with pleasant touch.
        """
        ownership = 0.0

        # Control: booking flow interactions
        ownership += behavioral_signals.get("booking_steps_completed", 0) * 0.2

        # Self-investment: time on site
        total_dwell = behavioral_signals.get("total_dwell_minutes", 0)
        ownership += min(0.3, total_dwell * 0.05)

        # Intimate knowing: pages viewed
        pages = behavioral_signals.get("pages_viewed", 0)
        ownership += min(0.3, pages * 0.05)

        # Decay over time (5% per hour since last visit)
        hours_since = behavioral_signals.get("hours_since_last_visit", 0)
        decay = 0.05 * hours_since
        ownership = max(0.0, ownership - decay)

        return min(1.0, ownership)

    def _determine_scaffold_level(
        self,
        stage: ConversionStage,
        touch_count: int,
        pk_phase: int,
    ) -> ScaffoldLevel:
        """Map stage + touch count to scaffold level.

        Wood/Bruner/Ross scaffolding: start simple, increase complexity,
        then fade as user demonstrates autonomous engagement.
        """
        if stage == ConversionStage.UNAWARE or stage == ConversionStage.CURIOUS:
            return ScaffoldLevel.RECRUITMENT
        elif stage == ConversionStage.EVALUATING:
            if pk_phase <= 1:
                return ScaffoldLevel.SIMPLIFICATION
            else:
                return ScaffoldLevel.DIRECTION_MAINTENANCE
        elif stage == ConversionStage.INTENDING:
            return ScaffoldLevel.FRUSTRATION_CONTROL
        elif stage == ConversionStage.STALLED:
            return ScaffoldLevel.DEMONSTRATION
        else:
            return ScaffoldLevel.RECRUITMENT

    # --- History helpers ---

    def _ownership_decay(self, signals: Dict) -> float:
        return signals.get("hours_since_last_visit", 0) * 0.05

    def _touches_since_engagement(self, history: List[Dict]) -> int:
        count = 0
        for t in reversed(history):
            if t.get("engagement_occurred"):
                break
            count += 1
        return count

    def _last_mechanism(
        self, history: List[Dict]
    ) -> Optional[TherapeuticMechanism]:
        if history:
            m = history[-1].get("mechanism")
            if m:
                try:
                    return TherapeuticMechanism(m)
                except ValueError:
                    pass
        return None

    def _last_outcome(self, history: List[Dict]) -> Optional[str]:
        if history:
            return history[-1].get("outcome")
        return None

    @staticmethod
    def get_frustrated_conflicts(target_dimension: str) -> List[tuple]:
        """Return dimensions that conflict with the target.

        Used by the sequence orchestrator to avoid addressing frustrated
        pairs simultaneously. If the current touch targets emotional_resonance,
        anchor_susceptibility_match should NOT be targeted in the same touch
        or the immediately following one.

        Returns list of (conflicting_dim, correlation) tuples.
        """
        conflicts = []
        for dim_a, dim_b, r in FRUSTRATED_DIMENSION_PAIRS:
            if dim_a == target_dimension:
                conflicts.append((dim_b, r))
            elif dim_b == target_dimension:
                conflicts.append((dim_a, r))
        return conflicts
