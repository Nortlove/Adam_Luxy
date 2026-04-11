// =============================================================================
// ADAM Neo4j Migration 001: Core Constraints
// Ensures data integrity for all core entities
// =============================================================================

// -----------------------------------------------------------------------------
// CORE ENTITY CONSTRAINTS
// -----------------------------------------------------------------------------

// User - Central entity for psychological profiling
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

// Cognitive Mechanisms - The 9 persuasion mechanisms
CREATE CONSTRAINT mechanism_id_unique IF NOT EXISTS
FOR (m:CognitiveMechanism) REQUIRE m.mechanism_id IS UNIQUE;

// Personality Dimensions - The 35 psychological constructs
CREATE CONSTRAINT dimension_id_unique IF NOT EXISTS
FOR (d:PersonalityDimension) REQUIRE d.dimension_id IS UNIQUE;

// Decision - User decisions with mechanism applications
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (d:Decision) REQUIRE d.decision_id IS UNIQUE;

// Request - Ad/content requests
CREATE CONSTRAINT request_id_unique IF NOT EXISTS
FOR (r:Request) REQUIRE r.request_id IS UNIQUE;

// Session - User sessions
CREATE CONSTRAINT session_id_unique IF NOT EXISTS
FOR (s:Session) REQUIRE s.session_id IS UNIQUE;

// Outcome - Decision outcomes for learning
CREATE CONSTRAINT outcome_id_unique IF NOT EXISTS
FOR (o:Outcome) REQUIRE o.outcome_id IS UNIQUE;

// -----------------------------------------------------------------------------
// INTELLIGENCE SOURCE CONSTRAINTS
// -----------------------------------------------------------------------------

// Empirical Patterns - Discovered behavioral patterns
CREATE CONSTRAINT empirical_pattern_id_unique IF NOT EXISTS
FOR (p:EmpiricalPattern) REQUIRE p.pattern_id IS UNIQUE;

// Behavioral Signatures - Nonconscious behavioral signals
CREATE CONSTRAINT behavioral_signature_id_unique IF NOT EXISTS
FOR (b:BehavioralSignature) REQUIRE b.signature_id IS UNIQUE;

// Graph Emergence - Emergent graph insights
CREATE CONSTRAINT graph_emergence_id_unique IF NOT EXISTS
FOR (g:GraphEmergence) REQUIRE g.emergence_id IS UNIQUE;

// Bandit Posteriors - Thompson Sampling posteriors
CREATE CONSTRAINT bandit_posterior_id_unique IF NOT EXISTS
FOR (b:BanditPosterior) REQUIRE b.posterior_id IS UNIQUE;

// Reasoning Insights - Claude's psychological insights
CREATE CONSTRAINT reasoning_insight_id_unique IF NOT EXISTS
FOR (r:ReasoningInsight) REQUIRE r.insight_id IS UNIQUE;

// Learning Signals - Gradient Bridge signals
CREATE CONSTRAINT learning_signal_id_unique IF NOT EXISTS
FOR (l:LearningSignal) REQUIRE l.signal_id IS UNIQUE;

// -----------------------------------------------------------------------------
// V3 COGNITIVE LAYER CONSTRAINTS
// -----------------------------------------------------------------------------

// Emergent Constructs - Discovered psychological constructs
CREATE CONSTRAINT emergent_construct_id_unique IF NOT EXISTS
FOR (e:EmergentConstruct) REQUIRE e.construct_id IS UNIQUE;

// Causal Edges - Discovered causal relationships
CREATE CONSTRAINT causal_edge_id_unique IF NOT EXISTS
FOR (c:CausalEdge) REQUIRE c.edge_id IS UNIQUE;

// State Trajectories - User psychological state trajectories
CREATE CONSTRAINT state_trajectory_id_unique IF NOT EXISTS
FOR (t:StateTrajectory) REQUIRE t.trajectory_id IS UNIQUE;

// Mechanism Interactions - Synergies and antagonisms
CREATE CONSTRAINT mechanism_interaction_id_unique IF NOT EXISTS
FOR (i:MechanismInteraction) REQUIRE i.interaction_id IS UNIQUE;

// Temporal User States - Point-in-time psychological states
CREATE CONSTRAINT temporal_state_id_unique IF NOT EXISTS
FOR (t:TemporalUserState) REQUIRE t.state_id IS UNIQUE;

// Session Narratives - Story understanding of sessions
CREATE CONSTRAINT session_narrative_id_unique IF NOT EXISTS
FOR (n:SessionNarrative) REQUIRE n.narrative_id IS UNIQUE;

// -----------------------------------------------------------------------------
// PLATFORM-SPECIFIC CONSTRAINTS (iHeart + WPP)
// -----------------------------------------------------------------------------

// Archetype - Amazon-derived user archetypes
CREATE CONSTRAINT archetype_id_unique IF NOT EXISTS
FOR (a:Archetype) REQUIRE a.archetype_id IS UNIQUE;

// Brand - Brand personalities for matching
CREATE CONSTRAINT brand_id_unique IF NOT EXISTS
FOR (b:Brand) REQUIRE b.brand_id IS UNIQUE;

// Station - iHeart radio stations
CREATE CONSTRAINT station_id_unique IF NOT EXISTS
FOR (s:Station) REQUIRE s.station_id IS UNIQUE;

// Content - Audio/visual content
CREATE CONSTRAINT content_id_unique IF NOT EXISTS
FOR (c:Content) REQUIRE c.content_id IS UNIQUE;

// Ad Creative - Advertising creatives
CREATE CONSTRAINT creative_id_unique IF NOT EXISTS
FOR (c:AdCreative) REQUIRE c.creative_id IS UNIQUE;

// Cohort - Emergent user cohorts
CREATE CONSTRAINT cohort_id_unique IF NOT EXISTS
FOR (c:EmergentCohort) REQUIRE c.cohort_id IS UNIQUE;
