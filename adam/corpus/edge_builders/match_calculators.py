"""
Match score calculators for edge construction (Phases 5-7).

These are the core intelligence generators — they compute how well
the ad-side psychological profile matches the user-side psychological profile.

v2: Expanded to use ALL ~108 annotated constructs (was ~25).
ALL PURE COMPUTATION — no Claude calls. Fast.
"""

from __future__ import annotations

import math
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# Helper: safe numeric extraction
# ─────────────────────────────────────────────────────────────────────

def _f(d: dict, key: str, default: float = 0.0) -> float:
    """Safely extract a float, treating None as default."""
    v = d.get(key)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _extract_group(d: dict, prefix: str) -> dict[str, float]:
    """Extract all keys with prefix, strip prefix, filter None/0."""
    return {
        k[len(prefix):]: float(v)
        for k, v in d.items()
        if k.startswith(prefix) and v is not None
        and not isinstance(v, str)
    }


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two dicts (shared keys only)."""
    shared = set(a.keys()) & set(b.keys())
    if not shared:
        return 0.0
    dot = sum(a[k] * b[k] for k in shared)
    mag_a = math.sqrt(sum(a[k] ** 2 for k in shared))
    mag_b = math.sqrt(sum(b[k] ** 2 for k in shared))
    if mag_a * mag_b < 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (mag_a * mag_b)))


def _weighted_match(ad: dict[str, float], user: dict[str, float],
                    threshold: float = 0.1) -> float:
    """Weighted match: ad intensity * user resonance, normalized."""
    matches, weights = [], []
    for key in ad:
        ad_val = ad[key]
        if ad_val > threshold:
            user_val = user.get(key, 0.0)
            matches.append(ad_val * user_val)
            weights.append(ad_val)
    return sum(matches) / sum(weights) if weights else 0.0


# ─────────────────────────────────────────────────────────────────────
# Individual match calculators
# ─────────────────────────────────────────────────────────────────────

def regulatory_fit_score(
    ad_gain: float, ad_loss: float,
    user_promotion: float, user_prevention: float,
) -> float:
    """
    Regulatory fit = alignment between ad framing and user orientation.
    Research: Cesario et al. (2004) — fit increases persuasion 20-40%.
    Returns: [-1.0, 1.0] where +1 = perfect fit, -1 = complete mismatch.
    """
    fit = (ad_gain * user_promotion + ad_loss * user_prevention) - \
          (ad_gain * user_prevention + ad_loss * user_promotion)
    return max(-1.0, min(1.0, fit))


def construal_fit_score(ad_construal: float, user_construal: float) -> float:
    """
    Construal fit = how well ad's abstraction level matches user's.
    Research: Trope & Liberman (2003).
    Returns: [0.0, 1.0]
    """
    return 1.0 - abs(ad_construal - user_construal)


def personality_brand_alignment(
    ad_sincerity: float, ad_excitement: float, ad_competence: float,
    ad_sophistication: float, ad_ruggedness: float, ad_warmth: float,
    ad_authenticity: float,
    user_o: float, user_c: float, user_e: float,
    user_a: float, user_n: float,
) -> float:
    """
    Brand personality -> Big Five alignment.
    Research: Matz et al. (2017) — personality-matched ads produce 40-50% higher conversion.
    Returns: [0.0, 1.0]
    """
    alignments = [
        ad_sincerity * user_a,
        ad_excitement * (user_e + user_o) / 2,
        ad_competence * user_c,
        ad_sophistication * user_o,
        ad_warmth * user_a,
        ad_ruggedness * (1.0 - user_n),
        ad_authenticity * user_a,
    ]
    weights = [ad_sincerity, ad_excitement, ad_competence,
               ad_sophistication, ad_warmth, ad_ruggedness, ad_authenticity]
    total = sum(weights)
    if total < 0.01:
        return 0.5
    return sum(a * w for a, w in zip(alignments, weights)) / total


def emotional_resonance(
    ad_emotional_tone: float, ad_hedonic: float,
    user_pleasure: float, user_arousal: float, user_dominance: float,
) -> float:
    """
    How well the ad's emotional strategy resonates with the user's affective state.
    Incorporates hedonic framing and full PAD model.
    Returns: [0.0, 1.0]
    """
    tone_match = 1.0 - abs(ad_emotional_tone - user_pleasure) / 2.0
    arousal_factor = 0.5 + 0.5 * user_arousal
    hedonic_boost = ad_hedonic * (0.5 + 0.5 * user_pleasure)
    dominance_factor = 0.5 + 0.25 * user_dominance
    return min(1.0, tone_match * arousal_factor * dominance_factor + hedonic_boost * 0.2)


def appeal_resonance(ad_appeals: dict[str, float],
                     user_nfc: float, user_pleasure: float,
                     user_neuroticism: float) -> float:
    """
    Match between ad appeal types and user cognitive/emotional profile.
    High NFC -> rational appeals. High emotion -> emotional/narrative appeals.
    Returns: [0.0, 1.0]
    """
    score = 0.0
    total = 0.0
    for appeal, intensity in ad_appeals.items():
        if intensity < 0.1:
            continue
        if appeal == "rational":
            resonance = intensity * user_nfc
        elif appeal == "emotional":
            resonance = intensity * (0.5 + 0.5 * user_pleasure)
        elif appeal == "fear":
            resonance = intensity * user_neuroticism
        elif appeal == "narrative":
            resonance = intensity * (user_nfc * 0.4 + (1.0 - user_neuroticism) * 0.6)
        elif appeal == "comparative":
            resonance = intensity * user_nfc * 0.8
        else:
            resonance = intensity * 0.5
        score += resonance
        total += intensity
    return score / total if total > 0 else 0.5


def processing_route_match(ad_processing_route: float,
                           user_nfc: float, user_info_depth: float) -> float:
    """
    Match between ad processing route (central vs peripheral) and user depth.
    High NFC + high info depth -> central processing (higher ad value).
    Returns: [0.0, 1.0]
    """
    user_central = (user_nfc + user_info_depth) / 2
    return 1.0 - abs(ad_processing_route - user_central)


def implicit_driver_match(ad_implicit: dict[str, float],
                          user_implicit: dict[str, float]) -> float:
    """
    Match between ad's implicit psychological targets and user's implicit drivers.
    Returns: [0.0, 1.0]
    """
    return _weighted_match(ad_implicit, user_implicit, threshold=0.1)


def lay_theory_alignment(user_lay_theories: dict[str, float],
                         ad_values: dict[str, float]) -> float:
    """
    How well the ad's value props align with the user's lay theories.
    e.g., price_quality believer + premium-priced product = high alignment.
    Returns: [0.0, 1.0]
    """
    score = 0.0
    n = 0
    pq = user_lay_theories.get("price_quality", 0.5)
    if pq > 0.5 and ad_values.get("status", 0) > 0.3:
        score += pq * ad_values["status"]
        n += 1
    nat = user_lay_theories.get("natural_goodness", 0.5)
    if nat > 0.5 and ad_values.get("social_responsibility", 0) > 0.3:
        score += nat * ad_values["social_responsibility"]
        n += 1
    effort = user_lay_theories.get("effort_quality", 0.5)
    if effort > 0.5 and (ad_values.get("performance", 0) > 0.3 or ad_values.get("reliability", 0) > 0.3):
        score += effort * max(ad_values.get("performance", 0), ad_values.get("reliability", 0))
        n += 1
    scarcity = user_lay_theories.get("scarcity_value", 0.5)
    if scarcity > 0.5 and ad_values.get("novelty", 0) > 0.3:
        score += scarcity * ad_values["novelty"]
        n += 1
    return score / n if n > 0 else 0.5


def value_alignment(ad_values: dict[str, float],
                    user_decision_style: dict[str, float]) -> float:
    """Match between advertised value propositions and user decision priorities."""
    maximizer = user_decision_style.get("maximizer", 0.5)
    if maximizer > 0.6:
        value_weights = {"performance": 0.25, "reliability": 0.25,
                         "knowledge": 0.2, "cost": 0.15, "transformation": 0.15}
    elif maximizer < 0.4:
        value_weights = {"convenience": 0.25, "pleasure": 0.25,
                         "cost": 0.2, "peace_of_mind": 0.15, "self_expression": 0.15}
    else:
        value_weights = {"performance": 0.15, "convenience": 0.15,
                         "pleasure": 0.15, "reliability": 0.15,
                         "cost": 0.15, "self_expression": 0.13, "novelty": 0.12}

    score, total = 0.0, 0.0
    for val, weight in value_weights.items():
        ad_val = ad_values.get(val, 0.0)
        if ad_val > 0.1:
            score += ad_val * weight
            total += weight
    return score / total if total > 0 else 0.5


def evolutionary_motive_match(ad_motives: dict[str, float],
                              user_motives: dict[str, float]) -> float:
    """Match between evolutionary motives targeted by ad and expressed by user."""
    return _weighted_match(ad_motives, user_motives, threshold=0.1)


def mechanism_effectiveness(ad_techniques: dict[str, float],
                            user_mechanisms_cited: dict[str, float]) -> dict[str, float]:
    """
    For each persuasion technique present in the ad, did the reviewer cite it?
    This is the GOLD signal — direct evidence of technique influence.
    """
    effectiveness = {}
    for technique, ad_intensity in ad_techniques.items():
        if ad_intensity > 0.15:
            user_citation = user_mechanisms_cited.get(technique, 0.0)
            if user_citation > 0.05:
                effectiveness[technique] = round(user_citation, 4)
    return effectiveness


def linguistic_style_match(ad_style: dict[str, float],
                           user_nfc: float, user_openness: float) -> float:
    """
    Match between ad linguistic style and user processing preferences.
    Returns: [0.0, 1.0]
    """
    formality = ad_style.get("formality", 0.5)
    complexity = ad_style.get("complexity", 0.5)
    directness = ad_style.get("directness", 0.5)

    user_complexity_pref = (user_nfc + user_openness) / 2
    complexity_match = 1.0 - abs(complexity - user_complexity_pref)
    directness_match = 1.0 - abs(directness - (1.0 - user_openness) * 0.5 - 0.25)

    return (complexity_match * 0.6 + directness_match * 0.4)


def identity_signaling_match(user_identity_signaling: float,
                             ad_status: float, ad_self_expression: float) -> float:
    """
    How well the ad serves the user's identity signaling needs.
    Returns: [0.0, 1.0]
    """
    if user_identity_signaling < 0.2:
        return 0.5
    ad_signal = max(ad_status, ad_self_expression)
    return user_identity_signaling * ad_signal


def linguistic_style_matching(
    ad_style: dict[str, float],
    user_style: dict[str, float],
) -> float:
    """
    Linguistic Style Matching between ad copy and reviewer writing.
    Research: Ireland et al. (2011) — LSM predicts rapport and persuasion.
    Nature (2020) — language style matching in reviews moderates helpfulness.
    Returns: [0.0, 1.0]
    """
    return _cosine_similarity(ad_style, user_style)


def uniqueness_popularity_fit(
    ad_social_proof: float, ad_scarcity: float,
    ad_novelty: float, ad_self_expression: float,
    user_creative: float, user_unpopular: float,
    user_avoidance: float,
) -> float:
    """
    Fit between ad's popularity/exclusivity signals and user's need for uniqueness.
    Research: Tian & Bearden (2001) — CNFU; Leibenstein (1950) — bandwagon/snob.
    High-NFU users respond negatively to social proof but positively to exclusivity.
    Returns: [-1.0, 1.0] where negative = active mismatch.
    """
    nfu = (user_creative + user_unpopular + user_avoidance) / 3
    if nfu < 0.15:
        return 0.0
    popularity_signal = ad_social_proof
    exclusivity_signal = max(ad_scarcity, ad_novelty, ad_self_expression)
    return max(-1.0, min(1.0,
        nfu * (exclusivity_signal - popularity_signal)
    ))


def involvement_weight_modifier(
    purchase_involvement: float,
    anticipated_regret: float,
) -> float:
    """
    Weight modifier based on purchase involvement level.
    Research: Zaichkowsky (1985) — involvement determines processing depth.
    High involvement amplifies central-route match dimensions.
    Returns: [0.5, 2.0] multiplier for central-route edge dimensions.
    """
    base = 0.5 + purchase_involvement
    regret_boost = 1.0 + anticipated_regret * 0.3
    return min(2.0, base * regret_boost)


def mental_simulation_resonance(
    ad_simulation: float,
    user_openness: float,
    user_hedonic_motive: float,
) -> float:
    """
    How well ad's mental simulation vividness resonates with user.
    Research: Escalas & Luce (2004); Elder & Krishna (2012) — visualization.
    Returns: [0.0, 1.0]
    """
    receptivity = (user_openness + user_hedonic_motive) / 2
    return ad_simulation * (0.4 + 0.6 * receptivity)


def reviewer_reader_linguistic_match(
    peer_style: dict[str, float],
    buyer_style: dict[str, float],
) -> float:
    """
    LSM between peer reviewer and prospective buyer.
    Research: "people who sound like us" — homophily in review processing.
    Returns: [0.0, 1.0]
    """
    return _cosine_similarity(peer_style, buyer_style)


def negative_review_diagnostic_match(
    peer_neg_diagnosticity: float,
    buyer_negativity_seeking: float,
    buyer_neuroticism: float,
) -> float:
    """
    How well a diagnostic negative review serves a negativity-seeking buyer.
    Research: SSRN (2023) — consumers selectively seek negative reviews.
    Returns: [0.0, 1.0]
    """
    need = max(buyer_negativity_seeking, buyer_neuroticism * 0.5)
    return peer_neg_diagnosticity * need


# ─────────────────────────────────────────────────────────────────────
# v4 NEW CONSTRUCT MATCHERS: negativity_bias, reactance, optimal_distinctiveness, brand_trust
# ─────────────────────────────────────────────────────────────────────

def negativity_bias_match(
    ad_loss_framing: float,
    ad_risk_resolution: float,
    user_negativity_bias: float,
) -> float:
    """Match ad loss framing to user's negativity bias tendency.
    High negativity bias users respond to loss framing BUT also need risk resolution.
    Research: Kahneman & Tversky (1979), Rozin & Royzman (2001).
    Returns: [-0.3, 1.0] — can be slightly negative if bias mismatched.
    """
    if user_negativity_bias < 0.2:
        return -ad_loss_framing * 0.3
    return (ad_loss_framing * 0.6 + ad_risk_resolution * 0.4) * user_negativity_bias


def reactance_fit(
    ad_reactance_triggers: float,
    user_reactance: float,
) -> float:
    """Penalize aggressive persuasion for reactance-prone users.
    Research: Brehm (1966), Miron & Brehm (2006).
    Returns: [-0.5, 0.2] — mostly a penalty signal.
    """
    if user_reactance > 0.5 and ad_reactance_triggers > 0.5:
        return -(ad_reactance_triggers * user_reactance)
    return (1.0 - ad_reactance_triggers) * user_reactance * 0.2


def optimal_distinctiveness_fit(
    ad_social_proof: float,
    ad_scarcity: float,
    ad_novelty: float,
    user_optimal_distinctiveness: float,
    user_uniqueness_creative: float,
) -> float:
    """Balance belonging (social proof) with differentiation (scarcity/novelty).
    Research: Brewer (1991) — Optimal Distinctiveness Theory.
    Returns: [0.0, 1.0]
    """
    if user_optimal_distinctiveness < 0.2:
        return ad_social_proof * 0.5
    belonging = ad_social_proof * 0.5
    distinction = (ad_scarcity * 0.4 + ad_novelty * 0.6) * (
        user_optimal_distinctiveness * 0.6 + user_uniqueness_creative * 0.4
    )
    return min(1.0, belonging * 0.4 + distinction * 0.6)


def brand_trust_fit(
    ad_credibility: float,
    ad_transparency: float,
    ad_familiarity: float,
    user_known_brand_trust: float,
    user_unknown_skepticism: float,
    user_review_reliance: float,
) -> float:
    """Match brand trust signals to user's trust profile.
    Research: Chaudhuri & Holbrook (2001), Ha & Perks (2005).
    Returns: [0.0, 1.0]
    """
    brand_is_known = ad_familiarity > 0.5
    if brand_is_known:
        trust_score = ad_familiarity * user_known_brand_trust
    else:
        trust_score = (ad_credibility * 0.5 + ad_transparency * 0.5) * (
            1.0 - user_unknown_skepticism * 0.7
        )
    review_penalty = user_review_reliance * (1.0 - ad_transparency) * 0.3
    return max(0.0, min(1.0, trust_score - review_penalty))


def self_monitoring_fit(
    ad_social_visibility: float, ad_status_appeal: float,
    user_self_monitoring: float,
) -> float:
    """High self-monitors respond to image/status cues; low self-monitors to product quality.
    Snyder (1974): self-monitoring moderates ad appeal effectiveness."""
    ad_image_cue = (ad_social_visibility + ad_status_appeal) / 2
    if user_self_monitoring > 0.5:
        return ad_image_cue * user_self_monitoring
    else:
        return (1.0 - ad_image_cue) * (1.0 - user_self_monitoring)


def spending_pain_match(
    ad_cost_framing: float, ad_value_prop_cost: float,
    user_spending_pain: float,
) -> float:
    """Tightwads need stronger cost justification; spendthrifts respond to pleasure.
    Rick, Cryder & Loewenstein (2008)."""
    cost_mitigation = (ad_cost_framing + ad_value_prop_cost) / 2
    if user_spending_pain > 0.5:
        return cost_mitigation * user_spending_pain
    else:
        return (1.0 - cost_mitigation) * 0.5 + 0.3


def disgust_contamination_fit(
    ad_contamination_framing: float, ad_disease_avoidance: float,
    user_disgust_sensitivity: float,
) -> float:
    """Disgust-sensitive buyers need purity/safety messaging.
    Tybur, Lieberman & Griskevicius (2009)."""
    purity_signal = max(ad_contamination_framing, ad_disease_avoidance)
    if user_disgust_sensitivity > 0.3:
        return purity_signal * user_disgust_sensitivity
    else:
        return 0.3


def anchor_susceptibility_match(
    ad_anchor_deployment: float, ad_anchoring_technique: float,
    user_anchor_susceptibility: float,
) -> float:
    """Anchor-susceptible buyers respond to reference pricing/comparison framing.
    Tversky & Kahneman (1974)."""
    anchor_strength = max(ad_anchor_deployment, ad_anchoring_technique)
    return anchor_strength * user_anchor_susceptibility


def mental_ownership_match(
    ad_mental_simulation: float, ad_psychological_ownership: float,
    user_mental_ownership: float,
) -> float:
    """When ad enables imagined possession and buyer shows endowment language.
    Peck & Shu (2009)."""
    ownership_cue = (ad_mental_simulation + ad_psychological_ownership) / 2
    return ownership_cue * user_mental_ownership


def persuasion_confidence_multiplier(
    helpful_votes: int, total_votes: int,
    review_length: int, annotation_confidence: float,
) -> float:
    """
    Bayesian confidence multiplier based on helpful votes.
    Returns: float >= 1.0
    """
    if total_votes == 0:
        return 1.0
    helpfulness_ratio = helpful_votes / total_votes if total_votes > 0 else 0.0
    length_factor = min(1.0, review_length / 500)
    quality_factor = (length_factor + annotation_confidence) / 2
    return 1.0 + math.log(1 + helpful_votes) * helpfulness_ratio * quality_factor


# ─────────────────────────────────────────────────────────────────────
# Category-dependent mechanism activation weights (v2 Section 9.1)
# Derived from empirical patterns across product categories.
# Weights are relative multipliers (1.0 = baseline).
# ─────────────────────────────────────────────────────────────────────

CATEGORY_MECHANISM_WEIGHTS: dict[str, dict[str, float]] = {
    "Fashion": {
        "personality_brand_alignment": 1.4,
        "emotional_resonance": 1.2,
        "identity_signaling_match": 1.5,
        "optimal_distinctiveness_fit": 1.4,
        "self_monitoring_fit": 1.5,
        "brand_trust_fit": 1.3,
        "linguistic_style_matching": 1.3,
        "disgust_contamination_fit": 0.7,
        "anchor_susceptibility_match": 0.8,
        "spending_pain_match": 1.2,
        "negativity_bias_match": 1.1,
    },
    "Electronics": {
        "processing_route_match": 1.4,
        "lay_theory_alignment": 1.3,
        "appeal_resonance": 1.2,
        "anchor_susceptibility_match": 1.3,
        "brand_trust_fit": 1.2,
        "negativity_bias_match": 1.3,
        "self_monitoring_fit": 0.7,
        "optimal_distinctiveness_fit": 0.8,
        "disgust_contamination_fit": 0.5,
        "mental_ownership_match": 1.2,
    },
    "Health": {
        "disgust_contamination_fit": 1.8,
        "brand_trust_fit": 1.4,
        "negativity_bias_match": 1.5,
        "reactance_fit": 1.2,
        "personality_brand_alignment": 1.3,
        "optimal_distinctiveness_fit": 1.2,
        "self_monitoring_fit": 1.2,
        "identity_signaling_match": 1.1,
        "anchor_susceptibility_match": 0.8,
    },
    "Beauty": {
        "disgust_contamination_fit": 1.8,
        "brand_trust_fit": 1.4,
        "personality_brand_alignment": 1.4,
        "negativity_bias_match": 1.5,
        "optimal_distinctiveness_fit": 1.3,
        "self_monitoring_fit": 1.4,
        "identity_signaling_match": 1.3,
        "emotional_resonance": 1.2,
        "mental_ownership_match": 1.3,
        "anchor_susceptibility_match": 0.8,
    },
    "Home": {
        "processing_route_match": 1.2,
        "lay_theory_alignment": 1.2,
        "spending_pain_match": 1.3,
        "brand_trust_fit": 0.9,
        "negativity_bias_match": 0.9,
        "self_monitoring_fit": 0.6,
        "optimal_distinctiveness_fit": 0.6,
        "identity_signaling_match": 0.6,
        "disgust_contamination_fit": 0.8,
    },
    "Automotive": {
        "processing_route_match": 1.5,
        "brand_trust_fit": 1.4,
        "negativity_bias_match": 1.3,
        "spending_pain_match": 1.4,
        "anchor_susceptibility_match": 1.2,
        "self_monitoring_fit": 0.5,
        "optimal_distinctiveness_fit": 0.4,
        "identity_signaling_match": 0.5,
        "disgust_contamination_fit": 0.5,
    },
}

_CATEGORY_ALIASES: dict[str, str] = {
    "All Beauty": "Beauty", "Luxury Beauty": "Beauty", "Beauty & Personal Care": "Beauty",
    "Skin Care": "Beauty", "Hair Care": "Beauty", "Makeup": "Beauty",
    "Health & Household": "Health", "Health & Personal Care": "Health",
    "Sports & Outdoors": "Health", "Personal Care": "Health",
    "Clothing, Shoes & Jewelry": "Fashion", "Clothing": "Fashion",
    "Shoes": "Fashion", "Accessories": "Fashion",
    "Cell Phones & Accessories": "Electronics", "Computers": "Electronics",
    "Camera & Photo": "Electronics", "Video Games": "Electronics",
    "Home & Kitchen": "Home", "Kitchen & Dining": "Home",
    "Tools & Home Improvement": "Home", "Garden & Outdoor": "Home",
    "Patio, Lawn & Garden": "Home", "Automotive": "Automotive",
}


def get_category_weights(category: str) -> dict[str, float]:
    """Resolve category to mechanism weight overrides.
    Returns empty dict (baseline 1.0 for everything) if category not mapped."""
    normalized = _CATEGORY_ALIASES.get(category, category)
    return CATEGORY_MECHANISM_WEIGHTS.get(normalized, {})


def verified_purchase_trust_signal(is_verified: bool, helpful_votes: int) -> float:
    """Verified purchases with helpful votes are the gold standard of trust.
    Returns 0.0-1.0 trust multiplier."""
    base = 0.7 if is_verified else 0.3
    helpful_boost = min(0.3, math.log1p(helpful_votes) * 0.1)
    return min(1.0, base + helpful_boost)


def review_recency_weight(review_ts: int, product_earliest_ts: int, product_latest_ts: int) -> float:
    """More recent reviews better reflect current product reality.
    Returns 0.3-1.0 weight (never fully discounts old reviews)."""
    span = max(1, product_latest_ts - product_earliest_ts)
    age_frac = max(0.0, min(1.0, (review_ts - product_earliest_ts) / span))
    return 0.3 + 0.7 * age_frac


def star_rating_polarization(rating: float, product_avg: float, product_std: float) -> float:
    """How far this review diverges from the product norm.
    Extreme divergence signals a strong opinion worth weighting differently.
    Returns 0.0-1.0 (0 = matches mean, 1 = extreme outlier)."""
    if product_std < 0.01:
        return 0.0
    z = abs(rating - product_avg) / product_std
    return min(1.0, z / 3.0)


# ─────────────────────────────────────────────────────────────────────
# Master edge computation
# ─────────────────────────────────────────────────────────────────────

def compute_brand_buyer_edge(
    ad_annotation: dict[str, float],
    user_annotation: dict[str, float],
    review_meta: dict,
    product_stats: Optional[dict] = None,
    annotation_uncertainties: Optional[dict] = None,
) -> dict[str, object]:
    """Compute ALL match scores for a BRAND_CONVERTED edge.

    v2: Uses all ~108 annotated constructs across 8 match dimensions
    (was 6 in v1), plus 4 new dimensions.
    v5: Added metadata-derived signals (verified trust, recency, polarization).
    v6: Session 34-4 — optional confidence-weighted composite alignment.

    Args:
        ad_annotation: Flat dict of ad-side construct scores (ad_ prefixed)
        user_annotation: Flat dict of user-side construct scores (user_ prefixed)
        annotation_uncertainties: Optional dict of {dim_name: confidence_weight}
            from SelfConsistencyScorer. When provided, each dimension's
            contribution to composite_alignment is scaled by its confidence_weight.
        review_meta: Review metadata (rating, helpful_vote, text length)
        product_stats: Optional product-level stats (avg_rating, std_rating,
            earliest_ts, latest_ts) for metadata-based signals.

    Returns: Dict of edge properties ready for Neo4j.
    """
    pstats = product_stats or {}
    # ── 1. Regulatory Fit ──
    reg_fit = regulatory_fit_score(
        _f(ad_annotation, "ad_framing_gain"),
        _f(ad_annotation, "ad_framing_loss"),
        _f(user_annotation, "user_regulatory_focus_promotion", 0.5),
        _f(user_annotation, "user_regulatory_focus_prevention", 0.5),
    )

    # ── 2. Construal Fit ──
    constr_fit = construal_fit_score(
        _f(ad_annotation, "ad_processing_targets_construal_level", 0.5),
        _f(user_annotation, "user_construal_level", 0.5),
    )

    # ── 3. Personality-Brand Alignment (expanded with ruggedness + authenticity) ──
    pers_align = personality_brand_alignment(
        _f(ad_annotation, "ad_brand_personality_sincerity"),
        _f(ad_annotation, "ad_brand_personality_excitement"),
        _f(ad_annotation, "ad_brand_personality_competence"),
        _f(ad_annotation, "ad_brand_personality_sophistication"),
        _f(ad_annotation, "ad_brand_personality_ruggedness"),
        _f(ad_annotation, "ad_brand_personality_warmth"),
        _f(ad_annotation, "ad_brand_personality_authenticity"),
        _f(user_annotation, "user_personality_openness", 0.5),
        _f(user_annotation, "user_personality_conscientiousness", 0.5),
        _f(user_annotation, "user_personality_extraversion", 0.5),
        _f(user_annotation, "user_personality_agreeableness", 0.5),
        _f(user_annotation, "user_personality_neuroticism", 0.5),
    )

    # ── 4. Emotional Resonance (expanded with hedonic + PAD model) ──
    emo_res = emotional_resonance(
        _f(ad_annotation, "ad_linguistic_style_emotional_tone"),
        _f(ad_annotation, "ad_framing_hedonic"),
        _f(user_annotation, "user_emotion_pleasure"),
        _f(user_annotation, "user_emotion_arousal", 0.5),
        _f(user_annotation, "user_emotion_dominance", 0.5),
    )

    # ── 5. Value Alignment ──
    ad_values = _extract_group(ad_annotation, "ad_value_propositions_")
    user_ds = _extract_group(user_annotation, "user_decision_style_")
    val_align = value_alignment(ad_values, user_ds)

    # ── 6. Evolutionary Motive Match ──
    ad_evo = _extract_group(ad_annotation, "ad_evolutionary_targets_")
    user_evo = _extract_group(user_annotation, "user_evolutionary_motives_")
    evo_match = evolutionary_motive_match(ad_evo, user_evo)

    # ── 7. Mechanism Effectiveness ──
    ad_techs = _extract_group(ad_annotation, "ad_persuasion_techniques_")
    user_mechs = _extract_group(user_annotation, "user_mechanisms_cited_")
    mech_eff = mechanism_effectiveness(ad_techs, user_mechs)

    # ── 8. Appeal Resonance (NEW) ──
    ad_appeals = _extract_group(ad_annotation, "ad_appeals_")
    appeal_res = appeal_resonance(
        ad_appeals,
        _f(user_annotation, "user_need_for_cognition", 0.5),
        _f(user_annotation, "user_emotion_pleasure"),
        _f(user_annotation, "user_personality_neuroticism", 0.5),
    )

    # ── 9. Processing Route Match (NEW) ──
    proc_match = processing_route_match(
        _f(ad_annotation, "ad_processing_targets_processing_route", 0.5),
        _f(user_annotation, "user_need_for_cognition", 0.5),
        _f(user_annotation, "user_decision_style_information_search_depth", 0.5),
    )

    # ── 10. Implicit Driver Match (NEW) ──
    ad_implicit = _extract_group(ad_annotation, "ad_implicit_targets_")
    user_implicit = _extract_group(user_annotation, "user_implicit_drivers_")
    impl_match = implicit_driver_match(ad_implicit, user_implicit)

    # ── 11. Lay Theory Alignment (NEW) ──
    user_lay = _extract_group(user_annotation, "user_lay_theories_")
    lay_align = lay_theory_alignment(user_lay, ad_values)

    # ── 12. Linguistic Style Match (NEW) ──
    ad_style = _extract_group(ad_annotation, "ad_linguistic_style_")
    ling_match = linguistic_style_match(
        ad_style,
        _f(user_annotation, "user_need_for_cognition", 0.5),
        _f(user_annotation, "user_personality_openness", 0.5),
    )

    # ── 13. Identity Signaling Match (NEW) ──
    id_match = identity_signaling_match(
        _f(user_annotation, "user_implicit_drivers_identity_signaling"),
        ad_values.get("status", 0.0),
        ad_values.get("self_expression", 0.0),
    )

    # ── 14. Linguistic Style Matching (v3) ──
    ad_ling = _extract_group(ad_annotation, "ad_linguistic_style_")
    user_ling = _extract_group(user_annotation, "user_linguistic_style_")
    lsm = linguistic_style_matching(ad_ling, user_ling)

    # ── 15. Uniqueness-Popularity Fit (v3) ──
    nfu_fit = uniqueness_popularity_fit(
        _f(ad_annotation, "ad_persuasion_techniques_social_proof"),
        _f(ad_annotation, "ad_persuasion_techniques_scarcity"),
        ad_values.get("novelty", 0.0),
        ad_values.get("self_expression", 0.0),
        _f(user_annotation, "user_uniqueness_need_creative_choice"),
        _f(user_annotation, "user_uniqueness_need_unpopular_choice"),
        _f(user_annotation, "user_uniqueness_need_avoidance_of_similarity"),
    )

    # ── 16. Mental Simulation Resonance (v3) ──
    sim_res = mental_simulation_resonance(
        _f(ad_annotation, "ad_mental_simulation_vividness"),
        _f(user_annotation, "user_personality_openness", 0.5),
        _f(user_annotation, "user_evolutionary_motives_affiliation"),
    )

    # ── 17. Involvement Weight Modifier (v3) ──
    inv_mod = involvement_weight_modifier(
        _f(user_annotation, "user_purchase_involvement", 0.5),
        _f(user_annotation, "user_anticipated_regret"),
    )

    # ── 18. Negativity Bias Match (v4) ──
    neg_bias = negativity_bias_match(
        _f(ad_annotation, "ad_framing_loss"),
        max(
            _f(ad_annotation, "ad_value_propositions_peace_of_mind"),
            _f(ad_annotation, "ad_value_propositions_reliability"),
        ),
        _f(user_annotation, "user_negativity_bias"),
    )

    # ── 19. Reactance Fit (v4) ──
    react_fit = reactance_fit(
        _f(ad_annotation, "ad_reactance_triggers"),
        _f(user_annotation, "user_reactance"),
    )

    # ── 20. Optimal Distinctiveness (v4) ──
    od_fit = optimal_distinctiveness_fit(
        _f(ad_annotation, "ad_persuasion_techniques_social_proof"),
        _f(ad_annotation, "ad_persuasion_techniques_scarcity"),
        ad_values.get("novelty", 0.0),
        _f(user_annotation, "user_optimal_distinctiveness"),
        _f(user_annotation, "user_uniqueness_need_creative_choice"),
    )

    # ── 21. Brand Trust Fit (v4) ──
    bt_fit = brand_trust_fit(
        _f(ad_annotation, "ad_brand_trust_signals_credibility_cues"),
        _f(ad_annotation, "ad_brand_trust_signals_transparency"),
        _f(ad_annotation, "ad_brand_trust_signals_familiarity_leverage"),
        _f(user_annotation, "user_brand_trust_known_brand_trust"),
        _f(user_annotation, "user_brand_trust_unknown_brand_skepticism"),
        _f(user_annotation, "user_brand_trust_review_reliance"),
    )

    # ── 22. Self-Monitoring Fit (v5) ──
    sm_fit = self_monitoring_fit(
        _f(ad_annotation, "ad_social_visibility"),
        ad_values.get("status", 0.0),
        _f(user_annotation, "user_self_monitoring"),
    )

    # ── 23. Spending Pain Match (v5) ──
    sp_match = spending_pain_match(
        _f(ad_annotation, "ad_framing_utilitarian"),
        ad_values.get("cost", 0.0),
        _f(user_annotation, "user_spending_pain_sensitivity"),
    )

    # ── 24. Disgust/Contamination Fit (v5) ──
    dg_fit = disgust_contamination_fit(
        _f(ad_annotation, "ad_contamination_risk_framing"),
        _f(ad_annotation, "ad_evolutionary_targets_disease_avoidance"),
        _f(user_annotation, "user_disgust_sensitivity"),
    )

    # ── 25. Anchor Susceptibility Match (v5) ──
    anch_match = anchor_susceptibility_match(
        _f(ad_annotation, "ad_anchor_deployment"),
        _f(ad_annotation, "ad_persuasion_techniques_anchoring"),
        _f(user_annotation, "user_anchor_susceptibility"),
    )

    # ── 26. Mental Ownership Match (v5) ──
    mo_match = mental_ownership_match(
        _f(ad_annotation, "ad_mental_simulation_vividness"),
        _f(ad_annotation, "ad_implicit_targets_psychological_ownership"),
        _f(user_annotation, "user_mental_ownership_strength"),
    )

    # ── 27. Cosine Similarity of full brand personality vs Big Five ──
    brand_vec = _extract_group(ad_annotation, "ad_brand_personality_")
    big_five_vec = {
        "sincerity": _f(user_annotation, "user_personality_agreeableness", 0.5),
        "excitement": (_f(user_annotation, "user_personality_extraversion", 0.5) +
                       _f(user_annotation, "user_personality_openness", 0.5)) / 2,
        "competence": _f(user_annotation, "user_personality_conscientiousness", 0.5),
        "sophistication": _f(user_annotation, "user_personality_openness", 0.5),
        "warmth": _f(user_annotation, "user_personality_agreeableness", 0.5),
        "ruggedness": 1.0 - _f(user_annotation, "user_personality_neuroticism", 0.5),
        "authenticity": _f(user_annotation, "user_personality_agreeableness", 0.5),
    }
    full_cosine = _cosine_similarity(brand_vec, big_five_vec)

    # ── Confidence Multiplier ──
    helpful = int(_f(review_meta, "helpful_vote"))
    text_len = len(review_meta.get("text", "") or "")
    ann_conf = _f(user_annotation, "annotation_confidence", 0.5)
    # Fix: use helpful as both helpful and total only when total not available
    total_votes = int(_f(review_meta, "total_vote", helpful))
    pcm = persuasion_confidence_multiplier(helpful, max(total_votes, helpful), text_len, ann_conf)

    # ── Metadata-derived signals (Tier A: zero annotation cost) ──
    is_verified = bool(review_meta.get("verified_purchase", True))
    vp_trust = verified_purchase_trust_signal(is_verified, helpful)

    rev_ts = int(_f(review_meta, "timestamp", 0))
    earliest_ts = int(pstats.get("earliest_ts") or 0)
    latest_ts = int(pstats.get("latest_ts") or rev_ts)
    recency = review_recency_weight(rev_ts, earliest_ts, latest_ts) if rev_ts > 0 else 0.5

    prod_avg = pstats.get("avg_rating") or 3.0
    prod_std = pstats.get("std_rating") or 1.0
    polarization = star_rating_polarization(
        float(review_meta.get("rating", 3)), prod_avg, prod_std
    )

    # ── Category-aware weighting (v5) ──
    category = review_meta.get("category", "")
    cat_w = get_category_weights(category)

    def _cw(dim_name: str, base_weight: float) -> float:
        return base_weight * cat_w.get(dim_name, 1.0)

    # ── Composite Alignment Score (data-calibrated v6) ──
    #
    # v6 CRITICAL FIX (Enhancement #34, Session 34-2 diagnostic):
    # v5 treated ALL dimensions as positive contributors. Logistic regression
    # on 1,492 LUXY Ride bilateral edges revealed 11 dimensions whose SIGN
    # was inverted — higher values HURT conversion. The v5 composite was
    # anticorrelated with conversion (r=-0.29, AUC=0.30).
    #
    # v6 uses data-calibrated weights with correct signs. Dimensions that
    # empirically HURT conversion (reactance_fit, negativity_bias_match,
    # spending_pain_match, etc.) now have NEGATIVE weights — their contribution
    # is subtracted from the composite.
    #
    # Result: r=+0.88, AUC=0.99 on the same data.
    #
    # The category-aware multiplier (_cw) is preserved — it modulates the
    # MAGNITUDE of the weight, not the sign.

    raw_composite = (
        # --- Positive contributors (higher = better for conversion) ---
        emo_res     * _cw("emotional_resonance", 0.138) +          # r=+0.80 ***
        bt_fit      * _cw("brand_trust_fit", 0.125) +              # r=+0.78 ***
        reg_fit     * _cw("regulatory_fit_score", 0.087) +         # r=+0.74 ***
        appeal_res  * _cw("appeal_resonance", 0.083) +             # r=+0.62 ***
        evo_match   * _cw("evolutionary_motive_match", 0.075) +    # r=+0.07
        anch_match  * _cw("anchor_susceptibility_match", 0.033) +  # r=+0.11
        val_align   * _cw("value_alignment", 0.030) +              # r=+0.06
        mo_match    * _cw("mental_ownership_match", 0.028) +       # r=+0.14
        od_fit      * _cw("optimal_distinctiveness_fit", 0.025) +  # r=+0.34
        pers_align  * _cw("personality_brand_alignment", 0.008) +  # r=+0.55
        id_match    * _cw("identity_signaling_match", 0.006) +     # r=+0.00
        # --- Negative contributors (higher = worse for conversion) ---
        # These are SUBTRACTED: high reactance, negativity, spending pain
        # all empirically reduce conversion probability.
        - sim_res     * _cw("mental_simulation_resonance", 0.064) +  # r=-0.15
        - react_fit   * _cw("reactance_fit", 0.059) +               # r=-0.79 ***
        - sp_match    * _cw("spending_pain_match", 0.054) +          # r=-0.54 ***
        - sm_fit      * _cw("self_monitoring_fit", 0.044) +          # r=+0.08 (model says subtract)
        - proc_match  * _cw("processing_route_match", 0.037) +      # r=-0.30 ***
        - full_cosine * 0.035 +                                       # r=-0.40 ***
        - dg_fit      * _cw("disgust_contamination_fit", 0.027) +   # r=-0.18
        - neg_bias    * _cw("negativity_bias_match", 0.019) +       # r=-0.78 ***
        # --- Near-zero contributors (kept for completeness, minimal impact) ---
        ling_match  * _cw("linguistic_style_match", 0.012) +
        lsm         * _cw("linguistic_style_matching", 0.007) +
        lay_align   * _cw("lay_theory_alignment", 0.004) +
        constr_fit  * _cw("construal_fit_score", 0.001) +
        max(0, nfu_fit) * _cw("uniqueness_popularity_fit", 0.025)
    )
    # Session 34-4: Confidence-weighted composite alignment
    # When annotation uncertainties are available, scale each dimension's
    # contribution by its confidence_weight. High-uncertainty dimensions
    # contribute less, reducing noise in barrier diagnosis.
    if annotation_uncertainties:
        # Map dimension variable → dimension name for lookup
        _dim_vars = {
            "emo_res": "emotional_resonance", "bt_fit": "brand_trust_fit",
            "reg_fit": "regulatory_fit_score", "appeal_res": "appeal_resonance",
            "evo_match": "evolutionary_motive_match", "anch_match": "anchor_susceptibility_match",
            "val_align": "value_alignment", "mo_match": "mental_ownership_match",
            "od_fit": "optimal_distinctiveness_fit", "pers_align": "personality_brand_alignment",
            "id_match": "identity_signaling_match", "sim_res": "mental_simulation_resonance",
            "react_fit": "reactance_fit", "sp_match": "spending_pain_match",
            "sm_fit": "self_monitoring_fit", "proc_match": "processing_route_match",
            "full_cosine": "full_cosine_alignment", "dg_fit": "disgust_contamination_fit",
            "neg_bias": "negativity_bias_match", "ling_match": "linguistic_style_match",
            "lsm": "linguistic_style_matching", "lay_align": "lay_theory_alignment",
            "constr_fit": "construal_fit_score", "nfu_fit": "uniqueness_popularity_fit",
        }
        # Compute average confidence weight across dimensions that contribute
        conf_weights = [
            annotation_uncertainties.get(dim_name, 1.0)
            for dim_name in _dim_vars.values()
            if dim_name in annotation_uncertainties
        ]
        if conf_weights:
            avg_conf = sum(conf_weights) / len(conf_weights)
            raw_composite *= avg_conf  # Scale composite by average confidence

    # Shift to 0-1 range: raw_composite can be negative due to negative weights.
    # Empirical range on LUXY Ride data: roughly [-0.15, +0.25].
    # Sigmoid normalization maps to (0, 1) with midpoint at 0.
    import math
    composite_raw = raw_composite * min(inv_mod, 1.5) * min(pcm, 2.0)
    composite = 1.0 / (1.0 + math.exp(-10.0 * composite_raw))  # Sigmoid with gain=10

    # ── Read actual outcome (NOT hardcoded) ──
    outcome = user_annotation.get("user_conversion_outcome")
    if not outcome or outcome not in ("satisfied", "neutral", "regret", "evangelized", "warned"):
        rating = review_meta.get("rating", 3)
        if isinstance(rating, (int, float)):
            if rating >= 4:
                outcome = "satisfied"
            elif rating <= 2:
                outcome = "regret"
            else:
                outcome = "neutral"
        else:
            outcome = "neutral"

    # ── Build final properties dict ──
    props: dict[str, object] = {
        "regulatory_fit_score": round(reg_fit, 4),
        "construal_fit_score": round(constr_fit, 4),
        "personality_brand_alignment": round(pers_align, 4),
        "emotional_resonance": round(emo_res, 4),
        "value_alignment": round(val_align, 4),
        "evolutionary_motive_match": round(evo_match, 4),
        "appeal_resonance": round(appeal_res, 4),
        "processing_route_match": round(proc_match, 4),
        "implicit_driver_match": round(impl_match, 4),
        "lay_theory_alignment": round(lay_align, 4),
        "linguistic_style_match": round(ling_match, 4),
        "identity_signaling_match": round(id_match, 4),
        "full_cosine_alignment": round(full_cosine, 4),
        "linguistic_style_matching": round(lsm, 4),
        "uniqueness_popularity_fit": round(nfu_fit, 4),
        "mental_simulation_resonance": round(sim_res, 4),
        "involvement_weight_modifier": round(inv_mod, 4),
        "composite_alignment": round(composite, 4),
        "star_rating": review_meta.get("rating", 0),
        "outcome": outcome,
        "helpful_votes": helpful,
        "negativity_bias_match": round(neg_bias, 4),
        "reactance_fit": round(react_fit, 4),
        "optimal_distinctiveness_fit": round(od_fit, 4),
        "brand_trust_fit": round(bt_fit, 4),
        "self_monitoring_fit": round(sm_fit, 4),
        "spending_pain_match": round(sp_match, 4),
        "disgust_contamination_fit": round(dg_fit, 4),
        "anchor_susceptibility_match": round(anch_match, 4),
        "mental_ownership_match": round(mo_match, 4),
        "persuasion_confidence_multiplier": round(pcm, 4),
        "verified_purchase_trust": round(vp_trust, 4),
        "review_recency_weight": round(recency, 4),
        "star_rating_polarization": round(polarization, 4),
        "annotation_tier": user_annotation.get("annotation_tier", "unknown"),
        "product_category": review_meta.get("category", ""),
    }
    for mech, score in mech_eff.items():
        props[f"mech_{mech}"] = round(score, 4)

    # Session 34-4: Store annotation confidence metadata
    if annotation_uncertainties:
        conf_weights = list(annotation_uncertainties.values())
        props["annotation_avg_confidence"] = round(
            sum(conf_weights) / len(conf_weights) if conf_weights else 1.0, 4
        )
        props["annotation_n_uncertain_dims"] = sum(
            1 for w in conf_weights if w < 0.6
        )

    return props


# ─────────────────────────────────────────────────────────────────────
# PEER_INFLUENCED edge computation (v2: buyer matching)
# ─────────────────────────────────────────────────────────────────────

def compute_peer_buyer_edge(
    peer_annotation: dict[str, float],
    buyer_annotation: dict[str, float],
    peer_meta: dict,
    product_stats: Optional[dict] = None,
) -> dict[str, object]:
    """Compute PEER_INFLUENCED edge with buyer-side construct matching.

    v2: Actually matches peer constructs against buyer psychology.
    v5: Added metadata-derived trust signals.
    """
    pstats = product_stats or {}
    helpful = int(_f(peer_meta, "helpful_votes"))
    rec_strength = _f(peer_annotation, "peer_ad_recommendation_strength")

    # Base influence from helpful votes + recommendation strength
    influence = min(1.0, helpful / 100.0) * 0.5 + rec_strength * 0.3

    # Authenticity resonance: peer authenticity * buyer agreeableness
    peer_auth = _f(peer_annotation, "peer_ad_testimonial_authenticity")
    buyer_agree = _f(buyer_annotation, "user_personality_agreeableness", 0.5)
    authenticity_resonance = peer_auth * (0.5 + 0.5 * buyer_agree)

    # Anxiety resolution: peer resolved_anxiety * buyer neuroticism
    peer_anxiety_res = _f(peer_annotation, "peer_ad_resolved_anxiety_narrative")
    buyer_neuroticism = _f(buyer_annotation, "user_personality_neuroticism", 0.5)
    anxiety_match = peer_anxiety_res * buyer_neuroticism

    # Narrative resonance: peer narrative * buyer openness
    peer_narrative = _f(peer_annotation, "peer_ad_narrative_arc_completeness")
    buyer_openness = _f(buyer_annotation, "user_personality_openness", 0.5)
    narrative_resonance = peer_narrative * (0.5 + 0.5 * buyer_openness)

    # Use case alignment: peer specificity * buyer NFC
    peer_use_case = _f(peer_annotation, "peer_ad_use_case_matching")
    buyer_nfc = _f(buyer_annotation, "user_need_for_cognition", 0.5)
    use_case_match = peer_use_case * (0.5 + 0.5 * buyer_nfc)

    # Social proof amplification: peer SP * buyer extraversion
    peer_sp = _f(peer_annotation, "peer_ad_social_proof_amplification")
    buyer_extra = _f(buyer_annotation, "user_personality_extraversion", 0.5)
    sp_resonance = peer_sp * (0.5 + 0.5 * buyer_extra)

    # Expertise resonance: peer expertise * buyer conscientiousness
    peer_expertise = _f(peer_annotation, "peer_ad_domain_expertise_signals")
    buyer_consc = _f(buyer_annotation, "user_personality_conscientiousness", 0.5)
    expertise_resonance = peer_expertise * (0.5 + 0.5 * buyer_consc)

    # Emotional contagion: peer emotional potency * buyer emotion sensitivity
    peer_emotion = _f(peer_annotation, "peer_ad_emotional_contagion_potency")
    buyer_pleasure = _f(buyer_annotation, "user_emotion_pleasure")
    emotional_contagion = peer_emotion * (0.5 + 0.25 * abs(buyer_pleasure))

    # Linguistic style match between peer reviewer and buyer (v3)
    peer_ling = {
        k.replace("peer_ad_linguistic_style_", ""): float(v)
        for k, v in peer_annotation.items()
        if k.startswith("peer_ad_linguistic_style_") and v is not None
    }
    buyer_ling = _extract_group(buyer_annotation, "user_linguistic_style_")
    peer_buyer_lsm = reviewer_reader_linguistic_match(peer_ling, buyer_ling)

    # Mental simulation enablement (v3)
    peer_sim = _f(peer_annotation, "peer_ad_mental_simulation_enablement")
    buyer_open = _f(buyer_annotation, "user_personality_openness", 0.5)
    sim_effect = peer_sim * (0.5 + 0.5 * buyer_open)

    # Negative review diagnostic match (v3)
    neg_diag = negative_review_diagnostic_match(
        _f(peer_annotation, "peer_ad_negative_diagnosticity"),
        _f(buyer_annotation, "user_negativity_seeking"),
        _f(buyer_annotation, "user_personality_neuroticism", 0.5),
    )

    # Helpful vote confidence: upvoted reviews carry more weight
    text_len = len(peer_meta.get("text", "") or "")
    total_votes = max(helpful, int(_f(peer_meta, "total_vote", helpful)))
    peer_pcm = persuasion_confidence_multiplier(helpful, total_votes, text_len, 0.5)

    # Composite peer influence (v3 rebalanced, now modulated by helpful confidence)
    raw_composite = (
        influence * 0.15 +
        authenticity_resonance * 0.12 +
        anxiety_match * 0.10 +
        narrative_resonance * 0.08 +
        use_case_match * 0.08 +
        sp_resonance * 0.08 +
        expertise_resonance * 0.08 +
        emotional_contagion * 0.08 +
        peer_buyer_lsm * 0.10 +
        sim_effect * 0.07 +
        neg_diag * 0.06
    )
    composite = min(1.0, raw_composite * min(peer_pcm, 2.0))

    # Boost influence weight with composite
    final_influence = min(1.0, influence + composite * 0.2)

    # Read actual buyer outcome
    buyer_rating = _f(buyer_annotation, "star_rating", 3)
    outcome = buyer_annotation.get("user_conversion_outcome")
    if not outcome or outcome not in ("satisfied", "neutral", "regret", "evangelized", "warned"):
        if buyer_rating >= 4:
            outcome = "satisfied"
        elif buyer_rating <= 2:
            outcome = "regret"
        else:
            outcome = "neutral"

    is_verified = bool(peer_meta.get("verified_purchase", True))
    peer_vp_trust = verified_purchase_trust_signal(is_verified, helpful)

    peer_ts = int(_f(peer_meta, "timestamp", 0))
    earliest_ts = int(pstats.get("earliest_ts") or 0)
    latest_ts = int(pstats.get("latest_ts") or peer_ts)
    peer_recency = review_recency_weight(peer_ts, earliest_ts, latest_ts) if peer_ts > 0 else 0.5

    return {
        "influence_weight": round(final_influence, 4),
        "peer_authenticity_resonance": round(authenticity_resonance, 4),
        "anxiety_resolution_match": round(anxiety_match, 4),
        "narrative_resonance": round(narrative_resonance, 4),
        "use_case_match": round(use_case_match, 4),
        "sp_resonance": round(sp_resonance, 4),
        "expertise_resonance": round(expertise_resonance, 4),
        "emotional_contagion": round(emotional_contagion, 4),
        "peer_buyer_linguistic_match": round(peer_buyer_lsm, 4),
        "mental_simulation_effect": round(sim_effect, 4),
        "negative_diagnosticity_match": round(neg_diag, 4),
        "composite_peer_alignment": round(composite, 4),
        "star_rating": int(buyer_rating),
        "outcome": outcome,
        "helpful_votes": helpful,
        "verified_purchase_trust": round(peer_vp_trust, 4),
        "review_recency_weight": round(peer_recency, 4),
    }
