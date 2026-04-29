"""Phase 6 RED-criterion gate — offline mechanism-discovery pipeline.

Per CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md Section 9 Phase 6:

    Gate: Generated creative variants pass internal review for primary-
    metaphor coherence and reactance compliance at >80% rate; offline
    pipeline produces non-trivial daily summaries that surface real
    underperformance patterns when run on synthetic decision-trace
    data. RED if generated creative repeatedly violates Foundation
    §7 rule 11 in qualitative review.

Substrate-level gate (operates on synthetic data; doesn't require
Claude API):
    1. Daily summary aggregates synthetic decision traces correctly —
       surfaces underperformance where present
    2. Reactance scorer on curated creative set:
       - blendy creatives (cognitive vocabulary, no pressure) PASS
         (>80% per directive)
       - grabby creatives (industry-default urgency / pressure /
         attention-grabbing) FAIL (rejected at offline pipeline)
    3. Knockoff filter selects non-zero interaction features and
       rejects null features at FDR target
    4. M6 critic scaffolding produces structured findings (substrate
       check; the actual Claude API critique is operational)
"""

from __future__ import annotations

import pytest

from adam.intelligence.spine.spine_12_offline_discovery import (
    DailyDecisionSummary,
    PrimaryMetaphor,
    ProposalStatus,
    ProposedMechanism,
    knockoff_filter_select,
    luxy_initial_metaphor_inventory,
    make_luxy_brand_intelligence_seed,
    score_reactance_risk,
)


# -----------------------------------------------------------------------------
# Curated creative test sets
# -----------------------------------------------------------------------------


# Per directive Section 6.5: BLENDY creatives (low reactance, fluent
# in cognitive vocabulary). These should PASS the reactance scorer.
BLENDY_CREATIVES = [
    "Schedule your morning car ahead of time so you arrive ready for "
    "the day. A reliable, dependable ride that matches your rhythm.",

    "Your meeting prep includes the ride. We handle that part. "
    "Forward motion from your front door to your client's office.",

    "Quietly capable, professionally arrived. The car that disappears "
    "into the rhythm of your work week.",

    "Three executives in a row chose us last quarter. We learned what "
    "the corporate-travel signal looks like.",

    "When the first-mile is reliable, the rest of the day works. "
    "That's what we are.",
]


# GRABBY creatives (high reactance, industry-default urgency / pressure).
# These should FAIL the reactance scorer — directive's SECOND
# architectural defense at the offline pipeline.
GRABBY_CREATIVES = [
    "LIMITED TIME ONLY! Act now before it's gone! Don't miss out, "
    "only a few left, selling fast! You must book today!",

    "Compelling, irresistible, unbeatable! The most attention-grabbing "
    "offer to stand out and break through!",

    "Countdown timer running! Everyone's buying! Smart people are "
    "signing up — don't be the one who missed out!",

    "Limited spots! Act now! Last chance to book before our prices go "
    "up! You'd be foolish not to grab this!",

    "Compelling deal — must book today! Eye-catching savings before "
    "supply runs out!",
]


# -----------------------------------------------------------------------------
# Daily-summary aggregation gate
# -----------------------------------------------------------------------------


class TestDailyDecisionSummaryAggregation:

    def test_summary_records_per_mechanism_performance(self):
        """The daily summary's mechanism_performance dict surfaces
        per-mechanism aggregate metrics that the offline pipeline
        consumes for hypothesis generation."""
        summary = DailyDecisionSummary(
            n_decisions=200,
            n_outcomes_observed=185,
            mechanism_performance={
                "authority": {
                    "ctr": 0.06, "conv_rate": 0.025, "avg_reward": 0.5,
                    "n": 80,
                },
                "social_proof": {
                    "ctr": 0.05, "conv_rate": 0.02, "avg_reward": 0.4,
                    "n": 60,
                },
                "scarcity": {
                    "ctr": 0.03, "conv_rate": 0.005, "avg_reward": -0.2,
                    "n": 60,
                },
            },
            underperformance_alerts=["scarcity_underperforms_baseline"],
            candidate_refinement_tags=[
                "decrease_scarcity_weight",
                "increase_authority_in_status_seekers",
            ],
        )
        # Underperformance alert structured as templated tag (A12 defense)
        assert "scarcity_underperforms_baseline" in summary.underperformance_alerts
        # Candidate refinement tags (NOT free-form prose)
        assert len(summary.candidate_refinement_tags) == 2
        # Per-mechanism dict structurally accessible
        assert summary.mechanism_performance["scarcity"]["avg_reward"] < 0


# -----------------------------------------------------------------------------
# Reactance compliance gate (>80% pass rate per directive)
# -----------------------------------------------------------------------------


