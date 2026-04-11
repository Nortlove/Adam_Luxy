// =============================================================================
// ADAM Neo4j Migration 008: iHeart Schema
// iHeart Audio Platform - Primary Learning Interface for ADAM
// 175M+ listeners, continuous psychological signal capture
// =============================================================================

// -----------------------------------------------------------------------------
// IHEART-SPECIFIC CONSTRAINTS
// -----------------------------------------------------------------------------

// Station - Radio stations and streaming channels
CREATE CONSTRAINT iheart_station_id_unique IF NOT EXISTS
FOR (s:Station) REQUIRE s.station_id IS UNIQUE;

// Track - Music tracks with audio features
CREATE CONSTRAINT iheart_track_id_unique IF NOT EXISTS
FOR (t:Track) REQUIRE t.track_id IS UNIQUE;

// Artist - Music artists
CREATE CONSTRAINT iheart_artist_id_unique IF NOT EXISTS
FOR (a:Artist) REQUIRE a.artist_id IS UNIQUE;

// Podcast - Podcast shows
CREATE CONSTRAINT iheart_podcast_id_unique IF NOT EXISTS
FOR (p:Podcast) REQUIRE p.podcast_id IS UNIQUE;

// PodcastEpisode - Individual podcast episodes
CREATE CONSTRAINT iheart_episode_id_unique IF NOT EXISTS
FOR (e:PodcastEpisode) REQUIRE e.episode_id IS UNIQUE;

// ListeningSession - User listening sessions
CREATE CONSTRAINT iheart_session_id_unique IF NOT EXISTS
FOR (s:ListeningSession) REQUIRE s.session_id IS UNIQUE;

// AdDecision - ADAM ad decisions
CREATE CONSTRAINT iheart_decision_id_unique IF NOT EXISTS
FOR (d:AdDecision) REQUIRE d.decision_id IS UNIQUE;

// AdCreative - Audio ad creatives
CREATE CONSTRAINT iheart_creative_id_unique IF NOT EXISTS
FOR (c:AdCreative) REQUIRE c.creative_id IS UNIQUE;

// Campaign - Advertising campaigns
CREATE CONSTRAINT iheart_campaign_id_unique IF NOT EXISTS
FOR (c:Campaign) REQUIRE c.campaign_id IS UNIQUE;

// Genre - Music/podcast genres
CREATE CONSTRAINT iheart_genre_id_unique IF NOT EXISTS
FOR (g:Genre) REQUIRE g.genre_id IS UNIQUE;

// ListeningEvent - Granular listening events
CREATE CONSTRAINT iheart_event_id_unique IF NOT EXISTS
FOR (e:ListeningEvent) REQUIRE e.event_id IS UNIQUE;

// -----------------------------------------------------------------------------
// IHEART-SPECIFIC INDEXES
// -----------------------------------------------------------------------------

// Station indexes
CREATE INDEX station_format IF NOT EXISTS
FOR (s:Station) ON (s.format);

CREATE INDEX station_market IF NOT EXISTS
FOR (s:Station) ON (s.market);

CREATE INDEX station_dma IF NOT EXISTS
FOR (s:Station) ON (s.dma_code);

CREATE INDEX station_coverage IF NOT EXISTS
FOR (s:Station) ON (s.coverage_type);

// Track indexes
CREATE INDEX track_artist IF NOT EXISTS
FOR (t:Track) ON (t.artist_id);

CREATE INDEX track_isrc IF NOT EXISTS
FOR (t:Track) ON (t.isrc);

CREATE INDEX track_energy IF NOT EXISTS
FOR (t:Track) ON (t.energy);

CREATE INDEX track_valence IF NOT EXISTS
FOR (t:Track) ON (t.valence);

// Artist indexes
CREATE INDEX artist_name IF NOT EXISTS
FOR (a:Artist) ON (a.name);

// Podcast indexes
CREATE INDEX podcast_category IF NOT EXISTS
FOR (p:Podcast) ON (p.category);

CREATE INDEX podcast_publisher IF NOT EXISTS
FOR (p:Podcast) ON (p.publisher);

// Episode indexes
CREATE INDEX episode_podcast IF NOT EXISTS
FOR (e:PodcastEpisode) ON (e.podcast_id);

CREATE INDEX episode_published IF NOT EXISTS
FOR (e:PodcastEpisode) ON (e.published_at);

