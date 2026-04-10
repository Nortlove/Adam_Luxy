"""
Consumer-Brand Relationship Neo4j Schema
========================================

Contains the Cypher queries to initialize the Neo4j schema for the
5-Channel Consumer-Brand Relationship Detection System.

Execute with:
    from adam.intelligence.relationship.schema import initialize_relationship_schema
    await initialize_relationship_schema(neo4j_driver)
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA INITIALIZATION QUERIES
# =============================================================================

CONSTRAINT_QUERIES: List[str] = [
    # Core constraints
    "CREATE CONSTRAINT relationship_id IF NOT EXISTS FOR (r:ConsumerBrandRelationship) REQUIRE r.relationship_id IS UNIQUE",
    "CREATE CONSTRAINT signal_id IF NOT EXISTS FOR (s:RelationshipSignal) REQUIRE s.signal_id IS UNIQUE",
    "CREATE CONSTRAINT rel_type_id IF NOT EXISTS FOR (rt:RelationshipType) REQUIRE rt.type_id IS UNIQUE",
    "CREATE CONSTRAINT obs_channel_id IF NOT EXISTS FOR (ch:ObservationChannel) REQUIRE ch.channel_id IS UNIQUE",
    "CREATE CONSTRAINT language_pattern_id IF NOT EXISTS FOR (lp:LanguagePattern) REQUIRE lp.pattern_id IS UNIQUE",
    "CREATE CONSTRAINT validated_scale_id IF NOT EXISTS FOR (vs:ValidatedScale) REQUIRE vs.scale_id IS UNIQUE",
    "CREATE CONSTRAINT engagement_strategy_id IF NOT EXISTS FOR (es:EngagementStrategy) REQUIRE es.strategy_id IS UNIQUE",
    "CREATE CONSTRAINT ad_template_id IF NOT EXISTS FOR (act:AdCreativeTemplate) REQUIRE act.template_id IS UNIQUE",
    "CREATE CONSTRAINT relationship_outcome_id IF NOT EXISTS FOR (ro:RelationshipOutcome) REQUIRE ro.outcome_id IS UNIQUE",
]

INDEX_QUERIES: List[str] = [
    # Performance indexes
    "CREATE INDEX rel_brand IF NOT EXISTS FOR (r:ConsumerBrandRelationship) ON (r.brand_id)",
    "CREATE INDEX rel_type IF NOT EXISTS FOR (r:ConsumerBrandRelationship) ON (r.primary_relationship_type)",
    "CREATE INDEX rel_consumer IF NOT EXISTS FOR (r:ConsumerBrandRelationship) ON (r.consumer_id)",
    "CREATE INDEX signal_channel IF NOT EXISTS FOR (s:RelationshipSignal) ON (s.channel)",
    "CREATE INDEX signal_brand IF NOT EXISTS FOR (s:RelationshipSignal) ON (s.brand_id)",
    "CREATE INDEX signal_type IF NOT EXISTS FOR (s:RelationshipSignal) ON (s.relationship_type)",
    "CREATE INDEX pattern_rel_type IF NOT EXISTS FOR (lp:LanguagePattern) ON (lp.relationship_type)",
    "CREATE INDEX pattern_channel IF NOT EXISTS FOR (lp:LanguagePattern) ON (lp.primary_channel)",
]

# Observation Channels (The 5-Channel Taxonomy)
CHANNEL_QUERIES: List[str] = [
    """
    MERGE (ch1:ObservationChannel {channel_id: 'customer_reviews'})
    SET ch1.channel_name = 'Customer Reviews',
        ch1.channel_number = 1,
        ch1.is_observable = true,
        ch1.is_predictable = false,
        ch1.description = 'How customers talk about the brand/product in review contexts',
        ch1.reveals_aspects = ['Functional satisfaction', 'Emotional attachment', 'Relationship longevity', 'Identity integration', 'Loyalty indicators'],
        ch1.high_signal_relationships = ['committed_partnership', 'reliable_tool', 'dependency', 'childhood_friend', 'enemy', 'mentor']
    """,
    """
    MERGE (ch2:ObservationChannel {channel_id: 'social_signals'})
    SET ch2.channel_name = 'Social Media Signaling',
        ch2.channel_number = 2,
        ch2.is_observable = true,
        ch2.is_predictable = false,
        ch2.description = 'How customers signal their brand relationship to OTHER HUMANS',
        ch2.reveals_aspects = ['Status signaling', 'Tribal membership', 'Value alignment display', 'Lifestyle curation', 'Advocacy behavior'],
        ch2.high_signal_relationships = ['status_marker', 'tribal_badge', 'self_expression_vehicle', 'aspirational_icon', 'enemy']
    """,
    """
    MERGE (ch3:ObservationChannel {channel_id: 'self_expression'})
    SET ch3.channel_name = 'Self-Expression / Internal Identity',
        ch3.channel_number = 3,
        ch3.is_observable = true,
        ch3.is_predictable = false,
        ch3.description = 'How customers use the brand for SELF-relationship (identity construction)',
        ch3.reveals_aspects = ['Self-brand integration', 'Identity coherence', 'Self-concept crystallization', 'Authenticity perception'],
        ch3.high_signal_relationships = ['self_identity_core', 'self_expression_vehicle', 'committed_partnership', 'childhood_friend']
    """,
    """
    MERGE (ch4:ObservationChannel {channel_id: 'brand_positioning'})
    SET ch4.channel_name = 'Brand Self-Definition',
        ch4.channel_number = 4,
        ch4.is_observable = true,
        ch4.is_predictable = false,
        ch4.description = 'How the BRAND defines itself on owned channels',
        ch4.reveals_aspects = ['Brand archetype', 'Desired relationships', 'Target psychographics', 'Value proposition'],
        ch4.high_signal_relationships = ['mentor', 'tribal_badge', 'aspirational_icon', 'caregiver']
    """,
    """
    MERGE (ch5:ObservationChannel {channel_id: 'advertising'})
    SET ch5.channel_name = 'Advertisements',
        ch5.channel_number = 5,
        ch5.is_observable = true,
        ch5.is_predictable = true,
        ch5.description = 'PREDICTION TARGET: How brands signal desired relationships to consumers',
        ch5.reveals_aspects = ['Relationship invitation', 'Existing customer display', 'Value proposition framing'],
        ch5.high_signal_relationships = []
    """,
]

# Relationship Types
RELATIONSHIP_TYPE_QUERIES: List[str] = [
    # ==========================================================================
    # SELF-DEFINITION CATEGORY
    # ==========================================================================
    """
    MERGE (rt1:RelationshipType {type_id: 'self_identity_core'})
    SET rt1.type_name = 'Self-Identity Core',
        rt1.category = 'self_definition',
        rt1.definition = 'Brand integrated into core self-concept. Consumer IS the brand.',
        rt1.relational_model = 'communal_sharing',
        rt1.typical_strength_range = [4, 5],
        rt1.vulnerability_to_dissolution = 'very_low',
        rt1.primary_detection_channel = 'self_expression',
        rt1.secondary_detection_channels = ['customer_reviews', 'social_signals']
    """,
    """
    MERGE (rt2:RelationshipType {type_id: 'self_expression_vehicle'})
    SET rt2.type_name = 'Self-Expression Vehicle',
        rt2.category = 'self_definition',
        rt2.definition = 'Brand communicates self to self and others.',
        rt2.relational_model = 'communal_sharing',
        rt2.typical_strength_range = [3, 4],
        rt2.vulnerability_to_dissolution = 'moderate',
        rt2.primary_detection_channel = 'social_signals',
        rt2.secondary_detection_channels = ['self_expression']
    """,
    """
    MERGE (rt_compartment:RelationshipType {type_id: 'compartmentalized_identity'})
    SET rt_compartment.type_name = 'Compartmentalized Identity',
        rt_compartment.category = 'self_definition',
        rt_compartment.definition = 'Brand serves ONE specific life context (work self, hobby self). Not full identity, just one facet.',
        rt_compartment.relational_model = 'market_pricing',
        rt_compartment.typical_strength_range = [2, 3],
        rt_compartment.vulnerability_to_dissolution = 'moderate',
        rt_compartment.primary_detection_channel = 'customer_reviews',
        rt_compartment.secondary_detection_channels = ['self_expression'],
        rt_compartment.advertising_implications = 'Honor specific context. Do not over-extend brand meaning.'
    """,
    # ==========================================================================
    # SOCIAL SIGNALING CATEGORY
    # ==========================================================================
    """
    MERGE (rt3:RelationshipType {type_id: 'status_marker'})
    SET rt3.type_name = 'Status Marker',
        rt3.category = 'social_signaling',
        rt3.definition = 'Brand serves external status communication function.',
        rt3.relational_model = 'market_pricing',
        rt3.typical_strength_range = [2, 3],
        rt3.vulnerability_to_dissolution = 'high',
        rt3.primary_detection_channel = 'social_signals',
        rt3.secondary_detection_channels = ['customer_reviews']
    """,
    """
    MERGE (rt_compliance:RelationshipType {type_id: 'social_compliance'})
    SET rt_compliance.type_name = 'Social Compliance',
        rt_compliance.category = 'social_signaling',
        rt_compliance.definition = 'Uses brand because peer group expects it. Conformity-driven, not genuine preference.',
        rt_compliance.relational_model = 'equality_matching',
        rt_compliance.typical_strength_range = [2, 3],
        rt_compliance.vulnerability_to_dissolution = 'high',
        rt_compliance.primary_detection_channel = 'self_expression',
        rt_compliance.secondary_detection_channels = ['customer_reviews'],
        rt_compliance.advertising_implications = 'Build genuine personal connection. Vulnerable if social circle shifts.'
    """,
    # ==========================================================================
    # SOCIAL BELONGING CATEGORY
    # ==========================================================================
    """
    MERGE (rt4:RelationshipType {type_id: 'tribal_badge'})
    SET rt4.type_name = 'Tribal Badge',
        rt4.category = 'social_belonging',
        rt4.definition = 'Brand marks group membership and tribal identity.',
        rt4.relational_model = 'communal_sharing',
        rt4.typical_strength_range = [3, 5],
        rt4.vulnerability_to_dissolution = 'low',
        rt4.primary_detection_channel = 'social_signals',
        rt4.secondary_detection_channels = ['customer_reviews', 'self_expression']
    """,
    """
    MERGE (rt_champion:RelationshipType {type_id: 'champion_evangelist'})
    SET rt_champion.type_name = 'Champion/Evangelist',
        rt_champion.category = 'social_belonging',
        rt_champion.definition = 'Super-advocate who actively recruits others. Creates content, defends brand, converts friends.',
        rt_champion.relational_model = 'communal_sharing',
        rt_champion.typical_strength_range = [5, 5],
        rt_champion.vulnerability_to_dissolution = 'very_low',
        rt_champion.primary_detection_channel = 'social_signals',
        rt_champion.secondary_detection_channels = ['customer_reviews'],
        rt_champion.advertising_implications = 'Give recognition and tools to evangelize. Do NOT waste ad dollars - already sold.'
    """,
    # ==========================================================================
    # EMOTIONAL BOND CATEGORY
    # ==========================================================================
    """
    MERGE (rt5:RelationshipType {type_id: 'committed_partnership'})
    SET rt5.type_name = 'Committed Partnership',
        rt5.category = 'emotional_bond',
        rt5.definition = 'Long-term emotional bond with high love, trust, commitment.',
        rt5.relational_model = 'communal_sharing',
        rt5.typical_strength_range = [4, 5],
        rt5.vulnerability_to_dissolution = 'low',
        rt5.primary_detection_channel = 'customer_reviews',
        rt5.secondary_detection_channels = ['social_signals', 'self_expression']
    """,
    """
    MERGE (rt6:RelationshipType {type_id: 'dependency'})
    SET rt6.type_name = 'Dependency',
        rt6.category = 'emotional_bond',
        rt6.definition = 'Excessive reliance creating anxiety about brand availability.',
        rt6.relational_model = 'communal_sharing',
        rt6.typical_strength_range = [4, 5],
        rt6.vulnerability_to_dissolution = 'very_low',
        rt6.primary_detection_channel = 'customer_reviews',
        rt6.secondary_detection_channels = ['self_expression']
    """,
    """
    MERGE (rt_guilty:RelationshipType {type_id: 'guilty_pleasure'})
    SET rt_guilty.type_name = 'Guilty Pleasure',
        rt_guilty.category = 'emotional_bond',
        rt_guilty.definition = 'Private consumption that conflicts with public self-image. Hidden usage.',
        rt_guilty.relational_model = 'communal_sharing',
        rt_guilty.typical_strength_range = [3, 4],
        rt_guilty.vulnerability_to_dissolution = 'moderate',
        rt_guilty.primary_detection_channel = 'self_expression',
        rt_guilty.secondary_detection_channels = ['customer_reviews'],
        rt_guilty.advertising_implications = 'Normalize. Respect privacy. AVOID social proof.'
    """,
    """
    MERGE (rt_rescue:RelationshipType {type_id: 'rescue_savior'})
    SET rt_rescue.type_name = 'Rescue/Savior',
        rt_rescue.category = 'emotional_bond',
        rt_rescue.definition = 'Intense gratitude because brand appeared during crisis or turning point.',
        rt_rescue.relational_model = 'communal_sharing',
        rt_rescue.typical_strength_range = [5, 5],
        rt_rescue.vulnerability_to_dissolution = 'very_low',
        rt_rescue.primary_detection_channel = 'customer_reviews',
        rt_rescue.secondary_detection_channels = ['self_expression'],
        rt_rescue.advertising_implications = 'Honor transformation story. Testimonial goldmine.'
    """,
    # ==========================================================================
    # FUNCTIONAL CATEGORY
    # ==========================================================================
    """
    MERGE (rt7:RelationshipType {type_id: 'reliable_tool'})
    SET rt7.type_name = 'Reliable Tool',
        rt7.category = 'functional_utility',
        rt7.definition = 'Purely functional relationship. Low emotional investment.',
        rt7.relational_model = 'market_pricing',
        rt7.typical_strength_range = [2, 3],
        rt7.vulnerability_to_dissolution = 'high',
        rt7.primary_detection_channel = 'customer_reviews',
        rt7.secondary_detection_channels = []
    """,
    # ==========================================================================
    # GUIDANCE CATEGORY
    # ==========================================================================
    """
    MERGE (rt8:RelationshipType {type_id: 'mentor'})
    SET rt8.type_name = 'Mentor',
        rt8.category = 'guidance_authority',
        rt8.definition = 'Brand as expert guide. Consumer as learner.',
        rt8.relational_model = 'authority_ranking',
        rt8.typical_strength_range = [3, 4],
        rt8.vulnerability_to_dissolution = 'moderate',
        rt8.primary_detection_channel = 'customer_reviews',
        rt8.secondary_detection_channels = ['brand_positioning']
    """,
    # ==========================================================================
    # THERAPEUTIC CATEGORY
    # ==========================================================================
    """
    MERGE (rt9:RelationshipType {type_id: 'comfort_companion'})
    SET rt9.type_name = 'Comfort Companion',
        rt9.category = 'therapeutic_escape',
        rt9.definition = 'Brand provides emotional comfort and stress relief.',
        rt9.relational_model = 'communal_sharing',
        rt9.typical_strength_range = [3, 4],
        rt9.vulnerability_to_dissolution = 'moderate',
        rt9.primary_detection_channel = 'customer_reviews',
        rt9.secondary_detection_channels = ['self_expression']
    """,
    # ==========================================================================
    # TEMPORAL/NOSTALGIC CATEGORY
    # ==========================================================================
    """
    MERGE (rt10:RelationshipType {type_id: 'childhood_friend'})
    SET rt10.type_name = 'Childhood Friend',
        rt10.category = 'temporal_nostalgic',
        rt10.definition = 'Nostalgic bond from earlier life. Identity continuity.',
        rt10.relational_model = 'communal_sharing',
        rt10.typical_strength_range = [3, 4],
        rt10.vulnerability_to_dissolution = 'low',
        rt10.primary_detection_channel = 'customer_reviews',
        rt10.secondary_detection_channels = ['self_expression']
    """,
    """
    MERGE (rt_seasonal:RelationshipType {type_id: 'seasonal_rekindler'})
    SET rt_seasonal.type_name = 'Seasonal Rekindler',
        rt_seasonal.category = 'temporal_nostalgic',
        rt_seasonal.definition = 'Predictable cyclical engagement tied to seasons, holidays, or contexts.',
        rt_seasonal.relational_model = 'equality_matching',
        rt_seasonal.typical_strength_range = [3, 4],
        rt_seasonal.vulnerability_to_dissolution = 'low',
        rt_seasonal.primary_detection_channel = 'customer_reviews',
        rt_seasonal.secondary_detection_channels = ['social_signals'],
        rt_seasonal.advertising_implications = 'Timing is everything. Build anticipation. Do NOT message off-season.'
    """,
    # ==========================================================================
    # ASPIRATIONAL CATEGORY
    # ==========================================================================
    """
    MERGE (rt11:RelationshipType {type_id: 'aspirational_icon'})
    SET rt11.type_name = 'Aspirational Icon',
        rt11.category = 'aspirational',
        rt11.definition = 'One-sided relationship with ideal-self brand.',
        rt11.relational_model = 'authority_ranking',
        rt11.typical_strength_range = [3, 4],
        rt11.vulnerability_to_dissolution = 'moderate',
        rt11.primary_detection_channel = 'social_signals',
        rt11.secondary_detection_channels = ['brand_positioning']
    """,
    # ==========================================================================
    # ACQUISITION/EXPLORATION CATEGORY
    # ==========================================================================
    """
    MERGE (rt_courtship:RelationshipType {type_id: 'courtship_dating'})
    SET rt_courtship.type_name = 'Courtship/Dating',
        rt_courtship.category = 'acquisition_exploration',
        rt_courtship.definition = 'Active exploration phase before commitment. Consumer is trying out the brand.',
        rt_courtship.relational_model = 'market_pricing',
        rt_courtship.typical_strength_range = [1, 2],
        rt_courtship.vulnerability_to_dissolution = 'very_high',
        rt_courtship.primary_detection_channel = 'customer_reviews',
        rt_courtship.secondary_detection_channels = [],
        rt_courtship.advertising_implications = 'Reduce risk. Demonstrate value. Conversion messaging, not retention.'
    """,
    """
    MERGE (rt_rebound:RelationshipType {type_id: 'rebound_relationship'})
    SET rt_rebound.type_name = 'Rebound Relationship',
        rt_rebound.category = 'acquisition_exploration',
        rt_rebound.definition = 'Chose brand as reaction AGAINST former brand, not genuine attraction.',
        rt_rebound.relational_model = 'market_pricing',
        rt_rebound.typical_strength_range = [2, 3],
        rt_rebound.vulnerability_to_dissolution = 'high',
        rt_rebound.primary_detection_channel = 'customer_reviews',
        rt_rebound.secondary_detection_channels = ['social_signals'],
        rt_rebound.advertising_implications = 'Build positive connection. AVOID competitor mentions.'
    """,
    # ==========================================================================
    # NEGATIVE/TRAPPED CATEGORY
    # ==========================================================================
    """
    MERGE (rt12:RelationshipType {type_id: 'enemy'})
    SET rt12.type_name = 'Enemy',
        rt12.category = 'negative',
        rt12.definition = 'Active hostility from perceived betrayal.',
        rt12.relational_model = 'negative_communal',
        rt12.typical_strength_range = [4, 5],
        rt12.vulnerability_to_dissolution = 'low',
        rt12.primary_detection_channel = 'social_signals',
        rt12.secondary_detection_channels = ['customer_reviews']
    """,
    """
    MERGE (rt_captive:RelationshipType {type_id: 'captive_enslavement'})
    SET rt_captive.type_name = 'Captive/Enslavement',
        rt_captive.category = 'negative',
        rt_captive.definition = 'Consumer feels trapped due to switching costs or lack of alternatives. Resents the relationship.',
        rt_captive.relational_model = 'market_pricing',
        rt_captive.typical_strength_range = [3, 4],
        rt_captive.vulnerability_to_dissolution = 'very_high',
        rt_captive.primary_detection_channel = 'customer_reviews',
        rt_captive.secondary_detection_channels = ['social_signals'],
        rt_captive.advertising_implications = 'Demonstrate value. Surprise with delight. NEVER use loyalty messaging.'
    """,
    """
    MERGE (rt_reluctant:RelationshipType {type_id: 'reluctant_user'})
    SET rt_reluctant.type_name = 'Reluctant User',
        rt_reluctant.category = 'negative',
        rt_reluctant.definition = 'Uses brand but actively dislikes it. No current alternative due to budget, availability, or requirements.',
        rt_reluctant.relational_model = 'market_pricing',
        rt_reluctant.typical_strength_range = [1, 2],
        rt_reluctant.vulnerability_to_dissolution = 'very_high',
        rt_reluctant.primary_detection_channel = 'customer_reviews',
        rt_reluctant.secondary_detection_channels = [],
        rt_reluctant.advertising_implications = 'Improve value perception. Exceed expectations. Will defect when alternatives appear.'
    """,
    # ==========================================================================
    # MISSING BASE TYPES (6 types)
    # ==========================================================================
    """
    MERGE (rt_fling:RelationshipType {type_id: 'fling'})
    SET rt_fling.type_name = 'Fling',
        rt_fling.category = 'emotional_bond',
        rt_fling.definition = 'Short-term, exciting but uncommitted relationship. Novelty-driven.',
        rt_fling.relational_model = 'market_pricing',
        rt_fling.typical_strength_range = [2, 3],
        rt_fling.vulnerability_to_dissolution = 'very_high',
        rt_fling.primary_detection_channel = 'customer_reviews',
        rt_fling.secondary_detection_channels = ['social_signals'],
        rt_fling.advertising_implications = 'Emphasize excitement and novelty. Limited-time offers work well.'
    """,
    """
    MERGE (rt_secret:RelationshipType {type_id: 'secret_affair'})
    SET rt_secret.type_name = 'Secret Affair',
        rt_secret.category = 'emotional_bond',
        rt_secret.definition = 'Hidden relationship that conflicts with public persona or stated values.',
        rt_secret.relational_model = 'communal_sharing',
        rt_secret.typical_strength_range = [3, 4],
        rt_secret.vulnerability_to_dissolution = 'moderate',
        rt_secret.primary_detection_channel = 'self_expression',
        rt_secret.secondary_detection_channels = [],
        rt_secret.advertising_implications = 'Respect privacy. Discreet messaging. AVOID social proof.'
    """,
    """
    MERGE (rt_bestfriend:RelationshipType {type_id: 'best_friend_utility'})
    SET rt_bestfriend.type_name = 'Best Friend Utility',
        rt_bestfriend.category = 'functional_utility',
        rt_bestfriend.definition = 'Reliable, trusted, always-there functional relationship with emotional warmth.',
        rt_bestfriend.relational_model = 'equality_matching',
        rt_bestfriend.typical_strength_range = [3, 4],
        rt_bestfriend.vulnerability_to_dissolution = 'low',
        rt_bestfriend.primary_detection_channel = 'customer_reviews',
        rt_bestfriend.secondary_detection_channels = ['self_expression'],
        rt_bestfriend.advertising_implications = 'Emphasize reliability and trust. Everyday support messaging.'
    """,
    """
    MERGE (rt_caregiver:RelationshipType {type_id: 'caregiver'})
    SET rt_caregiver.type_name = 'Caregiver',
        rt_caregiver.category = 'guidance_authority',
        rt_caregiver.definition = 'Brand provides nurturing, protective, parental-like support.',
        rt_caregiver.relational_model = 'communal_sharing',
        rt_caregiver.typical_strength_range = [3, 4],
        rt_caregiver.vulnerability_to_dissolution = 'low',
        rt_caregiver.primary_detection_channel = 'customer_reviews',
        rt_caregiver.secondary_detection_channels = ['brand_positioning'],
        rt_caregiver.advertising_implications = 'Nurturing, protective messaging. Safety and reassurance.'
    """,
    """
    MERGE (rt_escape:RelationshipType {type_id: 'escape_artist'})
    SET rt_escape.type_name = 'Escape Artist',
        rt_escape.category = 'therapeutic_escape',
        rt_escape.definition = 'Brand provides escape from daily life, fantasy, transformation.',
        rt_escape.relational_model = 'communal_sharing',
        rt_escape.typical_strength_range = [3, 4],
        rt_escape.vulnerability_to_dissolution = 'moderate',
        rt_escape.primary_detection_channel = 'customer_reviews',
        rt_escape.secondary_detection_channels = ['social_signals'],
        rt_escape.advertising_implications = 'Escapism and fantasy messaging. Stress relief positioning.'
    """,
    """
    MERGE (rt_ex:RelationshipType {type_id: 'ex_relationship'})
    SET rt_ex.type_name = 'Ex-Relationship',
        rt_ex.category = 'negative',
        rt_ex.definition = 'Former relationship ended but not hostile. Neutral or wistful.',
        rt_ex.relational_model = 'market_pricing',
        rt_ex.typical_strength_range = [1, 2],
        rt_ex.vulnerability_to_dissolution = 'high',
        rt_ex.primary_detection_channel = 'customer_reviews',
        rt_ex.secondary_detection_channels = [],
        rt_ex.advertising_implications = 'Win-back messaging. Show improvement. Second chance positioning.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: GUILT AND OBLIGATION (2 types)
    # ==========================================================================
    """
    MERGE (rt_captor:RelationshipType {type_id: 'accountability_captor'})
    SET rt_captor.type_name = 'Accountability Captor',
        rt_captor.category = 'guilt_obligation',
        rt_captor.definition = 'Guilt-driven engagement through streaks, notifications, sunk cost. The Duolingo Owl effect.',
        rt_captor.relational_model = 'negative_communal',
        rt_captor.typical_strength_range = [3, 4],
        rt_captor.vulnerability_to_dissolution = 'moderate',
        rt_captor.primary_detection_channel = 'customer_reviews',
        rt_captor.secondary_detection_channels = ['social_signals'],
        rt_captor.advertising_implications = 'Use guilt gently. Progress visualization. Offer compassionate recovery.',
        rt_captor.academic_source = 'Guilt economy pattern (2023)'
    """,
    """
    MERGE (rt_subscription:RelationshipType {type_id: 'subscription_conscience'})
    SET rt_subscription.type_name = 'Subscription Conscience',
        rt_subscription.category = 'guilt_obligation',
        rt_subscription.definition = 'Guilt about unused subscriptions. Necessary evil relationship.',
        rt_subscription.relational_model = 'market_pricing',
        rt_subscription.typical_strength_range = [2, 3],
        rt_subscription.vulnerability_to_dissolution = 'high',
        rt_subscription.primary_detection_channel = 'customer_reviews',
        rt_subscription.secondary_detection_channels = ['self_expression'],
        rt_subscription.advertising_implications = 'Value reminders. Flexible commitment. Guilt relief.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: RITUAL AND TEMPORAL (2 types)
    # ==========================================================================
    """
    MERGE (rt_sacred:RelationshipType {type_id: 'sacred_practice'})
    SET rt_sacred.type_name = 'Sacred Practice',
        rt_sacred.category = 'ritual_temporal',
        rt_sacred.definition = 'Brand embedded in ritualized behavior with symbolic meaning. Morning routine, skincare sanctuary.',
        rt_sacred.relational_model = 'communal_sharing',
        rt_sacred.typical_strength_range = [4, 5],
        rt_sacred.vulnerability_to_dissolution = 'low',
        rt_sacred.primary_detection_channel = 'customer_reviews',
        rt_sacred.secondary_detection_channels = ['self_expression'],
        rt_sacred.advertising_implications = 'Enhance the ceremony. Sensory immersion. NEVER disrupt the ritual.',
        rt_sacred.academic_source = 'Liu, Zhu & Wang (2022) Brand Ritual'
    """,
    """
    MERGE (rt_temporal:RelationshipType {type_id: 'temporal_marker'})
    SET rt_temporal.type_name = 'Temporal Marker',
        rt_temporal.category = 'ritual_temporal',
        rt_temporal.definition = 'Brand commemorates life stages, marks anniversaries, embedded in personal chronology.',
        rt_temporal.relational_model = 'communal_sharing',
        rt_temporal.typical_strength_range = [4, 5],
        rt_temporal.vulnerability_to_dissolution = 'very_low',
        rt_temporal.primary_detection_channel = 'customer_reviews',
        rt_temporal.secondary_detection_channels = ['social_signals'],
        rt_temporal.advertising_implications = 'Milestone celebration. Memory anchoring. Legacy building.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: GRIEF AND LOSS (2 types)
    # ==========================================================================
    """
    MERGE (rt_mourning:RelationshipType {type_id: 'mourning_bond'})
    SET rt_mourning.type_name = 'Mourning Bond',
        rt_mourning.category = 'grief_loss',
        rt_mourning.definition = 'Genuine grief over discontinued products. All classic grief stages apply.',
        rt_mourning.relational_model = 'communal_sharing',
        rt_mourning.typical_strength_range = [4, 5],
        rt_mourning.vulnerability_to_dissolution = 'low',
        rt_mourning.primary_detection_channel = 'customer_reviews',
        rt_mourning.secondary_detection_channels = ['social_signals'],
        rt_mourning.advertising_implications = 'Show empathy. Acknowledge grief is valid. Bring-back campaigns.',
        rt_mourning.academic_source = 'Khatoon & Rehman (2025) Brand Grief Scale'
    """,
    """
    MERGE (rt_formula:RelationshipType {type_id: 'formula_betrayal'})
    SET rt_formula.type_name = 'Formula Betrayal',
        rt_formula.category = 'grief_loss',
        rt_formula.definition = 'Anger at changed formulas/recipes. Worse than discontinuation - felt as betrayal.',
        rt_formula.relational_model = 'negative_communal',
        rt_formula.typical_strength_range = [4, 5],
        rt_formula.vulnerability_to_dissolution = 'moderate',
        rt_formula.primary_detection_channel = 'customer_reviews',
        rt_formula.secondary_detection_channels = ['social_signals'],
        rt_formula.advertising_implications = 'Transparency. Classic version return. Consumer input promise.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: SALVATION AND REDEMPTION (2 types)
    # ==========================================================================
    """
    MERGE (rt_liferaft:RelationshipType {type_id: 'life_raft'})
    SET rt_liferaft.type_name = 'Life Raft',
        rt_liferaft.category = 'salvation_redemption',
        rt_liferaft.definition = 'Brand rescued consumer during crisis (breakup, illness, pandemic). Profound emotional debt.',
        rt_liferaft.relational_model = 'communal_sharing',
        rt_liferaft.typical_strength_range = [5, 5],
        rt_liferaft.vulnerability_to_dissolution = 'very_low',
        rt_liferaft.primary_detection_channel = 'customer_reviews',
        rt_liferaft.secondary_detection_channels = ['self_expression', 'social_signals'],
        rt_liferaft.advertising_implications = 'Continue supportive presence. Community messaging. Testimonial goldmine.'
    """,
    """
    MERGE (rt_transform:RelationshipType {type_id: 'transformation_agent'})
    SET rt_transform.type_name = 'Transformation Agent',
        rt_transform.category = 'salvation_redemption',
        rt_transform.definition = 'Brand fundamentally changed who the consumer is. Before/after identity shift.',
        rt_transform.relational_model = 'communal_sharing',
        rt_transform.typical_strength_range = [5, 5],
        rt_transform.vulnerability_to_dissolution = 'very_low',
        rt_transform.primary_detection_channel = 'customer_reviews',
        rt_transform.secondary_detection_channels = ['social_signals'],
        rt_transform.advertising_implications = 'Celebrate transformation. Before/after stories. Ambassador elevation.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: COGNITIVE DEPENDENCY (2 types)
    # ==========================================================================
    """
    MERGE (rt_brain:RelationshipType {type_id: 'second_brain'})
    SET rt_brain.type_name = 'Second Brain',
        rt_brain.category = 'cognitive_dependency',
        rt_brain.definition = 'Productivity tools as extensions of the mind. Cannot think or function without.',
        rt_brain.relational_model = 'communal_sharing',
        rt_brain.typical_strength_range = [5, 5],
        rt_brain.vulnerability_to_dissolution = 'very_low',
        rt_brain.primary_detection_channel = 'customer_reviews',
        rt_brain.secondary_detection_channels = ['self_expression'],
        rt_brain.advertising_implications = 'Emphasize reliability. NEVER threaten data. Cognitive load reduction.'
    """,
    """
    MERGE (rt_lockin:RelationshipType {type_id: 'platform_lock_in'})
    SET rt_lockin.type_name = 'Platform Lock-in',
        rt_lockin.category = 'cognitive_dependency',
        rt_lockin.definition = 'Rational ecosystem commitment. Chose knowing it constrains future choices.',
        rt_lockin.relational_model = 'market_pricing',
        rt_lockin.typical_strength_range = [3, 4],
        rt_lockin.vulnerability_to_dissolution = 'low',
        rt_lockin.primary_detection_channel = 'customer_reviews',
        rt_lockin.secondary_detection_channels = [],
        rt_lockin.advertising_implications = 'Justify investment. Show ecosystem value. Make lock-in feel smart.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: TRIBAL AND IDENTITY (4 types)
    # ==========================================================================
    """
    MERGE (rt_signal:RelationshipType {type_id: 'tribal_signal'})
    SET rt_signal.type_name = 'Tribal Signal',
        rt_signal.category = 'tribal_identity',
        rt_signal.definition = 'Recognition protocols between strangers. The Jeep Wave, Tesla Smile, Ducking.',
        rt_signal.relational_model = 'communal_sharing',
        rt_signal.typical_strength_range = [4, 5],
        rt_signal.vulnerability_to_dissolution = 'very_low',
        rt_signal.primary_detection_channel = 'social_signals',
        rt_signal.secondary_detection_channels = ['customer_reviews'],
        rt_signal.advertising_implications = 'Celebrate rituals. Honor protocols. Insider language.'
    """,
    """
    MERGE (rt_inherited:RelationshipType {type_id: 'inherited_legacy'})
    SET rt_inherited.type_name = 'Inherited Legacy',
        rt_inherited.category = 'tribal_identity',
        rt_inherited.definition = 'Generational brand loyalty passed through family. Honoring ancestors.',
        rt_inherited.relational_model = 'communal_sharing',
        rt_inherited.typical_strength_range = [4, 5],
        rt_inherited.vulnerability_to_dissolution = 'very_low',
        rt_inherited.primary_detection_channel = 'customer_reviews',
        rt_inherited.secondary_detection_channels = ['self_expression'],
        rt_inherited.advertising_implications = 'Heritage honor. Generational story. Family tradition.'
    """,
    """
    MERGE (rt_negation:RelationshipType {type_id: 'identity_negation'})
    SET rt_negation.type_name = 'Identity Negation',
        rt_negation.category = 'tribal_identity',
        rt_negation.definition = 'Using brand avoidance to define who you are NOT. Anti-consumption identity.',
        rt_negation.relational_model = 'negative_communal',
        rt_negation.typical_strength_range = [4, 5],
        rt_negation.vulnerability_to_dissolution = 'low',
        rt_negation.primary_detection_channel = 'social_signals',
        rt_negation.secondary_detection_channels = ['self_expression'],
        rt_negation.advertising_implications = 'Respect values. Anti-mainstream positioning. Authenticity.',
        rt_negation.academic_source = 'Undesired self construct research'
    """,
    """
    MERGE (rt_workspace:RelationshipType {type_id: 'workspace_culture'})
    SET rt_workspace.type_name = 'Workspace Culture',
        rt_workspace.category = 'tribal_identity',
        rt_workspace.definition = 'Teams/organizations define culture by shared tools. We run on Slack.',
        rt_workspace.relational_model = 'equality_matching',
        rt_workspace.typical_strength_range = [3, 4],
        rt_workspace.vulnerability_to_dissolution = 'moderate',
        rt_workspace.primary_detection_channel = 'customer_reviews',
        rt_workspace.secondary_detection_channels = ['social_signals'],
        rt_workspace.advertising_implications = 'Team productivity. Collaboration enhancement. Shared success.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: COLLECTOR AND QUEST (2 types)
    # ==========================================================================
    """
    MERGE (rt_grail:RelationshipType {type_id: 'grail_quest'})
    SET rt_grail.type_name = 'Grail Quest',
        rt_grail.category = 'collector_quest',
        rt_grail.definition = 'Pursuit of elusive holy grail product. The search itself is the relationship.',
        rt_grail.relational_model = 'market_pricing',
        rt_grail.typical_strength_range = [4, 5],
        rt_grail.vulnerability_to_dissolution = 'moderate',
        rt_grail.primary_detection_channel = 'social_signals',
        rt_grail.secondary_detection_channels = ['customer_reviews'],
        rt_grail.advertising_implications = 'Honor scarcity. Celebrate attainment. Collector community.'
    """,
    """
    MERGE (rt_completion:RelationshipType {type_id: 'completion_seeker'})
    SET rt_completion.type_name = 'Completion Seeker',
        rt_completion.category = 'collector_quest',
        rt_completion.definition = 'Project Pan phenomenon. Relationship through finishing products.',
        rt_completion.relational_model = 'equality_matching',
        rt_completion.typical_strength_range = [3, 4],
        rt_completion.vulnerability_to_dissolution = 'moderate',
        rt_completion.primary_detection_channel = 'social_signals',
        rt_completion.secondary_detection_channels = ['customer_reviews'],
        rt_completion.advertising_implications = 'Progress tracking. Completion celebration. Mindful consumption.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: TRUST AND INTIMACY (2 types)
    # ==========================================================================
    """
    MERGE (rt_financial:RelationshipType {type_id: 'financial_intimate'})
    SET rt_financial.type_name = 'Financial Intimate',
        rt_financial.category = 'trust_intimacy',
        rt_financial.definition = 'Apps with access to sensitive financial data. Deep vulnerability trust.',
        rt_financial.relational_model = 'communal_sharing',
        rt_financial.typical_strength_range = [4, 5],
        rt_financial.vulnerability_to_dissolution = 'low',
        rt_financial.primary_detection_channel = 'customer_reviews',
        rt_financial.secondary_detection_channels = [],
        rt_financial.advertising_implications = 'Security assurance. Privacy protection. NEVER be cavalier about data.'
    """,
    """
    MERGE (rt_therapist:RelationshipType {type_id: 'therapist_provider'})
    SET rt_therapist.type_name = 'Therapist Provider',
        rt_therapist.category = 'trust_intimacy',
        rt_therapist.definition = 'Service providers (barber, stylist) who function as emotional confidants.',
        rt_therapist.relational_model = 'communal_sharing',
        rt_therapist.typical_strength_range = [4, 5],
        rt_therapist.vulnerability_to_dissolution = 'very_low',
        rt_therapist.primary_detection_channel = 'customer_reviews',
        rt_therapist.secondary_detection_channels = ['self_expression'],
        rt_therapist.advertising_implications = 'Emotional support. Continuity. Personal connection.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: INSIDER AND COMPLICITY (2 types)
    # ==========================================================================
    """
    MERGE (rt_insider:RelationshipType {type_id: 'insider_compact'})
    SET rt_insider.type_name = 'Insider Compact',
        rt_insider.category = 'insider_complicity',
        rt_insider.definition = 'IYKYK gatekeeping dynamics. Exclusive knowledge relationship.',
        rt_insider.relational_model = 'equality_matching',
        rt_insider.typical_strength_range = [4, 5],
        rt_insider.vulnerability_to_dissolution = 'low',
        rt_insider.primary_detection_channel = 'social_signals',
        rt_insider.secondary_detection_channels = ['customer_reviews'],
        rt_insider.advertising_implications = 'Insider language. Respect earned access. Dont make too accessible.'
    """,
    """
    MERGE (rt_cocreator:RelationshipType {type_id: 'co_creator'})
    SET rt_cocreator.type_name = 'Co-Creator',
        rt_cocreator.category = 'insider_complicity',
        rt_cocreator.definition = 'Active partner in brand development. Glossier model.',
        rt_cocreator.relational_model = 'communal_sharing',
        rt_cocreator.typical_strength_range = [4, 5],
        rt_cocreator.vulnerability_to_dissolution = 'low',
        rt_cocreator.primary_detection_channel = 'social_signals',
        rt_cocreator.secondary_detection_channels = ['customer_reviews'],
        rt_cocreator.advertising_implications = 'Co-creation invitation. Implement feedback. Community ownership.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: VALUES AND PERMISSION (3 types)
    # ==========================================================================
    """
    MERGE (rt_ethical:RelationshipType {type_id: 'ethical_validator'})
    SET rt_ethical.type_name = 'Ethical Validator',
        rt_ethical.category = 'values_permission',
        rt_ethical.definition = 'Brand provides moral permission. Guilt-free purchase.',
        rt_ethical.relational_model = 'communal_sharing',
        rt_ethical.typical_strength_range = [3, 4],
        rt_ethical.vulnerability_to_dissolution = 'moderate',
        rt_ethical.primary_detection_channel = 'customer_reviews',
        rt_ethical.secondary_detection_channels = ['social_signals'],
        rt_ethical.advertising_implications = 'Values reflection. Impact transparency. Conscious consumption.'
    """,
    """
    MERGE (rt_arbiter:RelationshipType {type_id: 'status_arbiter'})
    SET rt_arbiter.type_name = 'Status Arbiter',
        rt_arbiter.category = 'values_permission',
        rt_arbiter.definition = 'Brand provides access to exclusive social spheres. Gatekeeping entry.',
        rt_arbiter.relational_model = 'authority_ranking',
        rt_arbiter.typical_strength_range = [4, 5],
        rt_arbiter.vulnerability_to_dissolution = 'low',
        rt_arbiter.primary_detection_channel = 'social_signals',
        rt_arbiter.secondary_detection_channels = ['customer_reviews'],
        rt_arbiter.advertising_implications = 'Access provision. Tier progression. Exclusivity gateway.'
    """,
    """
    MERGE (rt_competence:RelationshipType {type_id: 'competence_validator'})
    SET rt_competence.type_name = 'Competence Validator',
        rt_competence.category = 'values_permission',
        rt_competence.definition = 'Brand confirms consumer made the smart choice. BIFL community.',
        rt_competence.relational_model = 'market_pricing',
        rt_competence.typical_strength_range = [3, 4],
        rt_competence.vulnerability_to_dissolution = 'moderate',
        rt_competence.primary_detection_channel = 'customer_reviews',
        rt_competence.secondary_detection_channels = [],
        rt_competence.advertising_implications = 'Smart choice confirmation. Research validation. Quality proof.'
    """,
    # ==========================================================================
    # FOURNIER EXTENSION: META AND IRONIC (1 type)
    # ==========================================================================
    """
    MERGE (rt_ironic:RelationshipType {type_id: 'ironic_aware'})
    SET rt_ironic.type_name = 'Ironic Aware',
        rt_ironic.category = 'meta_ironic',
        rt_ironic.definition = 'Critical distance while still engaging. r/HailCorporate awareness.',
        rt_ironic.relational_model = 'market_pricing',
        rt_ironic.typical_strength_range = [2, 3],
        rt_ironic.vulnerability_to_dissolution = 'high',
        rt_ironic.primary_detection_channel = 'social_signals',
        rt_ironic.secondary_detection_channels = ['self_expression'],
        rt_ironic.advertising_implications = 'Self-aware transparency. Meta-humor. Authentic positioning.'
    """,
]

# Engagement Strategies
ENGAGEMENT_STRATEGY_QUERIES: List[str] = [
    """
    MERGE (es1:EngagementStrategy {strategy_id: 'identity_affirmation'})
    SET es1.strategy_name = 'Identity Affirmation',
        es1.target_relationship_types = ['self_identity_core'],
        es1.messaging_tone = 'affirming, heritage-focused, celebratory',
        es1.content_types = ['heritage content', 'community stories', 'milestone celebrations'],
        es1.call_to_action_style = 'soft_belonging',
        es1.avoid_patterns = ['trying to change them', 'aggressive CTAs', 'questioning identity']
    """,
    """
    MERGE (es2:EngagementStrategy {strategy_id: 'tribal_belonging'})
    SET es2.strategy_name = 'Tribal Belonging',
        es2.target_relationship_types = ['tribal_badge'],
        es2.messaging_tone = 'inclusive to tribe, exclusive to outsiders',
        es2.content_types = ['community events', 'member spotlights', 'insider content'],
        es2.call_to_action_style = 'join_community',
        es2.avoid_patterns = ['mass market appeal', 'generic messaging']
    """,
    """
    MERGE (es3:EngagementStrategy {strategy_id: 'status_recognition'})
    SET es3.strategy_name = 'Status Recognition',
        es3.target_relationship_types = ['status_marker'],
        es3.messaging_tone = 'exclusive, premium, aspirational',
        es3.content_types = ['luxury imagery', 'celebrity associations', 'exclusivity cues'],
        es3.call_to_action_style = 'elevate',
        es3.avoid_patterns = ['discount messaging', 'mass market imagery']
    """,
    """
    MERGE (es4:EngagementStrategy {strategy_id: 'relationship_deepening'})
    SET es4.strategy_name = 'Relationship Deepening',
        es4.target_relationship_types = ['committed_partnership'],
        es4.messaging_tone = 'warm, appreciative, partnership-oriented',
        es4.content_types = ['appreciation messages', 'exclusive offers', 'journey milestones'],
        es4.call_to_action_style = 'continue_together',
        es4.avoid_patterns = ['acquisition messaging', 'hard sells']
    """,
    """
    MERGE (es5:EngagementStrategy {strategy_id: 'functional_value'})
    SET es5.strategy_name = 'Functional Value',
        es5.target_relationship_types = ['reliable_tool'],
        es5.messaging_tone = 'clear, confident, no-nonsense',
        es5.content_types = ['product demonstrations', 'comparison charts', 'specifications'],
        es5.call_to_action_style = 'try_it',
        es5.avoid_patterns = ['emotional appeals', 'identity messaging']
    """,
    """
    MERGE (es6:EngagementStrategy {strategy_id: 'expertise_guidance'})
    SET es6.strategy_name = 'Expertise Guidance',
        es6.target_relationship_types = ['mentor'],
        es6.messaging_tone = 'expert, educational, helpful',
        es6.content_types = ['how-to content', 'expert tips', 'educational series'],
        es6.call_to_action_style = 'learn_more',
        es6.avoid_patterns = ['salesy pitches', 'condescending tone']
    """,
    """
    MERGE (es7:EngagementStrategy {strategy_id: 'comfort_provision'})
    SET es7.strategy_name = 'Comfort Provision',
        es7.target_relationship_types = ['comfort_companion'],
        es7.messaging_tone = 'warm, soothing, gentle',
        es7.content_types = ['relaxation moments', 'self-care content', 'sensory imagery'],
        es7.call_to_action_style = 'treat_yourself',
        es7.avoid_patterns = ['urgent CTAs', 'anxiety-inducing content']
    """,
]

# Link strategies to relationship types
LINKING_QUERIES: List[str] = [
    """
    MATCH (es:EngagementStrategy), (rt:RelationshipType)
    WHERE rt.type_id IN es.target_relationship_types
    MERGE (rt)-[:SUGGESTS]->(es)
    """,
]


async def initialize_relationship_schema(driver) -> None:
    """
    Initialize the full Neo4j schema for consumer-brand relationships.
    
    Args:
        driver: Neo4j async driver instance
    """
    async with driver.session() as session:
        # 1. Create constraints
        logger.info("Creating relationship schema constraints...")
        for query in CONSTRAINT_QUERIES:
            try:
                await session.run(query)
            except Exception as e:
                logger.debug(f"Constraint may already exist: {e}")
        
        # 2. Create indexes
        logger.info("Creating relationship schema indexes...")
        for query in INDEX_QUERIES:
            try:
                await session.run(query)
            except Exception as e:
                logger.debug(f"Index may already exist: {e}")
        
        # 3. Create observation channels
        logger.info("Creating observation channel nodes...")
        for query in CHANNEL_QUERIES:
            await session.run(query)
        
        # 4. Create relationship types
        logger.info("Creating relationship type nodes...")
        for query in RELATIONSHIP_TYPE_QUERIES:
            await session.run(query)
        
        # 5. Create engagement strategies
        logger.info("Creating engagement strategy nodes...")
        for query in ENGAGEMENT_STRATEGY_QUERIES:
            await session.run(query)
        
        # 6. Create links
        logger.info("Creating relationship links...")
        for query in LINKING_QUERIES:
            await session.run(query)
        
        logger.info("Consumer-brand relationship schema initialized successfully")


def get_schema_queries() -> List[str]:
    """Get all schema queries as a list for manual execution."""
    return (
        CONSTRAINT_QUERIES +
        INDEX_QUERIES +
        CHANNEL_QUERIES +
        RELATIONSHIP_TYPE_QUERIES +
        ENGAGEMENT_STRATEGY_QUERIES +
        LINKING_QUERIES
    )
