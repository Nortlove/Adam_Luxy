// =============================================================================
// ADAM Neo4j Migration: Advertising Psychology Knowledge Schema
// Location: adam/infrastructure/neo4j/migrations/016_advertising_psychology.cypher
// =============================================================================

// This migration creates the schema for storing 200+ empirical findings
// from advertising psychology research across 22 scientific domains.
//
// Core Insight: Advertising effectiveness operates primarily through 
// nonconscious processing (70-95% of decisions).
//
// Research Domains:
// 1. Signal Collection (Linguistic, Desktop, Mobile)
// 2. Personality Inference (Big Five via LIWC)
// 3. Regulatory Focus (Promotion/Prevention)
// 4. Cognitive State (Load, Circadian)
// 5. Approach-Avoidance (BIS/BAS)
// 6. Evolutionary Psychology
// 7. Memory Optimization (Spacing, Peak-End)
// 8. Nonconscious Processing
// 9. Moral Foundations
// 10. Psychophysics
// 11. Temporal Targeting
// 12. Social Effects

// =============================================================================
// CONSTRAINTS
// =============================================================================

// Advertising Psychology Knowledge node
CREATE CONSTRAINT IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
REQUIRE apk.knowledge_id IS UNIQUE;

// Confidence Tier classification
CREATE CONSTRAINT IF NOT EXISTS FOR (ct:ConfidenceTier) 
REQUIRE ct.tier IS UNIQUE;

// Research Domain classification
CREATE CONSTRAINT IF NOT EXISTS FOR (rd:ResearchDomain) 
REQUIRE rd.name IS UNIQUE;

// Signal-Construct Mapping
CREATE CONSTRAINT IF NOT EXISTS FOR (scm:SignalConstructMapping) 
REQUIRE scm.mapping_id IS UNIQUE;

// Message Frame Template
CREATE CONSTRAINT IF NOT EXISTS FOR (mft:MessageFrameTemplate) 
REQUIRE mft.template_id IS UNIQUE;

// Moral Foundation
CREATE CONSTRAINT IF NOT EXISTS FOR (mf:MoralFoundation) 
REQUIRE mf.name IS UNIQUE;

// Temporal Pattern
CREATE CONSTRAINT IF NOT EXISTS FOR (tp:TemporalPattern) 
REQUIRE tp.pattern_id IS UNIQUE;

// Cognitive Mechanism extension for new research
CREATE CONSTRAINT IF NOT EXISTS FOR (cm:CognitiveMechanism) 
REQUIRE cm.name IS UNIQUE;

// =============================================================================
// INDEXES
// =============================================================================

// Advertising Psychology Knowledge indexes
CREATE INDEX IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
ON (apk.research_domain);

CREATE INDEX IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
ON (apk.confidence_tier);

CREATE INDEX IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
ON (apk.predictor_name);

CREATE INDEX IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
ON (apk.outcome_metric);

CREATE INDEX IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
ON (apk.effect_type);

CREATE INDEX IF NOT EXISTS FOR (apk:AdvertisingPsychologyKnowledge) 
ON (apk.status);

// Signal mapping indexes
CREATE INDEX IF NOT EXISTS FOR (scm:SignalConstructMapping) 
ON (scm.signal_name);

CREATE INDEX IF NOT EXISTS FOR (scm:SignalConstructMapping) 
ON (scm.construct_name);

CREATE INDEX IF NOT EXISTS FOR (scm:SignalConstructMapping) 
ON (scm.signal_category);

// Temporal pattern indexes
CREATE INDEX IF NOT EXISTS FOR (tp:TemporalPattern) 
ON (tp.pattern_type);

// =============================================================================
// SEED CONFIDENCE TIERS
// =============================================================================

MERGE (t1:ConfidenceTier {tier: 1})
SET t1.name = 'TIER_1_META_ANALYZED',
    t1.criteria = 'Multiple meta-analyses, k>10 studies, large N',
    t1.use_case = 'Primary signals, high-stakes decisions',
    t1.description = 'Highest confidence - meta-analyzed findings'
;

MERGE (t2:ConfidenceTier {tier: 2})
SET t2.name = 'TIER_2_REPLICATED',
    t2.criteria = 'Independently replicated in 3+ studies',
    t2.use_case = 'Secondary signals, medium-stakes decisions',
    t2.description = 'Strong confidence - replicated findings'
;

