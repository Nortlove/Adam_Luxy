"""Processing-depth priors + route-split helpers for the plant model.

This module gives the plant model a structural upgrade over the flat
posture-band → route-fraction table: autopilot / attention fractions
are now derived from an **expected processing-depth distribution per
posture band** composed with a relative P(convert | depth) proxy. The
derivation is explicit and externally auditable.

Registry link: ``a14_compromises.DEPTH_PRIOR_UNVALIDATED``. Both
components of the derivation carry unvalidated-external-prior
compromises:

- ``_EXPECTED_DEPTH_BY_POSTURE_BAND`` — expected distribution of
  ProcessingDepth levels per posture band. Seeded from aggregated
  display-advertising dwell-time research (Lumen, Bruns et al.,
  Amplified Intelligence / Nelson-Field, Goldstein); the per-band
  deltas along the attentional-posture axis are theoretically
  motivated, not empirically calibrated on ADAM data.
- ``_RELATIVE_P_CONVERT_BY_DEPTH`` — relative per-depth conversion
  propensity used to translate depth-of-impression distributions to
  depth-of-conversion distributions. Externally-motivated proxy
  (derived from the processing-depth POSTERIOR WEIGHTS in
  ``adam/retargeting/engines/processing_depth.py``, which are
  themselves research-grounded posterior-update weights — not
  conversion rates directly).

Two follow-up slices retire the compromise:

1. **External threshold + distribution validation**. Validate the
   ProcessingDepth enum thresholds AND the expected distributions on
   ADAM pilot data. May surface context-specific corrections.
2. **Per-cell distribution priors**. Replace per-posture-band priors
   with cell-level priors informed by upstream page intelligence
   (Layer-11 processing-depth dimension).

Scope of this module
--------------------

- ``AUTOPILOT_ROUTE_DEPTHS``, ``ATTENTION_ROUTE_DEPTHS``,
  ``NON_CONVERTING_DEPTHS`` — the depth → route mapping contract.
  Formerly ad-hoc per caller; now central.
- ``expected_route_fractions(posture_band)`` — returns (autopilot,
  attention) fractions of converting mass for a given posture band.
  Consumed by ``PlantModel._route_split``.
- ``route_split_from_counts(counts)`` — converts realized per-depth
  impression counts into (autopilot_count, attention_count).
  Callers use this to derive the route counts ``RealizedOutcomes``
  now carries as an optional annotation.
"""

from __future__ import annotations

from typing import Dict, Mapping, Tuple

from adam.retargeting.engines.processing_depth import ProcessingDepth


# =============================================================================
# Depth → route mapping contract
# =============================================================================
#
# Research-grounded mapping. UNPROCESSED + PERIPHERAL are shallow-
# processing depths where the ad was present but not consciously
# evaluated — autopilot route by construction of the attention-
# inversion principle. EVALUATED is deep processing and represents
# attention-route conversions. REJECTED is deliberate decline within
# the observation window — the impression did not produce a
# conversion, so it is excluded from both route buckets.

AUTOPILOT_ROUTE_DEPTHS: frozenset[ProcessingDepth] = frozenset({
    ProcessingDepth.UNPROCESSED,
    ProcessingDepth.PERIPHERAL,
})

ATTENTION_ROUTE_DEPTHS: frozenset[ProcessingDepth] = frozenset({
    ProcessingDepth.EVALUATED,
})

NON_CONVERTING_DEPTHS: frozenset[ProcessingDepth] = frozenset({
    ProcessingDepth.REJECTED,
})


# =============================================================================
# Expected depth distribution per posture band (external prior)
# =============================================================================
#
# Sourced from aggregated display-ad research cited in
# ``adam/retargeting/engines/processing_depth.py`` (Lumen Research,
# Bruns et al. 2025, Amplified Intelligence / Nelson-Field,
# Goldstein et al. 2011). Baseline (``neutral`` posture) reflects the
# "30-50% of viewable display ads never meaningfully seen" finding
# plus average-dwell estimates.
#
# Per-band deltas: autopilot_* contexts shift mass from EVALUATED
# toward PERIPHERAL (the user is absorbed by content; ads in the
# periphery get scanned but rarely evaluated). vigilance_* contexts
# shift mass in the opposite direction (task-focused reading makes
# the user more discriminating; ads that survive attention get
# evaluated or rejected).
#
# Each row sums to 1.0.

