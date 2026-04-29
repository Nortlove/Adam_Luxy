# =============================================================================
# ADAM Spine #6 — Decision-Time Counterfactual Trace + Propensity Logging
# Location: adam/intelligence/spine/spine_6_decision_trace.py
# =============================================================================

"""Decision-time counterfactual trace + propensity logging.

PER DIRECTIVE SECTION 2 (Spine #6) + SECTION 5.4 (closed-form propensity).

At each recommendation, the orchestrator emits a structured trace: for
the chosen creative-mechanism pair, the engine evaluates ~3-5 alternative
pairs against the same user-state-context and stores
(chosen, alternatives, posterior_on_each, propensity_under_TS,
free_energy_decomposition, fluency_scores, carryover_adjustments) as a
Pydantic-typed object persisted to Redis (TTL aligned with demo loop)
and Neo4j (long-term).

WHY THIS IS SPINE — the integrating primitive

Per directive: "This is the single most powerful primitive for partner
trust *and* statistical efficiency. With logged propensities, every
served impression contributes to evaluating *every* arm via inverse-
propensity-weighted off-policy estimation, not just the played arm —
a 3-5x effective sample size multiplier at no marginal infrastructure
cost. And the trace becomes the do-calculus chain that the LUXY CMO
can inspect at any impression."

The DecisionTrace is the artifact the Defensive Reasoning panel
(Spine #13) reads at partner-display time. It is also the input to
off-policy evaluation (IPS, Doubly Robust, SNIPS) per directive
Section 5.2.

DECISION-TIME CONSUMERS (Rule A check)

The DecisionTrace is BOTH produced and consumed at decision time:
    - Produced: by the orchestrator for every served impression
    - Consumed: by the Defensive Reasoning renderer (Spine #13) at
      partner-display time
    - Consumed: by the off-policy evaluator (IPS/DR/SNIPS) at outcome
      arrival time
    - Consumed: by Spine #11's outcome routing (sapid → trace → user)

This IS the integrating primitive. Without it, the do-calculus chain
is fiction.

THIS COMMIT SHIPS

    - DecisionTrace Pydantic model with full structured decomposition
    - Alternative Pydantic model (per-candidate decomposition)
    - Closed-form TTTS propensity computation (Jeunen et al. 2025)
    - Inverse-propensity-weighted off-policy reward estimator (IPS)
    - Doubly Robust off-policy estimator
    - Self-Normalized IPS (SNIPS) off-policy estimator
    - In-memory store for tests (production binding writes to Neo4j +
      Redis hot cache)

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - Neo4j writeback wire (Pydantic model is ready)
    - Redis hot cache wire (TTL configuration)
    - Defensive Reasoning renderer reframing (separate from this commit;
      reads from DecisionTrace once that's wired)

REFERENCES

    Jeunen, Yates & Goodman 2025 — "Counterfactual Inference under
        Thompson Sampling" — closed-form propensity.
    Gilotte et al. 2018 — offline A/B testing for recsys via SNIPS.
    Bottou et al. 2013 — counterfactual reasoning and learning systems.
    Dudík 2011 — Doubly Robust off-policy.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic models — the structured trace
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AlternativeDecomposition(BaseModel):
    """One alternative the policy considered but did not select.

    Per directive Spine #6 schema: alternatives carries
    (creative_id, mechanism, posterior_score, free_energy_F,
    fluency_score, propensity_under_TS).

    Plus carryover_correction_term and epistemic_bonus per directive
    Section 5.1 step decomposition.
    """

    model_config = ConfigDict(extra="forbid")

    creative_id: Optional[str] = None
    mechanism: str
    posterior_score: float
    free_energy_F: float = 0.0
    fluency_score: float = 0.0
    fluency_floor_passed: bool = True
    posture_compatibility_score: float = 0.0
    carryover_correction_term: float = 0.0
    epistemic_bonus: float = 0.0
    propensity_under_TS: float = 0.0
    final_score: float = 0.0


class DecisionTrace(BaseModel):
    """Full structured trace for one decision.

    Per directive Section 2 Spine #6 schema. The do-calculus chain
    artifact partner-facing at decision-display time.

    `propensity_chosen` is the propensity of selecting the chosen
    arm under the policy (closed-form for TTTS per Jeunen 2025).
    Required for off-policy evaluation: every served impression
    contributes to evaluating every arm via IPS reweighting.

    `chain_of_reasoning` is the structured render of how the score
    decomposed (KL term, pragmatic, fluency, compatibility, carryover,
    epistemic — each as a contribution percentage). The Defensive
    Reasoning panel reads this directly.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    decision_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=_now_utc)
    bid_request_id: Optional[str] = None
    sapid: Optional[str] = None  # StackAdapt postback ID for round-trip

    # Choice + propensity
    chosen_creative_id: Optional[str] = None
    chosen_mechanism: str
    chosen_score: float
    propensity_chosen: float

    # Alternatives (typically 3-5)
    alternatives: List[AlternativeDecomposition] = Field(default_factory=list)

    # User state at decision time
    user_posterior_snapshot: Optional[Dict[str, Any]] = None

    # Page state at decision time
    page_posture: Optional[str] = None
    page_posture_confidence: float = 1.0
    page_posture_vector: Optional[List[float]] = None

    # Bid value (Kelly-derived)
    bid_value: Optional[float] = None

    # Outcome linkage (closed when sapid → outcome arrives)
    outcome_observed_at: Optional[datetime] = None
    outcome_class: Optional[str] = None
    outcome_value: Optional[float] = None

    @field_validator("propensity_chosen")
    @classmethod
    def _validate_propensity(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"propensity_chosen must be in [0, 1]; got {v}"
            )
        return v

    @field_validator("page_posture_confidence")
    @classmethod
    def _validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"page_posture_confidence must be in [0, 1]; got {v}"
            )
        return v

    def chain_of_reasoning(self) -> Dict[str, Any]:
        """Structured render of the chosen action's scoring decomposition.

        Returns a dict the Defensive Reasoning renderer (Spine #13)
        consumes to populate the contribution-decomposition bar chart.
        """
        chosen_alt = next(
            (a for a in self.alternatives if a.mechanism == self.chosen_mechanism),
            None,
        )
        if chosen_alt is None:
            # Build from chosen_score + posture only.
            return {
                "chosen_mechanism": self.chosen_mechanism,
                "chosen_score": self.chosen_score,
                "components": {},
                "posture": self.page_posture,
                "propensity": self.propensity_chosen,
            }
        return {
            "chosen_mechanism": self.chosen_mechanism,
            "chosen_score": self.chosen_score,
            "components": {
                "posterior": chosen_alt.posterior_score,
                "free_energy_F": chosen_alt.free_energy_F,
                "fluency": chosen_alt.fluency_score,
                "posture_compatibility": chosen_alt.posture_compatibility_score,
                "carryover": chosen_alt.carryover_correction_term,
                "epistemic_bonus": chosen_alt.epistemic_bonus,
            },
            "posture": self.page_posture,
            "propensity": self.propensity_chosen,
        }

    def to_neo4j_props(self) -> Dict[str, Any]:
        """Serialize to Neo4j-property-friendly dict.

        Lists + nested objects → JSON strings.
        """
        return {
            "decision_id": self.decision_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "bid_request_id": self.bid_request_id or "",
            "sapid": self.sapid or "",
            "chosen_mechanism": self.chosen_mechanism,
            "chosen_creative_id": self.chosen_creative_id or "",
            "chosen_score": float(self.chosen_score),
            "propensity_chosen": float(self.propensity_chosen),
            "alternatives_json": json.dumps(
                [a.model_dump() for a in self.alternatives],
                default=str,
            ),
            "user_posterior_snapshot_json": json.dumps(
                self.user_posterior_snapshot, default=str,
            ) if self.user_posterior_snapshot is not None else "",
            "page_posture": self.page_posture or "",
            "page_posture_confidence": float(self.page_posture_confidence),
            "bid_value": float(self.bid_value) if self.bid_value is not None else 0.0,
            "outcome_class": self.outcome_class or "",
            "outcome_observed_at": (
                self.outcome_observed_at.isoformat()
                if self.outcome_observed_at else ""
            ),
        }


