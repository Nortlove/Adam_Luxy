# =============================================================================
# ADAM Atom Input/Output Models
# Location: adam/atoms/models/atom_io.py
# =============================================================================

"""
ATOM INPUT/OUTPUT MODELS

Standard contracts for atom inputs and outputs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.atoms.models.evidence import FusionResult, MultiSourceEvidence
from adam.blackboard.models.zone1_context import RequestContext
from adam.blackboard.models.zone2_reasoning import AtomReasoningSpace, AtomType


# =============================================================================
# ATOM CONFIGURATION
# =============================================================================

class AtomTier(str, Enum):
    """Execution tier for atoms."""
    
    FAST = "fast"           # No Claude, cache/graph only
    STANDARD = "standard"   # May use Claude
    REASONING = "reasoning"  # Always uses Claude for synthesis


class AtomConfig(BaseModel):
    """Configuration for an atom."""
    
    atom_id: str
    atom_type: AtomType
    atom_name: str
    
    # Execution
    tier: AtomTier = Field(default=AtomTier.STANDARD)
    max_latency_ms: int = Field(default=500, ge=0)
    
    # Sources to query
    required_sources: List[str] = Field(default_factory=list)
    optional_sources: List[str] = Field(default_factory=list)
    
    # Claude configuration
    use_claude_for_fusion: bool = Field(default=True)
    claude_model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=1024, ge=0)
    
    # Caching
    enable_caching: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=300, ge=0)
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list)


# =============================================================================
# ATOM INPUT
# =============================================================================

class AtomInput(BaseModel):
    """
    Standard input for all atoms.
    
    Contains request context and any upstream atom outputs.
    """
    
    input_id: str = Field(
        default_factory=lambda: f"in_{uuid4().hex[:12]}"
    )
    
    # Request identification
    request_id: str
    user_id: str
    
    # Zone 1 context
    request_context: RequestContext
    
    # Upstream atom outputs (from dependencies)
    upstream_outputs: Dict[str, "AtomOutput"] = Field(default_factory=dict)
    
    # Pre-fetched evidence (optional, for optimization)
    pre_fetched_evidence: Optional[MultiSourceEvidence] = None

    # Psychological intelligence context — populated by intelligence prefetch
    # before DAG execution. Contains graph-derived data that atoms access via
    # PsychologicalConstructResolver and DSPDataAccessor.
    ad_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Pre-fetched psychological intelligence from Neo4j graph, "
            "corpus priors, and DSP enrichment. Keys: graph_type_inference, "
            "expanded_customer_type, dimensional_priors, ndf_intelligence, "
            "graph_mechanism_priors, dsp_graph_intelligence, "
            "corpus_fusion_intelligence."
        ),
    )

    # Buyer uncertainty profile (for information-value-aware reasoning)
    buyer_uncertainty: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Per-dimension uncertainty (variance, confidence) from BuyerUncertaintyProfile",
    )

    # Gradient field (which dimensions matter most for this archetype×category)
    gradient_field: Optional[Dict[str, float]] = Field(
        default=None,
        description="Gradient magnitudes per dimension from pre-computed gradient field",
    )

    # Execution hints
    latency_budget_ms: int = Field(default=500, ge=0)
    skip_claude: bool = Field(default=False)
    
    # Debug
    debug_mode: bool = Field(default=False)
    
    def get_upstream(self, atom_id: str) -> Optional["AtomOutput"]:
        """Get output from an upstream atom."""
        return self.upstream_outputs.get(atom_id)


# =============================================================================
# ATOM OUTPUT
# =============================================================================

class AtomOutput(BaseModel):
    """
    Standard output from all atoms.
    
    Contains the fusion result and any construct-specific outputs.
    """
    
    output_id: str = Field(
        default_factory=lambda: f"out_{uuid4().hex[:12]}"
    )
    
    # Atom identification
    atom_id: str
    atom_type: AtomType
    request_id: str
    
    # Fusion result (main output)
    fusion_result: FusionResult
    
    # Construct-specific outputs
    primary_assessment: str = ""
    assessment_value: Optional[float] = None
    secondary_assessments: Dict[str, Any] = Field(default_factory=dict)
    
    # Recommendations (for downstream atoms)
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_weights: Dict[str, float] = Field(default_factory=dict)
    
    # State inferences
    inferred_states: Dict[str, float] = Field(default_factory=dict)
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Evidence package (for downstream access)
    evidence_package: Optional[MultiSourceEvidence] = None
    
    # Execution metrics
    total_latency_ms: float = Field(default=0.0, ge=0.0)
    sources_queried: int = Field(default=0, ge=0)
    claude_used: bool = Field(default=False)
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)
    
    # Timestamp
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# ATOM EXECUTION RESULT
# =============================================================================

class AtomExecutionStatus(str, Enum):
    """Status of atom execution."""
    
    SUCCESS = "success"
    PARTIAL = "partial"  # Completed with degraded quality
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class AtomExecutionResult(BaseModel):
    """
    Complete result of atom execution including metadata.
    """
    
    # Status
    status: AtomExecutionStatus
    
    # Output (if successful)
    output: Optional[AtomOutput] = None
    
    # Error (if failed)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    duration_ms: float = Field(default=0.0, ge=0.0)
    
    # Resource usage
    claude_tokens_in: int = Field(default=0, ge=0)
    claude_tokens_out: int = Field(default=0, ge=0)
    neo4j_queries: int = Field(default=0, ge=0)
    cache_hits: int = Field(default=0, ge=0)
    cache_misses: int = Field(default=0, ge=0)
    
    # Learning signals emitted
    signals_emitted: int = Field(default=0, ge=0)
