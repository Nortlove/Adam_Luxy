# =============================================================================
# ADAM Health Check API
# Location: adam/api/health/__init__.py
# =============================================================================

"""
HEALTH CHECK ENDPOINTS

Provides liveness, readiness, and detailed health status endpoints
for Kubernetes probes and monitoring systems.

Endpoints:
- GET /health/live    - Liveness probe (is the process running?)
- GET /health/ready   - Readiness probe (can it accept traffic?)
- GET /health/status  - Detailed component status
"""

from adam.api.health.router import router

__all__ = ["router"]
