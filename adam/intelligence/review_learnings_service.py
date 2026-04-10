# =============================================================================
# Review Learnings Service - Strategic Integration
# Location: adam/intelligence/review_learnings_service.py
# =============================================================================

"""
REVIEW LEARNINGS SERVICE

Provides access to the massive review corpus learnings embedded in Neo4j:
- 43,821 Amazon sub-category paths with psychological profiles
- 115,485 granular categories from Google Maps, Yelp, Steam, Sephora
- 3,825 customer types with mechanism effectiveness
- 51 regional profiles with cultural values
- 47,434 category levels with hierarchy relationships

This service implements RELAXED MATCHING:
1. Exact sub-category match
2. Parent category match (climb hierarchy)
3. Similar category match (fuzzy)
4. Domain fallback (e.g., "electronics" domain)
5. Global priors (always available)

Usage:
    from adam.intelligence.review_learnings_service import get_review_learnings_service
    
    service = get_review_learnings_service()
    
    # Get psychology for a product category path
    profile = service.get_category_psychology("Electronics > Computers & Accessories > Laptops")
    
    # Get with brand context
    profile = service.get_product_psychology(brand="Apple", category="Laptops")
    
    # Get mechanism recommendations
    mechanisms = service.get_best_mechanisms_for_category("Electronics > Computers & Accessories")
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CategoryPsychProfile:
    """Psychological profile for a category/sub-category."""
    category_path: str
    level: int
    review_count: int
    
    # Archetype scores (normalized 0-1)
    archetypes: Dict[str, float] = field(default_factory=dict)
    
    # Framework dimensions
    frameworks: Dict[str, float] = field(default_factory=dict)
    
    # Mechanism effectiveness for this category
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Source of this profile (exact/parent/similar/domain/global)
    match_type: str = "exact"
    match_confidence: float = 1.0


@dataclass
class CustomerTypeProfile:
    """Granular customer type with mechanism effectiveness."""
    type_id: str
    base_archetype: str
    primary_dimension: str
    domain: str
    
    # Mechanism effectiveness for this customer type
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Population statistics
    population_share: float = 0.0


@dataclass
class MechanismRecommendation:
    """Recommendation for a persuasion mechanism."""
    mechanism: str
    effectiveness: float
    confidence: float
    source: str
    reasoning: str


# =============================================================================
# REVIEW LEARNINGS SERVICE
# =============================================================================

class ReviewLearningsService:
    """
    Service for querying review learnings from Neo4j.
    
    Implements hierarchical fallback:
    1. Exact sub-category path match
    2. Parent category match
    3. Similar category (fuzzy)
    4. Domain-level aggregation
    5. Global priors
    """
    
    _instance = None
    
    def __init__(self):
        self._driver = None
        self._connected = False
        
        # Cache for frequently accessed data
        self._category_cache: Dict[str, CategoryPsychProfile] = {}
        self._customer_type_cache: Dict[str, CustomerTypeProfile] = {}
        
        # Global priors (fallback)
        self._global_archetypes = {
            "Achiever": 0.20,
            "Explorer": 0.18,
            "Connector": 0.35,
            "Guardian": 0.15,
            "Pragmatist": 0.12,
        }
        
        self._global_mechanisms = {
            "liking": 0.40,
            "social_proof": 0.35,
            "commitment": 0.30,
            "reciprocity": 0.28,
            "authority": 0.25,
            "scarcity": 0.22,
        }
    
    @classmethod
    def get_instance(cls) -> "ReviewLearningsService":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._connect()
        return cls._instance
    
    def _connect(self) -> bool:
        """Connect to Neo4j."""
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "atomofthought")
            )
            self._connected = True
            logger.info("ReviewLearningsService connected to Neo4j")
            return True
        except Exception as e:
            logger.warning(f"ReviewLearningsService could not connect to Neo4j: {e}")
            self._connected = False
            return False
    
    # =========================================================================
    # CATEGORY PSYCHOLOGY LOOKUPS
    # =========================================================================
    
    def get_category_psychology(
        self,
        category_path: str,
        include_parent: bool = True,
    ) -> CategoryPsychProfile:
        """
        Get psychological profile for a category path.
        
        Implements relaxed matching with hierarchical fallback:
        1. Exact match on SubCategoryProfile
        2. Parent category match (climb up the hierarchy)
        3. Similar category (fuzzy match)
        4. Domain-level aggregation
        5. Global priors
        
        Args:
            category_path: Full category path (e.g., "Electronics > Computers > Laptops")
            include_parent: Whether to fall back to parent categories
            
        Returns:
            CategoryPsychProfile with match_type indicating the fallback level
        """
        # Check cache
        if category_path in self._category_cache:
            return self._category_cache[category_path]
        
        if not self._connected:
            return self._get_global_category_profile(category_path)
        
        # Try exact match
        profile = self._query_exact_category(category_path)
        if profile:
            self._category_cache[category_path] = profile
            return profile
        
        # Try parent categories
        if include_parent:
            parts = category_path.split(" > ")
            for i in range(len(parts) - 1, 0, -1):
                parent_path = " > ".join(parts[:i])
                profile = self._query_exact_category(parent_path)
                if profile:
                    profile.match_type = "parent"
                    profile.match_confidence = 0.7 + (0.1 * i / len(parts))
                    self._category_cache[category_path] = profile
                    return profile
        
        # Try fuzzy match
        profile = self._query_similar_category(category_path)
        if profile:
            profile.match_type = "similar"
            profile.match_confidence = 0.6
            self._category_cache[category_path] = profile
            return profile
        
        # Try domain-level
        domain = self._infer_domain(category_path)
        profile = self._query_domain_aggregate(domain)
        if profile:
            profile.match_type = "domain"
            profile.match_confidence = 0.4
            self._category_cache[category_path] = profile
            return profile
        
        # Global fallback
        return self._get_global_category_profile(category_path)
    
    def _query_exact_category(self, category_path: str) -> Optional[CategoryPsychProfile]:
        """Query Neo4j for exact category match."""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (p:SubCategoryProfile {category_path: $path})
                    RETURN p.category_path as path,
                           p.level as level,
                           p.review_count as review_count,
                           p.arch_achiever as achiever,
                           p.arch_explorer as explorer,
                           p.arch_connector as connector,
                           p.arch_guardian as guardian,
                           p.arch_pragmatist as pragmatist
                """, path=category_path)
                
                record = result.single()
                if record:
                    total = (record["achiever"] or 0) + (record["explorer"] or 0) + \
                            (record["connector"] or 0) + (record["guardian"] or 0) + \
                            (record["pragmatist"] or 0)
                    
                    if total > 0:
                        archetypes = {
                            "Achiever": (record["achiever"] or 0) / total,
                            "Explorer": (record["explorer"] or 0) / total,
                            "Connector": (record["connector"] or 0) / total,
                            "Guardian": (record["guardian"] or 0) / total,
                            "Pragmatist": (record["pragmatist"] or 0) / total,
                        }
                    else:
                        archetypes = self._global_archetypes.copy()
                    
                    return CategoryPsychProfile(
                        category_path=record["path"],
                        level=record["level"] or 0,
                        review_count=record["review_count"] or 0,
                        archetypes=archetypes,
                        mechanism_effectiveness=self._derive_mechanism_effectiveness(archetypes),
                        match_type="exact",
                        match_confidence=1.0,
                    )
        except Exception as e:
            logger.debug(f"Exact category query failed: {e}")
        
        return None
    
    def _query_similar_category(self, category_path: str) -> Optional[CategoryPsychProfile]:
        """Query Neo4j for similar category (fuzzy match)."""
        # Extract key terms from the path
        terms = [t.strip().lower() for t in category_path.split(">")]
        last_term = terms[-1] if terms else ""
        
        try:
            with self._driver.session() as session:
                # Search for categories containing the last term
                result = session.run("""
                    MATCH (p:SubCategoryProfile)
                    WHERE toLower(p.category_path) CONTAINS $term
                    RETURN p.category_path as path,
                           p.level as level,
                           p.review_count as review_count,
                           p.arch_achiever as achiever,
                           p.arch_explorer as explorer,
                           p.arch_connector as connector,
                           p.arch_guardian as guardian,
                           p.arch_pragmatist as pragmatist
                    ORDER BY p.review_count DESC
                    LIMIT 1
                """, term=last_term)
                
                record = result.single()
                if record:
                    total = (record["achiever"] or 0) + (record["explorer"] or 0) + \
                            (record["connector"] or 0) + (record["guardian"] or 0) + \
                            (record["pragmatist"] or 0)
                    
                    if total > 0:
                        archetypes = {
                            "Achiever": (record["achiever"] or 0) / total,
                            "Explorer": (record["explorer"] or 0) / total,
                            "Connector": (record["connector"] or 0) / total,
                            "Guardian": (record["guardian"] or 0) / total,
                            "Pragmatist": (record["pragmatist"] or 0) / total,
                        }
                    else:
                        archetypes = self._global_archetypes.copy()
                    
                    return CategoryPsychProfile(
                        category_path=record["path"],
                        level=record["level"] or 0,
                        review_count=record["review_count"] or 0,
                        archetypes=archetypes,
                        mechanism_effectiveness=self._derive_mechanism_effectiveness(archetypes),
                        match_type="similar",
                        match_confidence=0.6,
                    )
        except Exception as e:
            logger.debug(f"Similar category query failed: {e}")
        
        return None
    
    def _query_domain_aggregate(self, domain: str) -> Optional[CategoryPsychProfile]:
        """Query Neo4j for domain-level aggregate."""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (p:SubCategoryProfile)
                    WHERE p.category STARTS WITH $domain OR p.category_path STARTS WITH $domain
                    RETURN $domain as domain,
                           count(p) as profile_count,
                           sum(p.review_count) as total_reviews,
                           sum(p.arch_achiever) as achiever,
                           sum(p.arch_explorer) as explorer,
                           sum(p.arch_connector) as connector,
                           sum(p.arch_guardian) as guardian,
                           sum(p.arch_pragmatist) as pragmatist
                """, domain=domain)
                
                record = result.single()
                if record and record["profile_count"] > 0:
                    total = (record["achiever"] or 0) + (record["explorer"] or 0) + \
                            (record["connector"] or 0) + (record["guardian"] or 0) + \
                            (record["pragmatist"] or 0)
                    
                    if total > 0:
                        archetypes = {
                            "Achiever": (record["achiever"] or 0) / total,
                            "Explorer": (record["explorer"] or 0) / total,
                            "Connector": (record["connector"] or 0) / total,
                            "Guardian": (record["guardian"] or 0) / total,
                            "Pragmatist": (record["pragmatist"] or 0) / total,
                        }
                    else:
                        archetypes = self._global_archetypes.copy()
                    
                    return CategoryPsychProfile(
                        category_path=domain,
                        level=0,
                        review_count=record["total_reviews"] or 0,
                        archetypes=archetypes,
                        mechanism_effectiveness=self._derive_mechanism_effectiveness(archetypes),
                        match_type="domain",
                        match_confidence=0.4,
                    )
        except Exception as e:
            logger.debug(f"Domain aggregate query failed: {e}")
        
        return None
    
    def _get_global_category_profile(self, category_path: str) -> CategoryPsychProfile:
        """Return global fallback profile."""
        return CategoryPsychProfile(
            category_path=category_path,
            level=0,
            review_count=0,
            archetypes=self._global_archetypes.copy(),
            mechanism_effectiveness=self._global_mechanisms.copy(),
            match_type="global",
            match_confidence=0.2,
        )
    
    def _infer_domain(self, category_path: str) -> str:
        """Infer domain from category path."""
        path_lower = category_path.lower()
        
        # Map common terms to domains
        domain_keywords = {
            "Electronics": ["electronics", "computer", "phone", "camera", "audio", "tv"],
            "Beauty_and_Personal_Care": ["beauty", "cosmetic", "skincare", "hair", "makeup"],
            "Home_and_Kitchen": ["home", "kitchen", "furniture", "decor", "appliance"],
            "Clothing_Shoes_and_Jewelry": ["clothing", "shoes", "jewelry", "fashion", "apparel"],
            "Sports_and_Outdoors": ["sports", "outdoor", "fitness", "exercise", "athletic"],
            "Books": ["books", "reading", "literature", "fiction"],
            "Toys_and_Games": ["toys", "games", "puzzle", "play"],
            "Health_and_Household": ["health", "vitamin", "supplement", "wellness"],
            "Automotive": ["automotive", "car", "vehicle", "motor"],
            "Pet_Supplies": ["pet", "dog", "cat", "animal"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in path_lower for kw in keywords):
                return domain
        
        # Default to first part of path
        parts = category_path.split(" > ")
        return parts[0].replace(" ", "_") if parts else "General"
    
    def _derive_mechanism_effectiveness(
        self,
        archetypes: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Derive mechanism effectiveness from archetype distribution.
        
        Based on learned patterns from 941M+ review corpus.
        """
        # Archetype-mechanism affinity matrix (learned from reviews)
        affinity = {
            "Achiever": {
                "authority": 0.45, "commitment": 0.40, "scarcity": 0.35,
                "social_proof": 0.30, "liking": 0.25, "reciprocity": 0.20,
            },
            "Explorer": {
                "scarcity": 0.45, "social_proof": 0.35, "liking": 0.35,
                "reciprocity": 0.30, "authority": 0.25, "commitment": 0.20,
            },
            "Connector": {
                "liking": 0.50, "social_proof": 0.45, "reciprocity": 0.40,
                "commitment": 0.30, "authority": 0.20, "scarcity": 0.15,
            },
            "Guardian": {
                "commitment": 0.45, "authority": 0.40, "social_proof": 0.35,
                "liking": 0.30, "reciprocity": 0.25, "scarcity": 0.20,
            },
            "Pragmatist": {
                "reciprocity": 0.45, "scarcity": 0.40, "social_proof": 0.35,
                "authority": 0.30, "liking": 0.25, "commitment": 0.20,
            },
        }
        
        # Weighted combination based on archetype distribution
        effectiveness = {
            "liking": 0.0, "social_proof": 0.0, "commitment": 0.0,
            "reciprocity": 0.0, "authority": 0.0, "scarcity": 0.0,
        }
        
        for arch, weight in archetypes.items():
            if arch in affinity:
                for mech, eff in affinity[arch].items():
                    effectiveness[mech] += weight * eff
        
        return effectiveness
    
    # =========================================================================
    # PRODUCT-LEVEL LOOKUPS
    # =========================================================================
    
    def get_product_psychology(
        self,
        brand: Optional[str] = None,
        product: Optional[str] = None,
        category: Optional[str] = None,
    ) -> CategoryPsychProfile:
        """
        Get psychological profile for a product with brand context.
        
        Fallback order:
        1. Exact product + brand match
        2. Brand-level aggregate
        3. Category-level
        4. Global
        
        Args:
            brand: Brand name (e.g., "Apple")
            product: Product name (e.g., "iPhone 15")
            category: Category path (optional, will be inferred if not provided)
            
        Returns:
            CategoryPsychProfile with appropriate match
        """
        # If category provided, use category lookup
        if category:
            profile = self.get_category_psychology(category)
            
            # If brand provided, try to enhance with brand data
            if brand:
                brand_profile = self._query_brand_psychology(brand)
                if brand_profile:
                    # Blend brand and category profiles
                    profile = self._blend_profiles(profile, brand_profile, brand_weight=0.3)
            
            return profile
        
        # Try brand lookup if no category
        if brand:
            brand_profile = self._query_brand_psychology(brand)
            if brand_profile:
                return brand_profile
        
        # Try to infer category from product name
        if product:
            inferred_category = self._infer_category_from_product(product)
            if inferred_category:
                return self.get_category_psychology(inferred_category)
        
        # Global fallback
        return self._get_global_category_profile(product or brand or "unknown")
    
    def _query_brand_psychology(self, brand: str) -> Optional[CategoryPsychProfile]:
        """Query brand-level psychology from Neo4j."""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (b:Brand {name: $brand})-[:HAS_PSYCHOLOGY]->(p:BrandPsychProfile)
                    RETURN p.archetypes as archetypes,
                           p.mechanism_effectiveness as mechanisms
                    LIMIT 1
                """, brand=brand)
                
                record = result.single()
                if record:
                    archetypes = record.get("archetypes", {})
                    mechanisms = record.get("mechanisms", {})
                    
                    if archetypes:
                        return CategoryPsychProfile(
                            category_path=f"Brand:{brand}",
                            level=0,
                            review_count=0,
                            archetypes=archetypes,
                            mechanism_effectiveness=mechanisms or self._derive_mechanism_effectiveness(archetypes),
                            match_type="brand",
                            match_confidence=0.85,
                        )
        except Exception as e:
            logger.debug(f"Brand psychology query failed: {e}")
        
        return None
    
    def _infer_category_from_product(self, product: str) -> Optional[str]:
        """Infer category from product name using Neo4j."""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (p:SubCategoryProfile)
                    WHERE toLower(p.category_path) CONTAINS toLower($product)
                    RETURN p.category_path as path
                    ORDER BY p.review_count DESC
                    LIMIT 1
                """, product=product)
                
                record = result.single()
                if record:
                    return record["path"]
        except Exception as e:
            logger.debug(f"Category inference query failed: {e}")
        
        return None
    
    def _blend_profiles(
        self,
        primary: CategoryPsychProfile,
        secondary: CategoryPsychProfile,
        brand_weight: float = 0.3,
    ) -> CategoryPsychProfile:
        """Blend two profiles with weighting."""
        cat_weight = 1.0 - brand_weight
        
        blended_archetypes = {}
        for arch in primary.archetypes:
            p_val = primary.archetypes.get(arch, 0)
            s_val = secondary.archetypes.get(arch, 0)
            blended_archetypes[arch] = cat_weight * p_val + brand_weight * s_val
        
        blended_mechanisms = {}
        for mech in primary.mechanism_effectiveness:
            p_val = primary.mechanism_effectiveness.get(mech, 0)
            s_val = secondary.mechanism_effectiveness.get(mech, 0)
            blended_mechanisms[mech] = cat_weight * p_val + brand_weight * s_val
        
        return CategoryPsychProfile(
            category_path=primary.category_path,
            level=primary.level,
            review_count=primary.review_count,
            archetypes=blended_archetypes,
            mechanism_effectiveness=blended_mechanisms,
            match_type=f"blended_{primary.match_type}+{secondary.match_type}",
            match_confidence=primary.match_confidence * 0.8,
        )
    
    # =========================================================================
    # MECHANISM RECOMMENDATIONS
    # =========================================================================
    
    def get_best_mechanisms_for_category(
        self,
        category_path: str,
        top_n: int = 3,
    ) -> List[MechanismRecommendation]:
        """
        Get best persuasion mechanisms for a category.
        
        Returns mechanisms ranked by effectiveness for the category's
        dominant archetypes.
        """
        profile = self.get_category_psychology(category_path)
        
        # Sort mechanisms by effectiveness
        sorted_mechs = sorted(
            profile.mechanism_effectiveness.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        # Get dominant archetype for reasoning
        dominant_arch = max(profile.archetypes.items(), key=lambda x: x[1])
        
        recommendations = []
        for mech, effectiveness in sorted_mechs:
            recommendations.append(MechanismRecommendation(
                mechanism=mech,
                effectiveness=effectiveness,
                confidence=profile.match_confidence,
                source=f"{profile.match_type}_match",
                reasoning=f"{mech.title()} is effective for {dominant_arch[0]} archetype "
                         f"({dominant_arch[1]:.0%} of category audience)",
            ))
        
        return recommendations
    
    def get_mechanism_effectiveness(
        self,
        mechanism: str,
        category_path: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> Tuple[float, float, str]:
        """
        Get effectiveness of a specific mechanism for a context.
        
        Returns:
            (effectiveness, confidence, source) tuple
        """
        if category_path:
            profile = self.get_category_psychology(category_path)
        elif brand:
            profile = self.get_product_psychology(brand=brand)
        else:
            profile = self._get_global_category_profile("global")
        
        effectiveness = profile.mechanism_effectiveness.get(
            mechanism,
            self._global_mechanisms.get(mechanism, 0.3)
        )
        
        return effectiveness, profile.match_confidence, profile.match_type
    
    def get_archetype_mechanism_effectiveness(
        self,
        archetype: str,
    ) -> Dict[str, float]:
        """
        Get mechanism effectiveness scores for an archetype from rich framework data.
        
        This queries the Neo4j graph to compute mechanism effectiveness from:
        1. ProductPsychProfile nodes with framework_scores
        2. Aggregated across all products that attract this archetype
        3. Using Cialdini mechanism mappings from framework dimensions
        
        Args:
            archetype: Customer archetype (e.g., "achiever", "explorer")
            
        Returns:
            Dict of mechanism_name -> effectiveness_score (0-1)
        """
        archetype_lower = archetype.lower()
        
        # Cialdini mechanism to framework dimension mappings
        mechanism_framework_map = {
            "authority": ["authority", "cialdini.authority", "authority_sensitivity", "expert_trust"],
            "social_proof": ["social_proof", "cialdini.social_proof", "social_proof_sensitivity", "consensus"],
            "scarcity": ["scarcity", "cialdini.scarcity", "scarcity_sensitivity", "urgency"],
            "commitment": ["commitment", "cialdini.commitment", "commitment_consistency", "consistency"],
            "reciprocity": ["reciprocity", "cialdini.reciprocity", "reciprocity_norm", "obligation"],
            "liking": ["liking", "cialdini.liking", "affinity", "rapport"],
            "novelty": ["novelty", "novelty_seeking", "curiosity", "exploration"],
            "curiosity": ["curiosity", "need_for_cognition", "information_seeking"],
        }
        
        try:
            with self._driver.session() as session:
                # Query products with this archetype and their framework scores
                result = session.run("""
                    MATCH (p:ProductPsychProfile)
                    WHERE p.has_framework_scores = true
                    AND p[$archetype_prop] > 0.3
                    RETURN p.framework_scores_json as fw_json,
                           p[$archetype_prop] as arch_score,
                           p.social_proof_sensitivity as social_proof,
                           p.authority_sensitivity as authority,
                           p.scarcity_sensitivity as scarcity,
                           p.commitment_consistency as commitment,
                           p.reciprocity_norm as reciprocity
                    LIMIT 1000
                """, archetype_prop=archetype_lower)
                
                # Aggregate mechanism scores
                mechanism_totals = {mech: [] for mech in mechanism_framework_map.keys()}
                
                for record in result:
                    arch_weight = record.get("arch_score", 0.5)
                    
                    # Use direct property values if available
                    if record.get("social_proof") is not None:
                        mechanism_totals["social_proof"].append(record["social_proof"] * arch_weight)
                    if record.get("authority") is not None:
                        mechanism_totals["authority"].append(record["authority"] * arch_weight)
                    if record.get("scarcity") is not None:
                        mechanism_totals["scarcity"].append(record["scarcity"] * arch_weight)
                    if record.get("commitment") is not None:
                        mechanism_totals["commitment"].append(record["commitment"] * arch_weight)
                    if record.get("reciprocity") is not None:
                        mechanism_totals["reciprocity"].append(record["reciprocity"] * arch_weight)
                    
                    # Parse framework JSON for additional dimensions
                    fw_json = record.get("fw_json")
                    if fw_json:
                        try:
                            import json
                            frameworks = json.loads(fw_json)
                            
                            for mech, fw_keys in mechanism_framework_map.items():
                                for fw_key in fw_keys:
                                    if fw_key in frameworks:
                                        score = frameworks[fw_key]
                                        if isinstance(score, (int, float)):
                                            mechanism_totals[mech].append(score * arch_weight)
                        except (json.JSONDecodeError, TypeError):
                            pass
                
                # Compute weighted averages
                mechanism_effectiveness = {}
                for mech, scores in mechanism_totals.items():
                    if scores:
                        mechanism_effectiveness[mech] = min(1.0, sum(scores) / len(scores))
                    else:
                        # Default values based on archetype research
                        mechanism_effectiveness[mech] = self._default_archetype_mechanism(archetype_lower, mech)
                
                if mechanism_effectiveness:
                    logger.debug(f"Computed mechanism effectiveness for {archetype}: {len(mechanism_effectiveness)} mechanisms")
                    return mechanism_effectiveness
                    
        except Exception as e:
            logger.debug(f"Archetype mechanism query failed: {e}")
        
        # Fallback to defaults
        return self._get_default_archetype_mechanisms(archetype_lower)
    
    def _default_archetype_mechanism(self, archetype: str, mechanism: str) -> float:
        """Get default mechanism score for archetype (research-based fallback)."""
        defaults = {
            "achiever": {"authority": 0.85, "social_proof": 0.75, "scarcity": 0.70, "commitment": 0.65, "reciprocity": 0.55, "liking": 0.50, "novelty": 0.60, "curiosity": 0.55},
            "guardian": {"commitment": 0.85, "authority": 0.80, "scarcity": 0.75, "social_proof": 0.65, "liking": 0.60, "reciprocity": 0.55, "novelty": 0.40, "curiosity": 0.45},
            "explorer": {"novelty": 0.90, "curiosity": 0.85, "social_proof": 0.65, "authority": 0.50, "scarcity": 0.55, "commitment": 0.45, "liking": 0.60, "reciprocity": 0.50},
            "connector": {"social_proof": 0.90, "liking": 0.85, "reciprocity": 0.80, "authority": 0.55, "scarcity": 0.50, "commitment": 0.60, "novelty": 0.55, "curiosity": 0.50},
            "analyzer": {"authority": 0.90, "commitment": 0.75, "curiosity": 0.80, "social_proof": 0.60, "reciprocity": 0.55, "scarcity": 0.50, "novelty": 0.65, "liking": 0.45},
            "pragmatist": {"reciprocity": 0.85, "commitment": 0.80, "authority": 0.70, "scarcity": 0.65, "social_proof": 0.60, "liking": 0.55, "novelty": 0.50, "curiosity": 0.55},
        }
        return defaults.get(archetype, {}).get(mechanism, 0.5)
    
    def _get_default_archetype_mechanisms(self, archetype: str) -> Dict[str, float]:
        """Get all default mechanism scores for an archetype."""
        mechanisms = ["authority", "social_proof", "scarcity", "commitment", "reciprocity", "liking", "novelty", "curiosity"]
        return {m: self._default_archetype_mechanism(archetype, m) for m in mechanisms}
    
    # =========================================================================
    # CUSTOMER TYPE LOOKUPS
    # =========================================================================
    
    def get_customer_types_for_category(
        self,
        category_path: str,
        top_n: int = 5,
    ) -> List[CustomerTypeProfile]:
        """
        Get most likely customer types for a category.
        
        Queries CustomerTypeGranular nodes based on the category's
        archetype distribution.
        """
        profile = self.get_category_psychology(category_path)
        
        # Get dominant archetype
        dominant_arch = max(profile.archetypes.items(), key=lambda x: x[1])
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (ct:CustomerTypeGranular)
                    WHERE ct.base_archetype = $archetype
                    RETURN ct.type_id as type_id,
                           ct.base_archetype as archetype,
                           ct.primary_dimension as dimension,
                           ct.domain as domain
                    LIMIT $limit
                """, archetype=dominant_arch[0], limit=top_n)
                
                types = []
                for record in result:
                    types.append(CustomerTypeProfile(
                        type_id=record["type_id"],
                        base_archetype=record["archetype"],
                        primary_dimension=record["dimension"],
                        domain=record["domain"] or "general",
                    ))
                
                return types
        except Exception as e:
            logger.debug(f"Customer type query failed: {e}")
        
        # Return default types based on dominant archetype
        return [CustomerTypeProfile(
            type_id=f"{dominant_arch[0].lower()}_default",
            base_archetype=dominant_arch[0],
            primary_dimension="general",
            domain="general",
        )]
    
    # =========================================================================
    # CATEGORY HIERARCHY NAVIGATION
    # =========================================================================
    
    def get_category_hierarchy(
        self,
        root_category: Optional[str] = None,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get category hierarchy from Neo4j.
        
        Useful for populating dropdowns in the demo.
        
        Args:
            root_category: Starting category (None for top-level)
            max_depth: Maximum depth to traverse
            
        Returns:
            List of category dicts with children
        """
        try:
            with self._driver.session() as session:
                if root_category:
                    # Get children of a specific category
                    result = session.run("""
                        MATCH (p:AmazonCategoryLevel {name: $root})-[:CHILD_OF*0..$depth]->(c:AmazonCategoryLevel)
                        RETURN DISTINCT c.name as name, c.level as level, c.product_count as count
                        ORDER BY c.product_count DESC
                        LIMIT 50
                    """, root=root_category, depth=max_depth)
                else:
                    # Get top-level categories
                    result = session.run("""
                        MATCH (c:AmazonCategoryLevel {level: 0})
                        RETURN c.name as name, c.level as level, c.product_count as count
                        ORDER BY c.product_count DESC
                        LIMIT 50
                    """)
                
                categories = []
                for record in result:
                    categories.append({
                        "name": record["name"],
                        "level": record["level"],
                        "product_count": record["count"] or 0,
                    })
                
                return categories
        except Exception as e:
            logger.debug(f"Category hierarchy query failed: {e}")
        
        # Return default categories
        return [
            {"name": "Electronics", "level": 0, "product_count": 0},
            {"name": "Beauty_and_Personal_Care", "level": 0, "product_count": 0},
            {"name": "Home_and_Kitchen", "level": 0, "product_count": 0},
            {"name": "Clothing_Shoes_and_Jewelry", "level": 0, "product_count": 0},
            {"name": "Sports_and_Outdoors", "level": 0, "product_count": 0},
        ]
    
    def get_subcategories(self, parent_category: str) -> List[str]:
        """Get subcategories of a parent category."""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (parent:AmazonCategoryLevel {name: $parent})<-[:CHILD_OF]-(child:AmazonCategoryLevel)
                    RETURN DISTINCT child.name as name
                    ORDER BY child.name
                    LIMIT 100
                """, parent=parent_category)
                
                return [record["name"] for record in result]
        except Exception as e:
            logger.debug(f"Subcategory query failed: {e}")
        
        return []
    
    # =========================================================================
    # REGIONAL PSYCHOLOGY
    # =========================================================================
    
    def get_regional_psychology(self, state: str) -> Dict[str, Any]:
        """Get regional psychology for a US state."""
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (r:RegionalProfile {state: $state})
                    RETURN r.archetype_distribution as archetypes,
                           r.cultural_values as cultural_values,
                           r.political_lean as political_lean,
                           r.traditionalism as traditionalism
                """, state=state)
                
                record = result.single()
                if record:
                    return {
                        "state": state,
                        "archetypes": record["archetypes"] or {},
                        "cultural_values": record["cultural_values"] or {},
                        "political_lean": record["political_lean"],
                        "traditionalism": record["traditionalism"],
                    }
        except Exception as e:
            logger.debug(f"Regional psychology query failed: {e}")
        
        # Return neutral defaults
        return {
            "state": state,
            "archetypes": self._global_archetypes,
            "cultural_values": {},
            "political_lean": 0.0,
            "traditionalism": 0.5,
        }
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the embedded learnings."""
        stats = {
            "connected": self._connected,
            "cached_categories": len(self._category_cache),
            "cached_customer_types": len(self._customer_type_cache),
        }
        
        if self._connected:
            try:
                with self._driver.session() as session:
                    # Count key node types
                    result = session.run("""
                        MATCH (n)
                        WHERE n:SubCategoryProfile OR n:AmazonCategoryLevel 
                              OR n:CustomerTypeGranular OR n:RegionalProfile
                              OR n:CategoryGranular
                        RETURN labels(n)[0] as label, count(n) as count
                    """)
                    
                    stats["nodes"] = {}
                    for record in result:
                        stats["nodes"][record["label"]] = record["count"]
            except Exception as e:
                logger.debug(f"Statistics query failed: {e}")
        
        return stats


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

def get_review_learnings_service() -> ReviewLearningsService:
    """Get the singleton ReviewLearningsService instance."""
    return ReviewLearningsService.get_instance()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_category_psychology(category_path: str) -> CategoryPsychProfile:
    """Convenience function to get category psychology."""
    return get_review_learnings_service().get_category_psychology(category_path)


def get_product_psychology(
    brand: Optional[str] = None,
    product: Optional[str] = None,
    category: Optional[str] = None,
) -> CategoryPsychProfile:
    """Convenience function to get product psychology."""
    return get_review_learnings_service().get_product_psychology(brand, product, category)


def get_best_mechanisms(
    category_path: str,
    top_n: int = 3,
) -> List[MechanismRecommendation]:
    """Convenience function to get best mechanisms for category."""
    return get_review_learnings_service().get_best_mechanisms_for_category(category_path, top_n)


def get_category_hierarchy(
    root: Optional[str] = None,
    depth: int = 3,
) -> List[Dict[str, Any]]:
    """Convenience function to get category hierarchy."""
    return get_review_learnings_service().get_category_hierarchy(root, depth)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 70)
    print("REVIEW LEARNINGS SERVICE TEST")
    print("=" * 70)
    
    service = get_review_learnings_service()
    
    # Test statistics
    stats = service.get_statistics()
    print(f"\nStatistics:")
    print(json.dumps(stats, indent=2))
    
    # Test category lookups
    test_paths = [
        "Electronics > Computers & Accessories > Laptops",
        "Beauty & Personal Care > Skin Care > Face",
        "Home & Kitchen > Kitchen & Dining > Coffee",
        "Nonexistent > Category > Path",
    ]
    
    print("\n" + "=" * 70)
    print("CATEGORY PSYCHOLOGY LOOKUPS")
    print("=" * 70)
    
    for path in test_paths:
        print(f"\n{path}:")
        profile = service.get_category_psychology(path)
        print(f"  Match: {profile.match_type} (confidence: {profile.match_confidence:.2f})")
        print(f"  Reviews: {profile.review_count:,}")
        print(f"  Dominant archetype: {max(profile.archetypes.items(), key=lambda x: x[1])}")
        
        best_mechs = service.get_best_mechanisms_for_category(path, top_n=3)
        print(f"  Best mechanisms:")
        for rec in best_mechs:
            print(f"    - {rec.mechanism}: {rec.effectiveness:.1%}")
    
    # Test category hierarchy
    print("\n" + "=" * 70)
    print("CATEGORY HIERARCHY")
    print("=" * 70)
    
    top_cats = service.get_category_hierarchy()
    print(f"\nTop-level categories: {len(top_cats)}")
    for cat in top_cats[:5]:
        print(f"  - {cat['name']} ({cat['product_count']:,} products)")
