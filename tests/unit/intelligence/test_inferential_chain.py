"""Unit tests for InferentialChainGraph identity/validation layer.

The Neo4j-facing methods are covered by integration tests against a live
database. These tests verify the dataclass validation that enforces the
citation-required discipline on theoretical edges.
"""

from __future__ import annotations

import dataclasses
import pytest

from adam.intelligence.recommendation_class import (
    ActivatesEdge,
    PsychologicalConstructUpsert,
    ReceptivityEdge,
    RequiresEdge,
)


def _valid_construct() -> PsychologicalConstructUpsert:
    return PsychologicalConstructUpsert(
        construct_id="need_for_closure",
        name="Need for Closure",
        description=(
            "The desire to have a definite answer to a question, any answer, "
            "as opposed to remaining in a state of uncertainty."
        ),
        domain="motivational",
        research_basis="Kruglanski & Webster (1996), Journal of Personality and Social Psychology",
    )


# -----------------------------------------------------------------------------
# PsychologicalConstructUpsert
# -----------------------------------------------------------------------------

class TestPsychologicalConstructUpsert:
    def test_valid(self):
        _valid_construct().validate()

    def test_empty_construct_id_rejected(self):
        c = dataclasses.replace(_valid_construct(), construct_id="")
        with pytest.raises(ValueError, match="construct_id"):
            c.validate()

    def test_empty_name_rejected(self):
        c = dataclasses.replace(_valid_construct(), name="")
        with pytest.raises(ValueError, match="name"):
            c.validate()

    def test_empty_description_rejected(self):
        c = dataclasses.replace(_valid_construct(), description="")
        with pytest.raises(ValueError, match="description"):
            c.validate()

    def test_empty_domain_rejected(self):
        c = dataclasses.replace(_valid_construct(), domain="")
        with pytest.raises(ValueError, match="domain"):
            c.validate()

    def test_empty_research_basis_rejected(self):
        c = dataclasses.replace(_valid_construct(), research_basis="")
        with pytest.raises(ValueError, match="research_basis"):
            c.validate()

    def test_slug_form_enforced(self):
        c = dataclasses.replace(_valid_construct(), construct_id="Need For Closure")
        with pytest.raises(ValueError, match="slug-form"):
            c.validate()


# -----------------------------------------------------------------------------
# ActivatesEdge — theoretical edge with citation-required discipline
# -----------------------------------------------------------------------------

class TestActivatesEdge:
    def test_valid(self):
        edge = ActivatesEdge(
            source_construct_id="uncertainty_intolerance",
            target_construct_id="need_for_closure",
            strength=0.7,
            citation="Kruglanski & Webster (1996)",
        )
        edge.validate()

    def test_citation_required(self):
        """The citation-required discipline is load-bearing for the
        rule that theoretical edges must be grounded in literature.
        Empty citation must be rejected (A6 drift prevention)."""
        edge = ActivatesEdge(
            source_construct_id="uncertainty_intolerance",
            target_construct_id="need_for_closure",
            strength=0.7,
            citation="",
        )
        with pytest.raises(ValueError, match="citation"):
            edge.validate()

    def test_whitespace_only_citation_rejected(self):
        edge = ActivatesEdge(
            source_construct_id="a",
            target_construct_id="b",
            strength=0.5,
            citation="   ",
        )
        with pytest.raises(ValueError, match="citation"):
            edge.validate()

    def test_self_edge_rejected(self):
        edge = ActivatesEdge(
            source_construct_id="same_construct",
            target_construct_id="same_construct",
            strength=0.5,
            citation="anything",
        )
        with pytest.raises(ValueError, match="self-edge"):
            edge.validate()

    def test_strength_out_of_range(self):
        edge = ActivatesEdge(
            source_construct_id="a",
            target_construct_id="b",
            strength=1.5,
            citation="x",
        )
        with pytest.raises(ValueError, match="strength"):
            edge.validate()

    def test_empty_source_rejected(self):
        edge = ActivatesEdge(
            source_construct_id="",
            target_construct_id="b",
            strength=0.5,
            citation="x",
        )
        with pytest.raises(ValueError, match="source_construct_id"):
            edge.validate()


# -----------------------------------------------------------------------------
# ReceptivityEdge — Construct → Mechanism
# -----------------------------------------------------------------------------

