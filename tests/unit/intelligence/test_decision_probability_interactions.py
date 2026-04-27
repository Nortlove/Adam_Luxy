"""Pin state × trait interaction-term consumption in compute_decision_probability.

Discipline anchors:
    - The gradient field's interaction_terms dict carries OLS-fit coefficients
      that already passed the > 0.005 ΔR² and abs > 0.01 significance filters
      at fit time. Coefficients are applied AS-IS — no invented multipliers.
    - Coefficients were estimated on standardized dimensions (X_std), so we
      standardize buyer values at decision time using the gradient's own
      means/stds. Mixing raw values with a standardized-fit coefficient
      would silently distort the contribution.
    - Without these tests, a future refactor could silently drop interaction
      consumption — and the only signal would be slightly worse probabilities
      (drift the user explicitly warned against).
"""

from __future__ import annotations

from types import SimpleNamespace

from adam.intelligence.decision_probability import compute_decision_probability


def _gradient_with_interaction(
    interaction_terms,
    means=None,
    stds=None,
):
    """Minimal gradient_field stub — duck-typed against GradientVector."""
    return SimpleNamespace(
        gradients={},
        interaction_terms=interaction_terms,
        means=means or {},
        stds=stds or {},
    )


# -----------------------------------------------------------------------------
# Happy path — interaction term lands in weighted_sum and contributions
# -----------------------------------------------------------------------------


def test_interaction_term_contributes_to_weighted_sum():
    """An interaction coefficient with both buyer dims present must alter
    the weighted_sum and surface in dimension_contributions under the
    `interaction:` prefix."""
    buyer_ndf = {
        "approach_avoidance": 0.0, "temporal_horizon": 0.5,
        "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
        "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
        "arousal_seeking": 0.5,
    }
    message_features = {k: 0.5 for k in buyer_ndf}
    buyer_edge_dimensions = {
        "narrative_transport": 0.8,
        "construal_fit": 0.8,
    }

    # Without gradient (baseline)
    baseline = compute_decision_probability(
        buyer_ndf=buyer_ndf,
        message_features=message_features,
        buyer_edge_dimensions=buyer_edge_dimensions,
    )

    # With interaction coefficient: both buyer dims are 1 std above mean,
    # so x_a*x_b = 1.0; coefficient lands as +0.5 in logit space.
    gradient = _gradient_with_interaction(
        interaction_terms={"narrative_transport × construal_fit": 0.5},
        means={"narrative_transport": 0.5, "construal_fit": 0.5},
        stds={"narrative_transport": 0.3, "construal_fit": 0.3},
    )
    with_interaction = compute_decision_probability(
        buyer_ndf=buyer_ndf,
        message_features=message_features,
        buyer_edge_dimensions=buyer_edge_dimensions,
        gradient_field=gradient,
    )

    # Weighted sum must shift by approximately the interaction contribution.
    # Buyer is 0.8, mean 0.5, std 0.3 → x = 1.0 each → coeff * 1 * 1 = 0.5
    delta = with_interaction.weighted_sum - baseline.weighted_sum
    assert 0.45 < delta < 0.55, f"expected ≈+0.5 delta, got {delta}"

    key = "interaction:narrative_transport × construal_fit"
    assert key in with_interaction.dimension_contributions
    assert 0.45 < with_interaction.dimension_contributions[key] < 0.55


def test_negative_interaction_dampens_weighted_sum():
    """A negative interaction coefficient must DECREASE the weighted sum
    when both dims align in the positive direction. Catches sign flips."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"mimetic_desire": 0.8, "value_alignment": 0.8}

    baseline = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions,
    )
    gradient = _gradient_with_interaction(
        interaction_terms={"mimetic_desire × value_alignment": -0.4},
        means={"mimetic_desire": 0.5, "value_alignment": 0.5},
        stds={"mimetic_desire": 0.3, "value_alignment": 0.3},
    )
    with_interaction = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )

    assert with_interaction.weighted_sum < baseline.weighted_sum


# -----------------------------------------------------------------------------
# Soft-fail paths — wiring must never raise
# -----------------------------------------------------------------------------


def test_interaction_skipped_when_buyer_dim_missing():
    """If one half of the pair isn't in buyer_edge_dimensions, the term is
    skipped silently. Decision probability falls back to linear sum."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.8}  # construal_fit missing

    gradient = _gradient_with_interaction(
        interaction_terms={"narrative_transport × construal_fit": 0.5},
        means={"narrative_transport": 0.5, "construal_fit": 0.5},
        stds={"narrative_transport": 0.3, "construal_fit": 0.3},
    )
    result = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )

    # Interaction was dropped — no `interaction:` key surfaces
    interaction_keys = [k for k in result.dimension_contributions if k.startswith("interaction:")]
    assert interaction_keys == []


