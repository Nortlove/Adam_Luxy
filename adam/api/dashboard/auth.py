"""Dashboard authentication — v1 single-user Bearer token.

Phase A pilot uses a single hard-coded user identified by an
env-configured Bearer token. When Phase C multi-tenancy lands this
module is replaced with a proper SSO flow and per-session user
resolution — nothing outside this file should depend on the shape of
auth directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class DashboardUser:
    id: str
    email: str
    display_name: str
    role: str


def _expected_token() -> Optional[str]:
    """Return the configured dashboard token, or None if unset (dev mode)."""
    return os.environ.get("INFORMATIV_DASHBOARD_TOKEN")


async def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> DashboardUser:
    """FastAPI dependency that validates the dashboard Bearer token.

    When INFORMATIV_DASHBOARD_TOKEN is unset, auth is disabled (dev
    mode) and the request is accepted as the default single-tenant
    user. When the env var is set, the Authorization header must match.
    """

    expected = _expected_token()
    if expected:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if credentials.credentials != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid dashboard token",
            )

    return DashboardUser(
        id=os.environ.get("INFORMATIV_USER_ID", "user:chris"),
        email=os.environ.get("INFORMATIV_USER_EMAIL", "chris@informativgroup.com"),
        display_name=os.environ.get("INFORMATIV_USER_NAME", "Chris Nocera"),
        role="superadmin",
    )
