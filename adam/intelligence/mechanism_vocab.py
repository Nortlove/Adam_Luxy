# =============================================================================
# Mechanism Vocabulary Unification
# Location: adam/intelligence/mechanism_vocab.py
# =============================================================================
"""Bridge cohort-side (Cialdini-style) and canonical (taxonomy) mechanism names.

Closes the soft-fail asymmetry surfaced in Slice 2 honest tags
(commit 51a95ac) and Slice 8 posture-modulation (commit e48679a):

    Two mechanism vocabularies coexist in production code:

      MECHANISM_TAXONOMY (mechanism_taxonomy.py)
        9 canonical mechanisms with literature-anchored
        BLEND_COMPATIBLE / VIGILANCE_ACTIVATING classifications.
        Source: directive Phase 2 mechanism partitioning + migration 004.
        Examples: automatic_evaluation, mimetic_desire, embodied_cognition.

      MECHANISM_DIMENSION_MAP (per_user_posterior_modulation.py)
        18 cohort-side Cialdini-family mechanism names mapping to
        the 27-dim alignment vocabulary.
        Source: legacy cohort priors + L1 archetype priors in
        bilateral_cascade.py:374-389.
        Examples: social_proof, scarcity, authority, loss_aversion.

    Intersection: 5 mechanisms (mimetic_desire, embodied_cognition,
    temporal_construal, attention_dynamics, identity_construction).

WHY THIS MATTERS

Production cascades emit cohort-side names. Without translation:
  - posture_mechanism_prior.compatibility_prior(POSTURE_*, "social_proof")
    → MID (soft-fail) for ALL Cialdini-style mechanisms
  - posture_modulation factor → 1.0 (no-op) on ~13 of 18 mechanisms
  - bid_composer fluency_score in DecisionTrace → uninformative MID
  - Slice 8's structural attention-inversion gate (Phase 2 trilateral
    promotion) silently fires only on the 5-mechanism intersection

This module ships a translation map from cohort-side mechanism names
to their closest canonical-taxonomy equivalent. Posture lookups apply
the translation BEFORE consulting MECHANISM_TAXONOMY, so all 18 cohort-
side mechanisms get correctly classified.

CANONICAL MAPPING

Each cohort-side mechanism is mapped to the canonical taxonomy
mechanism whose psychological substrate best matches it. Mappings
are derived from Bargh-lineage automaticity research + Cialdini's
operationalizations:

  Identity-mapped (5) — same name, no translation needed:
    mimetic_desire, embodied_cognition, temporal_construal,
    attention_dynamics, identity_construction

  Translated (13):
    Cohort-side          → Canonical (Category)
    -------------------  → ----------------------------------------
    social_proof         → mimetic_desire (BLEND_COMPATIBLE)
    liking               → mimetic_desire (BLEND_COMPATIBLE)
    unity                → mimetic_desire (BLEND_COMPATIBLE)
    authority            → automatic_evaluation (BLEND_COMPATIBLE)
    cognitive_ease       → automatic_evaluation (BLEND_COMPATIBLE)
    anchoring            → automatic_evaluation (BLEND_COMPATIBLE)
    reciprocity          → automatic_evaluation (BLEND_COMPATIBLE)
    scarcity             → attention_dynamics (VIGILANCE_ACTIVATING)
    loss_aversion        → attention_dynamics (VIGILANCE_ACTIVATING)
    commitment           → identity_construction (VIGILANCE_ACTIVATING)
    regulatory_focus     → linguistic_framing (BLEND_COMPATIBLE)
    storytelling         → linguistic_framing (BLEND_COMPATIBLE)
    curiosity            → wanting_liking_dissociation (BLEND_COMPATIBLE)

These mappings preserve the BLEND/VIGILANCE diagonal that the
posture-mechanism prior matrix encodes. Cohort-side mechanisms that
operationalize a vigilance-recruiting psychology (scarcity, loss
aversion, commitment) translate to canonical VIGILANCE mechanisms;
those that operate via blend / fluency / automatic evaluation
translate to BLEND mechanisms.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: Cialdini 1984/2021 (six-principle taxonomy of
    influence — social_proof, authority, scarcity, etc.); Bargh
    auto-motive model (canonical taxonomy substrate); the cascade's
    own L1 archetype priors (bilateral_cascade.py:374-389) which
    emit cohort-side names. Translation choices documented inline
    above.

(b) Tests pin: every cohort-side mechanism in MECHANISM_DIMENSION_MAP
    has a translation; every translated value is in MECHANISM_TAXONOMY;
    BLEND ↔ BLEND and VIGILANCE ↔ VIGILANCE diagonals preserved
    where psychologically motivated; identity translation for
    canonical inputs; unknown inputs returned unchanged (soft-fail).

(c) calibration_pending=False — translation is structural, derived
    from the literature. Empirical recalibration of WHICH cohort
    mechanism best maps to WHICH canonical mechanism could come from
    the matched_vs_mismatched_diagonals accumulator (Foundation §2
    test interface) showing ratio differences across translations,
    but the v0.1 mapping is not pilot-tunable.

(d) Honest tags — what is NOT in this slice (named successors):

    * Bidirectional translation (canonical → cohort). Currently
      one-way (cohort → canonical) because the lookups all flow
      that direction. If a canonical-to-cohort path is ever needed,
      the inverse map must be defined explicitly (one canonical
      maps to multiple cohort variants — not a function).
    * Multi-mechanism / blended translations. Some cohort mechanisms
      genuinely span two canonical mechanisms (e.g., curiosity
      arguably blends wanting_liking_dissociation with
      attention_dynamics). v0.1 picks the dominant canonical for
      each; multi-canonical translations are a sibling refinement.
    * Translation directly into the canonical posture-mechanism
      compatibility prior table. Posture_mechanism_prior is updated
      in-place (Slice 11) to consume the translation; this module
      remains the source of truth.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from adam.intelligence.mechanism_taxonomy import MECHANISM_TAXONOMY
from adam.intelligence.per_user_posterior_modulation import (
    MECHANISM_DIMENSION_MAP,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Cohort-side → canonical-taxonomy translation map
# =============================================================================
#
# Five cohort mechanisms are also canonical (identity translation):
#   mimetic_desire, embodied_cognition, temporal_construal,
#   attention_dynamics, identity_construction.
#
# Thirteen cohort mechanisms translate to the canonical mechanism
# whose Bargh-lineage psychology best matches.

COHORT_TO_CANONICAL: Dict[str, str] = {
    # --- Identity (already canonical) ---
    "mimetic_desire": "mimetic_desire",
    "embodied_cognition": "embodied_cognition",
    "temporal_construal": "temporal_construal",
    "attention_dynamics": "attention_dynamics",
    "identity_construction": "identity_construction",

    # --- Translated to BLEND_COMPATIBLE canonicals ---
    "social_proof": "mimetic_desire",
    "liking": "mimetic_desire",
    "unity": "mimetic_desire",
    "authority": "automatic_evaluation",
    "cognitive_ease": "automatic_evaluation",
    "anchoring": "automatic_evaluation",
    "reciprocity": "automatic_evaluation",
    "regulatory_focus": "linguistic_framing",
    "storytelling": "linguistic_framing",
    "curiosity": "wanting_liking_dissociation",

    # --- Translated to VIGILANCE_ACTIVATING canonicals ---
    "scarcity": "attention_dynamics",
    "loss_aversion": "attention_dynamics",
    "commitment": "identity_construction",
}


# =============================================================================
# Translation
# =============================================================================


def to_canonical(mechanism: str) -> str:
    """Translate a cohort-side mechanism name to its canonical-taxonomy
    equivalent. Returns the input unchanged when:

      * the input is already a canonical mechanism (in MECHANISM_TAXONOMY)
      * no translation is registered (soft-fail)

    The unchanged-input return is what makes consumers safely
    composable: a posture_mechanism_prior.compatibility_prior call
    that wraps `to_canonical` first will still produce its canonical-
    soft-fail (MID) for genuinely unknown mechanisms, NOT a hidden
    error.

    Args:
        mechanism: cohort-side name (e.g., "social_proof") OR
            canonical taxonomy name (e.g., "mimetic_desire") OR
            anything else (returned unchanged).

    Returns:
        canonical taxonomy name when translation succeeds;
        input unchanged otherwise.
    """
    if not mechanism:
        return mechanism

    # Already canonical → return as-is.
    if mechanism in MECHANISM_TAXONOMY:
        return mechanism

    # Translatable cohort name → canonical.
    if mechanism in COHORT_TO_CANONICAL:
        return COHORT_TO_CANONICAL[mechanism]

    # Genuinely unknown → return unchanged (caller's soft-fail handles).
    logger.debug(
        "to_canonical: no translation for mechanism %r — returning unchanged",
        mechanism,
    )
    return mechanism


def to_canonical_or_none(mechanism: str) -> Optional[str]:
    """Strict variant — returns None for unknown inputs.

    Use when the caller wants to gate behavior on "did we recognize
    this mechanism at all?". The lenient ``to_canonical`` is the
    default for posture-lookup paths.
    """
    if not mechanism:
        return None
    if mechanism in MECHANISM_TAXONOMY:
        return mechanism
    if mechanism in COHORT_TO_CANONICAL:
        return COHORT_TO_CANONICAL[mechanism]
    return None


# =============================================================================
# Coverage helper — used by tests + diagnostics
# =============================================================================


def cohort_mechanisms_without_translation() -> list:
    """Return cohort mechanisms (in MECHANISM_DIMENSION_MAP) that have
    no entry in COHORT_TO_CANONICAL. Should be empty — every cohort
    mechanism must have a canonical mapping.
    """
    return sorted(
        set(MECHANISM_DIMENSION_MAP.keys()) - set(COHORT_TO_CANONICAL.keys())
    )


def translation_targets_not_in_taxonomy() -> list:
    """Return COHORT_TO_CANONICAL values that aren't in MECHANISM_TAXONOMY.
    Should be empty — every translation target must be a canonical
    mechanism."""
    return sorted(
        set(COHORT_TO_CANONICAL.values()) - set(MECHANISM_TAXONOMY.keys())
    )
