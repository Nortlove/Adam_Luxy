"""Dashboard API Router — HMT co-pilot (single-tenant pilot).

Endpoints:
    GET  /api/dashboard/health
    GET  /api/dashboard/me
    GET  /api/dashboard/campaigns
    GET  /api/dashboard/analytics/summary
    POST /api/dashboard/ledger/claims
    GET  /api/dashboard/ledger/claims

See ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md for the full architecture.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from adam.api.dashboard.auth import DashboardUser, require_user
from adam.api.dashboard.models import (
    AdjudicationBatchResponse,
    AdjudicationResultModel,
    AnalyticsSummary,
    AutopilotSettings,
    AutopilotUpdateRequest,
    CalibrationResponse,
    CampaignDecayClassification,
    CampaignListResponse,
    CampaignSummary,
    ClaimCreateRequest,
    ClaimListResponse,
    ClaimResponse,
    CurrentUserResponse,
    DashboardHealthResponse,
    DecayReport,
    DeviationHorizon,
    DeviationHorizonResponse,
    DeviationListResponse,
    DeviationSummary,
    ClientDecisionAuditResponse,
    ClientMessageObservation,
    ClientRecommendation,
    ClientRecommendationDecisionRequest,
    ClientRecommendationDecisionResponse,
    ClientReportResponse,
    ClientSegmentHighlight,
    DomainCalibration,
    SystemConvergenceResponse,
    MechanismEffectivenessResponse,
    MechanismPosterior,
    RecommendationDetail,
    RecommendationListResponse,
    RecommendationSummary,
    StackAdaptSource,
    TenantAdvertiser,
    TenantHierarchyResponse,
    TenantPartner,
    TenantWorkspace,
    UserDecisionRequest,
    UserDecisionResponse,
    UserMembership,
    WhyLibraryEntry,
    WhyLibraryResponse,
)
from adam.api.dashboard.service import (
    fetch_graph_intelligence,
    fetch_stackadapt_summary,
    generate_recommendations,
    get_recommendation_by_id,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# =============================================================================
# Health / identity
# =============================================================================


@router.get("/health", response_model=DashboardHealthResponse)
async def health() -> DashboardHealthResponse:
    """Public health probe. No auth."""
    neo4j_ok = False
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        neo4j_ok = bool(client.is_connected)
    except Exception:  # pragma: no cover - defensive
        neo4j_ok = False

    return DashboardHealthResponse(status="ok", neo4j_connected=neo4j_ok)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: DashboardUser = Depends(require_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
    )


# =============================================================================
# Campaigns (v1 skeleton — real StackAdapt / Neo4j wiring in next task)
# =============================================================================


@router.get("/campaigns", response_model=CampaignListResponse)
async def list_campaigns(
    _user: DashboardUser = Depends(require_user),
) -> CampaignListResponse:
    """List campaigns pulled live from StackAdapt GraphQL.

    When StackAdapt is unreachable, returns an empty list with a
    source=unavailable annotation the dashboard can render as a
    configuration banner rather than failing the request.
    """
    summary = await fetch_stackadapt_summary()

    campaigns = [
        CampaignSummary(
            id=c.id,
            name=c.name,
            channel_type=c.channel_type,
            group_name=c.group_name,
            status=c.status,
            impressions=c.impressions,
            clicks=c.clicks,
            conversions=c.conversions,
            spend_usd=c.spend_usd,
            ctr=c.ctr,
            cpa_usd=c.cpa_usd,
            roas=c.roas,
        )
        for c in summary.campaigns
    ]

    return CampaignListResponse(
        campaigns=campaigns,
        total=len(campaigns),
        stackadapt=StackAdaptSource(
            source=summary.source,
            reason=summary.reason,
            advertiser_name=summary.advertiser_name,
        ),
    )


# =============================================================================
# Analytics summary (v1 skeleton)
# =============================================================================


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    _user: DashboardUser = Depends(require_user),
) -> AnalyticsSummary:
    """High-level KPI digest — live StackAdapt totals + Neo4j graph stats."""
    stackadapt = await fetch_stackadapt_summary()
    graph = await fetch_graph_intelligence()

    live_campaigns = sum(
        1
        for c in stackadapt.campaigns
        if (c.status or "").upper() in {"ACTIVE", "LIVE", "RUNNING"}
    )

    return AnalyticsSummary(
        campaigns_total=len(stackadapt.campaigns),
        campaigns_live=live_campaigns,
        total_impressions=stackadapt.impressions,
        total_clicks=stackadapt.clicks,
        total_conversions=stackadapt.conversions,
        total_spend_usd=stackadapt.spend_usd,
        overall_ctr=stackadapt.ctr,
        overall_cpa_usd=stackadapt.cpa_usd,
        overall_roas=stackadapt.roas,
        active_archetypes=graph.archetypes,
        edges_in_graph=graph.brand_converted_edges,
        advertiser_name=stackadapt.advertiser_name,
        stackadapt_source=stackadapt.source,
        stackadapt_reason=stackadapt.reason,
        graph_source=graph.source,
        last_updated=datetime.now(timezone.utc),
    )


# =============================================================================
# Multi-tenant shell (Phase C scaffolding; single-tenant operational in v1)
# =============================================================================


@router.get("/tenants/me", response_model=UserMembership)
async def get_my_membership(
    user: DashboardUser = Depends(require_user),
) -> UserMembership:
    """Current user's tenant membership (role, partner, advertiser).

    v1 pilot returns the superadmin membership stamped by migration
    022. When Phase C multi-tenancy lands this endpoint is how the
    dashboard resolves the active scope for any request.
    """
    partner: Optional[TenantPartner] = None
    advertiser: Optional[TenantAdvertiser] = None
    role = "superadmin"

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if client.is_connected:
            async with await client.session() as session:
                result = await session.run(
                    """
                    MATCH (u:DialogueUser {id: $user_id})
                    OPTIONAL MATCH (u)-[:BELONGS_TO_PARTNER]->(p:TenantPartner)
                    OPTIONAL MATCH (u)-[:ADMIN_OF_ADVERTISER]->(a:TenantAdvertiser)
                    RETURN u, p, a
                    """,
                    user_id=user.id,
                )
                record = await result.single()
                if record:
                    u_node = record["u"]
                    role = u_node.get("role", "superadmin")
                    if record["p"] is not None:
                        partner = _tenant_partner_from_node(record["p"])
                    if record["a"] is not None:
                        advertiser = _tenant_advertiser_from_node(record["a"])
    except Exception as exc:
        logger.warning("get_my_membership failed: %s", exc)

    return UserMembership(
        user_id=user.id,
        role=role,
        partner=partner,
        advertiser=advertiser,
    )


@router.get("/tenants/hierarchy", response_model=TenantHierarchyResponse)
async def get_tenant_hierarchy(
    user: DashboardUser = Depends(require_user),
) -> TenantHierarchyResponse:
    """The full Partner → Advertiser → Workspace hierarchy.

    Superadmin-only in the Phase C roll-out. v1 returns the full tree
    unconditionally (single-tenant pilot); when role scoping lands,
    non-superadmin callers will see only their own partner subtree.
    """
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return TenantHierarchyResponse(
                partners=[],
                total_partners=0,
                total_advertisers=0,
                total_workspaces=0,
            )
        async with await client.session() as session:
            partners_result = await session.run(
                """
                MATCH (p:TenantPartner)
                RETURN p
                ORDER BY p.created_at ASC
                """,
            )
            partners: list[TenantPartner] = []
            async for record in partners_result:
                partners.append(_tenant_partner_from_node(record["p"]))

            total_advertisers = 0
            total_workspaces = 0
            for partner in partners:
                adv_result = await session.run(
                    """
                    MATCH (p:TenantPartner {id: $partner_id})
                          -[:HAS_ADVERTISER]->(a:TenantAdvertiser)
                    RETURN a
                    ORDER BY a.created_at ASC
                    """,
                    partner_id=partner.id,
                )
                async for adv_record in adv_result:
                    advertiser = _tenant_advertiser_from_node(adv_record["a"])
                    ws_result = await session.run(
                        """
                        MATCH (a:TenantAdvertiser {id: $adv_id})
                              -[:HAS_WORKSPACE]->(w:TenantWorkspace)
                        RETURN w
                        ORDER BY w.created_at ASC
                        """,
                        adv_id=advertiser.id,
                    )
                    async for ws_record in ws_result:
                        advertiser.workspaces.append(
                            _tenant_workspace_from_node(ws_record["w"])
                        )
                        total_workspaces += 1
                    partner.advertisers.append(advertiser)
                    total_advertisers += 1
    except Exception as exc:
        logger.exception("get_tenant_hierarchy failed: %s", exc)
        return TenantHierarchyResponse(
            partners=[],
            total_partners=0,
            total_advertisers=0,
            total_workspaces=0,
        )

    return TenantHierarchyResponse(
        partners=partners,
        total_partners=len(partners),
        total_advertisers=total_advertisers,
        total_workspaces=total_workspaces,
    )


def _tenant_partner_from_node(node: Any) -> TenantPartner:
    created_at = node.get("created_at")
    if hasattr(created_at, "to_native"):
        created_at = created_at.to_native()
    return TenantPartner(
        id=node["id"],
        name=node.get("name", ""),
        kind=node.get("kind", "agency"),
        white_label_name=node.get("white_label_name"),
        billing_email=node.get("billing_email"),
        status=node.get("status", "active"),
        created_at=created_at or datetime.now(timezone.utc),
    )


def _tenant_advertiser_from_node(node: Any) -> TenantAdvertiser:
    created_at = node.get("created_at")
    if hasattr(created_at, "to_native"):
        created_at = created_at.to_native()
    return TenantAdvertiser(
        id=node["id"],
        partner_id=node.get("partner_id", ""),
        name=node.get("name", ""),
        category=node.get("category"),
        stackadapt_advertiser_id=node.get("stackadapt_advertiser_id"),
        status=node.get("status", "active"),
        created_at=created_at or datetime.now(timezone.utc),
    )


def _tenant_workspace_from_node(node: Any) -> TenantWorkspace:
    created_at = node.get("created_at")
    if hasattr(created_at, "to_native"):
        created_at = created_at.to_native()
    return TenantWorkspace(
        id=node["id"],
        advertiser_id=node.get("advertiser_id", ""),
        name=node.get("name", ""),
        purpose=node.get("purpose"),
        status=node.get("status", "active"),
        created_at=created_at or datetime.now(timezone.utc),
    )


# =============================================================================
# Autopilot settings (five-mode trust curve)
# =============================================================================


_DEFAULT_GATES: dict[str, dict[str, str]] = {
    "observer": {
        "creative_gate": "approve", "bid_gate": "approve",
        "audience_gate": "approve", "budget_gate": "approve",
        "kill_gate": "approve",
    },
    "explain": {
        "creative_gate": "approve", "bid_gate": "approve",
        "audience_gate": "notify", "budget_gate": "approve",
        "kill_gate": "approve",
    },
    "notify": {
        "creative_gate": "notify", "bid_gate": "auto",
        "audience_gate": "notify", "budget_gate": "approve",
        "kill_gate": "approve",
    },
    "delegate": {
        "creative_gate": "notify", "bid_gate": "auto",
        "audience_gate": "auto", "budget_gate": "notify",
        "kill_gate": "approve",
    },
    "autopilot": {
        "creative_gate": "auto", "bid_gate": "auto",
        "audience_gate": "auto", "budget_gate": "auto",
        "kill_gate": "approve",
    },
}


@router.get("/settings/autopilot", response_model=AutopilotSettings)
async def get_autopilot_settings(
    user: DashboardUser = Depends(require_user),
) -> AutopilotSettings:
    """Read the autopilot settings for the current user. If none
    exist, initialise with the default 'explain' mode.
    """
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Neo4j unavailable",
            )
        async with await client.session() as session:
            now = datetime.now(timezone.utc)
            result = await session.run(
                """
                MERGE (u:DialogueUser {id: $user_id})
                MERGE (a:AutopilotSetting {user_id: $user_id})
                  ON CREATE SET a.mode = 'explain',
                                a.creative_gate = 'approve',
                                a.bid_gate = 'approve',
                                a.audience_gate = 'notify',
                                a.budget_gate = 'approve',
                                a.kill_gate = 'approve',
                                a.campaigns_at_current_mode = 0,
                                a.successful_at_current_mode = 0,
                                a.last_graduated_at = null,
                                a.updated_at = $now
                MERGE (u)-[:HAS_AUTOPILOT_SETTING]->(a)
                RETURN a
                """,
                user_id=user.id, now=now,
            )
            record = await result.single()
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Autopilot setting not persisted",
                )
            node = record["a"]
            return _autopilot_from_node(node, user.id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_autopilot_settings failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.put("/settings/autopilot", response_model=AutopilotSettings)
async def update_autopilot_settings(
    request: AutopilotUpdateRequest,
    user: DashboardUser = Depends(require_user),
) -> AutopilotSettings:
    """Change the autopilot mode or per-gate overrides. Switching
    mode resets the campaigns-at-current-mode counter so the
    graduation signal tracks time at the *current* mode.
    """
    defaults = _DEFAULT_GATES[request.mode]
    gates = {
        "creative_gate": request.creative_gate or defaults["creative_gate"],
        "bid_gate": request.bid_gate or defaults["bid_gate"],
        "audience_gate": request.audience_gate or defaults["audience_gate"],
        "budget_gate": request.budget_gate or defaults["budget_gate"],
        # Kill is never auto; force approve unless user explicitly set notify.
        "kill_gate": request.kill_gate
        if request.kill_gate in ("approve", "notify")
        else "approve",
    }

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Neo4j unavailable",
            )

        now = datetime.now(timezone.utc)
        async with await client.session() as session:
            result = await session.run(
                """
                MERGE (u:DialogueUser {id: $user_id})
                MERGE (a:AutopilotSetting {user_id: $user_id})
                  ON CREATE SET a.campaigns_at_current_mode = 0,
                                a.successful_at_current_mode = 0
                SET a.mode = $mode,
                    a.creative_gate = $creative_gate,
                    a.bid_gate = $bid_gate,
                    a.audience_gate = $audience_gate,
                    a.budget_gate = $budget_gate,
                    a.kill_gate = $kill_gate,
                    a.campaigns_at_current_mode = 0,
                    a.successful_at_current_mode = 0,
                    a.updated_at = $now
                MERGE (u)-[:HAS_AUTOPILOT_SETTING]->(a)
                RETURN a
                """,
                user_id=user.id,
                mode=request.mode,
                creative_gate=gates["creative_gate"],
                bid_gate=gates["bid_gate"],
                audience_gate=gates["audience_gate"],
                budget_gate=gates["budget_gate"],
                kill_gate=gates["kill_gate"],
                now=now,
            )
            record = await result.single()
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Autopilot update failed",
                )
            return _autopilot_from_node(record["a"], user.id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("update_autopilot_settings failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


def _autopilot_from_node(node: Any, user_id: str) -> AutopilotSettings:
    def _dt(key: str) -> Optional[datetime]:
        value = node.get(key)
        if value is None:
            return None
        return value.to_native() if hasattr(value, "to_native") else value

    return AutopilotSettings(
        user_id=user_id,
        mode=node.get("mode", "explain"),
        creative_gate=node.get("creative_gate", "approve"),
        bid_gate=node.get("bid_gate", "approve"),
        audience_gate=node.get("audience_gate", "notify"),
        budget_gate=node.get("budget_gate", "approve"),
        kill_gate=node.get("kill_gate", "approve"),
        campaigns_at_current_mode=int(
            node.get("campaigns_at_current_mode", 0)
        ),
        successful_at_current_mode=int(
            node.get("successful_at_current_mode", 0)
        ),
        last_graduated_at=_dt("last_graduated_at"),
        updated_at=_dt("updated_at") or datetime.now(timezone.utc),
    )


# =============================================================================
# Decay Adjudicator (Task 33)
# =============================================================================


@router.get("/decay/report", response_model=DecayReport)
async def decay_report(
    _user: DashboardUser = Depends(require_user),
) -> DecayReport:
    """Run Task 33 and return the latest DecayCohortReport.

    v1 runs the task on every GET since the cohort is fully
    deterministic from current StackAdapt state. Once the scheduler
    is wired this becomes a read-only fetch of the most recent
    persisted DecayCohort.
    """
    from adam.intelligence.daily.task_33_decay_adjudicator import (
        run_decay_adjudicator,
    )

    report = await run_decay_adjudicator()
    return DecayReport(
        run_id=report.run_id,
        run_date=report.run_date,
        task_version=report.task_version,
        campaigns=[
            CampaignDecayClassification(
                campaign_id=c.campaign_id,
                campaign_name=c.campaign_name,
                total_users=c.total_users,
                continue_count=c.continue_count,
                restart_count=c.restart_count,
                abandon_count=c.abandon_count,
                zero_data_count=c.zero_data_count,
                advertiser_avg_cpa=c.advertiser_avg_cpa,
                campaign_cpa=c.campaign_cpa,
                flags=c.flags,
                recommended_action=c.recommended_action,
                rationale=c.rationale,
            )
            for c in report.campaigns
        ],
        total_users_classified=report.total_users_classified,
        overall_abandon_rate=report.overall_abandon_rate,
        source=report.source,
        source_note=report.source_note,
    )


# =============================================================================
# Multi-horizon adjudication view
# =============================================================================


_HORIZON_TO_DAYS: dict[str, float] = {
    "hours": 1.0,
    "days": 7.0,
    "weeks": 14.0,
    "months": 60.0,
}


@router.get(
    "/deviations/horizons",
    response_model=DeviationHorizonResponse,
)
async def deviation_horizons(
    user: DashboardUser = Depends(require_user),
) -> DeviationHorizonResponse:
    """Horizon progress per Deviation.

    For each deviation we compute when the causal-adjudication
    window closes (horizon_class → expected days) and compare to the
    current time. Deviations with an elapsed window become
    'ready' — the Inferential Learning Agent can adjudicate them.
    """
    horizons: list[DeviationHorizon] = []
    ready = 0
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return DeviationHorizonResponse(
                horizons=[], total=0, ready_count=0,
            )
        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})-[:DEVIATED]->(d:Deviation)
                RETURN d
                ORDER BY d.created_at DESC
                """,
                user_id=user.id,
            )
            now = datetime.now(timezone.utc)
            async for record in result:
                d = record["d"]
                created_at = (
                    d["created_at"].to_native()
                    if hasattr(d["created_at"], "to_native")
                    else d["created_at"]
                )
                horizon_class = d.get("horizon_class", "days")
                window_days = _HORIZON_TO_DAYS.get(horizon_class, 7.0)
                from datetime import timedelta

                horizon_ends_at = created_at + timedelta(days=window_days)
                elapsed = (now - created_at).total_seconds() / 86_400.0
                remaining = (horizon_ends_at - now).total_seconds() / 86_400.0

                outcome = d.get("adjudication_outcome")
                adj_status = d.get("adjudication_status", "pending")
                if adj_status == "adjudicated":
                    h_status = "adjudicated"
                elif remaining <= 0:
                    h_status = "ready"
                    ready += 1
                elif elapsed > 0:
                    h_status = "in_progress"
                else:
                    h_status = "too_early"

                horizons.append(
                    DeviationHorizon(
                        deviation_id=d["id"],
                        recommendation_id=d["recommendation_id"],
                        horizon_class=horizon_class,
                        created_at=created_at,
                        horizon_ends_at=horizon_ends_at,
                        days_elapsed=max(0.0, elapsed),
                        days_remaining=max(0.0, remaining),
                        status=h_status,
                        adjudication_outcome=outcome,
                    )
                )
    except Exception as exc:
        logger.exception("deviation_horizons failed: %s", exc)

    return DeviationHorizonResponse(
        horizons=horizons,
        total=len(horizons),
        ready_count=ready,
    )


