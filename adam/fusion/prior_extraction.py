"""
Prior Extraction Service (Layer 1)
====================================

The billion-review corpus provides **prior knowledge** — empirical
baselines for which psychological approaches work for which profiles
in which categories. This service makes those priors available to
every decision point in the platform.

Query interface:
    Input:  category, brand (opt), target trait profile, target mechanism
    Output: CorpusPrior with ranked mechanism priors, confidence intervals,
            evidence counts, and helpful-vote-weighted confidence

Handles:
    - Exact category match
    - Parent category fallback
    - Cross-category psychological transfer (the highest-leverage capability)
    - Helpful-vote confidence boosting

The returned CorpusPrior feeds directly into Thompson Sampling bandits
as corpus-calibrated starting distributions (not uniform priors).
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from adam.fusion.models import (
    ConfidenceLevel,
    CorpusPrior,
    MechanismPriorDetail,
    PriorConfidence,
    PriorSource,
    PriorSourceType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CATEGORY HIERARCHY (for parent fallback)
# =============================================================================

CATEGORY_HIERARCHY: Dict[str, str] = {
    # Subcategories → parent categories
    "bluetooth_speakers": "Electronics",
    "headphones": "Electronics",
    "laptops": "Electronics",
    "smartphones": "Electronics",
    "tablets": "Electronics",
    "cameras": "Electronics",
    "skincare": "Beauty_and_Personal_Care",
    "makeup": "Beauty_and_Personal_Care",
    "haircare": "Beauty_and_Personal_Care",
    "fragrance": "Beauty_and_Personal_Care",
    "running_shoes": "Clothing_Shoes_and_Jewelry",
    "dresses": "Clothing_Shoes_and_Jewelry",
    "watches": "Clothing_Shoes_and_Jewelry",
    "kitchen_appliances": "Home_and_Kitchen",
    "cookware": "Home_and_Kitchen",
    "furniture": "Home_and_Kitchen",
    "bedding": "Home_and_Kitchen",
    "vitamins": "Health_and_Household",
    "supplements": "Health_and_Household",
    "cleaning": "Health_and_Household",
    "dog_food": "Pet_Supplies",
    "cat_toys": "Pet_Supplies",
    "board_games": "Toys_and_Games",
    "fiction": "Books",
    "nonfiction": "Books",
    "textbooks": "Books",
    "baby_food": "Baby_Products",
    "diapers": "Baby_Products",
    "protein_powder": "Grocery_and_Gourmet_Food",
    "snacks": "Grocery_and_Gourmet_Food",
    "coffee": "Grocery_and_Gourmet_Food",
    "car_accessories": "Automotive",
    "tires": "Automotive",
    "hand_tools": "Tools_and_Home_Improvement",
    "power_tools": "Tools_and_Home_Improvement",
}

# Psychological transfer bridges: trait_profile → related categories
# A high-openness buyer of experimental cookbooks and a high-openness
# buyer of indie music share an invariant
TRAIT_CATEGORY_BRIDGES: Dict[str, List[str]] = {
    "high_openness": [
        "Books", "Digital_Music", "Arts_Crafts_and_Sewing",
        "Musical_Instruments", "Software", "Toys_and_Games",
    ],
    "high_conscientiousness": [
        "Office_Products", "Tools_and_Home_Improvement", "Automotive",
        "Industrial_and_Scientific", "Health_and_Household",
    ],
    "high_extraversion": [
        "Sports_and_Outdoors", "Clothing_Shoes_and_Jewelry",
        "Cell_Phones_and_Accessories", "Beauty_and_Personal_Care",
    ],
    "high_agreeableness": [
        "Baby_Products", "Pet_Supplies", "Grocery_and_Gourmet_Food",
        "Home_and_Kitchen", "Gift_Cards",
    ],
    "high_neuroticism": [
        "Health_and_Household", "Home_and_Kitchen",
        "Baby_Products", "Automotive",
    ],
    "promotion_focused": [
        "Sports_and_Outdoors", "Electronics", "Digital_Music",
        "Clothing_Shoes_and_Jewelry", "Beauty_and_Personal_Care",
    ],
    "prevention_focused": [
        "Health_and_Household", "Automotive", "Baby_Products",
        "Home_and_Kitchen", "Industrial_and_Scientific",
    ],
}


class PriorExtractionService:
    """
    Extracts structured priors from the billion-review corpus.

    This is the primary interface from the inference engine to
    corpus intelligence. Every mechanism selection, creative generation,
    and cold-start bootstrap should query this service.
    """

    def __init__(self):
        self._priors_data: Optional[Dict[str, Any]] = None
        self._helpful_vote_stats: Dict[str, float] = {}  # category → avg votes
        self._graph_service = None

    # =========================================================================
    # DATA LOADING
    # =========================================================================

    def _load_priors(self) -> Dict[str, Any]:
        """Load merged priors via UnifiedIntelligenceService (Layer 1), with file fallback."""
        if self._priors_data is not None:
            return self._priors_data

        try:
            from adam.intelligence.unified_intelligence_service import (
                get_unified_intelligence_service,
            )
            svc = get_unified_intelligence_service()
            raw = svc._load_layer1_priors()
            if raw:
                self._priors_data = raw
                total = raw.get("total_reviews_processed", 0)
                logger.info(f"PriorExtractionService loaded via UnifiedIntelligenceService ({total:,} reviews)")
                return self._priors_data
        except Exception as e:
            logger.warning(f"UnifiedIntelligenceService unavailable for priors: {e}")

        priors_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "learning", "ingestion_merged_priors.json",
        )
        if not os.path.exists(priors_path):
            logger.warning(f"Priors file not found: {priors_path}")
            self._priors_data = {}
            return self._priors_data
        try:
            with open(priors_path) as f:
                self._priors_data = json.load(f)
            total = self._priors_data.get("total_reviews_processed", 0)
            logger.info(f"Loaded corpus priors from file ({total:,} reviews)")
        except Exception as e:
            logger.error(f"Failed to load priors: {e}")
            self._priors_data = {}
        return self._priors_data

    def _get_graph_service(self):
        """Lazy-load graph intelligence service."""
        if self._graph_service is None:
            from adam.services.graph_intelligence import get_graph_intelligence_service
            self._graph_service = get_graph_intelligence_service()
        return self._graph_service

    # =========================================================================
    # CATEGORY MATCHING
    # =========================================================================

    def _normalize_category(self, category: str) -> str:
        """Normalize category name to match stored format."""
        return category.strip().replace(" ", "_").replace("-", "_")

    def _find_category_data(
        self,
        category: str,
        matrices: Dict[str, Any],
    ) -> Tuple[Optional[Dict], str, bool]:
        """
        Find category effectiveness data with fallback chain.

        Returns: (data, matched_category, is_fallback)
        """
        norm = self._normalize_category(category)

        # 1. Exact match
        for variant in [norm, norm.title(), norm.lower(), norm.upper(),
                        norm.replace("_", " "), category]:
            if variant in matrices:
                return matrices[variant], variant, False

        # 2. Partial match (e.g. "Beauty" matches "Beauty_and_Personal_Care")
        cat_lower = norm.lower()
        for stored_cat, data in matrices.items():
            if cat_lower in stored_cat.lower() or stored_cat.lower() in cat_lower:
                return data, stored_cat, True

        # 3. Parent category fallback
        parent = CATEGORY_HIERARCHY.get(cat_lower)
        if parent:
            if parent in matrices:
                return matrices[parent], parent, True

        return None, category, True

    # =========================================================================
    # HELPFUL VOTE WEIGHTING
    # =========================================================================

    def _compute_helpful_vote_weight(
        self,
        category: str,
        archetype: Optional[str] = None,
    ) -> float:
        """
        Compute helpful-vote confidence multiplier for a category.

        Categories/profiles with more helpful-vote-validated reviews
        get tighter confidence intervals.
        """
        data = self._load_priors()

        # Check product_ad_profile_aggregates for helpful vote stats
        product_profiles = data.get("product_ad_profile_aggregates", {})
        if not product_profiles:
            return 1.0

        norm_cat = self._normalize_category(category)
        cat_profile = None

        for key, profile in product_profiles.items():
            if norm_cat.lower() in key.lower():
                cat_profile = profile
                break

        if not cat_profile:
            return 1.0

        # Use avg_helpful_votes if available
        avg_votes = 0
        if isinstance(cat_profile, dict):
            avg_votes = cat_profile.get("avg_helpful_votes", 0)
            if avg_votes == 0:
                avg_votes = cat_profile.get("high_influence_reviews", 0) * 0.1

        if avg_votes <= 0:
            return 1.0

        # Logarithmic boost: categories with high helpful vote density
        # get a confidence multiplier
        return 1.0 + math.log(1 + avg_votes) * 0.1

    # =========================================================================
    # CROSS-CATEGORY TRANSFER
    # =========================================================================

    def _find_transfer_categories(
        self,
        target_category: str,
        trait_profile: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[str, str, float]]:
        """
        Find categories to transfer from via psychological invariants.

        Attempts graph traversal first (TraitCategoryBridge nodes / TRANSFERS_TO
        edges in Neo4j), falling back to the static TRAIT_CATEGORY_BRIDGES dict.

        Returns: [(source_category, invariant_name, transfer_strength)]
        """
        if not trait_profile:
            return []

        # --- Attempt 1: Graph traversal ---
        graph_transfers = self._graph_transfer_lookup(target_category, trait_profile)
        if graph_transfers:
            return graph_transfers

        # --- Fallback: Static dict ---
        transfers = []

        for trait_key, bridge_categories in TRAIT_CATEGORY_BRIDGES.items():
            # Parse trait from key
            trait_name = trait_key.replace("high_", "").replace("_focused", "")
            trait_value = trait_profile.get(trait_name, 0.5)

            # Check if the profile has this trait strongly
            is_high = "high" in trait_key and trait_value > 0.65
            is_focused = "focused" in trait_key and trait_value > 0.6

            if is_high or is_focused:
                for bridge_cat in bridge_categories:
                    norm_target = self._normalize_category(target_category)
                    if bridge_cat.lower() != norm_target.lower():
                        # Transfer strength based on trait extremity
                        strength = min(1.0, (trait_value - 0.5) * 2)
                        transfers.append((bridge_cat, trait_key, strength))

        # Sort by transfer strength
        transfers.sort(key=lambda x: x[2], reverse=True)
        return transfers[:5]  # Top 5 transfer sources

    def _graph_transfer_lookup(
        self,
        target_category: str,
        trait_profile: Dict[str, float],
    ) -> List[Tuple[str, str, float]]:
        """
        Attempt graph-based cross-category transfer lookup.

        Uses GraphPatternPersistence.find_transfer_categories() to walk
        TraitCategoryBridge / TRANSFERS_TO edges in Neo4j.
        Returns empty list if graph unavailable or no results found.
        """
        try:
            import asyncio
            from adam.infrastructure.neo4j.pattern_persistence import get_pattern_persistence

            persistence = get_pattern_persistence()

            # Run the async query from sync context
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    persistence.find_transfer_categories(trait_profile, top_k=5),
                    loop,
                )
                categories = future.result(timeout=2.0)
            except RuntimeError:
                categories = asyncio.run(
                    persistence.find_transfer_categories(trait_profile, top_k=5)
                )

            if categories:
                norm_target = self._normalize_category(target_category)
                transfers = []
                for cat in categories:
                    if cat.lower() != norm_target.lower():
                        transfers.append((cat, "graph_traversal", 0.7))
                return transfers[:5] if transfers else []
        except Exception:
            pass
        return []

    # =========================================================================
    # PRIMARY EXTRACTION METHOD
    # =========================================================================

    def extract_prior(
        self,
        category: str,
        archetype: Optional[str] = None,
        trait_profile: Optional[Dict[str, float]] = None,
        target_mechanism: Optional[str] = None,
        brand: Optional[str] = None,
        asin: Optional[str] = None,
    ) -> CorpusPrior:
        """
        Extract structured corpus prior for a query.

        This is the main entry point. Given a product category and
        optional targeting parameters, returns ranked mechanism priors
        with confidence intervals and evidence counts.

        When an ASIN is provided, the category-level prior is enriched
        with product-specific intelligence: archetype-weighted mechanism
        priors, the product's ad profile, and its archetype affinities.

        Args:
            category: Product category (e.g., "Electronics", "Beauty")
            archetype: Target customer archetype (e.g., "analyst", "explorer")
            trait_profile: Big Five + extended trait scores {trait: 0-1}
            target_mechanism: If specified, emphasize this mechanism
            brand: Brand name for brand-specific intelligence
            asin: Specific Amazon ASIN for product-level resolution

        Returns:
            CorpusPrior with ranked mechanism priors (product-enriched if ASIN given)
        """
        data = self._load_priors()
        if not data:
            return CorpusPrior(category=category)

        # --- Step 1: Get category effectiveness matrix ---
        cat_matrices = data.get("category_effectiveness_matrices", {})
        global_matrix = data.get("global_effectiveness_matrix", {})

        cat_data, matched_cat, is_fallback = self._find_category_data(
            category, cat_matrices
        )

        # --- Step 2: Determine archetype ---
        effective_archetype = archetype
        if not effective_archetype and trait_profile:
            effective_archetype = self._infer_archetype_from_traits(
                trait_profile, data
            )
        if not effective_archetype:
            # Use the category's dominant archetype
            cat_archetypes = data.get("category_archetype_distributions", {})
            cat_arch_data = cat_archetypes.get(matched_cat, {})
            if cat_arch_data:
                effective_archetype = max(cat_arch_data, key=cat_arch_data.get)

        # --- Step 3: Extract mechanism priors ---
        mechanism_priors = []
        total_evidence = 0
        source_data = None

        if cat_data and effective_archetype:
            # Category-specific data for this archetype
            source_data = cat_data.get(effective_archetype, {})
        elif cat_data:
            # Average across all archetypes in this category
            source_data = self._average_across_archetypes(cat_data)
        elif global_matrix and effective_archetype:
            # Global data for this archetype
            source_data = global_matrix.get(effective_archetype, {})
            is_fallback = True

        if source_data:
            mechanism_priors, total_evidence = self._build_mechanism_priors(
                source_data, category, effective_archetype, is_fallback
            )

        # --- Step 4: Cross-category transfer if no/thin data ---
        is_transfer = False
        transfer_sources = []
        transfer_invariant = None

        if total_evidence < 100 or not mechanism_priors:
            transfers = self._find_transfer_categories(category, trait_profile)
            if transfers:
                transfer_priors = self._extract_transfer_priors(
                    transfers, cat_matrices, global_matrix, effective_archetype
                )
                if transfer_priors:
                    # Merge transfer priors with any existing (lower weight)
                    mechanism_priors = self._merge_transfer_priors(
                        mechanism_priors, transfer_priors
                    )
                    is_transfer = True
                    transfer_sources = [t[0] for t in transfers[:3]]
                    transfer_invariant = transfers[0][1] if transfers else None
                    total_evidence += sum(
                        mp.confidence.evidence_count for mp in transfer_priors
                    )

        # --- Step 5: Apply helpful-vote weighting ---
        hv_weight = self._compute_helpful_vote_weight(category, effective_archetype)
        for mp in mechanism_priors:
            mp.confidence.helpful_vote_weight = hv_weight

        # --- Step 6: Filter to target mechanism if specified ---
        if target_mechanism:
            # Move target mechanism to top
            mechanism_priors.sort(
                key=lambda m: (m.mechanism == target_mechanism, m.effect_size),
                reverse=True,
            )

        # --- Step 7: Enrich with graph creative implications ---
        self._enrich_with_graph_implications(mechanism_priors)

        # --- Build result ---
        dominant = mechanism_priors[0].mechanism if mechanism_priors else None
        overall_confidence = PriorConfidence(
            evidence_count=total_evidence,
            categories_seen=1 + len(transfer_sources),
            helpful_vote_weight=hv_weight,
            source_type=(
                PriorSourceType.TRANSFER if is_transfer
                else PriorSourceType.CORPUS
            ),
            confidence_level=self._compute_confidence_level(total_evidence, is_transfer),
        )

        # --- Step 8: Product-level enrichment (if ASIN provided) ---
        product_asin = None
        product_mechanism_priors = {}
        product_ad_profile = None
        product_archetype_affinities = None
        product_intelligence_source = None

        if asin:
            # Try Layer 3 (Neo4j annotated graph) first via UnifiedIntelligenceService
            l3_data = self._get_layer3_product_intelligence(asin, category)
            if l3_data:
                product_asin = asin
                product_mechanism_priors = l3_data.get("mechanism_priors", {})
                product_ad_profile = l3_data.get("ad_profile")
                product_archetype_affinities = l3_data.get("archetype_profile")
                product_intelligence_source = "layer3_annotated_graph"
                if not category:
                    category = l3_data.get("category", category)
            else:
                # Fall back to JSON-based product intelligence
                product_data = self._get_product_intelligence(asin)
                if product_data:
                    product_asin = asin
                    product_mechanism_priors = product_data.get("mechanism_priors", {})
                    product_ad_profile = product_data.get("ad_profile")
                    product_archetype_affinities = product_data.get("archetype_profile")
                    product_intelligence_source = product_data.get("source", "direct_product")

                    if not archetype and product_data.get("dominant_archetype"):
                        effective_archetype = product_data["dominant_archetype"]

                    if not category and product_data.get("category"):
                        category = product_data["category"]

        return CorpusPrior(
            category=category,
            archetype=effective_archetype,
            trait_profile=trait_profile,
            mechanism_priors=mechanism_priors,
            total_evidence=total_evidence,
            dominant_mechanism=dominant,
            overall_confidence=overall_confidence,
            is_transfer=is_transfer,
            transfer_source_categories=transfer_sources,
            transfer_invariant=transfer_invariant,
            helpful_vote_density=hv_weight - 1.0,
            # Product-level intelligence
            product_asin=product_asin,
            product_mechanism_priors=product_mechanism_priors,
            product_ad_profile=product_ad_profile,
            product_archetype_affinities=product_archetype_affinities,
            product_intelligence_source=product_intelligence_source,
        )

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _get_layer3_product_intelligence(
        self, asin: str, category: str = "All_Beauty"
    ) -> Optional[Dict[str, Any]]:
        """
        Get product intelligence from Layer 3 annotated graph via
        UnifiedIntelligenceService.get_intelligence().

        Returns mechanism priors derived from Claude-annotated
        ProductDescription nodes (65 constructs) and BRAND_CONVERTED
        edge statistics (27 dimensions).
        """
        try:
            from adam.intelligence.unified_intelligence_service import (
                get_unified_intelligence_service,
            )
            svc = get_unified_intelligence_service()
            intel = svc.get_intelligence(category=category, asin=asin)
            if not intel.get("has_annotated_depth"):
                return None

            mechanism_priors = {}
            for m in intel.get("fused_mechanisms", []):
                mechanism_priors[m["mechanism"]] = m["fused_score"]

            product_props = intel.get("layer3", {}).get("product")
            ad_profile = None
            if product_props:
                ad_profile = {
                    "primary_persuasion": next(
                        (k.replace("ad_persuasion_techniques_", "")
                         for k in product_props
                         if k.startswith("ad_persuasion_techniques_")
                         and product_props[k] and float(product_props[k]) > 0.3),
                        "",
                    ),
                    "category": product_props.get("main_category", category),
                }

            return {
                "asin": asin,
                "category": category,
                "mechanism_priors": mechanism_priors,
                "ad_profile": ad_profile,
                "archetype_profile": intel.get("layer1", {}).get("archetype_weights"),
                "source": "layer3_annotated_graph",
                "layers_used": intel.get("layers_used", []),
            }
        except Exception as e:
            logger.debug(f"Layer 3 product intelligence lookup failed for {asin}: {e}")
            return None

    def _get_product_intelligence(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Get product-level intelligence for a specific ASIN.

        Uses ProductIntelligenceService for direct lookup or similarity transfer.
        """
        try:
            from adam.fusion.product_intelligence import get_product_intelligence_service
            service = get_product_intelligence_service()
            result = service.get_product_enriched_prior(asin)
            return result
        except ImportError:
            logger.debug("ProductIntelligenceService not available")
        except Exception as e:
            logger.debug(f"Product intelligence lookup failed for {asin}: {e}")
        return None

    def _infer_archetype_from_traits(
        self,
        trait_profile: Dict[str, float],
        data: Dict[str, Any],
    ) -> Optional[str]:
        """Map a trait profile to the closest corpus archetype."""
        ndf_data = data.get("ndf_population", {})
        ndf_by_arch = ndf_data.get("ndf_by_archetype", {})

        if not ndf_by_arch:
            # Simple heuristic fallback
            openness = trait_profile.get("openness", 0.5)
            conscientiousness = trait_profile.get("conscientiousness", 0.5)
            extraversion = trait_profile.get("extraversion", 0.5)
            agreeableness = trait_profile.get("agreeableness", 0.5)

            if openness > 0.7:
                return "explorer"
            elif conscientiousness > 0.7:
                return "analyst"
            elif extraversion > 0.7:
                return "connector"
            elif agreeableness > 0.7:
                return "guardian"
            else:
                return "pragmatist"

        # NDF-based matching
        # Map Big Five to NDF dimensions
        ndf_profile = {
            "approach_avoidance": trait_profile.get("extraversion", 0.5),
            "uncertainty_tolerance": trait_profile.get("openness", 0.5),
            "cognitive_engagement": trait_profile.get("conscientiousness", 0.5),
            "social_calibration": trait_profile.get("agreeableness", 0.5),
            "arousal_seeking": trait_profile.get("extraversion", 0.5) * 0.7
            + (1.0 - trait_profile.get("neuroticism", 0.5)) * 0.3,
            "status_sensitivity": 0.5,
            "temporal_horizon": trait_profile.get("conscientiousness", 0.5),
        }

        best_match = None
        best_distance = float("inf")

        for arch_name, arch_data in ndf_by_arch.items():
            arch_means = arch_data.get("ndf_means", {})
            if not arch_means:
                continue

            distance = sum(
                (ndf_profile.get(dim, 0.5) - arch_means.get(dim, 0.5)) ** 2
                for dim in ndf_profile
            )
            if distance < best_distance:
                best_distance = distance
                best_match = arch_name.replace("_archetype", "")

        return best_match

    def _average_across_archetypes(
        self,
        cat_data: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Average mechanism effectiveness across all archetypes."""
        merged: Dict[str, Dict[str, float]] = {}

        for archetype, mechanisms in cat_data.items():
            if not isinstance(mechanisms, dict):
                continue
            for mech, stats in mechanisms.items():
                if not isinstance(stats, dict):
                    continue
                if mech not in merged:
                    merged[mech] = {"success_rate": 0, "sample_size": 0, "count": 0}
                sr = stats.get("success_rate", 0)
                ss = stats.get("sample_size", 0)
                merged[mech]["success_rate"] += sr * ss
                merged[mech]["sample_size"] += ss
                merged[mech]["count"] += 1

        result = {}
        for mech, agg in merged.items():
            total_ss = agg["sample_size"]
            if total_ss > 0:
                result[mech] = {
                    "success_rate": agg["success_rate"] / total_ss,
                    "sample_size": total_ss,
                }
            elif agg["count"] > 0:
                result[mech] = {
                    "success_rate": agg["success_rate"] / agg["count"],
                    "sample_size": agg["count"],
                }

        return result

    def _build_mechanism_priors(
        self,
        source_data: Dict[str, Any],
        category: str,
        archetype: Optional[str],
        is_fallback: bool,
    ) -> Tuple[List[MechanismPriorDetail], int]:
        """Build MechanismPriorDetail list from source data."""
        priors = []
        total_evidence = 0

        for mechanism, stats in source_data.items():
            if not isinstance(stats, dict):
                continue

            sr = stats.get("success_rate", 0.0)
            ss = stats.get("sample_size", 0)
            cats_seen = stats.get("categories_seen", 1)
            total_evidence += ss

            # Convert to Beta distribution parameters
            # α = sr × ss (weighted successes)
            # β = (1-sr) × ss (weighted failures)
            # But scale down for manageable posteriors
            scale = min(ss, 10000)  # Cap pseudo-observations at 10k
            alpha = max(1.0, sr * scale)
            beta_p = max(1.0, (1.0 - sr) * scale)

            confidence = PriorConfidence(
                evidence_count=ss,
                categories_seen=cats_seen,
                source_type=PriorSourceType.CORPUS,
                confidence_level=self._compute_confidence_level(ss, is_fallback),
            )

            priors.append(MechanismPriorDetail(
                mechanism=mechanism,
                effect_size=sr,
                alpha=alpha,
                beta_param=beta_p,
                confidence=confidence,
                source=PriorSource(
                    source_type=PriorSourceType.CORPUS,
                    category=category,
                    archetype=archetype,
                    mechanism=mechanism,
                ),
            ))

        # Sort by effect size
        priors.sort(key=lambda m: m.effect_size, reverse=True)
        return priors, total_evidence

    def _extract_transfer_priors(
        self,
        transfers: List[Tuple[str, str, float]],
        cat_matrices: Dict,
        global_matrix: Dict,
        archetype: Optional[str],
    ) -> List[MechanismPriorDetail]:
        """Build priors from transfer categories."""
        aggregated: Dict[str, Dict[str, float]] = {}

        for source_cat, invariant, strength in transfers:
            cat_data, _, _ = self._find_category_data(source_cat, cat_matrices)
            source = cat_data or global_matrix

            if not source:
                continue

            mech_data = source.get(archetype, {}) if archetype else source
            if not mech_data or not isinstance(mech_data, dict):
                continue

            # Check if mech_data is {mechanism: stats} or {archetype: {mechanism: stats}}
            first_val = next(iter(mech_data.values()), None)
            if isinstance(first_val, dict) and "success_rate" not in first_val:
                # It's archetype-level; average
                mech_data = self._average_across_archetypes(mech_data)

            for mech, stats in mech_data.items():
                if not isinstance(stats, dict):
                    continue
                sr = stats.get("success_rate", 0)
                ss = stats.get("sample_size", 0)

                if mech not in aggregated:
                    aggregated[mech] = {
                        "success_rate": 0.0,
                        "sample_size": 0,
                        "weight_sum": 0.0,
                        "categories": [],
                        "invariant": invariant,
                    }

                w = strength * ss
                aggregated[mech]["success_rate"] += sr * w
                aggregated[mech]["sample_size"] += ss
                aggregated[mech]["weight_sum"] += w
                aggregated[mech]["categories"].append(source_cat)

        # Build transfer priors with reduced confidence
        priors = []
        for mech, agg in aggregated.items():
            ws = agg["weight_sum"]
            if ws <= 0:
                continue

            sr = agg["success_rate"] / ws
            ss = agg["sample_size"]
            # Transfer priors get lower effective sample size
            effective_ss = max(1, int(ss * 0.3))  # 30% of original

            alpha = max(1.0, sr * min(effective_ss, 3000))
            beta_p = max(1.0, (1.0 - sr) * min(effective_ss, 3000))

            priors.append(MechanismPriorDetail(
                mechanism=mech,
                effect_size=sr,
                alpha=alpha,
                beta_param=beta_p,
                confidence=PriorConfidence(
                    evidence_count=effective_ss,
                    categories_seen=len(set(agg["categories"])),
                    source_type=PriorSourceType.TRANSFER,
                    confidence_level=ConfidenceLevel.MODERATE,
                ),
                source=PriorSource(
                    source_type=PriorSourceType.TRANSFER,
                    mechanism=mech,
                    transfer_from_category=agg["categories"][0] if agg["categories"] else None,
                    transfer_via=agg["invariant"],
                ),
            ))

        priors.sort(key=lambda m: m.effect_size, reverse=True)
        return priors

    def _merge_transfer_priors(
        self,
        existing: List[MechanismPriorDetail],
        transfer: List[MechanismPriorDetail],
    ) -> List[MechanismPriorDetail]:
        """Merge transfer priors into existing, weighting existing higher."""
        existing_mechs = {mp.mechanism: mp for mp in existing}
        merged = list(existing)

        for tp in transfer:
            if tp.mechanism in existing_mechs:
                # Existing direct data takes priority; blend slightly
                ep = existing_mechs[tp.mechanism]
                # Weighted average: 70% existing, 30% transfer
                ep.effect_size = ep.effect_size * 0.7 + tp.effect_size * 0.3
            else:
                merged.append(tp)

        merged.sort(key=lambda m: m.effect_size, reverse=True)
        return merged

    def _enrich_with_graph_implications(
        self,
        priors: List[MechanismPriorDetail],
    ) -> None:
        """Attach creative implications from graph if available."""
        try:
            gs = self._get_graph_service()
            construct_ids = [f"mechanism_{mp.mechanism}" for mp in priors[:5]]
            implications = gs.sync_get_creative_implications(construct_ids)

            for mp in priors:
                cid = f"mechanism_{mp.mechanism}"
                if cid in implications:
                    impl_data = implications[cid]
                    if isinstance(impl_data, dict):
                        mp.creative_implications = impl_data.get("construct", {})
        except Exception as e:
            logger.debug(f"Graph enrichment skipped: {e}")

    def _compute_confidence_level(
        self,
        evidence_count: int,
        is_fallback: bool = False,
    ) -> ConfidenceLevel:
        """Map evidence count to confidence level."""
        if is_fallback:
            if evidence_count > 1000:
                return ConfidenceLevel.MODERATE
            return ConfidenceLevel.LOW

        if evidence_count >= 10000:
            return ConfidenceLevel.VERY_HIGH
        elif evidence_count >= 1000:
            return ConfidenceLevel.HIGH
        elif evidence_count >= 100:
            return ConfidenceLevel.MODERATE
        elif evidence_count > 0:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.SPECULATIVE

    # =========================================================================
    # BATCH EXTRACTION (for onboarding)
    # =========================================================================

    def extract_all_mechanism_priors_for_category(
        self,
        category: str,
    ) -> Dict[str, CorpusPrior]:
        """
        Extract priors for ALL archetypes in a category.

        Used during advertiser onboarding to pre-populate
        Thompson bandit distributions for all segments.

        Returns: {archetype: CorpusPrior}
        """
        data = self._load_priors()
        cat_archetypes = data.get("category_archetype_distributions", {})

        norm_cat = self._normalize_category(category)
        archetypes = None

        for variant in [norm_cat, category, norm_cat.title()]:
            if variant in cat_archetypes:
                archetypes = cat_archetypes[variant]
                break

        if not archetypes:
            # Use global archetypes
            archetypes = data.get("global_archetype_distribution", {})

        results = {}
        for arch_name in archetypes:
            clean_name = arch_name.replace("_archetype", "")
            results[clean_name] = self.extract_prior(
                category=category,
                archetype=clean_name,
            )

        return results

    def get_corpus_summary(self) -> Dict[str, Any]:
        """Return summary statistics about the corpus."""
        data = self._load_priors()
        return {
            "total_reviews_processed": data.get("total_reviews_processed", 0),
            "total_products_linked": data.get("total_products_linked", 0),
            "amazon_categories": data.get("amazon_categories", 0),
            "multi_dataset_sources": data.get("multi_dataset_sources", 0),
            "categories_available": list(
                data.get("category_effectiveness_matrices", {}).keys()
            ),
            "archetypes_available": list(
                data.get("global_archetype_distribution", {}).keys()
            ),
            "dimension_count": len(data.get("dimension_distributions", {})),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[PriorExtractionService] = None


def get_prior_extraction_service() -> PriorExtractionService:
    """Get singleton PriorExtractionService."""
    global _service
    if _service is None:
        _service = PriorExtractionService()
    return _service
