# =============================================================================
# ADAM Phase 3 deliverable 2 — Outcome → TheoryLearner routing tests
# Location: tests/unit/test_phase3_outcome_routing.py
# =============================================================================

"""
OUTCOME-ROUTING TESTS — B3-LUXY Phase 3 deliverable 2

Pins the path: outcome arrives → cached atom_outputs read from Redis →
chain_attestations extracted → TheoryLearner.process_chain_outcome
called per attestation → per-link LinkPosteriors updated.

This is the load-bearing path for closing the learning loop on the 9
redone atoms' chain attestations. Without this, atom-level theory
updates would only happen for `mechanism_activation`'s legacy
inferential_chains.
"""

from unittest.mock import AsyncMock, MagicMock, patch

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


# =============================================================================
# CHAIN-ATTESTATION SERIALIZATION ROUND-TRIP (CACHE COMPATIBILITY)
# =============================================================================


def _make_attestation(
    atom_id: str,
    adjustments: list[tuple[str, float]],
    a14_flags: list[str] = None,
) -> ChainAttestation:
    """Build a ChainAttestation for tests."""
    chain = [
        ConstructLink(
            source_construct="src",
            relation_type=RelationType.MODULATED_BY,
            target_construct=f"target_{atom_id}",
            evidence_value=0.5,
            confidence=0.7,
            citation="test_citation 1.0",
            calibration_status=CalibrationStatus.PINNED,
        )
    ]
    final = TypedEvidence(
        construct=f"construct_{atom_id}",
        value=0.5,
        confidence=0.7,
        citation="test_citation 1.0",
        calibration_status=CalibrationStatus.PINNED,
    )
    provenance = ChainProvenance(
        atom_id=atom_id,
        a14_flags_active=a14_flags or [],
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
        provenance=provenance,
    )


class TestChainAttestationCacheRoundTrip:
    """Pin: ChainAttestation survives JSON-dict serialization (Redis cache
    write/read cycle)."""

    def test_pydantic_dump_then_rehydrate_preserves_chain(self):
        """ChainAttestation → model_dump(mode=json) → ChainAttestation
        round-trips cleanly."""
        original = _make_attestation(
            "atom_autonomy_reactance",
            [("scarcity", -0.2), ("authority", 0.1)],
            a14_flags=["REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING"],
        )
        dumped = original.model_dump(mode="json")
        rehydrated = ChainAttestation(**dumped)

        assert rehydrated.atom_id == original.atom_id
        assert len(rehydrated.chain) == len(original.chain)
        assert rehydrated.theoretical_link_keys == original.theoretical_link_keys
        assert len(rehydrated.mechanism_adjustments) == len(original.mechanism_adjustments)
        assert (
            rehydrated.provenance.a14_flags_active
            == original.provenance.a14_flags_active
        )

    def test_atom_output_to_dict_includes_chain_attestation(self):
        """AtomOutput.to_dict() must preserve the chain_attestation field
        (load-bearing for orchestrator → Redis cache)."""
        from adam.atoms.models.atom_io import AtomOutput
        from adam.atoms.models.evidence import FusionResult
        from adam.blackboard.models.zone2_reasoning import AtomType

        attestation = _make_attestation("atom_test", [("scarcity", -0.1)])
        fusion = FusionResult(
            construct="test_construct",
            assessment="test",
            confidence=0.7,
        )
        output = AtomOutput(
            atom_id="atom_test",
            atom_type=AtomType.AUTONOMY_REACTANCE,
            request_id="req_test",
            fusion_result=fusion,
            chain_attestation=attestation,
        )

        # to_dict() should include chain_attestation
        d = output.to_dict()
        assert "chain_attestation" in d
        assert d["chain_attestation"] is not None
        assert d["chain_attestation"]["atom_id"] == "atom_test"

    def test_atom_output_to_dict_chain_attestation_none_for_wrappers(self):
        """Wrapper atoms (no chain_attestation field set) should serialize None."""
        from adam.atoms.models.atom_io import AtomOutput
        from adam.atoms.models.evidence import FusionResult
        from adam.blackboard.models.zone2_reasoning import AtomType

        fusion = FusionResult(
            construct="test_construct",
            assessment="test",
            confidence=0.7,
        )
        output = AtomOutput(
            atom_id="atom_wrapper",
            atom_type=AtomType.CUSTOM,
            request_id="req_test",
            fusion_result=fusion,
            # chain_attestation defaults to None
        )

        d = output.to_dict()
        assert d.get("chain_attestation") is None


