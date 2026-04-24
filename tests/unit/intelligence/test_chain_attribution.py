"""Unit tests for chain_attribution — the pure-Python attribution path.

Graph-traversal (Neo4j-backed) is not covered here; integration tests
against a live Neo4j / test container live in tests/integration.
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.recommendation_class import (
    ChainEdge,
    attribute_residual,
    compute_link_id,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _activates(src: str, dst: str, strength: float, depth: int = 2) -> ChainEdge:
    return ChainEdge(
        source_id=src,
        target_id=dst,
        rel_type="ACTIVATES",
        strength=strength,
        evidence_count=0,
        depth_from_mechanism=depth,
    )


def _receptivity(src: str, dst: str, effectiveness: float) -> ChainEdge:
    return ChainEdge(
        source_id=src,
        target_id=dst,
        rel_type="CREATES_RECEPTIVITY_TO",
        strength=effectiveness,
        evidence_count=0,
        depth_from_mechanism=1,
    )


def _requires(src: str, dst: str) -> ChainEdge:
    return ChainEdge(
        source_id=src,
        target_id=dst,
        rel_type="REQUIRES",
        strength=0.0,
        evidence_count=0,
        depth_from_mechanism=1,
    )


# -----------------------------------------------------------------------------
# ChainEdge validation
# -----------------------------------------------------------------------------


class TestChainEdgeValidation:
    def test_rejects_empty_source(self):
        edge = ChainEdge(
            source_id="",
            target_id="mechanism_x",
            rel_type="CREATES_RECEPTIVITY_TO",
            strength=0.5,
            evidence_count=0,
            depth_from_mechanism=1,
        )
        with pytest.raises(ValueError, match="source_id is required"):
            edge.validate()

    def test_rejects_unknown_rel_type(self):
        edge = ChainEdge(
            source_id="c1",
            target_id="c2",
            rel_type="CAUSES",  # type: ignore[arg-type]
            strength=0.5,
            evidence_count=0,
            depth_from_mechanism=1,
        )
        with pytest.raises(ValueError, match="rel_type must be"):
            edge.validate()

    def test_rejects_strength_out_of_range(self):
        edge = ChainEdge(
            source_id="c1",
            target_id="c2",
            rel_type="ACTIVATES",
            strength=1.5,
            evidence_count=0,
            depth_from_mechanism=2,
        )
        with pytest.raises(ValueError, match=r"strength must be in \[0, 1\]"):
            edge.validate()

    def test_rejects_negative_evidence_count(self):
        edge = ChainEdge(
            source_id="c1",
            target_id="c2",
            rel_type="ACTIVATES",
            strength=0.5,
            evidence_count=-1,
            depth_from_mechanism=2,
        )
        with pytest.raises(ValueError, match="evidence_count must be >= 0"):
            edge.validate()

    def test_rejects_depth_below_one(self):
        edge = ChainEdge(
            source_id="c1",
            target_id="c2",
            rel_type="ACTIVATES",
            strength=0.5,
            evidence_count=0,
            depth_from_mechanism=0,
        )
        with pytest.raises(ValueError, match="depth_from_mechanism must be >= 1"):
            edge.validate()


# -----------------------------------------------------------------------------
# link_id determinism
# -----------------------------------------------------------------------------


class TestLinkId:
    def test_same_inputs_same_id(self):
        a = compute_link_id("c1", "ACTIVATES", "c2")
        b = compute_link_id("c1", "ACTIVATES", "c2")
        assert a == b

    def test_different_rel_type_different_id(self):
        a = compute_link_id("c1", "ACTIVATES", "c2")
        b = compute_link_id("c1", "REQUIRES", "c2")
        assert a != b

    def test_direction_matters(self):
        # ACTIVATES is directional; reversing source/target must hash differently.
        a = compute_link_id("c1", "ACTIVATES", "c2")
        b = compute_link_id("c2", "ACTIVATES", "c1")
        assert a != b

    def test_id_has_stable_prefix(self):
        # Readers rely on "link_" prefix for display parsing.
        link_id = compute_link_id("foo", "ACTIVATES", "bar")
        assert link_id.startswith("link_")

    def test_chain_edge_property_matches_function(self):
        edge = _activates("c1", "c2", 0.7)
        assert edge.link_id == compute_link_id("c1", "ACTIVATES", "c2")


# -----------------------------------------------------------------------------
# attribute_residual — empty / edge cases
# -----------------------------------------------------------------------------


class TestAttributeResidualEdgeCases:
    def test_empty_chain_returns_empty(self):
        assert attribute_residual([], -0.05) == {}

    def test_zero_residual_returns_empty(self):
        edges = [_activates("c1", "c2", 0.5), _receptivity("c2", "mech_x", 0.8)]
        assert attribute_residual(edges, 0.0) == {}

    def test_all_requires_returns_empty(self):
        # REQUIRES edges carry zero weight — attribution must be empty rather
        # than flat, because flat would be dishonest pseudo-attribution.
        edges = [_requires("mech_x", "prereq_1"), _requires("mech_x", "prereq_2")]
        assert attribute_residual(edges, -0.1) == {}

    def test_all_strength_zero_returns_empty(self):
        # If every magnitude-bearing edge has strength 0 (e.g., graph
        # defaults), attribution must be empty rather than divide by zero.
        edges = [_activates("c1", "c2", 0.0), _receptivity("c2", "mech_x", 0.0)]
        assert attribute_residual(edges, -0.1) == {}


# -----------------------------------------------------------------------------
# attribute_residual — attribution math
# -----------------------------------------------------------------------------


class TestAttributeResidualMath:
    def test_single_edge_gets_entire_residual(self):
        edge = _receptivity("c1", "mech_x", 0.8)
        out = attribute_residual([edge], -0.04)
        assert len(out) == 1
        assert math.isclose(out[edge.link_id], -0.04)

    def test_attribution_preserves_sign_negative(self):
        # FAILING cells have negative unexplained residual.
        edges = [_receptivity("c1", "mech_x", 1.0), _activates("c0", "c1", 1.0)]
        out = attribute_residual(edges, -0.1)
        assert all(v < 0 for v in out.values())
        assert math.isclose(sum(out.values()), -0.1, abs_tol=1e-9)

    def test_attribution_preserves_sign_positive(self):
        edges = [_receptivity("c1", "mech_x", 1.0), _activates("c0", "c1", 1.0)]
        out = attribute_residual(edges, 0.1)
        assert all(v > 0 for v in out.values())
        assert math.isclose(sum(out.values()), 0.1, abs_tol=1e-9)

    def test_proportional_to_strength(self):
        # Equal depth, two edges. Stronger edge gets larger share.
        strong = _receptivity("c_strong", "mech_x", 0.9)
        weak = _receptivity("c_weak", "mech_x", 0.1)
        out = attribute_residual([strong, weak], -0.1)
        assert out[strong.link_id] < out[weak.link_id]  # more negative = larger share of failure
        assert math.isclose(
            out[strong.link_id] / out[weak.link_id], 9.0, abs_tol=1e-9,
        )

    def test_requires_edges_ignored_in_mixed_input(self):
        # REQUIRES alongside magnitude-bearing edges: magnitude-bearing
        # edges get all attribution; REQUIRES entries are absent from dict.
        receptive = _receptivity("c1", "mech_x", 0.5)
        prereq = _requires("mech_x", "prereq_1")
        out = attribute_residual([receptive, prereq], -0.05)
        assert receptive.link_id in out
        assert prereq.link_id not in out

    def test_sum_equals_residual(self):
        edges = [
            _receptivity("c1", "mech_x", 0.5),
            _receptivity("c2", "mech_x", 0.3),
            _activates("c0", "c1", 0.2),
        ]
        residual = -0.2
        out = attribute_residual(edges, residual)
        assert math.isclose(sum(out.values()), residual, abs_tol=1e-9)

    def test_duplicate_link_ids_sum_portions(self):
        # If traversal produces the same edge twice (e.g., two different
        # cascade paths converge on it), portions must sum rather than
        # overwrite.
        edge_a = _activates("c1", "c2", 0.5, depth=2)
        # Same (source, rel_type, target) — link_ids will match.
        edge_b = _activates("c1", "c2", 0.5, depth=3)
        out = attribute_residual([edge_a, edge_b], -0.1)
        assert len(out) == 1
        assert math.isclose(out[edge_a.link_id], -0.1, abs_tol=1e-9)
