# =============================================================================
# ADAM Enhancement #19: Cross-Platform Identity Resolution
# Location: adam/identity/__init__.py
# =============================================================================

"""
CROSS-PLATFORM IDENTITY RESOLUTION

Enterprise-Grade Identity Resolution System for Cross-Platform User Tracking

Core Capabilities:
1. IDENTIFIER MANAGEMENT
   - 20+ identifier types with classification
   - Deterministic (email, phone, login)
   - Device-level (IDFA/GAID, cookies, fingerprint)
   - Industry standard (UID2, RampID, ID5)

2. MATCHING STRATEGIES
   - Deterministic: 100% confidence exact matches
   - Probabilistic: ML-based feature scoring
   - Household: Shared signals resolution

3. IDENTITY GRAPH
   - Unified identity per real person
   - Cross-device linking
   - Temporal persistence tracking

4. PRIVACY CONTROLS
   - Consent-aware processing
   - Bloom filter secure matching
   - Differential privacy support

Expected Performance:
- Resolution latency: <20ms p99
- Match rate: 65-75% for returning users
- False positive rate: <0.1%
- Cross-device coverage: 40% of users
"""

# Models
from adam.identity.models import (
    # Identifiers
    IdentifierType,
    MatchConfidence,
    IdentifierSource,
    Identifier,
    IdentityLink,
    
    # Identity
    UnifiedIdentity,
    MatchResult,
    
    # Household
    HouseholdSignals,
    HouseholdMember,
    Household,
)

# Matching
from adam.identity.matching import (
    DeterministicMatcher,
    ProbabilisticMatcher,
    MatchFeatures,
)

# Service
from adam.identity.service import (
    IdentityResolver,
    get_identity_resolver,
)

# Graph
from adam.identity.graph import (
    Neo4jIdentityGraph,
    get_identity_graph,
    IDENTITY_GRAPH_SCHEMA,
)

# Privacy
from adam.identity.privacy import (
    BloomFilter,
    BloomFilterMatcher,
    BloomFilterConfig,
    DifferentialPrivacyEngine,
    get_differential_privacy_engine,
    PrivacyBudget,
)

# Household
from adam.identity.household import (
    HouseholdResolver,
    get_household_resolver,
)

# Partners
from adam.identity.partners import (
    PartnerConnector,
    PartnerConfig,
    PartnerSyncResult,
    UID2Connector,
    get_uid2_connector,
    IHeartConnector,
    get_iheart_connector,
    RampIDConnector,
    get_rampid_connector,
)

__all__ = [
    # Identifiers
    "IdentifierType",
    "MatchConfidence",
    "IdentifierSource",
    "Identifier",
    "IdentityLink",
    
    # Identity
    "UnifiedIdentity",
    "MatchResult",
    
    # Household
    "HouseholdSignals",
    "HouseholdMember",
    "Household",
    
    # Matching
    "DeterministicMatcher",
    "ProbabilisticMatcher",
    "MatchFeatures",
    
    # Service
    "IdentityResolver",
    "get_identity_resolver",
    
    # Graph
    "Neo4jIdentityGraph",
    "get_identity_graph",
    "IDENTITY_GRAPH_SCHEMA",
    
    # Privacy
    "BloomFilter",
    "BloomFilterMatcher",
    "BloomFilterConfig",
    "DifferentialPrivacyEngine",
    "get_differential_privacy_engine",
    "PrivacyBudget",
    
    # Household
    "HouseholdResolver",
    "get_household_resolver",
    
    # Partners
    "PartnerConnector",
    "PartnerConfig",
    "PartnerSyncResult",
    "UID2Connector",
    "get_uid2_connector",
    "IHeartConnector",
    "get_iheart_connector",
    "RampIDConnector",
    "get_rampid_connector",
]
