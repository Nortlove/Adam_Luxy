# =============================================================================
# ADAM Behavioral Analytics: API Module
# Location: adam/behavioral_analytics/api/__init__.py
# =============================================================================

"""
BEHAVIORAL ANALYTICS API

FastAPI router for behavioral analytics endpoints.

Endpoints:
- POST /api/v1/behavioral/event - Record single event
- POST /api/v1/behavioral/session - Analyze complete session
- POST /api/v1/behavioral/outcome - Record outcome for learning
- GET /api/v1/behavioral/knowledge/{construct} - Get knowledge for construct
- GET /api/v1/behavioral/knowledge - Get all research knowledge
- GET /api/v1/behavioral/hypotheses - Get active hypotheses
- POST /api/v1/behavioral/hypotheses/{id}/promote - Promote to knowledge
- GET /api/v1/behavioral/profiles/{user_id} - Get behavioral profile
- GET /api/v1/behavioral/drift - Get drift status
- GET /api/v1/behavioral/health - Get service health
"""

from adam.behavioral_analytics.api.router import router

__all__ = ["router"]
