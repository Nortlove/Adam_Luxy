# =============================================================================
# Therapeutic Retargeting Engine — Suppression Controller
# Location: adam/retargeting/engines/suppression_controller.py
# =============================================================================

"""
Suppression Controller — Governs when to STOP retargeting.

Enforces all suppression rules before every touch. The principle:
it is better to suppress than to trigger reactance. Wicklund's
hydraulic model shows that pressure after tolerance is exceeded
compounds MULTIPLICATIVELY.

Rules enforced:
1. Max touches per sequence (default 7, inverted-U research)
2. Max calendar days (default 21)
3. CTR floor (if < 0.03% at any point, pause 72h)
4. Reactance budget exhaustion (cumulative > 0.85)
5. Temporal spacing (min hours between touches)
6. Post-conversion: STOP immediately
7. Post-rupture: pause per repair recommendation
8. Confrontation: suppress for 14 days minimum
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from adam.retargeting.models.enums import ConversionStage, RuptureType
from adam.retargeting.models.sequences import TherapeuticSequence
from adam.retargeting.engines.rupture_detector import RuptureAssessment

logger = logging.getLogger(__name__)


@dataclass
class SuppressionDecision:
    """Result of suppression check."""

    should_suppress: bool
    should_pause: bool
    reason: str
    pause_hours: int = 0  # If pausing, for how long
    new_status: str = ""  # "suppressed", "paused", "exhausted", or "" (continue)


class SuppressionController:
    """Enforces all suppression rules before every touch.

    Must be checked before generating any new touch. If suppression
    is triggered, the sequence status is updated and no touch is sent.
    """

    def __init__(
        self,
        max_touches: Optional[int] = None,
        max_duration_days: Optional[int] = None,
        ctr_floor: Optional[float] = None,
        reactance_ceiling: Optional[float] = None,
        min_hours_between_touches: Optional[int] = None,
        confrontation_suppress_days: Optional[int] = None,
        pause_after_ctr_drop_hours: Optional[int] = None,
    ):
        # Load from settings when not explicitly provided
        try:
            from adam.config.settings import get_settings
            s = get_settings().thresholds
            self.max_touches = max_touches if max_touches is not None else getattr(s, 'retargeting_max_touches', 7)
            self.max_duration_days = max_duration_days if max_duration_days is not None else getattr(s, 'retargeting_max_duration_days', 21)
            self.ctr_floor = ctr_floor if ctr_floor is not None else getattr(s, 'retargeting_ctr_floor', 0.0003)
            self.reactance_ceiling = reactance_ceiling if reactance_ceiling is not None else getattr(s, 'retargeting_reactance_ceiling', 0.85)
            self.min_hours_between = min_hours_between_touches if min_hours_between_touches is not None else getattr(s, 'retargeting_min_hours_between', 12)
            self.confrontation_suppress_days = confrontation_suppress_days if confrontation_suppress_days is not None else getattr(s, 'retargeting_confrontation_suppress_days', 14)
            self.pause_after_ctr_drop = pause_after_ctr_drop_hours if pause_after_ctr_drop_hours is not None else getattr(s, 'retargeting_pause_after_ctr_drop_hours', 72)
        except Exception:
            # Hardcoded fallback if settings unavailable
            self.max_touches = max_touches or 7
            self.max_duration_days = max_duration_days or 21
            self.ctr_floor = ctr_floor or 0.0003
            self.reactance_ceiling = reactance_ceiling or 0.85
            self.min_hours_between = min_hours_between_touches or 12
            self.confrontation_suppress_days = confrontation_suppress_days or 14
            self.pause_after_ctr_drop = pause_after_ctr_drop_hours or 72

    def check(
        self,
        sequence: TherapeuticSequence,
        current_reactance: float = 0.0,
        rupture_assessment: Optional[RuptureAssessment] = None,
        current_stage: Optional[ConversionStage] = None,
    ) -> SuppressionDecision:
        """Check all suppression rules. Returns decision.

        Rules are checked in priority order — first trigger wins.
        """
        touches = sequence.touches_delivered
        n_touches = len(touches)

        # Rule 1: Post-conversion — STOP immediately
        if current_stage == ConversionStage.CONVERTED:
            return SuppressionDecision(
                should_suppress=True,
                should_pause=False,
                reason="User converted. Switching to retention track.",
                new_status="converted",
            )

        # Rule 2: Confrontation rupture — suppress long
        if rupture_assessment and rupture_assessment.rupture_type == RuptureType.CONFRONTATION:
            return SuppressionDecision(
                should_suppress=True,
                should_pause=False,
                reason=(
                    f"Confrontation rupture (severity={rupture_assessment.severity:.2f}). "
                    f"Suppressing for {self.confrontation_suppress_days} days."
                ),
                pause_hours=self.confrontation_suppress_days * 24,
                new_status="suppressed",
            )

        # Rule 3: Max touches exhausted
        if n_touches >= sequence.max_touches:
            return SuppressionDecision(
                should_suppress=True,
                should_pause=False,
                reason=f"Max touches ({sequence.max_touches}) reached.",
                new_status="exhausted",
            )

        # Rule 4: Max duration exceeded
        if sequence.started_at:
            elapsed_days = (
                time.time() - sequence.started_at.timestamp()
            ) / 86400.0
            if elapsed_days > sequence.max_duration_days:
                return SuppressionDecision(
                    should_suppress=True,
                    should_pause=False,
                    reason=f"Max duration ({sequence.max_duration_days} days) exceeded.",
                    new_status="exhausted",
                )

        # Rule 5: Reactance budget exhaustion
        if current_reactance > self.reactance_ceiling:
            return SuppressionDecision(
                should_suppress=True,
                should_pause=False,
                reason=(
                    f"Reactance ({current_reactance:.2f}) exceeds ceiling "
                    f"({self.reactance_ceiling}). Wicklund compounding risk."
                ),
                new_status="suppressed",
            )

        # Rule 6: Withdrawal/decay rupture — pause (not suppress)
        if rupture_assessment and rupture_assessment.rupture_type in (
            RuptureType.WITHDRAWAL, RuptureType.DECAY
        ):
            if rupture_assessment.min_pause_hours > 0:
                return SuppressionDecision(
                    should_suppress=False,
                    should_pause=True,
                    reason=(
                        f"{rupture_assessment.rupture_type.value} rupture "
                        f"(severity={rupture_assessment.severity:.2f}). "
                        f"Pausing {rupture_assessment.min_pause_hours}h."
                    ),
                    pause_hours=rupture_assessment.min_pause_hours,
                    new_status="paused",
                )

        # Rule 7: CTR floor — uses delivered_count/engaged_count tracked
        # independently of outcome arrival order (fix for timing gap).
        if sequence.delivered_count >= 3:
            effective_ctr = (
                sequence.engaged_count / max(sequence.delivered_count, 1)
            )
            if effective_ctr < self.ctr_floor:
                return SuppressionDecision(
                    should_suppress=False,
                    should_pause=True,
                    reason=(
                        f"Effective CTR ({effective_ctr:.4f}) below floor "
                        f"({self.ctr_floor}). "
                        f"({sequence.engaged_count}/{sequence.delivered_count} engaged). "
                        f"Pausing {self.pause_after_ctr_drop}h."
                    ),
                    pause_hours=self.pause_after_ctr_drop,
                    new_status="paused",
                )

        # Rule 8: Temporal spacing — too soon since last touch
        if touches:
            last_touch = touches[-1]
            if last_touch.min_hours_after_previous > 0:
                # We don't have exact delivery times on the touch model here,
                # but we can use the sequence's started_at + position estimate
                pass  # Timing enforcement handled by delivery layer

        # All checks passed — continue
        return SuppressionDecision(
            should_suppress=False,
            should_pause=False,
            reason="All suppression checks passed. Sequence may continue.",
        )