MERGE (t3:ConfidenceTier {tier: 3})
SET t3.name = 'TIER_3_SINGLE_STUDY',
    t3.criteria = 'Large sample, strong methodology, awaiting replication',
    t3.use_case = 'Exploratory, low-stakes, with monitoring',
    t3.description = 'Moderate confidence - awaiting replication'
;

MERGE (t4:ConfidenceTier {tier: 4})
SET t4.name = 'TIER_4_CONTESTED',
    t4.criteria = 'Failed or mixed replication attempts',
    t4.use_case = 'DO NOT RELY ON THESE',
    t4.description = 'Low confidence - contested or failed findings'
;

// =============================================================================
// SEED RESEARCH DOMAINS
// =============================================================================

MERGE (rd1:ResearchDomain {name: 'linguistic_signals'})
SET rd1.description = 'LIWC-22 based text analysis for psychological inference',
    rd1.key_finding = 'Big Five correlations r=0.08-0.14 (N=85,724)',
    rd1.reference = 'Koutsoumpis et al. (2022)'
;

MERGE (rd2:ResearchDomain {name: 'desktop_implicit'})
SET rd2.description = 'Cursor, keystroke, and scroll patterns',
    rd2.key_finding = 'Decisional conflict d=0.4-1.6 from cursor trajectory',
    rd2.reference = 'Freeman & Ambady (2010)'
;

MERGE (rd3:ResearchDomain {name: 'mobile_implicit'})
SET rd3.description = 'Touch, gesture, and sensor patterns',
    rd3.key_finding = 'Emotional arousal 89% accuracy from touch pressure',
    rd3.reference = 'Gao et al. (2012)'
;

MERGE (rd4:ResearchDomain {name: 'regulatory_focus'})
SET rd4.description = 'Promotion vs prevention focus detection and matching',
    rd4.key_finding = 'Frame matching OR=2-6x CTR',
    rd4.reference = 'Higgins (1997)'
;

MERGE (rd5:ResearchDomain {name: 'cognitive_state'})
SET rd5.description = 'Cognitive load and circadian optimization',
    rd5.key_finding = 'Load-reducing interventions d=0.5-0.8',
    rd5.reference = 'Sweller (Cognitive Load Theory)'
;

MERGE (rd6:ResearchDomain {name: 'approach_avoidance'})
SET rd6.description = 'BIS/BAS temperament orientation',
    rd6.key_finding = 'BIS~Neuroticism r=0.4-0.6, BAS~Extraversion r=0.3-0.5',
    rd6.reference = 'Gray RST'
;

MERGE (rd7:ResearchDomain {name: 'evolutionary_psychology'})
SET rd7.description = 'Life history strategy and costly signaling',
    rd7.key_finding = 'Consumption IS signaling of fitness traits',
    rd7.reference = 'Miller (2009) Spent'
;

MERGE (rd8:ResearchDomain {name: 'memory_optimization'})
SET rd8.description = 'Spacing effect and peak-end rule',
    rd8.key_finding = 'Spacing: 150% improvement; Peak-end: r=0.70',
    rd8.reference = 'Cepeda et al. (2008); Kahneman'
;

MERGE (rd9:ResearchDomain {name: 'nonconscious_processing'})
SET rd9.description = 'Low-attention processing and wanting-liking',
    rd9.key_finding = 'Low attention can be MORE effective for emotional',
    rd9.reference = 'Heath et al. (2006); Berridge'
;

MERGE (rd10:ResearchDomain {name: 'moral_foundations'})
SET rd10.description = 'Six moral foundations targeting',
    rd10.key_finding = 'Consumer behavior predictions d=0.3-0.5',
    rd10.reference = 'Haidt & Graham'
;

MERGE (rd11:ResearchDomain {name: 'psychophysics'})
SET rd11.description = 'JND, fluency, and cross-modal correspondences',
    rd11.key_finding = 'Price JND 10-15%; Name fluency $333/year advantage',
    rd11.reference = 'Weber-Fechner; Alter & Oppenheimer'
;

MERGE (rd12:ResearchDomain {name: 'temporal_targeting'})
SET rd12.description = 'Construal level and circadian patterns',
    rd12.key_finding = 'Construal matching g=0.475',
    rd12.reference = 'Trope & Liberman CLT'
;

