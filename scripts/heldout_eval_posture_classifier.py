#!/usr/bin/env python3
"""Held-out cross-domain evaluation of the persisted 5-class posture
classifier — the canonical criterion-(ii) gate.

History (2026-05-02):
  The original criterion-(ii) gate was LOOCV macro-AUC ≥ 0.30 on all
  persisted :PostureLabel records. Round-2 active-learning concentrated
  100 labels in ~12 domain families. Under that distribution LOOCV's
  left-out URL almost always had 5–10 sibling URLs with near-identical
  template paths still in the training fold, so URL-tfidf could
  template-memorize its way to 0.9465. A held-out evaluation on 50
  URLs from new domains scored macro-AUC = 0.7980 with top-1 accuracy
  = 22% — the model had collapsed to predicting INFORMATION_FORAGING
  on 49 of 50 URLs. The LOOCV evaluator was demoted to diagnostic-only
  and this evaluator became the gate.

The gate (BOTH conditions must clear):
  * held-out macro-AUC ≥ 0.50  (cross-domain ranking signal real, not
    just template memorization)
  * held-out top-1 accuracy ≥ 0.40  (the L3 cascade picks argmax, not
    a ranked list — high AUC with broken calibration is not enough)

Usage:
    # default: pick most-recent artifact under artifacts/posture_classifier/
    python3 scripts/heldout_eval_posture_classifier.py

    # explicit artifact
    python3 scripts/heldout_eval_posture_classifier.py \\
        --artifact artifacts/posture_classifier/posture_classifier_n100_<ts>.jsonl

Exit codes:
  0  — gate PASS (both conditions clear)
  1  — gate FAIL
  2  — fixture / artifact load error

Held-out fixture: see HELDOUT_URLS below — 50 URLs (10 per posture)
hand-curated from domains NOT present in any round-1 / round-2 /
round-3 training corpus. Treat as fixture, not training data: NEVER
persist these to :PostureLabel (would contaminate the gate).

Fixture-rotation trail (HELDOUT_ROTATION_MANIFEST below):
  * 2026-05-03  initial 50-URL fixture authored, but post-curation
    audit found docs.google.com/document/d/abc123/edit collided with
    training URL calendar.google.com/calendar/u/0/r (round-1 TASK
    label). Swapped to 3.basecamp.com/12345/projects/67890 to enforce
    the permanent fixture-isolation rule (held-out fixture domains
    must never appear in any training set, ever).
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

# Self-locate project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from adam.intelligence.posture_classifier import (
    DEFAULT_RANDOM_STATE,
    URLPostureClassifier,
    _bootstrap_macro_auc_ci,
    _per_class_one_vs_rest_auc,
    load_classifier_artifact,
)


# =============================================================================
# Gate thresholds — see module docstring for derivation.
# =============================================================================
GATE_MACRO_AUC_MIN: float = 0.50
GATE_TOP1_ACC_MIN: float = 0.40


# =============================================================================
# Held-out URL fixture — 50 URLs, 10 per posture, all from domains
# OUTSIDE the n=100 training corpus that closed (and was reopened from)
# the original LOOCV gate.
#
# Excluded training domains: kayak.com, businessinsider.com, reddit.com,
# concur.com, expensify.com, skift.com, bloomberg.com, nytimes.com,
# cntraveler.com, travelandleisure.com, hotels.com, afar.com, notion.so,
# clickup.com, nerdwallet.com, trustpilot.com, glassdoor.com, linkedin.com,
# bbc.com, news.ycombinator.com, architecturaldigest.com, bonappetit.com,
# eater.com, asana.com, calendar.google.com, investopedia.com,
# consumerreports.org, thepointsguy.com.
# =============================================================================
HELDOUT_URLS: List[Tuple[str, str, str]] = [
    # --- INFORMATION_FORAGING (10) ---
    ("https://www.tomsguide.com/best-picks/best-laptops-for-business-use",
     "INFORMATION_FORAGING", "Tom's Guide best-picks roundup"),
    ("https://www.cnet.com/tech/services-and-software/best-vpn/",
     "INFORMATION_FORAGING", "CNET best-VPN comparison roundup"),
    ("https://www.pcmag.com/picks/the-best-business-cloud-storage-services",
     "INFORMATION_FORAGING", "PCMag editor's-picks roundup"),
    ("https://www.zdnet.com/article/best-business-credit-card/",
     "INFORMATION_FORAGING", "ZDNet best-X article"),
    ("https://www.theverge.com/22808642/expense-management-software-comparison",
     "INFORMATION_FORAGING", "The Verge software-comparison piece"),
    ("https://www.engadget.com/best-business-laptops-130000821.html",
     "INFORMATION_FORAGING", "Engadget best-laptops review"),
    ("https://stratechery.com/2025/the-state-of-saas-2025/",
     "INFORMATION_FORAGING", "Stratechery long-form analysis"),
    ("https://hbr.org/2025/04/the-corporate-travel-recovery",
     "INFORMATION_FORAGING", "HBR research article"),
    ("https://www.mckinsey.com/industries/travel-logistics-and-infrastructure/our-insights/business-travel-2025",
     "INFORMATION_FORAGING", "McKinsey industry insights"),
    ("https://www.gartner.com/reviews/market/expense-management-software",
     "INFORMATION_FORAGING", "Gartner reviews market category"),

    # --- TRANSACTIONAL_COMPARISON (10) ---
    ("https://www.expedia.com/Hotels-Search?destination=Paris",
     "TRANSACTIONAL_COMPARISON", "Expedia hotel search"),
    ("https://www.booking.com/searchresults.html?dest_id=-2601889",
     "TRANSACTIONAL_COMPARISON", "Booking.com search results"),
    ("https://www.priceline.com/relax/in/3000017479/from/20250915/to/20250918",
     "TRANSACTIONAL_COMPARISON", "Priceline specific-property comparison"),
    ("https://www.amazon.com/dp/B09G9HD6PD",
     "TRANSACTIONAL_COMPARISON", "Amazon product detail — purchase-evaluation"),
    ("https://www.bestbuy.com/site/searchpage.jsp?st=laptop",
     "TRANSACTIONAL_COMPARISON", "BestBuy laptop search"),
    ("https://www.cars.com/shopping/results/?stock_type=used&makes[]=toyota",
     "TRANSACTIONAL_COMPARISON", "Cars.com inventory comparison"),
    ("https://www.zillow.com/homes/for_sale/Brooklyn-NY/",
     "TRANSACTIONAL_COMPARISON", "Zillow listing comparison"),
    ("https://www.redfin.com/city/30749/NY/Brooklyn",
     "TRANSACTIONAL_COMPARISON", "Redfin listing comparison"),
    ("https://www.carvana.com/cars/toyota-camry",
     "TRANSACTIONAL_COMPARISON", "Carvana model-search comparison"),
    ("https://www.vrbo.com/search?destination=Tokyo",
     "TRANSACTIONAL_COMPARISON", "VRBO search results"),

    # --- LEISURE_BROWSING (10) ---
    ("https://www.vogue.com/article/met-gala-2025-best-dressed",
     "LEISURE_BROWSING", "Vogue lifestyle article"),
    ("https://www.gq.com/story/best-watches-2025",
     "LEISURE_BROWSING", "GQ lifestyle browsing"),
    ("https://www.elledecor.com/design-decorate/house-tours/",
     "LEISURE_BROWSING", "Elle Decor house tours"),
    ("https://www.foodandwine.com/best-new-restaurants-2025",
     "LEISURE_BROWSING", "Food & Wine lifestyle"),
    ("https://www.thekitchn.com/recipes/quick-weeknight-dinners",
     "LEISURE_BROWSING", "The Kitchn recipe browsing"),
    ("https://www.atlasobscura.com/places/hidden-gems-paris",
     "LEISURE_BROWSING", "Atlas Obscura — diffuse exploration"),
    ("https://www.smithsonianmag.com/travel/best-museums-world",
     "LEISURE_BROWSING", "Smithsonian Magazine browsing"),
    ("https://www.outsideonline.com/2418701/best-hiking-gear-2025/",
     "LEISURE_BROWSING", "Outside Online lifestyle/gear browsing"),
    ("https://www.surfer.com/news/best-surf-spots-portugal",
     "LEISURE_BROWSING", "Surfer Magazine lifestyle"),
    ("https://www.refinery29.com/en-us/celebrity-style-2025",
     "LEISURE_BROWSING", "Refinery29 lifestyle browsing"),

    # --- SOCIAL_CONSUMPTION (10) ---
    ("https://twitter.com/home",
     "SOCIAL_CONSUMPTION", "Twitter home feed"),
    ("https://www.tiktok.com/foryou",
     "SOCIAL_CONSUMPTION", "TikTok For You feed"),
    ("https://www.instagram.com/explore/",
     "SOCIAL_CONSUMPTION", "Instagram explore feed"),
    ("https://www.facebook.com/",
     "SOCIAL_CONSUMPTION", "Facebook home feed"),
    ("https://medium.com/explore/business",
     "SOCIAL_CONSUMPTION", "Medium feed-driven content"),
    ("https://substack.com/inbox",
     "SOCIAL_CONSUMPTION", "Substack newsletter inbox"),
    ("https://www.npr.org/sections/news/",
     "SOCIAL_CONSUMPTION", "NPR news feed"),
    ("https://www.cnn.com/business",
     "SOCIAL_CONSUMPTION", "CNN business news feed"),
    ("https://www.washingtonpost.com/business/",
     "SOCIAL_CONSUMPTION", "WaPo business news feed"),
    ("https://www.theguardian.com/business",
     "SOCIAL_CONSUMPTION", "Guardian business news feed"),

    # --- TASK_COMPLETION (10) ---
    ("https://app.slack.com/client/T01ABC/CXX1234",
     "TASK_COMPLETION", "Slack workspace — in-flow comms"),
    ("https://app.zoom.us/wc/join/12345",
     "TASK_COMPLETION", "Zoom meeting join — in-flow"),
    ("https://app.monday.com/boards/12345",
     "TASK_COMPLETION", "Monday.com board — task tooling"),
    ("https://3.basecamp.com/12345/projects/67890",
     "TASK_COMPLETION", "Basecamp project — in-flow productivity"),
    ("https://www.dropbox.com/home",
     "TASK_COMPLETION", "Dropbox home — file management"),
    ("https://app.salesforce.com/lightning/o/Lead/list",
     "TASK_COMPLETION", "Salesforce Lead list — workflow"),
    ("https://app.figma.com/files/recent",
     "TASK_COMPLETION", "Figma recent files — design tooling"),
    ("https://app.airtable.com/workspace",
     "TASK_COMPLETION", "Airtable workspace — productivity"),
    ("https://qbo.intuit.com/app/homepage",
     "TASK_COMPLETION", "QuickBooks home — accounting tool"),
    ("https://app.hubspot.com/contacts/12345",
     "TASK_COMPLETION", "HubSpot contacts — CRM workflow"),
]


# =============================================================================
# Held-out fixture rotation manifest. Append-only audit trail. Each
# entry records one swap: dropped URL, replacement URL, and the reason
# (training-domain collision is the binding reason). Append, never
# rewrite history.
# =============================================================================
HELDOUT_ROTATION_MANIFEST: List[Dict[str, str]] = [
    {
        "rotation_id": "2026-05-03-001",
        "class": "TASK_COMPLETION",
        "out_url": "https://docs.google.com/document/d/abc123/edit",
        "out_domain": "google.com",
        "in_url": "https://3.basecamp.com/12345/projects/67890",
        "in_domain": "basecamp.com",
        "reason": (
            "Training corpus contains calendar.google.com (round-1 "
            "TASK label) — google.com violated the permanent fixture-"
            "isolation rule. Replaced with basecamp.com which is "
            "absent from training and from round-3 candidates."
        ),
    },
]


def _resolve_artifact_path(explicit: str | None) -> str | None:
    """Return the explicit path if given; else the most recent
    posture_classifier_n*.jsonl under artifacts/posture_classifier/."""
    if explicit:
        return explicit
    root = Path(__file__).resolve().parent.parent
    art_dir = root / "artifacts" / "posture_classifier"
    if not art_dir.exists():
        return None
    cands = sorted(
        art_dir.glob("posture_classifier_n*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return str(cands[0]) if cands else None


def _format_confusion(
    classes: List[str],
    confusion: Dict[str, Counter[str]],
) -> str:
    lines = []
    header = " " * 30 + "  ".join(f"{c[:10]:>10s}" for c in classes)
    lines.append(header)
    for true_lbl in classes:
        row = f"  {true_lbl:28s}"
        for pred_lbl in classes:
            cnt = confusion[true_lbl].get(pred_lbl, 0)
            mark = "*" if pred_lbl == true_lbl else " "
            row += f"  {cnt:>9d}{mark}"
        lines.append(row)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--artifact", type=str, default=None,
        help="Explicit classifier artifact path. Defaults to the most "
             "recent posture_classifier_n*.jsonl under artifacts/.",
    )
    parser.add_argument(
        "--bootstrap-n", type=int, default=1000,
        help="Bootstrap samples for macro-AUC 95%% CI. Default 1000.",
    )
    args = parser.parse_args()

    art_path = _resolve_artifact_path(args.artifact)
    if not art_path or not Path(art_path).exists():
        print(
            f"ERROR: classifier artifact not found "
            f"(artifact={art_path!r}). Train one with "
            f"scripts/train_and_evaluate_posture_classifier.py first.",
            file=sys.stderr,
        )
        return 2

    try:
        clf: URLPostureClassifier = load_classifier_artifact(art_path)
    except Exception as exc:
        print(f"ERROR: failed to load artifact {art_path}: {exc}",
              file=sys.stderr)
        return 2

    classes = list(clf.classes_)
    urls = [u for u, _, _ in HELDOUT_URLS]
    y_true = [lbl for _, lbl, _ in HELDOUT_URLS]
    dist = Counter(y_true)

    proba = clf.predict_proba(urls)
    if proba.shape != (len(urls), len(classes)):
        print(
            f"ERROR: predict_proba returned unexpected shape "
            f"{proba.shape} (expected ({len(urls)}, {len(classes)}))",
            file=sys.stderr,
        )
        return 2

    per_class = _per_class_one_vs_rest_auc(y_true, proba, classes)
    macro = float(np.mean(list(per_class.values())))
    ci_lo, ci_hi = _bootstrap_macro_auc_ci(
        y_true, proba, classes,
        n_bootstrap=int(args.bootstrap_n),
        seed=DEFAULT_RANDOM_STATE,
    )

    pred = [classes[int(np.argmax(p))] for p in proba]
    n_correct = sum(1 for a, b in zip(pred, y_true) if a == b)
    top1 = n_correct / len(y_true)

    confusion: Dict[str, Counter[str]] = {c: Counter() for c in classes}
    for t, p in zip(y_true, pred):
        confusion[t][p] += 1

    auc_pass = macro >= GATE_MACRO_AUC_MIN
    top1_pass = top1 >= GATE_TOP1_ACC_MIN
    gate_pass = auc_pass and top1_pass

    print("=" * 80)
    print("HELD-OUT POSTURE CLASSIFIER GATE — criterion (ii)")
    print("=" * 80)
    print(f"artifact:        {art_path}")
    print(f"n_heldout:       {len(urls)}  (10 per posture)")
    print(f"classifier:      v0.1-url-tfidf-logreg (frozen)")
    print()
    print("Per-class held-out one-vs-rest AUC:")
    for c in sorted(classes, key=lambda c: -per_class[c]):
        print(f"  {c:28s} AUC={per_class[c]:.4f}  (n={dist.get(c, 0)})")
    print()
    print(f"Macro-AUC:                 {macro:.4f}")
    print(f"Bootstrap 95% CI:          [{ci_lo:.4f}, {ci_hi:.4f}]")
    print(f"Top-1 accuracy:            {top1:.4f}  ({n_correct}/{len(y_true)})")
    print()
    print(f"Gate threshold (macro-AUC ≥ {GATE_MACRO_AUC_MIN:.2f}):  "
          f"{'✓ PASS' if auc_pass else '✗ FAIL'}")
    print(f"Gate threshold (top-1 ≥ {GATE_TOP1_ACC_MIN:.2f}):       "
          f"{'✓ PASS' if top1_pass else '✗ FAIL'}")
    print(f"Gate decision (BOTH must clear): "
          f"{'✓ PASS — criterion (ii) closed' if gate_pass else '✗ FAIL — criterion (ii) OPEN'}")
    print()
    print("Confusion (rows=true, cols=predicted, * = correct):")
    print(_format_confusion(classes, confusion))
    print()
    print("Misclassified URLs:")
    n_wrong = 0
    for url, t, p, pr in zip(urls, y_true, pred, proba):
        if t != p:
            n_wrong += 1
            top_p = float(np.max(pr))
            print(f"  TRUE={t:24s} PRED={p:24s} p={top_p:.3f}  {url}")
    if n_wrong == 0:
        print("  (none)")
    print()
    print("=" * 80)

    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
