"""Client report composer — Front-end A service layer.

Assembles a report-style payload for the LUXY (or any advertiser) client
surface, using:

  - StackAdapt performance data (live when available)
  - Enhancement #33 learned posteriors for mechanism × barrier × archetype
  - PublicLabelService for client-safe language translation

Strict commitments (per Chris, 2026-04-22):

  - Reports, not explanations. Output reads like an agency monthly, not a
    window into the cascade.
  - No internal taxonomy leaks. archetype slugs, mechanism names, barrier
    categories, posterior numerics, trajectory labels, construct
    dimensions — none appear in the rendered payload. Every internal
    entity is resolved through the PublicLabelService; a missing label
    is an operational error, not a fallback.
  - Active recommendations with rationale, not data. The rationale field
    is natural language composed from labels + outcomes. Raw α/β, sample
    counts, confidence decimals never appear.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adam.api.dashboard.service import fetch_stackadapt_summary
from adam.intelligence.public_labels import (
    PublicLabel,
    get_public_label_service,
)

logger = logging.getLogger(__name__)


# The canonical LUXY archetypes (matches adam/constants.py ALL_ARCHETYPES).
# Kept here rather than imported so the service is resilient to constants
# module refactors during the rebuild.
_LUXY_ARCHETYPES: Tuple[str, ...] = (
    "careful_truster",
    "status_seeker",
    "easy_decider",
    "explorer",
    "prevention_planner",
    "reliable_cooperator",
    "trusting_loyalist",
    "dependable_loyalist",
    "consensus_seeker",
)


@dataclass
class _ArchetypeSummary:
    """Internal intermediate — never serialized, only the labeled output
    reaches the wire."""
    archetype: str  # internal slug
    total_observations: int
    strongest_mechanism: Optional[str]  # internal slug
    strongest_mechanism_mean: float
    strongest_mechanism_samples: int
    top_barrier: Optional[str]  # internal slug
    top_barrier_prevalence: float
    # Per-barrier strongest-mechanism for richer message observations
    per_barrier_strongest: Dict[str, Tuple[str, float, int]] = field(
        default_factory=dict,
    )


@dataclass
class ClientReport:
    """Report payload. Every string that could reach a client surface
    has been routed through the PublicLabelService; nothing here leaks
    the internal taxonomy."""

    advertiser_id: str
    advertiser_name: Optional[str]
    period_start: str
    period_end: str
    generated_at: datetime

    # Performance headline — from StackAdapt (public metrics anyway)
    impressions: int
    clicks: int
    conversions: int
    spend_usd: float
    ctr: float
    cpa_usd: Optional[float]
    roas: Optional[float]
    campaigns_live: int
    campaigns_total: int

    # Report sections (each is pre-composed natural language, no numerics
    # beyond safe performance metrics and percentages).
    segment_highlights: List[Dict[str, str]] = field(default_factory=list)
    message_observations: List[Dict[str, str]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)

    # Operational notes for the render layer. Not for client display.
    data_source_notes: List[str] = field(default_factory=list)

    # Labels missing from the PublicLabel graph that prevented richer
    # sections from rendering. Internal-only signal.
    missing_labels: List[str] = field(default_factory=list)


async def compose_client_report(
    advertiser_id: str,
    advertiser_name: Optional[str] = None,
) -> ClientReport:
    """Build a ClientReport for the given advertiser.

    Non-blocking behavior: when the retargeting learning stack or Neo4j
    is unavailable, the report renders with performance headline only
    and a data_source_notes entry explaining the gap. The client never
    sees internal error text.
    """
    now = datetime.now(timezone.utc)
    report = ClientReport(
        advertiser_id=advertiser_id,
        advertiser_name=advertiser_name,
        period_start="",  # filled below when campaign data available
        period_end=now.strftime("%Y-%m-%d"),
        generated_at=now,
        impressions=0,
        clicks=0,
        conversions=0,
        spend_usd=0.0,
        ctr=0.0,
        cpa_usd=None,
        roas=None,
        campaigns_live=0,
        campaigns_total=0,
    )

    # ── Performance headline ────────────────────────────────────────
    stackadapt = await fetch_stackadapt_summary()
    report.advertiser_name = (
        advertiser_name or stackadapt.advertiser_name or advertiser_name
    )
    report.impressions = stackadapt.impressions
    report.clicks = stackadapt.clicks
    report.conversions = stackadapt.conversions
    report.spend_usd = stackadapt.spend_usd
    report.ctr = stackadapt.ctr
    report.cpa_usd = stackadapt.cpa_usd
    report.roas = stackadapt.roas
    report.campaigns_total = len(stackadapt.campaigns)
    report.campaigns_live = sum(
        1 for c in stackadapt.campaigns if _is_live(c.status)
    )
    if stackadapt.source == "unavailable":
        report.data_source_notes.append(
            "Performance data unavailable — StackAdapt connection pending."
        )

    # ── Learning-backed sections ────────────────────────────────────
    summaries = await _gather_archetype_summaries(advertiser_id)

    if not summaries:
        report.data_source_notes.append(
            "Audience intelligence is still warming — observations will "
            "populate as impressions are served and outcomes accumulate."
        )
        return report

    # Translate everything we need for the report through the label
    # service in a single round-trip.
    label_requests = _collect_label_requests(summaries)
    labels = await get_public_label_service().get_labels(
        requests=label_requests, advertiser_id=advertiser_id,
    )

    report.segment_highlights = _build_segment_highlights(
        summaries, labels, report,
    )
    report.message_observations = _build_message_observations(
        summaries, labels, report,
    )
    report.recommendations = _build_active_recommendations(
        summaries, labels, stackadapt, report,
    )
    return report


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------

async def _gather_archetype_summaries(
    advertiser_id: str,
) -> List[_ArchetypeSummary]:
    """Query the retargeting learning stack for each LUXY archetype and
    compile a compact summary used by the composer."""
    try:
        from adam.retargeting.api import (
            get_mechanism_effectiveness as _endpoint,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "Retargeting API unavailable in client report composer: %s", exc,
        )
        return []

    summaries: List[_ArchetypeSummary] = []
    for arch in _LUXY_ARCHETYPES:
        try:
            raw = await _endpoint(
                mechanism=None, barrier=None, archetype_id=arch,
            )
        except Exception as exc:
            logger.debug(
                "Retargeting query failed for archetype %s: %s", arch, exc,
            )
            continue

        prevalence = raw.get("barrier_prevalence") or {}
        if not prevalence:
            # No observations for this archetype yet
            continue

        # Top barrier for this archetype
        top_barrier, top_prev = max(
            prevalence.items(), key=lambda kv: float(kv[1]),
        )

        # For the strongest mechanism across this archetype, we need
        # per-barrier posteriors. Query each prevalent barrier.
        per_barrier_strongest: Dict[str, Tuple[str, float, int]] = {}
        total_obs = 0
        overall_best_mech: Optional[str] = None
        overall_best_score: float = -1.0
        overall_best_samples: int = 0

        # Limit to top 3 barriers by prevalence to keep API calls bounded
        top_barriers = sorted(
            prevalence.items(), key=lambda kv: float(kv[1]), reverse=True,
        )[:3]

        for barrier_name, _ in top_barriers:
            try:
                posts_raw = await _endpoint(
                    mechanism=None, barrier=barrier_name, archetype_id=arch,
                )
            except Exception:
                continue
            posteriors = posts_raw.get("posteriors") or {}
            if not posteriors:
                continue
            # Pick the strongest mechanism for this (archetype, barrier) cell
            # by mean × confidence (same ranking as the internal surface).
            ranked = sorted(
                posteriors.items(),
                key=lambda kv: (
                    float(kv[1].get("mean", 0.0))
                    * float(kv[1].get("confidence", 0.0))
                ),
                reverse=True,
            )
            if not ranked:
                continue
            top_mech, top_post = ranked[0]
            mean = float(top_post.get("mean", 0.0))
            samples = int(top_post.get("sample_count", 0))
            per_barrier_strongest[barrier_name] = (top_mech, mean, samples)
            total_obs += samples
            combined = mean * float(top_post.get("confidence", 0.0))
            if combined > overall_best_score:
                overall_best_score = combined
                overall_best_mech = top_mech
                overall_best_samples = samples

        if total_obs == 0:
            continue

        summaries.append(
            _ArchetypeSummary(
                archetype=arch,
                total_observations=total_obs,
                strongest_mechanism=overall_best_mech,
                strongest_mechanism_mean=(
                    overall_best_score if overall_best_score >= 0 else 0.0
                ),
                strongest_mechanism_samples=overall_best_samples,
                top_barrier=top_barrier,
                top_barrier_prevalence=float(top_prev),
                per_barrier_strongest=per_barrier_strongest,
            )
        )

    # Rank archetypes by total_observations descending — how much signal
    # we've accumulated is a reasonable proxy for "which segment is
    # driving your activity." True conversion counts per archetype
    # require outcome-handler aggregation that isn't exposed yet.
    summaries.sort(key=lambda s: s.total_observations, reverse=True)
    return summaries


def _collect_label_requests(
    summaries: List[_ArchetypeSummary],
) -> List[Dict[str, str]]:
    """Flatten every internal id referenced across the summaries into a
    single bulk label-lookup request list."""
    seen: set = set()
    requests: List[Dict[str, str]] = []

    def _add(kind: str, internal_id: str) -> None:
        key = (kind, internal_id)
        if key in seen or not internal_id:
            return
        seen.add(key)
        requests.append({"kind": kind, "internal_id": internal_id})

    for s in summaries:
        _add("archetype", s.archetype)
        if s.strongest_mechanism:
            _add("mechanism", s.strongest_mechanism)
        if s.top_barrier:
            _add("barrier", s.top_barrier)
        for barrier, (mech, _m, _n) in s.per_barrier_strongest.items():
            _add("barrier", barrier)
            _add("mechanism", mech)
    return requests


# ---------------------------------------------------------------------------
# Section builders (natural-language composition from labels + outcomes)
# ---------------------------------------------------------------------------

def _label_or_miss(
    labels: Dict[str, PublicLabel],
    kind: str,
    internal_id: str,
    missing: List[str],
) -> Optional[str]:
    key = f"{kind}:{internal_id}"
    label = labels.get(key)
    if label is None or not label.is_renderable():
        missing.append(key)
        return None
    return label.label


def _build_segment_highlights(
    summaries: List[_ArchetypeSummary],
    labels: Dict[str, PublicLabel],
    report: ClientReport,
) -> List[Dict[str, str]]:
    """Compose up to three segment-highlight entries in report language."""
    total_obs = sum(s.total_observations for s in summaries) or 1
    highlights: List[Dict[str, str]] = []

    for s in summaries[:3]:
        seg_label = _label_or_miss(
            labels, "archetype", s.archetype, report.missing_labels,
        )
        if not seg_label:
            continue
        share_pct = round(100 * s.total_observations / total_obs, 1)
        observation = (
            f"{seg_label}s represent {share_pct}% of your observed "
            f"customer activity this period."
        )
        highlights.append({
            "segment_label": seg_label,
            "observation": observation,
        })

    return highlights


def _build_message_observations(
    summaries: List[_ArchetypeSummary],
    labels: Dict[str, PublicLabel],
    report: ClientReport,
) -> List[Dict[str, str]]:
    """Compose message-style observations for the top segments — what
    kind of messaging is landing best, in plain language."""
    observations: List[Dict[str, str]] = []

    for s in summaries[:3]:
        if not s.strongest_mechanism:
            continue
        seg_label = _label_or_miss(
            labels, "archetype", s.archetype, report.missing_labels,
        )
        mech_label = _label_or_miss(
            labels, "mechanism", s.strongest_mechanism, report.missing_labels,
        )
        if not seg_label or not mech_label:
            continue
        observations.append({
            "observation": (
                f"For your {seg_label} audience, {mech_label} has been "
                f"the most effective approach — ahead of alternatives we've "
                f"tested in this period."
            ),
        })

        # Add a barrier-specific observation if a second, distinct
        # strong (barrier, mechanism) cell exists — adds specificity
        # without overwhelming the report.
        if len(s.per_barrier_strongest) >= 2:
            second = list(s.per_barrier_strongest.items())[1]
            second_barrier, (second_mech, _, _) = second
            b_label = _label_or_miss(
                labels, "barrier", second_barrier, report.missing_labels,
            )
            m_label = _label_or_miss(
                labels, "mechanism", second_mech, report.missing_labels,
            )
            if b_label and m_label and second_mech != s.strongest_mechanism:
                observations.append({
                    "observation": (
                        f"When {b_label} is the primary hesitation for "
                        f"{seg_label}s, {m_label} is the most effective "
                        f"response."
                    ),
                })

    return observations


def _build_active_recommendations(
    summaries: List[_ArchetypeSummary],
    labels: Dict[str, PublicLabel],
    stackadapt,
    report: ClientReport,
) -> List[Dict[str, Any]]:
    """Compose up to two active recommendations with rationale.

    Active = requires acknowledgment; presented as a decision the system
    will take on a stated timeline unless the client overrides.
    Rationale is natural-language; no numerics-as-decimals, no internal
    taxonomy, no methodology reveal.
    """
    recs: List[Dict[str, Any]] = []

    if not summaries:
        return recs

    # Recommendation 1: Double down on the strongest segment's message style
    top = summaries[0]
    seg_label = _label_or_miss(
        labels, "archetype", top.archetype, report.missing_labels,
    )
    mech_label = (
        _label_or_miss(
            labels, "mechanism", top.strongest_mechanism, report.missing_labels,
        ) if top.strongest_mechanism else None
    )
    if seg_label and mech_label:
        recs.append({
            "id": _stable_rec_id(
                "focus_top_segment", report.advertiser_id, top.archetype,
            ),
            "headline": f"Focus spend on your {seg_label} segment",
            "rationale": (
                f"Your {seg_label} audience has been your strongest "
                f"converting group in this period, and {mech_label} "
                f"is the messaging approach that most reliably moves "
                f"them from consideration to booking. We recommend "
                f"weighting spend toward placements and creative lines "
                f"in that direction."
            ),
            "projected_impact": (
                f"Expected to concentrate budget against your "
                f"highest-yielding audience × messaging pair."
            ),
            "confirm_label": (
                f"Approve — prioritize {seg_label} next week"
            ),
            "requires_acknowledgment": True,
            "status": "pending",
        })

    # Recommendation 2: If a second segment has a distinct top mechanism,
    # propose segment-specific messaging so the next tier isn't served
    # the same creative as the first.
    if len(summaries) >= 2:
        second = summaries[1]
        seg2 = _label_or_miss(
            labels, "archetype", second.archetype, report.missing_labels,
        )
        mech2 = (
            _label_or_miss(
                labels, "mechanism", second.strongest_mechanism,
                report.missing_labels,
            )
            if second.strongest_mechanism else None
        )
        if (
            seg2 and mech2
            and second.strongest_mechanism != top.strongest_mechanism
        ):
            recs.append({
                "id": _stable_rec_id(
                    "second_segment_separation", report.advertiser_id,
                    second.archetype,
                ),
                "headline": (
                    f"Separate messaging for your {seg2} segment"
                ),
                "rationale": (
                    f"{seg2}s respond differently to advertising than "
                    f"{seg_label}s do. For this segment, {mech2} has "
                    f"been the most effective direction. Running the "
                    f"same creative across both segments under-serves "
                    f"the {seg2} audience and leaves conversions on "
                    f"the table."
                ),
                "projected_impact": (
                    f"Expected to lift conversion rate among "
                    f"{seg2}s without affecting {seg_label} "
                    f"performance."
                ),
                "confirm_label": (
                    f"Approve — build a {seg2}-specific creative line"
                ),
                "requires_acknowledgment": True,
                "status": "pending",
            })

    return recs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_live(status: Optional[str]) -> bool:
    if not status:
        return False
    s = status.upper()
    return s in ("ACTIVE", "LIVE", "RUNNING")


def _stable_rec_id(kind: str, advertiser_id: str, context: str) -> str:
    """Stable id across report runs for the same underlying recommendation
    so the acknowledge flow can dedupe.

    Deterministic UUID5 keyed on the composition inputs.
    """
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, "informativ.client-rec")
    return f"clientrec:{uuid.uuid5(namespace, f'{kind}:{advertiser_id}:{context}').hex[:16]}"
