"""Pin Slice 37 — round-2 candidate pool + stratified entropy sampling.

Per 2026-05-03 directive (round-1 macro-AUC < 0.30 branch). The pool
substrate must:

  * provide ≥ 400 corporate-traveler-relevant candidate URLs;
  * flatten cleanly to (source, url) tuples via ``get_full_pool``;
  * produce a stratified top-N that respects the ``min_per_class``
    floor when sufficient candidates predict into each class;
  * return surfaced rows in entropy-descending order;
  * exclude URLs already labeled (``exclude_urls`` filter).
"""

from __future__ import annotations

from typing import List

import numpy as np
import pytest

from adam.intelligence.posture_candidate_pool import (
    CANDIDATE_URLS,
    CandidateScore,
    _shannon_entropy,
    get_full_pool,
    stratified_top_n,
)
from adam.intelligence.posture_classifier import URLPostureClassifier


# -----------------------------------------------------------------------------
# Pool shape contract
# -----------------------------------------------------------------------------


def test_pool_size_at_least_400():
    """Directive named ~500; floor at 400 is the binding constraint
    so a single source's URL list shrinking won't silently drop
    coverage below the operational target."""
    pool = get_full_pool()
    assert len(pool) >= 400, (
        f"Pool too small: {len(pool)} < 400 — directive named ~500 "
        f"corporate-traveler-relevant URLs"
    )


def test_pool_covers_directive_named_seed_sources():
    """Directive named eight seed sources; pool must include all of
    them under recognizable keys."""
    required = {
        "wirecutter",
        "bloomberg",
        "concur_expensify",
        "skift",
        "business_insider",
        "productivity_docs",
        "travel_comparison",
        "executive_news",
    }
    missing = required - set(CANDIDATE_URLS.keys())
    assert not missing, f"Missing seed sources: {missing}"


def test_get_full_pool_flattens_correctly():
    """Each (source, url) tuple matches the source-keyed dict
    contents exactly."""
    pool = get_full_pool()
    by_source: dict[str, list[str]] = {}
    for src, url in pool:
        by_source.setdefault(src, []).append(url)
    for src, expected_urls in CANDIDATE_URLS.items():
        assert by_source.get(src, []) == expected_urls, (
            f"Source {src} flatten mismatch"
        )


def test_pool_has_no_duplicate_urls():
    """Each URL should appear at most once across all sources."""
    pool = get_full_pool()
    urls = [u for (_, u) in pool]
    assert len(urls) == len(set(urls)), (
        "Duplicate URLs in pool — would inflate entropy ranking"
    )


# -----------------------------------------------------------------------------
# Shannon entropy contract
# -----------------------------------------------------------------------------


def test_entropy_uniform_is_log_n():
    """Shannon entropy in nats: uniform 5-class distribution = ln(5)."""
    p = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
    H = _shannon_entropy(p)
    assert H == pytest.approx(np.log(5.0), abs=1e-6)


def test_entropy_deterministic_is_zero():
    """One-hot distribution: entropy = 0."""
    p = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
    H = _shannon_entropy(p)
    assert H == pytest.approx(0.0, abs=1e-6)


def test_entropy_handles_zeros_via_clip():
    """log(0) is -inf; the clip should keep entropy finite."""
    p = np.array([0.5, 0.5, 0.0, 0.0, 0.0])
    H = _shannon_entropy(p)
    assert np.isfinite(H)
    assert H > 0


# -----------------------------------------------------------------------------
# Stratified top-N contract
# -----------------------------------------------------------------------------


def _build_toy_classifier() -> URLPostureClassifier:
    """Train a tiny multi-class classifier with 5 classes covering
    the production posture taxonomy. Used to validate stratified_top_n
    end-to-end without depending on the live :PostureLabel corpus."""
    train_urls = [
        # INFORMATION_FORAGING — reading-mode URLs
        "https://www.bloomberg.com/news/articles/markets-update-2025",
        "https://www.bloomberg.com/news/articles/economy-outlook-q4",
        "https://www.ft.com/content/cfo-priorities-2026",
        "https://www.economist.com/business/recent-articles",
        "https://hbr.org/topic/leadership/articles",
        # TASK_COMPLETION — productivity tools
        "https://www.concur.com/expense-management",
        "https://www.expensify.com/expense-reports",
        "https://www.notion.so/help/databases",
        "https://slack.com/help/articles/setup",
        # LEISURE_BROWSING — luxury travel
        "https://www.cntraveler.com/destinations/europe",
        "https://www.travelandleisure.com/luxury-travel",
        "https://www.afar.com/inspiration/luxury-travel",
        # SOCIAL_CONSUMPTION — community/social
        "https://www.linkedin.com/feed/main",
        "https://www.reddit.com/r/businesstravel/comments/recent",
        "https://x.com/business/posts/today",
        # TRANSACTIONAL_COMPARISON — comparison sites
        "https://www.kayak.com/flights/JFK-LHR",
        "https://www.expedia.com/Hotels-Search",
        "https://www.booking.com/searchresults",
    ]
    train_labels = [
        "INFORMATION_FORAGING", "INFORMATION_FORAGING",
        "INFORMATION_FORAGING", "INFORMATION_FORAGING",
        "INFORMATION_FORAGING",
        "TASK_COMPLETION", "TASK_COMPLETION",
        "TASK_COMPLETION", "TASK_COMPLETION",
        "LEISURE_BROWSING", "LEISURE_BROWSING", "LEISURE_BROWSING",
        "SOCIAL_CONSUMPTION", "SOCIAL_CONSUMPTION", "SOCIAL_CONSUMPTION",
        "TRANSACTIONAL_COMPARISON", "TRANSACTIONAL_COMPARISON",
        "TRANSACTIONAL_COMPARISON",
    ]
    clf = URLPostureClassifier(random_state=2026)
    clf.fit(train_urls, train_labels)
    return clf


