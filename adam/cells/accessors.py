"""W.1 production accessor wirings for CellFeaturesAggregator.

Per W.0 audit findings (commit 2cef8d3) and W.1 slice scope. This
module provides the 5 substrate accessors classified as direct-call,
lightweight-adapter, or coordinator-wrapper:

    cohort_accessor       — (a) direct-call to F.2 sibling accessor
    posture_accessor      — (b) adapter for URLPostureClassifier
    priming_accessor      — (b) sync-only adapter (skips async L2)
    cascade_tier_accessor — (b) adapter composing PageIntelligenceCache
                              .lookup + categorize_posture
    journey_accessor      — (c) coordinator wrapping JourneyTracking-
                              Service._journeys (sync) +
                              to_conversion_stage mapping

The 2 build-the-accessor cases (archetype, maximizer_prior) are
W.2's scope. Mindstate is deferred to M.0/M.1+ per Q20.

Q21 discipline: NO `asyncio.run` in the bid hot path. The priming
and journey adapters use SYNC-ONLY paths — reading from in-memory
caches that the source modules already maintain (_l1 LRU on
PagePrimingSignatureStore; _journeys dict on JourneyTrackingService).
The async paths (L2 Redis on priming, async cache backend on
journey) are NOT touched. Real-data fire rate at bid time is
proportional to how warm the sync caches are. The async backends
can populate the sync caches out-of-band (background warm-up loop
is future work; not in W.1 scope).

Q22 discipline: each accessor target sub-1.5ms p99. Aggregate
budget revised from <8ms to 12-15ms acceptable.

Q23 discipline: each accessor handles cold-start by returning
S6.2's neutral default (UNAWARE / INFORMATION_FORAGING / None /
(False, 0.5)) AT THE WRAPPER SEAM. Source modules' cold-start
behavior is shielded from S6.2's contract.

Note on private-attribute access: `make_priming_accessor` and
`make_journey_accessor` reach into `_l1` / `_journeys` on the
respective source modules. This is read-only access mirroring
the source modules' own internal patterns. Cleaner pattern (sync
method on each source module) is deferred to follow-up.
"""
import logging
from typing import Optional, Tuple

from adam.cells.taxonomy import ConversionStage

logger = logging.getLogger(__name__)


# ============================================================================
# (a) Direct-call: cohort_accessor
# ============================================================================

def make_cohort_accessor(graph_cache):
    """Direct-call binding to GraphIntelligenceCache
    .get_cohort_compensatory_flag.

    Per F.2 (commit 1c49a75): get_cohort_compensatory_flag
    returns (False, 0.50) for unknown buyers — matches S6.2's
    neutral-default contract exactly. Direct closure binding.
    """
    def cohort_accessor(buyer_id: str) -> Tuple[bool, float]:
        try:
            return graph_cache.get_cohort_compensatory_flag(buyer_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("cohort_accessor fallback for %s: %s", buyer_id, exc)
            return (False, 0.50)
    return cohort_accessor


# ============================================================================
# (b) Lightweight adapter: posture_accessor
# ============================================================================

def make_posture_accessor(classifier):
    """Adapter for URLPostureClassifier.predict.

    Source signature per W.0 audit Pass 2:
        URLPostureClassifier.predict(urls: List[str]) -> List[str]
    S6.2 expects:
        posture_accessor(url_hash: str) -> str

    Adapter handles: List wrapping, scalar extraction, fail-soft
    cold-start to FIVE_CLASS_POSTURES default INFORMATION_FORAGING.
    Unfit classifier (raises RuntimeError("Call fit() first")) → fail-soft.
    """
    def posture_accessor(url_hash: str) -> str:
        try:
            preds = classifier.predict([url_hash])
            if preds and preds[0]:
                return preds[0]
            return "INFORMATION_FORAGING"
        except Exception as exc:  # noqa: BLE001
            logger.debug("posture_accessor fallback for %s: %s", url_hash, exc)
            return "INFORMATION_FORAGING"
    return posture_accessor


# ============================================================================
# (b) Lightweight adapter: priming_accessor (sync-only path)
# ============================================================================

def make_priming_accessor(feature_store):
    """Sync-only adapter for PagePrimingSignatureStore.

    Source signature per W.0 audit Pass 4:
        async PagePrimingSignatureStore.get(url_hash) -> PagePrimingSignature
    S6.2 expects (sync):
        priming_accessor(url_hash: str) -> PagePrimingSignature | None

    Per Q21 (no asyncio.run in hot path): read SYNC paths only —
    L1 in-memory LRU (sync dict access) and L3 sync Memcached
    backend. Skip the async L2 Redis tier. Reaches into
    feature_store._l1 / feature_store._l3 read-only — mirrors the
    source module's own internal cascade order.

    Cold-miss returns neutral_signature (matches source module's
    cold-miss contract).
    """
    from adam.priming.signature import (
        PagePrimingSignature, neutral_signature,
    )

    def priming_accessor(url_hash: str):
        if not url_hash:
            return None
        try:
            # L1 (sync LRU)
            l1 = getattr(feature_store, "_l1", None)
            if l1 is not None:
                sig = l1.get(url_hash)
                if sig is not None:
                    return sig

            # L3 (sync Memcached)
            l3 = getattr(feature_store, "_l3", None)
            if l3 is not None:
                row = l3.get(url_hash)
                if row:
                    return PagePrimingSignature.from_feature_store_row(row)

            # Cold miss → neutral fallback (matches source module
            # contract; never returns None on miss).
            return neutral_signature(url_hash)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "priming_accessor fallback for %s: %s", url_hash, exc,
            )
            return None
    return priming_accessor


