"""Pydantic models for the HMT dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Identity
# =============================================================================


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str


# =============================================================================
# Health
# =============================================================================


class DashboardHealthResponse(BaseModel):
    status: Literal["ok"]
    neo4j_connected: bool


# =============================================================================
# Campaigns (skeleton — wired to real data in follow-up task)
# =============================================================================


class CampaignSummary(BaseModel):
    id: str
    name: str
    brand: str
    status: Literal["draft", "live", "paused", "completed"]
    spent_usd: Optional[float] = None
    cpa_usd: Optional[float] = None
    archetype_count: Optional[int] = None
    created_at: Optional[datetime] = None


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignSummary]
    total: int


# =============================================================================
# Dialogue Ledger
# =============================================================================


ElicitationMode = Literal[
    "forced_pair",
    "timed_pair",
    "k_afc",
    "rank_order",
    "story",
    "counter_example",
    "recallability",
    "scenario",
    "spies",
    "four_point",
    "freeform",
]


ClaimStatus = Literal[
    "hypothesis",  # always starts here
    "captured",
    "instrumented",
    "testing",
    "validated_user_right",
    "validated_system_right",
    "indeterminate",
    "retired",
]


Frame = Literal["gain", "loss", "neutral"]


Recallability = Literal["fluent", "hesitant", "absent"]


class ClaimCreateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    elicitation_mode: ElicitationMode
    domain: str = Field(..., min_length=1)
    stated_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="User-reported confidence, 0..1",
    )
    latency_ms: Optional[int] = Field(
        default=None, ge=0,
        description="Response latency in milliseconds",
    )
    frame: Frame = "neutral"
    session_id: Optional[str] = None
    mood_index: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0,
        description="Session-start mood probe, -1..1",
    )
    recallability: Optional[Recallability] = None


class ClaimResponse(BaseModel):
    id: str
    user_id: str
    text: str
    elicitation_mode: ElicitationMode
    domain: str
    stated_confidence: Optional[float]
    latency_ms: Optional[int]
    frame: Frame
    status: ClaimStatus
    recallability: Optional[Recallability]
    created_at: datetime


class ClaimListResponse(BaseModel):
    claims: list[ClaimResponse]
    total: int


# =============================================================================
# Analytics (skeleton)
# =============================================================================


class AnalyticsSummary(BaseModel):
    campaigns_live: int
    total_spend_usd: float
    average_cpa_usd: Optional[float] = None
    active_archetypes: int
    edges_in_graph: int
    last_updated: datetime
