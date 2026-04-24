"""
Campaign Intelligence Audit Log
==================================

Persistent audit trail for every DCIL cycle. Records data pulls,
statistical tests, scope determinations, directives, validations,
executions, and rollbacks.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import AuditEntry

logger = logging.getLogger(__name__)

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "dcil")


class CampaignIntelligenceAuditLog:
    """Persistent audit trail for the DCIL pipeline."""

    def __init__(self, config=None):
        self.config = config or get_dcil_config()
        self._entries: List[AuditEntry] = []
        self._ensure_log_dir()

    def log(
        self,
        stage: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        finding_ids: Optional[List[str]] = None,
        directive_ids: Optional[List[str]] = None,
        scope: str = "",
        success: bool = True,
        error: str = "",
    ) -> AuditEntry:
        """Log an audit entry."""
        entry = AuditEntry(
            stage=stage,
            action=action,
            details=details or {},
            finding_ids=finding_ids or [],
            directive_ids=directive_ids or [],
            scope=scope,
            success=success,
            error=error,
        )
        self._entries.append(entry)
        return entry

    def flush(self) -> None:
        """Write all entries to persistent storage."""
        if not self._entries:
            return

        date = time.strftime("%Y-%m-%d")

        # Write to file
        self._write_to_file(date)

        # Write to Redis
        self._write_to_redis(date)

        self._entries.clear()

    def get_cycle_summary(self) -> Dict[str, Any]:
        """Get summary of current cycle's audit entries."""
        stages = {}
        for entry in self._entries:
            if entry.stage not in stages:
                stages[entry.stage] = {"count": 0, "success": 0, "errors": 0}
            stages[entry.stage]["count"] += 1
            if entry.success:
                stages[entry.stage]["success"] += 1
            else:
                stages[entry.stage]["errors"] += 1

        return {
            "total_entries": len(self._entries),
            "stages": stages,
            "has_errors": any(not e.success for e in self._entries),
        }

    def _write_to_file(self, date: str) -> None:
        try:
            filepath = os.path.join(_LOG_DIR, f"dcil_audit_{date}.jsonl")
            with open(filepath, "a") as f:
                for entry in self._entries:
                    f.write(json.dumps({
                        "timestamp": entry.timestamp,
                        "stage": entry.stage,
                        "action": entry.action,
                        "details": entry.details,
                        "finding_ids": entry.finding_ids,
                        "directive_ids": entry.directive_ids,
                        "scope": entry.scope,
                        "success": entry.success,
                        "error": entry.error,
                    }) + "\n")
        except Exception as e:
            logger.debug("Audit file write failed: %s", e)

    def _write_to_redis(self, date: str) -> None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis = get_redis()
            if redis:
                key = f"{self.config.redis_prefix}:audit:{date}"
                existing = redis.get(key)
                entries = json.loads(existing) if existing else []
                for entry in self._entries:
                    entries.append({
                        "timestamp": entry.timestamp,
                        "stage": entry.stage,
                        "action": entry.action,
                        "success": entry.success,
                        "error": entry.error,
                    })
                redis.setex(key, self.config.snapshot_ttl_days * 86400, json.dumps(entries))
        except Exception as e:
            logger.debug("Audit Redis write failed: %s", e)

    def _ensure_log_dir(self):
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
        except Exception:
            pass


_audit_log: Optional[CampaignIntelligenceAuditLog] = None


def get_audit_log() -> CampaignIntelligenceAuditLog:
    global _audit_log
    if _audit_log is None:
        _audit_log = CampaignIntelligenceAuditLog()
    return _audit_log