# ============================================================================
# (b) Lightweight adapter: cascade_tier_accessor
# ============================================================================

def make_cascade_tier_accessor(page_intel_cache):
    """Adapter composing PageIntelligenceCache.lookup with
    categorize_posture.

    Source signatures per W.0 audit Pass 8:
        PageIntelligenceCache.lookup(page_url) -> Optional[PagePsychologicalProfile]
        categorize_posture(posture_float, posture_confidence) -> str
    S6.2 expects:
        cascade_tier_accessor(buyer_id, url_hash) -> Optional[str]

    Returns one of {blend_compatible, vigilance_activating, neutral,
    unknown} per S6.2 Pass C orthogonality finding (4-class
    attentional posture, NOT the 5-class FIVE_CLASS_POSTURES).
    """
    from adam.intelligence.page_attentional_posture_substrate import (
        categorize_posture,
    )

    def cascade_tier_accessor(buyer_id: str, url_hash: str) -> Optional[str]:
        if not url_hash:
            return None
        try:
            profile = page_intel_cache.lookup(url_hash)
            if profile is None:
                return None
            posture_float = float(
                getattr(profile, "attentional_posture", 0.0) or 0.0
            )
            posture_conf = float(
                getattr(profile, "attentional_posture_confidence", 0.0)
                or 0.0
            )
            return categorize_posture(posture_float, posture_conf)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "cascade_tier_accessor fallback for %s: %s",
                url_hash, exc,
            )
            return None
    return cascade_tier_accessor


# ============================================================================
# (c) Coordinator wrapper: journey_accessor
# ============================================================================

JOURNEY_DEFAULT_CATEGORY = "__bid_default__"
"""Q23 = (i) sentinel adjudication: bid-time has no campaign-
category context to thread to journey_storage.get_journey. Use a
sentinel that always misses → falls through to UNAWARE per S6.2's
neutral-default contract. Real category-threading wiring is
follow-up work."""


def make_journey_accessor(
    journey_service,
    default_category: str = JOURNEY_DEFAULT_CATEGORY,
):
    """Coordinator wrapper for JourneyTrackingService.

    Source signature per W.0 audit Pass 3:
        async JourneyTrackingService.get_journey(user_id, category)
            -> Optional[UserJourney]
    S6.2 expects (sync):
        journey_accessor(buyer_id: str) -> ConversionStage

    Three divergences resolved:
      (i) async → sync: use the sync `_journeys` in-memory dict
          (the source module's own L1) and skip the async cache
          fallback. Per Q21 (no asyncio.run in hot path).
      (ii) (user_id, category) → (buyer_id): use category sentinel
           per Q23. Until category-threading lands, journeys
           keyed under the sentinel never populate, so the
           wrapper effectively returns ConversionStage.UNAWARE
           always. Wiring exists for future use.
      (iii) UserJourney → ConversionStage: extract
            current_state.stage and map via to_conversion_stage
            (returns str), then coerce to ConversionStage enum.
    """
    from adam.user.journey.models import to_conversion_stage

    def journey_accessor(buyer_id: str) -> ConversionStage:
        if not buyer_id:
            return ConversionStage.UNAWARE
        try:
            key = f"{buyer_id}:{default_category}"
            journeys = getattr(journey_service, "_journeys", None)
            if journeys is None:
                return ConversionStage.UNAWARE
            journey = journeys.get(key)
            if journey is None:
                return ConversionStage.UNAWARE
            stage_str = to_conversion_stage(journey.current_state.stage)
            return ConversionStage(stage_str)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "journey_accessor fallback for %s: %s", buyer_id, exc,
            )
            return ConversionStage.UNAWARE
    return journey_accessor
