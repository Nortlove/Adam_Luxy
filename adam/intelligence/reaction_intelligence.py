"""
Audience Reaction Intelligence
================================

Comments, reviews, and social media posts about content reveal the
ACTUAL psychological state the content creates — not what we predict
from text extraction, but what real people demonstrably experience.

Reaction data CONFIRMS or CORRECTS the content-based edge profile:
- "This article is terrifying" → confirms anxiety prediction
- "Clickbait, nothing to worry about" → corrects false anxiety

Key insight: reaction language reveals STATE (how people feel),
not FRAMING (how content presents). Different word lists needed.

Uses the full 20 edge dimensions for bilateral cascade compatibility.

Storage:
- informativ:reaction:web:{url_pattern} — 24h TTL
- informativ:reaction:ctv:{content_id} — 48h TTL
"""

from __future__ import annotations

import json
import logging
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


# ============================================================================
# Audience Reaction Profile
# ============================================================================

@dataclass
class AudienceReactionProfile:
    """Psychological intelligence from audience reactions to content."""
    reaction_edge_profile: Dict[str, float] = field(default_factory=dict)
    content_edge_profile: Dict[str, float] = field(default_factory=dict)
    confirmation_scores: Dict[str, float] = field(default_factory=dict)
    correction_vector: Dict[str, float] = field(default_factory=dict)
    overall_agreement: float = 0.5
    reaction_count: int = 0
    reaction_sources: List[str] = field(default_factory=list)
    dominant_reaction_emotion: str = ""
    reaction_intensity: float = 0.0

    def to_redis_dict(self) -> Dict[str, Any]:
        return {
            "reaction_edge_profile": json.dumps(self.reaction_edge_profile),
            "content_edge_profile": json.dumps(self.content_edge_profile),
            "confirmation_scores": json.dumps(self.confirmation_scores),
            "correction_vector": json.dumps(self.correction_vector),
            "overall_agreement": self.overall_agreement,
            "reaction_count": self.reaction_count,
            "reaction_sources": json.dumps(self.reaction_sources),
            "dominant_reaction_emotion": self.dominant_reaction_emotion,
            "reaction_intensity": self.reaction_intensity,
        }

    @classmethod
    def from_redis_dict(cls, data: Dict[str, Any]) -> "AudienceReactionProfile":
        def _jl(val, default):
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return default
            return val if val is not None else default

        return cls(
            reaction_edge_profile=_jl(data.get("reaction_edge_profile"), {}),
            content_edge_profile=_jl(data.get("content_edge_profile"), {}),
            confirmation_scores=_jl(data.get("confirmation_scores"), {}),
            correction_vector=_jl(data.get("correction_vector"), {}),
            overall_agreement=float(data.get("overall_agreement", 0.5)),
            reaction_count=int(data.get("reaction_count", 0)),
            reaction_sources=_jl(data.get("reaction_sources"), []),
            dominant_reaction_emotion=data.get("dominant_reaction_emotion", ""),
            reaction_intensity=float(data.get("reaction_intensity", 0)),
        )


# ============================================================================
# Reaction-Specific Word Lists
# ============================================================================
# These differ from content word lists because reactions express STATE
# (how people feel) rather than FRAMING (how content presents).

_REACTION_ANXIETY = frozenset([
    "scary", "terrifying", "worried", "concerned", "frightened",
    "alarming", "anxious", "nervous", "afraid", "disturbing",
    "unsettling", "chilling", "what do we do", "keeps me up",
    "can't sleep", "losing sleep", "nightmare", "dread",
])

_REACTION_EXCITEMENT = frozenset([
    "amazing", "inspiring", "can't wait", "love this", "incredible",
    "excited", "pumped", "hyped", "brilliant", "mind-blown",
    "game changer", "blew my mind", "best thing", "so good",
    "obsessed", "fantastic", "phenomenal",
])

_REACTION_OUTRAGE = frozenset([
    "unacceptable", "furious", "disgusting", "how dare", "outraged",
    "infuriating", "enraged", "livid", "appalling", "shameful",
    "corrupt", "criminal", "scandal", "bs", "garbage", "pathetic",
    "embarrassing", "disgraceful",
])

_REACTION_SADNESS = frozenset([
    "heartbreaking", "devastating", "so sad", "crying", "tears",
    "tragic", "painful", "gutted", "mourning", "loss",
    "depressing", "hopeless", "bleak",
])