def test_interaction_skipped_when_std_degenerate():
    """When std is None or near zero, standardization is undefined.
    Skip rather than divide by zero or apply a raw-scale product."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.8, "construal_fit": 0.8}

    # std=0 (degenerate dimension — every observation identical)
    gradient = _gradient_with_interaction(
        interaction_terms={"narrative_transport × construal_fit": 0.5},
        means={"narrative_transport": 0.5, "construal_fit": 0.5},
        stds={"narrative_transport": 0.0, "construal_fit": 0.3},
    )
    result = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )

    interaction_keys = [k for k in result.dimension_contributions if k.startswith("interaction:")]
    assert interaction_keys == []


def test_interaction_skipped_when_means_missing():
    """No means dict at all → can't standardize → must skip silently.
    This path matters for early-cell gradients that have linear coefficients
    but interaction_terms came from a different fit."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.8, "construal_fit": 0.8}

    # Gradient with interaction_terms but EMPTY means/stds
    gradient = SimpleNamespace(
        gradients={},
        interaction_terms={"narrative_transport × construal_fit": 0.5},
        means={},
        stds={},
    )
    result = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )

    # No std → skipped. No exception.
    interaction_keys = [k for k in result.dimension_contributions if k.startswith("interaction:")]
    assert interaction_keys == []


def test_malformed_pair_name_skipped():
    """Pair name without ` × ` separator must be skipped rather than crash
    with ValueError on tuple unpack."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.8}

    gradient = _gradient_with_interaction(
        interaction_terms={"malformed_no_separator": 0.5},
        means={"narrative_transport": 0.5},
        stds={"narrative_transport": 0.3},
    )
    # Must not raise
    result = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )
    assert result is not None


def test_no_gradient_is_no_op():
    """gradient_field=None → no interaction terms applied, no exception.
    Backward-compatibility with all callers that don't pass gradient_field."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.8, "construal_fit": 0.8}

    result = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions,
        gradient_field=None,
    )
    interaction_keys = [k for k in result.dimension_contributions if k.startswith("interaction:")]
    assert interaction_keys == []


def test_empty_interaction_terms_is_no_op():
    """Gradient field with empty interaction_terms (e.g., insufficient
    sample size at fit time) → linear-only sum. No exception."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.8}

    gradient = _gradient_with_interaction(
        interaction_terms={},
        means={"narrative_transport": 0.5},
        stds={"narrative_transport": 0.3},
    )
    result = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )
    interaction_keys = [k for k in result.dimension_contributions if k.startswith("interaction:")]
    assert interaction_keys == []


# -----------------------------------------------------------------------------
# Standardization correctness — coefficient applied AS-IS, not amplified
# -----------------------------------------------------------------------------


def test_buyer_at_population_mean_zero_contribution():
    """When buyer values equal the population means on both dims, the
    standardized values are 0, so the interaction contribution is 0.
    This pins that we are NOT amplifying coefficients with arbitrary
    multipliers."""
    buyer_ndf = {k: 0.5 for k in (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    )}
    buyer_edge_dimensions = {"narrative_transport": 0.5, "construal_fit": 0.5}

    gradient = _gradient_with_interaction(
        interaction_terms={"narrative_transport × construal_fit": 99.0},
        means={"narrative_transport": 0.5, "construal_fit": 0.5},
        stds={"narrative_transport": 0.3, "construal_fit": 0.3},
    )
    baseline = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions,
    )
    with_interaction = compute_decision_probability(
        buyer_ndf=buyer_ndf, message_features=buyer_ndf,
        buyer_edge_dimensions=buyer_edge_dimensions, gradient_field=gradient,
    )

    # Even with coeff=99, standardized value at mean = 0, so contribution = 0
    delta = abs(with_interaction.weighted_sum - baseline.weighted_sum)
    assert delta < 0.01, f"buyer-at-mean must produce ~0 contribution, got {delta}"
