"""
SegmentBuilder — generates psychological audience segments from construct profiles.

Accepts a psychological profile (edge dimensions or construct activations) and
maps to targetable segments. No NDF compression — works with full 20-dimension
bilateral edge evidence or arbitrary construct activation dicts.

Two-tier architecture:
    PRIMARY: Graph-backed construct queries from Neo4j (441 constructs)
    FALLBACK: Static construct threshold rules (14 segments)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adam.platform.intelligence.taxonomy_mapper import ADAM_TO_TAXONOMY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Segment definitions — construct-native (no NDF compression)
#
# Each segment is defined by:
#   - Primary constructs that must be active (with direction: high/low)
#   - Mechanisms empirically effective for this segment
#   - INFORMATIV taxonomy IDs for SSP/DSP targeting
#
# The `construct_rules` dict maps edge dimension names → (threshold, direction).
# These work with the full 20-dim bilateral edge profile directly.
# ---------------------------------------------------------------------------
SEGMENT_DEFINITIONS = {
    "promotion_seeker": {
        "description": "Responds to gain-framed messaging, opportunity-focused",
        "construct_rules": {"regulatory_fit": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-001"],
        "mechanisms": ["anchoring", "scarcity"],
        "constructs": ["promotion_focus", "approach_motivation"],
    },
    "prevention_guard": {
        "description": "Responds to loss-aversion, risk-protection messaging",
        "construct_rules": {"regulatory_fit": (0.4, "below")},
        "taxonomy_ids": ["INFORMATIV-PSY-002"],
        "mechanisms": ["loss_aversion", "authority"],
        "constructs": ["prevention_focus", "loss_aversion"],
    },
    "future_planner": {
        "description": "Long-term oriented, investment-minded",
        "construct_rules": {"construal_fit": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-003"],
        "mechanisms": ["commitment_consistency"],
        "constructs": ["future_orientation", "delay_tolerance"],
    },
    "impulse_buyer": {
        "description": "Present-focused, responds to immediacy cues",
        "construct_rules": {"construal_fit": (0.4, "below"), "temporal_discounting": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-004"],
        "mechanisms": ["scarcity", "anchoring"],
        "constructs": ["present_orientation", "impulsivity"],
    },
    "social_validator": {
        "description": "Highly influenced by social proof and peer behavior",
        "construct_rules": {"social_proof_sensitivity": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-005"],
        "mechanisms": ["social_proof", "unity"],
        "constructs": ["social_proof_susceptibility", "conformity_need"],
    },
    "independent_decider": {
        "description": "Low social influence, values personal judgment",
        "construct_rules": {"autonomy_reactance": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-015"],
        "mechanisms": ["authority", "commitment_consistency"],
        "constructs": ["autonomy_reactance", "need_for_cognition"],
    },
    "uncertainty_tolerant": {
        "description": "Comfortable with ambiguity, open to exploration",
        "construct_rules": {"decision_entropy": (0.4, "below")},
        "taxonomy_ids": ["INFORMATIV-PSY-008"],
        "mechanisms": ["reciprocity", "liking"],
        "constructs": ["openness", "curiosity"],
    },
    "certainty_seeker": {
        "description": "Needs validation and guarantees before committing",
        "construct_rules": {"decision_entropy": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-009"],
        "mechanisms": ["authority", "social_proof"],
        "constructs": ["uncertainty_intolerance", "need_for_closure"],
    },
    "status_conscious": {
        "description": "Drawn to premium, exclusive, aspirational messaging",
        "construct_rules": {"value_alignment": (0.6, "above"), "mimetic_desire": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-006"],
        "mechanisms": ["scarcity", "authority"],
        "constructs": ["status_seeking", "identity_salience"],
    },
    "value_seeker": {
        "description": "Price-sensitive, responds to deals and value propositions",
        "construct_rules": {"cognitive_load_tolerance": (0.6, "above"), "information_seeking": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-012"],
        "mechanisms": ["anchoring", "reciprocity"],
        "constructs": ["price_sensitivity", "comparison_tendency"],
    },
    "deep_processor": {
        "description": "Engages deeply, prefers detailed information",
        "construct_rules": {"cognitive_load_tolerance": (0.65, "above"), "information_seeking": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-007"],
        "mechanisms": ["authority", "commitment_consistency"],
        "constructs": ["need_for_cognition", "analytical_processing"],
    },
    "quick_processor": {
        "description": "Prefers simple, fast messaging with clear CTAs",
        "construct_rules": {"cognitive_load_tolerance": (0.35, "below")},
        "taxonomy_ids": ["INFORMATIV-PSY-017"],
        "mechanisms": ["social_proof", "scarcity"],
        "constructs": ["cognitive_ease_preference", "heuristic_processing"],
    },
    "novelty_seeker": {
        "description": "Attracted to new, exciting, stimulating content",
        "construct_rules": {"emotional_resonance": (0.6, "above"), "narrative_transport": (0.6, "above")},
        "taxonomy_ids": ["INFORMATIV-PSY-008"],
        "mechanisms": ["scarcity", "liking"],
        "constructs": ["sensation_seeking", "openness"],
    },
    "comfort_seeker": {
        "description": "Prefers familiar, trusted, calming messaging",
        "construct_rules": {"brand_relationship_depth": (0.6, "above"), "emotional_resonance": (0.4, "below")},
        "taxonomy_ids": ["INFORMATIV-PSY-011"],
        "mechanisms": ["authority", "unity"],
        "constructs": ["brand_loyalty", "risk_aversion"],
    },
}

# Cypher: get construct activation levels and mechanism effectiveness
_CONSTRUCT_ACTIVATION_QUERY = """
MATCH (c:PsychologicalConstruct)
WHERE c.name IN $construct_names
OPTIONAL MATCH (c)-[e:EMPIRICALLY_EFFECTIVE]->(m:CognitiveMechanism)
OPTIONAL MATCH (c)-[:CONTEXTUALLY_MODERATES]->(cat:Category)
WHERE $category = '' OR cat.name STARTS WITH $category
RETURN c.name AS construct,
       c.domain_id AS domain,
       COLLECT(DISTINCT {mechanism: m.name, score: e.effectiveness, samples: e.sample_size}) AS mechanisms,
       COLLECT(DISTINCT cat.name) AS relevant_categories
