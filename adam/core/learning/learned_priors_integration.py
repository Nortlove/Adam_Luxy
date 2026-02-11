# =============================================================================
# ADAM Learned Priors Integration
# Location: adam/core/learning/learned_priors_integration.py
# =============================================================================

"""
LEARNED PRIORS INTEGRATION

Integrates learned priors from the deep learning process into system components:

1. Thompson Sampling warm-start - Initialize posteriors from learned effectiveness
2. Cold Start transfer priors - Use category/cluster priors for new users
3. Mechanism effectiveness lookup - Get best mechanisms per archetype
4. Calibration adjustment - Apply Platt scaling to confidence outputs

This module bridges the learning artifacts to runtime decision-making.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# PATHS TO LEARNING ARTIFACTS
# =============================================================================

LEARNING_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "learning"

THOMPSON_WARM_START_PATH = LEARNING_DATA_DIR / "thompson_sampling_warm_start.json"
CATEGORY_TRANSFER_PRIORS_PATH = LEARNING_DATA_DIR / "category_transfer_priors.json"
ARCHETYPE_MECHANISM_MATRIX_PATH = LEARNING_DATA_DIR / "archetype_mechanism_matrix_augmented.json"
CALIBRATION_CONFIG_PATH = LEARNING_DATA_DIR / "calibration_config.json"

# NEW: Complete cold-start priors from 941M+ review corpus
COMPLETE_COLDSTART_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"

# POST-INGESTION: Merged priors from unified ingestion (Phase 1.3)
# Produced by scripts/merge_ingestion_priors.py from all *_result.json files
INGESTION_MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "ingestion_merged_priors.json"

# Additional learning artifacts
BRAND_LOYALTY_PATH = LEARNING_DATA_DIR / "brand_loyalty_patterns.json"
TEMPORAL_PATTERNS_PATH = LEARNING_DATA_DIR / "temporal_patterns.json"
PRICE_SENSITIVITY_PATH = LEARNING_DATA_DIR / "price_sensitivity_profiles.json"
LINGUISTIC_PROFILES_PATH = LEARNING_DATA_DIR / "linguistic_profiles.json"


# =============================================================================
# LEARNED PRIORS SERVICE
# =============================================================================

class LearnedPriorsService:
    """
    Service providing access to learned priors throughout the ADAM system.
    
    This is the bridge between offline learning and online decision-making.
    
    PRIORS AVAILABLE (from 941M+ review corpus):
    - Thompson Sampling warm-start (mechanism effectiveness per archetype)
    - Category → Archetype priors (7 categories learned)
    - Brand → Archetype priors (100 brands learned)
    - Reviewer lifecycle patterns (new/casual/engaged/power_user)
    - Brand loyalty segments (loyalist/selective/explorer)
    - Temporal engagement patterns (best hours per archetype)
    - Price tier preferences (budget/mid_range/premium/luxury)
    - Global archetype distribution
    """
    
    _instance = None
    
    def __init__(self):
        self._thompson_warm_start: Dict = {}
        self._category_priors: Dict = {}
        self._cluster_priors: Dict = {}
        self._cluster_definitions: Dict = {}
        self._archetype_mechanism_matrix: Dict = {}
        self._calibration_config: Dict = {}
        
        # NEW: Complete cold-start priors from 941M+ reviews
        self._complete_coldstart_priors: Dict = {}
        self._brand_archetype_priors: Dict = {}
        self._reviewer_lifecycle: Dict = {}
        self._brand_loyalty_segments: Dict = {}
        self._temporal_patterns: Dict = {}
        self._price_tier_preferences: Dict = {}
        self._global_archetype_distribution: Dict = {}
        self._source_statistics: Dict = {}
        
        # LOCATION-AWARE PRIORS (from Google Reviews)
        self._state_archetype_priors: Dict = {}
        self._region_archetype_priors: Dict = {}
        self._density_archetype_priors: Dict = {}
        self._business_response_archetypes: Dict = {}
        self._response_time_by_archetype: Dict = {}
        self._state_category_preferences: Dict = {}
        self._photo_upload_by_archetype: Dict = {}
        self._multi_state_patterns: Dict = {}
        
        # ENHANCED PSYCHOLINGUISTIC PRIORS (from Yelp Enhanced Analysis)
        self._linguistic_fingerprints: Dict = {}
        self._complaint_patterns: Dict = {}
        self._praise_patterns: Dict = {}
        self._trust_loyalty_patterns: Dict = {}
        self._sentiment_intensity: Dict = {}
        self._temporal_behavior: Dict = {}
        self._user_profile_patterns: Dict = {}
        
        # PERSUASION PRIORS (Cialdini Principles)
        self._persuasion_sensitivity: Dict = {}
        self._emotion_sensitivity: Dict = {}
        self._decision_styles: Dict = {}
        self._social_influence_type: Dict = {}
        
        # POST-INGESTION: Merged priors from unified ingestion (Phase 2.1)
        # Loaded from data/learning/ingestion_merged_priors.json
        self._ingestion_merged_priors: Dict = {}
        self._ingestion_effectiveness_matrix: Dict = {}  # archetype → mechanism → {success_rate, alpha, beta}
        self._ingestion_archetype_distribution: Dict = {}  # global + by_category
        self._ingestion_dimension_distributions: Dict = {}  # 430+ dimensional priors
        self._ingestion_product_ad_profiles: Dict = {}  # product psychology aggregates
        
        # NDF (Nonconscious Decision Fingerprint) population priors (from ingestion)
        self._ndf_population: Dict = {}  # {ndf_means, ndf_stds, ndf_distributions}
        self._ndf_archetype_profiles: Dict = {}  # {archetype: {dim: mean_value}}
        self._ndf_category_profiles: Dict = {}  # {category: {ndf_means: {...}}}
        
        # Google hyperlocal (state/vertical/category/price NDF + location profiles) from ingestion_merged_priors
        self._google_hyperlocal: Dict = {}
        
        self._loaded = False
    
    @classmethod
    def get_instance(cls) -> "LearnedPriorsService":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load_all_priors()
        return cls._instance
    
    def load_all_priors(self) -> bool:
        """Load all learned priors from artifacts."""
        
        success = True
        
        # =====================================================================
        # COMPLETE COLD-START PRIORS (941M+ reviews) - Load first as primary
        # =====================================================================
        if COMPLETE_COLDSTART_PRIORS_PATH.exists():
            try:
                with open(COMPLETE_COLDSTART_PRIORS_PATH) as f:
                    self._complete_coldstart_priors = json.load(f)
                
                # Extract sub-components for easy access
                self._brand_archetype_priors = self._complete_coldstart_priors.get("brand_archetype_priors", {})
                self._reviewer_lifecycle = self._complete_coldstart_priors.get("reviewer_lifecycle", {})
                self._brand_loyalty_segments = self._complete_coldstart_priors.get("brand_loyalty_segments", {})
                self._temporal_patterns = self._complete_coldstart_priors.get("temporal_patterns", {})
                self._price_tier_preferences = self._complete_coldstart_priors.get("price_tier_preferences", {})
                self._global_archetype_distribution = self._complete_coldstart_priors.get("global_archetype_distribution", {})
                self._source_statistics = self._complete_coldstart_priors.get("source_statistics", {})
                
                # Merge category priors from complete cold-start (richer data)
                complete_category_priors = self._complete_coldstart_priors.get("category_archetype_priors", {})
                if complete_category_priors:
                    self._category_priors.update(complete_category_priors)
                
                # LOCATION-AWARE PRIORS (from Google Reviews)
                self._state_archetype_priors = self._complete_coldstart_priors.get("state_archetype_priors", {})
                self._region_archetype_priors = self._complete_coldstart_priors.get("region_archetype_priors", {})
                self._density_archetype_priors = self._complete_coldstart_priors.get("density_archetype_priors", {})
                self._business_response_archetypes = self._complete_coldstart_priors.get("business_response_archetypes", {})
                self._response_time_by_archetype = self._complete_coldstart_priors.get("response_time_by_archetype", {})
                self._state_category_preferences = self._complete_coldstart_priors.get("state_category_preferences", {})
                self._photo_upload_by_archetype = self._complete_coldstart_priors.get("photo_upload_by_archetype", {})
                self._multi_state_patterns = self._complete_coldstart_priors.get("multi_state_patterns", {})
                
                # ENHANCED PSYCHOLINGUISTIC PRIORS
                self._linguistic_fingerprints = self._complete_coldstart_priors.get("linguistic_style_fingerprints", {})
                self._complaint_patterns = self._complete_coldstart_priors.get("complaint_patterns_by_archetype", {})
                self._praise_patterns = self._complete_coldstart_priors.get("praise_patterns_by_archetype", {})
                self._trust_loyalty_patterns = self._complete_coldstart_priors.get("trust_loyalty_patterns", {})
                self._sentiment_intensity = self._complete_coldstart_priors.get("sentiment_intensity_by_archetype", {})
                self._temporal_behavior = self._complete_coldstart_priors.get("temporal_behavior_patterns", {})
                self._user_profile_patterns = self._complete_coldstart_priors.get("yelp_user_profile_patterns", {})
                
                # PERSUASION PRIORS
                self._persuasion_sensitivity = self._complete_coldstart_priors.get("archetype_persuasion_sensitivity", {})
                self._emotion_sensitivity = self._complete_coldstart_priors.get("archetype_emotion_sensitivity", {})
                self._decision_styles = self._complete_coldstart_priors.get("archetype_decision_styles", {})
                self._social_influence_type = self._complete_coldstart_priors.get("archetype_social_influence_type", {})
                
                total_reviews = sum(s.get("reviews", 0) for s in self._source_statistics.values())
                logger.info(f"Loaded complete cold-start priors: {total_reviews:,} reviews, "
                           f"{len(self._brand_archetype_priors)} brands, "
                           f"{len(complete_category_priors)} categories, "
                           f"{len(self._state_archetype_priors)} states")
            except Exception as e:
                logger.warning(f"Failed to load complete cold-start priors: {e}")
        
        # =====================================================================
        # POST-INGESTION MERGED PRIORS (Phase 2.1)
        # From data/learning/ingestion_merged_priors.json
        # Produced by scripts/merge_ingestion_priors.py
        # =====================================================================
        if INGESTION_MERGED_PRIORS_PATH.exists():
            try:
                with open(INGESTION_MERGED_PRIORS_PATH) as f:
                    self._ingestion_merged_priors = json.load(f)
                
                # The merge script outputs "global_effectiveness_matrix" (not "effectiveness_matrix")
                self._ingestion_effectiveness_matrix = (
                    self._ingestion_merged_priors.get("global_effectiveness_matrix")
                    or self._ingestion_merged_priors.get("effectiveness_matrix")
                    or {}
                )
                self._ingestion_archetype_distribution = (
                    self._ingestion_merged_priors.get("global_archetype_distribution")
                    or self._ingestion_merged_priors.get("archetype_distribution")
                    or {}
                )
                self._ingestion_dimension_distributions = self._ingestion_merged_priors.get(
                    "dimension_distributions", {}
                )
                self._ingestion_product_ad_profiles = self._ingestion_merged_priors.get(
                    "product_ad_profiles", {}
                )
                
                # =====================================================================
                # NDF POPULATION PRIORS (from ndf_population in merged priors)
                # =====================================================================
                ndf_pop = self._ingestion_merged_priors.get("ndf_population", {})
                if ndf_pop and ndf_pop.get("ndf_count", 0) > 0:
                    self._ndf_population = {
                        "ndf_count": ndf_pop.get("ndf_count", 0),
                        "ndf_means": ndf_pop.get("ndf_means", {}),
                        "ndf_stds": ndf_pop.get("ndf_stds", {}),
                        "ndf_distributions": ndf_pop.get("ndf_distributions", {}),
                    }
                    # Support both merge output (ndf_by_archetype) and single-source (ndf_archetype_profiles)
                    self._ndf_archetype_profiles = ndf_pop.get("ndf_archetype_profiles") or ndf_pop.get("ndf_by_archetype") or {}
                    
                    logger.info(
                        f"Loaded NDF population priors: {self._ndf_population['ndf_count']:,} reviews, "
                        f"{len(self._ndf_archetype_profiles)} archetype profiles"
                    )
                
                # Google hyperlocal (state/vertical/category/price NDF) for geo-aware targeting
                self._google_hyperlocal = self._ingestion_merged_priors.get("google_hyperlocal", {})
                if self._google_hyperlocal and self._google_hyperlocal.get("state_ndf_profiles"):
                    logger.info(
                        f"Loaded Google hyperlocal: {len(self._google_hyperlocal.get('state_ndf_profiles', {}))} states, "
                        f"{len(self._google_hyperlocal.get('vertical_ndf_profiles', {}))} verticals"
                    )
                
                # Also load per-category NDF from category results if available
                category_ndf = self._ingestion_merged_priors.get("category_ndf_profiles", {})
                if category_ndf:
                    self._ndf_category_profiles = category_ndf
                    logger.info(f"Loaded {len(category_ndf)} category-level NDF profiles")
                
                total = self._ingestion_merged_priors.get("total_reviews_processed", 0)
                cats = self._ingestion_merged_priors.get("amazon_categories", 0) or self._ingestion_merged_priors.get("categories_merged", 0)
                archs = len(self._ingestion_effectiveness_matrix)
                logger.info(
                    f"Loaded ingestion merged priors: {total:,} reviews, "
                    f"{cats} categories, {archs} archetypes in effectiveness matrix"
                )
            except Exception as e:
                logger.warning(f"Failed to load ingestion merged priors: {e}")
        
        # =====================================================================
        # THOMPSON WARM-START
        # =====================================================================
        if THOMPSON_WARM_START_PATH.exists():
            try:
                with open(THOMPSON_WARM_START_PATH) as f:
                    self._thompson_warm_start = json.load(f)
                logger.info(f"Loaded Thompson warm-start: {len(self._thompson_warm_start)} archetypes")
            except Exception as e:
                logger.warning(f"Failed to load Thompson warm-start: {e}")
                success = False
        
        # =====================================================================
        # CATEGORY TRANSFER PRIORS (supplement if not from complete cold-start)
        # =====================================================================
        if CATEGORY_TRANSFER_PRIORS_PATH.exists():
            try:
                with open(CATEGORY_TRANSFER_PRIORS_PATH) as f:
                    data = json.load(f)
                    # Only use if not already loaded from complete cold-start
                    if not self._category_priors:
                        self._category_priors = data.get("category_priors", {})
                    self._cluster_priors = data.get("cluster_priors", {})
                    self._cluster_definitions = data.get("cluster_definitions", {})
                logger.info(f"Loaded category priors: {len(self._category_priors)} categories")
            except Exception as e:
                logger.warning(f"Failed to load category priors: {e}")
                success = False
        
        # =====================================================================
        # ARCHETYPE-MECHANISM MATRIX
        # =====================================================================
        if ARCHETYPE_MECHANISM_MATRIX_PATH.exists():
            try:
                with open(ARCHETYPE_MECHANISM_MATRIX_PATH) as f:
                    self._archetype_mechanism_matrix = json.load(f)
                logger.info(f"Loaded mechanism matrix: {len(self._archetype_mechanism_matrix)} archetypes")
            except Exception as e:
                logger.warning(f"Failed to load mechanism matrix: {e}")
                # Try non-augmented version
                fallback_path = LEARNING_DATA_DIR / "archetype_mechanism_matrix.json"
                if fallback_path.exists():
                    with open(fallback_path) as f:
                        self._archetype_mechanism_matrix = json.load(f)
                    logger.info("Loaded fallback mechanism matrix")
                else:
                    success = False
        
        # =====================================================================
        # CALIBRATION CONFIG
        # =====================================================================
        if CALIBRATION_CONFIG_PATH.exists():
            try:
                with open(CALIBRATION_CONFIG_PATH) as f:
                    self._calibration_config = json.load(f)
                logger.info("Loaded calibration config")
            except Exception as e:
                logger.warning(f"Failed to load calibration config: {e}")
                success = False
        
        self._loaded = success
        return success
    
    # =========================================================================
    # POST-INGESTION ACCESSORS (Phase 2.1)
    # Used by LangGraph nodes: load_ingestion_dimensional_priors,
    # calculate_customer_ad_alignment, and Thompson warm-start update
    # =========================================================================
    
    def get_ingestion_dimensional_priors(self, category: str = "") -> Dict:
        """
        Get dimensional priors from ingestion for a category.
        
        Returns 430+ dimensional distributions (motivation, decision style,
        mechanism receptivity, etc.) aggregated from the review corpus.
        
        Args:
            category: Product category name (empty = global aggregate)
        
        Returns:
            Dict with dimensional distributions.
            Keys: motivation_distribution, decision_style_distribution,
                  mechanism_receptivity, persuasion_techniques, etc.
        """
        dims = self._ingestion_dimension_distributions
        if not dims:
            return {}
        
        # Currently we only have global aggregates (category-level TODO)
        # Return proportions from each dimension
        result = {}
        for key, value in dims.items():
            if key in ("categories_with_dimensions", "total_reviews_with_dimensions", "note"):
                continue
            if isinstance(value, dict) and "proportions" in value:
                result[key] = value["proportions"]
            elif isinstance(value, dict):
                result[key] = value
        
        return result
    
    def get_ingestion_archetype_distribution(self, category: str = "") -> Dict[str, float]:
        """
        Get archetype distribution from ingestion.
        
        These are TRUE population base rates derived from 560M+ reviews,
        not uniform assumptions.
        
        Args:
            category: Category name (empty = global distribution)
        
        Returns:
            Dict mapping archetype name → proportion (sums to ~1.0)
        """
        ad = self._ingestion_archetype_distribution
        if not ad:
            return {}
        
        # Try category-specific first
        if category:
            by_cat = ad.get("by_category", {})
            if category in by_cat:
                return by_cat[category]
        
        # Fall back to global
        return ad.get("global", {})
    
    def get_ingestion_effectiveness(self, archetype: str = "") -> Dict:
        """
        Get mechanism effectiveness from ingestion.
        
        Provides success_rate + Beta(alpha, beta) per archetype × mechanism,
        derived from empirical review corpus data.
        
        Args:
            archetype: Archetype name (empty = all archetypes)
        
        Returns:
            Dict of {mechanism: {success_rate, sample_size, alpha, beta}}
            or full matrix if no archetype specified.
        """
        em = self._ingestion_effectiveness_matrix
        if not em:
            return {}
        
        if archetype:
            return em.get(archetype, em.get(archetype.lower(), {}))
        
        return em
    
    def get_ingestion_product_ad_profiles_summary(self) -> Dict:
        """
        Get aggregated product ad profile statistics from ingestion.
        
        Returns distributions of persuasion techniques, emotional appeals,
        value propositions, and linguistic styles across all profiled products.
        """
        return self._ingestion_product_ad_profiles
    
    # =========================================================================
    # EXTENDED POST-INGESTION ACCESSORS (Phase 2.1 expansion)
    # These feed the 30-atom DAG, Thompson warm-start, ColdStartService,
    # and the ML hybrid extraction system.
    # =========================================================================
    
    def get_journey_stage_prior(self, category: str = "") -> Dict[str, float]:
        """
        Get journey stage distribution from ingestion data.
        
        Maps to UserStateAtom (journey position inference).
        Returns {stage: proportion} where stages include:
        awareness, consideration, decision, post_purchase, loyalty.
        """
        dims = self.get_ingestion_dimensional_priors(category)
        return dims.get("journey_stage_distribution", dims.get("journey_stage", {}))
    
    def get_price_sensitivity_prior(self, category: str = "") -> Dict[str, float]:
        """
        Get price sensitivity distribution from ingestion data.
        
        Maps to MechanismActivationAtom (scarcity calibration).
        High sensitivity → scarcity mechanism more effective.
        Returns {level: proportion} e.g. {high: 0.3, moderate: 0.5, low: 0.2}
        """
        dims = self.get_ingestion_dimensional_priors(category)
        return dims.get("price_sensitivity_distribution", dims.get("price_sensitivity", {}))
    
    def get_expertise_prior(self, category: str = "") -> Dict[str, float]:
        """
        Get expertise distribution from ingestion data.
        
        Maps to ConstrualLevelAtom (complexity calibration).
        Experts need different authority cues than novices.
        Returns {level: proportion} e.g. {expert: 0.2, intermediate: 0.5, novice: 0.3}
        """
        dims = self.get_ingestion_dimensional_priors(category)
        return dims.get("expertise_distribution", dims.get("expertise", {}))
    
    def get_pain_status_prior(self, category: str = "") -> Dict[str, float]:
        """
        Get pain/need urgency distribution from ingestion data.
        
        Maps to UserStateAtom (receptivity assessment).
        Acute pain → higher urgency appropriateness.
        Returns {status: proportion} e.g. {acute: 0.2, chronic: 0.3, aspirational: 0.5}
        """
        dims = self.get_ingestion_dimensional_priors(category)
        return dims.get("pain_status_distribution", dims.get("pain_points", {}))
    
    def get_credibility_prior(self, category: str = "") -> Dict[str, float]:
        """
        Get review credibility distribution from ingestion data.
        
        Maps to ReviewIntelligenceAtom (confidence weighting).
        Returns {level: proportion} e.g. {high: 0.4, moderate: 0.4, low: 0.2}
        """
        dims = self.get_ingestion_dimensional_priors(category)
        return dims.get("credibility_distribution", dims.get("review_credibility", {}))
    
    def get_product_category_profile(self, category: str) -> Dict[str, str]:
        """
        Get dominant psychological profile for a product category.
        
        Maps to BrandPersonalityAtom (fallback profiling), AdSelectionAtom.
        Returns {dominant_persuasion, dominant_emotion, dominant_value, dominant_style}
        """
        profiles = self._ingestion_product_ad_profiles
        if not profiles:
            return {}
        
        cat_profiles = profiles.get("category_product_profiles", {})
        return cat_profiles.get(category, {})
    
    def get_thompson_warm_start_from_ingestion(
        self,
        archetype: str,
        category: str = "",
    ) -> Dict[str, Dict[str, float]]:
        """
        Get Beta distribution parameters for Thompson Sampling warm-start
        from ingestion effectiveness data.
        
        Converts effectiveness_matrix success_rates into Beta(alpha, beta)
        parameters with proper sample size weighting.
        
        Returns {mechanism: {"alpha": float, "beta": float, "success_rate": float}}
        """
        # Try category-specific first
        if category:
            cat_matrices = {}
            try:
                merged_path = Path(__file__).resolve().parent.parent.parent / "data" / "learning" / "ingestion_merged_priors.json"
                if merged_path.exists():
                    import json
                    with open(merged_path) as f:
                        merged = json.load(f)
                    cat_matrices = merged.get("category_effectiveness_matrices", {})
            except Exception:
                pass
            
            cat_matrix = cat_matrices.get(category, {})
            arch_data = cat_matrix.get(archetype, cat_matrix.get(archetype.lower(), {}))
            if arch_data:
                result = {}
                for mech, stats in arch_data.items():
                    sr = stats.get("success_rate", 0.5)
                    ss = min(stats.get("sample_size", 10), 1000)  # Cap to prevent over-confident priors
                    result[mech] = {
                        "alpha": max(1.0, sr * ss),
                        "beta": max(1.0, (1 - sr) * ss),
                        "success_rate": sr,
                    }
                return result
        
        # Fall back to global effectiveness
        effectiveness = self.get_ingestion_effectiveness(archetype)
        result = {}
        for mech, stats in effectiveness.items():
            if isinstance(stats, dict):
                sr = stats.get("success_rate", 0.5)
                ss = min(stats.get("sample_size", 10), 1000)
                result[mech] = {
                    "alpha": max(1.0, sr * ss),
                    "beta": max(1.0, (1 - sr) * ss),
                    "success_rate": sr,
                }
        
        return result
    
    def get_ndf_for_new_atoms(self, archetype: str = "", category: str = "") -> Dict[str, float]:
        """
        Get NDF population priors formatted for the 19 new atoms.
        
        The new atoms (Game Theory, Decision Science, Cutting-Edge) all
        query NDF profiles. This method provides the best available
        population prior for their NDF-based calculations.
        """
        if archetype:
            profile = self.get_ndf_archetype_profile(archetype)
            if profile:
                return profile
        
        if category:
            cat_profile = self.get_ndf_category_profile(category)
            if cat_profile:
                return cat_profile
        
        # Global default
        return self.get_ndf_population_priors().get("global_averages", {
            "approach_avoidance": 0.5,
            "temporal_horizon": 0.5,
            "social_calibration": 0.5,
            "uncertainty_tolerance": 0.5,
            "status_sensitivity": 0.5,
            "cognitive_engagement": 0.5,
            "arousal_seeking": 0.5,
        })
    
    # =========================================================================
    # NDF (NONCONSCIOUS DECISION FINGERPRINT) PRIORS
    # =========================================================================
    
    def get_ndf_population_priors(self) -> Dict:
        """
        Get global NDF population statistics from 1B+ review ingestion.
        
        Returns:
            Dict with {ndf_count, ndf_means, ndf_stds, ndf_distributions}
            where means/stds are per-dimension and distributions are decile buckets.
        """
        return self._ndf_population
    
    def get_ndf_archetype_profile(self, archetype: str) -> Dict[str, float]:
        """
        Get mean NDF profile for a specific archetype.
        
        These are the population-level NDF means conditioned on archetype,
        serving as Bayesian priors when individual NDF is sparse.
        
        Args:
            archetype: Archetype name (e.g., "achiever", "connector")
        
        Returns:
            Dict of {dimension: mean_value} for the 8 NDF dimensions,
            or empty dict if archetype not found.
        """
        if not self._ndf_archetype_profiles:
            return {}
        return self._ndf_archetype_profiles.get(
            archetype, 
            self._ndf_archetype_profiles.get(archetype.lower(), {})
        )
    
    def get_ndf_all_archetype_profiles(self) -> Dict[str, Dict[str, float]]:
        """
        Get NDF profiles for all archetypes.
        
        Returns:
            Dict of {archetype: {dimension: mean_value}}
        """
        return self._ndf_archetype_profiles
    
    def get_ndf_category_profile(self, category: str) -> Dict:
        """
        Get NDF population statistics for a specific product category.
        
        Args:
            category: Category name (e.g., "Electronics", "Beauty")
        
        Returns:
            Dict with {ndf_means, ndf_stds, ndf_count} for that category.
        """
        if not self._ndf_category_profiles:
            return {}
        return self._ndf_category_profiles.get(
            category,
            self._ndf_category_profiles.get(category.lower(), {})
        )
    
    # =========================================================================
    # GOOGLE HYPERLOCAL (state / vertical / category / price NDF)
    # =========================================================================
    
    def get_ndf_for_state(self, state: str) -> Dict[str, float]:
        """
        Get NDF population profile for a US state (from Google Local ingestion).
        
        Use when request/campaign has geographic context (e.g. state targeting).
        Returns 7 NDF dimensions (ndf_means or direct dim keys) for that state.
        """
        if not self._google_hyperlocal:
            return {}
        state_profs = self._google_hyperlocal.get("state_ndf_profiles", {})
        prof = state_profs.get(state) or state_profs.get(state.replace(" ", "_"))
        if not prof:
            return {}
        return prof.get("ndf_means", prof) if isinstance(prof.get("ndf_means"), dict) else prof
    
    def get_ndf_for_vertical(self, vertical: str) -> Dict[str, float]:
        """
        Get NDF population profile for an ad vertical (dining, retail, professional, etc.).
        
        Use when campaign vertical is known. Returns 7 NDF dimensions for that vertical.
        """
        if not self._google_hyperlocal:
            return {}
        vert_profs = self._google_hyperlocal.get("vertical_ndf_profiles", {})
        prof = vert_profs.get(vertical) or vert_profs.get(vertical.lower())
        if not prof:
            return {}
        return prof.get("ndf_means", prof) if isinstance(prof.get("ndf_means"), dict) else prof
    
    def get_ndf_for_google_category(self, category: str) -> Dict[str, float]:
        """
        Get NDF profile for a Google Local category (Restaurant, Doctor, Hotel, etc.).
        
        Use for local-business-style targeting. Returns 7 NDF dimensions.
        """
        if not self._google_hyperlocal:
            return {}
        cat_profs = self._google_hyperlocal.get("category_ndf_profiles", {})
        prof = cat_profs.get(category) or cat_profs.get(category.lower())
        if not prof:
            return {}
        return prof.get("ndf_means", prof) if isinstance(prof.get("ndf_means"), dict) else prof
    
    def get_ndf_for_price_tier(self, tier: str) -> Dict[str, float]:
        """
        Get NDF profile for price tier ($, $$, $$$, $$$$) from Google Local.
        """
        if not self._google_hyperlocal:
            return {}
        tier_profs = self._google_hyperlocal.get("price_tier_ndf_profiles", {})
        prof = tier_profs.get(tier)
        if not prof:
            return {}
        return prof.get("ndf_means", prof) if isinstance(prof.get("ndf_means"), dict) else prof
    
    def get_google_location_profiles(self) -> Dict[str, Dict]:
        """
        Get per-state location profiles (review_count, top_construct, top_archetype).
        
        Use for hyperlocal targeting and regional insights.
        """
        if not self._google_hyperlocal:
            return {}
        return self._google_hyperlocal.get("location_profiles", {})
    
    def compute_ndf_bayesian_posterior(
        self,
        observed_ndf: Dict[str, float],
        archetype: str = "",
        category: str = "",
    ) -> Dict[str, float]:
        """
        Compute Bayesian posterior NDF by combining population prior with observation.
        
        Uses the Bayesian integration model from NDF_ACADEMIC_GROUNDING.md:
        
        posterior_mean = (prior_precision * prior_mean + obs_precision * obs_mean) 
                       / (prior_precision + obs_precision)
        
        Where:
        - prior = archetype-conditioned NDF population means
        - observation = real-time NDF extracted from user text
        - precision = 1/variance (higher precision = more weight)
        
        The prior precision is based on archetype sample size (more data = more weight).
        The observation precision is based on text length / quality.
        
        Args:
            observed_ndf: NDF extracted from user's text
            archetype: User's archetype (for conditioned prior)
            category: Product category (for category-conditioned prior)
        
        Returns:
            Dict of {dimension: posterior_mean} for all 8 NDF dimensions.
        """
        NDF_DIMS = [
            "approach_avoidance", "temporal_horizon", "social_calibration",
            "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
            "arousal_seeking", "cognitive_velocity",
        ]
        
        # Get prior: prefer archetype-conditioned, fall back to category, then global
        prior_means = {}
        prior_stds = {}
        prior_n = 1  # minimum sample count
        
        if archetype:
            arch_profile = self.get_ndf_archetype_profile(archetype)
            if arch_profile:
                prior_means = {d: arch_profile.get(d, 0.0) for d in NDF_DIMS}
                prior_n = arch_profile.get("count", 100)
        
        if not prior_means and category:
            cat_profile = self.get_ndf_category_profile(category)
            if cat_profile:
                prior_means = cat_profile.get("ndf_means", {})
                prior_stds = cat_profile.get("ndf_stds", {})
                prior_n = cat_profile.get("ndf_count", 50)
        
        if not prior_means and self._ndf_population:
            prior_means = self._ndf_population.get("ndf_means", {})
            prior_stds = self._ndf_population.get("ndf_stds", {})
            prior_n = self._ndf_population.get("ndf_count", 1000)
        
        if not prior_means:
            # No priors available - return observation as-is
            return observed_ndf
        
        # Compute posterior for each dimension
        posterior = {}
        for dim in NDF_DIMS:
            obs_val = observed_ndf.get(dim, 0.0)
            prior_val = prior_means.get(dim, 0.0)
            prior_std = prior_stds.get(dim, 0.25) if prior_stds else 0.25
            
            # Precision = 1 / variance
            # Prior precision scales with sample size (sqrt for diminishing returns)
            prior_var = max(0.001, prior_std ** 2)
            prior_precision = min(50.0, prior_n ** 0.5 / prior_var)
            
            # Observation precision: single observation, moderate certainty
            obs_precision = 4.0  # ~0.25 std equivalent
            
            # Bayesian posterior mean
            total_precision = prior_precision + obs_precision
            posterior_mean = (
                prior_precision * prior_val + obs_precision * obs_val
            ) / total_precision
            
            posterior[dim] = round(posterior_mean, 4)
        
        return posterior
    
    # =========================================================================
    # THOMPSON SAMPLING WARM-START
    # =========================================================================
    
    def get_thompson_warm_start_for_archetype(
        self,
        archetype: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Get Thompson Sampling warm-start parameters for an archetype.
        
        Args:
            archetype: User archetype (e.g., "Connector", "Achiever")
        
        Returns:
            Dict mapping mechanism → {alpha, beta, prior_mean, prior_variance}
        """
        return self._thompson_warm_start.get(archetype, {})
    
    def get_beta_parameters_for_mechanism(
        self,
        archetype: str,
        mechanism: str
    ) -> Tuple[float, float]:
        """
        Get Beta distribution parameters for a specific archetype-mechanism pair.
        
        Args:
            archetype: User archetype
            mechanism: Persuasion mechanism
        
        Returns:
            (alpha, beta) tuple for Beta distribution
        """
        archetype_data = self._thompson_warm_start.get(archetype, {})
        mech_data = archetype_data.get(mechanism, {})
        
        # Default to uninformative prior if not found
        alpha = mech_data.get("alpha", 1.0)
        beta = mech_data.get("beta", 1.0)
        
        return alpha, beta
    
    def sample_mechanism_effectiveness(
        self,
        archetype: str,
        mechanism: str
    ) -> float:
        """
        Sample expected effectiveness from learned posterior.
        
        Uses Thompson Sampling with warm-started priors.
        
        Args:
            archetype: User archetype
            mechanism: Persuasion mechanism
        
        Returns:
            Sampled effectiveness value (0-1)
        """
        alpha, beta = self.get_beta_parameters_for_mechanism(archetype, mechanism)
        return np.random.beta(alpha, beta)
    
    def get_best_mechanisms_for_archetype(
        self,
        archetype: str,
        top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Get the best mechanisms for an archetype based on learned effectiveness.
        
        Args:
            archetype: User archetype
            top_n: Number of top mechanisms to return
        
        Returns:
            List of (mechanism, effectiveness) tuples, sorted by effectiveness
        """
        archetype_data = self._archetype_mechanism_matrix.get(archetype, {})
        
        if not archetype_data:
            # Return default ordering
            return [
                ("liking", 0.4),
                ("commitment", 0.33),
                ("authority", 0.30),
            ][:top_n]
        
        # Sort by effectiveness
        sorted_mechs = sorted(
            [
                (mech, data.get("avg_effectiveness", 0))
                for mech, data in archetype_data.items()
            ],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_mechs[:top_n]
    
    # =========================================================================
    # COLD START TRANSFER PRIORS
    # =========================================================================
    
    def get_category_archetype_prior(
        self,
        category: str
    ) -> Dict[str, float]:
        """
        Get archetype probability distribution for a category.
        
        Args:
            category: Product/content category (e.g., "Electronics_Photography")
        
        Returns:
            Dict mapping archetype → probability
        """
        # Direct match
        if category in self._category_priors:
            return self._category_priors[category]
        
        # Try case-insensitive match
        for cat, priors in self._category_priors.items():
            if cat.lower() == category.lower():
                return priors
        
        # Try partial match
        for cat, priors in self._category_priors.items():
            if category.lower() in cat.lower() or cat.lower() in category.lower():
                return priors
        
        # Return uniform prior
        return self._get_global_archetype_prior()
    
    def get_cluster_archetype_prior(
        self,
        cluster: str
    ) -> Dict[str, float]:
        """
        Get archetype probability distribution for a category cluster.
        
        Args:
            cluster: Category cluster (e.g., "technology", "media", "lifestyle")
        
        Returns:
            Dict mapping archetype → probability
        """
        return self._cluster_priors.get(cluster, self._get_global_archetype_prior())
    
    def get_archetype_prior_for_context(
        self,
        category: Optional[str] = None,
        cluster: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Get best available archetype prior based on context.
        
        Priority:
        1. Direct category match
        2. Cluster match
        3. Inferred cluster from category
        4. Global prior
        
        Args:
            category: Product/content category
            cluster: Category cluster
        
        Returns:
            Dict mapping archetype → probability
        """
        # Try category first
        if category:
            cat_prior = self.get_category_archetype_prior(category)
            if cat_prior != self._get_global_archetype_prior():
                return cat_prior
        
        # Try explicit cluster
        if cluster:
            cluster_prior = self.get_cluster_archetype_prior(cluster)
            if cluster_prior != self._get_global_archetype_prior():
                return cluster_prior
        
        # Try inferring cluster from category
        if category:
            for cluster_name, categories in self._cluster_definitions.items():
                for cat in categories:
                    if category.lower() in cat.lower() or cat.lower() in category.lower():
                        return self.get_cluster_archetype_prior(cluster_name)
        
        return self._get_global_archetype_prior()
    
    def _get_global_archetype_prior(self) -> Dict[str, float]:
        """Get global archetype prior (aggregated from all categories)."""
        
        # Aggregate from category priors if available
        if self._category_priors:
            aggregated = {}
            total_weight = 0
            
            for cat_priors in self._category_priors.values():
                for arch, prob in cat_priors.items():
                    aggregated[arch] = aggregated.get(arch, 0) + prob
                total_weight += 1
            
            if total_weight > 0:
                return {
                    arch: prob / total_weight
                    for arch, prob in aggregated.items()
                }
        
        # Fallback to uniform with Connector bias (empirically observed)
        return {
            "Connector": 0.40,
            "Achiever": 0.20,
            "Explorer": 0.15,
            "Guardian": 0.12,
            "Pragmatist": 0.08,
            "Analyzer": 0.05,
        }
    
    def predict_archetype(
        self,
        category: Optional[str] = None,
        behavioral_signals: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, float]:
        """
        Predict most likely archetype based on available context.
        
        Args:
            category: Product/content category
            behavioral_signals: Any available behavioral signals
        
        Returns:
            (archetype, confidence) tuple
        """
        prior = self.get_archetype_prior_for_context(category=category)
        
        # Simple argmax for now (could incorporate behavioral signals)
        best_archetype = max(prior.items(), key=lambda x: x[1])
        
        return best_archetype[0], best_archetype[1]
    
    # =========================================================================
    # MECHANISM EFFECTIVENESS
    # =========================================================================
    
    def get_mechanism_effectiveness(
        self,
        archetype: str,
        mechanism: str
    ) -> Tuple[float, float]:
        """
        Get mechanism effectiveness for an archetype.
        
        Args:
            archetype: User archetype
            mechanism: Persuasion mechanism
        
        Returns:
            (effectiveness, std_dev) tuple
        """
        archetype_data = self._archetype_mechanism_matrix.get(archetype, {})
        mech_data = archetype_data.get(mechanism, {})
        
        effectiveness = mech_data.get("avg_effectiveness", 0.3)
        std_dev = mech_data.get("std_dev", 0.02)
        
        return effectiveness, std_dev
    
    def rank_mechanisms_for_archetype(
        self,
        archetype: str
    ) -> List[Dict[str, Any]]:
        """
        Rank all mechanisms for an archetype by effectiveness.
        
        Args:
            archetype: User archetype
        
        Returns:
            List of mechanism dicts with effectiveness data, sorted descending
        """
        archetype_data = self._archetype_mechanism_matrix.get(archetype, {})
        
        if not archetype_data:
            return []
        
        ranked = []
        for mech, data in archetype_data.items():
            ranked.append({
                "mechanism": mech,
                "effectiveness": data.get("avg_effectiveness", 0),
                "observations": data.get("observations", 0),
                "std_dev": data.get("std_dev", 0.02),
                "confidence": 1.0 - data.get("std_dev", 0.02) * 10,  # Higher std = lower confidence
            })
        
        return sorted(ranked, key=lambda x: x["effectiveness"], reverse=True)
    
    # =========================================================================
    # BRAND PRIORS (from 941M+ reviews - 23M+ brands)
    # =========================================================================
    
    def get_brand_archetype_prior(self, brand: str) -> Dict[str, float]:
        """
        Get archetype probability distribution for a brand.
        
        Learned from 941M+ reviews across 23M+ brands including:
        - Automotive: Ford, Toyota, BMW, Tesla, etc.
        - Gaming: PUBG, GTA V, Witcher 3, etc.
        - Beauty: Tatcha, Drunk Elephant, The Ordinary, etc.
        
        Args:
            brand: Brand name (case-insensitive)
        
        Returns:
            Dict mapping archetype → probability
        """
        # Direct match
        if brand in self._brand_archetype_priors:
            return self._brand_archetype_priors[brand]
        
        # Case-insensitive match
        brand_lower = brand.lower()
        for b, priors in self._brand_archetype_priors.items():
            if b.lower() == brand_lower:
                return priors
        
        # Partial match (contains)
        for b, priors in self._brand_archetype_priors.items():
            if brand_lower in b.lower() or b.lower() in brand_lower:
                return priors
        
        # Return global prior
        return self._get_global_archetype_prior()
    
    # =========================================================================
    # HIERARCHICAL RELAXED SEARCH (ensures we always find intelligence)
    # =========================================================================
    
    def get_hierarchical_priors(
        self,
        brand: str,
        product_name: str,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get priors using hierarchical relaxed search strategy.
        
        CRITICAL: This ensures we ALWAYS find relevant psychological intelligence
        even when exact matches don't exist. The search progressively relaxes
        while maintaining key identifiers.
        
        SEARCH HIERARCHY (from most specific to most general):
        0. amazon_{category}_{brand} {product_name} (EXACT CORPUS MATCH)
        1. amazon_{category}_{brand} (Category + Brand)
        2. Brand + Full Product Name 
        3. Brand + Type + Attribute ("Nike Men's Sneakers")  
        4. Brand + Type Only ("Nike Sneakers")
        5. Brand Only ("Nike")
        6. Category Fallback
        7. Global Priors (always available)
        
        Args:
            brand: Product brand (e.g., "Nike", "Adidas") - ALWAYS maintained
            product_name: Full product name (e.g., "Gazelle", "Alpha 3 Men's Sneakers")
            category: Product category (e.g., "Clothing_Shoes_and_Jewelry") - CRITICAL for precise lookup
            subcategory: Optional subcategory for more precise matching
            
        Returns:
            Dict with:
            - archetype_priors: Dict[str, float]
            - match_level: int (0-7, lower = more specific)
            - match_description: str
            - search_terms_used: List[str]
            - confidence_boost: float (higher for more specific matches)
        """
        import re
        import logging
        logger = logging.getLogger(__name__)
        
        brand_clean = brand.strip()
        product_clean = product_name.strip()
        
        # ===== LEVEL 0: EXACT CORPUS MATCH (amazon_{category}_{brand} {product}) =====
        # This is the MOST PRECISE lookup - matches exactly how data is stored
        if category:
            # Try exact match: amazon_Clothing_Shoes_and_Jewelry_adidas Gazelle
            exact_key = f"amazon_{category}_{brand_clean} {product_clean}"
            if exact_key in self._brand_archetype_priors:
                logger.info(f"EXACT CORPUS MATCH found: {exact_key}")
                return {
                    "archetype_priors": self._brand_archetype_priors[exact_key],
                    "match_level": 0,
                    "match_description": f"EXACT: amazon_{category}_{brand_clean} {product_clean}",
                    "search_terms_used": [category, brand_clean, product_clean],
                    "confidence_boost": 1.0,
                }
            
            # Try case variations
            for key, priors in self._brand_archetype_priors.items():
                if key.lower() == exact_key.lower():
                    logger.info(f"EXACT CORPUS MATCH (case-insensitive) found: {key}")
                    return {
                        "archetype_priors": priors,
                        "match_level": 0,
                        "match_description": f"EXACT: {key}",
                        "search_terms_used": [category, brand_clean, product_clean],
                        "confidence_boost": 1.0,
                    }
            
            # Try partial product name match within category+brand
            prefix = f"amazon_{category}_{brand_clean}"
            for key, priors in self._brand_archetype_priors.items():
                if key.lower().startswith(prefix.lower()):
                    # Check if product name is contained
                    if product_clean.lower() in key.lower():
                        logger.info(f"CORPUS MATCH (partial product) found: {key}")
                        return {
                            "archetype_priors": priors,
                            "match_level": 0,
                            "match_description": f"CORPUS: {key}",
                            "search_terms_used": [category, brand_clean, product_clean],
                            "confidence_boost": 0.95,
                        }
        
        # ===== LEVEL 1: Category + Brand (amazon_{category}_{brand}) =====
        if category:
            # Search for any product by this brand in this category
            category_brand_prefix = f"amazon_{category}_{brand_clean}"
            matching_keys = [k for k in self._brand_archetype_priors.keys() 
                           if k.lower().startswith(category_brand_prefix.lower())]
            
            if matching_keys:
                # Aggregate priors from all matching products
                aggregated = self._aggregate_priors(matching_keys)
                logger.info(f"CATEGORY+BRAND match: {len(matching_keys)} products for {brand_clean} in {category}")
                return {
                    "archetype_priors": aggregated,
                    "match_level": 1,
                    "match_description": f"Category+Brand: {len(matching_keys)} {brand_clean} products in {category}",
                    "search_terms_used": [category, brand_clean],
                    "confidence_boost": 0.9,
                    "products_matched": len(matching_keys),
                }
        
        # Extract search terms from product name for fallback levels
        product_lower = product_name.lower()
        
        # Common product type keywords to preserve
        TYPE_KEYWORDS = {
            'sneakers', 'shoes', 'boots', 'sandals', 'heels', 'loafers', 'flats',
            'shirt', 'pants', 'dress', 'jacket', 'coat', 'sweater', 'hoodie',
            'phone', 'laptop', 'tablet', 'computer', 'headphones', 'earbuds',
            'camera', 'tv', 'television', 'monitor', 'speaker',
            'bag', 'purse', 'wallet', 'backpack', 'luggage',
            'watch', 'jewelry', 'ring', 'necklace', 'bracelet',
            'perfume', 'cologne', 'makeup', 'skincare', 'lipstick',
            'vitamin', 'supplement', 'protein', 'health',
            'toy', 'game', 'puzzle', 'doll', 'figure',
            'tool', 'drill', 'saw', 'hammer', 'wrench',
            'gazelle',  # Product-specific terms
        }
        
        # Attribute keywords (gender, size descriptors)
        ATTRIBUTE_KEYWORDS = {
            "men's", "mens", "women's", "womens", "unisex", "kids", "children's",
            "adult", "junior", "senior", "youth", "toddler", "baby", "infant",
            "small", "medium", "large", "xl", "xxl", "plus", "petite", "tall",
            "wireless", "bluetooth", "smart", "electric", "portable", "mini",
            "pro", "max", "ultra", "premium", "deluxe", "professional",
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', product_lower)
        
        # Identify type keywords in product name
        found_types = [w for w in words if w in TYPE_KEYWORDS]
        found_attributes = [w for w in words if w in ATTRIBUTE_KEYWORDS]
        
        # Also check for partial type matches
        for type_kw in TYPE_KEYWORDS:
            if type_kw in product_lower and type_kw not in found_types:
                found_types.append(type_kw)
        
        brand_lower = brand.lower().strip()
        
        # ===== LEVEL 2: Brand + Full Product Name (any category) =====
        # Search across all categories for brand + product
        brand_product_pattern = f"{brand_lower} {product_lower}".lower()
        for key, priors in self._brand_archetype_priors.items():
            key_lower = key.lower()
            if brand_lower in key_lower and product_lower in key_lower:
                logger.info(f"BRAND+PRODUCT match found: {key}")
                return {
                    "archetype_priors": priors,
                    "match_level": 2,
                    "match_description": f"Brand+Product: {key}",
                    "search_terms_used": [brand, product_name],
                    "confidence_boost": 0.85,
                }
        
        # ===== LEVEL 3: Brand + Type + Attribute =====
        if found_types and found_attributes:
            for attr in found_attributes:
                for ptype in found_types:
                    search_key = f"{brand_lower}_{attr}_{ptype}"
                    search_variations = [
                        search_key,
                        f"{brand_lower} {attr} {ptype}",
                        f"{brand_lower}_{ptype}_{attr}",
                    ]
                    for key in search_variations:
                        priors = self._search_brand_priors(key)
                        if priors:
                            return {
                                "archetype_priors": priors,
                                "match_level": 3,
                                "match_description": f"Brand + {attr.title()} + {ptype.title()}",
                                "search_terms_used": [brand, attr, ptype],
                                "confidence_boost": 0.8,
                            }
        
        # ===== LEVEL 4: Brand + Type Only =====
        if found_types:
            for ptype in found_types:
                search_key = f"{brand_lower}_{ptype}"
                priors = self._search_brand_priors(search_key)
                if priors:
                    return {
                        "archetype_priors": priors,
                        "match_level": 4,
                        "match_description": f"Brand + {ptype.title()}",
                        "search_terms_used": [brand, ptype],
                        "confidence_boost": 0.75,
                    }
        
        # ===== LEVEL 5: Brand Only (search all categories) =====
        # Find all products by this brand across all categories
        brand_keys = [k for k in self._brand_archetype_priors.keys() 
                      if brand_lower in k.lower()]
        if brand_keys:
            aggregated = self._aggregate_priors(brand_keys)
            return {
                "archetype_priors": aggregated,
                "match_level": 5,
                "match_description": f"Brand Only: {len(brand_keys)} {brand} products across all categories",
                "search_terms_used": [brand],
                "confidence_boost": 0.6,
                "products_matched": len(brand_keys),
            }
        
        # ===== LEVEL 6: Category/Type Fallback =====
        # Map product types to categories
        TYPE_TO_CATEGORY = {
            'sneakers': 'Clothing_Shoes_and_Jewelry',
            'shoes': 'Clothing_Shoes_and_Jewelry',
            'boots': 'Clothing_Shoes_and_Jewelry',
            'sandals': 'Clothing_Shoes_and_Jewelry',
            'shirt': 'Clothing_Shoes_and_Jewelry',
            'pants': 'Clothing_Shoes_and_Jewelry',
            'dress': 'Clothing_Shoes_and_Jewelry',
            'phone': 'Electronics',
            'laptop': 'Electronics',
            'tablet': 'Electronics',
            'computer': 'Electronics',
            'headphones': 'Electronics',
            'camera': 'Electronics',
            'tv': 'Electronics',
            'perfume': 'Beauty_and_Personal_Care',
            'makeup': 'Beauty_and_Personal_Care',
            'skincare': 'Beauty_and_Personal_Care',
            'vitamin': 'Health_and_Household',
            'supplement': 'Health_and_Household',
            'toy': 'Toys_and_Games',
            'game': 'Toys_and_Games',
            'tool': 'Tools_and_Home_Improvement',
        }
        
        # Try category from provided hint or inferred from type
        search_category = category
        if not search_category and found_types:
            for ptype in found_types:
                if ptype in TYPE_TO_CATEGORY:
                    search_category = TYPE_TO_CATEGORY[ptype]
                    break
        
        if search_category:
            category_priors = self.get_category_archetype_prior(search_category)
            if category_priors != self._get_global_archetype_prior():
                return {
                    "archetype_priors": category_priors,
                    "match_level": 6,
                    "match_description": f"Category: {search_category}",
                    "search_terms_used": [search_category] + found_types,
                    "confidence_boost": 0.4,
                }
        
        # ===== LEVEL 7: Global Priors (always available) =====
        return {
            "archetype_priors": self._get_global_archetype_prior(),
            "match_level": 7,
            "match_description": "Global Priors (941M+ reviews)",
            "search_terms_used": ["global"],
            "confidence_boost": 0.3,
        }
    
    def _search_brand_priors(self, search_key: str) -> Optional[Dict[str, float]]:
        """Helper to search brand priors with fuzzy matching."""
        search_lower = search_key.lower()
        
        # Direct match
        if search_key in self._brand_archetype_priors:
            return self._brand_archetype_priors[search_key]
        
        # Case-insensitive match
        for key, priors in self._brand_archetype_priors.items():
            if key.lower() == search_lower:
                return priors
        
        # Contains match (be more strict - require both terms)
        search_parts = search_lower.split('_')
        for key, priors in self._brand_archetype_priors.items():
            key_lower = key.lower()
            # All search parts must be in key
            if all(part in key_lower for part in search_parts if len(part) > 2):
                return priors
        
        return None
    
    def _aggregate_priors(self, keys: List[str]) -> Dict[str, float]:
        """Aggregate priors from multiple matching keys."""
        if not keys:
            return self._get_global_archetype_prior()
        
        aggregated = {}
        count = 0
        
        for key in keys:
            priors = self._brand_archetype_priors.get(key, {})
            for arch, prob in priors.items():
                aggregated[arch] = aggregated.get(arch, 0) + prob
            count += 1
        
        if count > 0:
            # Average the probabilities and normalize to sum to 1.0
            total = sum(aggregated.values())
            if total > 0:
                return {arch: prob / total for arch, prob in aggregated.items()}
            return {arch: prob / count for arch, prob in aggregated.items()}
        
        return self._get_global_archetype_prior()
    
    # =========================================================================
    # MULTI-LEVEL WEIGHTED AGGREGATION (STATISTICAL POWER MAXIMIZER)
    # =========================================================================
    
    def _get_similar_products_from_claude(
        self,
        brand: str,
        product_name: str,
        category: str,
        num_products: int = 25,
    ) -> List[str]:
        """
        Ask Claude for similar products from the same brand.
        
        Example: For "Adidas GAZELLE INDOOR SHOES", Claude might return:
        ["Samba", "Campus", "Stan Smith", "Superstar", "Forum", ...]
        """
        import os
        
        try:
            import anthropic
            
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("No ANTHROPIC_API_KEY - skipping Claude similar products lookup")
                return []
            
            client = anthropic.Anthropic(api_key=api_key)
            
            prompt = f"""Given the brand "{brand}" and the product "{product_name}" in the category "{category}", 
provide a list of {num_products}-{num_products + 5} other {brand} products that are most similar to {product_name}.

IMPORTANT: 
- Return ONLY the distinctive product/model name, NOT the brand name
- Include as many similar products as you can think of
- Focus on products that attract SIMILAR CUSTOMER TYPES (same style, use case, market segment)

Good examples: ["Samba", "Stan Smith", "Superstar", "Campus", "Forum", "Continental 80", "Rivalry", "NMD", "Gazelle OG"]
Bad examples: ["Adidas Samba", "Adidas Stan Smith"]

Return as a JSON array of strings, nothing else."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            response_text = message.content[0].text.strip()
            similar_products = json.loads(response_text)
            
            if isinstance(similar_products, list):
                # Clean up: remove brand name if Claude included it anyway
                brand_lower = brand.lower()
                cleaned = []
                for prod in similar_products:
                    prod_clean = prod.strip()
                    prod_lower = prod_clean.lower()
                    if prod_lower.startswith(brand_lower):
                        prod_clean = prod_clean[len(brand):].strip()
                    for prefix in [f"{brand} ", f"{brand.upper()} ", f"{brand.lower()} "]:
                        if prod_clean.startswith(prefix):
                            prod_clean = prod_clean[len(prefix):]
                    cleaned.append(prod_clean)
                
                logger.info(f"CLAUDE PRODUCTS: {len(cleaned)} similar {brand} products: {cleaned}")
                return cleaned
            
        except Exception as e:
            logger.warning(f"Claude similar products lookup failed: {e}")
        
        return []
    
    def _get_similar_product_lines_from_claude(
        self,
        brand: str,
        product_name: str,
        category: str,
    ) -> List[str]:
        """
        Ask Claude for similar PRODUCT LINES (not individual products).
        
        Example: For "Adidas GAZELLE", Claude might return:
        ["Originals", "Lifestyle", "Heritage", "Retro"]
        
        This allows searching entire product line collections.
        """
        import os
        
        try:
            import anthropic
            
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("No ANTHROPIC_API_KEY - skipping Claude product lines lookup")
                return []
            
            client = anthropic.Anthropic(api_key=api_key)
            
            prompt = f"""For the brand "{brand}" and product "{product_name}", identify the PRODUCT LINES or COLLECTIONS that contain similar products.

I need the names of {brand}'s product LINES/COLLECTIONS (not individual products) that would attract similar customers.

For example, if the product is "Gazelle" (a lifestyle/retro sneaker), similar lines might include:
- "Originals" (the heritage/lifestyle collection)
- "Lifestyle" or "Casual" collections
- Other retro/heritage lines

Return 5-10 product LINE names as a JSON array of strings.
Return ONLY the line/collection names, not individual product names.

Example good response: ["Originals", "Lifestyle", "Heritage", "Retro", "Classic"]
Example bad response: ["Samba", "Stan Smith"] (these are products, not lines)

JSON array only, no explanation:"""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            response_text = message.content[0].text.strip()
            product_lines = json.loads(response_text)
            
            if isinstance(product_lines, list):
                logger.info(f"CLAUDE LINES: {brand} product lines similar to {product_name}: {product_lines}")
                return [line.lower() for line in product_lines]
            
        except Exception as e:
            logger.warning(f"Claude product lines lookup failed: {e}")
        
        return []
    
    def _decompose_product_terms(self, product_name: str) -> List[str]:
        """
        Intelligently decompose product name into searchable terms.
        
        Example: "GAZELLE INDOOR SHOES" → ["Gazelle", "Indoor Shoes"]
        
        Rules:
        - Skip very short words (< 3 chars)
        - Combine descriptive words (Indoor + Shoes = "Indoor Shoes")
        - Keep distinctive words separate (Gazelle)
        """
        # Common product type words that should be combined
        product_type_words = {
            "shoes", "sneakers", "boots", "sandals", "slippers",
            "shirt", "jacket", "pants", "shorts", "dress", "top",
            "bag", "backpack", "watch", "glasses", "headphones",
            "indoor", "outdoor", "running", "training", "casual", "athletic"
        }
        
        words = product_name.strip().split()
        terms = []
        
        i = 0
        while i < len(words):
            word = words[i]
            word_lower = word.lower()
            
            # Skip very short words unless they're meaningful
            if len(word) < 3 and word_lower not in {"ii", "iii", "iv", "v", "2", "3", "4"}:
                i += 1
                continue
            
            # Check if this is a modifier that should combine with next word
            if word_lower in {"indoor", "outdoor", "running", "training", "casual", "athletic", "mens", "womens", "men's", "women's"}:
                if i + 1 < len(words):
                    combined = f"{word} {words[i+1]}"
                    terms.append(combined)
                    i += 2
                    continue
            
            # Check if this word should combine with previous (for product types)
            if word_lower in product_type_words and terms:
                # Add as separate term too
                terms.append(word)
                i += 1
                continue
            
            terms.append(word)
            i += 1
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in terms:
            term_lower = term.lower()
            if term_lower not in seen:
                seen.add(term_lower)
                unique_terms.append(term)
        
        return unique_terms
    
    def get_deep_aggregated_intelligence(
        self,
        brand: str,
        product_name: str,
        category: str,
        subcategory: Optional[str] = None,
        similar_brands: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        INTELLIGENT PROGRESSIVE SEARCH for customer archetype intelligence.
        
        =======================================================================
        SEARCH STRATEGY: Progressive Widening with Intelligent Term Matching
        =======================================================================
        
        1. LEVEL 1: Perfect Match
           → Exact product name match (e.g., "Adidas GAZELLE INDOOR SHOES")
           
        2. LEVEL 2: Claude-Powered Similar Products  
           → Ask Claude: "What Adidas products are similar to GAZELLE INDOOR SHOES?"
           → Returns: ["Samba", "Campus", "Stan Smith", "Superstar"]
           → Query each of these
           
        3. LEVEL 3: Intelligent Term Decomposition
           → Break apart: "GAZELLE INDOOR SHOES" → ["Gazelle", "Indoor Shoes"]
           → Query: "Adidas Gazelle", "Adidas Indoor Shoes"
           → Context-aware splitting
           
        4. LEVEL 4: Full Brand + Category
           → All Adidas products in Clothing_Shoes_and_Jewelry
           → Only used as baseline, not primary
           
        5. LEVEL 5: Category Baseline
           → Overall category patterns for grounding
        
        WHY THIS APPROACH:
        - We widen scope INTELLIGENTLY, not blindly to the entire brand
        - "Adidas Gazelle" buyers ≈ "Adidas Samba" buyers (similar style)
        - "Adidas Gazelle" buyers ≠ "Adidas Running Ultraboost" buyers
        
        Args:
            brand: Product brand (e.g., "Adidas")
            product_name: Product name (e.g., "GAZELLE INDOOR SHOES")
            category: Category for corpus lookup
            subcategory: Optional subcategory
            similar_brands: Optional competitor brands
            
        Returns:
            Dict with intelligently aggregated customer intelligence
        """
        import logging
        logger = logging.getLogger(__name__)
        
        brand_clean = brand.strip()
        product_clean = product_name.strip()
        category_clean = category.strip()
        
        # Track contributions from each level
        level_breakdown = {}
        search_steps = []  # Track what searches were performed
        
        logger.info(f"=" * 70)
        logger.info(f"INTELLIGENT SEARCH: {brand_clean} {product_clean} in {category_clean}")
        logger.info(f"=" * 70)
        
        # Get all brand products for searching
        brand_category_prefix = f"amazon_{category_clean}_{brand_clean}"
        all_brand_keys = [
            k for k in self._brand_archetype_priors.keys()
            if k.lower().startswith(brand_category_prefix.lower())
        ]
        
        # =========================================================================
        # LEVEL 1: Perfect Match - Exact full product name string
        # =========================================================================
        logger.info(f"LEVEL 1: Searching for exact '{product_clean}' match...")
        
        exact_keys = []
        product_lower = product_clean.lower()
        for key in all_brand_keys:
            key_lower = key.lower()
            if product_lower in key_lower:
                exact_keys.append(key)
        
        exact_count = len(exact_keys)
        search_steps.append({
            "level": 1,
            "name": "perfect_match",
            "query": f"{brand_clean} + '{product_clean}' (exact string)",
            "matches": exact_count,
        })
        
        logger.info(f"  → Found {exact_count} exact matches")
        
        if exact_keys:
            level_breakdown["perfect_match"] = {
                "keys_found": exact_count,
                "priors": self._aggregate_priors(exact_keys),
                "weight": 1.0,  # Highest weight for exact matches
                "sample_keys": exact_keys[:5],
                "is_primary": True,
                "description": f"Exact '{product_clean}' matches",
            }
        
        # =========================================================================
        # LEVEL 1.5: Smart Term OR Match - Brand + (distinctive_term OR compound_term)
        # =========================================================================
        # SMART LOGIC: 
        # - "GAZELLE INDOOR SHOES" → ["Gazelle", "Indoor Shoes"] NOT ["Gazelle", "Indoor", "Shoes"]
        # - "Shoes" alone is too generic (matches everything)
        # - Keep compound descriptors together
        
        logger.info(f"LEVEL 1.5: Smart term extraction from '{product_clean}'...")
        
        # Generic product type words - these should NOT be searched alone
        generic_product_types = {
            "shoes", "shoe", "sneakers", "sneaker", "boots", "boot", "sandals", "sandal",
            "shirt", "shirts", "pants", "shorts", "jacket", "jackets", "top", "tops",
            "dress", "dresses", "socks", "sock", "hat", "hats", "cap", "caps",
            "bag", "bags", "backpack", "backpacks", "watch", "watches",
            "headphones", "earbuds", "glasses", "sunglasses",
        }
        
        # Modifiers that should combine with the next word
        modifiers = {
            "indoor", "outdoor", "running", "training", "casual", "athletic", "sport", "sports",
            "hiking", "walking", "basketball", "soccer", "football", "tennis", "golf",
            "classic", "original", "vintage", "retro", "modern", "slim", "wide",
            "low", "mid", "high", "lightweight", "waterproof",
        }
        
        # Skip words (articles, gender, etc.)
        skip_words = {
            "the", "a", "an", "and", "or", "for", "with", "in", "on", "by",
            "mens", "womens", "men's", "women's", "unisex", "kids", "adult",
            "size", "color", "pack", "set", "pair", "new",
        }
        
        # Smart term extraction
        words = product_clean.split()
        smart_terms = []
        i = 0
        
        while i < len(words):
            word = words[i].lower().strip()
            
            # Skip articles/gender/etc
            if word in skip_words or len(word) < 3:
                i += 1
                continue
            
            # Check if this is a modifier that should combine with next word
            if word in modifiers and i + 1 < len(words):
                next_word = words[i + 1].lower().strip()
                if next_word not in skip_words:
                    compound = f"{word} {next_word}"
                    smart_terms.append(compound)
                    logger.info(f"  → Compound term: '{compound}'")
                    i += 2
                    continue
            
            # Check if this is a generic product type (skip if alone)
            if word in generic_product_types:
                logger.info(f"  → Skipping generic term: '{word}' (too broad)")
                i += 1
                continue
            
            # This is a distinctive term - keep it
            smart_terms.append(word)
            logger.info(f"  → Distinctive term: '{word}'")
            i += 1
        
        logger.info(f"  → Smart terms: {smart_terms}")
        
        # Find all brand products containing ANY of these smart terms
        term_or_keys = []
        term_match_counts = {}
        
        for key in all_brand_keys:
            if key in exact_keys:
                continue  # Already counted in exact matches
            key_lower = key.lower()
            for term in smart_terms:
                if term in key_lower:
                    term_or_keys.append(key)
                    term_match_counts[term] = term_match_counts.get(term, 0) + 1
                    break  # Count each key once even if multiple terms match
        
        term_or_count = len(term_or_keys)
        search_steps.append({
            "level": 1.5,
            "name": "smart_term_or_match",
            "query": f"{brand_clean} + ({' OR '.join(smart_terms)})" if smart_terms else f"{brand_clean} (no distinctive terms found)",
            "matches": term_or_count,
            "details": [(term, count) for term, count in sorted(term_match_counts.items(), key=lambda x: -x[1])],
        })
        
        logger.info(f"  → Found {term_or_count} smart term OR matches")
        for term, count in sorted(term_match_counts.items(), key=lambda x: -x[1]):
            logger.info(f"    + '{term}': {count} matches")
        
        if term_or_keys:
            level_breakdown["term_or_match"] = {
                "keys_found": term_or_count,
                "priors": self._aggregate_priors(term_or_keys),
                "weight": 0.8,  # High weight - these are targeted term matches
                "sample_keys": term_or_keys[:5],
                "is_primary": len(exact_keys) == 0,  # Primary if no exact matches
                "description": f"{brand_clean} + ({' OR '.join(smart_terms)})",
            }
        
        # =========================================================================
        # LEVEL 2: Claude-Powered Similar Products (25+ products)
        # =========================================================================
        logger.info(f"LEVEL 2: Asking Claude for 25+ similar {brand_clean} products...")
        
        similar_product_names = self._get_similar_products_from_claude(
            brand_clean, product_clean, category_clean, num_products=25
        )
        
        similar_product_keys = []
        similar_found_products = []
        already_matched_keys = set(exact_keys + term_or_keys)  # Don't double count
        
        logger.info(f"  → Claude returned {len(similar_product_names)} products: {similar_product_names}")
        
        # Words to skip (too generic)
        skip_words = {
            brand_clean.lower(), "adidas", "nike", "puma", "reebok",
            "shoes", "shoe", "sneakers", "sneaker", "trainers", "trainer",
            "the", "a", "an", "and", "or", "for", "with",
        }
        
        for sim_product in similar_product_names:
            sim_words = sim_product.lower().split()
            
            # Try each word in the product name
            for word in sim_words:
                if word in skip_words or len(word) < 3:
                    continue
                
                word_matches = [
                    k for k in all_brand_keys 
                    if word in k.lower() and k not in already_matched_keys
                ]
                
                if word_matches:
                    similar_product_keys.extend(word_matches)
                    similar_found_products.append((sim_product, word, len(word_matches)))
                    logger.info(f"  → '{sim_product}' → '{word}': {len(word_matches)} matches")
                    break
        
        similar_product_keys = list(set(similar_product_keys))
        
        search_steps.append({
            "level": 2,
            "name": "claude_similar_products",
            "query": f"Claude suggested {len(similar_product_names)} similar products",
            "matches": len(similar_product_keys),
            "details": [(prod, f"→ '{term}'", count) for prod, term, count in similar_found_products],
        })
        
        logger.info(f"  → TOTAL from Claude: {len(similar_product_keys)} unique matches")
        
        if similar_product_keys:
            level_breakdown["similar_products"] = {
                "keys_found": len(similar_product_keys),
                "priors": self._aggregate_priors(similar_product_keys),
                "weight": 0.7,
                "sample_keys": similar_product_keys[:5],
                "is_primary": False,
                "description": f"Similar products ({len(similar_found_products)} types): {[p[0] for p in similar_found_products[:8]]}",
            }
        
        # =========================================================================
        # LEVEL 3: Intelligent Term Decomposition
        # =========================================================================
        logger.info(f"LEVEL 3: Decomposing '{product_clean}' into terms...")
        
        terms = self._decompose_product_terms(product_clean)
        logger.info(f"  → Terms: {terms}")
        
        term_keys = []
        term_matches = []
        
        for term in terms:
            term_lower = term.lower()
            # Find keys containing this term
            matches = [
                k for k in all_brand_keys 
                if term_lower in k.lower() and k not in exact_keys and k not in similar_product_keys
            ]
            if matches:
                term_keys.extend(matches)
                term_matches.append((term, len(matches)))
                logger.info(f"  → '{brand_clean} + {term}': {len(matches)} matches")
        
        # Remove duplicates
        term_keys = list(set(term_keys))
        
        search_steps.append({
            "level": 3,
            "name": "term_decomposition",
            "query": f"{brand_clean} + {terms}",
            "matches": len(term_keys),
            "details": term_matches,
        })
        
        if term_keys:
            level_breakdown["term_matches"] = {
                "keys_found": len(term_keys),
                "priors": self._aggregate_priors(term_keys),
                "weight": 0.5,  # Medium weight - term-based expansion
                "sample_keys": term_keys[:5],
                "is_primary": False,
                "description": f"Term matches: {[t[0] for t in term_matches]}",
            }
        
        # =========================================================================
        # LEVEL 4: Full Brand + Category (Baseline, not primary)
        # =========================================================================
        # Only add remaining brand products as baseline context
        
        used_keys = set(exact_keys + similar_product_keys + term_keys)
        remaining_brand_keys = [k for k in all_brand_keys if k not in used_keys]
        
        logger.info(f"LEVEL 4: {len(remaining_brand_keys)} remaining {brand_clean} products as baseline")
        
        search_steps.append({
            "level": 4,
            "name": "brand_baseline",
            "query": f"All other {brand_clean} in {category_clean}",
            "matches": len(remaining_brand_keys),
        })
        
        if remaining_brand_keys:
            level_breakdown["brand_baseline"] = {
                "keys_found": len(remaining_brand_keys),
                "priors": self._aggregate_priors(remaining_brand_keys),
                "weight": 0.2,  # Low weight - generic brand baseline
                "sample_keys": remaining_brand_keys[:5],
                "is_primary": False,
                "description": f"Other {brand_clean} products (baseline)",
            }
        
        # =========================================================================
        # LEVEL 5: Category Baseline (grounding)
        # =========================================================================
        category_priors = self.get_category_archetype_prior(category_clean)
        if category_priors and category_priors != self._get_global_archetype_prior():
            level_breakdown["category_baseline"] = {
                "keys_found": 1,
                "priors": category_priors,
                "weight": 0.1,  # Minimal weight - just for grounding
                "is_primary": False,
                "description": f"Overall {category_clean} patterns",
            }
            search_steps.append({
                "level": 5,
                "name": "category_baseline",
                "query": f"Category: {category_clean}",
                "matches": 1,
            })
        
        # =========================================================================
        # CONTEXT: Similar Brands (if provided)
        # =========================================================================
        if similar_brands:
            similar_brand_keys = []
            for sim_brand in similar_brands:
                sim_prefix = f"amazon_{category_clean}_{sim_brand}"
                sim_matches = [
                    k for k in self._brand_archetype_priors.keys()
                    if k.lower().startswith(sim_prefix.lower())
                ]
                similar_brand_keys.extend(sim_matches)
                if sim_matches:
                    logger.info(f"COMPETITOR: +{len(sim_matches)} '{sim_brand}' products")
            
            if similar_brand_keys:
                level_breakdown["competitor_context"] = {
                    "keys_found": len(similar_brand_keys),
                    "priors": self._aggregate_priors(similar_brand_keys[:500]),
                    "weight": 0.15,
                    "is_primary": False,
                    "description": f"Competitors: {similar_brands}",
                }
        
        # =========================================================================
        # WEIGHTED AGGREGATION
        # =========================================================================
        if not level_breakdown:
            logger.warning(f"No products found for {brand_clean} in {category_clean}")
            return {
                "aggregated_archetype_priors": self._get_global_archetype_prior(),
                "level_breakdown": {},
                "search_steps": search_steps,
                "primary_source": None,
                "intelligent_matches": 0,
                "total_products_analyzed": 0,
                "confidence_score": 0.2,
                "dominant_archetype": ("achiever", 0.2),
                "data_quality": "minimal",
                "intelligence_summary": f"No '{brand}' products found in '{category}'. Using global baseline.",
            }
        
        # Calculate weighted aggregate
        weighted_priors = {}
        total_weight = 0
        total_products = 0
        
        # Track "intelligent" matches (levels 1-3) vs baseline
        intelligent_matches = 0
        
        archetypes = ["achiever", "explorer", "connector", "guardian", "pragmatist", "analyst"]
        
        for level_name, level_data in level_breakdown.items():
            weight = level_data["weight"]
            priors = level_data["priors"]
            products = level_data["keys_found"]
            
            total_weight += weight
            total_products += products
            
            # Track intelligent matches (exact + term_or + similar + term-based)
            if level_name in ["perfect_match", "term_or_match", "similar_products", "term_matches"]:
                intelligent_matches += products
            
            for arch in archetypes:
                arch_val = priors.get(arch, 0)
                weighted_priors[arch] = weighted_priors.get(arch, 0) + (arch_val * weight)
        
        # Normalize weighted priors
        if total_weight > 0:
            for arch in archetypes:
                weighted_priors[arch] = weighted_priors.get(arch, 0) / total_weight
        
        # Normalize to sum to 1.0
        total_prob = sum(weighted_priors.values())
        if total_prob > 0:
            weighted_priors = {k: v / total_prob for k, v in weighted_priors.items()}
        
        # Find dominant archetype
        dominant = max(weighted_priors.items(), key=lambda x: x[1])
        
        # Calculate confidence - weighted toward intelligent matches
        intelligent_ratio = intelligent_matches / total_products if total_products > 0 else 0
        confidence = min(0.95, 0.3 + (intelligent_matches / 500) * 0.3 + (total_products / 2000) * 0.2 + intelligent_ratio * 0.15)
        
        # Determine data quality based on intelligent matches
        if intelligent_matches >= 500:
            data_quality = "excellent"
        elif intelligent_matches >= 100:
            data_quality = "good"
        elif intelligent_matches >= 20:
            data_quality = "moderate"
        elif total_products >= 100:
            data_quality = "baseline"
        else:
            data_quality = "limited"
        
        # Generate strategy from dominant archetype
        strategy = self.generate_ad_copy_strategy(
            archetype=dominant[0],
            category=category,
            brand=brand,
        )
        
        # Build intelligence summary
        exact_count = level_breakdown.get("perfect_match", {}).get("keys_found", 0)
        term_or_count = level_breakdown.get("term_or_match", {}).get("keys_found", 0)
        similar_count = level_breakdown.get("similar_products", {}).get("keys_found", 0)
        term_count = level_breakdown.get("term_matches", {}).get("keys_found", 0)
        
        summary_parts = []
        if exact_count > 0:
            summary_parts.append(f"{exact_count} exact '{product_name}' matches")
        if term_or_count > 0:
            summary_parts.append(f"{term_or_count} term-based matches")
        if similar_count > 0:
            summary_parts.append(f"{similar_count} similar product matches (Claude)")
        if term_count > 0:
            summary_parts.append(f"{term_count} decomposed term matches")
        
        if summary_parts:
            intelligence_summary = f"Intelligent search found: {', '.join(summary_parts)}. "
            intelligence_summary += f"Total: {intelligent_matches:,} targeted matches powering analysis."
        else:
            intelligence_summary = f"No targeted matches found. Using {total_products:,} {brand} products as baseline."
        
        logger.info(f"=" * 70)
        logger.info(f"RESULT: {dominant[0]} ({dominant[1]*100:.1f}%)")
        logger.info(f"Intelligent matches: {intelligent_matches:,} | Total products: {total_products:,}")
        logger.info(f"=" * 70)
        
        return {
            "aggregated_archetype_priors": weighted_priors,
            "level_breakdown": {
                name: {
                    "products_count": data["keys_found"],
                    "weight": data["weight"],
                    "is_primary": data.get("is_primary", False),
                    "description": data.get("description", ""),
                    "dominant_archetype": max(data["priors"].items(), key=lambda x: x[1]) if data["priors"] else None,
                }
                for name, data in level_breakdown.items()
            },
            "search_steps": search_steps,
            # Core metrics
            "intelligent_matches": intelligent_matches,
            "exact_product_matches": exact_count,
            "term_or_matches": term_or_count,
            "similar_product_matches": similar_count,
            "term_based_matches": term_count,
            "total_products_analyzed": total_products,
            "confidence_score": confidence,
            "dominant_archetype": dominant,
            "data_quality": data_quality,
            # Strategy
            "recommended_strategy": strategy,
            # Search info
            "search_parameters": {
                "brand": brand,
                "product": product_name,
                "category": category,
                "subcategory": subcategory,
                "similar_brands": similar_brands,
            },
            "intelligence_summary": intelligence_summary,
        }
    
    def get_archetype_for_brand(self, brand: str) -> Tuple[str, float]:
        """
        Get most likely archetype for a brand.
        
        Args:
            brand: Brand name
        
        Returns:
            (archetype, probability) tuple
        """
        priors = self.get_brand_archetype_prior(brand)
        if priors:
            best = max(priors.items(), key=lambda x: x[1])
            return best[0], best[1]
        return "Connector", 0.4  # Default
    
    # =========================================================================
    # TEMPORAL PATTERNS (best engagement hours per archetype)
    # =========================================================================
    
    def get_best_hours_for_archetype(self, archetype: str) -> List[int]:
        """
        Get best engagement hours for an archetype.
        
        Based on analysis of 941M+ reviews with timestamps.
        
        Args:
            archetype: User archetype
        
        Returns:
            List of best hours (0-23) sorted by engagement
        """
        pattern = self._temporal_patterns.get(archetype, {})
        return pattern.get("best_hours", [12, 18, 20])  # Default: noon, 6pm, 8pm
    
    def get_hourly_engagement(self, archetype: str) -> Dict[int, float]:
        """
        Get hourly engagement scores for an archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping hour (0-23) → engagement score (0-1)
        """
        pattern = self._temporal_patterns.get(archetype, {})
        hourly = pattern.get("hourly_engagement", {})
        # Convert string keys to int
        return {int(k): v for k, v in hourly.items()}
    
    def is_optimal_engagement_time(
        self,
        archetype: str,
        hour: int,
        threshold: float = 0.85
    ) -> bool:
        """
        Check if current hour is optimal for engaging this archetype.
        
        Args:
            archetype: User archetype
            hour: Hour of day (0-23)
            threshold: Minimum engagement score to consider optimal
        
        Returns:
            True if this is a good time to engage
        """
        hourly = self.get_hourly_engagement(archetype)
        engagement = hourly.get(hour, 0.7)
        return engagement >= threshold
    
    # =========================================================================
    # REVIEWER LIFECYCLE PATTERNS
    # =========================================================================
    
    def get_lifecycle_segment(self, review_count: int) -> str:
        """
        Determine lifecycle segment based on review count.
        
        Segments:
        - new_reviewer: 1-2 reviews
        - casual: 3-10 reviews
        - engaged: 11-50 reviews
        - power_user: 50+ reviews
        
        Args:
            review_count: Number of reviews by user
        
        Returns:
            Lifecycle segment name
        """
        if review_count <= 2:
            return "new_reviewer"
        elif review_count <= 10:
            return "casual"
        elif review_count <= 50:
            return "engaged"
        else:
            return "power_user"
    
    def get_lifecycle_archetype_distribution(self, segment: str) -> Dict[str, float]:
        """
        Get archetype distribution for a lifecycle segment.
        
        Args:
            segment: Lifecycle segment (new_reviewer/casual/engaged/power_user)
        
        Returns:
            Dict mapping archetype → probability
        """
        segment_data = self._reviewer_lifecycle.get(segment, {})
        return segment_data.get("archetype_distribution", self._get_global_archetype_prior())
    
    def predict_archetype_from_lifecycle(self, review_count: int) -> Tuple[str, float]:
        """
        Predict archetype based on user's review history count.
        
        Args:
            review_count: Number of reviews by user
        
        Returns:
            (archetype, confidence) tuple
        """
        segment = self.get_lifecycle_segment(review_count)
        distribution = self.get_lifecycle_archetype_distribution(segment)
        best = max(distribution.items(), key=lambda x: x[1])
        return best[0], best[1]
    
    # =========================================================================
    # BRAND LOYALTY SEGMENTS
    # =========================================================================
    
    def get_loyalty_segment(self, brand_count: int) -> str:
        """
        Determine brand loyalty segment.
        
        Segments:
        - brand_loyalist: 1 brand only
        - selective: 2-3 brands
        - explorer: 4+ brands
        
        Args:
            brand_count: Number of distinct brands purchased
        
        Returns:
            Loyalty segment name
        """
        if brand_count == 1:
            return "brand_loyalist"
        elif brand_count <= 3:
            return "selective"
        else:
            return "explorer"
    
    def get_loyalty_archetype_distribution(self, segment: str) -> Dict[str, float]:
        """
        Get archetype distribution for a loyalty segment.
        
        Args:
            segment: Loyalty segment (brand_loyalist/selective/explorer)
        
        Returns:
            Dict mapping archetype → probability
        """
        segment_data = self._brand_loyalty_segments.get(segment, {})
        return segment_data.get("archetype_distribution", self._get_global_archetype_prior())
    
    # =========================================================================
    # PRICE TIER PREFERENCES
    # =========================================================================
    
    def get_price_tier_preference(self, archetype: str) -> Dict[str, float]:
        """
        Get price tier preference distribution for an archetype.
        
        Tiers: budget (<$25), mid_range ($25-100), premium ($100-500), luxury ($500+)
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping tier → preference probability
        """
        return self._price_tier_preferences.get(archetype, {
            "budget": 0.25,
            "mid_range": 0.50,
            "premium": 0.20,
            "luxury": 0.05,
        })
    
    def get_preferred_price_tier(self, archetype: str) -> str:
        """
        Get most preferred price tier for an archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            Price tier name
        """
        prefs = self.get_price_tier_preference(archetype)
        if prefs:
            return max(prefs.items(), key=lambda x: x[1])[0]
        return "mid_range"
    
    # =========================================================================
    # LOCATION-AWARE PRIORS (from Google Reviews)
    # =========================================================================
    
    def get_state_archetype_prior(self, state: str) -> Dict[str, float]:
        """
        Get archetype probability distribution for a US state.
        
        Learned from Google Reviews across 51 states + DC.
        
        Args:
            state: State name (e.g., "California", "Texas", "New_York")
        
        Returns:
            Dict mapping archetype → probability
        """
        # Direct match
        if state in self._state_archetype_priors:
            return self._state_archetype_priors[state]
        
        # Try with/without underscores
        state_normalized = state.replace(" ", "_")
        if state_normalized in self._state_archetype_priors:
            return self._state_archetype_priors[state_normalized]
        
        state_normalized = state.replace("_", " ")
        for s, priors in self._state_archetype_priors.items():
            if s.replace("_", " ").lower() == state_normalized.lower():
                return priors
        
        # Return global prior
        return self._get_global_archetype_prior()
    
    def get_archetype_for_state(self, state: str) -> Tuple[str, float]:
        """
        Get most likely archetype for a state.
        
        Args:
            state: State name
        
        Returns:
            (archetype, probability) tuple
        """
        priors = self.get_state_archetype_prior(state)
        if priors:
            best = max(priors.items(), key=lambda x: x[1])
            return best[0], best[1]
        return "Connector", 0.4
    
    def get_region_archetype_prior(self, region: str) -> Dict[str, float]:
        """
        Get archetype probability distribution for a US region.
        
        Regions: Northeast, Southeast, Midwest, Southwest, West
        
        Args:
            region: Region name
        
        Returns:
            Dict mapping archetype → probability
        """
        return self._region_archetype_priors.get(region, self._get_global_archetype_prior())
    
    def get_density_archetype_prior(self, density: str) -> Dict[str, float]:
        """
        Get archetype probability distribution by geographic density.
        
        Density types: urban, suburban, rural
        
        Args:
            density: Density classification
        
        Returns:
            Dict mapping archetype → probability
        """
        return self._density_archetype_priors.get(density, self._get_global_archetype_prior())
    
    def get_business_response_impact(self, has_response: bool) -> Dict[str, float]:
        """
        Get archetype distribution based on business response presence.
        
        Args:
            has_response: Whether the business responded to the review
        
        Returns:
            Dict mapping archetype → probability
        """
        key = "has_response" if has_response else "no_response"
        return self._business_response_archetypes.get(key, self._get_global_archetype_prior())
    
    def get_avg_response_time_for_archetype(self, archetype: str) -> Optional[float]:
        """
        Get average business response time for reviews from an archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            Average response time in hours, or None if not available
        """
        response_data = self._response_time_by_archetype.get(archetype, {})
        return response_data.get("avg_response_hours")
    
    def get_state_category_preferences(self, state: str) -> Dict[str, float]:
        """
        Get top local service category preferences for a state.
        
        Args:
            state: State name
        
        Returns:
            Dict mapping local category → preference score
        """
        return self._state_category_preferences.get(state, {})
    
    def get_top_categories_for_state(self, state: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Get top N local service categories for a state.
        
        Args:
            state: State name
            top_n: Number of categories to return
        
        Returns:
            List of (category, preference) tuples
        """
        prefs = self.get_state_category_preferences(state)
        if not prefs:
            return []
        return sorted(prefs.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    def get_photo_upload_by_archetype(self) -> Dict[str, float]:
        """
        Get photo upload distribution by archetype.
        
        Shows which archetypes are most likely to upload photos with reviews.
        
        Returns:
            Dict mapping archetype → photo upload proportion
        """
        return self._photo_upload_by_archetype
    
    def get_multi_state_pattern(self, num_states: int) -> Dict[str, float]:
        """
        Get archetype distribution based on reviewer's geographic spread.
        
        Args:
            num_states: Number of states the reviewer has reviewed in
        
        Returns:
            Dict mapping archetype → probability
        """
        if num_states == 1:
            segment = "single_state"
        elif num_states <= 3:
            segment = "multi_state"
        else:
            segment = "traveler"
        
        segment_data = self._multi_state_patterns.get(segment, {})
        return segment_data.get("archetype_distribution", self._get_global_archetype_prior())
    
    def predict_archetype_with_location(
        self,
        state: Optional[str] = None,
        region: Optional[str] = None,
        density: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        has_business_response: Optional[bool] = None,
        num_states_reviewed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Location-aware archetype prediction using geographic signals.
        
        Combines:
        - State prior (25% weight)
        - Region prior (15% weight)  
        - Density prior (15% weight)
        - Category prior (20% weight)
        - Brand prior (15% weight)
        - Business response (5% weight)
        - Multi-state pattern (5% weight)
        
        Args:
            state: US state name
            region: US region (Northeast, Southeast, etc.)
            density: Geographic density (urban, suburban, rural)
            category: Local service category
            brand: Brand name
            has_business_response: Whether business responded
            num_states_reviewed: Reviewer's geographic spread
        
        Returns:
            Dict with predicted archetype, confidence, and breakdown
        """
        weighted_priors = {}
        weights_used = {}
        
        # 1. State prior (25%)
        if state and self._state_archetype_priors:
            state_prior = self.get_state_archetype_prior(state)
            for arch, prob in state_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.25
            weights_used["state"] = 0.25
        
        # 2. Region prior (15%)
        if region and self._region_archetype_priors:
            region_prior = self.get_region_archetype_prior(region)
            for arch, prob in region_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.15
            weights_used["region"] = 0.15
        
        # 3. Density prior (15%)
        if density and self._density_archetype_priors:
            density_prior = self.get_density_archetype_prior(density)
            for arch, prob in density_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.15
            weights_used["density"] = 0.15
        
        # 4. Category prior (20%)
        if category:
            cat_prior = self.get_category_archetype_prior(category)
            for arch, prob in cat_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.20
            weights_used["category"] = 0.20
        
        # 5. Brand prior (15%)
        if brand:
            brand_prior = self.get_brand_archetype_prior(brand)
            for arch, prob in brand_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.15
            weights_used["brand"] = 0.15
        
        # 6. Business response (5%)
        if has_business_response is not None and self._business_response_archetypes:
            response_prior = self.get_business_response_impact(has_business_response)
            for arch, prob in response_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.05
            weights_used["business_response"] = 0.05
        
        # 7. Multi-state pattern (5%)
        if num_states_reviewed is not None and self._multi_state_patterns:
            multi_state_prior = self.get_multi_state_pattern(num_states_reviewed)
            for arch, prob in multi_state_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.05
            weights_used["multi_state"] = 0.05
        
        # Use global prior for remaining weight
        remaining_weight = 1.0 - sum(weights_used.values())
        if remaining_weight > 0:
            global_prior = self._get_global_archetype_prior()
            for arch, prob in global_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * remaining_weight
            weights_used["global"] = remaining_weight
        
        # Normalize
        total = sum(weighted_priors.values())
        if total > 0:
            weighted_priors = {k: v / total for k, v in weighted_priors.items()}
        
        # Get best archetype
        best_archetype = max(weighted_priors.items(), key=lambda x: x[1])
        
        return {
            "archetype": best_archetype[0],
            "confidence": best_archetype[1],
            "distribution": weighted_priors,
            "weights_used": weights_used,
            "location_signals": {
                "state": state,
                "region": region,
                "density": density,
            },
        }
    
    # =========================================================================
    # LINGUISTIC STYLE PRIORS (for Ad Copy Optimization)
    # =========================================================================
    
    def get_linguistic_fingerprint(self, archetype: str) -> Dict[str, Any]:
        """
        Get linguistic style fingerprint for an archetype.
        
        Used for matching ad copy style to archetype's natural language.
        
        Returns fingerprint with:
        - certainty: How definitive their language is
        - hedging: How much they qualify statements
        - superlatives: Use of extreme language
        - first_person_ratio: Personal vs objective perspective
        - emotional_intensity: Exclamation, question, caps usage
        - complexity: Sentence length, vocabulary diversity
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict with linguistic style metrics
        """
        return self._linguistic_fingerprints.get(archetype, {})
    
    def get_optimal_ad_copy_style(self, archetype: str) -> Dict[str, Any]:
        """
        Get recommendations for ad copy style based on archetype's linguistic patterns.
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict with ad copy recommendations
        """
        fp = self.get_linguistic_fingerprint(archetype)
        if not fp:
            return {"style": "balanced", "recommendations": []}
        
        recommendations = []
        
        # Certainty
        certainty = fp.get("certainty", {}).get("mean", 0.1)
        if certainty > 0.15:
            recommendations.append("Use definitive language: 'THE best', 'Guaranteed'")
        else:
            recommendations.append("Use softer language: 'Consider', 'You might enjoy'")
        
        # Superlatives
        superlative_rate = fp.get("superlatives", {}).get("mean", 0.2)
        if superlative_rate > 0.4:
            recommendations.append("Use superlatives freely: 'Amazing', 'Incredible', 'Best ever'")
        else:
            recommendations.append("Avoid excessive superlatives - be measured")
        
        # Emotional intensity
        exclamation = fp.get("emotional_intensity", {}).get("exclamation_mean", 0.5)
        if exclamation > 0.8:
            recommendations.append("Use exclamation marks! Show enthusiasm!")
        else:
            recommendations.append("Keep punctuation understated")
        
        # Complexity
        sentence_len = fp.get("complexity", {}).get("avg_sentence_length", 13)
        if sentence_len > 15:
            recommendations.append("Use longer, detailed explanations")
        elif sentence_len < 12:
            recommendations.append("Keep sentences short and punchy")
        
        # First person
        first_person = fp.get("first_person_ratio", {}).get("mean", 0.3)
        if first_person > 0.4:
            recommendations.append("Use personal language: 'You'll love', 'Your experience'")
        else:
            recommendations.append("Use objective framing: 'Features include', 'Known for'")
        
        return {
            "archetype": archetype,
            "style": "enthusiastic" if exclamation > 0.7 else "measured",
            "certainty_level": "high" if certainty > 0.15 else "moderate" if certainty > 0.08 else "low",
            "sentence_target_length": round(sentence_len),
            "use_superlatives": superlative_rate > 0.35,
            "use_exclamations": exclamation > 0.7,
            "perspective": "personal" if first_person > 0.35 else "objective",
            "recommendations": recommendations,
        }
    
    # =========================================================================
    # PERSUASION TECHNIQUE PRIORS (Cialdini Principles)
    # =========================================================================
    
    def get_persuasion_sensitivity(self, archetype: str) -> Dict[str, Any]:
        """
        Get Cialdini persuasion technique sensitivity for an archetype.
        
        Techniques:
        - social_proof: "Everyone is doing it"
        - authority: "Experts recommend"
        - scarcity: "Limited time/availability"
        - reciprocity: "Free gift with purchase"
        - commitment: "Join our community"
        - liking: "People like you love this"
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping technique → sensitivity score
        """
        return self._persuasion_sensitivity.get(archetype, {})
    
    def get_best_persuasion_techniques(
        self, 
        archetype: str, 
        top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Get most effective persuasion techniques for an archetype.
        
        Args:
            archetype: User archetype
            top_n: Number of top techniques to return
        
        Returns:
            List of (technique, sensitivity) tuples, sorted by effectiveness
        """
        sensitivity = self.get_persuasion_sensitivity(archetype)
        if not sensitivity:
            return [("social_proof", 0.4), ("liking", 0.35), ("commitment", 0.3)][:top_n]
        
        sorted_techniques = sorted(
            [
                (tech, data.get("avg_sensitivity", 0))
                for tech, data in sensitivity.items()
            ],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_techniques[:top_n]
    
    def get_emotion_sensitivity(self, archetype: str) -> Dict[str, Any]:
        """
        Get emotional trigger sensitivity for an archetype.
        
        Emotions:
        - fear_anxiety: Risk/worry triggers
        - excitement: Enthusiasm/anticipation
        - trust: Safety/reliability
        - nostalgia: Memory/tradition
        - status: Prestige/exclusivity
        - value: Price/deal sensitivity
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping emotion → sensitivity score
        """
        return self._emotion_sensitivity.get(archetype, {})
    
    def get_best_emotional_triggers(
        self, 
        archetype: str, 
        top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Get most effective emotional triggers for an archetype.
        
        Args:
            archetype: User archetype
            top_n: Number of top triggers to return
        
        Returns:
            List of (emotion, sensitivity) tuples
        """
        sensitivity = self.get_emotion_sensitivity(archetype)
        if not sensitivity:
            return [("excitement", 0.4), ("trust", 0.35), ("value", 0.3)][:top_n]
        
        sorted_emotions = sorted(
            [
                (emotion, data.get("avg_sensitivity", 0))
                for emotion, data in sensitivity.items()
            ],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_emotions[:top_n]
    
    def get_decision_style(self, archetype: str) -> Dict[str, float]:
        """
        Get decision-making style distribution for an archetype.
        
        Styles:
        - analytical: Research-heavy, detail-oriented
        - impulsive: Quick decisions, action-oriented
        - social: Influenced by others, group-oriented
        - balanced: Mix of approaches
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping style → probability
        """
        return self._decision_styles.get(archetype, {})
    
    def get_dominant_decision_style(self, archetype: str) -> Tuple[str, float]:
        """
        Get dominant decision-making style for an archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            (style, probability) tuple
        """
        styles = self.get_decision_style(archetype)
        if styles:
            best = max(styles.items(), key=lambda x: x[1])
            return best[0], best[1]
        return "balanced", 0.5
    
    # =========================================================================
    # COMPLAINT & PRAISE PATTERNS
    # =========================================================================
    
    def get_complaint_patterns(self, archetype: str) -> Dict[str, Any]:
        """
        Get what an archetype typically complains about.
        
        Categories:
        - service_speed: Wait times, delays
        - cleanliness: Hygiene, tidiness
        - staff_attitude: Rudeness, unprofessionalism
        - value_price: Overpriced, poor value
        - quality: Product/service quality issues
        - reliability: Inconsistency
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping complaint category → {count, rate}
        """
        return self._complaint_patterns.get(archetype, {})
    
    def get_top_complaints(self, archetype: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Get top complaint triggers for an archetype.
        
        Args:
            archetype: User archetype
            top_n: Number of complaints to return
        
        Returns:
            List of (complaint_type, rate) tuples
        """
        patterns = self.get_complaint_patterns(archetype)
        if not patterns:
            return [("service_speed", 0.4), ("value_price", 0.2)][:top_n]
        
        sorted_complaints = sorted(
            [
                (cat, data.get("rate", 0))
                for cat, data in patterns.items()
            ],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_complaints[:top_n]
    
    def get_praise_patterns(self, archetype: str) -> Dict[str, Any]:
        """
        Get what an archetype typically praises.
        
        Categories:
        - quality: Product/service excellence
        - atmosphere: Ambiance, environment
        - service_quality: Attentiveness, helpfulness
        - value: Good deal, worth the price
        - reliability: Consistency, dependability
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict mapping praise category → {count, rate}
        """
        return self._praise_patterns.get(archetype, {})
    
    def get_top_praises(self, archetype: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Get top praise triggers for an archetype.
        
        Args:
            archetype: User archetype
            top_n: Number of praises to return
        
        Returns:
            List of (praise_type, rate) tuples
        """
        patterns = self.get_praise_patterns(archetype)
        if not patterns:
            return [("quality", 0.4), ("atmosphere", 0.25)][:top_n]
        
        sorted_praises = sorted(
            [
                (cat, data.get("rate", 0))
                for cat, data in patterns.items()
            ],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_praises[:top_n]
    
    # =========================================================================
    # TRUST & LOYALTY PATTERNS
    # =========================================================================
    
    def get_trust_loyalty_pattern(self, archetype: str) -> Dict[str, Any]:
        """
        Get trust and loyalty orientation for an archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict with trust and loyalty metrics
        """
        return self._trust_loyalty_patterns.get(archetype, {})
    
    def is_trust_focused(self, archetype: str) -> bool:
        """
        Check if archetype is trust-focused (responds to trust signals).
        
        Args:
            archetype: User archetype
        
        Returns:
            True if trust messaging is important
        """
        patterns = self.get_trust_loyalty_pattern(archetype)
        trust_data = patterns.get("trust", {})
        return trust_data.get("net_trust_orientation", 0) > 0.05
    
    def is_loyalty_focused(self, archetype: str) -> bool:
        """
        Check if archetype is loyalty-focused (responds to loyalty programs).
        
        Args:
            archetype: User archetype
        
        Returns:
            True if loyalty messaging is important
        """
        patterns = self.get_trust_loyalty_pattern(archetype)
        loyalty_data = patterns.get("loyalty", {})
        return loyalty_data.get("net_loyalty_orientation", 0) > 0.15
    
    # =========================================================================
    # SENTIMENT INTENSITY
    # =========================================================================
    
    def get_sentiment_intensity(self, archetype: str) -> Dict[str, Any]:
        """
        Get sentiment intensity patterns for an archetype.
        
        Shows how extreme their ratings tend to be.
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict with rating distribution and intensity metrics
        """
        return self._sentiment_intensity.get(archetype, {})
    
    def is_positive_biased(self, archetype: str) -> bool:
        """
        Check if archetype has a positive rating bias.
        
        Important for interpreting feedback from this archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            True if archetype tends toward positive ratings
        """
        sentiment = self.get_sentiment_intensity(archetype)
        return sentiment.get("positivity_bias", 0.5) > 0.55
    
    def is_critical_reviewer(self, archetype: str) -> bool:
        """
        Check if archetype tends to be critical in reviews.
        
        Important for interpreting feedback from this archetype.
        
        Args:
            archetype: User archetype
        
        Returns:
            True if archetype tends toward negative/critical reviews
        """
        sentiment = self.get_sentiment_intensity(archetype)
        return sentiment.get("extreme_negative_rate", 0.1) > 0.3
    
    # =========================================================================
    # USER PROFILE PATTERNS (Social Influence)
    # =========================================================================
    
    def get_user_profile_pattern(self, archetype: str) -> Dict[str, Any]:
        """
        Get Yelp user profile patterns for an archetype.
        
        Shows expertise, social connectivity, and status orientation.
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict with expertise, social, status, and positivity metrics
        """
        return self._user_profile_patterns.get(archetype, {})
    
    def get_social_influence_type(self, archetype: str) -> Dict[str, Any]:
        """
        Get social influence type for an archetype.
        
        From Yelp vote patterns (useful/funny/cool).
        
        Args:
            archetype: User archetype
        
        Returns:
            Dict with vote patterns and influence type
        """
        return self._social_influence_type.get(archetype, {})
    
    def is_information_authority(self, archetype: str) -> bool:
        """
        Check if archetype is an information authority (writes influential content).
        
        Based on Yelp 'useful' votes received.
        
        Args:
            archetype: User archetype
        
        Returns:
            True if archetype is an information provider
        """
        influence = self.get_social_influence_type(archetype)
        return influence.get("influence_type") == "information_seeker" and \
               influence.get("avg_useful_votes", 0) > 2
    
    def is_status_seeker(self, archetype: str) -> bool:
        """
        Check if archetype is status-oriented.
        
        Based on Yelp Elite status and profile patterns.
        
        Args:
            archetype: User archetype
        
        Returns:
            True if archetype values status/exclusivity
        """
        profile = self.get_user_profile_pattern(archetype)
        status = profile.get("status", {})
        return status.get("elite_rate", 0) > 0.15
    
    # =========================================================================
    # COMPREHENSIVE AD COPY OPTIMIZER
    # =========================================================================
    
    def generate_ad_copy_strategy(
        self,
        archetype: str,
        category: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive ad copy strategy for an archetype.
        
        Combines all learned priors to provide actionable ad copy guidance.
        
        Args:
            archetype: Target user archetype
            category: Product/service category (optional)
            brand: Brand name (optional)
        
        Returns:
            Comprehensive ad copy strategy with:
            - Linguistic style recommendations
            - Persuasion techniques to use
            - Emotional triggers to emphasize
            - Pain points to address
            - Trust/loyalty messaging
            - Timing recommendations
        """
        strategy = {
            "archetype": archetype,
            "category": category,
            "brand": brand,
        }
        
        # 1. Linguistic style
        strategy["linguistic_style"] = self.get_optimal_ad_copy_style(archetype)
        
        # 2. Persuasion techniques
        best_techniques = self.get_best_persuasion_techniques(archetype, top_n=3)
        strategy["persuasion_techniques"] = {
            "primary": best_techniques[0] if best_techniques else ("social_proof", 0.4),
            "secondary": best_techniques[1] if len(best_techniques) > 1 else None,
            "tertiary": best_techniques[2] if len(best_techniques) > 2 else None,
            "technique_to_phrase": {
                "social_proof": ["Join thousands who...", "Everyone loves...", "Most popular choice"],
                "authority": ["Expert-recommended", "Award-winning", "Industry-leading"],
                "scarcity": ["Limited time", "Only X left", "Exclusive access"],
                "reciprocity": ["Free gift with...", "Bonus included", "Complimentary..."],
                "commitment": ["Join our community", "Become a member", "Start your journey"],
                "liking": ["Made for people like you", "Your perfect match", "Designed for..."],
            },
        }
        
        # 3. Emotional triggers
        best_emotions = self.get_best_emotional_triggers(archetype, top_n=3)
        strategy["emotional_triggers"] = {
            "primary": best_emotions[0] if best_emotions else ("excitement", 0.4),
            "secondary": best_emotions[1] if len(best_emotions) > 1 else None,
            "emotion_to_phrase": {
                "fear_anxiety": ["Don't miss out", "Protect yourself", "Avoid the hassle"],
                "excitement": ["Discover", "Experience", "Unlock"],
                "trust": ["Guaranteed", "Reliable", "Trusted by..."],
                "nostalgia": ["Remember when...", "Classic", "Timeless"],
                "status": ["Exclusive", "Premium", "VIP access"],
                "value": ["Save", "Best deal", "Unbeatable price"],
            },
        }
        
        # 4. Decision style
        decision_style, confidence = self.get_dominant_decision_style(archetype)
        strategy["decision_approach"] = {
            "style": decision_style,
            "confidence": confidence,
            "cta_recommendation": {
                "analytical": "Learn more / Compare options / See the details",
                "impulsive": "Buy now / Get it today / Limited time",
                "social": "Join others / Share with friends / See what others say",
                "balanced": "Discover / Try it / Start now",
            }.get(decision_style, "Learn more"),
        }
        
        # 5. Pain points to address
        top_complaints = self.get_top_complaints(archetype, top_n=2)
        strategy["pain_points_to_address"] = {
            complaint: {
                "service_speed": "Fast service guaranteed",
                "cleanliness": "Pristine, sanitized environment",
                "staff_attitude": "Friendly, professional team",
                "value_price": "Best value guaranteed",
                "quality": "Premium quality assured",
                "reliability": "Consistent excellence every time",
            }.get(complaint, "Quality guaranteed")
            for complaint, _ in top_complaints
        }
        
        # 6. Delight triggers to emphasize
        top_praises = self.get_top_praises(archetype, top_n=2)
        strategy["delight_triggers"] = {
            praise: rate for praise, rate in top_praises
        }
        
        # 7. Trust/loyalty messaging
        strategy["trust_loyalty"] = {
            "emphasize_trust": self.is_trust_focused(archetype),
            "emphasize_loyalty": self.is_loyalty_focused(archetype),
            "trust_phrases": ["Guaranteed", "Money-back promise", "Trusted since..."],
            "loyalty_phrases": ["Rewards program", "VIP benefits", "Member exclusive"],
        }
        
        # 8. Rating interpretation
        strategy["feedback_interpretation"] = {
            "positive_bias": self.is_positive_biased(archetype),
            "critical_reviewer": self.is_critical_reviewer(archetype),
            "note": "A 3-star from this archetype is " + 
                   ("actually negative" if self.is_positive_biased(archetype) else 
                    "actually positive" if self.is_critical_reviewer(archetype) else 
                    "neutral"),
        }
        
        # 9. Social proof type
        strategy["social_proof_type"] = {
            "information_authority": self.is_information_authority(archetype),
            "status_seeker": self.is_status_seeker(archetype),
            "best_proof_type": "expert testimonials" if self.is_information_authority(archetype)
                              else "celebrity/influencer" if self.is_status_seeker(archetype)
                              else "customer reviews",
        }
        
        # 10. Temporal optimization
        best_hours = self.get_best_hours_for_archetype(archetype)
        temporal_behavior = self._temporal_behavior.get("hour_of_day", {}).get(archetype, {})
        strategy["timing"] = {
            "best_hours": best_hours,
            "peak_hour": temporal_behavior.get("peak_hour", 19),
            "weekend_preference": temporal_behavior.get("weekend_rate", 0.3) > 0.35,
        }
        
        return strategy

    # =========================================================================
    # GLOBAL DISTRIBUTION
    # =========================================================================
    
    def get_corpus_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the learning corpus.
        
        Returns:
            Dict with source statistics and totals
        """
        total_reviews = sum(s.get("reviews", 0) for s in self._source_statistics.values())
        total_reviewers = sum(s.get("unique_reviewers", 0) for s in self._source_statistics.values())
        
        return {
            "total_reviews": total_reviews,
            "total_unique_reviewers": total_reviewers,
            "sources": self._source_statistics,
            "categories_learned": len(self._category_priors),
            "brands_learned": len(self._brand_archetype_priors),
            "global_archetype_distribution": self._global_archetype_distribution,
        }
    
    # =========================================================================
    # COMPREHENSIVE COLD-START PREDICTION
    # =========================================================================
    
    def predict_archetype_comprehensive(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        review_count: Optional[int] = None,
        brand_count: Optional[int] = None,
        hour_of_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive archetype prediction using all available signals.
        
        Combines:
        - Category prior (30% weight)
        - Brand prior (25% weight)
        - Lifecycle prior (20% weight)
        - Loyalty prior (15% weight)
        - Temporal adjustment (10% weight)
        
        Args:
            category: Product/content category
            brand: Brand name
            review_count: User's total review count
            brand_count: Number of distinct brands user has purchased
            hour_of_day: Current hour (0-23) for temporal adjustment
        
        Returns:
            Dict with predicted archetype, confidence, and breakdown
        """
        weighted_priors = {}
        weights_used = {}
        
        # 1. Category prior (30%)
        if category:
            cat_prior = self.get_category_archetype_prior(category)
            for arch, prob in cat_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.30
            weights_used["category"] = 0.30
        
        # 2. Brand prior (25%)
        if brand:
            brand_prior = self.get_brand_archetype_prior(brand)
            for arch, prob in brand_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.25
            weights_used["brand"] = 0.25
        
        # 3. Lifecycle prior (20%)
        if review_count is not None:
            segment = self.get_lifecycle_segment(review_count)
            lifecycle_prior = self.get_lifecycle_archetype_distribution(segment)
            for arch, prob in lifecycle_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.20
            weights_used["lifecycle"] = 0.20
        
        # 4. Loyalty prior (15%)
        if brand_count is not None:
            segment = self.get_loyalty_segment(brand_count)
            loyalty_prior = self.get_loyalty_archetype_distribution(segment)
            for arch, prob in loyalty_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * 0.15
            weights_used["loyalty"] = 0.15
        
        # 5. Use global prior for remaining weight
        remaining_weight = 1.0 - sum(weights_used.values())
        if remaining_weight > 0:
            global_prior = self._get_global_archetype_prior()
            for arch, prob in global_prior.items():
                weighted_priors[arch] = weighted_priors.get(arch, 0) + prob * remaining_weight
            weights_used["global"] = remaining_weight
        
        # Normalize
        total = sum(weighted_priors.values())
        if total > 0:
            weighted_priors = {k: v / total for k, v in weighted_priors.items()}
        
        # Get best archetype
        best_archetype = max(weighted_priors.items(), key=lambda x: x[1])
        
        # Temporal adjustment (informational only)
        temporal_note = None
        if hour_of_day is not None and best_archetype[0] in self._temporal_patterns:
            is_optimal = self.is_optimal_engagement_time(best_archetype[0], hour_of_day)
            temporal_note = "optimal_time" if is_optimal else "suboptimal_time"
        
        return {
            "archetype": best_archetype[0],
            "confidence": best_archetype[1],
            "distribution": weighted_priors,
            "weights_used": weights_used,
            "temporal_status": temporal_note,
        }
    
    # =========================================================================
    # CALIBRATION
    # =========================================================================
    
    def get_platt_parameters(self) -> Tuple[float, float]:
        """
        Get Platt scaling parameters for confidence calibration.
        
        Returns:
            (A, B) parameters for sigmoid: 1 / (1 + exp(-(A*x + B)))
        """
        params = self._calibration_config.get("platt_parameters", {})
        return params.get("A", 1.0), params.get("B", 0.0)
    
    def calibrate_confidence(self, raw_confidence: float) -> float:
        """
        Apply Platt scaling to calibrate a confidence score.
        
        Args:
            raw_confidence: Uncalibrated confidence (0-1)
        
        Returns:
            Calibrated confidence (0-1)
        """
        A, B = self.get_platt_parameters()
        
        # Avoid numerical issues
        z = -(A * raw_confidence + B)
        z = np.clip(z, -500, 500)
        
        calibrated = 1 / (1 + np.exp(z))
        return float(np.clip(calibrated, 0, 1))
    
    def is_calibration_needed(self) -> bool:
        """Check if calibration adjustment is recommended."""
        analysis = self._calibration_config.get("analysis", {})
        diagnosis = analysis.get("diagnosis", "unknown")
        return diagnosis != "well-calibrated"
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    @property
    def is_loaded(self) -> bool:
        """Check if priors are loaded."""
        return self._loaded
    
    def get_loading_status(self) -> Dict[str, bool]:
        """Get status of each prior type."""
        return {
            "thompson_warm_start": bool(self._thompson_warm_start),
            "category_priors": bool(self._category_priors),
            "cluster_priors": bool(self._cluster_priors),
            "mechanism_matrix": bool(self._archetype_mechanism_matrix),
            "calibration_config": bool(self._calibration_config),
            # Complete cold-start priors
            "complete_coldstart": bool(self._complete_coldstart_priors),
            "brand_priors": bool(self._brand_archetype_priors),
            "temporal_patterns": bool(self._temporal_patterns),
            "lifecycle_patterns": bool(self._reviewer_lifecycle),
            "loyalty_segments": bool(self._brand_loyalty_segments),
            "price_preferences": bool(self._price_tier_preferences),
            "global_distribution": bool(self._global_archetype_distribution),
            # Location-aware priors (Google Reviews)
            "state_priors": bool(self._state_archetype_priors),
            "region_priors": bool(self._region_archetype_priors),
            "density_priors": bool(self._density_archetype_priors),
            "business_response": bool(self._business_response_archetypes),
            "state_categories": bool(self._state_category_preferences),
            "multi_state_patterns": bool(self._multi_state_patterns),
            # Enhanced psycholinguistic priors
            "linguistic_fingerprints": bool(self._linguistic_fingerprints),
            "complaint_patterns": bool(self._complaint_patterns),
            "praise_patterns": bool(self._praise_patterns),
            "trust_loyalty_patterns": bool(self._trust_loyalty_patterns),
            "sentiment_intensity": bool(self._sentiment_intensity),
            "persuasion_sensitivity": bool(self._persuasion_sensitivity),
            "emotion_sensitivity": bool(self._emotion_sensitivity),
            "decision_styles": bool(self._decision_styles),
            "social_influence_type": bool(self._social_influence_type),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of loaded priors."""
        corpus_stats = self.get_corpus_statistics()
        return {
            "loaded": self._loaded,
            "loading_status": self.get_loading_status(),
            "corpus": {
                "total_reviews": corpus_stats.get("total_reviews", 0),
                "total_reviewers": corpus_stats.get("total_unique_reviewers", 0),
                "sources": list(corpus_stats.get("sources", {}).keys()),
            },
            "counts": {
                "categories": len(self._category_priors),
                "brands": len(self._brand_archetype_priors),
                "states": len(self._state_archetype_priors),
                "regions": len(self._region_archetype_priors),
                "archetypes_in_thompson": len(self._thompson_warm_start),
                "archetypes_in_mechanism_matrix": len(self._archetype_mechanism_matrix),
            },
            "capabilities": {
                "category_prediction": bool(self._category_priors),
                "brand_prediction": bool(self._brand_archetype_priors),
                "lifecycle_prediction": bool(self._reviewer_lifecycle),
                "temporal_optimization": bool(self._temporal_patterns),
                "price_tier_prediction": bool(self._price_tier_preferences),
                "thompson_sampling": bool(self._thompson_warm_start),
                "mechanism_ranking": bool(self._archetype_mechanism_matrix),
                "confidence_calibration": bool(self._calibration_config),
                # Location-aware capabilities
                "state_prediction": bool(self._state_archetype_priors),
                "region_prediction": bool(self._region_archetype_priors),
                "density_prediction": bool(self._density_archetype_priors),
                "business_response_analysis": bool(self._business_response_archetypes),
                "state_category_analysis": bool(self._state_category_preferences),
                "multi_state_analysis": bool(self._multi_state_patterns),
            },
        }


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

def get_learned_priors() -> LearnedPriorsService:
    """Get the singleton LearnedPriorsService instance."""
    return LearnedPriorsService.get_instance()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_best_mechanisms(archetype: str, top_n: int = 3) -> List[Tuple[str, float]]:
    """Convenience function to get best mechanisms for archetype."""
    return get_learned_priors().get_best_mechanisms_for_archetype(archetype, top_n)


def get_archetype_prior(category: str) -> Dict[str, float]:
    """Convenience function to get archetype prior for category."""
    return get_learned_priors().get_category_archetype_prior(category)


def calibrate(confidence: float) -> float:
    """Convenience function to calibrate confidence."""
    return get_learned_priors().calibrate_confidence(confidence)


def warm_start_beta(archetype: str, mechanism: str) -> Tuple[float, float]:
    """Convenience function to get warm-start Beta parameters."""
    return get_learned_priors().get_beta_parameters_for_mechanism(archetype, mechanism)


# =============================================================================
# NEW CONVENIENCE FUNCTIONS (Cold-Start Learning)
# =============================================================================

def get_brand_prior(brand: str) -> Dict[str, float]:
    """Convenience function to get archetype prior for brand."""
    return get_learned_priors().get_brand_archetype_prior(brand)


def predict_archetype_for_brand(brand: str) -> Tuple[str, float]:
    """Convenience function to predict archetype from brand."""
    return get_learned_priors().get_archetype_for_brand(brand)


def get_best_engagement_hours(archetype: str) -> List[int]:
    """Convenience function to get best hours for archetype engagement."""
    return get_learned_priors().get_best_hours_for_archetype(archetype)


def is_good_time_to_engage(archetype: str, hour: int) -> bool:
    """Convenience function to check if current time is good for engagement."""
    return get_learned_priors().is_optimal_engagement_time(archetype, hour)


def predict_archetype_from_review_count(review_count: int) -> Tuple[str, float]:
    """Convenience function to predict archetype from review history."""
    return get_learned_priors().predict_archetype_from_lifecycle(review_count)


def get_preferred_price_tier_for_archetype(archetype: str) -> str:
    """Convenience function to get preferred price tier."""
    return get_learned_priors().get_preferred_price_tier(archetype)


def predict_archetype_comprehensive(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    review_count: Optional[int] = None,
    brand_count: Optional[int] = None,
    hour_of_day: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Comprehensive archetype prediction using all available signals.
    
    This is the recommended function for cold-start archetype prediction.
    """
    return get_learned_priors().predict_archetype_comprehensive(
        category=category,
        brand=brand,
        review_count=review_count,
        brand_count=brand_count,
        hour_of_day=hour_of_day,
    )


def get_corpus_stats() -> Dict[str, Any]:
    """Convenience function to get learning corpus statistics."""
    return get_learned_priors().get_corpus_statistics()


def get_priors_summary() -> Dict[str, Any]:
    """Convenience function to get summary of all loaded priors."""
    return get_learned_priors().get_summary()


# =============================================================================
# LOCATION-AWARE CONVENIENCE FUNCTIONS (Google Reviews)
# =============================================================================

def get_state_prior(state: str) -> Dict[str, float]:
    """Convenience function to get archetype prior for a US state."""
    return get_learned_priors().get_state_archetype_prior(state)


def predict_archetype_for_state(state: str) -> Tuple[str, float]:
    """Convenience function to predict archetype from state."""
    return get_learned_priors().get_archetype_for_state(state)


def get_region_prior(region: str) -> Dict[str, float]:
    """Convenience function to get archetype prior for a US region."""
    return get_learned_priors().get_region_archetype_prior(region)


def get_density_prior(density: str) -> Dict[str, float]:
    """Convenience function to get archetype prior for geographic density."""
    return get_learned_priors().get_density_archetype_prior(density)


def get_state_top_categories(state: str, top_n: int = 5) -> List[Tuple[str, float]]:
    """Convenience function to get top local service categories for a state."""
    return get_learned_priors().get_top_categories_for_state(state, top_n)


def predict_archetype_with_location(
    state: Optional[str] = None,
    region: Optional[str] = None,
    density: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Location-aware archetype prediction.
    
    Combines geographic signals with category/brand for comprehensive prediction.
    """
    return get_learned_priors().predict_archetype_with_location(
        state=state,
        region=region,
        density=density,
        category=category,
        brand=brand,
    )


# =============================================================================
# ENHANCED PSYCHOLINGUISTIC CONVENIENCE FUNCTIONS
# =============================================================================

def get_ad_copy_style(archetype: str) -> Dict[str, Any]:
    """Get optimal ad copy style recommendations for an archetype."""
    return get_learned_priors().get_optimal_ad_copy_style(archetype)


def get_best_persuasion_techniques(archetype: str, top_n: int = 3) -> List[Tuple[str, float]]:
    """Get most effective Cialdini persuasion techniques for an archetype."""
    return get_learned_priors().get_best_persuasion_techniques(archetype, top_n)


def get_best_emotional_triggers(archetype: str, top_n: int = 3) -> List[Tuple[str, float]]:
    """Get most effective emotional triggers for an archetype."""
    return get_learned_priors().get_best_emotional_triggers(archetype, top_n)


def get_decision_style(archetype: str) -> Tuple[str, float]:
    """Get dominant decision-making style for an archetype."""
    return get_learned_priors().get_dominant_decision_style(archetype)


def get_complaint_patterns(archetype: str) -> List[Tuple[str, float]]:
    """Get top complaint triggers for an archetype."""
    return get_learned_priors().get_top_complaints(archetype, top_n=3)


def get_praise_patterns(archetype: str) -> List[Tuple[str, float]]:
    """Get top praise triggers for an archetype."""
    return get_learned_priors().get_top_praises(archetype, top_n=3)


def is_trust_focused(archetype: str) -> bool:
    """Check if archetype responds to trust messaging."""
    return get_learned_priors().is_trust_focused(archetype)


def is_loyalty_focused(archetype: str) -> bool:
    """Check if archetype responds to loyalty programs."""
    return get_learned_priors().is_loyalty_focused(archetype)


def is_positive_reviewer(archetype: str) -> bool:
    """Check if archetype has positive rating bias."""
    return get_learned_priors().is_positive_biased(archetype)


def is_critical_reviewer(archetype: str) -> bool:
    """Check if archetype tends to be critical."""
    return get_learned_priors().is_critical_reviewer(archetype)


def generate_ad_strategy(
    archetype: str,
    category: Optional[str] = None,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive ad copy strategy for an archetype.
    
    This is the RECOMMENDED function for ad optimization.
    Returns complete strategy with linguistic style, persuasion techniques,
    emotional triggers, pain points, and timing recommendations.
    """
    return get_learned_priors().generate_ad_copy_strategy(
        archetype=archetype,
        category=category,
        brand=brand,
    )
