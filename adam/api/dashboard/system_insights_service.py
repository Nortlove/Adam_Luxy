"""System Insights — Front-end B (internal / superadmin) service layer.

Aggregates Enhancement #33's per-archetype retargeting learning into
system-wide views that answer the operator's core questions:

  - Which (archetype × barrier × mechanism) cells has the system
    accumulated real confidence in? (The top_converged list.)

  - Which are still noisy — evidence is accumulating but hasn't crossed
    a threshold yet? (novel_findings.)

  - Which mechanisms recur across multiple archetypes — platform-level
    signals worth treating as stronger priors for new campaigns?
    (cross_archetype_patterns.)

Internal-only. This surface exposes raw taxonomy (archetype slugs,
barrier and mechanism names, posterior numerics) deliberately — that
is the point of Front-end B. Client surfaces never consume this.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from adam.api.dashboard.models import (
    AdvertiserSummary,
    ConvergedCell,
    CrossArchetypePattern,
    NovelFinding,
    SystemConvergenceResponse,
)

logger = logging.getLogger(__name__)


# Canonical LUXY archetypes — duplicated here rather than imported so the
# service is resilient to constants-module refactors during the rebuild.
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


# Thresholds for categorizing the state of a posterior. These are
# pilot-grade defaults; they should migrate to configurable settings
# when they become load-bearing for the learning loop itself.
CONVERGENCE_RANK_THRESHOLD = 0.4
"""Cells with mean * confidence >= this score land in top_converged."""

MIN_SAMPLES_FOR_CONVERGED = 5
"""Floor — a high mean with 2 samples is not converged; it's lucky."""

NOVEL_MIN_SAMPLES = 2
"""Floor for appearing in novel_findings — we need at least one data point."""

NOVEL_MAX_RANK = CONVERGENCE_RANK_THRESHOLD
"""Ceiling for novel — anything above it is converged, not novel."""


@dataclass
class _CellObservation:
    """Intermediate scratch-space per (archetype, barrier, mechanism) cell."""
    archetype: str
    barrier: str
    mechanism: str
    mean: float
    alpha: float
    beta: float
    sample_count: int
    confidence: float

    @property
    def rank_score(self) -> float:
        return self.mean * self.confidence

    def to_converged(self) -> ConvergedCell:
        return ConvergedCell(
            archetype=self.archetype,
            barrier=self.barrier,
            mechanism=self.mechanism,
            mean=round(self.mean, 4),
            sample_count=self.sample_count,
            confidence=round(self.confidence, 4),
            alpha=round(self.alpha, 2),
            beta=round(self.beta, 2),
            rank_score=round(self.rank_score, 4),
        )


async def compose_system_convergence() -> SystemConvergenceResponse:
    """Gather cross-archetype mechanism posteriors and package for render.

    Non-blocking: when the retargeting stack is unavailable, returns an
    empty response with cells_examined=0 so the UI can render a 'no
    signal yet' state rather than crashing.
    """
    cells = await _gather_cells()

    if not cells:
        return SystemConvergenceResponse(cells_examined=0)

    converged: List[ConvergedCell] = []
    novel: List[NovelFinding] = []

    for c in cells:
        if (
            c.rank_score >= CONVERGENCE_RANK_THRESHOLD
            and c.sample_count >= MIN_SAMPLES_FOR_CONVERGED
        ):
            converged.append(c.to_converged())
        elif (
            c.sample_count >= NOVEL_MIN_SAMPLES
            and c.rank_score < NOVEL_MAX_RANK
        ):
            novel.append(
                NovelFinding(
                    archetype=c.archetype,
                    barrier=c.barrier,
                    mechanism=c.mechanism,
                    mean=round(c.mean, 4),
                    sample_count=c.sample_count,
                    confidence=round(c.confidence, 4),
                    note=_novel_note(c),
                )
            )

    # Sort converged by rank_score descending. Keep top 25 for the
    # operator view — the full list would sprawl and nobody reads
    # a 500-row posterior dump by preference.
    converged.sort(key=lambda x: x.rank_score, reverse=True)
    converged = converged[:25]

    # Novel findings: rank by sample_count descending (accumulation speed)
    # so the "most active non-converged" cells appear first.
    novel.sort(key=lambda x: x.sample_count, reverse=True)
    novel = novel[:15]

    patterns = _detect_cross_archetype_patterns(cells)

    # Advertiser breakdown — single-tenant pilot returns LUXY summary.
    advertiser_summary = AdvertiserSummary(
        advertiser_id="luxy_ride",
        advertiser_name="LUXY Ride",
        total_cells_with_evidence=len(cells),
        top_converged_cell_count=len(converged),
        total_observations=sum(c.sample_count for c in cells),
    )

    return SystemConvergenceResponse(
        top_converged=converged,
        novel_findings=novel,
        cross_archetype_patterns=patterns,
        advertisers=[advertiser_summary],
        cells_examined=len(cells),
    )


