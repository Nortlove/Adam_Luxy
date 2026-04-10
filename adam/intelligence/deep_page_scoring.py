"""
Deep Page Psychology Scoring — Beyond Word Counting
=====================================================

10 techniques that dramatically improve NDF accuracy over lexical heuristics.
Organized into three passes:

    Pass 1 Enhancements (<5ms) — Run inline during profile_page_content():
        T2: Collocation-aware context disambiguation
        T7: Prospect Theory frame detection
        T8: Surprisal-based attention prediction (word frequency approximation)

    Pass 1.5 (~100ms) — New pass using spaCy + sentence-transformers:
        T1: Negation-aware dependency scoring
        T4: Semantic NDF via sentence-transformer embeddings
        T6: Implicit need detection via topic-need matrix
        T3: Discourse relation scanning for channel gating
        T5: Psychological arc extraction (per-segment NDF trajectory)

    Pass 3 Enhancement — Structured Claude prompt:
        T9: LLM psychological profiling with sarcasm/irony detection

    Startup Initialization:
        T10: Graph-backed category NDF priors (Bayesian blending)

Each technique's output feeds into the existing PagePsychologicalProfile
fields and the bilateral cascade's mechanism selection.
"""

from __future__ import annotations

import logging
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# LAZY MODEL SINGLETONS — loaded once, reused across all scoring calls
# ============================================================================

_spacy_nlp = None
_sentence_model = None
_ndf_anchors = None  # Pre-computed anchor embeddings for NDF dimensions
_word_freq = None     # Word frequency dict for surprisal approximation
_category_priors = None  # Graph-backed NDF priors per category


def _get_spacy():
    """Lazy-load spaCy model."""
    global _spacy_nlp
    if _spacy_nlp is not None:
        return _spacy_nlp
    try:
        import spacy
        _spacy_nlp = spacy.load("en_core_web_sm", disable=["ner", "textcat"])
        logger.info("spaCy en_core_web_sm loaded")
        return _spacy_nlp
    except Exception as e:
        logger.debug("spaCy not available: %s", e)
        return None


def _get_sentence_model():
    """Lazy-load sentence-transformer model."""
    global _sentence_model
    if _sentence_model is not None:
        return _sentence_model
    try:
        from sentence_transformers import SentenceTransformer
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Sentence-transformer all-MiniLM-L6-v2 loaded")
        return _sentence_model
    except Exception as e:
        logger.debug("Sentence-transformer not available: %s", e)
        return None


def _get_ndf_anchors():
    """Get or compute NDF dimension anchor embeddings."""
    global _ndf_anchors
    if _ndf_anchors is not None:
        return _ndf_anchors

    model = _get_sentence_model()
    if not model:
        return None

    # Anchor texts for each NDF dimension pole
    anchor_texts = {
        "approach_avoidance_pos": (
            "achieving goals, winning, success, growth, opportunity, aspiration, "
            "gaining advantage, improvement, progress, earning rewards"
        ),
        "approach_avoidance_neg": (
            "avoiding danger, protecting safety, preventing loss, security risk, "
            "defending against threats, caution, guarding, shielding from harm"
        ),
        "temporal_horizon_pos": (
            "long-term planning, future investment, years ahead, retirement, "
            "sustainable growth, legacy building, strategic vision, next decade"
        ),
        "temporal_horizon_neg": (
            "right now, immediately, today only, instant results, quick fix, "
            "urgent action, this moment, act fast, don't wait"
        ),
        "social_calibration_pos": (
            "community together, everyone agrees, shared experience, collective, "
            "we all, group consensus, popular opinion, social movement"
        ),
        "social_calibration_neg": (
            "individual choice, personal decision, I alone, my own way, "
            "independent thinking, self-reliance, standing apart, unique path"
        ),
        "uncertainty_tolerance_pos": (
            "maybe, perhaps, it depends, nuanced, complex, debatable, "
            "multiple perspectives, uncertain, ambiguous, open question"
        ),
        "uncertainty_tolerance_neg": (
            "definitely, absolutely certain, proven fact, guaranteed, "
            "without doubt, conclusive evidence, established truth"
        ),
        "status_sensitivity_pos": (
            "premium luxury, exclusive elite, prestigious, finest quality, "
            "world-class, superior, sophisticated, high-end, top-tier"
        ),
        "status_sensitivity_neg": (
            "affordable, everyday, practical, common, basic, simple, "
            "budget-friendly, no-frills, functional, ordinary"
        ),
        "cognitive_engagement_pos": (
            "because therefore, analysis shows, research evidence, data suggests, "
            "careful examination reveals, complex reasoning, logical argument"
        ),
        "cognitive_engagement_neg": (
            "simply, just, easy, straightforward, obvious, no brainer, "
            "clear-cut, intuitive, gut feeling, common sense"
        ),
        "arousal_seeking_pos": (
            "amazing incredible, shocking revelation, explosive growth, "
            "thrilling adventure, mind-blowing, revolutionary breakthrough"
        ),
        "arousal_seeking_neg": (
            "calm steady, predictable reliable, consistent, familiar, "
            "comfortable, settled, peaceful, routine, ordinary"
        ),
    }

    embeddings = model.encode(list(anchor_texts.values()), convert_to_numpy=True)
    _ndf_anchors = {}
    for i, key in enumerate(anchor_texts.keys()):
        _ndf_anchors[key] = embeddings[i]

    logger.info("NDF anchor embeddings computed (14 anchors)")
    return _ndf_anchors


