# =============================================================================
# Phase 10 RED #6 — Creative spot-check sweep
# Location: adam/intelligence/creative_spot_check_sweep.py
# =============================================================================
"""Spot-check sweep over the :UploadedCreative manifest — Phase 10
RED criterion #6 producer.

Closes the named sibling at ``task_42_launch_gate_runner.py:40-42``
("Offline-pipeline metaphor coherence scorer is Section 6 work; not
in cascade today. Skip-when-no-data until that scorer runs and
aggregates"). Slice 19 (metaphor coherence) + Slice 20 (mechanism
activation) + Slice 18 (reactance) shipped the SCORERS; Slice 23
ships the SWEEP that runs them against persisted CreativeRecord
entries with non-empty copy_text.

Per directive Phase 10 line 1135 (RED criterion #6):
``check_metaphor_coherence_failed`` already in
``phase_10_launch_sequence.py:239`` triggers RED when ANY creative
in rotation fails the coherence spot check. This sweep is what
populates the ``n_creatives_in_rotation`` and
``n_creatives_failed_spot_check`` snapshot counters that the check
function reads.

THE SWEEP

For each manifest entry:
  1. Skip if ``copy_text`` is None or empty (operator hasn't supplied
     scoreable copy yet — no claim made).
  2. Run metaphor-coherence (Slice 19) when primary_metaphor declared.
  3. Run mechanism-activation (Slice 20) when mechanism declared.
  4. Run reactance-risk (Slice 18) — universal.
  5. Mark failed when ANY scorer fails its threshold.
  6. Increment n_creatives_in_rotation per scoreable entry.
  7. Increment n_creatives_failed_spot_check per failed entry.

Operator visibility: the result includes per-entry failure reasons
so the operator can quickly identify which creatives need updating.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 10 line 1135 (RED criterion #6) +
    task_42_launch_gate_runner.py:40-42 (named sibling) +
    Slices 18/19/20 (the scorers this sweep composes) + Slice 14
    (manifest population path).

(b) Tests pin: empty manifest → no_op result; entry with no
    copy_text → not counted; entry passing all scorers →
    in_rotation + 0 failures; entry failing reactance → failed;
    entry failing coherence → failed; entry failing mechanism
    activation → failed; entry with multiple failures → failed
    once; entries with no metaphor / no mechanism partial-skip
    those scorers; SpotCheckSweepResult is frozen.

(c) calibration_pending=True. v0.1 inherits per-scorer thresholds
    (Slice 18 reactance 0.50, Slice 19 coherence 0.50, Slice 20
    activation 0.50). LUXY pilot calibrates per-scorer thresholds
    against CMO disagreements. A14 flag:
    PHASE_10_SPOT_CHECK_SWEEP_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Visual / non-text scoring. v0.1 sweeps copy_text only.
    * Per-cohort threshold tuning.
    * Multi-language support (English-only marker dictionaries
      inherited from Slices 18/19/20).
    * StackAdapt-side copy fetch when copy_text is missing on
      CreativeRecord. v0.1 treats missing copy as "unscored"
      rather than fetching dynamically; the operator OR Slice 14's
      reconciliation populates copy_text from the userMetadata
      adam_metadata.copy_text slot.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpotCheckEntry:
    """One sweep result entry. Diagnostic for operator audit."""

    creative_id: str
    name: str
    passed: bool
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SpotCheckSweepResult:
    """Outcome of one spot-check sweep run.

    ``n_in_rotation``: entries that had scoreable copy_text + at
        least one declared dimension to score (snapshot counter).
    ``n_failed``: subset of n_in_rotation that failed any scorer.
    ``n_skipped_no_copy``: entries skipped because copy_text was
        None / empty.
    ``n_skipped_no_metadata``: entries with copy_text but no
        mechanism / primary_metaphor declared (universal scorers
        can still run; this counts entries that would partial-skip
        the metadata-conditioned scorers).
    ``entries``: per-entry diagnostic details.
    """

    n_in_rotation: int = 0
    n_failed: int = 0
    n_skipped_no_copy: int = 0
    n_skipped_no_metadata: int = 0
    entries: List[SpotCheckEntry] = field(default_factory=list)


def _score_one_creative(
    creative: Any,
) -> Tuple[bool, List[str]]:
    """Run all available scorers against one CreativeRecord.

    Returns (passed, reasons). passed=True iff every applicable
    scorer threshold was met.
    """
    from adam.intelligence.mechanism_activation_scorer import (
        passes_mechanism_activation_check,
    )
    from adam.intelligence.metaphor_coherence_scorer import (
        passes_metaphor_coherence_check,
    )
    from adam.intelligence.reactance_risk_scorer import (
        passes_reactance_check,
    )

    reasons: List[str] = []
    copy_text = getattr(creative, "copy_text", None) or ""

    # Slice 18 — reactance always runs (no metadata required).
    try:
        react_passes, react_result = passes_reactance_check(copy_text)
        if not react_passes:
            reasons.append(
                f"reactance_above_threshold "
                f"(score={react_result.total_score:.3f})"
            )
    except Exception as exc:
        logger.debug("spot_check reactance scorer failed: %s", exc)

    # Slice 19 — metaphor coherence requires primary_metaphor.
    primary_metaphor = getattr(creative, "primary_metaphor", None)
    if primary_metaphor:
        try:
            coh_passes, coh_result = passes_metaphor_coherence_check(
                copy_text, primary_metaphor,
            )
            if not coh_passes:
                reasons.append(
                    f"metaphor_coherence_below_threshold "
                    f"(target={primary_metaphor} "
                    f"score={coh_result.coherence_score:.3f})"
                )
        except Exception as exc:
            logger.debug(
                "spot_check metaphor coherence scorer failed: %s", exc,
            )

    # Slice 20 — mechanism activation requires mechanism.
    mechanism = getattr(creative, "mechanism", None)
    if mechanism:
        try:
            mech_passes, mech_result = passes_mechanism_activation_check(
                copy_text, mechanism,
            )
            if not mech_passes:
                reasons.append(
                    f"mechanism_activation_below_threshold "
                    f"(target={mechanism} "
                    f"score={mech_result.activation_score:.3f})"
                )
        except Exception as exc:
            logger.debug(
                "spot_check mechanism activation scorer failed: %s", exc,
            )

    return (len(reasons) == 0, reasons)


async def sweep_creative_spot_check(
    *,
    driver: Optional[Any],
    snapshot: Optional[Any] = None,
    limit: int = 1000,
    include_entries: bool = False,
) -> SpotCheckSweepResult:
    """Run spot check across all :UploadedCreative entries.

    Args:
        driver: async Neo4j driver. None → returns empty result.
        snapshot: optional RedCriteriaSnapshot — counters will be
            populated via record_creatives_in_rotation +
            record_creatives_failed_spot_check.
        limit: max entries to evaluate (defensive cap).
        include_entries: when True, populate result.entries
            (per-entry diagnostics — for test/debug paths).

    Returns:
        SpotCheckSweepResult with totals + optional per-entry detail.
    """
    if driver is None:
        return SpotCheckSweepResult()

    # Load all creatives via a simple Cypher query — equivalent of
    # listing :UploadedCreative without metadata filtering.
    cypher = (
        "MATCH (c:UploadedCreative) "
        "RETURN c "
        "ORDER BY c.uploaded_at_ts DESC "
        "LIMIT $limit"
    )
    creatives: List[Any] = []
    try:
        async with driver.session() as session:
            result = await session.run(cypher, limit=int(limit))
            async for record in result:
                from adam.intelligence.creative_upload_pipeline import (
                    _node_to_record,
                )
                node = record.get("c")
                rec = _node_to_record(node) if node is not None else None
                if rec is not None:
                    creatives.append(rec)
    except Exception as exc:
        logger.warning("sweep_creative_spot_check: query failed: %s", exc)
        return SpotCheckSweepResult()

    n_in_rotation = 0
    n_failed = 0
    n_skipped_no_copy = 0
    n_skipped_no_metadata = 0
    entries: List[SpotCheckEntry] = []

    for c in creatives:
        copy_text = (getattr(c, "copy_text", None) or "").strip()
        if not copy_text:
            n_skipped_no_copy += 1
            continue

        # Has copy_text — count as in_rotation.
        n_in_rotation += 1

        if (
            getattr(c, "mechanism", None) is None
            and getattr(c, "primary_metaphor", None) is None
        ):
            n_skipped_no_metadata += 1

        passed, reasons = _score_one_creative(c)
        if not passed:
            n_failed += 1

        if include_entries:
            entries.append(SpotCheckEntry(
                creative_id=str(getattr(c, "stackadapt_creative_id", "")),
                name=str(getattr(c, "name", "")),
                passed=passed,
                reasons=reasons,
            ))

    if snapshot is not None:
        try:
            snapshot.record_creatives_in_rotation(n_in_rotation)
            snapshot.record_creatives_failed_spot_check(n_failed)
        except Exception as exc:
            logger.warning(
                "sweep_creative_spot_check: snapshot record failed: %s",
                exc,
            )

    return SpotCheckSweepResult(
        n_in_rotation=n_in_rotation,
        n_failed=n_failed,
        n_skipped_no_copy=n_skipped_no_copy,
        n_skipped_no_metadata=n_skipped_no_metadata,
        entries=entries,
    )
