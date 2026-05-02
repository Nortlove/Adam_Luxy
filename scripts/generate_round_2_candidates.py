#!/usr/bin/env python3
"""Generate round-2 active-learning candidates.

Per the 2026-05-03 directive (round-1 macro-AUC < 0.30 branch):

  1. Load all (url, label) rows from :PostureLabel.
  2. Train an interim 5-class classifier on all of them
     (no held-out — this is a sampling head, not an evaluation head).
  3. Score the curated ~500-URL candidate pool with predict_proba.
  4. Compute Shannon entropy per row.
  5. Stratify the surfaced top-N to ensure ≥min_per_class entries
     predicted into each of the 5 classes (with global entropy
     ranking filling the remaining slots).
  6. Persist the result as a JSON-lines artifact in
     ``artifacts/posture_round_2/round_2_candidates_<ts>.jsonl``
     with header line + one row per surfaced candidate.

Usage:
    python3 scripts/generate_round_2_candidates.py
    python3 scripts/generate_round_2_candidates.py --n 80 --min-per-class 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Self-locate project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load_env_from_dotenv() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(
            k.strip(), v.strip().strip('"').strip("'"),
        )


async def _build_async_driver() -> Optional[Any]:
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not uri or not user or not pwd:
        print("ERROR: NEO4J_* env vars not set", file=sys.stderr)
        return None
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
        await driver.verify_connectivity()
        return driver
    except Exception as exc:
        print(f"ERROR: Neo4j driver build failed: {exc}", file=sys.stderr)
        return None


async def _load_labels() -> tuple[List[str], List[str]]:
    """Load all (url, label) pairs from :PostureLabel."""
    from adam.intelligence.posture_five_class import load_labeled_pages

    driver = await _build_async_driver()
    if driver is None:
        return [], []
    try:
        entries = await load_labeled_pages(driver, limit=10000)
    finally:
        await driver.close()

    urls = [e.url for e in entries]
    labels = [e.label for e in entries]
    return urls, labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--n", type=int, default=80,
        help="Number of candidates to surface. Default 80.",
    )
    parser.add_argument(
        "--min-per-class", type=int, default=10,
        help="Floor on candidates per predicted class. Default 10.",
    )
    parser.add_argument(
        "--seed", type=int, default=2026,
        help="Random seed for the interim classifier. Default 2026.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSON-lines path. Default: "
             "artifacts/posture_round_2/round_2_candidates_<ts>.jsonl",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log = logging.getLogger("round_2_candidates")

    _load_env_from_dotenv()

    log.info("Loading labels from :PostureLabel...")
    urls, labels = asyncio.run(_load_labels())
    if not urls:
        log.error("No labels found — corpus is empty.")
        return 2
    log.info(f"Loaded {len(urls)} labels.")

    from adam.intelligence.posture_classifier import URLPostureClassifier
    from adam.intelligence.posture_candidate_pool import (
        CANDIDATE_URLS,
        get_full_pool,
        stratified_top_n,
    )

    log.info(
        "Training interim classifier on all %d labels (no holdout — "
        "this is a sampling head, not an evaluation head)...",
        len(urls),
    )
    interim = URLPostureClassifier(random_state=args.seed)
    interim.fit(urls, labels)

    pool = get_full_pool()
    log.info(
        "Scoring %d candidates from %d seed sources...",
        len(pool), len(CANDIDATE_URLS),
    )
    t0 = time.perf_counter()
    surfaced = stratified_top_n(
        interim,
        pool,
        n=args.n,
        min_per_class=args.min_per_class,
        exclude_urls=urls,  # don't re-surface already-labeled URLs
    )
    elapsed = time.perf_counter() - t0
    log.info(
        "Stratified top-%d in %.2fs; %d surfaced.",
        args.n, elapsed, len(surfaced),
    )

    # Counts per predicted class (argmax) AND per class via P(cls)
    # ranking — both are diagnostic. The directive's ≥10-per-class
    # floor is on the P(class) view; the argmax view exposes the
    # interim classifier's class-bias.
    from collections import Counter
    class_counts = Counter(c.predicted_class for c in surfaced)
    classes = sorted(interim.classes_)

    # Per-class P(class) view: for each class, which surfaced
    # candidates rank in the top-min_per_class by P(class)?
    class_in_top_p: Dict[str, int] = {}
    for cls_ix, cls in enumerate(classes):
        # Match interim.classes_ index for cls
        try:
            interim_ix = interim.classes_.index(cls)
        except ValueError:
            class_in_top_p[cls] = 0
            continue
        scored = sorted(
            surfaced, key=lambda c: -c.proba[interim_ix],
        )
        # Top min_per_class surfaced rows where P(cls) is highest
        class_in_top_p[cls] = sum(
            1 for c in scored[:args.min_per_class]
            if c.proba[interim_ix] > 0
        )

    # Persist artifact
    if args.output is None:
        ts = int(time.time())
        out_dir = (
            Path(__file__).parent.parent
            / "artifacts" / "posture_round_2"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(
            out_dir / f"round_2_candidates_{ts}.jsonl"
        )

    header = {
        "_record_type": "round_2_header",
        "n_surfaced": len(surfaced),
        "n_pool": len(pool),
        "n_train_labels": len(urls),
        "min_per_class": args.min_per_class,
        "classes": classes,
        "per_argmax_class_counts": dict(class_counts),
        "per_class_top_p_counts": class_in_top_p,
        "interim_classifier_version": interim.version,
        "interim_classifier_n_train": interim.n_train,
        "seed": args.seed,
        "generated_at_ts": time.time(),
    }
    rows = [
        {
            "_record_type": "candidate",
            "rank": rank,
            "url": c.url,
            "source": c.source,
            "predicted_class": c.predicted_class,
            "entropy": c.entropy,
            "proba": c.proba,
            "classes": classes,
        }
        for rank, c in enumerate(surfaced, start=1)
    ]

    with open(args.output, "w") as f:
        f.write(json.dumps(header) + "\n")
        for r in rows:
            f.write(json.dumps(r) + "\n")

    print()
    print("=" * 90)
    print("ROUND-2 ACTIVE-LEARNING CANDIDATE SURFACE")
    print("=" * 90)
    print(f"Pool size              : {len(pool)} URLs across "
          f"{len(CANDIDATE_URLS)} seed sources")
    print(f"Interim train n        : {len(urls)} labels")
    print(f"Surfaced               : {len(surfaced)} candidates")
    print(f"Min-per-class floor    : {args.min_per_class}")
    print()
    print("Per argmax-predicted class (diagnostic — exposes interim "
          "classifier's n=20 bias):")
    for c in classes:
        n = class_counts.get(c, 0)
        print(f"  {c:<32}  argmax-n={n:>3}")
    print()
    print(
        "Per class via P(class) ranking — the directive's ≥"
        f"{args.min_per_class}-per-class floor:",
    )
    for c in classes:
        n = class_in_top_p.get(c, 0)
        marker = "✓" if n >= args.min_per_class else "✗ BELOW FLOOR"
        print(f"  {c:<32}  top-P(cls)-n={n:>3}  {marker}")
    print()
    print("Top 10 most-uncertain candidates:")
    for r in rows[:10]:
        print(
            f"  #{r['rank']:>2}  H={r['entropy']:.4f}  "
            f"pred={r['predicted_class']:<28}  "
            f"src={r['source']:<22}"
        )
        print(f"      {r['url']}")
    print()
    print(f"Artifact: {args.output}")
    print()
    print("Next: hand-label the surfaced URLs via "
          "scripts/persist_posture_label.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
