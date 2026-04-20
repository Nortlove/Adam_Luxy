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
    channel_type: Optional[str] = None
    group_name: Optional[str] = None
    status: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend_usd: float = 0.0
    ctr: float = 0.0
    cpa_usd: Optional[float] = None
    roas: Optional[float] = None


class StackAdaptSource(BaseModel):
    source: Literal["live", "unavailable"]
    reason: Optional[str] = None
    advertiser_name: Optional[str] = None


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignSummary]
    total: int
    stackadapt: StackAdaptSource


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
# Dialogue Ledger — Deviations + Calibration
# =============================================================================


AdjudicationStatus = Literal["pending", "testing", "adjudicated"]
AdjudicationOutcome = Literal["user_right", "system_right", "indeterminate"]


class DeviationSummary(BaseModel):
    id: str
    user_id: str
    recommendation_id: str
    system_choice: str
    user_choice: Optional[str] = None
    stated_rationale: Optional[str] = None
    rationale_class: Optional[Literal["idiosyncratic", "missing_context", "model_wrong"]] = None
    adjudication_status: AdjudicationStatus
    adjudication_outcome: Optional[AdjudicationOutcome] = None
    horizon_class: Literal["hours", "days", "weeks", "months"]
    created_at: datetime


class DeviationListResponse(BaseModel):
    deviations: list[DeviationSummary]
    total: int


class DomainCalibration(BaseModel):
    """Per-domain summary of a user's claim activity.

    Brier score is only meaningful once claims have been adjudicated
    against outcomes — for v1 we report activity counts and
    recallability breakdown so the UI can start surfacing the user's
    elicitation profile even before outcomes land.
    """

    domain: str
    total_claims: int
    fluent_recall_count: int
    hesitant_recall_count: int
    absent_recall_count: int
    avg_latency_ms: Optional[float] = None
    validated_count: int = 0
    brier_score: Optional[float] = None


class CalibrationResponse(BaseModel):
    domains: list[DomainCalibration]
    source: Literal["live", "unavailable"]
    source_note: Optional[str] = None


# =============================================================================
# Analytics (skeleton)
# =============================================================================


# =============================================================================
# Recommendations + Uncertainty Panel
# =============================================================================


RecommendationType = Literal[
    "creative_rotate",
    "mechanism_shift",
    "budget_shift",
    "pause_campaign",
    "resume_campaign",
    "archetype_reweight",
    "audience_expand",
    "other",
]


RecommendationStatus = Literal[
    "pending",
    "accepted",
    "modified",
    "rejected",
    "expired",
]


HorizonClass = Literal["hours", "days", "weeks", "months"]


DecisionKind = Literal["accept", "modify", "reject"]


RationaleClass = Literal["idiosyncratic", "missing_context", "model_wrong"]


class RecommendationAlternative(BaseModel):
    id: str
    label: str
    description: str
    predicted_outcome: Optional[str] = None


class ConfidentClaim(BaseModel):
    claim: str
    sources: list[str] = Field(default_factory=list)
    strength: float = Field(ge=0.0, le=1.0)


class UncertainClaim(BaseModel):
    claim: str
    missing: str
    would_reduce: Optional[str] = None


class PossiblyWrongClaim(BaseModel):
    claim: str
    conflicting_signal: str
    alternative: Optional[str] = None


class UncertaintyBreakdown(BaseModel):
    """The Confident / Uncertain / Possibly-Wrong decomposition required
    on every AI recommendation per HMT Foundation §7.1."""

    confident: list[ConfidentClaim] = Field(default_factory=list)
    uncertain: list[UncertainClaim] = Field(default_factory=list)
    possibly_wrong: list[PossiblyWrongClaim] = Field(default_factory=list)


class UserDecisionRequest(BaseModel):
    kind: DecisionKind
    chosen_alternative: Optional[str] = None
    rationale_class: Optional[RationaleClass] = None
    rationale_text: Optional[str] = Field(default=None, max_length=4000)


class UserDecisionResponse(BaseModel):
    id: str
    user_id: str
    recommendation_id: str
    kind: DecisionKind
    chosen_alternative: Optional[str] = None
    rationale_class: Optional[RationaleClass] = None
    rationale_text: Optional[str] = None
    claim_id: Optional[str] = None
    created_at: datetime


class RecommendationSummary(BaseModel):
    id: str
    type: RecommendationType
    title: str
    summary: str
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    preferred_choice: str
    expected_horizon_class: HorizonClass
    status: RecommendationStatus
    created_at: datetime


class RecommendationDetail(RecommendationSummary):
    alternatives: list[RecommendationAlternative]
    evidence: UncertaintyBreakdown
    decisions: list[UserDecisionResponse] = Field(default_factory=list)


class RecommendationListResponse(BaseModel):
    recommendations: list[RecommendationSummary]
    total: int
    source: Literal["live", "synthetic", "unavailable"]
    source_note: Optional[str] = None


# =============================================================================
# Analytics
# =============================================================================


class AnalyticsSummary(BaseModel):
    campaigns_total: int
    campaigns_live: int
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_spend_usd: float
    overall_ctr: float
    overall_cpa_usd: Optional[float] = None
    overall_roas: Optional[float] = None
    active_archetypes: int
    edges_in_graph: int
    advertiser_name: Optional[str] = None
    stackadapt_source: Literal["live", "unavailable"]
    stackadapt_reason: Optional[str] = None
    graph_source: Literal["live", "unavailable"]
    last_updated: datetime