MERGE (rd13:ResearchDomain {name: 'social_effects'})
SET rd13.description = 'Social contagion and identity',
    rd13.key_finding = 'Ingroup favoritism d=0.32 (212 studies)',
    rd13.reference = 'Tajfel SIT; Christakis & Fowler'
;

// =============================================================================
// SEED MORAL FOUNDATIONS
// =============================================================================

MERGE (mf1:MoralFoundation {name: 'care_harm'})
SET mf1.sensitivity = 'Protecting others from harm',
    mf1.appeals = ['helping', 'nurturing', 'protection of vulnerable'],
    mf1.imagery = ['children', 'animals', 'caring interactions'],
    mf1.products = ['health', 'safety', 'charitable']
;

MERGE (mf2:MoralFoundation {name: 'fairness_cheating'})
SET mf2.sensitivity = 'Justice, equality, reciprocity',
    mf2.appeals = ['fair pricing', 'equal treatment', 'transparency'],
    mf2.avoid = 'Dynamic pricing visibility (triggers outrage)',
    mf2.products = ['ethical brands', 'fair trade']
;

MERGE (mf3:MoralFoundation {name: 'loyalty_betrayal'})
SET mf3.sensitivity = 'Group membership, patriotism',
    mf3.appeals = ['heritage', 'tradition', 'brand community'],
    mf3.imagery = ['flags', 'teams', 'families', 'generations'],
    mf3.products = ['domestic brands', 'legacy brands']
;

MERGE (mf4:MoralFoundation {name: 'authority_subversion'})
SET mf4.sensitivity = 'Respect for hierarchy, tradition',
    mf4.appeals = ['expertise', 'established brands', 'endorsements'],
    mf4.imagery = ['professionals', 'institutions', 'certificates'],
    mf4.products = ['premium brands', 'traditional categories']
;

MERGE (mf5:MoralFoundation {name: 'sanctity_degradation'})
SET mf5.sensitivity = 'Purity, contamination avoidance',
    mf5.appeals = ['natural', 'clean', 'pure', 'organic'],
    mf5.avoid = 'Any contamination associations',
    mf5.products = ['food', 'beauty', 'cleaning', 'health']
;

MERGE (mf6:MoralFoundation {name: 'liberty_oppression'})
SET mf6.sensitivity = 'Freedom from constraint',
    mf6.appeals = ['choice', 'freedom', 'no obligations'],
    mf6.avoid = 'Controlling language, forced bundling',
    mf6.products = ['experiences', 'travel', 'customizable']
;

// =============================================================================
// SEED KEY SIGNAL-CONSTRUCT MAPPINGS
// =============================================================================

// LIWC → Personality mappings (Tier 1)
MERGE (scm1:SignalConstructMapping {mapping_id: 'liwc_positive_emotion_extraversion'})
SET scm1.signal_name = 'liwc_positive_emotion',
    scm1.signal_category = 'linguistic',
    scm1.construct_name = 'extraversion',
    scm1.effect_size = 0.14,
    scm1.effect_type = 'correlation',
    scm1.confidence_tier = 1,
    scm1.sample_size = 85724,
    scm1.study_count = 31,
    scm1.reference = 'Koutsoumpis et al. (2022)'
;

MERGE (scm2:SignalConstructMapping {mapping_id: 'liwc_negative_emotion_neuroticism'})
SET scm2.signal_name = 'liwc_negative_emotion',
    scm2.signal_category = 'linguistic',
    scm2.construct_name = 'neuroticism',
    scm2.effect_size = 0.14,
    scm2.effect_type = 'correlation',
    scm2.confidence_tier = 1,
    scm2.sample_size = 85724,
    scm2.study_count = 31,
    scm2.reference = 'Koutsoumpis et al. (2022)'
;

// Cursor trajectory → Decisional conflict (Tier 1)
MERGE (scm3:SignalConstructMapping {mapping_id: 'cursor_auc_decisional_conflict'})
SET scm3.signal_name = 'cursor_trajectory_auc',
    scm3.signal_category = 'desktop_implicit',
    scm3.construct_name = 'decisional_conflict',
    scm3.effect_size = 0.80,
    scm3.effect_type = 'cohens_d',
    scm3.confidence_interval = '0.4-1.6',
    scm3.confidence_tier = 1,
    scm3.sample_size = 2500,
    scm3.study_count = 8,
    scm3.reference = 'Freeman & Ambady (2010)'
;

