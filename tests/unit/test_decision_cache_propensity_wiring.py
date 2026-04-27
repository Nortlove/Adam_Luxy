"""Pin propensity persistence — DecisionContext → Neo4j metadata + first-class props.

Discipline anchors:
    - Propensity must land on DecisionContext as first-class fields,
      NOT just inside metadata_json. OPE/WCLS queries need to filter
      WHERE dc.pscore_known = true without parsing JSON.
    - When p_t_known=False, ts_propensity and epsilon_floor on the
      Neo4j node MUST be null — not 0.0. A 0.0 sentinel would silently
      corrupt aggregates like AVG(ts_propensity), and 1/p_t weights
      would zero-divide. This matches the M4 migration's discipline.
    - to_outcome_metadata() carries propensity into the JSON blob so
      late-arriving outcomes (after cache eviction) can still read it.
"""

from __future__ import annotations

from adam.api.stackadapt.decision_cache import DecisionContext


def test_decision_context_carries_propensity_fields():
    """The dataclass exposes propensity as first-class fields."""
    ctx = DecisionContext(
        decision_id="d1", archetype="status_seeker",
        mechanism_sent="social_proof",
        ts_propensity=0.97, epsilon_floor=0.02, p_t_known=True,
    )
    assert ctx.ts_propensity == 0.97
    assert ctx.epsilon_floor == 0.02
    assert ctx.p_t_known is True


def test_decision_context_default_p_t_known_false():
    """Conservative default: pre-rewire callers see p_t_known=False so
    OPE/WCLS exclude their rows. Same discipline as the M4 migration."""
    ctx = DecisionContext(decision_id="d1")
    assert ctx.p_t_known is False
    assert ctx.ts_propensity == 0.0


def test_outcome_metadata_includes_propensity():
    """The outcome handler reads metadata_json to recover decision context
    after cache eviction. Propensity must be in the blob."""
    ctx = DecisionContext(
        decision_id="d1", mechanism_sent="social_proof",
        ts_propensity=0.97, epsilon_floor=0.02, p_t_known=True,
    )
    md = ctx.to_outcome_metadata()
    assert md["ts_propensity"] == 0.97
    assert md["epsilon_floor"] == 0.02
    assert md["pscore_known"] is True


def test_outcome_metadata_uses_pscore_known_field_name():
    """The outcome metadata uses pscore_known (matching the M4 :AdDecision
    schema property), not p_t_known. The DecisionContext attribute is
    p_t_known internally; metadata exposes pscore_known to downstream
    consumers (OPE estimator suite, Neo4j queries)."""
    ctx = DecisionContext(decision_id="d1", p_t_known=True)
    md = ctx.to_outcome_metadata()
    assert "pscore_known" in md
    # Internal attribute name doesn't leak as the metadata key
    assert "p_t_known" not in md
