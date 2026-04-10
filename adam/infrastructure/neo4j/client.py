# =============================================================================
# ADAM Neo4j Client
# Location: adam/infrastructure/neo4j/client.py
# =============================================================================

"""
Neo4j Client Wrapper

Provides a simple interface to the Neo4j driver for components that need
direct database access (like the GraphIntelligenceService).

This wraps the Infrastructure singleton from adam.core.dependencies to provide
a consistent interface for Neo4j operations.
"""

import logging
from typing import Optional

from neo4j import AsyncDriver, AsyncGraphDatabase

from adam.config.settings import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Simple Neo4j client wrapper.
    
    Provides access to the Neo4j async driver with automatic connection handling.
    
    The AsyncDriver binds its connection pool to the event loop that created it.
    All async operations must run on the same loop. The graph_intelligence module
    maintains a persistent background loop to guarantee this.
    """
    
    _instance: Optional["Neo4jClient"] = None
    
    def __init__(self):
        self._driver: Optional[AsyncDriver] = None
        self._connected: bool = False
    
    @classmethod
    def get_instance(cls) -> "Neo4jClient":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def connect(self) -> bool:
        """
        Connect to Neo4j.
        
        Returns True if connection successful.
        """
        if self._connected and self._driver:
            return True
        
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j.uri,
                auth=(settings.neo4j.username, settings.neo4j.password),
                max_connection_pool_size=settings.neo4j.max_connection_pool_size,
            )
            
            # Verify connection
            await self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"Connected to Neo4j at {settings.neo4j.uri}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._connected = False
            return False
    
    async def close(self) -> None:
        """Close the connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Neo4j connection closed")
    
    @property
    def driver(self) -> Optional[AsyncDriver]:
        """Get the Neo4j async driver."""
        return self._driver
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected and self._driver is not None
    
    async def session(self, database: Optional[str] = None):
        """
        Get a Neo4j session.
        
        Usage:
            async with client.session() as session:
                result = await session.run("MATCH (n) RETURN n LIMIT 10")
        """
        if not self._connected:
            await self.connect()
        
        if not self._driver:
            raise RuntimeError("Neo4j driver not available")
        
        db = database or settings.neo4j.database
        return self._driver.session(database=db)


# =============================================================================
# SINGLETON ACCESSORS
# =============================================================================

_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """
    Get singleton Neo4jClient.
    
    This is the primary entry point for components needing Neo4j access.
    
    Example:
        client = get_neo4j_client()
        async with client.session() as session:
            result = await session.run("MATCH (n:CognitiveMechanism) RETURN n")
    """
    global _client
    if _client is None:
        _client = Neo4jClient.get_instance()
    return _client


async def get_neo4j_driver() -> Optional[AsyncDriver]:
    """
    Get the Neo4j async driver directly.
    
    Convenience function for components that need raw driver access.
    Will attempt to connect if not already connected.
    """
    client = get_neo4j_client()
    if not client.is_connected:
        await client.connect()
    return client.driver
