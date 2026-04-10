# =============================================================================
# Inferential Hypothesis Engine
# Location: adam/intelligence/inferential_hypothesis_engine.py
# =============================================================================

"""
Generates, tests, validates, and transfers INFERENTIAL HYPOTHESES.

This is NOT A/B testing. This is theory-guided causal inference.

A/B test: "Does variant A beat variant B?"
This system: "WHY did variant A beat B? BECAUSE cognitive_load_tolerance was
high AND the causal chain low_uncertainty_tolerance→need_for_closure→authority
was active. THEREFORE authority should also beat social_proof in ANY context
where clt > 0.7, because the same causal chain applies."

The power: one conversion teaches the system about thousands of contexts.
A/B testing needs data in EACH context. Inferential transfer needs data in
ONE context and theory to propagate.

Hypothesis lifecycle:
1. GENERATED — From a CausalRecipe (conversion decomposition)
2. THEORY_CHECKED — Theory graph confirms/denies plausibility
3. EMPIRICALLY_TESTED — Past data checked for statistical support
4. VALIDATED — Both theory + data agree → promote to knowledge
5. TRANSFERRED — Applied to new contexts via zero-shot/few-shot
6. COMPOUNDED — Derived hypotheses generated from validated ones

Cross-disciplinary inspiration:
- PHYSICS: Hypothesis → Prediction → Experiment → Theory revision
- MEDICINE: Case report → Hypothesis → Clinical trial → Practice change
- EVOLUTIONARY BIOLOGY: Mutation → Selection → Propagation
"""

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from adam.intelligence.causal_decomposition import CausalRecipe

logger = logging.getLogger(__name__)


class HypothesisStatus(str, Enum):
    GENERATED = "generated"
    THEORY_CHECKED = "theory_checked"
    EMPIRICALLY_TESTED = "empirically_tested"
    VALIDATED = "validated"
    TRANSFERRED = "transferred"
    INVALIDATED = "invalidated"
    COMPOUNDED = "compounded"


@dataclass
class InferentialHypothesis:
    """A testable, transferable hypothesis derived from causal decomposition.

    Not a correlation ("X predicts Y") but a causal claim
    ("X causes Y because [theory chain]").
    """

    hypothesis_id: str
    status: HypothesisStatus = HypothesisStatus.GENERATED

    # The claim
    conditions: Dict[str, Tuple[str, float]] = field(default_factory=dict)
    # e.g., {"cognitive_load_tolerance": (">", 0.7), "regulatory_fit": ("<", 0.15)}
    predicted_mechanism: str = ""
    predicted_effectiveness: float = 0.0
    vs_alternative: str = ""  # What it beats

    # Theory backing
    causal_chain: Optional[Dict[str, Any]] = None
    theory_plausibility: float = 0.0  # 0-1: how plausible is this per theory?
    theory_explanation: str = ""  # Human-readable causal story

    # Empirical support
    supporting_observations: int = 0
    contradicting_observations: int = 0
    effect_size: float = 0.0  # Cohen's d
    p_value: float = 1.0
    statistical_power: float = 0.0

    # Transferability
    transferability_score: float = 0.0  # 0-1: how context-dependent?
    contexts_tested: int = 0
    contexts_validated: int = 0

    # Derived hypotheses
    derived_from: Optional[str] = None  # Parent hypothesis ID
    derived_hypotheses: List[str] = field(default_factory=list)

    # Falsification
    falsification_criteria: str = ""  # What would disprove this?

    # Source
    source_recipe_id: str = ""
    generated_at: float = field(default_factory=time.time)

    @property
    def confidence(self) -> float:
        """Combined confidence from theory + empirical evidence."""
        if self.supporting_observations == 0:
            return self.theory_plausibility * 0.5
        empirical_conf = min(0.95, 1.0 - self.p_value) if self.p_value < 0.5 else 0.0
        return self.theory_plausibility * 0.4 + empirical_conf * 0.6

    @property
    def is_actionable(self) -> bool:
        """Whether this hypothesis is strong enough to act on.

        Theory-checked hypotheses with strong theory support (>0.6) are
        actionable even without empirical data — this is the cold-start
        transfer principle. The theory graph provides enough confidence
        to justify exploration. Validated hypotheses need lower theory
        support since empirical data provides the confidence.
        """
        if self.status == HypothesisStatus.VALIDATED:
            return True  # Empirically proven — always act
        if self.status == HypothesisStatus.TRANSFERRED:
            return self.confidence > 0.3  # Transferred — moderate bar
        if self.status == HypothesisStatus.THEORY_CHECKED:
            # Theory-backed but untested — act if theory has any support
            # This is the cold-start principle: theory alone justifies exploration
            return self.theory_plausibility >= 0.2
        return False

    def matches_context(self, edge_dimensions: Dict[str, float]) -> bool:
        """Check if a context (page/buyer) matches this hypothesis's conditions."""
        for dim, (op, threshold) in self.conditions.items():
            val = edge_dimensions.get(dim, 0.5)
            if op == ">" and val <= threshold:
                return False
            elif op == "<" and val >= threshold:
                return False
            elif op == "=" and abs(val - threshold) > 0.1:
                return False
        return True


