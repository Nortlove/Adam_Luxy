"""Tests for Spine #4 — Trilateral L3 Cascade with Hard Fluency Floor.

Pins per directive Section 4 (Spine #4) + Section 9 Phase 2 gate:
    1. Five posture classes match the directive verbatim
    2. PagePostureScore distribution sums to 1.0; entries in [0, 1]
    3. Compatibility matrix has expected qualitative entries
       (scarcity/urgency on TASK_COMPLETION = strongly negative;
       social_proof on SOCIAL_CONSUMPTION = positive; etc.)
    4. compute_fluency_score scales with posture_confidence
    5. check_fluency_floor returns False below the floor (HARD constraint)
    6. score_candidate composes user posterior + bilateral edge +
       posture compatibility + carryover correctly
    7. filter_by_fluency_floor splits eligible vs filtered
    8. PHASE 2 GATE: trilateral scoring is NOT posture-invariant —
       same (user, creative) pair across different postures produces
       qualitatively different scores
    9. PHASE 2 GATE: known-grabby pairings (urgency on social-consumption)
       fail the fluency floor
"""

from __future__ import annotations

import pytest

from adam.intelligence.spine.spine_4_trilateral_cascade import (
    DEFAULT_FLUENCY_FLOOR,
    POSTURE_CLASSES_ORDERED,
    POSTURE_MECHANISM_COMPATIBILITY,
    PageAttentionalPosture,
    PagePostureScore,
    TrilateralScore,
    check_fluency_floor,
    compute_fluency_score,
    filter_by_fluency_floor,
    get_posture_mechanism_compatibility,
    score_candidate,
)


# -----------------------------------------------------------------------------
# Posture taxonomy
# -----------------------------------------------------------------------------


class TestPostureTaxonomy:

    def test_five_classes_per_directive(self):
        expected = {
            "information_foraging", "task_completion", "leisure_browsing",
            "social_consumption", "transactional_comparison",
        }
        actual = {p.value for p in PageAttentionalPosture}
        assert actual == expected

    def test_ordered_tuple_has_five_classes(self):
        assert len(POSTURE_CLASSES_ORDERED) == 5
        # Stable order matters for posture_distribution vector indexing.
        assert POSTURE_CLASSES_ORDERED[0] == PageAttentionalPosture.INFORMATION_FORAGING
        assert POSTURE_CLASSES_ORDERED[-1] == PageAttentionalPosture.TRANSACTIONAL_COMPARISON


# -----------------------------------------------------------------------------
# PagePostureScore validation
# -----------------------------------------------------------------------------


class TestPagePostureScore:

    def _valid_distribution(self):
        return [0.6, 0.2, 0.1, 0.05, 0.05]

    def test_valid_construction(self):
        s = PagePostureScore(
            page_url="https://example.com/blog/post",
            posture_distribution=self._valid_distribution(),
            posture_confidence=0.85,
            argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
        )
        assert s.posture_confidence == 0.85
        assert s.argmax_posture == PageAttentionalPosture.INFORMATION_FORAGING

    def test_distribution_must_sum_to_one(self):
        with pytest.raises(ValueError, match="sum to ~1"):
            PagePostureScore(
                page_url="x",
                posture_distribution=[0.4, 0.2, 0.1, 0.05, 0.05],  # sums to 0.8
                posture_confidence=0.5,
                argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
            )

    def test_distribution_wrong_length_rejected(self):
        with pytest.raises(ValueError, match="length"):
            PagePostureScore(
                page_url="x",
                posture_distribution=[0.5, 0.5],
                posture_confidence=0.5,
                argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
            )

    def test_distribution_entries_in_unit_interval(self):
        with pytest.raises(ValueError, match="in \\[0, 1\\]"):
            PagePostureScore(
                page_url="x",
                posture_distribution=[1.5, -0.5, 0.0, 0.0, 0.0],
                posture_confidence=0.5,
                argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
            )

    def test_confidence_in_unit_interval(self):
        with pytest.raises(ValueError, match="posture_confidence"):
            PagePostureScore(
                page_url="x",
                posture_distribution=self._valid_distribution(),
                posture_confidence=1.5,
                argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
            )

    def test_valence_in_signed_unit_interval(self):
        with pytest.raises(ValueError, match="emotional_valence"):
            PagePostureScore(
                page_url="x",
                posture_distribution=self._valid_distribution(),
                posture_confidence=0.5,
                argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
                emotional_valence=2.0,
            )

    def test_valid_negative_valence(self):
        # Valence is signed; negative is valid.
        s = PagePostureScore(
            page_url="x",
            posture_distribution=self._valid_distribution(),
            posture_confidence=0.5,
            argmax_posture=PageAttentionalPosture.INFORMATION_FORAGING,
            emotional_valence=-0.6,
        )
        assert s.emotional_valence == -0.6


