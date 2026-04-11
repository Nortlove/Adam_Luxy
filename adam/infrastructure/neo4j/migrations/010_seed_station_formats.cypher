// =============================================================================
// ADAM Neo4j Migration 010: Seed Station Formats
// Radio format → psychological profile mappings for cold-start
// =============================================================================

// -----------------------------------------------------------------------------
// STATION FORMATS WITH PSYCHOLOGICAL PRIORS
// These are learned from research and refined through observation
// -----------------------------------------------------------------------------

// CHR - Contemporary Hit Radio
MERGE (f:StationFormat {format_id: 'CHR'})
SET f.name = 'Contemporary Hit Radio',
    f.description = 'Top 40, current hits across genres',
    f.typical_demo = '18-34',
    
    // Big Five distribution
    f.openness_mean = 0.55,
    f.openness_std = 0.18,
    f.conscientiousness_mean = 0.48,
    f.conscientiousness_std = 0.20,
    f.extraversion_mean = 0.68,
    f.extraversion_std = 0.15,
    f.agreeableness_mean = 0.55,
    f.agreeableness_std = 0.18,
    f.neuroticism_mean = 0.52,
    f.neuroticism_std = 0.20,
    
    // Regulatory focus
    f.promotion_tendency = 0.65,
    f.prevention_tendency = 0.35,
    
    // Construal level
    f.abstract_tendency = 0.45,
    
    // Primary mechanisms
    f.primary_mechanisms = ['mimetic_desire', 'attention_dynamics', 'identity_construction'],
    
    // Ad characteristics
    f.optimal_ad_energy = 0.7,
    f.optimal_ad_pace = 'fast',
    
    f.created_at = datetime();

// Country
MERGE (f:StationFormat {format_id: 'Country'})
SET f.name = 'Country',
    f.description = 'Country music, storytelling, traditional values',
    f.typical_demo = '25-54',
    
    f.openness_mean = 0.45,
    f.openness_std = 0.18,
    f.conscientiousness_mean = 0.58,
    f.conscientiousness_std = 0.18,
    f.extraversion_mean = 0.55,
    f.extraversion_std = 0.18,
    f.agreeableness_mean = 0.62,
    f.agreeableness_std = 0.15,
    f.neuroticism_mean = 0.48,
    f.neuroticism_std = 0.20,
    
    f.promotion_tendency = 0.45,
    f.prevention_tendency = 0.55,
    f.abstract_tendency = 0.50,
    
    f.primary_mechanisms = ['identity_construction', 'evolutionary_motive_activation', 'temporal_construal'],
    f.optimal_ad_energy = 0.55,
    f.optimal_ad_pace = 'moderate',
    
    f.created_at = datetime();

// Rock
MERGE (f:StationFormat {format_id: 'Rock'})
SET f.name = 'Rock',
    f.description = 'Rock music, authenticity, rebellion',
    f.typical_demo = '25-54',
    
    f.openness_mean = 0.58,
    f.openness_std = 0.18,
    f.conscientiousness_mean = 0.48,
    f.conscientiousness_std = 0.20,
    f.extraversion_mean = 0.55,
    f.extraversion_std = 0.20,
    f.agreeableness_mean = 0.45,
    f.agreeableness_std = 0.18,
    f.neuroticism_mean = 0.52,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.55,
    f.prevention_tendency = 0.45,
    f.abstract_tendency = 0.48,
    
    f.primary_mechanisms = ['identity_construction', 'automatic_evaluation', 'evolutionary_motive_activation'],
    f.optimal_ad_energy = 0.65,
    f.optimal_ad_pace = 'moderate',
    
    f.created_at = datetime();

// Classical
MERGE (f:StationFormat {format_id: 'Classical'})
SET f.name = 'Classical',
    f.description = 'Classical music, sophistication, tradition',
    f.typical_demo = '45+',
    
    f.openness_mean = 0.72,
    f.openness_std = 0.15,
    f.conscientiousness_mean = 0.62,
    f.conscientiousness_std = 0.15,
    f.extraversion_mean = 0.42,
    f.extraversion_std = 0.18,
    f.agreeableness_mean = 0.58,
    f.agreeableness_std = 0.15,
    f.neuroticism_mean = 0.45,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.45,
    f.prevention_tendency = 0.55,
    f.abstract_tendency = 0.68,
    
    f.primary_mechanisms = ['temporal_construal', 'embodied_cognition', 'attention_dynamics'],
    f.optimal_ad_energy = 0.35,
    f.optimal_ad_pace = 'slow',
    
    f.created_at = datetime();

