"""
Creative Pattern Extractor (Layer 2)
======================================

Product descriptions in the corpus are millions of real-world "ads"
with verified purchase outcomes. This is the world's largest natural
A/B test of advertising copy.

This service extracts **structural patterns** — not literal copy —
from product descriptions that successfully converted specific
psychological profiles. These patterns become structured constraints
for Claude's copy generation.

Query interface:
    Input:  category, target psychological profile, desired mechanism, platform
    Output: CreativeConstraints with ranked patterns, framing guidance,
            emotional register, mechanism deployment style, resonance templates

The patterns are weighted by helpful-vote signal: creative patterns
appearing in product descriptions whose reviews received high helpful
votes are double-validated (converted original buyer + influenced
subsequent buyers).
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import Any, Dict, List, Optional

from adam.fusion.models import (
    ConfidenceLevel,
    CreativeConstraints,
    CreativePattern,
    PersuasionFraming,
    PlatformID,
    PriorConfidence,
    PriorSourceType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ARCHETYPE → FRAMING MAPPINGS (from corpus analysis)
# =============================================================================

# These mappings encode patterns discovered from the billion-review corpus:
# which framing works for which psychological profiles

ARCHETYPE_FRAMING_PATTERNS: Dict[str, PersuasionFraming] = {
    "analyst": PersuasionFraming(
        regulatory_focus="prevention",
        construal_level="concrete",
        emotional_register=["trust", "relief", "confidence"],
        mechanism_deployment=["authority", "commitment", "social_proof"],
        implicit_drivers=["risk_mitigation", "optimization", "control"],
        decision_stage="consideration",
        advertising_style="rational",
    ),
    "explorer": PersuasionFraming(
        regulatory_focus="promotion",
        construal_level="abstract",
        emotional_register=["excitement", "curiosity", "wonder"],
        mechanism_deployment=["scarcity", "identity_construction", "storytelling"],
        implicit_drivers=["novelty_seeking", "status_signaling", "self_expression"],
        decision_stage="discovery",
        advertising_style="aspirational",
    ),
    "guardian": PersuasionFraming(
        regulatory_focus="prevention",
        construal_level="concrete",
        emotional_register=["trust", "security", "belonging"],
        mechanism_deployment=["authority", "reciprocity", "unity"],
        implicit_drivers=["loss_aversion", "family_protection", "reliability"],
        decision_stage="consideration",
        advertising_style="emotional",
    ),
    "connector": PersuasionFraming(
        regulatory_focus="promotion",
        construal_level="mixed",
        emotional_register=["belonging", "joy", "pride"],
        mechanism_deployment=["social_proof", "liking", "unity"],
        implicit_drivers=["social_validation", "identity_affirmation", "community"],
        decision_stage="intent",
        advertising_style="emotional",
    ),
    "achiever": PersuasionFraming(
        regulatory_focus="promotion",
        construal_level="abstract",
        emotional_register=["pride", "ambition", "excitement"],
        mechanism_deployment=["authority", "scarcity", "commitment"],
        implicit_drivers=["status_signaling", "achievement", "competitive_edge"],
        decision_stage="intent",
        advertising_style="aspirational",
    ),
    "pragmatist": PersuasionFraming(
        regulatory_focus="balanced",
        construal_level="concrete",
        emotional_register=["relief", "trust", "satisfaction"],
        mechanism_deployment=["reciprocity", "commitment", "social_proof"],
        implicit_drivers=["value_optimization", "efficiency", "practical_benefit"],
        decision_stage="conversion",
        advertising_style="direct_response",
    ),
}

# Category → language register tendencies (from corpus)
CATEGORY_LANGUAGE_REGISTERS: Dict[str, str] = {
    "Electronics": "technical",
    "Beauty_and_Personal_Care": "aspirational",
    "Books": "narrative",
    "Clothing_Shoes_and_Jewelry": "aspirational",
    "Home_and_Kitchen": "casual",
    "Health_and_Household": "authoritative",
    "Toys_and_Games": "casual",
    "Sports_and_Outdoors": "aspirational",
    "Tools_and_Home_Improvement": "technical",
    "Grocery_and_Gourmet_Food": "casual",
    "Baby_Products": "authoritative",
    "Automotive": "technical",
    "Pet_Supplies": "casual",
    "Office_Products": "technical",
    "Industrial_and_Scientific": "technical",
    "Digital_Music": "narrative",
    "Software": "technical",
    "Arts_Crafts_and_Sewing": "narrative",
}


class CreativePatternExtractor:
    """
    Extracts proven creative patterns from the corpus.

    This is the interface from the copy generation engine to corpus
    intelligence. Every ad copy generation should query this service
    for empirically-grounded creative constraints.
    """

    def __init__(self):
        self._priors_data: Optional[Dict[str, Any]] = None
        self._graph_service = None
        self._prior_extraction_service = None

    def _load_priors(self) -> Dict[str, Any]:
        """Load merged priors (cached)."""
        if self._priors_data is not None:
            return self._priors_data

        try:
            from adam.intelligence.unified_intelligence_service import get_unified_intelligence_service
            svc = get_unified_intelligence_service()
            raw = svc._load_layer1_priors()
            if raw:
                self._priors_data = raw
                return self._priors_data
        except Exception:
            pass

        logger.warning("UnifiedIntelligenceService unavailable; loading priors from file")
        priors_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "learning", "ingestion_merged_priors.json",
        )
        if not os.path.exists(priors_path):
            self._priors_data = {}
            return self._priors_data

        try:
            with open(priors_path) as f:
                self._priors_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load priors: {e}")
            self._priors_data = {}
        return self._priors_data

    def _get_graph_service(self):
        """Lazy-load graph service."""
        if self._graph_service is None:
            from adam.services.graph_intelligence import get_graph_intelligence_service
            self._graph_service = get_graph_intelligence_service()
        return self._graph_service

    def _get_prior_service(self):
        """Lazy-load prior extraction service."""
        if self._prior_extraction_service is None:
            from adam.fusion.prior_extraction import get_prior_extraction_service
            self._prior_extraction_service = get_prior_extraction_service()
        return self._prior_extraction_service

    # =========================================================================
    # PRIMARY EXTRACTION METHOD
    # =========================================================================

    def extract_creative_constraints(
        self,
        category: str,
        target_archetype: Optional[str] = None,
        target_trait_profile: Optional[Dict[str, float]] = None,
        target_mechanism: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> CreativeConstraints:
        """
        Extract corpus-backed creative constraints.

        Args:
            category: Product category
            target_archetype: Target archetype (e.g., "analyst", "explorer")
            target_trait_profile: Big Five scores {trait: 0-1}
            target_mechanism: Desired primary mechanism
            platform: Target platform (stackadapt, audioboom, iheart)

        Returns:
            CreativeConstraints with ranked patterns and guidance
        """
        platform_id = None
        if platform:
            try:
                platform_id = PlatformID(platform.lower())
            except ValueError:
                pass

        # --- Step 1: Get mechanism effectiveness from corpus ---
        prior_svc = self._get_prior_service()
        corpus_prior = prior_svc.extract_prior(
            category=category,
            archetype=target_archetype,
            trait_profile=target_trait_profile,
            target_mechanism=target_mechanism,
        )

        # --- Step 2: Build framing from archetype patterns ---
        framing = self._determine_framing(
            target_archetype, target_trait_profile, category
        )

        # --- Step 3: Extract creative patterns from corpus data ---
        patterns = self._extract_patterns_from_corpus(
            category=category,
            archetype=target_archetype,
            framing=framing,
            mechanism_priors=corpus_prior.mechanism_priors,
        )

        # --- Step 4: Get resonance templates from graph ---
        resonance_templates = self._get_resonance_templates(
            category=category,
            archetype=target_archetype,
            mechanism=target_mechanism,
        )

        # --- Step 5: Apply platform-specific adjustments ---
        if platform_id:
            self._apply_platform_adjustments(framing, platform_id)

        # --- Step 6: Aggregate recommended mechanisms ---
        recommended_mechs = [
            mp.mechanism for mp in corpus_prior.ranked_mechanisms(5)
        ]

        recommended_emotions = list(set(
            framing.emotional_register[:3]
            if framing else []
        ))

        # --- Build result ---
        overall_conf = corpus_prior.overall_confidence.confidence_score
        return CreativeConstraints(
            category=category,
            target_profile=target_trait_profile,
            platform=platform_id,
            patterns=patterns,
            recommended_framing=framing,
            recommended_mechanisms=recommended_mechs,
            recommended_emotional_register=recommended_emotions,
            resonance_templates=resonance_templates,
            overall_confidence=overall_conf,
        )

    # =========================================================================
    # FRAMING DETERMINATION
    # =========================================================================

    def _determine_framing(
        self,
        archetype: Optional[str],
        trait_profile: Optional[Dict[str, float]],
        category: str,
    ) -> PersuasionFraming:
        """Determine optimal framing from archetype + traits + category."""

        # 1. Start with archetype-based framing if available
        if archetype and archetype.lower() in ARCHETYPE_FRAMING_PATTERNS:
            base_framing = ARCHETYPE_FRAMING_PATTERNS[archetype.lower()]
        elif trait_profile:
            # Infer framing from trait profile
            base_framing = self._infer_framing_from_traits(trait_profile)
        else:
            base_framing = PersuasionFraming()

        # 2. Adjust with category-specific data
        data = self._load_priors()
        dim_dists = data.get("dimension_distributions", {})

        # Check for regulatory focus patterns in this category
        reg_focus = dim_dists.get("regulatory_focus_patterns", {})
        if reg_focus:
            cat_norm = category.replace(" ", "_").lower()
            for key, val in reg_focus.items():
                if cat_norm in key.lower():
                    if isinstance(val, dict):
                        promo = val.get("promotion", 0.5)
                        prev = val.get("prevention", 0.5)
                        if promo > prev + 0.1:
                            base_framing.regulatory_focus = "promotion"
                        elif prev > promo + 0.1:
                            base_framing.regulatory_focus = "prevention"

        # 3. Try enriching with graph creative implications
        try:
            gs = self._get_graph_service()
            constructs = gs.sync_get_category_constructs(category, limit=5)
            if constructs:
                construct_ids = [c["construct_id"] for c in constructs[:3]]
                implications = gs.sync_get_creative_implications(construct_ids)
                if implications:
                    self._enrich_framing_from_graph(base_framing, implications)
        except Exception as e:
            logger.debug(f"Graph framing enrichment skipped: {e}")

        return base_framing

    def _infer_framing_from_traits(
        self, trait_profile: Dict[str, float]
    ) -> PersuasionFraming:
        """Infer framing from Big Five trait profile."""
        openness = trait_profile.get("openness", 0.5)
        conscientiousness = trait_profile.get("conscientiousness", 0.5)
        extraversion = trait_profile.get("extraversion", 0.5)
        agreeableness = trait_profile.get("agreeableness", 0.5)
        neuroticism = trait_profile.get("neuroticism", 0.5)

        # Regulatory focus
        if extraversion > 0.6 and openness > 0.6:
            reg_focus = "promotion"
        elif conscientiousness > 0.6 and neuroticism > 0.5:
            reg_focus = "prevention"
        else:
            reg_focus = "balanced"

        # Construal level
        if openness > 0.6:
            construal = "abstract"
        elif conscientiousness > 0.6:
            construal = "concrete"
        else:
            construal = "mixed"

        # Emotional register
        emotions = []
        if extraversion > 0.6:
            emotions.extend(["excitement", "joy"])
        if agreeableness > 0.6:
            emotions.extend(["belonging", "trust"])
        if neuroticism > 0.6:
            emotions.extend(["security", "relief"])
        if openness > 0.6:
            emotions.extend(["curiosity", "wonder"])
        if not emotions:
            emotions = ["trust", "satisfaction"]

        # Mechanisms (from Oyibo et al. 2017 Big Five → Cialdini mapping)
        mechanisms = []
        if conscientiousness > 0.6:
            mechanisms.extend(["commitment", "reciprocity"])
        if agreeableness > 0.6:
            mechanisms.extend(["authority", "liking"])
        if extraversion > 0.6:
            mechanisms.extend(["social_proof", "unity"])
        if openness < 0.4:
            mechanisms.extend(["authority", "social_proof"])
        if not mechanisms:
            mechanisms = ["social_proof", "reciprocity"]

        return PersuasionFraming(
            regulatory_focus=reg_focus,
            construal_level=construal,
            emotional_register=emotions[:4],
            mechanism_deployment=mechanisms[:4],
            decision_stage="consideration",
            advertising_style="emotional" if extraversion > 0.5 else "rational",
        )

    def _enrich_framing_from_graph(
        self, framing: PersuasionFraming, implications: Dict[str, Any]
    ) -> None:
        """Enrich framing with graph-derived creative implications."""
        for cid, impl_data in implications.items():
            construct_data = impl_data.get("construct", {})
            if not construct_data:
                continue

            creative = construct_data.get("creative_implications", {})
            if isinstance(creative, str):
                try:
                    creative = json.loads(creative)
                except (json.JSONDecodeError, TypeError):
                    continue

            if not isinstance(creative, dict):
                continue

            # Merge message_frame into framing
            msg_frame = creative.get("message_frame")
            if msg_frame:
                if "gain" in msg_frame.lower():
                    framing.regulatory_focus = "promotion"
                elif "loss" in msg_frame.lower() or "prevent" in msg_frame.lower():
                    framing.regulatory_focus = "prevention"

            # Merge style into advertising style
            style = creative.get("style")
            if style and style not in framing.advertising_style:
                framing.advertising_style = style

    def _apply_platform_adjustments(
        self, framing: PersuasionFraming, platform: PlatformID
    ) -> None:
        """Adjust framing for platform-specific constraints."""
        if platform == PlatformID.AUDIOBOOM:
            # Podcast: conversational, narrative, longer form
            framing.advertising_style = "emotional"
            if "storytelling" not in framing.mechanism_deployment:
                framing.mechanism_deployment.append("storytelling")
            framing.construal_level = "mixed"  # Balance abstract/concrete for audio

        elif platform == PlatformID.STACKADAPT:
            # Programmatic: concise, direct, visual-oriented
            framing.construal_level = "concrete"
            if framing.decision_stage == "discovery":
                framing.advertising_style = "aspirational"
            else:
                framing.advertising_style = "direct_response"

        elif platform == PlatformID.IHEART:
            # Streaming audio: emotional, memorable, repetition-friendly
            framing.advertising_style = "emotional"
            if "storytelling" not in framing.mechanism_deployment:
                framing.mechanism_deployment.append("storytelling")

    # =========================================================================
    # PATTERN EXTRACTION FROM CORPUS
    # =========================================================================

    def _extract_patterns_from_corpus(
        self,
        category: str,
        archetype: Optional[str],
        framing: PersuasionFraming,
        mechanism_priors: list,
    ) -> List[CreativePattern]:
        """Build ranked creative patterns from corpus data."""
        patterns = []
        data = self._load_priors()

        # Get product ad profile aggregates for this category
        product_profiles = data.get("product_ad_profile_aggregates", {})
        category_profiles = data.get("category_product_profiles", {})

        cat_norm = category.replace(" ", "_")
        language_register = CATEGORY_LANGUAGE_REGISTERS.get(cat_norm, "neutral")

        # Build a primary pattern from the corpus prior + framing
        for i, mp in enumerate(mechanism_priors[:5]):
            # Build key appeals from mechanism
            key_appeals = self._mechanism_to_appeals(mp.mechanism)

            pattern = CreativePattern(
                pattern_id=f"corpus_{cat_norm}_{mp.mechanism}_{i}",
                category=category,
                target_archetype=archetype,
                framing=PersuasionFraming(
                    regulatory_focus=framing.regulatory_focus,
                    construal_level=framing.construal_level,
                    emotional_register=framing.emotional_register[:3],
                    mechanism_deployment=[mp.mechanism],
                    implicit_drivers=framing.implicit_drivers[:2],
                    decision_stage=framing.decision_stage,
                    advertising_style=framing.advertising_style,
                ),
                purchase_confirmation_rate=mp.effect_size,
                evidence_count=mp.confidence.evidence_count,
                helpful_vote_boost=mp.confidence.helpful_vote_weight,
                confidence=mp.confidence,
                language_register=language_register,
                key_appeals=key_appeals,
            )
            patterns.append(pattern)

        # Enrich with product profile data if available
        self._enrich_with_product_profiles(
            patterns, product_profiles, category_profiles, cat_norm
        )

        return patterns

    def _mechanism_to_appeals(self, mechanism: str) -> List[str]:
        """Map mechanism to key appeals for creative."""
        appeal_map = {
            "social_proof": ["popularity", "peer_validation", "trending"],
            "scarcity": ["limited_time", "exclusivity", "urgency"],
            "authority": ["expert_endorsement", "credentials", "proven_results"],
            "commitment": ["consistency", "follow_through", "values_alignment"],
            "reciprocity": ["free_value", "generosity", "fair_exchange"],
            "liking": ["similarity", "attractiveness", "familiarity"],
            "unity": ["shared_identity", "community", "belonging"],
            "fomo": ["missing_out", "social_momentum", "time_sensitivity"],
            "identity_construction": ["self_expression", "aspiration", "transformation"],
            "storytelling": ["narrative", "journey", "emotional_arc"],
            "fear_appeal": ["protection", "safety", "risk_awareness"],
            "humor": ["entertainment", "memorable", "disarming"],
            "mimetic_desire": ["aspiration", "emulation", "social_status"],
            "attention_dynamics": ["curiosity_gap", "pattern_interrupt", "surprise"],
            "embodied_cognition": ["sensory", "physical_experience", "immersion"],
        }
        return appeal_map.get(mechanism, ["benefit", "value"])

    def _enrich_with_product_profiles(
        self,
        patterns: List[CreativePattern],
        product_profiles: Dict,
        category_profiles: Dict,
        cat_norm: str,
    ) -> None:
        """Enrich patterns with product profile aggregate data."""
        # Look for category in product profiles
        cat_data = None
        for key, val in product_profiles.items():
            if cat_norm.lower() in key.lower():
                cat_data = val
                break

        if not cat_data and category_profiles:
            for key, val in category_profiles.items():
                if cat_norm.lower() in key.lower():
                    cat_data = val
                    break

        if not cat_data or not isinstance(cat_data, dict):
            return

        # Extract Cialdini scores from product profiles
        cialdini = cat_data.get("cialdini_scores", {})
        if isinstance(cialdini, dict):
            # Find dominant Cialdini principle
            dominant = max(cialdini, key=cialdini.get) if cialdini else None
            if dominant and patterns:
                # Ensure dominant mechanism is in top pattern
                top_pattern = patterns[0]
                if dominant not in top_pattern.framing.mechanism_deployment:
                    top_pattern.framing.mechanism_deployment.insert(0, dominant)
                    top_pattern.framing.mechanism_deployment = (
                        top_pattern.framing.mechanism_deployment[:4]
                    )

    # =========================================================================
    # RESONANCE TEMPLATES FROM GRAPH
    # =========================================================================

    def _get_resonance_templates(
        self,
        category: str,
        archetype: Optional[str],
        mechanism: Optional[str],
    ) -> List[str]:
        """
        Get high-helpful-vote persuasive templates from the graph.

        These are language patterns that have been peer-validated through
        helpful votes — not just converted the original buyer but influenced
        subsequent buyers.
        """
        templates = []

        # First try the PersuasionResonanceIndex (no async needed)
        try:
            from adam.fusion.resonance_index import get_persuasion_resonance_index
            resonance_idx = get_persuasion_resonance_index()
            patterns = resonance_idx.get_resonance_patterns_for_copy(
                category=category,
                archetype=archetype,
                mechanism=mechanism,
            )
            if patterns:
                return patterns[:5]
        except Exception as e:
            logger.debug(f"Resonance index query skipped: {e}")

        # Fallback: query Neo4j directly via persistent loop
        try:
            from adam.infrastructure.neo4j.pattern_persistence import (
                get_pattern_persistence,
            )
            from adam.services.graph_intelligence import _run_async

            if archetype:
                persistence = get_pattern_persistence()

                async def _fetch_templates():
                    return await persistence.get_best_templates_for_archetype(
                        archetype=archetype,
                        mechanism=mechanism,
                        limit=5,
                    )

                result = _run_async(_fetch_templates())
                if result:
                    for tmpl in result:
                        if isinstance(tmpl, dict):
                            pattern = tmpl.get("pattern", "")
                            if pattern:
                                templates.append(pattern)
                        elif hasattr(tmpl, "pattern"):
                            templates.append(tmpl.pattern)

        except Exception as e:
            logger.debug(f"Resonance template fetch skipped: {e}")

        return templates[:5]

    # =========================================================================
    # BATCH EXTRACTION (for advertiser onboarding)
    # =========================================================================

    def extract_all_patterns_for_category(
        self,
        category: str,
    ) -> Dict[str, CreativeConstraints]:
        """
        Extract creative constraints for ALL archetypes in a category.

        Used during advertiser onboarding to pre-generate creative
        guidance for all audience segments.

        Returns: {archetype: CreativeConstraints}
        """
        archetypes = list(ARCHETYPE_FRAMING_PATTERNS.keys())
        results = {}

        for arch in archetypes:
            results[arch] = self.extract_creative_constraints(
                category=category,
                target_archetype=arch,
            )

        return results


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[CreativePatternExtractor] = None


def get_creative_pattern_extractor() -> CreativePatternExtractor:
    """Get singleton CreativePatternExtractor."""
    global _service
    if _service is None:
        _service = CreativePatternExtractor()
    return _service
