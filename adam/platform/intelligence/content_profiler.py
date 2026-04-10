"""
ContentProfiler — runs NDF profiling on content items for any Blueprint connector.

Wraps the UnifiedIntelligenceService to provide:
  - 7+1 NDF dimension extraction from text
  - Mechanism relevance scoring
  - Construct-level profiling
  - Confidence estimation

This is the component that connectors call via set_profiler(profiler)
to get the full 441-construct intelligence applied to their content.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NDF_DIMENSIONS = [
    "approach_avoidance",
    "temporal_horizon",
    "social_calibration",
    "uncertainty_tolerance",
    "status_sensitivity",
    "cognitive_engagement",
    "arousal_seeking",
    "cognitive_velocity",
]

MECHANISM_KEYWORDS = {
    "social_proof": ["review", "popular", "bestsell", "rated", "recommend", "people", "everyone", "million"],
    "scarcity": ["limited", "exclusive", "only", "last", "hurry", "rare", "scarce", "running out"],
    "authority": ["expert", "doctor", "scientist", "research", "study", "proven", "certified", "award"],
    "reciprocity": ["free", "bonus", "gift", "complimentary", "included", "extra", "sample"],
    "commitment_consistency": ["subscribe", "join", "member", "commit", "pledge", "loyal"],
    "liking": ["love", "favorite", "beautiful", "amazing", "gorgeous", "enjoy", "fun"],
    "unity": ["family", "community", "together", "belong", "tribe", "us", "our"],
    "anchoring": ["was $", "save", "discount", "% off", "compare", "value", "deal"],
    "loss_aversion": ["miss", "lose", "risk", "protect", "safeguard", "don't let", "before it's gone"],
}

EMOTION_KEYWORDS = {
    "excitement": ["exciting", "thrill", "amazing", "incredible", "wow", "breakthrough"],
    "trust": ["trust", "reliable", "safe", "secure", "guarantee", "proven", "tested"],
    "fear": ["risk", "danger", "warning", "protect", "threat", "worry"],
    "joy": ["happy", "deligh", "enjoy", "love", "wonderful", "great"],
    "curiosity": ["discover", "learn", "explore", "find out", "secret", "reveal", "new"],
    "nostalgia": ["remember", "classic", "tradition", "heritage", "timeless", "retro"],
    "urgency": ["now", "today", "immediately", "hurry", "quick", "fast", "instant"],
}


class ContentProfiler:
    """
    NDF profiling engine for Blueprint connectors.

    Wraps ADAM's UnifiedIntelligenceService for graph-based profiling
    with fallback to heuristic analysis when the graph is unavailable.
    """

    def __init__(self, unified_intelligence=None, graph_intelligence=None, neo4j_driver=None):
        self._unified = unified_intelligence
        self._graph = graph_intelligence
        self._neo4j = neo4j_driver

    async def profile(self, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Profile content and return NDF dimensions, segments, constructs, and mechanisms.
        This is the method that connectors call via set_profiler(profiler).
        """
        text = f"{title} {body}".strip()
        metadata = metadata or {}

        ndf = await self._extract_ndf(text, metadata)
        mechanisms = self._score_mechanisms(text)
        constructs = self._extract_constructs(text, ndf)
        segments = self._build_segments(ndf, mechanisms)
        confidence = self._compute_confidence(text, ndf, mechanisms)

        if self._unified:
            try:
                category = metadata.get("category", "All_Beauty")
                intel = self._unified.get_intelligence(category=category)
                if intel and "layer1" in intel:
                    layer1 = intel["layer1"]
                    if "ndf_profile" in layer1:
                        for dim, val in layer1["ndf_profile"].items():
                            if dim in ndf:
                                ndf[dim] = 0.6 * ndf[dim] + 0.4 * val
                    confidence = min(1.0, confidence + 0.2)
            except Exception as e:
                logger.debug("Graph enrichment unavailable: %s", e)

        return {
            "ndf_profile": ndf,
            "segments": segments,
            "constructs": constructs,
            "mechanisms": [m["mechanism"] for m in mechanisms[:5]],
            "mechanism_scores": mechanisms,
            "confidence": confidence,
            "emotions": self._detect_emotions(text),
        }

    async def _extract_ndf(self, text: str, metadata: Dict[str, Any]) -> Dict[str, float]:
        """Extract 7+1 NDF dimensions from text content."""
        lower = text.lower()
        word_count = len(lower.split())

        gain_words = sum(1 for w in ["benefit", "gain", "reward", "positive", "opportunity", "advantage", "improve"] if w in lower)
        loss_words = sum(1 for w in ["risk", "avoid", "prevent", "protect", "danger", "loss", "miss"] if w in lower)
        total_valence = gain_words + loss_words + 1
        approach_avoidance = 0.5 + 0.3 * (gain_words - loss_words) / total_valence

        future_words = sum(1 for w in ["future", "long-term", "plan", "invest", "tomorrow", "years"] if w in lower)
        present_words = sum(1 for w in ["now", "today", "instant", "immediate", "quick"] if w in lower)
        total_temporal = future_words + present_words + 1
        temporal_horizon = 0.5 + 0.3 * (future_words - present_words) / total_temporal

        social_words = sum(1 for w in ["review", "people", "everyone", "community", "social", "popular", "recommend"] if w in lower)
        social_calibration = min(1.0, 0.3 + 0.1 * social_words)

        uncertain_words = sum(1 for w in ["maybe", "might", "could", "possibly", "uncertain", "depends"] if w in lower)
        certain_words = sum(1 for w in ["definitely", "guarantee", "proven", "certain", "always", "100%"] if w in lower)
        total_cert = uncertain_words + certain_words + 1
        uncertainty_tolerance = 0.5 + 0.2 * (uncertain_words - certain_words) / total_cert

        status_words = sum(1 for w in ["premium", "luxury", "exclusive", "elite", "prestigious", "vip", "high-end"] if w in lower)
        status_sensitivity = min(1.0, 0.3 + 0.15 * status_words)

        cognitive_engagement = min(1.0, 0.2 + 0.003 * word_count)

        arousal_words = sum(1 for w in ["exciting", "thrill", "amazing", "incredible", "breakthrough", "revolutionary"] if w in lower)
        calm_words = sum(1 for w in ["calm", "peaceful", "gentle", "soothing", "relax", "quiet"] if w in lower)
        total_arousal = arousal_words + calm_words + 1
        arousal_seeking = 0.5 + 0.2 * (arousal_words - calm_words) / total_arousal

        sentence_count = max(1, len(re.split(r'[.!?]+', text)))
        avg_sentence_len = word_count / sentence_count
        cognitive_velocity = min(1.0, max(0.0, 0.3 + 0.02 * avg_sentence_len))

        return {
            "approach_avoidance": round(max(0.0, min(1.0, approach_avoidance)), 4),
            "temporal_horizon": round(max(0.0, min(1.0, temporal_horizon)), 4),
            "social_calibration": round(max(0.0, min(1.0, social_calibration)), 4),
            "uncertainty_tolerance": round(max(0.0, min(1.0, uncertainty_tolerance)), 4),
            "status_sensitivity": round(max(0.0, min(1.0, status_sensitivity)), 4),
            "cognitive_engagement": round(max(0.0, min(1.0, cognitive_engagement)), 4),
            "arousal_seeking": round(max(0.0, min(1.0, arousal_seeking)), 4),
            "cognitive_velocity": round(max(0.0, min(1.0, cognitive_velocity)), 4),
        }

    def _score_mechanisms(self, text: str) -> List[Dict[str, Any]]:
        lower = text.lower()
        scores = []
        for mechanism, keywords in MECHANISM_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                score = min(1.0, 0.2 + 0.15 * hits)
                scores.append({
                    "mechanism": mechanism,
                    "score": round(score, 3),
                    "keyword_hits": hits,
                })
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores

    def _extract_constructs(self, text: str, ndf: Dict[str, float]) -> Dict[str, float]:
        constructs = {}
        if ndf.get("approach_avoidance", 0.5) > 0.6:
            constructs["promotion_focus"] = ndf["approach_avoidance"]
        elif ndf.get("approach_avoidance", 0.5) < 0.4:
            constructs["prevention_focus"] = 1.0 - ndf["approach_avoidance"]

        if ndf.get("temporal_horizon", 0.5) > 0.6:
            constructs["future_orientation"] = ndf["temporal_horizon"]
        elif ndf.get("temporal_horizon", 0.5) < 0.4:
            constructs["present_orientation"] = 1.0 - ndf["temporal_horizon"]

        if ndf.get("social_calibration", 0.5) > 0.6:
            constructs["social_proof_susceptibility"] = ndf["social_calibration"]
        if ndf.get("status_sensitivity", 0.5) > 0.6:
            constructs["status_seeking"] = ndf["status_sensitivity"]
        if ndf.get("cognitive_engagement", 0.5) > 0.6:
            constructs["need_for_cognition"] = ndf["cognitive_engagement"]
        if ndf.get("arousal_seeking", 0.5) > 0.6:
            constructs["sensation_seeking"] = ndf["arousal_seeking"]

        return constructs

    def _build_segments(self, ndf: Dict[str, float], mechanisms: List[Dict]) -> List[str]:
        segments = []
        aa = ndf.get("approach_avoidance", 0.5)
        if aa > 0.6:
            segments.append("promotion_motivated")
        elif aa < 0.4:
            segments.append("prevention_motivated")

        th = ndf.get("temporal_horizon", 0.5)
        if th > 0.6:
            segments.append("future_oriented")
        elif th < 0.4:
            segments.append("present_oriented")

        if ndf.get("social_calibration", 0.5) > 0.6:
            segments.append("socially_influenced")
        if ndf.get("status_sensitivity", 0.5) > 0.6:
            segments.append("status_conscious")
        if ndf.get("cognitive_engagement", 0.5) > 0.7:
            segments.append("high_elaboration")
        elif ndf.get("cognitive_engagement", 0.5) < 0.3:
            segments.append("low_elaboration")
        if ndf.get("arousal_seeking", 0.5) > 0.6:
            segments.append("novelty_seeker")

        for m in mechanisms[:3]:
            segments.append(f"mechanism_{m['mechanism']}")

        return segments

    def _detect_emotions(self, text: str) -> Dict[str, float]:
        lower = text.lower()
        emotions = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                emotions[emotion] = min(1.0, 0.2 + 0.2 * hits)
        return emotions

    def _compute_confidence(self, text: str, ndf: Dict[str, float], mechanisms: List[Dict]) -> float:
        word_count = len(text.split())
        text_conf = min(0.4, 0.01 * word_count)
        mechanism_conf = min(0.3, 0.1 * len(mechanisms))
        ndf_conf = 0.3 if any(abs(v - 0.5) > 0.1 for v in ndf.values()) else 0.1
        return round(min(1.0, text_conf + mechanism_conf + ndf_conf), 3)
