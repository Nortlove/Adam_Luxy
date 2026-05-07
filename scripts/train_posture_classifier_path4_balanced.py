#!/usr/bin/env python3
"""G1.path4 — train URLPostureClassifier with class_weight='balanced'
against the existing audit-tracked corpus CSV.

Loads `audits/url_resolution_1777847380/training_corpus.csv` (n=100,
tracked at commit ef44990), trains the URLPostureClassifier with
class_weight="balanced" (the new default introduced in this slice's
fit() amendment), and persists the resulting checkpoint at
`artifacts/posture_classifier/posture_classifier_n100_balanced_<ts>.jsonl`.

Per directive Path 4 discipline:
  - NO corpus expansion (uses the existing 100-row CSV as-is, even
    rows flagged REPLACE in the audit; URL tokens still drive the
    classifier, and the audit's REPLACE-flag is for held-out fixture
    integrity, not training-set integrity)
  - NO architecture change beyond class_weight
  - NO held-out fixture rotation (separate slice if needed)

Usage:
    python3 scripts/train_posture_classifier_path4_balanced.py
    python3 scripts/train_posture_classifier_path4_balanced.py \\
        --corpus audits/url_resolution_1777847380/training_corpus.csv \\
        --artifact-dir artifacts/posture_classifier/
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Self-locate project root.
sys.path.insert(0, str(Path(__file__).parent.parent))


def _load_corpus_csv(path: Path) -> Tuple[List[str], List[str]]:
    """Load (urls, labels) from the audit-tracked training corpus CSV.

    Schema (per ef44990): url, label, labeler, labeled_at_ts,
    http_status, http_error, final_url, n_redirects, saas_interior,
    synthetic_patterns, recommendation, recommendation_reason.

    All rows kept regardless of recommendation status (see slice
    discipline: NO corpus expansion / contraction)."""
    urls: List[str] = []
    labels: List[str] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = (row.get("url") or "").strip()
            lbl = (row.get("label") or "").strip()
            if u and lbl:
                urls.append(u)
                labels.append(lbl)
    return urls, labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--corpus", type=str,
        default="audits/url_resolution_1777847380/training_corpus.csv",
        help="Path to training-corpus CSV. Default: audit-tracked n=100.",
    )
    parser.add_argument(
        "--artifact-dir", type=str,
        default="artifacts/posture_classifier",
        help="Output directory for the trained checkpoint.",
    )
    parser.add_argument(
        "--seed", type=int, default=2026,
        help="Random seed for determinism. Default 2026.",
    )
    parser.add_argument(
        "--class-weight", type=str, default="balanced",
        choices=["balanced", "none"],
        help="class_weight regime. Default 'balanced'. 'none' = uniform.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log = logging.getLogger("posture_path4_train")

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        log.error("corpus CSV not found: %s", corpus_path)
        return 2

    urls, labels = _load_corpus_csv(corpus_path)
    log.info("loaded %d (url, label) rows from %s", len(urls), corpus_path)
    if len(urls) < 2:
        log.error("Need n >= 2; got n=%d", len(urls))
        return 3

    from collections import Counter
    counts = Counter(labels)
    log.info("per-class label counts: %s", dict(counts))

    cw = "balanced" if args.class_weight == "balanced" else None
    log.info("training URLPostureClassifier (class_weight=%r, seed=%d)",
             cw, args.seed)

    from adam.intelligence.posture_classifier import (
        URLPostureClassifier,
        persist_classifier_artifact,
    )

    clf = URLPostureClassifier(random_state=args.seed)
    t0 = time.perf_counter()
    clf.fit(urls, labels, class_weight=cw)
    elapsed = time.perf_counter() - t0
    log.info("fit complete in %.3fs", elapsed)

    os.makedirs(args.artifact_dir, exist_ok=True)
    ts = int(time.time())
    suffix = "balanced" if cw == "balanced" else "uniform"
    artifact_path = Path(args.artifact_dir) / (
        f"posture_classifier_n{len(urls)}_{suffix}_{ts}.jsonl"
    )

    eval_summary = {
        "training_corpus": str(corpus_path),
        "n_train": len(urls),
        "class_weight": cw,
        "per_class_counts": dict(counts),
        "trained_at_ts": time.time(),
        "slice_id": "G1.path4",
    }
    persist_classifier_artifact(clf, str(artifact_path),
                                eval_summary=eval_summary)
    log.info("persisted: %s", artifact_path)
    print(str(artifact_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
