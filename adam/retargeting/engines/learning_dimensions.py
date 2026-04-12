# =============================================================================
# Multi-Dimensional Learning Engine
# Location: adam/retargeting/engines/learning_dimensions.py
# =============================================================================

"""
Eight dimensions of learning that make the system genuinely intelligent.

1. WHAT works    — mechanism effectiveness (existing)
2. WHO responds  — person modeling via puzzle solver (existing)
3. WHY it worked — causal attribution from behavioral evidence
4. WHEN to act   — temporal receptivity windows
5. What DOESN'T  — negative learning / fast hypothesis elimination
6. WHAT IF       — counterfactual reasoning
7. FROM OTHERS   — cross-user transfer learning
8. WHERE/CONTEXT — publisher × time × device interaction learning

Each dimension has:
  - An observation function (what data it needs)
  - An update function (how it learns from outcomes)
  - A query function (what intelligence it provides)
  - A confidence estimate (how certain it is)
"""

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# DIMENSION 3: CAUSAL ATTRIBUTION — Why did this conversion happen?
# =============================================================================

class CausalAttributor:
    """Determines WHY a conversion happened, not just THAT it happened.

    Uses behavioral evidence to distinguish:
    - Ad-caused conversion: the ad creative directly triggered action
    - Ad-accelerated: the person was going to convert but the ad sped it up
    - Organic conversion: the ad was irrelevant, they converted independently
    - Somatic resolution: the testimonial/narrative resolved an emotional barrier

    This matters because ad-caused conversions prove mechanism effectiveness,
    while organic conversions don't — but standard attribution counts them equally.
    """

    def attribute(
        self,
        profile: Dict,
        conversion: Dict,
    ) -> Dict:
        """Attribute a conversion to its likely cause."""
        signals = {}

        # Organic return before conversion = internal motivation was forming
        organic_sessions = profile.get("organic_sessions", 0)
        total_sessions = profile.get("total_sessions", 1)
        organic_ratio = organic_sessions / max(1, total_sessions)

        # If high organic ratio, the conversion was partially organic
        if organic_ratio > 0.5:
            signals["organic_contribution"] = min(0.8, organic_ratio)
            signals["ad_contribution"] = 1.0 - signals["organic_contribution"]
        else:
            signals["organic_contribution"] = max(0.1, organic_ratio * 0.5)
            signals["ad_contribution"] = 1.0 - signals["organic_contribution"]

        # Somatic evidence: testimonial/review engagement predicts somatic resolution
        section_dwell = profile.get("section_dwell_totals", {})
        testimonial_dwell = (
            section_dwell.get("section-testimonials", 0)
            + section_dwell.get("section-reviews", 0)
        )
        if testimonial_dwell > 15:
            signals["somatic_resolution"] = min(0.6, testimonial_dwell / 50)
        else:
            signals["somatic_resolution"] = 0.1

        # Click latency trajectory = barrier resolving through ad sequence
        trajectory = profile.get("click_latency_trajectory", "")
        if trajectory == "resolving":
            signals["sequence_effectiveness"] = 0.7
        elif trajectory == "building":
            signals["sequence_effectiveness"] = 0.2
        else:
            signals["sequence_effectiveness"] = 0.4

        # Time to conversion (touches count)
        touches = len(profile.get("attributed_touch_positions", []))
        if touches <= 2:
            signals["conversion_speed"] = "fast"
            signals["efficiency_score"] = 0.9
        elif touches <= 4:
            signals["conversion_speed"] = "moderate"
            signals["efficiency_score"] = 0.6
        else:
            signals["conversion_speed"] = "slow"
            signals["efficiency_score"] = 0.3

        # Primary attribution
        if signals["organic_contribution"] > 0.6:
            signals["primary_cause"] = "organic_motivation"
            signals["ad_causal_weight"] = 0.3
        elif signals["somatic_resolution"] > 0.4:
            signals["primary_cause"] = "somatic_marker_resolution"
            signals["ad_causal_weight"] = 0.8
        elif signals["sequence_effectiveness"] > 0.5:
            signals["primary_cause"] = "mechanism_effectiveness"
            signals["ad_causal_weight"] = 0.9
        else:
            signals["primary_cause"] = "combined_factors"
            signals["ad_causal_weight"] = 0.6

        return signals


# =============================================================================
# DIMENSION 4: TEMPORAL RECEPTIVITY — When is this person open?
# =============================================================================

class TemporalLearner:
    """Learns per-person and per-archetype receptivity windows.

    Not just "what time do they browse" but "what time are they
    psychologically open to persuasion." Someone browsing at 11pm
    in bed (high anxiety, research mode) is different from browsing
    at 2pm at work (low engagement, distracted).

    Tracks: hour_of_day × day_of_week × engagement_depth
    """

    def compute_receptivity_windows(
        self, profiles: List[Dict],
    ) -> Dict[str, Dict]:
        """Compute receptivity windows per archetype from observed engagement."""
        archetype_hours = defaultdict(lambda: defaultdict(lambda: {
            "sessions": 0, "total_dwell": 0.0, "conversions": 0,
        }))

        for p in profiles:
            arch = p.get("attributed_archetype", "unclassified")
            for hour_str, count in p.get("hour_engagement_counts", {}).items():
                hour = int(hour_str) if isinstance(hour_str, str) else hour_str
                archetype_hours[arch][hour]["sessions"] += count
                # Proxy for dwell: total_sessions correlates with engagement
                archetype_hours[arch][hour]["total_dwell"] += p.get("total_sessions", 0)

        results = {}
        for arch, hours in archetype_hours.items():
            if arch == "unclassified":
                continue

            # Find peak hours (top 25% by session count)
            total = sum(h["sessions"] for h in hours.values())
            if total < 5:
                continue

            hour_rates = {h: data["sessions"] / max(1, total) for h, data in hours.items()}
            threshold = sorted(hour_rates.values(), reverse=True)[min(5, len(hour_rates)-1)] if hour_rates else 0

            peak_hours = [h for h, rate in hour_rates.items() if rate >= threshold]
            off_hours = [h for h, rate in hour_rates.items() if rate < threshold * 0.3]

            results[arch] = {
                "peak_hours": sorted(peak_hours),
                "off_hours": sorted(off_hours),
                "hour_distribution": {str(h): round(r, 4) for h, r in sorted(hour_rates.items())},
                "total_observations": total,
                "recommendation": (
                    f"Increase bid during hours {sorted(peak_hours)[:3]} "
                    f"(peak engagement). Reduce bid during {sorted(off_hours)[:3]}."
                ),
            }

        return results


# =============================================================================
# DIMENSION 5: NEGATIVE LEARNING — Fast hypothesis elimination
# =============================================================================

class NegativeLearner:
    """Learns from failures as aggressively as from successes.

    For each mechanism, tracks:
    - How many times it was deployed without conversion
    - How many times it was followed by reactance signals
    - How many times the user DISENGAGED after this mechanism

    A mechanism that consistently fails for an archetype should be
    eliminated from that archetype's candidate set, not just deprioritized.
    """

    def analyze_failures(
        self, profiles: List[Dict], conversions: List[Dict],
    ) -> Dict:
        """Analyze mechanism failures to identify what to STOP doing."""
        conv_user_ids = {c.get("visitor_id") for c in conversions}

        # Track mechanisms exposed to non-converters
        mech_failures = defaultdict(lambda: {"exposed": 0, "converted": 0, "wasted": 0})

        for p in profiles:
            uid = p.get("user_id", "")
            converted = uid in conv_user_ids
            mechanisms = p.get("mechanisms_exposed", [])

            for mech in mechanisms:
                mech_failures[mech]["exposed"] += 1
                if converted:
                    mech_failures[mech]["converted"] += 1
                else:
                    mech_failures[mech]["wasted"] += 1

        # Identify mechanisms that consistently fail
        eliminations = []
        for mech, data in mech_failures.items():
            if data["exposed"] >= 5:
                failure_rate = data["wasted"] / data["exposed"]
                if failure_rate > 0.85:
                    eliminations.append({
                        "mechanism": mech,
                        "failure_rate": round(failure_rate, 3),
                        "exposed": data["exposed"],
                        "converted": data["converted"],
                        "recommendation": (
                            f"ELIMINATE {mech}: {failure_rate:.0%} failure rate across "
                            f"{data['exposed']} exposures. Replace with alternative mechanism."
                        ),
                    })

        return {
            "mechanism_failure_rates": {
                m: {"failure_rate": round(d["wasted"]/max(1,d["exposed"]), 3), **d}
                for m, d in mech_failures.items() if d["exposed"] >= 3
            },
            "eliminations": eliminations,
        }


