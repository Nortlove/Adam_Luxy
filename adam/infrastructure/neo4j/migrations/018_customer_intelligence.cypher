// =============================================================================
// ADAM Migration 018: Customer Intelligence from Review Analysis
// 
// This migration adds nodes and relationships for storing customer intelligence
// derived from product review analysis. This is a core component of ADAM's
// learning loop - real customer psychology flows from reviews into all decisions.
// =============================================================================

// =============================================================================
// CONSTRAINTS
// =============================================================================

// CustomerIntelligence - aggregated intelligence from reviews
CREATE CONSTRAINT customer_intelligence_pk IF NOT EXISTS
FOR (ci:CustomerIntelligence) REQUIRE ci.product_id IS UNIQUE;

// ReviewerProfile - individual reviewer psychological profile
CREATE CONSTRAINT reviewer_profile_pk IF NOT EXISTS
FOR (rp:ReviewerProfile) REQUIRE rp.reviewer_id IS UNIQUE;

// ProductReview - individual review record
CREATE CONSTRAINT product_review_pk IF NOT EXISTS
FOR (pr:ProductReview) REQUIRE pr.review_id IS UNIQUE;

// =============================================================================
// INDEXES
// =============================================================================

// Fast lookup by product name
CREATE INDEX customer_intelligence_product_name IF NOT EXISTS
FOR (ci:CustomerIntelligence) ON (ci.product_name);

// Fast lookup by brand
CREATE INDEX customer_intelligence_brand IF NOT EXISTS
FOR (ci:CustomerIntelligence) ON (ci.brand);

// Fast lookup by dominant archetype (for archetype transfer)
CREATE INDEX customer_intelligence_archetype IF NOT EXISTS
FOR (ci:CustomerIntelligence) ON (ci.dominant_archetype);

// Fast lookup by confidence (for quality filtering)
CREATE INDEX customer_intelligence_confidence IF NOT EXISTS
FOR (ci:CustomerIntelligence) ON (ci.overall_confidence);

// Reviewer lookup by detected archetype
CREATE INDEX reviewer_archetype IF NOT EXISTS
FOR (rp:ReviewerProfile) ON (rp.detected_archetype);

// Review lookup by rating (for ideal customer extraction)
CREATE INDEX review_rating IF NOT EXISTS
FOR (pr:ProductReview) ON (pr.rating);

// =============================================================================
// CUSTOMER INTELLIGENCE NODE
// =============================================================================

// This is the aggregated customer intelligence from all reviews for a product.
// It integrates with:
// - ColdStartService (archetype priors)
// - MetaLearner (mechanism posteriors)
// - CopyGeneration (customer language)
// - GraphEdgeService (relationship traversal)

// Example CustomerIntelligence node:
// (:CustomerIntelligence {
//     product_id: "amazon_B0CHX2F5QT",
//     product_name: "iPhone 15 Pro",
//     brand: "Apple",
//     reviews_analyzed: 156,
//     sources_used: ["amazon", "product_page"],
//     last_updated: datetime(),
//     scrape_confidence: 0.85,
//     
//     // Archetype distribution
//     buyer_archetypes: {Achiever: 0.35, Explorer: 0.25, Guardian: 0.20, Connector: 0.15, Pragmatist: 0.05},
//     dominant_archetype: "Achiever",
//     archetype_confidence: 0.75,
//     
//     // Big Five averages
//     avg_openness: 0.68,
//     avg_conscientiousness: 0.72,
//     avg_extraversion: 0.58,
//     avg_agreeableness: 0.65,
//     avg_neuroticism: 0.42,
//     
//     // Regulatory focus
//     regulatory_focus_promotion: 0.62,
//     regulatory_focus_prevention: 0.38,
//     
//     // Purchase motivations
//     purchase_motivations: ["quality", "convenience", "status"],
//     primary_motivation: "quality",
//     
//     // Language patterns
//     characteristic_phrases: ["exactly what I needed", "game changer", "highly recommend"],
//     power_words: ["amazing", "perfect", "excellent", "love"],
//     language_tone: "enthusiastic",
//     
//     // Mechanism predictions
//     mechanism_authority: 0.78,
//     mechanism_social_proof: 0.72,
//     mechanism_scarcity: 0.65,
//     
//     // Quality metrics
//     avg_rating: 4.5,
//     overall_confidence: 0.72
// })

// =============================================================================
// RELATIONSHIPS
// =============================================================================

// CustomerIntelligence relates to ReviewArchetype (from 004_seed_mechanisms)
// INFORMS_ARCHETYPE - customer intelligence informs archetype understanding
// (:CustomerIntelligence)-[:INFORMS_ARCHETYPE {
//     sample_size: 156,
//     confidence: 0.75,
//     contribution_weight: 0.35
// }]->(:ReviewArchetype)

