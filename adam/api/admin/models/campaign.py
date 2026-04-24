"""Campaign models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


CAMPAIGN_STATUSES = ["draft", "configured", "review", "active", "paused", "completed", "archived"]
VALID_TRANSITIONS = {
    "draft": ["configured"],
    "configured": ["review", "draft"],
    "review": ["active", "configured"],
    "active": ["paused", "completed"],
    "paused": ["active", "completed"],
    "completed": ["archived"],
    "archived": [],
}


class CampaignCreate(BaseModel):
    organization_id: str
    name: str = Field(..., max_length=255)
    brand_name: str = Field(..., max_length=255)
    brand_asin: Optional[str] = None
    brand_website: Optional[str] = None
    brand_category: Optional[str] = None
    brand_logo_url: Optional[str] = None
    notes: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    brand_name: Optional[str] = None
    brand_asin: Optional[str] = None
    brand_website: Optional[str] = None
    brand_category: Optional[str] = None
    brand_logo_url: Optional[str] = None
    total_budget: Optional[float] = None
    daily_budget: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timezone: Optional[str] = None
    geo_targets: Optional[List[Dict[str, Any]]] = None
    frequency_cap: Optional[Dict[str, Any]] = None
    dayparting: Optional[Dict[str, Any]] = None
    dsp_platform: Optional[str] = None
    dsp_advertiser_id: Optional[str] = None
    dsp_api_key: Optional[str] = None
    dcil_enabled: Optional[bool] = None
    dcil_auto_execute: Optional[bool] = None
    dcil_safety_rails: Optional[Dict[str, Any]] = None
    tier_a_frequency: Optional[str] = None
    conversion_pixel_id: Optional[str] = None
    conversion_type: Optional[str] = None
    conversion_value: Optional[float] = None
    attribution_window_days: Optional[int] = None
    notes: Optional[str] = None


class CampaignResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    status: str
    brand_name: str
    brand_asin: Optional[str] = None
    brand_website: Optional[str] = None
    brand_category: Optional[str] = None
    brand_logo_url: Optional[str] = None
    total_budget: Optional[float] = None
    daily_budget: Optional[float] = None
    currency: str = "USD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timezone: str = "America/New_York"
    geo_targets: List[Dict[str, Any]] = []
    frequency_cap: Dict[str, Any] = {}
    dayparting: Dict[str, Any] = {}
    dsp_platform: str = "stackadapt"
    dsp_advertiser_id: Optional[str] = None
    dcil_enabled: bool = True
    dcil_auto_execute: bool = False
    dcil_safety_rails: Dict[str, Any] = {}
    tier_a_frequency: str = "adaptive"
    conversion_pixel_id: Optional[str] = None
    conversion_type: str = "purchase"
    conversion_value: Optional[float] = None
    attribution_window_days: int = 30
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    archetype_count: int = 0
    creative_count: int = 0


class CampaignList(BaseModel):
    campaigns: List[CampaignResponse]
    total: int
    page: int = 1
    per_page: int = 20


class CampaignPerformance(BaseModel):
    campaign_id: str
    snapshot_date: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0
    revenue: float = 0
    ctr: float = 0
    cvr: float = 0
    cpa: float = 0
    roas: float = 0
    archetype_breakdown: Dict[str, Any] = {}
    domain_breakdown: Dict[str, Any] = {}
