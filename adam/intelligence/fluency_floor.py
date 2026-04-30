# =============================================================================
# Fluency Floor — Phase 2 hard eligibility filter for creative selection
# Location: adam/intelligence/fluency_floor.py
# =============================================================================
"""Hard eligibility filter on creative ↔ page fluency.

Closes directive Phase 2 line 974-976:

    "Fluency floor implementation (hard constraint, not optimization term):
       - Calibrate threshold against held-out labeled set (50–100 page-
         creative pairs).
       - Wire as eligibility filter, not as score modifier."

WHY THIS EXISTS
---------------

``compute_blend_fit(creative, page)`` returns a continuous alignment
score and a per-axis decomposition. The directive's discipline (line
974) makes the boundary explicit: at decision time, fluency is NOT a
soft score modifier that nudges ranking — it is a hard eligibility
filter. Creatives below the calibrated fluency threshold must be
excluded from selection entirely; they cannot win on other dimensions.

The selection-layer rationale: a creative that's a poor blend with
the page invokes vigilance / interrupts the user's attentional pattern
regardless of how well it matches the buyer's archetype × mechanism
profile. Foundation rule 11 (the fitness function IS the ethics):
the floor prevents the bandit from learning to exploit configurations
that grab attention rather than blend.

THIS SLICE
----------

Self-contained substrate. The primitive + the calibrator, both
ready for the first creative-selection call site to wire them in.

  * ``FluencyFloorVerdict`` — frozen dataclass: pass/fail, score,
    threshold, decomposition, reason.
  * ``passes_fluency_floor(creative, page, threshold)`` — single-pair
    decision; returns ``FluencyFloorVerdict``.
  * ``filter_creatives_by_fluency_floor(candidates, page, threshold)``
    — bulk eligibility filter; returns ``(eligible, rejected)`` so the
    caller can audit what was dropped.
  * ``calibrate_threshold(labeled_pairs, target_violation_rate)`` —
    threshold-from-data per directive line 975-976.

INTEGRATION PATTERN (named successor — NOT in this slice)
---------------------------------------------------------

    # Caller pre-derives bundles for each creative + page once,
    # then runs the eligibility filter before any ranking pass.
    eligible, rejected = filter_creatives_by_fluency_floor(
        candidates=[(creative_obj, derive_creative_bundle(creative_obj))
                    for creative_obj in candidate_creatives],
        page=page_bundle,
    )
    # Only `eligible` enters the ranker / bandit.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: confidence-weighted blend_fit primitive (existing module
    ``adam/intelligence/blend_fit.py``) operationalizes the attention-
    inversion principle from Foundation rule 11 (fitness function IS
    ethics) + the platform-core attention-inversion commitment
    (project_attention_inversion_platform_core.md). Threshold-from-
    data calibration follows the standard precision/recall ROC-cut
    pattern.

(b) Tests pin: pass/fail at threshold; verdict carries score +
    threshold + decomposition + reason; bulk filter returns
    (eligible, rejected) tuples preserving caller objects;
    calibration recovers a threshold that respects the configured
    violation rate; soft-fail on empty / degenerate decomposition;
    pathological labeled sets fall back to default threshold.

(c) calibration_pending=True. Threshold default 0.40 is a
    conservative slack default; LUXY pilot data will calibrate against
    a 50-100 hand-labeled page-creative held-out set per directive
    line 978 ("0.5–2% violation range"). A14 flag:
    PHASE_2_FLUENCY_FLOOR_THRESHOLD_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Five-class posture head (sentence-transformer + 300-500 hand-
      labeled URLs + auxiliary regression heads + active-learning
      loop) per directive line 967-969 — the floor primitive does not
      depend on this; it operates on already-derived bundle features.
    * Posture × mechanism compatibility prior matrix per directive
      line 970 — sibling slice; would compose with this one in the
      cascade.
    * Wiring into a specific creative-selection call site
      (wpp/iheart/cascade) — requires bundle-derivation pipeline
      from creative dicts and page atom_outputs, which is its own
      slice.
    * Empirical calibration of ``_BLEND_AXIS_WEIGHTS`` from pilot
      data (already flagged in ``a14_compromises.
      BLEND_FIT_WEIGHTS_UNVALIDATED``) — the floor does not depend on
      this calibration; it consumes whichever weights blend_fit
      currently uses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from adam.intelligence.blend_fit import (
    BlendFitDecomposition,
    CreativeFeatureBundle,
    compute_blend_fit,
)
from adam.intelligence.pages.claude_feature_scoring import PageFeatureBundle

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending threshold + violation rate
# =============================================================================

# A14 PHASE_2_FLUENCY_FLOOR_THRESHOLD_PILOT_PENDING
#
# Default conservative; below 0.40 effective blend_fit, a creative is
# considered to interrupt the user's attentional pattern with high
# enough probability that it should not enter the selection pool.
# LUXY pilot calibration against 50-100 labeled page-creative pairs
# will replace this default per directive line 975-976.
FLUENCY_FLOOR_THRESHOLD: float = 0.40

# Directive line 978 calibration target — violations in the held-out
# set should fall in [0.5%, 2%]. We default to the upper bound so the
# threshold is conservative when the labeled set is sparse.
DEFAULT_TARGET_VIOLATION_RATE: float = 0.02

# Floor on calibrated threshold to prevent runaway-low when the labeled
# set is degenerate (e.g., all "fluent" labels). Matches the
# pre-calibration default — calibration cannot drive the floor below
# the default by accident.
MIN_CALIBRATED_THRESHOLD: float = 0.10
# Ceiling — if calibration wants threshold above this, something is
# wrong with the labels (almost everything is non-fluent); cap and warn.
MAX_CALIBRATED_THRESHOLD: float = 0.95


# =============================================================================
# Verdict
# =============================================================================


@dataclass(frozen=True)
class FluencyFloorVerdict:
    """Outcome of a single fluency-floor decision.

    ``passed``: True iff ``score >= threshold``. The decision-time
    consumer routes pass=True creatives into the selection pool and
    drops pass=False creatives entirely.

    ``decomposition``: per-axis attribution from blend_fit; consumers
    that want to audit *why* a creative was dropped (which axis killed
    the score) read this rather than treating the verdict as a
    black-box.

    ``reason``: short human-readable label intended for diagnostic /
    dashboard surfaces. Examples: "below_threshold", "neutral_fallback",
    "passed".
    """

    passed: bool
    score: float
    threshold: float
    decomposition: Optional[BlendFitDecomposition]
    reason: str


@dataclass(frozen=True)
class CalibrationResult:
    """Outcome of ``calibrate_threshold``.

    ``threshold``: recommended floor (defaults if calibration failed).
    ``observed_violation_rate``: fraction of NOT-fluent labels that
        passed at the recommended threshold. Should be ≤ target when
        calibration succeeded.
    ``observed_rejection_rate_of_fluent``: fraction of fluent labels
        that were rejected at the recommended threshold. The cost of
        precision; reported for downstream cost-benefit decisions.
    ``status``: "calibrated" | "fallback_default" | "fallback_floor"
        | "fallback_ceiling" — describes which path produced the
        threshold.
    ``n_pairs``: count of labeled pairs consumed.
    """

    threshold: float
    observed_violation_rate: float
    observed_rejection_rate_of_fluent: float
    status: str
    n_pairs: int


# =============================================================================
# Single-pair decision
# =============================================================================


def passes_fluency_floor(
    creative: CreativeFeatureBundle,
    page: PageFeatureBundle,
    threshold: float = FLUENCY_FLOOR_THRESHOLD,
) -> FluencyFloorVerdict:
    """Hard eligibility decision on one (creative, page) pair.

    Returns a ``FluencyFloorVerdict``. The directive's discipline:
    use ``verdict.passed`` to gate inclusion in the selection pool —
    do NOT use ``verdict.score`` as a multiplier.

    Soft-fail discipline:
      * blend_fit raising → return verdict with passed=False, reason
        "blend_fit_failed". The honest default for a primitive that
        couldn't compute is rejection, NOT fall-through pass — the
        directive explicitly forbids falling through to "neutral pass"
        when fluency is meant to be a hard floor.
      * blend_fit returning the neutral 0.5 fallback (zero effective
        weight) → return verdict with passed=False, reason
        "neutral_fallback". Without information we cannot certify
        fluency, so we cannot pass.
    """
    try:
        score, decomposition = compute_blend_fit(creative, page)
    except Exception as exc:
        logger.warning("fluency floor — blend_fit raised: %s", exc)
        return FluencyFloorVerdict(
            passed=False,
            score=0.0,
            threshold=threshold,
            decomposition=None,
            reason="blend_fit_failed",
        )

    # Neutral fallback (zero effective weight) → cannot certify
    if decomposition is None or decomposition.total_effective_weight <= 0.0:
        return FluencyFloorVerdict(
            passed=False,
            score=score,
            threshold=threshold,
            decomposition=decomposition,
            reason="neutral_fallback",
        )

    if score >= threshold:
        return FluencyFloorVerdict(
            passed=True,
            score=score,
            threshold=threshold,
            decomposition=decomposition,
            reason="passed",
        )

    return FluencyFloorVerdict(
        passed=False,
        score=score,
        threshold=threshold,
        decomposition=decomposition,
        reason="below_threshold",
    )


# =============================================================================
# Bulk eligibility filter
# =============================================================================


def filter_creatives_by_fluency_floor(
    candidates: Iterable[Tuple[Any, CreativeFeatureBundle]],
    page: PageFeatureBundle,
    threshold: float = FLUENCY_FLOOR_THRESHOLD,
) -> Tuple[List[Tuple[Any, FluencyFloorVerdict]], List[Tuple[Any, FluencyFloorVerdict]]]:
    """Run ``passes_fluency_floor`` over a list of candidates.

    Args:
        candidates: iterable of ``(creative_obj, creative_bundle)``
            pairs. ``creative_obj`` is whatever the caller wants
            preserved (a dict, an ORM row, an ID) — this primitive does
            not unpack it. The ``creative_bundle`` carries the features
            blend_fit needs.
        page: ``PageFeatureBundle`` for the page context. One per
            decision moment (every candidate is scored against the
            same page).
        threshold: optional override of the default floor.

    Returns:
        ``(eligible, rejected)`` — both are lists of
        ``(creative_obj, verdict)`` tuples. Order within each list
        follows the input order.
    """
    eligible: List[Tuple[Any, FluencyFloorVerdict]] = []
    rejected: List[Tuple[Any, FluencyFloorVerdict]] = []

    for creative_obj, bundle in candidates:
        verdict = passes_fluency_floor(bundle, page, threshold=threshold)
        if verdict.passed:
            eligible.append((creative_obj, verdict))
        else:
            rejected.append((creative_obj, verdict))

    return eligible, rejected


# =============================================================================
# Calibration — threshold-from-data over labeled pairs
# =============================================================================


LabeledPair = Tuple[CreativeFeatureBundle, PageFeatureBundle, bool]
"""(creative, page, fluent) tuple. ``fluent=True`` means a human
labeler judged the creative-on-page pair as a continuous, non-
disruptive blend. ``fluent=False`` means the pair interrupted the
attentional pattern."""


def calibrate_threshold(
    labeled_pairs: Sequence[LabeledPair],
    target_violation_rate: float = DEFAULT_TARGET_VIOLATION_RATE,
) -> CalibrationResult:
    """Find the lowest threshold whose violation rate respects the target.

    "Violation rate" = fraction of NOT-fluent labels that pass the
    threshold (false positives — disruptive creatives that escape the
    filter). The directive (line 978) targets [0.5%, 2%]; we default
    to 2%.

    Algorithm (standard threshold-from-data ROC cut):
      1. Score every labeled pair with blend_fit.
      2. Sort thresholds by candidate cut points (the unique scores
         + a small ε above each, plus 0.0 and 1.0 endpoints).
      3. For each candidate, count not-fluent-pass-through and
         fluent-rejection. Pick the LOWEST threshold whose
         not-fluent-pass-through ≤ target.
      4. Clip to ``[MIN_CALIBRATED_THRESHOLD, MAX_CALIBRATED_THRESHOLD]``.

    Soft-fail behavior:
      * empty / degenerate labeled set → return default threshold +
        status="fallback_default".
      * blend_fit raises on a pair → that pair is dropped (logged); if
        all pairs drop, return fallback default.
      * No threshold satisfies the target (every threshold lets too
        many violations through) → return ceiling threshold +
        status="fallback_ceiling".
      * Threshold below floor after clipping → return floor +
        status="fallback_floor".
    """
    if not labeled_pairs:
        return CalibrationResult(
            threshold=FLUENCY_FLOOR_THRESHOLD,
            observed_violation_rate=0.0,
            observed_rejection_rate_of_fluent=0.0,
            status="fallback_default",
            n_pairs=0,
        )

    scored: List[Tuple[float, bool]] = []
    for creative_bundle, page_bundle, is_fluent in labeled_pairs:
        try:
            score, _ = compute_blend_fit(creative_bundle, page_bundle)
        except Exception as exc:
            logger.warning(
                "calibrate_threshold dropping pair (blend_fit raised): %s", exc,
            )
            continue
        scored.append((float(score), bool(is_fluent)))

    if not scored:
        return CalibrationResult(
            threshold=FLUENCY_FLOOR_THRESHOLD,
            observed_violation_rate=0.0,
            observed_rejection_rate_of_fluent=0.0,
            status="fallback_default",
            n_pairs=0,
        )

    n = len(scored)
    n_fluent = sum(1 for _, f in scored if f)
    n_not_fluent = n - n_fluent

    if n_not_fluent == 0 or n_fluent == 0:
        # Degenerate label distribution — calibration cannot separate.
        # Fall back to default; honestly tag.
        return CalibrationResult(
            threshold=FLUENCY_FLOOR_THRESHOLD,
            observed_violation_rate=(
                1.0 if n_not_fluent > 0 else 0.0
            ),
            observed_rejection_rate_of_fluent=0.0,
            status="fallback_default",
            n_pairs=n,
        )

    # Candidate thresholds: every unique score AND every unique score
    # plus a tiny ε. The +ε candidates are essential — without them,
    # "score >= threshold" can trap the calibrator at the wrong side of
    # equal-score ties, e.g., a clean-separable set with scores in
    # {0.05, 1.0} forces the algorithm to pick threshold=1.0 (only
    # candidate above 0.05 in the set) when threshold=0.5 would equally
    # satisfy the target. Adding 0.05+ε to the candidate set lets the
    # algorithm find the lowest threshold strictly above each not-fluent
    # cluster.
    sorted_unique_scores = sorted({s for s, _ in scored})
    eps = 1e-6
    candidate_thresholds = [0.0]
    for s in sorted_unique_scores:
        candidate_thresholds.append(s)
        candidate_thresholds.append(s + eps)
    candidate_thresholds.append(1.0)

    best_threshold: Optional[float] = None
    best_violation_rate: float = 1.0
    best_rejection_rate_of_fluent: float = 0.0

    for threshold in candidate_thresholds:
        not_fluent_pass = sum(
            1 for s, f in scored if (not f) and s >= threshold
        )
        fluent_reject = sum(
            1 for s, f in scored if f and s < threshold
        )
        violation_rate = not_fluent_pass / n_not_fluent
        rejection_rate_of_fluent = fluent_reject / n_fluent

        if violation_rate <= target_violation_rate:
            # Found a threshold that satisfies the target. Take the
            # LOWEST such threshold (minimizes fluent-rejection cost).
            if best_threshold is None or threshold < best_threshold:
                best_threshold = threshold
                best_violation_rate = violation_rate
                best_rejection_rate_of_fluent = rejection_rate_of_fluent

    if best_threshold is None:
        # No threshold satisfied the target — return ceiling, which is
        # the most conservative possible filter (lets nothing through
        # below the highest score).
        return CalibrationResult(
            threshold=MAX_CALIBRATED_THRESHOLD,
            observed_violation_rate=best_violation_rate,
            observed_rejection_rate_of_fluent=best_rejection_rate_of_fluent,
            status="fallback_ceiling",
            n_pairs=n,
        )

    if best_threshold < MIN_CALIBRATED_THRESHOLD:
        # Calibration wants below-floor — conservative-clip to floor
        # and re-measure rates at the clipped value.
        clipped = MIN_CALIBRATED_THRESHOLD
        not_fluent_pass = sum(
            1 for s, f in scored if (not f) and s >= clipped
        )
        fluent_reject = sum(
            1 for s, f in scored if f and s < clipped
        )
        return CalibrationResult(
            threshold=clipped,
            observed_violation_rate=not_fluent_pass / n_not_fluent,
            observed_rejection_rate_of_fluent=fluent_reject / n_fluent,
            status="fallback_floor",
            n_pairs=n,
        )

    if best_threshold > MAX_CALIBRATED_THRESHOLD:
        # Calibration wants above-ceiling — cap at ceiling and
        # re-measure rates. This happens when separable scores +
        # the +ε candidate logic land slightly above 1.0, or when the
        # only thresholds satisfying the target sit in (CEILING, 1.0].
        clipped = MAX_CALIBRATED_THRESHOLD
        not_fluent_pass = sum(
            1 for s, f in scored if (not f) and s >= clipped
        )
        fluent_reject = sum(
            1 for s, f in scored if f and s < clipped
        )
        return CalibrationResult(
            threshold=clipped,
            observed_violation_rate=not_fluent_pass / n_not_fluent,
            observed_rejection_rate_of_fluent=fluent_reject / n_fluent,
            status="fallback_ceiling",
            n_pairs=n,
        )

    return CalibrationResult(
        threshold=best_threshold,
        observed_violation_rate=best_violation_rate,
        observed_rejection_rate_of_fluent=best_rejection_rate_of_fluent,
        status="calibrated",
        n_pairs=n,
    )
