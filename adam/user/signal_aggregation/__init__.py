# =============================================================================
# ADAM Signal Aggregation (#08)
# =============================================================================

"""
SIGNAL AGGREGATION

Process and aggregate behavioral signals from multiple sources.
"""

from adam.user.signal_aggregation.service import SignalAggregationService
from adam.user.signal_aggregation.processors import (
    SignalProcessor,
    iHeartSignalProcessor,
    WebSignalProcessor,
)

__all__ = [
    "SignalAggregationService",
    "SignalProcessor",
    "iHeartSignalProcessor",
    "WebSignalProcessor",
]
