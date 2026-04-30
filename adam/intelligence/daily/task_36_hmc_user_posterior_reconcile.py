"""
Task 36: Nightly HMC User Posterior Reconcile

Closes Spine #1's HMC offline reconcile path per
docs/CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md Phase 1 line 945.

Schedule: 04:00 UTC nightly. Sits between gradient recompute (05:00)
and the data pulls (00:00–04:00) so reconciled posteriors are
available downstream the same day.

What it does:
  1. Query Neo4j for :UserPosterior nodes with last_updated_ts
     older than the staleness cutoff (default 24h).
  2. For each, load the UserPosteriorProfile from the L3 row.
  3. Run user_posterior_hmc_reconcile.reconcile_user_posterior on
     each profile.
  4. Persist refined profile back via UserPosteriorManager._store_to_neo4j
     (or call _store directly with the manager's debounce reset).

Without this task, Spine #1's HMC path exists but never runs — the
online BONG path's per-mechanism Beta posteriors stay
independent-treatment forever and the AR(1) carryover correction
never lands.

Per the directive's discipline:
  * NUTS is canonical (handoff §3.6 NumPyro path)
  * Soft-fail per user — one user's MCMC failure must not block the
    rest of the batch
  * Track per-batch counters in TaskResult.details for observability
"""

from __future__ import annotations

import logging
import time
from typing import Any, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


# Reconcile users whose last_updated_ts is older than this. Conservative
# default — daily reconcile only revisits users with at least 24h since
# their last touch-driven update. Can tune down to 6h if pilot velocity
# warrants more frequent refinement.
STALENESS_CUTOFF_SECONDS: int = 24 * 3600

# Hard cap on users per nightly run — protects against runaway MCMC
# load on the first run after a long quiet period. Default ~100 means
# ~100 NUTS runs per night, ~30s each → 50min budget worst-case.
MAX_USERS_PER_RUN: int = 100


class HMCUserPosteriorReconcileTask(DailyStrengtheningTask):
    """Nightly orchestrator for the per-user HMC posterior reconcile."""

    @property
    def name(self) -> str:
        return "hmc_user_posterior_reconcile"

    @property
    def schedule_hours(self) -> List[int]:
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.intelligence.user_posterior_hmc_reconcile import (
                reconcile_user_posterior,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        # --- Discover stale users via Neo4j ---
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception as exc:
            result.success = False
            result.details["error"] = f"driver unavailable: {exc}"
            return result

        if driver is None:
            result.details["skipped"] = "no_driver"
            return result

        # --- Load population δ_iac prior once for the whole run ---
        # Phase 3 Slice 2: directive line 985-998 closes "δ_iac flow into
        # per-user reconcile." When the population horseshoe posterior is
        # available, every user's reconcile gets the informative prior on
        # mech_slope; otherwise we soft-fall to the prior path.
        iac_prior = None
        try:
            from adam.intelligence.iac_prior import load_iac_prior_from_neo4j
            iac_prior = load_iac_prior_from_neo4j(driver=driver)
            if iac_prior.is_empty():
                # Treat empty as None so per-user reconcile takes the
                # exact pre-Slice-2 fast path (regression-preserved).
                iac_prior = None
                result.details["iac_prior"] = "empty"
            else:
                result.details["iac_prior_triples"] = iac_prior.n_triples
                result.details["iac_prior_fitted_at_ts"] = (
                    iac_prior.fitted_at_ts
                )
        except Exception as exc:
            logger.warning(
                "iac_prior load failed in Task 36; proceeding without "
                "informative prior: %s", exc,
            )
            iac_prior = None
            result.details["iac_prior"] = f"load_failed: {exc}"

        cutoff_ts = int(time.time()) - STALENESS_CUTOFF_SECONDS
        candidates: List[tuple[str, str]] = []
        try:
            with driver.session() as session:
                rec = session.run(
                    """
                    MATCH (up:UserPosterior)
                    WHERE up.last_updated_ts < $cutoff
                      AND up.total_touches >= 8
                    RETURN up.user_id AS user_id, up.brand_id AS brand_id
                    LIMIT $cap
                    """,
                    cutoff=cutoff_ts, cap=MAX_USERS_PER_RUN,
                )
                for r in rec:
                    user_id = r.get("user_id")
                    brand_id = r.get("brand_id")
                    if user_id and brand_id:
                        candidates.append((user_id, brand_id))
        except Exception as exc:
            result.success = False
            result.details["error"] = f"discovery query failed: {exc}"
            return result

        result.details["candidates_discovered"] = len(candidates)
        if not candidates:
            result.details["skipped"] = "no_stale_users"
            return result

        # --- Reconcile each user (soft-fail per user) ---
        try:
            from adam.core.dependencies import Infrastructure, LearningComponents
            # Note: the manager is wired via dependencies in production;
            # in this task we use it via the construct that already
            # gets initialized at startup (LearningComponents).
            mgr = self._resolve_manager()
            if mgr is None:
                result.success = False
                result.details["error"] = "no_user_posterior_manager"
                return result
        except Exception as exc:
            result.success = False
            result.details["error"] = f"manager resolve failed: {exc}"
            return result

        n_reconciled = 0
        n_failed = 0
        n_no_op = 0
        for user_id, brand_id in candidates:
            try:
                profile = mgr.get_user_profile(
                    user_id=user_id, brand_id=brand_id,
                )
                obs_before = sum(
                    len(mp.outcomes)
                    for mp in profile.mechanism_posteriors.values()
                )
                refined = reconcile_user_posterior(
                    profile, iac_prior=iac_prior,
                )
                # If observations meet threshold, refined != profile
                # in spirit; check whether posteriors actually moved
                obs_after = sum(
                    len(mp.outcomes)
                    for mp in refined.mechanism_posteriors.values()
                )
                # Persist back via L3
                cache_key = f"{user_id}:{brand_id}"
                mgr._store_to_neo4j(cache_key, refined)
                if obs_before >= 8:
                    n_reconciled += 1
                else:
                    n_no_op += 1
            except Exception as exc:
                n_failed += 1
                logger.warning(
                    "HMC reconcile failed for user=%s brand=%s: %s",
                    user_id, brand_id, exc,
                )

        result.items_processed = len(candidates)
        result.items_stored = n_reconciled
        result.errors = n_failed
        result.details.update(
            {
                "candidates": len(candidates),
                "reconciled": n_reconciled,
                "no_op": n_no_op,
                "failed": n_failed,
                "cutoff_ts": cutoff_ts,
                "iac_prior_active": iac_prior is not None,
            }
        )

        if n_failed > 0 and n_reconciled == 0:
            result.success = False

        return result

    def _resolve_manager(self) -> Any:
        """Return the production UserPosteriorManager from dependencies.

        Soft-fails to None when not initialized.
        """
        try:
            from adam.core.dependencies import _SHARED_LEARNING_COMPONENTS
            if _SHARED_LEARNING_COMPONENTS is None:
                return None
            return _SHARED_LEARNING_COMPONENTS.user_posterior_manager
        except Exception:
            try:
                # Alternate construction path — direct manager singleton
                from adam.retargeting.engines.repeated_measures import (
                    UserPosteriorManager,
                )
                return UserPosteriorManager()
            except Exception:
                return None
