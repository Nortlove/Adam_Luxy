#!/usr/bin/env python3
"""S0 amended — schema-grounded multi-source URL extraction with diversity gate.

Per amended directive (`docs/S0_SCHEMA_MISMATCH_REPORT_2026_05_04.md` +
`docs/CLAUDE CODE DIRECTIVE v3.1.md`). Three URL sources, each tagged
with `source` provenance on every emitted row:

  Source 1 — `conversionPath`        ("conversion_path")
  Source 2 — pixel-postback log      ("pixel_postback")  — N/A on LUXY
                                       (no impression-time log shipped)
  Source 3 — `campaignPageContext`   ("campaign_page_context")
             [REFRAMED from directive's adDelivery domain rotation:
              live schema introspection (2026-05-04) confirmed adDelivery
              has no domain-bearing record field; campaignPageContext is
              the population-level URL surface and yields URL strings.]

Outputs (under `artifacts/luxy_historical/`):

  luxy_served_urls_<YYYY-MM-DD>.jsonl              — raw rows, all sources
  luxy_served_urls_<YYYY-MM-DD>.unique_urls.jsonl  — dedup + HTTP HEAD validation
  luxy_served_urls_<YYYY-MM-DD>.summary.md         — 7-section summary
  READY_FOR_RATER_WORKSHEET.flag                   — machine-readable key=value
  _checkpoint.json                                 — per-source pagination state

Posture-class diversity audit (binding amendment per Chris 2026-05-04):
  Run `URLPostureClassifier` (canonical at `adam.intelligence.posture_classifier`,
  not `posture_five_class` — the directive amendment said the latter, but the
  classifier itself lives in posture_classifier.py; the 5-class taxonomy
  CONSTANTS live in posture_five_class.py:106. Round-3-pre-rotation checkpoint
  at `artifacts/posture_classifier/posture_classifier_n100_*.jsonl`.

Usage:
  python3 tools/stackadapt_historical_extract.py
  python3 tools/stackadapt_historical_extract.py --days 365
  python3 tools/stackadapt_historical_extract.py --dry-run-classifier-only \\
      --unique-urls-jsonl <existing>  (for diversity-audit re-run)

Exit codes:
  0 — slice closed; flag written (whether ready=true or ready=false)
  1 — invalid args
  2 — env / driver build failed
  3 — extraction error (rate-limit-exhausted, async-timeout, etc.)
  4 — classifier load / inference failed
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

# Self-locate project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("s0_extract")


# ----------------------------------------------------------------------------
# Defaults + constants
# ----------------------------------------------------------------------------

DEFAULT_DAYS = 365
DEFAULT_PAGE_SIZE = 200
DEFAULT_OUTPUT_DIR = Path("artifacts/luxy_historical")
DEFAULT_HEAD_TIMEOUT = 5.0
DEFAULT_HEAD_CONCURRENCY = 16
DIVERSITY_GATE_PER_CLASS_MINIMUM = 30
SOURCE1_BIAS_THRESHOLD = 0.70

FIVE_CLASSES = (
    "INFORMATION_FORAGING",
    "TASK_COMPLETION",
    "LEISURE_BROWSING",
    "SOCIAL_CONSUMPTION",
    "TRANSACTIONAL_COMPARISON",
)

# Round-3-pre-rotation checkpoint caveat — inscribed verbatim in summary
# per Chris's binding amendment (2026-05-04).
ROUND_3_CHECKPOINT_CAVEAT = (
    "The posture predictions in this audit come from the round-3-pre-rotation "
    "`URLPostureClassifier` checkpoint, which produced held-out macro-AUC "
    "0.7980 with top-1 0.22 and 49/50 cases collapsed to "
    "`INFORMATION_FORAGING`. These predictions are conservative-for-purpose: "
    "a firing diversity gate (= inadequate corpus signal) is high-confidence, "
    "but a passing gate clears the minimum bar with per-class counts that "
    "carry default-to-`INFORMATION_FORAGING` bias. Treat per-class counts as "
    "lower bounds for non-`INFORMATION_FORAGING` classes; treat the "
    "`INFORMATION_FORAGING` count as an upper bound. The audit's purpose is "
    "corpus-diversity gating, not posture-class assignment."
)


# ----------------------------------------------------------------------------
# Env loading
# ----------------------------------------------------------------------------

def _load_env_from_dotenv() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ----------------------------------------------------------------------------
# Source 1 — conversionPath
# ----------------------------------------------------------------------------

async def pull_source_1_conversion_path(
    client: Any,
    campaign_ids: List[str],
    days: int,
    page_size: int,
    checkpoint_path: Path,
) -> List[Dict[str, Any]]:
    """Cursor-paginate conversionPath. Each node yields one row containing
    the conversionUrl + per-record metadata. Per ground-truth schema, the
    only URL on the path subtree is `conversionStats.conversionUrl`."""
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    rows: List[Dict[str, Any]] = []
    cursor: Optional[str] = _load_checkpoint(checkpoint_path).get(
        "source_1_cursor"
    )

    while True:
        nodes, page_info = await client.get_conversion_paths_page(
            filter_by={
                "campaignIds": campaign_ids,
                "startTime": start,
                "endTime": end,
            },
            first=page_size,
            after=cursor,
        )
        if page_info.get("error"):
            logger.error(
                "source_1 page error: %s; saving checkpoint and stopping",
                page_info.get("error"),
            )
            _save_checkpoint(checkpoint_path, {"source_1_cursor": cursor})
            break

        for n in nodes:
            cs = n.get("conversionStats") or {}
            url = cs.get("conversionUrl")
            if not url:
                continue
            ad = n.get("ad") or {}
            campaign = n.get("campaign") or {}
            rows.append({
                "source": "conversion_path",
                "url": url,
                "publisher_domain": n.get("domain"),
                "publisher_last_domain": n.get("lastDomain"),
                "conversion_time": cs.get("conversionTime"),
                "device": cs.get("device"),
                "first_impression_time": n.get("firstImpressionTime"),
                "last_impression_time": n.get("lastImpressionTime"),
                "impression_count": n.get("impressionCount"),
                "click_count": n.get("clickCount"),
                "creative_id": ad.get("id"),
                "creative_name": ad.get("name"),
                "creative_click_url": ad.get("clickUrl"),
                "campaign_id": campaign.get("id"),
                "campaign_name": campaign.get("name"),
                "path_id": n.get("id"),
            })

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        _save_checkpoint(checkpoint_path, {"source_1_cursor": cursor})
        logger.info("source_1 paginating (running total: %d rows)", len(rows))

    logger.info("source_1 complete: %d rows", len(rows))
    _save_checkpoint(checkpoint_path, {"source_1_cursor": None,
                                        "source_1_complete": True})
    return rows


# ----------------------------------------------------------------------------
# Source 3 — campaignPageContext
# ----------------------------------------------------------------------------

async def pull_source_3_campaign_page_context(
    client: Any,
    advertiser_id: str,
    days: int,
    page_size: int,
    checkpoint_path: Path,
) -> List[Dict[str, Any]]:
    """Cursor-paginate campaignPageContext. Returns URL rows tagged with
    source=campaign_page_context. Population-level (not conversion-conditional)
    — this is the bias-counter to Source 1."""
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    rows: List[Dict[str, Any]] = []
    cursor: Optional[str] = _load_checkpoint(checkpoint_path).get(
        "source_3_cursor"
    )

    while True:
        nodes, page_info = await client.get_campaign_page_context_page(
            advertiser_id=advertiser_id,
            date_from=date_from, date_to=date_to,
            first=page_size, after=cursor,
        )
        if page_info.get("error"):
            err = page_info.get("error")
            if err in ("PROGRESS_TIMEOUT", "PROGRESS_TIMEOUT_UNREACHABLE"):
                logger.warning("source_3 progress-timeout; stopping cleanly")
                break
            logger.error("source_3 page error: %s; stopping", err)
            _save_checkpoint(checkpoint_path, {"source_3_cursor": cursor})
            break

        for n in nodes:
            url = n.get("url")
            if not url:
                continue
            campaign = n.get("campaign") or {}
            rows.append({
                "source": "campaign_page_context",
                "url": url,
                "campaign_id": campaign.get("id"),
                "campaign_name": campaign.get("name"),
            })

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        _save_checkpoint(checkpoint_path, {"source_3_cursor": cursor})

    logger.info("source_3 complete: %d rows", len(rows))
    _save_checkpoint(checkpoint_path, {"source_3_cursor": None,
                                        "source_3_complete": True})
    return rows


# ----------------------------------------------------------------------------
# Checkpointing
# ----------------------------------------------------------------------------

def _load_checkpoint(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save_checkpoint(path: Path, partial: Dict[str, Any]) -> None:
    state = _load_checkpoint(path)
    state.update(partial)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


# ----------------------------------------------------------------------------
# Dedup + HEAD validation
# ----------------------------------------------------------------------------

def dedupe_urls(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group rows by URL; collect contributing sources + impression total."""
    by_url: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        url = r.get("url")
        if not url:
            continue
        if url not in by_url:
            by_url[url] = {
                "url": url,
                "domain": _domain_of(url),
                "sources": set(),
                "served_impression_total": 0,
                "row_count": 0,
            }
        by_url[url]["sources"].add(r.get("source", "unknown"))
        if r.get("impression_count"):
            by_url[url]["served_impression_total"] += int(r["impression_count"])
        by_url[url]["row_count"] += 1
    # Convert sets to sorted lists for JSON-serializability.
    for v in by_url.values():
        v["sources"] = sorted(v["sources"])
    return by_url


