"""
Blueprint Management API Router.

Provides endpoints for:
- Listing available Blueprint types and their specs
- Activating a Blueprint for a tenant
- Managing Blueprint lifecycle
- Health monitoring
- Running manual pipeline cycles
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from adam.platform.blueprints.engine import BlueprintEngine, get_blueprint_engine
from adam.platform.blueprints.registry import BlueprintRegistry
from adam.platform.tenants.models import BlueprintType
from adam.platform.tenants.service import TenantService, get_tenant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])


class ActivateBlueprintRequest(BaseModel):
    tenant_id: str
    connector_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    adapter_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PipelineCycleResult(BaseModel):
    tenant_id: str
    connectors: Dict[str, Any] = Field(default_factory=dict)
    delivery: Dict[str, Any] = Field(default_factory=dict)


async def _engine() -> BlueprintEngine:
    return await get_blueprint_engine()


async def _tenants() -> TenantService:
    return await get_tenant_service()


@router.get("/registry")
async def list_blueprint_specs():
    """All available Blueprint types with their component compositions."""
    return BlueprintRegistry.list_all()


@router.get("/registry/{blueprint_type}")
async def get_blueprint_spec(blueprint_type: BlueprintType):
    try:
        spec = BlueprintRegistry.get(blueprint_type)
        return spec.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/activate")
async def activate_blueprint(
    req: ActivateBlueprintRequest,
    engine: BlueprintEngine = Depends(_engine),
    svc: TenantService = Depends(_tenants),
):
    """
    Activate a Blueprint for an existing tenant.
    Wires connectors, intelligence, and delivery adapters.
    """
    tenant = await svc.get_tenant(req.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {req.tenant_id} not found")

    try:
        instance = await engine.activate(
            tenant=tenant,
            connector_configs=req.connector_configs,
            adapter_configs=req.adapter_configs,
        )
        return instance.get_health()
    except Exception as e:
        logger.error("Blueprint activation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tenant_id}/deactivate")
async def deactivate_blueprint(
    tenant_id: str,
    engine: BlueprintEngine = Depends(_engine),
):
    ok = await engine.deactivate(tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No active blueprint for {tenant_id}")
    return {"status": "deactivated", "tenant_id": tenant_id}


@router.get("/{tenant_id}/health")
async def blueprint_health(
    tenant_id: str,
    engine: BlueprintEngine = Depends(_engine),
):
    instance = engine.get_instance(tenant_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"No active blueprint for {tenant_id}")
    return instance.get_health()


@router.post("/{tenant_id}/cycle")
async def run_pipeline_cycle(
    tenant_id: str,
    engine: BlueprintEngine = Depends(_engine),
):
    """Manually trigger one full pipeline cycle for a tenant."""
    result = await engine.run_pipeline_cycle(tenant_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/health")
async def all_blueprints_health(engine: BlueprintEngine = Depends(_engine)):
    """Health of all active Blueprint instances."""
    return await engine.get_all_health()


@router.get("/connectors/available")
async def list_connectors():
    from adam.platform.connectors.factory import list_available_connectors
    return list_available_connectors()


@router.get("/delivery/available")
async def list_delivery_adapters():
    from adam.platform.delivery.factory import list_available_adapters
    return list_available_adapters()