_EXPECTED_DEPTH_BY_POSTURE_BAND: Mapping[str, Mapping[ProcessingDepth, float]] = {
    "autopilot_high": {
        ProcessingDepth.UNPROCESSED: 0.42,
        ProcessingDepth.PERIPHERAL:  0.42,
        ProcessingDepth.EVALUATED:   0.11,
        ProcessingDepth.REJECTED:    0.05,
    },
    "autopilot_low": {
        ProcessingDepth.UNPROCESSED: 0.41,
        ProcessingDepth.PERIPHERAL:  0.38,
        ProcessingDepth.EVALUATED:   0.15,
        ProcessingDepth.REJECTED:    0.06,
    },
    "neutral": {
        ProcessingDepth.UNPROCESSED: 0.40,
        ProcessingDepth.PERIPHERAL:  0.35,
        ProcessingDepth.EVALUATED:   0.18,
        ProcessingDepth.REJECTED:    0.07,
    },
    "vigilance_low": {
        ProcessingDepth.UNPROCESSED: 0.38,
        ProcessingDepth.PERIPHERAL:  0.32,
        ProcessingDepth.EVALUATED:   0.22,
        ProcessingDepth.REJECTED:    0.08,
    },
    "vigilance_high": {
        ProcessingDepth.UNPROCESSED: 0.36,
        ProcessingDepth.PERIPHERAL:  0.29,
        ProcessingDepth.EVALUATED:   0.26,
        ProcessingDepth.REJECTED:    0.09,
    },
}

VALID_POSTURE_BANDS: frozenset[str] = frozenset(_EXPECTED_DEPTH_BY_POSTURE_BAND.keys())


# =============================================================================
# Relative P(convert | depth) — externally-motivated proxy
# =============================================================================
#
# Used to translate expected-impression-distribution to
# expected-conversion-distribution. The proxy comes from the
# ProcessingDepth POSTERIOR WEIGHTS in
# ``adam/retargeting/engines/processing_depth.py``:
#   UNPROCESSED: 0.05   (minimal subliminal / mere-exposure)
#   PERIPHERAL:  0.30   (Heath's low-attention processing)
#   EVALUATED:   0.80   (active consideration)
#   REJECTED:    0.00   (deliberately declined)
#
# Honest caveat: the source weights are posterior-update weights on
# LEARNING observations, not P(convert | depth) directly. Using them
# as relative conversion-propensity proxies is a structural
# assumption; ``a14_compromises.DEPTH_PRIOR_UNVALIDATED`` names it.
# Empirical validation on ADAM pilot data is a named successor slice.

_RELATIVE_P_CONVERT_BY_DEPTH: Mapping[ProcessingDepth, float] = {
    ProcessingDepth.UNPROCESSED: 0.05,
    ProcessingDepth.PERIPHERAL:  0.30,
    ProcessingDepth.EVALUATED:   0.80,
    ProcessingDepth.REJECTED:    0.00,
}


# =============================================================================
# Public helpers
# =============================================================================


def expected_depth_distribution(
    posture_band: str,
) -> Dict[ProcessingDepth, float]:
    """Return the expected per-impression depth distribution for a band.

    Unknown posture band raises ``ValueError`` rather than silently
    returning a default.
    """
    _validate_posture_band(posture_band)
    return dict(_EXPECTED_DEPTH_BY_POSTURE_BAND[posture_band])


def expected_route_fractions(posture_band: str) -> Tuple[float, float]:
    """Return (autopilot_fraction, attention_fraction) of converting mass.

    Derived from the expected depth distribution × relative P(convert |
    depth) proxy. The returned fractions sum to 1.0 by construction —
    every converting impression is either autopilot-route or
    attention-route (REJECTED does not convert). If the caller wants
    a "unresolved route" allowance, it applies upstream.
    """
    _validate_posture_band(posture_band)
    dist = _EXPECTED_DEPTH_BY_POSTURE_BAND[posture_band]
    conversion_mass: Dict[ProcessingDepth, float] = {
        depth: dist[depth] * _RELATIVE_P_CONVERT_BY_DEPTH[depth]
        for depth in ProcessingDepth
    }
    total = sum(conversion_mass.values())
    if total <= 0.0:
        # Degenerate (would only happen if priors were misconfigured).
        # Neutral 50/50 is safer than raising.
        return (0.5, 0.5)
    autopilot_mass = sum(
        conversion_mass[d] for d in AUTOPILOT_ROUTE_DEPTHS
    )
    attention_mass = sum(
        conversion_mass[d] for d in ATTENTION_ROUTE_DEPTHS
    )
    return (autopilot_mass / total, attention_mass / total)


