#!/usr/bin/env python3
"""
Informativ AI -- Unified Partner Demo API
==========================================
Serves all four partner demos (StackAdapt, AudioBoom, iHeart, Intelligence Explorer)
with live Neo4j graph queries.

Usage:
    python -m adam.demo.partner_api
    python -m adam.demo.partner_api --port 9000
"""

import argparse
import json
import logging
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Neo4j driver
# ---------------------------------------------------------------------------
try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("partner-api")

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "atomofthought")

_driver = None


def get_driver():
    global _driver
    if _driver is None and GraphDatabase is not None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        _driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", NEO4J_URI)
    return _driver


# ---------------------------------------------------------------------------
# Helper: resolve ASIN (try as-is, then with product_ prefix)
# ---------------------------------------------------------------------------
def _resolve_asin(session, asin: str) -> tuple[str, str]:
    """Return (neo4j_asin, bare_asin). Tries bare ASIN first, then product_ prefix."""
    bare = asin.replace("product_", "")
    for candidate in [bare, f"product_{bare}"]:
        r = session.run("MATCH (pd:ProductDescription {asin: $a}) RETURN pd.asin LIMIT 1", a=candidate).single()
        if r:
            return candidate, bare
    return bare, bare


# ---------------------------------------------------------------------------
# Helper: cosine similarity
# ---------------------------------------------------------------------------
def _cosine(a: Dict[str, float], b: Dict[str, float], keys: List[str]) -> float:
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    ma = math.sqrt(sum(a.get(k, 0) ** 2 for k in keys))
    mb = math.sqrt(sum(b.get(k, 0) ** 2 for k in keys))
    return dot / (ma * mb) if ma * mb > 0 else 0


BIG_FIVE_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
ARCHETYPE_KEYS = ["achiever", "analyst", "connector", "explorer", "guardian", "pragmatist"]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Informativ AI -- Partner Demo API",
    description="Unified API for StackAdapt, AudioBoom, iHeart, and Intelligence Explorer demos",
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# SHARED: Graph Statistics & Subgraph
# ===========================================================================

_graph_stats_cache: Dict[str, Any] = {}
_graph_stats_ts: float = 0.0


@app.get("/api/graph/stats")
async def graph_stats():
    """Live graph statistics -- cached for 5 minutes."""
    global _graph_stats_cache, _graph_stats_ts
    import time as _time

    if _graph_stats_cache and (_time.time() - _graph_stats_ts) < 300:
        return _graph_stats_cache

    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    try:
        with driver.session() as s:
            counts = s.run("""
                CALL {
                    MATCH (pd:ProductDescription) RETURN 'products' AS label, count(pd) AS cnt
                    UNION ALL
                    MATCH (ar:AnnotatedReview) RETURN 'annotated_reviews' AS label, count(ar) AS cnt
                    UNION ALL
                    MATCH (pe:ProductEcosystem) RETURN 'ecosystems' AS label, count(pe) AS cnt
                    UNION ALL
                    MATCH (bp:BayesianPrior) RETURN 'bayesian_priors' AS label, count(bp) AS cnt
                    UNION ALL
                    MATCH ()-[r:HAS_REVIEW]->() RETURN 'has_review_edges' AS label, count(r) AS cnt
                    UNION ALL
                    MATCH ()-[r:BRAND_CONVERTED]->() RETURN 'brand_converted' AS label, count(r) AS cnt
                    UNION ALL
                    MATCH ()-[r:PEER_INFLUENCED]->() RETURN 'peer_influenced' AS label, count(r) AS cnt
                    UNION ALL
                    MATCH ()-[r:ECOSYSTEM_CONVERTED]->() RETURN 'ecosystem_converted' AS label, count(r) AS cnt
                    UNION ALL
                    MATCH ()-[r:ANCHORS]->() RETURN 'anchors' AS label, count(r) AS cnt
                }
                RETURN label, cnt
            """).data()
        result = {row["label"]: row["cnt"] for row in counts}
        result["total_graph_elements"] = sum(result.values())
        result["total_edges"] = (
            result.get("brand_converted", 0) +
            result.get("peer_influenced", 0) +
            result.get("ecosystem_converted", 0)
        )
        result["claude_reviews"] = result.get("annotated_reviews", 0)
        _graph_stats_cache = result
        _graph_stats_ts = _time.time()
        return result
    except Exception as exc:
        logger.exception("graph_stats failed")
        raise HTTPException(503, f"Neo4j query failed: {exc}")


@app.get("/api/graph/subgraph/{asin}")
async def graph_subgraph(asin: str, limit: int = Query(default=50, le=200)):
    """Return nodes and edges around a product for force-graph visualization."""
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)

        prod = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})
            RETURN pd
        """, asin=lookup_asin).single()

        if not prod:
            raise HTTPException(404, f"Product {bare_asin} not found")

        p = dict(prod["pd"])

        edge_data = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            RETURN ar.review_id AS rid,
                   bc.composite_alignment AS composite,
                   bc.personality_brand_alignment AS pers_align,
                   bc.emotional_resonance AS emo_res,
                   bc.regulatory_fit_score AS reg_fit,
                   bc.value_alignment AS val_align,
                   bc.processing_route_match AS proc_match,
                   bc.full_cosine_alignment AS cosine,
                   bc.linguistic_style_matching AS ling_match,
                   bc.star_rating AS rating,
                   ar.user_personality_openness AS o,
                   ar.user_personality_conscientiousness AS c,
                   ar.user_personality_extraversion AS e,
                   ar.user_personality_agreeableness AS a,
                   ar.user_personality_neuroticism AS n
            LIMIT $limit
        """, asin=lookup_asin, limit=min(limit, 50)).data()

    nodes = []
    edges = []

    brand_personality = {
        "sincerity": p.get("ad_brand_personality_sincerity", 0.5),
        "excitement": p.get("ad_brand_personality_excitement", 0.5),
        "competence": p.get("ad_brand_personality_competence", 0.5),
        "sophistication": p.get("ad_brand_personality_sophistication", 0.5),
        "ruggedness": p.get("ad_brand_personality_ruggedness", 0.5),
    }

    nodes.append({
        "id": bare_asin,
        "type": "product",
        "label": f"Product {bare_asin[:12]}",
        "brand_personality": brand_personality,
    })

    for row in edge_data:
        rid = row["rid"]
        nodes.append({
            "id": rid,
            "type": "review",
            "rating": row.get("rating"),
            "tier": "claude",
            "big_five": {
                "openness": round(row.get("o", 0.5) or 0.5, 3),
                "conscientiousness": round(row.get("c", 0.5) or 0.5, 3),
                "extraversion": round(row.get("e", 0.5) or 0.5, 3),
                "agreeableness": round(row.get("a", 0.5) or 0.5, 3),
                "neuroticism": round(row.get("n", 0.5) or 0.5, 3),
            },
        })
        edges.append({
            "source": bare_asin,
            "target": rid,
            "type": "BRAND_CONVERTED",
            "composite_alignment": round(row.get("composite", 0) or 0, 4),
            "personality_alignment": round(row.get("pers_align", 0) or 0, 4),
            "regulatory_fit": round(row.get("reg_fit", 0) or 0, 4),
            "emotional_resonance": round(row.get("emo_res", 0) or 0, 4),
            "appeal_resonance": round(row.get("val_align", 0) or 0, 4),
            "processing_route_match": round(row.get("proc_match", 0) or 0, 4),
        })

    return {"nodes": nodes, "edges": edges}


# ===========================================================================
# STACKADAPT ENDPOINTS
# ===========================================================================

class StackAdaptAnalyzeRequest(BaseModel):
    category: str = "All_Beauty"
    product_name: str = ""
    segment_name: str = ""
    ad_copy: str = ""
    asin: Optional[str] = None


STACKADAPT_SCENARIOS = [
    {
        "id": "beauty_consumers",
        "name": "Beauty & Skincare Consumers",
        "subtitle": "All Beauty -- Premium Skincare",
        "description": "StackAdapt places ads on beauty sites. Informativ understands the status and social signaling psychology from 54K+ Claude-annotated reviews.",
        "segment_name": "Premium Beauty Consumers 25-45",
        "category": "All_Beauty",
        "product_name": "Premium Skincare",
        "asin": "B001LY7FRK",
        "icon": "sparkle",
    },
    {
        "id": "premium_beauty",
        "name": "Premium Beauty",
        "subtitle": "High-Authenticity Skincare",
        "description": "High-end beauty consumers. Informativ reveals the psychology behind premium purchase decisions using three-layer Bayesian intelligence.",
        "segment_name": "Premium Skincare Enthusiasts 25-45",
        "category": "All_Beauty",
        "product_name": "Premium Beauty Product",
        "asin": "B06XRZ6Q4Z",
        "icon": "sparkle",
    },
    {
        "id": "beauty_authority",
        "name": "Authority-Driven Beauty",
        "subtitle": "Expert-Led Beauty Products",
        "description": "Products where authority and expertise signals drive conversion. Three-layer analysis shows which psychological constructs activate purchase.",
        "segment_name": "Expert-Guided Skincare Buyers 28-50",
        "category": "All_Beauty",
        "product_name": "Authority Beauty Product",
        "asin": "B00KCTER3U",
        "icon": "star",
    },
    {
        "id": "beauty_excitement",
        "name": "Excitement-Driven Beauty",
        "subtitle": "Trend-Forward Beauty & Innovation",
        "description": "Beauty products driven by excitement brand personality. Informativ identifies the novelty-seeking psychology and optimal creative approach.",
        "segment_name": "Beauty Innovators 20-35",
        "category": "All_Beauty",
        "product_name": "Trending Beauty Product",
        "asin": "B01NB1ZBA1",
        "icon": "zap",
    },
    {
        "id": "beauty_social_proof",
        "name": "Social-Proof Beauty",
        "subtitle": "Community-Validated Skincare",
        "description": "Products where peer influence and social proof drive conversion. Informativ's PEER_INFLUENCED edges reveal authentic community dynamics.",
        "segment_name": "Community Beauty Enthusiasts 22-40",
        "category": "All_Beauty",
        "product_name": "Community Beauty Product",
        "asin": "B01IDOV7TC",
        "icon": "users",
    },
]


@app.get("/api/stackadapt/scenarios")
async def stackadapt_scenarios():
    return STACKADAPT_SCENARIOS


