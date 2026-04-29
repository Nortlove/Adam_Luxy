"""Tests for Spine #12 — Offline Mechanism-Discovery Pipeline.

Pins per directive Section 6 + Section 8.1 (M6 repurposed):
    1. PipelineCadence enum has all 4 cadences
    2. DailyDecisionSummary structures performance + alerts as
       templated tags (A12 defense)
    3. Knockoff-filter FDR control: selects high-W features; rejects
       null-effect features; controls FDR
    4. PrimaryMetaphor + LUXY initial inventory matches directive §6.3
    5. ReactanceRiskScore: pressure phrases + override phrases +
       explicitness phrases counted; high-reactance creative rejected
    6. ProposedMechanism lifecycle: PROPOSED → CRITIQUED → KNOCKOFF_FILTERED
       → APPROVED → PROMOTED
    7. BrandIntelligenceLibrary: LUXY seed has primary metaphors +
       archetype inventory + goal-state inventory per directive
"""

from __future__ import annotations

import pytest

from adam.intelligence.spine.spine_12_offline_discovery import (
    LUXY_INITIAL_PRIMARY_METAPHORS,
    BrandIntelligenceLibrary,
    DailyDecisionSummary,
    KnockoffSelection,
    PipelineCadence,
    PrimaryMetaphor,
    ProposalStatus,
    ProposedMechanism,
    REACTANCE_EXPLICITNESS_PHRASES,
    REACTANCE_OVERRIDE_PHRASES,
    REACTANCE_PRESSURE_PHRASES,
    ReactanceRiskScore,
    knockoff_filter_select,
    luxy_initial_metaphor_inventory,
    make_luxy_brand_intelligence_seed,
    score_reactance_risk,
)


# -----------------------------------------------------------------------------
# Pipeline cadences
# -----------------------------------------------------------------------------


class TestPipelineCadences:

    def test_four_cadences_per_directive(self):
        expected = {"daily", "weekly", "monthly", "quarterly"}
        actual = {c.value for c in PipelineCadence}
        assert actual == expected


# -----------------------------------------------------------------------------
# DailyDecisionSummary
# -----------------------------------------------------------------------------


class TestDailyDecisionSummary:

    def test_minimal_construction(self):
        s = DailyDecisionSummary(
            n_decisions=100, n_outcomes_observed=85,
        )
        assert s.n_decisions == 100
        assert s.candidate_refinement_tags == []

    def test_structured_performance_dict(self):
        s = DailyDecisionSummary(
            n_decisions=100, n_outcomes_observed=85,
            mechanism_performance={
                "authority": {"ctr": 0.05, "conv_rate": 0.02, "n": 50},
            },
            cohort_mechanism_performance={
                "status_seeker": {
                    "authority": {"ctr": 0.06, "n": 30},
                },
            },
        )
        assert s.mechanism_performance["authority"]["ctr"] == 0.05
        assert (
            s.cohort_mechanism_performance["status_seeker"]["authority"]["n"] == 30
        )


# -----------------------------------------------------------------------------
# Knockoff-filter FDR control
# -----------------------------------------------------------------------------


class TestKnockoffFilterSelect:

    def test_no_features_returns_empty(self):
        result = knockoff_filter_select({}, {}, fdr_target=0.1)
        assert result.selected_features == []
        assert result.n_features_considered == 0

    def test_features_with_high_evidence_selected(self):
        """Features with z-stat much higher than knockoff z-stat get
        selected."""
        z_orig = {
            "feat_a": 5.0,    # strong evidence
            "feat_b": 4.5,    # strong
            "feat_c": 0.3,    # weak / null
            "feat_d": 0.1,    # null
        }
        z_knockoff = {
            "feat_a": 0.5,    # knockoff much weaker
            "feat_b": 0.3,
            "feat_c": 0.4,    # similar to original
            "feat_d": 0.2,
        }
        result = knockoff_filter_select(z_orig, z_knockoff, fdr_target=0.5)
        # The genuinely strong features should be selected.
        assert "feat_a" in result.selected_features
        # Null features should not be.
        assert "feat_c" not in result.selected_features
        assert "feat_d" not in result.selected_features

    def test_invalid_fdr_target_rejected(self):
        with pytest.raises(ValueError, match="fdr_target"):
            knockoff_filter_select({"a": 1.0}, {"a": 0.5}, fdr_target=1.5)

    def test_mismatched_keys_rejected(self):
        with pytest.raises(ValueError, match="same set of keys"):
            knockoff_filter_select(
                {"a": 1.0}, {"a": 0.5, "b": 0.5},
            )

    def test_fdr_target_in_result(self):
        z_orig = {"a": 5.0}
        z_knockoff = {"a": 0.5}
        result = knockoff_filter_select(z_orig, z_knockoff, fdr_target=0.1)
        assert result.fdr_target == 0.1


# -----------------------------------------------------------------------------
# Primary metaphor inventory (LUXY initial)
# -----------------------------------------------------------------------------


