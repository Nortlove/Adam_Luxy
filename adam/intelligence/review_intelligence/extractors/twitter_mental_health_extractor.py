"""
Twitter Mental Health Intelligence Extractor
=============================================

THE EMOTIONAL STATE LAYER

Unique Value: 11.8M tweets with MENTAL HEALTH CLASSIFICATIONS:
- Depression (2.4M)
- Anxiety (1.1M)
- PTSD (1.1M)
- Bipolar (489K)
- Borderline (187K)
- Panic (73K)
- Control (6.5M baseline)

Plus:
- Pre-computed emotion scores (anger, fear, joy, sadness, etc.)
- Music sharing patterns linked to mental states
- Temporal patterns (when do different states post?)

Cookie-Less Power:
- Language patterns → Emotional state inference
- Music preferences → Psychological profile
- Ethical safeguards for sensitive targeting

CRITICAL: This data is used for SUPPORTIVE messaging, never exploitation.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Set
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
import re

from ..base_extractor import (
    BaseReviewExtractor,
    ExtractionResult,
    AggregatedIntelligence,
    DataSource,
    PsychologicalConstruct,
    Archetype,
    PersuasionMechanism,
)
from .. import IntelligenceLayer

logger = logging.getLogger(__name__)


# =============================================================================
# MENTAL HEALTH AWARE DATA STRUCTURES
# =============================================================================

class MentalHealthState:
    """Mental health state classifications."""
    CONTROL = "control"  # Baseline/no indication
    DEPRESSION = "depression"
    ANXIETY = "anxiety"
    PTSD = "ptsd"
    BIPOLAR = "bipolar"
    BORDERLINE = "borderline"
    PANIC = "panic"


@dataclass
class EmotionalProfile:
    """Emotional profile extracted from Twitter data."""
    
    # Core emotion scores (pre-computed in dataset)
    anger: float = 0.0
    disgust: float = 0.0
    fear: float = 0.0
    joy: float = 0.0
    neutral: float = 0.0
    sadness: float = 0.0
    surprise: float = 0.0
    
    # Mental health indicator
    disorder_indicator: str = MentalHealthState.CONTROL
    
    # Sentiment
    sentiment_direction: Optional[str] = None  # positive/negative/neutral
    sentiment_score: Optional[float] = None
    
    # Behavioral patterns
    posting_hour_distribution: Dict[int, float] = field(default_factory=dict)
    music_genre_preferences: Dict[str, float] = field(default_factory=dict)


@dataclass
class LanguagePattern:
    """Language pattern associated with emotional states."""
    
    pattern_type: str  # "word", "phrase", "structure"
    pattern: str
    associated_states: List[str]  # Which mental states use this pattern
    frequency_by_state: Dict[str, float]  # state -> relative frequency
    
    # For mechanism targeting
    mechanism_implications: Dict[str, float]  # mechanism -> effectiveness modifier


@dataclass
class EmotionalStateSafeguard:
    """Safeguard rules for ethical targeting."""
    
    state: str
    
    # Mechanisms to AVOID for this state
    avoid_mechanisms: List[str]
    
    # Mechanisms that may be SUPPORTIVE
    supportive_mechanisms: List[str]
    
    # Content to avoid
    avoid_topics: List[str]
    
    # Recommended approach
    recommended_approach: str


# =============================================================================
# SAFEGUARD DEFINITIONS
# =============================================================================

EMOTIONAL_SAFEGUARDS = {
    MentalHealthState.DEPRESSION: EmotionalStateSafeguard(
        state=MentalHealthState.DEPRESSION,
        avoid_mechanisms=[
            "fear_appeal",  # Don't amplify negative emotions
            "scarcity",  # Don't create pressure
            "fomo",  # Don't trigger comparison
            "social_comparison",  # Don't trigger inadequacy
        ],
        supportive_mechanisms=[
            "unity",  # Belonging helps
            "social_proof",  # Others experience this too
            "storytelling",  # Emotional connection
            "hope",  # Future-oriented
        ],
        avoid_topics=[
            "failure", "loss", "isolation", "perfection"
        ],
        recommended_approach="gentle_supportive_inclusive"
    ),
    MentalHealthState.ANXIETY: EmotionalStateSafeguard(
        state=MentalHealthState.ANXIETY,
        avoid_mechanisms=[
            "scarcity",  # Creates pressure/urgency
            "fear_appeal",  # Amplifies worry
            "urgency",  # Triggers stress
            "surprise",  # Unpredictability is stressful
        ],
        supportive_mechanisms=[
            "trust",  # Reduces uncertainty
            "authority",  # Expert reassurance
            "commitment_consistency",  # Predictability
            "authenticity",  # No hidden agenda
        ],
        avoid_topics=[
            "risk", "danger", "deadline", "limited time"
        ],
        recommended_approach="calm_reassuring_predictable"
    ),
    MentalHealthState.PTSD: EmotionalStateSafeguard(
        state=MentalHealthState.PTSD,
        avoid_mechanisms=[
            "fear_appeal",  # Can trigger
            "surprise",  # Avoid unexpected
            "urgency",  # Creates stress
            "nostalgia",  # Can trigger memories
        ],
        supportive_mechanisms=[
            "trust",
            "safety",
            "control",  # Sense of agency
            "unity",  # Community support
        ],
        avoid_topics=[
            "trauma", "violence", "accident", "sudden"
        ],
        recommended_approach="safe_controlled_transparent"
    ),
}


# =============================================================================
# TWITTER MENTAL HEALTH EXTRACTOR
# =============================================================================

class TwitterMentalHealthExtractor(BaseReviewExtractor):
    """
    Extractor for Twitter mental health dataset.
    
    This extractor builds:
    1. Emotional state → language pattern mappings
    2. Music → psychology correlations
    3. Safeguard rules for ethical targeting
    4. Temporal patterns by emotional state
    
    ETHICAL PRINCIPLES:
    - Never target vulnerable states for exploitation
    - Use insights for supportive/appropriate messaging
    - Respect privacy - use aggregated patterns only
    - Enable opt-out from sensitive targeting
    """
    
    def __init__(
        self,
        data_path: Path,
        batch_size: int = 1000,
    ):
        super().__init__(
            data_source=DataSource.TWITTER_MENTAL_HEALTH,
            data_path=data_path,
            batch_size=batch_size,
        )
        
        # State-specific language patterns
        self._language_patterns: Dict[str, List[LanguagePattern]] = defaultdict(list)
        
        # Music-emotion correlations
        self._music_emotion_map: Dict[str, EmotionalProfile] = {}
        
        # Temporal patterns
        self._state_temporal_patterns: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        
        # Safeguards
        self.safeguards = EMOTIONAL_SAFEGUARDS
        
        # Initialize state-specific markers
        self._init_emotional_markers()
    
    def _init_emotional_markers(self):
        """Initialize markers specific to emotional states."""
        
        # Language patterns associated with depression
        self.depression_markers = [
            "tired", "exhausted", "empty", "numb", "pointless",
            "worthless", "alone", "hopeless", "can't", "anymore",
            "give up", "no energy", "what's the point", "don't care",
            "sleep all day", "can't sleep", "crying", "sad",
        ]
        
        # Language patterns associated with anxiety
        self.anxiety_markers = [
            "worried", "anxious", "panic", "nervous", "scared",
            "what if", "afraid", "overwhelmed", "stress", "can't relax",
            "racing thoughts", "heart pounding", "can't breathe",
            "overthinking", "worst case", "catastrophe",
        ]
        
        # Language patterns associated with positive states
        self.positive_markers = [
            "happy", "excited", "grateful", "blessed", "amazing",
            "wonderful", "love", "joy", "thrilled", "fantastic",
            "best day", "can't wait", "so good", "awesome",
        ]
        
        # Device/platform psychological associations
        self.device_psychology = {
            "Twitter for iPhone": {
                "likely_demographic": "younger_affluent",
                "posting_context": "mobile_on_the_go",
            },
            "Twitter for Android": {
                "likely_demographic": "broader_mainstream",
                "posting_context": "mobile_varied",
            },
            "Twitter Web App": {
                "likely_demographic": "professional_desktop",
                "posting_context": "deliberate_considered",
            },
        }
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def iter_reviews(self) -> Iterator[Dict[str, Any]]:
        """Iterate over tweets (treated as reviews of emotional state)."""
        tweet_file = self.data_path / "tweet_profiles_anonymized.csv"
        
        if not tweet_file.exists():
            logger.error(f"Tweet file not found: {tweet_file}")
            return
        
        try:
            with open(tweet_file, 'r', encoding='utf-8') as f:
                # Handle large field sizes
                csv.field_size_limit(500000)
                reader = csv.DictReader(f)
                
                for row in reader:
                    yield row
        except Exception as e:
            logger.error(f"Error reading tweet file: {e}")
    
    def iter_music_profiles(self) -> Iterator[Dict[str, Any]]:
        """Iterate over music sharing profiles."""
        music_file = self.data_path / "musics_profiles_anonymized.csv"
        
        if not music_file.exists():
            logger.warning(f"Music file not found: {music_file}")
            return
        
        try:
            with open(music_file, 'r', encoding='utf-8') as f:
                csv.field_size_limit(500000)
                reader = csv.DictReader(f)
                
                for row in reader:
                    yield row
        except Exception as e:
            logger.error(f"Error reading music file: {e}")
    
    def iter_user_profiles(self) -> Iterator[Dict[str, Any]]:
        """Iterate over user profiles."""
        user_file = self.data_path / "user_profiles_anonymized.csv"
        
        if not user_file.exists():
            logger.warning(f"User file not found: {user_file}")
            return
        
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
        except Exception as e:
            logger.error(f"Error reading user file: {e}")
    
    def extract_review_text(self, review: Dict[str, Any]) -> str:
        """
        For Twitter, there's no direct text in tweet_profiles.
        Text is in the music profiles (lyrics) or inferred from patterns.
        """
        # Tweet profiles don't have text content
        # Return empty - we use other signals
        return ""
    
    def extract_rating(self, review: Dict[str, Any]) -> Optional[float]:
        """
        No direct rating, but we can infer from:
        - like_count (positive signal)
        - retweet_count (engagement)
        """
        try:
            likes = int(review.get('like_count', 0) or 0)
            retweets = int(review.get('retweet_count', 0) or 0)
            
            # Normalize engagement as a "rating"
            engagement = likes + retweets * 2  # Retweets weighted higher
            
            # Log scale normalization (most tweets have low engagement)
            if engagement == 0:
                return 0.5  # Neutral
            elif engagement < 10:
                return 0.6
            elif engagement < 100:
                return 0.7
            elif engagement < 1000:
                return 0.8
            else:
                return 0.9
        except:
            return 0.5
    
    def extract_helpful_signal(self, review: Dict[str, Any]) -> Optional[float]:
        """Use engagement as helpful signal."""
        return self.extract_rating(review)
    
    def extract_context(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Extract rich contextual information from tweets."""
        context = {
            'disorder': review.get('disorder', MentalHealthState.CONTROL),
            'tweet_type': review.get('tweet_type'),
            'language': review.get('lang'),
            'source': review.get('source'),  # Device/app
            'created_at': review.get('created_at'),
        }
        
        # Extract temporal context
        created_at = review.get('created_at')
        if created_at:
            try:
                # Parse datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                context['hour_of_day'] = dt.hour
                context['day_of_week'] = dt.weekday()
                context['is_night'] = 22 <= dt.hour or dt.hour <= 5
            except:
                pass
        
        # Device psychology
        source = review.get('source', '')
        if source in self.device_psychology:
            context['device_psychology'] = self.device_psychology[source]
        
        return context
    
    def get_unique_value(self) -> str:
        """Return what makes Twitter Mental Health uniquely valuable."""
        return """
        EMOTIONAL STATE INTELLIGENCE LAYER
        
        1. MENTAL HEALTH CLASSIFICATIONS: Real labels for 11.8M users
           - Depression: 2.4M tweets
           - Anxiety: 1.1M tweets
           - PTSD: 1.1M tweets
           - Bipolar: 489K tweets
           - Control: 6.5M baseline
           → Build: LANGUAGE_PATTERN → EMOTIONAL_STATE classifiers
        
        2. PRE-COMPUTED EMOTION SCORES: 7 emotion dimensions
           - Anger, Disgust, Fear, Joy, Neutral, Sadness, Surprise
           → Direct feed into UserStateAtom
        
        3. MUSIC-MOOD CORRELATIONS: What music do different states share?
           → Map: MUSIC_GENRE → PSYCHOLOGICAL_STATE
           → Power iHeart audio targeting
        
        4. TEMPORAL PATTERNS: When do different states post?
           - Depression posts more at night
           - Anxiety spikes certain hours
           → Temporal targeting with sensitivity
        
        5. DEVICE PATTERNS: iOS vs Android vs Web
           → Different mindsets, different contexts
        
        ETHICAL IMPERATIVE:
        - NEVER exploit vulnerable states
        - Use for SUPPORTIVE messaging only
        - Enable safeguards and opt-outs
        """
    
    def extract_dataset_specific_signals(
        self, review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Twitter-specific signals."""
        signals = {}
        
        # Mental health state
        disorder = review.get('disorder', MentalHealthState.CONTROL)
        signals['mental_health_state'] = disorder
        signals['is_control_group'] = disorder == MentalHealthState.CONTROL
        
        # Engagement metrics
        signals['like_count'] = int(review.get('like_count', 0) or 0)
        signals['retweet_count'] = int(review.get('retweet_count', 0) or 0)
        signals['reply_count'] = int(review.get('reply_count', 0) or 0)
        signals['quote_count'] = int(review.get('quote_count', 0) or 0)
        
        # Tweet characteristics
        signals['tweet_type'] = review.get('tweet_type')
        signals['is_retweet'] = review.get('referenced_tweet_type') == 'retweeted'
        signals['is_reply'] = review.get('referenced_tweet_type') == 'replied_to'
        
        # Device/platform
        signals['platform'] = review.get('source')
        
        return signals
    
    # =========================================================================
    # ECOSYSTEM OUTPUT METHODS
    # =========================================================================
    
    def format_for_dsp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for DSP - with ethical safeguards.
        
        DSPs get:
        - Contextual emotional signals (not individual targeting)
        - Safeguard rules for what NOT to show
        - Supportive messaging guidance
        """
        # Get emotional state if scoped to one
        emotional_state = None
        if intelligence.scope_type == "emotional_state":
            emotional_state = intelligence.scope_value
        
        # Get applicable safeguards
        safeguard = self.safeguards.get(emotional_state)
        
        output = {
            "segment_type": "emotional_contextual",
            "scope": {
                "type": intelligence.scope_type,
                "value": intelligence.scope_value,
            },
            
            # Contextual signals (aggregated, not individual)
            "emotional_context": {
                "dominant_emotions": self._get_dominant_emotions(
                    intelligence.construct_distributions
                ),
                "mechanism_receptivity": {
                    mech.value if hasattr(mech, 'value') else str(mech): score
                    for mech, score in intelligence.mechanism_effectiveness.items()
                },
            },
            
            # ETHICAL SAFEGUARDS
            "safeguards": {
                "enabled": True,
                "avoid_mechanisms": safeguard.avoid_mechanisms if safeguard else [],
                "avoid_topics": safeguard.avoid_topics if safeguard else [],
                "recommended_approach": safeguard.recommended_approach if safeguard else "standard",
            },
            
            # Supportive guidance
            "supportive_guidance": {
                "recommended_mechanisms": safeguard.supportive_mechanisms if safeguard else [],
                "tone": self._recommend_supportive_tone(emotional_state),
                "messaging_principles": self._get_messaging_principles(emotional_state),
            },
            
            "sample_size": intelligence.sample_size,
            "ethical_note": "This data is for supportive messaging only. Never exploit vulnerable states.",
        }
        
        return output
    
    def format_for_ssp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for SSP (iHeart) - Music/audio context.
        
        SSPs get:
        - Music preference → emotional state correlations
        - Audio content recommendations
        - Sensitivity flags for content adjacency
        """
        return {
            "inventory_type": "audio_emotional",
            "scope": {
                "type": intelligence.scope_type,
                "value": intelligence.scope_value,
            },
            
            # Music-emotion mappings (for iHeart)
            "audio_intelligence": {
                "genre_emotional_profiles": self._get_genre_profiles(),
                "mood_playlist_mapping": self._get_mood_playlists(),
            },
            
            # Content sensitivity
            "content_sensitivity": {
                "sensitive_states_present": self._has_sensitive_states(intelligence),
                "content_adjacency_rules": self._get_adjacency_rules(intelligence),
            },
            
            # Yield signals
            "audience_value": {
                "emotional_composition": self._get_emotional_composition(intelligence),
                "engagement_patterns": self._get_engagement_patterns(intelligence),
            },
            
            "sample_size": intelligence.sample_size,
        }
    
    def format_for_agency(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for Agency (WPP) - Strategic emotional intelligence.
        
        Agencies get:
        - Emotional landscape analysis
        - Campaign sensitivity guidance
        - Cross-platform emotional insights
        """
        emotional_state = None
        if intelligence.scope_type == "emotional_state":
            emotional_state = intelligence.scope_value
        
        return {
            "strategic_context": {
                "emotional_landscape": {
                    "state_distribution": self._get_state_distribution(intelligence),
                    "temporal_patterns": self._get_temporal_insights(intelligence),
                    "engagement_by_state": self._get_engagement_by_state(intelligence),
                },
            },
            
            # Creative guidance with sensitivity
            "creative_brief": {
                "emotional_context": emotional_state,
                "recommended_tone": self._recommend_supportive_tone(emotional_state),
                "messaging_do": self._get_messaging_dos(emotional_state),
                "messaging_dont": self._get_messaging_donts(emotional_state),
                "visual_guidance": self._get_visual_guidance(emotional_state),
            },
            
            # Campaign planning
            "campaign_planning": {
                "optimal_timing": self._get_optimal_timing(intelligence),
                "platform_recommendations": self._get_platform_recs(intelligence),
                "sensitivity_requirements": self._get_sensitivity_requirements(emotional_state),
            },
            
            # Cross-platform
            "cross_platform": {
                "audio_recommendations": self._get_audio_recs_for_state(emotional_state),
                "social_recommendations": self._get_social_recs_for_state(emotional_state),
            },
            
            "ethical_guidelines": self._get_ethical_guidelines(emotional_state),
            "sample_size": intelligence.sample_size,
        }
    
    # =========================================================================
    # TWITTER-SPECIFIC EXTRACTION METHODS
    # =========================================================================
    
    def build_language_patterns(
        self,
        state: str = None,
        min_frequency: float = 0.01,
    ) -> List[LanguagePattern]:
        """
        Build language patterns from tweet data.
        
        This extracts the linguistic markers that differentiate
        emotional states - enabling inference without tracking.
        """
        # Note: tweet_profiles doesn't have text content directly
        # We use music profiles which have lyrics
        
        state_word_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        state_totals: Dict[str, int] = defaultdict(int)
        
        for music in self.iter_music_profiles():
            disorder = music.get('disorder', MentalHealthState.CONTROL)
            
            if state and disorder != state:
                continue
            
            # Get lyric text
            lyric = music.get('lyric', '')
            if not lyric:
                continue
            
            # Tokenize and count
            words = re.findall(r'\b[a-z]+\b', lyric.lower())
            for word in words:
                if len(word) > 3:  # Skip short words
                    state_word_counts[disorder][word] += 1
                    state_totals[disorder] += 1
        
        # Find words that differentiate states
        patterns = []
        all_states = list(state_word_counts.keys())
        
        for word in self._get_common_words(state_word_counts):
            frequency_by_state = {}
            
            for s in all_states:
                if state_totals[s] > 0:
                    frequency_by_state[s] = (
                        state_word_counts[s][word] / state_totals[s]
                    )
            
            # Check if word differentiates states
            if max(frequency_by_state.values()) - min(frequency_by_state.values()) > 0.001:
                # This word is used differently across states
                associated = [
                    s for s, freq in frequency_by_state.items()
                    if freq > min_frequency
                ]
                
                if associated:
                    patterns.append(LanguagePattern(
                        pattern_type="word",
                        pattern=word,
                        associated_states=associated,
                        frequency_by_state=frequency_by_state,
                        mechanism_implications=self._infer_mechanism_implications(word),
                    ))
        
        return patterns
    
    def build_music_emotion_map(self) -> Dict[str, EmotionalProfile]:
        """
        Build mapping: music genre → emotional profile.
        
        This enables:
        - iHeart audio targeting based on psychological state
        - Content-based emotional inference
        """
        genre_profiles: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: {
                'anger': [], 'disgust': [], 'fear': [], 'joy': [],
                'neutral': [], 'sadness': [], 'surprise': [],
                'disorder_counts': defaultdict(int),
            }
        )
        
        for music in self.iter_music_profiles():
            genres_str = music.get('genres', '')
            if not genres_str:
                continue
            
            genres = [g.strip() for g in genres_str.split('|') if g.strip()]
            disorder = music.get('disorder', MentalHealthState.CONTROL)
            
            # Get emotion scores
            emotions = {
                'anger': self._safe_float(music.get('emotion_anger_score')),
                'disgust': self._safe_float(music.get('emotion_disgust_score')),
                'fear': self._safe_float(music.get('emotion_fear_score')),
                'joy': self._safe_float(music.get('emotion_joy_score')),
                'neutral': self._safe_float(music.get('emotion_neutral_score')),
                'sadness': self._safe_float(music.get('emotion_sadness_score')),
                'surprise': self._safe_float(music.get('emotion_surprise_score')),
            }
            
            # Add to each genre
            for genre in genres:
                for emotion, score in emotions.items():
                    if score is not None:
                        genre_profiles[genre][emotion].append(score)
                genre_profiles[genre]['disorder_counts'][disorder] += 1
        
        # Aggregate into profiles
        result = {}
        for genre, data in genre_profiles.items():
            profile = EmotionalProfile()
            
            for emotion in ['anger', 'disgust', 'fear', 'joy', 'neutral', 'sadness', 'surprise']:
                scores = data.get(emotion, [])
                if scores:
                    setattr(profile, emotion, sum(scores) / len(scores))
            
            # Dominant disorder for this genre
            disorder_counts = data.get('disorder_counts', {})
            if disorder_counts:
                profile.disorder_indicator = max(
                    disorder_counts,
                    key=disorder_counts.get
                )
            
            result[genre] = profile
        
        self._music_emotion_map = result
        return result
    
    def build_temporal_patterns(self) -> Dict[str, Dict[int, float]]:
        """
        Build temporal patterns by emotional state.
        
        Maps: emotional_state → hour_of_day → relative_activity
        """
        state_hour_counts: Dict[str, Dict[int, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        state_totals: Dict[str, int] = defaultdict(int)
        
        for tweet in self.iter_reviews():
            disorder = tweet.get('disorder', MentalHealthState.CONTROL)
            created_at = tweet.get('created_at')
            
            if not created_at:
                continue
            
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                hour = dt.hour
                
                state_hour_counts[disorder][hour] += 1
                state_totals[disorder] += 1
            except:
                continue
        
        # Normalize to relative activity
        patterns = {}
        for state, hour_counts in state_hour_counts.items():
            total = state_totals[state]
            if total > 0:
                patterns[state] = {
                    hour: count / total * 24  # Normalize so average = 1.0
                    for hour, count in hour_counts.items()
                }
        
        self._state_temporal_patterns = patterns
        return patterns
    
    def infer_emotional_state(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Infer emotional state from text.
        
        This is the COOKIE-LESS TARGETING method:
        - No tracking required
        - Just analyze the content/context
        - Returns probability distribution over states
        """
        text_lower = text.lower()
        
        # Start with uniform prior
        state_scores = {
            MentalHealthState.CONTROL: 0.5,
            MentalHealthState.DEPRESSION: 0.1,
            MentalHealthState.ANXIETY: 0.1,
            MentalHealthState.PTSD: 0.05,
            MentalHealthState.BIPOLAR: 0.05,
            MentalHealthState.BORDERLINE: 0.05,
            MentalHealthState.PANIC: 0.05,
        }
        
        # Check depression markers
        depression_count = sum(1 for m in self.depression_markers if m in text_lower)
        if depression_count > 0:
            state_scores[MentalHealthState.DEPRESSION] += depression_count * 0.1
            state_scores[MentalHealthState.CONTROL] -= depression_count * 0.05
        
        # Check anxiety markers
        anxiety_count = sum(1 for m in self.anxiety_markers if m in text_lower)
        if anxiety_count > 0:
            state_scores[MentalHealthState.ANXIETY] += anxiety_count * 0.1
            state_scores[MentalHealthState.CONTROL] -= anxiety_count * 0.05
        
        # Check positive markers
        positive_count = sum(1 for m in self.positive_markers if m in text_lower)
        if positive_count > 0:
            state_scores[MentalHealthState.CONTROL] += positive_count * 0.1
        
        # Temporal context adjustment
        if context:
            hour = context.get('hour_of_day')
            if hour is not None and self._state_temporal_patterns:
                for state, hourly in self._state_temporal_patterns.items():
                    if hour in hourly:
                        # Adjust based on when this state typically posts
                        state_scores[state] *= hourly[hour]
        
        # Normalize to probabilities
        total = sum(state_scores.values())
        if total > 0:
            state_scores = {k: v / total for k, v in state_scores.items()}
        
        return state_scores
    
    def get_safeguard_rules(
        self,
        emotional_state: str,
    ) -> Optional[EmotionalStateSafeguard]:
        """Get safeguard rules for an emotional state."""
        return self.safeguards.get(emotional_state)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except:
            return None
    
    def _get_common_words(
        self,
        state_word_counts: Dict[str, Dict[str, int]],
        min_total: int = 100,
    ) -> Set[str]:
        """Get words that appear frequently enough to analyze."""
        word_totals = defaultdict(int)
        
        for state, counts in state_word_counts.items():
            for word, count in counts.items():
                word_totals[word] += count
        
        return {w for w, c in word_totals.items() if c >= min_total}
    
    def _infer_mechanism_implications(self, word: str) -> Dict[str, float]:
        """Infer which mechanisms a word relates to."""
        implications = {}
        word_lower = word.lower()
        
        # Social proof words
        if word_lower in ["everyone", "popular", "trending", "reviews"]:
            implications[PersuasionMechanism.SOCIAL_PROOF.value] = 0.8
        
        # Fear words
        if word_lower in ["afraid", "scared", "danger", "risk", "worry"]:
            implications[PersuasionMechanism.FEAR_APPEAL.value] = 0.8
        
        # Trust words
        if word_lower in ["trust", "reliable", "safe", "secure"]:
            implications[PersuasionMechanism.TRUST.value] = 0.8
        
        # Unity words
        if word_lower in ["together", "community", "belong", "family"]:
            implications[PersuasionMechanism.UNITY.value] = 0.8
        
        return implications
    
    def _get_dominant_emotions(
        self,
        construct_distributions: Dict,
    ) -> Dict[str, float]:
        """Get dominant emotions from construct distributions."""
        # Map constructs to emotions
        emotion_related = {}
        for const, dist in construct_distributions.items():
            const_str = const.value if hasattr(const, 'value') else str(const)
            if 'mean' in dist:
                emotion_related[const_str] = dist['mean']
        return emotion_related
    
    def _recommend_supportive_tone(self, emotional_state: str) -> str:
        """Recommend tone for supportive messaging."""
        tone_map = {
            MentalHealthState.DEPRESSION: "warm_gentle_hopeful",
            MentalHealthState.ANXIETY: "calm_reassuring_steady",
            MentalHealthState.PTSD: "safe_predictable_transparent",
            MentalHealthState.BIPOLAR: "balanced_grounding_consistent",
            MentalHealthState.PANIC: "soothing_slow_controlled",
            MentalHealthState.BORDERLINE: "validating_stable_clear",
            MentalHealthState.CONTROL: "friendly_engaging_positive",
        }
        return tone_map.get(emotional_state, "friendly_supportive")
    
    def _get_messaging_principles(self, emotional_state: str) -> List[str]:
        """Get messaging principles for an emotional state."""
        safeguard = self.safeguards.get(emotional_state)
        
        if safeguard:
            return [
                f"Avoid: {', '.join(safeguard.avoid_mechanisms[:3])}",
                f"Use: {', '.join(safeguard.supportive_mechanisms[:3])}",
                f"Approach: {safeguard.recommended_approach}",
            ]
        
        return ["Be supportive and authentic"]
    
    def _has_sensitive_states(self, intelligence: AggregatedIntelligence) -> bool:
        """Check if intelligence includes sensitive emotional states."""
        return intelligence.scope_type == "emotional_state" and \
               intelligence.scope_value in self.safeguards
    
    def _get_adjacency_rules(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """Get content adjacency rules."""
        if intelligence.scope_type == "emotional_state":
            safeguard = self.safeguards.get(intelligence.scope_value)
            if safeguard:
                return {
                    "avoid_adjacent_topics": safeguard.avoid_topics,
                    "preferred_adjacent_content": ["uplifting", "supportive", "informational"],
                }
        return {}
    
    def _get_emotional_composition(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, float]:
        """Get emotional composition of audience."""
        return {
            arch.value if hasattr(arch, 'value') else str(arch): score
            for arch, score in intelligence.archetype_prevalence.items()
        }
    
    def _get_engagement_patterns(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """Get engagement patterns."""
        return {
            "mechanism_effectiveness": {
                mech.value if hasattr(mech, 'value') else str(mech): score
                for mech, score in intelligence.mechanism_effectiveness.items()
            }
        }
    
    def _get_genre_profiles(self) -> Dict[str, Dict[str, float]]:
        """Get genre → emotional profile mappings."""
        if not self._music_emotion_map:
            self.build_music_emotion_map()
        
        return {
            genre: {
                'anger': profile.anger,
                'joy': profile.joy,
                'sadness': profile.sadness,
                'fear': profile.fear,
            }
            for genre, profile in self._music_emotion_map.items()
        }
    
    def _get_mood_playlists(self) -> Dict[str, List[str]]:
        """Get mood → playlist genre recommendations."""
        return {
            "energizing": ["pop", "dance", "hip-hop"],
            "calming": ["ambient", "classical", "acoustic"],
            "uplifting": ["indie-pop", "folk", "soul"],
            "focus": ["lo-fi", "instrumental", "classical"],
        }
    
    def _get_state_distribution(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, float]:
        """Get distribution of emotional states."""
        # This would be populated from actual data
        return {
            "control": 0.55,
            "depression": 0.20,
            "anxiety": 0.10,
            "other": 0.15,
        }
    
    def _get_temporal_insights(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """Get temporal insights."""
        if not self._state_temporal_patterns:
            self.build_temporal_patterns()
        
        return {
            "peak_hours_by_state": {
                state: max(hours.items(), key=lambda x: x[1])[0] if hours else None
                for state, hours in self._state_temporal_patterns.items()
            }
        }
    
    def _get_engagement_by_state(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, float]:
        """Get engagement levels by state."""
        # Would be populated from actual data
        return {"average_engagement": 0.5}
    
    def _get_messaging_dos(self, emotional_state: str) -> List[str]:
        """Get messaging dos for a state."""
        safeguard = self.safeguards.get(emotional_state)
        if safeguard:
            return [
                f"Use {mech} mechanism" for mech in safeguard.supportive_mechanisms
            ]
        return ["Be authentic and supportive"]
    
    def _get_messaging_donts(self, emotional_state: str) -> List[str]:
        """Get messaging don'ts for a state."""
        safeguard = self.safeguards.get(emotional_state)
        if safeguard:
            return [
                f"Avoid {mech} mechanism" for mech in safeguard.avoid_mechanisms
            ] + [
                f"Avoid topic: {topic}" for topic in safeguard.avoid_topics
            ]
        return []
    
    def _get_visual_guidance(self, emotional_state: str) -> Dict[str, Any]:
        """Get visual creative guidance."""
        guidance_map = {
            MentalHealthState.DEPRESSION: {
                "colors": "warm_soft_hopeful",
                "imagery": "nature_light_connection",
                "avoid": "dark_isolated_overwhelming",
            },
            MentalHealthState.ANXIETY: {
                "colors": "calm_blue_green",
                "imagery": "organized_peaceful_clear",
                "avoid": "chaotic_busy_surprising",
            },
        }
        return guidance_map.get(emotional_state, {
            "colors": "brand_appropriate",
            "imagery": "positive_authentic",
        })
    
    def _get_optimal_timing(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """Get optimal timing recommendations."""
        return {
            "general_best_hours": [10, 11, 14, 15, 19, 20],
            "avoid_for_sensitive": [22, 23, 0, 1, 2, 3],
        }
    
    def _get_platform_recs(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, str]:
        """Get platform recommendations."""
        return {
            "twitter": "contextual_support",
            "audio": "calming_playlists",
            "display": "non_intrusive",
        }
    
    def _get_sensitivity_requirements(
        self, emotional_state: str
    ) -> Dict[str, Any]:
        """Get sensitivity requirements."""
        if emotional_state in self.safeguards:
            return {
                "level": "high",
                "review_required": True,
                "safeguards_enabled": True,
            }
        return {
            "level": "standard",
            "review_required": False,
        }
    
    def _get_audio_recs_for_state(
        self, emotional_state: str
    ) -> Dict[str, Any]:
        """Get audio recommendations for emotional state."""
        recs = {
            MentalHealthState.DEPRESSION: {
                "genres": ["uplifting", "acoustic", "soul"],
                "tempo": "moderate",
                "tone": "hopeful",
            },
            MentalHealthState.ANXIETY: {
                "genres": ["ambient", "classical", "lo-fi"],
                "tempo": "slow",
                "tone": "calming",
            },
        }
        return recs.get(emotional_state, {
            "genres": ["varied"],
            "tempo": "dynamic",
        })
    
    def _get_social_recs_for_state(
        self, emotional_state: str
    ) -> Dict[str, Any]:
        """Get social media recommendations for emotional state."""
        return {
            "content_type": "supportive_community",
            "engagement_style": "gentle_non_pushy",
        }
    
    def _get_ethical_guidelines(
        self, emotional_state: str
    ) -> Dict[str, Any]:
        """Get ethical guidelines for targeting."""
        return {
            "principle": "support_not_exploit",
            "rules": [
                "Never use vulnerability for manipulation",
                "Prioritize user wellbeing over engagement",
                "Provide value and support",
                "Enable easy opt-out",
                "Review all sensitive targeting",
            ],
            "accountability": "ADAM ethical review required for sensitive states",
        }
