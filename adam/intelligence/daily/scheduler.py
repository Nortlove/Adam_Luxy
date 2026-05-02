"""
Daily Intelligence Strengthening + Campaign Intelligence Scheduler
====================================================================

Orchestrates execution of 22 strengthening tasks + 10 DCIL tasks.

Strengthening DAG (Tasks 1-22):
    01:00 Task 5 (Reviews) ─────────────┐
    02:00 Task 2 (Publisher Drift) ──────┤
    03:00 Task 7 (Social Sentiment) ─────┼──► 05:00 Task 8 (Gradient Recompute)
    04:00 Task 4 (Fatigue Detection) ────┤           │
    Every 4h Task 3 (News Cycle) ────────┤           ▼
    Every 6h Task 1 (Competitive) ───────┤   Every 8h Task 10 (Temperature)
    06:00/18:00 Task 6 (Calendar) ───────┘
    Weekly Task 9 (Brand Positioning)

Campaign Intelligence Loop (Tasks 23-32):
    04:00 Task 23 (DSP Pull) ──► Task 24 (Normalize)
    05:00 Task 25 (Hypotheses) + Task 26 (Bilateral Analysis)
    06:00 Task 27 (Scope I²) ──► Task 28 (Directives)
    07:00 Task 29 (Coherence) ──► Task 30 (Execution)
    08:00 Task 31 (Tier A/B/C Reports)
    12:00+18:00 Task 32 (Rollback Monitor)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

_shutdown = False
_task_registry: Dict[str, DailyStrengtheningTask] = {}


def get_task_registry() -> Dict[str, DailyStrengtheningTask]:
    """Get or initialize the task registry."""
    global _task_registry
    if not _task_registry:
        _register_all_tasks()
    return _task_registry


def _register_all_tasks() -> None:
    """Register all strengthening tasks."""
    global _task_registry

    tasks: List[DailyStrengtheningTask] = []

    try:
        from adam.intelligence.daily.task_01_competitive_intel import CompetitiveIntelligenceTask
        tasks.append(CompetitiveIntelligenceTask())
    except Exception as e:
        logger.debug("Task 1 (competitive) not available: %s", e)

    try:
        from adam.intelligence.daily.task_02_publisher_drift import PublisherDriftTask
        tasks.append(PublisherDriftTask())
    except Exception as e:
        logger.debug("Task 2 (publisher drift) not available: %s", e)

    try:
        from adam.intelligence.daily.task_03_news_cycle import NewsCycleTask
        tasks.append(NewsCycleTask())
    except Exception as e:
        logger.debug("Task 3 (news cycle) not available: %s", e)

    try:
        from adam.intelligence.daily.task_04_fatigue import FatigueDetectionTask
        tasks.append(FatigueDetectionTask())
    except Exception as e:
        logger.debug("Task 4 (fatigue) not available: %s", e)

    try:
        from adam.intelligence.daily.task_05_review_refresh import ReviewRefreshTask
        tasks.append(ReviewRefreshTask())
    except Exception as e:
        logger.debug("Task 5 (review refresh) not available: %s", e)

    try:
        from adam.intelligence.daily.task_06_cultural_calendar import CulturalCalendarTask
        tasks.append(CulturalCalendarTask())
    except Exception as e:
        logger.debug("Task 6 (cultural calendar) not available: %s", e)

    try:
        from adam.intelligence.daily.task_07_social_sentiment import SocialSentimentTask
        tasks.append(SocialSentimentTask())
    except Exception as e:
        logger.debug("Task 7 (social sentiment) not available: %s", e)

    try:
        from adam.intelligence.daily.task_08_gradient_recompute import GradientRecomputeTask
        tasks.append(GradientRecomputeTask())
    except Exception as e:
        logger.debug("Task 8 (gradient recompute) not available: %s", e)

    try:
        from adam.intelligence.daily.task_09_brand_positioning import BrandPositioningTask
        tasks.append(BrandPositioningTask())
    except Exception as e:
        logger.debug("Task 9 (brand positioning) not available: %s", e)

    try:
        from adam.intelligence.daily.task_10_temperature import TemperatureIndexTask
        tasks.append(TemperatureIndexTask())
    except Exception as e:
        logger.debug("Task 10 (temperature) not available: %s", e)

    try:
        from adam.intelligence.daily.task_11_inventory_discovery import InventoryDiscoveryTask
        tasks.append(InventoryDiscoveryTask())
    except Exception as e:
        logger.debug("Task 11 (inventory discovery) not available: %s", e)

    try:
        from adam.intelligence.daily.task_12_taxonomy_builder import TaxonomyBuilderTask
        tasks.append(TaxonomyBuilderTask())
    except Exception as e:
        logger.debug("Task 12 (taxonomy builder) not available: %s", e)

    try:
        from adam.intelligence.daily.task_13_reaction_collection import ReactionCollectionTask
        tasks.append(ReactionCollectionTask())
    except Exception as e:
        logger.debug("Task 13 (reaction collection) not available: %s", e)

    try:
        from adam.intelligence.daily.task_14_ctv_enrichment import CTVEnrichmentTask
        tasks.append(CTVEnrichmentTask())
    except Exception as e:
        logger.debug("Task 14 (CTV enrichment) not available: %s", e)

    try:
        from adam.intelligence.daily.task_15_self_teaching import SelfTeachingTask
        tasks.append(SelfTeachingTask())
    except Exception as e:
        logger.debug("Task 15 (self-teaching) not available: %s", e)

    try:
        from adam.intelligence.daily.task_16_page_gradients import PageGradientTask
        tasks.append(PageGradientTask())
    except Exception as e:
        logger.debug("Task 16 (page gradients) not available: %s", e)

    try:
        from adam.intelligence.daily.task_17_copy_evolution import CopyEvolutionTask
        tasks.append(CopyEvolutionTask())
    except Exception as e:
        logger.debug("Task 17 (copy evolution) not available: %s", e)

    # Task 33 (decay_adjudicator) is intentionally NOT registered here.
    # Its module exposes async run_decay_adjudicator() rather than a
    # DailyStrengtheningTask subclass, and its canonical invocation is
    # via the dashboard endpoint /api/dashboard/decay/run (see
    # adam/api/dashboard/router.py). Per task_33's docstring: "v1
    # pilot can run either scheduled or on-demand via the dashboard."
    # The dashboard path is in place; forcing a scheduler shim would
    # be duplication.

    try:
        from adam.intelligence.daily.task_18_recalibration import RecalibrationTask
        tasks.append(RecalibrationTask())
    except Exception as e:
        logger.debug("Task 18 (composite_alignment recalibration) not available: %s", e)

    try:
        from adam.intelligence.daily.task_19_resonance_evolution import ResonanceEvolutionTask
        tasks.append(ResonanceEvolutionTask())
    except Exception as e:
        logger.debug("Task 19 (resonance evolution) not available: %s", e)

    try:
        from adam.intelligence.daily.task_20_quality_audit import LearningQualityAuditTask
        tasks.append(LearningQualityAuditTask())
    except Exception as e:
        logger.debug("Task 20 (quality audit) not available: %s", e)

    try:
        from adam.intelligence.daily.task_21_tensor_archetypes import TensorArchetypeTask
        tasks.append(TensorArchetypeTask())
    except Exception as e:
        logger.debug("Task 21 (tensor archetypes) not available: %s", e)

    try:
        from adam.intelligence.daily.task_22_causal_mediation import CausalMediationTask
        tasks.append(CausalMediationTask())
    except Exception as e:
        logger.debug("Task 22 (causal mediation) not available: %s", e)

    # --- Campaign Intelligence Loop (DCIL) Tasks 23-32 ---

    try:
        from adam.intelligence.daily.task_23_dsp_performance_pull import DSPPerformancePullTask
        tasks.append(DSPPerformancePullTask())
    except Exception as e:
        logger.debug("Task 23 (DSP pull) not available: %s", e)

    try:
        from adam.intelligence.daily.task_24_performance_normalizer import PerformanceNormalizerTask
        tasks.append(PerformanceNormalizerTask())
    except Exception as e:
        logger.debug("Task 24 (normalizer) not available: %s", e)

    try:
        from adam.intelligence.daily.task_25_hypothesis_testing import HypothesisTestingTask
        tasks.append(HypothesisTestingTask())
    except Exception as e:
        logger.debug("Task 25 (hypothesis testing) not available: %s", e)

    try:
        from adam.intelligence.daily.task_26_bilateral_analysis import BilateralAnalysisTask
        tasks.append(BilateralAnalysisTask())
    except Exception as e:
        logger.debug("Task 26 (bilateral analysis) not available: %s", e)

    try:
        from adam.intelligence.daily.task_27_scope_determination import ScopeDeterminationTask
        tasks.append(ScopeDeterminationTask())
    except Exception as e:
        logger.debug("Task 27 (scope determination) not available: %s", e)

    try:
        from adam.intelligence.daily.task_28_directive_generation import DirectiveGenerationTask
        tasks.append(DirectiveGenerationTask())
    except Exception as e:
        logger.debug("Task 28 (directive generation) not available: %s", e)

    try:
        from adam.intelligence.daily.task_29_coherence_validation import CoherenceValidationTask
        tasks.append(CoherenceValidationTask())
    except Exception as e:
        logger.debug("Task 29 (coherence validation) not available: %s", e)

    try:
        # Task 29.5 — DCIL bridge sync. Closes Loop β by syncing the
        # validated directives task_29 writes to Redis into the
        # management.dcil_directives table the dashboard reads from.
        # Must run AFTER task_29 within the daily cycle.
        from adam.intelligence.daily.task_29_5_dcil_bridge_sync import DCILBridgeSyncTask
        tasks.append(DCILBridgeSyncTask())
    except Exception as e:
        logger.debug("Task 29.5 (DCIL bridge sync) not available: %s", e)

    try:
        # Task 29.6 — Horizon adjudicator. Closes Loop γ auto-path:
        # nightly sweep over users-with-pending-deviations,
        # adjudicate_ready_deviations() per user. Without this, the
        # auto-adjudication path NEVER fires — the function is
        # exposed only via the dashboard's operator-triggered route.
        from adam.intelligence.daily.task_29_6_horizon_adjudicator import HorizonAdjudicatorTask
        tasks.append(HorizonAdjudicatorTask())
    except Exception as e:
        logger.debug("Task 29.6 (horizon adjudicator) not available: %s", e)

    # F1 daily runner (task #55) — buyer review metaphor scoring.
    # Activates the buyer half of F3's metaphor_alignment cascade wire.
    try:
        from adam.intelligence.daily.task_29_7_buyer_metaphor_scoring import BuyerMetaphorScoringTask
        tasks.append(BuyerMetaphorScoringTask())
    except Exception as e:
        logger.debug("Task 29.7 (buyer metaphor scoring) not available: %s", e)

    # F2 daily runner (task #55) — brand product copy metaphor scoring.
    # Activates the brand half of F3's metaphor_alignment cascade wire.
    try:
        from adam.intelligence.daily.task_29_8_brand_metaphor_scoring import BrandMetaphorScoringTask
        tasks.append(BrandMetaphorScoringTask())
    except Exception as e:
        logger.debug("Task 29.8 (brand metaphor scoring) not available: %s", e)

    try:
        from adam.intelligence.daily.task_30_execution import CampaignExecutionTask
        tasks.append(CampaignExecutionTask())
    except Exception as e:
        logger.debug("Task 30 (campaign execution) not available: %s", e)

    try:
        from adam.intelligence.daily.task_31_tier_reporting import TierReportingTask
        tasks.append(TierReportingTask())
    except Exception as e:
        logger.debug("Task 31 (tier reporting) not available: %s", e)

    try:
        from adam.intelligence.daily.task_32_rollback_monitor import RollbackMonitorTask
        tasks.append(RollbackMonitorTask())
    except Exception as e:
        logger.debug("Task 32 (rollback monitor) not available: %s", e)

    # Task 34 — Hierarchical Bayes nightly refit. Without this scheduled,
    # per-cell (archetype × mechanism × category) posteriors stay frozen
    # and the cascade reads stale priors. Per audit §6 + handoff §3.5.
    try:
        from adam.intelligence.daily.task_34_hierarchical_bayes_refit import (
            HierarchicalBayesRefitTask,
        )
        tasks.append(HierarchicalBayesRefitTask())
    except Exception as e:
        logger.debug("Task 34 (hierarchical Bayes refit) not available: %s", e)

    # Task 35 — Causal Forest weekly CATE fit. Without this scheduled,
    # heterogeneous treatment effects stay frozen and the cascade reads
    # stale per-cell CATEs. Per audit §6 + handoff §2.10.
    try:
        from adam.intelligence.daily.task_35_causal_forest_fit import (
            CausalForestFitTask,
        )
        tasks.append(CausalForestFitTask())
    except Exception as e:
        logger.debug("Task 35 (causal forest weekly fit) not available: %s", e)

    # Task 36 — Spine #1 HMC offline user-posterior reconcile. Per
    # CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md Phase 1 line 945. Refines the
    # online BONG path's per-mechanism Beta posteriors with AR(1)
    # carryover + random intercept via NumPyro NUTS. Without this
    # scheduled, the HMC path exists but never runs.
    try:
        from adam.intelligence.daily.task_36_hmc_user_posterior_reconcile import (
            HMCUserPosteriorReconcileTask,
        )
        tasks.append(HMCUserPosteriorReconcileTask())
    except Exception as e:
        logger.debug("Task 36 (HMC user-posterior reconcile) not available: %s", e)

    # Task 38 — Spine #6 DecisionTrace daily drain. Per
    # CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md line 248. Hourly consumer
    # of the in-memory trace log produced by the cascade producer
    # wiring (ab10f26). Without this scheduled, traces accumulate
    # in memory and never reach Redis hot cache or Neo4j archival.
    try:
        from adam.intelligence.daily.task_38_decision_trace_drain import (
            DecisionTraceDrainTask,
        )
        tasks.append(DecisionTraceDrainTask())
    except Exception as e:
        logger.debug("Task 38 (DecisionTrace drain) not available: %s", e)

    # Task 39 — Spine Section 8 mSPRT campaign-level monitor. Per
    # CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md line 31, Section 8.3 line
    # 913, line 1125, line 1134. Daily aggregation of treatment vs
    # control conversions + mSPRT step → boundary status for the
    # partner dashboard + RED-criterion launch-deferral trigger.
    # Without this scheduled, the campaign monitor (f4a9093) +
    # aggregation function exist but never run on real data.
    try:
        from adam.intelligence.daily.task_39_msprt_campaign_monitor import (
            MSPRTCampaignMonitorTask,
        )
        tasks.append(MSPRTCampaignMonitorTask())
    except Exception as e:
        logger.debug("Task 39 (mSPRT campaign monitor) not available: %s", e)

    # Task 40 — Spine #5 dual_eval_context nightly re-warm. As new
    # :GoalStateLabel nodes accumulate (via Slice 18's Claude API
    # labeler), this task re-runs warm_dual_eval_from_neo4j so the
    # production cascade's primary model swaps to whichever of B / C
    # wins on the latest labeled set. Without this scheduled, the
    # Slice 20 startup wire only runs at process boot — adding labels
    # mid-run wouldn't propagate to the cascade until the next deploy.
    try:
        from adam.intelligence.daily.task_40_dual_eval_rewarm import (
            DualEvalRewarmTask,
        )
        tasks.append(DualEvalRewarmTask())
    except Exception as e:
        logger.debug("Task 40 (dual_eval re-warm) not available: %s", e)

    # Task 41 — Spine #6 OPE daily estimator. Audit Tier 1 #5 closure
    # consumer side: ope.py ships full IPS/DR/SNIPS estimators with
    # zero production callers; this nightly task runs them on the
    # accumulated :DecisionContext-[:HAD_OUTCOME]->:AdOutcome rows
    # (Slice 6 sibling writer populates input) and persists daily
    # :OPEDailyEstimate snapshots for trending + dashboard surfaces.
    # Without this scheduled, the directive's "every served impression
    # contributes to evaluating every arm" multiplier (line 244)
    # cannot fire.
    try:
        from adam.intelligence.daily.task_41_ope_daily_estimator import (
            OPEDailyEstimatorTask,
        )
        tasks.append(OPEDailyEstimatorTask())
    except Exception as e:
        logger.debug("Task 41 (OPE daily estimator) not available: %s", e)

    # Task 42 — Slice 8 launch-gate runner. Audit Tier 1 #10 found
    # all 8 RED-criteria check functions + run_launch_gate_evaluation
    # aggregator existed but only the sapid counter was incrementing
    # in production. Slice 8's red_criteria_snapshot is the producer
    # side; this task is the daily consumer that reads the snapshot
    # + sapid monitor, runs the gate, and persists :LaunchGateResult
    # for trending. Without this scheduled, the directive's
    # "continuous monitoring" line 1128 has no closure.
    try:
        from adam.intelligence.daily.task_42_launch_gate_runner import (
            LaunchGateRunnerTask,
        )
        tasks.append(LaunchGateRunnerTask())
    except Exception as e:
        logger.debug("Task 42 (launch-gate runner) not available: %s", e)

    # Task 43 — Original-Slice-B autonomous label-accumulation loop.
    # Task 40's docstring (lines 62-67) named this as the missing
    # sibling: Task 40 RETRAINS dual-eval B/C on accumulated
    # :GoalStateLabel nodes; this task GENERATES the labels from
    # newly-seen DecisionTrace.page_url values via Claude API. Sits
    # at 02:00 UTC slot — before Task 40 (03:00) so the retrain sees
    # today's new labels.
    try:
        from adam.intelligence.daily.task_43_label_new_pages import (
            LabelNewPagesTask,
        )
        tasks.append(LabelNewPagesTask())
    except Exception as e:
        logger.debug("Task 43 (label new pages) not available: %s", e)

    # Task 44 — Slice 16 identity-stability sweep. RED criterion #4
    # producer (named sibling in task_42_launch_gate_runner.py:43-46).
    # Surveys recently-active buyers, decays their identity_stability
    # by days-since-last-touch, increments record_user_active +
    # record_identity_collapse on the snapshot accumulator. Runs at
    # 04:00 UTC alongside Task 41 — both populate state Task 42
    # (05:00) reads from the snapshot.
    try:
        from adam.intelligence.daily.task_44_identity_stability_sweep import (
            IdentityStabilitySweepTask,
        )
        tasks.append(IdentityStabilitySweepTask())
    except Exception as e:
        logger.debug(
            "Task 44 (identity-stability sweep) not available: %s", e,
        )

    # Task 45 — Slice 23 creative spot-check sweep. RED criterion #6
    # producer (named sibling in task_42_launch_gate_runner.py:40-42).
    # Runs Slice 18 (reactance) + 19 (metaphor coherence) + 20
    # (mechanism activation) scorers against :UploadedCreative
    # copy_text; increments record_creatives_in_rotation +
    # record_creatives_failed_spot_check. Same 04:00 slot as Task 44.
    try:
        from adam.intelligence.daily.task_45_creative_spot_check import (
            CreativeSpotCheckTask,
        )
        tasks.append(CreativeSpotCheckTask())
    except Exception as e:
        logger.debug(
            "Task 45 (creative spot-check) not available: %s", e,
        )

    for task in tasks:
        _task_registry[task.name] = task

    logger.info("Registered %d daily strengthening tasks", len(_task_registry))


async def run_all_due_tasks() -> List[TaskResult]:
    """Run all tasks that are due according to their schedules."""
    registry = get_task_registry()
    results = []

    for name, task in registry.items():
        if _shutdown:
            break
        if task.is_due():
            logger.info("Running strengthening task: %s", name)
            result = await task.run()
            results.append(result)

    return results


async def run_task_by_name(name: str) -> Optional[TaskResult]:
    """Run a specific task by name (ignores schedule)."""
    registry = get_task_registry()
    task = registry.get(name)
    if task:
        return await task.run()
    return None


async def _scheduler_loop() -> None:
    """Main scheduler loop. Checks for due tasks every 5 minutes."""
    global _shutdown

    logger.info("Daily Intelligence Strengthening scheduler started")

    # Defer first cycle by 5 minutes so the server can start handling
    # requests immediately without background tasks blocking the event loop.
    await asyncio.sleep(300)

    while not _shutdown:
        try:
            results = await run_all_due_tasks()
            if results:
                successes = sum(1 for r in results if r.success)
                logger.info(
                    "Strengthening cycle: %d/%d tasks succeeded",
                    successes, len(results),
                )
        except Exception as e:
            logger.error("Scheduler cycle error: %s", e)

        # Sleep 5 minutes, checking for shutdown every 10 seconds
        for _ in range(30):
            if _shutdown:
                break
            await asyncio.sleep(10)

    logger.info("Daily Intelligence Strengthening scheduler stopped")


async def start_strengthening_scheduler(app=None) -> None:
    """Start the scheduler as a background task."""
    global _shutdown
    _shutdown = False
    task = asyncio.create_task(_scheduler_loop())
    if app is not None:
        app._strengthening_scheduler_task = task
    logger.info("Daily Intelligence Strengthening scheduler queued")


def request_shutdown() -> None:
    """Request graceful shutdown of the scheduler."""
    global _shutdown
    _shutdown = True
