# =============================================================================
# ADAM API Module
# =============================================================================

"""
ADAM API

FastAPI routers for the ADAM platform.
"""

from adam.api.learning_endpoints import router as learning_router
from adam.api.emergence_endpoints import router as emergence_router

__all__ = [
    "learning_router",
    "emergence_router",
]
