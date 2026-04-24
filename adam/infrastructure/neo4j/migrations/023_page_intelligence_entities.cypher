// =============================================================================
// ADAM Migration 023: Page Intelligence Entities
// (Author, Publication, Section, Topic, Article as first-class graph nodes)
//
// Per ADAM_THEORETICAL_FOUNDATION.md §2.3, §4.2: the page is the third side
// of the bilateral transaction — the environmental prime, in Bargh's frame,
// that activates goal structures in the reader before the ad ever loads.
// Prior architecture stored author/publisher as string fields on per-article
// Redis hashes with a 14-day TTL (ref: adam/intelligence/domain_taxonomy.py).
// This migration promotes them to durable Neo4j entities so their accumulated
// psychological posteriors survive operating lifetime, compound into
// hierarchical shrinkage priors for new articles, and resolve across domains
// (one Author writing for multiple Publications keeps a single entity with
// a consistent voice signature).
//
// Hierarchical construct inference chain (Phase D target):
//   P(reader_state | article) ∝
//     P(reader_state | author, publication, section, topic)      ← prior
//     × Π_i P(lexicon_i_evidence | reader_state)                  ← likelihood
//
// Entity posteriors accumulate from every observed article. Article-specific
// inferences become light Bayesian updates on top of well-characterized
// upstream priors instead of cold-start classifications.
//
// This migration is schema-only: constraints, indexes, and documented node
// shapes. No seed data — entities materialize on first observation via the
// shadow-write path from the domain_taxonomy ingestion layer (Phase A
// Python work that follows this migration).
//
// Reads still route through Redis in Phase A; the switch to Neo4j-primary
// reads lands in Phase B (task 29). Keeping writes and reads separated
// ensures the backfill is verifiable before downstream code depends on it.
// =============================================================================


// =============================================================================
// CONSTRAINTS — uniqueness keys
// =============================================================================

// Author — one node per distinct writer identity. Resolved cross-publication
// via canonical slug and, where available, Schema.org Person.url. Chris's
// directive: author voice is consistent across publications — do NOT
// publisher-scope authors. An author at CNN is the same entity as that
// author at Reuters (when identity can be established).
CREATE CONSTRAINT page_author_pk IF NOT EXISTS
FOR (a:Author) REQUIRE a.id IS UNIQUE;

// Publication — masthead-level (Vogue, Wired, NYT), NOT corporate parent.
// Condé Nast is the publisher_parent; Vogue/Wired/New Yorker are separate
// Publication nodes because editorial voice converges at the masthead.
CREATE CONSTRAINT page_publication_pk IF NOT EXISTS
FOR (p:Publication) REQUIRE p.id IS UNIQUE;

// Section — editorial area vocabulary (World News, Opinion, Style, Business).
// Shared vocabulary: one Section node per canonical slug. Per-publication
// activation lives on the (:Publication)-[:HAS_SECTION]->(:Section) edge.
CREATE CONSTRAINT page_section_pk IF NOT EXISTS
FOR (s:Section) REQUIRE s.id IS UNIQUE;

// Topic — topic vocabulary, hierarchical. Shared across publications.
// Subtopic relationships modeled via (:Topic)-[:SUBTOPIC_OF]->(:Topic).
CREATE CONSTRAINT page_topic_pk IF NOT EXISTS
FOR (t:Topic) REQUIRE t.id IS UNIQUE;

// Article — per-URL entity with its own construct-activation posterior.
// Articles accumulate impression observations and, over time, develop
// article-specific posteriors distinct from the pure hierarchical prior.
CREATE CONSTRAINT page_article_pk IF NOT EXISTS
FOR (ar:Article) REQUIRE ar.id IS UNIQUE;

// Additional uniqueness on Article.url to prevent duplicate ingestion when
// canonical resolution hasn't run yet.
CREATE CONSTRAINT page_article_url_unique IF NOT EXISTS
FOR (ar:Article) REQUIRE ar.url IS UNIQUE;


// =============================================================================
// INDEXES — access patterns
// =============================================================================

// Author access
CREATE INDEX page_author_slug_idx IF NOT EXISTS
FOR (a:Author) ON (a.slug);

CREATE INDEX page_author_url_idx IF NOT EXISTS
FOR (a:Author) ON (a.url);

CREATE INDEX page_author_observations_idx IF NOT EXISTS
FOR (a:Author) ON (a.observation_count);

// Publication access
CREATE INDEX page_publication_domain_idx IF NOT EXISTS
FOR (p:Publication) ON (p.canonical_domain);

CREATE INDEX page_publication_slug_idx IF NOT EXISTS
FOR (p:Publication) ON (p.slug);

CREATE INDEX page_publication_parent_idx IF NOT EXISTS
FOR (p:Publication) ON (p.publisher_parent);

// Section / Topic vocabulary lookup
CREATE INDEX page_section_slug_idx IF NOT EXISTS
FOR (s:Section) ON (s.canonical_slug);

CREATE INDEX page_topic_slug_idx IF NOT EXISTS
FOR (t:Topic) ON (t.canonical_slug);

