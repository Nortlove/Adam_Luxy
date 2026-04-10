#!/usr/bin/env python3
"""
ADAM BRAND TRAIT EXTRACTION FRAMEWORK
=====================================

Extracts brand positioning and communication traits from brand descriptions.
These traits inform how to match brands with customer segments and channels.

CRITICAL DISTINCTION:
- Customer Susceptibility (Tier 1-2): How customers RESPOND to persuasion
- Brand Traits (Tier 3): How brands POSITION themselves in communications

Data Source: Brand descriptions, about pages, marketing copy, product descriptions

BRAND TRAITS EXTRACTED:
1. Trust Communication - How brand builds trust (guarantees, history, transparency)
2. Authority Positioning - Expert/professional vs. peer/friendly positioning
3. Innovation vs Heritage - Cutting-edge vs. established/traditional
4. Accessibility vs Exclusivity - Mass market vs. premium/exclusive
5. Emotional vs Rational Appeal - Feelings-focused vs. logic/specs-focused
6. Value Proposition Type - Price, quality, convenience, status, etc.
7. Social Responsibility - CSR, sustainability, community messaging
8. Authenticity Signals - Genuine/founder-led vs. corporate
9. Risk Mitigation Messaging - Guarantees, warranties, trial offers
10. Urgency/Scarcity Usage - How brand uses urgency tactics

Usage:
    These traits determine:
    - Which customer segments the brand aligns with
    - Which persuasion mechanisms fit the brand voice
    - Optimal channel/format matching
    - Message tone and complexity calibration
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BrandTraitScore:
    """Score for a brand trait dimension."""
    trait: str
    score: float  # 0-1 scale, interpretation depends on trait
    confidence: float  # 0-1 based on signal strength
    evidence: List[str] = field(default_factory=list)
    signals_detected: int = 0
    
    @property
    def level(self) -> str:
        """Categorical level."""
        if self.score >= 0.7:
            return "high"
        elif self.score >= 0.4:
            return "moderate"
        else:
            return "low"


# =============================================================================
# TRAIT 1: TRUST COMMUNICATION STYLE
# =============================================================================

TRUST_COMMUNICATION = {
    "trait_name": "Trust Communication",
    "description": "How the brand builds and communicates trustworthiness",
    "customer_alignment": {
        "high_trust_messaging": ["risk_averse", "skeptical"],
        "low_trust_messaging": ["early_adopter", "risk_tolerant"],
    },
    
    "high_trust_markers": {
        "guarantee_language": [
            r"\b(money.?back|satisfaction|100%?) guarantee\w*\b",
            r"\brisk.?free (trial|return|purchase)\b",
            r"\bno.?(questions?.?asked|hassle) return\w*\b",
            r"\b(full|complete) refund\b",
            r"\b(free|easy) return\w*\b",
        ],
        "history_heritage": [
            r"\b(since|founded|established|serving) \d{4}\b",
            r"\b(\d+|over \d+) years (of experience|in business|serving)\b",
            r"\bgeneration\w*\b.{0,20}\b(family|tradition)\b",
            r"\btime.?tested\b",
            r"\btrusted (for|by)\b.{0,20}\b(years|decades|generations)\b",
        ],
        "certification_validation": [
            r"\b(certified|accredited|licensed|approved)\b.{0,20}\b(by|from)\b",
            r"\b(fda|usda|iso|gmp|organic|non.?gmo)\b.{0,10}\b(certified|approved)\b",
            r"\bthird.?party (tested|verified|certified)\b",
            r"\bindependent(ly)? (tested|verified|audited)\b",
        ],
        "transparency_signals": [
            r"\b(transparent|transparency|openly|honest)\w*\b",
            r"\bnothing to hide\b",
            r"\bfull (disclosure|ingredient\w*|label)\b",
            r"\bsee (exactly|precisely) what\b",
        ],
        "social_proof_claims": [
            r"\b(trusted by|serving|used by)\b.{0,20}\b(\d+|millions?|thousands?|hundreds?)\b",
            r"\b(award.?winning|highly.?rated|top.?rated)\b",
            r"\b(\d+\.?\d*)\+? (star|out of \d) (rating|reviews?)\b",
        ],
    },
    
    "low_trust_markers": {
        "new_unproven": [
            r"\b(brand.?new|just launched|introducing)\b",
            r"\b(startup|new company|newly founded)\b",
            r"\bfirst (time|ever)\b.{0,20}\b(offering|available)\b",
        ],
        "no_guarantees": [
            r"\b(all sales?|no) (final|refunds?|returns?)\b",
            r"\bas.?is\b",
            r"\bno (warranty|guarantee)\b",
        ],
    },
    
    "application": {
        "high": "Brand heavily emphasizes trust - match with risk-averse customers, lead with guarantees",
        "moderate": "Standard trust messaging - balanced approach",
        "low": "Brand doesn't emphasize trust - may appeal to early adopters, avoid guarantee-focused messaging"
    }
}


# =============================================================================
# TRAIT 2: AUTHORITY POSITIONING
# =============================================================================

AUTHORITY_POSITIONING = {
    "trait_name": "Authority Positioning",
    "description": "How the brand positions expertise and credibility",
    "customer_alignment": {
        "high_authority": ["authority_susceptible", "expert_seekers"],
        "low_authority": ["peer_oriented", "authenticity_seekers"],
    },
    
    "high_authority_markers": {
        "expert_credentials": [
            r"\b(expert|specialist|professional)\w*\b.{0,20}\b(team|staff|formulated|developed)\b",
            r"\b(doctor|scientist|engineer|researcher)\w*\b.{0,20}\b(developed|created|formulated)\b",
            r"\b(phd|md|dds|pe|cpa)\w*\b",
            r"\bboard.?certified\b",
        ],
        "research_claims": [
            r"\b(clinically|scientifically|research).?(proven|tested|backed|studied)\b",
            r"\bpeer.?reviewed\b",
            r"\b(studies|research|trials?) (show|prove|demonstrate)\b",
            r"\bpatented\b.{0,20}\b(formula|technology|process)\b",
        ],
        "industry_leadership": [
            r"\b(industry|market) leader\w*\b",
            r"\b(leading|premier|top) (brand|company|provider)\b",
            r"\b(pioneer|innovator)\w*\b.{0,15}\b(in|of)\b",
            r"\bsetting the standard\b",
        ],
        "institutional_backing": [
            r"\b(used|trusted|recommended) by (professional|doctor|expert)\w*\b",
            r"\b(hospital|clinic|university)\b.{0,20}\b(uses?|trusts?|partners?)\b",
            r"\bas (seen|featured) (on|in)\b.{0,20}\b(news|tv|magazine)\b",
        ],
    },
    
    "low_authority_markers": {
        "peer_positioning": [
            r"\b(by|from) (people|folks|someone) (like you|who understand)\b",
            r"\bmade (by|for) (real|everyday|regular) people\b",
            r"\bwe('re| are) (just like|one of) you\b",
            r"\bfrom (our|one) family to yours\b",
        ],
        "community_focus": [
            r"\bcommunity.?(driven|focused|built)\b",
            r"\b(small|local) business\b",
            r"\bhandmade\b",
            r"\bartisan\w*\b",
        ],
    },
    
    "application": {
        "high": "Brand leads with expertise - match with authority-susceptible customers, expert endorsement mechanisms",
        "moderate": "Balanced authority - can flex between expert and relatable",
        "low": "Brand positions as peer/relatable - match with authenticity-seekers, avoid expert-heavy messaging"
    }
}


# =============================================================================
# TRAIT 3: INNOVATION VS HERITAGE
# =============================================================================

INNOVATION_VS_HERITAGE = {
    "trait_name": "Innovation vs Heritage",
    "description": "Whether brand positions as cutting-edge or traditional/established",
    "customer_alignment": {
        "high_innovation": ["early_adopters", "novelty_seekers", "tech_savvy"],
        "high_heritage": ["traditionalists", "risk_averse", "quality_focused"],
    },
    
    "innovation_markers": {
        "cutting_edge": [
            r"\b(cutting.?edge|state.?of.?the.?art|next.?gen(eration)?|advanced)\b",
            r"\b(revolutionary|breakthrough|game.?chang\w*|disruptive)\b",
            r"\b(innovative|innovation)\w*\b",
            r"\bfirst (of its kind|ever|to market)\b",
        ],
        "technology_focus": [
            r"\b(technology|tech|ai|ml|smart|intelligent)\b.{0,15}\b(powered|driven|enabled)\b",
            r"\bproprietary (technology|algorithm|system)\b",
            r"\b(latest|newest) (technology|innovation|advancement)\b",
        ],
        "future_oriented": [
            r"\bfuture (of|proof|ready|forward)\b",
            r"\b(reimagin|reinvent|transform)\w*\b",
            r"\bchanging (the way|how)\b",
        ],
    },
    
    "heritage_markers": {
        "tradition_history": [
            r"\b(traditional|time.?honored|classic)\b",
            r"\b(heritage|legacy|history)\b",
            r"\b(original|authentic) (recipe|formula|method)\b",
            r"\b(handed down|passed down|generation)\w*\b",
        ],
        "established_stability": [
            r"\b(established|trusted|proven|reliable)\b.{0,15}\b(brand|company|name)\b",
            r"\b(since|over) \d{2,4} years?\b",
            r"\bstanding the test of time\b",
        ],
        "craftsmanship": [
            r"\bcrafts?(man|woman)?ship\b",
            r"\bhand.?(made|crafted|finished)\b",
            r"\bartisan\w*\b",
            r"\bsmall.?batch\b",
        ],
    },
    
    "application": {
        "innovation_high": "Brand leads with innovation - match with early adopters, novelty mechanisms",
        "heritage_high": "Brand leads with heritage - match with traditionalists, trust/proof mechanisms",
        "balanced": "Brand balances both - can appeal to broader audience"
    }
}


# =============================================================================
# TRAIT 4: ACCESSIBILITY VS EXCLUSIVITY
# =============================================================================

ACCESSIBILITY_VS_EXCLUSIVITY = {
    "trait_name": "Accessibility vs Exclusivity",
    "description": "Mass market accessibility vs premium/exclusive positioning",
    "customer_alignment": {
        "high_accessibility": ["value_seekers", "price_sensitive"],
        "high_exclusivity": ["status_seekers", "premium_buyers"],
    },
    
    "accessibility_markers": {
        "affordability": [
            r"\b(affordable|budget.?friendly|low.?cost|economical)\b",
            r"\bwon't break the bank\b",
            r"\b(great|best) value\b",
            r"\b(save|saving)\w*\b.{0,15}\b(money|cost|price)\b",
        ],
        "mass_availability": [
            r"\b(available|sold) (everywhere|nationwide|online)\b",
            r"\bfor everyone\b",
            r"\b(accessible|easy to get)\b",
            r"\bno (membership|subscription) (required|needed)\b",
        ],
        "inclusive_language": [
            r"\b(everyone|anybody|all)\b.{0,15}\b(can|deserve)\b",
            r"\bmade for (real|everyday|all) (people|users?|customer)\w*\b",
            r"\bwelcom\w* (all|everyone)\b",
        ],
    },
    
    "exclusivity_markers": {
        "premium_positioning": [
            r"\b(premium|luxury|high.?end|elite|exclusive)\b",
            r"\bworld.?class\b",
            r"\b(finest|best|superior) (quality|materials?|ingredients?)\b",
            r"\b(top|ultra).?premium\b",
        ],
        "limited_access": [
            r"\b(limited|exclusive|select|by invitation)\b.{0,15}\b(access|availability|edition|membership)\b",
            r"\bmembers? only\b",
            r"\bwaitlist\b",
            r"\b(rare|scarce|limited.?edition)\b",
        ],
        "status_signaling": [
            r"\b(status|prestige|sophisticated|discerning)\b",
            r"\b(for|designed for|made for) (connoisseur|enthusiast|aficionado)\w*\b",
            r"\bthose who (demand|expect|appreciate) the (best|finest)\b",
        ],
    },
    
    "application": {
        "accessibility_high": "Mass market positioning - lead with value, broad appeal, ROI",
        "exclusivity_high": "Premium positioning - lead with quality, status, exclusivity mechanisms",
        "balanced": "Mid-market positioning - balance value and quality messaging"
    }
}


# =============================================================================
# TRAIT 5: EMOTIONAL VS RATIONAL APPEAL
# =============================================================================

EMOTIONAL_VS_RATIONAL = {
    "trait_name": "Emotional vs Rational Appeal",
    "description": "Whether brand communications emphasize feelings or logic/specs",
    "customer_alignment": {
        "high_emotional": ["feeling_oriented", "low_need_for_cognition"],
        "high_rational": ["analytical", "high_need_for_cognition"],
    },
    
    "emotional_markers": {
        "feeling_language": [
            r"\b(feel|feeling)\w*\b.{0,15}\b(amazing|great|confident|beautiful|loved)\b",
            r"\b(love|joy|happiness|peace|comfort)\b",
            r"\b(inspire|inspiring|inspirational)\w*\b",
            r"\b(dream|dreaming|dreams?)\b.{0,10}\b(come true|achieve|live)\b",
        ],
        "sensory_experience": [
            r"\b(experience|sensation|feeling)\b.{0,15}\b(like no other|unforgettable|incredible)\b",
            r"\bindulg\w*\b",
            r"\bpamper\w*\b",
            r"\b(treat|reward) yourself\b",
        ],
        "lifestyle_imagery": [
            r"\b(lifestyle|living your best|transform your)\b",
            r"\b(imagine|picture|envision)\b.{0,15}\b(yourself|your life)\b",
            r"\byou deserve\b",
        ],
        "story_narrative": [
            r"\b(story|journey|adventure)\b",
            r"\b(our|the) founder\b",
            r"\b(passion|passionate|heart)\b.{0,15}\b(behind|drives?|creating)\b",
        ],
    },
    
    "rational_markers": {
        "specifications": [
            r"\b(specification|specs?|technical|performance)\b",
            r"\b\d+\s?(gb|tb|mhz|ghz|mah|mp|fps|hz)\b",
            r"\b(dimensions?|measurements?|weight|size)\b.{0,10}\b[:=]\b",
            r"\b(capacity|speed|resolution|accuracy)\b",
        ],
        "comparison_data": [
            r"\b(compared to|vs\.?|versus)\b.{0,20}\b(competitors?|alternatives?|others?)\b",
            r"\b(\d+%?|twice|triple|half)\b.{0,15}\b(more|less|better|faster)\b",
            r"\b(benchmark|performance|test) (results?|data)\b",
        ],
        "logical_structure": [
            r"\b(because|therefore|as a result|consequently)\b",
            r"\b(feature|benefit|advantage)\w*\b.{0,5}\b[:=]\b",
            r"\b(proven|evidence|data) (shows?|suggests?|indicates?)\b",
        ],
        "roi_focus": [
            r"\b(roi|return on investment|cost.?savings?)\b",
            r"\bpay(s)? for itself\b",
            r"\b(save|saving)\w*\b.{0,15}\b(\$|dollar|money|time|hour)\b",
            r"\b(efficiency|productivity|performance) (gain|improvement)\b",
        ],
    },
    
    "application": {
        "emotional_high": "Brand leads with emotion - match with feeling-oriented customers, storytelling mechanisms",
        "rational_high": "Brand leads with logic - match with analytical customers, evidence mechanisms",
        "balanced": "Brand uses both - can adapt messaging to customer type"
    }
}


# =============================================================================
# TRAIT 6: VALUE PROPOSITION TYPE
# =============================================================================

VALUE_PROPOSITION_TYPE = {
    "trait_name": "Value Proposition Type",
    "description": "Primary value proposition the brand emphasizes",
    "customer_alignment": {
        "price_value": ["price_sensitive", "value_seekers"],
        "quality_value": ["quality_focused", "premium_buyers"],
        "convenience_value": ["time_constrained", "efficiency_seekers"],
        "status_value": ["status_seekers", "self_monitors"],
    },
    
    "price_value_markers": [
        r"\b(best|lowest|unbeatable|competitive) price\w*\b",
        r"\b(save|savings?)\b.{0,15}\b(\d+%?|\$\d+)\b",
        r"\b(cheap|affordable|budget|discount|deal)\w*\b",
        r"\bmore (bang|value) for (your|the) buck\b",
    ],
    
    "quality_value_markers": [
        r"\b(premium|superior|exceptional|outstanding|finest) quality\b",
        r"\b(best|top) (in class|of the best|quality)\b",
        r"\b(quality|excellence) (you can|that) (trust|depend|count)\b",
        r"\bno (compromise|shortcuts?) (on|in) quality\b",
    ],
    
    "convenience_value_markers": [
        r"\b(easy|simple|quick|fast|effortless)\b.{0,15}\b(to use|setup|install|order)\b",
        r"\bsave(s)? (you )?(time|effort|hassle)\b",
        r"\b(delivered|shipped)\b.{0,15}\b(to your door|fast|free)\b",
        r"\bone.?(click|stop|step)\b",
    ],
    
    "status_value_markers": [
        r"\b(prestige|prestigious|exclusive|elite)\b",
        r"\b(luxury|luxurious|high.?end)\b",
        r"\b(status|symbol|statement)\b",
        r"\bfor (those|people) who (demand|expect|appreciate) the (best|finest)\b",
    ],
    
    "innovation_value_markers": [
        r"\b(innovative|revolutionary|breakthrough|cutting.?edge)\b",
        r"\b(first|only) (to|one to)\b.{0,20}\b(offer|provide|feature)\b",
        r"\b(unique|proprietary|patented)\b.{0,15}\b(technology|feature|design)\b",
    ],
    
    "application": {
        "price": "Match with price-sensitive customers, value-framing mechanisms",
        "quality": "Match with quality-focused customers, premium mechanisms",
        "convenience": "Match with time-constrained customers, simplicity mechanisms",
        "status": "Match with status-seekers, exclusivity mechanisms",
        "innovation": "Match with early adopters, novelty mechanisms"
    }
}


# =============================================================================
# TRAIT 7: SOCIAL RESPONSIBILITY MESSAGING
# =============================================================================

SOCIAL_RESPONSIBILITY = {
    "trait_name": "Social Responsibility",
    "description": "How much brand emphasizes CSR, sustainability, ethics",
    "customer_alignment": {
        "high_csr": ["values_driven", "socially_conscious"],
        "low_csr": ["pragmatic", "value_focused"],
    },
    
    "high_responsibility_markers": {
        "environmental": [
            r"\b(sustainable|sustainability|eco.?friendly|green|environmental)\w*\b",
            r"\b(carbon|climate) (neutral|positive|footprint)\b",
            r"\b(recycl\w*|biodegradable|compostable)\b",
            r"\b(renewable|organic|natural)\b.{0,15}\b(materials?|ingredients?|sourced)\b",
        ],
        "social_impact": [
            r"\b(give|giving) back\b",
            r"\b(portion|percentage|\d+%?) (of|from) (sales?|proceeds?|profits?)\b.{0,20}\b(goes?|donated|supports?)\b",
            r"\b(support|help)\w*\b.{0,15}\b(community|cause|charity|nonprofit)\b",
            r"\b(social|community) (impact|mission|responsibility)\b",
        ],
        "ethical_sourcing": [
            r"\b(ethically?|responsibly?) (sourced|made|produced|manufactured)\b",
            r"\bfair.?trade\b",
            r"\b(cruelty|animal).?free\b",
            r"\b(vegan|plant.?based)\b",
        ],
        "transparency_values": [
            r"\b(transparent|transparency) (about|in)\b.{0,20}\b(sourcing|supply|production)\b",
            r"\b(know|trace) where (it|your product) comes from\b",
            r"\bsupply chain (transparency|visibility)\b",
        ],
    },
    
    "low_responsibility_markers": {
        "no_csr_messaging": [
            # Absence of CSR language combined with pure value/performance focus
        ],
    },
    
    "application": {
        "high": "Brand leads with values - match with conscious consumers, values-based mechanisms",
        "moderate": "Some CSR messaging - can appeal to broader audience",
        "low": "Minimal CSR - focus on product performance, avoid values-based messaging"
    }
}


# =============================================================================
# TRAIT 8: AUTHENTICITY SIGNALS
# =============================================================================

AUTHENTICITY_SIGNALS = {
    "trait_name": "Authenticity Signals",
    "description": "Genuine/founder-led vs corporate positioning",
    "customer_alignment": {
        "high_authenticity": ["authenticity_seekers", "small_business_supporters"],
        "low_authenticity": ["brand_agnostic", "convenience_seekers"],
    },
    
    "high_authenticity_markers": {
        "founder_story": [
            r"\b(founded|started|created) by\b",
            r"\b(our|the) founder\w*\b",
            r"\b(family|mom.?and.?pop|husband.?and.?wife|family.?owned)\b",
            r"\bborn (out of|from)\b.{0,20}\b(passion|frustration|need)\b",
        ],
        "personal_touch": [
            r"\bpersonal(ly)? (crafted|made|created|selected)\b",
            r"\b(we|i) (personally|hand)\b",
            r"\b(small|local|indie|independent)\b.{0,10}\b(business|company|brand)\b",
        ],
        "real_story": [
            r"\b(real|true|genuine|authentic) (story|people|ingredients?)\b",
            r"\bno (bs|nonsense|gimmicks?|pretense)\b",
            r"\bwhat you see is what you get\b",
            r"\bhonest(ly)?\b.{0,15}\b(made|crafted|about)\b",
        ],
        "behind_scenes": [
            r"\b(behind the scenes?|how we make|our process)\b",
            r"\bmeet (the|our) (team|makers?|creators?)\b",
            r"\b(visit|tour) (our|the) (factory|workshop|farm)\b",
        ],
    },
    
    "low_authenticity_markers": {
        "corporate_language": [
            r"\b(leading|global|multinational|enterprise)\b.{0,10}\b(brand|company|corporation)\b",
            r"\b(leveraging|synergy|stakeholder|deliverable)\w*\b",
            r"\b(optimize|maximize|scalable)\w*\b.{0,15}\b(solution|platform)\b",
        ],
    },
    
    "application": {
        "high": "Brand emphasizes authenticity - match with authenticity-seekers, storytelling mechanisms",
        "moderate": "Some authentic elements - balanced approach",
        "low": "Corporate positioning - focus on brand scale, reliability, professionalism"
    }
}


# =============================================================================
# TRAIT 9: RISK MITIGATION MESSAGING
# =============================================================================

RISK_MITIGATION = {
    "trait_name": "Risk Mitigation Messaging",
    "description": "How much brand emphasizes reducing purchase risk",
    "customer_alignment": {
        "high_mitigation": ["risk_averse", "cautious_buyers"],
        "low_mitigation": ["confident_buyers", "low_research"],
    },
    
    "high_mitigation_markers": {
        "guarantees": [
            r"\b(money.?back|satisfaction|happiness) guarantee\w*\b",
            r"\b(\d+).?day (trial|return|guarantee)\b",
            r"\brisk.?free (trial|purchase|order)\b",
            r"\bno (questions? asked|hassle) return\w*\b",
        ],
        "warranties": [
            r"\b(lifetime|(\d+).?year|extended) warranty\b",
            r"\b(warranted|warrants?|guaranteed) (for|against)\b",
            r"\bprotection plan\b",
        ],
        "trial_offers": [
            r"\btry (it )?(for )?(free|before you buy)\b",
            r"\bfree (trial|sample|demo)\b",
            r"\b(test|try) (it out|before)\b.{0,15}\b(commit|buy)\b",
        ],
        "reassurance_language": [
            r"\b(safe|secure) (purchase|checkout|ordering)\b",
            r"\byou('re| are) (protected|covered)\b",
            r"\bnothing to (lose|risk)\b",
            r"\bworst case\b.{0,15}\b(return|refund|get your money back)\b",
        ],
    },
    
    "low_mitigation_markers": {
        "final_sale": [
            r"\b(all sales?|no) (final|refunds?|returns?)\b",
            r"\bas.?is\b",
            r"\bnon.?refundable\b",
        ],
    },
    
    "application": {
        "high": "Brand reduces risk heavily - match with risk-averse customers, guarantee mechanisms",
        "moderate": "Standard policies - balanced approach",
        "low": "Limited risk mitigation - may appeal to confident buyers, avoid risk-focused messaging"
    }
}


# =============================================================================
# TRAIT 10: URGENCY/SCARCITY USAGE
# =============================================================================

URGENCY_SCARCITY_USAGE = {
    "trait_name": "Urgency/Scarcity Usage",
    "description": "How much brand uses urgency and scarcity tactics in communications",
    "customer_alignment": {
        "high_urgency": ["scarcity_reactive", "fomo_susceptible"],
        "low_urgency": ["deliberate_buyers", "high_reactance"],
    },
    
    "high_urgency_markers": {
        "time_pressure": [
            r"\b(limited|for a limited) time (only|offer)\b",
            r"\b(offer|sale|deal) (ends|expires|ending)\b",
            r"\b(act|order|buy) (now|today|fast)\b",
            r"\b(last|final) chance\b",
            r"\b(hurry|don't wait|don't miss)\b",
        ],
        "quantity_scarcity": [
            r"\b(only|just) (\d+|a few|limited) (left|remaining|available)\b",
            r"\b(selling|going) fast\b",
            r"\b(limited|low|almost out of) (stock|inventory|supply)\b",
            r"\bwhile (supplies|they) last\b",
        ],
        "exclusive_access": [
            r"\b(exclusive|limited|special) (access|offer|edition)\b",
            r"\bfirst come,? first serve\w*\b",
            r"\b(members?|subscribers?) only\b",
            r"\binvitation only\b",
        ],
        "fomo_triggers": [
            r"\bdon't miss (out|this|your chance)\b",
            r"\b(join|be one of|become) the (\d+|few|select)\b",
            r"\beveryone('s| is) (getting|buying|talking about)\b",
        ],
    },
    
    "low_urgency_markers": {
        "always_available": [
            r"\b(always|everday|anytime) available\b",
            r"\bno (rush|pressure|deadline)\b",
            r"\btake your time\b",
            r"\bwhenever you('re| are) ready\b",
        ],
        "anti_pressure": [
            r"\bno (pressure|pushy) (sales?|tactics?)\b",
            r"\bno (obligation|commitment) (to buy|required)\b",
            r"\bbrowse at your (leisure|pace)\b",
        ],
    },
    
    "application": {
        "high": "Brand uses urgency heavily - match with scarcity-reactive, urgency mechanisms work",
        "moderate": "Some urgency - use selectively",
        "low": "Brand avoids urgency - match with deliberate buyers, avoid pressure tactics"
    }
}


# =============================================================================
# MAIN ANALYZER CLASS
# =============================================================================

class BrandTraitAnalyzer:
    """
    Analyzes brand descriptions to extract positioning and communication traits.
    
    Unlike customer susceptibility (how customers RESPOND), this detects
    how brands POSITION themselves in communications.
    """
    
    def __init__(self):
        self.traits = {
            "trust_communication": TRUST_COMMUNICATION,
            "authority_positioning": AUTHORITY_POSITIONING,
            "innovation_vs_heritage": INNOVATION_VS_HERITAGE,
            "accessibility_vs_exclusivity": ACCESSIBILITY_VS_EXCLUSIVITY,
            "emotional_vs_rational": EMOTIONAL_VS_RATIONAL,
            "value_proposition_type": VALUE_PROPOSITION_TYPE,
            "social_responsibility": SOCIAL_RESPONSIBILITY,
            "authenticity_signals": AUTHENTICITY_SIGNALS,
            "risk_mitigation": RISK_MITIGATION,
            "urgency_scarcity_usage": URGENCY_SCARCITY_USAGE,
        }
        
        # Compile patterns
        self._compiled_patterns = {}
        for trait_name, trait_data in self.traits.items():
            self._compiled_patterns[trait_name] = self._compile_trait_patterns(trait_data)
    
    def _compile_trait_patterns(self, trait_data: Dict) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns from trait data."""
        compiled = {"high": [], "low": []}
        
        # Find marker dictionaries
        for key, value in trait_data.items():
            if key.endswith("_markers") and isinstance(value, dict):
                direction = "high" if any(h in key.lower() for h in ["high", "innovation", "emotional", "accessibility", "price", "quality", "convenience", "status", "authenticity"]) else "low"
                if "low" in key.lower():
                    direction = "low"
                
                for category, patterns in value.items():
                    if isinstance(patterns, list):
                        for pattern in patterns:
                            try:
                                compiled[direction].append(re.compile(pattern, re.IGNORECASE))
                            except re.error:
                                pass
            elif key.endswith("_markers") and isinstance(value, list):
                # Direct list of patterns (like value_proposition subtypes)
                direction = "high"
                for pattern in value:
                    try:
                        compiled[direction].append(re.compile(pattern, re.IGNORECASE))
                    except re.error:
                        pass
        
        return compiled
    
    def _count_matches(self, text: str, patterns: List[re.Pattern]) -> Tuple[int, List[str]]:
        """Count pattern matches and extract evidence."""
        count = 0
        evidence = []
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                count += len(matches)
                # Store the matches as evidence
                if isinstance(matches[0], tuple):
                    evidence.extend([m[0] if m[0] else m for m in matches[:3]])
                else:
                    evidence.extend(matches[:3])
        return count, evidence[:10]
    
    def analyze_description(self, text: str) -> Dict[str, BrandTraitScore]:
        """
        Analyze brand description for all trait dimensions.
        
        Args:
            text: Brand description, about page, marketing copy
            
        Returns:
            Dictionary of trait names to BrandTraitScore objects
        """
        text_lower = text.lower()
        results = {}
        
        for trait_name, patterns in self._compiled_patterns.items():
            high_count, high_evidence = self._count_matches(text_lower, patterns["high"])
            low_count, low_evidence = self._count_matches(text_lower, patterns["low"])
            
            total_signals = high_count + low_count
            
            if total_signals == 0:
                score = 0.5
                confidence = 0.0
            else:
                score = high_count / total_signals
                confidence = min(1.0, total_signals / 5)
            
            all_evidence = [f"HIGH: {e}" for e in high_evidence] + [f"LOW: {e}" for e in low_evidence]
            
            results[trait_name] = BrandTraitScore(
                trait=trait_name,
                score=score,
                confidence=confidence,
                evidence=all_evidence,
                signals_detected=total_signals,
            )
        
        return results
    
    def analyze_brand(self, descriptions: List[str]) -> Dict[str, BrandTraitScore]:
        """
        Aggregate trait scores across multiple brand descriptions.
        
        Args:
            descriptions: List of brand description texts
            
        Returns:
            Aggregated brand trait profile
        """
        if not descriptions:
            return {name: BrandTraitScore(trait=name, score=0.5, confidence=0.0)
                    for name in self.traits}
        
        # Analyze each description
        all_scores = defaultdict(list)
        all_evidence = defaultdict(list)
        all_signals = defaultdict(int)
        
        for desc in descriptions:
            desc_scores = self.analyze_description(desc)
            for trait, score_obj in desc_scores.items():
                if score_obj.confidence > 0:
                    all_scores[trait].append(score_obj.score)
                    all_evidence[trait].extend(score_obj.evidence[:5])
                    all_signals[trait] += score_obj.signals_detected
        
        # Aggregate
        results = {}
        for trait_name in self.traits:
            scores = all_scores[trait_name]
            if scores:
                avg_score = sum(scores) / len(scores)
                confidence = min(1.0, len(scores) / 3)  # 3+ descriptions = max
            else:
                avg_score = 0.5
                confidence = 0.0
            
            results[trait_name] = BrandTraitScore(
                trait=trait_name,
                score=avg_score,
                confidence=confidence,
                evidence=all_evidence[trait_name][:10],
                signals_detected=all_signals[trait_name],
            )
        
        return results
    
    def get_customer_alignment(self, 
                                brand_profile: Dict[str, BrandTraitScore]
                               ) -> Dict[str, Any]:
        """
        Determine which customer types align with this brand's positioning.
        
        Args:
            brand_profile: Output from analyze_description or analyze_brand
            
        Returns:
            Customer segment alignment recommendations
        """
        alignments = {
            "strong_alignment": [],
            "moderate_alignment": [],
            "misalignment": [],
            "mechanism_recommendations": [],
        }
        
        # Analyze each trait for customer alignment
        for trait_name, score_obj in brand_profile.items():
            trait_data = self.traits.get(trait_name, {})
            customer_alignment = trait_data.get("customer_alignment", {})
            
            if score_obj.confidence < 0.3:
                continue
            
            if score_obj.score > 0.6:  # High on this trait
                # Find which customers align with high values
                for alignment_key in ["high_trust_messaging", "high_authority", "high_innovation",
                                       "high_csr", "high_authenticity", "high_mitigation",
                                       "high_urgency", "high_exclusivity", "high_emotional"]:
                    if alignment_key in customer_alignment:
                        alignments["strong_alignment"].extend(customer_alignment[alignment_key])
            elif score_obj.score < 0.4:  # Low on this trait
                for alignment_key in ["low_trust_messaging", "low_authority", "low_csr",
                                       "low_authenticity", "low_mitigation", "low_urgency"]:
                    if alignment_key in customer_alignment:
                        alignments["moderate_alignment"].extend(customer_alignment[alignment_key])
        
        # Deduplicate
        alignments["strong_alignment"] = list(set(alignments["strong_alignment"]))
        alignments["moderate_alignment"] = list(set(alignments["moderate_alignment"]))
        
        # Generate mechanism recommendations based on brand positioning
        if brand_profile.get("trust_communication", BrandTraitScore("", 0.5, 0)).score > 0.6:
            alignments["mechanism_recommendations"].append({
                "mechanism": "guarantee",
                "strength": "high",
                "reason": "Brand emphasizes trust - guarantee mechanisms align"
            })
        
        if brand_profile.get("authority_positioning", BrandTraitScore("", 0.5, 0)).score > 0.6:
            alignments["mechanism_recommendations"].append({
                "mechanism": "authority",
                "strength": "high",
                "reason": "Brand positions as expert - authority mechanisms align"
            })
        
        if brand_profile.get("urgency_scarcity_usage", BrandTraitScore("", 0.5, 0)).score > 0.6:
            alignments["mechanism_recommendations"].append({
                "mechanism": "scarcity",
                "strength": "high",
                "reason": "Brand uses urgency - scarcity mechanisms align with voice"
            })
        
        if brand_profile.get("emotional_vs_rational", BrandTraitScore("", 0.5, 0)).score > 0.6:
            alignments["mechanism_recommendations"].append({
                "mechanism": "storytelling",
                "strength": "high",
                "reason": "Brand leads with emotion - storytelling mechanisms align"
            })
        elif brand_profile.get("emotional_vs_rational", BrandTraitScore("", 0.5, 0)).score < 0.4:
            alignments["mechanism_recommendations"].append({
                "mechanism": "evidence",
                "strength": "high",
                "reason": "Brand leads with logic - evidence mechanisms align"
            })
        
        return alignments