// News/Talk
MERGE (f:StationFormat {format_id: 'News_Talk'})
SET f.name = 'News/Talk',
    f.description = 'News, politics, talk shows, information',
    f.typical_demo = '35-64',
    
    f.openness_mean = 0.58,
    f.openness_std = 0.20,
    f.conscientiousness_mean = 0.58,
    f.conscientiousness_std = 0.18,
    f.extraversion_mean = 0.52,
    f.extraversion_std = 0.20,
    f.agreeableness_mean = 0.48,
    f.agreeableness_std = 0.20,
    f.neuroticism_mean = 0.55,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.42,
    f.prevention_tendency = 0.58,
    f.abstract_tendency = 0.62,
    
    f.primary_mechanisms = ['linguistic_framing', 'evolutionary_motive_activation', 'automatic_evaluation'],
    f.optimal_ad_energy = 0.50,
    f.optimal_ad_pace = 'moderate',
    
    f.created_at = datetime();

// Urban
MERGE (f:StationFormat {format_id: 'Urban'})
SET f.name = 'Urban',
    f.description = 'Hip-hop, R&B, urban contemporary',
    f.typical_demo = '18-34',
    
    f.openness_mean = 0.58,
    f.openness_std = 0.18,
    f.conscientiousness_mean = 0.50,
    f.conscientiousness_std = 0.20,
    f.extraversion_mean = 0.65,
    f.extraversion_std = 0.15,
    f.agreeableness_mean = 0.52,
    f.agreeableness_std = 0.18,
    f.neuroticism_mean = 0.52,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.62,
    f.prevention_tendency = 0.38,
    f.abstract_tendency = 0.45,
    
    f.primary_mechanisms = ['mimetic_desire', 'identity_construction', 'wanting_liking_dissociation'],
    f.optimal_ad_energy = 0.70,
    f.optimal_ad_pace = 'fast',
    
    f.created_at = datetime();

// Alternative
MERGE (f:StationFormat {format_id: 'Alternative'})
SET f.name = 'Alternative',
    f.description = 'Alternative rock, indie, non-mainstream',
    f.typical_demo = '18-34',
    
    f.openness_mean = 0.68,
    f.openness_std = 0.15,
    f.conscientiousness_mean = 0.48,
    f.conscientiousness_std = 0.20,
    f.extraversion_mean = 0.52,
    f.extraversion_std = 0.20,
    f.agreeableness_mean = 0.52,
    f.agreeableness_std = 0.18,
    f.neuroticism_mean = 0.55,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.58,
    f.prevention_tendency = 0.42,
    f.abstract_tendency = 0.55,
    
    f.primary_mechanisms = ['identity_construction', 'attention_dynamics', 'automatic_evaluation'],
    f.optimal_ad_energy = 0.55,
    f.optimal_ad_pace = 'moderate',
    
    f.created_at = datetime();

// Jazz
MERGE (f:StationFormat {format_id: 'Jazz'})
SET f.name = 'Jazz',
    f.description = 'Jazz music, sophistication, improvisation',
    f.typical_demo = '35-64',
    
    f.openness_mean = 0.70,
    f.openness_std = 0.15,
    f.conscientiousness_mean = 0.55,
    f.conscientiousness_std = 0.18,
    f.extraversion_mean = 0.48,
    f.extraversion_std = 0.20,
    f.agreeableness_mean = 0.58,
    f.agreeableness_std = 0.15,
    f.neuroticism_mean = 0.45,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.48,
    f.prevention_tendency = 0.52,
    f.abstract_tendency = 0.65,
    
    f.primary_mechanisms = ['embodied_cognition', 'attention_dynamics', 'temporal_construal'],
    f.optimal_ad_energy = 0.40,
    f.optimal_ad_pace = 'slow',
    
    f.created_at = datetime();

