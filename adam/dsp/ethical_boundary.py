"""
DSP Enrichment Engine — Ethical Boundary Engine
=================================================

Enforces ethical constraints on psychological targeting.

Core principle: The same psychological knowledge that enables persuasion
also reveals vulnerability. Ethical targeting means PROTECTING vulnerable
consumers, not exploiting them.

Protection categories:
    1. Sleep-deprived consumers (late-night sessions)
    2. Cognitively depleted consumers (long sessions, many decisions)
    3. Emotionally distressed consumers (negative content + high arousal)
    4. Financially stressed consumers (financial hardship signals)
    5. Health-anxious consumers (health anxiety + solution-seeking)
    6. Minors (age-restricted content/targeting)
    7. Decision-fatigued consumers (excessive comparison/choice)
    8. Grief/loneliness (life-event vulnerability)
    9. Addiction susceptibility (gambling, compulsive patterns)
"""

from typing import Any, Dict, List

from adam.dsp.models import (
    PsychologicalStateVector,
    PersuasionStrategy,
    PersuasionRoute,
    EmotionalVehicle,
    VulnerabilityType,
)


class EthicalBoundaryEngine:
    """
    Enforces ethical constraints on psychological targeting.
    Protects vulnerable consumers while allowing legitimate persuasion.
    """

    # Category-vulnerability suppression matrix
    SUPPRESSION_MATRIX: Dict[VulnerabilityType, List[str]] = {
        VulnerabilityType.SLEEP_DEPRIVATION: [
            "gambling", "high_interest_lending", "impulse_luxury",
            "irreversible_commitments", "complex_financial_products",
        ],
        VulnerabilityType.COGNITIVE_DEPLETION: [
            "complex_multi_step_offers", "high_pressure_upsells",
            "auto_renewal_signup", "complicated_terms",
        ],
        VulnerabilityType.EMOTIONAL_DISTRESS: [
            "fear_appeals", "guilt_messaging", "scarcity_urgency",
            "body_image_pressure", "social_comparison",
        ],
        VulnerabilityType.FINANCIAL_STRESS: [
            "high_interest_lending", "gambling", "luxury_impulse",
            "buy_now_pay_later_aggressive", "unrealistic_income_promises",
        ],
        VulnerabilityType.HEALTH_ANXIETY: [
            "unregulated_supplements", "miracle_cures",
            "fear_based_health_marketing", "unvalidated_treatments",
        ],
        VulnerabilityType.LONELINESS: [
            "parasocial_exploitation", "paid_companionship_aggressive",
            "belonging_manipulation", "social_pressure_tactics",
        ],
        VulnerabilityType.GRIEF: [
            "memorial_exploitation", "emotional_manipulation",
            "urgency_pressure", "guilt_based_appeals",
        ],
        VulnerabilityType.ADDICTION_SUSCEPTIBILITY: [
            "gambling", "alcohol_promotion", "compulsive_shopping_triggers",
            "variable_reward_exploitation",
        ],
        VulnerabilityType.MINOR_DETECTED: [
            "age_restricted_products", "data_collection",
            "in_app_purchase_pressure", "influencer_undisclosed",
        ],
        VulnerabilityType.DECISION_FATIGUE: [
            "complex_multi_option_displays", "high_cognitive_demand_offers",
            "multi_step_conversion_funnels",
        ],
    }

    def evaluate(
        self,
        state: PsychologicalStateVector,
        strategy: PersuasionStrategy,
        ad_category: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate whether a targeting strategy violates ethical boundaries.

        Returns:
            dict with: approved (bool), risk_level, audit_trail,
            suppressed_categories, modified_strategy (if needed)
        """
        audit_trail = []
        suppressed = []
        risk_level = "low"
        approved = True

        # Check each vulnerability flag against suppression matrix
        for flag in state.vulnerability_flags:
            suppressed_cats = self.SUPPRESSION_MATRIX.get(flag, [])
            if ad_category and ad_category.lower() in [c.lower() for c in suppressed_cats]:
                approved = False
                risk_level = "blocked"
                suppressed.append(ad_category)
                audit_trail.append(
                    f"BLOCKED: '{ad_category}' suppressed for vulnerability '{flag.value}'"
                )
            elif suppressed_cats:
                audit_trail.append(
                    f"WARNING: Vulnerability '{flag.value}' detected. "
                    f"Suppressed categories: {suppressed_cats}"
                )
                if risk_level != "blocked":
                    risk_level = "elevated"

        # Severity-based global protections
        if state.vulnerability_severity > 0.6:
            risk_level = "high"
            audit_trail.append(
                f"HIGH SEVERITY: vulnerability_severity={state.vulnerability_severity:.2f}. "
                f"All high-pressure tactics suppressed."
            )

        # Generate modified strategy if needed
        modified_strategy = None
        if state.protection_mode and approved:
            modified_strategy = self._generate_safe_strategy(strategy, state)
            audit_trail.append("Strategy modified to safe version due to vulnerability.")

        return {
            "approved": approved,
            "risk_level": risk_level,
            "vulnerability_flags": [f.value for f in state.vulnerability_flags],
            "vulnerability_severity": state.vulnerability_severity,
            "suppressed_categories": suppressed,
            "audit_trail": audit_trail,
            "modified_strategy": modified_strategy,
        }

    def _generate_safe_strategy(
        self,
        original: PersuasionStrategy,
        state: PsychologicalStateVector,
    ) -> PersuasionStrategy:
        """Generate a safe strategy when vulnerability detected."""
        safe = PersuasionStrategy()
        safe.message_frame = "informational"
        safe.persuasion_route = PersuasionRoute.INFORMATIONAL
        safe.emotional_vehicle = EmotionalVehicle.NEUTRAL
        safe.argument_strength = "simple_heuristic"
        safe.social_proof_type = "none"
        safe.social_proof_strength = 0.0
        safe.scarcity_messaging = "none"
        safe.avoid_elements = [
            "All urgency/scarcity messaging",
            "All fear/guilt appeals",
            "All high-pressure CTAs",
            "All controlling language",
        ]
        safe.vulnerability_protections = original.vulnerability_protections
        safe.reasoning_trace = [
            "ETHICAL OVERRIDE: Vulnerability detected. "
            "Strategy replaced with safe informational approach."
        ]
        safe.confidence = 0.3  # low confidence reflects ethical caution
        return safe
