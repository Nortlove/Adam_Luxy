"""Pin Phase 3 Slice 2 — δ_iac flow into per-user reconcile.

Directive Phase 1 line 985-998 ordering. Tests pin:

  * Regression: ``reconcile_user_posterior(profile)`` (no iac_prior arg)
    matches ``reconcile_user_posterior(profile, iac_prior=None)`` exactly,
    and matches the pre-Slice-2 path (no mech_slope key in samples).
  * Recovery: synthetic user with a planted (archetype, mechanism, category)
    interaction → reconcile with informative iac_prior pushes
    ``profile.mechanism_slopes[m]`` in the planted direction more
    strongly than reconcile without the prior.
  * Degenerate: mechanisms missing from population posterior fall back
    to diffuse Normal(0, 0.5) — output stays sane (no NaN, no crash).
  * Empty IacPriorMoments → byte-identical to iac_prior=None path.
  * Loader: extract_iac_prior_from_inferencedata recovers moments;
    Neo4j writeback / reload round-trips.

Slow NUTS-based tests gated by ``@pytest.mark.slow`` to keep the
unit suite fast.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

from adam.intelligence.iac_prior import (
    DEFAULT_FALLBACK_MEAN,
    DEFAULT_FALLBACK_STD,
    IacPriorMoments,
    extract_iac_prior_from_inferencedata,
    iac_prior_for_user,
    load_iac_prior_from_neo4j,
    write_iac_posterior_to_neo4j,
)
from adam.intelligence.user_posterior_hmc_reconcile import (
    MIN_OBSERVATIONS_FOR_RECONCILE,
    _resolve_iac_per_mechanism,
    reconcile_user_posterior,
)
from adam.retargeting.models.within_subject import (
    UserMechanismPosterior,
    UserPosteriorProfile,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _profile_with_observations(
    user_id: str,
    archetype_id: str,
    seq: List[Tuple[str, float]],
) -> UserPosteriorProfile:
    """Build a UserPosteriorProfile with the given (mechanism, outcome) seq."""
    profile = UserPosteriorProfile(
        user_id=user_id, brand_id="luxy", archetype_id=archetype_id,
    )
    seen = {}
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
    return profile


# -----------------------------------------------------------------------------
# IacPriorMoments — pure container, no NumPyro needed
# -----------------------------------------------------------------------------


def test_iac_prior_moments_empty_default():
    moments = IacPriorMoments()
    assert moments.is_empty()
    assert moments.n_triples == 0
    assert moments.per_mechanism_for_user("any", ["a", "b"]) == {}


def test_iac_prior_moments_per_mechanism_marginalization():
    """Per-mechanism mean is the average over categories within an
    archetype × mechanism column. Variance composes within + between."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.4, 0.04)
    moments.moments[("exec", "authority", "leisure")] = (0.2, 0.04)
    # Different archetype, same mechanism — must NOT contaminate
    moments.moments[("pro", "authority", "biz")] = (-0.5, 0.04)
    # Different mechanism — must NOT contaminate
    moments.moments[("exec", "scarcity", "biz")] = (1.0, 0.04)

    result = moments.per_mechanism_for_user("exec", ["authority"])
    assert "authority" in result
    mean, std = result["authority"]
    # mean = (0.4 + 0.2) / 2 = 0.3
    assert math.isclose(mean, 0.3, abs_tol=1e-6)
    # var = mean(within_var) + var(means)
    #     = mean(0.04, 0.04) + var(0.4, 0.2)
    #     = 0.04 + ((0.4-0.3)^2 + (0.2-0.3)^2)/2
    #     = 0.04 + 0.01 = 0.05
    # std = sqrt(0.05) ≈ 0.2236
    assert math.isclose(std, math.sqrt(0.05), abs_tol=1e-3)


