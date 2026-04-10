"""
TenantService — tenant lifecycle management and Blueprint activation.

Follows ADAM's singleton pattern (see get_kafka_producer, get_cold_start_service)
and integrates with the existing Infrastructure singleton for Neo4j/Redis access.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from adam.platform.tenants.models import (
    ActivationResult,
    BlueprintType,
    ScaleTier,
    Tenant,
    TenantConfig,
    TenantStatus,
    _generate_api_key,
    _generate_tenant_id,
)
from adam.platform.tenants.namespace import TenantNamespace

logger = logging.getLogger(__name__)


BLUEPRINT_COMPONENTS = {
    BlueprintType.PUB_ENR: {
        "description": "Publisher Audience Segment Enrichment",
        "components": [
            "content_profiler",      # NDF profiling of publisher content
            "segment_builder",       # 12-domain psychological segments
            "taxonomy_mapper",       # Map ADAM constructs → IAB taxonomy
        ],
        "connectors": ["rss", "sitemap", "cms_webhook"],
        "delivery": ["magnite", "prebid", "index_exchange"],
    },
    BlueprintType.DSP_TGT: {
        "description": "DSP Psychological Audience Targeting",
        "components": [
            "bidstream_enricher",    # Real-time impression enrichment
            "segment_scorer",        # 27-dimension alignment scoring
            "mechanism_optimizer",   # Persuasion mechanism selection
        ],
        "connectors": ["bidstream", "audience_feed"],
        "delivery": ["stackadapt", "ttd", "dv360"],
    },
    BlueprintType.AUD_LST: {
        "description": "Audio Listener Intelligence",
        "components": [
            "content_profiler",
            "listener_modeler",      # Temporal listener state
            "host_briefing_gen",     # Host-read ad guidance
        ],
        "connectors": ["s3_audio", "rss", "transcript_db"],
        "delivery": ["megaphone", "triton", "spotify_ad_studio"],
    },
    BlueprintType.DSP_CRE: {
        "description": "DSP Creative Optimization",
        "components": [
            "creative_analyzer",     # NDF analysis of ad creative
            "alignment_scorer",      # Creative ↔ audience alignment
            "variant_optimizer",     # Multi-arm creative testing
        ],
        "connectors": ["creative_api", "asset_feed"],
        "delivery": ["stackadapt", "ttd"],
    },
    BlueprintType.PUB_YLD: {
        "description": "Publisher Yield Optimization",
        "components": [
            "floor_optimizer",       # Psychological attention → floor price
            "context_enricher",      # Content moment → ad context signal
            "demand_scorer",         # Score demand partners per slot
        ],
        "connectors": ["rss", "sitemap", "real_time_content"],
        "delivery": ["magnite", "pubmatic", "openx"],
    },
    BlueprintType.BRD_INT: {
        "description": "Brand Intelligence Suite",
        "components": [
            "brand_analyzer",        # Cialdini + Aaker brand profiling
            "competitive_mapper",    # Competitive mechanism landscape
            "copy_optimizer",        # Copy effectiveness prediction
        ],
        "connectors": ["brand_feed", "creative_api"],
        "delivery": ["analytics_dashboard"],
    },
    BlueprintType.AGY_PLN: {
        "description": "Agency Planning Tools",
        "components": [
            "audience_planner",      # Psychological audience sizing
            "media_matcher",         # Media ↔ audience alignment
            "campaign_predictor",    # Outcome prediction
        ],
        "connectors": ["audience_feed", "media_plan_feed"],
        "delivery": ["planning_api"],
    },
    BlueprintType.CTV_AUD: {
        "description": "CTV Audience Intelligence",
        "components": [
            "content_profiler",
            "household_modeler",     # Household-level psychology
            "moment_optimizer",      # Content moment targeting
        ],
        "connectors": ["content_api", "acr_feed"],
        "delivery": ["freewheel", "springserve"],
    },
    BlueprintType.RET_PSY: {
        "description": "Retail Psychological Targeting",
        "components": [
            "product_profiler",      # 80-construct product NDF
            "shopper_modeler",       # Purchase psychology model
            "mechanism_optimizer",
        ],
        "connectors": ["product_feed", "purchase_feed"],
        "delivery": ["retail_media_api"],
    },
    BlueprintType.SOC_AUD: {
        "description": "Social Audience Enrichment",
        "components": [
            "social_profiler",       # Social signal → NDF
            "engagement_modeler",    # Engagement prediction
            "creative_advisor",      # Social creative guidance
        ],
        "connectors": ["social_api"],
        "delivery": ["meta_api", "tiktok_api", "snap_api"],
    },
    BlueprintType.EXC_DAT: {
        "description": "Exchange Data Enrichment",
        "components": [
            "bidstream_enricher",
            "contextual_scorer",     # URL → NDF context scoring
            "segment_builder",
        ],
        "connectors": ["exchange_feed"],
        "delivery": ["seat_api"],
    },
}


class TenantService:
    """
    Manages tenant lifecycle: registration → activation → serving → deactivation.

    State is persisted in Redis (hot) and Neo4j (durable).
    The shared ADAM intelligence graph (Layer 1/2/3) is NEVER partitioned —
    tenant isolation applies only to content, segments, and delivery.
    """

    def __init__(self, neo4j_driver=None, redis_client=None):
        self._neo4j = neo4j_driver
        self._redis = redis_client
        self._tenants: Dict[str, Tenant] = {}
        self._key_index: Dict[str, str] = {}  # api_key_hash → tenant_id

    async def initialize(self) -> None:
        """Load active tenants from Redis on startup."""
        if self._redis is None:
            logger.warning("TenantService initialized without Redis — in-memory only")
            return

        try:
            cursor = None
            pattern = "bp:*:config"
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                for key in keys:
                    raw = await self._redis.get(key)
                    if raw:
                        data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
                        tenant = Tenant.model_validate(data)
                        self._tenants[tenant.tenant_id] = tenant
                        self._key_index[tenant.api_key_hash] = tenant.tenant_id
                if cursor == 0:
                    break
            logger.info("Loaded %d tenants from Redis", len(self._tenants))
        except Exception as e:
            logger.warning("Could not load tenants from Redis: %s", e)

    # ── Registration ──────────────────────────────────────────────────────

    async def register(
        self,
        blueprint_id: BlueprintType,
        organization_name: Optional[str] = None,
        scale_tier: ScaleTier = ScaleTier.STARTER,
        **extra_config,
    ) -> ActivationResult:
        """
        Single-call tenant activation:
        1. Generate tenant_id and API key
        2. Create namespace isolation in Redis
        3. Register tenant node in Neo4j
        4. Return credentials
        """
        tenant_id = _generate_tenant_id(blueprint_id)
        api_key = _generate_api_key()
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        config = TenantConfig(
            blueprint_id=blueprint_id,
            organization_name=organization_name,
            scale_tier=scale_tier,
            **extra_config,
        )

        tenant = Tenant(
            tenant_id=tenant_id,
            api_key_hash=api_key_hash,
            config=config,
            status=TenantStatus.ACTIVATING,
        )

        ns = TenantNamespace(tenant_id, blueprint_id.value)

        if self._redis:
            await ns.initialize_redis(self._redis, tenant.model_dump(mode="json"))

        if self._neo4j:
            async with self._neo4j.session() as session:
                await TenantNamespace.register_in_graph(
                    session, tenant_id, blueprint_id.value, config.model_dump()
                )

        tenant.status = TenantStatus.ACTIVE
        tenant.activated_at = datetime.now(timezone.utc)

        self._tenants[tenant_id] = tenant
        self._key_index[api_key_hash] = tenant_id

        if self._redis:
            await self._redis.set(
                ns.config_key(),
                json.dumps(tenant.model_dump(mode="json"), default=str),
            )

        bp_spec = BLUEPRINT_COMPONENTS.get(blueprint_id, {})

        logger.info(
            "Tenant %s activated (blueprint=%s, tier=%s)",
            tenant_id, blueprint_id.value, scale_tier.value,
        )

        return ActivationResult(
            tenant_id=tenant_id,
            api_key=api_key,
            api_endpoint=f"/api/v1/{tenant_id}",
            dashboard_url=f"/dashboard/{tenant_id}",
            docs_url=f"/api/v1/{tenant_id}/docs",
            status=tenant.status,
            intelligence_depth={
                "graph_elements": "52.8M+",
                "psychological_constructs": 441,
                "edge_dimensions": 27,
                "learning_systems": 9,
                "reasoning_atoms": 30,
                "blueprint": bp_spec.get("description", ""),
                "active_components": bp_spec.get("components", []),
                "supported_connectors": bp_spec.get("connectors", []),
                "supported_delivery": bp_spec.get("delivery", []),
            },
        )

    # ── Lookup ────────────────────────────────────────────────────────────

    async def resolve_by_key(self, api_key_hash: str) -> Optional[Tenant]:
        tid = self._key_index.get(api_key_hash)
        if tid:
            return self._tenants.get(tid)
        return None

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    async def list_tenants(
        self,
        blueprint_filter: Optional[BlueprintType] = None,
        status_filter: Optional[TenantStatus] = None,
    ) -> List[Tenant]:
        tenants = list(self._tenants.values())
        if blueprint_filter:
            tenants = [t for t in tenants if t.blueprint_id == blueprint_filter]
        if status_filter:
            tenants = [t for t in tenants if t.status == status_filter]
        return tenants

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def pause(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.PAUSED
        await self._persist(tenant)
        logger.info("Tenant %s paused", tenant_id)
        return True

    async def resume(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant or tenant.status != TenantStatus.PAUSED:
            return False
        tenant.status = TenantStatus.ACTIVE
        await self._persist(tenant)
        logger.info("Tenant %s resumed", tenant_id)
        return True

    async def deactivate(self, tenant_id: str) -> bool:
        """Deactivate tenant and clean up namespace data."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.status = TenantStatus.DEACTIVATED
        ns = TenantNamespace(tenant_id, tenant.blueprint_id.value)

        if self._neo4j:
            try:
                async with self._neo4j.session() as session:
                    await TenantNamespace.deactivate_in_graph(session, tenant_id)
            except Exception as e:
                logger.error("Failed to deactivate tenant %s in Neo4j: %s", tenant_id, e)

        if self._redis:
            try:
                await ns.destroy_redis(self._redis)
            except Exception as e:
                logger.error("Failed to clean Redis for tenant %s: %s", tenant_id, e)

        self._key_index = {k: v for k, v in self._key_index.items() if v != tenant_id}
        del self._tenants[tenant_id]
        logger.info("Tenant %s deactivated and cleaned up", tenant_id)
        return True

    # ── Stats ─────────────────────────────────────────────────────────────

    async def get_stats(self) -> Dict:
        by_blueprint: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for t in self._tenants.values():
            bp = t.blueprint_id.value
            by_blueprint[bp] = by_blueprint.get(bp, 0) + 1
            st = t.status.value
            by_status[st] = by_status.get(st, 0) + 1

        return {
            "total_tenants": len(self._tenants),
            "by_blueprint": by_blueprint,
            "by_status": by_status,
        }

    # ── Blueprint Info ────────────────────────────────────────────────────

    @staticmethod
    def get_available_blueprints() -> Dict[str, Dict]:
        result = {}
        for bp_type, spec in BLUEPRINT_COMPONENTS.items():
            result[bp_type.value] = {
                "name": bp_type.value,
                "description": spec["description"],
                "components": spec["components"],
                "connectors": spec["connectors"],
                "delivery_adapters": spec["delivery"],
            }
        return result

    # ── Namespace Helper ──────────────────────────────────────────────────

    def get_namespace(self, tenant_id: str) -> Optional[TenantNamespace]:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        return TenantNamespace(tenant_id, tenant.blueprint_id.value)

    # ── Internal ──────────────────────────────────────────────────────────

    async def _persist(self, tenant: Tenant) -> None:
        if not self._redis:
            return
        ns = TenantNamespace(tenant.tenant_id, tenant.blueprint_id.value)
        try:
            await self._redis.set(
                ns.config_key(),
                json.dumps(tenant.model_dump(mode="json"), default=str),
            )
        except Exception as e:
            logger.error("Failed to persist tenant %s: %s", tenant.tenant_id, e)


# ── Singleton ─────────────────────────────────────────────────────────────

_tenant_service: Optional[TenantService] = None


async def get_tenant_service(
    neo4j_driver=None, redis_client=None
) -> TenantService:
    """Module-level singleton following ADAM's get_kafka_producer() pattern."""
    global _tenant_service
    if _tenant_service is None:
        _tenant_service = TenantService(
            neo4j_driver=neo4j_driver,
            redis_client=redis_client,
        )
        await _tenant_service.initialize()
    return _tenant_service