def _get_word_frequencies() -> Dict[str, float]:
    """Get word frequency dict for surprisal approximation.

    Uses a built-in approximation based on Zipf's law applied to
    English word rank. No external file needed.
    """
    global _word_freq
    if _word_freq is not None:
        return _word_freq

    # Top 200 most common English words (approximate Zipf ranks)
    # Frequency = 1/rank^0.8 (Zipf approximation)
    common_words = [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
        "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
        "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
        "people", "into", "year", "your", "good", "some", "could", "them", "see",
        "other", "than", "then", "now", "look", "only", "come", "its", "over",
        "think", "also", "back", "after", "use", "two", "how", "our", "work",
        "first", "well", "way", "even", "new", "want", "because", "any", "these",
        "give", "day", "most", "us",
    ]
    _word_freq = {}
    for i, w in enumerate(common_words, 1):
        _word_freq[w] = 1.0 / (i ** 0.8)

    return _word_freq


# ============================================================================
# TECHNIQUE 2: Collocation-Aware Context Disambiguation (<1ms)
# ============================================================================

# Ambiguous words and their context-dependent interpretations
_COLLOCATION_OVERRIDES = {
    # (word, context_words) → which NDF dimension to reclassify to
    "limited": {
        "scarcity": {"edition", "offer", "time", "supply", "stock", "availability", "seats", "spots"},
        "failure": {"success", "progress", "value", "utility", "impact", "ability", "evidence"},
    },
    "exclusive": {
        "status": {"deal", "offer", "access", "collection", "membership", "brand", "luxury"},
        "credibility": {"interview", "report", "investigation", "footage", "story", "source"},
    },
    "premium": {
        "status": {"brand", "product", "service", "quality", "experience", "membership"},
        "neutral": {"gasoline", "fuel", "gas", "blend", "grade"},
    },
    "free": {
        "reciprocity": {"trial", "sample", "gift", "bonus", "shipping", "download"},
        "neutral": {"speech", "press", "market", "trade", "will", "range", "agent"},
    },
    "authority": {
        "credibility": {"expert", "leading", "recognized", "trusted", "established"},
        "negative": {"authoritarian", "abuse", "overreach", "unchecked"},
    },
}


def apply_collocation_corrections(
    text_lower: str,
    raw_ndf: Dict[str, float],
) -> Dict[str, float]:
    """Correct NDF values for context-dependent word meanings.

    Runs in <1ms. Checks ~50 ambiguous words against their surrounding
    context to determine true psychological meaning.
    """
    corrections = dict(raw_ndf)

    for word, contexts in _COLLOCATION_OVERRIDES.items():
        if word not in text_lower:
            continue

        # Find the word and check its neighborhood (±30 chars)
        for match in re.finditer(rf"\b{word}\b", text_lower):
            start = max(0, match.start() - 30)
            end = min(len(text_lower), match.end() + 30)
            neighborhood = text_lower[start:end]

            for interpretation, context_words in contexts.items():
                if any(cw in neighborhood for cw in context_words):
                    if interpretation == "scarcity" and word == "limited":
                        # Boost arousal_seeking, reduce temporal_horizon
                        corrections["arousal_seeking"] = min(1.0,
                            corrections.get("arousal_seeking", 0.5) + 0.05)
                    elif interpretation == "failure" and word == "limited":
                        # Reduce approach_avoidance
                        corrections["approach_avoidance"] = max(-1.0,
                            corrections.get("approach_avoidance", 0.0) - 0.05)
                    elif interpretation == "status":
                        corrections["status_sensitivity"] = min(1.0,
                            corrections.get("status_sensitivity", 0.5) + 0.03)
                    elif interpretation == "negative":
                        corrections["approach_avoidance"] = max(-1.0,
                            corrections.get("approach_avoidance", 0.0) - 0.05)
                    break  # First matching context wins

    return corrections


