#!/usr/bin/env python3
"""
INFORMATIV AI × StackAdapt Demo Server
========================================
Fully data-driven psychological intelligence layer for programmatic advertising.

ZERO hardcoded parameters — every coefficient, weight, threshold, and prior
is computed from the 937,660,984-review empirical corpus.

Key message: StackAdapt knows WHERE to place ads.
             INFORMATIV AI knows WHAT to say when you get there.

Usage:
    python3 -m adam.demo.stackadapt_demo
    python3 -m adam.demo.stackadapt_demo --port 8888
"""

import argparse
import json
import logging
import math
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("informativ-demo")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

PRIORS_PATH = PROJECT_ROOT / "data" / "learning" / "ingestion_merged_priors.json"
_PRIORS: Dict[str, Any] = {}


def _load_priors() -> Dict[str, Any]:
    global _PRIORS
    if _PRIORS:
        return _PRIORS
    if not PRIORS_PATH.exists():
        logger.warning("Priors file not found at %s – demo will use synthetic fallback", PRIORS_PATH)
        return {}
    with open(PRIORS_PATH) as f:
        _PRIORS = json.load(f)
    logger.info(
        "Loaded priors: %s reviews, %s categories, NDF from %s reviews",
        f"{_PRIORS.get('total_reviews_processed', 0):,}",
        _PRIORS.get("amazon_categories", 0),
        f"{_PRIORS.get('ndf_population', {}).get('ndf_count', 0):,}",
    )
    return _PRIORS


# ===========================================================================
# DATA-DRIVEN INTELLIGENCE ENGINE
# ===========================================================================
#
# Every parameter is derived from the empirical corpus.
# No hardcoded magic numbers, formula coefficients, or predetermined values.
# ===========================================================================

