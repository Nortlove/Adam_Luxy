"""
NONCONSCIOUS DECISION FINGERPRINT (NDF) EXTRACTOR
==================================================

Extracts 7 nonconscious decision dimensions from review text using fast
regex-based linguistic marker detection. Designed for ingestion-speed
processing (10k+ reviews/sec when used alongside Hyperscan).

The 7 NDF Dimensions (see docs/NONCONSCIOUS_DECISION_MODELS.md):

  α  approach_avoidance   [-1,1]  Promotion vs. Prevention regulatory focus
  τ  temporal_horizon     [0,1]   Immediate gratification vs. future investment
  σ  social_calibration   [0,1]   Independent vs. socially-referenced decisions
  υ  uncertainty_tolerance[0,1]   Need for closure vs. openness to ambiguity
  ρ  status_sensitivity   [0,1]   Signaling motivation (costly signaling)
  κ  cognitive_engagement [0,1]   Central vs. peripheral processing (ELM)
  λ  arousal_seeking      [0,1]   Sensation-seeking / optimal stimulation level

Each dimension is extracted from linguistic markers backed by research:
  - Pennebaker (LIWC): function words, pronouns, cognitive process words
  - Higgins: regulatory focus language (promotion/prevention)
  - Trope & Liberman: temporal construal language
  - Cacioppo: need for cognition indicators
  - Gosling: behavioral residue patterns

Performance target: < 0.1ms per review (pure string operations, no NLP models).
"""

import re
from typing import Dict, Optional, Tuple

# =============================================================================
# WORD LISTS (compiled once, shared across all calls)
# =============================================================================

# α: Approach-Avoidance (Regulatory Focus)
# Promotion (approach, gain, aspiration) vs. Prevention (avoidance, loss, obligation)
_PROMOTION_WORDS = frozenset([
    "achieve", "gain", "ideal", "hope", "aspire", "accomplish", "advance",
    "success", "win", "grow", "improve", "upgrade", "enhance", "opportunity",
    "dream", "exciting", "amazing", "love", "perfect", "fantastic", "wonderful",
    "great", "excellent", "awesome", "incredible", "outstanding", "brilliant",
    "favorite", "best", "thrilled", "delighted", "impressed", "exceeded",
    "innovative", "creative", "inspired", "transformed", "elevated",
    "beautiful", "gorgeous", "stunning", "superb", "magnificent",
])
_PREVENTION_WORDS = frozenset([
    "safe", "secure", "protect", "careful", "duty", "responsible", "reliable",
    "avoid", "prevent", "risk", "worry", "concern", "afraid", "fear",
    "cautious", "conservative", "stable", "consistent", "dependable", "trust",
    "warranty", "guarantee", "return", "refund", "careful", "durable",
    "sturdy", "solid", "built", "lasts", "withstand", "endure",
    "problem", "issue", "broke", "failed", "defective", "disappointed",
    "waste", "terrible", "horrible", "awful", "worst", "dangerous",
    "warning", "damage", "leak", "crack", "malfunction",
])

# τ: Temporal Horizon (Construal Level)
_FUTURE_WORDS = frozenset([
    "will", "plan", "eventually", "investment", "long-term", "future",
    "years", "months", "lasting", "permanent", "lifetime", "enduring",
    "worth", "value", "quality", "build", "grow", "develop",
    "expect", "anticipate", "looking forward", "down the road",
    "over time", "in the long run", "sustainable", "durable",
])
_PRESENT_WORDS = frozenset([
    "now", "immediately", "instant", "today", "right away", "quick",
    "fast", "hurry", "urgent", "asap", "needed", "impulse",
    "couldn't wait", "had to have", "on the spot", "spur of the moment",
    "same day", "overnight", "rush", "craving", "want",
])

