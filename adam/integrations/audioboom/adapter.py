"""
Audioboom Platform Adapter
============================

Implements the ADAM ↔ Audioboom integration:
- Show psychological profiling → Audioboom Showcase targeting
- Brand-show matching → Audioboom Marketplace
- Host-read briefings → Audioboom host portal
- Adaptive Ad intelligence → Real-time ad insertion
- Outcome reporting → ADAM learning loop

Audioboom products mapped to ADAM:
- Showcase: Psychologically-targeted ad marketplace
- Adaptive Ads: Dynamic ad insertion with ADAM intelligence
- Host-read: Briefing-powered host endorsements
- Video Podcasts: Visual + audio psychological targeting
"""

import logging
from typing import Any, Dict, List, Optional

from adam.integrations.base.adapter import (
    BasePlatformAdapter,
    AdapterMode,
    PlatformCredentials,
    SyncedSegment,
    SyncedCreative,
    CampaignConfig,
    CampaignStatus,
    PlatformCampaign,
    PlatformMetrics,
)

logger = logging.getLogger(__name__)


class AudioboomAdapter(BasePlatformAdapter):
    """
    Audioboom platform adapter.

    In DEMO mode: simulates all Audioboom API responses.
    In PRODUCTION mode: calls Audioboom's API.
    """

    PLATFORM_NAME = "audioboom"
    SUPPORTED_FORMATS = ["audio", "host_read", "adaptive", "video_podcast"]

    # Audioboom API base
    API_BASE = "https://api.audioboom.com/v2"

    def __init__(
        self,
        credentials: Optional[PlatformCredentials] = None,
        mode: AdapterMode = AdapterMode.DEMO,
    ):
        super().__init__(credentials, mode)

    # =========================================================================
    # DEMO OVERRIDES
    # =========================================================================

    def _demo_sync_segment(self, segment: Any) -> SyncedSegment:
        seg_id = getattr(segment, "segment_id", "unknown")
        return SyncedSegment(
            adam_segment_id=seg_id,
            platform_segment_id=f"ab_showcase_{seg_id}",
            platform_name="audioboom",
            size=getattr(segment, "estimated_reach", 50000),
            status="active",
            last_synced="2026-02-10T00:00:00Z",
        )

    def _demo_get_metrics(self, campaign_id: str) -> PlatformMetrics:
        """Generate realistic Audioboom/podcast metrics."""
        import random
        impressions = random.randint(50000, 300000)
        # Podcast ads have higher CTR
        ctr = random.uniform(0.012, 0.035)
        clicks = int(impressions * ctr)
        conv_rate = random.uniform(0.010, 0.028)
        conversions = int(impressions * conv_rate)
        # Podcast CPM is higher
        cpm = random.uniform(15.0, 30.0)
        spend = impressions * cpm / 1000
        return PlatformMetrics(
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            spend=round(spend, 2),
            cpm=round(cpm, 2),
            ctr=round(ctr, 4),
            conversion_rate=round(conv_rate, 4),
            cpa=round(spend / conversions, 2) if conversions > 0 else 0,
            roas=round(conversions * 50 / spend, 2) if spend > 0 else 0,
        )

    # =========================================================================
    # PRODUCTION IMPLEMENTATIONS
    # =========================================================================

    async def _sync_segment_impl(self, segment: Any) -> SyncedSegment:
        """Sync segment to Audioboom Showcase."""
        # Audioboom uses a REST API
        seg_id = getattr(segment, "segment_id", "unknown")
        payload = {
            "name": f"ADAM: {getattr(segment, 'name', 'Unknown')}",
            "description": getattr(segment, "description", ""),
            "targeting": {
                "psychological_profile": getattr(segment, "defining_constructs", {}),
            },
        }

        result = await self._api_request("POST", "/showcase/audiences", payload)
        return SyncedSegment(
            adam_segment_id=seg_id,
            platform_segment_id=result.get("id", ""),
            platform_name="audioboom",
            size=result.get("estimated_size", 0),
            status="active",
        )

    async def _upload_creative_impl(
        self,
        creative_spec: Any,
        segment_id: str,
    ) -> SyncedCreative:
        """Upload creative brief to Audioboom."""
        import uuid
        creative_id = f"adam_ab_cr_{uuid.uuid4().hex[:8]}"
        payload = {
            "type": "host_read_briefing",
            "brief": creative_spec if isinstance(creative_spec, dict) else {},
            "segment_id": segment_id,
        }
        result = await self._api_request("POST", "/creatives", payload)
        return SyncedCreative(
            adam_creative_id=creative_id,
            platform_creative_id=result.get("id", creative_id),
            platform_name="audioboom",
            format="host_read",
            status="active",
        )

    async def _create_campaign_impl(self, config: CampaignConfig) -> PlatformCampaign:
        """Create campaign on Audioboom."""
        payload = {
            "name": config.name,
            "budget": config.budget_total,
            "daily_budget": config.budget_daily,
            "audience_ids": config.segment_ids,
        }
        result = await self._api_request("POST", "/campaigns", payload)
        campaign = PlatformCampaign(
            campaign_id=result.get("id", ""),
            platform_name="audioboom",
            config=config,
            status=CampaignStatus.DRAFT,
        )
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    async def _get_metrics_impl(self, campaign_id: str) -> PlatformMetrics:
        """Get metrics from Audioboom."""
        result = await self._api_request("GET", f"/campaigns/{campaign_id}/metrics")
        return PlatformMetrics(
            impressions=result.get("impressions", 0),
            clicks=result.get("clicks", 0),
            conversions=result.get("conversions", 0),
            spend=result.get("spend", 0.0),
            cpm=result.get("cpm", 0.0),
            ctr=result.get("ctr", 0.0),
            conversion_rate=result.get("conversion_rate", 0.0),
            cpa=result.get("cpa", 0.0),
        )

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request to Audioboom."""
        if not self._credentials or not self._credentials.api_key:
            raise ValueError("Audioboom API key not configured")

        try:
            import httpx
            url = f"{self.API_BASE}{endpoint}"
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {self._credentials.api_key}"},
                        timeout=30.0,
                    )
                else:
                    response = await client.post(
                        url,
                        json=data,
                        headers={
                            "Authorization": f"Bearer {self._credentials.api_key}",
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )
                response.raise_for_status()
                return response.json()
        except ImportError:
            logger.error("httpx not installed")
            raise
        except Exception as e:
            logger.error(f"Audioboom API error: {e}")
            raise


_adapter: Optional[AudioboomAdapter] = None


def get_audioboom_adapter(
    mode: AdapterMode = AdapterMode.DEMO,
) -> AudioboomAdapter:
    global _adapter
    if _adapter is None:
        _adapter = AudioboomAdapter(mode=mode)
    return _adapter
