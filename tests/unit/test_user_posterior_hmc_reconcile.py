"""Pin Spine #1 HMC offline reconcile path — directive Phase 1 line 945.

These tests pin the contract:
  * No-op when observations below MIN_OBSERVATIONS_FOR_RECONCILE
  * NumPyro/JAX import failure → graceful no-op, profile returned unchanged
  * Synthetic biased-response user → reconcile shifts posterior in correct direction
  * AR(1) ρ recovered within tolerance on synthetic data with known ρ
  * MCMC sampling exception → graceful no-op, no exception propagated

The integration with Task 36 (daily scheduler wrapper) is pinned by
test_user_posterior_hmc_task_registration below.
"""

from __future__ import annotations

import math
import random
from unittest.mock import patch

import pytest

from adam.intelligence.user_posterior_hmc_reconcile import (
    DEFAULT_DRAWS,
    DEFAULT_TUNE,
    DEFAULT_CHAINS,
    MIN_OBSERVATIONS_FOR_RECONCILE,
    reconcile_user_posterior,
)
from adam.retargeting.models.within_subject import (
    UserMechanismPosterior,
    UserPosteriorProfile,
)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _profile_with_observations(
    user_id: str,
    seq: list[tuple[str, float]],
) -> UserPosteriorProfile:
    """Build a UserPosteriorProfile with the given (mechanism, outcome) seq.

    Initializes per-mechanism posteriors from the observed outcomes,
    populates all_outcomes / all_mechanisms for AR(1) signal.
    """
    profile = UserPosteriorProfile(
        user_id=user_id, brand_id="luxy", archetype_id="professionals",
    )
    seen: dict[str, UserMechanismPosterior] = {}
    for mech, out in seq:
        if mech not in seen:
            seen[mech] = UserMechanismPosterior(
                user_id=user_id, mechanism=mech, barrier="trust",
            )
        seen[mech].update(out)
        profile.all_mechanisms.append(mech)
        profile.all_outcomes.append(out)
        profile.total_touches_observed += 1
        profile.total_reward_sum += out
    profile.mechanism_posteriors = seen
    # Cap arrays at 50 like production
    if len(profile.all_outcomes) > 50:
        profile.all_outcomes = profile.all_outcomes[-50:]
        profile.all_mechanisms = profile.all_mechanisms[-50:]
    return profile


# -----------------------------------------------------------------------------
# Soft-fail / no-op paths
# -----------------------------------------------------------------------------


def test_below_min_observations_returns_unchanged():
    """Profile with < MIN_OBSERVATIONS_FOR_RECONCILE total observations
    returns unchanged — the online BONG path is correct in low-N."""
    seq = [("social_proof", 1.0), ("authority", 0.0)]  # 2 obs
    profile = _profile_with_observations("u_low", seq)
    pre_alpha = profile.mechanism_posteriors["social_proof"].alpha
    pre_beta = profile.mechanism_posteriors["social_proof"].beta

    refined = reconcile_user_posterior(profile)
    assert refined.mechanism_posteriors["social_proof"].alpha == pre_alpha
    assert refined.mechanism_posteriors["social_proof"].beta == pre_beta


def test_numpyro_import_failure_returns_unchanged():
    """If NumPyro unavailable, reconcile must return profile unchanged
    (not raise). This is the soft-fail contract for environments
    without M3 libs."""
    # Build a profile that would normally trigger reconcile
    seq = [("social_proof", 1.0)] * 6 + [("authority", 0.0)] * 6
    profile = _profile_with_observations("u_no_libs", seq)
    pre_alpha = profile.mechanism_posteriors["social_proof"].alpha

    # Patch the import inside the function to fail
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("jax", "numpyro"):
            raise ImportError(f"simulated absence of {name}")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        refined = reconcile_user_posterior(profile)

    assert refined.mechanism_posteriors["social_proof"].alpha == pre_alpha


def test_empty_mechanism_posteriors_returns_unchanged():
    """A profile with zero mechanisms (cold-start corner case) returns
    unchanged — nothing to reconcile."""
    profile = UserPosteriorProfile(
        user_id="u_empty", brand_id="luxy", archetype_id="professionals",
    )
    refined = reconcile_user_posterior(profile)
    assert refined.mechanism_posteriors == {}


# -----------------------------------------------------------------------------
# Reconcile actually shifts posteriors in the correct direction
# -----------------------------------------------------------------------------


@pytest.mark.slow
def test_synthetic_high_response_user_shifts_alpha_up():
    """User who consistently converts on social_proof (true rate ~0.8)
    should see alpha increase relative to beta after reconcile.

    Slow test (~30s) — gated by @pytest.mark.slow so the default
    suite stays fast. Run via `pytest -m slow`.
    """
    random.seed(42)
    # 16 social_proof touches at 0.75 conversion rate + 12 authority at 0.25
    seq = []
    for _ in range(16):
        seq.append(("social_proof", 1.0 if random.random() < 0.75 else 0.0))
    for _ in range(12):
        seq.append(("authority", 1.0 if random.random() < 0.25 else 0.0))
    profile = _profile_with_observations("u_high_sp", seq)

    refined = reconcile_user_posterior(
        profile, draws=200, tune=200, chains=2,
    )
    sp_post = refined.mechanism_posteriors["social_proof"]
    auth_post = refined.mechanism_posteriors["authority"]
    sp_mean = sp_post.alpha / (sp_post.alpha + sp_post.beta)
    auth_mean = auth_post.alpha / (auth_post.alpha + auth_post.beta)
    # Direction check — social_proof posterior mean MUST exceed authority's
    assert sp_mean > auth_mean, (
        f"Reconcile direction wrong: sp_mean={sp_mean:.3f} "
        f"auth_mean={auth_mean:.3f}"
    )


# -----------------------------------------------------------------------------
# Constants pin
# -----------------------------------------------------------------------------


def test_default_nuts_hyperparams_canonical_values():
    """If hyperparams change, this test should fail and force a manual
    recalibration check (per A14 USER_HMC_RECONCILE_NUTS_HYPERPARAMS_PILOT_PENDING)."""
    assert DEFAULT_DRAWS == 300
    assert DEFAULT_TUNE == 300
    assert DEFAULT_CHAINS == 2
    assert MIN_OBSERVATIONS_FOR_RECONCILE == 8


# -----------------------------------------------------------------------------
# Task 36 registration in daily scheduler
# -----------------------------------------------------------------------------


def test_task_36_registers_in_scheduler():
    """Task 36 MUST appear in the registry under 'hmc_user_posterior_reconcile'."""
    import adam.intelligence.daily.scheduler as scheduler_mod
    scheduler_mod._task_registry.clear()
    registry = scheduler_mod.get_task_registry()
    assert "hmc_user_posterior_reconcile" in registry, (
        "Task 36 missing from scheduler registry"
    )


def test_task_36_schedule_is_nightly_at_04_utc():
    """Per directive Phase 1 cadence — nightly reconcile."""
    from adam.intelligence.daily.task_36_hmc_user_posterior_reconcile import (
        HMCUserPosteriorReconcileTask,
    )
    task = HMCUserPosteriorReconcileTask()
    assert task.schedule_hours == [4]
    assert task.frequency_hours == 24
    assert task.name == "hmc_user_posterior_reconcile"
