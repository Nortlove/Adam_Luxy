# =============================================================================
# ADAM Amazon Local Data Module
# Location: adam/data/amazon/__init__.py
# =============================================================================

"""
AMAZON LOCAL DATA MODULE

Provides access to the local Amazon review database (1 billion+ reviews).

This module enables:
- Fast brand-based review lookups via SQLite FTS5
- Hierarchical product matching (brand + title + keywords)
- Access to helpful_vote data for persuasive pattern analysis
- Integration with the review orchestrator

Usage:
    from adam.data.amazon import get_amazon_client
    
    client = get_amazon_client()
    await client.initialize()
    
    # Get reviews by brand
    reviews, products = await client.get_reviews_by_brand("Lululemon", limit=100)
    
    # Get reviews for specific product
    reviews = await client.get_reviews_for_product("Lululemon", "Align Pant")
"""

from adam.data.amazon.models import (
    AmazonReview,
    AmazonProduct,
    MatchQuery,
)

from adam.data.amazon.client import (
    AmazonLocalClient,
    get_amazon_client,
    reset_amazon_client,
)

from adam.data.amazon.prelearning import (
    PreLearningOrchestrator,
    PreLearningConfig,
    PreLearningProgress,
    get_prelearning_orchestrator,
)

__all__ = [
    # Models
    "AmazonReview",
    "AmazonProduct",
    "MatchQuery",
    # Client
    "AmazonLocalClient",
    "get_amazon_client",
    "reset_amazon_client",
    # Pre-learning
    "PreLearningOrchestrator",
    "PreLearningConfig",
    "PreLearningProgress",
    "get_prelearning_orchestrator",
]
