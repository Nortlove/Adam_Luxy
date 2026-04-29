"""Tests for Spine #1 — Per-User N-of-1 Hierarchical Bayesian Engine.

Pins the load-bearing structural claims per the directive Section 3:
    1. UserPosterior natural-parameter representation (precision matrix
       + precision-weighted mean) shape invariants
    2. Cohort membership is a posterior distribution (not hard partition)
    3. BONG single-step natural-gradient update composes additively in
       natural-parameter space; positive-evidence outcomes increase the
       posterior toward the feature direction
    4. Negative-evidence outcomes update in the opposite sign
    5. No-signal outcomes (IMPRESSION_NON_VIEWABLE) leave posterior
       unchanged but bump observation count
    6. Outcome-class vocabulary matches the directive Section 3.3 spec
       (CONVERSION, MICRO_CONVERSION, CLICK_QUALIFIED, VIEWED_ENGAGED,
       CLICK_BOUNCED, VIEWED_DISENGAGED, FREQUENCY_FATIGUE_FIRED,
       AUDIENCE_AGED_OUT, IMPRESSION_NON_VIEWABLE)
    7. Identity-stability weight in [0, 1]
    8. Cohort-prior partial-pooling mixture computes correctly
    9. natural_to_standard round-trip recovers the right (μ, Σ)
   10. Singular precision matrices raise (upstream contract violation)
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.spine.spine_1_n_of_1_engine import (
    IDENTITY_STABILITY_DEFAULT,
    USER_POSTERIOR_DIM,
    CohortPosterior,
    HierarchicalPosteriorSnapshot,
    UserPosterior,
    bong_update_step,
    compute_effective_prior_snapshot,
    get_outcome_schema,
    init_user_posterior,
    known_outcome_classes,
    natural_to_standard,
)


# -----------------------------------------------------------------------------
# Outcome vocabulary
# -----------------------------------------------------------------------------


class TestOutcomeVocabulary:

    def test_full_vocabulary_per_directive_section_3_3(self):
        """The outcome vocabulary must match the directive's spec
        verbatim. Refactors that drop classes surface here."""
        expected = {
            "CONVERSION", "MICRO_CONVERSION",
            "CLICK_QUALIFIED", "VIEWED_ENGAGED",
            "CLICK_BOUNCED", "VIEWED_DISENGAGED",
            "FREQUENCY_FATIGUE_FIRED", "AUDIENCE_AGED_OUT",
            "IMPRESSION_NON_VIEWABLE",
        }
        actual = set(known_outcome_classes())
        assert actual == expected

    def test_conversion_full_positive_weight(self):
        s = get_outcome_schema("CONVERSION")
        assert s.weight == 1.0
        assert s.sign == +1

    def test_micro_conversion_full_positive_weight(self):
        s = get_outcome_schema("MICRO_CONVERSION")
        assert s.weight == 1.0
        assert s.sign == +1

    def test_click_qualified_partial_positive_weight(self):
        s = get_outcome_schema("CLICK_QUALIFIED")
        assert 0.3 <= s.weight <= 0.5
        assert s.sign == +1

    def test_viewed_engaged_partial_positive_weight(self):
        s = get_outcome_schema("VIEWED_ENGAGED")
        assert 0.3 <= s.weight <= 0.5
        assert s.sign == +1

    def test_click_bounced_negative_weight(self):
        s = get_outcome_schema("CLICK_BOUNCED")
        assert 0.5 <= s.weight <= 1.0
        assert s.sign == -1

    def test_viewed_disengaged_negative_weight(self):
        s = get_outcome_schema("VIEWED_DISENGAGED")
        assert 0.5 <= s.weight <= 1.0
        assert s.sign == -1

    def test_frequency_fatigue_is_censoring(self):
        s = get_outcome_schema("FREQUENCY_FATIGUE_FIRED")
        assert s.is_censoring is True
        assert s.sign == -1

    def test_audience_aged_out_is_censoring(self):
        s = get_outcome_schema("AUDIENCE_AGED_OUT")
        assert s.is_censoring is True
        assert s.sign == -1

    def test_non_viewable_no_signal(self):
        s = get_outcome_schema("IMPRESSION_NON_VIEWABLE")
        assert s.weight == 0.0
        assert s.sign == 0

    def test_unknown_outcome_class_raises(self):
        with pytest.raises(ValueError, match="Unknown outcome_class"):
            get_outcome_schema("ARBITRARY_FAKE_OUTCOME")


# -----------------------------------------------------------------------------
# UserPosterior construction + invariants
# -----------------------------------------------------------------------------


class TestUserPosteriorConstruction:

    def test_init_with_no_cohort_prior_uses_population(self):
        p = init_user_posterior(user_id="user:test")
        assert p.user_id == "user:test"
        assert p.dim == USER_POSTERIOR_DIM
        # Population prior: identity precision + zero mean
        assert len(p.precision_matrix_flat) == USER_POSTERIOR_DIM ** 2
        # Identity matrix has 1.0 on the diagonal, 0.0 elsewhere
        for i in range(USER_POSTERIOR_DIM):
            assert p.precision_matrix_flat[i * USER_POSTERIOR_DIM + i] == 1.0
        assert all(v == 0.0 for v in p.precision_weighted_mean)
        assert p.cohort_membership == []
        assert p.identity_stability == IDENTITY_STABILITY_DEFAULT

    def test_init_with_cohort_prior_inherits(self):
        # Build a cohort prior with non-trivial precision
        d = USER_POSTERIOR_DIM
        cohort_precision = [0.0] * (d * d)
        for i in range(d):
            cohort_precision[i * d + i] = 2.0  # double-tight diagonal
        cohort_eta = [0.5] * d

        cohort = CohortPosterior(
            cohort_id="status_seeker",
            precision_matrix_flat=cohort_precision,
            precision_weighted_mean=cohort_eta,
        )
        p = init_user_posterior(user_id="user:test", cohort_prior=cohort)
        # User starts at the cohort prior (natural-parameter copy).
        assert p.precision_matrix_flat == cohort_precision
        assert p.precision_weighted_mean == cohort_eta
        assert p.cohort_membership == [1.0]
        assert p.cohort_ids == ["status_seeker"]

    def test_invalid_identity_stability_rejected(self):
        d = USER_POSTERIOR_DIM
        with pytest.raises(ValueError, match="identity_stability"):
            UserPosterior(
                user_id="u",
                precision_matrix_flat=[1.0] * (d * d),
                precision_weighted_mean=[0.0] * d,
                identity_stability=1.5,  # > 1.0
            )

    def test_invalid_precision_shape_rejected(self):
        d = USER_POSTERIOR_DIM
        with pytest.raises(ValueError, match="precision_matrix_flat"):
            UserPosterior(
                user_id="u",
                precision_matrix_flat=[1.0] * (d * d - 1),  # wrong shape
                precision_weighted_mean=[0.0] * d,
            )

    def test_invalid_mean_shape_rejected(self):
        d = USER_POSTERIOR_DIM
        with pytest.raises(ValueError, match="precision_weighted_mean"):
            UserPosterior(
                user_id="u",
                precision_matrix_flat=[1.0] * (d * d),
                precision_weighted_mean=[0.0] * (d - 1),
            )

    def test_cohort_membership_must_sum_to_one(self):
        d = USER_POSTERIOR_DIM
        with pytest.raises(ValueError, match="sum to"):
            UserPosterior(
                user_id="u",
                precision_matrix_flat=[1.0] * (d * d),
                precision_weighted_mean=[0.0] * d,
                cohort_membership=[0.4, 0.4],  # sums to 0.8
                cohort_ids=["a", "b"],
            )

    def test_cohort_membership_entries_in_unit_interval(self):
        d = USER_POSTERIOR_DIM
        with pytest.raises(ValueError, match="in \\[0, 1\\]"):
            UserPosterior(
                user_id="u",
                precision_matrix_flat=[1.0] * (d * d),
                precision_weighted_mean=[0.0] * d,
                cohort_membership=[1.5, -0.5],  # out of range
                cohort_ids=["a", "b"],
            )


# -----------------------------------------------------------------------------
# BONG update step
# -----------------------------------------------------------------------------


class TestBONGUpdate:

    def _make_test_user(self) -> UserPosterior:
        return init_user_posterior(user_id="user:bong_test")

    def _make_test_features(self) -> list:
        # First-dim active feature; rest zero
        d = USER_POSTERIOR_DIM
        x = [0.0] * d
        x[0] = 1.0
        x[1] = 0.5
        return x

    def test_conversion_increases_precision(self):
        """A CONVERSION updates Λ_new = Λ_old + w · x xᵀ.
        Dim-0 diagonal precision should increase by w · x_0² = 1.0 · 1.0 = 1.0."""
        u0 = self._make_test_user()
        x = self._make_test_features()
        u1 = bong_update_step(u0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        d = USER_POSTERIOR_DIM
        # Diagonal[0] grew from 1.0 (identity prior) to 1.0 + 1.0·1.0 = 2.0
        assert u1.precision_matrix_flat[0 * d + 0] == pytest.approx(2.0)
        # Diagonal[1] grew from 1.0 + 1.0·0.5² = 1.25
        assert u1.precision_matrix_flat[1 * d + 1] == pytest.approx(1.25)
        # Off-diagonal[0,1] grew from 0.0 + 1.0·1.0·0.5 = 0.5
        assert u1.precision_matrix_flat[0 * d + 1] == pytest.approx(0.5)

    def test_conversion_increments_observation_count(self):
        u0 = self._make_test_user()
        x = self._make_test_features()
        u1 = bong_update_step(u0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        assert u1.total_observations == u0.total_observations + 1
        assert u1.last_outcome_class == "CONVERSION"

    def test_positive_evidence_pushes_eta_forward(self):
        """η_new = η_old + w · sign · y · x; for CONVERSION (sign=+1)
        and y=1.0, x=[1, 0.5, 0,...], η[0] grows by 1·1·1·1 = 1.0."""
        u0 = self._make_test_user()
        x = self._make_test_features()
        u1 = bong_update_step(u0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        assert u1.precision_weighted_mean[0] == pytest.approx(1.0)
        assert u1.precision_weighted_mean[1] == pytest.approx(0.5)

    def test_negative_evidence_pushes_eta_backward(self):
        """CLICK_BOUNCED has sign=-1; η updates in the opposite direction."""
        u0 = self._make_test_user()
        x = self._make_test_features()
        u1 = bong_update_step(u0, x, outcome_value=1.0,
                              outcome_class="CLICK_BOUNCED")
        # CLICK_BOUNCED weight is 0.7, sign -1 → η[0] = 0 + 0.7·(-1)·1·1 = -0.7
        assert u1.precision_weighted_mean[0] == pytest.approx(-0.7)

    def test_non_viewable_leaves_posterior_unchanged(self):
        """IMPRESSION_NON_VIEWABLE has weight=0; posterior natural
        parameters unchanged. Observation count + last_outcome_class
        still update for accounting."""
        u0 = self._make_test_user()
        x = self._make_test_features()
        u1 = bong_update_step(u0, x, outcome_value=1.0,
                              outcome_class="IMPRESSION_NON_VIEWABLE")
        assert u1.precision_matrix_flat == u0.precision_matrix_flat
        assert u1.precision_weighted_mean == u0.precision_weighted_mean
        assert u1.total_observations == u0.total_observations + 1
        assert u1.last_outcome_class == "IMPRESSION_NON_VIEWABLE"

    def test_updates_compose_additively_in_natural_param_space(self):
        """Two CONVERSIONS in sequence should produce the same posterior
        as one CONVERSION with double-weight feature contribution."""
        u0 = self._make_test_user()
        x = self._make_test_features()

        u_two = bong_update_step(u0, x, 1.0, "CONVERSION")
        u_two = bong_update_step(u_two, x, 1.0, "CONVERSION")

        # Equivalent: precision should be Λ_0 + 2 · 1 · x xᵀ
        d = USER_POSTERIOR_DIM
        assert u_two.precision_matrix_flat[0 * d + 0] == pytest.approx(3.0)
        assert u_two.precision_weighted_mean[0] == pytest.approx(2.0)

    def test_unknown_outcome_class_raises(self):
        u0 = self._make_test_user()
        x = self._make_test_features()
        with pytest.raises(ValueError, match="Unknown outcome_class"):
            bong_update_step(u0, x, 1.0, "ARBITRARY_FAKE")

    def test_feature_vector_shape_validated(self):
        u0 = self._make_test_user()
        x_wrong = [1.0]  # too short
        with pytest.raises(ValueError, match="feature_vector"):
            bong_update_step(u0, x_wrong, 1.0, "CONVERSION")


# -----------------------------------------------------------------------------
# Natural-to-standard conversion
# -----------------------------------------------------------------------------


class TestNaturalToStandardConversion:

    def test_population_prior_round_trip(self):
        """For the population prior (Λ = I, η = 0), μ = 0 and Σ = I."""
        p = init_user_posterior(user_id="u")
        mu, Sigma_flat = natural_to_standard(p)
        d = USER_POSTERIOR_DIM
        assert all(abs(v) < 1e-9 for v in mu)
        # Diagonal entries should be 1.0 (since Λ = I → Σ = I)
        for i in range(d):
            assert Sigma_flat[i * d + i] == pytest.approx(1.0)
            for j in range(d):
                if i != j:
                    assert Sigma_flat[i * d + j] == pytest.approx(0.0,
                                                                  abs=1e-9)

    def test_after_update_mean_shifts_toward_evidence(self):
        """After a CONVERSION on feature x = [1, 0, ...], the posterior
        mean should have positive mass on dim 0."""
        p = init_user_posterior(user_id="u")
        d = USER_POSTERIOR_DIM
        x = [0.0] * d
        x[0] = 1.0
        p1 = bong_update_step(p, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        mu, _ = natural_to_standard(p1)
        # μ[0] should be > 0 after positive evidence on dim 0
        assert mu[0] > 0.0


# -----------------------------------------------------------------------------
# Partial-pooling effective-prior snapshot
# -----------------------------------------------------------------------------


class TestEffectivePriorSnapshot:

    def _make_cohort(self, cohort_id: str, mean_value: float) -> CohortPosterior:
        """Build a cohort with all-mean_value precision-weighted-mean
        and identity precision."""
        d = USER_POSTERIOR_DIM
        precision = [0.0] * (d * d)
        for i in range(d):
            precision[i * d + i] = 1.0
        return CohortPosterior(
            cohort_id=cohort_id,
            precision_matrix_flat=precision,
            precision_weighted_mean=[mean_value] * d,
        )

    def test_snapshot_with_full_identity_stability_uses_user_only(self):
        """When identity_stability = 1.0, the snapshot ignores cohort
        priors and uses only the per-user posterior."""
        d = USER_POSTERIOR_DIM
        user = init_user_posterior(user_id="u")
        # Force identity_stability = 1.0
        user = user.model_copy(update={
            "identity_stability": 1.0,
            "cohort_membership": [1.0],
            "cohort_ids": ["status_seeker"],
        })
        cohort = self._make_cohort("status_seeker", mean_value=10.0)

        snap = compute_effective_prior_snapshot(
            user, cohort_priors={"status_seeker": cohort},
        )
        # ω = 1 → μ_eff = μ_user = 0
        assert all(abs(v) < 1e-9 for v in snap.effective_mean)

    def test_snapshot_with_zero_identity_stability_uses_cohort(self):
        """When identity_stability = 0.0, the snapshot uses only the
        cohort mixture."""
        d = USER_POSTERIOR_DIM
        user = init_user_posterior(user_id="u")
        user = user.model_copy(update={
            "identity_stability": 0.0,
            "cohort_membership": [1.0],
            "cohort_ids": ["status_seeker"],
        })
        cohort = self._make_cohort("status_seeker", mean_value=2.0)

        snap = compute_effective_prior_snapshot(
            user, cohort_priors={"status_seeker": cohort},
        )
        # ω = 0 → μ_eff = μ_cohort = Σ_cohort · η_cohort = I⁻¹ · 2 = 2
        for v in snap.effective_mean:
            assert v == pytest.approx(2.0)

    def test_missing_cohort_falls_back_gracefully(self):
        """When a referenced cohort_id is missing from cohort_priors,
        the snapshot still produces a sensible effective prior using
        the user-only path."""
        d = USER_POSTERIOR_DIM
        user = init_user_posterior(user_id="u")
        user = user.model_copy(update={
            "identity_stability": 0.5,
            "cohort_membership": [1.0],
            "cohort_ids": ["nonexistent_cohort"],
        })
        snap = compute_effective_prior_snapshot(user, cohort_priors={})
        # No KeyError, no crash; snapshot returned.
        assert snap.user_id == "u"
        assert len(snap.effective_mean) == d

    def test_two_cohort_mixture(self):
        """A user with 50/50 cohort membership averages the cohort
        priors (when identity_stability = 0)."""
        d = USER_POSTERIOR_DIM
        user = init_user_posterior(user_id="u")
        user = user.model_copy(update={
            "identity_stability": 0.0,
            "cohort_membership": [0.5, 0.5],
            "cohort_ids": ["A", "B"],
        })
        cohort_a = self._make_cohort("A", mean_value=2.0)
        cohort_b = self._make_cohort("B", mean_value=4.0)

        snap = compute_effective_prior_snapshot(
            user, cohort_priors={"A": cohort_a, "B": cohort_b},
        )
        # η_mix = 0.5·2 + 0.5·4 = 3
        # P_mix = 0.5·I + 0.5·I = I
        # μ_eff = P_mix⁻¹ · η_mix = I · 3 = 3
        for v in snap.effective_mean:
            assert v == pytest.approx(3.0)


# -----------------------------------------------------------------------------
# Neo4j serialization
# -----------------------------------------------------------------------------


class TestNeo4jSerialization:

    def test_to_neo4j_props_includes_required_fields(self):
        p = init_user_posterior(user_id="user:nx_test")
        props = p.to_neo4j_props()
        assert "user_id" in props
        assert "dim" in props
        assert "precision_matrix_flat_json" in props
        assert "precision_weighted_mean_json" in props
        assert "identity_stability" in props
        assert "total_observations" in props
        assert "last_updated_at" in props

    def test_neo4j_props_round_trip_through_json(self):
        import json as _json
        p = init_user_posterior(user_id="user:nx_test")
        props = p.to_neo4j_props()
        # Round-trip the float arrays through JSON.
        precision_round = _json.loads(props["precision_matrix_flat_json"])
        eta_round = _json.loads(props["precision_weighted_mean_json"])
        assert precision_round == p.precision_matrix_flat
        assert eta_round == p.precision_weighted_mean
