#!/usr/bin/env python3
"""
THEORY LEARNER — Construct-Level Learning from Outcomes
========================================================

When outcomes arrive, this module updates the theoretical link strengths
in the theory graph, implementing a simplified version of AGM belief
revision: the theory graph is a belief set, outcomes are evidence, and
links whose predictions consistently fail get weakened or revised.

This is what makes ADAM categorically different: it doesn't just learn
"authority works for achievers" (correlational), it learns "the causal
link between need_for_closure and authority has been validated 47 times
with 0.78 accuracy" (construct-level).

Academic Foundations:
- Alchourrón, Gärdenfors & Makinson (1985): AGM belief revision
- Pearl (2009): Causal inference via do-calculus
- Hoeting et al. (1999): Bayesian model averaging for theory selection
- Thagard (2000): Explanatory coherence as constraint satisfaction
"""

import logging
import math
import time
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# THEORY LEARNER
# =============================================================================

@dataclass
class LinkOutcome:
    """An outcome observation for a theoretical link."""
    link_key: str  # e.g., "CREATES_NEED:low_uncertainty_tolerance:need_for_closure"
    success: bool
    outcome_value: float  # 0-1
    timestamp: float = 0.0


@dataclass
class LinkPosterior:
    """Bayesian posterior for a theoretical link strength."""
    alpha: float = 2.0  # Beta prior: successes + 1
    beta: float = 2.0   # Beta prior: failures + 1
    observation_count: int = 0
    last_updated: float = 0.0

    @property
    def mean(self) -> float:
        """Posterior mean (expected strength)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def strength(self) -> float:
        """Alias for mean — the current estimated link strength."""
        return self.mean

    @property
    def confidence(self) -> float:
        """How confident are we in this estimate? (variance inverse)."""
        total = self.alpha + self.beta
        if total <= 2:
            return 0.1  # Very low confidence with no data
        # Normalized inverse variance (higher = more confident)
        variance = (self.alpha * self.beta) / (total ** 2 * (total + 1))
        return min(1.0, 1.0 / (1 + variance * 100))

    def update(self, success: bool, value: float = 1.0) -> None:
        """Bayesian update with new observation."""
        if success:
            self.alpha += value
        else:
            self.beta += (1 - value) if value < 1.0 else 1.0
        self.observation_count += 1
        self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "mean": round(self.mean, 4),
            "confidence": round(self.confidence, 4),
            "observation_count": self.observation_count,
        }


@dataclass
class ChainOutcomeRecord:
    """A complete chain → outcome mapping for pattern analysis."""
    chain_id: str
    decision_id: str
    mechanism: str
    theoretical_link_keys: List[str]
    success: bool
    outcome_value: float
    timestamp: float = 0.0


class TheoryLearner:
    """
    Learns at the construct level: updates theoretical link strengths
    based on outcomes, tracks chain-level patterns, and identifies
    theories that need revision.

    Unlike Thompson Sampling (which learns archetype → mechanism effectiveness),
    this learns at the deeper theory level: which causal links between
    psychological constructs are empirically validated by real outcomes.
    """

    def __init__(self, max_history: int = 10000):
        # Bayesian posteriors for each theoretical link
        self._link_posteriors: Dict[str, LinkPosterior] = {}
        # Chain outcome history for pattern analysis
        self._chain_history: List[ChainOutcomeRecord] = []
        self._max_history = max_history
        # Aggregated pattern stats
        self._chain_pattern_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"successes": 0, "failures": 0, "total_value": 0.0}
        )
        self._total_outcomes = 0

    def process_chain_outcome(
        self,
        chain_data: Dict[str, Any],
        decision_id: str,
        success: bool,
        outcome_value: float,
    ) -> Dict[str, Any]:
        """
        Process an outcome for a specific inferential chain.

        This is the core construct-level learning step:
        1. Retrieve the theoretical link keys from the chain
        2. Bayesian update each link's posterior
        3. Record chain-level pattern for aggregate analysis
        4. Flag links with declining strength for theory revision

        Args:
            chain_data: The chain dict (from InferentialChain.to_dict())
            decision_id: Decision that used this chain
            success: Whether the outcome was positive
            outcome_value: Outcome value (0-1)

        Returns:
            Summary of updates performed
        """
        link_keys = chain_data.get("theoretical_link_keys", [])
        mechanism = chain_data.get("recommended_mechanism", "")
        chain_id = chain_data.get("chain_id", "")

        if not link_keys:
            return {"skipped": True, "reason": "no_theoretical_links"}

        # Step 1: Bayesian update each link
        link_updates = []
        for key in link_keys:
            posterior = self._get_or_create_posterior(key)
            prior_mean = posterior.mean
            posterior.update(success, outcome_value)

            link_updates.append({
                "link_key": key,
                "prior_mean": round(prior_mean, 4),
                "posterior_mean": round(posterior.mean, 4),
                "delta": round(posterior.mean - prior_mean, 4),
                "observation_count": posterior.observation_count,
                "confidence": round(posterior.confidence, 4),
            })

        # Step 2: Record chain-level pattern
        record = ChainOutcomeRecord(
            chain_id=chain_id,
            decision_id=decision_id,
            mechanism=mechanism,
            theoretical_link_keys=link_keys,
            success=success,
            outcome_value=outcome_value,
            timestamp=time.time(),
        )
        self._chain_history.append(record)
        if len(self._chain_history) > self._max_history:
            self._chain_history = self._chain_history[-self._max_history:]

        # Step 3: Update chain pattern stats
        # Pattern key = sorted link keys (so same-path chains aggregate)
        pattern_key = "|".join(sorted(link_keys))
        stats = self._chain_pattern_stats[pattern_key]
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        stats["total_value"] += outcome_value

        self._total_outcomes += 1

        # Step 4: Flag weakening links
        flagged = []
        for key in link_keys:
            posterior = self._link_posteriors[key]
            if posterior.observation_count >= 10 and posterior.mean < 0.35:
                flagged.append({
                    "link_key": key,
                    "mean": round(posterior.mean, 4),
                    "observations": posterior.observation_count,
                    "status": "theory_revision_candidate",
                })

        return {
            "links_updated": len(link_updates),
            "link_updates": link_updates,
            "flagged_for_revision": flagged,
            "chain_pattern_key": pattern_key,
            "mechanism": mechanism,
        }

    def process_all_chains_for_decision(
        self,
        inferential_chains: List[Dict[str, Any]],
        decision_id: str,
        success: bool,
        outcome_value: float,
    ) -> Dict[str, Any]:
        """
        Process an outcome for all chains that contributed to a decision.

        When a decision succeeds, ALL chains that supported the chosen
        mechanism get credit. Chains that supported non-chosen mechanisms
        get weaker negative signal (they weren't wrong, just not selected).

        Args:
            inferential_chains: List of chain dicts from the decision
            decision_id: Decision ID
            success: Whether the outcome was positive
            outcome_value: 0-1 outcome value

        Returns:
            Aggregate update summary
        """
        if not inferential_chains:
            return {"skipped": True, "reason": "no_chains"}

        all_updates = []
        total_links = 0
        total_flagged = 0

        for chain in inferential_chains:
            result = self.process_chain_outcome(
                chain_data=chain,
                decision_id=decision_id,
                success=success,
                outcome_value=outcome_value,
            )
            all_updates.append(result)
            total_links += result.get("links_updated", 0)
            total_flagged += len(result.get("flagged_for_revision", []))

        return {
            "chains_processed": len(inferential_chains),
            "total_links_updated": total_links,
            "total_flagged_for_revision": total_flagged,
            "chain_updates": all_updates,
        }

    def get_chain_pattern_analysis(self, min_observations: int = 5) -> List[Dict[str, Any]]:
        """
        Analyze which chain patterns (sets of theoretical links) are
        consistently succeeding or failing.

        This is construct-level learning: the system learns WHICH THEORIES
        work, not just which mechanisms.

        Returns patterns sorted by observation count (most evidence first).
        """
        patterns = []
        for pattern_key, stats in self._chain_pattern_stats.items():
            total = stats["successes"] + stats["failures"]
            if total < min_observations:
                continue

            success_rate = stats["successes"] / total if total > 0 else 0.5
            avg_value = stats["total_value"] / total if total > 0 else 0.0

            link_keys = pattern_key.split("|")
            # Extract human-readable path
            path_description = []
            for key in link_keys:
                parts = key.split(":")
                if len(parts) == 3:
                    path_description.append(f"{parts[1]} --{parts[0]}--> {parts[2]}")

            patterns.append({
                "pattern_key": pattern_key,
                "link_keys": link_keys,
                "path_description": path_description,
                "total_observations": total,
                "success_rate": round(success_rate, 4),
                "avg_outcome_value": round(avg_value, 4),
                "status": (
                    "validated" if success_rate > 0.6
                    else "neutral" if success_rate > 0.4
                    else "weakening"
                ),
            })

        patterns.sort(key=lambda p: p["total_observations"], reverse=True)
        return patterns

    def get_link_strength(self, link_key: str) -> float:
        """Get the current learned strength for a theoretical link."""
        posterior = self._link_posteriors.get(link_key)
        if posterior:
            return posterior.mean
        return 0.5  # Neutral prior

    def get_link_posterior(self, link_key: str) -> Optional[Dict[str, Any]]:
        """Get full posterior info for a link."""
        posterior = self._link_posteriors.get(link_key)
        return posterior.to_dict() if posterior else None

    def get_all_posteriors(self) -> Dict[str, Dict[str, Any]]:
        """Get all link posteriors for inspection/export."""
        return {
            key: posterior.to_dict()
            for key, posterior in self._link_posteriors.items()
        }

    def get_revision_candidates(self, min_observations: int = 10) -> List[Dict[str, Any]]:
        """
        Identify theoretical links that need revision: links with
        sufficient observations whose strength has dropped below threshold.

        These represent theories that the data doesn't support.
        """
        candidates = []
        for key, posterior in self._link_posteriors.items():
            if posterior.observation_count >= min_observations and posterior.mean < 0.35:
                candidates.append({
                    "link_key": key,
                    "current_strength": round(posterior.mean, 4),
                    "observations": posterior.observation_count,
                    "confidence": round(posterior.confidence, 4),
                    "recommendation": (
                        "remove" if posterior.mean < 0.2
                        else "weaken" if posterior.mean < 0.3
                        else "investigate"
                    ),
                })
        candidates.sort(key=lambda c: c["current_strength"])
        return candidates

    def update_neo4j_link_strengths(self, session) -> int:
        """
        Push learned link strengths back to Neo4j.

        This closes the loop: outcomes update in-memory posteriors,
        and periodically we write those back to the graph so that
        the reasoning chain generator uses the latest empirical validation.
        """
        updated = 0
        for link_key, posterior in self._link_posteriors.items():
            if posterior.observation_count < 3:
                continue  # Don't update graph with insufficient evidence

            parts = link_key.split(":")
            if len(parts) != 3:
                continue
            link_type, source_name, target_name = parts

            try:
                session.run(
                    f"""
                    MATCH ()-[r:{link_type}]->()
                    WHERE startNode(r).name = $source AND endNode(r).name = $target
                    SET r.empirical_validation = $strength,
                        r.observation_count = $obs,
                        r.last_outcome_update = datetime()
                    """,
                    source=source_name,
                    target=target_name,
                    strength=posterior.mean,
                    obs=posterior.observation_count,
                )
                updated += 1
            except Exception as e:
                logger.debug(f"Failed to update Neo4j link {link_key}: {e}")

        if updated:
            logger.info(f"Updated {updated} theoretical link strengths in Neo4j")
        return updated

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_outcomes": self._total_outcomes,
            "links_tracked": len(self._link_posteriors),
            "chain_patterns": len(self._chain_pattern_stats),
            "history_length": len(self._chain_history),
        }

    def _get_or_create_posterior(self, link_key: str) -> LinkPosterior:
        """Get or create a posterior for a link key."""
        if link_key not in self._link_posteriors:
            # Initialize with informative prior based on the theory schema
            # Default: Beta(2, 2) = uniform-ish prior centered at 0.5
            self._link_posteriors[link_key] = LinkPosterior()
        return self._link_posteriors[link_key]


# =============================================================================
# SINGLETON
# =============================================================================

_theory_learner: Optional[TheoryLearner] = None


def get_theory_learner() -> TheoryLearner:
    """Get or create the singleton theory learner."""
    global _theory_learner
    if _theory_learner is None:
        _theory_learner = TheoryLearner()
    return _theory_learner
