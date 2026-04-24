"""Domain list models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    domain: str = Field(..., max_length=255)
    list_type: str = Field(..., pattern="^(whitelist|blacklist)$")
    audience: Optional[str] = None
    tier: int = Field(default=2, ge=1, le=3)
    source: str = Field(default="manual")


class DomainBulkCreate(BaseModel):
    domains: List[str]
    list_type: str = Field(..., pattern="^(whitelist|blacklist)$")
    tier: int = Field(default=2, ge=1, le=3)


class DomainResponse(BaseModel):
    id: str
    campaign_archetype_id: Optional[str] = None
    campaign_id: Optional[str] = None
    list_type: str
    domain: str
    audience: Optional[str] = None
    tier: int = 2
    source: str = "manual"
    added_by: Optional[str] = None
    added_at: str
