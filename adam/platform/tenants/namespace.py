"""
Tenant Namespace — data isolation across Neo4j, Redis, and Kafka.

Follows ADAM's existing patterns:
- Redis keys via CacheKeyBuilder (adam/infrastructure/redis/cache.py)
- Neo4j queries with tenant_id property filter
- Kafka consumer groups with tenant prefix
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TenantNamespace:
    """
    Manages namespace isolation for a single tenant across all infrastructure.

    Redis isolation: All keys prefixed with bp:{blueprint}:{tenant_id}:
    Neo4j isolation: All tenant-specific nodes carry tenant_id property.
    Kafka isolation: Per-tenant consumer groups within shared topics.
    """

    def __init__(self, tenant_id: str, blueprint_id: str):
        self.tenant_id = tenant_id
        self.blueprint_id = blueprint_id.lower()
        self._prefix = f"bp:{self.blueprint_id}:{self.tenant_id}"

    # ── Redis Key Generation ──────────────────────────────────────────────

    def redis_key(self, key_type: str, *parts: str) -> str:
        """Build a namespaced Redis key: bp:{blueprint}:{tenant}:{type}:{parts...}"""
        segments = [self._prefix, key_type] + list(parts)
        return ":".join(segments)

    def config_key(self) -> str:
        return self.redis_key("config")

    def profile_key(self, content_id: str) -> str:
        return self.redis_key("profile", content_id)

    def segments_key(self, content_id: str) -> str:
        return self.redis_key("segments", content_id)

    def delivery_key(self, ssp_id: str) -> str:
        return self.redis_key("delivery", ssp_id, "status")

    def priors_key(self, category: str) -> str:
        return self.redis_key("priors", category)

    def metrics_key(self, metric_name: str) -> str:
        return self.redis_key("metrics", metric_name)

    def pattern(self, key_type: str = "*") -> str:
        """Glob pattern for scanning all keys of a given type."""
        return f"{self._prefix}:{key_type}:*"

    def all_keys_pattern(self) -> str:
        return f"{self._prefix}:*"

    # ── Redis Lifecycle ───────────────────────────────────────────────────

    async def initialize_redis(self, redis_client, tenant_config: Dict[str, Any]) -> None:
        """Store tenant config and allocate key namespace."""
        await redis_client.set(
            self.config_key(),
            json.dumps(tenant_config, default=str),
        )
        logger.info("Redis namespace initialized for tenant %s", self.tenant_id)

    async def destroy_redis(self, redis_client) -> int:
        """Remove all keys in this tenant's namespace. Returns count deleted."""
        pattern = self.all_keys_pattern()
        count = 0
        async for key in redis_client.scan_iter(match=pattern, count=200):
            await redis_client.delete(key)
            count += 1
        logger.info("Destroyed %d Redis keys for tenant %s", count, self.tenant_id)
        return count

    # ── Neo4j Tenant Partition ────────────────────────────────────────────

    @staticmethod
    async def register_in_graph(session, tenant_id: str, blueprint_id: str, config: Dict[str, Any]) -> None:
        """Register the tenant as a node in Neo4j for query partitioning."""
        query = """
        MERGE (t:Tenant {tenant_id: $tenant_id})
        SET t.blueprint_id = $blueprint_id,
            t.status = 'active',
            t.organization = $org,
            t.category = $category,
            t.scale_tier = $scale_tier,
            t.activated_at = datetime()
        RETURN t.tenant_id AS id
        """
        await session.run(
            query,
            tenant_id=tenant_id,
            blueprint_id=blueprint_id,
            org=config.get("organization_name", ""),
            category=config.get("category", "general"),
            scale_tier=config.get("scale_tier", "starter"),
        )
        logger.info("Neo4j tenant node created for %s", tenant_id)

    @staticmethod
    async def deactivate_in_graph(session, tenant_id: str) -> None:
        query = """
        MATCH (t:Tenant {tenant_id: $tenant_id})
        SET t.status = 'deactivated', t.deactivated_at = datetime()
        """
        await session.run(query, tenant_id=tenant_id)

    @staticmethod
    async def get_tenant_content_count(session, tenant_id: str) -> int:
        result = await session.run(
            "MATCH (c:TenantContent {tenant_id: $tid}) RETURN count(c) AS cnt",
            tid=tenant_id,
        )
        record = await result.single()
        return record["cnt"] if record else 0

    # ── Neo4j Tenant-Scoped Queries ───────────────────────────────────────

    def cypher_content_filter(self, alias: str = "c") -> str:
        """Returns a Cypher WHERE clause fragment for tenant content isolation."""
        return f"{alias}.tenant_id = '{self.tenant_id}'"

    # ── Kafka Consumer Group ──────────────────────────────────────────────

    @property
    def consumer_group(self) -> str:
        return f"{self.blueprint_id}-{self.tenant_id}"

    # ── Convenience ───────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"TenantNamespace(tenant={self.tenant_id}, blueprint={self.blueprint_id})"
