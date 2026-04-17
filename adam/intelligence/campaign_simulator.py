"""
Pre-Campaign Performance Simulation
=====================================

Composes bilateral evidence, gradient fields, mechanism scoring, prospect
theory, and the dimension compressor into per-cell conversion predictions
BEFORE any money is spent.

The output: for each archetype × mechanism × domain-category combination,
a predicted P(conversion), expected CPA, expected ROAS, mechanism score,
and a reasoning chain explaining WHY.

This is the scientific method applied to advertising:
Predict → Execute → Validate → Learn → Better Predict

Usage:
    simulator = CampaignSimulator()
    forecast = simulator.simulate_campaign(
        asin="lux_luxy_ride",
        archetypes=["careful_truster", "status_seeker", ...],
        mechanisms=["authority", "social_proof", ...],
        domain_categories=["business", "travel", "lifestyle", ...],
        daily_budget=250.0,
        avg_cpm=12.0,
    )
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# Domain categories → goal activation profiles
# Each domain category primes specific nonconscious goals, which
# amplify or suppress specific mechanisms.
DOMAIN_GOAL_PROFILES = {
    "business_finance": {
        "goals": ["competence_verification", "status_signaling", "planning_completion"],
        "mechanism_boosts": {"authority": 0.15, "commitment": 0.08, "cognitive_ease": 0.05},
        "mechanism_penalties": {"liking": -0.05, "scarcity": -0.03},
        "examples": ["Bloomberg", "Forbes", "WSJ", "HBR", "Financial Times"],
    },
    "corporate_travel": {
        "goals": ["planning_completion", "threat_reduction", "competence_verification"],
        "mechanism_boosts": {"authority": 0.12, "cognitive_ease": 0.10, "commitment": 0.08},
        "mechanism_penalties": {"curiosity": -0.05, "scarcity": -0.04},
        "examples": ["Business Traveler", "Skift", "BTN", "Corporate Travel World"],
    },
    "luxury_lifestyle": {
        "goals": ["status_signaling", "indulgence_permission", "social_alignment"],
        "mechanism_boosts": {"social_proof": 0.12, "liking": 0.10, "scarcity": 0.08},
        "mechanism_penalties": {"cognitive_ease": -0.05, "authority": -0.03},
        "examples": ["Robb Report", "Departures", "DuJour", "Luxury Travel Magazine"],
    },
    "travel_planning": {
        "goals": ["planning_completion", "novelty_exploration", "threat_reduction"],
        "mechanism_boosts": {"curiosity": 0.10, "cognitive_ease": 0.12, "social_proof": 0.05},
        "mechanism_penalties": {"commitment": -0.05, "authority": -0.03},
        "examples": ["TripAdvisor", "Condé Nast Traveler", "Travel + Leisure", "Kayak"],
    },
    "airport_flight": {
        "goals": ["threat_reduction", "planning_completion", "affiliation_safety"],
        "mechanism_boosts": {"authority": 0.15, "cognitive_ease": 0.12, "commitment": 0.05},
        "mechanism_penalties": {"curiosity": -0.08, "liking": -0.05},
        "examples": ["FlightAware", "Airport guides", "airline blogs", "TSA info"],
    },
    "productivity_tech": {
        "goals": ["competence_verification", "planning_completion", "status_signaling"],
        "mechanism_boosts": {"cognitive_ease": 0.12, "authority": 0.08, "commitment": 0.05},
        "mechanism_penalties": {"scarcity": -0.05, "liking": -0.03},
        "examples": ["Wired", "TechCrunch", "productivity apps", "Slack blog"],
    },
}

# Archetype baseline conversion probabilities from bilateral evidence
# Derived from outcome distribution: P(convert) ≈ (evangelized + satisfied) / total
# with archetype-specific adjustments from interaction effects
ARCHETYPE_BASE_CONVERSION = {
    "careful_truster": 0.032,
    "status_seeker": 0.038,
    "easy_decider": 0.041,
    "corporate_executive": 0.029,
    "airport_anxiety": 0.026,
    "special_occasion": 0.035,
    "first_timer": 0.022,
    "repeat_loyal": 0.048,
}

# Mechanism effectiveness from bilateral evidence (20-dim scoring)
# Pre-computed from the cascade's edge_mechanism_adjustments formulas
# using the actual LUXY edge averages
MECHANISM_BASE_SCORES = {
    "authority": 0.688,
    "social_proof": 0.528,
    "commitment": 0.532,
    "loss_aversion": 0.549,
    "cognitive_ease": 0.465,
    "curiosity": 0.485,
    "liking": 0.472,
    "scarcity": 0.441,
    "reciprocity": 0.458,
    "unity": 0.412,
}

# Archetype × mechanism affinity (from bilateral evidence + interaction effects)
ARCHETYPE_MECHANISM_AFFINITY = {
    "careful_truster": {"authority": 1.25, "commitment": 1.15, "social_proof": 1.05, "cognitive_ease": 0.90},
    "status_seeker": {"social_proof": 1.30, "scarcity": 1.20, "liking": 1.15, "authority": 0.95},
    "easy_decider": {"cognitive_ease": 1.35, "social_proof": 1.10, "liking": 1.05, "authority": 0.85},
    "corporate_executive": {"authority": 1.30, "commitment": 1.20, "cognitive_ease": 1.05, "social_proof": 0.90},
    "airport_anxiety": {"authority": 1.20, "cognitive_ease": 1.25, "commitment": 1.10, "scarcity": 0.80},
    "special_occasion": {"liking": 1.25, "social_proof": 1.15, "scarcity": 1.10, "authority": 0.85},
    "first_timer": {"curiosity": 1.30, "cognitive_ease": 1.15, "social_proof": 1.10, "commitment": 0.80},
    "repeat_loyal": {"commitment": 1.35, "liking": 1.15, "cognitive_ease": 1.10, "curiosity": 0.80},
}

# Prospect theory: loss aversion amplification for below-threshold dimensions
LOSS_AVERSION_LAMBDA = 2.25
TRUST_THRESHOLD = 0.45
REACTANCE_THRESHOLD = 0.06


@dataclass
class CellPrediction:
    """Prediction for one archetype × mechanism × domain cell."""
    archetype: str
    mechanism: str
    domain_category: str

    # Core predictions
    p_conversion: float = 0.0
    mechanism_score: float = 0.0
    goal_alignment_score: float = 0.0

    # Financial projections
    expected_cpa: float = 0.0
    expected_roas: float = 0.0
    daily_conversions: float = 0.0

    # Confidence
    confidence: float = 0.0
    edge_count: int = 0

    # Reasoning chain
    reasoning: List[str] = field(default_factory=list)

    # Risk factors
    risks: List[str] = field(default_factory=list)


@dataclass
class CampaignForecast:
    """Complete pre-campaign forecast."""
    asin: str
    total_daily_budget: float
    avg_cpm: float
    avg_revenue_per_conversion: float

    # All cell predictions
    predictions: List[CellPrediction] = field(default_factory=list)

    # Recommended allocation
    budget_allocation: Dict[str, float] = field(default_factory=dict)

    # Top recommendations
    top_cells: List[CellPrediction] = field(default_factory=list)
    suppress_cells: List[CellPrediction] = field(default_factory=list)

    # Summary
    total_predicted_conversions: float = 0.0
    total_predicted_revenue: float = 0.0
    predicted_roas: float = 0.0

    generated_at: float = field(default_factory=time.time)


class CampaignSimulator:
    """Pre-campaign performance simulator.

    Composes bilateral evidence, mechanism scoring, goal activation,
    prospect theory, and archetype interaction effects into per-cell
    conversion predictions.
    """

    def __init__(self):
        self._edge_stats: Optional[Dict] = None

    def simulate_campaign(
        self,
        asin: str = "lux_luxy_ride",
        archetypes: Optional[List[str]] = None,
        mechanisms: Optional[List[str]] = None,
        domain_categories: Optional[List[str]] = None,
        daily_budget: float = 250.0,
        avg_cpm: float = 12.0,
        avg_revenue_per_conversion: float = 150.0,
    ) -> CampaignForecast:
        """Simulate campaign performance across all cells."""

        if archetypes is None:
            archetypes = list(ARCHETYPE_BASE_CONVERSION.keys())
        if mechanisms is None:
            mechanisms = ["authority", "social_proof", "cognitive_ease",
                         "commitment", "curiosity", "liking", "scarcity"]
        if domain_categories is None:
            domain_categories = list(DOMAIN_GOAL_PROFILES.keys())

        forecast = CampaignForecast(
            asin=asin,
            total_daily_budget=daily_budget,
            avg_cpm=avg_cpm,
            avg_revenue_per_conversion=avg_revenue_per_conversion,
        )

        # Load edge statistics
        self._load_edge_stats(asin)

        # Simulate each cell
        for arch in archetypes:
            for mech in mechanisms:
                for domain in domain_categories:
                    pred = self._simulate_cell(arch, mech, domain, avg_cpm)
                    forecast.predictions.append(pred)

        # Rank and allocate
        forecast.predictions.sort(key=lambda p: p.p_conversion, reverse=True)
        forecast.top_cells = forecast.predictions[:10]
        forecast.suppress_cells = [
            p for p in forecast.predictions if p.p_conversion < 0.005
        ]

        # Budget allocation via expected value
        self._allocate_budget(forecast, daily_budget, avg_revenue_per_conversion)

        # Summary
        forecast.total_predicted_conversions = sum(
            p.daily_conversions for p in forecast.predictions
            if p.archetype in forecast.budget_allocation
        )
        forecast.total_predicted_revenue = (
            forecast.total_predicted_conversions * avg_revenue_per_conversion
        )
        forecast.predicted_roas = (
            forecast.total_predicted_revenue / max(daily_budget, 1)
        )

        return forecast

    def _load_edge_stats(self, asin: str):
        """Load bilateral edge statistics."""
        try:
            from adam.api.stackadapt.graph_cache import get_graph_cache
            cache = get_graph_cache()
            self._edge_stats = cache.get_edge_aggregates(asin=asin)
        except Exception:
            self._edge_stats = None

    def _simulate_cell(
        self,
        archetype: str,
        mechanism: str,
        domain_category: str,
        avg_cpm: float,
    ) -> CellPrediction:
        """Simulate one archetype × mechanism × domain cell."""
        pred = CellPrediction(
            archetype=archetype,
            mechanism=mechanism,
            domain_category=domain_category,
        )

        # 1. Base conversion rate for this archetype
        base_p = ARCHETYPE_BASE_CONVERSION.get(archetype, 0.03)
        pred.reasoning.append(
            f"Base P(conv) for {archetype}: {base_p:.3f} "
            f"(from bilateral evidence outcome distribution)"
        )

        # 2. Mechanism score from bilateral evidence
        base_mech_score = MECHANISM_BASE_SCORES.get(mechanism, 0.5)

        # Apply archetype × mechanism affinity
        affinity = ARCHETYPE_MECHANISM_AFFINITY.get(archetype, {})
        arch_multiplier = affinity.get(mechanism, 1.0)
        mech_score = base_mech_score * arch_multiplier
        pred.mechanism_score = round(mech_score, 4)
        pred.reasoning.append(
            f"Mechanism {mechanism}: base={base_mech_score:.3f} × "
            f"affinity={arch_multiplier:.2f} = {mech_score:.3f}"
        )

        # 3. Domain goal alignment
        domain_profile = DOMAIN_GOAL_PROFILES.get(domain_category, {})
        goal_boost = domain_profile.get("mechanism_boosts", {}).get(mechanism, 0.0)
        goal_penalty = domain_profile.get("mechanism_penalties", {}).get(mechanism, 0.0)
        goal_alignment = goal_boost + goal_penalty
        pred.goal_alignment_score = round(goal_alignment, 4)

        if goal_alignment > 0:
            pred.reasoning.append(
                f"Domain {domain_category}: +{goal_alignment:.2f} goal alignment "
                f"(goals: {', '.join(domain_profile.get('goals', [])[:2])})"
            )
        elif goal_alignment < 0:
            pred.reasoning.append(
                f"Domain {domain_category}: {goal_alignment:.2f} goal misalignment "
                f"(goals don't activate {mechanism} receptivity)"
            )
            pred.risks.append(
                f"Goal misalignment: {domain_category} doesn't prime for {mechanism}"
            )

        # 4. Prospect theory adjustment
        # If bilateral evidence shows trust below threshold, loss aversion amplifies
        prospect_adj = 0.0
        if self._edge_stats:
            trust = self._edge_stats.get("avg_brand_relationship_depth", 0.5)
            reactance = self._edge_stats.get("avg_autonomy_reactance", 0.5)

            if trust < TRUST_THRESHOLD:
                trust_deficit = TRUST_THRESHOLD - trust
                prospect_adj -= trust_deficit * LOSS_AVERSION_LAMBDA * 0.1
                pred.reasoning.append(
                    f"Prospect theory: trust={trust:.3f} below threshold "
                    f"({TRUST_THRESHOLD}), loss aversion penalty {prospect_adj:+.3f}"
                )
                if mechanism in ("authority", "commitment", "social_proof"):
                    prospect_adj += trust_deficit * 0.05
                    pred.reasoning.append(
                        f"  → {mechanism} partially resolves trust deficit (+{trust_deficit*0.05:.3f})"
                    )

            pred.edge_count = int(self._edge_stats.get("edge_count", 0))

        # 5. Compose final P(conversion)
        # P = base × (1 + mechanism_lift) × (1 + goal_alignment) × (1 + prospect_adj)
        mechanism_lift = (mech_score - 0.5) * 0.8  # Mechanism score → lift
        p_conversion = (
            base_p
            * (1 + mechanism_lift)
            * (1 + goal_alignment)
            * (1 + prospect_adj)
        )
        p_conversion = max(0.001, min(0.15, p_conversion))
        pred.p_conversion = round(p_conversion, 5)

        # 6. Financial projections (per $1000 spend)
        impressions_per_1k = 1000 / max(avg_cpm, 0.01) * 1000
        clicks_per_1k = impressions_per_1k * 0.003  # ~0.3% CTR baseline
        conversions_per_1k = clicks_per_1k * p_conversion
        pred.expected_cpa = round(1000 / max(conversions_per_1k, 0.001), 2)

        # 7. Confidence based on evidence depth
        if self._edge_stats and pred.edge_count > 100:
            pred.confidence = min(0.85, 0.5 + pred.edge_count / 5000)
        elif self._edge_stats:
            pred.confidence = 0.4
        else:
            pred.confidence = 0.2

        pred.reasoning.append(
            f"Final P(conv): {pred.p_conversion:.4f}, CPA: ${pred.expected_cpa:.0f}, "
            f"confidence: {pred.confidence:.2f} ({pred.edge_count} edges)"
        )

        return pred

    def _allocate_budget(
        self,
        forecast: CampaignForecast,
        daily_budget: float,
        avg_revenue: float,
    ):
        """Allocate budget across archetypes using expected value."""
        # Group by archetype, pick best mechanism × domain for each
        arch_best: Dict[str, CellPrediction] = {}
        for pred in forecast.predictions:
            key = pred.archetype
            if key not in arch_best or pred.p_conversion > arch_best[key].p_conversion:
                arch_best[key] = pred

        # Thompson-style allocation: proportional to expected value
        total_ev = sum(
            p.p_conversion * avg_revenue
            for p in arch_best.values()
        )

        if total_ev > 0:
            for arch, pred in arch_best.items():
                ev = pred.p_conversion * avg_revenue
                share = ev / total_ev
                budget = round(daily_budget * share, 2)
                forecast.budget_allocation[arch] = budget

                # Calculate daily conversions for this allocation
                impressions = (budget / max(pred.expected_cpa * pred.p_conversion, 0.01))
                pred.daily_conversions = round(
                    budget / max(pred.expected_cpa, 1), 3
                )
                pred.expected_roas = round(
                    (pred.daily_conversions * avg_revenue) / max(budget, 1), 2
                )


def generate_campaign_forecast(
    asin: str = "lux_luxy_ride",
    daily_budget: float = 250.0,
    avg_cpm: float = 12.0,
    avg_revenue: float = 150.0,
) -> CampaignForecast:
    """Generate a complete pre-campaign forecast."""
    simulator = CampaignSimulator()
    return simulator.simulate_campaign(
        asin=asin,
        daily_budget=daily_budget,
        avg_cpm=avg_cpm,
        avg_revenue_per_conversion=avg_revenue,
    )
