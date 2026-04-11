// =============================================================================
// ADAM Neo4j Migration 005: Seed Personality Dimensions
// The 35 psychological constructs for comprehensive user profiling
// =============================================================================

// -----------------------------------------------------------------------------
// BIG FIVE PERSONALITY DIMENSIONS (5)
// The foundation of personality psychology
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_big5_openness'})
SET d.name = 'openness',
    d.full_name = 'Openness to Experience',
    d.domain = 'big_five',
    d.dimension_type = 'trait',
    d.description = 'Preference for novelty, creativity, and intellectual curiosity. High scorers seek new experiences; low scorers prefer routine.',
    d.low_description = 'Conventional, practical, prefers routine and familiarity',
    d.high_description = 'Creative, curious, open to new ideas and experiences',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High openness users respond to novel, creative ads. Low openness users respond to familiar, trusted approaches.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_big5_conscientiousness'})
SET d.name = 'conscientiousness',
    d.full_name = 'Conscientiousness',
    d.domain = 'big_five',
    d.dimension_type = 'trait',
    d.description = 'Tendency toward organization, dependability, and goal-directed behavior. High scorers are disciplined; low scorers are flexible.',
    d.low_description = 'Flexible, spontaneous, adaptable',
    d.high_description = 'Organized, disciplined, goal-oriented',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High conscientiousness users value quality, reliability, and detailed information. Low conscientiousness users respond to convenience.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_big5_extraversion'})
SET d.name = 'extraversion',
    d.full_name = 'Extraversion',
    d.domain = 'big_five',
    d.dimension_type = 'trait',
    d.description = 'Orientation toward the external world, social interaction, and stimulation. High scorers are outgoing; low scorers prefer solitude.',
    d.low_description = 'Reserved, introspective, prefers solitude',
    d.high_description = 'Outgoing, energetic, seeks social interaction',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High extraversion users respond to social proof and group activities. Low extraversion users prefer personal, individual messaging.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_big5_agreeableness'})
SET d.name = 'agreeableness',
    d.full_name = 'Agreeableness',
    d.domain = 'big_five',
    d.dimension_type = 'trait',
    d.description = 'Tendency toward cooperation, trust, and concern for others. High scorers are compassionate; low scorers are competitive.',
    d.low_description = 'Competitive, skeptical, challenging',
    d.high_description = 'Cooperative, trusting, helpful',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High agreeableness users respond to prosocial messaging. Low agreeableness users respond to competitive, status-based appeals.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_big5_neuroticism'})
SET d.name = 'neuroticism',
    d.full_name = 'Neuroticism',
    d.domain = 'big_five',
    d.dimension_type = 'trait',
    d.description = 'Tendency toward negative emotions, stress reactivity, and emotional instability. High scorers experience more anxiety; low scorers are emotionally stable.',
    d.low_description = 'Emotionally stable, calm, resilient',
    d.high_description = 'Emotionally reactive, prone to anxiety',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High neuroticism users may respond to safety and security messaging. Low neuroticism users respond to adventure and risk.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// REGULATORY FOCUS (2)
// Higgins (1997) - Promotion vs Prevention orientation
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_reg_promotion'})
SET d.name = 'promotion_focus',
    d.full_name = 'Promotion Focus',
    d.domain = 'regulatory_focus',
    d.dimension_type = 'orientation',
    d.description = 'Focus on gains, growth, and advancement. Promotion-focused individuals seek to maximize positive outcomes.',
    d.low_description = 'Less focused on gains and advancement',
    d.high_description = 'Strongly focused on achieving gains and aspirations',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Respond to gain-framed messages emphasizing benefits, growth, and achievement.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_reg_prevention'})
SET d.name = 'prevention_focus',
    d.full_name = 'Prevention Focus',
    d.domain = 'regulatory_focus',
    d.dimension_type = 'orientation',
    d.description = 'Focus on security, safety, and avoiding losses. Prevention-focused individuals seek to minimize negative outcomes.',
    d.low_description = 'Less focused on security and loss avoidance',
    d.high_description = 'Strongly focused on security and avoiding losses',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Respond to loss-framed messages emphasizing safety, security, and risk avoidance.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// COGNITIVE STYLE (4)
// How people process information
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_cog_need_for_cognition'})
SET d.name = 'need_for_cognition',
    d.full_name = 'Need for Cognition',
    d.domain = 'cognitive_style',
    d.dimension_type = 'trait',
    d.description = 'Tendency to engage in and enjoy effortful cognitive activities. High NFC individuals prefer complex information.',
    d.low_description = 'Prefers simple, straightforward information',
    d.high_description = 'Enjoys complex, detailed information processing',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High NFC users respond to detailed, argument-rich ads. Low NFC users respond to simple, heuristic-based appeals.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_cog_self_monitoring'})