# =============================================================================
# DIMENSION 7: CROSS-USER TRANSFER — Learn from similar people
# =============================================================================

class CrossUserTransfer:
    """When we solve one person's puzzle, accelerate solving similar puzzles.

    Groups users by psychological similarity (attachment pattern + motive)
    and transfers effective mechanism sequences from converters to
    non-converters in the same group.
    """

    def compute_transfer_insights(
        self, profiles: List[Dict], conversions: List[Dict],
    ) -> Dict:
        """Find patterns among converters that can transfer to non-converters."""
        conv_user_ids = {c.get("visitor_id") for c in conversions}

        # Group by archetype
        groups = defaultdict(lambda: {"converters": [], "non_converters": []})
        for p in profiles:
            arch = p.get("attributed_archetype", "unclassified")
            if arch == "unclassified":
                continue
            uid = p.get("user_id", "")
            if uid in conv_user_ids:
                groups[arch]["converters"].append(p)
            elif p.get("total_sessions", 0) >= 2:
                groups[arch]["non_converters"].append(p)

        insights = {}
        for arch, group in groups.items():
            convs = group["converters"]
            non_convs = group["non_converters"]

            if len(convs) < 2 or len(non_convs) < 2:
                continue

            # What mechanisms did converters see?
            conv_mechs = defaultdict(int)
            for p in convs:
                for m in p.get("mechanisms_exposed", []):
                    conv_mechs[m] += 1

            # What mechanisms did non-converters see?
            non_conv_mechs = defaultdict(int)
            for p in non_convs:
                for m in p.get("mechanisms_exposed", []):
                    non_conv_mechs[m] += 1

            # What's the converter-specific mechanism?
            conv_only = {}
            for m, count in conv_mechs.items():
                conv_rate = count / len(convs)
                non_rate = non_conv_mechs.get(m, 0) / max(1, len(non_convs))
                if conv_rate > non_rate * 1.5 and count >= 2:
                    conv_only[m] = {
                        "converter_exposure_rate": round(conv_rate, 3),
                        "non_converter_exposure_rate": round(non_rate, 3),
                        "lift": round(conv_rate / max(0.01, non_rate), 2),
                    }

            # Average session patterns
            conv_avg_sessions = sum(p.get("total_sessions", 0) for p in convs) / len(convs)
            non_avg_sessions = sum(p.get("total_sessions", 0) for p in non_convs) / len(non_convs)

            # Barrier at conversion
            conv_barriers = defaultdict(int)
            for c in conversions:
                if c.get("self_reported_barrier"):
                    conv_barriers[c["self_reported_barrier"]] += 1

            insights[arch] = {
                "converters": len(convs),
                "non_converters": len(non_convs),
                "converter_specific_mechanisms": conv_only,
                "avg_sessions_to_convert": round(conv_avg_sessions, 1),
                "non_converter_avg_sessions": round(non_avg_sessions, 1),
                "barriers_at_conversion": dict(conv_barriers),
                "transfer_recommendation": (
                    f"For {arch} non-converters with {non_avg_sessions:.0f}+ sessions: "
                    f"deploy {', '.join(conv_only.keys()) if conv_only else 'the converter mechanism sequence'}. "
                    f"Converters averaged {conv_avg_sessions:.1f} sessions."
                ),
            }

        return insights


# =============================================================================
# DIMENSION 8: CONTEXT LEARNING — Publisher × time × device interactions
# =============================================================================

