"""
Validated Language Patterns for Relationship Detection
=======================================================

This module contains validated linguistic patterns derived from academic
research for detecting consumer-brand relationship types.

Academic Sources:
- Escalas & Bettman (2003) Self-Brand Connection Scale (α=0.96)
- Thomson, MacInnis & Park (2005) Brand Attachment Scale (α=0.94)
- Park et al. (2010) Brand Attachment (α=0.95)
- Taute & Sierra (2014) Brand Tribalism Scale (α=0.89)
- Carroll & Ahuvia (2006) Brand Love Scale (α=0.91)
- Sprott, Czellar & Spangenberg (2009) Brand Engagement in Self-Concept (α=0.93)
- Hollebeek, Glynn & Brodie (2014) Consumer Brand Engagement Scale (α=0.92)
"""

from typing import List, Dict
from .models import (
    LanguagePattern,
    RelationshipTypeId,
    LinguisticMarkerType,
    ObservationChannel,
)


# =============================================================================
# SELF-IDENTITY CORE PATTERNS
# =============================================================================

SELF_IDENTITY_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="identity_copula_am",
        pattern_text="I am a [brand] person",
        pattern_regex=r"i am a (\w+) (person|guy|girl|user|owner|fan|loyalist)",
        examples=[
            "I am a Ford guy",
            "I'm a Nike person through and through",
            "I am a Mac user for life",
        ],
        relationship_type=RelationshipTypeId.SELF_IDENTITY_CORE,
        marker_type=LinguisticMarkerType.IDENTITY_INTEGRATION,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.98,
        },
        validated_source="Escalas & Bettman (2003)",
        cronbachs_alpha=0.96,
    ),
    LanguagePattern(
        pattern_id="identity_is_me",
        pattern_text="[brand] is who I am / part of me",
        pattern_regex=r"(\w+) is (who i am|part of me|me$|a part of my life|a part of who)",
        examples=[
            "Apple is who I am",
            "Nike is part of me",
            "This brand is me",
        ],
        relationship_type=RelationshipTypeId.SELF_IDENTITY_CORE,
        marker_type=LinguisticMarkerType.IDENTITY_INTEGRATION,
        base_weight=0.98,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.98,
        },
        validated_source="Escalas & Bettman (2003)",
    ),
    LanguagePattern(
        pattern_id="identity_blood_dna",
        pattern_text="[brand] is in my blood/DNA",
        pattern_regex=r"(in my blood|in my dna|born (\w+)|bred to be|raised on)",
        examples=[
            "Ford is in my blood",
            "I was born Apple",
            "Racing is in my DNA",
        ],
        relationship_type=RelationshipTypeId.SELF_IDENTITY_CORE,
        marker_type=LinguisticMarkerType.IDENTITY_INTEGRATION,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.95,
        },
    ),
    LanguagePattern(
        pattern_id="identity_always_been",
        pattern_text="I have always been [brand]",
        pattern_regex=r"(always been|always will be|never change from|forever a)",
        examples=[
            "I've always been a Toyota person",
            "I will always be Nike",
            "Forever a Pepsi person",
        ],
        relationship_type=RelationshipTypeId.SELF_IDENTITY_CORE,
        marker_type=LinguisticMarkerType.IDENTITY_INTEGRATION,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="identity_defines_me",
        pattern_text="[brand] defines/reflects who I am",
        pattern_regex=r"(defines who|reflects who|says a lot about who|represents who)",
        examples=[
            "This brand defines who I am",
            "It reflects who I am as a person",
            "My car says a lot about who I am",
        ],
        relationship_type=RelationshipTypeId.SELF_IDENTITY_CORE,
        marker_type=LinguisticMarkerType.IDENTITY_INTEGRATION,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.95,
        },
        validated_source="Park et al. (2010)",
    ),
]


# =============================================================================
# SELF-EXPRESSION VEHICLE PATTERNS
# =============================================================================

SELF_EXPRESSION_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="expression_values",
        pattern_text="Brand aligns with my values",
        pattern_regex=r"(share.? (my|the same) values|stand for what i believe|believe in what they)",
        examples=[
            "They share my values",
            "They stand for what I believe in",
            "I believe in what they're doing",
        ],
        relationship_type=RelationshipTypeId.SELF_EXPRESSION_VEHICLE,
        marker_type=LinguisticMarkerType.VALUE_ALIGNMENT,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.80,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="expression_resonates",
        pattern_text="Brand resonates / is 'me'",
        pattern_regex=r"(resonates with|just clicks|feels like me|very.? ['\"]?me['\"]?|my aesthetic)",
        examples=[
            "This brand resonates with me",
            "It just clicks with who I am",
            "It's very 'me'",
        ],
        relationship_type=RelationshipTypeId.SELF_EXPRESSION_VEHICLE,
        marker_type=LinguisticMarkerType.VALUE_ALIGNMENT,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.75,
            ObservationChannel.SOCIAL_SIGNALS: 0.82,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="expression_suits_me",
        pattern_text="[brand] suits me well",
        pattern_regex=r"(suits me|right for me|fits me|made for people like me|perfect fit for)",
        examples=[
            "This brand suits me perfectly",
            "It's right for me",
            "Made for people like me",
        ],
        relationship_type=RelationshipTypeId.SELF_EXPRESSION_VEHICLE,
        marker_type=LinguisticMarkerType.VALUE_ALIGNMENT,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
        validated_source="Escalas & Bettman (2003)",
    ),
]


# =============================================================================
# STATUS MARKER PATTERNS
# =============================================================================

STATUS_MARKER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="status_people_notice",
        pattern_text="People notice when you have [brand]",
        pattern_regex=r"people (notice|compliment|ask about|comment on|always say)",
        examples=[
            "People notice when you have a Rolex",
            "I always get compliments",
            "People ask about it all the time",
        ],
        relationship_type=RelationshipTypeId.STATUS_MARKER,
        marker_type=LinguisticMarkerType.STATUS_DISPLAY,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.50,
        },
    ),
    LanguagePattern(
        pattern_id="status_investment",
        pattern_text="Investment piece / worth the price",
        pattern_regex=r"(investment piece|worth every penny|worth the price|treat myself|treat yourself)",
        examples=[
            "It's an investment piece",
            "Worth every penny",
            "I decided to treat myself",
        ],
        relationship_type=RelationshipTypeId.STATUS_MARKER,
        marker_type=LinguisticMarkerType.STATUS_DISPLAY,
        base_weight=0.75,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.80,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.40,
        },
    ),
    LanguagePattern(
        pattern_id="status_turns_heads",
        pattern_text="Turns heads / commands respect",
        pattern_regex=r"(turns heads|commands respect|makes a statement|stands out|gets attention)",
        examples=[
            "This car turns heads",
            "It commands respect",
            "Really makes a statement",
        ],
        relationship_type=RelationshipTypeId.STATUS_MARKER,
        marker_type=LinguisticMarkerType.STATUS_DISPLAY,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.78,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.45,
        },
    ),
    LanguagePattern(
        pattern_id="status_exclusive",
        pattern_text="Exclusive / not everyone can have it",
        pattern_regex=r"(not everyone|exclusive|aspirational|prestigious|luxury|premium)",
        examples=[
            "Not everyone can have one",
            "It's exclusive",
            "Truly aspirational",
        ],
        relationship_type=RelationshipTypeId.STATUS_MARKER,
        marker_type=LinguisticMarkerType.STATUS_DISPLAY,
        base_weight=0.72,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.70,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.35,
        },
    ),
]


# =============================================================================
# TRIBAL BADGE PATTERNS
# =============================================================================

