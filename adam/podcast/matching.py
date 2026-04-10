"""
Show-to-Brand Psychological Matching Engine
==============================================

Matches brands/advertisers to podcast shows based on psychological
construct alignment rather than surface-level genre/demographic targeting.

The inferential advantage: instead of "true crime audiences buy insurance"
(correlational), this engine reasons:

    Show audience has high {prevention_focus, need_for_closure} →
    Brand messaging activates {authority, trust} mechanisms →
    Match quality = construct overlap + mechanism compatibility

This produces matches that:
1. Transfer to new shows (zero-shot: new show in same genre gets same quality)
2. Are explainable ("here's WHY this brand fits this show")
3. Optimize for RPM (revenue per mille — the key Audioboom metric)
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


@dataclass
class BrandShowMatch:
    """A match between a brand and a podcast show."""
    show_id: str
    show_name: str
    brand_name: str
    
    # Match quality (0-1)
    overall_match: float = 0.0
    construct_overlap: float = 0.0  # How similar are audience/brand constructs
    mechanism_compatibility: float = 0.0  # Do the recommended mechanisms align
    
    # Matched constructs (shared between brand and audience)
    shared_constructs: List[str] = field(default_factory=list)
    
    # Recommended mechanism for this match
    best_mechanism: str = ""
    mechanism_confidence: float = 0.0
    
    # RPM projection (revenue per 1000 downloads)
    projected_rpm: float = 0.0
    
    # Reasoning chain
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "show_id": self.show_id,
            "show_name": self.show_name,
            "brand_name": self.brand_name,
            "overall_match": round(self.overall_match, 3),
            "construct_overlap": round(self.construct_overlap, 3),
            "mechanism_compatibility": round(self.mechanism_compatibility, 3),
            "shared_constructs": self.shared_constructs,
            "best_mechanism": self.best_mechanism,
            "projected_rpm": round(self.projected_rpm, 2),
            "reasoning": self.reasoning,
        }


class ShowBrandMatcher:
    """
    Matches brands to podcast shows using psychological construct alignment.

    PRIMARY PATH: Neo4j graph for brand construct inference, mechanism
                  compatibility, and learned RPM/weights from Thompson posteriors
    FALLBACK: Static dictionaries
    """

    # Average podcast RPMs by genre (IAB 2024-2025 estimates) -- FALLBACK
    GENRE_BASE_RPM = {
        "true_crime": 22.0,
        "comedy": 18.0,
        "news_politics": 20.0,
        "business": 25.0,
        "health_wellness": 20.0,
        "technology": 22.0,
        "sports": 18.0,
        "education_learning": 20.0,
        "parenting_family": 22.0,
        "arts_culture": 16.0,
    }

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

    def match_brand_to_shows(
        self,
        brand_name: str,
        brand_category: str,
        brand_constructs: Optional[Dict[str, float]] = None,
        show_profiles: List[Any] = None,
    ) -> List[BrandShowMatch]:
        """
        Match a brand to podcast shows ranked by psychological fit.
        """
        if not show_profiles:
            return []

        # Infer brand constructs from category if not provided
        if not brand_constructs:
            brand_constructs = self._infer_brand_constructs(brand_category)

        # Get graph-backed mechanism effectiveness for this brand category
        graph_mech_eff = {}
        try:
            gs = self._get_graph_service()
            if gs:
                graph_mech_eff = _run_async(
                    gs.get_mechanism_effectiveness(brand_category, list(brand_constructs.keys()))
                )
        except Exception:
            pass

        matches = []
        for show in show_profiles:
            match = self._compute_match(
                show=show,
                brand_name=brand_name,
                brand_constructs=brand_constructs,
                graph_mech_eff=graph_mech_eff,
            )
            matches.append(match)

        # Sort by overall match quality
        matches.sort(key=lambda m: m.overall_match, reverse=True)
        return matches

    def _compute_match(
        self,
        show: Any,
        brand_name: str,
        brand_constructs: Dict[str, float],
        graph_mech_eff: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> BrandShowMatch:
        """Compute match quality between a brand and a show."""
        show_id = getattr(show, "show_id", "unknown")
        show_name = getattr(show, "show_name", "Unknown Show")
        show_constructs = getattr(show, "audience_constructs", {})
        show_personality = getattr(show, "audience_personality", {})
        genre = getattr(show, "genre", "").lower().replace(" ", "_")

        # 1. Construct overlap: cosine-like similarity
        shared = []
        overlap_sum = 0.0
        total_weight = 0.0
        for construct, brand_level in brand_constructs.items():
            if construct in show_constructs:
                show_level = show_constructs[construct]
                match_quality = 1.0 - abs(brand_level - show_level)
                overlap_sum += match_quality * brand_level
                total_weight += brand_level
                if match_quality > 0.6:
                    shared.append(construct)

        construct_overlap = overlap_sum / total_weight if total_weight > 0 else 0.3

        # 2. Mechanism compatibility
        show_mechs = {
            m.get("mechanism", ""): m.get("predicted_effectiveness", 0)
            for m in getattr(show, "mechanism_recommendations", [])
        }

        # Use graph mechanism effectiveness if available, else infer from constructs
        if graph_mech_eff:
            brand_mechs = {
                m: d.get("score", 0.5)
                for m, d in graph_mech_eff.items()
            }
            if not brand_mechs:
                brand_mechs = self._infer_brand_mechanisms(brand_constructs)
        else:
            brand_mechs = self._infer_brand_mechanisms(brand_constructs)

        mech_compat = 0.0
        best_mech = ""
        best_mech_score = 0.0
        for mech, brand_need in brand_mechs.items():
            if mech in show_mechs:
                compat = min(brand_need, show_mechs[mech])
                mech_compat += compat
                if compat > best_mech_score:
                    best_mech = mech
                    best_mech_score = compat

        mechanism_compatibility = min(1.0, mech_compat / max(len(brand_mechs), 1))

        # 3. Overall match (weighted blend)
        # Weights could be learned from Thompson posteriors; use defaults for now
        overall = 0.55 * construct_overlap + 0.45 * mechanism_compatibility

        # 4. RPM projection
        base_rpm = self.GENRE_BASE_RPM.get(genre, 18.0)
        rpm_lift = 1.0 + overall * 0.5
        projected_rpm = base_rpm * rpm_lift

        # 5. Reasoning
        reasoning = (
            f"Brand '{brand_name}' matches '{show_name}' "
            f"(construct overlap: {construct_overlap:.0%}, "
            f"mechanism compatibility: {mechanism_compatibility:.0%}). "
            f"Shared constructs: {', '.join(shared[:3]) if shared else 'indirect match'}. "
            f"Best mechanism: {best_mech.replace('_', ' ') if best_mech else 'general'}."
        )

        return BrandShowMatch(
            show_id=show_id,
            show_name=show_name,
            brand_name=brand_name,
            overall_match=overall,
            construct_overlap=construct_overlap,
            mechanism_compatibility=mechanism_compatibility,
            shared_constructs=shared[:5],
            best_mechanism=best_mech,
            mechanism_confidence=best_mech_score,
            projected_rpm=projected_rpm,
            reasoning=reasoning,
        )

    def _infer_brand_constructs(self, category: str) -> Dict[str, float]:
        """
        Infer brand psychological constructs from category.

        PRIMARY: Graph category constructs
        FALLBACK: Static dictionary
        """
        # Try graph-backed construct inference
        try:
            gs = self._get_graph_service()
            if gs:
                graph_constructs = _run_async(
                    gs.get_category_constructs(category)
                )
                if graph_constructs:
                    result = {}
                    for gc in graph_constructs[:7]:
                        cid = gc["construct_id"]
                        relevance = gc.get("relevance", 0.5)
                        result[cid] = round(0.5 + relevance * 0.3, 2)
                    if result:
                        return result
        except Exception:
            pass

        # FALLBACK: static dictionary
        category_constructs = {
            "finance": {"prevention_focus": 0.8, "trust_propensity": 0.7, "risk_sensitivity": 0.75},
            "insurance": {"prevention_focus": 0.85, "risk_aversion": 0.8, "trust_propensity": 0.7},
            "technology": {"openness": 0.75, "need_for_cognition": 0.7, "curiosity": 0.7},
            "fashion": {"identity_salience": 0.8, "social_proof_susceptibility": 0.7, "status_sensitivity": 0.6},
            "health": {"prevention_focus": 0.75, "conscientiousness": 0.7, "trust_propensity": 0.65},
            "education": {"need_for_cognition": 0.8, "curiosity": 0.75, "cognitive_engagement": 0.7},
            "food": {"agreeableness": 0.6, "social_proof_susceptibility": 0.55, "arousal_seeking": 0.5},
            "travel": {"openness": 0.75, "sensation_seeking": 0.7, "approach_motivation": 0.65},
            "automotive": {"status_sensitivity": 0.7, "identity_salience": 0.65, "prevention_focus": 0.6},
            "mattress": {"prevention_focus": 0.7, "trust_propensity": 0.65, "conscientiousness": 0.6},
            "sleep": {"prevention_focus": 0.7, "trust_propensity": 0.65, "conscientiousness": 0.6},
            "fitness": {"approach_motivation": 0.75, "conscientiousness": 0.7, "identity_salience": 0.6},
            "athletic": {"approach_motivation": 0.75, "identity_salience": 0.7, "sensation_seeking": 0.6},
            "meditation": {"openness": 0.75, "conscientiousness": 0.6, "prevention_focus": 0.6},
            "wellness": {"prevention_focus": 0.7, "openness": 0.65, "trust_propensity": 0.6},
            "software": {"need_for_cognition": 0.75, "analytical_processing": 0.7, "openness": 0.6},
            "saas": {"need_for_cognition": 0.75, "analytical_processing": 0.7, "openness": 0.6},
        }
        cat_lower = category.lower()
        for key, constructs in category_constructs.items():
            if key in cat_lower:
                return constructs
        return {"openness": 0.5, "conscientiousness": 0.5}

    def _infer_brand_mechanisms(self, constructs: Dict[str, float]) -> Dict[str, float]:
        """
        Infer which mechanisms a brand needs from its constructs.

        PRIMARY: Graph SUSCEPTIBLE_TO edges for each construct
        FALLBACK: Static threshold rules
        """
        # Try graph-backed mechanism inference
        try:
            gs = self._get_graph_service()
            if gs:
                all_mechs: Dict[str, float] = {}
                for cid in list(constructs.keys())[:5]:
                    mech_eff = _run_async(
                        gs.get_mechanism_effectiveness("general", [cid])
                    )
                    for mech, data in mech_eff.items():
                        score = data.get("score", 0.5)
                        if mech in all_mechs:
                            all_mechs[mech] = max(all_mechs[mech], score)
                        else:
                            all_mechs[mech] = score
                if all_mechs:
                    return dict(sorted(all_mechs.items(), key=lambda x: x[1], reverse=True)[:6])
        except Exception:
            pass

        # FALLBACK: static rules
        mechs = {}
        if constructs.get("prevention_focus", 0) > 0.6:
            mechs["authority"] = 0.8
            mechs["social_proof"] = 0.6
        if constructs.get("identity_salience", 0) > 0.6:
            mechs["identity_construction"] = 0.8
            mechs["mimetic_desire"] = 0.6
        if constructs.get("need_for_cognition", 0) > 0.6:
            mechs["authority"] = max(mechs.get("authority", 0), 0.7)
            mechs["anchoring"] = 0.6
        if constructs.get("social_proof_susceptibility", 0) > 0.6:
            mechs["social_proof"] = max(mechs.get("social_proof", 0), 0.75)
        if constructs.get("arousal_seeking", 0) > 0.6:
            mechs["scarcity"] = 0.7
            mechs["attention_dynamics"] = 0.6
        if not mechs:
            mechs = {"social_proof": 0.5, "authority": 0.4}
        return mechs


_matcher: Optional[ShowBrandMatcher] = None


def get_show_brand_matcher() -> ShowBrandMatcher:
    global _matcher
    if _matcher is None:
        _matcher = ShowBrandMatcher()
    return _matcher
