# =============================================================================
# ADAM Online Learning Substrate Tests
# Location: tests/unit/test_online_learning_substrate.py
# =============================================================================

"""Tests for task #30 — per-decision online learning substrate."""

from __future__ import annotations

from typing import Dict
from unittest.mock import MagicMock

import math
import pytest

from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)
from adam.intelligence.online_learning_substrate import (
    aggregate_mechanism_strength,
    aggregate_mechanism_strengths_from_attestations,
    read_link_strengths_batch,
)


# ============================================================================
# Helpers
# ============================================================================


class FakeTheoryLearner:
    """Minimal TheoryLearner stand-in for tests."""

    def __init__(self, strengths: Dict[str, float]) -> None:
        self._strengths = strengths

    def get_link_strength(self, link_key: str) -> float:
        return self._strengths.get(link_key, 0.5)


def _make_link(
    source: str, target: str, relation: RelationType = RelationType.CREATES_NEED_FOR,
) -> ConstructLink:
    return ConstructLink(
        source_construct=source,
        relation_type=relation,
        target_construct=target,
        evidence_value=0.5,
        confidence=0.7,
        citation="test §1",
    )


def _make_attestation(
    *,
    atom_id: str,
    chain_links: list[ConstructLink],
    mechanism_adjustments: list[tuple[str, list[str], float]],
) -> ChainAttestation:
    """Build a chain attestation. mechanism_adjustments is list of
    (mechanism_id, list-of-link-ids, adjustment_value)."""
    final = TypedEvidence(
        construct="x",
        value=0.5,
        confidence=0.7,
        citation="test §1",
        calibration_status=CalibrationStatus.PINNED,
    )
    adj_ev = [
        AdjustmentEvidence(
            mechanism_id=mech,
            adjustment_value=val,
            chain_links_responsible=link_ids,
            confidence=0.7,
        )
        for mech, link_ids, val in mechanism_adjustments
    ]
    return ChainAttestation(
        atom_id=atom_id,
        request_id="req",
        target_construct="t",
        chain=chain_links,
        final_assessment=final,
        mechanism_adjustments=adj_ev,
        provenance=ChainProvenance(atom_id=atom_id),
    )


# ============================================================================
# read_link_strengths_batch
# ============================================================================


class TestBatchRead:

    def test_known_keys_return_strengths(self):
        learner = FakeTheoryLearner({
            "CREATES_NEED_FOR:a:b": 0.7,
            "CREATES_NEED_FOR:c:d": 0.3,
        })
        result = read_link_strengths_batch(
            learner, ["CREATES_NEED_FOR:a:b", "CREATES_NEED_FOR:c:d"],
        )
        assert result == {
            "CREATES_NEED_FOR:a:b": 0.7,
            "CREATES_NEED_FOR:c:d": 0.3,
        }

    def test_unknown_keys_return_neutral(self):
        learner = FakeTheoryLearner({})
        result = read_link_strengths_batch(learner, ["unknown:a:b"])
        assert result == {"unknown:a:b": 0.5}


# ============================================================================
# aggregate_mechanism_strength — geometric mean
# ============================================================================


class TestGeometricAggregation:

    def test_empty_list_neutral(self):
        learner = FakeTheoryLearner({})
        assert aggregate_mechanism_strength([], learner) == 0.5

    def test_single_link_returns_strength(self):
        learner = FakeTheoryLearner({"CREATES_NEED_FOR:a:b": 0.7})
        result = aggregate_mechanism_strength(
            ["CREATES_NEED_FOR:a:b"], learner,
        )
        assert result == pytest.approx(0.7, abs=1e-9)

    def test_geometric_mean_of_two_links(self):
        learner = FakeTheoryLearner({
            "k1": 0.4,
            "k2": 0.9,
        })
        # Geometric mean: sqrt(0.4 * 0.9) ≈ 0.6
        result = aggregate_mechanism_strength(["k1", "k2"], learner)
        assert result == pytest.approx(math.sqrt(0.4 * 0.9), abs=1e-9)

    def test_geometric_mean_drags_with_weak_link(self):
        """A chain with one weak link produces a lower aggregate than
        the arithmetic mean would. Foundation §4.4: chains are
        multiplicative."""
        learner = FakeTheoryLearner({
            "k1": 0.1,    # weak
            "k2": 0.7,
            "k3": 0.7,
        })
        # Geometric: (0.1 * 0.7 * 0.7) ^ (1/3) ≈ 0.365
        # Arithmetic: 0.5 — would mask the weak link
        result = aggregate_mechanism_strength(["k1", "k2", "k3"], learner)
        arithmetic = (0.1 + 0.7 + 0.7) / 3
        assert result < arithmetic
        assert result == pytest.approx((0.1 * 0.7 * 0.7) ** (1/3), abs=1e-9)

    def test_zero_strength_zeros_aggregate(self):
        """A dead link kills the chain."""
        learner = FakeTheoryLearner({"k1": 0.0, "k2": 0.9})
        result = aggregate_mechanism_strength(["k1", "k2"], learner)
        assert result == 0.0

    def test_unknown_keys_get_neutral_in_aggregate(self):
        learner = FakeTheoryLearner({})  # all keys unknown → 0.5 each
        result = aggregate_mechanism_strength(
            ["unknown1", "unknown2", "unknown3"], learner,
        )
        # Geometric mean of 3 × 0.5 = 0.5
        assert result == pytest.approx(0.5, abs=1e-9)


# ============================================================================
# aggregate_mechanism_strengths_from_attestations
# ============================================================================


