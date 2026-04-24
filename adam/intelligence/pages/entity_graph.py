"""
Page Entity Graph — Neo4j shadow-write service for page-intelligence entities.

Phase A substrate for the page-intelligence subsystem. Promotes Author,
Publication, Section, Topic, and Article from per-article string fields in
Redis (14-day TTL) to durable Neo4j nodes with accumulating psychological
posteriors that survive the operating lifetime.

Theoretical substrate (ADAM_THEORETICAL_FOUNDATION.md §4.2): the page is the
environmental prime. Accumulating author / publication / section / topic
posteriors provide the hierarchical shrinkage anchors for any new article's
construct-activation inference (Phase D):

    P(reader_state | article) ∝
      P(reader_state | author, publication, section, topic)   ← hierarchical prior
      × Π_i P(lexicon_i_evidence | reader_state)               ← likelihood

Schema: adam/infrastructure/neo4j/migrations/023_page_intelligence_entities.cypher

Design commitments (orientation discipline):

- Entities are first-class. Author is not a string field; it is a node with
  cross-publication identity resolution. (A12 bilateral primitive.)
- Centroid / variance updates are Welford's online algorithm computed in a
  single atomic Cypher transaction to avoid read-modify-write races under
  concurrent impressions.
- 20-dim construct-activation space matches EDGE_DIMENSIONS in
  domain_taxonomy.py — same space as BRAND_CONVERTED bilateral edges.
- Primary-metaphor axes stored as 8-dim stub (zeros) until Phase G provides
  the empirical scoring module.
- Confidence propagation is first-class on Article nodes
  (exposure_context_confidence) so downstream LinkPosterior updates in
  Phase E can weight signed rewards by how much we trust the upstream
  page-state inference.
- Shadow-write semantics: exceptions are logged but NOT raised, because
  the primary ingestion path must not be blocked by Neo4j issues during
  the migration window. Phase B flips reads to Neo4j-primary once the
  shadow-write has been verified against real traffic.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from adam.infrastructure.neo4j.client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


# =============================================================================
# SYNC → ASYNC BRIDGE — persistent background loop for fire-and-forget writes
# =============================================================================
# Mirrors the pattern established in adam/services/graph_intelligence.py:
# the Neo4j AsyncDriver binds its pool to the loop that created it, so we
# reuse a single long-lived background loop rather than spinning up a new
# one per call (which would invalidate the driver's pool).

_bg_loop: Optional[asyncio.AbstractEventLoop] = None
_bg_thread: Optional[threading.Thread] = None
_bg_lock = threading.Lock()


def _get_bg_loop() -> asyncio.AbstractEventLoop:
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            _bg_loop = asyncio.new_event_loop()

            def _run():
                asyncio.set_event_loop(_bg_loop)
                _bg_loop.run_forever()

            _bg_thread = threading.Thread(
                target=_run, daemon=True, name="PageEntityGraph-bg-loop",
            )
            _bg_thread.start()
    return _bg_loop


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine on the background loop without awaiting its
    result. Exceptions are logged via an attached callback so silent
    shadow-write failures are still observable in logs."""
    loop = _get_bg_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)

    def _on_done(fut):
        exc = fut.exception()
        if exc is not None:
            logger.warning(
                "PageEntityGraph shadow-write failed: %s", exc, exc_info=exc,
            )

    future.add_done_callback(_on_done)


# =============================================================================
# CONSTANTS — must stay in sync with domain_taxonomy.EDGE_DIMENSIONS
# =============================================================================

CONSTRUCT_DIMENSIONS: int = 20
"""20-dim edge space; matches adam/intelligence/domain_taxonomy.py.
Extending to 27 in the future: update this constant and the list-length
assertions; Neo4j list properties are length-agnostic so the schema
accommodates it without a migration."""

PRIMARY_METAPHOR_AXES: int = 8
"""8 primary metaphor axes (warmth, distance, vertical, solidity,
containment, force, path, closeness). Phase G populates. Zeros until then."""

_AUTHOR_ID_PREFIX = "author:"
_PUBLICATION_ID_PREFIX = "publication:"
_SECTION_ID_PREFIX = "section:"
_TOPIC_ID_PREFIX = "topic:"
_ARTICLE_ID_PREFIX = "article:"


# =============================================================================
# ID / SLUG NORMALIZATION
# =============================================================================

def _slugify(value: str) -> str:
    """Lowercase, strip punctuation, preserve existing hyphens, collapse
    whitespace and hyphen runs to single hyphen.

    Notes on backfill: domain_taxonomy.py uses a stricter slugify that
    strips hyphens entirely. When backfilling from its Redis keys, use
    the slugify_strict variant below so existing keys resolve to the
    same entity they did in Redis.
    """
    lowered = value.lower().strip()
    # Strip punctuation except alphanumerics, whitespace, and hyphens.
    stripped = re.sub(r"[^a-z0-9\s\-]", "", lowered)
    # Collapse whitespace-and-hyphen runs to single hyphen; trim edges.
    return re.sub(r"[\s\-]+", "-", stripped).strip("-")


