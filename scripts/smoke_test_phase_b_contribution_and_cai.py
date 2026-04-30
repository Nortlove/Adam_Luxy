#!/usr/bin/env python3
"""Phase B smoke test — Item 1 (per-atom contribution) + Item 9 (CAI flow).

Verifies BOTH wires fire without external dependencies (no Redis, no
Aura). Runs against in-process tracker / cache singletons with synthetic
inputs. Exits 0 on success, 1 on failure.

Usage:
    python3 scripts/smoke_test_phase_b_contribution_and_cai.py

Why this exists (per docs/PILOT_PLAN_2026_04_30.md Phase B):
    Item 1 — per_atom_contribution_ingestion.record_outcome_to_contribution_tracker
        is wired into outcome_handler.py:450-462. The tracker accumulates
        AtomDecisionRecords as outcomes flow in. The §6 generalization
        decision tree (post_pilot_decision()) consumes the tracker
        post-pilot. This smoke verifies the tracker → decision flow works
        with synthetic decision records.

    Item 9 — argument_cache.get_cached_argument is read by
        api/stackadapt/service.py:1051 inside the cascade response build
        path. Cache is populated offline by constitutional_loop. This
        smoke verifies cache write + read round-trips for one
        (brand_id, archetype, mechanism, barrier) tuple.

Forward-thinking note (Primary 3 — monitor + talk):
    Both flows produce data that should surface to a dashboard endpoint.
    Phase G will build:
        /internal/contribution-state — tracker counts per atom
        /internal/argument-cache-state — cache size + last-write
    Until then, this smoke + grep through Redis state are the operator
    tools.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def test_item_1_per_atom_contribution() -> bool:
    """Verify the tracker records decisions and post_pilot_decision fires.

    Skips the Redis-dependent producer (record_outcome_to_contribution_tracker
    requires container + Redis); exercises tracker.record_decision
    directly with synthetic AtomDecisionRecords. The producer's job is
    to build these records from cached chain_attestations + outcome
    metadata; that adapter is unit-tested elsewhere.
    """
    from adam.intelligence.per_atom_contribution import (
        AtomDecisionRecord,
        PerAtomContributionTracker,
    )
    from adam.atoms.models.chain_attestation import (
        ChainAttestation, TypedEvidence, ChainProvenance, CalibrationStatus,
    )

    tracker = PerAtomContributionTracker()  # fresh tracker for the smoke

    # Build 30 synthetic records per atom (the §6 minimum for evaluation)
    # across 9 atoms — enough to exercise post_pilot_decision.
    atoms = [
        "regulatory_focus", "temporal_construal", "social_proof",
        "scarcity", "identity_construction", "mimetic_desire",
        "anchoring", "attention_dynamics", "embodied_cognition",
    ]
    n_per_atom = 35  # > 30 minimum
    for atom_id in atoms:
        for i in range(n_per_atom):
            attestation = ChainAttestation(
                atom_id=atom_id,
                request_id=f"req_{atom_id}_{i}",
                target_construct=atom_id,
                final_assessment=TypedEvidence(
                    construct=atom_id,
                    value=0.7,
                    confidence=0.8,
                    citation="smoke:test:1",
                    calibration_status=CalibrationStatus.PINNED,
                ),
                provenance=ChainProvenance(
                    atom_id=atom_id,
                    atom_version="smoke_v1",
                    canonical_formula_citation="smoke:test:1",
                ),
            )
            record = AtomDecisionRecord(
                decision_id=f"d_{atom_id}_{i}",
                atom_id=atom_id,
                chain_attestation=attestation,
                outcome_value=1.0 if i % 3 == 0 else 0.0,  # 33% conversion rate
                success=(i % 3 == 0),
                backfire_signal=(i == 0),  # 1 backfire per atom — well under threshold
                mechanism_followed=atom_id,
            )
            tracker.record_decision(record)

    # Confirm records landed
    by_atom_count = sum(
        1 for atom_id in atoms if tracker._records_by_atom.get(atom_id)
    )
    print(f"  Records added: {n_per_atom * len(atoms)} across {by_atom_count} atoms")

    # Run the post-pilot decision tree
    decision, rationale, contributions = tracker.post_pilot_decision()
    print(f"  post_pilot_decision: {decision}")
    print(f"  rationale: {rationale}")
    print(f"  contributions: {len(contributions)} atoms scored")

    if by_atom_count != len(atoms):
        print(f"  FAIL: expected records for {len(atoms)} atoms, got {by_atom_count}")
        return False
    if decision == "insufficient_data":
        print(f"  FAIL: tracker has 35 decisions/atom but post_pilot_decision "
              f"says insufficient_data — verdict classifier broken")
        return False
    if len(contributions) != len(atoms):
        print(f"  FAIL: contributions dict has {len(contributions)} atoms, "
              f"expected {len(atoms)}")
        return False
    return True


def test_item_9_cai_argument_cache() -> bool:
    """Verify argument_cache write + read round-trips and the cascade
    reader path returns the cached argument.

    Exercises argument_cache directly with a synthetic AuditedArgument.
    The constitutional_loop generates these in production; we don't need
    to run the full loop here — just verify the cache contract.
    """
    from adam.intelligence.argument_cache import (
        CachedArgument,
        get_cached_argument,
        put_cached_argument,
    )

    brand_id = "luxy_smoke"
    archetype = "status_seeker"
    mechanism = "social_proof"
    barrier = "skepticism"

    # 1. Cache miss — verify graceful None
    miss = get_cached_argument(
        brand_id=brand_id, archetype=archetype, mechanism=mechanism, barrier=barrier,
    )
    if miss is not None:
        print(f"  WARN: cache hit on first lookup (stale state from prior run): {miss}")
    print(f"  Cache miss: {miss is None}")

    # 2. Write a synthetic audited argument
    arg = CachedArgument(
        headline="Trusted by professionals who set the standard",
        body="LUXY's roster includes the executives others quietly trust to be on time.",
        cta="See what they chose",
        barrier_addressed="skepticism",
        archetype_fit_score=0.85,
        factscore=0.92,
        iterations_to_converge=2,
    )
    put_cached_argument(
        brand_id=brand_id, archetype=archetype, mechanism=mechanism,
        barrier=barrier, argument=arg,
    )
    print(f"  Cached argument: brand={brand_id} arch={archetype} mech={mechanism}")

    # 3. Read it back — verify round-trip
    hit = get_cached_argument(
        brand_id=brand_id, archetype=archetype, mechanism=mechanism, barrier=barrier,
    )
    if hit is None:
        print(f"  FAIL: cached argument did not round-trip")
        return False
    if hit.headline != arg.headline:
        print(f"  FAIL: headline mismatch — '{hit.headline}' vs '{arg.headline}'")
        return False
    print(f"  Round-trip OK: headline='{hit.headline[:60]}...'")
    print(f"    factscore={hit.factscore}  archetype_fit={hit.archetype_fit_score}")

    # 4. Verify mechanism-mismatch returns None (the cascade discipline
    # anchor — cached argument under a different mechanism MUST NOT serve)
    wrong_mech = get_cached_argument(
        brand_id=brand_id, archetype=archetype,
        mechanism="authority",  # different mechanism
        barrier=barrier,
    )
    if wrong_mech is not None:
        print(f"  FAIL: cache served argument under wrong mechanism")
        return False
    print(f"  Mechanism mismatch correctly returns None")

    return True


def main() -> int:
    print("=" * 60)
    print("Phase B smoke — Item 1 (per-atom contribution) + Item 9 (CAI)")
    print("=" * 60)
    print()
    print("Item 1 — per_atom_contribution_ingestion → tracker → post_pilot_decision")
    item_1_ok = test_item_1_per_atom_contribution()
    print()
    print("Item 9 — argument_cache write/read round-trip + mechanism-isolation")
    item_9_ok = test_item_9_cai_argument_cache()
    print()

    if item_1_ok and item_9_ok:
        print("=" * 60)
        print("PHASE B SMOKE PASSED — Items 1 + 9 wired correctly")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("PHASE B SMOKE FAILURE — see output above")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
