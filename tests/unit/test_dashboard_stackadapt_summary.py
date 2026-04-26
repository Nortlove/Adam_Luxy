"""Unit tests for the StackAdapt GraphQL summary parsing.

Discipline anchors:
    - Per-campaign metrics live on the top-level `campaignDelivery`
      resolver in StackAdapt's current schema. The earlier `Campaign.stats`
      field was removed and silently produced all-zero metrics through the
      fallback path. These tests pin the new shape.
    - The primary query MUST request `campaignDelivery(...)` and MUST NOT
      request `stats` directly on a Campaign node — the latter would
      regress to the broken state where every campaign reads as zeros and
      threshold generators silently produce no signal.
    - Three response shapes are handled non-destructively in
      `_parse_summary`: CampaignDeliveryOutcome (real records), Progress
      (async pending), and missing (degraded fallback). All three yield a
      sensible StackAdaptSummary with advertiser totals preserved.
"""

from __future__ import annotations

import re

from adam.api.dashboard.service import (
    _CAMPAIGNS_QUERY,
    _CAMPAIGNS_QUERY_FALLBACK,
    _parse_summary,
)


# -----------------------------------------------------------------------------
# Query-shape regression tests — guard against re-drift to Campaign.stats
# -----------------------------------------------------------------------------


def test_primary_query_uses_campaign_delivery_not_campaign_stats():
    """Per-campaign stats must come from campaignDelivery, not Campaign.stats.

    The StackAdapt schema removed `Campaign.stats`. Re-introducing it would
    make every per-campaign metric silently read as zero (because the
    response carries an `errors` array and the parser falls back to a query
    that omits per-campaign stats entirely). Pin the structural shape.
    """
    # Must include campaignDelivery resolver with TABLE/TOTAL parameters.
    assert "campaignDelivery" in _CAMPAIGNS_QUERY
    assert "dataType: TABLE" in _CAMPAIGNS_QUERY
    assert "granularity: TOTAL" in _CAMPAIGNS_QUERY
    # Must thread the date range as variables (not f-string interpolation).
    assert "$from" in _CAMPAIGNS_QUERY
    assert "$to" in _CAMPAIGNS_QUERY

    # Must NOT request `stats {` directly on a Campaign node — that's the
    # broken pattern. Allowed only on the Advertiser node and on the
    # CampaignDelivery records via `metrics {` (different field name).
    # We assert the structural pattern: no occurrence of `stats {` inside
    # a `campaigns(first: ...) { nodes { ... } }` block.
    campaigns_block = re.search(
        r"campaigns\(first:\s*\d+\)\s*\{\s*nodes\s*\{[^}]*\}",
        _CAMPAIGNS_QUERY,
        flags=re.DOTALL,
    )
    assert campaigns_block is not None, (
        "expected a campaigns(first:N) { nodes { ... } } block in primary query"
    )
    assert "stats" not in campaigns_block.group(0), (
        "primary query regressed: Campaign.stats reappeared inside the "
        "campaigns(first:N).nodes block. Per-campaign metrics must come "
        "from campaignDelivery, not Campaign.stats — the latter is gone "
        "from the StackAdapt schema and silently zeros every campaign."
    )


def test_fallback_query_has_no_per_campaign_metrics():
    """The fallback is intentionally degraded — campaign list only.

    When the primary errors (e.g. future schema drift on campaignDelivery),
    the fallback returns advertiser totals + campaign list with no
    per-campaign metrics. Threshold generators silently produce no signal,
    which is the correct degraded behavior.
    """
    assert "campaignDelivery" not in _CAMPAIGNS_QUERY_FALLBACK
    campaigns_block = re.search(
        r"campaigns\(first:\s*\d+\)\s*\{\s*nodes\s*\{[^}]*\}",
        _CAMPAIGNS_QUERY_FALLBACK,
        flags=re.DOTALL,
    )
    assert campaigns_block is not None
    assert "stats" not in campaigns_block.group(0)


# -----------------------------------------------------------------------------
# _parse_summary tests — three response shapes
# -----------------------------------------------------------------------------


def _advertiser_node() -> dict:
    return {
        "id": "122463",
        "name": "Luxy Ride",
        "stats": {
            "impressionsBigint": "2844679",
            "clicksBigint": "709",
            "conversionsBigint": "56",
            "cost": "60385.884677",
            "ctr": 0.025,
            "ecpa": "1078.319",
            "roas": 0,
        },
    }


def _campaign_node(cid: str, name: str) -> dict:
    return {
        "id": cid,
        "name": name,
        "channelType": "Display",
        "campaignGroup": {"name": "Professionals"},
        "campaignStatus": {"status": "ACTIVE"},
    }


def _delivery_record(cid: str, **metrics) -> dict:
    return {
        "campaign": {"id": cid},
        "metrics": {
            "impressionsBigint": "0",
            "clicksBigint": "0",
            "conversionsBigint": "0",
            "cost": "0",
            "ctr": 0.0,
            "ecpa": None,
            "roas": None,
            **metrics,
        },
    }