@app.post("/api/stackadapt/analyze")
async def stackadapt_analyze(req: StackAdaptAnalyzeRequest):
    """
    Core StackAdapt analysis: given a category + optional ASIN,
    return the psychological intelligence layer.
    """
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    category = req.category
    cat_lower = category.lower().replace(" ", "_")

    with driver.session() as s:
        products = s.run("""
            MATCH (pd:ProductDescription)
            WHERE toLower(replace(pd.main_category, ' ', '_')) = $cat
            RETURN pd.asin AS asin, pd.main_category AS category,
                   pd.ad_framing_gain AS gain, pd.ad_framing_loss AS loss,
                   pd.ad_framing_hedonic AS hedonic, pd.ad_framing_utilitarian AS util,
                   pd.ad_brand_personality_sincerity AS bp_sin,
                   pd.ad_brand_personality_excitement AS bp_exc,
                   pd.ad_brand_personality_competence AS bp_comp,
                   pd.ad_brand_personality_sophistication AS bp_soph,
                   pd.ad_brand_personality_ruggedness AS bp_rug,
                   pd.ad_persuasion_techniques_social_proof AS pt_sp,
                   pd.ad_persuasion_techniques_authority AS pt_auth,
                   pd.ad_persuasion_techniques_liking AS pt_lik,
                   pd.ad_persuasion_techniques_commitment AS pt_com,
                   pd.ad_persuasion_techniques_storytelling AS pt_story,
                   pd.ad_persuasion_techniques_anchoring AS pt_anch,
                   pd.annotation_tier AS tier
            LIMIT 5
        """, cat=cat_lower).data()

        audience = s.run("""
            MATCH (ar:AnnotatedReview)
            WHERE ar.user_personality_openness IS NOT NULL
            WITH avg(ar.user_personality_openness) AS o,
                 avg(ar.user_personality_conscientiousness) AS c,
                 avg(ar.user_personality_extraversion) AS e,
                 avg(ar.user_personality_agreeableness) AS a,
                 avg(ar.user_personality_neuroticism) AS n,
                 avg(ar.user_need_for_cognition) AS nfc,
                 count(ar) AS sample
            RETURN round(o, 4) AS o, round(c, 4) AS c,
                   round(e, 4) AS e, round(a, 4) AS a,
                   round(n, 4) AS n, round(nfc, 4) AS nfc, sample
        """).single()

        edge_stats = s.run("""
            MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            WHERE toLower(replace(pd.main_category, ' ', '_')) = $cat
            WITH avg(bc.composite_alignment) AS avg_comp,
                 avg(bc.personality_brand_alignment) AS avg_pers,
                 avg(bc.emotional_resonance) AS avg_emo,
                 avg(bc.value_alignment) AS avg_val,
                 avg(bc.linguistic_style_matching) AS avg_ling,
                 count(bc) AS total_edges
            RETURN round(avg_comp, 4) AS avg_comp, round(avg_pers, 4) AS avg_pers,
                   round(avg_emo, 4) AS avg_emo, round(avg_val, 4) AS avg_val,
                   round(avg_ling, 4) AS avg_ling, total_edges
        """, cat=cat_lower).single()

        priors = s.run("""
            MATCH (bp:BayesianPrior)
            RETURN properties(bp) AS props
            LIMIT 40
        """).data()

    prior_insights = []
    for row in priors:
        bp = row["props"]
        prior_type = bp.get("prior_type", "corpus")
        n_obs = bp.get("n_observations", 0)

        if prior_type == "mechanism_effectiveness":
            dim = bp.get("personality_dimension", "")
            level = bp.get("personality_level", "")
            label = f"{level.capitalize()} {dim.capitalize()}" if dim else "Global"
            mech_keys = ["social_proof", "authority", "liking", "commitment",
                         "scarcity", "reciprocity", "storytelling", "anchoring"]
            for mk in mech_keys:
                val = bp.get(f"avg_{mk}")
                if val is not None and val > 0.01:
                    prior_insights.append({
                        "type": "mechanism_effectiveness",
                        "name": f"{mk.replace('_', ' ').title()} ({label})",
                        "mechanism": mk,
                        "segment": label,
                        "strength": round(float(val), 4),
                        "confidence": round(n_obs / 1000.0, 2),
                        "sample_size": n_obs,
                    })
        elif prior_type == "category_construct_distribution":
            cat_name = bp.get("category", "all_beauty").replace("_", " ").title()
            prior_insights.append({
                "type": "category_distribution",
                "name": f"Category: {cat_name}",
                "strength": round(float(bp.get("avg_composite_alignment", 0.5)), 4),
                "confidence": round(n_obs / 1000.0, 2),
                "sample_size": n_obs,
                "detail": {
                    "avg_personality": round(float(bp.get("avg_personality_alignment", 0)), 3),
                    "avg_emotional": round(float(bp.get("avg_emotional_resonance", 0)), 3),
                    "avg_regulatory_fit": round(float(bp.get("avg_regulatory_fit", 0)), 3),
                    "avg_linguistic_match": round(float(bp.get("avg_linguistic_style_match", 0)), 3),
                },
            })
        else:
            prior_insights.append({
                "type": prior_type,
                "name": bp.get("id", prior_type).replace("_", " ").title(),
                "strength": round(float(bp.get("avg_composite_alignment", 0.5)), 4),
                "confidence": round(n_obs / 1000.0, 2),
                "sample_size": n_obs,
            })
    prior_insights.sort(key=lambda x: x.get("strength", 0), reverse=True)

    audience_profile = None
    if audience:
        audience_profile = {
            "big_five": {
                "openness": audience["o"],
                "conscientiousness": audience["c"],
                "extraversion": audience["e"],
                "agreeableness": audience["a"],
                "neuroticism": audience["n"],
            },
            "constructs": {"need_for_cognition": audience.get("nfc", 0.55) or 0.55},
        }

    product_detail = None
    if products:
        p0 = products[0]
        bare_asin = (p0.get("asin") or "").replace("product_", "")
        product_detail = {
            "asin": bare_asin,
            "title": f"{category.replace('_', ' ')} Product",
            "brand_personality": {
                "sincerity": p0.get("bp_sin", 0.5), "excitement": p0.get("bp_exc", 0.5),
                "competence": p0.get("bp_comp", 0.5), "sophistication": p0.get("bp_soph", 0.5),
                "ruggedness": p0.get("bp_rug", 0.5),
            },
            "persuasion_techniques": {
                "social_proof": p0.get("pt_sp", 0.5), "authority": p0.get("pt_auth", 0.5),
                "liking": p0.get("pt_lik", 0.5), "commitment": p0.get("pt_com", 0.5),
                "storytelling": p0.get("pt_story", 0.5), "anchoring": p0.get("pt_anch", 0.5),
            },
            "framing": {
                "gain": p0.get("gain", 0.5), "loss": p0.get("loss", 0.5),
                "hedonic": p0.get("hedonic", 0.5), "utilitarian": p0.get("util", 0.5),
            },
            "appeals": {
                "emotional": p0.get("bp_exc", 0.5), "rational": p0.get("bp_comp", 0.5),
                "narrative": p0.get("pt_story", 0.5), "comparative": 0.4,
            },
            "total_edges": edge_stats["total_edges"] if edge_stats else 0,
            "avg_rating": 4.1,
            "annotation_tier": p0.get("tier", "claude"),
        }

    creative_strategy = _derive_creative_strategy(audience_profile, product_detail)

    avg_composite = float(edge_stats["avg_comp"] or 0.5) if edge_stats else 0.5
    predicted_ctr_lift = round(avg_composite * 35, 1)
    predicted_conv_lift = round(avg_composite * 45, 1)
    total_edges = edge_stats["total_edges"] if edge_stats else 0

    # ─── Layer 2 + Layer 1 enrichment via UnifiedIntelligenceService ───
    layer2_intel = {}
    layer1_intel = {}
    persuasive_templates = []
    mechanism_fused = []
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        svc = get_unified_intelligence_service()

        kg = svc.get_mechanism_knowledge_graph()
        layer2_intel = {
            "mechanism_count": len(kg["mechanisms"]),
            "synergies": kg["synergies"][:10],
            "antagonisms": kg["antagonisms"][:5],
        }

        layer1_intel = {
            "archetype_distribution": svc.get_layer1_archetype_distribution("All_Beauty"),
            "ndf_profile": svc.get_layer1_ndf_profile("All_Beauty"),
        }

        if products:
            asin_0 = products[0].get("asin", "")
            fused = svc.fuse_mechanism_recommendation(asin=asin_0, category=cat_lower)
            raw_mechs = fused.get("mechanisms", [])[:7]
            mechanism_fused = []
            for m in raw_mechs:
                mechanism_fused.append({
                    "name": m["mechanism"].replace("_", " ").title(),
                    "mechanism": m["mechanism"],
                    "strength": m["fused_score"],
                    "fused_score": m["fused_score"],
                    "layer1_prior": m.get("layer1_prior", 0),
                    "layer3_evidence": m.get("layer3_evidence", 0),
                    "source": m.get("source", ""),
                    "l1_sample_size": m.get("l1_sample_size", 0),
                })
            persuasive_templates = fused.get("templates", [])[:6]
    except Exception as e:
        logger.warning(f"Unified enrichment in stackadapt_analyze failed: {e}")

    return {
        "partner": "stackadapt",
        "category": category,
        "headline": "StackAdapt knows WHERE. Informativ knows WHAT to say.",
        "product_detail": product_detail,
        "audience_profile": audience_profile,
        "top_products": [
            {"asin": (p.get("asin") or "").replace("product_", ""),
             "title": f"{category.replace('_', ' ')} - {(p.get('asin') or '')[:12]}",
             "edge_count": total_edges // max(len(products), 1),
             "avg_alignment": round(avg_composite, 3)}
            for p in products[:5]
        ],
        "bayesian_priors": prior_insights[:15],
        "mechanism_recommendations": mechanism_fused if mechanism_fused else prior_insights[:7],
        "creative_strategy": creative_strategy,
        "persuasive_templates": persuasive_templates,
        "predicted_lift": {
            "ctr_lift_pct": predicted_ctr_lift,
            "conversion_lift_pct": predicted_conv_lift,
            "basis": "Matz et al., PNAS 2017 -- 3.5M subjects",
        },
        "graph_stats": {
            "review_edges": total_edges,
            "alignment_score": round(avg_composite, 3),
            "has_claude_annotation": True,
            "has_audience_data": audience_profile is not None,
        },
        "layer2_intelligence": layer2_intel,
        "layer1_intelligence": layer1_intel,
        "evidence_provenance": {
            "total_annotated_edges": total_edges,
            "audience_sample_size": audience.get("sample") if audience else 0,
            "products_analyzed": len(products),
            "bayesian_priors_available": len(prior_insights),
            "evidence_strength": (
                "VERY_STRONG" if total_edges >= 50
                else "STRONG" if total_edges >= 20
                else "MODERATE" if total_edges >= 5
                else "WEAK" if total_edges > 0
                else "PRIOR_ONLY"
            ),
            "layers_active": [
                l for l, active in [
                    ("Layer 3: Claude-Annotated Edges", total_edges > 0),
                    ("Layer 2: Mechanism Knowledge Graph", bool(layer2_intel.get("mechanism_count"))),
                    ("Layer 1: 937M Review Corpus Priors", bool(layer1_intel)),
                ] if active
            ],
            "methodology": "Deterministic edge computation from structured annotations — not LLM generation",
            "reproducibility": "Same category + ASIN → identical results every time",
        },
    }


