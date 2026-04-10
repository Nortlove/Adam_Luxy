# =============================================================================
# Review Intelligence Source for AtomDAG
# Location: adam/atoms/review_intelligence_source.py
# =============================================================================

"""
REVIEW INTELLIGENCE SOURCE

Enhanced intelligence source that leverages the massive review corpus learnings:
- 114,608 categories from Amazon, Google Maps, Yelp, Steam, Sephora, etc.
- 12M+ brand profiles with psychological profiles
- 78 regional profiles with cultural values
- 252+ psychological dimensions per profile

This module bridges the review learnings to the AtomDAG's intelligence sources,
providing EMPIRICAL_PATTERNS evidence from real customer data.

Integration Points:
1. EMPIRICAL_PATTERNS source → Category/brand psychology
2. CROSS_DOMAIN_TRANSFER → Similar product recommendations
3. TEMPORAL_PATTERNS → Regional psychology injection
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from adam.atoms.core.base import (
    IntelligenceEvidence,
    IntelligenceSourceType,
    ConfidenceSemantics,
    EvidenceStrength,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ReviewIntelligenceContext:
    """Context for review intelligence queries."""
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    archetype: Optional[str] = None


@dataclass
class PsychologicalProfile:
    """Psychological profile from review learnings."""
    archetypes: Dict[str, float]
    mechanisms: Dict[str, float]
    source: str
    confidence: float
    review_count: int = 0
    
    def get_dominant_archetype(self) -> Tuple[str, float]:
        """Get the dominant archetype."""
        if self.archetypes:
            return max(self.archetypes.items(), key=lambda x: x[1])
        return ("Connector", 0.4)  # Default
    
    def get_best_mechanisms(self, top_n: int = 3) -> List[Tuple[str, float]]:
        """Get best mechanisms sorted by effectiveness."""
        return sorted(
            self.mechanisms.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]


# =============================================================================
# REVIEW INTELLIGENCE QUERIES
# =============================================================================

async def query_review_intelligence(
    context: ReviewIntelligenceContext,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query review learnings for psychological intelligence.
    
    This is the main entry point for atoms to access review corpus learnings.
    Implements hierarchical fallback:
    1. Product-specific (brand + category + product)
    2. Category-specific (category + subcategory)
    3. Brand-specific
    4. Regional (state/region psychology)
    5. Global priors
    
    Args:
        context: ReviewIntelligenceContext with query parameters
        target_construct: What we're trying to assess
        
    Returns:
        IntelligenceEvidence if data found, None otherwise
    """
    profile = None
    source_desc = "review_corpus"
    
    # =========================================================================
    # STRATEGY 1: Try LearnedPriorsService (fastest, in-memory)
    # =========================================================================
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        if priors.is_loaded:
            # Build comprehensive prediction using all available signals
            prediction = priors.predict_archetype_comprehensive(
                category=context.category or context.subcategory,
                brand=context.brand,
            )
            
            # Add location if available
            if context.state or context.region:
                location_prediction = priors.predict_archetype_with_location(
                    state=context.state,
                    region=context.region,
                    category=context.category,
                    brand=context.brand,
                )
                
                # Blend predictions
                for arch, prob in location_prediction.get("distribution", {}).items():
                    if arch in prediction["distribution"]:
                        # Average the two predictions
                        prediction["distribution"][arch] = (
                            prediction["distribution"][arch] * 0.6 + prob * 0.4
                        )
            
            # Get mechanism recommendations based on archetype
            # Try to get archetype from prediction, or detect using granular system
            archetype = prediction.get("archetype")
            if not archetype:
                # Try granular type detection from context
                try:
                    from adam.intelligence.granular_type_detector import detect_granular_type
                    context_text = f"{context.brand or ''} {context.category or ''}"
                    if len(context_text.strip()) > 5:
                        granular_result = detect_granular_type(context_text)
                        archetype = granular_result.archetype.title()
                        logger.debug(f"Detected granular archetype: {granular_result.type_id}")
                except Exception:
                    pass
                
                # Final fallback
                if not archetype:
                    archetype = "Connector"  # Social default
            
            best_mechanisms = priors.get_best_mechanisms_for_archetype(archetype, top_n=3)
            
            # Create evidence
            if best_mechanisms:
                best_mech, best_eff = best_mechanisms[0]
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=target_construct,
                    assessment=best_mech,
                    assessment_value=best_eff,
                    confidence=prediction.get("confidence", 0.7),
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.STRONG if best_eff > 0.4 else EvidenceStrength.MODERATE,
                    support_count=3,  # Top 3 mechanisms
                    reasoning=(
                        f"Review corpus analysis: {best_mech} is optimal for {archetype} "
                        f"archetype ({prediction.get('confidence', 0):.0%} confidence). "
                        f"Based on {context.brand or 'general'} {context.category or 'category'} context. "
                        f"Top 3: {', '.join([f'{m[0]}({m[1]:.0%})' for m in best_mechanisms])}"
                    ),
                    metadata={
                        "source": "learned_priors_service",
                        "archetype_distribution": prediction.get("distribution", {}),
                        "dominant_archetype": archetype,
                        "mechanisms": [
                            {"name": m[0], "effectiveness": m[1]}
                            for m in best_mechanisms
                        ],
                        "weights_used": prediction.get("weights_used", {}),
                        "context": {
                            "brand": context.brand,
                            "category": context.category,
                            "state": context.state,
                        },
                    },
                )
    except ImportError:
        logger.debug("LearnedPriorsService not available")
    except Exception as e:
        logger.debug(f"LearnedPriorsService query failed: {e}")
    
    # =========================================================================
    # STRATEGY 2: Try ReviewLearningsService (Neo4j queries)
    # =========================================================================
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        
        # Build category path
        category_path = context.category
        if context.subcategory:
            category_path = f"{context.category} > {context.subcategory}"
        
        # Get product psychology
        category_profile = service.get_product_psychology(
            brand=context.brand,
            product=context.product,
            category=category_path,
        )
        
        if category_profile and category_profile.match_type != "global":
            # Get mechanism recommendations
            best_mechanisms = service.get_best_mechanisms_for_category(
                category_profile.category_path,
                top_n=3,
            )
            
            dominant_arch, arch_prob = max(
                category_profile.archetypes.items(),
                key=lambda x: x[1]
            )
            
            if best_mechanisms:
                best_mech = best_mechanisms[0]
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=target_construct,
                    assessment=best_mech.mechanism,
                    assessment_value=best_mech.effectiveness,
                    confidence=category_profile.match_confidence,
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=_effectiveness_to_strength(best_mech.effectiveness),
                    support_count=category_profile.review_count,
                    reasoning=(
                        f"Neo4j review learnings ({category_profile.match_type} match): "
                        f"{best_mech.mechanism} is optimal for {dominant_arch} archetype "
                        f"({arch_prob:.0%} of audience). "
                        f"Based on {category_profile.review_count:,} reviews. "
                        f"Path: {category_profile.category_path}"
                    ),
                    metadata={
                        "source": "review_learnings_service",
                        "match_type": category_profile.match_type,
                        "category_path": category_profile.category_path,
                        "archetype_distribution": category_profile.archetypes,
                        "mechanisms": [
                            {"name": m.mechanism, "effectiveness": m.effectiveness}
                            for m in best_mechanisms
                        ],
                        "review_count": category_profile.review_count,
                    },
                )
    except ImportError:
        logger.debug("ReviewLearningsService not available")
    except Exception as e:
        logger.debug(f"ReviewLearningsService query failed: {e}")
    
    # =========================================================================
    # FALLBACK: Return None (caller will use other intelligence sources)
    # =========================================================================
    return None