TRIBAL_BADGE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="tribal_my_people",
        pattern_text="My people/tribe use [brand]",
        pattern_regex=r"(my|our) (people|tribe|community|family|crew|squad)",
        examples=[
            "My people know the real deal",
            "Our community loves this",
            "This is what our tribe uses",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_BADGE,
        marker_type=LinguisticMarkerType.TRIBAL_MEMBERSHIP,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.80,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
        validated_source="Taute & Sierra (2014)",
        cronbachs_alpha=0.89,
    ),
    LanguagePattern(
        pattern_id="tribal_fellow_owners",
        pattern_text="Fellow [brand] owners",
        pattern_regex=r"fellow (\w+) (owners|users|people|fans|lovers|enthusiasts)",
        examples=[
            "Fellow Jeep owners know",
            "Us Tesla people understand",
            "Fellow coffee lovers",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_BADGE,
        marker_type=LinguisticMarkerType.TRIBAL_MEMBERSHIP,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.75,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
        validated_source="Taute & Sierra (2014)",
    ),
    LanguagePattern(
        pattern_id="tribal_defense",
        pattern_text="Defending brand from criticism",
        pattern_regex=r"(don.?t talk bad|leave .+ alone|back off|don.?t hate|stop hating)",
        examples=[
            "Don't talk bad about Apple",
            "Leave my brand alone",
            "Stop hating on Ford",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_BADGE,
        marker_type=LinguisticMarkerType.TRIBAL_MEMBERSHIP,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.80,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
        validated_source="Taute & Sierra (2014)",
    ),
    LanguagePattern(
        pattern_id="tribal_hashtag",
        pattern_text="#Team[brand] / [brand] Nation",
        pattern_regex=r"(#team|#squad|nation|family|for life|gang|mafia)",
        examples=[
            "#TeamiPhone",
            "Android nation",
            "Jeep family for life",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_BADGE,
        marker_type=LinguisticMarkerType.TRIBAL_MEMBERSHIP,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.65,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
]


# =============================================================================
# COMMITTED PARTNERSHIP PATTERNS
# =============================================================================

COMMITTED_PARTNERSHIP_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="love_brand",
        pattern_text="I love [brand]",
        pattern_regex=r"i (love|adore|am obsessed with|absolutely love|truly love)",
        examples=[
            "I love this brand",
            "I adore everything they make",
            "I'm obsessed with their products",
        ],
        relationship_type=RelationshipTypeId.COMMITTED_PARTNERSHIP,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.65,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
        validated_source="Carroll & Ahuvia (2006)",
        cronbachs_alpha=0.91,
    ),
    LanguagePattern(
        pattern_id="loyal_customer",
        pattern_text="Loyal customer for X years",
        pattern_regex=r"(loyal|been using for|been a customer|been buying|\d+ years)",
        examples=[
            "Loyal customer for 10 years",
            "Been using this brand for decades",
            "15 years and counting",
        ],
        relationship_type=RelationshipTypeId.COMMITTED_PARTNERSHIP,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
    LanguagePattern(
        pattern_id="never_switch",
        pattern_text="Would never switch",
        pattern_regex=r"(never switch|wouldn.?t switch|only brand|never change|always come back)",
        examples=[
            "I would never switch brands",
            "This is the only brand I buy",
            "I always come back to them",
        ],
        relationship_type=RelationshipTypeId.COMMITTED_PARTNERSHIP,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="never_disappoints",
        pattern_text="Never disappoints",
        pattern_regex=r"(never disappoint|never let.? me down|always deliver|consistent|reliable)",
        examples=[
            "They never disappoint",
            "Never lets me down",
            "Always delivers quality",
        ],
        relationship_type=RelationshipTypeId.COMMITTED_PARTNERSHIP,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.60,
            ObservationChannel.SELF_EXPRESSION: 0.65,
        },
    ),
    LanguagePattern(
        pattern_id="emotional_connection",
        pattern_text="Feel connected/bonded",
        pattern_regex=r"(feel connected|strong bond|connection to|bonded|attached)",
        examples=[
            "I feel connected to this brand",
            "There's a strong bond",
            "I'm emotionally attached",
        ],
        relationship_type=RelationshipTypeId.COMMITTED_PARTNERSHIP,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.72,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
        validated_source="Thomson et al. (2005)",
        cronbachs_alpha=0.94,
    ),
]


# =============================================================================
# DEPENDENCY PATTERNS
# =============================================================================

DEPENDENCY_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="dependency_cant_live",
        pattern_text="Can't live without",
        pattern_regex=r"(can.?t live without|can.?t imagine life without|need this|essential|lifeline)",
        examples=[
            "Can't live without my iPhone",
            "This is essential to my life",
            "It's my lifeline",
        ],
        relationship_type=RelationshipTypeId.DEPENDENCY,
        marker_type=LinguisticMarkerType.DEPENDENCY,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="dependency_addicted",
        pattern_text="Addicted to [brand]",
        pattern_regex=r"(addicted|hooked|obsessed|can.?t stop|always need)",
        examples=[
            "I'm addicted to their coffee",
            "Totally hooked on this brand",
            "Can't stop buying from them",
        ],
        relationship_type=RelationshipTypeId.DEPENDENCY,
        marker_type=LinguisticMarkerType.DEPENDENCY,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
    LanguagePattern(
        pattern_id="dependency_panic",
        pattern_text="Panic when unavailable",
        pattern_regex=r"(panic|freak out|stress when|worried about|scared to run out)",
        examples=[
            "I panic when they're out of stock",
            "I stress when I can't get it",
            "Freaked out when they discontinued it",
        ],
        relationship_type=RelationshipTypeId.DEPENDENCY,
        marker_type=LinguisticMarkerType.DEPENDENCY,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
]


# =============================================================================
# RELIABLE TOOL PATTERNS
# =============================================================================

RELIABLE_TOOL_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="functional_works",
        pattern_text="It just works",
        pattern_regex=r"(just works|does the job|works as expected|reliable|dependable)",
        examples=[
            "It just works",
            "Does exactly what it should",
            "Very reliable product",
        ],
        relationship_type=RelationshipTypeId.RELIABLE_TOOL,
        marker_type=LinguisticMarkerType.FUNCTIONAL,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.50,
            ObservationChannel.SELF_EXPRESSION: 0.30,
        },
    ),
    LanguagePattern(
        pattern_id="functional_practical",
        pattern_text="Practical choice",
        pattern_regex=r"(practical|functional|no frills|gets the job done|efficient|effective)",
        examples=[
            "A practical choice",
            "Very functional design",
            "No frills, just works",
        ],
        relationship_type=RelationshipTypeId.RELIABLE_TOOL,
        marker_type=LinguisticMarkerType.FUNCTIONAL,
        base_weight=0.75,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.40,
            ObservationChannel.SELF_EXPRESSION: 0.20,
        },
    ),
    LanguagePattern(
        pattern_id="functional_value",
        pattern_text="Good value / cost-effective",
        pattern_regex=r"(good value|great value|cost effective|bang for buck|worth the money)",
        examples=[
            "Great value for the price",
            "Very cost effective",
            "Best bang for your buck",
        ],
        relationship_type=RelationshipTypeId.RELIABLE_TOOL,
        marker_type=LinguisticMarkerType.FUNCTIONAL,
        base_weight=0.70,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.45,
            ObservationChannel.SELF_EXPRESSION: 0.25,
        },
    ),
]


# =============================================================================
# MENTOR PATTERNS
# =============================================================================

MENTOR_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="mentor_taught_me",
        pattern_text="They taught me",
        pattern_regex=r"(taught me|learned from|expert quality|professional grade|trust their expertise)",
        examples=[
            "They taught me everything about coffee",
            "I learned so much from their tutorials",
            "Trust their expertise completely",
        ],
        relationship_type=RelationshipTypeId.MENTOR,
        marker_type=LinguisticMarkerType.EXPERTISE,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.65,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
    LanguagePattern(
        pattern_id="mentor_authority",
        pattern_text="The authority / gold standard",
        pattern_regex=r"(the authority|gold standard|industry leader|best in class|the expert)",
        examples=[
            "They're the authority on this",
            "The gold standard in the industry",
            "Best in class, no question",
        ],
        relationship_type=RelationshipTypeId.MENTOR,
        marker_type=LinguisticMarkerType.EXPERTISE,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.60,
        },
    ),
]


# =============================================================================
# CHILDHOOD FRIEND PATTERNS
# =============================================================================

CHILDHOOD_FRIEND_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="nostalgia_childhood",
        pattern_text="Reminds me of childhood",
        pattern_regex=r"(reminds me of|growing up|childhood|like my mom|tradition|memories)",
        examples=[
            "Reminds me of my childhood",
            "Like what my mom used",
            "A family tradition",
        ],
        relationship_type=RelationshipTypeId.CHILDHOOD_FRIEND,
        marker_type=LinguisticMarkerType.NOSTALGIA,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.60,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="nostalgia_generations",
        pattern_text="Used for generations",
        pattern_regex=r"(generations|grandma|grandfather|family recipe|handed down|heritage)",
        examples=[
            "My family has used this for generations",
            "Just like grandma used to make",
            "A family heritage brand",
        ],
        relationship_type=RelationshipTypeId.CHILDHOOD_FRIEND,
        marker_type=LinguisticMarkerType.NOSTALGIA,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.55,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="nostalgia_comfort",
        pattern_text="Nostalgic comfort",
        pattern_regex=r"(takes me back|brings back memories|comforting familiarity|like home)",
        examples=[
            "Takes me back to simpler times",
            "Brings back so many memories",
            "It's like coming home",
        ],
        relationship_type=RelationshipTypeId.CHILDHOOD_FRIEND,
        marker_type=LinguisticMarkerType.NOSTALGIA,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.58,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# ENEMY PATTERNS
# =============================================================================

ENEMY_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="enemy_never_again",
        pattern_text="Never again / betrayed",
        pattern_regex=r"(never again|betrayed|used to love but|scam|false advertising|ruined)",
        examples=[
            "Never buying from them again",
            "I feel betrayed by this brand",
            "Complete scam, avoid at all costs",
        ],
        relationship_type=RelationshipTypeId.ENEMY,
        marker_type=LinguisticMarkerType.HOSTILE,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
    LanguagePattern(
        pattern_id="enemy_boycott",
        pattern_text="Boycott / spread the word",
        pattern_regex=r"(boycott|spread the word|don.?t support|cancelled|exposed|warn everyone)",
        examples=[
            "I'm boycotting this company",
            "Spreading the word to avoid them",
            "They've been exposed",
        ],
        relationship_type=RelationshipTypeId.ENEMY,
        marker_type=LinguisticMarkerType.HOSTILE,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.98,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
    LanguagePattern(
        pattern_id="enemy_hate",
        pattern_text="Hate this brand",
        pattern_regex=r"(hate|despise|worst company|horrible|terrible company|avoid)",
        examples=[
            "I hate this brand now",
            "Worst company I've dealt with",
            "Avoid at all costs",
        ],
        relationship_type=RelationshipTypeId.ENEMY,
        marker_type=LinguisticMarkerType.HOSTILE,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.65,
        },
    ),
]


# =============================================================================
# COMFORT COMPANION PATTERNS
# =============================================================================