def _slugify_strict(value: str) -> str:
    """Legacy-compatible slugify matching domain_taxonomy.py exactly.

    Strips hyphens entirely. Used during backfill so authors whose Redis
    slug was generated under the old rule resolve to the same Neo4j
    entity id. For new entities prefer _slugify (hyphen-preserving).
    """
    lowered = value.lower().strip()
    stripped = re.sub(r"[^a-z0-9\s]", "", lowered)
    return re.sub(r"\s+", "-", stripped).strip("-")


def _url_hash(url: str) -> str:
    """Stable short hash for article id generation (canonicalized URL)."""
    return hashlib.sha1(url.strip().lower().encode("utf-8")).hexdigest()[:16]


def author_id(slug_or_url: str) -> str:
    """Canonical Author.id. Prefer URL-derived if provided, otherwise slug."""
    if slug_or_url.startswith("http"):
        return f"{_AUTHOR_ID_PREFIX}url:{_url_hash(slug_or_url)}"
    return f"{_AUTHOR_ID_PREFIX}{_slugify(slug_or_url)}"


def publication_id(slug_or_domain: str) -> str:
    slug = _slugify(slug_or_domain.replace(".", "-"))
    return f"{_PUBLICATION_ID_PREFIX}{slug}"


def section_id(slug_or_name: str) -> str:
    return f"{_SECTION_ID_PREFIX}{_slugify(slug_or_name)}"


def topic_id(slug_or_name: str) -> str:
    return f"{_TOPIC_ID_PREFIX}{_slugify(slug_or_name)}"


def article_id(url: str) -> str:
    return f"{_ARTICLE_ID_PREFIX}{_url_hash(url)}"


# =============================================================================
# INPUT DATACLASSES — structured shapes for upsert operations
# =============================================================================

