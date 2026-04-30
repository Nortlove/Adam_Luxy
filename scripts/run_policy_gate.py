#!/usr/bin/env python3
"""CI/CD policy-gate runner — applies handoff §4.4 to two DR estimates.

Per CODEBASE_AUDIT_2026_04_29.md §6: ``ope.policy_gate`` existed at
adam/intelligence/ope.py:412 but had NO caller — no CI/CD pipeline,
no script, no orchestrator. This CLI is the missing invocation
surface. A CI workflow (or Makefile, or scripts/release.sh) calls
this script with paths to the candidate-DR and current-DR JSON files
and gates merge/deploy on the exit code:

    Exit 0  → policy_gate.passed=True   (ship candidate)
    Exit 1  → policy_gate.passed=False  (block; candidate fails gate)
    Exit 2  → input error (missing/invalid JSON, unparseable DR)

The gate criterion is the handoff §4.4 verbatim rule:

    candidate_dr.point_estimate ≥ current_dr.point_estimate
        AND
    candidate_dr.ci_lower > current_dr.point_estimate

Both JSON files MUST contain the OPEEstimateResult-shaped fields
``point_estimate`` and ``ci_lower``. Whatever upstream stage
fits/scores the candidate writes that JSON; this script reads it and
gates. Decoupling fitting from gating keeps the gate pure — it can
be invoked from CI without the full ML stack.

Usage:
    python scripts/run_policy_gate.py \\
        --candidate-dr path/to/candidate_dr.json \\
        --current-dr   path/to/current_dr.json

The CLI also accepts ``--quiet`` to suppress stdout and emit only
the exit code, which CI systems often prefer for terse logs.

Example candidate_dr.json:
    {
      "estimator": "DR",
      "point_estimate": 0.0512,
      "variance": 0.000003,
      "std_error": 0.00173,
      "ci_lower": 0.04781,
      "ci_upper": 0.05459,
      "n_samples": 12450,
      "n_excluded": 0
    }

Discipline rule (B3-LUXY a/b/c/d):
    (a) The gate math IS adam.intelligence.ope.policy_gate. This
        script is the I/O wrapper, not a re-implementation.
    (b) Regression: see test_run_policy_gate_script.py
        (PASS exit 0, FAIL exit 1, missing file exit 2, malformed
        JSON exit 2, missing required fields exit 2).
    (c) calibration_pending=False — the gate criterion is the
        canonical §4.4 rule, not pilot-tuned.
    (d) Honest tag — the gate is intentionally strict: condition (2)
        is `>` not `>=` so a candidate that only ties the current
        policy's point estimate within noise FAILS the gate. This is
        the canonical handoff rule and must NOT be relaxed without
        an explicit handoff revision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


_REQUIRED_FIELDS = ("point_estimate", "ci_lower")


def _exit(code: int, message: str = "", quiet: bool = False) -> None:
    """Emit message (unless quiet) and exit with the given code.

    Wrapped so tests can monkey-patch sys.exit cleanly.
    """
    if message and not quiet:
        # Errors go to stderr; PASS / FAIL summary goes to stdout.
        stream = sys.stderr if code != 0 else sys.stdout
        print(message, file=stream)
    sys.exit(code)


def _load_dr_json(path: Path) -> Tuple[Dict[str, Any], str]:
    """Load and validate one DR estimate JSON file.

    Returns (data, '') on success. Returns ({}, error_message) on
    failure — caller decides exit code.
    """
    if not path.is_file():
        return {}, f"input not found: {path}"

    try:
        with path.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return {}, f"invalid JSON in {path}: {exc}"
    except OSError as exc:
        return {}, f"failed to read {path}: {exc}"

    if not isinstance(data, dict):
        return {}, f"{path}: top-level must be an object, got {type(data).__name__}"

    for field in _REQUIRED_FIELDS:
        if field not in data:
            return {}, f"{path}: missing required field '{field}'"
        try:
            float(data[field])
        except (TypeError, ValueError):
            return {}, (
                f"{path}: field '{field}' is not numeric: {data[field]!r}"
            )

    return data, ""


def _build_estimate(data: Dict[str, Any]) -> Any:
    """Build an OPEEstimateResult from the loaded JSON."""
    from adam.intelligence.ope import OPEEstimateResult

    return OPEEstimateResult(
        estimator=str(data.get("estimator", "DR")),
        point_estimate=float(data["point_estimate"]),
        variance=float(data.get("variance", 0.0)),
        std_error=float(data.get("std_error", 0.0)),
        ci_lower=float(data["ci_lower"]),
        ci_upper=float(data.get("ci_upper", 0.0)),
        n_samples=int(data.get("n_samples", 0)),
        n_excluded=int(data.get("n_excluded", 0)),
    )


def run_gate(
    candidate_path: Path,
    current_path: Path,
    quiet: bool = False,
) -> int:
    """Load both DR JSONs, run policy_gate, return the intended exit code.

    Pulled out as a function (vs. inline in main) so tests can call it
    directly without touching argparse or sys.exit.
    """
    candidate_data, err = _load_dr_json(candidate_path)
    if err:
        _exit(2, err, quiet=quiet)
    current_data, err = _load_dr_json(current_path)
    if err:
        _exit(2, err, quiet=quiet)

    from adam.intelligence.ope import policy_gate

    candidate_dr = _build_estimate(candidate_data)
    current_dr = _build_estimate(current_data)

    result = policy_gate(candidate_dr=candidate_dr, current_dr=current_dr)

    status = "PASS" if result.passed else "FAIL"
    summary = (
        f"[policy_gate] {status}: "
        f"candidate point={result.candidate_dr_point} ci_lower={result.candidate_dr_lower}, "
        f"current point={result.current_dr_point}\n"
        + "\n".join(f"  - {r}" for r in result.reasons)
    )

    if not quiet:
        print(summary)

    return 0 if result.passed else 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the handoff §4.4 OPE gate to two DR estimates. "
            "Exit 0 = PASS, exit 1 = FAIL, exit 2 = input error."
        ),
    )
    parser.add_argument(
        "--candidate-dr", required=True, type=Path,
        help="Path to candidate-policy DR estimate JSON",
    )
    parser.add_argument(
        "--current-dr", required=True, type=Path,
        help="Path to current-policy DR estimate JSON",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress stdout/stderr; only the exit code is emitted",
    )
    args = parser.parse_args(argv)

    code = run_gate(
        candidate_path=args.candidate_dr,
        current_path=args.current_dr,
        quiet=args.quiet,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
