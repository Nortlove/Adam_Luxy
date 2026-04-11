// =============================================================================
// ADAM Neo4j Migration 015: Amazon Media-Psychology-Product Graph
// =============================================================================
// 
// Creates the graph structure for the Media-Psychology-Product Triangle:
//
//                      PSYCHOLOGICAL PROFILE
//                              ▲
//                             /│\
//                            / │ \
//                           /  │  \
//                          ▼   │   ▼
//                   MEDIA ◀────┼───▶ PRODUCT
//                              │
//                              ▼
//                          REVIEWER
//
// This graph enables:
// - "People who consume X media tend to buy Y products"
// - "This psychological profile responds to Z mechanisms"
// - "Match ads to media consumption for seamless persuasion"
// =============================================================================

// -----------------------------------------------------------------------------
// SECTION 1: Category Classification Nodes
// -----------------------------------------------------------------------------

// Media categories (content consumption)
MERGE (c:CategoryType {name: 'MEDIA'})
SET c.description = 'Content consumption categories - reveals psychological preferences',
    c.categories = ['Books', 'Digital_Music', 'Kindle_Store', 'Movies_and_TV', 'Magazine_Subscriptions'];

// Product categories (purchase behavior)
MERGE (c:CategoryType {name: 'PRODUCT'})
SET c.description = 'Physical/consumable products - reveals lifestyle and needs',
    c.categories = ['All_Beauty', 'Amazon_Fashion', 'Beauty_and_Personal_Care', 'Clothing_Shoes_and_Jewelry', 'Grocery_and_Gourmet_Food'];

// -----------------------------------------------------------------------------
// SECTION 2: Media Category Nodes with Psychology
// -----------------------------------------------------------------------------

// Books
MERGE (c:AmazonCategory:MediaCategory {name: 'Books'})
SET c.category_type = 'MEDIA',
    c.openness = 0.72,
    c.need_for_cognition = 0.75,
    c.introspection = 0.70,
    c.delayed_gratification = 0.65,
    c.persuasion_style = 'intellectual_appeal',
    c.optimal_mechanisms = ['authority', 'self_improvement', 'intellectual_stimulation'];

// Digital Music
MERGE (c:AmazonCategory:MediaCategory {name: 'Digital_Music'})
SET c.category_type = 'MEDIA',
    c.openness = 0.68,
    c.emotional_sensitivity = 0.72,
    c.identity_expression = 0.70,
    c.mood_regulation = 0.75,
    c.persuasion_style = 'emotional_resonance',
    c.optimal_mechanisms = ['identity_expression', 'nostalgia', 'mood_matching'];

// Movies and TV
MERGE (c:AmazonCategory:MediaCategory {name: 'Movies_and_TV'})
SET c.category_type = 'MEDIA',
    c.openness = 0.62,
    c.need_for_escapism = 0.68,
    c.social_bonding = 0.60,
    c.emotional_processing = 0.65,
    c.persuasion_style = 'narrative_transport',
    c.optimal_mechanisms = ['storytelling', 'social_proof', 'escapism'];

// Kindle Store
MERGE (c:AmazonCategory:MediaCategory {name: 'Kindle_Store'})
SET c.category_type = 'MEDIA',
    c.openness = 0.70,
    c.need_for_cognition = 0.72,
    c.convenience_orientation = 0.68,
    c.tech_savvy = 0.65,
    c.persuasion_style = 'convenience_intellectual',
    c.optimal_mechanisms = ['convenience', 'intellectual_stimulation', 'value'];

// Magazine Subscriptions
MERGE (c:AmazonCategory:MediaCategory {name: 'Magazine_Subscriptions'})
SET c.category_type = 'MEDIA',
    c.openness = 0.65,
    c.need_for_information = 0.70,
    c.habit_formation = 0.72,
    c.identity_expression = 0.60,
    c.persuasion_style = 'identity_commitment',
    c.optimal_mechanisms = ['commitment', 'social_identity', 'authority'];

// -----------------------------------------------------------------------------
// SECTION 3: Product Category Nodes with Psychology
// -----------------------------------------------------------------------------

// All Beauty
MERGE (c:AmazonCategory:ProductCategory {name: 'All_Beauty'})
SET c.category_type = 'PRODUCT',
    c.self_image_investment = 0.75,
    c.social_presentation = 0.70,
    c.identity_expression = 0.68,
    c.experimentation = 0.60,
    c.persuasion_style = 'aspirational_identity',
    c.purchase_drivers = ['self_enhancement', 'social_approval', 'ritual'],
    c.optimal_mechanisms = ['social_proof', 'identity_expression', 'authority'];

// Amazon Fashion
MERGE (c:AmazonCategory:ProductCategory {name: 'Amazon_Fashion'})
SET c.category_type = 'PRODUCT',
    c.status_consciousness = 0.72,
    c.identity_expression = 0.75,
    c.trend_awareness = 0.70,
    c.social_signaling = 0.68,
    c.persuasion_style = 'social_aspiration',
    c.purchase_drivers = ['social_signaling', 'identity', 'trend_following'],
    c.optimal_mechanisms = ['social_proof', 'scarcity', 'identity_expression'];

