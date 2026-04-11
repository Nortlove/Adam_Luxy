// =============================================================================
// ADAM Neo4j Migration 006: Amazon Dataset Schema
// Schema for 1.2B+ Amazon reviews → psychological priors pipeline
// =============================================================================

// -----------------------------------------------------------------------------
// AMAZON-SPECIFIC CONSTRAINTS
// -----------------------------------------------------------------------------

// Amazon User - Distinct from platform User, linked via identity resolution
CREATE CONSTRAINT amazon_user_id_unique IF NOT EXISTS
FOR (u:AmazonUser) REQUIRE u.amazon_user_id IS UNIQUE;

// Amazon Product - Products from the corpus
CREATE CONSTRAINT amazon_product_asin_unique IF NOT EXISTS
FOR (p:AmazonProduct) REQUIRE p.asin IS UNIQUE;

// Amazon Review - Individual reviews
CREATE CONSTRAINT amazon_review_id_unique IF NOT EXISTS
FOR (r:AmazonReview) REQUIRE r.review_id IS UNIQUE;

// Amazon Category - Product categories
CREATE CONSTRAINT amazon_category_name_unique IF NOT EXISTS
FOR (c:AmazonCategory) REQUIRE c.name IS UNIQUE;

// Linguistic Profile - Extracted linguistic features per user
CREATE CONSTRAINT linguistic_profile_id_unique IF NOT EXISTS
FOR (l:LinguisticProfile) REQUIRE l.profile_id IS UNIQUE;

// Inferred Personality - Big Five inference from reviews
CREATE CONSTRAINT inferred_personality_id_unique IF NOT EXISTS
FOR (p:InferredPersonality) REQUIRE p.personality_id IS UNIQUE;

// Review Archetype - Clustered reviewer archetypes
CREATE CONSTRAINT review_archetype_id_unique IF NOT EXISTS
FOR (a:ReviewArchetype) REQUIRE a.archetype_id IS UNIQUE;

// Category Psychology - Category-specific psychological patterns
CREATE CONSTRAINT category_psychology_id_unique IF NOT EXISTS
FOR (c:CategoryPsychology) REQUIRE c.psychology_id IS UNIQUE;

// -----------------------------------------------------------------------------
// AMAZON-SPECIFIC INDEXES
// -----------------------------------------------------------------------------

// AmazonUser indexes
CREATE INDEX amazon_user_review_count IF NOT EXISTS
FOR (u:AmazonUser) ON (u.review_count);

CREATE INDEX amazon_user_first_review IF NOT EXISTS
FOR (u:AmazonUser) ON (u.first_review_at);

CREATE INDEX amazon_user_last_review IF NOT EXISTS
FOR (u:AmazonUser) ON (u.last_review_at);

CREATE INDEX amazon_user_confidence IF NOT EXISTS
FOR (u:AmazonUser) ON (u.profile_confidence);

// AmazonProduct indexes
CREATE INDEX amazon_product_category IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.main_category);

CREATE INDEX amazon_product_rating IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.average_rating);

CREATE INDEX amazon_product_review_count IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.rating_number);

CREATE INDEX amazon_product_parent IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.parent_asin);

// AmazonReview indexes
CREATE INDEX amazon_review_user IF NOT EXISTS
FOR (r:AmazonReview) ON (r.user_id);

CREATE INDEX amazon_review_product IF NOT EXISTS
FOR (r:AmazonReview) ON (r.asin);

CREATE INDEX amazon_review_timestamp IF NOT EXISTS
FOR (r:AmazonReview) ON (r.timestamp);

CREATE INDEX amazon_review_rating IF NOT EXISTS
FOR (r:AmazonReview) ON (r.rating);

CREATE INDEX amazon_review_verified IF NOT EXISTS
FOR (r:AmazonReview) ON (r.verified_purchase);

CREATE INDEX amazon_review_helpful IF NOT EXISTS
FOR (r:AmazonReview) ON (r.helpful_vote);

// LinguisticProfile indexes
CREATE INDEX linguistic_profile_user IF NOT EXISTS
FOR (l:LinguisticProfile) ON (l.amazon_user_id);

CREATE INDEX linguistic_profile_word_count IF NOT EXISTS
FOR (l:LinguisticProfile) ON (l.total_word_count);

// InferredPersonality indexes
CREATE INDEX inferred_personality_user IF NOT EXISTS
FOR (p:InferredPersonality) ON (p.amazon_user_id);

CREATE INDEX inferred_personality_confidence IF NOT EXISTS
FOR (p:InferredPersonality) ON (p.inference_confidence);

// ReviewArchetype indexes
CREATE INDEX review_archetype_cluster IF NOT EXISTS
FOR (a:ReviewArchetype) ON (a.cluster_id);

CREATE INDEX review_archetype_member_count IF NOT EXISTS
FOR (a:ReviewArchetype) ON (a.member_count);

// CategoryPsychology indexes
CREATE INDEX category_psychology_category IF NOT EXISTS
FOR (c:CategoryPsychology) ON (c.category_name);

// -----------------------------------------------------------------------------
// AMAZON VECTOR INDEXES
// -----------------------------------------------------------------------------

// AmazonUser linguistic embedding
CREATE VECTOR INDEX amazon_user_embedding IF NOT EXISTS
FOR (u:AmazonUser) ON (u.linguistic_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// ReviewArchetype centroid embedding
CREATE VECTOR INDEX archetype_centroid_embedding IF NOT EXISTS
FOR (a:ReviewArchetype) ON (a.centroid_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// AmazonProduct embedding (from description/features)
CREATE VECTOR INDEX amazon_product_embedding IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.product_embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// AMAZON FULL-TEXT INDEXES
// -----------------------------------------------------------------------------

CREATE FULLTEXT INDEX amazon_review_text_search IF NOT EXISTS
FOR (r:AmazonReview) ON EACH [r.title, r.text];

CREATE FULLTEXT INDEX amazon_product_search IF NOT EXISTS
FOR (p:AmazonProduct) ON EACH [p.title, p.description, p.store];