async def query_regional_psychology(
    state: str,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query regional psychology from Google Maps learnings.
    
    Returns regional psychological modifiers based on:
    - State archetype distribution
    - Cultural values (traditionalism, individualism)
    - Political lean → decision style correlations
    - Religiosity and authority orientation
    
    Args:
        state: US state name
        target_construct: What we're assessing
        
    Returns:
        IntelligenceEvidence with regional psychology
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        if priors.is_loaded and priors._state_archetype_priors:
            state_prior = priors.get_state_archetype_prior(state)
            
            if state_prior and state_prior != priors._get_global_archetype_prior():
                dominant_arch, arch_prob = max(state_prior.items(), key=lambda x: x[1])
                
                # Get mechanism recommendations for this archetype
                best_mechanisms = priors.get_best_mechanisms_for_archetype(dominant_arch, top_n=3)
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.TEMPORAL_PATTERNS,  # Regional is temporal-ish
                    construct=target_construct,
                    assessment=dominant_arch,
                    assessment_value=arch_prob,
                    confidence=0.75,  # Regional priors are moderately confident
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.MODERATE,
                    support_count=1,
                    reasoning=(
                        f"Regional psychology ({state}): {dominant_arch} dominant "
                        f"({arch_prob:.0%}). Top mechanisms: "
                        f"{', '.join([f'{m[0]}({m[1]:.0%})' for m in best_mechanisms])}"
                    ),
                    metadata={
                        "source": "google_maps_regional",
                        "state": state,
                        "archetype_distribution": state_prior,
                        "dominant_archetype": dominant_arch,
                        "mechanisms": [
                            {"name": m[0], "effectiveness": m[1]}
                            for m in best_mechanisms
                        ],
                    },
                )
    except ImportError:
        logger.debug("LearnedPriorsService not available for regional psychology")
    except Exception as e:
        logger.debug(f"Regional psychology query failed: {e}")
    
    return None