// Article access — URL, canonical URL, publication, author, time-series
CREATE INDEX page_article_canonical_url_idx IF NOT EXISTS
FOR (ar:Article) ON (ar.canonical_url);

CREATE INDEX page_article_publication_idx IF NOT EXISTS
FOR (ar:Article) ON (ar.publication_id);

CREATE INDEX page_article_schema_type_idx IF NOT EXISTS
FOR (ar:Article) ON (ar.schema_org_type);

CREATE INDEX page_article_published_at_idx IF NOT EXISTS
FOR (ar:Article) ON (ar.published_at);

CREATE INDEX page_article_observations_idx IF NOT EXISTS
FOR (ar:Article) ON (ar.observation_count);

// Relationship indexes for frequently-traversed edges
CREATE INDEX page_writes_for_article_count_idx IF NOT EXISTS
FOR ()-[r:WRITES_FOR]-() ON (r.article_count);

CREATE INDEX page_has_section_observations_idx IF NOT EXISTS
FOR ()-[r:HAS_SECTION]-() ON (r.observation_count);

CREATE INDEX page_covers_topic_article_count_idx IF NOT EXISTS
FOR ()-[r:COVERS_TOPIC]-() ON (r.article_count);


// =============================================================================
// NODE DEFINITIONS (documented shape; Cypher is schemaless)
// =============================================================================

// -------- Author --------
// id: string                        — format "author:{slug}" or "author:{url-hash}"
// name: string                      — display name (e.g., "Jane Smith")
// slug: string                      — lowercased, punctuation-stripped, hyphenated
// url: string | null                — Schema.org Person.url (canonical cross-pub key)
// social_handles: list<string>      — Twitter/LinkedIn/Substack handles, for cross-
//                                     pub identity resolution
// observation_count: int            — number of articles observed under this author
// first_seen: datetime              — first article observation
// last_seen: datetime               — most recent article observation
// last_updated: datetime            — last posterior update
// construct_centroid: list<float>   — 20-dim edge-space centroid (same dims as
//                                     BRAND_CONVERTED edges). Running mean via
//                                     Welford's algorithm in the service layer.
// construct_variance: list<float>   — 20-dim per-dimension Welford variance.
//                                     Used as shrinkage strength in hierarchical
//                                     Bayes — sparse authors shrink hard toward
//                                     publication+section priors.
// construct_observations: int       — observations contributing to centroid
//                                     (may differ from observation_count if
//                                     some articles lacked construct inference)
// primary_metaphor_axes: list<float> — 8-dim stub (warmth/cold, distance/close,
//                                     vertical, solidity, containment, force,
//                                     path, closeness). Populated in Phase G.
// style_signature: list<float>      — optional dense embedding of author voice
//                                     for similarity-based identity resolution.
//                                     Stub until style-encoding service exists.


// -------- Publication --------
// id: string                        — format "publication:{slug}"
// name: string                      — display name (e.g., "The New York Times")
// canonical_domain: string          — primary domain (e.g., "nytimes.com")
// alternate_domains: list<string>   — additional domains (e.g., "nyt.com")
// slug: string                      — canonical slug for id generation
// publisher_parent: string | null   — corporate parent (e.g., "Condé Nast").
//                                     Stored as string for future roll-up; a
//                                     dedicated Publisher node can be added
//                                     later if corporate-level posteriors
//                                     become load-bearing.
// observation_count: int            — total articles observed at this publication
// first_seen: datetime
// last_seen: datetime
// last_updated: datetime
// construct_centroid: list<float>   — 20-dim publication-level centroid
// construct_variance: list<float>   — 20-dim per-dimension variance
// construct_observations: int
// primary_metaphor_axes: list<float> — 8-dim stub
// editorial_register: string | null — coarse register tag ("prestige_press",
//                                     "tabloid", "trade", "opinion_journal",
//                                     "wire_service", "long_form_magazine").
//                                     Inferred or manually assigned; shapes
//                                     cognitive_load priors.


// -------- Section --------
// id: string                        — format "section:{canonical_slug}"
// name: string                      — display name (e.g., "World News")
// canonical_slug: string            — normalized identifier (e.g., "world_news")
// description: string | null        — human-readable description
// observation_count: int            — total articles observed in this section
//                                     across all publications (vocabulary node
//                                     doesn't carry its own centroid; per-
//                                     publication activation lives on the
//                                     HAS_SECTION relationship)


// -------- Topic --------
// id: string                        — format "topic:{canonical_slug}"
// name: string                      — display name
// canonical_slug: string
// description: string | null
// observation_count: int
// is_transient: bool                — true for event-specific topics with
//                                     expected decay (e.g., "2024_election");
//                                     false for evergreen topics (e.g., "climate")