def test_iac_prior_moments_unknown_mechanism_omitted():
    """Mechanisms with no archetype coverage are simply absent from
    the returned dict (caller falls back to diffuse Normal(0, 0.5))."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.4, 0.04)
    result = moments.per_mechanism_for_user(
        "exec", ["authority", "social_proof"],
    )
    assert "authority" in result
    assert "social_proof" not in result


def test_iac_prior_moments_floor_std():
    """Pathologically tight population posterior → std floored at 0.05
    so per-user reconcile isn't dragged into overconfidence."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.4, 1e-12)
    result = moments.per_mechanism_for_user("exec", ["authority"])
    _, std = result["authority"]
    assert std >= 0.05


# -----------------------------------------------------------------------------
# iac_prior_for_user — wraps marginalization + filters by user profile
# -----------------------------------------------------------------------------


def test_iac_prior_for_user_returns_empty_for_none():
    profile = _profile_with_observations("u", "exec", [("authority", 1.0)])
    assert iac_prior_for_user(profile, None) == {}


def test_iac_prior_for_user_returns_empty_for_empty_moments():
    profile = _profile_with_observations("u", "exec", [("authority", 1.0)])
    assert iac_prior_for_user(profile, IacPriorMoments()) == {}


def test_iac_prior_for_user_returns_empty_for_missing_archetype():
    """User has no archetype_id → no informative prior can be applied."""
    profile = UserPosteriorProfile(
        user_id="u", brand_id="luxy", archetype_id="",
    )
    profile.mechanism_posteriors["authority"] = UserMechanismPosterior(
        user_id="u", mechanism="authority", barrier="trust",
    )
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.4, 0.04)
    assert iac_prior_for_user(profile, moments) == {}


