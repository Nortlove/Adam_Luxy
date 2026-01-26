# =============================================================================
# ADAM Enhancement #19: Household Models
# Location: adam/identity/models/household.py
# =============================================================================

"""
Household-level identity resolution models.

Enables:
- Household detection from shared signals
- Role inference (primary, secondary, child)
- Household-level targeting
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, computed_field
import uuid


class HouseholdSignals(BaseModel):
    """Signals used for household detection."""
    
    shared_ip_count: int = 0
    shared_wifi_ssid: bool = False
    same_postal_code: bool = False
    same_address_hash: bool = False
    activity_overlap_score: float = 0.0
    different_device_types: bool = False
    household_probability: float = 0.0
    
    def compute_probability(
        self,
        ip_weight: float = 0.30,
        wifi_weight: float = 0.25,
        address_weight: float = 0.25,
        temporal_weight: float = 0.20
    ) -> float:
        """Compute household probability from signals."""
        score = 0.0
        
        if self.shared_ip_count > 0:
            score += ip_weight * min(1.0, self.shared_ip_count / 10)
        
        if self.shared_wifi_ssid:
            score += wifi_weight
        
        if self.same_address_hash:
            score += address_weight
        elif self.same_postal_code:
            score += address_weight * 0.5
        
        score += temporal_weight * self.activity_overlap_score
        
        # Boost if different device types (suggests multiple people)
        if self.different_device_types:
            score = min(1.0, score * 1.1)
        
        self.household_probability = score
        return score


class HouseholdMember(BaseModel):
    """A member of a household."""
    
    identity_id: str
    household_id: str
    role: Literal["primary", "secondary", "child", "unknown"] = "unknown"
    role_confidence: float = 0.5
    membership_confidence: float = 0.0
    join_signals: List[str] = Field(default_factory=list)
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class Household(BaseModel):
    """A household containing multiple identities."""
    
    household_id: str = Field(
        default_factory=lambda: f"hh_{uuid.uuid4().hex[:12]}"
    )
    
    members: List[HouseholdMember] = Field(default_factory=list)
    primary_member_id: Optional[str] = None
    
    # Household characteristics
    estimated_size: int = 0
    has_children: bool = False
    
    # Location
    postal_hash: Optional[str] = None
    address_hash: Optional[str] = None
    
    # Confidence
    overall_confidence: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def add_member(
        self,
        identity_id: str,
        confidence: float,
        signals: List[str],
        role: str = "unknown"
    ) -> HouseholdMember:
        """Add a member to the household."""
        member = HouseholdMember(
            identity_id=identity_id,
            household_id=self.household_id,
            role=role,
            membership_confidence=confidence,
            join_signals=signals,
        )
        self.members.append(member)
        self.estimated_size = len(self.members)
        self.last_updated = datetime.utcnow()
        return member
    
    def get_member(self, identity_id: str) -> Optional[HouseholdMember]:
        """Get member by identity ID."""
        for member in self.members:
            if member.identity_id == identity_id:
                return member
        return None
    
    @computed_field
    @property
    def member_count(self) -> int:
        """Number of members in household."""
        return len(self.members)
    
    @computed_field
    @property
    def is_valid(self) -> bool:
        """Whether household has minimum required confidence."""
        return self.overall_confidence >= 0.6 and self.member_count >= 1
