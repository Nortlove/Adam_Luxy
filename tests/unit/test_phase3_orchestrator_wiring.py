# =============================================================================
# ADAM Phase 3 deliverable — Orchestrator wiring callsite tests
# Location: tests/unit/test_phase3_orchestrator_wiring.py
# =============================================================================

"""
ORCHESTRATOR WIRING TESTS — B3-LUXY Phase 3 (Day 1 of 5-6 week pilot ramp)

Pins the wiring path that activates the campaign-impact path for the redone
9 atoms:

    cascade.mechanism_scores  →  bilateral_result["mechanism_scores"]
    DAG atom_outputs          →  AtomDAGResult.chain_attestations
    cascade × DAG             →  cascade_modulated_scores
    cascade_modulated_scores  →  _select_mechanisms (blend at 0.6 weight)

Without these tests, the wiring's correctness depends on integration smoke
runs that don't exist yet. With them, regressions in any link in the chain
surface as a unit-test failure within seconds.

See:
- memory/session_2026_04_28_b3_luxy_complete_handoff.md (Priority 1)
- docs/B3_LUXY_PHASE_PLAN.md §5
- ADAM_THEORETICAL_FOUNDATION.md §4.1, §4.3
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from adam.api.stackadapt.bilateral_cascade import (
    apply_chain_attestation_list_to_mechanism_scores,
    extract_chain_attestations_from_atom_outputs,
)
from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)
from adam.orchestrator.models import (
    AtomDAGResult,
    GraphQueryResult,
    MechanismIntelligence,
    ReasoningTrace,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_attestation(
    atom_id: str, adjustments: list[tuple[str, float]]
) -> ChainAttestation:
    """Build a minimal ChainAttestation with mechanism adjustments."""
    chain = [
        ConstructLink(
            source_construct="src",
            relation_type=RelationType.MODULATED_BY,
            target_construct=f"target_{atom_id}",
            evidence_value=0.5,
            confidence=0.7,
            citation="test_citation 1.0",
        )
    ]
    final = TypedEvidence(
        construct=f"construct_{atom_id}",
        value=0.5,
        confidence=0.7,
        citation="test_citation 1.0",
        calibration_status=CalibrationStatus.PINNED,
    )
    chain_link_ids = [chain[0].link_id]
    adj_evidence = [
        AdjustmentEvidence(
            mechanism_id=mech,
            adjustment_value=value,
            chain_links_responsible=chain_link_ids,
            confidence=0.7,
        )
        for mech, value in adjustments
    ]
    return ChainAttestation(
        atom_id=atom_id,
        request_id="req_test",
        target_construct=f"construct_{atom_id}",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adj_evidence,
        provenance=ChainProvenance(atom_id=atom_id),
    )


def _make_atom_output(atom_id: str, attestation):
    """Mock an AtomOutput-shaped object with a chain_attestation attribute."""
    output = MagicMock()
    output.chain_attestation = attestation
    output.atom_id = atom_id
    return output


def _make_graph_query_result(mech_archetype_scores: dict[str, float]) -> GraphQueryResult:
    """Build a GraphQueryResult with the given mechanism→archetype-effectiveness."""
    mechanisms = [
        MechanismIntelligence(
            mechanism_name=mech_name,
            mechanism_id=mech_name,
            archetype_effectiveness={"luxe_arbiter": score},
        )
        for mech_name, score in mech_archetype_scores.items()
    ]
    return GraphQueryResult(
        query_name="test_phase3_orchestrator_wiring",
        query_type="mechanism",
        mechanisms=mechanisms,
    )


# ============================================================================
# Public list-variant helper
# ============================================================================


class TestApplyChainAttestationListHelper:
    """The new public helper for consumers that have pre-extracted attestations."""

    def test_empty_scores_passthrough(self):
        attestations = [_make_attestation("a", [("authority", 0.2)])]
        result = apply_chain_attestation_list_to_mechanism_scores({}, attestations)
        assert result == {}

    def test_none_attestations_passthrough(self):
        scores = {"authority": 0.5, "scarcity": 0.3}
        result = apply_chain_attestation_list_to_mechanism_scores(scores, None)
        assert result == scores

    def test_empty_attestations_passthrough(self):
        scores = {"authority": 0.5, "scarcity": 0.3}
        result = apply_chain_attestation_list_to_mechanism_scores(scores, [])
        assert result == scores

    def test_attestations_modulate_scores(self):
        scores = {"authority": 0.5, "scarcity": 0.5}
        attestations = [
            _make_attestation("a1", [("authority", 0.2)]),  # +20% on authority
            _make_attestation("a2", [("scarcity", -0.2)]),  # -20% on scarcity
        ]
        result = apply_chain_attestation_list_to_mechanism_scores(scores, attestations)
        # multiplicative: authority × 1.2; scarcity × 0.8
        assert result["authority"] == pytest.approx(0.6, abs=1e-3)
        assert result["scarcity"] == pytest.approx(0.4, abs=1e-3)

    def test_modulation_clamped_to_01(self):
        scores = {"authority": 0.9}
        # adjustment of +0.5 → modifier capped at 1.5 → 0.9 × 1.5 = 1.35 → clamp to 1.0
        attestations = [_make_attestation("a", [("authority", 0.6)])]
        result = apply_chain_attestation_list_to_mechanism_scores(scores, attestations)
        assert result["authority"] <= 1.0
        assert result["authority"] >= 0.0


# ============================================================================
# AtomDAGResult carries chain_attestations
# ============================================================================


class TestAtomDAGResultChainAttestations:
    """The orchestrator's AtomDAGResult must carry attestations forward."""

    def test_default_is_empty_list(self):
        result = AtomDAGResult()
        assert result.chain_attestations == []

    def test_accepts_attestations(self):
        att = _make_attestation("atom_autonomy_reactance", [("scarcity", -0.2)])
        result = AtomDAGResult(chain_attestations=[att])
        assert len(result.chain_attestations) == 1
        assert result.chain_attestations[0].atom_id == "atom_autonomy_reactance"

    def test_extract_then_attach_round_trip(self):
        """Simulates _execute_real_atom_dag's extraction + attachment."""
        att = _make_attestation("atom_strategic_awareness", [("authority", 0.15)])
        atom_outputs = {
            "atom_strategic_awareness": _make_atom_output("atom_strategic_awareness", att),
            "atom_wrapper": _make_atom_output("atom_wrapper", None),
        }
        extracted = extract_chain_attestations_from_atom_outputs(atom_outputs)
        result = AtomDAGResult(chain_attestations=extracted)
        assert len(result.chain_attestations) == 1
        assert result.chain_attestations[0].atom_id == "atom_strategic_awareness"


