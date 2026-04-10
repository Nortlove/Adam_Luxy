"""
Self-Service Onboarding Data Models.

Covers the full 6-phase onboarding wizard:
  Phase 1: Account Creation
  Phase 2: Platform Identification (Blueprint selection)
  Phase 3: Inbound Data Specification
  Phase 4: Intelligence Menu (return type selection)
  Phase 5: Connection Wiring
  Phase 6: Feedback Loop Setup
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Phase 1: Account Creation ──────────────────────────────────────────

class AccountCreationRequest(BaseModel):
    company_name: str
    company_website: str = ""
    company_type: str = ""
    contact_name: str
    contact_email: str
    contact_role: str = ""
    contact_phone: Optional[str] = None
    password: str
    monthly_volume_estimate: str = ""
    primary_goal: str = ""


class AccountCreationResponse(BaseModel):
    tenant_id: str
    auth_token: str
    next_step_url: str
    status: str = "onboarding"


# ── Phase 2: Platform Identification ───────────────────────────────────

class PlatformSelectionRequest(BaseModel):
    business_type: str  # user-facing label from the selection UI
    sub_goal: Optional[str] = None  # disambiguation ("targeting" vs "creative")
    blueprint_id: Optional[str] = None  # if directly selected


class PlatformSelectionResponse(BaseModel):
    blueprint_id: str
    blueprint_description: str
    phase: str = "2_complete"
    available_data_questions: List[str] = Field(default_factory=list)


# ── Phase 3: Inbound Data Specification ────────────────────────────────

class InboundDataRequest(BaseModel):
    user_signals: List[str] = Field(default_factory=list)
    signal_delivery_method: str = "realtime_api"
    signal_format: str = "json"
    has_outcome_data: bool = False
    outcome_method: Optional[str] = None
    has_creative_metadata: bool = False
    content_types: List[str] = Field(default_factory=list)
    content_access_method: Optional[str] = None
    content_access_url: Optional[str] = None
    ssp_platforms: List[str] = Field(default_factory=list)
    uses_prebid: Optional[bool] = None
    first_party_data: List[str] = Field(default_factory=list)
    amazon_products: bool = False
    brand_names: List[str] = Field(default_factory=list)
    product_names: List[str] = Field(default_factory=list)
    product_category: str = ""
    advertising_channels: List[str] = Field(default_factory=list)
    audio_content_types: List[str] = Field(default_factory=list)
    listener_behavior_data: List[str] = Field(default_factory=list)
    ad_serving_technology: str = ""
    catalog_size: str = ""


class InboundDataResponse(BaseModel):
    phase: str = "3_complete"
    intelligence_ceiling: Dict[str, float]
    available_return_types: List[Dict[str, Any]]
    recommended_type: str
    upgrade_hints: List[Dict[str, Any]]


# ── Phase 4: Intelligence Menu Selection ───────────────────────────────

class IntelligenceProduct(BaseModel):
    id: str
    name: str
    description: str
    power_level: float
    pricing: str
    recommended: bool = False
    upgrade_available: bool = False
    upgrade_hint: str = ""
    follow_up_questions: List[Dict[str, Any]] = Field(default_factory=list)


class IntelligenceSelectionRequest(BaseModel):
    selected_products: List[str]
    response_fields: List[str] = Field(default_factory=list)
    response_format: str = "json"
    delivery_method: str = "api_response"
    webhook_url: Optional[str] = None
    s3_bucket: Optional[str] = None
    product_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class IntelligenceSelectionResponse(BaseModel):
    phase: str = "4_complete"
    selected_count: int
    total_power: float
    active_pipelines: List[str]


# ── Phase 5: Connection Wiring ─────────────────────────────────────────

class ConnectionWiringRequest(BaseModel):
    connector_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    adapter_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    response_format_preferences: Dict[str, Any] = Field(default_factory=dict)


class ConnectionWiringResponse(BaseModel):
    phase: str = "5_complete"
    api_base_url: str
    api_key: str
    endpoints: Dict[str, str]
    connector_status: Dict[str, str]
    adapter_status: Dict[str, str]
    rate_limits: Dict[str, int]


# ── Phase 6: Feedback Loop Setup ──────────────────────────────────────

class FeedbackConfigRequest(BaseModel):
    outcome_events: List[str] = Field(default_factory=list)
    feedback_method: str = "realtime_postback"
    attribution_window_click_days: int = 7
    attribution_window_view_days: int = 1
    webhook_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_schedule_hours: Optional[int] = None


class FeedbackConfigResponse(BaseModel):
    phase: str = "6_complete"
    webhook_url: str
    tracking_pixel_code: str
    batch_upload_url: str
    learning_systems_activated: int
    improvement_timeline: List[Dict[str, str]]


# ── Full Tenant Configuration ──────────────────────────────────────────

class OnboardingPhase(str, Enum):
    ACCOUNT_CREATED = "1_complete"
    PLATFORM_SELECTED = "2_complete"
    INBOUND_CONFIGURED = "3_complete"
    INTELLIGENCE_SELECTED = "4_complete"
    CONNECTIONS_WIRED = "5_complete"
    FEEDBACK_CONFIGURED = "6_complete"
    ACTIVATED = "activated"


class TenantOnboardingState(BaseModel):
    """Tracks the full onboarding state for a tenant across all 6 phases."""
    tenant_id: str
    phase: OnboardingPhase = OnboardingPhase.ACCOUNT_CREATED
    company_name: str = ""
    company_website: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_role: str = ""
    primary_goal: str = ""
    monthly_volume_estimate: str = ""
    blueprint_id: Optional[str] = None
    business_type: str = ""

    # Phase 3 — stored inbound config
    inbound_data: Optional[InboundDataRequest] = None
    intelligence_ceiling: Dict[str, float] = Field(default_factory=dict)

    # Phase 4 — intelligence selections
    selected_products: List[str] = Field(default_factory=list)
    response_fields: List[str] = Field(default_factory=list)
    response_format: str = "json"
    delivery_method: str = "api_response"
    webhook_url: Optional[str] = None

    # Phase 5 — connection wiring
    connector_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    adapter_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    api_key: Optional[str] = None
    api_base_url: str = ""

    # Phase 6 — feedback loop
    feedback_config: Optional[FeedbackConfigRequest] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None


# ── Business Type → Blueprint Mapping ──────────────────────────────────

BUSINESS_TYPE_BLUEPRINT_MAP = {
    "dsp_targeting": "DSP-TGT",
    "dsp_creative": "DSP-CRE",
    "dsp_both": "DSP-TGT",
    "ssp_enrich": "PUB-ENR",
    "ssp_yield": "PUB-YLD",
    "ssp_both": "PUB-ENR",
    "publisher": "PUB-ENR",
    "audio_podcast": "AUD-LST",
    "brand_advertiser": "BRD-INT",
    "agency": "AGY-PLN",
    "ctv_streaming": "CTV-AUD",
    "retail_media": "RET-PSY",
    "ad_exchange": "EXC-DAT",
    "social_ugc": "SOC-AUD",
}

BUSINESS_TYPE_LABELS = {
    "dsp_targeting": "We buy ad inventory (DSP / Trading Desk / Media Buyer) — Targeting",
    "dsp_creative": "We buy ad inventory (DSP / Trading Desk / Media Buyer) — Creative Optimization",
    "dsp_both": "We buy ad inventory (DSP / Trading Desk / Media Buyer) — Both",
    "ssp_enrich": "We help publishers sell inventory (SSP) — Enrich Data",
    "ssp_yield": "We help publishers sell inventory (SSP) — Optimize Yield",
    "ssp_both": "We help publishers sell inventory (SSP) — Both",
    "publisher": "We publish content and sell ads (Publisher / Media)",
    "audio_podcast": "We operate a podcast or audio platform",
    "brand_advertiser": "We are a brand / advertiser",
    "agency": "We manage advertising for multiple brands (Agency)",
    "ctv_streaming": "We operate a streaming / CTV platform",
    "retail_media": "We are a retail media network",
    "ad_exchange": "We operate an ad exchange",
    "social_ugc": "We operate a social / UGC platform",
}

# ── Return Type Definitions Per Blueprint ──────────────────────────────

RETURN_TYPE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "DSP-TGT": [
        {"id": "segments", "name": "Psychological Audience Segments", "description": "14 psychological segments per ad request, delivered as segment IDs in your DSP's native format.", "base_power": 0.95, "pricing": "$0.02-0.05 CPM", "requires": ["content_url"]},
        {"id": "creative_match", "name": "Creative-Audience Match Scores", "description": "Per-creative psychological fit score (0-100) for each audience segment.", "base_power": 0.90, "pricing": "$0.01-0.03 CPM", "requires": ["creative_metadata"]},
        {"id": "mechanism_reco", "name": "Mechanism Recommendations", "description": "Per-impression recommendation of which cognitive mechanism to activate.", "base_power": 0.80, "pricing": "$0.01-0.02 CPM", "requires": []},
        {"id": "sequential_plans", "name": "Sequential Persuasion Plans", "description": "Multi-touch journey plans showing optimal message sequence per user.", "base_power": 0.75, "pricing": "$0.03-0.08 CPM", "requires": ["user_id"]},
        {"id": "contextual_fusion", "name": "Contextual x Psychological Fusion", "description": "Compound signal combining page context with user psychology.", "base_power": 0.40, "pricing": "$0.02-0.04 CPM", "requires": ["content_url"]},
    ],
    "PUB-ENR": [
        {"id": "segment_enrichment", "name": "Audience Segment Enrichment", "description": "Psychological segments pushed to your SSP via SDA/Curated Audiences. Zero impact on your stack.", "base_power": 0.92, "pricing": "$0.01-0.03 CPM", "requires": ["content_access"]},
        {"id": "content_dashboard", "name": "Content Intelligence Dashboard", "description": "Psychological profile of every article/section and which advertising mechanisms work best.", "base_power": 0.88, "pricing": "Included", "requires": ["content_access"]},
        {"id": "advertiser_match", "name": "Advertiser Match Scores", "description": "Ranked list of which advertisers are the best psychological fit for your audience.", "base_power": 0.85, "pricing": "$500/mo", "requires": ["content_access"]},
        {"id": "premium_packages", "name": "Premium Inventory Packages", "description": "Pre-built psychological deal packages for your sales team.", "base_power": 0.78, "pricing": "$1,000/mo", "requires": ["content_access"]},
        {"id": "creative_guidance", "name": "Personalized Creative Guidance", "description": "Per-impression guidance on what creative characteristics will perform best.", "base_power": 0.55, "pricing": "$0.01-0.02 CPM", "requires": ["outcome_data"]},
    ],
    "PUB-YLD": [
        {"id": "segment_enrichment", "name": "Audience Segment Enrichment", "description": "Psychological segments pushed to SSP for higher CPMs.", "base_power": 0.90, "pricing": "$0.01-0.03 CPM", "requires": ["content_access"]},
        {"id": "floor_optimization", "name": "Floor Price Optimization", "description": "Psychological attention scores drive dynamic floor prices.", "base_power": 0.85, "pricing": "Rev share", "requires": ["content_access"]},
        {"id": "demand_scoring", "name": "Demand Partner Scoring", "description": "Score demand partners per slot based on psychological match.", "base_power": 0.80, "pricing": "Included", "requires": ["content_access"]},
    ],
    "AUD-LST": [
        {"id": "listener_profiles", "name": "Listener Psychological Profiles", "description": "Personality inferred from listening behavior. No PII required.", "base_power": 0.92, "pricing": "$0.02-0.05 CPM", "requires": ["listener_behavior"]},
        {"id": "show_intelligence", "name": "Show/Station Intelligence", "description": "Per-show psychological audience composition. What personality types listen?", "base_power": 0.88, "pricing": "Included", "requires": ["content_access"]},
        {"id": "advertiser_match", "name": "Advertiser-Show Match Scores", "description": "Brand-show compatibility on psychological dimensions.", "base_power": 0.85, "pricing": "$500/mo", "requires": []},
        {"id": "host_briefing", "name": "Host-Read Brief Generation", "description": "AI briefing documents for host-read endorsements tailored to audience psychology.", "base_power": 0.82, "pricing": "$1,000/mo", "requires": ["content_access"]},
        {"id": "audio_creative", "name": "Adaptive Audio Creative Guidance", "description": "Personality-matched recommendations for audio ad characteristics.", "base_power": 0.78, "pricing": "$0.01-0.03 CPM", "requires": []},
    ],
    "DSP-CRE": [
        {"id": "creative_match", "name": "Creative-Audience Match Scores", "description": "Per-creative psychological fit score for each audience segment.", "base_power": 0.92, "pricing": "$0.01-0.03 CPM", "requires": ["creative_metadata"]},
        {"id": "variant_optimization", "name": "Variant Optimization", "description": "Multi-arm bandit testing with gradient-based creative optimization.", "base_power": 0.88, "pricing": "$0.02-0.05 CPM", "requires": ["creative_metadata", "outcome_data"]},
        {"id": "creative_generation", "name": "Creative Effectiveness Prediction", "description": "Predict which creative characteristics will perform best.", "base_power": 0.82, "pricing": "$0.01-0.03 CPM", "requires": ["creative_metadata"]},
    ],
    "BRD-INT": [
        {"id": "customer_profile", "name": "Customer Psychology Profile", "description": "Deep 441-construct NDF profile from purchase reviews. Empirically measured.", "base_power": 0.95, "pricing": "$2,000/mo", "requires": []},
        {"id": "competitive_intel", "name": "Competitive Intelligence", "description": "Your customers' psychology vs. competitors'. Psychological whitespace analysis.", "base_power": 0.88, "pricing": "$1,000/mo", "requires": []},
        {"id": "creative_variants", "name": "Personality-Matched Creative", "description": "Ad copy variants optimized for each psychological segment.", "base_power": 0.85, "pricing": "$1,500/mo", "requires": []},
        {"id": "media_planning", "name": "Media Planning Intelligence", "description": "Your brand matched to psychologically-optimal media placements.", "base_power": 0.82, "pricing": "$1,000/mo", "requires": []},
        {"id": "campaign_feed", "name": "Campaign Optimization Feed", "description": "Real-time psychological targeting signals for your DSP campaigns.", "base_power": 0.78, "pricing": "$0.02-0.05 CPM", "requires": ["outcome_data"]},
    ],
    "AGY-PLN": [
        {"id": "multi_brand_dashboard", "name": "Multi-Brand Campaign Intelligence", "description": "Cross-client psychological performance analytics.", "base_power": 0.90, "pricing": "$5,000/mo", "requires": []},
        {"id": "product_inventory_match", "name": "Product-to-Inventory Match", "description": "Upload product feed — ADAM matches each to psychologically-optimal inventory.", "base_power": 0.88, "pricing": "$3,000/mo", "requires": []},
        {"id": "sequential_orchestration", "name": "Sequential Persuasion Orchestration", "description": "Multi-touch journey campaigns with psychological state awareness.", "base_power": 0.85, "pricing": "$0.05-0.10 CPM", "requires": ["outcome_data"]},
        {"id": "supply_path", "name": "Supply-Path Optimization", "description": "Graph-powered optimal path factoring psychological match quality.", "base_power": 0.82, "pricing": "Included", "requires": []},
        {"id": "creative_effectiveness", "name": "Creative Effectiveness Intelligence", "description": "Why specific creative works for specific audience segments.", "base_power": 0.78, "pricing": "$1,000/mo", "requires": ["creative_metadata"]},
    ],
    "CTV-AUD": [
        {"id": "household_profiles", "name": "Household Psychological Profiles", "description": "Household-level psychology from viewing patterns.", "base_power": 0.88, "pricing": "$0.03-0.08 CPM", "requires": []},
        {"id": "content_intelligence", "name": "Content Moment Intelligence", "description": "Psychological profile of content moments for ad placement.", "base_power": 0.85, "pricing": "$0.02-0.05 CPM", "requires": ["content_access"]},
        {"id": "advertiser_match", "name": "Advertiser Match Scores", "description": "Brand-content compatibility on psychological dimensions.", "base_power": 0.82, "pricing": "$500/mo", "requires": []},
    ],
    "RET-PSY": [
        {"id": "purchase_psychology", "name": "Purchase Psychology Models", "description": "80-construct product NDF + purchase decision psychology.", "base_power": 0.92, "pricing": "$0.02-0.05 CPM", "requires": []},
        {"id": "shopper_profiles", "name": "Shopper Psychological Profiles", "description": "Why they buy, not just what they buy.", "base_power": 0.88, "pricing": "$0.01-0.03 CPM", "requires": []},
        {"id": "mechanism_targeting", "name": "Mechanism Targeting", "description": "Which persuasion mechanisms drive conversion for each product.", "base_power": 0.85, "pricing": "$0.01-0.02 CPM", "requires": []},
    ],
    "SOC-AUD": [
        {"id": "engagement_prediction", "name": "Psychological Engagement Prediction", "description": "Predict engagement from NDF profiles.", "base_power": 0.85, "pricing": "$0.02-0.05 CPM", "requires": []},
        {"id": "creator_match", "name": "Creator-Brand Matching", "description": "Match brands to creators on psychological dimensions.", "base_power": 0.82, "pricing": "$1,000/mo", "requires": []},
        {"id": "social_creative", "name": "Social Creative Guidance", "description": "Platform-specific creative guidance from psychology.", "base_power": 0.78, "pricing": "$0.01-0.03 CPM", "requires": []},
    ],
    "EXC-DAT": [
        {"id": "quality_scoring", "name": "Psychological Quality Scores", "description": "Per-impression psychological quality score for premium tier creation.", "base_power": 0.88, "pricing": "$0.01-0.02 CPM", "requires": []},
        {"id": "segment_syndication", "name": "Segment Syndication", "description": "NDF segments syndicated to marketplace buyers.", "base_power": 0.85, "pricing": "$0.005-0.01 CPM", "requires": []},
    ],
}
