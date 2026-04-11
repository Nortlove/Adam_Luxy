// =============================================================================
// ADAM Neo4j Migration 017: Emergent Intelligence Infrastructure
// Location: adam/infrastructure/neo4j/migrations/017_emergent_intelligence.cypher
// =============================================================================

// This migration adds schema support for:
// 1. Emergence Engine - Novel construct discovery
// 2. Causal Discovery - Causal relationship learning
// 3. Predictive Processing - Precision-weighted beliefs
// 4. Cross-Disciplinary Science - New research domains

// =============================================================================
// EMERGENT CONSTRUCT SCHEMA
// =============================================================================

// Constraint for emergent constructs
CREATE CONSTRAINT emergent_construct_id IF NOT EXISTS
FOR (ec:EmergentConstruct) REQUIRE ec.construct_id IS UNIQUE;

// Indexes for emergent constructs
CREATE INDEX emergent_construct_status IF NOT EXISTS
FOR (ec:EmergentConstruct) ON (ec.status);

CREATE INDEX emergent_construct_discovered IF NOT EXISTS
FOR (ec:EmergentConstruct) ON (ec.discovered_at);

CREATE INDEX emergent_construct_lift IF NOT EXISTS
FOR (ec:EmergentConstruct) ON (ec.predictive_lift);

// =============================================================================
// CAUSAL EDGE SCHEMA
// =============================================================================

// Constraint for causal variables
CREATE CONSTRAINT causal_variable_name IF NOT EXISTS
FOR (cv:CausalVariable) REQUIRE cv.name IS UNIQUE;

// Constraint for causal graphs
CREATE CONSTRAINT causal_graph_id IF NOT EXISTS
FOR (cg:CausalGraph) REQUIRE cg.graph_id IS UNIQUE;

// Index for causal edges
CREATE INDEX causal_edge_strength IF NOT EXISTS
FOR ()-[r:CAUSES]-() ON (r.strength);

CREATE INDEX causal_edge_confidence IF NOT EXISTS
FOR ()-[r:CAUSES]-() ON (r.confidence);

// =============================================================================
// BELIEF STATE SCHEMA (Predictive Processing)
// =============================================================================

// Constraint for belief states
CREATE CONSTRAINT belief_state_user IF NOT EXISTS
FOR (bs:BeliefState) REQUIRE bs.user_id IS UNIQUE;

// Index for belief state uncertainty
CREATE INDEX belief_state_uncertainty IF NOT EXISTS
FOR (bs:BeliefState) ON (bs.total_uncertainty);

// =============================================================================
// CROSS-DISCIPLINARY RESEARCH DOMAINS
// =============================================================================

// Add new research domains
MERGE (rd:ResearchDomain {name: 'evolutionary_psychology'})
SET rd.description = 'Costly signaling, life history theory, mating motivation, kin selection',
    rd.key_findings = ['costly_signal_luxury', 'life_history_strategy', 'mating_motivation_spending'],
    rd.effect_size_range = '0.35-0.55';

MERGE (rd2:ResearchDomain {name: 'social_physics'})
SET rd2.description = 'Network effects, social contagion, threshold models, weak ties',
    rd2.key_findings = ['three_degrees_influence', 'complex_contagion', 'weak_tie_discovery'],
    rd2.effect_size_range = '0.30-0.55';

MERGE (rd3:ResearchDomain {name: 'reinforcement_learning'})
SET rd3.description = 'Model-based vs model-free, prediction error, successor representation',
    rd3.key_findings = ['model_based_vs_free', 'prediction_error_learning', 'explore_exploit_balance'],
    rd3.effect_size_range = '0.40-0.60';

MERGE (rd4:ResearchDomain {name: 'predictive_processing'})
SET rd4.description = 'Free energy minimization, precision weighting, active inference, curiosity',
    rd4.key_findings = ['prediction_error_attention', 'precision_weighting', 'curiosity_information_gap'],
    rd4.effect_size_range = '0.40-0.55';

MERGE (rd5:ResearchDomain {name: 'psychophysics'})
SET rd5.description = 'Weber-Fechner law, perceptual fluency, cross-modal correspondences',
    rd5.key_findings = ['jnd_pricing', 'fluency_preference', 'crossmodal_brand'],
    rd5.effect_size_range = '0.35-0.70';

MERGE (rd6:ResearchDomain {name: 'memory_reconsolidation'})
SET rd6.description = 'Reconsolidation windows, testing effect, context-dependent memory',
    rd6.key_findings = ['reconsolidation_window_6h', 'testing_effect_recall', 'context_matching'],
    rd6.effect_size_range = '0.35-0.50';

MERGE (rd7:ResearchDomain {name: 'embodied_cognition'})
SET rd7.description = 'Approach-avoidance movements, IKEA effect, haptic influences',
    rd7.key_findings = ['swipe_direction_attitude', 'ikea_effect_valuation', 'touch_ownership'],
    rd7.effect_size_range = '0.38-0.55';

MERGE (rd8:ResearchDomain {name: 'media_preferences'})
SET rd8.description = 'Music → personality (MUSIC model), podcast → traits, genre preferences',
    rd8.key_findings = ['sophisticated_music_openness', 'true_crime_morbid_curiosity', 'fiction_empathy'],
    rd8.effect_size_range = '0.15-0.51';

// =============================================================================
// EMERGENT CONSTRUCT STATUS NODES
// =============================================================================

MERGE (cs1:ConstructStatus {name: 'candidate'})
SET cs1.description = 'Detected pattern, not yet validated';

