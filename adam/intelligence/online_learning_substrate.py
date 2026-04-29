# =============================================================================
# ADAM Per-Decision Online Learning Substrate
# Location: adam/intelligence/online_learning_substrate.py
# =============================================================================

"""
PER-DECISION ONLINE LEARNING SUBSTRATE (task #30)

Today: TheoryLearner LinkPosteriors update at outcome time. The cascade
scores mechanisms at decision time using L1/L2/L3 logic + edge-derived
features. The cascade does NOT read fresh LinkPosteriors at decision
time — so updates that landed an hour ago don't reach the next
decision.

This module is the substrate that lets the cascade refresh from the
latest LinkPosteriors before scoring. It does NOT yet wire into the
cascade's scoring path — that's a follow-up commit. Building substrate
first lets us test the read + aggregation in isolation; the wiring is
a small, focused commit when Chris approves the scoring change.

WHAT THIS LANDS

  - read_link_strengths_batch(theory_learner, link_keys) — batch
    accessor wrapping TheoryLearner.get_link_strength.
  - aggregate_mechanism_strength(link_keys, theory_learner) — turns a
    list of link_keys (typically from ChainAttestation.theoretical_link_keys)
    into a single per-mechanism strength via geometric mean
    (multiplicative aggregation: any single weak link drags the chain
    down). Returns 0.5 (neutral) on empty input.
  - aggregate_mechanism_strengths_from_attestations — decision-time
    helper. Takes a list of ChainAttestations (the orchestrator already
    has these per-decision) and produces (mechanism_id → aggregate
    strength) dict for use as a multiplicative modulator on
    cascade.mechanism_scores.

WHAT THIS DOES NOT LAND

  - Integration into _select_mechanisms's scoring blend. That's a
    one-liner once we approve the modulation form (geometric vs
    arithmetic vs Bayesian update).
  - Per-decision online updates to LinkPosteriors at decision time.
    Posteriors STILL update at outcome time only — that's the correct
    Bayesian semantics. What's online is the cascade's READ of those
    posteriors, not the WRITE.
  - Fancy aggregation (Bayesian model averaging across links). Geometric
    mean is the principled minimum.

DISCIPLINE

  - Pure functions. No side effects.
  - Geometric mean for chain-aggregation (multiplicative): a chain
    with one link at 0.1 has aggregate ~0.3 across 3 links of (0.1,
    0.7, 0.7). Arithmetic would give 0.5 — masking the weak link.
    Foundation §4.4: theory chains ARE multiplicative; geometric mean
    matches the underlying epistemology.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional


def read_link_strengths_batch(
    theory_learner: Any,
    link_keys: Iterable[str],
) -> Dict[str, float]:
    """Batch accessor: read current LinkPosterior means for many keys.

    Args:
        theory_learner: TheoryLearner instance (or duck-type with
            `get_link_strength(link_key) -> float`)
        link_keys: iterable of link_keys in TheoryLearner's
            "{relation}:{source}:{target}" format

    Returns:
        dict mapping link_key → posterior mean. Unknown keys map to
        0.5 (TheoryLearner.get_link_strength's neutral fallback).
    """
    return {key: theory_learner.get_link_strength(key) for key in link_keys}


def aggregate_mechanism_strength(
    link_keys: List[str],
    theory_learner: Any,
) -> float:
    """Aggregate per-mechanism strength via geometric mean of link
    strengths.

    Geometric mean is the right aggregation for theoretical chains:
    a chain with any weak link is overall weak (multiplicative). The
    arithmetic mean would mask single-link failures.

    Empty input → 0.5 (neutral). All-zero → 0.0 (the chain is dead).

    Args:
        link_keys: link_keys driving the mechanism (typically from
            ChainAttestation.theoretical_link_keys)
        theory_learner: TheoryLearner instance

    Returns:
        Aggregate strength in [0, 1].
    """
    if not link_keys:
        return 0.5
    strengths = [theory_learner.get_link_strength(k) for k in link_keys]
    # Geometric mean: nth root of product. Use log-space to avoid
    # underflow on long chains with small strengths.
    if any(s <= 0.0 for s in strengths):
        return 0.0
    log_sum = sum(math.log(s) for s in strengths)
    return math.exp(log_sum / len(strengths))


def aggregate_mechanism_strengths_from_attestations(
    attestations: List[Any],
    theory_learner: Any,
) -> Dict[str, float]:
    """Decision-time helper: build (mechanism_id → aggregate strength)
    from a list of ChainAttestations.

    For each mechanism mentioned in any attestation's mechanism_adjustments,
    aggregate the strengths of all link_keys that the attestation
    declared responsible for that mechanism. When multiple attestations
    contribute to the same mechanism, the aggregate is the average of
    each attestation's per-mechanism geometric-mean strength.

    The returned dict can be used as a multiplicative modulator on
    cascade.mechanism_scores: `score(m) ← score(m) × strength(m)` (with
    strength(m) clamped to a sane range to avoid wild swings on cold
    cells).

    Args:
        attestations: list of ChainAttestation objects from the DAG
        theory_learner: TheoryLearner instance

    Returns:
        dict mapping mechanism_id → aggregate strength in [0, 1].
        Empty dict when no attestation declares any mechanism.
    """
    # mechanism_id → list of (per-attestation strength) values
    by_mech: Dict[str, List[float]] = {}

    for att in attestations:
        # Build link_id → link_key map from the attestation's chain
        link_id_to_key: Dict[str, str] = {}
        for link in att.chain:
            # link.link_id is the per-attestation UUID; link.link_key
            # is "relation:source:target" format
            link_id_to_key[link.link_id] = link.link_key

        for adj in att.mechanism_adjustments:
            # chain_links_responsible holds link_ids — translate to
            # link_keys for TheoryLearner lookup
            keys = [
                link_id_to_key[lid]
                for lid in adj.chain_links_responsible
                if lid in link_id_to_key
            ]
            if not keys:
                continue
            strength = aggregate_mechanism_strength(keys, theory_learner)
            by_mech.setdefault(adj.mechanism_id, []).append(strength)

    # Average per-mechanism across attestations
    result: Dict[str, float] = {}
    for mech, vals in by_mech.items():
        if vals:
            result[mech] = sum(vals) / len(vals)
    return result


__all__ = [
    "aggregate_mechanism_strength",
    "aggregate_mechanism_strengths_from_attestations",
    "read_link_strengths_batch",
]
