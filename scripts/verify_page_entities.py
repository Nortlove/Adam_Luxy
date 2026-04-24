#!/usr/bin/env python3
"""Phase A verification — PageEntityGraph end-to-end against live Neo4j.

Exercises the full shadow-write path: creates one synthetic article
observation for a known publication, section, author, and topic, writes
through PageEntityGraph, then queries back every node and relationship
to verify the Welford centroid update, observation counters, and edge
creation all behave correctly.

Usage:
    # Applies migration 023 first if not already applied, then runs verify.
    python3 scripts/verify_page_entities.py

    # Just verify (skip migration):
    python3 scripts/verify_page_entities.py --skip-migration

    # Dry-run the write path (no Neo4j connection required):
    python3 scripts/verify_page_entities.py --dry-run

Designed for Chris to run in <10 minutes to confirm Phase A works before
Phase B flips reads to Neo4j-primary.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Repo-root on path so `adam` imports work when invoked directly.
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adam.config.settings import settings
from adam.infrastructure.neo4j.client import get_neo4j_client
from adam.infrastructure.neo4j.migration_runner import run_migrations
from adam.intelligence.pages import (
    ArticleObservation,
    AuthorUpsert,
    PageEntityGraph,
    PublicationUpsert,
    SectionUpsert,
    TopicUpsert,
)
from adam.intelligence.pages.entity_graph import CONSTRUCT_DIMENSIONS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("verify_page_entities")


# Synthetic article observation — deterministic so re-running converges
# on the same entities (idempotency verification).
_FIXTURE_URL = (
    "https://www.nytimes.com/2026/04/21/opinion/"
    "verify-page-entities-phase-a.html"
)
_FIXTURE_VECTOR_FIRST = [
    0.50, 0.30, 0.70, 0.20, 0.10, 0.40, 0.60, 0.30, 0.20, 0.50,
    0.40, 0.30, 0.70, 0.60, 0.20, 0.50, 0.40, 0.30, 0.60, 0.50,
]
_FIXTURE_VECTOR_SECOND = [
    0.60, 0.40, 0.80, 0.30, 0.20, 0.50, 0.70, 0.40, 0.30, 0.60,
    0.50, 0.40, 0.80, 0.70, 0.30, 0.60, 0.50, 0.40, 0.70, 0.60,
]


def _fixture_observation(vector: List[float]) -> ArticleObservation:
    return ArticleObservation(
        url=_FIXTURE_URL,
        title="Verify Page Entities — Phase A",
        publication=PublicationUpsert(
            name="The New York Times",
            canonical_domain="nytimes.com",
            publisher_parent="The New York Times Company",
            editorial_register="prestige_press",
        ),
        authors=[
            AuthorUpsert(
                name="Ezra Klein",
                url="https://www.nytimes.com/by/ezra-klein",
                social_handles=["@ezraklein"],
            ),
            AuthorUpsert(name="Jane Co-Author"),
        ],
        section=SectionUpsert(
            name="Opinion",
            description="Opinion and editorial commentary",
        ),
        topics=[
            TopicUpsert(
                name="Climate Change",
                parent_topic_slug="Environment",
            ),
            TopicUpsert(name="Policy"),
        ],
        schema_org_type="OpinionNewsArticle",
        published_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
        word_count=1850,
        construct_vector=vector,
        exposure_context_confidence=0.72,
        lexicon_evidence={"smoke_test": True},
    )


# Queries used to verify the write took effect.
_Q_AUTHORS = """
MATCH (ar:Article {url: $url})-[:BY]->(a:Author)
RETURN a.id AS id,
       a.name AS name,
       a.url AS url,
       a.observation_count AS obs,
       a.construct_observations AS n,
       a.construct_centroid[0] AS first_dim_mean,
       a.construct_variance[0] AS first_dim_variance
ORDER BY a.name
"""

_Q_PUBLICATION = """
MATCH (ar:Article {url: $url})-[:PUBLISHED_IN]->(p:Publication)
RETURN p.id AS id,
       p.name AS name,
       p.canonical_domain AS domain,
       p.publisher_parent AS parent,
       p.editorial_register AS reg,
       p.observation_count AS obs,
       p.construct_observations AS n,
       p.construct_centroid[0] AS first_dim_mean