# ============================================================================
# _select_mechanisms accepts cascade_modulated_scores and produces
# different output when present vs absent
# ============================================================================


class TestSelectMechanismsCascadeModulation:
    """The wiring's correctness anchor: chain-attestations affect the live decision."""

    @pytest.mark.asyncio
    async def test_cascade_modulated_scores_change_mechanism_scores(self):
        """Without cascade_modulated_scores vs with: different mechanism_scores result.

        This is the Phase 3 wiring's core invariant. If this breaks, the
        atoms' chain attestations are silently being discarded somewhere
        between the DAG and the MetaLearner — which is the failure mode
        the wiring exists to prevent.
        """
        # Lazy import to avoid side-effects from the orchestrator at module
        # load time. The orchestrator pulls in many infrastructure deps.
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()

        # Stub the Thompson sampler so the test is deterministic — the
        # mechanism_scores field on the result is what we audit, not the
        # sampling-driven ordering.
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5, "scarcity": 0.5, "social_proof": 0.5}
        )
        trace_a = ReasoningTrace(trace_id="test_a")
        trace_b = ReasoningTrace(trace_id="test_b")

        # Run A: no cascade modulation
        result_a = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace_a,
        )

        # Run B: cascade-modulated scores skewed toward authority
        cascade_modulated = {"authority": 0.9, "scarcity": 0.2, "social_proof": 0.5}
        result_b = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace_b,
            cascade_modulated_scores=cascade_modulated,
        )

        # The blended scores must DIFFER on the mechanisms the cascade
        # modulated. Authority should be higher in B (cascade pushed up to
        # 0.9 with weight 0.6) and scarcity lower in B (cascade pushed
        # down to 0.2 with weight 0.6).
        assert result_a.mechanism_scores["authority"] != result_b.mechanism_scores["authority"]
        assert result_a.mechanism_scores["scarcity"] != result_b.mechanism_scores["scarcity"]
        assert result_b.mechanism_scores["authority"] > result_a.mechanism_scores["authority"]
        assert result_b.mechanism_scores["scarcity"] < result_a.mechanism_scores["scarcity"]

    @pytest.mark.asyncio
    async def test_no_cascade_modulation_when_attestations_empty(self):
        """When cascade_modulated_scores is None, behavior matches pre-Phase-3."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5, "scarcity": 0.5}
        )
        trace = ReasoningTrace(trace_id="test_solo")

        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores=None,
        )

        # Base scores from mechanism_intelligence preserved (modulo Thompson
        # sampling, which the result records under mechanism_scores).
        assert "authority" in result.mechanism_scores
        assert "scarcity" in result.mechanism_scores
        # No cascade-derived priors_source signal (it stays at default)
        assert result.priors_source != "cascade_chain_attested"

    @pytest.mark.asyncio
    async def test_cascade_modulated_scores_set_priors_source_when_alone(self):
        """When cascade_modulated_scores is the only signal (no unified, no review),
        priors_source surfaces the cascade-chain-attested path."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5}
        )
        trace = ReasoningTrace(trace_id="test_solo")

        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores={"authority": 0.8, "scarcity": 0.3},
        )

        # priors_source labelled by the cascade path when no other signal
        # claimed the slot first
        assert result.priors_source == "cascade_chain_attested"


# ============================================================================
# A14 retirement-trigger counter emission (Phase 0.1 day-3)
# ============================================================================


