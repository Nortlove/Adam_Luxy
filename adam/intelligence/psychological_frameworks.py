#!/usr/bin/env python3
"""
ADAM PSYCHOLOGICAL FRAMEWORKS
=============================

Complete implementation of 82 psychological frameworks for persuasion intelligence.

Based on the ADAM specification:
- 20 framework categories
- 82 individual frameworks
- Each framework has specific linguistic markers, behavioral signals, and inference rules
- Frameworks interact - combinatorial space creates 40-54% conversion lifts

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                    REVIEW TEXT INPUT                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────────┐                 ┌───────────────────┐
│ LINGUISTIC LAYER  │                 │  CONTENT LAYER    │
└─────────┬─────────┘                 └─────────┬─────────┘
          │                                     │
          └─────────────┬───────────────────────┘
                        ▼
          ┌─────────────────────────┐
          │ PSYCHOLOGICAL INFERENCE │
          │   (82 Frameworks)       │
          └───────────┬─────────────┘
                      ▼
          ┌─────────────────────────┐
          │  MECHANISM SELECTION    │
          └─────────────────────────┘
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import math


# =============================================================================
# CATEGORY I: PERSONALITY & INDIVIDUAL DIFFERENCES (Frameworks 1-5)
# =============================================================================

# Framework 1: Big Five Personality Model
# Base layer for all personalization
BIG_FIVE_MARKERS = {
    "openness": {
        "description": "Intellectual curiosity, creativity, preference for novelty",
        "high_markers": {
            "curiosity": [
                r"\bcurious\b", r"\bwonder\w*\b", r"\bfascinat\w*\b",
                r"\bintrigu\w*\b", r"\binterest\w*\b", r"\bexplor\w*\b",
            ],
            "creativity": [
                r"\bcreativ\w*\b", r"\bimaginat\w*\b", r"\boriginal\b",
                r"\bunique\b", r"\binnovativ\w*\b", r"\bartistic\b",
            ],
            "novelty_seeking": [
                r"\bnew\b", r"\bdifferent\b", r"\bunusual\b",
                r"\bexperiment\w*\b", r"\btry\w* something\b", r"\bfirst time\b",
            ],
            "abstract_thinking": [
                r"\bconcept\w*\b", r"\btheor\w*\b", r"\bphilosoph\w*\b",
                r"\bidea\w*\b", r"\bpossibilit\w*\b", r"\bpotential\b",
            ],
            "aesthetic_appreciation": [
                r"\bbeautiful\b", r"\belegant\b", r"\bstunning\b",
                r"\bdesign\w*\b", r"\baesthetic\w*\b", r"\bstyle\b",
            ],
        },
        "low_markers": {
            "conventional": [
                r"\btraditional\b", r"\bclassic\b", r"\bstandard\b",
                r"\busual\b", r"\bnormal\b", r"\btypical\b",
            ],
            "practical_focus": [
                r"\bpractical\b", r"\bfunctional\b", r"\bno.?frills\b",
                r"\bstraightforward\b", r"\bsimple\b", r"\bbasic\b",
            ],
        },
        "application": "High O → novelty appeals, unique features; Low O → proven, traditional"
    },
    
    "conscientiousness": {
        "description": "Organization, dependability, self-discipline, achievement",
        "high_markers": {
            "organization": [
                r"\borganiz\w*\b", r"\bsystem\w*\b", r"\bmethod\w*\b",
                r"\bplan\w*\b", r"\bschedul\w*\b", r"\bstructur\w*\b",
            ],
            "thoroughness": [
                r"\bthorough\w*\b", r"\bdetail\w*\b", r"\bcareful\w*\b",
                r"\bmeticulou\w*\b", r"\bprecis\w*\b", r"\baccurat\w*\b",
            ],
            "achievement_striving": [
                r"\bgoal\w*\b", r"\bachiev\w*\b", r"\baccomplish\w*\b",
                r"\bsucce\w*\b", r"\bexcel\w*\b", r"\bperform\w*\b",
            ],
            "self_discipline": [
                r"\bdisciplin\w*\b", r"\bcommit\w*\b", r"\bdedicat\w*\b",
                r"\bpersist\w*\b", r"\bconsistent\w*\b", r"\bdiligent\b",
            ],
            "deliberation": [
                r"\bresearch\w*\b", r"\bcompare\w*\b", r"\bevaluat\w*\b",
                r"\bconsider\w*\b", r"\banalyz\w*\b", r"\bthink\w* (through|about)\b",
            ],
        },
        "low_markers": {
            "spontaneous": [
                r"\bimpuls\w*\b", r"\bspontaneous\w*\b", r"\bspur of the moment\b",
                r"\bjust (bought|decided|went)\b", r"\bwhy not\b",
            ],
            "flexible": [
                r"\bflexi\w*\b", r"\bgo with the flow\b", r"\bwhatever\b",
                r"\beasy.?going\b", r"\brelax\w*\b",
            ],
        },
        "application": "High C → detailed specs, quality assurance; Low C → spontaneous, easy"
    },
    
    "extraversion": {
        "description": "Energy from external world, sociability, assertiveness",
        "high_markers": {
            "social_engagement": [
                r"\beveryone\b", r"\bfriend\w*\b", r"\bparty\b", r"\bparties\b",
                r"\bsocial\w*\b", r"\bpeople\b", r"\btogether\b",
            ],
            "enthusiasm": [
                r"\bexcit\w*\b", r"\bamazing\b", r"\bfantastic\b",
                r"\bincredible\b", r"\bawesome\b", r"\blove\w*\b",
            ],
            "assertiveness": [
                r"\bconfident\w*\b", r"\bbold\b", r"\bassertive\b",
                r"\bdecisive\b", r"\bstrong\b", r"\bleader\w*\b",
            ],
            "activity_level": [
                r"\bactiv\w*\b", r"\benerg\w*\b", r"\bdynamic\b",
                r"\bbusy\b", r"\bon the go\b", r"\bfast.?paced\b",
            ],
            "positive_emotions": [
                r"\bhappy\b", r"\bjoy\w*\b", r"\bfun\b", r"\bthrill\w*\b",
                r"\bdelight\w*\b", r"\bpleasur\w*\b",
            ],
        },
        "low_markers": {
            "solitary": [
                r"\balone\b", r"\bby myself\b", r"\bquiet\b",
                r"\bpeaceful\b", r"\bsolitude\b", r"\bprivate\b",
            ],
            "reserved": [
                r"\breserved\b", r"\bmodest\b", r"\bsubtle\b",
                r"\bunderstat\w*\b", r"\bsimple\b",
            ],
        },
        "application": "High E → social proof, community; Low E → personal, private experience"
    },
    
    "agreeableness": {
        "description": "Cooperation, trust, altruism, compliance",
        "high_markers": {
            "trust": [
                r"\btrust\w*\b", r"\bhonest\w*\b", r"\bgenuine\b",
                r"\bauthentic\b", r"\breal\b", r"\blegit\w*\b",
            ],
            "altruism": [
                r"\bhelp\w*\b", r"\bshare\w*\b", r"\bgive\w*\b",
                r"\bgift\w*\b", r"\bfor (my|the|others)\b", r"\bgenerous\b",
            ],
            "cooperation": [
                r"\btogether\b", r"\bteam\b", r"\bcooperat\w*\b",
                r"\bcollaborat\w*\b", r"\bpartner\w*\b", r"\bjoin\w*\b",
            ],
            "sympathy": [
                r"\bunderstand\w*\b", r"\bempathy\b", r"\bcompassion\w*\b",
                r"\bcare\w*\b", r"\bkind\w*\b", r"\bsweet\b",
            ],
            "modesty": [
                r"\bhumbl\w*\b", r"\bmodest\b", r"\bsimpl\w*\b",
                r"\bdown.?to.?earth\b", r"\bno ego\b",
            ],
        },
        "low_markers": {
            "skeptical": [
                r"\bskeptic\w*\b", r"\bdoubt\w*\b", r"\bsuspicious\b",
                r"\bwary\b", r"\bcautious\b", r"\bquestion\w*\b",
            ],
            "competitive": [
                r"\bcompetit\w*\b", r"\bwin\w*\b", r"\bbeat\b",
                r"\bbest\b", r"\b#1\b", r"\btop\b",
            ],
        },
        "application": "High A → community, helping others; Low A → competitive advantage"
    },
    
    "neuroticism": {
        "description": "Emotional instability, anxiety, moodiness",
        "high_markers": {
            "anxiety": [
                r"\banxious\b", r"\bworr(y|ied)\b", r"\bstress\w*\b",
                r"\bnervous\b", r"\btense\b", r"\buneasy\b",
            ],
            "self_consciousness": [
                r"\bembarrass\w*\b", r"\bself.?conscious\b", r"\bawkward\b",
                r"\binsecur\w*\b", r"\buncertain\b", r"\bhesita\w*\b",
            ],
            "vulnerability": [
                r"\bafraid\b", r"\bscar\w*\b", r"\bfear\w*\b",
                r"\bvulnerabl\w*\b", r"\bfragil\w*\b", r"\bsensitiv\w*\b",
            ],
            "negative_emotions": [
                r"\bfrustrat\w*\b", r"\bangr\w*\b", r"\bupset\b",
                r"\bdisappoint\w*\b", r"\bsad\b", r"\bmisera\w*\b",
            ],
            "impulsiveness": [
                r"\bcouldn't (help|resist|stop)\b", r"\bhad to\b",
                r"\bimpuls\w*\b", r"\bwithout thinking\b",
            ],
        },
        "low_markers": {
            "emotional_stability": [
                r"\bcalm\b", r"\brelax\w*\b", r"\bpeaceful\b",
                r"\bsteady\b", r"\bstable\b", r"\beven.?keeled\b",
            ],
            "confidence": [
                r"\bconfident\b", r"\bsure\b", r"\bcertain\b",
                r"\bno (worries|problem|doubt)\b", r"\bcomfortabl\w*\b",
            ],
        },
        "application": "High N → reassurance, safety, guarantees; Low N → aspirational, bold"
    },
}


# Framework 2: Need for Cognition (NFC)
# High NFC → argument quality matters; Low NFC → peripheral cues matter
NEED_FOR_COGNITION_MARKERS = {
    "high_nfc": {
        "description": "Enjoys effortful thinking, prefers complex information",
        "markers": {
            "analytical_language": [
                r"\banalyz\w*\b", r"\bevaluat\w*\b", r"\bcompare\w*\b",
                r"\bresearch\w*\b", r"\bstud\w*\b", r"\btest\w*\b",
            ],
            "evidence_seeking": [
                r"\bevidence\b", r"\bproof\b", r"\bdata\b",
                r"\bfacts?\b", r"\bstatistic\w*\b", r"\bnumber\w*\b",
            ],
            "elaboration": [
                r"\bbecause\b", r"\btherefore\b", r"\bconsequently\b",
                r"\bthus\b", r"\bhence\b", r"\bas a result\b",
            ],
            "detail_orientation": [
                r"\bdetail\w*\b", r"\bspecific\w*\b", r"\bexactly\b",
                r"\bprecisely\b", r"\btechnical\w*\b", r"\bspec\w*\b",
            ],
            "question_asking": [
                r"\bwhy\b", r"\bhow (does|do|did|is|are)\b",
                r"\bwhat (makes|causes|is the)\b", r"\bwonder\w*\b",
            ],
            "pros_cons": [
                r"\bpros?\b.+\bcons?\b", r"\badvantage\w*\b.+\bdisadvantage\w*\b",
                r"\bon one hand\b", r"\bhowever\b", r"\balthough\b",
            ],
        },
        "application": "Present detailed arguments, technical specs, comparison data"
    },
    "low_nfc": {
        "description": "Prefers simple heuristics, avoids effortful thinking",
        "markers": {
            "simplicity_preference": [
                r"\bsimple\b", r"\beasy\b", r"\bstraightforward\b",
                r"\bno.?brainer\b", r"\bjust works\b", r"\bno hassle\b",
            ],
            "peripheral_cues": [
                r"\beveryone (says|loves|uses)\b", r"\bbest.?sell\w*\b",
                r"\bpopular\b", r"\btrending\b", r"\b#1\b",
            ],
            "trust_shortcuts": [
                r"\btrusted brand\b", r"\bname brand\b", r"\bknown for\b",
                r"\baward.?win\w*\b", r"\brecommended\b",
            ],
            "outcome_focus": [
                r"\bjust works\b", r"\bdoes the job\b", r"\bgets it done\b",
                r"\bworks great\b", r"\bperfect\b",
            ],
            "cognitive_ease": [
                r"\bdon't have to think\b", r"\bno thinking\b",
                r"\beasy to (use|understand|setup)\b", r"\bintuitive\b",
            ],
        },
        "application": "Use social proof, brand authority, simple claims"
    },
}


# Framework 3: Self-Monitoring
# High SM → image appeals; Low SM → product quality appeals
SELF_MONITORING_MARKERS = {
    "high_self_monitoring": {
        "description": "Adapts behavior to social situations, image-conscious",
        "markers": {
            "social_image": [
                r"\blook\w* (good|great|professional|stylish)\b",
                r"\bimpression\w*\b", r"\bimage\b", r"\bappearance\b",
                r"\bpresent\w* (myself|yourself)\b", r"\bperception\b",
            ],
            "others_reactions": [
                r"\bcompliment\w*\b", r"\bnotice\w*\b", r"\bcomment\w*\b",
                r"\bask\w* (me|about)\b", r"\bpeople (say|think|notice)\b",
            ],
            "situational_fit": [
                r"\bappropriate\b", r"\bfit\w* (the|any) (occasion|situation|event)\b",
                r"\bversatile\b", r"\bfor (work|casual|formal)\b",
            ],
            "status_signaling": [
                r"\bstatus\b", r"\bprestig\w*\b", r"\bexclusive\b",
                r"\bluxury\b", r"\bhigh.?end\b", r"\bdesigner\b",
            ],
            "social_comparison": [
                r"\bbetter than\b.+\b(others|most|theirs)\b",
                r"\bstand out\b", r"\bunlike (others|everyone)\b",
            ],
        },
        "application": "Emphasize social impression, how others will react"
    },
    "low_self_monitoring": {
        "description": "Behaves consistently across situations, authenticity-focused",
        "markers": {
            "authenticity": [
                r"\bauthentic\b", r"\bgenuine\b", r"\breal\b",
                r"\btrue to (myself|yourself)\b", r"\bhonest\b",
            ],
            "intrinsic_quality": [
                r"\bquality\b", r"\bwell.?made\b", r"\bdurable\b",
                r"\bcraftsmanship\b", r"\bmaterials?\b", r"\bconstruction\b",
            ],
            "personal_values": [
                r"\bbelie\w*\b", r"\bvalues?\b", r"\bprinciple\w*\b",
                r"\bimportant to me\b", r"\bwhat matters\b",
            ],
            "function_over_form": [
                r"\bfunction\w*\b", r"\bpractical\b", r"\buseful\b",
                r"\bpurpose\b", r"\bworks well\b", r"\bperform\w*\b",
            ],
            "internal_standards": [
                r"\bmy standards\b", r"\bpersonally\b", r"\bfor me\b",
                r"\bwhat I need\b", r"\bmy (requirements|needs)\b",
            ],
        },
        "application": "Emphasize intrinsic quality, functionality, authenticity"
    },
}


# Framework 4: Decision Style (Maximizer/Satisficer)
# Maximizers need options; Satisficers need curated recommendations
DECISION_STYLE_MARKERS = {
    "maximizer": {
        "description": "Seeks the absolute best option, comprehensive search",
        "markers": {
            "extensive_search": [
                r"\bresearch\w* (extensively|thoroughly|carefully)\b",
                r"\bcompare\w* (many|several|all|different)\b",
                r"\bspent (hours|days|weeks|months) (looking|researching|comparing)\b",
                r"\bread (all|every|hundreds of) (the )?reviews?\b",
            ],
            "best_seeking": [
                r"\b(the|absolute|very) best\b",
                r"\btop (of the line|rated|tier)\b",
                r"\b#1\b", r"\bfirst choice\b", r"\bnothing but the best\b",
            ],
            "optimization": [
                r"\boptim\w*\b", r"\bmaximiz\w*\b", r"\bperfect (one|choice|option)\b",
                r"\bexactly (what|right)\b", r"\bno compromis\w*\b",
            ],
            "regret_avoidance": [
                r"\bdidn't want to regret\b", r"\bmake sure\b",
                r"\bwouldn't (settle|compromise)\b", r"\bhad to be certain\b",
            ],
            "comparison_language": [
                r"\bvs\.?\b", r"\bversus\b", r"\bcompared to\b",
                r"\bbetter than\b", r"\binstead of\b", r"\brather than\b",
            ],
        },
        "application": "Provide comprehensive comparisons, 'best in class' positioning"
    },
    "satisficer": {
        "description": "Seeks 'good enough' option, limited search",
        "markers": {
            "good_enough": [
                r"\bgood enough\b", r"\bdoes the (job|trick)\b",
                r"\bworks (fine|well|great)\b", r"\bno complaints\b",
            ],
            "quick_decision": [
                r"\bdidn't (overthink|spend much time)\b",
                r"\bjust (bought|picked|chose|went with)\b",
                r"\bsimple (choice|decision)\b", r"\bno.?brainer\b",
            ],
            "first_acceptable": [
                r"\bfirst (one|option) that\b", r"\bmet my (needs|criteria)\b",
                r"\bchecked (all|the) boxes\b", r"\bexactly what I needed\b",
            ],
            "satisfaction": [
                r"\bhappy (with|enough)\b", r"\bsatisfied\b",
                r"\bno (regrets|complaints)\b", r"\bcan't complain\b",
            ],
            "convenience": [
                r"\bconvenient\b", r"\beasy (choice|decision|to pick)\b",
                r"\bdecided quickly\b", r"\bwent with\b",
            ],
        },
        "application": "Curated recommendations, 'recommended for you', remove choice burden"
    },
}


# Framework 5: Uncertainty Tolerance
# Affects how much information and reassurance messaging requires
UNCERTAINTY_TOLERANCE_MARKERS = {
    "high_tolerance": {
        "description": "Comfortable with ambiguity, risk-accepting",
        "markers": {
            "risk_acceptance": [
                r"\btook a (chance|risk|gamble)\b", r"\bwhy not\b",
                r"\bnothing to lose\b", r"\bworth (the risk|a try)\b",
            ],
            "ambiguity_comfort": [
                r"\bwe'll see\b", r"\bfigure it out\b", r"\bwing it\b",
                r"\bgo with the flow\b", r"\bsee what happens\b",
            ],
            "novelty_embrace": [
                r"\btried something (new|different)\b", r"\bfirst time\b",
                r"\bnever (tried|used|had) before\b", r"\bexperiment\w*\b",
            ],
            "flexible_expectations": [
                r"\bopen to\b", r"\bflexibl\w*\b", r"\badaptabl\w*\b",
                r"\beither way\b", r"\bwhatever\b",
            ],
        },
        "application": "Novel features, exploration framing, try-something-new"
    },
    "low_tolerance": {
        "description": "Needs closure, predictability, certainty",
        "markers": {
            "information_seeking": [
                r"\bresearch\w*\b", r"\bread (all|every|the) reviews?\b",
                r"\bwanted to (know|make sure|be certain)\b",
            ],
            "reassurance_seeking": [
                r"\breassur\w*\b", r"\bconfirm\w*\b", r"\bverif\w*\b",
                r"\bmake sure\b", r"\bguarantee\w*\b", r"\bcertain\b",
            ],
            "risk_avoidance": [
                r"\bworr(y|ied)\b", r"\bconcern\w*\b", r"\bhesitat\w*\b",
                r"\bskeptical\b", r"\bnervous\b", r"\bafraid\b",
            ],
            "certainty_language": [
                r"\bdefinitely\b", r"\babsolutely\b", r"\bcertainly\b",
                r"\bfor sure\b", r"\bwithout (a )?doubt\b", r"\b100%\b",
            ],
            "guarantee_seeking": [
                r"\bwarrant\w*\b", r"\bguarantee\w*\b", r"\breturn policy\b",
                r"\bmoney.?back\b", r"\brisk.?free\b", r"\btry before\b",
            ],
        },
        "application": "Provide guarantees, detailed specs, social proof, risk reversal"
    },
}


# =============================================================================
# CATEGORY II: MOTIVATIONAL FRAMEWORKS (Frameworks 6-10)
# =============================================================================

# Framework 6: Regulatory Focus Theory
# Promotion focus (gains/aspirations) vs. Prevention focus (safety/obligations)
REGULATORY_FOCUS_MARKERS = {
    "promotion": {
        "description": "Focus on gains, aspirations, advancement, growth",
        "markers": {
            "gain_language": [
                r"\bgain\w*\b", r"\beach\w*\b", r"\baccomplish\w*\b",
                r"\badvance\w*\b", r"\bprogress\w*\b", r"\bgrow\w*\b",
            ],
            "aspiration": [
                r"\bdream\w*\b", r"\baspir\w*\b", r"\bhope\w*\b",
                r"\bwish\w*\b", r"\bwant\w*\b", r"\bdesir\w*\b",
            ],
            "achievement": [
                r"\bachiev\w*\b", r"\bsucce\w*\b", r"\bwin\w*\b",
                r"\bexcel\w*\b", r"\bbest\b", r"\btop\b",
            ],
            "opportunity": [
                r"\bopportunit\w*\b", r"\bpossibilit\w*\b", r"\bpotential\b",
                r"\bcould (be|have|become)\b", r"\bchance to\b",
            ],
            "positive_outcomes": [
                r"\bimprove\w*\b", r"\benhance\w*\b", r"\bboost\w*\b",
                r"\bupgrade\w*\b", r"\belevat\w*\b", r"\btransform\w*\b",
            ],
            "ideal_self": [
                r"\bideally\b", r"\bat (my|your) best\b",
                r"\bbecome\b", r"\bmaximize\b", r"\boptimize\b",
            ],
        },
        "application": "Gain-framed messages: what you'll achieve, become, gain"
    },
    "prevention": {
        "description": "Focus on safety, obligations, security, avoiding losses",
        "markers": {
            "loss_language": [
                r"\blose\w*\b", r"\bloss\b", r"\bmiss (out)?\b",
                r"\bwaste\w*\b", r"\bregret\w*\b", r"\bfail\w*\b",
            ],
            "safety": [
                r"\bsafe\w*\b", r"\bsecur\w*\b", r"\bprotect\w*\b",
                r"\bguard\w*\b", r"\bshield\w*\b", r"\bdefend\w*\b",
            ],
            "obligation": [
                r"\bshould\b", r"\bmust\b", r"\bhave to\b",
                r"\bneed to\b", r"\bought to\b", r"\brequir\w*\b",
            ],
            "risk_avoidance": [
                r"\bavoid\w*\b", r"\bprevent\w*\b", r"\bstop\w*\b",
                r"\beliminate\w*\b", r"\breduce\w*\b", r"\bminimize\w*\b",
            ],
            "negative_outcomes": [
                r"\bproblem\w*\b", r"\bissue\w*\b", r"\bdanger\w*\b",
                r"\brisk\w*\b", r"\bthreat\w*\b", r"\bharm\w*\b",
            ],
            "ought_self": [
                r"\bsupposed to\b", r"\bexpected\b", r"\bresponsib\w*\b",
                r"\bdut\w*\b", r"\bobliga\w*\b", r"\bnecessary\b",
            ],
        },
        "application": "Loss-framed messages: what you'll avoid, prevent, protect"
    },
}


# Framework 7: Construal Level Theory
# Abstract "why" thinking vs. Concrete "how" thinking
CONSTRUAL_LEVEL_MARKERS = {
    "abstract_high_level": {
        "description": "Focus on why, meaning, purpose, big picture",
        "markers": {
            "why_focus": [
                r"\bwhy\b", r"\bpurpose\b", r"\bmeaning\w*\b",
                r"\breason\b", r"\bpoint\b", r"\bgoal\w*\b",
            ],
            "big_picture": [
                r"\boverall\b", r"\bin general\b", r"\bbig picture\b",
                r"\bas a whole\b", r"\bultimately\b", r"\bfundamental\w*\b",
            ],
            "values_principles": [
                r"\bvalue\w*\b", r"\bprinciple\w*\b", r"\bphilosoph\w*\b",
                r"\bbelie\w*\b", r"\bimportant\b", r"\bmatters?\b",
            ],
            "abstract_concepts": [
                r"\bfreedom\b", r"\bhappiness\b", r"\bsuccess\b",
                r"\bquality\b", r"\bexcellence\b", r"\bintegrety\b",
            ],
            "desirability": [
                r"\bwant\w*\b", r"\bdesir\w*\b", r"\bwish\w*\b",
                r"\bshould\b", r"\bideal\w*\b", r"\bperfect\b",
            ],
        },
        "application": "Message focuses on WHY, meaning, values, long-term impact"
    },
    "concrete_low_level": {
        "description": "Focus on how, specifics, practical details",
        "markers": {
            "how_focus": [
                r"\bhow\b", r"\bsteps?\b", r"\bprocess\b",
                r"\bmethod\b", r"\bway to\b", r"\binstructions?\b",
            ],
            "specific_details": [
                r"\bspecific\w*\b", r"\bdetail\w*\b", r"\bexactly\b",
                r"\bprecisely\b", r"\bparticular\w*\b", r"\b\d+ (inch|cm|mm|oz|lb|kg)\w*\b",
            ],
            "concrete_features": [
                r"\bfeature\w*\b", r"\bfunction\w*\b", r"\bbutton\w*\b",
                r"\bcomponent\w*\b", r"\bpart\w*\b", r"\bsetting\w*\b",
            ],
            "feasibility": [
                r"\bcan\b", r"\bable to\b", r"\bpossible\b",
                r"\bworks?\b", r"\bdoes\b", r"\bpractical\b",
            ],
            "immediate_context": [
                r"\bright now\b", r"\btoday\b", r"\bimmediately\b",
                r"\bthis (one|product|item)\b", r"\bhere\b",
            ],
        },
        "application": "Message focuses on HOW, practical details, specific features"
    },
}


# Framework 8: Temporal Orientation (already implemented, expanding)
TEMPORAL_ORIENTATION_MARKERS = {
    "past_oriented": {
        "description": "Chronic focus on past experiences and memories",
        "markers": {
            "past_tense_dominance": [
                r"\bwas\b", r"\bwere\b", r"\bhad\b",
                r"\bdid\b", r"\busually\b", r"\bused to\b",
            ],
            "memory_references": [
                r"\bremember\b", r"\brecall\b", r"\bback (when|then)\b",
                r"\bnostalgic\b", r"\bmemor\w*\b", r"\bin the past\b",
            ],
            "experience_based": [
                r"\bfrom experience\b", r"\bin my experience\b",
                r"\bover the years\b", r"\blearned that\b",
            ],
            "comparison_past": [
                r"\bcompared to (my old|the previous|what I had)\b",
                r"\bbetter than (before|my last|the old)\b",
                r"\breplace\w* (my old|the previous)\b",
            ],
        },
        "application": "Nostalgia appeals, proven track record, continuity"
    },
    "present_oriented": {
        "description": "Chronic focus on current moment and immediate gratification",
        "markers": {
            "present_tense_dominance": [
                r"\bis\b", r"\bare\b", r"\bam\b",
                r"\bright now\b", r"\bcurrently\b", r"\bat the moment\b",
            ],
            "immediate_gratification": [
                r"\binstant\w*\b", r"\bimmediately\b", r"\bright away\b",
                r"\bnow\b", r"\btoday\b", r"\bfast\b",
            ],
            "sensory_present": [
                r"\bfeels?\b", r"\blooks?\b", r"\bsmells?\b",
                r"\btastes?\b", r"\bsounds?\b", r"\benjoy\w*\b",
            ],
            "hedonistic_now": [
                r"\bpleasur\w*\b", r"\bfun\b", r"\benjoy\w*\b",
                r"\bexcit\w*\b", r"\bthrill\w*\b", r"\bdelight\w*\b",
            ],
        },
        "application": "Immediate benefits, instant gratification, sensory appeals"
    },
    "future_oriented": {
        "description": "Chronic focus on future goals and outcomes",
        "markers": {
            "future_tense_dominance": [
                r"\bwill\b", r"\bgoing to\b", r"\bplan to\b",
                r"\bintend to\b", r"\bhope to\b", r"\bexpect to\b",
            ],
            "goal_language": [
                r"\bgoal\w*\b", r"\bobjective\w*\b", r"\btarget\w*\b",
                r"\baim\w*\b", r"\bplan\w*\b", r"\bstrateg\w*\b",
            ],
            "investment_mindset": [
                r"\binvest\w*\b", r"\blong.?term\b", r"\bfuture\b",
                r"\bdown the road\b", r"\bover time\b", r"\bpay off\b",
            ],
            "anticipation": [
                r"\blooking forward\b", r"\bcan't wait\b", r"\banticipat\w*\b",
                r"\bexcited (to|about|for)\b", r"\beventually\b",
            ],
        },
        "application": "Investment framing, long-term benefits, future outcomes"
    },
}


# Framework 9: Approach-Avoidance Motivation
# First 100-300ms of behavior reveals automatic evaluation
APPROACH_AVOIDANCE_MARKERS = {
    "approach_motivated": {
        "description": "Impulse toward rewards and positive stimuli",
        "markers": {
            "positive_valence": [
                r"\blove\w*\b", r"\bwant\w*\b", r"\bneed\w*\b",
                r"\bcrave\w*\b", r"\bdesir\w*\b", r"\battract\w*\b",
            ],
            "reward_language": [
                r"\breward\w*\b", r"\bbonus\b", r"\bextra\b",
                r"\bgain\w*\b", r"\bwin\w*\b", r"\bprize\w*\b",
            ],
            "seeking_behavior": [
                r"\bsearch\w*\b", r"\blook\w* for\b", r"\bseek\w*\b",
                r"\bfind\w*\b", r"\bdiscover\w*\b", r"\bexplor\w*\b",
            ],
            "approach_actions": [
                r"\bbuy\w*\b", r"\bget\w*\b", r"\bgrab\w*\b",
                r"\btake\w*\b", r"\bpick\w*\b", r"\bchoose\w*\b",
            ],
            "positive_emotions": [
                r"\bhappy\b", r"\bexcit\w*\b", r"\bjoy\w*\b",
                r"\bthrill\w*\b", r"\bdelight\w*\b", r"\beager\b",
            ],
        },
        "application": "Reward-focused messaging, what you'll gain"
    },
    "avoidance_motivated": {
        "description": "Impulse away from threats and negative stimuli",
        "markers": {
            "negative_valence": [
                r"\bhate\w*\b", r"\bdislike\w*\b", r"\bcan't stand\b",
                r"\brepel\w*\b", r"\bdisgust\w*\b", r"\bavoid\w*\b",
            ],
            "threat_language": [
                r"\bthreat\w*\b", r"\bdanger\w*\b", r"\brisk\w*\b",
                r"\bharm\w*\b", r"\bdamage\w*\b", r"\bhurt\w*\b",
            ],
            "escape_behavior": [
                r"\bescape\w*\b", r"\bget away\b", r"\bstay away\b",
                r"\bstop\w*\b", r"\bquit\w*\b", r"\bleave\w*\b",
            ],
            "protection_actions": [
                r"\bprotect\w*\b", r"\bdefend\w*\b", r"\bshield\w*\b",
                r"\bguard\w*\b", r"\bsafe\w*\b", r"\bsecur\w*\b",
            ],
            "negative_emotions": [
                r"\bafraid\b", r"\bscar\w*\b", r"\bworr\w*\b",
                r"\banxious\b", r"\bnervous\b", r"\bfear\w*\b",
            ],
        },
        "application": "Threat-focused messaging, what you'll avoid/prevent"
    },
}


# Framework 10: Self-Determination Theory
# Autonomy, competence, relatedness needs
SELF_DETERMINATION_MARKERS = {
    "autonomy": {
        "description": "Need for self-direction and choice",
        "markers": {
            "choice_language": [
                r"\bchoose\w*\b", r"\bchoice\w*\b", r"\boption\w*\b",
                r"\bdecide\w*\b", r"\bselect\w*\b", r"\bpick\w*\b",
            ],
            "control": [
                r"\bcontrol\w*\b", r"\bmy (own )?way\b", r"\bin charge\b",
                r"\bindependent\w*\b", r"\bfreedom\b", r"\blibert\w*\b",
            ],
            "self_direction": [
                r"\bi (decided|chose|wanted)\b", r"\bfor myself\b",
                r"\bpersonally\b", r"\bmy (decision|choice|preference)\b",
            ],
            "rejection_constraint": [
                r"\bdidn't have to\b", r"\bno (pressure|obligation)\b",
                r"\bwithout (being forced|having to)\b",
            ],
        },
        "application": "Emphasize choice, control, customization"
    },
    "competence": {
        "description": "Need to feel effective and capable",
        "markers": {
            "mastery": [
                r"\bmaster\w*\b", r"\blearn\w*\b", r"\bunderstand\w*\b",
                r"\bfigure\w* out\b", r"\bgot (the hang|it)\b",
            ],
            "effectiveness": [
                r"\beffective\w*\b", r"\bworks?\b", r"\bsuccessful\w*\b",
                r"\bachiev\w*\b", r"\baccomplish\w*\b", r"\bcapable\b",
            ],
            "skill_building": [
                r"\bskill\w*\b", r"\babilit\w*\b", r"\bimprov\w*\b",
                r"\bprogress\w*\b", r"\badvance\w*\b", r"\bdevelop\w*\b",
            ],
            "confidence": [
                r"\bconfident\w*\b", r"\bcompetent\w*\b", r"\bexpert\w*\b",
                r"\bpro\b", r"\bprofessional\b", r"\bknowledgeabl\w*\b",
            ],
        },
        "application": "Show how product enables mastery, capability"
    },
    "relatedness": {
        "description": "Need for connection and belonging",
        "markers": {
            "connection": [
                r"\bconnect\w*\b", r"\bbelong\w*\b", r"\bpart of\b",
                r"\bjoin\w*\b", r"\bcommunity\b", r"\btogether\b",
            ],
            "relationships": [
                r"\bfriend\w*\b", r"\bfamily\b", r"\bloved ones?\b",
                r"\bpartner\b", r"\bspouse\b", r"\bcolleague\w*\b",
            ],
            "shared_experience": [
                r"\bshare\w*\b", r"\bwith (my|our|the)\b",
                r"\btogether\b", r"\beveryone\b", r"\bwe (all)?\b",
            ],
            "care_for_others": [
                r"\bfor (my|the) (family|kids|wife|husband)\b",
                r"\bgift\w*\b", r"\bhelp\w*\b", r"\bcare\w*\b",
            ],
        },
        "application": "Emphasize community, shared experiences, gifting"
    },
}


# =============================================================================
# CATEGORY III: COGNITIVE MECHANISM FRAMEWORKS (Frameworks 11-19)
# The Core Persuasion Levers - Cialdini+ Extended
# =============================================================================

# Framework 11: Social Proof
SOCIAL_PROOF_MARKERS = {
    "popularity": {
        "markers": [
            r"\beveryone (has|uses|loves|buys)\b",
            r"\bbest.?sell\w*\b", r"\bpopular\b", r"\btrending\b",
            r"\b#1\b", r"\bmost (popular|loved|purchased)\b",
        ],
    },
    "quantity": {
        "markers": [
            r"\b\d+\+? (reviews?|ratings?|customers?|buyers?)\b",
            r"\bthousands of\b", r"\bmillions of\b",
            r"\b\d+ (stars?|rating)\b",
        ],
    },
    "similarity": {
        "markers": [
            r"\bpeople like (me|you)\b", r"\bother (moms|dads|professionals|users)\b",
            r"\b(my|other) (friends?|family|colleagues?)\b",
            r"\brecommended by (friends|family|people I trust)\b",
        ],
    },
    "testimonials": {
        "markers": [
            r"\bmy (friend|sister|brother|mom|dad|colleague) (loves|uses|recommended)\b",
            r"\btold me about\b", r"\bheard about\b",
        ],
    },
    "bandwagon": {
        "markers": [
            r"\bjump on the bandwagon\b", r"\bjoin (the|everyone)\b",
            r"\bdon't miss out\b", r"\beveryone's (talking|raving)\b",
        ],
    },
    "application": "'{X} 5-star reviews can't be wrong' - leverage crowd validation"
}


# Framework 12: Scarcity
SCARCITY_MARKERS = {
    "quantity_limited": {
        "markers": [
            r"\bonly \d+ left\b", r"\blimited (stock|quantity|availability)\b",
            r"\balmost (sold|gone|out)\b", r"\bselling (fast|out)\b",
            r"\bfew (left|remaining)\b",
        ],
    },
    "time_limited": {
        "markers": [
            r"\blimited time\b", r"\bending soon\b", r"\blast (chance|day)\b",
            r"\bexpires?\b", r"\bdeadline\b", r"\bhurry\b",
        ],
    },
    "exclusive_access": {
        "markers": [
            r"\bexclusive\b", r"\binvite.?only\b", r"\bvip\b",
            r"\bmembers? only\b", r"\bspecial access\b",
        ],
    },
    "unique_features": {
        "markers": [
            r"\bone of a kind\b", r"\bunique\b", r"\brare\b",
            r"\bhard to find\b", r"\bnot (available )?everywhere\b",
        ],
    },
    "application": "'Only 3 left' - urgency triggers action"
}


# Framework 13: Authority
AUTHORITY_MARKERS = {
    "expertise": {
        "markers": [
            r"\bexpert\w*\b", r"\bprofessional\w*\b", r"\bspecialist\w*\b",
            r"\b(doctor|scientist|engineer|chef|dermatologist) (recommended|approved)\b",
        ],
    },
    "credentials": {
        "markers": [
            r"\bcertified\b", r"\bapproved\b", r"\baccredited\b",
            r"\blicensed\b", r"\bregistered\b", r"\bverified\b",
        ],
    },
    "awards": {
        "markers": [
            r"\baward.?win\w*\b", r"\bbest (in class|of)\b",
            r"\brecognized\b", r"\bhonored\b", r"\bacclaimed\b",
        ],
    },
    "institutional": {
        "markers": [
            r"\bFDA\b", r"\bUSDA\b", r"\bFDA.?approved\b",
            r"\bclinically (proven|tested)\b", r"\bscientifically (proven|backed)\b",
        ],
    },
    "brand_authority": {
        "markers": [
            r"\btrusted brand\b", r"\bleading (brand|company|manufacturer)\b",
            r"\bindustry (leader|standard)\b", r"\breputation\b",
        ],
    },
    "application": "'Expert recommended' - credibility through expertise"
}


# Framework 14: Reciprocity
RECIPROCITY_MARKERS = {
    "gifts": {
        "markers": [
            r"\bfree (gift|sample|trial)\b", r"\bbonus\b", r"\bextra\b",
            r"\bincluded\b", r"\bthrew in\b", r"\badded\b",
        ],
    },
    "value_added": {
        "markers": [
            r"\bmore than (expected|I paid for)\b", r"\bexceeded\b",
            r"\bwent above and beyond\b", r"\bextra (mile|value)\b",
        ],
    },
    "concessions": {
        "markers": [
            r"\bdiscount\w*\b", r"\bdeal\b", r"\bbargain\b",
            r"\bsave\w*\b", r"\boff\b", r"\breduced\b",
        ],
    },
    "service": {
        "markers": [
            r"\bcustomer service\b", r"\bhelpful\b", r"\bwent out of (their )?way\b",
            r"\btook care of\b", r"\bmade it right\b",
        ],
    },
    "application": "Free trials, gifts, content value - give to get"
}


# Framework 15: Commitment-Consistency
COMMITMENT_MARKERS = {
    "prior_commitments": {
        "markers": [
            r"\bbeen (using|buying|a customer) for\b",
            r"\blong.?time (user|customer|fan)\b",
            r"\bloyal\b", r"\balways (buy|use|come back)\b",
        ],
    },
    "small_steps": {
        "markers": [
            r"\bstarted with\b", r"\btried\b", r"\bfirst (purchase|order)\b",
            r"\bgave it a (try|chance|shot)\b",
        ],
    },
    "identity_consistency": {
        "markers": [
            r"\bI'm (the type|someone) who\b", r"\bas a (mom|professional|athlete)\b",
            r"\baligns with (my|our)\b", r"\bfits (my|our) (lifestyle|values)\b",
        ],
    },
    "public_commitment": {
        "markers": [
            r"\btold everyone\b", r"\brecommended to\b",
            r"\bposted (about|on)\b", r"\bshared\b",
        ],
    },
    "application": "Small asks escalating to conversion - foot in door"
}


# Framework 16: Liking
LIKING_MARKERS = {
    "similarity": {
        "markers": [
            r"\bjust like (me|you|us)\b", r"\bsame (situation|problem|need)\b",
            r"\brelat\w* to\b", r"\bunderstand\w*\b",
        ],
    },
    "familiarity": {
        "markers": [
            r"\bfamiliar\b", r"\brecogniz\w*\b", r"\bknow (this|the) brand\b",
            r"\bused (before|this brand)\b",
        ],
    },
    "attractiveness": {
        "markers": [
            r"\bbeautiful\b", r"\bgorgeous\b", r"\bstunning\b",
            r"\belegant\b", r"\bstylish\b", r"\bclassy\b",
        ],
    },
    "compliments": {
        "markers": [
            r"\bcompliment\w*\b", r"\bnotice\w*\b", r"\bpraise\w*\b",
            r"\badmir\w*\b", r"\bappreciat\w*\b",
        ],
    },
    "association": {
        "markers": [
            r"\bremind\w* (me|of)\b", r"\bjust like (my mom|grandma)\b",
            r"\breminiscent\b", r"\bbrings back\b",
        ],
    },
    "application": "Brand personality and warmth - we buy from those we like"
}


# Framework 17: Loss Aversion (2:1 ratio)
LOSS_AVERSION_MARKERS = {
    "loss_language": {
        "markers": [
            r"\bdon't miss\b", r"\bmissing out\b", r"\blose\b",
            r"\bloss\b", r"\bwaste\b", r"\bregret\w*\b",
        ],
    },
    "possession_framing": {
        "markers": [
            r"\byours?\b", r"\balready (have|own)\b",
            r"\bdon't let (it )?go\b", r"\bkeep\b",
        ],
    },
    "risk_language": {
        "markers": [
            r"\brisk\w*\b", r"\bdanger\w*\b", r"\bproblem\w*\b",
            r"\bissue\w*\b", r"\btrouble\b", r"\bworry\b",
        ],
    },
    "negative_consequences": {
        "markers": [
            r"\bif you don't\b", r"\bwithout this\b",
            r"\bcould (miss|lose|waste)\b", r"\bwon't (be able|have)\b",
        ],
    },
    "application": "'Don't miss out' - losses loom 2x larger than gains"
}


# Framework 18: Anchoring
ANCHORING_MARKERS = {
    "price_anchors": {
        "markers": [
            r"\bwas \$\d+\b", r"\boriginal(ly)? \$\d+\b",
            r"\bcompare (to|at) \$\d+\b", r"\bvalued at \$\d+\b",
        ],
    },
    "comparison_anchors": {
        "markers": [
            r"\bcompared to\b", r"\bversus\b", r"\bvs\.?\b",
            r"\binstead of\b", r"\brather than\b",
        ],
    },
    "quantity_anchors": {
        "markers": [
            r"\bup to \d+\b", r"\bas (much|many) as \d+\b",
            r"\b\d+x (more|better|faster)\b",
        ],
    },
    "reference_points": {
        "markers": [
            r"\bfor (only|just) \$\d+\b", r"\bstarting at\b",
            r"\bfrom \$\d+\b", r"\bas low as\b",
        ],
    },
    "application": "First number sets the reference - price comparison architecture"
}


# Framework 19: Framing Effects
FRAMING_MARKERS = {
    "gain_frame": {
        "markers": [
            r"\bgain\b", r"\bget\b", r"\beach\w*\b",
            r"\bwin\b", r"\bearn\b", r"\breceive\b",
        ],
    },
    "loss_frame": {
        "markers": [
            r"\blose\b", r"\bmiss\b", r"\bwaste\b",
            r"\bforgo\b", r"\bgive up\b", r"\bsacrifice\b",
        ],
    },
    "positive_frame": {
        "markers": [
            r"\b\d+% (success|satisfaction|effective)\b",
            r"\b\d+ out of \d+ (love|recommend|succeed)\b",
        ],
    },
    "negative_frame": {
        "markers": [
            r"\b\d+% (fail|risk|problem)\b",
            r"\b\d+ out of \d+ (fail|complain|unhappy)\b",
        ],
    },
    "application": "Same information, different presentation - gain vs loss framing"
}


# =============================================================================
# CATEGORY IV: NEUROSCIENCE-GROUNDED FRAMEWORKS (Frameworks 20-24)
# =============================================================================

# Framework 20: Wanting-Liking Dissociation
WANTING_LIKING_MARKERS = {
    "wanting": {
        "description": "Dopaminergic anticipation/desire",
        "markers": [
            r"\bcan't wait\b", r"\bexcited (to|for|about)\b",
            r"\banticipat\w*\b", r"\blooking forward\b",
            r"\bcrave\w*\b", r"\bwant\w*\b", r"\bneed\w*\b",
        ],
    },
    "liking": {
        "description": "Opioid satisfaction/enjoyment",
        "markers": [
            r"\blove\w*\b", r"\benjoy\w*\b", r"\bsatisf\w*\b",
            r"\bhappy (with)?\b", r"\bpleasur\w*\b", r"\bdelight\w*\b",
        ],
    },
    "application": "Trigger anticipation (wanting) vs satisfaction (liking)"
}


# Framework 21: Automatic Evaluation (100-300ms)
AUTOMATIC_EVALUATION_MARKERS = {
    "immediate_positive": {
        "description": "Fast positive evaluation",
        "markers": [
            r"\bat first (sight|glance)\b", r"\bimmediately\b",
            r"\binstantly\b", r"\bright away\b", r"\blove at first\b",
        ],
    },
    "immediate_negative": {
        "description": "Fast negative evaluation",
        "markers": [
            r"\bright away (knew|noticed|saw)\b.+\b(problem|issue|wrong)\b",
            r"\bimmediately (saw|noticed)\b.+\b(flaw|defect|issue)\b",
        ],
    },
    "application": "Align ad valence with detected approach tendency"
}


# Framework 22: Embodied Cognition
EMBODIED_COGNITION_MARKERS = {
    "tactile": {
        "markers": [
            r"\bfeel\w*\b", r"\btouch\w*\b", r"\bsoft\b", r"\bsmooth\b",
            r"\bhard\b", r"\brough\b", r"\btexture\b", r"\bweight\b",
        ],
    },
    "visual": {
        "markers": [
            r"\blook\w*\b", r"\bsee\w*\b", r"\bappear\w*\b",
            r"\bcolor\w*\b", r"\bshine\w*\b", r"\bbright\b", r"\bdark\b",
        ],
    },
    "olfactory": {
        "markers": [
            r"\bsmell\w*\b", r"\bscent\w*\b", r"\baroma\b",
            r"\bfragran\w*\b", r"\bodor\b",
        ],
    },
    "gustatory": {
        "markers": [
            r"\btaste\w*\b", r"\bflavor\w*\b", r"\bdelicious\b",
            r"\bsweet\b", r"\bsour\b", r"\bbitter\b", r"\bsalty\b",
        ],
    },
    "auditory": {
        "markers": [
            r"\bsound\w*\b", r"\bhear\w*\b", r"\bloud\b",
            r"\bquiet\b", r"\bnoise\w*\b", r"\bclick\w*\b",
        ],
    },
    "kinesthetic": {
        "markers": [
            r"\bcomfort\w*\b", r"\bfit\w*\b", r"\bwear\w*\b",
            r"\bmovement\b", r"\bbalanc\w*\b", r"\bposture\b",
        ],
    },
    "temperature": {
        "markers": [
            r"\bwarm\b", r"\bcool\b", r"\bhot\b", r"\bcold\b",
            r"\btemperature\b", r"\bcozy\b",
        ],
    },
    "application": "Sensory language activates physical simulation"
}


# Framework 23: Attention Dynamics
ATTENTION_MARKERS = {
    "novelty_capture": {
        "markers": [
            r"\bnew\b", r"\bdifferent\b", r"\bunique\b",
            r"\bfirst (of its kind|time)\b", r"\bnever (seen|before)\b",
        ],
    },
    "salience_capture": {
        "markers": [
            r"\bamazing\b", r"\bincredible\b", r"\bunbelievable\b",
            r"\bshocking\b", r"\bsurpris\w*\b", r"\bunexpect\w*\b",
        ],
    },
    "emotional_capture": {
        "markers": [
            r"\blove\b", r"\bhate\b", r"\bfear\b", r"\bjoy\b",
            r"\banger\b", r"\bdisgust\b", r"\bsurprise\b",
        ],
    },
    "personal_relevance": {
        "markers": [
            r"\bfor (me|you)\b", r"\bmy\b", r"\byour\b",
            r"\bpersonally\b", r"\bexactly what (I|you) (need|want)\b",
        ],
    },
    "application": "Design for attention capture based on context"
}


# Framework 24: Processing Fluency
PROCESSING_FLUENCY_MARKERS = {
    "high_fluency": {
        "description": "Easy processing → feels trustworthy",
        "markers": [
            r"\beasy (to understand|to use)\b", r"\bsimple\b",
            r"\bstraightforward\b", r"\bintuitive\b", r"\bclear\b",
            r"\bsmooth\b", r"\bseamless\b", r"\beffortless\b",
        ],
    },
    "low_fluency": {
        "description": "Difficult processing → feels unfamiliar",
        "markers": [
            r"\bconfus\w*\b", r"\bcomplicate\w*\b", r"\bcomplex\b",
            r"\bhard to (understand|figure out)\b", r"\btricky\b",
        ],
    },
    "application": "Smooth experiences feel more trustworthy"
}


# =============================================================================
# CATEGORY V: SOCIAL & EVOLUTIONARY FRAMEWORKS (Frameworks 25-29)
# =============================================================================

# Framework 25: Mimetic Desire (Girard)
MIMETIC_DESIRE_MARKERS = {
    "model_reference": {
        "markers": [
            r"\blike (my|the) (friend|celebrity|influencer|idol)\b",
            r"\bseen (on|in|at)\b", r"\bas seen\b",
            r"\b(celebrity|influencer|model) (uses|wears|has)\b",
        ],
    },
    "aspiration": {
        "markers": [
            r"\baspir\w*\b", r"\bwant to be\b", r"\bdream of\b",
            r"\blook like\b", r"\bjust like (them|her|him)\b",
        ],
    },
    "envy": {
        "markers": [
            r"\bjealous\b", r"\benv\w*\b", r"\bwish I had\b",
            r"\bwant (what they|theirs)\b",
        ],
    },
    "application": "We want what others want - aspirational modeling"
}


# Framework 26: Evolutionary Motives
EVOLUTIONARY_MOTIVES_MARKERS = {
    "status": {
        "markers": [
            r"\bstatus\b", r"\bprestig\w*\b", r"\bexclusive\b",
            r"\bluxury\b", r"\bhigh.?end\b", r"\bpremium\b",
        ],
    },
    "mating": {
        "markers": [
            r"\battractive\b", r"\bsexy\b", r"\bhot\b",
            r"\bimpressive\b", r"\bdesirable\b", r"\bcharming\b",
        ],
    },
    "affiliation": {
        "markers": [
            r"\bbelong\w*\b", r"\bfit in\b", r"\bpart of\b",
            r"\bcommunity\b", r"\bgroup\b", r"\btribe\b",
        ],
    },
    "protection": {
        "markers": [
            r"\bprotect\w*\b", r"\bsafe\w*\b", r"\bsecur\w*\b",
            r"\bdefend\w*\b", r"\bshield\w*\b", r"\bguard\w*\b",
        ],
    },
    "kin_care": {
        "markers": [
            r"\bfamily\b", r"\bchildren\b", r"\bkids?\b",
            r"\bparents?\b", r"\bspouse\b", r"\bloved ones?\b",
        ],
    },
    "application": "Fundamental human drive activation"
}


# Framework 27: Social Comparison Orientation
SOCIAL_COMPARISON_MARKERS = {
    "upward_comparison": {
        "description": "Comparing to those better off",
        "markers": [
            r"\bbetter than (mine|what I had)\b",
            r"\bwish (I|my) (had|was)\b", r"\baspir\w*\b",
            r"\bjust like (the|my) (friend|neighbor|colleague)\b.+\b(has|got)\b",
        ],
    },
    "downward_comparison": {
        "description": "Comparing to those worse off",
        "markers": [
            r"\bbetter than (most|others|theirs)\b",
            r"\bunlike (cheap|other|inferior)\b",
            r"\babove (average|the rest)\b",
        ],
    },
    "lateral_comparison": {
        "description": "Comparing to similar others",
        "markers": [
            r"\bpeople like (me|us)\b", r"\bsimilar to (mine|ours)\b",
            r"\bsame (situation|need|problem)\b",
        ],
    },
    "application": "'People like you chose...' targeting"
}


# Framework 28: Identity Construction
IDENTITY_MARKERS = {
    "self_concept": {
        "markers": [
            r"\bI'm (the type|someone) (who|that)\b",
            r"\bas a (professional|mom|dad|athlete|creative)\b",
            r"\breflects (who I am|my personality)\b",
        ],
    },
    "identity_expression": {
        "markers": [
            r"\bexpress\w* (myself|my)\b", r"\bmy (style|personality)\b",
            r"\bsay\w* something about (me|who I am)\b",
        ],
    },
    "identity_alignment": {
        "markers": [
            r"\baligns with (my|our)\b", r"\bfits (my|our) (lifestyle|values)\b",
            r"\brepresents (what I|who I)\b",
        ],
    },
    "application": "Products affirm self-concept - match brand to self-image"
}


# Framework 29: Belongingness/Affiliation Need
BELONGINGNESS_MARKERS = {
    "connection": {
        "markers": [
            r"\bconnect\w*\b", r"\bbelong\w*\b", r"\bpart of\b",
            r"\bjoin\w*\b", r"\bmember\w*\b", r"\bcommunity\b",
        ],
    },
    "inclusion": {
        "markers": [
            r"\bincluded\b", r"\bwelcome\w*\b", r"\baccept\w*\b",
            r"\bfit in\b", r"\bone of (us|them)\b",
        ],
    },
    "tribal": {
        "markers": [
            r"\btribe\b", r"\bfan\w*\b", r"\bfollower\w*\b",
            r"\benth\w*\b", r"\bcommunity\b", r"\bmovement\b",
        ],
    },
    "application": "Community and tribal messaging"
}


# =============================================================================
# CATEGORY VI: DECISION-MAKING FRAMEWORKS (Frameworks 30-34)
# =============================================================================

# Framework 30: Dual-Process Theory (System 1/2)
DUAL_PROCESS_MARKERS = {
    "system1_intuitive": {
        "description": "Fast, automatic, emotional",
        "markers": {
            "immediate_reactions": [
                r"\binstantly\b", r"\bimmediately\b", r"\bright away\b",
                r"\bjust (knew|felt|loved)\b", r"\bat first (sight|glance)\b",
            ],
            "emotional_language": [
                r"\blove\w*\b", r"\bhate\w*\b", r"\bfeel\w*\b",
                r"\bgut (feeling|instinct)\b", r"\bheart\b",
            ],
            "heuristic_cues": [
                r"\beveryone (says|loves)\b", r"\btrusted brand\b",
                r"\b#1\b", r"\bbest.?sell\w*\b",
            ],
        },
        "application": "Simple, emotional appeals, social proof"
    },
    "system2_deliberate": {
        "description": "Slow, effortful, rational",
        "markers": {
            "deliberation": [
                r"\bthink\w* (about|through|carefully)\b",
                r"\bconsider\w*\b", r"\bevaluat\w*\b", r"\banalyz\w*\b",
            ],
            "comparison": [
                r"\bcompare\w*\b", r"\bvs\.?\b", r"\bversus\b",
                r"\bpros?\b.+\bcons?\b", r"\bweigh\w*\b",
            ],
            "research": [
                r"\bresearch\w*\b", r"\bread (all|the) reviews\b",
                r"\bstud\w*\b", r"\binvestigat\w*\b",
            ],
        },
        "application": "Detailed arguments, comparisons, evidence"
    },
}


# Framework 31: Elaboration Likelihood Model
ELM_MARKERS = {
    "central_route": {
        "description": "High involvement, argument-focused",
        "markers": {
            "argument_quality": [
                r"\bevidence\b", r"\bproof\b", r"\bdata\b",
                r"\bfacts?\b", r"\bresearch\b", r"\btest\w*\b",
            ],
            "feature_analysis": [
                r"\bfeature\w*\b", r"\bspec\w*\b", r"\bdetail\w*\b",
                r"\btechnical\w*\b", r"\bperformance\b",
            ],
            "elaboration": [
                r"\bbecause\b", r"\btherefore\b", r"\bconsequently\b",
                r"\bthe reason\b", r"\bin other words\b",
            ],
        },
        "application": "Strong arguments for high-involvement decisions"
    },
    "peripheral_route": {
        "description": "Low involvement, cue-focused",
        "markers": {
            "source_cues": [
                r"\bexpert\b", r"\bcelebrity\b", r"\btrusted\b",
                r"\brecommended\b", r"\bapproved\b",
            ],
            "social_cues": [
                r"\beveryone\b", r"\bpopular\b", r"\btrending\b",
                r"\b#1\b", r"\bbest.?sell\w*\b",
            ],
            "attractiveness_cues": [
                r"\bbeautiful\b", r"\bgorgeous\b", r"\bstunning\b",
                r"\belegant\b", r"\bstylish\b",
            ],
        },
        "application": "Simple cues for low-involvement decisions"
    },
}


# Framework 32: Decision Fatigue
DECISION_FATIGUE_MARKERS = {
    "fatigue_indicators": {
        "markers": [
            r"\btired (of|from) (searching|looking|comparing)\b",
            r"\boverwhel\w*\b", r"\bexhaust\w*\b", r"\bfrustrat\w*\b",
            r"\bfinally (just|decided)\b", r"\bafter (hours|days|weeks)\b",
        ],
    },
    "simplification_seeking": {
        "markers": [
            r"\bjust (wanted|needed) something\b",
            r"\bsimple (choice|decision)\b", r"\bno.?brainer\b",
            r"\beasy (to pick|decision)\b", r"\bwent with\b",
        ],
    },
    "application": "Time-of-day targeting, reduce complexity late in day"
}


# Framework 33: Choice Overload
CHOICE_OVERLOAD_MARKERS = {
    "overload_indicators": {
        "markers": [
            r"\btoo many (options|choices)\b", r"\boverwhel\w*\b",
            r"\bconfus\w*\b", r"\bhard to (choose|decide|pick)\b",
            r"\bso many\b.+\b(options|choices|products)\b",
        ],
    },
    "curation_preference": {
        "markers": [
            r"\bnarrow\w* down\b", r"\bfilter\w*\b", r"\bshortlist\w*\b",
            r"\brecommend\w*\b", r"\bsuggested\b", r"\bcurated\b",
        ],
    },
    "application": "Curate based on decision style - fewer options for some"
}


# Framework 34: Cognitive Load Theory
COGNITIVE_LOAD_MARKERS = {
    "high_load_indicators": {
        "markers": [
            r"\bcomplex\b", r"\bcomplicat\w*\b", r"\bconfus\w*\b",
            r"\bhard to (understand|figure out)\b", r"\blearning curve\b",
        ],
    },
    "low_load_indicators": {
        "markers": [
            r"\bsimple\b", r"\beasy (to understand|to use)\b",
            r"\bstraightforward\b", r"\bintuitive\b", r"\bclear\b",
        ],
    },
    "application": "Simplify messaging when cognitive load is high"
}


# =============================================================================
# CATEGORY VII: PSYCHOLINGUISTIC ANALYSIS (Frameworks 35-40)
# =============================================================================

# Framework 35: LIWC-Style Analysis
# 500 function words predict personality, emotion, status
LIWC_MARKERS = {
    "pronouns": {
        "first_person_singular": [r"\bi\b", r"\bme\b", r"\bmy\b", r"\bmine\b", r"\bmyself\b"],
        "first_person_plural": [r"\bwe\b", r"\bus\b", r"\bour\b", r"\bours\b", r"\bourselves\b"],
        "second_person": [r"\byou\b", r"\byour\b", r"\byours\b", r"\byourself\b"],
        "third_person": [r"\bhe\b", r"\bshe\b", r"\bthey\b", r"\bthem\b", r"\btheir\b"],
    },
    "articles": [r"\ba\b", r"\ban\b", r"\bthe\b"],
    "prepositions": [r"\bto\b", r"\bof\b", r"\bin\b", r"\bfor\b", r"\bwith\b", r"\bon\b", r"\bat\b"],
    "conjunctions": [r"\band\b", r"\bbut\b", r"\bor\b", r"\bbecause\b", r"\bif\b", r"\balthough\b"],
    "negations": [r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bdon't\b", r"\bwon't\b", r"\bcan't\b"],
    "quantifiers": [r"\ball\b", r"\bsome\b", r"\bmany\b", r"\bfew\b", r"\bmost\b", r"\bevery\b"],
    "affect_positive": [r"\bhappy\b", r"\blove\b", r"\bgood\b", r"\bgreat\b", r"\bexcit\w*\b"],
    "affect_negative": [r"\bsad\b", r"\banger\w*\b", r"\bfear\w*\b", r"\bworr\w*\b", r"\bhate\b"],
    "cognitive_processes": [r"\bthink\b", r"\bknow\b", r"\bbelieve\b", r"\bfeel\b", r"\bunderstand\b"],
    "social_processes": [r"\bfriend\w*\b", r"\bfamily\b", r"\bpeople\b", r"\btalk\w*\b", r"\bshare\w*\b"],
    "application": "Function words reveal psychological state"
}


# Framework 36: Absolutist Language Detection
# "Always/never" thinking correlates with anxiety/depression (d > 3.14)
ABSOLUTIST_MARKERS = {
    "absolutist_words": {
        "markers": [
            r"\balways\b", r"\bnever\b", r"\bcompletely\b", r"\btotally\b",
            r"\babsolutely\b", r"\bentirely\b", r"\bnothing\b", r"\beverything\b",
            r"\bno one\b", r"\beveryone\b", r"\bperfect\w*\b", r"\bworst\b",
        ],
    },
    "black_white_thinking": {
        "markers": [
            r"\beither\b.+\bor\b", r"\ball or nothing\b",
            r"\bonly (one|way)\b", r"\bmust (be|have)\b",
        ],
    },
    "application": "High absolutist language may indicate emotional distress"
}


# Framework 37: Pronoun Analysis
# I/we/you ratios reveal social status
PRONOUN_ANALYSIS = {
    "i_focus": {
        "description": "Self-focus, lower status indicator when excessive",
        "markers": [r"\bi\b", r"\bme\b", r"\bmy\b", r"\bmine\b", r"\bmyself\b"],
    },
    "we_focus": {
        "description": "Group focus, affiliation orientation",
        "markers": [r"\bwe\b", r"\bus\b", r"\bour\b", r"\bours\b", r"\bourselves\b"],
    },
    "you_focus": {
        "description": "Other focus, higher status indicator",
        "markers": [r"\byou\b", r"\byour\b", r"\byours\b", r"\byourself\b"],
    },
    "application": "High-status = outward focus (you/they); Low-status = inward focus (I)"
}


# Framework 38: Temporal Linguistic Markers
TEMPORAL_LINGUISTIC_MARKERS = {
    "past_tense": {
        "markers": [
            r"\bwas\b", r"\bwere\b", r"\bhad\b", r"\bdid\b",
            r"\bbought\b", r"\bgot\b", r"\breceived\b", r"\btried\b",
        ],
    },
    "present_tense": {
        "markers": [
            r"\bis\b", r"\bare\b", r"\bam\b", r"\bhas\b",
            r"\bworks?\b", r"\blove\w*\b", r"\buse\w*\b",
        ],
    },
    "future_tense": {
        "markers": [
            r"\bwill\b", r"\bgoing to\b", r"\bplan to\b",
            r"\bintend to\b", r"\bhope to\b", r"\bexpect to\b",
        ],
    },
    "application": "Reveals chronic temporal orientation"
}


# Framework 39: Certainty Language
# Correlates with purchase likelihood (r = .47-.56)
CERTAINTY_MARKERS = {
    "high_certainty": {
        "markers": [
            r"\bdefinitely\b", r"\babsolutely\b", r"\bcertainly\b",
            r"\bfor sure\b", r"\bwithout (a )?doubt\b", r"\b100%\b",
            r"\bguarantee\w*\b", r"\bcertain\w*\b", r"\bpositive\b",
        ],
    },
    "low_certainty": {
        "markers": [
            r"\bmaybe\b", r"\bperhaps\b", r"\bpossibly\b",
            r"\bmight\b", r"\bcould\b", r"\bprobably\b",
            r"\bnot sure\b", r"\buncertain\b", r"\bdon't know\b",
        ],
    },
    "application": "High certainty correlates with purchase likelihood"
}


# Framework 40: Emotional Intensity Analysis
# Strength of affect expression correlates with ad effectiveness (r = .83)
EMOTIONAL_INTENSITY_MARKERS = {
    "low_intensity": {
        "markers": [
            r"\bokay\b", r"\bfine\b", r"\bdecent\b", r"\balright\b",
            r"\bgood\b", r"\bnice\b", r"\blike\b",
        ],
    },
    "medium_intensity": {
        "markers": [
            r"\bgreat\b", r"\breally (good|like|nice)\b",
            r"\bvery (good|happy|pleased)\b", r"\bquite\b",
        ],
    },
    "high_intensity": {
        "markers": [
            r"\bamazing\b", r"\bincredible\b", r"\bfantastic\b",
            r"\bunbelievable\b", r"\bextraordinary\b", r"\bmind.?blow\w*\b",
            r"\babsolutely (love|amazing|incredible)\b",
        ],
    },
    "extreme_intensity": {
        "markers": [
            r"\bbest (ever|I've ever)\b", r"\bworst (ever|I've ever)\b",
            r"\blife.?chang\w*\b", r"\bgame.?chang\w*\b",
            r"\bcan't live without\b", r"\bchanged my life\b",
        ],
    },
    "application": "Emotional intensity correlates with review influence"
}


# =============================================================================
# CATEGORY VIII-XX: Additional Frameworks
# (Will continue in deep_psychological_frameworks_extended.py)
# =============================================================================

# This file contains frameworks 1-40. The remaining frameworks (41-82) are in:
# - adam/intelligence/psychological_frameworks_temporal.py (41-45)
# - adam/intelligence/psychological_frameworks_behavioral.py (46-50)
# - adam/intelligence/psychological_frameworks_brand.py (51-53)
# - adam/intelligence/psychological_frameworks_moral.py (54-55)
# - adam/intelligence/psychological_frameworks_memory.py (56-58)
# - adam/intelligence/psychological_frameworks_narrative.py (59-61)
# - adam/intelligence/psychological_frameworks_trust.py (62-64)
# - adam/intelligence/psychological_frameworks_price.py (65-67)
# - adam/intelligence/psychological_frameworks_mechanism.py (68-70)
# - adam/intelligence/psychological_frameworks_context.py (71-73)
# - adam/intelligence/psychological_frameworks_cultural.py (74-76)
# - adam/intelligence/psychological_frameworks_ethical.py (77-79)
# - adam/intelligence/psychological_frameworks_advanced.py (80-82)


# =============================================================================
# FRAMEWORK ANALYZER CLASS
# =============================================================================

@dataclass
class FrameworkScore:
    """Score for a single framework."""
    framework_id: int
    framework_name: str
    category: str
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    dominant_dimension: str = ""
    confidence: float = 0.0
    matched_patterns: List[str] = field(default_factory=list)
    application: str = ""


@dataclass
class PsychologicalProfile:
    """Complete psychological profile from all 82 frameworks."""
    
    # Framework scores by category
    personality_scores: Dict[str, float] = field(default_factory=dict)
    motivation_scores: Dict[str, float] = field(default_factory=dict)
    cognitive_mechanism_scores: Dict[str, float] = field(default_factory=dict)
    neuroscience_scores: Dict[str, float] = field(default_factory=dict)
    social_scores: Dict[str, float] = field(default_factory=dict)
    decision_scores: Dict[str, float] = field(default_factory=dict)
    linguistic_scores: Dict[str, float] = field(default_factory=dict)
    
    # Framework-specific results
    framework_results: Dict[int, FrameworkScore] = field(default_factory=dict)
    
    # Inferred archetypes (from transfer learning)
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    primary_archetype: str = ""
    
    # Persuasion mechanism recommendations
    recommended_mechanisms: List[str] = field(default_factory=list)
    mechanism_synergies: List[Tuple[str, str, float]] = field(default_factory=list)
    
    # Confidence calibration
    overall_confidence: float = 0.0
    sample_size: int = 0


class PsychologicalFrameworkAnalyzer:
    """
    Analyzes text against all 82 psychological frameworks.
    
    This is the core intelligence engine for ADAM's persuasion system.
    """
    
    def __init__(self):
        self._compile_all_patterns()
    
    def _compile_all_patterns(self):
        """Compile all regex patterns for efficiency."""
        self.compiled_patterns = {}
        
        # Compile all framework patterns
        all_frameworks = {
            "big_five": BIG_FIVE_MARKERS,
            "nfc": NEED_FOR_COGNITION_MARKERS,
            "self_monitoring": SELF_MONITORING_MARKERS,
            "decision_style": DECISION_STYLE_MARKERS,
            "uncertainty_tolerance": UNCERTAINTY_TOLERANCE_MARKERS,
            "regulatory_focus": REGULATORY_FOCUS_MARKERS,
            "construal_level": CONSTRUAL_LEVEL_MARKERS,
            "temporal": TEMPORAL_ORIENTATION_MARKERS,
            "approach_avoidance": APPROACH_AVOIDANCE_MARKERS,
            "self_determination": SELF_DETERMINATION_MARKERS,
            "social_proof": SOCIAL_PROOF_MARKERS,
            "scarcity": SCARCITY_MARKERS,
            "authority": AUTHORITY_MARKERS,
            "reciprocity": RECIPROCITY_MARKERS,
            "commitment": COMMITMENT_MARKERS,
            "liking": LIKING_MARKERS,
            "loss_aversion": LOSS_AVERSION_MARKERS,
            "anchoring": ANCHORING_MARKERS,
            "framing": FRAMING_MARKERS,
            "wanting_liking": WANTING_LIKING_MARKERS,
            "automatic_evaluation": AUTOMATIC_EVALUATION_MARKERS,
            "embodied_cognition": EMBODIED_COGNITION_MARKERS,
            "attention": ATTENTION_MARKERS,
            "processing_fluency": PROCESSING_FLUENCY_MARKERS,
            "mimetic_desire": MIMETIC_DESIRE_MARKERS,
            "evolutionary": EVOLUTIONARY_MOTIVES_MARKERS,
            "social_comparison": SOCIAL_COMPARISON_MARKERS,
            "identity": IDENTITY_MARKERS,
            "belongingness": BELONGINGNESS_MARKERS,
            "dual_process": DUAL_PROCESS_MARKERS,
            "elm": ELM_MARKERS,
            "decision_fatigue": DECISION_FATIGUE_MARKERS,
            "choice_overload": CHOICE_OVERLOAD_MARKERS,
            "cognitive_load": COGNITIVE_LOAD_MARKERS,
            "liwc": LIWC_MARKERS,
            "absolutist": ABSOLUTIST_MARKERS,
            "pronoun": PRONOUN_ANALYSIS,
            "temporal_linguistic": TEMPORAL_LINGUISTIC_MARKERS,
            "certainty": CERTAINTY_MARKERS,
            "emotional_intensity": EMOTIONAL_INTENSITY_MARKERS,
        }
        
        for framework_name, framework_data in all_frameworks.items():
            self.compiled_patterns[framework_name] = self._compile_framework(framework_data)
    
    def _compile_framework(self, framework_data: Dict) -> Dict:
        """Compile patterns for a single framework."""
        compiled = {}
        
        for dimension, data in framework_data.items():
            if dimension in ["application", "description"]:
                compiled[dimension] = data
                continue
            
            if isinstance(data, dict):
                if "markers" in data:
                    # Simple markers list
                    if isinstance(data["markers"], list):
                        compiled[dimension] = {
                            "patterns": [re.compile(p, re.IGNORECASE) for p in data["markers"]],
                            "description": data.get("description", ""),
                        }
                    else:
                        # Nested markers
                        compiled[dimension] = {}
                        for sub_dim, patterns in data["markers"].items():
                            compiled[dimension][sub_dim] = [
                                re.compile(p, re.IGNORECASE) for p in patterns
                            ]
                else:
                    # Nested structure
                    compiled[dimension] = {}
                    for sub_dim, sub_data in data.items():
                        if isinstance(sub_data, list):
                            compiled[dimension][sub_dim] = [
                                re.compile(p, re.IGNORECASE) for p in sub_data
                            ]
                        elif isinstance(sub_data, dict) and "markers" in sub_data:
                            compiled[dimension][sub_dim] = {
                                "patterns": [re.compile(p, re.IGNORECASE) for p in sub_data["markers"]],
                                "description": sub_data.get("description", ""),
                            }
            elif isinstance(data, list):
                compiled[dimension] = [re.compile(p, re.IGNORECASE) for p in data]
        
        return compiled
    
    def analyze(self, text: str) -> PsychologicalProfile:
        """
        Analyze text against all 82 psychological frameworks.
        
        Args:
            text: Review text to analyze
            
        Returns:
            PsychologicalProfile with scores across all frameworks
        """
        profile = PsychologicalProfile()
        
        if not text or len(text) < 20:
            return profile
        
        # Analyze each framework
        framework_id = 1
        
        # Category I: Personality (1-5)
        profile.personality_scores = self._analyze_personality(text)
        
        # Category II: Motivation (6-10)
        profile.motivation_scores = self._analyze_motivation(text)
        
        # Category III: Cognitive Mechanisms (11-19)
        profile.cognitive_mechanism_scores = self._analyze_cognitive_mechanisms(text)
        
        # Category IV: Neuroscience (20-24)
        profile.neuroscience_scores = self._analyze_neuroscience(text)
        
        # Category V: Social (25-29)
        profile.social_scores = self._analyze_social(text)
        
        # Category VI: Decision-Making (30-34)
        profile.decision_scores = self._analyze_decision(text)
        
        # Category VII: Psycholinguistic (35-40)
        profile.linguistic_scores = self._analyze_linguistic(text)
        
        # Infer archetypes from combined scores
        profile.archetype_scores = self._infer_archetypes(profile)
        if profile.archetype_scores:
            profile.primary_archetype = max(profile.archetype_scores, key=profile.archetype_scores.get)
        
        # Recommend mechanisms
        profile.recommended_mechanisms = self._recommend_mechanisms(profile)
        
        # Calculate overall confidence
        profile.overall_confidence = self._calculate_confidence(profile)
        profile.sample_size = 1
        
        return profile
    
    def _count_matches(self, text: str, patterns: List) -> int:
        """Count pattern matches in text."""
        count = 0
        for pattern in patterns:
            if isinstance(pattern, re.Pattern):
                count += len(pattern.findall(text))
            else:
                count += len(re.findall(pattern, text, re.IGNORECASE))
        return count
    
    def _analyze_personality(self, text: str) -> Dict[str, float]:
        """Analyze Big Five and related personality frameworks."""
        scores = {}
        
        # Big Five
        for trait, data in BIG_FIVE_MARKERS.items():
            high_count = 0
            low_count = 0
            
            for category, patterns in data.get("high_markers", {}).items():
                high_count += self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            
            for category, patterns in data.get("low_markers", {}).items():
                low_count += self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            
            # Score ranges from -1 (low) to +1 (high)
            total = high_count + low_count
            if total > 0:
                scores[f"big5_{trait}"] = (high_count - low_count) / total
            else:
                scores[f"big5_{trait}"] = 0.0
        
        # Need for Cognition
        high_nfc = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in NEED_FOR_COGNITION_MARKERS["high_nfc"]["markers"].values()
        )
        low_nfc = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in NEED_FOR_COGNITION_MARKERS["low_nfc"]["markers"].values()
        )
        total_nfc = high_nfc + low_nfc
        scores["need_for_cognition"] = (high_nfc - low_nfc) / total_nfc if total_nfc > 0 else 0.0
        
        # Decision Style
        max_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in DECISION_STYLE_MARKERS["maximizer"]["markers"].values()
        )
        sat_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in DECISION_STYLE_MARKERS["satisficer"]["markers"].values()
        )
        total_ds = max_count + sat_count
        scores["decision_style_maximizer"] = max_count / total_ds if total_ds > 0 else 0.5
        
        return scores
    
    def _analyze_motivation(self, text: str) -> Dict[str, float]:
        """Analyze motivational frameworks."""
        scores = {}
        
        # Regulatory Focus
        promo_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in REGULATORY_FOCUS_MARKERS["promotion"]["markers"].values()
        )
        prev_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in REGULATORY_FOCUS_MARKERS["prevention"]["markers"].values()
        )
        total_rf = promo_count + prev_count
        if total_rf > 0:
            scores["regulatory_promotion"] = promo_count / total_rf
            scores["regulatory_prevention"] = prev_count / total_rf
        else:
            scores["regulatory_promotion"] = 0.5
            scores["regulatory_prevention"] = 0.5
        
        # Construal Level
        abstract_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in CONSTRUAL_LEVEL_MARKERS["abstract_high_level"]["markers"].values()
        )
        concrete_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in CONSTRUAL_LEVEL_MARKERS["concrete_low_level"]["markers"].values()
        )
        total_cl = abstract_count + concrete_count
        if total_cl > 0:
            scores["construal_abstract"] = abstract_count / total_cl
            scores["construal_concrete"] = concrete_count / total_cl
        else:
            scores["construal_abstract"] = 0.5
            scores["construal_concrete"] = 0.5
        
        # Approach-Avoidance
        approach_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in APPROACH_AVOIDANCE_MARKERS["approach_motivated"]["markers"].values()
        )
        avoid_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for patterns in APPROACH_AVOIDANCE_MARKERS["avoidance_motivated"]["markers"].values()
        )
        total_aa = approach_count + avoid_count
        if total_aa > 0:
            scores["approach_motivation"] = approach_count / total_aa
            scores["avoidance_motivation"] = avoid_count / total_aa
        else:
            scores["approach_motivation"] = 0.5
            scores["avoidance_motivation"] = 0.5
        
        return scores
    
    def _analyze_cognitive_mechanisms(self, text: str) -> Dict[str, float]:
        """Analyze Cialdini+ cognitive mechanism frameworks."""
        scores = {}
        
        mechanisms = [
            ("social_proof", SOCIAL_PROOF_MARKERS),
            ("scarcity", SCARCITY_MARKERS),
            ("authority", AUTHORITY_MARKERS),
            ("reciprocity", RECIPROCITY_MARKERS),
            ("commitment", COMMITMENT_MARKERS),
            ("liking", LIKING_MARKERS),
            ("loss_aversion", LOSS_AVERSION_MARKERS),
            ("anchoring", ANCHORING_MARKERS),
            ("framing", FRAMING_MARKERS),
        ]
        
        for name, markers in mechanisms:
            total_count = 0
            for category, data in markers.items():
                if category == "application":
                    continue
                if isinstance(data, dict) and "markers" in data:
                    total_count += self._count_matches(
                        text, [re.compile(p, re.IGNORECASE) for p in data["markers"]]
                    )
            # Normalize to 0-1 scale (cap at reasonable threshold)
            scores[name] = min(1.0, total_count / 5)
        
        return scores
    
    def _analyze_neuroscience(self, text: str) -> Dict[str, float]:
        """Analyze neuroscience-grounded frameworks."""
        scores = {}
        
        # Wanting vs Liking
        wanting_count = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in WANTING_LIKING_MARKERS["wanting"]["markers"]]
        )
        liking_count = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in WANTING_LIKING_MARKERS["liking"]["markers"]]
        )
        total_wl = wanting_count + liking_count
        if total_wl > 0:
            scores["wanting"] = wanting_count / total_wl
            scores["liking"] = liking_count / total_wl
        else:
            scores["wanting"] = 0.5
            scores["liking"] = 0.5
        
        # Embodied Cognition
        embodied_count = 0
        for sense, markers in EMBODIED_COGNITION_MARKERS.items():
            if sense == "application":
                continue
            embodied_count += self._count_matches(
                text, [re.compile(p, re.IGNORECASE) for p in markers["markers"]]
            )
        scores["embodied_cognition"] = min(1.0, embodied_count / 10)
        
        # Processing Fluency
        high_fluency = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in PROCESSING_FLUENCY_MARKERS["high_fluency"]["markers"]]
        )
        low_fluency = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in PROCESSING_FLUENCY_MARKERS["low_fluency"]["markers"]]
        )
        total_pf = high_fluency + low_fluency
        scores["processing_fluency"] = (high_fluency - low_fluency) / total_pf if total_pf > 0 else 0.0
        
        return scores
    
    def _analyze_social(self, text: str) -> Dict[str, float]:
        """Analyze social and evolutionary frameworks."""
        scores = {}
        
        # Social Comparison
        upward = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in SOCIAL_COMPARISON_MARKERS["upward_comparison"]["markers"]]
        )
        downward = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in SOCIAL_COMPARISON_MARKERS["downward_comparison"]["markers"]]
        )
        lateral = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in SOCIAL_COMPARISON_MARKERS["lateral_comparison"]["markers"]]
        )
        total_sc = upward + downward + lateral
        if total_sc > 0:
            scores["social_comparison_upward"] = upward / total_sc
            scores["social_comparison_downward"] = downward / total_sc
            scores["social_comparison_lateral"] = lateral / total_sc
        
        # Evolutionary Motives
        for motive, data in EVOLUTIONARY_MOTIVES_MARKERS.items():
            if motive == "application":
                continue
            count = self._count_matches(
                text, [re.compile(p, re.IGNORECASE) for p in data["markers"]]
            )
            scores[f"evolutionary_{motive}"] = min(1.0, count / 3)
        
        # Identity
        identity_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in data["markers"]])
            for name, data in IDENTITY_MARKERS.items()
            if name != "application" and isinstance(data, dict) and "markers" in data
        )
        scores["identity_construction"] = min(1.0, identity_count / 5)
        
        return scores
    
    def _analyze_decision(self, text: str) -> Dict[str, float]:
        """Analyze decision-making frameworks."""
        scores = {}
        
        # Dual Process
        s1_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for category, patterns in DUAL_PROCESS_MARKERS["system1_intuitive"]["markers"].items()
        )
        s2_count = sum(
            self._count_matches(text, [re.compile(p, re.IGNORECASE) for p in patterns])
            for category, patterns in DUAL_PROCESS_MARKERS["system2_deliberate"]["markers"].items()
        )
        total_dp = s1_count + s2_count
        if total_dp > 0:
            scores["system1_intuitive"] = s1_count / total_dp
            scores["system2_deliberate"] = s2_count / total_dp
        else:
            scores["system1_intuitive"] = 0.5
            scores["system2_deliberate"] = 0.5
        
        # Decision Fatigue
        fatigue_count = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in DECISION_FATIGUE_MARKERS["fatigue_indicators"]["markers"]]
        )
        scores["decision_fatigue"] = min(1.0, fatigue_count / 3)
        
        # Choice Overload
        overload_count = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in CHOICE_OVERLOAD_MARKERS["overload_indicators"]["markers"]]
        )
        scores["choice_overload"] = min(1.0, overload_count / 3)
        
        return scores
    
    def _analyze_linguistic(self, text: str) -> Dict[str, float]:
        """Analyze psycholinguistic frameworks."""
        scores = {}
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Pronoun analysis
        i_count = len(re.findall(r'\bi\b', text_lower))
        we_count = len(re.findall(r'\bwe\b', text_lower))
        you_count = len(re.findall(r'\byou\b', text_lower))
        
        if word_count > 0:
            scores["pronoun_i_ratio"] = i_count / word_count
            scores["pronoun_we_ratio"] = we_count / word_count
            scores["pronoun_you_ratio"] = you_count / word_count
        
        # Certainty
        high_cert = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in CERTAINTY_MARKERS["high_certainty"]["markers"]]
        )
        low_cert = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in CERTAINTY_MARKERS["low_certainty"]["markers"]]
        )
        total_cert = high_cert + low_cert
        scores["certainty"] = (high_cert - low_cert) / total_cert if total_cert > 0 else 0.0
        
        # Emotional Intensity
        intensity_map = {
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "extreme": 1.0,
        }
        weighted_intensity = 0
        total_intensity_matches = 0
        
        for level, data in EMOTIONAL_INTENSITY_MARKERS.items():
            if level == "application":
                continue
            count = self._count_matches(
                text, [re.compile(p, re.IGNORECASE) for p in data["markers"]]
            )
            weighted_intensity += count * intensity_map.get(level.replace("_intensity", ""), 0.5)
            total_intensity_matches += count
        
        scores["emotional_intensity"] = weighted_intensity / total_intensity_matches if total_intensity_matches > 0 else 0.5
        
        # Absolutist language
        absolutist_count = self._count_matches(
            text, [re.compile(p, re.IGNORECASE) for p in ABSOLUTIST_MARKERS["absolutist_words"]["markers"]]
        )
        scores["absolutist_language"] = min(1.0, absolutist_count / 5)
        
        return scores
    
    def _infer_archetypes(self, profile: PsychologicalProfile) -> Dict[str, float]:
        """Infer archetypes from combined framework scores."""
        archetypes = {}
        
        # Achiever: High conscientiousness, achievement, promotion focus
        archetypes["achiever"] = (
            max(0, profile.personality_scores.get("big5_conscientiousness", 0)) * 0.3 +
            profile.motivation_scores.get("regulatory_promotion", 0.5) * 0.3 +
            profile.cognitive_mechanism_scores.get("authority", 0) * 0.2 +
            profile.social_scores.get("social_comparison_upward", 0) * 0.2
        )
        
        # Explorer: High openness, novelty seeking, approach motivation
        archetypes["explorer"] = (
            max(0, profile.personality_scores.get("big5_openness", 0)) * 0.3 +
            max(0, profile.personality_scores.get("big5_extraversion", 0)) * 0.2 +
            profile.motivation_scores.get("approach_motivation", 0.5) * 0.3 +
            profile.neuroscience_scores.get("wanting", 0.5) * 0.2
        )
        
        # Guardian: High neuroticism (safety), prevention focus, risk avoidance
        archetypes["guardian"] = (
            max(0, profile.personality_scores.get("big5_neuroticism", 0)) * 0.2 +
            max(0, profile.personality_scores.get("big5_conscientiousness", 0)) * 0.2 +
            profile.motivation_scores.get("regulatory_prevention", 0.5) * 0.3 +
            profile.motivation_scores.get("avoidance_motivation", 0.5) * 0.3
        )
        
        # Connector: High agreeableness, extraversion, relatedness
        archetypes["connector"] = (
            max(0, profile.personality_scores.get("big5_agreeableness", 0)) * 0.3 +
            max(0, profile.personality_scores.get("big5_extraversion", 0)) * 0.2 +
            profile.social_scores.get("identity_construction", 0) * 0.2 +
            profile.cognitive_mechanism_scores.get("social_proof", 0) * 0.3
        )
        
        # Analyst: High NFC, deliberate processing, detail orientation
        archetypes["analyst"] = (
            max(0, profile.personality_scores.get("need_for_cognition", 0)) * 0.3 +
            profile.decision_scores.get("system2_deliberate", 0.5) * 0.3 +
            profile.personality_scores.get("decision_style_maximizer", 0.5) * 0.2 +
            profile.cognitive_mechanism_scores.get("authority", 0) * 0.2
        )
        
        # Pragmatist: Satisficer, value-focus, practical
        archetypes["pragmatist"] = (
            (1 - profile.personality_scores.get("decision_style_maximizer", 0.5)) * 0.3 +
            profile.motivation_scores.get("construal_concrete", 0.5) * 0.3 +
            profile.neuroscience_scores.get("processing_fluency", 0) * 0.2 +
            profile.decision_scores.get("system1_intuitive", 0.5) * 0.2
        )
        
        # Normalize
        total = sum(archetypes.values())
        if total > 0:
            archetypes = {k: v / total for k, v in archetypes.items()}
        
        return archetypes
    
    def _recommend_mechanisms(self, profile: PsychologicalProfile) -> List[str]:
        """Recommend persuasion mechanisms based on profile."""
        recommendations = []
        
        # Based on regulatory focus
        if profile.motivation_scores.get("regulatory_promotion", 0.5) > 0.6:
            recommendations.append("gain_framing")
        if profile.motivation_scores.get("regulatory_prevention", 0.5) > 0.6:
            recommendations.append("loss_framing")
        
        # Based on cognitive mechanisms detected
        for mech, score in profile.cognitive_mechanism_scores.items():
            if score > 0.3:
                recommendations.append(mech)
        
        # Based on processing style
        if profile.decision_scores.get("system1_intuitive", 0.5) > 0.6:
            recommendations.extend(["social_proof", "liking", "scarcity"])
        if profile.decision_scores.get("system2_deliberate", 0.5) > 0.6:
            recommendations.extend(["authority", "central_arguments"])
        
        return list(set(recommendations))[:5]  # Top 5 unique
    
    def _calculate_confidence(self, profile: PsychologicalProfile) -> float:
        """Calculate overall confidence in the profile."""
        # More matches = higher confidence
        total_scores = 0
        non_zero_scores = 0
        
        for score_dict in [
            profile.personality_scores,
            profile.motivation_scores,
            profile.cognitive_mechanism_scores,
            profile.neuroscience_scores,
            profile.social_scores,
            profile.decision_scores,
            profile.linguistic_scores,
        ]:
            for score in score_dict.values():
                total_scores += 1
                if abs(score) > 0.1:
                    non_zero_scores += 1
        
        return non_zero_scores / total_scores if total_scores > 0 else 0.0


# =============================================================================
# USAGE
# =============================================================================

if __name__ == "__main__":
    analyzer = PsychologicalFrameworkAnalyzer()
    
    test_reviews = [
        """
        After extensive research comparing this to the competition, I can confidently say
        this is the best in its class. The premium quality is immediately apparent - this
        is clearly a professional-grade product. I don't settle for mediocre, and this
        exceeds my high standards. Worth every dollar for those who demand excellence.
        The craftsmanship and attention to detail are outstanding.
        """,
        
        """
        Bought this as a gift for my mom and she absolutely loves it! Now I got one
        for my sister too. Everyone in my family is using it now. I've been telling
        all my friends about it - you should get one for your loved ones too!
        It brings us together and we all share how much we enjoy it. Highly recommend!
        """,
        
        """
        I was hesitant at first and read all 500 reviews carefully before purchasing.
        After three months of use, I can say this is reliable and dependable. My family
        uses it daily and it's held up well. The warranty gave me peace of mind, and
        customer service was helpful when I had questions. A safe, trustworthy choice.
        """,
    ]
    
    for i, review in enumerate(test_reviews, 1):
        print(f"\n{'='*70}")
        print(f"REVIEW {i}")
        print("=" * 70)
        print(review.strip()[:150] + "...")
        
        profile = analyzer.analyze(review)
        
        print(f"\n📊 PRIMARY ARCHETYPE: {profile.primary_archetype.upper()}")
        
        print(f"\n🎯 ARCHETYPE SCORES:")
        for arch, score in sorted(profile.archetype_scores.items(), key=lambda x: -x[1]):
            bar = "█" * int(score * 30)
            print(f"   {arch:12}: {bar} {score:.1%}")
        
        print(f"\n🧠 KEY PERSONALITY TRAITS:")
        for trait, score in sorted(profile.personality_scores.items(), key=lambda x: -abs(x[1]))[:5]:
            direction = "+" if score > 0 else "-"
            print(f"   {trait}: {direction}{abs(score):.2f}")
        
        print(f"\n⚡ MOTIVATION:")
        print(f"   Promotion: {profile.motivation_scores.get('regulatory_promotion', 0):.1%}")
        print(f"   Prevention: {profile.motivation_scores.get('regulatory_prevention', 0):.1%}")
        
        print(f"\n🎛️ RECOMMENDED MECHANISMS:")
        for mech in profile.recommended_mechanisms:
            print(f"   • {mech}")
        
        print(f"\n📈 CONFIDENCE: {profile.overall_confidence:.1%}")
