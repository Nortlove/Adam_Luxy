"""Pilot bootstrap — populates management DB with the rows DCIL Loop β requires.

DCIL Loop β closes when an operator approves a directive in the dashboard
and the directive's status flips to APPROVED in the `dcil_directives` table.
That flow has three structural prerequisites the management DB must satisfy
on a fresh deployment:

  1. An organization row (FK target for `campaigns.organization_id`)
  2. A user row (referenced as `created_by` on auto-created campaigns)
  3. Campaign rows matching the StackAdapt campaign IDs that DCIL writes
     directives against (FK target for `dcil_directives.campaign_id`)

Without these, every directive insert fails the FK gate; the operator
queue stays empty for DCIL source even when the upstream pipeline runs.

This module is idempotent: each step is a no-op when the target row(s)
already exist. It runs once at startup (called from main.py lifespan)
when:
  - DB pool is initialized
  - `STACKADAPT_GRAPHQL_KEY` is configured (otherwise the campaign sync
    has no upstream to read from)

Failure modes are all soft: missing StackAdapt access, transient DB
issues, or already-populated state all degrade gracefully without
blocking server startup. The bootstrap reports a summary dict back
to the lifespan handler for log visibility.

Direction-agnostic vs DCIL scope question:
The campaigns + organization + user rows are tenant infrastructure
independent of DCIL upstream. Whether DCIL stays as the directive
generator or is later replaced by MRT-WCLS findings (per Doc 3 §I.1),
the operator-facing surface still needs `campaigns(id)` rows for any
directive to land. This bootstrap is therefore safe to run regardless
of the eventual DCIL-keep-vs-phase-out decision.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


_PILOT_ORG_NAME = "INFORMATIV"
_PILOT_ORG_SLUG = "informativ"
_PILOT_ORG_DOMAIN = "informativ.co"
_PILOT_USER_EMAIL = "system@informativ.co"
_PILOT_USER_FULL_NAME = "Pilot System User"


async def bootstrap_pilot_data() -> Dict[str, Any]:
    """Idempotent pilot data bootstrap.

    Returns a summary dict describing what was created vs what already
    existed. Safe to call repeatedly — each step short-circuits when the
    target row(s) exist.

    Returns:
        {
          "organization": {"created": bool, "id": str},
          "user": {"created": bool, "id": str},
          "campaigns": {"created": int, "skipped": int, "total": int},
          "skipped_reason": Optional[str],  # set when bootstrap deferred
        }
    """
    summary: Dict[str, Any] = {
        "organization": {"created": False, "id": None},
        "user": {"created": False, "id": None},
        "campaigns": {"created": 0, "skipped": 0, "total": 0},
        "skipped_reason": None,
    }

    # Defer when prerequisites missing — these are not error states,
    # they're "not configured for pilot bootstrap" states.
    if not os.environ.get("STACKADAPT_GRAPHQL_KEY"):
        summary["skipped_reason"] = "STACKADAPT_GRAPHQL_KEY not set"
        logger.info("pilot_bootstrap: skipped (%s)", summary["skipped_reason"])
        return summary

    try:
        from adam.api.admin.db import get_db, get_pool
        await get_pool()
        db = get_db()
    except Exception as exc:
        summary["skipped_reason"] = f"DB unavailable: {exc}"
        logger.warning("pilot_bootstrap: skipped (%s)", summary["skipped_reason"])
        return summary

    # 1. Organization
    try:
        org_id, org_was_created = await _ensure_organization(db)
        summary["organization"]["id"] = org_id
        summary["organization"]["created"] = org_was_created
    except Exception as exc:
        logger.warning("pilot_bootstrap: organization step failed: %s", exc)
        summary["skipped_reason"] = f"organization step: {exc}"
        return summary

    # 2. User
    try:
        user_id, user_was_created = await _ensure_pilot_user(db, org_id)
        summary["user"]["id"] = user_id
        summary["user"]["created"] = user_was_created
    except Exception as exc:
        logger.warning("pilot_bootstrap: user step failed: %s", exc)
        summary["skipped_reason"] = f"user step: {exc}"
        return summary

    # 3. Campaigns — pull live from StackAdapt and upsert
    try:
        from adam.api.dashboard.service import fetch_stackadapt_summary
        stackadapt_summary = await fetch_stackadapt_summary()
    except Exception as exc:
        logger.warning("pilot_bootstrap: StackAdapt fetch failed: %s", exc)
        summary["skipped_reason"] = f"StackAdapt fetch: {exc}"
        return summary

    if stackadapt_summary.source != "live":
        summary["skipped_reason"] = (
            f"StackAdapt source={stackadapt_summary.source} "
            f"(reason: {stackadapt_summary.reason})"
        )
        logger.info("pilot_bootstrap: campaign sync skipped (%s)", summary["skipped_reason"])
        return summary

    advertiser_name = stackadapt_summary.advertiser_name or "Unknown Advertiser"
    summary["campaigns"]["total"] = len(stackadapt_summary.campaigns)

    for sa_campaign in stackadapt_summary.campaigns:
        try:
            existed = await _ensure_campaign(
                db,
                stackadapt_id=sa_campaign.id,
                name=sa_campaign.name,
                org_id=org_id,
                user_id=user_id,
                advertiser_name=advertiser_name,
                channel_type=sa_campaign.channel_type,
                status=sa_campaign.status,
            )
            if existed:
                summary["campaigns"]["skipped"] += 1
            else:
                summary["campaigns"]["created"] += 1
        except Exception as exc:
            logger.warning(
                "pilot_bootstrap: campaign upsert failed for %s: %s",
                sa_campaign.id, exc,
            )

    logger.info(
        "pilot_bootstrap complete: org=%s, user=%s, campaigns=%d created / %d skipped / %d total",
        summary["organization"]["id"],
        summary["user"]["id"],
        summary["campaigns"]["created"],
        summary["campaigns"]["skipped"],
        summary["campaigns"]["total"],
    )
    return summary


async def _ensure_organization(db: Any) -> tuple[str, bool]:
    """Idempotent INFORMATIV organization MERGE.

    Returns (org_id, was_created). was_created=True iff this call
    inserted the row; False iff a matching slug already existed.
    """
    existing = await db.fetch_one(
        "SELECT id FROM organizations WHERE slug = $1", _PILOT_ORG_SLUG,
    )
    if existing:
        return existing["id"], False

    org_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO organizations (id, name, slug, domain, industry, tier, "
        "created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, datetime('now'), datetime('now'))",
        org_id, _PILOT_ORG_NAME, _PILOT_ORG_SLUG, _PILOT_ORG_DOMAIN,
        "advertising", "pilot",
    )
    return org_id, True


async def _ensure_pilot_user(db: Any, org_id: str) -> tuple[str, bool]:
    """Idempotent pilot system user MERGE.

    Returns (user_id, was_created). The pilot system user is the
    `created_by` for auto-bootstrapped campaign rows. It is NOT an
    authentication target — the operator's actual user is created
    separately via 002_seed_super_admin.
    """
    existing = await db.fetch_one(
        "SELECT id FROM users WHERE email = $1", _PILOT_USER_EMAIL,
    )
    if existing:
        return existing["id"], False

    user_id = str(uuid.uuid4())
    # No password hash — this user cannot log in. Sentinel value flagged
    # so any auth path that attempts to verify it sees a non-bcrypt string
    # and refuses immediately.
    sentinel_hash = "DISABLED:pilot_system_user_no_login"
    await db.execute(
        "INSERT INTO users (id, organization_id, email, password_hash, "
        "full_name, role, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, datetime('now'), datetime('now'))",
        user_id, org_id, _PILOT_USER_EMAIL, sentinel_hash,
        _PILOT_USER_FULL_NAME, "system",
    )
    return user_id, True


async def _ensure_campaign(
    db: Any,
    stackadapt_id: str,
    name: str,
    org_id: str,
    user_id: str,
    advertiser_name: str,
    channel_type: Optional[str],
    status: Optional[str],
) -> bool:
    """Idempotent campaign upsert keyed on the StackAdapt campaign id.

    Returns True if the row already existed, False if newly inserted.
    The StackAdapt id is stored as the management.campaigns.id for
    direct join-ability — DCIL writes directives keyed on the same
    StackAdapt id, so the FK resolves naturally.
    """
    existing = await db.fetch_one(
        "SELECT id FROM campaigns WHERE id = $1", stackadapt_id,
    )
    if existing:
        return True

    # Map StackAdapt campaign status to management campaign status.
    sa_status = (status or "").upper()
    mgmt_status = "active" if sa_status == "ACTIVE" else "paused"

    await db.execute(
        "INSERT INTO campaigns (id, organization_id, name, status, "
        "brand_name, dsp_platform, dsp_advertiser_id, "
        "created_by, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, "
        "datetime('now'), datetime('now'))",
        stackadapt_id, org_id, name, mgmt_status,
        advertiser_name, "stackadapt", stackadapt_id,
        user_id,
    )
    return False
