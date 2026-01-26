# ADAM WPP-iHeart Platform Alignment Specification
## Ensuring Architectural Compatibility Between Platform Integrations

**Document Purpose**: Explicitly define the boundaries, shared resources, and integration points between WPP Ad Desk (#28) and iHeart Ad Network Integration to ensure both platforms can operate coherently within ADAM.

**Version**: 1.0  
**Date**: January 2026  
**Status**: Architecture Alignment  
**Classification**: Platform Integration

---

# EXECUTIVE SUMMARY

## The Challenge

ADAM now has two major platform integrations:

| Platform | Integration Spec | Primary Channel | User Scale |
|----------|------------------|-----------------|------------|
| **WPP Ad Desk** | #28 (180KB) | Display, Video, Native | Billions |
| **iHeart** | New (137KB) | Audio (Radio, Podcast) | 175M+ |

Both platforms:
- Need access to the same user psychological profiles
- Use the same mechanism selection logic
- Feed outcomes back to the same learning systems
- Share the same Brand entities

**The Risk**: Without explicit alignment, these integrations could diverge, creating:
- Duplicate user profiles
- Inconsistent mechanism effectiveness data
- Conflicting learning signals
- Maintenance burden

## The Solution

This document establishes:
1. **Shared Resources** - What both platforms use identically
2. **Platform-Specific Resources** - What's unique to each
3. **Interface Contracts** - How platforms interact with shared systems
4. **Conflict Resolution** - What happens when platforms disagree

---

# PART 1: SHARED RESOURCE INVENTORY

## 1.1 Resources Used By Both Platforms

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SHARED RESOURCES                                        │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         USER LAYER                                      │  │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │  │
│   │   │ UserProfile     │  │ Mechanism       │  │ Journey         │        │  │
│   │   │ (Big Five,      │  │ Effectiveness   │  │ State           │        │  │
│   │   │  Reg Focus,     │  │ (per user)      │  │ (decision       │        │  │
│   │   │  Construal)     │  │                 │  │  stage)         │        │  │
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘        │  │
│   │                              ▲                                          │  │
│   │                              │                                          │  │
│   │                   BOTH PLATFORMS READ & WRITE                           │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         BRAND LAYER                                     │  │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │  │
│   │   │ Brand           │  │ Campaign        │  │ Creative        │        │  │
│   │   │ (personality,   │  │ (targeting,     │  │ (copy,          │        │  │
│   │   │  voice)         │  │  budget)        │  │  variants)      │        │  │
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘        │  │
│   │                              ▲                                          │  │
│   │                              │                                          │  │
│   │                   BOTH PLATFORMS READ (usually)                         │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         LEARNING LAYER                                  │  │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │  │
│   │   │ Gradient        │  │ A/B Testing     │  │ Model           │        │  │
│   │   │ Bridge          │  │ Infrastructure  │  │ Monitoring      │        │  │
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘        │  │
│   │                              ▲                                          │  │
│   │                              │                                          │  │
│   │                   BOTH PLATFORMS WRITE                                  │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         FOUNDATIONAL LAYER                              │  │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │  │
│   │   │ Amazon          │  │ Cold Start      │  │ Identity        │        │  │
│   │   │ Archetypes      │  │ Priors          │  │ Resolution      │        │  │
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘        │  │
│   │                              ▲                                          │  │
│   │                              │                                          │  │
│   │                   BOTH PLATFORMS READ                                   │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 Shared Data Models

These Pydantic models are used identically by both platforms:

```python
# =============================================================================
# SHARED USER MODELS - Used by WPP and iHeart
# =============================================================================

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class BigFiveProfile(BaseModel):
    """Personality profile - SHARED."""
    openness: float = Field(ge=0, le=1)
    conscientiousness: float = Field(ge=0, le=1)
    extraversion: float = Field(ge=0, le=1)
    agreeableness: float = Field(ge=0, le=1)
    neuroticism: float = Field(ge=0, le=1)


class RegulatoryFocusState(BaseModel):
    """Regulatory focus - SHARED."""
    promotion_strength: float = Field(ge=0, le=1)
    prevention_strength: float = Field(ge=0, le=1)


class ConstrualLevel(str, Enum):
    """Construal level - SHARED."""
    ABSTRACT = "abstract"
    CONCRETE = "concrete"
    MIXED = "mixed"


class UserDataTier(str, Enum):
    """Data richness tier - SHARED."""
    ANONYMOUS = "anonymous"           # Tier 0: No identity
    IDENTIFIED = "identified"         # Tier 1: Platform ID
    BEHAVIORAL = "behavioral"         # Tier 2: Some history
    PROFILED = "profiled"             # Tier 3: Psychological profile
    RICH = "rich"                     # Tier 4: Full history
    VALIDATED = "validated"           # Tier 5: Survey-validated


class UserProfile(BaseModel):
    """
    Unified user profile - SHARED BY BOTH PLATFORMS.
    
    CRITICAL: This is THE user model. Both WPP and iHeart
    read and write to the SAME user profiles.
    """
    user_id: str                      # ADAM canonical ID
    
    # Psychological profile
    big_five: BigFiveProfile
    regulatory_focus: RegulatoryFocusState
    construal_level: ConstrualLevel
    
    # Mechanism effectiveness (learned)
    mechanism_receptivity: Dict[str, float] = Field(default_factory=dict)
    
    # Profile metadata
    data_tier: UserDataTier
    profile_confidence: float = Field(ge=0, le=1)
    profile_source: str               # "amazon_archetype", "iheart_listening", "wpp_behavior"
    
    # Platform identities (for cross-platform matching)
    platform_ids: Dict[str, str] = Field(default_factory=dict)
    # e.g., {"iheart": "ih_123", "wpp": "wpp_456", "uid2": "uid2_789"}
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


# =============================================================================
# SHARED BRAND MODELS - Used by WPP and iHeart
# =============================================================================

class BrandPersonality(BaseModel):
    """Aaker's brand personality dimensions - SHARED."""
    sincerity: float = Field(ge=0, le=1)
    excitement: float = Field(ge=0, le=1)
    competence: float = Field(ge=0, le=1)
    sophistication: float = Field(ge=0, le=1)
    ruggedness: float = Field(ge=0, le=1)


class Brand(BaseModel):
    """
    Brand entity - SHARED BY BOTH PLATFORMS.
    
    The same brand (e.g., Nike) has ONE definition used
    for both WPP display campaigns and iHeart audio campaigns.
    """
    brand_id: str
    name: str
    
    # Psychological profile
    personality: BrandPersonality
    regulatory_focus_alignment: str   # "promotion", "prevention", "neutral"
    
    # Voice guidelines (used by Copy Generation)
    tone: str
    vocabulary_level: str
    formality: str
    
    # Constraints
    prohibited_words: List[str] = Field(default_factory=list)
    competitor_mentions: str = "never"
    
    # Mechanism affinities
    mechanism_affinities: Dict[str, float] = Field(default_factory=dict)
    
    # Category associations
    primary_category: str
    categories: List[str] = Field(default_factory=list)


# =============================================================================
# SHARED MECHANISM MODELS - Used by WPP and iHeart
# =============================================================================

class MechanismEffectiveness(BaseModel):
    """
    Mechanism effectiveness for a user - SHARED.
    
    Both platforms contribute to and read from this.
    """
    mechanism_id: str
    success_rate: float               # Bayesian posterior
    confidence: float                 # Based on evidence count
    evidence_count: int
    
    # Bayesian parameters
    alpha: float = 1.0                # Successes
    beta: float = 1.0                 # Failures
    
    # Platform contribution tracking
    wpp_evidence_count: int = 0
    iheart_evidence_count: int = 0
```

## 1.3 Shared Services

These services are called by both platforms:

| Service | Interface | WPP Uses For | iHeart Uses For |
|---------|-----------|--------------|-----------------|
| `IdentityResolutionService` | `resolve(platform, id)` | UID2/RampID → ADAM | iHeart ID → ADAM |
| `UserProfileService` | `get_profile(user_id)` | Display targeting | Audio targeting |
| `ColdStartService` | `bootstrap(context)` | New display users | New audio users |
| `MechanismSelectionService` | `select(profile, brand)` | Display creative | Audio copy |
| `CopyGenerationService` | `generate(request)` | Display copy | Audio copy (SSML) |
| `GradientBridge` | `propagate(signal)` | Display outcomes | Audio outcomes |
| `ABTestingService` | `assign(user, experiment)` | Display experiments | Audio experiments |

---

# PART 2: PLATFORM-SPECIFIC RESOURCES

## 2.1 WPP-Specific Resources

```python
# =============================================================================
# WPP-SPECIFIC MODELS - Not used by iHeart
# =============================================================================

class WPPInventorySlot(BaseModel):
    """WPP display/video inventory - WPP ONLY."""
    slot_id: str
    publisher_id: str
    placement_id: str
    
    # Display-specific
    format: str                       # "display", "video", "native"
    size: Optional[str] = None        # "300x250", "728x90"
    viewability_score: float
    
    # Supply path
    ssp_id: str
    exchange_path: List[str]


class WPPBidRequest(BaseModel):
    """WPP OpenRTB bid request - WPP ONLY."""
    request_id: str
    impression_id: str
    
    # User
    user_id: Optional[str]
    uid2_token: Optional[str]
    
    # Inventory
    inventory: WPPInventorySlot
    
    # Auction
    floor_price: float
    auction_type: int


class WPPSupplyPath(BaseModel):
    """Supply path optimization - WPP ONLY."""
    path_id: str
    publisher_id: str
    ssp_chain: List[str]
    
    # Quality metrics
    viewability_avg: float
    fraud_rate: float
    latency_ms: float
    
    # Cost metrics
    effective_cpm: float
    fee_percentage: float
```

## 2.2 iHeart-Specific Resources

```python
# =============================================================================
# iHEART-SPECIFIC MODELS - Not used by WPP
# =============================================================================

class Station(BaseModel):
    """Radio station - iHEART ONLY."""
    station_id: str
    call_sign: str
    format: str                       # "CHR", "Country", etc.
    market: str
    
    # Psychographic profile
    psychographic_profile: StationPsychographicProfile


class Track(BaseModel):
    """Music track - iHEART ONLY."""
    track_id: str
    artist_id: str
    
    # Audio features
    energy: float
    valence: float
    tempo: float
    
    # Psychological signals
    mechanism_affinities: Dict[str, float]


class iHeartAdSlot(BaseModel):
    """Audio ad slot - iHEART ONLY."""
    slot_id: str
    station_id: Optional[str]
    podcast_id: Optional[str]
    
    # Audio-specific
    position: str                     # "pre", "mid", "post"
    duration_seconds: int
    
    # Context
    preceding_content_type: str       # "music", "talk"
    preceding_energy: Optional[float]


class AudioParameters(BaseModel):
    """Audio delivery parameters - iHEART ONLY."""
    voice_id: str
    speaking_rate: float
    pitch_adjustment: float
    energy_level: float
    ssml: str
```

## 2.3 Resource Ownership Matrix

| Resource | Owner | WPP Access | iHeart Access |
|----------|-------|------------|---------------|
| `UserProfile` | Shared | Read/Write | Read/Write |
| `Brand` | Shared | Read | Read |
| `Campaign` | Shared | Read/Write | Read/Write |
| `Creative` | Per-Platform | Write own | Write own |
| `WPPInventorySlot` | WPP | Read/Write | None |
| `Station` | iHeart | None | Read/Write |
| `Track` | iHeart | None | Read |
| `iHeartAdSlot` | iHeart | None | Read/Write |
| `MechanismEffectiveness` | Shared | Read/Write | Read/Write |
| `JourneyState` | Shared | Read/Write | Read/Write |
| `AmazonArchetype` | Shared | Read | Read |

---

# PART 3: CROSS-PLATFORM INTEGRATION POINTS

## 3.1 Identity Resolution

**Challenge**: A user might interact with both WPP display ads and iHeart audio ads.

**Solution**: Single canonical ADAM ID with platform mappings.

```python
# =============================================================================
# CROSS-PLATFORM IDENTITY RESOLUTION
# =============================================================================

class CrossPlatformIdentityService:
    """
    Resolve identities across WPP and iHeart.
    
    RULE: One canonical ADAM ID per actual human.
    Both platforms contribute to and read from the same profile.
    """
    
    async def resolve_to_canonical(
        self,
        platform: str,
        platform_id: str,
        hints: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Resolve any platform ID to canonical ADAM ID.
        
        Args:
            platform: "wpp", "iheart", "uid2", etc.
            platform_id: The platform's ID for this user
            hints: Additional identity hints (e.g., hashed email)
        
        Returns:
            Canonical ADAM user ID
        """
        # Check if this platform ID is already linked
        existing = await self.graph.find_user_by_platform_id(platform, platform_id)
        
        if existing:
            return existing.user_id
        
        # Try to match via hints (e.g., same UID2 token)
        if hints:
            for hint_platform, hint_id in hints.items():
                matched = await self.graph.find_user_by_platform_id(
                    hint_platform, hint_id
                )
                if matched:
                    # Link this new platform ID to existing user
                    await self.graph.link_platform_id(
                        user_id=matched.user_id,
                        platform=platform,
                        platform_id=platform_id
                    )
                    return matched.user_id
        
        # Create new canonical ID
        new_user_id = f"adam:{uuid.uuid4()}"
        await self.graph.create_user(new_user_id, platform, platform_id)
        
        return new_user_id
    
    async def get_cross_platform_profile(
        self,
        user_id: str
    ) -> UserProfile:
        """
        Get unified profile combining signals from all platforms.
        """
        profile = await self.graph.get_user_profile(user_id)
        
        # Profile already contains signals from both platforms
        # because both platforms write to the same profile
        
        return profile
```

## 3.2 Mechanism Effectiveness Merging

**Challenge**: WPP and iHeart both learn about mechanism effectiveness. How to combine?

**Solution**: Bayesian updating with platform-weighted evidence.

```python
# =============================================================================
# CROSS-PLATFORM MECHANISM LEARNING
# =============================================================================

class CrossPlatformMechanismLearner:
    """
    Combine mechanism effectiveness signals from both platforms.
    
    KEY INSIGHT: Different platforms may have different signal quality.
    - WPP display: High volume, lower intent signal
    - iHeart audio: Lower volume, higher engagement signal
    """
    
    # Platform evidence quality weights
    PLATFORM_WEIGHTS = {
        "wpp": 1.0,      # Baseline
        "iheart": 1.5,   # Higher weight (audio engagement is higher intent)
    }
    
    async def update_mechanism_effectiveness(
        self,
        user_id: str,
        mechanism_id: str,
        outcome: bool,
        platform: str,
        context: Dict[str, Any]
    ) -> MechanismEffectiveness:
        """
        Update mechanism effectiveness with platform-weighted evidence.
        """
        current = await self.graph.get_mechanism_effectiveness(
            user_id, mechanism_id
        )
        
        if not current:
            current = MechanismEffectiveness(
                mechanism_id=mechanism_id,
                success_rate=0.5,
                confidence=0.3,
                evidence_count=0,
                alpha=1.0,
                beta=1.0
            )
        
        # Get platform weight
        weight = self.PLATFORM_WEIGHTS.get(platform, 1.0)
        
        # Bayesian update with weighted evidence
        if outcome:
            current.alpha += weight
        else:
            current.beta += weight
        
        # Update derived fields
        current.success_rate = current.alpha / (current.alpha + current.beta)
        current.confidence = 1 - (1 / (1 + current.alpha + current.beta))
        current.evidence_count += 1
        
        # Track platform contributions
        if platform == "wpp":
            current.wpp_evidence_count += 1
        elif platform == "iheart":
            current.iheart_evidence_count += 1
        
        # Persist
        await self.graph.update_mechanism_effectiveness(user_id, current)
        
        return current
```

## 3.3 Journey State Synchronization

**Challenge**: User might see WPP display ad, then hear iHeart audio ad. Journey state must be consistent.

**Solution**: Single journey state updated by both platforms.

```python
# =============================================================================
# CROSS-PLATFORM JOURNEY STATE
# =============================================================================

class CrossPlatformJourneyService:
    """
    Maintain consistent journey state across platforms.
    
    RULE: Journey state is user-level, not platform-level.
    Ad exposure on ANY platform can advance the journey.
    """
    
    async def update_journey_state(
        self,
        user_id: str,
        event_type: str,
        platform: str,
        context: Dict[str, Any]
    ) -> JourneyState:
        """
        Update journey state from any platform event.
        """
        current_state = await self.graph.get_journey_state(user_id)
        
        # Determine state transition
        new_state = self._calculate_transition(
            current_state=current_state.current_state if current_state else "unaware",
            event_type=event_type,
            platform=platform,
            context=context
        )
        
        # Update journey
        if current_state:
            current_state.current_state = new_state
            current_state.updated_at = datetime.utcnow()
            current_state.last_platform = platform
        else:
            current_state = JourneyState(
                user_id=user_id,
                current_state=new_state,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_platform=platform
            )
        
        await self.graph.update_journey_state(current_state)
        
        return current_state
    
    def _calculate_transition(
        self,
        current_state: str,
        event_type: str,
        platform: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Calculate state transition based on event.
        
        State machine is the same regardless of platform.
        """
        # Standard journey states
        TRANSITIONS = {
            ("unaware", "ad_impression"): "aware",
            ("aware", "ad_impression"): "considering",
            ("aware", "click"): "considering",
            ("considering", "ad_impression"): "considering",
            ("considering", "click"): "intending",
            ("considering", "conversion"): "converted",
            ("intending", "conversion"): "converted",
            ("converted", "ad_impression"): "loyal",
        }
        
        transition_key = (current_state, event_type)
        return TRANSITIONS.get(transition_key, current_state)
```

---

# PART 4: CONFLICT RESOLUTION

## 4.1 Potential Conflicts and Resolutions

| Conflict | Scenario | Resolution |
|----------|----------|------------|
| **Profile Divergence** | WPP thinks user is promotion-focused, iHeart thinks prevention | Weighted average by confidence |
| **Mechanism Disagreement** | Loss aversion works on WPP, fails on iHeart | Track per-platform effectiveness, use platform-specific |
| **Journey State Race** | Both platforms update simultaneously | Use timestamp-based last-write-wins with merge |
| **Brand Voice Mismatch** | Display copy and audio copy feel different | Enforce same brand guidelines, different execution |
| **Outcome Attribution** | User sees WPP ad, converts via iHeart | Multi-touch attribution with position weighting |

## 4.2 Profile Divergence Resolution

```python
async def resolve_profile_divergence(
    self,
    user_id: str
) -> UserProfile:
    """
    Resolve divergent profile signals from different platforms.
    
    Uses confidence-weighted averaging.
    """
    profile = await self.graph.get_user_profile(user_id)
    
    # Get platform-specific evidence counts
    wpp_evidence = profile.platform_evidence.get("wpp", {})
    iheart_evidence = profile.platform_evidence.get("iheart", {})
    
    # For each trait, calculate weighted average
    for trait in ["openness", "conscientiousness", "extraversion", 
                  "agreeableness", "neuroticism"]:
        
        wpp_value = wpp_evidence.get(trait, {}).get("value")
        wpp_conf = wpp_evidence.get(trait, {}).get("confidence", 0)
        
        iheart_value = iheart_evidence.get(trait, {}).get("value")
        iheart_conf = iheart_evidence.get(trait, {}).get("confidence", 0)
        
        if wpp_value is not None and iheart_value is not None:
            # Weighted average by confidence
            total_conf = wpp_conf + iheart_conf
            if total_conf > 0:
                merged_value = (
                    (wpp_value * wpp_conf) + (iheart_value * iheart_conf)
                ) / total_conf
                
                setattr(profile.big_five, trait, merged_value)
    
    return profile
```

---

# PART 5: IMPLEMENTATION CHECKLIST

## 5.1 Pre-Implementation Validation

Before implementing either platform integration:

```bash
# Shared resource checklist
[ ] UserProfile model defined in shared location
[ ] Brand model defined in shared location
[ ] MechanismEffectiveness model defined in shared location
[ ] JourneyState model defined in shared location
[ ] IdentityResolutionService interface defined
[ ] GradientBridge signal routing defined

# WPP-specific checklist
[ ] WPPInventorySlot model defined
[ ] WPPBidRequest model defined
[ ] WPP adapter layer implemented

# iHeart-specific checklist
[ ] Station model defined
[ ] Track model defined
[ ] iHeartAdSlot model defined
[ ] AudioParameters model defined
[ ] Audio copy generation implemented
```

## 5.2 Integration Testing Requirements

```python
# =============================================================================
# CROSS-PLATFORM INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestCrossPlatformIntegration:
    """
    Test that WPP and iHeart work together correctly.
    """
    
    async def test_user_profile_shared(self):
        """Same user accessible from both platforms."""
        # Create user via WPP
        wpp_user_id = await wpp_service.create_user("wpp_123")
        
        # Link to iHeart
        await identity_service.link_platform_id(
            user_id=wpp_user_id,
            platform="iheart",
            platform_id="ih_456"
        )
        
        # Verify same profile
        wpp_profile = await wpp_service.get_profile(wpp_user_id)
        iheart_profile = await iheart_service.get_profile_by_iheart_id("ih_456")
        
        assert wpp_profile.user_id == iheart_profile.user_id
    
    async def test_mechanism_effectiveness_merged(self):
        """Mechanism effectiveness combines both platforms."""
        user_id = "test_user"
        mechanism = "social_proof"
        
        # WPP outcome
        await gradient_bridge.process_outcome(
            user_id=user_id,
            mechanism=mechanism,
            outcome=True,
            platform="wpp"
        )
        
        # iHeart outcome
        await gradient_bridge.process_outcome(
            user_id=user_id,
            mechanism=mechanism,
            outcome=True,
            platform="iheart"
        )
        
        # Verify combined
        effectiveness = await mechanism_service.get_effectiveness(
            user_id, mechanism
        )
        
        assert effectiveness.wpp_evidence_count == 1
        assert effectiveness.iheart_evidence_count == 1
        assert effectiveness.evidence_count == 2
    
    async def test_journey_state_synchronized(self):
        """Journey state updates from both platforms."""
        user_id = "test_user"
        
        # WPP impression (unaware → aware)
        await journey_service.record_event(
            user_id=user_id,
            event_type="ad_impression",
            platform="wpp"
        )
        
        state1 = await journey_service.get_state(user_id)
        assert state1.current_state == "aware"
        
        # iHeart impression (aware → considering)
        await journey_service.record_event(
            user_id=user_id,
            event_type="ad_impression",
            platform="iheart"
        )
        
        state2 = await journey_service.get_state(user_id)
        assert state2.current_state == "considering"
```

---

# PART 6: SUMMARY

## 6.1 Key Alignment Decisions

| Decision | Rationale |
|----------|-----------|
| **Single UserProfile** | Users are humans, not platforms. One profile per person. |
| **Single Brand model** | Brands exist independent of channels. Same Nike everywhere. |
| **Shared Gradient Bridge** | Learning should be unified. Insights from display help audio. |
| **Platform-specific Creative** | Display and audio are fundamentally different executions. |
| **Platform-weighted evidence** | Audio engagement is higher intent than display impressions. |

## 6.2 Implementation Priority

1. **First**: Implement shared models in `/adam/shared/models/`
2. **Second**: Implement identity resolution with cross-platform linking
3. **Third**: Implement WPP adapter (display-specific)
4. **Fourth**: Implement iHeart adapter (audio-specific)
5. **Fifth**: Implement cross-platform integration tests

## 6.3 Verification Checklist

| Item | Status |
|------|--------|
| Shared models defined | ✅ |
| Platform-specific models defined | ✅ |
| Identity resolution specified | ✅ |
| Mechanism merging specified | ✅ |
| Journey synchronization specified | ✅ |
| Conflict resolution specified | ✅ |
| Integration tests defined | ✅ |

---

**END OF WPP-iHEART PLATFORM ALIGNMENT SPECIFICATION**
