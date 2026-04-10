"""
OutcomeBridge — closes the learning loop from delivery outcomes back to ADAM intelligence.

When a delivery adapter reports an outcome (impression, click, conversion),
this bridge:
  1. Routes the signal through the UnifiedLearningHub
  2. Updates the GradientBridge with Shapley-attributed credit
  3. Feeds the cold start Thompson sampler for exploration refinement
  4. Publishes to the event bus for downstream consumers

This is what makes the system self-improving — every outcome
strengthens the graph intelligence for all tenants.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OutcomeBridge:
    """
    Bridges delivery outcomes to the ADAM learning loop.

    Wraps UnifiedLearningHub.emit_outcome() and
    GradientBridgeService.compute_enhanced_attribution().
    """

    def __init__(
        self,
        learning_hub=None,
        gradient_bridge=None,
        cold_start_service=None,
        event_bus=None,
    ):
        self._learning_hub = learning_hub
        self._gradient_bridge = gradient_bridge
        self._cold_start = cold_start_service
        self._event_bus = event_bus
        self._outcomes_processed: int = 0
        self._last_outcome_at: Optional[datetime] = None

    async def record_outcome(
        self,
        tenant_id: str,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        mechanisms_used: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        archetype: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a delivery outcome through the full learning pipeline.

        Args:
            tenant_id: The tenant that generated this outcome
            decision_id: Unique decision ID for attribution tracking
            outcome_type: One of: impression, click, conversion, engagement, skip
            outcome_value: Numeric outcome value (0.0-1.0 for probability, or actual value)
            mechanisms_used: Persuasion mechanisms that were active
            user_id: Optional user identifier
            campaign_id: Optional campaign identifier
            archetype: Detected archetype (if known)
            metadata: Additional context

        Returns:
            Dict with attribution results and learning signals emitted
        """
        start = time.perf_counter()
        result: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "decision_id": decision_id,
            "outcome_type": outcome_type,
            "outcome_value": outcome_value,
            "signals_emitted": 0,
            "attribution": {},
        }

        if self._learning_hub:
            try:
                primary_mechanism = mechanisms_used[0] if mechanisms_used else None
                signals = await self._learning_hub.emit_outcome(
                    decision_id=decision_id,
                    outcome_value=outcome_value,
                    mechanism=primary_mechanism,
                    user_id=user_id,
                    archetype=archetype,
                    metadata={
                        "tenant_id": tenant_id,
                        "campaign_id": campaign_id,
                        "outcome_type": outcome_type,
                        **(metadata or {}),
                    },
                )
                result["signals_emitted"] = signals
            except Exception as e:
                logger.warning("Learning hub outcome failed: %s", e)

        if self._gradient_bridge and mechanisms_used:
            try:
                attribution = await self._gradient_bridge.compute_enhanced_attribution(
                    decision_id=decision_id,
                    request_id=decision_id,
                    user_id=user_id or "anonymous",
                    outcome_value=outcome_value,
                    fallback_mechanism=mechanisms_used[0] if mechanisms_used else None,
                )
                result["attribution"] = attribution
            except Exception as e:
                logger.debug("Gradient bridge attribution unavailable: %s", e)

        if self._cold_start and outcome_type in ("click", "conversion"):
            try:
                await self._cold_start.record_outcome(
                    decision_id=decision_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                    context={
                        "tenant_id": tenant_id,
                        "archetype": archetype,
                        "mechanisms": mechanisms_used,
                    },
                )
            except Exception as e:
                logger.debug("Cold start outcome recording failed: %s", e)

        if self._event_bus:
            try:
                from adam.core.learning.event_bus import Event
                event = Event(
                    topic="adam.outcomes.delivery",
                    data={
                        "tenant_id": tenant_id,
                        "decision_id": decision_id,
                        "outcome_type": outcome_type,
                        "outcome_value": outcome_value,
                        "mechanisms": mechanisms_used,
                        "archetype": archetype,
                    },
                )
                await self._event_bus.publish("adam.outcomes.delivery", event)
            except Exception:
                pass

        elapsed_ms = (time.perf_counter() - start) * 1000
        result["processing_ms"] = round(elapsed_ms, 2)

        self._outcomes_processed += 1
        self._last_outcome_at = datetime.now(timezone.utc)

        return result

    async def record_mechanism_effectiveness(
        self,
        tenant_id: str,
        mechanism: str,
        effectiveness: float,
        archetype: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        """
        Record mechanism-level effectiveness (aggregated from delivery outcomes).
        Returns number of learning signals emitted.
        """
        signals = 0

        if self._learning_hub:
            try:
                signals = await self._learning_hub.emit_mechanism_credit(
                    mechanism=mechanism,
                    credit=effectiveness,
                    archetype=archetype,
                )
            except Exception as e:
                logger.debug("Mechanism credit emission failed: %s", e)

        return signals

    def get_stats(self) -> Dict[str, Any]:
        return {
            "outcomes_processed": self._outcomes_processed,
            "last_outcome_at": self._last_outcome_at.isoformat() if self._last_outcome_at else None,
            "learning_hub_connected": self._learning_hub is not None,
            "gradient_bridge_connected": self._gradient_bridge is not None,
            "cold_start_connected": self._cold_start is not None,
            "event_bus_connected": self._event_bus is not None,
        }
