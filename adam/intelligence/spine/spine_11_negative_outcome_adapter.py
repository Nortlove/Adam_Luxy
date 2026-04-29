# =============================================================================
# ADAM Spine #11 — LUXY-Specific Negative-Outcome Adapter
# Location: adam/intelligence/spine/spine_11_negative_outcome_adapter.py
# =============================================================================

"""LUXY-specific negative-outcome adapter — multivariate outcome layer.

PER DIRECTIVE SECTION 2 (Spine #11 specification).

A multivariate outcome layer that explicitly captures negative outcomes —
clicked-but-bounced, viewed-and-disengaged, audience-membership-without-
conversion, frequency-cap-fired-without-engagement, time-on-page-below-
threshold, scroll-past-without-fixation — and pushes them as explicit
Pixel events.

Why this is spine: at ~$30K/week and B2B-travel conversion sparsity
(estimated 30-600 conversions/week), positive outcomes alone are
statistically too thin to drive per-user posterior updates. Negative
outcomes are dense, informative, and currently treated as missing data
by industry. Treating non-response as informative is the predictive-
coding insight: prediction error under "I expected this user to engage
and they didn't" is the highest-information-gain event in the funnel.

DECISION-TIME CONSUMER (Rule A check)

This adapter is consumed at OUTCOME time (which is decision-time-adjacent
— the next decision for this user reads the updated posterior produced
by routing this outcome through Spine #1):

    - Spine #1 (N-of-1 hierarchical Bayesian engine) receives every
      classified outcome and runs the BONG update on the user
      posterior. The next decision for that user reads the updated
      posterior.
    - Spine #6 (DecisionTrace) is closed when the outcome arrives
      (linking trace to outcome via sapid).
    - Spine #2 (scheduler) reads the outcome class from TouchEvent
      to determine if the next ABAB step in the replication phase
      should advance.

Therefore: cognitive primitive that closes the learning loop. NOT
measurement infrastructure.

THIS COMMIT SHIPS

    - RawPixelEvent Pydantic model — incoming raw event from the
      pixel handler (sapid, IP, user-agent, dwell, scroll, viewability,
      booking confirmation, etc.)
    - classify_pixel_event_to_outcome_class — heuristic mapping from
      raw signals to OutcomeClass vocabulary
    - OutcomeEvent — classified, ready-for-routing event
    - sapid round-trip linkage substrate (look up DecisionTrace by
      sapid; close the trace on outcome arrival)
    - route_outcome_to_posterior — calls Spine #1's bong_update_step
      with the outcome's update weight + feature vector

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - The actual FastAPI Pixel handler endpoint (HTTP route, HMAC
      validation, etc.) — wire to existing StackAdapt webhook scaffold
    - Persistent OutcomeEvent store (Neo4j writeback)
    - sapid round-trip MONITORING (load-bearing per directive but a
      separate dashboard concern)

REFERENCES

    Multi-state Markov models for clinical-trial outcome modeling.
    Competing-risks frameworks.
    Predictive-coding non-response treatment.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from adam.intelligence.spine.spine_1_n_of_1_engine import (
    USER_POSTERIOR_DIM,
    UserPosterior,
    bong_update_step,
    get_outcome_schema,
    known_outcome_classes,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Classification thresholds (calibration-pending; pilot-derived)
# =============================================================================


# Per directive Section 3.3 informative defaults; override at pilot time
# from observed distributions.
DEFAULT_DWELL_ENGAGED_SECONDS: float = 5.0
DEFAULT_DWELL_BOUNCED_SECONDS: float = 5.0  # < this → bounced
DEFAULT_SCROLL_ENGAGED_FRACTION: float = 0.25  # ≥ 25% scroll = engaged
DEFAULT_VIEWABILITY_REQUIRED: bool = True


# =============================================================================
# Pydantic models
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RawPixelEvent(BaseModel):
    """Incoming raw pixel event from the LUXY pixel handler / StackAdapt
    Universal Pixel.

    Carries the sapid (StackAdapt postback ID) — the only deterministic
    linkage between a served impression and a downstream observation.
    Per directive Section 3.7: "treat it as sacred."

    Fields are typed but tolerantly schema'd; the LUXY page may report
    a subset of these depending on event type.
    """

    model_config = ConfigDict(extra="forbid")

    sapid: str  # StackAdapt postback ID — the join key
    event_type: str  # e.g., "view", "click", "conversion", "frequency_cap"

    # Engagement signals (optional; populated by the type)
    dwell_seconds: Optional[float] = None
    scroll_fraction: Optional[float] = None  # 0.0 to 1.0
    viewable: Optional[bool] = None
    bounced: Optional[bool] = None  # explicit bounce flag

    # Conversion signals
    is_conversion: bool = False
    is_micro_conversion: bool = False
    conversion_value: Optional[float] = None

    # Audience-lifecycle signals
    audience_aged_out: bool = False
    frequency_cap_fired: bool = False

    # Bookkeeping
    occurred_at: datetime = Field(default_factory=_now_utc)
    user_id: Optional[str] = None  # Resolved from sapid → DecisionTrace lookup
    decision_id: Optional[str] = None  # Same

    @field_validator("sapid")
    @classmethod
    def _validate_sapid_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError(
                "sapid is required and must be non-empty. The sapid is "
                "the only deterministic linkage between served impression "
                "and downstream observation; events without sapid cannot "
                "be routed to the originating user posterior."
            )
        return v


class OutcomeEvent(BaseModel):
    """A classified outcome event ready for posterior update routing.

    Produced by classify_pixel_event_to_outcome_class. Carries the
    outcome_class (one of Spine #1's known vocabulary) plus the linkage
    fields (sapid, user_id, decision_id) the routing function uses.
    """

    model_config = ConfigDict(extra="forbid")

    sapid: str
    outcome_class: str
    user_id: str
    decision_id: str
    occurred_at: datetime = Field(default_factory=_now_utc)
    classification_diagnostic: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("outcome_class")
    @classmethod
    def _validate_known_outcome_class(cls, v: str) -> str:
        if v not in known_outcome_classes():
            raise ValueError(
                f"outcome_class '{v}' not in known vocabulary "
                f"({sorted(known_outcome_classes())}). Either the "
                f"vocabulary is being extended OR a classifier produced "
                f"an unknown class — both indicate a contract violation."
            )
        return v


# =============================================================================
# Classification — raw pixel event → OutcomeClass
# =============================================================================


def classify_pixel_event(
    event: RawPixelEvent,
    *,
    dwell_engaged_seconds: float = DEFAULT_DWELL_ENGAGED_SECONDS,
    dwell_bounced_seconds: float = DEFAULT_DWELL_BOUNCED_SECONDS,
    scroll_engaged_fraction: float = DEFAULT_SCROLL_ENGAGED_FRACTION,
) -> Tuple[str, Dict[str, Any]]:
    """Classify a RawPixelEvent into an outcome_class string + diagnostic.

    Returns (outcome_class, diagnostic_dict). The diagnostic carries
    the classifier's reasoning for partner-facing inspection ("we
    classified this as VIEWED_DISENGAGED because dwell=2.3s and
    scroll=0.08").

    Classification priority (highest→lowest):
        1. is_conversion → CONVERSION
        2. is_micro_conversion → MICRO_CONVERSION
        3. audience_aged_out → AUDIENCE_AGED_OUT
        4. frequency_cap_fired → FREQUENCY_FATIGUE_FIRED
        5. bounced explicit OR (event_type=click AND dwell < bounced
           threshold) → CLICK_BOUNCED
        6. event_type=click AND dwell ≥ engaged threshold → CLICK_QUALIFIED
        7. event_type=view AND viewable AND dwell ≥ engaged AND scroll ≥
           engaged → VIEWED_ENGAGED
        8. event_type=view AND viewable AND (dwell or scroll insufficient)
           → VIEWED_DISENGAGED
        9. event_type=view AND not viewable → IMPRESSION_NON_VIEWABLE
       10. fallthrough → IMPRESSION_NON_VIEWABLE (most conservative)
    """
    diag: Dict[str, Any] = {
        "event_type": event.event_type,
        "dwell_seconds": event.dwell_seconds,
        "scroll_fraction": event.scroll_fraction,
        "viewable": event.viewable,
        "bounced": event.bounced,
    }

    # 1. Conversion (highest priority)
    if event.is_conversion:
        diag["reason"] = "is_conversion=true"
        return "CONVERSION", diag

    # 2. Micro-conversion
    if event.is_micro_conversion:
        diag["reason"] = "is_micro_conversion=true"
        return "MICRO_CONVERSION", diag

    # 3. Audience-lifecycle censoring events
    if event.audience_aged_out:
        diag["reason"] = "audience_aged_out=true"
        return "AUDIENCE_AGED_OUT", diag

    # 4. Frequency-cap fatigue
    if event.frequency_cap_fired:
        diag["reason"] = "frequency_cap_fired=true"
        return "FREQUENCY_FATIGUE_FIRED", diag

    # 5. Click events
    if event.event_type == "click":
        is_bounced = (
            event.bounced is True
            or (event.dwell_seconds is not None
                and event.dwell_seconds < dwell_bounced_seconds)
        )
        if is_bounced:
            diag["reason"] = (
                f"click bounced (explicit={event.bounced}, "
                f"dwell={event.dwell_seconds})"
            )
            return "CLICK_BOUNCED", diag
        if (event.dwell_seconds is not None
                and event.dwell_seconds >= dwell_engaged_seconds):
            diag["reason"] = (
                f"click qualified (dwell={event.dwell_seconds} ≥ "
                f"{dwell_engaged_seconds})"
            )
            return "CLICK_QUALIFIED", diag
        # Click with no dwell signal → conservatively bounced.
        diag["reason"] = "click with no dwell signal"
        return "CLICK_BOUNCED", diag

    # 6. View events
    if event.event_type == "view":
        if event.viewable is not True:
            diag["reason"] = f"view not viewable (viewable={event.viewable})"
            return "IMPRESSION_NON_VIEWABLE", diag
        # Viewable: assess engagement
        dwell_ok = (
            event.dwell_seconds is not None
            and event.dwell_seconds >= dwell_engaged_seconds
        )
        scroll_ok = (
            event.scroll_fraction is not None
            and event.scroll_fraction >= scroll_engaged_fraction
        )
        if dwell_ok and scroll_ok:
            diag["reason"] = (
                f"viewed engaged (dwell={event.dwell_seconds}, "
                f"scroll={event.scroll_fraction})"
            )
            return "VIEWED_ENGAGED", diag
        diag["reason"] = (
            f"viewed disengaged (dwell={event.dwell_seconds}, "
            f"scroll={event.scroll_fraction})"
        )
        return "VIEWED_DISENGAGED", diag

    # Fallthrough
    diag["reason"] = "unrecognized event type; conservative non-viewable"
    return "IMPRESSION_NON_VIEWABLE", diag


# =============================================================================
# Sapid round-trip — the linkage between served impression and outcome
# =============================================================================


# In-memory sapid → (decision_id, user_id, feature_vector) registry for
# tests + early dev. Production wire reads from Neo4j DecisionTrace via
# sapid lookup. Per directive Section 3.7: "Round-trip rate is monitored
# as a load-bearing operational metric (target: ≥98%)."
_SAPID_REGISTRY: Dict[str, Tuple[str, str, List[float]]] = {}


def register_sapid_for_decision(
    sapid: str,
    decision_id: str,
    user_id: str,
    feature_vector: List[float],
) -> None:
    """Register the sapid → decision linkage at decision time.

    Called by the orchestrator immediately after a SchedulingDecision +
    Spine #6 DecisionTrace are produced; the sapid macro will be
    substituted by StackAdapt at impression-bid time and the sapid
    arrives back via the Pixel API. This linkage table is the round-
    trip anchor.
    """
    _SAPID_REGISTRY[sapid] = (decision_id, user_id, list(feature_vector))


def lookup_sapid(sapid: str) -> Optional[Tuple[str, str, List[float]]]:
    """Look up the (decision_id, user_id, feature_vector) for a sapid.

    Returns None when the sapid is unknown. Unknown sapid is itself an
    operational signal — the round-trip rate metric reads how many
    incoming pixel events fail to resolve a sapid.
    """
    return _SAPID_REGISTRY.get(sapid)


def reset_sapid_registry() -> None:
    """Test-only: clear the in-memory registry."""
    _SAPID_REGISTRY.clear()


def sapid_registry_size() -> int:
    return len(_SAPID_REGISTRY)


# =============================================================================
# Routing — RawPixelEvent → classified OutcomeEvent → Spine #1 update
# =============================================================================


def build_outcome_event(
    raw: RawPixelEvent,
) -> Optional[OutcomeEvent]:
    """Build an OutcomeEvent from a RawPixelEvent.

    Looks up the sapid in the registry to resolve user_id + decision_id.
    Returns None when sapid is unknown — the caller increments the
    "round-trip failure" counter and discards the event (the only
    deterministic linkage is via sapid; without it we cannot route to
    the originating posterior).
    """
    linkage = lookup_sapid(raw.sapid)
    if linkage is None:
        logger.debug(
            "sapid %s not in registry; round-trip failure",
            raw.sapid,
        )
        return None

    decision_id, user_id, _feature_vector = linkage
    outcome_class, diag = classify_pixel_event(raw)

    return OutcomeEvent(
        sapid=raw.sapid,
        outcome_class=outcome_class,
        user_id=user_id,
        decision_id=decision_id,
        occurred_at=raw.occurred_at,
        classification_diagnostic=diag,
    )


def route_outcome_to_posterior(
    outcome: OutcomeEvent,
    posterior: UserPosterior,
    feature_vector: Optional[List[float]] = None,
    outcome_value: float = 1.0,
) -> UserPosterior:
    """Route an OutcomeEvent through Spine #1's BONG update.

    Looks up the feature vector from the sapid registry by default
    (the same vector logged at decision time, ensuring the update is
    against the design vector that produced the served impression).
    Returns the updated UserPosterior.
    """
    if feature_vector is None:
        linkage = lookup_sapid(outcome.sapid)
        if linkage is None:
            raise ValueError(
                f"sapid {outcome.sapid} not in registry; cannot route "
                f"outcome to posterior without feature vector. The "
                f"orchestrator must call register_sapid_for_decision at "
                f"decision time."
            )
        _, _, feature_vector = linkage

    return bong_update_step(
        posterior=posterior,
        feature_vector=feature_vector,
        outcome_value=outcome_value,
        outcome_class=outcome.outcome_class,
    )


__all__ = [
    "DEFAULT_DWELL_ENGAGED_SECONDS",
    "DEFAULT_DWELL_BOUNCED_SECONDS",
    "DEFAULT_SCROLL_ENGAGED_FRACTION",
    "OutcomeEvent",
    "RawPixelEvent",
    "build_outcome_event",
    "classify_pixel_event",
    "lookup_sapid",
    "register_sapid_for_decision",
    "reset_sapid_registry",
    "route_outcome_to_posterior",
    "sapid_registry_size",
]
