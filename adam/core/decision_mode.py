"""
Decision Mode — Epistemic Status of Intelligence Produced by ADAM
==================================================================

Every decision ADAM produces has an epistemic status: either the reasoning
chain is grounded in evidence (full inference), incomplete (some links
grounded, others missing), or refused (no grounding at all, no decision
produced).

Why this exists
---------------
In a correlational system, degraded output is a weaker estimate of the same
thing. In an inferential system, a broken chain is not a weaker version of
an unbroken chain — it is a categorically different object. A chain with a
fabricated construct value is a "number with no referent"; it does not
correspond to any measured property of the user or context, yet it is
indistinguishable from a grounded number unless the system explicitly marks
it. If the learning loop consumes such outputs as real, it trains on
fabrications and becomes confidently wrong.

This module defines the three-state epistemic typing and the structural
gate that prevents ungrounded decisions from contaminating the learning
loop.

The three states
----------------
- GROUNDED   — every load-bearing link in the reasoning chain is backed by
               real evidence (bilateral edge evidence present, at least one
               construct assessment from a real atom run, theoretical link
               traversal successful). The learning loop may update posteriors
               from outcomes associated with this decision.

- INCOMPLETE — at least one load-bearing link is missing grounding. The
               decision may still be useful for response (a partial chain is
               often better than nothing from the user's perspective) but the
               learning loop MUST NOT update posteriors from outcomes
               associated with this decision, because the outcome cannot be
               cleanly credited to the links that were assessed — some of
               the causal contribution came from links the system did not
               measure. Causal observation may still record the outcome for
               later analysis.

- REFUSED    — too many load-bearing links are missing for a decision to be
               produced at all. No response, no learning, Prometheus counter
               incremented, diagnostic logged.

Discrete states vs. continuous grounding
----------------------------------------
The three-state typing is a stepping stone. The underlying reality is
continuous — binding affinities, even in biochemistry, are "digital but in
truth between digital and analog" (partial agonists, allosteric modulators,
cooperativity). A future refinement will replace the discrete states with a
probabilistic grounding score and a continuous gating function. The shape
of this module is designed so that replacement is local: consumers read
`DecisionMode` from `derive_mode(evidence)`, so when `derive_mode` gains a
probability gradient, the consumers do not change.

Load-bearing links
------------------
For the initial implementation, the three load-bearing links are:

1. `bilateral_edge_evidence_present` — L3 bilateral cascade produced real
   edge evidence (not a fallback to L1 archetype prior or L2 category
   posterior alone).

2. `atom_run_real` — at least one atom in the DAG was executed against real
   intelligence sources (the prefetch populated sources, Neo4j was
   reachable, the blackboard carried real data). An atom that ran with all
   0.5 defaults does not count as a real atom run.

3. `theoretical_link_traversed` — the theoretical graph traversal that
   connects construct assessments to mechanism recommendations succeeded
   (TheoryLearner lookup returned a chain, not an empty result).

Future refinement will add more links — page-context grounding, buyer
profile freshness, gradient-field validity — and may transition the per-link
booleans to per-link confidence scores. `GroundingEvidence.as_dict()` and
`derive_mode()` are the only two functions consumers need to be aware of,
and both will be backwards-compatible through the refinement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class DecisionMode(str, Enum):
    """Epistemic status of an ADAM decision.

    str-enum so it serializes cleanly to JSON and survives the webhook +
    cache + Neo4j round trip.
    """

    GROUNDED = "grounded"
    INCOMPLETE = "incomplete"
    REFUSED = "refused"


@dataclass
class GroundingEvidence:
    """Structural per-link test results for the reasoning chain.

    Each field is a yes/no claim about whether a specific load-bearing link
    in the chain has real evidence behind it. The mode is derived from the
    combination via `derive_mode`; consumers should not read individual
    fields except for diagnostics.

    Add fields here as the grounding criteria expand. Do not add scalars —
    if a new criterion is scalar, bucket it into a boolean at this layer so
    `derive_mode` stays structural. The probabilistic future will replace
    the dataclass wholesale; individual scalar fields will make that
    transition more painful.

    PATH-AWARE GROUNDING: ADAM has two production decision paths today
    that produce different evidence shapes:
      - "campaign_orchestrator": runs the bilateral cascade AND the
        30-atom DAG AND theoretical-link traversal. All 3 links are
        meaningful; GROUNDED requires all 3.
      - "stackadapt_creative_intelligence": runs only the bilateral
        cascade (the atoms are dead code on this path per the audit).
        atom_run_real is N/A; GROUNDED is determined by cascade_level
        and edge_count, NOT by the 3-link count.

    The `decision_path` field disambiguates so derive_mode applies the
    correct gate for each. Producers MUST set decision_path; legacy
    callers default to "campaign_orchestrator" for backwards compat.
    """

    # L3 bilateral cascade produced real edge evidence. False when the
    # cascade fell back to L1/L2 priors alone or raised an exception.
    bilateral_edge_evidence_present: bool = False

    # At least one atom ran against real intelligence (Neo4j reachable,
    # prefetch populated, blackboard carrying real data). False when all
    # atoms resolved to 0.5 defaults or when the AtomDAG execution raised
    # an exception.
    #
    # On the stackadapt_creative_intelligence path this is N/A (the
    # atoms are dead code per the audit). decision_path == "stackadapt_
    # creative_intelligence" callers should leave this False; derive_mode
    # ignores it for that path.
    atom_run_real: bool = False

    # TheoryLearner or equivalent theoretical graph traversal successful.
    # False when the traversal returned empty or raised.
    theoretical_link_traversed: bool = False

    # Path-aware grounding: which decision path produced this evidence.
    # derive_mode uses this to apply the correct gate.
    decision_path: str = "campaign_orchestrator"

    # Cascade level the producer reached. Meaningful for the
    # stackadapt_creative_intelligence path:
    #   0 → cascade returned no usable result (REFUSED)
    #   1 → archetype prior only
    #   2 → archetype + category posterior
    #   3 → bilateral edges (the GROUNDED threshold for this path)
    #   4 → inferential transfer (also GROUNDED)
    cascade_level: int = 0

    # L3 edge evidence count. Meaningful for stackadapt_creative_
    # intelligence: GROUNDED requires cascade_level >= 3 AND edge_count
    # >= some threshold (cfg.l3_min_edge_count, surfaced here as the
    # producer's threshold result).
    edge_count: int = 0

    # Diagnostic list of which links failed and why. Populated by producers
    # to help operators debug infrastructure failures that are degrading
    # the mode rate in production.
    failure_reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        """Return a serializable dict of the structural tests.

        Excludes the diagnostic `failure_reasons` list so the result is a
        clean per-link view. Use `as_full_dict` to include diagnostics.
        """
        return {
            "bilateral_edge_evidence_present": self.bilateral_edge_evidence_present,
            "atom_run_real": self.atom_run_real,
            "theoretical_link_traversed": self.theoretical_link_traversed,
            "decision_path": self.decision_path,
            "cascade_level": self.cascade_level,
            "edge_count": self.edge_count,
        }

    def as_full_dict(self) -> Dict[str, object]:
        """Return a full serializable view including diagnostics."""
        return {
            **self.as_dict(),
            "failure_reasons": list(self.failure_reasons),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, object]) -> "GroundingEvidence":
        """Reconstruct from a dict, tolerating missing keys.

        Legacy dicts (without decision_path / cascade_level / edge_count)
        default to campaign_orchestrator path with zero scalars — same
        behavior as before this typed-evidence shipped. New consumers
        will see explicit fields.
        """
        return cls(
            bilateral_edge_evidence_present=bool(d.get("bilateral_edge_evidence_present", False)),
            atom_run_real=bool(d.get("atom_run_real", False)),
            theoretical_link_traversed=bool(d.get("theoretical_link_traversed", False)),
            decision_path=str(d.get("decision_path", "campaign_orchestrator")),
            cascade_level=int(d.get("cascade_level", 0) or 0),
            edge_count=int(d.get("edge_count", 0) or 0),
            failure_reasons=list(d.get("failure_reasons", []) or []),
        )

    @property
    def missing_links(self) -> List[str]:
        """Return the names of load-bearing links that are not grounded."""
        missing = []
        if not self.bilateral_edge_evidence_present:
            missing.append("bilateral_edge_evidence_present")
        if not self.atom_run_real:
            missing.append("atom_run_real")
        if not self.theoretical_link_traversed:
            missing.append("theoretical_link_traversed")
        return missing

    @property
    def grounded_count(self) -> int:
        """Return how many load-bearing links are grounded (0-3 initially)."""
        return sum(
            1
            for present in (
                self.bilateral_edge_evidence_present,
                self.atom_run_real,
                self.theoretical_link_traversed,
            )
            if present
        )


def derive_mode(evidence: GroundingEvidence) -> DecisionMode:
    """Derive the epistemic status from the structural grounding evidence.

    Path-aware: each production decision path has its own grounding
    criteria because different paths produce different evidence shapes.

    stackadapt_creative_intelligence path (cascade-only, no atom DAG):
        - cascade_level == 0 → REFUSED (cascade returned no usable result)
        - cascade_level >= 3 AND bilateral_edge_evidence_present → GROUNDED
          (real L3 edge evidence backs the decision)
        - otherwise → INCOMPLETE (only L1/L2 priors; the cascade fell back)

    campaign_orchestrator path (cascade + atom DAG + theoretical traversal):
        - All three load-bearing links grounded → GROUNDED
        - At least one link grounded but not all → INCOMPLETE
        - No links grounded → REFUSED

    The campaign_orchestrator gate is intentionally strict (3-of-3) — its
    decisions traverse three independent reasoning sources, and crediting
    a posterior when one source is missing imports correlational error.
    The stackadapt_creative_intelligence gate is single-source by
    architecture; the bilateral cascade IS the reasoning chain on that
    path, so the gate is L3-with-edges, not 3-of-3.
    """
    if evidence.decision_path == "stackadapt_creative_intelligence":
        if evidence.cascade_level == 0:
            return DecisionMode.REFUSED
        if (
            evidence.cascade_level >= 3
            and evidence.bilateral_edge_evidence_present
        ):
            return DecisionMode.GROUNDED
        return DecisionMode.INCOMPLETE

    # campaign_orchestrator path (default)
    grounded = evidence.grounded_count
    if grounded == 3:
        return DecisionMode.GROUNDED
    if grounded == 0:
        return DecisionMode.REFUSED
    return DecisionMode.INCOMPLETE


# =============================================================================
# LEARNING-LOOP GATING POLICY
# =============================================================================


def should_update_posteriors(mode: DecisionMode) -> bool:
    """Structural gate — should the learning loop update posteriors for this decision?

    GROUNDED decisions produce trustworthy outcomes for credit assignment.
    INCOMPLETE decisions cannot be cleanly credited (the outcome is a mix
    of the links that were measured and the links that were not — crediting
    the measured links alone is exactly the correlational trap ADAM is built
    to avoid). REFUSED decisions never happened, so there is nothing to
    learn from.
    """
    return mode == DecisionMode.GROUNDED


def should_record_causal_observation(mode: DecisionMode) -> bool:
    """Causal observation is useful even for INCOMPLETE decisions.

    It does not credit any posterior. It records the full decision context
    and outcome so offline analysis can later ask: "do incomplete-chain
    decisions have any predictive value we could mine?" Answering that
    question requires keeping the records; it does not require crediting
    posteriors online.

    REFUSED decisions did not produce a response, so there is no causal
    observation to record.
    """
    return mode in (DecisionMode.GROUNDED, DecisionMode.INCOMPLETE)


def learning_gate_reason(mode: DecisionMode) -> str:
    """Human-readable reason for the learning-loop gate decision.

    Used in structured logs and the learning-loop update results so operators
    can see at a glance why a given outcome was or was not applied to the
    posteriors.
    """
    if mode == DecisionMode.GROUNDED:
        return "grounded_chain_posterior_update_authorized"
    if mode == DecisionMode.INCOMPLETE:
        return "incomplete_chain_posterior_update_refused_causal_observation_recorded"
    return "refused_decision_no_outcome_to_learn_from"


# =============================================================================
# METADATA SERIALIZATION — for the decision cache and outcome handler
# =============================================================================

DECISION_MODE_METADATA_KEY = "decision_mode"
GROUNDING_EVIDENCE_METADATA_KEY = "grounding_evidence"


def to_outcome_metadata(
    mode: DecisionMode,
    evidence: GroundingEvidence,
) -> Dict[str, object]:
    """Serialize the mode + evidence into the metadata dict that flows
    through decision cache → webhook → outcome handler.

    The keys are string constants (exported above) so consumers that cannot
    import this module — e.g., the webhook receiver in a different process
    — can still read the fields without a circular dependency.
    """
    return {
        DECISION_MODE_METADATA_KEY: mode.value,
        GROUNDING_EVIDENCE_METADATA_KEY: evidence.as_full_dict(),
    }


def from_outcome_metadata(
    metadata: Dict[str, object],
) -> tuple[DecisionMode, GroundingEvidence]:
    """Reconstruct mode + evidence from the metadata dict.

    Tolerant of missing fields: a metadata dict produced by an older
    version of the orchestrator (before this module existed) will yield
    GROUNDED + all-false evidence, which is the legacy-compatible default.
    The outcome handler should treat legacy decisions as GROUNDED for
    backwards compatibility, but new code paths should always populate the
    fields explicitly.
    """
    mode_str = metadata.get(DECISION_MODE_METADATA_KEY, DecisionMode.GROUNDED.value)
    try:
        mode = DecisionMode(mode_str)
    except ValueError:
        mode = DecisionMode.GROUNDED

    evidence_dict = metadata.get(GROUNDING_EVIDENCE_METADATA_KEY) or {}
    if isinstance(evidence_dict, dict):
        evidence = GroundingEvidence.from_dict(evidence_dict)
    else:
        evidence = GroundingEvidence()

    return mode, evidence


# =============================================================================
# CONVENIENCE CONSTRUCTORS FOR COMMON FAILURE MODES
# =============================================================================


def refused_evidence(reason: str) -> GroundingEvidence:
    """Build a fully-refused GroundingEvidence with a diagnostic reason."""
    return GroundingEvidence(
        bilateral_edge_evidence_present=False,
        atom_run_real=False,
        theoretical_link_traversed=False,
        failure_reasons=[reason],
    )


def partial_evidence(
    bilateral: bool,
    atom_real: bool,
    theoretical: bool,
    reasons: Optional[List[str]] = None,
) -> GroundingEvidence:
    """Build a GroundingEvidence from explicit booleans with optional diagnostics."""
    return GroundingEvidence(
        bilateral_edge_evidence_present=bilateral,
        atom_run_real=atom_real,
        theoretical_link_traversed=theoretical,
        failure_reasons=list(reasons or []),
    )