# σ: Social Calibration (Pennebaker pronoun analysis)
# Split into PRONOUN-based (nonconscious, harder to control) and CONTENT-based
# Per Pennebaker: pronouns are function words with the strongest personality signal
_SOCIAL_PRONOUNS = frozenset(["we", "us", "our", "ours", "ourselves"])
_INDIVIDUAL_PRONOUNS = frozenset(["i", "me", "my", "mine", "myself"])
_SOCIAL_CONTENT = frozenset([
    "everyone", "people", "family", "friends",
    "husband", "wife", "kids", "children", "boyfriend", "girlfriend",
    "neighbor", "coworker", "colleague", "community", "group",
    "recommend", "told", "suggested", "reviews", "others",
    "popular", "trending", "gift", "gifted", "gave", "shared", "together",
])
_INDIVIDUAL_CONTENT = frozenset([
    "personally", "opinion", "alone", "solo", "independent", "own", "individual",
])
# Combined sets for backward compatibility
_SOCIAL_WORDS = _SOCIAL_PRONOUNS | _SOCIAL_CONTENT
_INDIVIDUAL_WORDS = _INDIVIDUAL_PRONOUNS | _INDIVIDUAL_CONTENT

# υ: Uncertainty Tolerance (Need for Closure)
_CERTAINTY_WORDS = frozenset([
    "definitely", "absolutely", "certainly", "always", "never",
    "must", "guaranteed", "without doubt", "for sure", "100%",
    "clearly", "obviously", "undoubtedly", "precisely", "exactly",
    "perfect", "flawless", "zero", "every", "all",
    "best", "worst", "only", "nothing", "everything",
])
_TENTATIVE_WORDS = frozenset([
    "might", "maybe", "perhaps", "possibly", "could", "somewhat",
    "kind of", "sort of", "almost", "nearly", "relatively",
    "depends", "varies", "sometimes", "occasionally", "not sure",
    "mixed feelings", "on the fence", "pros and cons", "trade-off",
    "it seems", "appears", "likely", "unlikely", "tends",
    "moderate", "fair", "decent", "okay", "alright",
])

# ρ: Status Sensitivity (Costly Signaling)
_STATUS_WORDS = frozenset([
    "premium", "luxury", "exclusive", "high-end", "top-tier",
    "professional", "expert", "connoisseur", "discerning",
    "upgrade", "superior", "elite", "finest", "best-in-class",
    "designer", "brand", "name brand", "authentic", "genuine",
    "compared to", "better than", "unlike", "competitors",
    "worth every penny", "you get what you pay for", "invest",
    "quality over", "splurge", "indulge", "treat myself",
    "impressive", "compliments", "noticed", "admired",
])

# κ: Cognitive Engagement (Need for Cognition / ELM central route)
# Separated: causal connectives (strongest ELM central-route marker per Petty & Cacioppo)
# vs. general cognitive vocabulary
_CAUSAL_CONNECTIVES = frozenset([
    "because", "therefore", "however", "although", "despite",
    "consequently", "furthermore", "moreover", "nevertheless",
    "whereas", "since", "thus", "hence", "accordingly",
    "as a result", "on the other hand", "in contrast",
])
_COGNITIVE_WORDS = frozenset([
    "because", "therefore", "however", "although", "despite",
    "reason", "analyze", "compare", "evaluate", "research",
    "specification", "feature", "detail", "technical", "performance",
    "measured", "tested", "verified", "data", "evidence",
    "considering", "weighing", "factor", "criterion", "aspect",
    "pros", "cons", "trade-off", "versus", "alternative",
    "specifically", "particularly", "notably", "importantly",
    "consequently", "furthermore", "moreover", "nevertheless",
    "whereas", "hence", "accordingly",
    "in my experience", "after extensive", "thorough",
    "as a result", "on the other hand", "in contrast",
])

# λ: Arousal Seeking (Sensation Seeking / Optimal Stimulation)
_AROUSAL_WORDS = frozenset([
    "amazing", "incredible", "awesome", "wow", "mind-blowing",
    "obsessed", "addicted", "hooked", "can't stop", "love",
    "exciting", "thrilling", "adventurous", "bold", "intense",
    "new", "different", "unique", "novel", "innovative",
    "first time", "never seen", "game changer", "revolutionary",
    "surprising", "unexpected", "discovery", "experiment",
    "fun", "blast", "enjoy", "entertainment", "pleasure",
])

