# =============================================================================
# ADAM Consumer Psychology Research Seeder
# Location: adam/behavioral_analytics/knowledge/consumer_psychology_seeder.py
# =============================================================================

"""
CONSUMER PSYCHOLOGY RESEARCH SEEDER

Seeds the system with 25 years (1999-2025) of peer-reviewed consumer psychology
and advertising effectiveness research.

Research Domains:
1. Personality Traits (Big Five, Dark Triad, Self-monitoring)
2. Psychological States (Mood, Regulatory Focus, Construal Level, Emotions)
3. Individual Differences (Need for Cognition, Maximizing, Impulsivity)
4. Demographics & Culture (Generational, Gender, Cultural Values)
5. Visual Design (Color, White Space, Models, Metaphors)
6. Language & Narrative (Transportation, Fear, Humor, Framing)
7. Media Platforms (TV, Influencers, Native Ads, Video)
8. Moderators (Involvement, Celebrity Fit, Dual Mediation)

Key Meta-Analyses:
- Eisend & Tarrahi (2016): r=.20 overall advertising effectiveness
- Tannenbaum et al. (2015): d=0.29 fear appeals
- Van Laer et al. (2014): r=.47 narrative transportation
- Knoll & Matthes (2017): d=0.90/-0.96 celebrity fit
"""

from typing import List, Dict, Optional
from datetime import datetime
import logging

from adam.behavioral_analytics.models.advertising_knowledge import (
    AdvertisingKnowledge,
    AdvertisingInteraction,
    AdvertisingResearchSource,
    PredictorCategory,
    AdElement,
    OutcomeMetric,
    EffectType,
    RobustnessTier,
    InteractionType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PART I: PERSONALITY TRAITS
# =============================================================================

def create_personality_trait_knowledge() -> List[AdvertisingKnowledge]:
    """
    Create Big Five and extended personality → advertising response knowledge.
    
    Source: 2024 meta-analysis (15 studies, 308 correlations)
    Key finding: Agreeableness, Extraversion, and Openness produce significant
    positive effects on overall advertising response.
    """
    knowledge = []
    
    # Extraversion → Social Brand Preference
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PERSONALITY,
        predictor_name="extraversion",
        predictor_value="high",
        predictor_description="High extraversion from Big Five personality",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="social_appeal",
        element_description="Social, group-oriented, excitement-based appeals",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Preference for social brands and social networking adoption",
        effect_size=0.35,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=48,
        total_sample_size=15000,
        sources=[
            AdvertisingResearchSource(
                source_id="meta_2024_personality",
                authors="International Journal of Advertising",
                year=2024,
                journal="International Journal of Advertising",
                title="Personality and advertising response meta-analysis",
                study_type="meta-analysis",
                num_studies=15,
                num_effect_sizes=308,
                key_finding="Extraversion strongest predictor for social networking adoption",
            ),
        ],
        implementation_notes="Effect strengthens for unfamiliar brands. Use social proof and group imagery.",
        boundary_conditions=["Brand familiarity moderates: stronger for unfamiliar brands"],
        related_mechanisms=["social_proof", "identity_construction"],
    ))
    
    # Openness → Innovation Adoption
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PERSONALITY,
        predictor_name="openness",
        predictor_value="high",
        predictor_description="High openness to experience from Big Five",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="novelty_appeal",
        element_description="Novel, innovative, creative product messaging",
        outcome_metric=OutcomeMetric.PURCHASE_INTENT,
        outcome_direction="positive",
        outcome_description="Innovation adoption and brand affect leading to loyalty",
        effect_size=0.30,
        effect_type=EffectType.BETA,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=15,
        sources=[
            AdvertisingResearchSource(
                source_id="openness_innovation",
                authors="Multiple studies",
                year=2024,
                title="Openness and innovation adoption",
                key_finding="Significant positive β for innovation adoption",
            ),
        ],
        implementation_notes="Stronger in individualist cultures. Emphasize uniqueness and creativity.",
        boundary_conditions=["Culture moderates: individualist cultures show stronger effects"],
        related_mechanisms=["construal_level", "identity_construction"],
    ))
    
    # Conscientiousness → Brand Loyalty via Trust
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PERSONALITY,
        predictor_name="conscientiousness",
        predictor_value="high",
        predictor_description="High conscientiousness from Big Five",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="trust_quality_appeal",
        element_description="Reliability, quality, trustworthiness messaging",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Brand loyalty via trust pathway, premium willingness",
        effect_size=0.28,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=15,
        sources=[
            AdvertisingResearchSource(
                source_id="conscientiousness_loyalty",
                authors="Meta-analysis",
                year=2024,
                title="Conscientiousness and brand loyalty",
                key_finding="Positive via trust mediation",
            ),
        ],
        implementation_notes="Also protective against compulsive buying. Trust mediation is key.",
        related_mechanisms=["regulatory_focus"],
    ))
    
    # Neuroticism → Risk-Averse Messaging
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PERSONALITY,
        predictor_name="neuroticism",
        predictor_value="high",
        predictor_description="High neuroticism from Big Five",
        ad_element=AdElement.MESSAGE_FRAME,
        element_specification="safety_security_frame",
        element_description="Safety, security, risk-reduction messaging",
        outcome_metric=OutcomeMetric.PURCHASE_INTENT,
        outcome_direction="positive",
        outcome_description="Risk-averse purchasing behavior, safety messaging effective",
        effect_size=0.25,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=8,
        sources=[
            AdvertisingResearchSource(
                source_id="neuroticism_safety",
                authors="Various",
                year=2023,
                title="Neuroticism and consumer behavior",
                key_finding="Risk-averse purchasing, safety messaging effective",
            ),
        ],
        implementation_notes="Also predicts compulsive/panic buying. Self-esteem mediates.",
        boundary_conditions=["Self-esteem mediates the effect"],
        related_mechanisms=["regulatory_focus", "evolutionary_adaptations"],
    ))
    
    # Agreeableness → Prosocial Brand Response
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PERSONALITY,
        predictor_name="agreeableness",
        predictor_value="high",
        predictor_description="High agreeableness from Big Five",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="prosocial_appeal",
        element_description="CSR, community, prosocial brand messaging",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Positive response to prosocial brands, authority appeal susceptibility",
        effect_size=0.32,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=15,
        sources=[
            AdvertisingResearchSource(
                source_id="agreeableness_prosocial",
                authors="Meta-analysis",
                year=2024,
                title="Agreeableness and advertising response",
                key_finding="Significant positive effect on overall ad response",
            ),
        ],
        implementation_notes="Effects emerge primarily through value-expressive appeals, not utilitarian.",
        boundary_conditions=["Effects for value-expressive appeals only, not utilitarian"],
        related_mechanisms=["mimetic_desire", "social_proof"],
    ))
    
    # Need for Cognition × Argument Quality
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.INDIVIDUAL_DIFFERENCE,
        predictor_name="need_for_cognition",
        predictor_value="high",
        predictor_description="High need for cognition (Cacioppo & Petty)",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="strong_arguments",
        element_description="Information-rich, strong argument quality messaging",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Strong argument quality effects on attitudes",
        effect_size=0.65,
        effect_type=EffectType.CORRELATION,
        p_value=0.0001,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=10,
        sources=[
            AdvertisingResearchSource(
                source_id="haugtvedt1992",
                authors="Haugtvedt, Petty & Cacioppo",
                year=1992,
                journal="Journal of Consumer Psychology",
                title="Need for cognition and advertising",
                key_finding="F(1, 40) = 41.72, p < .0001 for high NFC",
            ),
        ],
        implementation_notes="High NFC: attitudes based on product attributes. Low NFC: peripheral cues.",
        boundary_conditions=["Interaction: F(1, 93) = 12.50, p < .001"],
        related_mechanisms=["construal_level", "attention_dynamics"],
    ))
    
    # Self-Monitoring → Image vs Quality Appeals
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.INDIVIDUAL_DIFFERENCE,
        predictor_name="self_monitoring",
        predictor_value="high",
        predictor_description="High self-monitoring (Snyder, 1974)",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="image_status_appeal",
        element_description="Image-based, status signaling, conspicuous luxury",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Preference for image appeals over quality appeals",
        effect_size=0.40,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=12,
        sources=[
            AdvertisingResearchSource(
                source_id="snyder_selfmon",
                authors="Snyder",
                year=1974,
                title="Self-monitoring scale",
                key_finding="High SM → image appeals; Low SM → quality appeals",
            ),
        ],
        implementation_notes="Low self-monitors prefer quality, functional attributes, 'quiet luxury'.",
        related_mechanisms=["identity_construction", "mimetic_desire"],
    ))
    
    # Need for Uniqueness
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.INDIVIDUAL_DIFFERENCE,
        predictor_name="need_for_uniqueness",
        predictor_value="high",
        predictor_description="High need for uniqueness (Tian, Bearden & Hunter, 2001)",
        ad_element=AdElement.CREATIVE_EXECUTION,
        element_specification="unique_limited_design",
        element_description="Unique designs, limited editions, mass customization",
        outcome_metric=OutcomeMetric.PURCHASE_INTENT,
        outcome_direction="positive",
        outcome_description="Preference for unique, early adoption, luxury brands",
        effect_size=0.38,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=8,
        sources=[
            AdvertisingResearchSource(
                source_id="tian2001",
                authors="Tian, Bearden & Hunter",
                year=2001,
                journal="Journal of Consumer Research",
                title="Need for uniqueness scale",
                key_finding="Three dimensions: Creative, Unpopular, Avoidance of Similarity",
            ),
        ],
        implementation_notes="Operates differently in collectivist cultures. Emphasize scarcity.",
        boundary_conditions=["Cultural moderation in collectivist contexts"],
        related_mechanisms=["evolutionary_adaptations", "identity_construction"],
    ))
    
    return knowledge