@dataclass
class AuthorUpsert:
    """Identifying information for an Author node.

    For cross-publication identity resolution, URL (from Schema.org
    Person.url) is the strongest key. Social handles are secondary.
    Name+slug is last resort and may produce per-publication-scoped
    identity collisions for common names — acceptable for MVP; Phase D+
    can add similarity-based merging via style_signature embeddings.
    """
    name: str
    url: Optional[str] = None
    social_handles: List[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return author_id(self.url if self.url else self.name)

    @property
    def slug(self) -> str:
        return _slugify(self.name)


@dataclass
class PublicationUpsert:
    """Identifying information for a Publication node (masthead level)."""
    name: str
    canonical_domain: str
    alternate_domains: List[str] = field(default_factory=list)
    publisher_parent: Optional[str] = None
    editorial_register: Optional[str] = None

    @property
    def id(self) -> str:
        return publication_id(self.canonical_domain)

    @property
    def slug(self) -> str:
        return _slugify(self.canonical_domain.replace(".", "-"))


@dataclass
class SectionUpsert:
    """Identifying information for a Section vocabulary node."""
    name: str
    description: Optional[str] = None

    @property
    def id(self) -> str:
        return section_id(self.name)

    @property
    def canonical_slug(self) -> str:
        return _slugify(self.name)


@dataclass
class TopicUpsert:
    """Identifying information for a Topic vocabulary node."""
    name: str
    description: Optional[str] = None
    is_transient: bool = False
    parent_topic_slug: Optional[str] = None

    @property
    def id(self) -> str:
        return topic_id(self.name)

    @property
    def canonical_slug(self) -> str:
        return _slugify(self.name)


@dataclass
class ArticleObservation:
    """One article observation — the top-level unit of ingestion.

    All referenced entities (authors, publication, section, topics) are
    upserted atomically with the article and its relationships. Centroid
    posteriors accumulate across all upstream entities in a single Cypher
    transaction via Welford's online algorithm.

    `construct_vector` is the inferred 20-dim activation for this article.
    Length must equal CONSTRUCT_DIMENSIONS. In Phase A (before the lexicon
    ensemble lands in Phase D), callers supply whatever inference the
    existing domain_taxonomy layer produces — the shadow-write accepts it
    and accumulates upstream; Phase D replaces that with the real
    lexicon-ensemble output.
    """
    url: str
    title: str
    publication: PublicationUpsert
    authors: List[AuthorUpsert] = field(default_factory=list)
    section: Optional[SectionUpsert] = None
    topics: List[TopicUpsert] = field(default_factory=list)
    canonical_url: Optional[str] = None
    dek: Optional[str] = None
    schema_org_type: Optional[str] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    word_count: Optional[int] = None
    image_url: Optional[str] = None
    construct_vector: List[float] = field(default_factory=list)
    exposure_context_confidence: float = 0.0
    lexicon_evidence: Dict[str, Any] = field(default_factory=dict)

    # Attentional posture (attention-inversion principle). Scalar in [-1, 1]:
    # -1 = autopilot-dominant, +1 = vigilance-dominant, 0 = neutral.
    # None when upstream has not scored it (empty-prior semantic — the
    # Welford update path skips this observation rather than imputing 0).
    attentional_posture: Optional[float] = None

    # Claude-scored #7 MV features. All None-valued when upstream has not
    # scored the article (same empty-prior semantics as attentional_posture).
    # Storage wiring (Welford updates on the entity graph) lands in the
    # follow-up slice; this field carries the observation into the ingest
    # path so the scoring pipeline has a stable shape today.
    #
    # See adam/intelligence/pages/claude_feature_scoring.py for shape.
    register_score: Optional[float] = None               # [-1, 1]
    register_category: Optional[str] = None              # REGISTER_CATEGORIES
    register_confidence: Optional[float] = None          # [0, 1]

    primary_metaphor_density: Optional[float] = None     # [0, 1]
    primary_metaphor_axes_scored: Optional[List[float]] = None  # 8 dims [0,1]
    primary_metaphor_confidence: Optional[float] = None  # [0, 1]

    goal_activation_profile: Optional[Dict[str, float]] = None  # 8 goals [0,1]
    goal_activation_confidence: Optional[float] = None   # [0, 1]

    temporal_horizon_induction: Optional[float] = None   # [-1, 1]
    temporal_horizon_confidence: Optional[float] = None  # [0, 1]

    processing_fluency: Optional[float] = None           # [0, 1]
    processing_fluency_confidence: Optional[float] = None  # [0, 1]

    @property
    def id(self) -> str:
        return article_id(self.canonical_url or self.url)

    def validate(self) -> None:
        """Raise ValueError if required invariants are violated."""
        if not self.url:
            raise ValueError("ArticleObservation.url is required")
        if not self.title:
            raise ValueError("ArticleObservation.title is required")
        if self.construct_vector and len(self.construct_vector) != CONSTRUCT_DIMENSIONS:
            raise ValueError(
                f"construct_vector length {len(self.construct_vector)} != "
                f"{CONSTRUCT_DIMENSIONS}"
            )
        if not (0.0 <= self.exposure_context_confidence <= 1.0):
            raise ValueError(
                f"exposure_context_confidence {self.exposure_context_confidence} "
                "outside [0, 1]"
            )
        if self.attentional_posture is not None and not (
            -1.0 <= self.attentional_posture <= 1.0
        ):
            raise ValueError(
                f"attentional_posture {self.attentional_posture} outside [-1, 1]"
            )
        # Claude-scored features.
        if self.register_score is not None and not (-1.0 <= self.register_score <= 1.0):
            raise ValueError(
                f"register_score {self.register_score} outside [-1, 1]"
            )
        if self.register_confidence is not None and not (0.0 <= self.register_confidence <= 1.0):
            raise ValueError(
                f"register_confidence {self.register_confidence} outside [0, 1]"
            )
        if self.primary_metaphor_density is not None and not (
            0.0 <= self.primary_metaphor_density <= 1.0
        ):
            raise ValueError(
                f"primary_metaphor_density {self.primary_metaphor_density} outside [0, 1]"
            )
        if (
            self.primary_metaphor_axes_scored is not None
            and len(self.primary_metaphor_axes_scored) != PRIMARY_METAPHOR_AXES
        ):
            raise ValueError(
                f"primary_metaphor_axes_scored length "
                f"{len(self.primary_metaphor_axes_scored)} != {PRIMARY_METAPHOR_AXES}"
            )
        if self.primary_metaphor_axes_scored is not None:
            for i, v in enumerate(self.primary_metaphor_axes_scored):
                if not (0.0 <= v <= 1.0):
                    raise ValueError(
                        f"primary_metaphor_axes_scored[{i}] {v} outside [0, 1]"
                    )
        if self.primary_metaphor_confidence is not None and not (
            0.0 <= self.primary_metaphor_confidence <= 1.0
        ):
            raise ValueError(
                f"primary_metaphor_confidence {self.primary_metaphor_confidence} "
                "outside [0, 1]"
            )
        if self.goal_activation_profile is not None:
            for goal_id, v in self.goal_activation_profile.items():
                if not (0.0 <= v <= 1.0):
                    raise ValueError(
                        f"goal_activation_profile[{goal_id}] {v} outside [0, 1]"
                    )
        if self.goal_activation_confidence is not None and not (
            0.0 <= self.goal_activation_confidence <= 1.0
        ):
            raise ValueError(
                f"goal_activation_confidence {self.goal_activation_confidence} "
                "outside [0, 1]"
            )
        if self.temporal_horizon_induction is not None and not (
            -1.0 <= self.temporal_horizon_induction <= 1.0
        ):
            raise ValueError(
                f"temporal_horizon_induction {self.temporal_horizon_induction} "
                "outside [-1, 1]"
            )
        if self.temporal_horizon_confidence is not None and not (
            0.0 <= self.temporal_horizon_confidence <= 1.0
        ):
            raise ValueError(
                f"temporal_horizon_confidence {self.temporal_horizon_confidence} "
                "outside [0, 1]"
            )
        if self.processing_fluency is not None and not (
            0.0 <= self.processing_fluency <= 1.0
        ):
            raise ValueError(
                f"processing_fluency {self.processing_fluency} outside [0, 1]"
            )
        if self.processing_fluency_confidence is not None and not (
            0.0 <= self.processing_fluency_confidence <= 1.0
        ):
            raise ValueError(
                f"processing_fluency_confidence {self.processing_fluency_confidence} "
                "outside [0, 1]"
            )


# =============================================================================
# CYPHER — upsert with atomic Welford centroid update
# =============================================================================
#
# Welford's online algorithm (numerically-stable running mean + variance):
#
#     new_n     = old_n + 1
#     delta_1   = x - old_mean
#     new_mean  = old_mean + delta_1 / new_n
#     delta_2   = x - new_mean
#     new_M2    = old_M2 + delta_1 * delta_2
#     new_var   = new_M2 / new_n                (biased estimator)
#
# We store variance directly (not M2). To reconstruct M2 on update:
#     old_M2 = old_var * old_n
# …which is valid at n ≥ 1. At n = 0 the initial vector is zeros and the
# first update seeds mean = x, variance = 0 correctly via the formula.

_ZERO_CONSTRUCT = [0.0] * CONSTRUCT_DIMENSIONS
_ZERO_METAPHOR = [0.0] * PRIMARY_METAPHOR_AXES


# Author upsert with Welford centroid update
_CYPHER_UPSERT_AUTHOR = """
MERGE (a:Author {id: $author_id})
  ON CREATE SET
    a.name = $name,
    a.slug = $slug,
    a.url = $url,
    a.social_handles = $social_handles,
    a.observation_count = 0,
    a.first_seen = datetime(),
    a.construct_centroid = $zero_construct,
    a.construct_variance = $zero_construct,
    a.construct_observations = 0,
    a.primary_metaphor_axes = $zero_metaphor,
    a.style_signature = [],
    a.attentional_posture = 0.0,
    a.attentional_posture_variance = 0.0,
    a.attentional_posture_observations = 0
  ON MATCH SET
    a.last_seen = datetime(),
    a.name = coalesce(a.name, $name),
    a.slug = coalesce(a.slug, $slug),
    a.url = coalesce(a.url, $url)
SET
    a.last_updated = datetime(),
    a.observation_count = a.observation_count + 1
WITH a, $construct_vector AS x, size($construct_vector) > 0 AS has_vector,
     a.construct_observations AS old_n,
     a.construct_centroid AS old_mean,
     a.construct_variance AS old_var
WITH a, x, has_vector, old_n, old_mean, old_var,
     CASE WHEN has_vector THEN old_n + 1 ELSE old_n END AS new_n
WITH a, x, has_vector, old_n, old_mean, old_var, new_n,
     CASE WHEN has_vector
          THEN [i IN range(0, size(x) - 1) |
                old_mean[i] + (x[i] - old_mean[i]) / toFloat(new_n)]
          ELSE old_mean END AS new_mean
WITH a, x, has_vector, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN has_vector
          THEN [i IN range(0, size(x) - 1) |
                ((old_var[i] * toFloat(old_n))
                 + (x[i] - old_mean[i]) * (x[i] - new_mean[i]))
                / toFloat(new_n)]
          ELSE old_var END AS new_var
SET a.construct_centroid = new_mean,
    a.construct_variance = new_var,
    a.construct_observations = new_n
RETURN a.id AS id, a.observation_count AS observations,
       a.construct_observations AS construct_observations
"""


# Publication upsert with Welford centroid update (mirrors Author pattern)
_CYPHER_UPSERT_PUBLICATION = """
MERGE (p:Publication {id: $publication_id})
  ON CREATE SET
    p.name = $name,
    p.canonical_domain = $canonical_domain,
    p.alternate_domains = $alternate_domains,
    p.slug = $slug,
    p.publisher_parent = $publisher_parent,
    p.editorial_register = $editorial_register,
    p.observation_count = 0,
    p.first_seen = datetime(),
    p.construct_centroid = $zero_construct,
    p.construct_variance = $zero_construct,
    p.construct_observations = 0,
    p.primary_metaphor_axes = $zero_metaphor,
    p.attentional_posture = 0.0,
    p.attentional_posture_variance = 0.0,
    p.attentional_posture_observations = 0
  ON MATCH SET
    p.last_seen = datetime(),
    p.name = coalesce(p.name, $name),
    p.publisher_parent = coalesce(p.publisher_parent, $publisher_parent),
    p.editorial_register = coalesce(p.editorial_register, $editorial_register)
SET
    p.last_updated = datetime(),
    p.observation_count = p.observation_count + 1
WITH p, $construct_vector AS x, size($construct_vector) > 0 AS has_vector,
     p.construct_observations AS old_n,
     p.construct_centroid AS old_mean,
     p.construct_variance AS old_var
WITH p, x, has_vector, old_n, old_mean, old_var,
     CASE WHEN has_vector THEN old_n + 1 ELSE old_n END AS new_n
WITH p, x, has_vector, old_n, old_mean, old_var, new_n,
     CASE WHEN has_vector
          THEN [i IN range(0, size(x) - 1) |
                old_mean[i] + (x[i] - old_mean[i]) / toFloat(new_n)]
          ELSE old_mean END AS new_mean
WITH p, x, has_vector, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN has_vector
          THEN [i IN range(0, size(x) - 1) |
                ((old_var[i] * toFloat(old_n))
                 + (x[i] - old_mean[i]) * (x[i] - new_mean[i]))
                / toFloat(new_n)]
          ELSE old_var END AS new_var
SET p.construct_centroid = new_mean,
    p.construct_variance = new_var,
    p.construct_observations = new_n
RETURN p.id AS id, p.observation_count AS observations
"""


# Section and Topic are vocabulary nodes — no per-entity centroid (that
# lives on the HAS_SECTION / COVERS_TOPIC relationship edges for per-
# publication granularity).
_CYPHER_UPSERT_SECTION = """
MERGE (s:Section {id: $section_id})
  ON CREATE SET
    s.name = $name,
    s.canonical_slug = $canonical_slug,
    s.description = $description,
    s.observation_count = 0,
    s.first_seen = datetime()
SET
    s.observation_count = s.observation_count + 1,
    s.last_updated = datetime(),
    s.name = coalesce(s.name, $name)
RETURN s.id AS id
"""


_CYPHER_UPSERT_TOPIC = """
MERGE (t:Topic {id: $topic_id})
  ON CREATE SET
    t.name = $name,
    t.canonical_slug = $canonical_slug,
    t.description = $description,
    t.is_transient = $is_transient,
    t.observation_count = 0,
    t.first_seen = datetime()
SET
    t.observation_count = t.observation_count + 1,
    t.last_updated = datetime()
RETURN t.id AS id
"""


# Article upsert — the per-URL entity carries article-specific centroid
# posteriors (article posteriors are hierarchical prior × lexicon evidence
# once Phase D lands; in Phase A we accept whatever upstream supplies).
_CYPHER_UPSERT_ARTICLE = """
MERGE (ar:Article {id: $article_id})
  ON CREATE SET
    ar.url = $url,
    ar.canonical_url = $canonical_url,
    ar.title = $title,
    ar.dek = $dek,
    ar.schema_org_type = $schema_org_type,
    ar.published_at = CASE WHEN $published_at IS NULL THEN null
                           ELSE datetime($published_at) END,
    ar.updated_at = CASE WHEN $updated_at IS NULL THEN null
                         ELSE datetime($updated_at) END,
    ar.word_count = $word_count,
    ar.image_url = $image_url,
    ar.publication_id = $publication_id,
    ar.author_ids = $author_ids,
    ar.section_id = $section_id,
    ar.topic_ids = $topic_ids,
    ar.construct_centroid = $zero_construct,
    ar.construct_variance = $zero_construct,
    ar.construct_observations = 0,
    ar.primary_metaphor_axes = $zero_metaphor,
    ar.exposure_context_confidence = 0.0,
    ar.observation_count = 0,
    ar.first_seen = datetime(),
    ar.attentional_posture = 0.0,
    ar.attentional_posture_variance = 0.0,
    ar.attentional_posture_observations = 0
SET
    ar.observation_count = ar.observation_count + 1,
    ar.last_updated = datetime(),
    ar.exposure_context_confidence =
        CASE WHEN $exposure_context_confidence > ar.exposure_context_confidence
             THEN $exposure_context_confidence
             ELSE ar.exposure_context_confidence END,
    ar.lexicon_evidence =
        CASE WHEN $lexicon_evidence IS NULL OR size(keys($lexicon_evidence)) = 0
             THEN ar.lexicon_evidence
             ELSE $lexicon_evidence END
WITH ar, $construct_vector AS x, size($construct_vector) > 0 AS has_vector,
     ar.construct_observations AS old_n,
     ar.construct_centroid AS old_mean,
     ar.construct_variance AS old_var
WITH ar, x, has_vector, old_n, old_mean, old_var,
     CASE WHEN has_vector THEN old_n + 1 ELSE old_n END AS new_n
WITH ar, x, has_vector, old_n, old_mean, old_var, new_n,
     CASE WHEN has_vector
          THEN [i IN range(0, size(x) - 1) |
                old_mean[i] + (x[i] - old_mean[i]) / toFloat(new_n)]
          ELSE old_mean END AS new_mean
WITH ar, x, has_vector, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN has_vector
          THEN [i IN range(0, size(x) - 1) |
                ((old_var[i] * toFloat(old_n))
                 + (x[i] - old_mean[i]) * (x[i] - new_mean[i]))
                / toFloat(new_n)]
          ELSE old_var END AS new_var
SET ar.construct_centroid = new_mean,
    ar.construct_variance = new_var,
    ar.construct_observations = new_n
RETURN ar.id AS id
"""


# Relationship writes — run after all entities exist
_CYPHER_WRITE_BY_RELATIONSHIP = """
MATCH (ar:Article {id: $article_id})
MATCH (a:Author {id: $author_id})
MERGE (ar)-[r:BY]->(a)
  ON CREATE SET r.byline_position = $byline_position
"""


_CYPHER_WRITE_PUBLISHED_IN = """
MATCH (ar:Article {id: $article_id})
MATCH (p:Publication {id: $publication_id})
MERGE (ar)-[:PUBLISHED_IN]->(p)
"""


_CYPHER_WRITE_IN_SECTION = """
MATCH (ar:Article {id: $article_id})
MATCH (s:Section {id: $section_id})
MERGE (ar)-[:IN_SECTION]->(s)
"""


_CYPHER_WRITE_ABOUT = """
MATCH (ar:Article {id: $article_id})
MATCH (t:Topic {id: $topic_id})
MERGE (ar)-[:ABOUT]->(t)
"""


_CYPHER_WRITE_SUBTOPIC_OF = """
MATCH (child:Topic {id: $child_id})
MATCH (parent:Topic {id: $parent_id})
MERGE (child)-[:SUBTOPIC_OF]->(parent)
"""


# Writes_for relationship with counters — accumulates per (author, publication).
_CYPHER_WRITE_WRITES_FOR = """
MATCH (a:Author {id: $author_id})
MATCH (p:Publication {id: $publication_id})
MERGE (a)-[r:WRITES_FOR]->(p)
  ON CREATE SET
    r.article_count = 0,
    r.first_written = datetime()
SET
    r.article_count = r.article_count + 1,
    r.last_written = datetime()
"""


# Per-publication-per-section activation posterior on the HAS_SECTION edge
# (Welford across the edge, exactly like entity-level posteriors).
_CYPHER_WRITE_HAS_SECTION = """
MATCH (p:Publication {id: $publication_id})
MATCH (s:Section {id: $section_id})
MERGE (p)-[r:HAS_SECTION]->(s)
  ON CREATE SET
    r.article_count = 0,
    r.observation_count = 0,
    r.construct_centroid = $zero_construct,
    r.construct_variance = $zero_construct,
    r.attentional_posture = 0.0,
    r.attentional_posture_variance = 0.0,
    r.attentional_posture_observations = 0
SET
    r.article_count = r.article_count + 1,
    r.observation_count = r.observation_count + 1,
    r.last_updated = datetime()
WITH r, $construct_vector AS x, size($construct_vector) > 0 AS has_vector,
     r.observation_count - 1 AS old_n,
     r.construct_centroid AS old_mean,
     r.construct_variance AS old_var
WITH r, x, has_vector, old_n, old_mean, old_var,
     CASE WHEN has_vector THEN old_n + 1 ELSE old_n END AS new_n
WITH r, x, has_vector, old_n, old_mean, old_var, new_n,
     CASE WHEN has_vector AND new_n > 0
          THEN [i IN range(0, size(x) - 1) |
                old_mean[i] + (x[i] - old_mean[i]) / toFloat(new_n)]
          ELSE old_mean END AS new_mean
WITH r, x, has_vector, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN has_vector AND new_n > 0
          THEN [i IN range(0, size(x) - 1) |
                ((old_var[i] * toFloat(old_n))
                 + (x[i] - old_mean[i]) * (x[i] - new_mean[i]))
                / toFloat(new_n)]
          ELSE old_var END AS new_var
SET r.construct_centroid = new_mean,
    r.construct_variance = new_var
"""


_CYPHER_WRITE_COVERS_TOPIC_AUTHOR = """
MATCH (a:Author {id: $author_id})
MATCH (t:Topic {id: $topic_id})
MERGE (a)-[r:COVERS_TOPIC]->(t)
  ON CREATE SET r.article_count = 0
SET r.article_count = r.article_count + 1
"""


_CYPHER_WRITE_COVERS_TOPIC_PUBLICATION = """
MATCH (p:Publication {id: $publication_id})
MATCH (t:Topic {id: $topic_id})
MERGE (p)-[r:COVERS_TOPIC]->(t)
  ON CREATE SET r.article_count = 0
SET r.article_count = r.article_count + 1
"""


# =============================================================================
# ATTENTIONAL POSTURE — scalar Welford updates (attention-inversion addition)
# =============================================================================
#
# These run AFTER the main entity upserts, only when upstream has supplied a
# posture score. Empty-prior semantic: if posture is not scored, the entity's
# running posterior is not touched (never imputes 0 to avoid contaminating
# the accumulated signal with no-evidence observations).
#
# coalesce() on the read side protects against nodes created before this
# migration when the ON CREATE SET initializers were not present.

_CYPHER_UPDATE_AUTHOR_POSTURE = """
MATCH (a:Author {id: $id})
WITH a, $posture AS x,
     coalesce(a.attentional_posture_observations, 0) AS old_n,
     coalesce(a.attentional_posture, 0.0) AS old_mean,
     coalesce(a.attentional_posture_variance, 0.0) AS old_var
WITH a, x, old_n, old_mean, old_var, old_n + 1 AS new_n
WITH a, x, old_n, old_mean, old_var, new_n,
     old_mean + (x - old_mean) / toFloat(new_n) AS new_mean
WITH a, x, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN new_n > 0
          THEN ((old_var * toFloat(old_n))
                + (x - old_mean) * (x - new_mean)) / toFloat(new_n)
          ELSE old_var END AS new_var
SET a.attentional_posture = new_mean,
    a.attentional_posture_variance = new_var,
    a.attentional_posture_observations = new_n
"""


_CYPHER_UPDATE_PUBLICATION_POSTURE = """
MATCH (p:Publication {id: $id})
WITH p, $posture AS x,
     coalesce(p.attentional_posture_observations, 0) AS old_n,
     coalesce(p.attentional_posture, 0.0) AS old_mean,
     coalesce(p.attentional_posture_variance, 0.0) AS old_var
WITH p, x, old_n, old_mean, old_var, old_n + 1 AS new_n
WITH p, x, old_n, old_mean, old_var, new_n,
     old_mean + (x - old_mean) / toFloat(new_n) AS new_mean
WITH p, x, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN new_n > 0
          THEN ((old_var * toFloat(old_n))
                + (x - old_mean) * (x - new_mean)) / toFloat(new_n)
          ELSE old_var END AS new_var
SET p.attentional_posture = new_mean,
    p.attentional_posture_variance = new_var,
    p.attentional_posture_observations = new_n
"""


_CYPHER_UPDATE_ARTICLE_POSTURE = """
MATCH (ar:Article {id: $id})
WITH ar, $posture AS x,
     coalesce(ar.attentional_posture_observations, 0) AS old_n,
     coalesce(ar.attentional_posture, 0.0) AS old_mean,
     coalesce(ar.attentional_posture_variance, 0.0) AS old_var
WITH ar, x, old_n, old_mean, old_var, old_n + 1 AS new_n
WITH ar, x, old_n, old_mean, old_var, new_n,
     old_mean + (x - old_mean) / toFloat(new_n) AS new_mean
WITH ar, x, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN new_n > 0
          THEN ((old_var * toFloat(old_n))
                + (x - old_mean) * (x - new_mean)) / toFloat(new_n)
          ELSE old_var END AS new_var
SET ar.attentional_posture = new_mean,
    ar.attentional_posture_variance = new_var,
    ar.attentional_posture_observations = new_n
"""


_CYPHER_UPDATE_HAS_SECTION_POSTURE = """
MATCH (p:Publication {id: $publication_id})-[r:HAS_SECTION]->(s:Section {id: $section_id})
WITH r, $posture AS x,
     coalesce(r.attentional_posture_observations, 0) AS old_n,
     coalesce(r.attentional_posture, 0.0) AS old_mean,
     coalesce(r.attentional_posture_variance, 0.0) AS old_var
WITH r, x, old_n, old_mean, old_var, old_n + 1 AS new_n
WITH r, x, old_n, old_mean, old_var, new_n,
     old_mean + (x - old_mean) / toFloat(new_n) AS new_mean
WITH r, x, old_n, old_mean, old_var, new_n, new_mean,
     CASE WHEN new_n > 0
          THEN ((old_var * toFloat(old_n))
                + (x - old_mean) * (x - new_mean)) / toFloat(new_n)
          ELSE old_var END AS new_var
SET r.attentional_posture = new_mean,
    r.attentional_posture_variance = new_var,
    r.attentional_posture_observations = new_n
"""


# =============================================================================
# SERVICE
# =============================================================================

class PageEntityGraph:
    """Neo4j shadow-write service for Author / Publication / Section / Topic /
    Article entities with accumulating hierarchical psychological posteriors.

    Phase A usage — shadow-writes alongside the existing Redis taxonomy
    writes in `adam/intelligence/domain_taxonomy.py`. In Phase B the
    read path switches to Neo4j-primary.

    All methods swallow Neo4j errors and log them, so the Redis primary
    path is never blocked by transient graph unavailability. Explicit
    error-propagation modes can be added later if a caller needs them.
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        self._client = client or get_neo4j_client()

    def record_article_sync(self, article: ArticleObservation) -> None:
        """Fire-and-forget shadow-write from synchronous code (e.g., the
        Redis path in domain_taxonomy.py). Returns immediately; the write
        completes asynchronously on the background loop. Exceptions are
        logged via the fire-and-forget callback but never raised."""
        _fire_and_forget(self.record_article(article))

    async def record_article(self, article: ArticleObservation) -> Optional[str]:
        """Write Author + Publication + Section + Topic + Article + all
        relationships for a single article observation. Returns the
        Article.id on success, None on failure (errors are logged).

        Idempotent — safe to call multiple times for the same article.
        Each call increments observation_count on all touched entities
        and folds the construct_vector into the running Welford posteriors.
        """
        try:
            article.validate()
        except ValueError as exc:
            logger.warning("ArticleObservation validation failed: %s", exc)
            return None

        if not self._client.is_connected:
            connected = await self._client.connect()
            if not connected:
                logger.debug(
                    "PageEntityGraph shadow-write skipped: Neo4j unavailable"
                )
                return None

        try:
            async with await self._client.session() as session:
                await self._write_one(session, article)
            return article.id
        except Exception as exc:  # noqa: BLE001 — shadow-write must not raise
            logger.warning(
                "PageEntityGraph shadow-write failed for %s: %s",
                article.url, exc, exc_info=True,
            )
            return None

    async def _write_one(self, session, article: ArticleObservation) -> None:
        vector = self._normalize_vector(article.construct_vector)

        # Upsert Publication (always present).
        await session.run(
            _CYPHER_UPSERT_PUBLICATION,
            publication_id=article.publication.id,
            name=article.publication.name,
            canonical_domain=article.publication.canonical_domain,
            alternate_domains=article.publication.alternate_domains,
            slug=article.publication.slug,
            publisher_parent=article.publication.publisher_parent,
            editorial_register=article.publication.editorial_register,
            construct_vector=vector,
            zero_construct=_ZERO_CONSTRUCT,
            zero_metaphor=_ZERO_METAPHOR,
        )

        # Upsert each Author (zero or more; common case 1).
        for author in article.authors:
            await session.run(
                _CYPHER_UPSERT_AUTHOR,
                author_id=author.id,
                name=author.name,
                slug=author.slug,
                url=author.url,
                social_handles=author.social_handles,
                construct_vector=vector,
                zero_construct=_ZERO_CONSTRUCT,
                zero_metaphor=_ZERO_METAPHOR,
            )

        # Upsert Section (optional).
        if article.section is not None:
            await session.run(
                _CYPHER_UPSERT_SECTION,
                section_id=article.section.id,
                name=article.section.name,
                canonical_slug=article.section.canonical_slug,
                description=article.section.description,
            )

        # Upsert each Topic.
        for topic in article.topics:
            await session.run(
                _CYPHER_UPSERT_TOPIC,
                topic_id=topic.id,
                name=topic.name,
                canonical_slug=topic.canonical_slug,
                description=topic.description,
                is_transient=topic.is_transient,
            )

        # Upsert Article.
        await session.run(
            _CYPHER_UPSERT_ARTICLE,
            article_id=article.id,
            url=article.url,
            canonical_url=article.canonical_url,
            title=article.title,
            dek=article.dek,
            schema_org_type=article.schema_org_type,
            published_at=article.published_at.isoformat() if article.published_at else None,
            updated_at=article.updated_at.isoformat() if article.updated_at else None,
            word_count=article.word_count,
            image_url=article.image_url,
            publication_id=article.publication.id,
            author_ids=[a.id for a in article.authors],
            section_id=article.section.id if article.section else None,
            topic_ids=[t.id for t in article.topics],
            exposure_context_confidence=article.exposure_context_confidence,
            lexicon_evidence=article.lexicon_evidence,
            construct_vector=vector,
            zero_construct=_ZERO_CONSTRUCT,
            zero_metaphor=_ZERO_METAPHOR,
        )

        # Write relationships.
        await session.run(
            _CYPHER_WRITE_PUBLISHED_IN,
            article_id=article.id,
            publication_id=article.publication.id,
        )

        for position, author in enumerate(article.authors, start=1):
            await session.run(
                _CYPHER_WRITE_BY_RELATIONSHIP,
                article_id=article.id,
                author_id=author.id,
                byline_position=position,
            )
            await session.run(
                _CYPHER_WRITE_WRITES_FOR,
                author_id=author.id,
                publication_id=article.publication.id,
            )

        if article.section is not None:
            await session.run(
                _CYPHER_WRITE_IN_SECTION,
                article_id=article.id,
                section_id=article.section.id,
            )
            await session.run(
                _CYPHER_WRITE_HAS_SECTION,
                publication_id=article.publication.id,
                section_id=article.section.id,
                construct_vector=vector,
                zero_construct=_ZERO_CONSTRUCT,
            )

        for topic in article.topics:
            await session.run(
                _CYPHER_WRITE_ABOUT,
                article_id=article.id,
                topic_id=topic.id,
            )
            await session.run(
                _CYPHER_WRITE_COVERS_TOPIC_PUBLICATION,
                publication_id=article.publication.id,
                topic_id=topic.id,
            )
            for author in article.authors:
                await session.run(
                    _CYPHER_WRITE_COVERS_TOPIC_AUTHOR,
                    author_id=author.id,
                    topic_id=topic.id,
                )
            # Subtopic hierarchy
            if topic.parent_topic_slug:
                parent_id = topic_id(topic.parent_topic_slug)
                await session.run(
                    _CYPHER_UPSERT_TOPIC,
                    topic_id=parent_id,
                    name=topic.parent_topic_slug,
                    canonical_slug=_slugify(topic.parent_topic_slug),
                    description=None,
                    is_transient=False,
                )
                await session.run(
                    _CYPHER_WRITE_SUBTOPIC_OF,
                    child_id=topic.id,
                    parent_id=parent_id,
                )

        # Attentional posture (attention-inversion addition) — scalar Welford
        # updates on Author, Publication, Article, and the HAS_SECTION edge.
        # Runs only when upstream supplied a posture score; otherwise the
        # entities' running posteriors are untouched (empty-prior semantic).
        if article.attentional_posture is not None:
            # Defensive clamp in case a caller violated the validate() contract.
            posture = max(-1.0, min(1.0, float(article.attentional_posture)))

            await session.run(
                _CYPHER_UPDATE_PUBLICATION_POSTURE,
                id=article.publication.id,
                posture=posture,
            )

            for author in article.authors:
                await session.run(
                    _CYPHER_UPDATE_AUTHOR_POSTURE,
                    id=author.id,
                    posture=posture,
                )

            await session.run(
                _CYPHER_UPDATE_ARTICLE_POSTURE,
                id=article.id,
                posture=posture,
            )

            if article.section is not None:
                await session.run(
                    _CYPHER_UPDATE_HAS_SECTION_POSTURE,
                    publication_id=article.publication.id,
                    section_id=article.section.id,
                    posture=posture,
                )

    @staticmethod
    def _normalize_vector(vector: Sequence[float]) -> List[float]:
        """Pad / truncate the construct vector to CONSTRUCT_DIMENSIONS.

        In practice callers should always supply a full 20-dim vector (or
        an empty list to skip the centroid update). This coercion exists
        to guard against accidental shape mismatches during migration.
        """
        if not vector:
            return []
        if len(vector) == CONSTRUCT_DIMENSIONS:
            return list(vector)
        if len(vector) > CONSTRUCT_DIMENSIONS:
            return list(vector[:CONSTRUCT_DIMENSIONS])
        # Pad short vectors with zeros — logs a warning because this
        # indicates a caller bug, not a normal operating condition.
        logger.warning(
            "construct_vector length %d padded to %d with zeros",
            len(vector), CONSTRUCT_DIMENSIONS,
        )
        padded = list(vector) + [0.0] * (CONSTRUCT_DIMENSIONS - len(vector))
        return padded


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_service: Optional[PageEntityGraph] = None


def get_page_entity_graph() -> PageEntityGraph:
    """Module-level accessor for the singleton PageEntityGraph service."""
    global _service
    if _service is None:
        _service = PageEntityGraph()
    return _service
