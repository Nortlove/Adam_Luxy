# ADAM Enhancement #19: Cross-Platform Identity Resolution
## Production-Ready Unified Identity System - COMPLETE SPECIFICATION

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P1 - Scale Enabler  
**Estimated Implementation**: 10 person-weeks  
**Dependencies**: #17 (Privacy & Consent), #02 (Blackboard)  
**Dependents**: #10 (Journey Tracking), #22 (Attribution), #08 (Signal Aggregation)  
**File Size**: ~75KB (Production-Ready)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Part 1: Core Data Models](#part-1-core-data-models)
3. [Part 2: Identity Graph Engine](#part-2-identity-graph-engine)
4. [Part 3: Deterministic Matching](#part-3-deterministic-matching)
5. [Part 4: Probabilistic Matching](#part-4-probabilistic-matching)
6. [Part 5: Privacy-Preserving Operations](#part-5-privacy-preserving-operations)
7. [Part 6: Household Resolution](#part-6-household-resolution)
8. [Part 7: Identity Resolution Service](#part-7-identity-resolution-service)
9. [Part 8: Partner Integrations](#part-8-partner-integrations)
10. [Part 9: Neo4j Schema & Operations](#part-9-neo4j-schema--operations)
11. [Part 10: FastAPI Endpoints](#part-10-fastapi-endpoints)
12. [Part 11: Integration & Testing](#part-11-integration--testing)
13. [Part 12: Deployment & Operations](#part-12-deployment--operations)
14. [Implementation Timeline](#implementation-timeline)
15. [Success Metrics](#success-metrics)

---

## Executive Summary

Users interact across multiple devices, apps, and platforms. Without identity resolution, ADAM sees fragmented profiles instead of unified individuals, degrading psychological profiling accuracy by **40-60%** and breaking attribution chains. This specification implements complete identity resolution infrastructure that:

1. **Links** identifiers across devices and platforms (deterministic + probabilistic)
2. **Maintains** a privacy-compliant identity graph with consent propagation
3. **Integrates** with industry standards (UID2, RampID, iHeart ID)
4. **Preserves** privacy through bloom filters and differential privacy
5. **Enables** household-level targeting with individual disambiguation
6. **Learns** from match outcomes to improve resolution accuracy

### The Identity Challenge

| Scenario | Without Resolution | With Resolution | Impact |
|----------|-------------------|-----------------|--------|
| Same user, 3 devices | 3 separate profiles | 1 unified profile | 3x data density |
| Cross-channel journey | Broken attribution | Complete journey | Accurate ROI |
| Profile confidence | Low (sparse data) | High (aggregated) | Better targeting |
| Frequency capping | Over-exposure | Proper control | User experience |
| Household targeting | Individual only | Household + individual | Expanded reach |

### Integration Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    IDENTITY RESOLUTION IN ADAM ECOSYSTEM                      │
│                                                                              │
│  Incoming        #19 Identity          #10 Journey        #22 Attribution   │
│  Signals ──────► Resolution ──────────► Tracking ─────────► Modeling        │
│      │               │                      │                    │          │
│      │               ▼                      │                    │          │
│      │      #02 BLACKBOARD                  │                    │          │
│      │      ┌─────────────────┐             │                    │          │
│      └─────►│ unified_identity │◄────────────┘                    │          │
│             │ identity_graph   │◄─────────────────────────────────┘          │
│             │ consent_status   │                                             │
│             └─────────────────┘                                              │
│                      │                                                       │
│                      ▼                                                       │
│            #17 Privacy/Consent                                               │
│            #06 Gradient Bridge (learning)                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Business Impact

| Capability | Baseline | With Identity Resolution | Evidence |
|------------|----------|--------------------------|----------|
| Cross-device recognition | 15-25% | 50-70% | Industry benchmarks |
| Profile completeness | 40% | 85% | Data density increase |
| Attribution accuracy | ±30% | ±10% | Verified attribution |
| False match rate | N/A | <1% | Quality threshold |
| Household reach expansion | 1x | 2.3x | Household graphs |

---


## Part 1: Core Data Models

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Set, Union, Literal
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, validator, root_validator
import numpy as np
import hashlib
import uuid
import json


# =============================================================================
# IDENTIFIER TYPES AND CLASSIFICATION
# =============================================================================

class IdentifierType(str, Enum):
    """
    Types of identifiers with confidence classification.
    
    Deterministic identifiers provide 100% match confidence.
    Device identifiers provide high confidence with proper handling.
    Probabilistic identifiers require ML matching.
    """
    
    # Deterministic (100% confidence when matched)
    EMAIL_HASH = "email_hash"
    PHONE_HASH = "phone_hash"
    LOGIN_ID = "login_id"
    CUSTOMER_ID = "customer_id"
    CRM_ID = "crm_id"
    
    # Device-based (high confidence with proper handling)
    DEVICE_ID = "device_id"           # Mobile IDFA/GAID
    COOKIE_ID = "cookie_id"           # Browser cookie
    FINGERPRINT = "fingerprint"       # Device fingerprint hash
    IP_HASH = "ip_hash"               # Hashed IP address
    
    # Platform-specific (deterministic within platform)
    IHEART_ID = "iheart_id"
    SPOTIFY_ID = "spotify_id"
    AMAZON_ID = "amazon_id"
    
    # Industry standard (cross-platform)
    UID2 = "uid2"                     # Unified ID 2.0
    RAMP_ID = "ramp_id"               # LiveRamp RampID
    ID5 = "id5"                       # ID5 identifier
    
    # Household-level
    HOUSEHOLD_ID = "household_id"
    POSTAL_HASH = "postal_hash"       # Hashed postal code
    
    # Transient (session-level only)
    SESSION_ID = "session_id"
    REQUEST_ID = "request_id"
    
    @property
    def is_deterministic(self) -> bool:
        """Whether this identifier type provides deterministic matches."""
        return self in {
            IdentifierType.EMAIL_HASH,
            IdentifierType.PHONE_HASH,
            IdentifierType.LOGIN_ID,
            IdentifierType.CUSTOMER_ID,
            IdentifierType.CRM_ID,
            IdentifierType.IHEART_ID,
            IdentifierType.SPOTIFY_ID,
            IdentifierType.AMAZON_ID,
        }
    
    @property
    def is_device_level(self) -> bool:
        """Whether this identifier is device-specific."""
        return self in {
            IdentifierType.DEVICE_ID,
            IdentifierType.COOKIE_ID,
            IdentifierType.FINGERPRINT,
        }
    
    @property
    def is_industry_standard(self) -> bool:
        """Whether this is an industry-standard cross-platform ID."""
        return self in {
            IdentifierType.UID2,
            IdentifierType.RAMP_ID,
            IdentifierType.ID5,
        }
    
    @property
    def persistence_days(self) -> int:
        """Expected persistence of this identifier type in days."""
        persistence_map = {
            IdentifierType.EMAIL_HASH: 3650,      # ~10 years
            IdentifierType.PHONE_HASH: 1825,      # ~5 years
            IdentifierType.LOGIN_ID: 3650,        # ~10 years
            IdentifierType.CUSTOMER_ID: 3650,     # ~10 years
            IdentifierType.DEVICE_ID: 365,        # ~1 year (reset on OS update)
            IdentifierType.COOKIE_ID: 30,         # ~1 month (ITP, browser limits)
            IdentifierType.FINGERPRINT: 90,       # ~3 months (browser changes)
            IdentifierType.IP_HASH: 7,            # ~1 week (dynamic IPs)
            IdentifierType.UID2: 365,             # ~1 year (refresh cycle)
            IdentifierType.RAMP_ID: 365,          # ~1 year
            IdentifierType.HOUSEHOLD_ID: 1095,    # ~3 years
            IdentifierType.SESSION_ID: 0,         # Session only
        }
        return persistence_map.get(self, 30)


class MatchConfidence(str, Enum):
    """Confidence levels for identity matches."""
    DETERMINISTIC = "deterministic"   # 100% certain (same email, login event)
    VERY_HIGH = "very_high"           # >98% confident (multiple strong signals)
    HIGH = "high"                     # 95-98% confident (2+ correlated signals)
    MEDIUM = "medium"                 # 80-95% confident (single strong signal)
    LOW = "low"                       # 60-80% confident (behavioral pattern)
    SPECULATIVE = "speculative"       # 50-60% confident (weak signals)
    INSUFFICIENT = "insufficient"     # <50% confident (do not use)
    
    @property
    def usable_for_targeting(self) -> bool:
        """Whether this confidence level is sufficient for ad targeting."""
        return self in {
            MatchConfidence.DETERMINISTIC,
            MatchConfidence.VERY_HIGH,
            MatchConfidence.HIGH,
            MatchConfidence.MEDIUM,
        }
    
    @classmethod
    def from_score(cls, score: float) -> 'MatchConfidence':
        """Convert numeric score to confidence level."""
        if score >= 1.0:
            return cls.DETERMINISTIC
        elif score >= 0.98:
            return cls.VERY_HIGH
        elif score >= 0.95:
            return cls.HIGH
        elif score >= 0.80:
            return cls.MEDIUM
        elif score >= 0.60:
            return cls.LOW
        elif score >= 0.50:
            return cls.SPECULATIVE
        else:
            return cls.INSUFFICIENT


class IdentifierSource(str, Enum):
    """Source of identifier observation."""
    LOGIN_EVENT = "login_event"
    REGISTRATION = "registration"
    PURCHASE = "purchase"
    PARTNER_SYNC = "partner_sync"
    SDK_COLLECTION = "sdk_collection"
    PIXEL_FIRE = "pixel_fire"
    API_CALL = "api_call"
    CLEAN_ROOM = "clean_room"
    INFERENCE = "inference"


class Identifier(BaseModel):
    """A single identifier for a user."""
    
    class Config:
        use_enum_values = True
        frozen = True
    
    identifier_type: IdentifierType
    identifier_value: str = Field(..., min_length=1, max_length=512)
    source: IdentifierSource
    source_system: str
    source_timestamp: datetime = Field(default_factory=datetime.utcnow)
    first_seen: datetime
    last_seen: datetime
    observation_count: int = Field(1, ge=1)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    verified: bool = Field(False)
    consent_for_linking: bool = Field(True)
    identifier_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    @property
    def age_days(self) -> float:
        return (datetime.utcnow() - self.first_seen).total_seconds() / 86400
    
    @property
    def recency_days(self) -> float:
        return (datetime.utcnow() - self.last_seen).total_seconds() / 86400
    
    @property
    def is_stale(self) -> bool:
        max_age = self.identifier_type.persistence_days
        return self.recency_days > max_age
    
    @property
    def effective_confidence(self) -> float:
        """Confidence adjusted for recency and verification."""
        base = self.confidence
        if self.recency_days > 0:
            decay_factor = max(0.5, 1.0 - (self.recency_days / (self.identifier_type.persistence_days * 2)))
            base *= decay_factor
        if self.verified:
            base = min(1.0, base * 1.1)
        return base


class IdentityLink(BaseModel):
    """A link between two identifiers indicating same person."""
    
    link_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_identifier_id: str
    target_identifier_id: str
    source_type: IdentifierType
    target_type: IdentifierType
    match_type: Literal["deterministic", "probabilistic"]
    confidence: MatchConfidence
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    match_signals: List[str] = Field(default_factory=list)
    match_features: Dict[str, float] = Field(default_factory=dict)
    match_algorithm: str = Field("unknown")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(True)
    
    @property
    def is_deterministic(self) -> bool:
        return self.match_type == "deterministic"


class UnifiedIdentity(BaseModel):
    """A unified identity representing one real person."""
    
    identity_id: str = Field(default_factory=lambda: f"uid_{uuid.uuid4().hex[:16]}")
    identifiers: Dict[str, List[Identifier]] = Field(default_factory=dict)
    primary_identifier_type: Optional[IdentifierType] = None
    primary_identifier_value: Optional[str] = None
    links: List[IdentityLink] = Field(default_factory=list)
    household_id: Optional[str] = None
    household_role: Optional[str] = None
    total_identifiers: int = Field(0, ge=0)
    deterministic_links: int = Field(0, ge=0)
    probabilistic_links: int = Field(0, ge=0)
    overall_confidence: float = Field(0.5, ge=0.0, le=1.0)
    known_devices: int = Field(0, ge=0)
    active_devices: int = Field(0, ge=0)
    linking_consent: bool = Field(True)
    cross_device_consent: bool = Field(True)
    profiling_consent: bool = Field(True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    merge_history: List[str] = Field(default_factory=list)
    uid2_token: Optional[str] = None
    ramp_id: Optional[str] = None
    iheart_id: Optional[str] = None
    
    def get_identifier(self, identifier_type: IdentifierType) -> Optional[Identifier]:
        type_key = identifier_type.value
        if type_key not in self.identifiers or not self.identifiers[type_key]:
            return None
        return max(self.identifiers[type_key], key=lambda x: x.effective_confidence)
    
    def get_all_identifier_values(self, identifier_type: IdentifierType) -> List[str]:
        type_key = identifier_type.value
        if type_key not in self.identifiers:
            return []
        return [id.identifier_value for id in self.identifiers[type_key]]
    
    @property
    def is_high_quality(self) -> bool:
        return (
            self.overall_confidence >= 0.75 and
            self.total_identifiers >= 2 and
            (self.deterministic_links >= 1 or self.overall_confidence >= 0.90)
        )
    
    @property
    def profile_completeness(self) -> float:
        has_email = IdentifierType.EMAIL_HASH.value in self.identifiers
        has_device = any(
            t.value in self.identifiers 
            for t in [IdentifierType.DEVICE_ID, IdentifierType.COOKIE_ID]
        )
        has_platform = any(
            t.value in self.identifiers 
            for t in [IdentifierType.IHEART_ID, IdentifierType.SPOTIFY_ID]
        )
        has_industry = any(
            t.value in self.identifiers 
            for t in [IdentifierType.UID2, IdentifierType.RAMP_ID]
        )
        score = 0.0
        if has_email: score += 0.3
        if has_device: score += 0.25
        if has_platform: score += 0.25
        if has_industry: score += 0.2
        return score


class MatchResult(BaseModel):
    """Result of a match operation."""
    
    match_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_identifiers: List[Identifier]
    query_context: Dict[str, Any] = Field(default_factory=dict)
    matched_identity: Optional[UnifiedIdentity] = None
    match_confidence: MatchConfidence = MatchConfidence.INSUFFICIENT
    match_score: float = Field(0.0, ge=0.0, le=1.0)
    new_identity_created: bool = Field(False)
    match_type: Literal["deterministic", "probabilistic", "new", "anonymous"]
    match_signals: List[str] = Field(default_factory=list)
    match_algorithm: str = Field("unknown")
    runner_up_identities: List[Tuple[str, float]] = Field(default_factory=list)
    resolution_time_ms: float = Field(0.0)
    candidates_evaluated: int = Field(0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MatchFeatures(BaseModel):
    """Feature vector for probabilistic matching."""
    
    ip_exact_match: float = Field(0.0, ge=0.0, le=1.0)
    ip_subnet_match: float = Field(0.0, ge=0.0, le=1.0)
    ip_geo_distance_km: float = Field(0.0, ge=0.0)
    fingerprint_similarity: float = Field(0.0, ge=0.0, le=1.0)
    screen_resolution_match: float = Field(0.0, ge=0.0, le=1.0)
    timezone_match: float = Field(0.0, ge=0.0, le=1.0)
    language_match: float = Field(0.0, ge=0.0, le=1.0)
    behavioral_similarity: float = Field(0.0, ge=0.0, le=1.0)
    content_preference_overlap: float = Field(0.0, ge=0.0, le=1.0)
    temporal_pattern_match: float = Field(0.0, ge=0.0, le=1.0)
    temporal_overlap_hours: float = Field(0.0, ge=0.0)
    geo_consistency: float = Field(0.0, ge=0.0, le=1.0)
    household_probability: float = Field(0.0, ge=0.0, le=1.0)
    same_wifi_probability: float = Field(0.0, ge=0.0, le=1.0)
    
    def to_vector(self) -> np.ndarray:
        return np.array([
            self.ip_exact_match, self.ip_subnet_match,
            min(1.0, self.ip_geo_distance_km / 100),
            self.fingerprint_similarity, self.screen_resolution_match,
            self.timezone_match, self.language_match,
            self.behavioral_similarity, self.content_preference_overlap,
            self.temporal_pattern_match,
            min(1.0, self.temporal_overlap_hours / 168),
            self.geo_consistency, self.household_probability,
            self.same_wifi_probability,
        ])
```

---


## Part 2: Identity Graph Engine

```python
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
import logging

logger = logging.getLogger(__name__)


class IdentityGraphConfig(BaseModel):
    """Configuration for the Identity Graph."""
    
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "adam"
    max_identifiers_per_identity: int = 100
    max_links_per_identity: int = 500
    stale_link_days: int = 90
    deterministic_confidence: float = 1.0
    probabilistic_min_confidence: float = 0.60
    merge_confidence_threshold: float = 0.95
    query_timeout_seconds: int = 30
    batch_size: int = 1000


class IdentityGraph:
    """Core identity graph operations with Neo4j."""
    
    def __init__(self, config: IdentityGraphConfig):
        self.config = config
        self._driver: Optional[AsyncDriver] = None
        
    async def connect(self) -> None:
        """Initialize Neo4j connection."""
        self._driver = AsyncGraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password),
            max_connection_pool_size=50,
        )
        async with self._driver.session(database=self.config.neo4j_database) as session:
            await session.run("RETURN 1")
        logger.info("Identity graph connected to Neo4j")
    
    async def disconnect(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None
    
    async def _get_session(self) -> AsyncSession:
        if not self._driver:
            await self.connect()
        return self._driver.session(database=self.config.neo4j_database)
    
    async def create_identity(self, identity: UnifiedIdentity) -> UnifiedIdentity:
        """Create a new unified identity in the graph."""
        async with await self._get_session() as session:
            await session.run("""
                CREATE (ui:UnifiedIdentity {
                    identity_id: $identity_id,
                    primary_identifier_type: $primary_type,
                    primary_identifier_value: $primary_value,
                    household_id: $household_id,
                    total_identifiers: $total,
                    overall_confidence: $confidence,
                    linking_consent: $linking_consent,
                    created_at: datetime(),
                    last_updated: datetime()
                })
            """, 
                identity_id=identity.identity_id,
                primary_type=identity.primary_identifier_type.value if identity.primary_identifier_type else None,
                primary_value=identity.primary_identifier_value,
                household_id=identity.household_id,
                total=identity.total_identifiers,
                confidence=identity.overall_confidence,
                linking_consent=identity.linking_consent,
            )
            
            # Create Identifier nodes
            for id_type, id_list in identity.identifiers.items():
                for identifier in id_list:
                    await session.run("""
                        MATCH (ui:UnifiedIdentity {identity_id: $identity_id})
                        CREATE (id:Identifier {
                            identifier_id: $identifier_id,
                            identifier_type: $type,
                            identifier_value: $value,
                            source: $source,
                            first_seen: datetime($first_seen),
                            last_seen: datetime($last_seen),
                            confidence: $confidence,
                            verified: $verified
                        })
                        CREATE (id)-[:BELONGS_TO {
                            linked_at: datetime(),
                            link_confidence: $confidence
                        }]->(ui)
                    """,
                        identity_id=identity.identity_id,
                        identifier_id=identifier.identifier_id,
                        type=identifier.identifier_type.value,
                        value=identifier.identifier_value,
                        source=identifier.source.value,
                        first_seen=identifier.first_seen.isoformat(),
                        last_seen=identifier.last_seen.isoformat(),
                        confidence=identifier.confidence,
                        verified=identifier.verified,
                    )
            
            return identity
    
    async def get_identity(self, identity_id: str) -> Optional[UnifiedIdentity]:
        """Retrieve a unified identity by ID."""
        async with await self._get_session() as session:
            result = await session.run("""
                MATCH (ui:UnifiedIdentity {identity_id: $identity_id})
                OPTIONAL MATCH (id:Identifier)-[r:BELONGS_TO]->(ui)
                RETURN ui, collect({identifier: id, link: r}) as identifiers
            """, identity_id=identity_id)
            
            record = await result.single()
            if not record:
                return None
            
            ui_data = dict(record["ui"])
            identifiers_data = record["identifiers"]
            
            identifiers: Dict[str, List[Identifier]] = {}
            for item in identifiers_data:
                if item["identifier"]:
                    id_data = dict(item["identifier"])
                    id_type = id_data["identifier_type"]
                    
                    identifier = Identifier(
                        identifier_id=id_data["identifier_id"],
                        identifier_type=IdentifierType(id_type),
                        identifier_value=id_data["identifier_value"],
                        source=IdentifierSource(id_data["source"]),
                        source_system="graph",
                        first_seen=id_data["first_seen"].to_native(),
                        last_seen=id_data["last_seen"].to_native(),
                        confidence=id_data["confidence"],
                        verified=id_data["verified"],
                    )
                    
                    if id_type not in identifiers:
                        identifiers[id_type] = []
                    identifiers[id_type].append(identifier)
            
            return UnifiedIdentity(
                identity_id=ui_data["identity_id"],
                identifiers=identifiers,
                primary_identifier_type=IdentifierType(ui_data["primary_identifier_type"]) if ui_data.get("primary_identifier_type") else None,
                primary_identifier_value=ui_data.get("primary_identifier_value"),
                household_id=ui_data.get("household_id"),
                overall_confidence=ui_data.get("overall_confidence", 0.5),
                linking_consent=ui_data.get("linking_consent", True),
                created_at=ui_data["created_at"].to_native(),
                last_updated=ui_data["last_updated"].to_native(),
            )
    
    async def find_identity_by_identifier(
        self, 
        identifier_type: IdentifierType, 
        identifier_value: str
    ) -> Optional[UnifiedIdentity]:
        """Find identity by a specific identifier."""
        async with await self._get_session() as session:
            result = await session.run("""
                MATCH (id:Identifier {
                    identifier_type: $type,
                    identifier_value: $value
                })-[:BELONGS_TO]->(ui:UnifiedIdentity)
                RETURN ui.identity_id as identity_id
                LIMIT 1
            """, type=identifier_type.value, value=identifier_value)
            
            record = await result.single()
            if not record:
                return None
            
            return await self.get_identity(record["identity_id"])
    
    async def add_identifier_to_identity(
        self,
        identity_id: str,
        identifier: Identifier,
        link_confidence: float = 1.0
    ) -> bool:
        """Add a new identifier to an existing identity."""
        async with await self._get_session() as session:
            # Check if identifier already exists
            existing = await session.run("""
                MATCH (id:Identifier {
                    identifier_type: $type,
                    identifier_value: $value
                })
                RETURN id.identifier_id as existing_id
            """, type=identifier.identifier_type.value, value=identifier.identifier_value)
            
            record = await existing.single()
            
            if record:
                # Update existing link
                await session.run("""
                    MATCH (id:Identifier {identifier_id: $identifier_id})
                    MATCH (ui:UnifiedIdentity {identity_id: $identity_id})
                    MERGE (id)-[r:BELONGS_TO]->(ui)
                    SET r.linked_at = datetime(),
                        r.link_confidence = $confidence,
                        id.last_seen = datetime()
                """,
                    identifier_id=record["existing_id"],
                    identity_id=identity_id,
                    confidence=link_confidence,
                )
            else:
                # Create new identifier
                await session.run("""
                    MATCH (ui:UnifiedIdentity {identity_id: $identity_id})
                    CREATE (id:Identifier {
                        identifier_id: $identifier_id,
                        identifier_type: $type,
                        identifier_value: $value,
                        source: $source,
                        first_seen: datetime(),
                        last_seen: datetime(),
                        confidence: $confidence,
                        verified: $verified
                    })
                    CREATE (id)-[:BELONGS_TO {
                        linked_at: datetime(),
                        link_confidence: $link_confidence
                    }]->(ui)
                """,
                    identity_id=identity_id,
                    identifier_id=identifier.identifier_id,
                    type=identifier.identifier_type.value,
                    value=identifier.identifier_value,
                    source=identifier.source.value,
                    confidence=identifier.confidence,
                    verified=identifier.verified,
                    link_confidence=link_confidence,
                )
            
            # Update identity metrics
            await session.run("""
                MATCH (ui:UnifiedIdentity {identity_id: $identity_id})
                SET ui.total_identifiers = ui.total_identifiers + 1,
                    ui.last_updated = datetime()
            """, identity_id=identity_id)
            
            return True
    
    async def merge_identities(
        self,
        source_identity_id: str,
        target_identity_id: str,
        reason: str = "deterministic_match"
    ) -> UnifiedIdentity:
        """Merge source identity into target identity."""
        async with await self._get_session() as session:
            # Move all BELONGS_TO relationships
            await session.run("""
                MATCH (id:Identifier)-[r:BELONGS_TO]->(source:UnifiedIdentity {identity_id: $source_id})
                MATCH (target:UnifiedIdentity {identity_id: $target_id})
                CREATE (id)-[:BELONGS_TO {
                    linked_at: datetime(),
                    link_confidence: r.link_confidence,
                    merged_from: $source_id
                }]->(target)
                DELETE r
            """, source_id=source_identity_id, target_id=target_identity_id)
            
            # Mark source as merged
            await session.run("""
                MATCH (source:UnifiedIdentity {identity_id: $source_id})
                SET source.merged_into = $target_id,
                    source.merge_reason = $reason,
                    source.merged_at = datetime(),
                    source.is_active = false
            """, source_id=source_identity_id, target_id=target_identity_id, reason=reason)
            
            # Update target
            await session.run("""
                MATCH (target:UnifiedIdentity {identity_id: $target_id})
                SET target.merge_history = coalesce(target.merge_history, []) + [$source_id],
                    target.last_updated = datetime()
            """, target_id=target_identity_id, source_id=source_identity_id)
            
            return await self.get_identity(target_identity_id)
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the identity graph."""
        async with await self._get_session() as session:
            result = await session.run("""
                MATCH (ui:UnifiedIdentity)
                WHERE ui.is_active <> false
                WITH count(ui) as identity_count
                MATCH (id:Identifier)
                WITH identity_count, count(id) as identifier_count
                MATCH ()-[r:BELONGS_TO]->()
                WITH identity_count, identifier_count, count(r) as belongs_to_count
                MATCH ()-[l:LINKED_TO]->()
                WHERE l.is_active = true
                RETURN identity_count, identifier_count, belongs_to_count, count(l) as link_count
            """)
            
            record = await result.single()
            if not record:
                return {}
            
            return {
                "total_identities": record["identity_count"],
                "total_identifiers": record["identifier_count"],
                "total_belongs_to_edges": record["belongs_to_count"],
                "total_active_links": record["link_count"],
                "avg_identifiers_per_identity": record["identifier_count"] / max(1, record["identity_count"]),
            }
```

---


## Part 3: Deterministic Matching

```python
class DeterministicMatcher:
    """Match identifiers with 100% confidence."""
    
    def __init__(self, identity_graph: IdentityGraph, config: IdentityGraphConfig):
        self.graph = identity_graph
        self.config = config
        self._match_count = 0
        self._no_match_count = 0
    
    async def find_deterministic_matches(
        self,
        identifier: Identifier
    ) -> List[Tuple[UnifiedIdentity, float]]:
        """Find exact matches for an identifier."""
        if not identifier.identifier_type.is_deterministic:
            return []
        
        identity = await self.graph.find_identity_by_identifier(
            identifier.identifier_type,
            identifier.identifier_value
        )
        
        if identity:
            self._match_count += 1
            return [(identity, 1.0)]
        
        self._no_match_count += 1
        return []
    
    async def link_deterministic(
        self,
        id1: Identifier,
        id2: Identifier,
        source: str = "deterministic_matcher"
    ) -> IdentityLink:
        """Create a deterministic link between identifiers."""
        link = IdentityLink(
            source_identifier_id=id1.identifier_id,
            target_identifier_id=id2.identifier_id,
            source_type=id1.identifier_type,
            target_type=id2.identifier_type,
            match_type="deterministic",
            confidence=MatchConfidence.DETERMINISTIC,
            confidence_score=1.0,
            match_signals=[source],
            match_algorithm="deterministic",
        )
        return link


class LoginEventProcessor:
    """Process login events for deterministic identity linking."""
    
    def __init__(
        self,
        deterministic_matcher: DeterministicMatcher,
        identity_graph: IdentityGraph
    ):
        self.matcher = deterministic_matcher
        self.graph = identity_graph
    
    async def process_login(
        self,
        user_login_id: str,
        device_id: Optional[str],
        email_hash: Optional[str],
        phone_hash: Optional[str],
        session_context: Dict[str, Any]
    ) -> MatchResult:
        """Process login event to link identifiers."""
        start_time = datetime.utcnow()
        has_consent = session_context.get("linking_consent", True)
        
        identifiers = self._build_identifiers(
            user_login_id, device_id, email_hash, phone_hash,
            session_context, has_consent
        )
        
        if not identifiers:
            return MatchResult(
                query_identifiers=[],
                query_context=session_context,
                match_type="anonymous",
                match_algorithm="login_processor",
            )
        
        # Find existing identity
        existing_identity = None
        for identifier in identifiers:
            if identifier.identifier_type.is_deterministic:
                matches = await self.matcher.find_deterministic_matches(identifier)
                if matches:
                    existing_identity = matches[0][0]
                    break
        
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        if existing_identity:
            for identifier in identifiers:
                await self.graph.add_identifier_to_identity(
                    existing_identity.identity_id, identifier, 1.0
                )
            
            return MatchResult(
                query_identifiers=identifiers,
                query_context=session_context,
                matched_identity=existing_identity,
                match_confidence=MatchConfidence.DETERMINISTIC,
                match_score=1.0,
                match_type="deterministic",
                match_signals=["login_event"],
                match_algorithm="login_processor",
                resolution_time_ms=elapsed_ms,
            )
        
        # Create new identity
        new_identity = UnifiedIdentity(
            identifiers={id.identifier_type.value: [id] for id in identifiers},
            linking_consent=has_consent,
            overall_confidence=1.0,
        )
        new_identity = await self.graph.create_identity(new_identity)
        
        return MatchResult(
            query_identifiers=identifiers,
            query_context=session_context,
            matched_identity=new_identity,
            match_confidence=MatchConfidence.DETERMINISTIC,
            match_score=1.0,
            new_identity_created=True,
            match_type="new",
            match_signals=["login_event"],
            match_algorithm="login_processor",
            resolution_time_ms=elapsed_ms,
        )
    
    def _build_identifiers(
        self, user_login_id: str, device_id: Optional[str],
        email_hash: Optional[str], phone_hash: Optional[str],
        context: Dict[str, Any], has_consent: bool
    ) -> List[Identifier]:
        """Build identifier list from login event."""
        identifiers = []
        now = datetime.utcnow()
        
        identifiers.append(Identifier(
            identifier_type=IdentifierType.LOGIN_ID,
            identifier_value=user_login_id,
            source=IdentifierSource.LOGIN_EVENT,
            source_system="login_service",
            first_seen=now, last_seen=now,
            confidence=1.0, verified=True,
            consent_for_linking=has_consent,
        ))
        
        if device_id:
            identifiers.append(Identifier(
                identifier_type=IdentifierType.DEVICE_ID,
                identifier_value=device_id,
                source=IdentifierSource.LOGIN_EVENT,
                source_system="login_service",
                first_seen=now, last_seen=now,
                confidence=1.0, verified=True,
                consent_for_linking=has_consent,
            ))
        
        if email_hash:
            identifiers.append(Identifier(
                identifier_type=IdentifierType.EMAIL_HASH,
                identifier_value=email_hash,
                source=IdentifierSource.LOGIN_EVENT,
                source_system="login_service",
                first_seen=now, last_seen=now,
                confidence=1.0, verified=True,
                consent_for_linking=has_consent,
            ))
        
        if phone_hash:
            identifiers.append(Identifier(
                identifier_type=IdentifierType.PHONE_HASH,
                identifier_value=phone_hash,
                source=IdentifierSource.LOGIN_EVENT,
                source_system="login_service",
                first_seen=now, last_seen=now,
                confidence=1.0, verified=True,
                consent_for_linking=has_consent,
            ))
        
        return identifiers
```

---

## Part 4: Probabilistic Matching

```python
from sklearn.ensemble import GradientBoostingClassifier
import pickle


class ProbabilisticMatcher:
    """Match identifiers based on behavioral signals."""
    
    def __init__(self, identity_graph: IdentityGraph, config: IdentityGraphConfig):
        self.graph = identity_graph
        self.config = config
        self.match_model: Optional['MatchModel'] = None
        self.feature_extractor = FeatureExtractor()
        
        self.thresholds = {
            MatchConfidence.VERY_HIGH: 0.98,
            MatchConfidence.HIGH: 0.95,
            MatchConfidence.MEDIUM: 0.80,
            MatchConfidence.LOW: 0.60,
            MatchConfidence.SPECULATIVE: 0.50,
        }
    
    async def load_model(self, model_path: str) -> None:
        self.match_model = MatchModel.load(model_path)
    
    async def find_probabilistic_matches(
        self,
        identifier: Identifier,
        context: Dict[str, Any],
        max_candidates: int = 100
    ) -> List[Tuple[UnifiedIdentity, float]]:
        """Find probabilistic matches for an identifier."""
        candidates = await self._get_candidates(identifier, context, max_candidates)
        
        if not candidates:
            return []
        
        query_features = await self.feature_extractor.extract(identifier, context)
        
        scored_matches = []
        for candidate in candidates:
            candidate_features = await self.feature_extractor.extract_from_identity(
                candidate, context
            )
            
            if self.match_model:
                score = self.match_model.score_match(query_features, candidate_features)
            else:
                score = self._heuristic_score(query_features, candidate_features)
            
            if score >= self.thresholds[MatchConfidence.SPECULATIVE]:
                scored_matches.append((candidate, score))
        
        scored_matches.sort(key=lambda x: -x[1])
        return scored_matches
    
    async def _get_candidates(
        self, identifier: Identifier, context: Dict[str, Any], max_candidates: int
    ) -> List[UnifiedIdentity]:
        """Generate candidate identities using blocking strategies."""
        candidates = []
        candidate_ids = set()
        
        # IP-based candidates
        if context.get("ip_hash"):
            async with await self.graph._get_session() as session:
                result = await session.run("""
                    MATCH (id:Identifier {identifier_type: 'ip_hash', identifier_value: $ip})
                          -[:BELONGS_TO]->(ui:UnifiedIdentity)
                    WHERE id.last_seen > datetime() - duration({days: 7})
                      AND ui.is_active <> false
                    RETURN DISTINCT ui.identity_id as identity_id
                    LIMIT 50
                """, ip=context["ip_hash"])
                
                async for record in result:
                    if record["identity_id"] not in candidate_ids:
                        identity = await self.graph.get_identity(record["identity_id"])
                        if identity:
                            candidates.append(identity)
                            candidate_ids.add(record["identity_id"])
        
        return candidates[:max_candidates]
    
    def _heuristic_score(
        self, query_features: MatchFeatures, candidate_features: MatchFeatures
    ) -> float:
        """Fallback heuristic scoring."""
        weights = {
            "ip_exact_match": 0.20,
            "fingerprint_similarity": 0.18,
            "behavioral_similarity": 0.15,
            "temporal_pattern_match": 0.12,
            "geo_consistency": 0.10,
            "timezone_match": 0.08,
            "language_match": 0.07,
            "household_probability": 0.10,
        }
        
        score = 0.0
        for feature, weight in weights.items():
            q_val = getattr(query_features, feature, 0.0)
            c_val = getattr(candidate_features, feature, 0.0)
            similarity = 1.0 - abs(q_val - c_val)
            score += weight * similarity
        
        return score


class FeatureExtractor:
    """Extract features for probabilistic matching."""
    
    async def extract(self, identifier: Identifier, context: Dict[str, Any]) -> MatchFeatures:
        return MatchFeatures(
            ip_exact_match=1.0 if context.get("ip_hash") else 0.0,
            fingerprint_similarity=0.0,
            screen_resolution_match=1.0 if context.get("screen_resolution") else 0.0,
            timezone_match=1.0 if context.get("timezone") else 0.0,
            language_match=1.0 if context.get("language") else 0.0,
            geo_consistency=1.0 if context.get("geo_hash") else 0.0,
            household_probability=context.get("household_probability", 0.0),
            same_wifi_probability=context.get("same_wifi_probability", 0.0),
        )
    
    async def extract_from_identity(
        self, identity: UnifiedIdentity, context: Dict[str, Any]
    ) -> MatchFeatures:
        has_ip = IdentifierType.IP_HASH.value in identity.identifiers
        has_fp = IdentifierType.FINGERPRINT.value in identity.identifiers
        
        return MatchFeatures(
            ip_exact_match=1.0 if has_ip else 0.0,
            fingerprint_similarity=1.0 if has_fp else 0.0,
            geo_consistency=1.0 if identity.household_id else 0.5,
            household_probability=0.5 if identity.household_id else 0.0,
        )


class MatchModel:
    """ML model for probabilistic identity matching."""
    
    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            min_samples_leaf=10, random_state=42,
        )
        self.feature_importance: Dict[str, float] = {}
        self.model_version: str = "1.0.0"
        self.trained_at: Optional[datetime] = None
    
    def train(
        self,
        feature_pairs: List[Tuple[MatchFeatures, MatchFeatures]],
        labels: List[bool]
    ) -> None:
        """Train the match model on labeled pairs."""
        X = []
        for f1, f2 in feature_pairs:
            v1 = f1.to_vector()
            v2 = f2.to_vector()
            combined = np.concatenate([v1, v2, np.abs(v1 - v2), v1 * v2])
            X.append(combined)
        
        X = np.array(X)
        y = np.array(labels)
        self.model.fit(X, y)
        self.trained_at = datetime.utcnow()
    
    def score_match(
        self, query_features: MatchFeatures, candidate_features: MatchFeatures
    ) -> float:
        """Score match probability."""
        v1 = query_features.to_vector()
        v2 = candidate_features.to_vector()
        combined = np.concatenate([v1, v2, np.abs(v1 - v2), v1 * v2])
        return self.model.predict_proba([combined])[0][1]
    
    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "feature_importance": self.feature_importance,
                "model_version": self.model_version,
                "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            }, f)
    
    @classmethod
    def load(cls, path: str) -> 'MatchModel':
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        model = cls()
        model.model = data["model"]
        model.feature_importance = data["feature_importance"]
        model.model_version = data["model_version"]
        model.trained_at = datetime.fromisoformat(data["trained_at"]) if data["trained_at"] else None
        return model
```

---


## Part 5: Privacy-Preserving Operations

```python
import mmh3
import math


class PrivacyConfig(BaseModel):
    """Configuration for privacy-preserving operations."""
    bloom_filter_size: int = 10_000_000
    bloom_filter_hash_count: int = 7
    bloom_filter_fp_rate: float = 0.01
    epsilon: float = 1.0
    delta: float = 1e-6
    salt_rotation_days: int = 90


class BloomFilterMatcher:
    """Privacy-preserving identity matching using Bloom filters."""
    
    def __init__(self, config: PrivacyConfig):
        self.config = config
        self.size = config.bloom_filter_size
        self.hash_count = config.bloom_filter_hash_count
        self.bit_array = bytearray(self.size // 8 + 1)
        self._items_added = 0
    
    def _get_hash_values(self, item: str, salt: str = "") -> List[int]:
        hashes = []
        salted_item = f"{salt}:{item}" if salt else item
        for i in range(self.hash_count):
            h = mmh3.hash(salted_item, seed=i) % self.size
            hashes.append(abs(h))
        return hashes
    
    def add(self, identifier_value: str, salt: str = "") -> None:
        hashes = self._get_hash_values(identifier_value, salt)
        for h in hashes:
            byte_idx = h // 8
            bit_idx = h % 8
            self.bit_array[byte_idx] |= (1 << bit_idx)
        self._items_added += 1
    
    def contains(self, identifier_value: str, salt: str = "") -> bool:
        hashes = self._get_hash_values(identifier_value, salt)
        for h in hashes:
            byte_idx = h // 8
            bit_idx = h % 8
            if not (self.bit_array[byte_idx] & (1 << bit_idx)):
                return False
        return True
    
    def intersection_count(self, other: 'BloomFilterMatcher') -> int:
        """Estimate intersection count with another bloom filter."""
        overlap_bits = 0
        total_bits = 0
        
        for i in range(len(self.bit_array)):
            for j in range(8):
                self_bit = (self.bit_array[i] >> j) & 1
                other_bit = (other.bit_array[i] >> j) & 1
                if self_bit and other_bit:
                    overlap_bits += 1
                if self_bit or other_bit:
                    total_bits += 1
        
        if total_bits == 0:
            return 0
        
        jaccard = overlap_bits / total_bits
        return int(min(self._items_added, other._items_added) * jaccard)


class DifferentialPrivacyEngine:
    """Add differential privacy to identity resolution queries."""
    
    def __init__(self, config: PrivacyConfig):
        self.epsilon = config.epsilon
        self.delta = config.delta
    
    def add_laplace_noise(self, value: float, sensitivity: float) -> float:
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale)
        return value + noise
    
    def privatize_count(self, count: int) -> int:
        noisy_count = self.add_laplace_noise(count, sensitivity=1.0)
        return max(0, int(round(noisy_count)))


class CleanRoomProtocol:
    """Protocol for privacy-safe identity matching in clean rooms."""
    
    def __init__(self, privacy_config: PrivacyConfig, identity_graph: IdentityGraph):
        self.config = privacy_config
        self.graph = identity_graph
    
    async def prepare_matching_set(
        self, audience_criteria: Dict[str, Any], salt: str
    ) -> BloomFilterMatcher:
        """Prepare bloom filter for clean room matching."""
        async with await self.graph._get_session() as session:
            result = await session.run("""
                MATCH (ui:UnifiedIdentity)
                WHERE ui.is_active <> false AND ui.linking_consent = true
                MATCH (id:Identifier)-[:BELONGS_TO]->(ui)
                WHERE id.identifier_type = 'email_hash'
                RETURN DISTINCT id.identifier_value as identifier
                LIMIT 10000000
            """)
            
            bf = BloomFilterMatcher(self.config)
            async for record in result:
                bf.add(record["identifier"], salt)
            return bf
    
    async def execute_match(
        self, adam_bloom: BloomFilterMatcher, partner_bloom: BloomFilterMatcher
    ) -> Dict[str, Any]:
        """Execute clean room matching protocol."""
        intersection_estimate = adam_bloom.intersection_count(partner_bloom)
        dp_engine = DifferentialPrivacyEngine(self.config)
        noisy_intersection = dp_engine.privatize_count(intersection_estimate)
        
        return {
            "protocol_version": "1.0",
            "estimated_overlap": noisy_intersection,
            "adam_match_rate": noisy_intersection / max(1, adam_bloom._items_added),
            "partner_match_rate": noisy_intersection / max(1, partner_bloom._items_added),
            "timestamp": datetime.utcnow().isoformat(),
        }
```

---

## Part 6: Household Resolution

```python
class HouseholdConfig(BaseModel):
    """Configuration for household resolution."""
    min_household_confidence: float = 0.75
    max_household_size: int = 10
    ip_weight: float = 0.30
    wifi_weight: float = 0.25
    address_weight: float = 0.25
    temporal_weight: float = 0.20


class HouseholdSignals(BaseModel):
    """Signals used for household detection."""
    shared_ip_count: int = 0
    shared_wifi_ssid: bool = False
    same_postal_code: bool = False
    same_address_hash: bool = False
    activity_overlap_score: float = 0.0
    different_device_types: bool = False
    household_probability: float = 0.0
    
    def compute_probability(self, config: HouseholdConfig) -> float:
        score = 0.0
        if self.shared_ip_count > 0:
            score += config.ip_weight * min(1.0, self.shared_ip_count / 10)
        if self.shared_wifi_ssid:
            score += config.wifi_weight
        if self.same_address_hash:
            score += config.address_weight
        elif self.same_postal_code:
            score += config.address_weight * 0.5
        score += config.temporal_weight * self.activity_overlap_score
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
    household_id: str = Field(default_factory=lambda: f"hh_{uuid.uuid4().hex[:12]}")
    members: List[HouseholdMember] = Field(default_factory=list)
    primary_member_id: Optional[str] = None
    estimated_size: int = 0
    has_children: bool = False
    postal_hash: Optional[str] = None
    address_hash: Optional[str] = None
    overall_confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_member(
        self, identity_id: str, confidence: float, signals: List[str], role: str = "unknown"
    ) -> HouseholdMember:
        member = HouseholdMember(
            identity_id=identity_id,
            household_id=self.household_id,
            role=role,
            membership_confidence=confidence,
            join_signals=signals,
        )
        self.members.append(member)
        self.estimated_size = len(self.members)
        return member


class HouseholdResolver:
    """Resolve identities into households."""
    
    def __init__(self, identity_graph: IdentityGraph, config: HouseholdConfig):
        self.graph = identity_graph
        self.config = config
    
    async def find_or_create_household(
        self, identity: UnifiedIdentity, context: Dict[str, Any]
    ) -> Optional[Household]:
        """Find existing household or create new one."""
        if identity.household_id:
            return await self.get_household(identity.household_id)
        
        candidates = await self._find_candidate_households(identity, context)
        
        if candidates:
            best_match = max(candidates, key=lambda x: x[1])
            household, confidence = best_match
            
            if confidence >= self.config.min_household_confidence:
                await self._add_to_household(household, identity, confidence, context)
                return household
        
        return await self._create_household(identity, context)
    
    async def _find_candidate_households(
        self, identity: UnifiedIdentity, context: Dict[str, Any]
    ) -> List[Tuple[Household, float]]:
        """Find households that might contain this identity."""
        candidates = []
        ip_identifiers = identity.identifiers.get(IdentifierType.IP_HASH.value, [])
        
        for ip_id in ip_identifiers:
            async with await self.graph._get_session() as session:
                result = await session.run("""
                    MATCH (id:Identifier {identifier_type: 'ip_hash', identifier_value: $ip})
                          -[:BELONGS_TO]->(ui:UnifiedIdentity)
                    WHERE ui.household_id IS NOT NULL
                    RETURN DISTINCT ui.household_id as household_id
                    LIMIT 10
                """, ip=ip_id.identifier_value)
                
                async for record in result:
                    hh = await self.get_household(record["household_id"])
                    if hh:
                        confidence = await self._score_household_match(identity, hh, context)
                        candidates.append((hh, confidence))
        
        return candidates
    
    async def _score_household_match(
        self, identity: UnifiedIdentity, household: Household, context: Dict[str, Any]
    ) -> float:
        """Score how well identity matches a household."""
        signals = HouseholdSignals()
        identity_ips = set(identity.get_all_identifier_values(IdentifierType.IP_HASH))
        
        for member in household.members:
            member_identity = await self.graph.get_identity(member.identity_id)
            if member_identity:
                member_ips = set(member_identity.get_all_identifier_values(IdentifierType.IP_HASH))
                signals.shared_ip_count = max(
                    signals.shared_ip_count, len(identity_ips.intersection(member_ips))
                )
        
        if context.get("postal_hash") == household.postal_hash:
            signals.same_postal_code = True
        if context.get("address_hash") == household.address_hash:
            signals.same_address_hash = True
        
        return signals.compute_probability(self.config)
    
    async def _add_to_household(
        self, household: Household, identity: UnifiedIdentity,
        confidence: float, context: Dict[str, Any]
    ) -> None:
        """Add identity to existing household."""
        household.add_member(
            identity_id=identity.identity_id,
            confidence=confidence,
            signals=["ip_cooccurrence"],
            role="secondary",
        )
        identity.household_id = household.household_id
        await self.graph.update_identity(identity)
        await self._save_household(household)
    
    async def _create_household(
        self, identity: UnifiedIdentity, context: Dict[str, Any]
    ) -> Household:
        """Create new household with identity as primary member."""
        household = Household(
            postal_hash=context.get("postal_hash"),
            address_hash=context.get("address_hash"),
            overall_confidence=0.5,
        )
        household.add_member(
            identity_id=identity.identity_id,
            confidence=1.0,
            signals=["founder"],
            role="primary",
        )
        household.primary_member_id = identity.identity_id
        identity.household_id = household.household_id
        identity.household_role = "primary"
        await self.graph.update_identity(identity)
        await self._save_household(household)
        return household
    
    async def _save_household(self, household: Household) -> None:
        """Save household to Neo4j."""
        async with await self.graph._get_session() as session:
            await session.run("""
                MERGE (hh:Household {household_id: $hh_id})
                SET hh.estimated_size = $size,
                    hh.postal_hash = $postal,
                    hh.overall_confidence = $confidence,
                    hh.last_updated = datetime()
            """,
                hh_id=household.household_id,
                size=household.estimated_size,
                postal=household.postal_hash,
                confidence=household.overall_confidence,
            )
            
            for member in household.members:
                await session.run("""
                    MATCH (hh:Household {household_id: $hh_id})
                    MATCH (ui:UnifiedIdentity {identity_id: $identity_id})
                    MERGE (ui)-[r:MEMBER_OF]->(hh)
                    SET r.role = $role, r.confidence = $confidence
                """,
                    hh_id=household.household_id,
                    identity_id=member.identity_id,
                    role=member.role,
                    confidence=member.membership_confidence,
                )
    
    async def get_household(self, household_id: str) -> Optional[Household]:
        """Retrieve household by ID."""
        async with await self.graph._get_session() as session:
            result = await session.run("""
                MATCH (hh:Household {household_id: $hh_id})
                OPTIONAL MATCH (ui:UnifiedIdentity)-[r:MEMBER_OF]->(hh)
                RETURN hh, collect({identity_id: ui.identity_id, role: r.role, confidence: r.confidence}) as members
            """, hh_id=household_id)
            
            record = await result.single()
            if not record:
                return None
            
            hh_data = dict(record["hh"])
            members = [
                HouseholdMember(
                    identity_id=m["identity_id"],
                    household_id=household_id,
                    role=m["role"] or "unknown",
                    membership_confidence=m["confidence"] or 0.5,
                )
                for m in record["members"] if m["identity_id"]
            ]
            
            return Household(
                household_id=household_id,
                members=members,
                estimated_size=hh_data.get("estimated_size", len(members)),
                postal_hash=hh_data.get("postal_hash"),
                overall_confidence=hh_data.get("overall_confidence", 0.5),
            )
```

---


## Part 7: Identity Resolution Service

```python
class IdentityResolver:
    """Main service for resolving and managing identities."""
    
    def __init__(
        self,
        graph: IdentityGraph,
        deterministic_matcher: DeterministicMatcher,
        probabilistic_matcher: ProbabilisticMatcher,
        household_resolver: HouseholdResolver,
        consent_manager: Optional['ConsentManager'],
        config: IdentityGraphConfig
    ):
        self.graph = graph
        self.deterministic = deterministic_matcher
        self.probabilistic = probabilistic_matcher
        self.household = household_resolver
        self.consent = consent_manager
        self.config = config
        
        self._resolutions = 0
        self._deterministic_matches = 0
        self._probabilistic_matches = 0
        self._new_identities = 0
    
    async def resolve(
        self,
        identifiers: List[Identifier],
        context: Dict[str, Any],
        require_consent: bool = True
    ) -> MatchResult:
        """Resolve identifiers to a unified identity."""
        start_time = datetime.utcnow()
        self._resolutions += 1
        
        # Check consent
        if require_consent:
            has_consent = await self._check_linking_consent(identifiers, context)
            if not has_consent:
                return self._create_anonymous_result(identifiers, context, start_time)
        
        # Try deterministic matches first
        deterministic_matches: Set[str] = set()
        for identifier in identifiers:
            if identifier.identifier_type.is_deterministic:
                matches = await self.deterministic.find_deterministic_matches(identifier)
                for identity, _ in matches:
                    deterministic_matches.add(identity.identity_id)
        
        if len(deterministic_matches) == 1:
            identity_id = list(deterministic_matches)[0]
            identity = await self.graph.get_identity(identity_id)
            await self._add_identifiers_to_identity(identity, identifiers)
            await self.household.find_or_create_household(identity, context)
            
            self._deterministic_matches += 1
            return self._create_match_result(
                identity, identifiers, context, start_time,
                match_type="deterministic",
                confidence=MatchConfidence.DETERMINISTIC
            )
        
        elif len(deterministic_matches) > 1:
            identity = await self._merge_identities(list(deterministic_matches))
            await self._add_identifiers_to_identity(identity, identifiers)
            await self.household.find_or_create_household(identity, context)
            
            self._deterministic_matches += 1
            return self._create_match_result(
                identity, identifiers, context, start_time,
                match_type="deterministic",
                confidence=MatchConfidence.DETERMINISTIC,
            )
        
        # Try probabilistic matching
        best_match: Optional[UnifiedIdentity] = None
        best_score = 0.0
        
        for identifier in identifiers:
            prob_matches = await self.probabilistic.find_probabilistic_matches(
                identifier, context
            )
            for identity, score in prob_matches:
                if score > best_score:
                    best_score = score
                    best_match = identity
        
        if best_match and best_score >= self.config.probabilistic_min_confidence:
            await self._add_identifiers_to_identity(best_match, identifiers, probabilistic=True)
            await self.household.find_or_create_household(best_match, context)
            
            self._probabilistic_matches += 1
            return self._create_match_result(
                best_match, identifiers, context, start_time,
                match_type="probabilistic",
                confidence=MatchConfidence.from_score(best_score),
                match_score=best_score,
            )
        
        # Create new identity
        new_identity = await self._create_new_identity(identifiers, context)
        await self.household.find_or_create_household(new_identity, context)
        
        self._new_identities += 1
        return self._create_match_result(
            new_identity, identifiers, context, start_time,
            match_type="new",
            confidence=MatchConfidence.DETERMINISTIC,
            new_identity=True
        )
    
    async def _check_linking_consent(
        self, identifiers: List[Identifier], context: Dict[str, Any]
    ) -> bool:
        for identifier in identifiers:
            if not identifier.consent_for_linking:
                return False
        return context.get("linking_consent", True)
    
    async def _add_identifiers_to_identity(
        self, identity: UnifiedIdentity, identifiers: List[Identifier],
        probabilistic: bool = False
    ) -> None:
        for identifier in identifiers:
            confidence = 1.0 if not probabilistic else 0.8
            await self.graph.add_identifier_to_identity(
                identity.identity_id, identifier, confidence
            )
    
    async def _merge_identities(self, identity_ids: List[str]) -> UnifiedIdentity:
        identities = [await self.graph.get_identity(id) for id in identity_ids]
        identities = [i for i in identities if i]
        if len(identities) < 2:
            return identities[0] if identities else None
        
        primary = max(identities, key=lambda i: i.total_identifiers)
        
        for identity in identities:
            if identity.identity_id != primary.identity_id:
                await self.graph.merge_identities(
                    identity.identity_id, primary.identity_id, "deterministic_match"
                )
        
        return await self.graph.get_identity(primary.identity_id)
    
    async def _create_new_identity(
        self, identifiers: List[Identifier], context: Dict[str, Any]
    ) -> UnifiedIdentity:
        identifiers_by_type: Dict[str, List[Identifier]] = {}
        for identifier in identifiers:
            key = identifier.identifier_type.value
            if key not in identifiers_by_type:
                identifiers_by_type[key] = []
            identifiers_by_type[key].append(identifier)
        
        identity = UnifiedIdentity(
            identifiers=identifiers_by_type,
            linking_consent=all(id.consent_for_linking for id in identifiers),
            overall_confidence=1.0 if len(identifiers) > 1 else 0.5,
        )
        return await self.graph.create_identity(identity)
    
    def _create_anonymous_result(
        self, identifiers: List[Identifier], context: Dict[str, Any], start_time: datetime
    ) -> MatchResult:
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return MatchResult(
            query_identifiers=identifiers,
            query_context=context,
            match_type="anonymous",
            match_signals=["no_consent"],
            match_algorithm="identity_resolver",
            resolution_time_ms=elapsed_ms,
        )
    
    def _create_match_result(
        self, identity: UnifiedIdentity, identifiers: List[Identifier],
        context: Dict[str, Any], start_time: datetime, match_type: str,
        confidence: MatchConfidence, match_score: float = 1.0,
        new_identity: bool = False
    ) -> MatchResult:
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return MatchResult(
            query_identifiers=identifiers,
            query_context=context,
            matched_identity=identity,
            match_confidence=confidence,
            match_score=match_score,
            new_identity_created=new_identity,
            match_type=match_type,
            match_algorithm="identity_resolver",
            resolution_time_ms=elapsed_ms,
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        total = max(1, self._resolutions)
        return {
            "total_resolutions": self._resolutions,
            "deterministic_matches": self._deterministic_matches,
            "probabilistic_matches": self._probabilistic_matches,
            "new_identities_created": self._new_identities,
            "deterministic_rate": self._deterministic_matches / total,
            "probabilistic_rate": self._probabilistic_matches / total,
        }
```

---

## Part 8: Partner Integrations

```python
import aiohttp


class UID2Connector:
    """Integration with Unified ID 2.0."""
    
    def __init__(self, api_key: str, secret_key: str, environment: str = "production"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://prod.uidapi.com" if environment == "production" else "https://integ.uidapi.com"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
    
    async def generate_uid2_from_email(
        self, email: str, consent_timestamp: datetime
    ) -> Optional[Dict[str, str]]:
        """Generate UID2 token from email."""
        normalized = email.strip().lower()
        email_hash = hashlib.sha256(normalized.encode()).hexdigest()
        
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/v2/token/generate",
                json={"email_hash": email_hash, "optout_check": 1}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "advertising_token": data.get("body", {}).get("advertising_token"),
                        "refresh_token": data.get("body", {}).get("refresh_token"),
                    }
        except aiohttp.ClientError as e:
            logger.error(f"UID2 API error: {e}")
        return None
    
    async def refresh_uid2(self, refresh_token: str) -> Optional[Dict[str, str]]:
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/v2/token/refresh",
                json={"refresh_token": refresh_token}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "advertising_token": data.get("body", {}).get("advertising_token"),
                        "refresh_token": data.get("body", {}).get("refresh_token"),
                    }
        except aiohttp.ClientError:
            pass
        return None


class IHeartConnector:
    """Integration with iHeart's identity system."""
    
    def __init__(self, api_key: str, partner_id: str, environment: str = "production"):
        self.api_key = api_key
        self.partner_id = partner_id
        self.base_url = "https://api.iheart.com/partner" if environment == "production" else "https://sandbox-api.iheart.com/partner"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session:
            headers = {"X-API-Key": self.api_key, "X-Partner-ID": self.partner_id, "Content-Type": "application/json"}
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
    
    async def resolve_iheart_id(self, iheart_user_id: str) -> Optional[Dict[str, Any]]:
        """Get identity data from iHeart."""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/users/{iheart_user_id}/identity") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "iheart_id": iheart_user_id,
                        "email_hash": data.get("email_hash"),
                        "device_ids": data.get("device_ids", []),
                        "household_id": data.get("household_id"),
                        "segments": data.get("psychographic_segments", []),
                    }
        except aiohttp.ClientError as e:
            logger.error(f"iHeart API error: {e}")
        return None
    
    async def sync_identity_to_iheart(
        self, adam_identity_id: str, adam_identity: UnifiedIdentity
    ) -> bool:
        """Sync ADAM identity to iHeart."""
        iheart_id = adam_identity.get_identifier(IdentifierType.IHEART_ID)
        if not iheart_id:
            return False
        
        session = await self._get_session()
        payload = {
            "partner_identity_id": adam_identity_id,
            "device_ids": adam_identity.get_all_identifier_values(IdentifierType.DEVICE_ID),
            "household_id": adam_identity.household_id,
        }
        
        try:
            async with session.post(
                f"{self.base_url}/users/{iheart_id.identifier_value}/sync",
                json=payload
            ) as response:
                return response.status == 200
        except aiohttp.ClientError:
            return False


class RampIDConnector:
    """Integration with LiveRamp RampID."""
    
    def __init__(self, api_key: str, client_id: str):
        self.api_key = api_key
        self.client_id = client_id
        self.base_url = "https://api.liveramp.com"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session:
            headers = {"Authorization": f"Bearer {self.api_key}", "X-Client-ID": self.client_id}
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
    
    async def translate_to_ramp_id(
        self, identifier_type: str, identifier_value: str
    ) -> Optional[str]:
        """Translate an identifier to RampID."""
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/v1/identity/translate",
                json={
                    "source_type": identifier_type,
                    "source_value": identifier_value,
                    "target_type": "ramp_id",
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("ramp_id")
        except aiohttp.ClientError:
            pass
        return None
```

---


## Part 9: Neo4j Schema & Operations

```cypher
// =============================================================================
// ADAM IDENTITY RESOLUTION - NEO4J SCHEMA
// =============================================================================

// Unified Identity node
CREATE CONSTRAINT unified_identity_id IF NOT EXISTS
FOR (ui:UnifiedIdentity) REQUIRE ui.identity_id IS UNIQUE;

// Identifier node
CREATE CONSTRAINT identifier_id IF NOT EXISTS
FOR (id:Identifier) REQUIRE id.identifier_id IS UNIQUE;

// Compound index for identifier lookup
CREATE INDEX identifier_lookup IF NOT EXISTS
FOR (id:Identifier) ON (id.identifier_type, id.identifier_value);

// Household node
CREATE CONSTRAINT household_id IF NOT EXISTS
FOR (hh:Household) REQUIRE hh.household_id IS UNIQUE;

// Performance indexes
CREATE INDEX identifier_last_seen IF NOT EXISTS
FOR (id:Identifier) ON (id.last_seen);

CREATE INDEX identity_household IF NOT EXISTS
FOR (ui:UnifiedIdentity) ON (ui.household_id);

CREATE INDEX identity_active IF NOT EXISTS
FOR (ui:UnifiedIdentity) ON (ui.is_active);

// Sample Queries
// Find identity by email hash:
// MATCH (id:Identifier {identifier_type: 'email_hash', identifier_value: $hash})
//       -[:BELONGS_TO]->(ui:UnifiedIdentity)
// WHERE ui.is_active <> false
// RETURN ui

// Get household members:
// MATCH (ui:UnifiedIdentity)-[r:MEMBER_OF]->(hh:Household {household_id: $hh_id})
// RETURN ui, r.role, r.confidence

// Cross-device identities:
// MATCH (ui:UnifiedIdentity) WHERE ui.known_devices > 1
// RETURN ui.identity_id, ui.known_devices
```

---

## Part 10: FastAPI Endpoints

```python
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn


class IdentifierInput(BaseModel):
    identifier_type: str
    identifier_value: str
    source: str = "api"
    verified: bool = False


class ContextInput(BaseModel):
    ip_hash: Optional[str] = None
    geo_hash: Optional[str] = None
    fingerprint_hash: Optional[str] = None
    timezone: Optional[str] = None
    linking_consent: bool = True


class ResolveRequest(BaseModel):
    identifiers: List[IdentifierInput]
    context: ContextInput = Field(default_factory=ContextInput)
    require_consent: bool = True


class IdentityResponse(BaseModel):
    identity_id: str
    total_identifiers: int
    overall_confidence: float
    household_id: Optional[str]
    match_type: str
    match_confidence: str
    match_score: float
    resolution_time_ms: float
    is_new: bool = False


app = FastAPI(
    title="ADAM Identity Resolution API",
    description="Cross-platform identity resolution service",
    version="2.0.0"
)

security = HTTPBearer()


async def get_identity_resolver() -> IdentityResolver:
    return app.state.resolver


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


@app.post("/v1/resolve", response_model=IdentityResponse)
async def resolve_identity(
    request: ResolveRequest,
    api_key: str = Depends(verify_api_key),
    resolver: IdentityResolver = Depends(get_identity_resolver)
):
    """Resolve identifiers to a unified identity."""
    try:
        identifiers = [
            Identifier(
                identifier_type=IdentifierType(id_input.identifier_type),
                identifier_value=id_input.identifier_value,
                source=IdentifierSource.API_CALL,
                source_system="api",
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                verified=id_input.verified,
            )
            for id_input in request.identifiers
        ]
        
        context = {
            "ip_hash": request.context.ip_hash,
            "geo_hash": request.context.geo_hash,
            "fingerprint_hash": request.context.fingerprint_hash,
            "linking_consent": request.context.linking_consent,
        }
        
        result = await resolver.resolve(
            identifiers=identifiers,
            context=context,
            require_consent=request.require_consent
        )
        
        if not result.matched_identity:
            raise HTTPException(status_code=404, detail="No identity resolved")
        
        return IdentityResponse(
            identity_id=result.matched_identity.identity_id,
            total_identifiers=result.matched_identity.total_identifiers,
            overall_confidence=result.matched_identity.overall_confidence,
            household_id=result.matched_identity.household_id,
            match_type=result.match_type,
            match_confidence=result.match_confidence.value,
            match_score=result.match_score,
            resolution_time_ms=result.resolution_time_ms,
            is_new=result.new_identity_created,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/identity/{identity_id}", response_model=IdentityResponse)
async def get_identity(
    identity_id: str,
    api_key: str = Depends(verify_api_key),
    resolver: IdentityResolver = Depends(get_identity_resolver)
):
    """Get a unified identity by ID."""
    identity = await resolver.graph.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    
    return IdentityResponse(
        identity_id=identity.identity_id,
        total_identifiers=identity.total_identifiers,
        overall_confidence=identity.overall_confidence,
        household_id=identity.household_id,
        match_type="lookup",
        match_confidence="deterministic",
        match_score=1.0,
        resolution_time_ms=0,
    )


@app.get("/v1/stats")
async def get_graph_stats(
    api_key: str = Depends(verify_api_key),
    resolver: IdentityResolver = Depends(get_identity_resolver)
):
    """Get identity graph statistics."""
    return await resolver.graph.get_graph_statistics()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "identity-resolution"}


@app.on_event("startup")
async def startup():
    config = IdentityGraphConfig()
    graph = IdentityGraph(config)
    await graph.connect()
    
    deterministic = DeterministicMatcher(graph, config)
    probabilistic = ProbabilisticMatcher(graph, config)
    household = HouseholdResolver(graph, HouseholdConfig())
    
    resolver = IdentityResolver(
        graph=graph,
        deterministic_matcher=deterministic,
        probabilistic_matcher=probabilistic,
        household_resolver=household,
        consent_manager=None,
        config=config
    )
    app.state.resolver = resolver


@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "resolver"):
        await app.state.resolver.graph.disconnect()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8019)
```

---

## Part 11: Integration & Testing

```python
import pytest


class TestIdentifier:
    """Tests for Identifier model."""
    
    def test_identifier_creation(self):
        identifier = Identifier(
            identifier_type=IdentifierType.EMAIL_HASH,
            identifier_value="abc123def456",
            source=IdentifierSource.LOGIN_EVENT,
            source_system="test",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        assert identifier.identifier_type == IdentifierType.EMAIL_HASH
        assert identifier.confidence == 1.0
        assert not identifier.is_stale
    
    def test_identifier_staleness(self):
        old_date = datetime.utcnow() - timedelta(days=400)
        identifier = Identifier(
            identifier_type=IdentifierType.DEVICE_ID,
            identifier_value="device123",
            source=IdentifierSource.SDK_COLLECTION,
            source_system="test",
            first_seen=old_date,
            last_seen=old_date,
        )
        assert identifier.is_stale


class TestMatchConfidence:
    """Tests for MatchConfidence enum."""
    
    def test_score_to_confidence(self):
        assert MatchConfidence.from_score(1.0) == MatchConfidence.DETERMINISTIC
        assert MatchConfidence.from_score(0.97) == MatchConfidence.HIGH
        assert MatchConfidence.from_score(0.85) == MatchConfidence.MEDIUM
        assert MatchConfidence.from_score(0.70) == MatchConfidence.LOW


class TestBloomFilter:
    """Tests for BloomFilterMatcher."""
    
    def test_bloom_filter_basic(self):
        config = PrivacyConfig()
        bf = BloomFilterMatcher(config)
        bf.add("test_identifier_1")
        bf.add("test_identifier_2")
        assert bf.contains("test_identifier_1")
        assert bf.contains("test_identifier_2")


@pytest.fixture
async def identity_graph():
    config = IdentityGraphConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test_password",
        neo4j_database="adam_test"
    )
    graph = IdentityGraph(config)
    await graph.connect()
    yield graph
    await graph.disconnect()


@pytest.fixture
async def identity_resolver(identity_graph):
    config = IdentityGraphConfig()
    deterministic = DeterministicMatcher(identity_graph, config)
    probabilistic = ProbabilisticMatcher(identity_graph, config)
    household = HouseholdResolver(identity_graph, HouseholdConfig())
    
    return IdentityResolver(
        graph=identity_graph,
        deterministic_matcher=deterministic,
        probabilistic_matcher=probabilistic,
        household_resolver=household,
        consent_manager=None,
        config=config
    )


@pytest.mark.asyncio
async def test_resolve_new_identity(identity_resolver):
    identifiers = [
        Identifier(
            identifier_type=IdentifierType.EMAIL_HASH,
            identifier_value=f"test_email_{datetime.utcnow().timestamp()}",
            source=IdentifierSource.LOGIN_EVENT,
            source_system="test",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
    ]
    
    result = await identity_resolver.resolve(
        identifiers=identifiers,
        context={"linking_consent": True},
    )
    
    assert result.matched_identity is not None
    assert result.new_identity_created
    assert result.match_type == "new"


@pytest.mark.asyncio
async def test_resolution_latency(identity_resolver):
    import time
    
    identifiers = [
        Identifier(
            identifier_type=IdentifierType.DEVICE_ID,
            identifier_value=f"perf_test_{i}",
            source=IdentifierSource.SDK_COLLECTION,
            source_system="test",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        for i in range(3)
    ]
    
    # Warm up
    await identity_resolver.resolve(identifiers, context={})
    
    # Measure
    latencies = []
    for _ in range(10):
        start = time.perf_counter()
        await identity_resolver.resolve(identifiers, context={})
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95_latency < 20, f"P95 latency {p95_latency}ms exceeds 20ms target"


# Blackboard Integration
class IdentityResolutionComponent:
    """ADAM component wrapper for identity resolution."""
    
    def __init__(self, resolver: IdentityResolver):
        self.resolver = resolver
        self.component_id = "identity_resolution"
    
    @property
    def dependencies(self) -> List[str]:
        return ["signal_aggregation"]
    
    @property
    def outputs(self) -> List[str]:
        return ["unified_identity", "identity_confidence", "household_id"]
    
    async def process(self, blackboard: 'ADAMBlackboard') -> 'ADAMBlackboard':
        identifiers = self._extract_identifiers(blackboard)
        
        context = {
            "ip_hash": blackboard.component_outputs.get("ip_hash"),
            "geo_hash": blackboard.component_outputs.get("geo_hash"),
            "linking_consent": blackboard.component_outputs.get("consent_status", {}).get("linking", True),
        }
        
        result = await self.resolver.resolve(identifiers=identifiers, context=context)
        
        if result.matched_identity:
            blackboard.component_outputs["unified_identity"] = result.matched_identity
            blackboard.component_outputs["identity_confidence"] = result.match_score
            blackboard.component_outputs["household_id"] = result.matched_identity.household_id
        
        return blackboard
    
    def _extract_identifiers(self, blackboard: 'ADAMBlackboard') -> List[Identifier]:
        identifiers = []
        if blackboard.component_outputs.get("device_id"):
            identifiers.append(Identifier(
                identifier_type=IdentifierType.DEVICE_ID,
                identifier_value=blackboard.component_outputs["device_id"],
                source=IdentifierSource.SDK_COLLECTION,
                source_system="blackboard",
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            ))
        return identifiers
```

---


## Part 12: Deployment & Operations

```yaml
# docker-compose.yml
version: "3.9"

services:
  identity-resolution:
    build:
      context: .
      dockerfile: Dockerfile.identity
    ports:
      - "8019:8019"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - LOG_LEVEL=INFO
      - PROBABILISTIC_MIN_CONFIDENCE=0.60
    depends_on:
      - neo4j
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8019/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "2"
          memory: 4G

  neo4j:
    image: neo4j:5.15.0-enterprise
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=4G
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

```python
# Configuration & Monitoring
from pydantic import BaseSettings
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class IdentityResolutionSettings(BaseSettings):
    """Settings for identity resolution service."""
    
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "adam"
    
    deterministic_confidence: float = 1.0
    probabilistic_min_confidence: float = 0.60
    merge_confidence_threshold: float = 0.95
    
    min_household_confidence: float = 0.75
    max_household_size: int = 10
    
    enable_bloom_filters: bool = True
    bloom_filter_fp_rate: float = 0.01
    
    uid2_api_key: str = ""
    iheart_api_key: str = ""
    ramp_api_key: str = ""
    
    log_level: str = "INFO"
    metrics_port: int = 9019
    
    class Config:
        env_prefix = "IDENTITY_"


# Prometheus Metrics
resolution_requests = Counter(
    "identity_resolution_requests_total",
    "Total identity resolution requests",
    ["match_type"]
)

resolution_latency = Histogram(
    "identity_resolution_latency_seconds",
    "Identity resolution latency",
    buckets=[0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
)

active_identities = Gauge(
    "identity_graph_active_identities",
    "Number of active unified identities"
)


class MetricsCollector:
    """Collect and expose metrics."""
    
    def __init__(self, resolver: IdentityResolver, port: int = 9019):
        self.resolver = resolver
        self.port = port
    
    def start(self):
        start_http_server(self.port)
    
    def record_resolution(self, result: MatchResult):
        resolution_requests.labels(match_type=result.match_type).inc()
        resolution_latency.observe(result.resolution_time_ms / 1000)
    
    async def update_graph_metrics(self):
        stats = await self.resolver.graph.get_graph_statistics()
        active_identities.set(stats.get("total_identities", 0))
```

---

## Implementation Timeline

```yaml
phase_1_foundation:
  duration: "Weeks 1-2"
  deliverables:
    - Core data models (Identifier, UnifiedIdentity, IdentityLink)
    - Neo4j schema and indexes
    - Basic graph CRUD operations
    - Unit tests for models
  success_criteria:
    - All data models validated
    - Graph operations <10ms latency
    - 100% test coverage on models

phase_2_deterministic:
  duration: "Weeks 3-4"
  deliverables:
    - DeterministicMatcher implementation
    - LoginEventProcessor
    - Identity merge logic
    - Deterministic link creation
  success_criteria:
    - Login events processed <20ms
    - Merge operations maintain data integrity
    - 100% accuracy on deterministic matches

phase_3_probabilistic:
  duration: "Weeks 5-6"
  deliverables:
    - ProbabilisticMatcher implementation
    - FeatureExtractor
    - MatchModel training pipeline
    - Candidate generation strategies
  success_criteria:
    - Probabilistic matching <50ms
    - False positive rate <1%
    - Match accuracy >85% on test set

phase_4_household:
  duration: "Week 7"
  deliverables:
    - HouseholdResolver implementation
    - Household signal detection
    - Role inference
    - Household graph relationships
  success_criteria:
    - Household detection >75% accuracy
    - No false household merges
    - Max 10 members per household

phase_5_privacy:
  duration: "Week 8"
  deliverables:
    - BloomFilterMatcher
    - DifferentialPrivacyEngine
    - CleanRoomProtocol
    - Consent integration
  success_criteria:
    - Bloom filter FP rate <1%
    - DP epsilon budget tracked
    - Clean room protocol tested

phase_6_partners:
  duration: "Week 9"
  deliverables:
    - UID2Connector
    - IHeartConnector
    - RampIDConnector
    - Sync protocols
  success_criteria:
    - All partner APIs integrated
    - Token refresh working
    - Error handling robust

phase_7_integration:
  duration: "Week 10"
  deliverables:
    - FastAPI endpoints
    - Blackboard integration
    - Performance optimization
    - Production deployment
  success_criteria:
    - API latency <20ms p95
    - 99.9% uptime
    - All integration tests passing
```

---

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Match Rate** | >70% | Users matched to unified ID |
| **False Positive Rate** | <1% | Manual audit of random matches |
| **Cross-Device Recognition** | >50% | Users seen on 2+ devices |
| **Resolution Latency** | <20ms p95 | Prometheus metrics |
| **Deterministic Match Rate** | >40% | Of all resolutions |
| **Probabilistic Accuracy** | >85% | Holdout validation |
| **Household Detection Rate** | >60% | Users assigned to households |
| **Profile Completeness** | >0.5 avg | Computed from identity data |
| **Partner Sync Success** | >95% | UID2/RampID/iHeart syncs |
| **Privacy Budget Compliance** | 100% | DP epsilon tracking |

---

## Integration Points

### With #02 Blackboard
- **Reads**: device_ids, session_context, consent_status
- **Writes**: unified_identity, identity_confidence, household_id

### With #08 Signal Aggregation
- **Receives**: behavioral signals, fingerprint, IP hash
- **Provides**: identity context for signal attribution

### With #10 Journey Tracking
- **Provides**: unified identity for journey state tracking
- **Enables**: cross-device journey continuity

### With #17 Privacy/Consent
- **Queries**: consent status before linking
- **Respects**: GDPR/CCPA consent requirements

### With #22 Attribution
- **Provides**: cross-device identity for attribution
- **Enables**: accurate conversion tracking

---

*Enhancement #19 Complete. Cross-Platform Identity Resolution unifies user profiles across devices and platforms for accurate psychological profiling, enabling ADAM's full targeting capabilities.*
