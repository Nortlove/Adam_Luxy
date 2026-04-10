"""
LIWC-lite scorer — fast local annotation using word-list patterns.

Provides Big Five personality estimates, emotion, regulatory focus,
cognitive complexity, and linguistic style from text alone.
No external LIWC license needed.

Based on published word-personality correlations from:
- Yarkoni (2010): "Personality in 100,000 Words"
- Schwartz et al. (2013): "Personality, Gender, and Age in the Language of Social Media"
- Pennebaker et al. (2015): LIWC2015 category descriptions

For ADAM demo prototype: these scores are approximate (r~0.15-0.25 at individual level)
but populate the graph meaningfully for the remaining reviews that don't get Claude annotation.
"""

from __future__ import annotations

import math
import re
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vader = SentimentIntensityAnalyzer()

# =========================================================================
# WORD CATEGORY DICTIONARIES
# Derived from published LIWC categories and personality correlations
# =========================================================================

# Openness markers: insight, abstract, creative, philosophical words
_OPENNESS_WORDS = frozenset("""
think thought feel believe understand imagine wonder consider perspective
insight creative beautiful art culture fascinating unique curious explore
philosophy abstract concept idea theory imagine novel innovative complex
subtle nuanced appreciate depth intellectual sophisticated unusual
poetry aesthetic vision dream inspiration metaphor paradox spectrum
diverse alternative unconventional experimental artistic remarkable
""".split())

# Conscientiousness markers: achievement, work, order, time
_CONSCIENTIOUSNESS_WORDS = frozenset("""
work hard effort achieve success goal plan organize schedule complete
finish deadline responsible duty careful thorough precise accurate
reliable consistent efficient productive quality standard maintain
routine discipline focus determined commit dedicated persistent
detail check verify ensure proper correct clean neat systematic
""".split())

# Extraversion markers: social, positive, enthusiastic, group
_EXTRAVERSION_WORDS = frozenset("""
love amazing awesome fantastic great wonderful excited happy fun party
friend friends family people group social talk share everyone together
wow incredible absolutely definitely totally love beautiful gorgeous
recommend perfect best ever fabulous excellent outstanding brilliant
favorite obsessed addicted hooked rave stunning gorgeous love
""".split())

# Agreeableness markers: prosocial, warm, cooperative, kind
_AGREEABLENESS_WORDS = frozenset("""
kind nice sweet gentle helpful generous caring warm friendly lovely
thank grateful appreciate please sorry understand compassion
support encourage comfort trust honest sincere genuine thoughtful
patient gift blessing thankful bless wonderful precious tender
share give donate volunteer charity community together harmony
""".split())

# Neuroticism markers: anxiety, negative emotion, worry, stress
_NEUROTICISM_WORDS = frozenset("""
worry anxious nervous afraid scared fear stress frustrated angry
upset disappointed sad depressed terrible horrible awful annoying
irritating hate disgusting worst problem issue concern trouble
unfortunately regret mistake broke broken damaged ruined allergic
reaction sensitive painful burning itching rash breakout disaster
""".split())

# Promotion focus: approach, achievement, gain, aspiration
_PROMOTION_WORDS = frozenset("""
achieve accomplish gain win success goal aspire hope wish ideal
advance grow improve upgrade enhance maximize best great wonderful
opportunity potential possible dream desire want eager excited
""".split())

# Prevention focus: obligation, safety, loss-avoidance, caution
_PREVENTION_WORDS = frozenset("""
should must ought need careful safe secure protect avoid prevent
careful cautious responsible duty obligation worry concern risk
safe reliable stable consistent maintain preserve guard ensure
""".split())

# Cognitive complexity: causal reasoning, insight, differentiation
_COGNITIVE_WORDS = frozenset("""
because therefore however although despite whereas nevertheless
consequently furthermore moreover alternatively specifically
particularly essentially fundamentally significantly notably
comparatively relatively apparently evidently presumably
""".split())

# Concrete words (low construal level)
_CONCRETE_WORDS = frozenset("""
hand face skin hair eye body touch feel smell taste color size
bottle tube container package box apply rub spread spray pump
morning night day week month daily routine step product ingredient
""".split())

# Abstract words (high construal level)
_ABSTRACT_WORDS = frozenset("""
confidence beauty identity self-expression transformation
philosophy approach concept value believe system overall general
quality experience lifestyle wellness holistic journey evolution
""".split())


