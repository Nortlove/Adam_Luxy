"""
Persuasion Resonance Index (Layer 5)
======================================

The helpful vote signal deserves its own architectural treatment because
it represents something unique: **verified peer persuasion with confirmed
purchase influence**.

A review with 500 helpful votes means 500 people found that reviewer's
perspective convincing enough to influence their decision. These reviews
are not just purchase confirmations — they are PEER-VALIDATED PERSUASION
EVENTS.

This layer:
1. Builds ResonanceTemplates as first-class graph entities
2. Computes category × archetype resonance scores
3. Normalizes vote scores by category baseline
4. Integrates with copy generation and host-read briefing
5. Enriches as new helpful vote data is processed

Key principle: A review with 500 helpful votes in a category with an
average of 10 helpful votes per review is an extraordinarily high-signal
persuasion template and should be weighted accordingly.

The resonance templates serve as:
- Confidence multipliers on psychological construct priors
- Seed content for personality-matched copy generation
- Ground truth for mechanism effectiveness calibration
- Persuasion pattern validation for psychological profile inference
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from adam.fusion.models import (
    CategoryResonanceProfile,
    PersuasionFraming,
    PriorSourceType,
    ResonanceTemplate,
)

logger = logging.getLogger(__name__)


class PersuasionResonanceIndex:
    """
    Index of helpful-vote-validated persuasion templates.

    Builds and maintains first-class resonance templates derived from
    high-helpful-vote reviews. These templates represent the structural
    patterns of language, framing, emotional tone, and mechanism usage
    that have been peer-validated as persuasive.
    """

    def __init__(self):
        self._templates: Dict[str, ResonanceTemplate] = {}
        self._category_profiles: Dict[str, CategoryResonanceProfile] = {}
        self._category_avg_votes: Dict[str, float] = {}
        self._loaded = False
        self._graph_service = None

    def _get_graph_service(self):
        if self._graph_service is None:
            from adam.services.graph_intelligence import get_graph_intelligence_service
            self._graph_service = get_graph_intelligence_service()
        return self._graph_service

    # =========================================================================
    # LOADING
    # =========================================================================

    def _ensure_loaded(self) -> None:
        """Load resonance data from multiple sources."""
        if self._loaded:
            return

        self._loaded = True

        # Source 1: High-influence JSONL files from helpful vote processing
        self._load_from_helpful_vote_files()

        # Source 2: Merged priors (product_ad_profile_aggregates)
        self._load_from_merged_priors()

        # Source 3: Neo4j PersuasiveTemplate nodes
        self._load_from_graph()

        total = len(self._templates)
        categories = len(self._category_profiles)
        logger.info(
            f"PersuasionResonanceIndex loaded: {total} templates "
            f"across {categories} category-archetype profiles"
        )

    # Maximum reviews to sample per JSONL file (these can be 900MB+)
    MAX_REVIEWS_PER_FILE = 5000

    def _load_from_helpful_vote_files(self) -> None:
        """
        Load from data/learning/helpful_vote/ JSONL files.

        These files can be very large (900MB+). We sample the top-N
        highest-vote reviews rather than reading the entire file.
        """
        base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "learning", "helpful_vote",
        )
        if not os.path.exists(base_dir):
            return

        for filename in os.listdir(base_dir):
            if not filename.endswith(".jsonl"):
                continue

            # Parse category from filename (e.g., high_influence_Beauty_and_Personal_Care.jsonl)
            category = filename.replace("high_influence_", "").replace(".jsonl", "")

            filepath = os.path.join(base_dir, filename)
            try:
                # Read a bounded sample — first pass collects top-vote reviews
                candidates = []
                with open(filepath) as f:
                    for line_num, line in enumerate(f):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            review = json.loads(line)
                            votes = review.get("helpful_votes", 0)
                            candidates.append((votes, review))

                            # Keep bounded — retain only highest-vote reviews
                            if len(candidates) > self.MAX_REVIEWS_PER_FILE * 2:
                                candidates.sort(key=lambda x: x[0], reverse=True)
                                candidates = candidates[:self.MAX_REVIEWS_PER_FILE]

                        except (json.JSONDecodeError, Exception) as e:
                            if line_num < 5:
                                logger.debug(f"Skipping line {line_num} in {filename}: {e}")

                        # Safety cap: stop reading after 50k lines
                        if line_num > 50000:
                            break

                # Sort by helpful votes and take top N
                candidates.sort(key=lambda x: x[0], reverse=True)
                candidates = candidates[:self.MAX_REVIEWS_PER_FILE]

                reviews_loaded = 0
                total_votes = 0
                for votes, review in candidates:
                    self._process_review_into_template(review, category)
                    reviews_loaded += 1
                    total_votes += votes

                if reviews_loaded > 0:
                    self._category_avg_votes[category] = total_votes / reviews_loaded
                    logger.debug(
                        f"Loaded {reviews_loaded} resonance reviews from {filename} "
                        f"(avg votes: {self._category_avg_votes[category]:.1f})"
                    )

            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")

    def _load_from_merged_priors(self) -> None:
        """Load resonance data from ingestion_merged_priors.json."""
        data = None
        try:
            from adam.intelligence.unified_intelligence_service import get_unified_intelligence_service
            svc = get_unified_intelligence_service()
            raw = svc._load_layer1_priors()
            if raw:
                data = raw
        except Exception:
            pass

        if data is None:
            priors_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "learning", "ingestion_merged_priors.json",
            )
            if not os.path.exists(priors_path):
                return
            logger.warning("UnifiedIntelligenceService unavailable; loading priors from file")
            try:
                with open(priors_path) as f:
                    data = json.load(f)
            except Exception as e:
                logger.debug(f"Merged priors resonance load failed: {e}")
                return

        if data:
            # Extract template statistics
            template_stats = data.get("template_statistics", {})
            if template_stats:
                logger.debug(
                    f"Template statistics from priors: {len(template_stats)} entries"
                )

            # Extract from product_ad_profile_aggregates
            profiles = data.get("product_ad_profile_aggregates", {})
            for cat_key, profile in profiles.items():
                if not isinstance(profile, dict):
                    continue

                avg_votes = profile.get("avg_helpful_votes", 0)
                if avg_votes > 0 and cat_key not in self._category_avg_votes:
                    self._category_avg_votes[cat_key] = avg_votes

    def _load_from_graph(self) -> None:
        """Load PersuasiveTemplate nodes from Neo4j."""
        try:
            from adam.infrastructure.neo4j.pattern_persistence import get_pattern_persistence
            from adam.services.graph_intelligence import _run_async

            persistence = get_pattern_persistence()

            archetypes = [
                "analyst", "explorer", "guardian", "connector",
                "achiever", "pragmatist",
            ]

            async def _fetch_all():
                results = []
                for arch in archetypes:
                    try:
                        templates = await persistence.get_best_templates_for_archetype(
                            archetype=arch,
                            mechanism=None,
                            limit=10,
                        )
                        for t in templates:
                            if isinstance(t, dict):
                                results.append((arch, t))
                    except Exception:
                        pass
                return results

            all_templates = _run_async(_fetch_all())

            for arch, tmpl in all_templates:
                pattern = tmpl.get("pattern", "")
                mechanism = tmpl.get("mechanism", "unknown")
                category = tmpl.get("category", "all")
                votes = tmpl.get("helpful_votes", 0)
                success_rate = tmpl.get("success_rate", 0)

                if not pattern:
                    continue

                tid = f"graph_{arch}_{mechanism}_{hash(pattern) % 10000}"
                cat_avg = self._category_avg_votes.get(category, 10.0)

                self._templates[tid] = ResonanceTemplate(
                    template_id=tid,
                    category=category,
                    archetype=arch,
                    mechanism=mechanism,
                    pattern=pattern,
                    helpful_votes=votes,
                    category_avg_votes=cat_avg,
                    normalized_vote_score=votes / max(1.0, cat_avg),
                    purchase_confirmation_rate=success_rate,
                    evidence_count=votes,
                    source_type=PriorSourceType.HELPFUL_VOTE,
                )

        except Exception as e:
            logger.debug(f"Graph resonance template load failed: {e}")

    # =========================================================================
    # REVIEW → TEMPLATE PROCESSING
    # =========================================================================

    def _process_review_into_template(
        self, review: Dict[str, Any], category: str
    ) -> None:
        """Convert a high-influence review into a resonance template."""
        # Extract key fields
        helpful_votes = review.get("helpful_votes", review.get("helpful_vote", 0))
        if helpful_votes < 3:
            return  # Skip low-vote reviews

        archetype = review.get("archetype", review.get("buyer_archetype", "unknown"))
        mechanisms = review.get("mechanisms_detected", review.get("mechanisms", []))
        text = review.get("text", review.get("review_text", ""))
        success_rate = review.get("success_rate", review.get("purchase_confirmation_rate", 0))

        if not mechanisms:
            mechanisms = self._detect_mechanisms_from_text(text)

        primary_mechanism = mechanisms[0] if mechanisms else "social_proof"

        # Build template pattern (structural, not literal)
        pattern = self._extract_structural_pattern(text, primary_mechanism)
        if not pattern:
            return

        tid = f"hv_{category}_{archetype}_{primary_mechanism}_{hash(text) % 100000}"
        cat_avg = self._category_avg_votes.get(category, 10.0)

        template = ResonanceTemplate(
            template_id=tid,
            category=category,
            archetype=archetype,
            mechanism=primary_mechanism,
            pattern=pattern,
            helpful_votes=helpful_votes,
            category_avg_votes=cat_avg,
            normalized_vote_score=helpful_votes / max(1.0, cat_avg),
            purchase_confirmation_rate=success_rate,
            evidence_count=helpful_votes,
            source_type=PriorSourceType.HELPFUL_VOTE,
        )

        self._templates[tid] = template

        # Update category profile
        profile_key = f"{category}:{archetype}"
        if profile_key not in self._category_profiles:
            self._category_profiles[profile_key] = CategoryResonanceProfile(
                category=category,
                archetype=archetype,
            )

        profile = self._category_profiles[profile_key]
        profile.templates.append(template)
        profile.total_helpful_votes += helpful_votes
        profile.template_count += 1

        # Recompute averages
        scores = [t.resonance_score for t in profile.templates]
        profile.avg_resonance_score = sum(scores) / len(scores) if scores else 0

        # Track dominant mechanisms
        mech_counts: Dict[str, int] = {}
        for t in profile.templates:
            mech_counts[t.mechanism] = mech_counts.get(t.mechanism, 0) + 1
        profile.dominant_mechanisms = sorted(
            mech_counts, key=mech_counts.get, reverse=True
        )[:5]

    def _extract_structural_pattern(
        self, text: str, mechanism: str
    ) -> Optional[str]:
        """Extract structural persuasion pattern from review text."""
        if not text or len(text) < 20:
            return None

        # Extract key phrases that indicate persuasive structure
        # (not the literal text, but the pattern type)
        patterns = []

        # Social proof patterns
        if mechanism == "social_proof":
            if any(w in text.lower() for w in ["everyone", "all my friends", "recommended"]):
                patterns.append("peer_validation_appeal")
            if any(w in text.lower() for w in ["best seller", "popular", "many people"]):
                patterns.append("popularity_appeal")

        # Authority patterns
        elif mechanism == "authority":
            if any(w in text.lower() for w in ["expert", "professional", "years of"]):
                patterns.append("expert_credibility_appeal")
            if any(w in text.lower() for w in ["tested", "compared", "research"]):
                patterns.append("evidence_based_appeal")

        # Scarcity patterns
        elif mechanism == "scarcity":
            if any(w in text.lower() for w in ["before it's gone", "limited", "hurry"]):
                patterns.append("urgency_appeal")
            if any(w in text.lower() for w in ["wish i had", "sooner", "don't wait"]):
                patterns.append("regret_prevention_appeal")

        # Reciprocity patterns
        elif mechanism == "reciprocity":
            if any(w in text.lower() for w in ["saved me", "hope this helps", "sharing"]):
                patterns.append("value_sharing_appeal")

        # Commitment patterns
        elif mechanism == "commitment":
            if any(w in text.lower() for w in ["bought again", "loyal", "always buy"]):
                patterns.append("consistency_appeal")

        # Storytelling patterns
        elif mechanism == "storytelling":
            if any(w in text.lower() for w in ["my story", "happened to me", "experience"]):
                patterns.append("personal_narrative_appeal")

        if not patterns:
            # Generic pattern based on text structure
            word_count = len(text.split())
            if word_count > 100:
                patterns.append("detailed_analytical_review")
            elif word_count > 50:
                patterns.append("moderate_narrative_review")
            else:
                patterns.append("concise_endorsement")

        return "; ".join(patterns)

    def _detect_mechanisms_from_text(self, text: str) -> List[str]:
        """Basic mechanism detection from review text."""
        text_lower = text.lower() if text else ""
        detected = []

        keyword_map = {
            "social_proof": ["everyone", "popular", "recommend", "best seller"],
            "authority": ["expert", "professional", "doctor", "years"],
            "scarcity": ["limited", "hurry", "before", "running out"],
            "reciprocity": ["saved me", "helped", "worth sharing"],
            "commitment": ["bought again", "loyal", "consistent"],
            "liking": ["love", "beautiful", "amazing", "gorgeous"],
            "storytelling": ["my story", "happened", "experience", "journey"],
        }

        for mechanism, keywords in keyword_map.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(mechanism)

        return detected or ["social_proof"]

    # =========================================================================
    # QUERY INTERFACE
    # =========================================================================

    def get_resonance_templates(
        self,
        category: str,
        archetype: Optional[str] = None,
        mechanism: Optional[str] = None,
        top_k: int = 5,
    ) -> List[ResonanceTemplate]:
        """
        Get top resonance templates for a query.

        Templates are ranked by resonance_score (combines vote
        normalization with purchase confirmation rate).

        Args:
            category: Product category
            archetype: Target archetype (optional)
            mechanism: Target mechanism (optional)
            top_k: Number of templates to return

        Returns:
            Ranked list of ResonanceTemplates
        """
        self._ensure_loaded()

        candidates = []
        for tid, template in self._templates.items():
            # Category match (fuzzy)
            cat_match = (
                category.lower().replace("_", " ")
                in template.category.lower().replace("_", " ")
                or template.category.lower().replace("_", " ")
                in category.lower().replace("_", " ")
                or template.category == "all"
            )
            if not cat_match:
                continue

            # Archetype match (if specified)
            if archetype and template.archetype != archetype:
                continue

            # Mechanism match (if specified)
            if mechanism and template.mechanism != mechanism:
                continue

            candidates.append(template)

        # Sort by resonance score
        candidates.sort(key=lambda t: t.resonance_score, reverse=True)
        return candidates[:top_k]

    def get_category_resonance_profile(
        self,
        category: str,
        archetype: str,
    ) -> Optional[CategoryResonanceProfile]:
        """Get the resonance profile for a category × archetype."""
        self._ensure_loaded()
        key = f"{category}:{archetype}"
        return self._category_profiles.get(key)

    def get_confidence_multiplier(
        self,
        category: str,
        archetype: Optional[str] = None,
        mechanism: Optional[str] = None,
    ) -> float:
        """
        Get helpful-vote confidence multiplier for a prior.

        This is used by Layer 1 (PriorExtractionService) to boost
        confidence on priors that have helpful-vote validation.

        Returns: multiplier >= 1.0 (>1 = boosted confidence)
        """
        self._ensure_loaded()

        templates = self.get_resonance_templates(
            category=category,
            archetype=archetype,
            mechanism=mechanism,
            top_k=10,
        )

        if not templates:
            return 1.0

        # Aggregate confidence multipliers
        multipliers = [t.confidence_multiplier for t in templates]
        # Geometric mean of top templates
        if multipliers:
            product = 1.0
            for m in multipliers:
                product *= m
            return product ** (1.0 / len(multipliers))

        return 1.0

    def get_resonance_patterns_for_copy(
        self,
        category: str,
        archetype: Optional[str] = None,
        mechanism: Optional[str] = None,
    ) -> List[str]:
        """
        Get resonance patterns formatted for copy generation.

        Returns structural patterns (not literal copy) that have been
        peer-validated as persuasive.
        """
        templates = self.get_resonance_templates(
            category=category,
            archetype=archetype,
            mechanism=mechanism,
            top_k=5,
        )

        return [t.pattern for t in templates if t.pattern]

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get resonance index statistics."""
        self._ensure_loaded()

        return {
            "total_templates": len(self._templates),
            "category_profiles": len(self._category_profiles),
            "categories_with_avg_votes": len(self._category_avg_votes),
            "top_categories_by_templates": sorted(
                [
                    {
                        "profile_key": k,
                        "template_count": v.template_count,
                        "total_votes": v.total_helpful_votes,
                        "avg_resonance": v.avg_resonance_score,
                        "dominant_mechanisms": v.dominant_mechanisms[:3],
                    }
                    for k, v in self._category_profiles.items()
                ],
                key=lambda x: x["total_votes"],
                reverse=True,
            )[:10],
            "vote_distribution": {
                cat: avg for cat, avg in sorted(
                    self._category_avg_votes.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10]
            },
        }


# =============================================================================
# SINGLETON
# =============================================================================

_index: Optional[PersuasionResonanceIndex] = None


def get_persuasion_resonance_index() -> PersuasionResonanceIndex:
    """Get singleton PersuasionResonanceIndex."""
    global _index
    if _index is None:
        _index = PersuasionResonanceIndex()
    return _index
