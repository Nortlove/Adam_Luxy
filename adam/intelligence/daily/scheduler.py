"""
Daily Intelligence Strengthening Scheduler
============================================

Orchestrates execution of all 10 strengthening tasks based on their
declared schedules. Runs as a background task in the ADAM application.

Dependency DAG:
    01:00 Task 5 (Reviews) ─────────────┐
    02:00 Task 2 (Publisher Drift) ──────┤
    03:00 Task 7 (Social Sentiment) ─────┼──► 05:00 Task 8 (Gradient Recompute)
    04:00 Task 4 (Fatigue Detection) ────┤           │
    Every 4h Task 3 (News Cycle) ────────┤           ▼
    Every 6h Task 1 (Competitive) ───────┤   Every 8h Task 10 (Temperature)
    06:00/18:00 Task 6 (Calendar) ───────┘
    Weekly Task 9 (Brand Positioning) ──────────────────────────────────
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
