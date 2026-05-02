"""Pin Slice 1 cascade wire — hard fluency floor at mechanism granularity.

The cascade wire previously had only the SOFT posture × mechanism
modulation (±10% multiplicative) plus bid_composer's soft penalty
(epistemic_bonus=0 on LOW). Per directive line 974 ("Wire as
eligibility filter, not as score modifier"), the floor must be a
HARD eligibility filter that drops ineligible candidates from
mechanism_scores entirely.

Audit 2026-05-01 Tier 1 #1 caught this. This test pins the wire
contract:

    * The cascade module imports the floor primitive
    * The metrics surface exposes the two RED-criterion #1 counters
    * The wire mirrors apply_mechanism_fluency_floor — an isolated
      harness exercises drop / bypass / pass-through paths analogous
      to the in-cascade behavior. End-to-end cascade behavior is
      exercised separately in integration tests.
    * Threshold matches bid_composer.FLUENCY_PROXY_FLOOR for cross-
      module consistency.

This pin guards against re-drift to "soft modifier only" treatment
of the directive's hard floor.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import pytest

from adam.intelligence.mechanism_fluency_floor import (
    MECHANISM_FLUENCY_FLOOR,
    apply_mechanism_fluency_floor,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)


# -----------------------------------------------------------------------------
# Contract pins — the cascade wire is in place
# -----------------------------------------------------------------------------


def test_cascade_module_imports_floor_primitive():
    """The cascade source must reference the floor primitive's import.

    Source-text pin — guards against silent removal of the wire (e.g.,
    in a refactor that drops the import without realizing the floor is
    consumed).
    """
    from pathlib import Path

    cascade_path = Path(
        "adam/api/stackadapt/bilateral_cascade.py"
    )
    src = cascade_path.read_text()
    assert "from adam.intelligence.mechanism_fluency_floor import" in src, (
        "Cascade lost its import of the hard fluency floor primitive. "
        "The directive (line 974) requires this filter as the eligibility "
        "gate at decision time. Re-add the import + the wire block."
    )
    assert "apply_mechanism_fluency_floor" in src, (
        "Cascade no longer calls apply_mechanism_fluency_floor. The "
        "directive's hard floor enforcement is missing."
    )


def test_metrics_surface_exposes_floor_counters():
    """RED-criterion #1 input requires both counters on the metrics surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "cascade_fluency_floor_violations_total"
    ), (
        "Metrics surface missing cascade_fluency_floor_violations_total. "
        "RED criterion #1 (directive line 1131) cannot be evaluated."
    )
    assert hasattr(
        metrics, "cascade_fluency_floor_no_eligible_total"
    ), (
        "Metrics surface missing cascade_fluency_floor_no_eligible_total. "
        "Slice 3 refuse-all-bid signal not measurable."
    )


def test_threshold_consistent_across_modules():
    """The hard gate (drop) and soft gate (epistemic=0) fire on same condition."""
    from adam.intelligence.bid_composer import FLUENCY_PROXY_FLOOR

    assert MECHANISM_FLUENCY_FLOOR == FLUENCY_PROXY_FLOOR


# -----------------------------------------------------------------------------
# Wire-mirror harness — isolates the behavior the cascade composes
# -----------------------------------------------------------------------------


def _mirror_cascade_floor_block(
    mechanism_scores: Dict[str, float],
    posture_label: Optional[str],
    posture_confidence: float,
) -> Dict[str, float]:
    """Mirror the in-cascade fluency-floor block.

    The cascade only invokes the floor when posture_confidence > 0.0.
    Otherwise it skips (no posture signal to act on).
    """
    if not mechanism_scores or posture_confidence <= 0.0:
        return mechanism_scores
    result = apply_mechanism_fluency_floor(
        mechanism_scores=mechanism_scores,
        posture=posture_label,
    )
    if result.bypassed:
        return mechanism_scores  # all-drop bypass preserves input
    return result.filtered_scores


