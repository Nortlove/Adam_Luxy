"""Pin the pilot bootstrap idempotency + structural invariants.

Discipline anchors:
    - The bootstrap is the single point that ensures DCIL Loop β has the
      FK targets it needs (organizations, users, campaigns). Failing
      these tests means a fresh deployment can't deliver directives to
      the operator queue.
    - Idempotency MUST hold — a second run on a populated DB produces
      no new rows. Failing this means restarts cause duplicate insertions.
    - Soft-fail semantics MUST hold — missing prerequisites (no
      STACKADAPT_GRAPHQL_KEY, DB unavailable, StackAdapt unreachable)
      degrade to a "skipped" return without raising. Server startup
      must not block on bootstrap.
"""

from __future__ import annotations

import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from adam.api.admin.services.pilot_bootstrap import (
    bootstrap_pilot_data,
    _ensure_organization,
    _ensure_pilot_user,
    _ensure_campaign,
    _PILOT_ORG_NAME,
    _PILOT_ORG_SLUG,
    _PILOT_USER_EMAIL,
)


# -----------------------------------------------------------------------------
# Soft-fail tests — bootstrap MUST NOT raise on missing prerequisites.
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skipped_when_no_stackadapt_key(monkeypatch):
    """Without the StackAdapt key, bootstrap returns a skipped summary
    rather than raising. Server startup must not block on this."""
    monkeypatch.delenv("STACKADAPT_GRAPHQL_KEY", raising=False)

    summary = await bootstrap_pilot_data()

    assert summary["skipped_reason"] == "STACKADAPT_GRAPHQL_KEY not set"
    assert summary["organization"]["created"] is False
    assert summary["user"]["created"] is False
    assert summary["campaigns"]["total"] == 0


# -----------------------------------------------------------------------------
# Idempotency tests — second runs MUST be no-ops.
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_organization_idempotent():
    """Existing organization with matching slug → return id, was_created=False."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value={"id": "existing-org-id"})
    db.execute = AsyncMock()

    org_id, was_created = await _ensure_organization(db)

    assert org_id == "existing-org-id"
    assert was_created is False
    # MUST NOT execute another INSERT
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_organization_creates_when_missing():
    """No matching slug → INSERT new row, return id, was_created=True."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()

    org_id, was_created = await _ensure_organization(db)

    assert org_id is not None and len(org_id) > 0
    assert was_created is True
    db.execute.assert_called_once()
    # The slug + name must be the canonical pilot constants
    args = db.execute.await_args.args
    assert _PILOT_ORG_NAME in args
    assert _PILOT_ORG_SLUG in args


@pytest.mark.asyncio
async def test_ensure_pilot_user_idempotent():
    """Existing pilot user → return id, was_created=False."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value={"id": "existing-user-id"})
    db.execute = AsyncMock()

    user_id, was_created = await _ensure_pilot_user(db, org_id="org-1")

    assert user_id == "existing-user-id"
    assert was_created is False
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_pilot_user_creates_with_disabled_password():
    """Newly created pilot user MUST carry a sentinel non-bcrypt
    password_hash so any auth path that examines it refuses immediately
    — the pilot system user is not an authentication target."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()

    user_id, was_created = await _ensure_pilot_user(db, org_id="org-1")

    assert was_created is True
    args = db.execute.await_args.args
    # password_hash is the 4th positional arg in the INSERT call
    password_hash = args[4]
    assert password_hash.startswith("DISABLED:"), (
        "Pilot system user MUST carry a non-bcrypt sentinel hash. Got: "
        f"{password_hash!r}"
    )
    assert _PILOT_USER_EMAIL in args


@pytest.mark.asyncio
async def test_ensure_campaign_idempotent_on_stackadapt_id():
    """Existing campaign row with the StackAdapt id → return existed=True,
    no new INSERT. The StackAdapt id IS the management.campaigns.id —
    that's the join key DCIL writes directives against."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value={"id": "3141825"})
    db.execute = AsyncMock()

    existed = await _ensure_campaign(
        db,
        stackadapt_id="3141825",
        name="ZGM-CTV-Prospecting-CorporateExecutives",
        org_id="org-1",
        user_id="user-1",
        advertiser_name="Luxy Ride",
        channel_type="CTV",
        status="ACTIVE",
    )

    assert existed is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_campaign_inserts_when_missing():
    """New StackAdapt id → INSERT row keyed on the StackAdapt id."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()

    existed = await _ensure_campaign(
        db,
        stackadapt_id="3141825",
        name="ZGM-CTV-Prospecting-CorporateExecutives",
        org_id="org-1",
        user_id="user-1",
        advertiser_name="Luxy Ride",
        channel_type="CTV",
        status="ACTIVE",
    )

    assert existed is False
    db.execute.assert_called_once()
    args = db.execute.await_args.args
    # The first positional arg AFTER the SQL is the campaign id —
    # it MUST be the StackAdapt id (the FK join key DCIL relies on)
    assert "3141825" in args


@pytest.mark.asyncio
async def test_ensure_campaign_maps_active_status():
    """StackAdapt status=ACTIVE maps to management status=active. Other
    StackAdapt statuses map to 'paused' (conservative default)."""
    db = MagicMock()
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()

    await _ensure_campaign(
        db, stackadapt_id="3141825", name="x", org_id="o", user_id="u",
        advertiser_name="a", channel_type="CTV", status="ACTIVE",
    )
    active_args = db.execute.await_args.args
    assert "active" in active_args

    db.execute.reset_mock()
    await _ensure_campaign(
        db, stackadapt_id="3143140", name="y", org_id="o", user_id="u",
        advertiser_name="a", channel_type="CTV", status="PAUSED",
    )
    paused_args = db.execute.await_args.args
    assert "paused" in paused_args
