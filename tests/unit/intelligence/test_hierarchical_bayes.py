"""Pin the M3 hierarchical-Bayes substrate.

Discipline anchors:
    - Closes the 'hierarchy declared but not computed' diagnosis: the
      module exposes a real PyMC model and a recovery path from
      posterior moments to Beta(α, β).
    - LibsMissingError raised cleanly when PyMC isn't installed —
      returning None would let TS sample meaningless posteriors.
    - Sigmoid recovery formula for p̂ from γ̂ and Beta(α, β) from p̂ and
      its posterior variance must NOT drift — that's the substrate for
      the entire shrinkage pipeline.
    - pscore_known=true filtering inherits the M1/M2 discipline: the
      hierarchical fit consumes the same logged-propensity-validated
      rows OPE / WCLS / CF do.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.hierarchical_bayes import (
    CellPosterior,
    HierarchicalObservation,
    HierarchyLibsMissingError,
    _HIERARCHY_PRIORS,
    _sigmoid,
    build_hierarchical_model,
    fit_hierarchical_model,
    load_observations_from_neo4j,
    run_nightly_hierarchical_refit,
    write_cell_posterior_to_neo4j,
)


def _obs(arch="status_seeker", mech="social_proof", cat="luxury_transportation",
         success=1) -> HierarchicalObservation:
    return HierarchicalObservation(
        archetype=arch, mechanism=mech, category=cat, success=success,
    )


# -----------------------------------------------------------------------------
# Soft-import gate
# -----------------------------------------------------------------------------


def test_build_raises_libs_missing_when_pymc_unavailable():
    """build_hierarchical_model must raise HierarchyLibsMissingError
    when PyMC isn't installed."""
    obs = [_obs(success=1), _obs(success=0)]
    with patch(
        "adam.intelligence.hierarchical_bayes._try_import_pymc",
        return_value=None,
    ):
        with pytest.raises(HierarchyLibsMissingError):
            build_hierarchical_model(obs)


def test_fit_raises_libs_missing_when_pymc_unavailable():
    obs = [_obs(success=1), _obs(success=0)]
    with patch(
        "adam.intelligence.hierarchical_bayes._try_import_pymc",
        return_value=None,
    ):
        with pytest.raises(HierarchyLibsMissingError):
            fit_hierarchical_model(obs)


def test_build_raises_value_error_on_empty():
    with pytest.raises(ValueError):
        build_hierarchical_model([])


def test_fit_raises_value_error_on_empty():
    with pytest.raises(ValueError):
        fit_hierarchical_model([])


# -----------------------------------------------------------------------------
# Handoff §3.3 priors are canonical
# -----------------------------------------------------------------------------


def test_hierarchy_priors_match_handoff_specification():
    """Handoff §3.3 specifies:
        µ ~ Normal(0, 1.5)
        σ_archetype ~ HalfNormal(0.5)
        σ_demo ~ HalfNormal(0.3)
        σ_ctx ~ HalfNormal(0.2)
    Pin these so a future refactor can't silently shift the
    hierarchy's σ landscape (which controls shrinkage strength)."""
    assert _HIERARCHY_PRIORS["mu_pop_loc"] == 0.0
    assert _HIERARCHY_PRIORS["mu_pop_scale"] == 1.5
    assert _HIERARCHY_PRIORS["sigma_archetype_scale"] == 0.5
    assert _HIERARCHY_PRIORS["sigma_demo_scale"] == 0.3
    assert _HIERARCHY_PRIORS["sigma_ctx_scale"] == 0.2


# -----------------------------------------------------------------------------
# Sigmoid recovery — load-bearing for Beta(α, β) shrinkage
# -----------------------------------------------------------------------------


def test_sigmoid_at_zero_is_half():
    assert _sigmoid(0.0) == 0.5


def test_sigmoid_negative_extreme():
    """Below ~-37, exp underflows to 0; sigmoid → 0 exactly."""
    assert _sigmoid(-100.0) < 1e-10


def test_sigmoid_positive_extreme():
    """Above ~37, exp overflows; sigmoid → 1 exactly."""
    assert _sigmoid(100.0) >= 1.0 - 1e-10


def test_sigmoid_monotonic():
    assert _sigmoid(0.5) > _sigmoid(0.0) > _sigmoid(-0.5)


# -----------------------------------------------------------------------------
# Observation loader — Neo4j unavailable + pscore filtering
# -----------------------------------------------------------------------------


def test_loader_returns_empty_when_driver_unavailable():
    obs = load_observations_from_neo4j(driver=None)
    assert obs == []


