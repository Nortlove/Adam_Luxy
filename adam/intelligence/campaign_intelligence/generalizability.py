"""
Generalizability Scope Determination
======================================

The "Self-Adjusting Focal Lens" from the deployment package.

Uses DerSimonian-Laird random-effects meta-analysis to determine at
what scope each learning should be applied:

    I² < 25%  → SYSTEM_WIDE     (universal finding, update global priors)
    I² 25-50% → CATEGORY_LEVEL  (finding specific to product category)
    I² 50-75% → ARCHETYPE_LEVEL (finding specific to archetype)
    I² > 75%  → CAMPAIGN_SPECIFIC (high heterogeneity, don't generalize)

This prevents two failure modes:
1. Campaign-specific noise polluting global priors (over-generalization)
2. Genuinely universal findings trapped in a single campaign (under-generalization)
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    HypothesisResult,
    HypothesisStatus,
    LearningScope,
    ScopedLearning,
)

logger = logging.getLogger(__name__)


class GeneralizabilityScopeDeterminer:
    """Determines the scope at which each learning should be applied."""

    def __init__(self, config=None):
        self.config = config or get_dcil_config()

    def determine_scope(
        self,
        finding: HypothesisResult,
        evidence_vectors: List[EffectObservation],
    ) -> ScopedLearning:
        """
        Determine the generalizability scope of a finding using
        DerSimonian-Laird random-effects meta-analysis.

        evidence_vectors: list of observations of this finding across
            different campaigns, archetypes, or categories. Each has
            an effect size and its variance (or sample size from which
            variance is estimated).
        """
        if len(evidence_vectors) < self.config.min_studies_for_meta_analysis:
            return ScopedLearning(
                finding_id=f"SL-{uuid.uuid4().hex[:8]}",
                finding_type=finding.hypothesis_name,
                statement=finding.finding,
                scope=LearningScope.CAMPAIGN_SPECIFIC,
                i_squared=100.0,
                tau_squared=0.0,
                effect_size=finding.effect_size,
                n_studies=len(evidence_vectors),
                affected_campaigns=[ev.campaign_id for ev in evidence_vectors if ev.campaign_id],
                source_hypothesis_id=finding.hypothesis_id,
            )

        # Run DerSimonian-Laird
        result = dersimonian_laird(evidence_vectors)

        # Determine scope from I²
        i2 = result["i_squared"]
        scope = self._i2_to_scope(i2)

        # Identify affected entities based on scope
        affected_archetypes = list(set(ev.archetype for ev in evidence_vectors if ev.archetype))
        affected_categories = list(set(ev.category for ev in evidence_vectors if ev.category))
        affected_campaigns = list(set(ev.campaign_id for ev in evidence_vectors if ev.campaign_id))

        # Build Neo4j updates based on scope
        neo4j_updates = self._build_neo4j_updates(
            scope, result, finding,
            affected_archetypes, affected_categories,
        )

        # Build propagation config for KPN
        propagation_config = self._build_propagation_config(scope, result)

        return ScopedLearning(
            finding_id=f"SL-{uuid.uuid4().hex[:8]}",
            finding_type=finding.hypothesis_name,
            statement=finding.finding,
            scope=scope,
            i_squared=i2,
            tau_squared=result["tau_squared"],
            effect_size=result["pooled_effect"],
            confidence_interval=(result["ci_lower"], result["ci_upper"]),
            n_studies=len(evidence_vectors),
            affected_archetypes=affected_archetypes,
            affected_categories=affected_categories,
            affected_campaigns=affected_campaigns,
            neo4j_updates=neo4j_updates,
            propagation_config=propagation_config,
            source_hypothesis_id=finding.hypothesis_id,
        )

    def _i2_to_scope(self, i_squared: float) -> LearningScope:
        """Map I² heterogeneity to learning scope."""
        if i_squared < self.config.i_squared_system_wide:
            return LearningScope.SYSTEM_WIDE
        elif i_squared < self.config.i_squared_category_archetype_split:
            return LearningScope.CATEGORY_LEVEL
        elif i_squared < self.config.i_squared_campaign_specific:
            return LearningScope.ARCHETYPE_LEVEL
        else:
            return LearningScope.CAMPAIGN_SPECIFIC

    def _build_neo4j_updates(
        self,
        scope: LearningScope,
        meta_result: Dict[str, Any],
        finding: HypothesisResult,
        archetypes: List[str],
        categories: List[str],
    ) -> List[Dict[str, Any]]:
        """Build Neo4j Cypher mutations based on scope."""
        updates = []
        effect = meta_result["pooled_effect"]

        if scope == LearningScope.SYSTEM_WIDE:
            # Update global mechanism priors
            updates.append({
                "scope": "system_wide",
                "description": f"Update global priors based on: {finding.finding}",
                "cypher": (
                    "MATCH (a:CustomerArchetype)-[r:RESPONDS_TO]->(m:CognitiveMechanism) "
                    "SET r.effectiveness = r.effectiveness * (1 + $effect_modifier), "
                    "r.updated_at = datetime() "
                ),
                "params": {"effect_modifier": min(0.1, effect * 0.05)},
            })

        elif scope == LearningScope.CATEGORY_LEVEL:
            for cat in categories:
                updates.append({
                    "scope": "category",
                    "category": cat,
                    "description": f"Update category '{cat}' priors",
                    "cypher": (
                        "MATCH (bp:BayesianPrior {category: $category}) "
                        "SET bp.posterior_mean = bp.alpha / (bp.alpha + bp.beta), "
                        "bp.updated_at = datetime() "
                    ),
                    "params": {"category": cat},
                })

        elif scope == LearningScope.ARCHETYPE_LEVEL:
            for arch in archetypes:
                updates.append({
                    "scope": "archetype",
                    "archetype": arch,
                    "description": f"Update archetype '{arch}' priors",
                    "cypher": (
                        "MATCH (a:CustomerArchetype {name: $archetype})-[r:RESPONDS_TO]->(m:CognitiveMechanism) "
                        "SET r.effectiveness = r.effectiveness * (1 + $effect_modifier), "
                        "r.updated_at = datetime() "
                    ),
                    "params": {"archetype": arch, "effect_modifier": min(0.1, effect * 0.05)},
                })

        # Campaign-specific: no Neo4j updates (changes stay in campaign config only)
        return updates

    def _build_propagation_config(
        self,
        scope: LearningScope,
        meta_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build KPN propagation config based on scope."""
        if scope == LearningScope.SYSTEM_WIDE:
            return {
                "max_hops": 5,
                "amplitude": 1.0,
                "signal_type": "SCOPED_LEARNING",
                "scope_filter": None,
            }
        elif scope == LearningScope.CATEGORY_LEVEL:
            return {
                "max_hops": 3,
                "amplitude": 0.8,
                "signal_type": "SCOPED_LEARNING",
                "scope_filter": "category",
            }
        elif scope == LearningScope.ARCHETYPE_LEVEL:
            return {
                "max_hops": 2,
                "amplitude": 0.6,
                "signal_type": "SCOPED_LEARNING",
                "scope_filter": "archetype",
            }
        else:
            return {
                "max_hops": 1,
                "amplitude": 0.3,
                "signal_type": "SCOPED_LEARNING",
                "scope_filter": "campaign",
            }


