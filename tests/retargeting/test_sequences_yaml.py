"""S8.2 — structural invariants of the LUXY sequences.yaml."""

import pathlib

import yaml

LUXY_YAML = (
    pathlib.Path(__file__).parent.parent.parent
    / "adam" / "retargeting" / "campaigns" / "luxy_ride" / "luxy_q2_2026"
    / "sequences.yaml"
)


def _load_raw() -> dict:
    return yaml.safe_load(LUXY_YAML.read_text(encoding="utf-8"))


def test_yaml_exists():
    assert LUXY_YAML.is_file()


def test_yaml_parses_clean():
    doc = _load_raw()
    assert isinstance(doc, dict)


def test_top_level_keys_exactly_metadata_and_archetypes():
    doc = _load_raw()
    assert set(doc) == {"metadata", "archetypes"}


def test_schema_version_pinned():
    doc = _load_raw()
    assert doc["metadata"]["schema_version"] == "1.0"


def test_metadata_tenant_and_campaign_ids():
    meta = _load_raw()["metadata"]
    assert meta["tenant_id"] == "luxy_ride"
    assert meta["campaign_id"] == "luxy_q2_2026"
    assert meta["layer"] == 2


def test_source_doc_filename_two_spaces():
    # Ground truth on disk: the bilateral source doc filename has TWO
    # spaces before "Advertising".
    meta = _load_raw()["metadata"]
    assert "Psycholinguistic  Advertising" in meta["source_doc"]


def test_five_archetype_keys():
    arch = _load_raw()["archetypes"]
    assert set(arch) == {
        "status_seeker", "easy_decider", "careful_truster",
        "skeptical_analyst", "disillusioned",
    }


def test_three_active_two_suppress():
    arch = _load_raw()["archetypes"]
    roles = {k: v["archetype_role"] for k, v in arch.items()}
    active = [k for k, r in roles.items() if r == "active"]
    suppress = [k for k, r in roles.items() if r == "suppress"]
    assert sorted(active) == ["careful_truster", "easy_decider", "status_seeker"]
    assert sorted(suppress) == ["disillusioned", "skeptical_analyst"]


def test_budget_allocation_sums_to_100():
    ba = _load_raw()["metadata"]["campaign_budget_allocation"]
    assert ba["status_seeker"] + ba["easy_decider"] + ba["careful_truster"] + ba["unallocated"] == 100
    assert ba["skeptical_analyst"] == 0
    assert ba["disillusioned"] == 0
    assert ba["status_seeker"] == 30
    assert ba["careful_truster"] == 40
    assert ba["easy_decider"] == 15


def test_correlation_r_values_in_range_or_null():
    arch = _load_raw()["archetypes"]
    for arch_name, body in arch.items():
        for bucket in ("helps", "hurts"):
            for finding in body.get("bilateral_findings", {}).get(bucket, []):
                r = finding.get("correlation_r")
                if r is not None:
                    assert -1.0 <= float(r) <= 1.0, f"{arch_name}/{bucket}: r={r}"


def test_active_archetypes_have_therapeutic_sequence():
    arch = _load_raw()["archetypes"]
    for name, body in arch.items():
        if body["archetype_role"] == "active":
            seq = body.get("therapeutic_sequence")
            assert isinstance(seq, dict), name
            assert seq["touch_count"] == len(seq["touches"]), name


def test_suppress_archetypes_have_no_therapeutic_sequence():
    arch = _load_raw()["archetypes"]
    for name, body in arch.items():
        if body["archetype_role"] == "suppress":
            assert "therapeutic_sequence" not in body, name
            assert isinstance(body.get("suppression_rule"), dict), name


def test_touch_numbers_1_indexed_contiguous():
    arch = _load_raw()["archetypes"]
    for name, body in arch.items():
        if body["archetype_role"] != "active":
            continue
        nums = [t["touch_number"] for t in body["therapeutic_sequence"]["touches"]]
        assert nums == list(range(1, len(nums) + 1)), name


def test_touch_text_quotes_under_15_words():
    # Copyright discipline: any extracted touch_text from the bilateral
    # doc must be <=15 words.
    arch = _load_raw()["archetypes"]
    for name, body in arch.items():
        if body["archetype_role"] != "active":
            continue
        for t in body["therapeutic_sequence"]["touches"]:
            txt = t.get("touch_text")
            if txt is not None:
                assert len(txt.split()) <= 15, f"{name} touch {t['touch_number']}: {txt!r}"


def test_all_8_archetypeid_values_mapped_exactly_once_in_active_maps_from():
    from adam.cold_start.models.enums import ArchetypeID
    arch = _load_raw()["archetypes"]
    seen = {}
    for name, body in arch.items():
        for layer1 in body.get("cold_start_archetype_crosswalk", {}).get("maps_from", []):
            assert layer1 not in seen, f"{layer1} mapped by both {seen[layer1]} and {name}"
            seen[layer1] = name
    assert set(seen) == {a.name for a in ArchetypeID}
    # Suppress archetypes have empty maps_from (intentional).
    for name in ("skeptical_analyst", "disillusioned"):
        assert arch[name]["cold_start_archetype_crosswalk"]["maps_from"] == []


def test_psychological_profile_summary_under_15_words():
    arch = _load_raw()["archetypes"]
    for name, body in arch.items():
        summary = body.get("psychological_profile", {}).get("summary", "")
        assert len(summary.split()) <= 15, f"{name}: {summary!r}"