def test_loader_filters_pscore_known_when_requested():
    """The pscore_known=true filter is the M1/M2 discipline anchor.
    Pin so a refactor can't silently include reconstructed-propensity
    rows."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)
    session.run = MagicMock(return_value=[])

    load_observations_from_neo4j(driver=driver, pscore_known_only=True)

    cypher = session.run.call_args.args[0]
    assert "dc.pscore_known = true" in cypher


def test_loader_drops_rows_missing_archetype_or_mechanism():
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    # First record is malformed (no mechanism); second is valid
    record_bad = MagicMock()
    record_bad.get = MagicMock(side_effect=lambda k:
        {"archetype": "status_seeker", "mechanism": "", "category": "luxury_transportation",
         "success": 1}.get(k))
    record_good = MagicMock()
    record_good.get = MagicMock(side_effect=lambda k:
        {"archetype": "status_seeker", "mechanism": "social_proof",
         "category": "luxury_transportation", "success": 1}.get(k))
    session.run = MagicMock(return_value=[record_bad, record_good])

    obs = load_observations_from_neo4j(driver=driver)
    assert len(obs) == 1
    assert obs[0].mechanism == "social_proof"


# -----------------------------------------------------------------------------
# Writeback — uses canonical BayesianPrior schema
# -----------------------------------------------------------------------------


def test_writeback_targets_bayesian_prior_node():
    """Posterior writeback must hit :BayesianPrior — the canonical
    storage location TS samples from at request time. A refactor that
    changed the label would break the online sampling path."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    cell = CellPosterior(
        archetype="status_seeker", mechanism="social_proof",
        category="luxury_transportation",
        alpha=12.5, beta=4.5, p_mean=0.74, p_variance=0.01, n_obs=100,
    )
    ok = write_cell_posterior_to_neo4j(cell, driver=driver)
    assert ok is True

    cypher = session.run.call_args.args[0]
    assert "BayesianPrior" in cypher
    assert "bp.alpha = $alpha" in cypher
    assert "bp.beta = $beta" in cypher


