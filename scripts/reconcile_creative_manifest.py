#!/usr/bin/env python3
"""One-shot CLI: reconcile :UploadedCreative manifest with StackAdapt.

Per directive Phase 8 line 1099 + Slice C / Slice 14 honest tags.
Surveys the StackAdapt account via list_ads and persists a
:UploadedCreative record per non-archived ad. Existing ads with
empty userMetadata are persisted with mechanism / metaphor /
posture all None — operator must tag them via a separate process
to make Slice C's lookup resolve.

Usage:
    python3 scripts/reconcile_creative_manifest.py
        [--first 50] [--max-pages 100] [--dry-run]

Env vars consumed:
    STACKADAPT_GRAPHQL_KEY  — StackAdapt GraphQL auth
    STACKADAPT_GRAPHQL_ENDPOINT  — defaults to
        https://api.stackadapt.com/graphql
    NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD / NEO4J_DATABASE
        — for the :UploadedCreative manifest persistence path.

Returns 0 on success (any reconciliation result, including 0 ads).
Returns non-zero on credential / connection failure.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Optional

# Self-locate the project root so the script runs from any cwd
# without requiring PYTHONPATH.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("reconcile_creative_manifest")


def _load_env_from_dotenv() -> None:
    """Best-effort .env load (so `python3 scripts/...` works without
    a venv-activated shell)."""
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def _build_client() -> Optional[Any]:
    api_key = (
        os.environ.get("STACKADAPT_GRAPHQL_KEY")
        or os.environ.get("STACKADAPT_API_KEY")
    )
    if not api_key:
        logger.error(
            "STACKADAPT_GRAPHQL_KEY / STACKADAPT_API_KEY not set — "
            "cannot reach StackAdapt API."
        )
        return None
    from adam.integrations.stackadapt.graphql_client import (
        StackAdaptGraphQLClient,
    )
    return StackAdaptGraphQLClient(api_key=api_key)


async def _build_driver() -> Optional[Any]:
    """Build an async Neo4j driver from env. None on failure."""
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not uri or not user or not pwd:
        logger.error(
            "NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD not set — "
            "cannot persist manifest."
        )
        return None
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
        await driver.verify_connectivity()
        return driver
    except Exception as exc:
        logger.error("Neo4j driver build failed: %s", exc)
        return None


async def _run(first: int, max_pages: int, dry_run: bool) -> int:
    _load_env_from_dotenv()
    client = await _build_client()
    if client is None:
        return 2

    driver: Optional[Any] = None
    if not dry_run:
        driver = await _build_driver()
        if driver is None:
            return 3
    else:
        logger.info("DRY RUN — no manifest writes will occur.")

    from adam.intelligence.creative_manifest_reconciliation import (
        reconcile_existing_creatives,
    )

    try:
        result = await reconcile_existing_creatives(
            client=client, driver=driver,
            first_per_page=first, max_pages=max_pages,
        )
    finally:
        if driver is not None:
            await driver.close()

    print()
    print("Reconciliation result")
    print("=====================")
    print(f"  ads listed                : {result.n_listed}")
    print(f"  records persisted         : {result.n_persisted}")
    print(f"  records with metadata     : {result.n_with_metadata}")
    print(f"  ads skipped (archived)    : {result.n_skipped_archived}")
    print(f"  errors                    : {len(result.errors)}")
    if result.errors:
        for e in result.errors[:20]:
            print(f"    - {e}")
        if len(result.errors) > 20:
            print(f"    ... ({len(result.errors) - 20} more)")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--first", type=int, default=50,
        help="page size (StackAdapt list_ads first arg). Default 50.",
    )
    p.add_argument(
        "--max-pages", type=int, default=100,
        help="max pages to consume (defensive cap). Default 100.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="list ads only — do NOT persist to Neo4j.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(
        first=args.first,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    sys.exit(main())