_REACTION_VALIDATION = frozenset([
    "same", "this", "agree", "exactly", "everyone should",
    "shared this", "so true", "nailed it", "spot on", "preach",
    "couldn't agree more", "needed to hear", "facts",
])

_REACTION_SKEPTICISM = frozenset([
    "clickbait", "misleading", "fake", "doubt", "skeptical",
    "propaganda", "biased", "exaggerated", "overblown", "fearmongering",
    "nothing to worry", "calm down", "nonsense", "bs",
])

_REACTION_EXPERTISE_SEEKING = frozenset([
    "does anyone know", "is this true", "sources", "can someone explain",
    "eli5", "help me understand", "where can I find", "any experts",
    "what should I do", "recommendations", "what's the best",
])

_REACTION_ACTION_INTENT = frozenset([
    "just bought", "signing up", "switching to", "going to",
    "ordered", "subscribed", "downloading", "trying this",
    "booking", "applying", "investing in", "started using",
])


# ============================================================================
# Reaction Edge Profile Extraction
# ============================================================================

def extract_reaction_edge_profile(reactions_text: str) -> Dict[str, float]:
    """Extract 20 edge dimensions from audience reactions.

    Maps reaction emotions to edge dimensions:
    - Anxiety → low regulatory_fit, high loss_aversion_intensity,
      high persuasion_susceptibility, low autonomy_reactance
    - Excitement → high emotional_resonance, high regulatory_fit (approach),
      low temporal_discounting (present)
    - Outrage → high emotional_resonance, low cooperative_framing_fit,
      high social_proof_sensitivity (tribal)
    - Sadness → low regulatory_fit, low emotional_resonance (drained),
      high narrative_transport
    - Validation → high social_proof_sensitivity, high mimetic_desire,
      high cooperative_framing_fit
    - Skepticism → high autonomy_reactance, high information_seeking,
      high cognitive_load_tolerance, high decision_entropy
    - Expertise-seeking → high information_seeking, high cognitive_load_tolerance,
      high persuasion_susceptibility (seeking guidance)
    - Action intent → low temporal_discounting (present-focused),
      low decision_entropy (decisive), high regulatory_fit (approach)
    """
    text_lower = reactions_text.lower()
    word_count = len(text_lower.split())
    if word_count < 10:
        return {dim: 0.5 for dim in EDGE_DIMENSIONS}

    # Count reaction markers
    def _count(words):
        return sum(1 for w in words if w in text_lower)

    anxiety = _count(_REACTION_ANXIETY)
    excitement = _count(_REACTION_EXCITEMENT)
    outrage = _count(_REACTION_OUTRAGE)
    sadness = _count(_REACTION_SADNESS)
    validation = _count(_REACTION_VALIDATION)
    skepticism = _count(_REACTION_SKEPTICISM)
    expertise = _count(_REACTION_EXPERTISE_SEEKING)
    action = _count(_REACTION_ACTION_INTENT)

    total = max(1, anxiety + excitement + outrage + sadness + validation +
                skepticism + expertise + action)

    edge = {}

    # ── regulatory_fit: approach vs prevention ──
    # excitement/action/validation → approach (high), anxiety/sadness/outrage → prevention (low)
    positive_signals = excitement + action + validation
    negative_signals = anxiety + outrage + sadness
    aa_total = max(1, positive_signals + negative_signals)
    edge["regulatory_fit"] = round(0.5 + 0.5 * (positive_signals - negative_signals) / aa_total, 4)

    # ── construal_fit: abstract vs concrete ──
    # expertise/validation = abstract (future, big-picture), action/outrage = concrete (present, reactive)
    abstract = expertise + validation
    concrete = action + outrage + anxiety
    cf_total = max(1, abstract + concrete)
    edge["construal_fit"] = round(abstract / cf_total, 4)

    # ── personality_alignment: how broad is the appeal ──
    # Validation/excitement = broad, skepticism = narrow (contrarian)
    broad = validation + excitement
    narrow = skepticism + outrage
    pa_total = max(1, broad + narrow)
    edge["personality_alignment"] = round(broad / pa_total, 4)

    # ── emotional_resonance: overall emotional activation ──
    # High for excitement, outrage, anxiety; low for skepticism, expertise
    high_emo = excitement + outrage + anxiety + sadness
    low_emo = skepticism + expertise
    er_total = max(1, high_emo + low_emo)
    edge["emotional_resonance"] = round(high_emo / er_total, 4)

    # ── value_alignment: moral/value congruence in reactions ──
    # Validation/outrage = value-driven, excitement/action = desire-driven
    value_driven = validation + outrage
    desire_driven = excitement + action
    va_total = max(1, value_driven + desire_driven)
    edge["value_alignment"] = round(value_driven / va_total, 4)

    # ── evolutionary_motive: threat/status/belonging activation ──
    # Anxiety/outrage = threat, validation = belonging, excitement = status
    threat_signals = anxiety + outrage
    belonging = validation
    evo_total = max(1, threat_signals + belonging + excitement)
    edge["evolutionary_motive"] = round((threat_signals + belonging * 0.5 + excitement * 0.3) / evo_total, 4)

    # ── linguistic_style: formal vs informal ──
    # Expertise = formal, outrage/excitement = informal
    formal = expertise + skepticism
    informal = outrage + excitement
    ls_total = max(1, formal + informal)
    edge["linguistic_style"] = round(formal / ls_total, 4)

    # ── persuasion_susceptibility: how open to influence ──
    # Anxiety/expertise = high (seeking guidance), skepticism = low (resistant)
    susceptible = anxiety + expertise + sadness
    resistant = skepticism + validation  # Validation = already decided
    ps_total = max(1, susceptible + resistant)
    edge["persuasion_susceptibility"] = round(susceptible / ps_total, 4)

    # ── cognitive_load_tolerance: remaining capacity ──
    # Skepticism/expertise = high tolerance (analytical), outrage/excitement = low (emotional)
    analytical = expertise + skepticism
    emotional = outrage + excitement + anxiety + sadness
    ct_total = max(1, analytical + emotional)
    edge["cognitive_load_tolerance"] = round(analytical / ct_total, 4)

    # ── narrative_transport: immersion depth ──
    # Sadness/excitement = transported, skepticism = detached
    transported = sadness + excitement + anxiety
    detached = skepticism
    nt_total = max(1, transported + detached)
    edge["narrative_transport"] = round(transported / nt_total, 4)

    # ── social_proof_sensitivity: tribal/social orientation ──
    # Validation/outrage = highly social, skepticism/expertise = individual
    social = validation + outrage
    individual = skepticism + expertise
    sp_total = max(1, social + individual)
    edge["social_proof_sensitivity"] = round(social / sp_total, 4)

    # ── loss_aversion_intensity: threat/loss salience ──
    # Anxiety = maximum loss salience, excitement = minimal
    loss_salient = anxiety + sadness + outrage
    gain_salient = excitement + action + validation
    la_total = max(1, loss_salient + gain_salient)
    edge["loss_aversion_intensity"] = round(loss_salient / la_total, 4)

    # ── temporal_discounting: present vs future orientation ──
    # Action/outrage = present (impulsive), expertise/validation = future (deliberate)
    present = action + outrage + anxiety
    future = expertise + validation
    td_total = max(1, present + future)
    edge["temporal_discounting"] = round(present / td_total, 4)

    # ── brand_relationship_depth: loyalty/commitment priming ──
    # Action intent = commitment, validation = loyalty, skepticism = churn risk
    committed = action + validation
    uncommitted = skepticism + outrage
    br_total = max(1, committed + uncommitted)
    edge["brand_relationship_depth"] = round(committed / br_total, 4)

    # ── autonomy_reactance: resistance to persuasion ──
    # Skepticism = high reactance, validation/excitement = low (open)
    reactive = skepticism + outrage
    open_signals = validation + excitement + action
    ar_total = max(1, reactive + open_signals)
    edge["autonomy_reactance"] = round(reactive / ar_total, 4)

    # ── information_seeking: desire for more info ──
    # Expertise = maximum, action = minimum (already decided)
    seeking = expertise + skepticism
    decided = action + validation + excitement
    is_total = max(1, seeking + decided)
    edge["information_seeking"] = round(seeking / is_total, 4)

    # ── mimetic_desire: wanting what others want ──
    # Validation = tribal agreement, action = following trend
    mimetic = validation + action + excitement
    independent = skepticism + expertise
    md_total = max(1, mimetic + independent)
    edge["mimetic_desire"] = round(mimetic / md_total, 4)

    # ── interoceptive_awareness: body-state awareness ──
    # Anxiety/excitement = felt physically, expertise = cerebral
    somatic = anxiety + excitement + outrage + sadness
    cerebral = expertise + skepticism
    ia_total = max(1, somatic + cerebral)
    edge["interoceptive_awareness"] = round(somatic / ia_total, 4)

    # ── cooperative_framing_fit: us-vs-them orientation ──
    # Validation = cooperative, outrage = adversarial
    cooperative = validation + action
    adversarial = outrage + skepticism
    co_total = max(1, cooperative + adversarial)
    edge["cooperative_framing_fit"] = round(cooperative / co_total, 4)

    # ── decision_entropy: uncertainty in decision ──
    # Skepticism/expertise = high entropy (undecided), action/validation = low (decided)
    undecided = skepticism + expertise + anxiety
    decided_signals = action + validation + excitement
    de_total = max(1, undecided + decided_signals)
    edge["decision_entropy"] = round(undecided / de_total, 4)

    return edge


