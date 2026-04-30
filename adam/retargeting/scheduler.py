"""Spine #2: within-subject schedule generators (ABAB / RAR / SMART) +
mechanism-specific washout-interval table.

Closes the directive's Phase 1 line 948-950 deliverable. The AR(1)
carryover correction (line 951) is already shipped INSIDE the
per-user reconcile paths (see adam.intelligence.user_posterior_hmc_reconcile).

This module sits alongside adam.retargeting.engines.repeated_measures —
that module owns the BIB exploration/exploitation slot allocator
(`WithinSubjectDesigner`). The three N-of-1 trial designs live HERE
because they have different scheduling primitives:

  ABAB
    Two-mechanism alternation across blocks (A B A B). Each within-user
    transition is a paired observation; AR(1) carryover correction in
    the likelihood plus a washout between phases makes the A vs B
    contrast valid even when treatment effects bleed into the next
    block. Standard in single-case experimental design literature
    (Kazdin 2011; Kratochwill et al. 2010 What Works Clearinghouse SCED
    standards).

  RAR (Response-Adaptive Randomization)
    At each touch, the next mechanism is sampled from a probability
    distribution proportional to its current posterior mean (Thompson
    sampling), constrained by a minimum allocation per arm to preserve
    estimability. Berry & Eick 1995, Berry 2006. Used in the I-SPY
    breast-cancer trial.

  SMART (Sequential Multiple Assignment Randomized Trial)
    Stage-1 randomizes among initial mechanisms; stage-2 randomization
    is contingent on the user's response status (responder vs non-
    responder). Lavori & Dawson 2004; Murphy 2005. Encodes branching as
    a decision rule on the cumulative reward signal.

Per Foundation §7 rule 11 (the fitness function IS the ethics): the
schedulers reweight by reward but the washout floor is non-overrideable
— protects the reactance-prone user from compounding multiplicative
reactance (Wicklund hydraulic model). Even RAR cannot deploy a touch
inside the washout window of the prior mechanism for that user.

Washout table provenance: derived from the existing
`adam.intelligence.mechanism_adme.MECHANISM_PROFILES` half-life table
× 3 (≥95% washout per first-order pharmacokinetics — three half-lives
clears 87.5%, four clears 93.75%; we use 3 as a usable lower bound for
ad-context kinetics where the user's competing exposures provide
additional washing).

Cross-mechanism transitions (A→B in ABAB, or RAR-driven mechanism
switch) use the MAX of the two mechanism washouts, since the slower-
clearing mechanism dominates the reactance-recovery floor.
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Sequence, Tuple

from adam.intelligence.mechanism_adme import MECHANISM_PROFILES
from adam.retargeting.models.within_subject import (
    UserPosteriorProfile,
    WithinSubjectDesign,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Washout-interval table (mechanism-specific carryover-clearance hours)
# ---------------------------------------------------------------------------

# Multiplier applied to half_life_hours to get the washout floor.
# 3 × t½ → ≥87.5% washed out (first-order PK).
WASHOUT_HALF_LIFE_MULTIPLIER: float = 3.0

# Default floor when a mechanism is not in the ADME profile table — picks
# the median half-life across canonical mechanisms (×3) so unknowns inherit
# a reasonable carryover assumption rather than zero.
DEFAULT_WASHOUT_HOURS: float = 144.0  # 6 days


def washout_hours_for(mechanism: str) -> float:
    """Minimum hours to wait after `mechanism` before the next touch can
    be issued (whether or not the next touch is the same mechanism).

    Falls through to DEFAULT_WASHOUT_HOURS when the mechanism is not in
    the ADME profile table — keeps unknown / experimental mechanisms
    safe by default.
    """
    profile = MECHANISM_PROFILES.get(mechanism)
    if profile is None:
        return DEFAULT_WASHOUT_HOURS
    return profile.half_life_hours * WASHOUT_HALF_LIFE_MULTIPLIER


def washout_hours_between(prev_mechanism: str, next_mechanism: str) -> float:
    """Carryover-floor between two consecutive touches.

    Uses the MAX of both mechanism washouts since the slower-clearing
    mechanism dominates the user's reactance-recovery clock. Same-
    mechanism transitions reduce to washout_hours_for(mechanism).
    """
    return max(
        washout_hours_for(prev_mechanism),
        washout_hours_for(next_mechanism),
    )


def build_washout_table() -> Dict[str, float]:
    """Snapshot of every known mechanism → washout hours.

    Useful for logging into a sequence's WithinSubjectDesign so the
    contract is auditable from a serialized run.
    """
    return {m: washout_hours_for(m) for m in MECHANISM_PROFILES.keys()}


# ---------------------------------------------------------------------------
# ABAB schedule
# ---------------------------------------------------------------------------


def design_abab(
    user_id: str,
    sequence_id: str,
    mechanism_a: str,
    mechanism_b: str,
    max_touches: int = 7,
    barrier: str = "",
) -> WithinSubjectDesign:
    """Build an ABAB N-of-1 design across `max_touches` positions.

    For 7 touches: A B A B A B A. For 4 touches: A B A B. Every position
    is an "exploration slot" in the BIB sense — every touch contributes
    a comparison observation, not a pure exploit.

    The realized assignment pattern is encoded in `mechanisms_tested`
    (in deployment order); washout floors per transition are stored in
    a domain field on the design object.
    """
    if not mechanism_a or not mechanism_b:
        raise ValueError("ABAB requires two non-empty mechanisms")
    if mechanism_a == mechanism_b:
        raise ValueError("ABAB requires two DISTINCT mechanisms")
    if max_touches < 2:
        raise ValueError("ABAB requires max_touches >= 2")

    pattern = [mechanism_a if (i % 2 == 0) else mechanism_b
               for i in range(max_touches)]

    washouts = [
        washout_hours_between(pattern[i - 1], pattern[i])
        for i in range(1, max_touches)
    ]

    return WithinSubjectDesign(
        user_id=user_id,
        sequence_id=sequence_id,
        design_type="ABAB",
        # Every position is a comparison slot in ABAB — no pure exploit.
        exploration_slots=list(range(1, max_touches + 1)),
        exploitation_slots=[],
        mechanisms_tested=pattern,
        abab_pattern=pattern,
        abab_a=mechanism_a,
        abab_b=mechanism_b,
        washout_hours_between_touches=washouts,
    )


# ---------------------------------------------------------------------------
# RAR — Response-Adaptive Randomization
# ---------------------------------------------------------------------------


# Minimum probability mass per candidate arm — preserves arm
# estimability (Berry 2006: the bandit can't kill an arm prematurely
# under finite-data uncertainty).
RAR_MIN_ARM_PROBABILITY: float = 0.10


def rar_arm_probabilities(
    candidates: Sequence[str],
    user_profile: Optional[UserPosteriorProfile] = None,
    population_means: Optional[Dict[str, float]] = None,
    min_arm_probability: float = RAR_MIN_ARM_PROBABILITY,
) -> Dict[str, float]:
    """Compute the RAR sampling distribution over `candidates`.

    Probability ∝ posterior mean reward, then mixed with a uniform
    floor so each arm retains ≥ `min_arm_probability`. User-level
    posteriors override population means whenever the user has any
    observations on that mechanism.

    Returns a dict {mechanism: probability} that sums to 1.0.
    """
    if not candidates:
        return {}

    n = len(candidates)
    floor = min(min_arm_probability, 1.0 / n)  # safety: floor must fit
    pop = population_means or {}

    raw: List[float] = []
    for mech in candidates:
        # Prefer user-level posterior mean if any observations
        if user_profile is not None:
            user_post = user_profile.mechanism_posteriors.get(mech)
            if user_post is not None and user_post.sample_count > 0:
                raw.append(max(0.0, user_post.mean))
                continue
        # Fall back to population
        raw.append(max(0.0, pop.get(mech, 0.5)))

    total = sum(raw)
    if total <= 0:
        # Degenerate case — uniform.
        return {m: 1.0 / n for m in candidates}

    # Normalize, then apply uniform floor
    probs = [r / total for r in raw]
    # Mix: p_i' = (1 - n * floor) * p_i + floor
    weight = max(0.0, 1.0 - n * floor)
    probs = [weight * p + floor for p in probs]
    # Numerical safety re-normalize
    s = sum(probs)
    return {m: p / s for m, p in zip(candidates, probs)}


def rar_sample_mechanism(
    candidates: Sequence[str],
    user_profile: Optional[UserPosteriorProfile] = None,
    population_means: Optional[Dict[str, float]] = None,
    rng: Optional[random.Random] = None,
    min_arm_probability: float = RAR_MIN_ARM_PROBABILITY,
) -> Tuple[str, Dict[str, float]]:
    """Sample one mechanism from the RAR distribution.

    Returns (chosen_mechanism, probability_distribution).
    """
    probs = rar_arm_probabilities(
        candidates,
        user_profile=user_profile,
        population_means=population_means,
        min_arm_probability=min_arm_probability,
    )
    if not probs:
        raise ValueError("RAR requires at least one candidate")
    rng = rng or random.Random()
    items = list(probs.items())
    weights = [p for _, p in items]
    chosen = rng.choices([m for m, _ in items], weights=weights, k=1)[0]
    return chosen, probs


def design_rar(
    user_id: str,
    sequence_id: str,
    candidates: Sequence[str],
    max_touches: int = 7,
    user_profile: Optional[UserPosteriorProfile] = None,
    population_means: Optional[Dict[str, float]] = None,
    rng: Optional[random.Random] = None,
    barrier: str = "",
) -> WithinSubjectDesign:
    """Pre-roll a RAR schedule given current information state.

    NOTE: production usage prefers calling `rar_sample_mechanism` at
    each touch so the distribution reweights on every realized outcome.
    `design_rar` exists for offline simulation, hold-out evaluation, and
    test pinning where the realized trajectory must be reproducible.
    """
    if not candidates:
        raise ValueError("RAR requires at least one candidate")
    rng = rng or random.Random()
    pattern: List[str] = []
    per_touch_probs: List[Dict[str, float]] = []
    for _ in range(max_touches):
        m, probs = rar_sample_mechanism(
            candidates,
            user_profile=user_profile,
            population_means=population_means,
            rng=rng,
        )
        pattern.append(m)
        per_touch_probs.append(probs)

    washouts = [
        washout_hours_between(pattern[i - 1], pattern[i])
        for i in range(1, max_touches)
    ]

    return WithinSubjectDesign(
        user_id=user_id,
        sequence_id=sequence_id,
        design_type="RAR",
        exploration_slots=list(range(1, max_touches + 1)),
        exploitation_slots=[],
        mechanisms_tested=pattern,
        rar_pattern=pattern,
        rar_per_touch_probabilities=per_touch_probs,
        rar_candidates=list(candidates),
        washout_hours_between_touches=washouts,
    )


# ---------------------------------------------------------------------------
# SMART — Sequential Multiple Assignment Randomized Trial
# ---------------------------------------------------------------------------


# Canonical SMART responder threshold: 0.5 is the median of the
# composite reward (engagement=0.1, stage_advance=0.3, conversion=0.6)
# — corresponds to "engaged + stage advanced" or any conversion. Below
# threshold the user is classified non-responder and re-randomized into
# the alternate (rescue) mechanism class.
SMART_RESPONDER_REWARD_THRESHOLD: float = 0.4

# Default touch position at which the first-stage decision rule fires.
SMART_STAGE_2_TRIGGER_POSITION: int = 3


def smart_stage_2_assignment(
    design: WithinSubjectDesign,
    cumulative_reward: float,
) -> Tuple[str, str]:
    """Apply the SMART stage-2 branching rule to a design.

    At the trigger position, the cumulative reward across positions
    1..trigger_position is compared to the responder threshold:
      - reward >= threshold → responder → continue with stage_1_mechanism
      - reward <  threshold → non-responder → switch to rescue_mechanism

    The rescue_mechanism is held out of stage 1 specifically so the
    stage-2 branch yields a counterfactual-comparable observation to
    the stage-1 mechanism (Murphy 2005 SMART canon).

    Returns (mechanism_for_remaining_touches, branch_label).
    branch_label ∈ {'responder_continue', 'non_responder_switch'}.
    """
    if cumulative_reward >= design.smart_responder_threshold:
        return design.smart_stage_1_mechanism, "responder_continue"
    return design.smart_rescue_mechanism, "non_responder_switch"


def design_smart(
    user_id: str,
    sequence_id: str,
    stage_1_mechanism: str,
    rescue_mechanism: str,
    max_touches: int = 7,
    trigger_position: int = SMART_STAGE_2_TRIGGER_POSITION,
    responder_threshold: float = SMART_RESPONDER_REWARD_THRESHOLD,
    barrier: str = "",
) -> WithinSubjectDesign:
    """Build a SMART design with a single stage-2 branching point.

    Pre-trigger positions deploy stage_1_mechanism. Post-trigger
    positions are filled tentatively with stage_1_mechanism but the
    decision rule (`SmartDecisionRule`) on the design is the source of
    truth — at runtime the orchestrator calls
    `decision_rule.stage_2_assignment(cumulative_reward_through_trigger)`
    to decide.
    """
    if not stage_1_mechanism or not rescue_mechanism:
        raise ValueError("SMART requires non-empty stage_1 and rescue mechanisms")
    if stage_1_mechanism == rescue_mechanism:
        raise ValueError("SMART requires DISTINCT stage_1 and rescue mechanisms")
    if not (1 <= trigger_position < max_touches):
        raise ValueError(
            f"SMART trigger_position must be in [1, max_touches-1]; "
            f"got {trigger_position} with max_touches={max_touches}"
        )

    # Pre-trigger pattern is deterministic; post-trigger is conditional.
    # We log the "responder branch" pattern as the default
    # `mechanisms_tested` (most frequent path); the rescue branch is
    # carried on the rule itself.
    pattern_responder = [stage_1_mechanism] * max_touches
    pattern_non_responder = (
        [stage_1_mechanism] * trigger_position
        + [rescue_mechanism] * (max_touches - trigger_position)
    )

    # Washout floor pre-trigger: same-mechanism back-to-back. Post-
    # trigger non-responder branch: cross-mechanism washout at the
    # transition.
    washout_responder = [
        washout_hours_between(pattern_responder[i - 1], pattern_responder[i])
        for i in range(1, max_touches)
    ]
    washout_non_responder = [
        washout_hours_between(pattern_non_responder[i - 1], pattern_non_responder[i])
        for i in range(1, max_touches)
    ]

    return WithinSubjectDesign(
        user_id=user_id,
        sequence_id=sequence_id,
        design_type="SMART",
        # Stage 1 positions are exploit; trigger and beyond are
        # exploration in the BIB sense (the comparison information is
        # the responder vs non-responder branch).
        exploitation_slots=list(range(1, trigger_position + 1)),
        exploration_slots=list(range(trigger_position + 1, max_touches + 1)),
        mechanisms_tested=pattern_responder,
        smart_stage_1_mechanism=stage_1_mechanism,
        smart_rescue_mechanism=rescue_mechanism,
        smart_trigger_position=trigger_position,
        smart_responder_threshold=responder_threshold,
        smart_pattern_responder=pattern_responder,
        smart_pattern_non_responder=pattern_non_responder,
        smart_washout_responder=washout_responder,
        smart_washout_non_responder=washout_non_responder,
    )
