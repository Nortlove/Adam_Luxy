"""Pin Phase 3 — δ_iac horseshoe interaction tensor in hierarchical_bayes.

Directive Phase 3 line 985-988. Tests pin:
  * Model builds with horseshoe + non-shrinkage prior on pre-specified slots
  * Interaction index covers all (archetype, mechanism, category) triples
    with at least one observation; pre-specified triples outside the data
    are silently dropped
  * Horseshoe-only model (no pre-specified) still builds correctly
  * On synthetic data with a planted strong interaction, the horseshoe
    posterior over delta_iac concentrates the mass on that slot

Slow-path NUTS test gated by @pytest.mark.slow.
"""

from __future__ import annotations

import math
import random

import pytest

# Soft import — these tests are meaningful only when PyMC is installed
pymc = pytest.importorskip("pymc")
np = pytest.importorskip("numpy")

from adam.intelligence.hierarchical_bayes import (
    HierarchicalObservation,
    build_hierarchical_model,
    build_hierarchical_model_with_interactions,
)


def _synthetic_observations(
    *,
    n_per_cell: int = 8,
    interaction_lift: float = 0.3,
    seed: int = 42,
):
    """Generate (archetype × mechanism × category) observations with
    one planted strong interaction at (exec, authority, biz)."""
    rng = random.Random(seed)
    obs = []
    for arc in ["exec", "pro"]:
        for mech in ["authority", "social_proof", "scarcity"]:
            for cat in ["biz", "leisure"]:
                base_p = 0.5
                if arc == "exec" and mech == "authority" and cat == "biz":
                    p = base_p + interaction_lift  # planted lift
                else:
                    p = base_p
                for _ in range(n_per_cell):
                    y = 1 if rng.random() < p else 0
                    obs.append(HierarchicalObservation(arc, mech, cat, y))
    return obs


# -----------------------------------------------------------------------------
# Model build / structure pin
# -----------------------------------------------------------------------------


def test_horseshoe_model_builds_with_no_pre_specified():
    """No pre-specified triples → all interactions go through horseshoe.
    The model must contain tau_iac, lambda_iac, delta_iac."""
    obs = _synthetic_observations()
    model, coords, triples = build_hierarchical_model_with_interactions(obs)
    assert "tau_iac" in model.named_vars
    assert "lambda_iac" in model.named_vars
    assert "delta_iac" in model.named_vars
    assert "delta_iac_scale" in model.named_vars
    # All 12 cells observed → 12 interaction slots
    assert len(triples) == 12
    assert len(coords["interaction"]) == 12


def test_horseshoe_model_builds_with_pre_specified():
    """Pre-specified triple → that slot uses non-shrinkage scale.
    Verified by structure: the is_prespecified mask is in named_vars."""
    obs = _synthetic_observations()
    pre = [("exec", "authority", "biz")]
    model, coords, triples = build_hierarchical_model_with_interactions(
        obs, pre_specified_interactions=pre,
    )
    assert "is_prespecified" in model.named_vars
    # The pre-specified triple must be in the interaction index
    assert ("exec", "authority", "biz") in triples


def test_horseshoe_silently_drops_pre_specified_outside_observed_data():
    """Pre-specifying an interaction with zero observations → silently
    dropped (no slot to estimate against). This protects the model
    from being polluted by impossible interactions."""
    obs = _synthetic_observations()
    # 'phantom' archetype doesn't exist in obs
    pre = [
        ("exec", "authority", "biz"),  # exists
        ("phantom", "authority", "biz"),  # does not — must drop
    ]
    model, coords, triples = build_hierarchical_model_with_interactions(
        obs, pre_specified_interactions=pre,
    )
    # phantom not in observed data, so not in triples
    assert ("phantom", "authority", "biz") not in triples
    # Real one still in
    assert ("exec", "authority", "biz") in triples


def test_horseshoe_interaction_coords_are_pipe_joined():
    """Coord labels are deterministic 'archetype|mechanism|category'
    strings — so consumers can deserialize without separate metadata."""
    obs = _synthetic_observations()
    _, coords, _ = build_hierarchical_model_with_interactions(obs)
    for label in coords["interaction"]:
        assert label.count("|") == 2


def test_horseshoe_rejects_empty_observations():
    with pytest.raises(ValueError):
        build_hierarchical_model_with_interactions([])


# -----------------------------------------------------------------------------
# Backbone preserved (smoke test that the new function doesn't break
# the existing hierarchical_bayes API contract)
# -----------------------------------------------------------------------------


def test_existing_build_hierarchical_model_still_works():
    """The old build_hierarchical_model must still produce a valid model
    — the horseshoe extension is additive, not a replacement."""
    obs = _synthetic_observations()
    model, coords = build_hierarchical_model(obs)
    assert "gamma_ctx" in model.named_vars
    assert "y_obs" in model.named_vars
    # And the new horseshoe vars are NOT in the old model
    assert "delta_iac" not in model.named_vars
    assert "tau_iac" not in model.named_vars


# -----------------------------------------------------------------------------
# NUTS sampling — slow integration test for posterior recovery
# -----------------------------------------------------------------------------


@pytest.mark.slow
def test_horseshoe_recovers_planted_interaction_above_noise_floor():
    """End-to-end: synthetic data with one planted strong interaction
    → horseshoe NUTS recovers a delta_iac posterior mean for that slot
    that's larger in magnitude than the median across the other 11
    slots. (We don't check exact magnitudes because NUTS with 200 draws
    is noisy on small synthetic data; we check the SIGNAL ordering.)
    """
    obs = _synthetic_observations(n_per_cell=20, interaction_lift=0.4)
    model, coords, triples = build_hierarchical_model_with_interactions(obs)
    planted_idx = triples.index(("exec", "authority", "biz"))

    with model:
        idata = pymc.sample(
            draws=200, tune=200, chains=2,
            target_accept=0.95,
            nuts_sampler="numpyro",
            progressbar=False,
            return_inferencedata=True,
        )

    delta_post = idata.posterior["delta_iac"]
    delta_mean = delta_post.mean(dim=("chain", "draw")).values  # shape (n_iac,)

    planted_magnitude = abs(float(delta_mean[planted_idx]))
    other_magnitudes = [
        abs(float(delta_mean[i])) for i in range(len(triples)) if i != planted_idx
    ]
    median_other = float(np.median(other_magnitudes))

    # The planted interaction must have larger posterior magnitude
    # than the median of the other (shrunk-toward-zero) slots.
    assert planted_magnitude > median_other, (
        f"horseshoe failed to lift planted interaction: "
        f"|planted|={planted_magnitude:.3f} median_other={median_other:.3f}"
    )