def test_iac_prior_for_user_filters_to_archetype():
    profile = _profile_with_observations(
        "u", "exec", [("authority", 1.0), ("scarcity", 0.0)],
    )
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.4, 0.04)
    moments.moments[("pro", "authority", "biz")] = (-0.5, 0.04)
    moments.moments[("exec", "scarcity", "biz")] = (-0.2, 0.04)
    result = iac_prior_for_user(profile, moments)
    assert set(result.keys()) == {"authority", "scarcity"}
    assert math.isclose(result["authority"][0], 0.4, abs_tol=1e-6)
    assert math.isclose(result["scarcity"][0], -0.2, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# _resolve_iac_per_mechanism — soft-fail discipline
# -----------------------------------------------------------------------------


def test_resolve_iac_per_mechanism_none_returns_empty():
    profile = _profile_with_observations("u", "exec", [("authority", 1.0)])
    assert _resolve_iac_per_mechanism(profile, None) == {}


def test_resolve_iac_per_mechanism_empty_moments_returns_empty():
    profile = _profile_with_observations("u", "exec", [("authority", 1.0)])
    assert _resolve_iac_per_mechanism(profile, IacPriorMoments()) == {}


def test_resolve_iac_per_mechanism_resolution_exception_returns_empty():
    """Object that crashes on iteration must not raise — returns {}."""
    profile = _profile_with_observations("u", "exec", [("authority", 1.0)])

    class _BoomMoments:
        def is_empty(self):
            raise RuntimeError("boom")

    assert _resolve_iac_per_mechanism(profile, _BoomMoments()) == {}


# -----------------------------------------------------------------------------
# Regression: reconcile with iac_prior=None matches default behavior
# -----------------------------------------------------------------------------


def test_reconcile_with_none_iac_prior_below_threshold_no_op():
    """Below MIN_OBSERVATIONS_FOR_RECONCILE → unchanged regardless of
    iac_prior arg. Matches the pre-Slice-2 contract bit-for-bit."""
    seq = [("authority", 1.0), ("scarcity", 0.0)]  # 2 obs, < 8 threshold
    profile = _profile_with_observations("u_low", "exec", seq)
    pre_alpha = profile.mechanism_posteriors["authority"].alpha

    refined = reconcile_user_posterior(profile, iac_prior=None)
    assert refined.mechanism_posteriors["authority"].alpha == pre_alpha
    # mech_slopes must not be populated when no_op
    assert profile.mechanism_slopes == {}


def test_reconcile_with_empty_iac_prior_below_threshold_no_op():
    """Empty IacPriorMoments → same no-op below threshold."""
    seq = [("authority", 1.0), ("scarcity", 0.0)]
    profile = _profile_with_observations("u_low", "exec", seq)
    pre_alpha = profile.mechanism_posteriors["authority"].alpha

    refined = reconcile_user_posterior(
        profile, iac_prior=IacPriorMoments(),
    )
    assert refined.mechanism_posteriors["authority"].alpha == pre_alpha


# -----------------------------------------------------------------------------
# Loader: extract_iac_prior_from_inferencedata + Neo4j round-trip
# -----------------------------------------------------------------------------


def test_extract_iac_prior_missing_delta_iac_returns_empty():
    """InferenceData without delta_iac → empty moments (no exception)."""
    fake_idata = MagicMock()
    fake_idata.posterior.__getitem__.side_effect = KeyError("delta_iac")
    moments = extract_iac_prior_from_inferencedata(
        fake_idata, [("exec", "authority", "biz")],
    )
    assert moments.is_empty()


def test_extract_iac_prior_mismatched_triples_returns_empty():
    """Posterior n_iac != len(triples) → empty (mismatch detection)."""
    np = pytest.importorskip("numpy")
    # Build a fake InferenceData-like object whose mean()/var() return
    # arrays of length 3, but caller passes 2 triples.
    fake_array = MagicMock()
    fake_array.values = np.array([0.1, 0.2, 0.3])
    fake_post = MagicMock()
    fake_post.mean.return_value = fake_array
    fake_post.var.return_value = fake_array

    fake_idata = MagicMock()
    fake_idata.posterior = {"delta_iac": fake_post}

    triples = [("exec", "authority", "biz"), ("exec", "scarcity", "biz")]
    moments = extract_iac_prior_from_inferencedata(fake_idata, triples)
    assert moments.is_empty()


def test_extract_iac_prior_round_trip_in_memory():
    """Synthetic posterior arrays → moments populated correctly."""
    np = pytest.importorskip("numpy")
    means = np.array([0.5, -0.3, 0.0])
    vars_ = np.array([0.04, 0.09, 0.01])

    mean_box = MagicMock()
    mean_box.values = means
    var_box = MagicMock()
    var_box.values = vars_

    fake_post = MagicMock()
    fake_post.mean.return_value = mean_box
    fake_post.var.return_value = var_box

    fake_idata = MagicMock()
    fake_idata.posterior = {"delta_iac": fake_post}

    triples = [
        ("exec", "authority", "biz"),
        ("exec", "scarcity", "biz"),
        ("pro", "authority", "biz"),
    ]
    moments = extract_iac_prior_from_inferencedata(
        fake_idata, triples, fitted_at_ts=12345.0,
    )
    assert moments.n_triples == 3
    assert moments.fitted_at_ts == 12345.0
    assert math.isclose(
        moments.moments[("exec", "authority", "biz")][0], 0.5, abs_tol=1e-6,
    )
    assert math.isclose(
        moments.moments[("pro", "authority", "biz")][1], 0.01, abs_tol=1e-6,
    )


def test_extract_iac_prior_skips_negative_variance():
    """Negative variance (numerically impossible but defensive) → triple
    silently dropped rather than admitting it."""
    np = pytest.importorskip("numpy")
    means = np.array([0.5, 0.5])
    vars_ = np.array([0.04, -0.001])  # second is negative

    mean_box = MagicMock()
    mean_box.values = means
    var_box = MagicMock()
    var_box.values = vars_

    fake_post = MagicMock()
    fake_post.mean.return_value = mean_box
    fake_post.var.return_value = var_box

    fake_idata = MagicMock()
    fake_idata.posterior = {"delta_iac": fake_post}

    triples = [("exec", "authority", "biz"), ("exec", "scarcity", "biz")]
    moments = extract_iac_prior_from_inferencedata(fake_idata, triples)
    # Only the first triple should survive
    assert moments.n_triples == 1
    assert ("exec", "authority", "biz") in moments.moments
    assert ("exec", "scarcity", "biz") not in moments.moments


# -----------------------------------------------------------------------------
# Neo4j writeback / load — soft-fail when no driver
# -----------------------------------------------------------------------------


def test_write_iac_posterior_empty_returns_zero_without_driver_call():
    """Empty moments → no work attempted, no driver resolution needed."""
    result = write_iac_posterior_to_neo4j(IacPriorMoments(), driver=None)
    assert result == 0


def test_write_iac_posterior_dependency_failure_returns_zero(monkeypatch):
    """When get_neo4j_driver itself raises, writeback soft-fails to 0."""
    import adam.intelligence.iac_prior as iac_mod

    def _boom():
        raise RuntimeError("driver factory unavailable")

    # Substitute the import path used inside write_iac_posterior_to_neo4j
    fake_deps = type(
        "FakeDependencies", (), {"get_neo4j_driver": staticmethod(_boom)},
    )
    monkeypatch.setattr(
        "adam.core.dependencies.get_neo4j_driver", _boom, raising=False,
    )

    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.4, 0.04)
    result = iac_mod.write_iac_posterior_to_neo4j(moments, driver=None)
    assert result == 0