# =============================================================================
# FAST LOOKUP STRUCTURES (split single words vs multi-word phrases)
# =============================================================================

def _split_word_set(words: frozenset):
    """Split a frozenset into single-word set and multi-word phrases list."""
    single = set()
    multi = []
    for w in words:
        if ' ' in w or '-' in w:
            multi.append(w.lower())
        else:
            single.add(w.lower())
    return frozenset(single), tuple(multi)

# Split each word list into fast-lookup single words + multi-word phrases
_PROMO_SINGLE, _PROMO_MULTI = _split_word_set(_PROMOTION_WORDS)
_PREV_SINGLE, _PREV_MULTI = _split_word_set(_PREVENTION_WORDS)
_FUT_SINGLE, _FUT_MULTI = _split_word_set(_FUTURE_WORDS)
_PRES_SINGLE, _PRES_MULTI = _split_word_set(_PRESENT_WORDS)
_SOC_SINGLE, _SOC_MULTI = _split_word_set(_SOCIAL_WORDS)
_IND_SINGLE, _IND_MULTI = _split_word_set(_INDIVIDUAL_WORDS)
_CERT_SINGLE, _CERT_MULTI = _split_word_set(_CERTAINTY_WORDS)
_TENT_SINGLE, _TENT_MULTI = _split_word_set(_TENTATIVE_WORDS)
_STAT_SINGLE, _STAT_MULTI = _split_word_set(_STATUS_WORDS)
_COG_SINGLE, _COG_MULTI = _split_word_set(_COGNITIVE_WORDS)
_ARO_SINGLE, _ARO_MULTI = _split_word_set(_AROUSAL_WORDS)
_CAUSAL_SINGLE, _CAUSAL_MULTI = _split_word_set(_CAUSAL_CONNECTIVES)
# Pronoun sets for weighted social calibration (Pennebaker: pronouns are most reliable)
_SOC_PRON_SET = frozenset(w.lower() for w in _SOCIAL_PRONOUNS)
_IND_PRON_SET = frozenset(w.lower() for w in _INDIVIDUAL_PRONOUNS)

# Punctuation patterns for cognitive velocity / arousal
_RE_CAPS_WORDS = re.compile(r'\b[A-Z]{2,}\b')  # ALL-CAPS words

# Simple word-splitter (strip punctuation from edges)
_WORD_STRIP = str.maketrans('', '', '.,;:!?"\'-()[]{}')


def _count_matches(words_lower: list, text_lower: str, single_set: frozenset, multi_phrases: tuple) -> int:
    """Count how many words match the single-word set + multi-word phrases in text."""
    # Single words: O(n) scan with set lookup
    count = sum(1 for w in words_lower if w in single_set)
    # Multi-word phrases: substring search (few phrases, fast)
    for phrase in multi_phrases:
        if phrase in text_lower:
            count += 1
    return count


# =============================================================================
# CORE EXTRACTION FUNCTION
# =============================================================================

