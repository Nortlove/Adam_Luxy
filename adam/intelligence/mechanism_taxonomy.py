"""mechanism_taxonomy — blend-compatible vs vigilance-activating split
(attention-inversion platform-core implication #2).

Partitions the nine ``CognitiveMechanism`` nodes seeded in migration 004
into two route-prior categories so downstream selection, adjudication,
and plant-model projection can condition on whether a mechanism
typically routes conversion through the autopilot path or through the
attention path.

Rationale (Foundation rule 11 + attention-inversion platform core):
- Blend-compatible mechanisms operate below conscious awareness. When
  they drive conversions, the conversion is autopilot-route and
  typically blend-and-fulfill; regret signals are expected to be low.
- Vigilance-activating mechanisms route through conscious attention.
  Conversions are more fragile and more regret-associated. Selection
  pressure SHOULD be aware that reinforcing vigilance mechanisms
  shapes the fitness landscape toward attention-grabbing patterns.

See: ``project_attention_inversion_platform_core.md`` — this module
ships implication #2 of five. Implication #1 is ``blend_fit`` in
``adam/intelligence/blend_fit.py`` (Tier 1 #14).

Scope of THIS slice
-------------------

- ``MechanismRouteCategory`` enum (BLEND_COMPATIBLE / VIGILANCE_ACTIVATING).
- ``MechanismClassification`` frozen dataclass carrying the category,
  a regret-correlation prior [0, 1], a route_prior string, and a
  rationale explaining the classification with literature anchors.
- ``MECHANISM_TAXONOMY`` — the nine-entry dict matching migration 004
  mechanism names.
- ``classify_mechanism(name)`` accessor + partition helpers.
- Registry integrity check at import time.

NOT in this slice (named follow-ups)
------------------------------------

- Selection wiring — the bandit / mechanism_selector doesn't yet
  consult this taxonomy when scoring candidate mechanisms.
- Plant-model ``_route_split`` conditioning on mechanism category —
  currently route fractions come only from posture band.
- Adjudicator regret-signal diagnostics — the
  ``regret_correlation_prior`` field is a prior expectation; pairing
  it with observed regret signals (attention-inversion implication #5)
  is a separate slice.
- Empirical validation on ADAM pilot data — named in
  ``a14_compromises.MECHANISM_TAXONOMY_UNVALIDATED``.

Classification discipline (orientation A1, A5)
----------------------------------------------

- Each classification names a primary literature anchor in the
  rationale. No "obvious" assignments.
- Borderline mechanisms (linguistic_framing, identity_construction)
  are named explicitly in their rationale text, not hidden in a
  dominant-category assignment.
- ``regret_correlation_prior`` values are theoretically motivated,
  NOT calibrated on ADAM data. They're A14 priors; the retirement
  trigger names the empirical validation slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Literal


# =============================================================================
# Types
# =============================================================================


class MechanismRouteCategory(str, Enum):
    """Route-prior category for a cognitive mechanism.

    ``BLEND_COMPATIBLE``: the mechanism typically operates below
    conscious awareness; conversions it drives are autopilot-route in
    expectation.

    ``VIGILANCE_ACTIVATING``: the mechanism typically routes through
    conscious attention; conversions are more regret-associated in
    expectation.
    """
    BLEND_COMPATIBLE = "blend_compatible"
    VIGILANCE_ACTIVATING = "vigilance_activating"


RoutePrior = Literal["autopilot", "attention"]


@dataclass(frozen=True)
class MechanismClassification:
    """One mechanism's route-prior classification.

    ``regret_correlation_prior``: theoretically-motivated [0, 1] prior
    over how strongly post-conversion regret signals should correlate
    with this mechanism's usage. Higher = more regret-correlation
    expected (vigilance mechanisms route conversions through conscious
    evaluation, which can be subsequently reassessed negatively). A14
    prior — see ``a14_compromises.MECHANISM_TAXONOMY_UNVALIDATED``.

    ``route_prior``: the projected route category. Must be consistent
    with ``category`` — enforced at registry-integrity check time.

    ``rationale``: primary literature anchor + reasoning for the
    classification. Mandatory, non-empty — stays honest about
    borderline cases by naming them explicitly rather than hiding
    them in a dominant assignment.
    """
    mechanism_name: str
    category: MechanismRouteCategory
    regret_correlation_prior: float
    route_prior: RoutePrior
    rationale: str

    def validate(self) -> None:
        if not self.mechanism_name.strip():
            raise ValueError("mechanism_name must be non-empty")
        if not (0.0 <= self.regret_correlation_prior <= 1.0):
            raise ValueError(
                f"regret_correlation_prior {self.regret_correlation_prior} "
                f"outside [0, 1] (mechanism {self.mechanism_name!r})"
            )
        # Category / route_prior consistency.
        expected_route: RoutePrior = (
            "autopilot"
            if self.category == MechanismRouteCategory.BLEND_COMPATIBLE
            else "attention"
        )
        if self.route_prior != expected_route:
            raise ValueError(
                f"route_prior {self.route_prior!r} inconsistent with "
                f"category {self.category.value!r} "
                f"(mechanism {self.mechanism_name!r})"
            )
        if not self.rationale.strip():
            raise ValueError(
                f"rationale must be non-empty (mechanism {self.mechanism_name!r})"
            )


# =============================================================================
# Taxonomy — must match migration 004 mechanism names exactly
# =============================================================================


MECHANISM_TAXONOMY: Dict[str, MechanismClassification] = {
    # -- BLEND-COMPATIBLE ---------------------------------------------------
    "automatic_evaluation": MechanismClassification(
        mechanism_name="automatic_evaluation",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.15,
        route_prior="autopilot",
        rationale=(
            "Bargh & Chartrand 1999 automatic attitude activation. "
            "Evaluation fires without awareness of the evaluation "
            "process; conversions driven via this mechanism are "
            "autopilot-route. Low regret correlation expected — the "
            "decision never surfaced for conscious reassessment."
        ),
    ),
    "wanting_liking_dissociation": MechanismClassification(
        mechanism_name="wanting_liking_dissociation",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.20,
        route_prior="autopilot",
        rationale=(
            "Berridge & Robinson 1998 / 2016 incentive-salience theory. "
            "Dopaminergic 'wanting' operates below conscious reportability; "
            "'liking' is hedonic and partly conscious. The mechanism's "
            "leverage is on wanting, which routes autopilot. Mild regret "
            "uptick over automatic_evaluation because liking/wanting "
            "mismatch can surface retrospectively."
        ),
    ),
    "evolutionary_motive_activation": MechanismClassification(
        mechanism_name="evolutionary_motive_activation",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.20,
        route_prior="autopilot",
        rationale=(
            "Kenrick & Griskevicius 2013 fundamental motives framework. "
            "Motive-system activation (self-protection, status, mate "
            "acquisition) operates below awareness; behavioral "
            "consequences are reportable but the motive substrate is "
            "not. Autopilot-route; low-to-moderate regret correlation."
        ),
    ),
    "linguistic_framing": MechanismClassification(
        mechanism_name="linguistic_framing",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.25,
        route_prior="autopilot",
        rationale=(
            "Lakoff & Johnson primary-metaphor work + Trope & Liberman "
            "construal cues. The mechanism's core leverage is via "
            "embodied primary-metaphor activation — automatic and "
            "pre-reflective. BORDERLINE: explicit / overt framing "
            "('notice how they phrase X') can surface the mechanism "
            "for conscious reassessment, triggering reactance. "
            "Modal case is autopilot; vigilance risk is on overt "
            "framing. Regret correlation sits mid-low."
        ),
    ),
    "mimetic_desire": MechanismClassification(
        mechanism_name="mimetic_desire",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.20,
        route_prior="autopilot",
        rationale=(
            "Girard mimetic-desire lineage + social-proof imitation "
            "work. Observing others wanting / using something activates "
            "analogous wanting in the observer automatically. Classic "
            "autopilot imitation; autopilot-route conversions dominate."
        ),
    ),
    "embodied_cognition": MechanismClassification(
        mechanism_name="embodied_cognition",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.15,
        route_prior="autopilot",
        rationale=(
            "Barsalou 1999 grounded cognition. Perceptual-motor "
            "simulation underlying comprehension is automatic and "
            "nonconscious. Conversions driven by embodied-cognition "
            "cues (e.g., tactile / spatial / temperature metaphors) "
            "route autopilot. Low regret correlation."
        ),
    ),
    "temporal_construal": MechanismClassification(
        mechanism_name="temporal_construal",
        category=MechanismRouteCategory.BLEND_COMPATIBLE,
        regret_correlation_prior=0.20,
        route_prior="autopilot",
        rationale=(
            "Trope & Liberman 2010 construal-level theory. "
            "Construal-level shifts are automatic responses to "
            "psychological-distance cues; the mechanism's leverage is "
            "at the construal-shift moment, not through conscious "
            "deliberation about distance. Autopilot-route."
        ),
    ),

    # -- VIGILANCE-ACTIVATING -----------------------------------------------
    "attention_dynamics": MechanismClassification(
        mechanism_name="attention_dynamics",
        category=MechanismRouteCategory.VIGILANCE_ACTIVATING,
        regret_correlation_prior=0.70,
        route_prior="attention",
        rationale=(
            "Saliency / orienting / pop-out manipulation. The "
            "mechanism IS attention capture — it activates conscious "
            "attention by definition. Archetype of the attention-"
            "grabbing pattern the attention-inversion principle warns "
            "against. High regret correlation expected — post-capture "
            "conversions are classically regret-associated (Pavlovian "
            "post-purchase dissonance)."
        ),
    ),
    "identity_construction": MechanismClassification(
        mechanism_name="identity_construction",
        category=MechanismRouteCategory.VIGILANCE_ACTIVATING,
        regret_correlation_prior=0.50,
        route_prior="attention",
        rationale=(
            "Social Identity Theory (Tajfel & Turner) + identity-threat "
            "literature (Sherman & Cohen). BORDERLINE: identity "
            "ACTIVATION ('for people like you') can land autopilot via "
            "group affiliation cues, but identity CONSTRUCTION (the "
            "mechanism's name) implies active identity work — "
            "'become who you want to be' framing triggers conscious "
            "self-evaluation. Identity-threat framing is classically "
            "reactance-inducing. Moderate regret correlation; "
            "classification is dominant-case rather than universal."
        ),
    ),
}


# =============================================================================
# Accessors
# =============================================================================


def classify_mechanism(mechanism_name: str) -> MechanismClassification:
    """Return the classification for a mechanism.

    Unknown mechanism names raise ``KeyError`` — the taxonomy must be
    kept in sync with migration 004, and silent-default fallback would
    let drift hide.
    """
    if mechanism_name not in MECHANISM_TAXONOMY:
        raise KeyError(
            f"unknown mechanism {mechanism_name!r}; "
            f"must be one of {sorted(MECHANISM_TAXONOMY.keys())}"
        )
    return MECHANISM_TAXONOMY[mechanism_name]


def blend_compatible_mechanisms() -> List[str]:
    """Return mechanism names classified as BLEND_COMPATIBLE, sorted."""
    return sorted(
        name
        for name, cls in MECHANISM_TAXONOMY.items()
        if cls.category == MechanismRouteCategory.BLEND_COMPATIBLE
    )


def vigilance_activating_mechanisms() -> List[str]:
    """Return mechanism names classified as VIGILANCE_ACTIVATING, sorted."""
    return sorted(
        name
        for name, cls in MECHANISM_TAXONOMY.items()
        if cls.category == MechanismRouteCategory.VIGILANCE_ACTIVATING
    )


# =============================================================================
# Registry integrity — run at import time
# =============================================================================


_EXPECTED_MECHANISM_NAMES = frozenset({
    "automatic_evaluation",
    "wanting_liking_dissociation",
    "evolutionary_motive_activation",
    "linguistic_framing",
    "mimetic_desire",
    "embodied_cognition",
    "attention_dynamics",
    "identity_construction",
    "temporal_construal",
})
"""The nine mechanisms seeded in migration 004. Kept as a frozen set
here to assert the taxonomy matches. If migration 004 ever adds a
mechanism, this set AND ``MECHANISM_TAXONOMY`` both need an update."""


def _validate_taxonomy_at_import() -> None:
    # Every entry is well-formed.
    for name, cls in MECHANISM_TAXONOMY.items():
        cls.validate()
        if cls.mechanism_name != name:
            raise ValueError(
                f"MECHANISM_TAXONOMY key {name!r} != "
                f"classification.mechanism_name {cls.mechanism_name!r}"
            )
    # Coverage: every seeded mechanism has a classification.
    missing = _EXPECTED_MECHANISM_NAMES - set(MECHANISM_TAXONOMY.keys())
    if missing:
        raise ValueError(
            f"MECHANISM_TAXONOMY missing classifications for: "
            f"{sorted(missing)}"
        )
    extra = set(MECHANISM_TAXONOMY.keys()) - _EXPECTED_MECHANISM_NAMES
    if extra:
        raise ValueError(
            f"MECHANISM_TAXONOMY has classifications for mechanisms "
            f"not in migration 004: {sorted(extra)}. If migration 004 "
            f"was updated, update _EXPECTED_MECHANISM_NAMES too."
        )


_validate_taxonomy_at_import()


__all__ = [
    "MECHANISM_TAXONOMY",
    "MechanismClassification",
    "MechanismRouteCategory",
    "blend_compatible_mechanisms",
    "classify_mechanism",
    "vigilance_activating_mechanisms",
]