# =============================================================================
# Causal Adjudicator + Why Library (Loop A → Loop B cross-pollination)
# =============================================================================


@router.post(
    "/deviations/adjudicate-ready",
    response_model=AdjudicationBatchResponse,
)
async def adjudicate_ready(
    user: DashboardUser = Depends(require_user),
) -> AdjudicationBatchResponse:
    """Run the Inferential Adjudicator over every Deviation whose
    horizon window has closed. Writes adjudication_status, creates
    Outcome nodes, and on system_right outcomes generates
    WhyLibraryEntry nodes for pre-emptive defensive reasoning.
    """
    from adam.intelligence.causal_adjudicator import (
        adjudicate_ready_deviations,
    )

    batch = await adjudicate_ready_deviations(user.id)
    return AdjudicationBatchResponse(
        adjudicated=[
            AdjudicationResultModel(
                deviation_id=r.deviation_id,
                recommendation_id=r.recommendation_id,
                outcome=r.outcome,  # type: ignore[arg-type]
                rationale=r.rationale,
                why_library_entry_id=r.why_library_entry_id,
                metric_observed=r.metric_observed,
                metric_value_before=r.metric_value_before,
                metric_value_after=r.metric_value_after,
            )
            for r in batch.adjudicated
        ],
        skipped_too_early=batch.skipped_too_early,
        skipped_no_data=batch.skipped_no_data,
        skipped_already_done=batch.skipped_already_done,
    )