// Touch pressure → Emotional arousal (Tier 1)
MERGE (scm4:SignalConstructMapping {mapping_id: 'touch_pressure_arousal'})
SET scm4.signal_name = 'touch_pressure',
    scm4.signal_category = 'mobile_implicit',
    scm4.construct_name = 'emotional_arousal',
    scm4.effect_size = 0.89,
    scm4.effect_type = 'accuracy',
    scm4.confidence_tier = 1,
    scm4.sample_size = 1500,
    scm4.study_count = 3,
    scm4.reference = 'Gao et al. (2012)'
;

// Swipe direction → Approach motivation (Tier 2)
MERGE (scm5:SignalConstructMapping {mapping_id: 'swipe_direction_approach'})
SET scm5.signal_name = 'swipe_direction',
    scm5.signal_category = 'mobile_implicit',
    scm5.construct_name = 'approach_motivation',
    scm5.effect_size = 0.35,
    scm5.effect_type = 'cohens_d',
    scm5.confidence_tier = 2,
    scm5.sample_size = 1538,
    scm5.study_count = 29,
    scm5.reference = 'Phaf et al. (2014)'
;

// =============================================================================
// SEED TEMPORAL PATTERNS
// =============================================================================

// Circadian patterns
MERGE (tp1:TemporalPattern {pattern_id: 'circadian_cognitive_peak'})
SET tp1.pattern_type = 'circadian',
    tp1.peak_hours = [10, 11, 16, 17],
    tp1.trough_hours = [4, 5, 6, 14, 15],
    tp1.recommendation = 'Complex messages at peak; Simple at trough',
    tp1.reference = 'Valdez et al. (2012)'
;

// Weekly patterns
MERGE (tp2:TemporalPattern {pattern_id: 'weekend_hedonic'})
SET tp2.pattern_type = 'weekly',
    tp2.weekend_effect = 0.22,
    tp2.saturday_volume_pct = 17,
    tp2.sunday_avg_spend = 86,
    tp2.recommendation = 'Weekend: emotional/hedonic. Weekday: utilitarian',
    tp2.reference = 'Shopping behavior research'
;

// Construal level × funnel stage
MERGE (tp3:TemporalPattern {pattern_id: 'construal_awareness'})
SET tp3.pattern_type = 'construal_funnel',
    tp3.funnel_stage = 'awareness',
    tp3.psychological_distance = 'far',
    tp3.construal_level = 'high_abstract',
    tp3.message_focus = 'WHY - benefits, values, desirability',
    tp3.effect_size = 0.475,
    tp3.reference = 'Trope & Liberman CLT'
;

MERGE (tp4:TemporalPattern {pattern_id: 'construal_decision'})
SET tp4.pattern_type = 'construal_funnel',
    tp4.funnel_stage = 'decision',
    tp4.psychological_distance = 'near',
    tp4.construal_level = 'low_concrete',
    tp4.message_focus = 'HOW - features, specs, feasibility',
    tp4.effect_size = 0.475,
    tp4.reference = 'Trope & Liberman CLT'
;

// =============================================================================
// SEED REGULATORY FOCUS TEMPLATES
// =============================================================================

// Promotion frame templates
MERGE (mft1:MessageFrameTemplate {template_id: 'promotion_achieve'})
SET mft1.focus_type = 'promotion',
    mft1.template = 'Achieve {benefit} with {product}',
    mft1.construal = 'abstract',
    mft1.effect_size_or = '2-6x CTR',
    mft1.reference = 'Higgins (1997)'
;

MERGE (mft2:MessageFrameTemplate {template_id: 'promotion_advance'})
SET mft2.focus_type = 'promotion',
    mft2.template = 'Advance your {goal} today',
    mft2.construal = 'abstract'
;

MERGE (mft3:MessageFrameTemplate {template_id: 'promotion_gain'})
SET mft3.focus_type = 'promotion',
    mft3.template = 'Gain the {advantage} you deserve',
    mft3.construal = 'abstract'
;

// Prevention frame templates
MERGE (mft4:MessageFrameTemplate {template_id: 'prevention_protect'})
SET mft4.focus_type = 'prevention',
    mft4.template = 'Protect your {asset} with {product}',
    mft4.construal = 'concrete',
    mft4.effect_size_or = '2-6x CTR',
    mft4.reference = 'Higgins (1997)'
;