# =============================================================================
# PART II: PSYCHOLOGICAL STATES
# =============================================================================

def create_psychological_state_knowledge() -> List[AdvertisingKnowledge]:
    """
    Create psychological state → advertising response knowledge.
    
    Covers: Mood, Regulatory Focus, Construal Level, Discrete Emotions, Scarcity
    """
    knowledge = []
    
    # Regulatory Focus: Promotion × Gain Frame
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="regulatory_focus",
        predictor_value="promotion",
        predictor_description="Promotion focus orientation (Higgins, 1997)",
        ad_element=AdElement.MESSAGE_FRAME,
        element_specification="gain_frame",
        element_description="Gain-framed messaging ('Get energized', achievement)",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Increased persuasion through regulatory fit",
        effect_size=0.35,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=20,
        sources=[
            AdvertisingResearchSource(
                source_id="lee_aaker2004",
                authors="Lee & Aaker",
                year=2004,
                title="Regulatory fit and persuasion",
                key_finding="Matching message to focus increases persuasion",
            ),
        ],
        implementation_notes="Promotion: comfort, advancement, eager strategies. Larger consideration sets.",
        related_mechanisms=["regulatory_focus"],
    ))
    
    # Regulatory Focus: Prevention × Loss Frame
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="regulatory_focus",
        predictor_value="prevention",
        predictor_description="Prevention focus orientation (Higgins, 1997)",
        ad_element=AdElement.MESSAGE_FRAME,
        element_specification="loss_frame",
        element_description="Loss-framed messaging ('Don't miss out', security)",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Increased persuasion through regulatory fit",
        effect_size=0.35,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=20,
        sources=[
            AdvertisingResearchSource(
                source_id="higgins1998",
                authors="Higgins",
                year=1998,
                title="Regulatory focus theory",
                key_finding="Prevention: safety, reliability, vigilant strategies",
            ),
        ],
        implementation_notes="Prevention: cautious, systematic, narrower choices. Discourages charitable giving with sadness.",
        boundary_conditions=["Prevention discourages charitable giving with sadness appeals"],
        related_mechanisms=["regulatory_focus"],
    ))
    
    # Construal Level: High × Abstract
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="construal_level",
        predictor_value="high",
        predictor_description="High/abstract construal level (Trope & Liberman)",
        ad_element=AdElement.MESSAGE_FRAME,
        element_specification="abstract_why_message",
        element_description="Abstract 'why' messages emphasizing desirability",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Matching effect: abstract pairs with psychological distance",
        effect_size=0.30,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=111,
        sources=[
            AdvertisingResearchSource(
                source_id="clt_review2024",
                authors="Systematic review",
                year=2024,
                title="Construal Level Theory systematic review",
                num_studies=111,
                key_finding="Matching effect validated across 111 studies",
            ),
        ],
        implementation_notes="For distant-future decisions, use abstract appeals emphasizing desirability.",
        related_mechanisms=["construal_level", "temporal_construal"],
    ))
    
    # Construal Level: Low × Concrete
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="construal_level",
        predictor_value="low",
        predictor_description="Low/concrete construal level",
        ad_element=AdElement.MESSAGE_FRAME,
        element_specification="concrete_how_message",
        element_description="Concrete 'how' messages emphasizing feasibility",
        outcome_metric=OutcomeMetric.CONVERSION,
        outcome_direction="positive",
        outcome_description="For immediate decisions, concrete appeals work better",
        effect_size=0.30,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=111,
        sources=[
            AdvertisingResearchSource(
                source_id="clt_visual2022",
                authors="2022 study",
                year=2022,
                title="CLT and visual distance",
                key_finding="Visually proximate images increase CVR at conversion",
            ),
        ],
        implementation_notes="Visually distant images increase CTR early; proximate increase CVR at conversion.",
        related_mechanisms=["construal_level", "temporal_construal"],
    ))
    
    # Positive Mood → Reduced Elaboration
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="mood",
        predictor_value="positive",
        predictor_description="Positive mood state (Schwarz & Clore)",
        ad_element=AdElement.CREATIVE_EXECUTION,
        element_specification="heuristic_cues",
        element_description="Peripheral cues, less argument-dependent execution",
        outcome_metric=OutcomeMetric.AD_ATTITUDE,
        outcome_direction="positive",
        outcome_description="More favorable brand attitudes through reduced cognitive elaboration",
        effect_size=0.28,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=15,
        sources=[
            AdvertisingResearchSource(
                source_id="batra1990",
                authors="Batra & Stayman",
                year=1990,
                journal="Journal of Consumer Research",
                title="Mood and advertising",
                key_finding="Positive mood → heuristic processing",
            ),
        ],
        implementation_notes="Effect eliminated when consumers identify mood source. Stronger for low NFC.",
        boundary_conditions=["Eliminated with mood discounting", "Stronger for low NFC", "Weak arguments"],
        related_mechanisms=["automatic_evaluation"],
    ))
    
    # Nostalgia → Brand Attitudes
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="nostalgia",
        predictor_value="personal",
        predictor_description="Personal nostalgia (yearning for lived past)",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="nostalgia_appeal",
        element_description="Nostalgic imagery and messaging",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Nostalgia → brand love pathway",
        effect_size=0.35,
        effect_type=EffectType.BETA,
        confidence_interval_lower=0.30,
        confidence_interval_upper=0.40,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=8,
        sources=[
            AdvertisingResearchSource(
                source_id="nostalgia_uk",
                authors="UK study",
                year=2023,
                title="Nostalgia and brand love",
                key_finding="β ≈ 0.30-0.40 for nostalgia → brand love",
            ),
        ],
        implementation_notes="Personal nostalgia effective in Western cultures; historical in collectivist.",
        boundary_conditions=["Effect disappears when consumers anticipate solo consumption"],
        related_mechanisms=["identity_construction", "temporal_construal"],
    ))
    
    # Scarcity Mindset
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="scarcity_mindset",
        predictor_value="active",
        predictor_description="Scarcity mindset activated",
        ad_element=AdElement.CREATIVE_EXECUTION,
        element_specification="favorite_emphasis",
        element_description="Emphasis on favorites, reduced options",
        outcome_metric=OutcomeMetric.PURCHASE_INTENT,
        outcome_direction="positive",
        outcome_description="Scarcity polarizes preferences toward favorites",
        effect_size=1.23,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_3_SINGLE_STUDY,
        study_count=1,
        total_sample_size=40,
        sources=[
            AdvertisingResearchSource(
                source_id="huijsmans2019",
                authors="Huijsmans et al.",
                year=2019,
                journal="PNAS",
                title="Scarcity mindset fMRI study",
                sample_size=40,
                key_finding="d=1.23 for confidence; d=0.98 for stress",
                effect_reported=1.23,
                effect_type="cohens_d",
            ),
        ],
        implementation_notes="Increased OFC activity, decreased dlPFC. Bright backgrounds amplify.",
        related_mechanisms=["evolutionary_adaptations", "wanting_liking_dissociation"],
    ))
    
    # FOMO
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.PSYCHOLOGICAL_STATE,
        predictor_name="fomo",
        predictor_value="high",
        predictor_description="Fear of missing out activated",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="social_urgency",
        element_description="Social proof with urgency",
        outcome_metric=OutcomeMetric.PURCHASE_INTENT,
        outcome_direction="positive",
        outcome_description="Strong ties → higher FOMO → higher purchase intent",
        effect_size=0.42,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=5,
        sources=[
            AdvertisingResearchSource(
                source_id="vansolt2019",
                authors="van Solt et al.",
                year=2019,
                title="FOMO and purchase behavior",
                key_finding="FOMO and anticipated regret as serial mediators",
            ),
        ],
        implementation_notes="Effect automatic and strongest for non-extraordinary experiences.",
        related_mechanisms=["mimetic_desire", "evolutionary_adaptations"],
    ))
    
    return knowledge


