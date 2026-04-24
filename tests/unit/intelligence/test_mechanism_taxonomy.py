"""Unit tests for the blend-compatible vs vigilance-activating
mechanism taxonomy (attention-inversion platform-core implication #2)."""

from __future__ import annotations

import pytest

from adam.intelligence.mechanism_taxonomy import (
    MECHANISM_TAXONOMY,
    MechanismClassification,
    MechanismRouteCategory,
    blend_compatible_mechanisms,
    classify_mechanism,
    vigilance_activating_mechanisms,
)


# Canonical nine — matches migration 004
_EXPECTED_MECHANISMS = frozenset({
    "automatic_evaluation",
    "wanting_liking_dissociation",
    "evolutionary_motive_activation",
    "linguistic_framing",
    "mimetic_desire",
    "embodied_cognition",
    "attention_dynamics",
    "identity_construction",
    "temporal_construal",
})


# -----------------------------------------------------------------------------
# Coverage — every seeded mechanism is classified
# -----------------------------------------------------------------------------


class TestCoverage:
    def test_all_nine_mechanisms_classified(self):
        assert set(MECHANISM_TAXONOMY.keys()) == _EXPECTED_MECHANISMS

    def test_taxonomy_has_exactly_nine_entries(self):
        assert len(MECHANISM_TAXONOMY) == 9


# -----------------------------------------------------------------------------
# Classification partition
# -----------------------------------------------------------------------------


class TestPartition:
    def test_every_entry_has_valid_category(self):
        for name, cls in MECHANISM_TAXONOMY.items():
            assert cls.category in MechanismRouteCategory, (
                f"{name} has invalid category {cls.category}"
            )

    def test_partition_is_exhaustive_and_exclusive(self):
        blend = set(blend_compatible_mechanisms())
        vigilance = set(vigilance_activating_mechanisms())
        assert blend | vigilance == _EXPECTED_MECHANISMS
        assert blend & vigilance == set()

    def test_blend_compatible_list_size(self):
        # 7 blend-compatible (automatic_evaluation, wanting_liking,
        # evolutionary_motive, linguistic_framing, mimetic_desire,
        # embodied_cognition, temporal_construal).
        assert len(blend_compatible_mechanisms()) == 7

    def test_vigilance_activating_list_size(self):
        # 2 vigilance-activating (attention_dynamics, identity_construction).
        assert len(vigilance_activating_mechanisms()) == 2

    def test_attention_dynamics_is_vigilance_activating(self):
        # The mechanism IS attention capture by definition; any other
        # classification would contradict the attention-inversion
        # platform principle.
        assert classify_mechanism("attention_dynamics").category == (
            MechanismRouteCategory.VIGILANCE_ACTIVATING
        )


# -----------------------------------------------------------------------------
# Regret-correlation prior + route-prior consistency
# -----------------------------------------------------------------------------


class TestRegretCorrelationAndRoute:
    def test_regret_prior_in_unit_interval(self):
        for name, cls in MECHANISM_TAXONOMY.items():
            assert 0.0 <= cls.regret_correlation_prior <= 1.0, (
                f"{name} regret_correlation_prior out of range: "
                f"{cls.regret_correlation_prior}"
            )

    def test_vigilance_mechanisms_have_higher_regret_than_blend_mechanisms(self):
        # The theoretical claim shipped in this taxonomy: attention-
        # route mechanisms correlate more strongly with regret signals
        # than autopilot-route mechanisms. The minimum vigilance
        # prior must exceed the maximum blend prior.
        blend_priors = [
            MECHANISM_TAXONOMY[n].regret_correlation_prior
            for n in blend_compatible_mechanisms()
        ]
        vigilance_priors = [
            MECHANISM_TAXONOMY[n].regret_correlation_prior
            for n in vigilance_activating_mechanisms()
        ]
        assert min(vigilance_priors) > max(blend_priors)

    def test_route_prior_matches_category(self):
        for name, cls in MECHANISM_TAXONOMY.items():
            if cls.category == MechanismRouteCategory.BLEND_COMPATIBLE:
                assert cls.route_prior == "autopilot", (
                    f"{name}: blend_compatible should have autopilot "
                    f"route_prior, got {cls.route_prior!r}"
                )
            else:
                assert cls.route_prior == "attention", (
                    f"{name}: vigilance_activating should have attention "
                    f"route_prior, got {cls.route_prior!r}"
                )


