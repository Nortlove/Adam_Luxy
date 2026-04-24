// =============================================================================
// ADAM Migration 026: Attentional Posture on Page Entities (2026-04-24)
// =============================================================================
// Per attention-inversion principle (Chris, 2026-04-23, now platform core):
// consciousness is RAM (scarce, serial). The brain punts benign familiar
// patterns to supraliminal / autopilot processing to free conscious resources.
// Pages differ in the attentional posture they induce — autopilot-dominant
// (long-form narrative, lifestyle, habitual browsing) vs vigilance-dominant
// (threat-news, evaluative listicles, comparison shopping). Different optimal
// ad postures in each.
//
// Ads served on autopilot-dominant pages reach the reader via blend-and-
// fulfill (bypassing the evaluation gate). Ads on vigilance-dominant pages
// trip evaluation and activate persuasion resistance. Attentional posture
// therefore belongs as a first-class dimension on the page side of the
// bilateral cascade.
//
// This migration adds the attentional_posture property + Welford variance
// + observation count triplet across Author, Publication, Article, and the
// HAS_SECTION relationship. Scalar in [-1, 1]:
//     -1 = fully autopilot-dominant
//     +1 = fully vigilance-dominant
//      0 = neutral / unknown
//
// References:
//   - adam/intelligence/pages/entity_graph.py (Welford Cypher + ArticleObservation.attentional_posture)
//   - adam/intelligence/page_intelligence.py (PagePsychologicalProfile.attentional_posture)
//   - adam/intelligence/page_edge_bridge.py (attentional_posture → 20-dim edge shift)
//   - project_attention_inversion_platform_core.md (the principle itself)
//
// This migration is idempotent — safe to re-run. Existing nodes without
// attentional_posture are initialized to (0.0, 0.0, 0); nodes that already
// have a posture (from Welford accumulation after this migration first ran)
// are left untouched.
// =============================================================================


// -----------------------------------------------------------------------------
// Initialize attentional_posture triplet on existing Author nodes
// -----------------------------------------------------------------------------
MATCH (a:Author)
WHERE a.attentional_posture IS NULL
SET a.attentional_posture = 0.0,
    a.attentional_posture_variance = 0.0,
    a.attentional_posture_observations = 0
;

// -----------------------------------------------------------------------------
// Initialize on existing Publication nodes
// -----------------------------------------------------------------------------
MATCH (p:Publication)
WHERE p.attentional_posture IS NULL
SET p.attentional_posture = 0.0,
    p.attentional_posture_variance = 0.0,
    p.attentional_posture_observations = 0
;

// -----------------------------------------------------------------------------
// Initialize on existing Article nodes
// -----------------------------------------------------------------------------
MATCH (ar:Article)
WHERE ar.attentional_posture IS NULL
SET ar.attentional_posture = 0.0,
    ar.attentional_posture_variance = 0.0,
    ar.attentional_posture_observations = 0
;

// -----------------------------------------------------------------------------
// Initialize on existing HAS_SECTION relationships
// -----------------------------------------------------------------------------
MATCH ()-[r:HAS_SECTION]->()
WHERE r.attentional_posture IS NULL
SET r.attentional_posture = 0.0,
    r.attentional_posture_variance = 0.0,
    r.attentional_posture_observations = 0
;

// -----------------------------------------------------------------------------
// Indexes for attentional_posture-conditioned queries
// -----------------------------------------------------------------------------
CREATE INDEX page_article_attentional_posture_idx IF NOT EXISTS
FOR (ar:Article) ON (ar.attentional_posture);

CREATE INDEX page_publication_attentional_posture_idx IF NOT EXISTS
FOR (p:Publication) ON (p.attentional_posture);

// -----------------------------------------------------------------------------
// Verification queries (expected counts depend on prior observation history)
// -----------------------------------------------------------------------------
MATCH (a:Author)
WHERE a.attentional_posture IS NOT NULL
RETURN COUNT(a) AS authors_with_posture
;

MATCH (p:Publication)
WHERE p.attentional_posture IS NOT NULL
RETURN COUNT(p) AS publications_with_posture
;

MATCH (ar:Article)
WHERE ar.attentional_posture IS NOT NULL
RETURN COUNT(ar) AS articles_with_posture
;
