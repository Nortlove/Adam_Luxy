// ============================================================
// Migration 031: Update dim_cog_decision_style with Schwartz
//                academic grounding + canonical name
// Slice: A.1 (refactor consolidate maximizer/satisficer)
// Predecessor: A.0 (cf41115), A.1.0 audit (c237e4b)
// ============================================================

// Update the existing dim_cog_decision_style PersonalityDimension
// node. Per audit §8.2 (Q10.B): keep dimension_id stable
// (0 READ_BY sites — renaming would be wasted churn). Update
// name property to canonical 'maximizer_tendency'. Add Schwartz
// 2002 academic_grounding + scale_min/max/anchors + provenance.

MATCH (d:PersonalityDimension {dimension_id: 'dim_cog_decision_style'})
SET d.name = 'maximizer_tendency',
    d.academic_grounding = 'Schwartz, B., Ward, A., Monterosso, J., Lyubomirsky, S., White, K., & Lehman, D. R. (2002). Maximizing versus satisficing: Happiness is a matter of choice. Journal of Personality and Social Psychology, 83(5), 1178–1197.',
    d.scale_min = 0.0,
    d.scale_max = 1.0,
    d.scale_anchor_low = 'satisficer (good-enough orientation)',
    d.scale_anchor_high = 'maximizer (optimal-choice orientation)',
    d.added_in = 'A.1',
    d.updated_at = datetime();

// Idempotency: re-running this migration MATCHes the same node
// and SET overwrites with identical values. The dimension_id
// UNIQUE constraint (migration 001) guarantees exactly one match.
// The name index (migration 002:54) rebuilds on next startup.

// Existing properties preserved unchanged (per audit §2):
// full_name, domain, dimension_type, description, low_description,
// high_description, measurement_method, ad_relevance,
// population_mean, population_std, created_at.