@router.get("/why-library", response_model=WhyLibraryResponse)
async def get_why_library(
    user: DashboardUser = Depends(require_user),
    limit: int = Query(100, ge=1, le=500),
) -> WhyLibraryResponse:
    """Read the user's WhyLibrary — validated bias patterns surfaced
    as defensive reasoning at recommendation time.
    """
    from adam.intelligence.causal_adjudicator import fetch_why_library

    entries_raw = await fetch_why_library(user.id, limit=limit)
    entries: list[WhyLibraryEntry] = []
    for e in entries_raw:
        entries.append(
            WhyLibraryEntry(
                id=e.get("id", ""),
                trigger_pattern=e.get("trigger_pattern", ""),
                bias_class=e.get("bias_class", "unspecified"),
                evidence_strength=float(e.get("evidence_strength", 0.0) or 0.0),
                scope=e.get("scope", "user"),
                scope_id=e.get("scope_id"),
                countermeasure=e.get("countermeasure", ""),
                supporting_deviation_ids=list(
                    e.get("supporting_deviation_ids", []) or []
                ),
                warning_posterior_mean=float(
                    e.get("warning_posterior_mean", 0.0) or 0.0
                ),
                warning_posterior_observations=int(
                    e.get("warning_posterior_observations", 0) or 0
                ),
                created_at=e.get("created_at") or datetime.now(timezone.utc),
                last_validated_at=e.get("last_validated_at"),
                retired_at=e.get("retired_at"),
            )
        )
    return WhyLibraryResponse(entries=entries, total=len(entries))