SET d.name = 'self_monitoring',
    d.full_name = 'Self-Monitoring',
    d.domain = 'cognitive_style',
    d.dimension_type = 'trait',
    d.description = 'Tendency to observe and control self-presentation. High self-monitors adapt to social situations.',
    d.low_description = 'Authentic, consistent across situations',
    d.high_description = 'Adapts presentation to social context',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High self-monitors respond to image-based, social-context ads. Low self-monitors respond to quality and value.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_cog_decision_style'})
SET d.name = 'decision_style',
    d.full_name = 'Decision Style',
    d.domain = 'cognitive_style',
    d.dimension_type = 'style',
    d.description = 'Preference for maximizing (finding the best option) vs satisficing (finding a good enough option).',
    d.low_description = 'Satisficer - accepts good enough options',
    d.high_description = 'Maximizer - seeks the optimal choice',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Maximizers need comparison information. Satisficers respond to quick, confident recommendations.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_cog_processing_style'})
SET d.name = 'processing_style',
    d.full_name = 'Information Processing Style',
    d.domain = 'cognitive_style',
    d.dimension_type = 'style',
    d.description = 'Preference for visual vs verbal information processing.',
    d.low_description = 'Verbal processor - prefers text and language',
    d.high_description = 'Visual processor - prefers images and video',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Visual processors respond to imagery. Verbal processors respond to copy-heavy content.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// TEMPORAL ORIENTATION (3)
// How people relate to time
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_temp_future_orientation'})
SET d.name = 'future_orientation',
    d.full_name = 'Future Orientation',
    d.domain = 'temporal',
    d.dimension_type = 'orientation',
    d.description = 'Degree to which one thinks about and plans for the future vs focuses on the present.',
    d.low_description = 'Present-focused, immediate gratification',
    d.high_description = 'Future-focused, delayed gratification',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Future-oriented users respond to long-term benefits. Present-oriented users respond to immediate rewards.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_temp_time_urgency'})
SET d.name = 'time_urgency',
    d.full_name = 'Time Urgency',
    d.domain = 'temporal',
    d.dimension_type = 'trait',
    d.description = 'Chronic sense of time pressure and need for speed.',
    d.low_description = 'Relaxed about time, unhurried',
    d.high_description = 'Time-pressured, seeks efficiency',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Time-urgent users respond to efficiency and quick wins. Relaxed users appreciate detailed exploration.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_temp_planning_horizon'})
SET d.name = 'planning_horizon',
    d.full_name = 'Planning Horizon',
    d.domain = 'temporal',
    d.dimension_type = 'trait',
    d.description = 'How far into the future one typically plans.',
    d.low_description = 'Short-term planner (days/weeks)',
    d.high_description = 'Long-term planner (months/years)',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Long-horizon planners respond to investment and durability. Short-horizon planners respond to immediate utility.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// SOCIAL ORIENTATION (4)
// How people relate to others
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_social_susceptibility'})
SET d.name = 'social_influence_susceptibility',
    d.full_name = 'Social Influence Susceptibility',
    d.domain = 'social',
    d.dimension_type = 'trait',
    d.description = 'Degree to which one is influenced by others opinions and behaviors.',
    d.low_description = 'Independent, resistant to social influence',
    d.high_description = 'Highly influenced by social context',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High susceptibility users respond strongly to social proof. Low susceptibility users prefer independent evaluation.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_social_uniqueness'})
SET d.name = 'need_for_uniqueness',
    d.full_name = 'Need for Uniqueness',
    d.domain = 'social',
    d.dimension_type = 'trait',
    d.description = 'Desire to differentiate oneself from others through consumption and behavior.',
    d.low_description = 'Comfortable with conformity',
    d.high_description = 'Seeks differentiation and uniqueness',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High uniqueness seekers respond to exclusivity and customization. Low uniqueness seekers respond to popularity.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_social_status_concern'})
SET d.name = 'status_concern',
    d.full_name = 'Status Concern',
    d.domain = 'social',
    d.dimension_type = 'trait',
    d.description = 'Importance placed on social status and prestige.',
    d.low_description = 'Status-indifferent',
    d.high_description = 'Status-conscious',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High status concern responds to premium, luxury, and prestige messaging. Low status concern responds to value.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_social_trust'})
SET d.name = 'general_trust',
    d.full_name = 'General Trust',
    d.domain = 'social',
    d.dimension_type = 'trait',
    d.description = 'Baseline level of trust in others and institutions.',
    d.low_description = 'Skeptical, requires proof',
    d.high_description = 'Trusting, accepts claims',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Low trust users need evidence and guarantees. High trust users accept brand promises.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// MOTIVATIONAL PROFILE (4)
