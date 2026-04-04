# =============================================================================
# Barrier Self-Report Extractor — Signal 2
# Location: adam/retargeting/engines/barrier_self_report.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 3
# =============================================================================

"""
Extracts barrier diagnosis from post-click site behavior.

The research validation identified three problems with first-page-only
inference: (1) 75-90% bounce rates mean most visitors have no second page,
(2) first navigation reflects salience/scent not necessarily need,
(3) time-weighted full paths are categorically more predictive.

The fix: extract barrier signal from THREE layers, not just page navigation.

Layer 1: Micro-interactions on the landing page (solves bounce problem)
    Even single-page visitors generate barrier signal through scroll
    behavior and section dwell.

Layer 2: Page navigation path (when available)
    Time-weighted path analysis for multi-page sessions.

Layer 3: Micro-interactions within sections
    FAQ expands, video plays, pricing calculator use — active
    engagement is more diagnostic than passive scrolling.

The barrier with highest weighted engagement is the self-reported barrier.
When self-report disagrees with the DiagnosticReasoner's algorithmic
diagnosis at confidence > 0.5, the self-report OVERRIDES. The person's
own behavior is a stronger signal than the model.
"""

import logging
from typing import Any, Dict, List, Optional

from adam.retargeting.models.telemetry import (
    SectionEngagement,
    TelemetrySessionPayload,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION-TO-BARRIER MAPPING
# =============================================================================

# Maps DOM section IDs on the advertiser's site to conversion barriers
# and the bilateral alignment dimensions most relevant to each barrier.
#
# These are configured per-site. The luxyride.com mapping is the default.
# For other sites, override SECTION_BARRIER_MAP via config.

SECTION_BARRIER_MAP: Dict[str, Dict[str, Any]] = {
    "section-pricing": {
        "barrier": "price_friction",
        "dims": ["anchor_susceptibility_match", "spending_pain"],
    },
    "section-reviews": {
        "barrier": "trust_deficit",
        "dims": ["brand_trust_fit"],
    },
    "section-testimonials": {
        "barrier": "trust_deficit",
        "dims": ["brand_trust_fit", "emotional_resonance"],
    },
    "section-how-it-works": {
        "barrier": "processing_overload",
        "dims": ["processing_route"],
    },
    "section-safety": {
        "barrier": "trust_deficit",
        "dims": ["brand_trust_fit", "negativity_bias_match"],
    },
    "section-fleet": {
        "barrier": "quality_uncertainty",
        "dims": ["quality_evidence_match"],
    },
    "section-booking": {
        "barrier": "intention_action_gap",
        "dims": [],
    },
    "section-faq": {
        "barrier": "processing_overload",
        "dims": ["processing_route"],
    },
}

# Page-path-to-barrier mapping for Layer 2 (navigation path)
PAGE_BARRIER_MAP: Dict[str, Dict[str, Any]] = {
    "/pricing": {
        "barrier": "price_friction",
        "dims": ["anchor_susceptibility_match", "spending_pain"],
    },
    "/reviews": {
        "barrier": "trust_deficit",
        "dims": ["brand_trust_fit"],
    },
    "/about": {
        "barrier": "trust_deficit",
        "dims": ["brand_trust_fit"],
    },
    "/faq": {
        "barrier": "processing_overload",
        "dims": ["processing_route"],
    },
    "/how-it-works": {
        "barrier": "processing_overload",
        "dims": ["processing_route"],
    },
    "/booking": {
        "barrier": "intention_action_gap",
        "dims": [],
    },
    "/fleet": {
        "barrier": "quality_uncertainty",
        "dims": ["quality_evidence_match"],
    },
}

# Minimum dwell threshold: 2 seconds.
# Under 2s is likely scroll-through, not deliberate engagement.
MIN_DWELL_SECONDS = 2.0


# =============================================================================
# BARRIER SELF-REPORT EXTRACTOR
# =============================================================================

class BarrierSelfReportExtractor:
    """Extract barrier diagnosis from post-click behavior.

    Uses three layers:
    1. Section-level dwell (works even for single-page bounces)
    2. Page navigation path (when available)
    3. Micro-interactions (FAQ expands, video plays, etc.)

    The barrier with highest weighted engagement is the self-reported barrier.
    """

    def __init__(
        self,
        section_map: Optional[Dict] = None,
        page_map: Optional[Dict] = None,
    ):
        self._section_map = section_map or SECTION_BARRIER_MAP
        self._page_map = page_map or PAGE_BARRIER_MAP

    def extract_barrier(
        self,
        section_engagements: List[SectionEngagement],
        pages_visited: Optional[List] = None,
        total_session_seconds: float = 0.0,
        bounced: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Compute barrier scores from session engagement data.

        Args:
            section_engagements: List of SectionEngagement from telemetry.
            pages_visited: List of PageVisit from telemetry (Layer 2).
            total_session_seconds: Total session duration.
            bounced: Whether the visitor only saw one page.

        Returns:
            Dict with self_reported_barrier, confidence, dimensions_to_target,
            all_barrier_scores, or None if no signal.
        """
        barrier_scores: Dict[str, float] = {}
        barrier_dims: Dict[str, List[str]] = {}

        # Layer 1: Section-level dwell
        # Weight = dwell_seconds * (1 + 0.5 * interactions)
        # Interaction bonus accounts for active engagement being
        # more diagnostic than passive scrolling.
        for se in section_engagements:
            mapping = self._section_map.get(se.section_id)
            if not mapping:
                continue

            if se.dwell_seconds < MIN_DWELL_SECONDS:
                continue

            barrier = mapping["barrier"]
            weight = se.dwell_seconds * (1.0 + 0.5 * se.interactions)

            barrier_scores[barrier] = barrier_scores.get(barrier, 0.0) + weight
            barrier_dims[barrier] = mapping["dims"]

        # Layer 2: Page navigation path (multi-page sessions)
        if pages_visited and len(pages_visited) > 1:
            for page in pages_visited:
                url = getattr(page, "url", "") if hasattr(page, "url") else str(page.get("url", ""))
                dwell = getattr(page, "dwell_seconds", 0.0) if hasattr(page, "dwell_seconds") else float(page.get("dwell_seconds", 0))

                # Match URL path against page map
                matched_mapping = None
                for path_prefix, pm in self._page_map.items():
                    if url.startswith(path_prefix):
                        matched_mapping = pm
                        break

                if matched_mapping and dwell >= MIN_DWELL_SECONDS:
                    barrier = matched_mapping["barrier"]
                    # Navigation is a weaker signal than section dwell (0.5x)
                    weight = dwell * 0.5
                    barrier_scores[barrier] = barrier_scores.get(barrier, 0.0) + weight
                    if barrier not in barrier_dims:
                        barrier_dims[barrier] = matched_mapping["dims"]

        if not barrier_scores:
            return None

        # Top barrier by weighted engagement
        top_barrier = max(barrier_scores, key=barrier_scores.get)
        total_weight = sum(barrier_scores.values())
        confidence = (
            barrier_scores[top_barrier] / total_weight if total_weight > 0 else 0.0
        )

        return {
            "self_reported_barrier": top_barrier,
            "confidence": round(confidence, 3),
            "dimensions_to_target": barrier_dims.get(top_barrier, []),
            "all_barrier_scores": {
                k: round(v, 2) for k, v in sorted(
                    barrier_scores.items(), key=lambda x: -x[1]
                )
            },
            "session_seconds": total_session_seconds,
            "bounced": bounced,
        }

    def extract_from_telemetry(
        self,
        payload: TelemetrySessionPayload,
    ) -> Optional[Dict[str, Any]]:
        """Convenience method: extract barrier from a full telemetry payload."""
        return self.extract_barrier(
            section_engagements=payload.section_engagements,
            pages_visited=payload.pages_visited,
            total_session_seconds=payload.total_session_seconds,
            bounced=payload.bounced,
        )

    def compare_to_algorithmic(
        self,
        self_report: Dict[str, Any],
        algorithmic_barrier: str,
    ) -> Dict[str, Any]:
        """Compare self-reported barrier to DiagnosticReasoner's diagnosis.

        Override rules:
        - If self-report confidence > 0.5 AND disagrees with algorithm:
          override. The person's behavior is a stronger signal.
        - If they agree: log as calibration validation.
        - If self-report confidence < 0.5: don't override (ambiguous).

        Args:
            self_report: Output from extract_barrier().
            algorithmic_barrier: The DiagnosticReasoner's barrier diagnosis.

        Returns:
            Dict with override decision and reasoning.
        """
        agrees = self_report["self_reported_barrier"] == algorithmic_barrier

        if agrees:
            return {
                "override": False,
                "barrier": algorithmic_barrier,
                "agreement": True,
                "note": "Self-report confirms algorithmic diagnosis. Model calibrated.",
            }
        elif self_report["confidence"] > 0.5:
            return {
                "override": True,
                "barrier": self_report["self_reported_barrier"],
                "original_barrier": algorithmic_barrier,
                "dimensions_to_target": self_report["dimensions_to_target"],
                "override_confidence": self_report["confidence"],
                "note": (
                    f"User behavior indicates {self_report['self_reported_barrier']} "
                    f"(confidence {self_report['confidence']:.2f}), "
                    f"overriding algorithmic diagnosis of {algorithmic_barrier}."
                ),
            }
        else:
            return {
                "override": False,
                "barrier": algorithmic_barrier,
                "agreement": False,
                "note": "Self-report ambiguous (low confidence). Keeping algorithmic diagnosis.",
            }


def get_barrier_extractor(
    section_map: Optional[Dict] = None,
    page_map: Optional[Dict] = None,
) -> BarrierSelfReportExtractor:
    """Get a BarrierSelfReportExtractor instance."""
    return BarrierSelfReportExtractor(section_map=section_map, page_map=page_map)
