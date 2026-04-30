"""Pin the Neo4j L3 tier for UserPosteriorManager — directive Phase 1
"Storage schema in Neo4j (UserPosterior node), Redis hot cache."

The manager's docstring documented L3 since session 36-10 but never
implemented it. This test pins the contract: write a UserPosteriorProfile
through the manager, verify the :UserPosterior Neo4j node carries the
expected payload, read it back through the manager when L1+L2 are cold.

Tests use mocked Neo4j driver (no live connection required for unit
suite — the in-process state machine is what we're pinning). The full
end-to-end against local Neo4j is exercised by the migration's
verification query in 030_user_posterior_storage.cypher.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from adam.retargeting.engines.repeated_measures import (
    NEO4J_DEBOUNCE_EVERY_N_UPDATES,
    USER_POSTERIOR_SCHEMA_VERSION,
    UserPosteriorManager,
)
from adam.retargeting.models.within_subject import UserPosteriorProfile


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _stubbed_session(rec=None):
    """Build a context-manager session whose .run().single() returns rec."""
    session = MagicMock()
    session_ctx = MagicMock()
    session.__enter__ = MagicMock(return_value=session_ctx)
    session.__exit__ = MagicMock(return_value=None)
    result = MagicMock()
    result.single = MagicMock(return_value=rec)
    session_ctx.run = MagicMock(return_value=result)
    return session, session_ctx


def _driver_with_session(session):
    driver = MagicMock()
    driver.session = MagicMock(return_value=session)
    return driver


# -----------------------------------------------------------------------------
# L3 load — Neo4j miss
# -----------------------------------------------------------------------------


def test_l3_load_missing_returns_none():
    """No :UserPosterior row → load returns None → falls back to cold-start."""
    session, _ = _stubbed_session(rec=None)
    driver = _driver_with_session(session)
    mgr = UserPosteriorManager(neo4j_driver=driver)
    result = mgr._load_from_neo4j("u_missing", "luxy")
    assert result is None


def test_l3_load_no_driver_returns_none():
    """No driver injected and no fallback available → None (soft-fail)."""
    mgr = UserPosteriorManager(neo4j_driver=None)
    # Patch the lazy-fallback to simulate no driver
    mgr._resolve_neo4j_driver = lambda: None
    assert mgr._load_from_neo4j("u", "b") is None


def test_l3_load_round_trips_pydantic_json():
    """A row with valid posterior_json → reconstitutes UserPosteriorProfile."""
    profile_in = UserPosteriorProfile(
        user_id="u_round_trip",
        brand_id="luxy",
        archetype_id="professionals",
        total_touches_observed=12,
        total_reward_sum=4.5,
    )
    rec = {"posterior_json": profile_in.model_dump_json()}
    session, _ = _stubbed_session(rec=rec)
    driver = _driver_with_session(session)
    mgr = UserPosteriorManager(neo4j_driver=driver)

    profile_out = mgr._load_from_neo4j("u_round_trip", "luxy")
    assert profile_out is not None
    assert profile_out.user_id == "u_round_trip"
    assert profile_out.archetype_id == "professionals"
    assert profile_out.total_touches_observed == 12
    assert profile_out.total_reward_sum == 4.5


def test_l3_load_malformed_json_returns_none():
    """Corrupt JSON → graceful None, not exception."""
    rec = {"posterior_json": "not valid json {{{"}
    session, _ = _stubbed_session(rec=rec)
    driver = _driver_with_session(session)
    mgr = UserPosteriorManager(neo4j_driver=driver)
    assert mgr._load_from_neo4j("u", "b") is None


# -----------------------------------------------------------------------------
# L3 store
# -----------------------------------------------------------------------------


def test_l3_store_calls_merge_with_full_payload():
    """_store_to_neo4j MERGEs on (user_id, brand_id) with full Pydantic JSON."""
    session, session_ctx = _stubbed_session(rec=None)
    driver = _driver_with_session(session)
    mgr = UserPosteriorManager(neo4j_driver=driver)

    profile = UserPosteriorProfile(
        user_id="u_persist",
        brand_id="luxy",
        archetype_id="executives",
        total_touches_observed=7,
        total_reward_sum=3.0,
    )
    mgr._store_to_neo4j("u_persist:luxy", profile)

    # Verify the Cypher was MERGE-keyed on user_id + brand_id
    session_ctx.run.assert_called_once()
    args, kwargs = session_ctx.run.call_args
    cypher = args[0]
    assert "MERGE (up:UserPosterior" in cypher
    assert "user_id: $user_id" in cypher
    assert "brand_id: $brand_id" in cypher
    # Verify denormalized fields land on the node for HMC reconcile
    assert "up.total_touches = $total_touches" in cypher
    assert "up.last_updated_ts = $last_updated_ts" in cypher
    assert "up.schema_version = $schema_version" in cypher
    # Verify payload
    assert kwargs["user_id"] == "u_persist"
    assert kwargs["brand_id"] == "luxy"
    assert kwargs["archetype_id"] == "executives"
    assert kwargs["total_touches"] == 7
    assert kwargs["total_reward"] == 3.0
    assert kwargs["schema_version"] == USER_POSTERIOR_SCHEMA_VERSION
    # JSON payload is parseable back into the same shape
    round_trip = UserPosteriorProfile.model_validate_json(
        kwargs["posterior_json"],
    )
    assert round_trip.user_id == profile.user_id


def test_l3_store_no_driver_is_silent_no_op():
    """No Neo4j driver → silent no-op, not exception."""
    mgr = UserPosteriorManager(neo4j_driver=None)
    mgr._resolve_neo4j_driver = lambda: None
    profile = UserPosteriorProfile(user_id="u", brand_id="b", archetype_id="a")
    mgr._store_to_neo4j("u:b", profile)  # MUST NOT RAISE


def test_l3_store_neo4j_exception_is_silent():
    """Any Neo4j-side exception (network, schema mismatch) is logged + swallowed."""
    session, session_ctx = _stubbed_session(rec=None)
    session_ctx.run = MagicMock(side_effect=RuntimeError("Neo4j down"))
    driver = _driver_with_session(session)
    mgr = UserPosteriorManager(neo4j_driver=driver)
    profile = UserPosteriorProfile(user_id="u", brand_id="b", archetype_id="a")
    # MUST NOT RAISE
    mgr._store_to_neo4j("u:b", profile)


# -----------------------------------------------------------------------------
# Debounced write — directive's "permanent, debounced writes"
# -----------------------------------------------------------------------------


def test_debounced_write_persists_only_every_n_updates():
    """The debounce counter MUST persist Neo4j only every Nth update.

    L1+L2 absorb the per-touch load; L3 is durable + lower-frequency.
    """
    session, session_ctx = _stubbed_session(rec=None)
    driver = _driver_with_session(session)

    # Use a stub prior_manager so update_user_posterior doesn't hit
    # real population state.
    class _StubPrior:
        def get_effective_posterior(self, mechanism, barrier, archetype, context):
            from adam.retargeting.engines.prior_manager import (
                BarrierConditionedPosterior,
            )
            return BarrierConditionedPosterior(
                mechanism=mechanism, barrier=barrier or "", archetype="a",
                level="campaign", alpha=2.0, beta=2.0, context_key="",
            )

    mgr = UserPosteriorManager(prior_manager=_StubPrior(), neo4j_driver=driver)

    # Run NEO4J_DEBOUNCE_EVERY_N_UPDATES updates — only the last
    # should trigger a Neo4j write.
    for i in range(NEO4J_DEBOUNCE_EVERY_N_UPDATES):
        mgr.update_user_posterior(
            user_id="u_debounce", brand_id="luxy",
            mechanism="social_proof", barrier="trust",
            archetype_id="professionals", reward=0.5,
            touch_position=i + 1,
        )

    # Exactly one MERGE :UserPosterior write across N updates.
    # session.run is also called by the L3 cold-start load on the first
    # update — count only the persist (MERGE) cypher invocations.
    write_calls = [
        c for c in session_ctx.run.call_args_list
        if "MERGE (up:UserPosterior" in c.args[0]
    ]
    assert len(write_calls) == 1, (
        f"Expected 1 Neo4j write per {NEO4J_DEBOUNCE_EVERY_N_UPDATES} "
        f"updates, got {len(write_calls)}"
    )


def test_debounce_counter_resets_after_persist():
    """After the debounce fires, the counter resets — next persist is
    another N updates away."""
    session, session_ctx = _stubbed_session(rec=None)
    driver = _driver_with_session(session)

    class _StubPrior:
        def get_effective_posterior(self, mechanism, barrier, archetype, context):
            from adam.retargeting.engines.prior_manager import (
                BarrierConditionedPosterior,
            )
            return BarrierConditionedPosterior(
                mechanism=mechanism, barrier=barrier or "", archetype="a",
                level="campaign", alpha=2.0, beta=2.0, context_key="",
            )

    mgr = UserPosteriorManager(prior_manager=_StubPrior(), neo4j_driver=driver)

    # 2 × N updates → exactly 2 persists
    for i in range(2 * NEO4J_DEBOUNCE_EVERY_N_UPDATES):
        mgr.update_user_posterior(
            user_id="u_resets", brand_id="luxy",
            mechanism="social_proof", barrier="trust",
            archetype_id="professionals", reward=0.5,
            touch_position=i + 1,
        )
    write_calls = [
        c for c in session_ctx.run.call_args_list
        if "MERGE (up:UserPosterior" in c.args[0]
    ]
    assert len(write_calls) == 2


# -----------------------------------------------------------------------------
# get_user_profile — L3 promotion when L1+L2 cold
# -----------------------------------------------------------------------------


def test_get_user_profile_promotes_from_l3_when_l1_l2_cold():
    """Cold L1+L2, hot L3 → load from Neo4j, promote into L1+L2."""
    profile_in = UserPosteriorProfile(
        user_id="u_promote", brand_id="luxy", archetype_id="professionals",
        total_touches_observed=42,
    )
    rec = {"posterior_json": profile_in.model_dump_json()}
    session, _ = _stubbed_session(rec=rec)
    driver = _driver_with_session(session)
    mgr = UserPosteriorManager(neo4j_driver=driver)

    result = mgr.get_user_profile(
        user_id="u_promote", brand_id="luxy", archetype_id="professionals",
    )
    assert result.total_touches_observed == 42
    # And it's now in L1
    assert "u_promote:luxy" in mgr._profiles