# =============================================================================
# Mechanism effectiveness — renders Enhancement #33's hierarchical retargeting
# learning posteriors. Dashboard proxy over /api/v1/retargeting/learning/
# mechanism-effectiveness so the bearer-auth surface stays consistent and
# tenant-scoping hooks can be added here without touching the internal API.
# =============================================================================


@router.get(
    "/learning/mechanism-effectiveness",
    response_model=MechanismEffectivenessResponse,
)
async def get_mechanism_effectiveness(
    user: DashboardUser = Depends(require_user),
    archetype_id: Optional[str] = Query(
        None,
        description=(
            "Canonical archetype slug (e.g., 'careful_truster'). When paired "
            "with barrier, returns the per-mechanism Beta posteriors for that "
            "cell. Alone, returns barrier prevalence for the archetype."
        ),
    ),
    barrier: Optional[str] = Query(
        None,
        description=(
            "Barrier category slug (e.g., 'trust_deficit'). Only honored when "
            "archetype_id is also provided."
        ),
    ),
) -> MechanismEffectivenessResponse:
    """Read Enhancement #33's learned posteriors for the dashboard.

    v1 single-tenant pilot returns the full hierarchy regardless of caller;
    tenant-scoping (filter by TenantAdvertiser from migration 022) lands in
    Phase C multi-tenant build.
    """
    try:
        from adam.retargeting.api import (
            get_mechanism_effectiveness as _retargeting_endpoint,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Retargeting API unavailable for mechanism-effectiveness: %s", exc,
        )
        return MechanismEffectivenessResponse(
            global_stats={"error": "retargeting-engine-unavailable"},
            archetype_id=archetype_id,
            barrier=barrier,
        )

    try:
        raw = await _retargeting_endpoint(
            mechanism=None, barrier=barrier, archetype_id=archetype_id,
        )
    except Exception as exc:  # pragma: no cover - engine error
        logger.warning("Retargeting endpoint raised: %s", exc, exc_info=True)
        raw = {"global_stats": {"error": str(exc)[:200]}}

    posteriors_raw = raw.get("posteriors")
    posteriors: Optional[dict[str, MechanismPosterior]] = None
    if posteriors_raw:
        posteriors = {
            mech: MechanismPosterior(
                mean=float(p.get("mean", 0.0)),
                alpha=float(p.get("alpha", 0.0)),
                beta=float(p.get("beta", 0.0)),
                sample_count=int(p.get("sample_count", 0)),
                confidence=float(p.get("confidence", 0.0)),
            )
            for mech, p in posteriors_raw.items()
        }

    barrier_prevalence_raw = raw.get("barrier_prevalence")
    barrier_prevalence: Optional[dict[str, float]] = None
    if barrier_prevalence_raw:
        barrier_prevalence = {
            k: float(v) for k, v in barrier_prevalence_raw.items()
        }

    return MechanismEffectivenessResponse(
        global_stats=raw.get("global_stats") or {},
        posteriors=posteriors,
        barrier_prevalence=barrier_prevalence,
        archetype_id=archetype_id,
        barrier=barrier,
    )


