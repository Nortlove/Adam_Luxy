# =============================================================================
# ADAM Neo4j Migration Runner
# Location: adam/infrastructure/neo4j/migration_runner.py
# =============================================================================

"""
MIGRATION RUNNER

Executes Neo4j migrations in order, tracking which migrations have been applied.
Uses a :Migration node in the database to track migration state.

Usage:
    # From command line
    python -m adam.infrastructure.neo4j.migration_runner
    
    # Programmatically
    from adam.infrastructure.neo4j.migration_runner import run_migrations
    await run_migrations()
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from neo4j import AsyncGraphDatabase, AsyncDriver
import structlog

from adam.config.settings import settings

logger = structlog.get_logger(__name__)


class MigrationRunner:
    """
    Executes Neo4j migrations in order.
    
    Migrations are .cypher files in the migrations/ directory.
    They are executed in alphanumeric order.
    Applied migrations are tracked in :Migration nodes.
    """
    
    MIGRATIONS_DIR = Path(__file__).parent / "migrations"
    
    def __init__(self, driver: AsyncDriver, database: str = "adam"):
        self._driver = driver
        self._database = database
        self._log = structlog.get_logger(__name__)
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of already-applied migration names."""
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                """
                MATCH (m:Migration)
                RETURN m.name AS name
                ORDER BY m.applied_at
                """
            )
            records = await result.data()
            return [r["name"] for r in records]
    
    async def mark_migration_applied(self, name: str) -> None:
        """Record that a migration has been applied."""
        async with self._driver.session(database=self._database) as session:
            await session.run(
                """
                CREATE (m:Migration {
                    name: $name,
                    applied_at: datetime()
                })
                """,
                name=name
            )
    
    def get_migration_files(self) -> List[Tuple[str, Path]]:
        """Get list of migration files in order."""
        if not self.MIGRATIONS_DIR.exists():
            self._log.warning("Migrations directory not found", 
                            path=str(self.MIGRATIONS_DIR))
            return []
        
        files = []
        for f in sorted(self.MIGRATIONS_DIR.glob("*.cypher")):
            files.append((f.stem, f))
        
        return files
    
    async def run_migration(self, name: str, path: Path) -> bool:
        """
        Execute a single migration file.
        
        Returns True if successful, False otherwise.
        """
        self._log.info("Running migration", name=name)
        
        try:
            # Read migration content
            content = path.read_text()
            
            # Split into statements (by semicolon, but be careful with comments)
            statements = self._parse_cypher_statements(content)
            
            # Execute each statement
            async with self._driver.session(database=self._database) as session:
                for i, stmt in enumerate(statements):
                    if stmt.strip():
                        try:
                            await session.run(stmt)
                            self._log.debug("Executed statement", 
                                          migration=name, 
                                          statement_num=i+1)
                        except Exception as e:
                            # Some statements may fail if already exists - that's OK
                            if "already exists" in str(e).lower():
                                self._log.debug("Already exists, skipping", 
                                              migration=name,
                                              statement_num=i+1)
                            else:
                                raise
            
            # Mark as applied
            await self.mark_migration_applied(name)
            self._log.info("Migration completed", name=name)
            return True
            
        except Exception as e:
            self._log.error("Migration failed", name=name, error=str(e))
            return False
    
    def _parse_cypher_statements(self, content: str) -> List[str]:
        """
        Parse Cypher file into individual statements.
        
        Handles:
        - // comments
        - Multi-line statements
        - Semicolon separators
        """
        statements = []
        current_statement = []
        in_block_comment = False
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Skip line comments
            if stripped.startswith('//'):
                continue
            
            # Handle block comments
            if '/*' in stripped:
                in_block_comment = True
                continue
            if '*/' in stripped:
                in_block_comment = False
                continue
            if in_block_comment:
                continue
            
            # Add to current statement
            current_statement.append(line)
            
            # If ends with semicolon, complete the statement
            if stripped.endswith(';'):
                stmt = '\n'.join(current_statement)
                # Remove trailing semicolon for Neo4j driver
                stmt = stmt.rstrip().rstrip(';')
                statements.append(stmt)
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            stmt = '\n'.join(current_statement)
            stmt = stmt.rstrip().rstrip(';')
            if stmt.strip():
                statements.append(stmt)
        
        return statements
    
    async def run_all(self, dry_run: bool = False) -> Tuple[int, int]:
        """
        Run all pending migrations.
        
        Args:
            dry_run: If True, just report what would be run
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        # Get already applied
        applied = await self.get_applied_migrations()
        self._log.info("Found applied migrations", count=len(applied))
        
        # Get all migration files
        all_migrations = self.get_migration_files()
        self._log.info("Found migration files", count=len(all_migrations))
        
        # Filter to pending
        pending = [(name, path) for name, path in all_migrations 
                   if name not in applied]
        
        if not pending:
            self._log.info("No pending migrations")
            return (0, 0)
        
        self._log.info("Pending migrations", count=len(pending),
                      migrations=[name for name, _ in pending])
        
        if dry_run:
            self._log.info("Dry run - no changes made")
            return (0, 0)
        
        # Run pending migrations
        success_count = 0
        fail_count = 0
        
        for name, path in pending:
            if await self.run_migration(name, path):
                success_count += 1
            else:
                fail_count += 1
                # Stop on first failure
                self._log.error("Stopping due to failed migration")
                break
        
        return (success_count, fail_count)


async def run_migrations(
    uri: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    database: str = "adam",
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Convenience function to run all migrations.
    
    Args:
        uri: Neo4j URI (defaults to settings)
        username: Neo4j username (defaults to settings)
        password: Neo4j password (defaults to settings)
        database: Database name
        dry_run: If True, just report what would be run
        
    Returns:
        Tuple of (successful_count, failed_count)
    """
    # Use settings if not provided
    uri = uri or settings.neo4j.uri
    username = username or settings.neo4j.username
    password = password or settings.neo4j.password
    
    logger.info("Connecting to Neo4j", uri=uri, database=database)
    
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    try:
        # Verify connectivity
        await driver.verify_connectivity()
        logger.info("Neo4j connection established")
        
        # Run migrations
        runner = MigrationRunner(driver, database)
        return await runner.run_all(dry_run=dry_run)
        
    finally:
        await driver.close()


async def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run ADAM Neo4j migrations")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Show what would be run without executing")
    parser.add_argument("--uri", help="Neo4j URI")
    parser.add_argument("--username", help="Neo4j username")
    parser.add_argument("--password", help="Neo4j password")
    parser.add_argument("--database", default="adam", help="Database name")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    
    success, failed = await run_migrations(
        uri=args.uri,
        username=args.username,
        password=args.password,
        database=args.database,
        dry_run=args.dry_run
    )
    
    print(f"\nMigrations complete: {success} successful, {failed} failed")
    
    if failed > 0:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
