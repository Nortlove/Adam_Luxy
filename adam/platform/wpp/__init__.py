# =============================================================================
# ADAM WPP Integration Package
# =============================================================================

"""
WPP AD DESK INTELLIGENCE LAYER

Integration with WPP's advertising infrastructure.

Key Components:
1. Amazon Priors - Psychological profiles from Amazon review corpus
2. Brand Intelligence - Brand-specific constraints and voice
3. Campaign Optimization - WPP campaign performance
4. Cross-Platform Learning - Learning across WPP properties
"""

from adam.platform.wpp.service import WPPAdDeskService
from adam.platform.wpp.amazon_priors import AmazonPriorService

__all__ = [
    "WPPAdDeskService",
    "AmazonPriorService",
]
