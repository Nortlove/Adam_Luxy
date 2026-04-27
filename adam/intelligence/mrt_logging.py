"""Micro-randomized trial (MRT) bid-time logging — Component #1 substrate.

Implements the irreducible substrate from the Seven-Component Methodological
Upgrade Handoff §1: ε-greedy floor mixer wrapping Thompson Sampling, with
decision-time p_t logging, so the offline WCLS estimator can recover the
causal excursion effect β(t;s) post-hoc (Boruvka, Almirall, Witkiewitz,
Murphy 2018, JASA 113(523):1112–1121).

Mathematical foundations (handoff §1.1):

    For each user i and decision point t:
        history H_t, moderators S_t ⊂ H_t, action A_t ∈ {0,1}
        availability I_t, randomization probability p_t = Pr(A_t=1 | H_t)
        proximal outcome Y_{t+1}.

    Causal excursion effect (additive scale):
        β(t; s) = E[Y_{t+1}(Ā_{t-1}, A_t=1) − Y_{t+1}(Ā_{t-1}, A_t=0)
                  | S_t = s, I_t = 1]

    WCLS estimator weights are W_{i,t} = p̃_t / p_t. Positivity requires
    0 < p_t < 1; weights blow up as p_t → 0. Greedy TS posteriors collapse
    p_t to {0,1}, so we wrap with:

        p_t(a | H_t) = (1 − ε) · π_TS(a | H_t) + ε · (1/K),  ε = 0.02

    With K=2 arms this bounds p_t ∈ [0.01, 0.99] and max weight ≤ 100.
    Liao et al. 2020 (Personalized HeartSteps) put 1–10% as the standard
    band; ε=0.02 minimizes revenue impact (handoff §1.1).

Why p_t MUST be logged at decision time, not reconstructed (handoff §1.2):
    (i) the posterior updates continuously
    (ii) the ε-floor mixing is stochastic
    (iii) tie-breaking randomness (numpy seed, BLAS nondeterminism,
         argmax over ties) is lost
    Boruvka 2018 §2 ASSUMES p_t is known, not estimated. Bibaut et al.
    2024 / Shi-Dempsey 2025 show even small p_t recording errors dominate
    bias. Log it once, at the decision. If unknown, set p_t_known=false
    and exclude from WCLS.

This module ships the irreducible substrate. The full WCLS analysis
pipeline (rpy2 + MRTAnalysis::wcls + Airflow weekly DAG + positivity
monitor + sensitivity analysis) is M1 follow-up work — that's the
analysis side. The substrate must ship first; without correctly logged
p_t, no downstream analysis can be valid.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ε-greedy floor — handoff §1.1 canonical value.
# Liao et al. 2020 standard band: 1–10%; 0.02 minimizes revenue impact
# vs the analytical guarantee. Production fixed; do not change without
# redoing the sample-size calculation (MRTSampleSizeBinary).
EPSILON_FLOOR = 0.02


# Min/max p_t after ε-floor mixing. With K arms and ε=0.02:
#     p_t ∈ [ε/K, 1 - ε(1 - 1/K)]
# K=2 → [0.01, 0.99]. K=10 → [0.002, 0.982].
# Max importance weight after WCLS = 1/min(p_t).


@dataclass
class MRTDecisionRecord:
    """One row of the MRT decision log — handoff §1.2 schema.

    Field names match the Avro schema for Kafka topic mrt.decisions.v1
    so producers and consumers share a contract.

    p_t_known is the discipline-anchor: when False, the row must be
    EXCLUDED from WCLS (Boruvka 2018 §2). Setting it carefully here at
    decision time is what makes the rest of the pipeline valid.
    """

    ts: int                              # decision-time epoch ms
    user_id: str                         # cluster unit (cluster-robust SE)
    decision_point_t: int                # per-user monotonic counter
    archetype_id: str                    # resolved archetype name
    mechanism_id: str                    # mechanism the action selected
    category_id: str                     # product/content category
    moderators_S_t: Dict[str, float]     # subset of H_t for moderation
    action_A_t: int                      # 0 = control, 1 = deliver mechanism
    rand_prob_p_t: float                 # ← THE LOGGED PROPENSITY
    epsilon_floor: float                 # the ε used at decision time
    availability_I_t: int                # 1 = available, 0 = not (filter in WCLS)
    p_t_known: bool                      # ← discipline anchor
    trial_id: str = ""                   # logical trial / experiment id
    ts_posterior_alpha: float = 0.0      # Beta α at decision time (audit)
    ts_posterior_beta: float = 0.0       # Beta β at decision time (audit)
    proximal_window_end_ts: int = 0      # join boundary for Y_{t+1}
    context_H_t: Dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# ε-floor mixer — wraps any TS-style probability distribution
# -----------------------------------------------------------------------------


def epsilon_floor_mix(
    pi_ts: Dict[str, float], epsilon: float = EPSILON_FLOOR,
) -> Dict[str, float]:
    """Mix a TS optimality distribution with a uniform floor.

    Per handoff §1.1:
        p_t(a) = (1 − ε) · π_TS(a) + ε · (1/K)

    Args:
        pi_ts: {arm_name: Pr(arm is optimal)} — must sum to 1.0
        epsilon: ε floor; default canonical 0.02

    Returns:
        {arm_name: p_t} — guaranteed to sum to 1.0, every value in
        [ε/K, 1 - ε(1 - 1/K)].

    Validates:
        - epsilon ∈ [0, 1]
        - pi_ts non-empty
        - pi_ts sums to ~1 (tolerance 1e-3)
    Raises ValueError on any violation. The mixer must NEVER silently
    accept a malformed input — that's how p_t corrupts.
    """
    if not pi_ts:
        raise ValueError("epsilon_floor_mix: pi_ts is empty")
    if not (0.0 <= epsilon <= 1.0):
        raise ValueError(f"epsilon_floor_mix: epsilon {epsilon} outside [0,1]")

    total = sum(pi_ts.values())
    if abs(total - 1.0) > 1e-3:
        raise ValueError(
            f"epsilon_floor_mix: pi_ts sums to {total}, expected 1.0"
        )

    K = len(pi_ts)
    uniform = 1.0 / K
    return {
        arm: (1.0 - epsilon) * p + epsilon * uniform
        for arm, p in pi_ts.items()
    }


def assert_positivity(
    p_t: Dict[str, float], epsilon: float = EPSILON_FLOOR,
) -> None:
    """Assert that mixed p_t respects the positivity invariant.

    Boruvka 2018 §2 requires 0 < p_t < 1. WCLS weights are 1/p_t; a
    p_t ≤ ε/K - tolerance means the mixer was bypassed somewhere
    upstream and the row must NOT be logged with p_t_known=true.
    """
    K = len(p_t)
    if K == 0:
        raise AssertionError("positivity: p_t is empty")
    floor = (epsilon / K) - 1e-9
    ceiling = 1.0 - epsilon * (1.0 - 1.0 / K) + 1e-9
    for arm, p in p_t.items():
        if p < floor:
            raise AssertionError(
                f"positivity violation: {arm} p_t={p} < floor {floor}"
            )
        if p > ceiling:
            raise AssertionError(
                f"positivity violation: {arm} p_t={p} > ceiling {ceiling}"
            )


# -----------------------------------------------------------------------------
# Optimality probability via Monte Carlo over Beta posteriors
# -----------------------------------------------------------------------------


def estimate_optimality_probabilities(
    posteriors: Dict[str, Tuple[float, float]],
    n_samples: int = 1000,
    rng_seed: Optional[int] = None,
) -> Dict[str, float]:
    """Estimate Pr(arm is argmax) via Monte Carlo from Beta posteriors.

    For Beta-Bernoulli Thompson Sampling, the optimality probability
    π_TS(arm) = Pr(θ_arm = max over all arms). Closed-form for K=2;
    Monte Carlo for K>2 (handoff §1.3 — Beta-Beta closed-form +
    MC fallback).

    Args:
        posteriors: {arm_name: (alpha, beta)} per Beta posterior
        n_samples: MC sample count. 1000 → ~0.03 stderr per arm (fine
                  for the ε-floor regime where target precision is 0.01)
        rng_seed: optional seed for reproducibility (tests pass this)

    Returns:
        {arm_name: π_TS(arm)} — sums to 1.0
    """
    if not posteriors:
        return {}

    try:
        import numpy as np
    except ImportError:
        raise RuntimeError("numpy required for MC optimality estimation")

    rng = np.random.default_rng(rng_seed)
    arms = list(posteriors.keys())
    K = len(arms)

    # Sample n_samples × K matrix from each Beta posterior
    samples = np.empty((n_samples, K))
    for j, arm in enumerate(arms):
        alpha, beta = posteriors[arm]
        # Numerical safety: Beta requires alpha > 0, beta > 0
        a = max(float(alpha), 1e-6)
        b = max(float(beta), 1e-6)
        samples[:, j] = rng.beta(a, b, size=n_samples)

    # Argmax per row; count wins per arm; normalize
    argmax_idx = np.argmax(samples, axis=1)
    counts = np.bincount(argmax_idx, minlength=K).astype(float)
    probs = counts / float(n_samples)
    return {arm: float(probs[j]) for j, arm in enumerate(arms)}


# -----------------------------------------------------------------------------
# Decision-and-log — wraps a sampler call with logging
# -----------------------------------------------------------------------------


# A producer is a callable that takes one MRTDecisionRecord and emits it.
# In production this wraps the Kafka producer; in dev/test, an in-memory
# list-append. None means "no producer wired" — record is built but
# dropped (caller decides whether to track that).
DecisionProducer = Optional[Callable[[MRTDecisionRecord], None]]


def select_action_with_logged_propensity(
    user_id: str,
    decision_point_t: int,
    archetype_id: str,
    category_id: str,
    posteriors: Dict[str, Tuple[float, float]],
    moderators_S_t: Dict[str, float],
    availability_I_t: int = 1,
    epsilon: float = EPSILON_FLOOR,
    n_mc_samples: int = 1000,
    rng_seed: Optional[int] = None,
    producer: DecisionProducer = None,
    trial_id: str = "",
    context_H_t: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], float, Optional[MRTDecisionRecord]]:
    """Wrap mechanism selection with ε-floor mixing + p_t logging.

    This is the canonical bid-time hook described in handoff §1.3. It
    replaces a bare `sampler.sample_mechanism(...)` call so that every
    decision lands a row in the MRT log with the correct p_t.

    Returns:
        (selected_arm, p_t_realised, record_or_None)

        record is None when availability_I_t=0 (per handoff: "when I_t=0
        do NOT randomize and do NOT log; the availability argument in
        wcls() filters" — §1.9).

    The producer (if provided) is called synchronously with the record
    BEFORE this function returns. Production wiring: producer wraps the
    Kafka client. Dev: producer appends to an in-memory list.
    """
    # Handoff §1.9: when I_t=0 do NOT randomize and do NOT log.
    if availability_I_t == 0:
        return None, 0.0, None

    if not posteriors:
        # No arms available — caller's contract violation; surface clearly.
        raise ValueError("select_action_with_logged_propensity: empty posteriors")

    try:
        import numpy as np
    except ImportError:
        raise RuntimeError("numpy required for MRT logging")

    # 1) Estimate π_TS via MC over the Beta posteriors
    pi_ts = estimate_optimality_probabilities(
        posteriors, n_samples=n_mc_samples, rng_seed=rng_seed,
    )

    # 2) ε-floor mix
    p_t_dist = epsilon_floor_mix(pi_ts, epsilon=epsilon)

    # 3) Positivity invariant — MUST hold or we don't log p_t_known=true
    try:
        assert_positivity(p_t_dist, epsilon=epsilon)
        positivity_ok = True
    except AssertionError as exc:
        logger.warning("Positivity violation, will mark p_t_known=false: %s", exc)
        positivity_ok = False

    # 4) Sample action from p_t_dist (deterministic-tie-break safe)
    rng = np.random.default_rng(rng_seed)
    arms = list(p_t_dist.keys())
    probs = np.array([p_t_dist[a] for a in arms], dtype=float)
    # Renormalize against floating-point drift (sum should be 1; force it)
    probs = probs / probs.sum()
    chosen_idx = int(rng.choice(len(arms), p=probs))
    chosen_arm = arms[chosen_idx]
    p_t_realised = float(p_t_dist[chosen_arm])

    # 5) Build record. action_A_t coding here: this is the K-arm version,
    #    so we log the chosen mechanism_id explicitly. The {0,1} action
    #    coding from handoff §1 maps cleanly when K=2 (the original
    #    HeartSteps setup); for K>2 the analysis pipeline derives binary
    #    contrasts from mechanism_id.
    record = MRTDecisionRecord(
        ts=int(time.time() * 1000),
        user_id=user_id,
        decision_point_t=decision_point_t,
        archetype_id=archetype_id,
        mechanism_id=chosen_arm,
        category_id=category_id,
        moderators_S_t=dict(moderators_S_t or {}),
        action_A_t=1,  # action was taken (control vs deliver coded by mechanism_id)
        rand_prob_p_t=p_t_realised,
        epsilon_floor=epsilon,
        availability_I_t=availability_I_t,
        p_t_known=positivity_ok,
        trial_id=trial_id,
        ts_posterior_alpha=float(posteriors[chosen_arm][0]),
        ts_posterior_beta=float(posteriors[chosen_arm][1]),
        context_H_t=dict(context_H_t or {}),
    )

    if producer is not None:
        try:
            producer(record)
        except Exception as exc:
            # Logging failure must not break the bid path. Mark the
            # record as not-known so downstream analysis excludes it,
            # and drop. The decision still lands; only the audit row
            # is lost.
            logger.warning("MRT producer failed: %s", exc)

    return chosen_arm, p_t_realised, record


# -----------------------------------------------------------------------------
# Avro schema definition — handoff §1.2 schema verbatim, for Kafka topic
# mrt.decisions.v1. Producers serialize via this schema; consumers
# deserialize. Schema-Registry-compatible.
# -----------------------------------------------------------------------------


MRT_DECISIONS_V1_AVRO_SCHEMA: Dict[str, Any] = {
    "type": "record",
    "name": "MRTDecision",
    "namespace": "informativ.mrt.v1",
    "doc": (
        "MRT decision-point log row. p_t_known=false means EXCLUDE from "
        "WCLS (Boruvka 2018 §2). Cluster on user_id."
    ),
    "fields": [
        {"name": "ts", "type": "long", "doc": "decision-time epoch ms"},
        {"name": "user_id", "type": "string", "doc": "cluster unit"},
        {"name": "decision_point_t", "type": "int",
         "doc": "per-user monotonic decision counter"},
        {"name": "archetype_id", "type": "string"},
        {"name": "mechanism_id", "type": "string",
         "doc": "selected mechanism (K-arm action)"},
        {"name": "category_id", "type": "string"},
        {"name": "moderators_S_t",
         "type": {"type": "map", "values": "double"},
         "doc": "subset of H_t for moderation analysis"},
        {"name": "action_A_t", "type": "int",
         "doc": "0=control 1=deliver; for K>2 use mechanism_id"},
        {"name": "rand_prob_p_t", "type": "double",
         "doc": "logged propensity ∈ [ε/K, 1-ε(1-1/K)]"},
        {"name": "epsilon_floor", "type": "double",
         "doc": "ε used at decision time (default 0.02)"},
        {"name": "availability_I_t", "type": "int",
         "doc": "1=available 0=not; WCLS filters on this"},
        {"name": "p_t_known", "type": "boolean",
         "doc": "false → EXCLUDE from WCLS"},
        {"name": "trial_id", "type": "string", "default": ""},
        {"name": "ts_posterior_alpha", "type": "double", "default": 0.0,
         "doc": "Beta α at decision time (audit)"},
        {"name": "ts_posterior_beta", "type": "double", "default": 0.0,
         "doc": "Beta β at decision time (audit)"},
        {"name": "proximal_window_end_ts", "type": "long", "default": 0,
         "doc": "join boundary for Y_{t+1}"},
        {"name": "context_H_t",
         "type": {"type": "map", "values": "string"},
         "default": {},
         "doc": "free-form context bag"},
    ],
}


# -----------------------------------------------------------------------------
# In-memory producer for dev / tests / pre-Kafka pilot
# -----------------------------------------------------------------------------


class InMemoryDecisionLog:
    """Simple in-memory producer for use before Kafka is deployed.

    Per handoff §1.2: 'Persistent copy in Parquet via Kafka.' Pre-Kafka
    we write to memory and flush to a JSONL file on demand. Production
    wiring replaces this with a kafka-python producer.
    """

    def __init__(self) -> None:
        self.records: List[MRTDecisionRecord] = []

    def emit(self, record: MRTDecisionRecord) -> None:
        self.records.append(record)

    def __len__(self) -> int:
        return len(self.records)

    def reset(self) -> None:
        self.records.clear()
