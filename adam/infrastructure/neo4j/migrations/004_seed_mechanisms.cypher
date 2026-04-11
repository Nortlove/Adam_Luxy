// =============================================================================
// ADAM Neo4j Migration 004: Seed Cognitive Mechanisms
// The 9 psychological mechanisms that form ADAM's persuasion intelligence
// =============================================================================

// -----------------------------------------------------------------------------
// THE 9 COGNITIVE MECHANISMS
// These are first-class entities, not labels. They explain WHY people convert.
// -----------------------------------------------------------------------------

// 1. Automatic Evaluation
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_01_automatic_evaluation'})
SET m.name = 'automatic_evaluation',
    m.full_name = 'Automatic Evaluation',
    m.description = 'Immediate, unconscious good/bad judgments that occur within milliseconds of stimulus presentation. These are the gut reactions that precede conscious thought and heavily influence subsequent processing.',
    m.detection_window_ms = 500,
    m.primary_signals = ['initial_dwell_time', 'first_scroll_direction', 'immediate_click_pattern'],
    m.secondary_signals = ['facial_expression_proxy', 'cursor_velocity_initial'],
    m.ad_implication = 'Ensure positive automatic evaluation through familiar, warm stimuli. Avoid triggering negative automatic reactions with unexpected or jarring elements.',
    m.message_strategies = ['warmth_cues', 'familiarity_signals', 'visual_fluency'],
    m.contraindications = ['cognitive_override_needed', 'deliberation_required'],
    m.research_basis = 'Bargh (1997) automaticity, Zajonc (1980) mere exposure',
    m.synergistic_mechanisms = ['attention_dynamics', 'embodied_cognition'],
    m.antagonistic_mechanisms = ['identity_construction'],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 2. Wanting-Liking Dissociation
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_02_wanting_liking_dissociation'})
SET m.name = 'wanting_liking_dissociation',
    m.full_name = 'Wanting-Liking Dissociation',
    m.description = 'The separation between wanting (incentive salience, dopamine-driven) and liking (hedonic impact, opioid-driven). People can want things they do not like and like things they do not want.',
    m.detection_window_ms = 5000,
    m.primary_signals = ['repeated_viewing', 'add_to_cart_without_purchase', 'wishlist_behavior'],
    m.secondary_signals = ['price_checking_frequency', 'comparison_shopping'],
    m.ad_implication = 'Target wanting through scarcity and urgency. Target liking through sensory richness and emotional resonance. Recognize when they diverge.',
    m.message_strategies = ['scarcity_cues', 'urgency_signals', 'anticipation_building'],
    m.contraindications = ['satisfaction_focus', 'post_purchase_context'],
    m.research_basis = 'Berridge (2009) wanting vs liking, dopamine research',
    m.synergistic_mechanisms = ['evolutionary_motive_activation', 'temporal_construal'],
    m.antagonistic_mechanisms = [],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 3. Evolutionary Motive Activation
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_03_evolutionary_motive_activation'})
SET m.name = 'evolutionary_motive_activation',
    m.full_name = 'Evolutionary Motive Activation',
    m.description = 'Ancestral motives (mate acquisition, status, kin care, self-protection, affiliation, disease avoidance) shape contemporary consumption in ways people do not recognize.',
    m.detection_window_ms = 10000,
    m.primary_signals = ['content_category_preferences', 'social_comparison_behavior', 'risk_assessment_patterns'],
    m.secondary_signals = ['time_of_month_patterns', 'seasonal_variations'],
    m.ad_implication = 'Subtly activate relevant evolutionary motives. Status products should hint at mate value. Safety products should activate protection motives.',
    m.message_strategies = ['status_signaling', 'mate_value_cues', 'protection_framing', 'affiliation_cues'],
    m.contraindications = ['explicit_motive_mention', 'perceived_manipulation'],
    m.research_basis = 'Griskevicius & Kenrick (2013) evolutionary consumer psychology',
    m.synergistic_mechanisms = ['mimetic_desire', 'identity_construction'],
    m.antagonistic_mechanisms = ['automatic_evaluation'],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 4. Linguistic Framing
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_04_linguistic_framing'})
SET m.name = 'linguistic_framing',
    m.full_name = 'Linguistic Framing',
    m.description = 'How information is linguistically framed shapes its processing and impact. Gain vs. loss frames, abstract vs. concrete language, metaphor selection all influence persuasion.',
    m.detection_window_ms = 3000,
    m.primary_signals = ['consumed_content_language', 'search_queries', 'interaction_patterns'],
    m.secondary_signals = ['language_style_matching', 'metaphor_resonance'],
    m.ad_implication = 'Match linguistic frame to regulatory focus. Prevention-focused users respond to loss frames. Promotion-focused users respond to gain frames.',
    m.message_strategies = ['gain_framing', 'loss_framing', 'metaphor_alignment', 'temporal_framing'],
    m.contraindications = ['frame_fatigue', 'perceived_manipulation'],
    m.research_basis = 'Tversky & Kahneman (1981) prospect theory, framing effects',
    m.synergistic_mechanisms = ['temporal_construal', 'identity_construction'],
    m.antagonistic_mechanisms = [],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 5. Mimetic Desire
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_05_mimetic_desire'})
SET m.name = 'mimetic_desire',
    m.full_name = 'Mimetic Desire',
    m.description = 'We desire through the desires of others (Girard). Social models mediate desire, making social proof deeply psychological rather than merely informational.',
    m.detection_window_ms = 86400000,
    m.primary_signals = ['social_graph_patterns', 'reference_behaviors', 'attention_to_others'],
    m.secondary_signals = ['influencer_following', 'peer_product_adoption'],
    m.ad_implication = 'Leverage social proof strategically. Show relevant social models. For high mimetic users, emphasize what admired others choose.',
    m.message_strategies = ['social_proof', 'influencer_alignment', 'peer_comparison'],
    m.contraindications = ['social_reactance', 'independence_seeking'],
    m.research_basis = 'Girard (1961) mimetic theory, Cialdini (2001) social proof',
    m.synergistic_mechanisms = ['evolutionary_motive_activation', 'identity_construction'],
    m.antagonistic_mechanisms = ['automatic_evaluation'],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 6. Embodied Cognition
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_06_embodied_cognition'})
SET m.name = 'embodied_cognition',
    m.full_name = 'Embodied Cognition',
    m.description = 'Physical experiences ground abstract concepts. Metaphors like warm relationships or weighty decisions reflect real cognitive mappings.',
    m.detection_window_ms = 5000,
    m.primary_signals = ['device_context', 'motion_patterns', 'spatial_signals'],
    m.secondary_signals = ['touch_patterns', 'scroll_pressure', 'orientation_changes'],
    m.ad_implication = 'Use embodied metaphors that match physical context. Mobile users in motion need different framing than stationary desktop users.',
    m.message_strategies = ['embodied_metaphor', 'physical_context_matching', 'sensory_language'],
    m.contraindications = ['metaphor_mismatch', 'physical_discomfort'],
    m.research_basis = 'Barsalou (2008) grounded cognition, Lakoff & Johnson (1980)',
    m.synergistic_mechanisms = ['automatic_evaluation', 'attention_dynamics'],
    m.antagonistic_mechanisms = [],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 7. Attention Dynamics
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_07_attention_dynamics'})
SET m.name = 'attention_dynamics',
    m.full_name = 'Attention Dynamics',
    m.description = 'Salience captures attention, habituation reduces it, and surprise resets processing. Attention is the gateway to all other processing.',
    m.detection_window_ms = 30000,
    m.primary_signals = ['gaze_patterns', 'dwell_time', 'revisit_frequency'],
    m.secondary_signals = ['scroll_pauses', 'zoom_behavior', 'element_interactions'],
    m.ad_implication = 'Manage novelty and familiarity. For habituated users, introduce novelty. For overwhelmed users, provide familiar anchors.',
    m.message_strategies = ['novelty_injection', 'familiarity_anchoring', 'surprise_elements'],
    m.contraindications = ['attention_fatigue', 'cognitive_overload'],
    m.research_basis = 'Itti & Koch (2001) saliency, attention research',
    m.synergistic_mechanisms = ['automatic_evaluation', 'embodied_cognition'],
    m.antagonistic_mechanisms = [],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 8. Identity Construction
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_08_identity_construction'})
SET m.name = 'identity_construction',
    m.full_name = 'Identity Construction',
    m.description = 'Consumption is identity work. People buy to signal to themselves and others who they are or want to become.',
    m.detection_window_ms = 604800000,
    m.primary_signals = ['consumption_patterns', 'brand_preferences', 'self_presentation'],
    m.secondary_signals = ['social_sharing', 'profile_curation', 'identity_statements'],
    m.ad_implication = 'Position product as identity-congruent or identity-aspirational. For identity-seekers, emphasize self-expression.',
    m.message_strategies = ['identity_affirmation', 'aspirational_identity', 'self_signaling'],
    m.contraindications = ['identity_threat', 'authenticity_concerns'],
    m.research_basis = 'Bodner & Prelec (2003) self-signaling, identity economics',
    m.synergistic_mechanisms = ['mimetic_desire', 'evolutionary_motive_activation'],
    m.antagonistic_mechanisms = ['automatic_evaluation'],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// 9. Temporal Construal
