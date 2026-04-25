"""Pydantic models for the HMT dashboard API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

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
# Mechanism effectiveness (Front-end A — learning surface)
#
# Renders what Enhancement #33's 5-level hierarchical retargeting learning is
# accumulating. Shows, per (archetype, barrier) cell: the Beta posterior on
# every therapeutic mechanism — mean efficacy, credible-interval width, and
# the sample count backing each estimate. This is the scientific substance
# of the pilot: proof that the system is learning per person, not guessing
# from static priors.
# =============================================================================


class MechanismPosterior(BaseModel):
    """Beta posterior on a (mechanism | barrier, archetype) cell.

    mean = alpha / (alpha + beta) is the current best estimate of resolution
    probability. confidence grows with sample_count; at low N the posterior
    is wide and the UI should render the uncertainty, not the point estimate.
    """
    mean: float
    alpha: float
    beta: float
    sample_count: int
    confidence: float


class MechanismEffectivenessResponse(BaseModel):
    global_stats: Dict[str, Any] = Field(default_factory=dict)
    posteriors: Optional[Dict[str, MechanismPosterior]] = None
    barrier_prevalence: Optional[Dict[str, float]] = None
    archetype_id: Optional[str] = None
    barrier: Optional[str] = None


# =============================================================================
# Client Report (Front-end A)
#
# Report-style payload for the advertiser-facing surface. Strict rule: NO
# internal taxonomy, NO posterior numerics, NO methodology reveal. Every
# entity referenced is translated through the PublicLabelService before
# it reaches this response. See adam/api/dashboard/client_report_service.py
# for the composer and the strategic rationale.
# =============================================================================


class ClientSegmentHighlight(BaseModel):
    """Outcome-framed observation about one customer segment. The
    segment_label here is a PublicLabel — never an internal archetype slug."""
    segment_label: str
    observation: str


class ClientMessageObservation(BaseModel):
    """A single message-style observation sentence — composed from
    labels + outcomes, never the underlying mechanism name."""
    observation: str


class ClientRecommendation(BaseModel):
    """Active recommendation with natural-language rationale.

    Rationale is plain English composed from public labels and outcome
    framing. No posterior values, no mechanism/archetype/barrier slugs,
    no confidence decimals.
    """
    id: str
    headline: str
    rationale: str
    projected_impact: Optional[str] = None
    confirm_label: str
    requires_acknowledgment: bool
    status: Literal["pending", "acknowledged", "declined"] = "pending"


# =============================================================================
# System Convergence (Front-end B — internal superadmin surface)
#
# Cross-archetype roll-up of the retargeting learning state. Lets the
# operator see which (archetype, barrier, mechanism) cells the system
# has accumulated real evidence for, which are still noisy, and which
# patterns recur across multiple archetypes (platform-level signal).
#
# Internal only — never rendered on client surfaces. The cells here
# reference the raw internal taxonomy (archetype slugs, barrier names,
# mechanism names, posterior numerics) deliberately — that is the point
# of Front-end B.
# =============================================================================


class ConvergedCell(BaseModel):
    """One (archetype, barrier, mechanism) cell with accumulated evidence."""
    archetype: str
    barrier: str
    mechanism: str
    mean: float
    sample_count: int
    confidence: float
    alpha: float
    beta: float
    # Rank score used for ordering: mean * confidence. Computed server-
    # side so the render doesn't re-derive and the ordering is stable.
    rank_score: float


class CrossArchetypePattern(BaseModel):
    """A mechanism that wins across multiple archetypes — platform-level
    signal worth treating as a stronger prior for novel campaigns."""
    mechanism: str
    archetypes: list[str]
    barrier: Optional[str] = None
    mean_across_archetypes: float
    total_sample_count: int


class NovelFinding(BaseModel):
    """A cell where evidence is accumulating but confidence is still
    below the threshold for treating as a validated prior. Flagged so
    the operator can decide whether to push more impressions through
    it or suppress it."""
    archetype: str
    barrier: str
    mechanism: str
    mean: float
    sample_count: int
    confidence: float
    note: str  # short description of why this is flagged


class AdvertiserSummary(BaseModel):
    """Per-advertiser roll-up. Pilot is single-tenant (LUXY); multi-
    tenant breakdown arrives with Phase C shell."""
    advertiser_id: str
    advertiser_name: Optional[str]
    total_cells_with_evidence: int
    top_converged_cell_count: int
    total_observations: int


class SystemConvergenceResponse(BaseModel):
    # Converged cells: mean*confidence > threshold AND sample_count >= floor.
    # These are the system's "we know this works" entries.
    top_converged: list[ConvergedCell] = Field(default_factory=list)
    # Novel findings: accumulating but not yet validated.
    novel_findings: list[NovelFinding] = Field(default_factory=list)
    # Cross-archetype patterns: same mechanism winning across ≥2 archetypes.
    cross_archetype_patterns: list[CrossArchetypePattern] = Field(
        default_factory=list,
    )
    advertisers: list[AdvertiserSummary] = Field(default_factory=list)
    # Total cells examined (diagnostic — operator sees coverage vs signal).
    cells_examined: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClientDecisionAuditEntry(BaseModel):
    """One row in the internal client-decisions audit view. Connects a
    Front-end A acknowledge/decline event to its adjudication state."""
    decision_id: str
    decision_kind: Literal["acknowledge", "decline"]
    decided_at: datetime
    latency_ms: Optional[int] = None
    feedback_text: Optional[str] = None
    rec_id: str
    rec_headline: str
    advertiser_id: Optional[str] = None
    deviation_id: Optional[str] = None
    adjudication_status: Optional[str] = None  # "pending" | "adjudicated"
    adjudication_outcome: Optional[str] = None  # "user_right" | "system_right" | "indeterminate"
    outcome_observation: Optional[str] = None  # json-encoded observation from adjudicator


class ClientDecisionAuditSummary(BaseModel):
    total_decisions: int
    acknowledge_count: int
    decline_count: int
    declines_with_feedback: int
    pending_adjudication: int
    adjudicated_system_right: int
    adjudicated_user_right: int
    adjudicated_indeterminate: int
    acceptance_rate: float


class ClientDecisionAuditResponse(BaseModel):
    summary: ClientDecisionAuditSummary
    entries: list[ClientDecisionAuditEntry] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClientRecommendationDecisionRequest(BaseModel):
    """Client acknowledges (accepts) or declines a recommendation.

    The client sends a snapshot of what they saw — headline, rationale,
    confirm_label — so we can persist an audit trail even though the
    rec was generated on-the-fly by the report composer and doesn't
    exist in the graph until the decision is made (persist-on-decide).
    """
    kind: Literal["acknowledge", "decline"]
    advertiser_id: str
    headline: str
    rationale: str
    confirm_label: str
    projected_impact: Optional[str] = None
    feedback_text: Optional[str] = Field(
        None,
        description="Optional client-supplied reason when declining.",
    )
    latency_ms: Optional[int] = Field(
        None,
        description=(
            "How long the client took to decide, in milliseconds. Signal "
            "for Type-1 vs Type-2 processing on the decision — captured "
            "for learning-loop calibration."
        ),
    )


class ClientRecommendationDecisionResponse(BaseModel):
    id: str
    recommendation_id: str
    kind: Literal["acknowledge", "decline"]
    created_at: datetime
    claim_id: Optional[str] = None
    deviation_id: Optional[str] = None


class ClientReportResponse(BaseModel):
    advertiser_id: str
    advertiser_name: Optional[str] = None
    period_start: Optional[str] = None
    period_end: str
    generated_at: datetime

    impressions: int
    clicks: int
    conversions: int
    spend_usd: float
    ctr: float
    cpa_usd: Optional[float] = None
    roas: Optional[float] = None
    campaigns_live: int
    campaigns_total: int

    segment_highlights: list[ClientSegmentHighlight] = Field(default_factory=list)
    message_observations: list[ClientMessageObservation] = Field(default_factory=list)
    recommendations: list[ClientRecommendation] = Field(default_factory=list)

    data_source_notes: list[str] = Field(default_factory=list)

    # Internal-only diagnostic — NOT rendered on the client surface.
    # Populated when a PublicLabel is missing; signals the internal team
    # to author a label. The route returns this field in responses only
    # to internal-role callers; the client renderer must ignore it.
    missing_labels: list[str] = Field(default_factory=list)


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
# Autopilot settings (five-mode trust curve)
# =============================================================================


AutopilotMode = Literal[
    "observer",
    "explain",
    "notify",
    "delegate",
    "autopilot",
]

GateKind = Literal["approve", "notify", "auto"]


class AutopilotSettings(BaseModel):
    """Per-decision-class gating for the five autopilot modes.

    Each gate determines how ADAM handles that kind of decision:
      approve: user must accept before ADAM acts
      notify : ADAM acts autonomously but surfaces the action
      auto   : ADAM acts silently (kill_switch is never "auto")
    """

    user_id: str
    mode: AutopilotMode
    creative_gate: GateKind
    bid_gate: GateKind
    audience_gate: GateKind
    budget_gate: GateKind
    kill_gate: GateKind  # intentionally never "auto"
    campaigns_at_current_mode: int = 0
    successful_at_current_mode: int = 0
    last_graduated_at: Optional[datetime] = None
    updated_at: datetime


class AutopilotUpdateRequest(BaseModel):
    mode: AutopilotMode
    creative_gate: Optional[GateKind] = None
    bid_gate: Optional[GateKind] = None
    audience_gate: Optional[GateKind] = None
    budget_gate: Optional[GateKind] = None
    kill_gate: Optional[GateKind] = None


# =============================================================================
# Decay adjudicator report (Task 33)
# =============================================================================


DecayAction = Literal["continue", "restart", "abandon", "monitor"]


class CampaignDecayClassification(BaseModel):
    campaign_id: str
    campaign_name: str
    total_users: int = 0
    continue_count: int = 0
    restart_count: int = 0
    abandon_count: int = 0
    zero_data_count: int = 0
    advertiser_avg_cpa: Optional[float] = None
    campaign_cpa: Optional[float] = None
    flags: list[str] = Field(default_factory=list)
    recommended_action: DecayAction
    rationale: str


class DecayReport(BaseModel):
    run_id: str
    run_date: datetime
    task_version: str
    campaigns: list[CampaignDecayClassification]
    total_users_classified: int
    overall_abandon_rate: float
    source: Literal["live", "unavailable"]
    source_note: Optional[str] = None


# =============================================================================
# Multi-horizon adjudication view
# =============================================================================


HorizonStatus = Literal["too_early", "ready", "in_progress", "adjudicated"]


class DeviationHorizon(BaseModel):
    """Horizon progress for a single Deviation.

    The `ready` status means the horizon_class window has elapsed but
    the causal-adjudication has not yet run. `too_early` means the
    horizon is still in the future.
    """

    deviation_id: str
    recommendation_id: str
    horizon_class: Literal["hours", "days", "weeks", "months"]
    created_at: datetime
    horizon_ends_at: datetime
    days_elapsed: float
    days_remaining: float
    status: HorizonStatus
    adjudication_outcome: Optional[AdjudicationOutcome] = None


class DeviationHorizonResponse(BaseModel):
    horizons: list[DeviationHorizon]
    total: int
    ready_count: int


# =============================================================================
# Causal Adjudicator + Why Library
# =============================================================================


class AdjudicationResultModel(BaseModel):
    deviation_id: str
    recommendation_id: str
    outcome: AdjudicationOutcome
    rationale: str
    why_library_entry_id: Optional[str] = None
    metric_observed: Optional[str] = None
    metric_value_before: Optional[float] = None
    metric_value_after: Optional[float] = None


class AdjudicationBatchResponse(BaseModel):
    adjudicated: list[AdjudicationResultModel]
    skipped_too_early: int
    skipped_no_data: int
    skipped_already_done: int


class WhyLibraryEntry(BaseModel):
    id: str
    trigger_pattern: str
    bias_class: str
    evidence_strength: float
    scope: Literal["user", "brand", "category", "platform"]
    scope_id: Optional[str] = None
    countermeasure: str
    supporting_deviation_ids: list[str] = Field(default_factory=list)
    warning_posterior_mean: float
    warning_posterior_observations: int
    created_at: datetime
    last_validated_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None


class WhyLibraryResponse(BaseModel):
    entries: list[WhyLibraryEntry]
    total: int


# =============================================================================
# Multi-tenant shell (Partner / Advertiser / Workspace)
# =============================================================================


TenantStatus = Literal["active", "paused", "suspended", "archived"]

PartnerKind = Literal["superadmin", "agency", "independent", "direct_brand"]


class TenantWorkspace(BaseModel):
    id: str
    advertiser_id: str
    name: str
    purpose: Optional[str] = None
    status: TenantStatus
    created_at: datetime


class TenantAdvertiser(BaseModel):
    id: str
    partner_id: str
    name: str
    category: Optional[str] = None
    stackadapt_advertiser_id: Optional[str] = None
    status: TenantStatus
    created_at: datetime
    workspaces: list[TenantWorkspace] = Field(default_factory=list)


class TenantPartner(BaseModel):
    id: str
    name: str
    kind: PartnerKind
    white_label_name: Optional[str] = None
    billing_email: Optional[str] = None
    status: TenantStatus
    created_at: datetime
    advertisers: list[TenantAdvertiser] = Field(default_factory=list)


class TenantHierarchyResponse(BaseModel):
    partners: list[TenantPartner]
    total_partners: int
    total_advertisers: int
    total_workspaces: int


class UserMembership(BaseModel):
    user_id: str
    role: Literal["superadmin", "partner_admin", "advertiser_admin", "viewer"]
    partner: Optional[TenantPartner] = None
    advertiser: Optional[TenantAdvertiser] = None


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


# RecommendationSource is the discriminator that lets the decide handler route to
# the correct backend write path and lets the UI prioritize the queue. The four
# sources have very different epistemic standing:
#
#   "dcil"                  — DCIL directive from inferential / theory-grounded
#                             path. Authoritative. Carries i², expected_lift_pct,
#                             rollback conditions. Decide routes to the admin
#                             directive approve/block endpoint so the directive
#                             lifecycle in dcil_directives is preserved.
#   "horizon_adjudication"  — Loop B horizon expired: an operator-deviated
#                             recommendation has reached its horizon window
#                             and is ready to adjudicate (system_right /
#                             user_right / indeterminate). Decide routes to
#                             the causal adjudicator. Closes the operator-
#                             deviation theory-update loop.
#   "chain_attribution"     — Loop A FAILING cell with a negative `unexplained`
#                             residual on the horizon-adjudicated rec-class.
#                             Reserved for when the Loop A horizon adjudicator
#                             pipeline lights up post-pilot; not produced today.
#   "threshold"             — Correlational A1 fallback (CPA / CTR / zero-conv
#                             generators) tracked under
#                             THRESHOLD_GENERATORS_AS_FALLBACK in the A14
#                             registry. Retired when DCIL achieves ≥1 directive
#                             per active campaign per week sustained.
RecommendationSource = Literal[
    "dcil", "horizon_adjudication", "chain_attribution", "threshold",
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
    # Source defaults to "threshold" for backward-compatibility with the
    # existing rule-based generators; the DCIL path explicitly sets "dcil".
    # The list view uses this to render priority order and route the decide
    # action.
    source: RecommendationSource = "threshold"


class DeviationContext(BaseModel):
    """Structural state of the deviation underlying a horizon adjudication.

    Surfaced first-class on RecommendationDetail (not derived from claim
    strings) so the UI can render the operator's task — judging an
    existing deviation — as the structural state it actually is. The
    operator sees what they chose, what the system chose, how long
    has elapsed, and the rationale they recorded at the time. No
    interpretation composed by the rendering layer.
    """

    deviation_id: str
    system_choice: str
    user_choice: Optional[str] = None
    days_elapsed: float
    horizon_window_days: float
    horizon_class: str
    stated_rationale: Optional[str] = None
    rationale_class: Optional[str] = None


class RecommendationDetail(RecommendationSummary):
    alternatives: list[RecommendationAlternative]
    evidence: UncertaintyBreakdown
    decisions: list[UserDecisionResponse] = Field(default_factory=list)

    # Structural fields populated for source="dcil". Optional so threshold
    # generators don't have to fabricate them. These are NOT redundant with
    # the evidence panel — they are the raw structural state that the
    # evidence panel surfaces derived views of, kept first-class so the UI
    # can render them without parsing claim strings.
    directive_id: Optional[str] = None
    parameter: Optional[str] = None
    current_value: Any = None
    proposed_value: Any = None
    i_squared: Optional[float] = None
    expected_lift_pct: Optional[float] = None
    generator_confidence: Optional[float] = None
    rollback_conditions: list[str] = Field(default_factory=list)

    # Upstream-authored narrative carried forward unchanged. Surfaced to the
    # operator with explicit attribution ("directive narrative — generator-
    # authored") so it is not mistaken for a derived view of atom state.
    # The directive generator's flattening of structured evidence into
    # English strings is upstream A4 drift to retire post-pilot at the
    # source (`adam/intelligence/campaign_intelligence/directive_generator.py`),
    # not here. We carry it through honestly rather than papering over.
    directive_rationale: Optional[str] = None
    directive_bilateral_evidence: Optional[str] = None

    # Populated for source="horizon_adjudication". Carries the structural
    # state of the deviation the operator is judging. UI renders a
    # DeviationContext panel from this field for horizon recs (slice D3),
    # the same way DirectiveSubstance renders directive structural fields
    # for DCIL recs.
    deviation_context: Optional[DeviationContext] = None


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