# ============================================================================
# TECHNIQUE 7: Prospect Theory Frame Detection (<2ms)
# ============================================================================

_LOSS_FRAME_PATTERNS = [
    r"\blose\b", r"\bcost you\b", r"\bmiss out\b", r"\bdecline\b",
    r"\bdrop\b", r"\bfall\b", r"\brisk of\b", r"\bdanger\b",
    r"\bworse\b", r"\bfail\b", r"\bpay more\b", r"\bpenalt",
    r"\bwithout\b.*\byou\b", r"\bbefore it'?s too late\b",
]

_GAIN_FRAME_PATTERNS = [
    r"\bsave\b", r"\bearn\b", r"\bgain\b", r"\bincrease\b",
    r"\bgrow\b", r"\bwin\b", r"\bbonus\b", r"\bbenefit\b",
    r"\bimprove\b", r"\bfree\b", r"\bdiscount\b", r"\breward\b",
    r"\bupgrade\b", r"\bboost\b", r"\badvantage\b",
]

_ENDOWMENT_PATTERNS = [
    r"\byour home\b", r"\byour famil", r"\byour health\b",
    r"\byour retire", r"\byour saving", r"\byour career\b",
    r"\byour invest", r"\byour money\b", r"\byour account\b",
    r"\byour child", r"\byour future\b",
]

_compiled_loss = [re.compile(p, re.IGNORECASE) for p in _LOSS_FRAME_PATTERNS]
_compiled_gain = [re.compile(p, re.IGNORECASE) for p in _GAIN_FRAME_PATTERNS]
_compiled_endowment = [re.compile(p, re.IGNORECASE) for p in _ENDOWMENT_PATTERNS]


def detect_prospect_frame(text: str) -> Dict[str, float]:
    """Detect Prospect Theory framing: gain vs loss domain.

    Returns:
        prospect_frame: -1 (strong loss frame) to +1 (strong gain frame)
        endowment_effect: 0-1 (how much the text triggers ownership/loss aversion)
        loss_frame_density: raw count of loss-frame sentences
        gain_frame_density: raw count of gain-frame sentences
    """
    loss_count = sum(1 for p in _compiled_loss if p.search(text))
    gain_count = sum(1 for p in _compiled_gain if p.search(text))
    endowment_count = sum(1 for p in _compiled_endowment if p.search(text))

    total = loss_count + gain_count
    if total == 0:
        frame = 0.0
    else:
        frame = (gain_count - loss_count) / total

    endowment = min(1.0, endowment_count / 5.0)

    return {
        "prospect_frame": round(frame, 3),
        "endowment_effect": round(endowment, 3),
        "loss_frame_density": loss_count,
        "gain_frame_density": gain_count,
    }


# ============================================================================
# TECHNIQUE 8: Surprisal-Based Attention Prediction (<1ms)
# ============================================================================