MERGE (m:CognitiveMechanism {mechanism_id: 'mech_09_temporal_construal'})
SET m.name = 'temporal_construal',
    m.full_name = 'Temporal Construal',
    m.description = 'Psychological distance determines construal level. Distant events are processed abstractly (why), near events concretely (how).',
    m.detection_window_ms = 60000,
    m.primary_signals = ['temporal_distance_signals', 'language_abstraction', 'planning_horizon'],
    m.secondary_signals = ['future_orientation', 'present_focus', 'abstraction_level'],
    m.ad_implication = 'Match construal to decision stage. Early stage = abstract benefits (why). Late stage = concrete features (how).',
    m.message_strategies = ['abstract_benefits', 'concrete_features', 'temporal_matching'],
    m.contraindications = ['construal_mismatch', 'temporal_confusion'],
    m.research_basis = 'Trope & Liberman (2010) construal level theory',
    m.synergistic_mechanisms = ['linguistic_framing', 'attention_dynamics'],
    m.antagonistic_mechanisms = [],
    m.population_base_rate = 0.5,
    m.created_at = datetime();

// -----------------------------------------------------------------------------
// CREATE MECHANISM INTERACTION RELATIONSHIPS
// Pre-populate known synergies and antagonisms
// -----------------------------------------------------------------------------

