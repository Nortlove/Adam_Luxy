# =============================================================================
# ADAM Behavioral Analytics: Personality Inferencer
# Location: adam/behavioral_analytics/classifiers/personality_inferencer.py
# =============================================================================

"""
PERSONALITY INFERENCER

Infers Big Five personality traits from media preferences, behavioral signals,
and linguistic features (LIWC-22).

Research Foundation:
- Music preferences predict personality (Rentfrow & Gosling, 2003, 2006)
  - Sophisticated/Intense music → Openness (r=0.30-0.44)
  - Contemporary music → Extraversion (r=0.25)
- Podcast preferences (Scrivner et al., 2021)
  - True crime → Morbid curiosity (sr=0.51)
- Film/TV preferences
  - Horror → Sensation seeking (inverse Neuroticism)
  - Documentary → Openness
- Behavioral signals
  - Typing rhythm → Emotional stability (Epp et al., 2011)
  - Touch pressure → Extraversion (Ghosh et al., 2017)
- Linguistic features (LIWC-22) → Koutsoumpis et al. (2022) meta-analysis
  - k=31 studies, N=85,724
  - Positive emotion → Extraversion (rho=0.11-0.14)
  - Negative emotion → Neuroticism (rho=0.08-0.14)
  - Social words → Extraversion (rho=0.10-0.14)
  - Insight words → Openness
  - CRITICAL: Requires 3000+ words (10+ reviews) for reliable inference

The Big Five (OCEAN):
1. Openness to Experience - Curiosity, creativity, novelty-seeking
2. Conscientiousness - Organization, dependability, self-discipline
3. Extraversion - Sociability, assertiveness, positive emotions
4. Agreeableness - Cooperation, trust, empathy
5. Neuroticism - Emotional instability, anxiety, moodiness
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.media_preferences import (
    MediaConsumptionProfile,
    MusicPreference,
    PodcastPreference,
    BookPreference,
    FilmTVPreference,
    MUSICDimensions,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PERSONALITY MODELS
# =============================================================================

class BigFiveProfile(BaseModel):
    """
    Big Five personality profile.
    
    Each trait is scored 0-1 where:
    - 0.5 = average/neutral
    - < 0.5 = low on trait
    - > 0.5 = high on trait
    """
    # Core traits
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Confidence for each trait
    openness_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Derived/related traits
    morbid_curiosity: float = Field(default=0.0, ge=0.0, le=1.0)
    need_for_cognition: float = Field(default=0.5, ge=0.0, le=1.0)
    sensation_seeking: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Evidence tracking
    signals_used: List[str] = Field(default_factory=list)
    domains_used: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    def get_dominant_traits(self, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """Get traits significantly above average."""
        traits = [
            ("openness", self.openness),
            ("conscientiousness", self.conscientiousness),
            ("extraversion", self.extraversion),
            ("agreeableness", self.agreeableness),
            ("neuroticism", self.neuroticism),
        ]
        
        dominant = [(name, value) for name, value in traits if value > threshold]
        dominant.sort(key=lambda x: x[1], reverse=True)
        return dominant
    
    def get_low_traits(self, threshold: float = 0.4) -> List[Tuple[str, float]]:
        """Get traits significantly below average."""
        traits = [
            ("openness", self.openness),
            ("conscientiousness", self.conscientiousness),
            ("extraversion", self.extraversion),
            ("agreeableness", self.agreeableness),
            ("neuroticism", self.neuroticism),
        ]
        
        low = [(name, value) for name, value in traits if value < threshold]
        low.sort(key=lambda x: x[1])
        return low
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "traits": {
                "openness": self.openness,
                "conscientiousness": self.conscientiousness,
                "extraversion": self.extraversion,
                "agreeableness": self.agreeableness,
                "neuroticism": self.neuroticism,
            },
            "confidences": {
                "openness": self.openness_confidence,
                "conscientiousness": self.conscientiousness_confidence,
                "extraversion": self.extraversion_confidence,
                "agreeableness": self.agreeableness_confidence,
                "neuroticism": self.neuroticism_confidence,
            },
            "derived_traits": {
                "morbid_curiosity": self.morbid_curiosity,
                "need_for_cognition": self.need_for_cognition,
                "sensation_seeking": self.sensation_seeking,
            },
            "dominant_traits": self.get_dominant_traits(),
            "low_traits": self.get_low_traits(),
            "overall_confidence": self.overall_confidence,
            "domains_used": self.domains_used,
        }


# =============================================================================
# PERSONALITY INFERENCER
# =============================================================================

class PersonalityInferencer:
    """
    Infers Big Five personality traits from media preferences and behavior.
    
    Uses research-validated mappings with effect sizes to estimate
    personality traits from observable signals.
    
    Primary signal sources:
    1. Music preferences (MUSIC model → Big Five)
    2. Podcast preferences (genre → traits)
    3. Book preferences (genre → cognitive style)
    4. Film/TV preferences (genre → traits)
    5. Behavioral signals (typing, touch → emotional indicators)
    """
    
    # Research-validated mappings: MUSIC dimensions → Big Five
    # Based on Rentfrow et al. (2011, 2012)
    MUSIC_TO_BIG_FIVE = {
        # Sophisticated music (Classical, Jazz, World)
        "sophisticated": {
            "openness": 0.44,  # Strong positive correlation
            "conscientiousness": 0.0,
            "extraversion": -0.10,
            "agreeableness": 0.05,
            "neuroticism": -0.05,
        },
        # Intense music (Metal, Punk, Rock)
        "intense": {
            "openness": 0.20,  # Moderate positive
            "conscientiousness": -0.15,
            "extraversion": 0.10,
            "agreeableness": -0.25,  # Negative correlation
            "neuroticism": 0.05,
        },
        # Contemporary music (EDM, Hip-Hop, Pop)
        "contemporary": {
            "openness": 0.05,
            "conscientiousness": -0.05,
            "extraversion": 0.30,  # Strong positive
            "agreeableness": 0.15,
            "neuroticism": 0.05,
        },
        # Mellow music (Jazz, R&B, Soul)
        "mellow": {
            "openness": 0.15,
            "conscientiousness": 0.10,
            "extraversion": -0.15,
            "agreeableness": 0.25,  # Positive correlation
            "neuroticism": 0.10,
        },
        # Unpretentious music (Country, Folk)
        "unpretentious": {
            "openness": -0.10,
            "conscientiousness": 0.20,  # Positive correlation
            "extraversion": 0.05,
            "agreeableness": 0.30,  # Strong positive
            "neuroticism": -0.05,
        },
    }
    
    # Podcast genre → trait mappings
    PODCAST_TO_TRAITS = {
        "true_crime": {
            "morbid_curiosity": 0.51,  # Strong correlation
            "openness": 0.10,
            "neuroticism": 0.05,
        },
        "news_politics": {
            "openness": 0.20,
            "conscientiousness": 0.15,
            "need_for_cognition": 0.30,
        },
        "educational": {
            "openness": 0.35,
            "conscientiousness": 0.20,
            "need_for_cognition": 0.40,
        },
        "comedy": {
            "extraversion": 0.25,
            "openness": 0.10,
            "agreeableness": 0.10,
        },
        "science": {
            "openness": 0.40,
            "conscientiousness": 0.15,
            "need_for_cognition": 0.45,
        },
        "self_help": {
            "conscientiousness": 0.25,
            "neuroticism": 0.15,  # Seeking improvement
            "openness": 0.10,
        },
    }
    
    # Film/TV genre → trait mappings
    FILM_TO_TRAITS = {
        "horror": {
            "sensation_seeking": 0.40,
            "neuroticism": -0.20,  # Low neuroticism seeks thrills
            "openness": 0.15,
        },
        "documentary": {
            "openness": 0.35,
            "conscientiousness": 0.20,
            "need_for_cognition": 0.40,
        },
        "reality_tv": {
            "extraversion": 0.15,
            "agreeableness": -0.10,  # Social comparison
            "openness": -0.10,
        },
        "science_fiction": {
            "openness": 0.40,
            "conscientiousness": 0.05,
        },
        "romance": {
            "agreeableness": 0.25,
            "extraversion": 0.10,
            "neuroticism": 0.10,
        },
        "action": {
            "sensation_seeking": 0.30,
            "extraversion": 0.15,
        },
    }
    
    def __init__(self):
        self._inference_count = 0
    
    def infer_from_media_profile(
        self,
        media_profile: MediaConsumptionProfile,
    ) -> BigFiveProfile:
        """
        Infer Big Five personality from complete media profile.
        
        Args:
            media_profile: MediaConsumptionProfile with preferences
            
        Returns:
            BigFiveProfile with trait estimates and confidence
        """
        profile = BigFiveProfile()
        
        # Accumulators for weighted averaging
        trait_signals: Dict[str, List[Tuple[float, float]]] = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": [],
            "morbid_curiosity": [],
            "need_for_cognition": [],
            "sensation_seeking": [],
        }
        
        # Process music preferences
        if media_profile.music:
            self._process_music(media_profile.music, trait_signals)
            profile.domains_used.append("music")
        
        # Process podcast preferences
        if media_profile.podcasts:
            self._process_podcasts(media_profile.podcasts, trait_signals)
            profile.domains_used.append("podcasts")
        
        # Process film/TV preferences
        if media_profile.film_tv:
            self._process_film_tv(media_profile.film_tv, trait_signals)
            profile.domains_used.append("film_tv")
        
        # Process book preferences
        if media_profile.books:
            self._process_books(media_profile.books, trait_signals)
            profile.domains_used.append("books")
        
        # Aggregate signals for each trait
        for trait, signals in trait_signals.items():
            if not signals:
                continue
            
            # Weighted average by effect size (confidence)
            total_weight = sum(abs(effect) for _, effect in signals)
            if total_weight > 0:
                weighted_sum = sum(
                    (0.5 + value * effect) * abs(effect)
                    for value, effect in signals
                )
                trait_value = weighted_sum / total_weight
                trait_value = max(0.0, min(1.0, trait_value))
                
                # Confidence based on number of signals and effect sizes
                confidence = min(0.9, 0.3 + len(signals) * 0.1 + total_weight * 0.2)
            else:
                trait_value = 0.5
                confidence = 0.3
            
            # Set trait values
            if trait == "openness":
                profile.openness = trait_value
                profile.openness_confidence = confidence
            elif trait == "conscientiousness":
                profile.conscientiousness = trait_value
                profile.conscientiousness_confidence = confidence
            elif trait == "extraversion":
                profile.extraversion = trait_value
                profile.extraversion_confidence = confidence
            elif trait == "agreeableness":
                profile.agreeableness = trait_value
                profile.agreeableness_confidence = confidence
            elif trait == "neuroticism":
                profile.neuroticism = trait_value
                profile.neuroticism_confidence = confidence
            elif trait == "morbid_curiosity":
                profile.morbid_curiosity = trait_value
            elif trait == "need_for_cognition":
                profile.need_for_cognition = trait_value
            elif trait == "sensation_seeking":
                profile.sensation_seeking = trait_value
        
        # Calculate overall confidence
        if profile.domains_used:
            confidences = [
                profile.openness_confidence,
                profile.conscientiousness_confidence,
                profile.extraversion_confidence,
                profile.agreeableness_confidence,
                profile.neuroticism_confidence,
            ]
            profile.overall_confidence = sum(confidences) / len(confidences)
            
            # Boost for multiple domains
            profile.overall_confidence = min(
                0.95, profile.overall_confidence + len(profile.domains_used) * 0.05
            )
        
        self._inference_count += 1
        
        logger.info(
            f"Inferred personality from {len(profile.domains_used)} domains: "
            f"O={profile.openness:.2f}, C={profile.conscientiousness:.2f}, "
            f"E={profile.extraversion:.2f}, A={profile.agreeableness:.2f}, "
            f"N={profile.neuroticism:.2f}"
        )
        
        return profile
    
    def infer_from_behavioral_features(
        self,
        features: Dict[str, float],
        existing_profile: Optional[BigFiveProfile] = None,
    ) -> BigFiveProfile:
        """
        Infer personality from behavioral features.
        
        Args:
            features: Behavioral features dict from session
            existing_profile: Optional existing profile to update
            
        Returns:
            BigFiveProfile with trait estimates
        """
        profile = existing_profile or BigFiveProfile()
        
        trait_signals: Dict[str, List[Tuple[float, float]]] = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": [],
        }
        
        # Keystroke rhythm → Emotional stability (inverse Neuroticism)
        # Research: Consistent typing rhythm correlates with stability
        if "keystroke_seq_rhythm_regularity" in features:
            regularity = features["keystroke_seq_rhythm_regularity"]
            # High regularity → low neuroticism
            trait_signals["neuroticism"].append((1 - regularity, 0.25))
            profile.signals_used.append("keystroke_rhythm")
        
        # Typing speed → Extraversion
        # Research: Faster typing correlates with extraversion
        if "keystroke_seq_speed_mean" in features:
            speed = min(1.0, features["keystroke_seq_speed_mean"] / 400)  # Normalize
            trait_signals["extraversion"].append((speed, 0.20))
            profile.signals_used.append("typing_speed")
        
        # Touch pressure → Extraversion
        # Research: Higher touch pressure correlates with extraversion
        if "pressure_mean" in features:
            pressure = features["pressure_mean"]
            trait_signals["extraversion"].append((pressure, 0.25))
            profile.signals_used.append("touch_pressure")
        
        # Scroll depth → Openness (deep reading = curiosity)
        if "max_depth" in features:
            depth = features["max_depth"]
            trait_signals["openness"].append((depth, 0.15))
            profile.signals_used.append("scroll_depth")
        
        # Error rate → Conscientiousness (inverse)
        if "keystroke_seq_error_rate" in features:
            error_rate = features["keystroke_seq_error_rate"]
            # High errors → low conscientiousness
            trait_signals["conscientiousness"].append((1 - error_rate * 5, 0.20))
            profile.signals_used.append("error_rate")
        
        # Cursor conflict → Neuroticism
        # Research: Indecisiveness correlates with neuroticism
        if "trajectory_conflict_mean" in features:
            conflict = features["trajectory_conflict_mean"]
            trait_signals["neuroticism"].append((conflict, 0.20))
            profile.signals_used.append("cursor_conflict")
        
        # Update profile with behavioral signals
        for trait, signals in trait_signals.items():
            if not signals:
                continue
            
            total_weight = sum(abs(effect) for _, effect in signals)
            if total_weight > 0:
                weighted_sum = sum(
                    (0.5 + value * effect) * abs(effect)
                    for value, effect in signals
                )
                new_value = weighted_sum / total_weight
                new_value = max(0.0, min(1.0, new_value))
                
                # Blend with existing value
                current = getattr(profile, trait)
                blended = current * 0.7 + new_value * 0.3  # 70% media, 30% behavior
                setattr(profile, trait, blended)
        
        return profile
    
    def _process_music(
        self,
        music: MusicPreference,
        trait_signals: Dict[str, List[Tuple[float, float]]],
    ) -> None:
        """Process music preferences into trait signals."""
        dims = music.music_dimensions
        
        for dim_name in ["sophisticated", "intense", "contemporary", "mellow", "unpretentious"]:
            dim_value = getattr(dims, dim_name)
            if dim_value <= 0:
                continue
            
            mappings = self.MUSIC_TO_BIG_FIVE.get(dim_name, {})
            for trait, effect in mappings.items():
                if effect != 0:
                    trait_signals[trait].append((dim_value, effect))
    
    def _process_podcasts(
        self,
        podcasts: PodcastPreference,
        trait_signals: Dict[str, List[Tuple[float, float]]],
    ) -> None:
        """Process podcast preferences into trait signals."""
        for genre in podcasts.genres:
            genre_key = genre.value if hasattr(genre, 'value') else str(genre)
            mappings = self.PODCAST_TO_TRAITS.get(genre_key, {})
            
            # Use engagement score if available
            if genre_key == "true_crime":
                engagement = podcasts.true_crime_engagement
            elif genre_key == "news_politics":
                engagement = podcasts.news_politics_engagement
            elif genre_key in ["educational", "science"]:
                engagement = podcasts.educational_engagement
            else:
                engagement = 0.7  # Default moderate engagement
            
            for trait, effect in mappings.items():
                if effect != 0:
                    trait_signals[trait].append((engagement, effect))
    
    def _process_film_tv(
        self,
        film_tv: FilmTVPreference,
        trait_signals: Dict[str, List[Tuple[float, float]]],
    ) -> None:
        """Process film/TV preferences into trait signals."""
        for genre in film_tv.genres:
            genre_key = genre.value if hasattr(genre, 'value') else str(genre)
            mappings = self.FILM_TO_TRAITS.get(genre_key, {})
            
            # Use specific preference scores if available
            if genre_key == "horror":
                engagement = film_tv.horror_preference
            elif genre_key == "documentary":
                engagement = film_tv.documentary_preference
            elif genre_key == "reality_tv":
                engagement = film_tv.reality_tv_preference
            else:
                engagement = 0.7
            
            for trait, effect in mappings.items():
                if effect != 0:
                    trait_signals[trait].append((engagement, effect))
    
    def _process_books(
        self,
        books: BookPreference,
        trait_signals: Dict[str, List[Tuple[float, float]]],
    ) -> None:
        """Process book preferences into trait signals."""
        # Fiction preference → Openness and Agreeableness
        trait_signals["openness"].append((books.fiction_preference, 0.15))
        trait_signals["agreeableness"].append((books.fiction_preference, 0.10))
        
        # Reading volume → Openness and Conscientiousness
        volume = min(1.0, books.books_per_year / 20)  # 20+ books = max
        trait_signals["openness"].append((volume, 0.25))
        trait_signals["conscientiousness"].append((volume, 0.15))
        
        # Genre diversity → Openness
        trait_signals["openness"].append((books.genre_diversity, 0.20))
    
    # =========================================================================
    # LIWC-BASED INFERENCE (from advertising_psychology_research)
    # =========================================================================
    
    # LIWC → Big Five correlations from Koutsoumpis et al. (2022) meta-analysis
    # k=31 studies, N=85,724
    LIWC_TO_BIG_FIVE = {
        # Extraversion correlates
        "positive_emotion": {"extraversion": 0.14, "agreeableness": 0.08},
        "social_words": {"extraversion": 0.14},
        "first_person_plural": {"extraversion": 0.10},  # We/us/our
        "exclamation_density": {"extraversion": 0.12},
        
        # Neuroticism correlates
        "first_person_singular": {"neuroticism": 0.10},  # I/me/my
        "negative_emotion": {"neuroticism": 0.14},
        "anxiety_words": {"neuroticism": 0.12},
        "sadness_words": {"neuroticism": 0.10},
        
        # Openness correlates
        "insight_words": {"openness": 0.10},
        "tentative_words": {"openness": 0.08},
        "six_letter_words": {"openness": 0.15},  # Word length
        "articles": {"openness": 0.10},  # Formal style
        
        # Conscientiousness correlates
        "achievement_words": {"conscientiousness": 0.08},
        "negations": {"conscientiousness": -0.06},  # Inverse
        
        # Agreeableness correlates (lowest predictability)
        "swear_words": {"agreeableness": -0.10},  # Inverse
    }
    
    # Minimum word count for reliable LIWC inference
    MIN_WORDS_FOR_LIWC = 3000  # ~10 reviews
    
    def infer_from_text(
        self,
        text: str,
        existing_profile: Optional[BigFiveProfile] = None,
        min_words: int = 3000,
    ) -> BigFiveProfile:
        """
        Infer Big Five personality from text using LIWC-22 features.
        
        CRITICAL: Single reviews (~100-500 words) are INSUFFICIENT for
        individual-level personality inference. Aggregate 10+ reviews
        (minimum 3000 words) for reliability.
        
        Expected accuracy ceiling: r = 0.20-0.40 for Big Five traits
        Reference: Koutsoumpis et al. (2022) meta-analysis (k=31, N=85,724)
        
        Args:
            text: Text to analyze (should be 3000+ words)
            existing_profile: Optional existing profile to update
            min_words: Minimum words for reliable inference
            
        Returns:
            BigFiveProfile with trait estimates
        """
        profile = existing_profile or BigFiveProfile()
        
        # Extract LIWC-style features
        features = self._extract_liwc_features(text)
        
        # Check if we have enough text
        word_count = features.get("word_count", 0)
        if word_count < min_words:
            logger.warning(
                f"Insufficient text for reliable LIWC inference: "
                f"{word_count} words (need {min_words}+). "
                f"Results will have low confidence."
            )
            confidence_penalty = 0.5  # Reduce confidence
        else:
            confidence_penalty = 1.0
        
        trait_signals: Dict[str, List[Tuple[float, float]]] = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": [],
        }
        
        # Apply LIWC → Big Five mappings
        for feature_name, trait_effects in self.LIWC_TO_BIG_FIVE.items():
            if feature_name not in features:
                continue
            
            feature_value = features[feature_name]
            
            for trait, correlation in trait_effects.items():
                if trait in trait_signals:
                    # Use correlation as effect size
                    trait_signals[trait].append((feature_value, correlation))
        
        # Aggregate signals for each trait
        for trait, signals in trait_signals.items():
            if not signals:
                continue
            
            total_weight = sum(abs(effect) for _, effect in signals)
            if total_weight > 0:
                weighted_sum = sum(
                    (0.5 + value * effect) * abs(effect)
                    for value, effect in signals
                )
                trait_value = weighted_sum / total_weight
                trait_value = max(0.0, min(1.0, trait_value))
                
                # Base confidence on effect sizes and word count
                confidence = min(0.8, 0.3 + len(signals) * 0.05 + total_weight * 0.5)
                confidence *= confidence_penalty
            else:
                trait_value = 0.5
                confidence = 0.2
            
            # Blend with existing profile if present
            if existing_profile:
                current = getattr(profile, trait)
                trait_value = current * 0.5 + trait_value * 0.5
            
            setattr(profile, trait, trait_value)
            setattr(profile, f"{trait}_confidence", confidence)
        
        profile.signals_used.append("liwc_text")
        profile.domains_used.append("linguistic")
        
        # Update overall confidence
        confidences = [
            profile.openness_confidence,
            profile.conscientiousness_confidence,
            profile.extraversion_confidence,
            profile.agreeableness_confidence,
            profile.neuroticism_confidence,
        ]
        profile.overall_confidence = sum(confidences) / len(confidences)
        
        self._inference_count += 1
        
        logger.info(
            f"Inferred personality from {word_count} words via LIWC: "
            f"O={profile.openness:.2f}, C={profile.conscientiousness:.2f}, "
            f"E={profile.extraversion:.2f}, A={profile.agreeableness:.2f}, "
            f"N={profile.neuroticism:.2f} (conf={profile.overall_confidence:.2f})"
        )
        
        return profile
    
    def infer_from_aggregated_texts(
        self,
        texts: List[str],
        existing_profile: Optional[BigFiveProfile] = None,
    ) -> BigFiveProfile:
        """
        Infer personality from multiple text samples.
        
        More reliable than single text - aggregates multiple reviews/posts.
        
        Args:
            texts: List of text samples (should total 3000+ words)
            existing_profile: Optional existing profile to update
            
        Returns:
            BigFiveProfile with trait estimates
        """
        combined_text = " ".join(texts)
        return self.infer_from_text(combined_text, existing_profile)
    
    def _extract_liwc_features(self, text: str) -> Dict[str, float]:
        """
        Extract LIWC-22 style features from text.
        
        This is a simplified extraction - production should use actual LIWC-22.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict of LIWC features (proportions and counts)
        """
        import re
        
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)
        word_count = len(words)
        
        if word_count == 0:
            return {"word_count": 0}
        
        features = {"word_count": word_count}
        
        # Positive emotion words
        positive_words = [
            'happy', 'good', 'great', 'love', 'nice', 'wonderful', 'excellent',
            'amazing', 'beautiful', 'best', 'enjoy', 'fun', 'glad', 'joy', 'like',
            'awesome', 'fantastic', 'perfect', 'positive', 'pleased',
        ]
        features["positive_emotion"] = sum(1 for w in words if w in positive_words) / word_count
        
        # Negative emotion words
        negative_words = [
            'bad', 'sad', 'angry', 'hate', 'terrible', 'awful', 'horrible',
            'upset', 'disappointed', 'frustrated', 'annoyed', 'worst', 'wrong',
            'hurt', 'pain', 'sorry', 'afraid', 'scared', 'worried',
        ]
        features["negative_emotion"] = sum(1 for w in words if w in negative_words) / word_count
        
        # Anxiety words
        anxiety_words = ['worried', 'nervous', 'anxious', 'afraid', 'scared', 'fear', 'stress']
        features["anxiety_words"] = sum(1 for w in words if w in anxiety_words) / word_count
        
        # Sadness words
        sadness_words = ['sad', 'cry', 'cried', 'depressed', 'lonely', 'miss', 'lost', 'grief']
        features["sadness_words"] = sum(1 for w in words if w in sadness_words) / word_count
        
        # Social words
        social_words = ['we', 'us', 'our', 'they', 'them', 'friends', 'family', 'people', 'together']
        features["social_words"] = sum(1 for w in words if w in social_words) / word_count
        
        # First person singular
        fp_singular = ['i', 'me', 'my', 'mine', 'myself']
        features["first_person_singular"] = sum(1 for w in words if w in fp_singular) / word_count
        
        # First person plural
        fp_plural = ['we', 'us', 'our', 'ours', 'ourselves']
        features["first_person_plural"] = sum(1 for w in words if w in fp_plural) / word_count
        
        # Insight words
        insight_words = ['think', 'know', 'consider', 'understand', 'realize', 'believe', 'feel']
        features["insight_words"] = sum(1 for w in words if w in insight_words) / word_count
        
        # Tentative words
        tentative_words = ['maybe', 'perhaps', 'might', 'possibly', 'probably', 'guess', 'seem']
        features["tentative_words"] = sum(1 for w in words if w in tentative_words) / word_count
        
        # Achievement words
        achievement_words = ['achieve', 'win', 'success', 'goal', 'accomplish', 'complete', 'earn']
        features["achievement_words"] = sum(1 for w in words if w in achievement_words) / word_count
        
        # Negations
        negations = ['no', 'not', 'never', 'none', 'nothing', 'neither', 'nobody']
        features["negations"] = sum(1 for w in words if w in negations) / word_count
        
        # Articles
        articles = ['a', 'an', 'the']
        features["articles"] = sum(1 for w in words if w in articles) / word_count
        
        # Six letter words (complexity)
        features["six_letter_words"] = sum(1 for w in words if len(w) >= 6) / word_count
        
        # Swear words (simplified list)
        swear_words = ['damn', 'hell', 'crap', 'suck', 'stupid', 'idiot']
        features["swear_words"] = sum(1 for w in words if w in swear_words) / word_count
        
        # Exclamation density
        exclamation_count = text.count('!')
        sentences = len(re.findall(r'[.!?]+', text)) or 1
        features["exclamation_density"] = min(1.0, exclamation_count / sentences)
        
        return features
    
    def get_stats(self) -> Dict[str, Any]:
        """Get inferencer statistics."""
        return {
            "inferences_performed": self._inference_count,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_inferencer: Optional[PersonalityInferencer] = None


def get_personality_inferencer() -> PersonalityInferencer:
    """Get singleton personality inferencer."""
    global _inferencer
    if _inferencer is None:
        _inferencer = PersonalityInferencer()
    return _inferencer
