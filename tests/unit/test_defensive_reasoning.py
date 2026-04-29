"""Tests for Defensive Reasoning at recommendation time renderer.

Pins:
    1. Returns None when no Why entry is recorded (A11 defense — no
       silent fabrication of rationale)
    2. Each reason tag renders via the templated formatter (templated
       structured slots, no LLM prose)
    3. Each alternative renders via the templated why-not formatter
    4. Aggregate A14 flags surface in discipline_flags
    5. The interim-renderer A14 flag is ALWAYS present on every view
       (discipline always visible)
    6. Pure-function determinism: identical inputs → identical output
    7. JSON serialization preserves all structured fields
    8. A14 flag identifier + retirement trigger documented
"""

from __future__ import annotations

import pytest

from adam.intelligence.defensive_reasoning import (
    AlternativeLine,
    DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG,
    DEFENSIVE_REASONING_RETIREMENT_TRIGGER,
    DefensiveReasoningView,
    ReasonLine,
    build_defensive_reasoning_view,
    render_view_to_dict,
)
from adam.intelligence.why_library import (
    AlternativeConsidered,
    make_why_entry,
    record_why,
    reset_default_store,
)


@pytest.fixture(autouse=True)
def _reset_store():
    reset_default_store()
    yield
    reset_default_store()


# -----------------------------------------------------------------------------
# Missing-entry path — A11 defense
# -----------------------------------------------------------------------------


class TestMissingEntry:

    def test_no_entry_returns_none(self):
        view = build_defensive_reasoning_view("never_recorded")
        assert view is None


# -----------------------------------------------------------------------------
# Basic rendering
# -----------------------------------------------------------------------------


class TestBasicRendering:

    def test_single_reason_renders(self):
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        assert view is not None
        assert view.recommendation_id == "rec_1"
        assert view.archetype == "careful_truster"
        assert view.mechanism == "authority"
        assert len(view.primary_reasons) == 1
        # Template substitutes archetype.
        line = view.primary_reasons[0]
        assert line.tag == "archetype_match_strong"
        assert "careful_truster" in line.template_filled

    def test_multiple_reasons_render(self):
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=[
                "archetype_match_strong",
                "mechanism_uncertainty_low",
                "mechanism_taxonomy_blend_compatible",
            ],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        assert len(view.primary_reasons) == 3
        # mechanism_uncertainty_low template substitutes mechanism.
        unc_line = next(
            r for r in view.primary_reasons
            if r.tag == "mechanism_uncertainty_low"
        )
        assert "authority" in unc_line.template_filled

    def test_summary_renders_top_line(self):
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        # Summary is templated — contains both archetype and mechanism.
        assert "careful_truster" in view.rendered_summary
        assert "authority" in view.rendered_summary
        assert "1 primary reason" in view.rendered_summary


# -----------------------------------------------------------------------------
# Alternatives rendering
# -----------------------------------------------------------------------------


class TestAlternativesRendering:

    def test_alternative_renders_with_score(self):
        alt = AlternativeConsidered(
            alternative_kind="mechanism",
            alternative_value="scarcity",
            score_at_consideration=0.72,
            why_not_tag="score_margin_below_threshold",
        )
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
            alternatives_considered=[alt],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        assert len(view.alternatives_considered) == 1
        a = view.alternatives_considered[0]
        assert a.alternative_value == "scarcity"
        # Template substitutes the value AND the score (formatted to 2 dp).
        assert "scarcity" in a.why_not_filled
        assert "0.72" in a.why_not_filled

    def test_summary_includes_alternative_count(self):
        alt = AlternativeConsidered(
            alternative_kind="mechanism",
            alternative_value="scarcity",
            score_at_consideration=0.72,
            why_not_tag="score_margin_below_threshold",
        )
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
            alternatives_considered=[alt],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        assert "1 alternative" in view.rendered_summary

    def test_annotation_passes_through(self):
        alt = AlternativeConsidered(
            alternative_kind="mechanism",
            alternative_value="scarcity",
            score_at_consideration=0.72,
            why_not_tag="score_margin_below_threshold",
            why_not_annotation="Becca: scarcity backfired in March test.",
        )
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
            alternatives_considered=[alt],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        a = view.alternatives_considered[0]
        # Human-authored annotation passes through unchanged.
        assert "Becca" in a.why_not_annotation
        assert "March test" in a.why_not_annotation

    def test_each_why_not_tag_template_renders(self):
        from adam.intelligence.why_library import WHY_NOT_REJECTION_TAGS
        # Smoke test that every tag has a renderable template.
        for tag in WHY_NOT_REJECTION_TAGS:
            alt = AlternativeConsidered(
                alternative_kind="mechanism",
                alternative_value="scarcity",
                score_at_consideration=0.5,
                why_not_tag=tag,
            )
            entry = make_why_entry(
                recommendation_id=f"rec_{tag}",
                archetype="careful_truster",
                mechanism="authority",
                primary_reason_tags=["archetype_match_strong"],
                alternatives_considered=[alt],
            )
            record_why(entry)
            view = build_defensive_reasoning_view(f"rec_{tag}")
            a = view.alternatives_considered[0]
            # Either the template substituted the value, OR the
            # fallback "no template" message — never empty.
            assert a.why_not_filled
            assert "scarcity" in a.why_not_filled or "no rendering template" in a.why_not_filled