def test_stratified_top_n_returns_at_most_n():
    clf = _build_toy_classifier()
    pool = get_full_pool()
    surfaced = stratified_top_n(clf, pool, n=80, min_per_class=10)
    assert len(surfaced) <= 80


def test_stratified_top_n_entropy_descending():
    """Surfaced rows in overall entropy-descending order (most
    uncertain first)."""
    clf = _build_toy_classifier()
    pool = get_full_pool()
    surfaced = stratified_top_n(clf, pool, n=80, min_per_class=10)
    if len(surfaced) < 2:
        pytest.skip("Not enough surfaced candidates to check ordering")
    for i in range(len(surfaced) - 1):
        assert surfaced[i].entropy >= surfaced[i + 1].entropy, (
            f"Entropy not descending at idx {i}: "
            f"{surfaced[i].entropy:.4f} < {surfaced[i + 1].entropy:.4f}"
        )


def test_stratified_top_n_respects_p_class_floor():
    """The ≥min_per_class floor is on **P(class)-ranked** candidates,
    not argmax-predicted-class. For each class, the surfaced set must
    contain ≥``min_per_class`` candidates that rank in the pool's
    top-(min_per_class + n_classes - 1) by P(class).

    The slack of (n_classes - 1) accounts for cross-class dedup: a
    URL can be the #1 P(class_A) AND #1 P(class_B) candidate, but
    enters the surfaced set once — so the second class's bucket
    pulls its #2 instead. Worst case: every class shares its top
    pick with every other class, so the floor's ``min_per_class``
    surfaced is drawn from the pool's top-(min_per_class + n - 1)."""
    clf = _build_toy_classifier()
    pool = get_full_pool()
    min_per_class = 10
    surfaced = stratified_top_n(
        clf, pool, n=80, min_per_class=min_per_class,
    )
    surfaced_urls = {c.url for c in surfaced}

    pool_proba = clf.predict_proba([u for (_, u) in pool])
    pool_urls_only = [u for (_, u) in pool]
    n_classes = len(clf.classes_)
    floor_window = min_per_class + n_classes - 1

    for cls_ix, cls in enumerate(clf.classes_):
        # Pool URLs ranked by P(class) descending.
        ranked = sorted(
            range(len(pool_urls_only)),
            key=lambda i: -pool_proba[i, cls_ix],
        )
        top_window_urls = {
            pool_urls_only[i] for i in ranked[:floor_window]
        }
        # Count surfaced URLs that fall in the pool's top-floor_window
        # by P(cls).
        surfaced_in_window = len(
            top_window_urls & surfaced_urls
        )
        assert surfaced_in_window >= min_per_class, (
            f"Class {cls}: only {surfaced_in_window} surfaced URLs "
            f"in pool's top-{floor_window} by P(cls); need "
            f"≥{min_per_class}"
        )


def test_stratified_top_n_excludes_already_labeled():
    """``exclude_urls`` filter must drop already-labeled URLs from
    the surfaced set."""
    clf = _build_toy_classifier()
    pool = get_full_pool()
    # Pick a few URLs from the pool to "exclude"
    excluded = [pool[0][1], pool[10][1], pool[20][1]]
    surfaced = stratified_top_n(
        clf, pool, n=80, min_per_class=10,
        exclude_urls=excluded,
    )
    surfaced_urls = {c.url for c in surfaced}
    for ex in excluded:
        assert ex not in surfaced_urls, (
            f"{ex} was excluded but still surfaced"
        )


def test_stratified_top_n_handles_empty_pool():
    clf = _build_toy_classifier()
    surfaced = stratified_top_n(clf, [], n=80, min_per_class=10)
    assert surfaced == []


def test_stratified_top_n_proba_sums_to_one():
    """Each surfaced row's proba vector should be a valid probability
    distribution (sum ≈ 1)."""
    clf = _build_toy_classifier()
    pool = get_full_pool()
    surfaced = stratified_top_n(clf, pool, n=80, min_per_class=10)
    for c in surfaced:
        assert sum(c.proba) == pytest.approx(1.0, abs=1e-6), (
            f"Proba doesn't sum to 1: {c.proba}"
        )
        assert len(c.proba) == len(clf.classes_)
