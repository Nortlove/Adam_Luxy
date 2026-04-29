# =============================================================================
# ADAM Spine #9 — Kelly-Fraction Bid Sizing Under Posterior Uncertainty
# Location: adam/intelligence/spine/spine_9_kelly_bid.py
# =============================================================================

"""Kelly-fraction bid sizing — posterior-uncertainty-aware position sizing.

PER DIRECTIVE SECTION 2 (Spine #9) + SECTION 5.

Replace flat CPM bids with a fractional Kelly position size keyed to
the posterior edge over the auction's clearing distribution. Use
QUARTER-KELLY by default for safety; upgrade to half-Kelly only after
stable per-user posteriors emerge.

WHY THIS IS SPINE

Per directive: "Flat CPM bids are dishonest about uncertainty. The
Kelly criterion is the optimal growth-rate position size; fractional
Kelly trades growth rate for drawdown control. Quarter-Kelly delivers
~70% of optimal growth at far less drawdown risk — the right
trade-off for a friendly pilot where blowing up the budget is far
costlier than slightly underbidding."

THE MATH

  Kelly fraction f* (per-bet, log-utility growth-rate optimum):
    f* = edge / odds
       = (p · b - q) / b
  where:
    p = prob(win) [for ad-tech: prob of conversion under serve]
    q = 1 - p
    b = odds (net payoff per unit bet) [for ad-tech: ratio of expected
        reward to bid amount]
    edge = p·b - q (expected return per unit bet)

  Fractional Kelly: f = κ · f* with κ ∈ (0, 1].
    κ = 1.0 → full Kelly (max growth, max drawdown)
    κ = 0.5 → half-Kelly (~75% growth, ~50% drawdown variance)
    κ = 0.25 → quarter-Kelly (~70% growth, far less drawdown)

  Per directive: quarter-Kelly default; upgrade to half-Kelly only
  after stable per-user posteriors emerge.

WINNER'S-CURSE SHADING

Per directive Section 5: "On open-exchange inventory, shade the Kelly
bid by an estimate of the winner's-curse penalty: the bid that wins
is on average above the second-highest bidder's value. This is well-
documented in the auction-theory literature; estimate the shading
factor empirically per supply path."

Supply paths with low winner's-curse risk (PMP, Deal-ID): no shading
or minimal shading. Open-exchange: ~10-15% shading factor (calibration-
pending).

PACING LAYER

Per directive: "Allocate budget across (cohort, mechanism) cells
proportional to `max(0, μ_lift) · (1 / σ_lift) · κ` with κ the
fractional Kelly fraction; this is 'drawdown-aware, edge-adaptive
pacing.'"

DECISION-TIME CONSUMERS (Rule A check)

  - Orchestrator's bid response — reads computed bid value to send
    to StackAdapt
  - Spine #6 DecisionTrace records bid_value per decision
  - Pacing layer (this module's helpers) reads cohort posteriors to
    allocate budget across cells

Cognitive primitive at the serving path. NOT measurement.

THIS COMMIT SHIPS

    - kelly_fraction: closed-form Kelly-criterion calculation
    - fractional_kelly: applies κ to the Kelly fraction
    - winner_curse_shading: per-supply-path shading factor
    - compute_kelly_bid: end-to-end Kelly bid given posterior edge,
      auction clearing distribution, and supply path
    - drawdown_aware_pacing_weight: pacing layer per directive

REFERENCES

    Kelly 1956 — A New Interpretation of Information Rate.
    MacLean, Thorp, Ziemba 2010 — fractional Kelly variants and
        practical drawdown control.
    Market-microstructure winner's-curse literature.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration constants
# =============================================================================


# Per directive: "Use quarter-Kelly by default for safety."
DEFAULT_KELLY_FRACTION: float = 0.25  # Quarter-Kelly


# Half-Kelly upgrade threshold — number of per-user observations
# required before considering half-Kelly. Pilot-pending.
HALF_KELLY_OBSERVATIONS_THRESHOLD: int = 30


# Maximum bid as a fraction of expected reward — safety cap independent
# of Kelly. Prevents the bid from exceeding any reasonable bound even
# when the posterior is wildly optimistic.
MAX_BID_AS_FRACTION_OF_REWARD: float = 0.5


# =============================================================================
# Supply path enum + shading factors
# =============================================================================


class SupplyPath(str, Enum):
    """Supply paths with different winner's-curse profiles.

    OPEN_EXCHANGE: highest winner's-curse risk; second-price auction
        with many bidders; the winning bid is on average ~10-15%
        above the second-highest bid's value
    PMP: Private Marketplace; less competition, lower winner's-curse
    DEAL_ID: explicit deal with floor price; minimal winner's-curse
    DIRECT: direct buy; no winner's-curse
    """

    OPEN_EXCHANGE = "open_exchange"
    PMP = "pmp"
    DEAL_ID = "deal_id"
    DIRECT = "direct"


# Winner's-curse shading factor per supply path (calibration-pending).
WINNER_CURSE_SHADING: Dict[SupplyPath, float] = {
    SupplyPath.OPEN_EXCHANGE: 0.12,  # ~12% downward shading
    SupplyPath.PMP: 0.05,
    SupplyPath.DEAL_ID: 0.02,
    SupplyPath.DIRECT: 0.00,
}


def winner_curse_shading_factor(supply_path: SupplyPath) -> float:
    """Return the shading factor for a supply path. Default 0.0
    (no shading) for unknown paths."""
    return WINNER_CURSE_SHADING.get(supply_path, 0.0)


# =============================================================================
# Kelly-fraction calculation
# =============================================================================


def kelly_fraction(
    p_win: float,
    odds: float,
) -> float:
    """Compute the full Kelly-criterion fraction for a single bet.

    f* = (p · b - q) / b   where b = odds, q = 1 - p

    Returns 0.0 when edge is non-positive (no profitable bet).
    Returns 0.0 when odds is non-positive (degenerate).

    Args:
        p_win: probability of "winning" the bet — for ad-tech, the
            posterior probability of conversion conditional on serving
            this candidate
        odds: net payoff per unit bet (b in Kelly's notation) — for
            ad-tech, expected reward / bid_amount

    Returns: Kelly fraction in [0, 1] (clipped at 1).
    """
    if not 0.0 <= p_win <= 1.0:
        raise ValueError(f"p_win must be in [0, 1]; got {p_win}")
    if odds <= 0.0:
        return 0.0
    q = 1.0 - p_win
    edge = p_win * odds - q
    if edge <= 0.0:
        return 0.0
    f = edge / odds
    return min(1.0, max(0.0, f))


def fractional_kelly(
    p_win: float,
    odds: float,
    *,
    kelly_fraction_kappa: float = DEFAULT_KELLY_FRACTION,
) -> float:
    """Compute the fractional Kelly bet size: κ · f*.

    Per directive: quarter-Kelly default; upgrade to half-Kelly only
    after stable per-user posteriors emerge.

    Validates κ ∈ (0, 1].
    """
    if not 0.0 < kelly_fraction_kappa <= 1.0:
        raise ValueError(
            f"kelly_fraction_kappa must be in (0, 1]; "
            f"got {kelly_fraction_kappa}"
        )
    return kelly_fraction_kappa * kelly_fraction(p_win, odds)


# =============================================================================
# End-to-end Kelly bid
# =============================================================================


@dataclass(frozen=True)
class KellyBidResult:
    """Structured Kelly-bid result.

    Decomposed for the DecisionTrace + partner-facing audit.
    """

    bid_amount: float
    p_win: float
    odds: float
    kelly_fraction_full: float
    kelly_fraction_used: float  # κ · f*
    winner_curse_shading_applied: float
    supply_path: SupplyPath
    capped_by_max_fraction: bool


def compute_kelly_bid(
    p_win: float,
    expected_reward: float,
    auction_clearing_estimate: float,
    supply_path: SupplyPath = SupplyPath.OPEN_EXCHANGE,
    *,
    kelly_fraction_kappa: float = DEFAULT_KELLY_FRACTION,
    max_bid_fraction_of_reward: float = MAX_BID_AS_FRACTION_OF_REWARD,
) -> KellyBidResult:
    """Compute the Kelly bid for a candidate.

    Args:
        p_win: posterior probability of conversion under this serve
            (read from Spine #1 user posterior + cohort policy)
        expected_reward: posterior expected reward (revenue contribution)
            of a conversion under this candidate
        auction_clearing_estimate: estimated clearing price for the
            auction at this supply path (used to compute odds)
        supply_path: SupplyPath enum (drives winner's-curse shading)
        kelly_fraction_kappa: fractional Kelly factor (default quarter)
        max_bid_fraction_of_reward: safety cap on bid as fraction of
            expected_reward

    Returns KellyBidResult with structured decomposition.
    """
    if expected_reward <= 0.0 or auction_clearing_estimate <= 0.0:
        return KellyBidResult(
            bid_amount=0.0, p_win=p_win,
            odds=0.0, kelly_fraction_full=0.0, kelly_fraction_used=0.0,
            winner_curse_shading_applied=0.0,
            supply_path=supply_path, capped_by_max_fraction=False,
        )

    # Odds: net payoff per unit bet ≈ (expected_reward - clearing) / clearing
    # If we win at the clearing price, our profit is reward - clearing;
    # our investment is clearing.
    odds = max(0.0, (expected_reward - auction_clearing_estimate)
               / auction_clearing_estimate)

    # Full Kelly fraction
    f_full = kelly_fraction(p_win, odds)
    # Apply κ
    f_used = kelly_fraction_kappa * f_full

    # Bid = f_used · expected_reward (the fraction of "bankroll"
    # equivalent at the impression level). For ad-tech, bankroll ≈
    # expected_reward.
    bid = f_used * expected_reward

    # Apply winner's-curse shading.
    shading = winner_curse_shading_factor(supply_path)
    shaded_bid = bid * (1.0 - shading)

    # Cap at max_bid_fraction_of_reward.
    cap = max_bid_fraction_of_reward * expected_reward
    capped = shaded_bid > cap
    final = min(shaded_bid, cap)

    return KellyBidResult(
        bid_amount=max(0.0, final),
        p_win=p_win,
        odds=odds,
        kelly_fraction_full=f_full,
        kelly_fraction_used=f_used,
        winner_curse_shading_applied=shading,
        supply_path=supply_path,
        capped_by_max_fraction=capped,
    )


# =============================================================================
# Drawdown-aware edge-adaptive pacing
# =============================================================================


def drawdown_aware_pacing_weight(
    expected_lift_mean: float,
    expected_lift_stddev: float,
    *,
    kelly_fraction_kappa: float = DEFAULT_KELLY_FRACTION,
) -> float:
    """Compute the pacing weight for a (cohort, mechanism) cell.

    Per directive Section 5.3: "Allocate budget across (cohort,
    mechanism) cells proportional to `max(0, μ_lift) · (1 / σ_lift)
    · κ` with κ the fractional Kelly fraction; this is 'drawdown-
    aware, edge-adaptive pacing.'"

    Returns 0.0 when expected_lift_mean ≤ 0 (no profitable cell) or
    when stddev is non-positive (degenerate).
    """
    if expected_lift_mean <= 0.0:
        return 0.0
    if expected_lift_stddev <= 0.0:
        return 0.0
    if not 0.0 < kelly_fraction_kappa <= 1.0:
        raise ValueError(
            f"kelly_fraction_kappa must be in (0, 1]; "
            f"got {kelly_fraction_kappa}"
        )
    return expected_lift_mean * (1.0 / expected_lift_stddev) * kelly_fraction_kappa


def normalize_pacing_weights(
    weights: Dict[str, float],
) -> Dict[str, float]:
    """Normalize a dict of pacing weights so they sum to 1 (allocation
    proportions across cells).

    Returns empty dict for all-zero input.
    """
    total = sum(max(0.0, w) for w in weights.values())
    if total <= 0.0:
        return {k: 0.0 for k in weights}
    return {k: max(0.0, w) / total for k, w in weights.items()}


__all__ = [
    "DEFAULT_KELLY_FRACTION",
    "HALF_KELLY_OBSERVATIONS_THRESHOLD",
    "MAX_BID_AS_FRACTION_OF_REWARD",
    "KellyBidResult",
    "SupplyPath",
    "WINNER_CURSE_SHADING",
    "compute_kelly_bid",
    "drawdown_aware_pacing_weight",
    "fractional_kelly",
    "kelly_fraction",
    "normalize_pacing_weights",
    "winner_curse_shading_factor",
]
