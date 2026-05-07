"""G1.path4 — class-balanced training regression tests.

Pin behavior of `URLPostureClassifier.fit(urls, labels, class_weight)`:

1. Default class_weight='balanced' on a deliberately imbalanced
   synthetic corpus does NOT collapse predictions to the modal class.
2. Backwards-compat: class_weight=None reproduces the prior uniform-
   weight behavior on a deterministic test corpus.
3. Round-trip: persist_classifier_artifact + load_classifier_artifact
   preserves the class_weight regime through JSONL serialization.
4. Class-collapse regression: imbalanced few-shot corpus collapses
   under uniform weights but NOT under balanced weights.
"""
from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from adam.intelligence.posture_classifier import (
    URLPostureClassifier,
    load_classifier_artifact,
    persist_classifier_artifact,
)


# Synthetic URL templates per posture class — picked so URL tokens
# carry class signal (the v0.1 classifier is URL-token-only).
URL_TEMPLATES = {
    "INFORMATION_FORAGING": [
        "https://example.com/research/topic-{i}",
        "https://example.com/learn/about/{i}",
        "https://example.com/wiki/article-{i}",
        "https://example.com/explore/{i}",
        "https://example.com/discover/{i}",
    ],
    "TASK_COMPLETION": [
        "https://app.example.com/dashboard/task-{i}",
        "https://app.example.com/workflow/{i}",
        "https://app.example.com/inbox/{i}",
        "https://app.example.com/calendar/{i}",
        "https://app.example.com/project/{i}",
    ],
    "LEISURE_BROWSING": [
        "https://entertainment.example.com/show/{i}",
        "https://entertainment.example.com/movie/{i}",
        "https://entertainment.example.com/celebrity/{i}",
        "https://entertainment.example.com/lifestyle/{i}",
        "https://entertainment.example.com/feed/{i}",
    ],
    "SOCIAL_CONSUMPTION": [
        "https://social.example.com/feed/{i}",
        "https://social.example.com/post/{i}",
        "https://social.example.com/profile/{i}",
        "https://social.example.com/comment/{i}",
        "https://social.example.com/share/{i}",
    ],
    "TRANSACTIONAL_COMPARISON": [
        "https://shop.example.com/compare/{i}",
        "https://shop.example.com/product/{i}",
        "https://shop.example.com/checkout/{i}",
        "https://shop.example.com/cart/{i}",
        "https://shop.example.com/buy/{i}",
    ],
}


def _make_corpus(per_class_counts: dict) -> tuple:
    """Build (urls, labels) where each class has the requested count
    of URLs from its template set. URL tokens carry class signal."""
    urls = []
    labels = []
    for cls, n in per_class_counts.items():
        templates = URL_TEMPLATES[cls]
        for i in range(n):
            tpl = templates[i % len(templates)]
            urls.append(tpl.format(i=i))
            labels.append(cls)
    return urls, labels


# ----------------------------------------------------------------------------
# 1. Default class_weight='balanced' on imbalanced corpus
# ----------------------------------------------------------------------------

class TestBalancedDefaultOnImbalancedCorpus:
    """Train on 80 INFO + 5 each of others = 100 total, 80% INFO.
    Under uniform weights this collapses to all-INFO; under balanced
    weights predictions should span multiple classes."""

    @pytest.fixture
    def imbalanced_corpus(self):
        return _make_corpus({
            "INFORMATION_FORAGING": 80,
            "TASK_COMPLETION": 5,
            "LEISURE_BROWSING": 5,
            "SOCIAL_CONSUMPTION": 5,
            "TRANSACTIONAL_COMPARISON": 5,
        })

    def test_default_is_balanced(self):
        """Pin: the default class_weight is 'balanced' (G1.path4 amendment)."""
        clf = URLPostureClassifier(random_state=2026)
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 5,
            "TASK_COMPLETION": 5,
        })
        clf.fit(urls, labels)
        assert clf.class_weight == "balanced"

    def test_balanced_default_does_not_collapse_to_modal(
        self, imbalanced_corpus,
    ):
        """Train on 80% INFO; predict on a balanced eval set; expect
        predictions across multiple classes."""
        urls, labels = imbalanced_corpus
        clf = URLPostureClassifier(random_state=2026)
        clf.fit(urls, labels)  # default 'balanced'

        # Eval set: 5 URLs per class, distinct from training-set indexing
        eval_urls = []
        eval_true = []
        for cls in URL_TEMPLATES:
            for i in range(100, 105):  # different i-range from training
                tpl = URL_TEMPLATES[cls][i % len(URL_TEMPLATES[cls])]
                eval_urls.append(tpl.format(i=i))
                eval_true.append(cls)

        preds = clf.predict(eval_urls)
        pred_counts = Counter(preds)
        modal_share = max(pred_counts.values()) / len(preds)

        # Under balanced weights, no single class should dominate
        # >= 60% of predictions on a class-balanced eval set with
        # discriminative URL tokens.
        assert modal_share < 0.60, (
            f"balanced weights produced modal_share={modal_share:.2f}; "
            f"pred_counts={dict(pred_counts)}"
        )


