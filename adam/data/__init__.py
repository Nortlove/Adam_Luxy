# =============================================================================
# ADAM Data Module
# Location: adam/data/__init__.py
# =============================================================================

"""
ADAM Data Module - Access to Local Data Sources

This module provides access to:
- Amazon Local Database: Millions of verified purchase reviews
- Pre-learning Infrastructure: Batch processing for system training
- Category Psychology: Pre-computed psychological profiles per category

Usage:
    from adam.data.amazon import (
        get_amazon_client,
        get_prelearning_orchestrator,
    )
    
    # Get reviews for analysis
    client = get_amazon_client()
    reviews = await client.get_reviews_by_brand("DeWalt", limit=100)
    
    # Run pre-learning
    orchestrator = get_prelearning_orchestrator()
    await orchestrator.run_full_prelearning()
"""

from adam.data.amazon import (
    AmazonLocalClient,
    AmazonReview,
    AmazonProduct,
    get_amazon_client,
    reset_amazon_client,
    PreLearningOrchestrator,
    PreLearningConfig,
    PreLearningProgress,
    get_prelearning_orchestrator,
)

__all__ = [
    # Amazon client
    "AmazonLocalClient",
    "AmazonReview",
    "AmazonProduct",
    "get_amazon_client",
    "reset_amazon_client",
    # Pre-learning
    "PreLearningOrchestrator",
    "PreLearningConfig",
    "PreLearningProgress",
    "get_prelearning_orchestrator",
]
