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
    RecommendationDetail,
    RecommendationListResponse,
    RecommendationSummary,
    StackAdaptSource,
    UserDecisionRequest,
    UserDecisionResponse,
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
