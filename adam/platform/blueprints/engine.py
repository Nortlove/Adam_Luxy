"""
Blueprint Engine — activates and manages Blueprint instances for tenants.

This is the central orchestrator that:
1. Reads the BlueprintSpec for a given Blueprint type
2. Instantiates the required connectors, intelligence components, and delivery adapters
3. Wires them together into a running pipeline
4. Manages the pipeline lifecycle (start, stop, health)

The shared ADAM intelligence graph (52.8M+ elements) is NEVER copied or partitioned.
Tenants get their own namespace for content and segments, but they all query
the same graph for psychological intelligence.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.platform.blueprints.registry import BlueprintRegistry, BlueprintSpec
from adam.platform.connectors.base import BaseConnector
from adam.platform.connectors.factory import create_connector
from adam.platform.delivery.base import BaseDeliveryAdapter
from adam.platform.delivery.factory import create_adapter
from adam.platform.tenants.models import BlueprintType, Tenant, TenantConfig
from adam.platform.tenants.namespace import TenantNamespace

logger = logging.getLogger(__name__)


class BlueprintInstance:
    """A running Blueprint instance for a specific tenant."""

    def __init__(
        self,
        tenant: Tenant,
        spec: BlueprintSpec,
        namespace: TenantNamespace,
    ):
        self.tenant = tenant
        self.spec = spec
        self.namespace = namespace
        self.connectors: Dict[str, BaseConnector] = {}
        self.delivery_adapters: Dict[str, BaseDeliveryAdapter] = {}
        self.intelligence_refs: List[str] = list(spec.intelligence_components)
        self.intelligence_bridge: Dict[str, Any] = {}
        self.active_optional: List[str] = []
        self.started_at: Optional[datetime] = None
        self._running = False

    async def start(self) -> None:
        """Start all connectors (background polling)."""
        self._running = True
        self.started_at = datetime.now(timezone.utc)

        for name, connector in self.connectors.items():
            try:
                await connector.start()
                logger.info(
                    "[%s] Connector %s started", self.tenant.tenant_id, name,
                )
            except Exception as e:
                logger.error(
                    "[%s] Failed to start connector %s: %s",
                    self.tenant.tenant_id, name, e,
                )

    async def stop(self) -> None:
        """Stop all connectors."""
        self._running = False
        for name, connector in self.connectors.items():
            try:
                await connector.stop()
            except Exception as e:
                logger.warning("[%s] Error stopping connector %s: %s", self.tenant.tenant_id, name, e)

    def get_health(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant.tenant_id,
            "blueprint": self.spec.blueprint_type.value,
            "running": self._running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "intelligence_components": self.intelligence_refs,
            "active_optional": self.active_optional,
            "connectors": {n: c.get_health() for n, c in self.connectors.items()},
            "delivery_adapters": {n: a.get_health() for n, a in self.delivery_adapters.items()},
            "intelligence_bridge": {
                k: (v is not None) for k, v in self.intelligence_bridge.items()
            },
        }


class BlueprintEngine:
    """
    Central engine managing all Blueprint instances across tenants.

    Responsible for:
    - Activating blueprints for new tenants (wiring connectors + adapters)
    - Checking optional component conditions (journey tracking, A/B testing)
    - Providing cross-tenant learning signals (anonymous, privacy-safe)
    - Managing the full lifecycle
    """

    def __init__(self, neo4j_driver=None, redis_client=None):
        self._neo4j = neo4j_driver
        self._redis = redis_client
        self._instances: Dict[str, BlueprintInstance] = {}
        self._shared_intelligence: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """Bootstrap shared intelligence references (singletons) and intelligence bridge."""
        try:
            from adam.cold_start.service import get_cold_start_service
            self._shared_intelligence["cold_start_service"] = get_cold_start_service()
        except (ImportError, Exception):
            pass

        try:
            from adam.services.graph_intelligence import GraphIntelligenceService
            self._shared_intelligence["graph_intelligence_service"] = GraphIntelligenceService(
                neo4j_driver=self._neo4j
            )
        except (ImportError, Exception):
            pass

        try:
            from adam.features.service import FeatureStoreService
            self._shared_intelligence["feature_store_service"] = FeatureStoreService(
                neo4j_driver=self._neo4j,
            )
        except (ImportError, Exception):
            pass

        try:
            from adam.intelligence.unified_intelligence_service import UnifiedIntelligenceService
            self._shared_intelligence["unified_intelligence_service"] = UnifiedIntelligenceService(
                neo4j_driver=self._neo4j
            )
        except (ImportError, Exception):
            pass

        try:
            from adam.platform.intelligence.content_profiler import ContentProfiler
            self._shared_intelligence["content_profiler"] = ContentProfiler(
                unified_intelligence=self._shared_intelligence.get("unified_intelligence_service"),
                graph_intelligence=self._shared_intelligence.get("graph_intelligence_service"),
                neo4j_driver=self._neo4j,
            )
        except (ImportError, Exception):
            pass

        try:
            from adam.platform.intelligence.segment_builder import SegmentBuilder
            self._shared_intelligence["segment_builder"] = SegmentBuilder(
                graph_intelligence=self._shared_intelligence.get("graph_intelligence_service"),
            )
        except (ImportError, Exception):
            pass

        try:
            from adam.platform.intelligence.taxonomy_mapper import TaxonomyMapper
            self._shared_intelligence["taxonomy_mapper"] = TaxonomyMapper()
        except (ImportError, Exception):
            pass

        try:
            from adam.platform.intelligence.outcome_bridge import OutcomeBridge
            learning_hub = None
            gradient_bridge = None
            event_bus = None
            try:
                from adam.core.learning.unified_learning_hub import get_unified_learning_hub
                learning_hub = get_unified_learning_hub()
            except (ImportError, Exception):
                pass
            try:
                from adam.core.learning.event_bus import get_event_bus_async
                event_bus = get_event_bus_async()
            except (ImportError, Exception):
                pass

            self._shared_intelligence["outcome_bridge"] = OutcomeBridge(
                learning_hub=learning_hub,
                gradient_bridge=gradient_bridge,
                cold_start_service=self._shared_intelligence.get("cold_start_service"),
                event_bus=event_bus,
            )
        except (ImportError, Exception):
            pass

        try:
            from adam.dsp.pipeline import DSPEnrichmentPipeline
            self._shared_intelligence["dsp_enrichment_pipeline"] = DSPEnrichmentPipeline()
        except (ImportError, Exception):
            pass

        logger.info(
            "BlueprintEngine initialized with %d shared intelligence components: %s",
            len(self._shared_intelligence),
            list(self._shared_intelligence.keys()),
        )

    async def activate(self, tenant: Tenant, connector_configs: Optional[Dict[str, Dict]] = None, adapter_configs: Optional[Dict[str, Dict]] = None) -> BlueprintInstance:
        """
        Activate a Blueprint for a tenant:
        1. Look up BlueprintSpec from registry
        2. Create TenantNamespace
        3. Instantiate connectors from spec.supported_connectors
        4. Instantiate delivery adapters from spec.supported_delivery
        5. Wire intelligence components (shared singletons)
        6. Check optional component conditions
        7. Start the pipeline
        """
        spec = BlueprintRegistry.get(tenant.blueprint_id)
        ns = TenantNamespace(tenant.tenant_id, tenant.blueprint_id.value)

        instance = BlueprintInstance(tenant=tenant, spec=spec, namespace=ns)

        connector_configs = connector_configs or {}
        for conn_type in spec.supported_connectors:
            if conn_type in connector_configs:
                cfg = {
                    **connector_configs[conn_type],
                    "neo4j_driver": self._neo4j,
                    "redis_client": self._redis,
                }
                try:
                    connector = create_connector(
                        connector_type=conn_type,
                        tenant_id=tenant.tenant_id,
                        namespace_prefix=ns._prefix,
                        config=cfg,
                    )
                    instance.connectors[conn_type] = connector
                except Exception as e:
                    logger.warning(
                        "[%s] Failed to create connector %s: %s",
                        tenant.tenant_id, conn_type, e,
                    )

        adapter_configs = adapter_configs or {}
        for adapter_type in spec.supported_delivery:
            cfg = adapter_configs.get(adapter_type, {})
            try:
                adapter = create_adapter(
                    adapter_type=adapter_type,
                    tenant_id=tenant.tenant_id,
                    namespace_prefix=ns._prefix,
                    config=cfg,
                )
                instance.delivery_adapters[adapter_type] = adapter
            except Exception as e:
                logger.warning(
                    "[%s] Failed to create adapter %s: %s",
                    tenant.tenant_id, adapter_type, e,
                )

        profiler = self._shared_intelligence.get("content_profiler")
        if profiler:
            for connector in instance.connectors.values():
                connector.set_profiler(profiler)

        dsp_pipeline = self._shared_intelligence.get("dsp_enrichment_pipeline")
        if dsp_pipeline:
            for connector in instance.connectors.values():
                if hasattr(connector, "set_dsp_pipeline"):
                    connector.set_dsp_pipeline(dsp_pipeline)

        instance.intelligence_bridge = {
            "profiler": profiler,
            "segment_builder": self._shared_intelligence.get("segment_builder"),
            "taxonomy_mapper": self._shared_intelligence.get("taxonomy_mapper"),
            "outcome_bridge": self._shared_intelligence.get("outcome_bridge"),
            "unified_intelligence": self._shared_intelligence.get("unified_intelligence_service"),
            "dsp_pipeline": dsp_pipeline,
        }

        for opt_flag, component_name in spec.optional_components.items():
            if getattr(tenant.config, opt_flag, False):
                instance.active_optional.append(component_name)
                logger.info(
                    "[%s] Optional component activated: %s (flag: %s)",
                    tenant.tenant_id, component_name, opt_flag,
                )

        self._instances[tenant.tenant_id] = instance

        await instance.start()
        logger.info(
            "[%s] Blueprint %s activated: %d connectors, %d adapters, %d intel components",
            tenant.tenant_id,
            spec.blueprint_type.value,
            len(instance.connectors),
            len(instance.delivery_adapters),
            len(instance.intelligence_refs),
        )

        return instance

    async def deactivate(self, tenant_id: str) -> bool:
        instance = self._instances.pop(tenant_id, None)
        if instance is None:
            return False
        await instance.stop()
        logger.info("[%s] Blueprint deactivated", tenant_id)
        return True

    def get_instance(self, tenant_id: str) -> Optional[BlueprintInstance]:
        return self._instances.get(tenant_id)

    async def get_all_health(self) -> Dict[str, Any]:
        return {
            "total_instances": len(self._instances),
            "shared_intelligence": list(self._shared_intelligence.keys()),
            "instances": {
                tid: inst.get_health()
                for tid, inst in self._instances.items()
            },
        }

    async def run_pipeline_cycle(self, tenant_id: str) -> Dict[str, Any]:
        """
        Manually trigger one full pipeline cycle for a tenant:
        connectors poll → process → deliver.
        """
        instance = self._instances.get(tenant_id)
        if not instance:
            return {"error": f"No active blueprint for {tenant_id}"}

        results = {"tenant_id": tenant_id, "connectors": {}, "delivery": {}}

        for name, connector in instance.connectors.items():
            try:
                count = await connector.run_cycle()
                results["connectors"][name] = {"items_processed": count}
            except Exception as e:
                results["connectors"][name] = {"error": str(e)}

        return results

    @property
    def active_count(self) -> int:
        return len(self._instances)


# ── Singleton ─────────────────────────────────────────────────────────────

_engine: Optional[BlueprintEngine] = None


async def get_blueprint_engine(
    neo4j_driver=None, redis_client=None
) -> BlueprintEngine:
    global _engine
    if _engine is None:
        _engine = BlueprintEngine(
            neo4j_driver=neo4j_driver,
            redis_client=redis_client,
        )
        await _engine.initialize()
    return _engine
