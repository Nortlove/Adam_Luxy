#!/bin/bash
# =============================================================================
# Resume session script — gets a fresh Claude Code session back to the
# state at the end of session 2026-05-02 EVE (criterion (ii) REOPENED:
# LOOCV gate retired, held-out gate live, round-3 diversification surfaced).
#
# Usage:
#     bash scripts/resume_session.sh
#
# Or in Cursor's chat:
#     Read the output of `bash scripts/resume_session.sh`, then read
#     the named handoff file, then wait for my direction.
# =============================================================================

set -e

EXPECTED_BRANCH="feature/hmt-dashboard"
CORRECTION_MEMO="docs/CRITERION_II_STATUS_CORRECTION_2026_05_02.md"
ROUND_3_ARTIFACT="artifacts/posture_round_3/round_3_diversification_candidates.jsonl"
HELDOUT_SCRIPT="scripts/heldout_eval_posture_classifier.py"

echo "================================================================"
echo "ADAM platform — session resume brief"
echo "================================================================"
echo

echo "Repo state:"
ACTUAL_HEAD=$(git rev-parse --short HEAD)
ACTUAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "  branch         : $ACTUAL_BRANCH (expected: $EXPECTED_BRANCH)"
echo "  HEAD           : $ACTUAL_HEAD"
echo

echo "Last 5 commits:"
git log -5 --oneline
echo

echo "Round-3 diversification candidates (80 URLs surfaced for labeling):"
if [ -f "$ROUND_3_ARTIFACT" ]; then
    echo "  ✓ $ROUND_3_ARTIFACT ($(wc -c < "$ROUND_3_ARTIFACT") bytes)"
    echo "  Header:"
    head -1 "$ROUND_3_ARTIFACT" | python3 -c "import sys, json; h = json.loads(sys.stdin.read()); print(f'    n_surfaced={h[\"n_surfaced\"]}'); print(f'    per_class_target_counts: {h[\"per_class_target_counts\"]}')"
else
    echo "  ✗ MISSING: $ROUND_3_ARTIFACT"
fi
echo

echo "Three hard-stop criteria for v3 transition:"
echo "  (i)   Phase 9 sim                ✓ closed at 14f3d9f"
echo "  (ii)  5-class posture head       REOPENED (held-out gate live)"
echo "          - LOOCV n=100 macro-AUC = 0.9465 (DIAGNOSTIC ONLY — retired)"
echo "          - held-out n=50 macro-AUC = 0.7980, top-1 = 0.22  ✗ FAIL"
echo "          - new gate: held-out macro-AUC ≥ 0.50 AND top-1 ≥ 0.40"
echo "          - status memo: $CORRECTION_MEMO"
echo "          - 80 round-3 diversification candidates surfaced"
echo "  (iii) Section 6 cadences         ✓ closed at 53253c8"
echo

echo "Live gate check (current persisted classifier):"
if [ -f "$HELDOUT_SCRIPT" ]; then
    GATE_OUT=$(python3 "$HELDOUT_SCRIPT" 2>/dev/null | grep -E "Macro-AUC|Top-1 accuracy|Gate decision" || true)
    if [ -n "$GATE_OUT" ]; then
        echo "$GATE_OUT" | sed 's/^/  /'
    else
        echo "  (no classifier artifact yet — train one first)"
    fi
else
    echo "  ✗ MISSING: $HELDOUT_SCRIPT"
fi
echo

echo "Posture suite check:"
python3 -m pytest tests/unit/test_posture_candidate_pool.py tests/unit/test_posture_active_learning.py tests/unit/test_posture_five_class.py -q 2>&1 | tail -3
echo

echo "================================================================"
echo "FOR THE NEXT CLAUDE CODE SESSION — READ IN ORDER:"
echo "================================================================"
echo
echo "1. Criterion-(ii) status correction memo (audit trail):"
echo "   $CORRECTION_MEMO"
echo
echo "2. The directive (ONLY roadmap):"
echo "   docs/CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md"
echo
echo "3. Prior session handoffs (arc context):"
echo "   ~/.claude/projects/-Users-chrisnocera-Sites-adam-platform/memory/session_2026_05_02_wrap_out_criterion_ii_round_2_ready.md"
echo "   ~/.claude/projects/-Users-chrisnocera-Sites-adam-platform/memory/session_2026_05_02_audit_arc_1_2_3_marathon.md"
echo
echo "Pending operator action: hand-label the 80 round-3 candidates over"
echo "2-3 days via scripts/persist_posture_label.py, then:"
echo "  1) re-train: python3 scripts/train_and_evaluate_posture_classifier.py"
echo "  2) gate:    python3 $HELDOUT_SCRIPT"
echo "  Both must pass: macro-AUC ≥ 0.50 AND top-1 ≥ 0.40."
echo
echo "Do NOT start v3 Phase 1 work, construct annotation, frontend"
echo "Slice 11, policy_gate, or Phase 7 partner surface until the"
echo "held-out gate clears."
echo "================================================================"
