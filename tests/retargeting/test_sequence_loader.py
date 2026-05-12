"""S8.2 — sequence_loader correctness, cache, multi-tenant isolation."""

import pathlib

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.sequence_loader import (
    LoadedSequences,
    SequenceLoaderError,
    SequenceTemplate,
    SuppressionRule,
    clear_cache,
    get_sequence_for_archetype,
    load_sequences,
    resolve_cold_start_archetype,
)

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "campaigns"


@pytest.fixture(autouse=True)
def _clear_loader_cache():
    clear_cache()
    yield
    clear_cache()


# --- LUXY load ---


def test_load_luxy_returns_loaded_sequences():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    assert isinstance(s, LoadedSequences)
    assert s.tenant_id == "luxy_ride"
    assert s.campaign_id == "luxy_q2_2026"


def test_luxy_has_3_active_2_suppress():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    assert set(s.active_archetypes) == {"status_seeker", "easy_decider", "careful_truster"}
    assert set(s.suppress_archetypes) == {"skeptical_analyst", "disillusioned"}


def test_luxy_metadata_fields():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    assert s.metadata.schema_version == "1.0"
    assert s.metadata.layer == 2
    assert s.metadata.active_archetype_count == 3
    assert s.metadata.suppress_archetype_count == 2
    assert "Psycholinguistic  Advertising" in s.metadata.source_doc


def test_luxy_active_archetype_is_sequence_template():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    ct = s.active_archetypes["careful_truster"]
    assert isinstance(ct, SequenceTemplate)
    assert ct.touch_count == 4
    assert len(ct.touches) == 4
    assert ct.derivation_status == "extracted_from_bilateral_doc"


def test_luxy_suppress_archetype_is_suppression_rule():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    sa = s.suppress_archetypes["skeptical_analyst"]
    assert isinstance(sa, SuppressionRule)
    assert sa.action == "suppress_bid"
    assert sa.budget_allocation_pct == 0


# --- cache behavior ---


def test_cache_hit_returns_same_object():
    a = load_sequences("luxy_ride", "luxy_q2_2026")
    b = load_sequences("luxy_ride", "luxy_q2_2026")
    assert a is b


def test_force_reload_returns_new_object():
    a = load_sequences("luxy_ride", "luxy_q2_2026")
    b = load_sequences("luxy_ride", "luxy_q2_2026", force_reload=True)
    assert a is not b
    # but content-equivalent
    assert b.tenant_id == a.tenant_id
    assert set(b.active_archetypes) == set(a.active_archetypes)


def test_clear_cache_drops_all_entries():
    a = load_sequences("luxy_ride", "luxy_q2_2026")
    clear_cache()
    b = load_sequences("luxy_ride", "luxy_q2_2026")
    assert a is not b


# --- error paths (fail-loud) ---


def test_unknown_tenant_raises():
    with pytest.raises(SequenceLoaderError):
        load_sequences("nonexistent_tenant", "nonexistent_campaign")


def test_unknown_campaign_for_known_tenant_raises():
    with pytest.raises(SequenceLoaderError):
        load_sequences("luxy_ride", "no_such_campaign")


def test_load_with_explicit_root_for_fixture():
    s = load_sequences(
        "tenant_synthetic_b", "synthetic_b_q1", campaigns_root=FIXTURE_ROOT,
    )
    assert s.tenant_id == "tenant_synthetic_b"
    assert set(s.active_archetypes) == {"synthetic_active_a", "synthetic_active_b"}
    assert set(s.suppress_archetypes) == {"synthetic_suppress"}


# --- lookup helpers ---


def test_get_sequence_for_archetype_active():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    r = get_sequence_for_archetype("status_seeker", s)
    assert isinstance(r, SequenceTemplate)


def test_get_sequence_for_archetype_suppress():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    r = get_sequence_for_archetype("disillusioned", s)
    assert isinstance(r, SuppressionRule)


def test_get_sequence_for_archetype_unknown_raises_keyerror():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    with pytest.raises(KeyError):
        get_sequence_for_archetype("not_an_archetype", s)


# --- cold-start resolution ---


def test_resolve_cold_start_luxy_all_8():
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    expected = {
        ArchetypeID.EXPLORER: "status_seeker",
        ArchetypeID.ACHIEVER: "status_seeker",
        ArchetypeID.CONNECTOR: "easy_decider",
        ArchetypeID.CREATOR: "easy_decider",
        ArchetypeID.PRAGMATIST: "easy_decider",
        ArchetypeID.GUARDIAN: "careful_truster",
        ArchetypeID.ANALYST: "careful_truster",
        ArchetypeID.NURTURER: "careful_truster",
    }
    for layer1, layer2 in expected.items():
        assert resolve_cold_start_archetype(layer1, s) == layer2, layer1


def test_resolve_cold_start_no_layer1_maps_to_suppress():
    # No Layer-1 archetype routes to LUXY's suppress archetypes
    # (their maps_from is empty); the suppress archetypes are reached
    # via downstream behavioral signals, not cold-start.
    s = load_sequences("luxy_ride", "luxy_q2_2026")
    values = {resolve_cold_start_archetype(a, s) for a in ArchetypeID}
    assert "skeptical_analyst" not in values
    assert "disillusioned" not in values
    # every Layer-1 routes SOMEWHERE (none None for LUXY, since all 8
    # are claimed by the 3 active archetypes)
    assert None not in values


# --- multi-tenant cache isolation ---


def test_loading_synthetic_does_not_pollute_luxy_cache():
    luxy_a = load_sequences("luxy_ride", "luxy_q2_2026")
    _ = load_sequences("tenant_synthetic_b", "synthetic_b_q1", campaigns_root=FIXTURE_ROOT)
    luxy_b = load_sequences("luxy_ride", "luxy_q2_2026")
    assert luxy_a is luxy_b  # LUXY cache untouched by synthetic load
    assert luxy_b.tenant_id == "luxy_ride"
    assert set(luxy_b.active_archetypes) == {"status_seeker", "easy_decider", "careful_truster"}


def test_no_yaml_load_only_safe_load_in_loader_source():
    src = (
        pathlib.Path(__file__).parent.parent.parent
        / "adam" / "retargeting" / "sequence_loader.py"
    ).read_text()
    assert "yaml.safe_load" in src
    assert "yaml.load(" not in src  # unsafe loader must not appear
