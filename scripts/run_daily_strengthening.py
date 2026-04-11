#!/usr/bin/env python3
"""
Run Daily Intelligence Strengthening Tasks
============================================

Executes all 10 strengthening tasks (or specific ones by name).
Useful for manual runs, testing, and initial population.

Usage:
    # Run all tasks (ignoring schedule)
    python scripts/run_daily_strengthening.py --all

    # Run specific tasks
    python scripts/run_daily_strengthening.py --tasks news_cycle,cultural_calendar

    # Run only tasks that are due per schedule
    python scripts/run_daily_strengthening.py --due

    # Dry run: show what would execute
    python scripts/run_daily_strengthening.py --all --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("daily_strengthening")


async def run(args: argparse.Namespace) -> None:
    from adam.intelligence.daily.scheduler import get_task_registry, run_all_due_tasks
    from adam.intelligence.daily.base import TaskResult

    registry = get_task_registry()
    logger.info("=" * 60)
    logger.info("ADAM Daily Intelligence Strengthening System")
    logger.info("Registered tasks: %d", len(registry))
    logger.info("=" * 60)

    for name, task in registry.items():
        logger.info(
            "  %-25s schedule=%s  freq=%dh",
            name, task.schedule_hours, task.frequency_hours,
        )

    logger.info("")

    # Determine which tasks to run
    if args.due:
        logger.info("Running tasks that are DUE per schedule...")
        results = await run_all_due_tasks()
    elif args.tasks:
        task_names = [t.strip() for t in args.tasks.split(",")]
        results = []
        for name in task_names:
            task = registry.get(name)
            if task:
                if args.dry_run:
                    logger.info("[DRY RUN] Would run: %s", name)
                else:
                    logger.info("Running: %s", name)
                    result = await task.run()
                    results.append(result)
            else:
                logger.error("Unknown task: %s", name)
    else:
        # Run all
        results = []
        for name, task in registry.items():
            if args.dry_run:
                logger.info("[DRY RUN] Would run: %s", name)
            else:
                logger.info("Running: %s ...", name)
                result = await task.run()
                results.append(result)
                logger.info("  %s", result.summary)

    if args.dry_run:
        return

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)

    successes = 0
    total_processed = 0
    total_stored = 0
    total_errors = 0
    total_duration = 0.0

    for r in results:
        status = "OK" if r.success else "FAIL"
        logger.info(
            "  [%4s] %-25s processed=%-5d stored=%-5d errors=%-3d %.1fs",
            status, r.task_name, r.items_processed, r.items_stored,
            r.errors, r.duration_seconds,
        )
        if r.details:
            for k, v in r.details.items():
                if v:  # Skip empty
                    logger.info("         %-20s: %s", k, v)
        if r.success:
            successes += 1
        total_processed += r.items_processed
        total_stored += r.items_stored
        total_errors += r.errors
        total_duration += r.duration_seconds

    logger.info("")
    logger.info(
        "TOTAL: %d/%d succeeded | %d processed | %d stored | %d errors | %.1fs",
        successes, len(results), total_processed, total_stored,
        total_errors, total_duration,
    )

    # Check Redis population
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        cursor, keys = r.scan(0, match="informativ:*", count=1000)
        logger.info("Redis informativ:* keys: %d (from first scan page)", len(keys))
    except Exception:
        logger.info("Redis not available — stored items went to /dev/null")


def main():
    parser = argparse.ArgumentParser(
        description="Run ADAM Daily Intelligence Strengthening tasks",
    )
    parser.add_argument(
        "--all", action="store_true", default=True,
        help="Run all tasks (default)",
    )
    parser.add_argument(
        "--tasks", type=str, default="",
        help="Comma-separated task names to run",
    )
    parser.add_argument(
        "--due", action="store_true",
        help="Only run tasks that are due per schedule",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would run without executing",
    )

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
