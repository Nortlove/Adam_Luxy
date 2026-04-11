// =============================================================================
// ADAM Neo4j Migration 002: Core Indexes
// Optimizes query performance for all primary access patterns
// =============================================================================

// -----------------------------------------------------------------------------
// USER INDEXES
// -----------------------------------------------------------------------------

// Primary user lookup
CREATE INDEX user_lookup IF NOT EXISTS
FOR (u:User) ON (u.user_id);

// Temporal queries
CREATE INDEX user_by_created IF NOT EXISTS
FOR (u:User) ON (u.created_at);

CREATE INDEX user_by_updated IF NOT EXISTS
FOR (u:User) ON (u.last_updated);

// Profile completeness for cold-start decisions
CREATE INDEX user_by_completeness IF NOT EXISTS
FOR (u:User) ON (u.profile_completeness);

// Platform-specific user lookups
CREATE INDEX user_by_iheart_id IF NOT EXISTS
FOR (u:User) ON (u.iheart_user_id);

CREATE INDEX user_by_wpp_id IF NOT EXISTS
FOR (u:User) ON (u.wpp_user_id);

// Identity resolution
CREATE INDEX user_by_uid2 IF NOT EXISTS
FOR (u:User) ON (u.uid2_token);

CREATE INDEX user_by_ramp_id IF NOT EXISTS
FOR (u:User) ON (u.ramp_id);

// -----------------------------------------------------------------------------
// MECHANISM INDEXES
// -----------------------------------------------------------------------------

CREATE INDEX mechanism_by_name IF NOT EXISTS
FOR (m:CognitiveMechanism) ON (m.name);

CREATE INDEX mechanism_by_type IF NOT EXISTS
FOR (m:CognitiveMechanism) ON (m.mechanism_type);

// -----------------------------------------------------------------------------
// PERSONALITY DIMENSION INDEXES
// -----------------------------------------------------------------------------

CREATE INDEX dimension_by_name IF NOT EXISTS
FOR (d:PersonalityDimension) ON (d.name);

CREATE INDEX dimension_by_domain IF NOT EXISTS
FOR (d:PersonalityDimension) ON (d.domain);

CREATE INDEX dimension_by_type IF NOT EXISTS
FOR (d:PersonalityDimension) ON (d.dimension_type);

// -----------------------------------------------------------------------------
// DECISION INDEXES
// -----------------------------------------------------------------------------

CREATE INDEX decision_by_user IF NOT EXISTS
FOR (d:Decision) ON (d.user_id);

CREATE INDEX decision_by_timestamp IF NOT EXISTS
FOR (d:Decision) ON (d.created_at);

CREATE INDEX decision_by_platform IF NOT EXISTS
FOR (d:Decision) ON (d.platform);

CREATE INDEX decision_by_outcome IF NOT EXISTS
FOR (d:Decision) ON (d.outcome_type);

// -----------------------------------------------------------------------------
// SESSION INDEXES
// -----------------------------------------------------------------------------

CREATE INDEX session_by_user IF NOT EXISTS
FOR (s:Session) ON (s.user_id);

CREATE INDEX session_by_start IF NOT EXISTS
FOR (s:Session) ON (s.started_at);

CREATE INDEX session_by_platform IF NOT EXISTS
FOR (s:Session) ON (s.platform);

// -----------------------------------------------------------------------------
// INTELLIGENCE SOURCE INDEXES
// -----------------------------------------------------------------------------

// Empirical patterns
CREATE INDEX pattern_by_condition IF NOT EXISTS
FOR (p:EmpiricalPattern) ON (p.condition);

CREATE INDEX pattern_by_prediction IF NOT EXISTS
FOR (p:EmpiricalPattern) ON (p.prediction);

CREATE INDEX pattern_by_confidence IF NOT EXISTS
FOR (p:EmpiricalPattern) ON (p.confidence);

CREATE INDEX pattern_by_created IF NOT EXISTS
FOR (p:EmpiricalPattern) ON (p.discovered_at);

// Behavioral signatures
CREATE INDEX signature_by_type IF NOT EXISTS
FOR (b:BehavioralSignature) ON (b.signal_type);

CREATE INDEX signature_by_user IF NOT EXISTS
FOR (b:BehavioralSignature) ON (b.user_id);