MERGE (cs2:ConstructStatus {name: 'validating'})
SET cs2.description = 'Currently undergoing predictive power testing';

MERGE (cs3:ConstructStatus {name: 'validated'})
SET cs3.description = 'Passed validation, awaiting promotion to knowledge';

MERGE (cs4:ConstructStatus {name: 'promoted'})
SET cs4.description = 'Promoted to first-class knowledge, actively used';

MERGE (cs5:ConstructStatus {name: 'rejected'})
SET cs5.description = 'Failed validation, not predictive';

MERGE (cs6:ConstructStatus {name: 'deprecated'})
SET cs6.description = 'Previously valid, no longer predictive';

// =============================================================================
// CAUSAL EDGE TYPE NODES
// =============================================================================

MERGE (et1:CausalEdgeType {name: 'directed'})
SET et1.description = 'A → B: A causes B',
    et1.symbol = '→';

MERGE (et2:CausalEdgeType {name: 'undirected'})
SET et2.description = 'A - B: Causal direction unknown',
    et2.symbol = '-';

MERGE (et3:CausalEdgeType {name: 'bidirected'})
SET et3.description = 'A ↔ B: Latent confounder between A and B',
    et3.symbol = '↔';

// =============================================================================
// INTELLIGENCE ENGINE NODES
// =============================================================================

MERGE (ie1:IntelligenceEngine {name: 'emergence_engine'})
SET ie1.description = 'Discovers novel psychological constructs from unexplained variance',
    ie1.version = '1.0',
    ie1.capabilities = ['anomaly_detection', 'pattern_clustering', 'construct_validation', 'knowledge_promotion'];

MERGE (ie2:IntelligenceEngine {name: 'causal_discovery'})
SET ie2.description = 'Learns causal structure from observational data',
    ie2.version = '1.0',
    ie2.capabilities = ['pc_algorithm', 'confounding_identification', 'ate_estimation', 'intervention_suggestion'];

MERGE (ie3:IntelligenceEngine {name: 'predictive_processing'})
SET ie3.description = 'Cognitive science-grounded ad selection via free energy minimization',
    ie3.version = '1.0',
    ie3.capabilities = ['precision_weighting', 'curiosity_scoring', 'active_inference', 'belief_updating'];

MERGE (ie4:IntelligenceEngine {name: 'neural_thompson'})
SET ie4.description = 'Context-aware exploration using neural network uncertainty',
    ie4.version = '1.0',
    ie4.capabilities = ['bootstrap_uncertainty', 'context_conditioning', 'learned_exploration', 'calibration_tracking'];

MERGE (ie5:IntelligenceEngine {name: 'streaming_synthesis'})
SET ie5.description = 'Progressive decision synthesis with confidence-gated early exit',
    ie5.version = '1.0',
    ie5.capabilities = ['progressive_synthesis', 'early_exit', 'context_value_estimation', 'anytime_algorithm'];

// =============================================================================
// GDS GRAPH PROJECTION METADATA
// =============================================================================

MERGE (gp1:GDSProjection {name: 'knowledge-graph'})
SET gp1.description = 'Projection for knowledge graph algorithms',
    gp1.node_labels = ['BehavioralKnowledge', 'PsychologicalConstruct', 'BehavioralSignal', 
                       'AdvertisingKnowledge', 'ResearchDomain', 'CognitiveMechanism'],
    gp1.relationship_types = ['MAPS_TO', 'DERIVED_FROM', 'BELONGS_TO', 'TESTS_MECHANISM'],
    gp1.algorithms_supported = ['pageRank', 'louvain', 'nodeSimilarity', 'node2vec'];

MERGE (gp2:GDSProjection {name: 'user-behavior-graph'})
SET gp2.description = 'Projection for user behavior analysis',
    gp2.node_labels = ['User', 'Session', 'Decision', 'Outcome', 'AdCreative'],
    gp2.relationship_types = ['HAD_SESSION', 'MADE_DECISION', 'RESULTED_IN', 'SHOWN_AD'],
    gp2.algorithms_supported = ['pageRank', 'pathfinding', 'communityDetection'];

// =============================================================================
// RELATIONSHIPS BETWEEN NEW COMPONENTS
// =============================================================================

// Link research domains to intelligence engines
MATCH (ie:IntelligenceEngine {name: 'emergence_engine'})
MATCH (rd:ResearchDomain)
WHERE rd.name IN ['predictive_processing', 'reinforcement_learning']
MERGE (ie)-[:LEVERAGES_RESEARCH]->(rd);

MATCH (ie:IntelligenceEngine {name: 'causal_discovery'})
MATCH (rd:ResearchDomain)
WHERE rd.name IN ['social_physics', 'evolutionary_psychology']
MERGE (ie)-[:LEVERAGES_RESEARCH]->(rd);

MATCH (ie:IntelligenceEngine {name: 'predictive_processing'})
MATCH (rd:ResearchDomain {name: 'predictive_processing'})
MERGE (ie)-[:IMPLEMENTS_THEORY]->(rd);

// Link GDS projections to intelligence engines
MATCH (ie:IntelligenceEngine {name: 'emergence_engine'})
MATCH (gp:GDSProjection {name: 'knowledge-graph'})
MERGE (ie)-[:USES_PROJECTION]->(gp);

MATCH (ie:IntelligenceEngine {name: 'causal_discovery'})
MATCH (gp:GDSProjection {name: 'knowledge-graph'})
MERGE (ie)-[:USES_PROJECTION]->(gp);
