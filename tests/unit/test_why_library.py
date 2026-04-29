"""Tests for the Why Library — structured store of recommendation reasons.

Pins:
    1. WhyEntry construction enforces non-empty primary_reason_tags
    2. primary_reason_tags must be in PRIMARY_REASON_TAGS vocabulary
    3. AlternativeConsidered.why_not_tag must be in WHY_NOT_REJECTION_TAGS
    4. AlternativeConsidered.alternative_kind restricted to
       {mechanism, archetype, variant}
    5. Append-only: re-recording same recommendation_id raises
    6. query_why_for_recommendation returns recorded entry
    7. query_why_for_archetype_mechanism returns most-recent N entries
    8. to_neo4j_props serializes lists as JSON strings
    9. A14 flag identifier + retirement trigger documented
"""

from __future__ import annotations

import json

import pytest

from adam.intelligence.why_library import (
    AlternativeConsidered,
    DuplicateRecommendationError,
    PRIMARY_REASON_TAGS,
    WHY_LIBRARY_INTERIM_TAG_VOCABULARY_FLAG,
    WHY_LIBRARY_RETIREMENT_TRIGGER,
    WHY_NOT_REJECTION_TAGS,
    WhyEntry,
    make_why_entry,
    query_why_for_archetype_mechanism,
    query_why_for_recommendation,
    record_why,
    reset_default_store,
)


@pytest.fixture(autouse=True)
def _reset_store():
    """Each test starts with a clean default store."""
    reset_default_store()
    yield
    reset_default_store()


# -----------------------------------------------------------------------------
# WhyEntry construction
# -----------------------------------------------------------------------------


class TestWhyEntryConstruction:

    def test_valid_entry_with_minimum_fields(self):
        e = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        assert e.recommendation_id == "rec_1"
        assert e.primary_reason_tags == ["archetype_match_strong"]
        assert e.alternatives_considered == []
        assert e.evidence_chain_refs == []

    def test_empty_primary_reason_tags_rejected(self):
        with pytest.raises(ValueError, match="primary_reason_tags"):
            make_why_entry(
                recommendation_id="rec_1",
                archetype="careful_truster",
                mechanism="authority",
                primary_reason_tags=[],
            )

    def test_invalid_reason_tag_rejected(self):
        with pytest.raises(ValueError, match="not in PRIMARY_REASON_TAGS"):
            make_why_entry(
                recommendation_id="rec_1",
                archetype="careful_truster",
                mechanism="authority",
                primary_reason_tags=["arbitrary_made_up_tag"],
            )

    def test_multiple_valid_tags_accepted(self):
        e = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=[
                "archetype_match_strong",
                "construct_chain_high_confidence",
                "edge_dimension_load_bearing",
            ],
        )
        assert len(e.primary_reason_tags) == 3

    def test_summary_annotation_is_optional(self):
        e = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
            summary_annotation="Becca: agreed with this on 2026-04-29",
        )
        assert "Becca" in e.summary_annotation


# -----------------------------------------------------------------------------
# AlternativeConsidered construction
# -----------------------------------------------------------------------------


class TestAlternativeConsidered:

    def test_valid_alternative(self):
        alt = AlternativeConsidered(
            alternative_kind="mechanism",
            alternative_value="scarcity",
            score_at_consideration=0.72,
            why_not_tag="score_margin_below_threshold",
        )
        assert alt.alternative_kind == "mechanism"
        assert alt.score_at_consideration == 0.72

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValueError, match="alternative_kind"):
            AlternativeConsidered(
                alternative_kind="something_else",
                alternative_value="x",
                score_at_consideration=0.5,
                why_not_tag="score_margin_below_threshold",
            )

    def test_invalid_why_not_tag_rejected(self):
        with pytest.raises(ValueError, match="WHY_NOT_REJECTION_TAGS"):
            AlternativeConsidered(
                alternative_kind="mechanism",
                alternative_value="scarcity",
                score_at_consideration=0.5,
                why_not_tag="arbitrary_reason",
            )

    def test_empty_why_not_tag_rejected(self):
        with pytest.raises(ValueError, match="why_not_tag"):
            AlternativeConsidered(
                alternative_kind="mechanism",
                alternative_value="scarcity",
                score_at_consideration=0.5,
                why_not_tag="",
            )

    def test_annotation_is_optional(self):
        alt = AlternativeConsidered(
            alternative_kind="mechanism",
            alternative_value="scarcity",
            score_at_consideration=0.5,
            why_not_tag="uncertainty_too_wide",
            why_not_annotation="LUXY's experience suggests scarcity backfires here.",
        )
        assert "LUXY" in alt.why_not_annotation

    def test_each_kind_value_accepted(self):
        for kind in ("mechanism", "archetype", "variant"):
            alt = AlternativeConsidered(
                alternative_kind=kind,
                alternative_value="x",
                score_at_consideration=0.5,
                why_not_tag="score_margin_below_threshold",
            )
            assert alt.alternative_kind == kind


# -----------------------------------------------------------------------------
# Vocabulary completeness
# -----------------------------------------------------------------------------


