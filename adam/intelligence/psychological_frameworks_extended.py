#!/usr/bin/env python3
"""
ADAM PSYCHOLOGICAL FRAMEWORKS - EXTENDED
=========================================

Frameworks 41-82: Temporal/State, Behavioral, Brand, Moral, Memory, 
Narrative, Trust, Price, Mechanism Interaction, Context, Cultural, 
Ethical Guardrails, and Advanced Inference.

This completes the 82-framework psychological intelligence system.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# CATEGORY VIII: TEMPORAL & STATE FRAMEWORKS (Frameworks 41-45)
# =============================================================================

# Framework 41: State × Trait Interaction
# Stable traits modulated by momentary states
STATE_TRAIT_INTERACTION_MARKERS = {
    "stable_trait_expressions": {
        "description": "Consistent personality patterns across situations",
        "markers": [
            r"\balways\b", r"\busually\b", r"\btypically\b",
            r"\bgenerally\b", r"\bnormally\b", r"\btend to\b",
            r"\bI'm (the type|someone) who\b", r"\bI (always|usually|typically)\b",
        ],
    },
    "state_modulated": {
        "description": "Temporary state affecting typical behavior",
        "markers": [
            r"\btoday\b", r"\bright now\b", r"\bat the moment\b",
            r"\bfor once\b", r"\bunusually\b", r"\buncharacteristically\b",
            r"\bin (this|that) (moment|situation)\b",
            r"\bwasn't (my usual|like me)\b",
        ],
    },
    "mood_state": {
        "description": "Current emotional state",
        "markers": [
            r"\bfeeling (happy|sad|anxious|excited|tired|stressed)\b",
            r"\bin a (good|bad|great|terrible) mood\b",
            r"\bhaving a (good|bad|rough|great) day\b",
        ],
    },
    "application": "Same person responds differently based on momentary state"
}


# Framework 42: Arousal Modulation
# Physiological activation level affects decision-making
AROUSAL_MODULATION_MARKERS = {
    "high_arousal": {
        "description": "Elevated physiological activation → prevention bias",
        "markers": [
            r"\bexcit\w*\b", r"\bthrill\w*\b", r"\brush\w*\b",
            r"\badrenaline\b", r"\bheart (racing|pounding)\b",
            r"\bcouldn't (wait|contain|help)\b", r"\bbuzzing\b",
            r"\bon edge\b", r"\bwired\b", r"\bjittery\b",
            r"\banxious\b", r"\bnervous\b", r"\bstress\w*\b",
        ],
    },
    "low_arousal": {
        "description": "Calm state → promotion focus enabled",
        "markers": [
            r"\bcalm\b", r"\brelax\w*\b", r"\bpeaceful\b",
            r"\bserene\b", r"\btranquil\b", r"\bzen\b",
            r"\bchill\w*\b", r"\blaid.?back\b", r"\beasy.?going\b",
            r"\bno (rush|hurry|pressure)\b", r"\btook my time\b",
        ],
    },
    "optimal_arousal": {
        "description": "Moderate activation for best decisions",
        "markers": [
            r"\bfocused\b", r"\bengaged\b", r"\battentive\b",
            r"\balert\b", r"\bsharp\b", r"\bin the zone\b",
        ],
    },
    "application": "High arousal → prevention bias; Low arousal → promotion enabled"
}


# Framework 43: Circadian Pattern Analysis
# Time-of-day psychological variation
CIRCADIAN_MARKERS = {
    "morning_state": {
        "description": "Morning cognitive patterns",
        "markers": [
            r"\bmorning\b", r"\bearly\b", r"\bfirst thing\b",
            r"\bstart(ed)? (my|the) day\b", r"\bwoke up\b",
            r"\bbreakfast\b", r"\bcoffee\b", r"\bam\b",
        ],
    },
    "afternoon_state": {
        "description": "Afternoon patterns - often post-lunch dip",
        "markers": [
            r"\bafternoon\b", r"\blunch\b", r"\bmidday\b",
            r"\bafter lunch\b", r"\bpm\b", r"\bmid.?day\b",
        ],
    },
    "evening_state": {
        "description": "Evening patterns - often tired, impulsive",
        "markers": [
            r"\bevening\b", r"\bnight\b", r"\blate\b",
            r"\bafter (work|dinner)\b", r"\bbefore bed\b",
            r"\btired\b", r"\bexhaust\w*\b", r"\blong day\b",
        ],
    },
    "weekend_state": {
        "description": "Weekend/leisure state",
        "markers": [
            r"\bweekend\b", r"\bsaturday\b", r"\bsunday\b",
            r"\bday off\b", r"\bfree time\b", r"\bleisure\b",
        ],
    },
    "application": "Peak receptivity windows vary by user chronotype"
}


# Framework 44: Journey Stage Detection
# Awareness → Consideration → Decision → Experience → Advocacy
JOURNEY_STAGE_MARKERS = {
    "awareness": {
        "description": "Just discovered, initial interest",
        "markers": [
            r"\bjust (heard|learned|discovered|found)\b",
            r"\bnew to (me|this)\b", r"\bfirst time (seeing|hearing)\b",
            r"\bdidn't know (about|this existed)\b",
            r"\bwhat is\b", r"\bwhat's\b", r"\bcurious about\b",
        ],
    },
    "consideration": {
        "description": "Actively evaluating options",
        "markers": [
            r"\bcomparing\b", r"\bresearching\b", r"\bevaluating\b",
            r"\bconsidering\b", r"\bthinking about\b", r"\blooking (at|into)\b",
            r"\boptions?\b", r"\balternatives?\b", r"\bchoices?\b",
            r"\bvs\.?\b", r"\bversus\b", r"\bor\b.+\binstead\b",
        ],
    },
    "decision": {
        "description": "Making purchase decision",
        "markers": [
            r"\b(finally )?(decided|chose|picked|went with)\b",
            r"\bpulled the trigger\b", r"\btook the plunge\b",
            r"\bbought\b", r"\bpurchased\b", r"\bordered\b",
            r"\bready to (buy|order|commit)\b",
        ],
    },
    "experience": {
        "description": "Using/experiencing the product",
        "markers": [
            r"\bbeen using\b", r"\bafter \d+ (days|weeks|months)\b",
            r"\bso far\b", r"\bin my experience\b",
            r"\bworks (great|well|fine)\b", r"\bhas been\b",
        ],
    },
    "advocacy": {
        "description": "Recommending to others",
        "markers": [
            r"\brecommend\w*\b", r"\btell (everyone|friends|family)\b",
            r"\bspread the word\b", r"\bconvert\w*\b",
            r"\bget (one|this|it) for\b", r"\byou (should|need|must)\b",
        ],
    },
    "application": "Match persuasion mechanism to funnel position"
}


# Framework 45: Temporal Construal
# Future self vs. present self identity
TEMPORAL_CONSTRUAL_MARKERS = {
    "future_self": {
        "description": "Projecting identity into future",
        "markers": [
            r"\bwill (be|become|have)\b", r"\bgoing to (be|become)\b",
            r"\bfuture (me|self)\b", r"\bsomeday\b", r"\beventually\b",
            r"\blong.?term\b", r"\binvest\w* in (my|the) future\b",
            r"\bfor years to come\b", r"\bwhen I (retire|graduate|move)\b",
        ],
    },
    "present_self": {
        "description": "Grounded in present identity",
        "markers": [
            r"\bright now\b", r"\bcurrently\b", r"\bat the moment\b",
            r"\btoday\b", r"\bthis (week|month|year)\b",
            r"\bimmediately\b", r"\binstantly\b", r"\bnow\b",
        ],
    },
    "identity_continuity": {
        "description": "Connection between present and future self",
        "markers": [
            r"\balways (wanted|dreamed)\b", r"\bfinally\b",
            r"\blife.?long\b", r"\bsince (childhood|I was young)\b",
            r"\bbucket list\b", r"\bdream (come true|realized)\b",
        ],
    },
    "application": "Future-self appeals for investment; Present-self for immediate gratification"
}


# =============================================================================
# CATEGORY IX: BEHAVIORAL SIGNAL FRAMEWORKS (Frameworks 46-50)
# =============================================================================

# Framework 46: Micro-Temporal Pattern Analysis
# Keystroke dynamics, scroll velocity, dwell time indicators in review text
MICRO_TEMPORAL_MARKERS = {
    "quick_decision": {
        "description": "Fast, confident decision language",
        "markers": [
            r"\bimmediately\b", r"\binstantly\b", r"\bright away\b",
            r"\bno hesitation\b", r"\bdidn't (think twice|hesitate)\b",
            r"\bquick (decision|purchase|buy)\b", r"\bimpuls\w*\b",
        ],
    },
    "deliberate_decision": {
        "description": "Slow, careful decision language",
        "markers": [
            r"\btook (my|a lot of) time\b", r"\bcarefully (considered|researched)\b",
            r"\bspent (hours|days|weeks|months)\b", r"\bdidn't rush\b",
            r"\bsleep on it\b", r"\bthought (about|through)\b",
        ],
    },
    "confidence_indicators": {
        "description": "Certainty in decision",
        "markers": [
            r"\bdefinitely\b", r"\babsolutely\b", r"\b100%\b",
            r"\bno (doubt|question|regrets)\b", r"\bcertain\b",
            r"\bconfident\b", r"\bsure\b",
        ],
    },
    "uncertainty_indicators": {
        "description": "Doubt in decision",
        "markers": [
            r"\bnot sure\b", r"\bmaybe\b", r"\bperhaps\b",
            r"\bwe'll see\b", r"\bhope(fully)?\b", r"\bfingers crossed\b",
            r"\btime will tell\b", r"\bstill (deciding|unsure)\b",
        ],
    },
    "application": "Sub-second timing reveals arousal, confidence, approach tendency"
}


# Framework 47: Cross-Category Behavior
# What else these customers buy reveals deeper psychology
CROSS_CATEGORY_MARKERS = {
    "multi_category_mentions": {
        "description": "References to purchases in other categories",
        "markers": [
            r"\balso (bought|got|ordered|have)\b",
            r"\bpairs? (well|nicely|great) with\b",
            r"\bmatches? (my|the)\b", r"\bgoes with\b",
            r"\bto (go|match|complement) with\b",
            r"\balong with\b", r"\btogether with\b",
        ],
    },
    "brand_loyalty_signals": {
        "description": "Mentions of brand relationships",
        "markers": [
            r"\b(big|huge|loyal) fan of (this|the) brand\b",
            r"\beverything from (this|the) brand\b",
            r"\ball (my|our) \w+ are from\b",
            r"\bstick with\b", r"\balways (buy|use|choose) this brand\b",
        ],
    },
    "lifestyle_indicators": {
        "description": "Lifestyle category mentions",
        "markers": [
            r"\bfor (my|the) (gym|office|travel|home|kitchen)\b",
            r"\bfitness\b", r"\boutdoor\w*\b", r"\btravel\w*\b",
            r"\bwork from home\b", r"\bremote work\b",
        ],
    },
    "application": "Transfer learning and expanded targeting based on co-purchase patterns"
}


# Framework 48: Content Consumption Patterns
# Engagement depth indicators in review text
CONTENT_CONSUMPTION_MARKERS = {
    "high_engagement": {
        "description": "Deep engagement with product/content",
        "markers": [
            r"\bread (all|every|the entire|the whole)\b",
            r"\bstudied\b", r"\bresearched (extensively|thoroughly)\b",
            r"\bcompared (many|several|all)\b",
            r"\bwatched (all|every|many) (videos?|reviews?)\b",
            r"\bspent (hours|days) (reading|researching|learning)\b",
        ],
    },
    "surface_engagement": {
        "description": "Quick, surface-level engagement",
        "markers": [
            r"\bglanced\b", r"\bskimmed\b", r"\bquick look\b",
            r"\bdidn't (read|look at) (all|every)\b",
            r"\bjust (bought|ordered|got) it\b",
        ],
    },
    "return_visitor": {
        "description": "Multiple visits before decision",
        "markers": [
            r"\bcame back\b", r"\breturned (to|several times)\b",
            r"\bkept (looking|coming back|thinking)\b",
            r"\bfinally (bought|decided|ordered)\b",
            r"\bafter (thinking|considering|waiting)\b",
        ],
    },
    "application": "Engagement depth predicts involvement level and route to persuasion"
}


# Framework 49: Physiological State Proxies
# Behavioral patterns inferring arousal/fatigue
PHYSIOLOGICAL_PROXY_MARKERS = {
    "fatigue_indicators": {
        "description": "Tired state from language",
        "markers": [
            r"\btired\b", r"\bexhaust\w*\b", r"\bworn out\b",
            r"\blong day\b", r"\bafter (work|a long)\b",
            r"\bburnt? out\b", r"\bdrained\b", r"\bwiped\b",
        ],
    },
    "energized_indicators": {
        "description": "High energy state",
        "markers": [
            r"\benerg\w*\b", r"\bpumped\b", r"\bexcit\w*\b",
            r"\bready to\b", r"\bcan't wait\b", r"\beager\b",
            r"\bmotivat\w*\b", r"\binspir\w*\b",
        ],
    },
    "stress_indicators": {
        "description": "Stress state",
        "markers": [
            r"\bstress\w*\b", r"\boverwhelm\w*\b", r"\banxious\b",
            r"\bpressure\b", r"\bdeadline\b", r"\bcrunch\b",
            r"\brushed\b", r"\bpanic\w*\b",
        ],
    },
    "relaxed_indicators": {
        "description": "Relaxed state",
        "markers": [
            r"\brelax\w*\b", r"\bcalm\b", r"\bpeaceful\b",
            r"\bno (rush|pressure|stress)\b", r"\btook my time\b",
            r"\bleisurely\b", r"\bunhurried\b",
        ],
    },
    "application": "Indirect physiological state measurement affects receptivity"
}


# Framework 50: Interaction Sequencing
# Order and timing of behavioral events
INTERACTION_SEQUENCING_MARKERS = {
    "research_then_buy": {
        "description": "Research-first pattern",
        "markers": [
            r"\bafter (researching|reading|comparing)\b.+\b(bought|ordered)\b",
            r"\bresearched\b.+\bthen (bought|ordered|decided)\b",
            r"\bfirst\b.+\bcompared\b.+\bthen\b",
        ],
    },
    "impulse_then_validate": {
        "description": "Buy-first, rationalize later",
        "markers": [
            r"\bbought (it )?(first|immediately)\b.+\bthen (read|looked)\b",
            r"\bimpulse\b.+\bbut\b.+\bturned out\b",
            r"\bdidn't (research|read)\b.+\bbefore\b",
        ],
    },
    "trial_then_commit": {
        "description": "Try before full commitment",
        "markers": [
            r"\btried (first|it out|a sample)\b.+\bthen (bought|ordered|committed)\b",
            r"\bsample\b.+\b(full|regular) (size|version|order)\b",
            r"\bstarted with\b.+\bthen (upgraded|got more)\b",
        ],
    },
    "application": "Sequence patterns reveal decision confidence and deliberation style"
}


# =============================================================================
# CATEGORY X: BRAND-CONSUMER MATCHING (Frameworks 51-53)
# =============================================================================

# Framework 51: Brand Personality Theory (Aaker)
# Sincerity, Excitement, Competence, Sophistication, Ruggedness
BRAND_PERSONALITY_MARKERS = {
    "sincerity": {
        "description": "Down-to-earth, honest, wholesome, cheerful",
        "markers": [
            r"\bhonest\b", r"\bgenuine\b", r"\bauthentic\b",
            r"\bwholesome\b", r"\bdown.?to.?earth\b", r"\bfriendly\b",
            r"\bwarm\b", r"\bcaring\b", r"\bfamily\b", r"\bhome\w*\b",
            r"\btrust\w*\b", r"\breliable\b", r"\bdependable\b",
        ],
    },
    "excitement": {
        "description": "Daring, spirited, imaginative, up-to-date",
        "markers": [
            r"\bexcit\w*\b", r"\bdaring\b", r"\bbold\b", r"\btrendy\b",
            r"\bcool\b", r"\bspirite\w*\b", r"\byoung\b", r"\bfresh\b",
            r"\binnovativ\w*\b", r"\bcutting.?edge\b", r"\bmodern\b",
            r"\bdynamic\b", r"\bener\w*\b",
        ],
    },
    "competence": {
        "description": "Reliable, intelligent, successful",
        "markers": [
            r"\breliable\b", r"\bintelligent\b", r"\bsmart\b",
            r"\bsuccessful\b", r"\bleader\w*\b", r"\bconfident\b",
            r"\bprofessional\b", r"\bcompetent\b", r"\bexpert\w*\b",
            r"\befficient\b", r"\beffective\b", r"\bquality\b",
        ],
    },
    "sophistication": {
        "description": "Upper class, charming, glamorous",
        "markers": [
            r"\belegant\b", r"\bsophisticat\w*\b", r"\brefined\b",
            r"\bluxur\w*\b", r"\bglamour\w*\b", r"\bprestig\w*\b",
            r"\bexclusive\b", r"\bpremium\b", r"\bhigh.?end\b",
            r"\bstylish\b", r"\bchic\b", r"\bclassy\b",
        ],
    },
    "ruggedness": {
        "description": "Outdoorsy, tough, strong",
        "markers": [
            r"\brugged\b", r"\btough\b", r"\bstrong\b", r"\bdurable\b",
            r"\boutdoor\w*\b", r"\badventur\w*\b", r"\brugged\b",
            r"\bmasculine\b", r"\brobust\b", r"\bsolid\b",
            r"\bbuilt to last\b", r"\bworkhorse\b", r"\bbeast\b",
        ],
    },
    "application": "Match brand personality to consumer personality for congruity"
}


# Framework 52: Brand-Self Congruity
# Match between brand image and self-concept
BRAND_SELF_CONGRUITY_MARKERS = {
    "actual_self_match": {
        "description": "Brand matches who I am",
        "markers": [
            r"\b(fits?|matches?) (who I am|my personality|me)\b",
            r"\bperfect for (me|someone like me)\b",
            r"\breflects (who I am|my)\b", r"\brepresents me\b",
            r"\bso me\b", r"\btotally me\b", r"\bmy (style|type)\b",
        ],
    },
    "ideal_self_match": {
        "description": "Brand matches who I want to be",
        "markers": [
            r"\bwho I want to (be|become)\b", r"\baspire\w*\b",
            r"\bmakes me feel (like|more)\b", r"\belevat\w*\b",
            r"\bupgrade\w*\b", r"\bnext level\b", r"\bbetter version\b",
        ],
    },
    "social_self_match": {
        "description": "Brand matches how I want others to see me",
        "markers": [
            r"\b(people|others|they) (see|think|perceive)\b",
            r"\bimpression\b", r"\bimage\b", r"\blook\w* (good|professional|stylish)\b",
            r"\bcompliment\w*\b", r"\bnotice\w*\b",
        ],
    },
    "mismatch_indicators": {
        "description": "Brand-self incongruity",
        "markers": [
            r"\bnot (me|my style|my type)\b", r"\bdoesn't (fit|match|suit)\b",
            r"\btoo (fancy|casual|young|old) for me\b",
            r"\bnot (who I am|my thing)\b",
        ],
    },
    "application": "Conversion lifts when brand 'fits' psychological profile"
}


# Framework 53: Psychological Ownership
# "This is mine" pre-purchase feeling
PSYCHOLOGICAL_OWNERSHIP_MARKERS = {
    "ownership_language": {
        "description": "Pre-purchase ownership feelings",
        "markers": [
            r"\bmy (new|future)\b", r"\bmine\b", r"\bgonna be mine\b",
            r"\balready (feels?|felt) like mine\b",
            r"\bcouldn't (wait|imagine|picture) (without|myself)\b",
            r"\bhad to have (it|this)\b", r"\bbelongs? (to|with) me\b",
        ],
    },
    "investment_language": {
        "description": "Time/effort invested creates ownership",
        "markers": [
            r"\bspent (time|hours|effort)\b.+\b(researching|customizing|configuring)\b",
            r"\bpersonaliz\w*\b", r"\bcustom\w*\b",
            r"\bbuilt\b.+\bmy (own|way)\b",
            r"\bchose (every|each|all)\b",
        ],
    },
    "attachment_language": {
        "description": "Emotional attachment to product",
        "markers": [
            r"\battach\w* to\b", r"\bcan't (part|live) (with|without)\b",
            r"\blove (this|it|my)\b", r"\btreasure\w*\b",
            r"\bsentimental\b", r"\bmeans? (a lot|so much)\b",
        ],
    },
    "application": "Language like 'my future car' predicts conversion"
}


# =============================================================================
# CATEGORY XI: MORAL & VALUES FRAMEWORKS (Frameworks 54-55)
# =============================================================================

# Framework 54: Moral Foundations Theory (Haidt)
# Care/Harm, Fairness, Loyalty, Authority, Purity, Liberty
MORAL_FOUNDATIONS_MARKERS = {
    "care_harm": {
        "description": "Concern for suffering and wellbeing",
        "markers": [
            r"\bcare\w*\b", r"\bcompassion\w*\b", r"\bkind\w*\b",
            r"\bgentle\b", r"\bprotect\w*\b", r"\bsafe\w*\b",
            r"\bharm\w*\b", r"\bhurt\w*\b", r"\bcruel\w*\b",
            r"\bsuffer\w*\b", r"\bpain\b", r"\bvulnerabl\w*\b",
        ],
    },
    "fairness_cheating": {
        "description": "Justice, rights, reciprocity",
        "markers": [
            r"\bfair\w*\b", r"\bjust(ice)?\b", r"\bequal\w*\b",
            r"\bright\w*\b", r"\bhonest\w*\b", r"\bdeserv\w*\b",
            r"\bcheat\w*\b", r"\bfraud\w*\b", r"\bscam\w*\b",
            r"\brip.?off\b", r"\bunfair\b", r"\bbiased\b",
        ],
    },
    "loyalty_betrayal": {
        "description": "Group loyalty, patriotism",
        "markers": [
            r"\bloyal\w*\b", r"\bfaithful\b", r"\bpatrioti\w*\b",
            r"\bteam\b", r"\bfamily\b", r"\bcommunity\b",
            r"\bbetray\w*\b", r"\btrait\w*\b", r"\bdisloyal\b",
            r"\bbackstab\w*\b",
        ],
    },
    "authority_subversion": {
        "description": "Respect for tradition, hierarchy",
        "markers": [
            r"\brespect\w*\b", r"\bhonor\w*\b", r"\btradition\w*\b",
            r"\bauthority\b", r"\bduty\b", r"\bobedien\w*\b",
            r"\bdisrespect\w*\b", r"\brebel\w*\b", r"\bdefian\w*\b",
        ],
    },
    "purity_degradation": {
        "description": "Cleanliness, sanctity, disgust",
        "markers": [
            r"\bpure\b", r"\bclean\w*\b", r"\bnatural\b",
            r"\borganic\b", r"\bwholesome\b", r"\bsacred\b",
            r"\bdisgust\w*\b", r"\bgross\b", r"\bcontaminat\w*\b",
            r"\btoxic\b", r"\bdirty\b", r"\bfilthy\b",
        ],
    },
    "liberty_oppression": {
        "description": "Freedom from tyranny, autonomy",
        "markers": [
            r"\bfreedom\b", r"\blibert\w*\b", r"\bindependen\w*\b",
            r"\bautonom\w*\b", r"\bchoice\b", r"\bright to\b",
            r"\boppress\w*\b", r"\btyrann\w*\b", r"\bcontrol\w*\b",
            r"\bforced\b", r"\bcoerced\b",
        ],
    },
    "application": "Different moral foundations respond to different appeals"
}


# Framework 55: Schwartz Values Framework (Expanded)
# 10 value types with detailed markers
SCHWARTZ_VALUES_EXPANDED = {
    "self_direction": {
        "description": "Independence of thought and action",
        "markers": [
            r"\bindependen\w*\b", r"\bfreedom\b", r"\bcreativ\w*\b",
            r"\bcurious\b", r"\bchoos\w*\b", r"\bmy (own )?way\b",
            r"\boriginal\b", r"\bunique\b", r"\bexplor\w*\b",
        ],
        "opposite": "conformity",
    },
    "stimulation": {
        "description": "Excitement, novelty, challenge",
        "markers": [
            r"\bexcit\w*\b", r"\bnew\b", r"\bnovel\w*\b",
            r"\bchalleng\w*\b", r"\badventur\w*\b", r"\bdaring\b",
            r"\bvariety\b", r"\bchange\w*\b",
        ],
        "opposite": "security",
    },
    "hedonism": {
        "description": "Pleasure, sensuous gratification",
        "markers": [
            r"\bpleasur\w*\b", r"\benjoy\w*\b", r"\bfun\b",
            r"\bgratif\w*\b", r"\bindulg\w*\b", r"\btreat\b",
            r"\bpamper\w*\b", r"\bluxur\w*\b",
        ],
    },
    "achievement": {
        "description": "Personal success through competence",
        "markers": [
            r"\bsuccess\w*\b", r"\bachiev\w*\b", r"\bambiti\w*\b",
            r"\binfluenti\w*\b", r"\bcapabl\w*\b", r"\bcompeten\w*\b",
            r"\bgoal\w*\b", r"\bexcel\w*\b",
        ],
    },
    "power": {
        "description": "Social status, prestige, dominance",
        "markers": [
            r"\bpower\w*\b", r"\bwealth\w*\b", r"\bauthority\b",
            r"\bstatus\b", r"\bprestig\w*\b", r"\bcontrol\w*\b",
            r"\bdomina\w*\b", r"\binfluenc\w*\b",
        ],
        "opposite": "universalism",
    },
    "security": {
        "description": "Safety, stability, harmony",
        "markers": [
            r"\bsafe\w*\b", r"\bsecur\w*\b", r"\bstable\w*\b",
            r"\border\w*\b", r"\bclean\w*\b", r"\bhealth\w*\b",
            r"\bprotect\w*\b",
        ],
        "opposite": "stimulation",
    },
    "conformity": {
        "description": "Restraint of socially disruptive actions",
        "markers": [
            r"\bobedien\w*\b", r"\bself.?disciplin\w*\b", r"\bpolite\w*\b",
            r"\bhonor\w* (parents|elders)\b", r"\brespect\w*\b",
            r"\brules?\b", r"\bproper\b",
        ],
        "opposite": "self_direction",
    },
    "tradition": {
        "description": "Respect for customs and ideas",
        "markers": [
            r"\btradition\w*\b", r"\bhumbl\w*\b", r"\bdevot\w*\b",
            r"\baccept\w*\b", r"\bmodest\w*\b", r"\breligio\w*\b",
            r"\bcultur\w*\b", r"\bheritage\b",
        ],
    },
    "benevolence": {
        "description": "Welfare of close others",
        "markers": [
            r"\bhelp\w*\b", r"\bhonest\w*\b", r"\bforgiv\w*\b",
            r"\bloyal\w*\b", r"\bresponsib\w*\b", r"\bfriendship\b",
            r"\blove\b", r"\bcar(e|ing)\b",
        ],
    },
    "universalism": {
        "description": "Welfare of all people and nature",
        "markers": [
            r"\bequal\w*\b", r"\bpeace\w*\b", r"\bjustic\w*\b",
            r"\bwisdom\b", r"\bbeauty\b", r"\bnature\b",
            r"\benviron\w*\b", r"\bsocial\b", r"\bworld\b",
        ],
        "opposite": "power",
    },
    "application": "Values predict long-term brand relationships better than personality"
}


# =============================================================================
# CATEGORY XII: MEMORY & LEARNING FRAMEWORKS (Frameworks 56-58)
# =============================================================================

# Framework 56: Elaborative Encoding
# Depth of processing → memory strength
ELABORATIVE_ENCODING_MARKERS = {
    "deep_processing": {
        "description": "Rich elaboration indicates stronger memory formation",
        "markers": [
            r"\bdetail\w*\b", r"\bspecific\w*\b", r"\bvivid\w*\b",
            r"\bremember (exactly|clearly|specifically)\b",
            r"\bstands? out\b", r"\bunforgettable\b", r"\bmemorable\b",
            r"\bwill never forget\b", r"\betched in (my )?memory\b",
        ],
    },
    "personal_connection": {
        "description": "Self-referential processing",
        "markers": [
            r"\bremind\w* me of\b", r"\bjust like (my|when I)\b",
            r"\bpersonally\b", r"\bto me\b", r"\bfor me\b",
            r"\bmy (experience|story|situation)\b",
        ],
    },
    "emotional_encoding": {
        "description": "Emotional events are better remembered",
        "markers": [
            r"\b(so|very|extremely) (happy|excited|thrilled)\b",
            r"\blife.?chang\w*\b", r"\bgame.?chang\w*\b",
            r"\bnever felt (this|so)\b", r"\bbrought (tears|joy)\b",
        ],
    },
    "application": "Reviews with rich elaboration indicate stronger brand memory formation"
}


# Framework 57: Mere Exposure Effect
# Familiarity breeds liking
MERE_EXPOSURE_MARKERS = {
    "familiarity": {
        "description": "Prior exposure creates preference",
        "markers": [
            r"\bfamiliar\b", r"\bknow (this|the) brand\b",
            r"\b(seen|heard) (of |about )?(this|the|it) before\b",
            r"\brecogniz\w*\b", r"\bremember (seeing|hearing)\b",
        ],
    },
    "repeated_exposure": {
        "description": "Multiple encounters",
        "markers": [
            r"\bkept seeing\b", r"\beverywhere\b", r"\ball over\b",
            r"\b(always|constantly) (see|hear|notice)\b",
            r"\bcan't (escape|avoid|miss)\b",
        ],
    },
    "trust_through_familiarity": {
        "description": "Familiarity creates trust",
        "markers": [
            r"\bknown (brand|company|name)\b", r"\bestablished\b",
            r"\bbeen around\b", r"\bfamiliar (name|brand)\b",
            r"\btrust\w*\b.+\b(know|familiar)\b",
        ],
    },
    "application": "Frequency of mention → brand consideration"
}


# Framework 58: Peak-End Rule
# Experiences judged by peak moment + ending
PEAK_END_MARKERS = {
    "peak_moment": {
        "description": "Most intense moment of experience",
        "markers": [
            r"\bbest (part|moment|thing)\b", r"\bhighlight\b",
            r"\bwow moment\b", r"\bblew (me|my mind) away\b",
            r"\bpeak\b", r"\bincredible moment\b",
            r"\bworst (part|moment|thing)\b", r"\blow point\b",
        ],
    },
    "ending_experience": {
        "description": "Final impression",
        "markers": [
            r"\bin the end\b", r"\bfinally\b", r"\bultimately\b",
            r"\boverall\b", r"\ball (in all|things considered)\b",
            r"\blast (impression|experience|thing)\b",
            r"\bended (up|with|on)\b",
        ],
    },
    "narrative_arc": {
        "description": "Story structure with climax/resolution",
        "markers": [
            r"\bstarted\b.+\bthen\b.+\bfinally\b",
            r"\bat first\b.+\bbut (then|eventually)\b",
            r"\bafter (all|everything)\b.+\b(worth|glad)\b",
        ],
    },
    "application": "Review narratives reveal peak-end structure of experience"
}


# =============================================================================
# CATEGORY XIII: NARRATIVE & MEANING FRAMEWORKS (Frameworks 59-61)
# =============================================================================

# Framework 59: Narrative Transportation Theory
# Absorption into stories reduces counterarguing
NARRATIVE_TRANSPORTATION_MARKERS = {
    "immersion_indicators": {
        "description": "Being absorbed in a story",
        "markers": [
            r"\blost (myself|track|in)\b", r"\babsorbed\b",
            r"\bengrossed\b", r"\bcaptivat\w*\b", r"\bhook\w*\b",
            r"\bcouldn't (stop|put down|look away)\b",
            r"\bon the edge of (my )?seat\b",
        ],
    },
    "story_structure": {
        "description": "Narrative elements",
        "markers": [
            r"\bstory\b", r"\bjourney\b", r"\badventure\b",
            r"\bbegan\b.+\bthen\b.+\bfinally\b",
            r"\bit all started\b", r"\blittle did (I|we) know\b",
        ],
    },
    "character_identification": {
        "description": "Relating to characters/people",
        "markers": [
            r"\bjust like (me|us)\b", r"\brelat\w* to\b",
            r"\bfelt like (I was|we were)\b", r"\bin (my|their) shoes\b",
            r"\bsaw (myself|ourselves)\b",
        ],
    },
    "application": "Story-structured reviews indicate high persuasion potential"
}


# Framework 60: Meaning-Making Framework
# Products as vessels for life meaning
MEANING_MAKING_MARKERS = {
    "life_event_connection": {
        "description": "Product tied to significant life events",
        "markers": [
            r"\bwedding\b", r"\bgraduation\b", r"\bbirthday\b",
            r"\banniversary\b", r"\bretirement\b", r"\bbaby\b",
            r"\bnew (job|home|chapter)\b", r"\bmilestone\b",
            r"\bonce in a lifetime\b", r"\bspecial occasion\b",
        ],
    },
    "identity_expression": {
        "description": "Product expresses who I am",
        "markers": [
            r"\bwho I am\b", r"\brepresents (me|my)\b",
            r"\bpart of (my|our) (identity|life|story)\b",
            r"\bdefines\b", r"\bsays something about\b",
        ],
    },
    "legacy_meaning": {
        "description": "Product as legacy/inheritance",
        "markers": [
            r"\bpass (down|on) to\b", r"\bheirloom\b",
            r"\bgeneration\w*\b", r"\blegacy\b", r"\bforever\b",
            r"\blast (a lifetime|forever)\b",
        ],
    },
    "transformation": {
        "description": "Product enabled life transformation",
        "markers": [
            r"\bchanged my (life|perspective|world)\b",
            r"\btransform\w*\b", r"\bbefore and after\b",
            r"\bnew (me|person|chapter)\b", r"\bturning point\b",
        ],
    },
    "application": "Reviews mentioning life events signal different psychological needs"
}


# Framework 61: Hero's Journey Structure
# Problem → Struggle → Solution/Transformation
HEROS_JOURNEY_MARKERS = {
    "call_to_adventure": {
        "description": "Problem/need emerges",
        "markers": [
            r"\bhad (a )?problem\b", r"\bneeded\b", r"\bwas (looking|searching)\b",
            r"\bstruggl\w*\b", r"\bcouldn't (find|figure out)\b",
            r"\bchalleng\w*\b", r"\bwas tired of\b",
        ],
    },
    "road_of_trials": {
        "description": "Searching, trying, failing",
        "markers": [
            r"\btried (many|several|everything|so many)\b",
            r"\bnothing worked\b", r"\bfailed\b", r"\bdisappoint\w*\b",
            r"\bfrustrat\w*\b", r"\babout to give up\b",
        ],
    },
    "meeting_mentor": {
        "description": "Discovery of solution",
        "markers": [
            r"\b(then )?(found|discovered|came across)\b",
            r"\brecommended by\b", r"\bheard about\b",
            r"\bfinally\b", r"\bat last\b",
        ],
    },
    "transformation": {
        "description": "Success, resolution",
        "markers": [
            r"\bproblem solved\b", r"\bfinally (works|found)\b",
            r"\bgame.?changer\b", r"\blife.?chang\w*\b",
            r"\btransform\w*\b", r"\bnow I (can|have|am)\b",
        ],
    },
    "return_with_elixir": {
        "description": "Sharing wisdom/recommending",
        "markers": [
            r"\b(highly )?recommend\b", r"\btell (everyone|friends)\b",
            r"\bspread the word\b", r"\bdon't (wait|hesitate)\b",
            r"\byou (need|should|must) (try|get|buy)\b",
        ],
    },
    "application": "Reviews following hero's journey arc are more persuasive"
}


# =============================================================================
# CATEGORY XIV: TRUST & CREDIBILITY (Frameworks 62-64)
# =============================================================================

# Framework 62: Source Credibility Model
# Expertise × Trustworthiness × Attractiveness
SOURCE_CREDIBILITY_MARKERS = {
    "expertise_indicators": {
        "description": "Reviewer demonstrates knowledge",
        "markers": [
            r"\b(as a|I'm a) (professional|expert|specialist|enthusiast)\b",
            r"\byears of experience\b", r"\bknow (a lot|my) (about|stuff)\b",
            r"\btechnical\w*\b", r"\bin.?depth\b",
            r"\bcompared (to|with) (other|many|several)\b",
        ],
    },
    "trustworthiness_indicators": {
        "description": "Reviewer seems honest",
        "markers": [
            r"\bhonestly\b", r"\bto be (honest|fair)\b",
            r"\bnot (sponsored|paid|affiliated)\b",
            r"\bbought (this )?with my own\b", r"\bno (reason|incentive)\b",
            r"\bbalanced\b", r"\bpros? and cons?\b",
        ],
    },
    "similarity_indicators": {
        "description": "Reviewer is like me",
        "markers": [
            r"\bsame (situation|need|problem|boat)\b",
            r"\bjust like (me|you)\b", r"\bif you're like me\b",
            r"\b(other )?(moms?|dads?|parents?|professionals?)\b",
        ],
    },
    "application": "Review credibility assessment affects weight in training data"
}


# Framework 63: Elaboration of Evidence
# Specific details vs. vague claims
EVIDENCE_ELABORATION_MARKERS = {
    "specific_evidence": {
        "description": "Detailed, verifiable claims",
        "markers": [
            r"\b\d+ (days?|weeks?|months?|years?)\b",
            r"\b\d+ (times?|uses?|washes?)\b",
            r"\bspecifically\b", r"\bexactly\b", r"\bprecisely\b",
            r"\b\d+(\.\d+)?\s?(inch|cm|mm|oz|lb|kg|ml)\w*\b",
            r"\bfor example\b", r"\bsuch as\b",
        ],
    },
    "vague_claims": {
        "description": "Unsubstantiated statements",
        "markers": [
            r"\breally (good|great|nice)\b",
            r"\bvery\b.+\b(good|nice|great)\b",
            r"\bpretty (good|nice|decent)\b",
            r"\bworks (well|fine|okay)\b",
        ],
    },
    "verification_language": {
        "description": "Evidence of actual use",
        "markers": [
            r"\bafter (using|owning|having) for\b",
            r"\bcan confirm\b", r"\bverified\b", r"\bproven\b",
            r"\b(actually|really) (works|does|is)\b",
        ],
    },
    "application": "Specificity in reviews correlates with reviewer reliability"
}


# Framework 64: Negativity Bias in Trust
# One negative outweighs five positives
NEGATIVITY_BIAS_MARKERS = {
    "negative_weighting": {
        "description": "Negative experiences",
        "markers": [
            r"\bbut\b.+\b(problem|issue|flaw|downside)\b",
            r"\bonly (complaint|issue|problem|downside)\b",
            r"\bwish (it|they) (had|would|could)\b",
            r"\bmissing\b", r"\blacks?\b", r"\bwithout\b",
        ],
    },
    "deal_breakers": {
        "description": "Fatal flaws",
        "markers": [
            r"\bdeal.?breaker\b", r"\bcan't (overlook|ignore|forgive)\b",
            r"\bwon't (buy|recommend)\b", r"\breturn\w*\b",
            r"\bregret\w*\b", r"\bwaste\b", r"\bdisappoint\w*\b",
        ],
    },
    "despite_negatives": {
        "description": "Positives overcome negatives",
        "markers": [
            r"\bdespite\b", r"\beven though\b", r"\bregardless\b",
            r"\bstill (love|recommend|worth)\b",
            r"\bminor (issue|flaw|complaint)\b",
        ],
    },
    "application": "Weight negative reviews differently in segment profiling"
}


# =============================================================================
# CATEGORY XV: PRICE & VALUE PSYCHOLOGY (Frameworks 65-67)
# =============================================================================

# Framework 65: Mental Accounting
# Money in different "buckets"
MENTAL_ACCOUNTING_MARKERS = {
    "splurge_account": {
        "description": "Discretionary/fun money",
        "markers": [
            r"\bsplurge\w*\b", r"\btreat (myself|yourself)\b",
            r"\bdeserve\w*\b", r"\bworthy of\b",
            r"\bindulg\w*\b", r"\bspecial treat\b",
        ],
    },
    "necessities_account": {
        "description": "Essential purchases",
        "markers": [
            r"\bneed\w*\b", r"\bessential\b", r"\bnecessary\b",
            r"\bhad to (have|buy|get)\b", r"\bcan't (live|do) without\b",
            r"\bmust.?have\b", r"\brequir\w*\b",
        ],
    },
    "investment_account": {
        "description": "Long-term value purchases",
        "markers": [
            r"\binvest\w*\b", r"\blong.?term\b", r"\blast (for )?years\b",
            r"\bpay(s)? (for itself|off)\b", r"\bworth (the|every)\b",
            r"\bsave (money|in the long run)\b",
        ],
    },
    "gift_account": {
        "description": "Gifts have different budget",
        "markers": [
            r"\bgift\w*\b", r"\bfor (my|the) (wife|husband|mom|dad|friend)\b",
            r"\bbought (it )?(as|for) a (gift|present)\b",
            r"\bspecial (for|occasion)\b",
        ],
    },
    "application": "'Worth the splurge' vs 'good value' reveals mental account"
}


# Framework 66: Reference Price Theory
# Internal price expectations
REFERENCE_PRICE_MARKERS = {
    "price_expectations": {
        "description": "Internal reference points",
        "markers": [
            r"\bexpected (to pay|it to cost)\b",
            r"\bthought it would (be|cost)\b",
            r"\bcompared to (other|similar|competing)\b",
            r"\bfor (this|the) price\b", r"\bat this price (point)?\b",
        ],
    },
    "price_surprise_positive": {
        "description": "Better than expected",
        "markers": [
            r"\b(much|way) (cheaper|less|better value)\b",
            r"\bsurpris\w* (at|by) the (low )?price\b",
            r"\bsteal\b", r"\bbargain\b", r"\bcan't beat\b",
            r"\bfor (only|just) \$?\d+\b",
        ],
    },
    "price_surprise_negative": {
        "description": "Worse than expected",
        "markers": [
            r"\b(too|way too|really) (expensive|pricey|costly)\b",
            r"\boverpriced\b", r"\brip.?off\b",
            r"\bnot worth\b.+\bprice\b", r"\bexpected (more|better)\b.+\bprice\b",
        ],
    },
    "price_quality_inference": {
        "description": "Price signals quality",
        "markers": [
            r"\bpay (for|more for) quality\b",
            r"\bget what you pay for\b",
            r"\bcheap (and|=) (bad|poor|low quality)\b",
            r"\bexpensive (but|and) (worth|quality)\b",
        ],
    },
    "application": "Review price language reveals segment's reference points"
}


# Framework 67: Pain of Paying
# Neural pain response to spending
PAIN_OF_PAYING_MARKERS = {
    "payment_pain": {
        "description": "Difficulty parting with money",
        "markers": [
            r"\bhard to (justify|spend|part with)\b",
            r"\bhurt (to|my wallet)\b", r"\bpainful\b",
            r"\bgulped\b", r"\bwinced\b", r"\bhesitat\w*\b",
            r"\bbig (purchase|investment|decision)\b",
        ],
    },
    "payment_ease": {
        "description": "Easy spending",
        "markers": [
            r"\bno.?brainer\b", r"\bdidn't (think twice|hesitate)\b",
            r"\beasy (decision|purchase|to justify)\b",
            r"\bworth every (penny|cent|dollar)\b",
            r"\bwould (pay|spend) (more|twice)\b",
        ],
    },
    "payment_method_preferences": {
        "description": "How payment affects pain",
        "markers": [
            r"\b(credit|debit) card\b", r"\bpay\w* plan\b",
            r"\bfinancing\b", r"\binstallments?\b",
            r"\bsubscription\b", r"\bmonthly\b",
        ],
    },
    "application": "Payment decoupling reduces pain - subscription vs. one-time"
}


# =============================================================================
# CATEGORY XVI: MECHANISM INTERACTION (Frameworks 68-70)
# =============================================================================

# Framework 68: Mechanism Synergy Effects
# Some mechanisms amplify each other
MECHANISM_SYNERGY = {
    "synergies": {
        "loss_aversion_scarcity": {
            "description": "Loss aversion + Scarcity = 1.4x combined effect",
            "combined_markers": [
                r"\bdon't miss\b.+\b(only|last|few left)\b",
                r"\b(limited|running out)\b.+\b(miss|lose)\b",
            ],
        },
        "social_proof_authority": {
            "description": "Expert-backed social proof",
            "combined_markers": [
                r"\bexpert\w*\b.+\brecommend\w*\b.+\beveryone\b",
                r"\bdoctor\w*\b.+\bpopular\b",
            ],
        },
        "scarcity_social_proof": {
            "description": "Popular + Limited = urgency",
            "combined_markers": [
                r"\beveryone\b.+\b(selling out|limited)\b",
                r"\bpopular\b.+\b(few left|hurry)\b",
            ],
        },
        "reciprocity_commitment": {
            "description": "Gift + small commitment builds",
            "combined_markers": [
                r"\bfree\b.+\bthen (bought|upgraded)\b",
                r"\btrial\b.+\bconverted\b",
            ],
        },
    },
    "application": "Combined mechanisms have multiplicative effects"
}


# Framework 69: Mechanism Interference
# Some mechanisms cancel each other
MECHANISM_INTERFERENCE = {
    "interferences": {
        "social_proof_exclusivity": {
            "description": "Popular conflicts with exclusive",
            "conflict_markers": [
                r"\beveryone has\b.+\bexclusive\b",
                r"\bpopular\b.+\brare\b",
            ],
        },
        "authority_liking": {
            "description": "Expert can seem cold/unlikeable",
            "conflict_markers": [
                r"\bexpert\b.+\bcold\b",
                r"\bprofessional\b.+\bunfriendly\b",
            ],
        },
        "scarcity_quality": {
            "description": "Too scarce may signal problems",
            "conflict_markers": [
                r"\bnever in stock\b.+\bsuspicious\b",
                r"\bhard to find\b.+\bwhy\b",
            ],
        },
    },
    "application": "Avoid conflicting mechanism combinations"
}


# Framework 70: Mechanism Sequencing
# Order matters
MECHANISM_SEQUENCING = {
    "effective_sequences": {
        "social_proof_first": {
            "description": "Social Proof → Loss Aversion works better than reverse",
            "sequence_markers": [
                r"\beveryone\b.+\bthen\b.+\bdon't miss\b",
                r"\bpopular\b.+\bso\b.+\bhurry\b",
            ],
        },
        "reciprocity_first": {
            "description": "Give value before asking",
            "sequence_markers": [
                r"\b(free|gift|bonus)\b.+\bthen\b.+\b(bought|subscribed)\b",
                r"\bafter\b.+\b(trial|sample)\b.+\b(committed|purchased)\b",
            ],
        },
        "authority_then_social": {
            "description": "Establish credibility, then show popularity",
            "sequence_markers": [
                r"\bexpert\w*\b.+\band\b.+\beveryone\b",
                r"\bprofessional\w*\b.+\bpopular\b",
            ],
        },
    },
    "application": "Sequence mechanisms optimally for maximum effect"
}


# =============================================================================
# CATEGORY XVII: CONTEXTUAL MODULATION (Frameworks 71-73)
# =============================================================================

# Framework 71: Regulatory Fit
# Message strategy matching regulatory focus
REGULATORY_FIT_MARKERS = {
    "promotion_fit": {
        "description": "Eager strategy for promotion focus",
        "markers": [
            r"\bachieve\w*\b.+\bgain\w*\b",
            r"\bmaximize\b.+\bopportunit\w*\b",
            r"\bgrow\w*\b.+\bpotential\b",
        ],
    },
    "prevention_fit": {
        "description": "Vigilant strategy for prevention focus",
        "markers": [
            r"\bprotect\w*\b.+\bsafe\w*\b",
            r"\bavoid\w*\b.+\brisk\w*\b",
            r"\bsecur\w*\b.+\bguarantee\w*\b",
        ],
    },
    "fit_experience": {
        "description": "Feeling right from fit",
        "markers": [
            r"\bfelt right\b", r"\bjust (clicked|knew)\b",
            r"\bperfect (fit|match)\b", r"\bmeant to be\b",
        ],
    },
    "application": "Regulatory fit produces 'feeling right' that increases persuasion 20-40%"
}


# Framework 72: Construal Fit
# Message abstraction matching construal level
CONSTRUAL_FIT_MARKERS = {
    "abstract_message_fit": {
        "description": "High construal + abstract message",
        "markers": [
            r"\bwhy\b.+\bmeaning\b",
            r"\bpurpose\b.+\bvalue\b",
            r"\bvision\b.+\bgoal\b",
        ],
    },
    "concrete_message_fit": {
        "description": "Low construal + concrete message",
        "markers": [
            r"\bhow\b.+\bsteps?\b",
            r"\bfeatures?\b.+\bspec\w*\b",
            r"\bdetail\w*\b.+\bfunction\w*\b",
        ],
    },
    "application": "Abstract messages for distant decisions; concrete for near decisions"
}


# Framework 73: Resource Depletion Context
# Ego depletion affects decision quality
RESOURCE_DEPLETION_MARKERS = {
    "depleted_state": {
        "description": "Low willpower/cognitive resources",
        "markers": [
            r"\btired\b", r"\bexhaust\w*\b", r"\bworn out\b",
            r"\bafter (a long|work|everything)\b",
            r"\bno (energy|patience|bandwidth)\b",
            r"\boverwhel\w*\b", r"\bstress\w*\b",
        ],
    },
    "resourced_state": {
        "description": "High willpower/cognitive resources",
        "markers": [
            r"\bfresh\b", r"\bclear.?headed\b", r"\bfocused\b",
            r"\benerg\w*\b", r"\bready to\b", r"\bsharp\b",
        ],
    },
    "depletion_behaviors": {
        "description": "Behaviors when depleted",
        "markers": [
            r"\bjust (bought|clicked|went with)\b",
            r"\bdidn't (think|care|bother)\b",
            r"\bwhatever\b", r"\bgave up (looking|researching)\b",
        ],
    },
    "application": "Simplify choices when ego depletion is detected"
}


# =============================================================================
# CATEGORY XVIII: CULTURAL & DEMOGRAPHIC (Frameworks 74-76)
# =============================================================================

# Framework 74: Cultural Self-Construal
# Independent vs. Interdependent self-concept
CULTURAL_SELF_CONSTRUAL_MARKERS = {
    "independent_culture": {
        "description": "'I' cultures - individualistic",
        "markers": [
            r"\bi\b", r"\bme\b", r"\bmy\b", r"\bmyself\b",
            r"\bpersonal\w*\b", r"\bindividual\w*\b",
            r"\bmy (own|choice|decision|preference)\b",
        ],
    },
    "interdependent_culture": {
        "description": "'We' cultures - collectivistic",
        "markers": [
            r"\bwe\b", r"\bour\b", r"\bus\b", r"\bourselves\b",
            r"\bfamily\b", r"\bgroup\b", r"\bcommunity\b",
            r"\btogether\b", r"\bour (family|group|team)\b",
        ],
    },
    "cultural_values": {
        "description": "Culture-specific value expressions",
        "markers": [
            r"\btradition\w*\b", r"\bheritage\b", r"\bcultur\w*\b",
            r"\bfamily (honor|tradition|name)\b",
        ],
    },
    "application": "'I' vs 'We' cultures respond to different appeals"
}


# Framework 75: Power Distance Orientation
# Acceptance of hierarchy
POWER_DISTANCE_MARKERS = {
    "high_power_distance": {
        "description": "Acceptance of hierarchy and authority",
        "markers": [
            r"\bauthority\b", r"\bexpert\w*\b", r"\bprofessional\w*\b",
            r"\brespect\w*\b", r"\bsuperior\b", r"\bsenior\b",
            r"\b(doctor|expert|professional) (says|recommends)\b",
        ],
    },
    "low_power_distance": {
        "description": "Equality, questioning authority",
        "markers": [
            r"\bequal\w*\b", r"\beveryone\b.+\bsame\b",
            r"\bquestion\w*\b", r"\bchalleng\w*\b",
            r"\bmy (own|opinion|research)\b",
        ],
    },
    "application": "Affects authority mechanism effectiveness"
}


# Framework 76: Uncertainty Avoidance (Hofstede)
# Cultural comfort with ambiguity
UNCERTAINTY_AVOIDANCE_CULTURAL_MARKERS = {
    "high_uncertainty_avoidance": {
        "description": "Need for rules, structure, certainty",
        "markers": [
            r"\brules?\b", r"\bguarantee\w*\b", r"\bcertain\w*\b",
            r"\bproven\b", r"\btested\b", r"\bverified\b",
            r"\b(need to|must) know\b", r"\bcan't (risk|chance)\b",
        ],
    },
    "low_uncertainty_avoidance": {
        "description": "Comfort with ambiguity, risk-taking",
        "markers": [
            r"\bwe'll see\b", r"\bfigure it out\b", r"\bwhy not\b",
            r"\btook a (chance|risk)\b", r"\bexperiment\w*\b",
            r"\bopen to\b", r"\bflexi\w*\b",
        ],
    },
    "application": "Affects need for guarantees and reassurance messaging"
}


# =============================================================================
# CATEGORY XIX: ETHICAL GUARDRAILS (Frameworks 77-79)
# =============================================================================

# Framework 77: Vulnerability Detection
# Psychological distress states - DO NOT TARGET
VULNERABILITY_MARKERS = {
    "distress_indicators": {
        "description": "Signs of psychological distress",
        "markers": [
            r"\bdesperat\w*\b", r"\bhopeless\b", r"\bdepress\w*\b",
            r"\banxiet\w*\b", r"\bpanic\w*\b", r"\bbreakdown\b",
            r"\bcan't (cope|handle|take)\b", r"\bat (my|the) limit\b",
            r"\brock bottom\b", r"\blow point\b",
        ],
    },
    "financial_distress": {
        "description": "Financial vulnerability",
        "markers": [
            r"\bcan't afford\b", r"\bstruggling (financially|to pay)\b",
            r"\bdebt\b", r"\bbroke\b", r"\bbankrupt\w*\b",
            r"\blast (resort|option|chance)\b",
        ],
    },
    "health_vulnerability": {
        "description": "Health-related vulnerability",
        "markers": [
            r"\bdesperately (need|trying)\b.+\b(cure|treatment|help)\b",
            r"\bnothing (else )?(works|worked|has worked)\b",
            r"\blast (hope|resort|chance)\b.+\b(cure|treatment)\b",
        ],
    },
    "grief_vulnerability": {
        "description": "Grief/loss vulnerability",
        "markers": [
            r"\bjust (lost|died|passed)\b",
            r"\bgrieving\b", r"\bmourning\b",
            r"\bin memory of\b",
        ],
    },
    "application": "DO NOT target users in distressed states with high-pressure messaging"
}


# Framework 78: Manipulation vs. Persuasion Boundary
# Autonomy preservation
MANIPULATION_BOUNDARY_MARKERS = {
    "autonomy_respecting": {
        "description": "Respects consumer choice",
        "markers": [
            r"\b(you )?decide\b", r"\b(your )?(choice|decision)\b",
            r"\bup to you\b", r"\bconsider\w*\b",
            r"\bif (you want|it works for you)\b",
        ],
    },
    "manipulation_red_flags": {
        "description": "Potentially manipulative tactics",
        "markers": [
            r"\bact now\b.+\bor (lose|miss|never)\b",
            r"\blast chance\b.+\bforever\b",
            r"\bonly (you|for you|today)\b.+\bspecial\b",
            r"\beveryone (is|has)\b.+\bdon't be (left|the only)\b",
        ],
    },
    "application": "Maintain ethical limits on psychological targeting"
}


# Framework 79: Identity Threat Limits
# Don't deliberately threaten identity to drive compensatory purchase
IDENTITY_THREAT_MARKERS = {
    "identity_threat_tactics": {
        "description": "Tactics that threaten self-concept - AVOID",
        "markers": [
            r"\byou're (not|less)\b.+\b(enough|good|complete)\b",
            r"\b(real|true) (men|women|professionals)\b.+\bhave\b",
            r"\bdon't you want to be\b",
            r"\bwithout this\b.+\byou're\b",
        ],
    },
    "positive_identity_building": {
        "description": "Building up self-concept - PREFERRED",
        "markers": [
            r"\byou (are|deserve)\b", r"\bfor people like you\b",
            r"\bbecause you\b.+\b(value|care|matter)\b",
            r"\benhance\b.+\byour\b",
        ],
    },
    "application": "Build identity up, don't tear it down to sell"
}


# =============================================================================
# CATEGORY XX: ADVANCED INFERENCE (Frameworks 80-82)
# =============================================================================

# Framework 80: Counterfactual Reasoning
# "What would have happened otherwise"
COUNTERFACTUAL_MARKERS = {
    "counterfactual_thinking": {
        "description": "Alternative outcome consideration",
        "markers": [
            r"\bif I had(n't)?\b", r"\bwould have (been|had)\b",
            r"\bcould have\b", r"\bshould have\b",
            r"\binstead of\b", r"\brather than\b",
            r"\bwhat if\b", r"\bimagine if\b",
        ],
    },
    "upward_counterfactual": {
        "description": "Could have been better",
        "markers": [
            r"\bcould have been better\b", r"\bshould have\b.+\binstead\b",
            r"\bwish I had\b", r"\bif only\b",
        ],
    },
    "downward_counterfactual": {
        "description": "Could have been worse",
        "markers": [
            r"\bcould have been worse\b", r"\bat least\b",
            r"\bthankfully\b", r"\bgrateful\b.+\b(didn't|not)\b",
        ],
    },
    "application": "Causal attribution for mechanism effectiveness"
}


# Framework 81: Transfer Learning Archetypes
# Cold start user classification - expanded from core archetypes
TRANSFER_ARCHETYPES = {
    "archetypes": {
        "explorer": {
            "description": "Novelty-seeking, adventure-focused",
            "primary_values": ["stimulation", "self_direction"],
            "cognitive_style": "experiential",
            "regulatory_focus": "promotion",
        },
        "achiever": {
            "description": "Success-driven, status-conscious",
            "primary_values": ["achievement", "power"],
            "cognitive_style": "analytical",
            "regulatory_focus": "promotion",
        },
        "connector": {
            "description": "Relationship-focused, community-oriented",
            "primary_values": ["benevolence", "universalism"],
            "cognitive_style": "social",
            "regulatory_focus": "mixed",
        },
        "guardian": {
            "description": "Security-focused, protection-driven",
            "primary_values": ["security", "conformity"],
            "cognitive_style": "analytical",
            "regulatory_focus": "prevention",
        },
        "analyst": {
            "description": "Knowledge-driven, detail-oriented",
            "primary_values": ["self_direction", "achievement"],
            "cognitive_style": "analytical",
            "regulatory_focus": "prevention",
        },
        "creator": {
            "description": "Innovation-focused, self-expression",
            "primary_values": ["self_direction", "stimulation"],
            "cognitive_style": "intuitive",
            "regulatory_focus": "promotion",
        },
        "nurturer": {
            "description": "Care-focused, others-oriented",
            "primary_values": ["benevolence", "security"],
            "cognitive_style": "social",
            "regulatory_focus": "prevention",
        },
        "pragmatist": {
            "description": "Value-focused, efficiency-driven",
            "primary_values": ["security", "conformity"],
            "cognitive_style": "analytical",
            "regulatory_focus": "prevention",
        },
    },
    "application": "Cold start classification for new users with limited data"
}


# Framework 82: Confidence Calibration
# How sure should we be about inferences
CONFIDENCE_CALIBRATION_MARKERS = {
    "high_confidence_indicators": {
        "description": "Strong signal quality",
        "markers": [
            r"\b(definitely|absolutely|certainly|100%)\b",
            r"\bwithout (a )?doubt\b", r"\bfor sure\b",
            r"\bno question\b", r"\bguarantee\b",
        ],
    },
    "low_confidence_indicators": {
        "description": "Weak signal quality",
        "markers": [
            r"\bmaybe\b", r"\bperhaps\b", r"\bpossibly\b",
            r"\bnot sure\b", r"\bi think\b", r"\bseems like\b",
            r"\bprobably\b", r"\bmight\b",
        ],
    },
    "sample_size_indicators": {
        "description": "Amount of data available",
        "markers": [
            r"\bafter \d+ (days|weeks|months|years)\b",
            r"\b\d+\+? (times|uses|washes|orders)\b",
            r"\blong.?term\b", r"\bextensive\w*\b",
        ],
    },
    "application": "Prevents overconfident targeting decisions"
}


# =============================================================================
# EXTENDED FRAMEWORK ANALYZER
# =============================================================================

class ExtendedFrameworkAnalyzer:
    """
    Analyzes text against frameworks 41-82.
    
    Complements the PsychologicalFrameworkAnalyzer for complete 82-framework coverage.
    """
    
    def __init__(self):
        self._compile_all_patterns()
    
    def _compile_all_patterns(self):
        """Compile all extended framework patterns."""
        self.compiled_patterns = {}
        
        all_frameworks = {
            # Category VIII: Temporal/State (41-45)
            "state_trait": STATE_TRAIT_INTERACTION_MARKERS,
            "arousal": AROUSAL_MODULATION_MARKERS,
            "circadian": CIRCADIAN_MARKERS,
            "journey_stage": JOURNEY_STAGE_MARKERS,
            "temporal_construal": TEMPORAL_CONSTRUAL_MARKERS,
            
            # Category IX: Behavioral (46-50)
            "micro_temporal": MICRO_TEMPORAL_MARKERS,
            "cross_category": CROSS_CATEGORY_MARKERS,
            "content_consumption": CONTENT_CONSUMPTION_MARKERS,
            "physiological_proxy": PHYSIOLOGICAL_PROXY_MARKERS,
            "interaction_sequence": INTERACTION_SEQUENCING_MARKERS,
            
            # Category X: Brand (51-53)
            "brand_personality": BRAND_PERSONALITY_MARKERS,
            "brand_self_congruity": BRAND_SELF_CONGRUITY_MARKERS,
            "psychological_ownership": PSYCHOLOGICAL_OWNERSHIP_MARKERS,
            
            # Category XI: Moral (54-55)
            "moral_foundations": MORAL_FOUNDATIONS_MARKERS,
            "schwartz_values": SCHWARTZ_VALUES_EXPANDED,
            
            # Category XII: Memory (56-58)
            "elaborative_encoding": ELABORATIVE_ENCODING_MARKERS,
            "mere_exposure": MERE_EXPOSURE_MARKERS,
            "peak_end": PEAK_END_MARKERS,
            
            # Category XIII: Narrative (59-61)
            "narrative_transportation": NARRATIVE_TRANSPORTATION_MARKERS,
            "meaning_making": MEANING_MAKING_MARKERS,
            "heros_journey": HEROS_JOURNEY_MARKERS,
            
            # Category XIV: Trust (62-64)
            "source_credibility": SOURCE_CREDIBILITY_MARKERS,
            "evidence_elaboration": EVIDENCE_ELABORATION_MARKERS,
            "negativity_bias": NEGATIVITY_BIAS_MARKERS,
            
            # Category XV: Price (65-67)
            "mental_accounting": MENTAL_ACCOUNTING_MARKERS,
            "reference_price": REFERENCE_PRICE_MARKERS,
            "pain_of_paying": PAIN_OF_PAYING_MARKERS,
            
            # Category XVI: Mechanism Interaction (68-70)
            "mechanism_synergy": MECHANISM_SYNERGY,
            "mechanism_interference": MECHANISM_INTERFERENCE,
            "mechanism_sequencing": MECHANISM_SEQUENCING,
            
            # Category XVII: Context (71-73)
            "regulatory_fit": REGULATORY_FIT_MARKERS,
            "construal_fit": CONSTRUAL_FIT_MARKERS,
            "resource_depletion": RESOURCE_DEPLETION_MARKERS,
            
            # Category XVIII: Cultural (74-76)
            "cultural_self_construal": CULTURAL_SELF_CONSTRUAL_MARKERS,
            "power_distance": POWER_DISTANCE_MARKERS,
            "uncertainty_avoidance_cultural": UNCERTAINTY_AVOIDANCE_CULTURAL_MARKERS,
            
            # Category XIX: Ethical (77-79)
            "vulnerability": VULNERABILITY_MARKERS,
            "manipulation_boundary": MANIPULATION_BOUNDARY_MARKERS,
            "identity_threat": IDENTITY_THREAT_MARKERS,
            
            # Category XX: Advanced (80-82)
            "counterfactual": COUNTERFACTUAL_MARKERS,
            "transfer_archetypes": TRANSFER_ARCHETYPES,
            "confidence_calibration": CONFIDENCE_CALIBRATION_MARKERS,
        }
        
        for name, framework in all_frameworks.items():
            self.compiled_patterns[name] = self._compile_framework(framework)
    
    def _compile_framework(self, framework: Dict) -> Dict:
        """Compile patterns for a framework."""
        compiled = {}
        
        for key, value in framework.items():
            if key == "application":
                compiled[key] = value
                continue
            
            if isinstance(value, dict):
                if "markers" in value:
                    if isinstance(value["markers"], list):
                        compiled[key] = {
                            "patterns": [re.compile(p, re.IGNORECASE) for p in value["markers"]],
                            "description": value.get("description", ""),
                        }
                    else:
                        compiled[key] = value
                elif "archetypes" in value:
                    compiled[key] = value
                elif "synergies" in value or "interferences" in value or "effective_sequences" in value:
                    compiled[key] = value
                else:
                    compiled[key] = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict):
                            if "markers" in sub_value:
                                compiled[key][sub_key] = {
                                    "patterns": [re.compile(p, re.IGNORECASE) for p in sub_value["markers"]],
                                    "description": sub_value.get("description", ""),
                                }
                            elif "combined_markers" in sub_value or "conflict_markers" in sub_value or "sequence_markers" in sub_value:
                                marker_key = [k for k in sub_value.keys() if "markers" in k][0] if any("markers" in k for k in sub_value.keys()) else None
                                if marker_key:
                                    compiled[key][sub_key] = {
                                        "patterns": [re.compile(p, re.IGNORECASE) for p in sub_value[marker_key]],
                                        "description": sub_value.get("description", ""),
                                    }
                                else:
                                    compiled[key][sub_key] = sub_value
                            else:
                                compiled[key][sub_key] = sub_value
                        elif isinstance(sub_value, list):
                            compiled[key][sub_key] = [re.compile(p, re.IGNORECASE) for p in sub_value]
            elif isinstance(value, str):
                compiled[key] = value
        
        return compiled
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text against frameworks 41-82."""
        results = {}
        
        if not text or len(text) < 20:
            return results
        
        # Analyze each framework category
        results["temporal_state"] = self._analyze_temporal_state(text)
        results["behavioral"] = self._analyze_behavioral(text)
        results["brand"] = self._analyze_brand(text)
        results["moral_values"] = self._analyze_moral_values(text)
        results["memory"] = self._analyze_memory(text)
        results["narrative"] = self._analyze_narrative(text)
        results["trust"] = self._analyze_trust(text)
        results["price"] = self._analyze_price(text)
        results["mechanism_interaction"] = self._analyze_mechanism_interaction(text)
        results["context"] = self._analyze_context(text)
        results["cultural"] = self._analyze_cultural(text)
        results["ethical"] = self._analyze_ethical(text)
        results["advanced"] = self._analyze_advanced(text)
        
        return results
    
    def _count_matches(self, text: str, patterns: List) -> int:
        """Count pattern matches."""
        count = 0
        for pattern in patterns:
            if isinstance(pattern, re.Pattern):
                count += len(pattern.findall(text))
        return count
    
    def _analyze_category(self, text: str, framework_names: List[str]) -> Dict[str, float]:
        """Generic category analysis."""
        scores = {}
        
        for fw_name in framework_names:
            if fw_name not in self.compiled_patterns:
                continue
            
            fw = self.compiled_patterns[fw_name]
            total = 0
            
            for key, value in fw.items():
                if key == "application" or not isinstance(value, dict):
                    continue
                
                if "patterns" in value:
                    total += self._count_matches(text, value["patterns"])
                else:
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict) and "patterns" in sub_value:
                            total += self._count_matches(text, sub_value["patterns"])
                        elif isinstance(sub_value, list):
                            total += self._count_matches(text, sub_value)
            
            scores[fw_name] = min(1.0, total / 5)
        
        return scores
    
    def _analyze_temporal_state(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["state_trait", "arousal", "circadian", "journey_stage", "temporal_construal"])
    
    def _analyze_behavioral(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["micro_temporal", "cross_category", "content_consumption", "physiological_proxy", "interaction_sequence"])
    
    def _analyze_brand(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["brand_personality", "brand_self_congruity", "psychological_ownership"])
    
    def _analyze_moral_values(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["moral_foundations", "schwartz_values"])
    
    def _analyze_memory(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["elaborative_encoding", "mere_exposure", "peak_end"])
    
    def _analyze_narrative(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["narrative_transportation", "meaning_making", "heros_journey"])
    
    def _analyze_trust(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["source_credibility", "evidence_elaboration", "negativity_bias"])
    
    def _analyze_price(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["mental_accounting", "reference_price", "pain_of_paying"])
    
    def _analyze_mechanism_interaction(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["mechanism_synergy", "mechanism_interference", "mechanism_sequencing"])
    
    def _analyze_context(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["regulatory_fit", "construal_fit", "resource_depletion"])
    
    def _analyze_cultural(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["cultural_self_construal", "power_distance", "uncertainty_avoidance_cultural"])
    
    def _analyze_ethical(self, text: str) -> Dict[str, float]:
        scores = self._analyze_category(text, ["vulnerability", "manipulation_boundary", "identity_threat"])
        
        # Flag if vulnerability detected
        if scores.get("vulnerability", 0) > 0.3:
            scores["VULNERABILITY_FLAG"] = True
        
        return scores
    
    def _analyze_advanced(self, text: str) -> Dict[str, float]:
        return self._analyze_category(text, ["counterfactual", "confidence_calibration"])


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    analyzer = ExtendedFrameworkAnalyzer()
    
    test_reviews = [
        """
        After struggling for months with my skin, I finally found this product.
        I tried everything - nothing worked. Then my dermatologist recommended this.
        It's been a game-changer! My skin has completely transformed. If you're 
        struggling like I was, you NEED to try this. Don't wait like I did.
        """,
        
        """
        Bought this as an anniversary gift for my wife. It's our 25th year together.
        She cried when she opened it - it means so much to us. This will be passed
        down to our daughter someday. Worth every penny for something this meaningful.
        """,
        
        """
        I'm desperate. Nothing has worked for my condition. This is my last hope.
        I can't afford much but I had to try something. I'm at rock bottom and
        praying this will help. Please let this work.
        """,
    ]
    
    for i, review in enumerate(test_reviews, 1):
        print(f"\n{'='*70}")
        print(f"REVIEW {i}")
        print("=" * 70)
        print(review.strip()[:150] + "...")
        
        results = analyzer.analyze(review)
        
        print(f"\n📊 EXTENDED FRAMEWORK ANALYSIS:")
        
        for category, scores in results.items():
            active_scores = {k: v for k, v in scores.items() if isinstance(v, (int, float)) and v > 0.2}
            if active_scores:
                print(f"\n   {category.upper()}:")
                for key, score in sorted(active_scores.items(), key=lambda x: -x[1])[:3]:
                    bar = "█" * int(score * 20)
                    print(f"      {key}: {bar} {score:.1%}")
        
        # Check for vulnerability flag
        if results.get("ethical", {}).get("VULNERABILITY_FLAG"):
            print(f"\n   ⚠️  VULNERABILITY DETECTED - DO NOT TARGET WITH HIGH-PRESSURE MESSAGING")
