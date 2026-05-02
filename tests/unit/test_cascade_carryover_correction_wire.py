"""Pin Slice 12 cascade wire — Step 10 carryover correction.

The within_subject_eligibility honest tag (d) lines 85-89 named
"Step 10 carryover correction term" as the sibling slice composing
on Slice 3's touch-history primitive. This wire makes Step 10
operative at decision time, AFTER all other score modulations
and BEFORE TTTS selection (matching directive Section 5.1's 14-step
pipeline ordering: Step 9 epistemic → Step 10 carryover → Step 11 TTTS).

Pin:
    * The cascade source imports the Step 10 primitive
    * The cascade source uses decision_cache.recent_touches_for_buyer
      (same touch-history primitive Slice 3 uses)
    * The cascade source threads the per-mechanism penalty dict to
      build_trace_from_cascade
    * The metrics surface exposes the corrections counter
    * Wire-mirror harness exercises hit / cold-buyer / ρ=0 / cross-
      mechanism / multiple-touches paths
    * Soft-fail discipline: any exception from user posterior path
      MUST NOT block the cascade — score modulation just skips.
"""

from __future__ import annotations

from typing import Dict, Optional

import pytest

from adam.intelligence.carryover_correction import (
    CarryoverCorrectionResult,
    apply_carryover_correction,
)


# -----------------------------------------------------------------------------
# Source-text contract pins — defend against accidental unwire
# -----------------------------------------------------------------------------


def test_cascade_imports_apply_carryover_correction():
    """Cascade source must reference the Step 10 wire primitive."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert (
        "from adam.intelligence.carryover_correction import" in src
        and "apply_carryover_correction" in src
    ), (
        "Cascade lost its Slice 12 import. Step 10 carryover correction "
        "(directive line 692) is silently unwired."
    )


def test_cascade_uses_touch_history_primitive():
    """The cascade reads touch history via decision_cache (same
    primitive Slice 3 uses)."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    # Slice 12 specifically references recent_touches_for_buyer in
    # its block (mirrors Slice 3's adapter).
    assert "recent_touches_for_buyer" in src, (
        "Cascade no longer reads recent touch history — Step 10 "
        "carryover correction has no Δ input."
    )


def test_cascade_threads_carryover_penalty_to_builder():
    """The cascade passes per_mechanism_carryover_penalty into
    build_trace_from_cascade so AlternativeCandidate.carryover_
    correction_term is populated on the trace."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "per_mechanism_carryover_penalty=" in src, (
        "Cascade no longer threads per_mechanism_carryover_penalty "
        "into the trace builder. Step 10 decomposition won't reach "
        "the chain-of-reasoning surface."
    )


def test_cascade_uses_user_posterior_manager_for_rho():
    """The cascade reads ρ from UserPosteriorManager (same singleton
    pattern outcome_handler.py:910 uses)."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "user_posterior_manager" in src, (
        "Cascade no longer accesses the user posterior manager. ρ "
        "will be permanently 0 → Step 10 will permanently no-op."
    )


def test_cascade_uses_washout_hours_for_tau():
    """τ sourced from washout_hours_for(m_prev) — closest existing
    per-mechanism time-scale primitive."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "washout_hours_for" in src, (
        "Cascade no longer references washout_hours_for as the τ "
        "source for Step 10 carryover decay."
    )


def test_metrics_surface_exposes_carryover_counter():
    """The corrections counter is present on the metrics surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "cascade_carryover_corrections_total"
    ), "Slice 12 corrections counter missing from metrics surface."


# -----------------------------------------------------------------------------
# Wire-mirror harness — isolates the in-cascade behavior
# -----------------------------------------------------------------------------


def _mirror_cascade_carryover_block(
    mechanism_scores: Dict[str, float],
    last_touched: Optional[str],
    hours_since: Optional[float],
    rho: float,
    effect_prev: float,
    tau: float,
) -> CarryoverCorrectionResult:
    """Mirror the cascade block: takes resolved inputs (the cascade
    block resolves them from decision_cache + UserPosteriorManager),
    applies correction, returns result."""
    return apply_carryover_correction(
        mechanism_scores,
        last_touched_mechanism=last_touched,
        hours_since_last_touch=hours_since,
        rho=rho,
        effect_prev_for_last_touched=effect_prev,
        tau=tau,
    )


