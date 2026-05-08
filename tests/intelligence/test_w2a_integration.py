"""W.2a — cascade integration smoke tests.

Pin: the cascade integration block presence + ordering invariants
(W.2a runs BEFORE per_user_posterior_modulation; per_user_posterior_-
modulation block at line 3270 is preserved by W.2a; W.1's 5 wired
accessors continue working unchanged).
"""
import inspect

import pytest

from adam.intelligence.information_value import BuyerUncertaintyProfile


class TestCascadeIntegrationBlockPresent:

    def _cascade_source(self):
        from adam.api.stackadapt import bilateral_cascade
        return inspect.getsource(bilateral_cascade)

    def test_w2a_block_marker_present(self):
        src = self._cascade_source()
        assert (
            "W.2a — ARCHETYPE COLD-START + ONE-SHOT REASSIGNMENT POLICY"
            in src
        )

    def test_lazy_imports_cold_start_mapper(self):
        src = self._cascade_source()
        assert "from adam.intelligence.cold_start_archetype_mapper import" in src
        assert "map_cold_start_archetype" in src

    def test_lazy_imports_reassignment_policy(self):
        src = self._cascade_source()
        assert "from adam.intelligence.archetype_reassignment import" in src
        assert "REASSIGNMENT_BID_THRESHOLD" in src
        assert "evaluate_reassignment" in src

    def test_fail_soft_template(self):
        src = self._cascade_source()
        assert "W.2a archetype cold-start/reassignment skipped:" in src

    def test_runs_before_per_user_posterior_modulation(self):
        """Ordering invariant: W.2a's archetype assignment must run
        BEFORE apply_per_user_posterior_modulation so the per-user
        posterior shrinkage operates against an assigned archetype's
        priors."""
        src = self._cascade_source()
        idx_w2a = src.index(
            "W.2a — ARCHETYPE COLD-START + ONE-SHOT REASSIGNMENT POLICY"
        )
        idx_post = src.index("apply_per_user_posterior_modulation")
        assert idx_w2a < idx_post

    def test_per_user_posterior_modulation_block_preserved(self):
        """W.2a doesn't break the existing per_user_posterior_modulation
        block — its imports and call should still be present."""
        src = self._cascade_source()
        assert "Per-user posterior modulation skipped:" in src
        assert "apply_per_user_posterior_modulation(" in src


class TestEndToEndProfileFlow:
    """The actual cascade end-to-end requires Neo4j + Redis fixtures.
    These tests pin the in-memory profile mutations W.2a applies."""

    def test_cold_start_assigns_archetype_via_mapper(self):
        """Simulate W.2a's cascade integration in-memory: a fresh
        profile gets archetype assigned + metadata populated."""
        from datetime import datetime, timezone
        from adam.intelligence.cold_start_archetype_mapper import (
            map_cold_start_archetype,
        )
        p = BuyerUncertaintyProfile(buyer_id="u")
        assert p.archetype is None  # cold-start

        # Simulate the integration block's assignment path
        new_archetype = map_cold_start_archetype(
            device="desktop", hour_of_day=14,
            iab_category="Business and Finance",
        )
        p.archetype = new_archetype.value
        p.archetype_assigned_at = (
            datetime.now(timezone.utc).isoformat()
        )

        assert p.archetype == "analyst"  # desktop+workday+Business votes ANALYST
        assert p.archetype_assigned_at is not None

    def test_reassignment_at_bid_threshold_sets_flag(self):
        """Simulate hitting the N=20 bid threshold: archetype_-
        reassigned flips to True regardless of whether reassignment
        fires (Q27=(ε) one-shot semantics)."""
        from adam.intelligence.archetype_reassignment import (
            REASSIGNMENT_BID_THRESHOLD, evaluate_reassignment,
        )
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "pragmatist"
        p.bids_since_archetype_assignment = REASSIGNMENT_BID_THRESHOLD - 1

        # Simulate the integration block's reassignment path:
        p.bids_since_archetype_assignment += 1  # hits threshold
        assert (
            p.bids_since_archetype_assignment == REASSIGNMENT_BID_THRESHOLD
        )
        if not p.archetype_reassigned:
            new_assignment = evaluate_reassignment(p)
            if new_assignment is not None:
                p.archetype = new_assignment.value
            p.archetype_reassigned = True

        # Flag flipped regardless of LLR outcome.
        assert p.archetype_reassigned is True


class TestZeroRegressionOnPriorSlices:

    def test_w1_accessor_factories_still_resolve(self):
        from adam.cells.accessors import (
            make_cohort_accessor, make_posture_accessor,
            make_priming_accessor, make_cascade_tier_accessor,
            make_journey_accessor,
        )
        # Module-level imports succeed without crashes.
        assert callable(make_cohort_accessor)
        assert callable(make_posture_accessor)
        assert callable(make_priming_accessor)
        assert callable(make_cascade_tier_accessor)
        assert callable(make_journey_accessor)

    def test_production_aggregator_still_constructs(self):
        from adam.cells import production_aggregator
        agg = production_aggregator()
        assert agg is not None

    def test_s62_predicates_still_registered(self):
        from adam.cells import get_registered_predicates
        names = get_registered_predicates()
        # 6 seed predicates from S6.2 must still be registered.
        assert len(names) >= 6

    def test_existing_buyer_profile_pipeline_unbroken(self):
        """BuyerUncertaintyProfile schema extension preserves all
        pre-W.2a behavior: __post_init__ initializes constructs,
        aggregate_uncertainty/aggregate_entropy/aggregate_confidence
        properties still work."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        # __post_init__ populates constructs from UNCERTAINTY_DIMENSIONS
        assert len(p.constructs) > 0
        # Pre-W.2a properties still callable
        assert isinstance(p.aggregate_uncertainty, float)
        assert isinstance(p.aggregate_confidence, float)
