"""
Unified Intelligence Service — Three-Layer Bayesian Fusion
==========================================================

Fuses three intelligence layers into a single query interface:

Layer 1 (JSON Priors): 937M review corpus aggregations — archetype distributions,
    mechanism effectiveness matrices, NDF profiles, geo/temporal/price priors.
    Source: data/learning/ingestion_merged_priors.json

Layer 2 (Old Neo4j Schema): 1.9M GranularTypes with 13.4M SUSCEPTIBLE_TO edges,
    38 CognitiveMechanisms with SYNERGIZES_WITH/ANTAGONIZES knowledge graph,
    2.2K PersuasiveTemplates, 12M BrandPriors, 5 BuyerArchetypes.

Layer 3 (New Neo4j Schema): Claude-annotated ProductDescriptions (65 constructs),
    AnnotatedReviews (73 constructs), BRAND_CONVERTED (18+ match dimensions),
    PEER_INFLUENCED (12 dimensions), ECOSYSTEM_CONVERTED (8 dimensions),
    BayesianPriors segmented by Big Five / category / outcome.

The fusion follows a Bayesian hierarchy:
    Layer 1 provides the prior (population-level base rates)
    Layer 2 provides structural intelligence (mechanism interactions, type mapping)
    Layer 3 provides the likelihood (individual-level precision)
    Posterior = weighted combination with evidence scaling
"""

from __future__ import annotations

import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"

PRIORS_PATH = Path("data/learning/ingestion_merged_priors.json")
COLDSTART_PRIORS_PATH = Path("data/learning/complete_coldstart_priors.json")

# GranularType dimension mapping: Layer 3 user properties → Layer 2 type dimensions
DIMENSION_MAPPING = {
    "motivation": {
        "pure_curiosity": lambda u: u.get("user_evolutionary_motives_affiliation", 0) < 0.3
            and u.get("user_personality_openness", 0.5) > 0.6,
        "eager_advancement": lambda u: u.get("user_regulatory_focus_promotion", 0.5) > 0.6,
        "safety_security": lambda u: u.get("user_regulatory_focus_prevention", 0.5) > 0.6,
        "social_belonging": lambda u: u.get("user_evolutionary_motives_affiliation", 0.3) > 0.5,
        "self_expression": lambda u: u.get("user_implicit_drivers_identity_signaling", 0.3) > 0.5,
    },
    "decision_style": {
        "gut_instinct": lambda u: u.get("user_decision_style_impulse", 0.3) > 0.5,
        "careful_analysis": lambda u: u.get("user_need_for_cognition", 0.5) > 0.6,
        "social_validation": lambda u: u.get("user_mechanisms_cited_social_proof", 0.3) > 0.4,
    },
    "regulatory_focus": {
        "eager_advancement": lambda u: u.get("user_regulatory_focus_promotion", 0.5) > 0.55,
        "vigilant_prevention": lambda u: u.get("user_regulatory_focus_prevention", 0.5) > 0.55,
    },
    "emotional_intensity": {
        "high_positive_activation": lambda u: u.get("user_emotion_pleasure", 0.5) > 0.6
            and u.get("user_emotion_arousal", 0.5) > 0.5,
        "low_negative_activation": lambda u: u.get("user_emotion_pleasure", 0.5) < 0.4,
        "measured_balanced": lambda u: 0.4 <= u.get("user_emotion_pleasure", 0.5) <= 0.6,
    },
    "cognitive_load": {
        "minimal_cognitive": lambda u: u.get("user_need_for_cognition", 0.5) < 0.4,
        "moderate_engagement": lambda u: 0.4 <= u.get("user_need_for_cognition", 0.5) <= 0.6,
        "deep_processing": lambda u: u.get("user_need_for_cognition", 0.5) > 0.6,
    },
    "temporal_orientation": {
        "immediate_present": lambda u: u.get("user_construal_level", 0.5) < 0.4,
        "near_future": lambda u: 0.4 <= u.get("user_construal_level", 0.5) <= 0.6,
        "distant_future": lambda u: u.get("user_construal_level", 0.5) > 0.6,
    },
    "social_influence": {
        "highly_independent": lambda u: u.get("user_mechanisms_cited_social_proof", 0.3) < 0.2,
        "informational_seeker": lambda u: u.get("user_mechanisms_cited_authority", 0.3) > 0.4,
        "socially_aware": lambda u: u.get("user_mechanisms_cited_social_proof", 0.3) > 0.4,
        "normatively_driven": lambda u: u.get("user_personality_agreeableness", 0.5) > 0.7,
        "opinion_leader": lambda u: u.get("user_personality_extraversion", 0.5) > 0.7
            and u.get("user_mechanisms_cited_social_proof", 0.3) < 0.3,
    },
}

