#!/usr/bin/env python3
"""URL resolution + reality audit for the posture-classifier corpus.

Diagnoses the 2026-05-03 discovery that earlier corpus + held-out
fixture URLs were synthetic templates (placeholder workspace IDs,
SaaS-interior app paths the bid stream never sees) rather than real
live pages. Without resolving real URLs, URL-tfidf training learns
template structure and the held-out gate measures template
recognition — exactly what the gate is meant to defeat.

For each URL, the audit captures:

  * HTTP HEAD status (with redirect-following) — does the URL
    actually return a page?
  * Final URL after redirects — did the request land on the
    requested path or get bounced to a generic homepage / login?
  * SaaS-interior heuristics — hostname starts with "app.",
    "my.", or has known authenticated-app subdomains the
    StackAdapt bid stream cannot see ad inventory on.
  * Synthetic-pattern regex matches — placeholder strings I
    generated when constructing templates (T0ABC, appXYZ,
    myteam, B0NEWPROD123, dest_id=Tokyo, /abc123/, etc.).
  * A recommendation: KEEP / REPLACE / REVIEW.

Three CSVs are written under audits/url_resolution_<ts>/:
  * training_corpus.csv   — all :PostureLabel rows
  * heldout_fixture.csv   — HELDOUT_URLS in scripts/heldout_eval_*
  * round_3_surface.csv   — current round-3 candidates JSONL

Usage:
    python3 scripts/audit_posture_url_resolution.py
    python3 scripts/audit_posture_url_resolution.py --workers 8

Exit 0 always (audit is diagnostic; downstream decisions are
operator's). Stdout summary lists per-population KEEP/REPLACE/REVIEW
totals plus the synthetic-pattern hit count — that's the headline
number for "how much of the corpus is template, not page."

NOTE: This audit only does HEAD checks. It does NOT attempt to
verify that the live page's CONTENT is consistent with its assigned
label — that's a content-inspection check the operator does on the
URLs the audit returns as KEEP. The audit catches "doesn't resolve"
and "obviously synthetic"; the operator catches "resolves but the
page isn't what we labeled."
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures as cf
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Self-locate project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests


# =============================================================================
# Synthetic-pattern detection
# =============================================================================

# Regexes that match placeholder strings I generated when
# constructing templates. Each match is strong evidence the URL is
# synthetic, not live.
_SYNTHETIC_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("workspace_id_T0ABC",     re.compile(r"T0[A-Z]{2,}")),
    ("workspace_id_T01ABC",    re.compile(r"T01[A-Z]{3,}")),
    ("channel_id_CXX",         re.compile(r"CXX\d+")),
    ("dm_id_D1234",            re.compile(r"/D\d{3,}")),
    ("airtable_appXYZ",        re.compile(r"app[A-Z]{3,}/tbl[A-Z]{3,}")),
    ("placeholder_myteam",     re.compile(r"/myteam(/|$)")),
    ("placeholder_myproject",  re.compile(r"/myproject(/|$)")),
    ("placeholder_myorg",      re.compile(r"/myorg(/|$)")),
    ("placeholder_myrepo",     re.compile(r"/myrepo(/|$)")),
    ("placeholder_abc123",     re.compile(r"/abc\d{3,}/")),
    ("placeholder_amazon_b0",  re.compile(r"/B0(NEWPROD|XYZ|ABCDEFGH)")),
    ("placeholder_12345",      re.compile(r"/12345(/|$|\.html)")),
    ("placeholder_some_hotel", re.compile(r"/some-hotel\.html")),
    ("placeholder_main_st",    re.compile(r"123-Main-St")),
    ("placeholder_dest_id",    re.compile(r"dest_id=(Tokyo|-?\d+)$")),
    ("placeholder_h12345",     re.compile(r"/h12345\.")),
    ("placeholder_de1632789",  re.compile(r"/de1632789/")),
    ("placeholder_PROJ",       re.compile(r"/PROJ/")),
    ("placeholder_zpid",       re.compile(r"/12345_zpid/")),
    ("placeholder_relax_in",   re.compile(r"/relax/in/3000017479")),
    ("synthetic_kayak_dates",  re.compile(r"/(JFK|LAX|SFO|ORD|EWR|DFW)-[A-Z]{3}/202[5-6]-\d{2}-\d{2}")),
    ("placeholder_67890",      re.compile(r"/67890")),
    ("doc_abc123",             re.compile(r"/abc123/edit")),
]


def synthetic_pattern_matches(url: str) -> List[str]:
    """Return list of pattern names that match. Empty list if none."""
    return [name for name, pat in _SYNTHETIC_PATTERNS if pat.search(url)]


# =============================================================================
# SaaS-interior heuristics
# =============================================================================

# Hostname prefixes that strongly indicate authenticated SaaS-app
# interiors — paths inside these subdomains generally require login
# and are never seen in a publisher bid stream.
_SAAS_INTERIOR_HOST_PREFIXES: Tuple[str, ...] = (
    "app.", "my.", "qbo.", "use.", "outlook.live.", "outlook.office.",
    "teams.microsoft.", "onedrive.live.", "drive.google.",
    "calendar.google.", "docs.google.", "sheets.google.",
    "mail.google.", "3.basecamp.", "discord.com/channels/",
)

# Domains that are ENTIRELY app-only (no marketing surface at root):
_PURE_SAAS_DOMAINS: Tuple[str, ...] = (
    "linear.app",  # marketing also at linear.app/, app at linear.app/inbox etc.
)


def is_saas_interior(url: str) -> bool:
    """Heuristic: would StackAdapt's bid stream plausibly see this
    URL? SaaS-interior URLs (app.slack.com/client/X) almost never
    appear in publisher bid streams — they're authenticated app
    surfaces, not ad-supported content."""
    p = urlparse(url)
    host = (p.netloc or "").lower()
    full = host + p.path
    for prefix in _SAAS_INTERIOR_HOST_PREFIXES:
        if host.startswith(prefix) or full.startswith(prefix):
            return True
    return False


def is_homepage_redirect(original_url: str, final_url: str) -> bool:
    """Final URL is just the domain root + maybe trailing slash,
    while original had a deeper path → site bounced us to homepage
    (commonly a 404-style soft redirect)."""
    op = urlparse(original_url)
    fp = urlparse(final_url)
    orig_path = (op.path or "/").rstrip("/")
    final_path = (fp.path or "/").rstrip("/")
    # Heuristic: original had a non-empty path; final landed at root
    # or a path much shorter than original.
    if orig_path in ("", "/"):
        return False  # original was already homepage-ish
    if final_path in ("", "/"):
        return True
    # Same hostname but final path is significantly shorter → likely
    # a generic landing page.
    if op.netloc == fp.netloc and len(final_path) < 3 and len(orig_path) > 10:
        return True
    return False


# =============================================================================
# HTTP probe
# =============================================================================

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _USER_AGENT, "Accept": "*/*"}


def probe_url(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """HEAD with redirect-following. Falls back to GET-stream on 405.
    Captures final URL + status. Never raises."""
    try:
        r = requests.head(
            url, headers=_HEADERS, allow_redirects=True, timeout=timeout,
        )
        if r.status_code == 405:
            # Site rejects HEAD; try GET with stream + close
            r = requests.get(
                url, headers=_HEADERS, allow_redirects=True,
                timeout=timeout, stream=True,
            )
            try:
                r.raw.close()
            except Exception:
                pass
        return {
            "http_ok": True,
            "status": r.status_code,
            "final_url": r.url,
            "n_redirects": len(r.history),
            "error": "",
        }
    except requests.Timeout:
        return {"http_ok": False, "status": -1, "final_url": "",
                "n_redirects": 0, "error": "timeout"}
    except requests.ConnectionError as e:
        return {"http_ok": False, "status": -1, "final_url": "",
                "n_redirects": 0, "error": f"connection_error: {e!s}[:120]"}
    except Exception as e:
        return {"http_ok": False, "status": -1, "final_url": "",
                "n_redirects": 0, "error": f"{type(e).__name__}: {e!s}"[:200]}


# =============================================================================
# Recommendation logic
# =============================================================================

def make_recommendation(
    probe: Dict[str, Any],
    original_url: str,
    saas_interior: bool,
    synthetic_matches: List[str],
) -> Tuple[str, str]:
    """Return (recommendation, reason).

    KEEP    — looks real-and-live (HEAD-200, no homepage redirect,
              no synthetic patterns, not SaaS interior).
    REPLACE — clear failure (4xx/5xx, timeout, homepage redirect,
              synthetic pattern hit, SaaS interior).
    REVIEW  — ambiguous (auth-required, anti-bot, HEAD rejected
              with no GET fallback signal).
    """
    if synthetic_matches:
        return "REPLACE", f"synthetic_pattern: {','.join(synthetic_matches)}"
    if saas_interior:
        return "REPLACE", "saas_interior_subdomain (not in bid stream)"
    if not probe["http_ok"]:
        return "REPLACE", f"http_error: {probe['error']}"
    status = probe["status"]
    if status == 0 or status < 0:
        return "REPLACE", "no_status"
    if 200 <= status < 300:
        if is_homepage_redirect(original_url, probe["final_url"]):
            return "REPLACE", (
                f"homepage_redirect ({original_url} → {probe['final_url']})"
            )
        return "KEEP", f"http_{status}"
    if status in (401, 403, 429):
        return "REVIEW", f"http_{status} (auth/anti-bot — verify by hand)"
    if status in (404, 410):
        return "REPLACE", f"http_{status} (page not found)"
    if 300 <= status < 400:
        return "REVIEW", f"http_{status} (unhandled redirect)"
    if 500 <= status < 600:
        return "REVIEW", f"http_{status} (server error — re-probe later)"
    return "REVIEW", f"http_{status}"


# =============================================================================
# Population loaders
# =============================================================================

def _load_env() -> None:
    p = Path("/Users/chrisnocera/Sites/adam-platform/.env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(
                    k.strip(), v.strip().strip('"').strip("'"),
                )


async def _load_training_corpus() -> List[Dict[str, Any]]:
    """All :PostureLabel rows: url, label, labeler, labeled_at_ts."""
    from neo4j import AsyncGraphDatabase
    from adam.intelligence.posture_five_class import load_labeled_pages

    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    pwd = os.environ["NEO4J_PASSWORD"]
    drv = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
    await drv.verify_connectivity()
    try:
        entries = await load_labeled_pages(drv, limit=10000)
    finally:
        await drv.close()
    return [{
        "url": e.url, "label": e.label, "labeler": e.labeler,
        "labeled_at_ts": e.labeled_at_ts,
    } for e in entries]


def _load_heldout_fixture() -> List[Dict[str, Any]]:
    from scripts.heldout_eval_posture_classifier import HELDOUT_URLS
    return [{"url": u, "label": lbl, "rationale": r}
            for u, lbl, r in HELDOUT_URLS]


def _load_round_3_surface() -> List[Dict[str, Any]]:
    p = Path(
        "/Users/chrisnocera/Sites/adam-platform/artifacts/posture_round_3/"
        "round_3_diversification_candidates.jsonl"
    )
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("_record_type") == "candidate":
            out.append({
                "url": obj["url"],
                "label": obj["target_class"],
                "source": obj.get("source", ""),
                "rationale": obj.get("rationale", ""),
            })
    return out


# =============================================================================
# Audit driver
# =============================================================================

def audit_population(
    rows: List[Dict[str, Any]],
    workers: int,
    population_name: str,
) -> List[Dict[str, Any]]:
    """Probe every URL in parallel; attach diagnostic columns;
    return enriched rows."""
    print(f"\n[{population_name}] probing {len(rows)} URLs "
          f"with {workers} workers...")
    t0 = time.time()
    probes: Dict[str, Dict[str, Any]] = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(probe_url, r["url"]): r["url"] for r in rows}
        done = 0
        for fut in cf.as_completed(futures):
            url = futures[fut]
            try:
                probes[url] = fut.result()
            except Exception as e:
                probes[url] = {
                    "http_ok": False, "status": -1, "final_url": "",
                    "n_redirects": 0, "error": f"future_error: {e!s}",
                }
            done += 1
            if done % 25 == 0 or done == len(rows):
                print(f"  {done}/{len(rows)} done "
                      f"({time.time() - t0:.1f}s)")
    # Enrich
    enriched: List[Dict[str, Any]] = []
    for r in rows:
        url = r["url"]
        pr = probes[url]
        synth = synthetic_pattern_matches(url)
        saas = is_saas_interior(url)
        rec, reason = make_recommendation(pr, url, saas, synth)
        enriched.append({
            **r,
            "http_status": pr["status"],
            "http_error": pr["error"],
            "final_url": pr["final_url"],
            "n_redirects": pr["n_redirects"],
            "saas_interior": saas,
            "synthetic_patterns": ";".join(synth),
            "recommendation": rec,
            "recommendation_reason": reason,
        })
    return enriched


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("")
        return
    cols = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k))
                        for k in cols})


def summarize(name: str, rows: List[Dict[str, Any]]) -> None:
    from collections import Counter
    rec_counts = Counter(r["recommendation"] for r in rows)
    by_class_rec: Dict[str, Counter[str]] = {}
    for r in rows:
        by_class_rec.setdefault(r["label"], Counter())[r["recommendation"]] += 1
    n_synth = sum(1 for r in rows if r["synthetic_patterns"])
    n_saas = sum(1 for r in rows if r["saas_interior"])
    print(f"\n=== {name} (n={len(rows)}) ===")
    print(f"  Overall: KEEP={rec_counts['KEEP']} "
          f"REPLACE={rec_counts['REPLACE']} "
          f"REVIEW={rec_counts['REVIEW']}")
    print(f"  Synthetic-pattern hits: {n_synth}")
    print(f"  SaaS-interior URLs:     {n_saas}")
    print(f"  Per-class breakdown:")
    for cls in sorted(by_class_rec):
        c = by_class_rec[cls]
        print(f"    {cls:28s}  KEEP={c['KEEP']:>3}  "
              f"REPLACE={c['REPLACE']:>3}  REVIEW={c['REVIEW']:>3}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--workers", type=int, default=12,
                    help="Concurrent HEAD probes. Default 12.")
    args = ap.parse_args()

    _load_env()

    out_dir = Path(
        f"/Users/chrisnocera/Sites/adam-platform/audits/"
        f"url_resolution_{int(time.time())}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Training corpus
    print("Loading :PostureLabel rows from Neo4j...")
    train_rows = asyncio.run(_load_training_corpus())
    train_enriched = audit_population(train_rows, args.workers,
                                      "TRAINING CORPUS")
    write_csv(train_enriched, out_dir / "training_corpus.csv")

    # 2) Held-out fixture
    held_rows = _load_heldout_fixture()
    held_enriched = audit_population(held_rows, args.workers,
                                     "HELD-OUT FIXTURE")
    write_csv(held_enriched, out_dir / "heldout_fixture.csv")

    # 3) Round-3 surface
    r3_rows = _load_round_3_surface()
    r3_enriched = audit_population(r3_rows, args.workers,
                                   "ROUND-3 SURFACE")
    write_csv(r3_enriched, out_dir / "round_3_surface.csv")

    print("\n" + "=" * 72)
    print("SUMMARIES")
    print("=" * 72)
    summarize("TRAINING CORPUS", train_enriched)
    summarize("HELD-OUT FIXTURE", held_enriched)
    summarize("ROUND-3 SURFACE", r3_enriched)

    print(f"\nCSVs written to: {out_dir}")
    print("Next step: operator reviews each CSV, decides which URLs"
          " to delete from :PostureLabel and which fixture URLs to"
          " replace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