# =============================================================================
# PART III: MESSAGE APPEALS
# =============================================================================

def create_message_appeal_knowledge() -> List[AdvertisingKnowledge]:
    """
    Create message appeal effectiveness knowledge.
    
    Covers: Narrative Transportation, Fear Appeals, Humor, Framing, Language
    """
    knowledge = []
    
    # Narrative Transportation → Attitudes (Meta-analyzed)
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="narrative_transportation",
        predictor_value="high",
        predictor_description="High narrative transportation (Green & Brock)",
        ad_element=AdElement.NARRATIVE,
        element_specification="transported_narrative",
        element_description="Story with identifiable characters, imaginable plot, verisimilitude",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Strong attitude effects through narrative immersion",
        effect_size=0.47,
        effect_type=EffectType.META_R,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=76,
        total_sample_size=20000,
        sources=[
            AdvertisingResearchSource(
                source_id="vanlaer2014",
                authors="Van Laer et al.",
                year=2014,
                journal="Journal of Consumer Research",
                title="Narrative transportation meta-analysis",
                study_type="meta-analysis",
                num_studies=76,
                num_effect_sizes=132,
                key_finding="r=.47 for attitudes, r=.39 for behavioral intentions",
                effect_reported=0.47,
            ),
        ],
        implementation_notes="Antecedents: identifiable characters (r=.33), imaginable plot (r=.42), reader transportability (r=.37).",
        related_mechanisms=["attention_dynamics", "identity_construction"],
    ))
    
    # User-Generated Content → Transportation
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="content_source",
        predictor_value="user_generated",
        predictor_description="User-generated content vs professional",
        ad_element=AdElement.NARRATIVE,
        element_specification="ugc_narrative",
        element_description="User-generated narrative content",
        outcome_metric=OutcomeMetric.ENGAGEMENT,
        outcome_direction="positive",
        outcome_description="UGC produces stronger transportation in digital contexts",
        effect_size=0.25,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=64,
        sources=[
            AdvertisingResearchSource(
                source_id="vanlaer2019",
                authors="Van Laer et al.",
                year=2019,
                title="Digital narrative transportation meta-analysis",
                num_studies=64,
                num_effect_sizes=138,
                key_finding="UGC stronger than professional; commercial > non-commercial",
            ),
        ],
        implementation_notes="Commercial domains show stronger effects than non-commercial.",
        related_mechanisms=["social_proof", "mimetic_desire"],
    ))
    
    # Fear Appeals with Efficacy (Meta-analyzed)
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="fear_appeal",
        predictor_value="with_efficacy",
        predictor_description="Fear appeal paired with efficacy statement",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="fear_efficacy_appeal",
        element_description="Fear-inducing message with solution/efficacy",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Overall d=0.29 for attitudes, intentions, behaviors",
        effect_size=0.29,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=127,
        total_sample_size=27372,
        sources=[
            AdvertisingResearchSource(
                source_id="tannenbaum2015",
                authors="Tannenbaum et al.",
                year=2015,
                journal="Psychological Bulletin",
                title="Fear appeals meta-analysis",
                study_type="meta-analysis",
                num_studies=127,
                sample_size=27372,
                key_finding="d=0.29 overall; no identified backfire conditions",
                effect_reported=0.29,
            ),
        ],
        implementation_notes="Efficacy required. High susceptibility and severity increase effect. Female audiences more responsive.",
        boundary_conditions=["Efficacy statements required", "One-time behaviors > repeated"],
        related_mechanisms=["regulatory_focus", "evolutionary_adaptations"],
    ))
    
    # Humor → Ad Attitude (Meta-analyzed)
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="humor_appeal",
        predictor_value="present",
        predictor_description="Humor used in advertising",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="humor_appeal",
        element_description="Humorous advertising execution",
        outcome_metric=OutcomeMetric.AD_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Strong positive effect on ad attitude",
        effect_size=0.26,
        effect_type=EffectType.META_R,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=50,
        sources=[
            AdvertisingResearchSource(
                source_id="eisend2009",
                authors="Eisend",
                year=2009,
                journal="Journal of the Academy of Marketing Science",
                title="Humor in advertising meta-analysis",
                study_type="meta-analysis",
                num_effect_sizes=369,
                key_finding="Aad r=.26, attention r=.19, brand attitude r=.13",
            ),
        ],
        implementation_notes="Effect on Aad is 2x effect on brand attitude. Requires product-humor fit for high involvement.",
        boundary_conditions=["Reduces source credibility (r=-.05)", "Most effective for hedonic products"],
        related_mechanisms=["automatic_evaluation"],
    ))
    
    # Humor → Source Credibility (Negative)
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="humor_appeal",
        predictor_value="present",
        predictor_description="Humor used in advertising",
        ad_element=AdElement.APPEAL_TYPE,
        element_specification="humor_appeal",
        element_description="Humorous advertising execution",
        outcome_metric=OutcomeMetric.SOURCE_CREDIBILITY,
        outcome_direction="negative",
        outcome_description="Small negative effect on source credibility",
        effect_size=-0.05,
        effect_type=EffectType.META_R,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=50,
        sources=[
            AdvertisingResearchSource(
                source_id="eisend2009_cred",
                authors="Eisend",
                year=2009,
                journal="JAMS",
                title="Humor meta-analysis",
                key_finding="Source credibility r=-.05",
            ),
        ],
        implementation_notes="Trade-off: humor helps Aad but hurts credibility.",
        related_mechanisms=["automatic_evaluation"],
    ))
    
    # Message Framing: Gain for Prevention Behaviors
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="behavior_type",
        predictor_value="prevention",
        predictor_description="Prevention behavior target (e.g., sunscreen use)",
        ad_element=AdElement.MESSAGE_FRAME,
        element_specification="gain_frame",
        element_description="Gain-framed message",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Gain-framed slightly more persuasive for prevention",
        effect_size=0.03,
        effect_type=EffectType.META_R,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=93,
        total_sample_size=21656,
        sources=[
            AdvertisingResearchSource(
                source_id="okeefe2007",
                authors="O'Keefe & Jensen",
                year=2007,
                title="Gain-loss framing meta-analysis (prevention)",
                num_studies=93,
                sample_size=21656,
                key_finding="r=.03, driven largely by dental hygiene",
            ),
        ],
        implementation_notes="Very small effect. Driven by dental hygiene studies.",
        related_mechanisms=["regulatory_focus"],
    ))
    
    # Concrete Language → Listening Signal
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="language_concreteness",
        predictor_value="high",
        predictor_description="Concrete language used",
        ad_element=AdElement.LANGUAGE_STYLE,
        element_specification="concrete_language",
        element_description="Specific, concrete, vivid language",
        outcome_metric=OutcomeMetric.ENGAGEMENT,
        outcome_direction="positive",
        outcome_description="+5.6% concreteness → +8.9% satisfaction (service contexts)",
        effect_size=0.089,
        effect_type=EffectType.PERCENTAGE,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=5,
        sources=[
            AdvertisingResearchSource(
                source_id="packard2021",
                authors="Packard & Berger",
                year=2021,
                journal="Journal of Consumer Research",
                title="Concrete language signals listening",
                key_finding="+5.6% concreteness = +8.9% satisfaction increase",
            ),
        ],
        implementation_notes="Concrete phrases remembered 10x more than abstract. More persuasive under uncertainty.",
        boundary_conditions=["Abstract more persuasive for positive WOM (implies generalization)"],
        related_mechanisms=["construal_level"],
    ))
    
    return knowledge


