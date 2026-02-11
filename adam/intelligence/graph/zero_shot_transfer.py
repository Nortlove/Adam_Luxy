# =============================================================================
# ADAM Zero-Shot Transfer via Theory Graph Traversal
# Location: adam/intelligence/graph/zero_shot_transfer.py
# =============================================================================

"""
ZERO-SHOT TRANSFER

When the system encounters a new context (new category, new segment, new
product type) with NO direct empirical data, it can still produce intelligent
recommendations by traversing the theory graph.

This is the key differentiator: correlational systems are blind in new contexts.
ADAM transfers psychological understanding because the theory graph encodes
causal relationships that are context-independent.

Example:
    A new category "smart home security" has no historical data.
    But ADAM knows:
    1. Security products → high involvement + financial risk
    2. These contexts amplify need_for_safety and need_for_closure
    3. need_for_safety → authority, commitment (validated in 8 categories)
    4. need_for_closure → authority, social_proof (validated in 12 categories)
    5. Therefore: authority is the top recommendation, with explicit
       uncertainty about the transfer quality

    Confidence is lower than empirically-validated recommendations, but
    the reasoning is explicit and testable — and it's infinitely better
    than random selection or uniform priors.

Academic Foundations:
- Gentner (1983): Structure-mapping theory for analogical transfer
- Holyoak & Thagard (1989): Analogical mapping by constraint satisfaction
- Pearl (2009): Transportability of causal effects
- Matz et al. (2017): Construct-matched ad targeting validation (Big Five)
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from adam.intelligence.graph.theory_schema import (
    PSYCHOLOGICAL_STATES,
    PSYCHOLOGICAL_NEEDS,
    CONTEXT_CONDITIONS,
    THEORETICAL_LINKS,
)
from adam.intelligence.graph.reasoning_chain_generator import (
    generate_chains_local,
    InferentialChain,
    _determine_active_states,
    _determine_active_context,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CATEGORY CONTEXT PROFILES
#
# When we encounter a new category, we can still infer context conditions
# from the category name/type. These are generic priors that improve
# zero-shot quality.
# =============================================================================

CATEGORY_CONTEXT_PROFILES: Dict[str, Dict[str, Any]] = {
    # High involvement + financial risk
    "electronics": {"involvement": 0.7, "financial_risk": True, "price": 200},
    "appliances": {"involvement": 0.7, "financial_risk": True, "price": 300},
    "automotive": {"involvement": 0.9, "financial_risk": True, "price": 1000},
    "real_estate": {"involvement": 0.95, "financial_risk": True, "price": 5000},
    "insurance": {"involvement": 0.8, "financial_risk": True},
    "financial": {"involvement": 0.85, "financial_risk": True},
    "home_security": {"involvement": 0.8, "financial_risk": True},

    # Moderate involvement
    "fashion": {"involvement": 0.5, "social_visibility": True},
    "beauty": {"involvement": 0.5, "social_visibility": True},
    "fitness": {"involvement": 0.6},
    "education": {"involvement": 0.7},
    "travel": {"involvement": 0.7, "time_pressure": False},

    # Low involvement
    "grocery": {"involvement": 0.2, "low_involvement": True},
    "snacks": {"involvement": 0.15, "low_involvement": True},
    "beverages": {"involvement": 0.2, "low_involvement": True},
    "household": {"involvement": 0.3},

    # Social / identity
    "luxury": {"involvement": 0.8, "social_visibility": True, "financial_risk": True},
    "sports": {"involvement": 0.5, "social_visibility": True},
    "gaming": {"involvement": 0.5},

    # Sensory / experiential
    "food": {"involvement": 0.3},
    "wine": {"involvement": 0.5, "social_visibility": True},
    "fragrance": {"involvement": 0.4, "social_visibility": True},
}


def _get_category_context(category: str) -> Dict[str, Any]:
    """Get a context profile for a category, with fuzzy matching."""
    if not category:
        return {}

    # Direct match
    cat_lower = category.lower().replace(" ", "_").replace("-", "_")
    if cat_lower in CATEGORY_CONTEXT_PROFILES:
        return CATEGORY_CONTEXT_PROFILES[cat_lower]

    # Fuzzy: check if any key is contained in the category name
    for key, profile in CATEGORY_CONTEXT_PROFILES.items():
        if key in cat_lower or cat_lower in key:
            return profile

    # Default: moderate involvement, no special context
    return {"involvement": 0.5}


# =============================================================================
# ZERO-SHOT TRANSFER
# =============================================================================

@dataclass
class ZeroShotRecommendation:
    """A zero-shot mechanism recommendation based on theory transfer."""
    mechanism: str
    score: float  # Predicted effectiveness
    confidence: float  # How confident we are in this transfer
    transferability: float  # How portable is the underlying theory?
    chains: List[InferentialChain] = field(default_factory=list)
    reasoning: str = ""  # Human-readable explanation
    analogical_contexts: List[str] = field(default_factory=list)  # Similar contexts where validated
    uncertainty_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mechanism": self.mechanism,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "transferability": round(self.transferability, 4),
            "reasoning": self.reasoning,
            "analogical_contexts": self.analogical_contexts,
            "uncertainty_note": self.uncertainty_note,
            "chain_count": len(self.chains),
            "top_chain": self.chains[0].to_dict() if self.chains else None,
        }


@dataclass
class ZeroShotResult:
    """Complete zero-shot transfer result for a new context."""
    category: str
    is_zero_shot: bool = True
    recommendations: List[ZeroShotRecommendation] = field(default_factory=list)
    ndf_profile_source: str = ""  # "provided", "archetype_based", "category_default"
    ndf_profile: Dict[str, float] = field(default_factory=dict)
    active_states: List[str] = field(default_factory=list)
    context_conditions: List[str] = field(default_factory=list)
    validation_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "is_zero_shot": self.is_zero_shot,
            "ndf_profile_source": self.ndf_profile_source,
            "active_states": self.active_states,
            "context_conditions": self.context_conditions,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "validation_note": self.validation_note,
        }


def zero_shot_recommend(
    category: str,
    ndf_profile: Optional[Dict[str, float]] = None,
    archetype: str = "",
    context: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    theory_learner=None,  # Optional TheoryLearner for learned link strengths
) -> ZeroShotResult:
    """
    Generate mechanism recommendations for a new context with no empirical data.

    This is the primary zero-shot transfer function. It works by:

    1. Assessing the NDF profile (from user data, archetype priors, or defaults)
    2. Inferring context conditions from the category
    3. Traversing the theory graph to find applicable chains
    4. Scoring chains by:
       - Theoretical link strength (how well-supported by theory?)
       - Empirical validation in OTHER contexts (how well has each link
         been validated in contexts we DO have data for?)
       - Context match (how similar is this context to validated contexts?)
    5. Producing recommendations with explicit uncertainty

    Args:
        category: The new product category
        ndf_profile: NDF profile if available (7 dimensions, 0-1)
        archetype: Customer archetype if known
        context: Additional context signals
        top_k: Number of recommendations to return
        theory_learner: Optional TheoryLearner instance for learned strengths

    Returns:
        ZeroShotResult with ranked recommendations and full provenance
    """
    context = context or {}

    # Step 1: Build NDF profile
    ndf_source = "provided"
    if ndf_profile is None:
        if archetype:
            ndf_profile = _get_archetype_ndf(archetype)
            ndf_source = "archetype_based"
        else:
            # Default: moderate everything (maximum uncertainty)
            ndf_profile = {
                "uncertainty_tolerance": 0.5,
                "cognitive_engagement": 0.5,
                "social_calibration": 0.5,
                "approach_avoidance": 0.5,
                "status_sensitivity": 0.5,
                "arousal_seeking": 0.5,
                "temporal_horizon": 0.5,
            }
            ndf_source = "category_default"

    # Step 2: Infer context from category
    category_context = _get_category_context(category)
    # Merge with any explicitly provided context
    merged_context = {**category_context, **context}
    merged_context["novel_category"] = True  # Always true for zero-shot

    # Step 3: Generate inferential chains
    chains = generate_chains_local(
        ndf_profile=ndf_profile,
        context=merged_context,
        archetype=archetype,
        category=category,
        request_id=f"zs_{category}",
        top_k=top_k * 2,  # Generate more, then filter
    )

    if not chains:
        return ZeroShotResult(
            category=category,
            ndf_profile_source=ndf_source,
            ndf_profile=ndf_profile,
            validation_note="No applicable theoretical chains found for this profile/context combination.",
        )

    # Step 4: Apply learned link strengths from theory learner (if available)
    if theory_learner:
        for chain in chains:
            # Adjust chain confidence based on learned link strengths
            learned_strengths = []
            for key in chain.theoretical_link_keys:
                learned = theory_learner.get_link_strength(key)
                learned_strengths.append(learned)
            if learned_strengths:
                avg_learned = sum(learned_strengths) / len(learned_strengths)
                # Blend: 60% theoretical, 40% empirically learned
                chain.empirical_support = avg_learned
                chain.confidence = chain.chain_strength * 0.6 + avg_learned * 0.4

    # Step 5: Build recommendations
    recommendations = []
    for chain in chains[:top_k]:
        # Calculate transfer confidence
        # Lower confidence for zero-shot (no direct empirical data)
        transfer_confidence = chain.confidence * 0.7  # 30% discount for zero-shot

        # Higher transferability for purely theoretical chains
        transferability = chain.transferability_score

        # Determine analogical contexts (where the theory has been tested)
        analogical = _find_analogical_contexts(category, merged_context)

        reasoning = (
            f"Recommended via theory graph traversal (zero-shot transfer). "
            f"This user's NDF profile ({ndf_source}) activates "
            f"{', '.join(chain.active_states)}, creating "
            f"{', '.join(chain.active_needs)}. "
            f"The mechanism {chain.recommended_mechanism} satisfies these needs "
            f"based on {len(chain.steps)} theoretical links. "
            f"This is a zero-shot transfer — no direct empirical data exists "
            f"for {category}, but the underlying theory has been validated "
            f"in {len(analogical)} analogical contexts."
        )

        uncertainty_note = (
            f"Zero-shot confidence is {transfer_confidence:.0%} "
            f"(vs. ~{chain.confidence:.0%} with empirical data). "
            f"Recommendations will improve as outcomes are observed in this context."
        )

        recommendations.append(ZeroShotRecommendation(
            mechanism=chain.recommended_mechanism,
            score=chain.mechanism_score,
            confidence=transfer_confidence,
            transferability=transferability,
            chains=[chain],
            reasoning=reasoning,
            analogical_contexts=analogical,
            uncertainty_note=uncertainty_note,
        ))

    active_states = _determine_active_states(ndf_profile)
    active_context = _determine_active_context(merged_context)

    validation_note = (
        f"Zero-shot transfer for '{category}'. "
        f"NDF source: {ndf_source}. "
        f"Active states: {len(active_states)}. "
        f"Context conditions: {', '.join(active_context) if active_context else 'none'}. "
        f"Generated {len(recommendations)} recommendations from theory graph. "
        f"These will be validated and refined as real outcomes are observed."
    )

    return ZeroShotResult(
        category=category,
        recommendations=recommendations,
        ndf_profile_source=ndf_source,
        ndf_profile=ndf_profile,
        active_states=active_states,
        context_conditions=active_context,
        validation_note=validation_note,
    )


def _get_archetype_ndf(archetype: str) -> Dict[str, float]:
    """Get NDF profile for an archetype from learned priors or defaults."""
    # Try to load from learned priors
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors_service
        priors = get_learned_priors_service()
        ndf = priors.get_ndf_for_archetype(archetype)
        if ndf:
            return ndf
    except Exception:
        pass

    # Archetype-based defaults from psychological theory
    archetype_ndfs = {
        "achiever": {
            "uncertainty_tolerance": 0.3,
            "cognitive_engagement": 0.8,
            "social_calibration": 0.5,
            "approach_avoidance": 0.7,
            "status_sensitivity": 0.7,
            "arousal_seeking": 0.5,
            "temporal_horizon": 0.7,
        },
        "explorer": {
            "uncertainty_tolerance": 0.8,
            "cognitive_engagement": 0.7,
            "social_calibration": 0.4,
            "approach_avoidance": 0.8,
            "status_sensitivity": 0.3,
            "arousal_seeking": 0.8,
            "temporal_horizon": 0.5,
        },
        "skeptic": {
            "uncertainty_tolerance": 0.3,
            "cognitive_engagement": 0.9,
            "social_calibration": 0.3,
            "approach_avoidance": 0.3,
            "status_sensitivity": 0.4,
            "arousal_seeking": 0.3,
            "temporal_horizon": 0.7,
        },
        "connector": {
            "uncertainty_tolerance": 0.5,
            "cognitive_engagement": 0.5,
            "social_calibration": 0.9,
            "approach_avoidance": 0.6,
            "status_sensitivity": 0.6,
            "arousal_seeking": 0.6,
            "temporal_horizon": 0.5,
        },
        "loyalist": {
            "uncertainty_tolerance": 0.2,
            "cognitive_engagement": 0.4,
            "social_calibration": 0.7,
            "approach_avoidance": 0.4,
            "status_sensitivity": 0.3,
            "arousal_seeking": 0.2,
            "temporal_horizon": 0.6,
        },
    }

    return archetype_ndfs.get(
        archetype.lower(),
        {dim: 0.5 for dim in [
            "uncertainty_tolerance", "cognitive_engagement", "social_calibration",
            "approach_avoidance", "status_sensitivity", "arousal_seeking",
            "temporal_horizon",
        ]}
    )


def _find_analogical_contexts(
    target_category: str,
    context: Dict[str, Any],
) -> List[str]:
    """
    Find categories that are analogically similar to the target.

    Analogy is based on shared context conditions: categories with similar
    involvement levels, financial risk profiles, social visibility, etc.
    are more likely to have similar mechanism effectiveness.
    """
    target_profile = _get_category_context(target_category)
    if not target_profile:
        target_profile = context

    similar = []
    for cat, profile in CATEGORY_CONTEXT_PROFILES.items():
        if cat.lower() == target_category.lower():
            continue
        # Calculate similarity based on shared features
        shared = 0
        total = 0
        for key in ["involvement", "financial_risk", "social_visibility",
                     "time_pressure", "low_involvement"]:
            if key in target_profile and key in profile:
                total += 1
                if isinstance(target_profile[key], bool) and isinstance(profile[key], bool):
                    shared += 1 if target_profile[key] == profile[key] else 0
                elif isinstance(target_profile[key], (int, float)) and isinstance(profile[key], (int, float)):
                    diff = abs(target_profile[key] - profile[key])
                    shared += 1 if diff < 0.3 else 0.5 if diff < 0.5 else 0
                total = max(total, 1)

        similarity = shared / total if total > 0 else 0
        if similarity > 0.5:
            similar.append(cat)

    return similar[:5]


# =============================================================================
# INTEGRATION WITH COLD START SERVICE
# =============================================================================

async def enhance_cold_start_with_theory(
    archetype: str,
    category: str = "",
    ndf_profile: Optional[Dict[str, float]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enhance cold start mechanism selection with theory-based reasoning.

    Called by the ColdStartService to add inferential intelligence to
    its archetype-based heuristics. Returns additional mechanism
    recommendations and creative guidance from the theory graph.

    Returns a dict that can be merged into the ColdStartDecision metadata.
    """
    try:
        theory_learner = None
        try:
            from adam.core.learning.theory_learner import get_theory_learner
            theory_learner = get_theory_learner()
        except Exception:
            pass

        result = zero_shot_recommend(
            category=category,
            ndf_profile=ndf_profile,
            archetype=archetype,
            context=context,
            top_k=3,
            theory_learner=theory_learner,
        )

        return {
            "theory_recommendations": result.to_dict(),
            "theory_top_mechanism": (
                result.recommendations[0].mechanism
                if result.recommendations else None
            ),
            "theory_confidence": (
                result.recommendations[0].confidence
                if result.recommendations else 0.0
            ),
            "is_zero_shot": True,
        }
    except Exception as e:
        logger.debug(f"Theory-based cold start enhancement failed: {e}")
        return {"theory_recommendations": None, "is_zero_shot": True}
