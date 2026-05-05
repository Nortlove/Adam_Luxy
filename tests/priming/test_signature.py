"""S3.1 — PagePrimingSignature data class + serialization round-trip.

Per directive §S3.1: closes when type, serialization, and round-trip
tests pass. Range invariants enforced in __post_init__ are tested
separately.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from adam.priming import (
    PagePrimingSignature,
    SIGNATURE_DIMENSIONS,
    SIGNATURE_VERSION_V1,
    neutral_signature,
)


# ----------------------------------------------------------------------------
# Construction + range invariants
# ----------------------------------------------------------------------------

class TestConstruction:
    def test_minimal_construction(self):
        sig = PagePrimingSignature(
            url_hash="abc123",
            valence=0.5,
            arousal=0.7,
            regulatory_focus_priming="promotion",
            cognitive_load_estimate=0.3,
            activated_frames=("frame_a", "frame_b"),
        )
        assert sig.url_hash == "abc123"
        assert sig.signature_version == SIGNATURE_VERSION_V1
        assert sig.confidence_per_dimension == {}

    def test_frozen_dataclass_cannot_mutate(self):
        sig = PagePrimingSignature(
            url_hash="x", valence=0.0, arousal=0.0,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.0,
            activated_frames=tuple(),
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            sig.valence = 0.9  # type: ignore[misc]

    def test_signature_dimensions_pinned(self):
        # Pin the canonical dimension list so accidental schema
        # changes break this test, not silently change downstream
        # consumers.
        assert SIGNATURE_DIMENSIONS == (
            "valence", "arousal", "regulatory_focus_priming",
            "cognitive_load_estimate", "activated_frames",
        )


class TestRangeInvariants:
    @pytest.mark.parametrize("valence", [-1.0, -0.5, 0.0, 0.5, 1.0])
    def test_valence_in_range_accepted(self, valence):
        PagePrimingSignature(
            url_hash="x", valence=valence, arousal=0.5,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.5, activated_frames=tuple(),
        )

    @pytest.mark.parametrize("valence", [-1.01, 1.5, -10, 100])
    def test_valence_out_of_range_rejected(self, valence):
        with pytest.raises(ValueError, match="valence"):
            PagePrimingSignature(
                url_hash="x", valence=valence, arousal=0.5,
                regulatory_focus_priming="neutral",
                cognitive_load_estimate=0.5, activated_frames=tuple(),
            )

    @pytest.mark.parametrize("arousal", [-0.01, 1.01, -1, 2])
    def test_arousal_out_of_range_rejected(self, arousal):
        with pytest.raises(ValueError, match="arousal"):
            PagePrimingSignature(
                url_hash="x", valence=0.0, arousal=arousal,
                regulatory_focus_priming="neutral",
                cognitive_load_estimate=0.5, activated_frames=tuple(),
            )

    @pytest.mark.parametrize("focus", [
        "promotion", "prevention", "neutral",
    ])
    def test_regulatory_focus_accepted(self, focus):
        PagePrimingSignature(
            url_hash="x", valence=0.0, arousal=0.5,
            regulatory_focus_priming=focus,
            cognitive_load_estimate=0.5, activated_frames=tuple(),
        )

    def test_invalid_regulatory_focus_rejected(self):
        with pytest.raises(ValueError, match="regulatory_focus_priming"):
            PagePrimingSignature(
                url_hash="x", valence=0.0, arousal=0.5,
                regulatory_focus_priming="invalid",  # type: ignore[arg-type]
                cognitive_load_estimate=0.5, activated_frames=tuple(),
            )

    def test_cognitive_load_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="cognitive_load_estimate"):
            PagePrimingSignature(
                url_hash="x", valence=0.0, arousal=0.5,
                regulatory_focus_priming="neutral",
                cognitive_load_estimate=1.5, activated_frames=tuple(),
            )

    def test_activated_frames_must_be_tuple(self):
        with pytest.raises(TypeError, match="tuple"):
            PagePrimingSignature(
                url_hash="x", valence=0.0, arousal=0.5,
                regulatory_focus_priming="neutral",
                cognitive_load_estimate=0.5,
                activated_frames=["a", "b"],  # type: ignore[arg-type]
            )

    def test_confidence_value_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="confidence_per_dimension"):
            PagePrimingSignature(
                url_hash="x", valence=0.0, arousal=0.5,
                regulatory_focus_priming="neutral",
                cognitive_load_estimate=0.5,
                activated_frames=tuple(),
                confidence_per_dimension={"valence": 1.2},
            )


# ----------------------------------------------------------------------------
# Feature-store row serialization round-trip
# ----------------------------------------------------------------------------

class TestFeatureStoreRoundTrip:
    def test_round_trip_basic(self):
        ts = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
        sig = PagePrimingSignature(
            url_hash="hash_abc",
            valence=0.42, arousal=0.71,
            regulatory_focus_priming="promotion",
            cognitive_load_estimate=0.18,
            activated_frames=("buy_now", "social_proof", "scarcity"),
            confidence_per_dimension={
                "valence": 0.95, "arousal": 0.85,
                "regulatory_focus_priming": 0.9,
                "cognitive_load_estimate": 0.6,
                "activated_frames": 0.78,
            },
            computed_at=ts,
        )
        row = sig.to_feature_store_row()
        sig2 = PagePrimingSignature.from_feature_store_row(row)
        assert sig2 == sig

    def test_round_trip_empty_frames_and_confidences(self):
        ts = datetime(2026, 5, 4, tzinfo=timezone.utc)
        sig = PagePrimingSignature(
            url_hash="empty", valence=0.0, arousal=0.0,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.0,
            activated_frames=tuple(),
            confidence_per_dimension={},
            computed_at=ts,
        )
        row = sig.to_feature_store_row()
        sig2 = PagePrimingSignature.from_feature_store_row(row)
        assert sig2 == sig

    def test_row_is_scalar_only(self):
        """Pin Enhancement #30 contract: feature-store row contains
        no nested objects (lists/dicts JSON-encoded as strings)."""
        sig = PagePrimingSignature(
            url_hash="x", valence=0.1, arousal=0.2,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.3,
            activated_frames=("a", "b"),
            confidence_per_dimension={"valence": 0.9},
        )
        row = sig.to_feature_store_row()
        for k, v in row.items():
            assert isinstance(v, (str, int, float, bool)), (
                f"row[{k!r}] is non-scalar: {type(v).__name__}"
            )

    def test_round_trip_handles_native_datetime_input(self):
        """from_feature_store_row tolerates a datetime object instead
        of an ISO string (e.g., from an ORM that already parsed)."""
        ts = datetime(2026, 5, 4, 9, 30, tzinfo=timezone.utc)
        row = {
            "url_hash": "x", "valence": 0.0, "arousal": 0.0,
            "regulatory_focus_priming": "neutral",
            "cognitive_load_estimate": 0.0,
            "activated_frames_json": "[]",
            "confidence_per_dimension_json": "{}",
            "computed_at": ts,
            "signature_version": SIGNATURE_VERSION_V1,
        }
        sig = PagePrimingSignature.from_feature_store_row(row)
        assert sig.computed_at == ts


class TestToDict:
    def test_to_dict_uses_lists_and_iso_timestamp(self):
        ts = datetime(2026, 5, 4, tzinfo=timezone.utc)
        sig = PagePrimingSignature(
            url_hash="x", valence=0.5, arousal=0.5,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.5,
            activated_frames=("a", "b"),
            computed_at=ts,
        )
        d = sig.to_dict()
        assert d["activated_frames"] == ["a", "b"]
        assert d["computed_at"] == ts.isoformat()
        # Dict is JSON-serializable end-to-end
        json.dumps(d)


# ----------------------------------------------------------------------------
# Cold-miss neutral fallback
# ----------------------------------------------------------------------------

class TestNeutralFallback:
    def test_neutral_signature_all_floor(self):
        sig = neutral_signature("hash_xyz")
        assert sig.url_hash == "hash_xyz"
        assert sig.valence == 0.0
        assert sig.arousal == 0.0
        assert sig.regulatory_focus_priming == "neutral"
        assert sig.cognitive_load_estimate == 0.0
        assert sig.activated_frames == tuple()
        assert all(v == 0.0 for v in sig.confidence_per_dimension.values())

    def test_neutral_signature_round_trip(self):
        sig = neutral_signature("x")
        row = sig.to_feature_store_row()
        sig2 = PagePrimingSignature.from_feature_store_row(row)
        assert sig2 == sig

    def test_neutral_signature_carries_canonical_version(self):
        sig = neutral_signature("x")
        assert sig.signature_version == SIGNATURE_VERSION_V1
