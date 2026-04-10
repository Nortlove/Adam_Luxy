# =============================================================================
# Therapeutic Retargeting Engine — StackAdapt Campaign Translator
# Location: adam/retargeting/integrations/stackadapt_translator.py
# Spec: Enhancement #33, Session 33-9
# =============================================================================

"""
Translates therapeutic sequences into StackAdapt-executable campaign configs.

Mapping:
- TherapeuticSequence → StackAdapt Campaign Group (one per archetype)
- TherapeuticTouch → StackAdapt Campaign (sequential with audience exclusion)
- Domain whitelists → StackAdapt Site Targeting (CSV)
- Frequency caps → StackAdapt Campaign Settings
- Dayparting → StackAdapt Scheduling grid
- Creative specs → StackAdapt Creative (headline, body, CTA, image)
- Suppression lists → StackAdapt Exclusion audiences

Output: Complete campaign configuration that can be executed in StackAdapt's
self-serve UI or via the GraphQL API.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from adam.retargeting.models.sequences import TherapeuticSequence, TherapeuticTouch
from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)
from adam.constants import THERAPEUTIC_TO_CIALDINI

logger = logging.getLogger(__name__)


# StackAdapt audience segment mapping
_ARCHETYPE_SEGMENT_PREFIX = "informativ"
_TOUCH_AUDIENCE_RULES = {
    1: "All site visitors (prospecting pool)",
    2: "Visited site but no booking start within 48h",
    3: "Booking started but abandoned",
    4: "Multiple visits, no conversion",
    5: "Returned after suppression period",
}


class StackAdaptCampaignTranslator:
    """Translates therapeutic sequences into StackAdapt campaign configurations."""

    def translate_sequence(
        self,
        sequence: TherapeuticSequence,
        brand_name: str = "",
        website_url: str = "",
        daily_budget: float = 50.0,
        domain_whitelist: Optional[List[str]] = None,
        domain_blacklist: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Translate a complete therapeutic sequence to StackAdapt config.

        Returns a dict that can be serialized to JSON for handoff to
        StackAdapt campaign managers or API integration.
        """
        campaign_group = {
            "campaign_group": {
                "name": (
                    f"{brand_name} — Therapeutic Retargeting "
                    f"({sequence.archetype_id})"
                ),
                "brand": brand_name,
                "website": website_url,
                "sequence_id": sequence.sequence_id,
                "archetype": sequence.archetype_id,
                "narrative_arc": sequence.narrative_arc_type,
                "max_touches": sequence.max_touches,
                "max_duration_days": sequence.max_duration_days,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "campaigns": [],
            "audience_segments": self._build_audience_segments(
                sequence, brand_name
            ),
            "site_targeting": {
                "whitelist": domain_whitelist or [],
                "blacklist": domain_blacklist or [],
            },
            "frequency_capping": self._build_frequency_caps(sequence),
            "suppression_rules": self._build_suppression_rules(sequence),
            "measurement": self._build_measurement_config(sequence),
        }

        # Translate each touch to a campaign
        for touch in sequence.touches_delivered:
            campaign = self._translate_touch(
                touch, sequence, brand_name, daily_budget
            )
            campaign_group["campaigns"].append(campaign)

        return campaign_group

    def _translate_touch(
        self,
        touch: TherapeuticTouch,
        sequence: TherapeuticSequence,
        brand_name: str,
        daily_budget: float,
    ) -> Dict[str, Any]:
        """Translate a single therapeutic touch to a StackAdapt campaign."""
        position = touch.position_in_sequence
        cialdini = THERAPEUTIC_TO_CIALDINI.get(touch.mechanism.value, "authority")

        # Budget allocation: later touches get more (they're more targeted)
        budget_multiplier = 0.8 + 0.1 * position
        touch_budget = round(daily_budget * budget_multiplier, 2)

        # Creative from touch strategy
        creative = touch.creative_strategy or {}

        campaign = {
            "campaign_name": (
                f"Touch {position}: {touch.mechanism.value} → "
                f"{touch.target_barrier.value}"
            ),
            "position_in_sequence": position,
            "touch_id": touch.touch_id,

            # Targeting
            "target_barrier": touch.target_barrier.value,
            "target_dimension": touch.target_alignment_dimension,
            "mechanism": touch.mechanism.value,
            "cialdini_equivalent": cialdini,

            # Creative specification
            "creative": {
                "headline_strategy": creative.get("creative_direction", ""),
                "narrative_chapter": touch.narrative_chapter,
                "narrative_function": touch.narrative_function,
                "construal_level": touch.construal_level,
                "processing_route": touch.processing_route,
                "testimonial_type": touch.testimonial_model_type,
                "scaffold_level": touch.scaffold_level.value,
                "autonomy_language": touch.autonomy_language,
                "opt_out_visible": touch.opt_out_visible,
                "argument_mode": (
                    "claude_generated"
                    if touch.mechanism == TherapeuticMechanism.CLAUDE_ARGUMENT
                    else "template"
                ),
            },

            # Trigger rules
            "trigger": {
                "type": touch.trigger_type,
                "conditions": touch.trigger_conditions,
                "min_hours_after_previous": touch.min_hours_after_previous,
                "max_hours_after_previous": touch.max_hours_after_previous,
            },

            # Budget
            "daily_budget": touch_budget,

            # Audience
            "audience_rule": _TOUCH_AUDIENCE_RULES.get(
                position, f"Custom audience for touch {position}"
            ),
            "exclude_converters": True,
            "exclude_previous_touch_engaged": position > 1,

            # Per-touch page mindstate targeting (resonance × repeated measures)
            # Each touch prescribes WHERE to show it, not just WHAT.
            "site_targeting": {
                "strategy": (
                    "per_touch_resonance"
                    if touch.target_page_cluster else "campaign_default"
                ),
                "target_page_cluster": touch.target_page_cluster or "any",
                "bid_multipliers": touch.placement_bid_strategy or {},
                "note": (
                    f"Optimized for {touch.mechanism.value} on "
                    f"{touch.target_page_cluster or 'any'} pages"
                    if touch.target_page_cluster
                    else "Using campaign-level site targeting"
                ),
            },
        }

        return campaign

    def _build_audience_segments(
        self,
        sequence: TherapeuticSequence,
        brand_name: str,
    ) -> List[Dict[str, str]]:
        """Build pixel-based audience segment definitions."""
        return [
            {
                "name": f"{brand_name} — Site Visitors (No Booking)",
                "rule": "page_url contains site AND NOT booking_start pixel",
                "use_for": "Touch 2+",
            },
            {
                "name": f"{brand_name} — Booking Abandoned",
                "rule": "booking_start pixel AND NOT booking_complete pixel",
                "use_for": "Touch 3-4",
            },
            {
                "name": f"{brand_name} — Converted",
                "rule": "booking_complete pixel",
                "use_for": "EXCLUDE from all retargeting",
            },
            {
                "name": f"{brand_name} — Multi-Visit No Action",
                "rule": "site visit count >= 3 AND NOT booking_start",
                "use_for": "Touch 3-5",
            },
        ]

    def _build_frequency_caps(
        self, sequence: TherapeuticSequence
    ) -> Dict[str, Any]:
        """Build frequency capping rules from sequence config."""
        return {
            "max_impressions_per_day": 1,
            "max_impressions_per_week": 3,
            "max_impressions_total": sequence.max_touches,
            "min_hours_between_impressions": 12,
            "note": (
                "CRITICAL: Do NOT use StackAdapt's standard creative rotation. "
                "Each touch MUST use a DIFFERENT creative mapped to the sequence. "
                "Set up as sequential campaigns with audience exclusion rules."
            ),
        }

    def _build_suppression_rules(
        self, sequence: TherapeuticSequence
    ) -> List[Dict[str, str]]:
        """Build suppression rules for the campaign group."""
        return [
            {
                "rule": "After conversion: suppress ALL retargeting",
                "action": "Add to Converted exclusion audience",
            },
            {
                "rule": f"After {sequence.max_touches} touches with no conversion",
                "action": f"Suppress for {sequence.suppression_duration_days} days",
            },
            {
                "rule": "CTR drops below 0.03% after touch 3",
                "action": "Pause 72 hours",
            },
            {
                "rule": "User visits competitor site within 72h",
                "action": "Restart sequence at touch 1 with comparison creative",
            },
        ]

    def _build_measurement_config(
        self, sequence: TherapeuticSequence
    ) -> Dict[str, Any]:
        """Build measurement framework for the campaign."""
        return {
            "primary_kpi": "cost_per_conversion",
            "secondary_kpis": [
                "per_touch_conversion_rate",
                "stage_advancement_rate",
                "barrier_resolution_rate",
            ],
            "hypothesis": (
                "Each subsequent touch should convert at a HIGHER rate than "
                "the previous (because it addresses a more specific failure). "
                "If touch N converts lower than touch N-1, the mechanism "
                "mapping is wrong for that archetype."
            ),
            "tracking_pixels": [
                "site_visit", "pricing_page", "booking_start",
                "booking_complete", "review_page",
            ],
            "attribution_window_days": 7,
            "report_frequency": "daily",
        }

    def export_to_json(
        self,
        config: Dict[str, Any],
        filepath: str = "",
    ) -> str:
        """Export campaign config to JSON string (or file)."""
        output = json.dumps(config, indent=2, default=str)
        if filepath:
            with open(filepath, "w") as f:
                f.write(output)
            logger.info("Campaign config exported to %s", filepath)
        return output
