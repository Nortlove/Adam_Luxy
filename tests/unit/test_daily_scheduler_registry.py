"""Pin G4 — tasks 16/17 registered in the daily scheduler.

Discipline anchors:
    - Tasks 16 (page gradients) and 17 (copy evolution) had real
      DailyStrengtheningTask subclasses but were forgotten in the
      scheduler's _register_all_tasks. This test pins their
      registration so a future refactor can't silently drop them
      back to dark code.
    - Task 33 (decay adjudicator) is intentionally NOT in the daily
      scheduler — its canonical invocation is via the dashboard
      endpoint /api/dashboard/decay/run. This test pins that
      intentional omission so a well-meaning refactor doesn't
      force-add it and create dual invocation paths.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# Reset the singleton between tests since _register_all_tasks() caches
# the registry on first access. Without reset, the order of tests
# could see stale state from a previous test.
@pytest.fixture(autouse=True)
def _reset_scheduler_singleton():
    import adam.intelligence.daily.scheduler as sched
    sched._task_registry = {}
    yield
    sched._task_registry = {}


def test_task_16_page_gradients_registered():
    """task_16 (PageGradientTask) must appear in the registry."""
    from adam.intelligence.daily.scheduler import get_task_registry

    registry = get_task_registry()
    task_names = {t.name for t in registry.values()} if isinstance(
        registry, dict,
    ) else {t.name for t in registry}

    assert "page_gradient_computation" in task_names


def test_task_17_copy_evolution_registered():
    """task_17 (CopyEvolutionTask) must appear in the registry."""
    from adam.intelligence.daily.scheduler import get_task_registry

    registry = get_task_registry()
    task_names = {t.name for t in registry.values()} if isinstance(
        registry, dict,
    ) else {t.name for t in registry}

    assert "copy_evolution" in task_names


def test_task_33_decay_NOT_registered_in_daily_scheduler():
    """Discipline anchor: task_33 (decay_adjudicator) is invokable via
    the dashboard endpoint /api/dashboard/decay/run, NOT via the daily
    scheduler. Forcing it into the scheduler would create dual
    invocation paths. Pin the intentional omission."""
    from adam.intelligence.daily.scheduler import get_task_registry

    registry = get_task_registry()
    task_names = {t.name for t in registry.values()} if isinstance(
        registry, dict,
    ) else {t.name for t in registry}

    # task_33's canonical name would be 'decay_adjudicator' or similar;
    # tighten to that specific pattern to avoid matching legitimate
    # registrations like 'horizon_adjudicator' (task_29.6).
    decay_specific = [n for n in task_names if "decay" in n.lower()]
    assert decay_specific == [], (
        f"task_33 (decay) appears in daily scheduler ({decay_specific}); "
        f"canonical invocation is dashboard /api/dashboard/decay/run"
    )


def test_registration_is_resilient_to_individual_task_import_failures():
    """The scheduler's per-task try/except means one broken import
    can't sabotage the rest. Pin the pattern: even if task_16 fails
    to import, the registry still builds with everything else."""
    import adam.intelligence.daily.scheduler as sched
    sched._task_registry = {}

    # Patch task_16 to raise ImportError on module load
    real_import = __import__

    def selective_import(name, *args, **kwargs):
        if "task_16_page_gradients" in name:
            raise ImportError("simulated task_16 unavailable")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=selective_import):
        registry = sched.get_task_registry()

    # task_16 missing, but other tasks should still be registered
    task_names = {t.name for t in registry.values()} if isinstance(
        registry, dict,
    ) else {t.name for t in registry}
    assert "page_gradient_computation" not in task_names
    # Other tasks survive
    assert len(task_names) > 5
