# =============================================================================
# ADAM Enhancement #01: Update Tier Controller
# Location: adam/graph_reasoning/update_tiers.py
# =============================================================================

"""
Update Tier Controller for Bidirectional Graph-Reasoning Fusion.

Manages graph updates across three tiers:
1. IMMEDIATE: Critical updates processed synchronously (<10ms)
2. ASYNC: Important updates processed asynchronously (<100ms)
3. BATCH: Bulk updates processed periodically (batch window)

This ensures consistent graph state while maintaining low latency
for critical operations.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from pydantic import BaseModel, Field
import asyncio
import logging
import uuid
from collections import deque

logger = logging.getLogger(__name__)


class UpdateTier(str, Enum):
    """Update processing tier."""
    IMMEDIATE = "immediate"  # Sync, <10ms, critical updates
    ASYNC = "async"          # Async, <100ms, important updates
    BATCH = "batch"          # Periodic, bulk updates


class UpdatePriority(str, Enum):
    """Priority within a tier."""
    CRITICAL = "critical"    # Must process immediately
    HIGH = "high"            # Should process soon
    NORMAL = "normal"        # Standard processing
    LOW = "low"              # Can be delayed


class UpdateCategory(str, Enum):
    """Category of graph update for routing."""
    USER_INTERACTION = "user_interaction"      # User clicked/converted
    PSYCHOLOGICAL_INFERENCE = "psychological_inference"  # Trait inference
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"  # Learning signal
    DECISION_OUTCOME = "decision_outcome"      # Decision result
    CONTENT_UPDATE = "content_update"          # Content metadata
    RELATIONSHIP_UPDATE = "relationship_update"  # Graph relationships
    AGGREGATION_UPDATE = "aggregation_update"  # Aggregate metrics
    MAINTENANCE = "maintenance"                 # System maintenance


class GraphUpdate(BaseModel):
    """A single graph update request."""
    
    update_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: UpdateCategory
    operation: str  # "create", "update", "delete", "merge"
    
    # Target
    target_node_type: Optional[str] = None
    target_node_id: Optional[str] = None
    target_relationship_type: Optional[str] = None
    
    # Payload
    properties: Dict[str, Any] = Field(default_factory=dict)
    cypher_query: Optional[str] = None
    cypher_params: Dict[str, Any] = Field(default_factory=dict)
    
    # Routing
    tier: UpdateTier = UpdateTier.ASYNC
    priority: UpdatePriority = UpdatePriority.NORMAL
    
    # Metadata
    source_component: str = "unknown"
    decision_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline_ms: Optional[float] = None
    
    # State
    processed: bool = False
    processed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0


# =============================================================================
# UPDATE ROUTING RULES
# =============================================================================

# Maps category + properties to appropriate tier
UPDATE_ROUTING_RULES: Dict[UpdateCategory, Dict[str, UpdateTier]] = {
    UpdateCategory.USER_INTERACTION: {
        "default": UpdateTier.IMMEDIATE,  # User interactions are critical
    },
    UpdateCategory.PSYCHOLOGICAL_INFERENCE: {
        "high_confidence": UpdateTier.IMMEDIATE,
        "default": UpdateTier.ASYNC,
    },
    UpdateCategory.MECHANISM_EFFECTIVENESS: {
        "learning_signal": UpdateTier.IMMEDIATE,
        "default": UpdateTier.ASYNC,
    },
    UpdateCategory.DECISION_OUTCOME: {
        "conversion": UpdateTier.IMMEDIATE,
        "default": UpdateTier.ASYNC,
    },
    UpdateCategory.CONTENT_UPDATE: {
        "default": UpdateTier.BATCH,
    },
    UpdateCategory.RELATIONSHIP_UPDATE: {
        "critical": UpdateTier.IMMEDIATE,
        "default": UpdateTier.ASYNC,
    },
    UpdateCategory.AGGREGATION_UPDATE: {
        "default": UpdateTier.BATCH,
    },
    UpdateCategory.MAINTENANCE: {
        "default": UpdateTier.BATCH,
    },
}


class UpdateTierController:
    """
    Controller for routing and processing graph updates across tiers.
    
    Maintains queues for each tier and handles:
    - Tier classification based on update category
    - Priority queuing within tiers
    - Batch aggregation
    - Error handling and retry
    """
    
    def __init__(
        self,
        immediate_handler: Optional[Callable[[GraphUpdate], Awaitable[bool]]] = None,
        async_handler: Optional[Callable[[GraphUpdate], Awaitable[bool]]] = None,
        batch_handler: Optional[Callable[[List[GraphUpdate]], Awaitable[int]]] = None,
        batch_window_seconds: float = 5.0,
        max_batch_size: int = 100,
        max_retries: int = 3,
    ):
        self.immediate_handler = immediate_handler or self._default_handler
        self.async_handler = async_handler or self._default_handler
        self.batch_handler = batch_handler or self._default_batch_handler
        
        self.batch_window = batch_window_seconds
        self.max_batch_size = max_batch_size
        self.max_retries = max_retries
        
        # Queues
        self._async_queue: asyncio.Queue = asyncio.Queue()
        self._batch_queue: deque = deque()
        
        # Statistics
        self._immediate_count = 0
        self._async_count = 0
        self._batch_count = 0
        self._error_count = 0
        
        # State
        self._batch_processor_running = False
        self._async_processor_running = False
    
    def classify_tier(self, update: GraphUpdate) -> UpdateTier:
        """Classify update to appropriate tier."""
        rules = UPDATE_ROUTING_RULES.get(update.category, {})
        
        # Check for explicit priority override
        if update.priority == UpdatePriority.CRITICAL:
            return UpdateTier.IMMEDIATE
        
        # Check category-specific rules
        for key, tier in rules.items():
            if key == "default":
                continue
            if key in update.properties:
                return tier
        
        # Return default for category
        return rules.get("default", UpdateTier.ASYNC)
    
    async def submit(self, update: GraphUpdate) -> bool:
        """
        Submit an update for processing.
        
        Routes to appropriate tier and handles processing.
        Returns True if successfully queued/processed.
        """
        # Classify if not explicitly set
        if update.tier == UpdateTier.ASYNC:  # Default, may need classification
            update.tier = self.classify_tier(update)
        
        try:
            if update.tier == UpdateTier.IMMEDIATE:
                return await self._process_immediate(update)
            
            elif update.tier == UpdateTier.ASYNC:
                await self._async_queue.put(update)
                return True
            
            else:  # BATCH
                self._batch_queue.append(update)
                return True
                
        except Exception as e:
            logger.error(f"Error submitting update {update.update_id}: {e}")
            self._error_count += 1
            return False
    
    async def _process_immediate(self, update: GraphUpdate) -> bool:
        """Process immediate tier update synchronously."""
        try:
            success = await self.immediate_handler(update)
            if success:
                update.processed = True
                update.processed_at = datetime.utcnow()
                self._immediate_count += 1
            return success
        except Exception as e:
            logger.error(f"Immediate update {update.update_id} failed: {e}")
            update.error = str(e)
            self._error_count += 1
            return False
    
    async def start_async_processor(self) -> None:
        """Start the async queue processor."""
        if self._async_processor_running:
            return
        
        self._async_processor_running = True
        logger.info("Starting async update processor")
        
        while self._async_processor_running:
            try:
                update = await asyncio.wait_for(
                    self._async_queue.get(),
                    timeout=1.0
                )
                
                success = await self.async_handler(update)
                if success:
                    update.processed = True
                    update.processed_at = datetime.utcnow()
                    self._async_count += 1
                else:
                    # Retry logic
                    update.retry_count += 1
                    if update.retry_count < self.max_retries:
                        await self._async_queue.put(update)
                    else:
                        logger.error(
                            f"Async update {update.update_id} failed after "
                            f"{self.max_retries} retries"
                        )
                        self._error_count += 1
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in async processor: {e}")
    
    async def start_batch_processor(self) -> None:
        """Start the batch queue processor."""
        if self._batch_processor_running:
            return
        
        self._batch_processor_running = True
        logger.info("Starting batch update processor")
        
        while self._batch_processor_running:
            await asyncio.sleep(self.batch_window)
            
            if not self._batch_queue:
                continue
            
            # Collect batch
            batch = []
            while self._batch_queue and len(batch) < self.max_batch_size:
                batch.append(self._batch_queue.popleft())
            
            if batch:
                try:
                    processed = await self.batch_handler(batch)
                    self._batch_count += processed
                    
                    for update in batch[:processed]:
                        update.processed = True
                        update.processed_at = datetime.utcnow()
                        
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    self._error_count += len(batch)
    
    async def stop_processors(self) -> None:
        """Stop all background processors."""
        self._async_processor_running = False
        self._batch_processor_running = False
    
    async def _default_handler(self, update: GraphUpdate) -> bool:
        """Default handler that logs update (for testing)."""
        logger.debug(
            f"Processing update: {update.category.value} "
            f"on {update.target_node_type}"
        )
        return True
    
    async def _default_batch_handler(self, updates: List[GraphUpdate]) -> int:
        """Default batch handler (for testing)."""
        logger.debug(f"Processing batch of {len(updates)} updates")
        return len(updates)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "immediate_processed": self._immediate_count,
            "async_processed": self._async_count,
            "batch_processed": self._batch_count,
            "errors": self._error_count,
            "async_queue_size": self._async_queue.qsize(),
            "batch_queue_size": len(self._batch_queue),
        }
    
    def get_queue_depths(self) -> Dict[str, int]:
        """Get current queue depths."""
        return {
            "async": self._async_queue.qsize(),
            "batch": len(self._batch_queue),
        }


# Singleton instance
_controller: Optional[UpdateTierController] = None


def get_update_tier_controller() -> UpdateTierController:
    """Get singleton Update Tier Controller."""
    global _controller
    if _controller is None:
        _controller = UpdateTierController()
    return _controller
