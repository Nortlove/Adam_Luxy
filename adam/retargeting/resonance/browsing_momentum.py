# =============================================================================
# Browsing Sequence Momentum Tracker
# Location: adam/retargeting/resonance/browsing_momentum.py
# =============================================================================

"""
Tracks compound psychological priming from multiple page visits within
a browsing session.

A buyer who reads 3 articles about airline failures before seeing our ad
is in a DEEPER negativity state than after 1. The browsing SEQUENCE
creates compound priming — each page's mindstate adds to a momentum
vector that modifies the buyer's current psychological field.

The momentum vector is an exponentially-weighted average of page
mindstate vectors observed during the session, with recency weighting.
Recent pages contribute more than older ones.

Integration:
- Pixel events include page_url for each pageview
- We look up page profiles from cache (or score on-the-fly)
- The momentum vector is passed to the bilateral cascade as
  additional context, modulating mechanism effectiveness

Example:
    Session: [airline_delay_article, airport_lounge_review, uber_complaint]
    Momentum: high negativity, high loss_aversion, low trust
    Result: anxiety_resolution mechanism gets +30% boost,
            social_proof gets dampened (buyer in distrust mode)
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Exponential decay half-life (in number of pages)
_DECAY_HALF_LIFE = 3.0  # After 3 pages, a page's influence halves


@dataclass
class BrowsingMomentum:
    """Compound psychological state from a browsing sequence."""

    buyer_id: str
    session_id: str = ""

    # Exponentially-weighted average of page mindstate vectors
    momentum_vector: Dict[str, float] = field(default_factory=dict)

    # Raw page sequence (most recent last)
    page_sequence: List[Dict[str, Any]] = field(default_factory=list)

    # Derived state
    sequence_length: int = 0
    dominant_valence: str = "neutral"  # positive, negative, mixed, neutral
    priming_depth: float = 0.0  # 0=no priming, 1=deep priming
    open_channels: List[str] = field(default_factory=list)
    closed_channels: List[str] = field(default_factory=list)

    # Timing
    first_page_at: float = 0.0
    last_page_at: float = 0.0


class BrowsingMomentumTracker:
    """Tracks and computes browsing sequence momentum per buyer.

    Maintains a rolling window of page mindstates per buyer session.
    Computes the compound psychological priming effect.
    """

    # Maximum pages to track per session
    _MAX_PAGES_PER_SESSION = 20
    # Maximum concurrent sessions
    _MAX_SESSIONS = 10_000
    # Session timeout (seconds)
    _SESSION_TIMEOUT = 1800  # 30 minutes

    def __init__(self):
        # buyer_id → BrowsingMomentum
        self._sessions: Dict[str, BrowsingMomentum] = {}

    def record_pageview(
        self,
        buyer_id: str,
        page_url: str,
        page_edge_dimensions: Optional[Dict[str, float]] = None,
        session_id: str = "",
    ) -> BrowsingMomentum:
        """Record a page view and update the momentum vector.

        Args:
            buyer_id: Buyer identifier
            page_url: URL of the page visited
            page_edge_dimensions: 20-dim edge vector for the page
                (from page intelligence cache)
            session_id: Optional session identifier

        Returns:
            Updated BrowsingMomentum for this buyer
        """
        now = time.time()

        # Get or create session
        momentum = self._sessions.get(buyer_id)
        if momentum is None or (now - momentum.last_page_at > self._SESSION_TIMEOUT):
            # New session
            momentum = BrowsingMomentum(
                buyer_id=buyer_id,
                session_id=session_id or f"sess_{int(now)}",
                first_page_at=now,
            )
            self._sessions[buyer_id] = momentum

        # Add page to sequence
        page_entry = {
            "url": page_url,
            "edge_dimensions": page_edge_dimensions or {},
            "timestamp": now,
        }
        momentum.page_sequence.append(page_entry)
        momentum.last_page_at = now
        momentum.sequence_length = len(momentum.page_sequence)

        # Cap sequence length
        if len(momentum.page_sequence) > self._MAX_PAGES_PER_SESSION:
            momentum.page_sequence = momentum.page_sequence[-self._MAX_PAGES_PER_SESSION:]

        # Recompute momentum vector
        self._compute_momentum(momentum)

        # Evict stale sessions
        if len(self._sessions) > self._MAX_SESSIONS:
            self._evict_stale(now)

        return momentum

    def get_momentum(self, buyer_id: str) -> Optional[BrowsingMomentum]:
        """Get current browsing momentum for a buyer."""
        momentum = self._sessions.get(buyer_id)
        if momentum is None:
            return None
        if time.time() - momentum.last_page_at > self._SESSION_TIMEOUT:
            del self._sessions[buyer_id]
            return None
        return momentum

    def _compute_momentum(self, momentum: BrowsingMomentum) -> None:
        """Recompute the exponentially-weighted momentum vector.

        Recent pages have more influence than older ones.
        The decay factor is: w_i = 2^(-i / half_life)
        where i is the distance from the most recent page.
        """
        pages = momentum.page_sequence
        if not pages:
            return

        n = len(pages)
        all_dims = set()
        for p in pages:
            all_dims.update(p.get("edge_dimensions", {}).keys())

        if not all_dims:
            return

        # Compute weighted average
        weighted_sum: Dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for i, page in enumerate(reversed(pages)):
            # i=0 is most recent, i=n-1 is oldest
            weight = 2.0 ** (-i / _DECAY_HALF_LIFE)
            dims = page.get("edge_dimensions", {})
            for dim in all_dims:
                weighted_sum[dim] += dims.get(dim, 0.5) * weight
            total_weight += weight

        if total_weight > 0:
            momentum.momentum_vector = {
                dim: val / total_weight
                for dim, val in weighted_sum.items()
            }

        # Derive state properties
        vec = momentum.momentum_vector

        # Dominant valence from emotional_resonance + regulatory_fit
        er = vec.get("emotional_resonance", 0.5)
        rf = vec.get("regulatory_fit", 0.5)
        if er > 0.6 and rf > 0.6:
            momentum.dominant_valence = "positive"
        elif er < 0.4 or rf < 0.4:
            momentum.dominant_valence = "negative"
        elif abs(er - 0.5) > 0.15 or abs(rf - 0.5) > 0.15:
            momentum.dominant_valence = "mixed"
        else:
            momentum.dominant_valence = "neutral"

        # Priming depth: how far from neutral is the momentum?
        deviations = [abs(v - 0.5) for v in vec.values()]
        momentum.priming_depth = min(1.0, np.mean(deviations) * 4) if deviations else 0.0

        # Open/closed channels based on extreme momentum values
        momentum.open_channels = [d for d, v in vec.items() if v > 0.65]
        momentum.closed_channels = [d for d, v in vec.items() if v < 0.35]

    def _evict_stale(self, now: float) -> None:
        """Evict sessions older than timeout."""
        stale = [
            bid for bid, m in self._sessions.items()
            if now - m.last_page_at > self._SESSION_TIMEOUT
        ]
        for bid in stale:
            del self._sessions[bid]
        if stale:
            logger.debug("Evicted %d stale browsing sessions", len(stale))

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "avg_sequence_length": (
                np.mean([m.sequence_length for m in self._sessions.values()])
                if self._sessions else 0
            ),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_tracker: Optional[BrowsingMomentumTracker] = None


def get_browsing_momentum_tracker() -> BrowsingMomentumTracker:
    global _tracker
    if _tracker is None:
        _tracker = BrowsingMomentumTracker()
    return _tracker
