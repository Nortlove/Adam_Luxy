"""1.A.SI.1 — Blind-analysis box construction tests.

Per directive §1.A.SI.1 closure: pre-registration discipline
enforced; placeholder data generator runs deterministically.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from adam.blind_analysis import (
    BlindAnalysisBox,
    BoxParameter,
    BoxValidationError,
    UnblindingState,
    placeholder_data_generator,
    sealed_box,
)


# ----------------------------------------------------------------------------
# Box construction + invariants
# ----------------------------------------------------------------------------

class TestBoxConstruction:
    def test_minimal_sealed_box(self):
        box = sealed_box(
            name="test_box",
            parameters=[
                BoxParameter("creative_id", ("A", "B")),
                BoxParameter("cell_id", ("c1",)),
            ],
            signal_region=[("A", "c1")],
            control_region=[("B", "c1")],
            decision_statistic="ipsw_corrected_lift",
            decision_threshold=0.05,
        )
        assert box.name == "test_box"
        assert box.state == UnblindingState.SEALED
        assert len(box.pre_registration_hash) == 64  # SHA-256 hex length

    def test_signal_control_overlap_rejected(self):
        with pytest.raises(BoxValidationError, match="overlap"):
            sealed_box(
                name="bad", parameters=[BoxParameter("x", ("a", "b"))],
                signal_region=[("a",)], control_region=[("a",)],
                decision_statistic="m", decision_threshold=0.0,
            )

    def test_signal_outside_grid_rejected(self):
        with pytest.raises(BoxValidationError, match="outside"):
            sealed_box(
                name="bad", parameters=[BoxParameter("x", ("a", "b"))],
                signal_region=[("z",)], control_region=[],
                decision_statistic="m", decision_threshold=0.0,
            )

    def test_control_outside_grid_rejected(self):
        with pytest.raises(BoxValidationError, match="outside"):
            sealed_box(
                name="bad", parameters=[BoxParameter("x", ("a", "b"))],
                signal_region=[("a",)], control_region=[("zz",)],
                decision_statistic="m", decision_threshold=0.0,
            )

    def test_parameter_grid_cartesian_product(self):
        box = sealed_box(
            name="grid",
            parameters=[
                BoxParameter("a", ("x", "y")),
                BoxParameter("b", (1, 2, 3)),
            ],
            signal_region=[("x", 1)],
            control_region=[("y", 3)],
            decision_statistic="m", decision_threshold=0.0,
        )
        grid = box.parameter_grid()
        assert len(grid) == 6
        assert ("x", 1) in grid
        assert ("y", 3) in grid


# ----------------------------------------------------------------------------
# Pre-registration hash discipline
# ----------------------------------------------------------------------------

class TestHashDeterminism:
    def test_same_inputs_yield_same_hash(self):
        b1 = sealed_box(
            name="x",
            parameters=[BoxParameter("a", ("p", "q")),
                        BoxParameter("b", (1, 2))],
            signal_region=[("p", 1), ("q", 2)],
            control_region=[("p", 2), ("q", 1)],
            decision_statistic="metric", decision_threshold=0.05,
        )
        b2 = sealed_box(
            name="x",
            parameters=[BoxParameter("a", ("p", "q")),
                        BoxParameter("b", (1, 2))],
            signal_region=[("q", 2), ("p", 1)],   # different order
            control_region=[("q", 1), ("p", 2)],  # different order
            decision_statistic="metric", decision_threshold=0.05,
        )
        assert b1.pre_registration_hash == b2.pre_registration_hash

    def test_threshold_change_changes_hash(self):
        kw = dict(
            name="x",
            parameters=[BoxParameter("a", ("p", "q"))],
            signal_region=[("p",)], control_region=[("q",)],
            decision_statistic="metric",
        )
        b1 = sealed_box(**kw, decision_threshold=0.05)
        b2 = sealed_box(**kw, decision_threshold=0.06)
        assert b1.pre_registration_hash != b2.pre_registration_hash

    def test_signal_region_change_changes_hash(self):
        kw = dict(
            name="x",
            parameters=[BoxParameter("a", ("p", "q", "r"))],
            decision_statistic="metric", decision_threshold=0.05,
        )
        b1 = sealed_box(signal_region=[("p",)], control_region=[("q",)], **kw)
        b2 = sealed_box(signal_region=[("p",), ("r",)],
                        control_region=[("q",)], **kw)
        assert b1.pre_registration_hash != b2.pre_registration_hash


# ----------------------------------------------------------------------------
# Frozen-immutability + state transitions
# ----------------------------------------------------------------------------

class TestImmutability:
    def test_sealed_box_is_frozen(self):
        box = sealed_box(
            name="x", parameters=[BoxParameter("a", ("p",))],
            signal_region=[("p",)], control_region=[],
            decision_statistic="m", decision_threshold=0.0,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            box.decision_threshold = 0.99  # type: ignore[misc]


class TestUnblindingStateTransitions:
    def _box(self):
        return sealed_box(
            name="t", parameters=[BoxParameter("a", ("p", "q"))],
            signal_region=[("p",)], control_region=[("q",)],
            decision_statistic="m", decision_threshold=0.0,
        )

    def test_authorize_from_sealed(self):
        b = self._box()
        b2 = b.authorize_unblinding(
            authorizing_party="CTO", justification="DMC consensus 2026-05-04",
        )
        assert b2.state == UnblindingState.AUTHORIZED
        assert "AUTHORIZED" in b2.notes
        # Hash unchanged — only state transitioned.
        assert b2.pre_registration_hash == b.pre_registration_hash

    def test_authorize_requires_party_and_justification(self):
        b = self._box()
        with pytest.raises(BoxValidationError):
            b.authorize_unblinding(authorizing_party="", justification="x")
        with pytest.raises(BoxValidationError):
            b.authorize_unblinding(authorizing_party="CTO", justification="")

    def test_cannot_skip_to_unblinded(self):
        b = self._box()
        with pytest.raises(BoxValidationError, match="must be AUTHORIZED"):
            b.mark_unblinded()

    def test_full_state_machine(self):
        b = self._box()
        b2 = b.authorize_unblinding("CTO", "approved")
        b3 = b2.mark_unblinded()
        assert b3.state == UnblindingState.UNBLINDED
        assert "UNBLINDED" in b3.notes

    def test_cannot_re_authorize(self):
        b = self._box().authorize_unblinding("CTO", "x")
        with pytest.raises(BoxValidationError, match="must be SEALED"):
            b.authorize_unblinding("CTO", "y")


# ----------------------------------------------------------------------------
# Placeholder data generator
# ----------------------------------------------------------------------------

class TestPlaceholderDataGenerator:
    def _box(self):
        return sealed_box(
            name="g",
            parameters=[
                BoxParameter("creative", ("A", "B", "C")),
                BoxParameter("cell", ("c1", "c2")),
            ],
            signal_region=[("A", "c1"), ("B", "c2")],
            control_region=[("C", "c1"), ("C", "c2")],
            decision_statistic="m", decision_threshold=0.0,
        )

    def test_generates_one_value_per_grid_point(self):
        box = self._box()
        data = placeholder_data_generator(box, seed=42)
        assert len(data) == len(box.parameter_grid())
        assert set(data.keys()) == set(box.parameter_grid())

    def test_seed_determinism(self):
        box = self._box()
        d1 = placeholder_data_generator(box, seed=42)
        d2 = placeholder_data_generator(box, seed=42)
        assert d1 == d2

    def test_different_seeds_different_data(self):
        box = self._box()
        d1 = placeholder_data_generator(box, seed=1)
        d2 = placeholder_data_generator(box, seed=2)
        assert d1 != d2

    def test_default_null_mean_zero(self):
        box = self._box()
        data = placeholder_data_generator(
            box, seed=0, null_mean=0.0, null_std=1.0,
        )
        # Sample mean should be near 0 (loose bound for n=6 points).
        sample_mean = sum(data.values()) / len(data)
        assert abs(sample_mean) < 2.0

    def test_custom_null_mean_offsets_data(self):
        box = self._box()
        d_zero = placeholder_data_generator(
            box, seed=0, null_mean=0.0, null_std=1.0,
        )
        d_offset = placeholder_data_generator(
            box, seed=0, null_mean=10.0, null_std=1.0,
        )
        # Same seed → corresponding values offset by ~10.
        for k in d_zero:
            assert abs((d_offset[k] - d_zero[k]) - 10.0) < 1e-9