# -----------------------------------------------------------------------------
# Posture × mechanism compatibility matrix
# -----------------------------------------------------------------------------


class TestCompatibilityMatrix:

    def test_scarcity_on_task_completion_strongly_negative(self):
        """Per directive: WANTING_LIKING / scarcity × TASK_COMPLETION
        on expense management ≈ -0.5 (hedonic appeal fights utilitarian
        task)."""
        c = get_posture_mechanism_compatibility(
            PageAttentionalPosture.TASK_COMPLETION, "scarcity",
        )
        assert c < -0.5

    def test_urgency_on_social_consumption_strongly_negative(self):
        """SOCIAL_CONSUMPTION × urgency: high reactance risk per
        directive (the user is fatigued from feed-grabbing)."""
        c = get_posture_mechanism_compatibility(
            PageAttentionalPosture.SOCIAL_CONSUMPTION, "urgency",
        )
        assert c < -0.5

    def test_social_proof_on_social_consumption_positive(self):
        """social_proof natural fit for SOCIAL_CONSUMPTION."""
        c = get_posture_mechanism_compatibility(
            PageAttentionalPosture.SOCIAL_CONSUMPTION, "social_proof",
        )
        assert c > 0

    def test_construal_concrete_on_information_foraging_positive(self):
        """Per directive: CONSTRUAL_LEVEL_CONCRETE × INFORMATION_FORAGING
        on a comparison page ≈ +0.7."""
        c = get_posture_mechanism_compatibility(
            PageAttentionalPosture.INFORMATION_FORAGING, "construal_concrete",
        )
        assert c >= 0.6

    def test_reliability_on_task_completion_strongly_positive(self):
        """RELIABILITY-AS-WEIGHT metaphor on TASK_COMPLETION (productivity
        / booking flow): strong fit for LUXY's primary metaphor + posture."""
        c = get_posture_mechanism_compatibility(
            PageAttentionalPosture.TASK_COMPLETION, "reliability_metaphor",
        )
        assert c > 0.5

    def test_unspecified_pair_returns_zero(self):
        c = get_posture_mechanism_compatibility(
            PageAttentionalPosture.INFORMATION_FORAGING,
            "totally_made_up_mechanism_xyz",
        )
        assert c == 0.0

    def test_compatibility_in_signed_unit_interval(self):
        """All matrix entries are in [-1, +1]."""
        for (posture, mech), score in POSTURE_MECHANISM_COMPATIBILITY.items():
            assert -1.0 <= score <= 1.0, (
                f"{posture.value} × {mech} = {score} out of [-1, +1]"
            )


# -----------------------------------------------------------------------------
# Fluency score + floor
# -----------------------------------------------------------------------------


class TestFluencyScore:

    def test_fluency_scales_with_confidence(self):
        f_high = compute_fluency_score(
            PageAttentionalPosture.TASK_COMPLETION, "scarcity",
            posture_confidence=1.0,
        )
        f_med = compute_fluency_score(
            PageAttentionalPosture.TASK_COMPLETION, "scarcity",
            posture_confidence=0.5,
        )
        f_low = compute_fluency_score(
            PageAttentionalPosture.TASK_COMPLETION, "scarcity",
            posture_confidence=0.0,
        )
        # Negative compatibility scaled by confidence: at conf=0, no effect.
        assert f_high < f_med < f_low
        assert f_low == 0.0

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="posture_confidence"):
            compute_fluency_score(
                PageAttentionalPosture.INFORMATION_FORAGING, "authority",
                posture_confidence=1.5,
            )


class TestFluencyFloor:

    def test_fluent_pair_passes(self):
        # construal_concrete on INFORMATION_FORAGING is +0.7 — fluent
        assert check_fluency_floor(
            PageAttentionalPosture.INFORMATION_FORAGING, "construal_concrete",
        ) is True

    def test_grabby_pair_fails(self):
        # urgency on SOCIAL_CONSUMPTION is -0.8 — well below default floor
        assert check_fluency_floor(
            PageAttentionalPosture.SOCIAL_CONSUMPTION, "urgency",
        ) is False

    def test_borderline_pair_with_low_confidence_passes(self):
        """Even a moderately negative compatibility passes when posture
        confidence is low (no strong evidence the page IS social
        consumption, so attenuate the negative compatibility)."""
        # urgency on SOCIAL_CONSUMPTION = -0.8; at confidence 0.4 →
        # fluency = -0.32 — passes default floor of -0.4.
        assert check_fluency_floor(
            PageAttentionalPosture.SOCIAL_CONSUMPTION, "urgency",
            posture_confidence=0.4,
        ) is True

    def test_custom_floor_threshold(self):
        # Tighter floor: -0.1. urgency on TASK_COMPLETION = -0.7.
        # Default floor (-0.4) FAILS this; tight floor (-0.1) also fails.
        # Fluent pair (reliability_metaphor on TASK_COMPLETION = +0.7)
        # passes both.
        assert check_fluency_floor(
            PageAttentionalPosture.TASK_COMPLETION, "reliability_metaphor",
            floor=-0.1,
        ) is True
        assert check_fluency_floor(
            PageAttentionalPosture.TASK_COMPLETION, "urgency",
            floor=-0.1,
        ) is False


