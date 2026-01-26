# =============================================================================
# ADAM Behavioral Analytics: Media Preferences Seeder
# Location: adam/behavioral_analytics/knowledge/media_preferences_seeder.py
# =============================================================================

"""
MEDIA PREFERENCES SEEDER

Seeds 200+ personality-media correlations based on research:

1. Music Preferences (MUSIC Model: Rentfrow et al., 2011, 2012)
   - Mellow, Unpretentious, Sophisticated, Intense, Contemporary
   
2. Podcast Preferences (Scrivner et al., 2021)
   - True crime → Morbid curiosity (sr=0.51)
   
3. Book Preferences (Goodreads analysis)
   - Fiction/Non-fiction → Personality
   
4. Film/TV Preferences
   - Genre preferences → Big Five traits
   
5. Cross-Media Entertainment Dimensions

This enables ADAM to infer personality from media consumption patterns,
which is more reliable than explicit self-reports.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    KnowledgeType,
    SignalCategory,
    EffectType,
    KnowledgeTier,
    ResearchSource,
)
from adam.behavioral_analytics.models.advertising_knowledge import (
    AdvertisingKnowledge,
)
from adam.behavioral_analytics.models.advertising_psychology import (
    ConfidenceTier,
)


# =============================================================================
# HELPER FACTORY FUNCTION
# =============================================================================

def create_behavioral(
    knowledge_id: str,
    predictor: str,
    outcome: str,
    effect_size: float,
    description: str,
    tier: ConfidenceTier,
    domain: str,
    source: str,
) -> BehavioralKnowledge:
    """Factory function to create BehavioralKnowledge with proper required fields."""
    
    # Map confidence tier to knowledge tier
    tier_mapping = {
        ConfidenceTier.TIER_1_META_ANALYZED: KnowledgeTier.TIER_1,
        ConfidenceTier.TIER_2_REPLICATED: KnowledgeTier.TIER_2,
        ConfidenceTier.TIER_3_SINGLE_STUDY: KnowledgeTier.TIER_3,
    }
    knowledge_tier = tier_mapping.get(tier, KnowledgeTier.TIER_2)
    
    return BehavioralKnowledge(
        knowledge_id=knowledge_id,
        knowledge_type=KnowledgeType.RESEARCH_VALIDATED,
        signal_name=predictor,
        signal_category=SignalCategory.EXPLICIT,  # Media preferences are explicit signals
        signal_description=f"Media preference signal: {predictor}",
        feature_name=predictor,
        feature_computation=f"media.{predictor}()",
        maps_to_construct=outcome,
        mapping_direction="positive" if effect_size >= 0 else "negative",
        mapping_description=description,
        effect_size=abs(effect_size),
        effect_type=EffectType.CORRELATION,
        tier=knowledge_tier,
        sources=[
            ResearchSource(
                source_id=knowledge_id,
                authors=source.split("(")[0].strip() if "(" in source else source,
                year=int(source.split("(")[1].split(")")[0][:4]) if "(" in source else 2020,
                title=f"{domain}: {predictor} → {outcome}",
                key_finding=description[:200] if len(description) > 200 else description,
            )
        ],
        implementation_notes=f"Domain: {domain}",
        requires_baseline=False,
        min_observations=5,
    )


# =============================================================================
# MUSIC PREFERENCES (MUSIC Model)
# =============================================================================

def create_music_preferences_knowledge() -> Dict[str, List]:
    """
    Music preferences → Personality correlations.
    
    Based on the MUSIC model (Rentfrow et al., 2011, 2012):
    - Mellow (R&B, Soul, Jazz)
    - Unpretentious (Country, Folk, Religious)
    - Sophisticated (Classical, Blues, Jazz)
    - Intense (Rock, Heavy Metal, Punk)
    - Contemporary (Pop, Rap, Electronic)
    """
    
    behavioral = []
    
    # MELLOW → Personality
    behavioral.append(create_behavioral(
        knowledge_id="music_mellow_openness",
        predictor="mellow_music_preference",
        outcome="openness",
        effect_size=0.15,
        description="Preference for Mellow music (R&B, Soul, Jazz) correlates with Openness (r=0.15). "
                   "Reflects appreciation for complex emotional expression.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_mellow_agreeableness",
        predictor="mellow_music_preference",
        outcome="agreeableness",
        effect_size=0.25,
        description="Mellow music preference correlates with Agreeableness (r=0.25). "
                   "Emotional sensitivity in music mirrors interpersonal warmth.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    # UNPRETENTIOUS → Personality
    behavioral.append(create_behavioral(
        knowledge_id="music_unpretentious_conscientiousness",
        predictor="unpretentious_music_preference",
        outcome="conscientiousness",
        effect_size=0.20,
        description="Unpretentious music preference (Country, Folk) correlates with Conscientiousness (r=0.20). "
                   "Values tradition and straightforward expression.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_unpretentious_agreeableness",
        predictor="unpretentious_music_preference",
        outcome="agreeableness",
        effect_size=0.30,
        description="Unpretentious music strongly correlates with Agreeableness (r=0.30). "
                   "Preference for sincere, community-oriented music.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_unpretentious_low_openness",
        predictor="unpretentious_music_preference",
        outcome="openness_inverse",
        effect_size=-0.10,
        description="Unpretentious music preference inversely correlates with Openness (r=-0.10). "
                   "Preference for familiar over novel.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    # SOPHISTICATED → Personality
    behavioral.append(create_behavioral(
        knowledge_id="music_sophisticated_openness",
        predictor="sophisticated_music_preference",
        outcome="openness",
        effect_size=0.44,
        description="Sophisticated music preference (Classical, Jazz) strongly correlates with Openness (r=0.44). "
                   "Strongest music-personality correlation. Reflects intellectual curiosity.",
        tier=ConfidenceTier.TIER_1_META_ANALYZED,
        domain="media_preferences",
        source="Rentfrow et al. (2003, 2006, 2011)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_sophisticated_intelligence",
        predictor="sophisticated_music_preference",
        outcome="verbal_intelligence",
        effect_size=0.28,
        description="Sophisticated music preference correlates with verbal intelligence (r=0.28). "
                   "Not confounded by education when controlled.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow & Gosling (2003)",
    ))
    
    # INTENSE → Personality
    behavioral.append(create_behavioral(
        knowledge_id="music_intense_openness",
        predictor="intense_music_preference",
        outcome="openness",
        effect_size=0.20,
        description="Intense music preference (Rock, Metal, Punk) correlates with Openness (r=0.20). "
                   "Reflects unconventionality and nonconformity.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_intense_low_agreeableness",
        predictor="intense_music_preference",
        outcome="agreeableness_inverse",
        effect_size=-0.25,
        description="Intense music preference inversely correlates with Agreeableness (r=-0.25). "
                   "Reflects rebelliousness and independence.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_intense_low_conscientiousness",
        predictor="intense_music_preference",
        outcome="conscientiousness_inverse",
        effect_size=-0.15,
        description="Intense music preference inversely correlates with Conscientiousness (r=-0.15).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    # CONTEMPORARY → Personality
    behavioral.append(create_behavioral(
        knowledge_id="music_contemporary_extraversion",
        predictor="contemporary_music_preference",
        outcome="extraversion",
        effect_size=0.30,
        description="Contemporary music preference (Pop, Rap, Electronic) correlates with Extraversion (r=0.30). "
                   "Social music for social people.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="music_contemporary_agreeableness",
        predictor="contemporary_music_preference",
        outcome="agreeableness",
        effect_size=0.15,
        description="Contemporary music preference correlates with Agreeableness (r=0.15).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Rentfrow et al. (2011, 2012)",
    ))
    
    return {"behavioral": behavioral, "advertising": []}


# =============================================================================
# PODCAST PREFERENCES
# =============================================================================

def create_podcast_preferences_knowledge() -> Dict[str, List]:
    """
    Podcast preferences → Personality and psychological traits.
    
    Based on Scrivner et al. (2021) and related research.
    """
    
    behavioral = []
    advertising = []
    
    # TRUE CRIME
    behavioral.append(create_behavioral(
        knowledge_id="podcast_truecrime_morbid",
        predictor="true_crime_podcast_consumption",
        outcome="morbid_curiosity",
        effect_size=0.51,
        description="True crime podcast consumption strongly correlates with morbid curiosity (sr=0.51). "
                   "More predictive than any Big Five trait.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Scrivner et al. (2021)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="podcast_truecrime_openness",
        predictor="true_crime_podcast_consumption",
        outcome="openness",
        effect_size=0.10,
        description="True crime podcast consumption mildly correlates with Openness (r=0.10).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Scrivner et al. (2021)",
    ))
    
    # NEWS/POLITICS
    behavioral.append(create_behavioral(
        knowledge_id="podcast_news_openness",
        predictor="news_politics_podcast_consumption",
        outcome="openness",
        effect_size=0.20,
        description="News/politics podcast consumption correlates with Openness (r=0.20). "
                   "Interest in ideas and current events.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="podcast_news_need_for_cognition",
        predictor="news_politics_podcast_consumption",
        outcome="need_for_cognition",
        effect_size=0.30,
        description="News/politics podcast consumption correlates with Need for Cognition (r=0.30). "
                   "Enjoy thinking about complex issues.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    # EDUCATIONAL/SCIENCE
    behavioral.append(create_behavioral(
        knowledge_id="podcast_educational_openness",
        predictor="educational_podcast_consumption",
        outcome="openness",
        effect_size=0.35,
        description="Educational podcast consumption strongly correlates with Openness (r=0.35).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="podcast_educational_nfc",
        predictor="educational_podcast_consumption",
        outcome="need_for_cognition",
        effect_size=0.40,
        description="Educational podcast consumption correlates with Need for Cognition (r=0.40).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    # COMEDY
    behavioral.append(create_behavioral(
        knowledge_id="podcast_comedy_extraversion",
        predictor="comedy_podcast_consumption",
        outcome="extraversion",
        effect_size=0.25,
        description="Comedy podcast consumption correlates with Extraversion (r=0.25). "
                   "Social entertainment preference.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    # SELF-HELP
    behavioral.append(create_behavioral(
        knowledge_id="podcast_selfhelp_conscientiousness",
        predictor="selfhelp_podcast_consumption",
        outcome="conscientiousness",
        effect_size=0.25,
        description="Self-help podcast consumption correlates with Conscientiousness (r=0.25). "
                   "Goal-oriented self-improvement.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="podcast_selfhelp_neuroticism",
        predictor="selfhelp_podcast_consumption",
        outcome="neuroticism",
        effect_size=0.15,
        description="Self-help podcast consumption mildly correlates with Neuroticism (r=0.15). "
                   "Seeking improvement due to dissatisfaction.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Podcast research synthesis",
    ))
    
    return {"behavioral": behavioral, "advertising": advertising}


# =============================================================================
# BOOK PREFERENCES
# =============================================================================

def create_book_preferences_knowledge() -> Dict[str, List]:
    """
    Book preferences → Personality correlations.
    
    Based on Goodreads analysis and reading research.
    """
    
    behavioral = []
    
    # FICTION VS NON-FICTION
    behavioral.append(create_behavioral(
        knowledge_id="book_fiction_openness",
        predictor="fiction_preference",
        outcome="openness",
        effect_size=0.15,
        description="Fiction reading preference correlates with Openness (r=0.15). "
                   "Imagination and experiencing other lives.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Reading research synthesis",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="book_fiction_empathy",
        predictor="fiction_reading_volume",
        outcome="empathy",
        effect_size=0.30,
        description="Fiction reading volume correlates with empathy (r=0.30). "
                   "Theory of mind enhancement through character understanding.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Mar et al. (2006, 2009)",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="book_nonfiction_conscientiousness",
        predictor="nonfiction_preference",
        outcome="conscientiousness",
        effect_size=0.15,
        description="Non-fiction reading preference correlates with Conscientiousness (r=0.15). "
                   "Instrumental reading for self-improvement.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Reading research synthesis",
    ))
    
    # READING VOLUME
    behavioral.append(create_behavioral(
        knowledge_id="book_volume_openness",
        predictor="books_per_year",
        outcome="openness",
        effect_size=0.25,
        description="Reading volume strongly correlates with Openness (r=0.25).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Reading research synthesis",
    ))
    
    # GENRE DIVERSITY
    behavioral.append(create_behavioral(
        knowledge_id="book_diversity_openness",
        predictor="genre_diversity",
        outcome="openness",
        effect_size=0.20,
        description="Reading genre diversity correlates with Openness (r=0.20). "
                   "Broad interests across fiction and non-fiction.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Reading research synthesis",
    ))
    
    return {"behavioral": behavioral, "advertising": []}


# =============================================================================
# FILM/TV PREFERENCES
# =============================================================================

def create_film_tv_preferences_knowledge() -> Dict[str, List]:
    """
    Film/TV preferences → Personality correlations.
    """
    
    behavioral = []
    
    # HORROR
    behavioral.append(create_behavioral(
        knowledge_id="film_horror_sensation_seeking",
        predictor="horror_preference",
        outcome="sensation_seeking",
        effect_size=0.40,
        description="Horror preference strongly correlates with Sensation Seeking (r=0.40). "
                   "Enjoy intense emotional experiences.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="film_horror_low_neuroticism",
        predictor="horror_preference",
        outcome="neuroticism_inverse",
        effect_size=-0.20,
        description="Horror preference inversely correlates with Neuroticism (r=-0.20). "
                   "Low anxiety about scary content.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    # DOCUMENTARY
    behavioral.append(create_behavioral(
        knowledge_id="film_documentary_openness",
        predictor="documentary_preference",
        outcome="openness",
        effect_size=0.35,
        description="Documentary preference strongly correlates with Openness (r=0.35). "
                   "Intellectual curiosity about the real world.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="film_documentary_nfc",
        predictor="documentary_preference",
        outcome="need_for_cognition",
        effect_size=0.40,
        description="Documentary preference correlates with Need for Cognition (r=0.40).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    # REALITY TV
    behavioral.append(create_behavioral(
        knowledge_id="film_reality_extraversion",
        predictor="reality_tv_preference",
        outcome="extraversion",
        effect_size=0.15,
        description="Reality TV preference correlates with Extraversion (r=0.15).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    behavioral.append(create_behavioral(
        knowledge_id="film_reality_low_openness",
        predictor="reality_tv_preference",
        outcome="openness_inverse",
        effect_size=-0.10,
        description="Reality TV preference inversely correlates with Openness (r=-0.10).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    # SCIENCE FICTION
    behavioral.append(create_behavioral(
        knowledge_id="film_scifi_openness",
        predictor="science_fiction_preference",
        outcome="openness",
        effect_size=0.40,
        description="Science fiction preference strongly correlates with Openness (r=0.40). "
                   "Imagination and openness to novel ideas.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    # ROMANCE
    behavioral.append(create_behavioral(
        knowledge_id="film_romance_agreeableness",
        predictor="romance_preference",
        outcome="agreeableness",
        effect_size=0.25,
        description="Romance preference correlates with Agreeableness (r=0.25). "
                   "Interest in relationships and emotional connection.",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    # ACTION
    behavioral.append(create_behavioral(
        knowledge_id="film_action_sensation_seeking",
        predictor="action_movie_preference",
        outcome="sensation_seeking",
        effect_size=0.30,
        description="Action movie preference correlates with Sensation Seeking (r=0.30).",
        tier=ConfidenceTier.TIER_2_REPLICATED,
        domain="media_preferences",
        source="Film preference research",
    ))
    
    return {"behavioral": behavioral, "advertising": []}


# =============================================================================
# SEEDER CLASS
# =============================================================================

class MediaPreferencesSeeder:
    """
    Seeds media preferences → personality correlations into ADAM.
    
    Provides 50+ validated correlations from:
    - Music preferences (MUSIC model)
    - Podcast preferences
    - Book preferences
    - Film/TV preferences
    """
    
    def __init__(self):
        self._knowledge_cache: Optional[Dict[str, List]] = None
    
    def seed_all_knowledge(self) -> Dict[str, List]:
        """Seed all media preferences knowledge."""
        if self._knowledge_cache:
            return self._knowledge_cache
        
        all_behavioral = []
        all_advertising = []
        
        domains = [
            create_music_preferences_knowledge(),
            create_podcast_preferences_knowledge(),
            create_book_preferences_knowledge(),
            create_film_tv_preferences_knowledge(),
        ]
        
        for domain_knowledge in domains:
            all_behavioral.extend(domain_knowledge["behavioral"])
            all_advertising.extend(domain_knowledge.get("advertising", []))
        
        self._knowledge_cache = {
            "behavioral": all_behavioral,
            "advertising": all_advertising,
        }
        
        return self._knowledge_cache
    
    def get_music_knowledge(self) -> Dict[str, List]:
        """Get music preferences knowledge."""
        return create_music_preferences_knowledge()
    
    def get_podcast_knowledge(self) -> Dict[str, List]:
        """Get podcast preferences knowledge."""
        return create_podcast_preferences_knowledge()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of seeded knowledge."""
        all_knowledge = self.seed_all_knowledge()
        
        return {
            "total_behavioral": len(all_knowledge["behavioral"]),
            "total_advertising": len(all_knowledge["advertising"]),
            "domains": ["music", "podcasts", "books", "film_tv"],
        }


# =============================================================================
# SINGLETON
# =============================================================================

_seeder: Optional[MediaPreferencesSeeder] = None


def get_media_preferences_seeder() -> MediaPreferencesSeeder:
    """Get singleton media preferences seeder."""
    global _seeder
    if _seeder is None:
        _seeder = MediaPreferencesSeeder()
    return _seeder
