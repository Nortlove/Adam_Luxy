# =============================================================================
# ADAM API: Behavioral Signal Collection
# =============================================================================

"""
Behavioral analytics API routers for signal collection.

Routers:
- desktop_router: Desktop implicit signal collection (cursor, keystroke, scroll)
- media_router: Media preference collection
"""

from adam.api.behavioral.desktop_router import router as desktop_router
from adam.api.behavioral.media_router import router as media_router

__all__ = ["desktop_router", "media_router"]
