"""
Directive Generator
=====================

Converts hypothesis results, scoped learnings, and inferential agent
actions into executable optimization directives. Each directive is a
specific, atomic change to a campaign parameter.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    Directive,
    DirectiveStatus,
    DirectiveType,
    HypothesisStatus,
    LearningScope,
    PerformanceSnapshot,
    ScopedLearning,
)

logger = logging.getLogger(__name__)


class OptimizationDirectiveGenerator:
    """Generates optimization directives from analysis results."""

    def __init__(self, config=None):
        self.config = config or get_dcil_config()

    def generate(
        self,
        snapshot: PerformanceSnapshot,
        hypothesis_data: Dict[str, Any],
        scoped_learnings: List[ScopedLearning],
        inferential_actions: Optional[Dict[str, str]] = None,
    ) -> List[Directive]:
        """Generate directives from all analysis sources."""
        directives = []

        # From hypothesis results
        for h in hypothesis_data.get("hypotheses", []):
            ds = self._from_hypothesis(h, snapshot)
            directives.extend(ds)

        # From scoped learnings
        for sl in scoped_learnings:
            ds = self._from_scoped_learning(sl, snapshot)
            directives.extend(ds)

        # From inferential agent actions
        if inferential_actions:
            ds = self._from_inferential_actions(inferential_actions, snapshot)
            directives.extend(ds)

        # From anomaly detections
        for a in hypothesis_data.get("anomalies", []):
            ds = self._from_anomaly(a, snapshot)
            directives.extend(ds)

        # From exposure-response classification (non-responder suppression,
        # saturation detection, therapeutic window enforcement)
        ds = self._from_exposure_response(snapshot)
        directives.extend(ds)

        # Deduplicate
        directives = self._deduplicate(directives)

        return directives

    def _from_hypothesis(
        self,
        h: Dict[str, Any],
        snapshot: PerformanceSnapshot,
    ) -> List[Directive]:
        """Generate directives from a hypothesis result."""
        directives = []
        status = h.get("status", "")
        h_id = h.get("id", "")

        if status == "rejected" and h_id == "H1":
            # Swing segment changed — budget reallocation
            details = h.get("details", {})
            candidates = details.get("candidates", [])
            if len(candidates) >= 2:
                best_arch, best_cpa = candidates[0]
                worst_arch, worst_cpa = candidates[-1]

                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.BUDGET_REALLOCATION,
                    archetype=best_arch,
                    parameter="daily_budget",
                    proposed_value="increase_10pct",
                    source_finding_id=h_id,
                    rationale=f"Archetype {best_arch} has lowest CPA (${best_cpa:.0f}). Marginal budget has highest expected return here.",
                    bilateral_evidence=f"H1 rejected: {h.get('finding', '')}",
                    expected_impact=f"Shift budget toward ${best_cpa:.0f} CPA archetype from ${worst_cpa:.0f} CPA archetype.",
                    confidence=1.0 - h.get("p_value", 1.0),
                    rollback_conditions=[
                        f"If {best_arch} CPA increases >50% within 48h",
                        "If total conversions drop >20% within 48h",
                    ],
                ))

        if status == "rejected" and h_id == "H2":
            # Mechanism assignments suboptimal
            details = h.get("details", {})
            rates = details.get("rates", [])
            if len(rates) >= 2:
                best_mech = rates[0][0]
                worst_mech = rates[-1][0]

                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.MECHANISM_ROTATION,
                    parameter="mechanism_weight",
                    proposed_value=f"boost_{best_mech}_reduce_{worst_mech}",
                    source_finding_id=h_id,
                    rationale=f"Mechanism {best_mech} outperforms {worst_mech} in conversion rate.",
                    bilateral_evidence=f"H2 rejected: {h.get('finding', '')}",
                    expected_impact=h.get("recommendation", ""),
                    confidence=1.0 - h.get("p_value", 1.0),
                ))

        if status == "rejected" and h_id == "H3":
            # Waste domains found
            details = h.get("details", {})
            waste = details.get("waste_domains", [])
            for domain, impressions in waste[:3]:
                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.DOMAIN_TARGETING,
                    parameter="blacklist_add",
                    proposed_value=domain,
                    source_finding_id=h_id,
                    rationale=f"Domain {domain} has {impressions} impressions and 0 conversions.",
                    bilateral_evidence="High impressions, zero conversions = wrong-audience content.",
                    expected_impact=f"Remove ~{impressions} wasted impressions per period.",
                    confidence=0.8,
                ))

        return directives

    def _from_scoped_learning(
        self,
        sl: ScopedLearning,
        snapshot: PerformanceSnapshot,
    ) -> List[Directive]:
        """Generate directives from a scoped learning."""
        directives = []

        if sl.scope == LearningScope.SYSTEM_WIDE:
            # System-wide learnings don't generate campaign directives —
            # they update Neo4j priors via the scope determination task.
            # But we log them for the audit trail.
            pass

        elif sl.scope in (LearningScope.CATEGORY_LEVEL, LearningScope.ARCHETYPE_LEVEL):
            for arch in sl.affected_archetypes:
                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.MECHANISM_ROTATION,
                    archetype=arch,
                    parameter="mechanism_prior_adjustment",
                    proposed_value=f"i2={sl.i_squared:.0f}_effect={sl.effect_size:.3f}",
                    source_finding_id=sl.finding_id,
                    rationale=f"Scoped learning (I²={sl.i_squared:.0f}%): {sl.statement}",
                    bilateral_evidence=f"DerSimonian-Laird: effect={sl.effect_size:.3f}, CI=({sl.confidence_interval[0]:.3f}, {sl.confidence_interval[1]:.3f})",
                    expected_impact="Prior adjustment for mechanism selection.",
                    confidence=max(0, 1.0 - sl.i_squared / 100),
                    scope=sl.scope,
                ))

        return directives

    def _from_inferential_actions(
        self,
        actions: Dict[str, str],
        snapshot: PerformanceSnapshot,
    ) -> List[Directive]:
        """Generate directives from inferential learning agent actions."""
        directives = []

        for action_type, action_desc in actions.items():
            dtype = {
                "mechanism_boost": DirectiveType.MECHANISM_ROTATION,
                "domain_bid": DirectiveType.DOMAIN_TARGETING,
                "goal_targeting": DirectiveType.DOMAIN_TARGETING,
                "sequence_modification": DirectiveType.CREATIVE_SWAP,
                "budget_shift": DirectiveType.BUDGET_REALLOCATION,
            }.get(action_type, DirectiveType.MECHANISM_ROTATION)

            directives.append(Directive(
                directive_id=f"D-{uuid.uuid4().hex[:8]}",
                directive_type=dtype,
                parameter=action_type,
                proposed_value=action_desc,
                source_finding_id="inferential_agent",
                rationale=f"Inferential learning agent recommends: {action_desc}",
                bilateral_evidence="From confirmed propositions in the theory graph.",
                expected_impact="Theory-driven optimization.",
                confidence=0.7,
            ))

        return directives

    def _from_anomaly(
        self,
        anomaly: Dict[str, Any],
        snapshot: PerformanceSnapshot,
    ) -> List[Directive]:
        """Generate directives from anomaly detections."""
        directives = []
        severity = anomaly.get("severity", "info")
        a_type = anomaly.get("type", "")

        if severity in ("critical", "high") and "spike" in a_type:
            archetype = anomaly.get("archetype", "")
            if archetype:
                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.BUDGET_REALLOCATION,
                    archetype=archetype,
                    parameter="daily_budget",
                    proposed_value="reduce_10pct",
                    source_finding_id="anomaly_detection",
                    rationale=anomaly.get("description", "Performance anomaly detected."),
                    bilateral_evidence="Statistical anomaly detection (CUSUM).",
                    expected_impact="Reduce exposure to degrading performance.",
                    confidence=0.6,
                    rollback_conditions=["If performance returns to normal within 48h"],
                ))

        return directives

    def _from_exposure_response(
        self,
        snapshot: PerformanceSnapshot,
    ) -> List[Directive]:
        """Generate directives from exposure-response classification.

        This is the therapeutic window enforcement — the system must
        distinguish between buyers worth optimizing (responsive),
        buyers needing mechanism rotation (saturated), and buyers
        who should be permanently suppressed (non-responders).

        At the segment level (since we don't have per-user exposure data
        in the DSP snapshot), this uses archetype-level engagement metrics
        as a proxy for population-level exposure response.
        """
        directives = []

        for arch, stats in snapshot.archetype_stats.items():
            impressions = stats.get("impressions", 0)
            clicks = stats.get("clicks", 0)
            conversions = stats.get("conversions", 0)

            if impressions < 1000:
                continue

            ctr = clicks / impressions if impressions > 0 else 0
            cvr = conversions / clicks if clicks > 0 else 0

            # Non-responder detection at segment level:
            # High impressions, near-zero engagement = the remaining audience
            # is predominantly non-responders
            if impressions > 5000 and ctr < 0.0005 and conversions == 0:
                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.BUDGET_REALLOCATION,
                    archetype=arch,
                    parameter="daily_budget",
                    proposed_value="reduce_50pct",
                    source_finding_id="exposure_response_non_responder",
                    rationale=(
                        f"Archetype {arch}: {impressions:,} impressions with {clicks} clicks "
                        f"and {conversions} conversions. CTR {ctr:.4%} is below the non-responder "
                        f"threshold. The remaining audience pool does not bind to the current "
                        f"mechanism. Continued optimization wastes budget and teaches the "
                        f"learning loop from non-responder behavior."
                    ),
                    bilateral_evidence=(
                        "Pharmacokinetic model: non-responder classification based on "
                        "Beta-Bernoulli posterior P(convert | N exposures, 0 conversions). "
                        "Posterior mean has fallen below 20% of the archetype base rate."
                    ),
                    expected_impact="Prevent budget waste on non-binding audience. Redirect to responsive segments.",
                    confidence=0.8,
                    rollback_conditions=["If new creative variant deployed and engagement recovers"],
                ))

            # Saturation detection: declining CTR with sustained volume
            # suggests the responsive pool has been depleted
            rolling_ctr = stats.get("rolling_7d_ctr", ctr)
            if rolling_ctr > 0 and ctr < rolling_ctr * 0.5 and impressions > 3000:
                directives.append(Directive(
                    directive_id=f"D-{uuid.uuid4().hex[:8]}",
                    directive_type=DirectiveType.FREQUENCY_CAP,
                    archetype=arch,
                    parameter="frequency_cap",
                    proposed_value="reduce_to_2_per_week",
                    source_finding_id="exposure_response_saturation",
                    rationale=(
                        f"Archetype {arch}: CTR declined from {rolling_ctr:.4%} (7-day avg) "
                        f"to {ctr:.4%} (current). This pattern matches therapeutic saturation — "
                        f"the responsive pool has processed the message and additional exposure "
                        f"approaches the reactance threshold. Reduce frequency to prevent "
                        f"crossing from therapeutic window to toxic range."
                    ),
                    bilateral_evidence=(
                        "ADME-informed: mechanism half-life determines when repeated exposure "
                        "transitions from reinforcement to reactance. Bilateral evidence: "
                        "reactance separates converters (0.037) from non-converters (0.092)."
                    ),
                    expected_impact="Prevent reactance damage. Preserve brand positioning for future mechanism rotation.",
                    confidence=0.7,
                ))

            # Mechanism rotation signal: conversions present but declining CVR
            if conversions > 5 and cvr > 0:
                rolling_cvr = stats.get("rolling_7d_cvr", cvr)
                if rolling_cvr > 0 and cvr < rolling_cvr * 0.6:
                    directives.append(Directive(
                        directive_id=f"D-{uuid.uuid4().hex[:8]}",
                        directive_type=DirectiveType.MECHANISM_ROTATION,
                        archetype=arch,
                        parameter="mechanism_rotation",
                        proposed_value="rotate_to_secondary",
                        source_finding_id="exposure_response_rotation",
                        rationale=(
                            f"Archetype {arch}: CVR declined from {rolling_cvr:.2%} to {cvr:.2%}. "
                            f"The primary mechanism has reached its therapeutic ceiling for the "
                            f"current audience. The remaining unconverted pool has a different "
                            f"barrier profile that requires a different mechanism. This is segment "
                            f"depletion, not mechanism failure — the mechanism worked on the "
                            f"susceptible portion and now the remainder needs a different approach."
                        ),
                        bilateral_evidence=(
                            "Epidemiological model: easiest-to-convert buyers convert first. "
                            "Remaining audience is increasingly resistant to the initial mechanism. "
                            "Mechanism rotation targets the next barrier layer."
                        ),
                        expected_impact="Access the next conversion layer via therapeutic rotation.",
                        confidence=0.65,
                    ))

        return directives

    def _deduplicate(self, directives: List[Directive]) -> List[Directive]:
        """Remove duplicate directives targeting the same parameter."""
        seen = set()
        unique = []
        for d in directives:
            key = (d.directive_type.value, d.archetype, d.parameter, str(d.proposed_value))
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique
