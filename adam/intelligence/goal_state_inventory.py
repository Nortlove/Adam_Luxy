# =============================================================================
# Spine #5 substrate — Goal-state inventory (LUXY) + Pydantic schema
# Location: adam/intelligence/goal_state_inventory.py
# =============================================================================
"""LUXY goal-state inventory — substrate for the Spine #5 free-energy scorer.

Closes directive Phase 6 line 1059 ("Goal-state inventory") + Spine #5
line 216 ("12–15 active goal states"). The directive names example
goal states across two passes (line 216 + line 793):

    commute-readiness, expense-management, expense-control,
    comparative-research, social-positioning, status-display,
    time-pressure, time-recovery, trip-planning,
    professional-encounter-preparation, anxiety-reduction, etc.

This slice ships those goal states as a typed inventory with the
attributes the future Spine #5 generative model will produce
posteriors over: posture compatibility, mechanism fulfillment priors,
primary-metaphor frame, and content-keyword markers (as priors for
the offline-trained inference model).

WHY THIS EXISTS — DECISION-TIME CONSUMER
----------------------------------------

Per directive line 216:

    "Goal states are mechanism-adjacent but distinct; they capture
     WHY the user is on that page, not what mechanism would persuade
     them."

The Spine #5 free-energy scorer ships once two pieces are in tree:
  1. THIS INVENTORY (the set of goal states + their attributes), AND
  2. The generative model q(goal_state | a, s, c) and
     p(goal_state | s, c) inferred from page-content and user-state
     embeddings.

Spine #5's KL term is `D_KL(q || p)` — a goal-misalignment penalty
on creative selection. The inventory is the structural set those
distributions are defined over. Without this inventory the directive's
goal states stay informal English in a docstring; this slice makes
them inspectable, queryable, and compose-able.

DECISION-TIME PATH (sibling-slice plumbing):

    page_content + user_state
        ↓ Spine #5 generative model (sibling)
    goal_state posterior over THIS INVENTORY (line 216, ~12-15 states)
        ↓ free-energy scorer
    F(a | s, c) = D_KL(q || p) - π(c) · log p(observation = a | goal)
        ↓ trilateral cascade
    score → score - λ_F · F                       (directive line 521)

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 6 line 1059; Spine #5 line 216 +
    line 793. Goal-state names taken verbatim from the directive
    where possible; LUXY-specific additions (airport_transfer,
    event_logistics, team_coordination, frequent_traveler_loyalty)
    are derived from the LUXY brand intelligence frame (corporate
    black-car). Primary-metaphor inventory (CONTAINMENT, RELIABILITY-
    AS-WEIGHT, FORWARD-MOTION, STATUS-AS-VERTICALITY, TIME-AS-RESOURCE)
    is from directive line 789.

(b) Tests pin: 12–15 inventory size (directive band); every state
    has the required attributes; mechanism_priors keys are in
    MECHANISM_TAXONOMY; posture_compatibility keys are recognized
    posture labels; primary_metaphor is one of LUXY's 5; keyword
    list non-empty; lookup helpers idempotent; Pydantic round-trip
    preserves all fields.

(c) calibration_pending=True. Each goal state's posture_compatibility
    + mechanism_priors are conservative pre-pilot defaults. LUXY
    pilot data + the offline goal-state inference pipeline (Spine
    #5 sibling) will calibrate. A14 flag:
    PHASE_6_GOAL_STATE_INVENTORY_PRIORS_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Generative model q(goal_state | a, s, c) and
      p(goal_state | s, c) per Spine #5 line 216. This slice ships
      the SET; the inference model that produces posteriors over
      the set is Spine #5 territory proper.
    * Free-energy decomposition (KL term + pragmatic term) per
      Spine #5 line 207-210. Composes once the generative model
      ships.
    * Empirical recalibration of posture_compatibility and
      mechanism_priors from pilot data. The current values are
      conservative defaults; pilot outcomes adjust.
    * Cross-vertical generalization. This inventory is LUXY-specific
      (corporate black-car). Other verticals would replace the
      inventory; the GoalState schema is reusable.
    * Neo4j writeback. The :GoalState node schema is documented
      below but no writer is shipped — sibling slice when the
      partner-facing dashboard reads goal-state posteriors.
    * Keyword extraction logic. The `keywords` field carries
      page-content markers as priors; the actual extraction +
      embedding alignment that produces a goal-state posterior is
      Spine #5 territory.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

from adam.intelligence.mechanism_taxonomy import MECHANISM_TAXONOMY
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_VIGILANCE,
)


# =============================================================================
# LUXY primary metaphor inventory (directive line 789)
# =============================================================================


class LUXYPrimaryMetaphor:
    """LUXY's primary-metaphor inventory per directive line 789.

    Constants rather than enum so the values can be stored on
    GoalState as plain strings (Pydantic serializes cleanly).
    """

    CONTAINMENT = "containment"
    """Inside the vehicle as protected space — control, safety, privacy."""

    RELIABILITY_AS_WEIGHT = "reliability_as_weight"
    """Heavy = trustworthy, dependable, substantial."""

    FORWARD_MOTION = "forward_motion"
    """Movement toward goal — progress, momentum."""

    STATUS_AS_VERTICALITY = "status_as_verticality"
    """Up = high status, prestige, premium."""

    TIME_AS_RESOURCE = "time_as_resource"
    """Time as scarce, valuable, recoverable."""


_LUXY_METAPHORS = frozenset({
    LUXYPrimaryMetaphor.CONTAINMENT,
    LUXYPrimaryMetaphor.RELIABILITY_AS_WEIGHT,
    LUXYPrimaryMetaphor.FORWARD_MOTION,
    LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
    LUXYPrimaryMetaphor.TIME_AS_RESOURCE,
})


_RECOGNIZED_POSTURES = frozenset({
    POSTURE_BLEND,
    POSTURE_VIGILANCE,
    POSTURE_NEUTRAL,
})


# =============================================================================
# Pydantic schema
# =============================================================================


class GoalState(BaseModel):
    """One goal state in the inventory.

    Per directive Spine #5 line 216: a goal state captures WHY the
    user is on a page (commute-readiness, expense-management, …),
    NOT what mechanism would persuade them. The mechanism_priors
    field encodes which mechanisms FULFILL the goal — that's the
    partial mapping the generative model uses.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str

    # Which postures align with this goal? Non-zero values mean the
    # goal is plausible-active when the page induces that posture.
    posture_compatibility: Dict[str, float]

    # Which mechanisms FULFILL this goal? Non-zero values mean the
    # mechanism naturally serves this goal (does NOT mean the
    # mechanism gets favored by selection — that's the cascade's job;
    # this is the substrate the Spine #5 generative model reads).
    mechanism_priors: Dict[str, float]

    # LUXY's primary-metaphor frame for creative aligned with this goal.
    # One of LUXYPrimaryMetaphor's 5 constants.
    primary_metaphor: str

    # Page-content keyword markers — priors for the offline goal-state
    # inference model. NOT used at decision time; provided as substrate
    # for the Spine #5 sibling generative-model trainer.
    keywords: List[str] = Field(default_factory=list)

    @field_validator("posture_compatibility")
    @classmethod
    def _posture_keys_recognized(
        cls, v: Dict[str, float],
    ) -> Dict[str, float]:
        for key in v.keys():
            if key not in _RECOGNIZED_POSTURES:
                raise ValueError(
                    f"posture_compatibility key {key!r} not recognized — "
                    f"must be one of {sorted(_RECOGNIZED_POSTURES)}"
                )
        for value in v.values():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"posture_compatibility value must be in [0, 1]; "
                    f"got {value}"
                )
        return v

    @field_validator("mechanism_priors")
    @classmethod
    def _mechanism_keys_in_taxonomy(
        cls, v: Dict[str, float],
    ) -> Dict[str, float]:
        for key in v.keys():
            if key not in MECHANISM_TAXONOMY:
                raise ValueError(
                    f"mechanism_priors key {key!r} not in MECHANISM_TAXONOMY"
                )
        for value in v.values():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"mechanism_priors value must be in [0, 1]; got {value}"
                )
        return v

    @field_validator("primary_metaphor")
    @classmethod
    def _metaphor_recognized(cls, v: str) -> str:
        if v not in _LUXY_METAPHORS:
            raise ValueError(
                f"primary_metaphor {v!r} not in LUXY inventory — "
                f"must be one of {sorted(_LUXY_METAPHORS)}"
            )
        return v


