# =============================================================================
# Resonance Engineering — Layer 6: EVOLVE
# Location: adam/retargeting/resonance/evolutionary_engine.py
# =============================================================================

"""
Evolutionary Engine — Active Self-Improvement for Resonance Engineering.

Five sub-engines that enable the system to discover, test, and evolve
resonance strategies beyond what theory predicts:

A. Hypothesis Generator: Proposes novel page_mindstate × mechanism combinations
B. Experiment Allocator: UCB1 allocation of 10% exploration budget
C. Synergy Detector: Finds non-obvious amplification effects
D. Evolution Manager: Propagate winners, prune losers, introduce mutations
E. Self-Evaluator: Monitor prediction accuracy, detect concept drift

The evolutionary loop runs on three timescales:
- Fast (per-impression): experiment allocation
- Medium (per-outcome): observation recording
- Slow (daily): hypothesis generation, synergy detection, evolution cycle
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from scipy.stats import pearsonr, fisher_exact

from adam.retargeting.resonance.models import (
    ResonanceHypothesis,
    ResonanceExperiment,
    PageMindstateVector,
    ALL_MINDSTATE_DIMS,
)
from adam.retargeting.resonance.resonance_learner import (
    ResonanceLearner,
    ResonanceObservation,
)

logger = logging.getLogger(__name__)

# Configuration
EXPLORATION_FRACTION = 0.10      # 10% of impressions for experiments
MIN_OBS_FOR_HYPOTHESIS = 30      # Need this many observations to propose
MIN_OBS_FOR_VALIDATION = 50      # Need this many to validate
SIGNIFICANCE_THRESHOLD = 0.05    # p < 0.05 to validate
LIFT_THRESHOLD_FOR_PROMOTION = 0.15  # 15% lift to promote to system knowledge
PRUNE_AFTER_N = 200              # Prune after this many observations if no effect
MAX_ACTIVE_EXPERIMENTS = 5       # Limit concurrent experiments


# ─────────────────────────────────────────────────────────────────────
# A. HYPOTHESIS GENERATOR
# ─────────────────────────────────────────────────────────────────────

class ResonanceHypothesisGenerator:
    """Proposes testable hypotheses about page × mechanism interactions.

    Three generation strategies:
    1. Residual-driven: Where is the resonance model systematically wrong?
    2. Counterintuitive: Test the OPPOSITE of what theory predicts
    3. Interaction-driven: Test non-obvious dimension × mechanism combinations
    """

    def generate(
        self,
        observations: List[ResonanceObservation],
        existing_hypotheses: Optional[List[ResonanceHypothesis]] = None,
        n: int = 3,
    ) -> List[ResonanceHypothesis]:
        """Generate up to n new hypotheses from observations."""
        existing = set(h.hypothesis_id for h in (existing_hypotheses or []))
        hypotheses = []

        if len(observations) >= MIN_OBS_FOR_HYPOTHESIS:
            # Strategy 1: Residual-driven
            h = self._generate_residual_hypothesis(observations)
            if h and h.hypothesis_id not in existing:
                hypotheses.append(h)

            # Strategy 2: Counterintuitive
            h = self._generate_counterintuitive_hypothesis(observations)
            if h and h.hypothesis_id not in existing:
                hypotheses.append(h)

            # Strategy 3: Interaction-driven
            h = self._generate_interaction_hypothesis(observations)
            if h and h.hypothesis_id not in existing:
                hypotheses.append(h)

        return hypotheses[:n]

    def _generate_residual_hypothesis(
        self, observations: List[ResonanceObservation]
    ) -> Optional[ResonanceHypothesis]:
        """Find where the model is systematically wrong."""
        # Compute residuals: predicted_resonance - actual_outcome
        residuals = []
        page_dims = []
        for obs in observations:
            if obs.page_mindstate_vector is not None:
                residual = obs.predicted_resonance - obs.outcome_score
                residuals.append(residual)
                page_dims.append(obs.page_mindstate_vector)

        if len(residuals) < MIN_OBS_FOR_HYPOTHESIS:
            return None

        residuals = np.array(residuals)
        page_matrix = np.array(page_dims)

        # Find the page dimension most correlated with residuals
        best_dim = None
        best_r = 0.0
        for i, dim_name in enumerate(ALL_MINDSTATE_DIMS):
            if i >= page_matrix.shape[1]:
                break
            col = page_matrix[:, i]
            if np.std(col) < 0.01:
                continue
            r, p = pearsonr(col, residuals)
            if abs(r) > abs(best_r) and p < 0.1:
                best_r = r
                best_dim = dim_name

        if best_dim is None or abs(best_r) < 0.1:
            return None

        # Most common mechanism in the observations
        mech_counts = {}
        for obs in observations:
            mech_counts[obs.mechanism] = mech_counts.get(obs.mechanism, 0) + 1
        top_mech = max(mech_counts, key=mech_counts.get) if mech_counts else "evidence_proof"

        direction = "high" if best_r > 0 else "low"
        effect = "suppresses" if best_r > 0 else "amplifies"

        return ResonanceHypothesis(
            hypothesis_type="residual_driven",
            statement=(
                f"Model over-predicts when page {best_dim} is {direction}. "
                f"Hypothesis: {direction} {best_dim} {effect} {top_mech} "
                f"(residual correlation r={best_r:.3f})."
            ),
            mechanism=top_mech,
            page_dimension=best_dim,
            page_value_range=(0.6, 1.0) if direction == "high" else (0.0, 0.4),
            predicted_effect=effect,
            predicted_magnitude=abs(best_r),
            source="prediction_residual",
            prior_observations=len(observations),
            prior_effect_size=abs(best_r),
        )

    def _generate_counterintuitive_hypothesis(
        self, observations: List[ResonanceObservation]
    ) -> Optional[ResonanceHypothesis]:
        """Test the opposite of what theory predicts.

        The biggest non-obvious effects come from testing assumptions.
        E.g., "anxiety_resolution on POSITIVE pages via contrast effect."
        """
        from adam.retargeting.resonance.cold_start import MECHANISM_IDEAL_VECTORS

        # Pick a mechanism and its strongest ideal dimension
        mechanisms = list(MECHANISM_IDEAL_VECTORS.keys())
        mech = mechanisms[hash(str(time.time())) % len(mechanisms)]
        ideal = MECHANISM_IDEAL_VECTORS[mech]

        # Find the dimension with the strongest ideal preference
        strongest_idx = int(np.argmax(np.abs(ideal)))
        if strongest_idx >= len(ALL_MINDSTATE_DIMS):
            return None

        dim = ALL_MINDSTATE_DIMS[strongest_idx]
        ideal_direction = "high" if ideal[strongest_idx] > 0 else "low"
        counter_direction = "low" if ideal_direction == "high" else "high"

        return ResonanceHypothesis(
            hypothesis_type="counterintuitive",
            statement=(
                f"Theory says {mech} works on {ideal_direction}-{dim} pages. "
                f"COUNTERINTUITIVE: Does {mech} work BETTER on {counter_direction}-{dim} "
                f"pages via contrast/surprise effect?"
            ),
            mechanism=mech,
            page_dimension=dim,
            page_value_range=(0.0, 0.3) if counter_direction == "low" else (0.7, 1.0),
            predicted_effect="amplifies",
            predicted_magnitude=0.15,
            source="theory_inversion",
            prior_observations=len(observations),
        )

    def _generate_interaction_hypothesis(
        self, observations: List[ResonanceObservation]
    ) -> Optional[ResonanceHypothesis]:
        """Test non-obvious dimension × dimension interaction effects."""
        if len(observations) < MIN_OBS_FOR_HYPOTHESIS * 2:
            return None

        page_matrix = np.array([
            o.page_mindstate_vector for o in observations
            if o.page_mindstate_vector is not None
        ])
        outcomes = np.array([o.outcome_score for o in observations if o.page_mindstate_vector is not None])

        if len(outcomes) < 30:
            return None

        # Test interaction: dim_A × dim_B → outcome
        best_interaction = None
        best_r = 0.0

        # Sample random pairs (exhaustive is too slow)
        rng = np.random.RandomState(int(time.time()) % 2**31)
        for _ in range(20):
            i = rng.randint(0, min(page_matrix.shape[1], len(ALL_MINDSTATE_DIMS)))
            j = rng.randint(0, min(page_matrix.shape[1], len(ALL_MINDSTATE_DIMS)))
            if i == j or i >= page_matrix.shape[1] or j >= page_matrix.shape[1]:
                continue

            interaction = page_matrix[:, i] * page_matrix[:, j]
            if np.std(interaction) < 0.01:
                continue

            r, p = pearsonr(interaction, outcomes)
            if abs(r) > abs(best_r) and p < 0.1:
                best_r = r
                best_interaction = (ALL_MINDSTATE_DIMS[i], ALL_MINDSTATE_DIMS[j])

        if best_interaction is None or abs(best_r) < 0.1:
            return None

        dim_a, dim_b = best_interaction
        top_mech = max(
            set(o.mechanism for o in observations),
            key=lambda m: sum(1 for o in observations if o.mechanism == m),
        )

        return ResonanceHypothesis(
            hypothesis_type="interaction_driven",
            statement=(
                f"Interaction effect: {dim_a} × {dim_b} predicts conversion "
                f"(r={best_r:.3f}). When BOTH are {'high' if best_r > 0 else 'mismatched'}, "
                f"{top_mech} is {'amplified' if best_r > 0 else 'suppressed'}."
            ),
            mechanism=top_mech,
            page_dimension=f"{dim_a}×{dim_b}",
            predicted_effect="amplifies" if best_r > 0 else "suppresses",
            predicted_magnitude=abs(best_r),
            source="interaction_discovery",
            prior_observations=len(observations),
            prior_effect_size=abs(best_r),
        )


# ─────────────────────────────────────────────────────────────────────
# B. EXPERIMENT ALLOCATOR
# ─────────────────────────────────────────────────────────────────────

class ResonanceExperimentAllocator:
    """Manages the exploration budget for resonance experiments."""

    def __init__(self, exploration_fraction: float = EXPLORATION_FRACTION):
        self.exploration_fraction = exploration_fraction
        self.active_experiments: List[ResonanceExperiment] = []

    def should_explore(self) -> bool:
        """Should this impression be allocated to exploration?"""
        return (
            np.random.random() < self.exploration_fraction
            and len(self.active_experiments) > 0
        )

    def select_experiment(self) -> Optional[ResonanceExperiment]:
        """UCB1 selection across active experiments."""
        if not self.active_experiments:
            return None

        total_impressions = sum(
            e.control_impressions + e.treatment_impressions
            for e in self.active_experiments
        ) + 1

        best_exp = None
        best_ucb = -1.0

        for exp in self.active_experiments:
            if exp.decision != "continue":
                continue

            n = exp.treatment_impressions + exp.control_impressions + 1
            reward = exp.treatment_rate
            ucb = reward + math.sqrt(2 * math.log(total_impressions) / n)

            if ucb > best_ucb:
                best_ucb = ucb
                best_exp = exp

        return best_exp

    def create_experiment(
        self, hypothesis: ResonanceHypothesis
    ) -> ResonanceExperiment:
        """Create a new experiment from a hypothesis."""
        exp = ResonanceExperiment(
            hypothesis_id=hypothesis.hypothesis_id,
            control_strategy=f"current_resonance_model",
            treatment_strategy=f"hypothesis_{hypothesis.hypothesis_type}_{hypothesis.page_dimension}",
            traffic_fraction=self.exploration_fraction / max(len(self.active_experiments) + 1, 1),
        )
        self.active_experiments.append(exp)
        return exp

    def evaluate_experiments(self) -> List[Dict[str, Any]]:
        """Evaluate all active experiments. Return decisions."""
        decisions = []
        for exp in self.active_experiments:
            if exp.decision != "continue":
                continue

            total = exp.treatment_impressions + exp.control_impressions
            if total < exp.min_observations:
                decisions.append({"experiment_id": exp.experiment_id, "decision": "continue", "reason": "insufficient_data"})
                continue

            # Fisher exact test for significance
            if exp.treatment_impressions > 0 and exp.control_impressions > 0:
                table = [
                    [exp.treatment_conversions, exp.treatment_impressions - exp.treatment_conversions],
                    [exp.control_conversions, exp.control_impressions - exp.control_conversions],
                ]
                try:
                    _, p = fisher_exact(table)
                    exp.current_p_value = p
                    exp.current_effect_size = exp.lift
                except Exception:
                    p = 1.0

                if p < SIGNIFICANCE_THRESHOLD and exp.lift > LIFT_THRESHOLD_FOR_PROMOTION:
                    exp.decision = "stop_winner"
                    decisions.append({"experiment_id": exp.experiment_id, "decision": "winner", "lift": exp.lift, "p": p})
                elif total >= exp.max_observations:
                    exp.decision = "stop_futility"
                    decisions.append({"experiment_id": exp.experiment_id, "decision": "futility", "lift": exp.lift, "p": p})
                else:
                    decisions.append({"experiment_id": exp.experiment_id, "decision": "continue", "p": p, "lift": exp.lift})

        # Clean up completed experiments
        self.active_experiments = [e for e in self.active_experiments if e.decision == "continue"]
        return decisions


# ─────────────────────────────────────────────────────────────────────
# C. SYNERGY DETECTOR
# ─────────────────────────────────────────────────────────────────────

class SynergyDetector:
    """Discovers non-obvious amplification effects."""

    def detect(
        self, observations: List[ResonanceObservation], min_n: int = 50
    ) -> List[Dict[str, Any]]:
        """Find interaction effects greater than the sum of parts.

        Returns list of discovered synergies with evidence.
        """
        if len(observations) < min_n:
            return []

        synergies = []
        page_matrix = np.array([
            o.page_mindstate_vector for o in observations
            if o.page_mindstate_vector is not None
        ])
        outcomes = np.array([
            o.outcome_score for o in observations
            if o.page_mindstate_vector is not None
        ])
        mechanisms = [
            o.mechanism for o in observations
            if o.page_mindstate_vector is not None
        ]

        if len(outcomes) < min_n:
            return []

        # For each mechanism, find page dimensions whose INTERACTION
        # predicts conversion better than either alone
        unique_mechs = set(mechanisms)
        for mech in unique_mechs:
            mask = np.array([m == mech for m in mechanisms])
            if mask.sum() < 20:
                continue

            X_mech = page_matrix[mask]
            y_mech = outcomes[mask]

            # Test top-5 dimension pairs for interaction effects
            # (exhaustive is O(n^2) — sample strategically)
            dim_cors = []
            for i in range(min(X_mech.shape[1], len(ALL_MINDSTATE_DIMS))):
                if np.std(X_mech[:, i]) > 0.01:
                    r, _ = pearsonr(X_mech[:, i], y_mech)
                    dim_cors.append((i, abs(r)))
            dim_cors.sort(key=lambda x: x[1], reverse=True)

            top_dims = [idx for idx, _ in dim_cors[:8]]
            for i in range(len(top_dims)):
                for j in range(i + 1, len(top_dims)):
                    idx_a, idx_b = top_dims[i], top_dims[j]
                    if idx_a >= len(ALL_MINDSTATE_DIMS) or idx_b >= len(ALL_MINDSTATE_DIMS):
                        continue

                    # Main effects
                    r_a, _ = pearsonr(X_mech[:, idx_a], y_mech)
                    r_b, _ = pearsonr(X_mech[:, idx_b], y_mech)

                    # Interaction effect
                    interaction = X_mech[:, idx_a] * X_mech[:, idx_b]
                    if np.std(interaction) < 0.01:
                        continue
                    r_ab, p_ab = pearsonr(interaction, y_mech)

                    # Synergy = interaction stronger than sum of main effects
                    if abs(r_ab) > abs(r_a) + abs(r_b) and p_ab < 0.1:
                        synergies.append({
                            "mechanism": mech,
                            "dim_a": ALL_MINDSTATE_DIMS[idx_a],
                            "dim_b": ALL_MINDSTATE_DIMS[idx_b],
                            "r_a": round(r_a, 3),
                            "r_b": round(r_b, 3),
                            "r_interaction": round(r_ab, 3),
                            "synergy_excess": round(abs(r_ab) - abs(r_a) - abs(r_b), 3),
                            "p_value": round(p_ab, 4),
                            "n_observations": int(mask.sum()),
                        })

        synergies.sort(key=lambda s: s["synergy_excess"], reverse=True)
        return synergies[:10]


# ─────────────────────────────────────────────────────────────────────
# D. EVOLUTION MANAGER
# ─────────────────────────────────────────────────────────────────────

class ResonanceEvolutionManager:
    """Manages the lifecycle of resonance strategies."""

    def __init__(self):
        self.promoted_strategies: List[Dict[str, Any]] = []
        self.pruned_strategies: List[Dict[str, Any]] = []
        self.mutations_generated: int = 0

    def evolution_cycle(
        self,
        experiment_decisions: List[Dict],
        synergies: List[Dict],
        hypotheses: List[ResonanceHypothesis],
    ) -> Dict[str, Any]:
        """Run one evolution cycle.

        1. PROMOTE: Winning experiments → system knowledge
        2. PRUNE: Futile experiments → marked as no-effect
        3. MUTATE: Generate novel combinations from successful patterns
        """
        results = {"promoted": 0, "pruned": 0, "mutated": 0}

        # Promote winners
        for decision in experiment_decisions:
            if decision.get("decision") == "winner":
                self.promoted_strategies.append({
                    "experiment_id": decision["experiment_id"],
                    "lift": decision.get("lift", 0),
                    "promoted_at": time.time(),
                })
                results["promoted"] += 1

            elif decision.get("decision") == "futility":
                self.pruned_strategies.append({
                    "experiment_id": decision["experiment_id"],
                    "pruned_at": time.time(),
                })
                results["pruned"] += 1

        # Promote strong synergies
        for synergy in synergies:
            if synergy.get("synergy_excess", 0) > 0.1 and synergy.get("p_value", 1) < 0.05:
                self.promoted_strategies.append({
                    "type": "synergy",
                    "mechanism": synergy["mechanism"],
                    "dims": f"{synergy['dim_a']}×{synergy['dim_b']}",
                    "effect": synergy["r_interaction"],
                    "promoted_at": time.time(),
                })
                results["promoted"] += 1

        # Mutate: cross-archetype transfer from validated hypotheses
        for h in hypotheses:
            if h.status == "validated":
                self.mutations_generated += 1
                results["mutated"] += 1

        return results

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "promoted": len(self.promoted_strategies),
            "pruned": len(self.pruned_strategies),
            "mutations": self.mutations_generated,
        }


# ─────────────────────────────────────────────────────────────────────
# E. SELF-EVALUATOR
# ─────────────────────────────────────────────────────────────────────

class ResonanceSelfEvaluator:
    """Monitors resonance model accuracy and triggers recalibration."""

    def __init__(
        self,
        accuracy_threshold: float = 0.15,
        drift_window: int = 100,
    ):
        self.threshold = accuracy_threshold
        self.drift_window = drift_window
        self._recalibrations_triggered = 0

    def evaluate(
        self, accuracy_tracker, model_stats: Dict
    ) -> Dict[str, Any]:
        """Evaluate model health and recommend action."""
        accuracy = accuracy_tracker.recent_accuracy
        trend = accuracy_tracker.accuracy_trend

        action = "none"
        if accuracy < self.threshold and len(accuracy_tracker.predictions) > self.drift_window:
            action = "recalibrate"
            self._recalibrations_triggered += 1
        elif trend == "degrading":
            action = "monitor_closely"

        return {
            "accuracy": round(accuracy, 4),
            "trend": trend,
            "action": action,
            "model_stage_distribution": model_stats.get("cells_by_stage", {}),
            "recalibrations_triggered": self._recalibrations_triggered,
        }


# ─────────────────────────────────────────────────────────────────────
# UNIFIED EVOLUTIONARY ENGINE
# ─────────────────────────────────────────────────────────────────────

class ResonanceEvolutionaryEngine:
    """Orchestrates all five evolutionary sub-engines.

    Usage:
        engine = ResonanceEvolutionaryEngine(learner)

        # Daily evolution cycle
        report = engine.run_evolution_cycle()

        # Per-impression: check if this should be an experiment
        if engine.should_explore():
            experiment = engine.get_active_experiment()
    """

    def __init__(self, learner: Optional[ResonanceLearner] = None):
        self._learner = learner or ResonanceLearner()
        self.hypothesis_generator = ResonanceHypothesisGenerator()
        self.experiment_allocator = ResonanceExperimentAllocator()
        self.synergy_detector = SynergyDetector()
        self.evolution_manager = ResonanceEvolutionManager()
        self.self_evaluator = ResonanceSelfEvaluator()

        self.all_hypotheses: List[ResonanceHypothesis] = []

    def run_evolution_cycle(self) -> Dict[str, Any]:
        """Run the full daily evolution cycle.

        Called during self-teaching (6 AM UTC) or on-demand.
        """
        report: Dict[str, Any] = {"timestamp": time.time()}

        observations = self._learner.get_observations()
        report["total_observations"] = len(observations)

        # 1. Generate new hypotheses
        new_hypotheses = self.hypothesis_generator.generate(
            observations, self.all_hypotheses, n=3
        )
        self.all_hypotheses.extend(new_hypotheses)
        report["new_hypotheses"] = len(new_hypotheses)
        report["hypotheses"] = [
            {"type": h.hypothesis_type, "statement": h.statement[:80]}
            for h in new_hypotheses
        ]

        # 2. Create experiments for new hypotheses (if under limit)
        experiments_created = 0
        for h in new_hypotheses:
            if len(self.experiment_allocator.active_experiments) < MAX_ACTIVE_EXPERIMENTS:
                self.experiment_allocator.create_experiment(h)
                h.status = "testing"
                experiments_created += 1
        report["experiments_created"] = experiments_created

        # 3. Evaluate active experiments
        decisions = self.experiment_allocator.evaluate_experiments()
        report["experiment_decisions"] = decisions

        # 4. Detect synergies
        synergies = self.synergy_detector.detect(observations)
        report["synergies_found"] = len(synergies)
        if synergies:
            report["top_synergy"] = synergies[0]

        # 5. Evolution cycle: promote/prune/mutate
        evolution = self.evolution_manager.evolution_cycle(
            decisions, synergies, self.all_hypotheses
        )
        report["evolution"] = evolution

        # 6. Self-evaluation
        evaluation = self.self_evaluator.evaluate(
            self._learner.accuracy_tracker,
            self._learner._model.stats,
        )
        report["self_evaluation"] = evaluation

        logger.info(
            "Evolution cycle: %d obs, %d hypotheses, %d synergies, "
            "accuracy=%.3f (%s), promoted=%d, pruned=%d",
            len(observations), len(new_hypotheses), len(synergies),
            evaluation["accuracy"], evaluation["trend"],
            evolution["promoted"], evolution["pruned"],
        )

        return report

    def should_explore(self) -> bool:
        """Should this impression be allocated to exploration?"""
        return self.experiment_allocator.should_explore()

    def get_active_experiment(self) -> Optional[ResonanceExperiment]:
        """Get the experiment to run for this impression."""
        return self.experiment_allocator.select_experiment()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_hypotheses": len(self.all_hypotheses),
            "hypotheses_by_status": dict(
                __import__('collections').Counter(h.status for h in self.all_hypotheses)
            ),
            "active_experiments": len(self.experiment_allocator.active_experiments),
            "evolution": self.evolution_manager.stats,
        }
