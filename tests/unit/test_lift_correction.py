"""Pin C3 — publication-bias-corrected lift constants.

Discipline anchors:
    - The uncorrected Matz headline (40-54% lift) is widely cited and
      widely WRONG — it ignores publication bias on the published g.
      The pre-registered effect (OR=1.30, d=0.15) yields ~31% lift,
      and that's what ADAM operates on.
    - d_to_relative_lift_pct uses the Chinn 2000 conversion
      OR = exp(d·π/√3) — peer-reviewed standard in evidence synthesis.
      Drift in this formula would silently change every cascade lift
      number.
    - The cascade pulls PERSONALITY_MATCHING_EFFECT.corrected_d at
      runtime, so a future correction (e.g., new RoBMA multiverse
      result) propagates to lift estimates without a separate cascade
      change.
"""

from __future__ import annotations

import pytest

from adam.api.stackadapt.bilateral_cascade import derive_lift_from_composite
from adam.core.learning.effect_size_correction import (
    PERSONALITY_MATCHING_EFFECT,
    d_to_relative_lift_pct,
)


# -----------------------------------------------------------------------------
# d_to_relative_lift_pct math
# -----------------------------------------------------------------------------


def test_d_to_lift_zero_is_zero():
    """d=0 → OR=1 → lift=0% exactly."""
    assert d_to_relative_lift_pct(0.0) == 0.0


def test_d_to_lift_for_matz_corrected_is_about_31():
    """Matz 2017 pre-registered d=0.15 → ~31% lift. This is the
    canonical anchor the cascade now uses."""
    lift = d_to_relative_lift_pct(0.15)
    assert 30.0 < lift < 33.0


def test_d_to_lift_for_matz_uncorrected_published_is_about_72():
    """Matz 2017 published g=0.30 (uncorrected) → ~72% lift. The
    headline 40-54% number is itself slightly conservative vs the raw
    OR conversion — the difference is the linear approximation often
    used in marketing decks."""
    lift = d_to_relative_lift_pct(0.30)
    assert 70.0 < lift < 75.0


def test_d_to_lift_monotonic():
    """Larger effects → larger lift. Pin so a sign flip can't hide."""
    assert d_to_relative_lift_pct(0.5) > d_to_relative_lift_pct(0.3)
    assert d_to_relative_lift_pct(0.3) > d_to_relative_lift_pct(0.15)
    assert d_to_relative_lift_pct(0.15) > d_to_relative_lift_pct(0.05)


def test_d_to_lift_negative_is_negative():
    """Negative d (backfire region) yields negative lift."""
    assert d_to_relative_lift_pct(-0.15) < 0.0


# -----------------------------------------------------------------------------
# Cascade integration — derive_lift_from_composite uses corrected ceiling
# -----------------------------------------------------------------------------


def test_cascade_lift_at_full_alignment_uses_corrected_ceiling():
    """At composite=1.0, full evidence, full confidence: lift should
    approximate the publication-bias-corrected ceiling (~31%) — NOT
    the uncorrected 54% headline."""
    ctr, conv = derive_lift_from_composite(
        composite=1.0, confidence=1.0, edge_count=10000,
    )
    # Within tolerance of the d=0.15 ceiling (~31%)
    assert 28.0 < conv < 35.0
    # Cascade lift (without a separate empirical CTR correction) uses
    # the same ceiling for both
    assert 28.0 < ctr < 35.0


def test_cascade_lift_zero_alignment_zero_lift():
    """composite=0 → no lift regardless of evidence/confidence."""
    ctr, conv = derive_lift_from_composite(
        composite=0.0, confidence=1.0, edge_count=10000,
    )
    assert ctr == 0.0
    assert conv == 0.0


def test_cascade_lift_low_evidence_discounted():
    """Few edges → evidence factor < 1 → lift below ceiling."""
    full_evidence_ctr, full_evidence_conv = derive_lift_from_composite(
        composite=1.0, confidence=1.0, edge_count=10000,
    )
    low_evidence_ctr, low_evidence_conv = derive_lift_from_composite(
        composite=1.0, confidence=1.0, edge_count=5,
    )
    assert low_evidence_conv < full_evidence_conv
    assert low_evidence_ctr < full_evidence_ctr


def test_cascade_lift_does_not_exceed_uncorrected_headline():
    """Sanity: the cascade should NEVER report 54%+ lift, because
    that's the uncorrected published value. Even at maxed-out
    composite/confidence/evidence, the ceiling is the corrected ~31%."""
    ctr, conv = derive_lift_from_composite(
        composite=1.0, confidence=1.0, edge_count=100000,
    )
    assert conv < 54.0, (
        "Cascade conversion lift hit uncorrected Matz headline — "
        "publication-bias correction was bypassed somewhere"
    )
    assert ctr < 40.0, (
        "Cascade CTR lift hit uncorrected Matz headline — "
        "publication-bias correction was bypassed somewhere"
    )


# -----------------------------------------------------------------------------
# Pin the canonical effect identity
# -----------------------------------------------------------------------------


def test_personality_matching_effect_uses_pre_registered_d():
    """PERSONALITY_MATCHING_EFFECT must remain pre-registered. A future
    edit that flips it back to UNCORRECTED would silently revert the
    correction across the system."""
    assert PERSONALITY_MATCHING_EFFECT.correction_method.value == "pre_registered"
    assert PERSONALITY_MATCHING_EFFECT.corrected_d == 0.15
