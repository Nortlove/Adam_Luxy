"""Cell-aggregation helpers for Q.2.A Cut B reporting endpoints.

Pure aggregation functions (no FastAPI / no I/O dependencies). The
service layer composes these over decision-trace iterables fetched
from Redis hot-cache + Neo4j long-term archival.

Discipline: each helper handles empty input gracefully (returns
zero-shaped result, never raises). The ``data_source_state`` literal
is decided at the service-layer boundary based on whether ANY traces
were retrievable, not by these helpers.

Cluster mapping policy: Becca's 5-creative pool clusters are derived
from chosen_creative_id by stripping the variant suffix. The cluster
is the prefix before the last "_<digit>" segment when present;
otherwise the full creative_id is used as the cluster_id (one-creative
cluster). This keeps the helper independent of any external mapping
table — the mapping IS the naming convention. Production calibration
of this convention belongs to a sibling slice; a Q.2.A consumer with
a different naming scheme can override via cluster_id_for_creative
hook.
"""

import re
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from adam.api.dashboard.models import (
    ArchetypeMetrics,
    ClusterMetrics,
    CohortConfidence,
    CohortMetrics,
    MechanismOrientation,
    PredicateMetrics,
)
from adam.intelligence.cohort_discovery import (
    COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD,
    COMPENSATORY_MECHANISM_INDICATORS,
    COMPENSATORY_TRANSACTIONAL_NEGATIVES,
    UserCohort,
)
from adam.intelligence.decision_trace import DecisionTrace


# 8 archetypes per adam.cold_start.unified_learning.Archetype
KNOWN_ARCHETYPES: Tuple[str, ...] = (
    "explorer",
    "achiever",
    "connector",
    "guardian",
    "seeker",
    "pragmatist",
    "influencer",
    "analyst",
)

# Predicate names known to M.0 / M.1 substrate. Used to compute the
# dormant flag — a predicate appearing in this catalog with zero fires
# in the window is reported as dormant, not omitted.
KNOWN_PREDICATES: Tuple[str, ...] = (
    "fomo_active",
    "psych_ownership",
    "maximizer_high",
    "compensatory_consumption",
    "persuasion_authority",
    "persuasion_social_proof",
)


_VARIANT_SUFFIX_RE = re.compile(r"_\d+$")


def cluster_id_for_creative(creative_id: Optional[str]) -> Optional[str]:
    """Derive cluster_id from creative_id by stripping the variant suffix.

    "ridelux_hero_3" → "ridelux_hero". A creative without a variant
    suffix returns itself. None passes through.
    """
    if not creative_id:
        return None
    return _VARIANT_SUFFIX_RE.sub("", creative_id) or creative_id


