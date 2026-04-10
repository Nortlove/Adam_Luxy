"""
ADAM Blueprint Intelligence Bridge

Connects the Blueprint deployment shell to the shared intelligence core.
Provides tenant-scoped wrappers around:
  - ContentProfiler (NDF profiling for connectors)
  - SegmentBuilder (psychological segment generation)
  - TaxonomyMapper (ADAM constructs → IAB taxonomy)
  - OutcomeBridge (delivery outcomes → learning loop)
"""

from adam.platform.intelligence.content_profiler import ContentProfiler
from adam.platform.intelligence.segment_builder import SegmentBuilder
from adam.platform.intelligence.taxonomy_mapper import TaxonomyMapper
from adam.platform.intelligence.outcome_bridge import OutcomeBridge

__all__ = [
    "ContentProfiler",
    "SegmentBuilder",
    "TaxonomyMapper",
    "OutcomeBridge",
]
