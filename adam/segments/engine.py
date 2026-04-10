"""
Psychological Segment Engine
==============================

Converts graph-inferred ConstructActivationProfiles into targetable
audience segments for DSP/SSP platforms.

This is NOT correlational clustering ("people who buy X also buy Y").
This is inferential segmentation:
    Observable Signals → Psychological Constructs → Segment Definition

Each segment has:
- A psychological profile (which constructs are active and at what levels)
- Predicted mechanism effectiveness (which persuasion approaches will work)
- Creative guidance (how to message this segment)
- Size estimation (expected reach based on construct prevalence)
- Platform-specific targeting parameters

The segments are portable across platforms because they're defined by
psychological constructs (which transfer) rather than behavioral
correlations (which don't transfer across platforms).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=30)
    else:
        return asyncio.run(coro)


# =============================================================================
# SEGMENT MODELS
# =============================================================================

class SegmentConfidence(Enum):
    HIGH = "high"  # Based on validated construct activations
    MODERATE = "moderate"  # Based on partial construct evidence
    EXPLORATORY = "exploratory"  # Zero-shot transfer, needs validation


@dataclass
class MechanismRecommendation:
    """Mechanism recommendation for a segment."""
    mechanism: str
    predicted_effectiveness: float  # 0-1
    confidence: float  # 0-1
    reasoning: str = ""
    creative_implications: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PsychologicalSegment:
    """
    A targetable audience segment defined by psychological constructs.

    Unlike behavioral segments ("visited category X 3+ times"), psychological
    segments are defined by underlying constructs that EXPLAIN behavior
    and transfer across contexts.
    """
    segment_id: str
    name: str
    description: str

    # Psychological definition
    defining_constructs: Dict[str, float] = field(default_factory=dict)
    # e.g. {"prevention_focus": 0.8, "need_for_closure": 0.7, "loss_aversion": 0.75}

    dominant_domain: str = ""  # e.g. "decision_making", "social_influence"
    regulatory_orientation: str = "balanced"  # "promotion", "prevention", "balanced"
    processing_style: str = "moderate"  # "systematic", "heuristic", "moderate"

    # Mechanism effectiveness predictions
    mechanism_recommendations: List[MechanismRecommendation] = field(default_factory=list)
    mechanisms_to_avoid: List[str] = field(default_factory=list)

    # Creative guidance (from ConstructCreativeEngine)
    creative_guidance: Dict[str, Any] = field(default_factory=dict)
    # e.g. {"frame": "loss", "tone": "authoritative", "cta": "Protect Now"}

    # Sizing
    estimated_prevalence: float = 0.0  # 0-1, fraction of population
    estimated_reach: int = 0  # Absolute reach estimate

    # Platform targeting
    platform_targeting: Dict[str, Any] = field(default_factory=dict)
    # Platform-specific params filled by adapters

    # Confidence and provenance
    confidence: SegmentConfidence = SegmentConfidence.MODERATE
    is_zero_shot: bool = False
    construct_evidence_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "name": self.name,
            "description": self.description,
            "defining_constructs": self.defining_constructs,
            "dominant_domain": self.dominant_domain,
            "regulatory_orientation": self.regulatory_orientation,
            "processing_style": self.processing_style,
            "mechanism_recommendations": [
                {
                    "mechanism": mr.mechanism,
                    "predicted_effectiveness": round(mr.predicted_effectiveness, 3),
                    "confidence": round(mr.confidence, 3),
                    "reasoning": mr.reasoning,
                }
                for mr in self.mechanism_recommendations
            ],
            "mechanisms_to_avoid": self.mechanisms_to_avoid,
            "creative_guidance": self.creative_guidance,
            "estimated_prevalence": round(self.estimated_prevalence, 4),
            "estimated_reach": self.estimated_reach,
            "confidence": self.confidence.value,
            "is_zero_shot": self.is_zero_shot,
        }


# =============================================================================
# CANONICAL SEGMENT DEFINITIONS
#
# These are the foundational psychological segments derived from the
# construct registry. Each is defined by a cluster of constructs that
# co-occur based on the causal edges in the graph.
# =============================================================================

CANONICAL_SEGMENTS = {
    "prevention_vigilant": {
        "name": "Prevention-Vigilant",
        "description": "Loss-averse, detail-oriented consumers who need safety and certainty before acting",
        "constructs": {
            "prevention_focus": 0.75, "need_for_closure": 0.70, "loss_aversion": 0.80,
            "risk_sensitivity": 0.75, "conscientiousness": 0.65,
        },
        "regulatory": "prevention",
        "processing": "systematic",
        "good_mechanisms": ["authority", "social_proof", "commitment"],
        "avoid_mechanisms": ["scarcity", "urgency"],
        "creative": {"frame": "loss", "tone": "authoritative", "cta_verbs": ["Protect", "Secure", "Verify"]},
        "prevalence": 0.18,
    },
    "promotion_explorer": {
        "name": "Promotion-Explorer",
        "description": "Novelty-seeking, aspirational consumers open to new experiences and gain-framed messaging",
        "constructs": {
            "promotion_focus": 0.80, "openness": 0.75, "sensation_seeking": 0.70,
            "approach_motivation": 0.75, "curiosity": 0.65,
        },
        "regulatory": "promotion",
        "processing": "heuristic",
        "good_mechanisms": ["identity_construction", "mimetic_desire", "attention_dynamics"],
        "avoid_mechanisms": ["commitment"],
        "creative": {"frame": "gain", "tone": "aspirational", "cta_verbs": ["Discover", "Explore", "Unlock"]},
        "prevalence": 0.15,
    },
    "social_connector": {
        "name": "Social Connector",
        "description": "Community-oriented consumers strongly influenced by social proof and group belonging",
        "constructs": {
            "social_proof_susceptibility": 0.80, "extraversion": 0.70,
            "agreeableness": 0.65, "conformity_need": 0.60,
            "relatedness_need": 0.75,
        },
        "regulatory": "balanced",
        "processing": "heuristic",
        "good_mechanisms": ["social_proof", "mimetic_desire", "unity"],
        "avoid_mechanisms": ["isolation_framing"],
        "creative": {"frame": "gain", "tone": "social_warm", "cta_verbs": ["Join", "Share", "Together"]},
        "prevalence": 0.14,
    },
    "analytical_evaluator": {
        "name": "Analytical Evaluator",
        "description": "Evidence-driven consumers who process deeply and require data-backed claims",
        "constructs": {
            "need_for_cognition": 0.80, "conscientiousness": 0.70,
            "analytical_processing": 0.75, "skepticism": 0.65,
            "cognitive_engagement": 0.70,
        },
        "regulatory": "prevention",
        "processing": "systematic",
        "good_mechanisms": ["authority", "anchoring", "commitment"],
        "avoid_mechanisms": ["scarcity", "social_proof"],
        "creative": {"frame": "neutral", "tone": "evidence_based", "cta_verbs": ["Compare", "Learn", "Evaluate"]},
        "prevalence": 0.12,
    },
    "impulse_experiential": {
        "name": "Impulse-Experiential",
        "description": "Sensation-seeking consumers who respond to urgency, novelty, and immediate gratification",
        "constructs": {
            "arousal_seeking": 0.80, "impulsivity": 0.70,
            "delay_discounting": 0.75, "sensation_seeking": 0.65,
            "present_bias": 0.70,
        },
        "regulatory": "promotion",
        "processing": "heuristic",
        "good_mechanisms": ["scarcity", "attention_dynamics", "embodied_cognition"],
        "avoid_mechanisms": ["commitment", "authority"],
        "creative": {"frame": "gain", "tone": "urgent_exciting", "cta_verbs": ["Get", "Now", "Limited"]},
        "prevalence": 0.10,
    },
    "identity_aspirant": {
        "name": "Identity Aspirant",
        "description": "Status-conscious consumers driven by self-concept and aspirational identity",
        "constructs": {
            "status_sensitivity": 0.75, "identity_salience": 0.80,
            "self_enhancement": 0.70, "narcissism_trait": 0.50,
            "social_comparison": 0.65,
        },
        "regulatory": "promotion",
        "processing": "moderate",
        "good_mechanisms": ["identity_construction", "mimetic_desire", "social_proof"],
        "avoid_mechanisms": ["authority"],
        "creative": {"frame": "gain", "tone": "aspirational_exclusive", "cta_verbs": ["Become", "Elevate", "Exclusive"]},
        "prevalence": 0.11,
    },
    "trust_seeker": {
        "name": "Trust Seeker",
        "description": "Risk-averse consumers who prioritize credibility, reviews, and established brands",
        "constructs": {
            "trust_propensity": 0.80, "uncertainty_intolerance": 0.70,
            "authority_susceptibility": 0.75, "brand_loyalty": 0.65,
            "risk_aversion": 0.75,
        },
        "regulatory": "prevention",
        "processing": "systematic",
        "good_mechanisms": ["authority", "social_proof", "commitment"],
        "avoid_mechanisms": ["scarcity", "novelty"],
        "creative": {"frame": "loss", "tone": "trustworthy", "cta_verbs": ["Trusted", "Proven", "Guaranteed"]},
        "prevalence": 0.13,
    },
    "value_optimizer": {
        "name": "Value Optimizer",
        "description": "Price-sensitive consumers who maximize utility and respond to comparative framing",
        "constructs": {
            "price_sensitivity": 0.80, "anchoring_susceptibility": 0.70,
            "cognitive_engagement": 0.60, "delay_tolerance": 0.65,
            "comparison_tendency": 0.75,
        },
        "regulatory": "prevention",
        "processing": "systematic",
        "good_mechanisms": ["anchoring", "reciprocity", "social_proof"],
        "avoid_mechanisms": ["identity_construction"],
        "creative": {"frame": "mixed", "tone": "value_rational", "cta_verbs": ["Save", "Compare", "Best Value"]},
        "prevalence": 0.07,
    },
}


# =============================================================================
# SEGMENT ENGINE
# =============================================================================

class PsychologicalSegmentEngine:
    """
    Converts ConstructActivationProfiles into PsychologicalSegments.

    Two modes:
    1. Profile → Segment matching: Given a user's construct profile,
       find the best-matching canonical segment(s)
    2. Category → Segment generation: Given a product category,
       generate all relevant segments with sizing estimates

    PRIMARY PATH: Neo4j graph + Thompson posteriors
    FALLBACK: CANONICAL_SEGMENTS hardcoded definitions
    """

    def __init__(self):
        self._construct_registry = None
        self._edge_registry = None
        self._graph_service = None

    def _get_graph_service(self):
        """Lazy-load graph intelligence service."""
        if self._graph_service is None:
            try:
                from adam.services.graph_intelligence import get_graph_intelligence_service
                self._graph_service = get_graph_intelligence_service()
            except ImportError:
                self._graph_service = None
        return self._graph_service

    def _ensure_registries(self):
        if self._construct_registry is None:
            try:
                from adam.dsp.construct_registry import build_construct_registry
                from adam.dsp.edge_registry import build_edge_registry
                self._construct_registry = build_construct_registry()
                self._edge_registry = build_edge_registry()
            except ImportError:
                self._construct_registry = {}
                self._edge_registry = {}

    def match_profile_to_segments(
        self,
        construct_activations: Dict[str, float],
        top_n: int = 3,
    ) -> List[Tuple[PsychologicalSegment, float]]:
        """
        Match a user's construct activation profile to canonical segments.

        Returns: List of (segment, match_score) sorted by match quality.
        """
        matches = []

        for seg_id, seg_def in CANONICAL_SEGMENTS.items():
            score = self._compute_segment_match(
                construct_activations, seg_def["constructs"]
            )
            if score > 0.2:  # Minimum threshold
                segment = self._build_segment(seg_id, seg_def)
                matches.append((segment, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_n]

    def generate_segments_for_category(
        self,
        category: str,
        total_audience: int = 100000,
    ) -> List[PsychologicalSegment]:
        """
        Generate all applicable psychological segments for a product category
        with sizing estimates.

        PRIMARY PATH: Neo4j graph constructs + mechanism effectiveness
        FALLBACK: CANONICAL_SEGMENTS static definitions
        """
        self._ensure_registries()

        # Try graph-backed segment generation first
        try:
            graph_segments = self._generate_graph_backed_segments(category, total_audience)
            if graph_segments:
                logger.info(f"Generated {len(graph_segments)} graph-backed segments for '{category}'")
                return graph_segments
        except Exception as e:
            logger.debug(f"Graph-backed segments unavailable, using fallback: {e}")

        # FALLBACK: static CANONICAL_SEGMENTS
        return self._generate_static_segments(category, total_audience)

    def _generate_graph_backed_segments(
        self,
        category: str,
        total_audience: int,
    ) -> List[PsychologicalSegment]:
        """Generate segments from live Neo4j graph data."""
        gs = self._get_graph_service()
        if gs is None:
            return []

        # Get graph-backed segment data
        graph_segments = _run_async(gs.get_segments_for_category(category))
        if not graph_segments:
            return []

        # Get mechanism effectiveness from graph
        mech_eff = _run_async(gs.get_mechanism_effectiveness(category))

        # Get learned priors for Thompson-adjusted scores
        learned_priors = _run_async(gs.get_learned_priors(category))

        segments = []
        for i, gs_def in enumerate(graph_segments):
            seg_id = f"graph_{gs_def['domain']}_{i}"
            constructs = gs_def.get("constructs", {})

            # Determine regulatory orientation from constructs
            has_prevention = any("prevention" in k for k in constructs)
            has_promotion = any(
                k in ("openness", "approach_motivation", "promotion_focus", "sensation_seeking")
                for k in constructs
            )
            reg_orient = "prevention" if has_prevention and not has_promotion else (
                "promotion" if has_promotion and not has_prevention else "balanced"
            )

            # Processing style from constructs
            has_nfc = any("cognition" in k or "analytical" in k for k in constructs)
            processing = "systematic" if has_nfc else "heuristic"

            # Build mechanism recommendations from graph effectiveness + learned priors
            mechanism_recs = []
            mech_items = gs_def.get("mechanisms", [])
            if not mech_items and mech_eff:
                # Use general mechanism effectiveness
                mech_items = [
                    {"mechanism": m, "score": d["score"], "confidence": d["confidence"],
                     "sample_size": d.get("sample_size", 0)}
                    for m, d in sorted(mech_eff.items(), key=lambda x: x[1]["score"], reverse=True)[:5]
                ]

            for mech_data in mech_items[:5]:
                mech_id = mech_data["mechanism"]
                score = mech_data["score"]
                confidence = mech_data.get("confidence", 0.5)

                # Adjust with Thompson posteriors from learned priors
                score, confidence = self._apply_learned_priors(
                    mech_id, score, confidence, learned_priors
                )

                mechanism_recs.append(MechanismRecommendation(
                    mechanism=mech_id,
                    predicted_effectiveness=min(0.95, score),
                    confidence=confidence,
                    reasoning=(
                        f"Graph-inferred: {gs_def['domain']} domain constructs "
                        f"→ {mech_id} (effect size from Neo4j edges)"
                    ),
                ))

            # If no mechanism recs from graph, fall back to general
            if not mechanism_recs:
                mechanism_recs = [MechanismRecommendation(
                    mechanism="social_proof",
                    predicted_effectiveness=0.5,
                    confidence=0.3,
                    reasoning="Default mechanism -- insufficient graph data",
                )]

            prevalence = gs_def.get("prevalence", 0.1)
            segment = PsychologicalSegment(
                segment_id=seg_id,
                name=gs_def.get("name", f"Segment {i+1}"),
                description=f"Graph-inferred segment from {gs_def['domain']} domain constructs",
                defining_constructs=constructs,
                dominant_domain=gs_def.get("domain", ""),
                regulatory_orientation=reg_orient,
                processing_style=processing,
                mechanism_recommendations=mechanism_recs,
                estimated_prevalence=prevalence,
                estimated_reach=int(total_audience * prevalence),
                confidence=SegmentConfidence.HIGH,
                construct_evidence_count=len(constructs),
            )
            segments.append(segment)

        # Sort by predicted effectiveness
        segments.sort(
            key=lambda s: s.estimated_prevalence * (
                s.mechanism_recommendations[0].predicted_effectiveness
                if s.mechanism_recommendations else 0
            ),
            reverse=True,
        )
        return segments

    def _generate_static_segments(
        self,
        category: str,
        total_audience: int,
    ) -> List[PsychologicalSegment]:
        """Static CANONICAL_SEGMENTS fallback path."""
        segments = []
        for seg_id, seg_def in CANONICAL_SEGMENTS.items():
            segment = self._build_segment(seg_id, seg_def)

            category_relevance = self._estimate_category_relevance(category, seg_def)
            segment.estimated_prevalence = seg_def["prevalence"] * category_relevance
            segment.estimated_reach = int(total_audience * segment.estimated_prevalence)
            segment.mechanism_recommendations = self._generate_mechanism_recommendations(
                seg_def, category
            )
            segments.append(segment)

        segments.sort(
            key=lambda s: s.estimated_prevalence * (
                s.mechanism_recommendations[0].predicted_effectiveness
                if s.mechanism_recommendations else 0
            ),
            reverse=True,
        )
        return segments

    def _apply_learned_priors(
        self,
        mechanism: str,
        score: float,
        confidence: float,
        learned_priors: Dict[str, Any],
    ) -> Tuple[float, float]:
        """Adjust mechanism score with Thompson posteriors from learned data."""
        if not learned_priors:
            return score, confidence

        # Look across all archetypes for this mechanism
        total_samples = 0
        weighted_rate = 0.0
        for _archetype, mechanisms in learned_priors.items():
            if isinstance(mechanisms, dict) and mechanism in mechanisms:
                mech_data = mechanisms[mechanism]
                if isinstance(mech_data, dict):
                    sr = mech_data.get("success_rate", 0)
                    ss = mech_data.get("sample_size", 0)
                    weighted_rate += sr * ss
                    total_samples += ss

        if total_samples > 0:
            empirical_rate = weighted_rate / total_samples
            # Bayesian-ish merge: graph score is prior, empirical is likelihood
            # Weight by sample size confidence
            sample_confidence = min(0.9, total_samples / 50000)
            merged_score = (1.0 - sample_confidence) * score + sample_confidence * empirical_rate
            merged_confidence = min(0.95, confidence + sample_confidence * 0.3)
            return merged_score, merged_confidence

        return score, confidence

    def create_custom_segment(
        self,
        name: str,
        construct_profile: Dict[str, float],
        mechanism_priors: Optional[Dict[str, float]] = None,
    ) -> PsychologicalSegment:
        """
        Create a custom segment from a specific construct profile.

        Used when the standard canonical segments don't fit.
        """
        self._ensure_registries()

        # Determine dominant characteristics
        sorted_constructs = sorted(
            construct_profile.items(), key=lambda x: x[1], reverse=True
        )
        top_constructs = dict(sorted_constructs[:7])

        # Determine regulatory orientation
        promo = construct_profile.get("promotion_focus", 0.5)
        prevent = construct_profile.get("prevention_focus", 0.5)
        reg_orient = "promotion" if promo > prevent + 0.1 else (
            "prevention" if prevent > promo + 0.1 else "balanced"
        )

        # Determine processing style
        nfc = construct_profile.get("need_for_cognition", 0.5)
        processing = "systematic" if nfc > 0.6 else (
            "heuristic" if nfc < 0.4 else "moderate"
        )

        # Generate description
        top_names = [c.replace("_", " ").title() for c, _ in sorted_constructs[:3]]
        description = f"Custom segment driven by {', '.join(top_names)}"

        segment = PsychologicalSegment(
            segment_id=f"custom_{name.lower().replace(' ', '_')}",
            name=name,
            description=description,
            defining_constructs=top_constructs,
            regulatory_orientation=reg_orient,
            processing_style=processing,
            confidence=SegmentConfidence.EXPLORATORY,
        )

        # Add mechanism recommendations from priors
        if mechanism_priors:
            sorted_mechs = sorted(
                mechanism_priors.items(), key=lambda x: x[1], reverse=True
            )
            for mech, score in sorted_mechs[:5]:
                segment.mechanism_recommendations.append(
                    MechanismRecommendation(
                        mechanism=mech,
                        predicted_effectiveness=score,
                        confidence=0.5,
                        reasoning=f"Derived from construct profile ({len(top_constructs)} active constructs)",
                    )
                )

        return segment

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _build_segment(
        self,
        seg_id: str,
        seg_def: Dict[str, Any],
    ) -> PsychologicalSegment:
        """Build a PsychologicalSegment from a canonical definition."""
        return PsychologicalSegment(
            segment_id=seg_id,
            name=seg_def["name"],
            description=seg_def["description"],
            defining_constructs=seg_def["constructs"],
            regulatory_orientation=seg_def.get("regulatory", "balanced"),
            processing_style=seg_def.get("processing", "moderate"),
            creative_guidance=seg_def.get("creative", {}),
            estimated_prevalence=seg_def.get("prevalence", 0.05),
            confidence=SegmentConfidence.HIGH,
            construct_evidence_count=len(seg_def["constructs"]),
            mechanisms_to_avoid=seg_def.get("avoid_mechanisms", []),
        )

    def _compute_segment_match(
        self,
        user_activations: Dict[str, float],
        segment_constructs: Dict[str, float],
    ) -> float:
        """Compute match score between user activations and segment definition."""
        if not segment_constructs:
            return 0.0

        total_match = 0.0
        total_weight = 0.0

        for construct_id, target_level in segment_constructs.items():
            weight = target_level  # Higher target = more important for match
            user_level = user_activations.get(construct_id, 0.5)

            # Match quality: how close is user to target?
            distance = abs(user_level - target_level)
            match = max(0, 1.0 - distance * 2.0)  # 0.5 distance = 0 match

            total_match += match * weight
            total_weight += weight

        return total_match / total_weight if total_weight > 0 else 0.0

    def _estimate_category_relevance(
        self,
        category: str,
        seg_def: Dict[str, Any],
    ) -> float:
        """
        Estimate how relevant a segment is for a given category.

        PRIMARY: Graph CONTEXTUALLY_MODERATES edges
        FALLBACK: Static affinity dictionary
        """
        # Try graph-backed category relevance
        try:
            gs = self._get_graph_service()
            if gs:
                moderation = _run_async(
                    gs.get_mechanism_effectiveness(category)
                )
                if moderation:
                    # If the graph has data for this category, compute relevance
                    # from mechanism score alignment with segment's good mechanisms
                    good_mechs = seg_def.get("good_mechanisms", [])
                    relevance_sum = 0.0
                    count = 0
                    for mech in good_mechs:
                        if mech in moderation:
                            relevance_sum += moderation[mech].get("score", 0.5)
                            count += 1
                    if count > 0:
                        # Scale to multiplier range (0.8 - 1.5)
                        avg_score = relevance_sum / count
                        return 0.8 + avg_score * 0.7
        except Exception:
            pass

        # FALLBACK: static affinity dictionary
        category_affinity = {
            "prevention_vigilant": {
                "finance": 1.5, "insurance": 1.5, "health": 1.3, "security": 1.5,
                "electronics": 1.1,
            },
            "promotion_explorer": {
                "travel": 1.4, "fashion": 1.3, "technology": 1.2, "gaming": 1.3,
                "entertainment": 1.2,
            },
            "social_connector": {
                "fashion": 1.3, "beauty": 1.3, "food": 1.2, "social": 1.5,
                "entertainment": 1.2,
            },
            "analytical_evaluator": {
                "electronics": 1.4, "finance": 1.3, "education": 1.3,
                "software": 1.3,
            },
            "impulse_experiential": {
                "food": 1.3, "entertainment": 1.3, "fashion": 1.2, "gaming": 1.3,
                "beauty": 1.2,
            },
            "identity_aspirant": {
                "luxury": 1.5, "fashion": 1.4, "automotive": 1.3, "beauty": 1.2,
            },
            "trust_seeker": {
                "health": 1.4, "finance": 1.3, "baby": 1.4, "organic": 1.3,
                "supplements": 1.3,
            },
            "value_optimizer": {
                "grocery": 1.3, "household": 1.2, "electronics": 1.2,
                "generic": 1.0,
            },
        }

        seg_name = seg_def.get("name", "").lower().replace("-", "_").replace(" ", "_")
        affinities = category_affinity.get(seg_name, {})

        cat_lower = category.lower()
        for key, multiplier in affinities.items():
            if key in cat_lower:
                return multiplier

        return 1.0  # Default: no adjustment

    def _generate_mechanism_recommendations(
        self,
        seg_def: Dict[str, Any],
        category: str,
    ) -> List[MechanismRecommendation]:
        """
        Generate mechanism recommendations for a segment.

        PRIMARY: Graph EMPIRICALLY_EFFECTIVE edges + Thompson posteriors
        FALLBACK: Static rank-based effectiveness
        """
        # Try graph-backed mechanism scoring
        try:
            gs = self._get_graph_service()
            if gs:
                mech_eff = _run_async(gs.get_mechanism_effectiveness(category))
                learned_priors = _run_async(gs.get_learned_priors(category))
                good_mechs = seg_def.get("good_mechanisms", [])

                if mech_eff:
                    recommendations = []
                    for mech in good_mechs:
                        if mech in mech_eff:
                            data = mech_eff[mech]
                            score = data["score"]
                            confidence = data["confidence"]

                            # Apply learned priors
                            score, confidence = self._apply_learned_priors(
                                mech, score, confidence, learned_priors
                            )

                            recommendations.append(MechanismRecommendation(
                                mechanism=mech,
                                predicted_effectiveness=min(0.95, score),
                                confidence=confidence,
                                reasoning=(
                                    f"Graph-empirical: {mech} effectiveness {score:.0%} "
                                    f"for '{seg_def['name']}' (sample={data.get('sample_size', 0)})"
                                ),
                                creative_implications=seg_def.get("creative", {}),
                            ))
                        else:
                            # Mechanism not in graph -- use base estimate
                            base_eff = 0.5
                            score, confidence = self._apply_learned_priors(
                                mech, base_eff, 0.3, learned_priors
                            )
                            recommendations.append(MechanismRecommendation(
                                mechanism=mech,
                                predicted_effectiveness=min(0.95, score),
                                confidence=confidence,
                                reasoning=f"Learned prior for {mech} (not in category graph edges)",
                                creative_implications=seg_def.get("creative", {}),
                            ))

                    if recommendations:
                        recommendations.sort(key=lambda r: r.predicted_effectiveness, reverse=True)
                        return recommendations
        except Exception as e:
            logger.debug(f"Graph mechanism recommendations failed: {e}")

        # FALLBACK: static rank-based effectiveness
        recommendations = []
        good_mechs = seg_def.get("good_mechanisms", [])

        for i, mech in enumerate(good_mechs):
            base_eff = 0.8 - i * 0.1
            cat_boost = self._get_category_mechanism_boost(category, mech)
            predicted = min(0.95, base_eff + cat_boost)

            recommendations.append(MechanismRecommendation(
                mechanism=mech,
                predicted_effectiveness=predicted,
                confidence=0.7 if i == 0 else 0.5,
                reasoning=f"Segment '{seg_def['name']}' has high {seg_def.get('regulatory', 'balanced')} "
                          f"orientation → {mech} is empirically effective",
                creative_implications=seg_def.get("creative", {}),
            ))

        return recommendations

    def _get_category_mechanism_boost(self, category: str, mechanism: str) -> float:
        """Get category-specific mechanism effectiveness boost (static fallback)."""
        boosts = {
            ("finance", "authority"): 0.1,
            ("finance", "social_proof"): 0.05,
            ("fashion", "social_proof"): 0.1,
            ("fashion", "identity_construction"): 0.1,
            ("electronics", "authority"): 0.1,
            ("electronics", "anchoring"): 0.08,
            ("food", "social_proof"): 0.05,
            ("health", "authority"): 0.12,
            ("luxury", "identity_construction"): 0.12,
            ("luxury", "scarcity"): 0.08,
        }
        cat_lower = category.lower()
        for (cat, mech), boost in boosts.items():
            if cat in cat_lower and mech == mechanism:
                return boost
        return 0.0


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[PsychologicalSegmentEngine] = None


def get_segment_engine() -> PsychologicalSegmentEngine:
    """Get singleton segment engine."""
    global _engine
    if _engine is None:
        _engine = PsychologicalSegmentEngine()
    return _engine
