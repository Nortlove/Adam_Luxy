# =============================================================================
# Autonomous Decision Engine
# Location: adam/ops/autonomous.py
# =============================================================================

"""
Makes decisions and acts on them without human intervention.

INTERNAL decisions (adjusting our own models) are fully autonomous.
EXTERNAL decisions (recommendations to agency) require human review.

Autonomous actions the system takes:
1. Calibrate thresholds from observed data (reactance ceiling, etc.)
2. Persist and update per-person belief states on every session
3. Maintain conversion probability rankings (high-intent flagging)
4. Auto-learn mechanism effectiveness from outcomes
5. Detect and log discoveries (surprising patterns)
6. Mark users for release when puzzle solver says to let go
7. Adjust mechanism priors based on accumulated evidence

Every action is logged with reasoning in the ops log.
"""

import asyncio
import json
import logging
import math
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AutonomousDecisionEngine:
    """Takes autonomous actions based on accumulated intelligence."""

    def __init__(self, redis_client):
        self._redis = redis_client

    # ─── BELIEF STATE PERSISTENCE ─────────────────────────────────

    async def persist_belief_state(
        self, user_id: str, belief_dict: Dict
    ) -> None:
        """Persist a user's puzzle solver belief state to Redis."""
        key = f"adam:belief:{user_id}"
        await self._redis.set(key, json.dumps(belief_dict), ex=3600 * 24 * 90)

    async def load_belief_state(self, user_id: str) -> Optional[Dict]:
        """Load a persisted belief state."""
        key = f"adam:belief:{user_id}"
        raw = await self._redis.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return None

    # ─── HIGH INTENT FLAGGING ─────────────────────────────────────

    async def flag_high_intent(
        self, user_id: str, conversion_prob: float, reason: str
    ) -> None:
        """Flag a user as high-intent for priority targeting."""
        data = json.dumps({
            "user_id": user_id,
            "conversion_probability": conversion_prob,
            "reason": reason,
            "flagged_at": time.time(),
        })
        await self._redis.set(
            f"adam:high_intent:{user_id}", data, ex=3600 * 24 * 7
        )
        # Add to the high-intent list
        await self._redis.sadd("adam:high_intent:list", user_id)
        await self._redis.expire("adam:high_intent:list", 3600 * 24 * 7)

    async def get_high_intent_users(self) -> List[Dict]:
        """Get all high-intent flagged users."""
        user_ids = await self._redis.smembers("adam:high_intent:list")
        results = []
        for uid in (user_ids or []):
            raw = await self._redis.get(f"adam:high_intent:{uid}")
            if raw:
                try:
                    results.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        return sorted(results, key=lambda x: -x.get("conversion_probability", 0))

    # ─── RELEASE MARKING ──────────────────────────────────────────

    async def mark_for_release(
        self, user_id: str, reason: str
    ) -> None:
        """Mark a user for release to dormant pool."""
        data = json.dumps({
            "user_id": user_id,
            "reason": reason,
            "released_at": time.time(),
        })
        await self._redis.set(
            f"adam:released:{user_id}", data, ex=3600 * 24 * 90
        )
        await self._redis.sadd("adam:released:list", user_id)

    async def get_released_users(self) -> List[Dict]:
        """Get all released users."""
        user_ids = await self._redis.smembers("adam:released:list")
        results = []
        for uid in (user_ids or []):
            raw = await self._redis.get(f"adam:released:{uid}")
            if raw:
                try:
                    results.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        return results

    # ─── MECHANISM EFFECTIVENESS LEARNING ─────────────────────────

    async def record_mechanism_outcome(
        self,
        mechanism: str,
        archetype: str,
        converted: bool,
        belief_state: Optional[Dict] = None,
    ) -> None:
        """Record a mechanism outcome for autonomous learning.

        Tracks per-(mechanism, archetype) success rates to calibrate
        the puzzle solver's MECHANISM_PROPERTIES table from real data.
        """
        key = f"adam:mech_learn:{mechanism}:{archetype}"
        raw = await self._redis.get(key)
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"successes": 0, "trials": 0, "outcomes": []}
        else:
            data = {"successes": 0, "trials": 0, "outcomes": []}

        data["trials"] += 1
        if converted:
            data["successes"] += 1

        # Keep last 50 outcomes for trend analysis
        data["outcomes"] = (data.get("outcomes", []) + [
            {"converted": converted, "timestamp": time.time()}
        ])[-50:]

        data["effectiveness"] = data["successes"] / max(1, data["trials"])
        data["last_updated"] = time.time()

        await self._redis.set(key, json.dumps(data), ex=3600 * 24 * 90)

    async def get_mechanism_effectiveness(self) -> Dict[str, Dict]:
        """Get learned mechanism effectiveness across all archetypes."""
        results = {}
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor, match="adam:mech_learn:*", count=100
            )
            for key in keys:
                raw = await self._redis.get(key)
                if raw:
                    try:
                        parts = key.split(":")
                        mech = parts[2] if len(parts) > 2 else "unknown"
                        arch = parts[3] if len(parts) > 3 else "unknown"
                        data = json.loads(raw)
                        results.setdefault(arch, {})[mech] = {
                            "effectiveness": data.get("effectiveness", 0),
                            "trials": data.get("trials", 0),
                            "successes": data.get("successes", 0),
                        }
                    except (json.JSONDecodeError, IndexError):
                        pass
            if cursor == 0:
                break
        return results

    # ─── DISCOVERY DETECTION ──────────────────────────────────────

    async def check_for_discoveries(
        self, profiles: List[Dict], conversions: List[Dict],
    ) -> List[Dict]:
        """Detect surprising patterns in the data.

        A discovery is a pattern that is:
        1. Statistically meaningful (enough observations)
        2. Surprising (differs from prior expectation)
        3. Actionable (implies a specific change)
        """
        discoveries = []

        if len(profiles) < 10 or len(conversions) < 3:
            return discoveries

        # Discovery 1: Section engagement predicts conversion
        conv_user_ids = {c.get("visitor_id") for c in conversions}

        sections = ["section-safety", "section-reviews", "section-pricing",
                    "section-fleet", "section-booking", "section-testimonials"]

        for section in sections:
            conv_dwell = []
            non_conv_dwell = []
            for p in profiles:
                dwell = p.get("section_dwell_totals", {}).get(section, 0)
                if dwell > 0:
                    if p.get("user_id") in conv_user_ids:
                        conv_dwell.append(dwell)
                    else:
                        non_conv_dwell.append(dwell)

            if len(conv_dwell) >= 3 and len(non_conv_dwell) >= 3:
                conv_avg = sum(conv_dwell) / len(conv_dwell)
                non_avg = sum(non_conv_dwell) / len(non_conv_dwell)
                if non_avg > 0:
                    ratio = conv_avg / non_avg
                    if ratio > 1.8 or ratio < 0.5:
                        discoveries.append({
                            "type": "section_conversion_predictor",
                            "section": section,
                            "converter_avg_dwell": round(conv_avg, 1),
                            "non_converter_avg_dwell": round(non_avg, 1),
                            "ratio": round(ratio, 2),
                            "sample_size": len(conv_dwell) + len(non_conv_dwell),
                            "insight": (
                                f"Users who {'spend more' if ratio > 1 else 'spend less'} time on "
                                f"{section} are {ratio:.1f}x more likely to convert. "
                                f"This {'confirms' if section in ('section-booking', 'section-pricing') else 'is a new finding about'} "
                                f"the role of {section.replace('section-', '')} engagement."
                            ),
                            "confidence": min(0.9, 0.3 + (len(conv_dwell) + len(non_conv_dwell)) * 0.03),
                            "discovered_at": time.time(),
                        })

        # Discovery 2: Organic returns as conversion predictor
        conv_organic = [p.get("organic_sessions", 0) for p in profiles if p.get("user_id") in conv_user_ids]
        non_conv_organic = [p.get("organic_sessions", 0) for p in profiles
                          if p.get("user_id") not in conv_user_ids and p.get("total_sessions", 0) >= 2]

        if len(conv_organic) >= 3 and len(non_conv_organic) >= 3:
            conv_org_rate = sum(1 for x in conv_organic if x > 0) / len(conv_organic)
            non_org_rate = sum(1 for x in non_conv_organic if x > 0) / len(non_conv_organic)
            if non_org_rate > 0 and conv_org_rate / non_org_rate > 1.5:
                discoveries.append({
                    "type": "organic_return_predictor",
                    "converter_organic_rate": round(conv_org_rate, 3),
                    "non_converter_organic_rate": round(non_org_rate, 3),
                    "lift": round(conv_org_rate / max(0.01, non_org_rate), 2),
                    "insight": (
                        f"Users who return organically convert at {conv_org_rate/max(0.01,non_org_rate):.1f}x the rate "
                        f"of ad-only visitors. Organic return is a leading indicator of conversion. "
                        f"Users showing organic returns should receive priority implementation_intention creative."
                    ),
                    "confidence": min(0.85, 0.3 + len(conv_organic) * 0.05),
                    "discovered_at": time.time(),
                })

        # Discovery 3: Device-specific conversion patterns
        conv_devices = defaultdict(int)
        total_devices = defaultdict(int)
        for p in profiles:
            for device, count in p.get("device_impressions", {}).items():
                total_devices[device] += count
                if p.get("user_id") in conv_user_ids:
                    conv_devices[device] += count

        for device in total_devices:
            if total_devices[device] >= 5:
                device_conv_rate = conv_devices[device] / total_devices[device]
                overall_conv_rate = len(conversions) / max(1, len(profiles))
                if device_conv_rate > overall_conv_rate * 1.5 or device_conv_rate < overall_conv_rate * 0.5:
                    discoveries.append({
                        "type": "device_conversion_pattern",
                        "device": device,
                        "device_conversion_rate": round(device_conv_rate, 4),
                        "overall_conversion_rate": round(overall_conv_rate, 4),
                        "ratio": round(device_conv_rate / max(0.001, overall_conv_rate), 2),
                        "insight": (
                            f"{device} users convert at {device_conv_rate/max(0.001, overall_conv_rate):.1f}x "
                            f"the overall rate. "
                            f"{'Increase' if device_conv_rate > overall_conv_rate else 'Decrease'} "
                            f"{device} bid multiplier."
                        ),
                        "confidence": min(0.8, 0.3 + total_devices[device] * 0.02),
                        "discovered_at": time.time(),
                    })

        # Store discoveries
        for d in discoveries:
            await self._redis.lpush(
                "adam:discoveries", json.dumps(d)
            )
            await self._redis.ltrim("adam:discoveries", 0, 100)

        return discoveries

    # ─── THRESHOLD CALIBRATION ────────────────────────────────────

    async def calibrate_thresholds(
        self, profiles: List[Dict], conversions: List[Dict],
    ) -> Dict:
        """Auto-calibrate system thresholds from observed data.

        Adjusts:
        - Reactance onset threshold (from actual engagement patterns)
        - Organic surge multiplier (from observed conversion correlation)
        - Barrier confidence threshold (from override accuracy)
        """
        calibrations = {}

        if len(profiles) < 15:
            return calibrations

        # Calibrate reactance: at what touch count do users disengage?
        touch_counts = []
        for p in profiles:
            touches = len(p.get("touch_outcomes", []))
            if touches > 0:
                touch_counts.append(touches)

        if len(touch_counts) >= 10:
            avg_touches = sum(touch_counts) / len(touch_counts)
            # Reactance typically starts at 1.5x average touch count
            calibrated_reactance_touches = int(avg_touches * 1.5)
            calibrations["reactance_touch_threshold"] = {
                "current": 4,  # Our default
                "calibrated": calibrated_reactance_touches,
                "based_on": len(touch_counts),
                "action": f"Adjust frequency decay threshold from 4 to {calibrated_reactance_touches} touches",
            }

        # Store calibrations
        if calibrations:
            await self._redis.set(
                "adam:calibrations",
                json.dumps({"calibrations": calibrations, "timestamp": time.time()}),
                ex=3600 * 24 * 7,
            )

        return calibrations

    # ─── AUTONOMOUS CYCLE ─────────────────────────────────────────

    async def run_autonomous_cycle(
        self, profiles: List[Dict], conversions: List[Dict],
    ) -> Dict:
        """Run a full autonomous decision cycle.

        This is called by the ops intelligence engine after its analysis.
        It takes ACTIONS, not just generates recommendations.
        """
        results = {
            "actions_taken": [],
            "discoveries": [],
            "calibrations": {},
            "high_intent_flagged": 0,
            "released": 0,
        }

        # 1. Run puzzle solver on every profile with enough data
        from adam.retargeting.engines.puzzle_solver import PuzzleSolver
        solver = PuzzleSolver()

        for p in profiles:
            user_id = p.get("user_id", "")
            if not user_id or p.get("total_sessions", 0) < 1:
                continue

            archetype = p.get("attributed_archetype", "")
            belief = solver.create_initial_belief(archetype)
            belief = solver.update_belief(belief, p)

            # Persist belief state
            await self.persist_belief_state(user_id, belief.to_dict())

            # Get recommendation
            rec = solver.recommend_next_touch(belief)

            # Flag high intent
            if rec.conversion_probability > 0.20:
                await self.flag_high_intent(
                    user_id, rec.conversion_probability,
                    f"Puzzle solver: {rec.mechanism} (conv={rec.conversion_probability:.3f})"
                )
                results["high_intent_flagged"] += 1

            # Check for release
            should_release, reason = solver.should_release(belief)
            if should_release:
                await self.mark_for_release(user_id, reason)
                results["released"] += 1
                results["actions_taken"].append({
                    "action": "release_to_dormant",
                    "user_id": user_id,
                    "reason": reason,
                })

        # 1b. Classify impression outcomes for all profiles
        try:
            from adam.retargeting.engines.impression_classifier import ImpressionClassifier
            classifier = ImpressionClassifier()

            outcome_dist = defaultdict(int)
            ad_averse_users = []
            accelerate_users = []

            for p in profiles:
                user_id = p.get("user_id", "")
                if not user_id:
                    continue

                outcome, conf, reasoning = classifier.classify_user_response(p)
                outcome_dist[outcome.value] += 1

                persistence, action_text = classifier.compute_persistence_score(p)

                # Ad-averse: stop retargeting
                if outcome.value == "ad_averse":
                    ad_averse_users.append(user_id)
                    await self.mark_for_release(user_id, f"Ad-averse: {reasoning}")
                    results["released"] += 1

                # Accelerate: high persistence = close to converting
                if persistence > 0.3:
                    accelerate_users.append({"user_id": user_id, "score": persistence})

                # Store classification
                await self._redis.set(
                    f"adam:impression_class:{user_id}",
                    json.dumps({
                        "outcome": outcome.value,
                        "confidence": conf,
                        "persistence": persistence,
                        "reasoning": reasoning,
                        "classified_at": time.time(),
                    }),
                    ex=3600 * 24 * 7,
                )

            results["impression_classification"] = {
                "distribution": dict(outcome_dist),
                "ad_averse_detected": len(ad_averse_users),
                "accelerate_candidates": len(accelerate_users),
            }

            if ad_averse_users:
                results["actions_taken"].append({
                    "action": "ad_averse_release",
                    "count": len(ad_averse_users),
                    "reason": "Users with zero clicks, zero organic, high exposure — ad-averse personality",
                })

        except Exception as e:
            logger.warning("Impression classification failed: %s", e)

        # 2. Record mechanism outcomes from conversions
        for c in conversions:
            mech = c.get("creative_id", c.get("mechanism_sent", ""))
            arch = ""
            cid = c.get("campaign_id", "")
            if "CT" in cid.upper():
                arch = "careful_truster"
            elif "SS" in cid.upper():
                arch = "status_seeker"
            elif "ED" in cid.upper():
                arch = "easy_decider"

            if mech and arch:
                await self.record_mechanism_outcome(mech, arch, True)

        # 3. Detect discoveries
        discoveries = await self.check_for_discoveries(profiles, conversions)
        results["discoveries"] = discoveries
        if discoveries:
            results["actions_taken"].append({
                "action": "discoveries_logged",
                "count": len(discoveries),
                "types": [d["type"] for d in discoveries],
            })

        # 4. Calibrate thresholds
        calibrations = await self.calibrate_thresholds(profiles, conversions)
        results["calibrations"] = calibrations
        if calibrations:
            results["actions_taken"].append({
                "action": "thresholds_calibrated",
                "calibrations": list(calibrations.keys()),
            })

        # 5. Get mechanism effectiveness summary
        mech_eff = await self.get_mechanism_effectiveness()
        results["mechanism_effectiveness"] = mech_eff

        # 6. Run multi-dimensional learning
        try:
            from adam.retargeting.engines.learning_dimensions import get_multi_dimensional_learner
            learner = get_multi_dimensional_learner()
            learning = learner.run_full_learning_cycle(profiles, conversions)
            results["multi_dimensional_learning"] = {
                "causal_summary": learning.get("causal_summary", {}),
                "avg_ad_causal_weight": learning.get("avg_ad_causal_weight", 0),
                "temporal_windows": learning.get("temporal_windows", {}),
                "failure_eliminations": learning.get("failure_analysis", {}).get("eliminations", []),
                "transfer_insights": learning.get("transfer_insights", {}),
                "context_recommendations": learning.get("context_effectiveness", {}).get("recommendations", []),
            }

            # Store learning results for the weekly report
            await self._redis.set(
                "adam:learning:multi_dimensional",
                json.dumps(results["multi_dimensional_learning"]),
                ex=3600 * 24 * 7,
            )
        except Exception as e:
            logger.warning("Multi-dimensional learning failed: %s", e)

        return results


# Singleton
_engine: Optional[AutonomousDecisionEngine] = None


def get_autonomous_engine(redis_client=None) -> Optional[AutonomousDecisionEngine]:
    global _engine
    if _engine is None and redis_client is not None:
        _engine = AutonomousDecisionEngine(redis_client)
    return _engine