async def _gather_cells() -> List[_CellObservation]:
    """Query retargeting mechanism-effectiveness for each archetype ×
    barrier pair and flatten into one list of cell observations."""
    try:
        from adam.retargeting.api import (
            get_mechanism_effectiveness as _endpoint,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "Retargeting API unavailable in system insights composer: %s",
            exc,
        )
        return []

    cells: List[_CellObservation] = []
    for archetype in _LUXY_ARCHETYPES:
        try:
            prevalence_result = await _endpoint(
                mechanism=None, barrier=None, archetype_id=archetype,
            )
        except Exception as exc:
            logger.debug(
                "Prevalence query failed for %s: %s", archetype, exc,
            )
            continue

        prevalence = prevalence_result.get("barrier_prevalence") or {}
        if not prevalence:
            continue

        # For each barrier observed for this archetype, pull the per-
        # mechanism posteriors and record each as a cell.
        for barrier in prevalence.keys():
            try:
                posts_result = await _endpoint(
                    mechanism=None, barrier=barrier, archetype_id=archetype,
                )
            except Exception:
                continue
            posteriors = posts_result.get("posteriors") or {}
            for mech, p in posteriors.items():
                try:
                    cells.append(
                        _CellObservation(
                            archetype=archetype,
                            barrier=barrier,
                            mechanism=mech,
                            mean=float(p.get("mean", 0.0)),
                            alpha=float(p.get("alpha", 0.0)),
                            beta=float(p.get("beta", 0.0)),
                            sample_count=int(p.get("sample_count", 0)),
                            confidence=float(p.get("confidence", 0.0)),
                        )
                    )
                except (TypeError, ValueError):
                    continue
    return cells


def _detect_cross_archetype_patterns(
    cells: List[_CellObservation],
) -> List[CrossArchetypePattern]:
    """Find mechanisms that win (are the top-ranked mechanism for their
    cell) across multiple archetypes. These are platform-level signals
    — evidence that the mechanism is broadly effective rather than
    narrow to one archetype."""
    # Per (archetype, barrier), pick the top-ranked mechanism.
    top_per_cell: Dict[Tuple[str, str], _CellObservation] = {}
    for c in cells:
        key = (c.archetype, c.barrier)
        prior = top_per_cell.get(key)
        if prior is None or c.rank_score > prior.rank_score:
            top_per_cell[key] = c

    # Group archetype winners by mechanism.
    by_mechanism: Dict[str, List[_CellObservation]] = defaultdict(list)
    for cell in top_per_cell.values():
        if cell.sample_count < MIN_SAMPLES_FOR_CONVERGED:
            continue
        by_mechanism[cell.mechanism].append(cell)

    patterns: List[CrossArchetypePattern] = []
    for mech, winners in by_mechanism.items():
        archetypes = sorted({w.archetype for w in winners})
        if len(archetypes) < 2:
            continue  # not cross-archetype
        total_samples = sum(w.sample_count for w in winners)
        mean_across = (
            sum(w.mean * w.sample_count for w in winners) / total_samples
            if total_samples > 0 else 0.0
        )
        # If every winner shares the same barrier, report it; otherwise
        # None (the pattern spans multiple barriers).
        barriers = {w.barrier for w in winners}
        shared_barrier = next(iter(barriers)) if len(barriers) == 1 else None
        patterns.append(
            CrossArchetypePattern(
                mechanism=mech,
                archetypes=archetypes,
                barrier=shared_barrier,
                mean_across_archetypes=round(mean_across, 4),
                total_sample_count=total_samples,
            )
        )

    # Rank by breadth (archetype count) then by total samples.
    patterns.sort(
        key=lambda p: (len(p.archetypes), p.total_sample_count),
        reverse=True,
    )
    return patterns[:10]


def _novel_note(cell: _CellObservation) -> str:
    """Short, operator-facing note classifying why a cell is novel."""
    if cell.mean > 0.6 and cell.sample_count < 5:
        return "high mean but few samples — could be lucky or real; more impressions will disambiguate"
    if cell.mean > 0.4 and cell.confidence < 0.3:
        return "moderate mean, low confidence — evidence accumulating, watch"
    if cell.mean < 0.3 and cell.sample_count >= 5:
        return "repeated low-efficacy signal — candidate for suppression"
    return "evidence still developing"
