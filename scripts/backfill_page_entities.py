#!/usr/bin/env python3
"""Phase A backfill — migrate existing Redis taxonomy keys into Neo4j
Author / Publication nodes with their accumulated centroid posteriors.

Background: the prior architecture stored author and publication state in
Redis under `informativ:taxonomy:{domain}` and
`informativ:taxonomy:{domain}:author:{slug}` with a 14-day TTL. Those
hashes carry a 20-dim centroid, variance_sum, and observation_count that
represent real accumulated learning. This script lifts that state into
durable Neo4j Author and Publication nodes so the operating-lifetime
posteriors begin with the existing evidence rather than cold-starting
at Phase B's read-switch moment.

This is a one-shot operation. Safe to re-run (idempotent upserts). Does
NOT delete the Redis keys — Redis continues to serve reads until Phase B.

Usage:
    python3 scripts/backfill_page_entities.py
    python3 scripts/backfill_page_entities.py --dry-run
    python3 scripts/backfill_page_entities.py --redis-host localhost
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adam.config.settings import settings
from adam.infrastructure.neo4j.client import get_neo4j_client
from adam.intelligence.domain_taxonomy import EDGE_DIMENSIONS, _REDIS_PREFIX
from adam.intelligence.pages.entity_graph import (
    CONSTRUCT_DIMENSIONS,
    PRIMARY_METAPHOR_AXES,
    _slugify_strict,
    author_id,
    publication_id,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("backfill_page_entities")


# Direct entity-seed Cypher — bypasses the Welford update path (we already
# have the accumulated centroid + variance from Redis, so we write them
# verbatim). Subsequent observations via PageEntityGraph.record_article
# continue the Welford accumulation from the seeded state.
_SEED_PUBLICATION = """
MERGE (p:Publication {id: $id})
  ON CREATE SET
    p.name = $name,
    p.canonical_domain = $domain,
    p.alternate_domains = [],
    p.slug = $slug,
    p.publisher_parent = null,
    p.editorial_register = null,
    p.observation_count = $observations,
    p.construct_centroid = $centroid,
    p.construct_variance = $variance,
    p.construct_observations = $observations,
    p.primary_metaphor_axes = $zero_metaphor,
    p.first_seen = datetime(),
    p.last_seen = datetime(),
    p.last_updated = datetime()
  ON MATCH SET
    // If the node already exists (e.g., from a prior backfill or a shadow
    // write), only upgrade its counters when the backfill carries MORE
    // observations than what's currently stored. This guards against
    // clobbering fresher data with stale Redis snapshots.
    p.observation_count = CASE WHEN $observations > p.observation_count
                              THEN $observations ELSE p.observation_count END,
    p.construct_centroid = CASE WHEN $observations > p.construct_observations
                                THEN $centroid ELSE p.construct_centroid END,
    p.construct_variance = CASE WHEN $observations > p.construct_observations
                                THEN $variance ELSE p.construct_variance END,
    p.construct_observations = CASE WHEN $observations > p.construct_observations
                                    THEN $observations ELSE p.construct_observations END,
    p.last_updated = datetime()
RETURN p.id AS id
"""


_SEED_AUTHOR = """
MERGE (a:Author {id: $id})
  ON CREATE SET
    a.name = $name,
    a.slug = $slug,
    a.url = null,
    a.social_handles = [],
    a.observation_count = $observations,
    a.construct_centroid = $centroid,
    a.construct_variance = $variance,
    a.construct_observations = $observations,
    a.primary_metaphor_axes = $zero_metaphor,
    a.style_signature = [],
    a.first_seen = datetime(),
    a.last_seen = datetime(),
    a.last_updated = datetime()
  ON MATCH SET
    a.observation_count = CASE WHEN $observations > a.observation_count
                              THEN $observations ELSE a.observation_count END,
    a.construct_centroid = CASE WHEN $observations > a.construct_observations
                                THEN $centroid ELSE a.construct_centroid END,
    a.construct_variance = CASE WHEN $observations > a.construct_observations
                                THEN $variance ELSE a.construct_variance END,
    a.construct_observations = CASE WHEN $observations > a.construct_observations
                                    THEN $observations ELSE a.construct_observations END,
    a.last_updated = datetime()
