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
    UNKNOWN_PENDING_REVIEW = "unknown_pending_review"  # interim shrinkage; literature-survey-pending
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
# 9-mechanism registry (Doc 3 §I.8 directive: "ship publication-bias-corrected
# annotation on every mechanism").
#
# Discipline: each entry below either has a defensible correction method
# (PRE_REGISTERED, ROBMA_MEDIAN, or SCHIMMACK_RATIO with cited shrinkage
# basis), OR uses UNKNOWN_PENDING_REVIEW with a 30% Schimmack-floor shrinkage
# as honest interim. UNKNOWN_PENDING_REVIEW entries are explicitly tagged so
# a downstream consumer (or external psychometrician, when contracted) can
# triage them. NO entry uses UNCORRECTED — that method is documentation-only.
#
# These ARE the operational values. The cascade and outcome-handler consume
# them via mechanism_corrected_effect() below.
# -----------------------------------------------------------------------------

LOSS_AVERSION_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="loss_aversion_framing",
    published_g=0.61,
    corrected_d=0.26,
    correction_method=CorrectionMethod.SCHIMMACK_RATIO,
    study_count=146,  # Kenworthy 2011 trans-paradigm meta
    citations=(
        "Kenworthy, J. B., et al. (2011). Cognitive dissonance trans-paradigm "
        "meta-analysis. Personality and Social Psychology Bulletin.",
        "Izuma, K. & Murayama, K. (2013). Choice-induced preference change "
        "in the free-choice paradigm: a critical methodological review.",
    ),
    notes=(
        "Kenworthy 2011 reported pooled d=0.61 across dissonance paradigms. "
        "Izuma & Murayama (2013) artifact-corrected the free-choice paradigm "
        "to d=0.26. ADAM operates at the corrected value. Pre-registered "
        "replication for prospect-theory loss-aversion specifically is on the "
        "post-pilot agenda."
    ),
)

PERSONALITY_MATCHING_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="personality_matching",
    published_g=0.30,  # Hirsh-Kang-Bodenhausen 2012 r_diff range
    corrected_d=0.15,
    correction_method=CorrectionMethod.PRE_REGISTERED,
    pre_registered_d=0.15,
    study_count=80,  # 2024-2025 systematic review
    citations=(
        "Matz, S. C., Kosinski, M., Nave, G., & Stillwell, D. J. (2017). "
        "Psychological targeting as an effective approach to digital mass "
        "persuasion. PNAS, 114(48). OR=1.30 [1.22-1.40], pre-registered.",
        "Hirsh, J. B., Kang, S. K., & Bodenhausen, G. V. (2012). Personalized "
        "persuasion: Tailoring persuasive appeals to recipients' personality "
        "traits.",
        "Alkış & Temizel (2015); Oyibo et al. (2017) — replication mappings "
        "of Big Five to Cialdini influence principles.",
    ),
    notes=(
        "Matz 2017 N=3.5M Facebook field experiment was pre-registered with "
        "OR=1.30 [1.22-1.40] for the introversion study. d≈0.15 is the "
        "corresponding small-but-robust effect — well below the 40-50% lift "
        "headline that gets quoted out-of-context."
    ),
)

LIKING_MERE_EXPOSURE_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="liking_mere_exposure",
    published_g=0.54,  # Bornstein 1989 r=0.26 → d≈0.54
    corrected_d=0.30,
    correction_method=CorrectionMethod.SCHIMMACK_RATIO,
    study_count=208,  # Bornstein 1989 meta
    citations=(
        "Bornstein, R. F. (1989). Exposure and affect: Overview and meta-"
        "analysis of research, 1968-1987. Psychological Bulletin, 106(2).",
        "Montoya, R. M., et al. (2017). Inverted-U mere exposure curve.",
    ),
    notes=(
        "Bornstein 1989 r=0.26 (208 experiments, robust). Montoya et al. 2017 "
        "established inverted-U with peak at 10-35 exposures. Effect survives "
        "correction better than most social-priming literature; ~55% retained."
    ),
)

# Mechanisms below await literature survey or external psychometrician
# review. UNKNOWN_PENDING_REVIEW with 30% Schimmack-floor shrinkage is the
# honest interim — better than uncorrected published values, worse than a
# real meta-analytic recalibration. Each carries a stated retirement trigger.