async def query_brand_psychology(
    brand: str,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query brand-specific psychology from review learnings.
    
    Based on analysis of customer reviews for specific brands:
    - Which archetypes buy this brand
    - Which mechanisms work best for brand customers
    - Brand personality alignment
    
    Args:
        brand: Brand name
        target_construct: What we're assessing
        
    Returns:
        IntelligenceEvidence with brand psychology
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        if priors.is_loaded and priors._brand_archetype_priors:
            brand_prior = priors.get_brand_archetype_prior(brand)
            
            if brand_prior and brand_prior != priors._get_global_archetype_prior():
                dominant_arch, arch_prob = max(brand_prior.items(), key=lambda x: x[1])
                
                # Get mechanism recommendations
                best_mechanisms = priors.get_best_mechanisms_for_archetype(dominant_arch, top_n=3)
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=target_construct,
                    assessment=dominant_arch,
                    assessment_value=arch_prob,
                    confidence=0.85,  # Brand priors are high confidence
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.STRONG,
                    support_count=1,
                    reasoning=(
                        f"Brand psychology ({brand}): {dominant_arch} archetype "
                        f"({arch_prob:.0%} of buyers). "
                        f"Best mechanisms: {', '.join([f'{m[0]}({m[1]:.0%})' for m in best_mechanisms])}"
                    ),
                    metadata={
                        "source": "brand_review_corpus",
                        "brand": brand,
                        "archetype_distribution": brand_prior,
                        "dominant_archetype": dominant_arch,
                        "mechanisms": [
                            {"name": m[0], "effectiveness": m[1]}
                            for m in best_mechanisms
                        ],
                    },
                )
    except ImportError:
        logger.debug("LearnedPriorsService not available for brand psychology")
    except Exception as e:
        logger.debug(f"Brand psychology query failed: {e}")
    
    return None


