"""Pin Slice 3 cascade wire — within-subject scheduler eligibility filter.

Audit Tier 1 #3: ``adam/retargeting/scheduler.py`` (415 lines,
ABAB/RAR/SMART + washout table) had zero callers in
run_bilateral_cascade. Steps 4 (schedule check) + 10 (carryover) of
the directive's 14-step pipeline were absent. Per directive line 122,
the within-subject scheduler is the only object allowed to determine
which mechanism is eligible at a given moment.

This test pins the wire:
    * The cascade source imports the eligibility primitive
    * The cascade source uses decision_cache.recent_touches_for_buyer
    * The metrics surface exposes both scheduler counters
    * A wire-mirror harness exercises drop / bypass / cold-buyer paths
    * Threshold inheritance from washout_hours_for is preserved
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

import pytest

from adam.intelligence.within_subject_eligibility import (
    apply_within_subject_eligibility,
)
from adam.retargeting.scheduler import washout_hours_for


# -----------------------------------------------------------------------------
# Source-text contract pins
# -----------------------------------------------------------------------------


def test_cascade_imports_eligibility_primitive():
    """Cascade source must reference the eligibility primitive."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert (
        "from adam.intelligence.within_subject_eligibility import"
        in src
    ), (
        "Cascade lost its import of within_subject_eligibility. The "
        "directive's Step 4 (within-subject schedule check) is missing."
    )
    assert "apply_within_subject_eligibility" in src


def test_cascade_uses_decision_cache_touch_history_adapter():
    """The cascade reads touch history via decision_cache adapter."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "recent_touches_for_buyer" in src, (
        "Cascade no longer reads recent touch history — eligibility "
        "filter has no input source."
    )


def test_metrics_surface_exposes_scheduler_counters():
    """Both scheduler counters present on metrics surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "cascade_scheduler_eligibility_drops_total"
    ), "Slice 3 drops counter missing from metrics surface."
    assert hasattr(
        metrics, "cascade_scheduler_no_eligible_total"
    ), "Slice 3 no-eligible counter missing from metrics surface."


# -----------------------------------------------------------------------------
# Wire-mirror harness — isolates the in-cascade behavior
# -----------------------------------------------------------------------------


def _mirror_cascade_scheduler_block(
    mechanism_scores: Dict[str, float],
    touch_history: Dict[str, float],
    last_touched: Optional[str],
) -> Dict[str, float]:
    """Mirror the cascade block: read touch history, apply filter,
    bypass on all-drop, return filtered scores."""
    if not mechanism_scores or not touch_history:
        return mechanism_scores
    elig = apply_within_subject_eligibility(
        mechanism_scores=mechanism_scores,
        user_touch_history=touch_history,
        last_touched_mechanism=last_touched,
    )
    if elig.bypassed:
        return mechanism_scores  # all-drop preserves input v0.1
    return elig.filtered_scores


def test_wire_drops_inside_washout():
    """Cascade-side drop semantic — inside-washout candidate removed."""
    floor = washout_hours_for("social_proof")
    sc_floor = washout_hours_for("scarcity")
    history = {
        "social_proof": floor - 1.0,    # inside → drop
        "scarcity": sc_floor + 5.0,     # outside → keep
    }
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    out = _mirror_cascade_scheduler_block(
        mechanism_scores=scores,
        touch_history=history,
        last_touched=None,
    )
    assert "social_proof" not in out
    assert "scarcity" in out


def test_wire_cold_buyer_pass_through():
    """No history → cascade does not invoke the filter (early-out)."""
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    out = _mirror_cascade_scheduler_block(
        mechanism_scores=scores,
        touch_history={},
        last_touched=None,
    )
    assert out is scores


def test_wire_all_inside_washout_bypassed(caplog):
    """All-inside-washout → bypassed → input intact + WARN."""
    floor = washout_hours_for("social_proof")
    sc_floor = washout_hours_for("scarcity")
    history = {
        "social_proof": floor - 1.0,
        "scarcity": sc_floor - 1.0,
    }
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    with caplog.at_level(logging.WARNING):
        out = _mirror_cascade_scheduler_block(
            mechanism_scores=scores,
            touch_history=history,
            last_touched=None,
        )
    assert out is scores
    assert "inside washout" in caplog.text.lower()


def test_wire_threshold_inherits_from_scheduler():
    """Default thresholds come from washout_hours_for — not hardcoded."""
    # Both candidates 1h short of social_proof's washout
    sp_floor = washout_hours_for("social_proof")
    history = {"social_proof": sp_floor - 0.1}
    scores = {"social_proof": 0.7}
    out = _mirror_cascade_scheduler_block(
        mechanism_scores=scores,
        touch_history=history,
        last_touched=None,
    )
    # All dropped → bypass returns scores intact
    assert out is scores

    # Now well past the washout
    history = {"social_proof": sp_floor + 100.0}
    out = _mirror_cascade_scheduler_block(
        mechanism_scores=scores,
        touch_history=history,
        last_touched=None,
    )
    # Above washout → unchanged scores returned (filter is no-op on
    # eligibility check that passes; pass-through equals input)
    assert out == scores


# -----------------------------------------------------------------------------
# Counter behavior pin — same labels chain as the cascade calls
# -----------------------------------------------------------------------------


def test_counter_inc_chain_works():
    """Counter access chain (no labels for these counters)."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    metrics.cascade_scheduler_eligibility_drops_total.inc(2)
    metrics.cascade_scheduler_no_eligible_total.inc()
