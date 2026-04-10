# =============================================================================
# Causal Structure Learner from Interventional Data
# Location: adam/intelligence/causal_structure_learner.py
# Unified System Evolution Directive, Section 6
# =============================================================================

"""
Learns causal structure between alignment dimensions from the system's
own interventional data. Every mechanism deployment is a soft intervention
on specific dimensions — observing which OTHER dimensions shift reveals
causal relationships no correlational analysis can provide.

Processes EnrichedInterventionRecords with diagnostic hypothesis weighting:
- H1 (wrong page) outcomes → weak mechanism evidence, strong page evidence
- H2 (wrong mechanism) outcomes → strong mechanism evidence
- H3-H5 outcomes → moderate evidence

Runs as a BATCH process (nightly or weekly). Not real-time.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EdgeDirection(str, Enum):
    FORWARD = "forward"
    REVERSE = "reverse"
    NONE = "none"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class CausalEdgeEvidence:
    """Evidence for a causal edge between two alignment dimensions."""

    dim_a: str
    dim_b: str

    interventions_on_a: int = 0
    b_shifted_given_a: int = 0
    interventions_on_b: int = 0
    a_shifted_given_b: int = 0

    log_odds_forward: float = 0.0
    log_odds_reverse: float = 0.0

    @property
    def direction_posterior(self) -> Dict[str, float]:
        scores = {
            "forward": self.log_odds_forward,
            "reverse": self.log_odds_reverse,
            "none": 0.0,
        }
        max_score = max(scores.values())
        exp_scores = {k: np.exp(v - max_score) for k, v in scores.items()}
        total = sum(exp_scores.values())
        return {k: round(v / total, 4) for k, v in exp_scores.items()}

    @property
    def most_likely_direction(self) -> EdgeDirection:
        posterior = self.direction_posterior
        best = max(posterior, key=posterior.get)
        return EdgeDirection(best)

    @property
    def confidence(self) -> float:
        return max(self.direction_posterior.values())

    @property
    def total_observations(self) -> int:
        return self.interventions_on_a + self.interventions_on_b


class CausalStructureLearner:
    """Learns causal structure from interventional data.

    Core idea: when we intervene on dimension A (via mechanism) and observe
    dimension B shift, that's evidence for A → B. When we intervene on B
    and A does NOT shift, that rules out B → A.

    Processes EnrichedInterventionRecords with hypothesis-aware weighting.
    """

    SHIFT_THRESHOLD = 0.03

    # Evidence strength modulation by diagnostic hypothesis
    # H1 (wrong page): mechanism evidence is weak
    # H2 (wrong mechanism): mechanism evidence is strong
    HYPOTHESIS_WEIGHTS = {
        "H1_wrong_page_mindstate": 0.3,
        "H2_wrong_mechanism": 1.0,
        "H3_wrong_stage_match": 0.7,
        "H4_pkm_reactance": 0.5,
        "H5_ad_fatigue": 0.2,
        "first_touch": 0.8,
        "": 0.5,
    }

    def __init__(self, dimension_names: List[str]):
        self.dimensions = dimension_names
        self._dim_index = {name: i for i, name in enumerate(dimension_names)}
        self.edges: Dict[Tuple[str, str], CausalEdgeEvidence] = {}
        for i, a in enumerate(dimension_names):
            for j, b in enumerate(dimension_names):
                if i < j:
                    self.edges[(a, b)] = CausalEdgeEvidence(dim_a=a, dim_b=b)
        self.total_records_processed = 0

    def process_record(self, record: Dict):
        """Process one EnrichedInterventionRecord (as dict)."""
        targeted = set(record.get("shifted_dimensions", []))
        shift_mags = record.get("shift_magnitudes", {})
        primary_hyp = record.get("primary_hypothesis", "")
        hyp_weight = self.HYPOTHESIS_WEIGHTS.get(primary_hyp, 0.5)

        # Determine which dimensions were targeted by the mechanism
        mechanism_targets = set(record.get("secondary_dimensions_targeted", {}).keys())
        barrier_dim = record.get("barrier_diagnosed", "")
        if barrier_dim:
            mechanism_targets.add(barrier_dim)

        # All shifted dimensions (from pre/post state comparison)
        shifted = set()
        for dim, mag in shift_mags.items():
            if abs(mag) > self.SHIFT_THRESHOLD:
                shifted.add(dim)

        # Update edge evidence
        evidence_increment = 0.1 * hyp_weight
        evidence_decrement = 0.02 * hyp_weight

        for (a, b), evidence in self.edges.items():
            a_targeted = a in mechanism_targets
            b_targeted = b in mechanism_targets
            a_shifted = a in shifted
            b_shifted = b in shifted

            if a_targeted and not b_targeted:
                evidence.interventions_on_a += 1
                if b_shifted:
                    evidence.b_shifted_given_a += 1
                    evidence.log_odds_forward += evidence_increment
                else:
                    evidence.log_odds_forward -= evidence_decrement

            if b_targeted and not a_targeted:
                evidence.interventions_on_b += 1
                if a_shifted:
                    evidence.a_shifted_given_b += 1
                    evidence.log_odds_reverse += evidence_increment
                else:
                    evidence.log_odds_reverse -= evidence_decrement

        self.total_records_processed += 1

    def process_batch(self, records: List[Dict]):
        """Process a batch of records."""
        for record in records:
            self.process_record(record)

    def get_discovered_graph(
        self, confidence_threshold: float = 0.7,
    ) -> Dict[str, List[Tuple[str, float]]]:
        """Return discovered causal graph as adjacency list."""
        graph = {dim: [] for dim in self.dimensions}
        for (a, b), evidence in self.edges.items():
            if evidence.total_observations < 10:
                continue
            direction = evidence.most_likely_direction
            conf = evidence.confidence
            if conf < confidence_threshold:
                continue
            if direction == EdgeDirection.FORWARD:
                graph[a].append((b, conf))
            elif direction == EdgeDirection.REVERSE:
                graph[b].append((a, conf))
            elif direction == EdgeDirection.BIDIRECTIONAL:
                graph[a].append((b, conf))
                graph[b].append((a, conf))
        return graph

    def validate_theory_link(self, cause_dim: str, effect_dim: str) -> Dict:
        """Check whether a theoretical causal link is supported by data."""
        key = tuple(sorted([cause_dim, effect_dim]))
        if key not in self.edges:
            return {"error": f"No edge data for {cause_dim} - {effect_dim}"}

        evidence = self.edges[key]
        data_direction = evidence.most_likely_direction

        theory_is_forward = key[0] == cause_dim
        if theory_is_forward:
            supported = data_direction in (EdgeDirection.FORWARD, EdgeDirection.BIDIRECTIONAL)
            interventions = evidence.interventions_on_a
            shift_rate = (
                evidence.b_shifted_given_a / max(evidence.interventions_on_a, 1)
            )
        else:
            supported = data_direction in (EdgeDirection.REVERSE, EdgeDirection.BIDIRECTIONAL)
            interventions = evidence.interventions_on_b
            shift_rate = (
                evidence.a_shifted_given_b / max(evidence.interventions_on_b, 1)
            )

        return {
            "theory_direction": f"{cause_dim} -> {effect_dim}",
            "data_direction": data_direction.value,
            "data_confidence": evidence.confidence,
            "interventions_on_cause": interventions,
            "effect_shifted_rate": round(shift_rate, 3),
            "supported": supported,
            "total_observations": evidence.total_observations,
        }

    @property
    def stats(self) -> Dict:
        total_edges = sum(
            1 for e in self.edges.values()
            if e.total_observations >= 10 and e.confidence > 0.6
        )
        return {
            "records_processed": self.total_records_processed,
            "dimension_pairs": len(self.edges),
            "edges_with_signal": total_edges,
        }
