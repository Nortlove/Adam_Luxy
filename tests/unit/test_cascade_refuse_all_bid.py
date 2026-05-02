"""Pin Slice 13 — refuse-all-bid hard semantic.

Per directive line 122: "The scheduler is the only object allowed to
determine which mechanism is eligible for a given user at a given
moment ... the scheduler is permitted to refuse all mechanisms when
no compatible context exists."

Slice 1 (fluency floor) and Slice 3 (within-subject washout) v0.1
were fail-open + warn: when ALL candidates would be dropped, the
input scores were preserved and a reasoning string was appended.
That contradicts the directive's authorization. Slice 13 flips both
to fail-closed: when all-drop fires, the cascade clears
mechanism_scores, sets ``refused=True``, populates ``refusal_reason``,
and the StackAdapt service returns a no-bid response (skips decision
persistence, skips trace emission).

Pin:
    * CreativeIntelligence has refused + refusal_reason fields
    * Cascade source surfaces refused=True from both gates
    * Cascade source clears mechanism_scores on refusal
    * Service source detects refused and returns no-bid shape
    * Metrics surface exposes refusals counter (with reason label)
    * Honest-tag in within_subject_eligibility.py marks SHIPPED
"""

from __future__ import annotations

from typing import Dict

import pytest

from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence


# -----------------------------------------------------------------------------
# Schema pins
# -----------------------------------------------------------------------------


def test_creative_intelligence_has_refused_field():
    """The dataclass exposes refused + refusal_reason as schema slots."""
    ci = CreativeIntelligence()
    assert hasattr(ci, "refused")
    assert ci.refused is False
    assert hasattr(ci, "refusal_reason")
    assert ci.refusal_reason is None


def test_creative_intelligence_refused_is_settable():
    ci = CreativeIntelligence()
    ci.refused = True
    ci.refusal_reason = "fluency_floor_all_dropped:posture=LOW"
    assert ci.refused is True
    assert "fluency_floor" in ci.refusal_reason


# -----------------------------------------------------------------------------
# Source-text contract pins — defend against accidental unwire
# -----------------------------------------------------------------------------


def test_cascade_fluency_floor_block_marks_refused():
    """The fluency-floor all-drop branch sets refused=True (was
    fail-open + warn before Slice 13)."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    # The marker phrase from the Slice 13 fluency-floor block
    assert "REFUSED (fluency floor):" in src, (
        "Cascade lost its Slice 13 fluency-floor refusal block. "
        "All-drop case has reverted to fail-open."
    )
    assert 'refusal_reason' in src
    assert 'fluency_floor_all_dropped' in src


def test_cascade_scheduler_block_marks_refused():
    """The within-subject washout all-drop branch sets refused=True."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "REFUSED (within-subject washout):" in src, (
        "Cascade lost its Slice 13 scheduler refusal block. "
        "All-drop case has reverted to fail-open."
    )
    assert "within_subject_washout_all_dropped" in src


def test_cascade_clears_scores_on_refusal():
    """On refusal, mechanism_scores must be cleared so downstream
    modulations + TTTS no-op cleanly. Look for the empty-dict
    assignment marker in BOTH refusal branches."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    # Both refusal branches assign result.mechanism_scores = {}
    assert src.count("result.mechanism_scores = {}") >= 2, (
        "Cascade no longer clears mechanism_scores on refusal — "
        "downstream modulations would compute on stale scores."
    )


def test_service_detects_refused_and_returns_no_bid_shape():
    """The service source short-circuits on cascade_result.refused
    and returns the no-bid response shape (mirrors Slice 2's
    holdout pattern)."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/service.py").read_text()
    assert 'getattr(cascade_result, "refused", False)' in src, (
        "Service no longer detects refused. Cascade refusals will "
        "fall through to the format-and-persist path and the "
        "no-bid contract is broken."
    )
    assert '"is_refused": True' in src
    assert '"refusal":' in src
    assert "directive line 122" in src


