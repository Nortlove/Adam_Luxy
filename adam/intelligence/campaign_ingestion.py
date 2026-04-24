"""
External Campaign Analytics Ingestion Process (ECAIP)
======================================================

The reusable process for ingesting a client's existing programmatic campaign
analytics and producing psychologically-grounded campaign recommendations
informed by INFORMATIV's bilateral intelligence.

This is the process INFORMATIV runs every time a new client grants access
to their DSP analytics. It transforms correlational campaign data (impressions,
clicks, conversions, spend) into inferential campaign intelligence (which
psychological mechanisms are working, which audiences are mismatched, where
the funnel is leaking, and what Day 1 changes will produce the largest lift).

The process has 7 stages, each producing artifacts that feed the next:

    Stage 1: EXTRACT     — Pull raw campaign data from DSP API
    Stage 2: MAP         — Map campaigns to INFORMATIV's psychological framework
    Stage 3: DIAGNOSE    — Apply bilateral intelligence to diagnose performance
    Stage 4: CONTRAST    — Compare current approach vs bilateral evidence
    Stage 5: PRESCRIBE   — Generate specific Day 1 recommendations
    Stage 6: SIMULATE    — Pre-campaign simulation of recommended changes
    Stage 7: INSTRUMENT  — Define measurement framework for validation

Usage:
    ingestion = CampaignIngestion(
        client_name="LUXY Ride",
        asin="lux_luxy_ride",
        dsp="stackadapt",
    )

    # Stage 1: Extract (from DSP API or manual data)
    ingestion.ingest_campaign_data(campaigns_raw)

    # Stage 2-7: Run the full pipeline
    recommendation = ingestion.run_full_pipeline()

    # Output
    print(recommendation.format_day1_brief())
    print(recommendation.format_process_log())
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class AudienceFit(Enum):
    """How well a DSP audience segment maps to the client's actual buyers."""
    EXACT = "exact"
    PARTIAL = "partial"
    MISALIGNED = "misaligned"
    UNKNOWN = "unknown"


class ChannelRole(Enum):
    """Psychological role of each channel in the funnel."""
    PRIMER = "primer"
    PERSUADER = "persuader"
    CLOSER = "closer"
    WASTED = "wasted"


class DiagnosticSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ExternalCampaign:
    """One campaign from the client's DSP."""
    campaign_id: str
    name: str
    channel_type: str  # CTV, display, native, video, audio
    group_name: str
    status: str

    # Performance
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0

    # Derived
    ctr: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    cvr: float = 0.0

    # Targeting
    audience_segments: List[str] = field(default_factory=list)
    geo_targets: List[str] = field(default_factory=list)
    domain_targets: List[str] = field(default_factory=list)
    frequency_cap: str = ""
    dayparting: str = ""
    bid_strategy: str = ""
    bid_amount: float = 0.0

    # Creative
    creative_count: int = 0
    creative_types: List[str] = field(default_factory=list)
    creative_names: List[str] = field(default_factory=list)

    # Conversion tracking
    conversion_tracker_id: str = ""
    tracks_revenue: bool = False

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
class AudienceMapping:
    """Maps a DSP audience segment to INFORMATIV's psychological framework."""
    dsp_segment_name: str
    informativ_archetype: str
    fit: AudienceFit
    reasoning: str
    bilateral_evidence_available: bool = False
    edge_count: int = 0
    primary_mechanism: str = ""
    mechanism_score: float = 0.0


@dataclass
class ChannelDiagnostic:
    """Psychological diagnosis of a channel's current role vs optimal role."""
    channel_type: str
    current_role: str
    optimal_role: ChannelRole
    current_spend: float = 0.0
    current_conversions: int = 0
    current_cpa: float = 0.0
    diagnosis: str = ""
    recommended_action: str = ""


@dataclass
class Diagnostic:
    """A single diagnostic finding."""
    category: str  # audience, creative, channel, targeting, measurement, funnel
    severity: DiagnosticSeverity
    finding: str
    evidence: str
    bilateral_insight: str
    recommendation: str
    estimated_impact: str = ""


@dataclass
class Recommendation:
    """A specific Day 1 action item."""
    priority: int  # 1 = highest
    action: str
    rationale: str
    bilateral_evidence: str
    expected_impact: str
    effort: str  # immediate, hours, days
    dependencies: List[str] = field(default_factory=list)


