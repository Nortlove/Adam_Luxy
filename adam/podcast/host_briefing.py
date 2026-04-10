"""
Host-Read Ad Briefing Generator
==================================

Generates actionable briefings for podcast hosts to deliver
psychologically-optimized host-read ads.

Host-read ads are 50%+ more effective than pre-produced ads
(IAB Podcast Advertising Revenue Study). This engine maximizes
that advantage by providing hosts with:

1. Personality-matched talking points (not a script — hosts sound best unscripted)
2. Mechanism-specific language guidance
3. Audience-aware tone recommendations
4. Brand-audience connection points
5. Things to emphasize and things to avoid

The briefings are designed to feel natural in the show's context
while subtly activating the most effective psychological mechanisms.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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


@dataclass
class HostBriefing:
    """Actionable briefing for a podcast host."""
    show_name: str
    brand_name: str
    product_name: str = ""

    # Core messaging
    key_message: str = ""
    talking_points: List[str] = field(default_factory=list)
    personal_connection_angle: str = ""

    # Tone guidance
    delivery_style: str = ""
    emotional_tone: str = ""
    pacing_guidance: str = ""

    # Mechanism-specific language
    mechanism_language: Dict[str, List[str]] = field(default_factory=dict)

    # Call to action
    cta_suggestion: str = ""
    offer_code: str = ""
    landing_url: str = ""

    # Do's and don'ts
    emphasize: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)

    # Duration guidance
    suggested_duration_seconds: int = 60

    # Match quality context
    match_quality: float = 0.0
    match_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "show_name": self.show_name,
            "brand_name": self.brand_name,
            "product_name": self.product_name,
            "key_message": self.key_message,
            "talking_points": self.talking_points,
            "personal_connection_angle": self.personal_connection_angle,
            "delivery_style": self.delivery_style,
            "emotional_tone": self.emotional_tone,
            "pacing_guidance": self.pacing_guidance,
            "mechanism_language": self.mechanism_language,
            "cta_suggestion": self.cta_suggestion,
            "offer_code": self.offer_code,
            "landing_url": self.landing_url,
            "emphasize": self.emphasize,
            "avoid": self.avoid,
            "suggested_duration_seconds": self.suggested_duration_seconds,
            "match_quality": round(self.match_quality, 2),
            "match_reasoning": self.match_reasoning,
        }


class HostBriefingGenerator:
    """
    Generates psychological host-read ad briefings.

    PRIMARY PATH: Creative implications from graph edges for mechanism language
    FALLBACK: MECHANISM_LANGUAGE static dictionary
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

    # Mechanism → natural language guidance for hosts (FALLBACK)
    MECHANISM_LANGUAGE = {
        "social_proof": [
            "Mention how many people use/love this product",
            "Share listener feedback or reviews you've seen",
            "Reference community adoption ('everyone in my circle uses...')",
        ],
        "authority": [
            "Cite expert endorsements or research backing",
            "Mention certifications, awards, or industry recognition",
            "Position yourself as having tried and vetted the product",
        ],
        "identity_construction": [
            "Connect the product to the listener's self-image",
            "Frame it as 'the kind of thing someone like you appreciates'",
            "Link to aspirational identity ('for people who value quality')",
        ],
        "scarcity": [
            "Mention limited-time offers naturally",
            "Note exclusive listener deals with deadlines",
            "Express genuine urgency ('I wanted to tell you before it ends')",
        ],
        "commitment": [
            "Reference the listener's existing behavior or values",
            "Build on consistency ('you already care about X, so...')",
            "Suggest a small first step that leads to deeper engagement",
        ],
        "mimetic_desire": [
            "Share your personal experience with the product",
            "Mention other influencers/celebrities who use it",
            "Create 'insider' feeling ('I discovered this and had to share')",
        ],
        "reciprocity": [
            "Frame the product as giving something valuable first",
            "Mention free trials, samples, or no-obligation offers",
            "Emphasize the brand's generosity or customer-first approach",
        ],
        "anchoring": [
            "Compare the price to a familiar reference point",
            "Mention the regular price before the discounted price",
            "Frame the value relative to what listeners already spend",
        ],
    }

    def generate_briefing(
        self,
        show_profile: Any,  # PodcastShowProfile
        brand_name: str,
        product_name: str = "",
        category: str = "",
        match: Any = None,  # BrandShowMatch
        offer_code: str = "",
        landing_url: str = "",
    ) -> HostBriefing:
        """
        Generate a complete host-read ad briefing.

        PRIMARY: Creative implications from graph edges for mechanism language
        FALLBACK: MECHANISM_LANGUAGE static dictionary
        """
        show_name = getattr(show_profile, "show_name", "Your Show")
        host_guidance = getattr(show_profile, "host_read_guidance", {})
        audience_desc = getattr(show_profile, "audience_description", "")
        mechs = getattr(show_profile, "mechanism_recommendations", [])
        audience_constructs = getattr(show_profile, "audience_constructs", {})

        briefing = HostBriefing(
            show_name=show_name,
            brand_name=brand_name,
            product_name=product_name or brand_name,
            offer_code=offer_code,
            landing_url=landing_url,
        )

        # Delivery style from show profile
        briefing.delivery_style = host_guidance.get("delivery_style", "balanced")
        briefing.emotional_tone = host_guidance.get("recommended_tone", "natural")
        briefing.pacing_guidance = host_guidance.get("pacing", "moderate")

        # Key message
        if match:
            best_mech = getattr(match, "best_mechanism", "")
            briefing.key_message = self._generate_key_message(
                brand_name, product_name, best_mech, audience_desc
            )
            briefing.match_quality = getattr(match, "overall_match", 0)
            briefing.match_reasoning = getattr(match, "reasoning", "")

        # Talking points
        briefing.talking_points = self._generate_talking_points(
            brand_name, product_name, category, mechs
        )

        # Personal connection angle
        briefing.personal_connection_angle = (
            f"Share a genuine moment when {product_name or brand_name} "
            f"solved a problem or improved something in your life. "
            f"Your audience ({audience_desc}) values authenticity."
        )

        # Mechanism-specific language -- try graph first
        graph_language = self._get_graph_mechanism_language(audience_constructs, mechs)
        for mech_rec in mechs[:3]:
            mech = mech_rec.get("mechanism", "")
            if mech in graph_language:
                briefing.mechanism_language[mech] = graph_language[mech]
            elif mech in self.MECHANISM_LANGUAGE:
                briefing.mechanism_language[mech] = self.MECHANISM_LANGUAGE[mech]

        # CTA suggestion
        briefing.cta_suggestion = self._generate_cta(
            brand_name, mechs, offer_code, landing_url
        )

        # Emphasize / Avoid
        briefing.emphasize = self._generate_emphasis(mechs, host_guidance)
        briefing.avoid = host_guidance.get("avoid", [
            "Generic scripted language",
            "Hard-sell pressure tactics",
        ])

        # Duration: based on mechanism complexity
        n_mechs = len(briefing.mechanism_language)
        n_points = len(briefing.talking_points)
        briefing.suggested_duration_seconds = max(45, min(90, 30 + n_mechs * 10 + n_points * 5))

        return briefing

    def _get_graph_mechanism_language(
        self,
        audience_constructs: Dict[str, float],
        mechs: List[Dict],
    ) -> Dict[str, List[str]]:
        """
        Get mechanism language from graph creative implications.

        PRIMARY: Graph creative_implications per construct
        FALLBACK: empty (caller falls back to MECHANISM_LANGUAGE)
        """
        try:
            gs = self._get_graph_service()
            if gs is None or not audience_constructs:
                return {}

            construct_ids = list(audience_constructs.keys())[:5]
            creative_impls = _run_async(gs.get_creative_implications(construct_ids))

            if not creative_impls:
                return {}

            graph_language: Dict[str, List[str]] = {}
            for _cid, impl_data in creative_impls.items():
                # Extract language guidance from edge creative_implications
                edges = impl_data.get("edges", [])
                for edge in edges:
                    mech = edge.get("mechanism", "")
                    implications = edge.get("implications", {})
                    if mech and implications:
                        tips = []
                        if isinstance(implications, dict):
                            for key, val in implications.items():
                                if isinstance(val, str):
                                    tips.append(val)
                                elif isinstance(val, list):
                                    tips.extend(val[:3])
                        elif isinstance(implications, str):
                            tips.append(implications)

                        if tips:
                            graph_language.setdefault(mech, []).extend(tips)

            # Deduplicate
            for mech in graph_language:
                graph_language[mech] = list(dict.fromkeys(graph_language[mech]))[:3]

            return graph_language

        except Exception as e:
            logger.debug(f"Graph mechanism language failed: {e}")
            return {}

    def _generate_key_message(
        self,
        brand: str,
        product: str,
        mechanism: str,
        audience_desc: str,
    ) -> str:
        """Generate a key message based on the best mechanism."""
        product_name = product or brand
        if mechanism == "social_proof":
            return f"Share how {product_name} has become a go-to choice and why your listeners (who are {audience_desc}) will love it too."
        elif mechanism == "authority":
            return f"Position {product_name} as the expert-backed, trusted choice for your discerning audience."
        elif mechanism == "identity_construction":
            return f"Connect {product_name} to the aspirational identity your listeners identify with."
        elif mechanism == "scarcity":
            return f"Create natural urgency around the limited-time {product_name} offer for your listeners."
        elif mechanism == "commitment":
            return f"Build on your audience's existing values to show how {product_name} is a natural next step."
        return f"Share your genuine experience with {product_name} in a way that resonates with your audience."

    def _generate_talking_points(
        self,
        brand: str,
        product: str,
        category: str,
        mechs: List[Dict],
    ) -> List[str]:
        """Generate talking points."""
        points = [
            f"Open with a personal story connecting you to {product or brand}",
            f"Highlight what makes {product or brand} different from alternatives",
        ]
        if mechs:
            top_mech = mechs[0].get("mechanism", "")
            if "social_proof" in top_mech:
                points.append("Mention specific numbers, ratings, or community size")
            elif "authority" in top_mech:
                points.append("Reference expert opinions, research, or certifications")
            elif "identity" in top_mech:
                points.append("Connect the product to your listeners' identity and values")

        points.append("Close with a clear next step and your unique offer code")
        return points

    def _generate_cta(
        self,
        brand: str,
        mechs: List[Dict],
        offer_code: str,
        landing_url: str,
    ) -> str:
        """Generate CTA suggestion."""
        code_part = f" Use code {offer_code} for a special discount." if offer_code else ""
        url_part = f" Visit {landing_url}" if landing_url else f" Search for {brand}"
        return f"Head to {brand} and try it for yourself.{code_part}{url_part}"

    def _generate_emphasis(
        self,
        mechs: List[Dict],
        host_guidance: Dict,
    ) -> List[str]:
        """Generate things to emphasize."""
        emphasis = [
            "Authentic personal experience with the product",
            "Natural conversational delivery (not reading a script)",
        ]
        principles = host_guidance.get("key_principles", [])
        emphasis.extend(principles[:2])
        return emphasis


_generator: Optional[HostBriefingGenerator] = None


def get_host_briefing_generator() -> HostBriefingGenerator:
    global _generator
    if _generator is None:
        _generator = HostBriefingGenerator()
    return _generator