# =============================================================================
# PART IV: VISUAL DESIGN
# =============================================================================

def create_visual_design_knowledge() -> List[AdvertisingKnowledge]:
    """
    Create visual design effectiveness knowledge.
    
    Covers: Color, White Space, Model Characteristics, Visual Metaphors, Logos
    """
    knowledge = []
    
    # Trust-Evoking Colors → Perceived Quality
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="color_trust",
        predictor_value="trust_evoking",
        predictor_description="Trust-evoking colors (blue, green)",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="trust_colors",
        element_description="Blue, green, calm color palette",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Perceived quality and recommendation likelihood",
        effect_size=0.58,
        effect_type=EffectType.BETA,
        p_value=0.001,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=3,
        total_sample_size=285,
        sources=[
            AdvertisingResearchSource(
                source_id="color2024",
                authors="2024 study",
                year=2024,
                title="Color and brand perception",
                sample_size=285,
                key_finding="Trust colors → quality β=0.58, recommend β=0.47",
            ),
        ],
        implementation_notes="Men prefer blue, green, black with bold shades; women prefer blue, purple, green with softer tints.",
        boundary_conditions=["Cultural: white=purity (Western) vs mourning (Eastern); red=danger (Western) vs luck (China)"],
        related_mechanisms=["automatic_evaluation"],
    ))
    
    # Excitement Colors → Innovation Perception
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="color_excitement",
        predictor_value="excitement_evoking",
        predictor_description="Excitement-evoking colors (red, orange)",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="excitement_colors",
        element_description="Red, orange, warm, vibrant colors",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Perceived innovation increases, but reliability decreases",
        effect_size=0.51,
        effect_type=EffectType.BETA,
        p_value=0.001,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=3,
        sources=[
            AdvertisingResearchSource(
                source_id="color2024_exc",
                authors="2024 study",
                year=2024,
                title="Color and innovation perception",
                key_finding="Innovation β=0.51, Reliability β=-0.32",
            ),
        ],
        implementation_notes="Trade-off: excitement colors increase innovation perception but decrease reliability.",
        contraindications=["Perceived reliability β=-0.32"],
        related_mechanisms=["automatic_evaluation"],
    ))
    
    # White Space → Luxury Perception
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="whitespace",
        predictor_value="high",
        predictor_description="High white space in design",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="high_whitespace",
        element_description="Generous white space, spatial openness",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Enhanced perceived quality, reputation, reduced purchase risk",
        effect_size=0.35,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=5,
        sources=[
            AdvertisingResearchSource(
                source_id="pracejus2006",
                authors="Pracejus, O'Guinn & Olsen",
                year=2006,
                journal="Journal of Consumer Research",
                title="White space and luxury perception",
                key_finding="White space signals luxury through rhetorical/cultural interpretation",
            ),
        ],
        implementation_notes="68% of luxury brands rank spatial openness as top-three visual tactic. Mechanism is cultural, not economic.",
        boundary_conditions=["Cultural: US positive effect; India/Hong Kong no effect"],
        related_mechanisms=["identity_construction"],
    ))
    
    # Model Attractiveness (Curvilinear)
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="model_attractiveness",
        predictor_value="moderate",
        predictor_description="Moderately attractive model",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="moderate_attractiveness",
        element_description="Normally attractive (not highly attractive) models",
        outcome_metric=OutcomeMetric.AD_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Often more effective than highly attractive models",
        effect_size=0.25,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=8,
        sources=[
            AdvertisingResearchSource(
                source_id="bower2001",
                authors="Bower & Landreth",
                year=2001,
                journal="Journal of Advertising",
                title="Model attractiveness curvilinear effects",
                key_finding="Highly attractive not always more effective; social comparison generates negative affect",
            ),
            AdvertisingResearchSource(
                source_id="tsai2007",
                authors="Tsai & Chang",
                year=2007,
                title="Adolescent ad response",
                key_finding="Highly attractive less effective than normally attractive for adolescents",
            ),
        ],
        implementation_notes="Curvilinear effect. Social comparison can generate negative affect and model derogation.",
        related_mechanisms=["mimetic_desire", "identity_construction"],
    ))
    
    # Eye Gaze: Averted → Transportation
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="eye_gaze",
        predictor_value="averted",
        predictor_description="Model with averted eye gaze (looking away)",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="averted_gaze",
        element_description="Model looking away from viewer",
        outcome_metric=OutcomeMetric.AD_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Stronger narrative transportation, more favorable response",
        effect_size=0.30,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=4,
        sources=[
            AdvertisingResearchSource(
                source_id="to2021",
                authors="To & Patrick",
                year=2021,
                journal="Journal of Consumer Research",
                title="Eye gaze and ad response",
                key_finding="Averted gaze → stronger transportation. Direct gaze → rational processing.",
            ),
        ],
        implementation_notes="Use averted for emotional/experiential products; direct for information-heavy.",
        related_mechanisms=["attention_dynamics", "narrative"],
    ))
    
    # Visual Metaphors → Persuasion
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="visual_metaphor",
        predictor_value="present",
        predictor_description="Visual metaphor used in ad",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="visual_metaphor",
        element_description="Metaphorical visual representation",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Increased persuasiveness through dual mechanisms",
        effect_size=0.35,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=10,
        sources=[
            AdvertisingResearchSource(
                source_id="jeong2008",
                authors="Jeong",
                year=2008,
                journal="Journal of Marketing Communications",
                title="Visual metaphor persuasion",
                key_finding="Visual argumentation and metaphorical rhetoric are independent and additive",
            ),
        ],
        implementation_notes="Moderate complexity optimal. Phillips & McQuarrie typology: Juxtaposition < Fusion < Replacement.",
        boundary_conditions=["Inverted-U: overly complex metaphors reduce comprehension"],
        related_mechanisms=["construal_level"],
    ))
    
    # Circular Logo → Comfort
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="logo_shape",
        predictor_value="circular",
        predictor_description="Circular logo shape",
        ad_element=AdElement.VISUAL_DESIGN,
        element_specification="circular_logo",
        element_description="Round, circular logo design",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Perceived comfort association",
        effect_size=0.28,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=3,
        total_sample_size=109,
        sources=[
            AdvertisingResearchSource(
                source_id="jiang2016",
                authors="Jiang et al.",
                year=2016,
                journal="Journal of Consumer Research",
                title="Logo shape and brand perception",
                sample_size=109,
                key_finding="Circular → comfort; Angular → durability",
            ),
        ],
        implementation_notes="Effect disappears when visual working memory is taxed (e.g., memorizing 10 digits).",
        boundary_conditions=["Requires cognitive resources"],
        related_mechanisms=["automatic_evaluation"],
    ))
    
    return knowledge