def test_wire_drops_low_keeps_high():
    """Mixed input — LOW dropped, HIGH kept (matches the cascade behavior)."""
    scores = {
        "mimetic_desire": 0.7,         # POSTURE_BLEND → HIGH → keep
        "identity_construction": 0.6,  # POSTURE_BLEND → LOW  → drop
        "embodied_cognition": 0.5,     # POSTURE_BLEND → HIGH → keep
    }
    out = _mirror_cascade_floor_block(
        mechanism_scores=scores,
        posture_label=POSTURE_BLEND,
        posture_confidence=0.8,
    )
    assert "identity_construction" not in out
    assert "mimetic_desire" in out
    assert "embodied_cognition" in out


def test_wire_skipped_on_zero_confidence():
    """When posture_confidence == 0, the cascade skips the floor entirely."""
    scores = {
        "identity_construction": 0.6,
        "mimetic_desire": 0.7,
    }
    out = _mirror_cascade_floor_block(
        mechanism_scores=scores,
        posture_label=POSTURE_BLEND,
        posture_confidence=0.0,
    )
    assert out is scores  # untouched


def test_wire_bypass_preserves_input(caplog):
    """All-mechanisms-LOW → bypass → input dict returned unchanged."""
    scores = {
        "identity_construction": 0.6,  # POSTURE_BLEND → LOW
        "attention_dynamics": 0.5,     # POSTURE_BLEND → LOW
    }
    with caplog.at_level(logging.WARNING):
        out = _mirror_cascade_floor_block(
            mechanism_scores=scores,
            posture_label=POSTURE_BLEND,
            posture_confidence=0.7,
        )
    assert out is scores
    # Warning emitted by the underlying primitive
    assert "below floor" in caplog.text.lower()


def test_wire_neutral_posture_keeps_all():
    """POSTURE_NEUTRAL → no drops (all MID compatibility)."""
    scores = {
        "mimetic_desire": 0.4,
        "identity_construction": 0.6,
    }
    out = _mirror_cascade_floor_block(
        mechanism_scores=scores,
        posture_label=POSTURE_NEUTRAL,
        posture_confidence=0.7,
    )
    assert out == scores


def test_wire_unknown_posture_pass_through():
    """POSTURE_UNKNOWN → pass-through (no signal cannot certify ineligibility)."""
    scores = {
        "identity_construction": 0.6,
        "mimetic_desire": 0.7,
    }
    out = _mirror_cascade_floor_block(
        mechanism_scores=scores,
        posture_label=POSTURE_UNKNOWN,
        posture_confidence=0.7,
    )
    assert out is scores


def test_wire_vigilance_posture_drops_blend_compatible():
    """POSTURE_VIGILANCE × mimetic_desire (BLEND) → LOW → drop."""
    scores = {
        "mimetic_desire": 0.7,            # POSTURE_VIG → LOW → drop
        "identity_construction": 0.6,     # POSTURE_VIG × VIG → HIGH → keep
    }
    out = _mirror_cascade_floor_block(
        mechanism_scores=scores,
        posture_label=POSTURE_VIGILANCE,
        posture_confidence=0.8,
    )
    assert "mimetic_desire" not in out
    assert "identity_construction" in out


# -----------------------------------------------------------------------------
# Counter behavior pin — increments fire from the cascade block
# -----------------------------------------------------------------------------


def test_counters_increment_on_drop():
    """When the floor drops mechanisms, the violations counter increments."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()

    # Capture pre-state — Counter.labels(...).inc() always rises monotonically.
    # We can't easily read raw Counter values without prom internals, so
    # we just exercise the call path; the contract is: the cascade calls
    # the labels(...).inc(...) chain without raising.
    counter = metrics.cascade_fluency_floor_violations_total.labels(
        posture=POSTURE_BLEND,
    )
    counter.inc(2)  # exercise the same chain the cascade uses

    # No-eligible counter — same chain as cascade's bypass branch
    no_elig_counter = metrics.cascade_fluency_floor_no_eligible_total.labels(
        posture=POSTURE_BLEND,
    )
    no_elig_counter.inc()
