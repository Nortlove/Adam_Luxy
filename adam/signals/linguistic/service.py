# =============================================================================
# ADAM Linguistic Signal Service
# Location: adam/signals/linguistic/service.py
# =============================================================================

"""
LINGUISTIC SIGNAL SERVICE

Enterprise-grade service for extracting psychological signals from text.

Implements LIWC-style analysis with modern NLP enhancements:
- Word category counting (pronouns, emotions, cognitive markers)
- Temporal orientation detection
- Regulatory focus inference
- Big Five personality estimation

Research Foundation:
- Pennebaker & King (1999): Language and personality
- Yarkoni (2010): Big Five correlates of word use
- Schwartz et al. (2013): Facebook personality prediction
- Mairesse et al. (2007): Personality recognition from text
"""

import hashlib
import re
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter as PrometheusCounter, Histogram
    LINGUISTIC_ANALYSIS_LATENCY = Histogram(
        'adam_linguistic_analysis_seconds',
        'Time spent analyzing text for psychological signals',
        ['analysis_type']
    )
    LINGUISTIC_PROFILES_CREATED = PrometheusCounter(
        'adam_linguistic_profiles_total',
        'Total number of psychological profiles extracted',
        ['confidence_level']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from adam.signals.linguistic.models import (
    LinguisticSignal,
    LinguisticSignalType,
    LinguisticFeatures,
    TextPsychologyProfile,
    InferredBigFive,
    RegulatoryFocusSignal,
    EmotionalValence,
    TemporalMarkers,
    ProcessingState,
)


# =============================================================================
# WORD DICTIONARIES (LIWC-inspired)
# =============================================================================

# Pronoun categories
FIRST_PERSON_SINGULAR = {"i", "me", "my", "mine", "myself"}
FIRST_PERSON_PLURAL = {"we", "us", "our", "ours", "ourselves"}
SECOND_PERSON = {"you", "your", "yours", "yourself", "yourselves"}
THIRD_PERSON = {"he", "she", "they", "them", "him", "her", "his", "hers", "their", "theirs"}

# Temporal markers
PAST_MARKERS = {
    "was", "were", "had", "been", "did", "used", "ago", "before", "earlier",
    "yesterday", "previously", "once", "former", "past", "remembered"
}
PRESENT_MARKERS = {
    "is", "am", "are", "now", "today", "currently", "presently", "right",
    "this", "being", "existing", "happening", "ongoing"
}
FUTURE_MARKERS = {
    "will", "shall", "going", "gonna", "tomorrow", "later", "soon", "next",
    "future", "plan", "intend", "expect", "hope", "upcoming", "eventually"
}

# Emotion words
POSITIVE_EMOTIONS = {
    "love", "happy", "joy", "wonderful", "great", "excellent", "amazing",
    "fantastic", "good", "nice", "beautiful", "perfect", "excited", "glad",
    "pleased", "delighted", "grateful", "thankful", "blessed", "awesome"
}
NEGATIVE_EMOTIONS = {
    "hate", "sad", "angry", "terrible", "awful", "horrible", "bad",
    "disappointed", "frustrated", "upset", "worried", "anxious", "fear",
    "afraid", "scared", "unhappy", "miserable", "annoyed", "irritated"
}
ANXIETY_WORDS = {"worried", "nervous", "anxious", "afraid", "scared", "fear", "panic"}
ANGER_WORDS = {"angry", "mad", "furious", "annoyed", "frustrated", "irritated", "rage"}
SADNESS_WORDS = {"sad", "depressed", "unhappy", "miserable", "grief", "sorrow", "crying"}

# Cognitive process words
INSIGHT_WORDS = {"think", "know", "consider", "understand", "realize", "believe", "feel"}
CAUSATION_WORDS = {"because", "effect", "hence", "therefore", "thus", "cause", "result"}
DISCREPANCY_WORDS = {"should", "would", "could", "might", "ought", "maybe", "perhaps"}
TENTATIVE_WORDS = {"maybe", "perhaps", "guess", "possibly", "probably", "might", "could"}
CERTAINTY_WORDS = {"always", "never", "definitely", "certainly", "absolutely", "sure"}

# Social words
SOCIAL_WORDS = {"friend", "family", "talk", "share", "together", "group", "people", "social"}
FAMILY_WORDS = {"family", "mother", "father", "parent", "child", "sister", "brother", "son", "daughter"}
FRIEND_WORDS = {"friend", "buddy", "pal", "mate", "companion"}

# Regulatory focus (Higgins, 1997)
PROMOTION_WORDS = {
    "achieve", "win", "gain", "success", "accomplish", "goal", "grow", "advance",
    "opportunity", "aspire", "dream", "hope", "eager", "ideal", "wish", "desire"
}
PREVENTION_WORDS = {
    "safe", "secure", "protect", "avoid", "prevent", "careful", "cautious",
    "responsible", "duty", "obligation", "should", "ought", "must", "loss", "risk"
}

# Articles, prepositions, conjunctions
ARTICLES = {"the", "a", "an"}
PREPOSITIONS = {"in", "on", "at", "to", "for", "with", "by", "from", "about", "into"}
CONJUNCTIONS = {"and", "but", "or", "nor", "yet", "so", "although", "because", "while"}
NEGATIONS = {"not", "no", "never", "neither", "nobody", "nothing", "none", "nowhere"}

# Filler and swear words
FILLER_WORDS = {"um", "uh", "like", "basically", "actually", "literally", "honestly"}
SWEAR_WORDS = {"damn", "hell", "crap"}  # Abbreviated for production


# =============================================================================
# BIG FIVE MAPPINGS
# =============================================================================

# Research-based mappings from linguistic features to Big Five
# Based on Yarkoni (2010), Schwartz et al. (2013)
BIG_FIVE_LINGUISTIC_WEIGHTS = {
    "openness": {
        "word_length_avg": 0.12,
        "unique_words_ratio": 0.15,
        "insight": 0.10,
        "prepositions": 0.08,
        "articles": 0.05,
        "positive_emotion": 0.08,
        "first_person_singular": -0.05,
    },
    "conscientiousness": {
        "word_length_avg": 0.08,
        "certainty": 0.12,
        "achievement": 0.15,
        "discrepancy": -0.10,
        "negations": -0.08,
        "swear_words": -0.15,
    },
    "extraversion": {
        "first_person_plural": 0.12,
        "social": 0.18,
        "positive_emotion": 0.15,
        "word_count": 0.05,  # More words = more extraverted
        "first_person_singular": -0.08,
    },
    "agreeableness": {
        "positive_emotion": 0.15,
        "social": 0.12,
        "first_person_plural": 0.10,
        "anger": -0.18,
        "swear_words": -0.12,
        "negations": -0.08,
    },
    "neuroticism": {
        "negative_emotion": 0.18,
        "anxiety": 0.20,
        "first_person_singular": 0.12,
        "certainty": -0.10,
        "positive_emotion": -0.12,
    },
}


# =============================================================================
# LINGUISTIC SIGNAL SERVICE
# =============================================================================

class LinguisticSignalService:
    """
    Service for extracting psychological signals from text.
    
    Provides LIWC-style linguistic analysis with:
    - Word category counting
    - Big Five inference
    - Regulatory focus detection
    - Emotional state extraction
    - Temporal orientation analysis
    
    Emits Learning Signals:
    - PERSONALITY signal on profile extraction
    - REGULATORY_FOCUS signal on focus detection
    """
    
    def __init__(
        self,
        gradient_bridge=None,
        min_words_for_inference: int = 50,
        cache_enabled: bool = True,
    ):
        """
        Initialize the linguistic signal service.
        
        Args:
            gradient_bridge: Optional GradientBridge for learning signals
            min_words_for_inference: Minimum words for reliable inference
            cache_enabled: Whether to cache analysis results
        """
        self._gradient_bridge = gradient_bridge
        self._min_words = min_words_for_inference
        self._cache_enabled = cache_enabled
        self._cache: Dict[str, TextPsychologyProfile] = {}
        
        logger.info("LinguisticSignalService initialized")
    
    def analyze_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> TextPsychologyProfile:
        """
        Analyze text and extract psychological profile.
        
        Args:
            text: Text to analyze
            user_id: Optional user ID for attribution
            session_id: Optional session ID
            
        Returns:
            TextPsychologyProfile with inferred psychological signals
            
        Metrics Emitted:
            - adam_linguistic_analysis_seconds: Analysis latency
            - adam_linguistic_profiles_total: Profile count by confidence
        """
        start_time = time.monotonic()
        
        if not text or len(text.strip()) == 0:
            return TextPsychologyProfile(word_count=0, overall_confidence=0.0)
        
        # Check cache
        text_hash = self._hash_text(text)
        if self._cache_enabled and text_hash in self._cache:
            return self._cache[text_hash]
        
        # Extract features
        features = self._extract_features(text)
        
        # Determine confidence based on word count
        base_confidence = min(1.0, features.word_count / 200)  # Full confidence at 200 words
        
        if features.word_count < self._min_words:
            # Low confidence for short texts
            profile = TextPsychologyProfile(
                source_text_hash=text_hash,
                word_count=features.word_count,
                raw_features=features,
                overall_confidence=base_confidence * 0.5,
            )
        else:
            # Full analysis
            big_five = self._infer_big_five(features)
            regulatory_focus = self._infer_regulatory_focus(features)
            emotional_state = self._extract_emotional_state(features)
            temporal = self._extract_temporal_orientation(features)
            processing_state = self._infer_processing_state(features)
            
            # Determine recommended strategies
            recommended_construal = "abstract" if big_five.openness > 0.6 else "concrete"
            if regulatory_focus.promotion_focus > regulatory_focus.prevention_focus + 0.15:
                recommended_framing = "gain"
            elif regulatory_focus.prevention_focus > regulatory_focus.promotion_focus + 0.15:
                recommended_framing = "loss"
            else:
                recommended_framing = "balanced"
            
            profile = TextPsychologyProfile(
                source_text_hash=text_hash,
                word_count=features.word_count,
                big_five=big_five,
                regulatory_focus=regulatory_focus,
                emotional_state=emotional_state,
                temporal_orientation=temporal,
                processing_state=processing_state,
                cognitive_complexity=self._compute_complexity(features),
                raw_features=features,
                recommended_construal=recommended_construal,
                recommended_framing=recommended_framing,
                overall_confidence=base_confidence * 0.8,
            )
        
        # Cache result
        if self._cache_enabled:
            self._cache[text_hash] = profile
        
        # Track metrics
        elapsed = time.monotonic() - start_time
        if PROMETHEUS_AVAILABLE:
            LINGUISTIC_ANALYSIS_LATENCY.labels(analysis_type='full').observe(elapsed)
            confidence_level = 'high' if profile.overall_confidence > 0.6 else 'medium' if profile.overall_confidence > 0.3 else 'low'
            LINGUISTIC_PROFILES_CREATED.labels(confidence_level=confidence_level).inc()
        
        # Emit learning signal to Gradient Bridge
        if self._gradient_bridge and profile.overall_confidence > 0.4:
            try:
                self._gradient_bridge.emit_signal_sync(
                    signal_type="LINGUISTIC_PROFILE_EXTRACTED",
                    payload={
                        "user_id": user_id,
                        "session_id": session_id,
                        "word_count": profile.word_count,
                        "regulatory_focus": profile.regulatory_focus.dominant_focus if profile.regulatory_focus else None,
                        "confidence": profile.overall_confidence,
                    }
                )
            except Exception as e:
                logger.debug("gradient_bridge_signal_failed", error=str(e))
        
        return profile
    
    def create_signal(
        self,
        text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        signal_type: LinguisticSignalType = LinguisticSignalType.PERSONALITY,
    ) -> LinguisticSignal:
        """
        Create a learning signal from text analysis.
        
        Args:
            text: Text to analyze
            user_id: User ID for attribution
            session_id: Session ID
            signal_type: Type of signal to emit
            
        Returns:
            LinguisticSignal for the learning system
        """
        profile = self.analyze_text(text, user_id, session_id)
        
        signal = LinguisticSignal(
            signal_type=signal_type,
            user_id=user_id,
            session_id=session_id,
            profile=profile,
            confidence=profile.overall_confidence,
            affects_profile=profile.overall_confidence > 0.5,
            profile_update_weight=min(0.5, profile.overall_confidence),
        )
        
        return signal
    
    def _extract_features(self, text: str) -> LinguisticFeatures:
        """Extract LIWC-style features from text."""
        
        # Tokenize
        words = self._tokenize(text)
        sentences = self._split_sentences(text)
        
        word_count = len(words)
        sentence_count = len(sentences)
        
        if word_count == 0:
            return LinguisticFeatures(word_count=0)
        
        # Word set for unique ratio
        word_set = set(w.lower() for w in words)
        words_lower = [w.lower() for w in words]
        word_counter = Counter(words_lower)
        
        # Compute features
        features = LinguisticFeatures(
            word_count=word_count,
            sentence_count=sentence_count,
            words_per_sentence=word_count / max(1, sentence_count),
            
            # Lexical
            word_length_avg=sum(len(w) for w in words) / word_count,
            long_words_ratio=sum(1 for w in words if len(w) > 6) / word_count,
            unique_words_ratio=len(word_set) / word_count,
            
            # Pronouns
            first_person_singular=self._category_ratio(word_counter, FIRST_PERSON_SINGULAR, word_count),
            first_person_plural=self._category_ratio(word_counter, FIRST_PERSON_PLURAL, word_count),
            second_person=self._category_ratio(word_counter, SECOND_PERSON, word_count),
            third_person=self._category_ratio(word_counter, THIRD_PERSON, word_count),
            
            # Temporal
            past_focus=self._category_ratio(word_counter, PAST_MARKERS, word_count),
            present_focus=self._category_ratio(word_counter, PRESENT_MARKERS, word_count),
            future_focus=self._category_ratio(word_counter, FUTURE_MARKERS, word_count),
            
            # Emotion
            positive_emotion=self._category_ratio(word_counter, POSITIVE_EMOTIONS, word_count),
            negative_emotion=self._category_ratio(word_counter, NEGATIVE_EMOTIONS, word_count),
            anxiety=self._category_ratio(word_counter, ANXIETY_WORDS, word_count),
            anger=self._category_ratio(word_counter, ANGER_WORDS, word_count),
            sadness=self._category_ratio(word_counter, SADNESS_WORDS, word_count),
            
            # Cognitive
            insight=self._category_ratio(word_counter, INSIGHT_WORDS, word_count),
            causation=self._category_ratio(word_counter, CAUSATION_WORDS, word_count),
            discrepancy=self._category_ratio(word_counter, DISCREPANCY_WORDS, word_count),
            tentative=self._category_ratio(word_counter, TENTATIVE_WORDS, word_count),
            certainty=self._category_ratio(word_counter, CERTAINTY_WORDS, word_count),
            
            # Social
            social=self._category_ratio(word_counter, SOCIAL_WORDS, word_count),
            family=self._category_ratio(word_counter, FAMILY_WORDS, word_count),
            friends=self._category_ratio(word_counter, FRIEND_WORDS, word_count),
            
            # Regulatory focus
            achievement=self._category_ratio(word_counter, PROMOTION_WORDS, word_count),
            risk=self._category_ratio(word_counter, PREVENTION_WORDS, word_count),
            
            # Structural
            articles=self._category_ratio(word_counter, ARTICLES, word_count),
            prepositions=self._category_ratio(word_counter, PREPOSITIONS, word_count),
            conjunctions=self._category_ratio(word_counter, CONJUNCTIONS, word_count),
            negations=self._category_ratio(word_counter, NEGATIONS, word_count),
            
            # Quality
            swear_words=self._category_ratio(word_counter, SWEAR_WORDS, word_count),
            filler_words=self._category_ratio(word_counter, FILLER_WORDS, word_count),
        )
        
        return features
    
    def _infer_big_five(self, features: LinguisticFeatures) -> InferredBigFive:
        """Infer Big Five personality from linguistic features."""
        
        scores = {}
        confidences = {}
        
        for trait, weights in BIG_FIVE_LINGUISTIC_WEIGHTS.items():
            score = 0.5  # Base
            weight_sum = 0.0
            
            for feature_name, weight in weights.items():
                feature_value = getattr(features, feature_name, 0.0)
                
                # Normalize feature value (most are ratios 0-1, word_count needs special handling)
                if feature_name == "word_count":
                    normalized = min(1.0, feature_value / 500)  # Normalize to 500 words
                elif feature_name == "word_length_avg":
                    normalized = min(1.0, (feature_value - 3) / 5)  # 3-8 char range
                else:
                    normalized = min(1.0, feature_value * 20)  # Scale up small ratios
                
                score += weight * (normalized - 0.5)
                weight_sum += abs(weight)
            
            # Clamp to 0-1
            scores[trait] = max(0.1, min(0.9, score))
            
            # Confidence based on weight coverage
            confidences[trait] = min(0.8, 0.4 + weight_sum)
        
        return InferredBigFive(
            openness=scores["openness"],
            conscientiousness=scores["conscientiousness"],
            extraversion=scores["extraversion"],
            agreeableness=scores["agreeableness"],
            neuroticism=scores["neuroticism"],
            openness_confidence=confidences["openness"],
            conscientiousness_confidence=confidences["conscientiousness"],
            extraversion_confidence=confidences["extraversion"],
            agreeableness_confidence=confidences["agreeableness"],
            neuroticism_confidence=confidences["neuroticism"],
            overall_confidence=sum(confidences.values()) / 5,
        )
    
    def _infer_regulatory_focus(self, features: LinguisticFeatures) -> RegulatoryFocusSignal:
        """Infer regulatory focus from linguistic features."""
        
        promo = 0.5 + features.achievement * 10 - features.risk * 5
        prev = 0.5 + features.risk * 10 - features.achievement * 5
        
        # Normalize
        total = promo + prev
        if total > 0:
            promo = promo / total
            prev = prev / total
        else:
            promo = prev = 0.5
        
        if promo > prev + 0.15:
            dominant = "promotion"
        elif prev > promo + 0.15:
            dominant = "prevention"
        else:
            dominant = "balanced"
        
        return RegulatoryFocusSignal(
            promotion_focus=promo,
            prevention_focus=prev,
            dominant_focus=dominant,
            confidence=0.6 + (abs(promo - prev) * 0.4),
        )
    
    def _extract_emotional_state(self, features: LinguisticFeatures) -> EmotionalValence:
        """Extract emotional state from features."""
        
        # Valence from positive - negative
        valence = (features.positive_emotion - features.negative_emotion) * 10
        valence = max(-1.0, min(1.0, valence))
        
        # Arousal from emotion intensity
        arousal = (features.positive_emotion + features.negative_emotion + features.anxiety + features.anger) * 5
        arousal = min(1.0, 0.3 + arousal)
        
        # Primary emotion
        emotion_scores = {
            "joy": features.positive_emotion,
            "anxiety": features.anxiety,
            "anger": features.anger,
            "sadness": features.sadness,
        }
        primary = max(emotion_scores, key=emotion_scores.get)
        intensity = emotion_scores[primary]
        
        return EmotionalValence(
            valence=valence,
            arousal=arousal,
            dominance=0.5 + valence * 0.2,  # Positive = more dominant
            primary_emotion=primary if intensity > 0.01 else None,
            emotion_intensity=min(1.0, intensity * 20),
            confidence=0.65,
        )
    
    def _extract_temporal_orientation(self, features: LinguisticFeatures) -> TemporalMarkers:
        """Extract temporal orientation from features."""
        
        total = features.past_focus + features.present_focus + features.future_focus
        
        if total > 0:
            past = features.past_focus / total
            present = features.present_focus / total
            future = features.future_focus / total
        else:
            past = present = future = 0.33
        
        # Determine dominant
        if past > present and past > future:
            dominant = "past"
        elif future > past and future > present:
            dominant = "future"
        else:
            dominant = "present"
        
        return TemporalMarkers(
            past_orientation=past,
            present_orientation=present,
            future_orientation=future,
            dominant_orientation=dominant,
            planning_language=features.future_focus * 5,
            reflection_language=features.past_focus * 5,
            immediacy_language=features.present_focus * 5,
            confidence=0.7 if total > 0.01 else 0.4,
        )
    
    def _infer_processing_state(self, features: LinguisticFeatures) -> ProcessingState:
        """Infer cognitive processing state."""
        
        # Analytical markers
        analytical = features.insight + features.causation + features.certainty
        
        # Emotional markers
        emotional = features.positive_emotion + features.negative_emotion + features.anxiety
        
        # Intuitive markers (tentative, quick)
        intuitive = features.tentative + features.filler_words
        
        if analytical > emotional and analytical > intuitive:
            return ProcessingState.ANALYTICAL
        elif emotional > analytical and emotional > intuitive:
            return ProcessingState.EMOTIONAL
        elif intuitive > analytical and intuitive > emotional:
            return ProcessingState.INTUITIVE
        else:
            return ProcessingState.MIXED
    
    def _compute_complexity(self, features: LinguisticFeatures) -> float:
        """Compute cognitive complexity of text."""
        
        # Complexity indicators
        complexity = 0.5
        complexity += features.word_length_avg * 0.05  # Longer words
        complexity += features.unique_words_ratio * 0.2  # More unique words
        complexity += features.prepositions * 2  # More complex sentence structure
        complexity += features.insight * 2  # Cognitive process words
        complexity -= features.filler_words * 3  # Fillers reduce complexity
        
        return max(0.1, min(0.9, complexity))
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization.
        
        Args:
            text: Raw text to tokenize
            
        Returns:
            List of lowercase words
        """
        return re.findall(r'\b\w+\b', text.lower())
    
    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitting.
        
        Args:
            text: Raw text to split
            
        Returns:
            List of sentences
        """
        return re.split(r'[.!?]+', text)
    
    def _category_ratio(self, counter: Counter, category: Set[str], total: int) -> float:
        """Compute ratio of category words.
        
        Args:
            counter: Word frequency counter
            category: Set of category words to count
            total: Total word count for normalization
            
        Returns:
            Ratio of category words (0.0-1.0)
        """
        if total == 0:
            return 0.0
        count = sum(counter.get(word, 0) for word in category)
        return count / total
    
    def _hash_text(self, text: str) -> str:
        """Create hash of text for caching.
        
        Args:
            text: Text to hash
            
        Returns:
            16-character MD5 hash
        """
        return hashlib.md5(text.encode()).hexdigest()[:16]
