# =============================================================================
# ADAM Temporal Patterns Service
# Location: adam/services/temporal_patterns.py
# =============================================================================

"""
TEMPORAL PATTERNS SERVICE

Analyzes and predicts temporal patterns in user behavior for optimal ad timing.

This service tracks:
1. Time-of-day engagement patterns (circadian rhythm matching)
2. Day-of-week patterns (weekday vs weekend behavior)
3. Seasonal patterns (holiday sensitivity, seasonal interests)
4. Life event detection (major life transitions)

Key Psycholinguistic Insight:
- Cognitive load varies by time of day (morning clarity vs afternoon fatigue)
- Emotional receptivity peaks at certain times
- Purchase decisions cluster around paydays, seasons, life events
- Matching message complexity to cognitive state improves effectiveness
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class DayPeriod(str, Enum):
    """Time of day periods."""
    
    EARLY_MORNING = "early_morning"  # 5-8
    MORNING = "morning"  # 8-12
    MIDDAY = "midday"  # 12-14
    AFTERNOON = "afternoon"  # 14-17
    EVENING = "evening"  # 17-21
    NIGHT = "night"  # 21-24
    LATE_NIGHT = "late_night"  # 0-5


class Chronotype(str, Enum):
    """User chronotype (circadian preference)."""
    
    MORNING_LARK = "morning_lark"
    NEUTRAL = "neutral"
    NIGHT_OWL = "night_owl"


@dataclass
class LifeEvent:
    """Detected life event."""
    
    event_type: str  # moving, new_job, new_baby, wedding, graduation, etc.
    confidence: float
    detected_at: datetime
    evidence: List[str] = field(default_factory=list)


@dataclass
class TemporalPatternProfile:
    """Complete temporal pattern profile for a user."""
    
    user_id: str
    
    # Chronotype
    chronotype: Chronotype = Chronotype.NEUTRAL
    chronotype_confidence: float = 0.5
    
    # Engagement patterns by period
    period_engagement: Dict[str, float] = field(default_factory=dict)
    best_engagement_period: Optional[DayPeriod] = None
    worst_engagement_period: Optional[DayPeriod] = None
    
    # Day of week patterns
    weekday_vs_weekend: float = 0.5  # 0 = weekday only, 1 = weekend only
    best_day_of_week: Optional[int] = None  # 0-6
    
    # Cognitive state predictions
    predicted_cognitive_load: Dict[str, float] = field(default_factory=dict)
    
    # Life events
    detected_life_events: List[LifeEvent] = field(default_factory=list)


# =============================================================================
# CIRCADIAN DEFAULTS
# =============================================================================

# Default cognitive load by time period (research-based)
# Higher = more cognitive resources available
DEFAULT_COGNITIVE_CAPACITY = {
    DayPeriod.EARLY_MORNING: 0.6,  # Ramping up
    DayPeriod.MORNING: 0.9,  # Peak for most people
    DayPeriod.MIDDAY: 0.7,  # Post-lunch dip
    DayPeriod.AFTERNOON: 0.75,  # Recovery
    DayPeriod.EVENING: 0.65,  # Winding down
    DayPeriod.NIGHT: 0.5,  # Tired but can still engage
    DayPeriod.LATE_NIGHT: 0.4,  # Low capacity
}

# Emotional receptivity by time period
# Higher = more open to emotional appeals
DEFAULT_EMOTIONAL_RECEPTIVITY = {
    DayPeriod.EARLY_MORNING: 0.5,  # Neutral
    DayPeriod.MORNING: 0.6,  # Open but focused
    DayPeriod.MIDDAY: 0.7,  # Relaxed
    DayPeriod.AFTERNOON: 0.65,  # Moderate
    DayPeriod.EVENING: 0.8,  # Most receptive (relaxed, leisure time)
    DayPeriod.NIGHT: 0.75,  # Receptive
    DayPeriod.LATE_NIGHT: 0.85,  # Guard is down, very receptive but impaired judgment
}


# =============================================================================
# SERVICE
# =============================================================================

class TemporalPatternsService:
    """
    Service for temporal pattern analysis.
    
    Provides:
    - User engagement pattern analysis
    - Optimal timing recommendations
    - Cognitive state predictions
    - Life event detection
    
    Key for psycholinguistic advertising:
    - Match message complexity to cognitive capacity
    - Match emotional appeals to emotional receptivity
    - Detect life events for highly relevant targeting
    """
    
    def __init__(
        self,
        neo4j_driver: Optional[AsyncDriver] = None,
    ):
        self.driver = neo4j_driver
        
        # Cache for user patterns
        self._cache: Dict[str, TemporalPatternProfile] = {}
        
        logger.info("TemporalPatternsService initialized")
    
    async def get_user_patterns(
        self,
        user_id: str,
    ) -> TemporalPatternProfile:
        """
        Get temporal patterns for a user.
        
        Combines historical data with intelligent defaults.
        """
        
        # Check cache
        if user_id in self._cache:
            return self._cache[user_id]
        
        # Try to load from graph
        if self.driver:
            profile = await self._query_patterns_from_graph(user_id)
            if profile:
                self._cache[user_id] = profile
                return profile
        
        # Build default profile with current time awareness
        profile = self._build_default_profile(user_id)
        self._cache[user_id] = profile
        return profile
    
    async def _query_patterns_from_graph(
        self,
        user_id: str,
    ) -> Optional[TemporalPatternProfile]:
        """Query temporal patterns from Neo4j."""
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (u:User {user_id: $user_id})-[:HAS_TEMPORAL_PATTERN]->(tp:TemporalPattern)
                    OPTIONAL MATCH (u)-[:EXPERIENCED_LIFE_EVENT]->(le:LifeEvent)
                    RETURN tp, COLLECT(le) as life_events
                    """,
                    user_id=user_id
                )
                
                record = await result.single()
                if not record or not record["tp"]:
                    return None
                
                tp_data = record["tp"]
                
                # Build life events
                life_events = []
                for le_data in record["life_events"]:
                    if le_data:
                        life_events.append(LifeEvent(
                            event_type=le_data.get("event_type", "unknown"),
                            confidence=le_data.get("confidence", 0.5),
                            detected_at=datetime.now(timezone.utc),
                        ))
                
                profile = TemporalPatternProfile(
                    user_id=user_id,
                    chronotype=Chronotype(tp_data.get("chronotype", "neutral")),
                    chronotype_confidence=tp_data.get("chronotype_confidence", 0.5),
                    detected_life_events=life_events,
                )
                
                return profile
                
        except Exception as e:
            logger.error(f"Error querying temporal patterns: {e}")
            return None
    
    def _build_default_profile(
        self,
        user_id: str,
    ) -> TemporalPatternProfile:
        """Build default profile with intelligent defaults."""
        
        # Build cognitive predictions based on defaults
        predicted_cognitive = {
            period.value: capacity
            for period, capacity in DEFAULT_COGNITIVE_CAPACITY.items()
        }
        
        return TemporalPatternProfile(
            user_id=user_id,
            chronotype=Chronotype.NEUTRAL,
            chronotype_confidence=0.3,  # Low confidence for defaults
            predicted_cognitive_load=predicted_cognitive,
        )
    
    async def detect_life_events(
        self,
        user_id: str,
    ) -> List[LifeEvent]:
        """
        Detect potential life events for a user.
        
        Life events are crucial for psycholinguistic advertising because:
        - They represent major decision points
        - They create high receptivity to relevant messages
        - They often trigger category entry
        """
        
        profile = await self.get_user_patterns(user_id)
        return profile.detected_life_events
    
    def get_current_cognitive_capacity(
        self,
        chronotype: Chronotype = Chronotype.NEUTRAL,
        hour: Optional[int] = None,
    ) -> float:
        """
        Get current cognitive capacity prediction.
        
        Adjusts based on chronotype:
        - Morning larks: shifted earlier
        - Night owls: shifted later
        """
        
        if hour is None:
            hour = datetime.now().hour
        
        # Determine period
        period = self._hour_to_period(hour)
        
        # Get base capacity
        base_capacity = DEFAULT_COGNITIVE_CAPACITY.get(period, 0.6)
        
        # Adjust for chronotype
        if chronotype == Chronotype.MORNING_LARK:
            if hour < 12:
                base_capacity += 0.1
            elif hour > 18:
                base_capacity -= 0.15
        elif chronotype == Chronotype.NIGHT_OWL:
            if hour < 10:
                base_capacity -= 0.15
            elif hour > 18:
                base_capacity += 0.1
        
        return max(0.1, min(1.0, base_capacity))
    
    def get_current_emotional_receptivity(
        self,
        hour: Optional[int] = None,
    ) -> float:
        """Get current emotional receptivity prediction."""
        
        if hour is None:
            hour = datetime.now().hour
        
        period = self._hour_to_period(hour)
        return DEFAULT_EMOTIONAL_RECEPTIVITY.get(period, 0.6)
    
    def _hour_to_period(self, hour: int) -> DayPeriod:
        """Convert hour to day period."""
        
        if 0 <= hour < 5:
            return DayPeriod.LATE_NIGHT
        elif 5 <= hour < 8:
            return DayPeriod.EARLY_MORNING
        elif 8 <= hour < 12:
            return DayPeriod.MORNING
        elif 12 <= hour < 14:
            return DayPeriod.MIDDAY
        elif 14 <= hour < 17:
            return DayPeriod.AFTERNOON
        elif 17 <= hour < 21:
            return DayPeriod.EVENING
        else:
            return DayPeriod.NIGHT
    
    def get_optimal_message_complexity(
        self,
        cognitive_capacity: float,
    ) -> str:
        """
        Recommend message complexity based on cognitive capacity.
        
        Key insight: Match complexity to capacity for better processing.
        """
        
        if cognitive_capacity >= 0.8:
            return "high"  # Can handle detailed, complex messages
        elif cognitive_capacity >= 0.6:
            return "medium"  # Moderate detail
        else:
            return "simple"  # Keep it very simple


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[TemporalPatternsService] = None


def get_temporal_patterns_service(
    neo4j_driver: Optional[AsyncDriver] = None,
) -> TemporalPatternsService:
    """Get or create the temporal patterns service singleton."""
    global _service
    
    if _service is None:
        _service = TemporalPatternsService(neo4j_driver=neo4j_driver)
    
    return _service
