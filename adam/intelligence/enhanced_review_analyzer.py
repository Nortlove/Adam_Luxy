# =============================================================================
# Enhanced Review Psychological Analyzer
# Location: adam/intelligence/enhanced_review_analyzer.py
# =============================================================================

"""
Enhanced Psychological Analyzer with 35 Constructs from Enhancement #27

This is ADAM's PRIMARY intelligence for review analysis - NOT Claude.
Detects psychological constructs using validated linguistic markers from
25 years of research (LIWC, Pennebaker, Yarkoni, Higgins, etc.)

Research Foundation:
- Enhancement #27: Extended Psychological Constructs (35 constructs, 12 domains)
- LIWC (Linguistic Inquiry and Word Count) - Pennebaker et al.
- Big Five personality from language - Yarkoni (2010)
- Regulatory Focus detection - Higgins (1997)
- Need for Cognition - Cacioppo & Petty (1982)
- Self-Monitoring - Snyder (1974)
- Decision Making styles - Schwartz (2002)

Usage:
    analyzer = EnhancedReviewAnalyzer()
    profile = analyzer.analyze_review(review_text, rating=5.0)
    
    # Access construct scores
    nfc_score = profile.get_construct("cognitive_nfc")
    print(f"Need for Cognition: {nfc_score.score:.2f} (confidence: {nfc_score.confidence:.2f})")
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class PsychologicalDomain(str, Enum):
    """The 12 psychological domains from Enhancement #27."""
    COGNITIVE_PROCESSING = "cognitive_processing"
    SELF_REGULATORY = "self_regulatory"
    TEMPORAL_PSYCHOLOGY = "temporal_psychology"
    DECISION_MAKING = "decision_making"
    SOCIAL_COGNITIVE = "social_cognitive"
    UNCERTAINTY_PROCESSING = "uncertainty_processing"
    INFORMATION_PROCESSING = "information_processing"
    MOTIVATIONAL_PROFILE = "motivational_profile"
    EMOTIONAL_PROCESSING = "emotional_processing"
    PURCHASE_PSYCHOLOGY = "purchase_psychology"
    VALUE_ORIENTATION = "value_orientation"
    BIG_FIVE = "big_five"


class ConstructType(str, Enum):
    """Classification of psychological constructs."""
    TRAIT = "trait"           # Stable personality-like dimensions
    DISPOSITION = "disposition"  # Chronic tendencies that are modifiable
    STATE = "state"           # Fluctuating momentary states


class DetectionMethod(str, Enum):
    """Methods for detecting psychological constructs."""
    LINGUISTIC = "linguistic"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    NONCONSCIOUS = "nonconscious"


@dataclass
class ConstructScore:
    """Score for a single psychological construct."""
    construct_id: str
    score: float  # 0-1 normalized
    confidence: float  # 0-1 confidence in score
    raw_score: float = 0.0
    signals_detected: int = 0
    detection_methods: List[DetectionMethod] = field(default_factory=list)
    
    @property
    def categorical_level(self) -> str:
        """Get categorical level (low/moderate/high)."""
        if self.score < 0.33:
            return "low"
        elif self.score < 0.67:
            return "moderate"
        else:
            return "high"