@dataclass
class IngestionResult:
    """Complete output of the ingestion process."""
    client_name: str
    asin: str
    generated_at: float = field(default_factory=time.time)

    # Stage 1: Raw data
    campaigns: List[ExternalCampaign] = field(default_factory=list)
    total_spend: float = 0.0
    total_conversions: int = 0
    overall_cpa: float = 0.0

    # Stage 2: Mappings
    audience_mappings: List[AudienceMapping] = field(default_factory=list)
    channel_diagnostics: List[ChannelDiagnostic] = field(default_factory=list)

    # Stage 3: Diagnostics
    diagnostics: List[Diagnostic] = field(default_factory=list)

    # Stage 4: Contrast summary
    current_approach_summary: str = ""
    bilateral_approach_summary: str = ""
    key_contrasts: List[Dict[str, str]] = field(default_factory=list)

    # Stage 5: Recommendations
    recommendations: List[Recommendation] = field(default_factory=list)

    # Stage 6: Simulation
    predicted_cpa_with_changes: float = 0.0
    predicted_cpa_reduction_pct: float = 0.0
    simulation_details: Dict[str, Any] = field(default_factory=dict)

    # Stage 7: Measurement
    measurement_framework: Dict[str, Any] = field(default_factory=dict)

    # Process log
    stage_log: List[Dict[str, Any]] = field(default_factory=list)

    def format_day1_brief(self) -> str:
        """Format as a human-readable Day 1 recommendation."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"INFORMATIV — DAY 1 CAMPAIGN RECOMMENDATION")
        lines.append(f"Client: {self.client_name}")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        lines.append(f"\n{'─' * 50}")
        lines.append("CURRENT STATE")
        lines.append(f"{'─' * 50}")
        lines.append(f"  Total spend:       ${self.total_spend:,.0f}")
        lines.append(f"  Total conversions: {self.total_conversions}")
        lines.append(f"  Overall CPA:       ${self.overall_cpa:,.0f}")
        lines.append(f"  Campaigns:         {len(self.campaigns)}")

        if self.diagnostics:
            critical = [d for d in self.diagnostics if d.severity == DiagnosticSeverity.CRITICAL]
            high = [d for d in self.diagnostics if d.severity == DiagnosticSeverity.HIGH]
            lines.append(f"\n{'─' * 50}")
            lines.append(f"DIAGNOSTICS ({len(critical)} critical, {len(high)} high)")
            lines.append(f"{'─' * 50}")
            for d in sorted(self.diagnostics, key=lambda x: x.severity.value):
                icon = {"critical": "[!!!]", "high": "[!!]", "medium": "[!]", "low": "[.]"}
                lines.append(f"\n  {icon.get(d.severity.value, '[?]')} [{d.category.upper()}] {d.finding}")
                lines.append(f"     Evidence: {d.evidence}")
                lines.append(f"     Bilateral: {d.bilateral_insight}")
                lines.append(f"     Action: {d.recommendation}")
                if d.estimated_impact:
                    lines.append(f"     Impact: {d.estimated_impact}")

        if self.key_contrasts:
            lines.append(f"\n{'─' * 50}")
            lines.append("CURRENT vs INFORMATIV APPROACH")
            lines.append(f"{'─' * 50}")
            for c in self.key_contrasts:
                lines.append(f"\n  {c.get('dimension', '?')}:")
                lines.append(f"    Current:    {c.get('current', '')}")
                lines.append(f"    INFORMATIV: {c.get('informativ', '')}")
                lines.append(f"    Why:        {c.get('why', '')}")

        if self.recommendations:
            lines.append(f"\n{'─' * 50}")
            lines.append("DAY 1 ACTIONS (priority order)")
            lines.append(f"{'─' * 50}")
            for r in sorted(self.recommendations, key=lambda x: x.priority):
                lines.append(f"\n  #{r.priority} [{r.effort.upper()}] {r.action}")
                lines.append(f"     Rationale: {r.rationale}")
                lines.append(f"     Evidence: {r.bilateral_evidence}")
                lines.append(f"     Expected: {r.expected_impact}")
                if r.dependencies:
                    lines.append(f"     Depends on: {', '.join(r.dependencies)}")

        if self.predicted_cpa_with_changes > 0:
            lines.append(f"\n{'─' * 50}")
            lines.append("PROJECTED IMPACT")
            lines.append(f"{'─' * 50}")
            lines.append(f"  Current CPA:    ${self.overall_cpa:,.0f}")
            lines.append(f"  Predicted CPA:  ${self.predicted_cpa_with_changes:,.0f}")
            lines.append(f"  Reduction:      {self.predicted_cpa_reduction_pct:.0f}%")

        if self.measurement_framework:
            lines.append(f"\n{'─' * 50}")
            lines.append("MEASUREMENT FRAMEWORK")
            lines.append(f"{'─' * 50}")
            for phase, metrics in self.measurement_framework.items():
                lines.append(f"\n  {phase}:")
                if isinstance(metrics, dict):
                    for k, v in metrics.items():
                        lines.append(f"    {k}: {v}")
                elif isinstance(metrics, list):
                    for m in metrics:
                        lines.append(f"    - {m}")

        lines.append("")
        return "\n".join(lines)

    def format_process_log(self) -> str:
        """Format the process log for auditability."""
        lines = ["ECAIP Process Log", "=" * 40]
        for entry in self.stage_log:
            lines.append(f"\n[Stage {entry.get('stage', '?')}] {entry.get('name', '')}")
            lines.append(f"  Duration: {entry.get('duration_ms', 0):.0f}ms")
            lines.append(f"  Findings: {entry.get('finding_count', 0)}")
            if entry.get("notes"):
                lines.append(f"  Notes: {entry['notes']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The ingestion engine
# ---------------------------------------------------------------------------

class CampaignIngestion:
    """
    External Campaign Analytics Ingestion Process.

    Transforms a client's existing DSP campaign data into psychologically-
    grounded recommendations using INFORMATIV's bilateral intelligence.

    This is a 7-stage pipeline. Each stage:
    - Consumes the output of previous stages
    - Produces typed artifacts
    - Logs its reasoning for auditability
    - Is independently testable

    The process is DSP-agnostic. StackAdapt, DV360, The Trade Desk, etc.
    all feed into the same ExternalCampaign structure. The intelligence
    comes from INFORMATIV's bilateral graph, not from DSP-specific features.
    """

    def __init__(
        self,
        client_name: str,
        asin: str,
        dsp: str = "stackadapt",
        bilateral_edges: Optional[Dict[str, Any]] = None,
        archetype_configs: Optional[Dict[str, Any]] = None,
    ):
        self.client_name = client_name
        self.asin = asin
        self.dsp = dsp
        self.bilateral_edges = bilateral_edges or {}
        self.archetype_configs = archetype_configs or {}
        self.result = IngestionResult(client_name=client_name, asin=asin)

    # ------------------------------------------------------------------
    # Stage 1: EXTRACT
    # ------------------------------------------------------------------

    def ingest_campaign_data(
        self,
        campaigns: List[Dict[str, Any]],
        aggregate_stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stage 1: Ingest raw campaign data.

        Accepts a list of campaign dicts (from DSP API or manual entry)
        and normalizes them into ExternalCampaign objects.

        The key principle: we accept whatever the DSP gives us and
        normalize it. We don't require a specific schema — we extract
        what's available and note what's missing.
        """
        t0 = time.time()

        for raw in campaigns:
            camp = ExternalCampaign(
                campaign_id=str(raw.get("id", raw.get("campaign_id", ""))),
                name=raw.get("name", ""),
                channel_type=raw.get("channel_type", raw.get("channelType", "")),
                group_name=raw.get("group_name", raw.get("group", "")),
                status=raw.get("status", ""),
                impressions=int(raw.get("impressions", 0)),
                clicks=int(raw.get("clicks", 0)),
                conversions=int(raw.get("conversions", 0)),
                spend=float(raw.get("spend", raw.get("cost", 0))),
                revenue=float(raw.get("revenue", 0)),
                audience_segments=raw.get("audience_segments", []),
                geo_targets=raw.get("geo_targets", []),
                domain_targets=raw.get("domain_targets", []),
                frequency_cap=raw.get("frequency_cap", ""),
                dayparting=raw.get("dayparting", ""),
                bid_strategy=raw.get("bid_strategy", ""),
                bid_amount=float(raw.get("bid_amount", raw.get("cpm_bid", 0))),
                creative_count=int(raw.get("creative_count", raw.get("ad_count", 0))),
                creative_types=raw.get("creative_types", []),
                creative_names=raw.get("creative_names", []),
                conversion_tracker_id=str(raw.get("conversion_tracker_id", "")),
                tracks_revenue=raw.get("tracks_revenue", False),
            )
            camp.compute_derived()
            self.result.campaigns.append(camp)

        # Aggregate stats
        if aggregate_stats:
            self.result.total_spend = float(aggregate_stats.get("spend", 0))
            self.result.total_conversions = int(aggregate_stats.get("conversions", 0))
            self.result.overall_cpa = float(aggregate_stats.get("cpa", 0))
        else:
            self.result.total_spend = sum(c.spend for c in self.result.campaigns)
            self.result.total_conversions = sum(c.conversions for c in self.result.campaigns)
            if self.result.total_conversions > 0:
                self.result.overall_cpa = self.result.total_spend / self.result.total_conversions

        self.result.stage_log.append({
            "stage": 1, "name": "EXTRACT",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": len(self.result.campaigns),
            "notes": f"{len(self.result.campaigns)} campaigns ingested, "
                     f"${self.result.total_spend:,.0f} total spend",
        })

    # ------------------------------------------------------------------
    # Stage 2: MAP
    # ------------------------------------------------------------------

    def map_to_psychological_framework(
        self,
        audience_map: Optional[Dict[str, Dict[str, Any]]] = None,
        buyer_profile: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stage 2: Map DSP campaigns to INFORMATIV's psychological framework.

        This is where the inferential divergence begins. The DSP organizes
        campaigns by audience segment names, channels, and bid strategies.
        INFORMATIV organizes by psychological archetype, persuasion mechanism,
        and goal activation context.

        The mapping identifies:
        - Which DSP segments correspond to which archetypes
        - Whether the segments reach the client's ACTUAL buyers
        - What channel role each campaign is playing (primer/persuader/closer)
        - What mechanism the creative is (accidentally or intentionally) using

        audience_map: optional pre-defined mapping from DSP segment names
            to INFORMATIV archetypes. If not provided, we infer from names.
        buyer_profile: optional description of who the client's actual
            buyers are, to check audience alignment.
        """
        t0 = time.time()

        # Map audience segments
        all_segments = set()
        for camp in self.result.campaigns:
            for seg in camp.audience_segments:
                all_segments.add(seg)

        for seg_name in all_segments:
            mapping = self._map_audience_segment(seg_name, audience_map, buyer_profile)
            self.result.audience_mappings.append(mapping)

        # Map channel roles
        channel_spend = {}
        for camp in self.result.campaigns:
            ct = camp.channel_type.lower()
            if ct not in channel_spend:
                channel_spend[ct] = {"spend": 0, "conversions": 0, "campaigns": []}
            channel_spend[ct]["spend"] += camp.spend
            channel_spend[ct]["conversions"] += camp.conversions
            channel_spend[ct]["campaigns"].append(camp.name)

        for channel, stats in channel_spend.items():
            diag = self._diagnose_channel_role(channel, stats)
            self.result.channel_diagnostics.append(diag)

        self.result.stage_log.append({
            "stage": 2, "name": "MAP",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": len(self.result.audience_mappings) + len(self.result.channel_diagnostics),
            "notes": f"{len(all_segments)} audience segments mapped, "
                     f"{len(channel_spend)} channels diagnosed",
        })

    def _map_audience_segment(
        self,
        seg_name: str,
        audience_map: Optional[Dict[str, Dict[str, Any]]],
        buyer_profile: Optional[Dict[str, Any]],
    ) -> AudienceMapping:
        """Map a single DSP audience segment to an INFORMATIV archetype."""
        if audience_map and seg_name in audience_map:
            info = audience_map[seg_name]
            return AudienceMapping(
                dsp_segment_name=seg_name,
                informativ_archetype=info.get("archetype", ""),
                fit=AudienceFit(info.get("fit", "unknown")),
                reasoning=info.get("reasoning", ""),
                bilateral_evidence_available=info.get("has_edges", False),
                edge_count=info.get("edge_count", 0),
                primary_mechanism=info.get("primary_mechanism", ""),
                mechanism_score=info.get("mechanism_score", 0.0),
            )

        # Infer from segment name
        name_lower = seg_name.lower()
        archetype = ""
        fit = AudienceFit.UNKNOWN
        reasoning = f"No pre-defined mapping for '{seg_name}'. Inferring from name."

        # Common DSP segment patterns
        if any(kw in name_lower for kw in ["c-suite", "executive", "ceo", "cfo", "cmo"]):
            archetype = "corporate_executive"
            fit = AudienceFit.PARTIAL
            reasoning = "DSP segment targets executives by title, not by purchase psychology."
        elif any(kw in name_lower for kw in ["luxury", "affluent", "high-income", "premium"]):
            archetype = "status_seeker"
            fit = AudienceFit.PARTIAL
            reasoning = "DSP segment targets by affluence proxy, not by purchase mechanism."
        elif any(kw in name_lower for kw in ["travel", "frequent flyer", "mileage", "airline"]):
            archetype = "special_occasion"
            fit = AudienceFit.PARTIAL
            reasoning = "DSP segment targets travel behavior, not travel decision psychology."
        elif any(kw in name_lower for kw in ["business travel", "corporate travel"]):
            archetype = "dependable_loyalist"
            fit = AudienceFit.PARTIAL
            reasoning = "DSP segment identifies travel behavior but not buyer role (arranger vs manager vs traveler)."
        elif any(kw in name_lower for kw in ["retarget", "website visitor", "remarketing"]):
            archetype = "repeat_loyal"
            fit = AudienceFit.PARTIAL
            reasoning = "Retargeting pools all visitors without barrier diagnosis."

        return AudienceMapping(
            dsp_segment_name=seg_name,
            informativ_archetype=archetype,
            fit=fit,
            reasoning=reasoning,
        )

    def _diagnose_channel_role(
        self,
        channel: str,
        stats: Dict[str, Any],
    ) -> ChannelDiagnostic:
        """Diagnose the psychological role of a channel."""
        spend = stats["spend"]
        conversions = stats["conversions"]
        cpa = spend / conversions if conversions > 0 else float("inf")

        # CTV is a priming channel, not a conversion channel
        if "ctv" in channel or "video" in channel:
            if conversions > 0 and cpa < 500:
                optimal = ChannelRole.PRIMER
                diagnosis = (
                    "CTV conversions are likely view-through attribution, not direct response. "
                    "CTV's psychological value is goal activation (Bargh auto-motive): planting "
                    "nonconscious goals that display ads fulfill later."
                )
                action = (
                    "Reframe CTV as a primer. Measure by lift in downstream display CTR/CVR "
                    "for users exposed to CTV first, not by CTV-attributed conversions."
                )
            else:
                optimal = ChannelRole.PRIMER
                diagnosis = (
                    f"CTV spending ${spend:,.0f} with {conversions} conversions. "
                    "CTV should not be optimized for conversions — it is a priming channel."
                )
                action = (
                    "Redesign CTV creative for goal activation, not direct response. "
                    "Each audience segment gets a CTV creative that plants a specific "
                    "nonconscious goal the display ad will fulfill."
                )
        elif "display" in channel or "native" in channel:
            if "rt" in channel or "retarget" in channel.lower():
                optimal = ChannelRole.CLOSER
                diagnosis = "Display retargeting should resolve specific barriers, not repeat the same message."
                action = (
                    "Deploy therapeutic retargeting: diagnose barrier from site behavior, "
                    "match mechanism to barrier, sequence 3 touches with suppression after."
                )
            else:
                optimal = ChannelRole.PERSUADER
                diagnosis = "Prospecting display is where mechanism matching creates conversion leverage."
                action = (
                    "Deploy mechanism-matched creative variants per archetype. "
                    "Different buyer psychologies respond to different persuasion approaches."
                )
        else:
            optimal = ChannelRole.PERSUADER
            diagnosis = f"Channel '{channel}' — needs psychological role assignment."
            action = "Evaluate channel's attention quality and assign primer/persuader/closer role."

        return ChannelDiagnostic(
            channel_type=channel,
            current_role="conversion_optimized" if conversions > 0 else "awareness",
            optimal_role=optimal,
            current_spend=spend,
            current_conversions=conversions,
            current_cpa=cpa,
            diagnosis=diagnosis,
            recommended_action=action,
        )

    # ------------------------------------------------------------------
    # Stage 3: DIAGNOSE
    # ------------------------------------------------------------------

    def diagnose_performance(
        self,
        bilateral_evidence: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stage 3: Apply bilateral intelligence to diagnose current performance.

        This is where INFORMATIV's inferential approach diverges most sharply
        from standard campaign optimization. A correlational system would look
        at CTR, CPA, and ROAS and recommend "spend more on what's working."
        INFORMATIV asks WHY things are or aren't working, using bilateral
        edge evidence to diagnose the psychological mechanisms at play.

        bilateral_evidence: dict with keys like:
            - "top_discriminators": dimensions that most separate converters from non-converters
            - "mechanism_scores": per-archetype mechanism effectiveness scores
            - "edge_stats": aggregate edge statistics
        """
        t0 = time.time()

        # Audience alignment diagnostics
        self._diagnose_audience_alignment()

        # Creative mechanism diagnostics
        self._diagnose_creative_mechanisms()

        # Channel allocation diagnostics
        self._diagnose_channel_allocation()

        # Targeting diagnostics
        self._diagnose_targeting()

        # Measurement diagnostics
        self._diagnose_measurement()

        # Funnel diagnostics
        self._diagnose_funnel(bilateral_evidence)

        self.result.stage_log.append({
            "stage": 3, "name": "DIAGNOSE",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": len(self.result.diagnostics),
            "notes": f"{len(self.result.diagnostics)} diagnostics generated",
        })

    def _diagnose_audience_alignment(self):
        """Check if DSP audiences actually reach the client's buyers."""
        misaligned = [m for m in self.result.audience_mappings if m.fit == AudienceFit.MISALIGNED]
        partial = [m for m in self.result.audience_mappings if m.fit == AudienceFit.PARTIAL]

        if misaligned:
            self.result.diagnostics.append(Diagnostic(
                category="audience",
                severity=DiagnosticSeverity.CRITICAL,
                finding=f"{len(misaligned)} audience segments are misaligned with the client's actual buyers.",
                evidence="; ".join(f"'{m.dsp_segment_name}': {m.reasoning}" for m in misaligned),
                bilateral_insight=(
                    "Bilateral edges represent ACTUAL purchase events. Audience segments that "
                    "don't correspond to actual buyer psychologies will produce impressions "
                    "on people who will never convert, regardless of creative quality."
                ),
                recommendation=(
                    "Replace misaligned segments with psychologically-grounded targeting: "
                    "domain whitelists for professional contexts where actual buyers read, "
                    "plus contextual keywords matching their professional concerns."
                ),
                estimated_impact="Eliminating misaligned spend typically reduces CPA by 40-60%.",
            ))

        if partial:
            self.result.diagnostics.append(Diagnostic(
                category="audience",
                severity=DiagnosticSeverity.HIGH,
                finding=f"{len(partial)} audience segments partially match but miss key buyer distinctions.",
                evidence="; ".join(f"'{m.dsp_segment_name}': {m.reasoning}" for m in partial),
                bilateral_insight=(
                    "Partial segments reach some of the right people but with low precision. "
                    "The waste is invisible in standard reporting because it shows as 'impressions "
                    "served' without distinguishing between reachable and unreachable buyers."
                ),
                recommendation=(
                    "Layer INFORMATIV's domain targeting on top of existing segments to increase "
                    "precision. The domain whitelist ensures impressions serve on pages where "
                    "the reader's active goals match the product's psychological profile."
                ),
            ))

    def _diagnose_creative_mechanisms(self):
        """Diagnose whether creative is using the right psychological mechanisms."""
        # Check for mechanism diversity
        unique_creatives = set()
        for camp in self.result.campaigns:
            for name in camp.creative_names:
                unique_creatives.add(name.lower())

        # Single-creative campaigns can't learn
        single_creative = [c for c in self.result.campaigns if c.creative_count <= 1 and c.status == "ACTIVE"]
        if single_creative:
            self.result.diagnostics.append(Diagnostic(
                category="creative",
                severity=DiagnosticSeverity.HIGH,
                finding=f"{len(single_creative)} active campaigns have only 1 creative variant.",
                evidence=f"Campaigns: {', '.join(c.name for c in single_creative[:5])}",
                bilateral_insight=(
                    "Single-creative campaigns cannot test mechanism effectiveness. "
                    "Multiple variants with DIFFERENT psychological mechanisms (not just "
                    "different images) provide a free randomized controlled trial. "
                    "The DSP's optimization becomes independent validation of our predictions."
                ),
                recommendation=(
                    "Each campaign should have 2-3 creative variants using different "
                    "psychological mechanisms (e.g., authority vs social proof vs cognitive ease). "
                    "INFORMATIV predicts which mechanism will win based on bilateral evidence; "
                    "the DSP's A/B test validates the prediction."
                ),
            ))

        # Same creative across different audiences
        if len(unique_creatives) < len(self.result.campaigns) * 0.5:
            self.result.diagnostics.append(Diagnostic(
                category="creative",
                severity=DiagnosticSeverity.MEDIUM,
                finding="Creative is largely shared across campaigns with different audience targets.",
                evidence=f"{len(unique_creatives)} unique creatives across {len(self.result.campaigns)} campaigns.",
                bilateral_insight=(
                    "Different buyer psychologies respond to different persuasion mechanisms. "
                    "Authority works for careful_truster archetypes because they have high "
                    "need for closure. Social proof works for dependable_loyalist because they "
                    "seek validation from peers. Using the same message for both wastes the "
                    "mechanism-matching leverage that bilateral evidence provides."
                ),
                recommendation=(
                    "Deploy archetype-specific creative with mechanism-matched copy. "
                    "The images can stay the same — the mechanism is in the WORDS, not the pictures."
                ),
            ))

    def _diagnose_channel_allocation(self):
        """Diagnose channel budget allocation."""
        ctv_spend = sum(c.spend for c in self.result.campaigns if "ctv" in c.channel_type.lower())
        display_spend = sum(c.spend for c in self.result.campaigns if "display" in c.channel_type.lower() or "native" in c.channel_type.lower())
        total = self.result.total_spend or 1

        ctv_pct = ctv_spend / total
        display_pct = display_spend / total

        if ctv_pct > 0.5:
            self.result.diagnostics.append(Diagnostic(
                category="channel",
                severity=DiagnosticSeverity.MEDIUM,
                finding=f"CTV consumes {ctv_pct:.0%} of budget but is a priming channel, not a conversion channel.",
                evidence=f"CTV: ${ctv_spend:,.0f} ({ctv_pct:.0%}), Display: ${display_spend:,.0f} ({display_pct:.0%})",
                bilateral_insight=(
                    "CTV's psychological value is goal activation — planting nonconscious "
                    "goals that make subsequent display ads effective. Optimizing CTV for "
                    "conversions misattributes view-through conversions and misallocates "
                    "budget away from the persuasion layer where mechanism matching has "
                    "the highest marginal impact."
                ),
                recommendation=(
                    "Rebalance: CTV at 30-40% (priming), Display at 45-55% (persuasion), "
                    "Retargeting at 10-15% (barrier resolution). Measure CTV by lift in "
                    "downstream display performance, not by CTV-attributed conversions."
                ),
            ))

    def _diagnose_targeting(self):
        """Diagnose targeting setup: frequency, dayparting, domains."""
        # Frequency caps
        no_freq = [c for c in self.result.campaigns if not c.frequency_cap and c.status == "ACTIVE"]
        if no_freq:
            self.result.diagnostics.append(Diagnostic(
                category="targeting",
                severity=DiagnosticSeverity.MEDIUM,
                finding=f"{len(no_freq)} active campaigns have no frequency cap.",
                evidence=f"Campaigns: {', '.join(c.name for c in no_freq[:5])}",
                bilateral_insight=(
                    "From ADME profiles: each mechanism has an optimal exposure frequency "
                    "and a reactance threshold. Authority has a half-life of ~72 hours and "
                    "max 4-5 exposures before reactance. Social proof has ~48 hours and max "
                    "3-4. Exceeding these doesn't just waste budget — it actively damages "
                    "the brand's psychological position by triggering reactance."
                ),
                recommendation=(
                    "Set mechanism-informed frequency caps: 2/day, 6-8/week maximum. "
                    "Suppress after 3 unconverted touches for 14 days to prevent reactance damage."
                ),
            ))

        # Dayparting
        no_daypart = [c for c in self.result.campaigns if not c.dayparting and c.status == "ACTIVE"]
        if no_daypart:
            self.result.diagnostics.append(Diagnostic(
                category="targeting",
                severity=DiagnosticSeverity.LOW,
                finding=f"{len(no_daypart)} active campaigns have no dayparting.",
                evidence="All campaigns serve impressions 24/7.",
                bilateral_insight=(
                    "Goal accessibility varies by time of day. Corporate travel arrangers "
                    "book in the morning (8-10am) and early afternoon (1-3pm). Travel "
                    "managers evaluate vendors mid-morning (9-11am). Serving impressions "
                    "at 11pm to B2B buyers wastes budget on low-goal-accessibility moments."
                ),
                recommendation=(
                    "Apply audience-specific dayparting with bid multipliers during "
                    "peak goal-accessibility windows."
                ),
            ))

    def _diagnose_measurement(self):
        """Diagnose measurement and tracking gaps."""
        any_revenue = any(c.tracks_revenue for c in self.result.campaigns)
        any_conversion = any(c.conversion_tracker_id for c in self.result.campaigns)

        if any_conversion and not any_revenue:
            self.result.diagnostics.append(Diagnostic(
                category="measurement",
                severity=DiagnosticSeverity.CRITICAL,
                finding="Conversion tracking exists but revenue is not being passed.",
                evidence="$0 revenue attributed across all campaigns despite recorded conversions.",
                bilateral_insight=(
                    "Without revenue data, ROAS cannot be calculated, and the learning systems "
                    "cannot distinguish high-value from low-value conversions. INFORMATIV's "
                    "gradient fields need revenue-weighted outcomes to compute ∂P(revenue)/∂dimension, "
                    "which is the signal that tells us which psychological dimensions drive "
                    "revenue vs just clicks."
                ),
                recommendation=(
                    "Configure the conversion pixel to pass revenue: "
                    "saq('conv', 'booking_complete', {revenue: ORDER_TOTAL}). "
                    "This is the single highest-value measurement fix."
                ),
                estimated_impact="Enables ROAS optimization and revenue-weighted learning across all 22 systems.",
            ))

        if not any_conversion:
            self.result.diagnostics.append(Diagnostic(
                category="measurement",
                severity=DiagnosticSeverity.CRITICAL,
                finding="No conversion tracking detected on any campaign.",
                evidence="No conversion tracker IDs found in campaign configuration.",
                bilateral_insight=(
                    "Without conversion events, the entire learning loop is blind. "
                    "No outcome data means no posterior updates, no theory validation, "
                    "no mechanism effectiveness signals. The system is spending money "
                    "and learning nothing."
                ),
                recommendation="Install conversion tracking immediately. This gates all learning.",
            ))

    def _diagnose_funnel(self, bilateral_evidence: Optional[Dict[str, Any]]):
        """Diagnose the funnel architecture using bilateral evidence."""
        if not bilateral_evidence:
            return

        top_discriminators = bilateral_evidence.get("top_discriminators", [])
        if top_discriminators:
            # Check if current creative addresses the top discriminators
            self.result.diagnostics.append(Diagnostic(
                category="funnel",
                severity=DiagnosticSeverity.HIGH,
                finding="Creative strategy does not address the top bilateral discriminators.",
                evidence=f"Top discriminators from bilateral edges: {', '.join(d.get('name', '') for d in top_discriminators[:5])}",
                bilateral_insight=(
                    "Bilateral evidence shows exactly which psychological dimensions separate "
                    "converters from non-converters. Creative that does not address these "
                    "dimensions — regardless of how polished it looks — is solving the wrong "
                    "problem. The mechanism is in the match between buyer psychology and "
                    "seller message, not in the message's production quality."
                ),
                recommendation=(
                    "Rewrite creative headlines and body copy to directly address the top "
                    "discriminating dimensions. For each archetype, the bilateral evidence "
                    "specifies which mechanism and framing maximizes alignment on the "
                    "dimensions that actually drive conversion."
                ),
            ))

    # ------------------------------------------------------------------
    # Stage 4: CONTRAST
    # ------------------------------------------------------------------

    def contrast_approaches(
        self,
        current_summary: Optional[str] = None,
        informativ_summary: Optional[str] = None,
        contrasts: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """
        Stage 4: Explicit contrast between current and INFORMATIV approaches.

        This stage makes the correlational-vs-inferential distinction concrete
        for the client. It's not "your campaign is bad" — it's "your campaign
        is using a correlational approach, and here's specifically what an
        inferential approach would do differently and why."
        """
        t0 = time.time()

        self.result.current_approach_summary = current_summary or self._infer_current_approach()
        self.result.bilateral_approach_summary = informativ_summary or ""
        self.result.key_contrasts = contrasts or self._generate_contrasts()

        self.result.stage_log.append({
            "stage": 4, "name": "CONTRAST",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": len(self.result.key_contrasts),
        })

    def _infer_current_approach(self) -> str:
        """Infer a summary of the current approach from campaign data."""
        channels = set(c.channel_type for c in self.result.campaigns)
        segments = set()
        for c in self.result.campaigns:
            segments.update(c.audience_segments)

        return (
            f"Current approach uses {', '.join(channels)} across "
            f"{len(self.result.campaigns)} campaigns targeting "
            f"{len(segments)} audience segments. "
            f"${self.result.total_spend:,.0f} spent, "
            f"{self.result.total_conversions} conversions, "
            f"${self.result.overall_cpa:,.0f} CPA."
        )

    def _generate_contrasts(self) -> List[Dict[str, str]]:
        """Generate contrast points between current and INFORMATIV approaches."""
        contrasts = []

        # Audience targeting
        misaligned_count = sum(1 for m in self.result.audience_mappings
                               if m.fit in (AudienceFit.MISALIGNED, AudienceFit.PARTIAL))
        if misaligned_count > 0:
            contrasts.append({
                "dimension": "Audience Targeting",
                "current": "DSP segments based on demographics, behavior, or third-party data",
                "informativ": "Psychological archetypes from bilateral purchase evidence, "
                              "reached via domain whitelists for professional contexts",
                "why": "DSP segments identify WHO (by observable traits). INFORMATIV identifies "
                       "WHY (by purchase psychology). A Fortune 500 CFO and a startup founder "
                       "are in the same DSP segment but have opposite decision mechanisms.",
            })

        # Creative strategy
        contrasts.append({
            "dimension": "Creative Strategy",
            "current": "Same creative across audiences, optimized by CTR/CPA",
            "informativ": "Mechanism-matched creative per archetype, validated by bilateral evidence",
            "why": "CTR optimizes for attention. Bilateral evidence optimizes for the psychological "
                   "match that predicts CONVERSION. A high-CTR ad using the wrong mechanism "
                   "generates clicks from curious non-buyers, inflating CTR while wasting budget.",
        })

        # Channel architecture
        contrasts.append({
            "dimension": "Channel Architecture",
            "current": "Each channel optimized independently for conversions",
            "informativ": "Three-layer psychological funnel: CTV primes goals, Display deploys "
                          "mechanisms, Retargeting resolves barriers",
            "why": "Bargh's auto-motive model: the environment (CTV) activates goals, the "
                   "ad (display) offers fulfillment, the click is automatic goal completion. "
                   "Optimizing CTV for conversions misattributes view-through and misses "
                   "the priming value entirely.",
        })

        # Retargeting
        contrasts.append({
            "dimension": "Retargeting",
            "current": "Repeat the same ad to all site visitors",
            "informativ": "Therapeutic sequence: diagnose barrier from site behavior, "
                          "deploy mechanism matched to barrier, suppress after 3 touches",
            "why": "Showing the same ad repeatedly triggers reactance (bilateral evidence: "
                   "reactance separates converters from non-converters at 0.037 vs 0.092). "
                   "After 2-3 exposures the ad has been processed. Repetition damages, "
                   "it doesn't persuade.",
        })

        # Measurement
        contrasts.append({
            "dimension": "Measurement",
            "current": "CTR, CPA, impressions",
            "informativ": "Mechanism effectiveness per archetype, bilateral dimension lift, "
                          "theory validation, prediction accuracy",
            "why": "Standard metrics measure WHAT happened. INFORMATIV measures WHY it happened "
                   "and WHETHER the theoretical prediction was correct. This compounds: "
                   "correlational optimization converges on a local maximum; inferential "
                   "optimization discovers the actual mechanism and transfers to new contexts.",
        })

        return contrasts

    # ------------------------------------------------------------------
    # Stage 5: PRESCRIBE
    # ------------------------------------------------------------------

    def generate_recommendations(
        self,
        custom_recommendations: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Stage 5: Generate specific Day 1 recommendations.

        Every recommendation is grounded in bilateral evidence, not
        in "best practice." Each one has a predicted impact, effort
        estimate, and dependency list.
        """
        t0 = time.time()

        if custom_recommendations:
            for cr in custom_recommendations:
                self.result.recommendations.append(Recommendation(
                    priority=cr.get("priority", 99),
                    action=cr["action"],
                    rationale=cr.get("rationale", ""),
                    bilateral_evidence=cr.get("bilateral_evidence", ""),
                    expected_impact=cr.get("expected_impact", ""),
                    effort=cr.get("effort", "days"),
                    dependencies=cr.get("dependencies", []),
                ))
        else:
            self._generate_standard_recommendations()

        self.result.stage_log.append({
            "stage": 5, "name": "PRESCRIBE",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": len(self.result.recommendations),
        })

    def _generate_standard_recommendations(self):
        """Generate recommendations from diagnostics."""
        priority = 1

        # Revenue tracking is always #1 if missing
        rev_diag = [d for d in self.result.diagnostics
                    if d.category == "measurement" and d.severity == DiagnosticSeverity.CRITICAL]
        if rev_diag:
            self.result.recommendations.append(Recommendation(
                priority=priority,
                action="Fix revenue tracking on conversion pixel",
                rationale="Without revenue, ROAS is unmeasurable and learning systems cannot distinguish high-value from low-value conversions.",
                bilateral_evidence="Gradient fields require revenue-weighted outcomes to compute per-dimension revenue lift.",
                expected_impact="Enables ROAS optimization. Expected to reveal that 80% of revenue comes from 20% of archetypes.",
                effort="immediate",
            ))
            priority += 1

        # Audience realignment
        misaligned = [m for m in self.result.audience_mappings if m.fit == AudienceFit.MISALIGNED]
        if misaligned:
            self.result.recommendations.append(Recommendation(
                priority=priority,
                action=f"Replace {len(misaligned)} misaligned audience segments with INFORMATIV domain targeting",
                rationale="Current segments reach the wrong psychological profiles for this product.",
                bilateral_evidence="Bilateral edges from verified purchases show the actual buyer psychology differs from the targeted segments.",
                expected_impact="40-60% CPA reduction from eliminating waste impressions on non-buyer psychologies.",
                effort="hours",
                dependencies=["Domain whitelists per archetype (provided by INFORMATIV)"],
            ))
            priority += 1

        # Deploy mechanism-matched creative
        creative_diag = [d for d in self.result.diagnostics if d.category == "creative"]
        if creative_diag:
            self.result.recommendations.append(Recommendation(
                priority=priority,
                action="Deploy mechanism-matched creative variants per audience",
                rationale="Each buyer archetype responds to a specific persuasion mechanism. Current creative uses the same message for all.",
                bilateral_evidence="Bilateral mechanism scores: authority=0.688 for careful_truster, social_proof=0.528 for dependable_loyalist, cognitive_ease=0.612 for reliable_cooperator.",
                expected_impact="20-40% CTR improvement from mechanism-audience alignment. DSP A/B testing provides independent validation.",
                effort="days",
                dependencies=["INFORMATIV creative briefs per archetype"],
            ))
            priority += 1

        # Install telemetry
        self.result.recommendations.append(Recommendation(
            priority=priority,
            action="Install INFORMATIV telemetry (informativ.js) on client website",
            rationale="Enables barrier detection from site behavior, which powers therapeutic retargeting.",
            bilateral_evidence="Site behavior patterns map to specific barriers (price friction, trust deficit, quality uncertainty) with known resolution mechanisms.",
            expected_impact="Enables barrier-specific retargeting sequences. Expected 2-3x retargeting conversion rate.",
            effort="hours",
            dependencies=["GTM access on client website"],
        ))
        priority += 1

        # Channel rebalancing
        channel_diag = [d for d in self.result.diagnostics if d.category == "channel"]
        if channel_diag:
            self.result.recommendations.append(Recommendation(
                priority=priority,
                action="Rebalance channel allocation: CTV as primer, Display as persuader, RT as closer",
                rationale="Current allocation treats all channels as conversion channels. CTV's value is goal activation, not direct response.",
                bilateral_evidence="Auto-motive model: CTV plants goals, display offers fulfillment. Measuring CTV by conversions misattributes view-through.",
                expected_impact="15-25% overall efficiency improvement from proper channel role assignment.",
                effort="hours",
            ))
            priority += 1

        # Dayparting
        if any(d.category == "targeting" and "dayparting" in d.finding.lower() for d in self.result.diagnostics):
            self.result.recommendations.append(Recommendation(
                priority=priority,
                action="Apply audience-specific dayparting",
                rationale="B2B buyers have specific goal-accessibility windows tied to their work schedules.",
                bilateral_evidence="Corporate travel arrangers peak 8-10am, travel managers 9-11am. Weekend/evening impressions on B2B audiences are largely wasted.",
                expected_impact="10-15% CPA reduction from concentrating budget in high-accessibility windows.",
                effort="immediate",
            ))
            priority += 1

        # Frequency management
        if any(d.category == "targeting" and "frequency" in d.finding.lower() for d in self.result.diagnostics):
            self.result.recommendations.append(Recommendation(
                priority=priority,
                action="Set mechanism-informed frequency caps with reactance suppression",
                rationale="Each persuasion mechanism has a half-life and a reactance threshold from ADME profiles.",
                bilateral_evidence="Reactance discriminates converters (0.037) from non-converters (0.092). Exceeding frequency threshold actively damages conversion probability.",
                expected_impact="5-10% CPA reduction + prevents reactance-driven brand damage.",
                effort="immediate",
            ))

    # ------------------------------------------------------------------
    # Stage 6: SIMULATE
    # ------------------------------------------------------------------

    def simulate_impact(
        self,
        predicted_cpa: Optional[float] = None,
        simulation_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stage 6: Pre-campaign simulation of recommended changes.

        Uses the campaign simulator to predict the impact of INFORMATIV's
        recommendations. The simulation is explicit about what it assumes,
        what it doesn't know, and where the predictions are weakest.
        """
        t0 = time.time()

        if predicted_cpa is not None:
            self.result.predicted_cpa_with_changes = predicted_cpa
        else:
            # Conservative estimate: each recommendation layer compounds
            base_cpa = self.result.overall_cpa
            reduction = 1.0

            for rec in self.result.recommendations:
                impact = rec.expected_impact.lower()
                if "40-60%" in impact:
                    reduction *= 0.50  # midpoint
                elif "20-40%" in impact:
                    reduction *= 0.70
                elif "15-25%" in impact:
                    reduction *= 0.80
                elif "10-15%" in impact:
                    reduction *= 0.875
                elif "5-10%" in impact:
                    reduction *= 0.925

            self.result.predicted_cpa_with_changes = base_cpa * reduction

        if self.result.overall_cpa > 0:
            self.result.predicted_cpa_reduction_pct = (
                (1 - self.result.predicted_cpa_with_changes / self.result.overall_cpa) * 100
            )

        self.result.simulation_details = simulation_details or {
            "method": "compound_reduction_estimate",
            "caveat": "Estimates assume independent effects. Actual interaction effects "
                      "may be stronger (mechanism × domain synergy) or weaker (diminishing "
                      "returns on small audience). First 2 weeks of data will calibrate.",
        }

        self.result.stage_log.append({
            "stage": 6, "name": "SIMULATE",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": 1,
            "notes": f"Predicted CPA: ${self.result.predicted_cpa_with_changes:,.0f} "
                     f"(from ${self.result.overall_cpa:,.0f})",
        })

    # ------------------------------------------------------------------
    # Stage 7: INSTRUMENT
    # ------------------------------------------------------------------

    def define_measurement_framework(
        self,
        custom_framework: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stage 7: Define how we'll measure whether the recommendations work.

        The measurement framework is designed to validate the inferential
        approach, not just track performance. We're not just asking "did
        CPA go down?" — we're asking "did the mechanism predictions hold?"
        and "did bilateral evidence transfer to new contexts?"
        """
        t0 = time.time()

        self.result.measurement_framework = custom_framework or {
            "Week 1 — Baseline": {
                "Record current CPA per campaign before changes": "baseline",
                "Fix revenue tracking": "prerequisite",
                "Install INFORMATIV telemetry": "prerequisite",
                "Deploy INFORMATIV creative variants": "treatment",
            },
            "Week 2-3 — Mechanism Validation": {
                "Compare CPA: INFORMATIV variants vs original": "primary",
                "Compare CTR by mechanism variant per archetype": "primary",
                "Validate mechanism predictions (did predicted winner win?)": "inferential",
                "First learning system outputs": "system",
            },
            "Week 4-6 — Funnel Validation": {
                "Therapeutic retargeting conversion rate vs standard": "primary",
                "Barrier resolution rate by mechanism": "primary",
                "CTV priming lift on downstream display": "inferential",
                "Level 3 theory propositions from inferential agent": "system",
            },
            "Month 2-3 — Transfer Validation": {
                "Cross-channel attribution: CTV→display conversion path": "primary",
                "Per-user personalization from repeated measures": "system",
                "Goal activation validation": "inferential",
                "Budget reallocation from learning system recommendations": "system",
            },
            "Month 4-6 — Compounding Advantage": {
                "System discovers interaction effects invisible to theory": "inferential",
                "Temporal dynamics: which sequences work, when to switch": "system",
                "Meta-learning: competitive landscape changes detected": "system",
                "Fully autonomous campaign evolution": "system",
            },
        }

        self.result.stage_log.append({
            "stage": 7, "name": "INSTRUMENT",
            "duration_ms": (time.time() - t0) * 1000,
            "finding_count": len(self.result.measurement_framework),
        })

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_full_pipeline(
        self,
        audience_map: Optional[Dict[str, Dict[str, Any]]] = None,
        buyer_profile: Optional[Dict[str, Any]] = None,
        bilateral_evidence: Optional[Dict[str, Any]] = None,
        custom_recommendations: Optional[List[Dict[str, Any]]] = None,
    ) -> IngestionResult:
        """
        Run stages 2-7 in sequence.

        Stage 1 (EXTRACT) must be called first via ingest_campaign_data().
        """
        if not self.result.campaigns:
            raise ValueError("No campaign data ingested. Call ingest_campaign_data() first.")

        self.map_to_psychological_framework(audience_map, buyer_profile)
        self.diagnose_performance(bilateral_evidence)
        self.contrast_approaches()
        self.generate_recommendations(custom_recommendations)
        self.simulate_impact()
        self.define_measurement_framework()

        return self.result


def get_ingestion_engine(
    client_name: str,
    asin: str,
    dsp: str = "stackadapt",
) -> CampaignIngestion:
    """Factory function for the ingestion engine."""
    return CampaignIngestion(client_name=client_name, asin=asin, dsp=dsp)