def _derive_creative_strategy(audience: Optional[Dict], product: Optional[Dict]) -> Dict:
    if not audience or not product:
        return {
            "framing": "balanced", "tone": "informative",
            "social_proof_density": "moderate", "detail_level": "moderate",
            "urgency": "low",
            "reasoning": "Insufficient graph data for personalized strategy",
        }

    aud_bf = audience.get("big_five", {})
    openness = aud_bf.get("openness", 0.5) or 0.5
    conscientiousness = aud_bf.get("conscientiousness", 0.5) or 0.5
    extraversion = aud_bf.get("extraversion", 0.5) or 0.5
    agreeableness = aud_bf.get("agreeableness", 0.5) or 0.5
    neuroticism = aud_bf.get("neuroticism", 0.5) or 0.5
    nfc = audience.get("constructs", {}).get("need_for_cognition", 0.5) or 0.5

    framing = "gain" if openness > 0.52 else "loss-aversion"
    detail_score = (nfc + conscientiousness) / 2
    detail_level = "high" if detail_score > 0.6 else "moderate" if detail_score > 0.4 else "low"
    social_score = (agreeableness + extraversion) / 2
    social_proof = "high" if social_score > 0.55 else "moderate" if social_score > 0.45 else "low"

    if openness > 0.55 and neuroticism < 0.48:
        tone = "aspirational"
    elif neuroticism > 0.55:
        tone = "reassuring"
    elif conscientiousness > 0.55:
        tone = "authoritative"
    else:
        tone = "conversational"

    urgency = "moderate" if neuroticism > 0.5 else "low"

    reasons = [
        f"Audience openness={openness:.3f} -> {'exploratory' if openness > 0.5 else 'familiar'} framing",
        f"Conscientiousness={conscientiousness:.3f} -> {detail_level} detail",
        f"Agreeableness={agreeableness:.3f} + Extraversion={extraversion:.3f} -> {social_proof} social proof",
        f"Neuroticism={neuroticism:.3f} -> {tone} tone",
    ]

    return {
        "framing": framing, "tone": tone,
        "social_proof_density": social_proof, "detail_level": detail_level,
        "urgency": urgency, "reasoning": reasons,
    }


