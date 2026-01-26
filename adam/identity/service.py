# =============================================================================
# ADAM Enhancement #19: Identity Resolution Service
# Location: adam/identity/service.py
# =============================================================================

"""
Main Identity Resolution Service.

Orchestrates cross-platform identity resolution:
1. Deterministic matching (email, phone, login)
2. Probabilistic matching (behavioral, fingerprint)
3. Household resolution
4. Industry ID sync (UID2, RampID)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import time
import uuid

from adam.identity.models.identifiers import (
    Identifier, IdentifierType, IdentifierSource, MatchConfidence
)
from adam.identity.models.identity import UnifiedIdentity, MatchResult
from adam.identity.models.household import Household, HouseholdMember

from adam.identity.matching.deterministic import DeterministicMatcher
from adam.identity.matching.probabilistic import ProbabilisticMatcher, MatchFeatures

logger = logging.getLogger(__name__)


class IdentityResolver:
    """
    Main Identity Resolution Service.
    
    Resolves incoming identifiers to unified identities using:
    1. Deterministic matching (exact email/phone/login)
    2. Probabilistic matching (behavioral signals)
    3. Identity creation for new users
    4. Household assignment
    
    Expected performance:
    - Resolution latency: <20ms p99
    - Match rate: 65-75% for returning users
    - False positive rate: <0.1%
    """
    
    def __init__(
        self,
        deterministic_matcher: Optional[DeterministicMatcher] = None,
        probabilistic_matcher: Optional[ProbabilisticMatcher] = None,
    ):
        self.deterministic = deterministic_matcher or DeterministicMatcher()
        self.probabilistic = probabilistic_matcher or ProbabilisticMatcher()
        
        # In-memory stores (production uses Neo4j)
        self._identities: Dict[str, UnifiedIdentity] = {}
        self._households: Dict[str, Household] = {}
        
        # Statistics
        self._resolutions: int = 0
        self._deterministic_matches: int = 0
        self._probabilistic_matches: int = 0
        self._new_identities: int = 0
    
    async def resolve(
        self,
        identifiers: List[Identifier],
        context: Optional[Dict[str, Any]] = None,
        create_if_new: bool = True,
    ) -> MatchResult:
        """
        Resolve identifiers to a unified identity.
        
        Args:
            identifiers: List of identifiers to resolve
            context: Additional context (location, device, behavior)
            create_if_new: Create new identity if no match found
            
        Returns:
            MatchResult with matched/created identity
        """
        start_time = time.time()
        self._resolutions += 1
        context = context or {}
        
        result = MatchResult(
            query_identifiers=identifiers,
            query_context=context,
        )
        
        # Step 1: Try deterministic matching
        identity, link = self.deterministic.find_match(identifiers)
        
        if identity:
            self._deterministic_matches += 1
            result.matched_identity = identity
            result.match_confidence = "deterministic"
            result.match_score = 1.0
            result.match_type = "deterministic"
            result.match_signals = link.match_signals if link else []
            result.match_algorithm = "deterministic"
            
            # Update identity with new identifiers
            self._update_identity_with_identifiers(identity, identifiers)
            
            result.resolution_time_ms = (time.time() - start_time) * 1000
            return result
        
        # Step 2: Try probabilistic matching
        candidates = self._get_probabilistic_candidates(identifiers, context)
        result.candidates_evaluated = len(candidates)
        
        if candidates:
            identity, link, score = self.probabilistic.find_match(
                identifiers, candidates, context
            )
            
            if identity and link:
                self._probabilistic_matches += 1
                result.matched_identity = identity
                result.match_confidence = link.confidence.value
                result.match_score = score
                result.match_type = "probabilistic"
                result.match_signals = link.match_signals
                result.match_algorithm = link.match_algorithm
                
                # Update identity
                self._update_identity_with_identifiers(identity, identifiers)
                
                result.resolution_time_ms = (time.time() - start_time) * 1000
                return result
        
        # Step 3: Create new identity if requested
        if create_if_new:
            identity = self._create_identity(identifiers)
            self._new_identities += 1
            
            result.matched_identity = identity
            result.match_confidence = "insufficient"
            result.match_score = 0.0
            result.match_type = "new"
            result.new_identity_created = True
            result.match_algorithm = "identity_creation"
        else:
            result.match_type = "anonymous"
        
        result.resolution_time_ms = (time.time() - start_time) * 1000
        return result
    
    def _get_probabilistic_candidates(
        self,
        identifiers: List[Identifier],
        context: Dict[str, Any]
    ) -> List[UnifiedIdentity]:
        """Get candidate identities for probabilistic matching."""
        candidates = []
        
        # Use IP-based lookup for candidates
        for identifier in identifiers:
            if identifier.identifier_type == IdentifierType.IP_HASH:
                # Find identities with same IP
                for identity in self._identities.values():
                    if identifier.identifier_value in identity.get_all_identifier_values(
                        IdentifierType.IP_HASH
                    ):
                        candidates.append(identity)
        
        # Limit candidates for performance
        return candidates[:100]
    
    def _create_identity(
        self,
        identifiers: List[Identifier]
    ) -> UnifiedIdentity:
        """Create new unified identity from identifiers."""
        identity = UnifiedIdentity(
            identity_id=f"uid_{uuid.uuid4().hex[:16]}"
        )
        
        for identifier in identifiers:
            identity.add_identifier(identifier)
        
        # Set primary identifier
        for priority_type in [
            IdentifierType.EMAIL_HASH,
            IdentifierType.PHONE_HASH,
            IdentifierType.LOGIN_ID,
            IdentifierType.DEVICE_ID,
        ]:
            primary = identity.get_identifier(priority_type)
            if primary:
                identity.primary_identifier_type = priority_type
                identity.primary_identifier_value = primary.identifier_value
                break
        
        # Store identity
        self._identities[identity.identity_id] = identity
        self.deterministic.register_identity(identity)
        
        logger.info(
            f"Created identity {identity.identity_id} with "
            f"{identity.total_identifiers} identifiers"
        )
        
        return identity
    
    def _update_identity_with_identifiers(
        self,
        identity: UnifiedIdentity,
        identifiers: List[Identifier]
    ) -> None:
        """Update existing identity with new identifiers."""
        for identifier in identifiers:
            identity.add_identifier(identifier)
        
        identity.last_updated = datetime.utcnow()
    
    async def link_identities(
        self,
        identity_id_1: str,
        identity_id_2: str,
        confidence: float = 0.95,
    ) -> Optional[UnifiedIdentity]:
        """
        Merge two identities into one.
        
        Used when deterministic signal connects previously separate identities.
        """
        identity_1 = self._identities.get(identity_id_1)
        identity_2 = self._identities.get(identity_id_2)
        
        if not identity_1 or not identity_2:
            return None
        
        # Merge into identity with more data
        if identity_1.total_identifiers >= identity_2.total_identifiers:
            primary, secondary = identity_1, identity_2
        else:
            primary, secondary = identity_2, identity_1
        
        # Copy identifiers
        for type_key, identifiers in secondary.identifiers.items():
            for identifier in identifiers:
                primary.add_identifier(identifier)
        
        # Update links
        primary.links.extend(secondary.links)
        primary.deterministic_links += secondary.deterministic_links
        primary.probabilistic_links += secondary.probabilistic_links
        
        # Track merge
        primary.merge_history.append(secondary.identity_id)
        primary.last_updated = datetime.utcnow()
        
        # Remove secondary
        del self._identities[secondary.identity_id]
        
        # Re-register primary
        self.deterministic.register_identity(primary)
        
        logger.info(
            f"Merged identity {secondary.identity_id} into {primary.identity_id}"
        )
        
        return primary
    
    async def get_identity(
        self,
        identity_id: str
    ) -> Optional[UnifiedIdentity]:
        """Get identity by ID."""
        return self._identities.get(identity_id)
    
    async def assign_household(
        self,
        identity_id: str,
        household_id: str,
        role: str = "unknown",
        confidence: float = 0.6
    ) -> Optional[HouseholdMember]:
        """Assign identity to a household."""
        identity = self._identities.get(identity_id)
        if not identity:
            return None
        
        household = self._households.get(household_id)
        if not household:
            household = Household(household_id=household_id)
            self._households[household_id] = household
        
        member = household.add_member(
            identity_id=identity_id,
            confidence=confidence,
            signals=["manual_assignment"],
            role=role
        )
        
        identity.household_id = household_id
        identity.household_role = role
        
        return member
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get resolution statistics."""
        total = self._resolutions
        return {
            "total_resolutions": total,
            "deterministic_matches": self._deterministic_matches,
            "probabilistic_matches": self._probabilistic_matches,
            "new_identities": self._new_identities,
            "match_rate": (
                (self._deterministic_matches + self._probabilistic_matches) / max(1, total)
            ),
            "deterministic_rate": self._deterministic_matches / max(1, total),
            "active_identities": len(self._identities),
            "active_households": len(self._households),
        }


# Singleton instance
_resolver: Optional[IdentityResolver] = None


def get_identity_resolver() -> IdentityResolver:
    """Get singleton Identity Resolver."""
    global _resolver
    if _resolver is None:
        _resolver = IdentityResolver()
    return _resolver
