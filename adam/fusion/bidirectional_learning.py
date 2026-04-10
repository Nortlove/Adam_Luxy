"""
Bidirectional Learning Loop (Layer 4)
=======================================

The fusion is not one-directional. Campaign outcomes enrich the corpus
understanding, not just the other way around.

Corpus → Campaign (Prior injection):
    Corpus provides starting archetypes, mechanism effectiveness estimates,
    creative patterns. Every new advertiser onboards with corpus-calibrated
    intelligence instead of starting cold.

Campaign → Corpus (Posterior feedback):
    When live campaigns show that a mechanism works differently on audio
    (iHeart) than the corpus predicted from text-based Amazon reviews, this
    is a MODALITY ADJUSTMENT SIGNAL. When a psychological profile converts
    differently on programmatic display (StackAdapt) than predicted, this
    is a CHANNEL ADJUSTMENT SIGNAL.

These adjustments are stored as platform-specific calibration factors on
corpus priors — not overwriting the priors, but adding conditional posteriors.

Source tagging:
    - source: "corpus" — static priors from billion-review analysis
    - source: "campaign" — live learning from partner platform outcomes
    - source: "fused" — converged estimates with prior/likelihood weights

The LangGraph orchestration checks for fused knowledge first (highest
confidence), falls back to corpus priors when no campaign data exists
(cold start), and uses campaign-only data for novel categories.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adam.fusion.models import (
    ChannelAdjustment,
    ConvergenceState,
    LearningSignalSource,
    ModalityAdjustment,
    PlatformID,
    PriorSourceType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MODALITY CHARACTERISTICS
# =============================================================================

MODALITY_MAP: Dict[str, str] = {
    PlatformID.STACKADAPT.value: "display",    # Programmatic display/native
    PlatformID.AUDIOBOOM.value: "audio",        # Podcast audio
    PlatformID.IHEART.value: "audio",           # Streaming audio
    PlatformID.AMAZON.value: "text",            # Text (corpus origin)
}

CHANNEL_MAP: Dict[str, str] = {
    PlatformID.STACKADAPT.value: "programmatic_display",
    PlatformID.AUDIOBOOM.value: "podcast",
    PlatformID.IHEART.value: "streaming_audio",
    PlatformID.AMAZON.value: "ecommerce",
}


class BidirectionalLearningLoop:
    """
    Manages the bidirectional flow between corpus and live campaigns.

    Responsibilities:
    1. Process campaign outcomes into calibration updates
    2. Detect and record modality adjustment signals
    3. Detect and record channel adjustment signals
    4. Track convergence of fused priors
    5. Tag sources on updated graph edges (corpus/campaign/fused)
    6. Detect corpus-campaign conflicts as learning signals
    """

    def __init__(self):
        self._calibration_layer = None
        self._prior_service = None
        self._graph_service = None

        # In-memory tracking
        self._modality_adjustments: Dict[str, ModalityAdjustment] = {}
        self._channel_adjustments: Dict[str, ChannelAdjustment] = {}
        self._conflict_log: List[Dict[str, Any]] = []
        self._outcomes_processed: int = 0

    def _get_calibration_layer(self):
        if self._calibration_layer is None:
            from adam.fusion.platform_calibration import get_platform_calibration_layer
            self._calibration_layer = get_platform_calibration_layer()
        return self._calibration_layer

    def _get_prior_service(self):
        if self._prior_service is None:
            from adam.fusion.prior_extraction import get_prior_extraction_service
            self._prior_service = get_prior_extraction_service()
        return self._prior_service

    def _get_graph_service(self):
        if self._graph_service is None:
            from adam.services.graph_intelligence import get_graph_intelligence_service
            self._graph_service = get_graph_intelligence_service()
        return self._graph_service

    # =========================================================================
    # OUTCOME PROCESSING
    # =========================================================================

    def process_campaign_outcome(
        self,
        platform: str,
        mechanism: str,
        category: str,
        observed_effectiveness: float,
        archetype: Optional[str] = None,
        campaign_id: Optional[str] = None,
        observation_count: int = 1,
    ) -> Dict[str, Any]:
        """
        Process a campaign outcome through the full bidirectional loop.

        This is the primary entry point from the Gradient Bridge.

        Flow:
        1. Get corpus prior for this mechanism × category
        2. Update platform calibration
        3. Detect modality/channel adjustments
        4. Check for corpus-campaign conflict
        5. Update convergence tracking
        6. Tag source on graph edges

        Args:
            platform: Platform identifier (stackadapt, audioboom, iheart)
            mechanism: Mechanism name
            category: Product category
            observed_effectiveness: Measured effectiveness [0, 1]
            archetype: Customer archetype if known
            campaign_id: Campaign identifier
            observation_count: Number of observations

        Returns:
            Dict with processing results and any detected signals
        """
        self._outcomes_processed += 1
        result = {
            "platform": platform,
            "mechanism": mechanism,
            "category": category,
            "observed": observed_effectiveness,
            "signals": [],
        }

        # --- Step 1: Get corpus prior ---
        prior_svc = self._get_prior_service()
        corpus_prior = prior_svc.extract_prior(
            category=category,
            archetype=archetype,
        )

        corpus_value = 0.5  # Default if no prior
        mech_prior = corpus_prior.get_mechanism_prior(mechanism)
        if mech_prior:
            corpus_value = mech_prior.effect_size
        result["corpus_prior"] = corpus_value

        # --- Step 2: Update platform calibration ---
        cal_layer = self._get_calibration_layer()
        calibration = cal_layer.update_calibration(
            platform=platform,
            mechanism=mechanism,
            category=category,
            corpus_prior=corpus_value,
            observed_effectiveness=observed_effectiveness,
            observation_count=observation_count,
        )
        result["platform_factor"] = calibration.platform_factor
        result["calibrated_score"] = calibration.calibrated_score

        # --- Step 3: Detect modality adjustment ---
        modality_signal = self._detect_modality_adjustment(
            platform=platform,
            mechanism=mechanism,
            category=category,
            corpus_effectiveness=corpus_value,
            observed_effectiveness=observed_effectiveness,
            observation_count=observation_count,
        )
        if modality_signal:
            result["signals"].append({
                "type": "modality_adjustment",
                "modality": modality_signal.modality,
                "adjustment_factor": modality_signal.adjustment_factor,
            })

        # --- Step 4: Detect channel adjustment ---
        channel_signal = self._detect_channel_adjustment(
            platform=platform,
            mechanism=mechanism,
            category=category,
            corpus_effectiveness=corpus_value,
            observed_effectiveness=observed_effectiveness,
            observation_count=observation_count,
        )
        if channel_signal:
            result["signals"].append({
                "type": "channel_adjustment",
                "channel": channel_signal.channel,
                "adjustment_factor": channel_signal.adjustment_factor,
            })

        # --- Step 5: Check for corpus-campaign conflict ---
        conflict = self._check_for_conflict(
            corpus_value=corpus_value,
            observed_value=observed_effectiveness,
            platform=platform,
            mechanism=mechanism,
            category=category,
        )
        if conflict:
            result["signals"].append({"type": "conflict", **conflict})

        # --- Step 6: Tag source on graph edges ---
        self._tag_source_on_graph(
            platform=platform,
            mechanism=mechanism,
            category=category,
            calibration=calibration,
        )

        result["source_tag"] = self._determine_source_tag(calibration)

        return result

    # =========================================================================
    # MODALITY ADJUSTMENT DETECTION
    # =========================================================================

    def _detect_modality_adjustment(
        self,
        platform: str,
        mechanism: str,
        category: str,
        corpus_effectiveness: float,
        observed_effectiveness: float,
        observation_count: int,
    ) -> Optional[ModalityAdjustment]:
        """
        Detect if there's a modality-specific adjustment needed.

        Modality = text (corpus) vs audio (podcast) vs display (programmatic)
        """
        modality = MODALITY_MAP.get(platform, "unknown")
        if modality == "text":
            # Corpus platform — no adjustment needed
            return None

        key = f"{modality}:{mechanism}:{category}"

        if key not in self._modality_adjustments:
            self._modality_adjustments[key] = ModalityAdjustment(
                modality=modality,
                mechanism=mechanism,
                category=category,
                corpus_effectiveness=corpus_effectiveness,
                modality_effectiveness=observed_effectiveness,
            )
        else:
            adj = self._modality_adjustments[key]
            # Weighted update
            old_weight = adj.observation_count
            new_weight = observation_count
            total = old_weight + new_weight
            if total > 0:
                adj.modality_effectiveness = (
                    adj.modality_effectiveness * old_weight
                    + observed_effectiveness * new_weight
                ) / total
            adj.corpus_effectiveness = corpus_effectiveness

        adj = self._modality_adjustments[key]
        adj.observation_count += observation_count

        # Compute adjustment factor (clamped to [0.2, 5.0] to prevent extremes
        # from low-evidence corpus priors)
        if corpus_effectiveness > 0.01:
            raw_factor = adj.modality_effectiveness / corpus_effectiveness
            adj.adjustment_factor = max(0.2, min(5.0, raw_factor))
        else:
            adj.adjustment_factor = 1.0

        # Compute confidence based on observation count
        adj.confidence = min(0.95, 0.2 + math.log(1 + adj.observation_count) * 0.08)

        # Only report significant adjustments (>10% difference with enough data)
        if abs(adj.adjustment_factor - 1.0) > 0.10 and adj.observation_count >= 10:
            return adj
        return None

    # =========================================================================
    # CHANNEL ADJUSTMENT DETECTION
    # =========================================================================

    def _detect_channel_adjustment(
        self,
        platform: str,
        mechanism: str,
        category: str,
        corpus_effectiveness: float,
        observed_effectiveness: float,
        observation_count: int,
    ) -> Optional[ChannelAdjustment]:
        """
        Detect channel-specific dynamics.

        Channel = programmatic_display vs podcast vs streaming_audio vs ecommerce
        """
        channel = CHANNEL_MAP.get(platform, "unknown")
        if channel == "ecommerce":
            return None

        key = f"{channel}:{mechanism}:{category}"

        if key not in self._channel_adjustments:
            self._channel_adjustments[key] = ChannelAdjustment(
                channel=channel,
                mechanism=mechanism,
                category=category,
                corpus_effectiveness=corpus_effectiveness,
                channel_effectiveness=observed_effectiveness,
            )
        else:
            adj = self._channel_adjustments[key]
            old_weight = adj.observation_count
            new_weight = observation_count
            total = old_weight + new_weight
            if total > 0:
                adj.channel_effectiveness = (
                    adj.channel_effectiveness * old_weight
                    + observed_effectiveness * new_weight
                ) / total
            adj.corpus_effectiveness = corpus_effectiveness

        adj = self._channel_adjustments[key]
        adj.observation_count += observation_count

        # Clamp to [0.2, 5.0] to prevent extreme ratios from low-evidence priors
        if corpus_effectiveness > 0.01:
            raw_factor = adj.channel_effectiveness / corpus_effectiveness
            adj.adjustment_factor = max(0.2, min(5.0, raw_factor))
        else:
            adj.adjustment_factor = 1.0

        adj.confidence = min(0.95, 0.2 + math.log(1 + adj.observation_count) * 0.08)

        if abs(adj.adjustment_factor - 1.0) > 0.10 and adj.observation_count >= 10:
            return adj
        return None

    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================

    def _check_for_conflict(
        self,
        corpus_value: float,
        observed_value: float,
        platform: str,
        mechanism: str,
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if corpus and campaign data conflict.

        Conflict = platform-specific dynamics differ significantly from
        Amazon purchase behavior. This is itself valuable intelligence.
        """
        if corpus_value < 0.01:
            return None

        ratio = observed_value / corpus_value
        deviation = abs(ratio - 1.0)

        # Significant conflict: >30% deviation
        if deviation > 0.30:
            conflict = {
                "corpus_value": corpus_value,
                "observed_value": observed_value,
                "deviation": deviation,
                "direction": "over_performs" if ratio > 1.0 else "under_performs",
                "platform": platform,
                "mechanism": mechanism,
                "category": category,
                "interpretation": (
                    f"{mechanism} {('over' if ratio > 1 else 'under')}-performs "
                    f"on {platform} by {deviation:.0%} vs corpus prediction. "
                    f"This suggests {MODALITY_MAP.get(platform, 'unknown')}-specific "
                    f"dynamics that differ from text-based purchase behavior."
                ),
            }
            self._conflict_log.append({
                **conflict,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(
                f"Corpus-campaign CONFLICT: {mechanism}/{category} on {platform} — "
                f"corpus={corpus_value:.2f}, observed={observed_value:.2f} "
                f"({deviation:.0%} deviation)"
            )
            return conflict

        return None

    # =========================================================================
    # SOURCE TAGGING
    # =========================================================================

    def _determine_source_tag(
        self, calibration
    ) -> str:
        """Determine appropriate source tag for this data point."""
        if calibration.is_stable:
            return PriorSourceType.FUSED.value
        elif calibration.campaign_observations > 0:
            return PriorSourceType.CAMPAIGN.value
        else:
            return PriorSourceType.CORPUS.value

    def _tag_source_on_graph(
        self,
        platform: str,
        mechanism: str,
        category: str,
        calibration,
    ) -> None:
        """
        Update source tags on Neo4j graph edges.

        This allows the LangGraph orchestration to check for fused
        knowledge first (highest confidence), fall back to corpus
        priors, or use campaign-only data.
        """
        source_tag = self._determine_source_tag(calibration)

        try:
            gs = self._get_graph_service()
            # This would update the source property on relevant edges
            # For now, we track it in memory; actual graph writes happen
            # via TheoryLearner when outcomes are processed
            logger.debug(
                f"Source tag for {platform}/{mechanism}/{category}: {source_tag}"
            )
        except Exception as e:
            logger.debug(f"Graph source tagging skipped: {e}")

    # =========================================================================
    # QUERY INTERFACE
    # =========================================================================

    def get_best_source(
        self,
        mechanism: str,
        category: str,
        platform: Optional[str] = None,
    ) -> Tuple[str, float, float]:
        """
        Get the best available intelligence source for a query.

        Priority:
        1. Fused (corpus + campaign converged) — highest confidence
        2. Platform-calibrated corpus prior — if platform specified
        3. Corpus prior — if no campaign data
        4. Campaign-only — if novel category with no corpus coverage

        Returns: (source_type, value, confidence)
        """
        cal_layer = self._get_calibration_layer()

        if platform:
            score, confidence, source_desc = cal_layer.get_calibrated_score(
                platform=platform,
                mechanism=mechanism,
                category=category,
                corpus_prior=0.5,  # Will be replaced
            )

            # Get actual corpus prior
            prior_svc = self._get_prior_service()
            corpus_prior = prior_svc.extract_prior(
                category=category
            )
            mech_prior = corpus_prior.get_mechanism_prior(mechanism)
            if mech_prior:
                corpus_value = mech_prior.effect_size
                score, confidence, source_desc = cal_layer.get_calibrated_score(
                    platform=platform,
                    mechanism=mechanism,
                    category=category,
                    corpus_prior=corpus_value,
                )
                return source_desc, score, confidence

        # No platform specified — return corpus prior
        prior_svc = self._get_prior_service()
        corpus_prior = prior_svc.extract_prior(category=category)
        mech_prior = corpus_prior.get_mechanism_prior(mechanism)
        if mech_prior:
            return (
                PriorSourceType.CORPUS.value,
                mech_prior.effect_size,
                mech_prior.confidence.confidence_score,
            )

        return PriorSourceType.CORPUS.value, 0.5, 0.1

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning loop statistics."""
        return {
            "outcomes_processed": self._outcomes_processed,
            "modality_adjustments": len(self._modality_adjustments),
            "channel_adjustments": len(self._channel_adjustments),
            "conflicts_detected": len(self._conflict_log),
            "top_modality_adjustments": sorted(
                [
                    {
                        "key": k,
                        "factor": v.adjustment_factor,
                        "confidence": v.confidence,
                        "observations": v.observation_count,
                    }
                    for k, v in self._modality_adjustments.items()
                    if abs(v.adjustment_factor - 1.0) > 0.05
                ],
                key=lambda x: abs(x["factor"] - 1.0),
                reverse=True,
            )[:10],
            "recent_conflicts": self._conflict_log[-5:],
        }


# =============================================================================
# SINGLETON
# =============================================================================

_loop: Optional[BidirectionalLearningLoop] = None


def get_bidirectional_learning_loop() -> BidirectionalLearningLoop:
    """Get singleton BidirectionalLearningLoop."""
    global _loop
    if _loop is None:
        _loop = BidirectionalLearningLoop()
    return _loop
