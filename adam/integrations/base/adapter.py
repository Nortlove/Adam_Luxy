"""
Platform Adapter Framework
============================

Abstract base adapter for DSP/SSP platform integrations.
Provides dual-mode operation:
    - DEMO mode: simulated responses for presentations/testing
    - PRODUCTION mode: real API calls to platform

Each platform adapter (StackAdapt, Audioboom, etc.) extends this base
and implements platform-specific methods.

The adapter framework handles:
- Authentication and API client management
- Segment sync (ADAM segments → platform audience lists)
- Creative upload (ADAM creative specs → platform creative objects)
- Campaign management (create, update, pause, resume)
- Reporting (platform metrics → ADAM outcome signals)
- Mode switching (demo ↔ production)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class AdapterMode(Enum):
    DEMO = "demo"
    PRODUCTION = "production"


class CampaignStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PlatformCredentials:
    """Platform API credentials (stored securely, never in memory longer than needed)."""
    api_key: str = ""
    api_secret: str = ""
    account_id: str = ""
    environment: str = "sandbox"  # "sandbox" or "production"


@dataclass
class SyncedSegment:
    """A segment that has been synced to a platform."""
    adam_segment_id: str
    platform_segment_id: str
    platform_name: str
    size: int = 0
    status: str = "active"
    last_synced: str = ""


@dataclass
class SyncedCreative:
    """A creative that has been uploaded to a platform."""
    adam_creative_id: str
    platform_creative_id: str
    platform_name: str
    format: str = ""  # "native", "display", "video", "audio"
    status: str = "active"


@dataclass
class CampaignConfig:
    """Campaign configuration for platform launch."""
    name: str
    segment_ids: List[str] = field(default_factory=list)
    creative_ids: List[str] = field(default_factory=list)
    budget_daily: float = 0.0
    budget_total: float = 0.0
    start_date: str = ""
    end_date: str = ""
    targeting: Dict[str, Any] = field(default_factory=dict)
    bid_strategy: str = "cpa_target"
    goal_cpa: float = 0.0


@dataclass
class PlatformCampaign:
    """A campaign on a platform."""
    campaign_id: str
    platform_name: str
    config: CampaignConfig = field(default_factory=CampaignConfig)
    status: CampaignStatus = CampaignStatus.DRAFT
    performance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformMetrics:
    """Performance metrics from a platform."""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    cpm: float = 0.0
    ctr: float = 0.0
    conversion_rate: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0


# =============================================================================
# ABSTRACT BASE ADAPTER
# =============================================================================

class BasePlatformAdapter(ABC):
    """
    Abstract base class for DSP/SSP platform adapters.

    Subclasses implement platform-specific API calls.
    The base class handles mode switching, error handling, and
    the ADAM ↔ platform data translation layer.
    """

    PLATFORM_NAME: str = "base"
    SUPPORTED_FORMATS: List[str] = []

    def __init__(
        self,
        credentials: Optional[PlatformCredentials] = None,
        mode: AdapterMode = AdapterMode.DEMO,
    ):
        self._credentials = credentials
        self._mode = mode
        self._synced_segments: Dict[str, SyncedSegment] = {}
        self._synced_creatives: Dict[str, SyncedCreative] = {}
        self._campaigns: Dict[str, PlatformCampaign] = {}
        self._initialized = False

    @property
    def mode(self) -> AdapterMode:
        return self._mode

    @mode.setter
    def mode(self, value: AdapterMode):
        self._mode = value
        logger.info(f"{self.PLATFORM_NAME} adapter switched to {value.value} mode")

    @property
    def is_demo(self) -> bool:
        return self._mode == AdapterMode.DEMO

    # =========================================================================
    # SEGMENT SYNC
    # =========================================================================

    async def sync_segment(
        self,
        segment: Any,  # PsychologicalSegment
    ) -> SyncedSegment:
        """
        Sync an ADAM psychological segment to the platform.

        In DEMO mode: returns a simulated sync result.
        In PRODUCTION mode: calls the platform API.
        """
        if self.is_demo:
            return self._demo_sync_segment(segment)
        return await self._sync_segment_impl(segment)

    async def sync_all_segments(
        self,
        segments: List[Any],
    ) -> List[SyncedSegment]:
        """Sync all segments to the platform."""
        results = []
        for segment in segments:
            synced = await self.sync_segment(segment)
            results.append(synced)
            self._synced_segments[synced.adam_segment_id] = synced
        return results

    # =========================================================================
    # CREATIVE UPLOAD
    # =========================================================================

    async def upload_creative(
        self,
        creative_spec: Any,  # CreativeSpec or PersonalityCreativeProfile
        segment_id: str = "",
    ) -> SyncedCreative:
        """
        Upload an ADAM creative to the platform.

        In DEMO mode: returns a simulated upload result.
        In PRODUCTION mode: calls the platform API.
        """
        if self.is_demo:
            return self._demo_upload_creative(creative_spec, segment_id)
        return await self._upload_creative_impl(creative_spec, segment_id)

    # =========================================================================
    # CAMPAIGN MANAGEMENT
    # =========================================================================

    async def create_campaign(
        self,
        config: CampaignConfig,
    ) -> PlatformCampaign:
        """Create a campaign on the platform."""
        if self.is_demo:
            return self._demo_create_campaign(config)
        return await self._create_campaign_impl(config)

    async def get_campaign_metrics(
        self,
        campaign_id: str,
    ) -> PlatformMetrics:
        """Get performance metrics for a campaign."""
        if self.is_demo:
            return self._demo_get_metrics(campaign_id)
        return await self._get_metrics_impl(campaign_id)

    # =========================================================================
    # OUTCOME REPORTING → ADAM LEARNING
    # =========================================================================

    async def report_outcomes(
        self,
        campaign_id: str,
    ) -> Dict[str, Any]:
        """
        Pull outcomes from the platform and feed into ADAM's learning loop.

        This closes the loop: Platform Metrics → ADAM Outcome Handler →
        Theory Learner → Updated Graph Edge Strengths → Better Predictions.
        """
        metrics = await self.get_campaign_metrics(campaign_id)

        # Convert platform metrics to ADAM outcome format
        outcomes = []
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            for seg_id in campaign.config.segment_ids:
                outcomes.append({
                    "segment_id": seg_id,
                    "impressions": metrics.impressions,
                    "clicks": metrics.clicks,
                    "conversions": metrics.conversions,
                    "ctr": metrics.ctr,
                    "conversion_rate": metrics.conversion_rate,
                    "cpa": metrics.cpa,
                })

        return {
            "campaign_id": campaign_id,
            "metrics": {
                "impressions": metrics.impressions,
                "clicks": metrics.clicks,
                "conversions": metrics.conversions,
                "cpa": metrics.cpa,
                "roas": metrics.roas,
            },
            "outcomes_for_learning": outcomes,
        }

    # =========================================================================
    # DEMO MODE IMPLEMENTATIONS
    # =========================================================================

    def _demo_sync_segment(self, segment: Any) -> SyncedSegment:
        seg_id = getattr(segment, "segment_id", "unknown")
        return SyncedSegment(
            adam_segment_id=seg_id,
            platform_segment_id=f"{self.PLATFORM_NAME}_seg_{seg_id}",
            platform_name=self.PLATFORM_NAME,
            size=getattr(segment, "estimated_reach", 10000),
            status="active",
            last_synced="2026-02-10T00:00:00Z",
        )

    def _demo_upload_creative(
        self,
        creative_spec: Any,
        segment_id: str,
    ) -> SyncedCreative:
        import uuid
        creative_id = f"cr_{uuid.uuid4().hex[:8]}"
        return SyncedCreative(
            adam_creative_id=creative_id,
            platform_creative_id=f"{self.PLATFORM_NAME}_{creative_id}",
            platform_name=self.PLATFORM_NAME,
            format="native",
            status="active",
        )

    def _demo_create_campaign(self, config: CampaignConfig) -> PlatformCampaign:
        import uuid
        campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
        campaign = PlatformCampaign(
            campaign_id=campaign_id,
            platform_name=self.PLATFORM_NAME,
            config=config,
            status=CampaignStatus.DRAFT,
        )
        self._campaigns[campaign_id] = campaign
        return campaign

    def _demo_get_metrics(self, campaign_id: str) -> PlatformMetrics:
        """Generate realistic demo metrics."""
        import random
        impressions = random.randint(50000, 200000)
        ctr = random.uniform(0.008, 0.025)
        clicks = int(impressions * ctr)
        conv_rate = random.uniform(0.008, 0.020)
        conversions = int(impressions * conv_rate)
        spend = impressions * random.uniform(0.005, 0.015)
        return PlatformMetrics(
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            spend=round(spend, 2),
            cpm=round(spend / impressions * 1000, 2) if impressions > 0 else 0,
            ctr=round(ctr, 4),
            conversion_rate=round(conv_rate, 4),
            cpa=round(spend / conversions, 2) if conversions > 0 else 0,
            roas=round(conversions * 50 / spend, 2) if spend > 0 else 0,
        )

    # =========================================================================
    # ABSTRACT METHODS (implemented by platform-specific adapters)
    # =========================================================================

    @abstractmethod
    async def _sync_segment_impl(self, segment: Any) -> SyncedSegment:
        """Platform-specific segment sync."""
        ...

    @abstractmethod
    async def _upload_creative_impl(
        self, creative_spec: Any, segment_id: str
    ) -> SyncedCreative:
        """Platform-specific creative upload."""
        ...

    @abstractmethod
    async def _create_campaign_impl(self, config: CampaignConfig) -> PlatformCampaign:
        """Platform-specific campaign creation."""
        ...

    @abstractmethod
    async def _get_metrics_impl(self, campaign_id: str) -> PlatformMetrics:
        """Platform-specific metrics retrieval."""
        ...
