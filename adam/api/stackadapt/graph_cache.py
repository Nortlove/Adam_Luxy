"""
StackAdapt Graph Intelligence Cache (Tier 1)
==============================================

Pre-loads Neo4j graph intelligence into memory at startup and refreshes
periodically so the Creative Intelligence API can serve graph-deep
responses in <2ms (cache hit) without any Neo4j latency at request time.

Cached data:
    1. Mechanism synergy/antagonism graph — which mechanisms amplify or cancel
    2. BayesianPrior nodes — category x personality x outcome priors with
       observed dimension averages (468 nodes)
    3. Category construct profiles — mechanism effectiveness per category
       including moderation deltas
    4. Product ad profiles — per-ASIN framing, brand personality, persuasion
       technique strengths (loaded on demand, then cached)

Refresh: every 15 minutes for BayesianPriors and category data.
         Mechanism graph is static — loaded once.
         Product profiles cached for 1 hour per ASIN.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")))
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", os.getenv("NEO4J_PASSWORD", os.getenv("NEO4J_PASS", "atomofthought")))

from adam.config.settings import get_settings

def _category_cache_ttl():
    return get_settings().cascade.category_cache_ttl

def _product_cache_ttl():
    return get_settings().cascade.product_cache_ttl


class GraphIntelligenceCache:
    """
    In-memory cache of graph intelligence for <2ms lookups.
    Thread-safe. Lazy-connects to Neo4j.
    """

    # Minimum seconds between Neo4j reconnection attempts
    _NEO4J_RETRY_INTERVAL = 30.0

    def __init__(self):
        self._driver = None
        self._neo4j_available: Optional[bool] = None
        self._last_neo4j_attempt: float = 0.0
        self._lock = threading.Lock()

        # Mechanism knowledge graph (static after load)
        self._mechanism_synergies: List[Tuple[str, str]] = []
        self._mechanism_antagonisms: List[Tuple[str, str]] = []
        self._mechanism_names: List[str] = []
        self._synergy_set: Set[Tuple[str, str]] = set()
        self._antagonism_set: Set[Tuple[str, str]] = set()

        # BayesianPrior nodes keyed by (category, prior_type)
        self._bayesian_priors: Dict[str, Dict[str, Any]] = {}

        # Category mechanism effectiveness from graph
        # {category: {archetype: {mechanism: {rate, confidence, n_obs, avg_dims}}}}
        self._category_graph_intel: Dict[str, Dict[str, Any]] = {}
        self._category_cache_ts: float = 0.0

        # Product ad profiles keyed by ASIN
        self._product_profiles: Dict[str, Dict[str, Any]] = {}
        self._product_cache_ts: Dict[str, float] = {}

        # BRAND_CONVERTED edge aggregates keyed by "asin:archetype"
        self._edge_aggregates: Dict[str, Dict[str, Any]] = {}
        self._edge_cache_ts: Dict[str, float] = {}

        # Gradient fields keyed by "archetype:category"
        self._gradient_fields: Dict[str, Any] = {}

        # Buyer uncertainty profiles keyed by buyer_id
        self._buyer_profiles: Dict[str, Any] = {}

        self._initialized = False

    # ── Connection ──────────────────────────────────────────────────────

    def _get_driver(self):
        if self._driver is not None:
            return self._driver

        # Respect retry interval — don't spam reconnection attempts
        now = time.time()
        if (
            self._neo4j_available is False
            and (now - self._last_neo4j_attempt) < self._NEO4J_RETRY_INTERVAL
        ):
            return None

        self._last_neo4j_attempt = now
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS),
            )
            self._driver.verify_connectivity()
            self._neo4j_available = True
            logger.info("GraphIntelligenceCache connected to Neo4j at %s", NEO4J_URI)
            return self._driver
        except Exception as e:
            logger.warning("Neo4j not available for graph cache: %s", e)
            self._neo4j_available = False
            self._driver = None
            return None

    @property
    def neo4j_available(self) -> bool:
        if self._neo4j_available is None:
            self._get_driver()
        elif self._neo4j_available is False:
            # Retry after interval — don't stay permanently unavailable
            if (time.time() - self._last_neo4j_attempt) >= self._NEO4J_RETRY_INTERVAL:
                self._get_driver()
        return bool(self._neo4j_available)

    # ── Initialization ──────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load all cacheable graph intelligence. Call once at startup."""
        start = time.time()

        self._load_mechanism_graph()
        self._load_bayesian_priors()
        self._load_gradient_fields()

        self._initialized = True
        elapsed = (time.time() - start) * 1000
        logger.info(
            "GraphIntelligenceCache initialized in %.0fms "
            "(mechanisms=%d, synergies=%d, antagonisms=%d, bayesian_priors=%d)",
            elapsed,
            len(self._mechanism_names),
            len(self._mechanism_synergies),
            len(self._mechanism_antagonisms),
            len(self._bayesian_priors),
        )

    # ── Cache Invalidation ───────────────────────────────────────────────

    def invalidate(
        self, archetype: str = "", category: str = "",
    ) -> int:
        """Invalidate cached entries for a specific (archetype, category) cell.

        Called after outcome processing updates BayesianPrior nodes in Neo4j,
        ensuring subsequent requests see fresh posterior data without waiting
        for the 15-minute periodic refresh.

        Returns the number of entries invalidated.
        """
        invalidated = 0
        with self._lock:
            # Invalidate BayesianPrior entries matching this cell
            keys_to_remove = []
            for key in self._bayesian_priors:
                parts = key.split(":")
                cat_match = not category or (parts[0] if parts else "") == category
                arch_match = not archetype or (parts[1] if len(parts) > 1 else "") == archetype
                if cat_match and arch_match:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._bayesian_priors[key]
                invalidated += 1

            # Invalidate category graph intel
            if category and category in self._category_graph_intel:
                del self._category_graph_intel[category]
                invalidated += 1

            # Invalidate gradient field for this cell
            if archetype and category:
                grad_key = f"{archetype}:{category}"
                if grad_key in self._gradient_fields:
                    del self._gradient_fields[grad_key]
                    invalidated += 1

            # Reset category cache timestamp to force reload on next access
            if invalidated > 0:
                self._category_cache_ts = 0.0

        if invalidated > 0:
            logger.debug(
                "GraphIntelligenceCache invalidated %d entries for %s/%s",
                invalidated, archetype or "*", category or "*",
            )
        return invalidated

    # ── Mechanism Synergy Graph ─────────────────────────────────────────

    def _load_mechanism_graph(self) -> None:
        """Load mechanism synergies and antagonisms from Neo4j or fallback."""
        driver = self._get_driver()
        if driver:
            try:
                with driver.session() as session:
                    mechs = session.run(
                        "MATCH (m:CognitiveMechanism) RETURN m.name AS name"
                    ).data()
                    if mechs:
                        syns = session.run(
                            "MATCH (a:CognitiveMechanism)-[:SYNERGIZES_WITH]->"
                            "(b:CognitiveMechanism) "
                            "RETURN a.name AS src, b.name AS tgt"
                        ).data()
                        ants = session.run(
                            "MATCH (a:CognitiveMechanism)-[:ANTAGONIZES]->"
                            "(b:CognitiveMechanism) "
                            "RETURN a.name AS src, b.name AS tgt"
                        ).data()
                        self._mechanism_names = [m["name"] for m in mechs]
                        self._mechanism_synergies = [(s["src"], s["tgt"]) for s in syns]
                        self._mechanism_antagonisms = [(a["src"], a["tgt"]) for a in ants]
                        self._synergy_set = set(self._mechanism_synergies)
                        self._antagonism_set = set(self._mechanism_antagonisms)
                        logger.info(
                            "Loaded mechanism graph from Neo4j: %d mechanisms, "
                            "%d synergies, %d antagonisms",
                            len(self._mechanism_names),
                            len(self._mechanism_synergies),
                            len(self._mechanism_antagonisms),
                        )
                        return
            except Exception as e:
                logger.warning("Failed to load mechanism graph from Neo4j: %s", e)

        # Research-grounded fallback (from unified_intelligence_service.py)
        self._mechanism_names = [
            "authority", "social_proof", "scarcity", "reciprocity",
            "commitment", "liking", "anchoring", "storytelling",
        ]
        self._mechanism_synergies = [
            ("authority", "social_proof"), ("social_proof", "liking"),
            ("commitment", "reciprocity"), ("scarcity", "anchoring"),
            ("storytelling", "liking"), ("storytelling", "social_proof"),
            ("authority", "commitment"), ("reciprocity", "liking"),
        ]
        self._mechanism_antagonisms = [
            ("scarcity", "reciprocity"), ("authority", "storytelling"),
            ("anchoring", "liking"),
        ]
        self._synergy_set = set(self._mechanism_synergies)
        self._antagonism_set = set(self._mechanism_antagonisms)
        logger.info("Using research-grounded mechanism graph fallback")

    def get_synergies_for(self, mechanism: str) -> List[str]:
        """Return mechanisms that synergize with the given one."""
        result = []
        for a, b in self._mechanism_synergies:
            if a == mechanism:
                result.append(b)
            elif b == mechanism:
                result.append(a)
        return result

    def get_antagonisms_for(self, mechanism: str) -> List[str]:
        """Return mechanisms that antagonize the given one."""
        result = []
        for a, b in self._mechanism_antagonisms:
            if a == mechanism:
                result.append(b)
            elif b == mechanism:
                result.append(a)
        return result

    def is_synergy(self, mech_a: str, mech_b: str) -> bool:
        return (mech_a, mech_b) in self._synergy_set or (mech_b, mech_a) in self._synergy_set

    def is_antagonism(self, mech_a: str, mech_b: str) -> bool:
        return (mech_a, mech_b) in self._antagonism_set or (mech_b, mech_a) in self._antagonism_set

    # ── BayesianPrior Nodes ─────────────────────────────────────────────

    def _load_bayesian_priors(self) -> None:
        """Load all 468 BayesianPrior nodes from Neo4j."""
        driver = self._get_driver()
        if not driver:
            return

        try:
            with driver.session() as session:
                results = session.run(
                    "MATCH (bp:BayesianPrior) RETURN properties(bp) AS props"
                ).data()

            for r in results:
                props = r["props"]
                cat = props.get("category", "all")
                prior_type = props.get("prior_type", "")
                key = f"{cat}:{prior_type}"
                self._bayesian_priors[key] = props

            logger.info("Loaded %d BayesianPrior nodes", len(self._bayesian_priors))
        except Exception as e:
            logger.warning("Failed to load BayesianPriors: %s", e)

    def get_bayesian_prior(self, category: str, prior_type: str = "") -> Optional[Dict[str, Any]]:
        """Get a specific BayesianPrior node."""
        key = f"{category}:{prior_type}"
        return self._bayesian_priors.get(key)

    def get_category_bayesian_priors(self, category: str) -> List[Dict[str, Any]]:
        """Get all BayesianPrior nodes for a category."""
        prefix = f"{category}:"
        return [v for k, v in self._bayesian_priors.items() if k.startswith(prefix)]

    def get_bayesian_mechanism_confidence(
        self, category: str, mechanism: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract mechanism-specific confidence from BayesianPrior nodes.
        Returns avg dimension scores and observation count.
        """
        priors = self.get_category_bayesian_priors(category)
        if not priors:
            return None

        mech_key = f"avg_{mechanism}"
        total_obs = 0
        total_score = 0.0
        count = 0
        avg_reg_fit = 0.0
        avg_construal = 0.0

        for bp in priors:
            score = bp.get(mech_key)
            n = bp.get("n_observations", 0)
            if score is not None and n > 0:
                total_score += float(score) * n
                total_obs += n
                count += 1
                if bp.get("avg_regulatory_fit"):
                    avg_reg_fit += float(bp["avg_regulatory_fit"]) * n
                if bp.get("avg_construal_fit"):
                    avg_construal += float(bp["avg_construal_fit"]) * n

        if total_obs == 0:
            return None

        return {
            "mechanism": mechanism,
            "category": category,
            "weighted_score": round(total_score / total_obs, 4),
            "n_observations": total_obs,
            "prior_count": count,
            "avg_regulatory_fit": round(avg_reg_fit / total_obs, 4) if avg_reg_fit else None,
            "avg_construal_fit": round(avg_construal / total_obs, 4) if avg_construal else None,
        }

    def get_all_mechanism_confidences(
        self, category: str, archetype: str = "",
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Get confidence data for ALL mechanisms in a category, optionally
        filtered by archetype. Used by bilateral cascade Level 2.

        Returns: {mechanism_name: {rate, n_obs, posterior_mean, ...}, ...}
        """
        priors = self.get_category_bayesian_priors(category)
        if not priors:
            return None

        # If archetype specified, prefer archetype-specific priors
        if archetype:
            archetype_priors = [
                bp for bp in priors
                if bp.get("archetype") == archetype
                or bp.get("personality_type") == archetype
            ]
            if archetype_priors:
                priors = archetype_priors

        from adam.constants import MECHANISMS

        result: Dict[str, Dict[str, Any]] = {}
        for mech in MECHANISMS:
            mech_key = f"avg_{mech}"
            total_score = 0.0
            total_obs = 0

            for bp in priors:
                score = bp.get(mech_key)
                n = bp.get("n_observations", 0)
                if score is not None and n > 0:
                    total_score += float(score) * n
                    total_obs += n

            if total_obs > 0:
                result[mech] = {
                    "rate": round(total_score / total_obs, 4),
                    "posterior_mean": round(total_score / total_obs, 4),
                    "n_obs": total_obs,
                    "observation_count": total_obs,
                }

        return result if result else None

    # ── Cross-Category Transfer Intelligence ─────────────────────────

    def get_universal_mechanism_priors(
        self, archetype: str = "",
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """Aggregate mechanism effectiveness across ALL categories.

        Returns the "universal prior" — what works across all categories
        regardless of product type. This captures psychological invariants:
        authority works well for achievers EVERYWHERE, not just in Electronics.

        When a new category has no BayesianPrior nodes, the cascade falls
        back to this universal prior instead of dropping to Level 1
        (hardcoded archetype prior with no empirical signal).
        """
        from adam.constants import MECHANISMS

        result: Dict[str, Dict[str, Any]] = {}
        for mech in MECHANISMS:
            mech_key = f"avg_{mech}"
            total_score = 0.0
            total_obs = 0
            category_count = 0
            categories_seen: set = set()

            for cache_key, bp in self._bayesian_priors.items():
                # Optionally filter by archetype
                if archetype:
                    bp_arch = bp.get("archetype") or bp.get("personality_type", "")
                    if bp_arch and bp_arch != archetype:
                        continue

                score = bp.get(mech_key)
                n = bp.get("n_observations", 0)
                cat = bp.get("category", "unknown")

                if score is not None and n > 0:
                    total_score += float(score) * n
                    total_obs += n
                    if cat not in categories_seen:
                        categories_seen.add(cat)
                        category_count += 1

            if total_obs > 0:
                result[mech] = {
                    "rate": round(total_score / total_obs, 4),
                    "posterior_mean": round(total_score / total_obs, 4),
                    "n_obs": total_obs,
                    "observation_count": total_obs,
                    "categories_pooled": category_count,
                    "source": "universal_cross_category",
                }

        return result if result else None

    def get_category_deviation(
        self, category: str, archetype: str = "",
    ) -> Optional[Dict[str, float]]:
        """Compute how a category deviates from the universal prior.

        Returns: {mechanism: delta} where delta = category_mean - universal_mean.
        Positive delta means this mechanism is MORE effective in this category
        than across all categories. Negative means LESS effective.

        This is the interesting signal: the deviation IS the category-specific
        knowledge. Universal patterns transfer freely; deviations must be learned.
        """
        universal = self.get_universal_mechanism_priors(archetype=archetype)
        category_specific = self.get_all_mechanism_confidences(
            category=category, archetype=archetype,
        )

        if not universal or not category_specific:
            return None

        deviations: Dict[str, float] = {}
        for mech, u_info in universal.items():
            c_info = category_specific.get(mech)
            if c_info:
                delta = c_info["rate"] - u_info["rate"]
                deviations[mech] = round(delta, 4)

        return deviations if deviations else None

    def get_similar_categories(
        self, category: str, archetype: str = "", top_n: int = 3,
    ) -> List[str]:
        """Find categories with similar mechanism effectiveness profiles.

        Uses cosine-like similarity between mechanism score vectors.
        When a new category has sparse data, the cascade can borrow
        strength from similar categories.
        """
        target = self.get_all_mechanism_confidences(
            category=category, archetype=archetype,
        )
        if not target:
            return []

        # Build target vector
        target_vec = {m: info["rate"] for m, info in target.items()}

        # Compare against all other categories
        all_categories: set = set()
        for key in self._bayesian_priors:
            cat = key.split(":")[0]
            if cat != category and cat != "all":
                all_categories.add(cat)

        similarities: List[tuple] = []
        for other_cat in all_categories:
            other = self.get_all_mechanism_confidences(
                category=other_cat, archetype=archetype,
            )
            if not other:
                continue

            # Cosine-like similarity
            dot = 0.0
            mag_a = 0.0
            mag_b = 0.0
            for mech in target_vec:
                a = target_vec.get(mech, 0.0)
                b = other.get(mech, {}).get("rate", 0.0)
                dot += a * b
                mag_a += a * a
                mag_b += b * b

            if mag_a > 0 and mag_b > 0:
                sim = dot / ((mag_a ** 0.5) * (mag_b ** 0.5))
                similarities.append((other_cat, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in similarities[:top_n]]

    # ── Product Ad Profiles ─────────────────────────────────────────────

    def get_product_profile(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Get full ad-side construct profile for a product.
        Loads from Neo4j on first access, then caches for 1 hour.
        """
        now = time.time()
        cached_ts = self._product_cache_ts.get(asin, 0)
        if asin in self._product_profiles and (now - cached_ts) < _product_cache_ttl():
            return self._product_profiles[asin]

        driver = self._get_driver()
        if not driver:
            return None

        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (pd:ProductDescription {asin: $asin}) "
                    "RETURN properties(pd) AS props",
                    asin=asin,
                ).single()

            if not result:
                return None

            props = result["props"]
            profile = self._extract_ad_constructs(props)

            with self._lock:
                self._product_profiles[asin] = profile
                self._product_cache_ts[asin] = now

            return profile
        except Exception as e:
            logger.warning("Failed to load product profile for %s: %s", asin, e)
            return None

    def _extract_ad_constructs(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ad-side constructs from ProductDescription properties."""
        profile: Dict[str, Any] = {
            "asin": props.get("asin", ""),
            "category": props.get("main_category", ""),
        }

        framing = {}
        brand_personality = {}
        persuasion_techniques = {}
        other_ad = {}

        for key, val in props.items():
            if val is None:
                continue
            if key.startswith("ad_framing_"):
                framing[key.replace("ad_framing_", "")] = val
            elif key.startswith("ad_brand_personality_"):
                brand_personality[key.replace("ad_brand_personality_", "")] = val
            elif key.startswith("ad_persuasion_techniques_"):
                persuasion_techniques[key.replace("ad_persuasion_techniques_", "")] = val
            elif key.startswith("ad_"):
                other_ad[key.replace("ad_", "")] = val

        profile["framing"] = framing
        profile["brand_personality"] = brand_personality
        profile["persuasion_techniques"] = persuasion_techniques
        profile["ad_constructs"] = other_ad
        return profile

    # ── BRAND_CONVERTED Edge Aggregates (Tier 2) ──────────────────────

    def get_edge_aggregates(
        self, asin: str, archetype: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated BRAND_CONVERTED edge statistics for a product,
        optionally filtered by buyer archetype.

        This is the Tier 2 live query — 10-30ms on cache miss.
        Results cached for 1 hour.
        """
        cache_key = f"{asin}:{archetype}"
        now = time.time()
        cached_ts = self._edge_cache_ts.get(cache_key, 0)
        if cache_key in self._edge_aggregates and (now - cached_ts) < _product_cache_ttl():
            return self._edge_aggregates[cache_key]

        driver = self._get_driver()
        if not driver:
            return None

        try:
            archetype_filter = ""
            params = {"asin": asin}
            if archetype:
                archetype_filter = "WHERE ar.user_archetype = $archetype "
                params["archetype"] = archetype

            # Aggregate ALL psychologically-meaningful edge dimensions.
            # The 7 core dims were always queried; the 8 extended construct
            # dims below were present on the graph but never aggregated —
            # causing level3_bilateral_edges to default them to 0.5 neutral,
            # hiding real signal (Audit #3, 2026-04-15). Mapping from edge
            # property names to cascade dimension names:
            #
            # Edge property                → Cascade name              Theory
            # reactance_fit               → autonomy_reactance        Brehm reactance
            # spending_pain_match         → loss_aversion_intensity   Prelec pain-of-paying
            # mental_simulation_resonance → narrative_transport       Green-Brock transportation
            # processing_route_match      → cognitive_load_tolerance  Petty-Cacioppo ELM
            # identity_signaling_match    → mimetic_desire            Girard mimesis via signaling
            # self_monitoring_fit         → social_proof_sensitivity  Snyder self-monitoring
            # anchor_susceptibility_match → persuasion_susceptibility Tversky-Kahneman anchoring
            # brand_trust_fit             → brand_relationship_depth  Fournier brand relationships
            query = (
                "MATCH (pd:ProductDescription {asin: $asin})"
                "-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview) "
                + archetype_filter +
                "RETURN count(bc) AS edge_count, "
                # 7 core alignment dimensions
                "avg(bc.regulatory_fit_score) AS avg_reg_fit, "
                "avg(bc.construal_fit_score) AS avg_construal_fit, "
                "avg(bc.personality_brand_alignment) AS avg_personality_align, "
                "avg(bc.emotional_resonance) AS avg_emotional, "
                "avg(bc.value_alignment) AS avg_value, "
                "avg(bc.evolutionary_motive_match) AS avg_evo, "
                "avg(bc.composite_alignment) AS avg_composite, "
                "stDev(bc.composite_alignment) AS std_composite, "
                "avg(bc.linguistic_style_matching) AS avg_linguistic, "
                "avg(bc.persuasion_confidence_multiplier) AS avg_confidence, "
                # 8 extended construct dimensions (Audit #3 fix)
                "avg(bc.reactance_fit) AS avg_autonomy_reactance, "
                "avg(bc.spending_pain_match) AS avg_loss_aversion_intensity, "
                "avg(bc.mental_simulation_resonance) AS avg_narrative_transport, "
                "avg(bc.processing_route_match) AS avg_cognitive_load_tolerance, "
                "avg(bc.identity_signaling_match) AS avg_mimetic_desire, "
                "avg(bc.self_monitoring_fit) AS avg_social_proof_sensitivity, "
                "avg(bc.anchor_susceptibility_match) AS avg_persuasion_susceptibility, "
                "avg(bc.brand_trust_fit) AS avg_brand_relationship_depth, "
                # 5 additional extended dims completing the full 20-dim coverage
                # appeal_resonance → interoceptive_awareness: Damasio somatic
                #   marker — affective appeal activates body-level resonance
                # lay_theory_alignment → information_seeking: Furnham naive
                #   psychology — when lay causal model aligns, buyer seeks
                #   less corrective information
                # optimal_distinctiveness_fit → cooperative_framing_fit:
                #   Brewer ODT — group identification sweet spot → receptive
                #   to cooperative/fair exchange framing
                # negativity_bias_match → temporal_discounting: Baumeister
                #   "bad is stronger than good" — negativity bias amplifies
                #   present-moment reactions → present-focus → higher
                #   temporal discounting
                # disgust_contamination_fit → decision_entropy: Rozin
                #   contamination sensitivity adds decision criteria beyond
                #   utility (purity, provenance, moral acceptability) →
                #   more dimensions to evaluate → higher decision entropy
                "avg(bc.appeal_resonance) AS avg_interoceptive_awareness, "
                "avg(bc.lay_theory_alignment) AS avg_information_seeking, "
                "avg(bc.optimal_distinctiveness_fit) AS avg_cooperative_framing_fit, "
                "avg(bc.negativity_bias_match) AS avg_temporal_discounting, "
                "avg(bc.disgust_contamination_fit) AS avg_decision_entropy"
            )

            with driver.session() as session:
                result = session.run(query, **params).single()

            # If archetype-filtered query returns 0, retry without filter.
            # Seed data and some edge sets don't have user_archetype on
            # AnnotatedReview nodes. The unfiltered query still returns
            # valid bilateral evidence — just not archetype-stratified.
            if (not result or result["edge_count"] == 0) and archetype_filter:
                logger.debug(
                    "Edge query with archetype=%s returned 0; retrying unfiltered",
                    archetype,
                )
                unfiltered_query = query.replace(archetype_filter, "")
                unfiltered_params = {"asin": asin}
                with driver.session() as session:
                    result = session.run(unfiltered_query, **unfiltered_params).single()

            if not result or result["edge_count"] == 0:
                return None

            aggregates = {
                k: round(float(v), 4) if isinstance(v, (int, float)) and v is not None else v
                for k, v in dict(result).items()
                if v is not None
            }
            aggregates["asin"] = asin
            aggregates["archetype_filter"] = archetype or "all"

            with self._lock:
                self._edge_aggregates[cache_key] = aggregates
                self._edge_cache_ts[cache_key] = now

            return aggregates
        except Exception as e:
            logger.warning("Edge aggregate query failed for %s: %s", asin, e)
            return None

    # ── Gradient Fields ─────────────────────────────────────────────────

    def _load_gradient_fields(self) -> None:
        """Load pre-computed gradient fields from BayesianPrior nodes."""
        try:
            from adam.intelligence.gradient_fields import gradient_from_neo4j_properties
        except ImportError:
            logger.info("gradient_fields module not available, skipping")
            return

        # Reconstruct gradients from BayesianPrior nodes that have gradient_ properties
        for key, props in self._bayesian_priors.items():
            if props.get("gradient_n_edges", 0) > 0:
                parts = key.split(":", 1)
                category = parts[0] if parts else ""
                archetype = props.get("archetype", props.get("personality_type", ""))
                if archetype:
                    gv = gradient_from_neo4j_properties(props, archetype, category)
                    cache_key = f"{archetype}:{category}"
                    self._gradient_fields[cache_key] = gv

        if self._gradient_fields:
            logger.info("Loaded %d pre-computed gradient fields", len(self._gradient_fields))

    def get_gradient_field(self, archetype: str, category: str) -> Optional[Any]:
        """Get pre-computed gradient field for an (archetype, category) cell.

        Three-tier fallback:
        1. Exact (archetype, category) match
        2. Archetype-global gradient (archetype, "")
        3. Cross-category pooling: average gradients from similar categories
           for this archetype. This ensures new/sparse categories still get
           gradient intelligence from related categories.
        """
        # Tier 1: exact match
        cache_key = f"{archetype}:{category}"
        gf = self._gradient_fields.get(cache_key)
        if gf and getattr(gf, "is_valid", False):
            return gf

        # Tier 2: archetype-global
        global_key = f"{archetype}:"
        gf = self._gradient_fields.get(global_key)
        if gf and getattr(gf, "is_valid", False):
            return gf

        # Tier 3: pool from all categories for this archetype
        # Average the gradient vectors across all categories where this
        # archetype has valid gradients. This captures the "universal
        # optimization direction" for this psychological profile.
        archetype_gradients = []
        for k, v in self._gradient_fields.items():
            if k.startswith(f"{archetype}:") and getattr(v, "is_valid", False):
                archetype_gradients.append(v)

        if len(archetype_gradients) >= 2:
            try:
                from adam.intelligence.gradient_fields import GradientVector
                # Average the gradient coefficients across categories
                pooled_gradients: Dict[str, float] = {}
                pooled_means: Dict[str, float] = {}
                pooled_optima: Dict[str, float] = {}
                total_edges = 0

                for gv in archetype_gradients:
                    total_edges += gv.n_edges
                    for dim, grad in gv.gradients.items():
                        pooled_gradients[dim] = pooled_gradients.get(dim, 0) + grad
                        pooled_means[dim] = pooled_means.get(dim, 0) + gv.means.get(dim, 0)
                        pooled_optima[dim] = pooled_optima.get(dim, 0) + gv.optima.get(dim, 0)

                n = len(archetype_gradients)
                pooled = GradientVector(
                    gradients={d: v / n for d, v in pooled_gradients.items()},
                    means={d: v / n for d, v in pooled_means.items()},
                    optima={d: v / n for d, v in pooled_optima.items()},
                    archetype=archetype,
                    category=f"pooled_{n}_categories",
                    n_edges=total_edges,
                    r_squared=0.1,  # Synthetic, mark as lower confidence
                )
                # Cache for reuse
                with self._lock:
                    self._gradient_fields[cache_key] = pooled
                logger.debug(
                    "Pooled gradient field for %s×%s from %d categories (%d total edges)",
                    archetype, category, n, total_edges,
                )
                return pooled
            except Exception as e:
                logger.debug("Cross-category gradient pooling failed: %s", e)

        return None

    def compute_and_cache_gradient(self, archetype: str, category: str) -> Optional[Any]:
        """Compute gradient field on demand and cache it.

        This is for cases where no pre-computed gradient exists but we have
        Neo4j access. Takes 100-500ms (batch operation, not real-time).
        """
        driver = self._get_driver()
        if not driver:
            return None

        try:
            from adam.intelligence.gradient_fields import compute_gradient_from_neo4j
            gv = compute_gradient_from_neo4j(driver, archetype, category)
            if gv.is_valid:
                cache_key = f"{archetype}:{category}"
                with self._lock:
                    self._gradient_fields[cache_key] = gv
                logger.info(
                    "Computed gradient field: %s × %s (n=%d, R²=%.3f)",
                    archetype, category, gv.n_edges, gv.r_squared,
                )
                return gv
        except Exception as e:
            logger.warning("Failed to compute gradient for %s × %s: %s", archetype, category, e)

        return None

    # ── Redis for buyer profiles ─────────────────────────────────────────

    _BUYER_PROFILE_PREFIX = "informativ:buyer:"
    _BUYER_PROFILE_TTL = 60 * 60 * 24 * 90  # 90 days

    def _get_redis(self):
        """Get Redis connection (lazy init, tolerant of failure)."""
        if not hasattr(self, "_redis"):
            self._redis = None
            try:
                import redis
                from adam.config.settings import get_settings
                rs = get_settings().redis
                self._redis = redis.Redis(
                    host=rs.host, port=rs.port, password=rs.password,
                    db=rs.db, ssl=rs.ssl,
                    socket_timeout=rs.socket_timeout,
                    socket_connect_timeout=rs.socket_connect_timeout,
                    decode_responses=True,
                )
                self._redis.ping()
                logger.info("Buyer profile Redis connected")
            except Exception as e:
                logger.debug("Redis not available for buyer profiles: %s", e)
                self._redis = None
        return self._redis

    def _load_buyer_profile_from_redis(self, buyer_id: str):
        """Try to load a buyer profile from Redis."""
        r = self._get_redis()
        if not r:
            return None
        try:
            import json
            data = r.get(f"{self._BUYER_PROFILE_PREFIX}{buyer_id}")
            if data:
                from adam.intelligence.information_value import BuyerUncertaintyProfile
                return BuyerUncertaintyProfile.from_dict(json.loads(data))
        except Exception as e:
            logger.debug("Failed to load buyer profile from Redis: %s", e)
        return None

    def _save_buyer_profile_to_redis(self, buyer_id: str, profile):
        """Persist a buyer profile to Redis (fire-and-forget)."""
        r = self._get_redis()
        if not r:
            return
        try:
            import json
            r.setex(
                f"{self._BUYER_PROFILE_PREFIX}{buyer_id}",
                self._BUYER_PROFILE_TTL,
                json.dumps(profile.to_dict()),
            )
        except Exception as e:
            logger.debug("Failed to save buyer profile to Redis: %s", e)

    # ── Buyer Uncertainty Profiles ──────────────────────────────────────

    def get_buyer_profile(self, buyer_id: str) -> Optional[Any]:
        """Get or create a BuyerUncertaintyProfile for information value bidding.

        Profiles are stored in-memory with Redis read-through/write-through.
        New buyers get default Beta(2,2) priors — high uncertainty, high info value.
        """
        if buyer_id in self._buyer_profiles:
            return self._buyer_profiles[buyer_id]

        # Try Redis before creating a new profile
        profile = self._load_buyer_profile_from_redis(buyer_id)
        if profile:
            with self._lock:
                self._buyer_profiles[buyer_id] = profile
            return profile

        # Create new profile with default priors
        try:
            from adam.intelligence.information_value import BuyerUncertaintyProfile
            profile = BuyerUncertaintyProfile(buyer_id=buyer_id)
            with self._lock:
                self._buyer_profiles[buyer_id] = profile
            return profile
        except ImportError:
            return None

    def update_buyer_profile(
        self,
        buyer_id: str,
        edge_dimensions: Dict[str, float],
        signal_type: str = "conversion",
        processing_depth_weight: float = 1.0,
    ) -> Optional[Dict[str, float]]:
        """Update a buyer's uncertainty profile with a new observation.

        Called from the webhook when a conversion/click/bounce event arrives.
        Returns the variance reduction per dimension (how much we learned).
        Write-through: persists to Redis after updating in-memory.

        Enhancement #34: processing_depth_weight scales the signal weight
        so unprocessed impressions produce minimal BONG posterior shift.
        """
        profile = self.get_buyer_profile(buyer_id)
        if not profile:
            return None

        import time as _time
        variance_deltas = profile.update_from_edge(
            edge_dimensions, signal_type,
            processing_depth_weight=processing_depth_weight,
        )
        profile.last_updated_ts = _time.time()

        # Write-through to Redis
        self._save_buyer_profile_to_redis(buyer_id, profile)

        return variance_deltas

    # ── Public API ──────────────────────────────────────────────────────

    def get_health(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "neo4j_available": self.neo4j_available,
            "mechanism_count": len(self._mechanism_names),
            "synergy_count": len(self._mechanism_synergies),
            "antagonism_count": len(self._mechanism_antagonisms),
            "bayesian_prior_count": len(self._bayesian_priors),
            "gradient_field_count": len(self._gradient_fields),
            "cached_products": len(self._product_profiles),
            "cached_edge_aggregates": len(self._edge_aggregates),
            "buyer_profiles": len(self._buyer_profiles),
        }

    def refresh(self) -> None:
        """Refresh time-sensitive caches (BayesianPriors, category data)."""
        self._load_bayesian_priors()
        logger.info("Graph cache refreshed")


# ── Singleton ──────────────────────────────────────────────────────────────

_cache: Optional[GraphIntelligenceCache] = None


def get_graph_cache() -> GraphIntelligenceCache:
    global _cache
    if _cache is None:
        _cache = GraphIntelligenceCache()
        _cache.initialize()
    return _cache
