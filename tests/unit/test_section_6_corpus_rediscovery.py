"""Pin Slice 33 — Section 6.2 monthly corpus mechanism re-discovery."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.section_6 import (
    CorpusRediscoveryResult,
    MechanismProposal,
    PrimaryMetaphorProposal,
    rediscover_from_corpus,
)
from adam.intelligence.section_6.corpus_rediscovery import (
    DEFAULT_FDR_ALPHA,
    _bh_survival_flags,
)


# -----------------------------------------------------------------------------
# Default constants + types
# -----------------------------------------------------------------------------


def test_default_fdr_alpha_matches_directive():
    """Per directive line 768: FDR < 0.1."""
    assert DEFAULT_FDR_ALPHA == 0.10


def test_dataclasses_frozen():
    p = MechanismProposal(name="x")
    with pytest.raises((AttributeError, Exception)):
        p.name = "y"  # type: ignore[misc]
    m = PrimaryMetaphorProposal(axis_name="x")
    with pytest.raises((AttributeError, Exception)):
        m.axis_name = "y"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# BH-FDR survival
# -----------------------------------------------------------------------------


def test_bh_empty_returns_empty():
    assert _bh_survival_flags([], 0.10) == []


def test_bh_all_above_threshold_none_survive():
    """All p_values > alpha → none survive."""
    flags = _bh_survival_flags([0.5, 0.6, 0.7], alpha=0.10)
    assert flags == [False, False, False]


def test_bh_strong_signal_survives():
    """Single very small p_value far below alpha → survives."""
    flags = _bh_survival_flags([0.001], alpha=0.10)
    assert flags == [True]


def test_bh_step_up_classic_example():
    """BH classic: with 5 p-values [0.005, 0.04, 0.06, 0.08, 0.30]
    and alpha=0.10, the BH-step-up finds k=4 (largest k where
    p_(k) ≤ k/n × α = 4/5 × 0.10 = 0.08), so the first 4 survive.
    """
    flags = _bh_survival_flags(
        [0.005, 0.04, 0.06, 0.08, 0.30], alpha=0.10,
    )
    assert sum(flags) == 4
    assert flags[-1] is False  # p=0.30 fails


# -----------------------------------------------------------------------------
# Pipeline soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_claude_client_returns_empty_inventory():
    out = await rediscover_from_corpus(
        corpus=["LUXY corporate travel — premium black-car"],
        claude_client=None,
    )
    assert isinstance(out, CorpusRediscoveryResult)
    assert out.proposed_mechanisms == []
    assert out.proposed_metaphors == []
    assert "no_claude_client" in out.errors


@pytest.mark.asyncio
async def test_empty_corpus_returns_empty_inventory():
    fake_client = MagicMock()
    fake_client.complete = AsyncMock()
    out = await rediscover_from_corpus(
        corpus=[], claude_client=fake_client,
    )
    assert out.corpus_n_documents == 0
    assert "empty_corpus" in out.errors
    fake_client.complete.assert_not_called()


@pytest.mark.asyncio
async def test_claude_api_raise_soft_fails():
    fake_client = MagicMock()
    fake_client.complete = AsyncMock(side_effect=RuntimeError("boom"))
    out = await rediscover_from_corpus(
        corpus=["doc1"], claude_client=fake_client,
    )
    assert any("claude_api_raised" in e for e in out.errors)
    assert out.proposed_mechanisms == []


@pytest.mark.asyncio
async def test_malformed_response_soft_fails():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.content = "not json — just prose"
    fake_client.complete = AsyncMock(return_value=fake_response)
    out = await rediscover_from_corpus(
        corpus=["doc1"], claude_client=fake_client,
    )
    assert any("parse_failed" in e for e in out.errors)


# -----------------------------------------------------------------------------
# Successful pipeline
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_well_formed_response_parsed_into_proposals():
    fake_client = MagicMock()
    payload = {
        "proposed_mechanisms": [
            {
                "name": "trust_via_credentials",
                "evidence_quotes": ["q1", "q2"],
                "supporting_metaphors": ["solidity"],
                "raw_p_value": 0.02,
            },
            {
                "name": "loss_avoidance_priming",
                "evidence_quotes": ["q3", "q4"],
                "supporting_metaphors": [],
                "raw_p_value": 0.30,
            },
        ],
        "proposed_metaphors": [
            {
                "axis_name": "time_as_resource",
                "evidence_quotes": ["t1", "t2"],
                "supporting_tokens": ["clock", "deadline"],
                "raw_p_value": 0.005,
            },
        ],
    }
    fake_response = MagicMock()
    fake_response.content = json.dumps(payload)
    fake_client.complete = AsyncMock(return_value=fake_response)

    out = await rediscover_from_corpus(
        corpus=["LUXY corporate travel"] * 3,
        claude_client=fake_client,
    )
    assert len(out.proposed_mechanisms) == 2
    assert len(out.proposed_metaphors) == 1
    # Strong signal survives BH-FDR; weak does not.
    surviving_mech_names = {
        p.name for p in out.proposed_mechanisms if p.survives_fdr
    }
    assert "trust_via_credentials" in surviving_mech_names
    # The 0.30 p_value should not survive at alpha=0.10.
    assert "loss_avoidance_priming" not in surviving_mech_names

    surviving_metaphors = {
        p.axis_name for p in out.proposed_metaphors if p.survives_fdr
    }
    assert "time_as_resource" in surviving_metaphors


@pytest.mark.asyncio
async def test_versioned_inventory_stamped_on_result():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.content = json.dumps({
        "proposed_mechanisms": [], "proposed_metaphors": [],
    })
    fake_client.complete = AsyncMock(return_value=fake_response)

    out = await rediscover_from_corpus(
        corpus=["doc"],
        claude_client=fake_client,
        inventory_version="luxy-2026-05-02-r1",
    )
    assert out.inventory_version == "luxy-2026-05-02-r1"


@pytest.mark.asyncio
async def test_json_with_code_fence_parsed():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.content = (
        "```json\n"
        + json.dumps({
            "proposed_mechanisms": [{
                "name": "x", "evidence_quotes": [], "raw_p_value": 0.04,
            }],
            "proposed_metaphors": [],
        })
        + "\n```"
    )
    fake_client.complete = AsyncMock(return_value=fake_response)
    out = await rediscover_from_corpus(
        corpus=["doc"], claude_client=fake_client,
    )
    assert len(out.proposed_mechanisms) == 1
    assert out.proposed_mechanisms[0].name == "x"


@pytest.mark.asyncio
async def test_invalid_p_value_clamped_to_one():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.content = json.dumps({
        "proposed_mechanisms": [{
            "name": "x", "evidence_quotes": [],
            "raw_p_value": "not a number",
        }],
        "proposed_metaphors": [],
    })
    fake_client.complete = AsyncMock(return_value=fake_response)
    out = await rediscover_from_corpus(
        corpus=["doc"], claude_client=fake_client,
    )
    assert out.proposed_mechanisms[0].raw_p_value == 1.0


@pytest.mark.asyncio
async def test_empty_proposal_name_filtered():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.content = json.dumps({
        "proposed_mechanisms": [
            {"name": "valid_mech", "raw_p_value": 0.05},
            {"name": "", "raw_p_value": 0.05},  # empty
            {"raw_p_value": 0.05},  # no name
        ],
        "proposed_metaphors": [],
    })
    fake_client.complete = AsyncMock(return_value=fake_response)
    out = await rediscover_from_corpus(
        corpus=["doc"], claude_client=fake_client,
    )
    assert len(out.proposed_mechanisms) == 1
    assert out.proposed_mechanisms[0].name == "valid_mech"