class TestLUXYPrimaryMetaphorInventory:

    def test_directive_specifies_five_metaphors(self):
        """Per directive Section 6.3: 'For LUXY: encode CONTAINMENT/
        CONTROL, RELIABILITY-AS-WEIGHT, FORWARD-MOTION/PROGRESS,
        STATUS-AS-VERTICALITY, TIME-AS-RESOURCE.'"""
        assert len(LUXY_INITIAL_PRIMARY_METAPHORS) == 5
        names = {m.name for m in LUXY_INITIAL_PRIMARY_METAPHORS}
        assert names == {
            "containment_control", "reliability_as_weight",
            "forward_motion_progress", "status_as_verticality",
            "time_as_resource",
        }

    def test_each_metaphor_has_source_and_target(self):
        for m in LUXY_INITIAL_PRIMARY_METAPHORS:
            assert m.source_domain
            assert m.target_domain

    def test_each_metaphor_has_canonical_lexicon(self):
        for m in LUXY_INITIAL_PRIMARY_METAPHORS:
            assert len(m.canonical_lexicon) > 0

    def test_inventory_dict_keyed_by_name(self):
        inv = luxy_initial_metaphor_inventory()
        assert "containment_control" in inv
        assert inv["containment_control"].source_domain == "physical_containment"


# -----------------------------------------------------------------------------
# Reactance-risk scorer (per directive §6.5)
# -----------------------------------------------------------------------------


class TestReactanceRiskScore:

    def test_clean_creative_low_score(self):
        text = (
            "Schedule your morning car ahead of time so you arrive ready "
            "for the day. A reliable, dependable ride that matches your "
            "rhythm."
        )
        score = score_reactance_risk(text)
        assert score.total_score == pytest.approx(0.0, abs=0.01)
        assert score.rejected is False

    def test_pressure_creative_flagged(self):
        text = (
            "Limited time only — act now! Don't miss out, only a few left, "
            "selling fast! You must book today before it's gone!"
        )
        score = score_reactance_risk(text)
        assert score.pressure_density > 0
        assert score.total_score > 0

    def test_override_phrases_increase_score(self):
        text = "Countdown timer says everyone's buying right now — smart people are signing up."
        score = score_reactance_risk(text)
        assert score.override_density > 0

    def test_explicitness_phrases_increase_score(self):
        text = "Compelling, irresistible, unbeatable — the most attention-grabbing eye-catching offer to stand out and break through."
        score = score_reactance_risk(text)
        assert score.explicitness_density > 0

    def test_high_total_score_triggers_rejection(self):
        text = (
            "Limited time! Act now! Compelling, irresistible offer "
            "everyone's buying. Don't miss out — countdown timer running."
        )
        score = score_reactance_risk(text, rejection_threshold=0.001)
        assert score.rejected is True

    def test_matched_phrases_recorded(self):
        text = "Limited time only! Act now and save."
        score = score_reactance_risk(text)
        assert "limited time" in score.matched_phrases
        assert "act now" in score.matched_phrases


# -----------------------------------------------------------------------------
# ProposedMechanism lifecycle
# -----------------------------------------------------------------------------


class TestProposedMechanism:

    def test_default_status_proposed(self):
        m = ProposedMechanism(
            proposal_id="prop:1",
            proposed_mechanism_name="novel_mechanism",
            proposed_class="state_prime",
            rationale_tag="corpus_evidence_strong",
        )
        assert m.status == ProposalStatus.PROPOSED

    def test_lifecycle_states_present(self):
        states = {s.value for s in ProposalStatus}
        assert "proposed" in states
        assert "critiqued" in states
        assert "knockoff_filtered" in states
        assert "human_approved" in states
        assert "promoted" in states
        assert "deprecated" in states

    def test_critic_disposition_optional(self):
        m = ProposedMechanism(
            proposal_id="prop:2",
            proposed_mechanism_name="another_mechanism",
            proposed_class="construal_shift",
            rationale_tag="x",
        )
        # Default None
        assert m.critic_overall_disposition is None


# -----------------------------------------------------------------------------
# BrandIntelligenceLibrary + LUXY seed
# -----------------------------------------------------------------------------


class TestBrandIntelligenceLibraryLuxySeed:

    def test_seed_has_brand_identity(self):
        bil = make_luxy_brand_intelligence_seed()
        assert bil.brand_id == "luxy"
        assert bil.brand_name == "LUXY"

    def test_seed_has_five_primary_metaphors_per_directive(self):
        bil = make_luxy_brand_intelligence_seed()
        assert len(bil.primary_metaphor_inventory) == 5

    def test_seed_archetypes_match_directive(self):
        """Per directive Section 6.3: target_archetypes status_seeker,
        careful_truster, easy_decider; suppress skeptical_analyst,
        disillusioned."""
        bil = make_luxy_brand_intelligence_seed()
        assert "status_seeker" in bil.target_archetypes
        assert "careful_truster" in bil.target_archetypes
        assert "easy_decider" in bil.target_archetypes
        assert "skeptical_analyst" in bil.suppress_archetypes
        assert "disillusioned" in bil.suppress_archetypes

    def test_seed_has_goal_state_inventory(self):
        bil = make_luxy_brand_intelligence_seed()
        assert "commute_readiness" in bil.goal_state_inventory
        assert "expense_management" in bil.goal_state_inventory
        assert "professional_encounter_prep" in bil.goal_state_inventory
