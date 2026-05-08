"""F.2 / S6.1 (2 of 2) — compensatory_consumption_pattern detection.

Pin the two-criterion heuristic detection function + thresholds +
pipeline integration + persistence-payload extension. The detection
uses Cialdini-mechanism vocabulary (the actual cohort_discovery
output per Q13 finding) as a proxy for compensatory-consumption
literature constructs — heuristic substrate, NOT load-bearing.

References (theoretical motivation, NOT empirical validation on
this platform's data):
    Mead, N. L., Baumeister, R. F., Stillman, T. F., Rawn, C. D., &
        Vohs, K. D. (2010). Social exclusion causes people to spend
        and consume strategically in the service of affiliation.
        Journal of Consumer Research 37(5), 902-919.
    Loh, H. C. et al. (2021). Compensatory consumption: A systematic
        review. Journal of Consumer Behavior 20(5), 1144-1156.
    Cialdini, R. B. (2009/2016). Influence: Science and Practice
        (mechanism vocabulary mapping).
"""
import pytest

from adam.intelligence.cohort_discovery import (
    COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD,
    COMPENSATORY_MECHANISM_INDICATORS,
    COMPENSATORY_MIN_COHORT_SIZE_FOR_HIGH_CONFIDENCE,
    COMPENSATORY_TRANSACTIONAL_NEGATIVES,
    COMPENSATORY_TRANSACTIONAL_WEAKNESS_THRESHOLD,
    CohortDiscoveryService,
    UserCohort,
    detect_compensatory_consumption_pattern,
)


# ---------------------------------------------------------------------------
# Detection logic — two-criterion combinations
# ---------------------------------------------------------------------------

class TestDetectionLogic:

    def test_empty_dominant_mechanisms_returns_neutral(self):
        """Test 1: empty dominant_mechanisms → (False, 0.50)."""
        c = UserCohort(
            cohort_id="empty", size=100, sample_members=[],
            dominant_mechanisms=[],
        )
        assert detect_compensatory_consumption_pattern(c) == (False, 0.50)

    def test_pure_affiliative_low_transactional_large_cohort_yields_true_high_conf(
        self,
    ):
        """Test 2: both criteria + sufficient sample → (True, 0.85)."""
        c = UserCohort(
            cohort_id="c2", size=300, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={
                "anchoring": 0.20,
                "scarcity": 0.25,
                "loss_aversion": 0.30,
            },
        )
        assert detect_compensatory_consumption_pattern(c) == (True, 0.85)

    def test_pure_affiliative_low_transactional_small_cohort_caps_confidence(
        self,
    ):
        """Test 3: both criteria but undersample → (True, 0.65)."""
        c = UserCohort(
            cohort_id="c3", size=100, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={
                "anchoring": 0.20,
                "scarcity": 0.25,
                "loss_aversion": 0.30,
            },
        )
        assert detect_compensatory_consumption_pattern(c) == (True, 0.65)

    def test_affiliative_dominance_only_yields_partial_evidence(self):
        """Test 4: affiliative met, transactional not → (False, 0.65)."""
        c = UserCohort(
            cohort_id="c4", size=300, sample_members=["u1"],
            dominant_mechanisms=[
                "social_proof", "liking", "unity", "authority",
            ],  # 3 / 4 = 0.75 affiliative, ≥ 0.50 threshold
            mechanism_effectiveness={
                "anchoring": 0.55,
                "scarcity": 0.55,
                "loss_aversion": 0.55,
            },  # mean = 0.55, NOT < 0.40
        )
        assert detect_compensatory_consumption_pattern(c) == (False, 0.65)

    def test_transactional_weakness_only_yields_partial_evidence(self):
        """Test 5: transactional met, affiliative not → (False, 0.65)."""
        c = UserCohort(
            cohort_id="c5", size=300, sample_members=["u1"],
            dominant_mechanisms=[
                "authority", "reciprocity", "commitment",
                "curiosity", "social_proof",
            ],  # 1 / 5 = 0.20 affiliative, < 0.50 threshold
            mechanism_effectiveness={
                "anchoring": 0.20,
                "scarcity": 0.25,
                "loss_aversion": 0.30,
            },  # mean = 0.25, < 0.40
        )
        assert detect_compensatory_consumption_pattern(c) == (False, 0.65)

    def test_neither_criterion_yields_neutral(self):
        """Test 6: neither criterion met → (False, 0.50)."""
        c = UserCohort(
            cohort_id="c6", size=300, sample_members=["u1"],
            dominant_mechanisms=["authority", "reciprocity"],
            mechanism_effectiveness={
                "anchoring": 0.55,
                "scarcity": 0.55,
                "loss_aversion": 0.55,
            },
        )
        assert detect_compensatory_consumption_pattern(c) == (False, 0.50)


# ---------------------------------------------------------------------------
# Threshold boundary semantics
# ---------------------------------------------------------------------------