# ---------------------------------------------------------------------------
# Effect observation for meta-analysis
# ---------------------------------------------------------------------------

class EffectObservation:
    """One observation of a finding's effect in a specific context."""

    def __init__(
        self,
        effect_size: float,
        variance: float = 0.0,
        sample_size: int = 0,
        effect_type: str = "",
        campaign_id: str = "",
        archetype: str = "",
        category: str = "",
        mechanism: str = "",
    ):
        self.effect_size = effect_size
        self.effect_type = effect_type  # "proportion", "proportion_difference", "rate_ratio", "mean_difference"
        self.sample_size = sample_size
        self.campaign_id = campaign_id
        self.archetype = archetype
        self.category = category
        self.mechanism = mechanism

        if variance > 0:
            self.variance = variance
        elif sample_size > 1:
            self.variance = _estimate_variance(effect_size, sample_size, effect_type)
        else:
            self.variance = 1.0


def _estimate_variance(effect: float, n: int, effect_type: str) -> float:
    """Estimate within-study variance based on effect type.

    Different effect types have different variance structures:
    - Raw proportion: Var = p(1-p)/n
    - Difference of proportions: Var = p1(1-p1)/n1 + p2(1-p2)/n2 ≈ 2*p(1-p)/n
    - Rate ratio (CPA ratio): Var ≈ (1/events1 + 1/events2)  (delta method on log-ratio)
    - Mean difference: Var ≈ 2*s²/n (assume equal variance groups)
    """
    if effect_type == "proportion" and 0 < abs(effect) < 1:
        p = max(0.001, min(0.999, abs(effect)))
        return (p * (1 - p)) / n

    if effect_type == "proportion_difference":
        # For a difference of two proportions: Var ≈ 2*p_avg*(1-p_avg)/n
        # Use |effect| as estimate of the underlying proportion scale
        p_avg = max(0.01, min(0.5, abs(effect) / 2 + 0.05))
        return 2 * p_avg * (1 - p_avg) / n

    if effect_type == "rate_ratio":
        # Delta method: Var(log(RR)) ≈ 1/a + 1/b where a,b are event counts
        # Conservative: assume events ≈ effect * n (very rough)
        events = max(1, int(abs(effect) * n * 0.1))
        return 1.0 / events + 1.0 / max(1, n - events)

    if effect_type == "mean_difference":
        # Assume pooled SD ≈ |effect| * 2 (moderate signal-to-noise)
        sd_estimate = max(0.01, abs(effect) * 2)
        return 2 * (sd_estimate ** 2) / n

    # Fallback: for unknown types, use a conservative estimate
    # that doesn't assume the effect is a proportion
    if 0 < abs(effect) < 1:
        p = max(0.001, min(0.999, abs(effect)))
        return (p * (1 - p)) / n
    else:
        sd_estimate = max(0.01, abs(effect) * 0.5)
        return (sd_estimate ** 2) / n