# =============================================================================
# Closed-form TTTS propensity (Jeunen 2025)
# =============================================================================


def compute_ttts_propensity(
    posterior_samples_per_arm: Dict[str, List[float]],
    chosen_arm: str,
    *,
    beta: float = 0.5,
) -> float:
    """Closed-form propensity of selecting `chosen_arm` under top-two
    Thompson sampling.

    Per Jeunen, Yates & Goodman 2025: under TTTS with parameter β, the
    propensity of arm a is:

        π(a) = β · P(a is best) + (1 - β) · P(a is second-best | a is not best)

    Approximated from posterior samples:
        P(a best) = fraction of samples where a's draw is highest
        P(a 2nd best | not best) = fraction of samples where a's draw
                                    is second when not first

    Returns propensity in [0, 1].

    Args:
        posterior_samples_per_arm: dict of arm → list of posterior
            samples (same length per arm; samples drawn from the per-
            arm posterior at decision time)
        chosen_arm: the arm whose propensity to compute
        beta: TTTS parameter; β = 0.5 is canonical (equal weight on
            best and second-best paths)

    Edge cases:
        - chosen_arm not in samples → 0.0
        - samples_per_arm has 0 samples → 0.0
        - All samples identical for chosen → uniform across arms
    """
    if chosen_arm not in posterior_samples_per_arm:
        return 0.0

    arms = sorted(posterior_samples_per_arm.keys())
    if not arms:
        return 0.0

    n_samples = len(posterior_samples_per_arm[chosen_arm])
    if n_samples == 0:
        return 0.0

    # Verify all arms have the same number of samples (TTTS assumes
    # paired draws from the joint posterior).
    for a in arms:
        if len(posterior_samples_per_arm[a]) != n_samples:
            raise ValueError(
                f"All arms must have the same number of posterior "
                f"samples; arm '{a}' has {len(posterior_samples_per_arm[a])} "
                f"vs chosen '{chosen_arm}' has {n_samples}"
            )

    # Count: P(chosen is best) and P(chosen is second-best when not best)
    n_best_chosen = 0
    n_second_chosen_given_not_best = 0
    n_not_best = 0

    for i in range(n_samples):
        draws = {a: posterior_samples_per_arm[a][i] for a in arms}
        # Sort arms by draw (descending); break ties by arm name.
        ranked = sorted(arms, key=lambda a: (-draws[a], a))
        best = ranked[0]
        second_best = ranked[1] if len(ranked) > 1 else None

        if best == chosen_arm:
            n_best_chosen += 1
        else:
            n_not_best += 1
            if second_best == chosen_arm:
                n_second_chosen_given_not_best += 1

    p_best = n_best_chosen / n_samples
    p_second_given_not_best = (
        n_second_chosen_given_not_best / n_not_best
        if n_not_best > 0 else 0.0
    )

    propensity = beta * p_best + (1.0 - beta) * p_second_given_not_best
    return max(0.0, min(1.0, propensity))