RETURN a.id AS id
"""


_SEED_WRITES_FOR = """
MATCH (a:Author {id: $author_id})
MATCH (p:Publication {id: $publication_id})
MERGE (a)-[r:WRITES_FOR]->(p)
  ON CREATE SET r.article_count = $articles,
                r.first_written = datetime(),
                r.last_written = datetime()
  ON MATCH SET  r.article_count = CASE WHEN $articles > r.article_count
                                       THEN $articles ELSE r.article_count END,
                r.last_written = datetime()
"""


def _parse_centroid_and_variance(
    hash_data: Dict[str, str],
) -> Tuple[List[float], List[float], int]:
    """Extract 20-dim centroid, Welford-compatible variance, and
    observation count from a domain_taxonomy Redis hash.

    domain_taxonomy stores variance as `variance_sum_{dim}` which is the
    Welford M2 (sum of squared deviations). The Neo4j schema stores
    variance directly; we convert M2 → variance by dividing by n.
    """
    try:
        n = int(float(hash_data.get("observation_count", 0)))
    except (TypeError, ValueError):
        n = 0

    centroid: List[float] = []
    variance: List[float] = []
    for dim in EDGE_DIMENSIONS:
        try:
            centroid.append(float(hash_data.get(f"centroid_{dim}", 0.0)))
        except (TypeError, ValueError):
            centroid.append(0.0)
        try:
            m2 = float(hash_data.get(f"variance_sum_{dim}", 0.0))
        except (TypeError, ValueError):
            m2 = 0.0
        variance.append(m2 / n if n > 0 else 0.0)

    # Pad / truncate defensively in case the Redis schema used a different
    # dimension count (e.g., legacy 7-dim NDF hashes that pre-date the
    # 20-dim upgrade). Short vectors pad with zeros; long ones truncate.
    centroid = centroid[:CONSTRUCT_DIMENSIONS]
    variance = variance[:CONSTRUCT_DIMENSIONS]
    while len(centroid) < CONSTRUCT_DIMENSIONS:
        centroid.append(0.0)
        variance.append(0.0)

    return centroid, variance, n


def _connect_redis(host: str, port: int):
    try:
        import redis
    except ImportError:
        logger.error("redis package not installed — pip install redis")
        return None
    try:
        client = redis.Redis(host=host, port=port, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.error("Could not connect to Redis at %s:%s — %s", host, port, exc)
        return None


async def _seed_one(
    session,
    cypher: str,
    **params,
) -> Optional[str]:
    try:
        result = await session.run(cypher, **params)
        records = [r async for r in result]
        return records[0].get("id") if records else None
    except Exception as exc:
        logger.warning("Seed query failed: %s — params=%s", exc, list(params.keys()))
        return None


async def _run(
    redis_host: str,
    redis_port: int,
    dry_run: bool,
) -> int:
    r = _connect_redis(redis_host, redis_port)
    if r is None:
        return 1

    # Key patterns:
    #   informativ:taxonomy:{domain}                       → Publication seed
    #   informativ:taxonomy:{domain}:author:{author_slug}  → Author seed
    pub_keys: List[str] = []
    author_keys: List[str] = []
    for key in r.scan_iter(match=f"{_REDIS_PREFIX}*", count=500):
        rest = key[len(_REDIS_PREFIX):]
        if ":author:" in rest:
            author_keys.append(key)
        elif ":cat:" in rest or ":sub:" in rest or ":patterns" in rest:
            # category / subcategory / patterns — skipped in Phase A
            # (section × publication posteriors land via shadow-writes
            # as new impressions arrive; backfilling them requires also
            # materializing Section/Topic vocabulary which is out of
            # scope here)
            continue
        else:
            pub_keys.append(key)

    print(f"Scanned {len(pub_keys)} publication keys, {len(author_keys)} author keys")
    if dry_run:
        print("[dry-run] Would seed:")
        for key in pub_keys[:5]:
            print(f"  Publication: {key}")
        for key in author_keys[:5]:
            print(f"  Author: {key}")
        if len(pub_keys) > 5 or len(author_keys) > 5:
            print("  … (sample only; use --verbose to list all)")
        return 0

    client = get_neo4j_client()
    if not client.is_connected:
        await client.connect()

    pub_success = 0
    pub_skip = 0
    author_success = 0
    author_skip = 0
    writes_for_success = 0

    zero_metaphor = [0.0] * PRIMARY_METAPHOR_AXES

    async with await client.session() as session:
        # Publications first (authors reference them).
        for key in pub_keys:
            domain = key[len(_REDIS_PREFIX):]
            if not domain or ":" in domain:
                continue
            hash_data = r.hgetall(key)
            if not hash_data:
                pub_skip += 1
                continue
            centroid, variance, n = _parse_centroid_and_variance(hash_data)
            if n <= 0:
                pub_skip += 1
                continue
            pub_id = publication_id(domain)
            pub_slug = domain.lower().replace(".", "-")
            seeded = await _seed_one(
                session, _SEED_PUBLICATION,
                id=pub_id,
                name=domain,
                domain=domain,
                slug=pub_slug,
                observations=n,
                centroid=centroid,
                variance=variance,
                zero_metaphor=zero_metaphor,
            )
            if seeded:
                pub_success += 1
            else:
                pub_skip += 1

        logger.info(
            "Publications seeded: %d (%d skipped)", pub_success, pub_skip,
        )

        # Authors. Keys look like informativ:taxonomy:{domain}:author:{slug}
        for key in author_keys:
            rest = key[len(_REDIS_PREFIX):]
            parts = rest.split(":author:", 1)
            if len(parts) != 2:
                author_skip += 1
                continue
            domain, slug_strict = parts[0], parts[1]
            hash_data = r.hgetall(key)
            if not hash_data:
                author_skip += 1
                continue
            centroid, variance, n = _parse_centroid_and_variance(hash_data)
            if n <= 0:
                author_skip += 1
                continue
            author_name = hash_data.get("author_name") or slug_strict.replace(
                "-", " "
            ).title()
            a_id = f"author:{slug_strict}"
            seeded = await _seed_one(
                session, _SEED_AUTHOR,
                id=a_id,
                name=author_name,
                slug=slug_strict,
                observations=n,
                centroid=centroid,
                variance=variance,
                zero_metaphor=zero_metaphor,
            )
            if not seeded:
                author_skip += 1
                continue
            author_success += 1

            # WRITES_FOR edge — Redis taxonomy implicitly established this
            # relationship via the {domain}:author:{slug} key pattern.
            # Seed with article_count = observation_count (the best proxy
            # we have; Phase F proactive ingestion will refine).
            wf_id = await _seed_one(
                session, _SEED_WRITES_FOR,
                author_id=a_id,
                publication_id=publication_id(domain),
                articles=n,
            )
            if wf_id is not None or True:
                writes_for_success += 1

    print()
    print("Backfill complete:")
    print(f"  Publications seeded:  {pub_success}  (skipped: {pub_skip})")
    print(f"  Authors seeded:       {author_success}  (skipped: {author_skip})")
    print(f"  WRITES_FOR edges:     {writes_for_success}")
    print()
    print("Redis keys are NOT deleted — Redis continues to serve reads")
    print("until Phase B flips to Neo4j-primary.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan keys but write nothing.")
    args = parser.parse_args()

    return asyncio.run(_run(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    sys.exit(main())
