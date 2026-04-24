"""
Organization Router — /api/v2/admin/organizations/*
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from adam.api.admin.db import get_db
from adam.api.admin.dependencies import require_super_admin
from adam.api.admin.models.organization import (
    OrganizationCreate,
    OrganizationList,
    OrganizationResponse,
    OrganizationUpdate,
)
from adam.api.admin.models.user import UserCreate, UserResponse
from adam.api.admin.auth import hash_password

router = APIRouter(prefix="/api/v2/admin/organizations", tags=["organizations"])


@router.get("", response_model=OrganizationList)
async def list_organizations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str = Query("active", alias="status"),
    user=Depends(require_super_admin),
):
    db = get_db()
    offset = (page - 1) * per_page

    orgs = await db.fetch_all(
        "SELECT * FROM organizations WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        status_filter, per_page, offset,
    )

    total_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM organizations WHERE status = $1", status_filter,
    )
    total = total_row["cnt"] if total_row else 0

    responses = []
    for o in orgs:
        camp_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM campaigns WHERE organization_id = $1", str(o["id"]),
        )
        user_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM users WHERE organization_id = $1", str(o["id"]),
        )
        responses.append(OrganizationResponse(
            id=str(o["id"]),
            name=o["name"],
            slug=o["slug"],
            domain=o.get("domain"),
            industry=o.get("industry"),
            tier=o.get("tier", "standard"),
            status=o.get("status", "active"),
            settings_json=json.loads(o.get("settings_json", "{}")) if isinstance(o.get("settings_json"), str) else o.get("settings_json", {}),
            created_at=str(o["created_at"]),
            updated_at=str(o["updated_at"]),
            campaign_count=camp_count["cnt"] if camp_count else 0,
            user_count=user_count["cnt"] if user_count else 0,
        ))

    return OrganizationList(organizations=responses, total=total, page=page, per_page=per_page)


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(req: OrganizationCreate, user=Depends(require_super_admin)):
    db = get_db()
    org_id = str(uuid.uuid4())
    now = str(datetime.now(timezone.utc))

    await db.execute(
        "INSERT INTO organizations (id, name, slug, domain, industry, tier, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        org_id, req.name, req.slug, req.domain, req.industry, req.tier, now, now,
    )

    return OrganizationResponse(
        id=org_id, name=req.name, slug=req.slug, domain=req.domain,
        industry=req.industry, tier=req.tier, status="active",
        created_at=now, updated_at=now,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, user=Depends(require_super_admin)):
    db = get_db()
    o = await db.fetch_one("SELECT * FROM organizations WHERE id = $1", org_id)
    if not o:
        raise HTTPException(status_code=404, detail="Organization not found")

    camp_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM campaigns WHERE organization_id = $1", org_id)
    user_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM users WHERE organization_id = $1", org_id)

    return OrganizationResponse(
        id=str(o["id"]), name=o["name"], slug=o["slug"], domain=o.get("domain"),
        industry=o.get("industry"), tier=o.get("tier", "standard"),
        status=o.get("status", "active"),
        settings_json=json.loads(o.get("settings_json", "{}")) if isinstance(o.get("settings_json"), str) else o.get("settings_json", {}),
        created_at=str(o["created_at"]), updated_at=str(o["updated_at"]),
        campaign_count=camp_count["cnt"] if camp_count else 0,
        user_count=user_count["cnt"] if user_count else 0,
    )


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(org_id: str, req: OrganizationUpdate, user=Depends(require_super_admin)):
    db = get_db()
    now = str(datetime.now(timezone.utc))

    updates = []
    values = []
    idx = 1
    for field in ["name", "domain", "industry", "tier", "status"]:
        val = getattr(req, field, None)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            values.append(val)
            idx += 1

    if req.settings_json is not None:
        updates.append(f"settings_json = ${idx}")
        values.append(json.dumps(req.settings_json))
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append(f"updated_at = ${idx}")
    values.append(now)
    idx += 1
    values.append(org_id)

    await db.execute(
        f"UPDATE organizations SET {', '.join(updates)} WHERE id = ${idx}",
        *values,
    )

    return await get_organization(org_id, user)


@router.delete("/{org_id}")
async def delete_organization(org_id: str, user=Depends(require_super_admin)):
    db = get_db()
    await db.execute("UPDATE organizations SET status = 'churned', updated_at = $1 WHERE id = $2",
                     str(datetime.now(timezone.utc)), org_id)
    return {"status": "archived"}


# --- Users within org ---

@router.get("/{org_id}/users")
async def list_org_users(org_id: str, user=Depends(require_super_admin)):
    db = get_db()
    users = await db.fetch_all(
        "SELECT id, email, full_name, role, is_active, last_login_at, created_at FROM users WHERE organization_id = $1",
        org_id,
    )
    return [UserResponse(
        id=str(u["id"]), email=u["email"], full_name=u["full_name"],
        role=u["role"], organization_id=org_id,
        is_active=bool(u.get("is_active", True)),
        last_login_at=str(u.get("last_login_at") or ""),
        created_at=str(u["created_at"]),
    ) for u in users]


@router.post("/{org_id}/users", response_model=UserResponse, status_code=201)
async def create_org_user(org_id: str, req: UserCreate, user=Depends(require_super_admin)):
    db = get_db()
    user_id = str(uuid.uuid4())
    now = str(datetime.now(timezone.utc))
    pw_hash = hash_password(req.password)

    await db.execute(
        "INSERT INTO users (id, organization_id, email, password_hash, full_name, role, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        user_id, org_id, req.email, pw_hash, req.full_name, req.role, now, now,
    )

    return UserResponse(
        id=user_id, email=req.email, full_name=req.full_name,
        role=req.role, organization_id=org_id, created_at=now,
    )
