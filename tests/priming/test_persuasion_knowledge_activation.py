"""B / S6-prep.2 — persuasion_knowledge_activation field tests.

Per slice spec: pin schema extension + heuristic extractor + cascade
backward-compatibility + pipeline integration + zero-regression on
existing fields.

References:
    Friestad, M., & Wright, P. (1994). The Persuasion Knowledge Model:
        How people cope with persuasion attempts. Journal of Consumer
        Research, 21(1), 1-31.
"""
import asyncio
from datetime import datetime, timezone

import pytest

from adam.platform.intelligence.content_profiler import (
    EXPLICIT_DISCLOSURE_CUES,
    PERSUASION_IMPERATIVE_STEMS,
    PERSUASION_SUPERLATIVE_STEMS,
    SALESY_DICTION_CUES,
    compute_persuasion_knowledge_activation,
)
from adam.priming.pipeline import map_profile_to_signature
from adam.priming.signature import (
    PagePrimingSignature,
    SIGNATURE_DIMENSIONS,
    SIGNATURE_VERSION_V1,
    SIGNATURE_VERSION_V2,
)


# Helper to make a minimal valid PagePrimingSignature for tests.
def _base_sig_kwargs(**overrides):
    base = dict(
        url_hash="hash_abc",
        valence=0.0,
        arousal=0.0,
        regulatory_focus_priming="neutral",
        cognitive_load_estimate=0.0,
        activated_frames=tuple(),
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1 — schema accepts the new field
# ---------------------------------------------------------------------------

def test_signature_accepts_persuasion_knowledge_activation():
    """PagePrimingSignature can be constructed with the new field."""
    sig = PagePrimingSignature(
        **_base_sig_kwargs(persuasion_knowledge_activation=0.5),
        confidence_per_dimension={"persuasion_knowledge": 0.7},
    )
    assert sig.persuasion_knowledge_activation == 0.5
    assert sig.confidence_per_dimension["persuasion_knowledge"] == 0.7


# ---------------------------------------------------------------------------
# Test 2 — defaults
# ---------------------------------------------------------------------------

def test_default_persuasion_knowledge_activation_is_zero():
    """Field defaults to 0.0 (backward-compat for old call sites that
    don't pass the field)."""
    sig = PagePrimingSignature(**_base_sig_kwargs())
    assert sig.persuasion_knowledge_activation == 0.0


def test_default_signature_version_is_v2():
    """New signatures default to SIGNATURE_VERSION_V2 per the schema
    upgrade in B/S6-prep.2."""
    sig = PagePrimingSignature(**_base_sig_kwargs())
    assert sig.signature_version == SIGNATURE_VERSION_V2


# ---------------------------------------------------------------------------
# Test 3 — range validation [0, 1]
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("invalid_value", [-0.1, -1.0, 1.1, 2.0])
def test_persuasion_knowledge_activation_range_rejected(invalid_value):
    """Range invariant enforced in __post_init__."""
    with pytest.raises(ValueError, match="persuasion_knowledge_activation"):
        PagePrimingSignature(
            **_base_sig_kwargs(persuasion_knowledge_activation=invalid_value)
        )


@pytest.mark.parametrize("valid_value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_persuasion_knowledge_activation_in_range_accepted(valid_value):
    sig = PagePrimingSignature(
        **_base_sig_kwargs(persuasion_knowledge_activation=valid_value)
    )
    assert sig.persuasion_knowledge_activation == valid_value


# ---------------------------------------------------------------------------
# Test 4 — backward-compatible deserialization
# ---------------------------------------------------------------------------

def test_legacy_v1_row_deserializes_with_default():
    """An old v1 cached entry (missing persuasion_knowledge_activation
    key) deserializes to a signature with default 0.0 + preserved v1
    version. This is the cascade backward-compat invariant."""
    legacy_row = {
        "url_hash": "hash_legacy",
        "valence": 0.5,
        "arousal": 0.5,
        "regulatory_focus_priming": "promotion",
        "cognitive_load_estimate": 0.3,
        "activated_frames_json": '["social_proof"]',
        # NO persuasion_knowledge_activation key
        "confidence_per_dimension_json": '{"valence": 0.7}',
        "computed_at_iso": "2026-04-01T12:00:00+00:00",
        "signature_version": SIGNATURE_VERSION_V1,
    }
    sig = PagePrimingSignature.from_feature_store_row(legacy_row)
    assert sig.persuasion_knowledge_activation == 0.0
    assert sig.signature_version == SIGNATURE_VERSION_V1


def test_v2_row_round_trips():
    """A v2 row (with the new field) round-trips through serialize +
    deserialize cleanly."""
    sig = PagePrimingSignature(
        **_base_sig_kwargs(persuasion_knowledge_activation=0.42),
        confidence_per_dimension={"persuasion_knowledge": 0.85},
    )
    row = sig.to_feature_store_row()
    assert row["persuasion_knowledge_activation"] == 0.42
    sig_round = PagePrimingSignature.from_feature_store_row(row)
    assert sig_round.persuasion_knowledge_activation == 0.42
    assert sig_round.signature_version == SIGNATURE_VERSION_V2


# ---------------------------------------------------------------------------
# Test 5 — explicit disclosure marker detection
# ---------------------------------------------------------------------------

def test_extractor_detects_single_disclosure_marker():
    """One #ad cue → score ≥ 0.30, confidence ≥ 0.85 (explicit
    disclosure → high confidence)."""
    score, conf = compute_persuasion_knowledge_activation(
        "This is a #ad post about new running shoes."
    )
    assert score >= 0.30
    assert conf >= 0.85


# ---------------------------------------------------------------------------
# Test 6 — multiple disclosure markers cap at family limit
# ---------------------------------------------------------------------------

def test_extractor_caps_explicit_family_at_family_limit():
    """3 explicit cues → 3 × 0.30 = 0.90 raw, but family cap is 0.60.
    Total contribution from this family alone is ≤ 0.60."""
    score, conf = compute_persuasion_knowledge_activation(
        "Check out my #ad post! #sponsored content [ad]"
    )
    # No salesy or aggressive cues in this text, so total = explicit
    # contribution which is capped at 0.60.
    assert 0.55 <= score <= 0.65
    assert conf >= 0.85


# ---------------------------------------------------------------------------
# Test 7 — salesy diction detection
# ---------------------------------------------------------------------------

def test_extractor_detects_salesy_diction():
    """Three salesy cues → score ≥ 0.20, confidence ≥ 0.65."""
    score, conf = compute_persuasion_knowledge_activation(
        "Act now! Limited time offer. Buy now and get free shipping."
    )
    # 4 salesy cues × 0.10 = 0.40 raw → capped at family limit 0.30.
    # Plus aggressive language density from "act", "buy", "get" stems.
    assert score >= 0.20
    assert conf >= 0.65


# ---------------------------------------------------------------------------
# Test 8 — aggressive persuasion language detection
# ---------------------------------------------------------------------------

def test_extractor_detects_aggressive_persuasion_density():
    """High-density superlatives + imperatives → contribution within
    [0, 0.20] from this family. No explicit or salesy cues here, so
    total score reflects just the aggressive family."""
    text = (
        "The best ultimate amazing incredible perfect product! "
        "Try it. Get one. Claim yours. Grab the deal. Join us today."
    )
    score, conf = compute_persuasion_knowledge_activation(text)
    # Family contribution capped at 0.20.
    assert 0.0 < score <= 0.20
    # Confidence either 0.50 (uninformative) or 0.65 (if aggressive
    # contribution >= 0.10). Since density is very high here, expect
    # 0.65.
    assert conf in (0.50, 0.65)


# ---------------------------------------------------------------------------
# Test 9 — editorial content yields low activation
# ---------------------------------------------------------------------------

def test_extractor_low_on_editorial_content():
    """Editorial article → score ≤ 0.05, confidence = 0.50
    (uninformative neutral)."""
    text = (
        "Climate scientists report that ocean temperatures rose 0.5 "
        "degrees Celsius in the past decade. The findings come from "
        "satellite data analysis. Researchers note implications for "
        "marine ecosystems and coastal communities. Further studies "
        "are planned to investigate regional variation patterns. "
        "The data was collected over a multi-year observation window."
    )
    score, conf = compute_persuasion_knowledge_activation(text)
    assert score <= 0.05
    assert conf == 0.50


# ---------------------------------------------------------------------------
# Test 10 — three families combine correctly
# ---------------------------------------------------------------------------

def test_extractor_combines_three_families():
    """One disclosure marker + one salesy phrase + high superlative
    density. Total = sum of family contributions, clipped to [0, 1].
    Explicit disclosure dominates → confidence 0.85."""
    text = (
        "#ad — Limited time offer on the best ultimate product! "
        "Buy now, get incredible savings."
    )
    score, conf = compute_persuasion_knowledge_activation(text)
    # Explicit (0.30) + salesy (0.10 from "limited time offer" +
    # 0.10 from "buy now" → 0.20 capped at 0.30) + aggressive density.
    assert score >= 0.50
    assert conf == 0.85


# ---------------------------------------------------------------------------
# Test 11 — Feature Store cascade backward-compatibility
# ---------------------------------------------------------------------------

def test_feature_store_cascade_round_trip_with_new_field():
    """Cascade-store round trip preserves the new field through
    in-memory backends."""
    from adam.priming.feature_store import (
        InMemoryL2Backend,
        PagePrimingSignatureStore,
    )

    sig = PagePrimingSignature(
        **_base_sig_kwargs(
            url_hash="hash_cascade",
            persuasion_knowledge_activation=0.42,
        ),
        confidence_per_dimension={"persuasion_knowledge": 0.85},
    )

    async def run():
        store = PagePrimingSignatureStore(
            l1_capacity=10, l2_backend=InMemoryL2Backend(),
        )
        await store.put(sig)
        # Drop L1 to force L2 path.
        store.invalidate("hash_cascade")
        retrieved = await store.get("hash_cascade")
        assert retrieved.persuasion_knowledge_activation == 0.42

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Test 12 — signature_version incremented from V1 to V2
# ---------------------------------------------------------------------------

def test_signature_version_v2_distinct_from_v1():
    """V2 is a distinct, ordered upgrade from V1."""
    assert SIGNATURE_VERSION_V1 == "page_priming_v1"
    assert SIGNATURE_VERSION_V2 == "page_priming_v2"
    assert SIGNATURE_VERSION_V1 != SIGNATURE_VERSION_V2


def test_signature_dimensions_includes_new_field():
    """SIGNATURE_DIMENSIONS tuple lists the new dimension."""
    assert "persuasion_knowledge_activation" in SIGNATURE_DIMENSIONS


# ---------------------------------------------------------------------------
# Test 13 — pipeline integration end-to-end
# ---------------------------------------------------------------------------

def test_pipeline_integration_propagates_persuasion_knowledge():
    """ContentProfiler.profile() → map_profile_to_signature →
    PagePrimingSignature: persuasion_knowledge_activation flows
    through end-to-end."""
    profile_with_pk = {
        "ndf_profile": {
            "approach_avoidance": 0.5, "temporal_horizon": 0.5,
            "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
            "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
            "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
        },
        "mechanisms": [],
        "emotions": {},
        "confidence": 0.7,
        "persuasion_knowledge": {"activation": 0.42, "confidence": 0.85},
    }
    sig = map_profile_to_signature("https://example.com/x", profile_with_pk)
    assert sig.persuasion_knowledge_activation == 0.42
    assert sig.confidence_per_dimension.get("persuasion_knowledge") == 0.85


def test_pipeline_integration_default_when_pk_block_absent():
    """If profile dict lacks 'persuasion_knowledge' key, mapper
    defaults to (0.0, 0.5) — backward-compat for any profile producer
    that hasn't been updated."""
    profile_no_pk = {
        "ndf_profile": {"approach_avoidance": 0.5},
        "mechanisms": [],
        "emotions": {},
        "confidence": 0.5,
    }
    sig = map_profile_to_signature("https://example.com/y", profile_no_pk)
    assert sig.persuasion_knowledge_activation == 0.0
    assert sig.confidence_per_dimension.get("persuasion_knowledge") == 0.5


# ---------------------------------------------------------------------------
# Test 14 — zero-regression on existing PagePrimingSignature fields
# ---------------------------------------------------------------------------

def test_zero_regression_on_existing_fields():
    """Construct a PagePrimingSignature with all pre-A.2 fields
    explicitly specified. Assert all pre-A.2 field values retained
    correctly. New field takes default."""
    sig = PagePrimingSignature(
        url_hash="hash_zr",
        valence=0.42,
        arousal=0.71,
        regulatory_focus_priming="promotion",
        cognitive_load_estimate=0.18,
        activated_frames=("buy_now", "scarcity"),
        confidence_per_dimension={"valence": 0.95, "arousal": 0.85},
    )
    assert sig.valence == 0.42
    assert sig.arousal == 0.71
    assert sig.regulatory_focus_priming == "promotion"
    assert sig.cognitive_load_estimate == 0.18
    assert sig.activated_frames == ("buy_now", "scarcity")
    assert sig.confidence_per_dimension["valence"] == 0.95
    assert sig.persuasion_knowledge_activation == 0.0  # default


def test_existing_neutral_signature_includes_new_field():
    """neutral_signature() (cold-miss fallback) emits the new field
    at floor value with confidence floored too."""
    from adam.priming.signature import neutral_signature

    sig = neutral_signature("hash_x")
    assert sig.persuasion_knowledge_activation == 0.0
    assert sig.confidence_per_dimension["persuasion_knowledge"] == 0.0
    assert sig.signature_version == SIGNATURE_VERSION_V2


# ---------------------------------------------------------------------------
# Bonus — cue list shape pins (so future authors know the conventions)
# ---------------------------------------------------------------------------

def test_cue_constants_are_tuples():
    """Tuple-not-list ensures immutability of the cue lists."""
    assert isinstance(EXPLICIT_DISCLOSURE_CUES, tuple)
    assert isinstance(SALESY_DICTION_CUES, tuple)
    assert isinstance(PERSUASION_SUPERLATIVE_STEMS, tuple)
    assert isinstance(PERSUASION_IMPERATIVE_STEMS, tuple)


def test_cue_lists_non_empty():
    assert len(EXPLICIT_DISCLOSURE_CUES) > 0
    assert len(SALESY_DICTION_CUES) > 0
    assert len(PERSUASION_SUPERLATIVE_STEMS) > 0
    assert len(PERSUASION_IMPERATIVE_STEMS) > 0


def test_explicit_cues_lowercased():
    """Detection is case-insensitive via input lowering, but cue
    constants are pre-lowered for clarity."""
    for cue in EXPLICIT_DISCLOSURE_CUES:
        assert cue == cue.lower(), (
            f"cue {cue!r} not lowercased — case-insensitive matcher "
            f"lowers input but cues should be pre-lowered too"
        )
