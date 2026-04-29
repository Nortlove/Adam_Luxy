# =============================================================================
# ADAM C4 (REDUCED) — HumanDeviation Log-and-Tag Tests
# Location: tests/unit/test_deviation_lifecycle.py
# =============================================================================

"""Tests for HumanDeviation log-and-tag substrate.

Per `docs/CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md` Section 8.1, the
verdict / adjudication machinery this module previously contained
has been CUT. What remains: log-and-tag.

Pins:
    1. HumanDeviation enforces RECORDED at construction (HMT rule 12)
    2. reason_tag is required (A12 defense — categorical not free-form)
    3. record_deviation_a14_flag emits DEVIATION_LOGGED for any deviation
"""

from __future__ import annotations

import pytest

from adam.intelligence.deviation_lifecycle import (
    DEVIATION_LOGGED_FLAG,
    record_deviation_a14_flag,
)
from adam.intelligence.dialogue_ledger.models import (
    DeviationLifecycleState,
    HumanDeviation,
    make_deviation,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _make_test_deviation() -> HumanDeviation:
    return make_deviation(
        user_id="user:test",
        decision_id="decision:test_1",
        domain="ad_conversion",
        system_recommendation={"mechanism": "authority", "tone": "warm"},
        user_substitute={"mechanism": "scarcity", "tone": "urgent"},
        reason_tag="archetype_mismatch",
        reason_text="The system suggested authority but I think this user "
                    "responds better to scarcity for this product category.",
        expected_outcome_tag="higher_conversion",
    )


# -----------------------------------------------------------------------------
# Construction-time invariants
# -----------------------------------------------------------------------------


class TestHumanDeviationConstruction:

    def test_construction_succeeds_with_recorded_state(self):
        d = _make_test_deviation()
        assert d.lifecycle_state == DeviationLifecycleState.RECORDED
        assert d.user_id == "user:test"
        assert d.reason_tag == "archetype_mismatch"

    def test_id_auto_generated_with_deviation_prefix(self):
        d = _make_test_deviation()
        assert d.id.startswith("deviation:")
        assert len(d.id) > len("deviation:")

    def test_empty_reason_tag_rejected(self):
        # A12 defense: free-form reason_text alone insufficient.
        with pytest.raises(ValueError, match="reason_tag"):
            make_deviation(
                user_id="u",
                decision_id="d",
                domain="ad_conversion",
                system_recommendation={},
                user_substitute={},
                reason_tag="",
            )

    def test_to_neo4j_props_serializes_dicts_as_json(self):
        d = _make_test_deviation()
        props = d.to_neo4j_props()
        # Dict fields persist as JSON strings (Neo4j scalar discipline).
        assert "system_recommendation_json" in props
        assert "user_substitute_json" in props
        assert isinstance(props["system_recommendation_json"], str)
        # Round-trippable.
        import json
        round_tripped = json.loads(props["system_recommendation_json"])
        assert round_tripped["mechanism"] == "authority"


# -----------------------------------------------------------------------------
# A14 flag emission
# -----------------------------------------------------------------------------


class TestA14FlagEmission:

    def test_recorded_deviation_emits_logged_flag(self):
        d = _make_test_deviation()
        flags = record_deviation_a14_flag(d)
        assert DEVIATION_LOGGED_FLAG in flags

    def test_flag_identifier_stable(self):
        assert DEVIATION_LOGGED_FLAG == "DEVIATION_LOGGED"