COMFORT_COMPANION_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="comfort_soothing",
        pattern_text="Soothing / calming",
        pattern_regex=r"(soothing|calming|relaxing|comfort|peaceful|stress relief)",
        examples=[
            "So soothing after a long day",
            "Helps me relax completely",
            "My comfort brand",
        ],
        relationship_type=RelationshipTypeId.COMFORT_COMPANION,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.55,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
    LanguagePattern(
        pattern_id="comfort_escape",
        pattern_text="My escape / treat",
        pattern_regex=r"(my escape|little treat|guilty pleasure|indulgence|self.?care)",
        examples=[
            "My little escape from reality",
            "My guilty pleasure",
            "Part of my self-care routine",
        ],
        relationship_type=RelationshipTypeId.COMFORT_COMPANION,
        marker_type=LinguisticMarkerType.EMOTIONAL_ATTACHMENT,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# ASPIRATIONAL ICON PATTERNS
# =============================================================================

ASPIRATIONAL_ICON_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="aspirational_dream",
        pattern_text="Dream [product] / one day I'll",
        pattern_regex=r"(dream car|dream watch|dream bag|one day i.?ll|saving for|goals|manifesting)",
        examples=[
            "My dream car",
            "One day I'll own one",
            "Saving up for this beauty",
        ],
        relationship_type=RelationshipTypeId.ASPIRATIONAL_ICON,
        marker_type=LinguisticMarkerType.STATUS_DISPLAY,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.60,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
    LanguagePattern(
        pattern_id="aspirational_working_toward",
        pattern_text="Working toward / achieving",
        pattern_regex=r"(working toward|working for|finally achieved|finally got|graduation gift|milestone)",
        examples=[
            "Finally achieved my goal",
            "Been working toward this for years",
            "A milestone purchase",
        ],
        relationship_type=RelationshipTypeId.ASPIRATIONAL_ICON,
        marker_type=LinguisticMarkerType.STATUS_DISPLAY,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.75,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
]


# =============================================================================
# CHAMPION/EVANGELIST PATTERNS (NEW)
# =============================================================================

CHAMPION_EVANGELIST_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="evangelist_tell_everyone",
        pattern_text="I tell everyone about [brand]",
        pattern_regex=r"(tell everyone|always recommend|always telling people|spread the word about|got .+ people to)",
        examples=[
            "I tell everyone about this brand",
            "I always recommend them to friends",
            "I've gotten so many people to switch",
        ],
        relationship_type=RelationshipTypeId.CHAMPION_EVANGELIST,
        marker_type=LinguisticMarkerType.EVANGELISM,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
    LanguagePattern(
        pattern_id="evangelist_converted",
        pattern_text="I've converted people",
        pattern_regex=r"(converted|brought over|convinced .+ to try|recruited|made .+ a fan)",
        examples=[
            "I've converted so many friends",
            "I brought my whole family over",
            "I convinced my office to switch",
        ],
        relationship_type=RelationshipTypeId.CHAMPION_EVANGELIST,
        marker_type=LinguisticMarkerType.EVANGELISM,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="evangelist_defend",
        pattern_text="I defend [brand] when criticized",
        pattern_regex=r"(i defend|always defend|stick up for|can.?t stand when people criticize|have to correct)",
        examples=[
            "I always defend this brand",
            "I can't stand when people criticize them",
            "I have to correct people when they're wrong about it",
        ],
        relationship_type=RelationshipTypeId.CHAMPION_EVANGELIST,
        marker_type=LinguisticMarkerType.EVANGELISM,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.80,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="evangelist_ambassador",
        pattern_text="Unofficial ambassador",
        pattern_regex=r"(unofficial ambassador|brand ambassador|walking advertisement|one.?person marketing)",
        examples=[
            "I'm like an unofficial ambassador",
            "I'm a walking advertisement for them",
            "One-person marketing team for this brand",
        ],
        relationship_type=RelationshipTypeId.CHAMPION_EVANGELIST,
        marker_type=LinguisticMarkerType.EVANGELISM,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.75,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# GUILTY PLEASURE PATTERNS (NEW)
# =============================================================================

GUILTY_PLEASURE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="guilty_pleasure_secret",
        pattern_text="My guilty pleasure / secret",
        pattern_regex=r"(guilty pleasure|my secret|don.?t judge|secret obsession|wouldn.?t admit)",
        examples=[
            "It's my guilty pleasure",
            "Don't judge me but...",
            "My secret obsession",
            "I wouldn't admit this publicly",
        ],
        relationship_type=RelationshipTypeId.GUILTY_PLEASURE,
        marker_type=LinguisticMarkerType.GUILT_SHAME,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="guilty_shouldnt",
        pattern_text="I know I shouldn't but...",
        pattern_regex=r"(know i shouldn.?t|shouldn.?t but|bad habit|against my principles|hypocritical)",
        examples=[
            "I know I shouldn't, but I love it",
            "It's against my principles, but...",
            "I'm a bit hypocritical because...",
        ],
        relationship_type=RelationshipTypeId.GUILTY_PLEASURE,
        marker_type=LinguisticMarkerType.GUILT_SHAME,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.60,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="guilty_hidden",
        pattern_text="Hidden / private consumption",
        pattern_regex=r"(hide|hidden|private|secretly|closet|under the radar|low.?key)",
        examples=[
            "I hide my purchases",
            "It's my secret indulgence",
            "Low-key obsessed",
        ],
        relationship_type=RelationshipTypeId.GUILTY_PLEASURE,
        marker_type=LinguisticMarkerType.GUILT_SHAME,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.55,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# RESCUE/SAVIOR PATTERNS (NEW)
# =============================================================================

RESCUE_SAVIOR_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="rescue_saved_life",
        pattern_text="Saved my life / business",
        pattern_regex=r"(saved my life|saved my business|saved my marriage|saved my skin|was my salvation)",
        examples=[
            "This product saved my life",
            "Literally saved my business",
            "It was my salvation during...",
        ],
        relationship_type=RelationshipTypeId.RESCUE_SAVIOR,
        marker_type=LinguisticMarkerType.RESCUE_GRATITUDE,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="rescue_game_changer",
        pattern_text="Game changer / turned everything around",
        pattern_regex=r"(game changer|life changer|changed everything|turned .+ around|before .+ i was)",
        examples=[
            "This was a complete game changer",
            "Turned everything around for me",
            "Before this, I was struggling",
        ],
        relationship_type=RelationshipTypeId.RESCUE_SAVIOR,
        marker_type=LinguisticMarkerType.RESCUE_GRATITUDE,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="rescue_dont_know_what",
        pattern_text="Don't know what I would have done",
        pattern_regex=r"(don.?t know what i would|couldn.?t have done it without|where would i be|was at rock bottom|desperate until)",
        examples=[
            "Don't know what I would have done without this",
            "Couldn't have made it without them",
            "I was desperate until I found this",
        ],
        relationship_type=RelationshipTypeId.RESCUE_SAVIOR,
        marker_type=LinguisticMarkerType.RESCUE_GRATITUDE,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="rescue_forever_grateful",
        pattern_text="Forever grateful / owe them",
        pattern_regex=r"(forever grateful|eternally grateful|owe them|indebted|will never forget)",
        examples=[
            "I'm forever grateful to this brand",
            "I owe them so much",
            "Will never forget how they helped me",
        ],
        relationship_type=RelationshipTypeId.RESCUE_SAVIOR,
        marker_type=LinguisticMarkerType.RESCUE_GRATITUDE,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# COURTSHIP/DATING PATTERNS (NEW)
# =============================================================================

COURTSHIP_DATING_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="courtship_trying_out",
        pattern_text="Trying out / testing",
        pattern_regex=r"(trying out|testing|giving .+ a try|first time|so far so good|seeing how)",
        examples=[
            "Just trying this out",
            "First time using this brand",
            "Giving them a try, so far so good",
        ],
        relationship_type=RelationshipTypeId.COURTSHIP_DATING,
        marker_type=LinguisticMarkerType.EXPLORATION_TRIAL,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.60,
        },
    ),
    LanguagePattern(
        pattern_id="courtship_curious",
        pattern_text="Curious / heard good things",
        pattern_regex=r"(curious about|heard good things|wanted to see|decided to try|gave .+ a shot)",
        examples=[
            "I was curious about this brand",
            "Heard good things, decided to try",
            "Gave it a shot based on reviews",
        ],
        relationship_type=RelationshipTypeId.COURTSHIP_DATING,
        marker_type=LinguisticMarkerType.EXPLORATION_TRIAL,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.72,
            ObservationChannel.SELF_EXPRESSION: 0.55,
        },
    ),
    LanguagePattern(
        pattern_id="courtship_comparing",
        pattern_text="Comparing to my usual brand",
        pattern_regex=r"(comparing to|compared to my usual|vs my regular|testing against|see if it.?s better)",
        examples=[
            "Comparing to my usual brand",
            "Testing it against what I normally use",
            "Wanted to see if it's better than...",
        ],
        relationship_type=RelationshipTypeId.COURTSHIP_DATING,
        marker_type=LinguisticMarkerType.EXPLORATION_TRIAL,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.65,
            ObservationChannel.SELF_EXPRESSION: 0.50,
        },
    ),
    LanguagePattern(
        pattern_id="courtship_not_sure_yet",
        pattern_text="Not sure yet / still deciding",
        pattern_regex=r"(not sure yet|still deciding|jury.?s still out|need more time|too early to tell)",
        examples=[
            "Not sure yet, need more time",
            "The jury's still out",
            "Too early to tell if I'll stick with them",
        ],
        relationship_type=RelationshipTypeId.COURTSHIP_DATING,
        marker_type=LinguisticMarkerType.EXPLORATION_TRIAL,
        base_weight=0.75,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.60,
            ObservationChannel.SELF_EXPRESSION: 0.55,
        },
    ),
]