# ----------------------------------------------------------------------------
# 2. Backwards-compat: class_weight=None reproduces uniform behavior
# ----------------------------------------------------------------------------

class TestBackwardsCompatNoneWeight:
    def test_none_weight_records_none_in_class_weight_field(self):
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 5,
            "TASK_COMPLETION": 5,
            "LEISURE_BROWSING": 5,
        })
        clf = URLPostureClassifier(random_state=2026)
        clf.fit(urls, labels, class_weight=None)
        assert clf.class_weight is None

    def test_none_weight_reproducible_with_fixed_seed(self):
        """Two fits with class_weight=None + same seed should produce
        identical coefficient matrices (uniform-weight determinism)."""
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 10,
            "TASK_COMPLETION": 10,
            "LEISURE_BROWSING": 10,
            "SOCIAL_CONSUMPTION": 10,
            "TRANSACTIONAL_COMPARISON": 10,
        })

        c1 = URLPostureClassifier(random_state=2026)
        c1.fit(urls, labels, class_weight=None)
        c2 = URLPostureClassifier(random_state=2026)
        c2.fit(urls, labels, class_weight=None)

        # Coefficient matrices identical (deterministic uniform-weight fit)
        import numpy as np
        assert np.allclose(c1.model.coef_, c2.model.coef_)
        assert np.allclose(c1.model.intercept_, c2.model.intercept_)

    def test_balanced_and_none_produce_different_coefficients(self):
        """Sanity: balanced and uniform regimes produce different
        models (proves the parameter is actually being passed through)."""
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 80,
            "TASK_COMPLETION": 5,
            "LEISURE_BROWSING": 5,
            "SOCIAL_CONSUMPTION": 5,
            "TRANSACTIONAL_COMPARISON": 5,
        })

        c_balanced = URLPostureClassifier(random_state=2026)
        c_balanced.fit(urls, labels, class_weight="balanced")
        c_uniform = URLPostureClassifier(random_state=2026)
        c_uniform.fit(urls, labels, class_weight=None)

        import numpy as np
        # On an imbalanced corpus, the two regimes MUST differ.
        assert not np.allclose(c_balanced.model.coef_,
                               c_uniform.model.coef_)


# ----------------------------------------------------------------------------
# 3. Round-trip: persist + load preserves class_weight
# ----------------------------------------------------------------------------

class TestArtifactRoundTripPreservesClassWeight:
    @pytest.mark.parametrize("cw", ["balanced", None])
    def test_class_weight_round_trips(self, cw, tmp_path):
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 5,
            "TASK_COMPLETION": 5,
            "LEISURE_BROWSING": 5,
        })
        clf = URLPostureClassifier(random_state=2026)
        clf.fit(urls, labels, class_weight=cw)

        path = tmp_path / "art.jsonl"
        persist_classifier_artifact(clf, str(path))
        loaded = load_classifier_artifact(str(path))

        assert loaded.class_weight == cw

    def test_legacy_artifact_without_class_weight_loads_as_none(
        self, tmp_path,
    ):
        """Older artifacts (pre-G1.path4) lack the class_weight key —
        load defaults to None (uniform), the regime they were trained
        under."""
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 5,
            "TASK_COMPLETION": 5,
            "LEISURE_BROWSING": 5,
        })
        clf = URLPostureClassifier(random_state=2026)
        clf.fit(urls, labels, class_weight=None)

        path = tmp_path / "legacy.jsonl"
        persist_classifier_artifact(clf, str(path))

        # Strip class_weight from the header to simulate a pre-path4 artifact
        lines = path.read_text().splitlines()
        header = json.loads(lines[0])
        header.pop("class_weight", None)
        lines[0] = json.dumps(header)
        path.write_text("\n".join(lines) + "\n")

        loaded = load_classifier_artifact(str(path))
        assert loaded.class_weight is None  # default for legacy

    def test_persisted_jsonl_contains_class_weight_in_header(
        self, tmp_path,
    ):
        urls, labels = _make_corpus({
            "INFORMATION_FORAGING": 5,
            "TASK_COMPLETION": 5,
        })
        clf = URLPostureClassifier(random_state=2026)
        clf.fit(urls, labels, class_weight="balanced")

        path = tmp_path / "art.jsonl"
        persist_classifier_artifact(clf, str(path))

        first_line = path.read_text().splitlines()[0]
        header = json.loads(first_line)
        assert header.get("class_weight") == "balanced"


