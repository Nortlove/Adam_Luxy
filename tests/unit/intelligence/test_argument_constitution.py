"""Pin the argument constitution — auditable governance for CLAUDE_ARGUMENT.

Discipline anchors:
    - Archetype slices preserve handoff §6.3 wording verbatim. Drift in
      this wording silently rewrites the rubric the critic LLM is graded
      against, which silently changes what arguments survive caching.
    - Mechanism faithfulness slices match ADAM's canonical mechanism list
      in adam/constants.py:MECHANISMS. A mismatch means the cascade can
      resolve a mechanism the constitution can't audit.
    - The blend_dont_grab principle is the platform's deepest strategic
      commitment (attention-inversion). Removing or weakening it would
      align the constitution with industry-default 'compelling headline'
      framings — exactly the structural failure mode the platform exists
      to avoid.
    - CONSTITUTION_VERSION is part of the cache key. Bumping the version
      MUST invalidate cached arguments (validated at the cache-layer test;
      this test pins that the version is exposed and immutable).
"""

from __future__ import annotations

import dataclasses

import pytest

from adam.constants import MECHANISMS
from adam.intelligence.argument_constitution import (
    ArchetypeSlice,
    ComposedConstitution,
    CONSTITUTION_VERSION,
    CrossCuttingPrinciple,
    MechanismSlice,
    compose_constitution,
    get_archetype_slice,
    get_cross_cutting_principles,
    get_mechanism_slice,
    known_archetypes,
    known_mechanisms,
)


# -----------------------------------------------------------------------------
# Coverage — every canonical archetype + mechanism resolves
# -----------------------------------------------------------------------------


CANONICAL_ARCHETYPES = {
    "status_seeker", "easy_decider", "careful_truster",
    "skeptical_analyst", "disillusioned",
}


def test_all_canonical_archetypes_have_slices():
    """Handoff §6.3 names exactly five archetypes; the constitution must
    cover all five. A missing slice means a cascade that resolves to that
    archetype has no rubric for the critic LLM."""
    assert known_archetypes() == CANONICAL_ARCHETYPES


def test_all_canonical_mechanisms_have_slices():
    """The constitution's mechanism vocabulary must match ADAM's canonical
    mechanism list. Drift here means the cascade can resolve a mechanism
    the constitution can't audit, breaking the learning loop's
    decision-to-creative attribution chain."""
    expected = {m.lower() for m in MECHANISMS}
    assert known_mechanisms() == expected


def test_every_archetype_lookup_returns_slice():
    for arch in CANONICAL_ARCHETYPES:
        slice_ = get_archetype_slice(arch)
        assert slice_ is not None
        assert slice_.archetype == arch


def test_every_mechanism_lookup_returns_slice():
    for mech in MECHANISMS:
        slice_ = get_mechanism_slice(mech)
        assert slice_ is not None
        assert slice_.mechanism == mech


# -----------------------------------------------------------------------------
# Handoff §6.3 wording preservation — verbatim text
# -----------------------------------------------------------------------------


def test_handoff_archetype_wording_preserved():
    """Handoff §6.3 specifies the tone-principle wording per archetype.
    These strings are reproduced verbatim. If the wording changes here
    without a CONSTITUTION_VERSION bump, the rubric silently drifts."""
    expected_wording = {
        "status_seeker": "exclusivity, signaling, aspirational identity; no self-deprecation",
        "easy_decider": "concise, single CTA; no information overload",
        "careful_truster": "transparency, guarantees, provenance; no scarcity gimmicks",
        "skeptical_analyst": "verifiable specs, comparative data, third-party evidence; no hyperbole",
        "disillusioned": "empathetic, low-pressure, acknowledge prior disappointments; no urgency",
    }
    for arch, expected in expected_wording.items():
        slice_ = get_archetype_slice(arch)
        assert slice_.tone_principle == expected, (
            f"{arch} tone_principle drifted from handoff §6.3 wording"
        )


# -----------------------------------------------------------------------------
# Cross-cutting principles — non-negotiable presence
# -----------------------------------------------------------------------------


def test_four_cross_cutting_principles_in_canonical_order():
    """Order is part of the contract — the critic LLM receives them in
    this order, with factual_grounding + ftc_compliance as the legal
    floor, blend_dont_grab as the strategic commitment, and
    mechanism_faithful as the architectural commitment."""
    principles = get_cross_cutting_principles()
    names = [p.name for p in principles]
    assert names == [
        "factual_grounding",
        "ftc_compliance",
        "blend_dont_grab",
        "mechanism_faithful",
    ]


def test_blend_dont_grab_forbids_industry_default_framings():
    """The blend_dont_grab principle is the platform's deepest strategic
    commitment. The forbidden framings ('compelling,' 'break through the
    noise,' 'stand out,' 'attention-grabbing,' 'eye-catching') must be
    explicitly listed in the rule text — this is what the critic LLM
    looks for."""
    principles = {p.name: p for p in get_cross_cutting_principles()}
    rule = principles["blend_dont_grab"].rule.lower()
    for forbidden in (
        "compelling", "break through", "stand out",
        "attention-grabbing", "eye-catching",
    ):
        assert forbidden in rule, (
            f"blend_dont_grab rule must explicitly forbid '{forbidden}' "
            "to keep the critic LLM grounded"
        )


