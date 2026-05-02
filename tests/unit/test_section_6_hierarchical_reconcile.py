"""Pin Slice 34 — Section 6.2 quarterly hierarchical prior reconciliation."""

from __future__ import annotations

import pytest

from adam.intelligence.section_6 import (
    HierarchicalReconciliationResult,
    PriorLevel,
    reconcile_hierarchy,
)
from adam.intelligence.section_6.hierarchical_reconcile import (
    DEFAULT_PARENT_PRIOR_STRENGTH,
    LEVEL_BRAND,
    LEVEL_CAMPAIGN,
    LEVEL_CATEGORY,
    LEVEL_CORPUS,
    LEVEL_ORDER,
)


# -----------------------------------------------------------------------------
# Constants + canonical level ordering
# -----------------------------------------------------------------------------


def test_level_order_matches_directive():
    """Per directive line 779: 'corpus → category → brand → campaign'."""
    assert LEVEL_ORDER == (
        LEVEL_CORPUS, LEVEL_CATEGORY, LEVEL_BRAND, LEVEL_CAMPAIGN,
    )
    assert LEVEL_CORPUS == "corpus"
    assert LEVEL_CATEGORY == "category"
    assert LEVEL_BRAND == "brand"
    assert LEVEL_CAMPAIGN == "campaign"


def test_default_parent_prior_strength_is_5():
    assert DEFAULT_PARENT_PRIOR_STRENGTH == 5.0


def test_dataclasses_frozen():
    pl = PriorLevel(level_name="x", parent_level=None)
    with pytest.raises((AttributeError, Exception)):
        pl.level_name = "y"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Empty observations → uninformative Beta(1,1)
# -----------------------------------------------------------------------------


def test_empty_observations_at_every_level():
    """No observations anywhere → every level has Beta(1, 1) per
    mechanism (uninformative prior)."""
    out = reconcile_hierarchy()
    assert isinstance(out, HierarchicalReconciliationResult)
    assert len(out.levels) == 4
    # Corpus level should have Beta(1, 1) per mechanism — flat prior.
    corpus = out.levels[0]
    for m, (a, b) in corpus.per_mechanism_alpha_beta.items():
        assert a == pytest.approx(1.0)
        assert b == pytest.approx(1.0)
    # Each subsequent level adds the parent's reweighted prior;
    # in the empty case the parent is Beta(1,1), so the child's α + β
    # increases by parent_prior_strength.
    category = out.levels[1]
    a0, b0 = category.per_mechanism_alpha_beta[
        list(category.per_mechanism_alpha_beta.keys())[0]
    ]
    # Parent contributes parent_prior_strength worth of mass.
    assert a0 + b0 == pytest.approx(2.0 + DEFAULT_PARENT_PRIOR_STRENGTH)


# -----------------------------------------------------------------------------
# Level structure
# -----------------------------------------------------------------------------


def test_corpus_has_no_parent():
    out = reconcile_hierarchy()
    assert out.levels[0].level_name == LEVEL_CORPUS
    assert out.levels[0].parent_level is None


def test_category_parent_is_corpus():
    out = reconcile_hierarchy()
    assert out.levels[1].parent_level == LEVEL_CORPUS


def test_brand_parent_is_category():
    out = reconcile_hierarchy()
    assert out.levels[2].parent_level == LEVEL_CATEGORY


def test_campaign_parent_is_brand():
    out = reconcile_hierarchy()
    assert out.levels[3].parent_level == LEVEL_BRAND


# -----------------------------------------------------------------------------
# Observations at level propagate into level's posterior
# -----------------------------------------------------------------------------


def test_corpus_observations_update_corpus_posterior():
    """100 observations on social_proof with 50 conversions → Beta(51, 51)
    at corpus level. Higher levels inherit via partial pooling."""
    out = reconcile_hierarchy(
        corpus_observations={"social_proof": (100, 50)},
        mechanisms=["social_proof"],
    )
    a, b = out.levels[0].per_mechanism_alpha_beta["social_proof"]
    assert a == pytest.approx(51.0)
    assert b == pytest.approx(51.0)


def test_brand_observations_dont_leak_into_corpus():
    """Per the hierarchical model: brand observations affect brand
    posterior, NOT the corpus posterior. (Reverse direction —
    parent → child only — at this slice's reconciliation step.)"""
    out = reconcile_hierarchy(
        brand_observations={"social_proof": (1000, 800)},
        mechanisms=["social_proof"],
    )
    # Corpus has Beta(1, 1) — unaffected.
    a, b = out.levels[0].per_mechanism_alpha_beta["social_proof"]
    assert a == pytest.approx(1.0)
    assert b == pytest.approx(1.0)
    # Brand has its own observations + parent (Beta(1,1) corpus +
    # Beta(1,1) category) blended in.
    brand_a, brand_b = out.levels[2].per_mechanism_alpha_beta[
        "social_proof"
    ]
    assert brand_a > 1.0
    assert brand_b > 1.0