# -----------------------------------------------------------------------------
# Rationale discipline — every entry explains itself
# -----------------------------------------------------------------------------


class TestRationale:
    @pytest.mark.parametrize(
        "mechanism", sorted(_EXPECTED_MECHANISMS),
    )
    def test_rationale_is_nonempty(self, mechanism):
        assert MECHANISM_TAXONOMY[mechanism].rationale.strip()

    def test_borderline_mechanisms_name_their_edge_case(self):
        # Discipline commitment in the module docstring: borderline
        # mechanisms must name their edge case in the rationale text,
        # not hide it in a dominant-category assignment.
        for name in ("linguistic_framing", "identity_construction"):
            rationale = MECHANISM_TAXONOMY[name].rationale.lower()
            assert (
                "borderline" in rationale
                or "edge case" in rationale
                or "mixed" in rationale
            ), f"{name} rationale should name the edge case explicitly"


# -----------------------------------------------------------------------------
# classify_mechanism() accessor
# -----------------------------------------------------------------------------


class TestClassifyAccessor:
    def test_returns_classification_for_known_mechanism(self):
        cls = classify_mechanism("automatic_evaluation")
        assert isinstance(cls, MechanismClassification)
        assert cls.mechanism_name == "automatic_evaluation"

    def test_raises_key_error_for_unknown_mechanism(self):
        with pytest.raises(KeyError, match="unknown mechanism"):
            classify_mechanism("nonexistent_mechanism")

    def test_key_error_lists_valid_mechanisms(self):
        with pytest.raises(KeyError) as exc_info:
            classify_mechanism("fabricated_mechanism")
        # All nine should appear in the error message.
        error_str = str(exc_info.value)
        for name in _EXPECTED_MECHANISMS:
            assert name in error_str


# -----------------------------------------------------------------------------
# Dataclass validation (regressions on malformed entries)
# -----------------------------------------------------------------------------


class TestClassificationValidation:
    def test_regret_prior_out_of_range_rejected(self):
        bad = MechanismClassification(
            mechanism_name="fake",
            category=MechanismRouteCategory.BLEND_COMPATIBLE,
            regret_correlation_prior=1.5,
            route_prior="autopilot",
            rationale="...",
        )
        with pytest.raises(ValueError, match="regret_correlation_prior"):
            bad.validate()

    def test_route_prior_category_mismatch_rejected(self):
        bad = MechanismClassification(
            mechanism_name="fake",
            category=MechanismRouteCategory.VIGILANCE_ACTIVATING,
            regret_correlation_prior=0.5,
            route_prior="autopilot",  # inconsistent
            rationale="...",
        )
        with pytest.raises(ValueError, match="inconsistent"):
            bad.validate()

    def test_empty_rationale_rejected(self):
        bad = MechanismClassification(
            mechanism_name="fake",
            category=MechanismRouteCategory.BLEND_COMPATIBLE,
            regret_correlation_prior=0.5,
            route_prior="autopilot",
            rationale="   ",
        )
        with pytest.raises(ValueError, match="rationale"):
            bad.validate()


# -----------------------------------------------------------------------------
# A14 registry integration
# -----------------------------------------------------------------------------


class TestA14Registration:
    def test_taxonomy_unvalidated_in_active_registry(self):
        from adam.intelligence.recommendation_class import (
            ACTIVE_COMPROMISES,
            MECHANISM_TAXONOMY_UNVALIDATED,
        )
        assert MECHANISM_TAXONOMY_UNVALIDATED in ACTIVE_COMPROMISES

    def test_retirement_trigger_names_both_validations(self):
        from adam.intelligence.recommendation_class import (
            MECHANISM_TAXONOMY_UNVALIDATED,
        )
        trigger = MECHANISM_TAXONOMY_UNVALIDATED.retirement_trigger.lower()
        # Both (a) category assignments and (b) regret priors must be
        # validated before retirement.
        assert "categor" in trigger
        assert "regret" in trigger
        # Rule 11 guard.
        assert "rule 11" in trigger or "regret-free" in trigger
