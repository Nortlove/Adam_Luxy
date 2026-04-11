// =============================================================================
// ADAM Neo4j Migration 003: Advanced Indexes
// Vector indexes for embedding similarity and full-text search
// =============================================================================

// -----------------------------------------------------------------------------
// VECTOR INDEXES - For embedding-based similarity search
// Requires Neo4j 5.11+ with vector index support
// -----------------------------------------------------------------------------

// User profile embedding - for archetype matching and similarity
CREATE VECTOR INDEX user_profile_embedding IF NOT EXISTS
FOR (u:User) ON (u.profile_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Behavioral signature embedding - for pattern matching
CREATE VECTOR INDEX behavioral_embedding IF NOT EXISTS
FOR (b:BehavioralSignature) ON (b.signature_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 256,
  `vector.similarity_function`: 'cosine'
}};

// Archetype embedding - for user matching
CREATE VECTOR INDEX archetype_embedding IF NOT EXISTS
FOR (a:Archetype) ON (a.archetype_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Brand personality embedding - for brand-user matching
CREATE VECTOR INDEX brand_embedding IF NOT EXISTS
FOR (b:Brand) ON (b.personality_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Content embedding - for content-user matching (iHeart)
CREATE VECTOR INDEX content_embedding IF NOT EXISTS
FOR (c:Content) ON (c.content_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Emergent construct embedding - for construct similarity
CREATE VECTOR INDEX emergent_construct_embedding IF NOT EXISTS
FOR (e:EmergentConstruct) ON (e.construct_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// Pattern embedding - for pattern similarity
CREATE VECTOR INDEX pattern_embedding IF NOT EXISTS
FOR (p:EmpiricalPattern) ON (p.pattern_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 256,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// FULL-TEXT SEARCH INDEXES
// For semantic search of reasoning insights and patterns
// -----------------------------------------------------------------------------

// Reasoning insight search - find insights by content
CREATE FULLTEXT INDEX reasoning_insight_search IF NOT EXISTS
FOR (r:ReasoningInsight) ON EACH [r.insight_content, r.insight_type, r.psychological_reasoning];

// Pattern search - find patterns by description
CREATE FULLTEXT INDEX pattern_search IF NOT EXISTS
FOR (p:EmpiricalPattern) ON EACH [p.pattern_name, p.condition, p.prediction, p.description];

// Emergent construct search - find novel constructs by description
CREATE FULLTEXT INDEX emergent_construct_search IF NOT EXISTS
FOR (e:EmergentConstruct) ON EACH [e.name, e.description, e.discovery_method];

// Brand search - find brands by name and description
CREATE FULLTEXT INDEX brand_search IF NOT EXISTS
FOR (b:Brand) ON EACH [b.name, b.description, b.category];

// Content search - find content by metadata (iHeart)
CREATE FULLTEXT INDEX content_search IF NOT EXISTS
FOR (c:Content) ON EACH [c.title, c.artist, c.genre, c.description];

// Station search - find stations by metadata (iHeart)
CREATE FULLTEXT INDEX station_search IF NOT EXISTS
FOR (s:Station) ON EACH [s.name, s.format, s.description, s.market];
