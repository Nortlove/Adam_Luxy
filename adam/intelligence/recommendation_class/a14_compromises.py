"""A14-compromise registry for the RecommendationClass primitive.

Antipattern A14 from ADAM_AGENT_ORIENTATION.md: *building N+1 on
unverified N*. Its pilot-scale analogue is shipping a thinner substrate
than the decided architecture and moving on to N+1 before the thinner
substrate is retired. The pilot plan (2026-04-24) names the compromises
explicitly so they cannot hide:

    "Six A14 compromises explicit with expiration conditions — named so
     drift cannot hide."

This module is the anchor for the four runtime-emitted compromises in
the RecommendationClass primitive. Every site in code that embodies
one of these compromises references the named constant here instead of
carrying its own prose description. The retirement trigger is a data
condition; when the condition is met the compromise retires and the
corresponding bias flag / behaviour in the code changes shape (not
always by deletion — `COUNTER_REGULATION_UNTRACKED` retires into an
empirical estimate, not into nothing).

Not captured here:
- Library-choice compromises (e.g. sklearn BayesianGaussianMixture vs
  PyMC NUTS in `archetype_compression.py`). Those are internal
  implementation choices that do not surface in any emitted output.
- Process-level compromises (git-hash pre-registration vs OSF-public;
  single-advertiser pilot vs multi-tenant). Tracked in the pilot plan
  memory, not in the runtime registry, because they do not flow into
  CompetingActivations or AdjudicatorOutput.
- "HB latent class without external psychometric validation" — tracked
  in the pilot plan memory (expires at contractor delivery month 4-5);
  not runtime-emitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class A14Compromise:
    """A named A14 compromise with its retirement condition and live sites.

    Fields:

    - ``name``: stable constant-case identifier. Used for cross-reference
      from the live sites and for the pilot report pack.
    - ``description``: one-to-two-sentence explanation of what the
      compromise is — what the pilot ships instead of the decided
      architecture.
    - ``retirement_trigger``: the data / milestone condition that moves
      the compromise from "shipped as A14" to "retired". Phrased in
      observable terms, not as a vague "post-pilot." When drift risk is
      high the trigger names a concrete weakness in the multi-lens
      registry (``retires_at_weakness``).
    - ``live_at_sites``: tuple of ``"module.py:linerange"`` locators that
      concretely embody this compromise. These are the audit anchors —
      future agents grep for the constant name and find the sites
      listed here, or find sites that reference the constant but are
      not listed here (drift signal either way).
    - ``retires_at_weakness``: structural-weakness number from the
      2026-04-23 registry, if applicable. ``None`` when the retirement
      is triggered by data accumulation rather than by a named
      weakness's resolution.
    """

    name: str
    description: str
    retirement_trigger: str
    live_at_sites: tuple[str, ...]
    retires_at_weakness: Optional[int] = None

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("A14Compromise.name must be non-empty")
        if self.name != self.name.upper() or " " in self.name:
            raise ValueError(
                f"A14Compromise.name must be CONSTANT_CASE; got {self.name!r}"
            )
        if not self.description.strip():
            raise ValueError(
                f"A14Compromise.description must be non-empty "
                f"(compromise {self.name!r})"
            )
        if not self.retirement_trigger.strip():
            raise ValueError(
                f"A14Compromise.retirement_trigger must be non-empty "
                f"(compromise {self.name!r}) — A14 discipline requires "
                f"an explicit retirement condition"
            )
        if not self.live_at_sites:
            raise ValueError(
                f"A14Compromise.live_at_sites must name at least one site "
                f"(compromise {self.name!r}) — compromises with no live "
                f"sites should be removed from the registry"
            )
        if self.retires_at_weakness is not None and self.retires_at_weakness < 1:
            raise ValueError(
                f"A14Compromise.retires_at_weakness must be >= 1 or None; "
                f"got {self.retires_at_weakness} (compromise {self.name!r})"
            )


# =============================================================================
# The four runtime-emitted compromises
# =============================================================================


SINGLE_LEVEL_SHRINKAGE = A14Compromise(
    name="SINGLE_LEVEL_SHRINKAGE",
    description=(
        "PlantModel shrinks each cell toward a single generic industry "
        "prior rather than the decided hierarchy (industry → partner → "
        "advertiser → workspace → class). Winner's-curse correction is "
        "present but single-level; the full hierarchical shrinkage that "
        "prevents partner-level and advertiser-level winner's-curse has "
        "not shipped. Every projection that takes this path emits "
        "`winners_curse_portion=True` in CompetingActivations."
    ),
    retirement_trigger=(
        "Weakness #8 (multi-tenant scope) ships, OR one of its "
        "independent pressures fires: second advertiser imminent, or "
        "per-advertiser decline-rate comparison / cross-advertiser "
        "convergence surfaces become load-bearing."
    ),
    live_at_sites=(
        "plant_model.py:86-95 (industry-prior constants header)",
        "plant_model.py:338-366 (_posterior_parameters docstring + impl)",
        "plant_model.py:468-470 (winners_curse flag emit)",
        "adjudicator.py:84-88 (DEFAULT_BIAS_MAGNITUDES winners_curse header)",
    ),
    retires_at_weakness=8,
)


DEPTH_PRIOR_UNVALIDATED = A14Compromise(
    name="DEPTH_PRIOR_UNVALIDATED",
    description=(
        "The autopilot-route / attention-route split on "
        "GoalFulfillmentOutcome is now derived from an expected "
        "processing-depth distribution per posture band "
        "(``_EXPECTED_DEPTH_BY_POSTURE_BAND`` in "
        "``processing_depth_priors.py``) composed with a relative "
        "P(convert | depth) proxy (``_RELATIVE_P_CONVERT_BY_DEPTH``). "
        "This is architectural progress over the former flat "
        "posture-band → route-fraction table (POSTURE_ONLY_ROUTE_SPLIT, "
        "retired 2026-04-25). Two remaining limitations: (a) the "
        "expected distributions are seeded from aggregated external "
        "display-advertising research (Lumen, Bruns et al., "
        "Amplified Intelligence / Nelson-Field, Goldstein) whose "
        "generalization to ADAM's deployment contexts has not been "
        "internally validated; (b) the priors are per-posture-band "
        "rather than per-cell — upstream page intelligence "
        "(Layer-11 processing-depth) can produce per-cell priors "
        "but the wiring is not yet live. Every projection still "
        "emits ``attention_route_residual=True``."
    ),
    retirement_trigger=(
        "Two slices must ship. (1) External threshold + distribution "
        "validation: validate the ProcessingDepth enum thresholds AND "
        "the per-posture expected distributions on ADAM pilot data; "
        "adjust priors or thresholds where they diverge from observed "
        "behavior. (2) Per-cell distribution priors: replace per-"
        "posture-band ``_EXPECTED_DEPTH_BY_POSTURE_BAND`` with "
        "cell-level priors informed by upstream page intelligence "
        "(Layer-11 processing-depth dimension). Retirement triggers "
        "when both ship; partial retirement is not meaningful since "
        "per-cell priors built on unvalidated thresholds inherit the "
        "same bias."
    ),
    live_at_sites=(
        "processing_depth_priors.py (_EXPECTED_DEPTH_BY_POSTURE_BAND + _RELATIVE_P_CONVERT_BY_DEPTH)",
        "plant_model.py (_route_split — consumes expected_route_fractions)",
        "plant_model.py (attention_residual flag emit in _competing_activations)",
        "adjudicator.py (DEFAULT_BIAS_MAGNITUDES attention_route header)",
    ),
    retires_at_weakness=None,
)


COUNTER_REGULATION_UNTRACKED = A14Compromise(
    name="COUNTER_REGULATION_UNTRACKED",
    description=(
        "Habituation and reactance dynamics (counter-regulation) are "
        "carried as a bias flag on CompetingActivations, not as a term "
        "in the plant model. The decided architecture has a per-user "
        "habituation model that the plant model conditions on; the "
        "pilot ships without it because per-user habituation data does "
        "not yet accumulate at useful density. Every projection emits "
        "`counter_regulation_untracked=True`; the adjudicator accounts "
        "for the expected residual via DEFAULT_BIAS_MAGNITUDES."
    ),
    retirement_trigger=(
        "Per-user habituation data accumulates to the density needed "
        "for empirical estimation of habituation / reactance terms. "
        "Likely weeks into pilot at current traffic; dependent on "
        "identity-resolution density in the exposure pipeline."
    ),
    live_at_sites=(
        "plant_model.py:477-480 (counter_regulation=True emit)",
        "adjudicator.py:92-94 (DEFAULT_BIAS_MAGNITUDES counter_regulation header)",
        "projected_impact.py:222 (CompetingActivations.counter_regulation_untracked field)",
    ),
    retires_at_weakness=None,
)


MECHANISM_TAXONOMY_UNVALIDATED = A14Compromise(
    name="MECHANISM_TAXONOMY_UNVALIDATED",
    description=(
        "``adam/intelligence/mechanism_taxonomy.py`` partitions the nine "
        "cognitive mechanisms seeded in migration 004 into "
        "BLEND_COMPATIBLE vs VIGILANCE_ACTIVATING categories, each "
        "carrying a regret-correlation prior in [0, 1]. The partition "
        "is theoretically motivated from the literature (Bargh & "
        "Chartrand on automatic evaluation; Berridge & Robinson on "
        "wanting-liking; Kenrick & Griskevicius on fundamental motives; "
        "Lakoff & Johnson on primary metaphor; Girard on mimetic "
        "desire; Barsalou on embodied cognition; Trope & Liberman on "
        "construal; Tajfel & Turner on social identity; saliency / "
        "orienting literature on attention dynamics). Two mechanisms "
        "are explicitly named borderline in their rationale text "
        "(linguistic_framing, identity_construction) — dominant "
        "classification is shipped but edge cases surface in the "
        "rationale rather than being hidden. Neither the category "
        "assignments nor the regret-correlation priors have been "
        "validated on ADAM pilot data."
    ),
    retirement_trigger=(
        "Empirical validation of (a) the category assignments on pilot "
        "data — do mechanisms classified BLEND_COMPATIBLE actually "
        "produce majority autopilot-route conversions when the "
        "adjudicator's route-split annotation is populated? — and "
        "(b) the regret-correlation priors — do observed post-"
        "conversion regret signals correlate with "
        "regret_correlation_prior values as predicted? Retirement "
        "requires BOTH validations. Per rule 11, the validation must "
        "guard against using regret purely as a reinforcement "
        "signal; regret-free must not imply reinforceable."
    ),
    live_at_sites=(
        "mechanism_taxonomy.py (MECHANISM_TAXONOMY dict + classifications)",
    ),
    retires_at_weakness=None,
)


BLEND_FIT_WEIGHTS_UNVALIDATED = A14Compromise(
    name="BLEND_FIT_WEIGHTS_UNVALIDATED",
    description=(
        "``adam/intelligence/blend_fit.py`` derives a scalar creative "
        "↔ page fit score by confidence-weighted aggregation over six "
        "alignment axes (goal, metaphor, fluency, posture, register, "
        "temporal horizon). The per-axis nominal weights "
        "(``_BLEND_AXIS_WEIGHTS``) are externally motivated by the "
        "attention-inversion platform-core theory — goal alignment "
        "carries the most weight because goal-activation / goal-"
        "fulfillment pairing is the mechanism by which context-primed "
        "goals get fulfilled without demanding attention. The weights "
        "have NOT been empirically calibrated on ADAM pilot data. "
        "Every blend_fit score emitted today is accompanied by a "
        "BlendFitDecomposition naming the per-axis contribution so "
        "downstream selection layers can audit which axes actually "
        "drove the score under these unvalidated weights."
    ),
    retirement_trigger=(
        "Empirical calibration of ``_BLEND_AXIS_WEIGHTS`` on ADAM "
        "pilot data — weights fit to maximize conversion lift on "
        "high-blend_fit creatives vs low-blend_fit creatives within "
        "matched (archetype, context_posture_band) cells, with "
        "explicit guarding against the fitness-function-corruption "
        "risk named in rule 11 (weights must penalize backfire, not "
        "just maximize conversion)."
    ),
    live_at_sites=(
        "blend_fit.py (_BLEND_AXIS_WEIGHTS table)",
        "blend_fit.py (compute_blend_fit aggregation)",
    ),
    retires_at_weakness=None,
)


VARIATIONAL_POSTERIOR_APPROXIMATION = A14Compromise(
    name="VARIATIONAL_POSTERIOR_APPROXIMATION",
    description=(
        "ArchetypeCompressor produces a variational Dirichlet-process "
        "mixture posterior via sklearn's BayesianGaussianMixture. The "
        "decided architecture is NUTS-sampled full hierarchical Bayes "
        "via PyMC, with construct-conditional priors from the "
        "PsychologicalConstruct graph and true multi-level hierarchy "
        "when Weakness #8 lands. Variational posteriors systematically "
        "under-represent tail uncertainty and can produce over-"
        "confident component assignments on well-separated data. Every "
        "ArchetypeCompressionResult emits `posterior_family=\"variational\"` "
        "so downstream consumers (adjudicator, plant-model audit) can "
        "branch on posterior quality when that matters."
    ),
    retirement_trigger=(
        "Either (a) the PsychologicalConstruct graph (migration 028, "
        "slice 5) is dense enough to supply construct-conditional "
        "priors that exercise custom-prior flexibility, or (b) "
        "Weakness #8 (multi-tenant scope) lands and a true multi-level "
        "hierarchy (industry → partner → advertiser → workspace → "
        "class) becomes load-bearing. Whichever fires first. On "
        "retirement the ArchetypeCompressor's internals swap to PyMC "
        "NUTS and emit `posterior_family=\"nuts\"`."
    ),
    live_at_sites=(
        "archetype_compression.py:1-60 (module docstring framing + library choice)",
        "archetype_compression.py (ArchetypeCompressionResult.posterior_family field)",
        "archetype_compression.py (posterior_family emit in fit())",
    ),
    retires_at_weakness=8,
)


# =============================================================================
# Registry
# =============================================================================


ACTIVE_COMPROMISES: tuple[A14Compromise, ...] = (
    SINGLE_LEVEL_SHRINKAGE,
    DEPTH_PRIOR_UNVALIDATED,
    COUNTER_REGULATION_UNTRACKED,
    VARIATIONAL_POSTERIOR_APPROXIMATION,
    BLEND_FIT_WEIGHTS_UNVALIDATED,
    MECHANISM_TAXONOMY_UNVALIDATED,
)
# INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY retired 2026-04-25 by
# adam/intelligence/recommendation_class/chain_attribution.py — the
# Adjudicator now computes strength-weighted attribution when
# chain_reader is injected.
#
# POSTURE_ONLY_ROUTE_SPLIT retired 2026-04-25 and REPLACED by
# DEPTH_PRIOR_UNVALIDATED after the plant-model refactor that derives
# route fractions from expected processing-depth distributions per
# posture band. The decided architecture's full retirement requires
# two further slices (external threshold validation + per-cell
# priors); see DEPTH_PRIOR_UNVALIDATED.retirement_trigger.


def _validate_registry() -> None:
    """Registry-integrity check run at import time.

    Fails loudly if any compromise is malformed or if names collide.
    Drift prevention: if a new compromise is added without populating a
    field, the package fails to import rather than silently shipping an
    unnamed shortcut.
    """
    seen_names: set[str] = set()
    for compromise in ACTIVE_COMPROMISES:
        compromise.validate()
        if compromise.name in seen_names:
            raise ValueError(
                f"A14 registry has duplicate name {compromise.name!r}"
            )
        seen_names.add(compromise.name)


_validate_registry()


# =============================================================================
# Report rendering
# =============================================================================


def format_for_report() -> str:
    """Render the active compromises as a report-pack block.

    Consumed by the weeks 11-12 pilot report pack (pilot plan) so every
    claim shipped to LUXY is accompanied by the exact list of A14
    compromises operating under the claim's adjudication, with the
    explicit retirement conditions. This is the external-surface version
    of the A14 discipline.
    """
    lines: list[str] = ["Active A14 compromises (runtime-emitted):", ""]
    for compromise in ACTIVE_COMPROMISES:
        lines.append(f"- {compromise.name}")
        lines.append(f"  Description: {compromise.description}")
        lines.append(f"  Retirement trigger: {compromise.retirement_trigger}")
        if compromise.retires_at_weakness is not None:
            lines.append(
                f"  Tied to structural weakness #"
                f"{compromise.retires_at_weakness}."
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "A14Compromise",
    "ACTIVE_COMPROMISES",
    "BLEND_FIT_WEIGHTS_UNVALIDATED",
    "COUNTER_REGULATION_UNTRACKED",
    "DEPTH_PRIOR_UNVALIDATED",
    "MECHANISM_TAXONOMY_UNVALIDATED",
    "SINGLE_LEVEL_SHRINKAGE",
    "VARIATIONAL_POSTERIOR_APPROXIMATION",
    "format_for_report",
]