# =============================================================================
# INTEGRATION WITH ADAM
# =============================================================================

def analyze_brand_traits(descriptions: List[str]) -> Dict[str, Any]:
    """
    Convenience function for ADAM integration.
    
    Args:
        descriptions: List of brand description texts
        
    Returns:
        Complete brand trait analysis with customer alignment
    """
    analyzer = BrandTraitAnalyzer()
    
    # Get brand trait profile
    profile = analyzer.analyze_brand(descriptions)
    
    # Get customer alignment
    alignment = analyzer.get_customer_alignment(profile)
    
    # Format for ADAM consumption
    result = {
        "brand_traits": {
            name: {
                "score": score.score,
                "level": score.level,
                "confidence": score.confidence,
                "signals_detected": score.signals_detected,
                "evidence": score.evidence,
            }
            for name, score in profile.items()
        },
        "customer_alignment": alignment,
        "brand_positioning_summary": _generate_positioning_summary(profile),
        "recommended_messaging_style": _get_messaging_style(profile),
    }
    
    return result


def _generate_positioning_summary(profile: Dict[str, BrandTraitScore]) -> str:
    """Generate human-readable brand positioning summary."""
    parts = []
    
    # Key positioning traits
    high_traits = [(name, score) for name, score in profile.items()
                   if score.score > 0.6 and score.confidence > 0.3]
    high_traits.sort(key=lambda x: x[1].score, reverse=True)
    
    if high_traits:
        trait_names = [t[0].replace("_", " ").title() for t in high_traits[:3]]
        parts.append(f"Strong positioning: {', '.join(trait_names)}")
    
    # Value proposition
    vp = profile.get("value_proposition_type")
    if vp and vp.confidence > 0.3:
        if vp.score > 0.6:
            parts.append("Value-focused messaging")
        elif vp.score < 0.4:
            parts.append("Premium/quality-focused messaging")
    
    return " | ".join(parts) if parts else "Balanced brand positioning"


