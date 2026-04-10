# =============================================================================
# ADAM Psychological Construct Resolver
# Location: adam/atoms/core/construct_resolver.py
# =============================================================================

"""
PSYCHOLOGICAL CONSTRUCT RESOLVER

Resolves psychological dimensions from the richest available source, with NDF
as fallback.  Follows the same accessor pattern as DSPDataAccessor.

Priority chain (checked in order):
    1. graph_type_inference  — 1.9M GranularType traversal (7 expanded dims)
    2. expanded_customer_type — pre-inferred from empirical psychology framework
    3. dimensional_priors    — 430+ corpus-aggregated dimensions
    4. NDF                   — 7+1 compressed dimensions (fallback)
    5. default (0.5)

Usage (mirrors DSPDataAccessor):
    psy = PsychologicalConstructResolver(atom_input)
    ut  = psy.uncertainty_tolerance       # float, richest source
    ce  = psy.cognitive_engagement        # float
    mechs = psy.mechanism_recommendations # dict from graph type inference
    print(psy.source_report)              # per-dimension source audit
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# DIMENSION -> CONTINUOUS SCORE LOOKUP TABLES
# Derived from adam/intelligence/empirical_psychology_framework.py definitions.
# Each maps a discrete expanded-type value to the equivalent NDF-scale float.
# =============================================================================

# --- regulatory_focus -> uncertainty_tolerance ---
# Higher approach / lower avoidance = more tolerant of uncertainty.
REGULATORY_FOCUS_TO_UNCERTAINTY_TOLERANCE: Dict[str, float] = {
    "eager_advancement":       0.75,
    "aspiration_driven":       0.65,
    "optimistic_exploration":  0.70,
    "pragmatic_balanced":      0.50,
    "situational_adaptive":    0.50,
    "vigilant_security":       0.20,
    "conservative_preservation": 0.25,
    "anxious_avoidance":       0.15,
}

# --- regulatory_focus -> approach_avoidance ---
# (approach_intensity - avoidance_intensity) / 2 + 0.5, from framework data.
REGULATORY_FOCUS_TO_APPROACH_AVOIDANCE: Dict[str, float] = {
    "eager_advancement":       0.925,
    "aspiration_driven":       0.825,
    "optimistic_exploration":  0.775,
    "pragmatic_balanced":      0.50,
    "situational_adaptive":    0.50,
    "vigilant_security":       0.15,
    "conservative_preservation": 0.20,
    "anxious_avoidance":       0.10,
}

# --- decision_style -> cognitive_engagement ---
# Maps to cognitive_effort_willingness from DecisionStyleDimension.
DECISION_STYLE_TO_COGNITIVE_ENGAGEMENT: Dict[str, float] = {
    "gut_instinct":            0.20,
    "recognition_based":       0.30,
    "affect_driven":           0.25,
    "satisficing":             0.40,
    "heuristic_based":         0.50,
    "social_referencing":      0.45,
    "authority_deferring":     0.40,
    "maximizing":              0.95,
    "analytical_systematic":   0.90,
    "risk_calculating":        0.85,
    "deliberative_reflective": 0.85,
    "consensus_building":      0.70,
}

# --- social_influence -> social_calibration ---
# Weighted blend of normative_influence and conformity_tendency.
SOCIAL_INFLUENCE_TO_SOCIAL_CALIBRATION: Dict[str, float] = {
    "highly_independent":  0.15,
    "informational_seeker": 0.45,
    "socially_aware":      0.60,
    "normatively_driven":  0.85,
    "opinion_leader":      0.35,
}

# --- emotional_intensity -> arousal_seeking ---
# Maps to arousal_level from EmotionalIntensityDimension.
EMOTIONAL_INTENSITY_TO_AROUSAL_SEEKING: Dict[str, float] = {
    "high_positive_activation": 0.90,
    "high_negative_activation": 0.85,
    "mixed_high_arousal":       0.80,
    "moderate_positive":        0.50,
    "moderate_negative":        0.45,
    "emotionally_neutral":      0.25,
    "low_positive_calm":        0.20,
    "low_negative_sad":         0.20,
    "apathetic_disengaged":     0.10,
}

# --- temporal_orientation -> temporal_horizon ---
# Maps to future_orientation from TemporalOrientationDimension.
TEMPORAL_ORIENTATION_TO_TEMPORAL_HORIZON: Dict[str, float] = {
    "immediate_present": 0.15,
    "short_term":        0.35,
    "medium_term":       0.60,
    "long_term_future":  0.90,
}

# --- cognitive_load -> cognitive_engagement (secondary signal) ---
# Maps to (1 - simplification_preference) from CognitiveLoadDimension.
COGNITIVE_LOAD_TO_ENGAGEMENT: Dict[str, float] = {
    "minimal_cognitive":  0.10,
    "moderate_cognitive":  0.50,
    "high_cognitive":      0.80,
}

# --- motivation -> status_sensitivity ---
# Derived from relatedness_need, category, and explicit status-related names.
# Only the most informative motivations are listed; unlisted ones get a
# category-based default computed in _motivation_to_status_sensitivity().
_STATUS_OVERRIDES: Dict[str, float] = {
    "status_signaling":            0.95,
    "ego_protection":              0.80,
    "self_esteem_enhancement":     0.70,
    "social_approval":             0.75,
    "belonging_affirmation":       0.60,
    "uniqueness_differentiation":  0.65,
    "social_compliance":           0.55,
    "relationship_maintenance":    0.45,
    "social_enjoyment":            0.50,
    "altruistic_giving":           0.35,
    "pure_curiosity":              0.15,
    "mastery_seeking":             0.25,
    "self_expression":             0.40,
    "flow_experience":             0.15,
    "personal_growth":             0.25,
    "values_alignment":            0.25,
    "goal_achievement":            0.30,
    "role_fulfillment":            0.45,
    "future_self_investment":      0.25,
    "guilt_avoidance":             0.40,
    "anxiety_reduction":           0.20,
    "reward_seeking":              0.30,
    "punishment_avoidance":        0.15,
    "authority_compliance":        0.30,
    "sensory_pleasure":            0.30,
    "excitement_seeking":          0.35,
    "nostalgia_comfort":           0.25,
    "escapism":                    0.15,
    "problem_solving":             0.10,
    "efficiency_optimization":     0.15,
    "cost_minimization":           0.15,
    "quality_assurance":           0.20,
    "risk_mitigation":             0.15,
    "immediate_gratification":     0.30,
    "delayed_gratification":       0.20,
    "scarcity_response":           0.40,
    "opportunity_cost_awareness":  0.20,
}


def _motivation_to_status_sensitivity(motivation: str) -> Optional[float]:
    """Derive status_sensitivity from a motivation name."""
    return _STATUS_OVERRIDES.get(motivation)


# =============================================================================
# RESOLVER CLASS
# =============================================================================

class PsychologicalConstructResolver:
    """
    Resolves psychological dimensions from the richest available source.

    Usage (identical pattern to DSPDataAccessor):
        psy = PsychologicalConstructResolver(atom_input)
        ut  = psy.uncertainty_tolerance
        ce  = psy.cognitive_engagement
        aa  = psy.approach_avoidance

        # Graph-derived recommendations
        mechs = psy.mechanism_recommendations

        # Source transparency
        print(psy.source_report)
    """

    __slots__ = (
        "_graph_type",
        "_expanded_type",
        "_dim_priors",
        "_ndf",
        "_graph_mechanism_priors",
        "_edge_dimensions",
        "_theory_intel",
        "_dsp_intel",
        "_corpus_intel",
        "_sources",
    )

    def __init__(self, atom_input):
        """
        Extract all psychological sources from atom_input.ad_context.

        Priority (richest first):
            1. edge_dimensions — 20+ continuous bilateral edge dims from L3 cascade
            2. graph_type_inference — 7 discrete dims from 1.9M GranularType
            3. expanded_customer_type — 7 discrete dims from archetype expansion
            4. dimensional_priors — 430+ corpus-aggregated dims
            5. ndf_intelligence — 7+1 compressed dims (FALLBACK ONLY)
            6. default (0.5)

        Works safely with any input shape — returns defaults when nothing
        is available.
        """
        ad_ctx = getattr(atom_input, "ad_context", None) or {}
        if not isinstance(ad_ctx, dict):
            ad_ctx = {}

        # Source 1: Graph type inference (highest priority)
        self._graph_type: Dict[str, Any] = ad_ctx.get("graph_type_inference", {}) or {}

        # Source 2: Expanded customer type
        expanded = ad_ctx.get("expanded_customer_type", {}) or {}
        self._expanded_type: Dict[str, Any] = (
            expanded.get("type", {}) if isinstance(expanded, dict) else {}
        ) or {}

        # Source 3: Dimensional priors from corpus
        self._dim_priors: Dict[str, Any] = ad_ctx.get("dimensional_priors", {}) or {}

        # Source 4: NDF (fallback)
        ndf_intel = ad_ctx.get("ndf_intelligence", {}) or {}
        self._ndf: Dict[str, float] = (
            ndf_intel.get("profile", {}) if isinstance(ndf_intel, dict) else {}
        ) or {}

        # Graph mechanism priors (separate top-level key)
        self._graph_mechanism_priors: Dict[str, float] = (
            ad_ctx.get("graph_mechanism_priors", {}) or {}
        )

        # Bilateral edge dimensions (20+ continuous dims from L3 cascade)
        # These are the RICHEST source — direct from 47M BRAND_CONVERTED edges.
        # When available, they should be preferred over NDF for all dimensions
        # that have a direct edge mapping.
        self._edge_dimensions: Dict[str, float] = (
            ad_ctx.get("edge_dimensions", {}) or {}
        )
        # Also check if edge dims were passed via buyer_uncertainty or gradient
        if not self._edge_dimensions:
            # Some paths store edge dimensions inside dsp_graph_intelligence
            dsp = ad_ctx.get("dsp_graph_intelligence", {}) or {}
            if dsp.get("edge_dimensions"):
                self._edge_dimensions = dsp["edge_dimensions"]

        # Theory graph intelligence (causal chains)
        self._theory_intel: Dict[str, Any] = (
            ad_ctx.get("theory_graph_intelligence", {}) or {}
        )

        # DSP intelligence (empirical effectiveness, synergies)
        self._dsp_intel: Dict[str, Any] = (
            ad_ctx.get("dsp_graph_intelligence", {}) or {}
        )

        # Corpus intelligence (937M review priors)
        self._corpus_intel: Dict[str, Any] = (
            ad_ctx.get("corpus_fusion_intelligence", {}) or {}
        )

        # Per-dimension source tracking
        self._sources: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Availability checks
    # ------------------------------------------------------------------

    @property
    def has_rich_constructs(self) -> bool:
        """True if any source richer than NDF is available."""
        return bool(self._graph_type) or bool(self._expanded_type)

    @property
    def has_ndf(self) -> bool:
        """True if NDF profile is available."""
        return bool(self._ndf)

    @property
    def has_any(self) -> bool:
        """True if any psychological data source is available."""
        return self.has_rich_constructs or self.has_ndf

    @property
    def source_report(self) -> Dict[str, str]:
        """Map of dimension -> source name (for debugging/transparency)."""
        return dict(self._sources)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_expanded_dim(self, dim_key: str) -> Optional[str]:
        """
        Get the discrete expanded-type value for *dim_key* from the best
        available source.

        Checks graph_type_inference first (under "dimensions" sub-dict or
        direct key), then expanded_customer_type.
        """
        # graph_type_inference may store dims under a "dimensions" sub-dict
        graph_dims = self._graph_type.get("dimensions", {})
        if isinstance(graph_dims, dict):
            val = graph_dims.get(dim_key)
            if val:
                return val

        # Or it may be a direct key on graph_type_inference
        val = self._graph_type.get(dim_key)
        if val and not isinstance(val, dict):
            return val

        # expanded_customer_type stores dims directly
        val = self._expanded_type.get(dim_key)
        if val and not isinstance(val, dict):
            return val

        return None

    def _resolve(
        self,
        ndf_key: str,
        expanded_dim_key: str,
        lookup: Dict[str, float],
        default: float = 0.5,
        edge_key: Optional[str] = None,
    ) -> float:
        """
        Resolve a continuous score for *ndf_key* from the richest source.

        Priority (lossless first):
            1. bilateral edge dimensions — continuous float from 47M edges (no compression)
            2. expanded type dimension → lookup table (discrete → float via table)
            3. dimensional priors — corpus-aggregated continuous values
            4. NDF direct value — compressed 7-dim fallback
            5. default (0.5)
        """
        # Priority 1: bilateral edge dimensions (RICHEST — no compression)
        _edge_key = edge_key or ndf_key
        if _edge_key in self._edge_dimensions:
            val = self._edge_dimensions[_edge_key]
            if val is not None:
                self._sources[ndf_key] = f"edge.{_edge_key}"
                return float(val)

        # Priority 2: expanded type → lookup
        discrete_val = self._get_expanded_dim(expanded_dim_key)
        if discrete_val is not None and discrete_val in lookup:
            source = (
                f"graph_type.{expanded_dim_key}"
                if self._graph_type
                else f"expanded_type.{expanded_dim_key}"
            )
            self._sources[ndf_key] = source
            return lookup[discrete_val]

        # Priority 3: dimensional priors (corpus-aggregated)
        if ndf_key in self._dim_priors:
            dim_val = self._dim_priors[ndf_key]
            if isinstance(dim_val, (int, float)):
                self._sources[ndf_key] = "dimensional_priors"
                return float(dim_val)

        # Priority 4: NDF fallback (compressed — use only when nothing richer available)
        if ndf_key in self._ndf:
            self._sources[ndf_key] = "ndf"
            return self._ndf[ndf_key]

        # Priority 5: default
        self._sources[ndf_key] = "default"
        return default

    # ------------------------------------------------------------------
    # Dimension properties (what atoms consume)
    # ------------------------------------------------------------------

    @property
    def uncertainty_tolerance(self) -> float:
        """Uncertainty tolerance (0=intolerant/prevention, 1=tolerant/promotion)."""
        return self._resolve(
            "uncertainty_tolerance",
            "regulatory_focus",
            REGULATORY_FOCUS_TO_UNCERTAINTY_TOLERANCE,
            edge_key="uncertainty_tolerance",
        )

    @property
    def cognitive_engagement(self) -> float:
        """Cognitive engagement / effort willingness (0=System1, 1=System2)."""
        score = self._resolve(
            "cognitive_engagement",
            "decision_style",
            DECISION_STYLE_TO_COGNITIVE_ENGAGEMENT,
            edge_key="cognitive_load_tolerance",
        )
        if self._sources.get("cognitive_engagement") == "default":
            cl_val = self._get_expanded_dim("cognitive_load")
            if cl_val and cl_val in COGNITIVE_LOAD_TO_ENGAGEMENT:
                self._sources["cognitive_engagement"] = "expanded_type.cognitive_load"
                return COGNITIVE_LOAD_TO_ENGAGEMENT[cl_val]
        return score

    @property
    def approach_avoidance(self) -> float:
        """Approach-avoidance orientation (0=strong avoidance, 1=strong approach)."""
        return self._resolve(
            "approach_avoidance",
            "regulatory_focus",
            REGULATORY_FOCUS_TO_APPROACH_AVOIDANCE,
            edge_key="regulatory_fit",
        )

    @property
    def social_calibration(self) -> float:
        """Social calibration / influence susceptibility (0=independent, 1=normative)."""
        return self._resolve(
            "social_calibration",
            "social_influence",
            SOCIAL_INFLUENCE_TO_SOCIAL_CALIBRATION,
            edge_key="social_proof_sensitivity",
        )

    @property
    def arousal_seeking(self) -> float:
        """Arousal seeking / emotional intensity (0=apathetic, 1=high arousal)."""
        return self._resolve(
            "arousal_seeking",
            "emotional_intensity",
            EMOTIONAL_INTENSITY_TO_AROUSAL_SEEKING,
            edge_key="emotional_resonance",
        )

    @property
    def status_sensitivity(self) -> float:
        """Status sensitivity (0=indifferent, 1=highly status-motivated)."""
        # motivation → status_sensitivity is a derived computation
        motivation = self._get_expanded_dim("motivation")
        if motivation:
            score = _motivation_to_status_sensitivity(motivation)
            if score is not None:
                source = (
                    "graph_type.motivation"
                    if self._graph_type
                    else "expanded_type.motivation"
                )
                self._sources["status_sensitivity"] = source
                return score

        # NDF fallback
        if "status_sensitivity" in self._ndf:
            self._sources["status_sensitivity"] = "ndf"
            return self._ndf["status_sensitivity"]

        self._sources["status_sensitivity"] = "default"
        return 0.35

    @property
    def temporal_horizon(self) -> float:
        """Temporal horizon (0=immediate/present, 1=long-term/future)."""
        return self._resolve(
            "temporal_horizon",
            "temporal_orientation",
            TEMPORAL_ORIENTATION_TO_TEMPORAL_HORIZON,
            edge_key="temporal_discounting",
        )

    @property
    def cognitive_velocity(self) -> float:
        """
        Cognitive velocity — meta-dimension reflecting processing speed.

        Derived from decision_style + emotional_intensity when available,
        otherwise falls back to NDF.
        """
        # Try to derive from expanded types
        ds = self._get_expanded_dim("decision_style")
        ei = self._get_expanded_dim("emotional_intensity")
        if ds and ei:
            ce = DECISION_STYLE_TO_COGNITIVE_ENGAGEMENT.get(ds)
            ar = EMOTIONAL_INTENSITY_TO_AROUSAL_SEEKING.get(ei)
            if ce is not None and ar is not None:
                # High arousal + low cognitive engagement = high velocity
                cv = max(0.0, min(1.0, ar * 0.6 + (1.0 - ce) * 0.4))
                self._sources["cognitive_velocity"] = "derived(decision_style+emotional_intensity)"
                return cv

        # NDF fallback
        if "cognitive_velocity" in self._ndf:
            self._sources["cognitive_velocity"] = "ndf"
            return self._ndf["cognitive_velocity"]

        self._sources["cognitive_velocity"] = "default"
        return 0.0

    # ------------------------------------------------------------------
    # Extended bilateral construct dimensions (13 dimensions)
    # These are the psychological constructs that NDF collapses away.
    # Each maps to a specific atom's primary construct.
    # ------------------------------------------------------------------

    def _get_edge_dim(self, edge_key: str, default: float = 0.5) -> float:
        """Get a bilateral edge dimension directly."""
        val = self._edge_dimensions.get(edge_key)
        if val is not None:
            self._sources[edge_key] = f"edge.{edge_key}"
            return float(val)
        self._sources[edge_key] = "default"
        return default

    @property
    def persuasion_susceptibility(self) -> float:
        """Overall persuasion susceptibility (0=resistant, 1=susceptible)."""
        return self._get_edge_dim("persuasion_susceptibility")

    @property
    def narrative_transport(self) -> float:
        """Story engagement / narrative transportability (0=resistant, 1=absorbed)."""
        return self._get_edge_dim("narrative_transport")

    @property
    def loss_aversion_intensity(self) -> float:
        """Loss aversion intensity (0=loss-neutral, 1=strongly loss-averse)."""
        return self._get_edge_dim("loss_aversion_intensity")

    @property
    def brand_relationship_depth(self) -> float:
        """Brand relationship depth (0=stranger, 1=devoted)."""
        return self._get_edge_dim("brand_relationship_depth")

    @property
    def autonomy_reactance(self) -> float:
        """Autonomy/reactance (0=compliant, 1=strongly reactant)."""
        return self._get_edge_dim("autonomy_reactance")

    @property
    def information_seeking(self) -> float:
        """Information seeking drive (0=satisficer, 1=maximizer)."""
        return self._get_edge_dim("information_seeking")

    @property
    def mimetic_desire(self) -> float:
        """Mimetic desire / social imitation tendency (0=independent, 1=mimetic)."""
        return self._get_edge_dim("mimetic_desire")

    @property
    def interoceptive_awareness(self) -> float:
        """Body-signal awareness in decision-making (0=cerebral, 1=somatic)."""
        return self._get_edge_dim("interoceptive_awareness")

    @property
    def cooperative_framing_fit(self) -> float:
        """Fairness / reciprocity orientation (0=competitive, 1=cooperative)."""
        return self._get_edge_dim("cooperative_framing_fit")

    @property
    def decision_entropy(self) -> float:
        """Decision difficulty / choice overload (0=decisive, 1=paralyzed)."""
        return self._get_edge_dim("decision_entropy")

    # ------------------------------------------------------------------
    # Full construct dict (replaces as_ndf_dict — includes ALL dimensions)
    # ------------------------------------------------------------------

    def as_full_construct_dict(self) -> Dict[str, float]:
        """
        Return ALL available dimensions (up to 20+) as a flat dict.

        Includes the 8 NDF-compatible dims plus the 13 extended construct
        dims when bilateral edge data is available. This is the FULL
        psychological signal — use this instead of as_ndf_dict() to
        preserve maximum fidelity.
        """
        d = {
            # 8 NDF-compatible (resolved from richest source)
            "uncertainty_tolerance": self.uncertainty_tolerance,
            "cognitive_engagement": self.cognitive_engagement,
            "approach_avoidance": self.approach_avoidance,
            "social_calibration": self.social_calibration,
            "arousal_seeking": self.arousal_seeking,
            "status_sensitivity": self.status_sensitivity,
            "temporal_horizon": self.temporal_horizon,
            "cognitive_velocity": self.cognitive_velocity,
        }
        # 13 extended construct dimensions (from bilateral edges when available)
        for ext_dim in [
            "persuasion_susceptibility", "narrative_transport",
            "loss_aversion_intensity", "brand_relationship_depth",
            "autonomy_reactance", "information_seeking", "mimetic_desire",
            "interoceptive_awareness", "cooperative_framing_fit",
            "decision_entropy", "cognitive_load_tolerance",
            "social_proof_sensitivity", "temporal_discounting",
        ]:
            val = self._edge_dimensions.get(ext_dim)
            if val is not None:
                d[ext_dim] = float(val)
        return d

    def as_ndf_dict(self) -> Dict[str, float]:
        """
        Return 8 dimensions as NDF-compatible dict (DEPRECATED — use as_full_construct_dict).

        Retained for backward compatibility with code that expects exactly
        8 keys. New code should use as_full_construct_dict() instead.
        """
        return {
            "uncertainty_tolerance": self.uncertainty_tolerance,
            "cognitive_engagement": self.cognitive_engagement,
            "approach_avoidance": self.approach_avoidance,
            "social_calibration": self.social_calibration,
            "arousal_seeking": self.arousal_seeking,
            "status_sensitivity": self.status_sensitivity,
            "temporal_horizon": self.temporal_horizon,
            "cognitive_velocity": self.cognitive_velocity,
        }

    @property
    def has_edge_dimensions(self) -> bool:
        """True if bilateral edge dimensions are available (richest source)."""
        return bool(self._edge_dimensions)

    @property
    def signal_fidelity(self) -> str:
        """Report which source tier is driving most dimensions."""
        sources = list(self._sources.values())
        if not sources:
            return "none"
        edge_count = sum(1 for s in sources if s.startswith("edge."))
        graph_count = sum(1 for s in sources if s.startswith("graph_type.") or s.startswith("expanded_type."))
        ndf_count = sum(1 for s in sources if s == "ndf")
        default_count = sum(1 for s in sources if s == "default")

        if edge_count > graph_count and edge_count > ndf_count:
            return f"bilateral_edge ({edge_count}/{len(sources)} dims)"
        if graph_count > ndf_count:
            return f"graph_type ({graph_count}/{len(sources)} dims)"
        if ndf_count > default_count:
            return f"ndf_compressed ({ndf_count}/{len(sources)} dims)"
        return f"default ({default_count}/{len(sources)} dims)"

    # ------------------------------------------------------------------
    # Graph-derived recommendations (atoms can use these directly)
    # ------------------------------------------------------------------

    @property
    def mechanism_recommendations(self) -> Dict[str, float]:
        """
        Mechanism priors from graph type system traversal.

        Returns {mechanism_name: score} or empty dict.
        """
        return self._graph_mechanism_priors

    @property
    def value_propositions(self) -> Dict[str, float]:
        """Value proposition matches from graph ALIGNS_WITH_VALUE edges."""
        return self._graph_type.get("graph_value_propositions", {}) or {}

    @property
    def style_recommendations(self) -> Dict[str, float]:
        """Linguistic style recommendations from graph MATCHES_STYLE edges."""
        return self._graph_type.get("graph_style_recommendations", {}) or {}

    @property
    def emotional_appeals(self) -> Dict[str, float]:
        """Emotional appeal matches from graph RESONATES_WITH edges."""
        return self._graph_type.get("graph_emotional_appeals", {}) or {}

    @property
    def technique_recommendations(self) -> Dict[str, float]:
        """Persuasion technique recommendations from graph."""
        return self._graph_type.get("graph_technique_recommendations", {}) or {}

    # ------------------------------------------------------------------
    # Expanded type dimension accessors (discrete names, not scores)
    # ------------------------------------------------------------------

    @property
    def motivation(self) -> Optional[str]:
        """Discrete motivation type name, or None."""
        return self._get_expanded_dim("motivation")

    @property
    def decision_style(self) -> Optional[str]:
        """Discrete decision style name, or None."""
        return self._get_expanded_dim("decision_style")

    @property
    def regulatory_focus(self) -> Optional[str]:
        """Discrete regulatory focus name, or None."""
        return self._get_expanded_dim("regulatory_focus")

    @property
    def emotional_intensity(self) -> Optional[str]:
        """Discrete emotional intensity name, or None."""
        return self._get_expanded_dim("emotional_intensity")

    @property
    def cognitive_load(self) -> Optional[str]:
        """Discrete cognitive load tolerance name, or None."""
        return self._get_expanded_dim("cognitive_load")

    @property
    def temporal_orientation(self) -> Optional[str]:
        """Discrete temporal orientation name, or None."""
        return self._get_expanded_dim("temporal_orientation")

    @property
    def social_influence(self) -> Optional[str]:
        """Discrete social influence type name, or None."""
        return self._get_expanded_dim("social_influence")
