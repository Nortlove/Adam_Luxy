# =============================================================================
# Copy Effectiveness Learner — Thompson Sampling Over Copy Parameters
# Location: adam/output/copy_generation/copy_learner.py
# =============================================================================

"""
Learns which copy parameters (tone, framing, evidence_type, cta_style)
work for which (archetype, barrier, page_cluster) combinations.

This is NOT A/B testing. This is inferential learning:
- "Loss framing + data evidence works on analytical pages for trust_deficit"
- "Warm tone + testimonial works on emotional pages for identity_misalignment"
- "Direct CTA + urgency works on transactional pages for intention_action_gap"

The learner uses Thompson Sampling with Beta posteriors per parameter
value per context cell. This means exploration is naturally balanced
with exploitation — uncertain parameter values get tried more often.

Architecture:
- Pre-compute: Generate variants offline via Claude (full psychological prompt)
- Cache: Store variants in Redis keyed by (archetype, barrier, mechanism, page_cluster)
- Select: At impression time, Thompson-sample the best variant (<1ms)
- Adapt: Apply edge-dimension parameter adjustments (<1ms)
- Learn: On outcome, update posteriors for the selected variant's parameters
- Evolve: Weekly, regenerate bottom 20% using learned parameters + Claude
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# Copy parameter space — the dimensions we learn over
COPY_PARAMETERS = {
    "tone": ["warm", "authoritative", "urgent", "balanced"],
    "framing": ["gain", "loss", "mixed"],
    "evidence_type": ["data", "testimonial", "comparison", "narrative"],
    "cta_style": ["soft", "direct", "urgent", "social"],
}


@dataclass
class CopyPosterior:
    """Beta(alpha, beta) posterior for a single copy parameter value."""
    alpha: float = 2.0
    beta: float = 2.0
    sample_count: int = 0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def sample(self) -> float:
        return float(np.random.beta(self.alpha, self.beta))

    def update(self, success: bool) -> None:
        if success:
            self.alpha += 1.0
        else:
            self.beta += 1.0
        self.sample_count += 1


@dataclass
class CopyVariantRecord:
    """A pre-generated copy variant with its parameter configuration."""
    variant_id: str
    headline: str
    body: str
    cta: str
    tone: str
    framing: str
    evidence_type: str
    cta_style: str
    generated_at: float = field(default_factory=time.time)
    served_count: int = 0
    conversion_count: int = 0

    @property
    def conversion_rate(self) -> float:
        if self.served_count == 0:
            return 0.0
        return self.conversion_count / self.served_count


class CopyEffectivenessLearner:
    """Learns which copy parameters work for which context cells.

    Context cell: (archetype, barrier, page_cluster)
    Learns over: tone, framing, evidence_type, cta_style
    """

    def __init__(self):
        # Posteriors: context_key → param_name → param_value → CopyPosterior
        self._posteriors: Dict[str, Dict[str, Dict[str, CopyPosterior]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        # Variant cache: context_key → list of CopyVariantRecord
        self._variants: Dict[str, List[CopyVariantRecord]] = defaultdict(list)
        # Serving log: decision_id → variant_id (for outcome attribution)
        self._served: Dict[str, str] = {}
        self._total_outcomes = 0

    def _context_key(self, archetype: str, barrier: str, page_cluster: str = "") -> str:
        return f"{archetype}:{barrier}:{page_cluster or 'any'}"

    def _ensure_posteriors(self, context_key: str) -> None:
        """Initialize posteriors for all parameter values in a context cell."""
        cell = self._posteriors[context_key]
        for param, values in COPY_PARAMETERS.items():
            if param not in cell:
                cell[param] = {}
            for val in values:
                if val not in cell[param]:
                    cell[param][val] = CopyPosterior()

    # =========================================================================
    # RECOMMENDATION (real-time, <1ms)
    # =========================================================================

    def recommend_params(
        self,
        archetype: str,
        barrier: str,
        page_cluster: str = "",
    ) -> Dict[str, str]:
        """Thompson-sample copy parameters for a context cell.

        Returns: {tone: "warm", framing: "loss", evidence_type: "data", cta_style: "soft"}
        Called at impression time — must be fast (<1ms).
        """
        key = self._context_key(archetype, barrier, page_cluster)
        self._ensure_posteriors(key)

        recommended = {}
        cell = self._posteriors[key]
        for param, values_dict in cell.items():
            # Thompson sample: draw from each value's posterior, pick highest
            best_val = None
            best_sample = -1.0
            for val, posterior in values_dict.items():
                s = posterior.sample()
                if s > best_sample:
                    best_sample = s
                    best_val = val
            recommended[param] = best_val or COPY_PARAMETERS[param][0]

        return recommended

    # =========================================================================
    # VARIANT CACHE (real-time serving)
    # =========================================================================

    def cache_variant(
        self,
        archetype: str,
        barrier: str,
        variant: CopyVariantRecord,
        page_cluster: str = "",
    ) -> None:
        """Store a pre-generated variant in the cache."""
        key = self._context_key(archetype, barrier, page_cluster)
        self._variants[key].append(variant)

    def select_variant(
        self,
        archetype: str,
        barrier: str,
        page_cluster: str = "",
    ) -> Optional[CopyVariantRecord]:
        """Select the best variant for a context cell using Thompson Sampling.

        Picks the variant whose parameter combination has the highest
        sampled posterior value. Returns None if no variants cached.
        """
        key = self._context_key(archetype, barrier, page_cluster)
        variants = self._variants.get(key, [])
        if not variants:
            return None

        self._ensure_posteriors(key)
        cell = self._posteriors[key]

        best_variant = None
        best_score = -1.0
        for v in variants:
            # Score = product of Thompson samples for each parameter
            score = 1.0
            for param in ["tone", "framing", "evidence_type", "cta_style"]:
                val = getattr(v, param, None)
                if val and val in cell.get(param, {}):
                    score *= cell[param][val].sample()
            if score > best_score:
                best_score = score
                best_variant = v

        return best_variant

    def record_serving(self, decision_id: str, variant_id: str) -> None:
        """Record that a variant was served for a decision (for outcome attribution)."""
        self._served[decision_id] = variant_id
        # Cap serving log
        if len(self._served) > 50_000:
            # Drop oldest half
            keys = list(self._served.keys())
            for k in keys[:25_000]:
                del self._served[k]

    # =========================================================================
    # LEARNING (from outcomes)
    # =========================================================================

    def record_outcome(
        self,
        decision_id: str,
        archetype: str,
        barrier: str,
        converted: bool,
        page_cluster: str = "",
    ) -> Dict[str, Any]:
        """Update posteriors from an observed outcome.

        Looks up the variant that was served for this decision_id,
        extracts its parameter configuration, and updates the Beta
        posteriors for each parameter value.
        """
        variant_id = self._served.get(decision_id)
        if not variant_id:
            return {"updated": False, "reason": "no serving record"}

        # Find the variant
        key = self._context_key(archetype, barrier, page_cluster)
        variant = None
        for v in self._variants.get(key, []):
            if v.variant_id == variant_id:
                variant = v
                break

        if not variant:
            # Try all cells
            for cell_variants in self._variants.values():
                for v in cell_variants:
                    if v.variant_id == variant_id:
                        variant = v
                        break

        if not variant:
            return {"updated": False, "reason": f"variant {variant_id} not found"}

        # Update variant stats
        variant.served_count += 1
        if converted:
            variant.conversion_count += 1

        # Update posteriors for each parameter
        self._ensure_posteriors(key)
        cell = self._posteriors[key]
        updated_params = []
        for param in ["tone", "framing", "evidence_type", "cta_style"]:
            val = getattr(variant, param, None)
            if val and val in cell.get(param, {}):
                cell[param][val].update(converted)
                updated_params.append(f"{param}={val}")

        self._total_outcomes += 1
        return {
            "updated": True,
            "variant_id": variant_id,
            "converted": converted,
            "params_updated": updated_params,
        }

    # =========================================================================
    # EVOLUTION (weekly, offline)
    # =========================================================================

    def get_bottom_performers(
        self, min_served: int = 10, bottom_pct: float = 0.2
    ) -> List[Tuple[str, CopyVariantRecord]]:
        """Identify bottom-performing variants for regeneration.

        Returns: [(context_key, variant)] for the lowest-converting variants
        that have been served at least min_served times.
        """
        candidates = []
        for key, variants in self._variants.items():
            for v in variants:
                if v.served_count >= min_served:
                    candidates.append((key, v))

        candidates.sort(key=lambda x: x[1].conversion_rate)
        n_bottom = max(1, int(len(candidates) * bottom_pct))
        return candidates[:n_bottom]

    def get_learned_params_summary(self) -> Dict[str, Dict[str, float]]:
        """Summary of learned parameter effectiveness across all cells."""
        param_means: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for key, cell in self._posteriors.items():
            for param, values in cell.items():
                for val, posterior in values.items():
                    if posterior.sample_count > 0:
                        param_means[param][val].append(posterior.mean)

        return {
            param: {
                val: float(np.mean(means)) if means else 0.5
                for val, means in values.items()
            }
            for param, values in param_means.items()
        }

    @property
    def stats(self) -> Dict[str, Any]:
        total_variants = sum(len(v) for v in self._variants.values())
        total_posteriors = sum(
            sum(len(vals) for vals in cell.values())
            for cell in self._posteriors.values()
        )
        return {
            "context_cells": len(self._posteriors),
            "cached_variants": total_variants,
            "posteriors": total_posteriors,
            "total_outcomes": self._total_outcomes,
            "serving_log_size": len(self._served),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_learner: Optional[CopyEffectivenessLearner] = None


def get_copy_learner() -> CopyEffectivenessLearner:
    global _learner
    if _learner is None:
        _learner = CopyEffectivenessLearner()
    return _learner
