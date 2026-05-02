"""Pin Slice 24 — Phase A → v3 interface seams.

Per the 2026-05-02 wrap-out handoff, the three components named for
v3 Phase 1 wrapping (Slice 7 Kelly, Slice 12 carryover, Slice 3
washout) needed indirection so v3 wrappers can register replacement
implementations without touching upstream callers.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: 2026-05-02 wrap-out handoff (interface stability
        discipline) + named v3 work-streams 1.D / 1.E / 1.F. Protocol
        pattern matches existing GoalStateModel Protocol in
        free_energy_dual_eval.

    (b) Boundary anchors:
          - Default registrations match pre-Slice-24 behavior
            (existing Slice 7 / 12 / Slice 3 tests still pass)
          - register_* replaces active impl
          - reset_to_defaults_for_tests restores defaults
          - Type pins via runtime_checkable Protocols
          - Soft-fail on registry lookup error in within_subject
            eligibility (back-compat to washout_hours_for direct call)
          - Cascade emit + emitter source-text contracts pin the
            registry calls

    (c) calibration_pending=False — pure interface refactor.

    (d) Honest tags — what is NOT in this slice (named successors):
          - v3 1.D HInfWrappedKellyBidComposer impl
          - v3 1.E FunnelMPCCarryoverStrategy impl
          - v3 1.F PKPDWashoutModel impl
          - Multi-process registry / configuration loader
          - Per-archetype routing
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from adam.intelligence.v3_interfaces import (
    BidComposer,
    CarryoverCorrectionStrategy,
    WashoutModel,
    get_active_bid_composer,
    get_active_carryover_strategy,
    get_active_washout_model,
    register_bid_composer,
    register_carryover_strategy,
    register_washout_model,
    reset_to_defaults_for_tests,
)


# -----------------------------------------------------------------------------
# Fixture — reset registry between tests
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_registries_between_tests():
    """Ensure no test leaks an alternative registration."""
    reset_to_defaults_for_tests()
    yield
    reset_to_defaults_for_tests()


# -----------------------------------------------------------------------------
# Default registrations
# -----------------------------------------------------------------------------


def test_default_bid_composer_implements_protocol():
    bc = get_active_bid_composer()
    assert isinstance(bc, BidComposer)
    # Default has the named "kelly_default" tag for telemetry.
    assert getattr(bc, "name", None) == "kelly_default"


def test_default_carryover_strategy_implements_protocol():
    cs = get_active_carryover_strategy()
    assert isinstance(cs, CarryoverCorrectionStrategy)
    assert getattr(cs, "name", None) == "step10_ar1_default"


def test_default_washout_model_implements_protocol():
    wm = get_active_washout_model()
    assert isinstance(wm, WashoutModel)
    assert getattr(wm, "name", None) == "constant_table_default"


# -----------------------------------------------------------------------------
# Default behavior matches pre-Slice-24 (contract preservation)
# -----------------------------------------------------------------------------


def test_default_carryover_matches_apply_carryover_correction():
    """The default strategy must produce identical output to the
    direct apply_carryover_correction call (Slice 12 contract)."""
    from adam.intelligence.carryover_correction import (
        apply_carryover_correction,
    )
    scores = {"social_proof": 0.7, "scarcity": 0.5}
    direct = apply_carryover_correction(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=2.0,
        rho=0.4,
        effect_prev_for_last_touched=0.6,
        tau=24.0,
    )
    via_registry = get_active_carryover_strategy().apply(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=2.0,
        rho=0.4,
        effect_prev_for_last_touched=0.6,
        tau=24.0,
    )
    assert direct.modulated_scores == via_registry.modulated_scores
    assert direct.per_mechanism_penalty == via_registry.per_mechanism_penalty
    assert direct.n_corrected == via_registry.n_corrected


def test_default_washout_min_wait_matches_washout_hours_for():
    from adam.retargeting.scheduler import washout_hours_for
    wm = get_active_washout_model()
    for mech in ("social_proof", "scarcity", "authority"):
        assert wm.min_wait_hours(mech) == washout_hours_for(mech)


def test_default_washout_residual_effect_at_zero_is_one():
    """At Δ=0, no decay applied → residual = 1.0."""
    wm = get_active_washout_model()
    assert wm.residual_effect_fraction("social_proof", 0.0) == pytest.approx(
        1.0,
    )


def test_default_washout_residual_effect_at_half_life_is_half():
    """At Δ=t½, residual = 0.5 by construction (first-order decay)."""
    from adam.intelligence.mechanism_adme import MECHANISM_PROFILES
    profile = MECHANISM_PROFILES.get("social_proof")
    if profile is None:
        pytest.skip("MECHANISM_PROFILES has no 'social_proof' entry")
    half_life = profile.half_life_hours
    wm = get_active_washout_model()
    assert wm.residual_effect_fraction(
        "social_proof", half_life,
    ) == pytest.approx(0.5, rel=0.01)


def test_default_washout_residual_effect_decays_to_zero():
    """At Δ → ∞, residual → 0."""
    wm = get_active_washout_model()
    assert wm.residual_effect_fraction("social_proof", 100000.0) < 1e-3


# -----------------------------------------------------------------------------
# Register / replace
# -----------------------------------------------------------------------------


def test_register_bid_composer_replaces_active():
    class _StubBC:
        name = "stub"
        def compose_chosen(self, **_):
            return 42.0
        def compose_alternatives(self, alts, **_):
            return alts

    register_bid_composer(_StubBC())
    bc = get_active_bid_composer()
    assert getattr(bc, "name", None) == "stub"
    assert bc.compose_chosen(
        chosen_mechanism="m",
        chosen_score=0.5,
        posture="p",
        bong_posterior=None,
    ) == 42.0


def test_register_carryover_strategy_replaces_active():
    from dataclasses import dataclass

    @dataclass
    class _StubResult:
        modulated_scores: Dict[str, float]
        per_mechanism_penalty: Dict[str, float]
        n_corrected: int
        rho: float

    class _StubCS:
        name = "stub_carry"
        def apply(self, scores, **_):
            return _StubResult(
                modulated_scores=dict(scores),
                per_mechanism_penalty={m: 0.0 for m in scores},
                n_corrected=0,
                rho=0.0,
            )

    register_carryover_strategy(_StubCS())
    cs = get_active_carryover_strategy()
    assert getattr(cs, "name", None) == "stub_carry"


def test_register_washout_model_replaces_active():
    class _StubWM:
        name = "stub_wm"
        def min_wait_hours(self, mech):
            return 99.0
        def residual_effect_fraction(self, mech, hours):
            return 0.42

    register_washout_model(_StubWM())
    wm = get_active_washout_model()
    assert getattr(wm, "name", None) == "stub_wm"
    assert wm.min_wait_hours("anything") == 99.0
    assert wm.residual_effect_fraction("any", 100.0) == 0.42


def test_reset_restores_defaults():
    class _StubBC:
        name = "stub"
        def compose_chosen(self, **_):
            return 0.0
        def compose_alternatives(self, alts, **_):
            return alts

    register_bid_composer(_StubBC())
    assert getattr(get_active_bid_composer(), "name", None) == "stub"
    reset_to_defaults_for_tests()
    assert (
        getattr(get_active_bid_composer(), "name", None)
        == "kelly_default"
    )


# -----------------------------------------------------------------------------
# Source-text contracts — call sites dispatch via registry
# -----------------------------------------------------------------------------


def test_decision_trace_emitter_uses_bid_composer_registry():
    """build_trace_from_cascade must dispatch via get_active_bid_composer."""
    from pathlib import Path
    src = Path("adam/intelligence/decision_trace_emitter.py").read_text()
    assert "get_active_bid_composer" in src, (
        "Emitter no longer dispatches via v3_interfaces.BidComposer "
        "registry — v3 1.D wrap point lost."
    )


def test_cascade_uses_carryover_strategy_registry():
    """bilateral_cascade must dispatch via get_active_carryover_strategy."""
    from pathlib import Path
    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "get_active_carryover_strategy" in src, (
        "Cascade no longer dispatches via v3_interfaces."
        "CarryoverCorrectionStrategy registry — v3 1.E wrap point lost."
    )


def test_within_subject_eligibility_uses_washout_registry():
    """passes_washout dispatches min_wait_hours via the registry."""
    from pathlib import Path
    src = Path(
        "adam/intelligence/within_subject_eligibility.py"
    ).read_text()
    assert "get_active_washout_model" in src, (
        "Within-subject eligibility no longer dispatches via "
        "v3_interfaces.WashoutModel registry — v3 1.F wrap point lost."
    )


# -----------------------------------------------------------------------------
# Soft-fail on registry exception (within-subject eligibility)
# -----------------------------------------------------------------------------


def test_passes_washout_soft_fails_to_direct_call():
    """When the v3 registry raises, passes_washout falls through to
    the direct washout_hours_for call — back-compat preserved even if
    a v3 wrapper crashes."""

    class _RaisingWM:
        name = "raising"
        def min_wait_hours(self, mech):
            raise RuntimeError("simulated v3 wrapper failure")
        def residual_effect_fraction(self, mech, hours):
            raise RuntimeError("simulated")

    register_washout_model(_RaisingWM())

    from adam.intelligence.within_subject_eligibility import (
        passes_washout,
    )
    # With a raising registry, passes_washout should NOT propagate the
    # exception. It falls through to washout_hours_for direct.
    # Just enough hours to clear default washout_hours_for value.
    out = passes_washout(
        mechanism="social_proof",
        hours_since_last_touch=999.0,
    )
    assert out is True  # 999h is well above any reasonable washout


# -----------------------------------------------------------------------------
# Default carryover doesn't break adjacent tests
# -----------------------------------------------------------------------------


def test_carryover_protocol_runtime_checkable():
    """The Protocol classes are runtime_checkable so isinstance
    works for non-class registrations (duck-typed objects)."""
    class _DuckBC:
        name = "duck"
        def compose_chosen(self, **_):
            return None
        def compose_alternatives(self, alts, **_):
            return alts

    assert isinstance(_DuckBC(), BidComposer)
