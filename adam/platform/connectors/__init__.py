"""
ADAM Content Connector Library

Pluggable modules that ingest content from external sources, run NDF profiling,
and store tenant-scoped enriched content in the graph.

Each connector implements the BaseConnector interface:
  - configure(config) → validate
  - poll() → ContentItem[]
  - process(item) → EnrichedContent (via NDF pipeline)
  - store(enriched) → graph node + Redis cache

See ADAM_Deep_Technical_Architecture.md §Connector Library.
"""

from adam.platform.connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ContentItem,
    EnrichedContent,
)

__all__ = [
    "BaseConnector",
    "ConnectorStatus",
    "ContentItem",
    "EnrichedContent",
]
