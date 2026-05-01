# =============================================================================
# Spine #9 — Kelly-Fraction Bid Sizing Under Posterior Uncertainty
# Location: adam/intelligence/kelly_bid_sizing.py
# =============================================================================
"""Fractional Kelly bid sizing with winner's-curse shading + pacing.

Closes directive Spine #9 (lines 295-313) + Phase 4 deliverable line
1021-1024:

    "Kelly-fraction bid sizing (Spine #9):
       - Quarter-Kelly default with calibration.
       - Winner's-curse shading per supply path.
       - Pacing-modifier integration."

WHY THIS EXISTS
---------------

Per directive line 299: "Flat CPM bids are dishonest about uncertainty.
The Kelly criterion is the optimal growth-rate position size; fractional
Kelly trades growth rate for drawdown control. Quarter-Kelly delivers
~70% of optimal growth at far less drawdown risk — the right trade-off
for a friendly pilot where blowing up the budget is far costlier than
slightly underbidding."

Composes with Spine #8 (epistemic bid bonus, shipped e73f4c1) to give
the directive's full dual-control bid_value formulation:

    bid_value(a | i, c) = pragmatic(a | i, c) + epistemic(a | i, c)
                          ↑                      ↑
                          this slice             Spine #8

Where pragmatic = quarter-Kelly × (winner's-curse shading) × (pacing).

KELLY-CRITERION MATH
--------------------

For a binary outcome with expected gain μ and variance σ² (the "edge"),
the full-Kelly fraction of the bankroll to bet is:

    f* = E[edge] / Var[edge] = μ / σ²        (continuous-payoff form)

Quarter-Kelly: f = 0.25 × f*. Half-Kelly: f = 0.50 × f*. The directive
defaults to quarter-Kelly (line 297) and notes upgrade to half-Kelly
"only after stable per-user posteriors emerge."

Why fractional rather than full Kelly: full-Kelly maximizes long-run
geometric growth but is variance-aggressive — drawdowns can exceed
50% of bankroll temporarily. Quarter-Kelly delivers ~70% of optimal
growth (MacLean, Thorp, Ziemba 2010) at quadratically reduced drawdown
risk. For a friendly pilot where budget-blow-up is far costlier than
slight underbidding, quarter-Kelly is the right default.

Edge inputs from upstream:
    posterior_edge     = E[reward | served] − E[reward | not served]
    posterior_variance = Var[reward | served]

Both come from the per-user BONG posterior (or downstream conversion-
prediction layer); the Kelly primitive accepts them as scalars and
does NOT recompute the posterior.

Zero / negative edge → zero bid (no positive expected value, no bid).
Zero variance → zero bid (defensive: if there's no posterior
uncertainty, we cannot reason about Kelly; the bidder should not
size on a degenerate edge).

WINNER'S-CURSE SHADING
----------------------

Per directive line 308: "On open-exchange inventory, shade the Kelly
bid by an estimate of the winner's-curse penalty: the bid that wins
is on average above the second-highest bidder's value."

The shading factor is per supply path. The directive (line 306)
explicitly distinguishes three:
  - open exchange:   highest winner's-curse penalty (random competitors)
  - PMP:             moderate (curated pool, partial-information)
  - deal-ID:         minimal (negotiated, transparent)

A14 calibration-pending defaults err on the conservative side
(more shading) — pilot data will calibrate per-path empirically per
the directive's "estimate the shading factor empirically per supply
path" instruction.

PACING-MODIFIER INTEGRATION
---------------------------

Per directive line 310 + 1024: pacing layer "Allocate budget across
(cohort, mechanism) cells proportional to max(0, μ_lift) · (1 / σ_lift)
· κ with κ the fractional Kelly fraction." The full formula needs
cohort-conditional Whittle-index allocation from Spine #7 (BLOCKED on
Loop B per the session handoff). Until cohorts ship, pacing_modifier
is a per-call scalar parameter; the bidder sets it from whatever
upstream pacing logic exists today.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations:
    - Kelly criterion: Kelly 1956 ("A New Interpretation of Information
      Rate"), the foundational result on optimal-growth position sizing
      under known edge.
    - Fractional Kelly variants: MacLean, Thorp, Ziemba 2010 ("Good
      and Bad Properties of the Kelly Criterion"), the canonical
      reference for quarter-Kelly's growth-vs-drawdown trade-off.
    - Winner's-curse: market-microstructure literature (Capen, Clapp,
      Campbell 1971 "Competitive Bidding in High-Risk Situations" is
      the foundational result; Milgrom & Weber 1982 for the modern
      formulation).

(b) Tests pin: Kelly_full = edge/variance; quarter-Kelly = 0.25 ×
    full; half-Kelly = 0.50 × full; zero / negative edge → zero
    bid; zero variance → zero bid (defensive); per-supply-path
    shading bands; pacing_modifier multiplies; KellyBidResult shape;
    dual-control composition with Spine #8 EpistemicBonusResult
    pinned via test (bid_value = pragmatic + epistemic).

(c) calibration_pending=True. Quarter-Kelly default and per-path
    shading factors are conservative pre-pilot. LUXY pilot data will
    calibrate via empirical clearing-price distributions per supply
    path. A14 flag: SPINE_9_KELLY_DEFAULTS_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Auction clearing distribution per supply path. The directive
      (line 306) calls for this estimated empirically per supply
      path. Until that estimator ships, the winner's-curse shading
      uses A14 conservative-band defaults (more shading = lower
      bid = safer). The shading factors here are scalars; the
      richer "shade by clearing-distribution estimate" composes
      once the estimator ships.
    * Cohort-conditional pacing per directive line 310. Spine #7
      (cohort discovery) is BLOCKED on Loop B per the session
      handoff. The pacing_modifier parameter accepts whatever
      upstream pacing logic supplies; the formal Whittle-index +
      restless-bandit allocation composes when cohorts ship.
    * Half-Kelly upgrade trigger ("after stable per-user posteriors
      emerge" per directive line 297). The constants for both
      quarters and halves are exposed; the trigger logic that
      promotes from quarter to half is its own slice — needs a
      definition of "stable per-user posterior" that is itself
      pilot-calibrated.
    * Bid composer wrapping Spine #8 + Spine #9 into one call.
      Per the discipline rule against premature abstraction, the
      composition is a one-line addition at the call site
      (bid_value = pragmatic.bid_value + epistemic.bonus). The
      composition pattern is pinned by test in
      tests/unit/test_kelly_bid_sizing.py rather than wrapped in
      a single-line helper.
    * Wiring into the cascade producer — the AlternativeCandidate
      .bid_value field on the DecisionTrace schema (ca03336) is
      the consumer slot. Producer wiring composes with the cascade
      producer (ab10f26) once a typed bid composer is wired in.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


# =============================================================================
# Supply paths (directive line 306-308)
# =============================================================================


class SupplyPath(str, Enum):
    """Programmatic supply paths with distinct winner's-curse profiles.

    Per directive line 306-308: open exchange has highest winner's-
    curse penalty (random competitors); PMP is moderate (curated
    pool); deal-ID is minimal (negotiated).
    """

    OPEN_EXCHANGE = "open_exchange"
    PMP = "private_marketplace"
    DEAL_ID = "deal_id"


# =============================================================================
# A14 calibration-pending defaults
# =============================================================================

# A14 SPINE_9_KELLY_DEFAULTS_PILOT_PENDING

DEFAULT_KELLY_FRACTION_QUARTER: float = 0.25
"""Per directive line 297: quarter-Kelly default. ~70% of optimal
growth at quadratically reduced drawdown risk (MacLean/Thorp/
Ziemba 2010)."""

DEFAULT_KELLY_FRACTION_HALF: float = 0.50
"""Half-Kelly upgrade. Per directive line 297: 'upgrade to half-
Kelly only after stable per-user posteriors emerge'. The trigger
logic for promoting a user from quarter to half is its own slice."""

# Per-supply-path shading factors (multiplicative on the Kelly bid).
# 1.0 = no shade; 0.85 = 15% shade. Conservative defaults — pilot
# data will calibrate empirically per the directive's instruction.
DEFAULT_WINNERS_CURSE_SHADING: Dict[SupplyPath, float] = {
    SupplyPath.OPEN_EXCHANGE: 0.85,  # ~15% shade — random competition
    SupplyPath.PMP:           0.92,  # ~8% shade  — curated pool
    SupplyPath.DEAL_ID:       1.00,  # no shade   — negotiated transparent
}

# Fallback shading when supply path is unrecognized.
_FALLBACK_SHADING: float = 0.80


# =============================================================================
# Result type
# =============================================================================


@dataclass(frozen=True)
class KellyBidResult:
    """Outcome of one Kelly-bid computation.

    ``bid_value``: the final pragmatic bid value to combine with
        Spine #8's epistemic bonus per the directive's dual-control
        formulation: bid = pragmatic + epistemic.
    ``raw_kelly_bid``: fractional-Kelly bid before shading + pacing.
    ``shaded_kelly_bid``: after winner's-curse shading, before pacing.
    ``kelly_fraction``: the fraction applied (0.25 = quarter, etc.).
    ``posterior_edge``: input — E[reward | served].
    ``posterior_variance``: input — Var[reward | served].
    ``supply_path``: which supply path's shading was used.
    ``rationale``: short label for diagnostic surfaces. Examples:
        "computed", "no_edge" (edge ≤ 0), "no_uncertainty" (variance
        ≤ 0), "computed_quarter_kelly".
    """

    bid_value: float
    raw_kelly_bid: float
    shaded_kelly_bid: float
    kelly_fraction: float
    posterior_edge: float
    posterior_variance: float
    supply_path: SupplyPath
    rationale: str


# =============================================================================
# Kelly math
# =============================================================================


def kelly_full_fraction(
    posterior_edge: float,
    posterior_variance: float,
) -> float:
    """Full Kelly fraction = E[edge] / Var[edge].

    Returns 0.0 when:
      * posterior_edge ≤ 0 (no positive expected value, no bid)
      * posterior_variance ≤ 0 (degenerate posterior — defensive)
      * either input is non-finite (NaN / Inf)
    """
    if not math.isfinite(posterior_edge) or not math.isfinite(posterior_variance):
        return 0.0
    if posterior_edge <= 0.0 or posterior_variance <= 0.0:
        return 0.0
    return posterior_edge / posterior_variance


def fractional_kelly_bid(
    posterior_edge: float,
    posterior_variance: float,
    *,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION_QUARTER,
    bankroll_unit: float = 1.0,
) -> float:
    """Fractional-Kelly bid before winner's-curse shading or pacing.

    Args:
        posterior_edge: E[reward | served].
        posterior_variance: Var[reward | served].
        kelly_fraction: 0.25 (quarter, default) / 0.50 (half) / etc.
        bankroll_unit: per-impression budget unit. Default 1.0 — the
            bid is in the same units as the edge. Caller scales by
            the actual budget unit it works in.

    Returns: kelly_fraction × kelly_full × bankroll_unit. 0.0 if
    Kelly is degenerate (zero / negative edge, zero variance).
    """
    f_full = kelly_full_fraction(posterior_edge, posterior_variance)
    if f_full == 0.0:
        return 0.0
    return float(kelly_fraction) * f_full * float(bankroll_unit)


# =============================================================================
# Winner's-curse shading
# =============================================================================


def winners_curse_shading_factor(supply_path: SupplyPath) -> float:
    """Return the shading factor for the supply path.

    Unknown supply paths fall back to the conservative
    _FALLBACK_SHADING (0.80) — when the path is unrecognized, we
    cannot confidently estimate the curse penalty, so we shade more.
    """
    if not isinstance(supply_path, SupplyPath):
        # Allow callers to pass strings for convenience
        try:
            supply_path = SupplyPath(supply_path)
        except ValueError:
            logger.debug(
                "winners_curse_shading_factor: unknown path %r → fallback",
                supply_path,
            )
            return _FALLBACK_SHADING
    return DEFAULT_WINNERS_CURSE_SHADING.get(supply_path, _FALLBACK_SHADING)


# =============================================================================
# Composed pragmatic bid
# =============================================================================


def compute_pragmatic_bid(
    posterior_edge: float,
    posterior_variance: float,
    supply_path: SupplyPath,
    *,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION_QUARTER,
    bankroll_unit: float = 1.0,
    pacing_modifier: float = 1.0,
) -> KellyBidResult:
    """Compose: fractional Kelly × winner's-curse shading × pacing.

    The full pragmatic bid value:

        raw_kelly = fractional_kelly_bid(edge, variance, kelly_fraction)
        shading   = winners_curse_shading_factor(supply_path)
        shaded    = raw_kelly × shading
        bid_value = shaded × max(0, pacing_modifier)

    Pacing modifier is clamped at 0 to prevent negative bids — the
    bidder may pause cells via pacing_modifier=0 but cannot bid
    negatively.

    Returns a frozen KellyBidResult with the final bid_value and the
    intermediate quantities for audit / chain_of_reasoning rendering.
    """
    raw_kelly = fractional_kelly_bid(
        posterior_edge, posterior_variance,
        kelly_fraction=kelly_fraction,
        bankroll_unit=bankroll_unit,
    )

    # Determine rationale for the early-exit cases
    if not math.isfinite(posterior_edge) or not math.isfinite(posterior_variance):
        rationale = "non_finite_input"
    elif posterior_edge <= 0.0:
        rationale = "no_edge"
    elif posterior_variance <= 0.0:
        rationale = "no_uncertainty"
    else:
        rationale = (
            f"kelly={kelly_fraction:.2f}"
        )

    if raw_kelly == 0.0:
        return KellyBidResult(
            bid_value=0.0,
            raw_kelly_bid=0.0,
            shaded_kelly_bid=0.0,
            kelly_fraction=float(kelly_fraction),
            posterior_edge=float(posterior_edge),
            posterior_variance=float(posterior_variance),
            supply_path=supply_path if isinstance(supply_path, SupplyPath)
                        else SupplyPath.OPEN_EXCHANGE,
            rationale=rationale,
        )

    shading = winners_curse_shading_factor(supply_path)
    shaded = raw_kelly * shading

    pacing_clamped = max(0.0, float(pacing_modifier))
    bid_value = shaded * pacing_clamped

    sp_obj = (
        supply_path if isinstance(supply_path, SupplyPath)
        else SupplyPath(supply_path)
        if str(supply_path) in {p.value for p in SupplyPath}
        else SupplyPath.OPEN_EXCHANGE
    )

    return KellyBidResult(
        bid_value=bid_value,
        raw_kelly_bid=raw_kelly,
        shaded_kelly_bid=shaded,
        kelly_fraction=float(kelly_fraction),
        posterior_edge=float(posterior_edge),
        posterior_variance=float(posterior_variance),
        supply_path=sp_obj,
        rationale=rationale,
    )