// Beauty and Personal Care
MERGE (c:AmazonCategory:ProductCategory {name: 'Beauty_and_Personal_Care'})
SET c.category_type = 'PRODUCT',
    c.self_care = 0.72,
    c.health_consciousness = 0.65,
    c.quality_sensitivity = 0.68,
    c.routine_orientation = 0.70,
    c.persuasion_style = 'wellness_authority',
    c.purchase_drivers = ['self_care', 'health', 'routine'],
    c.optimal_mechanisms = ['authority', 'health_wellness', 'consistency'];

// Clothing Shoes and Jewelry
MERGE (c:AmazonCategory:ProductCategory {name: 'Clothing_Shoes_and_Jewelry'})
SET c.category_type = 'PRODUCT',
    c.identity_expression = 0.75,
    c.social_awareness = 0.70,
    c.quality_consciousness = 0.65,
    c.style_consistency = 0.68,
    c.persuasion_style = 'identity_quality',
    c.purchase_drivers = ['identity', 'occasion', 'quality'],
    c.optimal_mechanisms = ['social_proof', 'identity_expression', 'quality'];

// Grocery and Gourmet Food
MERGE (c:AmazonCategory:ProductCategory {name: 'Grocery_and_Gourmet_Food'})
SET c.category_type = 'PRODUCT',
    c.health_consciousness = 0.68,
    c.quality_over_price = 0.65,
    c.culinary_exploration = 0.60,
    c.routine_efficiency = 0.70,
    c.persuasion_style = 'quality_health',
    c.purchase_drivers = ['health', 'convenience', 'quality', 'exploration'],
    c.optimal_mechanisms = ['authority', 'health_wellness', 'authenticity'];

// -----------------------------------------------------------------------------
// SECTION 4: Cross-Domain Relationships
// -----------------------------------------------------------------------------

// Link media to product categories via cross-domain reviewers
// These will be created dynamically as data is ingested

// Create relationship type for category correlations
// (populated by ingestion pipeline)

// -----------------------------------------------------------------------------
// SECTION 5: Indexes and Constraints
// -----------------------------------------------------------------------------

// Indexes for reviewer lookups
CREATE INDEX amazon_reviewer_id IF NOT EXISTS
FOR (r:AmazonReviewer) ON (r.amazon_user_id);

// Index for cross-domain flag
CREATE INDEX amazon_reviewer_cross_domain IF NOT EXISTS
FOR (r:AmazonReviewer) ON (r.is_cross_domain);

// Index for product lookups
CREATE INDEX amazon_product_asin IF NOT EXISTS
FOR (p:AmazonProduct) ON (p.asin);

// Index for category type
CREATE INDEX amazon_category_type IF NOT EXISTS
FOR (c:AmazonCategory) ON (c.category_type);

// Composite index for cross-domain queries
CREATE INDEX amazon_reviewer_cross_confidence IF NOT EXISTS
FOR (r:AmazonReviewer) ON (r.is_cross_domain, r.cross_domain_confidence);

// -----------------------------------------------------------------------------
// SECTION 6: Persuasion Mechanism Library
// -----------------------------------------------------------------------------

// Create mechanism nodes for the persuasion engine
MERGE (m:PersuasionMechanism {name: 'authority'})
SET m.description = 'Leverage expert credibility and trust',
    m.psychological_basis = 'Trust heuristic, cognitive shortcuts',
    m.effective_for_traits = ['conscientiousness', 'need_for_cognition'];

MERGE (m:PersuasionMechanism {name: 'social_proof'})
SET m.description = 'Show that others are doing/buying it',
    m.psychological_basis = 'Social validation, conformity',
    m.effective_for_traits = ['extraversion', 'agreeableness'];

MERGE (m:PersuasionMechanism {name: 'scarcity'})
SET m.description = 'Limited availability creates urgency',
    m.psychological_basis = 'Loss aversion, FOMO',
    m.effective_for_traits = ['impulsivity', 'extraversion'];

MERGE (m:PersuasionMechanism {name: 'identity_expression'})
SET m.description = 'Connect product to self-identity',
    m.psychological_basis = 'Self-concept, identity motivation',
    m.effective_for_traits = ['openness', 'extraversion'];

MERGE (m:PersuasionMechanism {name: 'nostalgia'})
SET m.description = 'Evoke positive memories and emotions',
    m.psychological_basis = 'Emotional memory, positive affect',
    m.effective_for_traits = ['agreeableness', 'emotional_sensitivity'];

MERGE (m:PersuasionMechanism {name: 'intellectual_stimulation'})
SET m.description = 'Appeal to curiosity and learning',
    m.psychological_basis = 'Need for cognition, curiosity',
    m.effective_for_traits = ['openness', 'need_for_cognition'];