// Synergies
MATCH (a:CognitiveMechanism {mechanism_id: 'mech_01_automatic_evaluation'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_07_attention_dynamics'})
MERGE (a)-[r:SYNERGIZES_WITH]->(b)
SET r.synergy_multiplier = 1.3,
    r.conditions_context = 'initial_exposure',
    r.observations = 0,
    r.created_at = datetime();

MATCH (a:CognitiveMechanism {mechanism_id: 'mech_01_automatic_evaluation'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_06_embodied_cognition'})
MERGE (a)-[r:SYNERGIZES_WITH]->(b)
SET r.synergy_multiplier = 1.25,
    r.conditions_context = 'mobile_context',
    r.observations = 0,
    r.created_at = datetime();

MATCH (a:CognitiveMechanism {mechanism_id: 'mech_02_wanting_liking_dissociation'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_03_evolutionary_motive_activation'})
MERGE (a)-[r:SYNERGIZES_WITH]->(b)
SET r.synergy_multiplier = 1.35,
    r.conditions_context = 'desire_activation',
    r.observations = 0,
    r.created_at = datetime();

MATCH (a:CognitiveMechanism {mechanism_id: 'mech_05_mimetic_desire'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_08_identity_construction'})
MERGE (a)-[r:SYNERGIZES_WITH]->(b)
SET r.synergy_multiplier = 1.4,
    r.conditions_context = 'social_identity',
    r.observations = 0,
    r.created_at = datetime();

MATCH (a:CognitiveMechanism {mechanism_id: 'mech_04_linguistic_framing'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_09_temporal_construal'})
MERGE (a)-[r:SYNERGIZES_WITH]->(b)
SET r.synergy_multiplier = 1.3,
    r.conditions_context = 'message_construction',
    r.observations = 0,
    r.created_at = datetime();

// Antagonisms
MATCH (a:CognitiveMechanism {mechanism_id: 'mech_01_automatic_evaluation'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_08_identity_construction'})
MERGE (a)-[r:ANTAGONIZES]->(b)
SET r.antagonism_penalty = 0.7,
    r.conditions_context = 'deliberative_mode',
    r.observations = 0,
    r.created_at = datetime();

MATCH (a:CognitiveMechanism {mechanism_id: 'mech_03_evolutionary_motive_activation'})
MATCH (b:CognitiveMechanism {mechanism_id: 'mech_01_automatic_evaluation'})
MERGE (a)-[r:ANTAGONIZES]->(b)
SET r.antagonism_penalty = 0.75,
    r.conditions_context = 'conscious_override',
    r.observations = 0,
    r.created_at = datetime();