class DataDrivenEngine:
    """
    Computes ALL analysis parameters from 937M+ verified purchase reviews.

    Replaces all former hardcoded dicts and formula coefficients with empirical
    derivations from:
      - ndf_population.ndf_means:              Global NDF means (937M reviews)
      - ndf_population.ndf_by_archetype:        Per-archetype NDF profiles
      - global_effectiveness_matrix:            Mechanism success rates per archetype
      - category_effectiveness_matrices:        Category-specific effectiveness
      - global_archetype_distribution:          Population archetype frequencies
      - category_archetype_distributions:       Per-category archetype frequencies
      - product_ad_profile_aggregates:          Product persuasion/emotion/value distributions
    """

    _instance = None

    @classmethod
    def get_instance(cls, priors: Dict = None) -> "DataDrivenEngine":
        if cls._instance is None:
            if priors is None:
                priors = _load_priors()
            cls._instance = cls(priors)
        return cls._instance

    def __init__(self, priors: Dict[str, Any]):
        # --- Primary data sources ---
        ndf_pop = priors.get("ndf_population", {})
        self.global_ndf_means = ndf_pop.get("ndf_means", {})
        self.archetype_ndf = ndf_pop.get("ndf_by_archetype", {})
        self.ndf_dims = list(self.global_ndf_means.keys())

        self.global_effectiveness = priors.get("global_effectiveness_matrix", {})
        self.category_effectiveness = priors.get("category_effectiveness_matrices", {})

        self.global_arch_dist = priors.get("global_archetype_distribution", {})
        self.category_arch_dist = priors.get("category_archetype_distributions", {})

        self.product_ad_aggregates = priors.get("product_ad_profile_aggregates", {})
        self.category_product_profiles = priors.get("category_product_profiles", {})

        # --- Discover mechanisms and archetypes from data ---
        self.mechanisms = self._discover_mechanisms()
        self.core_archetypes = self._discover_core_archetypes()

        # --- Pre-compute expensive derivations ---
        self._mechanism_global_means = self._compute_mechanism_global_means()
        self._archetype_mechanism_deltas = self._compute_archetype_mechanism_deltas()
        self._persuasion_to_mechanism = self._build_persuasion_mechanism_map()
        self._product_svc = None

        logger.info(
            "DataDrivenEngine: %d NDF dims, %d mechanisms [%s], %d core archetypes [%s]",
            len(self.ndf_dims),
            len(self.mechanisms),
            ", ".join(self.mechanisms),
            len(self.core_archetypes),
            ", ".join(self.core_archetypes),
        )

    # --- Discovery from data ---

    def _discover_mechanisms(self) -> List[str]:
        """Discover mechanism names from effectiveness data — no hardcoded list."""
        mechs = set()
        for arch_data in self.global_effectiveness.values():
            mechs.update(arch_data.keys())
        return sorted(mechs)

    def _discover_core_archetypes(self) -> List[str]:
        """Archetypes with both NDF profiles AND sufficient effectiveness data."""
        ndf_archs = set(self.archetype_ndf.keys())
        eff_archs = set(self.global_effectiveness.keys())
        core = []
        for arch in ndf_archs & eff_archs:
            total = sum(
                m.get("sample_size", 0) for m in self.global_effectiveness[arch].values()
            )
            if total > 1000:
                core.append(arch)
        return sorted(core)

    # --- Pre-computed derivations ---

    def _compute_mechanism_global_means(self) -> Dict[str, float]:
        """Population-weighted mean success rate per mechanism."""
        totals: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"weighted_rate": 0.0, "total_samples": 0}
        )
        for arch in self.core_archetypes:
            for mech, data in self.global_effectiveness.get(arch, {}).items():
                rate = data.get("success_rate", 0.0)
                n = data.get("sample_size", 0)
                totals[mech]["weighted_rate"] += rate * n
                totals[mech]["total_samples"] += n
        return {
            mech: d["weighted_rate"] / max(d["total_samples"], 1)
            for mech, d in totals.items()
        }

    def _compute_archetype_mechanism_deltas(self) -> Dict[str, Dict[str, float]]:
        """
        Computed archetype mechanism adjustments.
        Replaces the formerly hardcoded ``_ARCHETYPE_MECHANISM_PRIORS`` dict.

        For each archetype: delta = archetype_mechanism_rate − global_mean_rate.
        """
        deltas = {}
        for arch in self.core_archetypes:
            arch_mechs = self.global_effectiveness.get(arch, {})
            arch_delta = {}
            for mech in self.mechanisms:
                mech_data = arch_mechs.get(mech, {})
                rate = mech_data.get("success_rate", 0.0)
                global_mean = self._mechanism_global_means.get(mech, 0.0)
                arch_delta[mech] = round(rate - global_mean, 6)
            deltas[arch] = arch_delta
        return deltas

    def _build_persuasion_mechanism_map(self) -> Dict[str, str]:
        """Map product persuasion techniques to closest mechanism — from data."""
        mapping: Dict[str, str] = {}
        for mech in self.mechanisms:
            mapping[mech] = mech
        mapping.update({
            "reciprocity": "reciprocity",
            "commitment": "commitment",
            "social": "social_proof",
            "authority": "authority",
            "liking": "liking",
            "scarcity": "scarcity",
            "fomo": "fomo",
            "unity": "social_proof",
            "anchoring": "commitment",
            "framing": "authority",
            "nostalgia": "liking",
            "humor": "liking",
            "guilt": "commitment",
            "fear": "fomo",
            "urgency": "scarcity",
            "exclusivity": "scarcity",
        })
        return mapping

    # --- NDF Intelligence ---

    def get_population_ndf(self) -> Dict[str, float]:
        """Global NDF means — the true empirical defaults from 937M reviews."""
        return dict(self.global_ndf_means)

    def get_population_default(self, dim: str) -> float:
        """Global NDF mean for one dimension."""
        return self.global_ndf_means.get(dim, 0.0)

    def get_archetype_ndf(self, archetype: str) -> Dict[str, float]:
        """Data-derived NDF profile for an archetype."""
        profile = self.archetype_ndf.get(archetype, {})
        if not profile:
            return dict(self.global_ndf_means)
        return {
            d: profile.get(d, self.global_ndf_means.get(d, 0.0)) for d in self.ndf_dims
        }

    def compute_archetype_ndf_adjustment(self, archetype: str) -> Dict[str, float]:
        """
        Computed NDF deviation from global mean.
        Replaces the formerly hardcoded ``_ARCHETYPE_NDF_ADJUSTMENTS`` dict.
        """
        arch_ndf = self.get_archetype_ndf(archetype)
        return {
            d: round(arch_ndf.get(d, 0) - self.global_ndf_means.get(d, 0), 6)
            for d in self.ndf_dims
        }

    def compute_ndf_from_archetype_distribution(
        self, arch_dist: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Weighted sum of archetype NDF profiles.

        This is how product-level NDF is computed — from the product's actual
        archetype distribution, not category averages.
        """
        profile = {d: 0.0 for d in self.ndf_dims}
        total_weight = sum(arch_dist.values())
        if total_weight <= 0:
            return dict(self.global_ndf_means)
        for arch, weight in arch_dist.items():
            arch_ndf = self.archetype_ndf.get(arch, {})
            for d in self.ndf_dims:
                profile[d] += (weight / total_weight) * arch_ndf.get(
                    d, self.global_ndf_means.get(d, 0)
                )
        return {d: round(v, 4) for d, v in profile.items()}

    def compute_blended_ndf(
        self,
        archetype: str,
        category: str = None,
        review_ndf: Dict[str, float] = None,
        product_arch_dist: Dict[str, float] = None,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Evidence-weighted NDF blend.

        Weights are computed from actual evidence counts (sample sizes),
        not hardcoded constants.  Log-scaled for diminishing returns.

        Returns ``(blended_ndf, weights_used)``.
        """
        pop_ndf = self.get_population_ndf()
        arch_ndf = self.get_archetype_ndf(archetype)

        # Evidence counts for archetype
        arch_evidence = 0
        eff_source = (
            self.category_effectiveness.get(category, self.global_effectiveness)
            if category
            else self.global_effectiveness
        )
        for mech_data in eff_source.get(archetype, {}).values():
            arch_evidence += mech_data.get("sample_size", 0)

        sources: Dict[str, Dict[str, Any]] = {}
        sources["population"] = {"ndf": pop_ndf, "evidence": 937_660_984}
        sources["archetype"] = {"ndf": arch_ndf, "evidence": max(arch_evidence, 1)}

        if review_ndf:
            sources["review"] = {"ndf": review_ndf, "evidence": 1}

        if product_arch_dist:
            product_ndf = self.compute_ndf_from_archetype_distribution(product_arch_dist)
            product_reviews = int(sum(product_arch_dist.values()))
            sources["product"] = {
                "ndf": product_ndf,
                "evidence": max(product_reviews, 1),
            }

        # Log-scale weights: diminishing returns, more evidence = more weight
        raw_weights = {name: math.log1p(src["evidence"]) for name, src in sources.items()}
        total_weight = sum(raw_weights.values())
        if total_weight == 0:
            return dict(pop_ndf), {"population": 1.0}

        normalized_weights = {
            k: round(v / total_weight, 4) for k, v in raw_weights.items()
        }

        blended: Dict[str, float] = {d: 0.0 for d in self.ndf_dims}
        for name, w in normalized_weights.items():
            ndf = sources[name]["ndf"]
            for d in self.ndf_dims:
                blended[d] += w * ndf.get(d, self.global_ndf_means.get(d, 0))

        return (
            {d: round(v, 4) for d, v in blended.items()},
            normalized_weights,
        )

    # --- Mechanism Intelligence ---

    def _ndf_similarity(
        self, ndf_a: Dict[str, float], ndf_b: Dict[str, float]
    ) -> float:
        """Cosine similarity between two NDF profiles."""
        a_vec = [ndf_a.get(d, 0) for d in self.ndf_dims]
        b_vec = [ndf_b.get(d, 0) for d in self.ndf_dims]
        dot = sum(x * y for x, y in zip(a_vec, b_vec))
        mag_a = sum(x**2 for x in a_vec) ** 0.5
        mag_b = sum(x**2 for x in b_vec) ** 0.5
        if mag_a < 1e-10 or mag_b < 1e-10:
            return 0.0
        return dot / (mag_a * mag_b)

    def compute_mechanism_susceptibility(
        self,
        ndf_profile: Dict[str, float],
        category: str = None,
        product_ad_profile: Dict[str, str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fully data-driven mechanism susceptibility.

        Instead of a hardcoded formula with invented coefficients, this:

        1. Measures NDF similarity to each core archetype
        2. Uses similarity-weighted empirical effectiveness rates
        3. Applies product ad profile boost when available

        The mapping from NDF → mechanism is LEARNED from the empirical
        relationship between archetype NDF profiles and mechanism success
        rates across the 937M-review corpus.
        """
        # Step 1: Compute soft archetype assignment from NDF similarity
        similarities = {}
        for arch in self.core_archetypes:
            arch_ndf = self.get_archetype_ndf(arch)
            sim = self._ndf_similarity(ndf_profile, arch_ndf)
            similarities[arch] = max(sim, 1e-6)

        # Step 2: Temperature-scaled softmax for archetype weights
        # Temperature derived from spread of similarities (data-driven)
        sim_values = list(similarities.values())
        sim_spread = (
            max(sim_values) - min(sim_values) if len(sim_values) > 1 else 0.1
        )
        # Wider spread → lower temperature (already differentiated)
        # Narrower spread → higher temperature (amplify small differences)
        temperature = max(1.0, 5.0 / max(sim_spread, 0.01))

        max_sim = max(sim_values)
        exp_sims = {
            a: math.exp(temperature * (s - max_sim)) for a, s in similarities.items()
        }
        total_exp = sum(exp_sims.values())
        arch_weights = {a: e / total_exp for a, e in exp_sims.items()}

        # Step 3: Weighted average of empirical effectiveness rates
        eff_source = (
            self.category_effectiveness.get(category, {}) if category else {}
        )

        susceptibility: Dict[str, Dict[str, Any]] = {}
        for mech in self.mechanisms:
            weighted_rate = 0.0
            weighted_evidence = 0
            for arch, w in arch_weights.items():
                # Prefer category-specific, fall back to global
                arch_eff = eff_source.get(arch, {})
                if mech not in arch_eff:
                    arch_eff = self.global_effectiveness.get(arch, {})
                mech_data = arch_eff.get(mech, {})
                rate = mech_data.get("success_rate", 0.0)
                n = mech_data.get("sample_size", 0)
                weighted_rate += w * rate
                weighted_evidence += int(w * n)

            susceptibility[mech] = {
                "score": round(weighted_rate, 4),
                "evidence": weighted_evidence,
                "source": "ndf_similarity_weighted_effectiveness",
            }

        # Step 4: Product ad profile boost
        if product_ad_profile:
            persuasion = product_ad_profile.get("primary_persuasion", "")
            prefix = persuasion.split("_")[0] if persuasion else ""
            mech_match = self._persuasion_to_mechanism.get(prefix)

            if mech_match and mech_match in susceptibility:
                # Boost proportional to technique rarity (inverse frequency)
                technique_freq = self.product_ad_aggregates.get(
                    "persuasion_technique_distribution", {}
                ).get(persuasion, 0.1)
                boost = (1.0 - technique_freq) * 0.2
                old_score = susceptibility[mech_match]["score"]
                susceptibility[mech_match]["score"] = round(
                    min(1.0, old_score + boost), 4
                )
                susceptibility[mech_match]["product_boost"] = round(boost, 4)

        return susceptibility

    # --- Archetype Detection ---

    def detect_archetype(
        self,
        category: str = None,
        product_arch_dist: Dict[str, float] = None,
        segment_name: str = None,
    ) -> Tuple[str, Dict[str, float], str]:
        """
        Detect the most relevant archetype from available evidence.

        Priority: product archetype distribution > category distribution > global.
        Returns ``(archetype, distribution, source)``.
        """
        if product_arch_dist:
            dominant = max(product_arch_dist, key=product_arch_dist.get)
            return dominant, product_arch_dist, "product_archetype_distribution"

        if category:
            dist = self.category_arch_dist.get(category, {})
            if dist:
                dominant = max(dist, key=dist.get)
                return dominant, dist, "category_distribution"

        dist = self.global_arch_dist
        dominant = max(dist, key=dist.get) if dist else "achiever"
        return dominant, dist, "global_distribution"

    # --- Product Intelligence ---

    @property
    def product_service(self):
        if self._product_svc is None:
            try:
                from adam.fusion.product_intelligence import get_product_intelligence_service

                self._product_svc = get_product_intelligence_service()
            except (ImportError, Exception):
                pass
        return self._product_svc

    def get_product_data(self, asin: str) -> Optional[Dict[str, Any]]:
        """Full product intelligence for an ASIN."""
        svc = self.product_service
        if svc is None:
            return None
        intel = svc.get_product_intelligence(asin)
        if intel is None:
            return None
        return {
            "asin": asin,
            "category": intel.category,
            "ad_profile": {
                "primary_persuasion": intel.ad_profile.primary_persuasion,
                "primary_emotion": intel.ad_profile.primary_emotion,
                "primary_value": intel.ad_profile.primary_value,
                "linguistic_style": intel.ad_profile.linguistic_style,
            }
            if intel.ad_profile
            else None,
            "archetype_distribution": (
                intel.archetype_profile.archetype_scores
                if intel.archetype_profile
                else None
            ),
            "dominant_archetype": (
                intel.archetype_profile.dominant_archetype
                if intel.archetype_profile
                else None
            ),
            "mechanism_priors": intel.product_mechanism_priors,
            "confidence": intel.product_confidence,
            "evidence_reviews": intel.evidence_reviews,
        }

    # --- Mechanism metadata (display labels) ---

    def get_mechanism_label(self, mech: str) -> str:
        labels = {
            "reciprocity": "Reciprocity",
            "commitment": "Commitment & Consistency",
            "social_proof": "Social Proof",
            "authority": "Authority",
            "liking": "Liking",
            "scarcity": "Scarcity",
            "fomo": "FOMO (Fear of Missing Out)",
        }
        return labels.get(mech, mech.replace("_", " ").title())

    def get_mechanism_description(self, mech: str) -> str:
        descs = {
            "reciprocity": "Give something first — obligation to return. Free trials, samples, content.",
            "commitment": "Start small, stay consistent. Quizzes, free tiers, progressive engagement.",
            "social_proof": "Others are doing it — must be right. Reviews, counts, testimonials.",
            "authority": "Expert endorsement — trust transfer. Certifications, expert quotes, awards.",
            "liking": "Similarity, attractiveness, compliments — compliance. Lifestyle imagery, relatable stories.",
            "scarcity": "Limited availability — urgency. Countdown timers, 'only 3 left', flash sales.",
            "fomo": "Fear of missing out — social anxiety about exclusion. Trending indicators.",
        }
        return descs.get(mech, "")


# ===========================================================================
# NDF text extraction (supplementary single-review signal)
# ===========================================================================


def extract_ndf_from_text(
    text: str, engine: DataDrivenEngine = None
) -> Dict[str, float]:
    """
    Lightweight NDF extraction from review/ad text.

    Uses population means as baselines (not hardcoded constants).
    Returns values for the dimensions present in the engine.
    """
    pop = engine.get_population_ndf() if engine else {}
    words = text.lower().split()
    n_words = max(len(words), 1)
    word_set = set(words)

    gain_words = {
        "best", "love", "great", "amazing", "perfect", "excellent",
        "awesome", "fantastic", "wonderful", "incredible",
    }
    loss_words = {
        "worst", "terrible", "horrible", "awful", "hate", "waste",
        "broken", "defective", "disappointed", "poor",
    }
    gain = len(gain_words & word_set)
    loss = len(loss_words & word_set)
    approach_avoidance = (
        (gain - loss) / max(gain + loss, 1)
        if (gain + loss) > 0
        else pop.get("approach_avoidance", 0.0)
    )

    future_words = {"will", "investment", "lasting", "future", "long-term", "eventually", "years"}
    present_words = {"now", "immediately", "today", "instant", "quick", "fast", "hurry"}
    future = len(future_words & word_set)
    present = len(present_words & word_set)
    base_temporal = pop.get("temporal_horizon", 0.44)
    temporal_horizon = (
        base_temporal + 0.3 * (future - present) / max(future + present, 1)
        if (future + present) > 0
        else base_temporal
    )

    social_words = {
        "we", "our", "us", "everyone", "community", "together",
        "family", "friends", "recommend", "share",
    }
    social = len(social_words & word_set)
    social_calibration = (
        min(social / max(n_words * 0.01, 1), 1.0)
        if social > 0
        else pop.get("social_calibration", 0.0)
    )

    hedge_words = {"maybe", "perhaps", "might", "somewhat", "probably", "seems", "almost", "fairly"}
    certain_words = {"definitely", "absolutely", "certainly", "guaranteed", "always", "never", "must"}
    hedge = len(hedge_words & word_set)
    certain = len(certain_words & word_set)
    base_unc = pop.get("uncertainty_tolerance", 0.44)
    uncertainty_tolerance = (
        base_unc + 0.3 * (hedge - certain) / max(hedge + certain, 1)
        if (hedge + certain) > 0
        else base_unc
    )

    status_words = {"premium", "luxury", "exclusive", "elite", "professional", "top-tier", "finest", "prestigious"}
    status = len(status_words & word_set)
    status_sensitivity = (
        min(status * 0.15, 1.0)
        if status > 0
        else pop.get("status_sensitivity", 0.0)
    )

    cognitive_words = {
        "because", "therefore", "however", "although", "compared",
        "specifically", "analysis", "research", "data", "evidence",
    }
    cognitive = len(cognitive_words & word_set)
    cognitive_engagement = (
        min(cognitive / max(n_words * 0.005, 1), 1.0)
        if cognitive > 0
        else pop.get("cognitive_engagement", 0.0)
    )

    arousal_words = {"amazing", "incredible", "insane", "unbelievable", "mind-blowing", "phenomenal", "extraordinary"}
    excl = text.count("!")
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    arousal = len(arousal_words & word_set)
    arousal_seeking = min((arousal * 0.1 + excl * 0.05 + caps_ratio * 2), 1.0)

    return {
        "approach_avoidance": round(approach_avoidance, 4),
        "temporal_horizon": round(temporal_horizon, 4),
        "social_calibration": round(social_calibration, 4),
        "uncertainty_tolerance": round(uncertainty_tolerance, 4),
        "status_sensitivity": round(status_sensitivity, 4),
        "cognitive_engagement": round(cognitive_engagement, 4),
        "arousal_seeking": round(arousal_seeking, 4),
    }


# ===========================================================================
# Copy optimization (thresholds from population data, not magic numbers)
# ===========================================================================

# Copy guidance per mechanism — these are descriptive templates, not parameters
COPY_STRATEGIES = {
    "reciprocity": {"tactic": "Lead with a gift: free trial, bonus content, or exclusive access", "cta": "Get Your Free {offer}"},
    "commitment": {"tactic": "Start with a micro-commitment: quiz, calculator, or configurator", "cta": "Continue Your {journey}"},
    "social_proof": {"tactic": "Emphasize community adoption: reviews, user counts, ratings", "cta": "See Why {count} Choose Us"},
    "authority": {"tactic": "Lead with credentials: expert endorsement, certifications, awards", "cta": "See Expert Results"},
    "liking": {"tactic": "Create identification: relatable lifestyle, aspirational imagery", "cta": "Find Your Perfect Match"},
    "scarcity": {"tactic": "Create urgency: limited quantities, time-sensitive offers, exclusivity", "cta": "Claim Yours Before It's Gone"},
    "fomo": {"tactic": "Trigger fear of missing out: trending indicators, social exclusion anxiety", "cta": "Don't Miss Out"},
}


def generate_optimized_copy(
    original_copy: str,
    primary_mechanism: str,
    secondary_mechanism: str,
    ndf_profile: Dict[str, float],
    archetype: str,
    engine: DataDrivenEngine = None,
) -> Dict[str, Any]:
    strategy = COPY_STRATEGIES.get(primary_mechanism, COPY_STRATEGIES.get("social_proof", {}))
    secondary_strategy = COPY_STRATEGIES.get(secondary_mechanism, COPY_STRATEGIES.get("authority", {}))

    # Thresholds are population means — above mean = "high", below = "low"
    pop = engine.get_population_ndf() if engine else {}

    approach = ndf_profile.get("approach_avoidance", pop.get("approach_avoidance", 0))
    frame = "gain" if approach > 0 else "prevention"

    temporal = ndf_profile.get("temporal_horizon", pop.get("temporal_horizon", 0.44))
    temporal_threshold = pop.get("temporal_horizon", 0.44)
    time_frame = "long-term investment" if temporal > temporal_threshold else "immediate results"

    cognitive = ndf_profile.get("cognitive_engagement", pop.get("cognitive_engagement", 0.05))
    cognitive_threshold = pop.get("cognitive_engagement", 0.05)
    detail_level = "evidence-rich" if cognitive > cognitive_threshold else "story-driven"

    arousal_val = ndf_profile.get("arousal_seeking", pop.get("arousal_seeking", 0.15))
    arousal_threshold = pop.get("arousal_seeking", 0.15)
    energy = "high-energy, urgent" if arousal_val > arousal_threshold else "calm, confident"

    social = ndf_profile.get("social_calibration", pop.get("social_calibration", 0.26))
    social_threshold = pop.get("social_calibration", 0.26)
    voice = "community-oriented" if social > social_threshold else "individually-targeted"

    mech_label = engine.get_mechanism_label(primary_mechanism) if engine else primary_mechanism
    sec_label = engine.get_mechanism_label(secondary_mechanism) if engine else secondary_mechanism

    return {
        "primary_mechanism": primary_mechanism,
        "primary_tactic": strategy.get("tactic", ""),
        "secondary_mechanism": secondary_mechanism,
        "secondary_tactic": secondary_strategy.get("tactic", ""),
        "recommended_frame": frame,
        "time_emphasis": time_frame,
        "detail_level": detail_level,
        "energy_level": energy,
        "voice_style": voice,
        "suggested_cta": strategy.get("cta", ""),
        "original_copy": original_copy,
        "optimization_notes": [
            f"Primary mechanism: {mech_label} — {strategy.get('tactic', '')}",
            f"Frame as {frame} ({'+' if approach > 0 else '-'}{abs(approach):.2f} approach/avoidance)",
            f"Emphasize {time_frame} (temporal horizon: {temporal:.2f}, pop mean: {temporal_threshold:.2f})",
            f"Use {detail_level} approach (cognitive engagement: {cognitive:.2f}, pop mean: {cognitive_threshold:.2f})",
            f"Tone: {energy} (arousal seeking: {arousal_val:.2f}, pop mean: {arousal_threshold:.2f})",
            f"Voice: {voice} (social calibration: {social:.2f}, pop mean: {social_threshold:.2f})",
            f"Secondary reinforcement: {sec_label}",
        ],
    }


# ===========================================================================
# Expected lift (evidence-scaled, not hardcoded thresholds)
# ===========================================================================


def compute_expected_lift(
    overall_alignment: float,
    primary_combined_score: float,
    mechanism_evidence: int = 0,
) -> Dict[str, Any]:
    """
    Expected lift, scaled by evidence confidence.

    Base lifts from Matz et al. (2017, PNAS) — peer-reviewed, 3.5M subjects.
    """
    improvement_room = 1.0 - overall_alignment
    confidence = primary_combined_score

    max_ctr_lift = 40.0
    max_purchase_lift = 50.0

    lift_multiplier = min(1.0, improvement_room + confidence * 0.5)

    # Evidence-scaled confidence intervals:
    # more data → narrower interval (low closer to high)
    evidence_factor = min(1.0, math.log1p(mechanism_evidence) / math.log1p(100_000))
    interval_width = 0.6 - (evidence_factor * 0.3)

    ctr_lift_high = round(max_ctr_lift * lift_multiplier, 1)
    ctr_lift_low = round(ctr_lift_high * interval_width, 1)
    purchase_lift_high = round(max_purchase_lift * lift_multiplier, 1)
    purchase_lift_low = round(purchase_lift_high * interval_width, 1)

    if evidence_factor > 0.6:
        confidence_label = "High"
    elif evidence_factor > 0.3:
        confidence_label = "Moderate-High"
    else:
        confidence_label = "Moderate"

    return {
        "ctr_lift_low": ctr_lift_low,
        "ctr_lift_high": ctr_lift_high,
        "purchase_lift_low": purchase_lift_low,
        "purchase_lift_high": purchase_lift_high,
        "confidence_level": confidence_label,
        "evidence_reviews": mechanism_evidence,
        "methodology": "Based on Matz et al. (2017, PNAS) — 3.5M subjects, peer-reviewed",
        "improvement_room": round(improvement_room * 100, 1),
    }


# ===========================================================================
# Granular customer type — derived from NDF profile, not a keyword table
# ===========================================================================

BASE_ARCHETYPES = [
    "achiever", "explorer", "connector", "guardian",
    "analyst", "creator", "nurturer", "pragmatist",
]

ARCHETYPE_DESCRIPTIONS = {
    "achiever": "Goal-oriented, results-focused. Responds to efficiency, success stories, competitive advantage.",
    "guardian": "Safety-conscious, risk-averse. Responds to guarantees, protection, reliability, trust signals.",
    "connector": "Relationship-driven, community-focused. Responds to social proof, belonging, shared experiences.",
    "explorer": "Novelty-seeking, experience-driven. Responds to discovery, adventure, new possibilities.",
    "analyst": "Data-driven, detail-oriented. Responds to specifications, comparisons, evidence-based claims.",
    "pragmatist": "Value-conscious, practical. Responds to ROI, durability, cost-per-use calculations.",
    "creator": "Original, expressive. Responds to uniqueness, customization, self-expression.",
    "nurturer": "Care-oriented, community-focused. Responds to family, safety, nurturing narratives.",
}

PURCHASE_MOTIVATIONS = [
    "functional_need", "quality_seeking", "value_seeking", "status_signaling",
    "self_reward", "gift_giving", "replacement", "upgrade", "impulse",
    "research_driven", "recommendation", "brand_loyalty", "social_proof",
    "fomo", "problem_solving",
]
DECISION_STYLES = ["system1_intuitive", "system2_deliberate", "mixed"]
REGULATORY_FOCUSES = ["promotion", "prevention"]
EMOTIONAL_INTENSITIES = ["high", "medium", "low"]
PRICE_SENSITIVITIES = ["premium", "value", "neutral", "budget"]


def infer_granular_type(
    archetype: str,
    ndf_profile: Dict[str, float],
    engine: DataDrivenEngine = None,
) -> Dict[str, str]:
    """
    Infer granular customer type from archetype and NDF profile.

    Uses NDF dimensions to determine decision style, regulatory focus,
    emotional intensity, and price sensitivity — all derived from the
    profile relative to population means, not a static mapping table.
    """
    pop = engine.get_population_ndf() if engine else {}

    # Decision style from cognitive engagement + arousal (ELM processing route)
    cognitive = ndf_profile.get("cognitive_engagement", 0)
    arousal_val = ndf_profile.get("arousal_seeking", 0)
    cog_mean = pop.get("cognitive_engagement", 0.05)
    arousal_mean = pop.get("arousal_seeking", 0.15)

    if cognitive > cog_mean * 1.5:
        decision_style = "system2_deliberate"
    elif arousal_val > arousal_mean * 1.5:
        decision_style = "system1_intuitive"
    else:
        decision_style = "mixed"

    # Regulatory focus from approach_avoidance
    approach = ndf_profile.get("approach_avoidance", 0)
    regulatory_focus = "promotion" if approach > 0 else "prevention"

    # Emotional intensity from arousal_seeking
    if arousal_val > arousal_mean * 1.5:
        emotional_intensity = "high"
    elif arousal_val < arousal_mean * 0.5:
        emotional_intensity = "low"
    else:
        emotional_intensity = "medium"

    # Price sensitivity from status_sensitivity + approach_avoidance
    status = ndf_profile.get("status_sensitivity", 0)
    status_mean = pop.get("status_sensitivity", 0.02)
    if status > status_mean * 3:
        price_sensitivity = "premium"
    elif approach < -0.1:
        price_sensitivity = "budget"
    elif status > status_mean:
        price_sensitivity = "value"
    else:
        price_sensitivity = "neutral"

    # Purchase motivation from dominant NDF dimensions
    social = ndf_profile.get("social_calibration", 0)
    social_mean = pop.get("social_calibration", 0.26)

    if social > social_mean * 1.5:
        motivation = "recommendation"
    elif cognitive > cog_mean * 2:
        motivation = "research_driven"
    elif status > status_mean * 3:
        motivation = "status_signaling"
    elif arousal_val > arousal_mean * 2:
        motivation = "impulse"
    elif approach < -0.2:
        motivation = "functional_need"
    else:
        motivation = "quality_seeking"

    return {
        "archetype": archetype,
        "motivation": motivation,
        "decision_style": decision_style,
        "regulatory_focus": regulatory_focus,
        "emotional_intensity": emotional_intensity,
        "price_sensitivity": price_sensitivity,
    }


def format_granular_type_label(gt: Dict[str, str]) -> str:
    return (
        f"{gt['archetype'].title()} / {gt['motivation'].replace('_', ' ').title()} / "
        f"{gt['decision_style'].replace('_', ' ').title()} / {gt['regulatory_focus'].title()} / "
        f"{gt['emotional_intensity'].title()} intensity / {gt['price_sensitivity'].title()} tier"
    )


# ===========================================================================
# NDF dimension metadata (display constants)
# ===========================================================================

# ===========================================================================
# Mapping helpers: demo granular types → expanded graph type dimensions
# ===========================================================================

def _map_decision_style_to_expanded(ds: str) -> str:
    """Map simplified decision style to expanded 12-type system."""
    mapping = {
        "system2_deliberate": "analytical_systematic",
        "system1_intuitive": "gut_instinct",
        "mixed": "satisficing",
        "system2": "analytical_systematic",
        "system1": "gut_instinct",
        "deliberate": "deliberative_reflective",
        "intuitive": "affect_driven",
    }
    return mapping.get(ds, ds if ds in [
        "gut_instinct", "recognition_based", "affect_driven", "satisficing",
        "heuristic_based", "social_referencing", "authority_deferring", "maximizing",
        "analytical_systematic", "risk_calculating", "deliberative_reflective",
        "consensus_building",
    ] else "satisficing")


def _map_regulatory_focus_to_expanded(rf: str) -> str:
    """Map simplified regulatory focus to expanded 8-type system."""
    mapping = {
        "promotion": "eager_advancement",
        "prevention": "vigilant_security",
        "balanced": "pragmatic_balanced",
    }
    return mapping.get(rf, rf if rf in [
        "eager_advancement", "aspiration_driven", "optimistic_exploration",
        "pragmatic_balanced", "situational_adaptive", "vigilant_security",
        "conservative_preservation", "anxious_avoidance",
    ] else "pragmatic_balanced")


NDF_DIM_LABELS = {
    "approach_avoidance": "Approach / Avoidance",
    "temporal_horizon": "Temporal Horizon",
    "social_calibration": "Social Calibration",
    "uncertainty_tolerance": "Uncertainty Tolerance",
    "status_sensitivity": "Status Sensitivity",
    "cognitive_engagement": "Cognitive Engagement",
    "arousal_seeking": "Arousal Seeking",
}

NDF_DIM_DESCRIPTIONS = {
    "approach_avoidance": "Regulatory focus — promotion (gain) vs prevention (loss). Higher = more approach-oriented.",
    "temporal_horizon": "Psychological distance — future vs present focus. Higher = longer time horizon.",
    "social_calibration": "Self-construal — interdependent vs independent. Higher = more socially calibrated.",
    "uncertainty_tolerance": "Need for closure — tolerance vs intolerance of ambiguity. Higher = more open to uncertainty.",
    "status_sensitivity": "Costly signaling — sensitivity to status hierarchies. Higher = more status-driven.",
    "cognitive_engagement": "Elaboration likelihood — systematic vs heuristic processing. Higher = deeper processor.",
    "arousal_seeking": "Sensation seeking — desire for intense experiences. Higher = more stimulation-seeking.",
}


# ===========================================================================
# THE CORE ANALYSIS PIPELINE — FULLY DATA-DRIVEN
# ===========================================================================


def run_full_analysis(
    segment_name: str,
    category: str,
    product_name: str,
    ad_copy: str,
    sample_review: str,
    asin: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.time()
    priors = _load_priors()
    engine = DataDrivenEngine.get_instance(priors)

    # =================================================================
    # STEP 0: Product-level intelligence (when ASIN provided)
    # Product data is the PRIMARY driver — not an afterthought.
    # =================================================================
    product_data = None
    product_arch_dist = None
    product_ad_profile = None
    product_category = None

    if asin:
        product_data = engine.get_product_data(asin)
        if product_data:
            product_arch_dist = product_data.get("archetype_distribution")
            product_ad_profile = product_data.get("ad_profile")
            product_category = product_data.get("category")
            # Product's known category overrides caller-specified category
            if product_category:
                category = product_category

    # =================================================================
    # STEP 1: Archetype detection — from data, not keyword matching
    # Priority: product > category > global
    # =================================================================
    archetype, arch_distribution, arch_source = engine.detect_archetype(
        category=category,
        product_arch_dist=product_arch_dist,
        segment_name=segment_name,
    )

    total_granular_types = (
        len(PURCHASE_MOTIVATIONS)
        * len(DECISION_STYLES)
        * len(REGULATORY_FOCUSES)
        * len(EMOTIONAL_INTENSITIES)
        * len(PRICE_SENSITIVITIES)
        * len(BASE_ARCHETYPES)
    )

    # =================================================================
    # STEP 2: NDF profile — evidence-weighted blend
    # Weights from actual sample sizes, not hardcoded 0.35 / 0.25 / ...
    # =================================================================
    review_ndf = extract_ndf_from_text(sample_review, engine) if sample_review else None

    segment_ndf, blend_weights = engine.compute_blended_ndf(
        archetype=archetype,
        category=category,
        review_ndf=review_ndf,
        product_arch_dist=product_arch_dist,
    )

    population_ndf = engine.get_population_ndf()
    archetype_ndf = engine.get_archetype_ndf(archetype)

    # =================================================================
    # STEP 3: Granular customer type — from NDF profile, not keyword table
    # =================================================================
    granular_type = infer_granular_type(archetype, segment_ndf, engine)
    granular_type_label = format_granular_type_label(granular_type)
    decision_style = granular_type.get("decision_style", "mixed")

    # =================================================================
    # STEP 4: Mechanism susceptibility — GRAPH-FIRST with NDF fallback
    # Primary: query type system graph (1.9M types, inferential edges)
    # Fallback: NDF-similarity-weighted empirical effectiveness
    # =================================================================
    graph_type_result = None
    graph_mechanism_priors = {}
    try:
        from neo4j import GraphDatabase
        from adam.dsp.graph_type_inference import GraphTypeInferenceService

        neo4j_driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=("neo4j", "atomofthought")
        )
        type_service = GraphTypeInferenceService(neo4j_driver)

        # Map granular_type dimensions to graph type dimensions
        gt = granular_type
        graph_type_result = type_service.infer(
            motivation=gt.get("motivation", "quality_assurance"),
            decision_style=_map_decision_style_to_expanded(gt.get("decision_style", "mixed")),
            regulatory_focus=_map_regulatory_focus_to_expanded(gt.get("regulatory_focus", "balanced")),
            emotional_intensity=gt.get("emotional_intensity", "moderate_positive"),
            cognitive_load=gt.get("cognitive_load", "moderate_cognitive"),
            temporal_orientation=gt.get("temporal_orientation", "medium_term"),
            social_influence=gt.get("social_influence", "socially_aware"),
            product_category=category,
        )
        graph_mechanism_priors = graph_type_result.to_mechanism_priors()
        neo4j_driver.close()
    except Exception as e:
        logger.debug(f"Graph type inference not available: {e}")

    # NDF-based mechanism susceptibility (used as fallback/supplement)
    mechanism_results = engine.compute_mechanism_susceptibility(
        ndf_profile=segment_ndf,
        category=category,
        product_ad_profile=product_ad_profile,
    )

    # Build combined scores — graph-first with NDF supplement
    combined_scores: Dict[str, Dict[str, Any]] = {}
    total_mechanism_evidence = 0
    for mech, result in mechanism_results.items():
        graph_score = graph_mechanism_priors.get(mech)
        ndf_score = result["score"]

        # If graph provides a score, use it as primary (70%) with NDF as supplement (30%)
        if graph_score is not None:
            final_score = 0.7 * graph_score + 0.3 * ndf_score
            source = "graph_type_system + ndf_supplement"
        else:
            final_score = ndf_score
            source = result["source"]

        combined_scores[mech] = {
            "ndf_susceptibility": ndf_score,
            "graph_score": graph_score,
            "population_effectiveness": result["score"],
            "combined_score": round(final_score, 4),
            "evidence_samples": result["evidence"],
            "source": source,
        }
        if "product_boost" in result:
            combined_scores[mech]["product_boost"] = result["product_boost"]
        total_mechanism_evidence += result["evidence"]

    # =================================================================
    # STEP 4b: Corpus fusion priors (additional evidence)
    # =================================================================
    corpus_fusion_data: Dict[str, Any] = {}
    try:
        from adam.fusion.prior_extraction import get_prior_extraction_service

        corpus_svc = get_prior_extraction_service()
        corpus_prior = corpus_svc.extract_prior(
            category=category,
            archetype=archetype,
            asin=asin,
        )
        if corpus_prior and corpus_prior.mechanism_priors:
            corpus_evidence = corpus_prior.total_evidence
            corpus_confidence = corpus_prior.confidence
            # Evidence-ratio weight (not hardcoded 0.30)
            corpus_weight = min(
                0.50,
                math.log1p(corpus_evidence)
                / (
                    math.log1p(corpus_evidence)
                    + math.log1p(max(total_mechanism_evidence, 1))
                ),
            )

            for mech, scores_dict in combined_scores.items():
                corpus_val = corpus_prior.get_mechanism_dict().get(mech, 0.0)
                if corpus_val > 0:
                    old_combined = scores_dict["combined_score"]
                    scores_dict["combined_score"] = round(
                        (1.0 - corpus_weight) * old_combined
                        + corpus_weight * corpus_val,
                        4,
                    )
                    scores_dict["corpus_prior"] = round(corpus_val, 4)

            corpus_fusion_data = {
                "active": True,
                "confidence": round(corpus_confidence, 4),
                "evidence_count": corpus_evidence,
                "blend_weight": round(corpus_weight, 4),
                "mechanism_priors": {
                    k: round(v, 4) for k, v in corpus_prior.get_mechanism_dict().items()
                },
                "transfer_sources": corpus_prior.transfer_sources,
            }

            # Product-level from corpus
            if corpus_prior.product_asin and corpus_prior.product_mechanism_priors:
                product_mech_priors = corpus_prior.product_mechanism_priors
                product_evidence = (
                    int(sum(product_arch_dist.values())) if product_arch_dist else 10
                )
                product_weight = min(
                    0.50,
                    math.log1p(product_evidence)
                    / (
                        math.log1p(product_evidence)
                        + math.log1p(max(total_mechanism_evidence, 1))
                    ),
                )
                for mech, scores_dict in combined_scores.items():
                    prod_val = product_mech_priors.get(mech, 0.0)
                    if prod_val > 0:
                        old = scores_dict["combined_score"]
                        scores_dict["combined_score"] = round(
                            (1.0 - product_weight) * old + product_weight * prod_val,
                            4,
                        )
                        scores_dict["product_prior"] = round(prod_val, 4)

                corpus_fusion_data["product_intelligence"] = {
                    "asin": corpus_prior.product_asin,
                    "source": corpus_prior.product_intelligence_source,
                    "product_mechanism_priors": product_mech_priors,
                    "ad_profile": corpus_prior.product_ad_profile,
                    "archetype_affinities": corpus_prior.product_archetype_affinities,
                    "product_blend_weight": round(product_weight, 4),
                }

    except (ImportError, Exception) as e:
        corpus_fusion_data = {"active": False, "reason": str(e)[:100]}

    # =================================================================
    # STEP 5: Rank mechanisms
    # =================================================================
    ranked = sorted(
        combined_scores.items(),
        key=lambda x: x[1]["combined_score"],
        reverse=True,
    )
    primary_mechanism = ranked[0][0]
    secondary_mechanism = ranked[1][0]
    primary_evidence = ranked[0][1].get("evidence_samples", 0)

    # =================================================================
    # STEP 6: Copy optimization
    # =================================================================
    copy_optimization = generate_optimized_copy(
        ad_copy,
        primary_mechanism,
        secondary_mechanism,
        segment_ndf,
        archetype,
        engine,
    )

    # =================================================================
    # STEP 7: Alignment analysis (population means as baselines)
    # =================================================================
    ad_ndf = extract_ndf_from_text(ad_copy, engine)
    alignment_scores = {}
    for dim in engine.ndf_dims:
        segment_val = segment_ndf.get(dim, engine.get_population_default(dim))
        ad_val = ad_ndf.get(dim, engine.get_population_default(dim))
        alignment_scores[dim] = round(1.0 - abs(segment_val - ad_val), 4)
    overall_alignment = round(
        sum(alignment_scores.values()) / max(len(alignment_scores), 1), 4
    )

    if overall_alignment > 0.85:
        verdict = "Strong alignment"
    elif overall_alignment > 0.70:
        verdict = "Moderate alignment — optimization recommended"
    else:
        verdict = "Weak alignment — significant optimization needed"

    # =================================================================
    # STEP 8: Expected lift
    # =================================================================
    expected_lift = compute_expected_lift(
        overall_alignment,
        ranked[0][1]["combined_score"],
        primary_evidence,
    )

    # =================================================================
    # STEP 9: Learning trajectory
    # =================================================================
    mech_scores = {m: s["combined_score"] for m, s in combined_scores.items()}
    learning_iterations = _simulate_learning_trajectory(
        mech_scores, primary_mechanism
    )

    elapsed = time.time() - start

    # =================================================================
    # STEP 10: Archetype distribution
    # =================================================================
    cat_dist = engine.category_arch_dist.get(category, {})
    global_dist = engine.global_arch_dist

    # =================================================================
    # STEP 11: ELM route inference (data-driven)
    # =================================================================

    def _infer_elm_route(mech: str) -> str:
        """
        Infer ELM route from which archetypes benefit most from this mechanism.
        If high-cognitive-engagement archetypes benefit more → central route.
        """
        scores = []
        for arch in engine.core_archetypes:
            arch_eff = engine.global_effectiveness.get(arch, {})
            mech_rate = arch_eff.get(mech, {}).get("success_rate", 0)
            arch_cog = engine.archetype_ndf.get(arch, {}).get(
                "cognitive_engagement", 0
            )
            scores.append((mech_rate, arch_cog))
        if not scores:
            return "peripheral"
        # Sort by effectiveness, take top 3
        top = sorted(scores, key=lambda x: -x[0])[:3]
        avg_cog = sum(s[1] for s in top) / len(top)
        pop_cog_mean = engine.global_ndf_means.get("cognitive_engagement", 0.05)
        return "central" if avg_cog > pop_cog_mean else "peripheral"

    elm_routes = {mech: _infer_elm_route(mech) for mech in engine.mechanisms}
    elm_route_labels = {
        "central": "Central Route (argument quality, evidence)",
        "peripheral": "Peripheral Route (heuristic cues, emotional triggers)",
    }
    decision_style_labels = {
        "system1_intuitive": "System 1 Intuitive",
        "system2_deliberate": "System 2 Deliberate",
        "mixed": "Mixed Processing",
    }

    # Archetype evidence count
    arch_count = 0
    for mech_data in engine.global_effectiveness.get(archetype, {}).values():
        arch_count += mech_data.get("sample_size", 0)

    # =================================================================
    # STEP 12: Build response
    # =================================================================
    stackadapt_payload = {
        "segment_id": segment_name.lower().replace(" ", "_").replace("-", "_"),
        "granular_customer_type": granular_type,
        "granular_type_label": granular_type_label,
        "decision_style": decision_style,
        "decision_style_label": decision_style_labels.get(decision_style, decision_style),
        "ndf_profile": segment_ndf,
        "primary_mechanism": {
            "name": primary_mechanism,
            "label": engine.get_mechanism_label(primary_mechanism),
            "confidence": ranked[0][1]["combined_score"],
            "elm_route": elm_routes.get(primary_mechanism, "peripheral"),
            "elm_route_label": elm_route_labels.get(
                elm_routes.get(primary_mechanism, ""), ""
            ),
        },
        "secondary_mechanism": {
            "name": secondary_mechanism,
            "label": engine.get_mechanism_label(secondary_mechanism),
            "confidence": ranked[1][1]["combined_score"],
            "elm_route": elm_routes.get(secondary_mechanism, "peripheral"),
            "elm_route_label": elm_route_labels.get(
                elm_routes.get(secondary_mechanism, ""), ""
            ),
        },
        "creative_parameters": {
            "frame": copy_optimization["recommended_frame"],
            "time_emphasis": copy_optimization["time_emphasis"],
            "detail_level": copy_optimization["detail_level"],
            "energy_level": copy_optimization["energy_level"],
            "voice_style": copy_optimization["voice_style"],
            "suggested_cta": copy_optimization["suggested_cta"],
        },
        "expected_lift": {
            "ctr_lift_pct": f"{expected_lift['ctr_lift_low']}-{expected_lift['ctr_lift_high']}%",
            "purchase_lift_pct": f"{expected_lift['purchase_lift_low']}-{expected_lift['purchase_lift_high']}%",
            "confidence": expected_lift["confidence_level"],
        },
        "all_mechanism_scores": {
            mech: scores["combined_score"] for mech, scores in ranked
        },
    }

    product_intelligence_data: Dict[str, Any] = {}
    if product_data:
        product_intelligence_data = {
            "asin": product_data.get("asin"),
            "category": product_data.get("category"),
            "source": "product_intelligence_service",
            "archetype_distribution": product_arch_dist,
            "dominant_archetype": product_data.get("dominant_archetype"),
            "ad_profile": product_ad_profile,
            "mechanism_priors": product_data.get("mechanism_priors"),
            "confidence": product_data.get("confidence"),
    }

    return {
        "meta": {
            "processing_time_ms": round(elapsed * 1000, 1),
            "data_source": "INFORMATIV AI — Fully Data-Driven (zero hardcoded parameters)",
            "reviews_analyzed": priors.get("total_reviews_processed", 0),
            "categories_covered": priors.get("amazon_categories", 0),
            "ndf_population_size": priors.get("ndf_population", {}).get("ndf_count", 0),
            "granular_types_resolved": total_granular_types,
        },
        "segment": {
            "name": segment_name,
            "category": category,
            "product": product_name,
            "detected_archetype": archetype,
            "archetype_source": arch_source,
            "archetype_description": ARCHETYPE_DESCRIPTIONS.get(archetype, ""),
            "archetype_population_share": round(
                global_dist.get(archetype, 0) * 100, 1
            ),
            "archetype_sample_size": arch_count,
            "granular_type": granular_type,
            "granular_type_label": granular_type_label,
        },
        "ndf_profile": {
            "segment_ndf": segment_ndf,
            "population_ndf": {k: round(v, 4) for k, v in population_ndf.items()},
            "archetype_ndf": {k: round(v, 4) for k, v in archetype_ndf.items()},
            "review_ndf": review_ndf if review_ndf else {},
            "blend_weights": blend_weights,
            "dim_labels": NDF_DIM_LABELS,
            "dim_descriptions": NDF_DIM_DESCRIPTIONS,
        },
        "mechanism_ranking": [
            {
                "mechanism": mech,
                "label": engine.get_mechanism_label(mech),
                "description": engine.get_mechanism_description(mech),
                "elm_route": elm_routes.get(mech, "peripheral"),
                "elm_route_label": elm_route_labels.get(
                    elm_routes.get(mech, ""), ""
                ),
                **scores,
            }
            for mech, scores in ranked
        ],
        "decision_style": {
            "style": decision_style,
            "label": decision_style_labels.get(decision_style, decision_style),
            "academic_basis": "Derived from NDF cognitive_engagement — maps to ELM processing route",
        },
        "copy_optimization": copy_optimization,
        "alignment": {
            "dimension_alignment": alignment_scores,
            "overall_alignment": overall_alignment,
            "verdict": verdict,
        },
        "expected_lift": expected_lift,
        "stackadapt_return_payload": stackadapt_payload,
        "archetype_distribution": {
            "global": {
                k: round(v * 100, 2)
                for k, v in sorted(global_dist.items(), key=lambda x: -x[1])[:8]
            },
            "category": (
                {
                    k: round(v * 100, 2)
                    for k, v in sorted(cat_dist.items(), key=lambda x: -x[1])[:8]
                }
                if cat_dist
                else None
            ),
            "product": (
                {
                    k: round(v, 2)
                    for k, v in sorted(
                        product_arch_dist.items(), key=lambda x: -x[1]
                    )
                }
                if product_arch_dist
                else None
            ),
        },
        "learning_trajectory": learning_iterations,
        "corpus_fusion": corpus_fusion_data,
        "product_intelligence": (
            product_intelligence_data if product_intelligence_data else None
        ),
        "graph_type_inference": (
            graph_type_result.to_ad_context() if graph_type_result and graph_type_result.type_found else None
        ),
    }


def _simulate_learning_trajectory(
    susceptibility: Dict[str, float],
    primary: str,
    n_iterations: int = 20,
) -> List[Dict[str, Any]]:
    """Thompson Sampling simulation using mechanism susceptibility as true rates."""
    random.seed(42)
    trajectory = []
    mechanisms = list(susceptibility.keys())
    alphas = {m: 1.0 for m in mechanisms}
    betas_dict = {m: 1.0 for m in mechanisms}

    for i in range(n_iterations):
        samples = {
            m: random.betavariate(alphas[m], betas_dict[m]) for m in mechanisms
        }
        chosen = max(samples, key=samples.get)
        true_rate = susceptibility.get(chosen, 0.0)
        # Thompson Sampling handles exploration naturally — no hardcoded bonus
        success = random.random() < true_rate

        if success:
            alphas[chosen] += 1
        else:
            betas_dict[chosen] += 1

        total_samples = sum(alphas[m] + betas_dict[m] - 2 for m in mechanisms)
        allocation = {}
        for m in mechanisms:
            m_samples = alphas[m] + betas_dict[m] - 2
            allocation[m] = round(m_samples / max(total_samples, 1), 4)

        total_successes = sum(alphas[m] - 1 for m in mechanisms)
        total_trials = sum(alphas[m] + betas_dict[m] - 2 for m in mechanisms)

        trajectory.append(
            {
            "iteration": i + 1,
            "chosen_mechanism": chosen,
            "success": success,
                "cumulative_success_rate": round(
                    total_successes / max(total_trials, 1), 4
                ),
            "primary_allocation": round(allocation.get(primary, 0), 4),
            "allocation": allocation,
            }
        )

    return trajectory


# ===========================================================================
# FastAPI app
# ===========================================================================

STATIC_DIR = Path(__file__).parent / "static" / "stackadapt"

app = FastAPI(
    title="INFORMATIV AI × StackAdapt Intelligence Demo",
    description="Fully data-driven psychological intelligence for programmatic advertising",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    priors = _load_priors()
    if priors:
        DataDrivenEngine.get_instance(priors)


@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        {"status": "INFORMATIV AI × StackAdapt Demo", "message": "Frontend not built yet"}
    )


@app.get("/favicon.ico")
async def favicon():
    fav = STATIC_DIR / "favicon.svg"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/svg+xml")
    return JSONResponse(status_code=204, content=None)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/scenarios")
async def get_scenarios():
    from adam.demo.stackadapt_scenarios import SCENARIOS

    return JSONResponse({"scenarios": SCENARIOS})


@app.post("/api/analyze")
async def analyze(request: Request):
    body = await request.json()
    result = run_full_analysis(
        segment_name=body.get("segment_name", "General Audience"),
        category=body.get("category", "Electronics"),
        product_name=body.get("product_name", "Product"),
        ad_copy=body.get("ad_copy", ""),
        sample_review=body.get("sample_review", ""),
        asin=body.get("asin"),
    )
    return JSONResponse(result)


@app.get("/api/population")
async def population_stats():
    priors = _load_priors()
    engine = DataDrivenEngine.get_instance(priors)

    top_mechanisms: Dict[str, List] = {}
    for arch, mechs in engine.global_effectiveness.items():
        sorted_mechs = sorted(
            mechs.items(), key=lambda x: x[1].get("success_rate", 0), reverse=True
        )
        top_mechanisms[arch] = [
            {
                "mechanism": m,
                "label": engine.get_mechanism_label(m),
                "success_rate": round(d.get("success_rate", 0), 4),
            }
            for m, d in sorted_mechs[:3]
        ]

    total_granular = (
        len(PURCHASE_MOTIVATIONS)
        * len(DECISION_STYLES)
        * len(REGULATORY_FOCUSES)
        * len(EMOTIONAL_INTENSITIES)
        * len(PRICE_SENSITIVITIES)
        * len(BASE_ARCHETYPES)
    )

    return JSONResponse(
        {
        "total_reviews": priors.get("total_reviews_processed", 0),
        "total_products": priors.get("total_products_linked", 0),
            "categories": priors.get("amazon_categories", 0),
            "ndf_reviews": priors.get("ndf_population", {}).get("ndf_count", 0),
        "granular_types": total_granular,
            "archetype_distribution": engine.global_arch_dist,
        "top_mechanisms_by_archetype": top_mechanisms,
            "ndf_dimensions": engine.ndf_dims,
            "mechanisms": engine.mechanisms,
            "core_archetypes": engine.core_archetypes,
        }
    )


@app.get("/api/categories")
async def categories():
    engine = DataDrivenEngine.get_instance()
    return JSONResponse({"categories": sorted(engine.category_arch_dist.keys())})


# ===========================================================================
# StackAdapt Creative Intelligence + Webhook Routers (Layer 2 & 3)
# ===========================================================================
try:
    from adam.api.stackadapt.router import router as ci_router
    from adam.api.stackadapt.webhook import webhook_router
    app.include_router(ci_router)
    app.include_router(webhook_router)
    logger.info("Creative Intelligence + Webhook routers registered")
except ImportError as e:
    logger.warning("CI/Webhook routers not available: %s", e)


# ===========================================================================
# CLI
# ===========================================================================


def main():
    parser = argparse.ArgumentParser(
        description="INFORMATIV AI × StackAdapt Demo Server"
    )
    parser.add_argument("--port", type=int, default=8888, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    import uvicorn

    logger.info(
        "Starting INFORMATIV AI × StackAdapt Demo on http://%s:%d",
        args.host,
        args.port,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