def extract_ndf(text: str, rating: float = 0.0, helpful_votes: int = 0) -> Dict[str, float]:
    """
    Extract Nonconscious Decision Fingerprint from a single review.
    
    Returns dict with 7 float dimensions, each in their natural range.
    Fast: pure regex counting, ~0.05ms per review.
    
    Args:
        text: Review text
        rating: Star rating (0-5), used as behavioral residue
        helpful_votes: Helpful vote count, used as social signal
    
    Returns:
        Dict with keys: approach_avoidance, temporal_horizon, social_calibration,
        uncertainty_tolerance, status_sensitivity, cognitive_engagement, arousal_seeking
    """
    if not text or len(text) < 10:
        return _empty_ndf()
    
    text_lower = text.lower()
    # Split once, strip punctuation for clean word matching
    raw_words = text_lower.translate(_WORD_STRIP).split()
    word_count = len(raw_words)
    if word_count < 3:
        return _empty_ndf()
    
    # Count matches using fast set-lookup + substring search
    n_promotion = _count_matches(raw_words, text_lower, _PROMO_SINGLE, _PROMO_MULTI)
    n_prevention = _count_matches(raw_words, text_lower, _PREV_SINGLE, _PREV_MULTI)
    n_future = _count_matches(raw_words, text_lower, _FUT_SINGLE, _FUT_MULTI)
    n_present = _count_matches(raw_words, text_lower, _PRES_SINGLE, _PRES_MULTI)
    n_social = _count_matches(raw_words, text_lower, _SOC_SINGLE, _SOC_MULTI)
    n_individual = _count_matches(raw_words, text_lower, _IND_SINGLE, _IND_MULTI)
    n_certainty = _count_matches(raw_words, text_lower, _CERT_SINGLE, _CERT_MULTI)
    n_tentative = _count_matches(raw_words, text_lower, _TENT_SINGLE, _TENT_MULTI)
    n_status = _count_matches(raw_words, text_lower, _STAT_SINGLE, _STAT_MULTI)
    n_cognitive = _count_matches(raw_words, text_lower, _COG_SINGLE, _COG_MULTI)
    n_arousal = _count_matches(raw_words, text_lower, _ARO_SINGLE, _ARO_MULTI)
    n_causal = _count_matches(raw_words, text_lower, _CAUSAL_SINGLE, _CAUSAL_MULTI)
    
    # Pronoun-specific counts (Pennebaker: function words are harder to control,
    # thus more reliable nonconscious markers -- weight 2x vs content words)
    n_social_pronouns = sum(1 for w in raw_words if w in _SOC_PRON_SET)
    n_individual_pronouns = sum(1 for w in raw_words if w in _IND_PRON_SET)
    
    # Punctuation / style features
    n_exclamation = text.count('!')
    n_caps = len(_RE_CAPS_WORDS.findall(text))
    
    # Per-100-words normalization for density-based measures
    w100 = word_count / 100.0
    
    # α: Approach-Avoidance [-1, 1]
    total_reg = n_promotion + n_prevention
    if total_reg > 0:
        alpha = (n_promotion - n_prevention) / total_reg
    else:
        # Neutral: slight promotion bias from rating
        alpha = (rating - 3.0) / 5.0 if rating > 0 else 0.0
    
    # τ: Temporal Horizon [0, 1]
    total_temporal = n_future + n_present
    if total_temporal > 0:
        tau = n_future / total_temporal
    else:
        # Default: slightly present-oriented (most reviews are post-purchase)
        tau = 0.4
    
    # σ: Social Calibration [0, 1]
    # Pennebaker research: pronouns are function words with strongest personality signal
    # Weight pronoun-based signal 2x vs content-based signal (pronouns are harder to
    # consciously control, thus more reliable nonconscious markers)
    n_social_content = n_social - n_social_pronouns
    n_ind_content = n_individual - n_individual_pronouns
    weighted_social = n_social_pronouns * 2.0 + n_social_content
    weighted_individual = n_individual_pronouns * 2.0 + n_ind_content
    total_weighted = weighted_social + weighted_individual
    if total_weighted > 0:
        sigma = weighted_social / total_weighted
    else:
        sigma = 0.3  # Default: slightly individual-oriented
    
    # υ: Uncertainty Tolerance [0, 1]
    total_epistemic = n_certainty + n_tentative
    if total_epistemic > 0:
        upsilon = n_tentative / total_epistemic
    else:
        upsilon = 0.5  # Default: neutral
    
    # ρ: Status Sensitivity [0, 1]
    rho = min(1.0, n_status / (w100 + 0.01) * 0.5)
    
    # κ: Cognitive Engagement [0, 1]
    # ELM central route: causal connectives are the strongest marker (Petty & Cacioppo)
    # Combine: causal connectives (2x weight) + cognitive vocabulary + review length
    causal_density = n_causal / (w100 + 0.01) * 0.5  # Weighted 2x: strongest ELM marker
    cognitive_density = n_cognitive / (w100 + 0.01) * 0.3
    length_signal = min(1.0, word_count / 300.0)  # 300+ words = high engagement
    kappa = min(1.0, (causal_density + cognitive_density + length_signal) / 3.0)
    
    # λ: Arousal Seeking [0, 1]
    # Combine arousal words + exclamation marks + ALL-CAPS (cognitive velocity)
    arousal_density = n_arousal / (w100 + 0.01) * 0.3
    exclamation_signal = min(0.5, n_exclamation / (word_count / 50.0 + 0.01) * 0.3)
    caps_signal = min(0.3, n_caps / (w100 + 0.01) * 0.2)
    lam = min(1.0, arousal_density + exclamation_signal + caps_signal)
    
    # Cognitive Velocity (meta-dimension): how pre-cognitive is this text?
    # Higher velocity = less System 2 filtering = more reliable NDF signal
    # Based on: exclamation density, caps density, short avg sentence length
    excl_rate = n_exclamation / (word_count / 50.0 + 0.01)
    caps_rate = n_caps / (w100 + 0.01)
    # Sentence count estimate (rough: split on . ! ?)
    sentence_markers = text.count('.') + text.count('!') + text.count('?')
    avg_sentence_len = word_count / max(1, sentence_markers)
    # Short, punchy sentences = higher velocity (less deliberation)
    brevity_signal = max(0.0, 1.0 - avg_sentence_len / 30.0)
    cognitive_velocity = min(1.0, (
        min(0.4, excl_rate * 0.3) +
        min(0.3, caps_rate * 0.2) +
        brevity_signal * 0.3
    ))
    
    return {
        "approach_avoidance": round(_clamp(alpha, -1.0, 1.0), 4),
        "temporal_horizon": round(_clamp(tau, 0.0, 1.0), 4),
        "social_calibration": round(_clamp(sigma, 0.0, 1.0), 4),
        "uncertainty_tolerance": round(_clamp(upsilon, 0.0, 1.0), 4),
        "status_sensitivity": round(_clamp(rho, 0.0, 1.0), 4),
        "cognitive_engagement": round(_clamp(kappa, 0.0, 1.0), 4),
        "arousal_seeking": round(_clamp(lam, 0.0, 1.0), 4),
        "cognitive_velocity": round(_clamp(cognitive_velocity, 0.0, 1.0), 4),
    }