class TestVocabulary:

    def test_primary_reason_tags_includes_expected(self):
        # Pin the high-leverage reason tags so refactors that drop them
        # surface immediately.
        for tag in (
            "archetype_match_strong",
            "mechanism_uncertainty_low",
            "page_attentional_posture_aligned",
            "construct_chain_high_confidence",
            "mechanism_taxonomy_blend_compatible",
            "primary_metaphor_resonance",
        ):
            assert tag in PRIMARY_REASON_TAGS

    def test_why_not_rejection_tags_includes_expected(self):
        for tag in (
            "score_margin_below_threshold",
            "uncertainty_too_wide",
            "vigilance_activating_for_archetype",
            "calibration_pending",
            "horizon_discordance_alert",
        ):
            assert tag in WHY_NOT_REJECTION_TAGS


# -----------------------------------------------------------------------------
# Append-only contract
# -----------------------------------------------------------------------------


class TestAppendOnlyContract:

    def test_record_why_persists_entry(self):
        e = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        record_why(e)
        retrieved = query_why_for_recommendation("rec_1")
        assert retrieved is not None
        assert retrieved.id == e.id

    def test_duplicate_recommendation_id_rejected(self):
        e1 = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        e2 = make_why_entry(
            recommendation_id="rec_1",  # SAME id
            archetype="careful_truster",
            mechanism="scarcity",
            primary_reason_tags=["mechanism_uncertainty_low"],
        )
        record_why(e1)
        with pytest.raises(DuplicateRecommendationError):
            record_why(e2)

    def test_query_unknown_returns_none(self):
        assert query_why_for_recommendation("never_recorded") is None


# -----------------------------------------------------------------------------
# Cohort query — by archetype × mechanism
# -----------------------------------------------------------------------------


class TestCohortQuery:

    def test_query_by_archetype_mechanism_returns_recent_first(self):
        # Record three entries for the same archetype × mechanism.
        for i in range(3):
            record_why(make_why_entry(
                recommendation_id=f"rec_{i}",
                archetype="careful_truster",
                mechanism="authority",
                primary_reason_tags=["archetype_match_strong"],
            ))
        results = query_why_for_archetype_mechanism(
            archetype="careful_truster", mechanism="authority",
        )
        assert len(results) == 3
        # Most recent first.
        assert results[0].recommendation_id == "rec_2"
        assert results[2].recommendation_id == "rec_0"

    def test_query_respects_limit(self):
        for i in range(10):
            record_why(make_why_entry(
                recommendation_id=f"rec_{i}",
                archetype="careful_truster",
                mechanism="authority",
                primary_reason_tags=["archetype_match_strong"],
            ))
        results = query_why_for_archetype_mechanism(
            archetype="careful_truster", mechanism="authority",
            limit=3,
        )
        assert len(results) == 3

    def test_query_isolated_per_archetype_mechanism(self):
        record_why(make_why_entry(
            recommendation_id="rec_a",
            archetype="careful_truster", mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        ))
        record_why(make_why_entry(
            recommendation_id="rec_b",
            archetype="careful_truster", mechanism="scarcity",
            primary_reason_tags=["mechanism_uncertainty_low"],
        ))
        # authority cohort: only rec_a
        a = query_why_for_archetype_mechanism("careful_truster", "authority")
        assert len(a) == 1
        assert a[0].recommendation_id == "rec_a"
        # scarcity cohort: only rec_b
        b = query_why_for_archetype_mechanism("careful_truster", "scarcity")
        assert len(b) == 1
        assert b[0].recommendation_id == "rec_b"

    def test_unknown_cohort_returns_empty_list(self):
        results = query_why_for_archetype_mechanism(
            archetype="never_recorded", mechanism="never_either",
        )
        assert results == []


# -----------------------------------------------------------------------------
# Neo4j serialization
# -----------------------------------------------------------------------------


class TestNeo4jSerialization:

    def test_to_neo4j_props_serializes_lists_as_json(self):
        alt = AlternativeConsidered(
            alternative_kind="mechanism",
            alternative_value="scarcity",
            score_at_consideration=0.72,
            why_not_tag="score_margin_below_threshold",
        )
        e = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=[
                "archetype_match_strong",
                "construct_chain_high_confidence",
            ],
            evidence_chain_refs=["chain:abc", "chain:def"],
            alternatives_considered=[alt],
        )
        props = e.to_neo4j_props()
        # All list fields persist as JSON strings.
        assert isinstance(props["primary_reason_tags_json"], str)
        assert isinstance(props["evidence_chain_refs_json"], str)
        assert isinstance(props["alternatives_considered_json"], str)
        # Round-trippable.
        tags = json.loads(props["primary_reason_tags_json"])
        assert "archetype_match_strong" in tags
        assert "construct_chain_high_confidence" in tags
        refs = json.loads(props["evidence_chain_refs_json"])
        assert "chain:abc" in refs
        alts = json.loads(props["alternatives_considered_json"])
        assert alts[0]["alternative_value"] == "scarcity"


# -----------------------------------------------------------------------------
# A14 flag identifier + retirement trigger documented
# -----------------------------------------------------------------------------


class TestA14Flag:

    def test_flag_name_stable(self):
        assert WHY_LIBRARY_INTERIM_TAG_VOCABULARY_FLAG == (
            "WHY_LIBRARY_INTERIM_TAG_VOCABULARY"
        )

    def test_retirement_trigger_documented(self):
        # Three concrete pinned conditions surface in the trigger text.
        assert "≥30 rendered recommendations" in WHY_LIBRARY_RETIREMENT_TRIGGER
        assert "M2 CATE comparisons" in WHY_LIBRARY_RETIREMENT_TRIGGER
        assert "causal-difference scores" in WHY_LIBRARY_RETIREMENT_TRIGGER
