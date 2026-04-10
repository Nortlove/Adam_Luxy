"""
CTV (Connected TV) Content Intelligence
==========================================

Profiles TV shows, movies, and streaming content on the full 20 edge
dimensions used across the bilateral cascade. CTV viewers are in deeper
psychological states than web readers due to sustained immersion
(20-60 min lean-back).

The key insight: we can't WATCH the content, but we can profile it
from description text + genre priors + viewer reviews. Genre priors
carry 60% weight because CTV descriptions are too short for reliable
text-based extraction.

Taxonomy: Platform → Genre → Show → Episode
Storage: informativ:ctv:profile:{content_id} (30-day TTL)
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

EDGE_DIMENSIONS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire", "interoceptive_awareness",
    "cooperative_framing_fit", "decision_entropy",
]

_REDIS_PREFIX = "informativ:ctv:"
_CTV_TTL = 86400 * 30  # 30 days


# ============================================================================
# CTV Content Metadata
# ============================================================================

@dataclass
class CTVContentMetadata:
    """Metadata for a CTV content item (show, movie, episode)."""
    content_id: str = ""
    title: str = ""
    series_title: str = ""
    season: int = 0
    episode: int = 0
    genre: List[str] = field(default_factory=list)
    subgenre: str = ""
    content_rating: str = ""
    runtime_minutes: int = 0
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    cast: List[str] = field(default_factory=list)
    director: str = ""
    network_platform: str = ""
    release_year: int = 0
    iab_categories: List[str] = field(default_factory=list)
    edge_dimensions: Dict[str, float] = field(default_factory=dict)
    mechanism_adjustments: Dict[str, float] = field(default_factory=dict)
    immersion_depth: float = 0.5
    confidence: float = 0.0


# ============================================================================
# Genre → Edge Dimension Priors (from Zillmann mood management + excitation transfer)
# ============================================================================

_GENRE_EDGE_PRIORS = {
    "thriller": {
        "regulatory_fit": 0.2,              # Prevention frame (threat avoidance)
        "construal_fit": 0.3,               # Concrete, present-focused tension
        "personality_alignment": 0.4,       # Moderate — appeals to sensation-seekers
        "emotional_resonance": 0.9,         # Maximum emotional activation
        "value_alignment": 0.4,             # Neutral
        "evolutionary_motive": 0.85,        # Threat detection, survival
        "linguistic_style": 0.5,            # Mixed register
        "persuasion_susceptibility": 0.7,   # High uncertainty = more persuadable
        "cognitive_load_tolerance": 0.3,    # Low remaining — tracking plot/clues
        "narrative_transport": 0.85,        # Deep narrative immersion
        "social_proof_sensitivity": 0.3,    # Individual survival focus
        "loss_aversion_intensity": 0.8,     # Strong threat/loss frame
        "temporal_discounting": 0.8,        # Present-focused (danger NOW)
        "brand_relationship_depth": 0.2,    # Not primed for brand thinking
        "autonomy_reactance": 0.25,         # Low — immersed, guard down
        "information_seeking": 0.6,         # Tracking clues
        "mimetic_desire": 0.3,              # Individual survival
        "interoceptive_awareness": 0.8,     # Heart racing, tension felt
        "cooperative_framing_fit": 0.3,     # Individual survival
        "decision_entropy": 0.7,            # High suspense uncertainty
    },
    "horror": {
        "regulatory_fit": 0.1,              # Maximum prevention/threat frame
        "construal_fit": 0.2,               # Hyper-concrete (danger NOW)
        "personality_alignment": 0.35,      # Niche — sensation-seeking subset
        "emotional_resonance": 0.95,        # Peak emotional activation
        "value_alignment": 0.3,             # Often transgressive
        "evolutionary_motive": 0.95,        # Maximum threat activation
        "linguistic_style": 0.4,            # Visceral language
        "persuasion_susceptibility": 0.75,  # Dread = high suggestibility
        "cognitive_load_tolerance": 0.4,    # Moderate — some pattern-tracking
        "narrative_transport": 0.88,        # Deep immersion in dread
        "social_proof_sensitivity": 0.2,    # Isolation psychology
        "loss_aversion_intensity": 0.9,     # Maximum threat/loss
        "temporal_discounting": 0.9,        # Hyper-present
        "brand_relationship_depth": 0.15,   # Not primed
        "autonomy_reactance": 0.2,          # Very low — terror suppresses resistance
        "information_seeking": 0.4,         # Some pattern-tracking
        "mimetic_desire": 0.2,              # Isolation
        "interoceptive_awareness": 0.9,     # Body awareness maximal (fear response)
        "cooperative_framing_fit": 0.2,     # Isolation
        "decision_entropy": 0.8,            # Dread from not knowing
    },
    "drama": {
        "regulatory_fit": 0.45,             # Neutral to slight prevention
        "construal_fit": 0.6,               # Abstract — character arcs, themes
        "personality_alignment": 0.6,       # Broad appeal
        "emotional_resonance": 0.65,        # Moderate emotional depth
        "value_alignment": 0.6,             # Often morality-focused
        "evolutionary_motive": 0.4,         # Status, belonging
        "linguistic_style": 0.6,            # Often elevated register
        "persuasion_susceptibility": 0.5,   # Moderate
        "cognitive_load_tolerance": 0.4,    # Emotional intelligence engaged
        "narrative_transport": 0.7,         # Strong narrative involvement
        "social_proof_sensitivity": 0.65,   # Relationship-focused, social comparison
        "loss_aversion_intensity": 0.45,    # Moderate
        "temporal_discounting": 0.4,        # Future-oriented (character arcs)
        "brand_relationship_depth": 0.4,    # Some loyalty themes
        "autonomy_reactance": 0.35,         # Moderate — reflective state
        "information_seeking": 0.5,         # Understanding motivations
        "mimetic_desire": 0.6,              # Social comparison, aspiration
        "interoceptive_awareness": 0.55,    # Emotional resonance felt
        "cooperative_framing_fit": 0.65,    # Relationship-focused
        "decision_entropy": 0.5,            # Moderate ambiguity
    },
    "comedy": {
        "regulatory_fit": 0.7,              # Approach-oriented, positive
        "construal_fit": 0.4,               # Concrete, present-moment
        "personality_alignment": 0.65,      # Broad appeal, extraversion
        "emotional_resonance": 0.6,         # Positive arousal
        "value_alignment": 0.5,             # Neutral
        "evolutionary_motive": 0.3,         # Status through humor
        "linguistic_style": 0.3,            # Casual register
        "persuasion_susceptibility": 0.55,  # Comfortable with absurdity
        "cognitive_load_tolerance": 0.7,    # Low load = high remaining tolerance
        "narrative_transport": 0.5,         # Moderate immersion
        "social_proof_sensitivity": 0.65,   # Social bonding/shared humor
        "loss_aversion_intensity": 0.2,     # Low threat
        "temporal_discounting": 0.7,        # Present-moment enjoyment
        "brand_relationship_depth": 0.3,    # Not primed
        "autonomy_reactance": 0.3,          # Guard down, relaxed
        "information_seeking": 0.3,         # Low
        "mimetic_desire": 0.6,              # Social bonding
        "interoceptive_awareness": 0.45,    # Moderate (laughter is physical)
        "cooperative_framing_fit": 0.65,    # Social bonding
        "decision_entropy": 0.4,            # Low ambiguity
    },
    "documentary": {
        "regulatory_fit": 0.45,             # Neutral — depends on topic
        "construal_fit": 0.75,              # Abstract, big-picture
        "personality_alignment": 0.5,       # Openness to experience
        "emotional_resonance": 0.45,        # Calm engagement
        "value_alignment": 0.6,             # Often value-driven
        "evolutionary_motive": 0.35,        # Knowledge acquisition
        "linguistic_style": 0.7,            # Formal register
        "persuasion_susceptibility": 0.4,   # Seeking answers (lower suggestibility)
        "cognitive_load_tolerance": 0.15,   # Very low — heavily engaged cognitively
        "narrative_transport": 0.6,         # Moderate immersion
        "social_proof_sensitivity": 0.45,   # Balanced
        "loss_aversion_intensity": 0.35,    # Low threat
        "temporal_discounting": 0.3,        # Future-oriented, big-picture
        "brand_relationship_depth": 0.35,   # Some authority priming
        "autonomy_reactance": 0.5,          # Moderate — analytical viewers
        "information_seeking": 0.85,        # Maximum — learning mode
        "mimetic_desire": 0.35,             # Individual reasoning
        "interoceptive_awareness": 0.35,    # Calm engagement
        "cooperative_framing_fit": 0.5,     # Balanced
        "decision_entropy": 0.45,           # Seeking clarity
    },
    "romance": {
        "regulatory_fit": 0.65,             # Approach/aspiration
        "construal_fit": 0.6,               # Abstract — future fantasy
        "personality_alignment": 0.6,       # Agreeableness, openness
        "emotional_resonance": 0.7,         # Strong emotional engagement
        "value_alignment": 0.65,            # Relationship values
        "evolutionary_motive": 0.7,         # Attraction, pair-bonding
        "linguistic_style": 0.5,            # Mixed register
        "persuasion_susceptibility": 0.5,   # Moderate
        "cognitive_load_tolerance": 0.7,    # Low load — emotional processing
        "narrative_transport": 0.7,         # Strong narrative involvement
        "social_proof_sensitivity": 0.75,   # Highly social/relational
        "loss_aversion_intensity": 0.3,     # Low threat
        "temporal_discounting": 0.4,        # Future fantasy
        "brand_relationship_depth": 0.5,    # Loyalty/commitment themes
        "autonomy_reactance": 0.3,          # Low — emotionally open
        "information_seeking": 0.25,        # Low
        "mimetic_desire": 0.75,             # Strong aspiration/comparison
        "interoceptive_awareness": 0.6,     # Warmth, physical attraction felt
        "cooperative_framing_fit": 0.8,     # Relationship-focused
        "decision_entropy": 0.35,           # Wants resolution
    },
    "sci_fi": {
        "regulatory_fit": 0.55,             # Exploration-oriented
        "construal_fit": 0.8,               # Abstract — future/possibility
        "personality_alignment": 0.55,      # Openness to experience
        "emotional_resonance": 0.6,         # Wonder/excitement
        "value_alignment": 0.5,             # Neutral
        "evolutionary_motive": 0.45,        # Exploration, adaptation
        "linguistic_style": 0.6,            # Technical register
        "persuasion_susceptibility": 0.6,   # Comfortable with unknown
        "cognitive_load_tolerance": 0.25,   # Low — complex world-building
        "narrative_transport": 0.75,        # Deep immersion
        "social_proof_sensitivity": 0.4,    # Individual exploration
        "loss_aversion_intensity": 0.35,    # Moderate
        "temporal_discounting": 0.2,        # Future-oriented
        "brand_relationship_depth": 0.3,    # Not primed
        "autonomy_reactance": 0.4,          # Moderate
        "information_seeking": 0.7,         # Curious, analytical
        "mimetic_desire": 0.35,             # Individual exploration
        "interoceptive_awareness": 0.55,    # Wonder felt physically
        "cooperative_framing_fit": 0.4,     # Individual exploration
        "decision_entropy": 0.6,            # Comfortable with ambiguity
    },
    "fantasy": {
        "regulatory_fit": 0.5,              # Mixed — heroes and villains
        "construal_fit": 0.55,              # Timeless/epic scope
        "personality_alignment": 0.55,      # Openness, imagination
        "emotional_resonance": 0.7,         # Epic emotional scale
        "value_alignment": 0.6,             # Honor, loyalty themes
        "evolutionary_motive": 0.6,         # Status, belonging, power
        "linguistic_style": 0.65,           # Elevated, archaic register
        "persuasion_susceptibility": 0.55,  # Embraces unknown
        "cognitive_load_tolerance": 0.35,   # World-building complexity
        "narrative_transport": 0.8,         # Deep immersion
        "social_proof_sensitivity": 0.55,   # Group dynamics, loyalty
        "loss_aversion_intensity": 0.45,    # Stakes but also hope
        "temporal_discounting": 0.5,        # Timeless scope
        "brand_relationship_depth": 0.4,    # Loyalty/heritage themes
        "autonomy_reactance": 0.3,          # Immersed, guard down
        "information_seeking": 0.55,        # Lore curiosity
        "mimetic_desire": 0.55,             # Hero emulation
        "interoceptive_awareness": 0.6,     # Epic emotional resonance
        "cooperative_framing_fit": 0.6,     # Group loyalty
        "decision_entropy": 0.5,            # Moderate ambiguity
    },
    "action": {
        "regulatory_fit": 0.6,              # Approach — conquering threats
        "construal_fit": 0.3,               # Concrete, present-focused
        "personality_alignment": 0.5,       # Sensation-seeking
        "emotional_resonance": 0.85,        # Maximum adrenaline
        "value_alignment": 0.4,             # Power/competence
        "evolutionary_motive": 0.75,        # Threat, status, dominance
        "linguistic_style": 0.35,           # Simple, direct
        "persuasion_susceptibility": 0.4,   # Clear good/evil = less persuadable
        "cognitive_load_tolerance": 0.7,    # Low load — spectacle-driven
        "narrative_transport": 0.65,        # Moderate immersion
        "social_proof_sensitivity": 0.4,    # Individual heroism
        "loss_aversion_intensity": 0.5,     # Stakes but hero wins
        "temporal_discounting": 0.8,        # Present-focused intensity
        "brand_relationship_depth": 0.25,   # Not primed
        "autonomy_reactance": 0.35,         # Low — swept up in action
        "information_seeking": 0.2,         # Low
        "mimetic_desire": 0.45,             # Hero emulation
        "interoceptive_awareness": 0.8,     # Adrenaline, physical response
        "cooperative_framing_fit": 0.4,     # Individual heroism
        "decision_entropy": 0.25,           # Clear outcomes
    },
    "true_crime": {
        "regulatory_fit": 0.25,             # Prevention/threat frame
        "construal_fit": 0.55,              # Past events, future safety
        "personality_alignment": 0.45,      # Analytical personality
        "emotional_resonance": 0.7,         # Morbid fascination
        "value_alignment": 0.55,            # Justice-oriented
        "evolutionary_motive": 0.75,        # Threat detection, safety
        "linguistic_style": 0.55,           # Journalistic register
        "persuasion_susceptibility": 0.6,   # Mystery = open to influence
        "cognitive_load_tolerance": 0.2,    # Heavily engaged — piecing clues
        "narrative_transport": 0.8,         # Deep investigation immersion
        "social_proof_sensitivity": 0.5,    # Community safety
        "loss_aversion_intensity": 0.7,     # Threat/loss salient
        "temporal_discounting": 0.5,        # Past events, future safety
        "brand_relationship_depth": 0.25,   # Not primed
        "autonomy_reactance": 0.3,          # Low — absorbed in content
        "information_seeking": 0.8,         # Analytical — seeking answers
        "mimetic_desire": 0.3,              # Individual analysis
        "interoceptive_awareness": 0.65,    # Tension, unease felt
        "cooperative_framing_fit": 0.5,     # Community safety
        "decision_entropy": 0.6,            # Mystery uncertainty
    },
    "reality": {
        "regulatory_fit": 0.6,              # Social approach
        "construal_fit": 0.35,              # Concrete, present drama
        "personality_alignment": 0.6,       # Extraversion, social comparison
        "emotional_resonance": 0.6,         # Gossip/drama arousal
        "value_alignment": 0.4,             # Aspirational
        "evolutionary_motive": 0.6,         # Status, mate selection
        "linguistic_style": 0.25,           # Very casual register
        "persuasion_susceptibility": 0.6,   # Moderate
        "cognitive_load_tolerance": 0.8,    # Very low load — easy viewing
        "narrative_transport": 0.45,        # Lower — reality breaks immersion
        "social_proof_sensitivity": 0.85,   # Maximum social comparison
        "loss_aversion_intensity": 0.3,     # Low stakes
        "temporal_discounting": 0.8,        # Present drama
        "brand_relationship_depth": 0.4,    # Product placement primed
        "autonomy_reactance": 0.3,          # Low — aspirational mimicry
        "information_seeking": 0.2,         # Low
        "mimetic_desire": 0.85,             # Maximum — wanting what others have
        "interoceptive_awareness": 0.4,     # Moderate
        "cooperative_framing_fit": 0.7,     # Social dynamics
        "decision_entropy": 0.4,            # Low ambiguity
    },
    "news": {
        "regulatory_fit": 0.35,             # Often threat-oriented
        "construal_fit": 0.45,              # Current events — mixed level
        "personality_alignment": 0.5,       # Conscientiousness
        "emotional_resonance": 0.55,        # Moderate alertness
        "value_alignment": 0.55,            # Civic values
        "evolutionary_motive": 0.55,        # Threat monitoring, status
        "linguistic_style": 0.7,            # Formal register
        "persuasion_susceptibility": 0.6,   # Evolving stories = persuadable
        "cognitive_load_tolerance": 0.3,    # Must process information
        "narrative_transport": 0.4,         # Low — factual, not narrative
        "social_proof_sensitivity": 0.6,    # Community concern
        "loss_aversion_intensity": 0.55,    # Threat-oriented reporting
        "temporal_discounting": 0.6,        # Current, somewhat present-focused
        "brand_relationship_depth": 0.35,   # Some authority priming
        "autonomy_reactance": 0.5,          # Moderate — viewers judge sources
        "information_seeking": 0.7,         # High — seeking understanding
        "mimetic_desire": 0.4,              # Moderate civic mimicry
        "interoceptive_awareness": 0.45,    # Moderate alertness
        "cooperative_framing_fit": 0.55,    # Community concern
        "decision_entropy": 0.6,            # Evolving/uncertain stories
    },
    "sports_live": {
        "regulatory_fit": 0.65,             # Competition/winning approach
        "construal_fit": 0.2,               # Hyper-concrete (live action)
        "personality_alignment": 0.6,       # Extraversion, competitiveness
        "emotional_resonance": 0.85,        # Peak excitement
        "value_alignment": 0.5,             # Team loyalty
        "evolutionary_motive": 0.7,         # Competition, tribal affiliation
        "linguistic_style": 0.3,            # Casual, exclamatory
        "persuasion_susceptibility": 0.55,  # High uncertainty in outcomes
        "cognitive_load_tolerance": 0.6,    # Moderate — tracking action
        "narrative_transport": 0.7,         # Immersed in unfolding drama
        "social_proof_sensitivity": 0.9,    # Maximum tribal/communal
        "loss_aversion_intensity": 0.6,     # Fear of team losing
        "temporal_discounting": 0.9,        # Hyper-present (live)
        "brand_relationship_depth": 0.5,    # Team loyalty = brand loyalty
        "autonomy_reactance": 0.25,         # Low — tribal conformity
        "information_seeking": 0.4,         # Stats tracking
        "mimetic_desire": 0.8,              # Tribal belonging
        "interoceptive_awareness": 0.75,    # Physical excitement
        "cooperative_framing_fit": 0.85,    # Maximum tribal solidarity
        "decision_entropy": 0.7,            # Outcome unknown
    },
    "cooking": {
        "regulatory_fit": 0.65,             # Positive, creative
        "construal_fit": 0.4,               # Concrete, process-oriented
        "personality_alignment": 0.55,      # Openness, agreeableness
        "emotional_resonance": 0.45,        # Calm, sensory engagement
        "value_alignment": 0.6,             # Nurturance, sharing
        "evolutionary_motive": 0.5,         # Nurturance, provision
        "linguistic_style": 0.45,           # Mixed — instructional
        "persuasion_susceptibility": 0.45,  # Structured/recipe-based
        "cognitive_load_tolerance": 0.5,    # Moderate — learning recipes
        "narrative_transport": 0.45,        # Moderate immersion
        "social_proof_sensitivity": 0.55,   # Sharing/hospitality
        "loss_aversion_intensity": 0.2,     # Low threat
        "temporal_discounting": 0.5,        # Process-oriented
        "brand_relationship_depth": 0.5,    # Product/ingredient loyalty
        "autonomy_reactance": 0.35,         # Open to instruction
        "information_seeking": 0.6,         # Learning recipes
        "mimetic_desire": 0.55,             # Food as identity
        "interoceptive_awareness": 0.6,     # Sensory — taste, smell
        "cooperative_framing_fit": 0.6,     # Sharing/hospitality
        "decision_entropy": 0.3,            # Structured recipes
    },
    "animation": {
        "regulatory_fit": 0.6,              # Generally positive
        "construal_fit": 0.45,              # Mixed
        "personality_alignment": 0.55,      # Broad — openness, agreeableness
        "emotional_resonance": 0.55,        # Moderate
        "value_alignment": 0.55,            # Family values
        "evolutionary_motive": 0.35,        # Low threat
        "linguistic_style": 0.4,            # Casual
        "persuasion_susceptibility": 0.5,   # Moderate
        "cognitive_load_tolerance": 0.6,    # Low load — easy viewing
        "narrative_transport": 0.6,         # Moderate immersion
        "social_proof_sensitivity": 0.55,   # Family/shared viewing
        "loss_aversion_intensity": 0.25,    # Low threat
        "temporal_discounting": 0.5,        # Mixed
        "brand_relationship_depth": 0.4,    # Franchise loyalty possible
        "autonomy_reactance": 0.3,          # Low
        "information_seeking": 0.35,        # Low
        "mimetic_desire": 0.5,              # Character identification
        "interoceptive_awareness": 0.4,     # Moderate
        "cooperative_framing_fit": 0.6,     # Family/shared viewing
        "decision_entropy": 0.4,            # Low ambiguity
    },
}

_GENRE_MINDSET_MAP = {
    "thriller": ("immersed_tense", {"loss_aversion": 1.4, "authority": 1.2, "scarcity": 1.3, "curiosity": 0.7}),
    "horror": ("immersed_tense", {"loss_aversion": 1.5, "authority": 1.3, "scarcity": 1.2, "social_proof": 0.6}),
    "drama": ("immersed_reflective", {"social_proof": 1.2, "commitment": 1.2, "liking": 1.3, "scarcity": 0.8}),
    "comedy": ("immersed_relaxed", {"liking": 1.4, "social_proof": 1.2, "curiosity": 1.1, "authority": 0.7}),
    "documentary": ("immersed_analytical", {"authority": 1.4, "commitment": 1.2, "social_proof": 1.1, "scarcity": 0.6}),
    "romance": ("immersed_emotional", {"liking": 1.4, "social_proof": 1.3, "unity": 1.3, "authority": 0.7}),
    "sci_fi": ("immersed_wonder", {"curiosity": 1.4, "authority": 1.1, "social_proof": 1.0, "scarcity": 0.8}),
    "fantasy": ("immersed_epic", {"unity": 1.3, "curiosity": 1.2, "social_proof": 1.1, "authority": 1.0}),
    "action": ("immersed_adrenaline", {"scarcity": 1.3, "loss_aversion": 1.2, "social_proof": 1.1, "authority": 0.8}),
    "true_crime": ("immersed_analytical", {"authority": 1.3, "curiosity": 1.3, "loss_aversion": 1.2, "liking": 0.7}),
    "reality": ("immersed_social", {"social_proof": 1.5, "liking": 1.3, "scarcity": 1.2, "authority": 0.6}),
    "news": ("informed", {"authority": 1.3, "social_proof": 1.1, "loss_aversion": 1.1, "scarcity": 0.8}),
    "sports_live": ("immersed_tribal", {"unity": 1.5, "social_proof": 1.4, "scarcity": 1.2, "authority": 0.7}),
    "cooking": ("immersed_creative", {"liking": 1.2, "social_proof": 1.1, "reciprocity": 1.2, "scarcity": 0.7}),
    "animation": ("immersed_relaxed", {"liking": 1.3, "social_proof": 1.1, "curiosity": 1.1, "authority": 0.8}),
}


# ============================================================================
# Immersion Depth Computation
# ============================================================================

def compute_immersion_depth(genre: List[str], runtime_minutes: int) -> float:
    """Compute how deeply immersed the viewer is.

    Immersion = base_immersion(genre) × duration_factor(runtime).
    Longer content and more absorbing genres create deeper states.
    """
    _BASE_IMMERSION = {
        "sports_live": 0.90, "horror": 0.88, "thriller": 0.85,
        "true_crime": 0.80, "drama": 0.75, "sci_fi": 0.75,
        "fantasy": 0.75, "action": 0.72, "documentary": 0.70,
        "romance": 0.65, "comedy": 0.55, "reality": 0.50,
        "cooking": 0.45, "animation": 0.50, "news": 0.40,
    }

    # Use highest immersion genre
    base = 0.5
    for g in genre:
        g_lower = g.lower().replace("-", "_").replace(" ", "_")
        base = max(base, _BASE_IMMERSION.get(g_lower, 0.5))

    # Duration factor: full immersion at 45+ minutes
    duration_factor = min(1.0, runtime_minutes / 45.0) if runtime_minutes > 0 else 0.6

    return round(base * duration_factor, 3)


# ============================================================================
# CTV Content Profiler
# ============================================================================

def profile_ctv_content(
    content_id: str,
    title: str,
    description: str = "",
    genre: List[str] = None,
    content_rating: str = "",
    runtime_minutes: int = 0,
    cast: List[str] = None,
    keywords: List[str] = None,
    viewer_reviews_text: str = "",
    platform: str = "",
) -> "PagePsychologicalProfile":
    """Profile CTV content on 20 edge dimensions for bilateral cascade.

    Returns a PagePsychologicalProfile so it plugs directly into the
    bilateral cascade's context modulation pathway.

    Strategy:
    1. Build scorable text from metadata
    2. Run score_page_full_width() for 20-dim edge extraction from text
    3. Blend 60% genre prior + 40% text edge profile
    4. Apply immersion depth amplification
    5. Set CTV-specific fields (content_type, mindset, bandwidth)
    """
    from adam.intelligence.page_intelligence import (
        PagePsychologicalProfile, profile_page_content,
    )
    try:
        from adam.intelligence.page_edge_scoring import score_page_full_width
        _has_edge_scoring = True
    except ImportError:
        _has_edge_scoring = False

    genre = genre or []
    cast = cast or []
    keywords = keywords or []

    # Build scorable text from all available metadata
    text_parts = []
    if title:
        text_parts.append(title)
    if description:
        text_parts.append(description)
    if genre:
        text_parts.append(f"Genre: {', '.join(genre)}")
    if keywords:
        text_parts.append(f"Themes: {', '.join(keywords[:10])}")
    if content_rating:
        text_parts.append(f"Rated {content_rating}")
    if viewer_reviews_text:
        text_parts.append(viewer_reviews_text[:2000])

    scorable_text = ". ".join(text_parts)

    # Run 20-dim edge extraction on the text (fallback to profile_page_content)
    profile = profile_page_content(
        url=f"ctv://{platform}/{content_id}",
        text_content=scorable_text,
        title=title,
    )

    if _has_edge_scoring:
        text_edge = score_page_full_width(text=scorable_text, url=f"ctv://{platform}/{content_id}")
    else:
        # Fallback: use construct_activations and fill missing dims with 0.5
        text_edge = {dim: profile.construct_activations.get(dim, 0.5)
                     for dim in EDGE_DIMENSIONS}

    # Get genre prior (use primary genre)
    genre_prior = {}
    primary_genre = ""
    for g in genre:
        g_lower = g.lower().replace("-", "_").replace(" ", "_")
        if g_lower in _GENRE_EDGE_PRIORS:
            genre_prior = _GENRE_EDGE_PRIORS[g_lower]
            primary_genre = g_lower
            break

    if not genre_prior and genre:
        # Try partial match
        for g in genre:
            g_lower = g.lower()
            for known_genre in _GENRE_EDGE_PRIORS:
                if known_genre in g_lower or g_lower in known_genre:
                    genre_prior = _GENRE_EDGE_PRIORS[known_genre]
                    primary_genre = known_genre
                    break
            if genre_prior:
                break

    # Blend: 60% genre prior, 40% text edge profile
    blended_edge = {}
    for dim in EDGE_DIMENSIONS:
        text_val = text_edge.dimensions.get(dim, 0.5)
        prior_val = genre_prior.get(dim, 0.5) if genre_prior else text_val
        blended_edge[dim] = round(0.6 * prior_val + 0.4 * text_val, 4)

    # Compute immersion depth
    immersion = compute_immersion_depth(genre, runtime_minutes)

    # Apply immersion amplification
    # Deeper immersion = stronger emotions, lower bandwidth, higher arousal
    blended_edge["emotional_resonance"] = min(1.0, blended_edge["emotional_resonance"] * (1 + immersion * 0.25))
    blended_edge["interoceptive_awareness"] = min(1.0, blended_edge["interoceptive_awareness"] * (1 + immersion * 0.2))
    blended_edge["narrative_transport"] = min(1.0, blended_edge["narrative_transport"] * (1 + immersion * 0.15))
    blended_edge["autonomy_reactance"] = max(0.0, blended_edge["autonomy_reactance"] * (1 - immersion * 0.2))
    # regulatory_fit amplification: deeper immersion intensifies approach/prevention frame
    rf = blended_edge["regulatory_fit"]
    if rf < 0.5:
        blended_edge["regulatory_fit"] = max(0.0, rf * (1 - immersion * 0.3))
    else:
        blended_edge["regulatory_fit"] = min(1.0, rf * (1 + immersion * 0.3))

    # Store as edge_dimensions (primary) and construct_activations (fallback compat)
    profile.edge_dimensions = {k: round(v, 4) for k, v in blended_edge.items()}
    profile.construct_activations = dict(profile.edge_dimensions)

    # Set CTV-specific profile fields
    profile.content_type = "ctv_content"
    profile.emotional_valence = blended_edge.get("regulatory_fit", 0.5) - 0.5  # Center on 0
    profile.emotional_arousal = blended_edge.get("emotional_resonance", 0.5)
    profile.cognitive_load = 1.0 - blended_edge.get("cognitive_load_tolerance", 0.5)

    # Remaining bandwidth is MUCH lower for CTV (viewer attention consumed)
    profile.remaining_bandwidth = round(max(0.05, 0.4 * (1 - immersion)), 3)

    # Mindset and mechanism adjustments from genre
    if primary_genre and primary_genre in _GENRE_MINDSET_MAP:
        mindset, mech_mods = _GENRE_MINDSET_MAP[primary_genre]
        profile.mindset = mindset
        profile.mechanism_adjustments = dict(mech_mods)
    else:
        profile.mindset = "immersed_relaxed"

    # Processing mode: CTV is almost always immersive or emotional
    if blended_edge.get("cognitive_load_tolerance", 0.5) < 0.3:
        profile.processing_mode = "immersive"  # Documentary, true crime (low tolerance = high load)
    elif blended_edge.get("emotional_resonance", 0.5) > 0.7:
        profile.processing_mode = "emotional"  # Thriller, horror, action
    else:
        profile.processing_mode = "immersive"  # Default for CTV

    # Decision style: CTV viewers are in lean-back mode
    profile.primed_decision_style = {
        "decision_speed": "impulsive" if immersion > 0.7 else "moderate",
        "evidence_needed": "low",  # Not in analytical mode
        "persuasion_framing": "emotional_appeal",
        "elm_route": "peripheral",  # Almost always peripheral for CTV ads
        "construal_level": "abstract",  # Big-picture from narrative immersion
        "risk_orientation": "risk_averse" if blended_edge.get("regulatory_fit", 0.5) < 0.35 else "balanced",
    }

    # Confidence based on available data
    conf = 0.3  # Base
    if description and len(description) > 50:
        conf += 0.15
    if genre_prior:
        conf += 0.2  # Genre priors are reliable
    if viewer_reviews_text and len(viewer_reviews_text) > 100:
        conf += 0.15
    if runtime_minutes > 0:
        conf += 0.05
    profile.confidence = min(0.9, conf)

    profile.profile_source = "ctv_profiled"
    profile.url_pattern = f"ctv:{platform}:{content_id}"
    profile.domain = platform or "ctv"

    # Ad strategy for CTV
    if primary_genre:
        profile.recommended_ad_strategy = (
            f"CTV viewer immersed in {primary_genre} content (immersion={immersion:.2f}). "
            f"Remaining bandwidth: {profile.remaining_bandwidth:.2f}. "
            f"Use {profile.primed_decision_style.get('persuasion_framing', 'balanced')} messaging. "
            f"ELM route: {profile.primed_decision_style.get('elm_route', 'peripheral')}. "
            f"Keep ads short and emotionally aligned with content mood."
        )

    profile.scoring_passes_completed = ["ctv_genre_blend"]
    profile.profile_version = 2

    return profile


# ============================================================================
# CTV Intelligence Cache
# ============================================================================

class CTVIntelligenceCache:
    """Redis-backed cache for CTV content profiles."""

    def __init__(self):
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.Redis(host="localhost", port=6379, decode_responses=True)
            self._redis.ping()
            return self._redis
        except Exception:
            return None

    def lookup(
        self,
        content_id: str = "",
        title: str = "",
        genre: List[str] = None,
        platform: str = "",
    ) -> Optional["PagePsychologicalProfile"]:
        """Look up CTV content profile with fallback to genre taxonomy."""
        from adam.intelligence.page_intelligence import PagePsychologicalProfile

        r = self._get_redis()
        if not r:
            return None

        # Try exact content_id match
        if content_id:
            try:
                data = r.hgetall(f"{_REDIS_PREFIX}profile:{content_id}")
                if data:
                    return PagePsychologicalProfile.from_redis_dict(data)
            except Exception:
                pass

        # Try title hash match
        if title:
            import hashlib
            title_hash = hashlib.md5(title.lower().encode()).hexdigest()[:12]
            try:
                resolved_id = r.get(f"{_REDIS_PREFIX}lookup:{title_hash}")
                if resolved_id:
                    data = r.hgetall(f"{_REDIS_PREFIX}profile:{resolved_id}")
                    if data:
                        return PagePsychologicalProfile.from_redis_dict(data)
            except Exception:
                pass

        # Fallback: genre-level taxonomy inference
        if genre and platform:
            for g in genre:
                g_lower = g.lower().replace("-", "_").replace(" ", "_")
                try:
                    data = r.hgetall(f"{_REDIS_PREFIX}taxonomy:{platform}:genre:{g_lower}")
                    if data and int(data.get("observation_count", 0)) >= 3:
                        # Build profile from genre centroid (20 edge dimensions)
                        edge_centroid = {}
                        for dim in EDGE_DIMENSIONS:
                            edge_centroid[dim] = float(data.get(f"centroid_{dim}", 0.5))

                        profile = profile_ctv_content(
                            content_id=content_id or "inferred",
                            title=title or "unknown",
                            genre=genre,
                            platform=platform,
                        )
                        profile.profile_source = "ctv_taxonomy_genre"
                        profile.confidence = min(0.5, float(data.get("overall_consistency", 0.3)))
                        return profile
                except Exception:
                    pass

        # Last resort: genre prior only (no Redis needed)
        if genre:
            profile = profile_ctv_content(
                content_id=content_id or "genre_prior",
                title=title or "unknown",
                genre=genre,
                platform=platform or "unknown",
            )
            profile.profile_source = "ctv_genre_prior"
            return profile

        return None

    def store(self, content_id: str, profile) -> bool:
        """Store a CTV content profile in Redis."""
        r = self._get_redis()
        if not r:
            return False

        try:
            key = f"{_REDIS_PREFIX}profile:{content_id}"
            r.hset(key, mapping=profile.to_redis_dict())
            r.expire(key, _CTV_TTL)

            # Also store title lookup
            if profile.url_pattern:
                import hashlib
                title = profile.url_pattern.split(":")[-1] if ":" in profile.url_pattern else content_id
                title_hash = hashlib.md5(title.lower().encode()).hexdigest()[:12]
                r.set(f"{_REDIS_PREFIX}lookup:{title_hash}", content_id, ex=_CTV_TTL)

            return True
        except Exception as e:
            logger.warning("CTV profile store failed: %s", e)
            return False


# ── Singleton ──

_ctv_cache: Optional[CTVIntelligenceCache] = None

def get_ctv_cache() -> CTVIntelligenceCache:
    global _ctv_cache
    if _ctv_cache is None:
        _ctv_cache = CTVIntelligenceCache()
    return _ctv_cache
