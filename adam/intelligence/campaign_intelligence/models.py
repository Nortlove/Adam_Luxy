"""
DCIL Data Models
=================

Shared data structures for the Daily Campaign Intelligence Loop.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LearningScope(Enum):
    SYSTEM_WIDE = "system_wide"
    CATEGORY_LEVEL = "category_level"
    ARCHETYPE_LEVEL = "archetype_level"
    CAMPAIGN_SPECIFIC = "campaign_specific"


class DirectiveType(Enum):
    BUDGET_REALLOCATION = "budget_reallocation"
    PAUSE_RESUME = "pause_resume"
    DOMAIN_TARGETING = "domain_targeting"
    DAYPARTING = "dayparting"
    FREQUENCY_CAP = "frequency_cap"
    MECHANISM_ROTATION = "mechanism_rotation"
    GEO_TARGETING = "geo_targeting"
    CREATIVE_SWAP = "creative_swap"


class DirectiveStatus(Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    BLOCKED = "blocked"
    CAPPED = "capped"
    EXECUTED = "executed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class HypothesisStatus(Enum):
    NOT_TESTED = "not_tested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class FindingSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------------------------------------------------------------------------
# Performance Snapshot
# ---------------------------------------------------------------------------

@dataclass
class CampaignSnapshot:
    """One campaign's performance at a point in time."""
    campaign_id: str
    name: str
    channel_type: str
    group_name: str
    status: str

    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    ctr: float = 0.0
    cpa: float = 0.0
    cvr: float = 0.0
    roas: float = 0.0

    # Mapped by normalizer
    archetype: str = ""
    mechanism: str = ""

    # Domain-level breakdown (if available)
    domain_stats: List[Dict[str, Any]] = field(default_factory=list)

    # Creative-level breakdown (if available)
    creative_stats: List[Dict[str, Any]] = field(default_factory=list)

    def compute_derived(self):
        if self.impressions > 0:
            self.ctr = self.clicks / self.impressions
        if self.conversions > 0:
            self.cpa = self.spend / self.conversions
        if self.clicks > 0:
            self.cvr = self.conversions / self.clicks
        if self.spend > 0 and self.revenue > 0:
            self.roas = self.revenue / self.spend


@dataclass
class PerformanceSnapshot:
    """Full platform snapshot at a point in time."""
    timestamp: float = field(default_factory=time.time)
    date: str = ""
    advertiser_name: str = ""

    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    total_revenue: float = 0.0
    overall_ctr: float = 0.0
    overall_cpa: float = 0.0
    overall_roas: float = 0.0

    campaigns: List[CampaignSnapshot] = field(default_factory=list)

    # Aggregated by archetype
    archetype_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Aggregated by mechanism
    mechanism_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Aggregated by domain (top domains)
    domain_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Rolling averages from historical snapshots
    rolling_3d: Optional[Dict[str, float]] = None
    rolling_7d: Optional[Dict[str, float]] = None

    # Data provenance — Rule 7: never learn from simulated data
    data_source: str = "dsp_api"  # "dsp_api", "manual_import", "simulated"
    provenance_verified: bool = False  # True only when DSP API returned real data
    cascade_decisions_real: bool = True  # False if any decisions came from simulation fallback


# ---------------------------------------------------------------------------
# Hypothesis Testing
# ---------------------------------------------------------------------------

@dataclass
class HypothesisResult:
    """Result of a single hypothesis test."""
    hypothesis_id: str
    hypothesis_name: str
    status: HypothesisStatus
    p_value: float = 1.0
    effect_size: float = 0.0
    effect_type: str = ""  # "proportion_difference", "rate_ratio", "mean_difference"
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    sample_size: int = 0
    test_method: str = ""
    finding: str = ""
    recommendation: str = ""
    action_if_rejected: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Inferential chain: WHY the finding holds, not just WHAT the numbers show.
    # This is the mechanism materialization — without it, the finding is correlational.
    construct_chain: List[str] = field(default_factory=list)
    # e.g., ["low_uncertainty_tolerance", "need_for_closure", "authority_mechanism"]
    chain_conditions: List[str] = field(default_factory=list)
    # e.g., ["cognitive_engagement > 0.6", "construal_level = concrete"]
    chain_exceptions: List[str] = field(default_factory=list)
    # e.g., ["breaks when perceived as manipulative", "weakens under high reactance"]
    theory_update_type: str = ""  # "chain_strengthened", "chain_weakened", "condition_discovered", "exception_found"


@dataclass
class AnomalyDetection:
    """Result of trend/anomaly detection."""
    anomaly_type: str  # "sudden_drop", "gradual_decline", "spike", "change_point"
    severity: FindingSeverity
    metric: str
    campaign_id: str = ""
    archetype: str = ""
    current_value: float = 0.0
    expected_value: float = 0.0
    deviation_sigma: float = 0.0
    description: str = ""