"""

_Q_SECTION = """
MATCH (ar:Article {url: $url})-[:IN_SECTION]->(s:Section)
RETURN s.id AS id, s.name AS name, s.observation_count AS obs
"""

_Q_TOPICS = """
MATCH (ar:Article {url: $url})-[:ABOUT]->(t:Topic)
OPTIONAL MATCH (t)-[:SUBTOPIC_OF]->(parent:Topic)
RETURN t.id AS id, t.name AS name, t.observation_count AS obs,
       parent.id AS parent_id, parent.name AS parent_name
ORDER BY t.name
"""

_Q_ARTICLE = """
MATCH (ar:Article {url: $url})
RETURN ar.id AS id,
       ar.title AS title,
       ar.schema_org_type AS schema_type,
       ar.word_count AS wc,
       ar.observation_count AS obs,
       ar.construct_observations AS n,
       ar.exposure_context_confidence AS conf,
       ar.construct_centroid[0] AS first_dim_mean,
       ar.construct_variance[0] AS first_dim_variance
"""

_Q_HAS_SECTION = """
MATCH (p:Publication {id: $publication_id})
      -[r:HAS_SECTION]->(s:Section {id: $section_id})
RETURN r.article_count AS articles,
       r.observation_count AS obs,
       r.construct_centroid[0] AS first_dim_mean
"""

_Q_WRITES_FOR = """
MATCH (a:Author {id: $author_id})
      -[r:WRITES_FOR]->(p:Publication {id: $publication_id})