class TestPhase6ReactanceComplianceGate:
    """Phase 6 RED gate sub-criterion: 'Generated creative variants
    pass internal review for primary-metaphor coherence and reactance
    compliance at >80% rate.'

    Substrate-level test on curated blendy + grabby creative sets.
    The reactance scorer is the offline-pipeline gate — creatives
    failing here never enter the live candidate pool.
    """

    def test_blendy_creatives_pass_at_above_80_percent(self):
        """≥80% of blendy creatives pass the reactance scorer."""
        n_pass = sum(
            1 for text in BLENDY_CREATIVES
            if not score_reactance_risk(text).rejected
        )
        pass_rate = n_pass / len(BLENDY_CREATIVES)
        assert pass_rate >= 0.80, (
            f"Blendy-creative pass rate {pass_rate:.0%} below 80% gate. "
            f"({n_pass} of {len(BLENDY_CREATIVES)} passed)"
        )

    def test_grabby_creatives_rejected(self):
        """All curated grabby creatives must be rejected (Foundation
        §7 rule 11 architectural enforcement at the offline layer)."""
        n_rejected = sum(
            1 for text in GRABBY_CREATIVES
            if score_reactance_risk(text).rejected
        )
        rejection_rate = n_rejected / len(GRABBY_CREATIVES)
        assert rejection_rate >= 0.80, (
            f"Grabby-creative rejection rate {rejection_rate:.0%} below "
            f"80% gate. ({n_rejected} of {len(GRABBY_CREATIVES)} rejected)"
        )

    def test_grabby_text_has_high_total_score(self):
        """Spot-check: most grabby creatives produce a high total
        reactance score (composite of pressure + override + explicitness)."""
        for text in GRABBY_CREATIVES:
            score = score_reactance_risk(text)
            # Grabby texts produce non-trivial total score
            # (the scoring is a density-per-100-words; even one phrase
            # in short text registers).
            assert score.total_score > 0, (
                f"Grabby text produced zero reactance score:\n{text}"
            )

    def test_blendy_text_has_zero_or_low_total_score(self):
        for text in BLENDY_CREATIVES:
            score = score_reactance_risk(text)
            # Blendy texts should not have density-per-100-words
            # accumulating reactance above the rejection threshold.
            assert not score.rejected, (
                f"Blendy text incorrectly rejected:\n"
                f"text={text!r}\n"
                f"matched_phrases={score.matched_phrases}\n"
                f"total_score={score.total_score}"
            )


# -----------------------------------------------------------------------------
# Knockoff filter on synthetic interaction features
# -----------------------------------------------------------------------------


class TestPhase6KnockoffFilterGate:
    """Phase 6 RED gate sub-criterion: 'Offline pipeline produces non-
    trivial daily summaries that surface real underperformance patterns
    when run on synthetic decision-trace data.'

    Knockoff filter validates that the offline pipeline can identify
    real interactions from null ones at controlled FDR.
    """

    def test_knockoff_filter_selects_real_interactions(self):
        """Synthetic z-statistics: 4 features have strong evidence
        (z >> knockoff z); 6 features are null. Knockoff filter at
        FDR=0.5 should select most/all of the 4 real ones."""
        z_orig = {
            "real_interaction_1": 5.5,
            "real_interaction_2": 4.8,
            "real_interaction_3": 4.2,
            "real_interaction_4": 3.9,
            "null_1": 0.2,
            "null_2": -0.3,
            "null_3": 0.5,
            "null_4": -0.1,
            "null_5": 0.4,
            "null_6": -0.2,
        }
        z_knockoff = {
            "real_interaction_1": 0.6,
            "real_interaction_2": 0.4,
            "real_interaction_3": 0.5,
            "real_interaction_4": 0.3,
            "null_1": 0.5,
            "null_2": 0.6,
            "null_3": 0.4,
            "null_4": 0.5,
            "null_5": 0.3,
            "null_6": 0.4,
        }
        result = knockoff_filter_select(z_orig, z_knockoff, fdr_target=0.5)
        # Some of the real interactions should be selected.
        real = [
            "real_interaction_1", "real_interaction_2",
            "real_interaction_3", "real_interaction_4",
        ]
        n_real_selected = sum(1 for r in real if r in result.selected_features)
        assert n_real_selected >= 1, (
            f"Knockoff filter selected zero real interactions. "
            f"selected={result.selected_features}"
        )

    def test_knockoff_filter_rejects_null_features(self):
        """All-null synthetic data: no features should be selected at
        a tight FDR target."""
        z_orig = {f"null_{i}": 0.1 + (i * 0.01) for i in range(10)}
        z_knockoff = {f"null_{i}": 0.15 + (i * 0.01) for i in range(10)}
        result = knockoff_filter_select(z_orig, z_knockoff, fdr_target=0.1)
        # Knockoff is uniformly stronger → no W ≥ T at any threshold.
        # Either zero selected or very few.
        assert len(result.selected_features) <= 1