// Sports
MERGE (f:StationFormat {format_id: 'Sports'})
SET f.name = 'Sports',
    f.description = 'Sports talk, game coverage, analysis',
    f.typical_demo = '25-54',
    
    f.openness_mean = 0.48,
    f.openness_std = 0.20,
    f.conscientiousness_mean = 0.52,
    f.conscientiousness_std = 0.18,
    f.extraversion_mean = 0.62,
    f.extraversion_std = 0.15,
    f.agreeableness_mean = 0.52,
    f.agreeableness_std = 0.18,
    f.neuroticism_mean = 0.55,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.55,
    f.prevention_tendency = 0.45,
    f.abstract_tendency = 0.42,
    
    f.primary_mechanisms = ['mimetic_desire', 'evolutionary_motive_activation', 'identity_construction'],
    f.optimal_ad_energy = 0.65,
    f.optimal_ad_pace = 'fast',
    
    f.created_at = datetime();

// Hot AC - Hot Adult Contemporary
MERGE (f:StationFormat {format_id: 'Hot_AC'})
SET f.name = 'Hot Adult Contemporary',
    f.description = 'Current hits with adult appeal',
    f.typical_demo = '25-44',
    
    f.openness_mean = 0.52,
    f.openness_std = 0.18,
    f.conscientiousness_mean = 0.55,
    f.conscientiousness_std = 0.18,
    f.extraversion_mean = 0.58,
    f.extraversion_std = 0.18,
    f.agreeableness_mean = 0.58,
    f.agreeableness_std = 0.15,
    f.neuroticism_mean = 0.50,
    f.neuroticism_std = 0.18,
    
    f.promotion_tendency = 0.55,
    f.prevention_tendency = 0.45,
    f.abstract_tendency = 0.48,
    
    f.primary_mechanisms = ['attention_dynamics', 'mimetic_desire', 'temporal_construal'],
    f.optimal_ad_energy = 0.60,
    f.optimal_ad_pace = 'moderate',
    
    f.created_at = datetime();

// -----------------------------------------------------------------------------
// LINK FORMATS TO MECHANISMS
// Pre-populate format → mechanism effectiveness priors
// -----------------------------------------------------------------------------

MATCH (f:StationFormat {format_id: 'CHR'})
MATCH (m:CognitiveMechanism {mechanism_id: 'mech_05_mimetic_desire'})
MERGE (f)-[r:FORMAT_MECHANISM_PRIOR]->(m)
SET r.effectiveness = 0.75,
    r.confidence = 0.6,
    r.reasoning = 'CHR listeners are highly influenced by what is popular and trending',
    r.created_at = datetime();

MATCH (f:StationFormat {format_id: 'Classical'})
MATCH (m:CognitiveMechanism {mechanism_id: 'mech_09_temporal_construal'})
MERGE (f)-[r:FORMAT_MECHANISM_PRIOR]->(m)
SET r.effectiveness = 0.70,
    r.confidence = 0.65,
    r.reasoning = 'Classical listeners think abstractly and respond to sophisticated framing',
    r.created_at = datetime();

MATCH (f:StationFormat {format_id: 'Country'})
MATCH (m:CognitiveMechanism {mechanism_id: 'mech_08_identity_construction'})
MERGE (f)-[r:FORMAT_MECHANISM_PRIOR]->(m)
SET r.effectiveness = 0.72,
    r.confidence = 0.65,
    r.reasoning = 'Country music is deeply tied to identity and values expression',
    r.created_at = datetime();

MATCH (f:StationFormat {format_id: 'News_Talk'})
MATCH (m:CognitiveMechanism {mechanism_id: 'mech_04_linguistic_framing'})
MERGE (f)-[r:FORMAT_MECHANISM_PRIOR]->(m)
SET r.effectiveness = 0.70,
    r.confidence = 0.7,
    r.reasoning = 'News/Talk listeners are attuned to language and framing effects',
    r.created_at = datetime();

MATCH (f:StationFormat {format_id: 'Sports'})
MATCH (m:CognitiveMechanism {mechanism_id: 'mech_03_evolutionary_motive_activation'})
MERGE (f)-[r:FORMAT_MECHANISM_PRIOR]->(m)
SET r.effectiveness = 0.68,
    r.confidence = 0.6,
    r.reasoning = 'Sports engagement activates competition and status motives',
    r.created_at = datetime();