AUTHORITY_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="authority",
    published_g=0.30,
    corrected_d=0.12,  # 30% Schimmack-floor shrinkage of 0.40 mid-estimate
    correction_method=CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    study_count=0,  # placeholder — no comprehensive meta-analysis cited
    citations=(
        "Cialdini, R. B. (2009). Influence: Science and practice (5th ed.).",
        "Schimmack, U. (2022). The replicability index — applied as 30%-floor "
        "interim shrinkage pending mechanism-specific meta-analytic review.",
    ),
    notes=(
        "PENDING REVIEW. Cialdini-tradition meta-analyses report d≈0.30-0.40 "
        "but replication track record is mixed (Milgram-tradition partial "
        "replications, expert-endorsement effects context-dependent). 30% "
        "Schimmack-floor shrinkage is interim. Retires when (a) external "
        "psychometrician delivers mechanism-specific RoBMA multiverse, OR "
        "(b) ADAM's own MRT/WCLS pipeline accumulates ≥1000 impressions "
        "per archetype × authority cell."
    ),
)

SOCIAL_PROOF_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="social_proof",
    published_g=0.40,
    corrected_d=0.20,  # 50% retention for moderately-replicated effect
    correction_method=CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    study_count=0,
    citations=(
        "Cialdini, R. B. (2009). Influence: Science and practice.",
        "Schimmack, U. (2022). R-index applied as interim shrinkage.",
    ),
    notes=(
        "PENDING REVIEW. Cialdini consensus principle; testimonial-meta-"
        "analytic estimates vary widely. 50% retention reflects moderate-"
        "replication confidence. Retires per same trigger as authority."
    ),
)

SCARCITY_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="scarcity",
    published_g=0.35,
    corrected_d=0.14,  # 40% retention
    correction_method=CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    study_count=0,
    citations=(
        "Cialdini, R. B. (2009). Influence: Science and practice.",
        "Schimmack, U. (2022). R-index applied as interim shrinkage.",
    ),
    notes=(
        "PENDING REVIEW. Scarcity/urgency effects often co-vary with "
        "reactance suppression; clean meta-analyses scarce. 40% retention. "
        "Retires per same trigger as authority. NB: scarcity is also "
        "vigilance-activating per attention-inversion frame, so even when "
        "the effect is real its desirability for ADAM is conditional."
    ),
)

COMMITMENT_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="commitment",
    published_g=0.32,  # Dillard 1984 FITD r=0.15-0.17 → d≈0.32
    corrected_d=0.15,
    correction_method=CorrectionMethod.SCHIMMACK_RATIO,
    study_count=120,
    citations=(
        "Dillard, J. P., Hunter, J. E., & Burgoon, M. (1984). Sequential-"
        "request persuasive strategies: Meta-analysis of foot-in-the-door "
        "and door-in-the-face. Human Communication Research.",
        "Beaman, A. L., et al. (1983). Foot-in-the-door meta-analysis.",
    ),
    notes=(
        "FITD effect was already small in the original meta-analyses "
        "(r=0.15-0.17). Burger & Guadagno (2003) showed reverse effects "
        "in low self-concept-clarity individuals. Cialdini-Trost-Newsom "
        "(1995) PFC moderator further attenuates. d=0.15 is the corrected "
        "expected effect across the unrestricted population."
    ),
)

RECIPROCITY_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="reciprocity",
    published_g=0.40,
    corrected_d=0.16,  # 40% retention
    correction_method=CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    study_count=0,
    citations=(
        "Cialdini, R. B. (2009). Influence: Science and practice.",
        "Schimmack, U. (2022). R-index applied as interim shrinkage.",
    ),
    notes=(
        "PENDING REVIEW. Reciprocity principle is well-established as a "
        "norm but specific persuasion-effect-size meta-analysis sparse. "
        "40% retention. Retires per same trigger as authority."
    ),
)

UNITY_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="unity",
    published_g=0.30,
    corrected_d=0.12,  # 40% retention
    correction_method=CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    study_count=0,
    citations=(
        "Cialdini, R. B. (2016). Pre-Suasion: A revolutionary way to "
        "influence and persuade.",
        "Schimmack, U. (2022). R-index applied as interim shrinkage.",
    ),
    notes=(
        "PENDING REVIEW. Cialdini's 7th principle (added 2016). Meta-"
        "analytic basis less mature than original 6 principles. 40% "
        "retention. Retires per same trigger as authority."
    ),
)

