"""
Platform Calibration Layer (Layer 3)
======================================

Stores platform-specific adjustment factors on corpus priors.

The corpus priors come from Amazon verified purchases (text-based).
When live campaigns run on StackAdapt (programmatic display/native/audio),
Audioboom (podcast), or iHeart (streaming audio/podcast), the observed
effectiveness may differ from the corpus prediction.

This layer captures those differences as calibration factors:

    effective_score = corpus_prior × platform_factor × recency_weight

Over time, platform calibrations stabilize and become their own reliable
priors for that specific platform.

Updated by:
    - The Gradient Bridge when campaign outcomes arrive
    - The BidirectionalLearningLoop (Layer 4) for modality/channel adjustments

Serves calibrated priors to:
    - PriorExtractionService (Layer 1) — corpus priors adjusted for platform
    - CampaignSimulationEngine — realistic projections per platform
    - CopyGenerationService — platform-appropriate creative constraints
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adam.fusion.models import (
    ConvergenceState,
    PlatformCalibration,
    PlatformCalibrationSet,
    PlatformID,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DEFAULT CALIBRATION FACTORS (educated starting points)
# =============================================================================

# These are initial platform calibration factors based on modality
# characteristics. They will be updated as campaign data arrives.
DEFAULT_PLATFORM_FACTORS: Dict[str, Dict[str, float]] = {
    PlatformID.STACKADAPT.value: {
        # Programmatic display/native — shorter attention, less immersive
        "social_proof": 1.05,    # Social proof works well in display
        "scarcity": 1.10,        # Urgency effective in fast-scroll
        "authority": 0.85,       # Less room for authority cues in display
        "commitment": 0.80,      # Hard to build commitment in banner
        "reciprocity": 0.75,     # Limited reciprocity in programmatic
        "liking": 0.90,          # Visual appeal helps
        "unity": 0.85,           # Less community feel in programmatic
        "fomo": 1.15,            # FOMO very effective in display
        "identity_construction": 0.90,
        "storytelling": 0.70,    # Hard to tell stories in display
        "fear_appeal": 0.95,
        "humor": 0.80,           # Hard to be funny in banners
        "mimetic_desire": 1.00,
        "attention_dynamics": 1.20,  # Novelty/salience critical in display
        "embodied_cognition": 0.70,  # No physical experience
    },
    PlatformID.AUDIOBOOM.value: {
        # Podcast — intimate, high-attention, host-mediated
        "social_proof": 1.10,    # Host-mediated social proof is strong
        "scarcity": 0.90,        # Less urgency in podcast listening
        "authority": 1.20,       # Host authority transfers to brand
        "commitment": 1.05,      # Loyal audience = commitment receptive
        "reciprocity": 1.15,     # "This episode brought to you by" = reciprocity
        "liking": 1.25,          # Host liking transfers strongly
        "unity": 1.20,           # Podcast community = strong unity
        "fomo": 0.85,            # Less FOMO in asynchronous listening
        "identity_construction": 1.10,
        "storytelling": 1.30,    # Podcast IS storytelling medium
        "fear_appeal": 0.90,     # Less effective in relaxed listening
        "humor": 1.15,           # Humor works well in audio
        "mimetic_desire": 1.05,
        "attention_dynamics": 0.85,  # Less novelty-dependent
        "embodied_cognition": 0.90,  # Audio has some embodiment
    },
    PlatformID.IHEART.value: {
        # Streaming audio — shorter form, music context, repetition
        "social_proof": 1.00,
        "scarcity": 1.05,
        "authority": 1.05,
        "commitment": 0.85,
        "reciprocity": 1.00,
        "liking": 1.10,          # Music association = liking
        "unity": 1.05,           # Radio community
        "fomo": 1.00,
        "identity_construction": 1.00,
        "storytelling": 1.10,    # Audio storytelling effective
        "fear_appeal": 1.00,
        "humor": 1.10,
        "mimetic_desire": 1.00,
        "attention_dynamics": 1.05,
        "embodied_cognition": 0.85,
    },
}

# Recency decay half-life in days
RECENCY_HALF_LIFE_DAYS = 30.0


class PlatformCalibrationLayer:
    """
    Manages platform-specific calibration factors on corpus priors.

    Maintains calibration state per (platform, mechanism, category).
    Each calibration tracks:
    - platform_factor: how this platform differs from corpus
    - recency_weight: temporal decay on stale calibrations
    - convergence state: has the calibration stabilized?
    """

    def __init__(self):
        self._calibrations: Dict[str, PlatformCalibrationSet] = {}
        self._convergence: Dict[str, ConvergenceState] = {}
        self._last_save_time: float = 0
        self._persistence_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "learning", "platform_calibrations.json",
        )
        self._load_from_disk()

    # =========================================================================
    # CALIBRATED PRIOR ACCESS
    # =========================================================================

    def get_calibrated_score(
        self,
        platform: str,
        mechanism: str,
        category: str,
        corpus_prior: float,
    ) -> Tuple[float, float, str]:
        """
        Get calibrated effectiveness score for a platform.

        Returns: (calibrated_score, confidence, source_description)
        """
        try:
            platform_id = PlatformID(platform.lower())
        except ValueError:
            return corpus_prior, 0.3, "uncalibrated"

        key = f"{mechanism}:{category}"
        cal_set = self._calibrations.get(platform_id.value)

        if cal_set and key in cal_set.calibrations:
            cal = cal_set.calibrations[key]
            # Apply recency decay
            recency = self._compute_recency_weight(cal_set.last_updated)
            cal.recency_weight = recency
            cal.corpus_prior_value = corpus_prior
            score = min(1.0, corpus_prior * cal.platform_factor * recency)
            confidence = min(
                0.95,
                0.3 + math.log(1 + cal.campaign_observations) * 0.1
            )
            source = f"calibrated({cal.campaign_observations} obs, factor={cal.platform_factor:.2f})"
            return score, confidence, source

        # Fall back to default platform factors
        defaults = DEFAULT_PLATFORM_FACTORS.get(platform_id.value, {})
        factor = defaults.get(mechanism, 1.0)
        score = min(1.0, corpus_prior * factor)
        return score, 0.2, f"default_platform_factor({factor:.2f})"

    def get_all_calibrations(
        self,
        platform: str,
        category: str,
    ) -> Dict[str, Tuple[float, float]]:
        """
        Get all mechanism calibrations for a platform × category.

        Returns: {mechanism: (platform_factor, confidence)}
        """
        try:
            platform_id = PlatformID(platform.lower())
        except ValueError:
            return {}

        result = {}
        cal_set = self._calibrations.get(platform_id.value)

        if cal_set:
            for key, cal in cal_set.calibrations.items():
                mech, cat = key.split(":", 1) if ":" in key else (key, "all")
                if cat == category or cat == "all":
                    confidence = min(
                        0.95,
                        0.3 + math.log(1 + cal.campaign_observations) * 0.1
                    )
                    result[mech] = (cal.platform_factor, confidence)

        # Fill in defaults for mechanisms without calibrations
        defaults = DEFAULT_PLATFORM_FACTORS.get(platform_id.value, {})
        for mech, factor in defaults.items():
            if mech not in result:
                result[mech] = (factor, 0.15)

        return result

    # =========================================================================
    # CALIBRATION UPDATES (from campaign outcomes)
    # =========================================================================

    def update_calibration(
        self,
        platform: str,
        mechanism: str,
        category: str,
        corpus_prior: float,
        observed_effectiveness: float,
        observation_count: int = 1,
    ) -> PlatformCalibration:
        """
        Update calibration with new campaign observation.

        Uses exponential moving average to smooth updates:
        new_factor = α × (observed / corpus) + (1-α) × old_factor

        where α = min(0.3, observation_count / 100)

        Args:
            platform: Platform identifier
            mechanism: Mechanism name
            category: Product category
            corpus_prior: The corpus-predicted effectiveness
            observed_effectiveness: What was actually observed
            observation_count: Number of observations in this update

        Returns:
            Updated PlatformCalibration
        """
        try:
            platform_id = PlatformID(platform.lower())
        except ValueError:
            logger.warning(f"Unknown platform: {platform}")
            return PlatformCalibration(
                platform=PlatformID.STACKADAPT,
                mechanism=mechanism,
                category=category,
            )

        key = f"{mechanism}:{category}"

        # Get or create calibration set
        if platform_id.value not in self._calibrations:
            self._calibrations[platform_id.value] = PlatformCalibrationSet(
                platform=platform_id
            )
        cal_set = self._calibrations[platform_id.value]

        # Get or create calibration entry
        if key not in cal_set.calibrations:
            # Initialize from defaults
            defaults = DEFAULT_PLATFORM_FACTORS.get(platform_id.value, {})
            initial_factor = defaults.get(mechanism, 1.0)
            cal_set.calibrations[key] = PlatformCalibration(
                platform=platform_id,
                mechanism=mechanism,
                category=category,
                platform_factor=initial_factor,
                corpus_prior_value=corpus_prior,
            )

        cal = cal_set.calibrations[key]

        # Compute new observed factor
        if corpus_prior > 0.01:
            observed_factor = observed_effectiveness / corpus_prior
        else:
            observed_factor = 1.0

        # Exponential moving average
        alpha = min(0.3, observation_count / 100.0)
        new_factor = alpha * observed_factor + (1 - alpha) * cal.platform_factor

        # Update
        cal.platform_factor = max(0.1, min(3.0, new_factor))  # Clamp
        cal.campaign_observations += observation_count
        cal.corpus_prior_value = corpus_prior
        cal.observed_effectiveness = observed_effectiveness
        cal.recency_weight = 1.0  # Just updated

        # Update calibration set metadata
        cal_set.last_updated = datetime.now(timezone.utc)
        cal_set.total_observations += observation_count

        # Track convergence
        self._track_convergence(platform_id, mechanism, category, cal)

        # Auto-save periodically
        if time.time() - self._last_save_time > 60:
            self._save_to_disk()

        logger.debug(
            f"Calibration updated: {platform}/{mechanism}/{category} "
            f"factor={cal.platform_factor:.3f} "
            f"obs={cal.campaign_observations}"
        )

        return cal

    # =========================================================================
    # CONVERGENCE TRACKING
    # =========================================================================

    def _track_convergence(
        self,
        platform: PlatformID,
        mechanism: str,
        category: str,
        cal: PlatformCalibration,
    ) -> None:
        """Track whether a calibration has converged."""
        conv_key = f"{platform.value}:{mechanism}:{category}"

        if conv_key not in self._convergence:
            self._convergence[conv_key] = ConvergenceState(
                mechanism=mechanism,
                category=category,
                platform=platform,
                prior_value=cal.corpus_prior_value,
                posterior_value=cal.calibrated_score,
            )

        state = self._convergence[conv_key]
        old_posterior = state.posterior_value
        new_posterior = cal.calibrated_score
        delta = abs(new_posterior - old_posterior)

        state.delta_history.append(delta)
        state.delta_history = state.delta_history[-20:]  # Keep last 20
        state.posterior_value = new_posterior
        state.iterations += 1

        was_converged = state.is_converged
        state.check_convergence()

        if state.is_converged and not was_converged:
            cal.is_stable = True
            cal.stability_iterations = state.iterations
            logger.info(
                f"Calibration CONVERGED: {platform.value}/{mechanism}/{category} "
                f"factor={cal.platform_factor:.3f} after {state.iterations} iterations"
            )

    def get_convergence_status(self) -> Dict[str, Any]:
        """Get convergence status for all calibrations."""
        total = len(self._convergence)
        converged = sum(1 for s in self._convergence.values() if s.is_converged)
        return {
            "total_calibrations": total,
            "converged": converged,
            "convergence_rate": converged / max(1, total),
            "details": {
                key: {
                    "converged": state.is_converged,
                    "iterations": state.iterations,
                    "last_delta": state.delta_history[-1] if state.delta_history else None,
                }
                for key, state in self._convergence.items()
            },
        }

    # =========================================================================
    # RECENCY WEIGHTING
    # =========================================================================

    def _compute_recency_weight(self, last_updated: datetime) -> float:
        """Compute recency weight based on time since last update."""
        now = datetime.now(timezone.utc)
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        age_days = (now - last_updated).total_seconds() / 86400.0
        return math.exp(-0.693 * age_days / RECENCY_HALF_LIFE_DAYS)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def _save_to_disk(self) -> None:
        """Save calibrations to JSON."""
        try:
            data = {}
            for platform, cal_set in self._calibrations.items():
                data[platform] = {
                    "last_updated": cal_set.last_updated.isoformat(),
                    "total_observations": cal_set.total_observations,
                    "calibrations": {},
                }
                for key, cal in cal_set.calibrations.items():
                    data[platform]["calibrations"][key] = {
                        "mechanism": cal.mechanism,
                        "category": cal.category,
                        "platform_factor": cal.platform_factor,
                        "campaign_observations": cal.campaign_observations,
                        "corpus_prior_value": cal.corpus_prior_value,
                        "observed_effectiveness": cal.observed_effectiveness,
                        "is_stable": cal.is_stable,
                        "stability_iterations": cal.stability_iterations,
                    }

            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)

            self._last_save_time = time.time()
            logger.debug(f"Saved platform calibrations to {self._persistence_path}")

        except Exception as e:
            logger.warning(f"Failed to save calibrations: {e}")

    def _load_from_disk(self) -> None:
        """Load calibrations from JSON if exists."""
        if not os.path.exists(self._persistence_path):
            return

        try:
            with open(self._persistence_path) as f:
                data = json.load(f)

            for platform_str, platform_data in data.items():
                try:
                    platform_id = PlatformID(platform_str)
                except ValueError:
                    continue

                cal_set = PlatformCalibrationSet(
                    platform=platform_id,
                    total_observations=platform_data.get("total_observations", 0),
                )

                last_updated = platform_data.get("last_updated")
                if last_updated:
                    cal_set.last_updated = datetime.fromisoformat(last_updated)

                for key, cal_data in platform_data.get("calibrations", {}).items():
                    cal_set.calibrations[key] = PlatformCalibration(
                        platform=platform_id,
                        mechanism=cal_data["mechanism"],
                        category=cal_data["category"],
                        platform_factor=cal_data.get("platform_factor", 1.0),
                        campaign_observations=cal_data.get("campaign_observations", 0),
                        corpus_prior_value=cal_data.get("corpus_prior_value", 0.5),
                        observed_effectiveness=cal_data.get("observed_effectiveness", 0.5),
                        is_stable=cal_data.get("is_stable", False),
                        stability_iterations=cal_data.get("stability_iterations", 0),
                    )

                self._calibrations[platform_str] = cal_set

            total_cals = sum(
                len(cs.calibrations) for cs in self._calibrations.values()
            )
            logger.info(f"Loaded {total_cals} platform calibrations from disk")

        except Exception as e:
            logger.warning(f"Failed to load calibrations: {e}")


# =============================================================================
# SINGLETON
# =============================================================================

_layer: Optional[PlatformCalibrationLayer] = None


def get_platform_calibration_layer() -> PlatformCalibrationLayer:
    """Get singleton PlatformCalibrationLayer."""
    global _layer
    if _layer is None:
        _layer = PlatformCalibrationLayer()
    return _layer
