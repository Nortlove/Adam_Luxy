"""Pin the LUXY page-intelligence populator.

Discipline anchors:
    - The populator does NOT invent edge_dimensions. They come from the
      existing url_intelligence resolver. The populator's value is in
      RUNNING THE RESOLVER ONCE OFFLINE, caching the result, and adding
      the curated tier + archetype + audience metadata.
    - Pilot archetype labels (LUXY-specific: careful_truster,
      dependable_loyalist, etc.) are stamped as DESCRIPTIVE METADATA on
      the profile (mindset / primary_topic). They do NOT participate in
      the cascade's canonical archetype routing.
    - Confidence is bumped by tier per the curation provenance, but the
      bump is from the resolver's heuristic floor (~0.15) toward — not
      above — the resolver's heuristic ceiling for unscored URLs (~0.55).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.luxy_page_populator import (
    PopulationResult,
    load_luxy_mapping,
    populate_luxy_pages,
    populate_one_entry,
)


# -----------------------------------------------------------------------------
# Mapping loader
# -----------------------------------------------------------------------------


def _write_mapping(tmp_path: Path, content: dict) -> Path:
    p = tmp_path / "mapping.json"
    p.write_text(json.dumps(content))
    return p


def test_load_mapping_flattens_archetype_lists(tmp_path):
    mapping = {
        "generated_at": "2026-04-14",
        "archetype_domain_lists": {
            "careful_truster": [
                {"domain": "bcdtravel.com", "audience": "travel_managers", "tier": 1},
                {"domain": "policymed.com", "audience": "life_sciences", "tier": 1},
            ],
            "dependable_loyalist": [
                {"domain": "businesstravelnews.com", "audience": "travel_managers", "tier": 1},
            ],
        },
    }
    path = _write_mapping(tmp_path, mapping)

    entries = load_luxy_mapping(path)

    assert len(entries) == 3
    domains = {e["domain"] for e in entries}
    assert domains == {"bcdtravel.com", "policymed.com", "businesstravelnews.com"}
    # Pilot archetype labels carried through
    pilots = {e["pilot_archetype"] for e in entries}
    assert pilots == {"careful_truster", "dependable_loyalist"}


def test_load_mapping_skips_malformed_entries(tmp_path):
    mapping = {
        "archetype_domain_lists": {
            "careful_truster": [
                {"domain": "valid.com", "tier": 1},
                {"audience": "missing_domain", "tier": 1},  # no domain
                "not_a_dict",                                # wrong type
                {"domain": "", "tier": 1},                   # empty domain
            ],
            "broken_archetype": "not_a_list",                # wrong shape
        },
    }
    path = _write_mapping(tmp_path, mapping)

    entries = load_luxy_mapping(path)

    assert len(entries) == 1
    assert entries[0]["domain"] == "valid.com"


def test_load_mapping_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load_luxy_mapping(Path("/nonexistent/mapping.json"))


def test_load_mapping_raises_on_bad_top_level(tmp_path):
    mapping = {"archetype_domain_lists": "not_a_dict"}
    path = _write_mapping(tmp_path, mapping)
    with pytest.raises(ValueError):
        load_luxy_mapping(path)


# -----------------------------------------------------------------------------
# Single-entry populator — happy path
# -----------------------------------------------------------------------------


def _mock_resolver_returning(edge_dims: dict):
    """Patch resolve_url_intelligence to return a synthetic resolver result."""
    return patch(
        "adam.intelligence.url_intelligence.resolve_url_intelligence",
        return_value={
            "edge_dimensions": edge_dims,
            "confidence": 0.3,
            "resolution_tier": "tier_3_domain_priors",
            "url_signals": {},
        },
    )


def test_populate_one_entry_happy_path_dry_run():
    """dry_run=True must not touch Redis; must return success + a
    DRY_RUN-prefixed key marker."""
    entry = {
        "domain": "bcdtravel.com",
        "audience": "travel_managers",
        "tier": 1,
        "pilot_archetype": "careful_truster",
    }
    edge_dims = {
        "regulatory_fit": 0.6,
        "emotional_resonance": 0.4,
        "cognitive_load_tolerance": 0.7,
    }
    with _mock_resolver_returning(edge_dims):
        ok, key, err = populate_one_entry(entry, dry_run=True)

    assert ok is True
    assert key.startswith("DRY_RUN:")
    assert "bcdtravel.com" in key
    assert err is None


def test_populate_one_entry_writes_to_cache_when_not_dry_run():
    entry = {
        "domain": "bcdtravel.com", "audience": "x", "tier": 1,
        "pilot_archetype": "careful_truster",
    }
    edge_dims = {"regulatory_fit": 0.6, "emotional_resonance": 0.4}
    cache_mock = MagicMock()
    cache_mock.store = MagicMock(return_value=True)

    with _mock_resolver_returning(edge_dims), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        return_value=cache_mock,
    ):
        ok, key, err = populate_one_entry(entry, dry_run=False)

    assert ok is True
    assert err is None
    assert key.startswith("informativ:page:")
    cache_mock.store.assert_called_once()


def test_populate_stamps_pilot_metadata_onto_profile():
    """Profile must carry tier + pilot_archetype + audience as
    DESCRIPTIVE metadata. Confidence must be bumped per tier."""
    entry = {
        "domain": "policymed.com", "audience": "life_sciences", "tier": 1,
        "pilot_archetype": "careful_truster",
    }
    edge_dims = {"regulatory_fit": 0.6, "emotional_resonance": 0.4}
    cache_mock = MagicMock()
    cache_mock.store = MagicMock(return_value=True)

    with _mock_resolver_returning(edge_dims), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        return_value=cache_mock,
    ):
        populate_one_entry(entry, dry_run=False)

    stored_profile = cache_mock.store.call_args.args[0]
    assert stored_profile.profile_source == "luxy_pilot_curated_tier_1"
    assert stored_profile.edge_scoring_tier == "luxy_pilot_curated_tier_1"
    assert stored_profile.mindset == "careful_truster"   # pilot label as metadata
    assert stored_profile.primary_topic == "life_sciences"
    assert stored_profile.confidence == 0.55              # tier 1 confidence


def test_tier_confidence_monotonic():
    """Tier 1 > Tier 2 > Tier 3 confidence — curation provenance."""
    edge_dims = {"regulatory_fit": 0.5}
    confidences = []

    for tier in (1, 2, 3):
        entry = {
            "domain": f"d{tier}.com", "audience": "x", "tier": tier,
            "pilot_archetype": "careful_truster",
        }
        cache_mock = MagicMock()
        cache_mock.store = MagicMock(return_value=True)
        captured = {}
        def capture_store(p):
            captured["profile"] = p
            return True
        cache_mock.store.side_effect = capture_store

        with _mock_resolver_returning(edge_dims), patch(
            "adam.intelligence.page_intelligence.get_page_intelligence_cache",
            return_value=cache_mock,
        ):
            populate_one_entry(entry, dry_run=False)

        confidences.append(captured["profile"].confidence)

    assert confidences[0] > confidences[1] > confidences[2]


def test_unknown_tier_falls_back_to_default_confidence():
    entry = {
        "domain": "x.com", "audience": "x", "tier": 99,  # unknown tier
        "pilot_archetype": "careful_truster",
    }
    edge_dims = {"regulatory_fit": 0.5}
    cache_mock = MagicMock()
    cache_mock.store = MagicMock(return_value=True)
    captured = {}
    cache_mock.store.side_effect = lambda p: (captured.setdefault("p", p), True)[1]

    with _mock_resolver_returning(edge_dims), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        return_value=cache_mock,
    ):
        ok, _, _ = populate_one_entry(entry, dry_run=False)

    assert ok is True
    # Default tier confidence (not crashes, not 0.55)
    assert captured["p"].confidence == 0.30


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


def test_resolver_failure_returns_skip():
    entry = {
        "domain": "x.com", "audience": "x", "tier": 1,
        "pilot_archetype": "careful_truster",
    }
    with patch(
        "adam.intelligence.url_intelligence.resolve_url_intelligence",
        side_effect=ConnectionError("boom"),
    ):
        ok, key, err = populate_one_entry(entry, dry_run=True)
    assert ok is False
    assert "resolver failed" in err


def test_empty_edge_dims_returns_skip():
    """Resolver returned but with no dims — skip rather than write an
    empty profile that would shadow request-time resolution."""
    entry = {
        "domain": "x.com", "audience": "x", "tier": 1,
        "pilot_archetype": "careful_truster",
    }
    with _mock_resolver_returning({}):
        ok, key, err = populate_one_entry(entry, dry_run=True)
    assert ok is False
    assert "no edge_dimensions" in err


def test_store_failure_returns_skip():
    entry = {
        "domain": "x.com", "audience": "x", "tier": 1,
        "pilot_archetype": "careful_truster",
    }
    edge_dims = {"regulatory_fit": 0.5}
    cache_mock = MagicMock()
    cache_mock.store = MagicMock(return_value=False)  # Redis unavailable

    with _mock_resolver_returning(edge_dims), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        return_value=cache_mock,
    ):
        ok, key, err = populate_one_entry(entry, dry_run=False)
    assert ok is False
    assert "store returned False" in err


# -----------------------------------------------------------------------------
# End-to-end populate_luxy_pages
# -----------------------------------------------------------------------------


def test_populate_luxy_pages_end_to_end_dry_run(tmp_path):
    """Full path: load mapping, walk entries, return summary. Dry-run
    skips Redis."""
    mapping = {
        "archetype_domain_lists": {
            "careful_truster": [
                {"domain": "bcdtravel.com", "audience": "x", "tier": 1},
                {"domain": "policymed.com", "audience": "y", "tier": 2},
            ],
            "dependable_loyalist": [
                {"domain": "businesstravelnews.com", "audience": "z", "tier": 1},
            ],
        },
    }
    path = _write_mapping(tmp_path, mapping)
    edge_dims = {"regulatory_fit": 0.5, "emotional_resonance": 0.4}

    with _mock_resolver_returning(edge_dims):
        result = populate_luxy_pages(mapping_path=path, dry_run=True)

    assert isinstance(result, PopulationResult)
    assert result.dry_run is True
    assert result.written == 3
    assert result.skipped == 0
    assert result.errors == []
    assert len(result.written_keys) == 3
    assert all(k.startswith("DRY_RUN:") for k in result.written_keys)


def test_populate_luxy_pages_records_partial_failures(tmp_path):
    """Some entries succeed, some fail — populator continues, summary
    reports both."""
    mapping = {
        "archetype_domain_lists": {
            "careful_truster": [
                {"domain": "good.com", "audience": "x", "tier": 1},
                {"domain": "bad.com", "audience": "y", "tier": 2},
            ],
        },
    }
    path = _write_mapping(tmp_path, mapping)

    def selective_resolver(url, page_cache=None):
        if "bad.com" in url:
            raise ConnectionError("bad domain")
        return {
            "edge_dimensions": {"regulatory_fit": 0.5},
            "confidence": 0.3,
            "resolution_tier": "tier_3",
            "url_signals": {},
        }

    with patch(
        "adam.intelligence.url_intelligence.resolve_url_intelligence",
        side_effect=selective_resolver,
    ):
        result = populate_luxy_pages(mapping_path=path, dry_run=True)

    assert result.written == 1
    assert result.skipped == 1
    assert len(result.errors) == 1
    assert "bad.com" in result.errors[0]


def test_populate_luxy_pages_handles_missing_mapping(tmp_path):
    result = populate_luxy_pages(
        mapping_path=tmp_path / "nonexistent.json", dry_run=True,
    )
    assert result.written == 0
    assert len(result.errors) == 1
    assert "mapping load failed" in result.errors[0]
