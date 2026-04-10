# =============================================================================
# StackAdapt API-Ready Campaign Exporter
# Location: adam/retargeting/integrations/stackadapt_api_exporter.py
# =============================================================================

"""
Produces StackAdapt-executable campaign configurations.

StackAdapt supports:
- API-based campaign creation (GraphQL)
- Bulk JSON import for campaign setup
- Custom audience segments via conversion pixels
- Domain targeting lists (CSV whitelist/blacklist)
- Creative management with multiple variants
- Frequency capping rules
- Dayparting schedules
- Retargeting sequences with audience exclusion rules

This exporter produces a COMPLETE package that can be imported
into StackAdapt's self-serve platform or executed via their API.

Output structure:
campaigns/
├── {brand}_campaign_config.json     # Master config (all campaigns)
├── {brand}_audiences.json           # Pixel-based audience definitions
├── {brand}_creatives.json           # Creative specs per touch
├── {brand}_domain_whitelist.csv     # Domain targeting
├── {brand}_domain_blacklist.csv     # Domain exclusions
├── {brand}_retargeting_rules.json   # Sequential retargeting logic
├── {brand}_frequency_caps.json      # Per-campaign frequency rules
├── {brand}_dayparting.json          # Time-of-day scheduling
└── {brand}_measurement.json         # Conversion tracking setup
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)
from adam.retargeting.models.sequences import TherapeuticSequence, TherapeuticTouch
from adam.constants import THERAPEUTIC_TO_CIALDINI, FRUSTRATED_DIMENSION_PAIRS

logger = logging.getLogger(__name__)


# StackAdapt campaign types
SA_CAMPAIGN_TYPES = {
    "native": "Native Ads",
    "display": "Display Ads",
    "video": "Video Ads",
    "ctv": "Connected TV",
    "audio": "Digital Audio",
}


class StackAdaptAPIExporter:
    """Exports INFORMATIV campaign intelligence as StackAdapt-executable configs.

    Produces JSON files that can be:
    1. Uploaded via StackAdapt's bulk campaign creation tool
    2. Submitted via StackAdapt's GraphQL API
    3. Used as a handoff document for manual campaign setup

    The output includes ALL parameters needed to execute the campaign —
    no additional configuration should be required.
    """

    def export_campaign(
        self,
        brand_name: str,
        website_url: str,
        archetypes: List[Dict[str, Any]],
        retargeting_sequences: List[TherapeuticSequence],
        bilateral_analysis: Dict[str, Any],
        domain_whitelist: Optional[List[str]] = None,
        domain_blacklist: Optional[List[str]] = None,
        daily_budget: float = 100.0,
        campaign_duration_days: int = 30,
        channels: Optional[List[str]] = None,
        output_dir: str = "",
    ) -> Dict[str, Any]:
        """Export a complete StackAdapt campaign package.

        Args:
            brand_name: e.g., "LUXY Ride"
            website_url: e.g., "https://luxyride.com"
            archetypes: List of archetype dicts with conversion data
            retargeting_sequences: TherapeuticSequence objects per archetype
            bilateral_analysis: Calibrated alignment analysis results
            domain_whitelist: Approved placement domains
            domain_blacklist: Excluded domains
            daily_budget: Per-campaign daily budget
            campaign_duration_days: Campaign flight duration
            channels: StackAdapt channels to use

        Returns:
            Dict with all campaign components as nested dicts/lists
        """
        channels = channels or ["native", "display"]
        start_date = datetime.now(timezone.utc) + timedelta(days=1)
        end_date = start_date + timedelta(days=campaign_duration_days)

        package = {
            "meta": {
                "brand": brand_name,
                "website": website_url,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": "INFORMATIV Therapeutic Retargeting Engine v33+34",
                "campaign_flight": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d"),
                    "duration_days": campaign_duration_days,
                },
                "channels": channels,
                "total_daily_budget": daily_budget * len(archetypes),
            },

            # 1. Campaign structure (one campaign group per archetype)
            "campaign_groups": self._build_campaign_groups(
                brand_name, archetypes, retargeting_sequences,
                daily_budget, start_date, end_date, channels,
            ),

            # 2. Audience segment definitions (pixel-based)
            "audiences": self._build_audiences(brand_name, website_url, archetypes),

            # 3. Creative specifications per touch
            "creatives": self._build_creatives(
                brand_name, archetypes, retargeting_sequences, bilateral_analysis
            ),

            # 4. Domain targeting
            "site_targeting": {
                "whitelist": domain_whitelist or [],
                "blacklist": domain_blacklist or [],
            },

            # 5. Retargeting rules (sequential with exclusions)
            "retargeting_rules": self._build_retargeting_rules(
                brand_name, archetypes, retargeting_sequences
            ),

            # 6. Frequency capping
            "frequency_capping": self._build_frequency_caps(archetypes),

            # 7. Dayparting schedule
            "dayparting": self._build_dayparting(archetypes),

            # 8. Conversion tracking
            "measurement": self._build_measurement(brand_name, website_url),

            # 9. Calibration metadata (from Enhancement #34)
            "calibration": {
                "composite_weight_version": "v6_data_calibrated",
                "top_conversion_predictors": bilateral_analysis.get("top_predictors", []),
                "frustrated_dimension_pairs": [
                    {"dim_a": a, "dim_b": b, "correlation": r}
                    for a, b, r in FRUSTRATED_DIMENSION_PAIRS[:5]
                ],
                "recalibration_schedule": "Every 500 new edges or weekly",
            },
        }

        return package

    def _build_campaign_groups(
        self, brand_name, archetypes, sequences, budget, start, end, channels
    ):
        """One campaign group per archetype, containing sequential touch campaigns."""
        groups = []
        for arch in archetypes:
            arch_id = arch["archetype_id"]
            arch_name = arch.get("display_name", arch_id.replace("_", " ").title())
            conv_rate = arch.get("conversion_rate", 0)

            # Budget allocation: proportional to expected conversion rate
            budget_weight = max(0.1, conv_rate)
            arch_budget = round(budget * budget_weight / max(sum(a.get("conversion_rate", 0.1) for a in archetypes), 0.1), 2)

            # Find matching sequence
            seq = next((s for s in sequences if s.archetype_id == arch_id), None)
            max_touches = seq.max_touches if seq else 5

            campaigns = []
            for touch_num in range(1, max_touches + 1):
                touch = seq.touches_delivered[touch_num - 1] if seq and touch_num <= len(seq.touches_delivered) else None

                campaign = {
                    "campaign_name": f"{brand_name} — {arch_name} — Touch {touch_num}",
                    "campaign_type": channels[0] if channels else "native",
                    "status": "draft",  # Created as draft for review
                    "budget": {
                        "daily": arch_budget * (0.8 + 0.1 * touch_num),
                        "total": arch_budget * (0.8 + 0.1 * touch_num) * 30,
                        "currency": "USD",
                    },
                    "schedule": {
                        "start_date": start.strftime("%Y-%m-%d"),
                        "end_date": end.strftime("%Y-%m-%d"),
                        "timezone": "America/New_York",
                    },
                    "targeting": {
                        "audience_segment": f"informativ_{arch_id}_{brand_name.lower().replace(' ', '_')}_t{touch_num}",
                        "retargeting_pool": f"touch_{touch_num}_pool",
                        "exclude_audiences": [
                            f"informativ_{arch_id}_converted",
                            *[f"touch_{i}_engaged" for i in range(1, touch_num)],
                        ],
                    },
                    "optimization": {
                        "goal": "conversions" if touch_num >= 3 else "clicks",
                        "bid_strategy": "target_cpa" if touch_num >= 3 else "maximize_clicks",
                    },
                    # INFORMATIV intelligence
                    "informativ_params": {
                        "touch_position": touch_num,
                        "mechanism": touch.mechanism.value if touch else "evidence_proof",
                        "barrier_targeted": touch.target_barrier.value if touch else "trust_deficit",
                        "scaffold_level": touch.scaffold_level.value if touch else 2,
                        "narrative_chapter": touch.narrative_chapter if touch else touch_num,
                        "construal_level": touch.construal_level if touch else ("abstract" if touch_num <= 2 else "concrete"),
                        "autonomy_language": True,
                    },
                }
                campaigns.append(campaign)

            groups.append({
                "group_name": f"{brand_name} — {arch_name}",
                "archetype": arch_id,
                "conversion_rate": conv_rate,
                "budget_allocation_pct": round(budget_weight * 100 / max(sum(a.get("conversion_rate", 0.1) for a in archetypes), 0.1), 1),
                "campaigns": campaigns,
            })

        return groups

    def _build_audiences(self, brand_name, website_url, archetypes):
        """Pixel-based audience segment definitions."""
        brand_slug = brand_name.lower().replace(" ", "_")
        audiences = [
            {
                "name": f"{brand_name} — All Site Visitors",
                "type": "retargeting",
                "pixel_rule": f"url contains {website_url}",
                "lookback_days": 30,
                "min_visits": 1,
            },
            {
                "name": f"{brand_name} — Pricing Page Visitors",
                "type": "retargeting",
                "pixel_rule": f"url contains {website_url}/pricing OR url contains {website_url}/rates",
                "lookback_days": 14,
                "min_visits": 1,
            },
            {
                "name": f"{brand_name} — Booking Started",
                "type": "retargeting",
                "pixel_rule": f"event_name = booking_start",
                "lookback_days": 7,
            },
            {
                "name": f"{brand_name} — Booking Abandoned",
                "type": "retargeting",
                "pixel_rule": f"event_name = booking_start AND NOT event_name = booking_complete",
                "lookback_days": 7,
            },
            {
                "name": f"{brand_name} — Converted (EXCLUDE)",
                "type": "exclusion",
                "pixel_rule": f"event_name = booking_complete OR event_name = purchase",
                "lookback_days": 90,
                "note": "ALWAYS exclude from all retargeting campaigns",
            },
        ]

        # Per-archetype segments
        for arch in archetypes:
            arch_id = arch["archetype_id"]
            audiences.append({
                "name": f"{brand_name} — {arch_id} — Active Sequence",
                "type": "retargeting",
                "informativ_segment_id": f"informativ_{arch_id}_{brand_slug}_t1",
                "description": f"Users classified as {arch_id} by INFORMATIV bilateral intelligence",
            })

        return audiences

    def _build_creatives(self, brand_name, archetypes, sequences, analysis):
        """Creative specifications per archetype per touch."""
        creatives = []
        for arch in archetypes:
            arch_id = arch["archetype_id"]
            seq = next((s for s in sequences if s.archetype_id == arch_id), None)
            if not seq:
                continue

            for touch in seq.touches_delivered:
                strategy = touch.creative_strategy or {}
                cialdini = THERAPEUTIC_TO_CIALDINI.get(touch.mechanism.value, "authority")

                creative = {
                    "name": f"{brand_name} — {arch_id} — Touch {touch.position_in_sequence}",
                    "archetype": arch_id,
                    "touch_position": touch.position_in_sequence,

                    # Creative parameters (from INFORMATIV intelligence)
                    "mechanism": touch.mechanism.value,
                    "cialdini_principle": cialdini,
                    "barrier_targeted": touch.target_barrier.value,
                    "narrative_chapter": touch.narrative_chapter,
                    "narrative_function": touch.narrative_function,
                    "construal_level": touch.construal_level,
                    "processing_route": touch.processing_route,
                    "scaffold_level": touch.scaffold_level.value,

                    # Copy direction
                    "headline_direction": strategy.get("creative_direction", ""),
                    "tone": "warm" if touch.construal_level == "abstract" else "authoritative",
                    "cta_style": "soft" if touch.autonomy_language else "direct",

                    # Testimonial guidance
                    "testimonial_type": touch.testimonial_model_type or "coping",
                    "testimonial_matching": (
                        "Select testimonial from someone who SHARES the prospect's psychology. "
                        f"Archetype: {arch_id}. Barrier: {touch.target_barrier.value}."
                    ),

                    # Frustration warning
                    "frustrated_dimensions": [
                        {"dim": a, "conflicts_with": b, "r": r}
                        for a, b, r in FRUSTRATED_DIMENSION_PAIRS
                        if touch.target_alignment_dimension in (a, b)
                    ],

                    # Ad format specs
                    "formats": {
                        "native": {
                            "headline_max_chars": 50,
                            "body_max_chars": 150,
                            "cta_max_chars": 25,
                            "image_size": "1200x628",
                        },
                        "display": {
                            "sizes": ["300x250", "728x90", "160x600", "320x50"],
                        },
                    },
                }
                creatives.append(creative)

        return creatives

    def _build_retargeting_rules(self, brand_name, archetypes, sequences):
        """Sequential retargeting rules with audience exclusions."""
        rules = {
            "principle": (
                "Each retargeting touch deploys a DIFFERENT mechanism targeting "
                "the specific bilateral alignment gap. Standard retargeting repeats "
                "the same message. This system deploys a diagnostic intervention."
            ),
            "critical_rules": [
                "Do NOT use StackAdapt standard creative rotation",
                "Each touch MUST use the specific creative mapped to that position",
                "Set up as SEQUENTIAL campaigns with audience EXCLUSION rules",
                "After conversion: IMMEDIATELY exclude from ALL retargeting",
                "If CTR drops below 0.03% after 3 touches: pause 72 hours",
            ],
            "per_archetype_sequences": [],
        }

        for arch in archetypes:
            arch_id = arch["archetype_id"]
            seq = next((s for s in sequences if s.archetype_id == arch_id), None)
            if not seq:
                continue

            touches = []
            for touch in seq.touches_delivered:
                touches.append({
                    "position": touch.position_in_sequence,
                    "mechanism": touch.mechanism.value,
                    "barrier": touch.target_barrier.value,
                    "trigger": touch.trigger_type,
                    "min_hours_after_previous": touch.min_hours_after_previous,
                    "max_hours_after_previous": touch.max_hours_after_previous,
                    "audience_rule": f"Touch {touch.position_in_sequence - 1} served AND NOT engaged"
                    if touch.position_in_sequence > 1 else "All qualified visitors",
                })

            rules["per_archetype_sequences"].append({
                "archetype": arch_id,
                "max_touches": seq.max_touches,
                "max_duration_days": seq.max_duration_days,
                "suppression_after_max": f"{seq.suppression_duration_days} days",
                "touches": touches,
            })

        return rules

    def _build_frequency_caps(self, archetypes):
        """Per-archetype frequency capping rules."""
        caps = {}
        for arch in archetypes:
            arch_id = arch["archetype_id"]
            conv_rate = arch.get("conversion_rate", 0.5)

            # Higher converting archetypes can tolerate more impressions
            if conv_rate > 0.4:
                max_day, max_week = 2, 5
            elif conv_rate > 0.1:
                max_day, max_week = 1, 3
            else:
                max_day, max_week = 1, 2  # Low converters: minimal frequency

            caps[arch_id] = {
                "max_impressions_per_day": max_day,
                "max_impressions_per_week": max_week,
                "min_hours_between_impressions": 12,
                "conversion_rate_basis": conv_rate,
            }

        return caps

    def _build_dayparting(self, archetypes):
        """Time-of-day targeting schedule."""
        return {
            "timezone": "America/New_York",
            "schedule": {
                "monday_friday": {
                    "peak_hours": ["07:00-09:00", "17:00-19:00"],
                    "standard_hours": ["09:00-17:00", "19:00-22:00"],
                    "off_hours": ["22:00-07:00"],
                    "bid_adjustments": {
                        "peak": 1.3,
                        "standard": 1.0,
                        "off": 0.5,
                    },
                },
                "saturday_sunday": {
                    "peak_hours": ["09:00-12:00", "16:00-20:00"],
                    "standard_hours": ["12:00-16:00"],
                    "off_hours": ["20:00-09:00"],
                    "bid_adjustments": {
                        "peak": 1.2,
                        "standard": 0.9,
                        "off": 0.4,
                    },
                },
            },
            "note": "Adjust peak hours based on archetype behavior data after first week",
        }

    def _build_measurement(self, brand_name, website_url):
        """Conversion tracking and measurement setup."""
        return {
            "conversion_pixels": [
                {
                    "name": f"{brand_name} — Site Visit",
                    "event_name": "site_visit",
                    "trigger": f"page_url contains {website_url}",
                    "attribution_window_days": 30,
                },
                {
                    "name": f"{brand_name} — Pricing View",
                    "event_name": "pricing_view",
                    "trigger": f"page_url contains /pricing OR page_url contains /rates",
                    "attribution_window_days": 14,
                },
                {
                    "name": f"{brand_name} — Booking Start",
                    "event_name": "booking_start",
                    "trigger": "custom_event = booking_initiated",
                    "attribution_window_days": 7,
                },
                {
                    "name": f"{brand_name} — Booking Complete (PRIMARY)",
                    "event_name": "booking_complete",
                    "trigger": "custom_event = booking_confirmed",
                    "attribution_window_days": 7,
                    "revenue_tracking": True,
                    "is_primary_conversion": True,
                },
            ],
            "kpis": {
                "primary": "cost_per_booking",
                "secondary": [
                    "per_touch_conversion_rate",
                    "stage_advancement_rate",
                    "barrier_resolution_rate",
                    "retargeting_sequence_efficiency",
                ],
            },
            "reporting": {
                "frequency": "daily",
                "breakdowns": ["archetype", "touch_position", "mechanism", "creative"],
                "informativ_hypothesis": (
                    "Each subsequent touch should convert at a HIGHER rate than "
                    "the previous. If touch N converts lower than touch N-1, the "
                    "mechanism mapping is wrong for that archetype."
                ),
            },
        }

    def export_to_files(
        self, package: Dict[str, Any], output_dir: str
    ) -> List[str]:
        """Write the campaign package to individual files.

        Returns list of created file paths.
        """
        from pathlib import Path
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        brand = package["meta"]["brand"].lower().replace(" ", "_")
        files = []

        # Master config
        path = out / f"{brand}_campaign_config.json"
        with open(path, "w") as f:
            json.dump(package, f, indent=2, default=str)
        files.append(str(path))

        # Audiences
        path = out / f"{brand}_audiences.json"
        with open(path, "w") as f:
            json.dump(package["audiences"], f, indent=2)
        files.append(str(path))

        # Creatives
        path = out / f"{brand}_creatives.json"
        with open(path, "w") as f:
            json.dump(package["creatives"], f, indent=2, default=str)
        files.append(str(path))

        # Domain whitelist CSV
        if package["site_targeting"]["whitelist"]:
            path = out / f"{brand}_domain_whitelist.csv"
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["domain"])
                for d in package["site_targeting"]["whitelist"]:
                    writer.writerow([d])
            files.append(str(path))

        # Domain blacklist CSV
        if package["site_targeting"]["blacklist"]:
            path = out / f"{brand}_domain_blacklist.csv"
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["domain"])
                for d in package["site_targeting"]["blacklist"]:
                    writer.writerow([d])
            files.append(str(path))

        # Retargeting rules
        path = out / f"{brand}_retargeting_rules.json"
        with open(path, "w") as f:
            json.dump(package["retargeting_rules"], f, indent=2)
        files.append(str(path))

        # Frequency caps
        path = out / f"{brand}_frequency_caps.json"
        with open(path, "w") as f:
            json.dump(package["frequency_capping"], f, indent=2)
        files.append(str(path))

        # Dayparting
        path = out / f"{brand}_dayparting.json"
        with open(path, "w") as f:
            json.dump(package["dayparting"], f, indent=2)
        files.append(str(path))

        # Measurement
        path = out / f"{brand}_measurement.json"
        with open(path, "w") as f:
            json.dump(package["measurement"], f, indent=2)
        files.append(str(path))

        logger.info("Exported %d files to %s", len(files), output_dir)
        return files
