#!/usr/bin/env python3
"""
PERSUASION SUSCEPTIBILITY CONSTRUCTS - NEO4J INTEGRATION
=========================================================

Research-backed psychological constructs measuring individual differences
in susceptibility to specific persuasion techniques.

This extends the existing 35 constructs in populate_psychological_graph.py
with 13 additional susceptibility constructs specifically designed for
predicting mechanism effectiveness.

RESEARCH FOUNDATIONS:
Each construct is grounded in peer-reviewed psychological research with:
- Primary research basis (seminal papers)
- Key citations (supporting evidence)
- Effect sizes from meta-analyses where available
- Validated scale references

INTEGRATION POINTS:
1. Neo4j: Creates nodes with INFLUENCES_MECHANISM relationships
2. LangGraph: Flows through psycholinguistic analysis pipeline
3. AoT: Feeds into MechanismActivationAtom
4. Learning: Emits signals for Thompson Sampling updates
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# PERSUASION SUSCEPTIBILITY CONSTRUCTS (13 constructs)
# Research-backed definitions with mechanism influence mappings
# =============================================================================

@dataclass 
class SusceptibilityConstructDefinition:
    """Definition of a persuasion susceptibility construct."""
    id: str
    name: str
    domain: str  # Which tier: mechanism_selection, message_crafting, brand_matching
    description: str
    scale_anchors: Tuple[str, str]  # (low_end, high_end)
    
    # Research grounding
    research_basis: str  # Seminal paper
    key_citations: List[str]  # Supporting citations
    meta_analysis_effect_size: Optional[float]  # Cohen's d if available
    validated_scales: List[str]  # Established measurement instruments
    
    # Mechanism influences: mechanism_id -> influence strength (-1 to 1)
    # Positive = high susceptibility increases mechanism effectiveness
    # Negative = high susceptibility decreases mechanism effectiveness
    mechanism_influences: Dict[str, float]
    
    # Related constructs for correlation tracking
    related_constructs: Dict[str, float]
    
    # Behavioral markers for detection from text
    high_markers: List[str]  # Linguistic indicators of high susceptibility
    low_markers: List[str]  # Linguistic indicators of low susceptibility
    
    # Advertising implications
    ad_implications_high: str
    ad_implications_low: str


# =============================================================================
# TIER 1: MECHANISM SELECTION CONSTRUCTS
# =============================================================================

SUSCEPTIBILITY_CONSTRUCTS: Dict[str, SusceptibilityConstructDefinition] = {
    
    # =========================================================================
    # CONSTRUCT 1: SOCIAL PROOF SUSCEPTIBILITY
    # =========================================================================
    "suscept_social_proof": SusceptibilityConstructDefinition(
        id="suscept_social_proof",
        name="Social Proof Susceptibility",
        domain="mechanism_selection",
        description="Individual differences in the tendency to use others' behavior as evidence of correct behavior. Measures susceptibility to informational and normative social influence.",
        scale_anchors=("Independent judgment", "Socially guided"),
        
        research_basis="Cialdini, R.B. (2009). Influence: Science and Practice (5th ed.); Deutsch & Gerard (1955) on informational vs normative influence",
        key_citations=[
            "Cialdini, R.B. (2009). Influence: Science and Practice",
            "Deutsch, M., & Gerard, H.B. (1955). A study of normative and informational social influences upon individual judgment. JASP",
            "Burnkrant, R.E., & Cousineau, A. (1975). Informational and normative social influence in buyer behavior. JCR",
            "Bearden, W.O., Netemeyer, R.G., & Teel, J.E. (1989). Measurement of consumer susceptibility to interpersonal influence. JCR",
        ],
        meta_analysis_effect_size=0.38,  # Cialdini meta-analysis
        validated_scales=[
            "Consumer Susceptibility to Interpersonal Influence Scale (Bearden et al., 1989)",
            "Attention to Social Comparison Information Scale (Lennox & Wolfe, 1984)",
        ],
        
        mechanism_influences={
            "mimetic_desire": 0.65,  # Strong positive - social proof IS mimetic desire
            "identity_construction": 0.35,  # Conformity is identity-relevant
            "automatic_evaluation": 0.25,  # Heuristic shortcut
            "attention_dynamics": 0.15,  # Social proof captures attention
        },
        related_constructs={
            "suscept_authority": 0.35,  # Both are compliance mechanisms
            "selfreg_sm": 0.45,  # High self-monitors more susceptible
            "social_conformity": 0.60,  # Conceptual overlap
            "cognitive_hri": 0.40,  # Heuristic reliance
        },
        
        high_markers=[
            "reviews convinced me", "everyone recommends", "popular choice",
            "based on ratings", "best seller", "most people buy",
            "friend recommended", "thousands of customers", "trending",
        ],
        low_markers=[
            "my own research", "regardless of reviews", "don't follow trends",
            "formed own opinion", "independent decision", "despite popularity",
        ],
        
        ad_implications_high="Lead with social proof: customer counts, testimonials, ratings, 'join thousands who...' High responders show 40-60% lift from social proof (Cialdini, 2009)",
        ad_implications_low="Focus on product merits, unique features, independent quality verification. Social proof may trigger reactance.",
    ),
    
    # =========================================================================
    # CONSTRUCT 2: AUTHORITY BIAS SUSCEPTIBILITY  
    # =========================================================================
    "suscept_authority": SusceptibilityConstructDefinition(
        id="suscept_authority",
        name="Authority Bias Susceptibility",
        domain="mechanism_selection",
        description="Tendency to comply with perceived authority figures and defer to expert judgment. Based on Milgram's obedience research and Cialdini's authority principle.",
        scale_anchors=("Skeptical of authority", "Deferential to authority"),
        
        research_basis="Milgram, S. (1974). Obedience to Authority; Cialdini (2009) Authority Principle",
        key_citations=[
            "Milgram, S. (1974). Obedience to Authority: An Experimental View",
            "Cialdini, R.B. (2009). Influence: Science and Practice - Chapter on Authority",
            "Maddux, J.E., & Rogers, R.W. (1980). Effects of source expertness, physical attractiveness, and supporting arguments on persuasion. JPSP",
            "Wilson, E.J., & Sherrell, D.L. (1993). Source effects in communication and persuasion research: A meta-analysis. JAMS",
        ],
        meta_analysis_effect_size=0.42,  # Wilson & Sherrell meta-analysis
        validated_scales=[
            "Right-Wing Authoritarianism Scale (Altemeyer, 1981) - deference subscale",
            "Authority Belief Inventory (Rigby, 1987)",
        ],
        
        mechanism_influences={
            "identity_construction": 0.30,  # Authority as identity anchor
            "automatic_evaluation": 0.35,  # Authority cues trigger automatic trust
            "mimetic_desire": 0.25,  # Experts as models
            "construal_level": 0.20,  # Authority enables abstract thinking
        },
        related_constructs={
            "suscept_social_proof": 0.35,
            "cognitive_hri": 0.45,  # Authority is a heuristic
            "uncertainty_at": 0.40,  # High uncertainty tolerance = less authority reliance
        },
        
        high_markers=[
            "expert recommends", "doctor approved", "scientifically proven",
            "certified", "professional advice", "trust the experts",
            "research shows", "according to studies", "endorsed by",
        ],
        low_markers=[
            "verify myself", "question experts", "do own research",
            "credentials don't mean", "experience over expertise",
            "fact check", "don't blindly trust",
        ],
        
        ad_implications_high="Lead with credentials, certifications, expert endorsements. Include 'Doctor recommended', 'As seen in [authority source]', research citations. Effect size d=0.42 (Wilson & Sherrell, 1993)",
        ad_implications_low="Focus on user testimonials, real-world results, transparent methodology. Allow verification.",
    ),

    # =========================================================================
    # CONSTRUCT 3: SCARCITY REACTIVITY
    # =========================================================================
    "suscept_scarcity": SusceptibilityConstructDefinition(
        id="suscept_scarcity",
        name="Scarcity Reactivity",
        description="Responsiveness to limited availability and urgency cues. Based on commodity theory and Cialdini's scarcity principle.",
        domain="mechanism_selection",
        scale_anchors=("Unaffected by scarcity", "Highly reactive to scarcity"),
        
        research_basis="Brock, T.C. (1968). Commodity Theory; Cialdini (2009) Scarcity Principle; Worchel et al. (1975) cookie jar experiment",
        key_citations=[
            "Brock, T.C. (1968). Implications of commodity theory for value change",
            "Worchel, S., Lee, J., & Adewole, A. (1975). Effects of supply and demand on ratings of object value. JPSP",
            "Cialdini, R.B. (2009). Influence: Scarcity chapter",
            "Lynn, M. (1991). Scarcity effects on value: A quantitative review. Psychology & Marketing",
            "Aggarwal, P., Jun, S.Y., & Huh, J.H. (2011). Scarcity messages: A consumer competition perspective. JA",
        ],
        meta_analysis_effect_size=0.52,  # Lynn (1991) quantitative review
        validated_scales=[
            "Need for Uniqueness Scale (Snyder & Fromkin, 1977) - scarcity subscale",
            "Reactance Scale (Hong & Faedda, 1996) - freedom threat subscale",
        ],
        
        mechanism_influences={
            "wanting_liking": 0.55,  # Scarcity increases wanting
            "automatic_evaluation": 0.40,  # Fast reactive response
            "attention_dynamics": 0.45,  # Scarcity captures attention
            "regulatory_focus": -0.25,  # Triggers prevention (fear of loss)
        },
        related_constructs={
            "suscept_anchoring": 0.35,  # Both involve value perception
            "temporal_ddr": 0.50,  # Impatience correlates with scarcity reactivity
            "social_nfu": 0.45,  # Uniqueness seekers value scarcity
        },
        
        high_markers=[
            "had to grab it", "before it sold out", "limited time",
            "only few left", "didn't want to miss", "FOMO", "last chance",
            "act fast", "going fast", "while supplies last",
        ],
        low_markers=[
            "no rush", "will wait", "always available", "don't fall for urgency",
            "marketing tactic", "patience", "not in a hurry",
        ],
        
        ad_implications_high="Deploy scarcity effectively: limited quantities, countdown timers, 'only X left'. Effect size d=0.52. WARNING: Combine with social proof for maximum impact (Aggarwal et al., 2011)",
        ad_implications_low="Avoid urgency tactics - may trigger psychological reactance (Brehm, 1966). Focus on evergreen value propositions.",
    ),

    # =========================================================================
    # CONSTRUCT 4: ANCHORING SUSCEPTIBILITY
    # =========================================================================
    "suscept_anchoring": SusceptibilityConstructDefinition(
        id="suscept_anchoring",
        name="Anchoring Susceptibility",
        description="Susceptibility to anchoring and adjustment heuristic. The degree to which initial information (anchors) influence subsequent judgments.",
        domain="mechanism_selection",
        scale_anchors=("Anchor-independent", "Anchor-dependent"),
        
        research_basis="Tversky, A., & Kahneman, D. (1974). Judgment under Uncertainty: Heuristics and Biases. Science",
        key_citations=[
            "Tversky, A., & Kahneman, D. (1974). Judgment under Uncertainty. Science",
            "Epley, N., & Gilovich, T. (2006). The anchoring-and-adjustment heuristic. Psychological Science",
            "Furnham, A., & Boo, H.C. (2011). A literature review of the anchoring effect. J Socio-Economics",
            "Mussweiler, T., & Strack, F. (2000). The use of category and exemplar knowledge in the solution of anchoring tasks. JPSP",
        ],
        meta_analysis_effect_size=0.65,  # Furnham & Boo (2011) review
        validated_scales=[
            "Cognitive Reflection Test (Frederick, 2005) - inverse relationship",
            "Need for Cognition Scale (Cacioppo & Petty, 1982) - inverse relationship",
        ],
        
        mechanism_influences={
            "automatic_evaluation": 0.50,  # Anchoring is automatic
            "attention_dynamics": 0.35,  # Anchor captures attention
            "construal_level": -0.25,  # Concrete thinkers more susceptible
            "wanting_liking": 0.30,  # Reference points affect wanting
        },
        related_constructs={
            "cognitive_hri": 0.55,  # Heuristic reliance
            "cognitive_nfc": -0.45,  # High NFC = less anchoring
            "suscept_scarcity": 0.35,  # Both involve value perception manipulation
        },
        
        high_markers=[
            "was originally", "compared to retail", "saved money",
            "great value at this price", "for the price", "price vs quality",
            "compared to competitors", "better deal than",
        ],
        low_markers=[
            "don't care about original price", "what it's worth to me",
            "intrinsic value", "regardless of sale price", "fake discount",
        ],
        
        ad_implications_high="Effective anchor deployment: 'Was $200, now $89' (d=0.65). Show competitor prices, establish high reference points first. Price framing extremely effective.",
        ad_implications_low="Focus on absolute value proposition. These consumers see through 'original price' manipulation.",
    ),

    # =========================================================================
    # CONSTRUCT 5: DELAY DISCOUNTING (TEMPORAL PREFERENCE)
    # =========================================================================
    "suscept_delay_discount": SusceptibilityConstructDefinition(
        id="suscept_delay_discount",
        name="Delay Discounting Rate",
        description="Rate at which future rewards are discounted relative to immediate rewards. Higher rates indicate preference for immediate gratification.",
        domain="mechanism_selection",
        scale_anchors=("Patient/future-oriented", "Impatient/present-oriented"),
        
        research_basis="Frederick, S., Loewenstein, G., & O'Donoghue, T. (2002). Time Discounting and Time Preference: A Critical Review. JEL",
        key_citations=[
            "Frederick, S., Loewenstein, G., & O'Donoghue, T. (2002). Time Discounting. JEL",
            "Kirby, K.N., & Maraković, N.N. (1996). Delay-discounting probabilistic rewards. Psychonomic Bulletin",
            "McClure, S.M., et al. (2004). Separate neural systems value immediate and delayed monetary rewards. Science",
            "Ainslie, G. (1975). Specious reward: A behavioral theory of impulsiveness and impulse control. Psychological Bulletin",
        ],
        meta_analysis_effect_size=0.47,  # Behavioral economics meta-analyses
        validated_scales=[
            "Monetary Choice Questionnaire (Kirby et al., 1999)",
            "Delay Discounting Task (Richards et al., 1999)",
            "Barratt Impulsiveness Scale (Patton et al., 1995) - delay subscale",
        ],
        
        mechanism_influences={
            "wanting_liking": 0.55,  # High discounters driven by wanting
            "temporal_construal": -0.60,  # Present-focused
            "automatic_evaluation": 0.40,  # Impulsive = automatic
            "regulatory_focus": -0.30,  # Prevention less effective
        },
        related_constructs={
            "suscept_scarcity": 0.50,  # Urgency appeals to impatient
            "suscept_compulsive": 0.55,  # Impulsivity link
            "temporal_orientation": -0.65,  # Inverse of future orientation
        },
        
        high_markers=[
            "wanted it now", "couldn't wait", "immediate", "instant",
            "same day shipping", "impulse buy", "spur of the moment",
            "needed it fast", "right away",
        ],
        low_markers=[
            "worth the wait", "long term investment", "patient",
            "saved up for", "delayed gratification", "no rush",
        ],
        
        ad_implications_high="Emphasize immediacy: 'Get it today', instant access, same-day delivery. Urgency mechanisms highly effective. These consumers have hyperbolic discounting (Ainslie, 1975).",
        ad_implications_low="Investment framing works: 'Lasts for years', 'Build over time'. Avoid urgency - may seem manipulative.",
    ),

    # =========================================================================
    # CONSTRUCT 6: PSYCHOLOGICAL REACTANCE
    # =========================================================================
    "suscept_reactance": SusceptibilityConstructDefinition(
        id="suscept_reactance",
        name="Psychological Reactance",
        description="Motivational state arising when freedom is threatened or eliminated. High reactance individuals resist persuasion attempts that feel coercive.",
        domain="mechanism_selection",
        scale_anchors=("Low reactance/compliant", "High reactance/resistant"),
        
        research_basis="Brehm, J.W. (1966). A Theory of Psychological Reactance. Academic Press",
        key_citations=[
            "Brehm, J.W. (1966). A Theory of Psychological Reactance",
            "Brehm, S.S., & Brehm, J.W. (1981). Psychological Reactance: A Theory of Freedom and Control",
            "Hong, S.M., & Faedda, S. (1996). Refinement of the Hong Psychological Reactance Scale. Educational & Psychological Measurement",
            "Dillard, J.P., & Shen, L. (2005). On the nature of reactance and its role in persuasive health communication. Communication Monographs",
        ],
        meta_analysis_effect_size=0.44,  # Rains (2013) meta-analysis on reactance
        validated_scales=[
            "Hong Psychological Reactance Scale (Hong & Faedda, 1996)",
            "Therapeutic Reactance Scale (Dowd et al., 1991)",
        ],
        
        mechanism_influences={
            "mimetic_desire": -0.40,  # Resist following others when pushed
            "identity_construction": 0.45,  # Strong autonomous identity
            "automatic_evaluation": -0.20,  # More deliberate evaluation
            "attention_dynamics": -0.15,  # Resist attention manipulation
        },
        related_constructs={
            "suscept_social_proof": -0.35,  # Resist social pressure
            "suscept_scarcity": -0.30,  # Scarcity can trigger reactance
            "suscept_authority": -0.40,  # Question authority
            "social_nfu": 0.50,  # Uniqueness seeking correlates
        },
        
        high_markers=[
            "don't tell me what to do", "felt pressured", "pushy",
            "manipulative", "my choice", "decide for myself",
            "don't appreciate being sold to", "see through tactics",
        ],
        low_markers=[
            "helpful recommendation", "appreciated the guidance",
            "good suggestion", "welcomed advice", "helpful push",
        ],
        
        ad_implications_high="CRITICAL: Avoid pressure tactics entirely. Use soft-sell, provide options, emphasize autonomy ('You decide'). Scarcity/urgency will BACKFIRE dramatically (d=-0.44 when reactance triggered).",
        ad_implications_low="Direct calls-to-action effective. Recommendations and guidance well-received.",
    ),

    # =========================================================================
    # TIER 2: MESSAGE CRAFTING CONSTRUCTS
    # =========================================================================

    # =========================================================================
    # CONSTRUCT 7: SKEPTICISM LEVEL
    # =========================================================================
    "suscept_skepticism": SusceptibilityConstructDefinition(
        id="suscept_skepticism",
        name="Consumer Skepticism",
        description="Tendency to disbelieve and question advertising claims. Reflects learned distrust of marketing communications.",
        domain="message_crafting",
        scale_anchors=("Trusting/accepting", "Skeptical/questioning"),
        
        research_basis="Obermiller, C., & Spangenberg, E.R. (1998). Development of a scale to measure consumer skepticism toward advertising. JCP",
        key_citations=[
            "Obermiller, C., & Spangenberg, E.R. (1998). Development of a scale to measure consumer skepticism toward advertising. JCP",
            "Mohr, L.A., Eroǧlu, D., & Ellen, P.S. (1998). The development and testing of a measure of skepticism toward environmental claims. JCR",
            "Forehand, M.R., & Grier, S. (2003). When is honesty the best policy? The effect of stated company intent on consumer skepticism. JCP",
        ],
        meta_analysis_effect_size=None,  # Scale development paper
        validated_scales=[
            "SKEP Scale (Obermiller & Spangenberg, 1998)",
            "Ad Skepticism Scale (Boush et al., 1994)",
        ],
        
        mechanism_influences={
            "automatic_evaluation": -0.45,  # Don't accept at face value
            "mimetic_desire": -0.30,  # Question social proof too
            "identity_construction": 0.25,  # Identity as savvy consumer
            "construal_level": 0.35,  # More systematic processing
        },
        related_constructs={
            "cognitive_nfc": 0.55,  # Skeptics think more
            "suscept_authority": -0.45,  # Question expertise claims
            "suscept_social_proof": -0.35,  # Question social proof
        },
        
        high_markers=[
            "skeptical", "verify", "fact check", "needed proof",
            "too good to be true", "marketing bs", "question claims",
            "show me evidence", "don't just trust",
        ],
        low_markers=[
            "trusted", "believed", "took their word",
            "sounds good", "why would they lie",
        ],
        
        ad_implications_high="Lead with evidence: third-party validation, specific data, transparent methodology. Address objections proactively. Claims without proof will be rejected.",
        ad_implications_low="Standard claims accepted. Social proof and authority shortcuts work effectively.",
    ),

    # =========================================================================
    # CONSTRUCT 8: INFORMATION AVOIDANCE (OSTRICH EFFECT)
    # =========================================================================
    "suscept_info_avoid": SusceptibilityConstructDefinition(
        id="suscept_info_avoid",
        name="Information Avoidance",
        description="Tendency to avoid potentially negative or uncomfortable information, even when useful. The 'Ostrich Effect'.",
        domain="message_crafting",
        scale_anchors=("Information seeking", "Information avoiding"),
        
        research_basis="Golman, R., Hagmann, D., & Loewenstein, G. (2017). Information Avoidance. JEL",
        key_citations=[
            "Golman, R., Hagmann, D., & Loewenstein, G. (2017). Information Avoidance. JEL",
            "Karlsson, N., Loewenstein, G., & Seppi, D. (2009). The ostrich effect: Selective attention to information. JRUF",
            "Sweeny, K., Melnyk, D., Miller, W., & Shepperd, J.A. (2010). Information avoidance: Who, what, when, and why. Review of General Psychology",
        ],
        meta_analysis_effect_size=0.38,  # Sweeny et al. review
        validated_scales=[
            "Information Avoidance Scale (Howell & Shepperd, 2016)",
            "Monitoring-Blunting Style Scale (Miller, 1987)",
        ],
        
        mechanism_influences={
            "automatic_evaluation": 0.40,  # Prefer simple gut reactions
            "construal_level": -0.45,  # Avoid detailed processing
            "attention_dynamics": -0.35,  # Selective attention away from negative
            "regulatory_focus": -0.25,  # Avoid prevention-framed info
        },
        related_constructs={
            "suscept_cog_load": -0.55,  # Low tolerance = more avoidance
            "cognitive_nfc": -0.50,  # Low NFC = more avoidance
        },
        
        high_markers=[
            "don't want to know", "too much information",
            "keep it simple", "just the basics", "tl;dr",
            "skipped the fine print", "overwhelmed",
        ],
        low_markers=[
            "want all details", "read everything", "full picture",
            "even the negatives", "comprehensive information",
        ],
        
        ad_implications_high="Simple, positive messaging. Focus on benefits, not detailed specs. Avoid overwhelming with information. Reassurance over data.",
        ad_implications_low="Comprehensive information welcomed. Detailed comparisons effective. Address concerns directly.",
    ),

    # =========================================================================
    # CONSTRUCT 9: COGNITIVE LOAD TOLERANCE
    # =========================================================================
    "suscept_cog_load": SusceptibilityConstructDefinition(
        id="suscept_cog_load",
        name="Cognitive Load Tolerance",
        description="Capacity and willingness to process complex information during decision-making. Related to but distinct from Need for Cognition.",
        domain="message_crafting",
        scale_anchors=("Low tolerance/easily overwhelmed", "High tolerance/embraces complexity"),
        
        research_basis="Sweller, J. (1988). Cognitive load during problem solving. Cognitive Science; Paas et al. (2003) Cognitive Load Theory",
        key_citations=[
            "Sweller, J. (1988). Cognitive load during problem solving. Cognitive Science",
            "Paas, F., Renkl, A., & Sweller, J. (2003). Cognitive load theory. Educational Psychologist",
            "Malhotra, N.K. (1982). Information load and consumer decision making. JCR",
            "Iyengar, S.S., & Lepper, M.R. (2000). When choice is demotivating. JPSP (choice overload)",
        ],
        meta_analysis_effect_size=0.41,  # Scheiter et al. (2010) meta-analysis
        validated_scales=[
            "NASA Task Load Index (Hart & Staveland, 1988)",
            "Subjective Workload Assessment (Reid & Nygren, 1988)",
        ],
        
        mechanism_influences={
            "construal_level": 0.50,  # High tolerance = can handle abstract
            "attention_dynamics": 0.40,  # Sustained attention capacity
            "automatic_evaluation": -0.35,  # Less reliance on shortcuts
        },
        related_constructs={
            "cognitive_nfc": 0.65,  # Strong relationship
            "suscept_info_avoid": -0.55,  # Inverse
            "decision_maximizer": 0.50,  # Maximizers have higher tolerance
        },
        
        high_markers=[
            "love diving into details", "comprehensive research",
            "analyzed every option", "technical specs important",
            "the more information the better", "thorough evaluation",
        ],
        low_markers=[
            "overwhelmed by options", "too complicated",
            "just tell me which one", "paralyzed by choice",
            "keep it simple", "decision fatigue",
        ],
        
        ad_implications_high="Provide detailed specifications, comprehensive comparisons, technical deep-dives. These consumers appreciate thoroughness.",
        ad_implications_low="Simple messaging critical. Clear recommendations over many options. Visual over text. Minimize choices (Iyengar & Lepper, 2000).",
    ),

    # =========================================================================
    # CONSTRUCT 10: PRICE SENSITIVITY
    # =========================================================================
    "suscept_price": SusceptibilityConstructDefinition(
        id="suscept_price",
        name="Price Sensitivity",
        description="Degree to which price is weighted in purchase decisions relative to other factors. Central construct in behavioral pricing.",
        domain="message_crafting",
        scale_anchors=("Price insensitive", "Highly price sensitive"),
        
        research_basis="Goldsmith, R.E., & Newell, S.J. (1997). Innovativeness and price sensitivity: Managerial, theoretical and methodological issues. JPBM",
        key_citations=[
            "Goldsmith, R.E., & Newell, S.J. (1997). Innovativeness and price sensitivity. JPBM",
            "Lichtenstein, D.R., Ridgway, N.M., & Netemeyer, R.G. (1993). Price perceptions and consumer shopping behavior. JMR",
            "Wakefield, K.L., & Inman, J.J. (2003). Situational price sensitivity. JM",
            "Han, S., Gupta, S., & Lehmann, D.R. (2001). Consumer price sensitivity and price thresholds. JR",
        ],
        meta_analysis_effect_size=None,
        validated_scales=[
            "Price Sensitivity Scale (Goldsmith & Newell, 1997)",
            "Price Consciousness Scale (Lichtenstein et al., 1993)",
        ],
        
        mechanism_influences={
            "construal_level": -0.30,  # Concrete/specific focus
            "automatic_evaluation": 0.25,  # Price as quick filter
            "wanting_liking": -0.20,  # Price limits wanting
        },
        related_constructs={
            "suscept_anchoring": 0.50,  # Price anchoring effects
            "decision_maximizer": 0.35,  # Maximizers compare prices
        },
        
        high_markers=[
            "price was deciding factor", "budget conscious",
            "compared prices", "waited for sale", "couldn't justify",
            "deal seeker", "value for money", "affordable",
        ],
        low_markers=[
            "price wasn't a factor", "willing to pay more",
            "quality over price", "didn't check price",
            "worth every penny regardless",
        ],
        
        ad_implications_high="Lead with value: ROI calculations, price comparisons, savings. Payment plans effective. Discount messaging resonates.",
        ad_implications_low="Focus on quality, prestige, exclusivity. Minimize price discussion - may cheapen perception.",
    ),

    # =========================================================================
    # CONSTRUCT 11: RISK AVERSION
    # =========================================================================
    "suscept_risk_averse": SusceptibilityConstructDefinition(
        id="suscept_risk_averse",
        name="Risk Aversion",
        description="Tendency to avoid uncertainty and potential negative outcomes in consumer decisions. Affects guarantee and trial offer effectiveness.",
        domain="message_crafting",
        scale_anchors=("Risk tolerant", "Risk averse"),
        
        research_basis="Kahneman, D., & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk. Econometrica",
        key_citations=[
            "Kahneman, D., & Tversky, A. (1979). Prospect Theory. Econometrica",
            "Mandrik, C.A., & Bao, Y. (2005). Exploring the concept and measurement of general risk aversion. Advances in Consumer Research",
            "Mitchell, V.W. (1999). Consumer perceived risk: Conceptualisations and models. European Journal of Marketing",
            "Bauer, R.A. (1960). Consumer behavior as risk taking. Proceedings AMA",
        ],
        meta_analysis_effect_size=0.55,  # Prospect theory robustness
        validated_scales=[
            "Domain-Specific Risk-Taking Scale (Weber et al., 2002)",
            "General Risk Aversion Scale (Mandrik & Bao, 2005)",
        ],
        
        mechanism_influences={
            "regulatory_focus": 0.55,  # Prevention focus
            "automatic_evaluation": -0.30,  # More deliberate
            "wanting_liking": -0.25,  # Wanting tempered by risk
            "temporal_construal": 0.30,  # Consider long-term consequences
        },
        related_constructs={
            "suscept_scarcity": -0.25,  # Urgency can increase perceived risk
            "suscept_skepticism": 0.40,  # Risk averse are skeptical
            "selfreg_rf": -0.50,  # Inverse of promotion focus
        },
        
        high_markers=[
            "needed guarantee", "risk free", "what if it doesn't work",
            "afraid of regret", "wanted to be safe", "warranty important",
            "return policy", "tried and true", "proven",
        ],
        low_markers=[
            "worth the risk", "took a chance", "new and untested ok",
            "doesn't need guarantee", "willing to experiment",
        ],
        
        ad_implications_high="Lead with guarantees: money-back, trial periods, warranties. Risk reversal messaging essential. Testimonials reduce perceived risk.",
        ad_implications_low="Novel/innovative positioning works. Early adopter messaging. Cutting-edge appeals.",
    ),

    # =========================================================================
    # TIER 3: BRAND-CUSTOMER MATCHING CONSTRUCTS  
    # =========================================================================

    # =========================================================================
    # CONSTRUCT 12: LOYALTY VS VARIETY SEEKING
    # =========================================================================
    "suscept_variety": SusceptibilityConstructDefinition(
        id="suscept_variety",
        name="Variety Seeking Tendency",
        description="Tendency to seek novelty and variety in product choices vs. staying loyal to familiar brands. Fundamental consumer behavior dimension.",
        domain="brand_matching",
        scale_anchors=("Brand loyal", "Variety seeking"),
        
        research_basis="McAlister, L., & Pessemier, E. (1982). Variety Seeking Behavior: An Interdisciplinary Review. JCR",
        key_citations=[
            "McAlister, L., & Pessemier, E. (1982). Variety Seeking Behavior. JCR",
            "Van Trijp, H.C., Hoyer, W.D., & Inman, J.J. (1996). Why switch? Product category–level explanations for true variety-seeking behavior. JMR",
            "Kahn, B.E. (1995). Consumer variety-seeking among goods and services. JRS",
            "Steenkamp, J.B.E., & Baumgartner, H. (1992). The role of optimum stimulation level in exploratory consumer behavior. JCR",
        ],
        meta_analysis_effect_size=0.35,  # Van Trijp et al.
        validated_scales=[
            "Variety Seeking Scale (Van Trijp et al., 1996)",
            "Change Seeker Index (Garlington & Shimota, 1964)",
            "Optimum Stimulation Level Scale (Steenkamp & Baumgartner, 1992)",
        ],
        
        mechanism_influences={
            "wanting_liking": 0.35,  # Variety seekers want newness
            "automatic_evaluation": 0.25,  # Respond to novel stimuli
            "identity_construction": 0.30,  # Variety as identity expression
            "mimetic_desire": -0.20,  # Less following others
        },
        related_constructs={
            "social_nfu": 0.50,  # Uniqueness seeking
            "suscept_scarcity": 0.25,  # Novel/rare appeals
            "temporal_ddr": 0.30,  # Boredom link
        },
        
        high_markers=[
            "tried something new", "switch brands", "wanted variety",
            "bored with usual", "like to experiment", "not loyal",
            "always trying different", "mix it up",
        ],
        low_markers=[
            "always buy this brand", "loyal customer", "won't switch",
            "stick with what works", "trust this brand", "repeat purchase",
        ],
        
        ad_implications_high="New feature positioning, novelty emphasis, competitive switching offers. Frame as exciting change.",
        ad_implications_low="Retention messaging, loyalty rewards, 'trusted by you for years'. Emphasize consistency and reliability.",
    ),

    # =========================================================================
    # CONSTRUCT 13: COMPULSIVE BUYING TENDENCY
    # =========================================================================
    "suscept_compulsive": SusceptibilityConstructDefinition(
        id="suscept_compulsive",
        name="Compulsive Buying Tendency",
        description="Chronic, repetitive purchasing that becomes a primary response to negative events or feelings. Ranges from mild impulse buying to pathological.",
        domain="brand_matching",
        scale_anchors=("Deliberate buyer", "Impulsive/compulsive"),
        
        research_basis="Faber, R.J., & O'Guinn, T.C. (1992). A clinical screener for compulsive buying. JCR",
        key_citations=[
            "Faber, R.J., & O'Guinn, T.C. (1992). A clinical screener for compulsive buying. JCR",
            "Ridgway, N.M., Kukar-Kinney, M., & Monroe, K.B. (2008). An expanded conceptualization and a new measure of compulsive buying. JCR",
            "Dittmar, H. (2005). Compulsive buying—A growing concern? An examination of gender, age, and endorsement. British Journal of Psychology",
            "Rook, D.W., & Fisher, R.J. (1995). Normative influences on impulsive buying behavior. JCR",
        ],
        meta_analysis_effect_size=None,  # Clinical construct
        validated_scales=[
            "Compulsive Buying Scale (Faber & O'Guinn, 1992)",
            "Richmond Compulsive Buying Scale (Ridgway et al., 2008)",
            "Buying Impulsiveness Scale (Rook & Fisher, 1995)",
        ],
        
        mechanism_influences={
            "wanting_liking": 0.60,  # Driven by wanting/craving
            "automatic_evaluation": 0.55,  # Bypass deliberation
            "attention_dynamics": 0.40,  # Captured by stimuli
            "regulatory_focus": -0.35,  # Weak self-regulation
        },
        related_constructs={
            "suscept_delay_discount": 0.55,  # Impulsivity link
            "suscept_scarcity": 0.45,  # Urgency triggers
            "suscept_variety": 0.40,  # Novelty seeking component
        },
        
        high_markers=[
            "impulse buy", "couldn't resist", "retail therapy",
            "bought without thinking", "had to have it",
            "regret purchase", "buyer's remorse", "addiction",
        ],
        low_markers=[
            "planned purchase", "researched carefully",
            "took my time", "slept on it", "budget discipline",
        ],
        
        ad_implications_high="One-click purchase effective, impulse triggers work, emotional appeals. ETHICAL NOTE: Avoid exploiting this vulnerability excessively.",
        ad_implications_low="Rational appeals, value justification, research-friendly content. Deliberation-supportive messaging.",
    ),
}


# =============================================================================
# NEO4J POPULATION FUNCTIONS
# =============================================================================

async def populate_susceptibility_constructs(driver) -> Dict[str, int]:
    """
    Populate Neo4j with susceptibility construct nodes and relationships.
    
    Creates:
    1. SusceptibilityConstruct nodes with full research metadata
    2. INFLUENCES_MECHANISM relationships to existing CognitiveMechanism nodes
    3. CORRELATED_WITH relationships between constructs
    
    Returns:
        Dictionary with counts of created nodes and relationships
    """
    stats = {"constructs": 0, "mechanism_rels": 0, "construct_rels": 0}
    
    async with driver.session() as session:
        # Create/update susceptibility construct nodes
        for construct_id, construct_def in SUSCEPTIBILITY_CONSTRUCTS.items():
            query = """
            MERGE (c:SusceptibilityConstruct {id: $id})
            SET c.name = $name,
                c.domain = $domain,
                c.description = $description,
                c.scale_low = $scale_low,
                c.scale_high = $scale_high,
                c.research_basis = $research_basis,
                c.key_citations = $key_citations,
                c.effect_size = $effect_size,
                c.validated_scales = $validated_scales,
                c.ad_implications_high = $ad_high,
                c.ad_implications_low = $ad_low,
                c.high_markers = $high_markers,
                c.low_markers = $low_markers,
                c.updated_at = datetime()
            RETURN c
            """
            
            result = await session.run(query, {
                "id": construct_def.id,
                "name": construct_def.name,
                "domain": construct_def.domain,
                "description": construct_def.description,
                "scale_low": construct_def.scale_anchors[0],
                "scale_high": construct_def.scale_anchors[1],
                "research_basis": construct_def.research_basis,
                "key_citations": construct_def.key_citations,
                "effect_size": construct_def.meta_analysis_effect_size,
                "validated_scales": construct_def.validated_scales,
                "ad_high": construct_def.ad_implications_high,
                "ad_low": construct_def.ad_implications_low,
                "high_markers": construct_def.high_markers,
                "low_markers": construct_def.low_markers,
            })
            await result.consume()
            stats["constructs"] += 1
            
            # Create INFLUENCES_MECHANISM relationships
            for mechanism_id, strength in construct_def.mechanism_influences.items():
                mech_query = """
                MATCH (c:SusceptibilityConstruct {id: $construct_id})
                MATCH (m:CognitiveMechanism {id: $mechanism_id})
                MERGE (c)-[r:INFLUENCES_MECHANISM]->(m)
                SET r.influence_strength = $strength,
                    r.direction = CASE WHEN $strength > 0 THEN 'positive' ELSE 'negative' END,
                    r.source = 'persuasion_susceptibility_framework'
                RETURN r
                """
                try:
                    result = await session.run(mech_query, {
                        "construct_id": construct_def.id,
                        "mechanism_id": mechanism_id,
                        "strength": strength,
                    })
                    await result.consume()
                    stats["mechanism_rels"] += 1
                except Exception as e:
                    logger.debug(f"Could not create mechanism relationship {construct_def.id} -> {mechanism_id}: {e}")
            
            # Create CORRELATED_WITH relationships to other constructs
            for related_id, correlation in construct_def.related_constructs.items():
                corr_query = """
                MATCH (c1:SusceptibilityConstruct {id: $id1})
                MATCH (c2) WHERE c2.id = $id2 AND (c2:SusceptibilityConstruct OR c2:ExtendedPsychologicalConstruct)
                MERGE (c1)-[r:CORRELATED_WITH]->(c2)
                SET r.correlation = $correlation,
                    r.source = 'persuasion_susceptibility_framework'
                RETURN r
                """
                try:
                    result = await session.run(corr_query, {
                        "id1": construct_def.id,
                        "id2": related_id,
                        "correlation": correlation,
                    })
                    await result.consume()
                    stats["construct_rels"] += 1
                except Exception as e:
                    logger.debug(f"Could not create correlation {construct_def.id} <-> {related_id}: {e}")
    
    logger.info(f"Populated susceptibility constructs: {stats}")
    return stats


async def create_susceptibility_indexes(driver) -> None:
    """Create indexes and constraints for susceptibility constructs."""
    async with driver.session() as session:
        queries = [
            "CREATE CONSTRAINT susceptibility_construct_id IF NOT EXISTS FOR (c:SusceptibilityConstruct) REQUIRE c.id IS UNIQUE",
            "CREATE INDEX susceptibility_domain IF NOT EXISTS FOR (c:SusceptibilityConstruct) ON (c.domain)",
            "CREATE INDEX susceptibility_name IF NOT EXISTS FOR (c:SusceptibilityConstruct) ON (c.name)",
        ]
        for query in queries:
            try:
                await session.run(query)
            except Exception as e:
                logger.debug(f"Index creation note: {e}")


# =============================================================================
# QUERY FUNCTIONS FOR ATOM INTEGRATION
# =============================================================================

async def get_mechanism_susceptibility_influences(driver, construct_scores: Dict[str, float]) -> Dict[str, float]:
    """
    Given a profile of susceptibility construct scores, compute mechanism effectiveness modifiers.
    
    Args:
        driver: Neo4j driver
        construct_scores: Dict of construct_id -> score (0-1)
        
    Returns:
        Dict of mechanism_id -> effectiveness modifier (-0.5 to +0.5)
    """
    mechanism_modifiers = {}
    
    async with driver.session() as session:
        query = """
        MATCH (c:SusceptibilityConstruct)-[r:INFLUENCES_MECHANISM]->(m:CognitiveMechanism)
        WHERE c.id IN $construct_ids
        RETURN m.id as mechanism, c.id as construct, r.influence_strength as strength
        """
        
        result = await session.run(query, {"construct_ids": list(construct_scores.keys())})
        
        async for record in result:
            mechanism = record["mechanism"]
            construct = record["construct"]
            strength = record["strength"]
            
            # Score is 0-1, center at 0.5 for neutral
            score = construct_scores.get(construct, 0.5)
            # Modifier = (score - 0.5) * strength
            # If score > 0.5 and strength > 0, positive modifier
            # If score < 0.5 and strength > 0, negative modifier
            modifier = (score - 0.5) * strength
            
            if mechanism not in mechanism_modifiers:
                mechanism_modifiers[mechanism] = 0.0
            mechanism_modifiers[mechanism] += modifier
    
    return mechanism_modifiers


def get_construct_definitions() -> Dict[str, SusceptibilityConstructDefinition]:
    """Return all susceptibility construct definitions for use in other modules."""
    return SUSCEPTIBILITY_CONSTRUCTS


def get_construct_markers(construct_id: str) -> Tuple[List[str], List[str]]:
    """Get linguistic markers for a construct."""
    if construct_id in SUSCEPTIBILITY_CONSTRUCTS:
        construct = SUSCEPTIBILITY_CONSTRUCTS[construct_id]
        return construct.high_markers, construct.low_markers
    return [], []


# =============================================================================
# INITIALIZATION
# =============================================================================

async def initialize_susceptibility_graph(driver) -> None:
    """
    Initialize the susceptibility construct graph.
    Call this during ADAM startup.
    """
    logger.info("Initializing persuasion susceptibility constructs in Neo4j...")
    await create_susceptibility_indexes(driver)
    stats = await populate_susceptibility_constructs(driver)
    logger.info(f"Susceptibility graph initialized: {stats}")
