#!/bin/bash
# =============================================================================
# Resume session script — gets a fresh Claude Code session back to the
# state at the end of session 2026-05-02 PM (wrap-out criterion (ii)
# round-2 ready).
#
# Usage:
#     bash scripts/resume_session.sh
#
# Or in Cursor's chat:
#     Read the output of `bash scripts/resume_session.sh`, then read
#     the named handoff file, then wait for my direction.
# =============================================================================

set -e

EXPECTED_HEAD="8ad946a"
EXPECTED_BRANCH="feature/hmt-dashboard"
HANDOFF_FILE="/Users/chrisnocera/.claude/projects/-Users-chrisnocera-Sites-adam-platform/memory/session_2026_05_02_wrap_out_criterion_ii_round_2_ready.md"
ARTIFACT_FILE="artifacts/posture_round_2/round_2_candidates_1777757647.jsonl"

echo "================================================================"
echo "ADAM platform — session resume brief"
echo "================================================================"
echo

echo "Repo state:"
ACTUAL_HEAD=$(git rev-parse --short HEAD)
ACTUAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "  branch         : $ACTUAL_BRANCH (expected: $EXPECTED_BRANCH)"
echo "  HEAD           : $ACTUAL_HEAD (expected: $EXPECTED_HEAD)"
if [ "$ACTUAL_HEAD" != "$EXPECTED_HEAD" ] || [ "$ACTUAL_BRANCH" != "$EXPECTED_BRANCH" ]; then
    echo "  ⚠  WARNING: state has drifted from the expected resume point."
    echo "  If you intend to resume the 2026-05-02 PM handoff:"
    echo "    git checkout $EXPECTED_BRANCH"
    echo "    git checkout $EXPECTED_HEAD"
fi
echo

echo "Last 5 commits:"
git log -5 --oneline
echo

echo "Artifact (80 round-2 candidates surfaced for labeling):"
if [ -f "$ARTIFACT_FILE" ]; then
    echo "  ✓ $ARTIFACT_FILE ($(wc -c < "$ARTIFACT_FILE") bytes)"
    echo "  Header:"
    head -1 "$ARTIFACT_FILE" | python3 -c "import sys, json; h = json.loads(sys.stdin.read()); print(f'    n_surfaced={h[\"n_surfaced\"]}, n_pool={h[\"n_pool\"]}, classifier={h[\"interim_classifier_version\"]}'); print(f'    per_class_top_p_counts: {h[\"per_class_top_p_counts\"]}')"
else
    echo "  ✗ MISSING: $ARTIFACT_FILE"
    echo "    Re-generate: python3 scripts/generate_round_2_candidates.py"
fi
echo

echo "Three hard-stop criteria for v3 transition:"
echo "  (i)   Phase 9 sim                ✓ closed at 14f3d9f"
echo "  (ii)  5-class posture head       BELOW gate (round-2 surface ready)"
echo "          round-1 macro-AUC = 0.2580 < 0.30 (CI [0.0826, 0.4210])"
echo "          80 candidates persisted for hand-labeling"
echo "  (iii) Section 6 cadences         ✓ closed at 53253c8"
echo

echo "Posture suite check:"
python3 -m pytest tests/unit/test_posture_candidate_pool.py tests/unit/test_posture_active_learning.py tests/unit/test_posture_five_class.py -q 2>&1 | tail -3
echo

echo "================================================================"
echo "FOR THE NEXT CLAUDE CODE SESSION — READ IN ORDER:"
echo "================================================================"
echo
echo "1. The session handoff:"
echo "   $HANDOFF_FILE"
echo
echo "2. The directive (ONLY roadmap):"
echo "   docs/CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md"
echo
echo "3. The prior handoff (broader arc context):"
echo "   ~/.claude/projects/-Users-chrisnocera-Sites-adam-platform/memory/session_2026_05_02_audit_arc_1_2_3_marathon.md"
echo
echo "Pending operator decision: hand-label some/all of the 80 round-2"
echo "candidates via scripts/persist_posture_label.py, then re-run"
echo "scripts/train_and_evaluate_posture_classifier.py to check the gate."
echo
echo "Do NOT: start construct annotation, frontend Slice 11, policy_gate,"
echo "Phase 7 partner surface, or request more labels until round-2"
echo "surface is inspected."
echo "================================================================"
