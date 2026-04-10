# =============================================================================
# ADAM Recursive Self-Improvement Engine
# Location: adam/orchestrator/adaptive/self_improvement.py
# =============================================================================

"""
RECURSIVE SELF-IMPROVEMENT ENGINE

A novel system where the LangGraph computation graph MEASURES ITS OWN
PERFORMANCE and RESTRUCTURES ITSELF over time. This is not just parameter
tuning — it is structural optimization of the reasoning architecture.

Levels of self-improvement:
1. PARAMETER LEVEL: Adjust thresholds, weights, attention biases (fast, per-request)
2. TOPOLOGY LEVEL: Add/remove atoms, change edges, modify parallelism (medium, periodic)
3. STRATEGY LEVEL: Evolve the portfolio of meta-strategies (slow, batch)
4. ARCHITECTURE LEVEL: Propose entirely new atom combinations (very slow, experimental)

Inspired by:
- Schmidhuber (2004) — Optimal Ordered Problem Solver (self-modifying)
- Real et al. (2019) — Regularized Evolution for Architecture Search
- Elsken et al. (2019) — Neural Architecture Search
- Sutton & Barto (2018) — Reinforcement Learning framework

Key mechanism: Each graph configuration is treated as an "arm" in a
multi-armed bandit. The engine uses UCB1 (Upper Confidence Bound) to
balance exploration of new configurations vs. exploitation of known-good
configurations. Over time, the system converges on optimal architectures
for each context type.
"""

import logging
import math
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class ImprovementLevel(str, Enum):
    """Level of self-improvement being applied."""
    PARAMETER = "parameter"
    TOPOLOGY = "topology"
    STRATEGY = "strategy"
    ARCHITECTURE = "architecture"


@dataclass
class GraphConfiguration:
    """A specific graph configuration being evaluated."""
    config_id: str
    description: str
    level: ImprovementLevel

    # What makes this configuration unique
    active_atoms: List[str] = field(default_factory=list)
    pruned_atoms: List[str] = field(default_factory=list)
    parameter_overrides: Dict[str, float] = field(default_factory=dict)
    edge_modifications: List[Dict[str, str]] = field(default_factory=list)

    # Bandit statistics
    times_selected: int = 0
    total_reward: float = 0.0
    avg_quality: float = 0.0
    avg_latency_ms: float = 0.0

    # UCB1 fields
    ucb_score: float = float("inf")

    @property
    def mean_reward(self) -> float:
        if self.times_selected == 0:
            return 0.0
        return self.total_reward / self.times_selected


@dataclass
class ImprovementProposal:
    """A proposed improvement to the graph."""
    proposal_id: str
    level: ImprovementLevel
    description: str
    rationale: str

    # What to change
    changes: Dict[str, Any] = field(default_factory=dict)

    # Expected impact
    expected_quality_delta: float = 0.0
    expected_latency_delta_ms: float = 0.0
    confidence: float = 0.5

    # Evaluation
    approved: bool = False
    evaluated: bool = False
    actual_quality_delta: float = 0.0


@dataclass
class PerformanceSnapshot:
    """A snapshot of system performance at a point in time."""
    timestamp: float
    total_requests: int = 0
    success_rate: float = 0.0
    avg_quality: float = 0.0
    avg_latency_ms: float = 0.0
    atoms_per_request: float = 0.0
    top_config: str = ""
    improvement_level: str = ""


# =============================================================================
# SELF-IMPROVEMENT ENGINE
# =============================================================================

