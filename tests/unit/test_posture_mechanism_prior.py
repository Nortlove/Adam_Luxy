"""Pin Phase 2 posture × mechanism compatibility prior matrix.

Directive line 970 — the soft prior that biases the cascade toward
matched (posture, mechanism) cells when bilateral edge data is sparse.

Tests pin:
  * POSTURE_BLEND × BLEND_COMPATIBLE → HIGH (matched)
  * POSTURE_VIGILANCE × VIGILANCE_ACTIVATING → HIGH (matched)
  * POSTURE_BLEND × VIGILANCE_ACTIVATING → LOW (mismatched)
  * POSTURE_VIGILANCE × BLEND_COMPATIBLE → LOW (mismatched)
  * POSTURE_NEUTRAL × * → MID (no signal)
  * POSTURE_UNKNOWN × * → MID (no signal)
  * Unknown posture string → MID (soft-fail)
  * Unknown mechanism string → MID (soft-fail)
  * Bulk accessor returns the full per-mechanism dict
  * Coverage: every posture × every taxonomy mechanism has a defined
    prior (no missing cells)
  * Bands: HIGH > MID > LOW with the documented values.
"""

from __future__ import annotations

import pytest

from adam.intelligence.mechanism_taxonomy import (
    MECHANISM_TAXONOMY,
    MechanismRouteCategory,
    blend_compatible_mechanisms,
    vigilance_activating_mechanisms,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)
from adam.intelligence.posture_mechanism_prior import (
    COMPATIBILITY_HIGH,
    COMPATIBILITY_LOW,
    COMPATIBILITY_MID,
    all_recognized_postures,
    compatibility_prior,
    mechanism_compatibility_for_posture,
)


# -----------------------------------------------------------------------------
# Band values (pin documented defaults — change requires explicit
# calibration update)
# -----------------------------------------------------------------------------


def test_band_values_are_documented_defaults():
    assert COMPATIBILITY_HIGH == 0.75
    assert COMPATIBILITY_LOW == 0.25
    assert COMPATIBILITY_MID == 0.50


def test_bands_are_strictly_ordered():
    assert COMPATIBILITY_LOW < COMPATIBILITY_MID < COMPATIBILITY_HIGH


# -----------------------------------------------------------------------------
# Matched diagonals → HIGH
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("mechanism", blend_compatible_mechanisms())
def test_blend_posture_with_blend_compatible_mech_is_high(mechanism):
    assert compatibility_prior(POSTURE_BLEND, mechanism) == COMPATIBILITY_HIGH


@pytest.mark.parametrize("mechanism", vigilance_activating_mechanisms())
def test_vigilance_posture_with_vigilance_mech_is_high(mechanism):
    assert (
        compatibility_prior(POSTURE_VIGILANCE, mechanism) == COMPATIBILITY_HIGH
    )


# -----------------------------------------------------------------------------
# Mismatched diagonals → LOW
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("mechanism", vigilance_activating_mechanisms())
def test_blend_posture_with_vigilance_mech_is_low(mechanism):
    assert compatibility_prior(POSTURE_BLEND, mechanism) == COMPATIBILITY_LOW


@pytest.mark.parametrize("mechanism", blend_compatible_mechanisms())
def test_vigilance_posture_with_blend_compatible_mech_is_low(mechanism):
    assert (
        compatibility_prior(POSTURE_VIGILANCE, mechanism) == COMPATIBILITY_LOW
    )


# -----------------------------------------------------------------------------
# Neutral / unknown postures → MID
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("mechanism", sorted(MECHANISM_TAXONOMY.keys()))
def test_neutral_posture_returns_mid_for_every_mech(mechanism):
    assert compatibility_prior(POSTURE_NEUTRAL, mechanism) == COMPATIBILITY_MID


@pytest.mark.parametrize("mechanism", sorted(MECHANISM_TAXONOMY.keys()))
def test_unknown_posture_returns_mid_for_every_mech(mechanism):
    assert compatibility_prior(POSTURE_UNKNOWN, mechanism) == COMPATIBILITY_MID


# -----------------------------------------------------------------------------
# Soft-fail on unrecognized labels → MID
# -----------------------------------------------------------------------------


