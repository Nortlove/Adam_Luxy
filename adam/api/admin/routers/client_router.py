"""
Client Portal Router — /api/v2/client/*

Sanitized views for client_admin and client_viewer users.
No visibility into archetypes, mechanisms, bilateral evidence, or DCIL internals.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from adam.api.admin.db import get_db
from adam.api.admin.dependencies import get_current_user, get_org_filter

router = APIRouter(prefix="/api/v2/client", tags=["client_portal"])


@router.get("/dashboard")
async def client_dashboard(user=Depends(get_current_user)):
    org_id = get_org_filter(user)
    if not org_id:
        return {"error": "Super admins should use /api/v2/admin/"}

    db = get_db()
    campaigns = await db.fetch_all(
        "SELECT id, name, status, brand_name, daily_budget FROM campaigns WHERE organization_id = $1 AND status != 'archived'",
        org_id,
    )

    active = sum(1 for c in campaigns if c["status"] == "active")

    # Aggregate performance from latest snapshots
    total_spend = 0.0
    total_conversions = 0
    for c in campaigns:
        snap = await db.fetch_one(
            "SELECT spend, conversions FROM campaign_performance_snapshots WHERE campaign_id = $1 ORDER BY snapshot_date DESC LIMIT 1",
            str(c["id"]),
        )
        if snap:
            total_spend += float(snap.get("spend", 0))
            total_conversions += int(snap.get("conversions", 0))

    return {
        "total_campaigns": len(campaigns),
        "active_campaigns": active,
        "total_spend": total_spend,
        "total_conversions": total_conversions,
        "overall_cpa": total_spend / total_conversions if total_conversions > 0 else 0,
        "campaigns": [
            {
                "id": str(c["id"]),
                "name": c["name"],
                "status": c["status"],
                "brand_name": c["brand_name"],
            }
            for c in campaigns
        ],
    }


@router.get("/campaigns")
async def client_campaigns(user=Depends(get_current_user)):
    org_id = get_org_filter(user)
    if not org_id:
        raise HTTPException(status_code=403, detail="Use admin endpoints")

    db = get_db()
    campaigns = await db.fetch_all(
        "SELECT id, name, status, brand_name, daily_budget, total_budget, start_date, end_date, created_at "
        "FROM campaigns WHERE organization_id = $1 ORDER BY created_at DESC",
        org_id,
    )

    return [
        {
            "id": str(c["id"]),
            "name": c["name"],
            "status": c["status"],
            "brand_name": c["brand_name"],
            "daily_budget": c.get("daily_budget"),
            "total_budget": c.get("total_budget"),
            "start_date": str(c.get("start_date") or ""),
            "end_date": str(c.get("end_date") or ""),
            "created_at": str(c["created_at"]),
        }
        for c in campaigns
    ]


@router.get("/campaigns/{campaign_id}")
async def client_campaign_detail(campaign_id: str, user=Depends(get_current_user)):
    org_id = get_org_filter(user)
    if not org_id:
        raise HTTPException(status_code=403)

    db = get_db()
    c = await db.fetch_one("SELECT * FROM campaigns WHERE id = $1 AND organization_id = $2", campaign_id, org_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Sanitized view — no archetypes, no mechanisms, no DCIL config
    snap = await db.fetch_one(
        "SELECT * FROM campaign_performance_snapshots WHERE campaign_id = $1 ORDER BY snapshot_date DESC LIMIT 1",
        campaign_id,
    )

    result = {
        "id": str(c["id"]),
        "name": c["name"],
        "status": c["status"],
        "brand_name": c["brand_name"],
        "daily_budget": c.get("daily_budget"),
        "total_budget": c.get("total_budget"),
        "start_date": str(c.get("start_date") or ""),
        "end_date": str(c.get("end_date") or ""),
    }

    if snap:
        result["performance"] = {
            "date": str(snap["snapshot_date"]),
            "impressions": snap.get("impressions", 0),
            "clicks": snap.get("clicks", 0),
            "conversions": snap.get("conversions", 0),
            "spend": float(snap.get("spend", 0)),
            "cpa": float(snap.get("cpa", 0)),
            "roas": float(snap.get("roas", 0)),
        }

    return result


@router.get("/campaigns/{campaign_id}/reports")
async def client_reports(campaign_id: str, user=Depends(get_current_user)):
    """Client users see only Tier A reports."""
    org_id = get_org_filter(user)
    if not org_id:
        raise HTTPException(status_code=403)

    db = get_db()
    reports = await db.fetch_all(
        "SELECT id, tier, period_start, period_end, report_data, generated_at "
        "FROM reports WHERE campaign_id = $1 AND organization_id = $2 AND tier = 'tier_a' "
        "ORDER BY period_end DESC",
        campaign_id, org_id,
    )

    # Mark as viewed
    for r in reports:
        if not r.get("viewed_by_client"):
            await db.execute(
                "UPDATE reports SET viewed_by_client = 1, viewed_at = datetime('now') WHERE id = $1",
                str(r["id"]),
            )

    return [
        {
            "id": str(r["id"]),
            "period_start": str(r["period_start"]),
            "period_end": str(r["period_end"]),
            "report": json.loads(r["report_data"]) if isinstance(r.get("report_data"), str) else r.get("report_data", {}),
            "generated_at": str(r["generated_at"]),
        }
        for r in reports
    ]
