"""
FastAPI Dependencies for RBAC
================================

Dependency chain:
  get_current_user → require_super_admin / require_org_access / org_filter
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adam.api.admin.auth import decode_access_token
from adam.api.admin.db import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Decode JWT and return user dict. Raises 401 if invalid."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    db = get_db()
    user = await db.fetch_one(
        "SELECT id, email, full_name, role, organization_id, is_active FROM users WHERE id = $1",
        payload["sub"],
    )

    if user is None or not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


async def require_super_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Raise 403 if not super_admin."""
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return user


async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Raise 403 if not super_admin or client_admin."""
    if user.get("role") not in ("super_admin", "client_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_org_filter(user: Dict[str, Any]) -> Optional[str]:
    """Returns org_id to filter by, or None for super_admin (sees all)."""
    if user.get("role") == "super_admin":
        return None
    return user.get("organization_id")


async def verify_org_access(org_id: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Verify user has access to the specified organization."""
    if user.get("role") == "super_admin":
        return user
    if str(user.get("organization_id", "")) != str(org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this organization")
    return user


async def verify_campaign_access(campaign_id: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Verify user has access to the campaign's organization."""
    if user.get("role") == "super_admin":
        return user

    db = get_db()
    campaign = await db.fetch_one(
        "SELECT organization_id FROM campaigns WHERE id = $1", campaign_id,
    )
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if str(campaign["organization_id"]) != str(user.get("organization_id", "")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this campaign")
    return user