@dataclass
class ConstructProfile:
    """Complete psychological profile across all 35 constructs."""
    scores: Dict[str, ConstructScore] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
    review_rating: float = 0.0
    
    def get_construct(self, construct_id: str) -> Optional[ConstructScore]:
        return self.scores.get(construct_id)
    
    def get_domain_scores(self, domain: PsychologicalDomain) -> Dict[str, ConstructScore]:
        """Get all construct scores for a domain."""
        domain_constructs = DOMAIN_CONSTRUCTS.get(domain, [])
        return {cid: self.scores[cid] for cid in domain_constructs if cid in self.scores}
    
    @property
    def primary_archetype(self) -> Tuple[str, float]:
        """Infer primary archetype from construct profile."""
        archetype_scores = {}
        
        for archetype, mapping in ARCHETYPE_CONSTRUCT_MAPPING.items():
            score = 0.0
            weight_sum = 0.0
            
            for construct_id, weight in mapping.items():
                if construct_id in self.scores:
                    score += self.scores[construct_id].score * weight
                    weight_sum += abs(weight)
            
            if weight_sum > 0:
                archetype_scores[archetype] = score / weight_sum
        
        if not archetype_scores:
            return ("Unknown", 0.0)
        
        best = max(archetype_scores.items(), key=lambda x: x[1])
        return best
    
    def to_dict(self) -> dict:
        return {
            "scores": {k: {
                "score": v.score,
                "confidence": v.confidence,
                "categorical_level": v.categorical_level,
                "signals_detected": v.signals_detected,
            } for k, v in self.scores.items()},
            "primary_archetype": self.primary_archetype[0],
            "archetype_confidence": self.primary_archetype[1],
            "word_count": self.word_count,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


# =============================================================================
# CONSTRUCT DEFINITIONS FROM ENHANCEMENT #27
# =============================================================================

# Domain to construct mapping
DOMAIN_CONSTRUCTS = {
    PsychologicalDomain.BIG_FIVE: [
        "big5_openness", "big5_conscientiousness", "big5_extraversion",
        "big5_agreeableness", "big5_neuroticism",
    ],
    PsychologicalDomain.COGNITIVE_PROCESSING: [
        "cognitive_nfc", "cognitive_psp", "cognitive_hri",
    ],
    PsychologicalDomain.SELF_REGULATORY: [
        "selfreg_sm", "selfreg_rf_promotion", "selfreg_rf_prevention", "selfreg_lam",
    ],
    PsychologicalDomain.TEMPORAL_PSYCHOLOGY: [
        "temporal_orientation", "temporal_fsc", "temporal_ddr", "temporal_ph",
    ],
    PsychologicalDomain.DECISION_MAKING: [
        "decision_maximizer", "decision_regret", "decision_overload",
    ],
    PsychologicalDomain.SOCIAL_COGNITIVE: [
        "social_sco", "social_conformity", "social_nfu", "social_oli",
    ],
    PsychologicalDomain.UNCERTAINTY_PROCESSING: [
        "uncertainty_at", "uncertainty_nfc",
    ],
    PsychologicalDomain.INFORMATION_PROCESSING: [
        "info_vv", "info_holistic_analytic", "info_field_independence",
    ],
    PsychologicalDomain.MOTIVATIONAL_PROFILE: [
        "motivation_achievement", "motivation_affiliation", "motivation_iem",
    ],
    PsychologicalDomain.EMOTIONAL_PROCESSING: [
        "emotion_affect_intensity",
    ],
    PsychologicalDomain.PURCHASE_PSYCHOLOGY: [
        "purchase_pct",
    ],
    PsychologicalDomain.VALUE_ORIENTATION: [
        "value_hub", "value_consciousness",
    ],
}


# =============================================================================
# LINGUISTIC MARKERS FROM ENHANCEMENT #27
# =============================================================================

# All linguistic markers organized by construct
# Format: {construct_id: {marker_category: loading}}
# Positive loading = higher marker presence = higher construct score
# Negative loading = inverse relationship

CONSTRUCT_LINGUISTIC_MARKERS = {
    # =========================================================================
    # BIG FIVE (Traditional LIWC-based)
    # =========================================================================
    "big5_openness": {
        "cognitive_words": 0.30,
        "tentative_words": 0.20,
        "insight_words": 0.25,
        "novel_words": 0.25,
    },
    "big5_conscientiousness": {
        "certainty_words": 0.30,
        "achievement_words": 0.25,
        "work_words": 0.20,
        "order_words": 0.25,
    },
    "big5_extraversion": {
        "social_words": 0.30,
        "positive_emotion": 0.25,
        "we_pronouns": 0.20,
        "exclamation_marks": 0.25,
    },
    "big5_agreeableness": {
        "positive_emotion": 0.25,
        "we_pronouns": 0.20,
        "affiliation_words": 0.30,
        "i_pronouns": -0.15,  # Inverse
    },
    "big5_neuroticism": {
        "negative_emotion": 0.35,
        "anxiety_words": 0.25,
        "i_pronouns": 0.20,
        "certainty_words": -0.15,  # Inverse
    },
    
    # =========================================================================
    # COGNITIVE PROCESSING
    # =========================================================================
    "cognitive_nfc": {  # Need for Cognition
        "causal_reasoning": 0.25,
        "sentence_complexity": 0.30,
        "vocabulary_sophistication": 0.25,
        "hedging_language": 0.10,
        "question_words": 0.10,
    },
    "cognitive_psp": {  # Processing Speed Preference
        "certainty_words": 0.40,
        "hedging_words": -0.30,  # Inverse
        "quick_decision_words": 0.30,
    },
    "cognitive_hri": {  # Heuristic Reliance Index
        "certainty_expressions": 0.35,
        "reference_to_others": 0.35,
        "shortcut_language": 0.30,
    },
    
    # =========================================================================
    # SELF-REGULATORY
    # =========================================================================
    "selfreg_sm": {  # Self-Monitoring
        "social_reference": 0.35,
        "impression_management": 0.30,
        "situation_words": 0.20,
        "flexibility_words": 0.15,
    },
    "selfreg_rf_promotion": {  # Regulatory Focus - Promotion
        "achievement_words": 0.30,
        "gain_words": 0.25,
        "positive_outcome_words": 0.25,
        "approach_verbs": 0.20,
    },
    "selfreg_rf_prevention": {  # Regulatory Focus - Prevention
        "security_words": 0.30,
        "safety_words": 0.25,
        "avoid_words": 0.25,
        "loss_words": 0.20,
    },
    "selfreg_lam": {  # Locomotion-Assessment Mode
        "action_verbs": 0.35,
        "evaluation_words": -0.35,  # Inverse - high = locomotion
        "momentum_words": 0.30,
    },
    
    # =========================================================================
    # TEMPORAL PSYCHOLOGY
    # =========================================================================
    "temporal_orientation": {  # Future vs Past orientation
        "future_tense": 0.35,
        "past_tense": -0.25,  # Inverse
        "planning_words": 0.25,
        "goal_words": 0.30,
    },
    "temporal_fsc": {  # Future Self-Continuity
        "future_self_reference": 0.40,
        "consequence_words": 0.30,
        "planning_words": 0.20,
        "regret_anticipation": 0.10,
    },
    "temporal_ddr": {  # Delay Discounting Rate
        "immediacy_words": 0.40,
        "patience_words": -0.35,  # Inverse
        "urgency_words": 0.25,
    },
    "temporal_ph": {  # Planning Horizon
        "long_term_words": 0.40,
        "planning_words": 0.30,
        "goal_words": 0.20,
        "short_term_words": -0.30,  # Inverse
    },
    
    # =========================================================================
    # DECISION MAKING
    # =========================================================================
    "decision_maximizer": {  # Maximizer vs Satisficer
        "superlative_words": 0.35,
        "good_enough_words": -0.30,  # Inverse
        "comparison_words": 0.25,
        "perfectionist_words": 0.20,
    },
    "decision_regret": {  # Regret Anticipation
        "regret_words": 0.40,
        "counterfactual_words": 0.30,
        "safety_words": 0.20,
        "certainty_seeking": 0.15,
    },
    "decision_overload": {  # Choice Overload Susceptibility
        "overwhelm_words": 0.40,
        "simplicity_words": 0.30,
        "difficulty_words": 0.20,
        "guidance_words": 0.15,
    },
    
    # =========================================================================
    # SOCIAL-COGNITIVE
    # =========================================================================
    "social_sco": {  # Social Comparison Orientation
        "comparison_words": 0.40,
        "ranking_words": 0.30,
        "relative_words": 0.20,
        "competitive_words": 0.15,
    },
    "social_conformity": {  # Conformity Susceptibility
        "social_reference": 0.40,
        "norm_words": 0.30,
        "majority_words": 0.20,
        "trend_words": 0.15,
    },
    "social_nfu": {  # Need for Uniqueness
        "uniqueness_words": 0.40,
        "differentiation_words": 0.30,
        "exclusivity_words": 0.20,
        "conformity_words": -0.15,  # Inverse
    },
    "social_oli": {  # Opinion Leadership Index
        "advisory_words": 0.40,
        "expertise_words": 0.30,
        "opinion_words": 0.20,
        "knowledge_words": 0.15,
    },
    
    # =========================================================================
    # UNCERTAINTY PROCESSING
    # =========================================================================
    "uncertainty_at": {  # Ambiguity Tolerance
        "certainty_seeking": -0.40,  # Inverse
        "uncertainty_comfort": 0.30,
        "exploration_words": 0.20,
        "flexibility_words": 0.15,
    },
    "uncertainty_nfc": {  # Need for Closure
        "definiteness_words": 0.40,
        "closure_words": 0.30,
        "order_words": 0.20,
        "uncertainty_discomfort": 0.15,
    },
    
    # =========================================================================
    # INFORMATION PROCESSING
    # =========================================================================
    "info_vv": {  # Visualizer-Verbalizer
        "visual_words": 0.40,
        "descriptive_words": -0.35,  # Inverse - high = visualizer
        "spatial_words": 0.25,
    },
    "info_holistic_analytic": {  # Holistic vs Analytic
        "attribute_words": 0.35,  # High = analytic
        "relationship_words": -0.35,  # Inverse - high = holistic
        "categorization_words": 0.25,
    },
    "info_field_independence": {  # Field Independence
        "precise_words": 0.35,
        "context_words": -0.30,  # Inverse
        "focused_words": 0.25,
    },
    
    # =========================================================================
    # MOTIVATIONAL PROFILE
    # =========================================================================
    "motivation_achievement": {  # Achievement Motivation
        "achievement_words": 0.40,
        "challenge_words": 0.30,
        "performance_words": 0.20,
        "excellence_words": 0.15,
    },
    "motivation_affiliation": {  # Affiliation Motivation
        "social_words": 0.40,
        "belonging_words": 0.30,
        "relationship_words": 0.20,
        "community_words": 0.15,
    },
    "motivation_iem": {  # Intrinsic-Extrinsic Motivation
        "enjoyment_words": 0.40,
        "reward_words": -0.35,  # Inverse - high = intrinsic
        "passion_words": 0.25,
    },
    
    # =========================================================================
    # EMOTIONAL PROCESSING
    # =========================================================================
    "emotion_affect_intensity": {  # Affect Intensity
        "emotional_intensifiers": 0.45,
        "emotional_vocabulary": 0.30,
        "exclamation_marks": 0.20,
        "superlative_emotions": 0.15,
    },
    
    # =========================================================================
    # PURCHASE PSYCHOLOGY
    # =========================================================================
    "purchase_pct": {  # Purchase Confidence Threshold
        "certainty_seeking": 0.40,
        "question_frequency": 0.30,
        "hedging_words": 0.20,
    },
    
    # =========================================================================
    # VALUE ORIENTATION
    # =========================================================================
    "value_hub": {  # Hedonic-Utilitarian Balance
        "enjoyment_words": 0.40,
        "practical_words": -0.35,  # Inverse - high = hedonic
        "experience_words": 0.25,
    },
    "value_consciousness": {  # Value Consciousness
        "value_words": 0.40,
        "price_words": 0.30,
        "deal_words": 0.20,
        "quality_price_words": 0.15,
    },
}


# =============================================================================
# WORD DICTIONARIES FOR LINGUISTIC MARKERS
# =============================================================================

# Each dictionary maps marker categories to sets of words/patterns

WORD_DICTIONARIES = {
    # Pronouns
    "i_pronouns": {"i", "me", "my", "mine", "myself"},
    "we_pronouns": {"we", "us", "our", "ours", "ourselves"},
    "they_pronouns": {"they", "them", "their", "theirs", "themselves"},
    
    # Emotions
    "positive_emotion": {
        "love", "great", "amazing", "excellent", "fantastic", "wonderful",
        "perfect", "best", "awesome", "incredible", "happy", "pleased",
        "satisfied", "delighted", "thrilled", "impressed", "beautiful",
        "brilliant", "outstanding", "superb", "fabulous", "terrific", "joy",
    },
    "negative_emotion": {
        "hate", "terrible", "awful", "horrible", "worst", "bad", "poor",
        "disappointed", "frustrating", "annoying", "useless", "waste",
        "broken", "defective", "garbage", "trash", "regret", "angry",
        "upset", "unhappy", "failed", "problem", "issue", "frustration",
    },
    "anxiety_words": {
        "worried", "anxious", "nervous", "concerned", "afraid", "scared",
        "fear", "worry", "panic", "stress", "uneasy", "tense",
    },
    
    # Certainty and hedging
    "certainty_words": {
        "always", "never", "definitely", "absolutely", "certainly",
        "completely", "totally", "exactly", "precisely", "clearly",
        "obviously", "undoubtedly", "sure", "certain", "guaranteed",
    },
    "hedging_words": {
        "maybe", "perhaps", "possibly", "might", "could", "seems",
        "appears", "somewhat", "probably", "likely", "kind of",
        "sort of", "guess", "think", "wonder", "suppose",
    },
    "certainty_seeking": {
        "sure", "certain", "guarantee", "promise", "confirm", "verify",
        "reliable", "consistent", "depend", "trust", "proven",
    },
    
    # Cognitive
    "cognitive_words": {
        "think", "know", "understand", "realize", "believe", "consider",
        "analyze", "compare", "research", "learned", "figured", "reason",
        "because", "therefore", "however", "although", "whether",
    },
    "causal_reasoning": {
        "because", "therefore", "thus", "hence", "consequently", "since",
        "reason", "cause", "result", "due to", "leads to", "explains",
    },
    "insight_words": {
        "realize", "understand", "discover", "found", "know", "see",
        "recognize", "learn", "figured", "thought", "meaning",
    },
    
    # Social
    "social_words": {
        "friend", "friends", "family", "people", "everyone", "together",
        "share", "shared", "sharing", "recommend", "recommended", "told",
        "gift", "gifted", "party", "group", "team", "community",
    },
    "social_reference": {
        "people", "everyone", "others", "friends", "family", "they",
        "someone", "anybody", "somebody", "folks", "customers",
    },
    "affiliation_words": {
        "together", "team", "group", "community", "belong", "connect",
        "bond", "relationship", "support", "help", "care",
    },
    
    # Achievement
    "achievement_words": {
        "goal", "success", "achieve", "accomplished", "best", "top",
        "excellent", "superior", "quality", "premium", "professional",
        "efficient", "effective", "productive", "performance", "results",
        "win", "succeed", "accomplish", "master", "excel",
    },
    "challenge_words": {
        "challenge", "difficult", "hard", "tough", "demanding", "test",
        "push", "stretch", "overcome", "conquer",
    },
    "excellence_words": {
        "excellent", "exceptional", "outstanding", "superior", "premium",
        "top-notch", "first-class", "world-class", "elite",
    },
    
    # Regulatory Focus
    "gain_words": {
        "gain", "achieve", "advance", "grow", "improve", "enhance",
        "opportunity", "potential", "hope", "aspire", "eager",
    },
    "security_words": {
        "safe", "safety", "secure", "security", "protect", "protection",
        "reliable", "trust", "trusted", "dependable", "stable",
    },
    "safety_words": {
        "safe", "safety", "secure", "protection", "reliable", "stable",
        "risk-free", "guaranteed", "warranty",
    },
    "loss_words": {
        "lose", "loss", "miss", "risk", "danger", "threat",
        "prevent", "avoid", "careful", "cautious",
    },
    "avoid_words": {
        "avoid", "prevent", "protect", "careful", "cautious", "worry",
        "concerned", "risk", "dangerous", "warning",
    },
    "approach_verbs": {
        "get", "achieve", "gain", "reach", "attain", "pursue",
        "seek", "strive", "aim", "target",
    },
    
    # Temporal
    "future_tense": {
        "will", "going to", "plan to", "intend", "expect", "hope",
        "soon", "tomorrow", "eventually", "someday", "future",
    },
    "past_tense": {
        "was", "were", "had", "used to", "previously", "before",
        "ago", "past", "once", "formerly",
    },
    "planning_words": {
        "plan", "schedule", "prepare", "organize", "arrange", "goal",
        "target", "strategy", "anticipate", "expect",
    },
    "goal_words": {
        "goal", "objective", "aim", "target", "purpose", "intention",
        "aspiration", "ambition", "milestone",
    },
    "long_term_words": {
        "years", "long-term", "future", "eventually", "lifetime",
        "investment", "lasting", "permanent", "enduring",
    },
    "short_term_words": {
        "now", "today", "immediately", "quick", "instant", "fast",
        "right away", "asap", "hurry",
    },
    "immediacy_words": {
        "now", "immediately", "instant", "quick", "fast", "hurry",
        "rush", "urgent", "asap", "right away",
    },
    "patience_words": {
        "wait", "patient", "eventually", "time", "slow", "careful",
        "thorough", "deliberate",
    },
    "urgency_words": {
        "urgent", "hurry", "quick", "fast", "immediately", "now",
        "rush", "asap", "time-sensitive",
    },
    
    # Decision Making
    "superlative_words": {
        "best", "greatest", "perfect", "ideal", "optimal", "ultimate",
        "finest", "top", "premier", "supreme",
    },
    "good_enough_words": {
        "fine", "okay", "acceptable", "decent", "adequate", "sufficient",
        "works", "does the job", "good enough",
    },
    "comparison_words": {
        "better", "worse", "compare", "versus", "than", "compared to",
        "relative", "alternative", "option",
    },
    "perfectionist_words": {
        "perfect", "flawless", "ideal", "optimal", "exact", "precise",
        "meticulous", "thorough",
    },
    "regret_words": {
        "regret", "wish", "should have", "mistake", "wrong", "unfortunate",
        "disappointed", "if only",
    },
    "counterfactual_words": {
        "if", "would have", "could have", "should have", "might have",
        "what if", "instead",
    },
    "overwhelm_words": {
        "overwhelm", "too many", "confusing", "complicated", "complex",
        "difficult", "hard to choose", "so many options",
    },
    "simplicity_words": {
        "simple", "easy", "straightforward", "clear", "basic",
        "uncomplicated", "hassle-free",
    },
    "difficulty_words": {
        "difficult", "hard", "challenging", "complicated", "complex",
        "confusing", "tough",
    },
    "guidance_words": {
        "help", "guide", "recommend", "suggest", "advice", "tip",
        "direction", "assistance",
    },
    
    # Social Comparison
    "ranking_words": {
        "rank", "rating", "best", "top", "number one", "first",
        "leading", "highest", "lowest",
    },
    "relative_words": {
        "better", "worse", "more", "less", "compared", "relative",
        "versus", "than",
    },
    "competitive_words": {
        "compete", "competition", "beat", "win", "outperform", "ahead",
        "rival", "versus",
    },
    "norm_words": {
        "normal", "typical", "standard", "usual", "common", "regular",
        "average", "mainstream",
    },
    "majority_words": {
        "most", "majority", "everyone", "popular", "common", "mainstream",
        "widespread", "typical",
    },
    "trend_words": {
        "trend", "trending", "popular", "viral", "hot", "buzz",
        "latest", "new", "current",
    },
    "uniqueness_words": {
        "unique", "different", "special", "rare", "one-of-a-kind",
        "exclusive", "distinctive", "unusual", "original",
    },
    "differentiation_words": {
        "different", "unique", "stand out", "distinct", "unlike",
        "separate", "individual",
    },
    "exclusivity_words": {
        "exclusive", "limited", "rare", "special", "premium",
        "elite", "select", "only",
    },
    "conformity_words": {
        "everyone", "popular", "common", "standard", "normal", "typical",
        "mainstream", "regular",
    },
    
    # Opinion Leadership
    "advisory_words": {
        "recommend", "suggest", "advise", "should", "must", "try",
        "consider", "tip", "advice",
    },
    "expertise_words": {
        "expert", "professional", "experienced", "knowledge", "specialist",
        "authority", "master", "skilled",
    },
    "opinion_words": {
        "think", "believe", "opinion", "view", "perspective", "feel",
        "consider", "regard",
    },
    "knowledge_words": {
        "know", "learn", "understand", "research", "discover", "find out",
        "information", "facts",
    },
    
    # Uncertainty
    "uncertainty_comfort": {
        "explore", "try", "experiment", "curious", "open", "flexible",
        "adaptable", "versatile",
    },
    "exploration_words": {
        "explore", "discover", "try", "experiment", "investigate",
        "curious", "adventure",
    },
    "flexibility_words": {
        "flexible", "adaptable", "versatile", "open", "adjust",
        "accommodate", "change",
    },
    "definiteness_words": {
        "definitely", "certainly", "absolutely", "clearly", "obviously",
        "undoubtedly", "sure", "certain",
    },
    "closure_words": {
        "final", "decided", "settled", "concluded", "resolved",
        "done", "finished", "complete",
    },
    "order_words": {
        "organize", "order", "structure", "systematic", "methodical",
        "neat", "tidy", "arranged",
    },
    "uncertainty_discomfort": {
        "unclear", "uncertain", "unsure", "confusing", "ambiguous",
        "vague", "doubt",
    },
    
    # Information Processing
    "visual_words": {
        "see", "look", "view", "picture", "image", "color", "bright",
        "dark", "beautiful", "ugly", "appear", "visible",
    },
    "descriptive_words": {
        "describe", "explain", "detail", "elaborate", "specify",
        "outline", "articulate",
    },
    "spatial_words": {
        "space", "room", "area", "location", "place", "position",
        "size", "dimension", "layout",
    },
    "attribute_words": {
        "feature", "attribute", "characteristic", "property", "aspect",
        "quality", "trait", "specification",
    },
    "relationship_words": {
        "relationship", "connection", "link", "relate", "associated",
        "connected", "together", "combination",
    },
    "categorization_words": {
        "category", "type", "kind", "class", "group", "classify",
        "sort", "organize",
    },
    "context_words": {
        "context", "situation", "circumstance", "environment", "setting",
        "background", "scenario",
    },
    "precise_words": {
        "precise", "exact", "specific", "accurate", "detailed",
        "particular", "explicit",
    },
    "focused_words": {
        "focus", "concentrate", "specific", "particular", "target",
        "zero in", "pinpoint",
    },
    
    # Motivation
    "performance_words": {
        "performance", "result", "outcome", "achievement", "accomplish",
        "success", "effective", "efficient",
    },
    "belonging_words": {
        "belong", "member", "part of", "community", "group", "team",
        "together", "join",
    },
    "community_words": {
        "community", "group", "team", "together", "collective",
        "shared", "common",
    },
    "enjoyment_words": {
        "enjoy", "fun", "pleasure", "delight", "love", "happy",
        "exciting", "entertaining",
    },
    "reward_words": {
        "reward", "prize", "bonus", "incentive", "benefit", "perk",
        "earn", "win",
    },
    "passion_words": {
        "passion", "love", "enthusiastic", "excited", "obsessed",
        "devoted", "dedicated",
    },
    
    # Emotional Intensity
    "emotional_intensifiers": {
        "very", "extremely", "incredibly", "absolutely", "totally",
        "completely", "utterly", "so", "really", "truly",
    },
    "emotional_vocabulary": {
        "love", "hate", "amazing", "terrible", "fantastic", "horrible",
        "wonderful", "awful", "incredible", "devastating",
    },
    "superlative_emotions": {
        "best ever", "worst ever", "most amazing", "most horrible",
        "absolutely love", "completely hate",
    },
    
    # Value Orientation
    "practical_words": {
        "practical", "functional", "useful", "utilitarian", "efficient",
        "effective", "serves purpose",
    },
    "experience_words": {
        "experience", "feel", "sensation", "enjoy", "pleasure",
        "memorable", "moment",
    },
    "value_words": {
        "value", "worth", "bang for buck", "money well spent",
        "good deal", "bargain", "affordable",
    },
    "price_words": {
        "price", "cost", "expensive", "cheap", "affordable", "budget",
        "money", "dollar",
    },
    "deal_words": {
        "deal", "discount", "sale", "savings", "bargain", "offer",
        "promotion", "coupon",
    },
    "quality_price_words": {
        "quality for price", "value for money", "worth the price",
        "good for the price", "bang for buck",
    },
    
    # Miscellaneous
    "novel_words": {
        "new", "innovative", "creative", "original", "fresh",
        "novel", "unique", "different",
    },
    "work_words": {
        "work", "job", "task", "effort", "labor", "productive",
        "efficient", "accomplish",
    },
    "tentative_words": {
        "maybe", "perhaps", "might", "possibly", "seem", "appear",
        "suggest", "indicate",
    },
    "question_words": {
        "what", "why", "how", "when", "where", "which", "who",
    },
    "situation_words": {
        "situation", "context", "occasion", "circumstance", "setting",
        "environment", "scenario",
    },
    "impression_management": {
        "look", "appear", "seem", "image", "perception", "impression",
        "reputation", "status",
    },
    "action_verbs": {
        "do", "act", "start", "begin", "move", "go", "make",
        "create", "build", "implement",
    },
    "evaluation_words": {
        "evaluate", "assess", "consider", "analyze", "compare", "judge",
        "weigh", "review", "examine",
    },
    "momentum_words": {
        "keep going", "continue", "progress", "forward", "momentum",
        "advance", "proceed",
    },
    "future_self_reference": {
        "future me", "when i'm older", "someday i", "eventually i",
        "my future", "years from now",
    },
    "consequence_words": {
        "consequence", "result", "outcome", "effect", "impact",
        "down the road", "eventually",
    },
    "regret_anticipation": {
        "might regret", "don't want to miss", "fomo", "opportunity",
        "once in a lifetime",
    },
    "quick_decision_words": {
        "quick", "fast", "instant", "immediately", "no brainer",
        "easy choice", "obvious",
    },
    "shortcut_language": {
        "just", "simply", "easy", "quick", "obvious", "clearly",
        "no brainer", "everyone knows",
    },
    "reference_to_others": {
        "reviews", "ratings", "people say", "others", "customers",
        "users", "buyers", "recommend",
    },
}


# =============================================================================
# ARCHETYPE TO CONSTRUCT MAPPING
# =============================================================================

ARCHETYPE_CONSTRUCT_MAPPING = {
    "Achiever": {
        "big5_conscientiousness": 0.25,
        "selfreg_rf_promotion": 0.25,
        "motivation_achievement": 0.30,
        "decision_maximizer": 0.20,
    },
    "Explorer": {
        "big5_openness": 0.30,
        "selfreg_rf_promotion": 0.20,
        "social_nfu": 0.25,
        "uncertainty_at": 0.25,
    },
    "Guardian": {
        "selfreg_rf_prevention": 0.30,
        "uncertainty_nfc": 0.25,
        "decision_regret": 0.25,
        "big5_conscientiousness": 0.20,
    },
    "Connector": {
        "big5_extraversion": 0.25,
        "big5_agreeableness": 0.25,
        "motivation_affiliation": 0.30,
        "social_conformity": 0.20,
    },
    "Pragmatist": {
        "value_consciousness": 0.35,
        "cognitive_hri": 0.25,
        "value_hub": -0.20,  # Low hedonic = pragmatic
        "decision_overload": -0.20,  # Low overload = decisive
    },
    "Analyzer": {
        "cognitive_nfc": 0.35,
        "decision_maximizer": 0.25,
        "info_holistic_analytic": 0.25,
        "cognitive_psp": -0.15,  # Low = slow/deliberate
    },
}


# =============================================================================
# ENHANCED REVIEW ANALYZER
# =============================================================================

class EnhancedReviewAnalyzer:
    """
    Enhanced psychological analyzer with 35 constructs.
    
    This is ADAM's PRIMARY intelligence for review analysis.
    Uses validated linguistic markers from Enhancement #27.
    """
    
    def __init__(self):
        self.version = "2.0"
        
        # Compile word sets for efficient lookup
        self._word_sets: Dict[str, Set[str]] = {}
        for category, words in WORD_DICTIONARIES.items():
            self._word_sets[category] = set(w.lower() for w in words)
    
    def analyze_review(
        self,
        review_text: str,
        rating: float = 3.0,
    ) -> ConstructProfile:
        """
        Analyze a review for all 35 psychological constructs.
        
        Args:
            review_text: The review content
            rating: Star rating (1-5)
            
        Returns:
            ConstructProfile with scores for all constructs
        """
        # Tokenize
        words = self._tokenize(review_text)
        word_count = len(words)
        
        if word_count == 0:
            return ConstructProfile(word_count=0, review_rating=rating)
        
        # Count words in each category
        category_counts = self._count_categories(words, review_text)
        
        # Calculate construct scores
        scores = {}
        for construct_id, markers in CONSTRUCT_LINGUISTIC_MARKERS.items():
            score, confidence, signals = self._score_construct(
                markers, category_counts, word_count, rating
            )
            scores[construct_id] = ConstructScore(
                construct_id=construct_id,
                score=score,
                confidence=confidence,
                raw_score=score,
                signals_detected=signals,
                detection_methods=[DetectionMethod.LINGUISTIC],
            )
        
        return ConstructProfile(
            scores=scores,
            word_count=word_count,
            review_rating=rating,
        )
    
    def analyze_reviews(
        self,
        reviews: List[Tuple[str, float]],
    ) -> ConstructProfile:
        """
        Analyze multiple reviews and aggregate construct scores.
        
        Args:
            reviews: List of (review_text, rating) tuples
            
        Returns:
            Aggregated ConstructProfile
        """
        if not reviews:
            return ConstructProfile()
        
        profiles = [self.analyze_review(text, rating) for text, rating in reviews]
        
        # Aggregate scores (weighted by confidence)
        aggregated_scores = {}
        
        for construct_id in CONSTRUCT_LINGUISTIC_MARKERS.keys():
            total_score = 0.0
            total_weight = 0.0
            total_signals = 0
            
            for profile in profiles:
                if construct_id in profile.scores:
                    cs = profile.scores[construct_id]
                    weight = cs.confidence * profile.word_count
                    total_score += cs.score * weight
                    total_weight += weight
                    total_signals += cs.signals_detected
            
            if total_weight > 0:
                aggregated_scores[construct_id] = ConstructScore(
                    construct_id=construct_id,
                    score=total_score / total_weight,
                    confidence=min(1.0, total_weight / (len(profiles) * 100)),
                    signals_detected=total_signals,
                    detection_methods=[DetectionMethod.LINGUISTIC],
                )
        
        return ConstructProfile(
            scores=aggregated_scores,
            word_count=sum(p.word_count for p in profiles),
            review_rating=sum(r[1] for r in reviews) / len(reviews),
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        text = re.sub(r"[^\w\s']", " ", text.lower())
        return text.split()
    
    def _count_categories(
        self,
        words: List[str],
        full_text: str,
    ) -> Dict[str, int]:
        """Count words in each category."""
        counts = {}
        word_set = set(words)
        full_text_lower = full_text.lower()
        
        for category, word_dict in self._word_sets.items():
            # Single word matches
            count = len(word_set & word_dict)
            
            # Multi-word phrase matches
            for phrase in word_dict:
                if ' ' in phrase and phrase in full_text_lower:
                    count += 1
            
            counts[category] = count
        
        # Add special counts
        counts["exclamation_marks"] = full_text.count("!")
        counts["question_marks"] = full_text.count("?")
        
        # Sentence complexity (average words per sentence)
        sentences = re.split(r'[.!?]+', full_text)
        if sentences:
            avg_sentence_length = len(words) / max(len(sentences), 1)
            counts["sentence_complexity"] = int(avg_sentence_length > 15)
        
        # Vocabulary sophistication (unique words / total words)
        if words:
            vocab_ratio = len(set(words)) / len(words)
            counts["vocabulary_sophistication"] = int(vocab_ratio > 0.6)
        
        return counts
    
    def _score_construct(
        self,
        markers: Dict[str, float],
        category_counts: Dict[str, int],
        word_count: int,
        rating: float,
    ) -> Tuple[float, float, int]:
        """
        Calculate construct score from linguistic markers.
        
        Returns: (score, confidence, signals_detected)
        """
        score = 0.5  # Start at neutral
        total_weight = 0.0
        signals = 0
        
        for marker_category, loading in markers.items():
            count = category_counts.get(marker_category, 0)
            
            if count > 0:
                signals += count
                
                # Normalize by word count (frequency)
                frequency = min(count / max(word_count, 1) * 100, 1.0)
                
                # Apply loading (can be negative for inverse relationships)
                contribution = frequency * loading
                score += contribution
                total_weight += abs(loading)
        
        # Normalize score to 0-1
        score = max(0.0, min(1.0, score))
        
        # Calculate confidence based on signals and word count
        if signals == 0:
            confidence = 0.2  # Low confidence if no signals
        else:
            signal_factor = min(signals / 5, 1.0)  # More signals = more confidence
            length_factor = min(word_count / 100, 1.0)  # Longer reviews = more confidence
            confidence = 0.3 + (signal_factor * 0.4) + (length_factor * 0.3)
        
        return score, confidence, signals


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_analyzer_instance: Optional[EnhancedReviewAnalyzer] = None


def get_enhanced_analyzer() -> EnhancedReviewAnalyzer:
    """Get or create the singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = EnhancedReviewAnalyzer()
    return _analyzer_instance


def analyze_review(review_text: str, rating: float = 3.0) -> ConstructProfile:
    """Convenience function to analyze a single review."""
    analyzer = get_enhanced_analyzer()
    return analyzer.analyze_review(review_text, rating)


def analyze_reviews(reviews: List[Tuple[str, float]]) -> ConstructProfile:
    """Convenience function to analyze multiple reviews."""
    analyzer = get_enhanced_analyzer()
    return analyzer.analyze_reviews(reviews)
