"""
Base class for Daily Intelligence Strengthening Tasks.

Every task follows the same pipeline:
    Fetch -> NDF-Process -> Store -> (consumed at bid time)

Each task declares:
- schedule: cron-like timing (hours, frequency)
- input sources: what to fetch
- NDF processing: how to extract psychological intelligence
- output destinations: Redis keys + Neo4j relationships
- consumption pathway: how bid-time code uses the output
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_name: str
    success: bool
    items_processed: int = 0
    items_stored: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        status = "OK" if self.success else "FAILED"
        return (
            f"[{status}] {self.task_name}: "
            f"processed={self.items_processed} stored={self.items_stored} "
            f"errors={self.errors} duration={self.duration_seconds:.1f}s"
        )


class DailyStrengtheningTask(ABC):
    """Base class for all daily intelligence strengthening tasks.

    Subclasses implement:
    - name: unique task identifier
    - schedule_hours: list of UTC hours when task should run
    - frequency_hours: minimum hours between runs (for tasks that run more than daily)
    - execute(): the actual task logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique task identifier."""
        ...

    @property
    def schedule_hours(self) -> List[int]:
        """UTC hours when this task should run. Default: [5] (5 AM UTC)."""
        return [5]

    @property
    def frequency_hours(self) -> int:
        """Minimum hours between runs. Default: 24."""
        return 24

    @abstractmethod
    async def execute(self) -> TaskResult:
        """Execute the task. Returns TaskResult."""
        ...

    def _get_redis(self):
        """Get a Redis connection."""
        try:
            import redis
            r = redis.Redis(host="localhost", port=6379, decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

    def _extract_edge_dims(self, text: str) -> Dict[str, float]:
        """Extract 20 edge dimensions from text (same space as bilateral edges).

        Primary: uses full-width edge scoring (20 dims).
        Fallback: NDF extraction mapped to edge space (only if edge scoring fails).
        """
        try:
            from adam.intelligence.page_edge_scoring import score_page_full_width
            edge_profile = score_page_full_width(text=text)
            if edge_profile.dimensions:
                return edge_profile.dimensions
        except Exception:
            pass

        # Fallback: NDF extraction (7 dims — lossy, last resort)
        from adam.intelligence.page_intelligence import profile_page_content
        profile = profile_page_content(url="", text_content=text)
        # Return edge_dimensions if populated, else construct_activations
        if profile.edge_dimensions:
            return profile.edge_dimensions
        return profile.construct_activations

    def _ndf_from_text(self, text: str) -> Dict[str, float]:
        """Legacy wrapper — delegates to _extract_edge_dims.

        Kept for backward compatibility. All new code should call
        _extract_edge_dims() directly.
        """
        return self._extract_edge_dims(text)

    def _store_redis_hash(self, key: str, data: Dict[str, Any], ttl: int = 86400) -> bool:
        """Store a dict as a Redis hash with TTL."""
        import json
        r = self._get_redis()
        if not r:
            return False
        try:
            # JSON-encode complex values
            flat = {}
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    flat[k] = json.dumps(v)
                elif isinstance(v, bool):
                    flat[k] = int(v)
                else:
                    flat[k] = v
            r.hset(key, mapping=flat)
            r.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning("Redis store failed for %s: %s", key, e)
            return False

    def _read_redis_hash(self, key: str) -> Optional[Dict[str, str]]:
        """Read a Redis hash."""
        r = self._get_redis()
        if not r:
            return None
        try:
            data = r.hgetall(key)
            return data if data else None
        except Exception:
            return None

    async def run(self) -> TaskResult:
        """Run the task with timing and error handling."""
        start = time.time()
        try:
            result = await self.execute()
            result.duration_seconds = time.time() - start
            logger.info(result.summary)

            # Record last run time
            r = self._get_redis()
            if r:
                r.set(f"informativ:diss:last_run:{self.name}", str(time.time()), ex=86400 * 7)

            # Record metrics
            try:
                from adam.infrastructure.prometheus.metrics import get_metrics
                metrics = get_metrics()
                if metrics._initialized:
                    metrics.page_crawl_total.labels(
                        strategy="diss", pass_type=self.name,
                    ).inc(result.items_processed)
            except Exception:
                pass

            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error("Task %s failed after %.1fs: %s", self.name, elapsed, e)
            return TaskResult(
                task_name=self.name,
                success=False,
                duration_seconds=elapsed,
                details={"error": str(e)},
            )

    def is_due(self) -> bool:
        """Check if this task should run now."""
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)

        # Check if current hour matches schedule
        if now.hour not in self.schedule_hours:
            return False

        # Check frequency: don't run if ran recently
        r = self._get_redis()
        if r:
            last_run = r.get(f"informativ:diss:last_run:{self.name}")
            if last_run:
                elapsed_hours = (time.time() - float(last_run)) / 3600
                if elapsed_hours < self.frequency_hours * 0.9:  # 10% tolerance
                    return False

        return True
