"""Pin scripts/run_policy_gate.py — the CI/CD-invocable policy gate.

Audit §6 follow-up: ope.policy_gate had no CLI invocation surface.
This file pins the new ``scripts/run_policy_gate.py`` runner's
exit-code contract:

    Exit 0 → policy_gate returned passed=True
    Exit 1 → policy_gate returned passed=False
    Exit 2 → input error (missing file, malformed JSON, missing fields)

The gate math itself (handoff §4.4 criterion) is pinned by tests for
adam.intelligence.ope; this file pins ONLY the I/O wrapper.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure scripts/ is importable in the test's path
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# Import the script as a module so we can call run_gate() without a subprocess.
import run_policy_gate  # noqa: E402  -- after sys.path manipulation


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _write_dr(tmp_path: Path, name: str, **fields) -> Path:
    """Write a minimally-valid DR estimate JSON to tmp_path."""
    payload = {
        "estimator": "DR",
        "point_estimate": fields.get("point_estimate", 0.05),
        "variance": fields.get("variance", 1e-6),
        "std_error": fields.get("std_error", 1e-3),
        "ci_lower": fields.get("ci_lower", 0.045),
        "ci_upper": fields.get("ci_upper", 0.055),
        "n_samples": fields.get("n_samples", 1000),
        "n_excluded": fields.get("n_excluded", 0),
    }
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


# -----------------------------------------------------------------------------
# (a) Pass / fail / input-error exit codes
# -----------------------------------------------------------------------------


def test_pass_exits_zero_via_run_gate(tmp_path):
    """Candidate strictly better than current → exit 0."""
    candidate = _write_dr(
        tmp_path, "candidate.json",
        point_estimate=0.060, ci_lower=0.058,
    )
    current = _write_dr(
        tmp_path, "current.json",
        point_estimate=0.050, ci_lower=0.045,
    )
    code = run_policy_gate.run_gate(candidate, current, quiet=True)
    assert code == 0


def test_candidate_below_current_fails_exits_one(tmp_path):
    """Candidate point < current point → exit 1."""
    candidate = _write_dr(
        tmp_path, "candidate.json",
        point_estimate=0.040, ci_lower=0.035,
    )
    current = _write_dr(
        tmp_path, "current.json",
        point_estimate=0.050, ci_lower=0.045,
    )
    code = run_policy_gate.run_gate(candidate, current, quiet=True)
    assert code == 1


def test_candidate_ci_lower_not_above_current_fails_exits_one(tmp_path):
    """Even if candidate point ≥ current point, ci_lower must EXCEED
    current point. Equality fails (handoff §4.4 strict gt)."""
    candidate = _write_dr(
        tmp_path, "candidate.json",
        point_estimate=0.060, ci_lower=0.050,  # equals current point
    )
    current = _write_dr(
        tmp_path, "current.json",
        point_estimate=0.050, ci_lower=0.045,
    )
    code = run_policy_gate.run_gate(candidate, current, quiet=True)
    assert code == 1


# -----------------------------------------------------------------------------
# (a) Input error → exit 2
# -----------------------------------------------------------------------------


def test_missing_file_exits_two(tmp_path):
    candidate = tmp_path / "does_not_exist.json"
    current = _write_dr(tmp_path, "current.json")
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.run_gate(candidate, current, quiet=True)
    assert exc_info.value.code == 2


def test_malformed_json_exits_two(tmp_path):
    candidate = tmp_path / "candidate.json"
    candidate.write_text("not valid json {{{")
    current = _write_dr(tmp_path, "current.json")
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.run_gate(candidate, current, quiet=True)
    assert exc_info.value.code == 2


def test_missing_required_field_exits_two(tmp_path):
    """A DR JSON without 'point_estimate' or 'ci_lower' is rejected."""
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({"estimator": "DR", "ci_lower": 0.05}))
    current = _write_dr(tmp_path, "current.json")
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.run_gate(candidate, current, quiet=True)
    assert exc_info.value.code == 2


def test_non_numeric_required_field_exits_two(tmp_path):
    """A required field that's not numeric is rejected."""
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({
        "estimator": "DR",
        "point_estimate": "lots",
        "ci_lower": 0.05,
    }))
    current = _write_dr(tmp_path, "current.json")
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.run_gate(candidate, current, quiet=True)
    assert exc_info.value.code == 2


def test_top_level_not_object_exits_two(tmp_path):
    """A JSON list at top level is rejected."""
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps([1, 2, 3]))
    current = _write_dr(tmp_path, "current.json")
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.run_gate(candidate, current, quiet=True)
    assert exc_info.value.code == 2


# -----------------------------------------------------------------------------
# (b) main() argparse path
# -----------------------------------------------------------------------------


def test_main_pass_exits_zero(tmp_path, capsys):
    """End-to-end: argparse → run_gate → SystemExit(0)."""
    candidate = _write_dr(
        tmp_path, "candidate.json",
        point_estimate=0.060, ci_lower=0.058,
    )
    current = _write_dr(
        tmp_path, "current.json",
        point_estimate=0.050, ci_lower=0.045,
    )
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.main([
            "--candidate-dr", str(candidate),
            "--current-dr", str(current),
        ])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "PASS" in captured.out


def test_main_quiet_suppresses_output(tmp_path, capsys):
    """--quiet → no stdout."""
    candidate = _write_dr(
        tmp_path, "candidate.json",
        point_estimate=0.060, ci_lower=0.058,
    )
    current = _write_dr(
        tmp_path, "current.json",
        point_estimate=0.050, ci_lower=0.045,
    )
    with pytest.raises(SystemExit) as exc_info:
        run_policy_gate.main([
            "--candidate-dr", str(candidate),
            "--current-dr", str(current),
            "--quiet",
        ])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