class TestReceptivityEdge:
    def test_valid(self):
        edge = ReceptivityEdge(
            source_construct_id="need_for_closure",
            mechanism_name="identity_construction",
            effectiveness=0.75,
            citation="Kruglanski et al. (2006)",
            context="high_cognitive_engagement",
        )
        edge.validate()

    def test_citation_required(self):
        edge = ReceptivityEdge(
            source_construct_id="need_for_closure",
            mechanism_name="identity_construction",
            effectiveness=0.75,
            citation="",
        )
        with pytest.raises(ValueError, match="citation"):
            edge.validate()

    def test_effectiveness_range(self):
        edge = ReceptivityEdge(
            source_construct_id="c",
            mechanism_name="m",
            effectiveness=-0.1,
            citation="x",
        )
        with pytest.raises(ValueError, match="effectiveness"):
            edge.validate()

    def test_empty_mechanism_rejected(self):
        edge = ReceptivityEdge(
            source_construct_id="c",
            mechanism_name="",
            effectiveness=0.5,
            citation="x",
        )
        with pytest.raises(ValueError, match="mechanism_name"):
            edge.validate()


# -----------------------------------------------------------------------------
# RequiresEdge — Mechanism → prerequisite Construct
# -----------------------------------------------------------------------------

class TestRequiresEdge:
    def test_valid(self):
        edge = RequiresEdge(
            mechanism_name="identity_construction",
            prerequisite_construct_id="high_cognitive_engagement",
            citation="Petty & Cacioppo (1986) ELM",
        )
        edge.validate()

    def test_citation_required(self):
        edge = RequiresEdge(
            mechanism_name="m",
            prerequisite_construct_id="c",
            citation="",
        )
        with pytest.raises(ValueError, match="citation"):
            edge.validate()

    def test_empty_mechanism_rejected(self):
        edge = RequiresEdge(
            mechanism_name="",
            prerequisite_construct_id="c",
            citation="x",
        )
        with pytest.raises(ValueError, match="mechanism_name"):
            edge.validate()

    def test_empty_prerequisite_rejected(self):
        edge = RequiresEdge(
            mechanism_name="m",
            prerequisite_construct_id="",
            citation="x",
        )
        with pytest.raises(ValueError, match="prerequisite"):
            edge.validate()


# -----------------------------------------------------------------------------
# Canonical chain example — regression test that the Foundation §4.3 example
# is actually expressible through the data model
# -----------------------------------------------------------------------------

class TestCanonicalChainExpressibility:
    """Foundation §4.3 gives a canonical chain example:

        (UncertaintyIntolerance)-[:CAUSES_NEED_FOR]->(Closure)
        (Closure)-[:SATISFIED_BY]->(Authority)
        (HighCognitiveEngagement)-[:REQUIRES]->(SubstantiveEvidence)

    This test confirms the data model can represent it (modulo relationship-
    name choices — we use ACTIVATES for causes-need-for and
    CREATES_RECEPTIVITY_TO for satisfied-by)."""

    def test_full_chain_validates(self):
        # Constructs
        uncertainty_intolerance = PsychologicalConstructUpsert(
            construct_id="uncertainty_intolerance",
            name="Uncertainty Intolerance",
            description="Discomfort with unresolved questions.",
            domain="cognitive_control",
            research_basis="Carleton (2012), Journal of Anxiety Disorders",
        )
        need_for_closure = _valid_construct()

        uncertainty_intolerance.validate()
        need_for_closure.validate()

        # Construct → Construct (ACTIVATES)
        activates = ActivatesEdge(
            source_construct_id="uncertainty_intolerance",
            target_construct_id="need_for_closure",
            strength=0.8,
            citation="Kruglanski & Webster (1996); Roets & Van Hiel (2011)",
            context="general",
            notes="Canonical Bargh-lineage chain link.",
        )
        activates.validate()

        # Construct → Mechanism (CREATES_RECEPTIVITY_TO)
        # Using 'identity_construction' from migration 004's mechanism list
        # as the stand-in for authority (per MECHANISM_TO_ATOM mapping in
        # adam/constants.py: "authority" -> "identity_construction").
        receptivity = ReceptivityEdge(
            source_construct_id="need_for_closure",
            mechanism_name="identity_construction",
            effectiveness=0.75,
            citation="Kruglanski et al. (2006), European Journal of Social Psychology",
            context="high_cognitive_engagement",
            notes="Need-for-closure → authority receptivity via identity signaling.",
        )
        receptivity.validate()

        # Mechanism → prerequisite (REQUIRES)
        requires = RequiresEdge(
            mechanism_name="identity_construction",
            prerequisite_construct_id="high_cognitive_engagement",
            citation="Petty & Cacioppo (1986) Elaboration Likelihood Model",
            notes="Identity / authority appeals require central-route processing.",
        )
        requires.validate()
