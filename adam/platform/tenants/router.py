"""
Tenant Management API Router.

Follows ADAM's router pattern from adam/api/decision/router.py —
prefixed, typed responses, Depends() injection.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from adam.platform.tenants.models import (
    ActivationResult,
    BlueprintType,
    ScaleTier,
    TenantStatus,
)
from adam.platform.tenants.service import TenantService, get_tenant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


# ── Request / Response Models ─────────────────────────────────────────────


class RegisterRequest(BaseModel):
    blueprint_id: BlueprintType
    organization_name: Optional[str] = None
    scale_tier: ScaleTier = ScaleTier.STARTER
    category: str = "general"
    industry_verticals: List[str] = Field(default_factory=list)
    content_types: List[str] = Field(default_factory=lambda: ["text"])


class TenantSummary(BaseModel):
    tenant_id: str
    blueprint_id: str
    status: str
    organization_name: Optional[str] = None
    scale_tier: str
    content_items_processed: int = 0
    segments_generated: int = 0
    campaigns_served: int = 0


class BlueprintInfo(BaseModel):
    name: str
    description: str
    components: List[str]
    connectors: List[str]
    delivery_adapters: List[str]


# ── Dependency ────────────────────────────────────────────────────────────


async def _svc() -> TenantService:
    return await get_tenant_service()


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/blueprints", response_model=dict)
async def list_blueprints(svc: TenantService = Depends(_svc)):
    """Available Blueprint types and their component compositions."""
    return svc.get_available_blueprints()


@router.post("/register", response_model=ActivationResult)
async def register_tenant(
    req: RegisterRequest,
    svc: TenantService = Depends(_svc),
):
    """
    Single-call tenant registration and activation.
    Returns API key, endpoint URL, and intelligence depth summary.
    """
    try:
        result = await svc.register(
            blueprint_id=req.blueprint_id,
            organization_name=req.organization_name,
            scale_tier=req.scale_tier,
            category=req.category,
            industry_verticals=req.industry_verticals,
            content_types=req.content_types,
        )
        return result
    except Exception as e:
        logger.error("Tenant registration failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}", response_model=TenantSummary)
async def get_tenant(tenant_id: str, svc: TenantService = Depends(_svc)):
    tenant = await svc.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return TenantSummary(
        tenant_id=tenant.tenant_id,
        blueprint_id=tenant.blueprint_id.value,
        status=tenant.status.value,
        organization_name=tenant.config.organization_name,
        scale_tier=tenant.config.scale_tier.value,
        content_items_processed=tenant.content_items_processed,
        segments_generated=tenant.segments_generated,
        campaigns_served=tenant.campaigns_served,
    )


@router.get("/", response_model=List[TenantSummary])
async def list_tenants(
    blueprint: Optional[BlueprintType] = Query(None),
    status: Optional[TenantStatus] = Query(None),
    svc: TenantService = Depends(_svc),
):
    tenants = await svc.list_tenants(blueprint_filter=blueprint, status_filter=status)
    return [
        TenantSummary(
            tenant_id=t.tenant_id,
            blueprint_id=t.blueprint_id.value,
            status=t.status.value,
            organization_name=t.config.organization_name,
            scale_tier=t.config.scale_tier.value,
            content_items_processed=t.content_items_processed,
            segments_generated=t.segments_generated,
            campaigns_served=t.campaigns_served,
        )
        for t in tenants
    ]


@router.post("/{tenant_id}/pause")
async def pause_tenant(tenant_id: str, svc: TenantService = Depends(_svc)):
    ok = await svc.pause(tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found or already paused")
    return {"status": "paused", "tenant_id": tenant_id}


@router.post("/{tenant_id}/resume")
async def resume_tenant(tenant_id: str, svc: TenantService = Depends(_svc)):
    ok = await svc.resume(tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found or not paused")
    return {"status": "active", "tenant_id": tenant_id}


@router.delete("/{tenant_id}")
async def deactivate_tenant(tenant_id: str, svc: TenantService = Depends(_svc)):
    ok = await svc.deactivate(tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return {"status": "deactivated", "tenant_id": tenant_id}


@router.get("/{tenant_id}/stats")
async def tenant_stats(tenant_id: str, svc: TenantService = Depends(_svc)):
    tenant = await svc.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    ns = svc.get_namespace(tenant_id)
    return {
        "tenant_id": tenant_id,
        "blueprint": tenant.blueprint_id.value,
        "status": tenant.status.value,
        "scale_tier": tenant.config.scale_tier.value,
        "rate_limits": tenant.rate_limits,
        "namespace": ns._prefix if ns else None,
        "content_items_processed": tenant.content_items_processed,
        "segments_generated": tenant.segments_generated,
        "campaigns_served": tenant.campaigns_served,
    }


@router.get("/stats/overview")
async def platform_stats(svc: TenantService = Depends(_svc)):
    """Platform-wide tenant statistics."""
    return await svc.get_stats()
