# =============================================================================
# StackAdapt Campaign Executor
# Location: adam/ops/stackadapt_executor.py
# =============================================================================

"""
Executes approved campaign changes via StackAdapt GraphQL API.

Phase 1 (current): Generates human-readable instructions for the agency.
Phase 2 (with API key): Auto-executes via GraphQL mutations.

Supported actions:
- Adjust campaign budget (daily/total)
- Modify frequency caps
- Adjust device bid multipliers
- Adjust dayparting bid multipliers
- Pause/resume campaigns
- Add/remove domains from targeting lists
- Create/modify audiences
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# StackAdapt GraphQL API configuration
GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"
API_KEY = os.getenv("STACKADAPT_API_KEY", "")  # Placeholder — get from Becca


class StackAdaptExecutor:
    """Executes campaign changes via StackAdapt GraphQL API."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or API_KEY
        self._campaign_ids: Dict[str, str] = {}  # Our name → StackAdapt ID mapping
        self._execution_log: List[Dict] = []

    @property
    def is_configured(self) -> bool:
        """Whether we have API access for auto-execution."""
        return bool(self._api_key) and self._api_key != ""

    def set_campaign_mapping(self, mapping: Dict[str, str]):
        """Set the mapping from our campaign names to StackAdapt campaign IDs.

        This is populated from Becca's account info.
        Example: {"CT-T1": "sa_campaign_12345", "SS-T2": "sa_campaign_67890"}
        """
        self._campaign_ids = mapping
        logger.info("Campaign mapping set: %d campaigns", len(mapping))

    async def execute(self, action: Dict) -> Dict:
        """Execute a campaign action.

        If API key is configured: executes via GraphQL.
        If not: returns human-readable instructions.
        """
        action_type = action.get("type", "")
        result = {
            "action_type": action_type,
            "executed_at": time.time(),
            "auto_executed": False,
            "instructions": "",
            "graphql_response": None,
        }

        if self.is_configured:
            # Phase 2: Auto-execute via GraphQL
            try:
                response = await self._execute_graphql(action)
                result["auto_executed"] = True
                result["graphql_response"] = response
                result["status"] = "executed"
            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)
                result["instructions"] = self._generate_manual_instructions(action)
        else:
            # Phase 1: Generate instructions for manual execution
            result["instructions"] = self._generate_manual_instructions(action)
            result["status"] = "instructions_generated"

        self._execution_log.append(result)
        return result

    async def _execute_graphql(self, action: Dict) -> Dict:
        """Execute a GraphQL mutation against StackAdapt API."""
        import httpx

        action_type = action.get("type", "")
        mutation = self._build_mutation(action)

        if not mutation:
            return {"error": "No mutation generated for this action type"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GRAPHQL_ENDPOINT,
                json={"query": mutation["query"], "variables": mutation.get("variables", {})},
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def _build_mutation(self, action: Dict) -> Optional[Dict]:
        """Build a GraphQL mutation from an action."""
        action_type = action.get("type", "")

        if action_type == "budget_adjustment":
            campaign_id = self._resolve_campaign_id(action.get("campaign", ""))
            if not campaign_id:
                return None
            return {
                "query": """
                    mutation UpdateCampaignBudget($id: ID!, $dailyBudget: Float!) {
                        updateCampaign(id: $id, input: {
                            budget: { daily: $dailyBudget }
                        }) {
                            id
                            name
                            budget { daily total }
                        }
                    }
                """,
                "variables": {
                    "id": campaign_id,
                    "dailyBudget": action.get("new_daily_budget", 0),
                },
            }

        elif action_type == "frequency_cap":
            campaign_id = self._resolve_campaign_id(action.get("campaign", ""))
            if not campaign_id:
                return None
            return {
                "query": """
                    mutation UpdateFrequencyCap($id: ID!, $maxDaily: Int!, $maxWeekly: Int!) {
                        updateCampaign(id: $id, input: {
                            frequencyCap: {
                                maxImpressionsPerDay: $maxDaily
                                maxImpressionsPerWeek: $maxWeekly
                            }
                        }) {
                            id
                            name
                        }
                    }
                """,
                "variables": {
                    "id": campaign_id,
                    "maxDaily": action.get("max_daily", 2),
                    "maxWeekly": action.get("max_weekly", 7),
                },
            }

        elif action_type == "device_bid_adjustment":
            campaign_id = self._resolve_campaign_id(action.get("campaign", ""))
            if not campaign_id:
                return None
            return {
                "query": """
                    mutation UpdateDeviceBid($id: ID!, $desktop: Float!, $mobile: Float!, $tablet: Float!) {
                        updateCampaign(id: $id, input: {
                            deviceBidMultipliers: {
                                desktop: $desktop
                                mobile: $mobile
                                tablet: $tablet
                            }
                        }) {
                            id
                            name
                        }
                    }
                """,
                "variables": {
                    "id": campaign_id,
                    "desktop": action.get("desktop_multiplier", 1.0),
                    "mobile": action.get("mobile_multiplier", 1.0),
                    "tablet": action.get("tablet_multiplier", 0.9),
                },
            }

        elif action_type == "pause_campaign":
            campaign_id = self._resolve_campaign_id(action.get("campaign", ""))
            if not campaign_id:
                return None
            return {
                "query": """
                    mutation PauseCampaign($id: ID!) {
                        updateCampaign(id: $id, input: { status: PAUSED }) {
                            id
                            name
                            status
                        }
                    }
                """,
                "variables": {"id": campaign_id},
            }

        elif action_type == "resume_campaign":
            campaign_id = self._resolve_campaign_id(action.get("campaign", ""))
            if not campaign_id:
                return None
            return {
                "query": """
                    mutation ResumeCampaign($id: ID!) {
                        updateCampaign(id: $id, input: { status: ACTIVE }) {
                            id
                            name
                            status
                        }
                    }
                """,
                "variables": {"id": campaign_id},
            }

        elif action_type == "daypart_adjustment":
            campaign_id = self._resolve_campaign_id(action.get("campaign", ""))
            if not campaign_id:
                return None
            return {
                "query": """
                    mutation UpdateDayparting($id: ID!, $schedule: [DaypartInput!]!) {
                        updateCampaign(id: $id, input: {
                            dayparting: $schedule
                        }) {
                            id
                            name
                        }
                    }
                """,
                "variables": {
                    "id": campaign_id,
                    "schedule": action.get("schedule", []),
                },
            }

        return None

    def _resolve_campaign_id(self, our_name: str) -> Optional[str]:
        """Resolve our internal campaign name to a StackAdapt campaign ID."""
        return self._campaign_ids.get(our_name)

    def _generate_manual_instructions(self, action: Dict) -> str:
        """Generate human-readable instructions when API not available."""
        action_type = action.get("type", "")

        if action_type == "budget_adjustment":
            return (
                f"In StackAdapt:\n"
                f"1. Open campaign: {action.get('campaign', '')}\n"
                f"2. Edit Budget settings\n"
                f"3. Change daily budget to: ${action.get('new_daily_budget', 0):.2f}\n"
                f"4. Save"
            )
        elif action_type == "frequency_cap":
            return (
                f"In StackAdapt:\n"
                f"1. Open campaign: {action.get('campaign', '')}\n"
                f"2. Edit Delivery settings → Frequency Cap\n"
                f"3. Set max per day: {action.get('max_daily', 2)}\n"
                f"4. Set max per week: {action.get('max_weekly', 7)}\n"
                f"5. Save"
            )
        elif action_type == "device_bid_adjustment":
            return (
                f"In StackAdapt:\n"
                f"1. Open campaign: {action.get('campaign', '')}\n"
                f"2. Edit Targeting → Device\n"
                f"3. Set Desktop multiplier: {action.get('desktop_multiplier', 1.0):.1f}x\n"
                f"4. Set Mobile multiplier: {action.get('mobile_multiplier', 1.0):.1f}x\n"
                f"5. Save"
            )
        elif action_type == "pause_campaign":
            return (
                f"In StackAdapt:\n"
                f"1. Find campaign: {action.get('campaign', '')}\n"
                f"2. Change status to PAUSED"
            )
        elif action_type == "audience_exclusion":
            return (
                f"In StackAdapt:\n"
                f"1. Go to Audiences → Create New\n"
                f"2. Name: '{action.get('name', 'INFORMATIV Suppression')}'\n"
                f"3. Type: Exclusion\n"
                f"4. Criteria: {action.get('criteria', '')}\n"
                f"5. Apply to ALL active campaigns"
            )
        elif action_type == "audience_creation":
            return (
                f"In StackAdapt:\n"
                f"1. Go to Audiences → Create New\n"
                f"2. Name: '{action.get('name', 'INFORMATIV Custom Audience')}'\n"
                f"3. Type: Retargeting\n"
                f"4. Criteria: {action.get('criteria', '')}\n"
                f"5. Assign to recommended campaigns"
            )
        else:
            return f"Action: {action_type}\nDetails: {json.dumps(action, indent=2)}"


def get_executor(api_key: str = "") -> StackAdaptExecutor:
    return StackAdaptExecutor(api_key=api_key)