class TestBoundarySemantics:
    """Test 7: exactly at each threshold value — confirm boundary
    behavior (>=, <, >= per spec)."""

    def test_exactly_at_affiliative_threshold_passes(self):
        """affiliative_fraction == 0.50 should PASS criterion_1 (>=)."""
        c = UserCohort(
            cohort_id="b1", size=300, sample_members=["u1"],
            dominant_mechanisms=[
                "social_proof", "liking", "authority", "reciprocity",
            ],  # 2 / 4 = 0.50 exactly
            mechanism_effectiveness={
                "anchoring": 0.20, "scarcity": 0.25, "loss_aversion": 0.30,
            },
        )
        flag, conf = detect_compensatory_consumption_pattern(c)
        assert flag is True

    def test_exactly_at_transactional_threshold_fails(self):
        """mean transactional == 0.40 should FAIL criterion_2 (strict <)."""
        c = UserCohort(
            cohort_id="b2", size=300, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={
                "anchoring": 0.40, "scarcity": 0.40, "loss_aversion": 0.40,
            },  # mean = 0.40, NOT < 0.40 → criterion_2 FAILS
        )
        flag, _ = detect_compensatory_consumption_pattern(c)
        assert flag is False

    def test_exactly_at_size_threshold_grants_high_confidence(self):
        """cohort.size == 200 should PASS sufficient_sample (>=)."""
        c = UserCohort(
            cohort_id="b3", size=200, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={
                "anchoring": 0.20, "scarcity": 0.25, "loss_aversion": 0.30,
            },
        )
        assert detect_compensatory_consumption_pattern(c) == (True, 0.85)

    def test_one_below_size_threshold_caps_confidence(self):
        """cohort.size == 199 should FAIL sufficient_sample → (True, 0.65)."""
        c = UserCohort(
            cohort_id="b4", size=199, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={
                "anchoring": 0.20, "scarcity": 0.25, "loss_aversion": 0.30,
            },
        )
        assert detect_compensatory_consumption_pattern(c) == (True, 0.65)


# ---------------------------------------------------------------------------
# Cross-cutting: missing mechanism, determinism, caveat doc
# ---------------------------------------------------------------------------

class TestCrossCutting:

    def test_missing_mechanism_in_effectiveness_defaults_to_neutral(self):
        """Test 8: cohort.mechanism_effectiveness missing one of
        COMPENSATORY_TRANSACTIONAL_NEGATIVES → defaults to 0.5 for
        the missing entry. With 3 affiliative dominant_mechanisms,
        the mean of (0.10 + 0.5 + 0.5) / 3 = 0.367 < 0.40 → criterion
        passes; (True, 0.85)."""
        c = UserCohort(
            cohort_id="c8", size=300, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={"anchoring": 0.10},  # 2 missing
        )
        assert detect_compensatory_consumption_pattern(c) == (True, 0.85)

    def test_determinism_same_input_same_output(self):
        """Test 9: function is pure — same input twice → same output."""
        c = UserCohort(
            cohort_id="c9", size=300, sample_members=["u1"],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            mechanism_effectiveness={
                "anchoring": 0.20, "scarcity": 0.25, "loss_aversion": 0.30,
            },
        )
        r1 = detect_compensatory_consumption_pattern(c)
        r2 = detect_compensatory_consumption_pattern(c)
        assert r1 == r2 == (True, 0.85)

    def test_heuristic_substrate_caveat_pinned_in_docstring(self):
        """Test 20: docstring contains explicit heuristic-substrate
        caveat language — pins the intent so future readers cannot
        promote the detection logic to load-bearing without breaking
        this test."""
        doc = detect_compensatory_consumption_pattern.__doc__
        assert doc is not None
        assert "HEURISTIC SUBSTRATE" in doc, (
            "detect_compensatory_consumption_pattern docstring must "
            "contain explicit HEURISTIC SUBSTRATE caveat"
        )
        assert "not load-bearing" in doc.lower(), (
            "docstring must explicitly disclaim load-bearing status"
        )
        assert "Cialdini" in doc, (
            "docstring must reference the Cialdini-mechanism-vocabulary "
            "proxy framing"
        )


# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Test 17: constants are module-level and match spec defaults."""

    def test_compensatory_mechanism_indicators_pinned(self):
        assert COMPENSATORY_MECHANISM_INDICATORS == (
            "social_proof", "liking", "unity",
        )

    def test_compensatory_transactional_negatives_pinned(self):
        assert COMPENSATORY_TRANSACTIONAL_NEGATIVES == (
            "anchoring", "scarcity", "loss_aversion",
        )

    def test_thresholds_pinned(self):
        assert COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD == 0.50
        assert COMPENSATORY_TRANSACTIONAL_WEAKNESS_THRESHOLD == 0.40
        assert COMPENSATORY_MIN_COHORT_SIZE_FOR_HIGH_CONFIDENCE == 200


# ---------------------------------------------------------------------------
# Pipeline integration — _get_default_cohorts populates new fields
# ---------------------------------------------------------------------------

