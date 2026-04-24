"""
Campaign Router — /api/v2/admin/campaigns/*

CRUD + lifecycle transitions + performance + archetypes + creatives + domains.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from adam.api.admin.db import get_db
from adam.api.admin.dependencies import get_current_user, get_org_filter, require_admin, require_super_admin
from adam.api.admin.models.campaign import (
    VALID_TRANSITIONS,
    CampaignCreate,
    CampaignList,
    CampaignPerformance,
    CampaignResponse,
    CampaignUpdate,
)
from adam.api.admin.models.archetype import ArchetypeCreate, ArchetypeResponse, ArchetypeUpdate
from adam.api.admin.models.creative import CreativeCreate, CreativeResponse, CreativeUpdate
from adam.api.admin.models.domain import DomainBulkCreate, DomainCreate, DomainResponse
from adam.api.admin.models.directive import DCILStatus, DirectiveApprove, DirectiveBlock, DirectiveList, DirectiveResponse
from adam.api.admin.models.report import ReportList, ReportResponse
from adam.api.admin.models.tracker import TrackerCreate, TrackerResponse

router = APIRouter(prefix="/api/v2/admin/campaigns", tags=["campaigns"])


# ── Campaign CRUD ──

@router.get("", response_model=CampaignList)
async def list_campaigns(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    org_id: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    db = get_db()
    org_filter = get_org_filter(user)
    offset = (page - 1) * per_page

    conditions = []
    params = []
    idx = 1

    if org_filter:
        conditions.append(f"organization_id = ${idx}")
        params.append(org_filter)
        idx += 1
    elif org_id:
        conditions.append(f"organization_id = ${idx}")
        params.append(org_id)
        idx += 1

    if status_filter:
        conditions.append(f"status = ${idx}")
        params.append(status_filter)
        idx += 1

    where = " AND ".join(conditions) if conditions else "1=1"

    campaigns = await db.fetch_all(
        f"SELECT * FROM campaigns WHERE {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}",
        *params, per_page, offset,
    )

    total_row = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM campaigns WHERE {where}", *params)
    total = total_row["cnt"] if total_row else 0

    return CampaignList(
        campaigns=[_campaign_to_response(c) for c in campaigns],
        total=total, page=page, per_page=per_page,
    )


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(req: CampaignCreate, user=Depends(require_admin)):
    db = get_db()

    org_filter = get_org_filter(user)
    if org_filter and req.organization_id != org_filter:
        raise HTTPException(status_code=403, detail="Cannot create campaign for another organization")

    campaign_id = str(uuid.uuid4())
    now = str(datetime.now(timezone.utc))

    await db.execute(
        "INSERT INTO campaigns (id, organization_id, name, brand_name, brand_asin, brand_website, "
        "brand_category, brand_logo_url, notes, created_by, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
        campaign_id, req.organization_id, req.name, req.brand_name,
        req.brand_asin, req.brand_website, req.brand_category, req.brand_logo_url,
        req.notes, str(user["id"]), now, now,
    )

    c = await db.fetch_one("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    return _campaign_to_response(c)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, user=Depends(get_current_user)):
    db = get_db()
    c = await db.fetch_one("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    org_filter = get_org_filter(user)
    if org_filter and str(c["organization_id"]) != org_filter:
        raise HTTPException(status_code=403, detail="Access denied")

    return _campaign_to_response(c)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: str, req: CampaignUpdate, user=Depends(require_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))

    existing = await db.fetch_one("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Campaign not found")

    updates = []
    values = []
    idx = 1

    for field in [
        "name", "brand_name", "brand_asin", "brand_website", "brand_category",
        "brand_logo_url", "total_budget", "daily_budget", "currency",
        "start_date", "end_date", "timezone", "dsp_platform", "dsp_advertiser_id",
        "dcil_enabled", "dcil_auto_execute", "tier_a_frequency",
        "conversion_pixel_id", "conversion_type", "conversion_value",
        "attribution_window_days", "notes",
    ]:
        val = getattr(req, field, None)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            values.append(val if not isinstance(val, bool) else (1 if val else 0))
            idx += 1

    for json_field in ["geo_targets", "frequency_cap", "dayparting", "dcil_safety_rails"]:
        val = getattr(req, json_field, None)
        if val is not None:
            updates.append(f"{json_field} = ${idx}")
            values.append(json.dumps(val))
            idx += 1

    if req.dsp_api_key:
        updates.append(f"dsp_api_key_encrypted = ${idx}")
        values.append(req.dsp_api_key)  # TODO: encrypt with AES-256-GCM
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append(f"updated_at = ${idx}")
    values.append(now)
    idx += 1
    values.append(campaign_id)

    await db.execute(f"UPDATE campaigns SET {', '.join(updates)} WHERE id = ${idx}", *values)

    c = await db.fetch_one("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    return _campaign_to_response(c)


# ── Lifecycle Transitions ──

@router.post("/{campaign_id}/configure")
async def configure_campaign(campaign_id: str, user=Depends(require_admin)):
    return await _transition(campaign_id, "configured", user)


@router.post("/{campaign_id}/submit-review")
async def submit_review(campaign_id: str, user=Depends(require_admin)):
    return await _transition(campaign_id, "review", user)


@router.post("/{campaign_id}/activate")
async def activate_campaign(campaign_id: str, user=Depends(require_super_admin)):
    result = await _transition(campaign_id, "active", user)
    # TODO: trigger StackAdapt deployment via deployment_service
    return result


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, user=Depends(require_admin)):
    return await _transition(campaign_id, "paused", user)


@router.post("/{campaign_id}/resume")
async def resume_campaign(campaign_id: str, user=Depends(require_admin)):
    return await _transition(campaign_id, "active", user)


@router.post("/{campaign_id}/complete")
async def complete_campaign(campaign_id: str, user=Depends(require_admin)):
    return await _transition(campaign_id, "completed", user)


@router.post("/{campaign_id}/archive")
async def archive_campaign(campaign_id: str, user=Depends(require_admin)):
    return await _transition(campaign_id, "archived", user)


async def _transition(campaign_id: str, target: str, user):
    db = get_db()
    c = await db.fetch_one("SELECT status FROM campaigns WHERE id = $1", campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current = c["status"]
    if target not in VALID_TRANSITIONS.get(current, []):
        raise HTTPException(status_code=400, detail=f"Cannot transition from '{current}' to '{target}'")

    now = str(datetime.now(timezone.utc))
    await db.execute("UPDATE campaigns SET status = $1, updated_at = $2 WHERE id = $3", target, now, campaign_id)
    return {"status": target, "campaign_id": campaign_id, "transitioned_at": now}


# ── Archetypes ──

@router.get("/{campaign_id}/archetypes")
async def list_archetypes(campaign_id: str, user=Depends(get_current_user)):
    db = get_db()
    archs = await db.fetch_all("SELECT * FROM campaign_archetypes WHERE campaign_id = $1 ORDER BY budget_weight DESC", campaign_id)
    return [_archetype_to_response(a) for a in archs]


@router.post("/{campaign_id}/archetypes", response_model=ArchetypeResponse, status_code=201)
async def add_archetype(campaign_id: str, req: ArchetypeCreate, user=Depends(require_admin)):
    db = get_db()
    arch_id = str(uuid.uuid4())
    now = str(datetime.now(timezone.utc))
    await db.execute(
        "INSERT INTO campaign_archetypes (id, campaign_id, archetype_name, is_custom, budget_weight, "
        "primary_mechanism, secondary_mechanism, framing, notes, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        arch_id, campaign_id, req.archetype_name, 1 if req.is_custom else 0,
        req.budget_weight, req.primary_mechanism, req.secondary_mechanism,
        req.framing, req.notes, now, now,
    )
    a = await db.fetch_one("SELECT * FROM campaign_archetypes WHERE id = $1", arch_id)
    return _archetype_to_response(a)


@router.put("/{campaign_id}/archetypes/{arch_id}", response_model=ArchetypeResponse)
async def update_archetype(campaign_id: str, arch_id: str, req: ArchetypeUpdate, user=Depends(require_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))
    updates, values, idx = [], [], 1
    for field in ["budget_weight", "primary_mechanism", "secondary_mechanism", "framing", "notes"]:
        val = getattr(req, field, None)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            values.append(val)
            idx += 1
    if updates:
        updates.append(f"updated_at = ${idx}")
        values.append(now)
        idx += 1
        values.append(arch_id)
        await db.execute(f"UPDATE campaign_archetypes SET {', '.join(updates)} WHERE id = ${idx}", *values)
    a = await db.fetch_one("SELECT * FROM campaign_archetypes WHERE id = $1", arch_id)
    return _archetype_to_response(a)


@router.delete("/{campaign_id}/archetypes/{arch_id}")
async def delete_archetype(campaign_id: str, arch_id: str, user=Depends(require_admin)):
    db = get_db()
    await db.execute("DELETE FROM campaign_archetypes WHERE id = $1 AND campaign_id = $2", arch_id, campaign_id)
    return {"status": "deleted"}


# ── Creatives ──

@router.get("/{campaign_id}/archetypes/{arch_id}/creatives")
async def list_creatives(campaign_id: str, arch_id: str, user=Depends(get_current_user)):
    db = get_db()
    creatives = await db.fetch_all("SELECT * FROM creative_variants WHERE campaign_archetype_id = $1", arch_id)
    return [_creative_to_response(c) for c in creatives]


@router.post("/{campaign_id}/archetypes/{arch_id}/creatives", response_model=CreativeResponse, status_code=201)
async def add_creative(campaign_id: str, arch_id: str, req: CreativeCreate, user=Depends(require_admin)):
    db = get_db()
    creative_id = str(uuid.uuid4())
    now = str(datetime.now(timezone.utc))
    await db.execute(
        "INSERT INTO creative_variants (id, campaign_archetype_id, variant_label, mechanism, headline, "
        "body_copy, cta_text, image_url, landing_url, tone, construal_level, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)",
        creative_id, arch_id, req.variant_label, req.mechanism, req.headline,
        req.body_copy, req.cta_text, req.image_url, req.landing_url,
        req.tone, req.construal_level, now, now,
    )
    c = await db.fetch_one("SELECT * FROM creative_variants WHERE id = $1", creative_id)
    return _creative_to_response(c)


@router.put("/creatives/{creative_id}", response_model=CreativeResponse)
async def update_creative(creative_id: str, req: CreativeUpdate, user=Depends(require_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))
    updates, values, idx = [], [], 1
    for field in ["variant_label", "mechanism", "headline", "body_copy", "cta_text",
                   "image_url", "landing_url", "tone", "construal_level", "status"]:
        val = getattr(req, field, None)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            values.append(val)
            idx += 1
    if updates:
        updates.append(f"updated_at = ${idx}")
        values.append(now)
        idx += 1
        values.append(creative_id)
        await db.execute(f"UPDATE creative_variants SET {', '.join(updates)} WHERE id = ${idx}", *values)
    c = await db.fetch_one("SELECT * FROM creative_variants WHERE id = $1", creative_id)
    return _creative_to_response(c)


# ── Domains ──

@router.get("/{campaign_id}/domains")
async def list_domains(campaign_id: str, list_type: Optional[str] = None, user=Depends(get_current_user)):
    db = get_db()
    if list_type:
        domains = await db.fetch_all(
            "SELECT * FROM domain_lists WHERE (campaign_id = $1 OR campaign_archetype_id IN "
            "(SELECT id FROM campaign_archetypes WHERE campaign_id = $1)) AND list_type = $2 ORDER BY tier, domain",
            campaign_id, list_type,
        )
    else:
        domains = await db.fetch_all(
            "SELECT * FROM domain_lists WHERE campaign_id = $1 OR campaign_archetype_id IN "
            "(SELECT id FROM campaign_archetypes WHERE campaign_id = $1) ORDER BY list_type, tier, domain",
            campaign_id,
        )
    return [_domain_to_response(d) for d in domains]


@router.post("/{campaign_id}/archetypes/{arch_id}/domains", status_code=201)
async def add_domain(campaign_id: str, arch_id: str, req: DomainCreate, user=Depends(require_admin)):
    db = get_db()
    domain_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO domain_lists (id, campaign_archetype_id, campaign_id, list_type, domain, audience, tier, source, added_by) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        domain_id, arch_id, campaign_id, req.list_type, req.domain,
        req.audience, req.tier, req.source, str(user["id"]),
    )
    return {"id": domain_id, "status": "added"}


@router.post("/{campaign_id}/archetypes/{arch_id}/domains/bulk", status_code=201)
async def bulk_add_domains(campaign_id: str, arch_id: str, req: DomainBulkCreate, user=Depends(require_admin)):
    db = get_db()
    added = 0
    for domain in req.domains:
        domain_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO domain_lists (id, campaign_archetype_id, campaign_id, list_type, domain, tier, added_by) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            domain_id, arch_id, campaign_id, req.list_type, domain.strip(), req.tier, str(user["id"]),
        )
        added += 1
    return {"added": added}


@router.delete("/domains/{domain_id}")
async def remove_domain(domain_id: str, user=Depends(require_admin)):
    db = get_db()
    await db.execute("DELETE FROM domain_lists WHERE id = $1", domain_id)
    return {"status": "deleted"}


# ── DCIL Directives ──

@router.get("/{campaign_id}/directives", response_model=DirectiveList)
async def list_directives(campaign_id: str, status_filter: Optional[str] = None, user=Depends(require_super_admin)):
    db = get_db()
    if status_filter:
        directives = await db.fetch_all(
            "SELECT * FROM dcil_directives WHERE campaign_id = $1 AND status = $2 ORDER BY created_at DESC",
            campaign_id, status_filter,
        )
    else:
        directives = await db.fetch_all(
            "SELECT * FROM dcil_directives WHERE campaign_id = $1 ORDER BY created_at DESC", campaign_id,
        )

    responses = [_directive_to_response(d) for d in directives]
    pending = sum(1 for d in responses if d.status == "proposed")
    approved = sum(1 for d in responses if d.status == "approved")
    executed = sum(1 for d in responses if d.status == "executed")

    return DirectiveList(directives=responses, total=len(responses), pending=pending, approved=approved, executed=executed)


@router.post("/directives/{directive_id}/approve")
async def approve_directive(directive_id: str, req: DirectiveApprove, user=Depends(require_super_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))
    await db.execute(
        "UPDATE dcil_directives SET status = 'approved', reviewed_by = $1, reviewed_at = $2, review_notes = $3, updated_at = $4 WHERE id = $5",
        str(user["id"]), now, req.review_notes, now, directive_id,
    )
    return {"status": "approved", "directive_id": directive_id}


@router.post("/directives/{directive_id}/block")
async def block_directive(directive_id: str, req: DirectiveBlock, user=Depends(require_super_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))
    await db.execute(
        "UPDATE dcil_directives SET status = 'blocked', reviewed_by = $1, reviewed_at = $2, review_notes = $3, updated_at = $4 WHERE id = $5",
        str(user["id"]), now, req.review_notes, now, directive_id,
    )
    return {"status": "blocked", "directive_id": directive_id}


@router.post("/directives/{directive_id}/rollback")
async def rollback_directive(directive_id: str, user=Depends(require_super_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))
    await db.execute(
        "UPDATE dcil_directives SET status = 'rolled_back', rolled_back_at = $1, rollback_reason = 'manual', updated_at = $2 WHERE id = $3",
        now, now, directive_id,
    )
    return {"status": "rolled_back", "directive_id": directive_id}


# ── DCIL Status ──

@router.get("/{campaign_id}/dcil/status", response_model=DCILStatus)
async def dcil_status(campaign_id: str, user=Depends(require_super_admin)):
    db = get_db()
    c = await db.fetch_one("SELECT dcil_enabled, dcil_auto_execute, dcil_safety_rails FROM campaigns WHERE id = $1", campaign_id)
    if not c:
        raise HTTPException(status_code=404)

    pending = await db.fetch_one("SELECT COUNT(*) as cnt FROM dcil_directives WHERE campaign_id = $1 AND status = 'proposed'", campaign_id)
    executed = await db.fetch_one("SELECT COUNT(*) as cnt FROM dcil_directives WHERE campaign_id = $1 AND status = 'executed' AND DATE(created_at) = DATE('now')", campaign_id)
    rolled = await db.fetch_one("SELECT COUNT(*) as cnt FROM dcil_directives WHERE campaign_id = $1 AND status = 'rolled_back' AND DATE(created_at) = DATE('now')", campaign_id)

    safety = json.loads(c.get("dcil_safety_rails", "{}")) if isinstance(c.get("dcil_safety_rails"), str) else c.get("dcil_safety_rails", {})

    return DCILStatus(
        campaign_id=campaign_id,
        dcil_enabled=bool(c.get("dcil_enabled", True)),
        auto_execute=bool(c.get("dcil_auto_execute", False)),
        pending_directives=pending["cnt"] if pending else 0,
        executed_today=executed["cnt"] if executed else 0,
        rolled_back_today=rolled["cnt"] if rolled else 0,
        safety_rails=safety,
    )


# ── Reports ──

@router.get("/{campaign_id}/reports", response_model=ReportList)
async def list_reports(campaign_id: str, tier: Optional[str] = None, user=Depends(get_current_user)):
    db = get_db()
    org_filter = get_org_filter(user)

    if tier:
        if org_filter and tier != "tier_a":
            raise HTTPException(status_code=403, detail="Client users can only view Tier A reports")
        reports = await db.fetch_all(
            "SELECT * FROM reports WHERE campaign_id = $1 AND tier = $2 ORDER BY period_end DESC",
            campaign_id, tier,
        )
    else:
        if org_filter:
            reports = await db.fetch_all(
                "SELECT * FROM reports WHERE campaign_id = $1 AND tier = 'tier_a' ORDER BY period_end DESC",
                campaign_id,
            )
        else:
            reports = await db.fetch_all(
                "SELECT * FROM reports WHERE campaign_id = $1 ORDER BY tier, period_end DESC",
                campaign_id,
            )

    return ReportList(
        reports=[_report_to_response(r) for r in reports],
        total=len(reports),
    )


# ── Performance ──

@router.get("/{campaign_id}/performance")
async def get_performance(campaign_id: str, user=Depends(get_current_user)):
    db = get_db()
    snap = await db.fetch_one(
        "SELECT * FROM campaign_performance_snapshots WHERE campaign_id = $1 ORDER BY snapshot_date DESC LIMIT 1",
        campaign_id,
    )
    if not snap:
        return {"campaign_id": campaign_id, "message": "No performance data yet"}
    return _perf_to_response(snap)


@router.get("/{campaign_id}/performance/history")
async def get_performance_history(campaign_id: str, days: int = Query(30, ge=1, le=365), user=Depends(get_current_user)):
    db = get_db()
    snaps = await db.fetch_all(
        "SELECT * FROM campaign_performance_snapshots WHERE campaign_id = $1 ORDER BY snapshot_date DESC LIMIT $2",
        campaign_id, days,
    )
    return [_perf_to_response(s) for s in snaps]


# ── Conversion Trackers ──

@router.get("/{campaign_id}/trackers")
async def list_trackers(campaign_id: str, user=Depends(get_current_user)):
    db = get_db()
    trackers = await db.fetch_all("SELECT * FROM conversion_trackers WHERE campaign_id = $1", campaign_id)
    return [_tracker_to_response(t) for t in trackers]


@router.post("/{campaign_id}/trackers", response_model=TrackerResponse, status_code=201)
async def create_tracker(campaign_id: str, req: TrackerCreate, user=Depends(require_admin)):
    import secrets
    db = get_db()
    tracker_id = str(uuid.uuid4())
    webhook_secret = secrets.token_hex(32)
    postback_url = f"https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/webhook/conversion"
    pixel_snippet = _generate_pixel_snippet(req.pixel_id or "")

    await db.execute(
        "INSERT INTO conversion_trackers (id, campaign_id, tracker_type, pixel_id, pixel_snippet, postback_url, webhook_secret) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        tracker_id, campaign_id, req.tracker_type, req.pixel_id,
        pixel_snippet, postback_url, webhook_secret,
    )

    t = await db.fetch_one("SELECT * FROM conversion_trackers WHERE id = $1", tracker_id)
    return _tracker_to_response(t)


# ── Helpers ──

def _campaign_to_response(c) -> CampaignResponse:
    return CampaignResponse(
        id=str(c["id"]),
        organization_id=str(c["organization_id"]),
        name=c["name"],
        status=c["status"],
        brand_name=c["brand_name"],
        brand_asin=c.get("brand_asin"),
        brand_website=c.get("brand_website"),
        brand_category=c.get("brand_category"),
        brand_logo_url=c.get("brand_logo_url"),
        total_budget=c.get("total_budget"),
        daily_budget=c.get("daily_budget"),
        currency=c.get("currency", "USD"),
        start_date=str(c.get("start_date") or ""),
        end_date=str(c.get("end_date") or ""),
        timezone=c.get("timezone", "America/New_York"),
        geo_targets=json.loads(c.get("geo_targets", "[]")) if isinstance(c.get("geo_targets"), str) else c.get("geo_targets", []),
        frequency_cap=json.loads(c.get("frequency_cap", "{}")) if isinstance(c.get("frequency_cap"), str) else c.get("frequency_cap", {}),
        dayparting=json.loads(c.get("dayparting", "{}")) if isinstance(c.get("dayparting"), str) else c.get("dayparting", {}),
        dsp_platform=c.get("dsp_platform", "stackadapt"),
        dsp_advertiser_id=c.get("dsp_advertiser_id"),
        dcil_enabled=bool(c.get("dcil_enabled", True)),
        dcil_auto_execute=bool(c.get("dcil_auto_execute", False)),
        dcil_safety_rails=json.loads(c.get("dcil_safety_rails", "{}")) if isinstance(c.get("dcil_safety_rails"), str) else c.get("dcil_safety_rails", {}),
        tier_a_frequency=c.get("tier_a_frequency", "adaptive"),
        conversion_pixel_id=c.get("conversion_pixel_id"),
        conversion_type=c.get("conversion_type", "purchase"),
        conversion_value=c.get("conversion_value"),
        attribution_window_days=c.get("attribution_window_days", 30),
        notes=c.get("notes"),
        created_by=str(c.get("created_by") or ""),
        created_at=str(c["created_at"]),
        updated_at=str(c["updated_at"]),
    )


def _archetype_to_response(a) -> ArchetypeResponse:
    return ArchetypeResponse(
        id=str(a["id"]),
        campaign_id=str(a["campaign_id"]),
        archetype_name=a["archetype_name"],
        is_custom=bool(a.get("is_custom", False)),
        budget_weight=float(a.get("budget_weight", 0)),
        primary_mechanism=a.get("primary_mechanism"),
        secondary_mechanism=a.get("secondary_mechanism"),
        framing=a.get("framing", "gain"),
        notes=a.get("notes"),
        dsp_campaign_id=a.get("dsp_campaign_id"),
        dsp_campaign_status=a.get("dsp_campaign_status"),
        created_at=str(a["created_at"]),
        updated_at=str(a["updated_at"]),
    )


def _creative_to_response(c) -> CreativeResponse:
    return CreativeResponse(
        id=str(c["id"]),
        campaign_archetype_id=str(c["campaign_archetype_id"]),
        variant_label=c["variant_label"],
        mechanism=c["mechanism"],
        headline=c["headline"],
        body_copy=c.get("body_copy"),
        cta_text=c.get("cta_text"),
        image_url=c.get("image_url"),
        landing_url=c.get("landing_url"),
        tone=c.get("tone"),
        construal_level=c.get("construal_level"),
        status=c.get("status", "draft"),
        dsp_creative_id=c.get("dsp_creative_id"),
        impressions=c.get("impressions", 0),
        clicks=c.get("clicks", 0),
        conversions=c.get("conversions", 0),
        spend=float(c.get("spend", 0)),
        ctr=float(c.get("ctr", 0)),
        cvr=float(c.get("cvr", 0)),
        cpa=float(c.get("cpa", 0)),
        created_at=str(c["created_at"]),
        updated_at=str(c["updated_at"]),
    )


def _domain_to_response(d) -> DomainResponse:
    return DomainResponse(
        id=str(d["id"]),
        campaign_archetype_id=str(d.get("campaign_archetype_id") or ""),
        campaign_id=str(d.get("campaign_id") or ""),
        list_type=d["list_type"],
        domain=d["domain"],
        audience=d.get("audience"),
        tier=d.get("tier", 2),
        source=d.get("source", "manual"),
        added_by=str(d.get("added_by") or ""),
        added_at=str(d["added_at"]),
    )


def _directive_to_response(d) -> DirectiveResponse:
    return DirectiveResponse(
        id=str(d["id"]),
        campaign_id=str(d["campaign_id"]),
        directive_type=d["directive_type"],
        status=d["status"],
        campaign_archetype_id=str(d.get("campaign_archetype_id") or ""),
        parameter=d.get("parameter"),
        current_value=json.loads(d["current_value"]) if isinstance(d.get("current_value"), str) else d.get("current_value"),
        proposed_value=json.loads(d["proposed_value"]) if isinstance(d.get("proposed_value"), str) else d.get("proposed_value"),
        source_finding_id=d.get("source_finding_id"),
        rationale=d.get("rationale"),
        bilateral_evidence=d.get("bilateral_evidence"),
        scope=d.get("scope"),
        i_squared=float(d["i_squared"]) if d.get("i_squared") else None,
        confidence=float(d["confidence"]) if d.get("confidence") else None,
        expected_impact=d.get("expected_impact"),
        expected_lift_pct=float(d["expected_lift_pct"]) if d.get("expected_lift_pct") else None,
        rollback_conditions=json.loads(d.get("rollback_conditions", "[]")) if isinstance(d.get("rollback_conditions"), str) else d.get("rollback_conditions", []),
        reviewed_by=str(d.get("reviewed_by") or ""),
        reviewed_at=str(d.get("reviewed_at") or ""),
        review_notes=d.get("review_notes"),
        executed_at=str(d.get("executed_at") or ""),
        execution_result=d.get("execution_result"),
        rolled_back_at=str(d.get("rolled_back_at") or ""),
        rollback_reason=d.get("rollback_reason"),
        created_at=str(d["created_at"]),
        updated_at=str(d["updated_at"]),
    )


def _report_to_response(r) -> ReportResponse:
    return ReportResponse(
        id=str(r["id"]),
        campaign_id=str(r["campaign_id"]),
        organization_id=str(r["organization_id"]),
        tier=r["tier"],
        period_start=str(r["period_start"]),
        period_end=str(r["period_end"]),
        report_data=json.loads(r["report_data"]) if isinstance(r.get("report_data"), str) else r.get("report_data", {}),
        generated_at=str(r["generated_at"]),
        generated_by=r.get("generated_by", "dcil"),
        viewed_by_client=bool(r.get("viewed_by_client", False)),
        viewed_at=str(r.get("viewed_at") or ""),
    )


def _perf_to_response(s) -> CampaignPerformance:
    return CampaignPerformance(
        campaign_id=str(s["campaign_id"]),
        snapshot_date=str(s["snapshot_date"]),
        impressions=s.get("impressions", 0),
        clicks=s.get("clicks", 0),
        conversions=s.get("conversions", 0),
        spend=float(s.get("spend", 0)),
        revenue=float(s.get("revenue", 0)),
        ctr=float(s.get("ctr", 0)),
        cvr=float(s.get("cvr", 0)),
        cpa=float(s.get("cpa", 0)),
        roas=float(s.get("roas", 0)),
        archetype_breakdown=json.loads(s.get("archetype_breakdown", "{}")) if isinstance(s.get("archetype_breakdown"), str) else s.get("archetype_breakdown", {}),
        domain_breakdown=json.loads(s.get("domain_breakdown", "{}")) if isinstance(s.get("domain_breakdown"), str) else s.get("domain_breakdown", {}),
    )


def _tracker_to_response(t) -> TrackerResponse:
    return TrackerResponse(
        id=str(t["id"]),
        campaign_id=str(t["campaign_id"]),
        tracker_type=t["tracker_type"],
        pixel_id=t.get("pixel_id"),
        pixel_snippet=t.get("pixel_snippet"),
        postback_url=t.get("postback_url"),
        webhook_secret=t.get("webhook_secret"),
        is_verified=bool(t.get("is_verified", False)),
        verified_at=str(t.get("verified_at") or ""),
        events_received=t.get("events_received", 0),
        last_event_at=str(t.get("last_event_at") or ""),
        created_at=str(t["created_at"]),
    )


def _generate_pixel_snippet(pixel_id: str) -> str:
    return f"""<script>
!function(s,a,e,v,n,t,z){{if(s.saq)return;n=s.saq=function(){{
n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!s._saq)s._saq=n;n.push=n;n.loaded=!0;n.version='1.0';n.queue=[];
t=a.createElement(e);t.async=!0;t.src=v;z=a.getElementsByTagName(e)[0];
z.parentNode.insertBefore(t,z)}}(window,document,'script',
'https://tags.srv.stackadapt.com/events.js');
saq('ts', '{pixel_id}');
</script>"""