# =============================================================================
# Off-policy evaluation: IPS, Doubly Robust, SNIPS
# =============================================================================


def ips_estimate(
    traces: List[DecisionTrace],
    target_arm: str,
    *,
    propensity_floor: float = 0.01,
) -> float:
    """Inverse Propensity Score estimate of expected reward for `target_arm`.

    Per Bottou et al. 2013:
        IPS(π_e) = (1/N) Σ_i (1{a_i = target_arm} / π_log(a_i)) · r_i

    Where r_i is the observed reward when arm a_i was played and
    π_log(a_i) is the propensity logged at decision time.

    Propensity floor prevents division-by-near-zero from extreme
    propensities. Per directive Section 3.7 Boruvka 2018: propensities
    are truncated to [ε, 1-ε] in production.

    Returns 0.0 when no traces or no traces with the target arm.
    """
    if not traces:
        return 0.0

    total = 0.0
    for trace in traces:
        if trace.chosen_mechanism != target_arm:
            continue
        if trace.outcome_value is None:
            continue
        propensity = max(propensity_floor, trace.propensity_chosen)
        total += trace.outcome_value / propensity

    return total / len(traces)


def snips_estimate(
    traces: List[DecisionTrace],
    target_arm: str,
    *,
    propensity_floor: float = 0.01,
) -> float:
    """Self-Normalized Inverse Propensity Score estimate.

    Per Swaminathan & Joachims 2015:
        SNIPS(π_e) = Σ_i (1{a_i = target} / π_log) · r_i  /  Σ_i (1{a_i = target} / π_log)

    Reduces variance vs IPS at the cost of small bias. Useful for
    moderate-N regimes (LUXY pilot N).

    Returns 0.0 when no traces with the target arm.
    """
    if not traces:
        return 0.0

    weighted_reward_sum = 0.0
    weight_sum = 0.0
    for trace in traces:
        if trace.chosen_mechanism != target_arm:
            continue
        if trace.outcome_value is None:
            continue
        propensity = max(propensity_floor, trace.propensity_chosen)
        weight = 1.0 / propensity
        weighted_reward_sum += weight * trace.outcome_value
        weight_sum += weight

    if weight_sum == 0.0:
        return 0.0
    return weighted_reward_sum / weight_sum


