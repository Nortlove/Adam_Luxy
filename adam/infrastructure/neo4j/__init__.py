# =============================================================================
# ADAM Neo4j Infrastructure
# =============================================================================

"""
Neo4j infrastructure components for ADAM platform.

This module provides:
- Migration runner for schema deployment
- Connection pooling and driver management
- Query execution utilities
- Client wrapper for easy Neo4j access
"""

from adam.infrastructure.neo4j.migration_runner import (
    MigrationRunner,
    run_migrations,
)
from adam.infrastructure.neo4j.client import (
    Neo4jClient,
    get_neo4j_client,
    get_neo4j_driver,
)

__all__ = [
    "MigrationRunner",
    "run_migrations",
    "Neo4jClient",
    "get_neo4j_client",
    "get_neo4j_driver",
]
