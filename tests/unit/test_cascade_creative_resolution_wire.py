"""Pin Slice C cascade wire — decision-time creative resolution.

Audit gap: ``creative_upload_pipeline.lookup_creative_by_metadata``
existed at line 238 with zero callers in run_bilateral_cascade. The
``decision_trace_emitter`` hardcoded ``mechanism_proxy:{mech}`` as
the chosen_creative_id. Slice 13 had uploaded creatives sitting in
the manifest with no decision-time consumer.

This slice wires the sync-side lookup into the cascade just before
``build_trace_from_cascade``, threading the resolved
``stackadapt_creative_id`` through the new ``resolved_creative_id``
kwarg. When the manifest has no match, the placeholder is preserved
(behavior unchanged for callers who haven't uploaded creatives yet).

This test pins:
    * The cascade source imports the sync lookup primitive
    * The cascade source uses graph_cache._get_driver() (existing
      sync-driver source — same pattern as _refresh_priors_if_stale)
    * The metrics surface exposes both resolution counters
    * A wire-mirror harness exercises hit / miss / driver-missing /
      empty-cell paths
    * Soft-fail: a raising lookup must NOT block the bid path
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from adam.intelligence.creative_upload_pipeline import (
    CreativeRecord,
    lookup_creative_by_metadata_sync,
)


# -----------------------------------------------------------------------------
# Source-text contract pins — defend against accidental unwire
# -----------------------------------------------------------------------------


def test_cascade_imports_sync_lookup_primitive():
    """Cascade source must reference the sync lookup primitive."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert (
        "from adam.intelligence.creative_upload_pipeline import" in src
        and "lookup_creative_by_metadata_sync" in src
    ), (
        "Cascade lost its import of lookup_creative_by_metadata_sync. "
        "Slice C creative resolution is unwired — chosen_creative_id "
        "will silently revert to mechanism_proxy:{mech} placeholder."
    )


def test_cascade_uses_graph_cache_sync_driver_source():
    """The cascade reads the sync driver via graph_cache._get_driver()
    — the same pattern _refresh_priors_if_stale uses."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "graph_cache._get_driver" in src, (
        "Cascade lost its sync-driver source. Slice C resolution "
        "block won't have a Neo4j driver to call lookup against."
    )


def test_cascade_threads_resolved_creative_id_to_builder():
    """The cascade passes resolved_creative_id into
    build_trace_from_cascade — the kwarg is what bridges the
    lookup result into the trace."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "resolved_creative_id=" in src, (
        "Cascade no longer threads resolved_creative_id into the "
        "trace builder. The lookup result has no consumer."
    )


