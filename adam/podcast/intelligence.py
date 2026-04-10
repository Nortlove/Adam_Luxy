"""
Podcast Content Intelligence Engine
======================================

Profiles podcast shows and audiences using the ADAM psychological
construct framework. Instead of genre-based targeting ("true crime
listeners like X"), this engine reasons inferentially:

    Show Content → Psychological Constructs → Audience Profile →
    Mechanism Recommendations → Creative Guidance

Genre-to-personality mapping based on:
- Rentfrow & Gosling (2003): Music preferences and personality
- Greenberg et al. (2016): Genre-personality links validated at scale
- ADAM construct registry adaptation for podcast genres

This engine powers the Audioboom integration by providing:
1. Show psychological profiles (construct activations from genre + content)
2. Audience personality inference (what Big Five traits does this show attract?)
3. Mechanism recommendations (what persuasion works for this audience?)
4. Creative guidance (how should host-read ads be structured?)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=30)
    else:
        return asyncio.run(coro)


# =============================================================================
# GENRE → PERSONALITY MAPPING (Research-Backed)
# =============================================================================

# Based on Rentfrow & Gosling (2003, 2011), adapted for podcast genres
GENRE_PERSONALITY_MAP = {
    "true_crime": {
        "openness": 0.65, "conscientiousness": 0.55, "extraversion": 0.40,
        "agreeableness": 0.45, "neuroticism": 0.60,
        "constructs": {
            "need_for_cognition": 0.75, "curiosity": 0.70,
            "uncertainty_tolerance": 0.55, "analytical_processing": 0.65,
            "sensation_seeking": 0.50,
        },
        "audience_description": "Analytically curious, detail-oriented listeners comfortable with dark content",
    },
    "comedy": {
        "openness": 0.70, "conscientiousness": 0.40, "extraversion": 0.75,
        "agreeableness": 0.60, "neuroticism": 0.35,
        "constructs": {
            "social_proof_susceptibility": 0.65, "arousal_seeking": 0.60,
            "approach_motivation": 0.70, "conformity_need": 0.50,
        },
        "audience_description": "Social, outgoing listeners seeking entertainment and connection",
    },
    "news_politics": {
        "openness": 0.75, "conscientiousness": 0.65, "extraversion": 0.50,
        "agreeableness": 0.40, "neuroticism": 0.55,
        "constructs": {
            "need_for_cognition": 0.80, "analytical_processing": 0.75,
            "cognitive_engagement": 0.70, "identity_salience": 0.60,
        },
        "audience_description": "Informed, engaged citizens with strong cognitive processing needs",
    },
    "business": {
        "openness": 0.55, "conscientiousness": 0.80, "extraversion": 0.60,
        "agreeableness": 0.45, "neuroticism": 0.40,
        "constructs": {
            "status_sensitivity": 0.70, "self_enhancement": 0.65,
            "cognitive_engagement": 0.70, "delay_tolerance": 0.65,
        },
        "audience_description": "Achievement-oriented professionals focused on growth and status",
    },
    "health_wellness": {
        "openness": 0.65, "conscientiousness": 0.70, "extraversion": 0.50,
        "agreeableness": 0.65, "neuroticism": 0.55,
        "constructs": {
            "prevention_focus": 0.70, "trust_propensity": 0.60,
            "conscientiousness": 0.70, "risk_sensitivity": 0.65,
        },
        "audience_description": "Health-conscious, prevention-oriented listeners seeking trusted guidance",
    },
    "technology": {
        "openness": 0.80, "conscientiousness": 0.60, "extraversion": 0.45,
        "agreeableness": 0.50, "neuroticism": 0.40,
        "constructs": {
            "openness": 0.80, "need_for_cognition": 0.75,
            "curiosity": 0.80, "analytical_processing": 0.70,
        },
        "audience_description": "Intellectually curious, innovation-oriented early adopters",
    },
    "sports": {
        "openness": 0.45, "conscientiousness": 0.55, "extraversion": 0.75,
        "agreeableness": 0.55, "neuroticism": 0.50,
        "constructs": {
            "social_proof_susceptibility": 0.70, "identity_salience": 0.75,
            "arousal_seeking": 0.65, "conformity_need": 0.60,
        },
        "audience_description": "Identity-driven, socially connected fans with tribal loyalties",
    },
    "education_learning": {
        "openness": 0.80, "conscientiousness": 0.75, "extraversion": 0.45,
        "agreeableness": 0.60, "neuroticism": 0.40,
        "constructs": {
            "need_for_cognition": 0.85, "curiosity": 0.80,
            "cognitive_engagement": 0.80, "delay_tolerance": 0.70,
        },
        "audience_description": "Lifelong learners with deep intellectual engagement",
    },
    "parenting_family": {
        "openness": 0.55, "conscientiousness": 0.70, "extraversion": 0.55,
        "agreeableness": 0.80, "neuroticism": 0.60,
        "constructs": {
            "prevention_focus": 0.70, "trust_propensity": 0.65,
            "relatedness_need": 0.80, "risk_aversion": 0.65,
        },
        "audience_description": "Caring, community-oriented parents seeking trusted guidance",
    },
    "arts_culture": {
        "openness": 0.90, "conscientiousness": 0.50, "extraversion": 0.50,
        "agreeableness": 0.60, "neuroticism": 0.55,
        "constructs": {
            "openness": 0.90, "curiosity": 0.80,
            "identity_salience": 0.60, "sensation_seeking": 0.55,
        },
        "audience_description": "Aesthetically sensitive, culturally engaged listeners",
    },
}


# =============================================================================
# SHOW PROFILE MODEL
# =============================================================================

@dataclass
class PodcastShowProfile:
    """Psychological profile of a podcast show."""
    show_id: str
    show_name: str
    genre: str
    
    # Big Five audience profile
    audience_personality: Dict[str, float] = field(default_factory=dict)
    
    # Construct activations
    audience_constructs: Dict[str, float] = field(default_factory=dict)
    
    # Description
    audience_description: str = ""
    
    # Mechanism recommendations for this audience
    mechanism_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Creative guidance for host-read ads
    host_read_guidance: Dict[str, Any] = field(default_factory=dict)
    
    # Estimated audience size (from Audioboom or estimates)
    estimated_downloads: int = 0
    
    # Match quality for advertisers
    advertiser_match_scores: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "show_id": self.show_id,
            "show_name": self.show_name,
            "genre": self.genre,
            "audience_personality": {
                k: round(v, 2) for k, v in self.audience_personality.items()
            },
            "audience_constructs": {
                k: round(v, 2) for k, v in self.audience_constructs.items()
            },
            "audience_description": self.audience_description,
            "mechanism_recommendations": self.mechanism_recommendations,
            "host_read_guidance": self.host_read_guidance,
            "estimated_downloads": self.estimated_downloads,
        }


# =============================================================================
# PODCAST INTELLIGENCE ENGINE
# =============================================================================

class PodcastIntelligenceEngine:
    """
    Profiles podcast shows and their audiences using psychological constructs.

    PRIMARY PATH: GraphStateInferenceEngine for construct activations from
                  show metadata, with graph-backed personality inference
    FALLBACK: GENRE_PERSONALITY_MAP static mappings
    """

    def __init__(self):
        self._graph_service = None

    def _get_graph_service(self):
        if self._graph_service is None:
            try:
                from adam.services.graph_intelligence import get_graph_intelligence_service
                self._graph_service = get_graph_intelligence_service()
            except ImportError:
                self._graph_service = None
        return self._graph_service

    def profile_show(
        self,
        show_id: str,
        show_name: str,
        genre: str,
        description: str = "",
        estimated_downloads: int = 50000,
    ) -> PodcastShowProfile:
        """
        Generate a psychological profile for a podcast show.

        PRIMARY: Graph-inferred constructs from genre/description keywords
        FALLBACK: GENRE_PERSONALITY_MAP static lookup
        """
        # Try graph-backed profiling first
        try:
            graph_profile = self._profile_from_graph(
                show_id, show_name, genre, description, estimated_downloads
            )
            if graph_profile:
                return graph_profile
        except Exception as e:
            logger.debug(f"Graph profiling failed for {show_name}: {e}")

        # FALLBACK: static genre mapping
        return self._profile_from_static(
            show_id, show_name, genre, description, estimated_downloads
        )

    def _profile_from_graph(
        self,
        show_id: str,
        show_name: str,
        genre: str,
        description: str,
        estimated_downloads: int,
    ) -> Optional[PodcastShowProfile]:
        """Profile a show using live graph data."""
        gs = self._get_graph_service()
        if gs is None:
            return None

        # Map podcast genre to psychological domain
        genre_domain_map = {
            "true_crime": "cognition",
            "comedy": "social_influence",
            "news_politics": "cognition",
            "business": "motivation",
            "health_wellness": "motivation",
            "technology": "cognition",
            "sports": "social_influence",
            "education_learning": "cognition",
            "parenting_family": "decision_making",
            "arts_culture": "cognition",
        }
        genre_key = genre.lower().replace(" ", "_").replace("-", "_").replace("&", "")
        domain = genre_domain_map.get(genre_key, "cognition")

        # Get constructs from this domain
        domain_constructs = _run_async(gs.get_constructs_by_domain(domain))
        if not domain_constructs:
            return None

        # Get mechanism effectiveness for this genre-as-category
        mech_eff = _run_async(gs.get_mechanism_effectiveness(genre_key))

        # Build construct activations from graph data
        # Weight constructs by their relevance to the genre
        construct_activations = {}
        for dc in domain_constructs[:8]:
            cid = dc["construct_id"]
            # Base activation from domain presence
            activation = 0.5 + (dc.get("confidence", 0.5) - 0.5) * 0.5
            construct_activations[cid] = round(activation, 2)

        # Derive Big Five personality from construct activations
        personality = self._derive_personality_from_constructs(construct_activations)

        # Build audience description from top constructs
        top_construct_names = [
            dc.get("name", dc["construct_id"]).replace("_", " ")
            for dc in domain_constructs[:3]
        ]
        audience_desc = (
            f"Audience with high {', '.join(top_construct_names)} — "
            f"inferred from {domain} domain graph constructs"
        )

        profile = PodcastShowProfile(
            show_id=show_id,
            show_name=show_name,
            genre=genre,
            audience_personality=personality,
            audience_constructs=construct_activations,
            audience_description=audience_desc,
            estimated_downloads=estimated_downloads,
        )

        # Mechanism recommendations from graph
        profile.mechanism_recommendations = self._recommend_mechanisms_from_graph(
            mech_eff, personality
        )

        # Host guidance from personality
        profile.host_read_guidance = self._generate_host_guidance_from_personality(
            personality, show_name
        )

        return profile

    def _derive_personality_from_constructs(
        self,
        construct_activations: Dict[str, float],
    ) -> Dict[str, float]:
        """Reverse Big Five mapping from construct activations."""
        # Construct → Big Five influence mapping
        construct_big5_influence = {
            "openness": ["curiosity", "openness", "sensation_seeking", "cognitive_engagement"],
            "conscientiousness": ["need_for_cognition", "analytical_processing", "delay_tolerance", "conscientiousness"],
            "extraversion": ["arousal_seeking", "approach_motivation", "social_proof_susceptibility", "extraversion"],
            "agreeableness": ["trust_propensity", "relatedness_need", "agreeableness", "conformity_need"],
            "neuroticism": ["risk_sensitivity", "prevention_focus", "uncertainty_intolerance", "loss_aversion"],
        }

        personality = {}
        for trait, related_constructs in construct_big5_influence.items():
            scores = []
            for rc in related_constructs:
                for cid, activation in construct_activations.items():
                    if rc in cid.lower():
                        scores.append(activation)
            personality[trait] = round(sum(scores) / len(scores), 2) if scores else 0.5

        return personality

    def _recommend_mechanisms_from_graph(
        self,
        mech_eff: Dict[str, Dict[str, Any]],
        personality: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Generate mechanism recommendations from graph effectiveness data."""
        if mech_eff:
            recommendations = []
            for mech_id, data in sorted(
                mech_eff.items(), key=lambda x: x[1].get("score", 0), reverse=True
            )[:5]:
                recommendations.append({
                    "mechanism": mech_id,
                    "predicted_effectiveness": round(data.get("score", 0.5), 2),
                    "reasoning": (
                        f"Graph-empirical: {mech_id} effectiveness "
                        f"{data.get('score', 0):.0%} (source: {data.get('source', 'graph')})"
                    ),
                })
            if recommendations:
                return recommendations

        # Fallback to personality-based heuristic
        return self._recommend_mechanisms_static(personality)

    def _recommend_mechanisms_static(
        self,
        personality: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Static personality → mechanism mapping (fallback)."""
        mech_scores = {}
        if personality.get("extraversion", 0.5) > 0.6:
            mech_scores["social_proof"] = personality["extraversion"]
            mech_scores["mimetic_desire"] = personality["extraversion"] * 0.8
        if personality.get("conscientiousness", 0.5) > 0.6:
            mech_scores["authority"] = personality["conscientiousness"]
            mech_scores["commitment"] = personality["conscientiousness"] * 0.8
        if personality.get("openness", 0.5) > 0.6:
            mech_scores["identity_construction"] = personality["openness"] * 0.9
            mech_scores["attention_dynamics"] = personality["openness"] * 0.7
        if personality.get("neuroticism", 0.5) > 0.6:
            mech_scores["authority"] = max(mech_scores.get("authority", 0), personality["neuroticism"] * 0.8)
        if personality.get("agreeableness", 0.5) > 0.6:
            mech_scores["social_proof"] = max(mech_scores.get("social_proof", 0), personality["agreeableness"] * 0.8)
            mech_scores["reciprocity"] = personality["agreeableness"] * 0.7

        recommendations = []
        for mech, score in sorted(mech_scores.items(), key=lambda x: x[1], reverse=True)[:5]:
            recommendations.append({
                "mechanism": mech,
                "predicted_effectiveness": round(score, 2),
                "reasoning": f"Personality-derived: {mech.replace('_', ' ')} effectiveness",
            })
        return recommendations

    def _generate_host_guidance_from_personality(
        self,
        personality: Dict[str, float],
        show_name: str,
    ) -> Dict[str, Any]:
        """Generate host guidance from any personality dict."""
        if personality.get("extraversion", 0.5) > 0.65:
            style, tone, pacing = "energetic_conversational", "enthusiastic, social, story-driven", "dynamic with emphasis"
        elif personality.get("conscientiousness", 0.5) > 0.65:
            style, tone, pacing = "authoritative_detailed", "credible, evidence-based, structured", "measured and deliberate"
        elif personality.get("openness", 0.5) > 0.7:
            style, tone, pacing = "creative_narrative", "imaginative, thought-provoking, unique", "varied, storytelling rhythm"
        elif personality.get("agreeableness", 0.5) > 0.65:
            style, tone, pacing = "warm_personal", "friendly, relatable, empathetic", "gentle, conversational"
        else:
            style, tone, pacing = "balanced_professional", "clear, trustworthy, balanced", "moderate"

        return {
            "delivery_style": style,
            "recommended_tone": tone,
            "pacing": pacing,
            "key_principles": [
                "Lead with personal experience or connection to the product",
                f"Match the {show_name} audience's communication style",
                "Include a clear, personality-matched call to action",
                "Use language that resonates with the audience's values",
            ],
            "avoid": [
                "Generic scripted language that breaks show flow",
                "Pressure tactics if audience is anxiety-prone",
                "Overly formal tone if show is casual",
            ],
        }

    def _profile_from_static(
        self,
        show_id: str,
        show_name: str,
        genre: str,
        description: str,
        estimated_downloads: int,
    ) -> PodcastShowProfile:
        """FALLBACK: Profile from static GENRE_PERSONALITY_MAP."""
        genre_key = genre.lower().replace(" ", "_").replace("-", "_").replace("&", "")
        genre_data = GENRE_PERSONALITY_MAP.get(genre_key)

        if not genre_data:
            for key, data in GENRE_PERSONALITY_MAP.items():
                if key in genre_key or genre_key in key:
                    genre_data = data
                    break

        if not genre_data:
            genre_data = GENRE_PERSONALITY_MAP.get("education_learning", {})

        personality = {
            "openness": genre_data.get("openness", 0.5),
            "conscientiousness": genre_data.get("conscientiousness", 0.5),
            "extraversion": genre_data.get("extraversion", 0.5),
            "agreeableness": genre_data.get("agreeableness", 0.5),
            "neuroticism": genre_data.get("neuroticism", 0.5),
        }

        profile = PodcastShowProfile(
            show_id=show_id,
            show_name=show_name,
            genre=genre,
            audience_personality=personality,
            audience_constructs=genre_data.get("constructs", {}),
            audience_description=genre_data.get("audience_description", ""),
            estimated_downloads=estimated_downloads,
        )

        profile.mechanism_recommendations = self._recommend_mechanisms_static(personality)
        profile.host_read_guidance = self._generate_host_guidance_from_personality(
            personality, show_name
        )
        return profile

    def profile_shows_batch(
        self,
        shows: List[Dict[str, Any]],
    ) -> List[PodcastShowProfile]:
        """Profile multiple shows at once."""
        return [
            self.profile_show(
                show_id=s.get("id", f"show_{i}"),
                show_name=s.get("name", "Unknown"),
                genre=s.get("genre", "education"),
                description=s.get("description", ""),
                estimated_downloads=s.get("downloads", 50000),
            )
            for i, s in enumerate(shows)
        ]


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[PodcastIntelligenceEngine] = None


def get_podcast_intelligence_engine() -> PodcastIntelligenceEngine:
    global _engine
    if _engine is None:
        _engine = PodcastIntelligenceEngine()
    return _engine
