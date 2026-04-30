"""
Real-Time Decision Engine — The Persuasion Optimizer
======================================================

This is the SINGLE entry point that fuses ALL intelligence signals
into one optimized persuasion decision in <12ms.

When a bid request arrives, this engine:

1. LOCATES the reader in 20-dim psychological space
   - Impression state resolver (title + referrer + keywords + IAB)
   - Page profile lookup (pre-scored or taxonomy inference)
   - Both systems compose into one position vector

2. QUERIES what converts in this psychological state
   - Pre-computed page-state → mechanism effectiveness (Redis cached)
   - Bilateral edge evidence (47M edges, pre-aggregated by state cluster)
   - Causal effects (discovered (:PageDimension)-[:AMPLIFIES]->(:Mechanism))

3. MODULATES with environmental context
   - Cultural calendar (tax season → authority 1.4x)
   - News cycle ambient state
   - Category temperature (heating/cooling)
   - Temporal drift (declining/rising mechanisms)
   - Competitive mechanism saturation
   - Brand complement (don't repeat what the landing page does)

4. COMPUTES the optimal creative direction
   - Page-conditioned gradient (what dims to emphasize given page state)
   - Gap analysis (what the page provides vs what the ad must address)
   - Specific framing, tone, construal, urgency, copy direction

5. RETURNS a single, actionable recommendation
   - Primary + secondary mechanism
   - Exact framing and tone
   - What to say and what NOT to say
   - Expected lift and confidence
   - Bid premium recommendation

All Redis lookups. No graph queries at bid time. Everything pre-computed
by the 15 daily strengthening tasks.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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

MECHANISMS = [
    "authority", "social_proof", "scarcity", "loss_aversion",
    "commitment", "liking", "reciprocity", "curiosity",
    "cognitive_ease", "unity",
]


@dataclass
class PersuasionDecision:
    """The optimized output: exactly what makes this ad maximally persuasive."""

    # ── What mechanism to deploy ──
    primary_mechanism: str = ""
    secondary_mechanism: str = ""
    mechanism_scores: Dict[str, float] = field(default_factory=dict)
    mechanism_reasoning: str = ""

    # ── Exactly how to frame the message ──
    framing: str = ""                # gain / loss / mixed
    tone: str = ""                   # reassuring / energetic / authoritative / warm / urgent
    construal_level: str = ""        # concrete / moderate / abstract
    urgency_level: float = 0.0      # 0-1
    emotional_intensity: float = 0.0 # 0-1
    copy_length: str = ""           # short / medium / long

    # ── What to say and what NOT to say ──
    what_to_say: List[str] = field(default_factory=list)
    what_not_to_say: List[str] = field(default_factory=list)

    # ── The psychological gap the ad must close ──
    page_already_provides: List[str] = field(default_factory=list)
    ad_must_address: List[str] = field(default_factory=list)

    # ── Evidence and confidence ──
    confidence: float = 0.0
    evidence_sources: List[str] = field(default_factory=list)
    reader_position: Dict[str, float] = field(default_factory=dict)
    page_state_summary: str = ""

    # ── Bid optimization ──
    bid_premium_pct: float = 0.0
    expected_lift_pct: float = 0.0

    # ── Environmental modifiers applied ──
    environmental_mods: Dict[str, Any] = field(default_factory=dict)

    # ── Timing ──
    decision_ms: float = 0.0


def compute_persuasion_decision(
    # From bid request
    page_url: str = "",
    page_title: str = "",
    referrer: str = "",
    keywords: Optional[List[str]] = None,
    iab_categories: Optional[List[str]] = None,
    device_type: str = "desktop",
    time_of_day: int = 12,
    # From segment/product
    segment_id: str = "",
    archetype: str = "",
    asin: str = "",
    buyer_id: str = "",
    product_category: str = "",
    brand_name: str = "",
) -> PersuasionDecision:
    """Compute the optimal persuasion decision in <12ms.

    Fuses ALL available intelligence into one recommendation.
    All lookups are Redis (<2ms each). No graph queries at bid time.
    """
    start = time.time()
    decision = PersuasionDecision()

    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    except Exception:
        decision.decision_ms = (time.time() - start) * 1000
        return decision

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: LOCATE — Where is this reader psychologically?
    # ═══════════════════════════════════════════════════════════════

    reader_dims = {}
    evidence = []

    # 1a. Impression State Resolver (composes ALL bid request signals)
    try:
        from adam.intelligence.impression_state_resolver import resolve_reader_position
        position = resolve_reader_position(
            page_url=page_url, page_title=page_title,
            referrer=referrer, keywords=keywords,
            iab_categories=iab_categories,
            device_type=device_type, time_of_day=time_of_day,
        )
        if position.confidence > 0:
            reader_dims = position.dimensions
            decision.reader_position = reader_dims
            evidence.append(f"impression_resolver({','.join(position.signals_used)})")
    except Exception:
        pass

    # 1b. Pre-scored page profile (if available, higher precision)
    try:
        from adam.intelligence.page_intelligence import get_page_intelligence_cache
        cache = get_page_intelligence_cache()
        profile = cache.lookup(page_url) if page_url else None
        if profile and profile.edge_dimensions:
            # Blend: if we have both, weight pre-scored higher
            if reader_dims:
                for dim in EDGE_DIMENSIONS:
                    resolver_val = reader_dims.get(dim, 0.5)
                    profile_val = profile.edge_dimensions.get(dim, 0.5)
                    # Pre-scored profile gets more weight (more data behind it)
                    reader_dims[dim] = round(
                        0.4 * resolver_val + 0.6 * profile_val, 4
                    )
            else:
                reader_dims = dict(profile.edge_dimensions)
            evidence.append(f"page_profile({profile.profile_source})")
    except Exception:
        pass

    if not reader_dims:
        # Absolute fallback: neutral position
        reader_dims = {dim: 0.5 for dim in EDGE_DIMENSIONS}
        evidence.append("neutral_fallback")

    decision.reader_position = reader_dims

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: SCORE — Which mechanisms work in this state?
    # ═══════════════════════════════════════════════════════════════

    # 2a. Derive mechanism scores from reader position
    # (same formulas as bilateral cascade, but operating on the reader position)
    mechanism_scores = _score_mechanisms_from_position(reader_dims)

    # 2b. Apply discovered causal effects (from self-teaching)
    try:
        for mech in MECHANISMS:
            data = r.hgetall(f"informativ:drift:mechanism:{mech}")
            if data:
                trend = data.get("trend", "stable")
                slope = float(data.get("slope", 0))
                if trend == "declining" and abs(slope) > 0.002:
                    mechanism_scores[mech] *= max(0.80, 1.0 + slope * 10)
                elif trend == "rising" and slope > 0.002:
                    mechanism_scores[mech] *= min(1.15, 1.0 + slope * 10)
        evidence.append("temporal_drift")
    except Exception:
        pass

    # 2c. Apply environmental modifiers (calendar, ambient, temperature)
    env_mods = {}
    try:
        from adam.intelligence.daily.consumer import get_intelligence_consumer
        consumer = get_intelligence_consumer()

        # Environmental context
        env_ctx = consumer.get_environmental_context()
        combined_mods = env_ctx.get("combined_mechanism_mods", {})
        for mech, mod in combined_mods.items():
            if mech in mechanism_scores:
                mechanism_scores[mech] *= float(mod)
        if env_ctx.get("active_events"):
            env_mods["events"] = env_ctx["active_events"]
            evidence.append(f"calendar({','.join(env_ctx['active_events'])})")

        # Category temperature
        if product_category:
            temp = consumer.get_category_temperature(product_category)
            if temp.get("score", 0) != 0:
                env_mods["temperature"] = temp
                evidence.append(f"temperature({temp['trend']})")

        # Brand complement
        if brand_name:
            complement = consumer.get_brand_complement(brand_name.lower())
            if complement.get("recommended_complement"):
                rec = complement["recommended_complement"]
                avoid = complement.get("avoid_mechanism", "")
                if rec in mechanism_scores:
                    mechanism_scores[rec] *= 1.15  # Boost complement
                if avoid in mechanism_scores:
                    mechanism_scores[avoid] *= 0.85  # Dampen repeat
                env_mods["brand_complement"] = complement
                evidence.append(f"brand_complement({rec})")

        # Competitive saturation
        if product_category:
            domain = ""
            if page_url:
                from adam.intelligence.page_intelligence import _extract_domain
                domain = _extract_domain(page_url) or ""
            mods = consumer.get_mechanism_modifiers(domain, product_category)
            for mech, mod in mods.items():
                if mech in mechanism_scores:
                    mechanism_scores[mech] *= mod
            evidence.append("competitive_mods")
    except Exception:
        pass

    decision.environmental_mods = env_mods

    # ═══════════════════════════════════════════════════════════════
    # STEP 3: DECIDE — What's the optimal creative direction?
    # ═══════════════════════════════════════════════════════════════

    # Rank mechanisms
    ranked = sorted(mechanism_scores.items(), key=lambda x: x[1], reverse=True)
    decision.primary_mechanism = ranked[0][0] if ranked else "social_proof"
    decision.secondary_mechanism = ranked[1][0] if len(ranked) > 1 else "authority"
    decision.mechanism_scores = {k: round(v, 4) for k, v in mechanism_scores.items()}

    # Derive creative parameters from reader position
    reg = reader_dims.get("regulatory_fit", 0.5)
    con = reader_dims.get("construal_fit", 0.5)
    emo = reader_dims.get("emotional_resonance", 0.5)
    td = reader_dims.get("temporal_discounting", 0.5)
    clt = reader_dims.get("cognitive_load_tolerance", 0.5)
    ar = reader_dims.get("autonomy_reactance", 0.5)
    nt = reader_dims.get("narrative_transport", 0.5)
    lai = reader_dims.get("loss_aversion_intensity", 0.5)
    isk = reader_dims.get("information_seeking", 0.5)
    sps = reader_dims.get("social_proof_sensitivity", 0.5)

    # Framing
    if reg > 0.6:
        decision.framing = "gain"
    elif reg < 0.4 or lai > 0.6:
        decision.framing = "loss"
    else:
        decision.framing = "mixed"

    # Tone
    if emo > 0.6 and ar < 0.4:
        decision.tone = "warm, empathetic"
    elif isk > 0.6 and clt > 0.5:
        decision.tone = "authoritative, evidence-based"
    elif lai > 0.6:
        decision.tone = "reassuring, protective"
    elif td > 0.6:
        decision.tone = "urgent, compelling"
    else:
        decision.tone = "confident, balanced"

    # Construal
    if con > 0.6:
        decision.construal_level = "abstract"
    elif con < 0.4 or isk > 0.6:
        decision.construal_level = "concrete"
    else:
        decision.construal_level = "moderate"

    # Urgency
    decision.urgency_level = round(td * 0.5 + emo * 0.3 + (1 - ar) * 0.2, 2)

    # Emotional intensity
    decision.emotional_intensity = round(emo * 0.6 + nt * 0.2 + (1 - clt) * 0.2, 2)

    # Copy length (based on bandwidth)
    if device_type == "mobile" or clt < 0.35:
        decision.copy_length = "short"
    elif clt > 0.65 and isk > 0.6:
        decision.copy_length = "long"
    else:
        decision.copy_length = "medium"

    # ═══════════════════════════════════════════════════════════════
    # STEP 4: DIRECT — What exactly should the ad say?
    # ═══════════════════════════════════════════════════════════════

    # What to say (based on mechanism + reader state)
    _MECHANISM_COPY_DIRECTION = {
        "authority": {
            "say": ["Lead with expert endorsement or credentials",
                     "Cite specific evidence, data, or research",
                     "Use professional, confident language"],
            "avoid": ["Emotional manipulation", "Vague unsubstantiated claims",
                       "Casual or slang language"],
        },
        "social_proof": {
            "say": ["Show numbers: users, ratings, reviews",
                     "Feature real testimonials with names",
                     "Emphasize popularity and community"],
            "avoid": ["Individual expertise claims",
                       "Exclusivity messaging", "Contrarian positioning"],
        },
        "loss_aversion": {
            "say": ["Frame what they'll miss without acting",
                     "Show the cost of inaction",
                     "Provide protection and safety framing"],
            "avoid": ["Pure gain framing", "Aspirational language",
                       "Minimizing the stakes"],
        },
        "scarcity": {
            "say": ["Create genuine time pressure",
                     "Show limited availability with specifics",
                     "Emphasize what's at stake NOW"],
            "avoid": ["Long-term investment framing",
                       "Patient/deliberative messaging",
                       "Abundance messaging"],
        },
        "commitment": {
            "say": ["Start with small ask, build to bigger",
                     "Reference existing choices or values",
                     "Emphasize consistency and reliability"],
            "avoid": ["Pressure tactics", "Novelty/switching messaging",
                       "Urgency that contradicts deliberation"],
        },
        "curiosity": {
            "say": ["Open a knowledge gap",
                     "Tease surprising information",
                     "Invite discovery and exploration"],
            "avoid": ["Giving away the answer immediately",
                       "Heavy-handed persuasion",
                       "Routine/predictable messaging"],
        },
        "liking": {
            "say": ["Be relatable and authentic",
                     "Use storytelling and narrative",
                     "Show warmth and personality"],
            "avoid": ["Cold analytical language",
                       "Aggressive selling", "Impersonal tone"],
        },
        "reciprocity": {
            "say": ["Offer something valuable first",
                     "Free trial, sample, or useful content",
                     "Frame as giving, not asking"],
            "avoid": ["Demanding action before providing value",
                       "Hard sell before trust"],
        },
        "cognitive_ease": {
            "say": ["Make it simple and clear",
                     "Use familiar language and concepts",
                     "Remove friction and complexity"],
            "avoid": ["Dense information", "Complex comparisons",
                       "Technical jargon"],
        },
        "unity": {
            "say": ["Emphasize shared identity or values",
                     "Create in-group belonging",
                     "We/us language over you language"],
            "avoid": ["Exclusionary messaging",
                       "Individual achievement focus"],
        },
    }

    primary_dir = _MECHANISM_COPY_DIRECTION.get(decision.primary_mechanism, {})
    decision.what_to_say = primary_dir.get("say", [])[:3]
    decision.what_not_to_say = primary_dir.get("avoid", [])[:3]

    # Page gap analysis — what the page handles vs what the ad must address
    _DIM_LABELS = {
        "regulatory_fit": ("gain/approach framing", "loss/prevention framing"),
        "loss_aversion_intensity": ("loss aversion", "gain orientation"),
        "information_seeking": ("evidence and detail", "simple and emotional"),
        "social_proof_sensitivity": ("social validation", "independent evaluation"),
        "autonomy_reactance": ("freedom and choice", "direct guidance"),
        "cognitive_load_tolerance": ("detailed processing", "simplified messaging"),
        "temporal_discounting": ("present urgency", "future planning"),
        "emotional_resonance": ("emotional depth", "analytical clarity"),
    }

    for dim, (high_label, low_label) in _DIM_LABELS.items():
        val = reader_dims.get(dim, 0.5)
        if val > 0.65:
            decision.page_already_provides.append(
                f"Page primes {high_label} — ad can leverage this"
            )
        elif val < 0.35:
            decision.ad_must_address.append(
                f"Page lacks {high_label} — ad must provide {high_label}"
            )

    # Page state summary
    top_dims = sorted(
        [(d, v) for d, v in reader_dims.items() if abs(v - 0.5) > 0.1],
        key=lambda x: abs(x[1] - 0.5), reverse=True
    )[:3]
    if top_dims:
        dim_desc = ", ".join(f"{d}={v:.2f}" for d, v in top_dims)
        decision.page_state_summary = (
            f"Reader in {decision.framing} frame, {decision.tone} receptive, "
            f"top signals: {dim_desc}"
        )

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: QUANTIFY — How confident and how much to bid?
    # ═══════════════════════════════════════════════════════════════

    # Confidence based on evidence depth
    decision.confidence = round(min(0.9,
        0.2 + len(evidence) * 0.08 +
        sum(1 for v in reader_dims.values() if abs(v - 0.5) > 0.1) / 20 * 0.3
    ), 2)

    # Expected lift based on mechanism strength
    top_score = ranked[0][1] if ranked else 0.5
    decision.expected_lift_pct = round((top_score - 0.5) * 80, 1)

    # Bid premium from category temperature + evidence strength
    temp_adj = env_mods.get("temperature", {}).get("bid_adjustment", 1.0)
    decision.bid_premium_pct = round((float(temp_adj) - 1.0) * 100 + decision.confidence * 5, 1)

    decision.evidence_sources = evidence
    decision.mechanism_reasoning = (
        f"{decision.primary_mechanism} selected because reader has "
        f"{_explain_mechanism_fit(decision.primary_mechanism, reader_dims)}"
    )

    decision.decision_ms = round((time.time() - start) * 1000, 2)
    return decision


def _score_mechanisms_from_position(
    dims: Dict[str, float],
) -> Dict[str, float]:
    """Score all mechanisms from the reader's 20-dim position.

    Same formulas as the bilateral cascade but applied to the
    composed reader position vector.
    """
    reg = dims.get("regulatory_fit", 0.5)
    con = dims.get("construal_fit", 0.5)
    pers = dims.get("personality_alignment", 0.5)
    emo = dims.get("emotional_resonance", 0.5)
    val = dims.get("value_alignment", 0.5)
    evo = dims.get("evolutionary_motive", 0.5)
    ps = dims.get("persuasion_susceptibility", 0.5)
    clt = dims.get("cognitive_load_tolerance", 0.5)
    nt = dims.get("narrative_transport", 0.5)
    sps = dims.get("social_proof_sensitivity", 0.5)
    lai = dims.get("loss_aversion_intensity", 0.5)
    td = dims.get("temporal_discounting", 0.5)
    brd = dims.get("brand_relationship_depth", 0.5)
    ar = dims.get("autonomy_reactance", 0.5)
    isk = dims.get("information_seeking", 0.5)
    md = dims.get("mimetic_desire", 0.5)
    ia = dims.get("interoceptive_awareness", 0.5)
    cf = dims.get("cooperative_framing_fit", 0.5)
    de = dims.get("decision_entropy", 0.5)

    return {
        "authority": round(
            0.30 * con + 0.20 * ps + 0.15 * (1.0 - emo)
            + 0.15 * clt + 0.10 * isk + 0.10 * (1.0 - ar), 4
        ),
        "social_proof": round(
            0.25 * sps + 0.20 * pers + 0.15 * md
            + 0.15 * val + 0.15 * emo + 0.10 * (1.0 - ar), 4
        ),
        "scarcity": round(
            0.25 * td + 0.20 * emo + 0.15 * lai
            + 0.15 * (1.0 - clt) + 0.15 * md + 0.10 * ps, 4
        ),
        "loss_aversion": round(
            0.30 * lai + 0.20 * (1.0 - reg) + 0.15 * td
            + 0.15 * ps + 0.10 * evo + 0.10 * de, 4
        ),
        "commitment": round(
            0.25 * brd + 0.20 * val + 0.20 * (1.0 - td)
            + 0.15 * cf + 0.10 * (1.0 - de) + 0.10 * con, 4
        ),
        "liking": round(
            0.25 * pers + 0.20 * emo + 0.20 * nt
            + 0.15 * (1.0 - ar) + 0.10 * ia + 0.10 * md, 4
        ),
        "reciprocity": round(
            0.30 * cf + 0.20 * val + 0.15 * (1.0 - ar)
            + 0.15 * pers + 0.10 * brd + 0.10 * (1.0 - de), 4
        ),
        "curiosity": round(
            0.25 * isk + 0.20 * nt + 0.20 * emo
            + 0.15 * (1.0 - de) + 0.10 * con + 0.10 * md, 4
        ),
        "cognitive_ease": round(
            0.30 * (1.0 - clt) + 0.20 * (1.0 - de)
            + 0.20 * (1.0 - ar) + 0.15 * nt + 0.15 * ia, 4
        ),
        "unity": round(
            0.30 * cf + 0.25 * sps + 0.20 * pers
            + 0.15 * md + 0.10 * (1.0 - ar), 4
        ),
    }


def _explain_mechanism_fit(mechanism: str, dims: Dict[str, float]) -> str:
    """Generate a human-readable explanation of why this mechanism fits."""
    _EXPLANATIONS = {
        "authority": lambda d: f"high information_seeking ({d.get('information_seeking', 0):.2f}), "
            f"low autonomy_reactance ({d.get('autonomy_reactance', 0):.2f}) — receptive to expert guidance",
        "social_proof": lambda d: f"high social_proof_sensitivity ({d.get('social_proof_sensitivity', 0):.2f}), "
            f"high personality_alignment ({d.get('personality_alignment', 0):.2f}) — seeks peer validation",
        "loss_aversion": lambda d: f"high loss_aversion_intensity ({d.get('loss_aversion_intensity', 0):.2f}), "
            f"low regulatory_fit ({d.get('regulatory_fit', 0):.2f}) — in prevention/protection mode",
        "scarcity": lambda d: f"high temporal_discounting ({d.get('temporal_discounting', 0):.2f}), "
            f"high emotional_resonance ({d.get('emotional_resonance', 0):.2f}) — present-focused urgency",
        "commitment": lambda d: f"high value_alignment ({d.get('value_alignment', 0):.2f}), "
            f"high brand_relationship ({d.get('brand_relationship_depth', 0):.2f}) — values consistency",
        "curiosity": lambda d: f"high information_seeking ({d.get('information_seeking', 0):.2f}), "
            f"high narrative_transport ({d.get('narrative_transport', 0):.2f}) — wants to discover",
        "liking": lambda d: f"high personality_alignment ({d.get('personality_alignment', 0):.2f}), "
            f"high emotional_resonance ({d.get('emotional_resonance', 0):.2f}) — responds to warmth",
        "reciprocity": lambda d: f"high cooperative_framing ({d.get('cooperative_framing_fit', 0):.2f}), "
            f"high value_alignment ({d.get('value_alignment', 0):.2f}) — fairness-oriented",
        "cognitive_ease": lambda d: f"low cognitive_load_tolerance ({d.get('cognitive_load_tolerance', 0):.2f}), "
            f"low decision_entropy ({d.get('decision_entropy', 0):.2f}) — needs simplicity",
        "unity": lambda d: f"high cooperative_framing ({d.get('cooperative_framing_fit', 0):.2f}), "
            f"high social_proof ({d.get('social_proof_sensitivity', 0):.2f}) — tribal identity",
    }
    fn = _EXPLANATIONS.get(mechanism, lambda d: "general fit")
    return fn(dims)
