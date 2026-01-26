# =============================================================================
# ADAM Enhancement #19: UID2 Connector
# Location: adam/identity/partners/uid2.py
# =============================================================================

"""
Unified ID 2.0 (UID2) connector.

UID2 provides:
- Deterministic matching from email/phone
- Privacy-conscious design (user opt-out)
- Cross-platform identity resolution
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
import base64
import logging
import time

from .base import PartnerConnector, PartnerConfig, PartnerSyncResult
from adam.identity.models.identifiers import Identifier, IdentifierType

logger = logging.getLogger(__name__)


class UID2Config(PartnerConfig):
    """UID2-specific configuration."""
    
    partner_id: str = "uid2"
    api_base_url: str = "https://prod.uidapi.com"
    
    # UID2 specific
    operator_key: Optional[str] = None
    client_key: Optional[str] = None
    client_secret: Optional[str] = None
    
    # Token refresh
    token_refresh_seconds: int = 3600


class UID2Connector(PartnerConnector):
    """
    Connector for Unified ID 2.0.
    
    UID2 tokens are generated from:
    - Normalized, hashed email addresses
    - Normalized, hashed phone numbers
    
    Tokens refresh periodically and respect user opt-outs.
    """
    
    def __init__(self, config: Optional[UID2Config] = None):
        config = config or UID2Config()
        super().__init__(config)
        
        # Token cache
        self._token_cache: Dict[str, tuple] = {}  # hash -> (token, expiry)
    
    async def lookup(
        self,
        identifiers: List[Identifier]
    ) -> Optional[str]:
        """
        Lookup UID2 token for identifiers.
        
        Tries email first, then phone.
        """
        self._lookups += 1
        
        # Find email or phone hash
        email_hash = None
        phone_hash = None
        
        for id in identifiers:
            if id.identifier_type == IdentifierType.EMAIL_HASH:
                email_hash = id.identifier_value
                break
            elif id.identifier_type == IdentifierType.PHONE_HASH:
                phone_hash = id.identifier_value
        
        if not email_hash and not phone_hash:
            return None
        
        # Check cache
        cache_key = email_hash or phone_hash
        if cache_key in self._token_cache:
            token, expiry = self._token_cache[cache_key]
            if expiry > datetime.utcnow():
                self._matches += 1
                return token
        
        # In production, would call UID2 API
        # For now, simulate token generation
        token = self._simulate_token_generation(cache_key)
        
        if token:
            self._matches += 1
            # Cache for refresh period
            from datetime import timedelta
            expiry = datetime.utcnow() + timedelta(
                seconds=self.config.token_refresh_seconds
            )
            self._token_cache[cache_key] = (token, expiry)
        
        return token
    
    async def batch_lookup(
        self,
        identifier_batches: List[List[Identifier]]
    ) -> List[Optional[str]]:
        """Batch lookup UID2 tokens."""
        results = []
        for batch in identifier_batches:
            token = await self.lookup(batch)
            results.append(token)
        return results
    
    async def sync(
        self,
        our_identity_id: str,
        partner_id: str,
        identifiers: List[Identifier]
    ) -> PartnerSyncResult:
        """Sync identity with UID2."""
        self._syncs += 1
        start_time = time.time()
        
        try:
            # Lookup token
            token = await self.lookup(identifiers)
            
            latency = (time.time() - start_time) * 1000
            
            if token:
                return PartnerSyncResult(
                    partner_id=self.partner_id,
                    operation="sync",
                    success=True,
                    identifiers_sent=len(identifiers),
                    identifiers_matched=1,
                    identifiers_received=1,
                    match_rate=1.0,
                    latency_ms=latency,
                )
            else:
                return PartnerSyncResult(
                    partner_id=self.partner_id,
                    operation="sync",
                    success=True,
                    identifiers_sent=len(identifiers),
                    identifiers_matched=0,
                    identifiers_received=0,
                    match_rate=0.0,
                    latency_ms=latency,
                )
                
        except Exception as e:
            self._errors += 1
            return PartnerSyncResult(
                partner_id=self.partner_id,
                operation="sync",
                success=False,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def health_check(self) -> bool:
        """Check UID2 API health."""
        # In production, would ping API
        return True
    
    def get_identifier_type(self) -> IdentifierType:
        """UID2 identifier type."""
        return IdentifierType.UID2
    
    def _simulate_token_generation(self, input_hash: str) -> Optional[str]:
        """
        Simulate UID2 token generation.
        
        In production, this would call the UID2 API.
        """
        # Create a deterministic but fake UID2 token
        token_base = hashlib.sha256(
            f"uid2_{input_hash}".encode()
        ).digest()
        
        return f"UID2_{base64.urlsafe_b64encode(token_base[:16]).decode()}"
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email for UID2."""
        email = email.lower().strip()
        
        # Remove dots from gmail
        if "@gmail.com" in email:
            local, domain = email.split("@")
            local = local.replace(".", "")
            email = f"{local}@{domain}"
        
        return email
    
    @staticmethod
    def hash_email(email: str) -> str:
        """Hash email for UID2."""
        normalized = UID2Connector.normalize_email(email)
        return hashlib.sha256(normalized.encode()).hexdigest()


# Singleton instance
_connector: Optional[UID2Connector] = None


def get_uid2_connector(config: Optional[UID2Config] = None) -> UID2Connector:
    """Get singleton UID2 connector."""
    global _connector
    if _connector is None:
        _connector = UID2Connector(config)
    return _connector