class TestPipelineIntegration:

    def test_default_cohort_fallback_populates_new_fields(self):
        """Test 10 (default-cohort variant): the no-Neo4j fallback path
        runs detection on each default cohort. Each resulting UserCohort
        carries populated compensatory_consumption_pattern +
        compensatory_detection_confidence (not the schema-default
        values from E)."""
        svc = CohortDiscoveryService(neo4j_driver=None)
        defaults = svc._get_default_cohorts()
        assert len(defaults) > 0
        for c in defaults:
            # The flag has a definite value (boolean True or False).
            assert isinstance(c.compensatory_consumption_pattern, bool)
            # Confidence is one of the three calibration values.
            assert c.compensatory_detection_confidence in (0.50, 0.65, 0.85)

    def test_default_cohort_detection_results_consistent_with_function(
        self,
    ):
        """Pin that the default-cohort pipeline calls
        detect_compensatory_consumption_pattern (not some sibling
        function or stub) — running the function directly on the
        same cohorts must yield identical results."""
        svc = CohortDiscoveryService(neo4j_driver=None)
        defaults = svc._get_default_cohorts()
        for c in defaults:
            expected_flag, expected_conf = (
                detect_compensatory_consumption_pattern(c)
            )
            assert c.compensatory_consumption_pattern == expected_flag
            assert c.compensatory_detection_confidence == expected_conf


# ---------------------------------------------------------------------------
# Persistence-payload extension
# ---------------------------------------------------------------------------

class TestPersistencePayload:
    """Test 11 (payload variant): the cohort_metadata payload built by
    persist_cohort_assignments includes the F.2 fields. Without a live
    Neo4j driver we can't round-trip through the database, but we can
    pin that the metadata-construction comprehension was extended."""

    def test_cohort_metadata_includes_f2_fields(self):
        # Re-build the payload comprehension exactly as
        # persist_cohort_assignments does.
        import json
        svc = CohortDiscoveryService(neo4j_driver=None)
        defaults = svc._get_default_cohorts()
        cohort_metadata = [
            {
                "cohort_id": c.cohort_id,
                "size": c.size,
                "mechanism_effectiveness_json": json.dumps(
                    c.mechanism_effectiveness or {},
                ),
                "compensatory_consumption_pattern":
                    c.compensatory_consumption_pattern,
                "compensatory_detection_confidence":
                    c.compensatory_detection_confidence,
            }
            for c in svc._cohorts.values()
        ]
        assert cohort_metadata, "default-cohort fallback should populate _cohorts"
        for entry in cohort_metadata:
            assert "compensatory_consumption_pattern" in entry
            assert "compensatory_detection_confidence" in entry
            assert isinstance(entry["compensatory_consumption_pattern"], bool)
            assert isinstance(entry["compensatory_detection_confidence"], float)

    def test_persist_cohort_assignments_cypher_writes_f2_fields(self):
        """Pin that the cypher SET clause includes both F.2 fields by
        inspecting the function source (we cannot exec the cypher
        without Neo4j)."""
        import inspect
        from adam.intelligence import cohort_discovery
        source = inspect.getsource(
            cohort_discovery.CohortDiscoveryService.persist_cohort_assignments,
        )
        assert "uc.compensatory_consumption_pattern = c.compensatory_consumption_pattern" in source, (
            "persist cypher SET must write compensatory_consumption_pattern"
        )
        assert "uc.compensatory_detection_confidence = c.compensatory_detection_confidence" in source, (
            "persist cypher SET must write compensatory_detection_confidence"
        )


# ---------------------------------------------------------------------------
# Zero-regression on F.1 cell taxonomy + existing get_cohort_priors
# ---------------------------------------------------------------------------

class TestZeroRegression:

    def test_f1_cell_taxonomy_unchanged(self):
        """Test 19: F.1 substrate intact — F.2 doesn't touch
        adam/cells/."""
        from adam.cells import (
            CELL_TAXONOMY, EXPECTED_CELL_COUNT, construct_cell_id,
        )
        from adam.cold_start.models.enums import ArchetypeID
        from adam.retargeting.models.enums import ConversionStage
        from adam.cells.taxonomy import RegulatoryFocus

        assert len(CELL_TAXONOMY) == EXPECTED_CELL_COUNT == 2880
        cid = construct_cell_id(
            ArchetypeID.ANALYST, "TASK_COMPLETION",
            ConversionStage.INTENDING, RegulatoryFocus.PROMOTION,
            valence=0.5, arousal=0.7,
        )
        assert cid == "ANALYST_TC_INT_PROM_Q1"

    def test_user_cohort_e_schema_slot_unchanged(self):
        """E surface intact: schema slot still has safe defaults at
        construct time (population happens via detection in the
        pipeline, not via dataclass-level magic)."""
        c = UserCohort(cohort_id="x", size=1, sample_members=[])
        assert c.compensatory_consumption_pattern is False
        assert c.compensatory_detection_confidence == 0.5