MERGE (mft5:MessageFrameTemplate {template_id: 'prevention_avoid'})
SET mft5.focus_type = 'prevention',
    mft5.template = 'Avoid {problem} with {solution}',
    mft5.construal = 'concrete'
;

MERGE (mft6:MessageFrameTemplate {template_id: 'prevention_secure'})
SET mft6.focus_type = 'prevention',
    mft6.template = 'Secure your {valuable} today',
    mft6.construal = 'concrete'
;

// =============================================================================
// RELATIONSHIPS BETWEEN DOMAINS AND MECHANISMS
// =============================================================================

// Link research domains to ADAM's 9 cognitive mechanisms
MATCH (rd:ResearchDomain {name: 'regulatory_focus'})
MATCH (cm:CognitiveMechanism {name: 'regulatory_focus'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 1.0}]->(cm);

MATCH (rd:ResearchDomain {name: 'temporal_targeting'})
MATCH (cm:CognitiveMechanism {name: 'construal_level'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.9}]->(cm);

MATCH (rd:ResearchDomain {name: 'temporal_targeting'})
MATCH (cm:CognitiveMechanism {name: 'temporal_construal'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.9}]->(cm);

MATCH (rd:ResearchDomain {name: 'nonconscious_processing'})
MATCH (cm:CognitiveMechanism {name: 'automatic_evaluation'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.85}]->(cm);

MATCH (rd:ResearchDomain {name: 'nonconscious_processing'})
MATCH (cm:CognitiveMechanism {name: 'wanting_liking_dissociation'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.9}]->(cm);

MATCH (rd:ResearchDomain {name: 'social_effects'})
MATCH (cm:CognitiveMechanism {name: 'mimetic_desire'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.85}]->(cm);

MATCH (rd:ResearchDomain {name: 'social_effects'})
MATCH (cm:CognitiveMechanism {name: 'identity_construction'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.8}]->(cm);

MATCH (rd:ResearchDomain {name: 'evolutionary_psychology'})
MATCH (cm:CognitiveMechanism {name: 'evolutionary_adaptations'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.95}]->(cm);

MATCH (rd:ResearchDomain {name: 'cognitive_state'})
MATCH (cm:CognitiveMechanism {name: 'attention_dynamics'})
MERGE (rd)-[:INFORMS_MECHANISM {strength: 0.85}]->(cm);

// =============================================================================
// Link signal mappings to research domains
// =============================================================================

MATCH (scm:SignalConstructMapping)
WHERE scm.signal_category = 'linguistic'
MATCH (rd:ResearchDomain {name: 'linguistic_signals'})
MERGE (scm)-[:BELONGS_TO_DOMAIN]->(rd);

MATCH (scm:SignalConstructMapping)
WHERE scm.signal_category = 'desktop_implicit'
MATCH (rd:ResearchDomain {name: 'desktop_implicit'})
MERGE (scm)-[:BELONGS_TO_DOMAIN]->(rd);

MATCH (scm:SignalConstructMapping)
WHERE scm.signal_category = 'mobile_implicit'
MATCH (rd:ResearchDomain {name: 'mobile_implicit'})
MERGE (scm)-[:BELONGS_TO_DOMAIN]->(rd);

// Link signal mappings to confidence tiers
MATCH (scm:SignalConstructMapping)
WHERE scm.confidence_tier = 1
MATCH (ct:ConfidenceTier {tier: 1})
MERGE (scm)-[:HAS_CONFIDENCE_TIER]->(ct);

MATCH (scm:SignalConstructMapping)
WHERE scm.confidence_tier = 2
MATCH (ct:ConfidenceTier {tier: 2})
MERGE (scm)-[:HAS_CONFIDENCE_TIER]->(ct);

// Link message templates to regulatory focus domain
MATCH (mft:MessageFrameTemplate)
MATCH (rd:ResearchDomain {name: 'regulatory_focus'})
MERGE (mft)-[:BELONGS_TO_DOMAIN]->(rd);

// Link moral foundations to moral_foundations domain
MATCH (mf:MoralFoundation)
MATCH (rd:ResearchDomain {name: 'moral_foundations'})
MERGE (mf)-[:BELONGS_TO_DOMAIN]->(rd);

// Link temporal patterns to temporal_targeting domain
MATCH (tp:TemporalPattern)
MATCH (rd:ResearchDomain {name: 'temporal_targeting'})
MERGE (tp)-[:BELONGS_TO_DOMAIN]->(rd);
