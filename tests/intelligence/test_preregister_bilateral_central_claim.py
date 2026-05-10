"""Q.B/Q.3 (Sketch C+) — tests for the pre-registered box script.

Pin: box hash determinism (same params → same SHA-256), parameter
grid composition matches expectations, post_pilot_methods structure.
"""

import pytest

from adam.blind_analysis.box import UnblindingState
from adam.intelligence.causal_learning import (
    CANONICAL_CIALDINI_9,
    EDGE_DIMENSIONS,
)


def _import_module():
    """Lazy-import the script so test collection doesn't trigger
    its top-level execution."""
    from scripts import preregister_bilateral_central_claim
    return preregister_bilateral_central_claim


def test_archetype_values_count():
    mod = _import_module()
    assert len(mod.ARCHETYPE_VALUES) == 8


def test_archetype_values_include_all_8():
    mod = _import_module()
    assert "explorer" in mod.ARCHETYPE_VALUES
    assert "achiever" in mod.ARCHETYPE_VALUES
    assert "pragmatist" in mod.ARCHETYPE_VALUES
    assert "analyst" in mod.ARCHETYPE_VALUES


def test_post_pilot_methods_documented():
    mod = _import_module()
    methods = mod.POST_PILOT_COMPOSITION_METHODS
    assert "causal_decomposition_to_causal_forest" in methods
    assert "causal_forest_to_causal_conformal" in methods
    assert "dowhy_refutation_on_causal_dag_ensemble" in methods
    assert "causal_decomposition_to_causal_adjudicator" in methods


def test_post_pilot_methods_have_deferred_until():
    """Sketch C+ discipline: each post-pilot method has a deferred_until
    stamp documenting WHEN it's allowed to execute."""
    mod = _import_module()
    for name, method in mod.POST_PILOT_COMPOSITION_METHODS.items():
        assert "deferred_until" in method, f"missing deferred_until: {name}"
        assert "post_pilot" in method["deferred_until"]


def test_box_builds_with_correct_grid_size():
    mod = _import_module()
    box = mod.build_bilateral_central_claim_box()
    expected_grid_size = (
        len(mod.ARCHETYPE_VALUES) * len(EDGE_DIMENSIONS) * len(CANONICAL_CIALDINI_9)
    )
    # 8 × 21 × 9 = 1,512
    assert expected_grid_size == 1512
    assert len(box.parameters) == 3


def test_box_starts_in_sealed_state():
    mod = _import_module()
    box = mod.build_bilateral_central_claim_box()
    assert box.state == UnblindingState.SEALED


def test_box_decision_threshold_is_alpha_05():
    mod = _import_module()
    box = mod.build_bilateral_central_claim_box()
    assert box.decision_threshold == 0.05


def test_box_decision_statistic_is_named():
    mod = _import_module()
    box = mod.build_bilateral_central_claim_box()
    assert box.decision_statistic == "MODERATES_edge_count_per_archetype"


def test_box_hash_deterministic_across_builds():
    """Re-running the script with identical params produces identical
    hash — Sketch C+ box-as-identity invariant."""
    mod = _import_module()
    box_a = mod.build_bilateral_central_claim_box()
    box_b = mod.build_bilateral_central_claim_box()
    assert box_a.pre_registration_hash == box_b.pre_registration_hash


def test_box_signal_region_starts_empty():
    """Signal/control assignment per cell happens at discovery time;
    pre-registration commits to grid + threshold + discipline only.
    Empty signal region at sealing → discovery transitions cells
    from control → signal as evidence accumulates."""
    mod = _import_module()
    box = mod.build_bilateral_central_claim_box()
    assert len(box.signal_region) == 0
    assert len(box.control_region) > 0


def test_box_name_pinned():
    """The box name is the canonical reference for this pre-registration
    cycle. Pin it so any rename surfaces immediately."""
    mod = _import_module()
    box = mod.build_bilateral_central_claim_box()
    assert box.name == "bilateral_central_claim_v1"
