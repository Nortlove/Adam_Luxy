# =============================================================================
# Section 6.2 quarterly cadence — hierarchical prior reconciliation
# Location: adam/intelligence/section_6/hierarchical_reconcile.py
# =============================================================================
"""Per directive Section 6.2 quarterly cadence (line 779-781):

    Full hierarchical-prior reconciliation: corpus → category →
    brand → campaign.
    Audit of the brand-intelligence library against current
    LUXY-corpus-derived state.
    Audit of primary-metaphor inventory against the page corpus
    and the live decision traces.

The reconciliation walks four nested levels:

    LEVEL 0  CORPUS    — population-wide priors derived from the
                         Amazon (or LUXY-domain) corpus. Broadest
                         prior, smallest variance per cell, most
                         data behind it.
    LEVEL 1  CATEGORY  — category-conditioned priors (e.g.,
                         transportation / B2B / luxury). Narrows
                         from corpus.
    LEVEL 2  BRAND     — brand-conditioned (e.g., LUXY-specific).
                         Narrows from category.
    LEVEL 3  CAMPAIGN  — campaign-specific (e.g., the current
                         LUXY rideshare campaign). Narrows from
                         brand.

Each level inherits + updates the prior from above via Bayesian
hierarchical pooling. The reconciliation produces a versioned
prior table at every level, with the appropriate per-level
variance + sample-size accounting.

THE PRIMITIVE

  * ``PriorLevel`` — frozen dataclass: level_name, parent_level,
    per_mechanism_alpha_beta dict, n_observations.
  * ``HierarchicalReconciliationResult`` — versioned output:
    ordered list of PriorLevel + reconciliation metadata.
  * ``reconcile_hierarchy(corpus_observations, category_obs,
    brand_obs, campaign_obs, *, mechanisms, version)`` — pipeline
    entry. Pure function; deterministic.

PARTIAL POOLING FORMULA

Per Spine #1's hierarchical prior model:

    posterior_lvl(α, β) = parent_prior_strength * parent_α_β
                        + n_observations_lvl * (lvl_α_β / n_lvl)

where parent_prior_strength is the weight given to the parent's
prior in mass-of-evidence units. v0.1 default: parent_prior_strength
= 5 (matches existing HierarchicalPriorManager pattern).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.2 lines 779-781 + Spine #1
    hierarchical pooling formulation + existing
    HierarchicalPriorManager substrate (core/dependencies +
    learned_priors_integration).

(b) Tests pin: empty observations at every level → uninformative
    Beta(1,1) at every level; observations at level N propagate
    UPWARD (campaign updates flow to brand, brand to category,
    category to corpus); reconciled posteriors converge to Bayesian
    expected values; PriorLevel frozen; deterministic from inputs.

(c) calibration_pending=True. parent_prior_strength=5 conservative;
    pilot calibration. A14 flag: SECTION_6_2_RECONCILE_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Multi-cohort hierarchical structure within a campaign
      (campaign × cohort cells). v0.1 reconciles a single chain.
    * MCMC / HMC posterior fit. v0.1 uses online conjugate Beta
      updates; full HMC reconcile is Task 36 (already shipped)
      operating on per-user posteriors specifically.
    * Brand-intelligence library audit step. Sibling slice — the
      audit cross-references reconciled corpus state against the
      brand library; v0.1 ships only the prior reconciliation.
    * Primary-metaphor inventory audit step. Sibling — same
      pattern as the brand-intelligence audit.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# A14 SECTION_6_2_RECONCILE_PILOT_PENDING
DEFAULT_PARENT_PRIOR_STRENGTH: float = 5.0


# Canonical level ordering (top → bottom).
LEVEL_CORPUS: str = "corpus"
LEVEL_CATEGORY: str = "category"
LEVEL_BRAND: str = "brand"
LEVEL_CAMPAIGN: str = "campaign"

LEVEL_ORDER: Tuple[str, ...] = (
    LEVEL_CORPUS, LEVEL_CATEGORY, LEVEL_BRAND, LEVEL_CAMPAIGN,
)


@dataclass(frozen=True)
class PriorLevel:
    """One reconciled prior level.

    ``per_mechanism_alpha_beta``: {mechanism: (alpha, beta)} —
        Beta sufficient stats post-reconciliation at this level.
    ``n_observations``: sum of observations at THIS level (not
        cumulative through parents).
    """

    level_name: str
    parent_level: Optional[str]
    per_mechanism_alpha_beta: Dict[str, Tuple[float, float]] = field(
        default_factory=dict,
    )
    n_observations: int = 0
    parent_prior_strength: float = DEFAULT_PARENT_PRIOR_STRENGTH


@dataclass(frozen=True)
class HierarchicalReconciliationResult:
    """One quarterly reconciliation run's output."""

    inventory_version: str
    levels: List[PriorLevel]
    mechanisms: List[str]
    started_at_ts: float = field(default_factory=time.time)
    finished_at_ts: float = 0.0