# =============================================================================
# REBOUND RELATIONSHIP PATTERNS (NEW)
# =============================================================================

REBOUND_RELATIONSHIP_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="rebound_switched_from",
        pattern_text="Switched from [competitor]",
        pattern_regex=r"(switched from|came from|left|after .+ disappointed|used to use .+ but)",
        examples=[
            "Switched from Brand X after they disappointed me",
            "I came from Brand X",
            "Used to use X but they let me down",
        ],
        relationship_type=RelationshipTypeId.REBOUND_RELATIONSHIP,
        marker_type=LinguisticMarkerType.REBOUND_REJECTION,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.65,
        },
    ),
    LanguagePattern(
        pattern_id="rebound_anything_but",
        pattern_text="Anything but [competitor]",
        pattern_regex=r"(anything but|never going back to|done with|over .+ for good|refuse to use .+ again)",
        examples=[
            "Anything but Brand X at this point",
            "Never going back to them",
            "Done with that brand for good",
        ],
        relationship_type=RelationshipTypeId.REBOUND_RELATIONSHIP,
        marker_type=LinguisticMarkerType.REBOUND_REJECTION,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
    LanguagePattern(
        pattern_id="rebound_finally_left",
        pattern_text="Finally left / escaped [competitor]",
        pattern_regex=r"(finally left|finally escaped|finally free from|glad i left|should have switched sooner)",
        examples=[
            "Finally left Brand X",
            "So glad I escaped that brand",
            "Should have switched sooner",
        ],
        relationship_type=RelationshipTypeId.REBOUND_RELATIONSHIP,
        marker_type=LinguisticMarkerType.REBOUND_REJECTION,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.68,
        },
    ),
]


# =============================================================================
# CAPTIVE/ENSLAVEMENT PATTERNS (NEW)
# =============================================================================

CAPTIVE_ENSLAVEMENT_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="captive_no_choice",
        pattern_text="No choice / have to use",
        pattern_regex=r"(no choice|have to use|forced to|only option|monopoly|no alternative)",
        examples=[
            "I have no choice but to use them",
            "They're the only option",
            "It's basically a monopoly",
        ],
        relationship_type=RelationshipTypeId.CAPTIVE_ENSLAVEMENT,
        marker_type=LinguisticMarkerType.ENTRAPMENT,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
    LanguagePattern(
        pattern_id="captive_stuck",
        pattern_text="Stuck with / trapped",
        pattern_regex=r"(stuck with|trapped|locked in|can.?t leave|switching costs|too invested)",
        examples=[
            "I'm stuck with them",
            "Feel trapped in their ecosystem",
            "Too invested to leave now",
        ],
        relationship_type=RelationshipTypeId.CAPTIVE_ENSLAVEMENT,
        marker_type=LinguisticMarkerType.ENTRAPMENT,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
    LanguagePattern(
        pattern_id="captive_hate_need",
        pattern_text="Hate that I need them",
        pattern_regex=r"(hate that i need|hate that i have to|resent|frustrating that|wish i could leave)",
        examples=[
            "I hate that I need them",
            "Resent having to use this brand",
            "Wish I could leave but can't",
        ],
        relationship_type=RelationshipTypeId.CAPTIVE_ENSLAVEMENT,
        marker_type=LinguisticMarkerType.ENTRAPMENT,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="captive_hostage",
        pattern_text="Held hostage / hostage to",
        pattern_regex=r"(held hostage|hostage to|prisoner|captive|at their mercy|got you by)",
        examples=[
            "They've got us hostage",
            "We're prisoners to their platform",
            "Completely at their mercy",
        ],
        relationship_type=RelationshipTypeId.CAPTIVE_ENSLAVEMENT,
        marker_type=LinguisticMarkerType.ENTRAPMENT,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
]


# =============================================================================
# RELUCTANT USER PATTERNS (NEW)
# =============================================================================

RELUCTANT_USER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="reluctant_afford",
        pattern_text="All I can afford",
        pattern_regex=r"(all i can afford|only thing in my budget|can.?t afford better|cheaper option|budget forces)",
        examples=[
            "It's all I can afford right now",
            "Can't afford the better brands",
            "Budget forces me to use this",
        ],
        relationship_type=RelationshipTypeId.RELUCTANT_USER,
        marker_type=LinguisticMarkerType.RELUCTANCE,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.65,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
    LanguagePattern(
        pattern_id="reluctant_dont_like_but",
        pattern_text="Don't like it but...",
        pattern_regex=r"(don.?t like .+ but|not a fan but|hate .+ but|despite .+ issues|put up with)",
        examples=[
            "I don't like them, but it works",
            "Not a fan, but what can you do",
            "I put up with their issues",
        ],
        relationship_type=RelationshipTypeId.RELUCTANT_USER,
        marker_type=LinguisticMarkerType.RELUCTANCE,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
    LanguagePattern(
        pattern_id="reluctant_required",
        pattern_text="Required by employer/etc.",
        pattern_regex=r"(required by|work requires|company mandates|have to use for work|employer provides)",
        examples=[
            "My work requires us to use this",
            "Company mandates this platform",
            "Have to use it for my job",
        ],
        relationship_type=RelationshipTypeId.RELUCTANT_USER,
        marker_type=LinguisticMarkerType.RELUCTANCE,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.68,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
    LanguagePattern(
        pattern_id="reluctant_only_option_here",
        pattern_text="Only option available here",
        pattern_regex=r"(only option here|only .+ available|no other .+ in my area|rural|limited options)",
        examples=[
            "It's the only option in my area",
            "No other providers available here",
            "Limited options where I live",
        ],
        relationship_type=RelationshipTypeId.RELUCTANT_USER,
        marker_type=LinguisticMarkerType.RELUCTANCE,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.65,
            ObservationChannel.SELF_EXPRESSION: 0.68,
        },
    ),
]


# =============================================================================
# SOCIAL COMPLIANCE PATTERNS (NEW)
# =============================================================================

SOCIAL_COMPLIANCE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="compliance_everyone_uses",
        pattern_text="Everyone uses it",
        pattern_regex=r"(everyone uses|everyone has|everyone in my .+ uses|what we all use|standard in my)",
        examples=[
            "Everyone in my office uses it",
            "It's what we all use",
            "Standard in my industry",
        ],
        relationship_type=RelationshipTypeId.SOCIAL_COMPLIANCE,
        marker_type=LinguisticMarkerType.PEER_CONFORMITY,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
    LanguagePattern(
        pattern_id="compliance_pressure",
        pattern_text="Felt pressure to use",
        pattern_regex=r"(felt pressure|peer pressure|pressure to switch|didn.?t want to be|everyone else was)",
        examples=[
            "Felt pressure to switch to what everyone else uses",
            "Didn't want to be the only one not using it",
            "Peer pressure got me",
        ],
        relationship_type=RelationshipTypeId.SOCIAL_COMPLIANCE,
        marker_type=LinguisticMarkerType.PEER_CONFORMITY,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="compliance_fit_in",
        pattern_text="To fit in / not stand out",
        pattern_regex=r"(fit in|not stand out|same as everyone|blend in|be like everyone|part of the group)",
        examples=[
            "Wanted to fit in with the group",
            "Didn't want to stand out",
            "To be like everyone else",
        ],
        relationship_type=RelationshipTypeId.SOCIAL_COMPLIANCE,
        marker_type=LinguisticMarkerType.PEER_CONFORMITY,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.78,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# COMPARTMENTALIZED IDENTITY PATTERNS (NEW)
# =============================================================================

COMPARTMENTALIZED_IDENTITY_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="compartment_for_work",
        pattern_text="For work I use...",
        pattern_regex=r"(for work i use|my work .+|professional use|at the office|for business)",
        examples=[
            "For work I use this brand",
            "My work laptop is always...",
            "At the office we use...",
        ],
        relationship_type=RelationshipTypeId.COMPARTMENTALIZED_IDENTITY,
        marker_type=LinguisticMarkerType.CONTEXT_SPECIFIC,
        base_weight=0.80,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.72,
            ObservationChannel.SELF_EXPRESSION: 0.78,
        },
    ),
    LanguagePattern(
        pattern_id="compartment_when_role",
        pattern_text="When I'm [role], I prefer...",
        pattern_regex=r"(when i.?m .+ing|as a .+ i use|in my .+ mode|for my .+ side|my .+ self)",
        examples=[
            "When I'm working out, I use...",
            "As a parent, I prefer...",
            "My professional self uses...",
        ],
        relationship_type=RelationshipTypeId.COMPARTMENTALIZED_IDENTITY,
        marker_type=LinguisticMarkerType.CONTEXT_SPECIFIC,
        base_weight=0.78,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="compartment_context_brand",
        pattern_text="My [context] brand",
        pattern_regex=r"(my .+ brand|my go.?to for|only use for|specifically for|dedicated to)",
        examples=[
            "My go-to for gym clothes",
            "I only use this for cooking",
            "My dedicated travel brand",
        ],
        relationship_type=RelationshipTypeId.COMPARTMENTALIZED_IDENTITY,
        marker_type=LinguisticMarkerType.CONTEXT_SPECIFIC,
        base_weight=0.75,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.68,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
]


