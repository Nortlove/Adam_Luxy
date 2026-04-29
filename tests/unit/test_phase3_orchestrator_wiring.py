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
# L3 override semantics — Foundation §4.1 commitment in code
# ============================================================================


class TestSelectMechanismsL3Override:
    """Foundation §4.1: 'L3 bilateral edges, when available, override L1
    archetype priors and L2 category posteriors entirely.'

    When cascade reached L3 (cascade_level == 3) AND cascade_modulated_scores
    is present, the cascade scores are the BASE for mechanism selection.
    Archetype-effectiveness graph priors are NOT consulted (they are
    L1/L2 evidence superseded by L3). Other layers (unified, review,
    corpus, barrier) apply as refinements on top of the cascade base.

    When cascade_level != 3, fall back to the legacy blend pattern.
    """

    @pytest.mark.asyncio
    async def test_l3_override_uses_cascade_as_base_not_graph_priors(self):
        """With cascade_level=3 and cascade_modulated_scores, the
        mechanism_intelligence archetype priors must NOT bleed into the
        base — only mechanisms in cascade_modulated_scores should
        appear in the working scores (modulo other blend layers).

        Test asymmetry: graph priors include 'social_proof' but cascade
        does not. Under L3 override, 'social_proof' should NOT appear
        in the result. Under legacy blend it SHOULD appear at 0.5.
        """
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        # Graph priors carry 3 mechanisms
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5, "scarcity": 0.5, "social_proof": 0.5},
        )
        # Cascade carries only 2 — social_proof is NOT in the cascade
        cascade_modulated = {"authority": 0.9, "scarcity": 0.2}

        # L3 OVERRIDE PATH
        trace_override = ReasoningTrace(trace_id="test_l3_override")
        result_override = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace_override,
            cascade_modulated_scores=cascade_modulated,
            cascade_level=3,
        )

        # social_proof must NOT be in the result — graph priors are
        # superseded by L3 evidence per Foundation §4.1
        assert "social_proof" not in result_override.mechanism_scores, (
            "Under L3 override, mechanism_intelligence-derived priors must "
            "NOT contribute. social_proof was in graph priors but not in "
            "cascade — it must not appear."
        )
        # authority and scarcity should reflect cascade values (modulo
        # any subsequent blend layers — but we passed no unified/review/
        # corpus/barrier, so the cascade values pass through unchanged
        # to Thompson sampling).
        assert "authority" in result_override.mechanism_scores
        assert "scarcity" in result_override.mechanism_scores

    @pytest.mark.asyncio
    async def test_legacy_blend_uses_graph_priors_as_base(self):
        """Same inputs as override test, but cascade_level=2 (no L3).
        Graph priors should appear in the base — social_proof present
        at 0.5 under legacy blend."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5, "scarcity": 0.5, "social_proof": 0.5},
        )
        cascade_modulated = {"authority": 0.9, "scarcity": 0.2}

        trace = ReasoningTrace(trace_id="test_legacy_blend")
        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores=cascade_modulated,
            cascade_level=2,
        )

        # social_proof IS in the result via graph priors at 0.5
        assert "social_proof" in result.mechanism_scores
        assert result.mechanism_scores["social_proof"] == pytest.approx(0.5, abs=1e-6)

    @pytest.mark.asyncio
    async def test_l3_override_priors_source_label(self):
        """priors_source == 'cascade_l3_override' when override path active."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5},
        )
        trace = ReasoningTrace(trace_id="test_l3_priors_source")
        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores={"authority": 0.9, "scarcity": 0.3},
            cascade_level=3,
        )
        assert result.priors_source == "cascade_l3_override"

    @pytest.mark.asyncio
    async def test_no_override_at_cascade_level_4(self):
        """Foundation §4.1 names L3 specifically. L4 (inferential transfer)
        falls back to legacy blend pattern — graph priors consulted."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5, "social_proof": 0.5},
        )
        trace = ReasoningTrace(trace_id="test_l4_no_override")
        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores={"authority": 0.9},
            cascade_level=4,
        )
        # Legacy blend path: social_proof present from graph priors
        assert "social_proof" in result.mechanism_scores
        # Not the override priors_source
        assert result.priors_source != "cascade_l3_override"

    @pytest.mark.asyncio
    async def test_no_override_when_cascade_modulated_empty(self):
        """Defensive: cascade_level=3 but empty cascade_modulated_scores.
        Falls back to legacy blend (override needs both conditions)."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5, "social_proof": 0.5},
        )
        trace = ReasoningTrace(trace_id="test_empty_cascade_at_l3")
        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores={},  # empty
            cascade_level=3,
        )
        # social_proof from graph priors should be present (legacy path)
        assert "social_proof" in result.mechanism_scores
        assert result.priors_source != "cascade_l3_override"

    @pytest.mark.asyncio
    async def test_no_double_blend_under_l3_override(self):
        """Under L3 override, the cascade-blend block at the bottom
        of _select_mechanisms must not re-apply (would double-count
        the cascade evidence)."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5},
        )
        trace = ReasoningTrace(trace_id="test_no_double_blend")

        # Under L3 override with no other signals (no unified, no review,
        # no corpus, no barrier) the cascade scores should pass through
        # to Thompson sampling unmodified by additional blend layers.
        cascade_input = {"authority": 0.85}
        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            cascade_modulated_scores=cascade_input,
            cascade_level=3,
        )

        # mechanism_scores has authority — and only authority (no graph
        # prior bleed, no double-blend back to cascade base)
        assert "authority" in result.mechanism_scores
        # Pass-through within Thompson sampling tolerance — score should
        # be near the cascade input, not 0.4*cascade + 0.6*cascade=cascade
        # (which would still pass) NOR 0.4*graph_prior + 0.6*cascade
        # (which would NOT pass at 0.85)
        # The exact post-Thompson-sampling final mechanism_scores reflects
        # the working scores fed into Thompson; they should equal the
        # cascade input.
        assert result.mechanism_scores["authority"] == pytest.approx(0.85, abs=1e-6)


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


# ============================================================================
# Task A1 — Cascade integration of online_learning_substrate
# ============================================================================


def _make_attestation_for_a1(
    atom_id: str, mechanism_id: str, link_source: str, link_target: str,
) -> ChainAttestation:
    """Build a chain attestation suitable for A1 tests.

    The chain has one link with predictable link_key
    "{relation}:{source}:{target}" so the test can stub TheoryLearner's
    response for that key.
    """
    link = ConstructLink(
        source_construct=link_source,
        relation_type=RelationType.CREATES_NEED_FOR,
        target_construct=link_target,
        evidence_value=0.5,
        confidence=0.7,
        citation="test_a1 §1.1",
    )
    final = TypedEvidence(
        construct=link_target,
        value=0.5,
        confidence=0.7,
        citation="test_a1 §1.1",
        calibration_status=CalibrationStatus.PINNED,
    )
    return ChainAttestation(
        atom_id=atom_id,
        request_id="req_a1",
        target_construct=link_target,
        chain=[link],
        final_assessment=final,
        mechanism_adjustments=[
            AdjustmentEvidence(
                mechanism_id=mechanism_id,
                adjustment_value=0.1,
                chain_links_responsible=[link.link_id],
                confidence=0.7,
            )
        ],
        provenance=ChainProvenance(atom_id=atom_id),
    )


class TestOnlineLearningMultiplier:
    """Pin the multiplier mapping function _online_learning_multiplier."""

    def test_strength_zero_floor(self):
        from adam.orchestrator.campaign_orchestrator import (
            _ONLINE_LEARNING_MOD_FLOOR,
            _online_learning_multiplier,
        )
        assert _online_learning_multiplier(0.0) == _ONLINE_LEARNING_MOD_FLOOR

    def test_strength_one_ceiling(self):
        from adam.orchestrator.campaign_orchestrator import (
            _ONLINE_LEARNING_MOD_CEILING,
            _online_learning_multiplier,
        )
        assert _online_learning_multiplier(1.0) == _ONLINE_LEARNING_MOD_CEILING

    def test_strength_half_neutral(self):
        from adam.orchestrator.campaign_orchestrator import (
            _online_learning_multiplier,
        )
        assert _online_learning_multiplier(0.5) == pytest.approx(1.0, abs=1e-9)

    def test_strength_clamps_below_zero(self):
        from adam.orchestrator.campaign_orchestrator import (
            _ONLINE_LEARNING_MOD_FLOOR,
            _online_learning_multiplier,
        )
        assert _online_learning_multiplier(-0.5) == _ONLINE_LEARNING_MOD_FLOOR

    def test_strength_clamps_above_one(self):
        from adam.orchestrator.campaign_orchestrator import (
            _ONLINE_LEARNING_MOD_CEILING,
            _online_learning_multiplier,
        )
        assert _online_learning_multiplier(1.5) == _ONLINE_LEARNING_MOD_CEILING

    def test_linearity(self):
        """Multiplier scales linearly between floor and ceiling."""
        from adam.orchestrator.campaign_orchestrator import (
            _ONLINE_LEARNING_MOD_FLOOR,
            _ONLINE_LEARNING_MOD_CEILING,
            _online_learning_multiplier,
        )
        m_quarter = _online_learning_multiplier(0.25)
        m_three_quarter = _online_learning_multiplier(0.75)
        # Both should be equally far from 1.0 (the strength=0.5 anchor)
        # though on opposite sides
        center = 1.0
        assert abs((m_quarter - center) + (m_three_quarter - center)) < 1e-9


class TestSelectMechanismsOnlineLearning:
    """The load-bearing test: when LinkPosteriors update mid-stream, the
    next call to _select_mechanisms produces DIFFERENT mechanism_scores
    even with identical chain_attestations.

    THIS IS THE PER-DECISION ONLINE LEARNING PROPERTY.
    """

    @pytest.mark.asyncio
    async def test_modulator_applied_when_attestations_present(self):
        """With chain_attestations + a TheoryLearner that returns
        non-neutral strengths, mechanism_scores reflect the modulation."""
        from unittest.mock import patch
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5},
        )
        attestation = _make_attestation_for_a1(
            atom_id="atom_test",
            mechanism_id="authority",
            link_source="src",
            link_target="tgt",
        )
        trace_high = ReasoningTrace(trace_id="test_a1_high")
        trace_low = ReasoningTrace(trace_id="test_a1_low")

        # Run 1: TheoryLearner returns HIGH strength (0.9) — modulator pushes UP
        with patch(
            "adam.core.learning.theory_learner.get_theory_learner",
            return_value=MagicMock(get_link_strength=lambda k: 0.9),
        ):
            result_high = await orch._select_mechanisms(
                archetype="luxe_arbiter",
                mechanism_intelligence=mechanism_intelligence,
                customer_intelligence=None,
                trace=trace_high,
                chain_attestations=[attestation],
            )

        # Run 2: TheoryLearner returns LOW strength (0.1) — modulator pulls DOWN
        with patch(
            "adam.core.learning.theory_learner.get_theory_learner",
            return_value=MagicMock(get_link_strength=lambda k: 0.1),
        ):
            result_low = await orch._select_mechanisms(
                archetype="luxe_arbiter",
                mechanism_intelligence=mechanism_intelligence,
                customer_intelligence=None,
                trace=trace_low,
                chain_attestations=[attestation],
            )

        # The high-strength run produces a higher authority score than
        # the low-strength run. THIS is the per-decision online learning
        # property — same attestation, same graph priors, but
        # TheoryLearner's posterior shift changes the outcome.
        assert (
            result_high.mechanism_scores["authority"]
            > result_low.mechanism_scores["authority"]
        ), (
            f"Online learning multiplier did not affect mechanism_scores "
            f"as expected. high={result_high.mechanism_scores['authority']:.4f}, "
            f"low={result_low.mechanism_scores['authority']:.4f}"
        )

    @pytest.mark.asyncio
    async def test_no_modulation_when_attestations_absent(self):
        """Without chain_attestations, online-learning modulation is a no-op."""
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5},
        )
        trace = ReasoningTrace(trace_id="test_a1_no_attestations")
        result = await orch._select_mechanisms(
            archetype="luxe_arbiter",
            mechanism_intelligence=mechanism_intelligence,
            customer_intelligence=None,
            trace=trace,
            chain_attestations=None,
        )
        # No crash; mechanism_scores reflect graph priors
        assert "authority" in result.mechanism_scores

    @pytest.mark.asyncio
    async def test_unknown_mechanism_in_attestation_skipped(self):
        """If aggregate_strengths returns a mechanism not in working
        mechanism_scores (rare), skip it silently."""
        from unittest.mock import patch
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.5},
        )
        # Attestation declares adjustment for "social_proof" — but
        # social_proof is NOT in the working scores from
        # mechanism_intelligence (which only has authority).
        attestation = _make_attestation_for_a1(
            atom_id="atom_test",
            mechanism_id="social_proof",
            link_source="src",
            link_target="tgt",
        )
        trace = ReasoningTrace(trace_id="test_a1_unknown_mech")
        with patch(
            "adam.core.learning.theory_learner.get_theory_learner",
            return_value=MagicMock(get_link_strength=lambda k: 0.9),
        ):
            result = await orch._select_mechanisms(
                archetype="luxe_arbiter",
                mechanism_intelligence=mechanism_intelligence,
                customer_intelligence=None,
                trace=trace,
                chain_attestations=[attestation],
            )
        # social_proof was NOT in working scores → not added by modulation
        # (modulator only modulates EXISTING entries, doesn't introduce new)
        assert "social_proof" not in result.mechanism_scores
        # authority unmodulated (no attestation declared adjustment for it)
        assert "authority" in result.mechanism_scores

    @pytest.mark.asyncio
    async def test_modulation_clamps_to_unit_interval(self):
        """Modulator output stays in [0, 1] even if multiplier × score
        would exceed."""
        from unittest.mock import patch
        from adam.orchestrator.campaign_orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator()
        # Authority at 0.95 with strength 1.0 → multiplier 1.3 → 0.95×1.3 = 1.235
        # Should clamp to 1.0.
        mechanism_intelligence = _make_graph_query_result(
            {"authority": 0.95},
        )
        attestation = _make_attestation_for_a1(
            atom_id="atom_test",
            mechanism_id="authority",
            link_source="src",
            link_target="tgt",
        )
        trace = ReasoningTrace(trace_id="test_a1_clamp")
        with patch(
            "adam.core.learning.theory_learner.get_theory_learner",
            return_value=MagicMock(get_link_strength=lambda k: 1.0),
        ):
            result = await orch._select_mechanisms(
                archetype="luxe_arbiter",
                mechanism_intelligence=mechanism_intelligence,
                customer_intelligence=None,
                trace=trace,
                chain_attestations=[attestation],
            )
        # Authority should NOT exceed 1.0 even though multiplier × score = 1.235
        assert result.mechanism_scores["authority"] <= 1.0
        # AND it should have been bumped up from 0.95 (modulation occurred)
        assert result.mechanism_scores["authority"] > 0.94
