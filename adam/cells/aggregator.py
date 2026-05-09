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


# ============================================================================
# M.1 — aggregator-side fomo_score derivation (Q31 architectural simplification)
# ============================================================================
# Per M.0 audit (commit 9324f78): PageMindstateVector @property derivations
# never fire at bid time because PMV is never constructed in the bid path
# (extract_mindstate_vector lives in outcome_handler learning paths only).
# M.1 adds aggregator-side inline compute that bypasses the dead PMV path
# and produces identical values from the same logical inputs (Q31 two-path
# consistency invariant). C's PageMindstateVector.fomo_score @property
# remains for outcome_handler backward-compat.
#
# Constants mirror C's PageMindstateVector @property exactly
# (adam/retargeting/resonance/models.py:69-78). Pinned by an equivalence
# test for two-path consistency.

FOMO_REGULATORY_PROMOTION_MODIFIER: float = 1.2
FOMO_REGULATORY_PREVENTION_MODIFIER: float = 0.8
FOMO_REGULATORY_NEUTRAL_MODIFIER: float = 1.0
FOMO_SCARCITY_FRAME_NAME: str = "scarcity"


def compute_fomo_score(
    arousal: float,
    activated_frames,
    regulatory_focus_priming,
) -> float:
    """Compute FOMO score aggregator-side per Q31 adjudication.

    Mirrors C's PageMindstateVector.fomo_score @property
    (commit fd1a95a) but operates on inputs available at the
    bid-time aggregator seam (already-cached PagePrimingSignature
    values) rather than on PageMindstateVector fields that
    aren't constructed at bid time.

    Formula (identical to C's @property in computed value for
    matching logical inputs):

        fomo_score = arousal × scarcity_indicator × regulatory_modifier

    Where:
        arousal ∈ [0, 1] from PagePrimingSignature
        scarcity_indicator = 1.0 if FOMO_SCARCITY_FRAME_NAME ("scarcity")
                             in activated_frames else 0.0
        regulatory_modifier =
            1.2 if PROMOTION
            0.8 if PREVENTION
            1.0 otherwise (NEUTRAL or unknown)

    Result clipped to [0, 1].

    C-vs-M.1 input differences (do NOT affect computed value):
        C's @property reads self.scarcity_frame_present (a separate
        orchestrator-populated bool); M.1 derives the same bool by
        membership-checking "scarcity" in activated_frames (the
        canonical priming-side source per ContentProfiler
        MECHANISM_KEYWORDS top-5 per
        adam/platform/intelligence/content_profiler.py:35).

    Bid-time latency: <100μs per call (3 dict/comparison ops).

    Args:
        arousal: PagePrimingSignature.arousal ∈ [0, 1]
        activated_frames: PagePrimingSignature.activated_frames
            (tuple, list, frozenset, or other iterable of str).
            None → treated as empty (no scarcity contribution).
        regulatory_focus_priming: RegulatoryFocus enum value OR string
            ("promotion" / "prevention" / "neutral"). Anything not
            matching PROMOTION or PREVENTION → NEUTRAL modifier (1.0).
    """
    if activated_frames is None:
        scarcity_indicator = 0.0
    else:
        scarcity_indicator = (
            1.0 if FOMO_SCARCITY_FRAME_NAME in activated_frames
            else 0.0
        )

    # Handle both enum and string regulatory_focus_priming.
    reg_value = (
        regulatory_focus_priming.value
        if hasattr(regulatory_focus_priming, "value")
        else str(regulatory_focus_priming)
    )

    if reg_value == "promotion":
        modifier = FOMO_REGULATORY_PROMOTION_MODIFIER
    elif reg_value == "prevention":
        modifier = FOMO_REGULATORY_PREVENTION_MODIFIER
    else:
        modifier = FOMO_REGULATORY_NEUTRAL_MODIFIER

    raw = float(arousal) * scarcity_indicator * modifier
    return max(0.0, min(1.0, raw))


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
        # M.1: aggregator-side fomo_score per Q31 (bypass dead PMV
        # @property path). Falls back to mindstate.fomo_score if
        # mindstate is provided (preserves M.2/M.3 future wiring
        # path); otherwise computes inline from already-fetched
        # priming inputs.
        if mindstate is not None and getattr(mindstate, "fomo_score", None):
            fomo = float(mindstate.fomo_score)
        else:
            fomo = compute_fomo_score(
                arousal=arousal,
                activated_frames=activated_frames,
                regulatory_focus_priming=regulatory_focus,
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


# ============================================================================
# W.1 production_aggregator — wires 5 accessors per W.1 slice scope
# ============================================================================

def production_aggregator(
    *,
    graph_cache=None,
    posture_classifier=None,
    priming_store=None,
    page_intel_cache=None,
    journey_service=None,
    journey_default_category: str = "__bid_default__",
) -> CellFeaturesAggregator:
    """Build the W.1 production CellFeaturesAggregator.

    Wires 5 substrate accessors per W.1 scope:
        cohort       (a) direct-call to F.2 sibling accessor
        posture      (b) lightweight adapter for URLPostureClassifier
        priming      (b) lightweight adapter for PagePrimingSignatureStore
                          (sync paths only; skips async L2 per Q21)
        cascade_tier (b) lightweight adapter composing
                          PageIntelligenceCache + categorize_posture
        journey      (c) coordinator wrapper using sync _journeys dict
                          + to_conversion_stage mapping (Q23 sentinel
                          for category)

    The 2 build-the-accessor cases (archetype, maximizer_prior) and
    mindstate (deferred to M.0/M.1+ per Q20) remain at neutral
    defaults via S6.2 fail-soft pattern.

    Each accessor is fail-soft at construction — if its underlying
    source isn't available (no singleton, no instance provided),
    falls back to S6.2's neutral default lambda. Production
    deployments may pass real instances explicitly to activate
    specific wirings.

    Args:
        graph_cache: GraphIntelligenceCache instance. Defaults to
            get_graph_cache() singleton when available.
        posture_classifier: URLPostureClassifier instance. No
            singleton in repo; pass explicitly to activate posture
            wiring. Defaults to neutral-default lambda.
        priming_store: PagePrimingSignatureStore instance. No
            singleton in repo; pass explicitly to activate priming
            wiring. Defaults to neutral-default lambda.
        page_intel_cache: PageIntelligenceCache instance. Defaults
            to get_page_intelligence_cache() singleton when available.
        journey_service: JourneyTrackingService instance. Defaults
            to get_journey_tracking_service() singleton when
            available.
        journey_default_category: Sentinel category for journey
            lookups (per Q23 = (i)). Default sentinel never matches
            populated journeys, so journey accessor returns
            ConversionStage.UNAWARE until category-threading
            wiring lands.

    Returns:
        CellFeaturesAggregator with 5 accessors wired (or fail-
        soft defaults where underlying source unavailable) +
        2 W.2-deferred accessors at neutral defaults +
        mindstate at neutral default.
    """
    from adam.cells.accessors import (
        make_archetype_accessor,
        make_cascade_tier_accessor,
        make_cohort_accessor,
        make_journey_accessor,
        make_maximizer_prior_accessor,
        make_posture_accessor,
        make_priming_accessor,
    )

    # Try to fetch singletons when not explicitly provided.
    if graph_cache is None:
        try:
            from adam.api.stackadapt.graph_cache import get_graph_cache
            graph_cache = get_graph_cache()
        except Exception:  # noqa: BLE001
            graph_cache = None

    if page_intel_cache is None:
        try:
            from adam.intelligence.page_intelligence import (
                get_page_intelligence_cache,
            )
            page_intel_cache = get_page_intelligence_cache()
        except Exception:  # noqa: BLE001
            page_intel_cache = None

    if journey_service is None:
        try:
            from adam.user.journey.service import (
                get_journey_tracking_service,
            )
            journey_service = get_journey_tracking_service()
        except Exception:  # noqa: BLE001
            journey_service = None

    # Build accessors, falling back to neutral-default lambdas if
    # the underlying source isn't available.
    cohort_accessor_fn = (
        make_cohort_accessor(graph_cache)
        if graph_cache is not None
        else (lambda buyer_id: (False, 0.5))
    )
    posture_accessor_fn = (
        make_posture_accessor(posture_classifier)
        if posture_classifier is not None
        else (lambda url_hash: "INFORMATION_FORAGING")
    )
    priming_accessor_fn = (
        make_priming_accessor(priming_store)
        if priming_store is not None
        else (lambda url_hash: None)
    )
    cascade_tier_accessor_fn = (
        make_cascade_tier_accessor(page_intel_cache)
        if page_intel_cache is not None
        else None
    )
    journey_accessor_fn = (
        make_journey_accessor(journey_service, journey_default_category)
        if journey_service is not None
        else (lambda buyer_id: ConversionStage.UNAWARE)
    )

    # W.2c: archetype + maximizer_prior accessors read from
    # BuyerUncertaintyProfile via graph_cache.get_buyer_profile.
    # Both fall through to neutral defaults when graph_cache
    # unavailable (matches W.1's per-accessor fail-soft pattern).
    archetype_accessor_fn = (
        make_archetype_accessor(graph_cache)
        if graph_cache is not None
        else (lambda buyer_id: ArchetypeID.PRAGMATIST)
    )
    maximizer_prior_accessor_fn = (
        make_maximizer_prior_accessor(graph_cache)
        if graph_cache is not None
        else (lambda buyer_id, arch: (0.5, 10.0))
    )

    return CellFeaturesAggregator(
        archetype_accessor=archetype_accessor_fn,
        posture_accessor=posture_accessor_fn,
        journey_accessor=journey_accessor_fn,
        priming_accessor=priming_accessor_fn,
        mindstate_accessor=lambda buyer_id, url_hash: None,
        cohort_accessor=cohort_accessor_fn,
        maximizer_prior_accessor=maximizer_prior_accessor_fn,
        cascade_tier_accessor=cascade_tier_accessor_fn,
        enable_timing=False,
    )
