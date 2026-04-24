"""Conversion tracker models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TrackerCreate(BaseModel):
    tracker_type: str = Field(..., pattern="^(universal_pixel|s2s_postback|both)$")
    pixel_id: Optional[str] = None


class TrackerResponse(BaseModel):
    id: str
    campaign_id: str
    tracker_type: str
    pixel_id: Optional[str] = None
    pixel_snippet: Optional[str] = None
    postback_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    is_verified: bool = False
    verified_at: Optional[str] = None
    events_received: int = 0
    last_event_at: Optional[str] = None
    created_at: str