RETURN r.article_count AS articles
"""


async def _run_one(service: PageEntityGraph, vector: List[float]) -> Optional[str]:
    observation = _fixture_observation(vector)
    observation.validate()
    return await service.record_article(observation)


async def _query(session, cypher: str, **params) -> List[Dict[str, Any]]:
    result = await session.run(cypher, **params)
    return [dict(record) async for record in result]


def _check(label: str, condition: bool, detail: str = "") -> bool:
    mark = "PASS" if condition else "FAIL"
    msg = f"  [{mark}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition


async def _verify(dry_run: bool) -> int:
    """Returns an exit code (0 on success, 1 on any failure)."""
    service = PageEntityGraph()

    print("=" * 72)
    print("Phase A Verification — PageEntityGraph end-to-end")
    print("=" * 72)
    print(f"Neo4j URI: {settings.neo4j.uri}")
    print(f"Fixture URL: {_FIXTURE_URL}")
    print()

    if dry_run:
        print("[dry-run] Constructing fixture and exercising dataclass path only.")
        obs = _fixture_observation(_FIXTURE_VECTOR_FIRST)
        obs.validate()
        print(f"Observation id: {obs.id}")
        print(f"Publication id: {obs.publication.id}")
        print(f"Authors: {[a.id for a in obs.authors]}")
        print(f"Section id: {obs.section.id}")
        print(f"Topics: {[t.id for t in obs.topics]}")
        print("[dry-run] OK — no Neo4j writes attempted.")
        return 0

    # First write — creates entities, seeds centroids at vector value.
    print("[1/3] Writing first observation (creates entities; Welford n=0→1)")
    article_id = await _run_one(service, _FIXTURE_VECTOR_FIRST)
    if article_id is None:
        print("  FATAL: first record_article returned None. Check Neo4j "
              "connectivity and migration status.")
        return 1
    print(f"  Article id: {article_id}")

    # Second write — updates centroids via Welford (mean shifts toward new
    # vector, variance grows from 0).
    print("[2/3] Writing second observation (same URL; Welford n=1→2)")
    await _run_one(service, _FIXTURE_VECTOR_SECOND)

    print("[3/3] Verifying nodes and relationships")
    client = service._client
    passed = 0
    failed = 0

    async with await client.session() as session:
        # Article
        article_rows = await _query(session, _Q_ARTICLE, url=_FIXTURE_URL)
        if _check("Article node exists", len(article_rows) == 1):
            article = article_rows[0]
            _check("Article.observation_count == 2",
                   article["obs"] == 2, f"actual={article['obs']}")
            _check("Article.construct_observations == 2",
                   article["n"] == 2, f"actual={article['n']}")
            _check(
                "Article Welford mean ≈ avg of the two vectors (dim 0)",
                abs(article["first_dim_mean"] - 0.55) < 1e-6,
                f"actual={article['first_dim_mean']:.6f} (expected 0.55)",
            )
            _check(
                "Article Welford variance > 0 after two observations (dim 0)",
                article["first_dim_variance"] > 0.0,
                f"actual={article['first_dim_variance']:.6f}",
            )
            _check("Article.schema_org_type captured",
                   article["schema_type"] == "OpinionNewsArticle")
            _check("Article.exposure_context_confidence ≈ 0.72",
                   abs(article["conf"] - 0.72) < 1e-6)
            passed += 6 if article["obs"] == 2 else 0
            failed += 6 - (6 if article["obs"] == 2 else 0)
        else:
            failed += 6

        # Publication
        pub_rows = await _query(session, _Q_PUBLICATION, url=_FIXTURE_URL)
        if _check("Publication node exists via PUBLISHED_IN", len(pub_rows) == 1):
            pub = pub_rows[0]
            _check("Publication.canonical_domain == nytimes.com",
                   pub["domain"] == "nytimes.com")
            _check("Publication.observation_count >= 2", pub["obs"] >= 2,
                   f"actual={pub['obs']}")
            _check(
                "Publication Welford mean ≈ avg (dim 0)",
                abs(pub["first_dim_mean"] - 0.55) < 0.01,
                f"actual={pub['first_dim_mean']:.6f}",
            )

        # Authors
        author_rows = await _query(session, _Q_AUTHORS, url=_FIXTURE_URL)
        _check("Two Author nodes linked via BY", len(author_rows) == 2,
               f"actual={len(author_rows)}")
        klein = next((a for a in author_rows if a["name"] == "Ezra Klein"), None)
        if _check("Ezra Klein author present", klein is not None):
            _check("Ezra Klein URL captured",
                   klein["url"] == "https://www.nytimes.com/by/ezra-klein")
            _check("Ezra Klein construct_observations == 2", klein["n"] == 2,
                   f"actual={klein['n']}")

        # Section
        section_rows = await _query(session, _Q_SECTION, url=_FIXTURE_URL)
        _check("Section 'Opinion' linked via IN_SECTION",
               len(section_rows) == 1 and section_rows[0]["name"] == "Opinion")

        # Topics with hierarchical SUBTOPIC_OF
        topic_rows = await _query(session, _Q_TOPICS, url=_FIXTURE_URL)
        _check("Two Topic nodes linked via ABOUT", len(topic_rows) == 2,
               f"actual={len(topic_rows)}")
        climate = next((t for t in topic_rows if t["name"] == "Climate Change"), None)
        if _check("Climate Change topic present", climate is not None):
            _check("Climate Change has parent 'Environment' via SUBTOPIC_OF",
                   climate["parent_name"] == "Environment",
                   f"actual={climate['parent_name']}")

        # HAS_SECTION edge with posterior
        if pub_rows and section_rows:
            has_section_rows = await _query(
                session, _Q_HAS_SECTION,
                publication_id=pub_rows[0]["id"],
                section_id=section_rows[0]["id"],
            )
            if _check("HAS_SECTION relationship exists",
                      len(has_section_rows) == 1):
                _check(
                    "HAS_SECTION centroid shifted from zero (dim 0)",
                    has_section_rows[0]["first_dim_mean"] > 0.0,
                    f"actual={has_section_rows[0]['first_dim_mean']:.6f}",
                )

        # WRITES_FOR edge with article_count
        if klein and pub_rows:
            writes_for_rows = await _query(
                session, _Q_WRITES_FOR,
                author_id=klein["id"],
                publication_id=pub_rows[0]["id"],
            )
            _check("WRITES_FOR edge exists (Ezra Klein → NYT)",
                   len(writes_for_rows) == 1)
            if writes_for_rows:
                _check(
                    "WRITES_FOR.article_count >= 2",
                    writes_for_rows[0]["articles"] >= 2,
                    f"actual={writes_for_rows[0]['articles']}",
                )

    print()
    print("=" * 72)
    print("Verification complete. Review the [PASS]/[FAIL] list above.")
    print("Any FAIL means Phase A write path has a regression to fix")
    print("before Phase B read-switch is safe.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-migration", action="store_true",
                        help="Do not attempt to apply pending migrations.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip all Neo4j writes; exercise dataclass path only.")
    args = parser.parse_args()

    if not args.dry_run and not args.skip_migration:
        print("Applying any pending migrations (runs 023 if not yet applied)…")
        asyncio.run(run_migrations())
        print()

    return asyncio.run(_verify(dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
