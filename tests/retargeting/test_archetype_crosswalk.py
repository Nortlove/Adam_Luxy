"""S8.2 — tenant-scoped Layer-1 → Layer-2 crosswalk resolver."""

import pathlib
from dataclasses import replace

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.archetype_crosswalk import (
    resolve_layer_1_to_layer_2,
    validate_crosswalk_coverage,
)
from adam.retargeting.sequence_loader import (
    SequenceLoaderError,
    clear_cache,
    load_sequences,
)

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "campaigns"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


def _luxy():
    return load_sequences("luxy_ride", "luxy_q2_2026")


def _synthetic():
    return load_sequences("tenant_synthetic_b", "synthetic_b_q1", campaigns_root=FIXTURE_ROOT)


# --- LUXY crosswalk ---


def test_luxy_all_8_layer1_resolve():
    s = _luxy()
    mapping = {a: resolve_layer_1_to_layer_2(a, s) for a in ArchetypeID}
    assert mapping == {
        ArchetypeID.EXPLORER: "status_seeker",
        ArchetypeID.ACHIEVER: "status_seeker",
        ArchetypeID.CONNECTOR: "easy_decider",
        ArchetypeID.CREATOR: "easy_decider",
        ArchetypeID.PRAGMATIST: "easy_decider",
        ArchetypeID.GUARDIAN: "careful_truster",
        ArchetypeID.ANALYST: "careful_truster",
        ArchetypeID.NURTURER: "careful_truster",
    }


def test_luxy_connector_maps_to_easy_decider():
    assert resolve_layer_1_to_layer_2(ArchetypeID.CONNECTOR, _luxy()) == "easy_decider"


def test_luxy_analyst_conservative_tiebreak_to_careful_truster_not_skeptical():
    # The conservative tie-break: ANALYST routes to careful_truster
    # (active), NOT skeptical_analyst (suppress) — cold-start signals
    # can't observe the differentiating need-for-cognition /
    # attachment-avoidance traits.
    s = _luxy()
    assert resolve_layer_1_to_layer_2(ArchetypeID.ANALYST, s) == "careful_truster"
    assert resolve_layer_1_to_layer_2(ArchetypeID.ANALYST, s) != "skeptical_analyst"


def test_luxy_validate_crosswalk_coverage_passes():
    validate_crosswalk_coverage(_luxy())  # should not raise


# --- synthetic-tenant crosswalk (DIFFERENT mappings — proves isolation) ---


def test_synthetic_all_8_layer1_resolve():
    s = _synthetic()
    mapping = {a: resolve_layer_1_to_layer_2(a, s) for a in ArchetypeID}
    assert mapping == {
        ArchetypeID.EXPLORER: "synthetic_active_a",
        ArchetypeID.ACHIEVER: "synthetic_active_a",
        ArchetypeID.CONNECTOR: "synthetic_active_a",
        ArchetypeID.CREATOR: "synthetic_active_a",
        ArchetypeID.GUARDIAN: "synthetic_active_b",
        ArchetypeID.ANALYST: "synthetic_active_b",
        ArchetypeID.NURTURER: "synthetic_active_b",
        ArchetypeID.PRAGMATIST: "synthetic_active_b",
    }


def test_synthetic_differs_from_luxy():
    # CONNECTOR → easy_decider on LUXY but → synthetic_active_a on the
    # fixture; same resolver, different data.
    assert resolve_layer_1_to_layer_2(ArchetypeID.CONNECTOR, _luxy()) == "easy_decider"
    assert resolve_layer_1_to_layer_2(ArchetypeID.CONNECTOR, _synthetic()) == "synthetic_active_a"


def test_synthetic_validate_crosswalk_coverage_passes():
    validate_crosswalk_coverage(_synthetic())  # should not raise


# --- coverage validation catches fabricated defects ---


def test_validate_detects_unknown_layer2_target():
    s = _luxy()
    # Tamper: point ANALYST at a non-existent Layer-2 archetype.
    bad_crosswalk = dict(s.crosswalk)
    bad_crosswalk[ArchetypeID.ANALYST] = "ghost_archetype"
    bad = replace(s, crosswalk=bad_crosswalk)
    with pytest.raises(SequenceLoaderError):
        validate_crosswalk_coverage(bad)


def test_validate_detects_missing_layer1_key():
    s = _luxy()
    bad_crosswalk = dict(s.crosswalk)
    del bad_crosswalk[ArchetypeID.PRAGMATIST]
    bad = replace(s, crosswalk=bad_crosswalk)
    with pytest.raises(SequenceLoaderError):
        validate_crosswalk_coverage(bad)


def test_loader_rejects_yaml_with_overlapping_maps_from(tmp_path):
    # Build a minimal bad YAML where two archetypes both claim EXPLORER.
    bad_yaml = """
metadata:
  tenant_id: "bad_tenant"
  campaign_id: "bad_campaign"
  tenant_display_name: "Bad"
  campaign_display_name: "Bad"
  schema_version: "1.0"
  source_doc: "(test)"
  layer: 2
  archetype_count: 2
  active_archetype_count: 2
  suppress_archetype_count: 0
archetypes:
  a1:
    archetype_id: "a1"
    archetype_role: "active"
    cold_start_archetype_crosswalk:
      maps_from: ["EXPLORER", "ACHIEVER"]
    therapeutic_sequence:
      derivation_status: "derived_from_bilateral_findings_needs_authoring"
      touch_count: 1
      touches:
        - touch_number: 1
          touch_role: "initial_impression"
          mechanism_primary: "authority"
          touch_text_status: "needs_authoring"
          touch_text: null
  a2:
    archetype_id: "a2"
    archetype_role: "active"
    cold_start_archetype_crosswalk:
      maps_from: ["EXPLORER"]
    therapeutic_sequence:
      derivation_status: "derived_from_bilateral_findings_needs_authoring"
      touch_count: 1
      touches:
        - touch_number: 1
          touch_role: "initial_impression"
          mechanism_primary: "liking"
          touch_text_status: "needs_authoring"
          touch_text: null
"""
    root = tmp_path / "campaigns"
    (root / "bad_tenant" / "bad_campaign").mkdir(parents=True)
    (root / "bad_tenant" / "bad_campaign" / "sequences.yaml").write_text(bad_yaml)
    with pytest.raises(SequenceLoaderError):
        load_sequences("bad_tenant", "bad_campaign", campaigns_root=root)
