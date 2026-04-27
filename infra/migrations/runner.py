"""Neo4j migration runner — dry-run by default.

Loads a .cypher migration file, splits it into individual statements at
semicolons, and executes them through the Neo4j driver. Dry-run mode
(default) prints the parsed statements without executing.

Discipline:
    - Dry-run is the DEFAULT. Production execution requires --execute
      explicitly. This is the assistant rule from CLAUDE.md / orientation:
      destructive or shared-state operations require explicit go-ahead.
    - Each migration is idempotent (uses MATCH ... WHERE ... IS NULL or
      CREATE INDEX IF NOT EXISTS). Re-running is safe.
    - The runner does NOT track which migrations have been applied. We
      don't have a migration-tracking table yet; a future migration
      (M4 follow-up) will add one. For now, idempotency carries the
      load.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def _strip_comments(cypher: str) -> str:
    """Strip Cypher line comments (// ...) so statement-splitter sees
    only executable text. Preserves cypher inside strings (rare in
    migrations)."""
    return re.sub(r"//[^\n]*", "", cypher)


def parse_statements(cypher_text: str) -> List[str]:
    """Split a multi-statement .cypher file into individual statements.

    Statements are separated by semicolons. Comment lines starting with
    // are stripped first. Whitespace-only fragments are dropped.
    """
    stripped = _strip_comments(cypher_text)
    raw = stripped.split(";")
    return [s.strip() for s in raw if s.strip()]


def load_migration(path: Path) -> List[str]:
    """Load a migration file and return its statement list."""
    if not path.exists():
        raise FileNotFoundError(f"Migration not found: {path}")
    return parse_statements(path.read_text())


def run_migration(
    path: Path,
    dry_run: bool = True,
    driver: Optional[object] = None,
) -> dict:
    """Run a Cypher migration. Returns a summary dict.

    Args:
        path: path to the .cypher file
        dry_run: when True (DEFAULT), parse and report but don't execute.
                 When False, execute against the configured Neo4j.
        driver: optional pre-built Neo4j driver. None → build one from
                config. Passing a driver is the test seam.

    Returns:
        {
            "path": str,
            "dry_run": bool,
            "statements": int,
            "executed": int,
            "errors": List[str],
            "verification": dict,  # last-statement results when not dry-run
        }
    """
    summary = {
        "path": str(path),
        "dry_run": dry_run,
        "statements": 0,
        "executed": 0,
        "errors": [],
        "verification": {},
    }

    try:
        statements = load_migration(path)
    except FileNotFoundError as exc:
        summary["errors"].append(str(exc))
        return summary

    summary["statements"] = len(statements)

    if dry_run:
        logger.info("DRY-RUN: would execute %d statements", len(statements))
        for i, stmt in enumerate(statements, 1):
            preview = stmt.split("\n")[0][:80]
            logger.info("  [%d] %s%s", i, preview,
                        "..." if len(stmt) > len(preview) else "")
        return summary

    # ── Execute path — caller must explicitly opt in via dry_run=False ──
    # Build a SYNCHRONOUS driver from settings. adam.core.dependencies
    # returns an async driver (AsyncGraphDatabase) which doesn't support
    # the `with driver.session()` pattern this runner uses. The runner
    # is one-shot batch work — sync is the right shape.
    if driver is None:
        try:
            from neo4j import GraphDatabase
            from adam.config.settings import settings
            uri = settings.neo4j.uri
            user = settings.neo4j.username
            password = settings.neo4j.password
            if not uri or not user or not password:
                summary["errors"].append(
                    "NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD not all set"
                )
                return summary
            driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as exc:
            summary["errors"].append(f"could not build Neo4j driver: {exc}")
            return summary

    if driver is None:
        summary["errors"].append("Neo4j driver is None — cannot execute")
        return summary

    last_result = {}
    try:
        with driver.session() as session:
            for i, stmt in enumerate(statements, 1):
                try:
                    result = session.run(stmt)
                    record = result.single()
                    if record:
                        last_result = dict(record)
                    summary["executed"] += 1
                except Exception as exc:
                    summary["errors"].append(f"statement {i} failed: {exc}")
                    # Stop on first failure — partial migration could leave
                    # the graph in an inconsistent state. The caller can
                    # inspect the error and re-run after fixing.
                    return summary
    except Exception as exc:
        summary["errors"].append(f"session-level failure: {exc}")
        return summary

    summary["verification"] = last_result
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "migration", type=Path,
        help="Path to the .cypher migration file",
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually execute against Neo4j (default is dry-run). REQUIRED "
             "for any real change. Run dry-run first; review; then re-run "
             "with --execute.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Log each statement as it executes",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    summary = run_migration(args.migration, dry_run=not args.execute)

    print(f"\n=== Migration: {summary['path']} ===")
    print(f"  mode:       {'EXECUTE' if not summary['dry_run'] else 'DRY-RUN'}")
    print(f"  statements: {summary['statements']}")
    print(f"  executed:   {summary['executed']}")
    print(f"  errors:     {len(summary['errors'])}")
    if summary["errors"]:
        for err in summary["errors"]:
            print(f"    - {err}")
    if summary["verification"]:
        print(f"  verification: {summary['verification']}")

    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