class InferentialHypothesisEngine:
    """Generates, tests, validates, and transfers inferential hypotheses.

    The engine maintains a pool of hypotheses at various lifecycle stages.
    Each conversion feeds new hypotheses. Each impression tests existing ones.
    Validated hypotheses propagate to new contexts. Invalidated ones are
    revised or retired.
    """

    def __init__(self):
        self._hypotheses: Dict[str, InferentialHypothesis] = {}
        self._observation_buffer: List[Dict[str, Any]] = []
        self._hypothesis_counter = 0

    def generate_from_recipe(
        self,
        recipe: CausalRecipe,
    ) -> List[InferentialHypothesis]:
        """Generate hypotheses from a causal decomposition.

        Each recipe produces 1-3 hypotheses:
        1. Direct: "mechanism X works when conditions [A, B, C]"
        2. Contrast: "mechanism X beats mechanism Y when conditions [A, B]"
        3. Derived: If theory supports it, generate transfer hypotheses
        """
        hypotheses = []

        if not recipe.primary_ingredients:
            return hypotheses

        # ── HYPOTHESIS 1: Direct effectiveness claim ──
        self._hypothesis_counter += 1
        h1 = InferentialHypothesis(
            hypothesis_id=f"hyp_{self._hypothesis_counter:06d}",
            conditions=recipe.conditions,
            predicted_mechanism=recipe.mechanism,
            predicted_effectiveness=0.7,  # Initial estimate
            causal_chain=recipe.active_chain,
            theory_plausibility=recipe.chain_confidence,
            theory_explanation=self._explain_chain(recipe),
            source_recipe_id=recipe.decision_id,
            falsification_criteria=(
                f"If {recipe.mechanism} fails to convert in 5+ contexts "
                f"matching conditions {recipe.conditions}, hypothesis is falsified."
            ),
        )

        # Theory check
        h1 = self._check_theory_plausibility(h1)
        hypotheses.append(h1)
        self._hypotheses[h1.hypothesis_id] = h1

        # ── HYPOTHESIS 2: Contrast claim (if surprising) ──
        if recipe.is_surprising:
            self._hypothesis_counter += 1
            h2 = InferentialHypothesis(
                hypothesis_id=f"hyp_{self._hypothesis_counter:06d}",
                conditions=recipe.conditions,
                predicted_mechanism=recipe.mechanism,
                vs_alternative=recipe.surprise_reason.split("but")[0].strip() if "but" in recipe.surprise_reason else "",
                predicted_effectiveness=0.6,
                causal_chain=recipe.active_chain,
                theory_plausibility=recipe.chain_confidence * 0.8,
                theory_explanation=f"Surprising result: {recipe.surprise_reason}. "
                                   f"Theory suggests: {self._explain_chain(recipe)}",
                source_recipe_id=recipe.decision_id,
                falsification_criteria=f"Compare {recipe.mechanism} vs alternative in matching contexts.",
            )
            h2 = self._check_theory_plausibility(h2)
            hypotheses.append(h2)
            self._hypotheses[h2.hypothesis_id] = h2

        # ── HYPOTHESIS 3: Derived transfer hypotheses ──
        derived = self._generate_derived_hypotheses(recipe, h1)
        for d in derived:
            self._hypotheses[d.hypothesis_id] = d
        hypotheses.extend(derived)

        logger.info(
            "Generated %d hypotheses from recipe %s (mechanism=%s, conditions=%d)",
            len(hypotheses), recipe.decision_id, recipe.mechanism,
            len(recipe.conditions),
        )

        return hypotheses

    def test_empirically(
        self,
        hypothesis_id: str,
        observation: Dict[str, Any],
    ) -> Optional[InferentialHypothesis]:
        """Test a hypothesis against a new observation.

        Called when an impression outcome arrives in a context that
        matches the hypothesis conditions.
        """
        hyp = self._hypotheses.get(hypothesis_id)
        if not hyp:
            return None

        edge_dims = observation.get("edge_dimensions", {})
        if not hyp.matches_context(edge_dims):
            return hyp  # Context doesn't match — not a test

        mechanism_used = observation.get("mechanism_sent", "")
        converted = observation.get("converted", False)

        if mechanism_used == hyp.predicted_mechanism:
            if converted:
                hyp.supporting_observations += 1
            else:
                hyp.contradicting_observations += 1

        # Update statistics
        total = hyp.supporting_observations + hyp.contradicting_observations
        if total >= 5:
            # Compute effect size (success rate vs 50% null)
            success_rate = hyp.supporting_observations / total
            hyp.effect_size = 2.0 * (success_rate - 0.5)  # Simple effect measure

            # Compute p-value (binomial test approximation)
            if total > 0:
                z = (success_rate - 0.5) / math.sqrt(0.25 / total)
                # Normal approximation to binomial
                from statistics import NormalDist
                hyp.p_value = 1.0 - NormalDist().cdf(abs(z))

            hyp.statistical_power = min(1.0, total / 50.0)

            # Status transition
            if hyp.p_value < 0.05 and hyp.effect_size > 0.2:
                hyp.status = HypothesisStatus.VALIDATED
                logger.info(
                    "Hypothesis VALIDATED: %s (p=%.4f, d=%.2f, n=%d)",
                    hyp.hypothesis_id, hyp.p_value, hyp.effect_size, total,
                )
            elif hyp.p_value > 0.5 and total >= 20:
                hyp.status = HypothesisStatus.INVALIDATED
                logger.info(
                    "Hypothesis INVALIDATED: %s (p=%.4f, n=%d)",
                    hyp.hypothesis_id, hyp.p_value, total,
                )
            else:
                hyp.status = HypothesisStatus.EMPIRICALLY_TESTED

        return hyp

    def get_predictions_for_context(
        self,
        edge_dimensions: Dict[str, float],
        mechanism: str = "",
    ) -> List[InferentialHypothesis]:
        """Get all validated hypotheses that apply to a given context.

        Used by the placement optimizer and mechanism selector to
        leverage learned causal knowledge at decision time.
        """
        matching = []
        for hyp in self._hypotheses.values():
            if not hyp.is_actionable:
                continue
            if not hyp.matches_context(edge_dimensions):
                continue
            if mechanism and hyp.predicted_mechanism != mechanism:
                continue
            matching.append(hyp)

        return sorted(matching, key=lambda h: h.confidence, reverse=True)

    def get_transfer_candidates(
        self,
        hypothesis_id: str,
        available_pages: Dict[str, Dict[str, float]],
    ) -> List[Tuple[str, float]]:
        """Find pages where a validated hypothesis should also work.

        This is the TRANSFER step — taking a learned causal principle
        and finding new contexts where it applies.
        """
        hyp = self._hypotheses.get(hypothesis_id)
        if not hyp or not hyp.is_actionable:
            return []

        candidates = []
        for page_url, dims in available_pages.items():
            if hyp.matches_context(dims):
                # Compute expected effectiveness based on how well conditions are met
                match_quality = self._compute_match_quality(hyp, dims)
                candidates.append((page_url, match_quality))

        return sorted(candidates, key=lambda x: x[1], reverse=True)

    def _check_theory_plausibility(
        self, hyp: InferentialHypothesis
    ) -> InferentialHypothesis:
        """Check if the theory graph supports this hypothesis."""
        if hyp.causal_chain:
            # Chain exists — use confidence (which incorporates chain strength + empirical support)
            hyp.theory_plausibility = max(
                hyp.causal_chain.get("confidence", 0.3),
                hyp.causal_chain.get("coherence_score", 0.3),
                hyp.causal_chain.get("chain_strength", 0.3),
            )
            hyp.status = HypothesisStatus.THEORY_CHECKED
        else:
            # No chain — lower plausibility but still testable
            hyp.theory_plausibility = 0.2
        return hyp

    def _generate_derived_hypotheses(
        self,
        recipe: CausalRecipe,
        parent: InferentialHypothesis,
    ) -> List[InferentialHypothesis]:
        """Generate derived hypotheses from a parent.

        If "authority works when clt > 0.7" is validated, then:
        - "evidence_proof should also work when clt > 0.7"
          (because both use the central processing route)
        - "authority should work in OTHER categories where clt > 0.7"
          (because the causal chain is category-independent)
        """
        derived = []

        if not recipe.active_chain:
            return derived

        # Get the processing route from the chain
        route = recipe.active_chain.get("processing_route", "")

        if route == "central":
            # Central route mechanisms: authority, evidence_proof, commitment
            # If one works, others on the same route should too
            central_mechs = ["authority", "evidence_proof", "commitment"]
            for mech in central_mechs:
                if mech != recipe.mechanism:
                    self._hypothesis_counter += 1
                    d = InferentialHypothesis(
                        hypothesis_id=f"hyp_{self._hypothesis_counter:06d}",
                        conditions=recipe.conditions,
                        predicted_mechanism=mech,
                        predicted_effectiveness=parent.predicted_effectiveness * 0.8,
                        theory_plausibility=parent.theory_plausibility * 0.7,
                        theory_explanation=(
                            f"Derived from {parent.hypothesis_id}: "
                            f"if {recipe.mechanism} works via central route, "
                            f"{mech} should also work (same processing route)"
                        ),
                        derived_from=parent.hypothesis_id,
                        source_recipe_id=recipe.decision_id,
                        falsification_criteria=f"Test {mech} in matching contexts.",
                    )
                    d.status = HypothesisStatus.THEORY_CHECKED
                    derived.append(d)
                    parent.derived_hypotheses.append(d.hypothesis_id)

        return derived[:3]  # Max 3 derived per parent

    def _explain_chain(self, recipe: CausalRecipe) -> str:
        """Generate human-readable explanation of the causal chain."""
        if not recipe.active_chain:
            return f"{recipe.mechanism} converted under conditions {recipe.conditions}"

        chain = recipe.active_chain
        states = chain.get("active_states", [])
        needs = chain.get("active_needs", [])
        route = chain.get("processing_route", "unknown")

        parts = []
        if states:
            parts.append(f"buyer in state [{', '.join(states[:2])}]")
        if needs:
            parts.append(f"activated need [{', '.join(needs[:2])}]")
        parts.append(f"mechanism {recipe.mechanism} via {route} route")

        return " → ".join(parts) if parts else f"{recipe.mechanism} converted"

    def _compute_match_quality(
        self, hyp: InferentialHypothesis, dims: Dict[str, float]
    ) -> float:
        """How well does a context match the hypothesis conditions?"""
        if not hyp.conditions:
            return 0.5

        total_margin = 0.0
        for dim, (op, threshold) in hyp.conditions.items():
            val = dims.get(dim, 0.5)
            if op == ">":
                margin = val - threshold
            else:
                margin = threshold - val
            total_margin += max(0.0, margin)

        return min(1.0, total_margin / len(hyp.conditions))

    def get_test_priority_ranking(self) -> List[Tuple[str, float, str]]:
        """Rank hypotheses by INFORMATION VALUE — which test teaches us the most.

        Uses Bayesian Optimal Experiment Design:
            info_value(h) = uncertainty(h) × impact(h) × transferability(h)

        - Uncertainty: High variance hypotheses teach more (50/50 > 90/10)
        - Impact: Hypotheses on high-gradient dimensions matter more
        - Transferability: Theory-backed universal chains propagate further

        Returns: [(hypothesis_id, info_value, reason)] sorted by info_value desc.

        This is the extension of the cold-start information value principle
        to the hypothesis level. The cold start engine asks "which buyer
        should we explore to learn the most?" This asks "which hypothesis
        should we test to learn the most about the causal structure?"
        """
        rankings = []

        for hid, hyp in self._hypotheses.items():
            # Skip already validated/invalidated — nothing more to learn
            if hyp.status in (HypothesisStatus.VALIDATED, HypothesisStatus.INVALIDATED):
                continue

            # ── UNCERTAINTY ──
            # Beta posterior variance: highest at 50/50, lowest at extreme ratios
            # V(Beta(a,b)) = ab / ((a+b)²(a+b+1))
            a = hyp.supporting_observations + 1  # +1 for prior
            b = hyp.contradicting_observations + 1
            total = a + b
            variance = (a * b) / (total * total * (total + 1))
            # Normalize: max variance is 0.25 (at a=b=1), min approaches 0
            uncertainty = min(1.0, variance * 12)  # Scale to 0-1

            # ── IMPACT ──
            # Hypotheses about high-gradient dimensions matter more
            impact = 0.5  # Default moderate impact
            try:
                from adam.intelligence.gradient_fields import get_gradient_field
                for dim in hyp.conditions:
                    gf = get_gradient_field("", "")  # Universal gradient
                    if gf and hasattr(gf, 'gradients'):
                        dim_gradient = abs(gf.gradients.get(dim, 0.0))
                        impact = max(impact, dim_gradient * 5)  # Scale up
            except Exception:
                pass
            impact = min(1.0, impact)

            # ── TRANSFERABILITY ──
            # Theory-backed hypotheses transfer to more contexts
            transferability = hyp.theory_plausibility
            # Bonus for hypotheses with derived children (validating them
            # also validates the parent, compounding the learning)
            if hyp.derived_hypotheses:
                transferability = min(1.0, transferability + 0.1 * len(hyp.derived_hypotheses))

            # ── INFORMATION VALUE ──
            info_value = uncertainty * impact * transferability

            # Boost for surprising hypotheses (they challenge current theory,
            # so resolving them teaches the most about the causal structure)
            if hyp.source_recipe_id:
                from adam.intelligence.causal_decomposition import get_causal_decomposition_engine
                decomp = get_causal_decomposition_engine()
                for recipe in decomp._recipes:
                    if recipe.decision_id == hyp.source_recipe_id and recipe.is_surprising:
                        info_value *= 1.5  # 50% boost for surprising origins
                        break

            reason_parts = []
            if uncertainty > 0.6:
                reason_parts.append("high uncertainty (learns a lot)")
            if impact > 0.6:
                reason_parts.append("high-gradient dimensions")
            if transferability > 0.6:
                reason_parts.append("theory-backed (transfers widely)")
            reason = "; ".join(reason_parts) if reason_parts else "moderate priority"

            rankings.append((hid, round(info_value, 4), reason))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def get_next_test(self) -> Optional[Tuple[str, float, str]]:
        """Get the single highest-priority hypothesis to test next.

        This is what the system should test FIRST — the hypothesis that,
        if validated or invalidated, teaches the system the most about
        its causal structure.
        """
        ranking = self.get_test_priority_ranking()
        return ranking[0] if ranking else None

    @property
    def stats(self) -> Dict[str, Any]:
        status_counts = defaultdict(int)
        for h in self._hypotheses.values():
            status_counts[h.status.value] += 1
        return {
            "total_hypotheses": len(self._hypotheses),
            "by_status": dict(status_counts),
            "validated": status_counts.get("validated", 0),
            "actionable": sum(1 for h in self._hypotheses.values() if h.is_actionable),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[InferentialHypothesisEngine] = None


def get_inferential_hypothesis_engine() -> InferentialHypothesisEngine:
    global _engine
    if _engine is None:
        _engine = InferentialHypothesisEngine()
    return _engine