# ---------------------------------------------------------------------------
# DerSimonian-Laird random-effects meta-analysis
# ---------------------------------------------------------------------------

def dersimonian_laird(
    observations: List[EffectObservation],
) -> Dict[str, Any]:
    """
    DerSimonian-Laird random-effects meta-analysis.

    Returns:
        pooled_effect: weighted mean effect size
        tau_squared: between-study variance
        i_squared: heterogeneity percentage (0-100)
        q_statistic: Cochran's Q
        ci_lower, ci_upper: 95% confidence interval for pooled effect
        weights: per-study random-effects weights
    """
    k = len(observations)
    if k == 0:
        return {"pooled_effect": 0, "tau_squared": 0, "i_squared": 100,
                "q_statistic": 0, "ci_lower": 0, "ci_upper": 0, "weights": []}

    if k == 1:
        obs = observations[0]
        se = math.sqrt(obs.variance) if obs.variance > 0 else 0.5
        return {
            "pooled_effect": obs.effect_size,
            "tau_squared": 0,
            "i_squared": 0,
            "q_statistic": 0,
            "ci_lower": obs.effect_size - 1.96 * se,
            "ci_upper": obs.effect_size + 1.96 * se,
            "weights": [1.0],
        }

    # Step 1: Fixed-effect weights (inverse variance)
    w_fe = []
    for obs in observations:
        v = obs.variance if obs.variance > 0 else 1.0
        w_fe.append(1.0 / v)

    sum_w = sum(w_fe)
    if sum_w <= 0:
        return {"pooled_effect": 0, "tau_squared": 0, "i_squared": 100,
                "q_statistic": 0, "ci_lower": 0, "ci_upper": 0, "weights": []}

    # Step 2: Fixed-effect pooled estimate
    y_bar_fe = sum(w_fe[i] * observations[i].effect_size for i in range(k)) / sum_w

    # Step 3: Cochran's Q statistic
    q = sum(w_fe[i] * (observations[i].effect_size - y_bar_fe) ** 2 for i in range(k))

    # Step 4: Between-study variance (tau²)
    c = sum_w - sum(w ** 2 for w in w_fe) / sum_w
    tau_sq = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0

    # Step 5: I² heterogeneity
    i_squared = max(0.0, (q - (k - 1)) / q * 100) if q > 0 else 0.0

    # Step 6: Random-effects weights
    w_re = []
    for obs in observations:
        v = obs.variance if obs.variance > 0 else 1.0
        w_re.append(1.0 / (v + tau_sq))

    sum_w_re = sum(w_re)
    if sum_w_re <= 0:
        return {"pooled_effect": y_bar_fe, "tau_squared": tau_sq,
                "i_squared": i_squared, "q_statistic": q,
                "ci_lower": y_bar_fe, "ci_upper": y_bar_fe, "weights": w_re}

    # Step 7: Random-effects pooled estimate
    pooled = sum(w_re[i] * observations[i].effect_size for i in range(k)) / sum_w_re

    # Step 8: Confidence interval
    se_pooled = math.sqrt(1.0 / sum_w_re)
    ci_lower = pooled - 1.96 * se_pooled
    ci_upper = pooled + 1.96 * se_pooled

    # Normalize weights to sum to 1 for interpretability
    weight_sum = sum(w_re)
    normalized_weights = [w / weight_sum for w in w_re] if weight_sum > 0 else w_re

    return {
        "pooled_effect": pooled,
        "tau_squared": tau_sq,
        "i_squared": i_squared,
        "q_statistic": q,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "weights": normalized_weights,
    }
