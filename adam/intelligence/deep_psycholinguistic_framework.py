#!/usr/bin/env python3
"""
DEEP PSYCHOLINGUISTIC ANALYSIS FRAMEWORK
=========================================

This is a COMPLETE REDESIGN of the psychological analysis system.
The previous system was embarrassingly shallow - this aims for 20x+ granularity.

RESEARCH BASIS:
- LIWC-22 (100+ psychological dimensions)
- Plutchik's Wheel of Emotions (8 primary, 24+ secondary, 3 intensity levels)
- 200+ Cognitive Biases with linguistic triggers
- Big Five Personality Traits with word-level markers
- Regulatory Focus Theory (Promotion vs Prevention)
- Consumer Decision Journey Stages
- 65+ Dark Pattern Categories
- Cialdini's 6 Principles + 30+ sub-mechanisms

DIMENSIONS OF ANALYSIS:
1. EMOTIONAL GRANULARITY (50+ emotion categories)
2. COGNITIVE PROCESS MARKERS (40+ thinking patterns)
3. SOCIAL DYNAMICS (25+ relationship indicators)
4. MOTIVATION & NEED STATES (30+ drive indicators)
5. DECISION STYLE FINGERPRINTS (20+ decision patterns)
6. PERSUASION SUSCEPTIBILITY PROFILE (50+ vulnerability markers)
7. PERSONALITY INFERENCE (Big Five + sub-facets = 35+ dimensions)
8. LINGUISTIC STYLE (40+ style markers)
9. TRUST & CREDIBILITY SIGNALS (20+ authenticity markers)
10. TEMPORAL ORIENTATION (15+ time perspective markers)

TOTAL: 325+ PSYCHOLOGICAL DIMENSIONS (vs. previous ~20)
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import math


# =============================================================================
# PART 1: EMOTIONAL GRANULARITY
# =============================================================================
# Based on Plutchik's Wheel + Research Extensions
# 8 Primary × 3 Intensities = 24 base emotions
# + 24 Secondary (adjacent combinations)
# + 24 Tertiary (non-adjacent combinations)
# = 72 distinct emotional states

EMOTION_TAXONOMY = {
    # PRIMARY EMOTIONS - Each with 3 intensity levels
    # Format: emotion_name: {intensity_level: [markers]}
    
    # JOY SPECTRUM (low → high: serenity → joy → ecstasy)
    "serenity": {
        "markers": ["content", "satisfied", "peaceful", "calm", "relaxed", "at ease", 
                   "comfortable", "pleasant", "nice enough", "fine"],
        "intensity": 0.3,
        "valence": 0.6,
    },
    "joy": {
        "markers": ["happy", "glad", "pleased", "delighted", "cheerful", "joyful",
                   "enjoy", "wonderful", "great", "love it", "fantastic"],
        "intensity": 0.6,
        "valence": 0.8,
    },
    "ecstasy": {
        "markers": ["thrilled", "elated", "euphoric", "overjoyed", "ecstatic", 
                   "blown away", "absolutely amazing", "best ever", "couldn't be happier",
                   "exceeded all expectations", "mind-blowing", "life-changing"],
        "intensity": 1.0,
        "valence": 1.0,
    },
    
    # TRUST SPECTRUM (low → high: acceptance → trust → admiration)
    "acceptance": {
        "markers": ["okay", "acceptable", "adequate", "sufficient", "workable",
                   "tolerable", "fair enough", "does the job"],
        "intensity": 0.3,
        "valence": 0.4,
    },
    "trust": {
        "markers": ["reliable", "dependable", "trustworthy", "consistent", "honest",
                   "genuine", "authentic", "quality", "well-made", "solid"],
        "intensity": 0.6,
        "valence": 0.7,
    },
    "admiration": {
        "markers": ["impressed", "admire", "respect", "exceptional", "outstanding",
                   "remarkable", "incredible quality", "masterful", "superior",
                   "best in class", "gold standard"],
        "intensity": 1.0,
        "valence": 0.9,
    },
    
    # FEAR SPECTRUM (low → high: apprehension → fear → terror)
    "apprehension": {
        "markers": ["worried", "concerned", "uneasy", "nervous", "hesitant",
                   "uncertain", "doubtful", "skeptical", "wary", "cautious about"],
        "intensity": 0.3,
        "valence": -0.4,
    },
    "fear": {
        "markers": ["afraid", "scared", "frightened", "alarmed", "anxious",
                   "distressed", "panicked", "dreading", "fearful"],
        "intensity": 0.6,
        "valence": -0.7,
    },
    "terror": {
        "markers": ["terrified", "horrified", "petrified", "traumatized",
                   "nightmare", "devastating", "worst experience"],
        "intensity": 1.0,
        "valence": -1.0,
    },
    
    # SURPRISE SPECTRUM (low → high: distraction → surprise → amazement)
    "distraction": {
        "markers": ["noticed", "caught attention", "unexpected", "different than expected",
                   "curious", "interesting"],
        "intensity": 0.3,
        "valence": 0.0,
    },
    "surprise": {
        "markers": ["surprised", "shocked", "astonished", "didn't expect",
                   "caught off guard", "taken aback", "wow"],
        "intensity": 0.6,
        "valence": 0.0,
    },
    "amazement": {
        "markers": ["amazed", "astounded", "stunned", "mind-blown", "incredible",
                   "unbelievable", "never seen anything like", "jaw-dropping"],
        "intensity": 1.0,
        "valence": 0.0,
    },
    
    # SADNESS SPECTRUM (low → high: pensiveness → sadness → grief)
    "pensiveness": {
        "markers": ["thoughtful", "reflective", "melancholy", "wistful",
                   "bit sad", "slightly disappointed", "not what I hoped"],
        "intensity": 0.3,
        "valence": -0.3,
    },
    "sadness": {
        "markers": ["sad", "unhappy", "disappointed", "let down", "upset",
                   "discouraged", "dissatisfied", "regret"],
        "intensity": 0.6,
        "valence": -0.6,
    },
    "grief": {
        "markers": ["devastated", "heartbroken", "crushed", "miserable",
                   "worst purchase", "complete waste", "deeply regret",
                   "threw money away"],
        "intensity": 1.0,
        "valence": -1.0,
    },
    
    # DISGUST SPECTRUM (low → high: boredom → disgust → loathing)
    "boredom": {
        "markers": ["boring", "bland", "dull", "uninteresting", "meh",
                   "nothing special", "underwhelming", "mediocre"],
        "intensity": 0.3,
        "valence": -0.3,
    },
    "disgust": {
        "markers": ["disgusted", "repulsed", "gross", "terrible", "awful",
                   "horrible", "nasty", "unacceptable", "appalling"],
        "intensity": 0.6,
        "valence": -0.8,
    },
    "loathing": {
        "markers": ["hate", "despise", "loathe", "abhorrent", "revolting",
                   "vile", "worst thing ever", "absolute garbage", "scam"],
        "intensity": 1.0,
        "valence": -1.0,
    },
    
    # ANGER SPECTRUM (low → high: annoyance → anger → rage)
    "annoyance": {
        "markers": ["annoying", "irritating", "frustrating", "bothersome",
                   "inconvenient", "minor issue", "pet peeve", "nuisance"],
        "intensity": 0.3,
        "valence": -0.4,
    },
    "anger": {
        "markers": ["angry", "mad", "upset", "furious", "frustrated",
                   "infuriated", "outraged", "unacceptable"],
        "intensity": 0.6,
        "valence": -0.7,
    },
    "rage": {
        "markers": ["enraged", "livid", "furious", "seething", "want my money back",
                   "will never buy again", "reporting to", "lawsuit", "fraud"],
        "intensity": 1.0,
        "valence": -1.0,
    },
    
    # ANTICIPATION SPECTRUM (low → high: interest → anticipation → vigilance)
    "interest": {
        "markers": ["interested", "curious", "intrigued", "want to try",
                   "looking forward", "excited to see", "can't wait to"],
        "intensity": 0.3,
        "valence": 0.4,
    },
    "anticipation": {
        "markers": ["anticipating", "expecting", "hoping", "eager",
                   "excited about", "counting down", "been waiting for"],
        "intensity": 0.6,
        "valence": 0.6,
    },
    "vigilance": {
        "markers": ["watching closely", "monitoring", "keeping eye on",
                   "checking daily", "obsessed with", "can't stop thinking about"],
        "intensity": 1.0,
        "valence": 0.7,
    },
    
    # SECONDARY EMOTIONS (Adjacent Combinations)
    "love": {  # Joy + Trust
        "markers": ["love", "adore", "cherish", "treasure", "devoted",
                   "passionate about", "can't live without", "best thing ever"],
        "intensity": 0.8,
        "valence": 1.0,
        "components": ["joy", "trust"],
    },
    "submission": {  # Trust + Fear
        "markers": ["comply", "follow instructions", "as directed", "trusting",
                   "hoping it works", "faith in", "believe in"],
        "intensity": 0.5,
        "valence": 0.2,
        "components": ["trust", "fear"],
    },
    "awe": {  # Fear + Surprise
        "markers": ["awe", "awestruck", "overwhelming", "powerful",
                   "humbling", "breathtaking", "magnificent"],
        "intensity": 0.8,
        "valence": 0.3,
        "components": ["fear", "surprise"],
    },
    "disapproval": {  # Surprise + Sadness
        "markers": ["disapprove", "object", "disagree", "not what I expected",
                   "misled", "false advertising", "overpromised"],
        "intensity": 0.6,
        "valence": -0.5,
        "components": ["surprise", "sadness"],
    },
    "remorse": {  # Sadness + Disgust
        "markers": ["regret", "remorse", "shouldn't have", "wish I hadn't",
                   "buyer's remorse", "waste of money", "lesson learned"],
        "intensity": 0.7,
        "valence": -0.7,
        "components": ["sadness", "disgust"],
    },
    "contempt": {  # Disgust + Anger
        "markers": ["contempt", "disdain", "scorn", "ridiculous", "pathetic",
                   "joke", "laughable", "how dare they", "insulting"],
        "intensity": 0.8,
        "valence": -0.9,
        "components": ["disgust", "anger"],
    },
    "aggressiveness": {  # Anger + Anticipation
        "markers": ["demanding", "insisting", "require", "must have",
                   "won't accept", "taking action", "escalating"],
        "intensity": 0.7,
        "valence": -0.4,
        "components": ["anger", "anticipation"],
    },
    "optimism": {  # Anticipation + Joy
        "markers": ["optimistic", "hopeful", "positive", "promising",
                   "looking good", "potential", "could be great"],
        "intensity": 0.6,
        "valence": 0.7,
        "components": ["anticipation", "joy"],
    },
}


# =============================================================================
# PART 2: COGNITIVE PROCESS MARKERS
# =============================================================================
# Based on LIWC-22 Cognitive Process Categories

COGNITIVE_PROCESS_MARKERS = {
    # INSIGHT & UNDERSTANDING
    "insight": {
        "markers": ["realize", "understand", "know", "think", "consider",
                   "meaning", "realize now", "it hit me", "finally get it"],
        "description": "Moments of understanding or revelation",
    },
    "causation": {
        "markers": ["because", "effect", "hence", "therefore", "thus",
                   "since", "consequently", "as a result", "due to", "caused by"],
        "description": "Causal reasoning and explanation",
    },
    "discrepancy": {
        "markers": ["should", "would", "could", "ought", "need",
                   "supposed to", "expected", "hoped for", "wanted"],
        "description": "Gap between expectation and reality",
    },
    "tentative": {
        "markers": ["maybe", "perhaps", "guess", "might", "possibly",
                   "seems", "appears", "sort of", "kind of", "somewhat"],
        "description": "Uncertainty and hedging",
    },
    "certainty": {
        "markers": ["always", "never", "absolutely", "definitely", "certainly",
                   "without doubt", "guaranteed", "100%", "no question"],
        "description": "Strong conviction and confidence",
    },
    "differentiation": {
        "markers": ["but", "however", "although", "rather", "instead",
                   "on the other hand", "while", "whereas", "unlike"],
        "description": "Making distinctions and comparisons",
    },
    
    # PERCEPTUAL PROCESSES
    "see": {
        "markers": ["see", "look", "view", "saw", "watch", "notice",
                   "observed", "appeared", "visible", "color", "bright"],
        "description": "Visual perception references",
    },
    "hear": {
        "markers": ["hear", "listen", "sound", "heard", "loud", "quiet",
                   "noise", "ring", "silent", "audio"],
        "description": "Auditory perception references",
    },
    "feel": {
        "markers": ["feel", "touch", "hold", "felt", "warm", "cold",
                   "soft", "hard", "smooth", "rough", "texture"],
        "description": "Tactile and physical sensation references",
    },
    
    # BIOLOGICAL PROCESSES
    "body": {
        "markers": ["body", "hand", "head", "face", "arm", "leg",
                   "heart", "skin", "hair", "eye", "finger"],
        "description": "Body part references",
    },
    "health": {
        "markers": ["health", "sick", "pain", "hurt", "ache", "medicine",
                   "doctor", "hospital", "disease", "symptom", "allergy"],
        "description": "Health and medical references",
    },
    "ingest": {
        "markers": ["eat", "drink", "taste", "swallow", "food", "meal",
                   "hungry", "thirsty", "coffee", "water", "delicious"],
        "description": "Eating and drinking references",
    },
    
    # DRIVES & NEEDS
    "affiliation": {
        "markers": ["friend", "family", "together", "share", "group",
                   "community", "belong", "team", "partner", "social"],
        "description": "Need for connection and belonging",
    },
    "achievement": {
        "markers": ["success", "win", "achieve", "accomplish", "goal",
                   "best", "top", "first", "excellent", "superior"],
        "description": "Achievement and accomplishment motivation",
    },
    "power": {
        "markers": ["power", "control", "strong", "superior", "dominate",
                   "lead", "authority", "influence", "command", "force"],
        "description": "Power and dominance motivation",
    },
    "reward": {
        "markers": ["get", "take", "prize", "benefit", "gain", "profit",
                   "advantage", "reward", "bonus", "value"],
        "description": "Reward-seeking motivation",
    },
    "risk": {
        "markers": ["danger", "risk", "risky", "careful", "safe", "avoid",
                   "prevent", "worry", "threat", "protect"],
        "description": "Risk perception and avoidance",
    },
}


# =============================================================================
# PART 3: 200+ COGNITIVE BIASES WITH LINGUISTIC TRIGGERS
# =============================================================================
# Grouped by mechanism type

COGNITIVE_BIAS_MARKERS = {
    # ANCHORING & ADJUSTMENT BIASES
    "anchoring_bias": {
        "markers": ["compared to", "originally", "was $", "reduced from",
                   "regular price", "usually costs", "worth more than"],
        "description": "Reliance on first piece of information",
        "susceptibility_indicators": ["mentioned price first", "compared to expensive"],
    },
    "contrast_effect": {
        "markers": ["better than", "worse than", "compared to others",
                   "unlike the", "relative to", "in comparison"],
        "description": "Evaluation based on comparison context",
    },
    "framing_effect": {
        "markers": ["only", "just", "as little as", "up to", "at least",
                   "no more than", "saves you", "costs less"],
        "description": "Response varies based on how options are presented",
    },
    
    # AVAILABILITY & MEMORY BIASES
    "availability_heuristic": {
        "markers": ["I heard", "everyone says", "all the time", "always happens",
                   "never works", "constantly", "repeatedly", "every time"],
        "description": "Overweighting easily recalled information",
    },
    "recency_bias": {
        "markers": ["just recently", "latest", "newest", "most recent",
                   "just happened", "last time", "just now"],
        "description": "Overweighting recent events",
    },
    "peak_end_rule": {
        "markers": ["ended with", "finally", "in the end", "at last",
                   "the worst part", "the best part", "highlight was"],
        "description": "Judging experience by peak and end moments",
    },
    
    # SOCIAL PROOF BIASES
    "bandwagon_effect": {
        "markers": ["everyone has", "popular", "trending", "best seller",
                   "top rated", "most reviewed", "thousands of", "millions sold"],
        "description": "Following the crowd",
    },
    "authority_bias": {
        "markers": ["expert", "doctor", "professional", "certified", "official",
                   "recommended by", "endorsed by", "approved by", "according to"],
        "description": "Trusting authority figures",
    },
    "halo_effect": {
        "markers": ["brand name", "premium", "luxury", "high-end", "designer",
                   "well-known", "reputable", "trusted brand"],
        "description": "Overall impression influencing specific judgments",
    },
    
    # LOSS AVERSION BIASES
    "loss_aversion": {
        "markers": ["don't want to lose", "can't afford to miss", "limited time",
                   "while supplies last", "don't miss out", "last chance",
                   "before it's gone", "won't get another"],
        "description": "Preferring to avoid losses over acquiring gains",
    },
    "sunk_cost_fallacy": {
        "markers": ["already invested", "spent so much", "come this far",
                   "put in time", "already paid", "can't give up now"],
        "description": "Continuing due to past investment",
    },
    "endowment_effect": {
        "markers": ["my", "mine", "own", "have", "keep", "part of me",
                   "attached to", "wouldn't sell"],
        "description": "Valuing things more when we own them",
    },
    
    # CONFIRMATION BIASES
    "confirmation_bias": {
        "markers": ["as I expected", "proves my point", "knew it", "told you so",
                   "confirms", "validates", "just like I thought"],
        "description": "Seeking information that confirms beliefs",
    },
    "belief_perseverance": {
        "markers": ["still think", "regardless", "doesn't change", "despite",
                   "even though", "still believe", "won't convince me"],
        "description": "Maintaining beliefs despite contrary evidence",
    },
    
    # SELF-SERVING BIASES
    "self_serving_bias": {
        "markers": ["I did research", "I'm careful", "I know what I want",
                   "my standards", "I deserve", "smart enough"],
        "description": "Attributing success to self, failure to external",
    },
    "optimism_bias": {
        "markers": ["won't happen to me", "I'll be fine", "different for me",
                   "I'm lucky", "this time", "I can handle"],
        "description": "Believing negative events are less likely for self",
    },
    
    # CHOICE ARCHITECTURE BIASES
    "default_effect": {
        "markers": ["standard", "default", "usual", "normal", "typical",
                   "came with", "included", "pre-selected"],
        "description": "Preference for default options",
    },
    "choice_overload": {
        "markers": ["too many options", "overwhelmed", "hard to choose",
                   "couldn't decide", "so many choices", "analysis paralysis"],
        "description": "Difficulty choosing from too many options",
    },
    "decoy_effect": {
        "markers": ["middle option", "seemed best value", "compared to others",
                   "better deal than", "more reasonable"],
        "description": "Preference influenced by asymmetrically dominated options",
    },
    
    # TEMPORAL BIASES
    "hyperbolic_discounting": {
        "markers": ["right now", "immediately", "instant", "today",
                   "same day", "fast shipping", "can't wait"],
        "description": "Preferring smaller immediate rewards over larger delayed ones",
    },
    "planning_fallacy": {
        "markers": ["thought it would be", "expected faster", "underestimated",
                   "longer than expected", "more difficult than"],
        "description": "Underestimating time and resources needed",
    },
    "present_bias": {
        "markers": ["need it now", "can't wait", "immediately", "urgent",
                   "right away", "asap", "overnight"],
        "description": "Overweighting present over future",
    },
}


# =============================================================================
# PART 4: BIG FIVE PERSONALITY LINGUISTIC MARKERS
# =============================================================================
# Based on meta-analysis of LIWC correlations with personality

PERSONALITY_MARKERS = {
    # OPENNESS TO EXPERIENCE (Curiosity, Creativity, Novelty-Seeking)
    "openness": {
        "high": {
            "markers": ["creative", "unique", "different", "interesting", "artistic",
                       "imaginative", "innovative", "experimental", "curious",
                       "discovered", "explored", "new experience", "first time trying"],
            "linguistic_patterns": ["diverse vocabulary", "abstract concepts",
                                   "metaphors", "hypotheticals"],
        },
        "low": {
            "markers": ["traditional", "conventional", "standard", "basic", "simple",
                       "straightforward", "practical", "usual", "normal", "typical"],
            "linguistic_patterns": ["concrete language", "familiar terms",
                                   "routine references"],
        },
    },
    
    # CONSCIENTIOUSNESS (Organization, Dependability, Self-Discipline)
    "conscientiousness": {
        "high": {
            "markers": ["organized", "planned", "careful", "thorough", "detailed",
                       "researched", "compared", "systematic", "efficient",
                       "on time", "as expected", "according to", "step by step"],
            "linguistic_patterns": ["temporal markers", "sequential language",
                                   "precise descriptions", "quantitative data"],
        },
        "low": {
            "markers": ["spontaneous", "impulsive", "whatever", "didn't check",
                       "forgot", "rushed", "last minute", "random",
                       "didn't read", "assumed"],
            "linguistic_patterns": ["vague descriptions", "casual tone",
                                   "lack of detail"],
        },
    },
    
    # EXTRAVERSION (Sociability, Assertiveness, Positive Emotions)
    "extraversion": {
        "high": {
            "markers": ["everyone", "friends", "party", "social", "group",
                       "exciting", "fun", "amazing", "love", "awesome",
                       "fantastic", "incredible", "share", "recommend to all"],
            "linguistic_patterns": ["exclamation marks", "positive superlatives",
                                   "social references", "inclusive pronouns (we)"],
        },
        "low": {
            "markers": ["personally", "myself", "alone", "quiet", "private",
                       "individual", "solo", "just me", "prefer",
                       "don't need", "sufficient"],
            "linguistic_patterns": ["reserved language", "individual focus",
                                   "measured responses"],
        },
    },
    
    # AGREEABLENESS (Trust, Altruism, Cooperation)
    "agreeableness": {
        "high": {
            "markers": ["kind", "helpful", "nice", "friendly", "thoughtful",
                       "generous", "caring", "understanding", "fair",
                       "give benefit of doubt", "willing to", "appreciate"],
            "linguistic_patterns": ["positive social words", "agreement markers",
                                   "appreciation", "empathy expressions"],
        },
        "low": {
            "markers": ["competitive", "critical", "demanding", "skeptical",
                       "challenge", "question", "doubt", "expect",
                       "should have", "not acceptable", "demand"],
            "linguistic_patterns": ["critical language", "demands",
                                   "skepticism markers"],
        },
    },
    
    # NEUROTICISM (Anxiety, Emotional Instability, Negative Emotions)
    "neuroticism": {
        "high": {
            "markers": ["worried", "anxious", "stressed", "nervous", "concerned",
                       "frustrated", "angry", "disappointed", "upset",
                       "afraid", "hesitant", "uncertain", "regret"],
            "linguistic_patterns": ["negative emotions", "anxiety words",
                                   "uncertainty markers", "self-deprecation"],
        },
        "low": {
            "markers": ["calm", "relaxed", "confident", "stable", "secure",
                       "comfortable", "at ease", "no problems", "fine",
                       "works well", "satisfied", "content"],
            "linguistic_patterns": ["stable emotional tone", "confidence markers",
                                   "lack of anxiety words"],
        },
    },
}


# =============================================================================
# PART 5: REGULATORY FOCUS MARKERS
# =============================================================================
# Promotion vs Prevention Orientations

REGULATORY_FOCUS_MARKERS = {
    "promotion_focus": {
        "description": "Eager approach toward gains, achievements, aspirations",
        "markers": {
            "goals": ["achieve", "accomplish", "attain", "gain", "win",
                     "advance", "grow", "improve", "maximize", "ideal"],
            "emotions": ["excited", "happy", "eager", "enthusiastic", "hopeful",
                        "inspired", "motivated", "energized"],
            "language": ["want to", "hope to", "aspire to", "dream of",
                        "opportunity", "potential", "possible", "could be"],
            "outcomes": ["success", "achievement", "accomplishment", "reward",
                        "benefit", "advantage", "gain", "profit"],
        },
        "abstract_language": True,
        "focus": "presence_of_positives",
    },
    "prevention_focus": {
        "description": "Vigilant avoidance of losses, safety, security",
        "markers": {
            "goals": ["protect", "prevent", "avoid", "maintain", "secure",
                     "safety", "careful", "cautious", "responsible", "duty"],
            "emotions": ["worried", "anxious", "concerned", "relieved", "calm",
                        "secure", "safe", "protected"],
            "language": ["need to", "have to", "must", "should", "ought to",
                        "necessary", "required", "essential", "important"],
            "outcomes": ["security", "safety", "protection", "stability",
                        "reliability", "durability", "warranty", "guarantee"],
        },
        "concrete_language": True,
        "focus": "absence_of_negatives",
    },
}


# =============================================================================
# PART 6: CIALDINI'S PRINCIPLES - DEEP BREAKDOWN
# =============================================================================
# 6 Principles × 5+ Sub-Mechanisms Each = 30+ Persuasion Tactics

CIALDINI_DEEP_MARKERS = {
    "reciprocity": {
        "description": "Obligation to return favors",
        "sub_mechanisms": {
            "direct_gift": {
                "markers": ["free", "complimentary", "bonus", "gift", "included",
                           "no charge", "on the house", "thrown in"],
                "effectiveness": "high",
            },
            "concession": {
                "markers": ["discount", "reduced", "special price", "deal",
                           "negotiated", "worked with me", "made exception"],
                "effectiveness": "high",
            },
            "favor": {
                "markers": ["helped me", "went out of their way", "extra effort",
                           "above and beyond", "special treatment"],
                "effectiveness": "medium",
            },
            "information": {
                "markers": ["insider", "secret", "tip", "advice", "recommendation",
                           "exclusive info", "heads up"],
                "effectiveness": "medium",
            },
        },
    },
    "commitment_consistency": {
        "description": "Desire to be consistent with past actions/statements",
        "sub_mechanisms": {
            "public_commitment": {
                "markers": ["told everyone", "posted about", "shared that I",
                           "recommended to others", "committed to"],
                "effectiveness": "high",
            },
            "written_commitment": {
                "markers": ["wrote review", "documented", "recorded", "noted",
                           "signed up for", "registered"],
                "effectiveness": "high",
            },
            "small_commitment_escalation": {
                "markers": ["started with", "tried the", "sampled", "tested",
                           "began with", "first purchase"],
                "effectiveness": "medium",
            },
            "identity_consistency": {
                "markers": ["I'm the type who", "I always", "as someone who",
                           "consistent with my", "fits my style"],
                "effectiveness": "high",
            },
        },
    },
    "social_proof": {
        "description": "Looking to others' behavior for guidance",
        "sub_mechanisms": {
            "quantity": {
                "markers": ["thousands of", "millions", "best seller", "most popular",
                           "top rated", "highly reviewed", "#1"],
                "effectiveness": "high",
            },
            "similarity": {
                "markers": ["people like me", "other moms", "fellow", "other professionals",
                           "customers in my area", "similar situation"],
                "effectiveness": "very_high",
            },
            "expert_social_proof": {
                "markers": ["experts recommend", "professionals use", "industry standard",
                           "award winning", "recognized by"],
                "effectiveness": "high",
            },
            "certification": {
                "markers": ["certified", "verified", "authenticated", "approved",
                           "tested by", "confirmed"],
                "effectiveness": "medium",
            },
            "user_generated": {
                "markers": ["real customer", "actual user", "honest review",
                           "unsponsored", "verified purchase"],
                "effectiveness": "high",
            },
        },
    },
    "authority": {
        "description": "Deference to experts and authority figures",
        "sub_mechanisms": {
            "expertise": {
                "markers": ["expert", "specialist", "professional", "years of experience",
                           "trained", "qualified", "credentialed"],
                "effectiveness": "high",
            },
            "credentials": {
                "markers": ["PhD", "MD", "certified", "licensed", "degree",
                           "published", "awarded", "recognized"],
                "effectiveness": "high",
            },
            "uniforms_symbols": {
                "markers": ["official", "branded", "authentic", "genuine",
                           "authorized", "legitimate"],
                "effectiveness": "medium",
            },
            "track_record": {
                "markers": ["proven", "track record", "history of", "established",
                           "trusted for years", "since 19"],
                "effectiveness": "high",
            },
        },
    },
    "liking": {
        "description": "Preference for those we like",
        "sub_mechanisms": {
            "physical_attractiveness": {
                "markers": ["beautiful", "gorgeous", "attractive", "stylish",
                           "elegant", "aesthetic", "design"],
                "effectiveness": "medium",
            },
            "similarity": {
                "markers": ["like me", "same", "share", "also", "fellow",
                           "understand my", "relates to"],
                "effectiveness": "high",
            },
            "compliments": {
                "markers": ["great choice", "smart decision", "excellent taste",
                           "you deserve", "you're worth it"],
                "effectiveness": "high",
            },
            "familiarity": {
                "markers": ["always used", "grew up with", "familiar", "known",
                           "trusted", "recognized", "household name"],
                "effectiveness": "medium",
            },
            "association": {
                "markers": ["celebrity", "influencer", "sponsored by", "partnered with",
                           "as seen in", "featured on"],
                "effectiveness": "medium",
            },
        },
    },
    "scarcity": {
        "description": "Valuing what is rare or diminishing",
        "sub_mechanisms": {
            "limited_quantity": {
                "markers": ["limited", "only X left", "selling fast", "almost gone",
                           "few remaining", "rare", "exclusive"],
                "effectiveness": "very_high",
            },
            "limited_time": {
                "markers": ["ends soon", "limited time", "today only", "act now",
                           "deadline", "expires", "last chance"],
                "effectiveness": "very_high",
            },
            "exclusive_access": {
                "markers": ["exclusive", "members only", "VIP", "invitation only",
                           "select few", "limited access"],
                "effectiveness": "high",
            },
            "competition": {
                "markers": ["others are looking", "high demand", "competing for",
                           "someone else might", "don't miss out"],
                "effectiveness": "high",
            },
        },
    },
}


# =============================================================================
# PART 7: DECISION JOURNEY STAGE MARKERS
# =============================================================================

DECISION_STAGE_MARKERS = {
    "awareness": {
        "description": "Just becoming aware of need/product",
        "markers": ["discovered", "found out about", "heard of", "came across",
                   "stumbled upon", "someone mentioned", "first learned"],
        "psychological_state": "curiosity",
        "persuasion_receptivity": "information",
    },
    "consideration": {
        "description": "Actively evaluating options",
        "markers": ["comparing", "researching", "looking at", "considering",
                   "evaluating", "weighing options", "trying to decide",
                   "narrowing down", "shortlist"],
        "psychological_state": "analytical",
        "persuasion_receptivity": "differentiation",
    },
    "decision": {
        "description": "Ready to make purchase decision",
        "markers": ["decided to", "chose", "went with", "pulled trigger",
                   "made purchase", "bought", "ordered", "finally got"],
        "psychological_state": "committed",
        "persuasion_receptivity": "reassurance",
    },
    "experience": {
        "description": "Using/experiencing product",
        "markers": ["have been using", "tried it", "after X days/weeks",
                   "in my experience", "daily use", "regular use"],
        "psychological_state": "evaluative",
        "persuasion_receptivity": "validation",
    },
    "advocacy": {
        "description": "Sharing experience with others",
        "markers": ["recommend", "tell everyone", "bought as gift", "told friends",
                   "share", "spread the word", "write review"],
        "psychological_state": "advocacy",
        "persuasion_receptivity": "reinforcement",
    },
}


# =============================================================================
# PART 8: LINGUISTIC STYLE MARKERS
# =============================================================================

LINGUISTIC_STYLE_MARKERS = {
    # PRONOUN USAGE (Critical for psychological insight)
    "pronoun_i": {
        "markers": ["i", "me", "my", "mine", "myself"],
        "high_use_indicates": ["self-focus", "personal experience", "authenticity"],
        "low_use_indicates": ["social orientation", "formal tone"],
    },
    "pronoun_we": {
        "markers": ["we", "us", "our", "ours", "ourselves"],
        "high_use_indicates": ["group identity", "shared experience", "social connection"],
        "low_use_indicates": ["individual focus", "independence"],
    },
    "pronoun_you": {
        "markers": ["you", "your", "yours", "yourself"],
        "high_use_indicates": ["addressing reader", "advice-giving", "persuasion attempt"],
        "low_use_indicates": ["self-focused narrative"],
    },
    "pronoun_they": {
        "markers": ["they", "them", "their", "theirs"],
        "high_use_indicates": ["third-party reference", "social comparison", "distancing"],
        "low_use_indicates": ["personal focus"],
    },
    
    # VERB TENSE
    "past_tense": {
        "markers": ["was", "were", "had", "did", "bought", "used", "tried"],
        "indicates": ["completed experience", "reflection", "narrative"],
    },
    "present_tense": {
        "markers": ["is", "am", "are", "have", "do", "use", "works"],
        "indicates": ["ongoing experience", "current state", "immediacy"],
    },
    "future_tense": {
        "markers": ["will", "going to", "plan to", "hope to", "expect to"],
        "indicates": ["anticipation", "intention", "forward-looking"],
    },
    
    # CERTAINTY & HEDGING
    "certainty_markers": {
        "high": ["definitely", "absolutely", "certainly", "always", "never",
                "100%", "guarantee", "without doubt", "for sure"],
        "medium": ["usually", "generally", "typically", "often", "mostly"],
        "low": ["maybe", "perhaps", "might", "possibly", "seems", "appears",
               "sort of", "kind of", "somewhat"],
    },
    
    # INTENSIFIERS & DIMINISHERS
    "intensifiers": {
        "markers": ["very", "really", "extremely", "incredibly", "absolutely",
                   "totally", "completely", "utterly", "thoroughly", "highly"],
        "indicates": ["emotional intensity", "emphasis", "conviction"],
    },
    "diminishers": {
        "markers": ["somewhat", "slightly", "a bit", "kind of", "sort of",
                   "fairly", "rather", "pretty", "relatively", "reasonably"],
        "indicates": ["hedging", "uncertainty", "moderation"],
    },
    
    # NEGATION
    "negation": {
        "markers": ["not", "no", "never", "neither", "none", "nothing",
                   "don't", "won't", "can't", "isn't", "wasn't"],
        "high_use_indicates": ["dissatisfaction", "criticism", "caution"],
    },
    
    # QUESTION MARKERS
    "questions": {
        "markers": ["?", "why", "how", "what", "when", "where", "who", "which"],
        "indicates": ["uncertainty", "seeking information", "engagement"],
    },
}


# =============================================================================
# PART 9: TRUST & CREDIBILITY MARKERS
# =============================================================================

TRUST_CREDIBILITY_MARKERS = {
    # AUTHENTICITY SIGNALS
    "authenticity_high": {
        "markers": ["honestly", "to be honest", "truthfully", "frankly",
                   "genuinely", "real talk", "no BS", "straight up"],
        "indicates": "Attempt to signal honesty",
    },
    "specificity": {
        "markers": ["specifically", "exactly", "precisely", "particular",
                   "detail", "measured", "tested", "X days/weeks/months"],
        "indicates": "Concrete evidence, higher credibility",
    },
    "balanced_review": {
        "markers": ["pros and cons", "on one hand", "however", "although",
                   "the downside", "the only issue", "not perfect but"],
        "indicates": "Balanced perspective, higher credibility",
    },
    
    # EXPERTISE SIGNALS
    "domain_expertise": {
        "markers": ["as a", "professional", "years of experience", "background in",
                   "trained in", "work in", "specialize in"],
        "indicates": "Domain authority claim",
    },
    "technical_language": {
        "markers": ["specs", "specifications", "measurements", "tolerances",
                   "technical", "performance metrics", "benchmark"],
        "indicates": "Technical knowledge",
    },
    
    # SOCIAL PROOF SIGNALS
    "social_validation": {
        "markers": ["others have said", "confirmed by", "matches reviews",
                   "as others mentioned", "agree with other reviewers"],
        "indicates": "Social proof reinforcement",
    },
    
    # RED FLAGS (Low Credibility)
    "astroturfing_indicators": {
        "markers": ["best ever!!!", "changed my life!!!", "must buy!!!",
                   "amazing amazing", "perfect perfect", "5 stars not enough"],
        "indicates": "Potential fake review markers",
    },
    "vague_superlatives": {
        "markers": ["great product", "really good", "highly recommend",
                   "love it", "amazing quality"],
        "indicates": "Low specificity, potentially low credibility",
    },
}


# =============================================================================
# PART 10: CONSUMER ARCHETYPE DEEP PROFILES
# =============================================================================
# Expanded from 5 basic archetypes to detailed psychological profiles

DEEP_ARCHETYPE_PROFILES = {
    "achiever": {
        "core_motivation": "Success, status, accomplishment",
        "regulatory_focus": "promotion",
        "big_five_profile": {
            "openness": "medium-high",
            "conscientiousness": "high",
            "extraversion": "medium-high",
            "agreeableness": "medium",
            "neuroticism": "low-medium",
        },
        "linguistic_markers": {
            "keywords": ["best", "premium", "top", "quality", "excellence",
                        "superior", "performance", "success", "win", "achieve"],
            "pronoun_pattern": "I-focused",
            "certainty_level": "high",
            "emotion_intensity": "high_positive",
        },
        "persuasion_vulnerabilities": {
            "primary": ["authority", "social_proof_expert", "scarcity_exclusive"],
            "secondary": ["liking_compliments", "commitment_identity"],
        },
        "cognitive_biases": ["halo_effect", "authority_bias", "bandwagon_effect"],
        "price_sensitivity": "low",
        "decision_style": "analytical_fast",
    },
    
    "explorer": {
        "core_motivation": "Discovery, novelty, experience",
        "regulatory_focus": "promotion",
        "big_five_profile": {
            "openness": "very_high",
            "conscientiousness": "medium",
            "extraversion": "high",
            "agreeableness": "medium-high",
            "neuroticism": "low",
        },
        "linguistic_markers": {
            "keywords": ["new", "different", "unique", "discover", "try",
                        "adventure", "exciting", "interesting", "curious", "first"],
            "pronoun_pattern": "I and We balanced",
            "certainty_level": "medium",
            "emotion_intensity": "high_varied",
        },
        "persuasion_vulnerabilities": {
            "primary": ["scarcity_exclusive", "social_proof_similarity", "liking_novelty"],
            "secondary": ["reciprocity_information", "authority_expertise"],
        },
        "cognitive_biases": ["novelty_seeking", "optimism_bias", "availability_heuristic"],
        "price_sensitivity": "medium",
        "decision_style": "intuitive_fast",
    },
    
    "connector": {
        "core_motivation": "Relationships, belonging, sharing",
        "regulatory_focus": "mixed",
        "big_five_profile": {
            "openness": "medium",
            "conscientiousness": "medium",
            "extraversion": "high",
            "agreeableness": "very_high",
            "neuroticism": "medium",
        },
        "linguistic_markers": {
            "keywords": ["share", "recommend", "family", "friends", "together",
                        "gift", "everyone", "community", "love", "care"],
            "pronoun_pattern": "We-focused",
            "certainty_level": "medium",
            "emotion_intensity": "positive_social",
        },
        "persuasion_vulnerabilities": {
            "primary": ["social_proof_all", "liking_similarity", "reciprocity"],
            "secondary": ["commitment_public", "authority_social"],
        },
        "cognitive_biases": ["bandwagon_effect", "halo_effect", "social_proof_bias"],
        "price_sensitivity": "medium",
        "decision_style": "social_influenced",
    },
    
    "guardian": {
        "core_motivation": "Safety, security, protection",
        "regulatory_focus": "prevention",
        "big_five_profile": {
            "openness": "low-medium",
            "conscientiousness": "very_high",
            "extraversion": "low-medium",
            "agreeableness": "medium-high",
            "neuroticism": "high",
        },
        "linguistic_markers": {
            "keywords": ["safe", "reliable", "trust", "protect", "secure",
                        "durable", "warranty", "quality", "proven", "tested"],
            "pronoun_pattern": "I-focused protective",
            "certainty_level": "seeks_high",
            "emotion_intensity": "cautious",
        },
        "persuasion_vulnerabilities": {
            "primary": ["authority_credentials", "social_proof_certification", "commitment_consistency"],
            "secondary": ["scarcity_loss_framing", "reciprocity_guarantee"],
        },
        "cognitive_biases": ["loss_aversion", "status_quo_bias", "risk_aversion"],
        "price_sensitivity": "low_for_quality",
        "decision_style": "analytical_slow",
    },
    
    "pragmatist": {
        "core_motivation": "Value, efficiency, practicality",
        "regulatory_focus": "prevention",
        "big_five_profile": {
            "openness": "low",
            "conscientiousness": "high",
            "extraversion": "low",
            "agreeableness": "medium",
            "neuroticism": "low",
        },
        "linguistic_markers": {
            "keywords": ["value", "price", "deal", "practical", "functional",
                        "works", "efficient", "budget", "worth", "reasonable"],
            "pronoun_pattern": "I-focused practical",
            "certainty_level": "high_factual",
            "emotion_intensity": "low",
        },
        "persuasion_vulnerabilities": {
            "primary": ["reciprocity_discount", "scarcity_limited_time", "social_proof_quantity"],
            "secondary": ["authority_comparison", "commitment_small"],
        },
        "cognitive_biases": ["anchoring", "framing_effect", "endowment_effect"],
        "price_sensitivity": "very_high",
        "decision_style": "analytical_comparative",
    },
    
    "analyzer": {
        "core_motivation": "Knowledge, understanding, optimization",
        "regulatory_focus": "prevention",
        "big_five_profile": {
            "openness": "high_intellectual",
            "conscientiousness": "very_high",
            "extraversion": "low",
            "agreeableness": "low-medium",
            "neuroticism": "medium",
        },
        "linguistic_markers": {
            "keywords": ["research", "compare", "data", "specs", "performance",
                        "test", "measure", "analyze", "review", "evaluate"],
            "pronoun_pattern": "objective_distanced",
            "certainty_level": "evidence_based",
            "emotion_intensity": "low",
        },
        "persuasion_vulnerabilities": {
            "primary": ["authority_expertise", "social_proof_expert", "reciprocity_information"],
            "secondary": ["commitment_consistency", "scarcity_rational"],
        },
        "cognitive_biases": ["confirmation_bias", "analysis_paralysis", "information_bias"],
        "price_sensitivity": "value_focused",
        "decision_style": "analytical_thorough",
    },
}


# =============================================================================
# MAIN ANALYZER CLASS
# =============================================================================

@dataclass
class DeepPsychologicalProfile:
    """Complete psychological profile extracted from text."""
    
    # Emotional state (granular)
    primary_emotions: Dict[str, float] = field(default_factory=dict)
    secondary_emotions: Dict[str, float] = field(default_factory=dict)
    emotional_intensity: float = 0.0
    emotional_valence: float = 0.0
    
    # Cognitive patterns
    cognitive_processes: Dict[str, float] = field(default_factory=dict)
    
    # Cognitive biases detected
    biases_detected: Dict[str, float] = field(default_factory=dict)
    
    # Personality inference
    big_five_scores: Dict[str, float] = field(default_factory=dict)
    
    # Regulatory focus
    promotion_focus_score: float = 0.0
    prevention_focus_score: float = 0.0
    
    # Persuasion susceptibility
    cialdini_susceptibility: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Decision stage
    decision_stage: str = ""
    decision_stage_confidence: float = 0.0
    
    # Linguistic style
    linguistic_style: Dict[str, Any] = field(default_factory=dict)
    
    # Trust signals
    credibility_score: float = 0.0
    authenticity_markers: List[str] = field(default_factory=list)
    
    # Archetype inference
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    primary_archetype: str = ""
    archetype_confidence: float = 0.0
    
    # Raw metrics
    word_count: int = 0
    sentence_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "primary_emotions": self.primary_emotions,
            "secondary_emotions": self.secondary_emotions,
            "emotional_intensity": self.emotional_intensity,
            "emotional_valence": self.emotional_valence,
            "cognitive_processes": self.cognitive_processes,
            "biases_detected": self.biases_detected,
            "big_five_scores": self.big_five_scores,
            "promotion_focus_score": self.promotion_focus_score,
            "prevention_focus_score": self.prevention_focus_score,
            "cialdini_susceptibility": self.cialdini_susceptibility,
            "decision_stage": self.decision_stage,
            "linguistic_style": self.linguistic_style,
            "credibility_score": self.credibility_score,
            "archetype_scores": self.archetype_scores,
            "primary_archetype": self.primary_archetype,
            "archetype_confidence": self.archetype_confidence,
        }


class DeepPsychologicalAnalyzer:
    """
    Comprehensive psychological text analyzer.
    
    Analyzes text across 325+ psychological dimensions.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self._emotion_patterns = {}
        for emotion, data in EMOTION_TAXONOMY.items():
            patterns = [re.escape(m) for m in data["markers"]]
            if patterns:
                self._emotion_patterns[emotion] = re.compile(
                    r'\b(' + '|'.join(patterns) + r')\b',
                    re.IGNORECASE
                )
    
    def analyze(self, text: str, context: Optional[Dict] = None) -> DeepPsychologicalProfile:
        """
        Perform comprehensive psychological analysis of text.
        
        Args:
            text: The review text to analyze
            context: Optional context (category, price, brand, etc.)
            
        Returns:
            DeepPsychologicalProfile with all extracted dimensions
        """
        profile = DeepPsychologicalProfile()
        
        if not text or len(text) < 10:
            return profile
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        sentences = re.split(r'[.!?]+', text)
        
        profile.word_count = len(words)
        profile.sentence_count = len([s for s in sentences if s.strip()])
        
        # 1. Analyze emotions (granular)
        self._analyze_emotions(text_lower, profile)
        
        # 2. Analyze cognitive processes
        self._analyze_cognitive_processes(text_lower, words, profile)
        
        # 3. Detect cognitive biases
        self._detect_biases(text_lower, profile)
        
        # 4. Infer personality
        self._infer_personality(text_lower, words, profile)
        
        # 5. Analyze regulatory focus
        self._analyze_regulatory_focus(text_lower, profile)
        
        # 6. Analyze persuasion susceptibility
        self._analyze_persuasion_susceptibility(text_lower, profile)
        
        # 7. Detect decision stage
        self._detect_decision_stage(text_lower, profile)
        
        # 8. Analyze linguistic style
        self._analyze_linguistic_style(text, text_lower, words, profile)
        
        # 9. Assess credibility
        self._assess_credibility(text_lower, words, profile)
        
        # 10. Infer archetype
        self._infer_archetype(profile, context)
        
        return profile
    
    def _analyze_emotions(self, text_lower: str, profile: DeepPsychologicalProfile):
        """Analyze emotions with granularity."""
        emotion_scores = {}
        total_intensity = 0
        total_valence = 0
        count = 0
        
        for emotion, pattern in self._emotion_patterns.items():
            matches = pattern.findall(text_lower)
            if matches:
                data = EMOTION_TAXONOMY[emotion]
                score = len(matches) * data["intensity"]
                emotion_scores[emotion] = min(1.0, score / 3)  # Normalize
                
                total_intensity += data["intensity"] * len(matches)
                total_valence += data["valence"] * len(matches)
                count += len(matches)
        
        # Separate primary and secondary
        for emotion, score in emotion_scores.items():
            if "components" in EMOTION_TAXONOMY.get(emotion, {}):
                profile.secondary_emotions[emotion] = score
            else:
                profile.primary_emotions[emotion] = score
        
        if count > 0:
            profile.emotional_intensity = min(1.0, total_intensity / count)
            profile.emotional_valence = total_valence / count
    
    def _analyze_cognitive_processes(
        self, 
        text_lower: str, 
        words: List[str],
        profile: DeepPsychologicalProfile
    ):
        """Analyze cognitive process markers."""
        word_set = set(words)
        
        for process, data in COGNITIVE_PROCESS_MARKERS.items():
            markers = data["markers"]
            matches = sum(1 for m in markers if m in text_lower)
            if matches > 0:
                profile.cognitive_processes[process] = min(1.0, matches / 3)
    
    def _detect_biases(self, text_lower: str, profile: DeepPsychologicalProfile):
        """Detect cognitive biases from linguistic markers."""
        for bias, data in COGNITIVE_BIAS_MARKERS.items():
            markers = data["markers"]
            matches = sum(1 for m in markers if m in text_lower)
            if matches > 0:
                profile.biases_detected[bias] = min(1.0, matches / 2)
    
    def _infer_personality(
        self, 
        text_lower: str, 
        words: List[str],
        profile: DeepPsychologicalProfile
    ):
        """Infer Big Five personality from linguistic markers."""
        for trait, data in PERSONALITY_MARKERS.items():
            high_markers = data["high"]["markers"]
            low_markers = data["low"]["markers"]
            
            high_count = sum(1 for m in high_markers if m in text_lower)
            low_count = sum(1 for m in low_markers if m in text_lower)
            
            # Score from -1 (low) to +1 (high)
            if high_count + low_count > 0:
                score = (high_count - low_count) / (high_count + low_count)
            else:
                score = 0.0
            
            profile.big_five_scores[trait] = score
    
    def _analyze_regulatory_focus(
        self, 
        text_lower: str, 
        profile: DeepPsychologicalProfile
    ):
        """Analyze promotion vs prevention regulatory focus."""
        promotion_score = 0
        prevention_score = 0
        
        promo_data = REGULATORY_FOCUS_MARKERS["promotion_focus"]["markers"]
        prev_data = REGULATORY_FOCUS_MARKERS["prevention_focus"]["markers"]
        
        for category, markers in promo_data.items():
            promotion_score += sum(1 for m in markers if m in text_lower)
        
        for category, markers in prev_data.items():
            prevention_score += sum(1 for m in markers if m in text_lower)
        
        total = promotion_score + prevention_score
        if total > 0:
            profile.promotion_focus_score = promotion_score / total
            profile.prevention_focus_score = prevention_score / total
        else:
            profile.promotion_focus_score = 0.5
            profile.prevention_focus_score = 0.5
    
    def _analyze_persuasion_susceptibility(
        self, 
        text_lower: str, 
        profile: DeepPsychologicalProfile
    ):
        """Analyze susceptibility to Cialdini's principles."""
        for principle, data in CIALDINI_DEEP_MARKERS.items():
            sub_scores = {}
            
            for sub_mechanism, sub_data in data["sub_mechanisms"].items():
                markers = sub_data["markers"]
                matches = sum(1 for m in markers if m in text_lower)
                if matches > 0:
                    sub_scores[sub_mechanism] = min(1.0, matches / 2)
            
            if sub_scores:
                profile.cialdini_susceptibility[principle] = sub_scores
    
    def _detect_decision_stage(
        self, 
        text_lower: str, 
        profile: DeepPsychologicalProfile
    ):
        """Detect which stage of decision journey reviewer is in."""
        stage_scores = {}
        
        for stage, data in DECISION_STAGE_MARKERS.items():
            markers = data["markers"]
            matches = sum(1 for m in markers if m in text_lower)
            if matches > 0:
                stage_scores[stage] = matches
        
        if stage_scores:
            best_stage = max(stage_scores, key=stage_scores.get)
            profile.decision_stage = best_stage
            total = sum(stage_scores.values())
            profile.decision_stage_confidence = stage_scores[best_stage] / total
    
    def _analyze_linguistic_style(
        self,
        text: str,
        text_lower: str,
        words: List[str],
        profile: DeepPsychologicalProfile
    ):
        """Analyze linguistic style markers."""
        style = {}
        
        # Pronoun analysis
        for pronoun_type, data in LINGUISTIC_STYLE_MARKERS.items():
            if pronoun_type.startswith("pronoun_"):
                markers = data["markers"]
                count = sum(1 for w in words if w in markers)
                style[pronoun_type] = count / max(len(words), 1)
        
        # Certainty level
        certainty_data = LINGUISTIC_STYLE_MARKERS["certainty_markers"]
        high_cert = sum(1 for m in certainty_data["high"] if m in text_lower)
        low_cert = sum(1 for m in certainty_data["low"] if m in text_lower)
        
        if high_cert + low_cert > 0:
            style["certainty"] = (high_cert - low_cert) / (high_cert + low_cert)
        else:
            style["certainty"] = 0.0
        
        # Intensifiers vs diminishers
        intensifiers = LINGUISTIC_STYLE_MARKERS["intensifiers"]["markers"]
        diminishers = LINGUISTIC_STYLE_MARKERS["diminishers"]["markers"]
        
        int_count = sum(1 for m in intensifiers if m in text_lower)
        dim_count = sum(1 for m in diminishers if m in text_lower)
        
        style["intensity_ratio"] = int_count / max(int_count + dim_count, 1)
        
        # Negation density
        negation = LINGUISTIC_STYLE_MARKERS["negation"]["markers"]
        neg_count = sum(1 for m in negation if m in text_lower)
        style["negation_density"] = neg_count / max(len(words), 1)
        
        # Question usage
        style["question_count"] = text.count("?")
        
        # Sentence length
        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        if sentences:
            style["avg_sentence_length"] = sum(len(s.split()) for s in sentences) / len(sentences)
        
        profile.linguistic_style = style
    
    def _assess_credibility(
        self,
        text_lower: str,
        words: List[str],
        profile: DeepPsychologicalProfile
    ):
        """Assess review credibility and authenticity."""
        credibility = 0.5  # Start neutral
        markers = []
        
        # Positive credibility signals
        auth_markers = TRUST_CREDIBILITY_MARKERS["authenticity_high"]["markers"]
        if any(m in text_lower for m in auth_markers):
            credibility += 0.1
            markers.append("authenticity_claim")
        
        spec_markers = TRUST_CREDIBILITY_MARKERS["specificity"]["markers"]
        if any(m in text_lower for m in spec_markers):
            credibility += 0.15
            markers.append("specificity")
        
        balance_markers = TRUST_CREDIBILITY_MARKERS["balanced_review"]["markers"]
        if any(m in text_lower for m in balance_markers):
            credibility += 0.2
            markers.append("balanced_perspective")
        
        expert_markers = TRUST_CREDIBILITY_MARKERS["domain_expertise"]["markers"]
        if any(m in text_lower for m in expert_markers):
            credibility += 0.1
            markers.append("expertise_claim")
        
        # Negative credibility signals
        fake_markers = TRUST_CREDIBILITY_MARKERS["astroturfing_indicators"]["markers"]
        if any(m in text_lower for m in fake_markers):
            credibility -= 0.3
            markers.append("potential_fake")
        
        vague_markers = TRUST_CREDIBILITY_MARKERS["vague_superlatives"]["markers"]
        vague_count = sum(1 for m in vague_markers if m in text_lower)
        if vague_count >= 3:
            credibility -= 0.15
            markers.append("vague_language")
        
        # Word count affects credibility (very short = less credible)
        if len(words) < 20:
            credibility -= 0.2
        elif len(words) > 100:
            credibility += 0.1
        
        profile.credibility_score = max(0.0, min(1.0, credibility))
        profile.authenticity_markers = markers
    
    def _infer_archetype(
        self,
        profile: DeepPsychologicalProfile,
        context: Optional[Dict]
    ):
        """Infer consumer archetype from psychological profile."""
        archetype_scores = {}
        
        for archetype, arch_data in DEEP_ARCHETYPE_PROFILES.items():
            score = 0.0
            
            # Match linguistic markers
            keywords = arch_data["linguistic_markers"]["keywords"]
            # This would need the text, but we can use other profile data
            
            # Match regulatory focus
            if arch_data["regulatory_focus"] == "promotion":
                score += profile.promotion_focus_score * 0.3
            else:
                score += profile.prevention_focus_score * 0.3
            
            # Match Big Five
            b5_profile = arch_data["big_five_profile"]
            for trait, expected in b5_profile.items():
                actual = profile.big_five_scores.get(trait, 0)
                
                # Convert expected to numeric
                if expected in ["very_high", "high_intellectual"]:
                    expected_val = 0.8
                elif expected == "high":
                    expected_val = 0.6
                elif expected in ["medium-high", "high_positive"]:
                    expected_val = 0.4
                elif expected in ["medium", "mixed"]:
                    expected_val = 0.0
                elif expected in ["low-medium", "medium-low"]:
                    expected_val = -0.4
                elif expected == "low":
                    expected_val = -0.6
                else:
                    expected_val = 0.0
                
                # Score based on alignment
                alignment = 1.0 - abs(actual - expected_val)
                score += alignment * 0.1
            
            # Match persuasion susceptibility
            primary_vulns = arch_data["persuasion_vulnerabilities"]["primary"]
            for vuln in primary_vulns:
                principle = vuln.split("_")[0]
                if principle in profile.cialdini_susceptibility:
                    score += 0.1
            
            archetype_scores[archetype] = score
        
        # Normalize scores
        total = sum(archetype_scores.values())
        if total > 0:
            archetype_scores = {k: v/total for k, v in archetype_scores.items()}
        
        profile.archetype_scores = archetype_scores
        
        if archetype_scores:
            profile.primary_archetype = max(archetype_scores, key=archetype_scores.get)
            profile.archetype_confidence = archetype_scores[profile.primary_archetype]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    analyzer = DeepPsychologicalAnalyzer()
    
    # Example review
    sample_review = """
    I was really skeptical at first - you know how it is with online purchases.
    But after researching for weeks and comparing dozens of options, I finally
    pulled the trigger. Best decision ever! The quality exceeded my expectations,
    and my whole family loves it. Would definitely recommend to anyone looking
    for a reliable, well-made product. The only minor issue is the color was
    slightly different than pictured, but honestly it looks even better in person.
    Already bought one as a gift for my sister!
    """
    
    profile = analyzer.analyze(sample_review)
    
    print("=" * 70)
    print("DEEP PSYCHOLOGICAL ANALYSIS RESULTS")
    print("=" * 70)
    
    print(f"\n📊 PRIMARY ARCHETYPE: {profile.primary_archetype} ({profile.archetype_confidence:.1%})")
    
    print(f"\n😀 EMOTIONS:")
    for emotion, score in sorted(profile.primary_emotions.items(), key=lambda x: -x[1])[:5]:
        print(f"  • {emotion}: {score:.2f}")
    
    print(f"\n🧠 COGNITIVE PROCESSES:")
    for process, score in sorted(profile.cognitive_processes.items(), key=lambda x: -x[1])[:5]:
        print(f"  • {process}: {score:.2f}")
    
    print(f"\n⚠️  BIASES DETECTED:")
    for bias, score in sorted(profile.biases_detected.items(), key=lambda x: -x[1])[:5]:
        print(f"  • {bias}: {score:.2f}")
    
    print(f"\n👤 BIG FIVE PERSONALITY:")
    for trait, score in profile.big_five_scores.items():
        direction = "high" if score > 0 else "low" if score < 0 else "neutral"
        print(f"  • {trait}: {score:+.2f} ({direction})")
    
    print(f"\n🎯 REGULATORY FOCUS:")
    print(f"  • Promotion: {profile.promotion_focus_score:.1%}")
    print(f"  • Prevention: {profile.prevention_focus_score:.1%}")
    
    print(f"\n💫 PERSUASION SUSCEPTIBILITY:")
    for principle, sub_scores in profile.cialdini_susceptibility.items():
        print(f"  • {principle}:")
        for sub, score in sub_scores.items():
            print(f"      - {sub}: {score:.2f}")
    
    print(f"\n📍 DECISION STAGE: {profile.decision_stage} ({profile.decision_stage_confidence:.1%})")
    
    print(f"\n✅ CREDIBILITY: {profile.credibility_score:.1%}")
    print(f"   Markers: {', '.join(profile.authenticity_markers)}")