# =============================================================================
# PART V: MEDIA PLATFORMS
# =============================================================================

def create_media_platform_knowledge() -> List[AdvertisingKnowledge]:
    """
    Create media platform effectiveness knowledge.
    
    Covers: TV, Social Media Influencers, Native Advertising, Video Formats
    """
    knowledge = []
    
    # TV Brand Building
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="media_platform",
        predictor_value="television",
        predictor_description="Television advertising",
        ad_element=AdElement.MEDIA_PLATFORM,
        element_specification="television",
        element_description="TV advertising placement",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="2-4x greater brand ROI than high-growth digital",
        effect_size=2.5,  # Midpoint of 2-4x
        effect_type=EffectType.PERCENTAGE,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=20,
        sources=[
            AdvertisingResearchSource(
                source_id="tv_roi",
                authors="Industry research",
                year=2024,
                title="TV advertising effectiveness",
                key_finding="ROI $4.90-$7.00 per $1. 65% of media effects on sales from TV.",
            ),
        ],
        implementation_notes="39% higher brand recall vs digital. Carryover 26 days vs 14 for social. Synergy: +25% for other media.",
        related_mechanisms=["attention_dynamics"],
    ))
    
    # Influencer vs Celebrity
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="endorser_type",
        predictor_value="influencer",
        predictor_description="Social media influencer endorsement",
        ad_element=AdElement.CELEBRITY,
        element_specification="influencer_endorsement",
        element_description="Social media influencer (vs traditional celebrity)",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="More effective than brand posts, virtual influencers, traditional celebrities",
        effect_size=0.35,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=251,
        sources=[
            AdvertisingResearchSource(
                source_id="influencer2025",
                authors="JAMS meta-analysis",
                year=2025,
                journal="Journal of the Academy of Marketing Science",
                title="Social media influencer effectiveness",
                study_type="meta-analysis",
                num_studies=251,
                num_effect_sizes=1531,
                key_finding="Influencers more effective; credibility and attractiveness mediate",
            ),
        ],
        implementation_notes="Small/medium influencers better for engagement; larger for purchase intent.",
        related_mechanisms=["social_proof", "mimetic_desire"],
    ))
    
    # Native Advertising Recognition Trade-off
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="ad_format",
        predictor_value="native",
        predictor_description="Native advertising format",
        ad_element=AdElement.AD_FORMAT,
        element_specification="native_advertising",
        element_description="Native advertising (content-integrated)",
        outcome_metric=OutcomeMetric.BRAND_ATTITUDE,
        outcome_direction="positive",
        outcome_description="Only 7-18% recognize as ads; recognition → negative evaluation",
        effect_size=0.30,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=8,
        sources=[
            AdvertisingResearchSource(
                source_id="wojdynski2016",
                authors="Wojdynski & Evans",
                year=2016,
                journal="Journal of Advertising",
                title="Native advertising recognition",
                key_finding="7-18% recognition rate; recognition → more negative brand/publisher evaluation",
            ),
        ],
        implementation_notes="Positive mood + implicit disclosure → favorable. Negative mood + explicit disclosure → better.",
        boundary_conditions=["Recognition triggers negative evaluation for brand and publisher"],
        related_mechanisms=["automatic_evaluation"],
    ))
    
    # Video Length: 15 seconds optimal
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="video_length",
        predictor_value="15_seconds",
        predictor_description="15-second video ad",
        ad_element=AdElement.AD_FORMAT,
        element_specification="15sec_video",
        element_description="15-second video format",
        outcome_metric=OutcomeMetric.BRAND_RECALL,
        outcome_direction="positive",
        outcome_description="75% higher brand recall than 5-sec; avoids 30-sec drop-off",
        effect_size=0.75,
        effect_type=EffectType.PERCENTAGE,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=10,
        sources=[
            AdvertisingResearchSource(
                source_id="video_length",
                authors="Platform research",
                year=2024,
                title="Video ad length optimization",
                key_finding="FB/IG: 5-15sec; YouTube: 15sec; 6-sec bumpers deliver 60% of 30-sec impact",
            ),
        ],
        implementation_notes="Mid-roll 18.1% more likely to complete than pre-roll. For skippable: brand in first part.",
        related_mechanisms=["attention_dynamics"],
    ))
    
    # Ad Clutter → Conversion Drop
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="ad_clutter",
        predictor_value="high",
        predictor_description="High ad clutter environment (>2 ads/screen)",
        ad_element=AdElement.MEDIA_PLATFORM,
        element_specification="high_clutter",
        element_description="Cluttered ad environment",
        outcome_metric=OutcomeMetric.CONVERSION,
        outcome_direction="negative",
        outcome_description="Up to 85% reduction in conversion probability",
        effect_size=-0.85,
        effect_type=EffectType.PERCENTAGE,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        study_count=1,
        total_sample_size=1000000,
        sources=[
            AdvertisingResearchSource(
                source_id="clutter_eyetrack",
                authors="Eye-tracking field research",
                year=2024,
                title="Ad clutter attention study",
                sample_size=1000000,
                key_finding="1 SD clutter increase → up to 85% conversion reduction. >2 ads/screen → >50% attention drop",
            ),
        ],
        implementation_notes="Critical threshold: >2 ads per screen. Quality targeting: 107% attention boost.",
        related_mechanisms=["attention_dynamics"],
    ))
    
    return knowledge


