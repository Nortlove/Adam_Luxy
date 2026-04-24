"""RecommendationClass — the central primitive of ADAM's pilot adjudication.

A RecommendationClass is a structured causal hypothesis identified by the tuple
(advertiser, archetype, mechanism, context_posture_band, horizon_band). Every
recommendation ADAM emits is an instance of a class. Each class carries a
track record across firings: a pre-registered ProjectedImpact before observation,
a realized distribution after horizon completion, and a residual-divergence
decomposition that feeds back into the Inferential Learning Agent.

Theoretical substrate (ADAM_THEORETICAL_FOUNDATION.md §2.5, §4.3; project
memory project_weakness_4_recommendation_class_primitive.md):

- Reinforcement is selection at three time-scales (Bargh/Pinker/Dawkins).
- The inferential chain from archetype through mechanism through context to
  outcome is the load-bearing primitive, not individual effectiveness scores.
- Selection is amoral — the fitness function ADAM's learning loop designs
  determines the evolutionary pressure on every upstream component.
- Theory fidelity (predicted matches realized, within plant-model tolerance,
  with known biases accounted) is the adjudication question, not
  treatment-effect significance.

Phase of this package:
  Slice 1 (this commit): ProjectedImpact structured predicate — the data
  model every pre-registered claim carries. Not yet wired to the cascade.
  Subsequent slices: RecommendationClass node + Neo4j schema, HB latent-
  class archetype compression, SCM-native inferential chain on graph,
  git-commit pre-registration log.
"""

from adam.intelligence.recommendation_class.graph import (
    RecommendationClassGraph,
    RecommendationClassIdentity,
    claim_node_id,
    get_recommendation_class_graph,
    recommendation_class_id,
)
from adam.intelligence.recommendation_class.projected_impact import (
    AudienceScope,
    AudienceSummary,
    CompetingActivations,
    GoalFulfillmentOutcome,
    PrimingCondition,
    ProjectedImpact,
    SpiesDistribution,
    canonical_hash,
)

__all__ = [
    "AudienceScope",
    "AudienceSummary",
    "CompetingActivations",
    "GoalFulfillmentOutcome",
    "PrimingCondition",
    "ProjectedImpact",
    "RecommendationClassGraph",
    "RecommendationClassIdentity",
    "SpiesDistribution",
    "canonical_hash",
    "claim_node_id",
    "get_recommendation_class_graph",
    "recommendation_class_id",
]