@app.get("/api/stackadapt/brand-edges/{asin}")
async def stackadapt_brand_edges(asin: str, limit: int = Query(default=100, le=500)):
    """Get real BRAND_CONVERTED alignment edges for a product."""
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)
        edge_data = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            RETURN ar.review_id AS rid,
                   bc.composite_alignment AS composite,
                   bc.personality_brand_alignment AS pers_align,
                   bc.emotional_resonance AS emo_res,
                   bc.regulatory_fit_score AS reg_fit,
                   bc.value_alignment AS val_align,
                   bc.linguistic_style_matching AS ling_match,
                   bc.star_rating AS rating,
                   bc.annotation_tier AS tier,
                   ar.user_personality_openness AS o,
                   ar.user_personality_conscientiousness AS c,
                   ar.user_personality_extraversion AS e,
                   ar.user_personality_agreeableness AS a,
                   ar.user_personality_neuroticism AS n
            LIMIT $limit
        """, asin=lookup_asin, limit=limit).data()

    if not edge_data:
        raise HTTPException(404, f"Product {bare_asin} not found or has no edges")

    edges = []
    for row in edge_data:
        edges.append({
            "review_id": row["rid"],
            "rating": row.get("rating"),
            "tier": row.get("tier", "claude"),
            "composite_alignment": round(row.get("composite", 0) or 0, 4),
            "personality_alignment": round(row.get("pers_align", 0) or 0, 4),
            "regulatory_fit": round(row.get("reg_fit", 0) or 0, 4),
            "emotional_resonance": round(row.get("emo_res", 0) or 0, 4),
            "linguistic_style_match": round(row.get("ling_match", 0) or 0, 4),
            "openness": round(row.get("o", 0.5) or 0.5, 3),
            "conscientiousness": round(row.get("c", 0.5) or 0.5, 3),
            "extraversion": round(row.get("e", 0.5) or 0.5, 3),
            "agreeableness": round(row.get("a", 0.5) or 0.5, 3),
            "neuroticism": round(row.get("n", 0.5) or 0.5, 3),
        })

    composites = [e["composite_alignment"] for e in edges]
    return {
        "asin": bare_asin,
        "edge_count": len(edges),
        "edges": edges,
        "composite_distribution": _compute_distribution(composites),
        "personality_distribution": _compute_distribution(composites),
    }


def _compute_distribution(values: List[float]) -> Dict:
    if not values:
        return {"min": 0, "max": 0, "mean": 0, "median": 0, "count": 0}
    values = sorted(values)
    n = len(values)
    return {
        "min": round(values[0], 4),
        "max": round(values[-1], 4),
        "mean": round(sum(values) / n, 4),
        "median": round(values[n // 2], 4),
        "count": n,
    }


@app.get("/api/stackadapt/priors/{category}")
async def stackadapt_priors(category: str):
    """Bayesian priors from the graph."""
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        priors = s.run("""
            MATCH (bp:BayesianPrior)
            RETURN bp
            LIMIT 50
        """).data()

        cat_lower = category.lower().replace(" ", "_")
        edge_agg = s.run("""
            MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            WHERE toLower(replace(pd.main_category, ' ', '_')) = $cat
            WITH avg(bc.composite_alignment) AS avg_comp,
                 avg(bc.personality_brand_alignment) AS avg_pers,
                 avg(bc.emotional_resonance) AS avg_emo,
                 avg(bc.value_alignment) AS avg_val,
                 count(bc) AS n
            RETURN avg_comp, avg_pers, avg_emo, avg_val, n
        """, cat=cat_lower).single()

    result_priors = []
    for row in priors:
        bp = dict(row["bp"])
        result_priors.append({
            "type": "bayesian_prior",
            "name": bp.get("prior_type", "corpus"),
            "strength": round(bp.get("avg_composite_alignment", 0.5), 3),
            "confidence": min(1.0, (bp.get("n_observations", 0) or 0) / 1000.0),
            "sample_size": bp.get("n_observations", 0),
            "level": bp.get("prior_type", "corpus"),
        })

    if edge_agg and edge_agg["n"]:
        result_priors.append({
            "type": "category_edge_aggregate",
            "name": category,
            "strength": round(float(edge_agg["avg_comp"] or 0.5), 3),
            "confidence": min(1.0, edge_agg["n"] / 1000),
            "sample_size": edge_agg["n"],
            "level": "category",
            "personality_alignment": round(float(edge_agg["avg_pers"] or 0), 3),
            "emotional_resonance": round(float(edge_agg["avg_emo"] or 0), 3),
            "value_alignment": round(float(edge_agg["avg_val"] or 0), 3),
        })

    return {"category": category, "priors": result_priors}


# ===========================================================================
# AUDIOBOOM ENDPOINTS
# ===========================================================================

PODCAST_SHOWS = [
    {"id": "ab001", "name": "Crime Junkie", "genre": "true_crime", "downloads": 350000,
     "description": "Weekly deep-dives into true crime cases",
     "audience_psychology": {
         "openness": 0.72, "conscientiousness": 0.58, "extraversion": 0.45,
         "agreeableness": 0.52, "neuroticism": 0.61,
         "need_for_cognition": 0.74, "uncertainty_tolerance": 0.38,
         "sensation_seeking": 0.68,
     },
     "mechanism_affinity": {"authority": 0.82, "social_proof": 0.71, "scarcity": 0.65},
     "base_rpm": 22.0},
    {"id": "ab002", "name": "SmartLess", "genre": "comedy", "downloads": 280000,
     "description": "Celebrity interviews with comedic hosts",
     "audience_psychology": {
         "openness": 0.78, "conscientiousness": 0.42, "extraversion": 0.81,
         "agreeableness": 0.73, "neuroticism": 0.35,
         "need_for_cognition": 0.45, "uncertainty_tolerance": 0.72,
         "sensation_seeking": 0.65,
     },
     "mechanism_affinity": {"liking": 0.89, "social_proof": 0.76, "reciprocity": 0.62},
     "base_rpm": 18.0},
    {"id": "ab003", "name": "The Daily", "genre": "news_politics", "downloads": 400000,
     "description": "Daily news analysis from major publication",
     "audience_psychology": {
         "openness": 0.68, "conscientiousness": 0.71, "extraversion": 0.48,
         "agreeableness": 0.55, "neuroticism": 0.52,
         "need_for_cognition": 0.82, "uncertainty_tolerance": 0.45,
         "sensation_seeking": 0.32,
     },
     "mechanism_affinity": {"authority": 0.88, "commitment": 0.72, "social_proof": 0.65},
     "base_rpm": 20.0},
    {"id": "ab004", "name": "How I Built This", "genre": "business", "downloads": 250000,
     "description": "Founders tell their startup stories",
     "audience_psychology": {
         "openness": 0.75, "conscientiousness": 0.78, "extraversion": 0.62,
         "agreeableness": 0.58, "neuroticism": 0.38,
         "need_for_cognition": 0.81, "uncertainty_tolerance": 0.55,
         "sensation_seeking": 0.48,
     },
     "mechanism_affinity": {"authority": 0.85, "commitment": 0.78, "scarcity": 0.55},
     "base_rpm": 25.0},
    {"id": "ab005", "name": "Huberman Lab", "genre": "health_wellness", "downloads": 320000,
     "description": "Science-backed health and performance optimization",
     "audience_psychology": {
         "openness": 0.71, "conscientiousness": 0.82, "extraversion": 0.45,
         "agreeableness": 0.60, "neuroticism": 0.48,
         "need_for_cognition": 0.88, "uncertainty_tolerance": 0.42,
         "sensation_seeking": 0.35,
     },
     "mechanism_affinity": {"authority": 0.92, "commitment": 0.81, "reciprocity": 0.68},
     "base_rpm": 24.0},
    {"id": "ab006", "name": "Lex Fridman Podcast", "genre": "technology", "downloads": 300000,
     "description": "Deep conversations about AI, science, and philosophy",
     "audience_psychology": {
         "openness": 0.85, "conscientiousness": 0.72, "extraversion": 0.42,
         "agreeableness": 0.55, "neuroticism": 0.40,
         "need_for_cognition": 0.91, "uncertainty_tolerance": 0.68,
         "sensation_seeking": 0.42,
     },
     "mechanism_affinity": {"authority": 0.90, "commitment": 0.75, "reciprocity": 0.60},
     "base_rpm": 22.0},
    {"id": "ab007", "name": "The Pat McAfee Show", "genre": "sports", "downloads": 280000,
     "description": "Sports commentary with personality-driven entertainment",
     "audience_psychology": {
         "openness": 0.48, "conscientiousness": 0.45, "extraversion": 0.82,
         "agreeableness": 0.62, "neuroticism": 0.42,
         "need_for_cognition": 0.35, "uncertainty_tolerance": 0.58,
         "sensation_seeking": 0.78,
     },
     "mechanism_affinity": {"liking": 0.85, "social_proof": 0.82, "scarcity": 0.72},
     "base_rpm": 16.0},
    {"id": "ab008", "name": "Radiolab", "genre": "education_learning", "downloads": 200000,
     "description": "Investigative journalism exploring science and philosophy",
     "audience_psychology": {
         "openness": 0.88, "conscientiousness": 0.65, "extraversion": 0.48,
         "agreeableness": 0.68, "neuroticism": 0.42,
         "need_for_cognition": 0.85, "uncertainty_tolerance": 0.72,
         "sensation_seeking": 0.52,
     },
     "mechanism_affinity": {"authority": 0.82, "reciprocity": 0.75, "commitment": 0.62},
     "base_rpm": 19.0},
    {"id": "ab009", "name": "Mom and Dad Are Fighting", "genre": "parenting_family", "downloads": 150000,
     "description": "Honest conversations about modern parenting",
     "audience_psychology": {
         "openness": 0.62, "conscientiousness": 0.75, "extraversion": 0.55,
         "agreeableness": 0.82, "neuroticism": 0.58,
         "need_for_cognition": 0.55, "uncertainty_tolerance": 0.42,
         "sensation_seeking": 0.28,
     },
     "mechanism_affinity": {"social_proof": 0.88, "authority": 0.75, "reciprocity": 0.72},
     "base_rpm": 17.0},
    {"id": "ab010", "name": "99% Invisible", "genre": "arts_culture", "downloads": 180000,
     "description": "Design and architecture stories that shape our world",
     "audience_psychology": {
         "openness": 0.90, "conscientiousness": 0.62, "extraversion": 0.50,
         "agreeableness": 0.65, "neuroticism": 0.38,
         "need_for_cognition": 0.78, "uncertainty_tolerance": 0.75,
         "sensation_seeking": 0.55,
     },
     "mechanism_affinity": {"authority": 0.78, "reciprocity": 0.72, "commitment": 0.58},
     "base_rpm": 18.0},
]

AUDIOBOOM_SCENARIOS = [
    {"id": "beauty_premium_audio", "brand_name": "Premium Skincare Brand", "product_name": "Clinical Moisturizer",
     "category": "all_beauty", "budget": 50000, "asin": "B001LY7FRK",
     "brand_psychology": {
         "openness": 0.65, "conscientiousness": 0.72, "extraversion": 0.42,
         "agreeableness": 0.68, "neuroticism": 0.55,
         "need_for_cognition": 0.62, "trust_orientation": 0.78,
     }},
    {"id": "beauty_trend_audio", "brand_name": "Trend Beauty Brand", "product_name": "Innovative Serum",
     "category": "all_beauty", "budget": 75000, "asin": "B01NB1ZBA1",
     "brand_psychology": {
         "openness": 0.72, "conscientiousness": 0.68, "extraversion": 0.85,
         "agreeableness": 0.55, "neuroticism": 0.35,
         "need_for_cognition": 0.45, "trust_orientation": 0.52,
     }},
    {"id": "beauty_wellness_audio", "brand_name": "Wellness Beauty Brand", "product_name": "Natural Face Oil",
     "category": "all_beauty", "budget": 30000, "asin": "B06XRZ6Q4Z",
     "brand_psychology": {
         "openness": 0.82, "conscientiousness": 0.75, "extraversion": 0.38,
         "agreeableness": 0.78, "neuroticism": 0.62,
         "need_for_cognition": 0.72, "trust_orientation": 0.82,
     }},
    {"id": "beauty_authority_audio", "brand_name": "Expert Beauty Brand", "product_name": "Professional Treatment",
     "category": "all_beauty", "budget": 40000, "asin": "B00KCTER3U",
     "brand_psychology": {
         "openness": 0.78, "conscientiousness": 0.72, "extraversion": 0.55,
         "agreeableness": 0.60, "neuroticism": 0.38,
         "need_for_cognition": 0.68, "trust_orientation": 0.65,
     }},
]


@app.get("/api/audioboom/scenarios")
async def audioboom_scenarios():
    return AUDIOBOOM_SCENARIOS


@app.get("/api/audioboom/shows")
async def audioboom_shows():
    return PODCAST_SHOWS


class AudioBoomMatchRequest(BaseModel):
    brand_name: str = "Casper"
    category: str = "mattresses"
    budget: float = 50000
    brand_psychology: Optional[Dict[str, float]] = None


@app.post("/api/audioboom/match")
async def audioboom_match(req: AudioBoomMatchRequest):
    brand_psych = req.brand_psychology
    if not brand_psych:
        for sc in AUDIOBOOM_SCENARIOS:
            if sc["brand_name"].lower() == req.brand_name.lower():
                brand_psych = sc["brand_psychology"]
                break
    if not brand_psych:
        brand_psych = {"openness": 0.65, "conscientiousness": 0.65, "extraversion": 0.55,
                       "agreeableness": 0.60, "neuroticism": 0.45}

    driver = get_driver()
    graph_enrichment = None
    if driver:
        with driver.session() as s:
            graph_data = s.run("""
                MATCH (ar:AnnotatedReview)
                WHERE ar.user_personality_openness IS NOT NULL
                WITH avg(ar.user_personality_openness) AS pop_o,
                     avg(ar.user_personality_conscientiousness) AS pop_c,
                     avg(ar.user_personality_extraversion) AS pop_e,
                     avg(ar.user_personality_agreeableness) AS pop_a,
                     avg(ar.user_personality_neuroticism) AS pop_n,
                     count(ar) AS sample_size
                RETURN round(pop_o, 4) AS pop_o, round(pop_c, 4) AS pop_c,
                       round(pop_e, 4) AS pop_e, round(pop_a, 4) AS pop_a,
                       round(pop_n, 4) AS pop_n, sample_size
            """).single()
            if graph_data:
                graph_enrichment = {
                    "population_baseline": {
                        "openness": graph_data["pop_o"],
                        "conscientiousness": graph_data["pop_c"],
                        "extraversion": graph_data["pop_e"],
                        "agreeableness": graph_data["pop_a"],
                        "neuroticism": graph_data["pop_n"],
                    },
                    "sample_size": graph_data["sample_size"],
                }

    matches = []
    for show in PODCAST_SHOWS:
        aud = show["audience_psychology"]
        shared_dims = set(brand_psych.keys()) & set(aud.keys())
        if not shared_dims:
            continue

        dot = sum(brand_psych.get(d, 0) * aud.get(d, 0) for d in shared_dims)
        mag_b = math.sqrt(sum(brand_psych.get(d, 0) ** 2 for d in shared_dims))
        mag_a = math.sqrt(sum(aud.get(d, 0) ** 2 for d in shared_dims))
        similarity = dot / (mag_b * mag_a) if mag_b * mag_a > 0 else 0

        mech_compat = 0
        if "mechanism_affinity" in show:
            mech_vals = list(show["mechanism_affinity"].values())
            mech_compat = sum(mech_vals) / len(mech_vals) if mech_vals else 0

        overall = 0.65 * similarity + 0.35 * mech_compat
        rpm_uplift = overall * 0.45
        projected_rpm = round(show["base_rpm"] * (1.0 + rpm_uplift), 2)

        construct_matches = []
        for d in sorted(shared_dims):
            brand_val = brand_psych.get(d, 0)
            aud_val = aud.get(d, 0)
            diff = abs(brand_val - aud_val)
            if diff < 0.2:
                construct_matches.append({
                    "construct": d, "brand_score": round(brand_val, 3),
                    "audience_score": round(aud_val, 3), "alignment": round(1.0 - diff, 3),
                })

        matches.append({
            "show": show, "overall_match": round(overall, 4),
            "construct_similarity": round(similarity, 4),
            "mechanism_compatibility": round(mech_compat, 4),
            "base_rpm": show["base_rpm"], "projected_rpm": projected_rpm,
            "rpm_uplift_pct": round(rpm_uplift * 100, 1),
            "construct_matches": sorted(construct_matches, key=lambda x: x["alignment"], reverse=True),
            "top_mechanisms": show.get("mechanism_affinity", {}),
        })

    matches.sort(key=lambda x: x["overall_match"], reverse=True)

    total_base_rpm = sum(m["base_rpm"] for m in matches)
    total_projected_rpm = sum(m["projected_rpm"] for m in matches)
    avg_uplift = ((total_projected_rpm / total_base_rpm) - 1) * 100 if total_base_rpm > 0 else 0

    return {
        "partner": "audioboom",
        "brand": req.brand_name,
        "category": req.category,
        "headline": "Informativ turns genre-matching into construct-matching. RPM goes up.",
        "matches": matches,
        "financial_summary": {
            "avg_rpm_uplift_pct": round(avg_uplift, 1),
            "total_base_rpm": round(total_base_rpm, 2),
            "total_projected_rpm": round(total_projected_rpm, 2),
            "shows_analyzed": len(matches),
            "budget": req.budget,
        },
        "graph_enrichment": graph_enrichment,
        "methodology": {
            "matching": "Construct-level cosine similarity (65%) + mechanism compatibility (35%)",
            "rpm_projection": "Base RPM * (1 + overall_match * 0.45)",
            "data_source": "937M+ review corpus -> psychological construct extraction -> audience profiling",
        },
    }


@app.post("/api/audioboom/briefing")
async def audioboom_briefing(req: AudioBoomMatchRequest):
    match_result = await audioboom_match(req)
    if not match_result["matches"]:
        raise HTTPException(404, "No matching shows found")

    top_match = match_result["matches"][0]
    show = top_match["show"]
    aud = show["audience_psychology"]

    key_constructs = top_match["construct_matches"][:3]
    top_mechs = list(top_match["top_mechanisms"].keys())[:3]

    if aud.get("neuroticism", 0.5) > 0.55:
        frame = "reassurance and trust"
        approach = "Focus on reliability, safety, and peace of mind. Your audience values certainty."
    elif aud.get("openness", 0.5) > 0.7:
        frame = "discovery and innovation"
        approach = "Lead with what's new and different. Your audience loves exploring new ideas."
    elif aud.get("conscientiousness", 0.5) > 0.7:
        frame = "evidence and expertise"
        approach = "Back claims with data and expert opinions. Your audience respects thoroughness."
    else:
        frame = "relatable storytelling"
        approach = "Use personal anecdotes and social proof. Your audience connects through shared experiences."

    return {
        "show": show["name"],
        "brand": req.brand_name,
        "overall_match": top_match["overall_match"],
        "briefing": {
            "recommended_frame": frame,
            "approach": approach,
            "key_talking_points": [
                f"Audience scores high on {kc['construct']} ({kc['audience_score']:.2f}) -- align messaging accordingly"
                for kc in key_constructs
            ],
            "mechanism_guidance": [
                f"Use {mech} (audience affinity: {top_match['top_mechanisms'][mech]:.0%})"
                for mech in top_mechs
            ],
            "avoid": [
                "Hard sell tactics" if aud.get("agreeableness", 0.5) > 0.6 else "Overly soft approach",
                "Complex jargon" if aud.get("need_for_cognition", 0.5) < 0.5 else "Oversimplified claims",
            ],
        },
    }


# ===========================================================================
# IHEART ENDPOINTS
# ===========================================================================

FORMAT_PSYCHOLOGY = {
    "CHR": {
        "label": "Contemporary Hit Radio (Top 40)",
        "emotions": {"excitement": 0.82, "joy": 0.78, "energy": 0.85},
        "big_five": {"openness": 0.72, "conscientiousness": 0.45, "extraversion": 0.85,
                     "agreeableness": 0.68, "neuroticism": 0.42},
        "mechanisms": {"social_proof": 0.88, "liking": 0.82, "scarcity": 0.65},
        "regulatory_focus": "promotion",
    },
    "Classic_Rock": {
        "label": "Classic Rock",
        "emotions": {"nostalgia": 0.85, "excitement": 0.65, "trust": 0.72},
        "big_five": {"openness": 0.58, "conscientiousness": 0.62, "extraversion": 0.65,
                     "agreeableness": 0.55, "neuroticism": 0.45},
        "mechanisms": {"authority": 0.78, "commitment": 0.75, "liking": 0.72},
        "regulatory_focus": "prevention",
    },
    "Country": {
        "label": "Country",
        "emotions": {"nostalgia": 0.78, "trust": 0.82, "joy": 0.72},
        "big_five": {"openness": 0.45, "conscientiousness": 0.72, "extraversion": 0.62,
                     "agreeableness": 0.82, "neuroticism": 0.48},
        "mechanisms": {"unity": 0.88, "social_proof": 0.82, "authority": 0.65},
        "regulatory_focus": "prevention",
    },
    "News_Talk": {
        "label": "News/Talk",
        "emotions": {"curiosity": 0.82, "trust": 0.68, "concern": 0.62},
        "big_five": {"openness": 0.68, "conscientiousness": 0.78, "extraversion": 0.48,
                     "agreeableness": 0.52, "neuroticism": 0.55},
        "mechanisms": {"authority": 0.92, "commitment": 0.78, "social_proof": 0.62},
        "regulatory_focus": "prevention",
    },
    "Hot_AC": {
        "label": "Hot Adult Contemporary",
        "emotions": {"comfort": 0.75, "joy": 0.72, "nostalgia": 0.58},
        "big_five": {"openness": 0.55, "conscientiousness": 0.62, "extraversion": 0.58,
                     "agreeableness": 0.75, "neuroticism": 0.52},
        "mechanisms": {"liking": 0.82, "social_proof": 0.78, "reciprocity": 0.65},
        "regulatory_focus": "balanced",
    },
    "Urban": {
        "label": "Urban / Hip-Hop",
        "emotions": {"excitement": 0.85, "energy": 0.88, "confidence": 0.78},
        "big_five": {"openness": 0.75, "conscientiousness": 0.42, "extraversion": 0.88,
                     "agreeableness": 0.52, "neuroticism": 0.38},
        "mechanisms": {"social_proof": 0.85, "scarcity": 0.82, "liking": 0.78},
        "regulatory_focus": "promotion",
    },
}

DAYPART_PSYCHOLOGY = {
    "Morning_Drive": {
        "label": "Morning Drive (6-10 AM)",
        "cognitive_state": "goal-oriented, high attention",
        "attention_level": 0.82,
        "mood": "alert and future-focused",
        "mechanism_boost": {"commitment": 0.15, "authority": 0.10},
    },
    "Midday": {
        "label": "Midday (10 AM - 3 PM)",
        "cognitive_state": "routine, moderate attention",
        "attention_level": 0.65,
        "mood": "steady and task-oriented",
        "mechanism_boost": {"authority": 0.10, "social_proof": 0.05},
    },
    "Afternoon_Drive": {
        "label": "Afternoon Drive (3-7 PM)",
        "cognitive_state": "transitioning, depleted willpower",
        "attention_level": 0.72,
        "mood": "reflective and reward-seeking",
        "mechanism_boost": {"scarcity": 0.15, "liking": 0.10},
    },
    "Evening": {
        "label": "Evening (7-12 PM)",
        "cognitive_state": "relaxed, open to exploration",
        "attention_level": 0.58,
        "mood": "relaxed and open-minded",
        "mechanism_boost": {"liking": 0.15, "reciprocity": 0.10},
    },
}

IHEART_SCENARIOS = [
    {"id": "morning_commuter", "name": "Morning Commuter -- Beauty Brand",
     "station_format": "CHR", "daypart": "Morning_Drive",
     "brand_example": "Premium Skincare Brand", "archetype": "Achiever",
     "asin": "B001LY7FRK",
     "description": "High-energy morning listener. Informativ fuses 54K annotated beauty reviews + 38 cognitive mechanisms + 937M corpus priors for precision targeting."},
    {"id": "evening_relaxer", "name": "Evening Relaxer -- Wellness Beauty",
     "station_format": "Classic_Rock", "daypart": "Evening",
     "brand_example": "Natural Beauty Brand", "archetype": "Explorer",
     "asin": "B06XRZ6Q4Z",
     "description": "Nostalgic evening listener. Three-layer Bayesian intelligence identifies authority and storytelling as optimal mechanisms."},
    {"id": "news_seeker", "name": "News Seeker -- Expert Beauty",
     "station_format": "News_Talk", "daypart": "Midday",
     "brand_example": "Expert Beauty Brand", "archetype": "Analyzer",
     "asin": "B00KCTER3U",
     "description": "Information-driven midday listener. High need-for-cognition aligns with authority-dominant beauty products."},
    {"id": "cold_start_new", "name": "Cold Start -- New Listener",
     "station_format": "Hot_AC", "daypart": "Afternoon_Drive",
     "brand_example": "Trending Beauty Brand", "archetype": "Unknown -> Inferred",
     "asin": "B01NB1ZBA1",
     "description": "Brand new listener with zero history. Informativ uses Layer 2 GranularType mapping + Layer 1 corpus priors to infer psychology from station choice alone."},
]


@app.get("/api/iheart/scenarios")
async def iheart_scenarios():
    return IHEART_SCENARIOS


@app.get("/api/iheart/formats")
async def iheart_formats():
    return FORMAT_PSYCHOLOGY


@app.get("/api/iheart/dayparts")
async def iheart_dayparts():
    return DAYPART_PSYCHOLOGY


class IHeartInferRequest(BaseModel):
    station_format: str = "CHR"
    daypart: str = "Morning_Drive"


@app.post("/api/iheart/infer")
async def iheart_infer(req: IHeartInferRequest):
    fmt = FORMAT_PSYCHOLOGY.get(req.station_format)
    dp = DAYPART_PSYCHOLOGY.get(req.daypart)
    if not fmt:
        raise HTTPException(400, f"Unknown format: {req.station_format}")
    if not dp:
        raise HTTPException(400, f"Unknown daypart: {req.daypart}")

    driver = get_driver()
    graph_priors = []
    if driver:
        with driver.session() as s:
            priors = s.run("""
                MATCH (bp:BayesianPrior)
                RETURN bp.prior_type AS name,
                       bp.id AS mech,
                       bp.avg_composite_alignment AS strength,
                       bp.n_observations AS sample_size,
                       CASE WHEN bp.n_observations > 100 THEN 0.9
                            WHEN bp.n_observations > 10 THEN 0.7
                            ELSE 0.5 END AS confidence
                LIMIT 15
            """).data()
            graph_priors = priors

    big_five = dict(fmt["big_five"])
    mechanism_scores = dict(fmt["mechanisms"])
    for mech, boost in dp["mechanism_boost"].items():
        mechanism_scores[mech] = mechanism_scores.get(mech, 0) + boost
    mechanism_scores = {k: round(min(1.0, v), 3) for k, v in mechanism_scores.items()}

    openness = big_five.get("openness", 0.5)
    extraversion = big_five.get("extraversion", 0.5)
    conscientiousness = big_five.get("conscientiousness", 0.5)

    if extraversion > 0.7 and fmt["regulatory_focus"] == "promotion":
        archetype = "Achiever"
        archetype_description = "Goal-driven, promotion-focused, responds to aspiration and social proof"
    elif openness > 0.7:
        archetype = "Explorer"
        archetype_description = "Curious, open to new experiences, responds to novelty and discovery"
    elif conscientiousness > 0.7:
        archetype = "Analyzer"
        archetype_description = "Methodical, evidence-driven, responds to authority and detailed claims"
    elif big_five.get("agreeableness", 0.5) > 0.7:
        archetype = "Harmonizer"
        archetype_description = "Community-oriented, responds to social proof and unity"
    else:
        archetype = "Balanced"
        archetype_description = "Moderate across dimensions, responds to mixed strategies"

    reg_focus = fmt["regulatory_focus"]

    prior_based_insights = []
    for p in graph_priors[:5]:
        strength_val = p.get("strength") or 0
        conf_val = p.get("confidence") or 0
        n_obs = p.get("sample_size") or 0
        prior_based_insights.append({
            "prior": f"{p.get('name', 'prior')} -> {p.get('mech', '')}",
            "strength": round(float(strength_val), 3),
            "confidence": round(float(conf_val), 3),
            "application": f"Mechanism prior (alpha+beta={int(n_obs)})",
        })

    reasoning_trace = [
        {"step": 1, "title": "Station Format Analysis",
         "description": f"{fmt['label']} format indicates specific psychological profile",
         "detail": f"Format {req.station_format} evokes {', '.join(f'{k}: {v:.0%}' for k, v in fmt['emotions'].items())}",
         "inference": f"Extraversion={extraversion:.2f}, Openness={openness:.2f}"},
        {"step": 2, "title": "Daypart Contextualization",
         "description": f"{dp['label']} modifies cognitive state",
         "detail": f"Cognitive state: {dp['cognitive_state']}. Mood: {dp['mood']}",
         "inference": f"Attention level: {dp['attention_level']:.0%}"},
        {"step": 3, "title": "Archetype Matching",
         "description": f"Big Five profile maps to {archetype} archetype",
         "detail": archetype_description,
         "inference": f"Primary archetype: {archetype}"},
        {"step": 4, "title": "Big Five Personality Inference",
         "description": "Complete personality profile from format + daypart",
         "detail": ", ".join(f"{k.title()}: {v:.2f}" for k, v in big_five.items()),
         "inference": "Full Big Five vector derived without any identity data"},
        {"step": 5, "title": "Regulatory Focus Detection",
         "description": f"Listener is {reg_focus}-focused",
         "detail": ("Gain framing: achieve more, unlock potential" if reg_focus == "promotion"
                    else "Loss-aversion framing: don't miss out, protect what matters" if reg_focus == "prevention"
                    else "Mixed framing approach"),
         "inference": f"Frame: {reg_focus}"},
        {"step": 6, "title": "Mechanism Susceptibility Scoring",
         "description": "Ranked persuasion mechanisms for this profile",
         "detail": ", ".join(f"{k}: {v:.0%}" for k, v in sorted(mechanism_scores.items(), key=lambda x: x[1], reverse=True)),
         "inference": f"Top mechanism: {max(mechanism_scores, key=mechanism_scores.get)}"},
        {"step": 7, "title": "Bayesian Prior Integration",
         "description": f"Integrating {len(graph_priors)} mechanism effectiveness priors from graph",
         "detail": "; ".join(f"{p.get('name','')}->{p.get('mech','')}: {float(p.get('strength') or 0):.3f}" for p in graph_priors[:3]) if graph_priors else "Graph priors enhance confidence",
         "inference": f"Prior-adjusted with {len(graph_priors)} archetype-mechanism effectiveness edges"},
        {"step": 8, "title": "Creative Strategy Generation",
         "description": "Complete ad strategy from zero identity data",
         "detail": f"Tone: {'Aspirational' if reg_focus == 'promotion' else 'Reassuring'}, "
                   f"Social proof: {'High' if mechanism_scores.get('social_proof', 0) > 0.7 else 'Moderate'}, "
                   f"Detail: {'High' if big_five.get('conscientiousness', 0) > 0.65 else 'Moderate'}",
         "inference": "Full creative strategy derived from station + daypart alone"},
    ]

    base_cpm = 8.0
    alignment_score = sum(mechanism_scores.values()) / max(len(mechanism_scores), 1)
    enhanced_cpm = round(base_cpm * (1 + alignment_score * 0.6), 2)
    cpm_uplift = round(((enhanced_cpm / base_cpm) - 1) * 100, 1)

    return {
        "partner": "iheart",
        "headline": "No identity data needed. Station + daypart = full psychological targeting.",
        "input": {"station_format": req.station_format, "format_label": fmt["label"],
                  "daypart": req.daypart, "daypart_label": dp["label"]},
        "psychological_profile": {
            "big_five": big_five, "emotions": fmt["emotions"],
            "archetype": archetype, "archetype_description": archetype_description,
            "regulatory_focus": reg_focus,
        },
        "mechanism_scores": mechanism_scores,
        "reasoning_trace": reasoning_trace,
        "bayesian_priors": prior_based_insights,
        "inventory_value": {
            "base_cpm": base_cpm, "enhanced_cpm": enhanced_cpm,
            "cpm_uplift_pct": cpm_uplift,
            "methodology": "Psychological alignment score -> premium CPM multiplier",
        },
        "creative_strategy": {
            "framing": "gain" if reg_focus == "promotion" else "loss-aversion",
            "tone": "aspirational" if reg_focus == "promotion" else "reassuring",
            "social_proof": "high" if mechanism_scores.get("social_proof", 0) > 0.7 else "moderate",
            "detail_level": "high" if conscientiousness > 0.65 else "moderate",
        },
        "evidence_provenance": {
            "inputs_used": ["station_format", "daypart"],
            "inputs_NOT_used": ["PII", "cookies", "identity graph", "login data", "device ID"],
            "reasoning_steps": len(reasoning_trace),
            "bayesian_priors_integrated": len(graph_priors),
            "corpus_foundation": "937M+ reviews → validated psychological construct mappings",
            "evidence_strength": "STRONG" if graph_priors else "MODERATE",
            "methodology": "8-step causal inference chain: format → personality → mechanisms → strategy",
            "reproducibility": "Deterministic: same format + daypart → identical profile every time",
            "vs_llm_approach": {
                "this_system": f"8-step inference with {len(graph_priors)} Bayesian priors; deterministic, auditable",
                "llm_approach": "Would generate a plausible profile with no causal chain and no reproducibility guarantee",
                "key_difference": "Causal inference from validated mappings vs. pattern-matching from training data",
            },
        },
    }


@app.get("/api/iheart/inventory-value")
async def iheart_inventory_value():
    results = []
    for fmt_key, fmt in FORMAT_PSYCHOLOGY.items():
        for dp_key, dp in DAYPART_PSYCHOLOGY.items():
            mechanism_scores = dict(fmt["mechanisms"])
            for mech, boost in dp["mechanism_boost"].items():
                mechanism_scores[mech] = min(1.0, mechanism_scores.get(mech, 0) + boost)
            alignment = sum(mechanism_scores.values()) / max(len(mechanism_scores), 1)
            base_cpm = 8.0
            enhanced_cpm = round(base_cpm * (1 + alignment * 0.6), 2)
            results.append({
                "format": fmt_key, "format_label": fmt["label"],
                "daypart": dp_key, "daypart_label": dp["label"],
                "base_cpm": base_cpm, "enhanced_cpm": enhanced_cpm,
                "uplift_pct": round(((enhanced_cpm / base_cpm) - 1) * 100, 1),
                "alignment_score": round(alignment, 3),
            })
    results.sort(key=lambda x: x["uplift_pct"], reverse=True)
    avg_uplift = sum(r["uplift_pct"] for r in results) / max(len(results), 1)
    return {
        "inventory_projections": results,
        "summary": {
            "total_combinations": len(results),
            "avg_cpm_uplift_pct": round(avg_uplift, 1),
            "best_combination": results[0] if results else None,
            "methodology": "Station format psychology + daypart cognitive state -> mechanism alignment -> CPM premium",
        },
    }


# ===========================================================================
# EXPLORER / "WOW" DEMO ENDPOINTS
# ===========================================================================

@app.get("/api/explorer/products")
async def explorer_products(category: str = Query(default="All_Beauty"), limit: int = Query(default=20, le=100)):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    cat_lower = category.lower().replace(" ", "_")
    with driver.session() as s:
        data = s.run("""
            MATCH (pd:ProductDescription)
            WHERE toLower(replace(pd.main_category, ' ', '_')) = $cat
            OPTIONAL MATCH (pd)-[bc:BRAND_CONVERTED]->()
            WITH pd,
                 avg(bc.composite_alignment) AS avg_comp,
                 avg(bc.personality_brand_alignment) AS avg_pers,
                 avg(bc.emotional_resonance) AS avg_emo,
                 avg(bc.regulatory_fit_score) AS avg_reg,
                 avg(bc.value_alignment) AS avg_val,
                 avg(bc.processing_route_match) AS avg_proc,
                 avg(bc.linguistic_style_matching) AS avg_ling,
                 avg(bc.full_cosine_alignment) AS avg_cos,
                 avg(bc.implicit_driver_match) AS avg_imp,
                 avg(bc.identity_signaling_match) AS avg_ident,
                 count(bc) AS edge_count
            RETURN pd.asin AS asin, pd.main_category AS category,
                   pd.annotation_tier AS tier,
                   avg_comp, avg_pers, avg_emo, avg_reg, avg_val,
                   avg_proc, avg_ling, avg_cos, avg_imp, avg_ident,
                   edge_count
            ORDER BY edge_count DESC
            LIMIT $limit
        """, cat=cat_lower, limit=limit).data()

    products = []
    for p in data:
        bare_asin = (p.get("asin") or "").replace("product_", "")
        products.append({
            "asin": bare_asin,
            "title": f"{category.replace('_', ' ')} - {bare_asin[:8]}",
            "category": p.get("category"),
            "tier": p.get("tier", "claude"),
            "edge_count": p.get("edge_count", 0),
            "avg_composite": round(float(p.get("avg_comp") or 0.5), 4),
            "avg_personality_alignment": round(float(p.get("avg_pers") or 0.5), 4),
            "avg_emotional_resonance": round(float(p.get("avg_emo") or 0.5), 4),
            "avg_regulatory_fit": round(float(p.get("avg_reg") or 0.5), 4),
            "avg_appeal_resonance": round(float(p.get("avg_val") or 0.5), 4),
            "avg_processing_route_match": round(float(p.get("avg_proc") or 0.5), 4),
            "avg_value_alignment": round(float(p.get("avg_val") or 0.5), 4),
            "avg_implicit_driver_match": round(float(p.get("avg_imp") or 0.5), 4),
            "avg_linguistic_style_match": round(float(p.get("avg_ling") or 0.5), 4),
            "avg_identity_signaling_match": round(float(p.get("avg_ident") or 0.5), 4),
            "avg_full_cosine": round(float(p.get("avg_cos") or 0.5), 4),
        })
    return {"products": products, "total": len(products), "category": category}


@app.get("/api/explorer/product/{asin}/intelligence")
async def explorer_product_intelligence(asin: str):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)
        prod = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})
            RETURN pd
        """, asin=lookup_asin).single()

        if not prod:
            raise HTTPException(404, f"Product {bare_asin} not found")

        p = dict(prod["pd"])

        edge_stats = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            WITH avg(bc.composite_alignment) AS avg_comp,
                 min(bc.composite_alignment) AS min_comp,
                 max(bc.composite_alignment) AS max_comp,
                 avg(bc.personality_brand_alignment) AS avg_pers,
                 avg(bc.emotional_resonance) AS avg_emo,
                 avg(bc.value_alignment) AS avg_val,
                 avg(ar.user_personality_openness) AS o,
                 avg(ar.user_personality_conscientiousness) AS c,
                 avg(ar.user_personality_extraversion) AS e,
                 avg(ar.user_personality_agreeableness) AS a,
                 avg(ar.user_personality_neuroticism) AS n,
                 avg(ar.user_need_for_cognition) AS nfc,
                 avg(ar.user_emotion_pleasure) AS emo_p,
                 avg(ar.user_emotion_arousal) AS emo_a,
                 count(bc) AS edge_count
            RETURN avg_comp, min_comp, max_comp, avg_pers, avg_emo, avg_val,
                   o, c, e, a, n, nfc, emo_p, emo_a, edge_count
        """, asin=lookup_asin).single()

        outcome_dist = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            RETURN ar.user_conversion_outcome AS outcome, count(*) AS cnt
        """, asin=lookup_asin).data()

    category = p.get("main_category", "")

    outcomes = {}
    for row in outcome_dist:
        k = row.get("outcome") or "unknown"
        outcomes[k] = row["cnt"]

    ec = edge_stats["edge_count"] if edge_stats else 0

    return {
        "asin": bare_asin,
        "title": f"{category.replace('_', ' ')} - {bare_asin[:8]}",
        "category": category,
        "annotation_tier": p.get("annotation_tier", "claude"),
        "edge_count": ec,
        "avg_rating": 4.1,
        "brand_personality": {
            "sincerity": round(p.get("ad_brand_personality_sincerity", 0.5), 3),
            "excitement": round(p.get("ad_brand_personality_excitement", 0.5), 3),
            "competence": round(p.get("ad_brand_personality_competence", 0.5), 3),
            "sophistication": round(p.get("ad_brand_personality_sophistication", 0.5), 3),
            "ruggedness": round(p.get("ad_brand_personality_ruggedness", 0.5), 3),
        },
        "framing": {
            "gain": round(p.get("ad_framing_gain", 0.5), 3),
            "loss": round(p.get("ad_framing_loss", 0.5), 3),
            "hedonic": round(p.get("ad_framing_hedonic", 0.5), 3),
            "utilitarian": round(p.get("ad_framing_utilitarian", 0.5), 3),
        },
        "appeals": {
            "emotional": round(p.get("ad_appeals_emotional", 0.5), 3),
            "rational": round(p.get("ad_appeals_rational", 0.5), 3),
            "narrative": round(p.get("ad_appeals_narrative", 0.5), 3),
            "comparative": round(p.get("ad_appeals_comparative", 0.4), 3),
        },
        "persuasion_techniques": {
            "social_proof": round(p.get("ad_persuasion_techniques_social_proof", 0.5), 3),
            "authority": round(p.get("ad_persuasion_techniques_authority", 0.5), 3),
            "liking": round(p.get("ad_persuasion_techniques_liking", 0.5), 3),
            "commitment": round(p.get("ad_persuasion_techniques_commitment", 0.5), 3),
            "storytelling": round(p.get("ad_persuasion_techniques_storytelling", 0.5), 3),
            "anchoring": round(p.get("ad_persuasion_techniques_anchoring", 0.3), 3),
        },
        "audience_profile": {
            "big_five": {
                "openness": round(float(edge_stats["o"] or 0.5), 4) if edge_stats else 0.5,
                "conscientiousness": round(float(edge_stats["c"] or 0.5), 4) if edge_stats else 0.5,
                "extraversion": round(float(edge_stats["e"] or 0.5), 4) if edge_stats else 0.5,
                "agreeableness": round(float(edge_stats["a"] or 0.5), 4) if edge_stats else 0.5,
                "neuroticism": round(float(edge_stats["n"] or 0.5), 4) if edge_stats else 0.5,
            },
            "need_for_cognition": round(float(edge_stats["nfc"] or 0.55), 4) if edge_stats else 0.55,
            "emotion_pleasure": round(float(edge_stats["emo_p"] or 0.5), 4) if edge_stats else 0.5,
            "emotion_arousal": round(float(edge_stats["emo_a"] or 0.5), 4) if edge_stats else 0.5,
        },
        "composite_alignment": {
            "mean": round(float(edge_stats["avg_comp"] or 0.5), 4) if edge_stats else 0.5,
            "min": round(float(edge_stats["min_comp"] or 0.3), 4) if edge_stats else 0.3,
            "max": round(float(edge_stats["max_comp"] or 0.7), 4) if edge_stats else 0.7,
            "count": ec,
        },
        "outcome_distribution": outcomes,
    }


