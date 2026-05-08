"""E / S6-prep.4 — UserCohort compensatory_consumption_pattern
schema slot.

SCHEMA-ONLY scope per Q13 adjudication. Detection logic, offline-
pipeline integration, and bid-time access wiring are all DEFERRED
to F / S6.1 (the consumer slice — cells will condition on the flag
and dictate both the detection algorithm and the bid-time access
shape).

Pre-flight Pass C finding: persist_cohort_assignments
(adam/intelligence/cohort_discovery.py:474) uses explicit Cypher
field enumeration that writes only `size` + `mechanism_effectiveness_json`
to the UserCohort node. There is no full UserCohort load-from-Neo4j
function — cohorts are reconstructed each run by `discover_cohorts`.
The Cypher write extension is part of F's deferred offline-pipeline
work; until F lands, the new fields silently drop on Cypher persist.
This is BY DESIGN at the schema-only stage.

Test scope is therefore:
  - Schema acceptance (in-memory dataclass)
  - Default values
  - In-memory round-trip via dataclasses.asdict() ↔ UserCohort(**dict)
    — the canonical path that exists today
  - Backward-compatible deserialization for legacy dict-shaped entries
  - Range-invariant convention pinning
  - Zero-regression on existing UserCohort behavior
  - Schema slot pinned for F to consume
  - discover_cohorts pipeline still produces cohorts with safe defaults

References:
    Mead, N. L., Baumeister, R. F., Stillman, T. F., Rawn, C. D., &
        Vohs, K. D. (2010). Social exclusion causes people to spend
        and consume strategically in the service of affiliation.
        Journal of Consumer Research 37(5), 902-919.
    Loh, H. C. et al. (2021). Compensatory consumption: A systematic
        review. Journal of Consumer Behavior 20(5), 1144-1156.
"""
import dataclasses
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from adam.intelligence.cohort_discovery import (
    UserCohort,
    CohortDiscoveryService,
    get_cohort_discovery_service,
)


# ---------------------------------------------------------------------------
# Schema acceptance + defaults
# ---------------------------------------------------------------------------

class TestSchemaAcceptance:

    def test_user_cohort_accepts_new_fields(self):
        """UserCohort instantiates with the two new fields set."""
        c = UserCohort(
            cohort_id="cohort_test",
            size=200,
            sample_members=["u1", "u2", "u3"],
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.85,
        )
        assert c.compensatory_consumption_pattern is True
        assert c.compensatory_detection_confidence == 0.85

    def test_default_pattern_false_default_confidence_neutral(self):
        """Default values applied when new fields not specified.
        Default False → no compensatory pattern claimed for unmeasured
        cohorts; default 0.5 → uninformative neutral confidence
        (no evidence)."""
        c = UserCohort(
            cohort_id="cohort_default",
            size=100,
            sample_members=["u1"],
        )
        assert c.compensatory_consumption_pattern is False
        assert c.compensatory_detection_confidence == 0.5


# ---------------------------------------------------------------------------
# Backward-compatible (de)serialization via canonical in-memory path
# ---------------------------------------------------------------------------

class TestInMemoryRoundTrip:

    def test_asdict_to_constructor_round_trip_preserves_new_fields(self):
        """The canonical in-memory round-trip path is
        dataclasses.asdict() ↔ UserCohort(**dict). Pin that the new
        fields survive that round-trip."""
        original = UserCohort(
            cohort_id="cohort_x",
            size=250,
            sample_members=["u1", "u2"],
            dominant_mechanisms=["mimetic_desire", "social_proof"],
            mechanism_effectiveness={"social_proof": 0.72},
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.85,
        )
        as_dict = dataclasses.asdict(original)
        restored = UserCohort(**as_dict)
        assert restored.compensatory_consumption_pattern is True
        assert restored.compensatory_detection_confidence == 0.85
        assert restored == original

    def test_legacy_dict_without_new_fields_deserializes_with_defaults(self):
        """A pre-E persisted dict (only the 7 original fields) loads
        cleanly with safe defaults applied — no exceptions, no
        breakage."""
        legacy_dict = {
            "cohort_id": "cohort_legacy",
            "size": 100,
            "sample_members": ["u_legacy_1"],
            "dominant_mechanisms": ["temporal_construal"],
            "mechanism_effectiveness": {"temporal_construal": 0.65},
            "psychological_centroid": {},
            "discovered_at": datetime(2026, 5, 4, tzinfo=timezone.utc),
        }
        loaded = UserCohort(**legacy_dict)
        assert loaded.compensatory_consumption_pattern is False
        assert loaded.compensatory_detection_confidence == 0.5
        assert loaded.cohort_id == "cohort_legacy"
        assert loaded.size == 100


# ---------------------------------------------------------------------------
# Range-invariant convention
# ---------------------------------------------------------------------------