// CustomerIntelligence relates to CognitiveMechanism (from 004_seed_mechanisms)
// PREDICTS_MECHANISM_EFFECTIVENESS - review psychology predicts which mechanisms work
// (:CustomerIntelligence)-[:PREDICTS_MECHANISM_EFFECTIVENESS {
//     predicted_success_rate: 0.78,
//     confidence: 0.70,
//     sample_size: 156
// }]->(:CognitiveMechanism)

// CustomerIntelligence relates to PersonalityDimension (from 005_seed_personality)
// HAS_CUSTOMER_PROFILE - aggregate personality profile of buyers
// (:CustomerIntelligence)-[:HAS_CUSTOMER_PROFILE {
//     mean_score: 0.72,
//     std_deviation: 0.15,
//     sample_size: 156
// }]->(:PersonalityDimension)

// ReviewerProfile relates to CustomerIntelligence
// CONTRIBUTES_TO - individual reviewer contributes to aggregate
// (:ReviewerProfile)-[:CONTRIBUTES_TO {
//     weight: 0.05,
//     is_ideal_customer: true
// }]->(:CustomerIntelligence)

// ReviewerProfile relates to ReviewArchetype
// MATCHES_BUYER_ARCHETYPE - reviewer matches a buyer archetype
// (:ReviewerProfile)-[:MATCHES_BUYER_ARCHETYPE {
//     match_score: 0.85,
//     detected_at: datetime()
// }]->(:ReviewArchetype)

// =============================================================================
// SEED BUYER ARCHETYPES
// =============================================================================

// Create buyer archetypes that map to mechanism effectiveness
// These are distinct from the psychological archetypes - they represent
// buyer behavioral patterns derived from review analysis.

MERGE (achiever:BuyerArchetype {archetype_id: 'Achiever'})
SET achiever.name = 'Achiever',
    achiever.description = 'Goal-oriented buyers who value quality and status. Respond to authority and premium positioning.',
    achiever.openness = 0.65, achiever.conscientiousness = 0.75, achiever.extraversion = 0.60, achiever.agreeableness = 0.55, achiever.neuroticism = 0.40,
    achiever.regulatory_focus = 'promotion',
    achiever.primary_motivations = ['quality', 'status', 'performance'],
    achiever.mech_authority = 0.80, achiever.mech_social_proof = 0.65, achiever.mech_scarcity = 0.70, achiever.mech_reciprocity = 0.55, achiever.mech_commitment = 0.75,
    achiever.copy_triggers = ['premium', 'best', 'top-rated', 'professional', 'excellence'],
    achiever.updated_at = datetime();

MERGE (explorer:BuyerArchetype {archetype_id: 'Explorer'})
SET explorer.name = 'Explorer',
    explorer.description = 'Curious buyers seeking novel experiences. Respond to discovery framing and unique features.',
    explorer.openness = 0.85, explorer.conscientiousness = 0.55, explorer.extraversion = 0.70, explorer.agreeableness = 0.60, explorer.neuroticism = 0.45,
    explorer.regulatory_focus = 'promotion',
    explorer.primary_motivations = ['novelty', 'discovery', 'experience'],
    explorer.mech_authority = 0.55, explorer.mech_social_proof = 0.50, explorer.mech_scarcity = 0.75, explorer.mech_reciprocity = 0.60, explorer.mech_commitment = 0.50,
    explorer.copy_triggers = ['discover', 'new', 'innovative', 'explore', 'adventure'],
    explorer.updated_at = datetime();

MERGE (guardian:BuyerArchetype {archetype_id: 'Guardian'})
SET guardian.name = 'Guardian',
    guardian.description = 'Security-focused buyers valuing reliability and safety. Respond to trust and guarantee messaging.',
    guardian.openness = 0.45, guardian.conscientiousness = 0.80, guardian.extraversion = 0.45, guardian.agreeableness = 0.70, guardian.neuroticism = 0.55,
    guardian.regulatory_focus = 'prevention',
    guardian.primary_motivations = ['safety', 'reliability', 'security'],
    guardian.mech_authority = 0.75, guardian.mech_social_proof = 0.80, guardian.mech_scarcity = 0.40, guardian.mech_reciprocity = 0.70, guardian.mech_commitment = 0.65,
    guardian.copy_triggers = ['safe', 'reliable', 'trusted', 'guaranteed', 'proven'],
    guardian.updated_at = datetime();

MERGE (connector:BuyerArchetype {archetype_id: 'Connector'})
SET connector.name = 'Connector',
    connector.description = 'Socially-driven buyers influenced by community and relationships. Respond to social proof.',
    connector.openness = 0.60, connector.conscientiousness = 0.60, connector.extraversion = 0.80, connector.agreeableness = 0.75, connector.neuroticism = 0.50,
    connector.regulatory_focus = 'promotion',
    connector.primary_motivations = ['social_connection', 'belonging', 'sharing'],
    connector.mech_authority = 0.50, connector.mech_social_proof = 0.90, connector.mech_scarcity = 0.55, connector.mech_reciprocity = 0.80, connector.mech_commitment = 0.60,
    connector.copy_triggers = ['join', 'community', 'share', 'together', 'popular'],
    connector.updated_at = datetime();

