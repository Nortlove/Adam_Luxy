"""Argument Constitution — auditable principles governing CLAUDE_ARGUMENT output.

This module is the source-of-truth text that drives the CAI critique-revise
loop spec'd in the Seven-Component Methodological Upgrade Handoff §6
(Component #6 — Constitutional AI for CLAUDE_ARGUMENT).

Why a constitution is necessary:
    Claude generates an argument → it ships to retargeting unaudited. The
    handoff §6.1 names three risks:
      1. Factual hallucination → FTC false-advertising liability
      2. Archetype tone mismatch (Disillusioned-targeted user receives
         Status-Seeker hype tone)
      3. Brand-safety drift
    Without the constitution, every offline-generated argument is
    uncontrolled output. The constitution is the rubric against which the
    critic LLM scores generated arguments before they're cached for the
    cascade hot path.

Composition rule:
    A complete constitutional check assembles one ARCHETYPE slice + one
    MECHANISM slice + the four CROSS-CUTTING principles. Both slices are
    selected by the cascade's resolved (archetype, primary_mechanism)
    pair at generation time. The cache key includes CONSTITUTION_VERSION
    so a bump invalidates all cached arguments.

Ship discipline:
    - The principle text is hand-authored: this IS the editable governance
      surface, not synthetic intelligence. Future-Chris reads and edits it.
    - Where the handoff §6.3 specifies wording, that wording is preserved
      verbatim — see the per-archetype slices below.
    - No principles are invented. The cross-cutting blend_dont_grab
      principle comes from the attention-inversion platform commitment
      (memory: project_attention_inversion_platform_core); the others come
      from handoff §6.3.
    - Versioning is explicit. Bump CONSTITUTION_VERSION on principle
      change so cache keys invalidate. The change-log lives in the docstring
      of CONSTITUTION_VERSION.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple


CONSTITUTION_VERSION = "v1.0"
"""Constitution version. Bump on any principle change.

Change log:
    v1.0 (2026-04-27): Initial draft. Per-archetype slices preserve
        handoff §6.3 wording; per-mechanism slices derived from canonical
        Cialdini definitions; cross-cutting principles are
        factual_grounding, ftc_compliance, mechanism_faithful, and
        blend_dont_grab.