# -----------------------------------------------------------------------------
# Score candidate (trilateral scoring)
# -----------------------------------------------------------------------------


class TestScoreCandidate:

    def test_score_composes_components(self):
        score = score_candidate(
            user_id="u",
            mechanism="reliability_metaphor",
            posture=PageAttentionalPosture.TASK_COMPLETION,
            posture_confidence=1.0,
            user_posterior_mean_for_mechanism=0.5,
            bilateral_edge_score=0.3,
            carryover_correction=0.1,
        )
        # reliability_metaphor on TASK_COMPLETION = +0.7
        # base = 0.5 + 0.3 + 0.7 + 0.1 = 1.6
        assert score.score == pytest.approx(1.6)
        assert score.fluency_floor_passed is True
        assert score.components["user_posterior"] == 0.5
        assert score.components["bilateral_edge"] == 0.3
        assert score.components["posture_compatibility"] == pytest.approx(0.7)
        assert score.components["carryover"] == 0.1

    def test_grabby_pair_marked_floor_failed(self):
        score = score_candidate(
            user_id="u",
            mechanism="urgency",
            posture=PageAttentionalPosture.SOCIAL_CONSUMPTION,
            posture_confidence=1.0,
            user_posterior_mean_for_mechanism=2.0,  # high posterior — irrelevant
            bilateral_edge_score=2.0,
            carryover_correction=0.0,
        )
        # Even with great posterior + bilateral, fluency_floor_passed False
        assert score.fluency_floor_passed is False
        # Total score is still computed (caller can audit).
        assert score.score is not None

    def test_score_records_posture(self):
        score = score_candidate(
            user_id="u", mechanism="authority",
            posture=PageAttentionalPosture.INFORMATION_FORAGING,
        )
        assert score.posture == PageAttentionalPosture.INFORMATION_FORAGING


# -----------------------------------------------------------------------------
# Filter by fluency floor
# -----------------------------------------------------------------------------


class TestFilterByFluencyFloor:

    def test_split_eligible_and_filtered(self):
        scores = [
            score_candidate(  # eligible: reliability on TASK_COMPLETION = +0.7
                user_id="u", mechanism="reliability_metaphor",
                posture=PageAttentionalPosture.TASK_COMPLETION,
            ),
            score_candidate(  # filtered: urgency on SOCIAL_CONSUMPTION = -0.8
                user_id="u", mechanism="urgency",
                posture=PageAttentionalPosture.SOCIAL_CONSUMPTION,
            ),
        ]
        eligible, filtered = filter_by_fluency_floor(scores)
        assert len(eligible) == 1
        assert len(filtered) == 1
        assert eligible[0].mechanism == "reliability_metaphor"
        assert filtered[0].mechanism == "urgency"

    def test_custom_floor_changes_split(self):
        scores = [
            score_candidate(  # construal_concrete on TASK_COMPLETION = +0.6
                user_id="u", mechanism="construal_concrete",
                posture=PageAttentionalPosture.TASK_COMPLETION,
            ),
        ]
        # With strict floor 0.65, this is filtered.
        eligible_strict, filtered_strict = filter_by_fluency_floor(
            scores, floor=0.65,
        )
        assert len(eligible_strict) == 0
        assert len(filtered_strict) == 1
        # With permissive floor 0.0, this is eligible.
        eligible_perm, filtered_perm = filter_by_fluency_floor(
            scores, floor=0.0,
        )
        assert len(eligible_perm) == 1
        assert len(filtered_perm) == 0


# -----------------------------------------------------------------------------
# PHASE 2 GATE — trilateral scoring is NOT posture-invariant
# -----------------------------------------------------------------------------