# =============================================================================
# SEASONAL REKINDLER PATTERNS (NEW)
# =============================================================================

SEASONAL_REKINDLER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="seasonal_every_year",
        pattern_text="Every [season/holiday] I...",
        pattern_regex=r"(every year|every .+mas|every summer|every winter|annual|yearly tradition)",
        examples=[
            "Every Christmas I buy their...",
            "Every summer we use...",
            "It's an annual tradition",
        ],
        relationship_type=RelationshipTypeId.SEASONAL_REKINDLER,
        marker_type=LinguisticMarkerType.SEASONAL_TEMPORAL,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
    LanguagePattern(
        pattern_id="seasonal_tradition",
        pattern_text="Our tradition / ritual",
        pattern_regex=r"(our tradition|family tradition|ritual|wouldn.?t be .+ without|always during)",
        examples=[
            "It's our family tradition",
            "The holiday wouldn't be the same without",
            "Always use them during the season",
        ],
        relationship_type=RelationshipTypeId.SEASONAL_REKINDLER,
        marker_type=LinguisticMarkerType.SEASONAL_TEMPORAL,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="seasonal_time_of_year",
        pattern_text="Time of year for [brand]",
        pattern_regex=r"(time of year|that time again|season for|comes around|once a year)",
        examples=[
            "It's that time of year again",
            "The season for this brand",
            "Only buy it when the season comes around",
        ],
        relationship_type=RelationshipTypeId.SEASONAL_REKINDLER,
        marker_type=LinguisticMarkerType.SEASONAL_TEMPORAL,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: ACCOUNTABILITY CAPTOR PATTERNS
# The Duolingo Owl Effect - guilt/streak-driven engagement
# =============================================================================

ACCOUNTABILITY_CAPTOR_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="captor_streak_anxiety",
        pattern_text="Streak anxiety / broke my streak",
        pattern_regex=r"(broke my streak|lost my streak|streak anxiety|can.?t break|maintain.* streak|200.?day streak)",
        examples=[
            "I've cried over a broken 200-day streak",
            "Can't break my streak now",
            "The anxiety of maintaining my streak",
        ],
        relationship_type=RelationshipTypeId.ACCOUNTABILITY_CAPTOR,
        marker_type=LinguisticMarkerType.STREAK_ANXIETY,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="captor_guilt_notification",
        pattern_text="Guilt-inducing notifications",
        pattern_regex=r"(guilt.?trip|makes me feel guilty|the owl|duo owl|notification at|passive aggressive)",
        examples=[
            "The owl guilt-trips me every day",
            "That passive aggressive notification at 9 PM",
            "Duo owl wins again",
        ],
        relationship_type=RelationshipTypeId.ACCOUNTABILITY_CAPTOR,
        marker_type=LinguisticMarkerType.STREAK_ANXIETY,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="captor_abusive_relationship",
        pattern_text="Abusive relationship metaphor",
        pattern_regex=r"(abusive relationship|toxic but|manipulative|lure.* back|fear of losing|sunk cost)",
        examples=[
            "It's like an abusive relationship with the app",
            "Toxic but I can't quit",
            "Fear of losing my progress keeps me coming back",
        ],
        relationship_type=RelationshipTypeId.ACCOUNTABILITY_CAPTOR,
        marker_type=LinguisticMarkerType.STREAK_ANXIETY,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: SUBSCRIPTION CONSCIENCE PATTERNS
# Guilt about unused subscriptions
# =============================================================================

SUBSCRIPTION_CONSCIENCE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="subscription_necessary_evil",
        pattern_text="Necessary evil",
        pattern_regex=r"(necessary evil|have to have|need but hate|paying but not using|waste of money but)",
        examples=[
            "It's a necessary evil",
            "Paying for it but barely use it",
            "Need it but hate paying",
        ],
        relationship_type=RelationshipTypeId.SUBSCRIPTION_CONSCIENCE,
        marker_type=LinguisticMarkerType.SUBSCRIPTION_GUILT,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="subscription_guilt_paying",
        pattern_text="Guilt about paying but not using",
        pattern_regex=r"(feel guilty|should use more|paying for nothing|money down the drain|cancel but can.?t)",
        examples=[
            "Feel guilty every month when I see the charge",
            "Should use it more to justify the cost",
            "I should cancel but what if I need it",
        ],
        relationship_type=RelationshipTypeId.SUBSCRIPTION_CONSCIENCE,
        marker_type=LinguisticMarkerType.SUBSCRIPTION_GUILT,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.65,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: SACRED PRACTICE PATTERNS
# Ritualized consumption with symbolic meaning
# =============================================================================

SACRED_PRACTICE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="sacred_ritual",
        pattern_text="My ritual / sacred routine",
        pattern_regex=r"(my ritual|sacred|sanctuary|morning routine|evening routine|self.?care ritual)",
        examples=[
            "My morning coffee ritual is sacred",
            "Skincare is my sanctuary",
            "This is my sacred evening routine",
        ],
        relationship_type=RelationshipTypeId.SACRED_PRACTICE,
        marker_type=LinguisticMarkerType.RITUAL_SACRED,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.95,
        },
    ),
    LanguagePattern(
        pattern_id="sacred_meditative",
        pattern_text="Meditative / mindful consumption",
        pattern_regex=r"(meditative|mindful|presence|ceremony|verse in the poetry|rhythm)",
        examples=[
            "The ritual is almost meditative",
            "Each step is like a ceremony",
            "Sets a rhythm for my day",
        ],
        relationship_type=RelationshipTypeId.SACRED_PRACTICE,
        marker_type=LinguisticMarkerType.RITUAL_SACRED,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="sacred_look_forward",
        pattern_text="Look forward to the ritual",
        pattern_regex=r"(look forward to|can.?t wait for|favorite part of|the best part of my)",
        examples=[
            "I look forward to it the night before",
            "Can't wait for my morning ritual",
            "The best part of my morning",
        ],
        relationship_type=RelationshipTypeId.SACRED_PRACTICE,
        marker_type=LinguisticMarkerType.RITUAL_SACRED,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: TEMPORAL MARKER PATTERNS
# Brand marks life milestones
# =============================================================================

TEMPORAL_MARKER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="temporal_milestone",
        pattern_text="Where we [milestone]",
        pattern_regex=r"(where we .+(engaged|married|celebrated)|graduation|milestone|anniversary|first date)",
        examples=[
            "This is where we got engaged",
            "My graduation gift to myself",
            "Our anniversary restaurant",
        ],
        relationship_type=RelationshipTypeId.TEMPORAL_MARKER,
        marker_type=LinguisticMarkerType.MILESTONE_MARKER,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="temporal_backdrop",
        pattern_text="Backdrop to our lives",
        pattern_regex=r"(backdrop to|witnessed|been there for|through.*(good times|bad times)|holds memories)",
        examples=[
            "They've been the backdrop to our lives",
            "This place holds so many memories",
            "Been there through good times and bad",
        ],
        relationship_type=RelationshipTypeId.TEMPORAL_MARKER,
        marker_type=LinguisticMarkerType.MILESTONE_MARKER,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="temporal_heirloom",
        pattern_text="Heirloom / passed down",
        pattern_regex=r"(heirloom|pass.* down|three generations|from my (grand)?mother|will give to my)",
        examples=[
            "This is heirloom cookware",
            "Passed down three generations",
            "Will give this to my children",
        ],
        relationship_type=RelationshipTypeId.TEMPORAL_MARKER,
        marker_type=LinguisticMarkerType.MILESTONE_MARKER,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: MOURNING BOND PATTERNS
# Grieving discontinued products
# =============================================================================

MOURNING_BOND_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="mourning_devastated",
        pattern_text="Devastated / RIP product",
        pattern_regex=r"(devastated|distraught|mourning|rip|heartbroken|crying|never get over)",
        examples=[
            "I'm devastated they discontinued it",
            "RIP to the best product ever",
            "Still mourning the loss",
            "I will never get over this",
        ],
        relationship_type=RelationshipTypeId.MOURNING_BOND,
        marker_type=LinguisticMarkerType.PRODUCT_GRIEF,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.98,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="mourning_worst_thing",
        pattern_text="Worst thing to happen",
        pattern_regex=r"(worst thing|unique.* heartbreak|world ended|loss of my (hg|holy grail)|absolute worst)",
        examples=[
            "The absolute worst thing to happen to me",
            "It's a unique kind of heartbreak",
            "Still mourning the loss of my HG",
        ],
        relationship_type=RelationshipTypeId.MOURNING_BOND,
        marker_type=LinguisticMarkerType.PRODUCT_GRIEF,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
    LanguagePattern(
        pattern_id="mourning_hoarding",
        pattern_text="Hoarding remaining stock",
        pattern_regex=r"(hoard|stock.?pil|bought .+ more|snag|hunt.* down|last .+ ever)",
        examples=[
            "I hoarded every last one I could find",
            "Snagged 2 more off Amazon while I still can",
            "Hunting down the last remaining stock",
        ],
        relationship_type=RelationshipTypeId.MOURNING_BOND,
        marker_type=LinguisticMarkerType.PRODUCT_GRIEF,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.70,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: FORMULA BETRAYAL PATTERNS
# Anger at changed formulas/recipes
# =============================================================================

FORMULA_BETRAYAL_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="formula_changed",
        pattern_text="They changed the formula",
        pattern_regex=r"(changed the formula|new formula|not the same|used to be|reformulat|why did they change)",
        examples=[
            "They changed the formula and ruined it",
            "The new formula is terrible",
            "It's not the same anymore",
        ],
        relationship_type=RelationshipTypeId.FORMULA_BETRAYAL,
        marker_type=LinguisticMarkerType.FORMULA_ANGER,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
    LanguagePattern(
        pattern_id="formula_special_betrayal",
        pattern_text="Special kind of betrayal",
        pattern_regex=r"(special.* betrayal|worse than discontinu|same label|like we.?re not supposed to notice|pretend)",
        examples=[
            "That's a special kind of betrayal",
            "Worse than just discontinuing it",
            "They kept the same label like we wouldn't notice",
        ],
        relationship_type=RelationshipTypeId.FORMULA_BETRAYAL,
        marker_type=LinguisticMarkerType.FORMULA_ANGER,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: LIFE RAFT PATTERNS
# Brand rescued during crisis
# =============================================================================

LIFE_RAFT_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="liferaft_got_through",
        pattern_text="Got me through [crisis]",
        pattern_regex=r"(got me through|saved me during|helped me survive|there for me when|during (covid|pandemic|breakup|divorce|illness))",
        examples=[
            "This got me through my breakup",
            "Saved me during the pandemic",
            "Was there for me when no one else was",
        ],
        relationship_type=RelationshipTypeId.LIFE_RAFT,
        marker_type=LinguisticMarkerType.CRISIS_RESCUE,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="liferaft_community",
        pattern_text="Community saved me",
        pattern_regex=r"(community.*saved|together through|all there for each other|got through.*together|support system)",
        examples=[
            "The community saved me",
            "We were all there for each other",
            "Got through it together",
        ],
        relationship_type=RelationshipTypeId.LIFE_RAFT,
        marker_type=LinguisticMarkerType.CRISIS_RESCUE,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="liferaft_therapy",
        pattern_text="Like therapy / escape",
        pattern_regex=r"(like therapy|my escape|only place.*quiet|heads are quiet|mental health|saved my sanity)",
        examples=[
            "It's like therapy for me",
            "The only place where my head is quiet",
            "Saved my mental health",
        ],
        relationship_type=RelationshipTypeId.LIFE_RAFT,
        marker_type=LinguisticMarkerType.CRISIS_RESCUE,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.82,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: TRANSFORMATION AGENT PATTERNS
# Brand fundamentally changed who they are
# =============================================================================

TRANSFORMATION_AGENT_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="transform_changed_life",
        pattern_text="Changed my life",
        pattern_regex=r"(changed my life|life.?changing|transformed|before .+ i was|who i am today)",
        examples=[
            "This product changed my life",
            "Life-changing, no seriously",
            "Before this, I was a different person",
        ],
        relationship_type=RelationshipTypeId.TRANSFORMATION_AGENT,
        marker_type=LinguisticMarkerType.TRANSFORMATION,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="transform_strongest",
        pattern_text="Strongest I've ever been",
        pattern_regex=r"(strongest i.?ve|best version|never felt better|peak|completely different person|new me)",
        examples=[
            "I'm the strongest I've ever been",
            "The best version of myself",
            "Completely different person now",
        ],
        relationship_type=RelationshipTypeId.TRANSFORMATION_AGENT,
        marker_type=LinguisticMarkerType.TRANSFORMATION,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.88,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="transform_never_use_another",
        pattern_text="Never use another kind",
        pattern_regex=r"(never use another|no going back|can.?t imagine|how did i live|changed .+ forever)",
        examples=[
            "I'll never use another kind",
            "No going back after this",
            "How did I ever live without it",
        ],
        relationship_type=RelationshipTypeId.TRANSFORMATION_AGENT,
        marker_type=LinguisticMarkerType.TRANSFORMATION,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: SECOND BRAIN PATTERNS
# Cognitive extension/dependency
# =============================================================================

SECOND_BRAIN_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="brain_extension",
        pattern_text="Second brain / extension of mind",
        pattern_regex=r"(second brain|extension of my mind|outsourced my (brain|thinking|memory)|can.?t think without)",
        examples=[
            "Notion is my second brain",
            "It's an extension of my mind",
            "I've outsourced my thinking to this app",
        ],
        relationship_type=RelationshipTypeId.SECOND_BRAIN,
        marker_type=LinguisticMarkerType.COGNITIVE_EXTENSION,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="brain_all_stored",
        pattern_text="Everything stored here",
        pattern_regex=r"(digital life|everything stored|all my .+ in|can.?t function without|no need to (think|remember))",
        examples=[
            "My entire digital life is stored here",
            "All my thoughts, ideas, everything",
            "No need to remember anything anymore",
        ],
        relationship_type=RelationshipTypeId.SECOND_BRAIN,
        marker_type=LinguisticMarkerType.COGNITIVE_EXTENSION,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: PLATFORM LOCK-IN PATTERNS
# Rational ecosystem commitment
# =============================================================================

PLATFORM_LOCKIN_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="lockin_stuck_platform",
        pattern_text="Stuck with the platform",
        pattern_regex=r"(stuck with|locked in|once you choose|about the batteries|not cross.?compatible|switching costs)",
        examples=[
            "Once you choose a brand, you're stuck",
            "It's all about the batteries",
            "Switching costs are too high now",
        ],
        relationship_type=RelationshipTypeId.PLATFORM_LOCK_IN,
        marker_type=LinguisticMarkerType.ECOSYSTEM_LOCK,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.80,
        },
    ),
    LanguagePattern(
        pattern_id="lockin_might_as_well",
        pattern_text="Might as well continue",
        pattern_regex=r"(might as well|already have|keep adding|too invested|committed now|deep in the ecosystem)",
        examples=[
            "Already have their batteries, might as well continue",
            "Too invested in the ecosystem now",
            "I'm committed at this point",
        ],
        relationship_type=RelationshipTypeId.PLATFORM_LOCK_IN,
        marker_type=LinguisticMarkerType.ECOSYSTEM_LOCK,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.72,
            ObservationChannel.SELF_EXPRESSION: 0.78,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: TRIBAL SIGNAL PATTERNS
# Recognition protocols (Jeep Wave, Tesla Smile)
# =============================================================================

TRIBAL_SIGNAL_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="signal_the_wave",
        pattern_text="The wave / acknowledgment",
        pattern_regex=r"(the (jeep )?wave|wave at (each other|other)|nod at|acknowledge each|smile at other|fellow .+ owner)",
        examples=[
            "The Jeep wave is sacred",
            "We wave at each other on the road",
            "Fellow owners always acknowledge",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_SIGNAL,
        marker_type=LinguisticMarkerType.RECOGNITION_PROTOCOL,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.98,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="signal_unwritten_rule",
        pattern_text="Unwritten rules / protocol",
        pattern_regex=r"(unwritten rule|not in a manual|not official|hierarchy system|protocol|rules we follow)",
        examples=[
            "It's not in any manual but everyone does it",
            "Unwritten rules of the community",
            "There's a whole hierarchy system",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_SIGNAL,
        marker_type=LinguisticMarkerType.RECOGNITION_PROTOCOL,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.98,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="signal_joined_cult",
        pattern_text="Joined a cult (positive)",
        pattern_regex=r"(joined a cult|have i joined|one of us|you.?re one of us now|tesla smile)",
        examples=[
            "Have I joined a cult? Maybe",
            "It's basically a cult and I love it",
            "You're one of us now",
            "The Tesla smile is real",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_SIGNAL,
        marker_type=LinguisticMarkerType.RECOGNITION_PROTOCOL,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.98,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="signal_jeep_ducking",
        pattern_text="Jeep Ducking / tribal gestures",
        pattern_regex=r"(jeep duck|rubber duck|thoughtful.*gesture|owner.*owner|between.*drivers)",
        examples=[
            "Jeep Ducking is such a kind gesture",
            "Placing a rubber duck on another Jeep",
            "That wave between Wrangler drivers",
        ],
        relationship_type=RelationshipTypeId.TRIBAL_SIGNAL,
        marker_type=LinguisticMarkerType.RECOGNITION_PROTOCOL,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.98,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: INHERITED LEGACY PATTERNS
# Generational brand loyalty
# =============================================================================

INHERITED_LEGACY_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="legacy_father_drove",
        pattern_text="What my father drove/used",
        pattern_regex=r"(my (father|dad|grandfather|grandpa).*(drove|used|taught)|family were .+ guys|proud of what .+ drove)",
        examples=[
            "My family were Chevy guys",
            "Proud of what my father drove",
            "My dad taught me to use this brand",
        ],
        relationship_type=RelationshipTypeId.INHERITED_LEGACY,
        marker_type=LinguisticMarkerType.GENERATIONAL,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.95,
        },
    ),
    LanguagePattern(
        pattern_id="legacy_passed_down",
        pattern_text="Passed down / inherited",
        pattern_regex=r"(passed down|inherited|from my (granny|grandma|mother)|three generations|family heirloom)",
        examples=[
            "This pot was passed down from my granny",
            "Three generations have used this",
            "It's a family heirloom now",
        ],
        relationship_type=RelationshipTypeId.INHERITED_LEGACY,
        marker_type=LinguisticMarkerType.GENERATIONAL,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.95,
        },
    ),
    LanguagePattern(
        pattern_id="legacy_reminded_grandpa",
        pattern_text="Reminded me of grandpa",
        pattern_regex=r"(reminded me of my (grandpa|grandma|dad)|same memory|like my (mom|dad) used|buying one for my)",
        examples=[
            "It reminded me so much of my grandpa",
            "Just like my mom used to use",
            "Bought one for my mom for the same memory",
        ],
        relationship_type=RelationshipTypeId.INHERITED_LEGACY,
        marker_type=LinguisticMarkerType.GENERATIONAL,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: IDENTITY NEGATION PATTERNS
# Anti-consumption defining who you're NOT
# =============================================================================

IDENTITY_NEGATION_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="negation_refuse",
        pattern_text="Refuse to buy / won't support",
        pattern_regex=r"(refuse to buy|won.?t support|boycott|against consumerism|mindless consumer|conscious consumer)",
        examples=[
            "I refuse to buy from them",
            "Turned from mindless to conscious consumer",
            "Won't support that kind of company",
        ],
        relationship_type=RelationshipTypeId.IDENTITY_NEGATION,
        marker_type=LinguisticMarkerType.ANTI_CONSUMPTION,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.75,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="negation_own_you",
        pattern_text="Things own you / anti-stuff",
        pattern_regex=r"(things.*own you|own.*end up owning|anti.?consumption|minimalist|reject.* consumerism)",
        examples=[
            "The things you own end up owning you",
            "I've become an anti-consumer",
            "Rejecting mainstream consumerism",
        ],
        relationship_type=RelationshipTypeId.IDENTITY_NEGATION,
        marker_type=LinguisticMarkerType.ANTI_CONSUMPTION,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.70,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.95,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: WORKSPACE CULTURE PATTERNS
# Team/org identity through shared tools
# =============================================================================

WORKSPACE_CULTURE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="workspace_live_off",
        pattern_text="We live off [tool]",
        pattern_regex=r"(we live off|we run on|our team uses|company.wide|changed how we work|entire org)",
        examples=[
            "We live off Slack and Notion",
            "Our entire team runs on this",
            "Changed how we work as an organization",
        ],
        relationship_type=RelationshipTypeId.WORKSPACE_CULTURE,
        marker_type=LinguisticMarkerType.TEAM_CULTURE,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.82,
            ObservationChannel.SELF_EXPRESSION: 0.78,
        },
    ),
    LanguagePattern(
        pattern_id="workspace_future_of_work",
        pattern_text="Future way of working",
        pattern_regex=r"(future.* of working|way we collaborate|team culture|how we work|work together)",
        examples=[
            "The future way of working",
            "Defines our team culture",
            "Changed how we collaborate",
        ],
        relationship_type=RelationshipTypeId.WORKSPACE_CULTURE,
        marker_type=LinguisticMarkerType.TEAM_CULTURE,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.75,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: GRAIL QUEST PATTERNS
# Holy grail product pursuit
# =============================================================================

GRAIL_QUEST_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="grail_holy",
        pattern_text="Holy grail / HG",
        pattern_regex=r"(holy grail|hg|grail watch|grail (product|item)|the one i.?ve been|my grail)",
        examples=[
            "This is my holy grail",
            "Finally found my grail watch",
            "The HG I've been searching for",
        ],
        relationship_type=RelationshipTypeId.GRAIL_QUEST,
        marker_type=LinguisticMarkerType.GRAIL_PURSUIT,
        base_weight=0.95,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
    LanguagePattern(
        pattern_id="grail_endgame",
        pattern_text="Endgame / the one",
        pattern_regex=r"(endgame|end.?game|the one|finally (found|attained)|sweet relief|bug leaving)",
        examples=[
            "This is my endgame",
            "Finally attained my grail",
            "Felt the sweet relief of the bug leaving me",
        ],
        relationship_type=RelationshipTypeId.GRAIL_QUEST,
        marker_type=LinguisticMarkerType.GRAIL_PURSUIT,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="grail_hunting",
        pattern_text="Hunting / searching for",
        pattern_regex=r"(hunting for|searching for years|elusive|never obtain|scarcity|finally got my hands)",
        examples=[
            "Been hunting for this for years",
            "An elusive grail I may never obtain",
            "Finally got my hands on one",
        ],
        relationship_type=RelationshipTypeId.GRAIL_QUEST,
        marker_type=LinguisticMarkerType.GRAIL_PURSUIT,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: COMPLETION SEEKER PATTERNS
# Project Pan - relationship through finishing
# =============================================================================

COMPLETION_SEEKER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="completion_panned",
        pattern_text="Panned / finished / emptied",
        pattern_regex=r"(panned|finished|emptied|used up|hit pan|see the progress|project pan)",
        examples=[
            "Finally panned this product",
            "So satisfying to see the progress",
            "Part of my project pan",
        ],
        relationship_type=RelationshipTypeId.COMPLETION_SEEKER,
        marker_type=LinguisticMarkerType.COMPLETION_DRIVE,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="completion_accomplished",
        pattern_text="Feel accomplished / satisfying",
        pattern_regex=r"(feel.*accomplished|so satisfying|know.*better when you use it|over.?consuming|mindful)",
        examples=[
            "I feel like I've accomplished something",
            "So satisfying to actually finish",
            "Makes me realize how much we over-consume",
        ],
        relationship_type=RelationshipTypeId.COMPLETION_SEEKER,
        marker_type=LinguisticMarkerType.COMPLETION_DRIVE,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.90,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: FINANCIAL INTIMATE PATTERNS
# Trust with sensitive financial data
# =============================================================================

FINANCIAL_INTIMATE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="financial_trust_money",
        pattern_text="Trust with my money / accounts",
        pattern_regex=r"(trust.*with my (money|accounts|data)|sensitive data|financial|couldn.?t trust any other|security)",
        examples=[
            "I trust them with my money",
            "Couldn't trust any other company",
            "They have access to all my financial data",
        ],
        relationship_type=RelationshipTypeId.FINANCIAL_INTIMATE,
        marker_type=LinguisticMarkerType.FINANCIAL_TRUST,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.75,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="financial_large_amount",
        pattern_text="Large amount of accounts / data",
        pattern_regex=r"(large amount of|all my accounts|connected everything|full picture|complete access)",
        examples=[
            "Due to my large amount of accounts",
            "They have the full picture of my finances",
            "Connected everything to them",
        ],
        relationship_type=RelationshipTypeId.FINANCIAL_INTIMATE,
        marker_type=LinguisticMarkerType.FINANCIAL_TRUST,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.70,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: THERAPIST PROVIDER PATTERNS
# Service provider as emotional confidant
# =============================================================================

THERAPIST_PROVIDER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="therapist_decades",
        pattern_text="Same person for decades",
        pattern_regex=r"(same .+ (since|for) .+ years|decades|since i was|growing up|28 years|passed away)",
        examples=[
            "Been getting cut by the same guy since 8th grade",
            "Same stylist for 28 years until she passed",
            "Known them since I was a kid",
        ],
        relationship_type=RelationshipTypeId.THERAPIST_PROVIDER,
        marker_type=LinguisticMarkerType.EMOTIONAL_CONFIDANT,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="therapist_nice_when",
        pattern_text="Nice to me when [life event]",
        pattern_regex=r"(nice to me when|there for me|relationship ended|divorce|breakup|like therapy|tell .+ everything)",
        examples=[
            "Super nice when my relationship ended",
            "Been there for me through everything",
            "It's like therapy honestly",
        ],
        relationship_type=RelationshipTypeId.THERAPIST_PROVIDER,
        marker_type=LinguisticMarkerType.EMOTIONAL_CONFIDANT,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.95,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: INSIDER COMPACT PATTERNS
# IYKYK gatekeeping dynamics
# =============================================================================

INSIDER_COMPACT_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="insider_iykyk",
        pattern_text="IYKYK / if you know",
        pattern_regex=r"(iykyk|if you know|not for everyone|prove yourself|gatekeep|snobbery|let.* in)",
        examples=[
            "IYKYK",
            "Not for everyone, you have to prove yourself",
            "Part of the appeal is the gatekeeping",
        ],
        relationship_type=RelationshipTypeId.INSIDER_COMPACT,
        marker_type=LinguisticMarkerType.GATEKEEPING,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="insider_cult_following",
        pattern_text="Cult following / underground",
        pattern_regex=r"(cult following|underground|quietly built|hunt .+ down|trade (repair )? tips|forum)",
        examples=[
            "It's quietly built a cult following",
            "Owners hunt them down on eBay",
            "We trade tips on forums",
        ],
        relationship_type=RelationshipTypeId.INSIDER_COMPACT,
        marker_type=LinguisticMarkerType.GATEKEEPING,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="insider_pretension",
        pattern_text="Pretension / expertise",
        pattern_regex=r"(pretension|confidence.?to.?competence|differentiate|taste the difference|connoisseur)",
        examples=[
            "Oozing with pretension, but in a good way",
            "If you can differentiate, you get it",
            "A community of true connoisseurs",
        ],
        relationship_type=RelationshipTypeId.INSIDER_COMPACT,
        marker_type=LinguisticMarkerType.GATEKEEPING,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.80,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: CO-CREATOR PATTERNS
# Glossier model - active partner in brand
# =============================================================================

CO_CREATOR_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="cocreator_community_created",
        pattern_text="Community created / we built",
        pattern_regex=r"(community created|we built|our input|listened to us|created by .+ community|open thread)",
        examples=[
            "This product was created by the community",
            "They actually listened to our input",
            "We built this together",
        ],
        relationship_type=RelationshipTypeId.CO_CREATOR,
        marker_type=LinguisticMarkerType.CO_CREATION,
        base_weight=0.92,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="cocreator_like_friend",
        pattern_text="Like a friend, not corporation",
        pattern_regex=r"(like a friend|not a corporation|empower.*consumer|feel.*affiliation|part of .+ story)",
        examples=[
            "Feels like a friend, not a corporation",
            "They empower me as a consumer",
            "I feel like part of their story",
        ],
        relationship_type=RelationshipTypeId.CO_CREATOR,
        marker_type=LinguisticMarkerType.CO_CREATION,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: ETHICAL VALIDATOR PATTERNS
# Moral permission through purchase
# =============================================================================

ETHICAL_VALIDATOR_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="ethical_feel_good",
        pattern_text="Feel good about purchase",
        pattern_regex=r"(feel good|guilt.?free|values reflected|conscious spending|ethical|sustainable|no guilt)",
        examples=[
            "I feel good about buying from them",
            "Guilt-free purchase",
            "My values are reflected in their practices",
        ],
        relationship_type=RelationshipTypeId.ETHICAL_VALIDATOR,
        marker_type=LinguisticMarkerType.ETHICAL_PERMISSION,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.92,
        },
    ),
    LanguagePattern(
        pattern_id="ethical_keep_coming_back",
        pattern_text="Keep coming back because values",
        pattern_regex=r"(keep coming back|values aligned|repair.* reuse|worn wear|conscious choice|responsible)",
        examples=[
            "I keep coming back because of their values",
            "Repair and reuse mentality",
            "A responsible, conscious choice",
        ],
        relationship_type=RelationshipTypeId.ETHICAL_VALIDATOR,
        marker_type=LinguisticMarkerType.ETHICAL_PERMISSION,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.88,
            ObservationChannel.SOCIAL_SIGNALS: 0.85,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: STATUS ARBITER PATTERNS
# Access to otherwise unavailable social spheres
# =============================================================================

STATUS_ARBITER_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="arbiter_access",
        pattern_text="Access / getting your hands on",
        pattern_regex=r"(getting your hands|iron throne|loyal customer|secondary market|exclusive|tier|vip)",
        examples=[
            "Getting your hands on one is like the Iron Throne",
            "Unless you're a loyal customer, forget it",
            "Had to get it on the secondary market",
        ],
        relationship_type=RelationshipTypeId.STATUS_ARBITER,
        marker_type=LinguisticMarkerType.ACCESS_PROVIDER,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.85,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.82,
        },
    ),
    LanguagePattern(
        pattern_id="arbiter_climb_ladder",
        pattern_text="Climb the ladder / tiers",
        pattern_regex=r"(climb the (ladder|tiers)|beauty insider|rouge|diamond|platinum|elite|inner circle)",
        examples=[
            "Climbing the beauty ladder",
            "Finally made it to Rouge status",
            "Part of the inner circle now",
        ],
        relationship_type=RelationshipTypeId.STATUS_ARBITER,
        marker_type=LinguisticMarkerType.ACCESS_PROVIDER,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.82,
            ObservationChannel.SOCIAL_SIGNALS: 0.92,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: COMPETENCE VALIDATOR PATTERNS
# Confirms consumer made smart choice
# =============================================================================

COMPETENCE_VALIDATOR_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="competence_research",
        pattern_text="Research proved / BIFL",
        pattern_regex=r"(research proved|extensive research|buy it for life|bifl|smart choice|did my homework)",
        examples=[
            "Extensive research led me here",
            "A true BIFL purchase",
            "Did my homework and chose right",
        ],
        relationship_type=RelationshipTypeId.COMPETENCE_VALIDATOR,
        marker_type=LinguisticMarkerType.SMART_CHOICE,
        base_weight=0.85,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.92,
            ObservationChannel.SOCIAL_SIGNALS: 0.78,
            ObservationChannel.SELF_EXPRESSION: 0.85,
        },
    ),
    LanguagePattern(
        pattern_id="competence_prove_wrong",
        pattern_text="Prove others wrong / superior",
        pattern_regex=r"(prove.*wrong|superior|toughest i.?ve|good quality|posting.*opinion|people talking about)",
        examples=[
            "Posting this to prove people wrong",
            "The toughest I've ever used",
            "Superior to what everyone says",
        ],
        relationship_type=RelationshipTypeId.COMPETENCE_VALIDATOR,
        marker_type=LinguisticMarkerType.SMART_CHOICE,
        base_weight=0.82,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.90,
            ObservationChannel.SOCIAL_SIGNALS: 0.80,
            ObservationChannel.SELF_EXPRESSION: 0.78,
        },
    ),
]


