# =============================================================================
# Review Psychological Analyzer
# Location: adam/intelligence/review_analyzer.py
# =============================================================================

"""
Psychological Analyzer for Customer Reviews

This module performs deep psychological analysis on review text,
inferring personality traits, archetypes, motivations, and language
patterns from the way customers write about products.

Research Foundation:
- LIWC (Linguistic Inquiry and Word Count) - Pennebaker et al.
- Big Five personality from language - Yarkoni (2010)
- Regulatory Focus detection - Higgins (1997)
- Purchase motivation taxonomies - Tauber (1972)

Integration:
- Used by ReviewIntelligenceOrchestrator
- Produces ReviewAnalysis objects
- Results flow to CustomerIntelligenceProfile
"""

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.models.customer_intelligence import (
    LanguagePatterns,
    PurchaseMotivation,
    ReviewAnalysis,
    ReviewerProfile,
    ReviewSource,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LIWC-STYLE WORD CATEGORIES
# =============================================================================

# Pronoun categories (indicate self-focus vs social orientation)
PRONOUNS_I = {"i", "me", "my", "mine", "myself"}
PRONOUNS_WE = {"we", "us", "our", "ours", "ourselves"}
PRONOUNS_THEY = {"they", "them", "their", "theirs", "themselves"}

# Emotion words (indicate emotional arousal and valence)
EMOTION_POSITIVE = {
    "love", "great", "amazing", "excellent", "fantastic", "wonderful", 
    "perfect", "best", "awesome", "incredible", "happy", "pleased",
    "satisfied", "delighted", "thrilled", "impressed", "beautiful",
    "brilliant", "outstanding", "superb", "fabulous", "terrific",
}

EMOTION_NEGATIVE = {
    "hate", "terrible", "awful", "horrible", "worst", "bad", "poor",
    "disappointed", "frustrating", "annoying", "useless", "waste",
    "broken", "defective", "garbage", "trash", "regret", "angry",
    "upset", "unhappy", "failed", "problem", "issue",
}

# Certainty words (indicate conscientiousness)
CERTAINTY_WORDS = {
    "always", "never", "definitely", "absolutely", "certainly",
    "completely", "totally", "exactly", "precisely", "clearly",
    "obviously", "undoubtedly", "sure", "certain", "guaranteed",
}

# Tentative words (indicate openness/uncertainty)
TENTATIVE_WORDS = {
    "maybe", "perhaps", "possibly", "might", "could", "seems",
    "appears", "somewhat", "probably", "likely", "kind of",
    "sort of", "guess", "think", "wonder", "suppose",
}

# Social words (indicate extraversion)
SOCIAL_WORDS = {
    "friend", "friends", "family", "people", "everyone", "together",
    "share", "shared", "sharing", "recommend", "recommended", "told",
    "gift", "gifted", "party", "group", "team", "community",
}

# Achievement words (indicate conscientiousness/achievement motivation)
ACHIEVEMENT_WORDS = {
    "goal", "success", "achieve", "accomplished", "best", "top",
    "excellent", "superior", "quality", "premium", "professional",
    "efficient", "effective", "productive", "performance", "results",
}

# Risk/safety words (indicate prevention focus)
PREVENTION_WORDS = {
    "safe", "safety", "secure", "security", "protect", "protection",
    "reliable", "reliable", "trust", "trusted", "worry", "concerned",
    "careful", "cautious", "avoid", "risk", "dangerous", "warning",
}

# Promotion words (indicate promotion focus)
PROMOTION_WORDS = {
    "gain", "achieve", "advance", "grow", "improve", "enhance",
    "opportunity", "potential", "hope", "dream", "aspire", "eager",
    "excited", "exciting", "fun", "enjoy", "explore", "discover",
}

# Cognitive process words (indicate analytical thinking / openness)
COGNITIVE_WORDS = {
    "think", "know", "understand", "realize", "believe", "consider",
    "analyze", "compare", "research", "learned", "figured", "reason",
    "because", "therefore", "however", "although", "whether",
}


# =============================================================================
# PURCHASE MOTIVATION PATTERNS
# =============================================================================

MOTIVATION_PATTERNS = {
    PurchaseMotivation.CONVENIENCE: [
        r"easy to use", r"convenient", r"saves? time", r"quick", r"simple",
        r"hassle[- ]?free", r"effortless", r"straightforward",
    ],
    PurchaseMotivation.QUALITY: [
        r"high quality", r"well[- ]?made", r"durable", r"sturdy", r"solid",
        r"premium", r"excellent quality", r"built to last",
    ],
    PurchaseMotivation.VALUE: [
        r"great value", r"worth the money", r"good price", r"affordable",
        r"bang for .* buck", r"bargain", r"deal", r"savings?",
    ],
    PurchaseMotivation.STATUS: [
        r"looks? (great|amazing|premium)", r"compliments?", r"impressed",
        r"stylish", r"elegant", r"luxury", r"exclusive", r"envious",
    ],
    PurchaseMotivation.SECURITY: [
        r"feel safe", r"peace of mind", r"reliable", r"trust",
        r"dependable", r"secure", r"protection", r"warranty",
    ],
    PurchaseMotivation.RECOMMENDATION: [
        r"friend recommended", r"heard about", r"everyone (says?|loves?)",
        r"reviews? (were|said)", r"recommended by",
    ],
    PurchaseMotivation.UPGRADE: [
        r"upgrade", r"replaced? my old", r"better than .* previous",
        r"switched from", r"improvement over",
    ],
    PurchaseMotivation.PROBLEM_SOLVING: [
        r"solved? (my|the) problem", r"fixed", r"no more",
        r"finally (found|works?)", r"needed", r"solution",
    ],
    PurchaseMotivation.GIFT: [
        r"gift", r"present", r"gave it to", r"bought for (my|a)",
        r"birthday", r"christmas", r"anniversary",
    ],
    PurchaseMotivation.CURIOSITY: [
        r"wanted to try", r"curious", r"see what .* hype",
        r"heard so much", r"decided to try",
    ],
}


# =============================================================================
# ARCHETYPE PATTERNS
# =============================================================================

ARCHETYPE_INDICATORS = {
    "Achiever": {
        "patterns": [r"best", r"top", r"premium", r"professional", r"performance"],
        "traits": {"conscientiousness": 0.8, "promotion_focus": 0.75},
    },
    "Explorer": {
        "patterns": [r"discover", r"try", r"new", r"different", r"experience"],
        "traits": {"openness": 0.85, "promotion_focus": 0.7},
    },
    "Connector": {
        "patterns": [r"share", r"family", r"friends", r"together", r"gift"],
        "traits": {"extraversion": 0.8, "agreeableness": 0.75},
    },
    "Guardian": {
        "patterns": [r"safe", r"reliable", r"trust", r"protect", r"secure"],
        "traits": {"conscientiousness": 0.75, "prevention_focus": 0.8},
    },
    "Analyzer": {
        "patterns": [r"research", r"compare", r"specs?", r"features?", r"detail"],
        "traits": {"conscientiousness": 0.8, "openness": 0.7},
    },
    "Pragmatist": {
        "patterns": [r"value", r"price", r"worth", r"practical", r"efficient"],
        "traits": {"conscientiousness": 0.7, "neuroticism": 0.4},
    },
}


# =============================================================================
# REVIEW PSYCHOLOGICAL ANALYZER
# =============================================================================

class ReviewPsychologicalAnalyzer:
    """
    Analyzes review text to extract psychological insights.
    
    Uses LIWC-style word counting, pattern matching, and heuristics
    to infer Big Five personality, regulatory focus, archetype, and
    purchase motivations from review language.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.version = "1.0"
        
        # Compile regex patterns for efficiency
        self._compiled_motivation_patterns = {
            motivation: [re.compile(p, re.IGNORECASE) for p in patterns]
            for motivation, patterns in MOTIVATION_PATTERNS.items()
        }
        
        self._compiled_archetype_patterns = {
            archetype: [re.compile(p, re.IGNORECASE) for p in data["patterns"]]
            for archetype, data in ARCHETYPE_INDICATORS.items()
        }
    
    def analyze_review(
        self,
        review_text: str,
        rating: float,
        source: ReviewSource,
        review_id: str,
        source_url: Optional[str] = None,
        review_date: Optional[datetime] = None,
        reviewer_name: Optional[str] = None,
        verified_purchase: bool = False,
        helpful_votes: int = 0,
    ) -> ReviewAnalysis:
        """
        Perform complete psychological analysis of a review.
        
        Args:
            review_text: The review content
            rating: Star rating (1-5)
            source: Where the review came from
            review_id: Unique identifier
            source_url: URL where review was found
            review_date: When review was posted
            reviewer_name: Reviewer's display name
            verified_purchase: Whether purchase was verified
            helpful_votes: Number of helpful votes
            
        Returns:
            Complete ReviewAnalysis with psychological profile
        """
        # Tokenize and preprocess
        words = self._tokenize(review_text)
        word_set = set(words)
        
        # Count word categories
        word_categories = self._count_word_categories(words, word_set)
        
        # Infer Big Five personality
        big_five = self._infer_big_five(word_categories, len(words))
        
        # Infer regulatory focus
        reg_focus = self._infer_regulatory_focus(words, word_set)
        
        # Detect archetype
        archetype, archetype_conf = self._detect_archetype(
            review_text, word_categories, big_five, reg_focus
        )
        
        # Extract purchase motivations
        motivations = self._extract_motivations(review_text)
        
        # Calculate sentiment
        sentiment = self._calculate_sentiment(word_categories, rating)
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(review_text)
        
        # Calculate analysis confidence
        confidence = self._calculate_confidence(
            len(words), word_categories, helpful_votes
        )
        
        # Build reviewer profile
        reviewer_profile = ReviewerProfile(
            review_id=review_id,
            source=source,
            rating=rating,
            verified_purchase=verified_purchase,
            openness=big_five["openness"],
            conscientiousness=big_five["conscientiousness"],
            extraversion=big_five["extraversion"],
            agreeableness=big_five["agreeableness"],
            neuroticism=big_five["neuroticism"],
            promotion_focus=reg_focus["promotion"],
            prevention_focus=reg_focus["prevention"],
            archetype=archetype,
            archetype_confidence=archetype_conf,
            purchase_motivations=motivations,
            key_phrases=key_phrases,
            sentiment=sentiment,
            analysis_confidence=confidence,
        )
        
        # Build complete analysis
        return ReviewAnalysis(
            review_id=review_id,
            source=source,
            source_url=source_url,
            review_text=review_text,
            rating=rating,
            review_date=review_date,
            reviewer_name=reviewer_name,
            verified_purchase=verified_purchase,
            helpful_votes=helpful_votes,
            reviewer_profile=reviewer_profile,
            word_categories=word_categories,
            analyzed_at=datetime.utcnow(),
            analyzer_version=self.version,
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        # Remove punctuation and split
        text = re.sub(r"[^\w\s]", " ", text.lower())
        return text.split()
    
    def _count_word_categories(
        self, 
        words: List[str], 
        word_set: set
    ) -> Dict[str, int]:
        """Count words in each LIWC-style category."""
        return {
            "pronoun_i": len(word_set & PRONOUNS_I),
            "pronoun_we": len(word_set & PRONOUNS_WE),
            "pronoun_they": len(word_set & PRONOUNS_THEY),
            "emotion_positive": len(word_set & EMOTION_POSITIVE),
            "emotion_negative": len(word_set & EMOTION_NEGATIVE),
            "certainty": len(word_set & CERTAINTY_WORDS),
            "tentative": len(word_set & TENTATIVE_WORDS),
            "social": len(word_set & SOCIAL_WORDS),
            "achievement": len(word_set & ACHIEVEMENT_WORDS),
            "prevention": len(word_set & PREVENTION_WORDS),
            "promotion": len(word_set & PROMOTION_WORDS),
            "cognitive": len(word_set & COGNITIVE_WORDS),
            "total_words": len(words),
        }
    
    def _infer_big_five(
        self, 
        categories: Dict[str, int],
        total_words: int
    ) -> Dict[str, float]:
        """
        Infer Big Five personality traits from word categories.
        
        Based on research by Yarkoni (2010) and Pennebaker studies
        showing correlations between word use and personality.
        """
        if total_words == 0:
            return {
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            }
        
        # Normalize counts
        def norm(key):
            return min(categories.get(key, 0) / max(total_words, 1) * 100, 1.0)
        
        # Openness: cognitive words, tentative words
        openness = 0.5 + (norm("cognitive") * 0.3) + (norm("tentative") * 0.2)
        
        # Conscientiousness: certainty words, achievement words
        conscientiousness = 0.5 + (norm("certainty") * 0.3) + (norm("achievement") * 0.2)
        
        # Extraversion: social words, positive emotion, we-pronouns
        extraversion = 0.5 + (norm("social") * 0.25) + (norm("emotion_positive") * 0.15) + (norm("pronoun_we") * 0.1)
        
        # Agreeableness: positive emotion, we-pronouns, low I-pronouns
        agreeableness = 0.5 + (norm("emotion_positive") * 0.2) + (norm("pronoun_we") * 0.15) - (norm("pronoun_i") * 0.1)
        
        # Neuroticism: negative emotion, I-pronouns
        neuroticism = 0.5 + (norm("emotion_negative") * 0.3) + (norm("pronoun_i") * 0.1)
        
        # Clamp to [0, 1]
        return {
            "openness": max(0.0, min(1.0, openness)),
            "conscientiousness": max(0.0, min(1.0, conscientiousness)),
            "extraversion": max(0.0, min(1.0, extraversion)),
            "agreeableness": max(0.0, min(1.0, agreeableness)),
            "neuroticism": max(0.0, min(1.0, neuroticism)),
        }
    
    def _infer_regulatory_focus(
        self, 
        words: List[str],
        word_set: set
    ) -> Dict[str, float]:
        """
        Infer regulatory focus (promotion vs prevention).
        
        Based on Higgins (1997) regulatory focus theory.
        """
        promotion_count = len(word_set & PROMOTION_WORDS)
        prevention_count = len(word_set & PREVENTION_WORDS)
        
        total = promotion_count + prevention_count
        if total == 0:
            return {"promotion": 0.5, "prevention": 0.5}
        
        promotion = promotion_count / total
        prevention = prevention_count / total
        
        # Blend with 0.5 baseline
        return {
            "promotion": 0.5 + (promotion - 0.5) * 0.5,
            "prevention": 0.5 + (prevention - 0.5) * 0.5,
        }
    
    def _detect_archetype(
        self,
        text: str,
        categories: Dict[str, int],
        big_five: Dict[str, float],
        reg_focus: Dict[str, float],
    ) -> Tuple[str, float]:
        """
        Detect the most likely psychological archetype.
        
        Uses pattern matching and trait alignment.
        """
        archetype_scores = {}
        
        for archetype, patterns in self._compiled_archetype_patterns.items():
            # Pattern matching score
            pattern_matches = sum(
                1 for p in patterns if p.search(text)
            )
            pattern_score = min(pattern_matches / len(patterns), 1.0)
            
            # Trait alignment score
            expected_traits = ARCHETYPE_INDICATORS[archetype]["traits"]
            trait_score = 0.0
            trait_count = 0
            
            for trait, expected_value in expected_traits.items():
                if trait in big_five:
                    actual = big_five[trait]
                    trait_score += 1.0 - abs(expected_value - actual)
                    trait_count += 1
                elif trait == "promotion_focus":
                    actual = reg_focus["promotion"]
                    trait_score += 1.0 - abs(expected_value - actual)
                    trait_count += 1
                elif trait == "prevention_focus":
                    actual = reg_focus["prevention"]
                    trait_score += 1.0 - abs(expected_value - actual)
                    trait_count += 1
            
            trait_score = trait_score / trait_count if trait_count > 0 else 0.5
            
            # Combined score
            archetype_scores[archetype] = (pattern_score * 0.6) + (trait_score * 0.4)
        
        # Get best archetype
        best_archetype = max(archetype_scores, key=archetype_scores.get)
        best_score = archetype_scores[best_archetype]
        
        return best_archetype, best_score
    
    def _extract_motivations(self, text: str) -> List[PurchaseMotivation]:
        """Extract purchase motivations from review text."""
        motivations = []
        
        for motivation, patterns in self._compiled_motivation_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    motivations.append(motivation)
                    break  # Only count each motivation once
        
        return motivations
    
    def _calculate_sentiment(
        self, 
        categories: Dict[str, int],
        rating: float
    ) -> float:
        """
        Calculate overall sentiment from word categories and rating.
        
        Returns value from -1 (very negative) to 1 (very positive).
        """
        pos = categories.get("emotion_positive", 0)
        neg = categories.get("emotion_negative", 0)
        
        # Word-based sentiment
        if pos + neg > 0:
            word_sentiment = (pos - neg) / (pos + neg)
        else:
            word_sentiment = 0.0
        
        # Rating-based sentiment (1-5 scale to -1 to 1)
        rating_sentiment = (rating - 3) / 2
        
        # Combine (weight rating more heavily)
        return (word_sentiment * 0.3) + (rating_sentiment * 0.7)
    
    def _extract_key_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        """
        Extract key phrases from review for language patterns.
        
        Looks for common positive/negative constructions.
        """
        phrases = []
        
        # Common phrase patterns
        patterns = [
            r"love (the |how |that |this )?[\w\s]{3,30}",
            r"(really |absolutely |definitely )?(great|amazing|excellent) [\w\s]{3,20}",
            r"(best|perfect) [\w\s]{3,30}",
            r"(finally|exactly) what [\w\s]{3,30}",
            r"would (definitely )?recommend",
            r"(highly|strongly) recommend",
            r"can't (believe|imagine|live) [\w\s]{3,20}",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(m for m in match if m)
                if match and len(match) > 5:
                    phrases.append(match.strip())
        
        return phrases[:max_phrases]
    
    def _calculate_confidence(
        self,
        word_count: int,
        categories: Dict[str, int],
        helpful_votes: int,
    ) -> float:
        """
        Calculate confidence in the analysis.
        
        Higher confidence for longer reviews with more signal words
        and more helpful votes.
        """
        # Word count factor (more words = more signal)
        word_factor = min(word_count / 100, 1.0)
        
        # Signal word factor
        total_signal = sum(
            categories.get(k, 0) 
            for k in categories 
            if k != "total_words"
        )
        signal_factor = min(total_signal / 10, 1.0)
        
        # Helpful votes factor
        helpful_factor = min(helpful_votes / 20, 0.3)
        
        # Combine
        confidence = (word_factor * 0.4) + (signal_factor * 0.3) + (helpful_factor)
        
        return min(confidence, 1.0)


# =============================================================================
# LANGUAGE PATTERN AGGREGATOR
# =============================================================================

class LanguagePatternAggregator:
    """
    Aggregates language patterns across multiple reviews.
    
    Produces LanguagePatterns for CustomerIntelligenceProfile.
    """
    
    def aggregate(
        self, 
        analyses: List[ReviewAnalysis]
    ) -> LanguagePatterns:
        """
        Aggregate language patterns from multiple reviews.
        
        Args:
            analyses: List of individual review analyses
            
        Returns:
            Aggregated LanguagePatterns
        """
        all_phrases = []
        all_power_words = []
        positive_triggers = []
        negative_triggers = []
        
        sentiment_sum = 0.0
        formality_sum = 0.0
        
        for analysis in analyses:
            # Collect phrases from positive reviews
            if analysis.rating >= 4:
                all_phrases.extend(analysis.reviewer_profile.key_phrases)
                
                # Extract power words from highly rated reviews
                for word in EMOTION_POSITIVE:
                    if word in analysis.review_text.lower():
                        all_power_words.append(word)
            
            # Track sentiment
            sentiment_sum += analysis.reviewer_profile.sentiment
            
            # Estimate formality (shorter sentences, more complex words = formal)
            words = analysis.review_text.split()
            avg_word_length = sum(len(w) for w in words) / max(len(words), 1)
            formality_sum += min(avg_word_length / 8, 1.0)
        
        # Count phrase frequencies
        phrase_counts = Counter(all_phrases)
        common_phrases = [p for p, _ in phrase_counts.most_common(20)]
        
        # Count power word frequencies
        power_counts = Counter(all_power_words)
        power_words = [w for w, _ in power_counts.most_common(15)]
        
        # Determine tone from average sentiment
        avg_sentiment = sentiment_sum / max(len(analyses), 1)
        if avg_sentiment > 0.3:
            tone = "enthusiastic"
        elif avg_sentiment > 0:
            tone = "positive"
        elif avg_sentiment < -0.3:
            tone = "critical"
        else:
            tone = "neutral"
        
        # Average formality
        avg_formality = formality_sum / max(len(analyses), 1)
        
        return LanguagePatterns(
            common_phrases=common_phrases,
            power_words=power_words,
            positive_triggers=positive_triggers,
            negative_triggers=negative_triggers,
            dominant_tone=tone,
            formality_score=avg_formality,
        )


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_analyzer_instance: Optional[ReviewPsychologicalAnalyzer] = None
_aggregator_instance: Optional[LanguagePatternAggregator] = None


def get_review_analyzer() -> ReviewPsychologicalAnalyzer:
    """Get or create the singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ReviewPsychologicalAnalyzer()
    return _analyzer_instance


def get_language_aggregator() -> LanguagePatternAggregator:
    """Get or create the singleton aggregator instance."""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = LanguagePatternAggregator()
    return _aggregator_instance