def detect_dominant_emotion(reactions_text: str) -> Tuple[str, float]:
    """Detect the dominant reaction emotion and its intensity."""
    text_lower = reactions_text.lower()

    def _count(words):
        return sum(1 for w in words if w in text_lower)

    emotions = {
        "anxiety": _count(_REACTION_ANXIETY),
        "excitement": _count(_REACTION_EXCITEMENT),
        "outrage": _count(_REACTION_OUTRAGE),
        "sadness": _count(_REACTION_SADNESS),
        "validation": _count(_REACTION_VALIDATION),
        "skepticism": _count(_REACTION_SKEPTICISM),
    }

    total = max(1, sum(emotions.values()))
    dominant = max(emotions, key=emotions.get)
    intensity = emotions[dominant] / total

    return dominant, round(intensity, 3)


# ============================================================================
# Confirmation / Correction Logic
# ============================================================================

def compute_confirmation_correction(
    content_edge_profile: Dict[str, float],
    reaction_edge_profile: Dict[str, float],
    reaction_count: int,
) -> Tuple[Dict[str, float], Dict[str, float], float]:
    """Compute how much reactions confirm or correct the content edge profile.

    Returns:
        confirmation_scores: per-dimension agreement (0=contradiction, 1=match)
        correction_vector: per-dimension delta to apply to content edge profile
        overall_agreement: average agreement (0-1)
    """
    # Reaction weight scales with count, capped at 60%
    reaction_weight = min(0.6, reaction_count / 50.0)

    confirmation = {}
    correction = {}

    for dim in EDGE_DIMENSIONS:
        c = content_edge_profile.get(dim, 0.5)
        r = reaction_edge_profile.get(dim, 0.5)
        delta = r - c

        # Confirmation: 1 - normalized absolute difference
        # All edge dimensions are 0-1 range
        confirmation[dim] = round(max(0.0, 1.0 - abs(delta) * 2.0), 3)

        # Correction: weighted shift toward reaction edge profile
        correction[dim] = round(delta * reaction_weight, 4)

    overall = round(sum(confirmation.values()) / len(confirmation), 3) if confirmation else 0.5

    return confirmation, correction, overall