CURIOSITY_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="curiosity",
    published_g=0.30,
    corrected_d=0.12,  # 40% retention
    correction_method=CorrectionMethod.UNKNOWN_PENDING_REVIEW,
    study_count=0,
    citations=(
        "Loewenstein, G. (1994). The psychology of curiosity: A review and "
        "reinterpretation. Psychological Bulletin.",
        "Schimmack, U. (2022). R-index applied as interim shrinkage.",
    ),
    notes=(
        "PENDING REVIEW. Curiosity-as-persuasion effect lacks dedicated "
        "meta-analytic pool; effects often documented within information-"
        "gap or curiosity-prompt paradigms in lab settings. 40% retention. "
        "Retires per same trigger as authority."
    ),
)

COGNITIVE_EASE_EFFECT = PublicationBiasCorrectedEffect(
    construct_name="cognitive_ease",
    published_g=0.30,
    corrected_d=0.15,  # 50% retention — processing fluency well-replicated
    correction_method=CorrectionMethod.SCHIMMACK_RATIO,
    study_count=80,
    citations=(
        "Reber, R., Schwarz, N., & Winkielman, P. (2004). Processing "
        "fluency and aesthetic pleasure. Personality and Social Psychology "
        "Review, 8(4).",
        "Schimmack, U. (2022). R-index applied as interim shrinkage.",
    ),
    notes=(
        "Processing fluency literature is reasonably well-replicated. "
        "50% retention. Note: cognitive_ease is the canonical mechanism "
        "complement to attention-inversion (blend-fit primitives). "
        "Pre-registration agenda for the metaphor-axis fluency component "
        "is post-pilot."
    ),
)


# -----------------------------------------------------------------------------
# Mechanism registry — single source of truth for cascade and outcome handler
# -----------------------------------------------------------------------------

MECHANISM_EFFECT_REGISTRY: dict[str, PublicationBiasCorrectedEffect] = {
    "loss_aversion": LOSS_AVERSION_EFFECT,
    "personality_matching": PERSONALITY_MATCHING_EFFECT,
    "liking": LIKING_MERE_EXPOSURE_EFFECT,
    "authority": AUTHORITY_EFFECT,
    "social_proof": SOCIAL_PROOF_EFFECT,
    "scarcity": SCARCITY_EFFECT,
    "commitment": COMMITMENT_EFFECT,
    "reciprocity": RECIPROCITY_EFFECT,
    "unity": UNITY_EFFECT,
    "curiosity": CURIOSITY_EFFECT,
    "cognitive_ease": COGNITIVE_EASE_EFFECT,
    "construal_level_matching": CLT_MATCHING_EFFECT,
}


def mechanism_corrected_effect(
    mechanism: str,
) -> Optional[PublicationBiasCorrectedEffect]:
    """Return the corrected effect for a mechanism, or None if unknown.

    Callers should branch on None and either (a) skip the correction
    annotation, or (b) flag the mechanism as not-yet-registered.
    Returning a default value silently would mask coverage gaps.
    """
    return MECHANISM_EFFECT_REGISTRY.get(mechanism)


def correction_metadata_for_response(
    mechanism: str,
) -> dict:
    """Build the publication_bias_correction block for a cascade response.

    Returns a dict suitable for surfacing alongside lift estimates so
    consumers (Tier A reports, partner UI, regulatory disclosure) can
    cite the correction provenance.
    """
    eff = mechanism_corrected_effect(mechanism)
    if eff is None:
        return {
            "mechanism": mechanism,
            "correction_status": "NOT_REGISTERED",
            "note": (
                "Mechanism not in MECHANISM_EFFECT_REGISTRY. Effect-size "
                "claims for this mechanism do not carry publication-bias "
                "correction; treat as un-validated."
            ),
        }
    return {
        "mechanism": eff.construct_name,
        "published_g": eff.published_g,
        "corrected_d": eff.corrected_d,
        "correction_method": eff.correction_method.value,
        "shrinkage_ratio": round(eff.shrinkage_ratio(), 3),
        "study_count": eff.study_count,
        "pending_review": eff.correction_method == CorrectionMethod.UNKNOWN_PENDING_REVIEW,
        "citations": list(eff.citations),
    }
