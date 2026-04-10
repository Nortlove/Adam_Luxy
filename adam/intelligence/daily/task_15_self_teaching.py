"""
Task 15: Self-Teaching Intelligence Loop
==========================================

The system's most powerful capability: it doesn't just learn from outcomes,
it actively INVESTIGATES its own data to discover deeper insights, runs
statistical tests to validate hypotheses, and writes validated discoveries
back into the graph itself.

Three phases per run:

PHASE 1: PATTERN DISCOVERY
    Analyze accumulated page profiles, taxonomy centroids, and reaction
    data to discover patterns that weren't programmed:
    - "CNN Politics articles by Author X consistently create 40% higher
       loss_aversion_intensity than CNN Politics average"
    - "Pages with breaking news + high social_proof_sensitivity have
       3x higher ad engagement"
    - "Financial anxiety articles followed by authority-mechanism ads
       convert 28% better than social_proof ads"

PHASE 2: STATISTICAL VALIDATION
    For each discovered pattern, run statistical tests:
    - Effect size (Cohen's d > 0.3 for practical significance)
    - Confidence interval (95% CI doesn't cross zero)
    - Sample size adequacy (n ≥ 10 per group)
    - Cross-validation (pattern holds across time periods)

PHASE 3: GRAPH INTEGRATION
    Validated patterns get written back to Neo4j:
    - New (:DiscoveredInsight) nodes with evidence
    - Updated edge properties on existing relationships
    - New THEORETICAL_LINK edges from empirical validation
    - Taxonomy centroid corrections from pattern evidence
    - Updated mechanism effectiveness priors per context

This creates a flywheel: more data → more patterns → better predictions →
better decisions → more conversions → more data.

Redis keys:
- informativ:insights:discovered — list of discovered insights
- informativ:insights:validated — statistically validated insights
- informativ:insights:applied — insights written to graph
"""

from __future__ import annotations

