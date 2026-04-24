"""
Campaign Deployment Service
==============================

Orchestrates deploying a campaign to StackAdapt when it transitions
from 'review' to 'active'. Creates DSP campaigns, creative variants,
and domain targeting rules.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from adam.api.admin.db import get_db

logger = logging.getLogger(__name__)


async def deploy_campaign_to_dsp(campaign_id: str) -> Dict[str, Any]:
    """Deploy campaign configuration to StackAdapt via GraphQL."""
    db = get_db()

    campaign = await db.fetch_one("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not campaign:
        return {"success": False, "error": "Campaign not found"}

    archetypes = await db.fetch_all(
        "SELECT * FROM campaign_archetypes WHERE campaign_id = $1", campaign_id,
    )

    results = {
        "success": True,
        "campaign_id": campaign_id,
        "archetypes_deployed": 0,
        "creatives_deployed": 0,
        "errors": [],
    }

    api_key = campaign.get("dsp_api_key_encrypted", "")
    advertiser_id = campaign.get("dsp_advertiser_id", "")

    if not api_key or not advertiser_id:
        return {"success": False, "error": "DSP credentials not configured"}

    try:
        from adam.integrations.stackadapt_monitor import StackAdaptMonitor
        monitor = StackAdaptMonitor(api_key=api_key)

        for arch in archetypes:
            arch_id = str(arch["id"])

            # Create campaign in StackAdapt
            dsp_result = monitor._query(f"""
                mutation {{
                    createCampaign(input: {{
                        name: "{campaign['name']} - {arch['archetype_name']}"
                        advertiserId: "{advertiser_id}"
                        budget: {float(campaign.get('daily_budget', 0) * float(arch.get('budget_weight', 0.1)))}
                        budgetType: DAILY
                        objective: CONVERSIONS
                    }}) {{
                        campaign {{ id name status }}
                        userErrors {{ message }}
                    }}
                }}
            """)

            if dsp_result.get("errors"):
                results["errors"].append(f"Archetype {arch['archetype_name']}: {dsp_result['errors']}")
                continue

            dsp_campaign = (dsp_result.get("data", {}).get("createCampaign", {}).get("campaign") or {})
            dsp_campaign_id = dsp_campaign.get("id", "")

            if dsp_campaign_id:
                await db.execute(
                    "UPDATE campaign_archetypes SET dsp_campaign_id = $1, dsp_campaign_status = 'active' WHERE id = $2",
                    dsp_campaign_id, arch_id,
                )
                results["archetypes_deployed"] += 1

            # Deploy creatives for this archetype
            creatives = await db.fetch_all(
                "SELECT * FROM creative_variants WHERE campaign_archetype_id = $1", arch_id,
            )

            for creative in creatives:
                if dsp_campaign_id:
                    creative_result = monitor._query(f"""
                        mutation {{
                            createNativeAd(input: {{
                                campaignId: "{dsp_campaign_id}"
                                name: "{creative['variant_label']}"
                                headline: "{_escape_graphql(creative['headline'])}"
                                body: "{_escape_graphql(creative.get('body_copy', ''))}"
                                callToAction: "{_escape_graphql(creative.get('cta_text', 'Learn more'))}"
                                brandName: "{_escape_graphql(campaign['brand_name'])}"
                                url: "{creative.get('landing_url', campaign.get('brand_website', ''))}"
                            }}) {{
                                nativeAd {{ id name }}
                                userErrors {{ message }}
                            }}
                        }}
                    """)

                    dsp_creative_id = (creative_result.get("data", {}).get("createNativeAd", {}).get("nativeAd", {}).get("id", ""))
                    if dsp_creative_id:
                        await db.execute(
                            "UPDATE creative_variants SET dsp_creative_id = $1, status = 'active' WHERE id = $2",
                            dsp_creative_id, str(creative["id"]),
                        )
                        results["creatives_deployed"] += 1

            # Deploy domain targeting
            domains = await db.fetch_all(
                "SELECT domain, list_type FROM domain_lists WHERE campaign_archetype_id = $1 OR "
                "(campaign_id = $2 AND campaign_archetype_id IS NULL)",
                arch_id, campaign_id,
            )

            whitelist = [d["domain"] for d in domains if d["list_type"] == "whitelist"]
            blacklist = [d["domain"] for d in domains if d["list_type"] == "blacklist"]

            if whitelist and dsp_campaign_id:
                domain_list_str = ", ".join(f'"{d}"' for d in whitelist)
                monitor._query(f"""
                    mutation {{
                        updateCampaign(id: "{dsp_campaign_id}", input: {{
                            domainTargeting: {{
                                type: WHITELIST
                                domains: [{domain_list_str}]
                            }}
                        }}) {{
                            campaign {{ id }}
                            userErrors {{ message }}
                        }}
                    }}
                """)

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Deployment error: {str(e)}")

    logger.info("Campaign deployment result: %s", results)
    return results


def _escape_graphql(s: str) -> str:
    """Escape string for GraphQL mutation."""
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
