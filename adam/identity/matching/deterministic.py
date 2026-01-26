# =============================================================================
# ADAM Enhancement #19: Deterministic Matching
# Location: adam/identity/matching/deterministic.py
# =============================================================================

"""
Deterministic identity matching.

100% confidence matches based on:
- Same email hash
- Same phone hash
- Same login ID
- Same platform ID
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from adam.identity.models.identifiers import (
    Identifier, IdentifierType, IdentityLink, MatchConfidence
)
from adam.identity.models.identity import UnifiedIdentity

logger = logging.getLogger(__name__)


class DeterministicMatcher:
    """
    Matches identities using deterministic signals.
    
    Deterministic matching provides 100% confidence when
    the same identifier value is observed across contexts.
    """
    
    # Identifier types that support deterministic matching
    DETERMINISTIC_TYPES = {
        IdentifierType.EMAIL_HASH,
        IdentifierType.PHONE_HASH,
        IdentifierType.LOGIN_ID,
        IdentifierType.CUSTOMER_ID,
        IdentifierType.CRM_ID,
        IdentifierType.IHEART_ID,
        IdentifierType.SPOTIFY_ID,
        IdentifierType.AMAZON_ID,
        IdentifierType.UID2,
        IdentifierType.RAMP_ID,
    }
    
    def __init__(self):
        # In-memory index for testing (production uses Neo4j)
        self._identifier_index: Dict[str, str] = {}  # identifier_value -> identity_id
        self._identity_store: Dict[str, UnifiedIdentity] = {}
    
    def can_match_deterministic(self, identifier: Identifier) -> bool:
        """Check if identifier type supports deterministic matching."""
        return identifier.identifier_type in self.DETERMINISTIC_TYPES
    
    def find_match(
        self,
        identifiers: List[Identifier]
    ) -> Tuple[Optional[UnifiedIdentity], Optional[IdentityLink]]:
        """
        Find deterministic match for given identifiers.
        
        Returns the first match found and the link that produced it.
        """
        for identifier in identifiers:
            if not self.can_match_deterministic(identifier):
                continue
            
            # Create lookup key
            lookup_key = self._make_lookup_key(identifier)
            
            # Check index
            if lookup_key in self._identifier_index:
                identity_id = self._identifier_index[lookup_key]
                identity = self._identity_store.get(identity_id)
                
                if identity:
                    link = IdentityLink(
                        source_identifier_id=identifier.identifier_id,
                        target_identifier_id=identity_id,
                        source_type=identifier.identifier_type,
                        target_type=identifier.identifier_type,
                        match_type="deterministic",
                        confidence=MatchConfidence.DETERMINISTIC,
                        confidence_score=1.0,
                        match_signals=[f"exact_{identifier.identifier_type.value}"],
                        match_algorithm="deterministic_lookup",
                    )
                    
                    logger.debug(
                        f"Deterministic match: {identifier.identifier_type.value} "
                        f"-> identity {identity_id}"
                    )
                    return identity, link
        
        return None, None
    
    def find_all_matches(
        self,
        identifiers: List[Identifier]
    ) -> List[Tuple[UnifiedIdentity, IdentityLink]]:
        """Find all deterministic matches across identifiers."""
        matches = []
        seen_identity_ids = set()
        
        for identifier in identifiers:
            if not self.can_match_deterministic(identifier):
                continue
            
            lookup_key = self._make_lookup_key(identifier)
            
            if lookup_key in self._identifier_index:
                identity_id = self._identifier_index[lookup_key]
                
                if identity_id not in seen_identity_ids:
                    identity = self._identity_store.get(identity_id)
                    
                    if identity:
                        link = IdentityLink(
                            source_identifier_id=identifier.identifier_id,
                            target_identifier_id=identity_id,
                            source_type=identifier.identifier_type,
                            target_type=identifier.identifier_type,
                            match_type="deterministic",
                            confidence=MatchConfidence.DETERMINISTIC,
                            confidence_score=1.0,
                            match_signals=[f"exact_{identifier.identifier_type.value}"],
                            match_algorithm="deterministic_lookup",
                        )
                        matches.append((identity, link))
                        seen_identity_ids.add(identity_id)
        
        return matches
    
    def register_identity(self, identity: UnifiedIdentity) -> None:
        """Register identity in the deterministic index."""
        self._identity_store[identity.identity_id] = identity
        
        # Index all deterministic identifiers
        for type_key, identifiers in identity.identifiers.items():
            for identifier in identifiers:
                if self.can_match_deterministic(identifier):
                    lookup_key = self._make_lookup_key(identifier)
                    self._identifier_index[lookup_key] = identity.identity_id
    
    def _make_lookup_key(self, identifier: Identifier) -> str:
        """Create lookup key for identifier."""
        return f"{identifier.identifier_type.value}:{identifier.identifier_value}"
    
    def link_identifiers(
        self,
        source: Identifier,
        target: Identifier,
        via_event: str = "login_event"
    ) -> IdentityLink:
        """Create deterministic link between identifiers observed together."""
        return IdentityLink(
            source_identifier_id=source.identifier_id,
            target_identifier_id=target.identifier_id,
            source_type=source.identifier_type,
            target_type=target.identifier_type,
            match_type="deterministic",
            confidence=MatchConfidence.DETERMINISTIC,
            confidence_score=1.0,
            match_signals=[f"co_occurrence_{via_event}"],
            match_algorithm="event_co_occurrence",
        )
