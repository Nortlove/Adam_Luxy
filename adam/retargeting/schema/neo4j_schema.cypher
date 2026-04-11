// ============================================================
// INFORMATIV Enhancement #33: Therapeutic Retargeting Engine
// Neo4j Schema Definition
// ============================================================

// --- Conversion Barrier Diagnosis Node ---
CREATE CONSTRAINT barrier_diagnosis_id IF NOT EXISTS
FOR (bd:BarrierDiagnosis) REQUIRE bd.diagnosis_id IS UNIQUE;

// Properties: diagnosis_id, user_id, brand_id, archetype_id,
//   diagnosed_at, conversion_stage, stage_confidence,
//   primary_barrier, primary_barrier_confidence,
//   rupture_type, rupture_severity,
//   estimated_reactance_level, reactance_budget_remaining,
//   persuasion_knowledge_phase, ownership_level,
//   recommended_mechanism, mechanism_confidence

// --- Therapeutic Touch Node ---
CREATE CONSTRAINT therapeutic_touch_id IF NOT EXISTS
FOR (tt:TherapeuticTouch) REQUIRE tt.touch_id IS UNIQUE;

// Properties: touch_id, sequence_id, position_in_sequence,
//   mechanism, scaffold_level, construal_level, processing_route,
//   narrative_chapter, narrative_function,
//   trigger_type, delivered_at,
//   autonomy_language, opt_out_visible

// --- Therapeutic Sequence Node ---
CREATE CONSTRAINT therapeutic_sequence_id IF NOT EXISTS
FOR (ts:TherapeuticSequence) REQUIRE ts.sequence_id IS UNIQUE;

// Properties: sequence_id, user_id, brand_id, archetype_id,
//   max_touches, max_duration_days, status,
//   cumulative_reactance, narrative_arc_type,
//   started_at, completed_at, final_status

// --- Site Psychological Profile Node ---
CREATE CONSTRAINT site_profile_domain IF NOT EXISTS
FOR (sp:SitePsychProfile) REQUIRE sp.domain IS UNIQUE;

// Properties: domain, url_analyzed, analyzed_at,
//   trust_signaling, emotional_warmth, rational_density,
//   aspirational_level, simplicity, urgency_pressure,
//   social_proof_density, narrative_richness, autonomy_respect,
//   processing_route, regulatory_framing, construal_level,
//   page_category, content_quality_score

// --- Mechanism Effectiveness Prior Node ---
// (Extends existing BayesianPrior pattern from Enhancement #32)
CREATE CONSTRAINT mechanism_prior_id IF NOT EXISTS
FOR (mp:MechanismPrior) REQUIRE mp.prior_id IS UNIQUE;

// Properties: prior_id, mechanism, barrier_category,
//   archetype_id, alpha, beta (Thompson Sampling),
//   sample_count, last_updated,
//   personality_interaction_weights (vector)

// --- Indexes for query performance ---
CREATE INDEX barrier_diagnosis_user IF NOT EXISTS
FOR (bd:BarrierDiagnosis) ON (bd.user_id);

CREATE INDEX barrier_diagnosis_archetype IF NOT EXISTS
FOR (bd:BarrierDiagnosis) ON (bd.archetype_id);

CREATE INDEX therapeutic_touch_sequence IF NOT EXISTS
FOR (tt:TherapeuticTouch) ON (tt.sequence_id);

CREATE INDEX therapeutic_sequence_status IF NOT EXISTS
FOR (ts:TherapeuticSequence) ON (ts.status);

CREATE INDEX therapeutic_sequence_user IF NOT EXISTS
FOR (ts:TherapeuticSequence) ON (ts.user_id);

CREATE INDEX site_profile_category IF NOT EXISTS
FOR (sp:SitePsychProfile) ON (sp.page_category);

CREATE INDEX mechanism_prior_lookup IF NOT EXISTS
FOR (mp:MechanismPrior) ON (mp.mechanism, mp.barrier_category, mp.archetype_id);