# =============================================================================
# FOURNIER EXTENSION: IRONIC AWARE PATTERNS
# r/HailCorporate - critical distance while engaging
# =============================================================================

IRONIC_AWARE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        pattern_id="ironic_walking_ad",
        pattern_text="Walking ad / brainwashed",
        pattern_regex=r"(walking ad|brainwashed|shill|hailcorporate|unpaid.*advertisement|unknowing|acts as an ad)",
        examples=[
            "I know I'm a walking advertisement",
            "Basically brainwashed but aware",
            "Acting as an unknowing shill",
        ],
        relationship_type=RelationshipTypeId.IRONIC_AWARE,
        marker_type=LinguisticMarkerType.META_AWARENESS,
        base_weight=0.90,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.75,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.88,
        },
    ),
    LanguagePattern(
        pattern_id="ironic_permeated",
        pattern_text="Culture has permeated",
        pattern_regex=r"(permeated|popular culture|inured|don.?t even know|meta|ironic.*(but|and)|self.?aware)",
        examples=[
            "Pop culture has permeated so deeply",
            "We don't even know we're advertising",
            "Ironic but here I am",
        ],
        relationship_type=RelationshipTypeId.IRONIC_AWARE,
        marker_type=LinguisticMarkerType.META_AWARENESS,
        base_weight=0.88,
        channel_weights={
            ObservationChannel.CUSTOMER_REVIEWS: 0.70,
            ObservationChannel.SOCIAL_SIGNALS: 0.95,
            ObservationChannel.SELF_EXPRESSION: 0.90,
        },
    ),
]


