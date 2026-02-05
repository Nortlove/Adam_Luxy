# =============================================================================
# ADAM Signal Aggregation Service
# Location: adam/user/signal_aggregation/service.py
# =============================================================================

"""
SIGNAL AGGREGATION SERVICE

Orchestrates signal processing and aggregation across sources.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.user.signal_aggregation.processors import (
    SignalProcessor,
    RawSignal,
    ProcessedSignal,
    SignalWindow,
    SignalCategory,
    iHeartSignalProcessor,
    WebSignalProcessor,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics

logger = logging.getLogger(__name__)


# =============================================================================
# AGGREGATION MODELS
# =============================================================================

class UserSignalProfile(BaseModel):
    """Aggregated signal profile for a user."""
    
    user_id: str
    
    # Aggregated features
    behavioral_features: Dict[str, float] = Field(default_factory=dict)
    psychological_indicators: Dict[str, float] = Field(default_factory=dict)
    
    # Signal counts
    signal_counts: Dict[str, int] = Field(default_factory=dict)
    
    # Time range
    first_signal_at: Optional[datetime] = None
    last_signal_at: Optional[datetime] = None
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.3)
    
    # Updated
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# SERVICE
# =============================================================================

class SignalAggregationService:
    """
    Service for aggregating signals across sources.
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        
        # Register processors
        self.processors: Dict[SignalCategory, SignalProcessor] = {
            SignalCategory.AUDIO_LISTENING: iHeartSignalProcessor(),
            SignalCategory.AUDIO_SKIP: iHeartSignalProcessor(),
            SignalCategory.AD_INTERACTION: iHeartSignalProcessor(),
            SignalCategory.BEHAVIORAL: WebSignalProcessor(),
        }
        
        # In-memory buffer for windowing
        self._signal_buffer: Dict[str, List[ProcessedSignal]] = {}
    
    async def process_signal(
        self,
        raw_signal: RawSignal,
    ) -> List[ProcessedSignal]:
        """Process a single raw signal."""
        
        processor = self.processors.get(raw_signal.category)
        if not processor:
            logger.warning(f"No processor for category {raw_signal.category}")
            return []
        
        try:
            processed = await processor.process(raw_signal)
            
            # Buffer for aggregation
            for signal in processed:
                await self._buffer_signal(signal)
            
            return processed
        
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return []
    
    async def _buffer_signal(self, signal: ProcessedSignal) -> None:
        """Buffer signal for windowed aggregation."""
        if signal.user_id not in self._signal_buffer:
            self._signal_buffer[signal.user_id] = []
        
        self._signal_buffer[signal.user_id].append(signal)
        
        # Keep buffer bounded
        if len(self._signal_buffer[signal.user_id]) > 1000:
            self._signal_buffer[signal.user_id] = \
                self._signal_buffer[signal.user_id][-500:]
    
    async def get_user_profile(
        self,
        user_id: str,
    ) -> UserSignalProfile:
        """Get aggregated signal profile for a user."""
        
        # Check cache first
        if self.cache:
            cached = await self.cache.get(f"signal_profile:{user_id}")
            if cached:
                return UserSignalProfile(**cached)
        
        # Aggregate from buffer
        signals = self._signal_buffer.get(user_id, [])
        
        if not signals:
            return UserSignalProfile(user_id=user_id)
        
        # Aggregate features
        behavioral = {}
        psychological = {}
        counts = {}
        
        for signal in signals:
            # Aggregate features with exponential decay
            for feat, value in signal.features.items():
                if feat not in behavioral:
                    behavioral[feat] = []
                behavioral[feat].append(value)
            
            for indicator, value in signal.psychological_indicators.items():
                if indicator not in psychological:
                    psychological[indicator] = []
                psychological[indicator].append(value)
            
            cat = signal.category.value
            counts[cat] = counts.get(cat, 0) + 1
        
        # Average features
        aggregated_behavioral = {
            k: sum(v) / len(v) for k, v in behavioral.items()
        }
        aggregated_psychological = {
            k: sum(v) / len(v) for k, v in psychological.items()
        }
        
        profile = UserSignalProfile(
            user_id=user_id,
            behavioral_features=aggregated_behavioral,
            psychological_indicators=aggregated_psychological,
            signal_counts=counts,
            first_signal_at=signals[0].timestamp if signals else None,
            last_signal_at=signals[-1].timestamp if signals else None,
            overall_confidence=min(0.8, 0.3 + len(signals) * 0.01),
        )
        
        # Cache
        if self.cache:
            await self.cache.set(
                f"signal_profile:{user_id}",
                profile.model_dump(),
                ttl=3600,
            )
        
        return profile
    
    async def create_window(
        self,
        user_id: str,
        window_minutes: int = 30,
    ) -> Optional[SignalWindow]:
        """Create a time window of signals."""
        
        signals = self._signal_buffer.get(user_id, [])
        if not signals:
            return None
        
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=window_minutes)
        
        # Filter to window
        window_signals = [
            s for s in signals if s.timestamp >= cutoff
        ]
        
        if not window_signals:
            return None
        
        # Aggregate
        features = {}
        for signal in window_signals:
            for feat, value in signal.features.items():
                if feat not in features:
                    features[feat] = []
                features[feat].append(value)
        
        aggregated = {k: sum(v) / len(v) for k, v in features.items()}
        
        return SignalWindow(
            window_id=f"win_{uuid4().hex[:8]}",
            user_id=user_id,
            window_start=cutoff,
            window_end=now,
            features=aggregated,
            signal_count=len(window_signals),
            completeness=min(1.0, len(window_signals) / 50),
        )
    
    async def emit_learning_signal(
        self,
        user_id: str,
        outcome: Dict[str, Any],
    ) -> None:
        """Emit learning signal for outcome attribution."""
        producer = await get_kafka_producer()
        if producer:
            await producer.send(
                ADAMTopics.SIGNALS_LEARNING,
                {
                    "user_id": user_id,
                    "outcome": outcome,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[SignalAggregationService] = None


def get_signal_aggregation_service(
    redis_cache: Optional[ADAMRedisCache] = None,
) -> SignalAggregationService:
    """Get or create the signal aggregation service singleton."""
    global _service
    
    if _service is None:
        _service = SignalAggregationService(redis_cache=redis_cache)
    
    return _service
