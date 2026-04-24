"""
Campaign Execution Engine
===========================

Executes approved directives via StackAdapt GraphQL API.
Stores pre-change snapshots for rollback capability.

In Phase 1 (auto_execute=False), generates human-readable instructions.
In Phase 2 (auto_execute=True), executes mutations directly.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    Directive,
    DirectiveStatus,
    DirectiveType,
)

logger = logging.getLogger(__name__)


class CampaignExecutionEngine:
    """Executes optimization directives against the DSP."""

    def __init__(self, config=None):
        self.config = config or get_dcil_config()

    def execute_all(self, directives: List[Directive]) -> List[Directive]:
        """Execute all approved directives."""
        executed = []

        approved = [d for d in directives if d.status == DirectiveStatus.APPROVED]
        capped = [d for d in directives if d.status == DirectiveStatus.CAPPED]

        for directive in approved + capped:
            if self.config.auto_execute:
                result = self._execute_via_api(directive)
            else:
                result = self._generate_instructions(directive)

            directive.execution_result = result
            directive.executed_at = time.time()
            if "ERROR" not in result.upper():
                directive.status = DirectiveStatus.EXECUTED
            else:
                directive.status = DirectiveStatus.FAILED

            executed.append(directive)

        return executed

    def _execute_via_api(self, directive: Directive) -> str:
        """Execute directive via StackAdapt GraphQL mutation."""
        try:
            from adam.integrations.stackadapt_monitor import StackAdaptMonitor
            monitor = StackAdaptMonitor(api_key=self.config.stackadapt_api_key)

            # Snapshot pre-change state
            directive.pre_change_snapshot = self._snapshot_campaign(
                directive.campaign_id, monitor,
            )

            mutation = self._build_mutation(directive)
            if not mutation:
                return f"No mutation generated for directive type {directive.directive_type.value}"

            result = monitor._query(mutation)

            if result.get("errors"):
                return f"API error: {result['errors']}"

            return f"Executed: {directive.directive_type.value} on {directive.campaign_id or directive.archetype}"

        except Exception as e:
            return f"Execution error: {e}"

    def _generate_instructions(self, directive: Directive) -> str:
        """Generate human-readable instructions when auto-execute is off."""
        instructions = {
            DirectiveType.BUDGET_REALLOCATION: (
                f"BUDGET: {directive.archetype or directive.campaign_name} → {directive.proposed_value}\n"
                f"  Rationale: {directive.rationale}\n"
                f"  Evidence: {directive.bilateral_evidence}"
            ),
            DirectiveType.PAUSE_RESUME: (
                f"PAUSE/RESUME: Campaign {directive.campaign_name or directive.campaign_id} → {directive.proposed_value}\n"
                f"  Rationale: {directive.rationale}"
            ),
            DirectiveType.DOMAIN_TARGETING: (
                f"DOMAIN: {directive.parameter} → {directive.proposed_value}\n"
                f"  Campaign: {directive.campaign_name or 'all'}\n"
                f"  Rationale: {directive.rationale}"
            ),
            DirectiveType.DAYPARTING: (
                f"DAYPARTING: {directive.archetype or directive.campaign_name} → {directive.proposed_value}\n"
                f"  Rationale: {directive.rationale}"
            ),
            DirectiveType.FREQUENCY_CAP: (
                f"FREQUENCY: {directive.archetype or directive.campaign_name} → {directive.proposed_value}\n"
                f"  Rationale: {directive.rationale}"
            ),
            DirectiveType.MECHANISM_ROTATION: (
                f"MECHANISM: {directive.archetype or 'system'} → {directive.proposed_value}\n"
                f"  Rationale: {directive.rationale}\n"
                f"  Evidence: {directive.bilateral_evidence}"
            ),
            DirectiveType.CREATIVE_SWAP: (
                f"CREATIVE: {directive.parameter} → {directive.proposed_value}\n"
                f"  Rationale: {directive.rationale}"
            ),
        }

        return instructions.get(
            directive.directive_type,
            f"{directive.directive_type.value}: {directive.proposed_value}",
        )

    def _build_mutation(self, directive: Directive) -> str:
        """Build GraphQL mutation for a directive."""
        if not directive.campaign_id:
            return ""

        if directive.directive_type == DirectiveType.PAUSE_RESUME:
            new_status = "PAUSED" if "pause" in str(directive.proposed_value).lower() else "ACTIVE"
            return f"""
                mutation {{
                    updateCampaign(id: "{directive.campaign_id}", input: {{ status: {new_status} }}) {{
                        campaign {{ id name status }}
                        userErrors {{ message }}
                    }}
                }}
            """

        if directive.directive_type == DirectiveType.BUDGET_REALLOCATION:
            # Would need to resolve actual dollar amounts from current budget
            return ""

        return ""

    def _snapshot_campaign(self, campaign_id: str, monitor) -> Dict[str, Any]:
        """Snapshot current campaign state for rollback."""
        if not campaign_id:
            return {}

        try:
            result = monitor._query(f"""
                {{ campaigns(first: 1, filter: {{ id: "{campaign_id}" }}) {{
                    nodes {{
                        id name status
                        budget {{ daily total }}
                        stats {{
                            impressionsBigint clicksBigint conversionsBigint
                            cost ctr ecpa
                        }}
                    }}
                }} }}
            """)
            nodes = result.get("data", {}).get("campaigns", {}).get("nodes", [])
            return nodes[0] if nodes else {}
        except Exception:
            return {}

    def rollback(self, directive: Directive) -> str:
        """Rollback a previously executed directive."""
        if not directive.pre_change_snapshot:
            return "No pre-change snapshot available for rollback."

        if not self.config.auto_execute:
            return (
                f"ROLLBACK NEEDED: Revert {directive.directive_type.value} on "
                f"{directive.campaign_id or directive.archetype}. "
                f"Pre-change state: {json.dumps(directive.pre_change_snapshot, indent=2)}"
            )

        # Build reversal mutation from pre-change snapshot
        try:
            from adam.integrations.stackadapt_monitor import StackAdaptMonitor
            monitor = StackAdaptMonitor(api_key=self.config.stackadapt_api_key)

            pre = directive.pre_change_snapshot
            if "status" in pre:
                mutation = f"""
                    mutation {{
                        updateCampaign(id: "{directive.campaign_id}", input: {{ status: {pre['status']} }}) {{
                            campaign {{ id status }}
                            userErrors {{ message }}
                        }}
                    }}
                """
                result = monitor._query(mutation)
                if result.get("errors"):
                    return f"Rollback API error: {result['errors']}"

            directive.status = DirectiveStatus.ROLLED_BACK
            return f"Rolled back: {directive.directive_type.value} on {directive.campaign_id}"

        except Exception as e:
            return f"Rollback error: {e}"


def format_execution_summary(directives: List[Directive]) -> str:
    """Format all directives into a human-readable summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("DCIL OPTIMIZATION DIRECTIVES")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)

    by_status = {}
    for d in directives:
        status = d.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(d)

    for status in ["executed", "approved", "capped", "blocked", "failed"]:
        group = by_status.get(status, [])
        if not group:
            continue

        lines.append(f"\n--- {status.upper()} ({len(group)}) ---")
        for d in group:
            lines.append(f"\n  [{d.directive_type.value}] {d.directive_id}")
            if d.archetype:
                lines.append(f"  Archetype: {d.archetype}")
            lines.append(f"  Action: {d.parameter} → {d.proposed_value}")
            lines.append(f"  Rationale: {d.rationale}")
            if d.execution_result:
                lines.append(f"  Result: {d.execution_result}")
            if d.blocked_reason:
                lines.append(f"  Blocked: {d.blocked_reason}")

    lines.append("")
    return "\n".join(lines)
