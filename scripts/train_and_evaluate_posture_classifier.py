#!/usr/bin/env python3
"""Train + LOOCV evaluate the 5-class posture classifier on all
labels persisted in :PostureLabel.

Per the 2026-05-03 directive:
  * LOOCV given n=20.
  * One-vs-rest macro-AUC + per-class AUC.
  * Bootstrap 95% CI on macro-AUC.
  * If macro-AUC ≥ 0.30: persist classifier artifact + report
    ready-for-v3-transition.
  * If macro-AUC < 0.30: do NOT persist; defer to round-2
    candidate generation (separate script).

Usage:
    python3 scripts/train_and_evaluate_posture_classifier.py
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

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


async def _load_labels() -> Tuple[List[str], List[str]]:
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


def _format_summary(
    result, urls: List[str], labels: List[str],
) -> str:
    """Tabular summary."""
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append("5-CLASS POSTURE CLASSIFIER — LOOCV EVALUATION")
    lines.append("=" * 80)
    lines.append(f"n_samples:                {result.n_samples}")
    lines.append(f"n_classes:                {len(result.classes)}")
    lines.append(f"classes:                  {result.classes}")
    lines.append("")
    # Per-class breakdown of label counts.
    from collections import Counter
    counts = Counter(labels)
    lines.append("Per-class label counts:")
    for c in result.classes:
        lines.append(f"  {c:<32}  n={counts.get(c, 0)}")
    lines.append("")
    lines.append("Per-class one-vs-rest AUC:")
    for c, auc in sorted(
        result.per_class_auc.items(), key=lambda x: -x[1],
    ):
        lines.append(f"  {c:<32}  AUC={auc:.4f}")
    lines.append("")
    lines.append("Macro-averaged AUC:")
    lines.append(
        f"  point estimate            {result.macro_auc:.4f}"
    )
    lines.append(
        f"  bootstrap 95% CI          "
        f"[{result.macro_auc_bootstrap_ci_low:.4f}, "
        f"{result.macro_auc_bootstrap_ci_high:.4f}]"
    )
    lines.append(
        f"  bootstrap n               {result.bootstrap_n}"
    )
    lines.append("")
    lines.append(f"Gate threshold:           0.30 (chance for 5-class = 0.20)")
    if result.macro_auc >= 0.30:
        lines.append("Gate decision:            ✓ PASS")
    else:
        lines.append(
            f"Gate decision:            ✗ BELOW THRESHOLD "
            f"(by {0.30 - result.macro_auc:.4f})"
        )
    lines.append("=" * 80)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--bootstrap-n", type=int, default=1000,
        help="Bootstrap iterations for macro-AUC CI. Default 1000.",
    )
    parser.add_argument(
        "--seed", type=int, default=2026,
        help="Random seed for determinism.",
    )
    parser.add_argument(
        "--artifact-dir", type=str, default=None,
        help="Where to persist the classifier on PASS. Default: "
             "artifacts/posture_classifier/",
    )
    parser.add_argument(
        "--gate-threshold", type=float, default=0.30,
        help="Macro-AUC gate threshold. Default 0.30.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log = logging.getLogger("posture_classifier_eval")

    _load_env_from_dotenv()

    # Load labels
    log.info("Loading labels from :PostureLabel...")
    urls, labels = asyncio.run(_load_labels())
    if not urls:
        log.error("No labels found — corpus is empty.")
        return 2

    log.info(f"Loaded {len(urls)} labels.")

    if len(urls) < 2:
        log.error("LOOCV requires n ≥ 2.")
        return 3

    # Train + evaluate
    from adam.intelligence.posture_classifier import (
        URLPostureClassifier,
        loo_cv_evaluate,
        persist_classifier_artifact,
    )

    log.info("Running LOOCV...")
    t0 = time.perf_counter()
    result = loo_cv_evaluate(
        urls, labels, bootstrap_n=args.bootstrap_n, seed=args.seed,
    )
    elapsed = time.perf_counter() - t0
    log.info(f"LOOCV complete in {elapsed:.2f}s.")

    summary = _format_summary(result, urls, labels)
    print()
    print(summary)
    print()

    # Branch
    if result.macro_auc >= args.gate_threshold:
        log.info(
            "Gate PASS — training final classifier on all %d labels "
            "and persisting artifact.", len(urls),
        )
        # Train final on all 20.
        final_clf = URLPostureClassifier(random_state=args.seed)
        final_clf.fit(urls, labels)

        # Persist
        if args.artifact_dir is None:
            args.artifact_dir = str(
                Path(__file__).parent.parent
                / "artifacts" / "posture_classifier"
            )
        os.makedirs(args.artifact_dir, exist_ok=True)
        ts = int(time.time())
        artifact_path = os.path.join(
            args.artifact_dir,
            f"posture_classifier_n{len(urls)}_{ts}.jsonl",
        )

        eval_summary = {
            "n_samples": result.n_samples,
            "macro_auc": result.macro_auc,
            "macro_auc_ci_low": result.macro_auc_bootstrap_ci_low,
            "macro_auc_ci_high": result.macro_auc_bootstrap_ci_high,
            "per_class_auc": dict(result.per_class_auc),
            "gate_threshold": args.gate_threshold,
            "evaluated_at_ts": time.time(),
        }
        persist_classifier_artifact(
            final_clf, artifact_path, eval_summary=eval_summary,
        )
        log.info("Artifact persisted: %s", artifact_path)

        print()
        print("=" * 80)
        print("CRITERION (ii) STATUS: ready-for-v3-transition")
        print("=" * 80)
        print(f"  classifier:    {final_clf.version}")
        print(f"  n_train:       {final_clf.n_train}")
        print(f"  artifact:      {artifact_path}")
        print(f"  macro-AUC:     {result.macro_auc:.4f} "
              f"(threshold {args.gate_threshold:.2f}; pass)")
        return 0

    # Below gate
    log.warning(
        "Gate BELOW THRESHOLD — macro-AUC %.4f < %.4f. "
        "Round 2 active-learning is the next step.",
        result.macro_auc, args.gate_threshold,
    )
    print()
    print("=" * 80)
    print("CRITERION (ii) STATUS: BELOW GATE — round 2 needed")
    print("=" * 80)
    print(f"  macro-AUC:     {result.macro_auc:.4f} "
          f"(threshold {args.gate_threshold:.2f})")
    print(f"  CI 95%:        [{result.macro_auc_bootstrap_ci_low:.4f}, "
          f"{result.macro_auc_bootstrap_ci_high:.4f}]")
    print()
    print("Next: run scripts/generate_round_2_candidates.py to surface "
          "80 most-uncertain candidates for labeling.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