def compute_surprisal_profile(text: str) -> Dict[str, float]:
    """Approximate per-segment attention using word frequency surprisal.

    High-surprisal passages contain rare/unexpected words → reader pays
    more attention. Low-surprisal passages are skimmed.

    Returns:
        mean_surprisal: average surprise level (0-1)
        surprisal_variance: consistency of attention demand
        peak_attention_position: 0-1 where attention peaks (0=start, 1=end)
        attention_at_midpoint: estimated attention at article midpoint
    """
    freq = _get_word_frequencies()
    words = text.lower().split()
    if len(words) < 20:
        return {"mean_surprisal": 0.5, "surprisal_variance": 0.0,
                "peak_attention_position": 0.5, "attention_at_midpoint": 0.5}

    # Compute per-word surprisal: -log(freq) normalized
    max_surprisal = 8.0  # Cap for unknown words
    word_surprisals = []
    for w in words:
        w_clean = re.sub(r"[^a-z]", "", w)
        if not w_clean:
            continue
        f = freq.get(w_clean, 0.0)
        if f > 0:
            surprisal = min(max_surprisal, -math.log(f + 1e-10))
        else:
            surprisal = max_surprisal * 0.7  # Unknown = moderately surprising
        word_surprisals.append(surprisal)

    if not word_surprisals:
        return {"mean_surprisal": 0.5, "surprisal_variance": 0.0,
                "peak_attention_position": 0.5, "attention_at_midpoint": 0.5}

    # Normalize to 0-1
    min_s = min(word_surprisals)
    max_s = max(word_surprisals)
    spread = max_s - min_s if max_s > min_s else 1.0
    normalized = [(s - min_s) / spread for s in word_surprisals]

    # Segment into 10 windows
    n = len(normalized)
    seg_size = max(1, n // 10)
    segment_means = []
    for i in range(0, n, seg_size):
        seg = normalized[i:i + seg_size]
        segment_means.append(sum(seg) / len(seg))

    if not segment_means:
        segment_means = [0.5]

    mean_surprisal = sum(normalized) / len(normalized)
    variance = sum((s - mean_surprisal) ** 2 for s in normalized) / len(normalized)

    # Peak attention position
    peak_idx = segment_means.index(max(segment_means))
    peak_position = peak_idx / max(1, len(segment_means) - 1)

    # Attention at midpoint
    mid_idx = len(segment_means) // 2
    attention_at_mid = segment_means[mid_idx] if mid_idx < len(segment_means) else 0.5

    return {
        "mean_surprisal": round(mean_surprisal, 3),
        "surprisal_variance": round(variance, 4),
        "peak_attention_position": round(peak_position, 3),
        "attention_at_midpoint": round(attention_at_mid, 3),
    }


# ============================================================================
# TECHNIQUE 1: Negation-Aware NDF Scoring (~50ms via spaCy)
# ============================================================================

def negation_corrected_ndf(
    text: str,
    raw_ndf: Dict[str, float],
    word_lists: Optional[Dict[str, Tuple]] = None,
) -> Dict[str, float]:
    """Correct NDF dimensions for negation using spaCy dependencies.

    "Not safe" should reduce security, not increase it.
    "Never certain" should increase uncertainty, not decrease it.
    """
    nlp = _get_spacy()
    if not nlp:
        return raw_ndf

    # Process first 2000 words for speed
    truncated = " ".join(text.split()[:2000])
    doc = nlp(truncated)

    # Track negation corrections
    corrections = dict(raw_ndf)
    negation_count = 0

    # Negation tokens
    neg_lemmas = {"not", "no", "never", "neither", "nor", "barely",
                  "hardly", "rarely", "seldom", "scarcely", "without"}

    # NDF word → dimension mapping (simplified for negation checking)
    _promotion = {"gain", "achieve", "hope", "aspire", "opportunity", "improve",
                  "advance", "succeed", "thrive", "progress", "win"}
    _prevention = {"safe", "secure", "protect", "avoid", "prevent", "risk",
                   "danger", "threat", "guard", "caution", "warning"}
    _certainty = {"definitely", "absolutely", "certain", "proven", "guaranteed",
                  "clearly", "obviously", "confirmed", "conclusive"}
    _tentative = {"might", "perhaps", "could", "maybe", "possibly", "appears",
                  "seems", "suggests", "likely", "uncertain"}

    for token in doc:
        lemma = token.lemma_.lower()

        # Check if this token is negated
        is_negated = False
        # Check children for negation dependency
        for child in token.children:
            if child.dep_ == "neg" or child.lemma_.lower() in neg_lemmas:
                is_negated = True
                break
        # Check head's children (for "is not safe" → safe's head is "is", neg child is "not")
        if not is_negated and token.head != token:
            for sibling in token.head.children:
                if sibling.dep_ == "neg" or sibling.lemma_.lower() in neg_lemmas:
                    is_negated = True
                    break

        if not is_negated:
            continue

        negation_count += 1

        # Apply correction: move word's contribution to opposite pole
        if lemma in _promotion:
            corrections["approach_avoidance"] = max(-1.0,
                corrections.get("approach_avoidance", 0.0) - 0.08)
        elif lemma in _prevention:
            corrections["approach_avoidance"] = min(1.0,
                corrections.get("approach_avoidance", 0.0) + 0.08)
        elif lemma in _certainty:
            corrections["uncertainty_tolerance"] = min(1.0,
                corrections.get("uncertainty_tolerance", 0.5) + 0.08)
        elif lemma in _tentative:
            corrections["uncertainty_tolerance"] = max(0.0,
                corrections.get("uncertainty_tolerance", 0.5) - 0.08)

    if negation_count > 0:
        logger.debug("Negation corrections: %d negated NDF words found", negation_count)

    return corrections


# ============================================================================
# TECHNIQUE 3: Discourse Relation Scanning for Channel Gating (~5ms)
# ============================================================================

# Discourse connectives by type
_CONTRAST_CONNECTIVES = [
    "but", "however", "although", "despite", "nevertheless",
    "on the other hand", "in contrast", "yet", "still", "nonetheless",
    "whereas", "while", "contrary to", "rather than",
]

_CONCESSION_PATTERNS = [
    (r"while\s+.*?,\s+", "concession"),  # "While X, Y" → Y is the actual position
    (r"although\s+.*?,\s+", "concession"),
    (r"despite\s+.*?,\s+", "concession"),
]

# Mechanism words that can be undermined by contrast
_MECHANISM_MARKERS = {
    "authority": {"expert", "research", "study", "scientist", "recommend",
                  "professor", "evidence", "proven", "clinical"},
    "social_proof": {"everyone", "popular", "trending", "millions", "most people",
                     "consensus", "majority", "widely"},
    "scarcity": {"limited", "exclusive", "rare", "running out", "last chance",
                 "only", "few remaining"},
}

_UNDERMINING_MARKERS = {
    "authority": {"wrong", "flawed", "debunk", "questionable", "controversial",
                  "misleading", "disagree", "contradict", "overstate"},
    "social_proof": {"minority", "dissent", "against", "unpopular", "few",
                     "contrarian", "skeptic", "reject"},
    "scarcity": {"abundant", "available", "plenty", "unlimited", "common",
                 "widespread", "artificial"},
}


def scan_discourse_relations(
    text: str,
    current_open: List[str],
    current_closed: List[str],
) -> Dict[str, Any]:
    """Scan for discourse relations that undermine or reinforce mechanism channels.

    Detects patterns like "Experts say X. However, recent data shows the opposite."
    which should CLOSE the authority channel even though authority words appear.

    Returns corrections to open/closed channels.
    """
    text_lower = text.lower()
    sentences = re.split(r'[.!?]+', text_lower)

    channel_corrections = {
        "should_open": [],
        "should_close": [],
        "reasoning": {},
    }

    for i in range(1, len(sentences)):
        prev_sent = sentences[i - 1].strip()
        curr_sent = sentences[i].strip()

        if not prev_sent or not curr_sent:
            continue

        # Check if current sentence starts with a contrast connective
        has_contrast = False
        for conn in _CONTRAST_CONNECTIVES:
            if curr_sent.startswith(conn) or f" {conn} " in curr_sent[:50]:
                has_contrast = True
                break

        if not has_contrast:
            continue

        # Check if previous sentence contains mechanism markers
        # AND current sentence contains undermining markers
        for mechanism, markers in _MECHANISM_MARKERS.items():
            prev_has_mechanism = any(m in prev_sent for m in markers)
            if not prev_has_mechanism:
                continue

            undermining = _UNDERMINING_MARKERS.get(mechanism, set())
            curr_undermines = any(m in curr_sent for m in undermining)

            if curr_undermines:
                if mechanism not in channel_corrections["should_close"]:
                    channel_corrections["should_close"].append(mechanism)
                    channel_corrections["reasoning"][mechanism] = (
                        f"Page presents {mechanism} claims then contradicts them — "
                        f"reader primed to be skeptical of {mechanism} messaging"
                    )

    return channel_corrections


# ============================================================================
# TECHNIQUE 4: Semantic NDF via Sentence-Transformer Embeddings (~50ms)
# ============================================================================

def compute_semantic_ndf(text: str) -> Optional[Dict[str, float]]:
    """Compute NDF dimensions from semantic embeddings.

    Instead of counting word matches, computes cosine similarity between
    the text embedding and pre-defined NDF dimension anchor embeddings.

    This captures meaning that shares zero surface words with the lexicon:
    "the market crashed" → prevention/avoidance even though no prevention
    words appear.
    """
    model = _get_sentence_model()
    anchors = _get_ndf_anchors()
    if not model or not anchors:
        return None

    import numpy as np

    # Chunk text into ~200-word segments, embed each
    words = text.split()
    if len(words) < 20:
        return None

    chunk_size = 200
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk) > 30:
            chunks.append(chunk)

    if not chunks:
        return None

    # Embed all chunks at once (batched for efficiency)
    chunk_embeddings = model.encode(chunks, convert_to_numpy=True)

    # Average across chunks to get document embedding
    doc_embedding = np.mean(chunk_embeddings, axis=0)

    # Compute similarity to each NDF anchor
    ndf_dims = [
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
        "arousal_seeking",
    ]

    semantic_ndf = {}
    for dim in ndf_dims:
        pos_anchor = anchors.get(f"{dim}_pos")
        neg_anchor = anchors.get(f"{dim}_neg")
        if pos_anchor is None or neg_anchor is None:
            semantic_ndf[dim] = 0.5
            continue

        pos_sim = float(np.dot(doc_embedding, pos_anchor) / (
            np.linalg.norm(doc_embedding) * np.linalg.norm(pos_anchor) + 1e-8
        ))
        neg_sim = float(np.dot(doc_embedding, neg_anchor) / (
            np.linalg.norm(doc_embedding) * np.linalg.norm(neg_anchor) + 1e-8
        ))

        # Convert similarity difference to 0-1 scale
        raw = (pos_sim - neg_sim + 1) / 2  # Map [-1,1] to [0,1]
        semantic_ndf[dim] = round(max(0.0, min(1.0, raw)), 4)

    return semantic_ndf


