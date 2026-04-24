"""Campaign archetype models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArchetypeCreate(BaseModel):
    archetype_name: str = Field(..., max_length=100)
    is_custom: bool = False
    budget_weight: float = Field(default=0.0, ge=0, le=1)
    primary_mechanism: Optional[str] = None
    secondary_mechanism: Optional[str] = None
    framing: str = Field(default="gain", pattern="^(gain|loss)$")
    notes: Optional[str] = None


class ArchetypeUpdate(BaseModel):
    budget_weight: Optional[float] = None
    primary_mechanism: Optional[str] = None
    secondary_mechanism: Optional[str] = None
    framing: Optional[str] = None
    notes: Optional[str] = None


class ArchetypeResponse(BaseModel):
    id: str
    campaign_id: str
    archetype_name: str
    is_custom: bool = False
    budget_weight: float = 0.0
    primary_mechanism: Optional[str] = None
    secondary_mechanism: Optional[str] = None
    framing: str = "gain"
    notes: Optional[str] = None
    dsp_campaign_id: Optional[str] = None
    dsp_campaign_status: Optional[str] = None
    created_at: str
    updated_at: str
    creative_count: int = 0
    domain_count: int = 0


class ArchetypeIntelligence(BaseModel):
    archetype_name: str
    mechanism_scores: Dict[str, float] = {}
    recommended_mechanism: str = ""
    recommended_framing: str = ""
    bilateral_evidence_count: int = 0
    confidence: float = 0.0
    suggested_domains: List[str] = []
