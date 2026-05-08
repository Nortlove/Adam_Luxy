"""W.2a — BuyerUncertaintyProfile schema extension tests.

Pin: 4 new W.2a fields with safe defaults; backward-compat
deserialization of pre-W.2a Redis entries; round-trip preserves
new fields.
"""
import pytest

from adam.intelligence.information_value import BuyerUncertaintyProfile


class TestSchemaDefaults:

    def test_new_profile_has_archetype_none(self):
        p = BuyerUncertaintyProfile(buyer_id="u")
        assert p.archetype is None
        assert p.archetype_assigned_at is None
        assert p.archetype_reassigned is False
        assert p.bids_since_archetype_assignment == 0

    def test_explicit_archetype_construction(self):
        p = BuyerUncertaintyProfile(
            buyer_id="u",
            archetype="analyst",
            archetype_assigned_at="2026-05-08T12:00:00+00:00",
            archetype_reassigned=False,
            bids_since_archetype_assignment=10,
        )
        assert p.archetype == "analyst"
        assert p.bids_since_archetype_assignment == 10


class TestSerializationRoundTrip:

    def test_to_dict_includes_new_fields(self):
        p = BuyerUncertaintyProfile(
            buyer_id="u",
            archetype="explorer",
            archetype_assigned_at="2026-05-08T08:00:00+00:00",
            archetype_reassigned=True,
            bids_since_archetype_assignment=20,
        )
        d = p.to_dict()
        assert d["archetype"] == "explorer"
        assert d["archetype_assigned_at"] == "2026-05-08T08:00:00+00:00"
        assert d["archetype_reassigned"] is True
        assert d["bids_since_archetype_assignment"] == 20

    def test_from_dict_round_trip(self):
        original = BuyerUncertaintyProfile(
            buyer_id="u",
            archetype="connector",
            archetype_assigned_at="2026-05-08T15:30:00+00:00",
            archetype_reassigned=False,
            bids_since_archetype_assignment=7,
        )
        d = original.to_dict()
        restored = BuyerUncertaintyProfile.from_dict(d)
        assert restored.archetype == "connector"
        assert restored.archetype_assigned_at == "2026-05-08T15:30:00+00:00"
        assert restored.archetype_reassigned is False
        assert restored.bids_since_archetype_assignment == 7


class TestBackwardCompat:

    def test_legacy_dict_without_w2a_fields_deserializes(self):
        """Pre-W.2a Redis entries lack the 4 new fields. from_dict
        must apply safe defaults so legacy cache rows round-trip
        cleanly."""
        legacy = {
            "buyer_id": "u_legacy",
            "total_interactions": 5,
            "total_conversions": 1,
            "constructs": {},
        }
        p = BuyerUncertaintyProfile.from_dict(legacy)
        assert p.archetype is None
        assert p.archetype_assigned_at is None
        assert p.archetype_reassigned is False
        assert p.bids_since_archetype_assignment == 0
        assert p.buyer_id == "u_legacy"
        assert p.total_interactions == 5

    def test_partial_w2a_fields_deserialize_safely(self):
        """A dict with archetype but missing the other W.2a fields
        applies defaults to the missing ones."""
        partial = {
            "buyer_id": "u",
            "archetype": "guardian",
            # Missing: archetype_assigned_at, archetype_reassigned,
            # bids_since_archetype_assignment
        }
        p = BuyerUncertaintyProfile.from_dict(partial)
        assert p.archetype == "guardian"
        assert p.archetype_assigned_at is None
        assert p.archetype_reassigned is False
        assert p.bids_since_archetype_assignment == 0
