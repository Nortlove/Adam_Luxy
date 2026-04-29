# =============================================================================
# ADAM Dialogue Ledger Service Tests
# Location: tests/unit/test_dialogue_ledger_service.py
# =============================================================================

"""
Tests for the Dialogue Ledger v0.1 substrate (Loop B foundation).

Coverage:
  - HMT discipline rule 12 enforcement: Claims must be HYPOTHESIS at
    construction; the Pydantic validator + service-layer validator
    both reject other statuses
  - Pydantic validators (confidence range, mood range)
  - InMemoryDialogueLedgerBackend basic write/read round-trips
  - DialogueLedgerService composition: claim writes pair with
    LearningStatus(CAPTURED) automatically
  - User-history, status-filter, domain-filter retrieval
  - Singleton lifecycle
  - to_neo4j_props serialization
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.dialogue_ledger import (
    Claim,
    ClaimStatus,
    DialogueLedgerService,
    DialogueUser,
    ElicitationMode,
    HorizonClass,
    LearningStatus,
    LearningStatusState,
    get_dialogue_ledger_service,
)
from adam.intelligence.dialogue_ledger.models import (
    FrameLabel,
    RecallabilityLabel,
    make_claim,
)
from adam.intelligence.dialogue_ledger.service import (
    InMemoryDialogueLedgerBackend,
    reset_dialogue_ledger_service,
)


# ============================================================================
# HMT Rule 12 enforcement
# ============================================================================


class TestHMTRule12:
    """User self-reports are HYPOTHESES, not learnings — enforced at
    Claim construction."""

    def test_claim_constructor_rejects_non_hypothesis_status(self):
        with pytest.raises(ValueError, match="HYPOTHESIS"):
            Claim(
                user_id="user:test",
                text="I think X works",
                elicitation_mode=ElicitationMode.STORY,
                domain="test_domain",
                status=ClaimStatus.VALIDATED_USER_RIGHT,  # forbidden
            )

    def test_claim_default_status_is_hypothesis(self):
        c = Claim(
            user_id="user:test",
            text="I think X works",
            elicitation_mode=ElicitationMode.STORY,
            domain="test_domain",
        )
        assert c.status == ClaimStatus.HYPOTHESIS

    def test_make_claim_helper_enforces_hypothesis(self):
        c = make_claim(
            user_id="user:test",
            text="X works",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="test_domain",
        )
        assert c.status == ClaimStatus.HYPOTHESIS

    @pytest.mark.asyncio
    async def test_service_record_claim_rejects_non_hypothesis(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)
        c = Claim(
            user_id="user:test",
            text="X works",
            elicitation_mode=ElicitationMode.STORY,
            domain="test_domain",
        )
        # Bypass model validator via model_construct, then submit
        c.status = ClaimStatus.VALIDATED_USER_RIGHT  # forced
        with pytest.raises(ValueError, match="HYPOTHESIS"):
            await service.record_claim(c)


# ============================================================================
# Field validators
# ============================================================================


class TestValidators:
    def test_stated_confidence_range_enforced(self):
        with pytest.raises(ValueError, match="0, 1"):
            Claim(
                user_id="u",
                text="t",
                elicitation_mode=ElicitationMode.FORCED_PAIR,
                domain="d",
                stated_confidence=1.5,
            )
        with pytest.raises(ValueError, match="0, 1"):
            Claim(
                user_id="u",
                text="t",
                elicitation_mode=ElicitationMode.FORCED_PAIR,
                domain="d",
                stated_confidence=-0.1,
            )

    def test_mood_index_range_enforced(self):
        with pytest.raises(ValueError, match="0, 1"):
            Claim(
                user_id="u",
                text="t",
                elicitation_mode=ElicitationMode.FORCED_PAIR,
                domain="d",
                mood_index=2.0,
            )

    def test_optional_fields_can_be_none(self):
        c = Claim(
            user_id="u",
            text="t",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="d",
        )
        assert c.stated_confidence is None
        assert c.mood_index is None
        assert c.recallability is None


# ============================================================================
# Service write/read round-trip
# ============================================================================


class TestServiceWriteRead:

    @pytest.mark.asyncio
    async def test_record_claim_writes_to_backend(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        c = make_claim(
            user_id="user:chris",
            text="careful_truster prefers brand_trust_evidence",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="mechanism_selection",
            stated_confidence=0.7,
            latency_ms=1850,
        )
        result = await service.record_claim(c)
        assert result.id == c.id

        # Backend has the claim
        retrieved = await backend.get_claim(c.id)
        assert retrieved is not None
        assert retrieved.text == c.text
        assert retrieved.user_id == "user:chris"

    @pytest.mark.asyncio
    async def test_record_claim_creates_learning_status(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        c = make_claim(
            user_id="user:chris",
            text="x",
            elicitation_mode=ElicitationMode.STORY,
            domain="mechanism_selection",
        )
        await service.record_claim(c, capture_reason="from elicitation test")

        ls = backend.get_learning_status(c.id)
        assert ls is not None
        assert ls.current == LearningStatusState.CAPTURED
        assert ls.reason == "from elicitation test"

    @pytest.mark.asyncio
    async def test_record_claim_with_horizon(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        horizon_at = datetime.now(timezone.utc) + timedelta(days=14)
        c = make_claim(
            user_id="user:chris",
            text="x",
            elicitation_mode=ElicitationMode.STORY,
            domain="creative_voice",
        )
        await service.record_claim(c, horizon_ends_at=horizon_at)

        ls = backend.get_learning_status(c.id)
        assert ls.horizon_ends_at is not None
        # Allow microsecond drift in roundtrip
        assert abs((ls.horizon_ends_at - horizon_at).total_seconds()) < 1.0

    @pytest.mark.asyncio
    async def test_get_user_history(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        await service.ensure_user(DialogueUser(id="user:chris"))
        for i in range(5):
            await service.record_claim(make_claim(
                user_id="user:chris",
                text=f"claim {i}",
                elicitation_mode=ElicitationMode.FORCED_PAIR,
                domain="mechanism_selection",
            ))

        history = await service.get_user_history("user:chris", limit=10)
        assert len(history) == 5
        # Different users not mixed
        await service.record_claim(make_claim(
            user_id="user:other",
            text="other claim",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="mechanism_selection",
        ))
        history2 = await service.get_user_history("user:chris", limit=10)
        assert len(history2) == 5

    @pytest.mark.asyncio
    async def test_get_pending_claims_returns_only_hypothesis(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        for _ in range(3):
            await service.record_claim(make_claim(
                user_id="u",
                text="t",
                elicitation_mode=ElicitationMode.FORCED_PAIR,
                domain="mechanism_selection",
            ))

        pending = await service.get_pending_claims(limit=100)
        assert len(pending) == 3
        for c in pending:
            assert c.status == ClaimStatus.HYPOTHESIS

    @pytest.mark.asyncio
    async def test_get_domain_claims_filters(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        await service.record_claim(make_claim(
            user_id="u", text="a",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="mechanism_selection",
        ))
        await service.record_claim(make_claim(
            user_id="u", text="b",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="creative_voice",
        ))

        ms = await service.get_domain_claims("mechanism_selection")
        cv = await service.get_domain_claims("creative_voice")
        assert len(ms) == 1
        assert len(cv) == 1


# ============================================================================
# to_neo4j_props serialization
# ============================================================================


class TestSerialization:
    def test_claim_to_neo4j_props_basic(self):
        c = Claim(
            id="claim:abc123",
            user_id="user:chris",
            text="hello",
            elicitation_mode=ElicitationMode.TIMED_PAIR,
            domain="mechanism_selection",
            stated_confidence=0.8,
            latency_ms=2100,
            frame=FrameLabel.LOSS,
            session_id="session:xyz",
            mood_index=0.6,
            recallability=RecallabilityLabel.FLUENT,
        )
        props = c.to_neo4j_props()
        assert props["id"] == "claim:abc123"
        assert props["elicitation_mode"] == "timed_pair"
        assert props["frame"] == "loss"
        assert props["status"] == "hypothesis"
        assert props["stated_confidence"] == 0.8
        assert props["latency_ms"] == 2100
        assert props["recallability"] == "fluent"
        assert "created_at" in props

    def test_claim_to_neo4j_props_omits_none_optionals(self):
        c = Claim(
            user_id="u",
            text="t",
            elicitation_mode=ElicitationMode.FORCED_PAIR,
            domain="d",
        )
        props = c.to_neo4j_props()
        # Optional unset fields are NOT in the dict (not set to None)
        assert "stated_confidence" not in props
        assert "latency_ms" not in props
        assert "session_id" not in props
        assert "mood_index" not in props
        assert "recallability" not in props

    def test_learning_status_to_neo4j_props(self):
        ls = LearningStatus(
            claim_id="claim:test",
            current=LearningStatusState.INSTRUMENTED,
            reason="attached to outcome horizon",
            evidence_strength=0.42,
        )
        props = ls.to_neo4j_props()
        assert props["claim_id"] == "claim:test"
        assert props["current"] == "instrumented"
        assert props["evidence_strength"] == 0.42


# ============================================================================
# Singleton lifecycle
# ============================================================================


class TestSingleton:
    def test_singleton_returned_consistently(self):
        reset_dialogue_ledger_service()
        try:
            backend = InMemoryDialogueLedgerBackend()
            s1 = get_dialogue_ledger_service(backend=backend)
            s2 = get_dialogue_ledger_service()
            assert s1 is s2
        finally:
            reset_dialogue_ledger_service()

    def test_reset_clears_singleton(self):
        reset_dialogue_ledger_service()
        try:
            backend = InMemoryDialogueLedgerBackend()
            s1 = get_dialogue_ledger_service(backend=backend)
            reset_dialogue_ledger_service()
            backend2 = InMemoryDialogueLedgerBackend()
            s2 = get_dialogue_ledger_service(backend=backend2)
            assert s1 is not s2
        finally:
            reset_dialogue_ledger_service()


# ============================================================================
# DialogueUser
# ============================================================================


class TestDialogueUser:
    @pytest.mark.asyncio
    async def test_ensure_user_idempotent(self):
        backend = InMemoryDialogueLedgerBackend()
        service = DialogueLedgerService(backend)

        u = DialogueUser(id="user:chris", display_name="Chris N")
        await service.ensure_user(u)
        await service.ensure_user(u)  # second call should not duplicate

        all_users = backend.all_users()
        assert len(all_users) == 1
        assert all_users[0].id == "user:chris"

    def test_dialogue_user_defaults(self):
        u = DialogueUser(id="user:test")
        assert u.role == "planner"
        assert u.trust_mode_default == "explain"