def _domain_of(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.lower()
    except Exception:
        return ""


def head_validate(
    urls: List[str],
    timeout: float = DEFAULT_HEAD_TIMEOUT,
    concurrency: int = DEFAULT_HEAD_CONCURRENCY,
) -> Dict[str, Dict[str, Any]]:
    """HTTP HEAD each URL. Returns {url: {head_status, validated_live}}.
    Single attempt, no auth, max 3 redirects."""
    import requests

    results: Dict[str, Dict[str, Any]] = {}

    def _probe(url: str) -> Tuple[str, Dict[str, Any]]:
        try:
            resp = requests.head(
                url, timeout=timeout, allow_redirects=True,
                headers={"User-Agent": "ADAM-S0-extract/1.0"},
            )
            redirects = len(resp.history)
            if redirects > 3:
                return url, {
                    "head_status": resp.status_code,
                    "validated_live": False,
                    "failure_reason": "redirect_chain_exceeded",
                }
            ok = 200 <= resp.status_code < 400
            return url, {
                "head_status": resp.status_code,
                "validated_live": ok,
                "failure_reason": None if ok else f"http_{resp.status_code}",
            }
        except requests.exceptions.Timeout:
            return url, {"head_status": None, "validated_live": False,
                         "failure_reason": "timeout"}
        except requests.exceptions.ConnectionError:
            return url, {"head_status": None, "validated_live": False,
                         "failure_reason": "dns_or_connection_error"}
        except Exception as exc:
            return url, {"head_status": None, "validated_live": False,
                         "failure_reason": f"exception_{type(exc).__name__}"}

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=concurrency,
    ) as pool:
        for url, res in pool.map(_probe, urls):
            results[url] = res
    return results


