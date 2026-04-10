"""
Graph Intelligence Service
============================

Unified high-level service that wraps GraphPatternPersistence with:
- Caching (TTL-based, so repeated queries within a session are fast)
- Sync wrappers (for engines that aren't async)
- Composite queries (combine multiple low-level calls into engine-ready data)

This is the single dependency all engines use for graph data instead of
importing GraphPatternPersistence directly.

Every method has a graph-backed primary path and returns an empty/default
result if Neo4j is unavailable (engines handle the fallback themselves).
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# TTL CACHE
# =============================================================================

@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class _TTLCache:
    """Simple TTL-based in-memory cache."""

    def __init__(self, default_ttl: float = 300.0):
        self._store: Dict[str, _CacheEntry] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.time() + (ttl or self._default_ttl),
        )

    def clear(self):
        self._store.clear()


# =============================================================================
# GRAPH INTELLIGENCE SERVICE
# =============================================================================

class GraphIntelligenceService:
    """
    High-level graph intelligence service for all engines.

    Wraps GraphPatternPersistence and combines queries into
    engine-ready data structures with caching.
    """

    def __init__(self):
        self._persistence = None
        self._cache = _TTLCache(default_ttl=300.0)  # 5 min cache
        self._neo4j_available: Optional[bool] = None

    def _get_persistence(self):
        """Lazy-load persistence to avoid circular imports."""
        if self._persistence is None:
            from adam.infrastructure.neo4j.pattern_persistence import get_pattern_persistence
            self._persistence = get_pattern_persistence()
        return self._persistence

    async def _check_neo4j(self) -> bool:
        """Check if Neo4j is reachable (cached for 60s)."""
        cached = self._cache.get("__neo4j_available__")
        if cached is not None:
            return cached
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if not client.is_connected:
                connected = await client.connect()
            else:
                connected = True
            self._cache.set("__neo4j_available__", connected, ttl=60.0)
            return connected
        except Exception as e:
            logger.debug(f"Neo4j not available: {e}")
            self._cache.set("__neo4j_available__", False, ttl=60.0)
            return False

    # =========================================================================
    # HIGH-LEVEL COMPOSITE QUERIES
    # =========================================================================

    async def get_category_constructs(
        self,
        category: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get constructs relevant to a product category.

        Queries CONTEXTUALLY_MODERATES edges outbound from category nodes,
        plus constructs in relevant domains.

        Returns: [{construct_id, name, domain, relevance}]
        """
        cache_key = f"cat_constructs:{category}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return []

        try:
            persistence = self._get_persistence()

            # Get category moderation data (which mechanisms are boosted for this category)
            moderation = await persistence.get_dsp_category_moderation(category, limit=limit)

            # Also get constructs by domains that match common category mappings
            domain_map = {
                "finance": "decision_making", "insurance": "decision_making",
                "health": "motivation", "wellness": "motivation",
                "fashion": "social_influence", "luxury": "social_influence",
                "technology": "cognition", "electronics": "cognition",
                "food": "motivation", "fitness": "motivation",
                "travel": "motivation", "education": "cognition",
                "baby": "decision_making", "automotive": "decision_making",
                "gaming": "cognition", "beauty": "social_influence",
                "mattress": "motivation", "sleep": "motivation",
                "software": "cognition", "saas": "cognition",
            }

            cat_lower = category.lower().replace("_", " ")
            domain = None
            for key, dom in domain_map.items():
                if key in cat_lower:
                    domain = dom
                    break

            constructs = []
            if domain:
                domain_constructs = await persistence.get_constructs_by_domain(domain, limit=limit)
                for dc in domain_constructs:
                    dc["relevance"] = 0.7  # domain-based relevance
                    constructs.append(dc)

            # Add mechanism-connected constructs from moderation edges
            for mech_id, delta in moderation.items():
                mech_constructs = await persistence.get_constructs_for_mechanism(mech_id, limit=5)
                for mc in mech_constructs:
                    mc["relevance"] = min(1.0, abs(delta) + 0.3)
                    if mc["construct_id"] not in {c["construct_id"] for c in constructs}:
                        constructs.append(mc)

            # Sort by relevance
            constructs.sort(key=lambda x: x.get("relevance", 0), reverse=True)
            result = constructs[:limit]
            self._cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.debug(f"get_category_constructs failed: {e}")
            return []

    async def get_mechanism_effectiveness(
        self,
        category: str,
        constructs: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get mechanism effectiveness scores for a category + construct set.

        Combines:
        1. EMPIRICALLY_EFFECTIVE edges (from review corpus)
        2. CONTEXTUALLY_MODERATES deltas (category-specific boosts)
        3. construct → mechanism SUSCEPTIBLE_TO edges

        Returns: {mechanism_id: {score, sample_size, confidence, source}}
        """
        cache_key = f"mech_eff:{category}:{','.join(sorted(constructs or []))}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return {}

        try:
            persistence = self._get_persistence()
            combined: Dict[str, Dict[str, Any]] = {}

            # 1. Category moderation
            moderation = await persistence.get_dsp_category_moderation(category)
            for mech, delta in moderation.items():
                combined[mech] = {
                    "score": 0.5 + delta,  # baseline + delta
                    "sample_size": 0,
                    "confidence": 0.4,
                    "source": "category_moderation",
                }

            # 2. Construct susceptibility
            if constructs:
                for construct_id in constructs[:10]:
                    suscept = await persistence.get_dsp_mechanism_susceptibility(construct_id)
                    for mech, strength in suscept.items():
                        if mech in combined:
                            # Weighted merge
                            old = combined[mech]["score"]
                            combined[mech]["score"] = (old + strength) / 2.0
                            combined[mech]["confidence"] = min(0.8, combined[mech]["confidence"] + 0.1)
                        else:
                            combined[mech] = {
                                "score": strength,
                                "sample_size": 0,
                                "confidence": 0.5,
                                "source": "construct_susceptibility",
                            }

            # 3. Empirical effectiveness (highest quality signal)
            # Query for common archetypes that map to this category
            archetype_map = {
                "finance": "analyst", "insurance": "guardian",
                "health": "guardian", "technology": "explorer",
                "fashion": "connector", "luxury": "achiever",
                "food": "connector", "fitness": "achiever",
                "electronics": "analyst", "education": "explorer",
            }
            cat_lower = category.lower().replace("_", " ")
            archetype = None
            for key, arch in archetype_map.items():
                if key in cat_lower:
                    archetype = arch
                    break

            if archetype:
                empirical = await persistence.get_dsp_empirical_effectiveness(archetype)
                for mech, data in empirical.items():
                    sr = data.get("success_rate", 0)
                    ss = data.get("sample_size", 0)
                    if mech in combined:
                        # Empirical data is highest quality -- weight it heavily
                        old_score = combined[mech]["score"]
                        combined[mech]["score"] = 0.3 * old_score + 0.7 * sr
                        combined[mech]["sample_size"] = ss
                        combined[mech]["confidence"] = min(0.95, 0.5 + min(ss / 10000, 0.45))
                        combined[mech]["source"] = "empirical+moderation"
                    else:
                        combined[mech] = {
                            "score": sr,
                            "sample_size": ss,
                            "confidence": min(0.95, 0.5 + min(ss / 10000, 0.45)),
                            "source": "empirical",
                        }

            self._cache.set(cache_key, combined)
            return combined

        except Exception as e:
            logger.debug(f"get_mechanism_effectiveness failed: {e}")
            return {}

    async def get_creative_implications(
        self,
        construct_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Get combined creative implications from multiple constructs.

        Returns: {construct_id: {construct: {...}, edges: [...]}}
        """
        if not construct_ids:
            return {}

        cache_key = f"creative_impl:{','.join(sorted(construct_ids[:10]))}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return {}

        try:
            persistence = self._get_persistence()
            result = {}
            for cid in construct_ids[:10]:
                impl = await persistence.get_construct_creative_implications(cid)
                if impl:
                    result[cid] = impl
            self._cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.debug(f"get_creative_implications failed: {e}")
            return {}

    async def get_construct_neighborhood(
        self,
        construct_id: str,
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """Get constructs within N hops of the given construct."""
        cache_key = f"neighborhood:{construct_id}:{max_hops}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return []

        try:
            persistence = self._get_persistence()
            result = await persistence.get_construct_neighborhood(construct_id, max_hops)
            self._cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.debug(f"get_construct_neighborhood failed: {e}")
            return []

    async def get_inferential_chains(
        self,
        source_id: str,
        target_mechanism: str,
    ) -> List[Dict[str, Any]]:
        """Get causal chain from a construct to a mechanism."""
        cache_key = f"inf_chain:{source_id}:{target_mechanism}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return []

        try:
            persistence = self._get_persistence()
            result = await persistence.get_inferential_chain(source_id, target_mechanism)
            self._cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.debug(f"get_inferential_chains failed: {e}")
            return []

    async def get_segments_for_category(
        self,
        category: str,
    ) -> List[Dict[str, Any]]:
        """
        Get dynamic segment definitions for a category.

        Builds segments by:
        1. Getting category-relevant constructs
        2. Clustering them by co-occurrence (neighborhood overlap)
        3. Computing mechanism effectiveness per cluster
        4. Generating creative guidance per cluster

        Returns: [{name, constructs, mechanisms, creative, prevalence}]
        """
        cache_key = f"segments:{category}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return []

        try:
            # Get relevant constructs
            constructs = await self.get_category_constructs(category)
            if not constructs:
                return []

            # Get mechanism effectiveness
            construct_ids = [c["construct_id"] for c in constructs]
            mech_eff = await self.get_mechanism_effectiveness(category, construct_ids)

            # Group constructs by domain for natural clustering
            domain_clusters: Dict[str, List[Dict]] = {}
            for c in constructs:
                domain = c.get("domain", "general")
                domain_clusters.setdefault(domain, []).append(c)

            segments = []
            for domain, cluster_constructs in domain_clusters.items():
                if len(cluster_constructs) < 2:
                    continue

                # Build segment from cluster
                construct_dict = {
                    c["construct_id"]: c.get("relevance", 0.5)
                    for c in cluster_constructs[:7]
                }

                # Get mechanism recommendations for this cluster
                cluster_mechs = []
                for mech_id, data in sorted(
                    mech_eff.items(), key=lambda x: x[1]["score"], reverse=True
                )[:5]:
                    cluster_mechs.append({
                        "mechanism": mech_id,
                        "score": data["score"],
                        "confidence": data["confidence"],
                        "sample_size": data.get("sample_size", 0),
                    })

                # Get creative implications
                creative_impl = await self.get_creative_implications(
                    [c["construct_id"] for c in cluster_constructs[:3]]
                )

                segments.append({
                    "name": f"{domain.replace('_', ' ').title()} Profile",
                    "domain": domain,
                    "constructs": construct_dict,
                    "mechanisms": cluster_mechs,
                    "creative": creative_impl,
                    "prevalence": min(0.25, len(cluster_constructs) / 20),
                })

            self._cache.set(cache_key, segments)
            return segments

        except Exception as e:
            logger.debug(f"get_segments_for_category failed: {e}")
            return []

    async def get_available_categories(self) -> List[str]:
        """
        Get available categories from graph CONTEXTUALLY_MODERATES edges.

        Returns distinct category construct IDs.
        """
        cache_key = "available_categories"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return []

        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            async with await client.session() as session:
                query = """
                MATCH (c:DSPConstruct)-[:CONTEXTUALLY_MODERATES]->()
                WHERE c.construct_id STARTS WITH 'cat_'
                RETURN DISTINCT c.construct_id AS cat_id, c.name AS name
                ORDER BY c.name
                """
                result = await session.run(query)
                records = await result.data()

                categories = []
                for r in records:
                    # Convert cat_id back to human form
                    cat_id = r["cat_id"]
                    # strip 'cat_' prefix and convert underscores to spaces
                    cat_name = cat_id.replace("cat_", "").replace("_", " ").title()
                    categories.append(cat_name)

                self._cache.set(cache_key, categories, ttl=600.0)
                return categories

        except Exception as e:
            logger.debug(f"get_available_categories failed: {e}")
            return []

    async def get_learned_priors(
        self,
        category: str,
    ) -> Dict[str, Any]:
        """
        Get learned priors from the ingestion data for a category.

        Returns: {archetype: {mechanism: {success_rate, sample_size}}}
        """
        cache_key = f"learned_priors:{category}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = None
        try:
            from adam.intelligence.unified_intelligence_service import get_unified_intelligence_service
            svc = get_unified_intelligence_service()
            raw = svc._load_layer1_priors()
            if raw:
                data = raw
        except Exception:
            pass

        if data is None:
            import os
            logger.warning("UnifiedIntelligenceService unavailable; loading priors from file")
            priors_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "learning", "ingestion_merged_priors.json",
            )
            if not os.path.exists(priors_path):
                return {}

            try:
                with open(priors_path) as f:
                    data = json.load(f)
            except Exception as e:
                logger.debug(f"get_learned_priors failed: {e}")
                return {}

        if data:
            # Try category-specific effectiveness first
            cat_matrices = data.get("category_effectiveness_matrices", {})

            # Normalize category name to match stored format
            cat_variants = [
                category,
                category.replace(" ", "_"),
                category.replace("_", " "),
                category.title().replace(" ", "_"),
            ]

            for variant in cat_variants:
                if variant in cat_matrices:
                    result = cat_matrices[variant]
                    self._cache.set(cache_key, result, ttl=600.0)
                    return result

            # Fallback to global effectiveness matrix
            global_matrix = data.get("global_effectiveness_matrix", {})
            if global_matrix:
                self._cache.set(cache_key, global_matrix, ttl=600.0)
                return global_matrix

            return {}

    async def get_construct_by_id(self, construct_id: str) -> Optional[Dict[str, Any]]:
        """Get a single construct by ID."""
        cache_key = f"construct:{construct_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return None

        try:
            persistence = self._get_persistence()
            result = await persistence.get_dsp_construct(construct_id)
            if result:
                self._cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.debug(f"get_construct_by_id failed: {e}")
            return None

    async def get_constructs_by_domain(self, domain: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get constructs by domain."""
        cache_key = f"domain_constructs:{domain}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not await self._check_neo4j():
            return []

        try:
            persistence = self._get_persistence()
            result = await persistence.get_constructs_by_domain(domain, limit)
            self._cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.debug(f"get_constructs_by_domain failed: {e}")
            return []

    def clear_cache(self):
        """Clear the entire cache."""
        self._cache.clear()

    # =========================================================================
    # SYNC WRAPPERS
    # =========================================================================

    def sync_get_category_constructs(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Sync wrapper for get_category_constructs."""
        return _run_async(self.get_category_constructs(category, limit))

    def sync_get_mechanism_effectiveness(
        self, category: str, constructs: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Sync wrapper for get_mechanism_effectiveness."""
        return _run_async(self.get_mechanism_effectiveness(category, constructs))

    def sync_get_creative_implications(self, construct_ids: List[str]) -> Dict[str, Any]:
        """Sync wrapper for get_creative_implications."""
        return _run_async(self.get_creative_implications(construct_ids))

    def sync_get_segments_for_category(self, category: str) -> List[Dict[str, Any]]:
        """Sync wrapper for get_segments_for_category."""
        return _run_async(self.get_segments_for_category(category))

    def sync_get_available_categories(self) -> List[str]:
        """Sync wrapper for get_available_categories."""
        return _run_async(self.get_available_categories())

    def sync_get_learned_priors(self, category: str) -> Dict[str, Any]:
        """Sync wrapper for get_learned_priors."""
        return _run_async(self.get_learned_priors(category))


# =============================================================================
# ASYNC HELPER — Persistent background event loop
# =============================================================================

import threading

_bg_loop: Optional[asyncio.AbstractEventLoop] = None
_bg_thread: Optional[threading.Thread] = None
_bg_lock = threading.Lock()


def _get_bg_loop() -> asyncio.AbstractEventLoop:
    """
    Get (or create) a persistent background event loop running in its own thread.

    The Neo4j AsyncDriver binds its connection pool to a specific event loop.
    Using asyncio.run() creates a *new* loop each time; the old driver becomes
    unusable in the new loop, causing hangs.  By reusing the same loop across
    all sync→async bridge calls, we keep the driver alive for the lifetime of
    the process.
    """
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            _bg_loop = asyncio.new_event_loop()

            def _run():
                asyncio.set_event_loop(_bg_loop)
                _bg_loop.run_forever()

            _bg_thread = threading.Thread(target=_run, daemon=True)
            _bg_thread.start()
    return _bg_loop


def _run_async(coro):
    """Run an async coroutine synchronously via a persistent background loop."""
    loop = _get_bg_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[GraphIntelligenceService] = None


def get_graph_intelligence_service() -> GraphIntelligenceService:
    """Get singleton GraphIntelligenceService."""
    global _service
    if _service is None:
        _service = GraphIntelligenceService()
    return _service