# =============================================================================
# System Convergence (Front-end B — internal superadmin surface)
#
# Cross-archetype roll-up of Enhancement #33's retargeting learning
# state. Surface the cells the system has accumulated real confidence
# in, the novel findings still accumulating, and the cross-archetype
# patterns worth treating as platform-level priors. Internal only;
# client surfaces consume the PublicLabel-translated report endpoint.
# =============================================================================


@router.get(
    "/system/convergence",
    response_model=SystemConvergenceResponse,
)
async def get_system_convergence(
    user: DashboardUser = Depends(require_user),
) -> SystemConvergenceResponse:
    """Cross-archetype learning state for the internal operator surface."""
    from adam.api.dashboard.system_insights_service import (
        compose_system_convergence,
    )
    try:
        return await compose_system_convergence()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "System convergence composition failed: %s", exc, exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="System convergence temporarily unavailable",
        )


@router.get(
    "/system/client-decisions",
    response_model=ClientDecisionAuditResponse,
)
async def get_client_decision_audit(
    user: DashboardUser = Depends(require_user),
    limit: int = Query(100, ge=1, le=500),
) -> ClientDecisionAuditResponse:
    """Internal audit view of every client-rec acknowledge/decline event.

    Reads the UserDecision nodes produced by the Front-end A
    acknowledge-persistence flow and joins them with their Deviation +
    Outcome where applicable. Powers the Front-end B client-decisions
    audit tab so the operator can see what clients have been doing with
    recommendations and whether the causal adjudicator has resolved
    pending declines.
    """
    from adam.api.dashboard.client_decisions_service import (
        compose_client_decision_audit,
    )
    try:
        return await compose_client_decision_audit(limit=limit)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Client decision audit composition failed: %s", exc, exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Client decision audit temporarily unavailable",
        )


# =============================================================================
# Client Report (Front-end A)
#
# Produces the report-style payload for the advertiser-facing surface.
# Strict rule: every entity that could identify our methodology is
# resolved through the PublicLabelService before returning. See
# adam/api/dashboard/client_report_service.py for the composer.
# =============================================================================


@router.get(
    "/client/report",
    response_model=ClientReportResponse,
)
async def get_client_report(
    user: DashboardUser = Depends(require_user),
    advertiser_id: Optional[str] = Query(
        None,
        description=(
            "Advertiser to scope the report to. For the single-tenant LUXY "
            "pilot, defaults to 'luxy_ride' when omitted."
        ),
    ),
) -> ClientReportResponse:
    """Compose the client-facing report for an advertiser.

    Output contains ONLY labeled natural-language sections + safe
    performance metrics. No internal taxonomy, no posteriors, no
    mechanism/barrier/archetype slugs.

    ``missing_labels`` is populated as an internal diagnostic when a
    PublicLabel is absent; it is returned in the response body so an
    internal-role caller can surface the gap, but the client renderer
    must not display it.
    """
    from adam.api.dashboard.client_report_service import (
        compose_client_report,
    )

    effective_advertiser_id = advertiser_id or "luxy_ride"
    try:
        report = await compose_client_report(
            advertiser_id=effective_advertiser_id,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Client report composition failed for %s: %s",
            effective_advertiser_id, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Report composition temporarily unavailable",
        )

    # Fold any prior acknowledge/decline decisions back into the rec
    # list so the render shows persisted state on refresh.
    if report.recommendations:
        from adam.api.dashboard.client_decisions_service import (
            bulk_decisions_for_user,
        )
        rec_ids = [r["id"] for r in report.recommendations]
        prior = await bulk_decisions_for_user(user.id, rec_ids)
        for r in report.recommendations:
            existing = prior.get(r["id"])
            if existing is not None:
                r["status"] = (
                    "acknowledged" if existing.kind == "acknowledge"
                    else "declined"
                )

    return ClientReportResponse(
        advertiser_id=report.advertiser_id,
        advertiser_name=report.advertiser_name,
        period_start=report.period_start or None,
        period_end=report.period_end,
        generated_at=report.generated_at,
        impressions=report.impressions,
        clicks=report.clicks,
        conversions=report.conversions,
        spend_usd=report.spend_usd,
        ctr=report.ctr,
        cpa_usd=report.cpa_usd,
        roas=report.roas,
        campaigns_live=report.campaigns_live,
        campaigns_total=report.campaigns_total,
        segment_highlights=[
            ClientSegmentHighlight(**h) for h in report.segment_highlights
        ],
        message_observations=[
            ClientMessageObservation(**o) for o in report.message_observations
        ],
        recommendations=[
            ClientRecommendation(**r) for r in report.recommendations
        ],
        data_source_notes=report.data_source_notes,
        missing_labels=report.missing_labels,
    )