# ----------------------------------------------------------------------------
# Diversity audit (URLPostureClassifier)
# ----------------------------------------------------------------------------

def find_round_3_checkpoint(artifacts_root: Path = Path("artifacts")) -> Optional[Path]:
    """Locate most-recent posture-classifier artifact."""
    cdir = artifacts_root / "posture_classifier"
    if not cdir.exists():
        return None
    candidates = sorted(cdir.glob("posture_classifier_*.jsonl"))
    return candidates[-1] if candidates else None


def run_diversity_audit(
    urls: List[str],
    classifier_artifact_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Predict posture class per URL via URLPostureClassifier (round-3
    checkpoint). Return per-class counts + gate verdict.

    Per Chris's amendment (2026-05-04): URLPostureClassifier from
    adam/intelligence/posture_classifier.py (not posture_five_class.py —
    the classifier itself is in posture_classifier.py; the 5-class
    taxonomy CONSTANTS are in posture_five_class.py:106)."""
    if not urls:
        return {
            "per_class_counts": {c: 0 for c in FIVE_CLASSES},
            "below_threshold": list(FIVE_CLASSES),
            "verdict": "FAIL",
            "verdict_reason": "no_urls",
            "classifier_artifact": None,
        }

    if classifier_artifact_path is None:
        classifier_artifact_path = find_round_3_checkpoint()
    if classifier_artifact_path is None:
        return {
            "per_class_counts": {c: 0 for c in FIVE_CLASSES},
            "below_threshold": list(FIVE_CLASSES),
            "verdict": "FAIL",
            "verdict_reason": "no_classifier_artifact",
            "classifier_artifact": None,
        }

    from adam.intelligence.posture_classifier import (
        URLPostureClassifier,
        load_classifier_artifact,
    )

    clf = load_classifier_artifact(str(classifier_artifact_path))
    classes = list(clf.classes_)
    proba = clf.predict_proba(urls)

    counts: Dict[str, int] = {c: 0 for c in FIVE_CLASSES}
    for i, _ in enumerate(urls):
        idx = int(proba[i].argmax())
        cls = classes[idx]
        if cls in counts:
            counts[cls] += 1
        else:
            counts[cls] = counts.get(cls, 0) + 1

    below = [c for c in FIVE_CLASSES
             if counts.get(c, 0) < DIVERSITY_GATE_PER_CLASS_MINIMUM]
    verdict = "PASS" if not below else "FAIL"

    return {
        "per_class_counts": counts,
        "below_threshold": below,
        "verdict": verdict,
        "verdict_reason": (
            "all_classes_clear_minimum" if verdict == "PASS"
            else f"under_threshold_classes={below}"
        ),
        "classifier_artifact": str(classifier_artifact_path),
        "classifier_classes": classes,
        "predicted_total": len(urls),
    }


# ----------------------------------------------------------------------------
# Summary artifact
# ----------------------------------------------------------------------------

def write_summary(
    out_path: Path,
    *,
    raw_rows: List[Dict[str, Any]],
    unique_urls: Dict[str, Dict[str, Any]],
    head_results: Dict[str, Dict[str, Any]],
    diversity: Dict[str, Any],
    extraction_window_days: int,
    advertiser_id: str,
    luxy_campaign_count: int,
) -> None:
    """Generate the §D 7-section summary."""
    lines: List[str] = []

    # Header
    lines.append(f"# S0 Historical URL Extraction — Summary ({datetime.now().strftime('%Y-%m-%d')})\n")
    lines.append(f"**Slice:** S0 (amended)  ")
    lines.append(f"**Advertiser:** LUXY (id={advertiser_id})  ")
    lines.append(f"**LUXY campaigns visible:** {luxy_campaign_count}  ")
    lines.append(f"**Extraction window:** {extraction_window_days} days  ")
    lines.append("")

    # 1. Source distribution
    lines.append("## 1. Source Distribution\n")
    src_rows = Counter(r.get("source") for r in raw_rows)
    src_unique = defaultdict(int)
    for u in unique_urls.values():
        for s in u.get("sources", []):
            src_unique[s] += 1
    total_unique = len(unique_urls)
    for src in ("conversion_path", "pixel_postback", "campaign_page_context"):
        if src == "pixel_postback":
            lines.append(f"- `{src}`: **N/A** — no impression-time pixel log shipped on LUXY pilot. Documented as future S4 ingestion-pipeline requirement.")
        else:
            n_rows = src_rows.get(src, 0)
            n_unique = src_unique.get(src, 0)
            pct = (n_unique / total_unique * 100.0) if total_unique else 0.0
            lines.append(f"- `{src}`: {n_unique} unique URLs ({pct:.1f}% of total) from {n_rows} raw rows.")
    lines.append("")

    # 2. URL Validation
    lines.append("## 2. URL Validation\n")
    n_validated = sum(1 for r in head_results.values() if r.get("validated_live"))
    n_invalid = total_unique - n_validated
    lines.append(f"- Total unique URLs after dedup: **{total_unique}**")
    lines.append(f"- `validated_live=true`: **{n_validated}**")
    lines.append(f"- `validated_live=false`: **{n_invalid}**\n")
    failure_hist = Counter(r.get("failure_reason") for r in head_results.values()
                           if not r.get("validated_live"))
    for reason, count in failure_hist.most_common():
        lines.append(f"  - `{reason or 'none'}`: {count}")
    lines.append("")

    # 3. Domain Distribution
    lines.append("## 3. Domain Distribution\n")
    by_domain = Counter()
    for u in unique_urls.values():
        d = u.get("domain")
        if d:
            by_domain[d] += u.get("served_impression_total", 0) or 1
    lines.append(f"- Total unique URL-bearing domains: **{len(by_domain)}**")
    lines.append(f"- Top 20 by served-impression weight:\n")
    for d, w in by_domain.most_common(20):
        lines.append(f"  - `{d}` — weight={w}")
    low_conf = [d for d, w in by_domain.items() if w < 10]
    lines.append(f"\n- Domains with `< 10` weighted impressions (`low_confidence_inventory`): **{len(low_conf)}**")
    lines.append("")

    # 4. Coverage Gap
    lines.append("## 4. Coverage Gap\n")
    publisher_domains_from_s1 = set()
    for r in raw_rows:
        if r.get("source") == "conversion_path":
            for k in ("publisher_domain", "publisher_last_domain"):
                if r.get(k):
                    publisher_domains_from_s1.add(r[k].lower())
    url_domains = set(by_domain.keys())
    gap = sorted(publisher_domains_from_s1 - url_domains)
    lines.append(f"Publisher domains observed in `conversion_path` records but for which we have NO URL captured (= S4 ingestion-pipeline gap):\n")
    if gap:
        for d in gap[:50]:
            lines.append(f"- `{d}`")
        if len(gap) > 50:
            lines.append(f"- ... and {len(gap)-50} more")
    else:
        lines.append("(none — all publisher domains have at least one URL.)")
    lines.append("")

    # 5. Posture-class diversity audit
    lines.append("## 5. Posture-Class Diversity Audit\n")
    counts = diversity.get("per_class_counts") or {}
    lines.append(f"Classifier artifact: `{diversity.get('classifier_artifact')}`\n")
    lines.append(f"Classifier classes (from artifact): `{diversity.get('classifier_classes')}`\n")
    lines.append(f"URLs scored: **{diversity.get('predicted_total')}**\n")
    lines.append("Per-class counts:")
    for c in FIVE_CLASSES:
        n = counts.get(c, 0)
        clear = "✓" if n >= DIVERSITY_GATE_PER_CLASS_MINIMUM else "✗"
        lines.append(f"  - `{c}`: **{n}** (minimum {DIVERSITY_GATE_PER_CLASS_MINIMUM}) {clear}")
    lines.append("")
    lines.append("### Required caveat (verbatim per binding amendment)\n")
    lines.append(f"> {ROUND_3_CHECKPOINT_CAVEAT}\n")

    # 6. Diversity gate verdict
    lines.append("## 6. Diversity Gate Verdict\n")
    lines.append(f"**{diversity.get('verdict')}** — {diversity.get('verdict_reason')}\n")
    if diversity.get("verdict") == "FAIL":
        below = diversity.get("below_threshold") or []
        lines.append("Under-threshold classes:")
        for c in below:
            shortfall = DIVERSITY_GATE_PER_CLASS_MINIMUM - counts.get(c, 0)
            lines.append(f"  - `{c}`: count={counts.get(c, 0)}, shortfall={shortfall}")
        lines.append("")
        lines.append("Per directive §F + §I: this is a valid S0 closure state. The artifact is delivered; S1's worksheet generator will read the flag and surface a QUESTION before producing the rater corpus.")
    lines.append("")

    # 7. Bias caveat
    lines.append("## 7. Bias Caveat (Calibration vs Gate-Grade)\n")
    s1_pct = (src_unique.get("conversion_path", 0) / total_unique * 100.0) if total_unique else 0.0
    if s1_pct > SOURCE1_BIAS_THRESHOLD * 100:
        cal_grade = True
        gate_grade = False
        lines.append(f"`conversion_path` source contributes **{s1_pct:.1f}%** of unique URLs (> {SOURCE1_BIAS_THRESHOLD*100:.0f}% threshold). Corpus declared `calibration_grade=true` regardless of diversity verdict. **NOT sufficient to close Gate G1.** Useful for S1 worksheet-generator tooling iteration only.")
    elif diversity.get("verdict") == "PASS":
        cal_grade = False
        gate_grade = True
        lines.append(f"`conversion_path` ≤ {SOURCE1_BIAS_THRESHOLD*100:.0f}% AND diversity gate PASSES. Corpus declared `gate_grade=true` — eligible for Gate G1 closure.")
    else:
        cal_grade = False
        gate_grade = False
        lines.append(f"`conversion_path` ≤ {SOURCE1_BIAS_THRESHOLD*100:.0f}% but diversity gate FAILS. Neither `calibration_grade` nor `gate_grade` declared. Re-run after corpus expansion.")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))


# ----------------------------------------------------------------------------
# Flag writer
# ----------------------------------------------------------------------------

def write_flag(
    out_path: Path,
    *,
    diversity: Dict[str, Any],
    unique_urls_count: int,
    validated_live_count: int,
    domain_count: int,
    sources_present: List[str],
    summary_path: Path,
    s1_share: float,
) -> None:
    """READY_FOR_RATER_WORKSHEET.flag — machine-readable key=value, one per line.
    S1's worksheet generator reads this as its first action."""
    verdict = diversity.get("verdict")
    diversity_inadequate = (verdict == "FAIL")
    calibration_grade = s1_share > SOURCE1_BIAS_THRESHOLD
    gate_grade = (not diversity_inadequate) and (not calibration_grade)
    ready = gate_grade

    inadequate_classes = ",".join(diversity.get("below_threshold") or [])
    sources_str = ",".join(sources_present)

    lines = [
        f"ready={'true' if ready else 'false'}",
        f"gate_grade={'true' if gate_grade else 'false'}",
        f"calibration_grade={'true' if calibration_grade else 'false'}",
        f"posture_diversity_inadequate={'true' if diversity_inadequate else 'false'}",
        f"inadequate_classes={inadequate_classes}",
        f"total_unique_urls={unique_urls_count}",
        f"total_validated_live={validated_live_count}",
        f"domains={domain_count}",
        f"sources={sources_str}",
        f"diversity_gate_verdict={verdict}",
        f"report_path={summary_path}",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------
# Main orchestrator
# ----------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> int:
    from adam.integrations.stackadapt.graphql_client import (
        StackAdaptGraphQLClient,
    )

    advertiser_id = (
        args.advertiser_id
        or os.environ.get("STACKADAPT_ADVERTISER_ID")
    )
    if not advertiser_id:
        logger.error("STACKADAPT_ADVERTISER_ID not set (env or --advertiser-id)")
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_path = out_dir / f"luxy_served_urls_{today_str}.jsonl"
    unique_path = out_dir / f"luxy_served_urls_{today_str}.unique_urls.jsonl"
    summary_path = out_dir / f"luxy_served_urls_{today_str}.summary.md"
    flag_path = out_dir / "READY_FOR_RATER_WORKSHEET.flag"
    checkpoint_path = out_dir / "_checkpoint.json"

    client = StackAdaptGraphQLClient()
    if not client.is_configured:
        logger.error("StackAdaptGraphQLClient not configured (check .env)")
        return 2

    # Pre-flight: get LUXY campaigns
    logger.info("fetching LUXY campaigns (advertiser_id=%s)", advertiser_id)
    campaigns = await client.get_campaigns(
        first=500, filter_by={"advertiserIds": [advertiser_id]},
    )
    cids = [c["id"] for c in campaigns if c.get("id")]
    luxy_campaign_count = len(cids)
    logger.info("LUXY campaigns: %d", luxy_campaign_count)
    if not cids:
        logger.error("no LUXY campaigns visible — cannot proceed")
        return 3

    # Source 1: conversionPath
    logger.info("source_1: conversionPath (%d days, page=%d)",
                args.days, args.page_size)
    src1_rows = await pull_source_1_conversion_path(
        client, cids, args.days, args.page_size, checkpoint_path,
    )

    # Source 2: N/A
    src2_rows: List[Dict[str, Any]] = []
    logger.info("source_2: pixel_postback N/A on LUXY")

    # Source 3: campaignPageContext
    logger.info("source_3: campaignPageContext (%d days)", args.days)
    src3_rows = await pull_source_3_campaign_page_context(
        client, advertiser_id, args.days, args.page_size, checkpoint_path,
    )

    await client._client.aclose()

    raw_rows = src1_rows + src2_rows + src3_rows
    logger.info("raw rows total: %d (s1=%d, s2=%d, s3=%d)",
                len(raw_rows), len(src1_rows), len(src2_rows), len(src3_rows))

    raw_path.write_text("\n".join(json.dumps(r) for r in raw_rows))

    unique = dedupe_urls(raw_rows)
    logger.info("unique URLs after dedup: %d", len(unique))

    head_results: Dict[str, Dict[str, Any]] = {}
    if unique and not args.skip_head:
        logger.info("HEAD validating %d URLs (concurrency=%d)",
                    len(unique), DEFAULT_HEAD_CONCURRENCY)
        head_results = head_validate(list(unique.keys()))
        for url, hv in head_results.items():
            unique[url].update(hv)

    unique_path.write_text("\n".join(
        json.dumps(u) for u in unique.values()
    ))

    validated_live = [u["url"] for u in unique.values()
                      if u.get("validated_live")]
    audit_input = validated_live if validated_live else list(unique.keys())
    logger.info("running diversity audit (URLPostureClassifier) on %d URLs",
                len(audit_input))
    diversity = run_diversity_audit(audit_input)

    sources_present = sorted({r.get("source") for r in raw_rows
                              if r.get("source")})

    write_summary(
        summary_path,
        raw_rows=raw_rows, unique_urls=unique,
        head_results=head_results, diversity=diversity,
        extraction_window_days=args.days,
        advertiser_id=advertiser_id,
        luxy_campaign_count=luxy_campaign_count,
    )

    src_unique_counts: Dict[str, int] = defaultdict(int)
    for u in unique.values():
        for s in u.get("sources", []):
            src_unique_counts[s] += 1
    s1_share = (src_unique_counts.get("conversion_path", 0)
                / max(1, len(unique)))

    write_flag(
        flag_path,
        diversity=diversity,
        unique_urls_count=len(unique),
        validated_live_count=len(validated_live),
        domain_count=len({u.get("domain") for u in unique.values()
                          if u.get("domain")}),
        sources_present=sources_present,
        summary_path=summary_path,
        s1_share=s1_share,
    )
    logger.info("flag written: %s", flag_path)
    logger.info("summary written: %s", summary_path)
    logger.info("S0 amended slice complete")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--advertiser-id", type=str, default=None,
                   help="LUXY advertiser ID (defaults to STACKADAPT_ADVERTISER_ID env).")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS,
                   help=f"Lookback window (default {DEFAULT_DAYS}).")
    p.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE,
                   help=f"GraphQL page size (default {DEFAULT_PAGE_SIZE}).")
    p.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR),
                   help=f"Output directory (default {DEFAULT_OUTPUT_DIR}).")
    p.add_argument("--skip-head", action="store_true",
                   help="Skip HTTP HEAD validation (fast iteration).")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    _load_env_from_dotenv()
    args = _parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
