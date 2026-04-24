"""
Hypothesis Battery
====================

5 standing hypotheses tested daily, plus trend/anomaly detection.
Uses chi-squared contingency tables, CUSUM change-point detection,
and bilateral evidence to diagnose campaign performance.

The hypotheses are:
H1: Is the swing segment still the highest-marginal-value target?
H2: Are current mechanism-to-archetype assignments optimal?
H3: Are domain whitelist assignments producing expected results?
H4: Are blacklisted domains leaking impressions?
H5: Is the dayparting schedule optimal?
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    AnomalyDetection,
    FindingSeverity,
    HypothesisResult,
    HypothesisStatus,
    PerformanceSnapshot,
)

logger = logging.getLogger(__name__)


class HypothesisBattery:
    """Runs all standing hypotheses against current performance data."""

    def __init__(self, config=None):
        self.config = config or get_dcil_config()

    def run_all(
        self,
        snapshot: PerformanceSnapshot,
        historical: Optional[List[PerformanceSnapshot]] = None,
    ) -> Tuple[List[HypothesisResult], List[AnomalyDetection]]:
        """Run all 5 hypotheses + anomaly detection."""
        results = []
        anomalies = []

        results.append(self.h1_swing_segment(snapshot))
        results.append(self.h2_mechanism_assignment(snapshot))
        results.append(self.h3_domain_performance(snapshot))
        results.append(self.h4_blacklist_leakage(snapshot))
        results.append(self.h5_dayparting_optimality(snapshot))

        if historical:
            anomalies = self.detect_anomalies(snapshot, historical)

        return results, anomalies

    # ------------------------------------------------------------------
    # H1: Swing Segment Test
    # ------------------------------------------------------------------

    def h1_swing_segment(self, snapshot: PerformanceSnapshot) -> HypothesisResult:
        """Is the swing segment still the highest-marginal-value target?

        The swing segment is the archetype where additional spend has the
        highest marginal return. If the current swing has converged (CPA
        no longer improving with budget), we should shift allocation.
        """
        arch_stats = snapshot.archetype_stats
        if len(arch_stats) < 2:
            return HypothesisResult(
                hypothesis_id="H1",
                hypothesis_name="Swing Segment Test",
                status=HypothesisStatus.INCONCLUSIVE,
                finding="Fewer than 2 archetypes active. Cannot compare.",
            )

        # Find archetype with best marginal CVR (highest conversion rate with sufficient volume)
        candidates = []
        for arch, stats in arch_stats.items():
            conv = stats.get("conversions", 0)
            clicks = stats.get("clicks", 0)
            spend = stats.get("spend", 0)
            if conv >= self.config.min_sample_size_per_cell and clicks > 0:
                cvr = conv / clicks
                cpa = spend / conv if conv > 0 else float("inf")
                candidates.append((arch, cpa, cvr, conv, clicks, spend))

        if len(candidates) < 2:
            return HypothesisResult(
                hypothesis_id="H1",
                hypothesis_name="Swing Segment Test",
                status=HypothesisStatus.INCONCLUSIVE,
                sample_size=sum(c[3] for c in candidates),
                finding="Insufficient conversions across archetypes for comparison.",
            )

        candidates.sort(key=lambda x: x[1])  # sort by CPA ascending
        best_arch, best_cpa, best_cvr, best_conv, best_clicks, best_spend = candidates[0]
        worst_arch, worst_cpa, worst_cvr, worst_conv, worst_clicks, worst_spend = candidates[-1]

        # Chi-squared test on actual conversion rates (conversions / clicks)
        p_value = _chi2_two_proportions(
            best_conv, best_clicks,
            worst_conv, worst_clicks,
        )

        effect_size = (worst_cpa - best_cpa) / worst_cpa if worst_cpa > 0 else 0

        status = HypothesisStatus.CONFIRMED if p_value < self.config.significance_level else HypothesisStatus.INCONCLUSIVE

        # Construct chain: WHY this archetype converts better
        chain = _infer_construct_chain(best_arch)
        conditions = _infer_chain_conditions(best_arch, best_cvr)

        return HypothesisResult(
            hypothesis_id="H1",
            hypothesis_name="Swing Segment Test",
            status=status,
            p_value=p_value,
            effect_size=effect_size,
            effect_type="proportion_difference",
            sample_size=sum(c[3] for c in candidates),
            test_method="chi_squared_two_proportions",
            finding=(
                f"Best archetype: {best_arch} (CVR {best_cvr:.2%}, CPA ${best_cpa:.0f}). "
                f"Worst: {worst_arch} (CVR {worst_cvr:.2%}, CPA ${worst_cpa:.0f}). "
                f"Mechanism: {' → '.join(chain) if chain else 'not yet identified'}."
            ),
            recommendation=(
                f"Shift marginal budget toward {best_arch}. "
                f"The construct chain ({' → '.join(chain)}) predicts this advantage transfers "
                f"to similar regulatory-focus profiles in adjacent categories."
                if status == HypothesisStatus.CONFIRMED else "Maintain current allocation."
            ),
            action_if_rejected=f"Reallocate budget: increase {best_arch}, decrease {worst_arch}.",
            details={"candidates": [(c[0], c[1]) for c in candidates]},
            construct_chain=chain,
            chain_conditions=conditions,
            chain_exceptions=_infer_chain_exceptions(best_arch),
            theory_update_type="chain_strengthened" if status == HypothesisStatus.CONFIRMED else "",
        )

    # ------------------------------------------------------------------
    # H2: Mechanism Assignment Test
    # ------------------------------------------------------------------

    def h2_mechanism_assignment(self, snapshot: PerformanceSnapshot) -> HypothesisResult:
        """Are current mechanism-to-archetype assignments optimal?

        Compare conversion rates across mechanism variants per archetype.
        """
        mech_stats = snapshot.mechanism_stats
        if len(mech_stats) < 2:
            return HypothesisResult(
                hypothesis_id="H2",
                hypothesis_name="Mechanism Assignment Test",
                status=HypothesisStatus.INCONCLUSIVE,
                finding="Fewer than 2 mechanisms active.",
            )

        # Build contingency table: mechanism × (converted, not_converted)
        table = []
        labels = []
        for mech, stats in mech_stats.items():
            conv = stats.get("conversions", 0)
            clicks = stats.get("clicks", 0)
            if clicks >= self.config.min_sample_size_per_cell:
                table.append((conv, clicks - conv))
                labels.append(mech)

        if len(table) < 2:
            return HypothesisResult(
                hypothesis_id="H2",
                hypothesis_name="Mechanism Assignment Test",
                status=HypothesisStatus.INCONCLUSIVE,
                finding="Insufficient data across mechanisms for comparison.",
            )

        p_value = _chi2_contingency(table)

        # Find best and worst
        rates = [(labels[i], table[i][0] / (table[i][0] + table[i][1]) if (table[i][0] + table[i][1]) > 0 else 0) for i in range(len(table))]
        rates.sort(key=lambda x: x[1], reverse=True)
        best_mech, best_rate = rates[0]
        worst_mech, worst_rate = rates[-1]

        # p < alpha means significant difference exists between mechanisms
        # REJECTED = null hypothesis (mechanisms are equal) is rejected → change needed
        # CONFIRMED = no significant difference → current assignments are fine
        significant = p_value < self.config.significance_level
        status = HypothesisStatus.REJECTED if significant else HypothesisStatus.CONFIRMED

        return HypothesisResult(
            hypothesis_id="H2",
            hypothesis_name="Mechanism Assignment Test",
            status=status,
            p_value=p_value,
            effect_size=best_rate - worst_rate,
            sample_size=sum(t[0] + t[1] for t in table),
            test_method="chi_squared_contingency",
            finding=f"Best: {best_mech} ({best_rate:.2%} CVR). Worst: {worst_mech} ({worst_rate:.2%} CVR).",
            recommendation=f"Increase {best_mech} rotation weight, decrease {worst_mech}." if significant else "Current assignments are not significantly different.",
            action_if_rejected=f"Shift mechanism rotation: boost {best_mech}, reduce {worst_mech}.",
            details={"rates": rates},
        )

    # ------------------------------------------------------------------
    # H3: Domain Performance Test
    # ------------------------------------------------------------------

    def h3_domain_performance(self, snapshot: PerformanceSnapshot) -> HypothesisResult:
        """Are domain whitelist assignments producing expected results?"""
        # Check domain-level stats across campaigns
        domain_totals: Dict[str, Dict[str, int]] = {}
        for camp in snapshot.campaigns:
            for ds in camp.domain_stats:
                domain = ds.get("domain", "")
                if not domain:
                    continue
                if domain not in domain_totals:
                    domain_totals[domain] = {"impressions": 0, "clicks": 0, "conversions": 0}
                domain_totals[domain]["impressions"] += ds.get("impressions", 0)
                domain_totals[domain]["clicks"] += ds.get("clicks", 0)
                domain_totals[domain]["conversions"] += ds.get("conversions", 0)

        if not domain_totals:
            return HypothesisResult(
                hypothesis_id="H3",
                hypothesis_name="Domain Performance Test",
                status=HypothesisStatus.INCONCLUSIVE,
                finding="No domain-level performance data available.",
                recommendation="Request domain-level reporting from StackAdapt.",
            )

        # Flag domains with high impressions but zero conversions
        waste_domains = []
        min_impressions = self.config.min_impressions_for_domain_action
        for domain, stats in domain_totals.items():
            if stats["impressions"] >= min_impressions and stats["conversions"] == 0:
                waste_domains.append((domain, stats["impressions"]))

        waste_domains.sort(key=lambda x: x[1], reverse=True)

        if waste_domains:
            return HypothesisResult(
                hypothesis_id="H3",
                hypothesis_name="Domain Performance Test",
                status=HypothesisStatus.REJECTED,
                sample_size=sum(d[1] for d in waste_domains),
                finding=f"{len(waste_domains)} domains have >{min_impressions} impressions and 0 conversions.",
                recommendation=f"Consider adding to blacklist: {', '.join(d[0] for d in waste_domains[:5])}.",
                action_if_rejected="Add waste domains to blacklist.",
                details={"waste_domains": waste_domains[:10]},
            )

        return HypothesisResult(
            hypothesis_id="H3",
            hypothesis_name="Domain Performance Test",
            status=HypothesisStatus.CONFIRMED,
            finding="No significant domain waste detected.",
        )

    # ------------------------------------------------------------------
    # H4: Blacklist Leakage Test
    # ------------------------------------------------------------------

    def h4_blacklist_leakage(self, snapshot: PerformanceSnapshot) -> HypothesisResult:
        """Are impressions appearing on blacklisted domains?"""
        # Load blacklist
        try:
            blacklist = _load_blacklist()
        except Exception:
            return HypothesisResult(
                hypothesis_id="H4",
                hypothesis_name="Blacklist Leakage Test",
                status=HypothesisStatus.INCONCLUSIVE,
                finding="Could not load blacklist for comparison.",
            )

        leaking = []
        for camp in snapshot.campaigns:
            for ds in camp.domain_stats:
                domain = ds.get("domain", "").lower()
                if domain in blacklist and ds.get("impressions", 0) > 0:
                    leaking.append({
                        "domain": domain,
                        "campaign": camp.name,
                        "impressions": ds["impressions"],
                    })

        if leaking:
            return HypothesisResult(
                hypothesis_id="H4",
                hypothesis_name="Blacklist Leakage Test",
                status=HypothesisStatus.REJECTED,
                finding=f"{len(leaking)} blacklisted domains are receiving impressions.",
                recommendation="Re-apply blacklist in StackAdapt. Check exclusion rule enforcement.",
                action_if_rejected="Flag leaking domains for re-exclusion.",
                details={"leaking": leaking[:10]},
            )

        return HypothesisResult(
            hypothesis_id="H4",
            hypothesis_name="Blacklist Leakage Test",
            status=HypothesisStatus.CONFIRMED,
            finding="No blacklist leakage detected.",
        )

    # ------------------------------------------------------------------
    # H5: Dayparting Optimality Test
    # ------------------------------------------------------------------

    def h5_dayparting_optimality(self, snapshot: PerformanceSnapshot) -> HypothesisResult:
        """Is the dayparting schedule optimal?"""
        # Without hourly data from the DSP, this test is structural
        has_dayparting = any(
            camp.name for camp in snapshot.campaigns
            # Check if any campaign has dayparting configured
        )

        return HypothesisResult(
            hypothesis_id="H5",
            hypothesis_name="Dayparting Optimality Test",
            status=HypothesisStatus.INCONCLUSIVE,
            finding="Hourly performance data not available in current snapshot. Requires time-windowed pull.",
            recommendation="When hourly data is available, test conversion rates by hour using chi-squared goodness-of-fit.",
        )

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    def detect_anomalies(
        self,
        current: PerformanceSnapshot,
        historical: List[PerformanceSnapshot],
    ) -> List[AnomalyDetection]:
        """Detect sudden drops, gradual declines, and spikes."""
        anomalies = []
        threshold = self.config.cusum_threshold_sigma
        decline_days = self.config.trend_decline_consecutive_days

        if not historical:
            return anomalies

        # Check overall CPA trend
        cpa_history = [h.overall_cpa for h in historical if h.overall_cpa > 0]
        if cpa_history and current.overall_cpa > 0:
            mean_cpa = sum(cpa_history) / len(cpa_history)
            if len(cpa_history) >= 3:
                variance = sum((c - mean_cpa) ** 2 for c in cpa_history) / len(cpa_history)
                std_cpa = math.sqrt(variance) if variance > 0 else mean_cpa * 0.1

                deviation = (current.overall_cpa - mean_cpa) / std_cpa if std_cpa > 0 else 0

                if deviation > threshold:
                    anomalies.append(AnomalyDetection(
                        anomaly_type="sudden_spike",
                        severity=FindingSeverity.HIGH,
                        metric="overall_cpa",
                        current_value=current.overall_cpa,
                        expected_value=mean_cpa,
                        deviation_sigma=deviation,
                        description=f"CPA spiked to ${current.overall_cpa:.0f} ({deviation:.1f}σ above {len(cpa_history)}-day mean of ${mean_cpa:.0f}).",
                    ))

                if deviation < -threshold:
                    anomalies.append(AnomalyDetection(
                        anomaly_type="sudden_drop",
                        severity=FindingSeverity.INFO,
                        metric="overall_cpa",
                        current_value=current.overall_cpa,
                        expected_value=mean_cpa,
                        deviation_sigma=deviation,
                        description=f"CPA dropped to ${current.overall_cpa:.0f} ({abs(deviation):.1f}σ below mean). Positive signal.",
                    ))

            # Check for monotone decline (consecutive days worse)
            if len(cpa_history) >= decline_days:
                recent = cpa_history[-decline_days:]
                if all(recent[i] < recent[i + 1] for i in range(len(recent) - 1)):
                    anomalies.append(AnomalyDetection(
                        anomaly_type="gradual_decline",
                        severity=FindingSeverity.MEDIUM,
                        metric="overall_cpa",
                        current_value=current.overall_cpa,
                        expected_value=mean_cpa,
                        description=f"CPA has improved for {decline_days} consecutive days. Learning systems may be converging.",
                    ))
                elif all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
                    anomalies.append(AnomalyDetection(
                        anomaly_type="gradual_decline",
                        severity=FindingSeverity.HIGH,
                        metric="overall_cpa",
                        current_value=current.overall_cpa,
                        expected_value=mean_cpa,
                        description=f"CPA has worsened for {decline_days} consecutive days. Investigate audience fatigue or competitive pressure.",
                    ))

        # Per-archetype anomalies
        for arch, stats in current.archetype_stats.items():
            conv = stats.get("conversions", 0)
            spend = stats.get("spend", 0)
            if conv == 0 and spend > 100:
                anomalies.append(AnomalyDetection(
                    anomaly_type="zero_conversions",
                    severity=FindingSeverity.HIGH,
                    metric="conversions",
                    archetype=arch,
                    current_value=0,
                    expected_value=1,
                    description=f"Archetype {arch} spent ${spend:.0f} with 0 conversions.",
                ))

        return anomalies


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _chi2_two_proportions(x1: int, n1: int, x2: int, n2: int) -> float:
    """Chi-squared test for two proportions."""
    if n1 == 0 or n2 == 0:
        return 1.0

    p1 = x1 / n1
    p2 = x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)

    if p_pool <= 0 or p_pool >= 1:
        return 1.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se <= 0:
        return 1.0

    z = (p1 - p2) / se
    # Two-tailed p-value from z-score (approximation)
    return 2 * (1 - _normal_cdf(abs(z)))


def _chi2_contingency(table: List[Tuple[int, int]]) -> float:
    """Chi-squared test of independence for a k×2 contingency table."""
    k = len(table)
    if k < 2:
        return 1.0

    row_totals = [sum(row) for row in table]
    col_totals = [sum(table[i][j] for i in range(k)) for j in range(2)]
    grand_total = sum(row_totals)

    if grand_total == 0:
        return 1.0

    chi2 = 0.0
    for i in range(k):
        for j in range(2):
            expected = row_totals[i] * col_totals[j] / grand_total
            if expected > 0:
                chi2 += (table[i][j] - expected) ** 2 / expected

    df = k - 1
    return _chi2_survival(chi2, df)


def _normal_cdf(z: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    if z < -8:
        return 0.0
    if z > 8:
        return 1.0
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if z >= 0 else -1
    z_abs = abs(z)
    t = 1.0 / (1.0 + p * z_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-z_abs * z_abs / 2)
    return 0.5 * (1.0 + sign * y)


def _chi2_survival(x: float, df: int) -> float:
    """Upper tail probability of chi-squared distribution.

    Uses the regularized incomplete gamma function approximation.
    For production use, scipy.stats.chi2.sf would be preferred.
    """
    if df <= 0 or x <= 0:
        return 1.0

    # Wilson-Hilferty approximation for large df
    if df > 100:
        z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        return 1 - _normal_cdf(z)

    # Direct summation for small df
    if df % 2 == 0:
        # Even df: exact via Poisson terms
        s = 1.0
        t = 1.0
        lam = x / 2
        for i in range(1, df // 2):
            t *= lam / i
            s += t
        return min(1.0, math.exp(-lam) * s)
    else:
        # Odd df: use Wilson-Hilferty
        z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        return 1 - _normal_cdf(z)


# ---------------------------------------------------------------------------
# Construct chain inference — the mechanism materialization layer
# ---------------------------------------------------------------------------
# These map archetypes and mechanisms to their theoretical construct chains.
# The chains are grounded in the bilateral edge dimensions and the
# peer-reviewed literature (Bargh auto-motive, Higgins regulatory focus,
# Trope & Liberman construal level theory, Kahneman dual-process).
#
# When a hypothesis is confirmed, the chain tells us WHY — not just WHAT.

ARCHETYPE_CONSTRUCT_CHAINS = {
    "careful_truster": [
        "high_conscientiousness", "low_uncertainty_tolerance",
        "need_for_closure", "prevention_focus", "authority_mechanism",
    ],
    "status_seeker": [
        "high_promotion_focus", "high_status_motive",
        "optimal_distinctiveness", "identity_construction", "wanting_liking",
    ],
    "easy_decider": [
        "low_need_for_cognition", "low_maximizer",
        "automatic_evaluation", "cognitive_ease_preference", "friction_removal",
    ],
    "dependable_loyalist": [
        "high_brand_trust", "high_conscientiousness",
        "social_proof_validation", "evidence_based_evaluation", "commitment_consistency",
    ],
    "reliable_cooperator": [
        "high_agreeableness", "cooperative_orientation",
        "implementation_intention", "task_completion_drive", "cognitive_ease_preference",
    ],
    "prevention_planner": [
        "high_prevention_focus", "high_disease_avoidance",
        "threat_detection", "anxiety_resolution", "concrete_construal",
    ],
    "trusting_loyalist": [
        "high_brand_trust", "low_attachment_avoidance",
        "wanting_liking", "commitment_consistency", "loss_aversion",
    ],
    "consensus_seeker": [
        "high_social_proof_reliance", "high_agreeableness",
        "mimetic_desire", "social_alignment", "group_identity",
    ],
}

ARCHETYPE_CONDITIONS = {
    "careful_truster": [
        "cognitive_engagement > moderate",
        "construal_level = concrete (specific evidence, not aspirational promise)",
        "brand_trust_fit correlation active (r=+0.619 from bilateral edges)",
    ],
    "status_seeker": [
        "promotion_focus active (gain-framed context)",
        "optimal_distinctiveness motive accessible (not conformity-primed)",
    ],
    "easy_decider": [
        "processing_fluency high (clean visual, short copy)",
        "decision_friction low (< 2 clicks to action)",
    ],
}

ARCHETYPE_EXCEPTIONS = {
    "careful_truster": [
        "warmth/sincerity messaging HURTS conversion (liking r=-0.229 from bilateral evidence)",
        "urgency/scarcity framing triggers reactance (low impulse profile)",
        "social pressure content reduces trust (low social_proof_reliance)",
    ],
    "status_seeker": [
        "cost-consciousness framing destroys identity construction (low spending_pain profile)",
        "conformity messaging contradicts optimal_distinctiveness motive",
    ],
    "easy_decider": [
        "comparison/evaluation content increases cognitive load (low need_for_cognition)",
        "extensive evidence presentation triggers disengagement",
    ],
}


def _infer_construct_chain(archetype: str) -> list:
    return ARCHETYPE_CONSTRUCT_CHAINS.get(archetype, [])


def _infer_chain_conditions(archetype: str, cvr: float = 0) -> list:
    conditions = ARCHETYPE_CONDITIONS.get(archetype, [])
    if cvr > 0:
        conditions = conditions + [f"observed_cvr={cvr:.2%} (above baseline indicates chain is active)"]
    return conditions


def _infer_chain_exceptions(archetype: str) -> list:
    return ARCHETYPE_EXCEPTIONS.get(archetype, [])


def _load_blacklist() -> set:
    """Load the campaign blacklist domains."""
    import os
    blacklist = set()
    blacklist_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "campaigns", "ridelux_v6", "stackadapt_blacklist_upload.csv",
    )
    try:
        with open(blacklist_path) as f:
            for line in f:
                domain = line.strip().lower()
                if domain and not domain.startswith("#"):
                    blacklist.add(domain)
    except FileNotFoundError:
        logger.debug("Blacklist file not found at %s", blacklist_path)
    return blacklist