# -----------------------------------------------------------------------------
# Reason-tag template completeness
# -----------------------------------------------------------------------------


class TestReasonTemplateCompleteness:

    def test_each_primary_reason_tag_has_template(self):
        from adam.intelligence.why_library import PRIMARY_REASON_TAGS
        for tag in PRIMARY_REASON_TAGS:
            entry = make_why_entry(
                recommendation_id=f"rec_{tag}",
                archetype="careful_truster",
                mechanism="authority",
                primary_reason_tags=[tag],
            )
            record_why(entry)
            view = build_defensive_reasoning_view(f"rec_{tag}")
            line = view.primary_reasons[0]
            # Template substituted (does NOT contain the fallback).
            assert "no rendering template" not in line.template_filled, (
                f"Reason tag '{tag}' has no rendering template — add one"
            )


# -----------------------------------------------------------------------------
# Discipline flags
# -----------------------------------------------------------------------------


class TestDisciplineFlags:

    def test_interim_renderer_flag_always_present(self):
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")

        assert DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG in view.discipline_flags

    def test_aggregate_a14_flags_surfaced(self):
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        record_why(entry)
        view = build_defensive_reasoning_view(
            "rec_1",
            aggregate_a14_flags=["TEST_FLAG_X", "TEST_FLAG_Y"],
        )

        assert "TEST_FLAG_X" in view.discipline_flags
        assert "TEST_FLAG_Y" in view.discipline_flags
        # Plus the renderer's own flag.
        assert DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG in view.discipline_flags


# -----------------------------------------------------------------------------
# Pure-function determinism
# -----------------------------------------------------------------------------


class TestDeterminism:

    def test_identical_inputs_produce_identical_output(self):
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
            alternatives_considered=[
                AlternativeConsidered(
                    alternative_kind="mechanism",
                    alternative_value="scarcity",
                    score_at_consideration=0.72,
                    why_not_tag="score_margin_below_threshold",
                ),
            ],
        )
        v1 = build_defensive_reasoning_view(
            "rec_1", why_entry_override=entry,
            aggregate_a14_flags=["FLAG_A"],
        )
        v2 = build_defensive_reasoning_view(
            "rec_1", why_entry_override=entry,
            aggregate_a14_flags=["FLAG_A"],
        )
        # Compare the rendered_summary, primary_reasons, alternatives,
        # discipline_flags — everything except possibly created_at
        # (which the view doesn't carry).
        assert v1.rendered_summary == v2.rendered_summary
        assert [r.template_filled for r in v1.primary_reasons] == (
            [r.template_filled for r in v2.primary_reasons]
        )
        assert [a.why_not_filled for a in v1.alternatives_considered] == (
            [a.why_not_filled for a in v2.alternatives_considered]
        )
        assert v1.discipline_flags == v2.discipline_flags


# -----------------------------------------------------------------------------
# JSON serialization
# -----------------------------------------------------------------------------


class TestJSONSerialization:

    def test_render_view_to_dict_round_trips(self):
        import json
        entry = make_why_entry(
            recommendation_id="rec_1",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
            evidence_chain_refs=["chain:abc"],
            alternatives_considered=[
                AlternativeConsidered(
                    alternative_kind="mechanism",
                    alternative_value="scarcity",
                    score_at_consideration=0.72,
                    why_not_tag="score_margin_below_threshold",
                ),
            ],
        )
        record_why(entry)
        view = build_defensive_reasoning_view("rec_1")
        d = render_view_to_dict(view)

        # JSON-serializable.
        s = json.dumps(d)
        d2 = json.loads(s)

        assert d2["recommendation_id"] == "rec_1"
        assert d2["archetype"] == "careful_truster"
        assert len(d2["primary_reasons"]) == 1
        assert d2["primary_reasons"][0]["tag"] == "archetype_match_strong"
        assert len(d2["alternatives_considered"]) == 1
        assert d2["alternatives_considered"][0]["alternative_value"] == "scarcity"
        assert "chain:abc" in d2["evidence_chain_refs"]


# -----------------------------------------------------------------------------
# Override path (used by tests + the orchestrator integration)
# -----------------------------------------------------------------------------


class TestOverridePath:

    def test_why_entry_override_bypasses_store_lookup(self):
        # Don't record in the store — pass the entry directly.
        entry = make_why_entry(
            recommendation_id="rec_inline",
            archetype="careful_truster",
            mechanism="authority",
            primary_reason_tags=["archetype_match_strong"],
        )
        view = build_defensive_reasoning_view(
            "rec_inline", why_entry_override=entry,
        )
        assert view is not None
        assert view.recommendation_id == "rec_inline"


# -----------------------------------------------------------------------------
# A14 flag documented
# -----------------------------------------------------------------------------


class TestA14FlagDocumented:

    def test_flag_name_stable(self):
        assert DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG == (
            "DEFENSIVE_REASONING_INTERIM_RENDERER"
        )

    def test_retirement_trigger_documented(self):
        assert "≥30 rendered" in DEFENSIVE_REASONING_RETIREMENT_TRIGGER
        assert "M2-derived causal-margin numbers" in (
            DEFENSIVE_REASONING_RETIREMENT_TRIGGER
        )