def _empty_ndf() -> Dict[str, float]:
    return {
        "approach_avoidance": 0.0,
        "temporal_horizon": 0.4,
        "social_calibration": 0.3,
        "uncertainty_tolerance": 0.5,
        "status_sensitivity": 0.0,
        "cognitive_engagement": 0.0,
        "arousal_seeking": 0.0,
        "cognitive_velocity": 0.0,
    }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# =============================================================================
# NDF AGGREGATOR (for population-level statistics during ingestion)
# =============================================================================

class NDFAggregator:
    """
    Accumulates NDF values across reviews for a category.
    
    Produces population-level distributions:
    - Mean and std for each dimension
    - Distribution buckets (deciles)
    - Cross-dimension correlations (which dimensions co-occur)
    - Archetype-conditioned means (NDF profile per archetype)
    """
    
    __slots__ = (
        '_sums', '_sq_sums', '_count',
        '_arch_sums', '_arch_counts',
        '_buckets',
    )
    
    DIMS = (
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
        "arousal_seeking", "cognitive_velocity",
    )
    
    def __init__(self):
        self._sums = {d: 0.0 for d in self.DIMS}
        self._sq_sums = {d: 0.0 for d in self.DIMS}
        self._count = 0
        self._arch_sums = {}  # {archetype: {dim: sum}}
        self._arch_counts = {}  # {archetype: count}
        # 10 buckets per dimension for distribution
        self._buckets = {d: [0] * 10 for d in self.DIMS}
    
    def add(self, ndf: Dict[str, float], archetype: str = ""):
        """Add one NDF observation."""
        self._count += 1
        for dim in self.DIMS:
            val = ndf.get(dim, 0.0)
            self._sums[dim] += val
            self._sq_sums[dim] += val * val
            
            # Bucket: map [-1,1] or [0,1] to 0-9
            if dim == "approach_avoidance":
                bucket_val = (val + 1.0) / 2.0  # Map [-1,1] to [0,1]
            else:
                bucket_val = val
            bucket_idx = min(9, max(0, int(bucket_val * 10)))
            self._buckets[dim][bucket_idx] += 1
        
        if archetype:
            if archetype not in self._arch_sums:
                self._arch_sums[archetype] = {d: 0.0 for d in self.DIMS}
                self._arch_counts[archetype] = 0
            self._arch_counts[archetype] += 1
            for dim in self.DIMS:
                self._arch_sums[archetype][dim] += ndf.get(dim, 0.0)
    
    def to_dict(self) -> Dict:
        """Export aggregated NDF statistics."""
        if self._count == 0:
            return {"ndf_count": 0}
        
        n = self._count
        means = {}
        stds = {}
        for dim in self.DIMS:
            mean = self._sums[dim] / n
            var = max(0.0, self._sq_sums[dim] / n - mean * mean)
            means[dim] = round(mean, 4)
            stds[dim] = round(var ** 0.5, 4)
        
        # Archetype-conditioned NDF profiles
        archetype_profiles = {}
        for arch, counts in self._arch_counts.items():
            if counts < 10:
                continue
            archetype_profiles[arch] = {
                dim: round(self._arch_sums[arch][dim] / counts, 4)
                for dim in self.DIMS
            }
            archetype_profiles[arch]["count"] = counts
        
        return {
            "ndf_count": n,
            "ndf_means": means,
            "ndf_stds": stds,
            "ndf_distributions": {
                dim: self._buckets[dim] for dim in self.DIMS
            },
            "ndf_archetype_profiles": archetype_profiles,
        }