# ============================================================================
# Apply Corrections to Profile
# ============================================================================

def apply_reaction_corrections(
    profile,  # PagePsychologicalProfile
    reaction: AudienceReactionProfile,
) -> Any:  # Returns PagePsychologicalProfile
    """Apply reaction-based corrections to a page/CTV profile.

    - Applies correction vector to edge_dimensions (primary) or
      construct_activations (fallback)
    - Adjusts mechanisms when reactions disagree with content
    - Boosts confidence when reactions confirm
    """
    if not reaction.correction_vector:
        return profile

    # Read from edge_dimensions (primary) or construct_activations (fallback)
    source_dims = getattr(profile, "edge_dimensions", None)
    if not source_dims:
        source_dims = dict(profile.construct_activations)

    corrected_edge = dict(source_dims)
    for dim, delta in reaction.correction_vector.items():
        if dim in corrected_edge:
            corrected_edge[dim] = round(corrected_edge[dim] + delta, 4)
            # Clamp all edge dimensions to 0-1
            corrected_edge[dim] = max(0.0, min(1.0, corrected_edge[dim]))

    # Write back to both edge_dimensions and construct_activations
    profile.edge_dimensions = corrected_edge
    profile.construct_activations = dict(corrected_edge)

    # Update emotional fields from edge dimensions
    profile.emotional_valence = corrected_edge.get("regulatory_fit", 0.5) - 0.5
    profile.emotional_arousal = corrected_edge.get("emotional_resonance", profile.emotional_arousal)

    # Mechanism adjustments when reactions show content underestimated emotion
    content_resonance = reaction.content_edge_profile.get("emotional_resonance", 0.5)
    reaction_resonance = reaction.reaction_edge_profile.get("emotional_resonance", 0.5)

    if content_resonance < 0.4 and reaction_resonance > 0.6:
        # Content seemed calm but reactions are intense — adjust mechanisms
        for mech in ["loss_aversion", "social_proof"]:
            if mech in profile.mechanism_adjustments:
                profile.mechanism_adjustments[mech] = min(1.5,
                    profile.mechanism_adjustments[mech] * 1.2)
        for mech in ["cognitive_ease"]:
            if mech in profile.mechanism_adjustments:
                profile.mechanism_adjustments[mech] = max(0.5,
                    profile.mechanism_adjustments[mech] * 0.8)

    # Confidence adjustment
    if reaction.overall_agreement > 0.7:
        profile.confidence = min(1.0, profile.confidence * 1.2)
    elif reaction.overall_agreement < 0.3:
        # Strong disagreement — lower confidence in content edge profile
        profile.confidence = max(0.1, profile.confidence * 0.8)

    # Add reaction metadata to social proof signals
    profile.social_proof_signals["reaction_agreement"] = reaction.overall_agreement
    profile.social_proof_signals["reaction_count"] = reaction.reaction_count
    profile.social_proof_signals["dominant_reaction"] = reaction.dominant_reaction_emotion
    profile.social_proof_signals["reaction_intensity"] = reaction.reaction_intensity

    return profile


