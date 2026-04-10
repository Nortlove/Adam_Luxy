"""
StackAdapt Platform Adapter (Consolidated)
=============================================

Implements the INFORMATIV ↔ StackAdapt integration:
- Psychological audience segments → StackAdapt Audiences (GraphQL API)
- Audience taxonomy metadata → StackAdapt Third-Party Catalogue (Data Taxonomy API)
- Personality-matched creative → StackAdapt Native/Display/Video/CTV/Audio
- Campaign management via StackAdapt GraphQL API
- Outcome reporting → INFORMATIV learning loop

StackAdapt APIs (verified March 2026):
    GraphQL API:        api.stackadapt.com/graphql (campaigns, audiences, creatives)
    Data Taxonomy API:  api.stackadapt.com/data-partner/graphql (segment taxonomy)
    Pixel API:          tags.srv.stackadapt.com (conversion tracking / audience gen)
    REST API:           DEPRECATED — do not use

Docs: https://docs.stackadapt.com/

Key concepts:
    Advertiser → Brand | Campaign → INFORMATIV Campaign | Audience → PsychologicalSegment
    Creative → PersonalityCreativeProfile | Conversion Pixel → Outcome tracking
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


class StackAdaptAdapter(BasePlatformAdapter):
    """
    StackAdapt platform adapter.

    In DEMO mode: simulates all API responses for presentation.
    In PRODUCTION mode: calls StackAdapt GraphQL API.
    """

    PLATFORM_NAME = "stackadapt"
    SUPPORTED_FORMATS = ["native", "display", "video", "ctv", "audio"]

    # StackAdapt GraphQL endpoint
    GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"

    def __init__(
        self,
        credentials: Optional[PlatformCredentials] = None,
        mode: AdapterMode = AdapterMode.DEMO,
    ):
        super().__init__(credentials, mode)
        self._graphql_client = None

    # =========================================================================
    # DEMO OVERRIDES (richer than base)
    # =========================================================================

    def _demo_sync_segment(self, segment: Any) -> SyncedSegment:
        """Demo: simulate StackAdapt audience creation."""
        seg_id = getattr(segment, "segment_id", "unknown")
        seg_name = getattr(segment, "name", "Unknown")
        reach = getattr(segment, "estimated_reach", 10000)

        return SyncedSegment(
            adam_segment_id=seg_id,
            platform_segment_id=f"sa_aud_{seg_id}_{reach}",
            platform_name="stackadapt",
            size=reach,
            status="active",
            last_synced="2026-02-10T00:00:00Z",
        )

    def _demo_upload_creative(
        self,
        creative_spec: Any,
        segment_id: str,
    ) -> SyncedCreative:
        """Demo: simulate StackAdapt creative upload."""
        import uuid
        creative_id = f"sa_cr_{uuid.uuid4().hex[:8]}"

        # Determine format from creative spec
        fmt = "native"
        if hasattr(creative_spec, "voice_style") and creative_spec.voice_style:
            fmt = "audio"

        return SyncedCreative(
            adam_creative_id=creative_id,
            platform_creative_id=creative_id,
            platform_name="stackadapt",
            format=fmt,
            status="active",
        )

    def _demo_get_metrics(self, campaign_id: str) -> PlatformMetrics:
        """Demo: generate realistic StackAdapt metrics."""
        import random
        # StackAdapt typically achieves better CTR/CVR than industry avg
        impressions = random.randint(100000, 500000)
        ctr = random.uniform(0.01, 0.03)  # 1-3% for native
        clicks = int(impressions * ctr)
        conv_rate = random.uniform(0.01, 0.025)
        conversions = int(impressions * conv_rate)
        spend = impressions * random.uniform(0.006, 0.012)
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
    # PRODUCTION IMPLEMENTATIONS
    # =========================================================================

    async def _sync_segment_impl(self, segment: Any) -> SyncedSegment:
        """
        Sync segment to StackAdapt via GraphQL.

        Creates or updates a StackAdapt Audience with:
        - Custom audience name (ADAM segment name)
        - Description including psychological profile
        - Targeting parameters derived from construct profile
        """
        seg_id = getattr(segment, "segment_id", "unknown")
        seg_name = getattr(segment, "name", "Unknown")
        description = getattr(segment, "description", "")
        constructs = getattr(segment, "defining_constructs", {})

        # Build targeting metadata
        targeting_meta = {
            "adam_segment_id": seg_id,
            "psychological_profile": {
                "regulatory_orientation": getattr(segment, "regulatory_orientation", "balanced"),
                "processing_style": getattr(segment, "processing_style", "moderate"),
                "top_constructs": dict(list(constructs.items())[:5]),
            },
        }

        # GraphQL mutation to create audience
        mutation = """
        mutation CreateAudience($input: CreateAudienceInput!) {
            createAudience(input: $input) {
                id
                name
                estimatedSize
                status
            }
        }
        """
        variables = {
            "input": {
                "name": f"ADAM: {seg_name}",
                "description": f"ADAM Psychological Segment: {description}",
                "type": "CUSTOM",
                "metadata": targeting_meta,
            }
        }

        result = await self._execute_graphql(mutation, variables)

        audience = result.get("data", {}).get("createAudience", {})
        return SyncedSegment(
            adam_segment_id=seg_id,
            platform_segment_id=audience.get("id", ""),
            platform_name="stackadapt",
            size=audience.get("estimatedSize", 0),
            status=audience.get("status", "active"),
        )

    async def _upload_creative_impl(
        self,
        creative_spec: Any,
        segment_id: str,
    ) -> SyncedCreative:
        """Upload creative to StackAdapt via GraphQL."""
        import uuid
        creative_id = f"adam_cr_{uuid.uuid4().hex[:8]}"

        # Build creative from spec
        headline = ""
        body = ""
        cta = ""
        if hasattr(creative_spec, "headline_templates") and creative_spec.headline_templates:
            headline = creative_spec.headline_templates[0]
        if hasattr(creative_spec, "value_propositions") and creative_spec.value_propositions:
            body = creative_spec.value_propositions[0]
        if hasattr(creative_spec, "cta_templates") and creative_spec.cta_templates:
            cta = creative_spec.cta_templates[0]

        mutation = """
        mutation CreateNativeAd($input: CreateNativeAdInput!) {
            createNativeAd(input: $input) {
                id
                status
                headline
            }
        }
        """
        variables = {
            "input": {
                "headline": headline,
                "body": body,
                "callToAction": cta,
                "brandName": "ADAM",
            }
        }

        result = await self._execute_graphql(mutation, variables)
        ad = result.get("data", {}).get("createNativeAd", {})

        return SyncedCreative(
            adam_creative_id=creative_id,
            platform_creative_id=ad.get("id", ""),
            platform_name="stackadapt",
            format="native",
            status=ad.get("status", "active"),
        )

    async def _create_campaign_impl(self, config: CampaignConfig) -> PlatformCampaign:
        """Create campaign on StackAdapt via GraphQL."""
        mutation = """
        mutation CreateCampaign($input: CreateCampaignInput!) {
            createCampaign(input: $input) {
                id
                name
                status
                budget { daily total }
            }
        }
        """
        variables = {
            "input": {
                "name": config.name,
                "budget": {
                    "daily": config.budget_daily,
                    "total": config.budget_total,
                },
                "startDate": config.start_date,
                "endDate": config.end_date,
                "bidStrategy": config.bid_strategy.upper(),
                "goalCpa": config.goal_cpa,
            }
        }

        result = await self._execute_graphql(mutation, variables)
        campaign_data = result.get("data", {}).get("createCampaign", {})

        campaign = PlatformCampaign(
            campaign_id=campaign_data.get("id", ""),
            platform_name="stackadapt",
            config=config,
            status=CampaignStatus.DRAFT,
        )
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    async def _get_metrics_impl(self, campaign_id: str) -> PlatformMetrics:
        """Get campaign metrics from StackAdapt via GraphQL."""
        query = """
        query CampaignPerformance($campaignId: ID!) {
            campaign(id: $campaignId) {
                performance {
                    impressions
                    clicks
                    conversions
                    spend
                    cpm
                    ctr
                    conversionRate
                    cpa
                }
            }
        }
        """
        result = await self._execute_graphql(query, {"campaignId": campaign_id})
        perf = (
            result.get("data", {})
            .get("campaign", {})
            .get("performance", {})
        )

        return PlatformMetrics(
            impressions=perf.get("impressions", 0),
            clicks=perf.get("clicks", 0),
            conversions=perf.get("conversions", 0),
            spend=perf.get("spend", 0.0),
            cpm=perf.get("cpm", 0.0),
            ctr=perf.get("ctr", 0.0),
            conversion_rate=perf.get("conversionRate", 0.0),
            cpa=perf.get("cpa", 0.0),
        )

    # =========================================================================
    # GRAPHQL CLIENT
    # =========================================================================

    async def _execute_graphql(
        self,
        query: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a GraphQL query/mutation against StackAdapt API."""
        if not self._credentials or not self._credentials.api_key:
            raise ValueError("StackAdapt API key not configured")

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.GRAPHQL_ENDPOINT,
                    json={"query": query, "variables": variables},
                    headers={
                        "Authorization": f"Bearer {self._credentials.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
        except ImportError:
            logger.error("httpx not installed — required for StackAdapt API")
            raise
        except Exception as e:
            logger.error(f"StackAdapt API error: {e}")
            raise


# =============================================================================
# SINGLETON
# =============================================================================

_adapter: Optional[StackAdaptAdapter] = None


def get_stackadapt_adapter(
    mode: AdapterMode = AdapterMode.DEMO,
) -> StackAdaptAdapter:
    """Get singleton StackAdapt adapter."""
    global _adapter
    if _adapter is None:
        _adapter = StackAdaptAdapter(mode=mode)
    return _adapter