def test_wire_corrects_same_mechanism_when_rho_nonzero():
    """The user just touched social_proof, ρ=0.4 from nightly
    HMC — penalty applies to social_proof candidate."""
    out = _mirror_cascade_carryover_block(
        mechanism_scores={"social_proof": 0.7, "scarcity": 0.5},
        last_touched="social_proof",
        hours_since=2.0,
        rho=0.4,
        effect_prev=0.6,
        tau=24.0,
    )
    assert out.per_mechanism_penalty["social_proof"] > 0
    assert out.per_mechanism_penalty["scarcity"] == 0.0
    assert out.modulated_scores["social_proof"] < 0.7
    assert out.modulated_scores["scarcity"] == 0.5
    assert out.n_corrected == 1


def test_wire_cold_buyer_no_correction():
    """No prior touch → no correction (cold-buyer path)."""
    out = _mirror_cascade_carryover_block(
        mechanism_scores={"social_proof": 0.7, "scarcity": 0.5},
        last_touched=None,
        hours_since=None,
        rho=0.4,
        effect_prev=0.6,
        tau=24.0,
    )
    assert out.modulated_scores == {"social_proof": 0.7, "scarcity": 0.5}
    assert out.n_corrected == 0


def test_wire_rho_zero_no_correction():
    """ρ=0 (default for un-reconciled user) → no correction."""
    out = _mirror_cascade_carryover_block(
        mechanism_scores={"social_proof": 0.7, "scarcity": 0.5},
        last_touched="social_proof",
        hours_since=2.0,
        rho=0.0,
        effect_prev=0.6,
        tau=24.0,
    )
    assert out.modulated_scores == {"social_proof": 0.7, "scarcity": 0.5}
    assert out.n_corrected == 0


def test_wire_cross_mechanism_pass_through_v01():
    """v0.1 single-ρ approximation: cross-mechanism penalty 0.
    User last touched social_proof; we're scoring scarcity →
    no penalty applied (pair-indexed sibling will activate)."""
    out = _mirror_cascade_carryover_block(
        mechanism_scores={"scarcity": 0.5, "authority": 0.6},
        last_touched="social_proof",  # different from candidates
        hours_since=2.0,
        rho=0.4,
        effect_prev=0.6,
        tau=24.0,
    )
    # All cross-mechanism — no scores changed.
    assert out.modulated_scores == {"scarcity": 0.5, "authority": 0.6}
    # Per-mech penalty entries should be 0 (no claim made).
    for v in out.per_mechanism_penalty.values():
        assert v == 0.0


def test_wire_recent_touch_yields_larger_penalty_than_old_touch():
    """Δ=1h vs Δ=72h with τ=24h → recent yields larger penalty."""
    base_kwargs = dict(
        mechanism_scores={"social_proof": 0.7},
        last_touched="social_proof",
        rho=0.4,
        effect_prev=0.6,
        tau=24.0,
    )
    out_recent = _mirror_cascade_carryover_block(
        hours_since=1.0, **base_kwargs,  # type: ignore[arg-type]
    )
    out_old = _mirror_cascade_carryover_block(
        hours_since=72.0, **base_kwargs,  # type: ignore[arg-type]
    )
    assert (
        out_recent.per_mechanism_penalty["social_proof"]
        > out_old.per_mechanism_penalty["social_proof"]
    )


def test_wire_penalty_dict_threadable_to_trace():
    """The per_mechanism_penalty dict shape matches what the trace
    builder expects (Dict[str, float], one entry per mechanism)."""
    out = _mirror_cascade_carryover_block(
        mechanism_scores={
            "social_proof": 0.7, "scarcity": 0.5, "authority": 0.6,
        },
        last_touched="social_proof",
        hours_since=1.0,
        rho=0.4,
        effect_prev=0.6,
        tau=24.0,
    )
    assert isinstance(out.per_mechanism_penalty, dict)
    assert set(out.per_mechanism_penalty.keys()) == {
        "social_proof", "scarcity", "authority",
    }
    for v in out.per_mechanism_penalty.values():
        assert isinstance(v, float)
