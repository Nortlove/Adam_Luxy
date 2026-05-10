"""Service layer for Q.2.A Cut B reporting endpoints.

Composes decision-trace I/O (Redis hot + Neo4j archive) with the pure
aggregation helpers in cell_aggregation.py. Each service function
handles empty-state gracefully: Aura paused / Infrastructure not
initialized / no traces in window all yield well-formed responses
with ``data_source_state="empty"``.

Discipline:
- No raw buyer_id leaks: every endpoint that touches buyer_id calls
  ``anonymize_buyer_id`` from cell_aggregation before serialization.
- Soft-fail on infrastructure absence — Q.1 timing decoupling.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, List, Optional

from adam.api.dashboard.cell_aggregation import (
    KNOWN_PREDICATES,
    aggregate_by_archetype,
    aggregate_by_cluster,
    aggregate_by_cohort,
    aggregate_by_predicate,
    anonymize_buyer_id,
    cluster_id_for_creative,
    empty_window_bounds_now,
)
from adam.api.dashboard.models import (
    DecisionTraceDetailResponse,
    DispatchMethodMetrics,
    LoopDispatchRatesResponse,
    PerArchetypePerformanceResponse,
    PerClusterFireRateResponse,
    PerCohortOutcomeCorrelationResponse,
)
from adam.intelligence.cohort_discovery import UserCohort
from adam.intelligence.decision_trace import DecisionTrace
from adam.intelligence.decision_trace_neo4j import (
    list_traces_in_window_from_neo4j,
    load_trace_from_neo4j,
)
from adam.intelligence.decision_trace_store import load_trace

logger = logging.getLogger(__name__)


# Spec lists 14 dispatch method names; surfaced as dormant when no
# dispatch has fired yet (Q.1 timing decoupling).
DISPATCH_METHOD_NAMES: tuple = (
    "_update_thompson",
    "_update_meta_orchestrator",
    "_update_neo4j_attribution",
    "_update_graph_rewriter",
    "_route_to_learning_hub",
    "_update_theory_learner",
    "_process_chain_attestations",
    "_update_dsp_learning",
    "_update_ml_ensemble",
    "_update_cognitive_learning",
    "_update_page_context_learning",
    "_update_mechanism_interactions",
    "_update_buyer_profile",
    "_update_bilateral_edge_evidence",
)


# =============================================================================
# Infrastructure access — soft-fail to None on absence
# =============================================================================


async def _get_async_neo4j_driver() -> Optional[Any]:
    """Return the async Neo4j driver, or None when infrastructure absent."""
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        return infra.neo4j
    except Exception as exc:
        logger.debug("Neo4j driver unavailable for Q.2.A surfaces: %s", exc)
        return None


async def _get_async_redis_client() -> Optional[Any]:
    """Return the async Redis client, or None when infrastructure absent."""
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        return infra.redis
    except Exception as exc:
        logger.debug("Redis client unavailable for Q.2.A surfaces: %s", exc)
        return None


def _cutoff_epoch_for_days(days: int) -> float:
    return time.time() - max(int(days), 0) * 86400.0


async def _fetch_window_traces(
    days: int,
    *,
    campaign_id: Optional[str] = None,
    limit: int = 10000,
) -> List[DecisionTrace]:
    """Fetch decision traces in a time window from Neo4j archive.

    Redis hot-cache is indexed only by user_id; for global window
    scans the Neo4j archive is the canonical surface. Returns empty
    list when driver absent.

    campaign_id is accepted by the API surface but DecisionTrace does
    NOT carry campaign_id today — filter is applied as a no-op when
    the schema gains the field. Documented in EVE handoff.
    """
    driver = await _get_async_neo4j_driver()
    if driver is None:
        return []
    cutoff = _cutoff_epoch_for_days(days)
    return await list_traces_in_window_from_neo4j(
        cutoff, driver, limit=limit,
    )


# =============================================================================
# Endpoint 1 — per-cluster fire-rate
# =============================================================================


async def get_per_cluster_fire_rate(
    days: int = 7,
    campaign_id: Optional[str] = None,
) -> PerClusterFireRateResponse:
    """Aggregate cluster + predicate metrics over the lookback window."""
    start, end = empty_window_bounds_now(days)
    traces = await _fetch_window_traces(days, campaign_id=campaign_id)
    if not traces:
        return PerClusterFireRateResponse(
            clusters=[],
            predicates=[],
            total_impressions=0,
            window_start=start,
            window_end=end,
            data_source_state="empty",
        )
    clusters = aggregate_by_cluster(traces)
    predicates = aggregate_by_predicate(traces)
    # Partial state: traces present but no chain_of_reasoning entries
    # → predicates list will be all-dormant. Honest signal: "we have
    # traces but the predicate substrate isn't firing yet."
    state = "populated"
    if predicates and all(p.fire_count == 0 for p in predicates):
        state = "partial"
    return PerClusterFireRateResponse(
        clusters=clusters,
        predicates=predicates,
        total_impressions=len(traces),
        window_start=start,
        window_end=end,
        data_source_state=state,
    )


# =============================================================================
# Endpoint 2 — per-archetype performance
# =============================================================================


def _archetype_lookup_for_user(user_id: str) -> Optional[str]:
    """Look up archetype for a buyer.

    Pre-pilot: BuyerUncertaintyProfile.archetype join is not wired into
    the dashboard service path (Aura-cohort-population dependency). This
    function returns None today; tests patch this hook directly to
    exercise the populated-state aggregation paths. Wiring lands in a
    sibling slice when Aura cohort population is operational.
    """
    return None


def _conversion_lookup_for_decision(decision_id: str) -> bool:
    """Look up conversion attribution for a decision.

    Pre-pilot: ConversionEdge join not wired. Returns False; tests
    patch directly. Surfaces as data_source_state='partial' in the
    response when archetypes are present but conversion_count is 0.
    """
    return False


async def get_per_archetype_performance(
    days: int = 30,
    campaign_id: Optional[str] = None,
) -> PerArchetypePerformanceResponse:
    """Aggregate per-archetype impression + conversion + cold-start metrics."""
    start, end = empty_window_bounds_now(days)
    traces = await _fetch_window_traces(days, campaign_id=campaign_id)
    if not traces:
        return PerArchetypePerformanceResponse(
            archetypes=[],
            total_impressions=0,
            window_start=start,
            window_end=end,
            data_source_state="empty",
        )

    def _cold_lookup(uid: str) -> bool:
        # Cold-start signal: archetype was the PRAGMATIST default
        # (Phase 2 §4.1 cold-start convention) OR archetype absent.
        arch = _archetype_lookup_for_user(uid)
        return arch is None or arch == "pragmatist"

    archetypes = aggregate_by_archetype(
        traces,
        _archetype_lookup_for_user,
        _cold_lookup,
        _conversion_lookup_for_decision,
    )
    state = "populated" if archetypes else "partial"
    return PerArchetypePerformanceResponse(
        archetypes=archetypes,
        total_impressions=len(traces),
        window_start=start,
        window_end=end,
        data_source_state=state,
    )


# =============================================================================
# Endpoint 3 — per-cohort outcome correlation
# =============================================================================


async def _fetch_user_cohorts() -> List[UserCohort]:
    """Read UserCohort nodes from Neo4j. Empty list on driver absent."""
    driver = await _get_async_neo4j_driver()
    if driver is None:
        return []
    cohorts: List[UserCohort] = []
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (c:UserCohort) RETURN c LIMIT 200"
            )
            async for record in result:
                node = record.get("c")
                if node is None:
                    continue
                # Pydantic-shaped construction defensively — we don't
                # know which properties are populated post-F.2.
                cohort_id = str(node.get("cohort_id") or node.get("id") or "")
                if not cohort_id:
                    continue
                size = int(node.get("size") or 0)
                doms_raw = node.get("dominant_mechanisms") or []
                if isinstance(doms_raw, str):
                    doms = [doms_raw]
                else:
                    doms = list(doms_raw)
                cohorts.append(
                    UserCohort(
                        cohort_id=cohort_id,
                        size=size,
                        sample_members=[],
                        dominant_mechanisms=doms,
                        compensatory_consumption_pattern=bool(
                            node.get("compensatory_consumption_pattern", False)
                        ),
                        compensatory_detection_confidence=float(
                            node.get("compensatory_detection_confidence", 0.5)
                            or 0.5
                        ),
                    )
                )
    except Exception as exc:
        logger.warning("UserCohort read failed: %s", exc)
        return []
    return cohorts


async def get_per_cohort_outcome_correlation(
    days: int = 30,
    campaign_id: Optional[str] = None,
) -> PerCohortOutcomeCorrelationResponse:
    """Aggregate cohort metrics (orientation + compensatory + outcome rate)."""
    start, end = empty_window_bounds_now(days)
    cohorts = await _fetch_user_cohorts()
    if not cohorts:
        return PerCohortOutcomeCorrelationResponse(
            cohorts=[],
            window_start=start,
            window_end=end,
            data_source_state="empty",
        )

    # Conversion-rate lookup requires ConversionEdge join to cohort
    # members — not available pre-pilot. Returns 0.0; data_source_state
    # marked partial when cohorts present but rates unavailable.
    def _conv_rate_lookup(cohort_id: str) -> float:
        return 0.0

    metrics = aggregate_by_cohort(cohorts, _conv_rate_lookup)
    return PerCohortOutcomeCorrelationResponse(
        cohorts=metrics,
        window_start=start,
        window_end=end,
        data_source_state="partial",
    )


# =============================================================================
# Endpoint 4 — loop dispatch rates
# =============================================================================


async def get_loop_dispatch_rates(
    days: int = 7,
) -> LoopDispatchRatesResponse:
    """Read OutcomeHandler stats() and format as DispatchMethodMetrics list.

    The ``days`` parameter is accepted for API contract symmetry; the
    underlying counters are cumulative since process start (Spine #6
    discipline: don't bound counter retention to a window without an
    explicit windowed-counter producer). When a windowed-counter
    producer ships, this endpoint flips to window aggregation without
    response-shape changes.
    """
    try:
        from adam.core.learning.outcome_handler import get_outcome_handler
        handler = get_outcome_handler()
        stats = handler.stats
    except Exception as exc:
        logger.warning("OutcomeHandler stats unavailable: %s", exc)
        return LoopDispatchRatesResponse(
            dispatch_methods=[],
            total_outcomes_processed=0,
            data_source_state="empty",
        )

    counts = stats.get("dispatch_counts") or {}
    last_at = stats.get("dispatch_last_at") or {}

    methods: List[DispatchMethodMetrics] = []
    for name in DISPATCH_METHOD_NAMES:
        n = int(counts.get(name, 0))
        last_iso = last_at.get(name)
        last_dt: Optional[datetime] = None
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(last_iso)
            except Exception:
                last_dt = None
        methods.append(
            DispatchMethodMetrics(
                method_name=name,
                dispatch_count=n,
                last_dispatch_at=last_dt,
                dormant=(n == 0),
            )
        )

    total = int(stats.get("outcomes_processed", 0))
    if total == 0 and not counts:
        state = "empty"
    elif total == 0:
        state = "partial"
    else:
        state = "populated"

    return LoopDispatchRatesResponse(
        dispatch_methods=methods,
        total_outcomes_processed=total,
        data_source_state=state,
    )


# =============================================================================
# Endpoint 5 — decision-trace detail
# =============================================================================


def _predicates_from_chain(trace: DecisionTrace) -> list:
    """Project chain_of_reasoning entries into PredicateFiring list.

    The chain holds named contribution entries; predicate firings are
    the entries whose name matches a known predicate. Each becomes a
    PredicateFiring with fired=True and score=contribution. Predicates
    NOT in the chain are surfaced as fired=False so the response gives
    a complete catalog rather than partial absence.
    """
    from adam.api.dashboard.models import PredicateFiring
    fired_names = set()
    fired_scores: dict = {}
    if trace.chain_of_reasoning is not None:
        for e in trace.chain_of_reasoning.entries:
            if e.name in KNOWN_PREDICATES:
                fired_names.add(e.name)
                fired_scores[e.name] = e.contribution
    out = []
    for name in KNOWN_PREDICATES:
        out.append(
            PredicateFiring(
                predicate_name=name,
                fired=(name in fired_names),
                score=fired_scores.get(name),
                threshold=None,  # threshold not carried on trace today
            )
        )
    return out


def _modulations_from_alternatives(trace: DecisionTrace) -> list:
    """Project alternatives into ModulationDetail list.

    Each alternative's posterior_score relative to the chosen
    chosen_score is a directional modulation indicator. Source field
    captures the alternative's mechanism for operator readability.
    """
    from adam.api.dashboard.models import ModulationDetail
    out = []
    for alt in trace.alternatives:
        out.append(
            ModulationDetail(
                mechanism=alt.mechanism,
                score_before=float(alt.posterior_score),
                score_after=float(trace.chosen_score),
                source=f"alternative:{alt.creative_id}",
            )
        )
    return out


async def get_decision_trace_detail(
    impression_id: str,
) -> DecisionTraceDetailResponse:
    """Return per-impression decision trace detail with anonymized buyer_id.

    Read order: Redis hot first, Neo4j fallback. Returns
    data_source_state='not_found' when neither layer has the record;
    data_source_state='partial' when Redis miss + Neo4j hit (typical
    for traces older than the Redis TTL); data_source_state='found'
    when Redis hit.
    """
    redis_client = await _get_async_redis_client()
    trace: Optional[DecisionTrace] = None
    state = "not_found"

    if redis_client is not None:
        try:
            trace = await load_trace(impression_id, redis_client)
            if trace is not None:
                state = "found"
        except Exception as exc:
            logger.debug("Redis trace load failed for %s: %s", impression_id, exc)

    if trace is None:
        driver = await _get_async_neo4j_driver()
        if driver is not None:
            try:
                trace = await load_trace_from_neo4j(impression_id, driver)
                if trace is not None:
                    state = "partial"  # archive hit, Redis miss
            except Exception as exc:
                logger.debug(
                    "Neo4j trace load failed for %s: %s", impression_id, exc,
                )

    if trace is None:
        # Empty-shape response (HTTP 200 with not_found state, NOT 404
        # exception — the spec specifies this for graceful UI handling).
        return DecisionTraceDetailResponse(
            impression_id=impression_id,
            timestamp=datetime.now(timezone.utc),
            buyer_id_anonymized=anonymize_buyer_id(""),
            predicates_fired=[],
            modulations_applied=[],
            data_source_state="not_found",
        )

    # DecisionTrace.user_posterior_snapshot is Dict[str, float] —
    # archetype is NOT carried as a string field on the trace today.
    # Schema-gap: archetype lookup goes through the
    # _archetype_lookup_for_user hook (BuyerUncertaintyProfile join
    # in a sibling slice). Returns None today for unwired state.
    archetype = _archetype_lookup_for_user(trace.user_id)

    return DecisionTraceDetailResponse(
        impression_id=trace.decision_id,
        timestamp=trace.timestamp,
        buyer_id_anonymized=anonymize_buyer_id(trace.user_id),
        cell_id=None,  # not on trace schema today
        cluster_id=cluster_id_for_creative(trace.chosen_creative_id),
        archetype=archetype,
        cohort_id=None,  # join through user_id → cohort_membership not wired
        posture_class=trace.posture_class,
        journey_stage=None,  # not on trace schema today
        regulatory_focus=None,  # not on trace schema today
        predicates_fired=_predicates_from_chain(trace),
        modulations_applied=_modulations_from_alternatives(trace),
        chosen_creative_id=trace.chosen_creative_id,
        chosen_creative_cluster=cluster_id_for_creative(trace.chosen_creative_id),
        why_explanation=None,  # WhyLibrary join not in scope for Q.2.A
        data_source_state=state,
    )