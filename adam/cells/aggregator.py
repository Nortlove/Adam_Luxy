"""S6.2 cell features aggregator — assembles CellFeatureSet from
bid-time substrate at the BEFORE seam in run_bilateral_cascade.

Per S6.2.0 audit (commit 0dc2a19) + Q16 adjudication: combined
aggregator + evaluator slice. The aggregator is the substrate-fetch
coordinator that S6.2 ships because no prior bid-time consumer of
the B/C/D/E/F.2 stack exists.

Bid-time latency: target <8ms p99 total. Each substrate fetch is
pre-cached upstream; aggregator's marginal cost is
dictionary-construction overhead + cell_id construction (4μs p99
per F.1 Test 17).

Design: dependency injection via constructor — substrate accessors
are passed as callables so the aggregator is testable without
mocking module-level imports. A `default_aggregator()` factory
wires the actual modules for production use.

Fail-soft: each substrate fetch is wrapped with a per-source
default. Any fetch raising an exception falls back to the default
value and aggregation completes with a valid CellFeatureSet. The
aggregator NEVER propagates exceptions to the bid-time path.
"""
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Tuple

from adam.cells.constructor import (
    compute_valence_arousal_quadrant,
    construct_cell_id,
)
from adam.cells.features import CellFeatureSet
from adam.cells.taxonomy import (
    ConversionStage,
    RegulatoryFocus,
    ValenceArousalQuadrant,
)
from adam.cold_start.models.enums import ArchetypeID


# Type aliases for clarity in constructor injection.
ArchetypeAccessor = Callable[[str], ArchetypeID]
PostureAccessor = Callable[[str], str]
JourneyAccessor = Callable[[str], ConversionStage]
PrimingAccessor = Callable[[str], Any]
MindstateAccessor = Callable[[str, str], Any]
CohortAccessor = Callable[[str], Tuple[bool, float]]
MaximizerPriorAccessor = Callable[[str, ArchetypeID], Tuple[float, float]]
CascadeTierAccessor = Callable[[str, str], Optional[str]]


