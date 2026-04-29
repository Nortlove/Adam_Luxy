# =============================================================================
# ADAM Agency-Facing Dashboard Aggregator (task #33)
# Location: adam/intelligence/agency_dashboard.py
# =============================================================================

"""
AGENCY-FACING DASHBOARD — JSON payload aggregator

Per simulation: this is the artifact that makes Becca's next pitch
undeniable. Real-time view of mechanism rotation per archetype with
conversion lift attached, processing-depth per arm, page-context-
conditional CTR, three-timescale views per HMT §A9 discipline, and
A14 retirement-trigger progress reading the Prometheus counter.

WHAT THIS LANDS

A pure aggregator function `build_agency_dashboard_payload(...)` that
takes the relevant inputs and returns a JSON-serializable dict
suitable for direct API response or frontend rendering. The frontend
framework is deferred — the payload is the contract.

THE PAYLOAD

```
{
  "decision_summary": {
    "request_id": "...",
    "primary_mechanism": "authority",
    "archetype": "careful_truster",
    "cascade_level": 3,
    "edge_count": 1234
  },
  "uncertainty_panel": {  // from dialogue_ledger.uncertainty_panel
    "confident": [...],
    "uncertain": [...],
    "possibly_wrong": [...]
  },
  "construct_chain": {  // from chain_rendering
    "recommendation_summary": "...",
    "n_attestations": 3,
    "attestations": [...]
  },
  "rotation_events": [  // from mechanism_rotation
    {
      "rotation_id": "...",
      "public_summary": "...",
      "triggered_at": "..."
    }
  ],
  "attention_inversion_diagonals": {  // from mechanism_taxonomy_runtime
    "matched": [{...}],
    "mismatched": [{...}]
  },
  "page_posture_predictions": {  // from page_attentional_posture_substrate
    "author_predictions_count": 12,
    "publication_predictions_count": 5
  },
  "session_mood": {  // from dialogue_ledger.mood_probe
    "mood_index": 0.75,
    "confidence": 1.0
  } | null
}
```

VOCABULARY DISCIPLINE

Per orientation A10 + simulation analysis: this dashboard MUST NOT
look like a programmatic dashboard. CPA / ROAS / CTR are not primary.
The cognitive vocabulary leads:

  - "construct_chain" not "reasoning explanation"
  - "uncertainty_panel" not "confidence scores"
  - "rotation_events" not "campaign updates"
  - "attention_inversion_diagonals" not "performance segments"
  - "session_mood" not "user sentiment"

The frontend is responsible for not undoing this in display labels.
The backend payload is the source of truth on naming.

PILOT 2 STORY

By Week 8 of pilot:
  - rotation_events shows 1+ pre-registered rotations TRIGGERED, with
    conversion-rate before/after attached
  - attention_inversion_diagonals shows matched > mismatched on
    conversion rate (Foundation §2 prediction empirically supported)
  - construct_chain renders the cognitive explanation for every
    recommendation Becca shows LUXY
  - uncertainty_panel surfaces what's calibration-pending — making
    A14 discipline visible publicly

Becca's pitch slide: this dashboard, screenshot. No DSP can show this.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.intelligence.chain_rendering import (
    RecommendationChainRendering,
    recommendation_to_dict,
)
from adam.intelligence.dialogue_ledger.mood_probe import SessionMoodState
from adam.intelligence.dialogue_ledger.uncertainty_panel import (
    UncertaintyBucket,
    UncertaintyPanel,
)
from adam.intelligence.mechanism_rotation import (
    RotationEvent,
    RotationRegistry,
)
from adam.intelligence.mechanism_taxonomy_runtime import (
    CategoryConditionalCounts,
    TaxonomyConditionalAccumulator,
)
from adam.intelligence.page_attentional_posture_substrate import (
    PageAttentionalPostureAccumulator,
)


# =============================================================================
# SECTION SERIALIZERS
# =============================================================================


def _uncertainty_panel_to_dict(panel: UncertaintyPanel) -> Dict[str, Any]:
    """Serialize an UncertaintyPanel for the dashboard payload.

    Returns a dict with the three bucket lists where each item is a
    JSON-friendly dict.
    """
    def _item_to_dict(item: Any) -> Dict[str, Any]:
        return {
            "claim": item.claim,
            "bucket": item.bucket.value,
            "evidence_trace": list(item.evidence_trace),
            "quantitative_basis": dict(item.quantitative_basis),
        }

    return {
        "confident": [_item_to_dict(it) for it in panel.confident],
        "uncertain": [_item_to_dict(it) for it in panel.uncertain],
        "possibly_wrong": [_item_to_dict(it) for it in panel.possibly_wrong],
        "summary": dict(panel.panel_summary),
    }


def _rotation_events_to_list(
    rotation_registry: RotationRegistry,
) -> List[Dict[str, Any]]:
    """Serialize all triggered rotation events for dashboard rendering."""
    events: List[Dict[str, Any]] = []
    for event in rotation_registry.all_triggered_events():
        events.append({
            "rotation_id": event.rotation_id,
            "triggered_at": event.triggered_at.isoformat(),
            "public_summary": event.public_summary(),
            "from_mechanism": event.from_evidence.mechanism,
            "to_mechanism": event.to_evidence.mechanism,
            "from_edge_count": event.from_evidence.edge_count,
            "to_edge_count": event.to_evidence.edge_count,
            "from_cate_estimate": event.from_evidence.cate_estimate,
            "to_cate_estimate": event.to_evidence.cate_estimate,
            "commitment_public_statement": event.commitment_public_statement,
        })
    return events


def _diagonals_to_dict(
    accumulator: TaxonomyConditionalAccumulator,
) -> Dict[str, Any]:
    """Serialize the matched-vs-mismatched diagonals for dashboard."""
    matched, mismatched = accumulator.matched_vs_mismatched_diagonals()

    def _cell_to_dict(cell: CategoryConditionalCounts) -> Dict[str, Any]:
        return {
            "mechanism_category": cell.mechanism_category.value,
            "page_attentional_posture": cell.page_attentional_posture,
            "n_decisions": cell.n_decisions,
            "n_conversions": cell.n_conversions,
            "n_backfires": cell.n_backfires,
            "conversion_rate": cell.conversion_rate,
            "backfire_rate": cell.backfire_rate,
        }

    matched_list = [_cell_to_dict(c) for c in matched]
    mismatched_list = [_cell_to_dict(c) for c in mismatched]

    # Aggregate stats for the Foundation §2 test
    matched_total_decisions = sum(c["n_decisions"] for c in matched_list)
    matched_total_conversions = sum(c["n_conversions"] for c in matched_list)
    mismatched_total_decisions = sum(c["n_decisions"] for c in mismatched_list)
    mismatched_total_conversions = sum(c["n_conversions"] for c in mismatched_list)

    return {
        "matched": matched_list,
        "mismatched": mismatched_list,
        "matched_aggregate_conversion_rate": (
            matched_total_conversions / matched_total_decisions
            if matched_total_decisions else 0.0
        ),
        "mismatched_aggregate_conversion_rate": (
            mismatched_total_conversions / mismatched_total_decisions
            if mismatched_total_decisions else 0.0
        ),
        "n_matched_decisions": matched_total_decisions,
        "n_mismatched_decisions": mismatched_total_decisions,
    }


def _page_posture_summary(
    accumulator: PageAttentionalPostureAccumulator,
) -> Dict[str, Any]:
    """Serialize page-posture accumulator stats."""
    return {
        "author_predictions_count": len(accumulator.all_author_ids()),
        "publication_predictions_count": len(accumulator.all_publication_ids()),
        "section_predictions_count": len(accumulator.all_section_ids()),
    }


def _mood_state_to_dict(
    mood: Optional[SessionMoodState],
) -> Optional[Dict[str, Any]]:
    if mood is None:
        return None
    return {
        "mood_index": mood.mood_index,
        "confidence": mood.confidence,
        "set_at": mood.set_at.isoformat(),
        "deadline_hit": mood.deadline_hit,
    }


# =============================================================================
# MAIN AGGREGATOR
# =============================================================================


def build_agency_dashboard_payload(
    *,
    decision_summary: Dict[str, Any],
    uncertainty_panel: Optional[UncertaintyPanel] = None,
    chain_rendering: Optional[RecommendationChainRendering] = None,
    rotation_registry: Optional[RotationRegistry] = None,
    taxonomy_accumulator: Optional[TaxonomyConditionalAccumulator] = None,
    page_posture_accumulator: Optional[PageAttentionalPostureAccumulator] = None,
    session_mood: Optional[SessionMoodState] = None,
    a14_flags_active: Optional[List[str]] = None,
    generated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build the partner-facing dashboard payload.

    Pure function — no I/O, no LLM, no side effects. The caller assembles
    the inputs (typically from a single decision flow + the global
    accumulator singletons) and the function returns the JSON-serializable
    payload.

    All sections are OPTIONAL — pass None for sections not yet available
    (e.g., during pilot warmup the rotation_events section is empty).
    The payload always includes `decision_summary` as the load-bearing
    one-line context.
    """
    if not decision_summary:
        raise ValueError("decision_summary is required")

    payload: Dict[str, Any] = {
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "decision_summary": dict(decision_summary),
    }

    if uncertainty_panel is not None:
        payload["uncertainty_panel"] = _uncertainty_panel_to_dict(uncertainty_panel)

    if chain_rendering is not None:
        payload["construct_chain"] = recommendation_to_dict(chain_rendering)

    if rotation_registry is not None:
        events = _rotation_events_to_list(rotation_registry)
        payload["rotation_events"] = events
        payload["rotation_events_count"] = len(events)

    if taxonomy_accumulator is not None:
        payload["attention_inversion_diagonals"] = _diagonals_to_dict(
            taxonomy_accumulator,
        )

    if page_posture_accumulator is not None:
        payload["page_posture"] = _page_posture_summary(page_posture_accumulator)

    if session_mood is not None:
        payload["session_mood"] = _mood_state_to_dict(session_mood)

    if a14_flags_active:
        payload["a14_flags_active"] = list(a14_flags_active)

    return payload


