# =============================================================================
# Product-Level Intelligence Service
# Location: adam/fusion/product_intelligence.py
# =============================================================================

"""
PRODUCT INTELLIGENCE SERVICE

Provides ASIN-level intelligence from the ingested corpus.

Each of the 32 category result files contains up to 500 product ad profiles
and 500 product archetype profiles. This service:

  1. Loads and indexes all 16,000+ ASIN-level profiles across categories.
  2. Resolves product-level intelligence for a given ASIN or product query.
  3. Enriches category-level priors with product-specific data.
  4. Enables zero-shot product matching via persuasion profile similarity.

Data sources:
  - data/reingestion_output/{Category}_result.json
    → product_ad_profiles:        {ASIN: {primary_persuasion, primary_emotion, primary_value, linguistic_style}}
    → product_archetype_profiles: {ASIN: {archetype: score, ...}}
    → templates:                  [{pattern, helpful_votes, mechanisms, archetype, ...}]
    → effectiveness_matrix:       {archetype: {mechanism: {success_rate, sample_size}}}
"""

import json
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Where the per-category result files live
RESULT_DIR = Path("data/reingestion_output")


# =============================================================================
# PRODUCT INTELLIGENCE MODELS
# =============================================================================

class ProductAdProfile(BaseModel):
    """Psychological advertising profile for a single product (ASIN)."""
    asin: str
    category: str
    primary_persuasion: str = ""
    primary_emotion: str = ""
    primary_value: str = ""
    linguistic_style: str = ""


class ProductArchetypeProfile(BaseModel):
    """Which archetypes are drawn to this product, with affinity scores."""
    asin: str
    category: str
    archetype_scores: Dict[str, float] = Field(default_factory=dict)

    @property
    def dominant_archetype(self) -> Optional[str]:
        if not self.archetype_scores:
            return None
        return max(self.archetype_scores, key=self.archetype_scores.get)

    @property
    def dominant_score(self) -> float:
        if not self.archetype_scores:
            return 0.0
        return max(self.archetype_scores.values())


class ProductIntelligence(BaseModel):
    """Full product-level intelligence for a single ASIN."""
    asin: str
    category: str
    ad_profile: Optional[ProductAdProfile] = None
    archetype_profile: Optional[ProductArchetypeProfile] = None

    # Derived from product archetype + category effectiveness
    product_mechanism_priors: Dict[str, float] = Field(
        default_factory=dict,
        description="Mechanism effectiveness weighted by product's archetype affinity"
    )
    product_confidence: float = Field(
        0.0,
        description="How much product-specific data backs these priors (0-1)"
    )
    evidence_reviews: int = 0

    # Nearest product matches (for zero-shot)
    similar_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Similar ASINs by persuasion profile"
    )


# =============================================================================
# PRODUCT INTELLIGENCE SERVICE
# =============================================================================