class CellFeaturesAggregator:
    """Stateful aggregator with cached references to substrate
    accessors. Constructed once per process; called many times per
    bid stream.

    Constructor takes substrate accessors as keyword args — makes
    testing via dependency injection straightforward, avoids
    global-import side-effects.
    """

    def __init__(
        self,
        *,
        archetype_accessor: ArchetypeAccessor,
        posture_accessor: PostureAccessor,
        journey_accessor: JourneyAccessor,
        priming_accessor: PrimingAccessor,
        mindstate_accessor: MindstateAccessor,
        cohort_accessor: CohortAccessor,
        maximizer_prior_accessor: MaximizerPriorAccessor,
        cascade_tier_accessor: Optional[CascadeTierAccessor] = None,
        enable_timing: bool = False,
    ):
        self._archetype = archetype_accessor
        self._posture = posture_accessor
        self._journey = journey_accessor
        self._priming = priming_accessor
        self._mindstate = mindstate_accessor
        self._cohort = cohort_accessor
        self._maximizer = maximizer_prior_accessor
        self._cascade_tier = cascade_tier_accessor
        self._enable_timing = enable_timing

    def aggregate(
        self,
        buyer_id: str,
        url_hash: str,
    ) -> CellFeatureSet:
        """Aggregate the full feature set for one bid event.

        Args:
            buyer_id: StackAdapt buyer postback identifier
            url_hash: hash of the page URL the bid is for

        Returns:
            CellFeatureSet with all substrate fields populated
            (or safe defaults where individual fetches failed).

        Bid-time latency: target <8ms p99 over realistic substrate
        loads.

        Fail-soft: never raises. Substrate fetch failures are
        absorbed via per-source defaults.
        """
        archetype = self._fetch_with_default(
            lambda: self._archetype(buyer_id),
            ArchetypeID.PRAGMATIST,  # neutral default
        )
        posture = self._fetch_with_default(
            lambda: self._posture(url_hash),
            "INFORMATION_FORAGING",  # neutral default
        )
        journey = self._fetch_with_default(
            lambda: self._journey(buyer_id),
            ConversionStage.UNAWARE,  # neutral default
        )

        priming = self._fetch_with_default(
            lambda: self._priming(url_hash),
            None,
        )
        regulatory_focus = self._extract_regulatory_focus(priming)
        valence = float(getattr(priming, "valence", 0.0) or 0.0) if priming else 0.0
        arousal = float(getattr(priming, "arousal", 0.5) or 0.5) if priming else 0.5
        cognitive_load = (
            float(getattr(priming, "cognitive_load_estimate", 0.5) or 0.5)
            if priming else 0.5
        )
        pkm_activation = (
            float(getattr(priming, "persuasion_knowledge_activation", 0.0) or 0.0)
            if priming else 0.0
        )
        # Confidence may live in priming.confidence_per_dimension dict
        # (PagePrimingSignature pattern) OR as a top-level attribute.
        pkm_confidence = self._extract_pkm_confidence(priming)
        activated_frames = self._extract_activated_frames(priming)

        mindstate = self._fetch_with_default(
            lambda: self._mindstate(buyer_id, url_hash),
            None,
        )
        fomo = (
            float(getattr(mindstate, "fomo_score", 0.0) or 0.0)
            if mindstate else 0.0
        )
        psych_own = (
            float(getattr(mindstate, "psych_ownership_proxy", 0.0) or 0.0)
            if mindstate else 0.0
        )
        depletion = (
            float(getattr(mindstate, "depletion_proxy", 0.0) or 0.0)
            if mindstate else 0.0
        )
        session_position = (
            float(getattr(mindstate, "session_position_seconds", 0.0) or 0.0)
            if mindstate else 0.0
        )
        browsing_momentum = (
            float(getattr(mindstate, "browsing_momentum", 0.5) or 0.5)
            if mindstate else 0.5
        )

        comp_flag, comp_conf = self._fetch_with_default(
            lambda: self._cohort(buyer_id),
            (False, 0.5),
        )

        max_mean, max_strength = self._fetch_with_default(
            lambda: self._maximizer(buyer_id, archetype),
            (0.5, 10.0),
        )

        cascade_tier: Optional[str] = None
        if self._cascade_tier is not None:
            cascade_tier = self._fetch_with_default(
                lambda: self._cascade_tier(buyer_id, url_hash),
                None,
            )

        quadrant = compute_valence_arousal_quadrant(valence, arousal)
        cell_id = self._fetch_with_default(
            lambda: construct_cell_id(
                archetype=archetype,
                posture=posture,
                conversion_stage=journey,
                regulatory_focus=regulatory_focus,
                valence=valence,
                arousal=arousal,
            ),
            f"{archetype.value.upper()}_PARENT_FALLBACK",
        )

        aggregated_at = (
            datetime.now(timezone.utc).isoformat()
            if self._enable_timing else None
        )

        return CellFeatureSet(
            cell_id=cell_id,
            archetype=archetype,
            posture=posture,
            journey=journey,
            regulatory_focus=regulatory_focus,
            valence_arousal=quadrant,
            valence=valence,
            arousal=arousal,
            cognitive_load_estimate=cognitive_load,
            persuasion_knowledge_activation=pkm_activation,
            confidence_persuasion_knowledge=pkm_confidence,
            activated_frames=frozenset(activated_frames),
            fomo_score=fomo,
            psych_ownership_proxy=psych_own,
            depletion_proxy=depletion,
            session_position_seconds=session_position,
            browsing_momentum=browsing_momentum,
            compensatory_consumption_pattern=comp_flag,
            compensatory_detection_confidence=comp_conf,
            maximizer_tendency_posterior_mean=max_mean,
            maximizer_tendency_posterior_strength=max_strength,
            cascade_attentional_posture=cascade_tier,
            aggregated_at=aggregated_at,
        )

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _fetch_with_default(fetch_fn, default_value):
        """Fail-soft wrapper. Any exception → default."""
        try:
            return fetch_fn()
        except Exception:  # noqa: BLE001
            return default_value

    @staticmethod
    def _extract_regulatory_focus(priming) -> RegulatoryFocus:
        if priming is None:
            return RegulatoryFocus.NEUTRAL
        raw = getattr(priming, "regulatory_focus_priming", "neutral")
        try:
            return RegulatoryFocus(raw)
        except ValueError:
            return RegulatoryFocus.NEUTRAL

    @staticmethod
    def _extract_pkm_confidence(priming) -> float:
        """Persuasion-knowledge confidence may live as attribute or
        in confidence_per_dimension dict (PagePrimingSignature pattern
        from B / S6-prep.2)."""
        if priming is None:
            return 0.5
        # Direct attribute (some signature variants).
        direct = getattr(priming, "confidence_persuasion_knowledge", None)
        if isinstance(direct, (int, float)):
            return float(direct)
        # PagePrimingSignature dict pattern.
        dim_dict = getattr(priming, "confidence_per_dimension", None)
        if isinstance(dim_dict, dict):
            value = dim_dict.get("persuasion_knowledge_activation")
            if isinstance(value, (int, float)):
                return float(value)
        return 0.5

    @staticmethod
    def _extract_activated_frames(priming):
        if priming is None:
            return ()
        frames = getattr(priming, "activated_frames", ())
        if frames is None:
            return ()
        return tuple(frames)


# ============================================================================
# Default-aggregator factory for production wiring
# ============================================================================

def default_aggregator() -> CellFeaturesAggregator:
    """Construct a CellFeaturesAggregator wired with safe-default
    accessors that return neutral values.

    This factory is intentionally minimal — it exists so the bilateral
    cascade integration block can import a working aggregator without
    knowing about the substrate accessor wiring details. Each accessor
    is replaceable by the cascade caller (or by tests via the
    constructor injection path).

    Production callers may construct their own aggregator with real
    accessors wired to per_user_posterior_modulation, posture_classifier,
    journey state machine, priming Feature Store cascade, mindstate
    cache, graph_cache.get_cohort_compensatory_flag, etc.
    """
    return CellFeaturesAggregator(
        archetype_accessor=lambda buyer_id: ArchetypeID.PRAGMATIST,
        posture_accessor=lambda url_hash: "INFORMATION_FORAGING",
        journey_accessor=lambda buyer_id: ConversionStage.UNAWARE,
        priming_accessor=lambda url_hash: None,
        mindstate_accessor=lambda buyer_id, url_hash: None,
        cohort_accessor=lambda buyer_id: (False, 0.5),
        maximizer_prior_accessor=lambda buyer_id, arch: (0.5, 10.0),
        cascade_tier_accessor=None,
        enable_timing=False,
    )