# =============================================================================
# Convenience: Foundation §2 attention-inversion test result
# =============================================================================


def attention_inversion_test_result(
    accumulator: TaxonomyConditionalAccumulator,
) -> Dict[str, Any]:
    """Compact test-result dict for Foundation §2 prediction.

    Returns:
        {
          "matched_conversion_rate": float,
          "mismatched_conversion_rate": float,
          "absolute_lift": float,  // matched - mismatched
          "relative_lift": float | None,  // None when mismatched_rate=0
          "n_matched": int,
          "n_mismatched": int,
          "supports_foundation_prediction": bool,  // true iff matched > mismatched AND n thresholds met
          "interpretive_note": str
        }
    """
    matched, mismatched = accumulator.matched_vs_mismatched_diagonals()

    n_matched_decisions = sum(c.n_decisions for c in matched)
    n_matched_conversions = sum(c.n_conversions for c in matched)
    n_mismatched_decisions = sum(c.n_decisions for c in mismatched)
    n_mismatched_conversions = sum(c.n_conversions for c in mismatched)

    matched_rate = (
        n_matched_conversions / n_matched_decisions
        if n_matched_decisions else 0.0
    )
    mismatched_rate = (
        n_mismatched_conversions / n_mismatched_decisions
        if n_mismatched_decisions else 0.0
    )
    absolute_lift = matched_rate - mismatched_rate
    relative_lift = (
        absolute_lift / mismatched_rate
        if mismatched_rate > 0 else None
    )

    # Foundation §2 prediction: matched > mismatched on conversion rate
    # WITH minimum sample size for both arms (50 per arm — per LUXY
    # pilot scale).
    min_per_arm = 50
    enough_data = (
        n_matched_decisions >= min_per_arm
        and n_mismatched_decisions >= min_per_arm
    )
    supports_prediction = enough_data and (matched_rate > mismatched_rate)

    if not enough_data:
        note = (
            f"Insufficient data for Foundation §2 test "
            f"(matched={n_matched_decisions}, mismatched={n_mismatched_decisions}, "
            f"min={min_per_arm} each)"
        )
    elif supports_prediction:
        note = (
            f"Foundation §2 prediction supported: matched conversion "
            f"rate ({matched_rate:.4f}) exceeds mismatched "
            f"({mismatched_rate:.4f})"
        )
    else:
        note = (
            f"Foundation §2 prediction NOT supported by current data: "
            f"matched ({matched_rate:.4f}) does not exceed mismatched "
            f"({mismatched_rate:.4f}). Investigate before next pilot."
        )

    return {
        "matched_conversion_rate": matched_rate,
        "mismatched_conversion_rate": mismatched_rate,
        "absolute_lift": absolute_lift,
        "relative_lift": relative_lift,
        "n_matched": n_matched_decisions,
        "n_mismatched": n_mismatched_decisions,
        "supports_foundation_prediction": supports_prediction,
        "interpretive_note": note,
    }


__all__ = [
    "attention_inversion_test_result",
    "build_agency_dashboard_payload",
]
