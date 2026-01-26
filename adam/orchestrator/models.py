# =============================================================================
# ADAM Orchestrator Models
# Location: adam/orchestrator/models.py
# =============================================================================

"""
Data models for the Campaign Orchestrator.

These models capture the full reasoning trace of ADAM's decision process,
providing visibility into what the system did and why.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # Forward references handled by Pydantic


# =============================================================================
# DATA SOURCE TRACKING
# =============================================================================

class DataSourceType(str, Enum):
    """Types of data sources ADAM uses."""
    PRODUCT_REVIEWS = "product_reviews"
    PRODUCT_DATABASE = "product_database"
    NEO4J_GRAPH = "neo4j_graph"
    USER_INPUT = "user_input"
    BEHAVIORAL_SIGNALS = "behavioral_signals"
    CACHED_INTELLIGENCE = "cached_intelligence"


class DataSourceInfo(BaseModel):
    """Information about a data source used in analysis."""
    source_type: DataSourceType
    source_name: str
    records_retrieved: int = 0
    query_time_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    sample_data: Optional[Dict[str, Any]] = None


# =============================================================================
# GRAPH INTELLIGENCE
# =============================================================================

class MechanismEdge(BaseModel):
    """An edge relationship between mechanisms."""
    target_mechanism: str
    relationship_type: str  # SYNERGIZES_WITH, ANTAGONIZES, etc.
    strength: float = 0.0
    context: Optional[str] = None


class MechanismIntelligence(BaseModel):
    """Intelligence about a cognitive mechanism from the graph."""
    mechanism_name: str
    mechanism_id: str
    description: Optional[str] = None
    
    # Effectiveness for different archetypes
    archetype_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Relationships with other mechanisms
    synergies: List[MechanismEdge] = Field(default_factory=list)
    antagonisms: List[MechanismEdge] = Field(default_factory=list)
    
    # Optimal conditions
    optimal_construal_level: Optional[str] = None  # "high" or "low"
    optimal_regulatory_focus: Optional[str] = None  # "promotion" or "prevention"


class ArchetypeIntelligence(BaseModel):
    """Intelligence about a buyer archetype from the graph."""
    archetype_name: str
    archetype_id: str
    description: Optional[str] = None
    
    # Psychological traits
    personality_profile: Dict[str, float] = Field(default_factory=dict)
    regulatory_focus: str = "balanced"  # promotion, prevention, balanced
    
    # Mechanism effectiveness
    mechanism_responses: Dict[str, float] = Field(default_factory=dict)
    
    # Language preferences
    preferred_tone: Optional[str] = None
    preferred_framing: Optional[str] = None


class GraphQueryResult(BaseModel):
    """Result of a Neo4j graph query."""
    query_name: str
    query_type: str  # mechanism, archetype, synergy, etc.
    cypher_query: Optional[str] = None  # For debugging/visibility
    execution_time_ms: float = 0.0
    nodes_returned: int = 0
    edges_returned: int = 0
    
    # Actual data returned
    mechanisms: List[MechanismIntelligence] = Field(default_factory=list)
    archetypes: List[ArchetypeIntelligence] = Field(default_factory=list)
    
    # Raw result for custom queries
    raw_result: Optional[Dict[str, Any]] = None


# =============================================================================
# ATOM EXECUTION
# =============================================================================

class EvidenceItem(BaseModel):
    """A piece of evidence used by an atom."""
    source: str
    construct: str
    value: float
    confidence: float
    raw_data: Optional[Dict[str, Any]] = None


class AtomExecutionResult(BaseModel):
    """Result of executing a single atom."""
    atom_name: str
    atom_type: str
    execution_time_ms: float = 0.0
    
    # What the atom determined
    primary_output: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    
    # Evidence used
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    
    # Reasoning explanation
    reasoning: Optional[str] = None


class AtomDAGResult(BaseModel):
    """Result of executing the full AtomDAG."""
    execution_order: List[str] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0
    
    # Individual atom results
    atom_results: Dict[str, AtomExecutionResult] = Field(default_factory=dict)
    
    # Aggregated outputs
    final_psychological_profile: Dict[str, Any] = Field(default_factory=dict)
    final_mechanism_activations: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# MECHANISM SELECTION
# =============================================================================

class ThompsonSamplingTrace(BaseModel):
    """Trace of Thompson Sampling decision process."""
    mechanism: str
    prior_alpha: float
    prior_beta: float
    sampled_value: float
    rank: int


class MechanismSelectionResult(BaseModel):
    """Result of mechanism selection via MetaLearner."""
    selected_mechanisms: List[str] = Field(default_factory=list)
    selection_method: str = "thompson_sampling"
    
    # Thompson Sampling details
    sampling_traces: List[ThompsonSamplingTrace] = Field(default_factory=list)
    
    # Final scores
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Priors used
    priors_source: str = "cold_start"  # cold_start, review_intelligence, behavioral
    review_intelligence_applied: bool = False


# =============================================================================
# SEGMENT RECOMMENDATIONS
# =============================================================================

class SegmentRecommendation(BaseModel):
    """A customer segment recommendation."""
    segment_id: str
    segment_name: str
    archetype: str
    
    # Match quality
    match_score: float
    match_explanation: str
    
    # Psychological profile
    personality_traits: Dict[str, float] = Field(default_factory=dict)
    regulatory_focus: Dict[str, float] = Field(default_factory=dict)
    
    # Persuasion strategy
    primary_mechanism: str
    secondary_mechanisms: List[str] = Field(default_factory=list)
    mechanism_explanation: str
    
    # Messaging recommendations
    recommended_tone: str
    recommended_frame: str  # gain, loss-avoidance
    example_hook: str
    
    # Evidence source
    evidence_source: str  # "review_analysis", "graph_inference", "cold_start"
    confidence: float


class StationRecommendation(BaseModel):
    """A station/daypart recommendation."""
    station_format: str
    station_description: str
    recommendation_reason: str
    
    # Match quality
    listener_profile_match: float
    peak_receptivity_score: float
    
    # Timing
    best_dayparts: List[str] = Field(default_factory=list)
    daypart_explanations: Dict[str, str] = Field(default_factory=dict)
    
    # Expected performance
    expected_engagement: str
    confidence_level: float


# =============================================================================
# FULL REASONING TRACE
# =============================================================================

class ReasoningTrace(BaseModel):
    """
    Complete reasoning trace showing how ADAM made its decisions.
    
    This provides full visibility into the system's intelligence for:
    - Demo presentations (showing ADAM's power)
    - Monitoring (ensuring system is working correctly)
    - Debugging (finding issues)
    - Learning (improving the system)
    """
    
    # Metadata
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_processing_time_ms: float = 0.0
    
    # Data sources used
    data_sources: List[DataSourceInfo] = Field(default_factory=list)
    
    # Review intelligence (if product URL provided)
    review_intelligence_summary: Optional[Dict[str, Any]] = None
    
    # Graph queries executed
    graph_queries: List[GraphQueryResult] = Field(default_factory=list)
    
    # Atom execution
    atom_dag_result: Optional[AtomDAGResult] = None
    
    # Mechanism selection
    mechanism_selection: Optional[MechanismSelectionResult] = None
    
    # Key decisions made
    key_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Warnings or issues
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# FINAL CAMPAIGN ANALYSIS RESULT
# =============================================================================

class CampaignAnalysisResult(BaseModel):
    """
    Complete result of campaign analysis.
    
    Contains both the recommendations AND the full reasoning trace
    showing how ADAM arrived at those recommendations.
    """
    
    # Request info
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Input echoed back
    brand: str
    product: str
    description: str
    call_to_action: str
    product_url: Optional[str] = None
    
    # Core recommendations
    customer_segments: List[SegmentRecommendation] = Field(default_factory=list)
    station_recommendations: List[StationRecommendation] = Field(default_factory=list)
    
    # Messaging recommendations
    primary_mechanism: str
    secondary_mechanisms: List[str] = Field(default_factory=list)
    recommended_tone: str
    recommended_frame: str
    example_copy: Optional[str] = None
    
    # Customer language (from reviews)
    customer_language: Dict[str, Any] = Field(default_factory=dict)
    
    # Confidence
    overall_confidence: float = 0.0
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # Full reasoning trace (for demo/monitoring)
    reasoning_trace: Optional[ReasoningTrace] = None
    
    # Processing info
    processing_time_ms: float = 0.0
    components_used: List[str] = Field(default_factory=list)
    
    # Channel recommendations (iHeart integration)
    channel_recommendations: Optional["ChannelIntelligenceResult"] = None


# =============================================================================
# CHANNEL INTELLIGENCE (iHeart Integration)
# =============================================================================

class EmotionMatch(BaseModel):
    """An emotion evoked by a show matching target profile."""
    emotion_name: str
    intensity: float = 0.0
    valence: float = 0.0  # -1 to 1
    arousal: float = 0.0  # 0 to 1


class TraitMatch(BaseModel):
    """A personality trait attracted by a show."""
    trait_name: str
    correlation: float = 0.0
    dimension: Optional[str] = None  # Big Five dimension


class PersuasionMatch(BaseModel):
    """A persuasion technique receptivity score."""
    technique_name: str
    effectiveness: float = 0.0
    principle: Optional[str] = None


class TimeSlotMatch(BaseModel):
    """A time slot with attention and receptivity scores."""
    slot_name: str
    hours: str
    attention_level: float = 0.0
    typical_mood: Optional[str] = None
    persuasion_score: float = 0.0
    reasoning: str = ""


class ShowMatch(BaseModel):
    """A show/podcast matching the target psychological profile."""
    show_name: str
    show_id: Optional[str] = None
    show_description: str = ""
    show_type: str = "show"  # show, podcast, station
    
    # Parent entities
    station_name: Optional[str] = None
    station_format: Optional[str] = None
    network: Optional[str] = None
    
    # Timing
    air_time: Optional[str] = None
    days: Optional[str] = None
    
    # Psychological profile scores
    emotion_score: float = 0.0
    trait_score: float = 0.0
    mindset_score: float = 0.0
    persuasion_score: float = 0.0
    total_score: float = 0.0
    
    # Matched dimensions
    matched_emotions: List[EmotionMatch] = Field(default_factory=list)
    matched_traits: List[TraitMatch] = Field(default_factory=list)
    matched_persuasion: List[PersuasionMatch] = Field(default_factory=list)
    
    # Optimal time slots
    optimal_time_slots: List[TimeSlotMatch] = Field(default_factory=list)
    
    # Reasoning
    match_reasoning: str = ""
    synergy_explanation: str = ""
    
    # Learning metadata
    selection_confidence: float = 0.0
    evidence_sources: List[str] = Field(default_factory=list)


class ShowPsycholinguisticProfile(BaseModel):
    """Complete psycholinguistic profile for a show."""
    show_name: str
    show_description: str = ""
    
    # STATE dimension
    evoked_emotions: List[EmotionMatch] = Field(default_factory=list)
    created_mindsets: List[Dict[str, Any]] = Field(default_factory=list)
    
    # BEHAVIOR dimension
    triggered_behaviors: List[Dict[str, Any]] = Field(default_factory=list)
    induced_urges: List[Dict[str, Any]] = Field(default_factory=list)
    
    # TRAITS dimension
    attracted_traits: List[TraitMatch] = Field(default_factory=list)
    cognitive_styles: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Persuasion receptivity
    persuasion_receptivity: List[PersuasionMatch] = Field(default_factory=list)
    
    # Timing
    time_slots: List[str] = Field(default_factory=list)


class ChannelIntelligenceResult(BaseModel):
    """
    Complete channel intelligence result.
    
    Contains recommended shows/podcasts with full psychological
    reasoning and synergy analysis.
    """
    
    # Top recommended shows
    recommended_shows: List[ShowMatch] = Field(default_factory=list)
    
    # Top recommended podcasts
    recommended_podcasts: List[ShowMatch] = Field(default_factory=list)
    
    # Station recommendations
    recommended_stations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Optimal time slots across all channels
    optimal_time_slots: List[TimeSlotMatch] = Field(default_factory=list)
    
    # Persuasion technique recommendations per channel type
    persuasion_by_channel: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Overall reasoning
    channel_selection_reasoning: str = ""
    synergy_analysis: str = ""
    
    # Query metadata
    query_time_ms: float = 0.0
    shows_evaluated: int = 0
    
    # Learning signals
    selection_method: str = "psycholinguistic_matching"
    confidence_score: float = 0.0
    learning_feedback_enabled: bool = True