# ----------------------------------------------------------------------------
# 4. Class-collapse regression test
# ----------------------------------------------------------------------------

class TestClassCollapseRegression:
    """The mode of failure G1.path4 addresses: heavy imbalance + small n
    + uniform weights → predictions collapse to modal class.

    The balanced regime should mitigate; the uniform regime should NOT."""

    @pytest.fixture
    def collapse_prone_corpus(self):
        """50 INFO + 3 each of others = 62 total, 80% INFO. Provokes
        class collapse under uniform weights at low-N."""
        return _make_corpus({
            "INFORMATION_FORAGING": 50,
            "TASK_COMPLETION": 3,
            "LEISURE_BROWSING": 3,
            "SOCIAL_CONSUMPTION": 3,
            "TRANSACTIONAL_COMPARISON": 3,
        })

    @pytest.fixture
    def balanced_eval_set(self):
        """5 URLs per class for prediction-diversity measurement."""
        eval_urls = []
        eval_true = []
        for cls in URL_TEMPLATES:
            for i in range(200, 205):
                tpl = URL_TEMPLATES[cls][i % len(URL_TEMPLATES[cls])]
                eval_urls.append(tpl.format(i=i))
                eval_true.append(cls)
        return eval_urls, eval_true

    def test_uniform_collapses_balanced_does_not(
        self, collapse_prone_corpus, balanced_eval_set,
    ):
        urls, labels = collapse_prone_corpus
        eval_urls, eval_true = balanced_eval_set

        # Uniform regime — expected to collapse heavily toward INFO
        c_uniform = URLPostureClassifier(random_state=2026)
        c_uniform.fit(urls, labels, class_weight=None)
        uniform_preds = c_uniform.predict(eval_urls)
        uniform_modal = max(Counter(uniform_preds).values()) / len(uniform_preds)

        # Balanced regime — should produce diverse predictions
        c_balanced = URLPostureClassifier(random_state=2026)
        c_balanced.fit(urls, labels, class_weight="balanced")
        balanced_preds = c_balanced.predict(eval_urls)
        balanced_modal = max(Counter(balanced_preds).values()) / len(balanced_preds)

        # The balanced regime must be strictly less concentrated
        # toward the modal class than the uniform regime on this
        # collapse-prone corpus.
        assert balanced_modal < uniform_modal, (
            f"balanced_modal={balanced_modal:.2f} >= "
            f"uniform_modal={uniform_modal:.2f} — balanced regime "
            f"failed to mitigate class collapse"
        )
        # Additionally, the balanced regime should produce predictions
        # spanning at least 3 distinct classes on a 5-class eval set.
        assert len(set(balanced_preds)) >= 3, (
            f"balanced regime produced predictions across only "
            f"{len(set(balanced_preds))} class(es); expected >= 3"
        )

    def test_g1_path4_diagnostic_signal_pinned(
        self, collapse_prone_corpus, balanced_eval_set,
    ):
        """Pin the headline diagnostic from session #002 EVE: under
        uniform weights at this N + imbalance, the classifier collapses
        toward a single class. The balanced regime breaks this."""
        urls, labels = collapse_prone_corpus
        eval_urls, _ = balanced_eval_set

        c_uniform = URLPostureClassifier(random_state=2026)
        c_uniform.fit(urls, labels, class_weight=None)
        uniform_preds = c_uniform.predict(eval_urls)
        uniform_unique_classes = len(set(uniform_preds))

        # Uniform regime should produce predictions across very few
        # classes (the collapse signal). Bound at <= 3 to allow for
        # sklearn version drift; a stricter bound would over-pin.
        assert uniform_unique_classes <= 3, (
            f"uniform regime produced {uniform_unique_classes} unique "
            f"classes; expected <= 3 (collapse signal)"
        )