# =============================================================================
# PART VI: MODERATORS AND INTERACTIONS
# =============================================================================

def create_moderator_interactions() -> List[AdvertisingInteraction]:
    """
    Create cross-reference matrix of interaction effects.
    
    Key moderating relationships from the research synthesis.
    """
    interactions = []
    
    # Celebrity-Product Fit (Most powerful)
    interactions.append(AdvertisingInteraction(
        primary_variable="celebrity_endorsement",
        primary_value="present",
        moderating_variable="product_fit",
        moderating_value="high",
        interaction_type=InteractionType.ENABLES,
        interaction_description="Celebrity endorsement only works with high product fit",
        effect_when_moderator_present=0.90,
        effect_when_moderator_absent=-0.96,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        sources=[
            AdvertisingResearchSource(
                source_id="knoll2017",
                authors="Knoll & Matthes",
                year=2017,
                journal="Journal of the Academy of Marketing Science",
                title="Celebrity endorsement meta-analysis",
                study_type="meta-analysis",
                num_studies=46,
                sample_size=10357,
                key_finding="Male actors + high fit + implicit: d=0.90; Female models + poor fit + explicit: d=-0.96",
            ),
        ],
        implementation_notes="Most important moderator in advertising. Poor fit actively harmful. Endorser brands/awards outperform celebrities.",
    ))
    
    # Product Involvement × Creativity
    interactions.append(AdvertisingInteraction(
        primary_variable="advertising_creativity",
        primary_value="high",
        moderating_variable="product_involvement",
        moderating_value="high",
        interaction_type=InteractionType.AMPLIFIES,
        interaction_description="Creativity effects stronger for high-involvement products",
        effect_when_moderator_present=0.653,
        effect_when_moderator_absent=0.340,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        sources=[
            AdvertisingResearchSource(
                source_id="creativity_involvement",
                authors="ELM research",
                year=2023,
                title="Creativity and involvement",
                key_finding="High involvement r=.653; Low involvement r=.340",
            ),
        ],
        implementation_notes="ELM framework validated. High involvement: central processing, argument quality matters.",
    ))
    
    # Personality × Brand Familiarity
    interactions.append(AdvertisingInteraction(
        primary_variable="personality_targeting",
        primary_value="extraversion",
        moderating_variable="brand_familiarity",
        moderating_value="unfamiliar",
        interaction_type=InteractionType.AMPLIFIES,
        interaction_description="Extraversion effects stronger for unfamiliar brands",
        effect_when_moderator_present=0.40,
        effect_when_moderator_absent=0.25,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        sources=[
            AdvertisingResearchSource(
                source_id="personality_familiarity",
                authors="Meta-analysis",
                year=2024,
                title="Personality and brand familiarity interaction",
                key_finding="E stronger for unfamiliar; A,C,O stronger for familiar brands",
            ),
        ],
        implementation_notes="Reverse for A, C, O: these work better with familiar brands.",
    ))
    
    # Cultural Adaptation (Diminishing over time)
    interactions.append(AdvertisingInteraction(
        primary_variable="cultural_adaptation",
        primary_value="present",
        moderating_variable="time_period",
        moderating_value="recent",
        interaction_type=InteractionType.ATTENUATES,
        interaction_description="Cultural adaptation effects have diminished over 25 years",
        effect_when_moderator_present=0.049,
        effect_when_moderator_absent=0.073,
        effect_type=EffectType.META_R,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        sources=[
            AdvertisingResearchSource(
                source_id="hornikx2023",
                authors="Hornikx, Janssen & O'Keefe",
                year=2023,
                title="Cultural adaptation meta-analysis",
                study_type="meta-analysis",
                num_studies=120,
                key_finding="Effects diminished: r=-.152 correlation with year. Early r=.073, recent r=.049",
            ),
        ],
        implementation_notes="Effects mainly for North Americans and Asians; less for Western Europeans. Globalization reducing differences.",
    ))
    
    # Humor × Product Type
    interactions.append(AdvertisingInteraction(
        primary_variable="humor_appeal",
        primary_value="present",
        moderating_variable="product_type",
        moderating_value="hedonic",
        interaction_type=InteractionType.AMPLIFIES,
        interaction_description="Humor more effective for hedonic products",
        effect_when_moderator_present=0.32,
        effect_when_moderator_absent=0.18,
        effect_type=EffectType.CORRELATION,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        sources=[
            AdvertisingResearchSource(
                source_id="humor_hedonic",
                authors="Eisend",
                year=2009,
                title="Humor meta-analysis moderators",
                key_finding="Humor most effective for hedonic products",
            ),
        ],
        implementation_notes="Product-humor fit required for high-involvement products.",
    ))
    
    # White Space × Culture
    interactions.append(AdvertisingInteraction(
        primary_variable="whitespace",
        primary_value="high",
        moderating_variable="culture",
        moderating_value="western",
        interaction_type=InteractionType.ENABLES,
        interaction_description="White space effects only in Western cultures",
        effect_when_moderator_present=0.35,
        effect_when_moderator_absent=0.0,
        effect_type=EffectType.COHENS_D,
        robustness_tier=RobustnessTier.TIER_2_REPLICATED,
        sources=[
            AdvertisingResearchSource(
                source_id="whitespace_culture",
                authors="Liu & Li",
                year=2024,
                title="White space cross-cultural",
                key_finding="US positive; India/Hong Kong no effect",
            ),
        ],
        implementation_notes="Cultural interpretation mechanism. Not economic signaling.",
    ))
    
    return interactions