def test_parse_summary_with_delivery_records_merges_metrics_by_id():
    """campaignDelivery records resolve to per-campaign metrics by id."""
    payload = {
        "data": {
            "advertisers": {"nodes": [_advertiser_node()]},
            "campaigns": {
                "nodes": [
                    _campaign_node("3141825", "ZGM-CTV-Prospecting-Execs"),
                    _campaign_node("3143140", "ZGM-CTV-Prospecting-Pros"),
                    _campaign_node("3143251", "ZGM-CTV-Prospecting-Leisure"),
                ]
            },
            "campaignDelivery": {
                "__typename": "CampaignDeliveryOutcome",
                "records": {
                    "nodes": [
                        _delivery_record(
                            "3141825",
                            impressionsBigint="185821",
                            clicksBigint="23",
                            conversionsBigint="5",
                            cost="6148.16",
                            ctr=0.012,
                            ecpa="1229.633",
                        ),
                        _delivery_record(
                            "3143251",
                            impressionsBigint="50000",
                            clicksBigint="100",
                            conversionsBigint="0",
                            cost="2500.0",
                            ctr=0.002,
                            ecpa=None,
                        ),
                        # 3143140 missing — campaign with no activity in window
                    ]
                },
            },
        }
    }

    summary = _parse_summary(payload)

    # Advertiser totals preserved verbatim.
    assert summary.advertiser_name == "Luxy Ride"
    assert summary.impressions == 2_844_679
    assert summary.conversions == 56
    assert summary.spend_usd == 60385.884677
    assert summary.cpa_usd == 1078.319
    assert summary.source == "live"

    # Per-campaign metrics merged by id.
    by_id = {c.id: c for c in summary.campaigns}
    assert len(by_id) == 3

    # Campaign with delivery record gets real metrics.
    assert by_id["3141825"].impressions == 185_821
    assert by_id["3141825"].conversions == 5
    assert by_id["3141825"].spend_usd == 6148.16
    assert by_id["3141825"].cpa_usd == 1229.633

    # Campaign with delivery record but zero conversions: cpa_usd is None.
    assert by_id["3143251"].impressions == 50_000
    assert by_id["3143251"].conversions == 0
    assert by_id["3143251"].cpa_usd is None  # not zero-as-float; None

    # Campaign WITHOUT a delivery record gets zero metrics — no activity
    # in the window, threshold generators correctly produce no signal.
    assert by_id["3143140"].impressions == 0
    assert by_id["3143140"].clicks == 0
    assert by_id["3143140"].conversions == 0
    assert by_id["3143140"].spend_usd == 0.0
    assert by_id["3143140"].cpa_usd is None
    # But campaign metadata (name, status, group) is still populated.
    assert by_id["3143140"].name == "ZGM-CTV-Prospecting-Pros"
    assert by_id["3143140"].status == "ACTIVE"


def test_parse_summary_with_progress_async_pending_yields_zero_metrics():
    """Progress union variant → log info + empty metrics, not a crash.

    StackAdapt may return Progress when the delivery query is being
    computed asynchronously. The next call cycle typically resolves to
    real records. Until then, the dashboard should render correctly with
    zero per-campaign metrics — threshold generators silently produce no
    signal, which is the right behavior under uncertainty.
    """
    payload = {
        "data": {
            "advertisers": {"nodes": [_advertiser_node()]},
            "campaigns": {
                "nodes": [_campaign_node("3141825", "ZGM-CTV")]
            },
            "campaignDelivery": {"__typename": "Progress", "_": "computing"},
        }
    }

    summary = _parse_summary(payload)

    # Advertiser totals still resolved.
    assert summary.advertiser_name == "Luxy Ride"
    assert summary.impressions == 2_844_679

    # Campaign present but with zero metrics.
    assert len(summary.campaigns) == 1
    c = summary.campaigns[0]
    assert c.id == "3141825"
    assert c.name == "ZGM-CTV"
    assert c.status == "ACTIVE"
    assert c.impressions == 0
    assert c.spend_usd == 0.0


def test_parse_summary_with_no_delivery_field_yields_zero_metrics():
    """Missing campaignDelivery (e.g. fallback query payload) → zero metrics.

    The fallback query intentionally omits campaignDelivery. _parse_summary
    handles this the same as Progress: campaigns get zero metrics,
    advertiser totals still populate from the advertisers node.
    """
    payload = {
        "data": {
            "advertisers": {"nodes": [_advertiser_node()]},
            "campaigns": {
                "nodes": [
                    _campaign_node("3141825", "ZGM-CTV-A"),
                    _campaign_node("3143140", "ZGM-CTV-B"),
                ]
            },
            # campaignDelivery absent — fallback path
        }
    }

    summary = _parse_summary(payload)

    assert summary.advertiser_name == "Luxy Ride"
    assert summary.impressions == 2_844_679
    assert summary.conversions == 56
    assert len(summary.campaigns) == 2
    for c in summary.campaigns:
        assert c.impressions == 0
        assert c.clicks == 0
        assert c.conversions == 0
        assert c.spend_usd == 0.0
        assert c.cpa_usd is None
        assert c.status == "ACTIVE"  # metadata still populated


def test_parse_summary_with_delivery_record_missing_campaign_id_is_skipped():
    """Defensive: a delivery record without campaign.id is silently skipped.

    Should not raise. Other records merge normally; the malformed record
    contributes nothing to the per-campaign map.
    """
    payload = {
        "data": {
            "advertisers": {"nodes": [_advertiser_node()]},
            "campaigns": {"nodes": [_campaign_node("3141825", "ZGM-CTV")]},
            "campaignDelivery": {
                "__typename": "CampaignDeliveryOutcome",
                "records": {
                    "nodes": [
                        # malformed: no campaign.id
                        {
                            "campaign": {},
                            "metrics": {
                                "impressionsBigint": "999",
                                "clicksBigint": "1",
                            },
                        },
                        _delivery_record(
                            "3141825", impressionsBigint="200", clicksBigint="3",
                        ),
                    ]
                },
            },
        }
    }

    summary = _parse_summary(payload)

    assert len(summary.campaigns) == 1
    c = summary.campaigns[0]
    assert c.id == "3141825"
    assert c.impressions == 200  # the well-formed record won
    assert c.clicks == 3
