"""Creative variant models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreativeCreate(BaseModel):
    variant_label: str = Field(..., max_length=100)
    mechanism: str = Field(..., max_length=100)
    headline: str
    body_copy: Optional[str] = None
    cta_text: Optional[str] = Field(default=None, max_length=200)
    image_url: Optional[str] = None
    landing_url: Optional[str] = None
    tone: Optional[str] = None
    construal_level: Optional[str] = Field(default=None, pattern="^(concrete|abstract)$")


class CreativeUpdate(BaseModel):
    variant_label: Optional[str] = None
    mechanism: Optional[str] = None
    headline: Optional[str] = None
    body_copy: Optional[str] = None
    cta_text: Optional[str] = None
    image_url: Optional[str] = None
    landing_url: Optional[str] = None
    tone: Optional[str] = None
    construal_level: Optional[str] = None
    status: Optional[str] = None


class CreativeResponse(BaseModel):
    id: str
    campaign_archetype_id: str
    variant_label: str
    mechanism: str
    headline: str
    body_copy: Optional[str] = None
    cta_text: Optional[str] = None
    image_url: Optional[str] = None
    landing_url: Optional[str] = None
    tone: Optional[str] = None
    construal_level: Optional[str] = None
    status: str = "draft"
    dsp_creative_id: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0
    ctr: float = 0
    cvr: float = 0
    cpa: float = 0
    created_at: str
    updated_at: str