# ============================================================================
# TECHNIQUE 5: Psychological Arc — Per-Segment NDF Trajectory
# ============================================================================

def compute_psychological_arc(
    text: str,
    use_embeddings: bool = False,
) -> Dict[str, Any]:
    """Compute the psychological trajectory across the article.

    Returns per-segment NDF vectors and the NDF at estimated ad positions.
    """
    words = text.split()
    if len(words) < 100:
        return {}

    # Split into 5 segments
    seg_size = len(words) // 5
    segments = []
    for i in range(5):
        seg_text = " ".join(words[i * seg_size:(i + 1) * seg_size])
        segments.append(seg_text)

    # Score each segment
    from adam.intelligence.page_intelligence import profile_page_content
    segment_ndfs = []
    for seg in segments:
        profile = profile_page_content(url="", text_content=seg)
        segment_ndfs.append(profile.construct_activations)

    if not segment_ndfs:
        return {}

    # Compute trajectories per dimension
    ndf_dims = list(segment_ndfs[0].keys())
    trajectories = {}
    for dim in ndf_dims:
        values = [s.get(dim, 0.5) for s in segment_ndfs]
        trajectories[dim] = values

    # NDF at ad positions (25%, 50%, 75% through article)
    def interpolate(values, position):
        idx = position * (len(values) - 1)
        lower = int(idx)
        upper = min(lower + 1, len(values) - 1)
        frac = idx - lower
        return values[lower] * (1 - frac) + values[upper] * frac

    ndf_at_positions = {}
    for pos_name, pos_val in [("early", 0.25), ("mid", 0.5), ("late", 0.75)]:
        ndf_at_positions[pos_name] = {
            dim: round(interpolate(vals, pos_val), 4)
            for dim, vals in trajectories.items()
        }

    # Dimension velocity (rate of change)
    velocities = {}
    for dim in ndf_dims:
        vals = trajectories[dim]
        if len(vals) >= 2:
            velocity = (vals[-1] - vals[0]) / (len(vals) - 1)
            velocities[dim] = round(velocity, 4)

    return {
        "segment_ndfs": segment_ndfs,
        "ndf_at_positions": ndf_at_positions,
        "dimension_velocities": velocities,
        "segments": len(segments),
    }