MERGE (pragmatist:BuyerArchetype {archetype_id: 'Pragmatist'})
SET pragmatist.name = 'Pragmatist',
    pragmatist.description = 'Value-conscious buyers focused on practical benefits and ROI. Respond to logical arguments.',
    pragmatist.openness = 0.50, pragmatist.conscientiousness = 0.85, pragmatist.extraversion = 0.50, pragmatist.agreeableness = 0.55, pragmatist.neuroticism = 0.35,
    pragmatist.regulatory_focus = 'prevention',
    pragmatist.primary_motivations = ['value', 'efficiency', 'practicality'],
    pragmatist.mech_authority = 0.65, pragmatist.mech_social_proof = 0.60, pragmatist.mech_scarcity = 0.45, pragmatist.mech_reciprocity = 0.55, pragmatist.mech_commitment = 0.80,
    pragmatist.copy_triggers = ['value', 'efficient', 'practical', 'smart choice', 'worth it'],
    pragmatist.updated_at = datetime();

// =============================================================================
// CONNECT BUYER ARCHETYPES TO MECHANISMS
// =============================================================================

// Achiever mechanism connections
MATCH (achiever:BuyerArchetype {archetype_id: 'Achiever'})
MATCH (authority:CognitiveMechanism {name: 'authority'})
MERGE (achiever)-[r1:RESPONDS_TO_MECHANISM]->(authority)
SET r1.effectiveness = 0.80, r1.confidence = 0.75;

MATCH (achiever:BuyerArchetype {archetype_id: 'Achiever'})
MATCH (scarcity:CognitiveMechanism {name: 'scarcity'})
MERGE (achiever)-[r2:RESPONDS_TO_MECHANISM]->(scarcity)
SET r2.effectiveness = 0.70, r2.confidence = 0.70;

// Guardian mechanism connections  
MATCH (guardian:BuyerArchetype {archetype_id: 'Guardian'})
MATCH (social_proof:CognitiveMechanism {name: 'social_proof'})
MERGE (guardian)-[r3:RESPONDS_TO_MECHANISM]->(social_proof)
SET r3.effectiveness = 0.80, r3.confidence = 0.75;

MATCH (guardian:BuyerArchetype {archetype_id: 'Guardian'})
MATCH (authority:CognitiveMechanism {name: 'authority'})
MERGE (guardian)-[r4:RESPONDS_TO_MECHANISM]->(authority)
SET r4.effectiveness = 0.75, r4.confidence = 0.70;

// Connector mechanism connections
MATCH (connector:BuyerArchetype {archetype_id: 'Connector'})
MATCH (social_proof:CognitiveMechanism {name: 'social_proof'})
MERGE (connector)-[r5:RESPONDS_TO_MECHANISM]->(social_proof)
SET r5.effectiveness = 0.90, r5.confidence = 0.85;

MATCH (connector:BuyerArchetype {archetype_id: 'Connector'})
MATCH (reciprocity:CognitiveMechanism {name: 'reciprocity'})
MERGE (connector)-[r6:RESPONDS_TO_MECHANISM]->(reciprocity)
SET r6.effectiveness = 0.80, r6.confidence = 0.75;

// Explorer mechanism connections
MATCH (explorer:BuyerArchetype {archetype_id: 'Explorer'})
MATCH (scarcity:CognitiveMechanism {name: 'scarcity'})
MERGE (explorer)-[r7:RESPONDS_TO_MECHANISM]->(scarcity)
SET r7.effectiveness = 0.75, r7.confidence = 0.70;

// Pragmatist mechanism connections
MATCH (pragmatist:BuyerArchetype {archetype_id: 'Pragmatist'})
MATCH (commitment:CognitiveMechanism {name: 'commitment_consistency'})
MERGE (pragmatist)-[r8:RESPONDS_TO_MECHANISM]->(commitment)
SET r8.effectiveness = 0.80, r8.confidence = 0.75;

// =============================================================================
// VERIFICATION
// =============================================================================

// Verify buyer archetypes created
MATCH (ba:BuyerArchetype)
RETURN ba.archetype_id AS archetype, ba.description AS description
ORDER BY ba.archetype_id;

// Verify mechanism connections
MATCH (ba:BuyerArchetype)-[r:RESPONDS_TO_MECHANISM]->(m:CognitiveMechanism)
RETURN ba.archetype_id AS archetype, m.name AS mechanism, r.effectiveness AS effectiveness
ORDER BY ba.archetype_id, r.effectiveness DESC;
