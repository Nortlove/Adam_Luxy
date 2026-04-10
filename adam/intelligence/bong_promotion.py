# =============================================================================
# BONG Promotion Tracker
# Location: adam/intelligence/bong_promotion.py
# Unified System Evolution Directive, Section 5/A.4
# =============================================================================

"""
Tracks criteria for promoting BONG from additive to authoritative.

BONG becomes the authority for Thompson Sampling and information value
bidding when ALL conditions are met:
1. Calibration check passes
2. 1,000+ posterior updates across 50+ unique individuals
3. BONG-selected mechanism differs from Beta in >15% of cases
4. On disagreements, BONG wins at equal or better rate

Once promoted:
- select_mechanism() reads from BONG exclusively
- information_value() uses BONG joint entropy exclusively
- Betas continue to update (audit trail) but nothing reads them
- After 30 days: remove Beta update path
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class PromotionTracker:
    """Track criteria for BONG promotion to authoritative."""

    calibration_passed: bool = False
    calibration_correction_applied: float = 1.0

    total_bong_updates: int = 0
    unique_individuals_updated: Set[str] = field(default_factory=set)

    # Selection disagreement tracking
    total_selections: int = 0
    disagreement_count: int = 0
    # On disagreements: which one's outcome was better?
    bong_deployed_on_disagreement: int = 0
    beta_deployed_on_disagreement: int = 0
    bong_conversion_on_disagreement: int = 0
    beta_conversion_on_disagreement: int = 0

    # Promotion state
    promoted: bool = False
    promoted_at: Optional[float] = None

    @property
    def disagreement_rate(self) -> float:
        if self.total_selections == 0:
            return 0.0
        return self.disagreement_count / self.total_selections

    @property
    def bong_win_rate(self) -> float:
        """BONG conversion rate on disagreement cases where BONG was deployed."""
        if self.bong_deployed_on_disagreement == 0:
            return 0.0
        return self.bong_conversion_on_disagreement / self.bong_deployed_on_disagreement

    @property
    def beta_win_rate(self) -> float:
        if self.beta_deployed_on_disagreement == 0:
            return 0.0
        return self.beta_conversion_on_disagreement / self.beta_deployed_on_disagreement

    @property
    def ready_for_promotion(self) -> bool:
        return (
            self.calibration_passed
            and self.total_bong_updates >= 1000
            and len(self.unique_individuals_updated) >= 50
            and self.disagreement_rate >= 0.15
            and (
                self.bong_deployed_on_disagreement < 10
                or self.bong_win_rate >= self.beta_win_rate
            )
        )

    def record_update(self, user_id: str):
        """Record a BONG posterior update."""
        self.total_bong_updates += 1
        self.unique_individuals_updated.add(user_id)

    def record_selection(
        self,
        bong_selected: str,
        beta_selected: str,
        deployed: str,
    ):
        """Record a mechanism selection with both BONG and Beta recommendations."""
        self.total_selections += 1
        if bong_selected != beta_selected:
            self.disagreement_count += 1
            if deployed == bong_selected:
                self.bong_deployed_on_disagreement += 1
            elif deployed == beta_selected:
                self.beta_deployed_on_disagreement += 1

    def record_disagreement_outcome(self, deployed_was_bong: bool, converted: bool):
        """Record outcome on a disagreement case."""
        if converted:
            if deployed_was_bong:
                self.bong_conversion_on_disagreement += 1
            else:
                self.beta_conversion_on_disagreement += 1

    def check_and_promote(self) -> bool:
        """Check promotion criteria and promote if met."""
        if self.promoted:
            return True
        if self.ready_for_promotion:
            self.promoted = True
            self.promoted_at = time.time()
            logger.info(
                "BONG PROMOTED to authoritative. Updates=%d, users=%d, "
                "disagreement=%.1f%%, BONG_win=%.1f%% vs Beta_win=%.1f%%",
                self.total_bong_updates,
                len(self.unique_individuals_updated),
                self.disagreement_rate * 100,
                self.bong_win_rate * 100,
                self.beta_win_rate * 100,
            )
            return True
        return False

    @property
    def stats(self) -> Dict:
        return {
            "calibration_passed": self.calibration_passed,
            "total_bong_updates": self.total_bong_updates,
            "unique_individuals": len(self.unique_individuals_updated),
            "total_selections": self.total_selections,
            "disagreement_count": self.disagreement_count,
            "disagreement_rate": round(self.disagreement_rate, 3),
            "bong_win_rate": round(self.bong_win_rate, 3),
            "beta_win_rate": round(self.beta_win_rate, 3),
            "promoted": self.promoted,
            "ready": self.ready_for_promotion,
        }


# Singleton
_tracker: Optional[PromotionTracker] = None


def get_promotion_tracker() -> PromotionTracker:
    """Get or create the singleton PromotionTracker."""
    global _tracker
    if _tracker is None:
        _tracker = PromotionTracker()
    return _tracker
