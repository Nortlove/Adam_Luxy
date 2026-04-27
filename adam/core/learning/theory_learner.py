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
        """Bayesian update with new observation.

        Legacy signature — kept for backwards compatibility with callers
        that still reason in boolean-success terms. New code should use
        `update_signed()` which carries magnitude + direction and can
        represent negative ethics-gate outcomes (refund, complaint,
        regret) with the correct evidentiary weight.
        """
        if success:
            self.alpha += value
        else:
            self.beta += (1 - value) if value < 1.0 else 1.0
        self.observation_count += 1
        self.last_updated = time.time()

    def update_signed(self, signed_reward: float, weight: float = 1.0) -> None:
        """Bayesian update from a signed reward.

        This is the correct entry point for learning updates in the
        Phase 1 fitness-function refactor. A signed reward comes from
        `adam.core.outcome_types.compute_signed_reward()` and carries
        both direction (+/-) and magnitude (how strongly this outcome
        should move the posterior).

        Positive signed_reward is evidence FOR the link holding —
        alpha increments by the magnitude. Negative is evidence
        AGAINST — beta increments by the magnitude. Zero is a no-op
        (unknown outcome type, no update applied).

        `weight` is an additional multiplier, typically the Enhancement
        #34 processing_depth_weight that down-weights unprocessed
        impressions so they don't drive learning as strongly as
        deliberate engagements.

        Why this matters (Foundation §7 rule 11):
          The fitness function IS the ethics. If beta only ever
          increments from silent non-engagement (skip, bounce), the
          system cannot distinguish "user ignored this ad" from
          "user bought then demanded a refund." Selection pressure
          then rewards anything that converts, regardless of whether
          the conversion held. This method is how the platform
          represents the difference.
        """
        if signed_reward == 0.0:
            # Unknown outcome type — no update. resolve_outcome_type()
            # already warned at compute time.
            return

        magnitude = abs(signed_reward) * weight
        if signed_reward > 0:
            self.alpha += magnitude
        else:
            self.beta += magnitude
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
        maybe_persist_theory_learner(self)  # rate-limited Redis write

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

    def process_chain_outcome_signed(
        self,
        chain_data: Dict[str, Any],
        decision_id: str,
        signed_reward: float,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Process an outcome using a signed reward.

        This is the Phase 1 ethics-gate-aware variant of
        `process_chain_outcome`. A `signed_reward` comes from
        `adam.core.outcome_types.compute_signed_reward()` and carries:

          * direction — positive rewards increment alpha on each link
            posterior; negative rewards increment beta.
          * magnitude — how strongly this outcome should move the
            posterior. A REFUND (magnitude 3.0) updates the posterior
            three times as strongly as a baseline CONVERSION.

        `weight` is an additional scalar (typically processing_depth_
        weight) that down-weights unprocessed impressions. It stacks
        multiplicatively with the magnitude baked into signed_reward.

        When signed_reward is 0 (unknown outcome type), nothing is
        updated — the previous code-path silently treated unknowns as
        "not success" which incorrectly credited them to beta. Silent
        coercion of unknowns is an antipattern; let them be no-ops and
        let the warning surface upstream.

        Why this variant exists (Foundation §7 rule 11):
          The legacy `process_chain_outcome(success, outcome_value)`
          cannot distinguish a silent skip from an explicit refund —
          both set success=False. The learning loop therefore treats
          them identically. For the fitness function to embody the
          ethics, refunds must move posteriors 3× more strongly than
          skips, and regret/complaint signals must subtract from the
          evidence they fabricated, not just fail to add.
        """
        link_keys = chain_data.get("theoretical_link_keys", [])
        mechanism = chain_data.get("recommended_mechanism", "")
        chain_id = chain_data.get("chain_id", "")

        if not link_keys:
            return {"skipped": True, "reason": "no_theoretical_links"}

        if signed_reward == 0.0:
            return {"skipped": True, "reason": "unknown_outcome_type_zero_reward"}

        # Derive a backward-compat boolean and outcome value for the
        # chain-level pattern stats and history record. Magnitude is
        # preserved at the link-posterior level via update_signed.
        success = signed_reward > 0
        outcome_value = min(1.0, abs(signed_reward))

        # Step 1: Bayesian update each link using SIGNED reward
        link_updates = []
        for key in link_keys:
            posterior = self._get_or_create_posterior(key)
            prior_mean = posterior.mean
            posterior.update_signed(signed_reward, weight=weight)

            link_updates.append({
                "link_key": key,
                "prior_mean": round(prior_mean, 4),
                "posterior_mean": round(posterior.mean, 4),
                "delta": round(posterior.mean - prior_mean, 4),
                "signed_reward": round(signed_reward, 4),
                "weight": round(weight, 4),
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

        # Step 3: Update chain pattern stats. A negative ethics-gate
        # signal (refund, complaint, regret) counts as a failure
        # observation AND its magnitude biases the aggregate — a refund
        # contributes more strongly than a plain skip.
        pattern_key = "|".join(sorted(link_keys))
        stats = self._chain_pattern_stats[pattern_key]
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        stats["total_value"] += outcome_value

        self._total_outcomes += 1
        maybe_persist_theory_learner(self)  # rate-limited Redis write

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
            "reward_direction": "positive" if success else "negative",
            "signed_reward": round(signed_reward, 4),
        }

    def process_all_chains_for_decision_signed(
        self,
        inferential_chains: List[Dict[str, Any]],
        decision_id: str,
        signed_reward: float,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Signed-reward variant of `process_all_chains_for_decision`.

        Use this entry point when the outcome handler has computed a
        signed reward from `compute_signed_reward()`. All downstream
        link-posterior updates go through `update_signed()` with
        correct direction and magnitude.
        """
        if not inferential_chains:
            return {"skipped": True, "reason": "no_chains"}

        if signed_reward == 0.0:
            return {"skipped": True, "reason": "unknown_outcome_type_zero_reward"}

        all_updates = []
        total_links = 0
        total_flagged = 0

        for chain in inferential_chains:
            result = self.process_chain_outcome_signed(
                chain_data=chain,
                decision_id=decision_id,
                signed_reward=signed_reward,
                weight=weight,
            )
            all_updates.append(result)
            total_links += result.get("links_updated", 0)
            total_flagged += len(result.get("flagged_for_revision", []))

        return {
            "chains_processed": len(inferential_chains),
            "total_links_updated": total_links,
            "total_flagged_for_revision": total_flagged,
            "reward_direction": "positive" if signed_reward > 0 else "negative",
            "signed_reward": round(signed_reward, 4),
            "chain_updates": all_updates,
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
# PERSISTENCE — survive backend restarts
# =============================================================================
#
# Without persistence, every backend restart wiped accumulated theory:
# Bayesian posteriors on every theoretical link, chain-outcome history,
# pattern-stat aggregates, total observation count. Restarts happen
# during deployments, crashes, scheduled cycles — the platform was
# silently losing every accumulated belief on each cycle. The "system
# gets stronger with every outcome" claim was true within a single
# process lifetime; meaningless across restart boundaries.
#
# This block adds Redis-backed persistence:
#   - to_state_dict / from_state_dict: full state ↔ JSON
#   - save_to_redis: write current state under a known key
#   - load_from_redis: read state on init
#   - get_theory_learner now loads on first call
#
# Save cadence: every _PERSIST_EVERY_N_UPDATES outcome (default 10).
# Higher cadence = more Redis writes; lower = more risk of loss on
# unexpected shutdown. 10 is a defensible default for the pilot —
# adjusts via env if production traffic warrants.

import json
import os

_REDIS_KEY = "adam:theory_learner:state:v1"
_PERSIST_EVERY_N_UPDATES = int(
    os.environ.get("THEORY_LEARNER_PERSIST_EVERY_N", "10")
)


def _theory_learner_to_state_dict(learner: TheoryLearner) -> Dict[str, Any]:
    """Serialize a TheoryLearner to a JSON-able dict.

    Captures every piece of state that a fresh learner cannot
    reconstruct: link posteriors (Beta α/β, observation counts,
    last-updated timestamps), chain history, pattern-stat aggregates,
    total outcomes counter.
    """
    return {
        "schema_version": 1,
        "link_posteriors": {
            key: {
                "alpha": p.alpha,
                "beta": p.beta,
                "observation_count": p.observation_count,
                "last_updated": p.last_updated,
            }
            for key, p in learner._link_posteriors.items()
        },
        "chain_history": [
            {
                "chain_id": r.chain_id,
                "decision_id": r.decision_id,
                "mechanism": r.mechanism,
                "theoretical_link_keys": list(r.theoretical_link_keys),
                "success": r.success,
                "outcome_value": r.outcome_value,
                "timestamp": r.timestamp,
            }
            for r in learner._chain_history
        ],
        "chain_pattern_stats": {
            key: dict(stats)
            for key, stats in learner._chain_pattern_stats.items()
        },
        "total_outcomes": learner._total_outcomes,
        "max_history": learner._max_history,
    }


def _theory_learner_load_state_dict(
    learner: TheoryLearner, state: Dict[str, Any],
) -> None:
    """Restore a TheoryLearner from a state dict produced by
    _theory_learner_to_state_dict.

    Tolerant of missing fields — newly-added state fields default to
    empty/zero rather than raising. Schema version is checked; mismatched
    versions log a warning and skip the load (the in-memory learner
    starts fresh, no corruption).
    """
    if state.get("schema_version") != 1:
        logger.warning(
            "TheoryLearner state schema mismatch (got %s, expected 1); "
            "skipping load",
            state.get("schema_version"),
        )
        return

    for key, raw in (state.get("link_posteriors") or {}).items():
        learner._link_posteriors[key] = LinkPosterior(
            alpha=float(raw.get("alpha", 2.0)),
            beta=float(raw.get("beta", 2.0)),
            observation_count=int(raw.get("observation_count", 0)),
            last_updated=float(raw.get("last_updated", 0.0)),
        )

    for raw in (state.get("chain_history") or []):
        learner._chain_history.append(
            ChainOutcomeRecord(
                chain_id=raw.get("chain_id", ""),
                decision_id=raw.get("decision_id", ""),
                mechanism=raw.get("mechanism", ""),
                theoretical_link_keys=list(raw.get("theoretical_link_keys") or []),
                success=bool(raw.get("success", False)),
                outcome_value=float(raw.get("outcome_value", 0.0)),
                timestamp=float(raw.get("timestamp", 0.0)),
            )
        )

    for key, stats in (state.get("chain_pattern_stats") or {}).items():
        learner._chain_pattern_stats[key] = {
            "successes": float(stats.get("successes", 0)),
            "failures": float(stats.get("failures", 0)),
            "total_value": float(stats.get("total_value", 0.0)),
        }

    learner._total_outcomes = int(state.get("total_outcomes", 0))


def _save_theory_learner_to_redis(learner: TheoryLearner) -> bool:
    """Write the learner's state to Redis under _REDIS_KEY.

    Returns True on success. Soft-fails: Redis errors log debug and
    return False. The in-memory learner continues operating; next save
    attempt will retry.
    """
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis is None:
            return False
        state = _theory_learner_to_state_dict(learner)
        redis.set(_REDIS_KEY, json.dumps(state, default=str))
        return True
    except Exception as exc:
        logger.debug("TheoryLearner save_to_redis failed: %s", exc)
        return False


def _load_theory_learner_from_redis(learner: TheoryLearner) -> bool:
    """Restore the learner's state from Redis on init.

    Returns True if state was loaded (Redis available and key present).
    Soft-fails on any error. The in-memory learner remains in its
    fresh-init state if load fails.
    """
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis is None:
            return False
        raw = redis.get(_REDIS_KEY)
        if not raw:
            return False
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        state = json.loads(raw)
        _theory_learner_load_state_dict(learner, state)
        logger.info(
            "TheoryLearner state restored from Redis: %d posteriors, "
            "%d chain records, %d total outcomes",
            len(learner._link_posteriors),
            len(learner._chain_history),
            learner._total_outcomes,
        )
        return True
    except Exception as exc:
        logger.debug("TheoryLearner load_from_redis failed: %s", exc)
        return False


# =============================================================================
# SINGLETON
# =============================================================================

_theory_learner: Optional[TheoryLearner] = None


def get_theory_learner() -> TheoryLearner:
    """Get or create the singleton theory learner.

    On first call, attempts to restore prior state from Redis under
    _REDIS_KEY. If Redis is unavailable or the key is empty, the
    learner starts fresh — same behavior as before persistence
    shipped.
    """
    global _theory_learner
    if _theory_learner is None:
        _theory_learner = TheoryLearner()
        _load_theory_learner_from_redis(_theory_learner)
    return _theory_learner


def maybe_persist_theory_learner(learner: TheoryLearner) -> None:
    """Save the learner's state to Redis if it's time per the
    configured cadence.

    Called from the update methods after each Bayesian update.
    Save cadence is every _PERSIST_EVERY_N_UPDATES outcomes.
    """
    if learner._total_outcomes <= 0:
        return
    if learner._total_outcomes % _PERSIST_EVERY_N_UPDATES == 0:
        _save_theory_learner_to_redis(learner)