@router.post(
    "/client/recommendations/{recommendation_id}/decide",
    response_model=ClientRecommendationDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def decide_client_recommendation(
    recommendation_id: str,
    request: ClientRecommendationDecisionRequest,
    user: DashboardUser = Depends(require_user),
) -> ClientRecommendationDecisionResponse:
    """Persist the client's acknowledge or decline on a client report
    recommendation.

    Idempotent per (recommendation_id, user_id). Re-submission returns
    the existing decision rather than creating a duplicate.

    Decline with feedback_text captures the feedback as a Claim
    (status="hypothesis") and opens a Deviation for the causal
    adjudicator, same pipeline as the internal /decide path.
    """
    from adam.api.dashboard.client_decisions_service import (
        record_client_decision,
    )
    try:
        return await record_client_decision(
            user_id=user.id,
            recommendation_id=recommendation_id,
            request=request,
        )
    except Exception as exc:
        logger.exception(
            "decide_client_recommendation failed for user=%s rec=%s",
            user.id, recommendation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record decision: {exc}",
        )


# =============================================================================
# Recommendations — Uncertainty Panel + plan-before-patch + deviation capture
# =============================================================================


def _summary_from_detail(detail: RecommendationDetail) -> RecommendationSummary:
    return RecommendationSummary(
        id=detail.id,
        type=detail.type,
        title=detail.title,
        summary=detail.summary,
        campaign_id=detail.campaign_id,
        campaign_name=detail.campaign_name,
        preferred_choice=detail.preferred_choice,
        expected_horizon_class=detail.expected_horizon_class,
        status=detail.status,
        created_at=detail.created_at,
    )


@router.get("/recommendations", response_model=RecommendationListResponse)
async def list_recommendations(
    user: DashboardUser = Depends(require_user),
) -> RecommendationListResponse:
    """List pending recommendations for the current user.

    Recommendations are generated dynamically from live StackAdapt
    data. They carry structured Confident/Uncertain/Possibly-Wrong
    breakdowns per HMT Foundation §7.1.
    """
    recommendations, source, note = await generate_recommendations(user.id)
    return RecommendationListResponse(
        recommendations=[_summary_from_detail(r) for r in recommendations],
        total=len(recommendations),
        source=source,
        source_note=note,
    )


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=RecommendationDetail,
)
async def get_recommendation(
    recommendation_id: str,
    user: DashboardUser = Depends(require_user),
) -> RecommendationDetail:
    detail = await get_recommendation_by_id(user.id, recommendation_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found or no longer applicable",
        )

    # Fetch any decisions already recorded against this recommendation
    # so the UI can show the full history (not just the current state).
    detail.decisions = await _fetch_decisions(user.id, recommendation_id)
    return detail