// What drives behavior
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_mot_intrinsic'})
SET d.name = 'intrinsic_motivation',
    d.full_name = 'Intrinsic Motivation',
    d.domain = 'motivation',
    d.dimension_type = 'orientation',
    d.description = 'Driven by internal satisfaction vs external rewards.',
    d.low_description = 'Externally motivated by rewards',
    d.high_description = 'Internally motivated by satisfaction',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Intrinsically motivated users respond to mastery and meaning. Extrinsically motivated users respond to rewards.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_mot_achievement'})
SET d.name = 'achievement_motivation',
    d.full_name = 'Achievement Motivation',
    d.domain = 'motivation',
    d.dimension_type = 'trait',
    d.description = 'Drive to accomplish goals and excel.',
    d.low_description = 'Low achievement drive',
    d.high_description = 'Strong achievement drive',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High achievement users respond to performance and success themes.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_mot_power'})
SET d.name = 'power_motivation',
    d.full_name = 'Power Motivation',
    d.domain = 'motivation',
    d.dimension_type = 'trait',
    d.description = 'Drive to influence others and control resources.',
    d.low_description = 'Low power drive',
    d.high_description = 'Strong power drive',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High power users respond to control, authority, and dominance themes.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_mot_affiliation'})
SET d.name = 'affiliation_motivation',
    d.full_name = 'Affiliation Motivation',
    d.domain = 'motivation',
    d.dimension_type = 'trait',
    d.description = 'Drive to form and maintain social connections.',
    d.low_description = 'Low affiliation drive',
    d.high_description = 'Strong affiliation drive',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High affiliation users respond to belonging, community, and connection themes.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// UNCERTAINTY PROCESSING (3)
// How people handle ambiguity
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_unc_tolerance'})
SET d.name = 'uncertainty_tolerance',
    d.full_name = 'Uncertainty Tolerance',
    d.domain = 'uncertainty',
    d.dimension_type = 'trait',
    d.description = 'Comfort with ambiguous situations and incomplete information.',
    d.low_description = 'Intolerant of ambiguity, needs clarity',
    d.high_description = 'Comfortable with uncertainty',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Low tolerance users need clear, specific information. High tolerance users accept exploratory messaging.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_unc_need_for_closure'})
SET d.name = 'need_for_closure',
    d.full_name = 'Need for Cognitive Closure',
    d.domain = 'uncertainty',
    d.dimension_type = 'trait',
    d.description = 'Desire for definitive answers and discomfort with ambiguity.',
    d.low_description = 'Low closure need, comfortable exploring',
    d.high_description = 'High closure need, wants definitive answers',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High closure need users respond to clear recommendations. Low closure need users appreciate options.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_unc_risk_attitude'})
SET d.name = 'risk_attitude',
    d.full_name = 'Risk Attitude',
    d.domain = 'uncertainty',
    d.dimension_type = 'trait',
    d.description = 'General tendency toward risk-seeking vs risk-aversion.',
    d.low_description = 'Risk-averse, prefers safety',
    d.high_description = 'Risk-seeking, embraces uncertainty',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Risk-averse users need guarantees and safety. Risk-seekers respond to opportunity and adventure.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

// -----------------------------------------------------------------------------
// EMOTIONAL PROCESSING (3)
// How people experience and regulate emotions
// -----------------------------------------------------------------------------

MERGE (d:PersonalityDimension {dimension_id: 'dim_emo_affect_intensity'})
SET d.name = 'affect_intensity',
    d.full_name = 'Affect Intensity',
    d.domain = 'emotional',
    d.dimension_type = 'trait',
    d.description = 'Intensity with which emotions are experienced.',
    d.low_description = 'Low intensity emotional responses',
    d.high_description = 'Intense emotional experiences',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High intensity users respond to emotional appeals. Low intensity users respond to rational arguments.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_emo_regulation'})
SET d.name = 'emotion_regulation',
    d.full_name = 'Emotion Regulation',
    d.domain = 'emotional',
    d.dimension_type = 'trait',
    d.description = 'Ability to manage and control emotional responses.',
    d.low_description = 'Reactive, emotions influence decisions',
    d.high_description = 'Regulated, emotions are managed',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Low regulation users make emotional purchases. High regulation users deliberate.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();

MERGE (d:PersonalityDimension {dimension_id: 'dim_emo_positivity'})
SET d.name = 'positive_affectivity',
    d.full_name = 'Positive Affectivity',
    d.domain = 'emotional',
    d.dimension_type = 'trait',
    d.description = 'Tendency to experience positive emotions.',
    d.low_description = 'Neutral to negative baseline affect',
    d.high_description = 'Positive baseline affect',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'High positivity users respond to upbeat, optimistic messaging. Low positivity users need realistic framing.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();