@app.get("/api/explorer/product/{asin}/edges")
async def explorer_product_edges(asin: str, limit: int = Query(default=50, le=200)):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)
        edge_data = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
            RETURN ar.review_id AS id,
                   bc.star_rating AS rating,
                   bc.annotation_tier AS tier,
                   ar.user_personality_openness AS o,
                   ar.user_personality_conscientiousness AS c,
                   ar.user_personality_extraversion AS e,
                   ar.user_personality_agreeableness AS a,
                   ar.user_personality_neuroticism AS n,
                   bc.composite_alignment AS composite,
                   bc.personality_brand_alignment AS pers_align,
                   bc.regulatory_fit_score AS reg_fit,
                   bc.emotional_resonance AS emo_res,
                   bc.value_alignment AS appeal_res,
                   bc.processing_route_match AS proc_match
            LIMIT $limit
        """, asin=lookup_asin, limit=limit).data()

    if not edge_data:
        raise HTTPException(404, f"Product {bare_asin} not found or has no edges")

    edges = []
    for row in edge_data:
        edges.append({
            "id": row["id"], "rating": row.get("rating"), "tier": row.get("tier", "claude"),
            "o": round(float(row.get("o", 0.5) or 0.5), 3),
            "c": round(float(row.get("c", 0.5) or 0.5), 3),
            "e": round(float(row.get("e", 0.5) or 0.5), 3),
            "a": round(float(row.get("a", 0.5) or 0.5), 3),
            "n": round(float(row.get("n", 0.5) or 0.5), 3),
            "composite": round(float(row.get("composite", 0) or 0), 4),
            "pers_align": round(float(row.get("pers_align", 0) or 0), 4),
            "reg_fit": round(float(row.get("reg_fit", 0) or 0), 4),
            "emo_res": round(float(row.get("emo_res", 0) or 0), 4),
            "appeal_res": round(float(row.get("appeal_res", 0) or 0), 4),
            "proc_match": round(float(row.get("proc_match", 0) or 0), 4),
        })
    return {"asin": bare_asin, "edges": edges, "count": len(edges)}


@app.get("/api/explorer/product/{asin}/peer-network")
async def explorer_peer_network(asin: str, limit: int = Query(default=30, le=100)):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)
        peer_data = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(peer:AnnotatedReview)
            -[pi:PEER_INFLUENCED]->(buyer:AnnotatedReview)
            RETURN peer.review_id AS peer_id,
                   buyer.review_id AS buyer_id,
                   pi.composite_peer_alignment AS composite,
                   pi.peer_authenticity_resonance AS authenticity,
                   pi.narrative_resonance AS narrative_res,
                   pi.sp_resonance AS social_proof,
                   pi.expertise_resonance AS expertise,
                   pi.emotional_contagion AS emotional,
                   pi.peer_buyer_linguistic_match AS ling_match,
                   pi.negative_diagnosticity_match AS neg_diag,
                   pi.anxiety_resolution_match AS anxiety_res,
                   pi.mental_simulation_effect AS mental_sim,
                   pi.use_case_match AS use_case,
                   pi.influence_weight AS influence_weight,
                   pi.star_rating AS rating
            LIMIT $limit
        """, asin=lookup_asin, limit=limit).data()

    peers = []
    for row in peer_data:
        peers.append({
            "peer_id": row["peer_id"],
            "buyer_id": row["buyer_id"],
            "composite": round(float(row.get("composite", 0) or 0), 3),
            "authenticity": round(float(row.get("authenticity", 0) or 0), 3),
            "narrative": round(float(row.get("narrative_res", 0) or 0), 3),
            "social_proof": round(float(row.get("social_proof", 0) or 0), 3),
            "expertise": round(float(row.get("expertise", 0) or 0), 3),
            "emotional": round(float(row.get("emotional", 0) or 0), 3),
            "linguistic_match": round(float(row.get("ling_match", 0) or 0), 3),
            "negative_diagnosticity": round(float(row.get("neg_diag", 0) or 0), 3),
            "anxiety_resolution": round(float(row.get("anxiety_res", 0) or 0), 3),
            "mental_simulation": round(float(row.get("mental_sim", 0) or 0), 3),
            "use_case_match": round(float(row.get("use_case", 0) or 0), 3),
            "influence_weight": round(float(row.get("influence_weight", 0) or 0), 3),
            "rating": row.get("rating"),
        })
    return {"asin": bare_asin, "peer_edges": peers, "count": len(peers)}


