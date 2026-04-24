"""Effect-Size Correction Utility — Publication-Bias Adjustment for Psychological Priors.

Rationale
---------
Published effect sizes in social and behavioral psychology are systematically
inflated by publication bias, selective reporting, questionable research
practices, and file-drawer effects. Schimmack (2022) replicability-index
analyses and Maier et al. (2023) RoBMA multiverse meta-analyses converge on
roughly 30-60% of published effects surviving publication-bias correction.

ADAM operates on corrected effect sizes throughout. The correction priorities,
in order of strength:

1. **Pre-registered effect** — if a pre-registered large-scale study reported
   the effect, use that directly. Pre-registration is the strongest single
   protection against publication bias.
2. **RoBMA multiverse median** — where no pre-registration exists but a
   publication-bias-adjusted multiverse meta-analysis does (Maier et al. 2023
   family), use the multiverse median.
3. **Schimmack-ratio shrinkage** — as a fallback, shrink published meta-
   analytic effects by the replicability-index-implied ratio for the field.
4. **Uncorrected** — never operational. Permitted only for documentation of
   the uncorrected published value alongside the corrected value.

This module provides PublicationBiasCorrectedEffect, a d→Beta-prior mapping,
and pre-computed constants for ADAM's recalibrated constructs. Additional
constructs are added as their recalibrations ship.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CorrectionMethod(str, Enum):
    PRE_REGISTERED = "pre_registered"
    ROBMA_MEDIAN = "robma_median"
    SCHIMMACK_RATIO = "schimmack_ratio"
    UNCORRECTED = "uncorrected"


@dataclass(frozen=True)
class PublicationBiasCorrectedEffect:
    """A psychological effect size corrected for publication bias.

    Attributes
    ----------
    construct_name : str
        Canonical ADAM construct identifier (e.g. 'construal_level_matching').
    published_g : float
        Uncorrected meta-analytic Hedges' g (or Cohen's d). Transparency only;
        never operational.
    corrected_d : float
        Operational value. Pre-registered where available; RoBMA multiverse
        median otherwise; Schimmack-shrunk as fallback.
    correction_method : CorrectionMethod
        Which correction strategy produced corrected_d.
    pre_registered_d : Optional[float]
        Pre-registered effect, when available.
    study_count : int
        Underlying meta-analysis study count.
    citations : tuple[str, ...]
        Canonical citations for effect and correction.
    notes : str
        Provenance and rationale.
    """

    construct_name: str
    published_g: float
    corrected_d: float
    correction_method: CorrectionMethod
    pre_registered_d: Optional[float] = None
    study_count: int = 0
    citations: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if (
            self.correction_method == CorrectionMethod.UNCORRECTED
            and self.corrected_d != self.published_g
        ):
            raise ValueError(
                "UNCORRECTED requires corrected_d == published_g. "
                "Use a genuine correction method or fix the inputs."
            )
        if (
            self.correction_method == CorrectionMethod.PRE_REGISTERED
            and self.pre_registered_d is None
        ):
            raise ValueError(
                "PRE_REGISTERED correction method requires pre_registered_d."
            )

    def shrinkage_ratio(self) -> float:
        """corrected_d / published_g."""
        if self.published_g == 0:
            return 1.0
        return self.corrected_d / self.published_g


def d_to_success_probability(
    d: float,
    slope: float = 0.2,
    clip: tuple[float, float] = (0.1, 0.9),
) -> float:
    """Map Cohen's d to a success probability under ADAM's linear convention.

    p = 0.5 + slope * d, clipped to [clip[0], clip[1]].

    Slope 0.2 approximates the probit mapping for small |d| (|d| <= 0.6) while
    remaining free of scipy dependency. May be tuned per construct if
    empirically grounded.
    """
    p = 0.5 + slope * d
    return max(clip[0], min(clip[1], p))


def to_beta_prior(
    effect: PublicationBiasCorrectedEffect,
    prior_concentration: float = 30.0,
) -> tuple[float, float]:
    """Convert corrected effect to Beta(alpha, beta) prior parameters.

    Parameters
    ----------
    effect : PublicationBiasCorrectedEffect
        Corrected effect to convert.
    prior_concentration : float
        Pseudo-sample-size controlling prior informativity. Higher = narrower.
        Default 30 permits meaningful updating from ~30+ real observations.

    Returns
    -------
    tuple[float, float]
        (alpha, beta) of a Beta distribution.
    """
    p = d_to_success_probability(effect.corrected_d)
    alpha = prior_concentration * p
    beta = prior_concentration * (1.0 - p)
    return alpha, beta


# -----------------------------------------------------------------------------
# Pre-computed corrected effects
# -----------------------------------------------------------------------------

CLT_MATCHING_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="construal_level_matching",
    published_g=0.475,
    corrected_d=0.276,
    correction_method=CorrectionMethod.PRE_REGISTERED,
    pre_registered_d=0.276,
    study_count=111,
    citations=(
        "Trope, Y. & Liberman, N. (2010). Construal level theory of "
        "psychological distance. Psychological Review, 117(2), 440-463.",
        "Schimmack, U. (2022). The replicability index (R-index).",
        "Maier, M., Bartoš, F., & Wagenmakers, E.-J. (2023). Robust Bayesian "
        "meta-analysis (RoBMA) in R.",
    ),
    notes=(
        "Meta-analytic pooled Hedges' g = 0.475 (111 studies) is subject to "
        "publication-bias inflation. Schimmack (2022) R-index analyses and "
        "Maier et al. (2023) RoBMA multiverse converge on ~30-42% of the "
        "published effect surviving correction. The pre-registered d = 0.276 "
        "is ADAM's operational value — the largest defensible CLT matching "
        "effect that survived pre-registration, independent of the meta-"
        "analytic pool that may include unpublished-null bias. See "
        "docs/CLT_recalibration_2026_04_24.md."
    ),
)


# -----------------------------------------------------------------------------
# Additional constructs requiring recalibration (flagged for post-pilot work)
# -----------------------------------------------------------------------------
# The following constructs currently carry uncorrected published effect sizes
# and require recalibration post-pilot using the same utility:
#   - regulatory_focus (graph_edge_service.py:669 currently 0.475; Higgins 1997)
#   - social_proof
#   - scarcity / urgency
#   - authority
#   - reciprocity
#   - mimetic_desire
#   - identity_construction
#   - loss_aversion_framing
# Each requires: review of published meta-analytic effect, identification of
# pre-registered replications (e.g., ManyLabs, Registered Replication Reports),
# RoBMA multiverse where available, and a corrected_d. Schedule: post-pilot,
# begins when external psychometrician contractor delivers 27-dimension
# validation (month 4-5).
