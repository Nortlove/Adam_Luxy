// =============================================================================
// ADAM Neo4j Migration 009: iHeart Relationships
// Relationship schemas for iHeart learning flows
// =============================================================================

// -----------------------------------------------------------------------------
// STATION RELATIONSHIPS
// -----------------------------------------------------------------------------

// HAS_PSYCHOGRAPHIC_PROFILE: Station's learned psychological profile
// Updated continuously from listener behavior
/*
(:Station)-[:HAS_PSYCHOGRAPHIC_PROFILE {
  // Big Five distribution
  openness_mean: FLOAT,
  openness_std: FLOAT,
  conscientiousness_mean: FLOAT,
  conscientiousness_std: FLOAT,
  extraversion_mean: FLOAT,
  extraversion_std: FLOAT,
  agreeableness_mean: FLOAT,
  agreeableness_std: FLOAT,
  neuroticism_mean: FLOAT,
  neuroticism_std: FLOAT,
  
  // Regulatory focus
  promotion_tendency: FLOAT,
  prevention_tendency: FLOAT,
  
  // Construal level
  abstract_tendency: FLOAT,
  
  // Sample basis
  listener_sample_size: INTEGER,
  confidence: FLOAT,
  computed_at: DATETIME
}]->(:StationPsychProfile)
*/

// PLAYS_CONTENT: Station → Content relationship (playlist)
/*
(:Station)-[:PLAYS_CONTENT {
  frequency: FLOAT,         // How often played
  daypart_distribution: MAP, // When played
  last_played: DATETIME
}]->(:Track)
*/

// IN_MARKET: Station → Market
/*
(:Station)-[:IN_MARKET {
  is_primary: BOOLEAN,
  coverage_percentage: FLOAT
}]->(:Market)
*/

// HAS_FORMAT: Station → Format with psychological priors
/*
(:Station)-[:HAS_FORMAT]->(:StationFormat)
*/

// -----------------------------------------------------------------------------
// CONTENT RELATIONSHIPS
// -----------------------------------------------------------------------------

// PERFORMED_BY: Track → Artist
/*
(:Track)-[:PERFORMED_BY {
  is_primary: BOOLEAN,
  role: STRING  // "artist", "featuring", "producer"
}]->(:Artist)
*/

// IN_GENRE: Track/Podcast → Genre
/*
(:Track)-[:IN_GENRE {
  confidence: FLOAT,
  is_primary: BOOLEAN
}]->(:Genre)

(:Podcast)-[:IN_GENRE]->(:Genre)
*/

// BELONGS_TO_PODCAST: Episode → Podcast
/*
(:PodcastEpisode)-[:BELONGS_TO_PODCAST]->(:Podcast)
*/

// GENRE_HIERARCHY: Genre parent-child
/*
(:Genre)-[:CHILD_OF]->(:Genre)
*/

// HAS_AUDIO_FEATURES: Track → AudioFeatures
// Spotify-style audio features for mood/energy matching
/*
(:Track)-[:HAS_AUDIO_FEATURES {
  energy: FLOAT,            // 0-1
  valence: FLOAT,           // 0-1, happiness
  tempo: FLOAT,             // BPM
  danceability: FLOAT,      // 0-1
  acousticness: FLOAT,      // 0-1
  instrumentalness: FLOAT,  // 0-1
  liveness: FLOAT,          // 0-1
  speechiness: FLOAT,       // 0-1
  loudness: FLOAT,          // dB
  key: INTEGER,
  mode: INTEGER,            // 0=minor, 1=major
  time_signature: INTEGER,
  duration_ms: INTEGER
}]->(:AudioFeatures)
*/

// -----------------------------------------------------------------------------
// LISTENING SESSION RELATIONSHIPS
// -----------------------------------------------------------------------------

// HAD_SESSION: User → Session
/*
(:User)-[:HAD_SESSION {
  platform: STRING,
  device_type: STRING
}]->(:ListeningSession)
*/

// SESSION_ON_STATION: Session → Station
/*
(:ListeningSession)-[:SESSION_ON_STATION {
  tuned_in_at: DATETIME,
  tuned_out_at: DATETIME,
  duration_seconds: INTEGER
}]->(:Station)
*/

// LISTENED_TO: Session → Content
/*
(:ListeningSession)-[:LISTENED_TO {
  started_at: DATETIME,
  completed: BOOLEAN,
  completion_percentage: FLOAT,
  skipped: BOOLEAN,
  skip_position_seconds: INTEGER
}]->(:Track | :PodcastEpisode)
*/

// HAD_EVENT: Session → Event (granular)
/*
(:ListeningSession)-[:HAD_EVENT]->(:ListeningEvent)
*/

