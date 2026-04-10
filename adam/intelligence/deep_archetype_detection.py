#!/usr/bin/env python3
"""
DEEP ARCHETYPE DETECTION SYSTEM
===============================

This is a COMPLETE REIMAGINING of archetype detection.

The previous approach was superficial keyword matching.
This approach is based on actual psychological frameworks:

1. SCHWARTZ VALUE THEORY - 10 universal values
2. REGULATORY FOCUS - Promotion vs Prevention  
3. SELF-CONSTRUAL - Independent vs Interdependent
4. COGNITIVE STYLE - Analytical vs Intuitive vs Social
5. NARRATIVE PATTERNS - How people construct stories
6. JUSTIFICATION STYLE - How people explain decisions
7. TEMPORAL ORIENTATION - Past/Present/Future focus
8. RISK ORIENTATION - Approach vs Avoidance
9. AUTHORITY ORIENTATION - Deference vs Skepticism
10. SOCIAL COMPARISON - Upward/Downward/Lateral

Each archetype is a UNIQUE CONSTELLATION across ALL dimensions.
Detection requires pattern matching across 500+ linguistic markers.

ARCHETYPES ARE NOT DEFINED BY KEYWORDS.
ARCHETYPES ARE DEFINED BY PSYCHOLOGICAL PROFILES.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import math


# =============================================================================
# DIMENSION 1: SCHWARTZ VALUE ORIENTATIONS
# =============================================================================
# 10 Universal Values with specific linguistic manifestations

SCHWARTZ_VALUES = {
    "self_direction": {
        "definition": "Independence of thought and action—choosing, creating, exploring",
        "markers": {
            # Linguistic structures, not just keywords
            "thought_patterns": [
                r"\bi decided\b",
                r"\bmy choice\b",
                r"\bi chose\b",
                r"\bi wanted\b",
                r"\bfor myself\b",
                r"\bon my own\b",
                r"\bindependent\w*\b",
                r"\bmy own way\b",
                r"\bi prefer\b",
                r"\bpersonally\b",
            ],
            "value_expressions": [
                r"\bfreedom\b",
                r"\bcreativ\w*\b",
                r"\bexplor\w*\b",
                r"\bcurious\b",
                r"\boriginal\b",
                r"\bunique\b",
                r"\bdifferent\b",
                r"\bindividual\w*\b",
            ],
            "rejection_of_conformity": [
                r"\bdon't follow\b",
                r"\bnot like everyone\b",
                r"\bmy own\b",
                r"\bdifferent from\b",
                r"\bstand out\b",
            ],
        },
        "opposite": "conformity",
    },
    
    "stimulation": {
        "definition": "Excitement, novelty, and challenge in life",
        "markers": {
            "excitement_seeking": [
                r"\bexcit\w*\b",
                r"\bthrilling\b",
                r"\badventur\w*\b",
                r"\bchalleng\w*\b",
                r"\bdaring\b",
                r"\bbold\b",
                r"\brisk\w*\b",
            ],
            "novelty_seeking": [
                r"\bnew\b",
                r"\bfirst time\b",
                r"\bnever tried\b",
                r"\bdiscovered\b",
                r"\bexperiment\w*\b",
                r"\btry\w* something\b",
            ],
            "variety_seeking": [
                r"\bvariety\b",
                r"\bdifferent\b",
                r"\bchange\w*\b",
                r"\bswitch\w*\b",
                r"\balternative\b",
            ],
            "boredom_avoidance": [
                r"\bbored\b",
                r"\bboring\b",
                r"\bsame old\b",
                r"\broutine\b",
                r"\brepetitive\b",
            ],
        },
        "opposite": "security",
    },
    
    "hedonism": {
        "definition": "Pleasure and sensuous gratification for oneself",
        "markers": {
            "pleasure_orientation": [
                r"\bpleasur\w*\b",
                r"\benjoy\w*\b",
                r"\bdelight\w*\b",
                r"\bfun\b",
                r"\bgratif\w*\b",
                r"\bsatisf\w*\b",
                r"\bhappy\b",
                r"\bhappiness\b",
            ],
            "sensory_focus": [
                r"\bfeels? (good|great|amazing)\b",
                r"\btaste[sd]?\b",
                r"\bsmell[sd]?\b",
                r"\bbeautiful\b",
                r"\bgorgeous\b",
                r"\bluxur\w*\b",
                r"\bindulg\w*\b",
                r"\btreat (myself|yourself)\b",
            ],
            "comfort_seeking": [
                r"\bcomfort\w*\b",
                r"\brelax\w*\b",
                r"\bpamper\w*\b",
                r"\bspoil\w*\b",
                r"\bdeserve\b",
            ],
            "self_reward": [
                r"\breward (myself|yourself)\b",
                r"\btreat\b",
                r"\bgift to (myself|yourself)\b",
                r"\bi deserve\b",
            ],
        },
        "opposite": None,
    },
    
    "achievement": {
        "definition": "Personal success through demonstrating competence",
        "markers": {
            "success_orientation": [
                r"\bsuccess\w*\b",
                r"\bachiev\w*\b",
                r"\baccomplish\w*\b",
                r"\bwin\w*\b",
                r"\bbeat\b",
                r"\bexcel\w*\b",
                r"\boutperform\w*\b",
            ],
            "competence_demonstration": [
                r"\bbest\b",
                r"\btop\b",
                r"\bfirst\b",
                r"\bleading\b",
                r"\bsuperior\b",
                r"\bhigh.?end\b",
                r"\bpremium\b",
                r"\bprofessional\b",
            ],
            "ambition_language": [
                r"\bgoal\w*\b",
                r"\bambiti\w*\b",
                r"\bdriven\b",
                r"\bdetermin\w*\b",
                r"\bstriv\w*\b",
                r"\bpush\w*\b",
            ],
            "comparison_upward": [
                r"\bbetter than\b",
                r"\bmore than\b",
                r"\bsurpass\w*\b",
                r"\bexceed\w*\b",
                r"\bnext level\b",
                r"\bupgrad\w*\b",
            ],
            "recognition_seeking": [
                r"\brecogniz\w*\b",
                r"\brespect\w*\b",
                r"\badmir\w*\b",
                r"\bimpressive\b",
                r"\bprestig\w*\b",
            ],
        },
        "opposite": None,
    },
    
    "power": {
        "definition": "Social status and prestige, control or dominance",
        "markers": {
            "status_orientation": [
                r"\bstatus\b",
                r"\bprestig\w*\b",
                r"\bexclusive\b",
                r"\belite\b",
                r"\bhigh.?end\b",
                r"\bluxur\w*\b",
                r"\bpremium\b",
            ],
            "control_language": [
                r"\bcontrol\w*\b",
                r"\bpower\w*\b",
                r"\bdomina\w*\b",
                r"\binfluenc\w*\b",
                r"\bauthority\b",
                r"\bin charge\b",
            ],
            "wealth_display": [
                r"\bwealth\w*\b",
                r"\bexpensive\b",
                r"\bcost\w* \$?\d+\b",
                r"\binvest\w*\b",
                r"\bworth\b",
                r"\bprice\w* (tag|point)\b",
            ],
            "superiority_claims": [
                r"\babove\b",
                r"\bsuperior\b",
                r"\bbetter than (most|others)\b",
                r"\bnot (for )?everyone\b",
                r"\bdiscerning\b",
            ],
        },
        "opposite": "universalism",
    },
    
    "security": {
        "definition": "Safety, harmony, and stability of society, relationships, and self",
        "markers": {
            "safety_orientation": [
                r"\bsafe\w*\b",
                r"\bsecur\w*\b",
                r"\bprotect\w*\b",
                r"\bguard\w*\b",
                r"\bdefend\w*\b",
                r"\bshield\w*\b",
            ],
            "stability_seeking": [
                r"\bstable\b",
                r"\bstability\b",
                r"\breliab\w*\b",
                r"\bdependab\w*\b",
                r"\bconsistent\w*\b",
                r"\bpredictab\w*\b",
            ],
            "risk_avoidance": [
                r"\bavoid\w*\b",
                r"\bprevent\w*\b",
                r"\bworr(y|ied)\b",
                r"\bconcern\w*\b",
                r"\bcareful\w*\b",
                r"\bcautious\b",
            ],
            "guarantee_seeking": [
                r"\bguarantee\w*\b",
                r"\bwarrant\w*\b",
                r"\binsur\w*\b",
                r"\breturn policy\b",
                r"\bmoney.?back\b",
                r"\brisk.?free\b",
            ],
            "trust_building": [
                r"\btrust\w*\b",
                r"\breput\w*\b",
                r"\bestablish\w*\b",
                r"\bprov(en|ing)\b",
                r"\btrack record\b",
            ],
        },
        "opposite": "stimulation",
    },
    
    "conformity": {
        "definition": "Restraint of actions likely to upset or harm others or violate norms",
        "markers": {
            "norm_adherence": [
                r"\bnormal\b",
                r"\bstandard\b",
                r"\btypical\b",
                r"\btraditional\b",
                r"\bconventional\b",
                r"\busual\b",
            ],
            "social_acceptance": [
                r"\baccepted\b",
                r"\bappropriate\b",
                r"\bproper\b",
                r"\bpolite\b",
                r"\brespectful\b",
            ],
            "others_orientation": [
                r"\bwhat (others|people) think\b",
                r"\beveryone (says|does|has)\b",
                r"\bsupposed to\b",
                r"\bshould\b",
                r"\bexpected\b",
            ],
            "rule_following": [
                r"\brules?\b",
                r"\bfollow\w*\b",
                r"\bobey\w*\b",
                r"\bcomply\w*\b",
                r"\bas (directed|instructed)\b",
            ],
        },
        "opposite": "self_direction",
    },
    
    "tradition": {
        "definition": "Respect, commitment, and acceptance of customs and ideas",
        "markers": {
            "tradition_references": [
                r"\btradition\w*\b",
                r"\bclassic\b",
                r"\btimeless\b",
                r"\bheritage\b",
                r"\blegacy\b",
                r"\bhistor\w*\b",
            ],
            "past_orientation": [
                r"\balways (been|had|used)\b",
                r"\bfor (years|generations|decades)\b",
                r"\bmy (parents|grandparents|family)\b",
                r"\bgrew up with\b",
                r"\bremember when\b",
            ],
            "custom_adherence": [
                r"\bcustom\w*\b",
                r"\britual\w*\b",
                r"\bceremony\b",
                r"\bcelebrat\w*\b",
            ],
            "respect_for_elders": [
                r"\brespect\w*\b",
                r"\bhonor\w*\b",
                r"\bwise\b",
                r"\bexperienc\w*\b",
            ],
        },
        "opposite": None,
    },
    
    "benevolence": {
        "definition": "Preserving and enhancing welfare of close others",
        "markers": {
            "care_for_close_others": [
                r"\bfamily\b",
                r"\bfriend\w*\b",
                r"\bloved ones?\b",
                r"\bchildren\b",
                r"\bkids?\b",
                r"\bspouse\b",
                r"\bpartner\b",
                r"\bparents?\b",
            ],
            "helping_orientation": [
                r"\bhelp\w*\b",
                r"\bsupport\w*\b",
                r"\bcare (for|about)\b",
                r"\btake care\b",
                r"\blook after\b",
            ],
            "gift_giving": [
                r"\bgift\w*\b",
                r"\bbought (for|as)\b",
                r"\bgave\b",
                r"\bshare\w*\b",
                r"\bfor (my|the) (wife|husband|son|daughter|mom|dad|friend)\b",
            ],
            "loyalty_expressions": [
                r"\bloyal\w*\b",
                r"\bfaithful\b",
                r"\bdevot\w*\b",
                r"\bcommit\w*\b",
            ],
            "empathy_expressions": [
                r"\bunderstand\w*\b",
                r"\bempathy\b",
                r"\bcompassion\w*\b",
                r"\bsympathy\b",
            ],
        },
        "opposite": None,
    },
    
    "universalism": {
        "definition": "Understanding, tolerance, protection for all people and nature",
        "markers": {
            "broad_concern": [
                r"\beveryone\b",
                r"\ball people\b",
                r"\bsociety\b",
                r"\bcommunity\b",
                r"\bworld\b",
                r"\bglobal\b",
            ],
            "justice_orientation": [
                r"\bfair\w*\b",
                r"\bjust(ice)?\b",
                r"\bequal\w*\b",
                r"\bright[s]?\b",
            ],
            "environmental_concern": [
                r"\benviron\w*\b",
                r"\bsustain\w*\b",
                r"\beco\w*\b",
                r"\bgreen\b",
                r"\bplanet\b",
                r"\bnature\b",
                r"\borganic\b",
            ],
            "tolerance_expressions": [
                r"\btoleran\w*\b",
                r"\baccept\w*\b",
                r"\bopen.?mind\w*\b",
                r"\bdivers\w*\b",
                r"\binclus\w*\b",
            ],
        },
        "opposite": "power",
    },
}


# =============================================================================
# DIMENSION 2: COGNITIVE STYLE PATTERNS
# =============================================================================

COGNITIVE_STYLES = {
    "analytical": {
        "definition": "Systematic, logical, data-driven reasoning",
        "markers": {
            "logical_connectors": [
                r"\btherefore\b",
                r"\bthus\b",
                r"\bhence\b",
                r"\bconsequently\b",
                r"\bas a result\b",
                r"\bbecause\b",
                r"\bsince\b",
                r"\bdue to\b",
            ],
            "comparison_structures": [
                r"\bcompared to\b",
                r"\bversus\b",
                r"\bvs\.?\b",
                r"\brather than\b",
                r"\bas opposed to\b",
                r"\bunlike\b",
                r"\bin contrast\b",
            ],
            "quantitative_language": [
                r"\b\d+%\b",
                r"\b\d+ (times|x)\b",
                r"\b\d+/\d+\b",
                r"\bratio\b",
                r"\bpercentage\b",
                r"\bmeasur\w*\b",
                r"\bstat\w*\b",
            ],
            "evidence_language": [
                r"\bevidence\b",
                r"\bproof\b",
                r"\bdata\b",
                r"\bresearch\b",
                r"\bstudy\b",
                r"\btest\w*\b",
                r"\bverif\w*\b",
            ],
            "evaluation_structures": [
                r"\bpros? and cons?\b",
                r"\badvantages? and disadvantages?\b",
                r"\bstrengths? and weaknesses?\b",
                r"\bon one hand.+on the other\b",
            ],
            "precision_language": [
                r"\bexactly\b",
                r"\bprecisely\b",
                r"\bspecifically\b",
                r"\bin particular\b",
                r"\b\d+ (inch|cm|mm|oz|lb|kg|ml|g)\w*\b",
            ],
        },
    },
    
    "intuitive": {
        "definition": "Gut-feeling, impression-based, holistic",
        "markers": {
            "feeling_language": [
                r"\bfeel\w*\b",
                r"\bsense\w*\b",
                r"\bintuition\b",
                r"\bgut\b",
                r"\binstinct\w*\b",
                r"\bvibe\w*\b",
            ],
            "impression_language": [
                r"\bseems?\b",
                r"\bappears?\b",
                r"\blooks? like\b",
                r"\bkind of\b",
                r"\bsort of\b",
                r"\bi (just )?know\b",
            ],
            "holistic_evaluations": [
                r"\boverall\b",
                r"\bin general\b",
                r"\bas a whole\b",
                r"\bbig picture\b",
                r"\bessence\b",
            ],
            "emotional_processing": [
                r"\blove\b",
                r"\bhate\b",
                r"\bfell in love\b",
                r"\bhad to have\b",
                r"\bcouldn't resist\b",
            ],
            "speed_language": [
                r"\bimmediately\b",
                r"\binstantly\b",
                r"\bright away\b",
                r"\bat first (sight|glance)\b",
            ],
        },
    },
    
    "social": {
        "definition": "Others-oriented, consensus-seeking, relationship-based",
        "markers": {
            "social_proof_seeking": [
                r"\beveryone (says|loves|recommends)\b",
                r"\b(all|most) (reviews|people)\b",
                r"\bpopular\b",
                r"\btrending\b",
                r"\bbest sell\w*\b",
                r"\bhighly rated\b",
            ],
            "recommendation_orientation": [
                r"\brecommend\w*\b",
                r"\bsuggest\w*\b",
                r"\badvised?\b",
                r"\btold me\b",
                r"\bheard (from|about)\b",
            ],
            "relationship_context": [
                r"\bmy (friend|colleague|neighbor|coworker)\b",
                r"\bsomeone I (know|trust)\b",
                r"\bword of mouth\b",
            ],
            "consensus_language": [
                r"\bagreed?\b",
                r"\bconsensus\b",
                r"\bmajority\b",
                r"\bmost people\b",
                r"\bcommon\w*\b",
            ],
            "endorsement_references": [
                r"\bendorse\w*\b",
                r"\bapproved\b",
                r"\bcertified\b",
                r"\bverified\b",
            ],
        },
    },
    
    "experiential": {
        "definition": "Direct experience-based, trial-oriented",
        "markers": {
            "personal_experience": [
                r"\bi (have )?(tried|used|tested|owned)\b",
                r"\bin my experience\b",
                r"\bfirsthand\b",
                r"\bpersonally\b",
                r"\bfor myself\b",
            ],
            "trial_language": [
                r"\btried\b",
                r"\btested\b",
                r"\bexperimented\b",
                r"\bgave it a (try|shot|chance)\b",
            ],
            "duration_markers": [
                r"\bfor \d+ (days?|weeks?|months?|years?)\b",
                r"\bafter (using|trying|owning)\b",
                r"\bover time\b",
                r"\blong.?term\b",
            ],
            "sensory_details": [
                r"\bfelt\b",
                r"\bsmelled\b",
                r"\btasted\b",
                r"\blooked\b",
                r"\bsounded\b",
                r"\btexture\b",
            ],
        },
    },
}


# =============================================================================
# DIMENSION 3: SELF-CONSTRUAL
# =============================================================================

SELF_CONSTRUAL = {
    "independent": {
        "definition": "Self as separate, autonomous, unique individual",
        "markers": {
            "i_focus": [
                r"\bi\b",
                r"\bme\b",
                r"\bmy\b",
                r"\bmine\b",
                r"\bmyself\b",
            ],
            "uniqueness_emphasis": [
                r"\bunique\b",
                r"\bdifferent\b",
                r"\bspecial\b",
                r"\bindividual\b",
                r"\bpersonal\b",
                r"\bmy own\b",
            ],
            "autonomy_language": [
                r"\bi decided\b",
                r"\bmy choice\b",
                r"\bfor myself\b",
                r"\bon my own\b",
                r"\bindependent\w*\b",
            ],
            "self_expression": [
                r"\bexpress (myself|my)\b",
                r"\bmy (style|taste|preference)\b",
                r"\breflects? (me|who I am)\b",
            ],
            "achievement_self": [
                r"\bi (achieved|accomplished|succeeded)\b",
                r"\bmy (success|achievement|accomplishment)\b",
            ],
        },
    },
    
    "interdependent": {
        "definition": "Self as connected to, part of larger social units",
        "markers": {
            "we_focus": [
                r"\bwe\b",
                r"\bus\b",
                r"\bour\b",
                r"\bours\b",
                r"\bourselves\b",
            ],
            "group_identity": [
                r"\b(my|our) (family|team|group|community)\b",
                r"\bwe all\b",
                r"\btogether\b",
                r"\bshared\b",
            ],
            "relationship_orientation": [
                r"\bfor (my|the) (family|kids|spouse|partner)\b",
                r"\bwith (my|the) (family|friends)\b",
                r"\bour (home|family|group)\b",
            ],
            "social_harmony": [
                r"\beveryone (happy|satisfied|pleased)\b",
                r"\bfits? (in|with)\b",
                r"\bbelongs?\b",
                r"\bpart of\b",
            ],
            "role_emphasis": [
                r"\bas a (parent|mother|father|spouse|member)\b",
                r"\bmy role\b",
                r"\bresponsib\w* (to|for)\b",
            ],
        },
    },
}


# =============================================================================
# DIMENSION 4: NARRATIVE PATTERNS
# =============================================================================

NARRATIVE_PATTERNS = {
    "hero_journey": {
        "description": "Overcoming challenges, transformation narrative",
        "markers": {
            "challenge_setup": [
                r"\bproblem\b",
                r"\bchallenge\b",
                r"\bstruggl\w*\b",
                r"\bdifficult\w*\b",
                r"\bhard time\b",
            ],
            "quest_language": [
                r"\bsearch\w*\b",
                r"\blook\w* for\b",
                r"\btried (many|several|different)\b",
                r"\bfinally found\b",
            ],
            "transformation": [
                r"\bchanged\b",
                r"\btransform\w*\b",
                r"\bgame.?changer\b",
                r"\bbefore and after\b",
                r"\bnow I\b",
            ],
            "triumph": [
                r"\bsolv\w*\b",
                r"\bfix\w*\b",
                r"\bwork\w* (great|perfect)\b",
                r"\bproblem solved\b",
            ],
        },
    },
    
    "discovery": {
        "description": "Finding something new, exploration narrative",
        "markers": {
            "discovery_language": [
                r"\bdiscover\w*\b",
                r"\bfound\b",
                r"\bstumbl\w* (upon|across)\b",
                r"\bcame across\b",
            ],
            "surprise_elements": [
                r"\bsurpris\w*\b",
                r"\bunexpect\w*\b",
                r"\bdidn't (know|expect|realize)\b",
                r"\bwho knew\b",
            ],
            "revelation": [
                r"\brealize\w*\b",
                r"\bturns? out\b",
                r"\blittle did I know\b",
                r"\bhidden gem\b",
            ],
        },
    },
    
    "cautionary": {
        "description": "Warning, negative experience narrative",
        "markers": {
            "warning_language": [
                r"\bwarning\b",
                r"\bbeware\b",
                r"\bcareful\b",
                r"\bwatch out\b",
                r"\bdon't (buy|get|make)\b",
            ],
            "regret_expression": [
                r"\bregret\w*\b",
                r"\bwish I (hadn't|didn't)\b",
                r"\bshould have\b",
                r"\bif only\b",
            ],
            "lesson_learned": [
                r"\blearn\w* (my|the) lesson\b",
                r"\bnever again\b",
                r"\bnext time\b",
                r"\bwon't make that mistake\b",
            ],
        },
    },
    
    "validation": {
        "description": "Confirming expectations, reassurance narrative",
        "markers": {
            "expectation_confirmation": [
                r"\bas expected\b",
                r"\bjust (like|as) (described|advertised|pictured)\b",
                r"\bexactly what\b",
                r"\bmet (my )?expectations\b",
            ],
            "reassurance": [
                r"\bdon't worry\b",
                r"\byou (won't|can't) go wrong\b",
                r"\bsafe bet\b",
                r"\breliable\b",
            ],
            "confirmation_language": [
                r"\bconfirm\w*\b",
                r"\bverif\w*\b",
                r"\bproves?\b",
                r"\bvalidat\w*\b",
            ],
        },
    },
    
    "advocacy": {
        "description": "Passionate recommendation, evangelist narrative",
        "markers": {
            "strong_recommendation": [
                r"\bhighly recommend\b",
                r"\bmust (have|buy|get|try)\b",
                r"\bdo yourself a favor\b",
                r"\byou (need|want) this\b",
            ],
            "enthusiasm": [
                r"\bamazing\b",
                r"\bincredible\b",
                r"\bfantastic\b",
                r"\bunbelievable\b",
                r"\bmind.?blow\w*\b",
            ],
            "evangelism": [
                r"\btell everyone\b",
                r"\bspread the word\b",
                r"\bconvert\w*\b",
                r"\bconvinc\w*\b",
            ],
        },
    },
}


# =============================================================================
# DIMENSION 5: JUSTIFICATION PATTERNS
# =============================================================================

JUSTIFICATION_PATTERNS = {
    "rational": {
        "description": "Logical, feature-based justifications",
        "markers": {
            "feature_focus": [
                r"\bfeature\w*\b",
                r"\bspec\w*\b",
                r"\bcapabilit\w*\b",
                r"\bfunction\w*\b",
                r"\bperformance\b",
            ],
            "comparison_basis": [
                r"\bcompared to\b",
                r"\bbetter than\b",
                r"\bunlike (other|the)\b",
                r"\bvs\.?\b",
            ],
            "logical_structure": [
                r"\bbecause\b",
                r"\bsince\b",
                r"\btherefore\b",
                r"\bthe reason\b",
            ],
            "value_calculation": [
                r"\bworth\b",
                r"\bvalue\b",
                r"\bcost.?benefit\b",
                r"\bprice.?(to|per|for)\b",
            ],
        },
    },
    
    "emotional": {
        "description": "Feeling-based, affective justifications",
        "markers": {
            "feeling_basis": [
                r"\bi (felt|feel)\b",
                r"\bmade me (feel|happy)\b",
                r"\blove\b",
                r"\bhate\b",
            ],
            "desire_language": [
                r"\bwanted\b",
                r"\bneeded\b",
                r"\bhad to have\b",
                r"\bcouldn't resist\b",
            ],
            "emotional_connection": [
                r"\bconnect\w*\b",
                r"\bresonat\w*\b",
                r"\bspeak\w* to me\b",
                r"\bmean\w* (a lot|so much)\b",
            ],
        },
    },
    
    "social": {
        "description": "Others-oriented, relationship-based justifications",
        "markers": {
            "social_validation": [
                r"\beveryone (loves|has|uses|recommends)\b",
                r"\bpopular\b",
                r"\btrending\b",
            ],
            "recommendation_basis": [
                r"\brecommended by\b",
                r"\badvised to\b",
                r"\bmy (friend|colleague|family) (said|suggested|recommended)\b",
            ],
            "belonging": [
                r"\bfit in\b",
                r"\blike (everyone|others)\b",
                r"\bpart of\b",
            ],
        },
    },
    
    "authority": {
        "description": "Expert/authority-based justifications",
        "markers": {
            "expert_reference": [
                r"\bexpert\w*\b",
                r"\bprofessional\w*\b",
                r"\bspecialist\w*\b",
                r"\b(doctor|dermatologist|mechanic|chef) recommend\w*\b",
            ],
            "credential_emphasis": [
                r"\baward.?win\w*\b",
                r"\bcertified\b",
                r"\bapproved\b",
                r"\brated\b",
            ],
            "trust_in_brand": [
                r"\btrusted brand\b",
                r"\breputation\b",
                r"\bknown for\b",
                r"\bbrand name\b",
            ],
        },
    },
    
    "experiential": {
        "description": "Personal experience-based justifications",
        "markers": {
            "personal_test": [
                r"\bi (tested|tried|used)\b",
                r"\bin my experience\b",
                r"\bfrom (my|personal) experience\b",
            ],
            "outcome_evidence": [
                r"\bworked for me\b",
                r"\bi saw results\b",
                r"\bactually (works|worked)\b",
            ],
            "time_investment": [
                r"\bafter \d+ (days|weeks|months)\b",
                r"\bover time\b",
                r"\blong.?term\b",
            ],
        },
    },
}


# =============================================================================
# DIMENSION 6: TEMPORAL ORIENTATION
# =============================================================================

TEMPORAL_ORIENTATION = {
    "past_focus": {
        "description": "Emphasis on history, memory, tradition",
        "markers": {
            "past_references": [
                r"\bused to\b",
                r"\bback when\b",
                r"\bin the past\b",
                r"\bpreviously\b",
                r"\bformerly\b",
            ],
            "memory_language": [
                r"\bremember\w*\b",
                r"\bnostalgic\b",
                r"\bmemor\w*\b",
                r"\brecall\b",
            ],
            "past_comparison": [
                r"\bcompared to (before|the old|my previous)\b",
                r"\bbetter than (my old|the last|previous)\b",
                r"\bunlike (before|the old)\b",
            ],
        },
    },
    
    "present_focus": {
        "description": "Emphasis on current state, immediate experience",
        "markers": {
            "present_markers": [
                r"\bright now\b",
                r"\bcurrently\b",
                r"\bat the moment\b",
                r"\btoday\b",
                r"\bthese days\b",
            ],
            "immediate_experience": [
                r"\bam (using|enjoying|loving)\b",
                r"\bworks great\b",
                r"\bis (perfect|amazing|great)\b",
            ],
            "present_needs": [
                r"\bneed\w* (it )?(now|immediately)\b",
                r"\bcan't wait\b",
                r"\binstant\b",
            ],
        },
    },
    
    "future_focus": {
        "description": "Emphasis on planning, anticipation, goals",
        "markers": {
            "future_references": [
                r"\bwill\b",
                r"\bgoing to\b",
                r"\bplan to\b",
                r"\bintend to\b",
                r"\bhope to\b",
            ],
            "anticipation": [
                r"\blooking forward\b",
                r"\bcan't wait\b",
                r"\bexcited (to|about|for)\b",
                r"\banticipat\w*\b",
            ],
            "investment_language": [
                r"\binvest\w*\b",
                r"\blong.?term\b",
                r"\bfuture\b",
                r"\bdown the road\b",
            ],
            "goal_language": [
                r"\bgoal\w*\b",
                r"\bplan\w*\b",
                r"\baim\w*\b",
                r"\btarget\w*\b",
            ],
        },
    },
}


# =============================================================================
# DIMENSION 7: RISK ORIENTATION
# =============================================================================

RISK_ORIENTATION = {
    "risk_seeking": {
        "description": "Comfort with uncertainty, adventure-seeking",
        "markers": {
            "risk_language": [
                r"\brisk\w*\b",
                r"\bgamble\b",
                r"\bchance\b",
                r"\bbold\b",
                r"\bdaring\b",
            ],
            "uncertainty_tolerance": [
                r"\bwhy not\b",
                r"\bgave it a (try|shot|chance)\b",
                r"\bnothing to lose\b",
                r"\bworst that could happen\b",
            ],
            "exploration_language": [
                r"\bexperiment\w*\b",
                r"\btried something new\b",
                r"\bfirst time\b",
                r"\bnever tried\b",
            ],
        },
    },
    
    "risk_averse": {
        "description": "Preference for certainty, safety-seeking",
        "markers": {
            "safety_seeking": [
                r"\bsafe\b",
                r"\bsecure\b",
                r"\bprotect\w*\b",
                r"\bguarantee\w*\b",
            ],
            "uncertainty_avoidance": [
                r"\bworr(y|ied)\b",
                r"\bconcern\w*\b",
                r"\bafraid\b",
                r"\bhesitat\w*\b",
                r"\bskeptical\b",
            ],
            "research_behavior": [
                r"\bresearch\w*\b",
                r"\bread (all the )?reviews\b",
                r"\bcompared\b",
                r"\bcareful\w* (consider|research|review)\b",
            ],
            "safety_nets": [
                r"\breturn policy\b",
                r"\bwarranty\b",
                r"\bmoney.?back\b",
                r"\brisk.?free\b",
            ],
        },
    },
}


# =============================================================================
# DEEP ARCHETYPE DEFINITIONS
# =============================================================================
# Each archetype is a UNIQUE CONSTELLATION across ALL dimensions

DEEP_ARCHETYPES = {
    "achiever": {
        "description": "Success-driven, status-conscious, quality-focused",
        
        # Schwartz Values Profile (which values dominate)
        "value_profile": {
            "high": ["achievement", "power", "self_direction"],
            "medium": ["hedonism", "stimulation"],
            "low": ["conformity", "tradition", "benevolence"],
        },
        
        # Cognitive Style
        "cognitive_style": {
            "primary": "analytical",
            "secondary": "experiential",
        },
        
        # Self-Construal
        "self_construal": "independent",
        
        # Regulatory Focus
        "regulatory_focus": "promotion",
        
        # Narrative Patterns
        "narrative_patterns": ["hero_journey", "advocacy"],
        
        # Justification Style
        "justification_style": {
            "primary": "rational",
            "secondary": "authority",
        },
        
        # Temporal Orientation
        "temporal_orientation": "future_focus",
        
        # Risk Orientation
        "risk_orientation": "moderate_risk_seeking",
        
        # Linguistic Signatures (specific to this archetype)
        "linguistic_signatures": {
            "sentence_patterns": [
                r"\bthe best\b.+\bi've\b",
                r"\binvest\w* in\b.+\bquality\b",
                r"\bworth (every|the)\b.+\b(dollar|penny|cent)\b",
                r"\bpremium\b.+\bexpect\b",
                r"\bstandards?\b.+\bhigh\b",
            ],
            "comparative_patterns": [
                r"\bbetter than\b.+\b(competitor|alternative|other)\b",
                r"\bsuperior\b.+\bto\b",
                r"\boutperform\w*\b",
                r"\bnext level\b",
            ],
            "self_reference_patterns": [
                r"\bi (demand|expect|require)\b",
                r"\bmy standards\b",
                r"\bi don't settle\b",
                r"\bas (a professional|someone who)\b",
            ],
            "quality_patterns": [
                r"\bquality\b.+\b(matter|important|first)\b",
                r"\bpay (more )?for\b.+\bquality\b",
                r"\bcraftsmanship\b",
                r"\battention to detail\b",
                r"\bbuilt to last\b",
            ],
            "status_patterns": [
                r"\bprestigious\b",
                r"\bexclusive\b",
                r"\bluxury\b",
                r"\bhigh.?end\b",
                r"\bdiscerning\b",
            ],
        },
    },
    
    "explorer": {
        "description": "Novelty-seeking, experience-driven, adventure-focused",
        
        "value_profile": {
            "high": ["stimulation", "self_direction", "hedonism"],
            "medium": ["universalism", "achievement"],
            "low": ["security", "conformity", "tradition"],
        },
        
        "cognitive_style": {
            "primary": "experiential",
            "secondary": "intuitive",
        },
        
        "self_construal": "independent",
        
        "regulatory_focus": "promotion",
        
        "narrative_patterns": ["discovery", "hero_journey"],
        
        "justification_style": {
            "primary": "experiential",
            "secondary": "emotional",
        },
        
        "temporal_orientation": "present_focus",
        
        "risk_orientation": "risk_seeking",
        
        "linguistic_signatures": {
            "discovery_patterns": [
                r"\bdiscover\w*\b.+\b(new|hidden|amazing)\b",
                r"\bfound\b.+\b(gem|treasure|perfect)\b",
                r"\bstumbl\w*\b.+\b(upon|across)\b",
                r"\bfirst time\b.+\btry\w*\b",
            ],
            "experience_patterns": [
                r"\bexperience\b.+\b(new|different|unique)\b",
                r"\badventure\b",
                r"\bexplor\w*\b",
                r"\bcurious\b.+\btry\b",
            ],
            "novelty_patterns": [
                r"\bnew\b.+\bexcit\w*\b",
                r"\bdifferent from\b.+\b(anything|everything)\b",
                r"\bunique\b",
                r"\binnovative\b",
                r"\bfresh\b.+\b(approach|take|perspective)\b",
            ],
            "spontaneity_patterns": [
                r"\bimpuls\w*\b",
                r"\bspur of the moment\b",
                r"\bjust\b.+\b(decided|went for it)\b",
                r"\bwhy not\b",
            ],
            "sensation_patterns": [
                r"\bthrill\w*\b",
                r"\bexcit\w*\b",
                r"\badrenaline\b",
                r"\brush\b",
            ],
        },
    },
    
    "connector": {
        "description": "Relationship-focused, community-oriented, sharing-driven",
        
        "value_profile": {
            "high": ["benevolence", "conformity", "tradition"],
            "medium": ["universalism", "security"],
            "low": ["power", "achievement", "self_direction"],
        },
        
        "cognitive_style": {
            "primary": "social",
            "secondary": "intuitive",
        },
        
        "self_construal": "interdependent",
        
        "regulatory_focus": "mixed",
        
        "narrative_patterns": ["advocacy", "validation"],
        
        "justification_style": {
            "primary": "social",
            "secondary": "emotional",
        },
        
        "temporal_orientation": "present_focus",
        
        "risk_orientation": "moderate_risk_averse",
        
        "linguistic_signatures": {
            "relationship_patterns": [
                r"\b(my|for) (family|friends|loved ones)\b",
                r"\btogether\b",
                r"\bshare\w*\b.+\bwith\b",
                r"\beveryone\b.+\b(loves|enjoys|happy)\b",
            ],
            "gift_patterns": [
                r"\b(bought|got) (this )?(for|as a gift)\b",
                r"\bgift\w*\b.+\b(perfect|great|loved)\b",
                r"\bmade\b.+\b(happy|smile|day)\b",
            ],
            "recommendation_patterns": [
                r"\brecommend\b.+\b(to|for) (everyone|anyone|all)\b",
                r"\btell\b.+\b(everyone|friends|family)\b",
                r"\bspread the word\b",
            ],
            "social_proof_patterns": [
                r"\beveryone (says|loves|has)\b",
                r"\b(friends|family) (all|also) (have|love|use)\b",
                r"\bpopular\b.+\b(among|with)\b",
            ],
            "caring_patterns": [
                r"\bcare\b.+\b(about|for)\b",
                r"\bhelp\w*\b",
                r"\bsupport\w*\b",
                r"\bthoughtful\b",
            ],
        },
    },
    
    "guardian": {
        "description": "Security-focused, protection-driven, reliability-seeking",
        
        "value_profile": {
            "high": ["security", "conformity", "tradition"],
            "medium": ["benevolence", "universalism"],
            "low": ["stimulation", "hedonism", "power"],
        },
        
        "cognitive_style": {
            "primary": "analytical",
            "secondary": "social",
        },
        
        "self_construal": "interdependent",
        
        "regulatory_focus": "prevention",
        
        "narrative_patterns": ["validation", "cautionary"],
        
        "justification_style": {
            "primary": "authority",
            "secondary": "rational",
        },
        
        "temporal_orientation": "past_focus",
        
        "risk_orientation": "risk_averse",
        
        "linguistic_signatures": {
            "safety_patterns": [
                r"\bsafe\w*\b.+\b(for|to use|family)\b",
                r"\bprotect\w*\b",
                r"\bsecure\w*\b",
                r"\bno (worries|concerns|issues)\b",
            ],
            "reliability_patterns": [
                r"\breliab\w*\b",
                r"\bdependab\w*\b",
                r"\bconsistent\w*\b",
                r"\balways works\b",
                r"\bnever (fails|fails|disappointed)\b",
            ],
            "trust_patterns": [
                r"\btrust\w*\b.+\b(brand|company|product)\b",
                r"\breputation\b",
                r"\bestablished\b",
                r"\bproven\b",
                r"\btrack record\b",
            ],
            "warranty_patterns": [
                r"\bwarrant\w*\b",
                r"\bguarantee\w*\b",
                r"\breturn policy\b",
                r"\bcustomer (service|support)\b",
            ],
            "caution_patterns": [
                r"\bcareful\w* (research|consider|review)\b",
                r"\bread (all )?the reviews\b",
                r"\bafter much (research|consideration)\b",
                r"\bdidn't rush\b",
            ],
            "protection_patterns": [
                r"\bprotect\w*\b.+\b(family|children|home)\b",
                r"\bkeep\w*\b.+\bsafe\b",
                r"\bpeace of mind\b",
            ],
        },
    },
    
    "pragmatist": {
        "description": "Value-focused, efficiency-driven, practical-minded",
        
        "value_profile": {
            "high": ["security", "conformity"],
            "medium": ["self_direction", "achievement"],
            "low": ["power", "hedonism", "stimulation"],
        },
        
        "cognitive_style": {
            "primary": "analytical",
            "secondary": "experiential",
        },
        
        "self_construal": "independent",
        
        "regulatory_focus": "prevention",
        
        "narrative_patterns": ["validation"],
        
        "justification_style": {
            "primary": "rational",
            "secondary": "experiential",
        },
        
        "temporal_orientation": "present_focus",
        
        "risk_orientation": "moderate_risk_averse",
        
        "linguistic_signatures": {
            "value_patterns": [
                r"\bvalue\b.+\b(for|money|price)\b",
                r"\bworth\b.+\b(the|every)\b.+\b(money|dollar|penny)\b",
                r"\bgreat\b.+\b(price|deal|value)\b",
                r"\baffordab\w*\b",
                r"\bbudget\b.+\b(friendly|conscious)\b",
            ],
            "efficiency_patterns": [
                r"\befficient\w*\b",
                r"\bpractical\w*\b",
                r"\bfunctional\w*\b",
                r"\bdoes the job\b",
                r"\bworks (well|great|fine)\b",
            ],
            "comparison_patterns": [
                r"\bcompared to\b.+\b(more expensive|pricier)\b",
                r"\bcheaper than\b",
                r"\bbetter (value|deal|price)\b",
                r"\bwhy pay more\b",
            ],
            "no_frills_patterns": [
                r"\bno.?frills\b",
                r"\bbasic but\b",
                r"\bsimple\b.+\b(works|effective)\b",
                r"\bdon't need\b.+\b(fancy|expensive)\b",
            ],
            "smart_shopping_patterns": [
                r"\bsmart (buy|purchase|choice)\b",
                r"\bresearch\w*\b.+\bbefore\b",
                r"\bcompare\w* (prices|options)\b",
                r"\bwaited for\b.+\b(sale|deal|discount)\b",
            ],
        },
    },
    
    "analyst": {
        "description": "Knowledge-driven, detail-oriented, expertise-seeking",
        
        "value_profile": {
            "high": ["self_direction", "achievement"],
            "medium": ["security", "universalism"],
            "low": ["hedonism", "power", "tradition"],
        },
        
        "cognitive_style": {
            "primary": "analytical",
            "secondary": "experiential",
        },
        
        "self_construal": "independent",
        
        "regulatory_focus": "prevention",
        
        "narrative_patterns": ["validation", "hero_journey"],
        
        "justification_style": {
            "primary": "rational",
            "secondary": "authority",
        },
        
        "temporal_orientation": "future_focus",
        
        "risk_orientation": "risk_averse",
        
        "linguistic_signatures": {
            "research_patterns": [
                r"\bresearch\w*\b.+\b(extensive|thorough|deep)\b",
                r"\bcompared\b.+\b(\d+|many|several)\b.+\b(options|products|brands)\b",
                r"\bread\b.+\b(review|article|study)\b",
                r"\btest\w*\b.+\bmyself\b",
            ],
            "technical_patterns": [
                r"\bspec\w*\b",
                r"\b\d+\s?(mm|cm|inch|hz|mhz|gb|mb|tb)\b",
                r"\bperformance\b.+\b(metrics|data|numbers)\b",
                r"\btechnical\w*\b",
            ],
            "precision_patterns": [
                r"\bexactly\b",
                r"\bprecisely\b",
                r"\bspecifically\b",
                r"\bmeasur\w*\b",
                r"\b\d+(\.\d+)?\b.+\b(better|worse|improvement)\b",
            ],
            "evaluation_patterns": [
                r"\bpros?\b.+\bcons?\b",
                r"\badvantages?\b.+\bdisadvantages?\b",
                r"\bcomprehensive\b.+\breview\b",
                r"\bdetailed\b.+\b(analysis|review|comparison)\b",
            ],
            "objectivity_patterns": [
                r"\bobjective\w*\b",
                r"\bunbiased\b",
                r"\bfactual\b",
                r"\bevidence\b",
                r"\bdata\b",
            ],
        },
    },
}


# =============================================================================
# DEEP ARCHETYPE DETECTOR CLASS
# =============================================================================

@dataclass
class DeepArchetypeResult:
    """Complete archetype detection result."""
    
    # Primary result
    primary_archetype: str = ""
    primary_confidence: float = 0.0
    
    # Full scores
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    
    # Dimension scores that led to this
    value_profile: Dict[str, float] = field(default_factory=dict)
    cognitive_style_scores: Dict[str, float] = field(default_factory=dict)
    self_construal_scores: Dict[str, float] = field(default_factory=dict)
    narrative_pattern_scores: Dict[str, float] = field(default_factory=dict)
    justification_style_scores: Dict[str, float] = field(default_factory=dict)
    temporal_orientation_scores: Dict[str, float] = field(default_factory=dict)
    risk_orientation_scores: Dict[str, float] = field(default_factory=dict)
    
    # Matched patterns (for explainability)
    matched_patterns: Dict[str, List[str]] = field(default_factory=dict)
    
    # Regulatory focus
    promotion_score: float = 0.0
    prevention_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_archetype": self.primary_archetype,
            "primary_confidence": self.primary_confidence,
            "archetype_scores": self.archetype_scores,
            "value_profile": self.value_profile,
            "cognitive_style": self.cognitive_style_scores,
            "self_construal": self.self_construal_scores,
            "narrative_patterns": self.narrative_pattern_scores,
            "justification_styles": self.justification_style_scores,
            "temporal_orientation": self.temporal_orientation_scores,
            "risk_orientation": self.risk_orientation_scores,
            "promotion_score": self.promotion_score,
            "prevention_score": self.prevention_score,
        }


class DeepArchetypeDetector:
    """
    Deep archetype detection using multi-dimensional psychological profiling.
    
    This is NOT keyword matching.
    This is pattern matching across 500+ linguistic markers
    organized into psychological dimensions.
    """
    
    def __init__(self):
        self._compile_all_patterns()
    
    def _compile_all_patterns(self):
        """Compile all regex patterns for efficiency."""
        self._compiled = {}
        
        # Compile value patterns
        self._compiled["values"] = {}
        for value, data in SCHWARTZ_VALUES.items():
            self._compiled["values"][value] = {}
            for category, patterns in data["markers"].items():
                self._compiled["values"][value][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile cognitive style patterns
        self._compiled["cognitive"] = {}
        for style, data in COGNITIVE_STYLES.items():
            self._compiled["cognitive"][style] = {}
            for category, patterns in data["markers"].items():
                self._compiled["cognitive"][style][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile self-construal patterns
        self._compiled["construal"] = {}
        for construal, data in SELF_CONSTRUAL.items():
            self._compiled["construal"][construal] = {}
            for category, patterns in data["markers"].items():
                self._compiled["construal"][construal][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile narrative patterns
        self._compiled["narrative"] = {}
        for narrative, data in NARRATIVE_PATTERNS.items():
            self._compiled["narrative"][narrative] = {}
            for category, patterns in data["markers"].items():
                self._compiled["narrative"][narrative][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile justification patterns
        self._compiled["justification"] = {}
        for just_type, data in JUSTIFICATION_PATTERNS.items():
            self._compiled["justification"][just_type] = {}
            for category, patterns in data["markers"].items():
                self._compiled["justification"][just_type][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile temporal patterns
        self._compiled["temporal"] = {}
        for temp_type, data in TEMPORAL_ORIENTATION.items():
            self._compiled["temporal"][temp_type] = {}
            for category, patterns in data["markers"].items():
                self._compiled["temporal"][temp_type][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile risk patterns
        self._compiled["risk"] = {}
        for risk_type, data in RISK_ORIENTATION.items():
            self._compiled["risk"][risk_type] = {}
            for category, patterns in data["markers"].items():
                self._compiled["risk"][risk_type][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
        
        # Compile archetype signature patterns
        self._compiled["signatures"] = {}
        for archetype, data in DEEP_ARCHETYPES.items():
            self._compiled["signatures"][archetype] = {}
            for category, patterns in data["linguistic_signatures"].items():
                self._compiled["signatures"][archetype][category] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]
    
    def detect(self, text: str, context: Optional[Dict] = None) -> DeepArchetypeResult:
        """
        Detect archetype through deep multi-dimensional analysis.
        
        Args:
            text: Review text to analyze
            context: Optional context (category, price, brand)
            
        Returns:
            DeepArchetypeResult with full profiling
        """
        result = DeepArchetypeResult()
        
        if not text or len(text) < 20:
            return result
        
        # 1. Score all dimensions
        result.value_profile = self._score_values(text)
        result.cognitive_style_scores = self._score_cognitive_styles(text)
        result.self_construal_scores = self._score_self_construal(text)
        result.narrative_pattern_scores = self._score_narrative_patterns(text)
        result.justification_style_scores = self._score_justification_styles(text)
        result.temporal_orientation_scores = self._score_temporal_orientation(text)
        result.risk_orientation_scores = self._score_risk_orientation(text)
        
        # 2. Calculate regulatory focus
        self._calculate_regulatory_focus(result)
        
        # 3. Score archetype signatures directly
        signature_scores = self._score_archetype_signatures(text)
        
        # 4. Calculate final archetype scores
        archetype_scores = self._calculate_archetype_scores(result, signature_scores, context)
        result.archetype_scores = archetype_scores
        
        # 5. Determine primary archetype
        if archetype_scores:
            result.primary_archetype = max(archetype_scores, key=archetype_scores.get)
            result.primary_confidence = archetype_scores[result.primary_archetype]
        
        return result
    
    def _score_dimension(self, text: str, dimension_patterns: Dict) -> Dict[str, float]:
        """Generic dimension scoring."""
        scores = {}
        
        for dim_type, categories in dimension_patterns.items():
            total_matches = 0
            for category, patterns in categories.items():
                for pattern in patterns:
                    if pattern.search(text):
                        total_matches += 1
            
            # Normalize by number of pattern categories
            if categories:
                scores[dim_type] = min(1.0, total_matches / (len(categories) * 2))
            else:
                scores[dim_type] = 0.0
        
        return scores
    
    def _score_values(self, text: str) -> Dict[str, float]:
        """Score Schwartz values."""
        return self._score_dimension(text, self._compiled["values"])
    
    def _score_cognitive_styles(self, text: str) -> Dict[str, float]:
        """Score cognitive styles."""
        return self._score_dimension(text, self._compiled["cognitive"])
    
    def _score_self_construal(self, text: str) -> Dict[str, float]:
        """Score self-construal."""
        return self._score_dimension(text, self._compiled["construal"])
    
    def _score_narrative_patterns(self, text: str) -> Dict[str, float]:
        """Score narrative patterns."""
        return self._score_dimension(text, self._compiled["narrative"])
    
    def _score_justification_styles(self, text: str) -> Dict[str, float]:
        """Score justification styles."""
        return self._score_dimension(text, self._compiled["justification"])
    
    def _score_temporal_orientation(self, text: str) -> Dict[str, float]:
        """Score temporal orientation."""
        return self._score_dimension(text, self._compiled["temporal"])
    
    def _score_risk_orientation(self, text: str) -> Dict[str, float]:
        """Score risk orientation."""
        return self._score_dimension(text, self._compiled["risk"])
    
    def _score_archetype_signatures(self, text: str) -> Dict[str, float]:
        """Score direct archetype signatures."""
        return self._score_dimension(text, self._compiled["signatures"])
    
    def _calculate_regulatory_focus(self, result: DeepArchetypeResult):
        """Calculate promotion vs prevention focus from dimension scores."""
        
        # Promotion indicators
        promotion_values = ["achievement", "power", "hedonism", "stimulation", "self_direction"]
        promotion_score = sum(result.value_profile.get(v, 0) for v in promotion_values) / len(promotion_values)
        
        # Add cognitive style contribution
        if result.cognitive_style_scores.get("intuitive", 0) > 0.3:
            promotion_score += 0.1
        
        # Add risk orientation
        promotion_score += result.risk_orientation_scores.get("risk_seeking", 0) * 0.2
        
        # Prevention indicators
        prevention_values = ["security", "conformity", "tradition"]
        prevention_score = sum(result.value_profile.get(v, 0) for v in prevention_values) / len(prevention_values)
        
        # Add cognitive style contribution
        if result.cognitive_style_scores.get("analytical", 0) > 0.3:
            prevention_score += 0.1
        
        # Add risk orientation
        prevention_score += result.risk_orientation_scores.get("risk_averse", 0) * 0.2
        
        # Normalize
        total = promotion_score + prevention_score
        if total > 0:
            result.promotion_score = promotion_score / total
            result.prevention_score = prevention_score / total
        else:
            result.promotion_score = 0.5
            result.prevention_score = 0.5
    
    def _calculate_archetype_scores(
        self,
        result: DeepArchetypeResult,
        signature_scores: Dict[str, float],
        context: Optional[Dict]
    ) -> Dict[str, float]:
        """Calculate final archetype scores from all dimensions."""
        
        archetype_scores = {}
        
        for archetype, profile in DEEP_ARCHETYPES.items():
            score = 0.0
            weights_sum = 0.0
            
            # 1. Direct signature match (weight: 0.3)
            sig_score = signature_scores.get(archetype, 0)
            score += sig_score * 0.3
            weights_sum += 0.3
            
            # 2. Value profile alignment (weight: 0.25)
            value_alignment = 0.0
            high_values = profile["value_profile"]["high"]
            low_values = profile["value_profile"]["low"]
            
            for v in high_values:
                value_alignment += result.value_profile.get(v, 0)
            for v in low_values:
                value_alignment -= result.value_profile.get(v, 0) * 0.5
            
            value_alignment = max(0, value_alignment / len(high_values))
            score += value_alignment * 0.25
            weights_sum += 0.25
            
            # 3. Cognitive style match (weight: 0.15)
            primary_cog = profile["cognitive_style"]["primary"]
            cog_score = result.cognitive_style_scores.get(primary_cog, 0)
            score += cog_score * 0.15
            weights_sum += 0.15
            
            # 4. Self-construal match (weight: 0.1)
            construal = profile["self_construal"]
            construal_score = result.self_construal_scores.get(construal, 0)
            score += construal_score * 0.1
            weights_sum += 0.1
            
            # 5. Regulatory focus match (weight: 0.1)
            reg_focus = profile["regulatory_focus"]
            if reg_focus == "promotion":
                reg_score = result.promotion_score
            elif reg_focus == "prevention":
                reg_score = result.prevention_score
            else:
                reg_score = 0.5
            score += reg_score * 0.1
            weights_sum += 0.1
            
            # 6. Narrative pattern match (weight: 0.05)
            narrative_prefs = profile["narrative_patterns"]
            narr_score = max(result.narrative_pattern_scores.get(n, 0) for n in narrative_prefs) if narrative_prefs else 0
            score += narr_score * 0.05
            weights_sum += 0.05
            
            # 7. Justification style match (weight: 0.05)
            just_primary = profile["justification_style"]["primary"]
            just_score = result.justification_style_scores.get(just_primary, 0)
            score += just_score * 0.05
            weights_sum += 0.05
            
            archetype_scores[archetype] = score / weights_sum if weights_sum > 0 else 0
        
        # Normalize
        total = sum(archetype_scores.values())
        if total > 0:
            archetype_scores = {k: v/total for k, v in archetype_scores.items()}
        
        return archetype_scores


# =============================================================================
# USAGE
# =============================================================================

if __name__ == "__main__":
    detector = DeepArchetypeDetector()
    
    # Test with different review styles
    reviews = [
        # Achiever-style
        """
        After extensive research comparing this to the competition, I can confidently say
        this is the best in its class. The premium quality is immediately apparent - this
        is clearly a professional-grade product. I don't settle for mediocre, and this
        exceeds my high standards. Worth every dollar for those who demand excellence.
        """,
        
        # Guardian-style
        """
        I was hesitant at first and read all the reviews carefully before purchasing.
        After three months of use, I can say this is reliable and dependable. My family
        uses it daily and it's held up well. The warranty gave me peace of mind, and
        customer service was helpful when I had questions. A safe, trustworthy choice.
        """,
        
        # Explorer-style
        """
        Discovered this gem by accident and I'm so glad I took the chance! It's completely
        different from anything I've tried before - unique and innovative. The experience
        was exciting and it sparked my curiosity to explore more from this brand.
        First time trying something like this and it won't be the last!
        """,
        
        # Connector-style
        """
        Bought this as a gift for my mom and she absolutely loves it! Now I got one
        for my sister too. Everyone in my family is using it now. I've been telling
        all my friends about it - you should get one for your loved ones too!
        It brings us together and we all share how much we enjoy it.
        """,
    ]
    
    for i, review in enumerate(reviews, 1):
        print(f"\n{'='*70}")
        print(f"REVIEW {i}")
        print("=" * 70)
        print(review.strip()[:200] + "...")
        
        result = detector.detect(review)
        
        print(f"\n📊 PRIMARY ARCHETYPE: {result.primary_archetype.upper()}")
        print(f"   Confidence: {result.primary_confidence:.1%}")
        
        print(f"\n📈 ALL ARCHETYPE SCORES:")
        for arch, score in sorted(result.archetype_scores.items(), key=lambda x: -x[1]):
            bar = "█" * int(score * 30)
            print(f"   {arch:12}: {bar} {score:.1%}")
        
        print(f"\n🎯 REGULATORY FOCUS:")
        print(f"   Promotion: {result.promotion_score:.1%}")
        print(f"   Prevention: {result.prevention_score:.1%}")
        
        print(f"\n💎 TOP VALUES:")
        for val, score in sorted(result.value_profile.items(), key=lambda x: -x[1])[:5]:
            if score > 0:
                print(f"   {val}: {score:.2f}")
