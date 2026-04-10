# =============================================================================
# ADAM Demo - Modular Routers
# =============================================================================

"""
Modular API routers for the ADAM demonstration platform.

This module exports all router modules for easy aggregation in the main API.

Structure:
    - core.py: Status, health, recommend, archetypes (IMPLEMENTED)
    - learning.py: Learning system and statistics (STUB)
    - learned_priors.py: Learned priors and intelligence (STUB)
    - campaign.py: Campaign analysis and scenarios (STUB)
    - reviews.py: Review intelligence (STUB)
    - framework82.py: 82-framework analysis (STUB)
    - categories.py: Category management (STUB)
    - brands.py: Brand analysis (STUB)
    - feedback.py: Feedback and outcomes (STUB)
    - customer_types.py: Customer type analysis (STUB)
    - integration.py: Pipeline and integration status (STUB)

Note: Most endpoints are still in the main api.py file for backward compatibility.
The router structure is in place for gradual migration.
"""

import logging

logger = logging.getLogger(__name__)

# Import routers - these are stubs for now, real endpoints are in api.py
try:
    from adam.demo.routers.core import router as core_router
except ImportError as e:
    logger.warning(f"Could not import core_router: {e}")
    core_router = None

try:
    from adam.demo.routers.learning import router as learning_router
except ImportError as e:
    logger.warning(f"Could not import learning_router: {e}")
    learning_router = None

try:
    from adam.demo.routers.learned_priors import router as learned_priors_router
except ImportError as e:
    logger.warning(f"Could not import learned_priors_router: {e}")
    learned_priors_router = None

try:
    from adam.demo.routers.campaign import router as campaign_router
except ImportError as e:
    logger.warning(f"Could not import campaign_router: {e}")
    campaign_router = None

try:
    from adam.demo.routers.reviews import router as reviews_router
except ImportError as e:
    logger.warning(f"Could not import reviews_router: {e}")
    reviews_router = None

try:
    from adam.demo.routers.framework82 import router as framework82_router
except ImportError as e:
    logger.warning(f"Could not import framework82_router: {e}")
    framework82_router = None

try:
    from adam.demo.routers.categories import router as categories_router
except ImportError as e:
    logger.warning(f"Could not import categories_router: {e}")
    categories_router = None

try:
    from adam.demo.routers.brands import router as brands_router
except ImportError as e:
    logger.warning(f"Could not import brands_router: {e}")
    brands_router = None

try:
    from adam.demo.routers.feedback import router as feedback_router
except ImportError as e:
    logger.warning(f"Could not import feedback_router: {e}")
    feedback_router = None

try:
    from adam.demo.routers.customer_types import router as customer_types_router
except ImportError as e:
    logger.warning(f"Could not import customer_types_router: {e}")
    customer_types_router = None

try:
    from adam.demo.routers.integration import router as integration_router
except ImportError as e:
    logger.warning(f"Could not import integration_router: {e}")
    integration_router = None


__all__ = [
    "core_router",
    "learning_router",
    "learned_priors_router",
    "campaign_router",
    "reviews_router",
    "framework82_router",
    "categories_router",
    "brands_router",
    "feedback_router",
    "customer_types_router",
    "integration_router",
    "get_all_routers",
]


def get_all_routers():
    """
    Get all routers for inclusion in the main API.
    
    Returns a list of (router, prefix, tags) tuples.
    Only returns routers that were successfully imported.
    """
    routers = []
    
    router_configs = [
        (core_router, "", ["Core"]),
        (learning_router, "", ["Learning"]),
        (learned_priors_router, "", ["Learned Priors"]),
        (campaign_router, "", ["Campaign Analysis"]),
        (reviews_router, "", ["Review Intelligence"]),
        (framework82_router, "", ["Framework-82"]),
        (categories_router, "", ["Categories"]),
        (brands_router, "", ["Brands"]),
        (feedback_router, "", ["Feedback"]),
        (customer_types_router, "", ["Customer Types"]),
        (integration_router, "", ["Integration"]),
    ]
    
    for router, prefix, tags in router_configs:
        if router is not None:
            routers.append((router, prefix, tags))
    
    return routers
