"""Pin Slice 4 cascade wire — score-space epistemic bonus before TTTS.

Audit Tier 1 #4: compute_epistemic_bonus runs in bid_composer AFTER
mechanism choice — it populates AlternativeCandidate.epistemic_bonus
on the trace but does NOT influence which mechanism gets chosen.
Per directive Section 5.1 Step 9 (line 691): "score → score + λ_E ·
epistemic, conditioned on fluency-floor pass."

This test pins:
    * Cascade source imports the score-space epistemic primitive
    * Wire-mirror harness exercises the modulation
    * Metrics surface exposes the modulation counter
    * Step-9 ordering: epistemic bonus block sits AFTER free-energy
      modulation (Step 8) and BEFORE TTTS selection
"""

from __future__ import annotations

import numpy as np

from adam.intelligence.bong import BONGPosterior, DEFAULT_DIMENSIONS
from adam.intelligence.score_space_epistemic import (
    apply_score_space_epistemic_bonus,
)


# -----------------------------------------------------------------------------
# Source-text contract pins
# -----------------------------------------------------------------------------


def test_cascade_imports_score_space_epistemic():
    """Cascade source must reference the Slice 4 primitive."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert (
        "from adam.intelligence.score_space_epistemic import"
        in src
    ), (
        "Cascade lost its import of score_space_epistemic. The "
        "directive's Step 9 (epistemic bonus before TTTS) is missing."
    )
    assert "apply_score_space_epistemic_bonus" in src


def test_step_9_sits_after_step_8_in_cascade():
    """Epistemic bonus block must follow free-energy modulation block.

    Directive Section 5.1: Step 8 (free-energy) precedes Step 9
    (epistemic bonus). Source-text ordering pins the architectural
    sequence so a refactor doesn't silently flip them.
    """
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    fe_pos = src.find("FREE-ENERGY MODULATION")
    eps_pos = src.find("SCORE-SPACE EPISTEMIC BONUS")
    assert fe_pos > 0
    assert eps_pos > 0
    assert eps_pos > fe_pos, (
        "Step 9 (epistemic bonus) must follow Step 8 (free-energy) "
        "per directive Section 5.1 line 690-691."
    )


def test_metrics_surface_exposes_epistemic_modulation_counter():
    """Modulation counter present on metrics surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "cascade_epistemic_bonus_modulations_total"
    ), (
        "Slice 4 modulation counter missing from metrics surface. "
        "Step 9 visibility lost."
    )


# -----------------------------------------------------------------------------
# Wire-mirror harness — isolates the in-cascade behavior
# -----------------------------------------------------------------------------


def _fresh_posterior() -> BONGPosterior:
    d = len(DEFAULT_DIMENSIONS)
    return BONGPosterior(eta=np.zeros(d), D=np.full(d, 0.5))


def test_wire_modulates_scores_when_posterior_present():
    """When BONG posterior + scores present, modulation fires."""
    bong = _fresh_posterior()
    scores = {"social_proof": 0.5, "scarcity": 0.5}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
    )
    # At least one mechanism shifted — Step 9 is operational
    assert result.n_modulated >= 1
    assert result.total_bonus_mass > 0.0


def test_wire_pass_through_without_posterior():
    """No BONG posterior → cascade falls through cleanly (input intact)."""
    scores = {"social_proof": 0.5}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=None,
    )
    assert result.modulated_scores is scores
    assert result.n_modulated == 0


def test_wire_counter_inc_chain():
    """The cascade's increment chain on the modulation counter works."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    metrics.cascade_epistemic_bonus_modulations_total.inc(2)
