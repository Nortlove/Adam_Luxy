# =============================================================================
# Daily Intelligence Brief
# Location: adam/intelligence/daily_intelligence_brief.py
# =============================================================================

"""
Produces a daily intelligence brief summarizing what the system learned,
what it's testing, what it recommends, and whether it's getting smarter.

Run daily (or on-demand) to give the operator actionable intelligence
for steering the pilot.

Sections:
1. LEARNING: What the system learned yesterday
2. TESTING: What hypotheses are being tested today
3. PREDICTIONS: Active predictions and their status
4. RECOMMENDATIONS: Budget reallocation, domain changes, copy regeneration
5. ACCURACY: Is prediction accuracy improving?
6. NEXT ACTIONS: What the system will do next
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_daily_brief() -> Dict[str, Any]:
    """Generate the daily intelligence brief.

    Returns a structured dict that can be rendered as markdown,
    JSON, or sent via notification.
    """
    brief = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {},
    }

    # ── 1. LEARNING ──
    learning = {"new_hypotheses": 0, "validated": 0, "invalidated": 0, "surprising": 0}
    try:
        from adam.intelligence.inferential_hypothesis_engine import get_inferential_hypothesis_engine
        he = get_inferential_hypothesis_engine()
        stats = he.stats
        learning["total_hypotheses"] = stats.get("total_hypotheses", 0)
        learning["validated"] = stats.get("validated", 0)
        learning["actionable"] = stats.get("actionable", 0)
        learning["by_status"] = stats.get("by_status", {})
    except Exception:
        pass

    try:
        from adam.intelligence.causal_decomposition import get_causal_decomposition_engine
        de = get_causal_decomposition_engine()
        ds = de.stats
        learning["decompositions"] = ds.get("total_decompositions", 0)
        learning["surprising"] = ds.get("surprising_conversions", 0)
    except Exception:
        pass

    brief["sections"]["learning"] = learning

    # ── 2. TESTING ──
    testing = {"hypotheses_under_test": [], "info_value_ranking": []}
    try:
        from adam.intelligence.inferential_hypothesis_engine import get_inferential_hypothesis_engine
        he = get_inferential_hypothesis_engine()
        ranking = he.get_test_priority_ranking()
        for hid, iv, reason in ranking[:5]:
            h = he._hypotheses.get(hid)
            if h:
                testing["info_value_ranking"].append({
                    "hypothesis_id": hid,
                    "info_value": iv,
                    "mechanism": h.predicted_mechanism,
                    "conditions": {k: f"{op}{v}" for k, (op, v) in h.conditions.items()},
                    "reason": reason,
                    "supporting": h.supporting_observations,
                    "contradicting": h.contradicting_observations,
                })
    except Exception:
        pass

    brief["sections"]["testing"] = testing

    # ── 3. PREDICTIONS ──
    predictions = {"active": 0, "completed": 0, "validated": 0, "accuracy": 0}
    try:
        from adam.intelligence.prediction_engine import get_prediction_engine
        pe = get_prediction_engine()
        ps = pe.stats
        predictions.update(ps)
    except Exception:
        pass

    brief["sections"]["predictions"] = predictions

    # ── 4. RECOMMENDATIONS ──
    recommendations = []

    # Check archetype performance
    try:
        from adam.intelligence.causal_decomposition import get_causal_decomposition_engine
        de = get_causal_decomposition_engine()
        if de.stats["total_decompositions"] > 0:
            # Check if one archetype is producing more recipes than others
            arch_counts = {}
            for r in de._recipes:
                arch = r.archetype
                arch_counts[arch] = arch_counts.get(arch, 0) + 1
            if arch_counts:
                top_arch = max(arch_counts, key=arch_counts.get)
                recommendations.append({
                    "type": "budget_allocation",
                    "message": f"Archetype '{top_arch}' producing most learnings ({arch_counts[top_arch]}). Consider increasing budget allocation.",
                    "priority": "medium",
                })
    except Exception:
        pass

    # Check for surprising patterns
    try:
        from adam.intelligence.causal_decomposition import get_causal_decomposition_engine
        de = get_causal_decomposition_engine()
        surprising = [r for r in de._recipes if r.is_surprising]
        if surprising:
            recommendations.append({
                "type": "investigate",
                "message": f"{len(surprising)} surprising conversions detected. Theory may need revision.",
                "priority": "high",
                "details": [r.surprise_reason for r in surprising[:3]],
            })
    except Exception:
        pass

    # Check counterfactual insights
    try:
        from adam.intelligence.counterfactual_tracker import get_counterfactual_tracker
        ct = get_counterfactual_tracker()
        stats = ct.stats
        if stats["validated"] > 0:
            for mech, alts in stats.get("mechanism_alternatives", {}).items():
                for alt_mech, count in sorted(alts.items(), key=lambda x: -x[1])[:1]:
                    if count >= 3:
                        recommendations.append({
                            "type": "mechanism_switch",
                            "message": f"Counterfactual analysis suggests {alt_mech} may outperform {mech} ({count} predictions)",
                            "priority": "high",
                        })
    except Exception:
        pass

    brief["sections"]["recommendations"] = recommendations

    # ── 5. ACCURACY ──
    accuracy = {"trend": "insufficient_data", "avg": 0}
    try:
        from adam.intelligence.prediction_engine import get_prediction_engine
        pe = get_prediction_engine()
        accuracy["trend"] = pe.prediction_accuracy_trend
        accuracy["avg"] = pe.stats.get("avg_accuracy", 0)
    except Exception:
        pass

    brief["sections"]["accuracy"] = accuracy

    # ── 6. SYSTEM HEALTH ──
    health = {}
    try:
        from adam.infrastructure.resilience.circuit_breaker import get_circuit_breaker
        for svc in ["neo4j", "redis", "prefetch"]:
            cb = get_circuit_breaker(svc)
            health[f"circuit_{svc}"] = cb.state.value
    except Exception:
        pass

    try:
        from adam.retargeting.engines.prior_manager import get_prior_manager
        pm = get_prior_manager()
        health["prior_manager"] = pm.stats
    except Exception:
        pass

    brief["sections"]["health"] = health

    return brief


def format_brief_markdown(brief: Dict[str, Any]) -> str:
    """Format the brief as readable markdown."""
    lines = [
        f"# INFORMATIV Daily Intelligence Brief",
        f"Generated: {brief['generated_at']}",
        "",
    ]

    # Learning
    learn = brief["sections"].get("learning", {})
    lines.append("## What We Learned")
    lines.append(f"- **{learn.get('decompositions', 0)}** conversions decomposed into causal recipes")
    lines.append(f"- **{learn.get('total_hypotheses', 0)}** hypotheses in pool ({learn.get('validated', 0)} validated)")
    lines.append(f"- **{learn.get('surprising', 0)}** surprising outcomes (theory violations)")
    lines.append("")

    # Testing
    testing = brief["sections"].get("testing", {})
    lines.append("## What We're Testing")
    for h in testing.get("info_value_ranking", [])[:3]:
        lines.append(f"- **{h['hypothesis_id']}**: {h['mechanism']} when {h['conditions']} (IV={h['info_value']:.3f})")
    lines.append("")

    # Predictions
    preds = brief["sections"].get("predictions", {})
    lines.append("## Prediction Status")
    lines.append(f"- Active: {preds.get('active_predictions', 0)}")
    lines.append(f"- Validated: {preds.get('validated', 0)}")
    lines.append(f"- Accuracy trend: **{preds.get('accuracy_trend', 'insufficient_data')}**")
    lines.append("")

    # Recommendations
    recs = brief["sections"].get("recommendations", [])
    if recs:
        lines.append("## Recommendations")
        for r in recs:
            priority = "🔴" if r["priority"] == "high" else "🟡"
            lines.append(f"- {priority} {r['message']}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    brief = generate_daily_brief()
    print(format_brief_markdown(brief))
    # Also save as JSON
    with open("campaigns/ridelux_v6/daily_brief.json", "w") as f:
        json.dump(brief, f, indent=2, default=str)
    print(f"\nJSON saved to campaigns/ridelux_v6/daily_brief.json")