async def query_category_psychology(
    category: str,
    subcategory: Optional[str] = None,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query category-specific psychology from review learnings.
    
    Uses the 114,608 category profiles with:
    - Archetype distributions
    - Mechanism effectiveness
    - 252+ psychological dimensions
    
    Args:
        category: Top-level category
        subcategory: Optional subcategory for more specific match
        target_construct: What we're assessing
        
    Returns:
        IntelligenceEvidence with category psychology
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        if priors.is_loaded:
            # Build category key
            cat_key = category
            if subcategory:
                cat_key = f"{category}_{subcategory}"
            
            cat_prior = priors.get_category_archetype_prior(cat_key)
            
            if cat_prior and cat_prior != priors._get_global_archetype_prior():
                dominant_arch, arch_prob = max(cat_prior.items(), key=lambda x: x[1])
                
                best_mechanisms = priors.get_best_mechanisms_for_archetype(dominant_arch, top_n=3)
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=target_construct,
                    assessment=dominant_arch,
                    assessment_value=arch_prob,
                    confidence=0.80,
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.STRONG,
                    support_count=1,
                    reasoning=(
                        f"Category psychology ({cat_key}): {dominant_arch} dominant "
                        f"({arch_prob:.0%}). Optimal mechanisms: "
                        f"{', '.join([f'{m[0]}({m[1]:.0%})' for m in best_mechanisms])}"
                    ),
                    metadata={
                        "source": "category_review_corpus",
                        "category": category,
                        "subcategory": subcategory,
                        "archetype_distribution": cat_prior,
                        "dominant_archetype": dominant_arch,
                        "mechanisms": [
                            {"name": m[0], "effectiveness": m[1]}
                            for m in best_mechanisms
                        ],
                    },
                )
    except ImportError:
        logger.debug("LearnedPriorsService not available for category psychology")
    except Exception as e:
        logger.debug(f"Category psychology query failed: {e}")
    
    return None


def _effectiveness_to_strength(effectiveness: float) -> EvidenceStrength:
    """Convert effectiveness score to evidence strength."""
    if effectiveness > 0.5:
        return EvidenceStrength.STRONG
    elif effectiveness > 0.35:
        return EvidenceStrength.MODERATE
    else:
        return EvidenceStrength.WEAK


# =============================================================================
# COMPREHENSIVE CONTEXT BUILDER
# =============================================================================

def build_review_context(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    product: Optional[str] = None,
    state: Optional[str] = None,
    region: Optional[str] = None,
    archetype: Optional[str] = None,
) -> ReviewIntelligenceContext:
    """Build a context object for review intelligence queries."""
    return ReviewIntelligenceContext(
        brand=brand,
        category=category,
        subcategory=subcategory,
        product=product,
        state=state,
        region=region,
        archetype=archetype,
    )


# =============================================================================
# BANKING-SPECIFIC INTELLIGENCE
# =============================================================================

# Banking psychology from 19K+ bank reviews (47 banks)
_BANKING_CHECKPOINT_CACHE: Optional[Dict] = None


def _load_banking_checkpoint() -> Optional[Dict]:
    """Load banking psychology checkpoint (cached)."""
    global _BANKING_CHECKPOINT_CACHE
    
    if _BANKING_CHECKPOINT_CACHE is not None:
        return _BANKING_CHECKPOINT_CACHE
    
    try:
        import json
        from pathlib import Path
        
        checkpoint_path = Path(__file__).parent.parent.parent / "data" / "learning" / "multi_domain" / "checkpoint_bank_reviews.json"
        
        if checkpoint_path.exists():
            with open(checkpoint_path) as f:
                _BANKING_CHECKPOINT_CACHE = json.load(f)
            logger.info(f"Loaded banking checkpoint: {_BANKING_CHECKPOINT_CACHE.get('total_reviews', 0):,} reviews")
        else:
            logger.debug("Banking checkpoint not found")
            _BANKING_CHECKPOINT_CACHE = {}
    except Exception as e:
        logger.debug(f"Failed to load banking checkpoint: {e}")
        _BANKING_CHECKPOINT_CACHE = {}
    
    return _BANKING_CHECKPOINT_CACHE