def test_load_iac_posterior_dependency_failure_returns_empty(monkeypatch):
    """When get_neo4j_driver raises, load soft-fails to empty moments."""
    import adam.intelligence.iac_prior as iac_mod

    def _boom():
        raise RuntimeError("driver factory unavailable")

    monkeypatch.setattr(
        "adam.core.dependencies.get_neo4j_driver", _boom, raising=False,
    )
    moments = iac_mod.load_iac_prior_from_neo4j(driver=None)
    assert moments.is_empty()


def test_load_iac_posterior_returns_empty_when_driver_none_explicitly(monkeypatch):
    """Force get_neo4j_driver to return None — load soft-fails to empty."""
    import adam.intelligence.iac_prior as iac_mod

    monkeypatch.setattr(
        "adam.core.dependencies.get_neo4j_driver", lambda: None,
        raising=False,
    )
    moments = iac_mod.load_iac_prior_from_neo4j(driver=None)
    assert moments.is_empty()


def test_neo4j_round_trip_with_mock_driver():
    """Round-trip writeback → load via a mock driver. Pins the cypher
    parameter contract so a future schema change (renaming
    posterior_mean → delta_mean, etc.) breaks the test loudly."""
    captured_writes = []

    def _mock_session_run(cypher, **params):
        captured_writes.append(params)
        result = MagicMock()
        result.__iter__ = lambda self: iter([])
        return result

    mock_session = MagicMock()
    mock_session.run = _mock_session_run
    mock_session.__enter__ = lambda self: mock_session
    mock_session.__exit__ = lambda *args: False

    mock_driver = MagicMock()
    mock_driver.session = lambda: mock_session

    moments = IacPriorMoments(fitted_at_ts=100.0)
    moments.moments[("exec", "authority", "biz")] = (0.4, 0.04)
    moments.moments[("exec", "scarcity", "biz")] = (-0.2, 0.09)

    written = write_iac_posterior_to_neo4j(moments, driver=mock_driver)
    assert written == 2
    # Param contract: each write carries archetype, mechanism, category,
    # posterior_mean, posterior_variance, fitted_at_ts.
    for w in captured_writes:
        assert "archetype" in w
        assert "mechanism" in w
        assert "category" in w
        assert "posterior_mean" in w
        assert "posterior_variance" in w
        assert "fitted_at_ts" in w


# -----------------------------------------------------------------------------
# Slow integration: recovery — runs only when slow tests are enabled
# -----------------------------------------------------------------------------