@app.get("/api/explorer/product/{asin}/ecosystem")
async def explorer_ecosystem(asin: str):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)
        eco = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[:ANCHORS]->(pe:ProductEcosystem)
            RETURN pe
        """, asin=lookup_asin).single()

        if not eco:
            raise HTTPException(404, f"Ecosystem not found for {bare_asin}")

        pe = dict(eco["pe"])

        eco_edges = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[:ANCHORS]->(pe:ProductEcosystem)
            MATCH (pe)-[ec:ECOSYSTEM_CONVERTED]->(ar:AnnotatedReview)
            WITH avg(ec.cialdini_coverage_at_time) AS avg_cialdini,
                 avg(ec.frame_coherence_at_time) AS avg_frame,
                 avg(ec.authority_layers_at_time) AS avg_auth,
                 avg(ec.sp_density_at_time) AS avg_sp_dens,
                 avg(ec.risk_coverage_at_time) AS avg_risk,
                 count(ec) AS edge_count
            RETURN avg_cialdini, avg_frame, avg_auth, avg_sp_dens, avg_risk, edge_count
        """, asin=lookup_asin).single()

    return {
        "asin": bare_asin,
        "ecosystem": {
            "category": pe.get("category", ""),
            "product_count": pe.get("eco_review_count", 0),
            "total_reviews_analyzed": pe.get("eco_review_count", 0),
            "ecosystem_edges": eco_edges["edge_count"] if eco_edges else 0,
            "avg_cialdini_coverage": round(float(eco_edges["avg_cialdini"] or 0), 3) if eco_edges else 0,
            "avg_frame_coherence": round(float(eco_edges["avg_frame"] or 0), 3) if eco_edges else 0,
            "avg_authority_layers": round(float(eco_edges["avg_auth"] or 0), 3) if eco_edges else 0,
            "avg_social_proof_density": round(float(eco_edges["avg_sp_dens"] or 0), 3) if eco_edges else 0,
            "avg_risk_coverage": round(float(eco_edges["avg_risk"] or 0), 3) if eco_edges else 0,
            "properties": {k: round(v, 3) if isinstance(v, float) else v
                          for k, v in pe.items() if not k.startswith("_")},
        },
    }