"""


class SegmentBuilder:
    """
    Builds psychological audience segments from edge dimension profiles.

    Accepts the full 20-dimension bilateral edge profile (or any subset)
    and matches against construct-native segment definitions.

    PRIMARY PATH: Graph-backed construct queries from Neo4j
    FALLBACK: Static construct threshold rules
    """

    def __init__(self, graph_intelligence=None):
        self._graph = graph_intelligence
        self._neo4j_driver = None

    def _get_driver(self):
        """Lazy-load Neo4j driver."""
        if self._neo4j_driver is None:
            try:
                from adam.infrastructure.neo4j.client import get_neo4j_client
                client = get_neo4j_client()
                if client.is_connected:
                    self._neo4j_driver = client.driver
            except Exception:
                pass
        return self._neo4j_driver

    def build_segments(
        self,
        profile: Dict[str, float],
        mechanisms: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build segments from a psychological profile.

        Args:
            profile: Edge dimensions dict. Accepts both the 20-dim bilateral
                     edge format (regulatory_fit, emotional_resonance, etc.)
                     and legacy 7-dim NDF format (approach_avoidance, etc.)
                     for backward compatibility with existing callers.
            mechanisms: Optional mechanism activations for mechanism-based segments.
            category: Optional product category for category-specific graph queries.
        """
        # Normalize legacy NDF keys → edge dimension keys if needed
        normalized = self._normalize_profile(profile)

        # Try graph-backed segment building first
        try:
            graph_segments = self._build_graph_backed_segments(normalized, category)
            if graph_segments:
                logger.debug("Graph-backed segments: %d matches", len(graph_segments))
                return graph_segments
        except Exception as e:
            logger.debug("Graph segment building unavailable: %s", e)

        # FALLBACK: static construct threshold rules
        return self._build_static_segments(normalized, mechanisms)

    def _normalize_profile(self, profile: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize profile keys to edge dimension names.

        Accepts both 20-dim edge format and legacy 7-dim NDF format.
        When NDF keys are present, maps them to the closest edge dimensions.
        """
        # If profile already has edge dimension keys, use as-is
        edge_keys = {
            "regulatory_fit", "construal_fit", "personality_alignment",
            "emotional_resonance", "value_alignment", "evolutionary_motive",
            "social_proof_sensitivity", "cognitive_load_tolerance",
            "narrative_transport", "loss_aversion_intensity",
            "temporal_discounting", "brand_relationship_depth",
            "autonomy_reactance", "information_seeking", "mimetic_desire",
            "interoceptive_awareness", "cooperative_framing_fit",
            "decision_entropy", "persuasion_susceptibility",
        }
        if any(k in edge_keys for k in profile):
            return profile

        # Legacy NDF key → edge dimension mapping
        legacy_map = {
            "approach_avoidance": "regulatory_fit",
            "temporal_horizon": "construal_fit",
            "social_calibration": "personality_alignment",
            "uncertainty_tolerance": "decision_entropy",  # inverted below
            "status_sensitivity": "value_alignment",
            "cognitive_engagement": "cognitive_load_tolerance",
            "arousal_seeking": "emotional_resonance",
        }
        normalized = {}
        for old_key, new_key in legacy_map.items():
            if old_key in profile:
                val = profile[old_key]
                # uncertainty_tolerance is inverted relative to decision_entropy
                if old_key == "uncertainty_tolerance":
                    val = 1.0 - val
                normalized[new_key] = val
        return normalized

    def _build_graph_backed_segments(
        self,
        profile: Dict[str, float],
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build segments by querying graph constructs matching the profile.

        Uses the 441 graph constructs instead of hardcoded threshold rules.
        """
        driver = self._get_driver()
        if driver is None:
            return []

        # Determine which constructs are activated from the edge profile
        active_constructs = []
        for seg_def in SEGMENT_DEFINITIONS.values():
            for construct_name in seg_def.get("constructs", []):
                if construct_name not in active_constructs:
                    # Check if this segment's rules match the profile
                    if self._evaluate_construct_rules(profile, seg_def["construct_rules"]):
                        active_constructs.extend(seg_def["constructs"])

        if not active_constructs:
            return []

        active_constructs = list(set(active_constructs))

        # Query graph for these constructs + their mechanism effectiveness
        try:
            with driver.session() as session:
                result = session.run(
                    _CONSTRUCT_ACTIVATION_QUERY,
                    construct_names=active_constructs,
                    category=category or "",
                )
                records = result.data()
        except Exception as e:
            logger.debug("Graph construct query failed: %s", e)
            return []

        if not records:
            return []

        # Index graph results by construct name
        graph_mechs = {}
        for rec in records:
            cname = rec["construct"]
            mechs = [
                m["mechanism"] for m in rec.get("mechanisms", [])
                if m.get("mechanism") and m.get("score", 0) > 0.4
            ]
            graph_mechs[cname] = {
                "mechanisms": mechs,
                "domain": rec.get("domain", ""),
            }

        # Build segments using graph-enriched mechanism data
        matching = []
        for seg_id, seg_def in SEGMENT_DEFINITIONS.items():
            if not self._evaluate_construct_rules(profile, seg_def["construct_rules"]):
                continue

            # Prefer graph-backed mechanisms over static ones
            mech_names = seg_def["mechanisms"]
            for cname in seg_def["constructs"]:
                if cname in graph_mechs and graph_mechs[cname]["mechanisms"]:
                    mech_names = graph_mechs[cname]["mechanisms"]
                    break

            taxonomy_ids = list(seg_def["taxonomy_ids"])
            for cname in seg_def["constructs"]:
                if cname in ADAM_TO_TAXONOMY:
                    tid = ADAM_TO_TAXONOMY[cname]["id"]
                    if tid not in taxonomy_ids:
                        taxonomy_ids.append(tid)

            strength = self._compute_segment_strength(profile, seg_def["construct_rules"])

            matching.append({
                "segment_id": seg_id,
                "segment_name": seg_id.replace("_", " ").title(),
                "description": seg_def["description"],
                "taxonomy_ids": taxonomy_ids,
                "recommended_mechanisms": mech_names[:5],
                "strength": strength,
                "evidence_source": "graph_constructs",
            })

        matching.sort(key=lambda x: x["strength"], reverse=True)
        return matching

    def _build_static_segments(
        self,
        profile: Dict[str, float],
        mechanisms: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """FALLBACK: Static construct threshold rules (no graph)."""
        matching = []
        for seg_id, seg_def in SEGMENT_DEFINITIONS.items():
            if self._evaluate_construct_rules(profile, seg_def["construct_rules"]):
                matching.append({
                    "segment_id": seg_id,
                    "segment_name": seg_id.replace("_", " ").title(),
                    "description": seg_def["description"],
                    "taxonomy_ids": seg_def["taxonomy_ids"],
                    "recommended_mechanisms": seg_def["mechanisms"],
                    "strength": self._compute_segment_strength(profile, seg_def["construct_rules"]),
                    "evidence_source": "static_construct_rules",
                })

        if mechanisms:
            for m in mechanisms[:3]:
                taxonomy_id = ADAM_TO_TAXONOMY.get(m, {}).get("id", "")
                matching.append({
                    "segment_id": f"mechanism_{m}",
                    "segment_name": f"Mechanism: {m.replace('_', ' ').title()}",
                    "description": f"Content activates {m} persuasion mechanism",
                    "taxonomy_ids": [taxonomy_id] if taxonomy_id else [],
                    "recommended_mechanisms": [m],
                    "strength": 0.7,
                    "evidence_source": "mechanism_activation",
                })

        matching.sort(key=lambda x: x["strength"], reverse=True)
        return matching

    def get_segment_names(self, profile: Dict[str, float]) -> List[str]:
        """Simplified: return just segment IDs."""
        segments = self.build_segments(profile)
        return [s["segment_id"] for s in segments]

    def get_available_segments(self) -> Dict[str, Dict[str, Any]]:
        """Return all available segment definitions."""
        return {
            seg_id: {
                "description": seg_def["description"],
                "taxonomy_ids": seg_def["taxonomy_ids"],
                "mechanisms": seg_def["mechanisms"],
                "constructs": seg_def.get("constructs", []),
            }
            for seg_id, seg_def in SEGMENT_DEFINITIONS.items()
        }

    def _evaluate_construct_rules(
        self,
        profile: Dict[str, float],
        rules: Dict[str, tuple],
    ) -> bool:
        """
        Evaluate whether a profile matches a segment's construct rules.

        Each rule is (threshold, direction) where direction is "above" or "below".
        ALL rules must match for the segment to activate.
        """
        for dim, (threshold, direction) in rules.items():
            val = profile.get(dim, 0.5)
            if direction == "above" and val <= threshold:
                return False
            elif direction == "below" and val >= threshold:
                return False
        return True

    def _compute_segment_strength(
        self,
        profile: Dict[str, float],
        rules: Dict[str, tuple],
    ) -> float:
        """How strongly the profile matches this segment's construct rules."""
        if not rules:
            return 0.5
        strengths = []
        for dim, (threshold, direction) in rules.items():
            val = profile.get(dim, 0.5)
            if direction == "above":
                strengths.append(max(0, (val - threshold) / (1.0 - threshold + 0.01)))
            else:
                strengths.append(max(0, (threshold - val) / (threshold + 0.01)))
        return round(sum(strengths) / len(strengths), 3) if strengths else 0.5