def route_split_from_counts(
    processing_depth_counts: Mapping[str, int],
) -> Tuple[int, int]:
    """Derive (autopilot_count, attention_count) from per-depth counts.

    Scope 2 helper formalizing the caller-side split that used to be
    ad-hoc. Callers who have per-impression depth annotations invoke
    this to produce the route counts ``RealizedOutcomes`` accepts.
    REJECTED impressions are excluded (they did not convert within
    the observation window).

    Unknown depth keys raise ``ValueError``. Empty dict returns (0, 0).
    """
    autopilot_count = 0
    attention_count = 0
    for depth_value, count in processing_depth_counts.items():
        if count < 0:
            raise ValueError(
                f"processing_depth count for {depth_value!r} "
                f"must be >= 0; got {count}"
            )
        try:
            depth = ProcessingDepth(depth_value)
        except ValueError as exc:
            raise ValueError(
                f"unknown ProcessingDepth value {depth_value!r}; "
                f"expected one of {[d.value for d in ProcessingDepth]}"
            ) from exc
        if depth in AUTOPILOT_ROUTE_DEPTHS:
            autopilot_count += count
        elif depth in ATTENTION_ROUTE_DEPTHS:
            attention_count += count
        # NON_CONVERTING_DEPTHS: deliberately excluded from route
        # counts (did not produce conversions within the window).
    return (autopilot_count, attention_count)


def normalize_depth_counts_to_distribution(
    processing_depth_counts: Mapping[str, int],
) -> Dict[str, float]:
    """Convert per-depth counts into a fractional distribution.

    Used by the adjudicator to populate
    ``EvidenceTrace.processing_depth_distribution``. All four enum
    values appear in the returned dict with fraction 0.0 for depths
    not present in the counts. Empty input returns all-zero
    distribution.

    Unknown depth keys raise ``ValueError`` at the enum boundary.
    """
    total = sum(processing_depth_counts.values())
    distribution: Dict[str, float] = {d.value: 0.0 for d in ProcessingDepth}
    if total <= 0:
        return distribution
    for depth_value, count in processing_depth_counts.items():
        # Validate enum value; will raise on unknown.
        ProcessingDepth(depth_value)
        distribution[depth_value] = count / total
    return distribution


# =============================================================================
# Internal
# =============================================================================


def _validate_posture_band(posture_band: str) -> None:
    if posture_band not in _EXPECTED_DEPTH_BY_POSTURE_BAND:
        raise ValueError(
            f"unknown posture_band {posture_band!r}; "
            f"must be one of {sorted(_EXPECTED_DEPTH_BY_POSTURE_BAND.keys())}"
        )


# =============================================================================
# Integrity check — run at import time
# =============================================================================


def _validate_priors_at_import() -> None:
    """Confirm each posture band's distribution sums to 1.0 (± float eps)."""
    for band, dist in _EXPECTED_DEPTH_BY_POSTURE_BAND.items():
        total = sum(dist.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"_EXPECTED_DEPTH_BY_POSTURE_BAND[{band!r}] "
                f"sums to {total}, expected 1.0"
            )
        missing = set(ProcessingDepth) - set(dist.keys())
        if missing:
            raise ValueError(
                f"_EXPECTED_DEPTH_BY_POSTURE_BAND[{band!r}] "
                f"missing ProcessingDepth keys: {missing}"
            )
    for depth in ProcessingDepth:
        if depth not in _RELATIVE_P_CONVERT_BY_DEPTH:
            raise ValueError(
                f"_RELATIVE_P_CONVERT_BY_DEPTH missing {depth}"
            )


_validate_priors_at_import()


__all__ = [
    "ATTENTION_ROUTE_DEPTHS",
    "AUTOPILOT_ROUTE_DEPTHS",
    "NON_CONVERTING_DEPTHS",
    "VALID_POSTURE_BANDS",
    "expected_depth_distribution",
    "expected_route_fractions",
    "normalize_depth_counts_to_distribution",
    "route_split_from_counts",
]