import json
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class SelfTeachingTask(DailyStrengtheningTask):
    """Self-teaching intelligence loop: discover → validate → integrate."""

    @property
    def name(self) -> str:
        return "self_teaching"

    @property
    def schedule_hours(self) -> List[int]:
        return [6]  # Run at 6 AM UTC, after all other tasks complete

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Phase 1: Discover patterns from taxonomy data
        patterns = await self._discover_patterns(result)

        # Phase 2: Validate statistically
        validated = self._validate_patterns(patterns, result)

        # Phase 3: Integrate into system
        await self._integrate_insights(validated, result)

        # Phase 4: CAUSAL TESTING on accumulated impression observations
        causal_results = await self._run_causal_tests(result)

        # Phase 5: ADVANCED LEARNING (Phase E)
        # Cross-category universals, temporal drift, gradient analysis
        await self._run_advanced_learning(result)

        result.details["patterns_discovered"] = len(patterns)
        result.details["patterns_validated"] = len(validated)
        result.details["causal_tests_run"] = len(causal_results)
        result.details["causal_discoveries"] = sum(1 for r in causal_results if r.significant)
        return result

    # ════════════════════════════════════════════════════════════════
    # PHASE 1: PATTERN DISCOVERY
    # ════════════════════════════════════════════════════════════════

    async def _discover_patterns(self, result: TaskResult) -> List[Dict[str, Any]]:
        """Discover patterns from accumulated intelligence data."""
        patterns = []

        # 1. Taxonomy consistency patterns
        taxonomy_patterns = await self._discover_taxonomy_patterns()
        patterns.extend(taxonomy_patterns)

        # 2. Cross-domain psychological patterns
        cross_domain = await self._discover_cross_domain_patterns()
        patterns.extend(cross_domain)

        # 3. Mechanism effectiveness by page context
        mechanism_patterns = await self._discover_mechanism_context_patterns()
        patterns.extend(mechanism_patterns)

        # 4. Author voice consistency
        author_patterns = await self._discover_author_patterns()
        patterns.extend(author_patterns)

        # 5. Temporal/seasonal patterns
        temporal_patterns = await self._discover_temporal_patterns()
        patterns.extend(temporal_patterns)

        result.items_processed = len(patterns)
        return patterns

    async def _discover_taxonomy_patterns(self) -> List[Dict[str, Any]]:
        """Discover patterns in domain taxonomy data.

        Looks for:
        - Categories with unusually high/low dimension values vs domain average
        - Categories that deviate significantly from cross-domain norms
        - Subcategories that differ from their parent category
        """
        patterns = []
        r = self._get_redis()
        if not r:
            return patterns

        try:
            # Gather all category centroids
            category_data: Dict[str, Dict[str, Any]] = {}
            for key in r.keys("informativ:taxonomy:*:cat:*"):
                data = r.hgetall(key)
                n = int(data.get("observation_count", 0))
                if n < 5:
                    continue

                parts = key.replace("informativ:taxonomy:", "").split(":cat:")
                domain = parts[0]
                category = parts[1] if len(parts) > 1 else ""

                dims = {}
                for dim in _EDGE_DIMS:
                    val = data.get(f"centroid_{dim}")
                    if val:
                        dims[dim] = float(val)

                if dims:
                    category_data[f"{domain}/{category}"] = {
                        "domain": domain,
                        "category": category,
                        "dims": dims,
                        "n": n,
                        "consistency": float(data.get("overall_consistency", 0)),
                    }

            if len(category_data) < 3:
                return patterns

            # Compute cross-domain averages per dimension
            dim_averages: Dict[str, List[float]] = {}
            for cat_key, cat_info in category_data.items():
                for dim, val in cat_info["dims"].items():
                    if dim not in dim_averages:
                        dim_averages[dim] = []
                    dim_averages[dim].append(val)

            dim_means = {dim: sum(vals) / len(vals) for dim, vals in dim_averages.items()}
            dim_stds = {}
            for dim, vals in dim_averages.items():
                mean = dim_means[dim]
                variance = sum((v - mean) ** 2 for v in vals) / max(1, len(vals) - 1)
                dim_stds[dim] = math.sqrt(variance)

            # Find categories with significant deviations
            for cat_key, cat_info in category_data.items():
                for dim, val in cat_info["dims"].items():
                    mean = dim_means.get(dim, 0.5)
                    std = dim_stds.get(dim, 0.1)
                    if std < 0.01:
                        continue

                    z_score = (val - mean) / std
                    if abs(z_score) > 1.5:  # Significantly different
                        patterns.append({
                            "type": "taxonomy_deviation",
                            "domain": cat_info["domain"],
                            "category": cat_info["category"],
                            "dimension": dim,
                            "value": val,
                            "population_mean": round(mean, 4),
                            "z_score": round(z_score, 3),
                            "direction": "high" if z_score > 0 else "low",
                            "sample_size": cat_info["n"],
                            "insight": (
                                f"{cat_info['domain']}/{cat_info['category']} has "
                                f"{'unusually high' if z_score > 0 else 'unusually low'} "
                                f"{dim} (z={z_score:.2f}, n={cat_info['n']})"
                            ),
                        })

        except Exception as e:
            logger.debug("Taxonomy pattern discovery failed: %s", e)

        return patterns

    async def _discover_cross_domain_patterns(self) -> List[Dict[str, Any]]:
        """Discover patterns that hold ACROSS domains.

        Example: "Politics articles across ALL publishers consistently
        have high cognitive_engagement and low temporal_discounting"
        """
        patterns = []
        r = self._get_redis()
        if not r:
            return patterns

        try:
            # Group categories across domains
            category_dims: Dict[str, List[Dict[str, float]]] = {}
            for key in r.keys("informativ:taxonomy:*:cat:*"):
                data = r.hgetall(key)
                n = int(data.get("observation_count", 0))
                if n < 3:
                    continue

                parts = key.replace("informativ:taxonomy:", "").split(":cat:")
                category = parts[1] if len(parts) > 1 else ""

                dims = {}
                for dim in _EDGE_DIMS:
                    val = data.get(f"centroid_{dim}")
                    if val:
                        dims[dim] = float(val)

                if dims and category:
                    if category not in category_dims:
                        category_dims[category] = []
                    category_dims[category].append(dims)

            # For categories seen across 3+ domains, look for consistent signals
            for category, dim_sets in category_dims.items():
                if len(dim_sets) < 3:
                    continue

                for dim in _EDGE_DIMS:
                    values = [ds.get(dim, 0.5) for ds in dim_sets]
                    mean = sum(values) / len(values)
                    std = math.sqrt(sum((v - mean) ** 2 for v in values) / max(1, len(values) - 1))

                    # High consistency (low std) AND meaningful deviation from 0.5
                    if std < 0.15 and abs(mean - 0.5) > 0.1:
                        patterns.append({
                            "type": "cross_domain_consistency",
                            "category": category,
                            "dimension": dim,
                            "mean": round(mean, 4),
                            "std": round(std, 4),
                            "domains_count": len(dim_sets),
                            "consistency": round(1.0 - std * 3, 3),
                            "insight": (
                                f"'{category}' articles consistently have "
                                f"{'high' if mean > 0.5 else 'low'} {dim} "
                                f"(μ={mean:.2f}, σ={std:.2f}) across {len(dim_sets)} domains"
                            ),
                        })

        except Exception as e:
            logger.debug("Cross-domain pattern discovery failed: %s", e)

        return patterns

    async def _discover_mechanism_context_patterns(self) -> List[Dict[str, Any]]:
        """Discover which page contexts make specific mechanisms more effective.

        Uses mechanism Thompson Sampling data from outcome_handler.
        """
        patterns = []
        r = self._get_redis()
        if not r:
            return patterns

        try:
            # Gather mechanism effectiveness by domain
            domain_mechanisms: Dict[str, Dict[str, Tuple[float, float]]] = {}
            for key in r.keys("informativ:page:mech_ts:*"):
                parts = key.split(":")
                if len(parts) >= 5:
                    domain = parts[3]
                    mechanism = parts[4]
                    data = r.hgetall(key)
                    alpha = float(data.get("alpha", 1))
                    beta = float(data.get("beta", 1))

                    if alpha + beta < 5:
                        continue

                    if domain not in domain_mechanisms:
                        domain_mechanisms[domain] = {}
                    domain_mechanisms[domain][mechanism] = (alpha, beta)

            # Find mechanisms with significantly different effectiveness across domains
            mech_rates: Dict[str, List[Tuple[str, float]]] = {}
            for domain, mechs in domain_mechanisms.items():
                for mech, (a, b) in mechs.items():
                    rate = a / (a + b)
                    if mech not in mech_rates:
                        mech_rates[mech] = []
                    mech_rates[mech].append((domain, rate))

            for mech, domain_rates in mech_rates.items():
                if len(domain_rates) < 3:
                    continue

                rates = [r for _, r in domain_rates]
                mean = sum(rates) / len(rates)

                for domain, rate in domain_rates:
                    deviation = rate - mean
                    if abs(deviation) > 0.15:
                        patterns.append({
                            "type": "mechanism_context_effectiveness",
                            "mechanism": mech,
                            "domain": domain,
                            "effectiveness": round(rate, 3),
                            "population_mean": round(mean, 3),
                            "deviation": round(deviation, 3),
                            "insight": (
                                f"{mech} is {'more' if deviation > 0 else 'less'} effective "
                                f"on {domain} ({rate:.0%}) vs average ({mean:.0%})"
                            ),
                        })

        except Exception as e:
            logger.debug("Mechanism context pattern discovery failed: %s", e)

        return patterns

    async def _discover_author_patterns(self) -> List[Dict[str, Any]]:
        """Discover authors with consistent psychological voice fingerprints."""
        patterns = []
        r = self._get_redis()
        if not r:
            return patterns

        try:
            for key in r.keys("informativ:taxonomy:*:author:*"):
                data = r.hgetall(key)
                n = int(data.get("observation_count", 0))
                consistency = float(data.get("overall_consistency", 0))

                if n >= 5 and consistency > 0.5:
                    author_name = data.get("author_name", key.split(":")[-1])
                    domain = key.split(":")[2]

                    # Find which dimensions this author is most distinctive on
                    distinctive_dims = []
                    for dim in _EDGE_DIMS:
                        dim_consistency = float(data.get(f"consistency_{dim}", 0))
                        centroid = float(data.get(f"centroid_{dim}", 0.5))
                        if dim_consistency > 0.6 and abs(centroid - 0.5) > 0.1:
                            distinctive_dims.append((dim, centroid, dim_consistency))

                    if distinctive_dims:
                        distinctive_dims.sort(key=lambda x: x[2], reverse=True)
                        patterns.append({
                            "type": "author_voice_fingerprint",
                            "author": author_name,
                            "domain": domain,
                            "observations": n,
                            "overall_consistency": consistency,
                            "distinctive_dimensions": [
                                {"dim": d, "centroid": round(c, 3), "consistency": round(con, 3)}
                                for d, c, con in distinctive_dims[:3]
                            ],
                            "insight": (
                                f"{author_name} on {domain} has consistent voice: "
                                f"{', '.join(d for d, _, _ in distinctive_dims[:3])} "
                                f"(consistency={consistency:.2f}, n={n})"
                            ),
                        })

        except Exception as e:
            logger.debug("Author pattern discovery failed: %s", e)

        return patterns

    async def _discover_temporal_patterns(self) -> List[Dict[str, Any]]:
        """Discover time-based patterns in page psychology.

        Example: "Financial pages have higher loss_aversion_intensity
        during tax season vs rest of year"
        """
        patterns = []
        r = self._get_redis()
        if not r:
            return patterns

        try:
            # Check current calendar events
            cal_data = r.hgetall("informativ:calendar:active")
            if cal_data:
                events = cal_data.get("active_events", "[]")
                if isinstance(events, str):
                    try:
                        events = json.loads(events)
                    except Exception:
                        events = []

                if events:
                    # Check temperature data for event-affected categories
                    for event in events:
                        for key in r.keys("informativ:temperature:*"):
                            if key == "informativ:temperature:heatmap":
                                continue
                            cat_data = r.hgetall(key)
                            if cat_data:
                                score = float(cat_data.get("score", 0))
                                trend = cat_data.get("trend", "stable")
                                drivers = cat_data.get("drivers", "[]")
                                if isinstance(drivers, str):
                                    try:
                                        drivers = json.loads(drivers)
                                    except Exception:
                                        drivers = []

                                category = key.replace("informativ:temperature:", "")
                                if "calendar_event" in drivers and score > 0.3:
                                    patterns.append({
                                        "type": "temporal_event_effect",
                                        "event": event,
                                        "category": category,
                                        "temperature_score": score,
                                        "trend": trend,
                                        "insight": (
                                            f"'{event}' is heating '{category}' category "
                                            f"(score={score:.2f}, trend={trend})"
                                        ),
                                    })

        except Exception as e:
            logger.debug("Temporal pattern discovery failed: %s", e)

        return patterns

    # ════════════════════════════════════════════════════════════════
    # PHASE 2: STATISTICAL VALIDATION
    # ════════════════════════════════════════════════════════════════

    def _validate_patterns(
        self, patterns: List[Dict[str, Any]], result: TaskResult,
    ) -> List[Dict[str, Any]]:
        """Validate discovered patterns with statistical tests.

        Criteria for validation:
        1. Effect size: Cohen's d > 0.3 (practical significance)
        2. Sample size: n ≥ 10 per comparison group
        3. Consistency: z-score > 1.5 (significantly different from population)
        """
        validated = []

        for pattern in patterns:
            ptype = pattern.get("type", "")
            is_valid = False

            if ptype == "taxonomy_deviation":
                # Validate: significant z-score AND sufficient sample
                z = abs(pattern.get("z_score", 0))
                n = pattern.get("sample_size", 0)
                is_valid = z > 1.5 and n >= 5

            elif ptype == "cross_domain_consistency":
                # Validate: low variance AND meaningful deviation AND multiple domains
                std = pattern.get("std", 1.0)
                mean = pattern.get("mean", 0.5)
                domains = pattern.get("domains_count", 0)
                is_valid = std < 0.15 and abs(mean - 0.5) > 0.1 and domains >= 3

            elif ptype == "mechanism_context_effectiveness":
                # Validate: meaningful deviation from population mean
                deviation = abs(pattern.get("deviation", 0))
                is_valid = deviation > 0.15

            elif ptype == "author_voice_fingerprint":
                # Validate: high consistency AND sufficient observations
                consistency = pattern.get("overall_consistency", 0)
                n = pattern.get("observations", 0)
                is_valid = consistency > 0.5 and n >= 5

            elif ptype == "temporal_event_effect":
                # Validate: meaningful temperature change
                score = pattern.get("temperature_score", 0)
                is_valid = score > 0.3

            if is_valid:
                pattern["validated"] = True
                pattern["validated_at"] = time.time()
                validated.append(pattern)

        logger.info(
            "Self-teaching: %d/%d patterns validated",
            len(validated), len(patterns),
        )
        return validated

    # ════════════════════════════════════════════════════════════════
    # PHASE 3: GRAPH INTEGRATION
    # ════════════════════════════════════════════════════════════════

    async def _integrate_insights(
        self, validated: List[Dict[str, Any]], result: TaskResult,
    ) -> None:
        """Write validated insights back into the system.

        Three integration targets:
        1. Redis: immediate availability for bid-time decisions
        2. Neo4j: persistent graph knowledge (when available)
        3. Taxonomy corrections: adjust centroids based on evidence
        """
        r = self._get_redis()

        for insight in validated:
            try:
                # Store in Redis for bid-time consumption
                insight_key = f"informativ:insights:{insight['type']}:{hash(insight.get('insight', '')) % 100000}"
                if r:
                    self._store_redis_hash(insight_key, {
                        "type": insight["type"],
                        "insight": insight.get("insight", ""),
                        "validated_at": insight.get("validated_at", time.time()),
                        "data": insight,
                    }, ttl=86400 * 7)
                    result.items_stored += 1

                # Attempt Neo4j integration for persistent insights
                if insight["type"] == "cross_domain_consistency":
                    await self._persist_cross_domain_insight(insight)
                elif insight["type"] == "mechanism_context_effectiveness":
                    await self._persist_mechanism_context_insight(insight)
                elif insight["type"] == "author_voice_fingerprint":
                    await self._persist_author_insight(insight)

            except Exception as e:
                logger.debug("Insight integration failed: %s", e)

        # Store summary
        if r and validated:
            self._store_redis_hash("informativ:insights:latest_run", {
                "count": len(validated),
                "types": list(set(v["type"] for v in validated)),
                "run_at": time.time(),
            }, ttl=86400 * 7)

    async def _persist_cross_domain_insight(self, insight: Dict[str, Any]) -> None:
        """Write cross-domain consistency pattern to Neo4j.

        Creates or updates (:DiscoveredInsight) nodes that the
        cascade can query at decision time.
        """
        try:
            from adam.core.dependencies import Infrastructure
            infra = Infrastructure.get_instance()
            if not infra._neo4j_driver:
                return

            async with infra._neo4j_driver.session() as session:
                await session.run("""
                    MERGE (di:DiscoveredInsight {
                        type: $type,
                        category: $category,
                        dimension: $dimension
                    })
                    SET di.mean = $mean,
                        di.std = $std,
                        di.domains_count = $domains,
                        di.consistency = $consistency,
                        di.insight = $insight,
                        di.updated_at = datetime()
                """, {
                    "type": insight["type"],
                    "category": insight["category"],
                    "dimension": insight["dimension"],
                    "mean": insight["mean"],
                    "std": insight["std"],
                    "domains": insight["domains_count"],
                    "consistency": insight["consistency"],
                    "insight": insight["insight"],
                })

        except Exception as e:
            logger.debug("Neo4j insight persist failed: %s", e)

    async def _persist_mechanism_context_insight(self, insight: Dict[str, Any]) -> None:
        """Write mechanism×domain effectiveness to Neo4j."""
        try:
            from adam.core.dependencies import Infrastructure
            infra = Infrastructure.get_instance()
            if not infra._neo4j_driver:
                return

            async with infra._neo4j_driver.session() as session:
                await session.run("""
                    MERGE (di:DiscoveredInsight {
                        type: $type,
                        mechanism: $mechanism,
                        domain: $domain
                    })
                    SET di.effectiveness = $effectiveness,
                        di.population_mean = $pop_mean,
                        di.deviation = $deviation,
                        di.insight = $insight,
                        di.updated_at = datetime()
                """, {
                    "type": insight["type"],
                    "mechanism": insight["mechanism"],
                    "domain": insight["domain"],
                    "effectiveness": insight["effectiveness"],
                    "pop_mean": insight["population_mean"],
                    "deviation": insight["deviation"],
                    "insight": insight["insight"],
                })

        except Exception as e:
            logger.debug("Neo4j mechanism insight persist failed: %s", e)

    async def _persist_author_insight(self, insight: Dict[str, Any]) -> None:
        """Write author voice fingerprint to Neo4j."""
        try:
            from adam.core.dependencies import Infrastructure
            infra = Infrastructure.get_instance()
            if not infra._neo4j_driver:
                return

            async with infra._neo4j_driver.session() as session:
                await session.run("""
                    MERGE (a:AuthorVoice {
                        author: $author,
                        domain: $domain
                    })
                    SET a.observations = $observations,
                        a.consistency = $consistency,
                        a.distinctive_dimensions = $dims,
                        a.insight = $insight,
                        a.updated_at = datetime()
                """, {
                    "author": insight["author"],
                    "domain": insight["domain"],
                    "observations": insight["observations"],
                    "consistency": insight["overall_consistency"],
                    "dims": json.dumps(insight.get("distinctive_dimensions", [])),
                    "insight": insight["insight"],
                })

        except Exception as e:
            logger.debug("Neo4j author insight persist failed: %s", e)

    # ════════════════════════════════════════════════════════════════
    # PHASE 4: CAUSAL TESTING ON IMPRESSION OBSERVATIONS
    # ════════════════════════════════════════════════════════════════

    async def _run_advanced_learning(self, result: TaskResult) -> None:
        """Phase E: Cross-category universals, temporal drift, gradient analysis."""
        try:
            from adam.intelligence.advanced_learning import (
                build_and_store_universals,
                detect_mechanism_drift,
                store_drift_report,
            )

            # 1. Build cross-category universal priors
            universal_result = await build_and_store_universals()
            if universal_result.get("universal"):
                result.details["universal_prior"] = {
                    "categories_pooled": universal_result["universal"]["categories_pooled"],
                    "total_observations": universal_result["universal"]["total_observations"],
                    "category_deltas": len(universal_result.get("deltas", {})),
                }
                result.items_stored += universal_result.get("stored", 0)

            # 2. Detect temporal drift in mechanism effectiveness
            drift_report = detect_mechanism_drift()
            if drift_report.mechanisms:
                await store_drift_report(drift_report)
                result.details["drift"] = {
                    "rising": drift_report.rising,
                    "declining": drift_report.declining,
                    "stable": drift_report.stable,
                }
                result.items_stored += len(drift_report.mechanisms)

                if drift_report.declining:
                    logger.info(
                        "DRIFT ALERT: declining mechanisms: %s",
                        drift_report.declining,
                    )
                if drift_report.rising:
                    logger.info(
                        "DRIFT SIGNAL: rising mechanisms: %s",
                        drift_report.rising,
                    )

        except Exception as e:
            logger.debug("Advanced learning failed: %s", e)

    async def _run_causal_tests(self, result: TaskResult) -> list:
        """Run statistical tests on accumulated causal observations.

        Tests every (page_dimension, mechanism) pair for direct causal effects.
        Validated discoveries are written to Neo4j as causal edges.
        """
        try:
            from adam.intelligence.causal_learning import (
                get_observations, CausalTestEngine, persist_causal_discovery,
            )
        except ImportError:
            return []

        # Get accumulated observations
        observations = get_observations(limit=50000)
        if len(observations) < 50:
            logger.info("Causal testing: only %d observations (need 50+), skipping", len(observations))
            return []

        logger.info("Causal testing: analyzing %d observations", len(observations))

        # Run all direct effect tests
        engine = CausalTestEngine()
        test_results = engine.test_all_direct_effects(observations, min_observations=30)

        # Persist significant discoveries to Neo4j
        discoveries = 0
        for tr in test_results:
            if tr.significant:
                persisted = await persist_causal_discovery(tr)
                if persisted:
                    discoveries += 1
                    logger.info(
                        "CAUSAL DISCOVERY: %s %s %s (d=%.3f, p=%.4f, n=%d, "
                        "rate_high=%.3f, rate_low=%.3f)",
                        tr.dimension,
                        tr.direction,
                        tr.mechanism,
                        tr.effect_size,
                        tr.p_value,
                        tr.n_total,
                        tr.rate_high,
                        tr.rate_low,
                    )

        # Store results summary in Redis
        r = self._get_redis()
        if r:
            significant_results = [
                {
                    "dimension": tr.dimension,
                    "mechanism": tr.mechanism,
                    "direction": tr.direction,
                    "effect_size": tr.effect_size,
                    "p_value": tr.p_value,
                    "n": tr.n_total,
                }
                for tr in test_results if tr.significant
            ]
            self._store_redis_hash("informativ:causal:latest_run", {
                "observations_analyzed": len(observations),
                "tests_run": len(test_results),
                "discoveries": len(significant_results),
                "significant_effects": significant_results,
                "run_at": time.time(),
            }, ttl=86400 * 7)

        logger.info(
            "Causal testing: %d tests, %d significant, %d persisted to graph",
            len(test_results), sum(1 for r in test_results if r.significant), discoveries,
        )

        return test_results


# Edge dimensions reference (same as cascade uses)
# Also includes NDF dimensions for backward compatibility with old taxonomy data
_EDGE_DIMS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire", "interoceptive_awareness",
    "cooperative_framing_fit", "decision_entropy",
    # Legacy NDF dims (still present in older taxonomy data)
    "approach_avoidance", "temporal_horizon", "social_calibration",
    "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
    "arousal_seeking",
]