// Session indexes
CREATE INDEX session_user IF NOT EXISTS
FOR (s:ListeningSession) ON (s.user_id);

CREATE INDEX session_station IF NOT EXISTS
FOR (s:ListeningSession) ON (s.station_id);

CREATE INDEX session_started IF NOT EXISTS
FOR (s:ListeningSession) ON (s.started_at);

CREATE INDEX session_platform IF NOT EXISTS
FOR (s:ListeningSession) ON (s.platform);

// AdDecision indexes
CREATE INDEX decision_user IF NOT EXISTS
FOR (d:AdDecision) ON (d.user_id);

CREATE INDEX decision_session IF NOT EXISTS
FOR (d:AdDecision) ON (d.session_id);

CREATE INDEX decision_timestamp IF NOT EXISTS
FOR (d:AdDecision) ON (d.timestamp);

CREATE INDEX decision_campaign IF NOT EXISTS
FOR (d:AdDecision) ON (d.campaign_id);

CREATE INDEX decision_outcome IF NOT EXISTS
FOR (d:AdDecision) ON (d.outcome_type);

// Creative indexes
CREATE INDEX creative_campaign IF NOT EXISTS
FOR (c:AdCreative) ON (c.campaign_id);

CREATE INDEX creative_brand IF NOT EXISTS
FOR (c:AdCreative) ON (c.brand_id);

// Campaign indexes
CREATE INDEX campaign_brand IF NOT EXISTS
FOR (c:Campaign) ON (c.brand_id);

CREATE INDEX campaign_active IF NOT EXISTS
FOR (c:Campaign) ON (c.is_active);

// Genre indexes
CREATE INDEX genre_parent IF NOT EXISTS
FOR (g:Genre) ON (g.parent_genre_id);

// Event indexes
CREATE INDEX event_user IF NOT EXISTS
FOR (e:ListeningEvent) ON (e.user_id);

CREATE INDEX event_session IF NOT EXISTS
FOR (e:ListeningEvent) ON (e.session_id);

CREATE INDEX event_type IF NOT EXISTS
FOR (e:ListeningEvent) ON (e.event_type);

CREATE INDEX event_timestamp IF NOT EXISTS
FOR (e:ListeningEvent) ON (e.timestamp);

// -----------------------------------------------------------------------------
// IHEART VECTOR INDEXES
// -----------------------------------------------------------------------------

// Station psychographic embedding
CREATE VECTOR INDEX station_psych_embedding IF NOT EXISTS
FOR (s:Station) ON (s.psychographic_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Track audio feature embedding
CREATE VECTOR INDEX track_audio_embedding IF NOT EXISTS
FOR (t:Track) ON (t.audio_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 256,
  `vector.similarity_function`: 'cosine'
}};

// Track lyrics embedding (for content matching)
CREATE VECTOR INDEX track_lyrics_embedding IF NOT EXISTS
FOR (t:Track) ON (t.lyrics_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Artist personality embedding
CREATE VECTOR INDEX artist_embedding IF NOT EXISTS
FOR (a:Artist) ON (a.personality_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Podcast topic embedding
CREATE VECTOR INDEX podcast_embedding IF NOT EXISTS
FOR (p:Podcast) ON (p.topic_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Ad creative embedding
CREATE VECTOR INDEX creative_embedding IF NOT EXISTS
FOR (c:AdCreative) ON (c.creative_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// IHEART FULL-TEXT INDEXES
// -----------------------------------------------------------------------------

CREATE FULLTEXT INDEX station_search IF NOT EXISTS
FOR (s:Station) ON EACH [s.name, s.call_sign, s.format_name, s.market];

CREATE FULLTEXT INDEX track_search IF NOT EXISTS
FOR (t:Track) ON EACH [t.title, t.album, t.lyrics_preview];

CREATE FULLTEXT INDEX artist_search IF NOT EXISTS
FOR (a:Artist) ON EACH [a.name, a.bio];

CREATE FULLTEXT INDEX podcast_search IF NOT EXISTS
FOR (p:Podcast) ON EACH [p.title, p.description, p.publisher];

CREATE FULLTEXT INDEX episode_search IF NOT EXISTS
FOR (e:PodcastEpisode) ON EACH [e.title, e.description, e.transcript_preview];
