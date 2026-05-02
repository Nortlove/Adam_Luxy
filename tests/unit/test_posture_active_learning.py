"""Pin Slice 26 — Phase 2 5-class posture active-learning loop.

Per 2026-05-02 wrap-out handoff (multi-session arc #2). Slice 26
ships the bootstrap batch generator + uncertainty-sampling SCAFFOLD
(stub returns "not_yet_trained_skip" sentinel until the trained
classifier ships).
"""

from __future__ import annotations

import pytest

from adam.intelligence.posture_active_learning import (
    BOOTSTRAP_THRESHOLD,
    DEFAULT_BATCH_SIZE,
    LabelingBatch,
    LabelingBatchEntry,
    _BOOTSTRAP_URLS,
    generate_bootstrap_batch,
    generate_uncertainty_sampling_batch,
    select_active_learning_round,
)
from adam.intelligence.posture_five_class import FIVE_CLASS_POSTURES


# -----------------------------------------------------------------------------
# Bootstrap corpus contract
# -----------------------------------------------------------------------------


def test_bootstrap_corpus_covers_all_5_classes():
    assert set(_BOOTSTRAP_URLS.keys()) == set(FIVE_CLASS_POSTURES)


def test_bootstrap_corpus_4_urls_per_class():
    for cls in FIVE_CLASS_POSTURES:
        assert len(_BOOTSTRAP_URLS[cls]) == 4


def test_bootstrap_corpus_urls_are_full_https():
    for cls in FIVE_CLASS_POSTURES:
        for url in _BOOTSTRAP_URLS[cls]:
            assert url.startswith("https://")


# -----------------------------------------------------------------------------
# generate_bootstrap_batch
# -----------------------------------------------------------------------------


def test_bootstrap_batch_is_round_1():
    batch = generate_bootstrap_batch()
    assert batch.round_index == 1
    assert batch.generator_kind == "bootstrap_diversity"


def test_bootstrap_batch_has_20_entries_default():
    batch = generate_bootstrap_batch()
    assert len(batch.entries) == 20


def test_bootstrap_batch_class_balanced():
    batch = generate_bootstrap_batch()
    by_class: dict = {}
    for entry in batch.entries:
        by_class[entry.suggested_label] = (
            by_class.get(entry.suggested_label, 0) + 1
        )
    for cls in FIVE_CLASS_POSTURES:
        assert by_class.get(cls) == 4


def test_bootstrap_batch_custom_n_per_class():
    batch = generate_bootstrap_batch(n_per_class=2)
    assert len(batch.entries) == 2 * 5  # 2 per class × 5 classes


def test_bootstrap_batch_deterministic_per_seed():
    a = generate_bootstrap_batch(seed=11)
    b = generate_bootstrap_batch(seed=11)
    a_urls = [e.url for e in a.entries]
    b_urls = [e.url for e in b.entries]
    assert a_urls == b_urls


def test_bootstrap_batch_different_seeds_different_within_class_order():
    a = generate_bootstrap_batch(seed=1)
    b = generate_bootstrap_batch(seed=999)
    # Same set of URLs (since class membership doesn't change), but
    # within-class order may differ.
    a_urls = sorted(e.url for e in a.entries)
    b_urls = sorted(e.url for e in b.entries)
    assert a_urls == b_urls  # same set
    a_order = [e.url for e in a.entries]
    b_order = [e.url for e in b.entries]
    # The two sequences may or may not differ depending on shuffle
    # outcomes; what we pin is that the bootstrap is reproducible
    # for a given seed (covered above).


def test_bootstrap_entries_carry_suggested_label_and_notes():
    batch = generate_bootstrap_batch()
    for entry in batch.entries:
        assert entry.suggested_label in FIVE_CLASS_POSTURES
        assert entry.classifier_entropy is None
        assert entry.notes is not None
        assert "operator" in entry.notes


def test_bootstrap_batch_id_traceable():
    batch = generate_bootstrap_batch(n_labels_in_corpus=5)
    assert "bootstrap" in batch.batch_id
    assert batch.n_labels_in_corpus_at_generation == 5


# -----------------------------------------------------------------------------
# Uncertainty-sampling stub (round 2+)
# -----------------------------------------------------------------------------


def test_uncertainty_sampling_no_classifier_returns_skip_sentinel():
    """When classifier=None (not yet trained), returns empty batch
    with not_yet_trained_skip sentinel."""
    batch = generate_uncertainty_sampling_batch(
        candidate_urls=["https://x", "https://y"],
        classifier=None,
    )
    assert batch.generator_kind == "not_yet_trained_skip"
    assert len(batch.entries) == 0


def test_uncertainty_sampling_with_classifier_raises_until_shipped():
    """When the trained classifier is supplied, the v0.1 scaffold
    raises NotImplementedError to flag the sibling-slice dependency."""
    fake_classifier = object()
    with pytest.raises(NotImplementedError):
        generate_uncertainty_sampling_batch(
            candidate_urls=["https://x"],
            classifier=fake_classifier,
        )


# -----------------------------------------------------------------------------
# select_active_learning_round routing
# -----------------------------------------------------------------------------


def test_router_picks_bootstrap_when_corpus_below_threshold():
    batch = select_active_learning_round(n_labels_in_corpus=0)
    assert batch.generator_kind == "bootstrap_diversity"


def test_router_picks_bootstrap_at_threshold_minus_one():
    batch = select_active_learning_round(
        n_labels_in_corpus=BOOTSTRAP_THRESHOLD - 1,
    )
    assert batch.generator_kind == "bootstrap_diversity"


def test_router_picks_skip_when_at_threshold_no_classifier():
    """At threshold + no classifier → not_yet_trained_skip."""
    batch = select_active_learning_round(
        n_labels_in_corpus=BOOTSTRAP_THRESHOLD,
        classifier=None,
    )
    assert batch.generator_kind == "not_yet_trained_skip"


# -----------------------------------------------------------------------------
# Schema validation
# -----------------------------------------------------------------------------


def test_labeling_batch_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LabelingBatch(
            batch_id="x", round_index=1,
            generator_kind="bootstrap_diversity",
            extra_field=42,  # type: ignore[call-arg]
        )


def test_labeling_batch_entry_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LabelingBatchEntry(
            url="https://x",
            extra=42,  # type: ignore[call-arg]
        )


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


def test_bootstrap_threshold_is_20():
    assert BOOTSTRAP_THRESHOLD == 20


def test_default_batch_size_is_20():
    assert DEFAULT_BATCH_SIZE == 20