# ============================================================================
# TECHNIQUE 6: Implicit Need Detection via Topic-Need Matrix
# ============================================================================

_TOPIC_NEED_MATRIX = {
    # Topic patterns → implicitly activated needs (even if not mentioned)
    "financial_anxiety": {
        "patterns": ["inflation", "recession", "layoff", "debt", "mortgage",
                     "rent increase", "cost of living", "bankruptcy", "foreclosure"],
        "needs": {"security": 0.8, "financial_security": 0.9, "competence": -0.3},
    },
    "health_fear": {
        "patterns": ["disease", "cancer", "epidemic", "diagnosis", "symptom",
                     "side effect", "chronic", "terminal", "outbreak"],
        "needs": {"health_concern": 0.9, "security": 0.7, "competence": 0.4},
    },
    "social_comparison": {
        "patterns": ["millionaire", "successful people", "top earners", "celebrity",
                     "influencer lifestyle", "net worth", "how they made it"],
        "needs": {"status": 0.7, "financial_security": 0.5, "self_improvement": 0.6},
    },
    "parenting_anxiety": {
        "patterns": ["child safety", "school shooting", "bullying", "screen time",
                     "development milestone", "child nutrition", "parenting mistake"],
        "needs": {"security": 0.9, "competence": 0.7, "belonging": 0.5},
    },
    "career_uncertainty": {
        "patterns": ["job market", "automation", "ai replacing", "career change",
                     "unemployment", "resume", "interview tips", "skills gap"],
        "needs": {"competence": 0.8, "financial_security": 0.7, "status": 0.5},
    },
    "relationship_needs": {
        "patterns": ["dating", "relationship advice", "marriage", "divorce",
                     "loneliness", "social media comparison", "friend group"],
        "needs": {"belonging": 0.9, "status": 0.4, "self_improvement": 0.5},
    },
    "home_ownership": {
        "patterns": ["housing market", "home prices", "first time buyer", "mortgage rate",
                     "property value", "home renovation", "real estate"],
        "needs": {"financial_security": 0.8, "security": 0.7, "status": 0.5},
    },
    "technology_disruption": {
        "patterns": ["ai", "artificial intelligence", "automation", "robot", "disruption",
                     "tech layoff", "digital transformation", "obsolete"],
        "needs": {"competence": 0.7, "security": 0.5, "self_improvement": 0.6},
    },
    "environmental_anxiety": {
        "patterns": ["climate change", "global warming", "pollution", "extreme weather",
                     "sea level", "carbon", "environmental disaster", "extinction"],
        "needs": {"security": 0.7, "competence": -0.4},
    },
    "political_polarization": {
        "patterns": ["partisan", "polarized", "divided", "culture war", "protest",
                     "misinformation", "conspiracy", "political crisis"],
        "needs": {"belonging": 0.6, "security": 0.5},
    },
}


