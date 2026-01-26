# =============================================================================
# ADAM Behavioral Analytics: LangGraph Workflow Nodes
# Location: adam/behavioral_analytics/workflow_nodes.py
# =============================================================================

"""
LANGGRAPH WORKFLOW NODES

Nodes for integrating behavioral analytics into the LangGraph decision workflow.

Workflow Integration:
1. collect_implicit_signals - Collect and process implicit signals
2. infer_psychological_state - Infer psychological state from signals
3. query_behavioral_knowledge - Get relevant knowledge for context
4. record_for_hypothesis_testing - Record signals for hypothesis testing
5. apply_behavioral_context - Apply context to atom reasoning
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from adam.behavioral_analytics.engine import (
    BehavioralAnalyticsEngine,
    PsychologicalInference,
    get_behavioral_analytics_engine,
)
from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    DeviceType,
    SignalDomain,
)
from adam.behavioral_analytics.models.mechanisms import (
    CognitiveMechanism,
    UserMechanismProfile,
)
from adam.behavioral_analytics.atom_interface import (
    AtomKnowledgeInterface,
    AtomBehavioralContext,
    get_atom_knowledge_interface,
)
from adam.behavioral_analytics.classifiers import (
    get_purchase_intent_classifier,
    get_emotional_state_classifier,
    get_cognitive_load_estimator,
    get_decision_confidence_analyzer,
)
from adam.behavioral_analytics.knowledge.hypothesis_engine import (
    get_hypothesis_engine,
)

logger = logging.getLogger(__name__)


# =============================================================================
# STATE TYPE
# =============================================================================

class BehavioralWorkflowState:
    """State for behavioral workflow nodes."""
    
    def __init__(self, state: Dict[str, Any]):
        self._state = state
    
    @property
    def session_id(self) -> str:
        return self._state.get("session_id", "")
    
    @property
    def user_id(self) -> Optional[str]:
        return self._state.get("user_id")
    
    @property
    def request_id(self) -> str:
        return self._state.get("request_id", "")
    
    @property
    def behavioral_session(self) -> Optional[BehavioralSession]:
        return self._state.get("behavioral_session")
    
    @behavioral_session.setter
    def behavioral_session(self, session: BehavioralSession):
        self._state["behavioral_session"] = session
    
    @property
    def behavioral_features(self) -> Dict[str, float]:
        return self._state.get("behavioral_features", {})
    
    @behavioral_features.setter
    def behavioral_features(self, features: Dict[str, float]):
        self._state["behavioral_features"] = features
    
    @property
    def psychological_inference(self) -> Optional[PsychologicalInference]:
        return self._state.get("psychological_inference")
    
    @psychological_inference.setter
    def psychological_inference(self, inference: PsychologicalInference):
        self._state["psychological_inference"] = inference
    
    @property
    def behavioral_context(self) -> Optional[AtomBehavioralContext]:
        return self._state.get("behavioral_context")
    
    @behavioral_context.setter
    def behavioral_context(self, context: AtomBehavioralContext):
        self._state["behavioral_context"] = context
    
    @property
    def behavioral_knowledge(self) -> List[Dict[str, Any]]:
        return self._state.get("behavioral_knowledge", [])
    
    @behavioral_knowledge.setter
    def behavioral_knowledge(self, knowledge: List[Dict[str, Any]]):
        self._state["behavioral_knowledge"] = knowledge
    
    def to_dict(self) -> Dict[str, Any]:
        return self._state


# =============================================================================
# WORKFLOW NODES
# =============================================================================

async def collect_implicit_signals(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Collect and process implicit behavioral signals.
    
    This node:
    1. Gets the behavioral session from state
    2. Extracts features using the BehavioralAnalyticsEngine
    3. Updates state with features
    
    Args:
        state: Workflow state dict
        
    Returns:
        Updated state with behavioral_features
    """
    ws = BehavioralWorkflowState(state)
    
    session = ws.behavioral_session
    if not session:
        logger.debug("No behavioral session in state, creating empty features")
        state["behavioral_features"] = {}
        state["behavioral_signals_collected"] = False
        return state
    
    try:
        engine = get_behavioral_analytics_engine()
        
        # Process session (features are extracted internally)
        result = await engine.process_session(session, include_hypothesis_testing=False)
        
        state["behavioral_features"] = result.get("features", {})
        state["behavioral_signals"] = result.get("signals", [])
        state["behavioral_signals_collected"] = True
        state["behavioral_signal_count"] = result.get("signal_count", 0)
        
        logger.info(
            f"Collected {result.get('feature_count', 0)} features, "
            f"{result.get('signal_count', 0)} signals"
        )
    except Exception as e:
        logger.error(f"Failed to collect implicit signals: {e}")
        state["behavioral_features"] = {}
        state["behavioral_signals_collected"] = False
        state["behavioral_error"] = str(e)
    
    return state


