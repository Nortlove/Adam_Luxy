# =============================================================================
# Phase A → v3 interface seams
# Location: adam/intelligence/v3_interfaces.py
# =============================================================================
"""Protocol indirections + registries for the three Phase A components
that v3 Phase 1 will wrap with control-theoretic / pharmacokinetic
replacements.

Per the 2026-05-02 wrap-out handoff, v3 Phase 1 work-streams 1.D / 1.E /
1.F will partially or fully replace components Phase A has shipped:

  * 1.D  H∞ robust controller wrapping Kelly bid sizing (Slice 7).
  * 1.E  Funnel-MPC replacing the within-subject scheduler outer loop
         (Slice 3 + Slice 12).
  * 1.F  PK/PD model replacing the constant-table frequency-cap /
         washout (Slice 3 substrate via retargeting/scheduler.py).

Audit found the three components are exposed as top-level free functions
called directly by the cascade + emitter — there is no indirection point
where v3 wrappers can plug in without rewriting call sites. This module
introduces three protocol + default-implementation + registry triplets
so v3 wrappers can register a replacement implementation without touching
upstream callers.

THE PATTERN

For each replacement target, this module ships:
  1. A Protocol class defining the minimum interface.
  2. A default implementation that delegates to the existing Phase A
     function — contract-preserving (existing tests still pass).
  3. A module-level register / get accessor pair.

The cascade + emitter switch from direct function calls to
``get_active_*().method(...)``. The default registration matches today's
behavior exactly. v3 wrappers register a different implementation at
startup; no caller changes required.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: Phase A wrap-out handoff (2026-05-02 — interface
    stability discipline item) + named v3 work-streams 1.D / 1.E / 1.F.
    The Protocol pattern matches the existing
    ``goal_state_model.GoalStateModel`` Protocol used by Slice 17a
    free_energy_dual_eval (an established codebase pattern).

(b) Tests pin: each protocol has a default implementation that
    behaves identically to the pre-Slice-24 direct call (contract-
    preserving smoke tests); register / get round-trip works;
    re-registering replaces the active implementation; resetting
    restores defaults; per-protocol type pins.

(c) calibration_pending=False — pure interface refactor with
    contract-preserving defaults. No v3 wrappers shipped here.

(d) Honest tags — what is NOT in this slice (named successors):

    * v3 1.D HInfWrappedKellyBidComposer implementation. v3 Phase 1
      work-stream.
    * v3 1.E FunnelMPCCarryoverStrategy implementation. v3 Phase 1.
    * v3 1.F PKPDWashoutModel implementation. v3 Phase 1.
    * Registry persistence / multi-process registration. v0.1
      registries are in-process module-level globals; multi-pod
      deploy will need either a deployment-time hook or a
      configuration-driven loader. Sibling slice (parallel to the
      Persistent Redis snapshot multi-pod sibling).
    * Per-archetype / per-cohort routing of multiple registered
      implementations. v0.1 has ONE active impl per protocol.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# 1. BidComposer — v3 1.D wrap target
# =============================================================================


@runtime_checkable
class BidComposer(Protocol):
    """Pluggable bid composer. v3 1.D registers a wrapper that takes
    Kelly's output as a NOMINAL set-point and produces a robust bid
    via H∞ controller."""

    def compose_chosen(
        self,
        *,
        chosen_mechanism: str,
        chosen_score: float,
        posture: str,
        bong_posterior: Any,
        supply_path: Any = None,
        observation_precision: Optional[float] = None,
        w_max: Optional[float] = None,
        decay_scale: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
    ) -> Optional[float]:
        """Compose the trace-level bid value for the chosen mechanism.

        Returns None when bid cannot be computed (no posterior /
        degenerate variance / etc.) per the existing Kelly contract.
        """
        ...

    def compose_alternatives(
        self,
        alternatives: List[Any],
        *,
        posture: str,
        bong_posterior: Any,
        supply_path: Any = None,
        observation_precision: Optional[float] = None,
        w_max: Optional[float] = None,
        decay_scale: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
    ) -> List[Any]:
        """Bulk variant — populate AlternativeCandidate bid slots."""
        ...


class _DefaultKellyBidComposer:
    """Default BidComposer — delegates to the existing Slice 7
    compose_chosen_bid_value + compose_alternatives functions."""

    name: str = "kelly_default"

    def compose_chosen(
        self,
        *,
        chosen_mechanism: str,
        chosen_score: float,
        posture: str,
        bong_posterior: Any,
        supply_path: Any = None,
        observation_precision: Optional[float] = None,
        w_max: Optional[float] = None,
        decay_scale: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
    ) -> Optional[float]:
        from adam.intelligence.bid_composer import (
            DEFAULT_KELLY_FRACTION_QUARTER,
            DEFAULT_OBSERVATION_PRECISION,
            DEFAULT_PRECISION_DECAY_SCALE,
            DEFAULT_SUPPLY_PATH,
            DEFAULT_W_MAX,
            compose_chosen_bid_value,
        )
        kwargs: Dict[str, Any] = {
            "chosen_mechanism": chosen_mechanism,
            "chosen_score": chosen_score,
            "posture": posture,
            "bong_posterior": bong_posterior,
            "supply_path": supply_path or DEFAULT_SUPPLY_PATH,
            "observation_precision": (
                observation_precision
                if observation_precision is not None
                else DEFAULT_OBSERVATION_PRECISION
            ),
            "w_max": w_max if w_max is not None else DEFAULT_W_MAX,
            "decay_scale": (
                decay_scale
                if decay_scale is not None
                else DEFAULT_PRECISION_DECAY_SCALE
            ),
            "kelly_fraction": (
                kelly_fraction
                if kelly_fraction is not None
                else DEFAULT_KELLY_FRACTION_QUARTER
            ),
        }
        return compose_chosen_bid_value(**kwargs)

    def compose_alternatives(
        self,
        alternatives: List[Any],
        *,
        posture: str,
        bong_posterior: Any,
        supply_path: Any = None,
        observation_precision: Optional[float] = None,
        w_max: Optional[float] = None,
        decay_scale: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
    ) -> List[Any]:
        from adam.intelligence.bid_composer import (
            DEFAULT_KELLY_FRACTION_QUARTER,
            DEFAULT_OBSERVATION_PRECISION,
            DEFAULT_PRECISION_DECAY_SCALE,
            DEFAULT_SUPPLY_PATH,
            DEFAULT_W_MAX,
            compose_alternatives,
        )
        kwargs: Dict[str, Any] = {
            "posture": posture,
            "bong_posterior": bong_posterior,
            "supply_path": supply_path or DEFAULT_SUPPLY_PATH,
            "observation_precision": (
                observation_precision
                if observation_precision is not None
                else DEFAULT_OBSERVATION_PRECISION
            ),
            "w_max": w_max if w_max is not None else DEFAULT_W_MAX,
            "decay_scale": (
                decay_scale
                if decay_scale is not None
                else DEFAULT_PRECISION_DECAY_SCALE
            ),
            "kelly_fraction": (
                kelly_fraction
                if kelly_fraction is not None
                else DEFAULT_KELLY_FRACTION_QUARTER
            ),
        }
        return compose_alternatives(alternatives, **kwargs)


# =============================================================================
# 2. CarryoverCorrectionStrategy — v3 1.E wrap target
# =============================================================================


@runtime_checkable
class CarryoverCorrectionStrategy(Protocol):
    """Pluggable carryover-correction strategy. v3 1.E registers a
    funnel-MPC strategy that replaces the AR(1) decay formula with a
    receding-horizon plan."""

    def apply(
        self,
        mechanism_scores: Dict[str, float],
        *,
        last_touched_mechanism: Optional[str],
        hours_since_last_touch: Optional[float],
        rho: float,
        effect_prev_for_last_touched: float,
        tau: float,
    ) -> Any:
        """Return CarryoverCorrectionResult-shaped object with
        modulated_scores + per_mechanism_penalty + n_corrected + rho."""
        ...


class _DefaultCarryoverStrategy:
    """Default CarryoverCorrectionStrategy — delegates to the Slice 12
    apply_carryover_correction function."""

    name: str = "step10_ar1_default"

    def apply(
        self,
        mechanism_scores: Dict[str, float],
        *,
        last_touched_mechanism: Optional[str],
        hours_since_last_touch: Optional[float],
        rho: float,
        effect_prev_for_last_touched: float,
        tau: float,
    ) -> Any:
        from adam.intelligence.carryover_correction import (
            apply_carryover_correction,
        )
        return apply_carryover_correction(
            mechanism_scores,
            last_touched_mechanism=last_touched_mechanism,
            hours_since_last_touch=hours_since_last_touch,
            rho=rho,
            effect_prev_for_last_touched=effect_prev_for_last_touched,
            tau=tau,
        )


# =============================================================================
# 3. WashoutModel — v3 1.F wrap target
# =============================================================================


@runtime_checkable
class WashoutModel(Protocol):
    """Pluggable washout / frequency-cap model. v3 1.F registers a
    PK/PD model that replaces the constant-table washout floors with
    a continuous Hill-curve residual-effect function."""

    def min_wait_hours(self, mechanism: str) -> float:
        """Minimum hours to wait before the next touch (back-compat
        with the existing washout_hours_for contract)."""
        ...

    def residual_effect_fraction(
        self, mechanism: str, hours_since: float,
    ) -> float:
        """Fraction of prior touch's effect still present at
        ``hours_since`` (∈ [0, 1]). v3 PK/PD impl uses the Hill
        function; default approximates with first-order exponential
        decay anchored on the same washout_hours_for half-life."""
        ...


class _DefaultWashoutModel:
    """Default WashoutModel — delegates to the existing
    retargeting/scheduler.washout_hours_for primitive + the
    mechanism_adme half-life table for the residual fraction."""

    name: str = "constant_table_default"

    def min_wait_hours(self, mechanism: str) -> float:
        from adam.retargeting.scheduler import washout_hours_for
        return washout_hours_for(mechanism)

    def residual_effect_fraction(
        self, mechanism: str, hours_since: float,
    ) -> float:
        """First-order exponential decay anchored on the half-life
        from MECHANISM_PROFILES (when available) — closest contract-
        preserving approximation to the v3 PK/PD continuous curve."""
        try:
            from adam.intelligence.mechanism_adme import (
                MECHANISM_PROFILES,
            )
            profile = MECHANISM_PROFILES.get(mechanism)
            if profile is None:
                # Fall back to default washout half-life.
                from adam.retargeting.scheduler import (
                    DEFAULT_WASHOUT_HOURS,
                    WASHOUT_HALF_LIFE_MULTIPLIER,
                )
                half_life = DEFAULT_WASHOUT_HOURS / WASHOUT_HALF_LIFE_MULTIPLIER
            else:
                half_life = float(profile.half_life_hours)
        except Exception:
            return 0.0  # safe fallback — assume fully washed
        if half_life <= 0.0:
            return 0.0
        delta = max(0.0, float(hours_since))
        # exp(-ln(2) * Δ / t½) → 0.5 at Δ=t½.
        import math
        return math.exp(-math.log(2.0) * delta / half_life)


# =============================================================================
# Registry — single active implementation per protocol
# =============================================================================


_lock = threading.Lock()
_active_bid_composer: BidComposer = _DefaultKellyBidComposer()
_active_carryover_strategy: CarryoverCorrectionStrategy = (
    _DefaultCarryoverStrategy()
)
_active_washout_model: WashoutModel = _DefaultWashoutModel()


def get_active_bid_composer() -> BidComposer:
    return _active_bid_composer


def register_bid_composer(impl: BidComposer) -> None:
    """Replace the active bid composer. v3 1.D startup hook calls
    this with the H∞-wrapped composer."""
    global _active_bid_composer
    with _lock:
        _active_bid_composer = impl
    logger.info(
        "v3_interfaces: bid_composer registered=%s",
        getattr(impl, "name", type(impl).__name__),
    )


def get_active_carryover_strategy() -> CarryoverCorrectionStrategy:
    return _active_carryover_strategy


def register_carryover_strategy(
    impl: CarryoverCorrectionStrategy,
) -> None:
    """Replace the active carryover strategy. v3 1.E startup hook
    calls this with the funnel-MPC strategy."""
    global _active_carryover_strategy
    with _lock:
        _active_carryover_strategy = impl
    logger.info(
        "v3_interfaces: carryover_strategy registered=%s",
        getattr(impl, "name", type(impl).__name__),
    )


def get_active_washout_model() -> WashoutModel:
    return _active_washout_model


def register_washout_model(impl: WashoutModel) -> None:
    """Replace the active washout model. v3 1.F startup hook calls
    this with the PK/PD model."""
    global _active_washout_model
    with _lock:
        _active_washout_model = impl
    logger.info(
        "v3_interfaces: washout_model registered=%s",
        getattr(impl, "name", type(impl).__name__),
    )


def reset_to_defaults_for_tests() -> None:
    """Restore default implementations. Tests use this to isolate
    registry state between cases."""
    global _active_bid_composer, _active_carryover_strategy
    global _active_washout_model
    with _lock:
        _active_bid_composer = _DefaultKellyBidComposer()
        _active_carryover_strategy = _DefaultCarryoverStrategy()
        _active_washout_model = _DefaultWashoutModel()
