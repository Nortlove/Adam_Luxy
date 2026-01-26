# =============================================================================
# ADAM Fast Path Router
# Location: adam/performance/fast_path.py
# =============================================================================

"""
FAST PATH ROUTER

Route simple requests through fast path for sub-50ms latency.

Fast path uses:
- Cached user profiles
- Pre-computed mechanism selections
- Simple heuristic decisions
- No atom DAG execution
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from adam.performance.latency import ExecutionPath

logger = logging.getLogger(__name__)


# =============================================================================
# FAST PATH CRITERIA
# =============================================================================

class FastPathCriteria(BaseModel):
    """Criteria for using fast path."""
    
    # User must have cached profile
    require_cached_profile: bool = Field(default=True)
    
    # Minimum profile confidence
    min_profile_confidence: float = Field(ge=0.0, le=1.0, default=0.6)
    
    # Must have mechanism history
    require_mechanism_history: bool = Field(default=True)
    min_mechanism_observations: int = Field(default=10, ge=0)
    
    # Request characteristics
    max_ad_candidates: int = Field(default=10, ge=1)
    
    # Skip for new users
    min_user_interactions: int = Field(default=5, ge=0)


class FastPathDecision(BaseModel):
    """Result of fast path routing decision."""
    
    use_fast_path: bool
    selected_path: ExecutionPath
    
    # Reasoning
    reason: str
    criteria_met: Dict[str, bool] = Field(default_factory=dict)
    
    # If fast path, precomputed values
    cached_profile: Optional[Dict[str, Any]] = None
    cached_mechanisms: Optional[Dict[str, float]] = None
    
    # Timing
    decision_time_ms: float = Field(default=0.0)


# =============================================================================
# FAST PATH ROUTER
# =============================================================================

class FastPathRouter:
    """
    Router that decides between fast and full paths.
    """
    
    def __init__(
        self,
        cache=None,
        criteria: Optional[FastPathCriteria] = None,
    ):
        self.cache = cache
        self.criteria = criteria or FastPathCriteria()
    
    async def route(
        self,
        user_id: str,
        request_context: Dict[str, Any],
    ) -> FastPathDecision:
        """
        Decide execution path for a request.
        """
        import time
        start = time.perf_counter()
        
        criteria_met = {}
        
        # Check cached profile
        cached_profile = None
        if self.cache:
            cached_profile = await self.cache.get(f"profile:{user_id}")
        
        has_profile = cached_profile is not None
        criteria_met["cached_profile"] = has_profile
        
        if self.criteria.require_cached_profile and not has_profile:
            return self._slow_path("No cached profile", criteria_met, start)
        
        # Check profile confidence
        if cached_profile:
            confidence = cached_profile.get("confidence", 0.0)
            criteria_met["profile_confidence"] = confidence >= self.criteria.min_profile_confidence
            
            if confidence < self.criteria.min_profile_confidence:
                return self._slow_path("Profile confidence too low", criteria_met, start)
        
        # Check mechanism history
        cached_mechanisms = None
        if self.cache:
            cached_mechanisms = await self.cache.get(f"mechanisms:{user_id}")
        
        has_mechanisms = cached_mechanisms is not None
        criteria_met["mechanism_history"] = has_mechanisms
        
        if self.criteria.require_mechanism_history:
            if not has_mechanisms:
                return self._slow_path("No mechanism history", criteria_met, start)
            
            observations = cached_mechanisms.get("total_observations", 0)
            criteria_met["mechanism_observations"] = (
                observations >= self.criteria.min_mechanism_observations
            )
            
            if observations < self.criteria.min_mechanism_observations:
                return self._slow_path("Insufficient mechanism data", criteria_met, start)
        
        # Check request characteristics
        num_candidates = len(request_context.get("ad_candidates", []))
        criteria_met["ad_candidates"] = num_candidates <= self.criteria.max_ad_candidates
        
        if num_candidates > self.criteria.max_ad_candidates:
            return self._reasoning_path("Too many ad candidates", criteria_met, start)
        
        # Check user interaction history
        interactions = cached_profile.get("interaction_count", 0) if cached_profile else 0
        criteria_met["user_interactions"] = interactions >= self.criteria.min_user_interactions
        
        if interactions < self.criteria.min_user_interactions:
            return self._reasoning_path("New user needs full reasoning", criteria_met, start)
        
        # All criteria met - use fast path
        duration = (time.perf_counter() - start) * 1000
        
        return FastPathDecision(
            use_fast_path=True,
            selected_path=ExecutionPath.FAST,
            reason="All fast path criteria met",
            criteria_met=criteria_met,
            cached_profile=cached_profile,
            cached_mechanisms=cached_mechanisms,
            decision_time_ms=duration,
        )
    
    def _slow_path(
        self,
        reason: str,
        criteria_met: Dict[str, bool],
        start: float,
    ) -> FastPathDecision:
        """Return decision for standard path."""
        import time
        duration = (time.perf_counter() - start) * 1000
        
        return FastPathDecision(
            use_fast_path=False,
            selected_path=ExecutionPath.STANDARD,
            reason=reason,
            criteria_met=criteria_met,
            decision_time_ms=duration,
        )
    
    def _reasoning_path(
        self,
        reason: str,
        criteria_met: Dict[str, bool],
        start: float,
    ) -> FastPathDecision:
        """Return decision for reasoning path."""
        import time
        duration = (time.perf_counter() - start) * 1000
        
        return FastPathDecision(
            use_fast_path=False,
            selected_path=ExecutionPath.REASONING,
            reason=reason,
            criteria_met=criteria_met,
            decision_time_ms=duration,
        )
    
    async def execute_fast_path(
        self,
        decision: FastPathDecision,
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute fast path decision.
        
        Uses cached data to make quick decision without atom DAG.
        """
        if not decision.use_fast_path:
            raise ValueError("Cannot execute fast path for non-fast decision")
        
        profile = decision.cached_profile or {}
        mechanisms = decision.cached_mechanisms or {}
        
        # Simple scoring based on cached data
        ad_candidates = request_context.get("ad_candidates", [])
        
        if not ad_candidates:
            return {"selected_ad": None, "fast_path": True}
        
        # Score each candidate
        best_score = -1.0
        best_candidate = None
        
        for candidate in ad_candidates:
            score = self._score_candidate_fast(candidate, profile, mechanisms)
            if score > best_score:
                best_score = score
                best_candidate = candidate
        
        return {
            "selected_ad": best_candidate,
            "score": best_score,
            "fast_path": True,
            "mechanism": mechanisms.get("best_mechanism", "automatic_evaluation"),
        }
    
    def _score_candidate_fast(
        self,
        candidate: Dict[str, Any],
        profile: Dict[str, Any],
        mechanisms: Dict[str, float],
    ) -> float:
        """Fast scoring of a candidate."""
        score = 0.5
        
        # Mechanism alignment
        candidate_mechanism = candidate.get("mechanism")
        if candidate_mechanism and candidate_mechanism in mechanisms:
            score += mechanisms[candidate_mechanism] * 0.3
        
        # Category alignment
        user_categories = profile.get("category_affinities", {})
        candidate_category = candidate.get("category")
        if candidate_category and candidate_category in user_categories:
            score += user_categories[candidate_category] * 0.2
        
        # Base quality
        score += candidate.get("quality_score", 0.5) * 0.2
        
        return min(1.0, max(0.0, score))