MERGE (m:PersuasionMechanism {name: 'self_improvement'})
SET m.description = 'Promise of becoming better version of self',
    m.psychological_basis = 'Growth motivation, ideal self',
    m.effective_for_traits = ['conscientiousness', 'openness'];

MERGE (m:PersuasionMechanism {name: 'convenience'})
SET m.description = 'Emphasize ease and time-saving',
    m.psychological_basis = 'Effort minimization, efficiency',
    m.effective_for_traits = ['conscientiousness', 'practical_orientation'];

MERGE (m:PersuasionMechanism {name: 'health_wellness'})
SET m.description = 'Connect to health and wellbeing',
    m.psychological_basis = 'Self-preservation, health goals',
    m.effective_for_traits = ['conscientiousness', 'health_consciousness'];

MERGE (m:PersuasionMechanism {name: 'authenticity'})
SET m.description = 'Emphasize genuine, real, unprocessed',
    m.psychological_basis = 'Trust, anti-artificiality',
    m.effective_for_traits = ['openness', 'quality_consciousness'];

MERGE (m:PersuasionMechanism {name: 'storytelling'})
SET m.description = 'Narrative transport into brand story',
    m.psychological_basis = 'Narrative transportation, empathy',
    m.effective_for_traits = ['openness', 'emotional_sensitivity'];

MERGE (m:PersuasionMechanism {name: 'escapism'})
SET m.description = 'Offer mental escape from daily routine',
    m.psychological_basis = 'Mood regulation, hedonic motivation',
    m.effective_for_traits = ['openness', 'need_for_escapism'];

// Link mechanisms to categories
MATCH (c:MediaCategory {name: 'Books'})
MATCH (m:PersuasionMechanism) WHERE m.name IN ['authority', 'self_improvement', 'intellectual_stimulation']
MERGE (c)-[:OPTIMAL_MECHANISM]->(m);

MATCH (c:MediaCategory {name: 'Digital_Music'})
MATCH (m:PersuasionMechanism) WHERE m.name IN ['identity_expression', 'nostalgia']
MERGE (c)-[:OPTIMAL_MECHANISM]->(m);

MATCH (c:MediaCategory {name: 'Movies_and_TV'})
MATCH (m:PersuasionMechanism) WHERE m.name IN ['storytelling', 'social_proof', 'escapism']
MERGE (c)-[:OPTIMAL_MECHANISM]->(m);

MATCH (c:ProductCategory {name: 'All_Beauty'})
MATCH (m:PersuasionMechanism) WHERE m.name IN ['social_proof', 'identity_expression', 'authority']
MERGE (c)-[:OPTIMAL_MECHANISM]->(m);

MATCH (c:ProductCategory {name: 'Amazon_Fashion'})
MATCH (m:PersuasionMechanism) WHERE m.name IN ['social_proof', 'scarcity', 'identity_expression']
MERGE (c)-[:OPTIMAL_MECHANISM]->(m);

MATCH (c:ProductCategory {name: 'Grocery_and_Gourmet_Food'})
MATCH (m:PersuasionMechanism) WHERE m.name IN ['authority', 'health_wellness', 'authenticity']
MERGE (c)-[:OPTIMAL_MECHANISM]->(m);

// -----------------------------------------------------------------------------
// SECTION 7: Cross-Domain Query Templates (stored as procedures)
// -----------------------------------------------------------------------------

// Note: These are example queries that can be run by the application

// Query: Find reviewers who consume both media and products
// MATCH (r:AmazonReviewer)
// WHERE r.is_cross_domain = true
// AND r.cross_domain_confidence > 0.5
// RETURN r.amazon_user_id, r.media_categories, r.product_categories

// Query: Find media-product correlations
// MATCH (r:AmazonReviewer)-[:REVIEWED_IN]->(mc:MediaCategory)
// MATCH (r)-[:REVIEWED_IN]->(pc:ProductCategory)
// WITH mc.name AS media, pc.name AS product, COUNT(r) AS co_occurrence
// RETURN media, product, co_occurrence ORDER BY co_occurrence DESC

// Query: Get persuasion recommendation for media consumer
// MATCH (mc:MediaCategory {name: $media_category})
// MATCH (mc)-[:OPTIMAL_MECHANISM]->(m:PersuasionMechanism)
// WITH mc, COLLECT(m.name) AS mechanisms
// RETURN mc.persuasion_style, mechanisms

// Query: Find psychologically similar reviewers
// MATCH (r1:AmazonReviewer {amazon_user_id: $target_id})
// MATCH (r2:AmazonReviewer)
// WHERE r2.amazon_user_id <> r1.amazon_user_id
// WITH r1, r2,
//      ABS(r1.openness - r2.openness) + 
//      ABS(r1.conscientiousness - r2.conscientiousness) +
//      ABS(r1.extraversion - r2.extraversion) AS psych_distance
// WHERE psych_distance < 0.3
// RETURN r2.amazon_user_id, psych_distance
// ORDER BY psych_distance LIMIT 10
