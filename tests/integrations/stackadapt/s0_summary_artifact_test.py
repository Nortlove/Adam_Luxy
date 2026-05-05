"""S0 §G test 5 — summary artifact has all 7 required sections.

Per directive §D the summary `.md` must include sections in order with
the verbatim caveat block. These tests pin the section presence + the
caveat verbatim against silent regression.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.stackadapt_historical_extract as s0_cli


REQUIRED_SECTIONS = [
    "## 1. Source Distribution",
    "## 2. URL Validation",
    "## 3. Domain Distribution",
    "## 4. Coverage Gap",
    "## 5. Posture-Class Diversity Audit",
    "## 6. Diversity Gate Verdict",
    "## 7. Bias Caveat",
]


def _build_summary(tmp_path, *, raw_rows=None, unique_urls=None,
                    head_results=None, diversity=None):
    summary_path = tmp_path / "summary.md"
    s0_cli.write_summary(
        summary_path,
        raw_rows=raw_rows or [
            {"source": "conversion_path", "url": "https://luxyride.com/page-1",
             "publisher_domain": "foxnews.com", "impression_count": 10},
        ],
        unique_urls=unique_urls or {
            "https://luxyride.com/page-1": {
                "url": "https://luxyride.com/page-1",
                "domain": "luxyride.com",
                "sources": ["conversion_path"],
                "served_impression_total": 10,
                "row_count": 1,
                "validated_live": True,
                "head_status": 200,
                "failure_reason": None,
            },
        },
        head_results=head_results or {
            "https://luxyride.com/page-1": {
                "head_status": 200, "validated_live": True,
                "failure_reason": None,
            },
        },
        diversity=diversity or {
            "per_class_counts": {c: 6 for c in s0_cli.FIVE_CLASSES},
            "below_threshold": list(s0_cli.FIVE_CLASSES),
            "verdict": "FAIL",
            "verdict_reason": "under_threshold",
            "classifier_artifact": "/tmp/x",
            "classifier_classes": list(s0_cli.FIVE_CLASSES),
            "predicted_total": 30,
        },
        extraction_window_days=365,
        advertiser_id="122463",
        luxy_campaign_count=12,
    )
    return summary_path.read_text()


class TestSectionOrder:
    def test_all_seven_sections_present_in_order(self, tmp_path):
        summary = _build_summary(tmp_path)
        positions = [summary.find(s) for s in REQUIRED_SECTIONS]
        assert all(p > 0 for p in positions), (
            f"missing sections: {[s for s, p in zip(REQUIRED_SECTIONS, positions) if p < 0]}"
        )
        assert positions == sorted(positions), (
            "sections out of order"
        )


class TestCaveatVerbatim:
    """Pin Chris's binding amendment caveat as verbatim text."""

    def test_round_3_caveat_appears_verbatim(self, tmp_path):
        summary = _build_summary(tmp_path)
        # Match the load-bearing phrases of the caveat.
        for phrase in [
            "round-3-pre-rotation",
            "macro-AUC",
            "0.7980",
            "top-1 0.22",
            "49/50 cases collapsed",
            "INFORMATION_FORAGING",
            "conservative-for-purpose",
            "lower bounds for non-",
            "upper bound",
            "corpus-diversity gating, not posture-class assignment",
        ]:
            assert phrase in summary, f"caveat missing phrase: {phrase!r}"


class TestDiversityVerdictRendered:
    def test_pass_verdict_renders_pass(self, tmp_path):
        summary = _build_summary(tmp_path, diversity={
            "per_class_counts": {c: 100 for c in s0_cli.FIVE_CLASSES},
            "below_threshold": [],
            "verdict": "PASS",
            "verdict_reason": "all_classes_clear_minimum",
            "classifier_artifact": "/tmp/x",
            "classifier_classes": list(s0_cli.FIVE_CLASSES),
            "predicted_total": 500,
        })
        assert "**PASS**" in summary
        assert "all_classes_clear_minimum" in summary

    def test_fail_verdict_renders_fail_with_shortfall(self, tmp_path):
        diversity = {
            "per_class_counts": {
                "INFORMATION_FORAGING": 100, "TASK_COMPLETION": 100,
                "LEISURE_BROWSING": 5, "SOCIAL_CONSUMPTION": 100,
                "TRANSACTIONAL_COMPARISON": 100,
            },
            "below_threshold": ["LEISURE_BROWSING"],
            "verdict": "FAIL",
            "verdict_reason": "under_threshold",
            "classifier_artifact": "/tmp/x",
            "classifier_classes": list(s0_cli.FIVE_CLASSES),
            "predicted_total": 405,
        }
        summary = _build_summary(tmp_path, diversity=diversity)
        assert "**FAIL**" in summary
        assert "LEISURE_BROWSING" in summary
        assert "shortfall=25" in summary  # 30 - 5


class TestBiasCaveatRoutes:
    def test_high_source1_share_declares_calibration_grade(self, tmp_path):
        # All URLs are from conversion_path → 100% S1 share → calibration_grade
        unique = {
            f"https://luxyride.com/p{i}": {
                "url": f"https://luxyride.com/p{i}",
                "domain": "luxyride.com",
                "sources": ["conversion_path"],
                "served_impression_total": 1, "row_count": 1,
                "validated_live": True, "head_status": 200,
                "failure_reason": None,
            } for i in range(20)
        }
        summary = _build_summary(tmp_path, unique_urls=unique, raw_rows=[
            {"source": "conversion_path",
             "url": f"https://luxyride.com/p{i}",
             "publisher_domain": "foxnews.com", "impression_count": 1}
            for i in range(20)
        ])
        assert "calibration_grade=true" in summary
        assert "NOT sufficient to close Gate G1" in summary