class TestRangeInvariantConvention:

    @pytest.mark.parametrize("conf", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_in_range_confidence_accepted(self, conf):
        """Plain @dataclass — no validator, but pin the documented
        [0, 1] convention by exercising the range. F's detection
        logic must respect this convention when populating values."""
        c = UserCohort(
            cohort_id="c", size=10, sample_members=[],
            compensatory_detection_confidence=conf,
        )
        assert c.compensatory_detection_confidence == conf

    @pytest.mark.parametrize("conf", [-0.1, 1.1])
    def test_out_of_range_confidence_construct_does_not_validate(
        self, conf,
    ):
        """Plain @dataclass does NOT validate at construct time —
        out-of-range values pass through. This test pins that
        convention rather than enforcement; F's detection logic +
        any future validator slice must add explicit validation if
        enforcement is needed."""
        c = UserCohort(
            cohort_id="c", size=10, sample_members=[],
            compensatory_detection_confidence=conf,
        )
        assert c.compensatory_detection_confidence == conf


# ---------------------------------------------------------------------------
# Zero-regression
# ---------------------------------------------------------------------------

class TestZeroRegression:

    def test_pre_e_user_cohort_construction_unchanged(self):
        """Construct a UserCohort with all 7 pre-E fields specified.
        All pre-E values + types preserved; new fields appear with
        defaults."""
        ts = datetime(2026, 5, 4, tzinfo=timezone.utc)
        c = UserCohort(
            cohort_id="cohort_pre_e",
            size=180,
            sample_members=["u1", "u2", "u3"],
            dominant_mechanisms=["social_proof", "mimetic_desire"],
            mechanism_effectiveness={
                "social_proof": 0.7, "mimetic_desire": 0.65,
            },
            psychological_centroid={"openness": 0.6, "extraversion": 0.7},
            discovered_at=ts,
        )
        # Pre-E fields preserved.
        assert c.cohort_id == "cohort_pre_e"
        assert c.size == 180
        assert c.sample_members == ["u1", "u2", "u3"]
        assert c.dominant_mechanisms == ["social_proof", "mimetic_desire"]
        assert c.mechanism_effectiveness == {
            "social_proof": 0.7, "mimetic_desire": 0.65,
        }
        assert c.psychological_centroid == {
            "openness": 0.6, "extraversion": 0.7,
        }
        assert c.discovered_at == ts
        # New fields default-populated.
        assert c.compensatory_consumption_pattern is False
        assert c.compensatory_detection_confidence == 0.5

    def test_default_cohort_pipeline_populates_new_fields(self):
        """Run _get_default_cohorts (the no-Neo4j fallback that ships
        in discover_cohorts when the driver is unavailable). Assert
        each resulting UserCohort carries the new fields with VALID
        values.

        Schema-evolution note: F.2 (commit landing this slice) wires
        detect_compensatory_consumption_pattern into _get_default_cohorts
        per the F.2 spec. Pre-F.2 this test asserted always (False, 0.5)
        defaults; post-F.2 the fields are populated by detection running
        on the default cohort signatures. We pin VALID-value invariants
        rather than specific values, since the values are F.2's contract.
        """
        service = CohortDiscoveryService(neo4j_driver=None)
        defaults = service._get_default_cohorts()
        assert len(defaults) > 0, (
            "default-cohort fallback should produce at least one cohort"
        )
        for c in defaults:
            assert isinstance(c.compensatory_consumption_pattern, bool), (
                f"default cohort {c.cohort_id} flag has wrong type: "
                f"{type(c.compensatory_consumption_pattern)}"
            )
            assert 0.0 <= c.compensatory_detection_confidence <= 1.0, (
                f"default cohort {c.cohort_id} confidence out of range: "
                f"{c.compensatory_detection_confidence}"
            )

    def test_singleton_factory_still_works(self):
        """get_cohort_discovery_service singleton path unaffected by
        schema extension."""
        # Reset singleton to ensure fresh state.
        import adam.intelligence.cohort_discovery as cd_mod
        cd_mod._service = None
        s1 = get_cohort_discovery_service()
        s2 = get_cohort_discovery_service()
        assert s1 is s2
        cd_mod._service = None  # cleanup


# ---------------------------------------------------------------------------
# Schema slot pinned for F to consume
# ---------------------------------------------------------------------------

class TestSchemaSlotPin:

    def test_field_types_and_defaults_pinned(self):
        """Pin the schema contract that F / S6.1 will consume:
        compensatory_consumption_pattern: bool = False
        compensatory_detection_confidence: float = 0.5

        Future F-driven slices may revise (e.g., enum instead of
        bool, additional fields) — but this test surfaces any such
        revision so it's an explicit decision, not an accident.
        """
        fields = {f.name: f for f in dataclasses.fields(UserCohort)}

        assert "compensatory_consumption_pattern" in fields
        assert "compensatory_detection_confidence" in fields

        ccp = fields["compensatory_consumption_pattern"]
        assert ccp.type is bool, (
            f"compensatory_consumption_pattern type changed: {ccp.type}"
        )
        assert ccp.default is False, (
            f"compensatory_consumption_pattern default changed: {ccp.default}"
        )

        cdc = fields["compensatory_detection_confidence"]
        assert cdc.type is float, (
            f"compensatory_detection_confidence type changed: {cdc.type}"
        )
        assert cdc.default == 0.5, (
            f"compensatory_detection_confidence default changed: {cdc.default}"
        )

    def test_schema_slot_documented_in_class(self):
        """Pin the slice-marker in the class definition so future
        readers know these fields are schema-slots awaiting F's
        detection logic + Cypher persistence extension."""
        import inspect
        source = inspect.getsource(UserCohort)
        assert "S6-prep.4" in source, (
            "schema-slot marker missing from UserCohort source"
        )
        assert "F / S6.1" in source, (
            "deferred-to-F marker missing from UserCohort source"
        )