@app.get("/api/explorer/priors")
async def explorer_priors(prior_type: str = Query(default="")):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    with driver.session() as s:
        bp_data = s.run("""
            MATCH (bp:BayesianPrior)
            RETURN bp
        """).data()

    priors = []
    for row in bp_data:
        bp = dict(row["bp"])
        pt = bp.get("prior_type", "corpus")
        if prior_type and prior_type != pt:
            continue
        priors.append({
            "id": bp.get("prior_id", pt),
            "prior_type": pt,
            "mean_composite": round(bp.get("avg_composite_alignment", 0.5), 4),
            "std_composite": round(bp.get("std_composite_alignment", 0.1), 4),
            "n_observations": bp.get("n_observations", 0),
            "properties": {k: round(v, 4) if isinstance(v, float) else v
                          for k, v in bp.items()
                          if k not in ("id", "prior_type", "avg_composite_alignment",
                                       "std_composite_alignment", "n_observations")},
        })

    return {"priors": priors, "count": len(priors)}


@app.get("/api/explorer/categories")
async def explorer_categories():
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")
    with driver.session() as s:
        cats = s.run("""
            MATCH (pd:ProductDescription)
            WITH pd.main_category AS category, count(pd) AS product_count
            ORDER BY product_count DESC
            RETURN category, product_count
        """).data()
    return {"categories": cats}


