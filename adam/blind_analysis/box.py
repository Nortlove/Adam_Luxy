"""Blind-analysis box construction (directive §1.A.SI.1).

The blind-analysis box pre-registers the parameters of an analysis
BEFORE any data is unblinded. The box specifies:

  * The PARAMETER GRID being scanned (e.g., (creative_id × cell_id ×
    cohort_id × posture_class) combinations).
  * The DECISION STATISTIC + threshold for "interestingly-large lift"
    (e.g., IPSW-corrected lift > 5% with p < 0.005).
  * The CONTROL REGIONS — combinations excluded from the signal scan,
    used only for null-distribution estimation.
  * The PRE-REGISTRATION HASH that locks the box parameters into a
    reproducible commitment.

Once a box is sealed (`sealed_box(...)`) the parameter set cannot be
mutated; subsequent reads return the same hash. Any attempt to widen
the parameter grid, lower the threshold, or move points between
signal/control after sealing is a blinding-discipline violation and
raises `BoxValidationError`.

Placeholder data generation (per §1.A.SI.1):
  Use `placeholder_data_generator(box, seed=...)` during analysis
  development. The generator emits synthetic outcome data over the
  box's parameter grid with NULL-hypothesis statistics (no signal
  injected). This lets analysis code run end-to-end without ever
  touching live unblinded data; the live unblinding is a separate
  authorized event.

Reference: Lyons (2008) "Open statistical issues in particle physics"
(Annals of Applied Statistics 2:887–915) — pre-registered blind
analysis as a discipline against multiple-comparisons + post-hoc
fitting bias.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Optional, Tuple


class BoxValidationError(ValueError):
    """Raised when a sealed box is mutated, when signal + control
    regions overlap, or when an unblinding attempt occurs without
    explicit authorization."""


class UnblindingState(str, Enum):
    SEALED = "sealed"               # Box committed; no live data touched
    AUTHORIZED = "authorized"       # CTO / DMC authorized unblinding
    UNBLINDED = "unblinded"         # Live data has been touched


@dataclass(frozen=True)
class BoxParameter:
    """One axis of the parameter grid being scanned.

    name: dimension name (e.g., 'creative_id').
    values: hashable tuple of the values along this axis.
    description: human-readable description for the pre-registration.
    """
    name: str
    values: Tuple[Any, ...]
    description: str = ""


@dataclass(frozen=True)
class BlindAnalysisBox:
    """Sealed pre-registered analysis box.

    `pre_registration_hash` is computed from `(parameters, signal_region,
    control_region, decision_statistic, decision_threshold)` so any
    drift in any field changes the hash. The hash is the
    public-facing commitment recorded in the OSF pre-registration.
    """
    name: str
    parameters: Tuple[BoxParameter, ...]
    signal_region: FrozenSet[Tuple]   # subset of full parameter grid
    control_region: FrozenSet[Tuple]  # disjoint subset
    decision_statistic: str           # named metric
    decision_threshold: float
    sealed_at: datetime
    pre_registration_hash: str
    state: UnblindingState = UnblindingState.SEALED
    notes: str = ""

    def __post_init__(self) -> None:
        # Disjoint regions invariant.
        overlap = self.signal_region & self.control_region
        if overlap:
            raise BoxValidationError(
                f"signal_region and control_region overlap: "
                f"{sorted(overlap)[:5]}... ({len(overlap)} points)"
            )

    def parameter_grid(self) -> List[Tuple]:
        """Materialize the full Cartesian product of parameter values
        in deterministic order. Lexicographic by the order of
        `parameters` (axis-by-axis). Pin the grid construction so
        the pre-registration hash is order-stable."""
        return _cartesian_product(self.parameters)

    def is_in_signal(self, point: Tuple) -> bool:
        return point in self.signal_region

    def is_in_control(self, point: Tuple) -> bool:
        return point in self.control_region

    def authorize_unblinding(
        self, authorizing_party: str, justification: str,
    ) -> "BlindAnalysisBox":
        """Move the box from SEALED → AUTHORIZED. Frozen-dataclass:
        returns a new instance.

        Per directive §G.1 §3 (DMC charter, blinding discipline):
        unblinding must be authorized by the CTO and recorded with
        timestamp + justification + scope."""
        if self.state != UnblindingState.SEALED:
            raise BoxValidationError(
                f"cannot authorize from state {self.state!r}; must be SEALED"
            )
        if not authorizing_party or not justification:
            raise BoxValidationError(
                "authorizing_party and justification are both required"
            )
        new_notes = (
            (self.notes + "\n" if self.notes else "")
            + f"AUTHORIZED at {datetime.now(timezone.utc).isoformat()} "
            f"by {authorizing_party}: {justification}"
        )
        # Build replacement via constructor (preserves frozen invariants).
        return BlindAnalysisBox(
            name=self.name,
            parameters=self.parameters,
            signal_region=self.signal_region,
            control_region=self.control_region,
            decision_statistic=self.decision_statistic,
            decision_threshold=self.decision_threshold,
            sealed_at=self.sealed_at,
            pre_registration_hash=self.pre_registration_hash,
            state=UnblindingState.AUTHORIZED,
            notes=new_notes,
        )

    def mark_unblinded(self) -> "BlindAnalysisBox":
        """Move AUTHORIZED → UNBLINDED. Cannot skip from SEALED."""
        if self.state != UnblindingState.AUTHORIZED:
            raise BoxValidationError(
                f"cannot mark unblinded from state {self.state!r}; must "
                f"be AUTHORIZED first"
            )
        return BlindAnalysisBox(
            name=self.name, parameters=self.parameters,
            signal_region=self.signal_region,
            control_region=self.control_region,
            decision_statistic=self.decision_statistic,
            decision_threshold=self.decision_threshold,
            sealed_at=self.sealed_at,
            pre_registration_hash=self.pre_registration_hash,
            state=UnblindingState.UNBLINDED,
            notes=self.notes + f"\nUNBLINDED at "
                  f"{datetime.now(timezone.utc).isoformat()}",
        )


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _cartesian_product(parameters: Tuple[BoxParameter, ...]) -> List[Tuple]:
    """Deterministic lexicographic Cartesian product of parameter axes."""
    if not parameters:
        return []
    if len(parameters) == 1:
        return [(v,) for v in parameters[0].values]
    head = parameters[0]
    tail = _cartesian_product(parameters[1:])
    return [(v,) + t for v in head.values for t in tail]


def _compute_pre_registration_hash(
    name: str,
    parameters: Tuple[BoxParameter, ...],
    signal_region: FrozenSet[Tuple],
    control_region: FrozenSet[Tuple],
    decision_statistic: str,
    decision_threshold: float,
) -> str:
    """Deterministic SHA-256 over the canonical-ordered representation
    of all box-defining fields. Two boxes with the same parameters
    produce the same hash regardless of insertion order."""
    payload = {
        "name": name,
        "parameters": [
            {"name": p.name, "values": list(p.values),
             "description": p.description}
            for p in parameters
        ],
        "signal_region": sorted([list(t) for t in signal_region]),
        "control_region": sorted([list(t) for t in control_region]),
        "decision_statistic": decision_statistic,
        "decision_threshold": float(decision_threshold),
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sealed_box(
    name: str,
    parameters: Iterable[BoxParameter],
    signal_region: Iterable[Tuple],
    control_region: Iterable[Tuple],
    decision_statistic: str,
    decision_threshold: float,
    notes: str = "",
) -> BlindAnalysisBox:
    """Factory: build + seal + hash + return a `BlindAnalysisBox`.

    The factory enforces:
      * signal_region and control_region disjoint
      * each region's points are within the parameter grid
      * pre-registration hash is computed deterministically
    """
    params = tuple(parameters)
    sig = frozenset(signal_region)
    ctl = frozenset(control_region)

    grid = set(_cartesian_product(params))
    bad_sig = sig - grid
    if bad_sig:
        raise BoxValidationError(
            f"signal_region contains points outside the parameter grid: "
            f"{sorted(bad_sig)[:5]}..."
        )
    bad_ctl = ctl - grid
    if bad_ctl:
        raise BoxValidationError(
            f"control_region contains points outside the parameter grid: "
            f"{sorted(bad_ctl)[:5]}..."
        )

    pre_hash = _compute_pre_registration_hash(
        name, params, sig, ctl, decision_statistic, decision_threshold,
    )
    return BlindAnalysisBox(
        name=name,
        parameters=params,
        signal_region=sig,
        control_region=ctl,
        decision_statistic=decision_statistic,
        decision_threshold=decision_threshold,
        sealed_at=datetime.now(timezone.utc),
        pre_registration_hash=pre_hash,
        state=UnblindingState.SEALED,
        notes=notes,
    )


def placeholder_data_generator(
    box: BlindAnalysisBox,
    *,
    seed: int = 0,
    null_mean: float = 0.0,
    null_std: float = 1.0,
) -> Dict[Tuple, float]:
    """Synthetic NULL-hypothesis data over the entire parameter grid.

    Uses Python's `random.Random(seed)` for determinism; emits one
    Gaussian-distributed value per grid point with mean `null_mean`
    and std `null_std`. NO SIGNAL is injected — by design. Analysis
    code can run end-to-end against this generator and exercise its
    decision logic without touching live data.

    For consistency tests against the Gross-Vitells LEE trial factor
    in §1.A.SI.2, the NULL-only generator produces Type-I error
    estimates — what fraction of placeholder runs cross the
    decision_threshold by chance. The trial factor predicts how this
    fraction scales with grid size.
    """
    rng = random.Random(seed)
    return {
        point: rng.gauss(null_mean, null_std)
        for point in box.parameter_grid()
    }