async def infer_psychological_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Infer psychological state from signals.
    
    This node:
    1. Gets features from state
    2. Runs classifiers for each psychological dimension
    3. Combines into psychological inference
    4. Updates state with inference
    
    Args:
        state: Workflow state with behavioral_features
        
    Returns:
        Updated state with psychological_inference
    """
    features = state.get("behavioral_features", {})
    
    if not features:
        logger.debug("No behavioral features for inference")
        state["psychological_inference"] = None
        state["inference_performed"] = False
        return state
    
    try:
        # Run classifiers
        purchase_classifier = get_purchase_intent_classifier()
        emotion_classifier = get_emotional_state_classifier()
        load_estimator = get_cognitive_load_estimator()
        confidence_analyzer = get_decision_confidence_analyzer()
        
        # Get classifications
        purchase_result = purchase_classifier.predict(features)
        emotion_result = emotion_classifier.classify(features)
        load_result = load_estimator.estimate(features)
        confidence_result = confidence_analyzer.analyze(features)
        
        # Build inference
        inference = PsychologicalInference(
            session_id=state.get("session_id", ""),
            user_id=state.get("user_id"),
            emotional_arousal=emotion_result.arousal,
            emotional_valence=emotion_result.valence,
            decision_confidence=confidence_result["confidence_score"],
            cognitive_load=load_result["load_score"],
            purchase_intent=purchase_result["intent_score"],
            frustration_level=features.get("rage_click_count", 0) / 3,
            processing_mode=confidence_result["processing_mode"],
            inference_confidence=(
                purchase_result["confidence"] +
                emotion_result.confidence +
                load_result["confidence"] +
                confidence_result["analysis_confidence"]
            ) / 4,
            signals_used=state.get("behavioral_signal_count", 0),
        )
        
        state["psychological_inference"] = inference.to_dict()
        state["inference_performed"] = True
        
        # Store individual classifier results for debugging
        state["classifier_results"] = {
            "purchase_intent": purchase_result,
            "emotional_state": emotion_result.to_dict(),
            "cognitive_load": load_result,
            "decision_confidence": confidence_result,
        }
        
        logger.info(
            f"Inferred psychological state: "
            f"arousal={inference.emotional_arousal:.2f}, "
            f"confidence={inference.decision_confidence:.2f}, "
            f"intent={inference.purchase_intent:.2f}"
        )
    except Exception as e:
        logger.error(f"Failed to infer psychological state: {e}")
        state["psychological_inference"] = None
        state["inference_performed"] = False
        state["inference_error"] = str(e)
    
    return state


async def query_behavioral_knowledge(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Get relevant behavioral knowledge.
    
    This node:
    1. Determines relevant constructs from context
    2. Queries knowledge for each construct
    3. Updates state with knowledge
    
    Args:
        state: Workflow state
        
    Returns:
        Updated state with behavioral_knowledge
    """
    try:
        interface = get_atom_knowledge_interface()
        
        # Determine constructs to query based on decision type
        decision_type = state.get("decision_type", "ad_selection")
        
        construct_mapping = {
            "ad_selection": ["decision_confidence", "purchase_intent", "emotional_arousal"],
            "message_framing": ["regulatory_focus", "construal_level", "emotional_arousal"],
            "timing_optimization": ["cognitive_load", "decision_confidence", "processing_mode"],
        }
        
        constructs = construct_mapping.get(decision_type, ["decision_confidence", "purchase_intent"])
        
        # Query knowledge for each construct
        knowledge = await interface.get_relevant_knowledge(constructs)
        
        # Flatten to list
        all_knowledge = []
        for construct, items in knowledge.items():
            for item in items:
                item["relevant_to"] = construct
                all_knowledge.append(item)
        
        state["behavioral_knowledge"] = all_knowledge
        state["knowledge_constructs_queried"] = constructs
        
        logger.info(
            f"Retrieved {len(all_knowledge)} knowledge items for "
            f"{len(constructs)} constructs"
        )
    except Exception as e:
        logger.error(f"Failed to query behavioral knowledge: {e}")
        state["behavioral_knowledge"] = []
        state["knowledge_error"] = str(e)
    
    return state