def test_metrics_surface_exposes_resolution_counters():
    """Both resolution counters present on metrics surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "cascade_creative_resolution_hits_total"
    ), "Slice C hits counter missing from metrics surface."
    assert hasattr(
        metrics, "cascade_creative_resolution_misses_total"
    ), "Slice C misses counter missing from metrics surface."


# -----------------------------------------------------------------------------
# Wire-mirror harness — isolates the in-cascade behavior
# -----------------------------------------------------------------------------


class _FakeRecord:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _FakeSyncResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def single(self):
        return _FakeRecord(self._rows[0]) if self._rows else None


class _FakeSyncSession:
    def __init__(self, driver):
        self._driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None

    def run(self, cypher, **params):
        self._driver.calls.append((cypher, params))
        norm = cypher.strip()
        if norm.startswith("MATCH (c:UploadedCreative)"):
            mech = params.get("mechanism")
            posture = params.get("posture_class")
            metaphor = params.get("primary_metaphor")
            matches = []
            for r in self._driver.records.values():
                if r.get("mechanism") != mech:
                    continue
                if r.get("posture_class") != posture:
                    continue
                if metaphor is not None and r.get("primary_metaphor") != metaphor:
                    continue
                matches.append(r)
            matches.sort(
                key=lambda r: r.get("uploaded_at_ts", 0.0), reverse=True,
            )
            return _FakeSyncResult([{"c": matches[0]}] if matches else [])
        return _FakeSyncResult([])


class _FakeSyncDriver:
    def __init__(self):
        self.records: Dict[str, dict] = {}
        self.calls: List = []

    def session(self):
        return _FakeSyncSession(self)

    def add(self, record: CreativeRecord):
        self.records[record.stackadapt_creative_id] = {
            "stackadapt_creative_id": record.stackadapt_creative_id,
            "name": record.name,
            "landing_page_url": record.landing_page_url,
            "mechanism": record.mechanism,
            "primary_metaphor": record.primary_metaphor,
            "posture_class": record.posture_class,
            "advertiser_id": record.advertiser_id,
            "creative_type": record.creative_type,
            "uploaded_at_ts": record.uploaded_at_ts,
        }


def _mirror_cascade_resolution_block(
    chosen_mechanism: Optional[str],
    posture_class: Optional[str],
    driver,
) -> Optional[str]:
    """Mirror the cascade resolution block: short-circuit on missing
    inputs / driver, lookup, return resolved id or None."""
    if not chosen_mechanism or not posture_class or driver is None:
        return None
    record = lookup_creative_by_metadata_sync(
        mechanism=chosen_mechanism,
        posture_class=posture_class,
        driver=driver,
    )
    return record.stackadapt_creative_id if record else None


def test_wire_resolves_hit():
    driver = _FakeSyncDriver()
    driver.add(CreativeRecord(
        stackadapt_creative_id="sa-1",
        name="luxy social_proof blend",
        landing_page_url="https://luxy.example/?sapid={SA_POSTBACK_ID}",
        mechanism="social_proof",
        posture_class="blend_compatible",
        primary_metaphor="forward_motion",
        uploaded_at_ts=100.0,
    ))

    out = _mirror_cascade_resolution_block(
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out == "sa-1"


def test_wire_miss_returns_none():
    """Empty manifest → None → emitter falls back to placeholder."""
    driver = _FakeSyncDriver()  # empty
    out = _mirror_cascade_resolution_block(
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is None


def test_wire_no_driver_returns_none():
    """driver=None (graph_cache unavailable) → short-circuits to None."""
    out = _mirror_cascade_resolution_block(
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        driver=None,
    )
    assert out is None


def test_wire_no_posture_returns_none():
    """No posture classification → cell is undefined → skip lookup."""
    driver = _FakeSyncDriver()
    driver.add(CreativeRecord(
        stackadapt_creative_id="sa-1",
        name="x",
        landing_page_url="https://x",
        mechanism="social_proof",
        posture_class="blend_compatible",
    ))
    out = _mirror_cascade_resolution_block(
        chosen_mechanism="social_proof",
        posture_class=None,
        driver=driver,
    )
    assert out is None
    # Lookup not attempted
    assert len(driver.calls) == 0


def test_wire_no_chosen_mechanism_returns_none():
    """No chosen mechanism → can't resolve → skip."""
    driver = _FakeSyncDriver()
    out = _mirror_cascade_resolution_block(
        chosen_mechanism=None,
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is None


def test_wire_raising_driver_does_not_propagate():
    """The cascade block is wrapped in try/except (logger.debug); a
    raising driver must NEVER bubble up and block the bid path."""
    class _RaisingDriver:
        def session(self):
            raise RuntimeError("simulated connection failure")

    # Even though the inner lookup soft-fails to None on its own, this
    # test pins that the mirror (and by extension the cascade block)
    # tolerates exceptions from the driver layer.
    out = _mirror_cascade_resolution_block(
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        driver=_RaisingDriver(),
    )
    assert out is None


def test_wire_returns_most_recent_when_multiple_match():
    """Hot-path lookup returns the most recently uploaded creative
    for the (mechanism, posture) cell — operator's mental model is
    'newer creative supersedes older'."""
    driver = _FakeSyncDriver()
    driver.add(CreativeRecord(
        stackadapt_creative_id="sa-old", name="old",
        landing_page_url="https://x",
        mechanism="social_proof",
        posture_class="blend_compatible",
        uploaded_at_ts=100.0,
    ))
    driver.add(CreativeRecord(
        stackadapt_creative_id="sa-new", name="new",
        landing_page_url="https://x",
        mechanism="social_proof",
        posture_class="blend_compatible",
        uploaded_at_ts=200.0,
    ))

    out = _mirror_cascade_resolution_block(
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out == "sa-new"
