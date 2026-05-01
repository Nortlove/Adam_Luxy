"""
Task 34: Nightly Hierarchical Bayes Refit

Schedules ``run_nightly_hierarchical_refit`` per Seven-Component
Methodological Upgrade Handoff §3.5. Without this, the
(archetype × mechanism × category) posteriors that the cascade reads
stay frozen at last-fit values; per-cell learning never closes.

Schedule: 02:00 UTC nightly. Sits between the data-pull tasks
(00:00–04:00) and the gradient-recompute task (05:00) so refit
posteriors are available downstream the same cycle.

Audit reference: CODEBASE_AUDIT_2026_04_29.md §6 — "Schedule
run_nightly_hierarchical_refit() as a job."

KNOCKOFF-FDR WIRING (added 2026-05-01)
--------------------------------------

Before invoking the refit, the task loads the prior horseshoe fit's
``IacPriorMoments`` (``adam.intelligence.iac_prior``) from Neo4j and
runs ``select_pre_specified_for_next_fit`` (BH-style FDR per
``adam.intelligence.iac_fdr_selection``) at the canonical 0.10 target.
The resulting list of (archetype, mechanism, category) triples is
passed to ``run_nightly_hierarchical_refit`` as
``pre_specified_interactions`` — these triples bypass the horseshoe
shrinkage with a wider Normal(0, 1.0) prior, so the system's belief
about which interactions exist iteratively tightens night-over-night.

First run (no prior horseshoe fit) → empty IacPriorMoments → empty
selection → pre_specified_interactions stays None → original
behavior preserved. Iterative behavior turns on once the first
interaction-aware fit produces moments.

Citation: directive line 988 ("Knockoff-filter FDR control on which
interactions are non-zero") + Phase 6 line 1055 ("Knockoff-filter
FDR control wired").

Discipline (B3-LUXY a/b/c/d):
    (a) The fit math lives in hierarchical_bayes.py; the FDR math
        lives in iac_fdr_selection.py; this task is the scheduling
        wrapper that composes them. No re-implementation of either.
    (b) Regression: see test_task_34_hierarchical_bayes_refit.py.
        Existing tests pin: skip-when-no-driver, skip-when-no-
        observations, success path records r̂_max + cells_written.
        FDR-wiring tests pin: empty IacPriorMoments → refit called
        with pre_specified=None; non-empty moments → refit called
        with FDR-selected triples; load failure → soft-fail
        (refit still runs without pre_specified).
    (c) calibration_pending=False on cadence; calibration_pending=True
        on FDR target (0.10 default; LUXY pilot may tighten — A14 flag
        on iac_fdr_selection.DEFAULT_FDR_TARGET).
    (d) Honest tag — the task swallows fit-level errors into
        TaskResult.details rather than raising, matching every other
        daily task's contract. The FDR wiring is purely additive: any
        failure in the FDR load / selection chain logs a warning and
        falls through to the original (no-FDR) refit path.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class HierarchicalBayesRefitTask(DailyStrengtheningTask):
    """Nightly orchestrator for the per-cell hierarchical posterior refit."""

    @property
    def name(self) -> str:
        return "hierarchical_bayes_refit"

    @property
    def schedule_hours(self) -> List[int]:
        return [2]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.intelligence.hierarchical_bayes import (
                run_nightly_hierarchical_refit,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        # Knockoff-FDR wiring — load prior horseshoe IacPriorMoments
        # from Neo4j and run BH-style FDR selection at q=0.10. The
        # resulting (archetype, mechanism, category) triples bypass
        # horseshoe shrinkage in the next refit (directive line 988
        # + Phase 6 line 1055). Soft-fail by design: any failure in
        # the FDR chain falls through to pre_specified=None, which
        # preserves the original (no-FDR) refit path. First run
        # (no prior horseshoe fit) hits the empty-moments branch and
        # produces an empty selection — same code path.
        pre_specified: Optional[List[Tuple[str, str, str]]] = None
        try:
            from adam.intelligence.iac_fdr_selection import (
                select_pre_specified_for_next_fit,
            )
            from adam.intelligence.iac_prior import load_iac_prior_from_neo4j

            moments = load_iac_prior_from_neo4j()
            if not moments.is_empty():
                pre_specified = select_pre_specified_for_next_fit(moments)
                result.details["fdr_n_candidates"] = moments.n_triples
                result.details["fdr_n_selected"] = len(pre_specified)
            else:
                result.details["fdr_n_candidates"] = 0
                result.details["fdr_n_selected"] = 0
        except Exception as exc:
            logger.warning(
                "Task 34 FDR-load skipped (refit will run without "
                "pre-specified interactions): %s", exc,
            )
            result.details["fdr_load_warning"] = str(exc)

        try:
            diag = run_nightly_hierarchical_refit(
                days_lookback=90,
                pre_specified_interactions=pre_specified,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"refit failed: {exc}"
            return result

        cells_recovered = int(getattr(diag, "cells_recovered", 0) or 0)
        r_hat_max = float(getattr(diag, "r_hat_max", 0.0) or 0.0)
        divergences = int(getattr(diag, "divergences", 0) or 0)
        ess_bulk_min = float(getattr(diag, "ess_bulk_min", 0.0) or 0.0)
        errors = list(getattr(diag, "errors", []) or [])
        iac_triples_written = int(getattr(diag, "iac_triples_written", 0) or 0)

        result.items_processed = cells_recovered
        result.items_stored = cells_recovered
        result.errors = len(errors)
        # Preserve fdr_* keys already on result.details from the
        # FDR-load branch above; merge fit diagnostics on top.
        result.details.update({
            "cells_recovered": cells_recovered,
            "r_hat_max": r_hat_max,
            "divergences": divergences,
            "ess_bulk_min": ess_bulk_min,
            "fit_errors": errors[:10],  # cap details payload
            # Slice 4: δ_iac writeback diagnostic. Closes the FDR loop
            # — these triples become tomorrow's IacPriorMoments load.
            "iac_triples_written": iac_triples_written,
        })

        # Diagnostic flags — surface but don't fail the task
        if r_hat_max > 1.01:
            result.details["warning_r_hat"] = (
                f"r_hat_max={r_hat_max:.3f} > 1.01 (chains may not have converged)"
            )
        if divergences:
            result.details["warning_divergences"] = divergences

        if errors and cells_recovered == 0:
            # Total failure — no posteriors recovered
            result.success = False

        return result
