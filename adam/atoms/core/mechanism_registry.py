# =============================================================================
# ADAM Mechanism Effectiveness Registry
# Location: adam/atoms/core/mechanism_registry.py
# =============================================================================

"""
MECHANISM EFFECTIVENESS REGISTRY

Shared intelligence source for all atoms. Replaces the pattern of 22 atoms
each maintaining their own hardcoded mechanism-effectiveness dicts with a
single registry backed by:

1. Graph-derived empirical data (RESPONDS_TO edges, BRAND_CONVERTED aggregates)
2. Theory graph chains (State→Need→Mechanism causal reasoning)
3. Mechanism synergies (MECHANISM_SYNERGY edges)
4. Hardcoded fallbacks (only when graph unavailable)

Usage in atoms:
    from adam.atoms.core.mechanism_registry import get_mechanism_registry

    registry = get_mechanism_registry()

    # Get mechanism effectiveness for this archetype
    scores = registry.get_mechanism_scores(archetype="achiever")

    # Get mechanism adjustment for a specific construct state
    adj = registry.get_construct_adjustment(
        construct="ambiguity_attitude",
        value="ambiguity_averse",
        mechanism="authority",
    )

    # Get mechanism synergies
    synergies = registry.get_synergies("authority")

    # Get theory-backed recommendation
    theory = registry.get_theory_recommendation(ndf_profile={...})

Atoms can still use their hardcoded maps as fallback — this registry
is additive, not a forced replacement.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MechanismEffectivenessRegistry:
    """
    Centralized mechanism intelligence for all atoms.

    Populated from ad_context during each request, providing atoms with
    a unified interface to graph-derived, theory-based, and empirical
    mechanism effectiveness data.

    Thread-safe for concurrent atom execution within a single request.
    """

    def __init__(self):
        self._mechanism_priors: Dict[str, float] = {}
        self._dsp_empirical: Dict[str, Dict[str, Any]] = {}
        self._synergies: List[Dict[str, Any]] = []
        self._theory_scores: Dict[str, float] = {}
        self._theory_chains: List[Dict[str, Any]] = []
        self._corpus_priors: Dict[str, Dict[str, Any]] = {}
        self._populated = False

    def populate_from_ad_context(self, ad_context: Optional[Dict[str, Any]]) -> None:
        """
        Populate the registry from the ad_context dict built by
        IntelligencePrefetchService.

        Called once per request, before atom DAG execution.
        """
        if not ad_context:
            return

        # Graph mechanism priors (RESPONDS_TO edges)
        self._mechanism_priors = ad_context.get("graph_mechanism_priors", {}) or {}

        # DSP empirical effectiveness
        dsp = ad_context.get("dsp_graph_intelligence", {}) or {}
        self._dsp_empirical = dsp.get("empirical_effectiveness", {}) or {}
        self._synergies = dsp.get("mechanism_synergies", []) or []

        # Theory graph chains
        theory = ad_context.get("theory_graph_intelligence", {}) or {}
        self._theory_scores = theory.get("mechanism_scores", {}) or {}
        self._theory_chains = theory.get("chains", []) or []

        # Corpus fusion priors
        corpus = ad_context.get("corpus_fusion_intelligence", {}) or {}
        self._corpus_priors = corpus.get("mechanism_priors", {}) or {}

        self._populated = bool(
            self._mechanism_priors or self._dsp_empirical or self._theory_scores
        )

        if self._populated:
            logger.debug(
                "MechanismRegistry populated: %d graph priors, %d empirical, "
                "%d theory scores, %d synergies",
                len(self._mechanism_priors),
                len(self._dsp_empirical),
                len(self._theory_scores),
                len(self._synergies),
            )

    @property
    def is_populated(self) -> bool:
        """True if registry has any graph/theory/empirical data."""
        return self._populated

    # =========================================================================
    # MECHANISM SCORES
    # =========================================================================

    def get_mechanism_scores(
        self,
        archetype: str = "",
        blend_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Get blended mechanism effectiveness scores from all sources.

        Uses evidence-weighted blending: each source's weight scales with
        confidence × log(1 + observations). High-confidence, well-observed
        sources naturally dominate. Falls back to static 50/30/20 when
        observation counts aren't available.

        Returns empty dict if no data available (atom uses its own fallback).
        """
        if not self._populated:
            return {}

        import math

        # Collect all mechanism names
        all_mechs = set()
        all_mechs.update(self._mechanism_priors.keys())
        all_mechs.update(self._theory_scores.keys())
        all_mechs.update(self._corpus_priors.keys())
        all_mechs.update(self._dsp_empirical.keys())

        if not all_mechs:
            return {}

        blended = {}
        for mech in all_mechs:
            sources: List[Tuple[float, float]] = []  # (score, evidence_weight)

            # Graph empirical (RESPONDS_TO edges) — weight by observation count
            graph_score = self._mechanism_priors.get(mech)
            if graph_score is not None:
                emp = self._dsp_empirical.get(mech, {})
                n_obs = emp.get("sample_size", 10) if emp else 10
                confidence = emp.get("confidence", 0.6) if emp else 0.6
                weight = confidence * math.log(1 + n_obs)
                sources.append((graph_score, weight))

            # Theory (causal chain reasoning) — lower base weight, scales with chain count
            theory_score = self._theory_scores.get(mech)
            if theory_score is not None:
                n_chains = sum(
                    1 for c in self._theory_chains
                    if c.get("mechanism") == mech
                )
                weight = 0.5 * math.log(1 + max(n_chains, 1) * 5)
                sources.append((theory_score, weight))

            # Corpus (937M reviews) — high base observations
            corpus_entry = self._corpus_priors.get(mech)
            if corpus_entry:
                corpus_score = corpus_entry.get("effect_size", 0.5)
                n_reviews = corpus_entry.get("n_reviews", 100)
                weight = 0.4 * math.log(1 + n_reviews)
                sources.append((corpus_score, weight))

            if sources:
                total_weight = sum(w for _, w in sources)
                if total_weight > 0:
                    blended[mech] = sum(s * w for s, w in sources) / total_weight

        return blended

    def get_mechanism_score(self, mechanism: str) -> Optional[float]:
        """Get a single mechanism's blended score, or None if unavailable."""
        scores = self.get_mechanism_scores()
        return scores.get(mechanism)

    # =========================================================================
    # SYNERGIES
    # =========================================================================

    def get_synergies(self, mechanism: str) -> List[Dict[str, Any]]:
        """
        Get synergistic/antagonistic mechanisms for the given mechanism.

        Returns list of {pair: [mech1, mech2], synergy_score, combined_lift}.
        """
        result = []
        for syn in self._synergies:
            pair = syn.get("pair", [])
            if mechanism in pair:
                result.append(syn)
        return result

    def get_synergy_score(self, mech1: str, mech2: str) -> Optional[float]:
        """Get synergy score between two mechanisms, or None if unknown."""
        for syn in self._synergies:
            pair = syn.get("pair", [])
            if mech1 in pair and mech2 in pair:
                return syn.get("synergy_score")
        return None

    # =========================================================================
    # THEORY CHAINS
    # =========================================================================

    def get_theory_chains(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Get theory-backed reasoning chains (State→Need→Mechanism).

        Each chain includes: mechanism, score, confidence, active_states,
        active_needs, processing_route.
        """
        return self._theory_chains[:top_k]

    def get_theory_recommendation(
        self, ndf_profile: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Get theory-derived mechanism scores (pre-computed from NDF)."""
        return dict(self._theory_scores)

    # =========================================================================
    # EMPIRICAL EVIDENCE
    # =========================================================================

    def get_empirical_effectiveness(self, mechanism: str) -> Optional[Dict[str, Any]]:
        """
        Get empirical effectiveness data for a mechanism.

        Returns {success_rate, sample_size, confidence} from RESPONDS_TO edges.
        """
        return self._dsp_empirical.get(mechanism)

    def get_evidence_depth(self, mechanism: str) -> str:
        """
        Classify evidence depth for a mechanism.

        Returns: "strong" (>50 observations), "moderate" (10-50),
                 "weak" (<10), "none" (no data).
        """
        emp = self._dsp_empirical.get(mechanism)
        if not emp:
            if mechanism in self._mechanism_priors:
                return "weak"
            return "none"

        sample = emp.get("sample_size", 0)
        if sample >= 50:
            return "strong"
        elif sample >= 10:
            return "moderate"
        return "weak"

    # =========================================================================
    # CONSTRUCT-MECHANISM ADJUSTMENT (for atom-specific logic)
    # =========================================================================

    def get_construct_adjustment(
        self,
        construct: str,
        value: str,
        mechanism: str,
        fallback: float = 0.0,
    ) -> float:
        """
        Get the adjustment for a mechanism given a construct state.

        Currently returns fallback (atoms use their own maps).
        Future: will query ConstructMechanismEdge relationships in the graph.

        Args:
            construct: Construct type (e.g., "ambiguity_attitude")
            value: Construct value (e.g., "ambiguity_averse")
            mechanism: Mechanism name (e.g., "authority")
            fallback: Value to return if no graph data available
        """
        # TODO: Query graph for construct→mechanism adjustment edges
        # For now, atoms continue using their own hardcoded maps
        # with this method available for future graph-backed lookup.
        return fallback


# =============================================================================
# PER-REQUEST FACTORY
# =============================================================================

def create_mechanism_registry(
    ad_context: Optional[Dict[str, Any]] = None,
) -> MechanismEffectivenessRegistry:
    """
    Create a new MechanismEffectivenessRegistry populated from ad_context.

    Called once per request. The registry is passed to atoms via ad_context
    so they can access it via:
        registry = ad_context.get("_mechanism_registry")
    """
    registry = MechanismEffectivenessRegistry()
    registry.populate_from_ad_context(ad_context)
    return registry


# Convenience accessor for atoms that receive ad_context
def get_mechanism_registry(
    ad_context: Optional[Dict[str, Any]] = None,
) -> MechanismEffectivenessRegistry:
    """
    Get the mechanism registry from ad_context, or create an empty one.

    Usage in atoms:
        registry = get_mechanism_registry(ad_context)
        if registry.is_populated:
            scores = registry.get_mechanism_scores()
        else:
            # Use atom's own hardcoded map as fallback
            scores = MY_HARDCODED_MAP[...]
    """
    if ad_context and "_mechanism_registry" in ad_context:
        return ad_context["_mechanism_registry"]

    # Create and optionally populate
    registry = MechanismEffectivenessRegistry()
    if ad_context:
        registry.populate_from_ad_context(ad_context)
    return registry