# =============================================================================
# LUXY goal-state inventory (~12-15 per directive Spine #5 line 216)
# =============================================================================
#
# Mechanisms in MECHANISM_TAXONOMY (3db50de):
#   BLEND_COMPATIBLE: automatic_evaluation, wanting_liking_dissociation,
#     evolutionary_motive_activation, linguistic_framing, mimetic_desire,
#     embodied_cognition, temporal_construal
#   VIGILANCE_ACTIVATING: attention_dynamics, identity_construction
#
# All values calibration-pending. A14 flag:
# PHASE_6_GOAL_STATE_INVENTORY_PRIORS_PILOT_PENDING.

_LUXY_GOAL_STATES: Dict[str, GoalState] = {}


def _register(state: GoalState) -> None:
    _LUXY_GOAL_STATES[state.id] = state


# 1. commute_readiness — daily commute prep (directive line 216, 793)
_register(GoalState(
    id="commute_readiness",
    name="Commute readiness",
    description=(
        "User is preparing for or in transit to work / business; "
        "wants reliable, predictable, on-schedule transport."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.7,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.3,
    },
    mechanism_priors={
        "embodied_cognition": 0.7,       # weight / containment grounding
        "temporal_construal": 0.6,       # near-term concrete planning
        "automatic_evaluation": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.RELIABILITY_AS_WEIGHT,
    keywords=["commute", "morning", "office", "work", "schedule",
              "punctual", "office hours"],
))

# 2. airport_transfer — flight-related transit
_register(GoalState(
    id="airport_transfer",
    name="Airport transfer",
    description=(
        "User is heading to or from an airport; flight-aware, "
        "luggage-aware, time-critical with low margin for error."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.5,
        POSTURE_NEUTRAL: 0.6,
        POSTURE_VIGILANCE: 0.6,
    },
    mechanism_priors={
        "temporal_construal": 0.8,       # time-critical, concrete
        "embodied_cognition": 0.6,       # luggage / weight / containment
        "automatic_evaluation": 0.6,
        "linguistic_framing": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.FORWARD_MOTION,
    keywords=["airport", "flight", "luggage", "terminal", "TSA",
              "departure", "arrival", "JFK", "LAX", "LGA", "EWR"],
))

# 3. comparative_research — evaluating options (directive line 216)
_register(GoalState(
    id="comparative_research",
    name="Comparative research",
    description=(
        "User is evaluating black-car alternatives (Uber Black, Lyft "
        "Lux, Carey, Blacklane, Boston Coach); seeking head-to-head "
        "differentiation, pricing transparency, service comparisons."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.2,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.9,           # research = vigilance posture
    },
    mechanism_priors={
        "automatic_evaluation": 0.7,
        "linguistic_framing": 0.7,
        "identity_construction": 0.5,    # vigilance-compatible
        "attention_dynamics": 0.4,       # vigilance-compatible
    },
    primary_metaphor=LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
    keywords=["compare", "vs", "review", "best", "rating", "pricing",
              "alternative", "competitor", "Uber Black", "Carey",
              "Blacklane"],
))

# 4. expense_management — receipts, expense-report-friendly (directive 216)
_register(GoalState(
    id="expense_management",
    name="Expense management",
    description=(
        "User needs receipts, expense-report-friendly options, "
        "corporate billing, Concur/SAP-compatible documentation."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.4,
        POSTURE_NEUTRAL: 0.6,
        POSTURE_VIGILANCE: 0.6,
    },
    mechanism_priors={
        "linguistic_framing": 0.7,
        "automatic_evaluation": 0.6,
        "temporal_construal": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.RELIABILITY_AS_WEIGHT,
    keywords=["expense", "receipt", "Concur", "SAP", "reimburse",
              "billing", "invoice", "T&E", "corporate card",
              "expense report"],
))

# 5. social_positioning — status through transport (directive 216)
_register(GoalState(
    id="social_positioning",
    name="Social positioning",
    description=(
        "User wants the transport choice to signal status to clients "
        "/ peers / superiors. Visible-arrival context dominates."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.5,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.5,
    },
    mechanism_priors={
        "identity_construction": 0.8,
        "evolutionary_motive_activation": 0.6,
        "mimetic_desire": 0.6,
        "attention_dynamics": 0.4,
    },
    primary_metaphor=LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
    keywords=["client meeting", "executive", "VIP", "premium",
              "luxury", "status", "first impression", "make an entrance"],
))

# 6. status_display — visible signal of standing (directive 793)
_register(GoalState(
    id="status_display",
    name="Status display",
    description=(
        "Distinct from social_positioning: the user actively values "
        "the conspicuous-consumption signal of black-car-over-rideshare. "
        "Wants the choice to be SEEN as premium."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.4,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.6,
    },
    mechanism_priors={
        "identity_construction": 0.9,
        "evolutionary_motive_activation": 0.7,
        "mimetic_desire": 0.7,
    },
    primary_metaphor=LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
    keywords=["luxury", "exclusive", "prestige", "elite", "executive",
              "platinum", "concierge", "fleet"],
))

# 7. time_pressure — urgent, time-critical (directive 216)
_register(GoalState(
    id="time_pressure",
    name="Time pressure",
    description=(
        "User is late / running behind / in a deadline-driven moment. "
        "Conscious, vigilance-dominant; minimal patience for friction."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.2,
        POSTURE_NEUTRAL: 0.4,
        POSTURE_VIGILANCE: 0.9,
    },
    mechanism_priors={
        "attention_dynamics": 0.7,
        "automatic_evaluation": 0.7,
        "temporal_construal": 0.7,
    },
    primary_metaphor=LUXYPrimaryMetaphor.TIME_AS_RESOURCE,
    keywords=["urgent", "asap", "now", "late", "delayed", "rush hour",
              "missed", "overdue", "ETA"],
))

# 8. time_recovery — getting back on schedule (directive 793)
_register(GoalState(
    id="time_recovery",
    name="Time recovery",
    description=(
        "User has lost time (delayed flight, traffic, missed meeting) "
        "and is rescheduling / rerouting. Concrete, near-term, "
        "logistics-dense."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.3,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.7,
    },
    mechanism_priors={
        "temporal_construal": 0.8,
        "automatic_evaluation": 0.6,
        "linguistic_framing": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.TIME_AS_RESOURCE,
    keywords=["delayed", "rebook", "reschedule", "next available",
              "alternate", "backup", "fastest"],
))

# 9. trip_planning — future scheduling (directive 216)
_register(GoalState(
    id="trip_planning",
    name="Trip planning",
    description=(
        "User is planning future travel — booking ahead, coordinating "
        "calendar, evaluating options for upcoming trip."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.6,
        POSTURE_NEUTRAL: 0.6,
        POSTURE_VIGILANCE: 0.5,
    },
    mechanism_priors={
        "temporal_construal": 0.6,       # far-term, more abstract
        "linguistic_framing": 0.6,
        "automatic_evaluation": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.FORWARD_MOTION,
    keywords=["upcoming trip", "next week", "next month", "itinerary",
              "calendar", "schedule a ride", "book in advance"],
))

# 10. professional_encounter_preparation — heading to meeting (directive 793)
_register(GoalState(
    id="professional_encounter_preparation",
    name="Professional encounter preparation",
    description=(
        "User is en route to a high-stakes meeting / pitch / interview "
        "/ negotiation. Wants composure, predictability, no surprises."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.6,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.5,
    },
    mechanism_priors={
        "embodied_cognition": 0.7,       # composure / containment
        "automatic_evaluation": 0.6,
        "identity_construction": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.CONTAINMENT,
    keywords=["meeting", "pitch", "interview", "negotiation",
              "presentation", "client", "investor", "boardroom"],
))

# 11. anxiety_reduction — safety / predictability seeking (directive 793)
_register(GoalState(
    id="anxiety_reduction",
    name="Anxiety reduction",
    description=(
        "User is avoiding rideshare — late-night travel, unfamiliar "
        "city, female safety, family member transportation. Predictability "
        "is the dominant value."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.7,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.4,
    },
    mechanism_priors={
        "embodied_cognition": 0.8,       # containment / safe-space
        "automatic_evaluation": 0.7,
        "evolutionary_motive_activation": 0.6,  # safety motive
    },
    primary_metaphor=LUXYPrimaryMetaphor.CONTAINMENT,
    keywords=["safe", "safety", "secure", "professional driver",
              "vetted", "background check", "late night", "alone",
              "trusted", "screened"],
))

# 12. event_logistics — wedding/gala/conference (LUXY-specific)
_register(GoalState(
    id="event_logistics",
    name="Event logistics",
    description=(
        "User is coordinating ground-transport for an event — wedding, "
        "gala, conference, awards ceremony. Often multi-vehicle, "
        "schedule-coordinated, group-aware."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.5,
        POSTURE_NEUTRAL: 0.7,
        POSTURE_VIGILANCE: 0.5,
    },
    mechanism_priors={
        "linguistic_framing": 0.6,
        "temporal_construal": 0.6,
        "identity_construction": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
    keywords=["wedding", "gala", "conference", "event", "ceremony",
              "reception", "venue", "RSVP"],
))

# 13. team_coordination — group logistics (LUXY-specific)
_register(GoalState(
    id="team_coordination",
    name="Team coordination",
    description=(
        "User is coordinating transport for a team — multiple riders, "
        "shared origin or destination, group billing, executive "
        "assistant booking on behalf of group."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.4,
        POSTURE_NEUTRAL: 0.7,
        POSTURE_VIGILANCE: 0.5,
    },
    mechanism_priors={
        "linguistic_framing": 0.7,
        "automatic_evaluation": 0.6,
        "temporal_construal": 0.5,
    },
    primary_metaphor=LUXYPrimaryMetaphor.RELIABILITY_AS_WEIGHT,
    keywords=["team", "group", "executive assistant", "EA", "multiple",
              "fleet", "shared", "split bill", "group booking"],
))

# 14. frequent_traveler_loyalty — repeat-customer engagement (LUXY-specific)
_register(GoalState(
    id="frequent_traveler_loyalty",
    name="Frequent traveler loyalty",
    description=(
        "User is a repeat / high-value customer engaging with loyalty "
        "program features — status tier, points balance, member "
        "benefits, concierge tier."
    ),
    posture_compatibility={
        POSTURE_BLEND: 0.7,
        POSTURE_NEUTRAL: 0.5,
        POSTURE_VIGILANCE: 0.3,
    },
    mechanism_priors={
        "identity_construction": 0.6,
        "mimetic_desire": 0.4,
        "automatic_evaluation": 0.6,
    },
    primary_metaphor=LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
    keywords=["loyalty", "rewards", "points", "tier", "platinum",
              "elite member", "frequent rider", "preferred",
              "status program"],
))


# =============================================================================
# Lookup helpers
# =============================================================================


def get_goal_state(goal_state_id: str) -> Optional[GoalState]:
    """Return the GoalState by id, or None if not found."""
    return _LUXY_GOAL_STATES.get(goal_state_id)


def list_goal_states() -> List[GoalState]:
    """Return all goal states in deterministic id order."""
    return [_LUXY_GOAL_STATES[k] for k in sorted(_LUXY_GOAL_STATES.keys())]


def goal_state_ids() -> List[str]:
    """Return all goal-state ids in sorted order."""
    return sorted(_LUXY_GOAL_STATES.keys())


def goal_states_for_posture(
    posture: str, threshold: float = 0.5,
) -> List[GoalState]:
    """Return goal states whose posture_compatibility[posture] ≥ threshold.

    Used by the Spine #5 generative model (sibling slice) to filter
    the candidate goal-state set by page posture before computing
    the full posterior. Empty list when no states pass the threshold.
    """
    return [
        g for g in list_goal_states()
        if g.posture_compatibility.get(posture, 0.0) >= threshold
    ]


def goal_states_with_metaphor(metaphor: str) -> List[GoalState]:
    """Return goal states using the given primary metaphor."""
    return [
        g for g in list_goal_states()
        if g.primary_metaphor == metaphor
    ]


# =============================================================================
# Slice 12 — Neo4j writeback / reload
# =============================================================================
#
# Schema (idempotent MERGE on goal_state_id):
#
#   (:GoalState {
#       goal_state_id*,                (UNIQUE — MERGE key)
#       name,
#       description,
#       primary_metaphor,
#       posture_compatibility_json,    (serialized dict)
#       mechanism_priors_json,         (serialized dict)
#       keywords_json,                 (serialized list)
#       last_updated_ts
#   })
#
# Nested fields (posture_compatibility, mechanism_priors, keywords) are
# JSON-serialized because Neo4j node properties must be primitive or
# arrays of primitive — nested maps aren't supported. Tests pin the
# round-trip preserves the typed shape.


_GOAL_STATE_NODE_LABEL = "GoalState"


_PERSIST_GOAL_STATE_CYPHER: str = (
    "MERGE (g:" + _GOAL_STATE_NODE_LABEL + " {goal_state_id: $goal_state_id}) "
    "SET g.name = $name, "
    "    g.description = $description, "
    "    g.primary_metaphor = $primary_metaphor, "
    "    g.posture_compatibility_json = $posture_compatibility_json, "
    "    g.mechanism_priors_json = $mechanism_priors_json, "
    "    g.keywords_json = $keywords_json, "
    "    g.last_updated_ts = $last_updated_ts"
)


_LOAD_GOAL_STATE_CYPHER: str = (
    "MATCH (g:" + _GOAL_STATE_NODE_LABEL + " {goal_state_id: $goal_state_id}) "
    "RETURN g.goal_state_id AS goal_state_id, "
    "       g.name AS name, "
    "       g.description AS description, "
    "       g.primary_metaphor AS primary_metaphor, "
    "       g.posture_compatibility_json AS posture_compatibility_json, "
    "       g.mechanism_priors_json AS mechanism_priors_json, "
    "       g.keywords_json AS keywords_json "
    "LIMIT 1"
)


_LOAD_ALL_GOAL_STATES_CYPHER: str = (
    "MATCH (g:" + _GOAL_STATE_NODE_LABEL + ") "
    "RETURN g.goal_state_id AS goal_state_id, "
    "       g.name AS name, "
    "       g.description AS description, "
    "       g.primary_metaphor AS primary_metaphor, "
    "       g.posture_compatibility_json AS posture_compatibility_json, "
    "       g.mechanism_priors_json AS mechanism_priors_json, "
    "       g.keywords_json AS keywords_json"
)


def _state_to_cypher_params(state: GoalState) -> Dict[str, Any]:
    """Serialize nested fields for Neo4j primitives-only constraint."""
    return {
        "goal_state_id": state.id,
        "name": state.name,
        "description": state.description,
        "primary_metaphor": state.primary_metaphor,
        "posture_compatibility_json": json.dumps(state.posture_compatibility),
        "mechanism_priors_json": json.dumps(state.mechanism_priors),
        "keywords_json": json.dumps(list(state.keywords)),
        "last_updated_ts": time.time(),
    }


def _record_to_state(record: Any) -> Optional[GoalState]:
    """Reconstruct GoalState from a cypher record. Returns None on
    parse failure (logged at WARNING)."""
    try:
        posture = json.loads(
            record.get("posture_compatibility_json") or "{}"
        )
        priors = json.loads(record.get("mechanism_priors_json") or "{}")
        keywords = json.loads(record.get("keywords_json") or "[]")
        return GoalState(
            id=str(record.get("goal_state_id")),
            name=str(record.get("name") or ""),
            description=str(record.get("description") or ""),
            primary_metaphor=str(record.get("primary_metaphor") or ""),
            posture_compatibility=posture,
            mechanism_priors=priors,
            keywords=list(keywords),
        )
    except Exception as exc:
        logger.warning(
            "GoalState parse failed for goal_state_id=%s: %s",
            record.get("goal_state_id"), exc,
        )
        return None


async def write_goal_state_to_neo4j(
    state: GoalState,
    driver: Optional[Any],
) -> bool:
    """Persist one GoalState to Neo4j. Idempotent (MERGE on id).

    Returns True on success. Soft-fails (returns False) when:
      - driver is None
      - cypher session raises

    Bid path / decision path NEVER block on this — the inventory is
    static substrate; writeback is a one-time seed (or refresh when
    inventory is updated upstream).
    """
    if driver is None:
        return False

    try:
        async with driver.session() as session:
            await session.run(
                _PERSIST_GOAL_STATE_CYPHER,
                **_state_to_cypher_params(state),
            )
        return True
    except Exception as exc:
        logger.warning(
            "write_goal_state_to_neo4j failed for goal_state_id=%s: %s",
            state.id, exc,
        )
        return False


async def write_all_goal_states_to_neo4j(
    driver: Optional[Any],
) -> int:
    """Bulk-write the entire LUXY inventory. Returns count successfully
    written. Soft-fails to 0 when driver unavailable.

    Use case: deploy-time seed of the :GoalState nodes so the partner
    surface (Spine #5 sibling) can read inventory without re-loading
    the Python module.
    """
    if driver is None:
        return 0

    written = 0
    for state in list_goal_states():
        if await write_goal_state_to_neo4j(state, driver):
            written += 1

    if written:
        logger.info(
            "GoalState inventory writeback: %d states persisted", written,
        )
    return written


async def load_goal_state_from_neo4j(
    goal_state_id: str,
    driver: Optional[Any],
) -> Optional[GoalState]:
    """Fetch one GoalState by id. Returns None on missing / failure."""
    if driver is None or not goal_state_id:
        return None

    try:
        async with driver.session() as session:
            result = await session.run(
                _LOAD_GOAL_STATE_CYPHER,
                goal_state_id=goal_state_id,
            )
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "load_goal_state_from_neo4j failed for id=%s: %s",
            goal_state_id, exc,
        )
        return None

    if record is None:
        return None
    return _record_to_state(record)


async def load_all_goal_states_from_neo4j(
    driver: Optional[Any],
) -> List[GoalState]:
    """Fetch all :GoalState nodes. Returns [] when driver unavailable
    or no nodes exist."""
    if driver is None:
        return []

    states: List[GoalState] = []
    try:
        async with driver.session() as session:
            result = await session.run(_LOAD_ALL_GOAL_STATES_CYPHER)
            async for record in result:
                state = _record_to_state(record)
                if state is not None:
                    states.append(state)
    except Exception as exc:
        logger.warning(
            "load_all_goal_states_from_neo4j failed: %s", exc,
        )
        return []

    return states
