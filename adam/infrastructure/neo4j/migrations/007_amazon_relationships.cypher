// =============================================================================
// ADAM Neo4j Migration 007: Amazon Relationship Schemas
// Relationships for Amazon review → psychological prior pipeline
// =============================================================================

// -----------------------------------------------------------------------------
// AMAZON USER RELATIONSHIPS
// -----------------------------------------------------------------------------

// WROTE_REVIEW: Links user to their reviews
// Critical for aggregating linguistic signals per user
/*
(:AmazonUser)-[:WROTE_REVIEW {
  review_id: STRING,
  timestamp: DATETIME,
  rating: FLOAT,
  verified_purchase: BOOLEAN
}]->(:AmazonReview)
*/

// HAS_LINGUISTIC_PROFILE: User's aggregated linguistic features
/*
(:AmazonUser)-[:HAS_LINGUISTIC_PROFILE {
  computed_at: DATETIME,
  review_count_used: INTEGER,
  confidence: FLOAT
}]->(:LinguisticProfile)
*/

// HAS_INFERRED_PERSONALITY: Big Five inference from reviews
/*
(:AmazonUser)-[:HAS_INFERRED_PERSONALITY {
  inferred_at: DATETIME,
  method: STRING,  // "linguistic", "behavioral", "hybrid"
  confidence: FLOAT,
  review_count_used: INTEGER
}]->(:InferredPersonality)
*/

// MATCHES_ARCHETYPE: User's best-matching reviewer archetype
/*
(:AmazonUser)-[:MATCHES_ARCHETYPE {
  match_score: FLOAT,
  distance_to_centroid: FLOAT,
  matched_at: DATETIME
}]->(:ReviewArchetype)
*/

// PREFERS_CATEGORY: User's category preferences (behavioral signal)
/*
(:AmazonUser)-[:PREFERS_CATEGORY {
  review_count: INTEGER,
  average_rating: FLOAT,
  verified_ratio: FLOAT,
  first_review: DATETIME,
  last_review: DATETIME,
  sentiment_mean: FLOAT
}]->(:AmazonCategory)
*/

// -----------------------------------------------------------------------------
// AMAZON REVIEW RELATIONSHIPS
// -----------------------------------------------------------------------------

// REVIEWS_PRODUCT: Links review to product
/*
(:AmazonReview)-[:REVIEWS_PRODUCT {
  rating: FLOAT,
  helpful_vote: INTEGER
}]->(:AmazonProduct)
*/

// IN_CATEGORY: Review belongs to category
/*
(:AmazonReview)-[:IN_CATEGORY]->(:AmazonCategory)
*/

// HAS_LINGUISTIC_FEATURES: Extracted features from review text
/*
(:AmazonReview)-[:HAS_LINGUISTIC_FEATURES {
  word_count: INTEGER,
  sentence_count: INTEGER,
  
  // LIWC-style features
  positive_emotion: FLOAT,
  negative_emotion: FLOAT,
  cognitive_process: FLOAT,
  social_words: FLOAT,
  affective_words: FLOAT,
  
  // Complexity
  avg_word_length: FLOAT,
  flesch_reading_ease: FLOAT,
  
  // Sentiment
  sentiment_score: FLOAT,
  sentiment_magnitude: FLOAT,
  
  // Big Five linguistic markers
  openness_markers: FLOAT,
  conscientiousness_markers: FLOAT,
  extraversion_markers: FLOAT,
  agreeableness_markers: FLOAT,
  neuroticism_markers: FLOAT,
  
  extracted_at: DATETIME
}]->(:LinguisticFeatureSet)
*/

// -----------------------------------------------------------------------------
// AMAZON PRODUCT RELATIONSHIPS
// -----------------------------------------------------------------------------

// BELONGS_TO_CATEGORY: Product category membership
/*
(:AmazonProduct)-[:BELONGS_TO_CATEGORY {
  is_main_category: BOOLEAN,
  category_level: INTEGER  // 0=main, 1=sub, 2=sub-sub, etc.
}]->(:AmazonCategory)
*/

// BOUGHT_TOGETHER: Co-purchase relationships
/*
(:AmazonProduct)-[:BOUGHT_TOGETHER {
  strength: FLOAT,
  observed_count: INTEGER
}]->(:AmazonProduct)
*/

// HAS_CATEGORY_PSYCHOLOGY: Category-level psychological patterns
/*
(:AmazonCategory)-[:HAS_CATEGORY_PSYCHOLOGY {
  computed_at: DATETIME,
  sample_size: INTEGER
}]->(:CategoryPsychology)
*/

// -----------------------------------------------------------------------------
// ARCHETYPE RELATIONSHIPS
// -----------------------------------------------------------------------------

// ARCHETYPE_FOR_CATEGORY: Category-specific archetypes
/*
(:ReviewArchetype)-[:ARCHETYPE_FOR_CATEGORY {
  prevalence: FLOAT,  // % of category users matching
  created_at: DATETIME
}]->(:AmazonCategory)
*/

// SIMILAR_TO_ARCHETYPE: Archetype similarity for cold-start
/*
(:ReviewArchetype)-[:SIMILAR_TO_ARCHETYPE {
  similarity_score: FLOAT,
  similarity_basis: STRING  // "personality", "behavior", "linguistic"
}]->(:ReviewArchetype)
*/

// ARCHETYPE_RESPONDS_TO: Archetype-level mechanism effectiveness
// Used for cold-start before user-level data exists
/*
(:ReviewArchetype)-[:ARCHETYPE_RESPONDS_TO {
  success_rate: FLOAT,
  confidence: FLOAT,
  sample_size: INTEGER,
  computed_at: DATETIME
}]->(:CognitiveMechanism)
*/

// ARCHETYPE_HAS_TRAIT: Archetype personality profile
/*
(:ReviewArchetype)-[:ARCHETYPE_HAS_TRAIT {
  value: FLOAT,
  confidence: FLOAT
}]->(:PersonalityDimension)
*/

// -----------------------------------------------------------------------------
// CROSS-PLATFORM IDENTITY LINKAGE
// -----------------------------------------------------------------------------

// LIKELY_SAME_USER: Probabilistic identity match
// Links Amazon users to platform users
/*
(:AmazonUser)-[:LIKELY_SAME_USER {
  match_probability: FLOAT,
  match_method: STRING,  // "email", "name", "behavioral", "device"
  matched_at: DATETIME,
  confidence: FLOAT
}]->(:User)
*/

// USES_ARCHETYPE_PRIOR: Platform user using Amazon archetype for cold-start
/*
(:User)-[:USES_ARCHETYPE_PRIOR {
  archetype_id: STRING,
  applied_at: DATETIME,
  weight: FLOAT,  // Decays as direct signals accumulate
  initial_confidence: FLOAT
}]->(:ReviewArchetype)
*/
