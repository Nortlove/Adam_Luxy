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


# -----------------------------------------------------------------------------
# Slice D1: horizon-adjudication projection
#
# The mapping from (Deviation, original Recommendation) → RecommendationDetail
# preserves bilateral structure (system_choice + user_choice) and produces
# alternatives whose predicted_outcome strings are cited against
# adam/intelligence/causal_adjudicator.py:585-638. Drift guard: if a future
# change weakens the citation (e.g., asserts WhyLibraryEntry on user_right),
# these tests fire.
# -----------------------------------------------------------------------------


@pytest.fixture
def ready_horizon_record() -> dict:
    """A Deviation with horizon expired + the snapshot Recommendation
    node it deviated from. Mirrors the shape returned by the Cypher
    query in _load_horizon_adjudications."""
    return {
        "deviation": {
            "id": "deviation:abc123",
            "user_id": "user:chris",
            "recommendation_id": "rec:luxy:budget_shift:20260418",
            "system_choice": "approve",
            "user_choice": "diagnose",
            "stated_rationale": (
                "Wanted to see the bilateral diagnostic before scaling spend."
            ),
            "rationale_class": "missing_context",
            "adjudication_status": "pending",
            "horizon_class": "days",
            "created_at": datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc),
        },
        "original_recommendation": {
            "id": "rec:luxy:budget_shift:20260418",
            "title": "Increase Q2 LUXY daily budget to $600",
            "summary": "DCIL proposed +20% daily for careful_truster archetype.",
            "type": "budget_shift",
            "campaign_id": "luxy_q2",
            "campaign_name": "Q2 LUXY",
        },
    }


def test_horizon_source_and_id(ready_horizon_record: dict) -> None:
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    assert rec.source == "horizon_adjudication"
    # ID prefixed for decide-handler routing in slice D2.
    assert rec.id == "horizon:deviation:abc123"


def test_horizon_alternatives_are_three_adjudication_outcomes(
    ready_horizon_record: dict,
) -> None:
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    alt_ids = {a.id for a in rec.alternatives}
    assert alt_ids == {"system_right", "user_right", "indeterminate"}


def test_horizon_predicted_outcomes_match_causal_adjudicator(
    ready_horizon_record: dict,
) -> None:
    """Drift guard: the predicted_outcome strings make structural claims
    about what the adjudicator does (causal_adjudicator.py:585-638). If
    those strings are softened or made fictional, this test must fire.

    Specifically: WhyLibraryEntry is created ONLY on system_right
    (line 635-638). Past me wrote a version that claimed user_right
    'may generate a WhyLibraryEntry'; this test ensures that mistake
    cannot return."""
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    alts = {a.id: a for a in rec.alternatives}

    sr = alts["system_right"].predicted_outcome or ""
    assert "WhyLibraryEntry" in sr
    assert "system_choice" in sr

    ur = alts["user_right"].predicted_outcome or ""
    # WhyLibraryEntry must NOT be claimed for user_right.
    assert "No WhyLibraryEntry" in ur
    assert "user_choice" in ur

    ind = alts["indeterminate"].predicted_outcome or ""
    assert "No WhyLibraryEntry" in ind
    assert "confounded" in ind


def test_horizon_evidence_carries_system_and_user_choices(
    ready_horizon_record: dict,
) -> None:
    """A12 (unidirectional rendering) counterpart: the bilateral split
    must be visible — both system_choice and user_choice present."""
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    confident_text = " ".join(c.claim for c in rec.evidence.confident)
    assert "approve" in confident_text  # system_choice
    assert "diagnose" in confident_text  # user_choice


def test_horizon_summary_is_structural_no_exhortation(
    ready_horizon_record: dict,
) -> None:
    """Vigilance check: the summary must not include exhortation
    ('Decide!', 'so theory updates', etc.). It is a structural state
    description — what is, not what to do."""
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    lower = rec.summary.lower()
    # No imperative voice or exhortation.
    assert "decide" not in lower
    assert "so theory" not in lower
    # Structural facts that must be present.
    assert "horizon" in lower
    assert "expired" in lower
    assert "elapsed" in lower