"""


# -----------------------------------------------------------------------------
# Slice schema
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchetypeSlice:
    """The tone principle for one of the five archetypes.

    Sources: handoff §6.3 wording verbatim. No invention.
    """

    archetype: str
    tone_principle: str
    what_works: FrozenSet[str]
    what_fails: FrozenSet[str]


@dataclass(frozen=True)
class MechanismSlice:
    """The mechanism-faithfulness principle for one Cialdini mechanism.

    The handoff §6.3 mechanism_faithful principle says: 'if mechanism=$X,
    the argument must concretely invoke that Cialdini principle.' These
    slices specify what 'concretely invoke' means per mechanism and what
    fails — drawn from canonical Cialdini definitions (Influence, 1984;
    revised 2021 with the unity principle).
    """

    mechanism: str
    must_concretely_invoke: str
    forbidden_substitutes: FrozenSet[str]


@dataclass(frozen=True)
class CrossCuttingPrinciple:
    """A constitutional principle that applies to every argument."""

    name: str
    rule: str
    why: str


@dataclass(frozen=True)
class ComposedConstitution:
    """The full constitutional bundle for one (archetype, mechanism) pair.

    This is what the critic LLM receives as the rubric. The composition
    is deterministic — the cache key is (brand_id, archetype, mechanism,
    barrier_hash, CONSTITUTION_VERSION).
    """

    archetype_slice: ArchetypeSlice
    mechanism_slice: MechanismSlice
    cross_cutting: Tuple[CrossCuttingPrinciple, ...]
    constitution_version: str = CONSTITUTION_VERSION


# -----------------------------------------------------------------------------
# The five archetype slices — handoff §6.3 wording preserved verbatim
# -----------------------------------------------------------------------------


_ARCHETYPE_SLICES: Dict[str, ArchetypeSlice] = {
    "status_seeker": ArchetypeSlice(
        archetype="status_seeker",
        tone_principle=(
            "exclusivity, signaling, aspirational identity; no self-deprecation"
        ),
        what_works=frozenset({
            "exclusivity_signal",
            "aspirational_identity",
            "in_group_recognition",
            "elevated_register",
        }),
        what_fails=frozenset({
            "self_deprecation",
            "humble_brag",
            "low_status_framing",
            "everyman_appeal",
        }),
    ),
    "easy_decider": ArchetypeSlice(
        archetype="easy_decider",
        tone_principle=(
            "concise, single CTA; no information overload"
        ),
        what_works=frozenset({
            "single_cta",
            "concise_value",
            "low_cognitive_load",
            "short_sentences",
        }),
        what_fails=frozenset({
            "multiple_ctas",
            "information_overload",
            "comparative_table",
            "long_explanation",
        }),
    ),
    "careful_truster": ArchetypeSlice(
        archetype="careful_truster",
        tone_principle=(
            "transparency, guarantees, provenance; no scarcity gimmicks"
        ),
        what_works=frozenset({
            "transparency",
            "guarantee_or_warranty",
            "provenance_or_origin",
            "third_party_certification",
        }),
        what_fails=frozenset({
            "scarcity_gimmick",
            "countdown_timer",
            "limited_quantity_claim",
            "manufactured_urgency",
        }),
    ),
    "skeptical_analyst": ArchetypeSlice(
        archetype="skeptical_analyst",
        tone_principle=(
            "verifiable specs, comparative data, third-party evidence; no hyperbole"
        ),
        what_works=frozenset({
            "verifiable_spec",
            "comparative_data",
            "third_party_evidence",
            "citation_or_source",
        }),
        what_fails=frozenset({
            "hyperbole",
            "best_in_class_claim",
            "superlative_without_source",
            "emotional_appeal",
        }),
    ),
    "disillusioned": ArchetypeSlice(
        archetype="disillusioned",
        tone_principle=(
            "empathetic, low-pressure, acknowledge prior disappointments; no urgency"
        ),
        what_works=frozenset({
            "empathy_acknowledgment",
            "low_pressure_register",
            "prior_disappointment_awareness",
            "no_obligation_framing",
        }),
        what_fails=frozenset({
            "urgency_language",
            "high_pressure_close",
            "fomo_appeal",
            "aspirational_hype",
        }),
    ),
}


# -----------------------------------------------------------------------------
# The ten mechanism slices — Cialdini-faithful invocation specs
# -----------------------------------------------------------------------------
# ADAM's mechanism vocabulary in adam/constants.py:MECHANISMS lists 10 (the
# handoff says "9" — small discrepancy; we cover all 10). Each spec answers
# the §6.3 mechanism_faithful question: what does 'concretely invoke this
# principle' mean, and what counts as a forbidden substitute?


_MECHANISM_SLICES: Dict[str, MechanismSlice] = {
    "social_proof": MechanismSlice(
        mechanism="social_proof",
        must_concretely_invoke=(
            "specific peer behavior — count, segment, or behavior of similar "
            "others choosing the product. Generic 'people love it' fails."
        ),
        forbidden_substitutes=frozenset({
            "generic_popularity_claim",
            "vague_widespread_use",
            "anonymous_endorsement",
        }),
    ),
    "authority": MechanismSlice(
        mechanism="authority",
        must_concretely_invoke=(
            "named expert, certification body, or institutional endorsement "
            "with verifiable credentials. 'Experts agree' without naming fails."
        ),
        forbidden_substitutes=frozenset({
            "anonymous_expert_claim",
            "uncited_research",
            "implied_authority_via_aesthetic",
        }),
    ),
    "scarcity": MechanismSlice(
        mechanism="scarcity",
        must_concretely_invoke=(
            "verifiable supply or time constraint with a real-world cause "
            "(production capacity, seasonal availability, manufacturing batch). "
            "Manufactured urgency without a real constraint fails."
        ),
        forbidden_substitutes=frozenset({
            "manufactured_urgency",
            "fake_countdown",
            "permanent_'limited'_offer",
        }),
    ),
    "reciprocity": MechanismSlice(
        mechanism="reciprocity",
        must_concretely_invoke=(
            "concrete first-mover gift, free trial, or value transfer to the "
            "buyer with no purchase precondition. Discount-as-reciprocity fails."
        ),
        forbidden_substitutes=frozenset({
            "discount_framed_as_gift",
            "purchase_required_'gift'",
            "implied_obligation_without_value",
        }),
    ),
    "commitment": MechanismSlice(
        mechanism="commitment",
        must_concretely_invoke=(
            "small, low-friction first step that aligns with the buyer's "
            "stated values or prior expressed preferences (foot-in-the-door, "
            "Cialdini 1984). Direct ask without anchoring fails."
        ),
        forbidden_substitutes=frozenset({
            "direct_high_commitment_ask",
            "value_misaligned_first_step",
            "manipulation_via_self_perception",
        }),
    ),
    "liking": MechanismSlice(
        mechanism="liking",
        must_concretely_invoke=(
            "concrete similarity, shared value, or shared identity between "
            "buyer and brand/spokesperson. Generic 'people like you' without "
            "specified shared trait fails."
        ),
        forbidden_substitutes=frozenset({
            "generic_'people_like_you'",
            "demographic_proxy_for_similarity",
            "manufactured_familiarity",
        }),
    ),
    "unity": MechanismSlice(
        mechanism="unity",
        must_concretely_invoke=(
            "shared category-defining identity (Cialdini 2021 — the "
            "we-identity). The buyer and brand belong to the same "
            "self-relevant in-group. Mere demographic targeting fails."
        ),
        forbidden_substitutes=frozenset({
            "demographic_'community'_claim",
            "tribal_aesthetic_without_substance",
            "vague_'we'_pronouns",
        }),
    ),
    "cognitive_ease": MechanismSlice(
        mechanism="cognitive_ease",
        must_concretely_invoke=(
            "fluent processing — short sentences, familiar vocabulary, "
            "single-claim structure, no novel jargon. Complexity disguised "
            "as clarity fails."
        ),
        forbidden_substitutes=frozenset({
            "marketing_jargon",
            "compound_claims",
            "novel_terminology_without_definition",
        }),
    ),
    "curiosity": MechanismSlice(
        mechanism="curiosity",
        must_concretely_invoke=(
            "specific information gap (Loewenstein 1994) — the buyer can "
            "name what they don't know but want to. Vague intrigue fails."
        ),
        forbidden_substitutes=frozenset({
            "clickbait_tease",
            "information_withholding",
            "vague_intrigue_without_payoff",
        }),
    ),
    "loss_aversion": MechanismSlice(
        mechanism="loss_aversion",
        must_concretely_invoke=(
            "specific loss the buyer would experience without the product, "
            "framed against their current state (Kahneman-Tversky 1979). "
            "Generic FOMO fails."
        ),
        forbidden_substitutes=frozenset({
            "generic_fomo",
            "'don't_miss_out'_without_specified_loss",
            "loss_frame_without_endowment",
        }),
    ),
}


# -----------------------------------------------------------------------------
# Cross-cutting principles — apply to every (archetype, mechanism) pair
# -----------------------------------------------------------------------------
# Order matters: factual_grounding and ftc_compliance are non-negotiable
# legal/safety floor; blend_dont_grab is the strategic platform commitment;
# mechanism_faithful is the architectural commitment to the construct
# vocabulary.


_CROSS_CUTTING: Tuple[CrossCuttingPrinciple, ...] = (
    CrossCuttingPrinciple(
        name="factual_grounding",
        rule=(
            "Every factual claim in the argument must trace to the brand's "
            "verified knowledge base (website, datasheet, regulatory "
            "filing). Claims without traceable provenance fail."
        ),
        why=(
            "Handoff §6.1 — factual hallucination is the FTC false-advertising "
            "liability surface. Component 6's FActScore (Min et al. 2023) "
            "operationalizes this by atomic-fact decomposition against "
            "brand_kb."
        ),
    ),
    CrossCuttingPrinciple(
        name="ftc_compliance",
        rule=(
            "No unverifiable testimonials. No implied medical, financial, "
            "or weight-loss outcomes without substantiation. All material "
            "connections (paid endorsement, employee status, sponsored "
            "content) must be disclosed."
        ),
        why=(
            "Handoff §6.3 — FTC false-advertising and material-connection "
            "disclosure rules are statutory minimum, not aesthetic preference."
        ),
    ),
    CrossCuttingPrinciple(
        name="blend_dont_grab",
        rule=(
            "The argument must read as CONTINUOUS with the attentional pattern "
            "of the surrounding context AND offer affordance toward a goal "
            "the surroundings primed. It must NOT signal advertising "
            "linguistically. Industry-default framings — 'compelling headline,' "
            "'break through the noise,' 'stand out from competitors,' "
            "'attention-grabbing,' 'eye-catching' — are forbidden because they "
            "trigger the vigilance route the platform exists to avoid."
        ),
        why=(
            "Attention-inversion is the platform's deepest strategic "
            "commitment (memory: project_attention_inversion_platform_core). "
            "Industry frames attention-as-conversion; ADAM's frame is "
            "attention-as-barrier. A 'compelling' headline by industry "
            "criteria is a structural failure by ADAM criteria."
        ),
    ),
    CrossCuttingPrinciple(
        name="mechanism_faithful",
        rule=(
            "If the cascade resolved primary_mechanism=X, the argument must "
            "concretely invoke X per its mechanism slice — not a paraphrase, "
            "not a forbidden substitute, not a different mechanism that "
            "happens to sound similar."
        ),
        why=(
            "Handoff §6.3 mechanism_faithful — the cascade resolved a "
            "specific mechanism on bilateral edge evidence; the argument "
            "must operationalize that resolution. Substituting a different "
            "Cialdini principle silently severs the decision-to-creative "
            "chain that the learning loop attributes outcomes to."
        ),
    ),
)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def get_archetype_slice(archetype: str) -> Optional[ArchetypeSlice]:
    """Return the archetype slice for one of the five canonical archetypes.

    Names match handoff §6.3: status_seeker, easy_decider, careful_truster,
    skeptical_analyst, disillusioned. Returns None for unrecognized names —
    the caller decides whether to soft-fail or raise.
    """
    return _ARCHETYPE_SLICES.get(archetype.lower())


def get_mechanism_slice(mechanism: str) -> Optional[MechanismSlice]:
    """Return the mechanism slice for one of the ten ADAM mechanisms.

    Names match adam/constants.py:MECHANISMS. Returns None for
    unrecognized names.
    """
    return _MECHANISM_SLICES.get(mechanism.lower())


def get_cross_cutting_principles() -> Tuple[CrossCuttingPrinciple, ...]:
    """Return all four cross-cutting principles in canonical order."""
    return _CROSS_CUTTING


def compose_constitution(
    archetype: str, mechanism: str,
) -> Optional[ComposedConstitution]:
    """Assemble the full constitution for one (archetype, mechanism) pair.

    This is what the critic LLM receives as its rubric. Returns None if
    either slice is unrecognized — the caller is responsible for handling
    the missing case (typically: log + fall through to template path).
    """
    arch_slice = get_archetype_slice(archetype)
    mech_slice = get_mechanism_slice(mechanism)
    if arch_slice is None or mech_slice is None:
        return None
    return ComposedConstitution(
        archetype_slice=arch_slice,
        mechanism_slice=mech_slice,
        cross_cutting=_CROSS_CUTTING,
    )


def known_archetypes() -> FrozenSet[str]:
    """Return the canonical archetype names."""
    return frozenset(_ARCHETYPE_SLICES.keys())


def known_mechanisms() -> FrozenSet[str]:
    """Return the canonical mechanism names."""
    return frozenset(_MECHANISM_SLICES.keys())