// -----------------------------------------------------------------------------
// AD DECISION RELATIONSHIPS
// -----------------------------------------------------------------------------

// MADE_AD_DECISION: User → Decision
/*
(:User)-[:MADE_AD_DECISION {
  timestamp: DATETIME
}]->(:AdDecision)
*/

// DECISION_IN_SESSION: Decision → Session context
/*
(:AdDecision)-[:DECISION_IN_SESSION {
  position_in_session: STRING,  // "pre", "mid", "post"
  content_before_id: STRING
}]->(:ListeningSession)
*/

// SELECTED_CREATIVE: Decision → Creative
/*
(:AdDecision)-[:SELECTED_CREATIVE {
  selection_reason: STRING,
  selection_confidence: FLOAT
}]->(:AdCreative)
*/

// APPLIED_MECHANISM: Decision → Mechanism
// Critical for learning which mechanisms work
/*
(:AdDecision)-[:APPLIED_MECHANISM {
  intensity: FLOAT,
  activation_score: FLOAT,
  was_primary: BOOLEAN
}]->(:CognitiveMechanism)
*/

// HAD_OUTCOME: Decision → Outcome
/*
(:AdDecision)-[:HAD_OUTCOME {
  outcome_type: STRING,        // "listen_through", "click", "conversion", "skip"
  outcome_value: FLOAT,
  observed_at: DATETIME,
  attribution_confidence: FLOAT
}]->(:AdOutcome)
*/

// SERVED_ON_STATION: Decision → Station context
/*
(:AdDecision)-[:SERVED_ON_STATION {
  format_context: STRING
}]->(:Station)
*/

// AFTER_CONTENT: Decision context - what played before
/*
(:AdDecision)-[:AFTER_CONTENT {
  content_type: STRING,
  energy: FLOAT,
  valence: FLOAT
}]->(:Track | :PodcastEpisode)
*/

// -----------------------------------------------------------------------------
// CREATIVE AND CAMPAIGN RELATIONSHIPS
// -----------------------------------------------------------------------------

// BELONGS_TO_CAMPAIGN: Creative → Campaign
/*
(:AdCreative)-[:BELONGS_TO_CAMPAIGN]->(:Campaign)
*/

// CAMPAIGN_FOR_BRAND: Campaign → Brand
/*
(:Campaign)-[:CAMPAIGN_FOR_BRAND]->(:Brand)
*/

// CREATIVE_HAS_VARIANT: Creative variants for A/B testing
/*
(:AdCreative)-[:HAS_VARIANT {
  variant_type: STRING,  // "voice", "copy", "music"
  variant_id: STRING
}]->(:AdCreative)
*/

// USES_VOICE: Creative → Voice profile
/*
(:AdCreative)-[:USES_VOICE {
  voice_id: STRING,
  voice_personality: STRING
}]->(:VoiceProfile)
*/

// -----------------------------------------------------------------------------
// USER-CONTENT PREFERENCE RELATIONSHIPS
// -----------------------------------------------------------------------------

// PREFERS_STATION: User → Station preference
// Learned from listening patterns
/*
(:User)-[:PREFERS_STATION {
  listening_hours: FLOAT,
  session_count: INTEGER,
  last_listened: DATETIME,
  preference_score: FLOAT,
  computed_at: DATETIME
}]->(:Station)
*/

// PREFERS_ARTIST: User → Artist preference
/*
(:User)-[:PREFERS_ARTIST {
  play_count: INTEGER,
  skip_rate: FLOAT,
  completion_rate: FLOAT,
  preference_score: FLOAT
}]->(:Artist)
*/

// PREFERS_GENRE: User → Genre preference
/*
(:User)-[:PREFERS_GENRE {
  listening_percentage: FLOAT,
  preference_score: FLOAT
}]->(:Genre)
*/

// PREFERS_PODCAST_TOPIC: User → Topic preference
/*
(:User)-[:PREFERS_PODCAST_TOPIC {
  episode_count: INTEGER,
  completion_rate: FLOAT,
  preference_score: FLOAT
}]->(:Topic)
*/

// -----------------------------------------------------------------------------
// LEARNING SIGNAL RELATIONSHIPS
// -----------------------------------------------------------------------------

// EMITS_SIGNAL: Event → Learning Signal for Gradient Bridge
/*
(:ListeningEvent)-[:EMITS_SIGNAL {
  signal_type: STRING,
  signal_value: FLOAT,
  emitted_at: DATETIME
}]->(:LearningSignal)
*/

// INFORMS_PROFILE: Listening behavior → Profile update
/*
(:ListeningEvent)-[:INFORMS_PROFILE {
  construct_updated: STRING,
  delta: FLOAT,
  confidence: FLOAT
}]->(:User)
*/
