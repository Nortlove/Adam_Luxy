# =============================================================================
# ADAM DSP Construct Integration for Atoms of Thought
# Location: adam/atoms/core/dsp_integration.py
# =============================================================================

"""
DSP GRAPH INTELLIGENCE INTEGRATION LAYER

Provides clean, type-safe access to DSP construct/edge data for all atoms,
plus group helpers for common integration patterns.

Architecture:
    DSPDataAccessor     — Extracts DSP data from atom_input.ad_context
    CategoryModerationHelper  — Applies category-specific mechanism deltas (9 atoms)
    SusceptibilityHelper      — Applies decision-style susceptibility (6 atoms)
    EmpiricalEffectivenessHelper — Applies review-corpus empirical data (3 atoms)

Data flow:
    Neo4j → PatternPersistence → AtomIntelligenceInjector → PriorContext
    → ad_context["dsp_graph_intelligence"] → DSPDataAccessor → atom scoring

The DSP graph intelligence dict has this structure:
    {
        "empirical_effectiveness": {mechanism_id: {success_rate, sample_size, ...}},
        "alignment_edges": [{edge_type, target_id, strength, matrix, description}],
        "category_moderation": {mechanism_id: delta},
        "relationship_amplification": {mechanism_id: boost_factor},
        "mechanism_susceptibility": {mechanism_id: susceptibility_strength},
        "has_dsp": bool,
    }
"""

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DSP DATA ACCESSOR
# =============================================================================

class DSPDataAccessor:
    """
    Clean accessor for DSP graph intelligence from atom input context.

    Usage:
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            delta = dsp.get_category_delta("social_proof")
    """

    __slots__ = ("_dsp",)

    def __init__(self, atom_input):
        """
        Extract DSP graph intelligence from atom_input.ad_context.

        Works safely with any input shape — returns empty data if DSP
        intelligence is not available.
        """
        ad_ctx = getattr(atom_input, "ad_context", None) or {}
        if isinstance(ad_ctx, dict):
            self._dsp = ad_ctx.get("dsp_graph_intelligence", {})
        else:
            self._dsp = {}

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @property
    def has_dsp(self) -> bool:
        """True if any DSP graph data is available."""
        return bool(self._dsp.get("has_dsp", False))

    # ------------------------------------------------------------------
    # Single-mechanism lookups
    # ------------------------------------------------------------------

    def get_empirical(self, mechanism: str) -> Optional[Dict[str, Any]]:
        """
        Get empirical effectiveness for a single mechanism.

        Returns: {success_rate: float, sample_size: int, ...} or None.
        """
        return self._dsp.get("empirical_effectiveness", {}).get(mechanism)

    def get_category_delta(self, mechanism: str) -> Optional[float]:
        """
        Get category moderation delta for a single mechanism.

        Returns: float delta (positive = boost, negative = dampen) or None.
        """
        cat = self._dsp.get("category_moderation", {})
        return cat.get(mechanism) if mechanism in cat else None

    def get_susceptibility(self, mechanism: str) -> Optional[float]:
        """
        Get mechanism susceptibility score (0-1) for a single mechanism.

        Returns: float susceptibility or None.
        """
        sus = self._dsp.get("mechanism_susceptibility", {})
        return sus.get(mechanism) if mechanism in sus else None

    def get_relationship_boost(self, mechanism: str) -> Optional[float]:
        """
        Get relationship amplification boost for a single mechanism.

        Returns: float boost factor or None.
        """
        rel = self._dsp.get("relationship_amplification", {})
        return rel.get(mechanism) if mechanism in rel else None

    # ------------------------------------------------------------------
    # Bulk lookups
    # ------------------------------------------------------------------

    def get_all_empirical(self) -> Dict[str, Dict[str, Any]]:
        """All empirical effectiveness data: {mechanism: {success_rate, sample_size, ...}}."""
        return self._dsp.get("empirical_effectiveness", {})

    def get_all_category_moderation(self) -> Dict[str, float]:
        """All category moderation deltas: {mechanism: delta}."""
        return self._dsp.get("category_moderation", {})

    def get_all_susceptibility(self) -> Dict[str, float]:
        """All mechanism susceptibility scores: {mechanism: strength}."""
        return self._dsp.get("mechanism_susceptibility", {})

    def get_all_relationship_boosts(self) -> Dict[str, float]:
        """All relationship amplification boosts: {mechanism: boost_factor}."""
        return self._dsp.get("relationship_amplification", {})

    def get_alignment_edges(self) -> List[Dict[str, Any]]:
        """All alignment edges: [{edge_type, target_id, strength, matrix, description}]."""
        return self._dsp.get("alignment_edges", [])


# =============================================================================
# MECHANISM NAME NORMALIZATION
# =============================================================================

def _normalize_mechanism_id(dsp_id: str) -> str:
    """
    Normalize a DSP mechanism ID to the ADAM core mechanism format.

    DSP graph stores IDs like 'social_proof', 'identity_construction'.
    ADAM atoms use the same snake_case format, so this is mostly passthrough
    but handles edge cases (whitespace, casing).
    """
    return dsp_id.strip().lower().replace(" ", "_")


def _match_adjustment_keys(
    dsp_data: Dict[str, Any],
    adjustments: Dict[str, float],
) -> Dict[str, str]:
    """
    Build a mapping from DSP mechanism IDs to adjustment keys.

    The DSP graph may use slightly different mechanism names than the atom's
    internal adjustment keys. This finds the best match for each DSP entry.

    Returns: {dsp_id: adjustment_key}
    """
    mapping = {}
    adj_keys_lower = {k.lower().replace(" ", "_"): k for k in adjustments}

    for dsp_id in dsp_data:
        normalized = _normalize_mechanism_id(dsp_id)
        if normalized in adj_keys_lower:
            mapping[dsp_id] = adj_keys_lower[normalized]

    return mapping