# =============================================================================
# ALL PATTERNS REGISTRY
# =============================================================================

ALL_PATTERNS: List[LanguagePattern] = (
    SELF_IDENTITY_PATTERNS +
    SELF_EXPRESSION_PATTERNS +
    STATUS_MARKER_PATTERNS +
    TRIBAL_BADGE_PATTERNS +
    COMMITTED_PARTNERSHIP_PATTERNS +
    DEPENDENCY_PATTERNS +
    RELIABLE_TOOL_PATTERNS +
    MENTOR_PATTERNS +
    CHILDHOOD_FRIEND_PATTERNS +
    ENEMY_PATTERNS +
    COMFORT_COMPANION_PATTERNS +
    ASPIRATIONAL_ICON_PATTERNS +
    # FIRST EXPANSION PATTERNS
    CHAMPION_EVANGELIST_PATTERNS +
    GUILTY_PLEASURE_PATTERNS +
    RESCUE_SAVIOR_PATTERNS +
    COURTSHIP_DATING_PATTERNS +
    REBOUND_RELATIONSHIP_PATTERNS +
    CAPTIVE_ENSLAVEMENT_PATTERNS +
    RELUCTANT_USER_PATTERNS +
    SOCIAL_COMPLIANCE_PATTERNS +
    COMPARTMENTALIZED_IDENTITY_PATTERNS +
    SEASONAL_REKINDLER_PATTERNS +
    # FOURNIER EXTENSION PATTERNS (24 New Types)
    ACCOUNTABILITY_CAPTOR_PATTERNS +
    SUBSCRIPTION_CONSCIENCE_PATTERNS +
    SACRED_PRACTICE_PATTERNS +
    TEMPORAL_MARKER_PATTERNS +
    MOURNING_BOND_PATTERNS +
    FORMULA_BETRAYAL_PATTERNS +
    LIFE_RAFT_PATTERNS +
    TRANSFORMATION_AGENT_PATTERNS +
    SECOND_BRAIN_PATTERNS +
    PLATFORM_LOCKIN_PATTERNS +
    TRIBAL_SIGNAL_PATTERNS +
    INHERITED_LEGACY_PATTERNS +
    IDENTITY_NEGATION_PATTERNS +
    WORKSPACE_CULTURE_PATTERNS +
    GRAIL_QUEST_PATTERNS +
    COMPLETION_SEEKER_PATTERNS +
    FINANCIAL_INTIMATE_PATTERNS +
    THERAPIST_PROVIDER_PATTERNS +
    INSIDER_COMPACT_PATTERNS +
    CO_CREATOR_PATTERNS +
    ETHICAL_VALIDATOR_PATTERNS +
    STATUS_ARBITER_PATTERNS +
    COMPETENCE_VALIDATOR_PATTERNS +
    IRONIC_AWARE_PATTERNS
)

# Pattern lookup by ID
PATTERN_BY_ID: Dict[str, LanguagePattern] = {
    pattern.pattern_id: pattern for pattern in ALL_PATTERNS
}

# Patterns grouped by relationship type
PATTERNS_BY_RELATIONSHIP: Dict[RelationshipTypeId, List[LanguagePattern]] = {}
for pattern in ALL_PATTERNS:
    if pattern.relationship_type not in PATTERNS_BY_RELATIONSHIP:
        PATTERNS_BY_RELATIONSHIP[pattern.relationship_type] = []
    PATTERNS_BY_RELATIONSHIP[pattern.relationship_type].append(pattern)
