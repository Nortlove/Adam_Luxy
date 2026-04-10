# =============================================================================
# ADAM Atom Intelligence Injector
# Location: adam/intelligence/atom_intelligence_injector.py
# =============================================================================

"""
ATOM INTELLIGENCE INJECTOR

Feeds pre-computed intelligence to AoT atoms before execution.

This is the critical bridge between:
- Offline intelligence (re-ingestion, brand analysis)
- Online reasoning (atoms making decisions)

Without this, atoms only have:
- Real-time graph queries (limited to what's stored)
- Claude reasoning (expensive, slow)

With this, atoms get:
- Pre-computed archetype → mechanism effectiveness
- Persuasive templates proven to work
- Brand copy analysis (Cialdini, Aaker)
- Journey patterns (bought_together)
- Helpful vote intelligence

ARCHITECTURE:
                                    ┌─────────────────┐
                                    │   ReIngestion   │
                                    │   (offline)     │
                                    └────────┬────────┘
                                             │
                                             ▼
┌─────────────────┐              ┌─────────────────────┐
│  User Request   │──────────────│  Intelligence       │
│                 │              │  Injector           │
└─────────────────┘              │  - Templates        │
                                 │  - Effectiveness    │
                                 │  - Brand Copy       │
                                 │  - Journeys         │
                                 └─────────┬───────────┘
                                           │
                                           ▼
                                 ┌─────────────────────┐
                                 │   AoT Atoms         │
                                 │   (with priors!)    │
                                 └─────────────────────┘
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# INJECTED INTELLIGENCE MODELS
# =============================================================================

@dataclass
class InjectedIntelligence:
    """
    Complete intelligence package injected into atom execution.
    
    This is what atoms receive BEFORE they start reasoning.
    """
    
    # Request context
    request_id: str
    user_id: str
    brand_name: Optional[str] = None
    product_asin: Optional[str] = None
    
    # Pre-computed effectiveness (from helpful vote analysis)
    archetype_effectiveness: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Format: {archetype: {mechanism: success_rate}}
    
    # Persuasive templates (from high-helpful-vote reviews)
    persuasive_templates: List[Dict[str, Any]] = field(default_factory=list)
    # Format: [{pattern, mechanism, votes, archetype}]
    
    # Brand copy analysis (from product metadata)
    brand_cialdini_scores: Dict[str, float] = field(default_factory=dict)
    # Format: {principle: score}
    
    brand_aaker_scores: Dict[str, float] = field(default_factory=dict)
    # Format: {dimension: score}
    
    brand_personality: str = ""
    brand_tactics: List[str] = field(default_factory=list)
    
    # Journey intelligence (from bought_together)
    journey_products: List[Dict[str, Any]] = field(default_factory=list)
    # Format: [{asin, brand, frequency, journey_type}]
    
    # Review intelligence
    total_reviews: int = 0
    high_influence_reviews: int = 0
    avg_helpful_votes: float = 0.0
    
    # Inferred user archetype (if available)
    detected_archetype: Optional[str] = None
    archetype_confidence: float = 0.0
    
    # POST-INGESTION: Product ad psychology profile
    product_ad_profile: Dict[str, Any] = field(default_factory=dict)
    # Format: {primary_persuasion, primary_emotion, primary_value, linguistic_style}
    
    # NDF (Nonconscious Decision Fingerprint) intelligence
    ndf_profile: Dict[str, float] = field(default_factory=dict)
    # Format: {approach_avoidance, temporal_horizon, social_calibration,
    #          uncertainty_tolerance, status_sensitivity, cognitive_engagement,
    #          arousal_seeking, cognitive_velocity}
    
    ndf_mechanism_susceptibility: Dict[str, float] = field(default_factory=dict)
    # Format: {reciprocity, commitment, social_proof, authority, liking, scarcity, unity}
    
    ndf_population_priors: Dict[str, Any] = field(default_factory=dict)
    # Format: {ndf_means, ndf_stds, ndf_distributions}
    
    # DSP Graph Intelligence (from Neo4j DSPConstruct / EMPIRICALLY_EFFECTIVE edges)
    dsp_empirical_effectiveness: Dict[str, Dict] = field(default_factory=dict)
    # Format: {mechanism_id: {success_rate, sample_size, categories_seen}}
    
    dsp_alignment_edges: List[Dict[str, Any]] = field(default_factory=list)
    # Format: [{edge_type, target_id, strength, matrix, description}]
    
    dsp_category_moderation: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_id: delta} (positive=boost, negative=dampen)
    
    dsp_relationship_amplification: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_id: boost_factor}
    
    dsp_mechanism_susceptibility: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_id: susceptibility_strength}
    
    # Corpus Fusion Intelligence (from 1B+ reviews, Layers 1-5)
    corpus_mechanism_priors: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_name: empirical_prior_score}
    
    corpus_prior_confidence: float = 0.0
    corpus_evidence_count: int = 0
    
    corpus_creative_constraints: Dict[str, Any] = field(default_factory=dict)
    # Format: {framing_guidance, emotional_register, mechanism_deployment, ranked_patterns}
    
    corpus_platform_calibration: Dict[str, Any] = field(default_factory=dict)
    # Format: {mechanism_name: {calibrated_score, confidence, source}}
    
    # Quality metrics
    data_freshness_hours: float = 0.0
    confidence_level: str = "low"  # low, medium, high
    sources_available: List[str] = field(default_factory=list)
    
    @property
    def has_effectiveness_data(self) -> bool:
        """Check if we have mechanism effectiveness data."""
        return bool(self.archetype_effectiveness)
    
    @property
    def has_brand_intelligence(self) -> bool:
        """Check if we have brand copy analysis."""
        return bool(self.brand_cialdini_scores) or bool(self.brand_aaker_scores)
    
    @property
    def has_templates(self) -> bool:
        """Check if we have persuasive templates."""
        return len(self.persuasive_templates) > 0
    
    @property
    def has_ndf_intelligence(self) -> bool:
        """Check if we have NDF intelligence."""
        return bool(self.ndf_profile) or bool(self.ndf_mechanism_susceptibility)
    
    @property
    def has_dsp_intelligence(self) -> bool:
        """Check if we have DSP graph intelligence from Neo4j."""
        return bool(self.dsp_empirical_effectiveness) or bool(self.dsp_alignment_edges)
    
    @property
    def has_corpus_intelligence(self) -> bool:
        """Check if we have corpus fusion intelligence from review analysis."""
        return bool(self.corpus_mechanism_priors)
    
    def get_best_mechanism_for_archetype(self, archetype: str) -> Optional[str]:
        """Get the highest-performing mechanism for an archetype."""
        if archetype not in self.archetype_effectiveness:
            return None
        
        mechanisms = self.archetype_effectiveness[archetype]
        if not mechanisms:
            return None
        
        return max(mechanisms.keys(), key=lambda m: mechanisms.get(m, 0))
    
    def get_templates_for_mechanism(self, mechanism: str, limit: int = 5) -> List[str]:
        """Get templates that use a specific mechanism."""
        matching = [
            t["pattern"] 
            for t in self.persuasive_templates 
            if t.get("mechanism") == mechanism
        ]
        return matching[:limit]
    
    def to_atom_context(self) -> Dict[str, Any]:
        """
        Convert to format usable in atom input context.
        
        This is what gets injected into AtomInput.ad_context
        """
        return {
            "injected_intelligence": {
                "archetype_effectiveness": self.archetype_effectiveness,
                "best_templates": self.persuasive_templates[:10],
                "brand_cialdini": self.brand_cialdini_scores,
                "brand_aaker": self.brand_aaker_scores,
                "brand_personality": self.brand_personality,
                "brand_tactics": self.brand_tactics,
                "journey_products": self.journey_products[:5],
                "detected_archetype": self.detected_archetype,
                "archetype_confidence": self.archetype_confidence,
                "product_ad_profile": self.product_ad_profile,
                "review_stats": {
                    "total": self.total_reviews,
                    "high_influence": self.high_influence_reviews,
                    "avg_helpful": self.avg_helpful_votes,
                },
                "confidence_level": self.confidence_level,
                "sources": self.sources_available,
            },
            # NDF Intelligence: Nonconscious Decision Fingerprint
            # Available to ALL atoms for psychological targeting
            "ndf_intelligence": {
                "profile": self.ndf_profile,
                "mechanism_susceptibility": self.ndf_mechanism_susceptibility,
                "population_priors": self.ndf_population_priors,
                "has_ndf": bool(self.ndf_profile),
                # NDF dimension → atom mapping guide:
                # approach_avoidance → RegulatoryFocusAtom (promotion/prevention)
                # temporal_horizon → ConstrualLevelAtom (abstract/concrete)
                # social_calibration → RelationshipIntelligenceAtom (social vs individual)
                # uncertainty_tolerance → MessageFramingAtom (certainty level)
                # status_sensitivity → BrandPersonalityAtom (premium positioning)
                # cognitive_engagement → CopyGeneration (complexity level)
                # arousal_seeking → MessageFramingAtom (urgency/excitement)
                # cognitive_velocity → AdSelectionAtom (confidence weighting)
            },
            # DSP Graph Intelligence: Alignment matrices, empirical effectiveness,
            # category moderation, relationship amplification from Neo4j
            "dsp_graph_intelligence": {
                "empirical_effectiveness": self.dsp_empirical_effectiveness,
                "alignment_edges": self.dsp_alignment_edges,
                "category_moderation": self.dsp_category_moderation,
                "relationship_amplification": self.dsp_relationship_amplification,
                "mechanism_susceptibility": self.dsp_mechanism_susceptibility,
                "has_dsp": self.has_dsp_intelligence,
            },
            # Corpus Fusion Intelligence: Empirical priors from 1B+ reviews,
            # creative constraints, platform calibration (Layers 1-3, 5)
            "corpus_fusion_intelligence": {
                "mechanism_priors": self.corpus_mechanism_priors,
                "prior_confidence": self.corpus_prior_confidence,
                "evidence_count": self.corpus_evidence_count,
                "creative_constraints": self.corpus_creative_constraints,
                "platform_calibration": self.corpus_platform_calibration,
                "has_corpus": self.has_corpus_intelligence,
            },
            "has_precomputed_priors": True,
            "has_ndf_intelligence": bool(self.ndf_profile),
            "has_dsp_intelligence": self.has_dsp_intelligence,
            "has_corpus_intelligence": self.has_corpus_intelligence,
        }


# =============================================================================
# INTELLIGENCE INJECTOR SERVICE
# =============================================================================

class AtomIntelligenceInjector:
    """
    Gathers and injects pre-computed intelligence into atom execution.
    
    This is called by the SynergyOrchestrator BEFORE running atoms,
    ensuring they have all available intelligence upfront.
    
    Data Sources:
    1. GraphPatternPersistence - Templates, effectiveness, journeys
    2. UnifiedProductIntelligence - Brand copy analysis
    3. HelpfulVoteIntelligence - Real-time vote processing
    4. Redis Cache - Recently computed intelligence
    """
    
    def __init__(self):
        """Initialize the injector."""
        self._pattern_persistence = None
        self._cache = {}  # In-memory cache for session
    
    async def _get_pattern_persistence(self):
        """Get pattern persistence service."""
        if self._pattern_persistence is None:
            from adam.infrastructure.neo4j.pattern_persistence import (
                get_pattern_persistence
            )
            self._pattern_persistence = get_pattern_persistence()
        return self._pattern_persistence
    
    async def gather_intelligence(
        self,
        request_id: str,
        user_id: str,
        brand_name: Optional[str] = None,
        product_asin: Optional[str] = None,
        product_category: Optional[str] = None,
        detected_archetype: Optional[str] = None,
    ) -> InjectedIntelligence:
        """
        Gather all available intelligence for a decision request.
        
        This is the main entry point - call this before atom execution.
        
        Args:
            request_id: Unique request identifier
            user_id: User making the request
            brand_name: Brand being advertised (optional)
            product_asin: Product ASIN (optional)
            product_category: Product category (optional)
            detected_archetype: Pre-detected user archetype (optional)
            
        Returns:
            InjectedIntelligence with all available pre-computed data
        """
        intelligence = InjectedIntelligence(
            request_id=request_id,
            user_id=user_id,
            brand_name=brand_name,
            product_asin=product_asin,
            detected_archetype=detected_archetype,
        )
        
        sources = []
        
        # 1. Get effectiveness matrix from graph
        effectiveness = await self._get_effectiveness_from_graph(
            detected_archetype, product_category
        )
        if effectiveness:
            intelligence.archetype_effectiveness = effectiveness
            sources.append("graph_effectiveness")
        
        # 2. Get persuasive templates
        templates = await self._get_templates_from_graph(
            detected_archetype, product_category
        )
        if templates:
            intelligence.persuasive_templates = templates
            sources.append("graph_templates")
        
        # 3. Get product intelligence (brand copy analysis)
        if product_asin:
            product_intel = await self._get_product_intelligence(product_asin)
            if product_intel:
                intelligence.brand_cialdini_scores = product_intel.get("cialdini_scores", {})
                intelligence.brand_aaker_scores = product_intel.get("aaker_scores", {})
                intelligence.brand_personality = product_intel.get("primary_personality", "")
                intelligence.brand_tactics = product_intel.get("tactics", [])
                intelligence.total_reviews = product_intel.get("total_reviews", 0)
                intelligence.high_influence_reviews = product_intel.get("high_influence_reviews", 0)
                intelligence.avg_helpful_votes = product_intel.get("avg_helpful_votes", 0.0)
                sources.append("product_intelligence")
        
        # 4. Get journey products (bought_together)
        if product_asin:
            journeys = await self._get_journey_products(product_asin)
            if journeys:
                intelligence.journey_products = journeys
                sources.append("journey_patterns")
        
        # 5. Try to get brand analysis if we don't have ASIN
        if brand_name and not intelligence.has_brand_intelligence:
            brand_intel = await self._get_brand_intelligence(brand_name)
            if brand_intel:
                intelligence.brand_cialdini_scores = brand_intel.get("cialdini_scores", {})
                intelligence.brand_aaker_scores = brand_intel.get("aaker_scores", {})
                intelligence.brand_personality = brand_intel.get("primary_personality", "")
                sources.append("brand_intelligence")
        
        # 6. POST-INGESTION: Get product ad profile from Neo4j (Phase 2.5)
        # ProductAdProfile nodes created by import_reingestion_to_neo4j.py
        if product_asin or product_category:
            ad_profile = await self._get_product_ad_profile(
                product_asin, product_category
            )
            if ad_profile:
                intelligence.product_ad_profile = ad_profile
                sources.append("product_ad_profile")
        
        # 7. POST-INGESTION: Get ingestion effectiveness priors (Phase 2.2)
        # Empirical Beta(alpha, beta) from 560M+ reviews
        if detected_archetype:
            ingestion_priors = self._get_ingestion_priors(detected_archetype)
            if ingestion_priors:
                # Merge with graph effectiveness (ingestion has larger sample size)
                for mech, stats in ingestion_priors.items():
                    if mech not in intelligence.archetype_effectiveness.get(detected_archetype, {}):
                        if detected_archetype not in intelligence.archetype_effectiveness:
                            intelligence.archetype_effectiveness[detected_archetype] = {}
                        intelligence.archetype_effectiveness[detected_archetype][mech] = stats.get("success_rate", 0.5)
                sources.append("ingestion_effectiveness")
        
        # 8. DSP GRAPH INTELLIGENCE: Query Neo4j for alignment, empirical, category, relationship data
        dsp_intel = await self._get_dsp_graph_intelligence(
            detected_archetype, product_category
        )
        if dsp_intel:
            intelligence.dsp_empirical_effectiveness = dsp_intel.get("empirical_effectiveness", {})
            intelligence.dsp_alignment_edges = dsp_intel.get("alignment_edges", [])
            intelligence.dsp_category_moderation = dsp_intel.get("category_moderation", {})
            intelligence.dsp_relationship_amplification = dsp_intel.get("relationship_amplification", {})
            intelligence.dsp_mechanism_susceptibility = dsp_intel.get("mechanism_susceptibility", {})
            sources.append("dsp_graph_intelligence")
        
        # 9. CORPUS FUSION: Get fused corpus priors (Layers 1-3, 5)
        corpus_intel = await self._get_corpus_fusion_priors(
            detected_archetype, product_category
        )
        if corpus_intel:
            intelligence.corpus_mechanism_priors = corpus_intel.get("mechanism_priors", {})
            intelligence.corpus_prior_confidence = corpus_intel.get("confidence", 0.0)
            intelligence.corpus_evidence_count = corpus_intel.get("evidence_count", 0)
            intelligence.corpus_creative_constraints = corpus_intel.get("creative_constraints", {})
            intelligence.corpus_platform_calibration = corpus_intel.get("platform_calibration", {})
            sources.append("corpus_fusion")
        
        # Set confidence level based on sources
        intelligence.sources_available = sources
        if len(sources) >= 5:
            intelligence.confidence_level = "high"
        elif len(sources) >= 3:
            intelligence.confidence_level = "high"
        elif len(sources) >= 2:
            intelligence.confidence_level = "medium"
        else:
            intelligence.confidence_level = "low"
        
        logger.info(
            f"Gathered intelligence for request {request_id}: "
            f"{len(sources)} sources, confidence={intelligence.confidence_level}"
        )
        
        return intelligence
    
    # -------------------------------------------------------------------------
    # DATA SOURCE METHODS
    # -------------------------------------------------------------------------
    
    async def _get_corpus_fusion_priors(
        self,
        archetype: Optional[str],
        category: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Get corpus fusion priors from the 1B+ review corpus (Layers 1-3, 5).
        
        Returns a dict with:
        - mechanism_priors: {mechanism_name: prior_score}
        - confidence: overall confidence
        - evidence_count: number of reviews supporting priors
        - creative_constraints: framing guidance from Layer 2
        - platform_calibration: platform factors from Layer 3
        """
        try:
            from adam.fusion.prior_extraction import get_prior_extraction_service
            prior_service = get_prior_extraction_service()
            
            corpus_prior = prior_service.extract_prior(
                category=category or "",
                archetype=archetype,
            )
            
            if corpus_prior and corpus_prior.mechanism_priors:
                result = {
                    "mechanism_priors": corpus_prior.get_mechanism_dict(),
                    "confidence": corpus_prior.confidence,
                    "evidence_count": corpus_prior.evidence_count,
                    "creative_constraints": {},
                    "platform_calibration": {},
                }
                
                # Layer 2: Creative constraints
                try:
                    from adam.fusion.creative_patterns import get_creative_pattern_extractor
                    creative = get_creative_pattern_extractor()
                    constraints = creative.extract_creative_constraints(
                        category=category or "",
                        target_archetype=archetype,
                    )
                    if constraints:
                        result["creative_constraints"] = {
                            "framing_guidance": getattr(constraints, 'framing_guidance', {}),
                            "emotional_register": getattr(constraints, 'emotional_register', {}),
                            "mechanism_deployment": getattr(constraints, 'mechanism_deployment', {}),
                        }
                except Exception as e:
                    logger.debug(f"Creative pattern extraction failed: {e}")
                
                # Layer 3: Platform calibration
                try:
                    from adam.fusion.platform_calibration import get_platform_calibration_layer
                    calibration = get_platform_calibration_layer()
                    cal_factors = {}
                    for mech_name, prior_score in list(result["mechanism_priors"].items())[:10]:
                        calibrated, conf, src = calibration.get_calibrated_score(
                            platform="general",
                            mechanism=mech_name,
                            category=category or "",
                            corpus_prior=prior_score,
                        )
                        cal_factors[mech_name] = {
                            "calibrated_score": calibrated,
                            "confidence": conf,
                            "source": src,
                        }
                    result["platform_calibration"] = cal_factors
                except Exception as e:
                    logger.debug(f"Platform calibration failed: {e}")
                
                return result
                
        except ImportError:
            logger.debug("Corpus fusion services not available")
        except Exception as e:
            logger.debug(f"Corpus fusion prior extraction failed: {e}")
        
        return None
    
    async def _get_effectiveness_from_graph(
        self,
        archetype: Optional[str],
        category: Optional[str],
    ) -> Dict[str, Dict[str, float]]:
        """Get archetype → mechanism effectiveness from Neo4j."""
        if not archetype:
            # Get for all common archetypes
            archetypes = [
                "explorer", "sage", "hero", "everyman", "rebel",
                "lover", "jester", "caregiver", "creator", "ruler",
                "magician", "innocent"
            ]
        else:
            archetypes = [archetype]
        
        try:
            persistence = await self._get_pattern_persistence()
            
            effectiveness = {}
            for arch in archetypes:
                rates = await persistence.get_mechanism_effectiveness(arch, category)
                if rates:
                    effectiveness[arch] = rates
            
            return effectiveness
            
        except Exception as e:
            logger.debug(f"Failed to get effectiveness: {e}")
            return {}
    
    async def _get_templates_from_graph(
        self,
        archetype: Optional[str],
        category: Optional[str],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get persuasive templates from Neo4j."""
        if not archetype:
            return []
        
        try:
            persistence = await self._get_pattern_persistence()
            templates = await persistence.get_best_templates_for_archetype(
                archetype, limit=limit
            )
            return templates
            
        except Exception as e:
            logger.debug(f"Failed to get templates: {e}")
            return []
    
    async def _get_product_intelligence(
        self,
        asin: str,
    ) -> Optional[Dict[str, Any]]:
        """Get pre-computed product intelligence."""
        try:
            persistence = await self._get_pattern_persistence()
            return await persistence.get_product_intelligence(asin)
            
        except Exception as e:
            logger.debug(f"Failed to get product intelligence: {e}")
            return None
    
    async def _get_journey_products(
        self,
        asin: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get co-purchase journey products."""
        try:
            persistence = await self._get_pattern_persistence()
            return await persistence.get_journey_products(asin, limit)
            
        except Exception as e:
            logger.debug(f"Failed to get journey products: {e}")
            return []
    
    async def _get_product_ad_profile(
        self,
        asin: Optional[str],
        category: Optional[str],
    ) -> Dict[str, Any]:
        """
        Get product ad psychology profile from Neo4j (POST-INGESTION).
        
        Queries ProductAdProfile nodes created by import_reingestion_to_neo4j.py.
        Falls back to category-level dominant profiles if no ASIN match.
        """
        try:
            persistence = await self._get_pattern_persistence()
            
            # Try ASIN-specific first
            if asin and hasattr(persistence, "get_product_ad_profile"):
                profile = await persistence.get_product_ad_profile(asin=asin)
                if profile:
                    return profile
            
            # Fallback: direct Cypher query
            if asin:
                from adam.infrastructure.neo4j.client import get_neo4j_client
                client = get_neo4j_client()
                if client.is_connected:
                    async with await client.session() as session:
                        result = await session.run(
                            """
                            MATCH (p:ProductAdProfile {asin: $asin})
                            RETURN p.primary_persuasion AS persuasion,
                                   p.primary_emotion AS emotion,
                                   p.primary_value AS value,
                                   p.linguistic_style AS style
                            """,
                            asin=asin,
                        )
                        record = await result.single()
                        if record:
                            return {
                                "primary_persuasion": record["persuasion"] or "",
                                "primary_emotion": record["emotion"] or "",
                                "primary_value": record["value"] or "",
                                "linguistic_style": record["style"] or "",
                            }
            
            return {}
        except Exception as e:
            logger.debug(f"Failed to get product ad profile: {e}")
            return {}
    
    def _get_ingestion_priors(self, archetype: str) -> Dict[str, Any]:
        """
        Get ingestion effectiveness priors for an archetype (POST-INGESTION).
        
        Returns empirical Beta(alpha, beta) parameters from 560M+ reviews.
        Loaded from LearnedPriorsService → ingestion_merged_priors.json.
        """
        try:
            from adam.core.learning.learned_priors_integration import LearnedPriorsService
            service = LearnedPriorsService.get_instance()
            return service.get_ingestion_effectiveness(archetype)
        except Exception as e:
            logger.debug(f"Failed to get ingestion priors: {e}")
            return {}
    
    async def _get_dsp_graph_intelligence(
        self,
        archetype: Optional[str],
        category: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Get DSP graph intelligence from Neo4j.
        
        Queries the 2,400+ DSPConstruct nodes and edges persisted by
        populate_neo4j_graph.py. This provides:
        - Empirical effectiveness (EMPIRICALLY_EFFECTIVE edges with sample_size)
        - Alignment matrix edges (7 matrices, 209 edges)
        - Category moderation deltas (CONTEXTUALLY_MODERATES)
        - Relationship amplification boosts (MODERATES)
        - Mechanism susceptibility by decision style (SUSCEPTIBLE_TO)
        """
        try:
            persistence = await self._get_pattern_persistence()
            result = {}
            
            # 1. Empirical effectiveness for this archetype
            if archetype:
                empirical = await persistence.get_dsp_empirical_effectiveness(archetype)
                if empirical:
                    result["empirical_effectiveness"] = empirical
            
            # 2. Category moderation
            if category:
                cat_mod = await persistence.get_dsp_category_moderation(category)
                if cat_mod:
                    result["category_moderation"] = cat_mod
            
            # 3. Alignment edges for archetype motivation
            # Try the archetype ID directly first (many archetypes have alignment
            # edges stored under their own name), then fall back to mapped motivation.
            if archetype:
                archetype_motivation_map = {
                    "explorer": "pure_curiosity",
                    "achiever": "status_signaling_mot",
                    "connector": "belonging_seeking",
                    "guardian": "risk_mitigation",
                    "pragmatist": "cost_minimization",
                    "analyst": "mastery_seeking",
                    "sage": "pure_curiosity",
                    "hero": "personal_growth",
                    "rebel": "autonomy_preservation",
                    "everyman": "problem_solving_mot",
                }
                # Try archetype name directly first
                alignment_edges = await persistence.get_dsp_alignment_edges(archetype.lower())
                if not alignment_edges:
                    # Fall back to mapped motivation construct
                    motivation = archetype_motivation_map.get(archetype.lower(), "problem_solving_mot")
                    alignment_edges = await persistence.get_dsp_alignment_edges(motivation)
                if alignment_edges:
                    result["alignment_edges"] = alignment_edges
            
            # 4. Mechanism susceptibility (if we can infer decision style)
            # Default to satisficing for unknown archetypes.
            # IDs match graph-stored construct_ids (no ds_ prefix).
            archetype_style_map = {
                "explorer": "gut_instinct",
                "achiever": "maximizing",
                "connector": "social_referencing",
                "guardian": "risk_calculating",
                "pragmatist": "satisficing",
                "analyst": "analytical_systematic",
                "sage": "deliberative_reflective",
                "hero": "maximizing",
                "rebel": "affect_driven",
                "everyman": "heuristic_based",
            }
            if archetype:
                style = archetype_style_map.get(archetype.lower(), "ds_satisficing")
                susceptibility = await persistence.get_dsp_mechanism_susceptibility(style)
                if susceptibility:
                    result["mechanism_susceptibility"] = susceptibility
            
            if result:
                logger.debug(
                    f"DSP graph intelligence gathered: "
                    f"{len(result.get('empirical_effectiveness', {}))} empirical, "
                    f"{len(result.get('alignment_edges', []))} alignment, "
                    f"{len(result.get('category_moderation', {}))} category mod"
                )
            
            return result if result else None
            
        except Exception as e:
            logger.debug(f"Failed to get DSP graph intelligence: {e}")
            return None
    
    async def _get_brand_intelligence(
        self,
        brand_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Get brand-level intelligence (aggregated from products)."""
        try:
            # Query for brand-level aggregated data
            from adam.infrastructure.neo4j.client import get_neo4j_client
            
            client = get_neo4j_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                query = """
                MATCH (p:ProductIntelligence {brand: $brand})
                WITH p LIMIT 10
                
                // Average the scores
                WITH collect(p) AS products
                WHERE size(products) > 0
                
                RETURN 
                    // Get most common personality
                    head([x IN products WHERE x.primary_personality <> '' | x.primary_personality]) AS primary_personality,
                    size(products) AS product_count
                """
                
                result = await session.run(query, brand=brand_name)
                record = await result.single()
                
                if record and record["product_count"] > 0:
                    return {
                        "primary_personality": record["primary_personality"] or "",
                        "product_count": record["product_count"],
                    }
                
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get brand intelligence: {e}")
            return None


# =============================================================================
# SINGLETON
# =============================================================================

_injector: Optional[AtomIntelligenceInjector] = None


def get_intelligence_injector() -> AtomIntelligenceInjector:
    """Get singleton intelligence injector."""
    global _injector
    if _injector is None:
        _injector = AtomIntelligenceInjector()
    return _injector


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def inject_intelligence_into_context(
    request_id: str,
    user_id: str,
    existing_context: Dict[str, Any],
    brand_name: Optional[str] = None,
    product_asin: Optional[str] = None,
    product_category: Optional[str] = None,
    detected_archetype: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to inject intelligence into an existing context dict.
    
    This is the simplest way to add intelligence to atom execution:
    
        context = await inject_intelligence_into_context(
            request_id=request_id,
            user_id=user_id,
            existing_context=ad_context,
            brand_name="Nike",
            product_asin="B08XXXXX",
        )
        
        # Now context["injected_intelligence"] has all the pre-computed data
    """
    injector = get_intelligence_injector()
    
    intelligence = await injector.gather_intelligence(
        request_id=request_id,
        user_id=user_id,
        brand_name=brand_name,
        product_asin=product_asin,
        product_category=product_category,
        detected_archetype=detected_archetype,
    )
    
    # Merge into existing context
    enriched = existing_context.copy()
    enriched.update(intelligence.to_atom_context())
    
    return enriched
