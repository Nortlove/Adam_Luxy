# =============================================================================
# ADAM Amazon Linguistic Feature Extraction
# Location: adam/data/amazon/features.py
# =============================================================================

"""
LINGUISTIC FEATURE EXTRACTION

Extracts LIWC-style linguistic features from Amazon review text.
These features are the basis for Big Five personality inference.

Research foundation:
- Pennebaker & King (1999): Linguistic correlates of personality
- Tausczik & Pennebaker (2010): LIWC psychology of word use
- Yarkoni (2010): Blog language and Big Five
- Schwartz et al. (2013): Facebook language and personality

Key insight: Different personality types use language differently:
- HIGH OPENNESS: More articles, prepositions, longer words, varied vocabulary
- HIGH CONSCIENTIOUSNESS: Fewer negations, more achievement words
- HIGH EXTRAVERSION: More social words, positive emotion, first person plural
- HIGH AGREEABLENESS: More positive emotion, social words, fewer swear words
- HIGH NEUROTICISM: More negative emotion, first person singular, anxiety words
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

import structlog
from prometheus_client import Histogram

from adam.data.amazon.models import AmazonReview, LinguisticFeatures

logger = structlog.get_logger(__name__)

# =============================================================================
# METRICS
# =============================================================================

EXTRACTION_LATENCY = Histogram(
    "adam_amazon_feature_extraction_seconds",
    "Latency of linguistic feature extraction",
)


# =============================================================================
# WORD LISTS (subset of LIWC-style categories)
# =============================================================================

@dataclass
class WordLists:
    """LIWC-style word lists for feature extraction."""
    
    # Affective processes
    POSITIVE_EMOTION: List[str] = None
    NEGATIVE_EMOTION: List[str] = None
    ANXIETY: List[str] = None
    ANGER: List[str] = None
    SADNESS: List[str] = None
    
    # Cognitive processes
    INSIGHT: List[str] = None
    CAUSATION: List[str] = None
    DISCREPANCY: List[str] = None
    TENTATIVE: List[str] = None
    CERTAINTY: List[str] = None
    
    # Social
    SOCIAL: List[str] = None
    FAMILY: List[str] = None
    FRIENDS: List[str] = None
    
    # Personal concerns
    WORK: List[str] = None
    LEISURE: List[str] = None
    MONEY: List[str] = None
    
    def __post_init__(self):
        # Initialize word lists (subset for demonstration)
        self.POSITIVE_EMOTION = [
            "love", "nice", "sweet", "happy", "joy", "glad", "good", "great",
            "excellent", "wonderful", "amazing", "fantastic", "beautiful",
            "perfect", "awesome", "brilliant", "lovely", "delightful",
            "pleased", "satisfied", "enjoy", "excited", "grateful", "thankful"
        ]
        
        self.NEGATIVE_EMOTION = [
            "hate", "bad", "wrong", "awful", "terrible", "horrible", "poor",
            "disappointed", "disappointing", "frustrating", "frustrated",
            "annoying", "annoyed", "angry", "sad", "upset", "unhappy",
            "worst", "waste", "useless", "broken", "fail", "failed"
        ]
        
        self.ANXIETY = [
            "worried", "nervous", "anxious", "afraid", "scared", "fear",
            "stress", "stressed", "concern", "concerned", "uncertain"
        ]
        
        self.ANGER = [
            "angry", "mad", "furious", "hate", "disgust", "annoyed",
            "irritated", "outraged", "hostile"
        ]
        
        self.SADNESS = [
            "sad", "unhappy", "depressed", "disappointed", "hurt", "lonely",
            "grief", "miserable", "hopeless"
        ]
        
        self.INSIGHT = [
            "think", "know", "consider", "understand", "realize", "feel",
            "believe", "find", "found", "thought", "seems", "appear"
        ]
        
        self.CAUSATION = [
            "because", "cause", "effect", "hence", "therefore", "thus",
            "consequently", "reason", "why", "result"
        ]
        
        self.DISCREPANCY = [
            "should", "would", "could", "ought", "want", "need", "wish",
            "hope", "expect", "supposed"
        ]
        
        self.TENTATIVE = [
            "maybe", "perhaps", "guess", "might", "possibly", "probably",
            "seem", "seems", "appear", "appears", "almost"
        ]
        
        self.CERTAINTY = [
            "always", "never", "definitely", "certainly", "absolutely",
            "completely", "totally", "exact", "exactly", "sure", "clearly"
        ]
        
        self.SOCIAL = [
            "talk", "share", "friend", "friends", "family", "people",
            "person", "social", "together", "group", "team", "we", "us"
        ]
        
        self.FAMILY = [
            "family", "mom", "dad", "mother", "father", "parent", "parents",
            "child", "children", "kid", "kids", "son", "daughter", "husband",
            "wife", "brother", "sister"
        ]
        
        self.FRIENDS = [
            "friend", "friends", "buddy", "pal", "mate"
        ]
        
        self.WORK = [
            "work", "job", "office", "boss", "project", "meeting", "business",
            "career", "professional", "working"
        ]
        
        self.LEISURE = [
            "fun", "play", "game", "movie", "music", "travel", "vacation",
            "relax", "relaxing", "hobby", "entertainment"
        ]
        
        self.MONEY = [
            "money", "price", "cost", "buy", "bought", "sell", "cheap",
            "expensive", "dollar", "value", "worth", "afford", "pay", "paid"
        ]


WORD_LISTS = WordLists()


# =============================================================================
# BIG FIVE LINGUISTIC MARKERS
# =============================================================================

@dataclass
class BigFiveMarkers:
    """
    Word patterns associated with Big Five traits.
    
    Based on research by Yarkoni (2010) and Schwartz et al. (2013).
    """
    
    # Openness markers: intellectual, creative language
    OPENNESS: List[str] = None
    
    # Conscientiousness markers: organized, achievement-oriented
    CONSCIENTIOUSNESS: List[str] = None
    
    # Extraversion markers: social, positive language
    EXTRAVERSION: List[str] = None
    
    # Agreeableness markers: warm, cooperative language
    AGREEABLENESS: List[str] = None
    
    # Neuroticism markers: anxious, negative language  
    NEUROTICISM: List[str] = None
    
    def __post_init__(self):
        self.OPENNESS = [
            "creative", "art", "poetry", "philosophy", "universe", "imagine",
            "idea", "ideas", "discover", "explore", "curious", "interesting",
            "novel", "original", "innovative", "concept", "theory", "abstract"
        ]
        
        self.CONSCIENTIOUSNESS = [
            "organize", "organized", "plan", "planning", "schedule", "detail",
            "careful", "thorough", "efficient", "complete", "finish", "achieve",
            "accomplish", "goal", "goals", "responsible", "reliable", "duty"
        ]
        
        self.EXTRAVERSION = [
            "party", "social", "fun", "excited", "exciting", "adventure",
            "friends", "talk", "talking", "energy", "energetic", "outgoing",
            "active", "together", "group", "crowd"
        ]
        
        self.AGREEABLENESS = [
            "kind", "kindness", "help", "helpful", "support", "care", "caring",
            "generous", "trust", "trusting", "cooperate", "cooperation",
            "gentle", "compassion", "empathy", "understanding", "forgive"
        ]
        
        self.NEUROTICISM = [
            "worry", "worried", "anxious", "anxiety", "stress", "stressed",
            "nervous", "fear", "afraid", "sad", "sadness", "depressed",
            "overwhelmed", "upset", "frustrated", "irritated", "angry"
        ]


BIG_FIVE_MARKERS = BigFiveMarkers()


# =============================================================================
# FEATURE EXTRACTION SERVICE
# =============================================================================

class LinguisticFeatureExtractor:
    """
    Extracts linguistic features from review text.
    
    This is the core component for transforming raw text into
    psychological signals that can be used for Big Five inference.
    """
    
    def __init__(self):
        self._word_lists = WORD_LISTS
        self._big_five = BIG_FIVE_MARKERS
        self._log = structlog.get_logger(__name__)
    
    def extract(self, review: AmazonReview) -> LinguisticFeatures:
        """
        Extract linguistic features from a single review.
        
        Args:
            review: The Amazon review to process
            
        Returns:
            LinguisticFeatures with all extracted metrics
        """
        with EXTRACTION_LATENCY.time():
            return self._extract_features(review)
    
    def extract_batch(self, reviews: List[AmazonReview]) -> List[LinguisticFeatures]:
        """Extract features from a batch of reviews."""
        return [self.extract(r) for r in reviews]
    
    def _extract_features(self, review: AmazonReview) -> LinguisticFeatures:
        """Core feature extraction logic."""
        
        text = review.text.lower()
        words = self._tokenize(text)
        sentences = self._split_sentences(review.text)
        
        word_count = len(words)
        sentence_count = len(sentences)
        
        # Avoid division by zero
        if word_count == 0:
            word_count = 1
        if sentence_count == 0:
            sentence_count = 1
        
        # Basic counts
        avg_word_length = sum(len(w) for w in words) / word_count
        avg_sentence_length = word_count / sentence_count
        
        # Readability
        flesch = self._flesch_reading_ease(words, sentences)
        fk_grade = self._flesch_kincaid_grade(words, sentences)
        
        # LIWC-style categories
        positive = self._count_category(words, self._word_lists.POSITIVE_EMOTION) / word_count
        negative = self._count_category(words, self._word_lists.NEGATIVE_EMOTION) / word_count
        anxiety = self._count_category(words, self._word_lists.ANXIETY) / word_count
        anger = self._count_category(words, self._word_lists.ANGER) / word_count
        sadness = self._count_category(words, self._word_lists.SADNESS) / word_count
        
        insight = self._count_category(words, self._word_lists.INSIGHT) / word_count
        causation = self._count_category(words, self._word_lists.CAUSATION) / word_count
        discrepancy = self._count_category(words, self._word_lists.DISCREPANCY) / word_count
        tentative = self._count_category(words, self._word_lists.TENTATIVE) / word_count
        certainty = self._count_category(words, self._word_lists.CERTAINTY) / word_count
        
        social = self._count_category(words, self._word_lists.SOCIAL) / word_count
        family = self._count_category(words, self._word_lists.FAMILY) / word_count
        friends = self._count_category(words, self._word_lists.FRIENDS) / word_count
        
        work = self._count_category(words, self._word_lists.WORK) / word_count
        leisure = self._count_category(words, self._word_lists.LEISURE) / word_count
        money = self._count_category(words, self._word_lists.MONEY) / word_count
        
        # Pronouns and function words
        articles = self._count_words(words, ["a", "an", "the"]) / word_count
        prepositions = self._count_words(words, [
            "in", "on", "at", "to", "for", "with", "from", "by", "of"
        ]) / word_count
        personal_pronouns = self._count_words(words, [
            "i", "me", "my", "mine", "myself", "you", "your", "yours",
            "he", "him", "his", "she", "her", "hers", "we", "us", "our",
            "they", "them", "their"
        ]) / word_count
        first_singular = self._count_words(words, ["i", "me", "my", "mine", "myself"]) / word_count
        first_plural = self._count_words(words, ["we", "us", "our", "ours", "ourselves"]) / word_count
        
        # Sentiment (simple polarity)
        sentiment_score = (positive - negative) * 5  # Scale to [-5, 5] roughly
        sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp to [-1, 1]
        sentiment_magnitude = positive + negative
        
        # Big Five markers
        openness = self._count_category(words, self._big_five.OPENNESS) / word_count
        conscientiousness = self._count_category(words, self._big_five.CONSCIENTIOUSNESS) / word_count
        extraversion = self._count_category(words, self._big_five.EXTRAVERSION) / word_count
        agreeableness = self._count_category(words, self._big_five.AGREEABLENESS) / word_count
        neuroticism = self._count_category(words, self._big_five.NEUROTICISM) / word_count
        
        return LinguisticFeatures(
            review_id=review.review_id,
            user_id=review.user_id,
            
            word_count=len(words),
            sentence_count=len(sentences),
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            
            flesch_reading_ease=max(0, min(100, flesch)),
            flesch_kincaid_grade=max(0, fk_grade),
            
            positive_emotion=min(1.0, positive * 10),
            negative_emotion=min(1.0, negative * 10),
            anxiety=min(1.0, anxiety * 20),
            anger=min(1.0, anger * 20),
            sadness=min(1.0, sadness * 20),
            
            insight=min(1.0, insight * 10),
            causation=min(1.0, causation * 20),
            discrepancy=min(1.0, discrepancy * 10),
            tentative=min(1.0, tentative * 20),
            certainty=min(1.0, certainty * 20),
            
            social_words=min(1.0, social * 10),
            family=min(1.0, family * 20),
            friends=min(1.0, friends * 50),
            
            work=min(1.0, work * 20),
            leisure=min(1.0, leisure * 20),
            money=min(1.0, money * 10),
            
            articles=min(1.0, articles * 10),
            prepositions=min(1.0, prepositions * 5),
            personal_pronouns=min(1.0, personal_pronouns * 5),
            first_person_singular=min(1.0, first_singular * 10),
            first_person_plural=min(1.0, first_plural * 20),
            
            sentiment_score=sentiment_score,
            sentiment_magnitude=min(1.0, sentiment_magnitude * 10),
            
            openness_markers=min(1.0, openness * 20),
            conscientiousness_markers=min(1.0, conscientiousness * 20),
            extraversion_markers=min(1.0, extraversion * 20),
            agreeableness_markers=min(1.0, agreeableness * 20),
            neuroticism_markers=min(1.0, neuroticism * 15),
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        # Remove punctuation and split
        words = re.findall(r'\b[a-z]+\b', text.lower())
        return words
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _count_category(self, words: List[str], category: List[str]) -> int:
        """Count words matching a category."""
        category_set = set(category)
        return sum(1 for w in words if w in category_set)
    
    def _count_words(self, words: List[str], target_words: List[str]) -> int:
        """Count occurrences of specific words."""
        target_set = set(target_words)
        return sum(1 for w in words if w in target_set)
    
    def _flesch_reading_ease(self, words: List[str], sentences: List[str]) -> float:
        """Calculate Flesch Reading Ease score."""
        if len(words) == 0 or len(sentences) == 0:
            return 50.0
        
        # Estimate syllables (rough heuristic)
        syllables = sum(self._count_syllables(w) for w in words)
        
        # Flesch formula
        score = 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syllables / len(words))
        return score
    
    def _flesch_kincaid_grade(self, words: List[str], sentences: List[str]) -> float:
        """Calculate Flesch-Kincaid Grade Level."""
        if len(words) == 0 or len(sentences) == 0:
            return 8.0
        
        syllables = sum(self._count_syllables(w) for w in words)
        
        grade = 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59
        return max(0, grade)
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word."""
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith("e"):
            count -= 1
        
        return max(1, count)