def test_ftc_compliance_names_required_disclosures():
    principles = {p.name: p for p in get_cross_cutting_principles()}
    rule = principles["ftc_compliance"].rule.lower()
    # Material-connection disclosure is statutory; testimonial substantiation
    # is statutory; medical/financial/weight-loss are FTC enforcement priorities
    assert "testimonial" in rule
    assert "material connection" in rule


# -----------------------------------------------------------------------------
# Compose path — assembles archetype + mechanism + cross-cutting
# -----------------------------------------------------------------------------


def test_compose_returns_full_bundle():
    bundle = compose_constitution("status_seeker", "social_proof")
    assert bundle is not None
    assert isinstance(bundle, ComposedConstitution)
    assert bundle.archetype_slice.archetype == "status_seeker"
    assert bundle.mechanism_slice.mechanism == "social_proof"
    assert len(bundle.cross_cutting) == 4
    assert bundle.constitution_version == CONSTITUTION_VERSION


def test_compose_case_insensitive_lookup():
    """Cascade may pass uppercase or mixed-case archetype/mechanism names.
    Lookup must be case-insensitive — drift between cascade vocabulary
    and constitution lookup keys would silently hit the soft-fail path."""
    bundle = compose_constitution("STATUS_SEEKER", "Social_Proof")
    assert bundle is not None


def test_compose_unknown_archetype_returns_none():
    """Soft-fail on unknown archetype — caller falls through to template
    path rather than crashing the cascade. NEVER raises."""
    bundle = compose_constitution("totally_made_up", "social_proof")
    assert bundle is None


def test_compose_unknown_mechanism_returns_none():
    bundle = compose_constitution("status_seeker", "totally_made_up")
    assert bundle is None


def test_compose_resolves_for_every_canonical_pair():
    """Cartesian product: 5 archetypes × 10 mechanisms = 50 cells.
    Every cell must resolve. A None return on any canonical pair means
    the cascade has a real-traffic resolution the constitution can't
    audit."""
    for arch in CANONICAL_ARCHETYPES:
        for mech in MECHANISMS:
            bundle = compose_constitution(arch, mech)
            assert bundle is not None, f"{arch} × {mech} failed to compose"


# -----------------------------------------------------------------------------
# Immutability — slices and principles are frozen
# -----------------------------------------------------------------------------


def test_archetype_slice_is_frozen():
    """Frozen dataclass — accidental mutation at runtime is impossible.
    A non-frozen slice would let a downstream caller silently rewrite
    the rubric for everyone."""
    slice_ = get_archetype_slice("status_seeker")
    with pytest.raises(dataclasses.FrozenInstanceError):
        slice_.tone_principle = "drift"


def test_mechanism_slice_is_frozen():
    slice_ = get_mechanism_slice("social_proof")
    with pytest.raises(dataclasses.FrozenInstanceError):
        slice_.must_concretely_invoke = "drift"


def test_cross_cutting_principle_is_frozen():
    principles = get_cross_cutting_principles()
    with pytest.raises(dataclasses.FrozenInstanceError):
        principles[0].rule = "drift"


# -----------------------------------------------------------------------------
# Versioning — bumps must invalidate caches downstream
# -----------------------------------------------------------------------------


def test_constitution_version_is_set():
    """CONSTITUTION_VERSION must be a non-empty string. The cache layer
    keys arguments by (brand_id, archetype, mechanism, barrier_hash,
    CONSTITUTION_VERSION); an empty version would break that key."""
    assert isinstance(CONSTITUTION_VERSION, str)
    assert len(CONSTITUTION_VERSION) > 0


def test_compose_includes_version_in_bundle():
    """The version travels with the composed bundle — the critic LLM and
    cache writer both see it. If a refactor strips the version, cache
    keys silently miss the version dimension."""
    bundle = compose_constitution("status_seeker", "social_proof")
    assert bundle.constitution_version == CONSTITUTION_VERSION


# -----------------------------------------------------------------------------
# Mechanism slice substance — Cialdini-faithful invocation specs
# -----------------------------------------------------------------------------


def test_mechanism_slices_specify_concrete_invocation():
    """Every mechanism slice must answer the §6.3 mechanism_faithful
    question: what does 'concretely invoke' mean? Empty or trivially
    short text would mean the critic has no signal to grade against."""
    for mech in MECHANISMS:
        slice_ = get_mechanism_slice(mech)
        assert len(slice_.must_concretely_invoke) > 50, (
            f"{mech} must_concretely_invoke too short to be auditable"
        )


def test_mechanism_slices_list_forbidden_substitutes():
    """Every mechanism slice must list at least one forbidden substitute.
    This is what the critic uses to flag arguments that paraphrase
    rather than concretely invoke."""
    for mech in MECHANISMS:
        slice_ = get_mechanism_slice(mech)
        assert len(slice_.forbidden_substitutes) >= 1, (
            f"{mech} has no forbidden_substitutes — critic has no flag list"
        )