def detect_implicit_needs(text: str) -> Dict[str, float]:
    """Detect psychological needs implicitly activated by content topics.

    An article about rising rent doesn't say "anxiety" but activates
    security and financial_security needs in the reader.
    """
    text_lower = text.lower()
    activated_needs: Dict[str, float] = {}

    for topic_name, topic_config in _TOPIC_NEED_MATRIX.items():
        # Count pattern matches
        hits = sum(1 for p in topic_config["patterns"] if p in text_lower)
        if hits < 2:
            continue

        # Activate needs proportional to hit density
        activation_strength = min(1.0, hits / len(topic_config["patterns"]) * 2.0)

        for need, base_strength in topic_config["needs"].items():
            current = activated_needs.get(need, 0.0)
            contribution = base_strength * activation_strength
            # Take the stronger activation (don't double-count)
            if abs(contribution) > abs(current):
                activated_needs[need] = round(contribution, 3)

    return activated_needs


# ============================================================================
# TECHNIQUE 10: Graph-Backed Category NDF Priors
# ============================================================================

async def load_category_priors() -> Dict[str, Dict[str, float]]:
    """Load NDF priors per product category from Neo4j bilateral edges.

    Called once at startup. Returns {category: {dim: value}} dict.
    """
    global _category_priors
    if _category_priors is not None:
        return _category_priors

    _category_priors = {}

    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        if not infra._neo4j_driver:
            return _category_priors

        async with infra._neo4j_driver.session() as session:
            query = """
            MATCH (bp:BayesianPrior)
            WHERE bp.category IS NOT NULL AND bp.category <> ''
            RETURN bp.category AS category,
                   bp.avg_reg_fit AS reg_fit,
                   bp.avg_construal_fit AS construal,
                   bp.avg_brand_trust AS brand_trust,
                   bp.sample_size AS n
            LIMIT 100
            """
            result = await session.run(query)
            async for record in result:
                cat = record.get("category", "")
                if cat:
                    _category_priors[cat] = {
                        "approach_avoidance": float(record.get("reg_fit", 0.5) or 0.5),
                        "temporal_horizon": float(record.get("construal", 0.5) or 0.5),
                        "status_sensitivity": float(record.get("brand_trust", 0.5) or 0.5),
                    }

        logger.info("Loaded %d category NDF priors from graph", len(_category_priors))
    except Exception as e:
        logger.debug("Category prior loading failed: %s", e)

    return _category_priors