def aggregate_by_cluster(traces: Iterable[DecisionTrace]) -> List[ClusterMetrics]:
    """Count impressions per cluster across the trace iterable."""
    counts: Counter = Counter()
    total = 0
    for tr in traces:
        cid = cluster_id_for_creative(tr.chosen_creative_id)
        if cid is None:
            continue
        counts[cid] += 1
        total += 1
    if total == 0:
        return []
    return [
        ClusterMetrics(
            cluster_id=cid,
            impression_count=n,
            share_of_total=n / total,
        )
        for cid, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def aggregate_by_predicate(
    traces: Iterable[DecisionTrace],
    *,
    known_predicates: Tuple[str, ...] = KNOWN_PREDICATES,
) -> List[PredicateMetrics]:
    """Count predicate fires across the trace iterable.

    Predicate fires are inferred from chain_of_reasoning entries whose
    name matches a known predicate. A trace with no chain entries
    contributes zero fires for all predicates. Any predicate in
    ``known_predicates`` with zero fires across the window is included
    as dormant=True so operators see absence-of-firing explicitly.
    """
    fire_counts: Counter = Counter()
    total_traces = 0
    for tr in traces:
        total_traces += 1
        if tr.chain_of_reasoning is None:
            continue
        for entry in tr.chain_of_reasoning.entries:
            if entry.name in known_predicates:
                fire_counts[entry.name] += 1
    if total_traces == 0:
        return []
    metrics: List[PredicateMetrics] = []
    for name in known_predicates:
        n = fire_counts.get(name, 0)
        metrics.append(
            PredicateMetrics(
                predicate_name=name,
                fire_count=n,
                fire_rate=n / total_traces if total_traces > 0 else 0.0,
                dormant=(n == 0),
            )
        )
    return metrics


def aggregate_by_archetype(
    traces: Iterable[DecisionTrace],
    archetype_lookup: Callable[[str], Optional[str]],
    cold_start_lookup: Callable[[str], bool],
    conversion_lookup: Callable[[str], bool],
) -> List[ArchetypeMetrics]:
    """Aggregate per-archetype impression + conversion counts.

    Args:
        traces: iterable of DecisionTrace
        archetype_lookup: ``user_id -> archetype_id`` (None for unknown)
        cold_start_lookup: ``user_id -> True if cold-start defaulted``
        conversion_lookup: ``decision_id -> True if converted``

    Returns: ArchetypeMetrics per archetype that received any
    impressions; archetypes that received zero impressions in the
    window are NOT included (operators see them as absent rather than
    as zero-row noise; the surface-level total_impressions captures
    coverage).
    """
    impressions: Counter = Counter()
    cold_starts: Counter = Counter()
    conversions: Counter = Counter()

    for tr in traces:
        arch = archetype_lookup(tr.user_id)
        if arch is None:
            continue
        impressions[arch] += 1
        if cold_start_lookup(tr.user_id):
            cold_starts[arch] += 1
        if conversion_lookup(tr.decision_id):
            conversions[arch] += 1

    metrics: List[ArchetypeMetrics] = []
    for arch in KNOWN_ARCHETYPES:
        n = impressions.get(arch, 0)
        if n == 0:
            continue
        n_conv = conversions.get(arch, 0)
        n_cold = cold_starts.get(arch, 0)
        metrics.append(
            ArchetypeMetrics(
                archetype_id=arch,
                impression_count=n,
                conversion_count=n_conv,
                conversion_rate=n_conv / n if n > 0 else 0.0,
                cold_start_share=n_cold / n if n > 0 else 0.0,
            )
        )
    return metrics


def classify_mechanism_orientation(
    dominant_mechanisms: List[str],
) -> Tuple[MechanismOrientation, str]:
    """Classify cohort dominant_mechanisms as affiliative / transactional / mixed.

    Returns the orientation literal AND the leading mechanism name (for
    the dominant_mechanism field on CohortMetrics). Empty list yields
    ("mixed", "unknown") so the response shape stays well-formed.
    """
    if not dominant_mechanisms:
        return "mixed", "unknown"
    lead = dominant_mechanisms[0]
    affiliative_count = sum(
        1 for m in dominant_mechanisms
        if m in COMPENSATORY_MECHANISM_INDICATORS
    )
    transactional_count = sum(
        1 for m in dominant_mechanisms
        if m in COMPENSATORY_TRANSACTIONAL_NEGATIVES
    )
    affiliative_share = affiliative_count / len(dominant_mechanisms)
    transactional_share = transactional_count / len(dominant_mechanisms)
    if affiliative_share >= COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD:
        return "affiliative", lead
    if transactional_share >= COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD:
        return "transactional", lead
    return "mixed", lead


def cohort_confidence_label(confidence: float) -> CohortConfidence:
    """Map F.2's numeric confidence to the three-bucket label.

    Per cohort_discovery.detect_compensatory_consumption_pattern:
        0.85 → high_confidence (both criteria met + size >= 200)
        0.65 → partial_evidence (one criterion OR undersample)
        else → uninformative
    """
    if confidence >= 0.80:
        return "high_confidence"
    if confidence >= 0.55:
        return "partial_evidence"
    return "uninformative"


def aggregate_by_cohort(
    cohorts: Iterable[UserCohort],
    cohort_conversion_rate_lookup: Callable[[str], float],
) -> List[CohortMetrics]:
    """Aggregate per-cohort outcome correlation metrics.

    Args:
        cohorts: UserCohort iterable (typically read from Neo4j)
        cohort_conversion_rate_lookup: ``cohort_id -> conversion_rate``
            (caller computes from ConversionEdges joined to cohort
            members; returns 0.0 when no observations available)
    """
    metrics: List[CohortMetrics] = []
    for cohort in cohorts:
        orientation, lead = classify_mechanism_orientation(
            cohort.dominant_mechanisms
        )
        conv_rate = cohort_conversion_rate_lookup(cohort.cohort_id)
        # Clamp to [0, 1] defensively — lookup may return out-of-range
        # on partial state.
        conv_rate = max(0.0, min(1.0, conv_rate))
        metrics.append(
            CohortMetrics(
                cohort_id=cohort.cohort_id,
                dominant_mechanism=lead,
                mechanism_orientation=orientation,
                compensatory_flag=cohort.compensatory_consumption_pattern,
                sample_size=cohort.size,
                conversion_rate=conv_rate,
                confidence_label=cohort_confidence_label(
                    cohort.compensatory_detection_confidence
                ),
            )
        )
    return metrics


# =============================================================================
# Privacy guard
# =============================================================================


def anonymize_buyer_id(buyer_id: str) -> str:
    """Anonymize a buyer_id for response surfaces.

    Returns the SHA-256 hex digest's first 12 chars prefixed with
    "buyer_" — deterministic (same input → same output) so operators
    can correlate across responses, but irreversible (no plaintext
    leak). Empty / None returns "buyer_unknown".
    """
    import hashlib
    if not buyer_id:
        return "buyer_unknown"
    digest = hashlib.sha256(buyer_id.encode("utf-8")).hexdigest()
    return f"buyer_{digest[:12]}"


# =============================================================================
# Empty-state response helpers
# =============================================================================


def empty_window_bounds_now(days: int) -> Tuple:
    """Return (window_start, window_end) for the requested lookback.

    Used by service functions to populate window bounds even when no
    traces are returned, so the response shape is identical between
    populated and empty states.
    """
    from datetime import datetime, timedelta, timezone
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(int(days), 0))
    return start, end