async def query_banking_psychology(
    bank_name: Optional[str] = None,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query banking-specific psychology from 19K+ bank reviews.
    
    Banking reviews are uniquely valuable for:
    - Trust/security psychology (critical for financial decisions)
    - Customer service interaction patterns
    - Financial anxiety indicators
    - Digital preference assessment
    
    Args:
        bank_name: Optional specific bank to query
        target_construct: What we're assessing
        
    Returns:
        IntelligenceEvidence with banking psychology
    """
    checkpoint = _load_banking_checkpoint()
    
    if not checkpoint:
        return None
    
    profile = None
    source_desc = "banking_global"
    
    # Try bank-specific profile first
    if bank_name:
        bank_key = bank_name.lower().replace(" ", "_").replace("'", "")
        profiles = checkpoint.get("profiles", {})
        
        for key, p in profiles.items():
            if bank_key in key.lower() or key.lower() in bank_key:
                profile = p
                source_desc = f"bank:{key}"
                break
    
    # Fall back to global banking psychology
    if not profile:
        profile = {
            "archetype_distribution": checkpoint.get("archetype_totals", {}),
            "cialdini_principles": checkpoint.get("cialdini_principles_global", {}),
            "banking_psychology": checkpoint.get("banking_psychology_global", {}),
            "total_reviews": checkpoint.get("total_reviews", 0),
        }
    
    if not profile or not profile.get("archetype_distribution"):
        return None
    
    # Get dominant archetype
    archetypes = profile.get("archetype_distribution", {})
    if archetypes:
        dominant_arch, arch_prob = max(archetypes.items(), key=lambda x: x[1])
    else:
        dominant_arch, arch_prob = "guardian", 0.4
    
    # Get best Cialdini principles for banking
    cialdini = profile.get("cialdini_principles", checkpoint.get("cialdini_principles_global", {}))
    best_mechanisms = sorted(cialdini.items(), key=lambda x: -x[1])[:3]
    
    # Get banking-specific insights
    banking_psych = profile.get("banking_psychology", checkpoint.get("banking_psychology_global", {}))
    
    # Determine mechanism recommendation
    if best_mechanisms:
        best_mech, best_eff = best_mechanisms[0]
    else:
        best_mech, best_eff = "commitment", 0.5  # Default for banking
    
    return IntelligenceEvidence(
        source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
        construct=target_construct,
        assessment=best_mech,
        assessment_value=best_eff,
        confidence=0.85,  # High confidence for banking domain
        confidence_semantics=ConfidenceSemantics.STATISTICAL,
        strength=EvidenceStrength.STRONG,
        support_count=profile.get("total_reviews", checkpoint.get("total_reviews", 19271)),
        reasoning=(
            f"Banking psychology ({source_desc}): {best_mech} optimal for {dominant_arch} "
            f"archetype ({arch_prob:.0%}). Trust score: {banking_psych.get('trust_security', 0):.0%}, "
            f"Anxiety sensitivity: {banking_psych.get('financial_anxiety', 0):.0%}. "
            f"Based on {profile.get('total_reviews', 19271):,} bank reviews."
        ),
        metadata={
            "source": "banking_review_corpus",
            "source_detail": source_desc,
            "archetype_distribution": archetypes,
            "dominant_archetype": dominant_arch,
            "mechanisms": [
                {"name": m[0], "effectiveness": m[1]}
                for m in best_mechanisms
            ],
            "banking_psychology": banking_psych,
            "trust_critical": True,
            "anxiety_sensitive": banking_psych.get("financial_anxiety", 0) > 0.05,
        },
    )


def is_financial_category(category: Optional[str], subcategory: Optional[str] = None) -> bool:
    """Check if a category is finance-related."""
    if not category:
        return False
    
    financial_keywords = [
        "finance", "banking", "bank", "credit", "loan", "mortgage",
        "insurance", "investment", "money", "financial", "fintech",
        "payment", "wallet", "savings", "checking",
    ]
    
    check = (category.lower() + " " + (subcategory or "").lower()).strip()
    return any(kw in check for kw in financial_keywords)


# =============================================================================
# COMPREHENSIVE REVIEW EVIDENCE AGGREGATOR
# =============================================================================

async def get_comprehensive_review_evidence(
    context: ReviewIntelligenceContext,
) -> Dict[str, Optional[IntelligenceEvidence]]:
    """
    Get all available review evidence for a context.
    
    Queries multiple sources in parallel and returns all evidence.
    
    Args:
        context: ReviewIntelligenceContext
        
    Returns:
        Dict mapping source name to evidence
    """
    evidence = {}
    
    # Main review intelligence
    evidence["review_intelligence"] = await query_review_intelligence(context)
    
    # Brand-specific if available
    if context.brand:
        evidence["brand_psychology"] = await query_brand_psychology(context.brand)
    
    # Category-specific
    if context.category:
        evidence["category_psychology"] = await query_category_psychology(
            context.category,
            context.subcategory,
        )
    
    # Regional if available
    if context.state:
        evidence["regional_psychology"] = await query_regional_psychology(context.state)
    
    # Banking-specific for financial categories/brands
    if is_financial_category(context.category, context.subcategory):
        evidence["banking_psychology"] = await query_banking_psychology(context.brand)
    elif context.brand and _is_bank_brand(context.brand):
        evidence["banking_psychology"] = await query_banking_psychology(context.brand)
    
    return evidence


def _is_bank_brand(brand: str) -> bool:
    """Check if a brand is a bank we have data for."""
    checkpoint = _load_banking_checkpoint()
    if not checkpoint:
        return False
    
    brand_lower = brand.lower().replace(" ", "_")
    profiles = checkpoint.get("profiles", {})
    
    for key in profiles.keys():
        if brand_lower in key.lower() or key.lower() in brand_lower:
            return True
    
    return False


# =============================================================================
# MECHANISM SCORE ADJUSTMENT
# =============================================================================

def adjust_mechanism_scores_with_review_evidence(
    base_scores: Dict[str, float],
    evidence: Dict[str, Optional[IntelligenceEvidence]],
    review_weight: float = 0.4,
) -> Dict[str, float]:
    """
    Adjust mechanism scores based on review evidence.
    
    Blends base psychological fit scores with learned effectiveness
    from the review corpus.
    
    Args:
        base_scores: Base mechanism scores from psychological fit
        evidence: Review evidence dict
        review_weight: Weight for review-based adjustments (0-1)
        
    Returns:
        Adjusted mechanism scores
    """
    adjusted = base_scores.copy()
    
    # Collect mechanism effectiveness from all evidence sources
    mechanism_boosts: Dict[str, List[float]] = {}
    
    for source_name, evi in evidence.items():
        if evi and evi.metadata:
            mechanisms = evi.metadata.get("mechanisms", [])
            for mech_data in mechanisms:
                mech_name = mech_data.get("name", "")
                effectiveness = mech_data.get("effectiveness", 0)
                
                # Normalize mechanism name
                mech_key = mech_name.lower().replace(" ", "_")
                
                if mech_key not in mechanism_boosts:
                    mechanism_boosts[mech_key] = []
                mechanism_boosts[mech_key].append(effectiveness)
    
    # Apply boosts to adjusted scores
    for mech_key, boosts in mechanism_boosts.items():
        if mech_key in adjusted:
            avg_boost = sum(boosts) / len(boosts)
            # Blend: (1-weight) * base + weight * review
            adjusted[mech_key] = (1 - review_weight) * adjusted[mech_key] + review_weight * avg_boost
    
    return adjusted


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 70)
        print("REVIEW INTELLIGENCE SOURCE TEST")
        print("=" * 70)
        
        # Test with different contexts
        test_cases = [
            {"brand": "Apple", "category": "Electronics", "subcategory": "Smartphones"},
            {"brand": "Nike", "category": "Sports", "state": "California"},
            {"category": "Beauty", "subcategory": "Skincare"},
            {"brand": "Tesla", "state": "Texas"},
        ]
        
        for case in test_cases:
            print(f"\n{'-' * 50}")
            print(f"Context: {case}")
            
            context = build_review_context(**case)
            evidence = await get_comprehensive_review_evidence(context)
            
            for source, evi in evidence.items():
                if evi:
                    print(f"\n  {source}:")
                    print(f"    Assessment: {evi.assessment}")
                    print(f"    Value: {evi.assessment_value:.2f}")
                    print(f"    Confidence: {evi.confidence:.2f}")
                    print(f"    Reasoning: {evi.reasoning[:100]}...")
                else:
                    print(f"\n  {source}: (no evidence)")
    
    asyncio.run(test())
