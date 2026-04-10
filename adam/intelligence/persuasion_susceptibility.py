#!/usr/bin/env python3
"""
ADAM PERSUASION SUSCEPTIBILITY FRAMEWORK
========================================

Measures individual susceptibility to specific persuasion mechanisms.
Unlike ADAM's existing psychological frameworks (which detect expressed traits),
this module measures RESPONSIVENESS to persuasion techniques.

CRITICAL DISTINCTION:
- Existing frameworks: "This person IS analytical" (expressed trait)
- This module: "This person RESPONDS TO social proof" (susceptibility)

TIER 1 CONSTRUCTS (Most valuable for mechanism selection):
1. Social Proof Susceptibility - How influenced by others' behavior
2. Authority Bias Susceptibility - How influenced by experts/credibility
3. Scarcity Reactivity - How influenced by urgency/limited availability
4. Anchoring Susceptibility - How influenced by reference points
5. Delay Discounting - Preference for immediate vs. delayed rewards

Training Approach:
- Extract behavioral signals from real reviews (not synthetic templates)
- Use contrastive patterns: people who explicitly mention being influenced vs. not
- Validate against actual conversion data when available
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math


@dataclass
class SusceptibilityScore:
    """Score for a persuasion susceptibility dimension."""
    dimension: str
    score: float  # 0-1, where 1 = highly susceptible
    confidence: float  # 0-1, confidence in the measurement
    evidence: List[str] = field(default_factory=list)
    signals_detected: int = 0
    
    @property
    def level(self) -> str:
        """Categorical level for mechanism activation."""
        if self.score >= 0.7:
            return "high"
        elif self.score >= 0.4:
            return "moderate"
        else:
            return "low"


# =============================================================================
# CONSTRUCT 1: SOCIAL PROOF SUSCEPTIBILITY
# =============================================================================

SOCIAL_PROOF_SUSCEPTIBILITY = {
    "construct_name": "Social Proof Susceptibility",
    "description": "Tendency to be influenced by what others do or think",
    "mechanism_mapping": ["social_proof", "bandwagon", "consensus"],
    
    "high_susceptibility_markers": {
        "explicit_influence": [
            r"\b(after|because of|due to) (the |all the )?(positive |great |good )?reviews?\b",
            r"\breviews? (convinced|sold|persuaded) me\b",
            r"\b(everyone|everybody|people) (seems?|loves?|recommends?|says?)\b",
            r"\bbased on (the )?reviews?\b",
            r"\btrusted the reviews?\b",
        ],
        "popularity_driven": [
            r"\b(best.?sell\w*|popular|trending|viral)\b.{0,30}\b(convinced|bought|tried)\b",
            r"\b(so many|thousands of|hundreds of) (people|customers|buyers)\b",
            r"\b(#1|number one|top.?rated)\b.{0,20}\bhad to\b",
            r"\b(highly|well) rated\b",
        ],
        "social_reference": [
            r"\b(my )?(friend|family|coworker|colleague|neighbor)\w* (recommended|suggested|told me|uses?)\b",
            r"\bsomeone told me\b",
            r"\bheard (good things|great things|a lot) about\b",
            r"\bwas recommended\b",
        ],
        "conformity_language": [
            r"\bjumped on the bandwagon\b",
            r"\bfigured i'd give it a (try|shot)\b.{0,30}\b(everyone|popular|reviews?)\b",
            r"\bseems like everyone\b",
            r"\bdidn't want to miss out\b",
        ],
        "rating_driven": [
            r"\b(4|5).?(star|out of 5)\b.{0,30}\b(convinced|bought|decided)\b",
            r"\bhigh rating\w*\b.{0,20}\b(influenced|convinced)\b",
            r"\b(saw|noticed) the (high )?rating\b",
        ],
    },
    
    "low_susceptibility_markers": {
        "independent_decision": [
            r"\bdon't (care|listen to) what others\b",
            r"\bmake (my )?own (decision|choice|judgment)\b",
            r"\bregardless of (reviews?|ratings?|what others)\b",
            r"\bdespite (the |mixed |negative )?reviews?\b",
        ],
        "skepticism": [
            r"\bdon't trust reviews?\b",
            r"\breviews? (can be|are often) (fake|biased|unreliable)\b",
            r"\bignored the (hype|reviews?|ratings?)\b",
            r"\btook reviews? with a grain of salt\b",
        ],
        "self_reliance": [
            r"\btried it (myself|for myself)\b",
            r"\bformed my own opinion\b",
            r"\bjudged (it )?for myself\b",
            r"\bmy own (research|testing|evaluation)\b",
        ],
        "contrarian": [
            r"\bwent against (the grain|popular opinion|the crowd)\b",
            r"\bdon't follow (trends?|the crowd|the hype)\b",
            r"\bI like to be different\b",
        ],
    },
    
    "application": {
        "high": "Emphasize customer counts, testimonials, ratings, 'join thousands who...'",
        "moderate": "Include social proof but balance with product merits",
        "low": "Focus on objective quality, unique features, independent evaluation"
    }
}


# =============================================================================
# CONSTRUCT 2: AUTHORITY BIAS SUSCEPTIBILITY
# =============================================================================

AUTHORITY_BIAS_SUSCEPTIBILITY = {
    "construct_name": "Authority Bias Susceptibility",
    "description": "Tendency to defer to experts, credentials, or official sources",
    "mechanism_mapping": ["authority", "expertise", "credibility"],
    
    "high_susceptibility_markers": {
        "expert_trust": [
            r"\b(doctor|expert|professional|specialist)\w* recommend\w*\b",
            r"\btrust(ed)? the expert\w*\b",
            r"\bbased on (doctor|expert|professional) (advice|recommendation)\b",
            r"\bmy (doctor|dermatologist|dentist|trainer)\b.{0,30}\b(said|suggested|recommended)\b",
        ],
        "credential_driven": [
            r"\b(fda|usda|certified|approved|endorsed) (approved|certified)\b.{0,20}\b(convinced|trust)\b",
            r"\bclinically (proven|tested)\b.{0,20}\b(convinced|trust)\b",
            r"\b(harvard|stanford|mit|research\w*)\b.{0,30}\b(backed|proven|shown)\b",
        ],
        "brand_authority": [
            r"\btrusted (brand|name|company)\b",
            r"\bbeen around for (years|decades)\b",
            r"\bestablished (brand|company)\b",
            r"\bindustry leader\b",
        ],
        "official_sources": [
            r"\baccording to (studies|research|science)\b",
            r"\bscientifically (proven|backed|supported)\b",
            r"\bpeer.?reviewed\b",
            r"\b(study|studies|research) (shows?|proves?|confirms?)\b",
        ],
        "deference_language": [
            r"\bthey know (best|better|what they're doing)\b",
            r"\bi'm not (an expert|a professional)\b.{0,30}\btrust\b",
            r"\bwho am i to (question|doubt)\b",
        ],
    },
    
    "low_susceptibility_markers": {
        "authority_skepticism": [
            r"\b(experts?|professionals?) (can be|are often) wrong\b",
            r"\bdon't (blindly )?trust (experts?|authorities?|credentials?)\b",
            r"\bcredentials? don't (mean|guarantee)\b",
            r"\bquestion (the experts?|authority)\b",
        ],
        "self_research": [
            r"\bdid my own research\b",
            r"\bverified (myself|for myself|it myself)\b",
            r"\bdidn't just take (their|the expert's) word\b",
            r"\bfact.?check\w*\b",
        ],
        "experience_over_expertise": [
            r"\b(real|actual) (users?|customers?|people) know better\b",
            r"\bexperience (matters|trumps|beats) (credentials?|degrees?)\b",
            r"\blearned from (trial and error|experience)\b",
        ],
    },
    
    "application": {
        "high": "Lead with credentials, expert endorsements, certifications, research backing",
        "moderate": "Include authority signals but also practical proof",
        "low": "Focus on real-world results, user testimonials, personal testing"
    }
}


# =============================================================================
# CONSTRUCT 3: SCARCITY REACTIVITY
# =============================================================================

SCARCITY_REACTIVITY = {
    "construct_name": "Scarcity Reactivity",
    "description": "Responsiveness to limited availability, urgency, and FOMO triggers",
    "mechanism_mapping": ["scarcity", "urgency", "fomo", "limited_time"],
    
    "high_susceptibility_markers": {
        "urgency_driven": [
            r"\b(grabbed|bought|ordered) (it )?(quickly|immediately|right away)\b.{0,20}\b(before|limited|running out)\b",
            r"\bdidn't want to miss (out|the deal|the sale|it)\b",
            r"\bhad to (act|buy|order) fast\b",
            r"\b(sale|deal|discount) (was )?ending\b.{0,20}\b(bought|grabbed|ordered)\b",
        ],
        "scarcity_response": [
            r"\b(only|just) (\d+|a few|limited) left\b.{0,20}\b(bought|grabbed|ordered)\b",
            r"\b(sold out|selling out|going fast)\b.{0,20}\b(hurried|rushed|grabbed)\b",
            r"\blimited (edition|time|stock|quantity)\b.{0,20}\b(had to|convinced|grabbed)\b",
            r"\brare (find|item|product)\b.{0,20}\b(had to|couldn't pass)\b",
        ],
        "fomo_language": [
            r"\b(fomo|fear of missing out)\b",
            r"\beveryone (else )?(was|is) (getting|buying)\b",
            r"\bdidn't want to (be left out|miss out|regret)\b",
            r"\b(last|final) chance\b.{0,20}\b(bought|grabbed)\b",
        ],
        "deal_driven": [
            r"\bthe (deal|price|discount) was too good\b",
            r"\bcouldn't (pass up|resist) (the deal|this price)\b",
            r"\bflash sale\b.{0,20}\b(bought|grabbed)\b",
            r"\b(black friday|prime day|cyber monday)\b.{0,20}\b(finally|grabbed)\b",
        ],
    },
    
    "low_susceptibility_markers": {
        "patience_signals": [
            r"\bwaited (for|until)\b.{0,30}\b(right time|right price|patience)\b",
            r"\bno rush\b",
            r"\bwill wait for\b",
            r"\bnot falling for (urgency|scarcity|fomo)\b",
        ],
        "skepticism": [
            r"\bfake (scarcity|urgency)\b",
            r"\bmarketing (trick|tactic|gimmick)\b.{0,20}\b(urgency|limited)\b",
            r"\balways (on sale|back in stock|available)\b",
            r"\bdon't fall for (limited time|scarcity)\b",
        ],
        "deliberation": [
            r"\btook my time\b",
            r"\bno (pressure|rush) to (buy|decide)\b",
            r"\bsleep on it\b",
            r"\bresearched for (weeks|months)\b",
        ],
    },
    
    "application": {
        "high": "Use urgency triggers, limited quantities, countdown timers, 'act now'",
        "moderate": "Light urgency with genuine deadlines",
        "low": "Avoid urgency tactics - they backfire; emphasize always available, quality"
    }
}


# =============================================================================
# CONSTRUCT 4: ANCHORING SUSCEPTIBILITY
# =============================================================================

ANCHORING_SUSCEPTIBILITY = {
    "construct_name": "Anchoring Susceptibility",
    "description": "Tendency to rely heavily on first piece of information (anchor) for decisions",
    "mechanism_mapping": ["anchoring", "contrast_effect", "price_framing"],
    
    "high_susceptibility_markers": {
        "price_anchor_response": [
            r"\b(compared to|versus|vs\.?) the (original|regular|retail|list) price\b",
            r"\b(was|originally|regularly) \$\d+.{0,20}(now|sale|only) \$\d+\b",
            r"\bsaved \$?\d+\b",
            r"\b(great|good|amazing) (deal|value|savings?)\b.{0,20}\b(was|compared to|versus)\b",
        ],
        "reference_point_language": [
            r"\bfor (this|that) price\b",
            r"\b(better|cheaper|more affordable) than (expected|i thought|alternatives?)\b",
            r"\bpay(ing)? (\$)?\d+ (more|extra|less)\b.{0,20}\bworth it\b",
            r"\brelative to\b",
        ],
        "comparison_shopping": [
            r"\bcheaper than (competitors?|alternatives?|similar)\b",
            r"\bcompared (prices?|costs?)\b",
            r"\bbetter (deal|price|value) than\b",
        ],
        "value_ratio_thinking": [
            r"\bfor (what you get|the quality|the features)\b.{0,20}\b(worth|reasonable|fair)\b",
            r"\b(price|cost) (per|to) (quality|performance|value) ratio\b",
            r"\bbang for (your|the) buck\b",
        ],
    },
    
    "low_susceptibility_markers": {
        "absolute_value_focus": [
            r"\bdon't (care about|compare to) (original|list|retail) price\b",
            r"\bwhat (it's|the product is) worth to me\b",
            r"\bignor(e|ed) the (sale|discount|original price)\b",
        ],
        "intrinsic_valuation": [
            r"\bwould (pay|have paid) (this|full) price\b",
            r"\bworth (this|the) price (regardless|anyway)\b",
            r"\bnot about (the deal|savings)\b",
        ],
        "anti_anchor": [
            r"\b(inflated|fake) (original|list|retail) price\b",
            r"\bmanufactured (discount|deal|savings)\b",
            r"\bmarketing (tactics?|tricks?)\b.{0,20}\b(anchor|price)\b",
        ],
    },
    
    "application": {
        "high": "Show price comparisons, 'was/now' pricing, competitor comparisons, savings calculations",
        "moderate": "Include value context without heavy anchoring",
        "low": "Focus on absolute value proposition, avoid comparative pricing tactics"
    }
}


# =============================================================================
# CONSTRUCT 5: DELAY DISCOUNTING (TEMPORAL PREFERENCE)
# =============================================================================

DELAY_DISCOUNTING = {
    "construct_name": "Delay Discounting",
    "description": "Preference for immediate vs. delayed rewards; impulsivity vs. patience",
    "mechanism_mapping": ["urgency", "instant_gratification", "long_term_value"],
    
    "high_discounting_markers": {  # Prefers immediate, impulsive
        "immediate_preference": [
            r"\bwanted it (now|right away|immediately|today)\b",
            r"\bcouldn't wait\b",
            r"\bneed(ed)? it (fast|quick|asap|now)\b",
            r"\b(same|next|2).?day (shipping|delivery)\b.{0,20}\b(had to|love|essential)\b",
        ],
        "impatience_signals": [
            r"\bimpati(ent|ence)\b",
            r"\bdon't (want|like) to wait\b",
            r"\b(hate|can't stand) waiting\b",
            r"\bwish (it|they|this) (was|were|came) faster\b",
        ],
        "impulse_buying": [
            r"\bimpulse (buy|purchase)\b",
            r"\bspur of the moment\b",
            r"\bjust (bought|grabbed|ordered) it\b",
            r"\bdidn't (overthink|think about) it\b",
        ],
        "instant_gratification": [
            r"\binstant (gratification|results?|satisfaction)\b",
            r"\bright (away|now|out of the box)\b",
            r"\bimmediate (results?|benefit|use)\b",
        ],
    },
    
    "low_discounting_markers": {  # Willing to wait, patient, long-term oriented
        "patience_signals": [
            r"\bworth the wait\b",
            r"\b(waited|patient|took my time)\b",
            r"\bno (rush|hurry)\b",
            r"\bwilling to wait\b.{0,20}\b(quality|right)\b",
        ],
        "long_term_thinking": [
            r"\b(long|longer).?term (investment|value|thinking)\b",
            r"\b(over|in the long) (time|run|haul)\b",
            r"\bpays off (later|eventually|over time)\b",
            r"\binvestment (in|for) (the future|myself)\b",
        ],
        "delayed_gratification": [
            r"\bsaved up\b",
            r"\bresisted (the urge|impulse|temptation)\b",
            r"\bwaited (for|until) (the right|a better)\b",
            r"\bdelayed (gratification|purchase)\b",
        ],
        "planning": [
            r"\bresearched (for|over) (weeks|months)\b",
            r"\bplanned (this )?purchase\b",
            r"\bwaited for (the right|a good) (time|price|moment)\b",
        ],
    },
    
    "application": {
        "high": "Emphasize instant access, immediate benefits, fast shipping, 'get it now'",
        "moderate": "Balance immediate benefits with long-term value",
        "low": "Emphasize durability, long-term value, investment framing"
    }
}


# =============================================================================
# CONSTRUCT 6: REACTANCE TENDENCY
# =============================================================================

REACTANCE_TENDENCY = {
    "construct_name": "Psychological Reactance",
    "description": "Tendency to resist perceived attempts to limit freedom of choice",
    "mechanism_mapping": ["soft_sell", "autonomy", "choice_framing"],
    
    "high_reactance_markers": {
        "resistance_to_pressure": [
            r"\bdon't (like|appreciate) being (pushed|pressured|sold to)\b",
            r"\bpushy (sales?|marketing|ads?)\b.{0,20}\b(hate|annoying|turned off)\b",
            r"\bfelt (pressured|pushed|manipulated)\b",
            r"\bdon't tell me what to (do|buy|think)\b",
        ],
        "autonomy_assertion": [
            r"\bmy (choice|decision)\b.{0,20}\b(not yours|not theirs|mine)\b",
            r"\bi'll (decide|choose) (myself|for myself)\b",
            r"\bdon't need (anyone|someone) to tell me\b",
        ],
        "contrarian_buying": [
            r"\bbought (it )?to prove\b",
            r"\bwent (with|for) (another|different|the other)\b.{0,20}\b(spite|prove|show)\b",
            r"\bdid the opposite\b",
        ],
        "ad_skepticism": [
            r"\b(ad|ads|advertising|marketing) (is|are) (annoying|manipulative|pushy)\b",
            r"\btrying to (sell|manipulate|trick) me\b",
            r"\bsee through (the|their) (marketing|tactics)\b",
        ],
    },
    
    "low_reactance_markers": {
        "receptivity": [
            r"\bthe (ad|commercial|marketing) (convinced|sold) me\b",
            r"\bgood (recommendation|suggestion)\b",
            r"\bhelpful (guidance|advice|suggestion)\b",
            r"\bappreciated the (recommendation|help|guidance)\b",
        ],
        "openness_to_influence": [
            r"\bopen to (suggestions?|recommendations?)\b",
            r"\bwelcome(d)? (advice|input|guidance)\b",
            r"\bglad (they|someone) (suggested|recommended)\b",
        ],
    },
    
    "application": {
        "high": "Use soft-sell, provide options, emphasize 'you decide', avoid pressure tactics",
        "moderate": "Balanced approach with gentle guidance",
        "low": "Direct calls-to-action are effective"
    }
}


# =============================================================================
# TIER 2: MESSAGE CRAFTING CONSTRUCTS
# =============================================================================

# =============================================================================
# CONSTRUCT 7: SKEPTICISM LEVEL
# =============================================================================

SKEPTICISM_LEVEL = {
    "construct_name": "Skepticism Level",
    "description": "Degree of critical evaluation and doubt toward claims and marketing",
    "mechanism_mapping": ["evidence", "transparency", "proof_points"],
    
    "high_skepticism_markers": {
        "doubt_expression": [
            r"\b(skeptic|skeptical|doubt|doubtful)\w*\b",
            r"\bdidn't (believe|trust|buy) (it|the|their)\b",
            r"\btoo good to be true\b",
            r"\bwas (suspicious|wary|cautious)\b",
        ],
        "verification_behavior": [
            r"\bhad to (verify|confirm|check|test)\b",
            r"\bverified (it )?(myself|for myself|independently)\b",
            r"\bfact.?check\w*\b",
            r"\bdouble.?check\w*\b",
            r"\bcross.?referenc\w*\b",
        ],
        "claims_questioning": [
            r"\bquestion\w* (the|their|these) claims?\b",
            r"\bdon't (just )?take (their|anyone's) word\b",
            r"\bneeded (proof|evidence|data)\b",
            r"\bwanted to see (for myself|actual|real)\b",
        ],
        "marketing_distrust": [
            r"\bmarketing (bs|nonsense|hype|speak)\b",
            r"\bjust (marketing|hype|spin)\b",
            r"\bdon't (believe|trust) (ads?|marketing|advertising)\b",
            r"\bcorporate (speak|jargon|bs)\b",
        ],
        "evidence_demanding": [
            r"\bwhere('s| is) the (proof|evidence|data)\b",
            r"\bshow me (the )?(proof|evidence|numbers|data)\b",
            r"\bprove it\b",
            r"\bclaims? (need|require) (proof|evidence)\b",
        ],
    },
    
    "low_skepticism_markers": {
        "trust_easily": [
            r"\btrusted (it|them|the brand) (immediately|right away)\b",
            r"\bdidn't (question|doubt|hesitate)\b",
            r"\btook (their|the) word for it\b",
            r"\bbelieved (the claims?|them|it)\b",
        ],
        "acceptance": [
            r"\bsounds? (good|great|right|legit)\b",
            r"\bmakes sense\b",
            r"\bif they say so\b",
            r"\bthey (must|should) know\b",
        ],
        "low_verification": [
            r"\bdidn't (need|bother) to (check|verify|research)\b",
            r"\bjust (bought|ordered|went with) it\b",
            r"\bwhy would they lie\b",
        ],
    },
    
    "application": {
        "high": "Lead with evidence, third-party validation, data, transparency, address objections proactively",
        "moderate": "Balance claims with supporting evidence",
        "low": "Simple claims are accepted; social proof and authority work well"
    }
}


# =============================================================================
# CONSTRUCT 8: INFORMATION AVOIDANCE (OSTRICH EFFECT)
# =============================================================================

INFORMATION_AVOIDANCE = {
    "construct_name": "Information Avoidance",
    "description": "Tendency to avoid potentially negative or uncomfortable information",
    "mechanism_mapping": ["positive_framing", "reassurance", "simplified_messaging"],
    
    "high_avoidance_markers": {
        "avoid_details": [
            r"\bdon't (want|need) to (know|hear|see) (the )?(details|specifics|numbers)\b",
            r"\btoo much (information|detail)\b",
            r"\bdidn't (want|need) to (read|know|look at)\b",
            r"\bskipped (the|over) (fine print|details|specs)\b",
        ],
        "discomfort_with_negatives": [
            r"\bdon't (want|like) to (think|hear) about (the )?(negative|bad|downside)\b",
            r"\bwould rather not know\b",
            r"\bignorance is bliss\b",
            r"\bdidn't (want|need) (bad|negative) news\b",
        ],
        "simplicity_seeking": [
            r"\bjust (tell|give) me (the )?(basics|bottom line|summary)\b",
            r"\btoo (much|complicated|complex) to (understand|process)\b",
            r"\bkeep it simple\b",
            r"\btl;?dr\b",
        ],
        "decision_avoidance": [
            r"\bdon't (want|like) to (decide|choose|think about it)\b",
            r"\bjust (tell|decide for) me\b",
            r"\bwhatever (is|you) (recommended|suggest)\b",
            r"\boverwhelm\w*\b.{0,20}\b(options?|choices?|decisions?)\b",
        ],
    },
    
    "low_avoidance_markers": {
        "information_seeking": [
            r"\bwant(ed)? (all|every|the full) (details?|information|picture)\b",
            r"\bread (all|every|the entire) (review|spec|detail)\b",
            r"\bneed to know everything\b",
            r"\bgive me (all|more) (details|information|data)\b",
        ],
        "embrace_complexity": [
            r"\bthe more (information|details?) the better\b",
            r"\bwant to (understand|know) (fully|completely|everything)\b",
            r"\bdive (deep|into) (the )?(details|specs|information)\b",
        ],
        "negative_info_seeking": [
            r"\bwant(ed)? to (know|see|read) the (negative|bad|cons|downsides?)\b",
            r"\bread (all )?the (negative|bad|1.?star) reviews?\b",
            r"\bwhat (are|could be) the (problems?|issues?|downsides?)\b",
        ],
    },
    
    "application": {
        "high": "Simple messaging, focus on positives, reassurance, avoid overwhelming details",
        "moderate": "Balanced detail level with easy opt-in for more",
        "low": "Provide comprehensive information, address concerns directly"
    }
}


# =============================================================================
# CONSTRUCT 9: COGNITIVE LOAD TOLERANCE
# =============================================================================

COGNITIVE_LOAD_TOLERANCE = {
    "construct_name": "Cognitive Load Tolerance",
    "description": "Capacity and willingness to process complex information",
    "mechanism_mapping": ["message_complexity", "detail_level", "presentation_style"],
    
    "high_tolerance_markers": {
        "complexity_comfort": [
            r"\blove (learning|understanding|diving into) (the )?(technical|complex|detailed)\b",
            r"\bengineering (details|specs|breakdown)\b.{0,20}\b(love|appreciate|want)\b",
            r"\bthe more (technical|detailed|complex) the better\b",
            r"\bfascinat\w* by (the )?(mechanics|details|how it works)\b",
        ],
        "extensive_research": [
            r"\bspent (hours|days|weeks) (researching|learning|understanding)\b",
            r"\bread (every|all the) (review|spec|detail|article)\b",
            r"\bcompared (every|all|dozens of) (option|product|feature)\b",
            r"\bthorough(ly)? research\w*\b",
        ],
        "detail_appreciation": [
            r"\bappreciate (the )?(detail|thorough|comprehensive)\b",
            r"\bwell.?documented\b",
            r"\b(love|want) (all )?(the )?(specs|specifications|technical details)\b",
            r"\bgranular (detail|information|data)\b",
        ],
        "analytical_language": [
            r"\banalyz\w* (every|all|the) (aspect|detail|option)\b",
            r"\bweigh\w* (all )?(the )?(options?|pros?|cons?)\b",
            r"\bsystematic(ally)? (evaluat|compar|review)\w*\b",
        ],
    },
    
    "low_tolerance_markers": {
        "overwhelm_signals": [
            r"\b(too|so) (much|many) (information|details?|options?|choices?)\b",
            r"\boverwhelm\w*\b",
            r"\bconfus\w*\b.{0,20}\b(options?|choices?|details?)\b",
            r"\bparalyz\w* (by|with) (choice|options?|information)\b",
        ],
        "simplicity_preference": [
            r"\bjust (works|want it to work)\b",
            r"\bdon't (care|need|want) (about )?(the )?(details|specs|technical)\b",
            r"\bkeep it (simple|basic|straightforward)\b",
            r"\bno.?brainer\b",
        ],
        "delegation_desire": [
            r"\bjust (tell|recommend) me (what|which) (to buy|is best)\b",
            r"\b(pick|choose|decide) for me\b",
            r"\bwhatever (you|they|experts?) (recommend|suggest)\b",
        ],
        "frustration_with_complexity": [
            r"\bwhy (is|does) (this|it) (have to be|need to be) (so )?(complicated|complex)\b",
            r"\bmake it (easier|simpler)\b",
            r"\bshould(n't)? be (this|so) (hard|complicated|difficult)\b",
        ],
    },
    
    "application": {
        "high": "Provide detailed specs, comparisons, technical deep-dives, comprehensive information",
        "moderate": "Clear summary with expandable details",
        "low": "Simple messaging, clear recommendations, visual over text, minimal choices"
    }
}


# =============================================================================
# CONSTRUCT 10: PRICE SENSITIVITY
# =============================================================================

PRICE_SENSITIVITY = {
    "construct_name": "Price Sensitivity",
    "description": "How much price influences purchase decisions relative to other factors",
    "mechanism_mapping": ["value_framing", "price_justification", "discount_appeals"],
    
    "high_sensitivity_markers": {
        "price_focus": [
            r"\bprice was (the |my )?(main|key|primary|deciding) factor\b",
            r"\bcouldn't (afford|justify) (the )?(higher|more expensive)\b",
            r"\bwent with (the )?(cheaper|cheapest|budget|affordable)\b",
            r"\bprice point\b.{0,20}\b(important|key|critical)\b",
        ],
        "deal_seeking": [
            r"\bwaited (for|until) (a )?sale\b",
            r"\b(always|only) (buy|shop) (on|during) (sales?|deals?|discount)\b",
            r"\bcompare(d)? prices? (everywhere|across|at multiple)\b",
            r"\bfound (a |the )?(better|best|lowest) price\b",
        ],
        "budget_consciousness": [
            r"\bon a (tight )?budget\b",
            r"\bcan't (afford|spend|justify) (that much|too much)\b",
            r"\b(budget|price) (friendly|conscious|sensitive)\b",
            r"\bmore than (i|we) (wanted|planned) to spend\b",
        ],
        "value_calculation": [
            r"\bcost per (use|serving|unit|day)\b",
            r"\b(price|cost) (to|vs\.?|versus) (quality|performance|value)\b",
            r"\bbang for (the|your) buck\b",
            r"\bworth (every|the) (penny|cent|dollar)\b.{0,10}\bconsidering\b",
        ],
    },
    
    "low_sensitivity_markers": {
        "quality_over_price": [
            r"\bdon't (care|mind) (about )?(the )?(price|cost|paying more)\b",
            r"\bquality (over|matters more than) price\b",
            r"\bwilling to (pay|spend) (more|extra|premium)\b",
            r"\bprice (wasn't|isn't) (a |an )?(issue|concern|factor)\b",
        ],
        "premium_preference": [
            r"\bwent with (the )?(premium|expensive|high.?end|best)\b",
            r"\byou get what you pay for\b",
            r"\b(cheap|budget|affordable) (usually )?means (low )?quality\b",
            r"\binvest(ed)? in (quality|the best)\b",
        ],
        "price_indifference": [
            r"\bdidn't (even )?(look at|check|compare) (the )?price\b",
            r"\bbought it (without|didn't check) (checking |looking at )?(the )?price\b",
            r"\bwould (have )?pay (any|double|triple) (price|amount)\b",
        ],
    },
    
    "application": {
        "high": "Lead with value, ROI, savings, payment plans, comparison to alternatives",
        "moderate": "Balance quality messaging with value justification",
        "low": "Focus on quality, prestige, exclusivity - minimize price discussion"
    }
}


# =============================================================================
# CONSTRUCT 11: RISK AVERSION (DECISION RISK)
# =============================================================================

RISK_AVERSION = {
    "construct_name": "Risk Aversion",
    "description": "Tendency to avoid uncertainty and potential negative outcomes in decisions",
    "mechanism_mapping": ["guarantees", "reassurance", "social_proof", "risk_reversal"],
    
    "high_aversion_markers": {
        "safety_seeking": [
            r"\bwanted to (be|feel|play it) safe\b",
            r"\bdidn't want to (risk|chance|gamble)\b",
            r"\bplaying it safe\b",
            r"\brisk.?free\b.{0,20}\b(important|needed|wanted)\b",
        ],
        "guarantee_importance": [
            r"\b(warranty|guarantee|return policy) (was |is )?(important|key|essential|must)\b",
            r"\bneeded (a |the )?(guarantee|warranty|safety net)\b",
            r"\b(money.?back|satisfaction) guarantee\b.{0,20}\bconvinced\b",
            r"\bwouldn't (buy|purchase) without (a )?(warranty|guarantee)\b",
        ],
        "regret_anticipation": [
            r"\bafraid (of|i'd) regret\b",
            r"\bwhat if (it|this) (doesn't|didn't) work\b",
            r"\bdidn't want to (be stuck|make a mistake|waste)\b",
            r"\bworried (about|i'd) (be disappointed|regret)\b",
        ],
        "research_for_certainty": [
            r"\bresearched (extensively|thoroughly|a lot) (to |before )(be sure|feel confident|reduce risk)\b",
            r"\bneeded (to be |to feel )?(certain|sure|confident)\b",
            r"\bread (every|all) (review|negative) to (make sure|be certain)\b",
        ],
        "proven_preference": [
            r"\bwent with (the )?(safe|proven|established|known)\b",
            r"\bstick with what (works|i know|is proven)\b",
            r"\bdidn't want to (experiment|try something new|take a chance)\b",
        ],
    },
    
    "low_aversion_markers": {
        "risk_comfort": [
            r"\bwilling to (take a |take the )?(risk|chance|gamble)\b",
            r"\bworth the (risk|gamble)\b",
            r"\b(don't|didn't) (mind|worry about) the risk\b",
            r"\btook a (chance|risk|leap)\b",
        ],
        "experimentation": [
            r"\blike (to )?try (new|different) (things|products|brands)\b",
            r"\bexperiment(ing)? with\b",
            r"\bwhat's the worst that (could|can) happen\b",
            r"\bno (risk|harm) in trying\b",
        ],
        "low_guarantee_need": [
            r"\bdon't (need|care about) (the )?(warranty|guarantee)\b",
            r"\b(warranty|guarantee) (wasn't|isn't) (important|a factor)\b",
            r"\bbought (it )?anyway\b.{0,20}\b(no guarantee|no warranty)\b",
        ],
    },
    
    "application": {
        "high": "Lead with guarantees, testimonials, trial periods, established brand trust, risk reversal",
        "moderate": "Balance innovation appeal with safety nets",
        "low": "Novel/cutting-edge appeals work; minimize focus on safety messaging"
    }
}


# =============================================================================
# CONSTRUCT 12: LOYALTY VS VARIETY SEEKING
# =============================================================================

LOYALTY_VS_VARIETY = {
    "construct_name": "Loyalty vs Variety Seeking",
    "description": "Tendency to stick with known brands vs. seek new alternatives",
    "mechanism_mapping": ["brand_loyalty", "novelty", "switching_incentives"],
    
    "high_loyalty_markers": {
        "brand_commitment": [
            r"\b(loyal|loyalty) (to|customer|fan)\b",
            r"\b(always|only) (buy|use|purchase|get) (this brand|from them)\b",
            r"\bbeen (using|buying|with) (them|this brand) for (years|\d+)\b",
            r"\bwouldn't (switch|change|try another)\b",
        ],
        "repeat_purchase": [
            r"\b(bought|ordered|purchased) (this )?(again|multiple times|many times)\b",
            r"\bkeep coming back\b",
            r"\brepeat (customer|buyer|purchase)\b",
            r"\bstock(ed)? up\b",
        ],
        "brand_trust": [
            r"\btrust (this brand|them|their products?)\b",
            r"\bnever (disappoints?|let me down|fails?)\b",
            r"\b(reliable|consistent|dependable) (brand|quality|product)\b",
            r"\bknow what (i'm getting|to expect)\b",
        ],
        "switching_aversion": [
            r"\bwhy (would i|change|switch)\b",
            r"\bno (reason|need) to (switch|try|change)\b",
            r"\bif it ain't broke\b",
            r"\bstick with what (works|i know)\b",
        ],
    },
    
    "high_variety_markers": {
        "novelty_seeking": [
            r"\b(love|like) (to )?try(ing)? (new|different) (things|products?|brands?)\b",
            r"\balways (looking for|trying) something (new|different)\b",
            r"\bvariety is (the spice|important)\b",
            r"\blike to (experiment|explore|mix it up)\b",
        ],
        "brand_switching": [
            r"\bswitch(ed|ing)? (brands?|products?|from)\b",
            r"\btried (many|several|different|various) (brands?|options?)\b",
            r"\bdon't (stick to|stay with) one (brand|product)\b",
            r"\bwanted to try (something|an alternative)\b",
        ],
        "boredom_signals": [
            r"\b(bored|tired) (of|with) (the same|using|my old)\b",
            r"\bneeded (a )?change\b",
            r"\bwanted something (new|fresh|different)\b",
            r"\btime (for|to try) (something new|a change)\b",
        ],
        "deal_switching": [
            r"\bwhoever has the (best|better) (deal|price)\b",
            r"\bswitch(ed)? for (a |the )(deal|price|discount)\b",
            r"\bnot (brand )?(loyal|attached)\b",
        ],
    },
    
    "application": {
        "loyalty_high": "Retention messaging, rewards, exclusive access, brand community",
        "variety_high": "New features, novelty positioning, competitive switching incentives",
        "balanced": "Balance trust messaging with innovation/newness"
    }
}


# =============================================================================
# CONSTRUCT 13: COMPULSIVE BUYING TENDENCY
# =============================================================================

COMPULSIVE_BUYING = {
    "construct_name": "Compulsive Buying Tendency",
    "description": "Tendency toward impulse purchases and emotional buying",
    "mechanism_mapping": ["impulse_triggers", "emotional_appeals", "urgency"],
    
    "high_compulsive_markers": {
        "impulse_buying": [
            r"\b(impulse|impulsive) (buy|purchase|bought|decision)\b",
            r"\b(couldn't|can't) (help|resist|stop) (myself|buying)\b",
            r"\bjust (had to|needed to) (have|get|buy) it\b",
            r"\bbought it (without thinking|on a whim|spontaneously)\b",
        ],
        "emotional_triggers": [
            r"\b(retail )?therapy\b",
            r"\bmade me (happy|feel better|smile)\b",
            r"\b(needed|deserved) (a )?treat\b",
            r"\b(stress|emotional|bored) (buying|shopping|purchase)\b",
        ],
        "regret_signals": [
            r"\b(buyer's|buying) remorse\b",
            r"\bwhy did i (buy|get|order) (this|so many)\b",
            r"\b(shouldn't|didn't need to) have (bought|ordered)\b",
            r"\bimpulse i regret\b",
        ],
        "unplanned_purchase": [
            r"\bwasn't (planning|intending) to (buy|purchase|order)\b",
            r"\bdidn't (need|plan|mean to)\b.{0,20}\b(bought|ordered|got)\b",
            r"\bended up (buying|getting|ordering)\b",
            r"\bsomehow (ended up|came home) with\b",
        ],
        "frequent_buying": [
            r"\b(another|yet another) (one|purchase|order)\b",
            r"\bkeep (buying|ordering|adding to cart)\b",
            r"\bcan't stop (buying|shopping|ordering)\b",
            r"\b(addiction|addicted) (to|buying)\b",
        ],
    },
    
    "low_compulsive_markers": {
        "deliberate_purchase": [
            r"\b(thought|planned|considered) (long and hard|carefully|thoroughly)\b",
            r"\bresearch(ed)? (extensively|carefully|thoroughly)\b",
            r"\b(waited|took my time) (to|before) (buy|purchase|decide)\b",
            r"\bsleep on it\b",
        ],
        "needs_based": [
            r"\bonly (buy|purchase|get) what (i|we) need\b",
            r"\bminimalist\b",
            r"\bcareful (with|about) (spending|purchases|money)\b",
            r"\bbudget and stick to it\b",
        ],
        "self_control": [
            r"\bresisted (the urge|temptation|impulse)\b",
            r"\bput it back\b",
            r"\bwalked away\b",
            r"\bdidn't (need|really need) it\b",
        ],
    },
    
    "application": {
        "high": "Impulse triggers effective, urgency works, emotional appeals, one-click purchase",
        "moderate": "Balanced approach - some urgency but with justification",
        "low": "Rational appeals, value justification, avoid pressure tactics"
    }
}


# =============================================================================
# MAIN ANALYZER CLASS
# =============================================================================

class PersuasionSusceptibilityAnalyzer:
    """
    Analyzes text (reviews, behaviors) for persuasion susceptibility signals.
    
    Unlike trait detection (what someone IS), this detects RESPONSIVENESS
    to specific persuasion techniques (how they RESPOND TO influence).
    """
    
    def __init__(self):
        self.constructs = {
            # Tier 1: Mechanism Selection (from customer reviews)
            "social_proof_susceptibility": SOCIAL_PROOF_SUSCEPTIBILITY,
            "authority_bias_susceptibility": AUTHORITY_BIAS_SUSCEPTIBILITY,
            "scarcity_reactivity": SCARCITY_REACTIVITY,
            "anchoring_susceptibility": ANCHORING_SUSCEPTIBILITY,
            "delay_discounting": DELAY_DISCOUNTING,
            "reactance_tendency": REACTANCE_TENDENCY,
            # Tier 2: Message Crafting (from customer reviews)
            "skepticism_level": SKEPTICISM_LEVEL,
            "information_avoidance": INFORMATION_AVOIDANCE,
            "cognitive_load_tolerance": COGNITIVE_LOAD_TOLERANCE,
            "price_sensitivity": PRICE_SENSITIVITY,
            "risk_aversion": RISK_AVERSION,
            # Tier 3: Brand-Customer Matching (from customer reviews)
            "loyalty_vs_variety": LOYALTY_VS_VARIETY,
            "compulsive_buying": COMPULSIVE_BUYING,
        }
        
        # Compile patterns for efficiency
        self._compiled_patterns = {}
        for construct_name, construct_data in self.constructs.items():
            self._compiled_patterns[construct_name] = {
                "high": self._compile_markers(construct_data.get("high_susceptibility_markers") or 
                                               construct_data.get("high_discounting_markers") or
                                               construct_data.get("high_reactance_markers", {})),
                "low": self._compile_markers(construct_data.get("low_susceptibility_markers") or
                                              construct_data.get("low_discounting_markers") or
                                              construct_data.get("low_reactance_markers", {})),
            }
    
    def _compile_markers(self, marker_dict: Dict[str, List[str]]) -> List[re.Pattern]:
        """Compile regex patterns from marker dictionary."""
        patterns = []
        for category, pattern_list in marker_dict.items():
            for pattern in pattern_list:
                try:
                    patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    pass
        return patterns
    
    def _count_matches(self, text: str, patterns: List[re.Pattern]) -> Tuple[int, List[str]]:
        """Count pattern matches and extract evidence."""
        count = 0
        evidence = []
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                count += len(matches)
                evidence.extend(matches[:3])  # Limit evidence per pattern
        return count, evidence[:10]  # Limit total evidence
    
    def analyze_text(self, text: str) -> Dict[str, SusceptibilityScore]:
        """
        Analyze text for all susceptibility dimensions.
        
        Args:
            text: Review text or other customer language
            
        Returns:
            Dictionary of construct names to SusceptibilityScore objects
        """
        text_lower = text.lower()
        results = {}
        
        for construct_name, patterns in self._compiled_patterns.items():
            high_count, high_evidence = self._count_matches(text_lower, patterns["high"])
            low_count, low_evidence = self._count_matches(text_lower, patterns["low"])
            
            total_signals = high_count + low_count
            
            # Calculate score: high signals push toward 1, low toward 0
            if total_signals == 0:
                score = 0.5  # No signal = neutral
                confidence = 0.0
            else:
                # Weighted calculation
                score = (high_count * 1.0 + low_count * 0.0) / total_signals
                # Confidence based on signal strength
                confidence = min(1.0, total_signals / 5)  # 5+ signals = max confidence
            
            # Combine evidence
            all_evidence = [f"HIGH: {e}" for e in high_evidence] + [f"LOW: {e}" for e in low_evidence]
            
            results[construct_name] = SusceptibilityScore(
                dimension=construct_name,
                score=score,
                confidence=confidence,
                evidence=all_evidence,
                signals_detected=total_signals,
            )
        
        return results
    
    def analyze_reviews(self, reviews: List[str]) -> Dict[str, SusceptibilityScore]:
        """
        Aggregate susceptibility scores across multiple reviews.
        
        Args:
            reviews: List of review texts from the same brand/product
            
        Returns:
            Aggregated susceptibility profile
        """
        if not reviews:
            return {name: SusceptibilityScore(dimension=name, score=0.5, confidence=0.0)
                    for name in self.constructs}
        
        # Analyze each review
        all_scores = defaultdict(list)
        all_evidence = defaultdict(list)
        all_signals = defaultdict(int)
        
        for review in reviews:
            review_scores = self.analyze_text(review)
            for construct, score_obj in review_scores.items():
                if score_obj.confidence > 0:  # Only include reviews with signals
                    all_scores[construct].append(score_obj.score)
                    all_evidence[construct].extend(score_obj.evidence[:3])
                    all_signals[construct] += score_obj.signals_detected
        
        # Aggregate
        results = {}
        for construct_name in self.constructs:
            scores = all_scores[construct_name]
            if scores:
                avg_score = sum(scores) / len(scores)
                # Confidence based on number of reviews with signals
                confidence = min(1.0, len(scores) / 10)  # 10+ reviews with signals = max
            else:
                avg_score = 0.5
                confidence = 0.0
            
            results[construct_name] = SusceptibilityScore(
                dimension=construct_name,
                score=avg_score,
                confidence=confidence,
                evidence=all_evidence[construct_name][:10],
                signals_detected=all_signals[construct_name],
            )
        
        return results
    
    def get_mechanism_recommendations(self, 
                                       susceptibility_profile: Dict[str, SusceptibilityScore]
                                      ) -> Dict[str, Dict[str, Any]]:
        """
        Convert susceptibility profile to mechanism recommendations.
        
        Args:
            susceptibility_profile: Output from analyze_text or analyze_reviews
            
        Returns:
            Mechanism recommendations with effectiveness predictions
        """
        recommendations = {}
        
        mechanism_mapping = {
            # Tier 1: Mechanism Selection
            "social_proof": ("social_proof_susceptibility", 1.0),
            "authority": ("authority_bias_susceptibility", 1.0),
            "expertise": ("authority_bias_susceptibility", 0.9),
            "scarcity": ("scarcity_reactivity", 1.0),
            "urgency": ("scarcity_reactivity", 0.9),
            "fomo": ("scarcity_reactivity", 0.8),
            "anchoring": ("anchoring_susceptibility", 1.0),
            "price_framing": ("anchoring_susceptibility", 0.9),
            "instant_gratification": ("delay_discounting", 1.0),
            "long_term_value": ("delay_discounting", -1.0),  # Inverse
            # Tier 2: Message Crafting
            "evidence_based": ("skepticism_level", 1.0),  # High skeptics need evidence
            "transparency": ("skepticism_level", 0.9),
            "simple_messaging": ("information_avoidance", 1.0),  # High avoiders need simple
            "reassurance": ("information_avoidance", 0.8),
            "detailed_content": ("cognitive_load_tolerance", 1.0),  # High tolerance = detailed
            "simplified_content": ("cognitive_load_tolerance", -1.0),  # Low tolerance = simple
            "value_framing": ("price_sensitivity", 1.0),
            "discount_appeals": ("price_sensitivity", 0.9),
            "premium_positioning": ("price_sensitivity", -1.0),  # Inverse for price sensitive
            "guarantees": ("risk_aversion", 1.0),
            "risk_reversal": ("risk_aversion", 0.9),
            "novelty_appeals": ("risk_aversion", -0.8),  # Inverse - risk averse avoid novelty
            # Tier 3: Brand-Customer Matching
            "brand_loyalty_rewards": ("loyalty_vs_variety", 1.0),  # High loyalty = loyalty programs work
            "novelty_positioning": ("loyalty_vs_variety", -1.0),  # Low loyalty (variety) = novelty works
            "switching_incentives": ("loyalty_vs_variety", -0.8),  # Variety seekers respond to switching
            "impulse_triggers": ("compulsive_buying", 1.0),  # High compulsive = impulse works
            "emotional_purchase_appeals": ("compulsive_buying", 0.9),
            "one_click_purchase": ("compulsive_buying", 0.8),
            "deliberate_consideration": ("compulsive_buying", -0.8),  # Low compulsive = needs deliberation
        }
        
        for mechanism, (construct, weight) in mechanism_mapping.items():
            if construct in susceptibility_profile:
                score_obj = susceptibility_profile[construct]
                
                # Calculate effectiveness
                if weight > 0:
                    effectiveness = score_obj.score * weight
                else:
                    # Inverse relationship
                    effectiveness = (1 - score_obj.score) * abs(weight)
                
                # Adjust confidence
                adjusted_confidence = score_obj.confidence
                
                recommendations[mechanism] = {
                    "effectiveness": effectiveness,
                    "confidence": adjusted_confidence,
                    "level": "high" if effectiveness > 0.6 else "moderate" if effectiveness > 0.3 else "low",
                    "use_recommendation": effectiveness > 0.4,
                }
        
        # Add warnings for key patterns
        warnings = []
        
        # Reactance warning
        if "reactance_tendency" in susceptibility_profile:
            reactance = susceptibility_profile["reactance_tendency"]
            if reactance.score > 0.6 and reactance.confidence > 0.3:
                warnings.append({
                    "type": "high_reactance",
                    "message": "High reactance - avoid pushy messaging, emphasize choice",
                    "affected_mechanisms": ["urgency", "scarcity", "fomo"],
                    "severity": "high",
                })
        
        # Skepticism warning
        if "skepticism_level" in susceptibility_profile:
            skepticism = susceptibility_profile["skepticism_level"]
            if skepticism.score > 0.7 and skepticism.confidence > 0.3:
                warnings.append({
                    "type": "high_skepticism",
                    "message": "High skepticism - lead with evidence, avoid unsubstantiated claims",
                    "affected_mechanisms": ["social_proof", "authority"],
                    "required_elements": ["data", "third_party_validation", "specific_proof"],
                    "severity": "high",
                })
        
        # Information overload risk
        if "cognitive_load_tolerance" in susceptibility_profile:
            cognitive = susceptibility_profile["cognitive_load_tolerance"]
            if cognitive.score < 0.3 and cognitive.confidence > 0.3:
                warnings.append({
                    "type": "low_cognitive_tolerance",
                    "message": "Low cognitive load tolerance - simplify messaging, reduce options",
                    "affected_mechanisms": ["detailed_content", "comparison_tables"],
                    "required_elements": ["simple_copy", "clear_cta", "visual_focus"],
                    "severity": "medium",
                })
        
        # Risk aversion consideration
        if "risk_aversion" in susceptibility_profile:
            risk = susceptibility_profile["risk_aversion"]
            if risk.score > 0.7 and risk.confidence > 0.3:
                warnings.append({
                    "type": "high_risk_aversion",
                    "message": "High risk aversion - emphasize guarantees, testimonials, established trust",
                    "required_elements": ["guarantee", "reviews", "trial_period"],
                    "severity": "high",
                })
        
        # Price sensitivity insight
        if "price_sensitivity" in susceptibility_profile:
            price = susceptibility_profile["price_sensitivity"]
            if price.score > 0.7 and price.confidence > 0.3:
                warnings.append({
                    "type": "high_price_sensitivity",
                    "message": "High price sensitivity - lead with value, ROI, and savings",
                    "required_elements": ["value_proposition", "price_justification", "comparisons"],
                    "severity": "medium",
                })
            elif price.score < 0.3 and price.confidence > 0.3:
                warnings.append({
                    "type": "low_price_sensitivity",
                    "message": "Low price sensitivity - focus on quality/prestige, minimize price discussion",
                    "avoid_elements": ["discount_heavy_messaging", "budget_framing"],
                    "severity": "low",
                })
        
        if warnings:
            recommendations["_warnings"] = warnings
            # Keep backward compatibility
            if any(w["type"] == "high_reactance" for w in warnings):
                recommendations["_warning"] = next(w for w in warnings if w["type"] == "high_reactance")
        
        return recommendations


# =============================================================================
# INTEGRATION WITH ADAM
# =============================================================================

def analyze_customer_susceptibility(reviews: List[str]) -> Dict[str, Any]:
    """
    Convenience function for ADAM integration.
    
    Args:
        reviews: List of customer review texts
        
    Returns:
        Complete susceptibility analysis with mechanism recommendations
    """
    analyzer = PersuasionSusceptibilityAnalyzer()
    
    # Get susceptibility profile
    profile = analyzer.analyze_reviews(reviews)
    
    # Get mechanism recommendations
    recommendations = analyzer.get_mechanism_recommendations(profile)
    
    # Format for ADAM consumption
    result = {
        "susceptibility_profile": {
            name: {
                "score": score.score,
                "level": score.level,
                "confidence": score.confidence,
                "signals_detected": score.signals_detected,
                "evidence": score.evidence,
            }
            for name, score in profile.items()
        },
        "mechanism_recommendations": recommendations,
        "summary": _generate_summary(profile, recommendations),
    }
    
    return result


def _generate_summary(profile: Dict[str, SusceptibilityScore],
                      recommendations: Dict[str, Dict[str, Any]]) -> str:
    """Generate human-readable summary of susceptibility analysis."""
    
    # Find highest susceptibilities
    high_suscept = [(name, score) for name, score in profile.items() 
                    if score.score > 0.6 and score.confidence > 0.3]
    high_suscept.sort(key=lambda x: x[1].score, reverse=True)
    
    # Find low susceptibilities (resistance)
    low_suscept = [(name, score) for name, score in profile.items()
                   if score.score < 0.4 and score.confidence > 0.3]
    
    parts = []
    
    if high_suscept:
        names = [s[0].replace("_", " ").title() for s in high_suscept[:3]]
        parts.append(f"High responsiveness to: {', '.join(names)}")
    
    if low_suscept:
        names = [s[0].replace("_", " ").title() for s in low_suscept[:2]]
        parts.append(f"Low responsiveness to: {', '.join(names)}")
    
    if "_warning" in recommendations:
        parts.append(f"⚠️ {recommendations['_warning']['message']}")
    
    return " | ".join(parts) if parts else "Neutral susceptibility profile"


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example reviews demonstrating different susceptibility patterns
    example_reviews = [
        "After reading all the positive reviews, I decided to give it a try. So many people love this!",
        "The 4.8 star rating convinced me. Everyone seems to recommend it.",
        "Was originally $150, now only $89 - couldn't pass up the savings!",
        "Only 3 left in stock so I grabbed it quickly. Didn't want to miss out.",
        "My doctor recommended this brand specifically, so I trust it.",
    ]
    
    result = analyze_customer_susceptibility(example_reviews)
    
    print("=" * 60)
    print("PERSUASION SUSCEPTIBILITY ANALYSIS")
    print("=" * 60)
    
    print("\nSusceptibility Profile:")
    for name, data in result["susceptibility_profile"].items():
        print(f"  {name}: {data['score']:.2f} ({data['level']}) - {data['signals_detected']} signals")
    
    print(f"\nSummary: {result['summary']}")
    
    print("\nMechanism Recommendations:")
    for mech, data in result["mechanism_recommendations"].items():
        if mech != "_warning":
            print(f"  {mech}: {data['effectiveness']:.2f} effectiveness - {'USE' if data['use_recommendation'] else 'AVOID'}")
