# ADAM Intelligence Components
"""
Intelligence components for ADAM platform.

- EmergenceEngine: Discovers novel psychological constructs
- GraphEdgeService: Leverages graph relationships for intelligence
- CohortDiscovery: Behavioral cohort identification
- CausalDiscovery: Causal relationship inference
- PredictiveProcessing: Predictive intelligence
"""

from adam.intelligence.emergence_engine import EmergenceEngine
from adam.intelligence.graph_edge_service import GraphEdgeService, get_graph_edge_service
from adam.intelligence.cohort_discovery import CohortDiscoveryService, get_cohort_discovery_service

__all__ = [
    "EmergenceEngine",
    "GraphEdgeService",
    "get_graph_edge_service",
    "CohortDiscoveryService",
    "get_cohort_discovery_service",
]