class SelfImprovementEngine:
    """
    Monitors graph performance and proposes/applies improvements.

    The engine maintains a population of graph configurations and
    uses evolutionary/bandit algorithms to find optimal configurations
    for different context types.
    """

    def __init__(
        self,
        evaluation_window: int = 100,
        improvement_interval: int = 50,
        exploration_constant: float = 1.414,
        min_samples_for_topology: int = 200,
        persistence_path: Optional[str] = None,
    ):
        self.evaluation_window = evaluation_window
        self.improvement_interval = improvement_interval
        self.exploration_constant = exploration_constant
        self.min_samples_for_topology = min_samples_for_topology
        self.persistence_path = persistence_path

        # Configuration population
        self._configurations: Dict[str, GraphConfiguration] = {}
        self._context_configs: Dict[str, List[str]] = defaultdict(list)

        # Performance tracking
        self._request_log: List[Dict[str, Any]] = []
        self._performance_history: List[PerformanceSnapshot] = []
        self._atom_contribution_scores: Dict[str, List[float]] = defaultdict(list)

        # Improvement proposals
        self._pending_proposals: List[ImprovementProposal] = []
        self._applied_proposals: List[ImprovementProposal] = []

        # Counters
        self._total_requests = 0
        self._last_improvement_at = 0

        # Initialize default configuration
        self._init_default_configs()

        # Load state
        if persistence_path:
            self._load_state()

    def _init_default_configs(self) -> None:
        """Initialize the default configuration population."""
        # Baseline: full DAG
        self._configurations["full_dag"] = GraphConfiguration(
            config_id="full_dag",
            description="Full 30-atom DAG",
            level=ImprovementLevel.TOPOLOGY,
            active_atoms=["all"],
        )

        # Minimal: core atoms only
        self._configurations["minimal"] = GraphConfiguration(
            config_id="minimal",
            description="Core 5 atoms only",
            level=ImprovementLevel.TOPOLOGY,
            active_atoms=[
                "atom_user_state", "atom_regulatory_focus",
                "atom_mechanism_activation", "atom_message_framing",
                "atom_ad_selection",
            ],
        )

        # Game theory focused
        self._configurations["game_theory_focus"] = GraphConfiguration(
            config_id="game_theory_focus",
            description="Core + game theory atoms",
            level=ImprovementLevel.TOPOLOGY,
            active_atoms=[
                "atom_user_state", "atom_regulatory_focus",
                "atom_review_intelligence", "atom_mechanism_activation",
                "atom_signal_credibility", "atom_strategic_awareness",
                "atom_regret_anticipation", "atom_information_asymmetry",
                "atom_message_framing", "atom_ad_selection",
            ],
        )

        # Neuro focused
        self._configurations["neuro_focus"] = GraphConfiguration(
            config_id="neuro_focus",
            description="Core + neuro/info theory atoms",
            level=ImprovementLevel.TOPOLOGY,
            active_atoms=[
                "atom_user_state", "atom_regulatory_focus",
                "atom_review_intelligence", "atom_mechanism_activation",
                "atom_narrative_identity", "atom_decision_entropy",
                "atom_predictive_error", "atom_cognitive_load",
                "atom_coherence_optimization",
                "atom_message_framing", "atom_ad_selection",
            ],
        )

    def record_request(
        self,
        config_id: str,
        context_bucket: str,
        atoms_activated: List[str],
        quality_score: float,
        latency_ms: float,
        success: bool,
        atom_contributions: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Record the outcome of a request for performance tracking.

        This is the primary learning signal for the self-improvement engine.
        """
        self._total_requests += 1

        # Update configuration stats
        if config_id in self._configurations:
            config = self._configurations[config_id]
            config.times_selected += 1
            reward = quality_score if success else 0.0
            config.total_reward += reward
            config.avg_quality = (
                config.avg_quality * 0.95 + quality_score * 0.05
            )
            config.avg_latency_ms = (
                config.avg_latency_ms * 0.95 + latency_ms * 0.05
            )

        # Track atom contributions
        if atom_contributions:
            for atom_id, contribution in atom_contributions.items():
                self._atom_contribution_scores[atom_id].append(contribution)
                # Keep only recent scores
                if len(self._atom_contribution_scores[atom_id]) > 500:
                    self._atom_contribution_scores[atom_id] = (
                        self._atom_contribution_scores[atom_id][-500:]
                    )

        # Log request
        self._request_log.append({
            "timestamp": time.time(),
            "config_id": config_id,
            "context_bucket": context_bucket,
            "atoms_activated": atoms_activated,
            "quality": quality_score,
            "latency_ms": latency_ms,
            "success": success,
        })

        # Trim log
        if len(self._request_log) > self.evaluation_window * 5:
            self._request_log = self._request_log[-self.evaluation_window * 5:]

        # Check if improvement cycle is due
        if (self._total_requests - self._last_improvement_at) >= self.improvement_interval:
            self._run_improvement_cycle()
            self._last_improvement_at = self._total_requests

    def select_configuration(
        self,
        context_bucket: str,
    ) -> GraphConfiguration:
        """
        Select the best configuration for this context using UCB1.

        UCB1 balances exploitation (known-good configs) with exploration
        (under-tested configs).
        """
        configs = list(self._configurations.values())
        total_pulls = sum(c.times_selected for c in configs)

        if total_pulls == 0:
            # No data yet — return full DAG
            return self._configurations["full_dag"]

        # Compute UCB1 scores
        for config in configs:
            if config.times_selected == 0:
                config.ucb_score = float("inf")
            else:
                exploitation = config.mean_reward
                exploration = self.exploration_constant * math.sqrt(
                    math.log(total_pulls) / config.times_selected
                )
                config.ucb_score = exploitation + exploration

        # Select highest UCB score
        best = max(configs, key=lambda c: c.ucb_score)

        logger.debug(
            f"Self-improvement selected config: {best.config_id} "
            f"(UCB={best.ucb_score:.3f}, pulls={best.times_selected})"
        )

        return best

    def get_atom_value_rankings(self) -> List[Tuple[str, float, float]]:
        """
        Get atoms ranked by their contribution value.

        Returns: [(atom_id, mean_contribution, contribution_variance)]
        """
        rankings = []
        for atom_id, scores in self._atom_contribution_scores.items():
            if len(scores) >= 10:
                rankings.append((
                    atom_id,
                    float(np.mean(scores)),
                    float(np.std(scores)),
                ))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def propose_improvements(self) -> List[ImprovementProposal]:
        """
        Analyze current performance and propose improvements.

        Returns a list of proposals that can be reviewed/applied.
        """
        proposals = []

        # Level 1: Parameter improvements (always applicable)
        param_proposals = self._propose_parameter_improvements()
        proposals.extend(param_proposals)

        # Level 2: Topology improvements (need enough data)
        if self._total_requests >= self.min_samples_for_topology:
            topo_proposals = self._propose_topology_improvements()
            proposals.extend(topo_proposals)

        # Level 3: Strategy improvements
        if self._total_requests >= self.min_samples_for_topology * 2:
            strat_proposals = self._propose_strategy_improvements()
            proposals.extend(strat_proposals)

        self._pending_proposals.extend(proposals)
        return proposals

    def get_performance_report(self) -> Dict[str, Any]:
        """Get a comprehensive performance report."""
        if not self._request_log:
            return {"total_requests": 0}

        recent = self._request_log[-self.evaluation_window:]

        config_stats = {}
        for config_id, config in self._configurations.items():
            if config.times_selected > 0:
                config_stats[config_id] = {
                    "times_selected": config.times_selected,
                    "mean_reward": config.mean_reward,
                    "avg_quality": config.avg_quality,
                    "avg_latency_ms": config.avg_latency_ms,
                    "ucb_score": config.ucb_score,
                }

        return {
            "total_requests": self._total_requests,
            "recent_success_rate": np.mean([
                1 if r["success"] else 0 for r in recent
            ]),
            "recent_avg_quality": np.mean([r["quality"] for r in recent]),
            "recent_avg_latency_ms": np.mean([r["latency_ms"] for r in recent]),
            "configurations": config_stats,
            "atom_rankings": self.get_atom_value_rankings()[:10],
            "pending_proposals": len(self._pending_proposals),
            "applied_proposals": len(self._applied_proposals),
            "improvement_cycles": len(self._performance_history),
        }

    def export_state(self) -> Dict[str, Any]:
        """Export engine state for persistence."""
        return {
            "configurations": {
                cid: {
                    "config_id": c.config_id,
                    "description": c.description,
                    "level": c.level.value,
                    "active_atoms": c.active_atoms,
                    "times_selected": c.times_selected,
                    "total_reward": c.total_reward,
                    "avg_quality": c.avg_quality,
                    "avg_latency_ms": c.avg_latency_ms,
                }
                for cid, c in self._configurations.items()
            },
            "atom_contributions": {
                k: v[-100:] for k, v in self._atom_contribution_scores.items()
            },
            "total_requests": self._total_requests,
            "performance_snapshots": [
                {
                    "timestamp": s.timestamp,
                    "success_rate": s.success_rate,
                    "avg_quality": s.avg_quality,
                    "avg_latency_ms": s.avg_latency_ms,
                }
                for s in self._performance_history[-50:]
            ],
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import previously saved state."""
        for cid, cdata in state.get("configurations", {}).items():
            if cid in self._configurations:
                config = self._configurations[cid]
                config.times_selected = cdata.get("times_selected", 0)
                config.total_reward = cdata.get("total_reward", 0.0)
                config.avg_quality = cdata.get("avg_quality", 0.0)
                config.avg_latency_ms = cdata.get("avg_latency_ms", 0.0)

        for atom_id, scores in state.get("atom_contributions", {}).items():
            self._atom_contribution_scores[atom_id] = scores

        self._total_requests = state.get("total_requests", 0)
        logger.info(f"Imported self-improvement state ({self._total_requests} requests)")

    # =========================================================================
    # PRIVATE: IMPROVEMENT CYCLE
    # =========================================================================

    def _run_improvement_cycle(self) -> None:
        """Run one improvement cycle — analyze and apply improvements."""
        recent = self._request_log[-self.evaluation_window:]
        if not recent:
            return

        # Take performance snapshot
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            total_requests=self._total_requests,
            success_rate=np.mean([1 if r["success"] else 0 for r in recent]),
            avg_quality=np.mean([r["quality"] for r in recent]),
            avg_latency_ms=np.mean([r["latency_ms"] for r in recent]),
            atoms_per_request=np.mean([
                len(r["atoms_activated"]) for r in recent
            ]),
        )
        self._performance_history.append(snapshot)

        # Check for performance regression
        if len(self._performance_history) >= 2:
            prev = self._performance_history[-2]
            if snapshot.avg_quality < prev.avg_quality * 0.9:
                logger.warning(
                    f"Performance regression detected: "
                    f"quality {prev.avg_quality:.3f} → {snapshot.avg_quality:.3f}"
                )
                # Roll back to previous configuration
                self._rollback_last_change()
                return

        # Propose and auto-apply parameter improvements
        proposals = self.propose_improvements()
        for proposal in proposals:
            if proposal.level == ImprovementLevel.PARAMETER and proposal.confidence > 0.7:
                self._apply_proposal(proposal)

        # Persist state
        if self.persistence_path:
            self._save_state()

        logger.info(
            f"Self-improvement cycle #{len(self._performance_history)}: "
            f"quality={snapshot.avg_quality:.3f}, "
            f"success={snapshot.success_rate:.2%}, "
            f"latency={snapshot.avg_latency_ms:.0f}ms"
        )

    def _propose_parameter_improvements(self) -> List[ImprovementProposal]:
        """Propose parameter-level improvements."""
        proposals = []
        recent = self._request_log[-self.evaluation_window:]
        if not recent:
            return proposals

        # Check if too many atoms are running (latency issue)
        avg_atoms = np.mean([len(r["atoms_activated"]) for r in recent])
        avg_latency = np.mean([r["latency_ms"] for r in recent])

        if avg_latency > 3000 and avg_atoms > 15:
            proposals.append(ImprovementProposal(
                proposal_id=f"param_prune_{self._total_requests}",
                level=ImprovementLevel.PARAMETER,
                description="Increase activation threshold to reduce latency",
                rationale=f"Avg latency {avg_latency:.0f}ms with {avg_atoms:.0f} atoms",
                changes={"activation_threshold_delta": +0.05},
                expected_latency_delta_ms=-500,
                confidence=0.7,
            ))

        # Check if too few atoms (quality issue)
        avg_quality = np.mean([r["quality"] for r in recent])
        if avg_quality < 0.4 and avg_atoms < 10:
            proposals.append(ImprovementProposal(
                proposal_id=f"param_expand_{self._total_requests}",
                level=ImprovementLevel.PARAMETER,
                description="Decrease activation threshold to improve quality",
                rationale=f"Avg quality {avg_quality:.2f} with only {avg_atoms:.0f} atoms",
                changes={"activation_threshold_delta": -0.05},
                expected_quality_delta=0.1,
                confidence=0.6,
            ))

        return proposals

    def _propose_topology_improvements(self) -> List[ImprovementProposal]:
        """Propose topology-level improvements based on atom contribution analysis."""
        proposals = []
        rankings = self.get_atom_value_rankings()

        if not rankings:
            return proposals

        # Find consistently low-value atoms
        low_value_atoms = [
            (atom_id, mean, std)
            for atom_id, mean, std in rankings
            if mean < 0.2 and std < 0.15  # Low mean AND low variance
        ]

        if low_value_atoms:
            atoms_to_prune = [a[0] for a in low_value_atoms[:3]]
            proposals.append(ImprovementProposal(
                proposal_id=f"topo_prune_{self._total_requests}",
                level=ImprovementLevel.TOPOLOGY,
                description=f"Prune low-value atoms: {atoms_to_prune}",
                rationale="These atoms consistently contribute < 0.2 to quality",
                changes={"prune_atoms": atoms_to_prune},
                expected_latency_delta_ms=-200 * len(atoms_to_prune),
                confidence=0.65,
            ))

        # Find high-value atom combinations
        # (atoms that co-occur in successful requests)
        recent_success = [
            r for r in self._request_log[-500:]
            if r["success"] and r["quality"] > 0.6
        ]

        if len(recent_success) >= 20:
            atom_co_occurrence = defaultdict(int)
            for req in recent_success:
                atoms = req["atoms_activated"]
                for i in range(len(atoms)):
                    for j in range(i + 1, len(atoms)):
                        pair = tuple(sorted([atoms[i], atoms[j]]))
                        atom_co_occurrence[pair] += 1

            # Find strongly co-occurring pairs
            top_pairs = sorted(
                atom_co_occurrence.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]

            if top_pairs:
                synergy_atoms = set()
                for (a1, a2), count in top_pairs:
                    synergy_atoms.add(a1)
                    synergy_atoms.add(a2)

                new_config_id = f"synergy_{self._total_requests}"
                proposals.append(ImprovementProposal(
                    proposal_id=f"topo_synergy_{self._total_requests}",
                    level=ImprovementLevel.TOPOLOGY,
                    description=f"Create synergy configuration with top co-occurring atoms",
                    rationale=f"Found {len(top_pairs)} high-value atom pairs",
                    changes={
                        "new_config": {
                            "config_id": new_config_id,
                            "active_atoms": list(synergy_atoms),
                        }
                    },
                    expected_quality_delta=0.05,
                    confidence=0.6,
                ))

        return proposals

    def _propose_strategy_improvements(self) -> List[ImprovementProposal]:
        """Propose strategy-level improvements."""
        proposals = []

        # Analyze which configurations work for which contexts
        context_performance = defaultdict(lambda: defaultdict(list))
        for req in self._request_log[-1000:]:
            context_performance[req["context_bucket"]][req["config_id"]].append(
                req["quality"]
            )

        # Find contexts where no config is performing well
        for bucket, configs in context_performance.items():
            best_quality = max(
                np.mean(qualities) for qualities in configs.values()
            )
            if best_quality < 0.4:
                proposals.append(ImprovementProposal(
                    proposal_id=f"strat_novel_{self._total_requests}_{bucket}",
                    level=ImprovementLevel.STRATEGY,
                    description=f"Need novel strategy for context: {bucket}",
                    rationale=f"Best config quality is only {best_quality:.2f}",
                    changes={"context_bucket": bucket},
                    expected_quality_delta=0.15,
                    confidence=0.4,
                ))

        return proposals

    def _apply_proposal(self, proposal: ImprovementProposal) -> None:
        """Apply an approved improvement proposal."""
        proposal.approved = True

        if proposal.level == ImprovementLevel.PARAMETER:
            threshold_delta = proposal.changes.get("activation_threshold_delta", 0)
            if threshold_delta != 0:
                # Store as parameter override in all configurations
                for config in self._configurations.values():
                    current = config.parameter_overrides.get(
                        "activation_threshold_delta", 0
                    )
                    config.parameter_overrides["activation_threshold_delta"] = (
                        current + threshold_delta
                    )

        elif proposal.level == ImprovementLevel.TOPOLOGY:
            new_config = proposal.changes.get("new_config")
            if new_config:
                config_id = new_config["config_id"]
                self._configurations[config_id] = GraphConfiguration(
                    config_id=config_id,
                    description=f"Auto-generated synergy config",
                    level=ImprovementLevel.TOPOLOGY,
                    active_atoms=new_config["active_atoms"],
                )

        self._applied_proposals.append(proposal)
        logger.info(f"Applied improvement: {proposal.description}")

    def _rollback_last_change(self) -> None:
        """Roll back the most recent improvement."""
        if not self._applied_proposals:
            return

        last = self._applied_proposals.pop()
        logger.warning(f"Rolling back improvement: {last.description}")

    def _save_state(self) -> None:
        """Persist state to disk."""
        if not self.persistence_path:
            return
        path = Path(self.persistence_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.export_state(), f, indent=2)

    def _load_state(self) -> None:
        """Load state from disk."""
        if not self.persistence_path:
            return
        path = Path(self.persistence_path)
        if path.exists():
            try:
                with open(path) as f:
                    state = json.load(f)
                self.import_state(state)
            except Exception as e:
                logger.warning(f"Failed to load self-improvement state: {e}")