def test_campaign_inherits_from_brand_inherits_from_category():
    """The hierarchical chain: campaign's posterior is influenced
    by brand observations even when campaign has no direct
    observations."""
    out = reconcile_hierarchy(
        brand_observations={"social_proof": (200, 180)},  # high success
        mechanisms=["social_proof"],
    )
    # Campaign level posterior should reflect brand's HIGH success
    # via the propagated prior.
    camp_a, camp_b = out.levels[3].per_mechanism_alpha_beta[
        "social_proof"
    ]
    # α >> β reflects the brand's high success rate.
    assert camp_a > camp_b


def test_n_observations_per_level_correct():
    """n_observations is per-level (not cumulative)."""
    out = reconcile_hierarchy(
        corpus_observations={"social_proof": (100, 50)},
        category_observations={"social_proof": (200, 100)},
        brand_observations={"social_proof": (50, 30)},
        campaign_observations={"social_proof": (10, 8)},
        mechanisms=["social_proof"],
    )
    n_by_level = {l.level_name: l.n_observations for l in out.levels}
    assert n_by_level[LEVEL_CORPUS] == 100
    assert n_by_level[LEVEL_CATEGORY] == 200
    assert n_by_level[LEVEL_BRAND] == 50
    assert n_by_level[LEVEL_CAMPAIGN] == 10


# -----------------------------------------------------------------------------
# Determinism + version stamping
# -----------------------------------------------------------------------------


def test_reconcile_is_deterministic():
    """Pure function — same inputs → same output."""
    a = reconcile_hierarchy(
        corpus_observations={"social_proof": (50, 25)},
        category_observations={"social_proof": (20, 15)},
        mechanisms=["social_proof"],
    )
    b = reconcile_hierarchy(
        corpus_observations={"social_proof": (50, 25)},
        category_observations={"social_proof": (20, 15)},
        mechanisms=["social_proof"],
    )
    for la, lb in zip(a.levels, b.levels):
        assert la.per_mechanism_alpha_beta == lb.per_mechanism_alpha_beta


def test_inventory_version_stamped():
    out = reconcile_hierarchy(inventory_version="luxy-q2-2026")
    assert out.inventory_version == "luxy-q2-2026"


def test_default_mechanisms_are_canonical_8():
    """When no mechanisms supplied, default to Cialdini-6 + reason_why
    + unity (matching mechanism_activation_scorer's CANONICAL_MECHANISMS)."""
    out = reconcile_hierarchy()
    assert set(out.mechanisms) == {
        "social_proof", "scarcity", "authority", "reciprocity",
        "commitment", "liking", "unity", "reason_why",
    }


# -----------------------------------------------------------------------------
# Partial pooling correctness
# -----------------------------------------------------------------------------


def test_strong_corpus_signal_propagates_to_campaign():
    """High corpus α / β ratio → campaign mean shifts toward corpus
    mean even when campaign has no direct observations."""
    out = reconcile_hierarchy(
        corpus_observations={"social_proof": (10000, 9000)},  # 90% conv
        mechanisms=["social_proof"],
    )
    # Corpus mean ≈ 0.9
    c_a, c_b = out.levels[0].per_mechanism_alpha_beta["social_proof"]
    corpus_mean = c_a / (c_a + c_b)
    assert corpus_mean == pytest.approx(0.9, abs=0.01)
    # Campaign with no direct obs has parent_prior_strength worth
    # of corpus's mass — so campaign mean should be biased toward
    # 0.9 (uninformative prior baseline is 0.5).
    cmp_a, cmp_b = out.levels[3].per_mechanism_alpha_beta["social_proof"]
    campaign_mean = cmp_a / (cmp_a + cmp_b)
    assert campaign_mean > 0.5  # propagated upward signal


def test_parent_prior_strength_controls_pooling():
    """Larger parent_prior_strength → more shrinkage toward parent."""
    out_weak = reconcile_hierarchy(
        corpus_observations={"social_proof": (1000, 900)},
        campaign_observations={"social_proof": (100, 10)},  # 10% conv,
                                                            # opposite direction
        mechanisms=["social_proof"],
        parent_prior_strength=0.1,  # weak shrinkage
    )
    out_strong = reconcile_hierarchy(
        corpus_observations={"social_proof": (1000, 900)},
        campaign_observations={"social_proof": (100, 10)},
        mechanisms=["social_proof"],
        parent_prior_strength=100.0,  # very strong shrinkage
    )
    weak_a, weak_b = out_weak.levels[3].per_mechanism_alpha_beta[
        "social_proof"
    ]
    weak_mean = weak_a / (weak_a + weak_b)
    strong_a, strong_b = out_strong.levels[3].per_mechanism_alpha_beta[
        "social_proof"
    ]
    strong_mean = strong_a / (strong_a + strong_b)
    # Weak shrinkage → campaign mean closer to its own data (~0.10).
    # Strong shrinkage → campaign mean closer to corpus signal (~0.90).
    assert weak_mean < strong_mean