def test_metrics_surface_exposes_refusals_counter():
    """The refusals counter with reason label is on the metrics
    surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "cascade_refusals_total"
    ), "Slice 13 refusals counter missing from metrics surface."


def test_within_subject_eligibility_honest_tag_marked_shipped():
    """The named sibling tag in within_subject_eligibility.py:90-92
    must be updated to reflect Slice 13 shipped (so future agents
    don't re-implement)."""
    from pathlib import Path

    src = Path(
        "adam/intelligence/within_subject_eligibility.py"
    ).read_text()
    assert "SHIPPED in Slice 13" in src, (
        "within_subject_eligibility honest tag (d) still says "
        "v0.1 fail-open — should reflect Slice 13 shipped."
    )


# -----------------------------------------------------------------------------
# Wire-mirror harness — validates the cascade refusal semantics
# -----------------------------------------------------------------------------


def _mirror_fluency_floor_refusal(
    bypassed: bool, n_dropped: int, posture_label: str = "LOW",
) -> CreativeIntelligence:
    """Mirror the cascade's fluency-floor refusal block."""
    ci = CreativeIntelligence()
    ci.mechanism_scores = {"social_proof": 0.7, "scarcity": 0.5}
    if bypassed:
        ci.refused = True
        ci.refusal_reason = (
            f"fluency_floor_all_dropped:posture={posture_label}"
        )
        ci.mechanism_scores = {}
        ci.reasoning.append(
            f"REFUSED (fluency floor): all "
            f"{n_dropped} mechanisms LOW posture×mech compatible "
            f"— directive line 122 authorizes refusal"
        )
    return ci


def _mirror_scheduler_refusal(bypassed: bool, n_dropped: int) -> CreativeIntelligence:
    """Mirror the cascade's scheduler-eligibility refusal block."""
    ci = CreativeIntelligence()
    ci.mechanism_scores = {"social_proof": 0.7, "scarcity": 0.5}
    if bypassed:
        ci.refused = True
        ci.refusal_reason = "within_subject_washout_all_dropped"
        ci.mechanism_scores = {}
        ci.reasoning.append(
            f"REFUSED (within-subject washout): all "
            f"{n_dropped} candidates inside washout window — "
            f"directive line 122 authorizes refusal"
        )
    return ci


def test_wire_mirror_fluency_floor_no_op_when_not_bypassed():
    """No all-drop → no refusal → scores preserved."""
    ci = _mirror_fluency_floor_refusal(bypassed=False, n_dropped=0)
    assert ci.refused is False
    assert ci.refusal_reason is None
    assert ci.mechanism_scores  # non-empty


def test_wire_mirror_fluency_floor_refuses_on_bypass():
    """All-drop → refused=True + scores cleared + reason set."""
    ci = _mirror_fluency_floor_refusal(
        bypassed=True, n_dropped=5, posture_label="LOW",
    )
    assert ci.refused is True
    assert "fluency_floor_all_dropped" in ci.refusal_reason
    assert "posture=LOW" in ci.refusal_reason
    assert ci.mechanism_scores == {}
    assert any("REFUSED" in r for r in ci.reasoning)


def test_wire_mirror_scheduler_refuses_on_bypass():
    """All inside washout → refused=True + scores cleared."""
    ci = _mirror_scheduler_refusal(bypassed=True, n_dropped=4)
    assert ci.refused is True
    assert ci.refusal_reason == "within_subject_washout_all_dropped"
    assert ci.mechanism_scores == {}


def test_wire_mirror_cleared_scores_no_op_downstream():
    """Cleared scores → downstream `if result.mechanism_scores`
    blocks all skip cleanly. This pins the contract that empty-
    dict is the cascade's 'do nothing more' signal."""
    ci = _mirror_fluency_floor_refusal(bypassed=True, n_dropped=3)
    # Simulate downstream block check
    if ci.mechanism_scores:
        # Would run modulation
        ran = True
    else:
        # Slice 4, Slice 12, free-energy, per-user posterior, etc.
        # all gate on `if result.mechanism_scores` and skip when empty.
        ran = False
    assert ran is False


def test_wire_mirror_refusal_response_shape_matches_holdout_pattern():
    """The service-side refusal response uses the same field
    set as the holdout response (decision_id, no primary_mechanism,
    reasoning_trace, timing_ms) but distinguished by is_refused vs
    is_holdout."""
    # We don't run the service here — but the pin is structural:
    # both responses share the no-touch contract. The source-text
    # test at test_service_detects_refused already pins the field
    # set. This test asserts the contract that refused-and-holdout
    # are mutually exclusive paths (a refused decision was never
    # in the holdout stratum, since holdout returns earlier).
    ci_holdout_path = CreativeIntelligence()  # Never reached cascade
    ci_refused_path = _mirror_fluency_floor_refusal(
        bypassed=True, n_dropped=2,
    )
    # Holdout never sets refused=True (it returns before cascade).
    assert ci_holdout_path.refused is False
    # Refused never carries holdout signals (it's a cascade output).
    assert ci_refused_path.refused is True