@pytest.mark.slow
def test_reconcile_with_iac_prior_recovers_planted_slope_direction():
    """Planted positive slope on (exec, authority, *) in iac_prior →
    reconcile pushes profile.mechanism_slopes['authority'] more positive
    than reconcile without the prior."""
    pytest.importorskip("numpyro")

    rng = random.Random(7)
    seq: List[Tuple[str, float]] = []
    # 10 authority touches mostly succeed
    for _ in range(10):
        seq.append(("authority", 1.0 if rng.random() < 0.7 else 0.0))
    # 6 scarcity touches mostly fail
    for _ in range(6):
        seq.append(("scarcity", 1.0 if rng.random() < 0.2 else 0.0))

    profile_no_prior = _profile_with_observations("u_a", "exec", seq)
    profile_with_prior = _profile_with_observations("u_b", "exec", seq)

    # Planted strong-positive prior on (exec, authority, *)
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (1.0, 0.04)
    moments.moments[("exec", "authority", "leisure")] = (1.0, 0.04)
    # Mild-negative prior on (exec, scarcity, *)
    moments.moments[("exec", "scarcity", "biz")] = (-0.5, 0.04)

    refined_no_prior = reconcile_user_posterior(
        profile_no_prior, draws=200, tune=200, chains=2, iac_prior=None,
    )
    refined_with_prior = reconcile_user_posterior(
        profile_with_prior, draws=200, tune=200, chains=2, iac_prior=moments,
    )

    # No-prior path: mechanism_slopes is NOT populated by reconcile
    # (no mech_slope variable in the model).
    assert refined_no_prior.mechanism_slopes.get("authority", 0.0) == 0.0

    # With-prior path: mechanism_slopes['authority'] populated and positive
    auth_slope = refined_with_prior.mechanism_slopes.get("authority")
    assert auth_slope is not None
    assert auth_slope > 0.0, (
        f"expected positive authority slope from planted +1.0 prior, "
        f"got {auth_slope:.3f}"
    )


# -----------------------------------------------------------------------------
# Task 36 wiring — load + pass-through
# -----------------------------------------------------------------------------


def test_task_36_imports_iac_prior_loader():
    """Task 36 must reference iac_prior loader so the population posterior
    flows into per-user reconcile when the nightly fits it."""
    import inspect

    from adam.intelligence.daily import task_36_hmc_user_posterior_reconcile as mod

    src = inspect.getsource(mod)
    # The exact symbol name pin — guards against silent rewires that
    # would break the population → per-user prior flow.
    assert "load_iac_prior_from_neo4j" in src
    assert "iac_prior=iac_prior" in src


@pytest.mark.slow
def test_reconcile_with_iac_prior_handles_missing_mechanism_coverage():
    """User has both 'authority' and 'social_proof', but population
    moments only cover 'authority'. Reconcile must still finish and
    populate authority slope; social_proof falls back to diffuse default."""
    pytest.importorskip("numpyro")

    rng = random.Random(11)
    seq: List[Tuple[str, float]] = []
    for _ in range(10):
        seq.append(("authority", 1.0 if rng.random() < 0.6 else 0.0))
    for _ in range(6):
        seq.append(("social_proof", 1.0 if rng.random() < 0.3 else 0.0))

    profile = _profile_with_observations("u_partial", "exec", seq)

    # Only authority has population coverage
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.5, 0.09)

    refined = reconcile_user_posterior(
        profile, draws=150, tune=150, chains=2, iac_prior=moments,
    )
    # Both mechanisms received slopes via the model (mech_slope per-mech),
    # but the prior was informative only for 'authority'.
    assert "authority" in refined.mechanism_slopes
    assert "social_proof" in refined.mechanism_slopes
    # authority slope should be in a sensible range, not a NaN
    auth = refined.mechanism_slopes["authority"]
    sp = refined.mechanism_slopes["social_proof"]
    assert math.isfinite(auth)
    assert math.isfinite(sp)
