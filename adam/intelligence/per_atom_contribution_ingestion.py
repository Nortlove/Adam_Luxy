# =============================================================================
# ADAM Per-Atom Contribution Ingestion (B3-LUXY Phase 3 deliverable 3 producer)
# Location: adam/intelligence/per_atom_contribution_ingestion.py
# =============================================================================

"""
PER-ATOM CONTRIBUTION INGESTION

The producer that feeds the §6 contribution-measurement framework with live
LUXY pilot data. At outcome time, reads the cached chain attestations from
the decision-time Redis cache, builds one AtomDecisionRecord per attesting
atom, feeds the global PerAtomContributionTracker.

Without this producer, `post_pilot_decision()` returns "insufficient_data"
forever and the §6 generalization decision tree never fires — the
measurement substrate exists but has no input.

CONTRACT
--------
This module is the bridge from `OutcomeHandler.process_outcome` to
`PerAtomContributionTracker.record_decision`. It:

  1. Reads `adam:atom_outputs:{decision_id}` from Redis (the same key
     populated by `_execute_real_atom_dag` and consumed by
     `_process_chain_attestations` for theory-learner routing).
  2. Resolves `mechanism_followed` from outcome metadata (the StackAdapt
     decision_cache → webhook → process_outcome path populates
     `mechanism_sent`).
  3. Maps `outcome_type` to `backfire_signal` via the canonical
     `is_negative_ethics_signal` (Foundation §7 rule 11).
  4. Rehydrates each atom's serialised ChainAttestation, builds
     AtomDecisionRecord, and feeds the tracker.

Runs alongside the theory-learner update — both consume the same cached
chain_attestations. The two consumers serve different purposes (theory
learner = per-link Bayesian update; contribution tracker = post-pilot
generalization decision) and intentionally read the same source so a
single decision-time cache write supports both.

See:
  - docs/B3_LUXY_PHASE_PLAN.md §6 (the three metrics + decision tree)
  - adam/intelligence/per_atom_contribution.py (tracker + AtomDecisionRecord)
  - adam/core/learning/outcome_handler.py:1768 (the parallel chain-attestation
    routing path that this producer mirrors at the cache-read level)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from adam.atoms.models.chain_attestation import ChainAttestation
from adam.core.outcome_types import is_negative_ethics_signal
from adam.intelligence.per_atom_contribution import (
    AtomDecisionRecord,
    PerAtomContributionTracker,
    get_per_atom_contribution_tracker,
)

logger = logging.getLogger(__name__)


# Cache key format mirrors campaign_orchestrator._execute_real_atom_dag's
# write site (line ~1071) and outcome_handler._process_chain_attestations'
# read site (line ~1803). Keep these three call sites in sync.
_REDIS_ATOM_OUTPUTS_KEY_FMT = "adam:atom_outputs:{decision_id}"


async def record_outcome_to_contribution_tracker(
    decision_id: str,
    outcome_type: str,
    outcome_value: float,
    success: bool,
    metadata: Optional[Dict[str, Any]] = None,
    tracker: Optional[PerAtomContributionTracker] = None,
) -> int:
    """Read cached atom_outputs for `decision_id` and feed one
    `AtomDecisionRecord` per attesting atom into the contribution tracker.

    Non-fatal at every step: cache load failures, rehydration failures,
    and missing metadata fields are logged at debug level and skipped.
    The producer never raises an exception out — outcome processing is
    the load-bearing path.

    Args:
        decision_id: ID of the decision whose outcome is being recorded.
            Same key the orchestrator used at decision time to cache
            atom_outputs.
        outcome_type: Outcome category (`conversion`, `refund`, etc.).
            Drives `backfire_signal` via `is_negative_ethics_signal`.
        outcome_value: 0.0–1.0 outcome quality scalar.
        success: Boolean success flag from the outcome handler's primary
            success determination (`is_positive_outcome(outcome_type) and
            outcome_value > threshold`).
        metadata: Outcome metadata. Reads `mechanism_sent` (canonical) or
            `mechanisms_applied[0]` (legacy) for `mechanism_followed`.
        tracker: Optional tracker instance. When None (the production
            path), uses the global singleton.

    Returns:
        Count of `AtomDecisionRecord`s added to the tracker. Zero when
        the cache is empty, no atoms emitted attestations, or all
        rehydrations failed.
    """
    metadata = metadata or {}

    # --- 1. Load cached atom_outputs ---
    try:
        from adam.core.container import get_container
        container = await get_container()
        if not getattr(container, "redis_cache", None):
            return 0
        cache_key = _REDIS_ATOM_OUTPUTS_KEY_FMT.format(decision_id=decision_id)
        cached = await container.redis_cache.get(cache_key)
    except Exception as e:
        logger.debug(
            "PerAtomContribution producer: cache load failed decision_id=%s: %s",
            decision_id, e,
        )
        return 0

    if not cached or not isinstance(cached, dict):
        return 0

    # --- 2. Resolve mechanism_followed from metadata ---
    # Decision_cache → webhook path populates `mechanism_sent`.
    # `mechanisms_applied` is the alternate field the synergy/decision
    # router uses. Read both, prefer mechanism_sent.
    mechanism_followed: Optional[str] = metadata.get("mechanism_sent") or None
    if not mechanism_followed:
        applied = metadata.get("mechanisms_applied")
        if applied and isinstance(applied, list) and applied:
            mechanism_followed = applied[0]

    # --- 3. Map outcome_type → backfire_signal ---
    # Foundation §7 rule 11 (fitness function IS the ethics): the
    # canonical helper covers refund / complaint / regret_signal /
    # churn_30d / ad_fatigue / negative_review.
    backfire_signal = is_negative_ethics_signal(outcome_type)

    # --- 4. Build records and feed tracker ---
    if tracker is None:
        tracker = get_per_atom_contribution_tracker()

    n_added = 0
    n_rehydrate_failures = 0
    for atom_id, atom_data in cached.items():
        if not isinstance(atom_data, dict):
            continue
        attestation_dict = atom_data.get("chain_attestation")
        if not attestation_dict:
            continue
        try:
            attestation = ChainAttestation(**attestation_dict)
        except Exception as e:
            n_rehydrate_failures += 1
            logger.debug(
                "PerAtomContribution producer: ChainAttestation rehydrate "
                "failed for atom_id=%s decision_id=%s: %s",
                atom_id, decision_id, e,
            )
            continue

        record = AtomDecisionRecord(
            decision_id=decision_id,
            atom_id=atom_id,
            chain_attestation=attestation,
            outcome_value=outcome_value,
            success=success,
            backfire_signal=backfire_signal,
            mechanism_followed=mechanism_followed,
        )
        tracker.record_decision(record)
        n_added += 1

    if n_added > 0:
        logger.debug(
            "PerAtomContribution producer: fed %d records (outcome_type=%s, "
            "backfire=%s, mechanism_followed=%s) for decision_id=%s",
            n_added, outcome_type, backfire_signal,
            mechanism_followed, decision_id,
        )

    if n_rehydrate_failures > 0:
        # Surface rehydration drift via Prometheus when available — this
        # would mean the cache schema diverged from the model, which is
        # the failure mode that would silently starve metrics over time.
        try:
            from adam.infrastructure.prometheus.metrics import get_metrics
            get_metrics().theory_update_source.labels(
                source="per_atom_contribution_rehydrate_failure",
            ).inc()
        except Exception:
            pass

    return n_added