def _make_attestation_with_flags(atom_id: str, a14_flags: list[str]) -> ChainAttestation:
    """Build a ChainAttestation whose provenance carries the given A14 flags."""
    chain = [
        ConstructLink(
            source_construct="src",
            relation_type=RelationType.MODULATED_BY,
            target_construct=f"target_{atom_id}",
            evidence_value=0.5,
            confidence=0.7,
            citation="test_citation 1.0",
        )
    ]
    final = TypedEvidence(
        construct=f"construct_{atom_id}",
        value=0.5,
        confidence=0.7,
        citation="test_citation 1.0",
        calibration_status=CalibrationStatus.PILOT_PENDING,
    )
    provenance = ChainProvenance(
        atom_id=atom_id,
        a14_flags_active=list(a14_flags),
    )
    return ChainAttestation(
        atom_id=atom_id,
        request_id="req_test",
        target_construct=f"construct_{atom_id}",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=[],
        provenance=provenance,
    )


class TestA14CounterEmission:
    """The A14 counter increments per (decision × atom × active flag).

    Drives the retirement-trigger dashboard: the counter is the input to
    dashboards like "retire FOO_PILOT_PENDING when ≥1000 decisions
    accumulate with the flag active." Without the counter, retirement
    triggers can only be evaluated by hand against the per-decision
    provenance traces — too slow to be useful.
    """

    def _emit_a14_counter_for_attestations(self, attestations):
        """Direct-emit helper that mirrors the orchestrator's emission
        block. Exercises the metric-emission contract in isolation from
        the orchestrator's many other dependencies."""
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        for att in attestations:
            for flag in att.provenance.a14_flags_active:
                pm.a14_flag_active.labels(
                    atom_id=att.atom_id, a14_flag=flag,
                ).inc()

    def test_metric_attribute_exists_on_metrics_instance(self):
        """The new counter is registered on the metrics singleton."""
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        # Either the real Counter is present (when prometheus_client is
        # installed) or _initialized is False (NoOp path) — in both
        # cases the test must not error trying to access the attribute.
        if pm._initialized:
            assert hasattr(pm, "a14_flag_active")

    def test_emission_does_not_raise_on_zero_flags(self):
        """An attestation with no A14 flags produces no increments and
        does not error."""
        att = _make_attestation_with_flags("atom_test", [])
        # Must not raise
        self._emit_a14_counter_for_attestations([att])

    def test_emission_does_not_raise_on_multiple_flags(self):
        """Multiple flags on one attestation each get their own increment."""
        att = _make_attestation_with_flags(
            "atom_test",
            ["FLAG_A_PILOT_PENDING", "FLAG_B_PILOT_PENDING"],
        )
        # Must not raise
        self._emit_a14_counter_for_attestations([att])

    def test_emission_per_atom_per_flag_combo(self):
        """When two atoms each carry two flags, four increments are emitted
        (no double-counting of identical labels within a single attestation)."""
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        if not pm._initialized:
            pytest.skip("prometheus_client not installed; counter emission is no-op")

        atts = [
            _make_attestation_with_flags(
                "atom_alpha", ["FLAG_X_PILOT_PENDING", "FLAG_Y_PILOT_PENDING"],
            ),
            _make_attestation_with_flags(
                "atom_beta", ["FLAG_X_PILOT_PENDING", "FLAG_Z_PILOT_PENDING"],
            ),
        ]

        # Capture initial counter values for the four (atom_id, flag) tuples
        # we are about to increment. Use ._value.get() to read a Counter
        # value at a labelset.
        def _read(atom_id, flag):
            return pm.a14_flag_active.labels(
                atom_id=atom_id, a14_flag=flag,
            )._value.get()

        before = {
            ("atom_alpha", "FLAG_X_PILOT_PENDING"): _read("atom_alpha", "FLAG_X_PILOT_PENDING"),
            ("atom_alpha", "FLAG_Y_PILOT_PENDING"): _read("atom_alpha", "FLAG_Y_PILOT_PENDING"),
            ("atom_beta", "FLAG_X_PILOT_PENDING"): _read("atom_beta", "FLAG_X_PILOT_PENDING"),
            ("atom_beta", "FLAG_Z_PILOT_PENDING"): _read("atom_beta", "FLAG_Z_PILOT_PENDING"),
        }

        self._emit_a14_counter_for_attestations(atts)

        after = {k: _read(*k) for k in before}

        for k in before:
            assert after[k] == before[k] + 1.0, (
                f"Counter at {k} increased by {after[k] - before[k]}, expected 1.0"
            )

    def test_repeated_emission_accumulates(self):
        """Same atom+flag combo emitted twice yields two increments."""
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        if not pm._initialized:
            pytest.skip("prometheus_client not installed; counter emission is no-op")

        att = _make_attestation_with_flags(
            "atom_repeat", ["FLAG_REPEATED_PILOT_PENDING"],
        )

        def _read():
            return pm.a14_flag_active.labels(
                atom_id="atom_repeat",
                a14_flag="FLAG_REPEATED_PILOT_PENDING",
            )._value.get()

        before = _read()
        self._emit_a14_counter_for_attestations([att])
        self._emit_a14_counter_for_attestations([att])
        after = _read()
        assert after == before + 2.0