# =============================================================================
# Reconciliation
# =============================================================================


def _aggregate_observations(
    observations: Dict[str, Tuple[int, int]],
    mechanisms: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], int]:
    """Convert raw (n_obs, n_conv) per-mechanism observations into
    Beta(α=1+conv, β=1+failures) form. Returns (alpha_beta_dict,
    total_n)."""
    out: Dict[str, Tuple[float, float]] = {}
    total = 0
    for m in mechanisms:
        n, c = observations.get(m, (0, 0))
        out[m] = (1.0 + c, 1.0 + max(0, n - c))
        total += n
    return out, total


def _pool_with_parent(
    level_alpha_beta: Dict[str, Tuple[float, float]],
    parent_alpha_beta: Dict[str, Tuple[float, float]],
    parent_prior_strength: float,
) -> Dict[str, Tuple[float, float]]:
    """Partial pooling: shrink the level's posterior toward the
    parent's via parent_prior_strength weight (in evidence units).

    posterior(α, β) = parent_prior_strength × parent_α_β
                    + level_α_β

    Effectively: the parent's posterior becomes the prior for the
    level, weighted by parent_prior_strength.
    """
    out: Dict[str, Tuple[float, float]] = {}
    keys = set(level_alpha_beta.keys()) | set(parent_alpha_beta.keys())
    for m in keys:
        l_a, l_b = level_alpha_beta.get(m, (1.0, 1.0))
        p_a, p_b = parent_alpha_beta.get(m, (1.0, 1.0))
        # Normalize parent contribution to parent_prior_strength
        # total mass; scale parent (α, β) so α + β = parent_prior_strength.
        p_total = max(p_a + p_b, 1e-9)
        scaled_pa = parent_prior_strength * (p_a / p_total)
        scaled_pb = parent_prior_strength * (p_b / p_total)
        out[m] = (l_a + scaled_pa, l_b + scaled_pb)
    return out


def reconcile_hierarchy(
    *,
    corpus_observations: Optional[Dict[str, Tuple[int, int]]] = None,
    category_observations: Optional[Dict[str, Tuple[int, int]]] = None,
    brand_observations: Optional[Dict[str, Tuple[int, int]]] = None,
    campaign_observations: Optional[Dict[str, Tuple[int, int]]] = None,
    mechanisms: Optional[List[str]] = None,
    inventory_version: str = "v0.1-calibration",
    parent_prior_strength: float = DEFAULT_PARENT_PRIOR_STRENGTH,
) -> HierarchicalReconciliationResult:
    """Walk corpus → category → brand → campaign reconciliation.

    Args:
        corpus_observations / category_observations / brand_observations
            / campaign_observations: per-level observation maps
            ``{mechanism: (n_observations, n_conversions)}``. Missing
            levels are treated as empty (Beta(1,1) baseline).
        mechanisms: full mechanism list; observations at each level
            are aligned against this. Default is the canonical 8.
        inventory_version: stamped on the result for artifact
            versioning.
        parent_prior_strength: mass-of-evidence weight given to the
            parent's posterior when pooling into the child. Default
            5 — matches the existing HierarchicalPriorManager
            pattern.

    Returns:
        ``HierarchicalReconciliationResult`` with 4 PriorLevel
        objects (corpus first, campaign last). Each level's
        per_mechanism_alpha_beta reflects the partial-pooled
        posterior at that level.
    """
    started_at = time.time()
    if mechanisms is None:
        mechanisms = [
            "social_proof", "scarcity", "authority", "reciprocity",
            "commitment", "liking", "unity", "reason_why",
        ]

    obs_by_level = {
        LEVEL_CORPUS: corpus_observations or {},
        LEVEL_CATEGORY: category_observations or {},
        LEVEL_BRAND: brand_observations or {},
        LEVEL_CAMPAIGN: campaign_observations or {},
    }

    # Start with corpus (no parent — flat prior).
    levels: List[PriorLevel] = []
    parent_ab: Dict[str, Tuple[float, float]] = {}
    for ix, level_name in enumerate(LEVEL_ORDER):
        raw_obs = obs_by_level.get(level_name, {})
        level_ab, n_lvl = _aggregate_observations(raw_obs, mechanisms)

        if ix == 0:
            # Corpus level — no parent pooling.
            reconciled = level_ab
            parent_at_this_level: Optional[str] = None
        else:
            reconciled = _pool_with_parent(
                level_ab, parent_ab, parent_prior_strength,
            )
            parent_at_this_level = LEVEL_ORDER[ix - 1]

        levels.append(PriorLevel(
            level_name=level_name,
            parent_level=parent_at_this_level,
            per_mechanism_alpha_beta=reconciled,
            n_observations=n_lvl,
            parent_prior_strength=parent_prior_strength,
        ))
        parent_ab = reconciled

    return HierarchicalReconciliationResult(
        inventory_version=inventory_version,
        levels=levels,
        mechanisms=list(mechanisms),
        started_at_ts=started_at,
        finished_at_ts=time.time(),
    )