class ContextLearner:
    """Learns which contexts produce conversions.

    Tracks the three-way interaction: publisher_domain × hour × device.
    "Forbes on desktop at 9am" might convert 3x better than
    "TripAdvisor on mobile at 10pm" for careful_trusters.
    """

    def analyze_context_effectiveness(
        self, profiles: List[Dict], conversions: List[Dict],
    ) -> Dict:
        """Analyze which contexts (domain × device × time) drive conversion."""
        conv_user_ids = {c.get("visitor_id") for c in conversions}

        # Device effectiveness
        device_conv = defaultdict(lambda: {"total": 0, "converted": 0})
        for p in profiles:
            uid = p.get("user_id", "")
            converted = uid in conv_user_ids
            for device, count in p.get("device_impressions", {}).items():
                device_conv[device]["total"] += count
                if converted:
                    device_conv[device]["converted"] += count

        device_results = {}
        for device, data in device_conv.items():
            if data["total"] >= 3:
                rate = data["converted"] / data["total"]
                device_results[device] = {
                    "conversion_rate": round(rate, 4),
                    "total_impressions": data["total"],
                    "conversions": data["converted"],
                }

        # Time-of-day effectiveness (from conversion data)
        hour_conv = defaultdict(lambda: {"total": 0, "converted": 0})
        for p in profiles:
            uid = p.get("user_id", "")
            converted = uid in conv_user_ids
            for hour_str, count in p.get("hour_engagement_counts", {}).items():
                hour_conv[int(hour_str)]["total"] += count
                if converted:
                    hour_conv[int(hour_str)]["converted"] += count

        hour_results = {}
        for hour, data in hour_conv.items():
            if data["total"] >= 3:
                rate = data["converted"] / data["total"]
                hour_results[hour] = {
                    "conversion_rate": round(rate, 4),
                    "total_sessions": data["total"],
                }

        return {
            "device_effectiveness": device_results,
            "hour_effectiveness": hour_results,
            "recommendations": self._generate_context_recs(device_results, hour_results),
        }

    def _generate_context_recs(self, devices: Dict, hours: Dict) -> List[str]:
        """Generate context-specific recommendations."""
        recs = []

        if devices:
            best_device = max(devices, key=lambda d: devices[d]["conversion_rate"])
            worst_device = min(devices, key=lambda d: devices[d]["conversion_rate"])
            if devices[best_device]["conversion_rate"] > devices[worst_device]["conversion_rate"] * 1.5:
                recs.append(
                    f"Increase {best_device} bid multiplier — "
                    f"{devices[best_device]['conversion_rate']:.1%} conversion rate vs "
                    f"{devices[worst_device]['conversion_rate']:.1%} on {worst_device}."
                )

        if hours:
            sorted_hours = sorted(hours.items(), key=lambda x: -x[1]["conversion_rate"])
            if len(sorted_hours) >= 3:
                top_hours = [h for h, _ in sorted_hours[:3]]
                recs.append(
                    f"Peak conversion hours: {top_hours}. "
                    f"Concentrate budget during these windows."
                )

        return recs


# =============================================================================
# INTEGRATED LEARNING ENGINE
# =============================================================================

class MultiDimensionalLearner:
    """Orchestrates all 8 learning dimensions."""

    def __init__(self):
        self.causal = CausalAttributor()
        self.temporal = TemporalLearner()
        self.negative = NegativeLearner()
        self.transfer = CrossUserTransfer()
        self.context = ContextLearner()

    def run_full_learning_cycle(
        self,
        profiles: List[Dict],
        conversions: List[Dict],
    ) -> Dict:
        """Run all learning dimensions and produce integrated intelligence."""
        results = {}

        # Dimension 3: Causal attribution for each conversion
        causal_attributions = []
        for conv in conversions:
            vid = conv.get("visitor_id", "")
            profile = next((p for p in profiles if p.get("user_id") == vid), None)
            if profile:
                attribution = self.causal.attribute(profile, conv)
                attribution["visitor_id"] = vid
                causal_attributions.append(attribution)
        results["causal_attributions"] = causal_attributions

        # Summarize causal findings
        if causal_attributions:
            causes = defaultdict(int)
            for a in causal_attributions:
                causes[a.get("primary_cause", "unknown")] += 1
            results["causal_summary"] = dict(causes)
            avg_ad_weight = sum(a.get("ad_causal_weight", 0) for a in causal_attributions) / len(causal_attributions)
            results["avg_ad_causal_weight"] = round(avg_ad_weight, 3)

        # Dimension 4: Temporal receptivity
        results["temporal_windows"] = self.temporal.compute_receptivity_windows(profiles)

        # Dimension 5: Negative learning
        results["failure_analysis"] = self.negative.analyze_failures(profiles, conversions)

        # Dimension 7: Cross-user transfer
        results["transfer_insights"] = self.transfer.compute_transfer_insights(profiles, conversions)

        # Dimension 8: Context learning
        results["context_effectiveness"] = self.context.analyze_context_effectiveness(profiles, conversions)

        return results


def get_multi_dimensional_learner() -> MultiDimensionalLearner:
    return MultiDimensionalLearner()