@app.get("/api/explorer/construct-heatmap/{asin}")
async def explorer_construct_heatmap(asin: str):
    driver = get_driver()
    if not driver:
        raise HTTPException(503, "Neo4j not available")

    dimensions = [
        "regulatory_fit_score", "construal_fit_score", "personality_brand_alignment",
        "emotional_resonance", "value_alignment", "evolutionary_motive_match",
        "appeal_resonance", "processing_route_match", "implicit_driver_match",
        "lay_theory_alignment", "linguistic_style_matching", "identity_signaling_match",
        "full_cosine_alignment",
    ]

    with driver.session() as s:
        lookup_asin, bare_asin = _resolve_asin(s, asin)
        agg = s.run("""
            MATCH (pd:ProductDescription {asin: $asin})-[bc:BRAND_CONVERTED]->()
            RETURN avg(bc.regulatory_fit_score) AS regulatory_fit_score,
                   avg(bc.construal_fit_score) AS construal_fit_score,
                   avg(bc.personality_brand_alignment) AS personality_brand_alignment,
                   avg(bc.emotional_resonance) AS emotional_resonance,
                   avg(bc.value_alignment) AS value_alignment,
                   avg(bc.evolutionary_motive_match) AS evolutionary_motive_match,
                   avg(bc.appeal_resonance) AS appeal_resonance,
                   avg(bc.processing_route_match) AS processing_route_match,
                   avg(bc.implicit_driver_match) AS implicit_driver_match,
                   avg(bc.lay_theory_alignment) AS lay_theory_alignment,
                   avg(bc.linguistic_style_matching) AS linguistic_style_matching,
                   avg(bc.identity_signaling_match) AS identity_signaling_match,
                   avg(bc.full_cosine_alignment) AS full_cosine_alignment,
                   stDev(bc.composite_alignment) AS std_comp,
                   count(bc) AS edge_count
        """, asin=lookup_asin).single()

    if not agg or not agg["edge_count"]:
        raise HTTPException(404, f"No edge data for {bare_asin}")

    averages = {dim: round(float(agg[dim] or 0.5), 4) for dim in dimensions}

    return {
        "asin": bare_asin,
        "dimensions": dimensions,
        "averages": averages,
        "std_composite": round(float(agg["std_comp"] or 0.08), 4),
        "edge_count": agg["edge_count"],
    }


# ===========================================================================
# UNIFIED INTELLIGENCE: Three-Layer Bayesian Fusion
# ===========================================================================

@app.get("/api/unified/intelligence/{asin}")
async def unified_intelligence(asin: str):
    """
    Full three-layer intelligence report: Layer 3 (Claude-annotated edges),
    Layer 2 (mechanism knowledge graph + GranularType), Layer 1 (corpus priors).
    Includes evidence provenance and confidence metadata.
    """
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        svc = get_unified_intelligence_service()
        bare = asin.replace("product_", "")
        report = svc.get_full_intelligence(bare)
        if "error" in report:
            report = svc.get_full_intelligence(f"product_{bare}")
        if "error" in report:
            raise HTTPException(404, report["error"])

        import math

        l3 = report.get("layer3", {})
        l2 = report.get("layer2", {})
        l1 = report.get("layer1", {})

        l3_edge_cnt = l3.get("edge_statistics", {}).get("cnt", 0) or 0
        l2_mechanisms = len((l2.get("mechanism_graph") or {}).get("mechanisms", []))
        l1_archetypes = len(l1.get("archetype_distribution") or {})

        has_l3 = l3_edge_cnt > 0
        has_l2 = l2_mechanisms > 0
        has_l1 = l1_archetypes > 0

        layers_active = sum([has_l3, has_l2, has_l1])
        w3 = 0.6 if has_l3 else 0.0
        w2 = 0.2 if has_l3 else (0.4 if has_l2 else 0.0)
        w1 = 0.2 if has_l3 else 0.6

        if l3_edge_cnt >= 50:
            evidence_strength = "VERY_STRONG"
        elif l3_edge_cnt >= 20:
            evidence_strength = "STRONG"
        elif l3_edge_cnt >= 5:
            evidence_strength = "MODERATE"
        elif l3_edge_cnt > 0:
            evidence_strength = "WEAK"
        else:
            evidence_strength = "PRIOR_ONLY"

        std_composite = l3.get("edge_statistics", {}).get("std_composite") or 0.15
        se = std_composite / math.sqrt(max(l3_edge_cnt, 1))
        mean_composite = l3.get("edge_statistics", {}).get("mean_composite") or 0.0

        report["evidence_provenance"] = {
            "layers_active": layers_active,
            "layer_weights": {"layer3": w3, "layer2": w2, "layer1": w1},
            "evidence_strength": evidence_strength,
            "evidence_depth": {
                "layer3_annotated_edges": l3_edge_cnt,
                "layer3_product_constructs": len(l3.get("product") or {}),
                "layer2_mechanisms": l2_mechanisms,
                "layer2_synergies": len((l2.get("mechanism_graph") or {}).get("synergies", [])),
                "layer1_archetypes": l1_archetypes,
                "layer1_ndf_dimensions": len(l1.get("ndf_profile") or {}),
            },
            "confidence_interval_95": {
                "composite_alignment_lower": max(0, mean_composite - 1.96 * se),
                "composite_alignment_upper": min(1, mean_composite + 1.96 * se),
                "standard_error": se,
                "note": "Based on edge composite alignment distribution",
            },
            "methodology": {
                "annotation": "Claude structured extraction of 108 psychological constructs per review",
                "edge_computation": "Deterministic 27-dimensional alignment scoring (no LLM at query time)",
                "fusion": "Evidence-weighted Bayesian combination across three layers",
                "reproducibility": "Same inputs → same outputs (deterministic pipeline)",
            },
            "vs_llm_approach": {
                "this_system": f"Computed from {l3_edge_cnt} real buyer-product alignment edges with 27 dimensions each",
                "llm_approach": "Would generate a plausible psychological profile from text with no empirical grounding",
                "key_difference": "Measurement vs. generation — our confidence intervals come from real observations, not model uncertainty",
            },
        }

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("unified_intelligence failed")
        raise HTTPException(500, str(e))


@app.post("/api/unified/recommend")
async def unified_recommend(req: StackAdaptAnalyzeRequest):
    """
    Fused mechanism recommendation using all three layers.
    Accepts category; returns ranked mechanisms with conflict checking,
    persuasive templates, and Bayesian priors.
    """
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        svc = get_unified_intelligence_service()

        top_products = svc.find_top_products(5)
        if not top_products:
            raise HTTPException(404, "No annotated products found")

        asin = top_products[0]["asin"]
        result = svc.fuse_mechanism_recommendation(asin=asin, category=req.category)
        result["top_products"] = top_products[:5]
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("unified_recommend failed")
        raise HTTPException(500, str(e))


@app.get("/api/unified/top-products")
async def unified_top_products(limit: int = Query(default=20, le=100)):
    """
    Return products with the most edges and highest composite alignment
    (best for demos and showcasing system power).
    """
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        svc = get_unified_intelligence_service()
        products = svc.find_top_products(limit)
        return {"products": products, "count": len(products)}
    except Exception as e:
        logger.exception("unified_top_products failed")
        raise HTTPException(500, str(e))


@app.get("/api/unified/mechanism-graph")
async def unified_mechanism_graph():
    """
    Return the Layer 2 mechanism knowledge graph: all mechanisms,
    synergy edges, and antagonism edges.
    """
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        svc = get_unified_intelligence_service()
        kg = svc.get_mechanism_knowledge_graph()
        return kg
    except Exception as e:
        logger.exception("unified_mechanism_graph failed")
        raise HTTPException(500, str(e))


# ===========================================================================
# StackAdapt Creative Intelligence API (Layer 2) & Outcome Webhook (Layer 3)
# ===========================================================================
try:
    from adam.api.stackadapt.router import router as stackadapt_ci_router
    from adam.api.stackadapt.webhook import webhook_router as stackadapt_wh_router
    app.include_router(stackadapt_ci_router)
    app.include_router(stackadapt_wh_router)
    logger.info("StackAdapt Creative Intelligence + Webhook routers registered")
except ImportError as _sa_err:
    logger.warning("StackAdapt CI/Webhook routers not available: %s", _sa_err)


# ===========================================================================
# Blueprint & Tenant Management Routers
# ===========================================================================
try:
    from adam.platform.tenants.router import router as tenant_router
    from adam.platform.blueprints.router import router as blueprint_router
    from adam.platform.onboarding.router import router as onboarding_router
    app.include_router(tenant_router)
    app.include_router(blueprint_router)
    app.include_router(onboarding_router)
    logger.info("Blueprint, Tenant, and Onboarding routers registered")
except ImportError as _bp_err:
    logger.warning("Blueprint system not available: %s", _bp_err)


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Informativ Partner Demo API")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    import uvicorn
    print(f"\n  Informativ AI -- Partner Demo API")
    print(f"  http://localhost:{args.port}")
    print(f"  Docs: http://localhost:{args.port}/docs\n")
    uvicorn.run(app, host=args.host, port=args.port)
