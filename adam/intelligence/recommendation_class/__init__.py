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

Package status (2026-04-25):
  Weeks 1-2: CLT recalibration + page-intelligence salvage + attentional_posture.
  Weeks 3-4: #4 RecommendationClass scaffolding — ProjectedImpact predicate,
    RecommendationClassGraph Neo4j entity, pre-registration file convention,
    archetype compression, inferential-chain SCM substrate.
  Weeks 5-7: #4 plant model — PlantModel (predicted SPIES distribution with
    CLT-recalibrated priors, single-level shrinkage, bias-flag population),
    SequentialSchedule (O'Brien-Fleming interim looks), ConformalCoverage
    (split-conformal marginal guarantee), Adjudicator (partition + residual-
    divergence decomposition + parameterization sensitivity).
  Weeks 8-9: Adjudicator evidence-trace + inferential-chain attribution
    full population.
"""

from adam.intelligence.recommendation_class.a14_compromises import (
    A14Compromise,
    ACTIVE_COMPROMISES,
    COUNTER_REGULATION_UNTRACKED,
    DEPTH_PRIOR_UNVALIDATED,
    SINGLE_LEVEL_SHRINKAGE,
    VARIATIONAL_POSTERIOR_APPROXIMATION,
    format_for_report as format_a14_compromises_for_report,
)
from adam.intelligence.recommendation_class.chain_attribution import (
    ChainEdge,
    ChainEdgeRelType,
    ChainReader,
    attribute_residual,
    compute_link_id,
    make_chain_reader,
)
from adam.intelligence.recommendation_class.processing_depth_priors import (
    ATTENTION_ROUTE_DEPTHS,
    AUTOPILOT_ROUTE_DEPTHS,
    NON_CONVERTING_DEPTHS,
    VALID_POSTURE_BANDS,
    expected_depth_distribution,
    expected_route_fractions,
    normalize_depth_counts_to_distribution,
    route_split_from_counts,
)
from adam.intelligence.recommendation_class.adjudicator import (
    Adjudicator,
    AdjudicatorOutput,
    DEFAULT_BIAS_MAGNITUDES,
    EvidenceTrace,
    ParameterizationSensitivity,
    Partition,
    RealizedOutcomes,
    ResidualDivergence,
    RouteSplitResidual,
)
from adam.intelligence.recommendation_class.archetype_compression import (
    ArchetypeCompressionResult,
    ArchetypeCompressor,
    DEFAULT_COVARIANCE_TYPE,
    DEFAULT_DIRICHLET_CONCENTRATION,
    DEFAULT_EFFECTIVE_WEIGHT_THRESHOLD,
    DEFAULT_MAX_COMPONENTS,
    DEFAULT_MIN_OBSERVATIONS,
    DEFAULT_SEED,
    PosteriorFamily,
)
from adam.intelligence.recommendation_class.conformal import (
    ConformalCoverage,
    ConformalInterval,
    DEFAULT_ALPHA as DEFAULT_CONFORMAL_ALPHA,
    DEFAULT_MIN_CALIBRATION_SIZE,
)
from adam.intelligence.recommendation_class.graph import (
    RecommendationClassGraph,
    RecommendationClassIdentity,
    claim_node_id,
    get_recommendation_class_graph,
    recommendation_class_id,
)
from adam.intelligence.recommendation_class.inferential_chain import (
    ActivatesEdge,
    InferentialChainGraph,
    PsychologicalConstructUpsert,
    ReceptivityEdge,
    RequiresEdge,
    get_inferential_chain_graph,
)
from adam.intelligence.recommendation_class.plant_model import (
    DEFAULT_CONVERSION_RATE_BIN_EDGES,
    DEFAULT_INDUSTRY_PRIOR_CONCENTRATION,
    DEFAULT_INDUSTRY_PRIOR_RATE,
    PlantModel,
    PlantModelInputs,
)
from adam.intelligence.recommendation_class.pre_registration import (
    current_git_head,
    pre_registration_path,
    pre_registration_root,
    read_pre_registration,
    write_pre_registration,
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
from adam.intelligence.recommendation_class.sequential_schedule import (
    DEFAULT_ALPHA as DEFAULT_SEQUENTIAL_ALPHA,
    DEFAULT_N_LOOKS,
    InterimDecision,
    InterimLookResult,
    LookSchedule,
    SequentialAdjudicator,
)

__all__ = [
    "ACTIVE_COMPROMISES",
    "ATTENTION_ROUTE_DEPTHS",
    "AUTOPILOT_ROUTE_DEPTHS",
    "ActivatesEdge",
    "Adjudicator",
    "AdjudicatorOutput",
    "ArchetypeCompressionResult",
    "ArchetypeCompressor",
    "AudienceScope",
    "AudienceSummary",
    "A14Compromise",
    "COUNTER_REGULATION_UNTRACKED",
    "ChainEdge",
    "ChainEdgeRelType",
    "ChainReader",
    "CompetingActivations",
    "ConformalCoverage",
    "ConformalInterval",
    "DEFAULT_BIAS_MAGNITUDES",
    "DEPTH_PRIOR_UNVALIDATED",
    "DEFAULT_CONFORMAL_ALPHA",
    "DEFAULT_CONVERSION_RATE_BIN_EDGES",
    "DEFAULT_COVARIANCE_TYPE",
    "DEFAULT_DIRICHLET_CONCENTRATION",
    "DEFAULT_EFFECTIVE_WEIGHT_THRESHOLD",
    "DEFAULT_INDUSTRY_PRIOR_CONCENTRATION",
    "DEFAULT_INDUSTRY_PRIOR_RATE",
    "DEFAULT_MAX_COMPONENTS",
    "DEFAULT_MIN_CALIBRATION_SIZE",
    "DEFAULT_MIN_OBSERVATIONS",
    "DEFAULT_N_LOOKS",
    "DEFAULT_SEED",
    "DEFAULT_SEQUENTIAL_ALPHA",
    "EvidenceTrace",
    "GoalFulfillmentOutcome",
    "InferentialChainGraph",
    "InterimDecision",
    "InterimLookResult",
    "LookSchedule",
    "NON_CONVERTING_DEPTHS",
    "ParameterizationSensitivity",
    "Partition",
    "PlantModel",
    "PlantModelInputs",
    "PosteriorFamily",
    "PrimingCondition",
    "ProjectedImpact",
    "PsychologicalConstructUpsert",
    "RealizedOutcomes",
    "ReceptivityEdge",
    "RecommendationClassGraph",
    "RecommendationClassIdentity",
    "RequiresEdge",
    "ResidualDivergence",
    "RouteSplitResidual",
    "SINGLE_LEVEL_SHRINKAGE",
    "SequentialAdjudicator",
    "SpiesDistribution",
    "VALID_POSTURE_BANDS",
    "VARIATIONAL_POSTERIOR_APPROXIMATION",
    "attribute_residual",
    "compute_link_id",
    "expected_depth_distribution",
    "expected_route_fractions",
    "canonical_hash",
    "claim_node_id",
    "current_git_head",
    "format_a14_compromises_for_report",
    "get_inferential_chain_graph",
    "get_recommendation_class_graph",
    "make_chain_reader",
    "normalize_depth_counts_to_distribution",
    "route_split_from_counts",
    "pre_registration_path",
    "pre_registration_root",
    "read_pre_registration",
    "recommendation_class_id",
    "write_pre_registration",
]