def _get_messaging_style(profile: Dict[str, BrandTraitScore]) -> Dict[str, str]:
    """Determine recommended messaging style based on brand traits."""
    style = {
        "tone": "balanced",
        "complexity": "moderate",
        "urgency_level": "moderate",
        "trust_emphasis": "moderate",
        "emotional_rational_balance": "balanced",
    }
    
    # Tone
    auth = profile.get("authority_positioning", BrandTraitScore("", 0.5, 0))
    authenticity = profile.get("authenticity_signals", BrandTraitScore("", 0.5, 0))
    if auth.score > 0.6:
        style["tone"] = "professional_authoritative"
    elif authenticity.score > 0.6:
        style["tone"] = "friendly_authentic"
    
    # Complexity
    emotional = profile.get("emotional_vs_rational", BrandTraitScore("", 0.5, 0))
    if emotional.score < 0.4:  # Rational
        style["complexity"] = "detailed_technical"
    elif emotional.score > 0.6:  # Emotional
        style["complexity"] = "simple_evocative"
    
    # Urgency
    urgency = profile.get("urgency_scarcity_usage", BrandTraitScore("", 0.5, 0))
    if urgency.score > 0.6:
        style["urgency_level"] = "high_use_scarcity"
    elif urgency.score < 0.4:
        style["urgency_level"] = "low_avoid_pressure"
    
    # Trust emphasis
    trust = profile.get("trust_communication", BrandTraitScore("", 0.5, 0))
    risk = profile.get("risk_mitigation", BrandTraitScore("", 0.5, 0))
    if trust.score > 0.6 or risk.score > 0.6:
        style["trust_emphasis"] = "high_lead_with_guarantees"
    
    # Emotional vs rational
    if emotional.score > 0.6:
        style["emotional_rational_balance"] = "emotional_storytelling"
    elif emotional.score < 0.4:
        style["emotional_rational_balance"] = "rational_evidence"
    
    return style


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example brand descriptions
    example_descriptions = [
        """
        Patagonia is a designer of outdoor clothing and gear for the silent sports: 
        climbing, surfing, skiing and snowboarding, fly fishing, and trail running. 
        We're a certified B Corp and we give 1% of sales to environmental causes. 
        Our mission is to save our home planet. We've been making quality outdoor 
        gear since 1973, using recycled materials and fair trade certified sewing.
        """,
        """
        Apple designs, manufactures, and markets smartphones, personal computers, 
        tablets, wearables, and accessories worldwide. Our products are known for 
        their innovative technology, premium quality, and beautiful design. 
        We lead the industry in creating revolutionary products that people love.
        """,
    ]
    
    result = analyze_brand_traits(example_descriptions[:1])  # Analyze Patagonia
    
    print("=" * 60)
    print("BRAND TRAIT ANALYSIS")
    print("=" * 60)
    
    print("\nBrand Traits:")
    for name, data in result["brand_traits"].items():
        if data["signals_detected"] > 0:
            print(f"  {name}: {data['score']:.2f} ({data['level']}) - {data['signals_detected']} signals")
    
    print(f"\nPositioning Summary: {result['brand_positioning_summary']}")
    
    print("\nCustomer Alignment:")
    print(f"  Strong: {result['customer_alignment']['strong_alignment']}")
    print(f"  Moderate: {result['customer_alignment']['moderate_alignment']}")
    
    print("\nMessaging Style:")
    for key, value in result["recommended_messaging_style"].items():
        print(f"  {key}: {value}")