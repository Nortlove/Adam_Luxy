"""
DCIL Configuration
===================

Safety rails, thresholds, and scheduling for the Daily Campaign Intelligence Loop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DCILConfig:
    """Configuration for the Daily Campaign Intelligence Loop."""

    # --- Safety Rails ---
    max_budget_change_pct_per_campaign: float = 15.0
    max_budget_change_pct_total: float = 25.0
    max_campaigns_paused_per_day: int = 1
    max_domains_removed_per_campaign_per_day: int = 3
    max_domains_added_per_campaign_per_day: int = 5
    min_days_before_mechanism_change: int = 7
    min_conversions_for_action: int = 30
    min_impressions_for_domain_action: int = 500
    cooldown_hours_after_change: int = 48

    # --- Generalizability Thresholds (I²) ---
    i_squared_system_wide: float = 25.0
    i_squared_category_archetype_split: float = 50.0
    i_squared_campaign_specific: float = 75.0
    min_studies_for_meta_analysis: int = 3

    # --- Rollback Triggers ---
    rollback_ctr_drop_pct: float = 50.0
    rollback_cpa_increase_pct: float = 100.0
    rollback_spend_overshoot_pct: float = 50.0
    rollback_window_hours: int = 24

    # --- Statistical Testing ---
    significance_level: float = 0.05
    min_sample_size_per_cell: int = 30
    cusum_threshold_sigma: float = 2.0
    trend_decline_consecutive_days: int = 3

    # --- Reporting Frequency (days between reports) ---
    tier_a_frequency: Dict[str, int] = field(default_factory=lambda: {
        "week_1": 1,
        "week_2_3": 3,
        "week_4_6": 7,
        "week_7_plus": 14,
    })

    # --- Execution Mode ---
    auto_execute: bool = False
    human_approval_required: bool = True

    # --- Redis Keys ---
    redis_prefix: str = "informativ:dcil"
    snapshot_ttl_days: int = 30

    # --- StackAdapt ---
    stackadapt_api_key: str = ""
    stackadapt_advertiser_id: str = ""

    def __post_init__(self):
        if not self.stackadapt_api_key:
            self.stackadapt_api_key = os.environ.get(
                "STACKADAPT_GRAPHQL_KEY",
                os.environ.get("STACKADAPT_API_KEY", ""),
            )
        if not self.stackadapt_advertiser_id:
            self.stackadapt_advertiser_id = os.environ.get(
                "STACKADAPT_ADVERTISER_ID", "",
            )


_config: DCILConfig | None = None


def get_dcil_config() -> DCILConfig:
    global _config
    if _config is None:
        _config = DCILConfig()
    return _config
