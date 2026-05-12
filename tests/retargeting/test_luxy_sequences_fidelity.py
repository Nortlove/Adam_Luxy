"""S8.2 — LUXY sequences fidelity to the bilateral source doc."""

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.sequence_loader import clear_cache, load_sequences


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


def _luxy():
    return load_sequences("luxy_ride", "luxy_q2_2026")


def test_careful_truster_4_touches_with_t1_needs_authoring_t234_extracted():
    ct = _luxy().active_archetypes["careful_truster"]
    assert ct.derivation_status == "extracted_from_bilateral_doc"
    assert ct.touch_count == 4
    statuses = {t.touch_number: t.touch_text_status for t in ct.touches}
    assert statuses[1] == "needs_authoring"
    assert statuses[2] == "extracted_from_doc"
    assert statuses[3] == "extracted_from_doc"
    assert statuses[4] == "extracted_from_doc"
    # T1 has no text; T2/T3/T4 carry <=15-word extracted text.
    by_num = {t.touch_number: t for t in ct.touches}
    assert by_num[1].touch_text is None
    for n in (2, 3, 4):
        assert by_num[n].touch_text is not None
        assert len(by_num[n].touch_text.split()) <= 15


def test_careful_truster_bilateral_findings_brand_trust_strongest():
    ct = _luxy().active_archetypes["careful_truster"]
    helps = {f["dimension"]: f.get("correlation_r") for f in ct.bilateral_findings["helps"]}
    hurts = {f["dimension"]: f.get("correlation_r") for f in ct.bilateral_findings["hurts"]}
    assert helps["brand_trust_fit"] == 0.619
    assert helps["appeals_comparative"] == 0.163
    assert hurts["liking"] == -0.229
    assert hurts["appeals_narrative"] == -0.226


def test_status_seeker_4_touches_all_needs_authoring():
    ss = _luxy().active_archetypes["status_seeker"]
    assert ss.touch_count == 4
    assert ss.derivation_status == "derived_from_bilateral_findings_needs_authoring"
    assert all(t.touch_text_status == "needs_authoring" for t in ss.touches)
    assert all(t.touch_text is None for t in ss.touches)


def test_easy_decider_4_touches_all_needs_authoring_with_evol_motive_finding():
    ed = _luxy().active_archetypes["easy_decider"]
    assert ed.touch_count == 4
    assert all(t.touch_text_status == "needs_authoring" for t in ed.touches)
    helps = {f["dimension"]: f.get("correlation_r") for f in ed.bilateral_findings["helps"]}
    hurts = {f["dimension"]: f.get("correlation_r") for f in ed.bilateral_findings["hurts"]}
    assert helps["evolutionary_motive_match"] == 0.484
    assert hurts["linguistic_complexity"] == -0.130


def test_two_suppression_rules_present():
    s = _luxy()
    assert set(s.suppress_archetypes) == {"skeptical_analyst", "disillusioned"}
    for name in ("skeptical_analyst", "disillusioned"):
        rule = s.suppress_archetypes[name]
        assert rule.action == "suppress_bid"
        assert rule.budget_allocation_pct == 0
        assert rule.rationale  # non-empty
        assert rule.psychological_basis  # non-empty


def test_three_active_sequences_present():
    s = _luxy()
    assert set(s.active_archetypes) == {"status_seeker", "easy_decider", "careful_truster"}
    for seq in s.active_archetypes.values():
        assert seq.touch_count >= 1
        assert len(seq.touches) == seq.touch_count


def test_luxy_budget_allocation_30_15_40_plus_zeros():
    s = _luxy()
    assert s.active_archetypes["status_seeker"].budget_allocation_pct == 30
    assert s.active_archetypes["easy_decider"].budget_allocation_pct == 15
    assert s.active_archetypes["careful_truster"].budget_allocation_pct == 40
    assert s.suppress_archetypes["skeptical_analyst"].budget_allocation_pct == 0
    assert s.suppress_archetypes["disillusioned"].budget_allocation_pct == 0


def test_analyst_routes_to_careful_truster_conservative_tiebreak():
    # Pinned: ANALYST (Layer-1) → careful_truster (active), NOT
    # skeptical_analyst (suppress). Conservative tie-break per S8.2.
    s = _luxy()
    assert s.crosswalk[ArchetypeID.ANALYST] == "careful_truster"


def test_conversion_rates_match_source_doc():
    s = _luxy()
    assert s.active_archetypes["status_seeker"].conversion_rate_pct == 94.5
    assert s.active_archetypes["easy_decider"].conversion_rate_pct == 90.9
    assert s.active_archetypes["careful_truster"].conversion_rate_pct == 65.0
    assert s.suppress_archetypes["skeptical_analyst"].conversion_rate_pct == 0.8
    assert s.suppress_archetypes["disillusioned"].conversion_rate_pct == 0.8