class TestAttestationAggregation:

    def test_single_attestation_single_mechanism(self):
        learner = FakeTheoryLearner({})  # all 0.5
        link1 = _make_link("a", "b")
        link2 = _make_link("c", "d")
        att = _make_attestation(
            atom_id="atom_x",
            chain_links=[link1, link2],
            mechanism_adjustments=[
                ("authority", [link1.link_id, link2.link_id], 0.1),
            ],
        )
        result = aggregate_mechanism_strengths_from_attestations(
            [att], learner,
        )
        # Geometric mean of two unknowns at 0.5 each = 0.5
        assert "authority" in result
        assert result["authority"] == pytest.approx(0.5, abs=1e-6)

    def test_single_attestation_uses_real_strengths(self):
        link1 = _make_link("a", "b")
        link2 = _make_link("c", "d")
        learner = FakeTheoryLearner({
            link1.link_key: 0.4,
            link2.link_key: 0.9,
        })
        att = _make_attestation(
            atom_id="atom_x",
            chain_links=[link1, link2],
            mechanism_adjustments=[
                ("authority", [link1.link_id, link2.link_id], 0.1),
            ],
        )
        result = aggregate_mechanism_strengths_from_attestations(
            [att], learner,
        )
        # Geometric mean of (0.4, 0.9) = sqrt(0.36) = 0.6
        assert result["authority"] == pytest.approx(math.sqrt(0.4 * 0.9), abs=1e-6)

    def test_multiple_attestations_average_per_mechanism(self):
        """When two attestations both contribute to 'authority',
        average their per-attestation aggregates."""
        link_a = _make_link("aa", "ab")
        link_b = _make_link("ba", "bb")
        learner = FakeTheoryLearner({
            link_a.link_key: 0.6,
            link_b.link_key: 0.4,
        })
        att1 = _make_attestation(
            atom_id="atom_1",
            chain_links=[link_a],
            mechanism_adjustments=[("authority", [link_a.link_id], 0.1)],
        )
        att2 = _make_attestation(
            atom_id="atom_2",
            chain_links=[link_b],
            mechanism_adjustments=[("authority", [link_b.link_id], -0.05)],
        )
        result = aggregate_mechanism_strengths_from_attestations(
            [att1, att2], learner,
        )
        # att1 produces 0.6 for authority, att2 produces 0.4
        # Average across attestations: 0.5
        assert result["authority"] == pytest.approx(0.5, abs=1e-6)

    def test_unknown_link_id_in_adjustment_skipped(self):
        """An adjustment_value referencing a link_id NOT in the chain
        is silently dropped from the aggregate."""
        link1 = _make_link("a", "b")
        learner = FakeTheoryLearner({link1.link_key: 0.7})
        att = _make_attestation(
            atom_id="atom_x",
            chain_links=[link1],
            mechanism_adjustments=[
                ("authority", [link1.link_id, "fake_link_id"], 0.1),
            ],
        )
        result = aggregate_mechanism_strengths_from_attestations(
            [att], learner,
        )
        # Only link1's strength used (fake link skipped)
        assert result["authority"] == pytest.approx(0.7, abs=1e-6)

    def test_no_link_ids_means_mechanism_skipped(self):
        """If all chain_links_responsible are unknown to the chain,
        the mechanism is dropped from the result."""
        link1 = _make_link("a", "b")
        learner = FakeTheoryLearner({})
        att = _make_attestation(
            atom_id="atom_x",
            chain_links=[link1],
            mechanism_adjustments=[
                ("authority", ["fake_id_1", "fake_id_2"], 0.1),
            ],
        )
        result = aggregate_mechanism_strengths_from_attestations(
            [att], learner,
        )
        assert "authority" not in result

    def test_empty_attestation_list_empty_result(self):
        learner = FakeTheoryLearner({})
        result = aggregate_mechanism_strengths_from_attestations(
            [], learner,
        )
        assert result == {}


# ============================================================================
# Online-learning property test
# ============================================================================


class TestOnlineLearningProperty:
    """The substrate's load-bearing property: when LinkPosteriors update
    between decisions, the aggregator reads the new values without
    cache invalidation."""

    def test_updated_strengths_reflected_in_next_aggregate(self):
        """Build an attestation, call aggregator, then mutate the
        learner's stored strengths, call aggregator again — second
        call sees the mutated values."""
        link1 = _make_link("a", "b")
        link2 = _make_link("c", "d")
        att = _make_attestation(
            atom_id="atom_x",
            chain_links=[link1, link2],
            mechanism_adjustments=[
                ("authority", [link1.link_id, link2.link_id], 0.1),
            ],
        )

        # Round 1: link strengths at 0.5
        learner = FakeTheoryLearner({
            link1.link_key: 0.5,
            link2.link_key: 0.5,
        })
        round1 = aggregate_mechanism_strengths_from_attestations(
            [att], learner,
        )
        assert round1["authority"] == pytest.approx(0.5, abs=1e-6)

        # Outcomes flow; LinkPosteriors update; learner now has higher strengths
        learner._strengths[link1.link_key] = 0.8
        learner._strengths[link2.link_key] = 0.8

        # Round 2: aggregator reads fresh strengths
        round2 = aggregate_mechanism_strengths_from_attestations(
            [att], learner,
        )
        assert round2["authority"] == pytest.approx(0.8, abs=1e-6)
        # The increase happened without cache invalidation — that IS
        # the per-decision online learning loop.
        assert round2["authority"] > round1["authority"]
