"""S8.2 — architectural acceptance: the same loader handles both LUXY
and the synthetic-tenant-B fixture with zero code changes.

If these tests pass, the platform scales: a second tenant onboards by
dropping a sequences.yaml file in their namespace.
"""

import pathlib

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.archetype_crosswalk import (
    resolve_layer_1_to_layer_2,
    validate_crosswalk_coverage,
)
from adam.retargeting.sequence_loader import (
    SequenceTemplate,
    SuppressionRule,
    clear_cache,
    get_sequence_for_archetype,
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


def test_same_loader_handles_both_tenants():
    luxy = _luxy()
    syn = _synthetic()
    assert luxy.tenant_id == "luxy_ride"
    assert syn.tenant_id == "tenant_synthetic_b"
    # Both produce well-formed LoadedSequences via the identical code path.
    validate_crosswalk_coverage(luxy)
    validate_crosswalk_coverage(syn)


def test_synthetic_has_3_archetypes_not_5_loader_does_not_care():
    syn = _synthetic()
    assert len(syn.active_archetypes) == 2
    assert len(syn.suppress_archetypes) == 1
    assert syn.archetype_ids() == (
        "synthetic_active_a", "synthetic_active_b", "synthetic_suppress",
    )
    # LUXY has 5; the loader hardcodes no expected count.
    assert len(_luxy().archetype_ids()) == 5


def test_load_order_independence():
    # Load synthetic first, then LUXY.
    clear_cache()
    syn_first = _synthetic()
    luxy_after = _luxy()
    clear_cache()
    # Load LUXY first, then synthetic.
    luxy_first = _luxy()
    syn_after = _synthetic()
    # Content equivalent regardless of order.
    assert syn_first.archetype_ids() == syn_after.archetype_ids()
    assert luxy_first.archetype_ids() == luxy_after.archetype_ids()
    assert syn_first.crosswalk == syn_after.crosswalk
    assert luxy_first.crosswalk == luxy_after.crosswalk


def test_luxy_has_careful_truster_synthetic_does_not_same_code():
    luxy = _luxy()
    syn = _synthetic()
    assert "careful_truster" in luxy.active_archetypes
    assert "careful_truster" not in syn.active_archetypes
    assert "careful_truster" not in syn.suppress_archetypes
    # Different active sets; identical loader.
    assert isinstance(get_sequence_for_archetype("careful_truster", luxy), SequenceTemplate)
    assert isinstance(get_sequence_for_archetype("synthetic_active_a", syn), SequenceTemplate)
    assert isinstance(get_sequence_for_archetype("synthetic_suppress", syn), SuppressionRule)


def test_crosswalk_partitions_differ_between_tenants():
    luxy = _luxy()
    syn = _synthetic()
    # LUXY: 2+3+3+0+0 partition (the 2 suppress get 0). Synthetic: 4+4+0.
    luxy_targets = [resolve_layer_1_to_layer_2(a, luxy) for a in ArchetypeID]
    syn_targets = [resolve_layer_1_to_layer_2(a, syn) for a in ArchetypeID]
    assert luxy_targets != syn_targets
    # Distinct target sets prove the data drives the mapping.
    assert set(t for t in luxy_targets if t) == {"status_seeker", "easy_decider", "careful_truster"}
    assert set(t for t in syn_targets if t) == {"synthetic_active_a", "synthetic_active_b"}


def test_cross_tenant_cache_isolation():
    luxy_a = _luxy()
    syn_a = _synthetic()
    luxy_b = _luxy()
    syn_b = _synthetic()
    # Each tenant's cache entry is independent; second loads are cache hits.
    assert luxy_a is luxy_b
    assert syn_a is syn_b
    # And they're distinct objects.
    assert luxy_a is not syn_a


def test_both_yamls_use_schema_version_1_0():
    assert _luxy().metadata.schema_version == "1.0"
    assert _synthetic().metadata.schema_version == "1.0"
