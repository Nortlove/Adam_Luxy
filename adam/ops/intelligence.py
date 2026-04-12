# =============================================================================
# INFORMATIV Operations Intelligence Engine
# Location: adam/ops/intelligence.py
# =============================================================================

"""
Autonomous intelligence system that monitors, analyzes, decides, and reports.

Three interconnected systems:
1. DASHBOARD — Real-time system status (telemetry flow, profiles, conversions)
2. INTELLIGENCE ENGINE — Analyzes data hourly, generates recommendations
3. OPS LOG — Audit trail of every decision with reasoning

The engine runs every hour and:
- Scans all signal profiles for patterns
- Compares archetype performance
- Detects reactance, barrier shifts, organic surges
- Generates specific, actionable recommendations
- Logs every decision with the data that led to it
- Fires alerts when thresholds are breached
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


# =============================================================================
# OPS LOG — Audit Trail
# =============================================================================

class LogLevel(str, Enum):
    INFO = "info"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    ACTION = "action"
    INSIGHT = "insight"


@dataclass
class OpsLogEntry:
    """Single entry in the operations log."""
    timestamp: float = field(default_factory=time.time)
    level: str = "info"
    category: str = ""       # "archetype", "mechanism", "reactance", "barrier", "system"
    title: str = ""
    detail: str = ""
    data: Dict = field(default_factory=dict)
    recommendation: str = ""
    action_taken: str = ""
    confidence: float = 0.0


# Redis keys
_OPS_LOG_KEY = "adam:ops:log"
_OPS_ALERTS_KEY = "adam:ops:alerts"
_OPS_RECOMMENDATIONS_KEY = "adam:ops:recommendations"
_OPS_DASHBOARD_KEY = "adam:ops:dashboard"
_OPS_LAST_RUN_KEY = "adam:ops:last_intelligence_run"
_MAX_LOG_ENTRIES = 500
_MAX_ALERTS = 50


# =============================================================================
# OPERATIONS ENGINE
# =============================================================================

class OperationsIntelligenceEngine:
    """Autonomous intelligence engine for monitoring, analysis, and recommendations."""

    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client

    # ─── OPS LOG ─────────────────────────────────────────────────────

    async def log(self, entry: OpsLogEntry) -> None:
        """Write an entry to the ops log."""
        try:
            data = json.dumps(asdict(entry))
            await self._redis.lpush(_OPS_LOG_KEY, data)
            await self._redis.ltrim(_OPS_LOG_KEY, 0, _MAX_LOG_ENTRIES - 1)
        except Exception as e:
            logger.debug("Ops log write failed: %s", e)

    async def get_log(self, limit: int = 50) -> List[Dict]:
        """Get recent ops log entries."""
        try:
            entries = await self._redis.lrange(_OPS_LOG_KEY, 0, limit - 1)
            return [json.loads(e) for e in entries]
        except Exception:
            return []

    # ─── ALERTS ──────────────────────────────────────────────────────

    async def fire_alert(
        self, severity: str, title: str, detail: str,
        recommended_action: str = "", data: Dict = None,
    ) -> None:
        """Fire an alert."""
        alert = {
            "timestamp": time.time(),
            "severity": severity,
            "title": title,
            "detail": detail,
            "recommended_action": recommended_action,
            "data": data or {},
            "acknowledged": False,
        }
        try:
            await self._redis.lpush(_OPS_ALERTS_KEY, json.dumps(alert))
            await self._redis.ltrim(_OPS_ALERTS_KEY, 0, _MAX_ALERTS - 1)
        except Exception as e:
            logger.debug("Alert fire failed: %s", e)

        # Also log it
        await self.log(OpsLogEntry(
            level="alert", category="system",
            title=title, detail=detail,
            recommendation=recommended_action,
        ))

    async def get_alerts(self, limit: int = 20) -> List[Dict]:
        """Get active alerts."""
        try:
            alerts = await self._redis.lrange(_OPS_ALERTS_KEY, 0, limit - 1)
            return [json.loads(a) for a in alerts]
        except Exception:
            return []

    # ─── DASHBOARD ───────────────────────────────────────────────────

    async def build_dashboard(self) -> Dict[str, Any]:
        """Build the complete operations dashboard."""
        dashboard = {
            "timestamp": time.time(),
            "timestamp_human": datetime.now(timezone.utc).isoformat(),
            "server": {"status": "healthy"},
            "telemetry": {},
            "profiles": {},
            "conversions": {},
            "archetypes": {},
            "barriers": {},
            "alerts": [],
            "recent_recommendations": [],
        }

        try:
            # Count profiles
            cursor = 0
            profile_count = 0
            total_sessions = 0
            ad_sessions = 0
            organic_sessions = 0
            converted_count = 0
            archetype_dist = defaultdict(int)
            barrier_dist = defaultdict(int)
            reactance_count = 0

            while True:
                cursor, keys = await self._redis.scan(
                    cursor, match="adam:*NONCONSCIOUS*profile*", count=100
                )
                for key in keys:
                    raw = await self._redis.get(key)
                    if raw:
                        try:
                            p = json.loads(raw)
                            profile_count += 1
                            total_sessions += p.get("total_sessions", 0)
                            ad_sessions += p.get("ad_attributed_sessions", 0)
                            organic_sessions += p.get("organic_sessions", 0)
                            if p.get("converted"):
                                converted_count += 1
                            arch = p.get("attributed_archetype", "unclassified")
                            archetype_dist[arch] += 1
                            barrier = p.get("self_reported_barrier", "")
                            if barrier:
                                barrier_dist[barrier] += 1
                            if p.get("reactance_detected"):
                                reactance_count += 1
                        except json.JSONDecodeError:
                            pass
                if cursor == 0:
                    break

            # Count conversions
            conv_cursor = 0
            conv_count = 0
            conv_revenue = 0.0
            while True:
                conv_cursor, keys = await self._redis.scan(
                    conv_cursor, match="adam:conversion:*", count=100
                )
                for key in keys:
                    raw = await self._redis.get(key)
                    if raw:
                        try:
                            c = json.loads(raw)
                            conv_count += 1
                            conv_revenue += c.get("metadata", {}).get("revenue", 0)
                        except json.JSONDecodeError:
                            pass
                if conv_cursor == 0:
                    break

            # Population baselines
            pop_organic = await self._redis.get("adam:CacheDomain.NONCONSCIOUS:population:organic_ratio")
            pop_sessions = await self._redis.get("adam:CacheDomain.NONCONSCIOUS:population:total_sessions")

            dashboard["telemetry"] = {
                "total_sessions_tracked": total_sessions,
                "ad_attributed_sessions": ad_sessions,
                "organic_sessions": organic_sessions,
                "population_sessions": int(pop_sessions or 0),
                "population_organic_ratio": float(pop_organic or 0),
            }

            dashboard["profiles"] = {
                "total_profiles": profile_count,
                "with_archetype": sum(v for k, v in archetype_dist.items() if k != "unclassified"),
                "reactance_detected": reactance_count,
                "reactance_rate": reactance_count / max(1, profile_count),
            }

            dashboard["conversions"] = {
                "total_conversions": conv_count,
                "total_revenue": round(conv_revenue, 2),
                "avg_revenue": round(conv_revenue / max(1, conv_count), 2),
            }

            dashboard["archetypes"] = dict(archetype_dist)
            dashboard["barriers"] = dict(sorted(barrier_dist.items(), key=lambda x: -x[1]))

            # Recent alerts and recommendations
            dashboard["alerts"] = await self.get_alerts(limit=5)
            dashboard["recent_recommendations"] = await self.get_recommendations(limit=5)

        except Exception as e:
            dashboard["error"] = str(e)
            logger.warning("Dashboard build error: %s", e)

        # Cache the dashboard
        try:
            await self._redis.set(_OPS_DASHBOARD_KEY, json.dumps(dashboard), ex=300)
        except Exception:
            pass

        return dashboard

    # ─── RECOMMENDATIONS ─────────────────────────────────────────────

    async def store_recommendation(self, rec: Dict) -> None:
        """Store a recommendation."""
        rec["timestamp"] = time.time()
        rec["timestamp_human"] = datetime.now(timezone.utc).isoformat()
        try:
            await self._redis.lpush(_OPS_RECOMMENDATIONS_KEY, json.dumps(rec))
            await self._redis.ltrim(_OPS_RECOMMENDATIONS_KEY, 0, 100)
        except Exception:
            pass

    async def get_recommendations(self, limit: int = 20) -> List[Dict]:
        """Get recent recommendations."""
        try:
            recs = await self._redis.lrange(_OPS_RECOMMENDATIONS_KEY, 0, limit - 1)
            return [json.loads(r) for r in recs]
        except Exception:
            return []

    # ─── INTELLIGENCE ANALYSIS (runs hourly) ─────────────────────────

    async def run_intelligence_cycle(self) -> Dict:
        """Run a full intelligence analysis cycle.

        Scans all profiles, analyzes patterns, generates recommendations,
        fires alerts, logs everything.
        """
        cycle_start = time.time()
        results = {"recommendations": [], "alerts": [], "insights": []}

        await self.log(OpsLogEntry(
            level="info", category="system",
            title="Intelligence cycle started",
        ))

        # Load all profiles
        profiles = []
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor, match="adam:*NONCONSCIOUS*profile*", count=100
            )
            for key in keys:
                raw = await self._redis.get(key)
                if raw:
                    try:
                        profiles.append(json.loads(raw))
                    except json.JSONDecodeError:
                        pass
            if cursor == 0:
                break

        if not profiles:
            await self.log(OpsLogEntry(
                level="info", category="system",
                title="No profiles to analyze",
                detail="Intelligence cycle complete — waiting for telemetry data",
            ))
            return results

        # Load conversions
        conversions = []
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor, match="adam:conversion:*", count=100
            )
            for key in keys:
                raw = await self._redis.get(key)
                if raw:
                    try:
                        conversions.append(json.loads(raw))
                    except json.JSONDecodeError:
                        pass
            if cursor == 0:
                break

        # ── Analysis 1: Archetype Performance ──

        archetype_profiles = defaultdict(list)
        for p in profiles:
            arch = p.get("attributed_archetype", "unclassified")
            archetype_profiles[arch].append(p)

        for arch, arch_profiles in archetype_profiles.items():
            if arch == "unclassified" or arch == "":
                continue

            n = len(arch_profiles)
            avg_sessions = sum(p.get("total_sessions", 0) for p in arch_profiles) / max(1, n)
            organic_rate = sum(
                p.get("organic_sessions", 0) / max(1, p.get("total_sessions", 1))
                for p in arch_profiles
            ) / max(1, n)
            reactance_rate = sum(1 for p in arch_profiles if p.get("reactance_detected")) / max(1, n)

            insight = {
                "archetype": arch,
                "profiles": n,
                "avg_sessions": round(avg_sessions, 1),
                "organic_rate": round(organic_rate, 3),
                "reactance_rate": round(reactance_rate, 3),
            }
            results["insights"].append(insight)

            # Reactance alert
            if reactance_rate > 0.20 and n >= 5:
                rec = {
                    "type": "frequency_adjustment",
                    "archetype": arch,
                    "severity": "high",
                    "title": f"{arch}: {reactance_rate:.0%} reactance rate",
                    "detail": f"{int(reactance_rate * n)}/{n} users showing engagement decline. "
                              f"Current frequency may be too aggressive.",
                    "recommendation": f"Reduce {arch} frequency cap by 30% or increase "
                                      f"min hours between impressions.",
                    "data": insight,
                    "confidence": min(0.95, 0.5 + n * 0.05),
                }
                results["recommendations"].append(rec)
                await self.store_recommendation(rec)
                await self.fire_alert("high", rec["title"], rec["detail"], rec["recommendation"])

            # Organic surge insight
            if organic_rate > 0.4 and n >= 3:
                rec = {
                    "type": "stage_transition",
                    "archetype": arch,
                    "severity": "medium",
                    "title": f"{arch}: High organic return rate ({organic_rate:.0%})",
                    "detail": f"Users are returning on their own — internal motivation forming. "
                              f"Consider shifting from awareness to implementation-focused creative.",
                    "recommendation": f"For {arch}: shift budget from Touch 1-2 to Touch 4-5. "
                                      f"These users don't need more awareness — they need friction removal.",
                    "data": insight,
                    "confidence": min(0.90, 0.4 + n * 0.05),
                }
                results["recommendations"].append(rec)
                await self.store_recommendation(rec)

        # ── Analysis 2: Barrier Distribution ──

        barrier_counts = defaultdict(int)
        for p in profiles:
            barrier = p.get("self_reported_barrier", "")
            if barrier:
                barrier_counts[barrier] += 1

        if barrier_counts:
            top_barrier = max(barrier_counts, key=barrier_counts.get)
            top_count = barrier_counts[top_barrier]
            total_with_barrier = sum(barrier_counts.values())
            top_pct = top_count / max(1, total_with_barrier)

            if top_pct > 0.5 and total_with_barrier >= 5:
                rec = {
                    "type": "creative_focus",
                    "severity": "medium",
                    "title": f"Dominant barrier: {top_barrier} ({top_pct:.0%} of users)",
                    "detail": f"{top_count}/{total_with_barrier} users show {top_barrier} as "
                              f"primary barrier. Creative should directly address this.",
                    "recommendation": f"Ensure Touch 2-3 creative copy directly addresses "
                                      f"{top_barrier}. Consider A/B test with barrier-specific variant.",
                    "data": {"barrier_distribution": dict(barrier_counts)},
                    "confidence": min(0.85, 0.4 + total_with_barrier * 0.03),
                }
                results["recommendations"].append(rec)
                await self.store_recommendation(rec)

        # ── Analysis 3: Conversion Patterns ──

        if conversions:
            conv_archetypes = defaultdict(int)
            conv_mechanisms = defaultdict(int)
            conv_barriers = defaultdict(int)

            for c in conversions:
                arch = ""
                cid = c.get("campaign_id", "")
                if "CT" in cid.upper():
                    arch = "careful_truster"
                elif "SS" in cid.upper():
                    arch = "status_seeker"
                elif "ED" in cid.upper():
                    arch = "easy_decider"
                if arch:
                    conv_archetypes[arch] += 1

                mech = c.get("creative_id", "")
                if mech:
                    conv_mechanisms[mech] += 1

                barrier = c.get("self_reported_barrier", "")
                if barrier:
                    conv_barriers[barrier] += 1

            if conv_archetypes:
                insight = {
                    "type": "conversion_distribution",
                    "by_archetype": dict(conv_archetypes),
                    "by_mechanism": dict(conv_mechanisms),
                    "by_barrier_at_conversion": dict(conv_barriers),
                    "total": len(conversions),
                }
                results["insights"].append(insight)

                # Check if one archetype is significantly outperforming
                if len(conv_archetypes) >= 2:
                    sorted_archs = sorted(conv_archetypes.items(), key=lambda x: -x[1])
                    best_arch, best_count = sorted_archs[0]
                    second_arch, second_count = sorted_archs[1]

                    if best_count >= second_count * 2 and best_count >= 3:
                        rec = {
                            "type": "budget_reallocation",
                            "severity": "high",
                            "title": f"{best_arch} converting at {best_count/max(1,second_count):.1f}x rate of {second_arch}",
                            "detail": f"{best_arch}: {best_count} conversions, {second_arch}: {second_count}. "
                                      f"Consider reallocating budget toward the higher-converting archetype.",
                            "recommendation": f"Increase {best_arch} daily budget by 20%. "
                                              f"Decrease {second_arch} by 10%. Monitor for 3 days.",
                            "data": insight,
                            "confidence": min(0.80, 0.3 + best_count * 0.1),
                        }
                        results["recommendations"].append(rec)
                        await self.store_recommendation(rec)

        # ── Analysis 4: Telemetry Flow Health ──

        last_session_ts = 0
        for p in profiles:
            ts = p.get("last_updated", 0)
            if ts > last_session_ts:
                last_session_ts = ts

        hours_since_last = (time.time() - last_session_ts) / 3600 if last_session_ts > 0 else 999
        if hours_since_last > 2:
            await self.fire_alert(
                "critical" if hours_since_last > 6 else "warning",
                f"Telemetry flow gap: {hours_since_last:.1f} hours",
                "No new telemetry sessions received. Check GTM tags on luxyride.com.",
                "Verify INFORMATIV telemetry tag is firing in GTM. Check browser console for errors.",
                {"hours_since_last_session": round(hours_since_last, 1)},
            )

        # ── Autonomous decisions ──

        try:
            from adam.ops.autonomous import get_autonomous_engine
            auto = get_autonomous_engine(self._redis)
            if auto:
                auto_results = await auto.run_autonomous_cycle(profiles, conversions)
                results["autonomous"] = {
                    "actions_taken": len(auto_results.get("actions_taken", [])),
                    "discoveries": len(auto_results.get("discoveries", [])),
                    "high_intent_flagged": auto_results.get("high_intent_flagged", 0),
                    "released": auto_results.get("released", 0),
                    "mechanism_effectiveness": auto_results.get("mechanism_effectiveness", {}),
                }

                # Log each autonomous action
                for action in auto_results.get("actions_taken", []):
                    await self.log(OpsLogEntry(
                        level="action", category=action.get("action", "unknown"),
                        title=f"Autonomous: {action.get('action', '')}",
                        detail=json.dumps(action)[:500],
                        action_taken=action.get("action", ""),
                    ))

                # Log discoveries
                for disc in auto_results.get("discoveries", []):
                    await self.log(OpsLogEntry(
                        level="insight", category=disc.get("type", "unknown"),
                        title=f"Discovery: {disc.get('type', '')}",
                        detail=disc.get("insight", ""),
                        data=disc,
                        confidence=disc.get("confidence", 0),
                    ))
        except Exception as e:
            logger.warning("Autonomous cycle failed: %s", e)

        # ── Log cycle completion ──

        cycle_duration = time.time() - cycle_start
        await self.log(OpsLogEntry(
            level="info", category="system",
            title="Intelligence cycle complete",
            detail=f"Analyzed {len(profiles)} profiles, {len(conversions)} conversions. "
                   f"Generated {len(results['recommendations'])} recommendations. "
                   f"Autonomous: {results.get('autonomous', {}).get('actions_taken', 0)} actions, "
                   f"{results.get('autonomous', {}).get('discoveries', 0)} discoveries. "
                   f"Duration: {time.time() - cycle_start:.1f}s.",
            data={
                "profiles_analyzed": len(profiles),
                "conversions_analyzed": len(conversions),
                "recommendations_generated": len(results["recommendations"]),
                "autonomous_actions": results.get("autonomous", {}).get("actions_taken", 0),
                "discoveries": results.get("autonomous", {}).get("discoveries", 0),
                "duration_seconds": round(time.time() - cycle_start, 1),
            },
        ))

        await self._redis.set(_OPS_LAST_RUN_KEY, json.dumps({
            "timestamp": time.time(),
            "profiles": len(profiles),
            "conversions": len(conversions),
            "recommendations": len(results["recommendations"]),
            "autonomous_actions": results.get("autonomous", {}).get("actions_taken", 0),
        }))

        return results


# =============================================================================
# SCHEDULER — Runs intelligence cycle hourly
# =============================================================================

_engine: Optional[OperationsIntelligenceEngine] = None
_shutdown = False


async def _intelligence_loop():
    """Run intelligence cycle every hour."""
    global _shutdown

    # Defer first run by 10 minutes (let server stabilize)
    for _ in range(60):
        if _shutdown:
            return
        await asyncio.sleep(10)

    logger.info("Operations Intelligence Engine started")

    while not _shutdown:
        try:
            if _engine:
                results = await _engine.run_intelligence_cycle()
                n_recs = len(results.get("recommendations", []))
                if n_recs > 0:
                    logger.info("Intelligence cycle: %d recommendations generated", n_recs)
        except Exception as e:
            logger.warning("Intelligence cycle error: %s", e)

        # Sleep 1 hour, checking for shutdown every 30 seconds
        for _ in range(120):
            if _shutdown:
                return
            await asyncio.sleep(30)


async def start_ops_intelligence(redis_client) -> OperationsIntelligenceEngine:
    """Start the operations intelligence engine."""
    global _engine, _shutdown
    _shutdown = False
    _engine = OperationsIntelligenceEngine(redis_client)
    asyncio.create_task(_intelligence_loop())
    logger.info("Operations Intelligence Engine scheduled (first run in 10 minutes)")
    return _engine


def get_ops_engine() -> Optional[OperationsIntelligenceEngine]:
    """Get the ops engine singleton."""
    return _engine