// -------- Article --------
// id: string                        — format "article:{url_hash}"
// url: string                       — canonical URL (resolved via canonical
//                                     link-rel where present)
// canonical_url: string | null      — explicit canonical if different from url
// title: string
// dek: string | null                — subtitle / standfirst
// schema_org_type: string | null    — Schema.org @type: "NewsArticle",
//                                     "OpinionArticle", "ReviewArticle",
//                                     "AnalysisNewsArticle",
//                                     "ReportageNewsArticle", "BlogPosting",
//                                     "BackgroundNewsArticle", etc.
//                                     First-class editorial-stance signal.
// published_at: datetime | null
// updated_at: datetime | null
// word_count: int | null
// image_url: string | null          — OG image or Schema.org image
// publication_id: string            — FK Publication.id (also materialized
//                                     as a relationship; duplicated here
//                                     for index-based filtering)
// author_ids: list<string>          — FK Author.id list (also via :BY edges)
// section_id: string | null         — FK Section.id (also via :IN_SECTION)
// topic_ids: list<string>           — FK Topic.id list (also via :ABOUT)
// construct_centroid: list<float>   — 20-dim article-specific posterior
//                                     (hierarchical prior × lexicon evidence)
// construct_variance: list<float>   — 20-dim per-dimension uncertainty
// construct_observations: int       — lexicon passes contributing to centroid
//                                     (articles can be re-inferred over time
//                                     as lexicon updates arrive)
// primary_metaphor_axes: list<float> — 8-dim stub
// exposure_context_confidence: float — overall confidence of the page-state
//                                     inference for this article. Propagates
//                                     into LinkPosterior.update_signed() as
//                                     the multiplier that protects theoretical
//                                     learning from shallow upstream context.
//                                     Range 0..1. Low confidence → small
//                                     downstream posterior movement regardless
//                                     of outcome magnitude.
// lexicon_evidence: map             — per-lexicon raw scores retained for
//                                     traceability (e.g., {"empath": {...},
//                                     "nrc_vad": {...}, "emfd": {...}}).
//                                     Supports audit of which lexicon drove
//                                     which construct dimension.
// observation_count: int            — impressions served on this article
// first_seen: datetime              — first ingestion time
// last_updated: datetime            — most recent posterior update


// =============================================================================
// RELATIONSHIPS (documented shape)
// =============================================================================

// (:Article)-[:BY {byline_position: int}]->(:Author)
//   byline_position: 1 for first author, 2 for co-authors, etc.
//
// (:Article)-[:PUBLISHED_IN]->(:Publication)
//   No extra properties — the publication_id duplicated on Article node
//   covers index-based filtering.
//
// (:Article)-[:IN_SECTION]->(:Section)
//
// (:Article)-[:ABOUT]->(:Topic)
//   One Article may have multiple ABOUT relationships for multi-topic pieces.
//
// (:Topic)-[:SUBTOPIC_OF]->(:Topic)
//   Hierarchical topic structure (e.g., "us_politics" -[:SUBTOPIC_OF]-> "politics").
//
// (:Author)-[:WRITES_FOR {
//     article_count: int,
//     first_written: datetime,
//     last_written: datetime
// }]->(:Publication)
//   Accumulates per author × publication. Enables queries like "which
//   publications does this author primarily write for" and reverse.
//
// (:Publication)-[:HAS_SECTION {
//     article_count: int,
//     observation_count: int,
//     construct_centroid: list<float>,     — 20-dim publication×section posterior
//     construct_variance: list<float>,     — 20-dim per-dimension uncertainty
//     last_updated: datetime
// }]->(:Section)
//   Per-publication per-section activation lives here. NYT-WorldNews primes
//   differently than FoxNews-WorldNews — the HAS_SECTION edge captures that.
//
// (:Author)-[:COVERS_TOPIC {article_count: int}]->(:Topic)
//   Which topics each author writes about — supports author-topic fit queries
//   and hierarchical shrinkage for topic-specific inference.
//
// (:Publication)-[:COVERS_TOPIC {article_count: int}]->(:Topic)
//   Publication-level topic coverage for editorial-focus inference.
//
// -----------------------------------------------------------------------------
// Mechanism posteriors — per-entity per-mechanism Beta posterior
// -----------------------------------------------------------------------------
//
// (:Author)-[:HAS_MECHANISM_POSTERIOR {
//     alpha: float,
//     beta: float,
//     observations: int,
//     last_updated: datetime
// }]->(:Mechanism)
//
// (:Publication)-[:HAS_MECHANISM_POSTERIOR { ... same shape ... }]->(:Mechanism)
//
// (:Article)-[:HAS_MECHANISM_POSTERIOR { ... same shape ... }]->(:Mechanism)
//   Article-level posteriors are created only for articles with enough
//   observations to justify a distinct posterior above the hierarchical
//   prior. Low-traffic articles inherit from publication × section.
//
// These posteriors are populated in Phase D when lexicon evidence drives
// outcome-weighted updates, and consumed by the bilateral cascade in
// Phase B read-switch. Phase A only materializes the schema.


// =============================================================================
// NO SEED DATA
// =============================================================================
// Author, Publication, Section, Topic, and Article nodes materialize
// lazily via the shadow-write path from the ingestion layer (Phase A
// Python work). Seeding a curated publisher list happens in Phase F
// (proactive ingestion) once the backfill + shadow-write path is
// verified end-to-end on real impressions.
