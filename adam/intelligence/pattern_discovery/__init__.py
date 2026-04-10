# =============================================================================
# ADAM Pattern Discovery
# Location: adam/intelligence/pattern_discovery/__init__.py
# =============================================================================

"""
Pattern Discovery for ADAM

This module discovers patterns in consumer behavior and brand effectiveness
from ad outcome data, including:

- Brand-archetype compatibility patterns
- Mechanism effectiveness by brand personality
- Voice-engagement correlations
- Nonconscious priming patterns
"""

from adam.intelligence.pattern_discovery.brand_pattern_learner import (
    BrandPatternLearner,
    DiscoveredPattern,
    PatternType,
    get_brand_pattern_learner,
)

__all__ = [
    "BrandPatternLearner",
    "DiscoveredPattern",
    "PatternType",
    "get_brand_pattern_learner",
]