def test_horizon_carries_original_recommendation_campaign(
    ready_horizon_record: dict,
) -> None:
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    assert rec.campaign_id == "luxy_q2"
    assert rec.campaign_name == "Q2 LUXY"
    assert "Q2 LUXY daily budget" in rec.title  # original title preserved


# -----------------------------------------------------------------------------
# Slice D2: operator-verdict adjudication routes to causal_adjudicator
# -----------------------------------------------------------------------------


class _FakeSession:
    """Minimal async-context-manager session that records run() calls.

    Records every Cypher query + parameters so tests can assert which
    writes happened. Returns canned records for specific queries.
    """

    def __init__(self, deviation_record: dict | None) -> None:
        self.deviation_record = deviation_record
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    async def run(self, query: str, **params):
        self.calls.append((query, params))

        class _Result:
            def __init__(self, record):
                self._record = record

            async def single(self):
                return self._record

        # The deviation lookup query returns the seed record.
        if "MATCH (d:Deviation {id: $deviation_id})" in query and "OPTIONAL MATCH (d)-[:FROM]->(r:Recommendation)" in query and "RETURN d, r" in query:
            return _Result(self.deviation_record)
        # All other queries are write-only — no return value needed.
        return _Result(None)


class _FakeClient:
    def __init__(self, deviation_record: dict | None, connected: bool = True) -> None:
        self._deviation_record = deviation_record
        self.is_connected = connected
        self.last_session: _FakeSession | None = None

    async def session(self) -> _FakeSession:
        self.last_session = _FakeSession(self._deviation_record)
        return self.last_session


@pytest.fixture
def pending_deviation_record() -> dict:
    """Shape mirrors what the Cypher query MATCH (d:Deviation)..RETURN d,r
    returns: a record with d (Deviation node dict) and r (Recommendation
    node dict)."""
    return {
        "d": {
            "id": "deviation:abc123",
            "recommendation_id": "rec:original_xyz",
            "user_id": "user:chris",
            "system_choice": "approve",
            "user_choice": "diagnose",
            "stated_rationale": "wanted diagnostic",
            "rationale_class": "missing_context",
            "adjudication_status": "pending",
            "horizon_class": "days",
            "created_at": datetime(2026, 4, 18, tzinfo=timezone.utc),
        },
        "r": {
            "id": "rec:original_xyz",
            "type": "budget_shift",
            "title": "Increase Q2 LUXY budget",
            "campaign_id": "luxy_q2",
        },
    }


def _patch_neo4j(monkeypatch, deviation_record):
    """Helper: patch the neo4j client lookup the operator-verdict
    function makes."""
    fake_client = _FakeClient(deviation_record)
    import adam.infrastructure.neo4j.client as neo4j_client_module
    monkeypatch.setattr(
        neo4j_client_module, "get_neo4j_client", lambda: fake_client,
    )
    return fake_client


@pytest.mark.asyncio
async def test_operator_verdict_persists_status_outcome_and_why_library_on_system_right(
    monkeypatch: pytest.MonkeyPatch, pending_deviation_record: dict,
) -> None:
    """The operator-led adjudication must write the same artifacts as
    the auto-adjudicator on system_right: Deviation status update,
    Outcome node attributed_to=system_choice, AND a WhyLibraryEntry.
    Drift guard cited at causal_adjudicator.py:587-638."""
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    client = _patch_neo4j(monkeypatch, pending_deviation_record)

    result = await adjudicate_deviation_with_operator_verdict(
        deviation_id="deviation:abc123",
        verdict="system_right",
        user_id="user:chris",
        rationale="Realized CPA drift confirmed system was right.",
    )
    assert result is not None
    assert result.outcome == "system_right"
    assert result.why_library_entry_id is not None  # WhyLibraryEntry created

    # Confirm the writes happened in the right order with the right shape.
    queries = [q for q, _ in client.last_session.calls]
    # Step 1: deviation lookup
    assert any("MATCH (d:Deviation {id: $deviation_id})" in q for q in queries)
    # Step 2: status update
    assert any(
        "SET d.adjudication_status = 'adjudicated'" in q
        and "d.adjudication_outcome = $verdict" in q
        for q in queries
    )
    # Step 3: Outcome node creation with verdict_source='operator'
    assert any("CREATE (o:Outcome" in q and "verdict_source: 'operator'" in q for q in queries)
    # Step 4: WhyLibraryEntry created (system_right only)
    assert any("CREATE (wl:WhyLibraryEntry" in q for q in queries)


