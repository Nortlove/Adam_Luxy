# =============================================================================
# ADAM Journey Sync Service
# Location: adam/platform/shared/journey_sync.py
# =============================================================================

"""
JOURNEY SYNC SERVICE

Synchronize user journey states across platforms.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.platform.shared.models import (
    Platform,
    JourneySyncResult,
)
from adam.user.journey.models import JourneyStage, DecisionUrgency
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


# Stage progression order (for "most advanced" sync)
STAGE_ORDER = [
    JourneyStage.UNAWARE,
    JourneyStage.AWARE,
    JourneyStage.CONSIDERING,
    JourneyStage.RESEARCHING,
    JourneyStage.COMPARING,
    JourneyStage.READY_TO_BUY,
    JourneyStage.DECIDING,
    JourneyStage.PURCHASING,
    JourneyStage.PURCHASED,
    JourneyStage.USING,
    JourneyStage.EVALUATING,
    JourneyStage.ADVOCATING,
]

# Urgency priority order
URGENCY_ORDER = [
    DecisionUrgency.PASSIVE,
    DecisionUrgency.PLANNING,
    DecisionUrgency.THIS_WEEK,
    DecisionUrgency.TODAY,
    DecisionUrgency.IMMEDIATE,
]


class JourneySyncService:
    """
    Service for synchronizing journey state across platforms.
    
    Sync strategies:
    1. MOST_ADVANCED: Take the most progressed stage
    2. MOST_RECENT: Take the most recently updated
    3. WEIGHTED: Weight by platform reliability and recency
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        
        # In-memory journey store (production: Neo4j)
        self._journey_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    async def sync_journey(
        self,
        adam_id: str,
        category: str,
        platform: Platform,
        stage: JourneyStage,
        urgency: DecisionUrgency,
        context: Optional[Dict[str, Any]] = None,
    ) -> JourneySyncResult:
        """
        Sync journey state from a platform.
        """
        
        # Get current states from all platforms
        user_journeys = self._journey_store.get(adam_id, {})
        category_journeys = user_journeys.get(category, {})
        
        # Record this platform's state
        category_journeys[platform.value] = {
            "stage": stage.value,
            "urgency": urgency.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "context": context or {},
        }
        
        # Sync using most_advanced strategy
        unified_stage, unified_urgency, conflict = self._sync_most_advanced(
            category_journeys
        )
        
        # Store
        if adam_id not in self._journey_store:
            self._journey_store[adam_id] = {}
        if category not in self._journey_store[adam_id]:
            self._journey_store[adam_id][category] = {}
        
        self._journey_store[adam_id][category] = category_journeys
        self._journey_store[adam_id][category]["_unified"] = {
            "stage": unified_stage,
            "urgency": unified_urgency,
        }
        
        # Cache
        if self.cache:
            await self.cache.set(
                f"journey_sync:{adam_id}:{category}",
                {
                    "unified_stage": unified_stage,
                    "unified_urgency": unified_urgency,
                    "platforms": category_journeys,
                },
                ttl=3600,
            )
        
        return JourneySyncResult(
            adam_id=adam_id,
            category=category,
            unified_stage=unified_stage,
            unified_urgency=unified_urgency,
            platform_states={
                p: s["stage"]
                for p, s in category_journeys.items()
                if not p.startswith("_")
            },
            sync_method="most_advanced",
            conflict_detected=conflict,
        )
    
    def _sync_most_advanced(
        self,
        platform_states: Dict[str, Dict[str, Any]],
    ) -> tuple:
        """
        Sync using most advanced stage.
        
        Returns (unified_stage, unified_urgency, conflict_detected)
        """
        
        stages = []
        urgencies = []
        
        for platform, state in platform_states.items():
            if platform.startswith("_"):
                continue
            
            try:
                stage = JourneyStage(state["stage"])
                urgency = DecisionUrgency(state["urgency"])
                stages.append(stage)
                urgencies.append(urgency)
            except (KeyError, ValueError):
                continue
        
        if not stages:
            return JourneyStage.UNAWARE.value, DecisionUrgency.PASSIVE.value, False
        
        # Find most advanced stage
        max_stage_idx = max(
            STAGE_ORDER.index(s) if s in STAGE_ORDER else 0
            for s in stages
        )
        unified_stage = STAGE_ORDER[max_stage_idx]
        
        # Find highest urgency
        max_urgency_idx = max(
            URGENCY_ORDER.index(u) if u in URGENCY_ORDER else 0
            for u in urgencies
        )
        unified_urgency = URGENCY_ORDER[max_urgency_idx]
        
        # Detect conflict (stages differ by > 2 steps)
        stage_indices = [
            STAGE_ORDER.index(s) if s in STAGE_ORDER else 0
            for s in stages
        ]
        conflict = (max(stage_indices) - min(stage_indices)) > 2
        
        return unified_stage.value, unified_urgency.value, conflict
    
    async def get_unified_journey(
        self,
        adam_id: str,
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """Get unified journey state for a category."""
        
        user_journeys = self._journey_store.get(adam_id, {})
        category_journeys = user_journeys.get(category, {})
        
        if "_unified" in category_journeys:
            return category_journeys["_unified"]
        
        return None
    
    async def get_all_journeys(
        self,
        adam_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Get all unified journeys for a user."""
        
        result = {}
        user_journeys = self._journey_store.get(adam_id, {})
        
        for category, data in user_journeys.items():
            if "_unified" in data:
                result[category] = data["_unified"]
        
        return result
    
    async def detect_cross_platform_signals(
        self,
        adam_id: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        """
        Detect signals that span platforms.
        
        Example: User researches on WPP display, then hears ad on iHeart.
        This is a cross-platform journey signal.
        """
        
        user_journeys = self._journey_store.get(adam_id, {})
        category_journeys = user_journeys.get(category, {})
        
        signals = []
        
        platforms = [
            p for p in category_journeys.keys()
            if not p.startswith("_")
        ]
        
        if len(platforms) > 1:
            # Multiple platforms have touched this category
            signals.append({
                "type": "cross_platform_consideration",
                "platforms": platforms,
                "category": category,
                "implication": "User is actively researching across channels",
            })
        
        # Check for stage progression across platforms
        stages_by_platform = {}
        for platform in platforms:
            if "stage" in category_journeys[platform]:
                try:
                    stage = JourneyStage(category_journeys[platform]["stage"])
                    stages_by_platform[platform] = stage
                except ValueError:
                    pass
        
        if len(stages_by_platform) > 1:
            stages = list(stages_by_platform.values())
            indices = [
                STAGE_ORDER.index(s) if s in STAGE_ORDER else 0
                for s in stages
            ]
            
            if max(indices) > 3:  # Past RESEARCHING
                signals.append({
                    "type": "multi_platform_intent",
                    "highest_stage": STAGE_ORDER[max(indices)].value,
                    "implication": "User shows purchase intent across platforms",
                })
        
        return signals