def test_writeback_records_provenance():
    """The writeback stamps shrinkage_source so TS / OPE consumers can
    distinguish hierarchically-shrunk priors from independent-cell
    priors during the transition window."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    cell = CellPosterior(
        archetype="x", mechanism="y", category="z",
        alpha=1.0, beta=1.0, p_mean=0.5, p_variance=0.1, n_obs=0,
    )
    write_cell_posterior_to_neo4j(cell, driver=driver)

    cypher = session.run.call_args.args[0]
    assert "shrinkage_source = 'hierarchical_bayes_v1'" in cypher


def test_writeback_returns_false_when_driver_unavailable():
    """When driver=None and the auto-built sync driver also unavailable
    (no NEO4J env vars / unreachable Neo4j), writeback returns False."""
    cell = CellPosterior(
        archetype="x", mechanism="y", category="z",
        alpha=1.0, beta=1.0, p_mean=0.5, p_variance=0.1, n_obs=0,
    )
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        return_value=None,
    ):
        ok = write_cell_posterior_to_neo4j(cell, driver=None)
    assert ok is False


# -----------------------------------------------------------------------------
# Nightly orchestrator
# -----------------------------------------------------------------------------


def test_nightly_returns_error_on_no_observations():
    """When the loader returns [] (no LUXY rows yet), the nightly job
    surfaces 'no observations available' rather than crashing on an
    empty fit."""
    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=[],
    ):
        diag = run_nightly_hierarchical_refit(driver=MagicMock())
    assert diag.cells_recovered == 0
    assert any("no observations" in e for e in diag.errors)


def test_nightly_propagates_libs_missing():
    """When PyMC isn't installed, the nightly job records the error
    in diagnostics rather than crashing. Same discipline as M2."""
    obs = [_obs(success=1), _obs(success=0)]
    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=obs,
    ), patch(
        "adam.intelligence.hierarchical_bayes._try_import_pymc",
        return_value=None,
    ):
        # fit_hierarchical_model raises HierarchyLibsMissingError;
        # nightly should propagate via exception
        with pytest.raises(HierarchyLibsMissingError):
            run_nightly_hierarchical_refit(driver=MagicMock())


# -----------------------------------------------------------------------------
# Slice 4 — δ_iac extract + writeback (closes the FDR loop)
# -----------------------------------------------------------------------------


def test_nightly_writes_iac_moments_when_fit_succeeds():
    """When fit returns idata + observed_triples, the nightly orchestrator
    extracts IacPriorMoments and writes them back. Diagnostic
    iac_triples_written reflects the writeback count."""
    from adam.intelligence.iac_prior import IacPriorMoments
    from adam.intelligence.hierarchical_bayes import FitDiagnostics

    obs = [_obs(success=1), _obs(success=0)]
    fake_cells = [
        CellPosterior(
            archetype="a", mechanism="m", category="c",
            alpha=1.0, beta=1.0, p_mean=0.5, p_variance=0.1, n_obs=2,
        ),
    ]
    fake_diag = FitDiagnostics(cells_recovered=1, fitted_at_ts=1.0)
    fake_idata = MagicMock(name="idata")
    fake_triples = [("a", "m", "c"), ("a", "m", "d")]

    fake_moments = IacPriorMoments(
        moments={
            ("a", "m", "c"): (0.4, 0.04),
            ("a", "m", "d"): (-0.2, 0.04),
        },
        fitted_at_ts=1.0,
    )

    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=obs,
    ), patch(
        "adam.intelligence.hierarchical_bayes.fit_hierarchical_model",
        return_value=(fake_cells, fake_diag, fake_idata, fake_triples),
    ), patch(
        "adam.intelligence.hierarchical_bayes.write_cell_posterior_to_neo4j",
        return_value=True,
    ), patch(
        "adam.intelligence.iac_prior.extract_iac_prior_from_inferencedata",
        return_value=fake_moments,
    ), patch(
        "adam.intelligence.iac_prior.write_iac_posterior_to_neo4j",
        return_value=2,
    ):
        diag = run_nightly_hierarchical_refit(driver=MagicMock())

    assert diag.iac_triples_written == 2
    assert not any("iac_prior writeback" in e for e in diag.errors)


def test_nightly_skips_iac_writeback_when_idata_none():
    """Sampler failure path returns idata=None → writeback is skipped;
    iac_triples_written stays at 0; no error appended."""
    from adam.intelligence.hierarchical_bayes import FitDiagnostics

    obs = [_obs(success=1)]
    fake_diag = FitDiagnostics()
    fake_diag.errors.append("NUTS sampler failed: synthetic")

    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=obs,
    ), patch(
        "adam.intelligence.hierarchical_bayes.fit_hierarchical_model",
        return_value=([], fake_diag, None, []),
    ):
        diag = run_nightly_hierarchical_refit(driver=MagicMock())

    assert diag.iac_triples_written == 0
    # Sampler error preserved; no extra writeback error appended.
    assert any("NUTS" in e for e in diag.errors)
    assert not any("iac_prior writeback" in e for e in diag.errors)


def test_nightly_skips_iac_writeback_when_no_triples():
    """observed_triples=[] (no observed (a, m, c) cells in fit) → skip."""
    from adam.intelligence.hierarchical_bayes import FitDiagnostics

    obs = [_obs(success=1)]
    fake_diag = FitDiagnostics(cells_recovered=0)

    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=obs,
    ), patch(
        "adam.intelligence.hierarchical_bayes.fit_hierarchical_model",
        return_value=([], fake_diag, MagicMock(), []),
    ):
        diag = run_nightly_hierarchical_refit(driver=MagicMock())

    assert diag.iac_triples_written == 0


def test_nightly_soft_fails_iac_extract_failure():
    """extract_iac_prior_from_inferencedata raising → writeback skipped;
    error appended to diag.errors but cells were already written."""
    from adam.intelligence.hierarchical_bayes import FitDiagnostics

    obs = [_obs(success=1)]
    fake_cells = [
        CellPosterior(
            archetype="a", mechanism="m", category="c",
            alpha=1.0, beta=1.0, p_mean=0.5, p_variance=0.1, n_obs=1,
        ),
    ]
    fake_diag = FitDiagnostics(cells_recovered=1)

    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=obs,
    ), patch(
        "adam.intelligence.hierarchical_bayes.fit_hierarchical_model",
        return_value=(fake_cells, fake_diag, MagicMock(), [("a", "m", "c")]),
    ), patch(
        "adam.intelligence.hierarchical_bayes.write_cell_posterior_to_neo4j",
        return_value=True,
    ), patch(
        "adam.intelligence.iac_prior.extract_iac_prior_from_inferencedata",
        side_effect=RuntimeError("malformed idata"),
    ):
        diag = run_nightly_hierarchical_refit(driver=MagicMock())

    assert diag.iac_triples_written == 0
    assert any("iac_prior writeback" in e for e in diag.errors)


def test_nightly_skips_iac_writeback_when_moments_empty():
    """Empty IacPriorMoments → writeback not invoked; counter stays 0."""
    from adam.intelligence.iac_prior import IacPriorMoments
    from adam.intelligence.hierarchical_bayes import FitDiagnostics

    obs = [_obs(success=1)]
    fake_cells = [
        CellPosterior(
            archetype="a", mechanism="m", category="c",
            alpha=1.0, beta=1.0, p_mean=0.5, p_variance=0.1, n_obs=1,
        ),
    ]
    fake_diag = FitDiagnostics(cells_recovered=1)

    with patch(
        "adam.intelligence.hierarchical_bayes.load_observations_from_neo4j",
        return_value=obs,
    ), patch(
        "adam.intelligence.hierarchical_bayes.fit_hierarchical_model",
        return_value=(fake_cells, fake_diag, MagicMock(), [("a", "m", "c")]),
    ), patch(
        "adam.intelligence.hierarchical_bayes.write_cell_posterior_to_neo4j",
        return_value=True,
    ), patch(
        "adam.intelligence.iac_prior.extract_iac_prior_from_inferencedata",
        return_value=IacPriorMoments(),
    ) as mock_extract, patch(
        "adam.intelligence.iac_prior.write_iac_posterior_to_neo4j",
        return_value=99,  # would-be count if write was called
    ) as mock_write:
        diag = run_nightly_hierarchical_refit(driver=MagicMock())

    assert diag.iac_triples_written == 0
    mock_extract.assert_called_once()
    # write should NOT be called when moments.is_empty()
    mock_write.assert_not_called()
