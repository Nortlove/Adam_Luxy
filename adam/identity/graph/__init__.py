# =============================================================================
# ADAM Enhancement #19: Identity Graph Package
# Location: adam/identity/graph/__init__.py
# =============================================================================

"""
Neo4j-Backed Identity Graph

Schema:
- UnifiedIdentity nodes
- Identifier nodes
- Household nodes
- BELONGS_TO, LINKED_TO, MEMBER_OF relationships
"""

from .neo4j_graph import (
    IDENTITY_GRAPH_SCHEMA,
    IdentityGraphQueries,
    Neo4jIdentityGraph,
    get_identity_graph,
)

__all__ = [
    "IDENTITY_GRAPH_SCHEMA",
    "IdentityGraphQueries",
    "Neo4jIdentityGraph",
    "get_identity_graph",
]
