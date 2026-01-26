# =============================================================================
# ADAM Enhancement #19: Household Resolution
# Location: adam/identity/household/resolver.py
# =============================================================================

"""
Household resolution engine.

Detects and links identities belonging to the same household using:
- Shared IP addresses
- Same postal/address hash
- WiFi SSID signals
- Activity pattern overlap
- Different device types (suggesting multiple people)
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import logging
import uuid

from adam.identity.models.identifiers import Identifier, IdentifierType
from adam.identity.models.identity import UnifiedIdentity
from adam.identity.models.household import (
    Household, HouseholdMember, HouseholdSignals
)

logger = logging.getLogger(__name__)


class HouseholdResolver:
    """
    Resolves household membership for identities.
    
    Uses multiple signals to determine if identities belong to
    the same household (physical residence).
    """
    
    def __init__(
        self,
        min_confidence_threshold: float = 0.6,
        ip_overlap_window_days: int = 30,
        max_household_size: int = 10,
    ):
        self.min_confidence = min_confidence_threshold
        self.ip_window = timedelta(days=ip_overlap_window_days)
        self.max_household_size = max_household_size
        
        # In-memory stores (production uses Neo4j)
        self.households: Dict[str, Household] = {}
        self.identity_to_household: Dict[str, str] = {}
        
        # IP-based lookup for candidate finding
        self.ip_to_identities: Dict[str, Set[str]] = {}
        
        # Statistics
        self._households_created = 0
        self._members_assigned = 0
    
    def compute_household_signals(
        self,
        identity1: UnifiedIdentity,
        identity2: UnifiedIdentity,
        context: Optional[Dict] = None
    ) -> HouseholdSignals:
        """
        Compute household signals between two identities.
        """
        context = context or {}
        signals = HouseholdSignals()
        
        # Check IP overlap
        ips1 = set(identity1.get_all_identifier_values(IdentifierType.IP_HASH))
        ips2 = set(identity2.get_all_identifier_values(IdentifierType.IP_HASH))
        shared_ips = ips1 & ips2
        signals.shared_ip_count = len(shared_ips)
        
        # Check postal code
        postal1 = identity1.get_all_identifier_values(IdentifierType.POSTAL_HASH)
        postal2 = identity2.get_all_identifier_values(IdentifierType.POSTAL_HASH)
        if postal1 and postal2:
            signals.same_postal_code = bool(set(postal1) & set(postal2))
        
        # Check for different device types (suggests different people)
        devices1 = set()
        devices2 = set()
        
        for id_type in [IdentifierType.DEVICE_ID, IdentifierType.COOKIE_ID]:
            if identity1.get_identifier(id_type):
                devices1.add(id_type.value)
            if identity2.get_identifier(id_type):
                devices2.add(id_type.value)
        
        signals.different_device_types = len(devices1 | devices2) > 1
        
        # Activity overlap from context
        if "activity_overlap" in context:
            signals.activity_overlap_score = context["activity_overlap"]
        
        # WiFi SSID from context
        if context.get("shared_wifi"):
            signals.shared_wifi_ssid = True
        
        # Address hash from context
        if context.get("same_address"):
            signals.same_address_hash = True
        
        # Compute probability
        signals.compute_probability()
        
        return signals
    
    def find_household_candidates(
        self,
        identity: UnifiedIdentity,
        all_identities: List[UnifiedIdentity]
    ) -> List[Tuple[UnifiedIdentity, HouseholdSignals]]:
        """
        Find potential household members for an identity.
        """
        candidates = []
        
        # Get identity's IPs
        identity_ips = set(
            identity.get_all_identifier_values(IdentifierType.IP_HASH)
        )
        
        for other in all_identities:
            if other.identity_id == identity.identity_id:
                continue
            
            signals = self.compute_household_signals(identity, other)
            
            if signals.household_probability >= self.min_confidence:
                candidates.append((other, signals))
        
        # Sort by probability
        candidates.sort(key=lambda x: x[1].household_probability, reverse=True)
        
        return candidates
    
    def resolve_household(
        self,
        identity: UnifiedIdentity,
        candidates: Optional[List[Tuple[UnifiedIdentity, HouseholdSignals]]] = None
    ) -> Optional[Household]:
        """
        Resolve household for an identity.
        
        Either joins existing household or creates new one.
        """
        # Check if already in a household
        if identity.identity_id in self.identity_to_household:
            household_id = self.identity_to_household[identity.identity_id]
            return self.households.get(household_id)
        
        # Check if any candidate is in a household
        if candidates:
            for candidate, signals in candidates:
                if candidate.identity_id in self.identity_to_household:
                    # Join existing household
                    household_id = self.identity_to_household[candidate.identity_id]
                    household = self.households[household_id]
                    
                    if household.member_count < self.max_household_size:
                        self._add_to_household(
                            identity, 
                            household, 
                            signals.household_probability
                        )
                        return household
        
        # Create new household if we have strong candidates
        if candidates:
            best_candidate, best_signals = candidates[0]
            
            if best_signals.household_probability >= self.min_confidence:
                household = self._create_household(
                    [identity, best_candidate],
                    best_signals
                )
                return household
        
        return None
    
    def _create_household(
        self,
        identities: List[UnifiedIdentity],
        signals: HouseholdSignals
    ) -> Household:
        """Create a new household with initial members."""
        household = Household(
            household_id=f"hh_{uuid.uuid4().hex[:12]}",
            overall_confidence=signals.household_probability,
            estimated_size=len(identities),
        )
        
        # Add members
        for i, identity in enumerate(identities):
            role = "primary" if i == 0 else "secondary"
            member = household.add_member(
                identity_id=identity.identity_id,
                confidence=signals.household_probability,
                signals=self._signals_to_list(signals),
                role=role
            )
            
            self.identity_to_household[identity.identity_id] = household.household_id
            self._members_assigned += 1
        
        if identities:
            household.primary_member_id = identities[0].identity_id
        
        self.households[household.household_id] = household
        self._households_created += 1
        
        logger.info(
            f"Created household {household.household_id} with "
            f"{len(identities)} members"
        )
        
        return household
    
    def _add_to_household(
        self,
        identity: UnifiedIdentity,
        household: Household,
        confidence: float
    ) -> HouseholdMember:
        """Add identity to existing household."""
        role = "secondary"
        if household.member_count >= 2:
            role = "unknown"
        
        member = household.add_member(
            identity_id=identity.identity_id,
            confidence=confidence,
            signals=["joined_existing"],
            role=role
        )
        
        self.identity_to_household[identity.identity_id] = household.household_id
        self._members_assigned += 1
        
        return member
    
    def _signals_to_list(self, signals: HouseholdSignals) -> List[str]:
        """Convert signals to list of string descriptions."""
        result = []
        if signals.shared_ip_count > 0:
            result.append(f"shared_ip_{signals.shared_ip_count}")
        if signals.shared_wifi_ssid:
            result.append("shared_wifi")
        if signals.same_postal_code:
            result.append("same_postal")
        if signals.same_address_hash:
            result.append("same_address")
        if signals.different_device_types:
            result.append("different_devices")
        return result
    
    def get_household(self, household_id: str) -> Optional[Household]:
        """Get household by ID."""
        return self.households.get(household_id)
    
    def get_identity_household(
        self, 
        identity_id: str
    ) -> Optional[Household]:
        """Get household for an identity."""
        if identity_id in self.identity_to_household:
            return self.households.get(
                self.identity_to_household[identity_id]
            )
        return None
    
    def get_household_members(
        self,
        household_id: str
    ) -> List[str]:
        """Get all identity IDs in a household."""
        household = self.households.get(household_id)
        if not household:
            return []
        return [m.identity_id for m in household.members]
    
    def infer_member_role(
        self,
        identity: UnifiedIdentity,
        household: Household
    ) -> str:
        """
        Infer the role of a member in the household.
        
        Uses behavioral signals and demographics.
        """
        # Simple heuristics (production would use ML)
        if household.primary_member_id == identity.identity_id:
            return "primary"
        
        # Check activity level
        total_interactions = 0
        for type_key, identifiers in identity.identifiers.items():
            for id in identifiers:
                total_interactions += getattr(id, 'observation_count', 1)
        
        # High activity = likely primary
        if total_interactions > 50:
            return "primary"
        
        # Check device types for child signals
        has_tablet = False
        has_gaming = False
        # Would check actual device metadata
        
        if has_tablet or has_gaming:
            return "child"
        
        return "secondary"
    
    def get_statistics(self) -> Dict[str, int]:
        """Get resolver statistics."""
        return {
            "households_created": self._households_created,
            "members_assigned": self._members_assigned,
            "active_households": len(self.households),
            "mapped_identities": len(self.identity_to_household),
        }


# Singleton instance
_resolver: Optional[HouseholdResolver] = None


def get_household_resolver() -> HouseholdResolver:
    """Get singleton household resolver."""
    global _resolver
    if _resolver is None:
        _resolver = HouseholdResolver()
    return _resolver