// Bandit posteriors
CREATE INDEX posterior_by_arm IF NOT EXISTS
FOR (b:BanditPosterior) ON (b.arm_id);

CREATE INDEX posterior_by_context IF NOT EXISTS
FOR (b:BanditPosterior) ON (b.context_type);

// Learning signals
CREATE INDEX learning_by_decision IF NOT EXISTS
FOR (l:LearningSignal) ON (l.decision_id);

CREATE INDEX learning_by_outcome IF NOT EXISTS
FOR (l:LearningSignal) ON (l.outcome_type);

CREATE INDEX learning_by_timestamp IF NOT EXISTS
FOR (l:LearningSignal) ON (l.timestamp);

// Reasoning insights
CREATE INDEX insight_by_request IF NOT EXISTS
FOR (r:ReasoningInsight) ON (r.request_id);

CREATE INDEX insight_by_type IF NOT EXISTS
FOR (r:ReasoningInsight) ON (r.insight_type);

// -----------------------------------------------------------------------------
// V3 COGNITIVE LAYER INDEXES
// -----------------------------------------------------------------------------

// Emergent constructs
CREATE INDEX emergent_by_validation IF NOT EXISTS
FOR (e:EmergentConstruct) ON (e.validated);

CREATE INDEX emergent_by_discovery IF NOT EXISTS
FOR (e:EmergentConstruct) ON (e.discovered_at);

CREATE INDEX emergent_by_confidence IF NOT EXISTS
FOR (e:EmergentConstruct) ON (e.statistical_confidence);

// Causal edges
CREATE INDEX causal_by_cause IF NOT EXISTS
FOR (c:CausalEdge) ON (c.cause_construct);

CREATE INDEX causal_by_effect IF NOT EXISTS
FOR (c:CausalEdge) ON (c.effect_construct);

CREATE INDEX causal_by_strength IF NOT EXISTS
FOR (c:CausalEdge) ON (c.causal_strength);

// Temporal states
CREATE INDEX temporal_state_by_user IF NOT EXISTS
FOR (t:TemporalUserState) ON (t.user_id);

CREATE INDEX temporal_state_by_time IF NOT EXISTS
FOR (t:TemporalUserState) ON (t.timestamp);

// State trajectories
CREATE INDEX trajectory_by_user IF NOT EXISTS
FOR (t:StateTrajectory) ON (t.user_id);

CREATE INDEX trajectory_by_type IF NOT EXISTS
FOR (t:StateTrajectory) ON (t.trajectory_type);

// Mechanism interactions
CREATE INDEX interaction_by_mechanism_a IF NOT EXISTS
FOR (i:MechanismInteraction) ON (i.mechanism_a);

CREATE INDEX interaction_by_mechanism_b IF NOT EXISTS
FOR (i:MechanismInteraction) ON (i.mechanism_b);

CREATE INDEX interaction_by_type IF NOT EXISTS
FOR (i:MechanismInteraction) ON (i.interaction_type);

// -----------------------------------------------------------------------------
// PLATFORM ENTITY INDEXES
// -----------------------------------------------------------------------------

// Archetypes
CREATE INDEX archetype_by_name IF NOT EXISTS
FOR (a:Archetype) ON (a.name);

CREATE INDEX archetype_by_category IF NOT EXISTS
FOR (a:Archetype) ON (a.category);

// Brands
CREATE INDEX brand_by_name IF NOT EXISTS
FOR (b:Brand) ON (b.name);

CREATE INDEX brand_by_category IF NOT EXISTS
FOR (b:Brand) ON (b.category);

// Stations (iHeart)
CREATE INDEX station_by_format IF NOT EXISTS
FOR (s:Station) ON (s.format);

CREATE INDEX station_by_market IF NOT EXISTS
FOR (s:Station) ON (s.market);

// Content
CREATE INDEX content_by_type IF NOT EXISTS
FOR (c:Content) ON (c.content_type);

CREATE INDEX content_by_station IF NOT EXISTS
FOR (c:Content) ON (c.station_id);

// Cohorts
CREATE INDEX cohort_by_discovery IF NOT EXISTS
FOR (c:EmergentCohort) ON (c.discovered_at);

CREATE INDEX cohort_by_size IF NOT EXISTS
FOR (c:EmergentCohort) ON (c.member_count);
