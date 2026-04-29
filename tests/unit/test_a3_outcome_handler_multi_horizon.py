# =============================================================================
# ADAM A3 — Outcome Handler Multi-Horizon Cohort Registration Tests
# Location: tests/unit/test_a3_outcome_handler_multi_horizon.py
# =============================================================================

"""Tests for task A3 — wiring multi_horizon_adjudication.register_conversion
into OutcomeHandler.process_outcome."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from adam.intelligence.multi_horizon_adjudication import (
    MultiHorizonAdjudicator,
    reset_multi_horizon_adjudicator,
)


class TestA3OutcomeHandlerMultiHorizon:

    @pytest.mark.asyncio
    async def test_conversion_registers_cohort(self):
        """Conversion outcome creates a ConversionCohort in the
        adjudicator with correct fields."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_multi_horizon_adjudicator()
        try:
            test_adj = MultiHorizonAdjudicator()
            with patch(
                "adam.intelligence.multi_horizon_adjudication.get_multi_horizon_adjudicator",
                return_value=test_adj,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a3_test_1",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={
                        "buyer_id": "user:luxy_001",
                        "treatment_arm": "bilateral",
                        "archetype": "careful_truster",
                        "mechanism_sent": "automatic_evaluation",
                    },
                )
            cohort = test_adj.get_cohort("dec_a3_test_1")
            assert cohort is not None
            assert cohort.decision_id == "dec_a3_test_1"
            assert cohort.user_id == "user:luxy_001"
            assert cohort.treatment_arm == "bilateral"
            assert cohort.archetype == "careful_truster"
        finally:
            reset_multi_horizon_adjudicator()

    @pytest.mark.asyncio
    async def test_skip_outcome_does_not_create_cohort(self):
        """Skip outcomes are not eligible for return-visit tracking."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_multi_horizon_adjudicator()
        try:
            test_adj = MultiHorizonAdjudicator()
            with patch(
                "adam.intelligence.multi_horizon_adjudication.get_multi_horizon_adjudicator",
                return_value=test_adj,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a3_skip",
                    outcome_type="skip",
                    outcome_value=0.0,
                    metadata={"mechanism_sent": "automatic_evaluation"},
                )
            assert test_adj.get_cohort("dec_a3_skip") is None
        finally:
            reset_multi_horizon_adjudicator()

    @pytest.mark.asyncio
    async def test_refund_outcome_does_not_create_cohort(self):
        """Refunds are not eligible — they cancel a prior conversion;
        the cohort was already registered when the conversion fired."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_multi_horizon_adjudicator()
        try:
            test_adj = MultiHorizonAdjudicator()
            with patch(
                "adam.intelligence.multi_horizon_adjudication.get_multi_horizon_adjudicator",
                return_value=test_adj,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a3_refund",
                    outcome_type="refund",
                    outcome_value=0.0,
                    metadata={"mechanism_sent": "automatic_evaluation"},
                )
            assert test_adj.get_cohort("dec_a3_refund") is None
        finally:
            reset_multi_horizon_adjudicator()

    @pytest.mark.asyncio
    async def test_default_treatment_arm_when_absent(self):
        """Without treatment_arm in metadata, defaults to 'bilateral'."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_multi_horizon_adjudicator()
        try:
            test_adj = MultiHorizonAdjudicator()
            with patch(
                "adam.intelligence.multi_horizon_adjudication.get_multi_horizon_adjudicator",
                return_value=test_adj,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a3_default_arm",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={
                        "buyer_id": "user:1",
                        "mechanism_sent": "automatic_evaluation",
                        # treatment_arm intentionally absent
                    },
                )
            cohort = test_adj.get_cohort("dec_a3_default_arm")
            assert cohort is not None
            assert cohort.treatment_arm == "bilateral"
        finally:
            reset_multi_horizon_adjudicator()

    @pytest.mark.asyncio
    async def test_user_id_optional(self):
        """Cohort registration works without user_id (return-visit
        tracking won't fire for that cohort but registration succeeds)."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_multi_horizon_adjudicator()
        try:
            test_adj = MultiHorizonAdjudicator()
            with patch(
                "adam.intelligence.multi_horizon_adjudication.get_multi_horizon_adjudicator",
                return_value=test_adj,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a3_no_user",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={"mechanism_sent": "automatic_evaluation"},
                )
            cohort = test_adj.get_cohort("dec_a3_no_user")
            assert cohort is not None
            assert cohort.user_id is None
        finally:
            reset_multi_horizon_adjudicator()

    @pytest.mark.asyncio
    async def test_conversion_stream_populates_adjudicator(self):
        """30+ conversions across both arms → adjudicator's
        compute_horizon_return_rates produces per-arm cells."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_multi_horizon_adjudicator()
        try:
            test_adj = MultiHorizonAdjudicator()
            with patch(
                "adam.intelligence.multi_horizon_adjudication.get_multi_horizon_adjudicator",
                return_value=test_adj,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                # Register 30 conversions per arm
                for i in range(30):
                    for arm in ("bilateral", "control"):
                        await handler.process_outcome(
                            decision_id=f"dec_a3_stream_{arm}_{i}",
                            outcome_type="conversion",
                            outcome_value=1.0,
                            metadata={
                                "buyer_id": f"user:{arm}_{i}",
                                "treatment_arm": arm,
                                "mechanism_sent": "automatic_evaluation",
                            },
                        )

            assert len(test_adj.all_cohorts()) == 60
            # Verify treatment_arm distribution
            bilateral_count = sum(
                1 for c in test_adj.all_cohorts()
                if c.treatment_arm == "bilateral"
            )
            control_count = sum(
                1 for c in test_adj.all_cohorts()
                if c.treatment_arm == "control"
            )
            assert bilateral_count == 30
            assert control_count == 30
        finally:
            reset_multi_horizon_adjudicator()