# ---------------------------------------------------------------------------
# Generalizability / Scope
# ---------------------------------------------------------------------------

@dataclass
class ScopedLearning:
    """A finding with its determined generalizability scope."""
    finding_id: str
    finding_type: str  # "mechanism_effectiveness", "domain_performance", etc.
    statement: str
    scope: LearningScope
    i_squared: float
    tau_squared: float
    effect_size: float
    effect_type: str = ""  # "proportion_difference", "rate_ratio", "mean_difference"
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    n_studies: int = 0

    # Inferential chain — the MECHANISM, not just the metric
    construct_chain: List[str] = field(default_factory=list)
    chain_conditions: List[str] = field(default_factory=list)
    chain_exceptions: List[str] = field(default_factory=list)
    theory_update_type: str = ""  # "chain_strengthened", "chain_weakened", "weight_only"

    affected_archetypes: List[str] = field(default_factory=list)
    affected_categories: List[str] = field(default_factory=list)
    affected_campaigns: List[str] = field(default_factory=list)

    neo4j_updates: List[Dict[str, Any]] = field(default_factory=list)
    propagation_config: Dict[str, Any] = field(default_factory=dict)

    source_hypothesis_id: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Optimization Directives
# ---------------------------------------------------------------------------

@dataclass
class Directive:
    """A single optimization action to execute."""
    directive_id: str
    directive_type: DirectiveType
    status: DirectiveStatus = DirectiveStatus.PROPOSED

    # What to change
    campaign_id: str = ""
    campaign_name: str = ""
    archetype: str = ""
    parameter: str = ""  # e.g., "daily_budget", "domain_whitelist", "frequency_cap"
    current_value: Any = None
    proposed_value: Any = None

    # Why
    source_finding_id: str = ""
    rationale: str = ""
    bilateral_evidence: str = ""

    # Impact
    expected_impact: str = ""
    confidence: float = 0.0
    scope: LearningScope = LearningScope.CAMPAIGN_SPECIFIC

    # Safety
    rollback_conditions: List[str] = field(default_factory=list)
    max_change_pct: float = 0.0
    cooldown_hours: int = 48

    # Execution
    executed_at: float = 0.0
    pre_change_snapshot: Dict[str, Any] = field(default_factory=dict)
    execution_result: str = ""

    # Validation
    blocked_reason: str = ""
    capped_from: Any = None

    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Platform State (for coherence validation)
# ---------------------------------------------------------------------------

@dataclass
class PlatformState:
    """Complete platform state assembled for coherence validation."""
    timestamp: float = field(default_factory=time.time)

    # Current campaign configs
    campaigns: List[CampaignSnapshot] = field(default_factory=list)
    total_daily_budget: float = 0.0

    # Neo4j learning state
    bayesian_priors: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    responds_to_edges: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Thompson posteriors (in-memory)
    thompson_posteriors: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # Recent execution history
    recent_directives: List[Directive] = field(default_factory=list)
    recent_rollbacks: List[Dict[str, Any]] = field(default_factory=list)

    # Knowledge propagation state
    kpn_state: Dict[str, Any] = field(default_factory=dict)

    # Gradient field priorities
    gradient_priorities: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

@dataclass
class AuditEntry:
    """One entry in the DCIL audit log."""
    timestamp: float = field(default_factory=time.time)
    stage: str = ""  # "pull", "normalize", "hypothesis", "scope", "directive", "validate", "execute", "report", "rollback"
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    finding_ids: List[str] = field(default_factory=list)
    directive_ids: List[str] = field(default_factory=list)
    scope: str = ""
    success: bool = True
    error: str = ""


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@dataclass
class TierAReport:
    """Customer-facing report."""
    date: str = ""
    period_label: str = ""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    archetype_distribution: Dict[str, float] = field(default_factory=dict)
    top_domains: List[Dict[str, Any]] = field(default_factory=list)
    geo_heatmap: Dict[str, int] = field(default_factory=dict)
    creative_winners: List[Dict[str, str]] = field(default_factory=list)
    customer_profile_summary: str = ""


@dataclass
class TierBReport:
    """Optimization engine summary."""
    date: str = ""
    hypotheses_tested: List[HypothesisResult] = field(default_factory=list)
    directives_generated: int = 0
    directives_approved: int = 0
    directives_blocked: int = 0
    directives_executed: int = 0
    changes_made: List[Dict[str, str]] = field(default_factory=list)
    learning_updates: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TierCReport:
    """Internal audit and system-wide learning report."""
    date: str = ""
    posterior_state: Dict[str, Any] = field(default_factory=dict)
    domain_accuracy: Dict[str, float] = field(default_factory=dict)
    creative_genealogy: List[Dict[str, Any]] = field(default_factory=list)
    suppression_effectiveness: Dict[str, Any] = field(default_factory=dict)
    scoped_learnings: List[ScopedLearning] = field(default_factory=list)
    generalizability_summary: Dict[str, int] = field(default_factory=dict)
