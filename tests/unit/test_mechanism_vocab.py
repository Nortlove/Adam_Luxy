"""Pin Slice 11 — mechanism vocabulary unification.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Translation derived from Cialdini 1984/2021 + Bargh-lineage
        canonical-mechanism substrate. Identity translation for the
        5 mechanisms in both vocabularies (mimetic_desire,
        embodied_cognition, temporal_construal, attention_dynamics,
        identity_construction).

    (b) Boundary anchors:
          - every cohort mechanism has a translation
          - every translation target is a canonical taxonomy mechanism
          - identity translation for canonical inputs
          - cohort → canonical preserves BLEND/VIGILANCE diagonal where
            psychologically motivated
          - unknown inputs return unchanged (soft-fail, lenient mode)
          - to_canonical_or_none returns None for unknown inputs
          - empty string returned unchanged
          - downstream consumers (compatibility_prior) pick up the
            translation transparently

    (c) calibration_pending=False — translation is structural.

    (d) Honest tags — what is NOT tested here:
          - Bidirectional translation (canonical → cohort) — sibling.
          - Multi-mechanism / blended translations — sibling.
"""

from __future__ import annotations

import pytest

from adam.intelligence.mechanism_taxonomy import (
    MECHANISM_TAXONOMY,
    MechanismRouteCategory,
)
from adam.intelligence.mechanism_vocab import (
    COHORT_TO_CANONICAL,
    cohort_mechanisms_without_translation,
    to_canonical,
    to_canonical_or_none,
    translation_targets_not_in_taxonomy,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_VIGILANCE,
)
from adam.intelligence.per_user_posterior_modulation import (
    MECHANISM_DIMENSION_MAP,
)
from adam.intelligence.posture_mechanism_prior import (
    COMPATIBILITY_HIGH,
    COMPATIBILITY_LOW,
    compatibility_prior,
)


# -----------------------------------------------------------------------------
# Coverage invariants
# -----------------------------------------------------------------------------


def test_every_cohort_mechanism_has_a_translation():
    """No cohort-side mechanism in MECHANISM_DIMENSION_MAP can be
    missing from COHORT_TO_CANONICAL — that would silently regress
    posture lookups on production cascades."""
    untranslated = cohort_mechanisms_without_translation()
    assert untranslated == [], (
        f"cohort mechanisms without canonical translation: {untranslated}"
    )


def test_every_translation_target_is_canonical():
    """Every translation value must resolve in MECHANISM_TAXONOMY."""
    out_of_scope = translation_targets_not_in_taxonomy()
    assert out_of_scope == [], (
        f"translation targets not in MECHANISM_TAXONOMY: {out_of_scope}"
    )


def test_translation_map_size_matches_dimension_map():
    """COHORT_TO_CANONICAL covers all 18 cohort mechanisms."""
    assert set(COHORT_TO_CANONICAL.keys()) == set(MECHANISM_DIMENSION_MAP.keys())


# -----------------------------------------------------------------------------
# Identity translations (5 mechanisms in both vocabs)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", [
    "mimetic_desire",
    "embodied_cognition",
    "temporal_construal",
    "attention_dynamics",
    "identity_construction",
])
def test_identity_translation_for_canonical_mechanisms(name):
    """Canonical mechanisms translate to themselves."""
    assert to_canonical(name) == name


# -----------------------------------------------------------------------------
# Cohort → canonical translations
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("cohort,canonical", [
    ("social_proof", "mimetic_desire"),
    ("liking", "mimetic_desire"),
    ("unity", "mimetic_desire"),
    ("authority", "automatic_evaluation"),
    ("cognitive_ease", "automatic_evaluation"),
    ("anchoring", "automatic_evaluation"),
    ("reciprocity", "automatic_evaluation"),
    ("regulatory_focus", "linguistic_framing"),
    ("storytelling", "linguistic_framing"),
    ("curiosity", "wanting_liking_dissociation"),
    ("scarcity", "attention_dynamics"),
    ("loss_aversion", "attention_dynamics"),
    ("commitment", "identity_construction"),
])
def test_cohort_to_canonical_translation(cohort, canonical):
    assert to_canonical(cohort) == canonical


# -----------------------------------------------------------------------------
# BLEND / VIGILANCE diagonal preservation
# -----------------------------------------------------------------------------


