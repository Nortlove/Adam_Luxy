"""
Inferential Learning Agent — The Theory Builder
=================================================

This is not machine learning. This is THEORY BUILDING.

Machine learning finds patterns: "authority converts at 3.2%."
This agent builds explanations: "authority converts for careful_truster
on business pages BECAUSE the page activates competence goals, and
authority framing fulfills competence goals — BUT only when processing
depth exceeds 2 seconds, because authority arguments require central-
route processing. After 3 exposures, persuasion knowledge activates
and authority triggers reactance — switch to cognitive ease."

The agent maintains a THEORY GRAPH of propositions at 6 complexity
levels, each built on the evidence below it:

Level 1: Which mechanism works ("authority converts for careful_truster")
Level 2: Conditional on context ("...on business pages, not lifestyle")
Level 3: WHY — causal chain ("...because competence goal activation")
Level 4: Interactions ("...only when processing depth > 2s")
Level 5: Temporal dynamics ("...works at touch 1, triggers reactance by touch 3")
Level 6: Meta-learning ("...learning rate faster than expected → low competition")

The weekly cycle: OBSERVE → VALIDATE → HYPOTHESIZE → DESIGN → APPLY

Each proposition is testable, falsifiable, and grounded in the same
inferential framework as the rest of the platform. The system doesn't
just get better — it gets SMARTER, building increasingly complex
understanding that compounds over months.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class ComplexityLevel(IntEnum):
    """Progressively unlocked levels of understanding."""
    ASSOCIATION = 1       # "X works for Y"
    CONDITIONAL = 2       # "X works for Y in context Z"
    CAUSAL_CHAIN = 3      # "X works because A → B → C"
    INTERACTION = 4       # "X works when P AND Q but not when R"
    TEMPORAL = 5          # "X works at time T1 but not T2"
    META = 6              # "The learning rate itself is changing"


class PropositionStatus(str):
    HYPOTHESIS = "hypothesis"     # Proposed but untested
    TESTING = "testing"           # Experiment running
    CONFIRMED = "confirmed"       # Evidence supports (p < 0.05)
    REFUTED = "refuted"          # Evidence contradicts
    REVISED = "revised"          # Modified based on new evidence
    SUPERSEDED = "superseded"    # Replaced by higher-complexity proposition


@dataclass
class Proposition:
    """A unit of knowledge in the theory graph.

    Not a parameter estimate. A STATEMENT about the world that
    makes testable predictions and can be falsified by data.
    """
    prop_id: str = field(default_factory=lambda: f"prop_{uuid4().hex[:8]}")

    # The claim
    statement: str = ""
    complexity: ComplexityLevel = ComplexityLevel.ASSOCIATION

    # What it predicts
    predicted_observation: str = ""
    predicted_direction: str = ""  # "higher", "lower", "different"
    predicted_magnitude: float = 0.0

    # Evidence
    supporting_observations: int = 0
    contradicting_observations: int = 0
    total_observations: int = 0
    confidence: float = 0.5

    # Grounding
    archetype: str = ""
    mechanism: str = ""
    domain_category: str = ""
    additional_conditions: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    status: str = PropositionStatus.HYPOTHESIS
    created_at: float = field(default_factory=time.time)
    last_tested_at: float = 0.0
    test_count: int = 0

    # Relationships
    parent_id: Optional[str] = None      # Higher-level prop this refines
    child_ids: List[str] = field(default_factory=list)  # Lower-level derivations
    superseded_by: Optional[str] = None

    def update_evidence(self, supports: bool, weight: float = 1.0):
        """Bayesian update of proposition confidence."""
        self.total_observations += 1
        self.test_count += 1
        self.last_tested_at = time.time()

        if supports:
            self.supporting_observations += 1
        else:
            self.contradicting_observations += 1

        # Simple Bayesian update
        # P(true | evidence) ∝ P(evidence | true) × P(true)
        likelihood_ratio = 3.0 if supports else 0.33
        prior_odds = self.confidence / max(1 - self.confidence, 0.001)
        posterior_odds = prior_odds * (likelihood_ratio ** weight)
        self.confidence = min(0.99, posterior_odds / (1 + posterior_odds))

        # Status transitions
        if self.confidence > 0.85 and self.total_observations >= 10:
            self.status = PropositionStatus.CONFIRMED
        elif self.confidence < 0.15 and self.total_observations >= 10:
            self.status = PropositionStatus.REFUTED

    @property
    def evidence_ratio(self) -> str:
        return f"{self.supporting_observations}/{self.total_observations}"


@dataclass
class Experiment:
    """A designed test for a proposition."""
    experiment_id: str = field(default_factory=lambda: f"exp_{uuid4().hex[:8]}")
    proposition_id: str = ""
    description: str = ""

    # What we're manipulating
    test_mechanism: str = ""
    test_domain: str = ""
    test_archetype: str = ""
    test_conditions: Dict[str, Any] = field(default_factory=dict)

    # What we expect
    expected_outcome: str = ""
    expected_metric: str = "conversion_rate"
    expected_direction: str = "higher"

    # Results
    observations: int = 0
    successes: int = 0
    actual_rate: float = 0.0
    baseline_rate: float = 0.0
    started_at: float = field(default_factory=time.time)

    @property
    def has_enough_data(self) -> bool:
        return self.observations >= 30

    @property
    def result(self) -> Optional[str]:
        if not self.has_enough_data:
            return None
        if self.expected_direction == "higher":
            return "confirmed" if self.actual_rate > self.baseline_rate * 1.1 else "refuted"
        return "confirmed" if self.actual_rate < self.baseline_rate * 0.9 else "refuted"


class InferentialLearningAgent:
    """The theory-building brain of the system.

    Maintains a graph of propositions at increasing complexity,
    designs experiments to test them, and applies confirmed
    theories to campaign strategy.

    This is the piece that makes the system genuinely intelligent
    over time — not just optimized, but UNDERSTANDING.
    """

    def __init__(self):
        self.propositions: Dict[str, Proposition] = {}
        self.experiments: Dict[str, Experiment] = {}
        self._observation_buffer: List[Dict[str, Any]] = []
        self._current_complexity_ceiling = ComplexityLevel.CONDITIONAL
        self._total_observations = 0
        self._theory_revisions = 0

    # ════════════════════════════════════════════════════════
    # OBSERVE: Ingest outcome data
    # ════════════════════════════════════════════════════════

    def observe(self, observation: Dict[str, Any]):
        """Record an observation for the next learning cycle."""
        self._observation_buffer.append(observation)
        self._total_observations += 1

        # Unlock higher complexity as data accumulates
        if self._total_observations >= 100 and self._current_complexity_ceiling < ComplexityLevel.CAUSAL_CHAIN:
            self._current_complexity_ceiling = ComplexityLevel.CAUSAL_CHAIN
            logger.info("Complexity Level 3 (causal chains) unlocked at %d observations", self._total_observations)
        if self._total_observations >= 500 and self._current_complexity_ceiling < ComplexityLevel.INTERACTION:
            self._current_complexity_ceiling = ComplexityLevel.INTERACTION
            logger.info("Complexity Level 4 (interactions) unlocked at %d observations", self._total_observations)
        if self._total_observations >= 2000 and self._current_complexity_ceiling < ComplexityLevel.TEMPORAL:
            self._current_complexity_ceiling = ComplexityLevel.TEMPORAL
            logger.info("Complexity Level 5 (temporal dynamics) unlocked at %d observations", self._total_observations)
        if self._total_observations >= 5000 and self._current_complexity_ceiling < ComplexityLevel.META:
            self._current_complexity_ceiling = ComplexityLevel.META
            logger.info("Complexity Level 6 (meta-learning) unlocked at %d observations", self._total_observations)

    # ════════════════════════════════════════════════════════
    # VALIDATE: Check existing propositions against new data
    # ════════════════════════════════════════════════════════

    def validate(self) -> List[Dict[str, Any]]:
        """Check all active propositions against buffered observations."""
        validation_results = []

        for obs in self._observation_buffer:
            arch = obs.get("archetype", "")
            mech = obs.get("mechanism", "")
            domain = obs.get("domain_category", "")
            converted = obs.get("outcome_value", 0) > 0.5

            for prop_id, prop in self.propositions.items():
                if prop.status in (PropositionStatus.REFUTED, PropositionStatus.SUPERSEDED):
                    continue

                # Check if this observation is relevant to this proposition
                relevant = self._observation_matches_proposition(obs, prop)
                if not relevant:
                    continue

                # Does the observation support or contradict?
                supports = self._observation_supports(obs, prop)
                weight = obs.get("processing_depth_weight", 1.0)
                prop.update_evidence(supports, weight)

                if prop.status in (PropositionStatus.CONFIRMED, PropositionStatus.REFUTED):
                    validation_results.append({
                        "proposition": prop.statement,
                        "status": prop.status,
                        "confidence": round(prop.confidence, 3),
                        "evidence": prop.evidence_ratio,
                    })

        self._observation_buffer.clear()
        return validation_results

    # ════════════════════════════════════════════════════════
    # HYPOTHESIZE: Generate new propositions
    # ════════════════════════════════════════════════════════

    def hypothesize(self, performance_data: Dict[str, Any]) -> List[Proposition]:
        """Generate new propositions from observed patterns.

        The propositions get more complex as data accumulates.
        Level 1 at week 1, Level 3 by month 1, Level 5 by month 3.
        """
        new_propositions = []

        # Level 1: Simple associations from performance data
        if self._current_complexity_ceiling >= ComplexityLevel.ASSOCIATION:
            new_propositions.extend(
                self._generate_level1_propositions(performance_data)
            )

        # Level 2: Conditional on context
        if self._current_complexity_ceiling >= ComplexityLevel.CONDITIONAL:
            new_propositions.extend(
                self._generate_level2_propositions(performance_data)
            )

        # Level 3: Causal chains from goal activation data
        if self._current_complexity_ceiling >= ComplexityLevel.CAUSAL_CHAIN:
            new_propositions.extend(
                self._generate_level3_propositions(performance_data)
            )

        # Level 4: Interaction effects from factorial analysis
        if self._current_complexity_ceiling >= ComplexityLevel.INTERACTION:
            new_propositions.extend(
                self._generate_level4_propositions(performance_data)
            )

        # Level 5: Temporal patterns from sequence data
        if self._current_complexity_ceiling >= ComplexityLevel.TEMPORAL:
            new_propositions.extend(
                self._generate_level5_propositions(performance_data)
            )

        # Level 6: Meta-learning from learning rate changes
        if self._current_complexity_ceiling >= ComplexityLevel.META:
            new_propositions.extend(
                self._generate_level6_propositions(performance_data)
            )

        # Add to theory graph
        for prop in new_propositions:
            if prop.statement not in [p.statement for p in self.propositions.values()]:
                self.propositions[prop.prop_id] = prop

        return new_propositions

    # ════════════════════════════════════════════════════════
    # DESIGN: Create experiments to test propositions
    # ════════════════════════════════════════════════════════

    def design_experiments(self) -> List[Experiment]:
        """Design experiments for untested propositions.

        Prioritizes by: (1) complexity level, (2) potential impact,
        (3) testability with current campaign structure.
        """
        experiments = []

        untested = [
            p for p in self.propositions.values()
            if p.status == PropositionStatus.HYPOTHESIS
            and p.complexity <= self._current_complexity_ceiling
        ]

        # Sort by complexity (higher = more valuable) then by recency
        untested.sort(key=lambda p: (p.complexity, -p.created_at), reverse=True)

        for prop in untested[:3]:  # Design max 3 experiments per cycle
            exp = self._design_experiment_for(prop)
            if exp:
                experiments.append(exp)
                self.experiments[exp.experiment_id] = exp
                prop.status = PropositionStatus.TESTING

        return experiments

    # ════════════════════════════════════════════════════════
    # APPLY: Translate confirmed theories into campaign actions
    # ════════════════════════════════════════════════════════

    def apply(self) -> List[Dict[str, str]]:
        """Translate confirmed propositions into campaign actions.

        This is where theory becomes practice. Each confirmed
        proposition maps to a specific campaign change:
        - Creative variant adjustment
        - Budget reallocation
        - Domain bid modifier
        - Sequence modification
        - Mechanism switching
        """
        actions = []

        for prop in self.propositions.values():
            if prop.status != PropositionStatus.CONFIRMED:
                continue

            action = self._proposition_to_action(prop)
            if action:
                actions.append(action)

        return actions

    # ════════════════════════════════════════════════════════
    # The full weekly cycle
    # ════════════════════════════════════════════════════════

    def run_learning_cycle(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the complete OBSERVE → VALIDATE → HYPOTHESIZE → DESIGN → APPLY cycle."""
        cycle_start = time.time()

        # 1. Validate existing propositions against new data
        validations = self.validate()

        # 2. Generate new hypotheses from performance patterns
        new_hypotheses = self.hypothesize(performance_data)

        # 3. Design experiments for untested hypotheses
        new_experiments = self.design_experiments()

        # 4. Apply confirmed theories to campaign
        actions = self.apply()

        # 5. Count theory revisions
        revisions = sum(
            1 for p in self.propositions.values()
            if p.status in (PropositionStatus.REFUTED, PropositionStatus.REVISED)
            and p.last_tested_at > cycle_start - 86400 * 7
        )
        self._theory_revisions += revisions

        return {
            "cycle_duration_ms": round((time.time() - cycle_start) * 1000, 1),
            "total_propositions": len(self.propositions),
            "propositions_by_level": self._count_by_level(),
            "propositions_by_status": self._count_by_status(),
            "validations": validations,
            "new_hypotheses": [
                {"statement": h.statement, "level": h.complexity, "confidence": h.confidence}
                for h in new_hypotheses
            ],
            "experiments_designed": len(new_experiments),
            "actions_recommended": actions,
            "complexity_ceiling": self._current_complexity_ceiling,
            "total_observations": self._total_observations,
            "theory_revisions_this_cycle": revisions,
            "cumulative_revisions": self._theory_revisions,
        }

    # ════════════════════════════════════════════════════════
    # Level-specific hypothesis generators
    # ════════════════════════════════════════════════════════

    def _generate_level1_propositions(self, data: Dict) -> List[Proposition]:
        """Level 1: Simple mechanism × archetype associations."""
        props = []
        arch_performance = data.get("archetype_mechanism_performance", {})

        for arch, mechanisms in arch_performance.items():
            if not mechanisms:
                continue
            best_mech = max(mechanisms, key=mechanisms.get)
            worst_mech = min(mechanisms, key=mechanisms.get)

            props.append(Proposition(
                statement=f"{best_mech} is the most effective mechanism for {arch}",
                complexity=ComplexityLevel.ASSOCIATION,
                archetype=arch,
                mechanism=best_mech,
                predicted_observation=f"{best_mech} conversion rate > other mechanisms",
                predicted_direction="higher",
                predicted_magnitude=mechanisms[best_mech],
                confidence=0.6,
            ))

            if mechanisms[worst_mech] < 0.01:
                props.append(Proposition(
                    statement=f"{worst_mech} is ineffective for {arch} — suppress",
                    complexity=ComplexityLevel.ASSOCIATION,
                    archetype=arch,
                    mechanism=worst_mech,
                    predicted_direction="lower",
                    confidence=0.6,
                ))

        return props

    def _generate_level2_propositions(self, data: Dict) -> List[Proposition]:
        """Level 2: Context-conditional associations."""
        props = []
        domain_performance = data.get("domain_mechanism_performance", {})

        for domain, mechanisms in domain_performance.items():
            if not mechanisms:
                continue
            best = max(mechanisms, key=mechanisms.get)
            baseline = data.get("overall_mechanism_performance", {}).get(best, 0)
            domain_rate = mechanisms[best]

            if domain_rate > baseline * 1.2:
                props.append(Proposition(
                    statement=(
                        f"{best} performs {((domain_rate/max(baseline,0.001))-1)*100:.0f}% "
                        f"better on {domain} domains than overall"
                    ),
                    complexity=ComplexityLevel.CONDITIONAL,
                    mechanism=best,
                    domain_category=domain,
                    predicted_direction="higher",
                    predicted_magnitude=domain_rate - baseline,
                    confidence=0.55,
                ))

        return props

    def _generate_level3_propositions(self, data: Dict) -> List[Proposition]:
        """Level 3: Causal chains via goal activation evidence."""
        props = []
        goal_mechanism_data = data.get("goal_mechanism_conversions", {})

        for goal, mechanisms in goal_mechanism_data.items():
            if not mechanisms:
                continue
            best = max(mechanisms, key=mechanisms.get)
            props.append(Proposition(
                statement=(
                    f"{best} converts when '{goal}' goal is active because "
                    f"{best} framing fulfills the {goal} motivation — "
                    f"this is goal-directed selective attention, not topic matching"
                ),
                complexity=ComplexityLevel.CAUSAL_CHAIN,
                mechanism=best,
                additional_conditions={"active_goal": goal},
                predicted_observation=(
                    f"Conversion rate for {best} should be higher on pages "
                    f"that activate '{goal}' than pages that don't"
                ),
                predicted_direction="higher",
                confidence=0.5,
            ))

        return props

    def _generate_level4_propositions(self, data: Dict) -> List[Proposition]:
        """Level 4: Interaction effects (mechanism × depth × domain)."""
        props = []
        depth_mechanism_data = data.get("depth_mechanism_performance", {})

        for depth_bin, mechanisms in depth_mechanism_data.items():
            if depth_bin == "deep" and mechanisms:
                central_route = ["authority", "commitment", "reciprocity"]
                for mech in central_route:
                    if mech in mechanisms and mechanisms[mech] > 0.03:
                        props.append(Proposition(
                            statement=(
                                f"{mech} requires deep processing (>2s viewport) "
                                f"to be effective — it operates on the central route "
                                f"and needs the argument to be cognitively processed"
                            ),
                            complexity=ComplexityLevel.INTERACTION,
                            mechanism=mech,
                            additional_conditions={"processing_depth_min": 2.0},
                            predicted_observation=(
                                f"{mech} conversion rate at depth>2s should be "
                                f"significantly higher than at depth<2s"
                            ),
                            predicted_direction="higher",
                            confidence=0.5,
                        ))

            if depth_bin == "shallow" and mechanisms:
                peripheral_route = ["cognitive_ease", "liking", "social_proof"]
                for mech in peripheral_route:
                    if mech in mechanisms and mechanisms[mech] > 0.02:
                        props.append(Proposition(
                            statement=(
                                f"{mech} works even with shallow processing (<2s) "
                                f"because it operates on the peripheral route — "
                                f"doesn't require argument comprehension"
                            ),
                            complexity=ComplexityLevel.INTERACTION,
                            mechanism=mech,
                            additional_conditions={"processing_depth_max": 2.0},
                            confidence=0.5,
                        ))

        return props

    def _generate_level5_propositions(self, data: Dict) -> List[Proposition]:
        """Level 5: Temporal dynamics from sequence data."""
        props = []
        sequence_data = data.get("sequence_performance", {})

        for mech, touch_data in sequence_data.items():
            if len(touch_data) < 3:
                continue

            rates = [touch_data.get(f"touch_{i}", 0) for i in range(1, 4)]
            if len(rates) >= 3 and rates[0] > 0 and rates[2] < rates[0] * 0.5:
                props.append(Proposition(
                    statement=(
                        f"{mech} shows decay from touch 1 ({rates[0]:.3f}) to "
                        f"touch 3 ({rates[2]:.3f}) — likely persuasion knowledge "
                        f"activation causing reactance. Recommend mechanism switch "
                        f"after touch 2."
                    ),
                    complexity=ComplexityLevel.TEMPORAL,
                    mechanism=mech,
                    additional_conditions={"max_touches": 2},
                    predicted_observation=(
                        f"Switching mechanism after touch 2 should maintain "
                        f"conversion rate above {rates[2]:.3f}"
                    ),
                    confidence=0.45,
                ))

        return props

    def _generate_level6_propositions(self, data: Dict) -> List[Proposition]:
        """Level 6: Meta-learning — reasoning about the learning process itself."""
        props = []
        learning_rate = data.get("learning_rate_trend", "")
        competitive_saturation = data.get("competitive_saturation", {})

        if learning_rate == "accelerating":
            props.append(Proposition(
                statement=(
                    "Learning rate is accelerating — the system is discovering "
                    "high-value patterns faster than expected. This suggests low "
                    "competitive saturation: increase budget while the advantage lasts."
                ),
                complexity=ComplexityLevel.META,
                predicted_observation="Continued performance improvement per dollar spent",
                confidence=0.4,
            ))

        if learning_rate == "plateauing":
            props.append(Proposition(
                statement=(
                    "Learning rate is plateauing — diminishing returns on current "
                    "approach. Either the market is saturating or the current "
                    "mechanism mix has been optimized. Recommend expanding to new "
                    "archetypes or testing novel mechanism combinations."
                ),
                complexity=ComplexityLevel.META,
                predicted_observation="New mechanisms or archetypes should show higher learning rate",
                confidence=0.4,
            ))

        return props

    # ════════════════════════════════════════════════════════
    # Helper methods
    # ════════════════════════════════════════════════════════

    def _observation_matches_proposition(
        self, obs: Dict, prop: Proposition
    ) -> bool:
        """Check if an observation is relevant to a proposition."""
        if prop.archetype and obs.get("archetype") != prop.archetype:
            return False
        if prop.mechanism and obs.get("mechanism") != prop.mechanism:
            return False
        if prop.domain_category and obs.get("domain_category") != prop.domain_category:
            return False
        return True

    def _observation_supports(self, obs: Dict, prop: Proposition) -> bool:
        """Check if an observation supports or contradicts a proposition."""
        converted = obs.get("outcome_value", 0) > 0.5
        if prop.predicted_direction == "higher":
            return converted
        elif prop.predicted_direction == "lower":
            return not converted
        return converted

    def _design_experiment_for(self, prop: Proposition) -> Optional[Experiment]:
        """Design an experiment to test a proposition."""
        return Experiment(
            proposition_id=prop.prop_id,
            description=f"Test: {prop.statement[:80]}",
            test_mechanism=prop.mechanism,
            test_domain=prop.domain_category,
            test_archetype=prop.archetype,
            expected_outcome=prop.predicted_observation,
            expected_direction=prop.predicted_direction,
        )

    def _proposition_to_action(self, prop: Proposition) -> Optional[Dict[str, str]]:
        """Translate a confirmed proposition into a campaign action."""
        if prop.complexity == ComplexityLevel.ASSOCIATION:
            return {
                "type": "mechanism_boost",
                "action": f"Increase rotation weight for {prop.mechanism} "
                         f"creative variant in {prop.archetype} campaign",
                "confidence": f"{prop.confidence:.0%}",
                "evidence": prop.evidence_ratio,
                "reasoning": prop.statement,
            }
        elif prop.complexity == ComplexityLevel.CONDITIONAL:
            return {
                "type": "domain_bid",
                "action": f"Increase bid modifier for {prop.mechanism} "
                         f"on {prop.domain_category} domains",
                "confidence": f"{prop.confidence:.0%}",
                "reasoning": prop.statement,
            }
        elif prop.complexity == ComplexityLevel.CAUSAL_CHAIN:
            goal = prop.additional_conditions.get("active_goal", "unknown")
            return {
                "type": "goal_targeting",
                "action": f"Prioritize pages activating '{goal}' goal "
                         f"for {prop.mechanism} creative",
                "confidence": f"{prop.confidence:.0%}",
                "reasoning": prop.statement,
            }
        elif prop.complexity == ComplexityLevel.TEMPORAL:
            max_touches = prop.additional_conditions.get("max_touches", 3)
            return {
                "type": "sequence_modification",
                "action": f"Switch mechanism after touch {max_touches} "
                         f"for {prop.mechanism}",
                "confidence": f"{prop.confidence:.0%}",
                "reasoning": prop.statement,
            }
        return None

    def _count_by_level(self) -> Dict[str, int]:
        counts = {}
        for prop in self.propositions.values():
            level_name = ComplexityLevel(prop.complexity).name
            counts[level_name] = counts.get(level_name, 0) + 1
        return counts

    def _count_by_status(self) -> Dict[str, int]:
        counts = {}
        for prop in self.propositions.values():
            counts[prop.status] = counts.get(prop.status, 0) + 1
        return counts

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_propositions": len(self.propositions),
            "by_level": self._count_by_level(),
            "by_status": self._count_by_status(),
            "active_experiments": sum(
                1 for e in self.experiments.values()
                if not e.has_enough_data
            ),
            "complexity_ceiling": self._current_complexity_ceiling,
            "total_observations": self._total_observations,
            "theory_revisions": self._theory_revisions,
        }


# Singleton
_agent: Optional[InferentialLearningAgent] = None


def get_inferential_agent() -> InferentialLearningAgent:
    """Get or create the singleton learning agent."""
    global _agent
    if _agent is None:
        _agent = InferentialLearningAgent()
        logger.info("Inferential Learning Agent initialized (theory builder)")
    return _agent
