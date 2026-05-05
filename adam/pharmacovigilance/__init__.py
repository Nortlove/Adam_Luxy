"""Pharmacovigilance schema + disproportionality metrics.

Per directive §G.3 — schema is fixed pre-pilot; data populates post-pilot.
EBGM with DuMouchel MGPS shrinkage is the canonical signal-localization
metric (DuMouchel 1999, *Amer. Stat.* 53:170-190).
"""
from adam.pharmacovigilance.schema import (
    PharmacovigilanceCell,
    DisproportionalityMetrics,
    SignalThresholds,
    TreeScanResult,
    compute_prr,
    compute_ror,
    compute_ic,
    compute_ic025,
    compute_ebgm_naive,
    is_signal,
)

__all__ = [
    "PharmacovigilanceCell",
    "DisproportionalityMetrics",
    "SignalThresholds",
    "TreeScanResult",
    "compute_prr",
    "compute_ror",
    "compute_ic",
    "compute_ic025",
    "compute_ebgm_naive",
    "is_signal",
]
