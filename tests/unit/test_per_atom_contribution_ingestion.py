# =============================================================================
# ADAM Per-Atom Contribution Ingestion Tests
# Location: tests/unit/test_per_atom_contribution_ingestion.py
# =============================================================================

"""
PRODUCER TESTS — B3-LUXY Phase 3 deliverable 3 (data ingestion path)

Pins the producer that feeds AtomDecisionRecords from cached chain
attestations into PerAtomContributionTracker. Without this producer, the
§6 generalization decision tree returns "insufficient_data" forever.

Coverage:
  - Cache load failures / empty / no-attestation cases produce 0 records.
  - Records are added per attesting atom with correct outcome fields.
  - Backfire-signal mapping covers refund / complaint / regret / churn /
    ad_fatigue / negative_review per outcome_types.is_negative_ethics_signal.
  - mechanism_followed resolved from metadata (mechanism_sent first,
    mechanisms_applied[0] fallback).
  - Rehydrate failures don't break processing (logged & skipped).
"""

from __future__ import annotations

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
from adam.intelligence.per_atom_contribution import (
    PerAtomContributionTracker,
    reset_per_atom_contribution_tracker,
)
from adam.intelligence.per_atom_contribution_ingestion import (
    record_outcome_to_contribution_tracker,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_attestation_dict(atom_id: str, mechanism_id: str = "authority",
                            adjustment_value: float = -0.2) -> dict:
    """Build a serialised ChainAttestation dict (the cached payload shape)."""
    chain = [
        ConstructLink(
            source_construct=f"src_{atom_id}",
            relation_type=RelationType.MODULATED_BY,
            target_construct=f"tgt_{atom_id}",
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
            mechanism_id=mechanism_id,
            adjustment_value=adjustment_value,
            chain_links_responsible=chain_link_ids,
            confidence=0.7,
        )
    ]
    attestation = ChainAttestation(
        atom_id=atom_id,
        request_id="req_test",
        target_construct=f"construct_{atom_id}",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adj_evidence,
        provenance=ChainProvenance(atom_id=atom_id),
    )
    # Serialise to a dict (the cached payload shape — what
    # _execute_real_atom_dag writes via to_dict() and ChainAttestation
    # re-hydrates via ChainAttestation(**attestation_dict))
    return attestation.model_dump()


def _make_cached_payload(atoms: dict[str, dict | None]) -> dict:
    """Build a cached payload dict — keys are atom_ids, values are atom_data
    dicts that may carry a chain_attestation field."""
    payload = {}
    for atom_id, attestation_dict in atoms.items():
        payload[atom_id] = {
            "primary_output": {},
            "secondary_assessments": {},
            "confidence": 0.7,
            "reasoning": "",
            "chain_attestation": attestation_dict,
        }
    return payload


def _patch_container_with_cache(cached_payload):
    """Build a patched get_container that returns a mock Redis with the
    given cached payload."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cached_payload)
    mock_container_obj = MagicMock()
    mock_container_obj.redis_cache = mock_redis
    return patch(
        "adam.core.container.get_container",
        new=AsyncMock(return_value=mock_container_obj),
    )


# ============================================================================
# Cache loading edge cases
# ============================================================================


class TestProducerCacheEdgeCases:
    """The producer must be safe when the cache is missing or unhelpful."""

    @pytest.mark.asyncio
    async def test_no_redis_returns_zero(self):
        mock_container_obj = MagicMock()
        mock_container_obj.redis_cache = None
        with patch(
            "adam.core.container.get_container",
            new=AsyncMock(return_value=mock_container_obj),
        ):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d1",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={},
                tracker=tracker,
            )
            assert n == 0
            assert tracker.n_decisions_total == 0

    @pytest.mark.asyncio
    async def test_empty_cache_returns_zero(self):
        with _patch_container_with_cache(None):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d1",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={},
                tracker=tracker,
            )
            assert n == 0

    @pytest.mark.asyncio
    async def test_cache_without_attestations_returns_zero(self):
        """When all atoms in the cache are unchanged wrappers (no
        chain_attestation field), no records are added."""
        cached = _make_cached_payload({
            "atom_wrapper_1": None,  # field absent / None
            "atom_wrapper_2": None,
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d1",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={},
                tracker=tracker,
            )
            assert n == 0


# ============================================================================
# Records-added contract
# ============================================================================


class TestProducerRecordsAdded:
    """The producer adds one record per attesting atom with correct fields."""

    @pytest.mark.asyncio
    async def test_one_attesting_atom_yields_one_record(self):
        cached = _make_cached_payload({
            "atom_autonomy_reactance": _make_attestation_dict(
                "atom_autonomy_reactance",
                mechanism_id="scarcity",
                adjustment_value=-0.2,
            ),
            "atom_wrapper": None,  # unchanged wrapper, ignored
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d1",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={"mechanism_sent": "authority"},
                tracker=tracker,
            )
            assert n == 1
            assert tracker.n_decisions_total == 1
            records = tracker._records_by_atom["atom_autonomy_reactance"]
            assert len(records) == 1
            r = records[0]
            assert r.decision_id == "d1"
            assert r.atom_id == "atom_autonomy_reactance"
            assert r.outcome_value == 1.0
            assert r.success is True
            assert r.backfire_signal is False  # conversion is positive
            assert r.mechanism_followed == "authority"

    @pytest.mark.asyncio
    async def test_multiple_attesting_atoms(self):
        cached = _make_cached_payload({
            "atom_autonomy_reactance": _make_attestation_dict(
                "atom_autonomy_reactance"
            ),
            "atom_strategic_awareness": _make_attestation_dict(
                "atom_strategic_awareness"
            ),
            "atom_wrapper": None,
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d2",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={"mechanism_sent": "social_proof"},
                tracker=tracker,
            )
            assert n == 2
            assert set(tracker.atom_ids_observed) == {
                "atom_autonomy_reactance",
                "atom_strategic_awareness",
            }


# ============================================================================
# Backfire-signal mapping
# ============================================================================


class TestProducerBackfireMapping:
    """Foundation §7 rule 11: ethics-signal outcomes map to backfire_signal."""

    @pytest.mark.parametrize(
        "outcome_type,expected_backfire",
        [
            ("conversion", False),
            ("click", False),
            ("engagement", False),
            ("skip", False),  # neutral, not backfire
            ("bounce", False),
            ("refund", True),
            ("complaint", True),
            ("regret_signal", True),
            ("churn_30d", True),
            ("ad_fatigue", True),
            ("negative_review", True),
        ],
    )
    @pytest.mark.asyncio
    async def test_ethics_signal_outcomes_set_backfire_signal(
        self, outcome_type, expected_backfire
    ):
        cached = _make_cached_payload({
            "atom_autonomy_reactance": _make_attestation_dict(
                "atom_autonomy_reactance"
            ),
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d_ethics",
                outcome_type=outcome_type,
                outcome_value=1.0 if expected_backfire is False else 0.0,
                success=outcome_type in ("conversion", "click", "engagement"),
                metadata={"mechanism_sent": "authority"},
                tracker=tracker,
            )
            assert n == 1
            r = tracker._records_by_atom["atom_autonomy_reactance"][0]
            assert r.backfire_signal is expected_backfire


# ============================================================================
# mechanism_followed resolution
# ============================================================================


class TestProducerMechanismResolution:
    """mechanism_followed comes from metadata; mechanism_sent is canonical."""

    @pytest.mark.asyncio
    async def test_mechanism_sent_is_primary(self):
        cached = _make_cached_payload({
            "atom_autonomy_reactance": _make_attestation_dict(
                "atom_autonomy_reactance"
            ),
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            await record_outcome_to_contribution_tracker(
                decision_id="d3",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={
                    "mechanism_sent": "authority",
                    "mechanisms_applied": ["scarcity"],  # ignored
                },
                tracker=tracker,
            )
            r = tracker._records_by_atom["atom_autonomy_reactance"][0]
            assert r.mechanism_followed == "authority"

    @pytest.mark.asyncio
    async def test_mechanisms_applied_fallback(self):
        cached = _make_cached_payload({
            "atom_autonomy_reactance": _make_attestation_dict(
                "atom_autonomy_reactance"
            ),
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            await record_outcome_to_contribution_tracker(
                decision_id="d4",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={"mechanisms_applied": ["scarcity"]},
                tracker=tracker,
            )
            r = tracker._records_by_atom["atom_autonomy_reactance"][0]
            assert r.mechanism_followed == "scarcity"

    @pytest.mark.asyncio
    async def test_no_mechanism_in_metadata_yields_none(self):
        cached = _make_cached_payload({
            "atom_autonomy_reactance": _make_attestation_dict(
                "atom_autonomy_reactance"
            ),
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            await record_outcome_to_contribution_tracker(
                decision_id="d5",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={},
                tracker=tracker,
            )
            r = tracker._records_by_atom["atom_autonomy_reactance"][0]
            assert r.mechanism_followed is None


# ============================================================================
# Rehydrate failures
# ============================================================================


class TestProducerRehydrateRobustness:
    """Schema drift in cached attestations must not break ingestion."""

    @pytest.mark.asyncio
    async def test_corrupt_attestation_skipped_others_processed(self):
        cached = _make_cached_payload({
            "atom_good": _make_attestation_dict("atom_good"),
            "atom_corrupt": {"this_is_not": "a_valid_chain_attestation"},
        })
        with _patch_container_with_cache(cached):
            tracker = PerAtomContributionTracker()
            n = await record_outcome_to_contribution_tracker(
                decision_id="d6",
                outcome_type="conversion",
                outcome_value=1.0,
                success=True,
                metadata={"mechanism_sent": "authority"},
                tracker=tracker,
            )
            assert n == 1  # good processed, corrupt skipped
            assert "atom_good" in tracker.atom_ids_observed
            assert "atom_corrupt" not in tracker.atom_ids_observed


# ============================================================================
# Singleton accessor
# ============================================================================


class TestProducerSingleton:
    """The default-tracker path uses the global singleton."""

    @pytest.mark.asyncio
    async def test_global_tracker_used_when_none_passed(self):
        from adam.intelligence.per_atom_contribution import (
            get_per_atom_contribution_tracker,
        )

        reset_per_atom_contribution_tracker()
        try:
            cached = _make_cached_payload({
                "atom_autonomy_reactance": _make_attestation_dict(
                    "atom_autonomy_reactance"
                ),
            })
            with _patch_container_with_cache(cached):
                n = await record_outcome_to_contribution_tracker(
                    decision_id="d_global",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    success=True,
                    metadata={"mechanism_sent": "authority"},
                )
                assert n == 1
                # The global tracker should have one record now
                assert get_per_atom_contribution_tracker().n_decisions_total == 1
        finally:
            reset_per_atom_contribution_tracker()