ARCHETYPE_BIG5 = {
    "Achiever":   {"o": 0.65, "c": 0.80, "e": 0.70, "a": 0.50, "n": 0.40},
    "Explorer":   {"o": 0.90, "c": 0.50, "e": 0.65, "a": 0.60, "n": 0.45},
    "Guardian":   {"o": 0.40, "c": 0.85, "e": 0.45, "a": 0.65, "n": 0.60},
    "Connector":  {"o": 0.60, "c": 0.55, "e": 0.85, "a": 0.80, "n": 0.50},
    "Pragmatist": {"o": 0.50, "c": 0.75, "e": 0.50, "a": 0.55, "n": 0.45},
}


class UnifiedIntelligenceService:
    """
    Three-layer Bayesian fusion service.

    Single entry point for all intelligence queries. Queries Layer 3 for
    individual depth, Layer 2 for structural intelligence, Layer 1 for
    population breadth, and fuses them with evidence-weighted Bayesian
    combination.
    """

    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        self._layer1_priors: Optional[Dict] = None
        self._layer1_coldstart: Optional[Dict] = None
        self._mechanism_graph: Optional[Dict] = None

    def _get_driver(self):
        if self._driver is not None:
            return self._driver
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self._driver.verify_connectivity()
            logger.info("UnifiedIntelligenceService connected to Neo4j")
            return self._driver
        except Exception as e:
            logger.error(f"Cannot connect to Neo4j: {e}")
            return None

    # ─── Layer 1: JSON Priors ──────────────────────────────────────────

    def _load_layer1_priors(self) -> Dict:
        if self._layer1_priors is not None:
            return self._layer1_priors
        if PRIORS_PATH.exists():
            try:
                self._layer1_priors = json.loads(PRIORS_PATH.read_text())
                logger.info(
                    f"Layer 1 priors loaded: {self._layer1_priors.get('total_reviews_processed', 0):,} reviews"
                )
            except Exception as e:
                logger.warning(f"Failed to load Layer 1 priors: {e}")
                self._layer1_priors = {}
        else:
            logger.warning(f"Layer 1 priors file not found: {PRIORS_PATH}")
            self._layer1_priors = {}
        return self._layer1_priors

    def get_layer1_mechanism_effectiveness(
        self, category: str = "All_Beauty", archetype: str = "achiever"
    ) -> Dict[str, Dict]:
        priors = self._load_layer1_priors()
        cat_matrices = priors.get("category_effectiveness_matrices", {})
        cat_data = cat_matrices.get(category, {})
        return cat_data.get(archetype, cat_data.get("analyst", {}))

    def get_layer1_archetype_distribution(
        self, category: str = "All_Beauty"
    ) -> Dict[str, float]:
        priors = self._load_layer1_priors()
        cat_dists = priors.get("category_archetype_distributions", {})
        return cat_dists.get(category, priors.get("global_archetype_distribution", {}))

    def get_layer1_ndf_profile(self, category: str = "All_Beauty") -> Dict[str, float]:
        priors = self._load_layer1_priors()
        ndf = priors.get("ndf_population", {})
        by_cat = ndf.get("ndf_by_category", {})
        return by_cat.get(category, ndf.get("ndf_means", {}))

    # ─── Layer 2: Structural Intelligence ──────────────────────────────

    # Research-grounded mechanism relationships (Cialdini 2021, Kahneman 2011, Petty & Cacioppo 1986)
    _MECHANISM_SYNERGIES = [
        ("authority", "social_proof"),
        ("social_proof", "liking"),
        ("commitment", "reciprocity"),
        ("scarcity", "anchoring"),
        ("storytelling", "liking"),
        ("storytelling", "social_proof"),
        ("authority", "commitment"),
        ("reciprocity", "liking"),
    ]
    _MECHANISM_ANTAGONISMS = [
        ("scarcity", "reciprocity"),
        ("authority", "storytelling"),
        ("anchoring", "liking"),
    ]
    _CORE_MECHANISMS = [
        "authority", "social_proof", "scarcity", "reciprocity",
        "commitment", "liking", "anchoring", "storytelling",
    ]

    def get_mechanism_knowledge_graph(self) -> Dict:
        """
        Return mechanism synergies, antagonisms, and contextual moderation.

        Queries Layer 2 CognitiveMechanism nodes first. When Layer 2 is
        absent (nodes don't exist), falls back to research-grounded
        mechanism relationships derived from Cialdini, Kahneman, and
        Elaboration Likelihood Model literature.
        """
        if self._mechanism_graph is not None:
            return self._mechanism_graph

        driver = self._get_driver()
        if driver:
            with driver.session() as session:
                mechs = session.run(
                    "MATCH (m:CognitiveMechanism) RETURN m.name AS name"
                ).data()
                if mechs:
                    syns = session.run(
                        "MATCH (a:CognitiveMechanism)-[:SYNERGIZES_WITH]->(b:CognitiveMechanism) "
                        "RETURN a.name AS src, b.name AS tgt"
                    ).data()
                    ants = session.run(
                        "MATCH (a:CognitiveMechanism)-[:ANTAGONIZES]->(b:CognitiveMechanism) "
                        "RETURN a.name AS src, b.name AS tgt"
                    ).data()
                    self._mechanism_graph = {
                        "mechanisms": [m["name"] for m in mechs],
                        "synergies": [(s["src"], s["tgt"]) for s in syns],
                        "antagonisms": [(a["src"], a["tgt"]) for a in ants],
                    }
                    return self._mechanism_graph

        self._mechanism_graph = {
            "mechanisms": list(self._CORE_MECHANISMS),
            "synergies": list(self._MECHANISM_SYNERGIES),
            "antagonisms": list(self._MECHANISM_ANTAGONISMS),
        }
        logger.info("Mechanism graph: using research-grounded fallback (Layer 2 nodes absent)")
        return self._mechanism_graph

    def map_profile_to_granular_type(
        self, user_props: Dict[str, float]
    ) -> Optional[str]:
        """
        Map Layer 3 continuous user profile to the closest Layer 2 GranularType
        by discretizing along the 7 psychological dimensions.
        """
        dims = []
        for dim_name, categories in DIMENSION_MAPPING.items():
            matched = None
            for cat_value, test_fn in categories.items():
                try:
                    if test_fn(user_props):
                        matched = cat_value
                        break
                except Exception:
                    continue
            if matched is None:
                matched = list(categories.keys())[0]
            dims.append(matched)
        return "|".join(dims)

    def get_granular_type_susceptibilities(
        self, type_id: str
    ) -> List[Dict[str, Any]]:
        """
        Follow SUSCEPTIBLE_TO edges from a GranularType to get mechanism
        susceptibility scores.
        """
        driver = self._get_driver()
        if not driver:
            return []

        with driver.session() as session:
            result = session.run(
                "MATCH (gt:GranularType {type_id: $tid})-[r:SUSCEPTIBLE_TO]->(m) "
                "RETURN m.name AS mechanism, labels(m)[0] AS label, "
                "r.rate AS rate, r.samples AS samples",
                tid=type_id,
            ).data()

        return [
            {
                "mechanism": r["mechanism"],
                "label": r["label"],
                "rate": r.get("rate"),
                "samples": r.get("samples"),
            }
            for r in result
        ]

    def get_persuasive_templates(
        self, mechanism: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve validated persuasive language patterns from Layer 2."""
        driver = self._get_driver()
        if not driver:
            return []

        with driver.session() as session:
            result = session.run(
                "MATCH (pt:PersuasiveTemplate) "
                "WHERE pt.mechanism = $mech "
                "RETURN pt.pattern AS pattern, pt.helpful_votes AS votes, "
                "pt.success_rate AS rate "
                "ORDER BY pt.helpful_votes DESC LIMIT $lim",
                mech=mechanism,
                lim=limit,
            ).data()

        return result

    def get_brand_prior(
        self, brand: str, domain: str = "Sephora Beauty"
    ) -> Optional[Dict[str, float]]:
        """Get archetype alignment scores for a brand from Layer 2 BrandPriors."""
        driver = self._get_driver()
        if not driver:
            return None

        with driver.session() as session:
            result = session.run(
                "MATCH (bp:BrandPrior) "
                "WHERE bp.brand_name = $brand AND bp.domain = $domain "
                "RETURN bp.achiever AS achiever, bp.explorer AS explorer, "
                "bp.guardian AS guardian, bp.connector AS connector, "
                "bp.pragmatist AS pragmatist",
                brand=brand,
                domain=domain,
            ).single()

        if not result:
            return None
        return dict(result)

    def check_mechanism_conflicts(
        self, mechanisms: List[str]
    ) -> Dict[str, Any]:
        """
        Use Layer 2's SYNERGIZES_WITH / ANTAGONIZES edges to validate
        a proposed mechanism combination.
        """
        kg = self.get_mechanism_knowledge_graph()
        synergies_found = []
        conflicts_found = []

        mech_set = {m.lower().replace(" ", "_") for m in mechanisms}

        for src, tgt in kg["synergies"]:
            if src.lower().replace(" ", "_") in mech_set and tgt.lower().replace(" ", "_") in mech_set:
                synergies_found.append((src, tgt))
        for src, tgt in kg["antagonisms"]:
            if src.lower().replace(" ", "_") in mech_set and tgt.lower().replace(" ", "_") in mech_set:
                conflicts_found.append((src, tgt))

        return {
            "valid": len(conflicts_found) == 0,
            "synergies": synergies_found,
            "conflicts": conflicts_found,
            "mechanisms_checked": mechanisms,
        }

    # ─── Layer 3: Individual Depth ─────────────────────────────────────

    def get_user_profile(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get full psychological profile from a Layer 3 AnnotatedReview."""
        driver = self._get_driver()
        if not driver:
            return None

        with driver.session() as session:
            result = session.run(
                "MATCH (r:AnnotatedReview {review_id: $rid}) "
                "RETURN properties(r) AS props",
                rid=review_id,
            ).single()

        if not result:
            return None
        return result["props"]

    def get_product_intelligence(self, asin: str) -> Optional[Dict[str, Any]]:
        """Get full Layer 3 product psychological profile."""
        driver = self._get_driver()
        if not driver:
            return None

        with driver.session() as session:
            result = session.run(
                "MATCH (pd:ProductDescription {asin: $asin}) "
                "RETURN properties(pd) AS props",
                asin=asin,
            ).single()

        if not result:
            return None
        return result["props"]

    def get_brand_edge_statistics(
        self, asin: str, limit: int = 100
    ) -> Dict[str, Any]:
        """Aggregate BRAND_CONVERTED edge statistics for a product."""
        driver = self._get_driver()
        if not driver:
            return {"count": 0}

        with driver.session() as session:
            result = session.run(
                "MATCH (pd:ProductDescription {asin: $asin})"
                "-[bc:BRAND_CONVERTED]->(r:AnnotatedReview) "
                "RETURN count(bc) AS cnt, "
                "avg(bc.personality_brand_alignment) AS avg_personality, "
                "avg(bc.emotional_resonance) AS avg_emotional, "
                "avg(bc.regulatory_fit_score) AS avg_reg_fit, "
                "avg(bc.construal_fit_score) AS avg_construal, "
                "avg(bc.value_alignment) AS avg_value, "
                "avg(bc.evolutionary_motive_match) AS avg_evo, "
                "avg(bc.composite_alignment) AS avg_composite, "
                "stDev(bc.composite_alignment) AS std_composite, "
                "avg(bc.persuasion_confidence_multiplier) AS avg_persuasion_conf",
                asin=asin,
            ).single()

        if not result:
            return {"count": 0}
        return {k: v for k, v in dict(result).items() if v is not None}

    def get_peer_influence_patterns(
        self, asin: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Aggregate PEER_INFLUENCED edge statistics for a product."""
        driver = self._get_driver()
        if not driver:
            return {"count": 0}

        with driver.session() as session:
            result = session.run(
                "MATCH (pd:ProductDescription {asin: $asin})"
                "-[:HAS_REVIEW]->(peer:AnnotatedReview)"
                "-[pi:PEER_INFLUENCED]->(buyer:AnnotatedReview) "
                "RETURN count(pi) AS cnt, "
                "avg(pi.peer_authenticity_resonance) AS avg_auth, "
                "avg(pi.narrative_resonance) AS avg_narrative, "
                "avg(pi.use_case_match) AS avg_use_case, "
                "avg(pi.influence_weight) AS avg_influence",
                asin=asin,
            ).single()

        if not result:
            return {"count": 0}
        return {k: v for k, v in dict(result).items() if v is not None}

    def get_bayesian_priors(self, category: str = "All Beauty") -> List[Dict]:
        """Get all Layer 3 BayesianPrior nodes."""
        driver = self._get_driver()
        if not driver:
            return []

        with driver.session() as session:
            result = session.run(
                "MATCH (bp:BayesianPrior) RETURN properties(bp) AS props"
            ).data()

        return [r["props"] for r in result]

    # ─── Fusion: Bayesian Combination ──────────────────────────────────

    def map_to_archetype(
        self, user_props: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Map Layer 3's continuous Big Five scores to a weighted archetype
        distribution using Euclidean distance to each archetype centroid.
        """
        o = user_props.get("user_personality_openness", 0.5)
        c = user_props.get("user_personality_conscientiousness", 0.5)
        e = user_props.get("user_personality_extraversion", 0.5)
        a = user_props.get("user_personality_agreeableness", 0.5)
        n = user_props.get("user_personality_neuroticism", 0.5)
        user_vec = {"o": o, "c": c, "e": e, "a": a, "n": n}

        distances = {}
        for name, centroid in ARCHETYPE_BIG5.items():
            dist = math.sqrt(
                sum((user_vec[d] - centroid[d]) ** 2 for d in "ocean"
                    if d in user_vec and d in centroid)
            )
            distances[name] = dist

        if not distances:
            return {k: 0.2 for k in ARCHETYPE_BIG5}

        inv_dists = {k: 1.0 / (v + 0.01) for k, v in distances.items()}
        total = sum(inv_dists.values())
        return {k: v / total for k, v in inv_dists.items()}

    def fuse_mechanism_recommendation(
        self,
        asin: str,
        user_props: Optional[Dict[str, float]] = None,
        category: str = "All_Beauty",
    ) -> Dict[str, Any]:
        """
        Produce a fully fused mechanism recommendation using all three layers.

        Returns ranked mechanisms with:
        - Layer 3 edge-based evidence (BRAND_CONVERTED alignment)
        - Layer 2 structural intelligence (synergies, antagonisms, templates)
        - Layer 1 population-level priors (archetype effectiveness)
        - Conflict checking and confidence intervals
        """
        result: Dict[str, Any] = {
            "asin": asin,
            "category": category,
            "layers_used": [],
            "mechanisms": [],
            "conflicts": [],
            "synergies": [],
            "templates": [],
        }

        # ─── Layer 3: individual-level edge evidence ───
        edge_stats = self.get_brand_edge_statistics(asin)
        product_intel = self.get_product_intelligence(asin)
        peer_patterns = self.get_peer_influence_patterns(asin)
        l3_priors = self.get_bayesian_priors(category)

        l3_mechanism_scores: Dict[str, float] = {}
        if product_intel:
            result["layers_used"].append("layer3_product")
            for mech in ["social_proof", "scarcity", "authority",
                         "reciprocity", "commitment", "liking",
                         "anchoring", "storytelling"]:
                score = product_intel.get(f"ad_persuasion_techniques_{mech}", 0.0)
                if score and score > 0.1:
                    l3_mechanism_scores[mech] = float(score)

        l3_composite = edge_stats.get("avg_composite")
        if l3_composite is not None and edge_stats.get("cnt", 0) > 5:
            result["layers_used"].append("layer3_edges")
            result["edge_evidence"] = {
                "n_edges": edge_stats["cnt"],
                "avg_composite_alignment": l3_composite,
                "avg_personality_alignment": edge_stats.get("avg_personality"),
                "avg_emotional_resonance": edge_stats.get("avg_emotional"),
                "avg_regulatory_fit": edge_stats.get("avg_reg_fit"),
            }

        if peer_patterns.get("cnt", 0) > 0:
            result["layers_used"].append("layer3_peer")
            result["peer_evidence"] = {
                "n_peer_edges": peer_patterns["cnt"],
                "avg_authenticity": peer_patterns.get("avg_auth"),
                "avg_narrative": peer_patterns.get("avg_narrative"),
                "avg_influence": peer_patterns.get("avg_influence"),
            }

        # ─── Layer 2: structural mechanism intelligence ───
        archetype_weights = {}
        if user_props:
            archetype_weights = self.map_to_archetype(user_props)
            result["inferred_archetype"] = archetype_weights

            gt_id = self.map_profile_to_granular_type(user_props)
            susceptibilities = self.get_granular_type_susceptibilities(gt_id)
            if susceptibilities:
                result["layers_used"].append("layer2_granular_type")
                result["granular_type"] = gt_id
                result["susceptibilities"] = susceptibilities

        kg = self.get_mechanism_knowledge_graph()
        if kg["mechanisms"]:
            result["layers_used"].append("layer2_mechanism_graph")

        # ─── Layer 1: population-level priors ───
        top_archetype = max(archetype_weights, key=archetype_weights.get) if archetype_weights else "achiever"
        l1_effectiveness = self.get_layer1_mechanism_effectiveness(
            category, top_archetype.lower()
        )
        if l1_effectiveness:
            result["layers_used"].append("layer1_corpus_priors")

        # ─── Bayesian fusion: combine all layers ───
        all_mechanisms = set(l3_mechanism_scores.keys())
        for mech_name, mech_data in l1_effectiveness.items():
            all_mechanisms.add(mech_name)

        fused_scores = []
        for mech in all_mechanisms:
            l3_score = l3_mechanism_scores.get(mech, 0.0)
            l1_data = l1_effectiveness.get(mech, {})
            l1_rate = l1_data.get("success_rate", 0.5) if isinstance(l1_data, dict) else 0.5
            l1_samples = l1_data.get("sample_size", 0) if isinstance(l1_data, dict) else 0

            l1_weight = min(1.0, l1_samples / 10000) if l1_samples > 0 else 0.1
            l3_weight = 1.0 if l3_score > 0.1 else 0.0

            if l3_weight > 0 and l1_weight > 0:
                fused = (l1_rate * l1_weight + l3_score * l3_weight) / (l1_weight + l3_weight)
                source = "fused_l1_l3"
            elif l3_weight > 0:
                fused = l3_score
                source = "layer3_only"
            else:
                fused = l1_rate
                source = "layer1_only"

            fused_scores.append({
                "mechanism": mech,
                "fused_score": round(fused, 4),
                "layer1_prior": round(l1_rate, 4),
                "layer3_evidence": round(l3_score, 4),
                "source": source,
                "l1_sample_size": l1_samples,
            })

        fused_scores.sort(key=lambda x: x["fused_score"], reverse=True)
        result["mechanisms"] = fused_scores[:8]

        # ─── Conflict checking via Layer 2 knowledge graph ───
        top_mechs = [m["mechanism"] for m in result["mechanisms"][:4]]
        conflict_check = self.check_mechanism_conflicts(top_mechs)
        result["conflicts"] = conflict_check["conflicts"]
        result["synergies"] = conflict_check["synergies"]

        # ─── Persuasive templates for top mechanisms ───
        for m in result["mechanisms"][:3]:
            templates = self.get_persuasive_templates(m["mechanism"])
            if templates:
                result["templates"].extend(
                    {"mechanism": m["mechanism"], **t} for t in templates[:2]
                )

        return result

    def get_intelligence(
        self,
        category: str = "All_Beauty",
        asin: Optional[str] = None,
        archetype: Optional[str] = None,
        personality: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Top-level unified intelligence query.

        Queries Layer 3 first (annotated graph), falls back to Layer 2
        (old schema), enriches with Layer 1 (JSON priors), and returns a
        fused payload consumable by MechanismActivationAtom, ColdStartService,
        GraphIntelligenceService, and partner_api demos.

        Fusion weights:
            Layer 3 present: 0.6 annotated + 0.2 structural + 0.2 corpus
            Layer 3 absent:  0.0 annotated + 0.4 structural + 0.6 corpus
        """
        result: Dict[str, Any] = {
            "category": category,
            "asin": asin,
            "layers_used": [],
            "has_annotated_depth": False,
        }

        # ─── Layer 3: individual-level annotated depth ───
        annotated: Dict[str, Any] = {}
        if asin:
            product = self.get_product_intelligence(asin)
            if product:
                annotated["product"] = product
                result["layers_used"].append("layer3_product")
                result["has_annotated_depth"] = True

            edge_stats = self.get_brand_edge_statistics(asin)
            if edge_stats.get("cnt", 0) > 0:
                annotated["edge_statistics"] = edge_stats
                result["layers_used"].append("layer3_edges")
                result["has_annotated_depth"] = True

            peer = self.get_peer_influence_patterns(asin)
            if peer.get("cnt", 0) > 0:
                annotated["peer_influence"] = peer
                result["layers_used"].append("layer3_peer")

        l3_priors = self.get_bayesian_priors(category)
        if l3_priors:
            annotated["bayesian_priors"] = l3_priors
            result["layers_used"].append("layer3_priors")
            result["has_annotated_depth"] = True

        result["layer3"] = annotated

        # ─── Layer 2: structural intelligence ───
        structural: Dict[str, Any] = {}

        kg = self.get_mechanism_knowledge_graph()
        if kg.get("mechanisms"):
            structural["mechanism_graph"] = {
                "n_mechanisms": len(kg["mechanisms"]),
                "n_synergies": len(kg["synergies"]),
                "n_antagonisms": len(kg["antagonisms"]),
            }
            result["layers_used"].append("layer2_mechanism_graph")

        if personality:
            gt_id = self.map_profile_to_granular_type(personality)
            susceptibilities = self.get_granular_type_susceptibilities(gt_id)
            if susceptibilities:
                structural["granular_type"] = gt_id
                structural["susceptibilities"] = susceptibilities
                result["layers_used"].append("layer2_granular_type")

        result["layer2"] = structural

        # ─── Layer 1: population-level priors ───
        corpus: Dict[str, Any] = {}

        effective_archetype = archetype
        if not effective_archetype and personality:
            weights = self.map_to_archetype(personality)
            effective_archetype = max(weights, key=weights.get) if weights else "achiever"
            corpus["inferred_archetype"] = effective_archetype
            corpus["archetype_weights"] = weights

        l1_effectiveness = self.get_layer1_mechanism_effectiveness(
            category, (effective_archetype or "achiever").lower()
        )
        if l1_effectiveness:
            corpus["mechanism_effectiveness"] = l1_effectiveness
            result["layers_used"].append("layer1_corpus")

        corpus["ndf_profile"] = self.get_layer1_ndf_profile(category)
        corpus["archetype_distribution"] = self.get_layer1_archetype_distribution(category)
        result["layer1"] = corpus

        # ─── Fused mechanism scores ───
        has_l3 = result["has_annotated_depth"]
        w3 = 0.6 if has_l3 else 0.0
        w2 = 0.2 if has_l3 else 0.4
        w1 = 0.2 if has_l3 else 0.6

        all_mechs: Dict[str, Dict[str, float]] = {}

        # Layer 3 product persuasion scores
        if "product" in annotated and annotated["product"]:
            for mech in ["social_proof", "scarcity", "authority",
                         "reciprocity", "commitment", "liking",
                         "anchoring", "storytelling"]:
                score = annotated["product"].get(
                    f"ad_persuasion_techniques_{mech}", 0.0
                )
                if score and float(score) > 0.05:
                    all_mechs.setdefault(mech, {})["l3"] = float(score)

        # Layer 2 susceptibility scores
        for s in structural.get("susceptibilities", []):
            name = s.get("mechanism", "").lower().replace(" ", "_")
            rate = s.get("rate")
            if name and rate:
                all_mechs.setdefault(name, {})["l2"] = float(rate)

        # Layer 1 corpus effectiveness
        for mech_name, mech_data in l1_effectiveness.items():
            rate = mech_data.get("success_rate", 0.5) if isinstance(mech_data, dict) else 0.5
            all_mechs.setdefault(mech_name, {})["l1"] = float(rate)

        fused_mechanisms = []
        for mech, layers in all_mechs.items():
            l3v = layers.get("l3", 0.0)
            l2v = layers.get("l2", 0.0)
            l1v = layers.get("l1", 0.5)

            numerator = w3 * l3v + w2 * l2v + w1 * l1v
            denominator = (w3 if l3v else 0) + (w2 if l2v else 0) + (w1 if l1v else 0)
            fused = numerator / denominator if denominator > 0 else l1v

            fused_mechanisms.append({
                "mechanism": mech,
                "fused_score": round(fused, 4),
                "layer3": round(l3v, 4),
                "layer2": round(l2v, 4),
                "layer1": round(l1v, 4),
            })

        fused_mechanisms.sort(key=lambda x: x["fused_score"], reverse=True)
        result["fused_mechanisms"] = fused_mechanisms[:10]
        result["fusion_weights"] = {"layer3": w3, "layer2": w2, "layer1": w1}

        # ─── Conflict check top mechanisms ───
        top_names = [m["mechanism"] for m in fused_mechanisms[:4]]
        if top_names:
            conflicts = self.check_mechanism_conflicts(top_names)
            result["conflicts"] = conflicts.get("conflicts", [])
            result["synergies"] = conflicts.get("synergies", [])

        return result

    def get_full_intelligence(self, asin: str) -> Dict[str, Any]:
        """
        Return a complete three-layer intelligence report for a product,
        suitable for demo display.
        """
        product = self.get_product_intelligence(asin)
        if not product:
            return {"error": f"Product {asin} not found in Layer 3"}

        edge_stats = self.get_brand_edge_statistics(asin)
        peer_patterns = self.get_peer_influence_patterns(asin)
        priors = self.get_bayesian_priors()

        brand_name = product.get("brand_name", "")
        brand_prior = self.get_brand_prior(brand_name) if brand_name else None

        kg = self.get_mechanism_knowledge_graph()

        ndf = self.get_layer1_ndf_profile()
        archetype_dist = self.get_layer1_archetype_distribution()

        return {
            "asin": asin,
            "layer3": {
                "product": {
                    k: v for k, v in product.items()
                    if k.startswith("ad_") or k in ("asin", "main_category", "annotation_tier")
                },
                "edge_statistics": edge_stats,
                "peer_influence": peer_patterns,
                "bayesian_priors": priors,
            },
            "layer2": {
                "brand_prior": brand_prior,
                "mechanism_graph": {
                    "n_mechanisms": len(kg["mechanisms"]),
                    "n_synergies": len(kg["synergies"]),
                    "n_antagonisms": len(kg["antagonisms"]),
                },
            },
            "layer1": {
                "ndf_profile": ndf,
                "archetype_distribution": archetype_dist,
            },
        }

    # ─── Convenience: find best demo products ──────────────────────────

    def find_top_products(self, limit: int = 20) -> List[Dict]:
        """Find products with the most edges and highest alignment (for demos)."""
        driver = self._get_driver()
        if not driver:
            return []

        with driver.session() as session:
            result = session.run(
                "MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(r:AnnotatedReview) "
                "WITH pd.asin AS asin, count(bc) AS review_count, "
                "avg(bc.personality_brand_alignment) AS avg_align, "
                "avg(bc.composite_alignment) AS avg_composite "
                "WHERE review_count > 5 "
                "RETURN asin, review_count, avg_align, avg_composite "
                "ORDER BY review_count DESC LIMIT $lim",
                lim=limit,
            ).data()

        return result


# ─── Singleton ─────────────────────────────────────────────────────────

_instance: Optional[UnifiedIntelligenceService] = None


def get_unified_intelligence_service() -> UnifiedIntelligenceService:
    global _instance
    if _instance is None:
        _instance = UnifiedIntelligenceService()
    return _instance
