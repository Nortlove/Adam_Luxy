# =============================================================================
# API Authentication Middleware
# Location: adam/api/auth/middleware.py
# =============================================================================

"""
API key authentication for production endpoints.

When ADAM_API_KEYS is set (comma-separated), all production endpoints
require a valid X-API-Key header. Health, metrics, and docs are exempt.

When ADAM_API_KEYS is empty, auth is disabled (development mode).
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[str]:
    """FastAPI dependency that enforces API key authentication.

    Exempt paths: /health, /metrics, /docs, /openapi.json, /redoc

    Usage:
        @router.get("/decisions", dependencies=[Depends(verify_api_key)])
        async def get_decisions(): ...

    Or applied to entire router:
        app.include_router(router, dependencies=[Depends(verify_api_key)])
    """
    # Exempt paths that should always be accessible
    exempt_prefixes = (
        "/health", "/metrics", "/docs", "/openapi.json", "/redoc",
        "/static",
        "/api/v1/stackadapt/webhook",  # Webhooks use HMAC signature auth, not API key
    )
    if any(request.url.path.startswith(p) for p in exempt_prefixes):
        return None

    from adam.config.settings import get_settings
    valid_keys = get_settings().api.api_key_set

    # If no keys configured, auth is disabled (development mode)
    if not valid_keys:
        return None

    if not api_key:
        logger.warning(
            "Unauthenticated request to %s from %s",
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if api_key not in valid_keys:
        logger.warning(
            "Invalid API key for %s from %s",
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    return api_key
