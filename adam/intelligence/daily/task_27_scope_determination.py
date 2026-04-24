"""
Task 27: Scope Determination
===============================

For each significant finding from Tasks 25-26, runs DerSimonian-Laird
meta-analysis to determine generalizability scope:
    I² < 25%  → SYSTEM_WIDE
    I² 25-50% → CATEGORY_LEVEL
    I² 50-75% → ARCHETYPE_LEVEL
    I² > 75%  → CAMPAIGN_SPECIFIC

Then propagates scoped learnings through the Knowledge Propagation
Network and applies Neo4j updates at the determined scope.

Schedule: 06:00 UTC daily (after analysis tasks)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    HypothesisResult,
    HypothesisStatus,
    LearningScope,
    ScopedLearning,
)

logger = logging.getLogger(__name__)


class ScopeDeterminationTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "scope_determination"

    @property
    def schedule_hours(self) -> List[int]:
        return [6]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        # Load hypothesis results from Task 25
        from adam.intelligence.daily.task_25_hypothesis_testing import get_latest_hypothesis_results
        hypothesis_data = get_latest_hypothesis_results()

        if hypothesis_data is None:
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                details={"error": "No hypothesis results available."},
            )

        # Load snapshot for evidence construction
        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        snapshot = get_latest_snapshot()

        from adam.intelligence.campaign_intelligence.generalizability import (
            GeneralizabilityScopeDeterminer,
            EffectObservation,
        )
        determiner = GeneralizabilityScopeDeterminer(config)

        scoped_learnings: List[ScopedLearning] = []
        scope_counts: Dict[str, int] = {s.value: 0 for s in LearningScope}

        # Process each rejected or confirmed hypothesis with evidence
        for h_data in hypothesis_data.get("hypotheses", []):
            status = h_data.get("status", "")
            if status not in ("rejected", "confirmed"):
                continue

            # Build evidence vectors from per-campaign data
            evidence = []
            if snapshot:
                for camp in snapshot.campaigns:
                    if not camp.archetype or camp.status != "ACTIVE":
                        continue
                    if camp.conversions > 0 or camp.clicks > 0:
                        # Effect size = conversion rate for this campaign
                        effect = camp.cvr if camp.cvr > 0 else camp.ctr
                        # Derive category from campaign group or config
                        category = _infer_category(camp, snapshot)
                        evidence.append(EffectObservation(
                            effect_size=effect,
                            sample_size=max(camp.clicks, 1),
                            campaign_id=camp.campaign_id,
                            archetype=camp.archetype,
                            category=category,
                            mechanism=camp.mechanism,
                        ))

            # Reconstruct HypothesisResult for the determiner
            finding = HypothesisResult(
                hypothesis_id=h_data.get("id", ""),
                hypothesis_name=h_data.get("name", ""),
                status=HypothesisStatus(status),
                p_value=h_data.get("p_value", 1.0),
                effect_size=h_data.get("effect_size", 0),
                sample_size=h_data.get("sample_size", 0),
                finding=h_data.get("finding", ""),
                recommendation=h_data.get("recommendation", ""),
                action_if_rejected=h_data.get("action", ""),
            )

            scoped = determiner.determine_scope(finding, evidence)
            scoped_learnings.append(scoped)
            scope_counts[scoped.scope.value] += 1

        # Propagate scoped learnings through KPN
        propagated = 0
        for sl in scoped_learnings:
            try:
                _propagate_scoped_learning(sl)
                propagated += 1
            except Exception as e:
                logger.warning("Failed to propagate scoped learning %s: %s", sl.finding_id, e)

        # Apply Neo4j updates
        neo4j_applied = 0
        for sl in scoped_learnings:
            for update in sl.neo4j_updates:
                try:
                    _apply_neo4j_update(update)
                    neo4j_applied += 1
                except Exception as e:
                    logger.warning("Neo4j update failed: %s", e)

        # Store scoped learnings
        _store_scoped_learnings(scoped_learnings, config)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(hypothesis_data.get("hypotheses", [])),
            items_stored=len(scoped_learnings),
            duration_seconds=duration,
            details={
                "scoped_learnings": len(scoped_learnings),
                "scope_distribution": scope_counts,
                "propagated": propagated,
                "neo4j_updates": neo4j_applied,
            },
        )


def _propagate_scoped_learning(sl: ScopedLearning) -> None:
    """Propagate a scoped learning through the Knowledge Propagation Network."""
    try:
        from adam.intelligence.knowledge_propagation import get_propagation_network
        kpn = get_propagation_network()

        signal_content = {
            "finding_id": sl.finding_id,
            "finding_type": sl.finding_type,
            "scope": sl.scope.value,
            "effect_size": sl.effect_size,
            "i_squared": sl.i_squared,
            "affected_archetypes": sl.affected_archetypes,
        }

        max_hops = sl.propagation_config.get("max_hops", 1)
        amplitude = sl.propagation_config.get("amplitude", 0.3)

        from adam.intelligence.knowledge_propagation import KnowledgeSignal
        signal = KnowledgeSignal(
            source="scope_determination",
            signal_type="scoped_learning",
            content=signal_content,
            amplitude=amplitude,
            max_hops=max_hops,
        )

        kpn.propagate(signal)
    except Exception as e:
        logger.debug("KPN propagation failed for %s: %s", sl.finding_id, e)


def _apply_neo4j_update(update: Dict) -> None:
    """Apply a single Neo4j update from a scoped learning."""
    try:
        from adam.infrastructure.neo4j_client import get_driver
        driver = get_driver()
        if driver is None:
            logger.debug("Neo4j not available for scope update")
            return

        with driver.session() as session:
            session.run(update["cypher"], update.get("params", {}))
            logger.info(
                "Applied %s-scope Neo4j update: %s",
                update.get("scope", "unknown"),
                update.get("description", ""),
            )
    except Exception as e:
        logger.debug("Neo4j update failed: %s", e)


_MEMORY_SCOPED_LEARNINGS = {}


def _store_scoped_learnings(learnings: List[ScopedLearning], config) -> None:
    date = time.strftime("%Y-%m-%d")
    data = {
        "timestamp": time.time(),
        "date": date,
        "learnings": [
            {
                "finding_id": sl.finding_id,
                "finding_type": sl.finding_type,
                "statement": sl.statement,
                "scope": sl.scope.value,
                "i_squared": sl.i_squared,
                "tau_squared": sl.tau_squared,
                "effect_size": sl.effect_size,
                "n_studies": sl.n_studies,
                "affected_archetypes": sl.affected_archetypes,
                "affected_campaigns": sl.affected_campaigns,
            }
            for sl in learnings
        ],
    }

    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:scoped_learnings:{date}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
            return
    except Exception:
        pass
    _MEMORY_SCOPED_LEARNINGS[date] = data


def _infer_category(camp, snapshot):
    """Infer product category from campaign metadata."""
    name_lower = (camp.name + " " + camp.group_name).lower()
    if any(kw in name_lower for kw in ["luxy", "limo", "car service", "chauffeur", "ground transport"]):
        return "luxury_transportation"
    if any(kw in name_lower for kw in ["hotel", "hospitality"]):
        return "hospitality"
    if any(kw in name_lower for kw in ["airline", "flight", "aviation"]):
        return "aviation"
    # Default: use advertiser name as category proxy
    if snapshot and snapshot.advertiser_name:
        return snapshot.advertiser_name.lower().replace(" ", "_")
    return "general"


def get_latest_scoped_learnings():
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            date = time.strftime("%Y-%m-%d")
            key = f"{get_dcil_config().redis_prefix}:scoped_learnings:{date}"
            data = redis.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    if _MEMORY_SCOPED_LEARNINGS:
        return _MEMORY_SCOPED_LEARNINGS[max(_MEMORY_SCOPED_LEARNINGS.keys())]
    return None