async def record_for_hypothesis_testing(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Record signals for hypothesis testing.
    
    This node:
    1. Gets session features and outcome (if available)
    2. Records observations for active hypotheses
    3. Checks for promotable hypotheses
    
    Args:
        state: Workflow state with behavioral data and outcome
        
    Returns:
        Updated state with hypothesis_updates
    """
    features = state.get("behavioral_features", {})
    outcome = state.get("decision_outcome")
    
    if not features:
        state["hypotheses_updated"] = []
        return state
    
    try:
        hypothesis_engine = get_hypothesis_engine()
        
        # Auto-generate hypotheses if session available
        session = state.get("behavioral_session")
        if session:
            new_hypotheses = await hypothesis_engine.auto_generate_hypotheses(session)
            state["hypotheses_generated"] = [h.hypothesis_id for h in new_hypotheses]
        
        # Record outcome if available
        hypotheses_updated = []
        if outcome is not None:
            active_hypotheses = hypothesis_engine.get_hypotheses_by_status("testing")
            
            for hypothesis in active_hypotheses:
                result = await hypothesis_engine.record_observation(
                    hypothesis.hypothesis_id,
                    features,
                    outcome.get("value", 0.0),
                    outcome.get("positive", False),
                )
                if result.get("status") == "recorded":
                    hypotheses_updated.append(hypothesis.hypothesis_id)
        
        state["hypotheses_updated"] = hypotheses_updated
        
        # Check for promotable hypotheses
        promotable = hypothesis_engine.get_promotable_hypotheses()
        state["hypotheses_promotable"] = [h.hypothesis_id for h in promotable]
        
        if hypotheses_updated:
            logger.info(f"Updated {len(hypotheses_updated)} hypotheses")
    except Exception as e:
        logger.error(f"Failed to record for hypothesis testing: {e}")
        state["hypothesis_error"] = str(e)
    
    return state


async def apply_behavioral_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Apply behavioral context to atom reasoning.
    
    This node:
    1. Builds AtomBehavioralContext from state
    2. Generates regulatory focus and construal hints
    3. Updates state for atom consumption
    
    Args:
        state: Workflow state
        
    Returns:
        Updated state with behavioral_context for atoms
    """
    try:
        interface = get_atom_knowledge_interface()
        
        session_id = state.get("session_id", "unknown")
        user_id = state.get("user_id")
        
        # Get or create context
        session = state.get("behavioral_session")
        context = await interface.get_behavioral_context(
            session_id=session_id,
            user_id=user_id,
            session=session,
        )
        
        # Convert to dict for state
        context_dict = context.to_dict()
        
        # Add specific hints for atoms
        state["behavioral_context"] = context_dict
        state["regulatory_focus_hints"] = context.get_regulatory_focus_hints()
        state["construal_level_hints"] = context.get_construal_level_hints()
        state["arousal_alignment"] = context.get_arousal_alignment_hints()
        
        logger.info(
            f"Applied behavioral context: "
            f"has_signals={context.has_implicit_signals}, "
            f"arousal={context.emotional_arousal:.2f}"
        )
    except Exception as e:
        logger.error(f"Failed to apply behavioral context: {e}")
        state["behavioral_context"] = None
        state["context_error"] = str(e)
    
    return state


# =============================================================================
# DESKTOP-SPECIFIC WORKFLOW NODES
# =============================================================================

async def collect_desktop_signals(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Collect desktop-specific behavioral signals.
    
    This node:
    1. Gets cursor trajectory data
    2. Gets keystroke dynamics
    3. Extracts desktop-specific features
    
    Desktop signals provide high-fidelity decisional conflict detection
    through cursor trajectory analysis.
    
    Args:
        state: Workflow state dict with raw_desktop_events
        
    Returns:
        Updated state with desktop_features
    """
    raw_events = state.get("raw_desktop_events", {})
    session = state.get("behavioral_session")
    
    if not raw_events and (not session or not session.has_desktop_signals):
        logger.debug("No desktop signals available")
        state["desktop_features"] = {}
        state["desktop_signals_collected"] = False
        return state
    
    try:
        engine = get_behavioral_analytics_engine()
        
        # If we have a session with desktop signals, features are already extracted
        if session and session.has_desktop_signals:
            state["desktop_features"] = session.desktop_features
            state["desktop_signals_collected"] = True
            
            # Provide detailed conflict analysis
            conflicts = session.conflict_indicators
            state["desktop_conflict_indicators"] = conflicts
            state["desktop_high_conflict_count"] = sum(
                1 for c in conflicts if c.get("conflict_score", 0) > 0.5
            )
            
            logger.info(
                f"Collected desktop signals: "
                f"{len(session.desktop_features)} features, "
                f"{len(conflicts)} conflict indicators"
            )
        else:
            # Would need to process raw events here
            state["desktop_features"] = {}
            state["desktop_signals_collected"] = False
    except Exception as e:
        logger.error(f"Failed to collect desktop signals: {e}")
        state["desktop_features"] = {}
        state["desktop_signals_collected"] = False
        state["desktop_error"] = str(e)
    
    return state


async def infer_mechanism_profile_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Infer cognitive mechanism profile.
    
    This node:
    1. Gets all behavioral features (mobile + desktop)
    2. Maps features to the 9 cognitive mechanisms
    3. Generates messaging recommendations
    
    This is the KEY NODE that unifies all signal domains into
    mechanism-based reasoning for atoms.
    
    Args:
        state: Workflow state with behavioral_features
        
    Returns:
        Updated state with mechanism_profile and recommendations
    """
    session = state.get("behavioral_session")
    inference_dict = state.get("psychological_inference")
    
    if not session or not session.features:
        logger.debug("No session/features for mechanism inference")
        state["mechanism_profile"] = None
        state["mechanism_inference_performed"] = False
        return state
    
    try:
        engine = get_behavioral_analytics_engine()
        
        # Reconstruct inference if available
        inference = None
        if inference_dict:
            inference = PsychologicalInference(**inference_dict)
        
        # Infer mechanism profile
        mechanism_profile = await engine.infer_mechanism_profile(session, inference)
        
        # Store in state
        state["mechanism_profile"] = mechanism_profile.to_dict()
        state["mechanism_inference_performed"] = True
        
        # Extract key mechanism insights for downstream nodes
        dominant = mechanism_profile.get_dominant_mechanisms()
        state["dominant_mechanisms"] = [
            {"mechanism": m.value, "strength": s}
            for m, s in dominant
        ]
        
        # Get messaging recommendations
        recommendations = mechanism_profile.get_messaging_recommendations()
        state["mechanism_recommendations"] = recommendations
        
        # Signal domains used
        state["mechanism_signal_domains"] = mechanism_profile.signal_domains
        state["mechanism_confidence"] = mechanism_profile.overall_confidence
        
        logger.info(
            f"Inferred mechanism profile: "
            f"{len(dominant)} dominant mechanisms, "
            f"confidence={mechanism_profile.overall_confidence:.2f}, "
            f"domains={mechanism_profile.signal_domains}"
        )
    except Exception as e:
        logger.error(f"Failed to infer mechanism profile: {e}")
        state["mechanism_profile"] = None
        state["mechanism_inference_performed"] = False
        state["mechanism_error"] = str(e)
    
    return state


async def apply_mechanism_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Apply mechanism context to atom reasoning.
    
    This node:
    1. Gets mechanism profile from state
    2. Generates mechanism-specific hints for each atom type
    3. Updates state with atom-consumable context
    
    This is what atoms use to select mechanism-aligned messaging.
    
    Args:
        state: Workflow state with mechanism_profile
        
    Returns:
        Updated state with mechanism context for atoms
    """
    profile_dict = state.get("mechanism_profile")
    
    if not profile_dict:
        logger.debug("No mechanism profile for context")
        state["mechanism_context"] = None
        return state
    
    try:
        # Reconstruct profile
        profile = UserMechanismProfile(**profile_dict)
        
        # Generate atom-specific hints
        atom_hints = {}
        
        # Regulatory Focus Atom hints
        atom_hints["regulatory_focus_atom"] = {
            "regulatory_focus_value": profile.regulatory_focus,
            "confidence": profile.regulatory_focus_confidence,
            "recommended_frame": "promotion" if profile.regulatory_focus > 0 else "prevention",
            "strength": abs(profile.regulatory_focus),
        }
        
        # Construal Level Atom hints
        atom_hints["construal_level_atom"] = {
            "construal_level_value": profile.construal_level,
            "confidence": profile.construal_level_confidence,
            "recommended_level": "abstract" if profile.construal_level > 0 else "concrete",
            "strength": abs(profile.construal_level),
        }
        
        # Message Framing Atom hints
        atom_hints["message_framing_atom"] = {
            "automatic_evaluation": profile.automatic_evaluation,
            "mimetic_susceptibility": profile.mimetic_susceptibility,
            "temporal_orientation": profile.temporal_orientation,
            "recommendations": profile.get_messaging_recommendations(),
        }
        
        # Ad Selection Atom hints
        atom_hints["ad_selection_atom"] = {
            "attention_engagement": profile.attention_engagement,
            "identity_activation": profile.identity_activation,
            "evolutionary_sensitivity": profile.evolutionary_sensitivity,
            "dominant_mechanisms": state.get("dominant_mechanisms", []),
        }
        
        state["mechanism_context"] = {
            "atom_hints": atom_hints,
            "signal_domains": profile.signal_domains,
            "overall_confidence": profile.overall_confidence,
        }
        
        # Also set individual mechanism values for easy access
        state["construal_level"] = profile.construal_level
        state["regulatory_focus"] = profile.regulatory_focus
        state["automatic_evaluation"] = profile.automatic_evaluation
        state["mimetic_susceptibility"] = profile.mimetic_susceptibility
        state["attention_engagement"] = profile.attention_engagement
        
        logger.info("Applied mechanism context to workflow state")
    except Exception as e:
        logger.error(f"Failed to apply mechanism context: {e}")
        state["mechanism_context"] = None
        state["mechanism_context_error"] = str(e)
    
    return state


async def record_mechanism_outcome(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow Node: Record mechanism predictions vs outcomes.
    
    This node:
    1. Gets mechanism predictions from state
    2. Gets outcome from decision
    3. Records for learning and hypothesis testing
    
    This enables the system to learn which mechanism activations
    lead to desired outcomes.
    
    Args:
        state: Workflow state with mechanism profile and outcome
        
    Returns:
        Updated state with mechanism learning recorded
    """
    profile_dict = state.get("mechanism_profile")
    outcome = state.get("decision_outcome")
    
    if not profile_dict or not outcome:
        logger.debug("No mechanism profile or outcome for recording")
        return state
    
    try:
        engine = get_behavioral_analytics_engine()
        
        # Record mechanism-outcome association for learning
        mechanism_outcomes = {
            "session_id": state.get("session_id"),
            "mechanisms_used": state.get("dominant_mechanisms", []),
            "recommendations_applied": state.get("mechanism_recommendations", {}),
            "outcome_type": outcome.get("type"),
            "outcome_value": outcome.get("value", 0.0),
            "outcome_positive": outcome.get("positive", False),
        }
        
        state["mechanism_outcomes"] = mechanism_outcomes
        state["mechanism_outcome_recorded"] = True
        
        # This would integrate with the learning bridge
        # await learning_bridge.record_mechanism_outcome(mechanism_outcomes)
        
        logger.info(
            f"Recorded mechanism outcome: "
            f"outcome={outcome.get('type')}, positive={outcome.get('positive')}"
        )
    except Exception as e:
        logger.error(f"Failed to record mechanism outcome: {e}")
        state["mechanism_outcome_recorded"] = False
        state["mechanism_outcome_error"] = str(e)
    
    return state


# =============================================================================
# WORKFLOW GRAPH BUILDER
# =============================================================================

def build_behavioral_workflow_nodes() -> Dict[str, Any]:
    """
    Build the behavioral workflow nodes for integration.
    
    Returns dict of node names to node functions.
    
    The full behavioral pipeline includes:
    - Signal collection (mobile + desktop)
    - Psychological inference
    - Mechanism profile inference (9 mechanisms)
    - Knowledge query
    - Context application
    - Outcome recording
    """
    return {
        # Core signal collection
        "collect_implicit_signals": collect_implicit_signals,
        "collect_desktop_signals": collect_desktop_signals,
        # Inference
        "infer_psychological_state": infer_psychological_state,
        "infer_mechanism_profile": infer_mechanism_profile_node,
        # Knowledge
        "query_behavioral_knowledge": query_behavioral_knowledge,
        # Context application
        "apply_behavioral_context": apply_behavioral_context,
        "apply_mechanism_context": apply_mechanism_context,
        # Learning
        "record_for_hypothesis_testing": record_for_hypothesis_testing,
        "record_mechanism_outcome": record_mechanism_outcome,
    }


def get_behavioral_workflow_edges() -> List[tuple]:
    """
    Get the edges for behavioral workflow integration.
    
    Returns list of (from_node, to_node) tuples.
    
    The workflow runs:
    1. Initialize → Collect signals (mobile + desktop in parallel if both present)
    2. Signals → Psychological inference
    3. Inference → Mechanism profile inference
    4. Profile → Knowledge query
    5. Knowledge → Context application (both behavioral and mechanism)
    6. After decision → Record outcomes for learning
    """
    return [
        # Signal collection (can be parallel for mobile/desktop)
        ("initialize", "collect_implicit_signals"),
        ("initialize", "collect_desktop_signals"),
        # Merge and infer
        ("collect_implicit_signals", "infer_psychological_state"),
        ("collect_desktop_signals", "infer_psychological_state"),
        # Mechanism inference (after psychological state)
        ("infer_psychological_state", "infer_mechanism_profile"),
        # Knowledge with mechanism context
        ("infer_mechanism_profile", "query_behavioral_knowledge"),
        # Apply contexts
        ("query_behavioral_knowledge", "apply_behavioral_context"),
        ("query_behavioral_knowledge", "apply_mechanism_context"),
        # After decision - record for learning
        ("holistic_synthesis", "record_for_hypothesis_testing"),
        ("holistic_synthesis", "record_mechanism_outcome"),
    ]


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

async def enhance_workflow_state(
    state: Dict[str, Any],
    session_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enhance workflow state with behavioral analytics.
    
    Runs all behavioral nodes in sequence, including:
    - Mobile and desktop signal collection
    - Psychological inference
    - Mechanism profile inference (9 mechanisms)
    - Knowledge query
    - Context application
    
    Args:
        state: Existing workflow state
        session_data: Optional raw session data to process
        
    Returns:
        Enhanced state with behavioral insights and mechanism profile
    """
    # Build session if data provided
    if session_data:
        session = BehavioralSession(
            session_id=session_data.get("session_id", state.get("session_id", "unknown")),
            user_id=session_data.get("user_id", state.get("user_id")),
            device_id=session_data.get("device_id", "unknown"),
            device_type=DeviceType(session_data.get("device_type", "mobile")),
        )
        state["behavioral_session"] = session
    
    # Run nodes in sequence
    # 1. Collect signals from all domains
    state = await collect_implicit_signals(state)
    state = await collect_desktop_signals(state)
    
    # 2. Psychological inference
    state = await infer_psychological_state(state)
    
    # 3. Mechanism profile inference (maps to 9 mechanisms)
    state = await infer_mechanism_profile_node(state)
    
    # 4. Query behavioral knowledge
    state = await query_behavioral_knowledge(state)
    
    # 5. Apply contexts
    state = await apply_behavioral_context(state)
    state = await apply_mechanism_context(state)
    
    return state


# =============================================================================
# HOLISTIC WORKFLOW INTEGRATION
# =============================================================================

# These functions integrate with the existing holistic_decision_workflow.py
# They use the existing WorkflowState format and contribute behavioral signals
# to the aggregated_signals slot.

async def behavioral_signal_contribution(
    request_id: str,
    user_id: str,
    session_id: str,
    session_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate behavioral signal contribution for the holistic workflow.
    
    This function is called from the holistic workflow's aggregate_signals node
    to contribute behavioral analytics signals to the decision.
    
    Integrates with:
    - adam/workflows/holistic_decision_workflow.py
    - adam/signals/ (Signal Aggregation #08)
    
    Args:
        request_id: Request identifier
        user_id: User identifier
        session_id: Session identifier
        session_context: Session context from workflow state
        
    Returns:
        Dict with behavioral signals for aggregated_signals state slot
    """
    try:
        engine = get_behavioral_analytics_engine()
        interface = get_atom_knowledge_interface()
        
        # Build session from context
        session = BehavioralSession(
            session_id=session_id,
            user_id=user_id,
            device_id=session_context.get("device_id", "unknown"),
            device_type=DeviceType(session_context.get("device_type", "mobile")),
        )
        
        # Process session
        result = await engine.process_session(session, include_hypothesis_testing=False)
        
        # Get intelligence evidence for multi-source fusion
        evidence = await interface.get_intelligence_evidence(
            session_id=session_id,
            user_id=user_id,
            session=session,
        )
        
        return {
            "source": "behavioral_analytics",
            "signals": result.get("signals", []),
            "features": result.get("features", {}),
            "inference": result.get("inference", {}),
            "mechanism_profile": result.get("mechanism_profile", {}),
            "dominant_mechanisms": result.get("dominant_mechanisms", []),
            "messaging_recommendations": result.get("messaging_recommendations", {}),
            "evidence_count": len(evidence),
            "evidence": [e.model_dump() for e in evidence[:10]],  # Limit for state size
            "signal_domains": [
                SignalDomain.MOBILE.value if session.has_mobile_signals else None,
                SignalDomain.DESKTOP.value if session.has_desktop_signals else None,
            ],
            "confidence": result.get("inference", {}).get("overall_confidence", 0.5),
        }
        
    except Exception as e:
        logger.error(f"Failed to generate behavioral signal contribution: {e}")
        return {
            "source": "behavioral_analytics",
            "error": str(e),
            "signals": [],
            "features": {},
            "confidence": 0.0,
        }


async def enrich_atom_outputs_with_behavioral(
    atom_outputs: Dict[str, Dict[str, Any]],
    request_id: str,
    user_id: str,
    session_id: str,
    session: Optional[BehavioralSession] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Enrich atom outputs with behavioral intelligence evidence.
    
    Called after atoms execute to add behavioral signals to their outputs.
    This supports the multi-source fusion pattern in BaseAtom.
    
    Args:
        atom_outputs: Existing atom outputs from DAG execution
        request_id: Request identifier
        user_id: User identifier
        session_id: Session identifier
        session: Optional behavioral session
        
    Returns:
        Enriched atom outputs with behavioral evidence
    """
    try:
        interface = get_atom_knowledge_interface()
        
        # Get behavioral context
        context = await interface.get_behavioral_context(
            session_id=session_id,
            user_id=user_id,
            session=session,
            include_mechanism_profile=True,
        )
        
        # Enrich each atom's output with relevant behavioral hints
        enriched = dict(atom_outputs)
        
        for atom_id, output in enriched.items():
            if "regulatory_focus" in atom_id.lower():
                output["behavioral_hints"] = context.get_regulatory_focus_hints()
            elif "construal" in atom_id.lower():
                output["behavioral_hints"] = context.get_construal_level_hints()
            elif "mechanism" in atom_id.lower():
                if context.mechanism_profile:
                    output["behavioral_hints"] = {
                        "dominant_mechanisms": context.get_dominant_mechanisms(),
                        "recommendations": context.get_messaging_recommendations(),
                    }
            
            # Add general behavioral context to all atoms
            output["behavioral_context"] = {
                "has_signals": context.has_implicit_signals,
                "arousal": context.emotional_arousal,
                "cognitive_load": context.cognitive_load,
                "purchase_intent": context.purchase_intent,
            }
        
        return enriched
        
    except Exception as e:
        logger.error(f"Failed to enrich atom outputs with behavioral: {e}")
        return atom_outputs


def get_behavioral_workflow_integration():
    """
    Get functions for integrating with the holistic decision workflow.
    
    Returns:
        Dict with integration functions
    """
    return {
        "signal_contribution": behavioral_signal_contribution,
        "enrich_atom_outputs": enrich_atom_outputs_with_behavioral,
        "enhance_workflow_state": enhance_workflow_state,
    }