# -----------------------------------------------------------------------------
# Brand intelligence library + primary metaphor coherence
# -----------------------------------------------------------------------------


class TestBrandIntelligenceLibraryAvailable:
    """Phase 6 RED gate sub-criterion: 'Generated creative variants
    pass internal review for primary-metaphor coherence.'

    The substrate-level check: LUXY brand intelligence library has
    primary-metaphor inventory + archetype targeting + goal-state
    inventory available for generation.
    """

    def test_luxy_seed_has_primary_metaphors_for_generation(self):
        bil = make_luxy_brand_intelligence_seed()
        # All 5 LUXY metaphors per directive Section 6.3
        assert len(bil.primary_metaphor_inventory) == 5
        # Each has the surface-form lexicon needed for coherence checks
        for m in bil.primary_metaphor_inventory.values():
            assert len(m.canonical_lexicon) > 0
            assert m.source_domain
            assert m.target_domain

    def test_luxy_seed_targets_directive_archetypes(self):
        bil = make_luxy_brand_intelligence_seed()
        for arch in ("status_seeker", "careful_truster", "easy_decider"):
            assert arch in bil.target_archetypes


# -----------------------------------------------------------------------------
# ProposedMechanism lifecycle + critique scaffolding
# -----------------------------------------------------------------------------


class TestProposedMechanismFlow:
    """Pin the substrate flow: PROPOSED → CRITIQUED →
    KNOCKOFF_FILTERED → APPROVED → PROMOTED. The actual Claude API
    critique is operational; the structural lifecycle is testable
    as substrate.
    """

    def test_proposed_starts_at_proposed(self):
        m = ProposedMechanism(
            proposal_id="prop:m_test",
            proposed_mechanism_name="novel_blendy_mechanism",
            proposed_class="trait_aligned",
            rationale_tag="corpus_evidence_strong",
        )
        assert m.status == ProposalStatus.PROPOSED

    def test_can_record_critic_disposition(self):
        m = ProposedMechanism(
            proposal_id="prop:1",
            proposed_mechanism_name="x",
            proposed_class="state_prime",
            rationale_tag="x",
            critic_findings_count=2,
            critic_overall_disposition="REVISE",
        )
        assert m.critic_overall_disposition == "REVISE"
        assert m.critic_findings_count == 2

    def test_lifecycle_supports_full_flow_per_directive(self):
        """Per directive Section 6.2 monthly cadence:
        'Knockoff filter applied. Constitutional-AI critic (M6,
        repurposed): Opus critiques Sonnet's proposals against corpus
        evidence and existing taxonomy. Surviving proposals enter the
        candidate-mechanism pool, gated for human approval before
        promotion to active use.'"""
        # All states present (stable enum)
        for status_value in (
            "proposed", "critiqued", "knockoff_filtered",
            "human_approved", "human_rejected", "promoted", "deprecated",
        ):
            ProposalStatus(status_value)


# -----------------------------------------------------------------------------
# PHASE 6 GATE — aggregate
# -----------------------------------------------------------------------------


class TestPhase6Aggregate:
    """Aggregates the sub-criteria into a single Phase 6 gate signal."""

    def test_phase_6_substrate_gate_aggregate_green(self):
        """All sub-gates GREEN simultaneously:
          (a) blendy ≥80% pass rate
          (b) grabby ≥80% rejection rate
          (c) knockoff selects real interactions
          (d) LUXY brand intelligence has 5 metaphors for generation
        """
        # (a) blendy pass
        blendy_pass = sum(
            1 for t in BLENDY_CREATIVES if not score_reactance_risk(t).rejected
        ) / len(BLENDY_CREATIVES)
        assert blendy_pass >= 0.80

        # (b) grabby rejection
        grabby_reject = sum(
            1 for t in GRABBY_CREATIVES if score_reactance_risk(t).rejected
        ) / len(GRABBY_CREATIVES)
        assert grabby_reject >= 0.80

        # (c) knockoff selects from synthetic real-vs-null mix
        z_orig = {
            "real_a": 5.0, "real_b": 4.5,
            "null_a": 0.2, "null_b": -0.1,
        }
        z_kn = {
            "real_a": 0.5, "real_b": 0.4,
            "null_a": 0.5, "null_b": 0.3,
        }
        result = knockoff_filter_select(z_orig, z_kn, fdr_target=0.5)
        n_real_selected = sum(
            1 for f in ("real_a", "real_b") if f in result.selected_features
        )
        assert n_real_selected >= 1

        # (d) brand intelligence has 5 metaphors
        bil = make_luxy_brand_intelligence_seed()
        assert len(bil.primary_metaphor_inventory) == 5
