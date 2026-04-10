"""
Tenant data models.

Follows the Pydantic BaseModel pattern used throughout ADAM (see adam/inference/models.py,
adam/platform/constructs/models.py, adam/infrastructure/kafka/events.py).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TenantStatus(str, Enum):
    PENDING = "pending"
    ACTIVATING = "activating"
    ACTIVE = "active"
    PAUSED = "paused"
    DEACTIVATED = "deactivated"
    ERROR = "error"


class BlueprintType(str, Enum):
    """
    Blueprint types from ADAM_Deep_Technical_Architecture.md.
    Each maps to a pre-deployed composition of ADAM enhancement components.
    """
    PUB_ENR = "PUB-ENR"       # Publisher Audience Segment Enrichment
    DSP_TGT = "DSP-TGT"       # DSP Psychological Audience Targeting
    AUD_LST = "AUD-LST"       # Audio Listener Intelligence
    DSP_CRE = "DSP-CRE"       # DSP Creative Optimization
    PUB_YLD = "PUB-YLD"       # Publisher Yield Optimization
    BRD_INT = "BRD-INT"       # Brand Intelligence Suite
    AGY_PLN = "AGY-PLN"       # Agency Planning Tools
    CTV_AUD = "CTV-AUD"       # CTV Audience Intelligence
    RET_PSY = "RET-PSY"       # Retail Psychological Targeting
    SOC_AUD = "SOC-AUD"       # Social Audience Enrichment
    EXC_DAT = "EXC-DAT"       # Exchange Data Enrichment


class ScaleTier(str, Enum):
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"
    ENTERPRISE = "enterprise"


RATE_LIMITS: Dict[ScaleTier, Dict[str, int]] = {
    ScaleTier.STARTER:    {"second": 10,   "minute": 500,    "day": 100_000},
    ScaleTier.GROWTH:     {"second": 100,  "minute": 5_000,  "day": 1_000_000},
    ScaleTier.SCALE:      {"second": 1000, "minute": 50_000, "day": 10_000_000},
    ScaleTier.ENTERPRISE: {"second": 5000, "minute": 200_000, "day": 50_000_000},
}


def _generate_tenant_id(blueprint: BlueprintType) -> str:
    prefix_map = {
        BlueprintType.PUB_ENR: "pub",
        BlueprintType.DSP_TGT: "dsp",
        BlueprintType.AUD_LST: "aud",
        BlueprintType.DSP_CRE: "dsc",
        BlueprintType.PUB_YLD: "pyld",
        BlueprintType.BRD_INT: "brd",
        BlueprintType.AGY_PLN: "agy",
        BlueprintType.CTV_AUD: "ctv",
        BlueprintType.RET_PSY: "ret",
        BlueprintType.SOC_AUD: "soc",
        BlueprintType.EXC_DAT: "exc",
    }
    prefix = prefix_map.get(blueprint, "ten")
    suffix = secrets.token_hex(2)
    return f"{prefix}-{suffix}"


def _generate_api_key() -> str:
    return f"adam_live_{secrets.token_urlsafe(32)}"


class ConnectorConfig(BaseModel):
    connector_type: str
    config: Dict[str, Any] = Field(default_factory=dict)


class DeliveryConfig(BaseModel):
    adapter_type: str
    config: Dict[str, Any] = Field(default_factory=dict)


class IdentityConfig(BaseModel):
    module_type: str = "contextual"
    config: Dict[str, Any] = Field(default_factory=dict)


class TenantConfig(BaseModel):
    """Complete configuration for an active tenant — stored in Redis."""
    blueprint_id: BlueprintType
    organization_name: Optional[str] = None
    scale_tier: ScaleTier = ScaleTier.STARTER
    content_types: List[str] = Field(default_factory=lambda: ["text"])
    category: str = "general"
    industry_verticals: List[str] = Field(default_factory=list)
    content_connector: Optional[ConnectorConfig] = None
    delivery_adapter: Optional[DeliveryConfig] = None
    identity_module: Optional[IdentityConfig] = None
    audio_pipeline_active: bool = False
    journey_tracking_active: bool = False
    ab_testing_active: bool = False
    onboarding_answers: Dict[str, Any] = Field(default_factory=dict)


class Tenant(BaseModel):
    """Represents an active tenant in the ADAM platform."""
    tenant_id: str
    api_key_hash: str
    config: TenantConfig
    status: TenantStatus = TenantStatus.PENDING
    activated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_items_processed: int = 0
    segments_generated: int = 0
    campaigns_served: int = 0

    @property
    def blueprint_id(self) -> BlueprintType:
        return self.config.blueprint_id

    @property
    def redis_namespace(self) -> str:
        return f"bp:{self.config.blueprint_id.value.lower()}:{self.tenant_id}"

    @property
    def kafka_consumer_group(self) -> str:
        return f"{self.config.blueprint_id.value.lower()}-{self.tenant_id}"

    @property
    def api_prefix(self) -> str:
        return f"/api/v1/{self.tenant_id}"

    @property
    def rate_limits(self) -> Dict[str, int]:
        return RATE_LIMITS.get(self.config.scale_tier, RATE_LIMITS[ScaleTier.STARTER])


class ActivationResult(BaseModel):
    tenant_id: str
    api_key: str
    api_endpoint: str
    dashboard_url: Optional[str] = None
    docs_url: Optional[str] = None
    status: TenantStatus
    first_segments_eta: str = "1-4 hours"
    intelligence_depth: Dict[str, Any] = Field(default_factory=dict)
