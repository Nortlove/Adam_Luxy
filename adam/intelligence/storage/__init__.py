# =============================================================================
# Intelligence Storage Module
# Location: adam/intelligence/storage/__init__.py
# =============================================================================

"""
Storage module for persistent psychological intelligence.

This module provides SQLite-based storage for:
- Unified psychological profiles
- Flow state analysis results
- Psychological needs
- Psycholinguistic constructs
- Ad recommendations with outcome tracking
- Learning signals for continuous improvement
"""

from adam.intelligence.storage.insight_storage import (
    InsightStorageService,
    get_insight_storage,
    reset_insight_storage,
)

__all__ = [
    "InsightStorageService",
    "get_insight_storage",
    "reset_insight_storage",
]
