# =============================================================================
# ADAM A2 — Outcome Handler Mechanism-Taxonomy Tagging Tests
# Location: tests/unit/test_a2_outcome_handler_taxonomy.py
# =============================================================================

"""Tests for task A2 — wiring mechanism_taxonomy_runtime.tag_decision +
TaxonomyConditionalAccumulator.record_outcome into OutcomeHandler.process_outcome.

Per Section 0.5 self-check: tests pin the load-bearing claim that
outcomes flow through the taxonomy accumulator at outcome time so
Foundation §2 attention-inversion data starts populating.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.mechanism_taxonomy import MechanismRouteCategory
from adam.intelligence.mechanism_taxonomy_runtime import (
    TaxonomyConditionalAccumulator,
    reset_taxonomy_accumulator,
    tag_decision,
)


def _patch_outcome_handler_dependencies(taxonomy_acc):
    """Patch the heavy outcome-handler dependencies so we can exercise
    the taxonomy-tagging block without spinning up Neo4j / Redis."""
    return patch.multiple(
        "adam.core.learning.outcome_handler",
        # Replace the singleton accessor so the OutcomeHandler uses our
        # test accumulator
    )


# ============================================================================
# A2 — outcome handler tags + records to accumulator
# ============================================================================


class TestA2OutcomeHandlerTaxonomyTagging:

    @pytest.mark.asyncio
    async def test_known_mechanism_records_to_accumulator(self):
        """Conversion outcome on a known mechanism → accumulator
        records (category, page_posture, converted=True, backfired=False).
        """
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_taxonomy_accumulator()
        try:
            test_acc = TaxonomyConditionalAccumulator()

            # Patch get_taxonomy_accumulator to return our test instance
            with patch(
                "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
                return_value=test_acc,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                # Run process_outcome for a synthetic conversion event.
                # Most downstream consumers will fail (no Neo4j etc.) but
                # we just need the taxonomy-tagging block to execute.
                # The block is non-fatal; failures elsewhere don't crash.
                await handler.process_outcome(
                    decision_id="dec_a2_test_1",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={
                        "mechanism_sent": "automatic_evaluation",
                        "page_attentional_posture": "blend_compatible",
                        "decision_context_found": True,
                    },
                )

            # Verify the accumulator received the outcome
            cell = test_acc.get_cell(
                MechanismRouteCategory.BLEND_COMPATIBLE,
                "blend_compatible",
            )
            assert cell.n_decisions == 1
            assert cell.n_conversions == 1
            assert cell.n_backfires == 0
        finally:
            reset_taxonomy_accumulator()

    @pytest.mark.asyncio
    async def test_refund_outcome_marks_backfire(self):
        """Refund outcome on a known mechanism → accumulator records
        backfired=True via is_negative_ethics_signal."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_taxonomy_accumulator()
        try:
            test_acc = TaxonomyConditionalAccumulator()

            with patch(
                "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
                return_value=test_acc,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a2_test_refund",
                    outcome_type="refund",
                    outcome_value=0.0,
                    metadata={
                        "mechanism_sent": "automatic_evaluation",
                        "page_attentional_posture": "blend_compatible",
                    },
                )

            cell = test_acc.get_cell(
                MechanismRouteCategory.BLEND_COMPATIBLE,
                "blend_compatible",
            )
            assert cell.n_decisions == 1
            assert cell.n_backfires == 1
            assert cell.n_conversions == 0
        finally:
            reset_taxonomy_accumulator()

    @pytest.mark.asyncio
    async def test_unknown_mechanism_skipped_silently(self):
        """Mechanism not in canonical taxonomy → tag_decision returns
        was_known=False, accumulator silently skips per substrate
        design."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_taxonomy_accumulator()
        try:
            test_acc = TaxonomyConditionalAccumulator()

            with patch(
                "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
                return_value=test_acc,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a2_test_unknown",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={
                        "mechanism_sent": "totally_made_up_mechanism",
                        "page_attentional_posture": "blend_compatible",
                    },
                )

            # No cells should have been created
            assert len(test_acc.all_cells()) == 0
        finally:
            reset_taxonomy_accumulator()

    @pytest.mark.asyncio
    async def test_no_mechanism_sent_skipped(self):
        """metadata without mechanism_sent → block records 'skipped'
        marker, no crash."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_taxonomy_accumulator()
        try:
            test_acc = TaxonomyConditionalAccumulator()

            with patch(
                "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
                return_value=test_acc,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a2_test_no_mech",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={
                        "page_attentional_posture": "blend_compatible",
                        # mechanism_sent intentionally absent
                    },
                )
            # No cells created; no crash
            assert len(test_acc.all_cells()) == 0
        finally:
            reset_taxonomy_accumulator()

    @pytest.mark.asyncio
    async def test_no_page_posture_still_records(self):
        """Without page_attentional_posture in metadata (A4 not yet
        wired), the accumulator still records the cell — page_posture
        defaults to None, cell excluded from matched/mismatched diagonals
        but accumulates volume."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_taxonomy_accumulator()
        try:
            test_acc = TaxonomyConditionalAccumulator()

            with patch(
                "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
                return_value=test_acc,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                await handler.process_outcome(
                    decision_id="dec_a2_test_no_posture",
                    outcome_type="conversion",
                    outcome_value=1.0,
                    metadata={
                        "mechanism_sent": "automatic_evaluation",
                        # page_attentional_posture intentionally absent
                    },
                )

            # Cell exists with page_posture=None
            cell = test_acc.get_cell(
                MechanismRouteCategory.BLEND_COMPATIBLE, None,
            )
            assert cell.n_decisions == 1
            # Diagonal partition excludes None-posture cells
            matched, mismatched = test_acc.matched_vs_mismatched_diagonals()
            assert cell not in matched
            assert cell not in mismatched
        finally:
            reset_taxonomy_accumulator()

    @pytest.mark.asyncio
    async def test_foundation_2_diagonal_populates_when_both_sides_present(self):
        """Stream of synthetic decisions × known mechanisms × known
        page postures → matched/mismatched diagonals populate as
        expected. THIS is the Foundation §2 attention-inversion test
        substrate firing end-to-end."""
        from adam.core.learning.outcome_handler import OutcomeHandler

        reset_taxonomy_accumulator()
        try:
            test_acc = TaxonomyConditionalAccumulator()

            with patch(
                "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
                return_value=test_acc,
            ):
                handler = OutcomeHandler.__new__(OutcomeHandler)
                handler._outcomes_processed = 0
                handler._total_updates = 0

                # 60 decisions: 30 matched (BLEND mech × blend page),
                # 30 mismatched (BLEND mech × vigilance page)
                for i in range(30):
                    await handler.process_outcome(
                        decision_id=f"dec_matched_{i}",
                        outcome_type="conversion",
                        outcome_value=1.0,
                        metadata={
                            "mechanism_sent": "automatic_evaluation",
                            "page_attentional_posture": "blend_compatible",
                        },
                    )
                for i in range(30):
                    await handler.process_outcome(
                        decision_id=f"dec_mismatched_{i}",
                        outcome_type="conversion",
                        outcome_value=1.0,
                        metadata={
                            "mechanism_sent": "automatic_evaluation",
                            "page_attentional_posture": "vigilance_activating",
                        },
                    )

            # Diagonal partition fires
            matched, mismatched = test_acc.matched_vs_mismatched_diagonals()
            assert len(matched) >= 1
            assert len(mismatched) >= 1
            matched_cell = next(
                c for c in matched
                if c.mechanism_category == MechanismRouteCategory.BLEND_COMPATIBLE
            )
            mismatched_cell = next(
                c for c in mismatched
                if c.mechanism_category == MechanismRouteCategory.BLEND_COMPATIBLE
            )
            assert matched_cell.n_decisions == 30
            assert mismatched_cell.n_decisions == 30
        finally:
            reset_taxonomy_accumulator()