# =============================================================================
# OUTCOME-HANDLER → THEORY-LEARNER ROUTING
# =============================================================================


class TestOutcomeHandlerChainAttestationRouting:
    """Pin OutcomeHandler._process_chain_attestations behavior."""

    @pytest.mark.asyncio
    async def test_no_cache_returns_empty(self):
        """No Redis cache → empty results list (no error)."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)  # bypass __init__

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = None
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=MagicMock(),
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )
        assert results == []

    @pytest.mark.asyncio
    async def test_empty_cache_returns_empty(self):
        """Empty cache returns empty results."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=MagicMock(),
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )
        assert results == []

    @pytest.mark.asyncio
    async def test_cache_with_no_attestations_returns_empty(self):
        """Atoms cached but none have chain_attestation field → empty."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            return_value={
                "atom_wrapper_1": {"primary_assessment": "x", "chain_attestation": None},
                "atom_wrapper_2": {"primary_assessment": "y"},  # field missing
            }
        )

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=MagicMock(),
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )
        assert results == []

    @pytest.mark.asyncio
    async def test_routes_single_attestation_to_theory_learner(self):
        """One redone atom's chain_attestation → TheoryLearner.process_chain_outcome called."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)
        attestation = _make_attestation(
            "atom_autonomy_reactance", [("scarcity", -0.2)]
        )
        cache_payload = {
            "atom_autonomy_reactance": {
                "atom_id": "atom_autonomy_reactance",
                "chain_attestation": attestation.model_dump(mode="json"),
            }
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cache_payload)

        mock_learner = MagicMock()
        mock_learner.process_chain_outcome = MagicMock(
            return_value={"links_updated": 1}
        )

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=mock_learner,
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={"mechanisms_applied": ["scarcity"]},
            )

        # process_chain_outcome called once
        assert mock_learner.process_chain_outcome.call_count == 1
        call_kwargs = mock_learner.process_chain_outcome.call_args.kwargs
        assert call_kwargs["decision_id"] == "test_decision"
        assert call_kwargs["success"] is True
        # chain_data has the integration-contract keys
        chain_data = call_kwargs["chain_data"]
        assert "chain_id" in chain_data
        assert "theoretical_link_keys" in chain_data
        assert "recommended_mechanism" in chain_data
        assert chain_data["recommended_mechanism"] == "scarcity"

        assert len(results) == 1
        assert results[0]["atom_id"] == "atom_autonomy_reactance"

    @pytest.mark.asyncio
    async def test_routes_signed_reward_through_signed_path(self):
        """When signed_reward is non-None and non-zero, routes through
        process_chain_outcome_signed (Phase 1 ethics-gate path)."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)
        attestation = _make_attestation(
            "atom_autonomy_reactance", [("scarcity", -0.2)]
        )
        cache_payload = {
            "atom_autonomy_reactance": {
                "atom_id": "atom_autonomy_reactance",
                "chain_attestation": attestation.model_dump(mode="json"),
            }
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cache_payload)

        mock_learner = MagicMock()
        mock_learner.process_chain_outcome_signed = MagicMock(
            return_value={"links_updated": 1}
        )
        mock_learner.process_chain_outcome = MagicMock()  # should NOT be called

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=mock_learner,
                success=False,
                outcome_value=0.5,
                signed_reward=-3.0,  # ethics-gate refund
                processing_depth_weight=1.0,
                metadata={"mechanisms_applied": ["scarcity"]},
            )

        # signed variant called; legacy NOT
        assert mock_learner.process_chain_outcome_signed.call_count == 1
        assert mock_learner.process_chain_outcome.call_count == 0
        signed_kwargs = mock_learner.process_chain_outcome_signed.call_args.kwargs
        assert signed_kwargs["signed_reward"] == -3.0
        assert signed_kwargs["weight"] == 1.0

    @pytest.mark.asyncio
    async def test_processes_multiple_atoms_independently(self):
        """3 redone atoms → 3 TheoryLearner calls (one per atom)."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)
        att1 = _make_attestation("atom1", [("scarcity", -0.1)])
        att2 = _make_attestation("atom2", [("authority", 0.1)])
        att3 = _make_attestation("atom3", [("unity", 0.15)])

        cache_payload = {
            "atom1": {"chain_attestation": att1.model_dump(mode="json")},
            "atom2": {"chain_attestation": att2.model_dump(mode="json")},
            "atom3": {"chain_attestation": att3.model_dump(mode="json")},
            "atom_wrapper": {"chain_attestation": None},
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cache_payload)

        mock_learner = MagicMock()
        mock_learner.process_chain_outcome = MagicMock(
            return_value={"links_updated": 1}
        )

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=mock_learner,
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )

        assert mock_learner.process_chain_outcome.call_count == 3
        assert len(results) == 3
        atom_ids = {r["atom_id"] for r in results}
        assert atom_ids == {"atom1", "atom2", "atom3"}

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_block_other_atoms(self):
        """If TheoryLearner.process_chain_outcome raises for one atom,
        processing continues for the others."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)
        att_ok = _make_attestation("atom_ok", [("scarcity", -0.1)])
        att_bad = _make_attestation("atom_bad", [("authority", 0.1)])

        cache_payload = {
            "atom_ok": {"chain_attestation": att_ok.model_dump(mode="json")},
            "atom_bad": {"chain_attestation": att_bad.model_dump(mode="json")},
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cache_payload)

        def _selective_raise(*args, **kwargs):
            chain_data = kwargs.get("chain_data") or args[0]
            chain_id = chain_data.get("chain_id", "")
            if chain_id == att_bad.attestation_id:
                raise RuntimeError("simulated learner failure")
            return {"links_updated": 1}

        mock_learner = MagicMock()
        mock_learner.process_chain_outcome = MagicMock(side_effect=_selective_raise)

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=mock_learner,
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )

        # Both attempted, 1 succeeded
        assert mock_learner.process_chain_outcome.call_count == 2
        assert len(results) == 1
        assert results[0]["atom_id"] == "atom_ok"

    @pytest.mark.asyncio
    async def test_invalid_attestation_dict_skipped(self):
        """Malformed cached attestation → skipped, no crash."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)
        cache_payload = {
            "atom_corrupt": {
                "chain_attestation": {"this_is_not_a_valid_chain_attestation": True},
            },
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cache_payload)

        mock_learner = MagicMock()

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=mock_learner,
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )

        assert results == []
        assert mock_learner.process_chain_outcome.call_count == 0

    @pytest.mark.asyncio
    async def test_results_carry_a14_flags_for_segmentation(self):
        """Result entries include a14_flags_active so contribution
        measurement can segment by pinned-vs-pending later."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        handler = OutcomeHandler.__new__(OutcomeHandler)
        attestation = _make_attestation(
            "atom_autonomy_reactance",
            [("scarcity", -0.2)],
            a14_flags=[
                "REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING",
                "BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING",
            ],
        )
        cache_payload = {
            "atom_autonomy_reactance": {
                "chain_attestation": attestation.model_dump(mode="json"),
            }
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cache_payload)

        mock_learner = MagicMock()
        mock_learner.process_chain_outcome = MagicMock(
            return_value={"links_updated": 5}
        )

        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = mock_redis
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            results = await handler._process_chain_attestations(
                decision_id="test_decision",
                learner=mock_learner,
                success=True,
                outcome_value=1.0,
                signed_reward=None,
                processing_depth_weight=1.0,
                metadata={},
            )

        assert len(results) == 1
        assert "a14_flags_active" in results[0]
        flags = results[0]["a14_flags_active"]
        assert "REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING" in flags
        assert "BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING" in flags
