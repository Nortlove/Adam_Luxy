# =============================================================================
# ADAM Enhancement #19: Partner Connector Base
# Location: adam/identity/partners/base.py
# =============================================================================

"""
Base class for partner identity connectors.

Partners include:
- UID2 (Unified ID 2.0)
- LiveRamp RampID
- iHeart platform
- ID5
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from adam.identity.models.identifiers import Identifier, IdentifierType

logger = logging.getLogger(__name__)


class PartnerSyncResult(BaseModel):
    """Result of a partner sync operation."""
    
    partner_id: str
    operation: str  # "lookup", "sync", "match"
    success: bool
    
    identifiers_sent: int = 0
    identifiers_matched: int = 0
    identifiers_received: int = 0
    
    match_rate: float = 0.0
    
    error_message: Optional[str] = None
    
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PartnerConfig(BaseModel):
    """Configuration for partner connector."""
    
    partner_id: str
    api_base_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    
    # Rate limiting
    requests_per_second: float = 10.0
    max_batch_size: int = 1000
    
    # Timeouts
    connect_timeout_ms: int = 5000
    read_timeout_ms: int = 30000
    
    # Features
    supports_batch: bool = True
    supports_streaming: bool = False
    supports_bloom_filter: bool = False


class PartnerConnector(ABC):
    """
    Abstract base class for partner identity connectors.
    
    Partners provide cross-platform identity resolution by:
    - Looking up their ID for our identifiers
    - Syncing identity graphs
    - Matching in clean rooms
    """
    
    def __init__(self, config: PartnerConfig):
        self.config = config
        self.partner_id = config.partner_id
        
        # Statistics
        self._lookups = 0
        self._syncs = 0
        self._matches = 0
        self._errors = 0
    
    @abstractmethod
    async def lookup(
        self,
        identifiers: List[Identifier]
    ) -> Optional[str]:
        """
        Lookup partner ID for given identifiers.
        
        Returns partner's ID if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def batch_lookup(
        self,
        identifier_batches: List[List[Identifier]]
    ) -> List[Optional[str]]:
        """
        Batch lookup partner IDs.
        
        Returns list of partner IDs (None for unmatched).
        """
        pass
    
    @abstractmethod
    async def sync(
        self,
        our_identity_id: str,
        partner_id: str,
        identifiers: List[Identifier]
    ) -> PartnerSyncResult:
        """
        Sync identity with partner.
        
        Establishes bidirectional link.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if partner API is healthy."""
        pass
    
    def get_identifier_type(self) -> IdentifierType:
        """Get the identifier type for this partner."""
        return IdentifierType.UID2  # Override in subclass
    
    def get_statistics(self) -> Dict[str, int]:
        """Get connector statistics."""
        return {
            "lookups": self._lookups,
            "syncs": self._syncs,
            "matches": self._matches,
            "errors": self._errors,
        }