# =============================================================================
# PART VII: OVERALL ADVERTISING EFFECTIVENESS
# =============================================================================

def create_baseline_effectiveness_knowledge() -> List[AdvertisingKnowledge]:
    """
    Create baseline advertising effectiveness knowledge from meta-meta-analyses.
    """
    knowledge = []
    
    # Overall Advertising Effectiveness
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="advertising_exposure",
        predictor_value="present",
        predictor_description="Exposure to advertising",
        ad_element=AdElement.CREATIVE_EXECUTION,
        element_specification="general_advertising",
        element_description="General advertising exposure",
        outcome_metric=OutcomeMetric.PERSUASION,
        outcome_direction="positive",
        outcome_description="Overall advertising effectiveness correlation",
        effect_size=0.20,
        effect_type=EffectType.META_R,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=1700,
        total_sample_size=2400000,
        sources=[
            AdvertisingResearchSource(
                source_id="eisend2016",
                authors="Eisend & Tarrahi",
                year=2016,
                journal="Journal of Advertising",
                title="Meta-meta-analysis of advertising effectiveness",
                study_type="meta-analysis",
                num_studies=44,
                num_effect_sizes=324,
                sample_size=2400000,
                key_finding="r=.20 overall. Based on 44 meta-analyses, 1,700+ primary studies",
            ),
        ],
        implementation_notes="Baseline. Effect varies dramatically with targeting precision and creative quality.",
        related_mechanisms=[],
    ))
    
    # Bias-Corrected Elasticity (More conservative)
    knowledge.append(AdvertisingKnowledge(
        predictor_category=PredictorCategory.CONTEXT,
        predictor_name="advertising_spend",
        predictor_value="increased",
        predictor_description="Increased advertising spend",
        ad_element=AdElement.MEDIA_PLATFORM,
        element_specification="general_spend",
        element_description="Advertising spend increase",
        outcome_metric=OutcomeMetric.CONVERSION,
        outcome_direction="positive",
        outcome_description="Short-term elasticity 0.0008; Long-term 0.03 (bias-corrected)",
        effect_size=0.03,
        effect_type=EffectType.BETA,
        robustness_tier=RobustnessTier.TIER_1_META_ANALYZED,
        study_count=50,
        sources=[
            AdvertisingResearchSource(
                source_id="korkames2025",
                authors="Korkames et al.",
                year=2025,
                title="Bias-corrected advertising elasticity",
                key_finding="5x smaller than traditional estimates after publication bias correction",
            ),
        ],
        implementation_notes="Traditional estimates are inflated 5x by publication selection bias.",
        related_mechanisms=[],
    ))
    
    return knowledge


