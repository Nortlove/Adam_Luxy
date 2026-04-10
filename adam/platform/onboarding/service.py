"""
OnboardingService — orchestrates the full 6-phase self-service tenant activation.

Phase 1: Account creation
Phase 2: Platform / Blueprint selection
Phase 3: Inbound data specification
Phase 4: Intelligence menu selection
Phase 5: Connection wiring + activation
Phase 6: Feedback loop configuration

Also retains the single-call `onboard()` for backward compatibility.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from adam.platform.tenants.models import (
    ActivationResult,
    BlueprintType,
    ScaleTier,
    TenantStatus,
    _generate_api_key,
    _generate_tenant_id,
)
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
    OnboardingPhase,
    PlatformSelectionRequest,
    PlatformSelectionResponse,
    TenantOnboardingState,
)
from adam.platform.onboarding.guidance import (
    IntelligenceCapabilityScore,
    OnboardingGuidance,
)

logger = logging.getLogger(__name__)


# ── Backward-compatible models ─────────────────────────────────────────

class OnboardingRequest(BaseModel):
    """Legacy single-call onboarding request."""
    blueprint_id: BlueprintType
    organization_name: str
    contact_email: Optional[str] = None
    scale_tier: ScaleTier = ScaleTier.STARTER
    industry_verticals: List[str] = Field(default_factory=list)
    category: str = "general"
    content_types: List[str] = Field(default_factory=lambda: ["text"])
    connector_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    adapter_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    onboarding_answers: Dict[str, Any] = Field(default_factory=dict)


class OnboardingResult(BaseModel):
    """Legacy single-call onboarding result."""
    tenant_id: str
    api_key: str
    status: str
    api_endpoint: str
    docs_url: str
    dashboard_url: str
    blueprint: str
    intelligence_summary: Dict[str, Any] = Field(default_factory=dict)
    connector_status: Dict[str, str] = Field(default_factory=dict)
    adapter_status: Dict[str, str] = Field(default_factory=dict)
    next_steps: List[str] = Field(default_factory=list)
    activated_at: str = ""


class OnboardingService:
    """
    Orchestrates both the legacy single-call and the new 6-phase self-service flow.
    """

    def __init__(self, tenant_service=None, blueprint_engine=None):
        self._tenant_svc = tenant_service
        self._blueprint_engine = blueprint_engine
        self._onboarding_states: Dict[str, TenantOnboardingState] = {}

    async def _ensure_services(self):
        if not self._tenant_svc:
            try:
                from adam.platform.tenants.service import get_tenant_service
                self._tenant_svc = await get_tenant_service()
            except Exception as e:
                raise RuntimeError(f"TenantService unavailable: {e}")
        if not self._blueprint_engine:
            try:
                from adam.platform.blueprints.engine import get_blueprint_engine
                self._blueprint_engine = await get_blueprint_engine()
            except Exception as e:
                raise RuntimeError(f"BlueprintEngine unavailable: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: Account Creation
    # ═══════════════════════════════════════════════════════════════════

    async def create_account(self, req: AccountCreationRequest) -> AccountCreationResponse:
        """Phase 1: Create tenant account, issue initial auth token."""
        prefix = "ten"
        suffix = secrets.token_hex(3)
        tenant_id = f"{prefix}-{suffix}"

        auth_token = secrets.token_urlsafe(48)

        state = TenantOnboardingState(
            tenant_id=tenant_id,
            phase=OnboardingPhase.ACCOUNT_CREATED,
            company_name=req.company_name,
            company_website=req.company_website,
            contact_name=req.contact_name,
            contact_email=req.contact_email,
            contact_role=req.contact_role,
            primary_goal=req.primary_goal,
            monthly_volume_estimate=req.monthly_volume_estimate,
        )
        self._onboarding_states[tenant_id] = state

        role_suggestion = OnboardingGuidance.suggest_blueprint_from_role(req.contact_role)

        logger.info(
            "Phase 1 complete: tenant=%s company=%s role_suggestion=%s",
            tenant_id, req.company_name, role_suggestion,
        )

        return AccountCreationResponse(
            tenant_id=tenant_id,
            auth_token=auth_token,
            next_step_url=f"/api/v1/onboarding/{tenant_id}/platform",
        )

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: Platform Identification
    # ═══════════════════════════════════════════════════════════════════

    async def select_platform(
        self, tenant_id: str, req: PlatformSelectionRequest
    ) -> PlatformSelectionResponse:
        """Phase 2: Select the business type / Blueprint."""
        state = self._get_state(tenant_id)

        if req.blueprint_id:
            bp_id = req.blueprint_id
        else:
            bp_id = BUSINESS_TYPE_BLUEPRINT_MAP.get(req.business_type, "PUB-ENR")

        state.blueprint_id = bp_id
        state.business_type = req.business_type or bp_id
        state.phase = OnboardingPhase.PLATFORM_SELECTED

        questions = OnboardingGuidance.get_phase3_questions(bp_id)
        question_ids = [q["id"] for q in questions]

        bp_descriptions = {
            "DSP-TGT": "DSP Psychological Audience Targeting — real-time impression enrichment with 27-dimension alignment scoring",
            "DSP-CRE": "DSP Creative Optimization — multi-arm bandit creative testing with gradient attribution",
            "PUB-ENR": "Publisher Audience Segment Enrichment — 14 psychological segments pushed to your SSP",
            "PUB-YLD": "Publisher Yield Optimization — floor price optimization via NDF attention scoring",
            "AUD-LST": "Audio Listener Intelligence — personality inference from listening behavior, host-read briefings",
            "BRD-INT": "Brand Intelligence Suite — 441-construct customer psychology from 937M+ reviews",
            "AGY-PLN": "Agency Planning Tools — multi-brand psychological campaign planning and prediction",
            "CTV-AUD": "CTV Audience Intelligence — household-level psychology from viewing patterns",
            "RET-PSY": "Retail Psychological Targeting — purchase psychology + mechanism optimization",
            "SOC-AUD": "Social Audience Enrichment — social signal NDF + engagement prediction",
            "EXC-DAT": "Exchange Data Enrichment — NDF quality scoring for premium tier creation",
        }

        logger.info("Phase 2 complete: tenant=%s blueprint=%s", tenant_id, bp_id)

        return PlatformSelectionResponse(
            blueprint_id=bp_id,
            blueprint_description=bp_descriptions.get(bp_id, bp_id),
            phase="2_complete",
            available_data_questions=question_ids,
        )

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: Inbound Data Specification
    # ═══════════════════════════════════════════════════════════════════

    async def configure_inbound_data(
        self, tenant_id: str, req: InboundDataRequest
    ) -> InboundDataResponse:
        """Phase 3: Configure inbound data, compute intelligence ceiling."""
        state = self._get_state(tenant_id)
        state.inbound_data = req
        state.phase = OnboardingPhase.INBOUND_CONFIGURED

        bp_id = state.blueprint_id or "PUB-ENR"
        scorer = IntelligenceCapabilityScore(req, bp_id)

        state.intelligence_ceiling = scorer.ceiling

        available_types = scorer.get_available_return_types()
        upgrade_hints = scorer.get_upgrade_hints()
        recommended = scorer.get_recommended_type()

        logger.info(
            "Phase 3 complete: tenant=%s ceiling=%s recommended=%s",
            tenant_id, scorer.ceiling, recommended,
        )

        return InboundDataResponse(
            phase="3_complete",
            intelligence_ceiling=scorer.ceiling,
            available_return_types=available_types,
            recommended_type=recommended,
            upgrade_hints=upgrade_hints,
        )

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: Intelligence Menu Selection
    # ═══════════════════════════════════════════════════════════════════

    async def select_intelligence(
        self, tenant_id: str, req: IntelligenceSelectionRequest
    ) -> IntelligenceSelectionResponse:
        """Phase 4: User selects which intelligence products they want."""
        state = self._get_state(tenant_id)
        state.selected_products = req.selected_products
        state.response_fields = req.response_fields
        state.response_format = req.response_format
        state.delivery_method = req.delivery_method
        state.webhook_url = req.webhook_url
        state.phase = OnboardingPhase.INTELLIGENCE_SELECTED

        total_power = 0.0
        if state.inbound_data and state.blueprint_id:
            scorer = IntelligenceCapabilityScore(state.inbound_data, state.blueprint_id)
            types = scorer.get_available_return_types()
            type_map = {t["id"]: t["power_level"] for t in types}
            total_power = sum(type_map.get(p, 0) for p in req.selected_products)

        logger.info(
            "Phase 4 complete: tenant=%s products=%s power=%.2f",
            tenant_id, req.selected_products, total_power,
        )

        return IntelligenceSelectionResponse(
            phase="4_complete",
            selected_count=len(req.selected_products),
            total_power=round(total_power, 2),
            active_pipelines=req.selected_products,
        )

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: Connection Wiring + Activation
    # ═══════════════════════════════════════════════════════════════════

    async def wire_connections(
        self, tenant_id: str, req: ConnectionWiringRequest
    ) -> ConnectionWiringResponse:
        """Phase 5: Wire connectors/adapters and activate the system."""
        await self._ensure_services()
        state = self._get_state(tenant_id)

        state.connector_configs = req.connector_configs
        state.adapter_configs = req.adapter_configs
        state.phase = OnboardingPhase.CONNECTIONS_WIRED

        bp_str = state.blueprint_id or "PUB-ENR"
        try:
            bp_type = BlueprintType(bp_str)
        except ValueError:
            bp_type = BlueprintType.PUB_ENR

        activation = await self._tenant_svc.register(
            blueprint_id=bp_type,
            organization_name=state.company_name,
            scale_tier=ScaleTier.GROWTH,
            category=state.inbound_data.product_category if state.inbound_data else "general",
            content_types=state.inbound_data.content_types if state.inbound_data else ["text"],
        )

        tenant = await self._tenant_svc.get_tenant(activation.tenant_id)
        connector_status: Dict[str, str] = {}
        adapter_status: Dict[str, str] = {}

        if tenant:
            try:
                instance = await self._blueprint_engine.activate(
                    tenant=tenant,
                    connector_configs=req.connector_configs,
                    adapter_configs=req.adapter_configs,
                )
                connector_status = {
                    name: conn.status.value
                    for name, conn in instance.connectors.items()
                }
                adapter_status = {
                    name: adapter.status.value
                    for name, adapter in instance.delivery_adapters.items()
                }
            except Exception as e:
                logger.error("Blueprint activation failed: %s", e)

        state.api_key = activation.api_key
        state.api_base_url = activation.api_endpoint
        real_tenant_id = activation.tenant_id
        state.tenant_id = real_tenant_id
        if real_tenant_id != tenant_id:
            self._onboarding_states[real_tenant_id] = state
            # Keep old key as alias so Phase 6 can still find the state
            # (frontend continues using the original tenant_id)

        endpoints = {
            "ingest_content": f"/api/v1/{real_tenant_id}/ingest/content",
            "ingest_signals": f"/api/v1/{real_tenant_id}/ingest/signals",
            "ingest_outcomes": f"/api/v1/{real_tenant_id}/ingest/outcomes",
            "intelligence_segments": f"/api/v1/{real_tenant_id}/intelligence/segments",
            "intelligence_batch": f"/api/v1/{real_tenant_id}/intelligence/batch",
            "dashboard": f"/api/v1/{real_tenant_id}/dashboard",
        }

        rate_limits = {"second": 100, "minute": 5_000, "day": 1_000_000}

        logger.info(
            "Phase 5 complete: tenant=%s (real=%s) api_key_prefix=%s",
            tenant_id, real_tenant_id, activation.api_key[:20],
        )

        return ConnectionWiringResponse(
            phase="5_complete",
            api_base_url=activation.api_endpoint,
            api_key=activation.api_key,
            endpoints=endpoints,
            connector_status=connector_status,
            adapter_status=adapter_status,
            rate_limits=rate_limits,
        )

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 6: Feedback Loop Setup
    # ═══════════════════════════════════════════════════════════════════

    async def configure_feedback(
        self, tenant_id: str, req: FeedbackConfigRequest
    ) -> FeedbackConfigResponse:
        """Phase 6: Configure outcome feedback for the learning loop."""
        state = self._get_state(tenant_id)
        state.feedback_config = req
        state.phase = OnboardingPhase.FEEDBACK_CONFIGURED
        state.activated_at = datetime.now(timezone.utc)

        real_tid = state.tenant_id
        webhook_url = f"https://api.adam.informativ.io/v1/{real_tid}/outcomes"
        pixel_code = (
            f'<img src="https://api.adam.informativ.io/v1/{real_tid}/pixel'
            f'?event=conversion&impression_id={{IMPRESSION_ID}}" width="1" height="1" />'
        )
        batch_url = f"https://api.adam.informativ.io/v1/{real_tid}/outcomes/batch"

        learning_count = 0
        if req.outcome_events:
            learning_count = min(9, len(req.outcome_events) * 3 + 3)

        timeline = OnboardingGuidance.generate_improvement_timeline()

        logger.info(
            "Phase 6 complete: tenant=%s events=%s method=%s learning_systems=%d",
            tenant_id, req.outcome_events, req.feedback_method, learning_count,
        )

        return FeedbackConfigResponse(
            phase="6_complete",
            webhook_url=webhook_url,
            tracking_pixel_code=pixel_code,
            batch_upload_url=batch_url,
            learning_systems_activated=learning_count,
            improvement_timeline=[{"week": t["week"], "description": t["description"]} for t in timeline],
        )

    # ═══════════════════════════════════════════════════════════════════
    # STATUS & MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════

    async def get_onboarding_status(self, tenant_id: str) -> Dict[str, Any]:
        """Check onboarding progress for a tenant."""
        state = self._onboarding_states.get(tenant_id)
        if state:
            return {
                "tenant_id": tenant_id,
                "phase": state.phase.value,
                "company_name": state.company_name,
                "blueprint_id": state.blueprint_id,
                "intelligence_ceiling": state.intelligence_ceiling,
                "selected_products": state.selected_products,
                "has_api_key": state.api_key is not None,
                "has_feedback": state.feedback_config is not None,
                "activated_at": state.activated_at.isoformat() if state.activated_at else None,
            }

        # Fall back to tenant service
        tenant = await self._tenant_svc.get_tenant(tenant_id) if self._tenant_svc else None
        if not tenant:
            return {"tenant_id": tenant_id, "status": "not_found"}

        instance = self._blueprint_engine.get_instance(tenant_id) if self._blueprint_engine else None

        return {
            "tenant_id": tenant_id,
            "status": tenant.status.value,
            "blueprint": tenant.blueprint_id.value,
            "blueprint_active": instance is not None,
            "connector_count": len(instance.connectors) if instance else 0,
            "adapter_count": len(instance.delivery_adapters) if instance else 0,
            "content_processed": tenant.content_items_processed,
            "segments_generated": tenant.segments_generated,
        }

    async def get_full_config(self, tenant_id: str) -> Dict[str, Any]:
        """Return full tenant configuration including onboarding state."""
        state = self._onboarding_states.get(tenant_id)
        if state:
            return state.model_dump(mode="json")

        tenant = await self._tenant_svc.get_tenant(tenant_id) if self._tenant_svc else None
        if not tenant:
            return {"tenant_id": tenant_id, "status": "not_found"}
        return tenant.model_dump(mode="json")

    async def get_phase3_questions(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Return dynamic Phase 3 questions based on blueprint selection."""
        state = self._onboarding_states.get(tenant_id)
        bp_id = state.blueprint_id if state else "PUB-ENR"
        return OnboardingGuidance.get_phase3_questions(bp_id or "PUB-ENR")

    async def get_intelligence_products(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Return ranked intelligence products for Phase 4."""
        state = self._onboarding_states.get(tenant_id)
        if not state or not state.inbound_data or not state.blueprint_id:
            return []
        products = OnboardingGuidance.compute_intelligence_products(
            state.inbound_data, state.blueprint_id
        )
        return [p.model_dump() for p in products]

    async def get_role_suggestion(self, contact_role: str) -> Dict[str, Any]:
        """Auto-suggest business type from role."""
        suggestion = OnboardingGuidance.suggest_blueprint_from_role(contact_role)
        return {
            "suggested_business_type": suggestion,
            "blueprint_id": BUSINESS_TYPE_BLUEPRINT_MAP.get(suggestion, "") if suggestion else "",
            "label": BUSINESS_TYPE_LABELS.get(suggestion, "") if suggestion else "",
        }

    # ═══════════════════════════════════════════════════════════════════
    # LEGACY SINGLE-CALL ONBOARD (backward compatibility)
    # ═══════════════════════════════════════════════════════════════════

    async def onboard(self, request: OnboardingRequest) -> OnboardingResult:
        """Single-call partner activation (legacy flow)."""
        await self._ensure_services()

        activation = await self._tenant_svc.register(
            blueprint_id=request.blueprint_id,
            organization_name=request.organization_name,
            scale_tier=request.scale_tier,
            category=request.category,
            industry_verticals=request.industry_verticals,
            content_types=request.content_types,
        )

        tenant = await self._tenant_svc.get_tenant(activation.tenant_id)
        if not tenant:
            raise RuntimeError(f"Tenant {activation.tenant_id} not found after registration")

        connector_status: Dict[str, str] = {}
        adapter_status: Dict[str, str] = {}

        try:
            instance = await self._blueprint_engine.activate(
                tenant=tenant,
                connector_configs=request.connector_configs,
                adapter_configs=request.adapter_configs,
            )
            connector_status = {
                name: conn.status.value
                for name, conn in instance.connectors.items()
            }
            adapter_status = {
                name: adapter.status.value
                for name, adapter in instance.delivery_adapters.items()
            }
        except Exception as e:
            logger.error("Blueprint activation failed for %s: %s", activation.tenant_id, e)

        if request.connector_configs:
            try:
                await self._blueprint_engine.run_pipeline_cycle(activation.tenant_id)
            except Exception as e:
                logger.debug("Initial ingestion trigger failed: %s", e)

        next_steps = self._generate_next_steps(request, connector_status, adapter_status)

        return OnboardingResult(
            tenant_id=activation.tenant_id,
            api_key=activation.api_key,
            status=activation.status.value,
            api_endpoint=activation.api_endpoint,
            docs_url=activation.docs_url or "",
            dashboard_url=activation.dashboard_url or "",
            blueprint=request.blueprint_id.value,
            intelligence_summary=activation.intelligence_depth,
            connector_status=connector_status,
            adapter_status=adapter_status,
            next_steps=next_steps,
            activated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _generate_next_steps(
        self, request: OnboardingRequest,
        connectors: Dict[str, str], adapters: Dict[str, str],
    ) -> List[str]:
        steps = []
        if not request.connector_configs:
            steps.append("Configure a content connector to start ingesting content.")
        if not request.adapter_configs:
            steps.append("Configure a delivery adapter to start pushing segments.")
        if not connectors:
            steps.append("No connectors are active. Add connector configuration to begin content ingestion.")
        steps.append(f"Your API key is active. Include X-API-Key header in all requests.")
        steps.append("Intelligence is available immediately — the shared graph (52.8M+ elements) is accessible.")
        if request.blueprint_id in (BlueprintType.DSP_TGT, BlueprintType.EXC_DAT):
            steps.append("For real-time enrichment, POST bid requests with mode='fast' (<100ms) or mode='full' (<200ms).")
        if request.blueprint_id == BlueprintType.AUD_LST:
            steps.append("Audio content will be profiled from transcripts. Host briefings generated per-show, per-campaign.")
        return steps

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL
    # ═══════════════════════════════════════════════════════════════════

    def _get_state(self, tenant_id: str) -> TenantOnboardingState:
        state = self._onboarding_states.get(tenant_id)
        if not state:
            raise ValueError(f"No onboarding state for tenant {tenant_id}. Complete Phase 1 first.")
        return state


_onboarding_service: Optional[OnboardingService] = None


async def get_onboarding_service() -> OnboardingService:
    global _onboarding_service
    if _onboarding_service is None:
        _onboarding_service = OnboardingService()
    return _onboarding_service
