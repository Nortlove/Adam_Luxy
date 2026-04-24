"""Unit tests for the A14 compromise registry."""

from __future__ import annotations

import pytest

from adam.intelligence.recommendation_class import (
    ACTIVE_COMPROMISES,
    COUNTER_REGULATION_UNTRACKED,
    INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY,
    POSTURE_ONLY_ROUTE_SPLIT,
    SINGLE_LEVEL_SHRINKAGE,
    VARIATIONAL_POSTERIOR_APPROXIMATION,
    A14Compromise,
    format_a14_compromises_for_report,
)


# -----------------------------------------------------------------------------
# Registry membership
# -----------------------------------------------------------------------------


def test_active_compromises_contains_all_named_constants() -> None:
    expected = {
        SINGLE_LEVEL_SHRINKAGE,
        POSTURE_ONLY_ROUTE_SPLIT,
        COUNTER_REGULATION_UNTRACKED,
        INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY,
        VARIATIONAL_POSTERIOR_APPROXIMATION,
    }
    assert set(ACTIVE_COMPROMISES) == expected
    assert len(ACTIVE_COMPROMISES) == 5


def test_all_compromise_names_are_unique() -> None:
    names = [c.name for c in ACTIVE_COMPROMISES]
    assert len(names) == len(set(names))


def test_all_compromise_names_are_constant_case() -> None:
    for compromise in ACTIVE_COMPROMISES:
        assert compromise.name == compromise.name.upper()
        assert " " not in compromise.name


# -----------------------------------------------------------------------------
# Field integrity
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("compromise", ACTIVE_COMPROMISES, ids=lambda c: c.name)
def test_compromise_has_nonempty_description(compromise: A14Compromise) -> None:
    assert compromise.description.strip()


@pytest.mark.parametrize("compromise", ACTIVE_COMPROMISES, ids=lambda c: c.name)
def test_compromise_has_nonempty_retirement_trigger(
    compromise: A14Compromise,
) -> None:
    assert compromise.retirement_trigger.strip(), (
        f"{compromise.name} must have an explicit retirement trigger — "
        "A14 discipline requires retirement to be named, not deferred."
    )


@pytest.mark.parametrize("compromise", ACTIVE_COMPROMISES, ids=lambda c: c.name)
def test_compromise_has_at_least_one_live_site(
    compromise: A14Compromise,
) -> None:
    assert compromise.live_at_sites, (
        f"{compromise.name} must name at least one live site — "
        "a compromise with no live sites should be removed from the registry."
    )
    for site in compromise.live_at_sites:
        assert site.strip()


@pytest.mark.parametrize("compromise", ACTIVE_COMPROMISES, ids=lambda c: c.name)
def test_retires_at_weakness_is_positive_or_none(
    compromise: A14Compromise,
) -> None:
    if compromise.retires_at_weakness is not None:
        assert compromise.retires_at_weakness >= 1


# -----------------------------------------------------------------------------
# Specific retirement-trigger wiring (cross-checks the pilot plan)
# -----------------------------------------------------------------------------


def test_single_level_shrinkage_retires_at_weakness_8() -> None:
    assert SINGLE_LEVEL_SHRINKAGE.retires_at_weakness == 8


def test_inferential_chain_attribution_empty_cites_weeks_8_9() -> None:
    trigger = INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY.retirement_trigger.lower()
    assert "week" in trigger
    assert "8" in trigger and "9" in trigger


def test_counter_regulation_trigger_names_habituation_data() -> None:
    trigger = COUNTER_REGULATION_UNTRACKED.retirement_trigger.lower()
    assert "habituation" in trigger


def test_posture_only_trigger_names_processing_depth() -> None:
    trigger = POSTURE_ONLY_ROUTE_SPLIT.retirement_trigger.lower()
    assert "processing-depth" in trigger or "processing depth" in trigger


def test_variational_posterior_retires_at_weakness_8() -> None:
    # Same retirement trigger as SINGLE_LEVEL_SHRINKAGE: multi-tenant
    # hierarchy lands with weakness #8 (or the earlier construct-graph-
    # density trigger, whichever fires first).
    assert VARIATIONAL_POSTERIOR_APPROXIMATION.retires_at_weakness == 8


def test_variational_posterior_trigger_names_pymc_swap() -> None:
    trigger = VARIATIONAL_POSTERIOR_APPROXIMATION.retirement_trigger.lower()
    assert "pymc" in trigger
    assert "nuts" in trigger


# -----------------------------------------------------------------------------
# Dataclass validation (ensure malformed entries fail loudly)
# -----------------------------------------------------------------------------


def test_validate_rejects_empty_name() -> None:
    bad = A14Compromise(
        name="",
        description="x",
        retirement_trigger="x",
        live_at_sites=("foo.py:1",),
    )
    with pytest.raises(ValueError, match="name must be non-empty"):
        bad.validate()


def test_validate_rejects_lowercase_name() -> None:
    bad = A14Compromise(
        name="single_level_shrinkage",
        description="x",
        retirement_trigger="x",
        live_at_sites=("foo.py:1",),
    )
    with pytest.raises(ValueError, match="CONSTANT_CASE"):
        bad.validate()


def test_validate_rejects_empty_retirement_trigger() -> None:
    bad = A14Compromise(
        name="EXAMPLE",
        description="x",
        retirement_trigger="   ",
        live_at_sites=("foo.py:1",),
    )
    with pytest.raises(ValueError, match="retirement_trigger must be non-empty"):
        bad.validate()


def test_validate_rejects_empty_live_at_sites() -> None:
    bad = A14Compromise(
        name="EXAMPLE",
        description="x",
        retirement_trigger="x",
        live_at_sites=(),
    )
    with pytest.raises(ValueError, match="live_at_sites must name at least one"):
        bad.validate()


def test_validate_rejects_nonpositive_retires_at_weakness() -> None:
    bad = A14Compromise(
        name="EXAMPLE",
        description="x",
        retirement_trigger="x",
        live_at_sites=("foo.py:1",),
        retires_at_weakness=0,
    )
    with pytest.raises(ValueError, match="retires_at_weakness must be >= 1"):
        bad.validate()


# -----------------------------------------------------------------------------
# Report rendering
# -----------------------------------------------------------------------------


def test_format_for_report_includes_every_compromise_name() -> None:
    rendered = format_a14_compromises_for_report()
    for compromise in ACTIVE_COMPROMISES:
        assert compromise.name in rendered


def test_format_for_report_includes_every_retirement_trigger() -> None:
    rendered = format_a14_compromises_for_report()
    for compromise in ACTIVE_COMPROMISES:
        # First 40 chars is sufficient to assert each trigger is present;
        # full-string comparison is brittle to whitespace normalization.
        assert compromise.retirement_trigger[:40] in rendered


def test_format_for_report_mentions_weakness_8_for_shrinkage() -> None:
    rendered = format_a14_compromises_for_report()
    assert "structural weakness #8" in rendered


def test_format_for_report_terminates_with_newline() -> None:
    rendered = format_a14_compromises_for_report()
    assert rendered.endswith("\n")
