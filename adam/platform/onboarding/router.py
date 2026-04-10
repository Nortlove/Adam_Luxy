"""
Onboarding API Router — 6-phase self-service partner activation.

Phase endpoints:
  POST /account           — Phase 1: Create account
  POST /{id}/platform     — Phase 2: Select platform/blueprint
  GET  /{id}/questions     — Dynamic Phase 3 questions
  POST /{id}/inbound-data — Phase 3: Configure inbound data
  GET  /{id}/products      — Ranked intelligence products for Phase 4
  POST /{id}/intelligence  — Phase 4: Select intelligence products
  POST /{id}/connections   — Phase 5: Wire connections + activate
  POST /{id}/feedback      — Phase 6: Configure feedback loop
  GET  /{id}/status        — Onboarding status
  GET  /{id}/config        — Full configuration

Also retains legacy:
  POST /activate          — Single-call activation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from adam.platform.onboarding.models import (
    AccountCreationRequest,
    AccountCreationResponse,
    BUSINESS_TYPE_BLUEPRINT_MAP,
    BUSINESS_TYPE_LABELS,
    ConnectionWiringRequest,
    ConnectionWiringResponse,
    FeedbackConfigRequest,
    FeedbackConfigResponse,
    InboundDataRequest,
    InboundDataResponse,
    IntelligenceSelectionRequest,
    IntelligenceSelectionResponse,
    PlatformSelectionRequest,
    PlatformSelectionResponse,
)
from adam.platform.onboarding.service import (
    OnboardingRequest,
    OnboardingResult,
    OnboardingService,
    get_onboarding_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


async def _svc() -> OnboardingService:
    return await get_onboarding_service()


# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: Account Creation
# ═══════════════════════════════════════════════════════════════════════

@router.post("/account", response_model=AccountCreationResponse)
async def create_account(
    request: AccountCreationRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Phase 1: Create account, issue auth token, start onboarding."""
    try:
        return await svc.create_account(request)
    except Exception as e:
        logger.error("Account creation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Platform Identification
# ═══════════════════════════════════════════════════════════════════════

@router.get("/business-types")
async def list_business_types():
    """Return all business type options for Phase 2 selection."""
    types = []
    for key, label in BUSINESS_TYPE_LABELS.items():
        types.append({
            "id": key,
            "label": label,
            "blueprint_id": BUSINESS_TYPE_BLUEPRINT_MAP.get(key, ""),
        })
    return {"business_types": types}


@router.post("/{tenant_id}/platform", response_model=PlatformSelectionResponse)
async def select_platform(
    tenant_id: str,
    request: PlatformSelectionRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Phase 2: Select your business type / Blueprint."""
    try:
        return await svc.select_platform(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Platform selection failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-blueprint")
async def suggest_blueprint(
    contact_role: str = Query(default=""),
    svc: OnboardingService = Depends(_svc),
):
    """Auto-suggest business type from contact role."""
    return await svc.get_role_suggestion(contact_role)


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Inbound Data Specification
# ═══════════════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/questions")
async def get_phase3_questions(
    tenant_id: str,
    svc: OnboardingService = Depends(_svc),
):
    """Return dynamic Phase 3 questions based on selected Blueprint."""
    try:
        questions = await svc.get_phase3_questions(tenant_id)
        return {"tenant_id": tenant_id, "questions": questions}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{tenant_id}/inbound-data", response_model=InboundDataResponse)
async def configure_inbound_data(
    tenant_id: str,
    request: InboundDataRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Phase 3: Specify inbound data, get intelligence capability score."""
    try:
        return await svc.configure_inbound_data(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Inbound data config failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Intelligence Menu
# ═══════════════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/products")
async def get_intelligence_products(
    tenant_id: str,
    svc: OnboardingService = Depends(_svc),
):
    """Return ranked intelligence products for Phase 4 selection."""
    try:
        products = await svc.get_intelligence_products(tenant_id)
        return {"tenant_id": tenant_id, "products": products}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{tenant_id}/intelligence", response_model=IntelligenceSelectionResponse)
async def select_intelligence(
    tenant_id: str,
    request: IntelligenceSelectionRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Phase 4: Select which intelligence products to activate."""
    try:
        return await svc.select_intelligence(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Intelligence selection failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: Connection Wiring
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{tenant_id}/connections", response_model=ConnectionWiringResponse)
async def wire_connections(
    tenant_id: str,
    request: ConnectionWiringRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Phase 5: Wire connectors/adapters and activate the system."""
    try:
        return await svc.wire_connections(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Connection wiring failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 6: Feedback Loop
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{tenant_id}/feedback", response_model=FeedbackConfigResponse)
async def configure_feedback(
    tenant_id: str,
    request: FeedbackConfigRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Phase 6: Configure outcome feedback loop for learning systems."""
    try:
        return await svc.configure_feedback(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Feedback config failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# STATUS & MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/status")
async def onboarding_status(
    tenant_id: str,
    svc: OnboardingService = Depends(_svc),
):
    """Check onboarding progress."""
    return await svc.get_onboarding_status(tenant_id)


@router.get("/{tenant_id}/config")
async def get_config(
    tenant_id: str,
    svc: OnboardingService = Depends(_svc),
):
    """Return full tenant configuration."""
    return await svc.get_full_config(tenant_id)


# ═══════════════════════════════════════════════════════════════════════
# LEGACY: Single-Call Activation
# ═══════════════════════════════════════════════════════════════════════

@router.post("/activate", response_model=OnboardingResult)
async def onboard_partner(
    request: OnboardingRequest,
    svc: OnboardingService = Depends(_svc),
):
    """Legacy single-call partner activation."""
    try:
        result = await svc.onboard(request)
        return result
    except Exception as e:
        logger.error("Onboarding failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