@pytest.mark.asyncio
async def test_operator_verdict_user_right_does_not_create_why_library(
    monkeypatch: pytest.MonkeyPatch, pending_deviation_record: dict,
) -> None:
    """Vigilance: WhyLibraryEntry is created ONLY on system_right
    (causal_adjudicator.py:635-638). user_right must NOT create one."""
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    client = _patch_neo4j(monkeypatch, pending_deviation_record)

    result = await adjudicate_deviation_with_operator_verdict(
        deviation_id="deviation:abc123",
        verdict="user_right",
        user_id="user:chris",
        rationale="Operator's diagnostic call exposed a creative issue.",
    )
    assert result is not None
    assert result.outcome == "user_right"
    assert result.why_library_entry_id is None

    queries = [q for q, _ in client.last_session.calls]
    # No WhyLibraryEntry creation query.
    assert not any("CREATE (wl:WhyLibraryEntry" in q for q in queries)
    # But Outcome node IS created with attributed_to='user_choice'.
    assert any("CREATE (o:Outcome" in q for q in queries)


@pytest.mark.asyncio
async def test_operator_verdict_indeterminate_attributed_to_confounded(
    monkeypatch: pytest.MonkeyPatch, pending_deviation_record: dict,
) -> None:
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    client = _patch_neo4j(monkeypatch, pending_deviation_record)
    result = await adjudicate_deviation_with_operator_verdict(
        deviation_id="deviation:abc123",
        verdict="indeterminate",
        user_id="user:chris",
        rationale=None,
    )
    assert result is not None
    assert result.outcome == "indeterminate"
    assert result.why_library_entry_id is None

    # attributed_to argument on the Outcome creation must be 'confounded'
    # (the causal_adjudicator convention for indeterminate). We check the
    # params dict on the Outcome-creation call.
    outcome_calls = [
        params for q, params in client.last_session.calls
        if "CREATE (o:Outcome" in q
    ]
    assert len(outcome_calls) == 1
    assert outcome_calls[0]["attributed_to"] == "confounded"


@pytest.mark.asyncio
async def test_operator_verdict_idempotent_on_already_adjudicated(
    monkeypatch: pytest.MonkeyPatch, pending_deviation_record: dict,
) -> None:
    """Operator double-clicks must be safe — the function must not
    double-write Outcomes or WhyLibraryEntries on a deviation that
    has already been adjudicated."""
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    pending_deviation_record["d"]["adjudication_status"] = "adjudicated"
    pending_deviation_record["d"]["adjudication_outcome"] = "system_right"
    client = _patch_neo4j(monkeypatch, pending_deviation_record)

    result = await adjudicate_deviation_with_operator_verdict(
        deviation_id="deviation:abc123",
        verdict="user_right",  # operator tries to flip the verdict
        user_id="user:chris",
        rationale=None,
    )
    assert result is not None
    # The prior verdict is preserved; we don't allow flipping silently.
    assert result.outcome == "system_right"
    assert "Already adjudicated" in result.rationale
    # No write queries beyond the lookup.
    queries = [q for q, _ in client.last_session.calls]
    assert not any("SET d.adjudication_status" in q for q in queries)
    assert not any("CREATE (o:Outcome" in q for q in queries)
    assert not any("CREATE (wl:WhyLibraryEntry" in q for q in queries)


