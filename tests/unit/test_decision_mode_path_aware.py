"""Pin path-aware grounding evidence + mode derivation.

Discipline anchors:
    - The cascade-only path (stackadapt_creative_intelligence) and the
      orchestrator path (cascade + atom DAG + theoretical traversal)
      produce different evidence shapes. The same derive_mode function
      must apply the correct gate for each path.
    - Backwards compat: existing callers that don't set decision_path
      get the campaign_orchestrator 3-link logic — same behavior as
      before this typed-evidence shipped.
    - Stackadapt path's gate: GROUNDED requires cascade_level >= 3 AND
      bilateral_edge_evidence_present. Without this gate, every L1/L2-
      only fallback decision was being marked GROUNDED via the legacy
      default and writing posteriors as if it had bilateral evidence.
"""

from __future__ import annotations

from adam.core.decision_mode import (
    DecisionMode,
    GroundingEvidence,
    derive_mode,
    from_outcome_metadata,
    should_update_posteriors,
)


# -----------------------------------------------------------------------------
# StackAdapt creative-intelligence path — new gate
# -----------------------------------------------------------------------------


def test_stackadapt_path_grounded_requires_l3_with_edges():
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=True,
        atom_run_real=False,  # N/A on this path
        theoretical_link_traversed=False,  # N/A on this path
        decision_path="stackadapt_creative_intelligence",
        cascade_level=3,
        edge_count=12317,
    )
    assert derive_mode(evidence) == DecisionMode.GROUNDED


def test_stackadapt_path_l4_with_edges_also_grounded():
    """cascade_level 4 (inferential transfer) with bilateral evidence
    is also GROUNDED on the stackadapt path."""
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=True,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=4,
        edge_count=200,
    )
    assert derive_mode(evidence) == DecisionMode.GROUNDED


def test_stackadapt_path_l1_only_is_incomplete_not_grounded():
    """The pre-fix bug: legacy default marked L1/L2-only decisions as
    GROUNDED. New path-aware logic correctly classifies them as
    INCOMPLETE — posteriors don't update on these."""
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=False,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=1,
        edge_count=0,
    )
    assert derive_mode(evidence) == DecisionMode.INCOMPLETE


def test_stackadapt_path_l2_only_is_incomplete():
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=False,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=2,
        edge_count=0,
    )
    assert derive_mode(evidence) == DecisionMode.INCOMPLETE


def test_stackadapt_path_l3_with_insufficient_edges_is_incomplete():
    """Reaching L3 isn't enough — needs bilateral_edge_evidence_present
    flag too (which the producer sets only when edge_count meets
    cfg.l3_min_edge_count). This guards against marking decisions as
    GROUNDED when L3 fired but with insufficient edge data."""
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=False,  # producer set False due to insufficient edges
        decision_path="stackadapt_creative_intelligence",
        cascade_level=3,
        edge_count=2,  # below threshold
    )
    assert derive_mode(evidence) == DecisionMode.INCOMPLETE


def test_stackadapt_path_cascade_level_zero_is_refused():
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=False,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=0,
        edge_count=0,
    )
    assert derive_mode(evidence) == DecisionMode.REFUSED


def test_stackadapt_path_grounded_authorizes_posterior_updates():
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=True,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=3,
        edge_count=100,
    )
    mode = derive_mode(evidence)
    assert should_update_posteriors(mode) is True


def test_stackadapt_path_incomplete_blocks_posterior_updates():
    """The whole point of typed grounding: degraded decisions DON'T
    write posteriors. Failing this test means the cascade L1/L2 fallback
    path can corrupt the BayesianPrior posteriors."""
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=False,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=2,
    )
    mode = derive_mode(evidence)
    assert mode == DecisionMode.INCOMPLETE
    assert should_update_posteriors(mode) is False


# -----------------------------------------------------------------------------
# Campaign orchestrator path — backwards compat (3-link logic unchanged)
# -----------------------------------------------------------------------------


def test_orchestrator_path_default_uses_3_link_logic():
    """Callers that don't set decision_path get the orchestrator 3-link
    logic — backwards compat with all existing call sites."""
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=True,
        atom_run_real=True,
        theoretical_link_traversed=True,
    )
    # decision_path defaulted to campaign_orchestrator
    assert evidence.decision_path == "campaign_orchestrator"
    assert derive_mode(evidence) == DecisionMode.GROUNDED


def test_orchestrator_path_2_of_3_is_incomplete():
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=True,
        atom_run_real=True,
        theoretical_link_traversed=False,
    )
    assert derive_mode(evidence) == DecisionMode.INCOMPLETE


def test_orchestrator_path_0_of_3_is_refused():
    evidence = GroundingEvidence(
        bilateral_edge_evidence_present=False,
        atom_run_real=False,
        theoretical_link_traversed=False,
    )
    assert derive_mode(evidence) == DecisionMode.REFUSED


# -----------------------------------------------------------------------------
# Serialization round-trip
# -----------------------------------------------------------------------------


def test_evidence_round_trips_through_dict():
    """Producer → DecisionContext → cache → outcome metadata → reader
    must preserve all typed-evidence fields."""
    original = GroundingEvidence(
        bilateral_edge_evidence_present=True,
        atom_run_real=False,
        theoretical_link_traversed=False,
        decision_path="stackadapt_creative_intelligence",
        cascade_level=3,
        edge_count=12317,
        failure_reasons=["test"],
    )
    serialized = original.as_full_dict()
    deserialized = GroundingEvidence.from_dict(serialized)

    assert deserialized.bilateral_edge_evidence_present == original.bilateral_edge_evidence_present
    assert deserialized.atom_run_real == original.atom_run_real
    assert deserialized.theoretical_link_traversed == original.theoretical_link_traversed
    assert deserialized.decision_path == original.decision_path
    assert deserialized.cascade_level == original.cascade_level
    assert deserialized.edge_count == original.edge_count
    assert deserialized.failure_reasons == original.failure_reasons


def test_legacy_metadata_dict_falls_back_to_orchestrator_path():
    """Outcomes from decisions persisted BEFORE this typed-evidence
    shipped will have metadata without decision_path / cascade_level /
    edge_count keys. from_dict must default these to
    campaign_orchestrator path with zero scalars — preserving the
    legacy 3-link logic for those outcomes."""
    legacy_dict = {
        "bilateral_edge_evidence_present": True,
        "atom_run_real": True,
        "theoretical_link_traversed": True,
    }
    evidence = GroundingEvidence.from_dict(legacy_dict)
    assert evidence.decision_path == "campaign_orchestrator"
    assert evidence.cascade_level == 0
    assert evidence.edge_count == 0
    # 3-link logic still applies for legacy
    assert derive_mode(evidence) == DecisionMode.GROUNDED


def test_from_outcome_metadata_reads_new_evidence_dict():
    """The metadata path the outcome handler uses to recover the
    grounding evidence must surface decision_path + cascade_level +
    edge_count for the new-shape evidence dicts produced by the
    StackAdapt cascade."""
    metadata = {
        "decision_mode": "incomplete",
        "grounding_evidence": {
            "bilateral_edge_evidence_present": False,
            "decision_path": "stackadapt_creative_intelligence",
            "cascade_level": 2,
            "edge_count": 0,
        },
    }
    mode, evidence = from_outcome_metadata(metadata)
    assert mode == DecisionMode.INCOMPLETE
    assert evidence.decision_path == "stackadapt_creative_intelligence"
    assert evidence.cascade_level == 2
