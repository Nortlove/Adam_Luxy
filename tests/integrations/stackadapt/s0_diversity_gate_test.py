"""S0 §G test 4 — diversity-gate verdict logic.

Per binding amendment (Chris 2026-05-04). The gate predicts posture-class
membership for each unique URL via URLPostureClassifier and verdicts
PASS only if every one of the 5 canonical classes has ≥ 30 URLs.

The 30-URL minimum is parameterized (constant `DIVERSITY_GATE_PER_CLASS_MINIMUM`
in the CLI module) — these tests exercise both threshold values to make
sure the verdict logic respects the parameter, not a hardcoded 30.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import numpy as np
import pytest

import tools.stackadapt_historical_extract as s0_cli


FIVE = list(s0_cli.FIVE_CLASSES)


def _mock_classifier_with_distribution(class_to_count: dict, classes=None):
    """Build a fake URLPostureClassifier returning a hard-assigned proba
    matrix over the requested URLs. classes_ is FIVE by default."""
    classes = classes or FIVE
    clf = MagicMock()
    clf.classes_ = classes

    total_per_class = list(class_to_count.items())
    n_total = sum(c for _, c in total_per_class)

    def _proba(urls):
        # Build proba so that argmax assigns each URL to the class
        # planned by class_to_count, in order.
        plan = []
        for cls, n in total_per_class:
            plan.extend([cls] * n)
        if len(plan) < len(urls):
            plan += [classes[0]] * (len(urls) - len(plan))
        plan = plan[:len(urls)]
        proba = np.zeros((len(urls), len(classes)))
        for i, cls in enumerate(plan):
            j = classes.index(cls)
            proba[i, j] = 1.0
        return proba

    clf.predict_proba = _proba
    return clf


class TestVerdictPass:
    @pytest.mark.parametrize("threshold,counts,expected_verdict", [
        (30, {c: 30 for c in FIVE}, "PASS"),
        (30, {c: 31 for c in FIVE}, "PASS"),
        (10, {c: 10 for c in FIVE}, "PASS"),
    ])
    def test_pass_when_every_class_clears_threshold(
        self, threshold, counts, expected_verdict, monkeypatch,
    ):
        monkeypatch.setattr(
            s0_cli, "DIVERSITY_GATE_PER_CLASS_MINIMUM", threshold,
        )
        urls = [f"https://e.com/{c}/{i}"
                for c, n in counts.items() for i in range(n)]
        clf = _mock_classifier_with_distribution(counts)
        with patch(
            "adam.intelligence.posture_classifier.load_classifier_artifact",
            return_value=clf,
        ):
            result = s0_cli.run_diversity_audit(
                urls,
                classifier_artifact_path="/tmp/fake_artifact",
            )
        assert result["verdict"] == expected_verdict
        assert result["below_threshold"] == []


class TestVerdictFail:
    @pytest.mark.parametrize("threshold,counts,below", [
        (30, {"INFORMATION_FORAGING": 100, "TASK_COMPLETION": 100,
              "LEISURE_BROWSING": 5, "SOCIAL_CONSUMPTION": 100,
              "TRANSACTIONAL_COMPARISON": 100}, ["LEISURE_BROWSING"]),
        (30, {"INFORMATION_FORAGING": 200, "TASK_COMPLETION": 0,
              "LEISURE_BROWSING": 0, "SOCIAL_CONSUMPTION": 0,
              "TRANSACTIONAL_COMPARISON": 0},
         ["TASK_COMPLETION", "LEISURE_BROWSING", "SOCIAL_CONSUMPTION",
          "TRANSACTIONAL_COMPARISON"]),
        (50, {c: 49 for c in FIVE}, FIVE),
    ])
    def test_fail_when_any_class_below_threshold(
        self, threshold, counts, below, monkeypatch,
    ):
        monkeypatch.setattr(
            s0_cli, "DIVERSITY_GATE_PER_CLASS_MINIMUM", threshold,
        )
        urls = [f"https://e.com/{i}" for i in range(sum(counts.values()))]
        clf = _mock_classifier_with_distribution(counts)
        with patch(
            "adam.intelligence.posture_classifier.load_classifier_artifact",
            return_value=clf,
        ):
            result = s0_cli.run_diversity_audit(
                urls,
                classifier_artifact_path="/tmp/fake_artifact",
            )
        assert result["verdict"] == "FAIL"
        assert sorted(result["below_threshold"]) == sorted(below)


class TestEdgeCases:
    def test_empty_urls_returns_fail_no_urls(self):
        result = s0_cli.run_diversity_audit([])
        assert result["verdict"] == "FAIL"
        assert result["verdict_reason"] == "no_urls"

    def test_no_classifier_artifact_returns_fail_named_reason(self, tmp_path):
        result = s0_cli.run_diversity_audit(
            ["https://e.com/x"],
            classifier_artifact_path=None,
        )
        # find_round_3_checkpoint will return None against tmp env
        with patch.object(s0_cli, "find_round_3_checkpoint",
                          return_value=None):
            result = s0_cli.run_diversity_audit(["https://e.com/x"])
            assert result["verdict"] == "FAIL"
            assert result["verdict_reason"] == "no_classifier_artifact"


class TestCheckpointDiscovery:
    def test_finds_most_recent_checkpoint(self, tmp_path):
        cdir = tmp_path / "posture_classifier"
        cdir.mkdir()
        (cdir / "posture_classifier_n100_111.jsonl").write_text("{}")
        (cdir / "posture_classifier_n100_222.jsonl").write_text("{}")
        latest = s0_cli.find_round_3_checkpoint(tmp_path)
        assert latest.name == "posture_classifier_n100_222.jsonl"

    def test_returns_none_when_no_artifacts(self, tmp_path):
        latest = s0_cli.find_round_3_checkpoint(tmp_path)
        assert latest is None