@pytest.mark.asyncio
async def test_operator_verdict_returns_none_when_deviation_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    _patch_neo4j(monkeypatch, None)  # lookup returns no record

    result = await adjudicate_deviation_with_operator_verdict(
        deviation_id="deviation:nonexistent",
        verdict="system_right",
        user_id="user:chris",
        rationale=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_operator_verdict_invalid_kind_raises(
    monkeypatch: pytest.MonkeyPatch, pending_deviation_record: dict,
) -> None:
    """Invalid verdict raises rather than silently coercing — same
    discipline as route_dcil_directive_decision (slice A2)."""
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    _patch_neo4j(monkeypatch, pending_deviation_record)

    with pytest.raises(ValueError, match="Invalid verdict"):
        await adjudicate_deviation_with_operator_verdict(
            deviation_id="deviation:abc123",
            verdict="random_string",  # type: ignore[arg-type]
            user_id="user:chris",
            rationale=None,
        )


@pytest.mark.asyncio
async def test_operator_verdict_default_rationale_when_none(
    monkeypatch: pytest.MonkeyPatch, pending_deviation_record: dict,
) -> None:
    """When operator provides no rationale, the Outcome observation
    still carries a structured default — audit trail must be informative."""
    from adam.intelligence.causal_adjudicator import (
        adjudicate_deviation_with_operator_verdict,
    )

    client = _patch_neo4j(monkeypatch, pending_deviation_record)
    result = await adjudicate_deviation_with_operator_verdict(
        deviation_id="deviation:abc123",
        verdict="user_right",
        user_id="user:chris",
        rationale=None,
    )
    assert result is not None
    assert "Operator-led verdict" in result.rationale
    assert "user_right" in result.rationale


def test_horizon_populates_deviation_context_structurally(
    ready_horizon_record: dict,
) -> None:
    """D3 surface contract: deviation_context carries structural state
    (not derived from claim strings). The UI's DeviationContextPanel
    reads from this field directly. Regression guard against accidental
    flattening of the structural fields into the claims-only path."""
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    ctx = rec.deviation_context
    assert ctx is not None
    assert ctx.deviation_id == "deviation:abc123"
    assert ctx.system_choice == "approve"
    assert ctx.user_choice == "diagnose"
    assert ctx.horizon_class == "days"
    assert ctx.horizon_window_days == 7.0
    # 8 days elapsed (Apr 18 → Apr 26)
    assert 7.5 < ctx.days_elapsed < 8.5
    assert ctx.stated_rationale is not None
    assert ctx.rationale_class == "missing_context"


def test_horizon_deviation_context_optional_when_user_choice_missing(
    ready_horizon_record: dict,
) -> None:
    """Reject decisions create deviations with user_choice=None
    (decide handler line 1183: chosen=None for kind=reject). The
    deviation_context must surface this honestly — None, not empty
    string."""
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    ready_horizon_record["deviation"]["user_choice"] = None
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    assert rec.deviation_context is not None
    assert rec.deviation_context.user_choice is None


def test_dcil_recommendation_has_no_deviation_context(
    budget_directive: dict, now: datetime,
) -> None:
    """A DCIL recommendation must NOT carry deviation_context. The two
    source-specific structural panels (DirectiveSubstance / DeviationContext)
    are mutually exclusive by source; populating both would break the
    A12 unidirectional discipline."""
    from adam.api.dashboard.service import _dcil_directive_to_recommendation
    rec = _dcil_directive_to_recommendation(budget_directive, "Q2 LUXY", now)
    assert rec.deviation_context is None


def test_horizon_with_missing_original_recommendation_does_not_crash(
    ready_horizon_record: dict,
) -> None:
    """If the original Recommendation node is missing (e.g., deviation
    pre-dates the audit-trail snapshot), the surface degrades gracefully
    rather than dropping the deviation silently — that would hide a
    real adjudication-needed from the operator."""
    from adam.api.dashboard.service import _horizon_deviation_to_recommendation
    ready_horizon_record["original_recommendation"] = None
    rec = _horizon_deviation_to_recommendation(
        ready_horizon_record, datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
    )
    assert rec.source == "horizon_adjudication"
    # Title degrades to deviation-id reference, but the rec exists.
    assert "deviation" in rec.title.lower() or "abc123" in rec.id


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