class ProductIntelligenceService:
    """
    Loads and indexes ASIN-level product intelligence from category result files.

    Supports:
      - Direct ASIN lookup
      - Persuasion-profile similarity matching (zero-shot transfer)
      - Product-weighted mechanism priors (archetype × effectiveness × product affinity)
    """

    def __init__(self, result_dir: Optional[Path] = None):
        self._result_dir = result_dir or RESULT_DIR
        self._loaded = False

        # Indexes
        self._ad_profiles: Dict[str, ProductAdProfile] = {}            # asin → profile
        self._archetype_profiles: Dict[str, ProductArchetypeProfile] = {}  # asin → profile
        self._category_for_asin: Dict[str, str] = {}                   # asin → category
        self._effectiveness: Dict[str, Dict] = {}                      # category → effectiveness_matrix

        # Persuasion-profile index for similarity search
        self._persuasion_index: Dict[str, List[str]] = {}              # persuasion_key → [asins]

    def _ensure_loaded(self):
        """Lazy-load all category result files."""
        if self._loaded:
            return

        result_files = sorted(self._result_dir.glob("*_result.json"))
        loaded_count = 0

        for fpath in result_files:
            try:
                category = fpath.stem.replace("_result", "")
                with open(fpath) as f:
                    data = json.load(f)

                # Index product ad profiles
                for asin, profile in data.get("product_ad_profiles", {}).items():
                    ad_prof = ProductAdProfile(
                        asin=asin,
                        category=category,
                        primary_persuasion=profile.get("primary_persuasion", ""),
                        primary_emotion=profile.get("primary_emotion", ""),
                        primary_value=profile.get("primary_value", ""),
                        linguistic_style=profile.get("linguistic_style", ""),
                    )
                    self._ad_profiles[asin] = ad_prof
                    self._category_for_asin[asin] = category

                    # Build persuasion-profile index for similarity search
                    key = f"{ad_prof.primary_persuasion}:{ad_prof.primary_emotion}:{ad_prof.primary_value}"
                    self._persuasion_index.setdefault(key, []).append(asin)

                # Index product archetype profiles
                for asin, scores in data.get("product_archetype_profiles", {}).items():
                    arch_prof = ProductArchetypeProfile(
                        asin=asin,
                        category=category,
                        archetype_scores=scores,
                    )
                    self._archetype_profiles[asin] = arch_prof
                    self._category_for_asin.setdefault(asin, category)

                # Store effectiveness matrix
                eff_matrix = data.get("effectiveness_matrix", {})
                if eff_matrix:
                    self._effectiveness[category] = eff_matrix

                loaded_count += 1

            except Exception as e:
                logger.warning(f"Failed to load {fpath.name}: {e}")

        self._loaded = True
        logger.info(
            f"ProductIntelligenceService loaded: {len(self._ad_profiles):,} ad profiles, "
            f"{len(self._archetype_profiles):,} archetype profiles from {loaded_count} categories"
        )

    # =========================================================================
    # DIRECT ASIN LOOKUP
    # =========================================================================

    def get_product_intelligence(self, asin: str) -> Optional[ProductIntelligence]:
        """
        Get full product-level intelligence for a specific ASIN.

        Checks Layer 3 annotated graph first (via UnifiedIntelligenceService),
        then falls back to JSON category result files. Returns mechanism priors
        weighted by the product's actual archetype affinity distribution.
        """
        # Try Layer 3 annotated graph first
        l3 = self._get_layer3_intelligence(asin)
        if l3:
            return l3

        self._ensure_loaded()

        ad_prof = self._ad_profiles.get(asin)
        arch_prof = self._archetype_profiles.get(asin)

        if not ad_prof and not arch_prof:
            return None

        category = self._category_for_asin.get(asin, "")
        intel = ProductIntelligence(
            asin=asin,
            category=category,
            ad_profile=ad_prof,
            archetype_profile=arch_prof,
        )

        # Compute product-weighted mechanism priors
        if arch_prof and category in self._effectiveness:
            intel.product_mechanism_priors = self._compute_product_mechanism_priors(
                arch_prof, self._effectiveness[category]
            )
            intel.product_confidence = self._compute_product_confidence(arch_prof)

        return intel

    def _get_layer3_intelligence(self, asin: str) -> Optional[ProductIntelligence]:
        """
        Query Layer 3 annotated graph for product intelligence.

        Uses UnifiedIntelligenceService to get ProductDescription properties
        and derive mechanism priors from Claude-annotated constructs.
        """
        try:
            from adam.intelligence.unified_intelligence_service import (
                get_unified_intelligence_service,
            )
            svc = get_unified_intelligence_service()
            product_props = svc.get_product_intelligence(asin)
            if not product_props:
                return None

            category = product_props.get("main_category", "All_Beauty")

            ad_prof = ProductAdProfile(
                asin=asin,
                category=category,
                primary_persuasion=next(
                    (k.replace("ad_persuasion_techniques_", "")
                     for k in product_props
                     if k.startswith("ad_persuasion_techniques_")
                     and product_props[k] and float(product_props[k]) > 0.3),
                    "",
                ),
                primary_emotion=next(
                    (k.replace("ad_emotional_appeal_", "")
                     for k in product_props
                     if k.startswith("ad_emotional_appeal_")
                     and product_props[k] and float(product_props[k]) > 0.3),
                    "",
                ),
                primary_value=next(
                    (k.replace("ad_value_propositions_", "")
                     for k in product_props
                     if k.startswith("ad_value_propositions_")
                     and product_props[k] and float(product_props[k]) > 0.3),
                    "",
                ),
            )

            mech_priors = {}
            for mech in ["social_proof", "scarcity", "authority",
                         "reciprocity", "commitment", "liking",
                         "anchoring", "storytelling"]:
                val = product_props.get(f"ad_persuasion_techniques_{mech}")
                if val and float(val) > 0.05:
                    mech_priors[mech] = round(float(val), 4)

            intel = ProductIntelligence(
                asin=asin,
                category=category,
                ad_profile=ad_prof,
                product_mechanism_priors=mech_priors,
                product_confidence=0.85,
            )
            return intel
        except Exception as e:
            logger.debug(f"Layer 3 product intelligence unavailable for {asin}: {e}")
            return None

    def _compute_product_mechanism_priors(
        self,
        arch_prof: ProductArchetypeProfile,
        effectiveness_matrix: Dict,
    ) -> Dict[str, float]:
        """
        Compute mechanism priors weighted by product archetype affinity.

        Instead of using the category average across archetypes, this weighs
        each archetype's mechanism effectiveness by how much that archetype
        is drawn to this specific product.

        Formula: for each mechanism m,
            prior(m) = Σ_a (archetype_affinity(a) × effectiveness(a, m)) / Σ_a archetype_affinity(a)
        """
        scores = arch_prof.archetype_scores
        if not scores:
            return {}

        total_affinity = sum(scores.values())
        if total_affinity <= 0:
            return {}

        mechanism_scores: Dict[str, float] = {}

        for archetype, affinity in scores.items():
            if affinity <= 0:
                continue
            weight = affinity / total_affinity

            arch_mechs = effectiveness_matrix.get(archetype, {})
            for mechanism, stats in arch_mechs.items():
                rate = stats.get("success_rate", 0.0) if isinstance(stats, dict) else 0.0
                mechanism_scores[mechanism] = mechanism_scores.get(mechanism, 0.0) + weight * rate

        return {k: round(v, 6) for k, v in sorted(
            mechanism_scores.items(), key=lambda x: -x[1]
        )}

    def _compute_product_confidence(self, arch_prof: ProductArchetypeProfile) -> float:
        """
        Confidence based on how much archetype data backs this product.

        Higher total archetype score = more reviews analyzed = higher confidence.
        """
        total = sum(arch_prof.archetype_scores.values())
        if total <= 0:
            return 0.0
        # Log scale: 10 reviews → 0.4, 100 → 0.6, 1000 → 0.8, 10000 → 0.95
        return min(0.95, 0.2 + 0.15 * math.log10(max(1, total)))

    # =========================================================================
    # SIMILARITY MATCHING (zero-shot product transfer)
    # =========================================================================

    def find_similar_products(
        self,
        asin: Optional[str] = None,
        persuasion: Optional[str] = None,
        emotion: Optional[str] = None,
        value: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find products with similar psychological profiles.

        If an ASIN is given, finds products with the same persuasion profile.
        If attributes are given directly, matches on those.
        Optionally filters by category.

        This enables zero-shot transfer: "This new product has no data,
        but these 5 similar products do — here are their priors."
        """
        self._ensure_loaded()

        # Determine search key
        if asin and asin in self._ad_profiles:
            prof = self._ad_profiles[asin]
            persuasion = persuasion or prof.primary_persuasion
            emotion = emotion or prof.primary_emotion
            value = value or prof.primary_value

        candidates = []

        # Exact match on persuasion profile
        key = f"{persuasion or ''}:{emotion or ''}:{value or ''}"
        exact_asins = self._persuasion_index.get(key, [])

        for match_asin in exact_asins:
            if match_asin == asin:
                continue
            if category:
                cat = self._category_for_asin.get(match_asin, "")
                if category.lower() not in cat.lower() and cat.lower() not in category.lower():
                    continue
            ad_prof = self._ad_profiles.get(match_asin)
            if ad_prof:
                candidates.append({
                    "asin": match_asin,
                    "category": ad_prof.category,
                    "match_type": "exact_profile",
                    "persuasion": ad_prof.primary_persuasion,
                    "emotion": ad_prof.primary_emotion,
                    "value": ad_prof.primary_value,
                    "linguistic_style": ad_prof.linguistic_style,
                })

        # If not enough exact matches, do partial matching
        if len(candidates) < top_k:
            for p_key, p_asins in self._persuasion_index.items():
                parts = p_key.split(":")
                match_score = 0
                if persuasion and len(parts) > 0 and parts[0] == persuasion:
                    match_score += 3
                if emotion and len(parts) > 1 and parts[1] == emotion:
                    match_score += 2
                if value and len(parts) > 2 and parts[2] == value:
                    match_score += 1

                if match_score >= 2 and p_key != key:
                    for match_asin in p_asins[:2]:
                        if match_asin == asin:
                            continue
                        if category:
                            cat = self._category_for_asin.get(match_asin, "")
                            if category.lower() not in cat.lower() and cat.lower() not in category.lower():
                                continue
                        ad_prof = self._ad_profiles.get(match_asin)
                        if ad_prof and not any(c["asin"] == match_asin for c in candidates):
                            candidates.append({
                                "asin": match_asin,
                                "category": ad_prof.category,
                                "match_type": "partial_profile",
                                "match_score": match_score,
                                "persuasion": ad_prof.primary_persuasion,
                                "emotion": ad_prof.primary_emotion,
                                "value": ad_prof.primary_value,
                                "linguistic_style": ad_prof.linguistic_style,
                            })

        return candidates[:top_k]

    def get_product_enriched_prior(
        self,
        asin: str,
        archetype: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get mechanism priors enriched with product-specific intelligence.

        If ASIN is found, returns product-weighted priors.
        If not found but similar products exist, returns transfer priors.
        """
        self._ensure_loaded()

        intel = self.get_product_intelligence(asin)
        if intel and intel.product_mechanism_priors:
            return {
                "asin": asin,
                "category": intel.category,
                "mechanism_priors": intel.product_mechanism_priors,
                "confidence": intel.product_confidence,
                "source": "direct_product",
                "ad_profile": intel.ad_profile.model_dump() if intel.ad_profile else None,
                "archetype_profile": intel.archetype_profile.archetype_scores if intel.archetype_profile else None,
                "dominant_archetype": intel.archetype_profile.dominant_archetype if intel.archetype_profile else None,
            }

        # Zero-shot: find similar products and aggregate their priors
        similar = self.find_similar_products(asin=asin, top_k=5)
        if similar:
            agg_priors: Dict[str, float] = {}
            count = 0
            for sim in similar:
                sim_intel = self.get_product_intelligence(sim["asin"])
                if sim_intel and sim_intel.product_mechanism_priors:
                    for mech, score in sim_intel.product_mechanism_priors.items():
                        agg_priors[mech] = agg_priors.get(mech, 0.0) + score
                    count += 1

            if count > 0:
                avg_priors = {k: round(v / count, 6) for k, v in agg_priors.items()}
                return {
                    "asin": asin,
                    "category": self._category_for_asin.get(asin, ""),
                    "mechanism_priors": avg_priors,
                    "confidence": min(0.6, 0.15 * count),  # Lower confidence for transfer
                    "source": "similar_product_transfer",
                    "similar_products_used": count,
                    "similar_asins": [s["asin"] for s in similar[:count]],
                }

        return None

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        self._ensure_loaded()
        return {
            "total_ad_profiles": len(self._ad_profiles),
            "total_archetype_profiles": len(self._archetype_profiles),
            "categories_loaded": len(self._effectiveness),
            "unique_persuasion_profiles": len(self._persuasion_index),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_product_intelligence_service: Optional[ProductIntelligenceService] = None


def get_product_intelligence_service() -> ProductIntelligenceService:
    """Get singleton ProductIntelligenceService."""
    global _product_intelligence_service
    if _product_intelligence_service is None:
        _product_intelligence_service = ProductIntelligenceService()
    return _product_intelligence_service