# =============================================================================
# SEEDER CLASS
# =============================================================================

class ConsumerPsychologySeeder:
    """
    Seeds the system with 25 years of consumer psychology research.
    
    Provides validated knowledge for:
    - Personality-based targeting
    - Psychological state-aware messaging
    - Message appeal optimization
    - Visual design effectiveness
    - Media platform selection
    - Moderator/interaction effects
    """
    
    def __init__(self):
        self._knowledge: Dict[str, AdvertisingKnowledge] = {}
        self._interactions: Dict[str, AdvertisingInteraction] = {}
    
    def seed_all_knowledge(self) -> tuple:
        """
        Seed all consumer psychology research knowledge.
        
        Returns tuple of (knowledge_list, interaction_list).
        """
        all_knowledge = []
        all_interactions = []
        
        # Personality traits
        personality = create_personality_trait_knowledge()
        all_knowledge.extend(personality)
        logger.info(f"Seeded {len(personality)} personality trait knowledge items")
        
        # Psychological states
        states = create_psychological_state_knowledge()
        all_knowledge.extend(states)
        logger.info(f"Seeded {len(states)} psychological state knowledge items")
        
        # Message appeals
        appeals = create_message_appeal_knowledge()
        all_knowledge.extend(appeals)
        logger.info(f"Seeded {len(appeals)} message appeal knowledge items")
        
        # Visual design
        visual = create_visual_design_knowledge()
        all_knowledge.extend(visual)
        logger.info(f"Seeded {len(visual)} visual design knowledge items")
        
        # Media platforms
        media = create_media_platform_knowledge()
        all_knowledge.extend(media)
        logger.info(f"Seeded {len(media)} media platform knowledge items")
        
        # Baseline effectiveness
        baseline = create_baseline_effectiveness_knowledge()
        all_knowledge.extend(baseline)
        logger.info(f"Seeded {len(baseline)} baseline effectiveness items")
        
        # Moderator interactions
        interactions = create_moderator_interactions()
        all_interactions.extend(interactions)
        logger.info(f"Seeded {len(interactions)} moderator interactions")
        
        # Index by ID
        for k in all_knowledge:
            self._knowledge[k.knowledge_id] = k
        
        for i in all_interactions:
            self._interactions[i.interaction_id] = i
        
        logger.info(
            f"Total consumer psychology knowledge seeded: "
            f"{len(all_knowledge)} items, {len(all_interactions)} interactions"
        )
        
        return all_knowledge, all_interactions
    
    def get_knowledge(self, knowledge_id: str) -> Optional[AdvertisingKnowledge]:
        """Get knowledge by ID."""
        return self._knowledge.get(knowledge_id)
    
    def get_knowledge_for_predictor(
        self,
        predictor_name: str,
    ) -> List[AdvertisingKnowledge]:
        """Get all knowledge for a predictor variable."""
        return [
            k for k in self._knowledge.values()
            if k.predictor_name == predictor_name
        ]
    
    def get_knowledge_for_outcome(
        self,
        outcome: OutcomeMetric,
    ) -> List[AdvertisingKnowledge]:
        """Get all knowledge predicting an outcome."""
        return [
            k for k in self._knowledge.values()
            if k.outcome_metric == outcome
        ]
    
    def get_tier1_knowledge(self) -> List[AdvertisingKnowledge]:
        """Get only meta-analyzed (Tier 1) knowledge."""
        return [
            k for k in self._knowledge.values()
            if k.robustness_tier == RobustnessTier.TIER_1_META_ANALYZED
        ]
    
    def get_interactions_for_variable(
        self,
        variable: str,
    ) -> List[AdvertisingInteraction]:
        """Get interactions involving a variable."""
        return [
            i for i in self._interactions.values()
            if i.primary_variable == variable or i.moderating_variable == variable
        ]
    
    def get_knowledge_for_mechanism(
        self,
        mechanism: str,
    ) -> List[AdvertisingKnowledge]:
        """Get knowledge related to a cognitive mechanism."""
        return [
            k for k in self._knowledge.values()
            if mechanism in k.related_mechanisms
        ]


# Singleton
_seeder: Optional[ConsumerPsychologySeeder] = None


def get_consumer_psychology_seeder() -> ConsumerPsychologySeeder:
    """Get singleton consumer psychology seeder."""
    global _seeder
    if _seeder is None:
        _seeder = ConsumerPsychologySeeder()
    return _seeder