# =============================================================================
# GROUP A: CATEGORY MODERATION HELPER (9 atoms)
# =============================================================================

class CategoryModerationHelper:
    """
    Applies DSP category moderation deltas to mechanism adjustments.

    Category moderation captures how mechanism effectiveness varies by product
    category (e.g., "authority" is +15% more effective in Electronics).

    Used by: cooperative_framing, information_asymmetry, regret_anticipation,
             signal_credibility, temporal_self, cognitive_load,
             ambiguity_attitude, interoceptive_style, strategic_timing.
    """

    BLEND_WEIGHT = 0.15  # 15% blend for category moderation

    @staticmethod
    def apply(
        adjustments: Dict[str, float],
        dsp: DSPDataAccessor,
        blend_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Apply category moderation deltas to mechanism adjustment scores.

        For each mechanism in adjustments that also has a category delta in
        DSP data, blend the delta into the adjustment score.

        Args:
            adjustments: Dict of mechanism_id -> adjustment score from the atom.
            dsp: DSPDataAccessor instance.
            blend_weight: Override for BLEND_WEIGHT (default 0.15).

        Returns:
            New adjustments dict with category moderation applied.
            Does NOT mutate the original.
        """
        if not dsp.has_dsp:
            return adjustments

        cat_mod = dsp.get_all_category_moderation()
        if not cat_mod:
            return adjustments

        weight = blend_weight if blend_weight is not None else CategoryModerationHelper.BLEND_WEIGHT
        result = adjustments.copy()
        mapping = _match_adjustment_keys(cat_mod, adjustments)

        for dsp_id, adj_key in mapping.items():
            delta = cat_mod[dsp_id]
            # Blend: (1 - w) * original + w * (original + delta)
            # Simplifies to: original + w * delta
            result[adj_key] = result[adj_key] + weight * delta

        return result


# =============================================================================
# GROUP B: SUSCEPTIBILITY HELPER (6 atoms)
# =============================================================================

class SusceptibilityHelper:
    """
    Applies DSP mechanism susceptibility to adjustments.

    Susceptibility captures how much a user's decision style makes them
    responsive to specific mechanisms (e.g., "satisficing" users are highly
    susceptible to "social_proof" at 0.85).

    Used by: decision_entropy, motivational_conflict, predictive_error,
             strategic_awareness, autonomy_reactance, query_order.
    """

    BLEND_WEIGHT = 0.15  # 15% blend for susceptibility

    @staticmethod
    def apply(
        adjustments: Dict[str, float],
        dsp: DSPDataAccessor,
        blend_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Apply susceptibility data to mechanism adjustment scores.

        Mechanisms the user is highly susceptible to get boosted;
        those with low susceptibility get dampened.

        The susceptibility value (0-1) is centered at 0.5:
            > 0.5 = boost (user is receptive)
            < 0.5 = dampen (user is resistant)
        """
        if not dsp.has_dsp:
            return adjustments

        suscept = dsp.get_all_susceptibility()
        if not suscept:
            return adjustments

        weight = blend_weight if blend_weight is not None else SusceptibilityHelper.BLEND_WEIGHT
        result = adjustments.copy()
        mapping = _match_adjustment_keys(suscept, adjustments)

        for dsp_id, adj_key in mapping.items():
            strength = suscept[dsp_id]
            # Convert susceptibility (0-1) to an adjustment centered at 0:
            # 0.85 → +0.35, 0.5 → 0.0, 0.2 → -0.30
            delta = (strength - 0.5)
            result[adj_key] = result[adj_key] + weight * delta

        return result


# =============================================================================
# GROUP C: EMPIRICAL EFFECTIVENESS HELPER (3 atoms)
# =============================================================================

class EmpiricalEffectivenessHelper:
    """
    Applies DSP empirical effectiveness to adjustments.

    Empirical effectiveness comes from the 937M+ review corpus:
    success_rate (0-1) and sample_size determine how much we trust the data.

    Used by: mimetic_desire, review_intelligence, user_state.
    """

    BLEND_WEIGHT = 0.15  # 15% blend for empirical data

    @staticmethod
    def apply(
        adjustments: Dict[str, float],
        dsp: DSPDataAccessor,
        blend_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Apply empirical effectiveness (success_rate weighted by sample_size).

        High success_rate + high sample_size = strong positive adjustment.
        Low success_rate + high sample_size = strong negative adjustment.
        Low sample_size = weak adjustment (uncertain evidence).
        """
        if not dsp.has_dsp:
            return adjustments

        empirical = dsp.get_all_empirical()
        if not empirical:
            return adjustments

        weight = blend_weight if blend_weight is not None else EmpiricalEffectivenessHelper.BLEND_WEIGHT
        result = adjustments.copy()
        mapping = _match_adjustment_keys(empirical, adjustments)

        for dsp_id, adj_key in mapping.items():
            stats = empirical[dsp_id]
            success_rate = stats.get("success_rate", 0.5)
            sample_size = stats.get("sample_size", 0)

            # Confidence from sample size: log1p(n) / 10, capped at 1.0
            confidence = min(1.0, math.log1p(sample_size) / 10.0) if sample_size > 0 else 0.1

            # Adjustment: (success_rate - 0.5) * confidence
            # success_rate=0.8, confidence=1.0 → +0.30
            # success_rate=0.3, confidence=0.5 → -0.10
            delta = (success_rate - 0.5) * confidence
            result[adj_key] = result[adj_key] + weight * delta

        return result