def _word_overlap(text_words: set[str], category: frozenset) -> float:
    """Fraction of text words that appear in category."""
    if not text_words:
        return 0.0
    overlap = len(text_words & category)
    return min(overlap / max(len(text_words), 1), 1.0)


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def score_review_liwc(
    text: str,
    star_rating: int = 3,
    helpful_votes: int = 0,
) -> dict[str, Any]:
    """
    Score a review using LIWC-lite word pattern analysis.

    Returns a flat dict matching the UserSideAnnotation structure
    but with annotation_tier='liwc' and lower confidence.
    """
    text_lower = text.lower()
    words = set(re.findall(r'[a-z]+', text_lower))
    word_list = re.findall(r'[a-z]+', text_lower)
    n_words = len(word_list)
    n_sentences = max(len(re.split(r'[.!?]+', text)), 1)

    # VADER sentiment
    vs = _vader.polarity_scores(text)
    compound = vs['compound']  # -1 to 1
    pos_ratio = vs['pos']
    neg_ratio = vs['neg']

    # --- Big Five ---
    raw_o = _word_overlap(words, _OPENNESS_WORDS)
    raw_c = _word_overlap(words, _CONSCIENTIOUSNESS_WORDS)
    raw_e = _word_overlap(words, _EXTRAVERSION_WORDS)
    raw_a = _word_overlap(words, _AGREEABLENESS_WORDS)
    raw_n = _word_overlap(words, _NEUROTICISM_WORDS)

    # Scale and center: word overlap ~0-0.05 range, expand to 0.2-0.8
    def _scale_big5(raw: float) -> float:
        return _clamp(0.35 + raw * 10.0, 0.1, 0.9)

    openness = _scale_big5(raw_o)
    conscientiousness = _scale_big5(raw_c)
    extraversion = _scale_big5(raw_e)
    agreeableness = _scale_big5(raw_a)
    neuroticism = _scale_big5(raw_n)

    # Adjust with sentiment: positive sentiment boosts E/A, negative boosts N
    extraversion = _clamp(extraversion + compound * 0.1)
    agreeableness = _clamp(agreeableness + compound * 0.08)
    neuroticism = _clamp(neuroticism - compound * 0.1)

    # Confidence is low for LIWC-based personality (per meta-analysis ~r=0.08-0.15)
    big5_conf = 0.15

    # --- Regulatory Focus ---
    promotion = _clamp(0.3 + _word_overlap(words, _PROMOTION_WORDS) * 8.0 + max(compound, 0) * 0.2)
    prevention = _clamp(0.3 + _word_overlap(words, _PREVENTION_WORDS) * 8.0 + max(-compound, 0) * 0.2)

    # --- Decision Style ---
    # Maximizer: long reviews, many comparisons, detailed analysis
    words_per_sent = n_words / n_sentences
    maximizer = _clamp(0.3 + (n_words / 500) * 0.3 + _word_overlap(words, _COGNITIVE_WORDS) * 5.0)
    impulse = _clamp(0.5 - maximizer * 0.3 + (1 if star_rating == 5 and n_words < 100 else 0) * 0.2)
    info_search = _clamp(0.2 + (n_words / 300) * 0.3)

    # --- Construal Level ---
    concrete_score = _word_overlap(words, _CONCRETE_WORDS)
    abstract_score = _word_overlap(words, _ABSTRACT_WORDS)
    construal = _clamp(0.3 + (abstract_score - concrete_score) * 8.0 + 0.2)

    # --- Need for Cognition ---
    nfc = _clamp(0.2 + _word_overlap(words, _COGNITIVE_WORDS) * 8.0 + (n_words / 600) * 0.2)

    # --- Emotion (PAD model) ---
    pleasure = _clamp(compound, -1.0, 1.0)
    arousal = _clamp(abs(compound) * 0.6 + (pos_ratio + neg_ratio) * 0.5)
    dominance = _clamp(0.5 + compound * 0.2 + (0.1 if star_rating >= 4 else -0.1))

    # Primary emotions from VADER + rating
    primary_emotions = []
    if compound > 0.3:
        primary_emotions.append("joy")
        if star_rating == 5:
            primary_emotions.append("excitement")
    elif compound < -0.3:
        primary_emotions.append("disappointment")
        if star_rating <= 2:
            primary_emotions.append("frustration")
    if neg_ratio > 0.15:
        primary_emotions.append("anger" if neg_ratio > 0.25 else "concern")
    if not primary_emotions:
        primary_emotions = ["neutral"]

    # --- Evolutionary Motives (estimated from content) ---
    beauty_self = len(words & {'skin', 'face', 'hair', 'beauty', 'look', 'appearance', 'attractive', 'pretty', 'glow', 'youth', 'aging', 'wrinkle'})
    evo_mate = _clamp(beauty_self / max(n_words, 1) * 15.0 + 0.1)
    evo_status = _clamp(0.15 + _word_overlap(words, {'luxury', 'premium', 'brand', 'expensive', 'quality', 'exclusive', 'designer', 'high-end'}) * 10.0)
    evo_affiliation = _clamp(0.2 + _word_overlap(words, {'friend', 'family', 'recommend', 'share', 'gift', 'together', 'everyone'}) * 8.0)
    evo_self_protection = _clamp(0.2 + _word_overlap(words, {'safe', 'gentle', 'sensitive', 'allergic', 'protect', 'natural', 'organic', 'chemical'}) * 8.0)
    evo_kin = _clamp(0.1 + _word_overlap(words, {'daughter', 'son', 'child', 'kids', 'baby', 'mom', 'mother', 'family', 'gift'}) * 10.0)
    evo_disease = _clamp(0.1 + _word_overlap(words, {'allergic', 'reaction', 'breakout', 'rash', 'irritation', 'sensitive', 'dermatologist', 'acne', 'eczema'}) * 10.0)

    # --- Mechanisms Cited ---
    social_proof = _clamp(0.1 + _word_overlap(words, {'reviews', 'everyone', 'popular', 'recommend', 'trending', 'viral', 'hype', 'rave'}) * 10.0)
    authority = _clamp(0.1 + _word_overlap(words, {'dermatologist', 'doctor', 'expert', 'professional', 'clinical', 'research', 'study', 'proven'}) * 10.0)
    scarcity = _clamp(0.05 + _word_overlap(words, {'limited', 'exclusive', 'sold', 'rare', 'hard', 'find', 'restock'}) * 10.0)

    # --- Implicit Drivers ---
    compensatory = _clamp(0.1 + _word_overlap(words, {'deserve', 'treat', 'splurge', 'indulge', 'reward', 'pamper', 'self-care'}) * 8.0)
    identity_signal = _clamp(0.1 + _word_overlap(words, {'identity', 'who', 'type', 'aesthetic', 'vibe', 'brand', 'luxury', 'premium', 'express'}) * 8.0)

    # --- Lay Theories ---
    price_quality = _clamp(0.3 + _word_overlap(words, {'expensive', 'cheap', 'price', 'worth', 'value', 'cost', 'afford', 'budget', 'quality'}) * 6.0)
    natural_goodness = _clamp(0.2 + _word_overlap(words, {'natural', 'organic', 'clean', 'chemical', 'free', 'vegan', 'cruelty', 'plant', 'botanical'}) * 6.0)

    # --- Purchase Reason ---
    if any(w in words for w in ['gift', 'present', 'birthday']):
        purchase_reason = "gift"
    elif any(w in words for w in ['repurchase', 'reorder', 'again', 'always']):
        purchase_reason = "repurchase"
    elif any(w in words for w in ['try', 'trying', 'sample', 'curious', 'heard']):
        purchase_reason = "discovery"
    elif any(w in words for w in ['replace', 'alternative', 'switch', 'instead']):
        purchase_reason = "replacement"
    else:
        purchase_reason = "routine"

    # --- Conversion Outcome (from star rating) ---
    if star_rating >= 5:
        conversion = "evangelized" if helpful_votes >= 3 else "satisfied"
    elif star_rating >= 4:
        conversion = "satisfied"
    elif star_rating == 3:
        conversion = "neutral"
    elif star_rating == 2:
        conversion = "regret"
    else:
        conversion = "warned" if helpful_votes >= 2 else "regret"

    return {
        # Meta
        "annotation_confidence": 0.25,
        "annotation_tier": "liwc",
        # Personality
        "personality_openness": round(openness, 3),
        "personality_conscientiousness": round(conscientiousness, 3),
        "personality_extraversion": round(extraversion, 3),
        "personality_agreeableness": round(agreeableness, 3),
        "personality_neuroticism": round(neuroticism, 3),
        "confidence_openness": big5_conf,
        "confidence_conscientiousness": big5_conf,
        "confidence_extraversion": big5_conf,
        "confidence_agreeableness": big5_conf,
        "confidence_neuroticism": big5_conf,
        # Regulatory focus
        "regulatory_promotion": round(promotion, 3),
        "regulatory_prevention": round(prevention, 3),
        # Decision style
        "decision_maximizer": round(maximizer, 3),
        "decision_impulse": round(impulse, 3),
        "decision_info_search": round(info_search, 3),
        # Construal
        "construal_level": round(construal, 3),
        # Need for cognition
        "need_for_cognition": round(nfc, 3),
        # Emotion
        "emotion_pleasure": round(pleasure, 3),
        "emotion_arousal": round(arousal, 3),
        "emotion_dominance": round(dominance, 3),
        "primary_emotions": primary_emotions[:3],
        # Evolutionary
        "evo_self_protection": round(evo_self_protection, 3),
        "evo_affiliation": round(evo_affiliation, 3),
        "evo_status": round(evo_status, 3),
        "evo_mate_acquisition": round(evo_mate, 3),
        "evo_kin_care": round(evo_kin, 3),
        "evo_disease_avoidance": round(evo_disease, 3),
        # Mechanisms
        "mech_social_proof": round(social_proof, 3),
        "mech_authority": round(authority, 3),
        "mech_scarcity": round(scarcity, 3),
        "mech_reciprocity": 0.1,
        "mech_commitment": 0.1,
        "mech_liking": round(_clamp(0.1 + max(compound, 0) * 0.3), 3),
        # Implicit drivers
        "implicit_compensatory": round(compensatory, 3),
        "implicit_identity_signaling": round(identity_signal, 3),
        "implicit_wanting_over_liking": 0.2,
        # Lay theories
        "lay_price_quality": round(price_quality, 3),
        "lay_natural_goodness": round(natural_goodness, 3),
        "lay_effort_quality": 0.3,
        "lay_scarcity_value": 0.15,
        # Stated
        "stated_purchase_reason": purchase_reason,
        # Conversion
        "conversion_outcome": conversion,
    }
