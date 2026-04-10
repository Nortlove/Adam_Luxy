"""
Daily Intelligence Strengthening System (DISS)
================================================

A scheduled pipeline that harvests, processes, and injects psychological
intelligence from external sources into ADAM's graph and cache layers.

Invariant: raw data enters, NDF-grounded structured intelligence exits.
Nothing stays as text. Everything becomes a prior, an edge update,
a gradient adjustment, or a mechanism modifier consumed at bid time.

10 Tasks:
1. Competitive Intelligence (Meta/Google Ad Libraries)
2. Publisher Psychological Drift Monitor
3. News Cycle Psychological State Detector
4. Ad Fatigue & Mechanism Wear Detection
5. Review Intelligence Refresh
6. Cultural Calendar Psychological Priming
7. Social Sentiment Mechanism Signal Extraction
8. Gradient Field Recomputation
9. Brand Psychological Positioning Tracker
10. Category Conversion Temperature Index
"""

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.daily.scheduler import run_all_due_tasks, get_task_registry

__all__ = [
    "DailyStrengtheningTask",
    "TaskResult",
    "run_all_due_tasks",
    "get_task_registry",
]