# =============================================================================
# MECHANISM SUSCEPTIBILITY FROM NDF
# =============================================================================

def compute_mechanism_susceptibility(ndf: Dict[str, float]) -> Dict[str, float]:
    """
    Compute susceptibility to each Cialdini mechanism from NDF dimensions.
    
    Each mechanism maps to evolved psychological machinery that the NDF
    dimensions measure. Returns {mechanism: susceptibility_score [0,1]}.
    """
    alpha = ndf.get("approach_avoidance", 0.0)
    tau = ndf.get("temporal_horizon", 0.5)
    sigma = ndf.get("social_calibration", 0.3)
    upsilon = ndf.get("uncertainty_tolerance", 0.5)
    rho = ndf.get("status_sensitivity", 0.0)
    kappa = ndf.get("cognitive_engagement", 0.0)
    lam = ndf.get("arousal_seeking", 0.0)
    
    def _sig(x: float) -> float:
        """Sigmoid: maps (-inf, inf) → (0, 1)."""
        import math
        return 1.0 / (1.0 + math.exp(-x))
    
    return {
        "reciprocity": round(_sig(
            0.4 * sigma + 0.3 * alpha + 0.2 * (1 - rho) + 0.1 * upsilon
        ), 4),
        "commitment": round(_sig(
            0.5 * (1 - upsilon) + 0.3 * (1 - lam) + 0.2 * tau
        ), 4),
        "social_proof": round(_sig(
            0.6 * sigma + 0.2 * (1 - kappa) + 0.2 * (1 - upsilon)
        ), 4),
        "authority": round(_sig(
            0.4 * rho + 0.3 * (1 - upsilon) + 0.2 * (1 - kappa) + 0.1 * (-alpha)
        ), 4),
        "liking": round(_sig(
            0.4 * sigma + 0.3 * alpha + 0.2 * lam + 0.1 * (1 - rho)
        ), 4),
        "scarcity": round(_sig(
            0.4 * alpha + 0.3 * lam + 0.2 * (1 - tau) + 0.1 * rho
        ), 4),
        "unity": round(_sig(
            0.6 * sigma + 0.2 * alpha + 0.1 * (1 - upsilon) + 0.1 * (1 - lam)
        ), 4),
    }
