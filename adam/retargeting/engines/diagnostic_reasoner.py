# =============================================================================
# DiagnosticReasoner — Core Platform Deductive Engine
# Location: adam/retargeting/engines/diagnostic_reasoner.py
# =============================================================================

"""
Diagnostic deduction engine for the ADAM psycholinguistic advertising system.

NOT a Thompson Sampling optimizer. This is a constraint-based deductive
engine that interprets each outcome as evidence about an underlying
psychological puzzle, then selects the constrained next move that
maximizes diagnostic information.

The 4-phase pipeline:
  A. Outcome Classification → Hypothesis Evaluation
  B. Candidate Generation → Constraint Filtering
  C. Move Selection (effectiveness × diagnostic value)
  D. Reasoning Trace + Upstream Signal Generation

Architecture:
  - Stateless service (all state via DiagnosticInput)
  - <30ms common path (CPU-bound: dict lookups, dot products, arithmetic)
  - Reusable platform primitive: called by SequenceOrchestrator,
    CampaignOrchestrator, first-touch flows, etc.
"""

import logging
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from adam.constants import (
    BARRIER_MECHANISM_CANDIDATES,
    DIMENSION_BARRIER_MAP,
    FRUSTRATED_DIMENSION_PAIRS,
)
from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)
from adam.retargeting.models.diagnostic_assessment import (
    ConstraintViolation,
    DiagnosticAssessment,
    DiagnosticInput,
    EngagementOutcome,
    FrustratedPairPlan,
    HypothesisEvaluation,
    NonConversionHypothesis,
    ReasoningStep,
)
from adam.retargeting.personality_mechanism_matrix import (
    PERSONALITY_MECHANISM_SUSCEPTIBILITY,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS (pre-computed from mechanism_selector.py)
# =============================================================================

PAGE_CLUSTERS = ["analytical", "emotional", "social", "transactional", "aspirational"]

POLAR_OPPOSITES = {
    "analytical": "emotional",
    "emotional": "analytical",
    "social": "analytical",
    "transactional": "aspirational",
    "aspirational": "transactional",
    "neutral": "emotional",
    "": "analytical",
}

# Psychological distance between clusters (0=same, 1=maximum distance)
CLUSTER_DISTANCE = {
    ("analytical", "emotional"): 1.0,
    ("analytical", "social"): 0.7,
    ("analytical", "transactional"): 0.4,
    ("analytical", "aspirational"): 0.6,
    ("emotional", "social"): 0.5,
    ("emotional", "transactional"): 0.9,
    ("emotional", "aspirational"): 0.4,
    ("social", "transactional"): 0.6,
    ("social", "aspirational"): 0.5,
    ("transactional", "aspirational"): 0.8,
}

AUTONOMY_SAFE_MECHANISMS = {
    "autonomy_restoration", "narrative_transportation",
    "social_proof_matched", "evidence_proof", "vivid_scenario",
}

PKM_PENALIZED_MECHANISMS = {
    "micro_commitment", "loss_framing", "dissonance_activation", "price_anchor",
}

STAGE_MECHANISM_FIT = {
    "curious": {
        "matched": {"narrative_transportation", "vivid_scenario"},
        "mismatched": {"implementation_intention", "loss_framing", "price_anchor"},
    },
    "evaluating": {
        "matched": {"evidence_proof", "social_proof_matched", "claude_argument"},
        "mismatched": set(),
    },
    "intending": {
        "matched": {"implementation_intention", "ownership_reactivation", "micro_commitment"},
        "mismatched": {"narrative_transportation"},
    },
    "stalled": {
        "matched": {"ownership_reactivation", "loss_framing", "implementation_intention"},
        "mismatched": set(),
    },
}

# Mechanism → primary bilateral dimension it addresses
MECHANISM_TARGET_DIMENSION = {
    "evidence_proof": "brand_trust_fit",
    "claude_argument": "brand_trust_fit",
    "social_proof_matched": "emotional_resonance",
    "narrative_transportation": "emotional_resonance",
    "vivid_scenario": "emotional_resonance",
    "construal_shift": "regulatory_fit_score",
    "autonomy_restoration": "persuasion_reactance_match",
    "ownership_reactivation": "composite_alignment",
    "implementation_intention": "composite_alignment",
    "micro_commitment": "composite_alignment",
    "loss_framing": "anchor_susceptibility_match",
    "price_anchor": "anchor_susceptibility_match",
    "dissonance_activation": "personality_brand_alignment",
    "anxiety_resolution": "negativity_bias_match",
    "frustration_control": "processing_route_match",
    "novelty_disruption": "evolutionary_motive_match",
}

# Cialdini mapping for personality susceptibility lookup
MECHANISM_TO_CIALDINI = {
    "evidence_proof": "authority",
    "claude_argument": "authority",
    "social_proof_matched": "social_proof",
    "narrative_transportation": "narrative",
    "vivid_scenario": "narrative",
    "construal_shift": "commitment",
    "autonomy_restoration": "autonomy_support",
    "ownership_reactivation": "commitment",
    "implementation_intention": "commitment",
    "micro_commitment": "commitment",
    "loss_framing": "scarcity",
    "price_anchor": "reciprocity",
    "dissonance_activation": "commitment",
    "anxiety_resolution": "authority",
    "frustration_control": "authority",
    "novelty_disruption": "scarcity",
}

# Scaffold level mapping from stage + PKM phase
SCAFFOLD_MAP = {
    ("curious", 1): "recruitment",
    ("curious", 2): "simplification",
    ("evaluating", 1): "simplification",
    ("evaluating", 2): "direction_maintenance",
    ("evaluating", 3): "direction_maintenance",
    ("intending", 1): "frustration_control",
    ("intending", 2): "frustration_control",
    ("intending", 3): "demonstration",
    ("stalled", 1): "demonstration",
    ("stalled", 2): "demonstration",
    ("stalled", 3): "demonstration",
}


# =============================================================================
# DIAGNOSTIC REASONER
# =============================================================================


class DiagnosticReasoner:
    """Diagnostic deduction engine for psycholinguistic advertising.

    Interprets each outcome as evidence about a psychological puzzle,
    then selects the constrained next move that maximizes diagnostic
    information — not just expected reward.

    This is a core platform primitive. Register via:
        adam.core.dependencies.get_diagnostic_reasoner()
    """

    def __init__(self, barrier_diagnostic_engine=None):
        self._barrier_engine = barrier_diagnostic_engine
        self._frustrated_index = self._build_frustrated_pairs_index()
        self._mechanism_ideal_cache: Dict[str, np.ndarray] = {}

    # ─── PUBLIC API ─────────────────────────────────────────────────

    async def reason(self, inp: DiagnosticInput) -> DiagnosticAssessment:
        """Full diagnostic reasoning pipeline. <30ms."""
        return self.reason_sync(inp)

    def reason_sync(self, inp: DiagnosticInput) -> DiagnosticAssessment:
        """Synchronous diagnostic reasoning pipeline."""
        t0 = time.perf_counter()
        steps: List[ReasoningStep] = []
        step_n = 0

        # ── Phase A: Outcome Classification ──────────────────────

        step_n += 1
        engagement = self._classify_engagement(inp)
        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="outcome_classification",
            description=f"Classified outcome as {engagement.value}",
            inputs={"engagement_type": inp.engagement_type, "converted": inp.converted},
            outputs={"classification": engagement.value},
        ))

        # Short-circuit: conversion
        if engagement == EngagementOutcome.CONVERSION:
            return self._handle_conversion(inp, steps, t0)

        # Short-circuit: active rejection
        if engagement == EngagementOutcome.ACTIVE_REJECTION:
            return self._handle_active_rejection(inp, steps, t0)

        # ── Phase A continued: Hypothesis Evaluation ─────────────

        step_n += 1
        hypotheses = self._evaluate_hypotheses(engagement, inp)
        primary = max(hypotheses, key=lambda h: h.confidence)
        primary.is_primary = True

        confidences = {h.hypothesis.value: round(h.confidence, 3) for h in hypotheses}
        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="hypothesis_evaluation",
            description=(
                f"Primary hypothesis: {primary.hypothesis.value} "
                f"(confidence={primary.confidence:.2f})"
            ),
            inputs={"deployed_mechanism": inp.deployed_mechanism, "deployed_page": inp.deployed_page_cluster},
            outputs={"confidences": confidences, "primary": primary.hypothesis.value},
        ))

        # ── Phase B: Candidate Generation ────────────────────────

        step_n += 1
        candidates = self._generate_candidates(inp, primary.hypothesis, engagement)
        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="candidate_generation",
            description=f"Generated {len(candidates)} candidate (mechanism, page_cluster) moves",
            outputs={"candidate_count": len(candidates)},
        ))

        # ── Phase B: Constraint Filtering ────────────────────────

        step_n += 1
        surviving, violations = self._apply_constraints(candidates, inp)
        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="constraint_check",
            description=(
                f"{len(candidates) - len(surviving)} eliminated by constraints, "
                f"{len(surviving)} surviving"
            ),
            outputs={
                "eliminated": len(candidates) - len(surviving),
                "surviving": len(surviving),
                "violation_types": list({v.constraint_type for v in violations}),
            },
        ))

        # ── Phase B: Diagnostic Value Scoring ────────────────────

        step_n += 1
        scored = self._score_candidates(surviving, inp, confidences)
        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="diagnostic_scoring",
            description=f"Scored {len(scored)} candidates by effectiveness × diagnostic value",
            outputs={"top_3": [(m, c, round(s, 3)) for m, c, s in scored[:3]]},
        ))

        # ── Phase C: Move Selection ──────────────────────────────

        step_n += 1
        if not scored:
            # All moves eliminated — fallback to autonomy_restoration on polar opposite
            mech = "autonomy_restoration"
            cluster = POLAR_OPPOSITES.get(inp.deployed_page_cluster, "analytical")
            confidence = 0.2
        else:
            mech, cluster, score = scored[0]
            confidence = min(0.95, score)

        scaffold = self._determine_scaffold(inp.current_stage, inp.pkm_phase)

        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="move_selection",
            description=(
                f"Selected: {mech} on {cluster} (scaffold={scaffold}, "
                f"confidence={confidence:.2f})"
            ),
            outputs={"mechanism": mech, "page_cluster": cluster, "scaffold": scaffold},
        ))

        # ── Phase C: Frustrated Pair Planning ────────────────────

        frustrated_plan = self._check_frustrated_pairs(inp, mech)

        # ── Phase D: Alternatives + Signals ──────────────────────

        step_n += 1
        alternatives = [
            {"mechanism": m, "page_cluster": c, "score": str(round(s, 3))}
            for m, c, s in scored[1:4]
        ] if len(scored) > 1 else []

        signals = self._generate_signals(inp, engagement, primary.hypothesis, mech, cluster)
        diagnostic_value = scored[0][2] * 0.4 if scored else 0.0
        diag_explanation = self._explain_diagnostic_value(
            mech, cluster, primary.hypothesis, inp,
        )

        steps.append(ReasoningStep(
            step_number=step_n,
            step_type="signal_generation",
            description=f"Generated {len(signals)} upstream signals",
            outputs={"signal_keys": list(signals.keys())},
        ))

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return DiagnosticAssessment(
            user_id=inp.user_id,
            brand_id=inp.brand_id,
            observed_outcome=engagement,
            outcome_interpretation=self._interpret_outcome(engagement, primary.hypothesis, inp),
            hypothesis_evaluations=hypotheses,
            primary_hypothesis=primary.hypothesis,
            hypothesis_confidences=confidences,
            next_mechanism=mech,
            next_page_cluster=cluster,
            next_scaffold_level=scaffold,
            move_confidence=confidence,
            reasoning_trace=steps,
            total_reasoning_ms=round(elapsed_ms, 2),
            expected_diagnostic_value=round(diagnostic_value, 4),
            diagnostic_explanation=diag_explanation,
            constraint_violations=violations,
            frustrated_pair_plan=frustrated_plan,
            alternatives_if_fails=alternatives,
            signals_for_upstream=signals,
        )

    # ─── PHASE A: OUTCOME CLASSIFICATION ────────────────────────

    def _classify_engagement(self, inp: DiagnosticInput) -> EngagementOutcome:
        if inp.converted:
            return EngagementOutcome.CONVERSION
        et = (inp.engagement_type or "").lower()
        if et in ("unsubscribe", "complaint", "ad_hide", "negative"):
            return EngagementOutcome.ACTIVE_REJECTION
        if not et:
            return EngagementOutcome.IGNORE
        if et in ("click", "site_visit", "booking_start"):
            return EngagementOutcome.CLICK_NO_CONVERT
        if "dwell" in et:
            return EngagementOutcome.PARTIAL_ENGAGEMENT
        return EngagementOutcome.CLICK_NO_CONVERT

    # ─── PHASE A: HYPOTHESIS EVALUATION ─────────────────────────

    def _evaluate_hypotheses(
        self,
        engagement: EngagementOutcome,
        inp: DiagnosticInput,
    ) -> List[HypothesisEvaluation]:
        h1 = self._eval_h1_wrong_page(inp)
        h2 = self._eval_h2_wrong_mechanism(inp)
        h3 = self._eval_h3_wrong_stage(inp)
        h4 = self._eval_h4_pkm_reactance(inp)
        h5 = self._eval_h5_fatigue(inp)

        hypotheses = [h1, h2, h3, h4, h5]

        # Normalize confidences
        total = sum(h.confidence for h in hypotheses)
        if total > 0:
            for h in hypotheses:
                h.confidence = round(h.confidence / total, 3)

        # Engagement-type priors: ignores make all hypotheses plausible,
        # clicks make H1/H5 less likely (page got attention)
        if engagement == EngagementOutcome.CLICK_NO_CONVERT:
            h1.confidence *= 0.3  # Page was good enough to click
            h5.confidence *= 0.3  # Ad was noticed
            # Renormalize
            total = sum(h.confidence for h in hypotheses)
            if total > 0:
                for h in hypotheses:
                    h.confidence = round(h.confidence / total, 3)

        elif engagement == EngagementOutcome.PARTIAL_ENGAGEMENT:
            h1.confidence *= 0.5  # Page had some resonance
            h5.confidence *= 0.2  # Definitely noticed
            total = sum(h.confidence for h in hypotheses)
            if total > 0:
                for h in hypotheses:
                    h.confidence = round(h.confidence / total, 3)

        # Enhancement #34: Apply external hypothesis modifiers from
        # nonconscious signals (processing depth, click latency, device
        # mismatch, reactance detection, etc.)
        ext = inp.external_h_modifiers
        if ext:
            h_map = {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5}
            for key, hyp in h_map.items():
                modifier = ext.get(key, 0.0)
                if modifier != 0.0:
                    hyp.confidence = max(0.0, hyp.confidence + modifier)
            # Renormalize after external modifiers
            total = sum(h.confidence for h in hypotheses)
            if total > 0:
                for h in hypotheses:
                    h.confidence = round(h.confidence / total, 3)

        return hypotheses

    def _eval_h1_wrong_page(self, inp: DiagnosticInput) -> HypothesisEvaluation:
        """H1: Wrong page mindstate — mechanism had low resonance with this page."""
        conf = 0.2  # Base prior
        evidence_for = []
        evidence_against = []

        # Check resonance between mechanism ideal and actual page
        resonance = self._get_mechanism_page_resonance(
            inp.deployed_mechanism, inp.deployed_page_cluster,
        )
        if resonance < 0.6:
            conf += 0.4
            evidence_for.append(
                f"Low resonance ({resonance:.2f}) between {inp.deployed_mechanism} "
                f"and {inp.deployed_page_cluster} cluster"
            )
        elif resonance > 0.9:
            conf -= 0.1
            evidence_against.append(
                f"High resonance ({resonance:.2f}) — page was well-suited"
            )

        # Check user's page_mechanism_posteriors for this cluster
        if inp.user_profile and hasattr(inp.user_profile, 'page_mechanism_posteriors'):
            key = f"{inp.deployed_mechanism}:{inp.deployed_page_cluster}"
            p = inp.user_profile.page_mechanism_posteriors.get(key)
            if p and p.sample_count >= 2:
                mean = p.alpha / (p.alpha + p.beta)
                if mean < 0.3:
                    conf += 0.2
                    evidence_for.append(
                        f"User history: {inp.deployed_mechanism} on "
                        f"{inp.deployed_page_cluster} has low mean ({mean:.2f})"
                    )
                elif mean > 0.6:
                    conf -= 0.1
                    evidence_against.append(
                        f"User history shows this combo works (mean={mean:.2f})"
                    )

        return HypothesisEvaluation(
            hypothesis=NonConversionHypothesis.WRONG_PAGE_MINDSTATE,
            confidence=max(0.0, conf),
            evidence_for=evidence_for,
            evidence_against=evidence_against,
        )

    def _eval_h2_wrong_mechanism(self, inp: DiagnosticInput) -> HypothesisEvaluation:
        """H2: Wrong mechanism for this person's personality/state."""
        conf = 0.2
        evidence_for = []
        evidence_against = []

        # Check personality susceptibility
        cialdini = MECHANISM_TO_CIALDINI.get(inp.deployed_mechanism, "")
        susceptibility = self._get_personality_susceptibility(cialdini, inp)
        if susceptibility < -0.1:
            conf += 0.3
            evidence_for.append(
                f"Personality resists {cialdini} (susceptibility={susceptibility:.2f})"
            )
        elif susceptibility > 0.1:
            evidence_against.append(
                f"Personality susceptible to {cialdini} ({susceptibility:.2f})"
            )

        # Check user-level posterior for this mechanism
        if inp.user_profile and hasattr(inp.user_profile, 'mechanism_posteriors'):
            p = inp.user_profile.mechanism_posteriors.get(inp.deployed_mechanism)
            if p and p.sample_count >= 2:
                mean = p.alpha / (p.alpha + p.beta)
                if mean < 0.3:
                    conf += 0.25
                    evidence_for.append(
                        f"User posterior for {inp.deployed_mechanism} is low (mean={mean:.2f})"
                    )

        # Check if mechanism is in barrier candidates
        barrier = inp.current_barrier or ""
        candidates = BARRIER_MECHANISM_CANDIDATES.get(barrier, [])
        if inp.deployed_mechanism not in candidates and candidates:
            conf += 0.2
            evidence_for.append(
                f"{inp.deployed_mechanism} is not a candidate for barrier {barrier}"
            )

        return HypothesisEvaluation(
            hypothesis=NonConversionHypothesis.WRONG_MECHANISM,
            confidence=max(0.0, conf),
            evidence_for=evidence_for,
            evidence_against=evidence_against,
        )

    def _eval_h3_wrong_stage(self, inp: DiagnosticInput) -> HypothesisEvaluation:
        """H3: Stage mismatch — mechanism appropriate for a different stage."""
        conf = 0.15
        evidence_for = []
        evidence_against = []

        stage = inp.current_stage
        fit = STAGE_MECHANISM_FIT.get(stage, {})
        if inp.deployed_mechanism in fit.get("mismatched", set()):
            conf += 0.5
            evidence_for.append(
                f"{inp.deployed_mechanism} is mismatched for stage {stage}"
            )
        elif inp.deployed_mechanism in fit.get("matched", set()):
            conf -= 0.1
            evidence_against.append(
                f"{inp.deployed_mechanism} is stage-appropriate for {stage}"
            )

        # Check if stage recently advanced (mechanism was for OLD stage)
        if inp.stage_advanced and inp.touch_position > 1:
            conf += 0.15
            evidence_for.append("Stage advanced — prior mechanism was for old stage")

        return HypothesisEvaluation(
            hypothesis=NonConversionHypothesis.WRONG_STAGE_MATCH,
            confidence=max(0.0, conf),
            evidence_for=evidence_for,
            evidence_against=evidence_against,
        )

    def _eval_h4_pkm_reactance(self, inp: DiagnosticInput) -> HypothesisEvaluation:
        """H4: PKM/reactance suppression — user detected tactic or felt pressured."""
        conf = 0.1
        evidence_for = []
        evidence_against = []

        if inp.reactance_level > 0.7:
            conf += 0.3
            evidence_for.append(
                f"High reactance ({inp.reactance_level:.2f}) — user feels pressured"
            )

        if inp.pkm_phase >= 2 and inp.deployed_mechanism in PKM_PENALIZED_MECHANISMS:
            conf += 0.35
            evidence_for.append(
                f"PKM phase {inp.pkm_phase} + 'salesy' mechanism "
                f"({inp.deployed_mechanism}) — user likely detected tactic"
            )

        if inp.reactance_level < 0.3 and inp.pkm_phase == 1:
            conf -= 0.1
            evidence_against.append("Low reactance, early PKM — tactic detection unlikely")

        # Consecutive ignores after salesy mechanism
        recent_ignores = sum(
            1 for t in (inp.touch_history or [])[-3:]
            if not t.get("engagement_type")
        )
        if recent_ignores >= 2 and inp.pkm_phase >= 2:
            conf += 0.15
            evidence_for.append(
                f"{recent_ignores} consecutive ignores in PKM phase {inp.pkm_phase}"
            )

        return HypothesisEvaluation(
            hypothesis=NonConversionHypothesis.PKM_REACTANCE_SUPPRESSION,
            confidence=max(0.0, conf),
            evidence_for=evidence_for,
            evidence_against=evidence_against,
        )

    def _eval_h5_fatigue(self, inp: DiagnosticInput) -> HypothesisEvaluation:
        """H5: Ad fatigue / banner blindness — repetition or clutter."""
        conf = 0.1
        evidence_for = []
        evidence_against = []

        # Total touch count
        if inp.touch_position > 6:
            conf += 0.25
            evidence_for.append(f"Touch {inp.touch_position} — approaching fatigue threshold")

        # Same mechanism deployed consecutively
        if len(inp.mechanisms_already_tried) >= 2:
            last_two = inp.mechanisms_already_tried[-2:]
            if last_two[0] == last_two[1] == inp.deployed_mechanism:
                conf += 0.3
                evidence_for.append(
                    f"Same mechanism ({inp.deployed_mechanism}) deployed 3x consecutively"
                )

        # Touches since last engagement
        touches_since_engagement = 0
        for t in reversed(inp.touch_history or []):
            if t.get("engagement_type"):
                break
            touches_since_engagement += 1
        if touches_since_engagement >= 3:
            conf += 0.2
            evidence_for.append(
                f"{touches_since_engagement} touches since last engagement"
            )

        if inp.touch_position <= 3:
            conf -= 0.1
            evidence_against.append("Early in sequence — fatigue unlikely")

        return HypothesisEvaluation(
            hypothesis=NonConversionHypothesis.AD_FATIGUE,
            confidence=max(0.0, conf),
            evidence_for=evidence_for,
            evidence_against=evidence_against,
        )

    # ─── PHASE B: CANDIDATE GENERATION ──────────────────────────

    def _generate_candidates(
        self,
        inp: DiagnosticInput,
        primary_hyp: NonConversionHypothesis,
        engagement: EngagementOutcome,
    ) -> List[Tuple[str, str, float]]:
        """Generate (mechanism, page_cluster, base_score) candidates.

        Strategy depends on primary hypothesis:
        H1 → same mechanism, different page (polar opposite + adjacent)
        H2 → different mechanism, mechanism's ideal page
        H3 → stage-appropriate mechanism, keep page
        H4 → autonomy-safe only, low-pressure page
        H5 → novelty/disruption, different everything
        """
        candidates = []
        barrier = inp.current_barrier or "trust_deficit"
        barrier_mechs = BARRIER_MECHANISM_CANDIDATES.get(barrier, ["evidence_proof"])

        if primary_hyp == NonConversionHypothesis.WRONG_PAGE_MINDSTATE:
            # Same mechanism, explore page space (polar opposite first)
            mech = inp.deployed_mechanism
            polar = POLAR_OPPOSITES.get(inp.deployed_page_cluster, "analytical")
            for cluster in PAGE_CLUSTERS:
                dist = self._cluster_distance(inp.deployed_page_cluster, cluster)
                score = 0.3 + dist * 0.5  # Higher distance = higher base score
                if cluster == polar:
                    score += 0.2
                candidates.append((mech, cluster, score))

        elif primary_hyp == NonConversionHypothesis.WRONG_MECHANISM:
            # Different mechanism, use each mechanism's ideal page
            for mech in barrier_mechs:
                if mech == inp.deployed_mechanism:
                    continue
                ideal_cluster = self._get_mechanism_ideal_cluster(mech)
                for cluster in PAGE_CLUSTERS:
                    coherence = self._get_mechanism_page_resonance(mech, cluster)
                    score = coherence * 0.8
                    if cluster == ideal_cluster:
                        score += 0.2
                    candidates.append((mech, cluster, score))

        elif primary_hyp == NonConversionHypothesis.WRONG_STAGE_MATCH:
            # Stage-appropriate mechanisms, keep successful page clusters
            stage = inp.current_stage
            matched = STAGE_MECHANISM_FIT.get(stage, {}).get("matched", set())
            for mech in matched:
                if mech in (inp.mechanisms_blacklisted or []):
                    continue
                for cluster in PAGE_CLUSTERS:
                    coherence = self._get_mechanism_page_resonance(mech, cluster)
                    score = coherence * 0.7
                    if cluster == inp.deployed_page_cluster:
                        score += 0.15  # Slight preference for same page
                    candidates.append((mech, cluster, score))

        elif primary_hyp == NonConversionHypothesis.PKM_REACTANCE_SUPPRESSION:
            # Autonomy-safe mechanisms, low-pressure pages
            for mech in AUTONOMY_SAFE_MECHANISMS:
                for cluster in PAGE_CLUSTERS:
                    coherence = self._get_mechanism_page_resonance(mech, cluster)
                    score = coherence * 0.6
                    # Prefer non-transactional (less salesy feel)
                    if cluster in ("emotional", "aspirational"):
                        score += 0.2
                    candidates.append((mech, cluster, score))

        elif primary_hyp == NonConversionHypothesis.AD_FATIGUE:
            # Novelty — different mechanism AND different page
            for mech in barrier_mechs:
                if mech in (inp.mechanisms_already_tried or [])[-2:]:
                    continue
                polar = POLAR_OPPOSITES.get(inp.deployed_page_cluster, "analytical")
                for cluster in PAGE_CLUSTERS:
                    dist = self._cluster_distance(inp.deployed_page_cluster, cluster)
                    score = dist * 0.5
                    if cluster == polar:
                        score += 0.3
                    if mech not in (inp.mechanisms_already_tried or []):
                        score += 0.2
                    candidates.append((mech, cluster, score))

        # Fallback: if no candidates generated, add all barrier candidates on all clusters
        if not candidates:
            for mech in barrier_mechs:
                for cluster in PAGE_CLUSTERS:
                    candidates.append((mech, cluster, 0.3))

        return candidates

    # ─── PHASE B: CONSTRAINT FILTERING ──────────────────────────

    def _apply_constraints(
        self,
        candidates: List[Tuple[str, str, float]],
        inp: DiagnosticInput,
    ) -> Tuple[List[Tuple[str, str, float]], List[ConstraintViolation]]:
        """Apply constraint graph. Returns (surviving, violations)."""
        surviving = []
        violations = []

        blacklist = set(inp.mechanisms_blacklisted or [])
        stage = inp.current_stage
        stage_mismatched = STAGE_MECHANISM_FIT.get(stage, {}).get("mismatched", set())

        for mech, cluster, score in candidates:
            # 1. Blacklist (hard eliminate)
            if mech in blacklist:
                violations.append(ConstraintViolation(
                    mechanism=mech, page_cluster=cluster,
                    constraint_type="blacklisted",
                    reason=f"{mech} permanently blacklisted for this user",
                ))
                continue

            # 2. Reactance limit (hard eliminate)
            if inp.reactance_level > 0.7 and mech not in AUTONOMY_SAFE_MECHANISMS:
                violations.append(ConstraintViolation(
                    mechanism=mech, page_cluster=cluster,
                    constraint_type="reactance_limit",
                    reason=f"Reactance {inp.reactance_level:.2f} > 0.7, {mech} not autonomy-safe",
                ))
                continue

            # 3. Frustrated pair (hard eliminate)
            fp_violation = self._check_frustrated_pair(mech, inp)
            if fp_violation:
                fp_violation.page_cluster = cluster
                violations.append(fp_violation)
                continue

            # 4. Stage mismatch (hard eliminate)
            if mech in stage_mismatched:
                violations.append(ConstraintViolation(
                    mechanism=mech, page_cluster=cluster,
                    constraint_type="stage_mismatch",
                    reason=f"{mech} mismatched for stage {stage}",
                ))
                continue

            # 5. Mechanism×page coherence (hard eliminate if very low)
            coherence = self._get_mechanism_page_resonance(mech, cluster)
            if coherence < 0.3:
                violations.append(ConstraintViolation(
                    mechanism=mech, page_cluster=cluster,
                    constraint_type="coherence_failure",
                    reason=f"Resonance {coherence:.2f} too low for {mech} on {cluster}",
                ))
                continue

            # 6. PKM penalty (soft — reduce score, don't eliminate)
            adjusted_score = score
            if inp.pkm_phase >= 2 and mech in PKM_PENALIZED_MECHANISMS:
                adjusted_score *= 0.3

            # 7. Repetition penalty (soft)
            if mech == inp.deployed_mechanism:
                adjusted_score *= 0.5

            surviving.append((mech, cluster, adjusted_score))

        return surviving, violations

    def _check_frustrated_pair(
        self,
        mechanism: str,
        inp: DiagnosticInput,
    ) -> Optional[ConstraintViolation]:
        """Check if mechanism targets a dimension frustrated with current target."""
        mech_dim = MECHANISM_TARGET_DIMENSION.get(mechanism, "")
        if not mech_dim:
            return None

        # What dimension is the sequence currently working on?
        current_dim = ""
        if inp.current_barrier:
            for dim, barrier in DIMENSION_BARRIER_MAP.items():
                if barrier == inp.current_barrier:
                    current_dim = dim
                    break

        if not current_dim or current_dim == mech_dim:
            return None

        # Check if these dimensions are frustrated
        frustrated = self._frustrated_index.get(current_dim, [])
        for pair_dim, corr in frustrated:
            if pair_dim == mech_dim:
                return ConstraintViolation(
                    mechanism=mechanism,
                    page_cluster="",
                    constraint_type="frustrated_pair",
                    reason=(
                        f"{mechanism} targets {mech_dim} which is frustrated with "
                        f"current target {current_dim} (r={corr:.3f})"
                    ),
                    severity=abs(corr),
                )

        return None

    # ─── PHASE B: SCORING ───────────────────────────────────────

    def _score_candidates(
        self,
        candidates: List[Tuple[str, str, float]],
        inp: DiagnosticInput,
        hypothesis_confidences: Dict[str, float],
    ) -> List[Tuple[str, str, float]]:
        """Score candidates by 0.6×effectiveness + 0.4×diagnostic_value."""
        scored = []
        for mech, cluster, base_score in candidates:
            effectiveness = self._estimate_effectiveness(mech, cluster, inp)
            diag_value = self._estimate_diagnostic_value(mech, cluster, inp, hypothesis_confidences)
            combined = 0.6 * effectiveness + 0.4 * diag_value
            # Incorporate base_score from candidate generation
            combined = combined * 0.7 + base_score * 0.3
            scored.append((mech, cluster, combined))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored

    def _estimate_effectiveness(
        self, mech: str, cluster: str, inp: DiagnosticInput,
    ) -> float:
        """Estimate expected effectiveness of this (mechanism, page_cluster) pair."""
        # User-level posterior (strongest signal if available)
        if inp.user_profile and hasattr(inp.user_profile, 'page_mechanism_posteriors'):
            key = f"{mech}:{cluster}"
            p = inp.user_profile.page_mechanism_posteriors.get(key)
            if p and p.sample_count >= 2:
                return p.alpha / (p.alpha + p.beta)

        # User-level mechanism posterior (without page)
        if inp.user_profile and hasattr(inp.user_profile, 'mechanism_posteriors'):
            p = inp.user_profile.mechanism_posteriors.get(mech)
            if p and p.sample_count >= 2:
                return p.alpha / (p.alpha + p.beta)

        # Population prior: position in BARRIER_MECHANISM_CANDIDATES ordering
        barrier = inp.current_barrier or "trust_deficit"
        candidates = BARRIER_MECHANISM_CANDIDATES.get(barrier, [])
        if mech in candidates:
            idx = candidates.index(mech)
            return max(0.3, 0.7 - idx * 0.1)  # First candidate = 0.7, decreasing

        return 0.3  # Unknown mechanism for this barrier

    def _estimate_diagnostic_value(
        self,
        mech: str,
        cluster: str,
        inp: DiagnosticInput,
        hypothesis_confidences: Dict[str, float],
    ) -> float:
        """Estimate information gain from observing the outcome of this move.

        High diagnostic value = the outcome would discriminate between hypotheses.
        A move where all hypotheses predict the same outcome has zero value.
        """
        # Posterior uncertainty: prefer moves we know LEAST about
        uncertainty = 1.0
        if inp.user_profile and hasattr(inp.user_profile, 'page_mechanism_posteriors'):
            key = f"{mech}:{cluster}"
            p = inp.user_profile.page_mechanism_posteriors.get(key)
            if p and p.sample_count >= 2:
                mean = p.alpha / (p.alpha + p.beta)
                # Variance of Beta distribution
                var = (p.alpha * p.beta) / ((p.alpha + p.beta) ** 2 * (p.alpha + p.beta + 1))
                uncertainty = min(1.0, var * 20)  # Scale to [0, 1]
            elif p and p.sample_count == 1:
                uncertainty = 0.8
            else:
                uncertainty = 1.0  # Never tried = maximum uncertainty

        # Hypothesis discrimination: does this move test a specific hypothesis?
        discrimination = 0.0
        max_conf_hyp = max(hypothesis_confidences.values()) if hypothesis_confidences else 0.0

        # If primary hypothesis is "wrong page" and this move changes page: discriminating
        if (hypothesis_confidences.get("wrong_page_mindstate", 0) > 0.3
                and cluster != inp.deployed_page_cluster):
            discrimination += 0.4

        # If primary is "wrong mechanism" and this move changes mechanism: discriminating
        if (hypothesis_confidences.get("wrong_mechanism", 0) > 0.3
                and mech != inp.deployed_mechanism):
            discrimination += 0.4

        # Changing BOTH mechanism and page is less discriminating (can't isolate)
        if (mech != inp.deployed_mechanism and cluster != inp.deployed_page_cluster):
            discrimination *= 0.7  # Penalize: harder to attribute

        return uncertainty * 0.5 + discrimination * 0.5

    # ─── PHASE C: FRUSTRATED PAIR PLANNING ──────────────────────

    def _check_frustrated_pairs(
        self,
        inp: DiagnosticInput,
        selected_mechanism: str,
    ) -> Optional[FrustratedPairPlan]:
        """If we need to address multiple barriers with frustrated dimensions,
        plan the sequential resolution."""
        # Identify ALL barriers from alignment gaps
        barriers_present = set()
        if inp.bilateral_edge:
            for dim, barrier in DIMENSION_BARRIER_MAP.items():
                val = inp.bilateral_edge.get(dim, 0.5)
                # Simplified threshold check
                if val < 0.35 or (dim in {"negativity_bias_match", "spending_pain_match",
                                          "processing_route_match", "composite_alignment"}
                                  and val > 0.5):
                    barriers_present.add(barrier)

        if len(barriers_present) < 2:
            return None

        # Check if any pair of barriers involves frustrated dimensions
        selected_dim = MECHANISM_TARGET_DIMENSION.get(selected_mechanism, "")
        deferred = []
        worst_corr = 0.0

        for dim, barrier in DIMENSION_BARRIER_MAP.items():
            if barrier not in barriers_present or barrier == inp.current_barrier:
                continue
            frustrated = self._frustrated_index.get(selected_dim, [])
            for pair_dim, corr in frustrated:
                if pair_dim == dim:
                    deferred.append(barrier)
                    worst_corr = min(worst_corr, corr)

        if not deferred:
            return None

        return FrustratedPairPlan(
            current_phase=1,
            total_phases=2,
            current_target_dimension=selected_dim,
            deferred_dimensions=[MECHANISM_TARGET_DIMENSION.get(d, d) for d in deferred],
            deferred_barriers=deferred,
            correlation=worst_corr,
            rationale=(
                f"Addressing {inp.current_barrier} first (dimension: {selected_dim}). "
                f"Deferring {', '.join(deferred)} because dimensions are anti-correlated "
                f"(r={worst_corr:.3f}). Sequential resolution required."
            ),
        )

    # ─── PHASE D: SIGNALS ──────────────────────────────────────

    def _generate_signals(
        self,
        inp: DiagnosticInput,
        engagement: EngagementOutcome,
        primary_hyp: NonConversionHypothesis,
        next_mech: str,
        next_cluster: str,
    ) -> Dict[str, Any]:
        signals: Dict[str, Any] = {}

        signals["stage_progression"] = inp.stage_advanced

        if engagement == EngagementOutcome.ACTIVE_REJECTION:
            signals["mechanism_blacklist"] = inp.deployed_mechanism
            signals["cooldown_required"] = True
            signals["cooldown_hours"] = 336 if inp.reactance_level > 0.8 else 72

        if inp.reactance_level > 0.7:
            signals["reactance_alert"] = inp.reactance_level

        # If hypothesis uncertainty is high (max < 0.4), recommend exploration
        if primary_hyp and all(
            v < 0.4 for v in [0.5]  # placeholder — use actual confidences
        ):
            signals["exploration_recommended"] = True

        # Page expansion signal on conversion (handled in _handle_conversion)
        if engagement == EngagementOutcome.CONVERSION:
            signals["crawl_expansion_signal"] = {
                "target_page_cluster": inp.deployed_page_cluster,
                "target_page_mindstate": inp.page_mindstate,
                "mechanism": inp.deployed_mechanism,
            }

        return signals

    # ─── SHORT-CIRCUIT HANDLERS ─────────────────────────────────

    def _handle_conversion(
        self, inp: DiagnosticInput, steps: List[ReasoningStep], t0: float,
    ) -> DiagnosticAssessment:
        """Conversion: the triple is proven. Emit expansion signal."""
        elapsed = (time.perf_counter() - t0) * 1000
        steps.append(ReasoningStep(
            step_number=len(steps) + 1,
            step_type="conversion_handling",
            description=(
                f"CONVERSION on {inp.deployed_mechanism} x {inp.deployed_page_cluster}. "
                f"Triple proven. Emitting crawl expansion signal."
            ),
            outputs={
                "proven_triple": {
                    "mechanism": inp.deployed_mechanism,
                    "page_cluster": inp.deployed_page_cluster,
                    "archetype": inp.archetype_id,
                },
            },
        ))

        return DiagnosticAssessment(
            user_id=inp.user_id,
            brand_id=inp.brand_id,
            observed_outcome=EngagementOutcome.CONVERSION,
            outcome_interpretation=(
                f"Conversion achieved with {inp.deployed_mechanism} on "
                f"{inp.deployed_page_cluster} page. The (person x page x mechanism) "
                f"triple is proven. Crawl for more pages with similar mindstate dimensions."
            ),
            primary_hypothesis=None,
            next_mechanism="",
            next_page_cluster="",
            next_scaffold_level="",
            move_confidence=1.0,
            reasoning_trace=steps,
            total_reasoning_ms=round(elapsed, 2),
            signals_for_upstream={
                "stage_progression": True,
                "crawl_expansion_signal": {
                    "target_page_cluster": inp.deployed_page_cluster,
                    "target_page_mindstate": inp.page_mindstate,
                    "mechanism": inp.deployed_mechanism,
                },
                "sequence_complete": True,
            },
        )

    def _handle_active_rejection(
        self, inp: DiagnosticInput, steps: List[ReasoningStep], t0: float,
    ) -> DiagnosticAssessment:
        """Active rejection: reactance triggered. Mandatory cooldown."""
        elapsed = (time.perf_counter() - t0) * 1000
        cooldown_hours = 336 if inp.reactance_level > 0.8 else 72

        steps.append(ReasoningStep(
            step_number=len(steps) + 1,
            step_type="rejection_handling",
            description=(
                f"ACTIVE REJECTION detected. {inp.deployed_mechanism} permanently "
                f"blacklisted for this user. Mandatory {cooldown_hours}h cooldown. "
                f"Next touch MUST use autonomy_restoration."
            ),
            outputs={
                "blacklisted_mechanism": inp.deployed_mechanism,
                "cooldown_hours": cooldown_hours,
            },
        ))

        return DiagnosticAssessment(
            user_id=inp.user_id,
            brand_id=inp.brand_id,
            observed_outcome=EngagementOutcome.ACTIVE_REJECTION,
            outcome_interpretation=(
                f"User actively rejected {inp.deployed_mechanism}. Reactance at "
                f"{inp.reactance_level:.2f}. Mechanism permanently blacklisted. "
                f"Mandatory {cooldown_hours}h cooldown. "
                f"Next touch must use autonomy_restoration."
            ),
            primary_hypothesis=NonConversionHypothesis.PKM_REACTANCE_SUPPRESSION,
            hypothesis_confidences={"pkm_reactance": 0.9},
            next_mechanism="autonomy_restoration",
            next_page_cluster=POLAR_OPPOSITES.get(inp.deployed_page_cluster, "emotional"),
            next_scaffold_level="recruitment",
            move_confidence=0.7,
            reasoning_trace=steps,
            total_reasoning_ms=round(elapsed, 2),
            constraint_violations=[ConstraintViolation(
                mechanism=inp.deployed_mechanism,
                page_cluster=inp.deployed_page_cluster,
                constraint_type="blacklisted",
                reason="Active rejection — permanently blacklisted for this user",
            )],
            signals_for_upstream={
                "mechanism_blacklist": inp.deployed_mechanism,
                "cooldown_required": True,
                "cooldown_hours": cooldown_hours,
                "reactance_alert": inp.reactance_level,
            },
        )

    # ─── UTILITY METHODS ────────────────────────────────────────

    def _build_frustrated_pairs_index(self) -> Dict[str, List[Tuple[str, float]]]:
        """Pre-index frustrated pairs for O(1) lookup by dimension."""
        index: Dict[str, List[Tuple[str, float]]] = {}
        for dim_a, dim_b, corr in FRUSTRATED_DIMENSION_PAIRS:
            index.setdefault(dim_a, []).append((dim_b, corr))
            index.setdefault(dim_b, []).append((dim_a, corr))
        return index

    def _get_mechanism_page_resonance(self, mechanism: str, page_cluster: str) -> float:
        """Estimate resonance between mechanism and page cluster.

        Uses the mechanism ideal vectors from cold_start.py.
        Higher = better fit. Range [0, 1].
        """
        # Known good/bad combinations from creative_adapter mechanism x cluster overrides
        KNOWN_RESONANCE = {
            ("evidence_proof", "analytical"): 0.95,
            ("evidence_proof", "emotional"): 0.4,
            ("evidence_proof", "social"): 0.7,
            ("evidence_proof", "transactional"): 0.8,
            ("evidence_proof", "aspirational"): 0.5,
            ("narrative_transportation", "analytical"): 0.6,
            ("narrative_transportation", "emotional"): 0.95,
            ("narrative_transportation", "social"): 0.7,
            ("narrative_transportation", "transactional"): 0.3,
            ("narrative_transportation", "aspirational"): 0.8,
            ("social_proof_matched", "analytical"): 0.7,
            ("social_proof_matched", "emotional"): 0.6,
            ("social_proof_matched", "social"): 0.95,
            ("social_proof_matched", "transactional"): 0.5,
            ("social_proof_matched", "aspirational"): 0.6,
            ("loss_framing", "analytical"): 0.5,
            ("loss_framing", "emotional"): 0.4,
            ("loss_framing", "social"): 0.4,
            ("loss_framing", "transactional"): 0.9,
            ("loss_framing", "aspirational"): 0.2,
            ("autonomy_restoration", "analytical"): 0.6,
            ("autonomy_restoration", "emotional"): 0.8,
            ("autonomy_restoration", "social"): 0.5,
            ("autonomy_restoration", "transactional"): 0.3,
            ("autonomy_restoration", "aspirational"): 0.7,
            ("claude_argument", "analytical"): 0.95,
            ("claude_argument", "emotional"): 0.5,
            ("claude_argument", "social"): 0.6,
            ("claude_argument", "transactional"): 0.7,
            ("claude_argument", "aspirational"): 0.5,
            ("vivid_scenario", "analytical"): 0.3,
            ("vivid_scenario", "emotional"): 0.95,
            ("vivid_scenario", "social"): 0.6,
            ("vivid_scenario", "transactional"): 0.3,
            ("vivid_scenario", "aspirational"): 0.8,
            ("implementation_intention", "analytical"): 0.7,
            ("implementation_intention", "emotional"): 0.3,
            ("implementation_intention", "social"): 0.4,
            ("implementation_intention", "transactional"): 0.9,
            ("implementation_intention", "aspirational"): 0.3,
            ("price_anchor", "analytical"): 0.8,
            ("price_anchor", "emotional"): 0.2,
            ("price_anchor", "social"): 0.4,
            ("price_anchor", "transactional"): 0.95,
            ("price_anchor", "aspirational"): 0.2,
            ("micro_commitment", "analytical"): 0.5,
            ("micro_commitment", "emotional"): 0.5,
            ("micro_commitment", "social"): 0.7,
            ("micro_commitment", "transactional"): 0.8,
            ("micro_commitment", "aspirational"): 0.4,
            ("ownership_reactivation", "analytical"): 0.5,
            ("ownership_reactivation", "emotional"): 0.8,
            ("ownership_reactivation", "social"): 0.5,
            ("ownership_reactivation", "transactional"): 0.6,
            ("ownership_reactivation", "aspirational"): 0.7,
            ("anxiety_resolution", "analytical"): 0.7,
            ("anxiety_resolution", "emotional"): 0.6,
            ("anxiety_resolution", "social"): 0.7,
            ("anxiety_resolution", "transactional"): 0.4,
            ("anxiety_resolution", "aspirational"): 0.6,
            ("dissonance_activation", "analytical"): 0.5,
            ("dissonance_activation", "emotional"): 0.6,
            ("dissonance_activation", "social"): 0.7,
            ("dissonance_activation", "transactional"): 0.3,
            ("dissonance_activation", "aspirational"): 0.8,
            ("construal_shift", "analytical"): 0.7,
            ("construal_shift", "emotional"): 0.5,
            ("construal_shift", "social"): 0.4,
            ("construal_shift", "transactional"): 0.6,
            ("construal_shift", "aspirational"): 0.5,
            ("frustration_control", "analytical"): 0.6,
            ("frustration_control", "emotional"): 0.5,
            ("frustration_control", "social"): 0.4,
            ("frustration_control", "transactional"): 0.7,
            ("frustration_control", "aspirational"): 0.3,
            ("novelty_disruption", "analytical"): 0.4,
            ("novelty_disruption", "emotional"): 0.5,
            ("novelty_disruption", "social"): 0.5,
            ("novelty_disruption", "transactional"): 0.6,
            ("novelty_disruption", "aspirational"): 0.7,
        }
        return KNOWN_RESONANCE.get((mechanism, page_cluster), 0.5)

    def _get_mechanism_ideal_cluster(self, mechanism: str) -> str:
        """Get the page cluster with highest resonance for this mechanism."""
        best_cluster = "analytical"
        best_score = 0.0
        for cluster in PAGE_CLUSTERS:
            score = self._get_mechanism_page_resonance(mechanism, cluster)
            if score > best_score:
                best_score = score
                best_cluster = cluster
        return best_cluster

    def _cluster_distance(self, a: str, b: str) -> float:
        """Psychological distance between two page clusters. [0, 1]."""
        if a == b:
            return 0.0
        key = (min(a, b), max(a, b))
        return CLUSTER_DISTANCE.get(key, 0.5)

    def _get_personality_susceptibility(self, cialdini: str, inp: DiagnosticInput) -> float:
        """Compute personality susceptibility for a Cialdini principle."""
        if not cialdini:
            return 0.0
        total = 0.0
        count = 0
        for trait, mechs in PERSONALITY_MECHANISM_SUSCEPTIBILITY.items():
            direction = mechs.get(cialdini, 0)
            if direction != 0:
                total += direction * 0.3  # Assume moderate trait intensity
                count += 1
        return total / max(count, 1)

    def _determine_scaffold(self, stage: str, pkm_phase: int) -> str:
        """Determine scaffold level from stage and PKM phase."""
        return SCAFFOLD_MAP.get((stage, pkm_phase), "direction_maintenance")

    def _interpret_outcome(
        self,
        engagement: EngagementOutcome,
        primary_hyp: NonConversionHypothesis,
        inp: DiagnosticInput,
    ) -> str:
        """Human-readable interpretation of the outcome."""
        interp = {
            NonConversionHypothesis.WRONG_PAGE_MINDSTATE: (
                f"{inp.deployed_mechanism} had low resonance with {inp.deployed_page_cluster} "
                f"page. The mechanism direction may be correct but the page context "
                f"didn't amplify it. Try polar opposite page cluster."
            ),
            NonConversionHypothesis.WRONG_MECHANISM: (
                f"{inp.deployed_mechanism} is not effective for this user's personality "
                f"and current barrier ({inp.current_barrier}). Switch to a different "
                f"mechanism from the barrier candidate set."
            ),
            NonConversionHypothesis.WRONG_STAGE_MATCH: (
                f"{inp.deployed_mechanism} is not appropriate for {inp.current_stage} "
                f"stage. The user's stage may have changed since last touch. "
                f"Switch to stage-matched mechanism."
            ),
            NonConversionHypothesis.PKM_REACTANCE_SUPPRESSION: (
                f"User's persuasion knowledge (phase {inp.pkm_phase}) and/or "
                f"reactance ({inp.reactance_level:.2f}) suppressed response to "
                f"{inp.deployed_mechanism}. Need autonomy-safe, non-salesy approach."
            ),
            NonConversionHypothesis.AD_FATIGUE: (
                f"After {inp.touch_position} touches, ad fatigue likely. "
                f"Need novel approach — different mechanism AND different page context."
            ),
        }
        return interp.get(primary_hyp, f"Non-conversion on touch {inp.touch_position}")

    def _explain_diagnostic_value(
        self,
        mech: str,
        cluster: str,
        primary_hyp: NonConversionHypothesis,
        inp: DiagnosticInput,
    ) -> str:
        """What we expect to learn from the recommended move."""
        if primary_hyp == NonConversionHypothesis.WRONG_PAGE_MINDSTATE:
            return (
                f"Testing {mech} on {cluster} (vs {inp.deployed_page_cluster}). "
                f"If this converts: page was the problem. If it fails: mechanism "
                f"may be wrong for this user."
            )
        elif primary_hyp == NonConversionHypothesis.WRONG_MECHANISM:
            return (
                f"Testing new mechanism {mech} (vs {inp.deployed_mechanism}). "
                f"If this works: confirms mechanism was wrong. If it fails: "
                f"barrier diagnosis may need revision."
            )
        elif primary_hyp == NonConversionHypothesis.WRONG_STAGE_MATCH:
            return (
                f"Testing stage-matched {mech} for {inp.current_stage}. "
                f"If this works: confirms stage mismatch was the issue."
            )
        elif primary_hyp == NonConversionHypothesis.PKM_REACTANCE_SUPPRESSION:
            return (
                f"Testing autonomy-safe {mech} to reduce reactance. "
                f"If engagement returns: confirms PKM/reactance was blocking."
            )
        else:
            return (
                f"Testing novel approach {mech} on {cluster} to break fatigue. "
                f"If engagement returns: confirms fatigue, not fundamental barrier."
            )


# =============================================================================
# SINGLETON
# =============================================================================

_diagnostic_reasoner: Optional[DiagnosticReasoner] = None


def get_diagnostic_reasoner(barrier_engine=None) -> DiagnosticReasoner:
    """Get or create the singleton DiagnosticReasoner."""
    global _diagnostic_reasoner
    if _diagnostic_reasoner is None:
        _diagnostic_reasoner = DiagnosticReasoner(
            barrier_diagnostic_engine=barrier_engine,
        )
    return _diagnostic_reasoner