_BLEND_COHORT = {"social_proof", "liking", "unity", "authority",
                 "cognitive_ease", "anchoring", "reciprocity",
                 "regulatory_focus", "storytelling", "curiosity"}

_VIGILANCE_COHORT = {"scarcity", "loss_aversion", "commitment"}


@pytest.mark.parametrize("cohort", sorted(_BLEND_COHORT))
def test_blend_cohort_translates_to_blend_canonical(cohort):
    canonical = to_canonical(cohort)
    cls = MECHANISM_TAXONOMY[canonical]
    assert cls.category == MechanismRouteCategory.BLEND_COMPATIBLE


@pytest.mark.parametrize("cohort", sorted(_VIGILANCE_COHORT))
def test_vigilance_cohort_translates_to_vigilance_canonical(cohort):
    canonical = to_canonical(cohort)
    cls = MECHANISM_TAXONOMY[canonical]
    assert cls.category == MechanismRouteCategory.VIGILANCE_ACTIVATING


# -----------------------------------------------------------------------------
# Soft-fail behavior
# -----------------------------------------------------------------------------


def test_unknown_mechanism_returned_unchanged():
    assert to_canonical("not_a_real_mechanism") == "not_a_real_mechanism"


def test_empty_string_returned_unchanged():
    assert to_canonical("") == ""


def test_to_canonical_or_none_returns_none_for_unknown():
    assert to_canonical_or_none("not_a_real_mechanism") is None
    assert to_canonical_or_none("") is None


def test_to_canonical_or_none_returns_canonical_for_known():
    assert to_canonical_or_none("social_proof") == "mimetic_desire"
    assert to_canonical_or_none("mimetic_desire") == "mimetic_desire"


# -----------------------------------------------------------------------------
# Downstream effect — compatibility_prior picks up translation
# -----------------------------------------------------------------------------


def test_cohort_mechanism_no_longer_soft_fails_to_mid():
    """Pre-Slice-11: compatibility_prior(POSTURE_BLEND, 'social_proof')
    returned MID (soft-fail) because social_proof wasn't in MECHANISM_TAXONOMY.
    Post-Slice-11: it should resolve via translation to mimetic_desire
    (BLEND_COMPATIBLE) → HIGH on POSTURE_BLEND."""
    prior = compatibility_prior(POSTURE_BLEND, "social_proof")
    assert prior == COMPATIBILITY_HIGH


def test_cohort_vigilance_mechanism_resolves_low_on_blend_posture():
    """scarcity → attention_dynamics (VIGILANCE_ACTIVATING) → LOW on POSTURE_BLEND."""
    prior = compatibility_prior(POSTURE_BLEND, "scarcity")
    assert prior == COMPATIBILITY_LOW


def test_cohort_vigilance_mechanism_resolves_high_on_vigilance_posture():
    """scarcity → attention_dynamics → HIGH on POSTURE_VIGILANCE."""
    prior = compatibility_prior(POSTURE_VIGILANCE, "scarcity")
    assert prior == COMPATIBILITY_HIGH


def test_cohort_blend_mechanism_resolves_low_on_vigilance_posture():
    """social_proof → mimetic_desire (BLEND_COMPATIBLE) → LOW on POSTURE_VIGILANCE."""
    prior = compatibility_prior(POSTURE_VIGILANCE, "social_proof")
    assert prior == COMPATIBILITY_LOW


def test_authority_resolves_to_automatic_evaluation_blend():
    """authority is a Cialdini principle that operates via deference /
    automatic-evaluation in the Bargh substrate. Translates to
    automatic_evaluation (BLEND_COMPATIBLE) → HIGH on POSTURE_BLEND."""
    prior = compatibility_prior(POSTURE_BLEND, "authority")
    assert prior == COMPATIBILITY_HIGH


# -----------------------------------------------------------------------------
# Idempotence — translating an already-canonical name is a no-op
# -----------------------------------------------------------------------------


def test_translation_is_idempotent():
    """to_canonical(to_canonical(x)) == to_canonical(x) for any x."""
    for name in list(COHORT_TO_CANONICAL.keys()) + ["unknown_x"]:
        once = to_canonical(name)
        twice = to_canonical(once)
        assert once == twice
