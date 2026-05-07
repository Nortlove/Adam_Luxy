#!/usr/bin/env python3
"""G1.path4 — held-out evaluation wrapper that emits JSON deliverable.

Re-uses the existing held-out-eval logic (HELDOUT_URLS fixture +
per-class one-vs-rest AUC + bootstrap CI + top-1 + confusion matrix)
but writes the result as a single JSON file at
`artifacts/evaluation/posture_balanced_<ts>.json` per the slice spec.

Per directive Path 4 discipline:
  - Held-out fixture used AS-IS (apples-to-apples comparison vs
    the prior unbalanced-checkpoint evaluation)
  - NO fixture rotation
  - Compares to prior unbalanced-checkpoint metrics inline
    (macro-AUC 0.7980, top-1 0.22, 49/50 → INFORMATION_FORAGING)

Usage:
    python3 scripts/heldout_eval_posture_path4_to_json.py \\
        --artifact artifacts/posture_classifier/posture_classifier_n100_balanced_<ts>.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict

# Self-locate project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


# Gate criteria per directive §G1 + EVE 2026-05-02 reopening.
GATE_MACRO_AUC_MIN = 0.50
GATE_TOP1_ACC_MIN = 0.40

# Prior-checkpoint metrics for inline comparison (session #002 EVE).
PRIOR_CHECKPOINT = {
    "artifact": "artifacts/posture_classifier/posture_classifier_n100_1777759342.jsonl",
    "macro_auc": 0.7980,
    "top_1": 0.22,
    "class_collapse_note": "49/50 predictions collapsed to INFORMATION_FORAGING",
    "class_weight": None,  # uniform (the prior regime)
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--artifact", type=str, required=True,
        help="Path to the balanced-checkpoint JSONL artifact.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSON path. Default: "
             "artifacts/evaluation/posture_balanced_<ts>.json",
    )
    parser.add_argument(
        "--bootstrap-n", type=int, default=1000,
        help="Bootstrap samples for macro-AUC 95%% CI. Default 1000.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log = logging.getLogger("posture_path4_eval")

    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        log.error("artifact not found: %s", artifact_path)
        return 2

    from adam.intelligence.posture_classifier import (
        URLPostureClassifier,
        _bootstrap_macro_auc_ci,
        _per_class_one_vs_rest_auc,
        load_classifier_artifact,
    )
    from scripts.heldout_eval_posture_classifier import HELDOUT_URLS

    clf: URLPostureClassifier = load_classifier_artifact(str(artifact_path))
    classes = list(clf.classes_)
    urls = [u for u, _, _ in HELDOUT_URLS]
    y_true = [lbl for _, lbl, _ in HELDOUT_URLS]
    dist = Counter(y_true)

    log.info("scoring %d held-out URLs against %d classes",
             len(urls), len(classes))
    proba = clf.predict_proba(urls)
    if proba.shape != (len(urls), len(classes)):
        log.error("predict_proba shape %s != expected (%d, %d)",
                  proba.shape, len(urls), len(classes))
        return 2

    per_class = _per_class_one_vs_rest_auc(y_true, proba, classes)
    macro = float(np.mean(list(per_class.values())))
    ci_lo, ci_hi = _bootstrap_macro_auc_ci(
        y_true, proba, classes,
        n_bootstrap=int(args.bootstrap_n),
        seed=2026,
    )

    pred = [classes[int(np.argmax(p))] for p in proba]
    n_correct = sum(1 for a, b in zip(pred, y_true) if a == b)
    top1 = n_correct / len(y_true) if y_true else 0.0

    confusion: Dict[str, Dict[str, int]] = {c: {c2: 0 for c2 in classes}
                                             for c in classes}
    for t, p in zip(y_true, pred):
        confusion[t][p] += 1

    pred_counter = Counter(pred)
    auc_pass = macro >= GATE_MACRO_AUC_MIN
    top1_pass = top1 >= GATE_TOP1_ACC_MIN
    if auc_pass and top1_pass:
        gate_status = "pass"
    elif auc_pass or top1_pass:
        gate_status = "partial"
    else:
        gate_status = "fail"

    out: Dict[str, Any] = {
        "timestamp": time.time(),
        "slice_id": "G1.path4",
        "training_corpus": "audits/url_resolution_1777847380/training_corpus.csv",
        "checkpoint": str(artifact_path),
        "held_out_fixture": "scripts/heldout_eval_posture_classifier.py:HELDOUT_URLS",
        "n_heldout": len(urls),
        "macro_auc": macro,
        "macro_auc_ci_low": ci_lo,
        "macro_auc_ci_high": ci_hi,
        "top_1": top1,
        "top_1_n_correct": n_correct,
        "per_class_auc": {c: per_class[c] for c in classes},
        "per_class_true_counts": dict(dist),
        "per_class_pred_counts": dict(pred_counter),
        "confusion_matrix": confusion,
        "gate_thresholds": {
            "macro_auc_min": GATE_MACRO_AUC_MIN,
            "top_1_min": GATE_TOP1_ACC_MIN,
        },
        "g1_gate_status": gate_status,
        "auc_pass": auc_pass,
        "top1_pass": top1_pass,
        "comparison_to_prior_checkpoint": {
            "prior": PRIOR_CHECKPOINT,
            "current": {
                "artifact": str(artifact_path),
                "macro_auc": macro,
                "top_1": top1,
                "class_weight": "balanced",
            },
            "macro_auc_delta": macro - PRIOR_CHECKPOINT["macro_auc"],
            "top_1_delta": top1 - PRIOR_CHECKPOINT["top_1"],
            "class_collapse_resolved": (
                # Heuristic: resolved if no single class dominates
                # >= 60% of predictions (the prior was 49/50 = 98%).
                max(pred_counter.values()) / len(pred) < 0.60
                if pred else False
            ),
            "modal_predicted_class_share": (
                max(pred_counter.values()) / len(pred) if pred else 0.0
            ),
        },
    }

    if args.output is None:
        os.makedirs("artifacts/evaluation", exist_ok=True)
        ts = int(time.time())
        out_path = Path("artifacts/evaluation") / (
            f"posture_balanced_{ts}.json"
        )
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    log.info("eval JSON written: %s", out_path)

    print()
    print("=" * 80)
    print(f"G1.path4 HELD-OUT EVAL — {artifact_path.name}")
    print("=" * 80)
    print(f"macro_auc:       {macro:.4f}  (gate: ≥ {GATE_MACRO_AUC_MIN:.2f}  "
          f"{'✓ PASS' if auc_pass else '✗ FAIL'})")
    print(f"top_1:           {top1:.4f}  (gate: ≥ {GATE_TOP1_ACC_MIN:.2f}  "
          f"{'✓ PASS' if top1_pass else '✗ FAIL'})")
    print(f"bootstrap CI:    [{ci_lo:.4f}, {ci_hi:.4f}]")
    print(f"G1 GATE:         {gate_status.upper()}")
    print()
    print(f"prior macro_auc: {PRIOR_CHECKPOINT['macro_auc']:.4f}  "
          f"(Δ {macro - PRIOR_CHECKPOINT['macro_auc']:+.4f})")
    print(f"prior top_1:     {PRIOR_CHECKPOINT['top_1']:.4f}  "
          f"(Δ {top1 - PRIOR_CHECKPOINT['top_1']:+.4f})")
    print(f"modal pred share: "
          f"{out['comparison_to_prior_checkpoint']['modal_predicted_class_share']:.2f}  "
          f"(prior 0.98)")
    print()
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
