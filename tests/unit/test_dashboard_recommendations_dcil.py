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


# -----------------------------------------------------------------------------
# Slice A2: decide handler routes by source — directive lifecycle preserved
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dcil_decision_accept_routes_to_approved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accept on a DCIL recommendation must update dcil_directives.status
    to 'approved' so the DCIL pipeline picks it up for execution. Without
    this the loop never closes — UI says approved, directive stays
    'proposed' forever."""
    from unittest.mock import AsyncMock, MagicMock
    from adam.api.dashboard.service import route_dcil_directive_decision

    fake_db = MagicMock()
    fake_db.execute = AsyncMock(return_value="UPDATE 1")

    import adam.api.admin.db as admin_db
    monkeypatch.setattr(admin_db, "get_db", lambda: fake_db)

    new_status = await route_dcil_directive_decision(
        directive_id="dir_abc",
        decision_kind="accept",
        review_notes=None,
        user_id="user:chris",
    )

    assert new_status == "approved"
    fake_db.execute.assert_awaited_once()
    sql, *args = fake_db.execute.await_args.args
    assert "UPDATE dcil_directives" in sql
    assert "SET status = $1" in sql
    assert args[0] == "approved"  # new status
    assert args[1] == "user:chris"  # reviewed_by
    assert args[5] == "dir_abc"  # directive id


@pytest.mark.asyncio
async def test_dcil_decision_reject_routes_to_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock, MagicMock
    from adam.api.dashboard.service import route_dcil_directive_decision

    fake_db = MagicMock()
    fake_db.execute = AsyncMock(return_value="UPDATE 1")
    import adam.api.admin.db as admin_db
    monkeypatch.setattr(admin_db, "get_db", lambda: fake_db)

    new_status = await route_dcil_directive_decision(
        directive_id="dir_abc",
        decision_kind="reject",
        review_notes="Too aggressive given current campaign state.",
        user_id="user:chris",
    )
    assert new_status == "blocked"
    args = fake_db.execute.await_args.args
    assert args[1] == "blocked"  # status
    assert args[4] == "Too aggressive given current campaign state."  # review_notes


@pytest.mark.asyncio
async def test_dcil_decision_modify_blocks_directive_with_deviation_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modify on a DCIL recommendation blocks the directive (operator wants
    a different value than DCIL proposed). The Deviation node captured
    upstream by decide_recommendation handles the operator's chosen
    alternative as a hypothesis adjudicated at horizon. The directive
    itself MUST NOT execute — it represents a value the operator did
    not endorse."""
    from unittest.mock import AsyncMock, MagicMock
    from adam.api.dashboard.service import route_dcil_directive_decision

    fake_db = MagicMock()
    fake_db.execute = AsyncMock(return_value="UPDATE 1")
    import adam.api.admin.db as admin_db
    monkeypatch.setattr(admin_db, "get_db", lambda: fake_db)

    new_status = await route_dcil_directive_decision(
        directive_id="dir_abc",
        decision_kind="modify",
        review_notes="Prefer 550 daily not 600.",
        user_id="user:chris",
    )
    assert new_status == "blocked"  # NOT executed; deviation captures alternative


@pytest.mark.asyncio
async def test_dcil_decision_default_review_notes_when_none_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the operator provides no rationale, review_notes still get a
    structured default so the audit trail is informative."""
    from unittest.mock import AsyncMock, MagicMock
    from adam.api.dashboard.service import route_dcil_directive_decision

    fake_db = MagicMock()
    fake_db.execute = AsyncMock(return_value="UPDATE 1")
    import adam.api.admin.db as admin_db
    monkeypatch.setattr(admin_db, "get_db", lambda: fake_db)

    await route_dcil_directive_decision(
        directive_id="dir_abc",
        decision_kind="accept",
        review_notes=None,
        user_id="user:chris",
    )
    args = fake_db.execute.await_args.args
    notes = args[4]
    assert notes is not None and len(notes) > 0
    assert "approved" in notes.lower()


@pytest.mark.asyncio
async def test_dcil_decision_unknown_kind_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown decision_kind should fail loudly rather than silently
    coerce to a default lifecycle state."""
    from unittest.mock import AsyncMock, MagicMock
    from adam.api.dashboard.service import route_dcil_directive_decision

    fake_db = MagicMock()
    fake_db.execute = AsyncMock(return_value="UPDATE 1")
    import adam.api.admin.db as admin_db
    monkeypatch.setattr(admin_db, "get_db", lambda: fake_db)

    with pytest.raises(ValueError, match="Unknown decision_kind"):
        await route_dcil_directive_decision(
            directive_id="dir_abc",
            decision_kind="ignore",
            review_notes=None,
            user_id="user:chris",
        )
    fake_db.execute.assert_not_awaited()


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
