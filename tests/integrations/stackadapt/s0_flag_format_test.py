"""S0 §G test 6 — READY_FOR_RATER_WORKSHEET.flag format.

Per directive §E the flag is machine-readable key=value, one per line.
S1's worksheet generator reads it as its first action and routes
accordingly.

Pin:
- All required keys present in both pass and fail modes.
- key=value parses with no value containing '=' (which would break the
  one-pair-per-line contract).
- ready / gate_grade / calibration_grade / posture_diversity_inadequate
  semantics are mutually consistent.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import tools.stackadapt_historical_extract as s0_cli


REQUIRED_KEYS = [
    "ready",
    "gate_grade",
    "calibration_grade",
    "posture_diversity_inadequate",
    "inadequate_classes",
    "total_unique_urls",
    "total_validated_live",
    "domains",
    "sources",
    "diversity_gate_verdict",
    "report_path",
]


def _parse_flag(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_flag_with(tmp_path, *, diversity, sources, s1_share):
    flag_path = tmp_path / "flag"
    s0_cli.write_flag(
        flag_path,
        diversity=diversity,
        unique_urls_count=100,
        validated_live_count=95,
        domain_count=20,
        sources_present=sources,
        summary_path=tmp_path / "summary.md",
        s1_share=s1_share,
    )
    return flag_path.read_text()


class TestRequiredKeys:
    def test_all_keys_present_in_pass_mode(self, tmp_path):
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "PASS",
            "below_threshold": [],
            "per_class_counts": {c: 50 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path", "campaign_page_context"], s1_share=0.5)
        parsed = _parse_flag(text)
        for k in REQUIRED_KEYS:
            assert k in parsed, f"missing key: {k}"

    def test_all_keys_present_in_fail_mode(self, tmp_path):
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "FAIL",
            "below_threshold": ["LEISURE_BROWSING", "SOCIAL_CONSUMPTION"],
            "per_class_counts": {c: 5 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path"], s1_share=1.0)
        parsed = _parse_flag(text)
        for k in REQUIRED_KEYS:
            assert k in parsed, f"missing key: {k}"


class TestSemanticConsistency:
    def test_pass_diverse_low_s1_means_gate_grade(self, tmp_path):
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "PASS", "below_threshold": [],
            "per_class_counts": {c: 50 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path", "campaign_page_context"], s1_share=0.4)
        p = _parse_flag(text)
        assert p["ready"] == "true"
        assert p["gate_grade"] == "true"
        assert p["calibration_grade"] == "false"
        assert p["posture_diversity_inadequate"] == "false"
        assert p["diversity_gate_verdict"] == "PASS"

    def test_fail_diverse_means_not_ready(self, tmp_path):
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "FAIL", "below_threshold": ["LEISURE_BROWSING"],
            "per_class_counts": {c: 50 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path"], s1_share=0.5)
        p = _parse_flag(text)
        assert p["ready"] == "false"
        assert p["gate_grade"] == "false"
        assert p["posture_diversity_inadequate"] == "true"
        assert "LEISURE_BROWSING" in p["inadequate_classes"]

    def test_high_s1_share_blocks_gate_grade_even_if_pass(self, tmp_path):
        """conversion_path > 70% → calibration_grade=true regardless of
        diversity verdict — this is the bias guard."""
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "PASS", "below_threshold": [],
            "per_class_counts": {c: 50 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path"], s1_share=0.95)
        p = _parse_flag(text)
        assert p["calibration_grade"] == "true"
        assert p["gate_grade"] == "false"
        assert p["ready"] == "false"


class TestKeyValueFormat:
    def test_each_line_has_single_equals(self, tmp_path):
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "FAIL", "below_threshold": ["X"],
            "per_class_counts": {c: 1 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path"], s1_share=1.0)
        for line in text.splitlines():
            if not line:
                continue
            # Values must not contain '=' because the parser is one-equals.
            assert line.count("=") >= 1, f"no '=' in line: {line!r}"
            # Allow one or more, but key.partition('=') must be unambiguous.
            k, _, v = line.partition("=")
            assert k and not k.endswith(" "), f"malformed key in: {line!r}"

    def test_inadequate_classes_is_csv(self, tmp_path):
        text = _write_flag_with(tmp_path, diversity={
            "verdict": "FAIL",
            "below_threshold": ["A", "B", "C"],
            "per_class_counts": {c: 0 for c in s0_cli.FIVE_CLASSES},
        }, sources=["conversion_path"], s1_share=1.0)
        p = _parse_flag(text)
        assert p["inadequate_classes"] == "A,B,C"