def test_unknown_posture_string_returns_mid():
    """Unknown posture (not in the recognized set) → soft-fail to MID."""
    assert (
        compatibility_prior("not_a_posture", "automatic_evaluation")
        == COMPATIBILITY_MID
    )


def test_unknown_mechanism_string_returns_mid():
    """Unknown mechanism (not in MECHANISM_TAXONOMY) → soft-fail to MID."""
    assert (
        compatibility_prior(POSTURE_BLEND, "fictional_mechanism")
        == COMPATIBILITY_MID
    )


def test_both_unknown_returns_mid():
    assert (
        compatibility_prior("garbage", "garbage_mechanism")
        == COMPATIBILITY_MID
    )


# -----------------------------------------------------------------------------
# Bulk accessor
# -----------------------------------------------------------------------------


def test_bulk_accessor_returns_every_taxonomy_mechanism_when_unfiltered():
    result = mechanism_compatibility_for_posture(POSTURE_BLEND)
    assert set(result.keys()) == set(MECHANISM_TAXONOMY.keys())
    # Every value must be one of the three bands.
    for v in result.values():
        assert v in (COMPATIBILITY_HIGH, COMPATIBILITY_LOW, COMPATIBILITY_MID)


def test_bulk_accessor_filters_to_requested_mechanisms():
    requested = ["automatic_evaluation", "attention_dynamics"]
    result = mechanism_compatibility_for_posture(POSTURE_BLEND, requested)
    assert set(result.keys()) == set(requested)
    # automatic_evaluation is BLEND_COMPATIBLE → HIGH on POSTURE_BLEND
    assert result["automatic_evaluation"] == COMPATIBILITY_HIGH
    # attention_dynamics is VIGILANCE_ACTIVATING → LOW on POSTURE_BLEND
    assert result["attention_dynamics"] == COMPATIBILITY_LOW


def test_bulk_accessor_handles_unknown_mechanism_in_list():
    """Unknown mechanism in the request list → soft-fail to MID, not omitted."""
    requested = ["automatic_evaluation", "fictional_mech"]
    result = mechanism_compatibility_for_posture(POSTURE_BLEND, requested)
    assert "automatic_evaluation" in result
    assert "fictional_mech" in result
    assert result["fictional_mech"] == COMPATIBILITY_MID


def test_bulk_accessor_neutral_posture_returns_mid_for_every_mech():
    result = mechanism_compatibility_for_posture(POSTURE_NEUTRAL)
    assert all(v == COMPATIBILITY_MID for v in result.values())


# -----------------------------------------------------------------------------
# Coverage — every (posture × mechanism) cell has a defined prior
# -----------------------------------------------------------------------------


def test_coverage_every_cell_has_defined_prior():
    """No missing cells in the 4×9 matrix. Every posture label paired
    with every taxonomy mechanism returns one of the three bands."""
    bands = {COMPATIBILITY_HIGH, COMPATIBILITY_LOW, COMPATIBILITY_MID}
    for posture in all_recognized_postures():
        for mechanism in MECHANISM_TAXONOMY:
            v = compatibility_prior(posture, mechanism)
            assert v in bands, (
                f"({posture}, {mechanism}) → {v}, not in {bands}"
            )


def test_recognized_postures_match_documented_set():
    """The set of recognized postures must include exactly the four
    canonical labels. Drift (e.g., adding a fifth class) requires a
    deliberate update here, not silent acceptance."""
    assert set(all_recognized_postures()) == {
        POSTURE_BLEND,
        POSTURE_VIGILANCE,
        POSTURE_NEUTRAL,
        POSTURE_UNKNOWN,
    }


def test_taxonomy_classification_invariants():
    """Sanity-pin: every taxonomy mechanism has a category in the
    MechanismRouteCategory enum. Without this, the prior matrix would
    have an undefined cell on a new category."""
    for name, classification in MECHANISM_TAXONOMY.items():
        assert classification.category in (
            MechanismRouteCategory.BLEND_COMPATIBLE,
            MechanismRouteCategory.VIGILANCE_ACTIVATING,
        ), f"mechanism {name} has unhandled category {classification.category}"
