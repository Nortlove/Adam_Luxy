"""
FastAPI middleware for tenant identification and API key validation.

Follows ADAM's existing CORS middleware pattern from adam/main.py.
Integrates with the TenantService to resolve API keys to tenants.
"""

from __future__ import annotations

import hashlib
import logging
import time
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_current_tenant: ContextVar[Optional[str]] = ContextVar("current_tenant", default=None)
_current_tenant_config: ContextVar[Optional[dict]] = ContextVar("current_tenant_config", default=None)


def get_current_tenant() -> Optional[str]:
    """Retrieve the current tenant_id from the request context."""
    return _current_tenant.get()


def get_current_tenant_config() -> Optional[dict]:
    return _current_tenant_config.get()


PUBLIC_PREFIXES = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
    "/api/v1/tenants/register",
    "/api/v1/tenants/blueprints",
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts API key from X-API-Key header, resolves to tenant, sets context.

    Public endpoints (health, docs, registration) are exempt.
    Tenant-scoped endpoints receive tenant_id injected into request state.
    """

    def __init__(self, app, tenant_service=None, api_key_header: str = "X-API-Key"):
        super().__init__(app)
        self._tenant_service = tenant_service
        self._api_key_header = api_key_header

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        api_key = request.headers.get(self._api_key_header)

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing API key", "hint": f"Include {self._api_key_header} header"},
            )

        if self._tenant_service is None:
            _current_tenant.set(None)
            return await call_next(request)

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        tenant = await self._tenant_service.resolve_by_key(key_hash)

        if tenant is None:
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API key"},
            )

        if tenant.status.value not in ("active", "activating"):
            return JSONResponse(
                status_code=403,
                content={"error": f"Tenant is {tenant.status.value}"},
            )

        token_tenant = _current_tenant.set(tenant.tenant_id)
        token_config = _current_tenant_config.set(tenant.config.model_dump())
        request.state.tenant_id = tenant.tenant_id
        request.state.tenant_config = tenant.config
        request.state.tenant_namespace = tenant.redis_namespace

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _current_tenant.reset(token_tenant)
            _current_tenant_config.reset(token_config)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Tenant-Id"] = tenant.tenant_id
        response.headers["X-Request-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response
