# =============================================================================
# Campaign Action Generator
# Location: adam/ops/campaign_actions.py
# =============================================================================

"""
Translates system recommendations into specific, executable StackAdapt
campaign changes.

Each recommendation produces:
1. A human-readable instruction for the agency
2. A machine-readable StackAdapt GraphQL mutation (for Phase 2)
3. The expected impact of the change
4. The measurement plan (how to verify the change worked)

This is the bridge between our intelligence and actual campaign changes.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Campaign name → StackAdapt campaign mapping
# These will be populated with actual StackAdapt campaign IDs from Becca
CAMPAIGN_MAP = {
    "CT-T1": {"name": "CT Touch 1 — social_proof_matched", "group": "Careful Truster"},
    "CT-T2": {"name": "CT Touch 2 — evidence_proof", "group": "Careful Truster"},
    "CT-T3": {"name": "CT Touch 3 — evidence_proof", "group": "Careful Truster"},
    "CT-T4": {"name": "CT Touch 4 — social_proof_matched", "group": "Careful Truster"},
    "CT-T5": {"name": "CT Touch 5 — anxiety_resolution", "group": "Careful Truster"},
    "SS-T1": {"name": "SS Touch 1 — narrative_transportation", "group": "Status Seeker"},
    "SS-T2": {"name": "SS Touch 2 — social_proof_matched", "group": "Status Seeker"},
    "SS-T3": {"name": "SS Touch 3 — narrative_transportation", "group": "Status Seeker"},
    "SS-T4": {"name": "SS Touch 4 — social_proof_matched", "group": "Status Seeker"},
    "SS-T5": {"name": "SS Touch 5 — claude_argument", "group": "Status Seeker"},
    "ED-T1": {"name": "ED Touch 1 — loss_framing", "group": "Easy Decider"},
    "ED-T2": {"name": "ED Touch 2 — implementation_intention", "group": "Easy Decider"},
    "ED-T3": {"name": "ED Touch 3 — micro_commitment", "group": "Easy Decider"},
    "ED-T4": {"name": "ED Touch 4 — ownership_reactivation", "group": "Easy Decider"},
    "ED-T5": {"name": "ED Touch 5 — micro_commitment", "group": "Easy Decider"},
    "EX-T1": {"name": "EX Touch 1 — narrative_transportation", "group": "Explorer"},
    "EX-T2": {"name": "EX Touch 2 — micro_commitment", "group": "Explorer"},
    "PP-T1": {"name": "PP Touch 1 — anxiety_resolution", "group": "Prevention Planner"},
    "PP-T2": {"name": "PP Touch 2 — evidence_proof", "group": "Prevention Planner"},
    "PP-T3": {"name": "PP Touch 3 — implementation_intention", "group": "Prevention Planner"},
    "RC-T1": {"name": "RC Touch 1 — social_proof_matched", "group": "Reliable Cooperator"},
    "RC-T2": {"name": "RC Touch 2 — implementation_intention", "group": "Reliable Cooperator"},
}


def generate_campaign_action(recommendation: Dict) -> Dict:
    """Generate a specific, executable campaign action from a recommendation.

    Returns a structured action with:
    - Human instructions (what to tell the agency)
    - StackAdapt changes (specific settings to modify)
    - Expected impact
    - Measurement plan
    """
    rec_type = recommendation.get("type", "")
    data = recommendation.get("data", {})
    title = recommendation.get("title", "")

    action = {
        "recommendation_title": title,
        "type": rec_type,
        "generated_at": time.time(),
        "stackadapt_changes": [],
        "agency_instructions": "",
        "expected_impact": "",
        "measurement_plan": "",
        "graphql_mutations": [],  # For Phase 2 auto-execution
    }

    if rec_type == "budget_reallocation":
        # Parse which archetypes to increase/decrease
        by_arch = data.get("by_archetype", {})
        if by_arch:
            sorted_archs = sorted(by_arch.items(), key=lambda x: -x[1])
            best = sorted_archs[0] if sorted_archs else None
            worst = sorted_archs[-1] if len(sorted_archs) > 1 else None

            changes = []
            instructions = []

            if best:
                best_arch, best_count = best
                group = _archetype_to_group(best_arch)
                changes.append({
                    "campaign_group": group,
                    "setting": "daily_budget",
                    "action": "increase",
                    "amount": "20%",
                    "reason": f"{best_count} conversions — highest converting archetype",
                })
                instructions.append(
                    f"INCREASE daily budget for '{group}' campaign group by 20%"
                )

            if worst and worst[1] < best[1] * 0.5:
                worst_arch, worst_count = worst
                group = _archetype_to_group(worst_arch)
                changes.append({
                    "campaign_group": group,
                    "setting": "daily_budget",
                    "action": "decrease",
                    "amount": "10%",
                    "reason": f"Only {worst_count} conversions — underperforming",
                })
                instructions.append(
                    f"DECREASE daily budget for '{group}' campaign group by 10%"
                )

            action["stackadapt_changes"] = changes
            action["agency_instructions"] = (
                "Budget Reallocation Required:\n\n"
                + "\n".join(f"  {i+1}. {inst}" for i, inst in enumerate(instructions))
                + "\n\nReason: Performance data shows significant conversion rate "
                "difference between archetypes. Reallocating budget toward "
                "higher-converting segments improves overall ROAS."
            )
            action["expected_impact"] = (
                "Expected: 15-25% improvement in cost per booking within 5 days. "
                "Monitor daily conversion counts per campaign group."
            )
            action["measurement_plan"] = (
                "Compare 7-day rolling average CPB before and after change. "
                "If CPB improves by >10%, maintain. If worsens, revert."
            )

    elif rec_type == "frequency_adjustment":
        archetype = recommendation.get("archetype", "")
        group = _archetype_to_group(archetype)

        action["stackadapt_changes"] = [{
            "campaign_group": group,
            "setting": "frequency_cap",
            "action": "reduce",
            "new_value": "max 2/day, 5/week",
            "reason": "Reactance detected — engagement declining with current frequency",
        }]
        action["agency_instructions"] = (
            f"Frequency Cap Reduction for '{group}':\n\n"
            f"  1. Open all campaigns in the '{group}' campaign group\n"
            f"  2. Change frequency cap from current to: Max 2 impressions/day, 5/week\n"
            f"  3. Increase minimum hours between impressions to 12 hours\n\n"
            f"Reason: Our behavioral signals detect engagement decline (reactance) "
            f"in this segment. Reducing frequency preserves brand perception."
        )
        action["expected_impact"] = (
            "Expected: CTR should increase within 3 days as ad fatigue decreases. "
            "Conversion rate may temporarily dip then recover stronger."
        )
        action["measurement_plan"] = (
            "Track per-impression engagement rate (not just total impressions). "
            "If engagement rate increases by >20%, the frequency was too high."
        )

    elif rec_type == "stage_transition":
        archetype = recommendation.get("archetype", "")
        group = _archetype_to_group(archetype)

        action["stackadapt_changes"] = [{
            "campaign_group": group,
            "setting": "budget_distribution",
            "action": "shift",
            "from_campaigns": "Touch 1-2",
            "to_campaigns": "Touch 4-5",
            "reason": "High organic return rate indicates users have self-advanced to intending stage",
        }]
        action["agency_instructions"] = (
            f"Budget Shift Within '{group}':\n\n"
            f"  1. REDUCE daily budget on Touch 1 and Touch 2 campaigns by 30%\n"
            f"  2. INCREASE daily budget on Touch 4 and Touch 5 campaigns by 30%\n\n"
            f"Reason: Users in this segment are returning organically — they've "
            f"moved past the awareness stage. They don't need more awareness ads. "
            f"They need friction-removal and implementation ads (Touch 4-5)."
        )
        action["expected_impact"] = (
            "Expected: Higher conversion rate on lower total spend. "
            "The organic returns show internal motivation has formed."
        )
        action["measurement_plan"] = (
            "Monitor Touch 4-5 conversion rate vs Touch 1-2. "
            "If T4-T5 converts at >2x T1-T2 rate, the shift is working."
        )

    elif rec_type == "creative_focus":
        barrier_data = data.get("barrier_distribution", {})
        top_barrier = max(barrier_data, key=barrier_data.get) if barrier_data else ""

        action["stackadapt_changes"] = [{
            "setting": "creative",
            "action": "new_variant",
            "target_barrier": top_barrier,
            "reason": f"{top_barrier} is the dominant barrier — creative should address it directly",
        }]
        action["agency_instructions"] = (
            f"Creative Variant Recommended:\n\n"
            f"  The dominant conversion barrier is '{top_barrier}'. "
            f"Current creative may not address this directly.\n\n"
            f"  Recommended: Create a new ad variant that specifically "
            f"addresses {top_barrier}. INFORMATIV will provide the copy.\n\n"
            f"  For now: No StackAdapt changes needed. INFORMATIV will "
            f"deliver new creative copy within 24 hours of acceptance."
        )
        action["expected_impact"] = (
            "Expected: Barrier-specific creative converts 20-40% higher "
            "than generic creative for users with this barrier."
        )
        action["measurement_plan"] = (
            "A/B test: run new variant alongside existing for 7 days. "
            "Compare conversion rate per 1000 impressions."
        )

    else:
        action["agency_instructions"] = (
            f"Recommendation: {title}\n\n"
            f"Details: {recommendation.get('detail', recommendation.get('recommendation', ''))}\n\n"
            f"Please review and implement as described."
        )
        action["expected_impact"] = "Impact dependent on implementation."
        action["measurement_plan"] = "Monitor campaign metrics for 7 days after change."

    return action


def _archetype_to_group(archetype: str) -> str:
    """Map archetype ID to StackAdapt campaign group name."""
    mapping = {
        "careful_truster": "LUXY Ride — Careful Truster",
        "status_seeker": "LUXY Ride — Status Seeker",
        "easy_decider": "LUXY Ride — Easy Decider",
        "explorer": "LUXY Ride — Explorer",
        "prevention_planner": "LUXY Ride — Prevention Planner",
        "reliable_cooperator": "LUXY Ride — Reliable Cooperator",
    }
    return mapping.get(archetype, f"LUXY Ride — {archetype}")


def generate_daily_action_report(
    recommendations: List[Dict],
    accepted: List[Dict],
) -> str:
    """Generate a daily action report summarizing all recommendations.

    This is what gets sent to the team each day:
    - What the system learned today
    - What changes it recommends
    - What changes were accepted and executed
    - What to watch for tomorrow
    """
    lines = [
        "# INFORMATIV Daily Intelligence Report",
        f"## {__import__('datetime').datetime.now().strftime('%A, %B %d, %Y')}",
        "",
        "---",
        "",
    ]

    if recommendations:
        lines.append(f"## Pending Recommendations ({len(recommendations)})")
        lines.append("")
        for i, rec in enumerate(recommendations, 1):
            action = generate_campaign_action(rec)
            lines.append(f"### {i}. {rec.get('title', rec.get('type', 'Recommendation'))}")
            lines.append(f"**Severity**: {rec.get('severity', 'medium')} | **Confidence**: {(rec.get('confidence', 0) * 100):.0f}%")
            lines.append("")
            lines.append("**StackAdapt Instructions:**")
            lines.append(f"```\n{action['agency_instructions']}\n```")
            lines.append(f"**Expected Impact**: {action['expected_impact']}")
            lines.append(f"**How to Verify**: {action['measurement_plan']}")
            lines.append("")
    else:
        lines.append("## No New Recommendations")
        lines.append("The system is still gathering data. Recommendations will appear when statistically significant patterns emerge.")
        lines.append("")

    if accepted:
        lines.append(f"## Accepted Actions ({len(accepted)})")
        lines.append("")
        for a in accepted:
            lines.append(f"- **{a.get('title', a.get('type', ''))}** — accepted {__import__('datetime').datetime.fromtimestamp(a.get('accepted_at', 0)).strftime('%H:%M')} — status: {a.get('status', 'unknown')}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by INFORMATIV bilateral psycholinguistic intelligence.*")

    return "\n".join(lines)