class TestPhase2Gate:
    """Per directive Section 9 Phase 2 gate:
    'Trilateral cascade produces qualitatively different scores for the
    same (user, creative) pair across different posture classes (sanity
    check: scoring should not be posture-invariant).'

    This test class is the gate proof.
    """

    def test_same_user_same_mechanism_different_postures_different_scores(self):
        """Same user, same mechanism (scarcity), but different page
        postures must produce materially different scores."""
        common_args = dict(
            user_id="u",
            mechanism="scarcity",
            posture_confidence=1.0,
            user_posterior_mean_for_mechanism=0.5,
            bilateral_edge_score=0.3,
            carryover_correction=0.0,
        )
        score_research = score_candidate(
            posture=PageAttentionalPosture.INFORMATION_FORAGING, **common_args,
        )
        score_task = score_candidate(
            posture=PageAttentionalPosture.TASK_COMPLETION, **common_args,
        )
        score_social = score_candidate(
            posture=PageAttentionalPosture.SOCIAL_CONSUMPTION, **common_args,
        )
        score_compare = score_candidate(
            posture=PageAttentionalPosture.TRANSACTIONAL_COMPARISON, **common_args,
        )

        # Scarcity:
        #   on INFORMATION_FORAGING = -0.5 (fights research mode)
        #   on TASK_COMPLETION = -0.7 (fights goal completion)
        #   on SOCIAL_CONSUMPTION = -0.7 (high reactance)
        #   on TRANSACTIONAL_COMPARISON = 0.0 (neutral)
        # The scoring MUST differ across postures.
        scores = {
            "research": score_research.score,
            "task": score_task.score,
            "social": score_social.score,
            "compare": score_compare.score,
        }
        assert len(set(scores.values())) >= 3, (
            f"Scores too similar across postures (posture-invariant scoring "
            f"would be a Phase 2 gate failure): {scores}"
        )
        # And the TRANSACTIONAL_COMPARISON score should be HIGHER than
        # the TASK_COMPLETION score (since scarcity neutral on the former,
        # strongly negative on the latter).
        assert score_compare.score > score_task.score

    def test_grabby_creative_filtered_only_on_grabby_postures(self):
        """A grabby mechanism passes the fluency floor on a posture
        where it's compatible, but fails on incompatible postures.

        This is the architectural property the directive points to:
        'the scoring should not be posture-invariant.'"""
        # urgency: passes default floor on TRANSACTIONAL_COMPARISON
        # (-0.2 ≥ -0.4) but fails on SOCIAL_CONSUMPTION (-0.8 < -0.4).
        s_compare = score_candidate(
            user_id="u", mechanism="urgency",
            posture=PageAttentionalPosture.TRANSACTIONAL_COMPARISON,
        )
        s_social = score_candidate(
            user_id="u", mechanism="urgency",
            posture=PageAttentionalPosture.SOCIAL_CONSUMPTION,
        )
        assert s_compare.fluency_floor_passed is True
        assert s_social.fluency_floor_passed is False

    def test_known_grabby_pairings_fail_floor(self):
        """The substrate's prior compatibility matrix correctly
        identifies grabby pairings (high reactance risk) by failing
        them at the default fluency floor."""
        grabby_pairings = [
            (PageAttentionalPosture.TASK_COMPLETION, "scarcity"),       # -0.7
            (PageAttentionalPosture.TASK_COMPLETION, "urgency"),        # -0.7
            (PageAttentionalPosture.SOCIAL_CONSUMPTION, "scarcity"),    # -0.7
            (PageAttentionalPosture.SOCIAL_CONSUMPTION, "urgency"),     # -0.8
            (PageAttentionalPosture.INFORMATION_FORAGING, "urgency"),   # -0.6
            (PageAttentionalPosture.LEISURE_BROWSING, "urgency"),       # -0.5
        ]
        for posture, mechanism in grabby_pairings:
            assert check_fluency_floor(posture, mechanism) is False, (
                f"{mechanism} on {posture.value} should fail the fluency "
                f"floor (it's known-grabby), but it passed."
            )

    def test_known_fluent_pairings_pass_floor(self):
        """Conversely, known-fluent pairings pass the floor."""
        fluent_pairings = [
            (PageAttentionalPosture.TASK_COMPLETION, "reliability_metaphor"),  # +0.7
            (PageAttentionalPosture.TASK_COMPLETION, "forward_motion_metaphor"),  # +0.7
            (PageAttentionalPosture.INFORMATION_FORAGING, "construal_concrete"),  # +0.7
            (PageAttentionalPosture.INFORMATION_FORAGING, "comparison_framing"),  # +0.6
            (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "comparison_framing"),  # +0.7
            (PageAttentionalPosture.SOCIAL_CONSUMPTION, "social_proof"),  # +0.5
        ]
        for posture, mechanism in fluent_pairings:
            assert check_fluency_floor(posture, mechanism) is True, (
                f"{mechanism} on {posture.value} should pass the fluency "
                f"floor (it's known-fluent), but it failed."
            )
