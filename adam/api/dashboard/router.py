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
    AnalyticsSummary,
    CampaignListResponse,
    CampaignSummary,
    ClaimCreateRequest,
    ClaimListResponse,
    ClaimResponse,
    CurrentUserResponse,
    DashboardHealthResponse,
    StackAdaptSource,
)
from adam.api.dashboard.service import (
    fetch_graph_intelligence,
    fetch_stackadapt_summary,
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
