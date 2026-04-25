"""Unit tests for the DCIL → recommendation projection in the dashboard service.

Discipline anchors:
    - The mapping carries directive's structural fields onto first-class
      RecommendationDetail fields without flattening (orientation A4
      counterpart: epistemic surface renders derived views, not composed
      strings).
    - Each rollback_condition becomes a structural PossiblyWrongClaim,
      one-to-one. No condition is silently dropped.
    - Generator-authored strings (rationale, bilateral_evidence) are
      preserved on dedicated fields with explicit attribution; they are
      not blended into Confident/Uncertain/Possibly-Wrong claims (which
      would launder upstream A4 drift into the rendering layer).
    - source="dcil" is set; id is prefixed "dcil:" so the decide handler
      can route to the admin directive endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from adam.api.dashboard.service import _dcil_directive_to_recommendation


# -----------------------------------------------------------------------------
# Fixture: a representative directive row as it would arrive from
# `dcil_directives` with JSON columns (current_value, proposed_value,
# rollback_conditions) deserialized — matching the row shape the loader
# normalizes via _maybe_parse.
# -----------------------------------------------------------------------------


@pytest.fixture
def budget_directive() -> dict:
    return {
        "id": "dir_uuid_abc",
        "campaign_id": "camp_xyz",
        "directive_type": "budget_reallocation",
        "status": "proposed",
        "parameter": "daily_budget",
        "current_value": 500,
        "proposed_value": 600,
        "rationale": (
            "High retention archetype showing increased capacity for spend."
        ),
        "bilateral_evidence": (
            "DerSimonian-Laird: effect=0.085, CI=(0.04, 0.13)"
        ),
        "i_squared": 23.0,
        "confidence": 0.78,
        "expected_lift_pct": 8.5,
        "rollback_conditions": [
            "if conversions drop >10% in 48h",
            "if CPA increases >15% over 7d",
        ],
        "scope": "campaign",
        "created_at": "2026-04-25T12:00:00+00:00",
        "updated_at": "2026-04-25T12:00:00+00:00",
    }


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 25, 12, 30, tzinfo=timezone.utc)


# -----------------------------------------------------------------------------
# Source attribution + ID routing
# -----------------------------------------------------------------------------


def test_source_is_dcil(budget_directive: dict, now: datetime) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.source == "dcil"


def test_id_is_prefixed_for_decide_routing(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.id == "dcil:dir_uuid_abc"
    assert rec.directive_id == "dir_uuid_abc"


# -----------------------------------------------------------------------------
# Structural fields preserved (no flattening)
# -----------------------------------------------------------------------------


def test_structural_fields_carried_through(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.parameter == "daily_budget"
    assert rec.current_value == 500
    assert rec.proposed_value == 600
    assert rec.i_squared == 23.0
    assert rec.expected_lift_pct == 8.5
    assert rec.generator_confidence == 0.78
    assert rec.rollback_conditions == [
        "if conversions drop >10% in 48h",
        "if CPA increases >15% over 7d",
    ]


def test_directive_type_maps_to_dashboard_type(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.type == "budget_shift"


def test_unknown_directive_type_falls_back_to_other(
    budget_directive: dict, now: datetime,
) -> None:
    budget_directive["directive_type"] = "novel_action_kind"
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.type == "other"


# -----------------------------------------------------------------------------
# Evidence panel — derived from structural fields
# -----------------------------------------------------------------------------


def test_confident_claims_are_structural_facts_not_interpretations(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    confident_claims = [c.claim for c in rec.evidence.confident]
    # Each claim is a label for a structural value — no interpretation.
    assert any("daily_budget: 500 → 600" in c for c in confident_claims)
    assert any("i² = 23%" in c for c in confident_claims)
    assert any("expected lift = +8.5%" in c for c in confident_claims)
    assert any("generator confidence = 0.78" in c for c in confident_claims)


def test_each_rollback_condition_becomes_a_possibly_wrong_claim(
    budget_directive: dict, now: datetime,
) -> None:
    """Drift guard: if a future change drops a rollback_condition silently,
    this test fires. Every condition must reach the operator."""
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert len(rec.evidence.possibly_wrong) == 2
    claims = [pw.claim for pw in rec.evidence.possibly_wrong]
    assert any("conversions drop >10% in 48h" in c for c in claims)
    assert any("CPA increases >15% over 7d" in c for c in claims)


def test_no_rollback_conditions_means_no_possibly_wrong_claims(
    budget_directive: dict, now: datetime,
) -> None:
    budget_directive["rollback_conditions"] = []
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.evidence.possibly_wrong == []


# -----------------------------------------------------------------------------
# Upstream A4 honesty — generator strings preserved with attribution,
# not laundered into derived claim slots
# -----------------------------------------------------------------------------


def test_generator_authored_strings_preserved_on_dedicated_fields(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.directive_rationale == budget_directive["rationale"]
    assert rec.directive_bilateral_evidence == budget_directive["bilateral_evidence"]


def test_uncertain_claim_explicitly_flags_upstream_a4_when_narrative_present(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    # The operator must know the rationale is an author-string, not a
    # derived view of atom state.
    assert any(
        "author-string" in u.claim or "Generator narrative" in u.claim
        for u in rec.evidence.uncertain
    )


def test_no_generator_narrative_means_no_a4_uncertain_claim(
    budget_directive: dict, now: datetime,
) -> None:
    budget_directive["rationale"] = None
    budget_directive["bilateral_evidence"] = None
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    a4_claims = [
        u for u in rec.evidence.uncertain
        if "author-string" in u.claim or "Generator narrative" in u.claim
    ]
    assert a4_claims == []


# -----------------------------------------------------------------------------
# Title and summary — derived from structural diff
# -----------------------------------------------------------------------------


def test_title_renders_structural_diff_not_rationale_text(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    # Title should reference the structural diff (parameter, values).
    assert "daily_budget" in rec.title
    assert "500" in rec.title
    assert "600" in rec.title
    # Title should NOT be the rationale string verbatim — that's A4
    # at the title slot.
    assert budget_directive["rationale"] not in rec.title


def test_alternatives_include_approve_block_modify(
    budget_directive: dict, now: datetime,
) -> None:
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    alt_ids = {a.id for a in rec.alternatives}
    assert alt_ids == {"approve", "block", "modify"}
    assert rec.preferred_choice == "approve"


# -----------------------------------------------------------------------------
# Defensive parsing — JSON-string columns from asyncpg vs. parsed dicts
# -----------------------------------------------------------------------------


def test_json_string_columns_are_parsed_defensively(now: datetime) -> None:
    """asyncpg returns JSON columns as strings; sqlite returns them parsed.
    The loader must handle both without losing data."""
    row = {
        "id": "dir_2",
        "campaign_id": "camp_xyz",
        "directive_type": "mechanism_rotation",
        "status": "proposed",
        "parameter": "primary_mechanism",
        "current_value": '"regulatory_focus"',  # JSON-encoded string
        "proposed_value": '"automatic_evaluation"',
        "rollback_conditions": '["if engagement falls"]',
        "rationale": None,
        "bilateral_evidence": None,
        "i_squared": None,
        "confidence": None,
        "expected_lift_pct": None,
        "created_at": "2026-04-25T12:00:00+00:00",
        "updated_at": "2026-04-25T12:00:00+00:00",
    }
    rec = _dcil_directive_to_recommendation(row, "Q2 LUXY", now)
    assert rec.current_value == "regulatory_focus"
    assert rec.proposed_value == "automatic_evaluation"
    assert rec.rollback_conditions == ["if engagement falls"]
