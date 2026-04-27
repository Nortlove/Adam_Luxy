"""Pin the publication-bias-correction registry against drift.

Discipline anchors:
    - Doc 3 §I.8 directive: ship the publication-bias-corrected annotation
      across all 9 ADAM mechanisms. The registry is what makes that claim
      operational. These tests pin the registry's coverage and integrity.
    - UNKNOWN_PENDING_REVIEW is honest interim; the test ensures every
      such entry has stated retirement triggers in its notes (to prevent
      it from being silently treated as final).
    - No entry uses UNCORRECTED operationally. UNCORRECTED is for
      documentation-only.
"""

from __future__ import annotations

from adam.core.learning.effect_size_correction import (
    CorrectionMethod,
    MECHANISM_EFFECT_REGISTRY,
    PublicationBiasCorrectedEffect,
    correction_metadata_for_response,
    mechanism_corrected_effect,
)


# Mechanisms ADAM actually scores in the cascade L3 path. The registry
# MUST cover these — gaps here mean cascade outputs lack provenance.
_CASCADE_MECHANISMS = {
    "authority",
    "social_proof",
    "scarcity",
    "loss_aversion",
    "commitment",
    "liking",
    "reciprocity",
    "curiosity",
    "cognitive_ease",
    "unity",
}


def test_registry_covers_all_cascade_mechanisms():
    """Every mechanism the cascade scores MUST have a registry entry.
    Failing this test means a cascade output's lift claim has no
    publication-bias-correction provenance."""
    missing = _CASCADE_MECHANISMS - set(MECHANISM_EFFECT_REGISTRY.keys())
    assert not missing, (
        f"Mechanisms in cascade L3 scoring but missing from "
        f"MECHANISM_EFFECT_REGISTRY: {sorted(missing)}. Doc 3 §I.8 "
        f"requires every mechanism carry the corrected annotation."
    )


def test_no_entry_uses_uncorrected_operationally():
    """UNCORRECTED is documentation-only. Any operational entry using
    it would mean the registry is shipping inflated published values
    as if they were corrected — exactly the failure mode Doc 3 §I.8
    flags as 'must ship before LUXY outcome claims.'"""
    for name, eff in MECHANISM_EFFECT_REGISTRY.items():
        assert eff.correction_method != CorrectionMethod.UNCORRECTED, (
            f"Mechanism {name!r} uses UNCORRECTED — that method is for "
            f"documentation only and must not appear in the operational "
            f"registry."
        )


def test_pre_registered_entries_have_pre_registered_d():
    """PRE_REGISTERED method MUST carry the actual pre-registered effect
    (not None). This is enforced by __post_init__ in the dataclass; the
    test pins it at the registry level too."""
    for name, eff in MECHANISM_EFFECT_REGISTRY.items():
        if eff.correction_method == CorrectionMethod.PRE_REGISTERED:
            assert eff.pre_registered_d is not None, (
                f"{name!r} uses PRE_REGISTERED but has no pre_registered_d"
            )


def test_unknown_pending_review_entries_carry_retirement_trigger():
    """UNKNOWN_PENDING_REVIEW is honest interim shrinkage. Each such
    entry MUST state its retirement trigger in notes — otherwise the
    interim value silently becomes treated as final."""
    for name, eff in MECHANISM_EFFECT_REGISTRY.items():
        if eff.correction_method == CorrectionMethod.UNKNOWN_PENDING_REVIEW:
            notes = eff.notes.lower()
            assert "retires" in notes or "retirement" in notes or "pending" in notes, (
                f"{name!r} is UNKNOWN_PENDING_REVIEW but notes lack a stated "
                f"retirement trigger. Notes must say when this entry "
                f"transitions to a defensible correction method. Notes: "
                f"{eff.notes[:200]}"
            )


def test_corrected_d_smaller_than_published_g_for_corrected_methods():
    """Publication-bias correction means shrinkage. corrected_d MUST be
    ≤ published_g for any genuinely-corrected entry (the inverse would
    be inflation, not correction)."""
    methods_that_must_shrink = {
        CorrectionMethod.PRE_REGISTERED,
        CorrectionMethod.ROBMA_MEDIAN,
        CorrectionMethod.SCHIMMACK_RATIO,
        CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    }
    for name, eff in MECHANISM_EFFECT_REGISTRY.items():
        if eff.correction_method in methods_that_must_shrink:
            assert eff.corrected_d <= eff.published_g, (
                f"{name!r}: corrected_d={eff.corrected_d} > "
                f"published_g={eff.published_g}. Correction inflated "
                f"the effect — that is not correction."
            )


def test_each_entry_has_at_least_one_citation():
    """No bare claims. Every corrected effect carries citations so a
    downstream auditor can trace the provenance."""
    for name, eff in MECHANISM_EFFECT_REGISTRY.items():
        assert len(eff.citations) >= 1, (
            f"{name!r} has no citations — provenance untraceable"
        )


def test_lookup_helper_returns_none_for_unknown():
    """mechanism_corrected_effect MUST return None (not a default value)
    for unknown mechanisms — silently returning a default would mask
    coverage gaps."""
    assert mechanism_corrected_effect("not_a_real_mechanism") is None


def test_metadata_response_for_known_mechanism():
    """The response-block helper produces structural fields a partner
    or regulatory consumer can cite directly."""
    meta = correction_metadata_for_response("loss_aversion")
    assert meta["mechanism"] == "loss_aversion_framing"
    assert meta["published_g"] > 0
    assert 0 < meta["corrected_d"] <= meta["published_g"]
    assert meta["correction_method"] in {
        m.value for m in CorrectionMethod
    }
    assert isinstance(meta["citations"], list) and len(meta["citations"]) >= 1
    assert "pending_review" in meta


def test_metadata_response_for_unknown_mechanism_flags_not_registered():
    """Unknown mechanism MUST surface as NOT_REGISTERED rather than
    silently returning a default-shaped dict — the consumer needs to
    know provenance is unavailable."""
    meta = correction_metadata_for_response("not_a_real_mechanism")
    assert meta["correction_status"] == "NOT_REGISTERED"
    assert "do not carry" in meta["note"].lower() or "un-validated" in meta["note"].lower()


def test_pending_review_flag_surfaced_in_metadata():
    """The pending_review flag is the explicit interim signal partners
    and regulators need to interpret claims correctly."""
    meta_known = correction_metadata_for_response("authority")
    assert meta_known["pending_review"] is True

    meta_pre_reg = correction_metadata_for_response("construal_level_matching")
    assert meta_pre_reg["pending_review"] is False