@router.post(
    "/recommendations/{recommendation_id}/decide",
    response_model=UserDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def decide_recommendation(
    recommendation_id: str,
    request: UserDecisionRequest,
    user: DashboardUser = Depends(require_user),
) -> UserDecisionResponse:
    """Record the user's decision on a recommendation.

    When a user rejects or modifies a recommendation, their stated
    rationale is captured as a HYPOTHESIS — not a learning — per HMT
    Rule 12. The Inferential Learning Agent adjudicates later at
    horizon expiry.
    """
    detail = await get_recommendation_by_id(user.id, recommendation_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found or no longer applicable",
        )

    if request.kind == "modify" and not request.chosen_alternative:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chosen_alternative required when kind=modify",
        )

    decision_id = f"decision:{uuid.uuid4()}"
    claim_id: Optional[str] = None
    created_at = datetime.now(timezone.utc)

    chosen = (
        detail.preferred_choice
        if request.kind == "accept"
        else (request.chosen_alternative if request.kind == "modify" else None)
    )

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Neo4j unavailable",
            )

        async with await client.session() as session:
            # 1. Snapshot the Recommendation at decision time (audit trail).
            await session.run(
                """
                MERGE (r:Recommendation {id: $rec_id})
                  ON CREATE SET r.user_id = $user_id,
                                r.campaign_id = $campaign_id,
                                r.campaign_name = $campaign_name,
                                r.type = $type,
                                r.title = $title,
                                r.summary = $summary,
                                r.preferred_choice = $preferred_choice,
                                r.expected_horizon_class = $horizon,
                                r.status = $status,
                                r.created_at = $created_at,
                                r.evidence_json = $evidence_json,
                                r.alternatives_json = $alternatives_json
                  ON MATCH  SET r.status = $status
                """,
                rec_id=detail.id,
                user_id=user.id,
                campaign_id=detail.campaign_id,
                campaign_name=detail.campaign_name,
                type=detail.type,
                title=detail.title,
                summary=detail.summary,
                preferred_choice=detail.preferred_choice,
                horizon=detail.expected_horizon_class,
                status=_status_from_decision(request.kind),
                created_at=detail.created_at,
                evidence_json=detail.evidence.model_dump_json(),
                alternatives_json=_alternatives_to_json(detail.alternatives),
            )

            # 2. If the user provided a rationale, persist it as a Claim.
            if request.rationale_text:
                claim_id = f"claim:{uuid.uuid4()}"
                await session.run(
                    """
                    MERGE (u:DialogueUser {id: $user_id})
                    CREATE (c:Claim {
                      id: $claim_id,
                      user_id: $user_id,
                      text: $text,
                      elicitation_mode: 'freeform',
                      domain: 'deviation_rationale',
                      stated_confidence: null,
                      latency_ms: null,
                      frame: 'neutral',
                      status: 'hypothesis',
                      session_id: null,
                      mood_index: null,
                      recallability: null,
                      created_at: $created_at
                    })
                    MERGE (u)-[:ASSERTED]->(c)
                    CREATE (ls:LearningStatus {
                      claim_id: $claim_id,
                      current: 'captured',
                      transitioned_at: $created_at,
                      reason: 'rationale capture at decision time'
                    })
                    MERGE (c)-[:HAS_STATUS]->(ls)
                    """,
                    user_id=user.id,
                    claim_id=claim_id,
                    text=request.rationale_text,
                    created_at=created_at,
                )

            # 3. The UserDecision node — the canonical decision record.
            await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})
                MATCH (r:Recommendation {id: $rec_id})
                CREATE (d:UserDecision {
                  id: $decision_id,
                  user_id: $user_id,
                  recommendation_id: $rec_id,
                  kind: $kind,
                  chosen_alternative: $chosen_alternative,
                  rationale_class: $rationale_class,
                  rationale_text: $rationale_text,
                  claim_id: $claim_id,
                  created_at: $created_at
                })
                MERGE (u)-[:MADE]->(d)
                MERGE (d)-[:ON]->(r)
                """,
                user_id=user.id,
                rec_id=detail.id,
                decision_id=decision_id,
                kind=request.kind,
                chosen_alternative=chosen,
                rationale_class=request.rationale_class,
                rationale_text=request.rationale_text,
                claim_id=claim_id,
                created_at=created_at,
            )

            # 4. If this is a reject or modify (i.e. a deviation from
            # preferred_choice), also create a Deviation node for the
            # causal-adjudication pipeline per HMT §9.2.
            if request.kind in ("reject", "modify"):
                deviation_id = f"deviation:{uuid.uuid4()}"
                await session.run(
                    """
                    MATCH (u:DialogueUser {id: $user_id})
                    MATCH (r:Recommendation {id: $rec_id})
                    CREATE (dev:Deviation {
                      id: $deviation_id,
                      user_id: $user_id,
                      recommendation_id: $rec_id,
                      system_choice: $system_choice,
                      user_choice: $user_choice,
                      stated_rationale: $rationale_text,
                      rationale_class: $rationale_class,
                      adjudication_status: 'pending',
                      adjudication_outcome: null,
                      horizon_class: $horizon,
                      created_at: $created_at
                    })
                    MERGE (u)-[:DEVIATED]->(dev)
                    MERGE (dev)-[:FROM]->(r)
                    """,
                    user_id=user.id,
                    rec_id=detail.id,
                    deviation_id=deviation_id,
                    system_choice=detail.preferred_choice,
                    user_choice=chosen,
                    rationale_text=request.rationale_text,
                    rationale_class=request.rationale_class,
                    horizon=detail.expected_horizon_class,
                    created_at=created_at,
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("decide_recommendation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record decision: {exc}",
        )

    return UserDecisionResponse(
        id=decision_id,
        user_id=user.id,
        recommendation_id=detail.id,
        kind=request.kind,
        chosen_alternative=chosen,
        rationale_class=request.rationale_class,
        rationale_text=request.rationale_text,
        claim_id=claim_id,
        created_at=created_at,
    )


def _status_from_decision(kind: str) -> str:
    if kind == "accept":
        return "accepted"
    if kind == "modify":
        return "modified"
    return "rejected"


def _alternatives_to_json(alternatives) -> str:
    """Serialize alternatives to JSON for Neo4j storage."""
    import json

    return json.dumps([a.model_dump() for a in alternatives])


async def _fetch_decisions(
    user_id: str, recommendation_id: str,
) -> list[UserDecisionResponse]:
    """Load any UserDecisions already recorded against a recommendation."""
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return []
        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (d:UserDecision {
                  user_id: $user_id, recommendation_id: $rec_id
                })
                RETURN d
                ORDER BY d.created_at DESC
                """,
                user_id=user_id, rec_id=recommendation_id,
            )
            decisions: list[UserDecisionResponse] = []
            async for record in result:
                node = record["d"]
                decisions.append(
                    UserDecisionResponse(
                        id=node["id"],
                        user_id=node["user_id"],
                        recommendation_id=node["recommendation_id"],
                        kind=node["kind"],
                        chosen_alternative=node.get("chosen_alternative"),
                        rationale_class=node.get("rationale_class"),
                        rationale_text=node.get("rationale_text"),
                        claim_id=node.get("claim_id"),
                        created_at=node["created_at"].to_native()
                        if hasattr(node["created_at"], "to_native")
                        else node["created_at"],
                    )
                )
            return decisions
    except Exception as exc:
        logger.warning("_fetch_decisions failed: %s", exc)
        return []


# =============================================================================
# Dialogue Ledger — claims
# =============================================================================


