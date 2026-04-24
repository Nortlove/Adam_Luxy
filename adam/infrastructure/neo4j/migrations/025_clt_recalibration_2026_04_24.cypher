// =============================================================================
// Migration 025: CLT Recalibration (2026-04-24)
// =============================================================================
// Recalibrate Construal Level Theory effect sizes from the uncorrected
// meta-analytic Hedges' g = 0.475 (Trope & Liberman lineage; 111 studies)
// to the pre-registered d = 0.276.
//
// Rationale
// ---------
// Schimmack (2022) replicability-index analyses and Maier et al. (2023) RoBMA
// multiverse meta-analyses show CLT published effects inflated ~42-70% vs
// publication-bias-corrected estimates. The pre-registered d = 0.276 survives
// correction and is ADAM's operational value.
//
// This migration updates nodes originally seeded by migration 016. Previous
// uncorrected values are retained as `published_g` for transparency; the
// operational `effect_size` field is overwritten. Each touched node receives
// a `recalibrated_at` timestamp and `recalibration_ref` pointer.
//
// See:
//   - adam/core/learning/effect_size_correction.py (CLT_MATCHING_EFFECT)
//   - docs/CLT_recalibration_2026_04_24.md
// =============================================================================

// -----------------------------------------------------------------------------
// ResearchDomain — temporal_targeting (rd12 in migration 016)
// -----------------------------------------------------------------------------

MATCH (rd:ResearchDomain {name: 'temporal_targeting'})
SET rd.key_finding = 'Construal matching d=0.276 (pre-registered; publication-bias-corrected from published g=0.475)',
    rd.effect_size = 0.276,
    rd.published_g = 0.475,
    rd.correction_method = 'pre_registered',
    rd.study_count = 111,
    rd.recalibrated_at = datetime(),
    rd.recalibration_ref = 'docs/CLT_recalibration_2026_04_24.md'
;

// -----------------------------------------------------------------------------
// TemporalPattern — construal_awareness (tp3) and construal_decision (tp4)
// -----------------------------------------------------------------------------

MATCH (tp:TemporalPattern)
WHERE tp.pattern_id IN ['construal_awareness', 'construal_decision']
SET tp.effect_size = 0.276,
    tp.published_g = 0.475,
    tp.correction_method = 'pre_registered',
    tp.recalibrated_at = datetime(),
    tp.recalibration_ref = 'docs/CLT_recalibration_2026_04_24.md'
;

// -----------------------------------------------------------------------------
// Verification queries (safe to re-run; idempotent)
// -----------------------------------------------------------------------------

// Expected: 1 corrected ResearchDomain
MATCH (rd:ResearchDomain {name: 'temporal_targeting'})
WHERE rd.effect_size = 0.276 AND rd.correction_method = 'pre_registered'
RETURN COUNT(rd) AS corrected_research_domains
;

// Expected: 2 corrected TemporalPatterns
MATCH (tp:TemporalPattern)
WHERE tp.pattern_id IN ['construal_awareness', 'construal_decision']
  AND tp.effect_size = 0.276
  AND tp.correction_method = 'pre_registered'
RETURN COUNT(tp) AS corrected_temporal_patterns
;