# ============================================================================
# Reaction Collection Helpers
# ============================================================================

def collect_web_reactions(html: str) -> str:
    """Extract comment/discussion text from a web page's HTML."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Find comment sections by common selectors
        comment_selectors = [
            "[class*='comment']", "[id*='comment']", "[class*='disqus']",
            "[class*='discussion']", "[class*='reply']", "[class*='response']",
            "[class*='user-content']", "[class*='reader']",
        ]

        comment_text = []
        for selector in comment_selectors:
            for el in soup.select(selector):
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 20 and len(text) < 5000:
                    comment_text.append(text)

        return " ".join(comment_text)[:10000]
    except Exception:
        return ""


async def collect_reddit_reactions(query: str, limit: int = 25) -> str:
    """Search Reddit for discussions about content."""
    try:
        import httpx
    except ImportError:
        return ""

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://www.reddit.com/search.json?q={query}&sort=relevance&limit={limit}"
            resp = await client.get(url, headers={
                "User-Agent": "ADAM-Intelligence/1.0 (research)"
            })
            if resp.status_code == 200:
                data = resp.json()
                texts = []
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    title = post.get("title", "")
                    selftext = post.get("selftext", "")
                    texts.append(f"{title} {selftext}")
                return " ".join(texts)[:10000]
    except Exception:
        pass
    return ""


# ============================================================================
# Reaction Intelligence Cache
# ============================================================================

class ReactionIntelligenceCache:
    """Redis-backed cache for audience reaction profiles."""

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
        self, content_key: str, is_ctv: bool = False,
    ) -> Optional[AudienceReactionProfile]:
        r = self._get_redis()
        if not r:
            return None

        prefix = "informativ:reaction:ctv:" if is_ctv else "informativ:reaction:web:"
        try:
            data = r.hgetall(f"{prefix}{content_key}")
            if data:
                return AudienceReactionProfile.from_redis_dict(data)
        except Exception:
            pass
        return None

    def store(
        self, content_key: str, profile: AudienceReactionProfile, is_ctv: bool = False,
    ) -> bool:
        r = self._get_redis()
        if not r:
            return False

        prefix = "informativ:reaction:ctv:" if is_ctv else "informativ:reaction:web:"
        ttl = 172800 if is_ctv else 86400  # 48h CTV, 24h web

        try:
            key = f"{prefix}{content_key}"
            # Serialize all values
            store_data = {}
            for k, v in profile.to_redis_dict().items():
                if isinstance(v, (dict, list)):
                    store_data[k] = json.dumps(v) if not isinstance(v, str) else v
                else:
                    store_data[k] = v
            r.hset(key, mapping=store_data)
            r.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning("Reaction store failed: %s", e)
            return False


# ── Singleton ──

_reaction_cache: Optional[ReactionIntelligenceCache] = None

def get_reaction_cache() -> ReactionIntelligenceCache:
    global _reaction_cache
    if _reaction_cache is None:
        _reaction_cache = ReactionIntelligenceCache()
    return _reaction_cache