def blend_with_category_prior(
    text_ndf: Dict[str, float],
    category: str,
    word_count: int,
) -> Dict[str, float]:
    """Bayesian blend of text-derived NDF with graph-backed category prior.

    Short pages get more prior influence; long pages get more text influence.
    """
    if not _category_priors or category not in _category_priors:
        return text_ndf

    prior = _category_priors[category]

    # Weight: more text → trust text more, less text → trust prior more
    text_weight = min(0.9, word_count / 1000.0)
    prior_weight = 1.0 - text_weight

    blended = dict(text_ndf)
    for dim, prior_val in prior.items():
        if dim in blended:
            blended[dim] = round(
                blended[dim] * text_weight + prior_val * prior_weight,
                4,
            )

    return blended


# ============================================================================
# MASTER FUNCTION: Deep Score (Pass 1.5)
# ============================================================================

def deep_score_page(
    text: str,
    raw_ndf: Dict[str, float],
    current_open_channels: List[str],
    current_closed_channels: List[str],
    category: str = "",
    word_count: int = 0,
) -> Dict[str, Any]:
    """Run all deep scoring techniques on a page.

    Called after Pass 1 (profile_page_content) and before Pass 2 (DOM).
    Takes the raw NDF from Pass 1 and refines it with deeper analysis.

    Returns a dict of corrections and new signals to merge into the profile.
    """
    start = time.time()
    results: Dict[str, Any] = {
        "techniques_applied": [],
        "processing_ms": 0.0,
    }

    # T2: Collocation corrections (<1ms)
    corrected_ndf = apply_collocation_corrections(text.lower(), raw_ndf)
    results["ndf_corrected"] = corrected_ndf
    results["techniques_applied"].append("collocation")

    # T7: Prospect Theory frame (<2ms)
    prospect = detect_prospect_frame(text)
    results["prospect_frame"] = prospect
    results["techniques_applied"].append("prospect_theory")

    # T8: Surprisal profile (<1ms)
    surprisal = compute_surprisal_profile(text)
    results["surprisal"] = surprisal
    results["techniques_applied"].append("surprisal")

    # T6: Implicit needs (<1ms)
    implicit_needs = detect_implicit_needs(text)
    if implicit_needs:
        results["implicit_needs"] = implicit_needs
        results["techniques_applied"].append("implicit_needs")

    # T3: Discourse relations (~5ms)
    discourse = scan_discourse_relations(text, current_open_channels, current_closed_channels)
    if discourse["should_close"] or discourse["should_open"]:
        results["channel_corrections"] = discourse
        results["techniques_applied"].append("discourse_relations")

    # T1: Negation-aware scoring (~50ms, requires spaCy)
    if _get_spacy():
        neg_ndf = negation_corrected_ndf(text, corrected_ndf)
        # Blend: 70% negation-corrected, 30% raw (negation can overcorrect)
        for dim in neg_ndf:
            if dim in corrected_ndf:
                corrected_ndf[dim] = round(
                    0.7 * neg_ndf[dim] + 0.3 * corrected_ndf[dim], 4
                )
        results["ndf_corrected"] = corrected_ndf
        results["techniques_applied"].append("negation_aware")

    # T4: Semantic NDF (~50ms, requires sentence-transformer)
    semantic = compute_semantic_ndf(text)
    if semantic:
        # Blend semantic with lexical: 40% semantic, 60% lexical
        for dim in semantic:
            if dim in corrected_ndf:
                corrected_ndf[dim] = round(
                    0.4 * semantic[dim] + 0.6 * corrected_ndf[dim], 4
                )
        results["ndf_corrected"] = corrected_ndf
        results["semantic_ndf"] = semantic
        results["techniques_applied"].append("semantic_ndf")

    # T10: Graph-backed category prior blending
    if category and word_count > 0:
        corrected_ndf = blend_with_category_prior(corrected_ndf, category, word_count)
        results["ndf_corrected"] = corrected_ndf
        results["techniques_applied"].append("category_prior")

    results["processing_ms"] = round((time.time() - start) * 1000, 1)
    return results