def doubly_robust_estimate(
    traces: List[DecisionTrace],
    target_arm: str,
    reward_model: Optional[Dict[Tuple[str, str], float]] = None,
    *,
    propensity_floor: float = 0.01,
) -> float:
    """Doubly Robust off-policy reward estimate.

    Per Dudík 2011:
        DR(π_e) = (1/N) Σ_i [
            q̂(x_i, target) +
            1{a_i = target} · (r_i - q̂(x_i, a_i)) / π_log(a_i)
        ]

    Where q̂ is a fitted reward model (per-(user, arm) reward estimate).
    DR is unbiased as long as either q̂ is correct OR π_log is correct.

    For substrate purposes, the reward model is provided as a dict
    keyed by (user_id, arm) → expected_reward. Defaults to 0.0 for
    missing keys (degrades to IPS).

    Returns 0.0 when no traces.
    """
    if not traces:
        return 0.0

    rm = reward_model or {}
    total = 0.0

    for trace in traces:
        # q̂(x_i, target)
        q_target = rm.get((trace.user_id, target_arm), 0.0)

        # 1{a_i = target} · (r_i - q̂(x_i, a_i)) / π_log(a_i)
        correction = 0.0
        if trace.chosen_mechanism == target_arm and trace.outcome_value is not None:
            propensity = max(propensity_floor, trace.propensity_chosen)
            q_played = rm.get((trace.user_id, trace.chosen_mechanism), 0.0)
            correction = (trace.outcome_value - q_played) / propensity

        total += q_target + correction

    return total / len(traces)


# =============================================================================
# In-memory store (test substrate; production wires to Neo4j + Redis)
# =============================================================================


@dataclass
class _DecisionTraceStore:
    """In-memory store for tests + early dev. Production wires to
    Neo4j (long-term) and Redis (hot cache; TTL aligned to demo loop)."""

    _by_decision_id: Dict[str, DecisionTrace] = field(default_factory=dict)
    _by_sapid: Dict[str, str] = field(default_factory=dict)


_default_store = _DecisionTraceStore()


def record_trace(
    trace: DecisionTrace,
    *,
    store: Optional[_DecisionTraceStore] = None,
) -> None:
    """Append a DecisionTrace to the store.

    Production binding: write through to Neo4j (long-term) + Redis
    (hot cache). In-memory binding is for tests + early dev.
    """
    s = store or _default_store
    s._by_decision_id[trace.decision_id] = trace
    if trace.sapid:
        s._by_sapid[trace.sapid] = trace.decision_id


def query_trace_by_id(
    decision_id: str,
    *,
    store: Optional[_DecisionTraceStore] = None,
) -> Optional[DecisionTrace]:
    """Look up a trace by decision_id."""
    s = store or _default_store
    return s._by_decision_id.get(decision_id)


def query_trace_by_sapid(
    sapid: str,
    *,
    store: Optional[_DecisionTraceStore] = None,
) -> Optional[DecisionTrace]:
    """Look up a trace by sapid (the sapid round-trip closes via this)."""
    s = store or _default_store
    decision_id = s._by_sapid.get(sapid)
    if decision_id is None:
        return None
    return s._by_decision_id.get(decision_id)


def reset_default_store() -> None:
    """Test-only: clear the default store."""
    _default_store._by_decision_id.clear()
    _default_store._by_sapid.clear()


def store_size() -> int:
    return len(_default_store._by_decision_id)


def close_trace_with_outcome(
    decision_id: str,
    outcome_class: str,
    outcome_value: float,
    observed_at: Optional[datetime] = None,
    *,
    store: Optional[_DecisionTraceStore] = None,
) -> Optional[DecisionTrace]:
    """Close a trace by attaching an observed outcome.

    The orchestrator calls this when an outcome arrives via Spine #11
    (sapid → trace lookup → outcome attachment). Returns the updated
    trace or None when decision_id unknown.
    """
    s = store or _default_store
    trace = s._by_decision_id.get(decision_id)
    if trace is None:
        return None

    updated = trace.model_copy(update={
        "outcome_class": outcome_class,
        "outcome_value": outcome_value,
        "outcome_observed_at": observed_at or _now_utc(),
    })
    s._by_decision_id[decision_id] = updated
    return updated


__all__ = [
    "AlternativeDecomposition",
    "DecisionTrace",
    "close_trace_with_outcome",
    "compute_ttts_propensity",
    "doubly_robust_estimate",
    "ips_estimate",
    "query_trace_by_id",
    "query_trace_by_sapid",
    "record_trace",
    "reset_default_store",
    "snips_estimate",
    "store_size",
]
