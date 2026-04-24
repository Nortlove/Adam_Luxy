"""Organization models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100, pattern="^[a-z0-9-]+$")
    domain: Optional[str] = None
    industry: Optional[str] = None
    tier: str = Field(default="standard", pattern="^(standard|premium|enterprise)$")


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    settings_json: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    tier: str
    status: str
    settings_json: Dict[str, Any] = {}
    created_at: str
    updated_at: str
    campaign_count: int = 0
    user_count: int = 0


class OrganizationList(BaseModel):
    organizations: List[OrganizationResponse]
    total: int
    page: int = 1
    per_page: int = 20