@router.post(
    "/ledger/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_claim(
    request: ClaimCreateRequest,
    user: DashboardUser = Depends(require_user),
) -> ClaimResponse:
    """Record a Claim into the Dialogue Ledger.

    Every claim enters with status='hypothesis' per HMT Rule 12 — user
    self-reports are hypotheses until instrumented, horizon-completed,
    and causally adjudicated.
    """
    claim_id = f"claim:{uuid.uuid4()}"
    created_at = datetime.now(timezone.utc)

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Neo4j unavailable",
            )

        async with await client.session() as session:
            await session.run(
                """
                MERGE (u:DialogueUser {id: $user_id})
                  ON CREATE SET u.email = $email,
                                u.display_name = $display_name,
                                u.role = $role,
                                u.created_at = $created_at
                MERGE (dom:DialogueDomain {name: $domain})
                CREATE (c:Claim {
                  id: $claim_id,
                  user_id: $user_id,
                  text: $text,
                  elicitation_mode: $mode,
                  domain: $domain,
                  stated_confidence: $stated_confidence,
                  latency_ms: $latency_ms,
                  frame: $frame,
                  status: 'hypothesis',
                  session_id: $session_id,
                  mood_index: $mood_index,
                  recallability: $recallability,
                  created_at: $created_at
                })
                MERGE (u)-[:ASSERTED]->(c)
                MERGE (c)-[:IN_DOMAIN]->(dom)
                CREATE (ls:LearningStatus {
                  claim_id: $claim_id,
                  current: 'captured',
                  transitioned_at: $created_at,
                  reason: 'initial capture'
                })
                MERGE (c)-[:HAS_STATUS]->(ls)
                """,
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                role=user.role,
                claim_id=claim_id,
                text=request.text,
                mode=request.elicitation_mode,
                domain=request.domain,
                stated_confidence=request.stated_confidence,
                latency_ms=request.latency_ms,
                frame=request.frame,
                session_id=request.session_id,
                mood_index=request.mood_index,
                recallability=request.recallability,
                created_at=created_at,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("create_claim failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record claim: {exc}",
        )

    return ClaimResponse(
        id=claim_id,
        user_id=user.id,
        text=request.text,
        elicitation_mode=request.elicitation_mode,
        domain=request.domain,
        stated_confidence=request.stated_confidence,
        latency_ms=request.latency_ms,
        frame=request.frame,
        status="hypothesis",
        recallability=request.recallability,
        created_at=created_at,
    )


@router.get("/ledger/deviations", response_model=DeviationListResponse)
async def list_deviations(
    limit: int = Query(100, ge=1, le=500),
    user: DashboardUser = Depends(require_user),
) -> DeviationListResponse:
    """List Deviation events for the current user, most recent first."""
    deviations: list[DeviationSummary] = []
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return DeviationListResponse(deviations=[], total=0)
        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})-[:DEVIATED]->(d:Deviation)
                RETURN d
                ORDER BY d.created_at DESC
                LIMIT $limit
                """,
                user_id=user.id, limit=limit,
            )
            async for record in result:
                d = record["d"]
                deviations.append(
                    DeviationSummary(
                        id=d["id"],
                        user_id=d["user_id"],
                        recommendation_id=d["recommendation_id"],
                        system_choice=d["system_choice"],
                        user_choice=d.get("user_choice"),
                        stated_rationale=d.get("stated_rationale"),
                        rationale_class=d.get("rationale_class"),
                        adjudication_status=d.get("adjudication_status", "pending"),
                        adjudication_outcome=d.get("adjudication_outcome"),
                        horizon_class=d.get("horizon_class", "days"),
                        created_at=d["created_at"].to_native()
                        if hasattr(d["created_at"], "to_native")
                        else d["created_at"],
                    )
                )
    except Exception as exc:
        logger.exception("list_deviations failed: %s", exc)
        return DeviationListResponse(deviations=[], total=0)
    return DeviationListResponse(deviations=deviations, total=len(deviations))


@router.get("/ledger/calibration", response_model=CalibrationResponse)
async def calibration_summary(
    user: DashboardUser = Depends(require_user),
) -> CalibrationResponse:
    """Per-domain calibration snapshot from the Dialogue Ledger.

    Until outcomes have been observed and causally adjudicated, the
    Brier score is null and the surface shows activity-only metrics:
    claim counts per domain, recallability distribution, latency
    averages. This is still diagnostically useful — a user whose
    confident claims mostly fail the recallability probe shouldn't be
    trusted on that domain.
    """
    domains: list[DomainCalibration] = []
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return CalibrationResponse(
                domains=[],
                source="unavailable",
                source_note="Neo4j not connected",
            )

        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})-[:ASSERTED]->(c:Claim)
                WITH c.domain AS domain,
                     count(c) AS total,
                     count(CASE WHEN c.recallability = 'fluent' THEN 1 END) AS fluent,
                     count(CASE WHEN c.recallability = 'hesitant' THEN 1 END) AS hesitant,
                     count(CASE WHEN c.recallability = 'absent' THEN 1 END) AS absent,
                     avg(c.latency_ms) AS avg_latency,
                     count(CASE
                       WHEN c.status IN ['validated_user_right', 'validated_system_right']
                       THEN 1
                     END) AS validated
                RETURN domain, total, fluent, hesitant, absent, avg_latency, validated
                ORDER BY total DESC
                """,
                user_id=user.id,
            )
            async for record in result:
                domains.append(
                    DomainCalibration(
                        domain=record["domain"] or "uncategorized",
                        total_claims=int(record["total"] or 0),
                        fluent_recall_count=int(record["fluent"] or 0),
                        hesitant_recall_count=int(record["hesitant"] or 0),
                        absent_recall_count=int(record["absent"] or 0),
                        avg_latency_ms=float(record["avg_latency"])
                        if record["avg_latency"] is not None
                        else None,
                        validated_count=int(record["validated"] or 0),
                        brier_score=None,  # populated once outcomes land
                    )
                )
    except Exception as exc:
        logger.exception("calibration_summary failed: %s", exc)
        return CalibrationResponse(
            domains=[],
            source="unavailable",
            source_note=str(exc),
        )

    return CalibrationResponse(
        domains=domains,
        source="live",
        source_note=(
            "Brier scores activate once claims have been adjudicated "
            "against observed outcomes."
            if not any(d.validated_count for d in domains)
            else None
        ),
    )


@router.get("/ledger/claims", response_model=ClaimListResponse)
async def list_claims(
    domain: Optional[str] = Query(None, description="Filter by dialogue domain"),
    limit: int = Query(100, ge=1, le=500),
    user: DashboardUser = Depends(require_user),
) -> ClaimListResponse:
    """List Claims asserted by the current user, most recent first."""
    claims: list[ClaimResponse] = []

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return ClaimListResponse(claims=[], total=0)

        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})-[:ASSERTED]->(c:Claim)
                WHERE $domain IS NULL OR c.domain = $domain
                RETURN c
                ORDER BY c.created_at DESC
                LIMIT $limit
                """,
                user_id=user.id,
                domain=domain,
                limit=limit,
            )

            async for record in result:
                c = record["c"]
                claims.append(
                    ClaimResponse(
                        id=c["id"],
                        user_id=c["user_id"],
                        text=c["text"],
                        elicitation_mode=c["elicitation_mode"],
                        domain=c["domain"],
                        stated_confidence=c.get("stated_confidence"),
                        latency_ms=c.get("latency_ms"),
                        frame=c.get("frame", "neutral"),
                        status=c.get("status", "hypothesis"),
                        recallability=c.get("recallability"),
                        created_at=c["created_at"].to_native()
                        if hasattr(c["created_at"], "to_native")
                        else c["created_at"],
                    )
                )
    except Exception as exc:
        logger.exception("list_claims failed: %s", exc)
        return ClaimListResponse(claims=[], total=0)

    return ClaimListResponse(claims=claims, total=len(claims))
