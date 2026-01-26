# =============================================================================
# ADAM Behavioral Analytics: Atom of Thought Interface
# Location: adam/behavioral_analytics/atom_interface.py
# =============================================================================

"""
ATOM OF THOUGHT INTERFACE FOR BEHAVIORAL ANALYTICS

Provides the interface for atoms to query behavioral knowledge and
incorporate implicit signals into their reasoning.

This integrates behavioral analytics into the existing Atom of Thought
DAG architecture, enabling atoms to:
1. Query research-validated knowledge
2. Access current session implicit signals
3. Receive psychological state inferences
4. Inform regulatory focus and construal level reasoning
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    KnowledgeTier,
)
from adam.behavioral_analytics.models.events import (
    BehavioralSession,
)
from adam.behavioral_analytics.models.mechanisms import (
    CognitiveMechanism,
    UserMechanismProfile,
    MechanismEvidence,
)
from adam.behavioral_analytics.engine import (
    BehavioralAnalyticsEngine,
    PsychologicalInference,
    get_behavioral_analytics_engine,
)
from adam.behavioral_analytics.knowledge.research_seeder import (
    get_research_knowledge_seeder,
)
from adam.behavioral_analytics.knowledge.advertising_psychology_seeder import (
    get_advertising_psychology_seeder,
)
from adam.behavioral_analytics.classifiers.regulatory_focus_detector import (
    get_regulatory_focus_detector,
    RegulatoryFocusDetection,
)
from adam.behavioral_analytics.classifiers.cognitive_state_estimator import (
    get_cognitive_state_estimator,
    CognitiveStateEstimation,
)
from adam.behavioral_analytics.models.advertising_psychology import (
    UserAdvertisingPsychologyProfile,
    RegulatoryFocusProfile,
    CognitiveStateProfile,
    MoralFoundationsProfile,
    TemporalPattern,
    ConstrualLevelProfile,
)

# Intelligence Source integration (10 intelligence sources)
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
    NonconsciousSignalEvidence,
)

logger = logging.getLogger(__name__)


class AtomBehavioralContext:
    """
    Behavioral context provided to an atom for reasoning.
    
    Contains:
    - Current psychological state inference
    - Cognitive mechanism profile (9 mechanisms)
    - Relevant behavioral knowledge
    - Session features
    - Knowledge-based reasoning hints
    
    This is the UNIFIED context that atoms receive, incorporating
    signals from all domains (mobile, desktop, media).
    """
    
    def __init__(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        inference: Optional[PsychologicalInference] = None,
        mechanism_profile: Optional[UserMechanismProfile] = None,
        knowledge: Optional[List[BehavioralKnowledge]] = None,
        features: Optional[Dict[str, float]] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.inference = inference
        self.mechanism_profile = mechanism_profile
        self.knowledge = knowledge or []
        self.features = features or {}
        self.timestamp = datetime.now(timezone.utc)
    
    @property
    def has_implicit_signals(self) -> bool:
        """Whether we have implicit behavioral signals."""
        return bool(self.features)
    
    @property
    def emotional_arousal(self) -> float:
        """Current emotional arousal level."""
        return self.inference.emotional_arousal if self.inference else 0.5
    
    @property
    def decision_confidence(self) -> float:
        """Current decision confidence level."""
        return self.inference.decision_confidence if self.inference else 0.5
    
    @property
    def cognitive_load(self) -> float:
        """Current cognitive load level."""
        return self.inference.cognitive_load if self.inference else 0.5
    
    @property
    def purchase_intent(self) -> float:
        """Current purchase intent score."""
        return self.inference.purchase_intent if self.inference else 0.5
    
    @property
    def processing_mode(self) -> str:
        """Current cognitive processing mode (system1/system2/mixed)."""
        return self.inference.processing_mode if self.inference else "mixed"
    
    def get_regulatory_focus_hints(self) -> Dict[str, Any]:
        """
        Get hints for regulatory focus determination.
        
        Returns behavioral signals relevant to promotion vs prevention focus.
        """
        hints = {
            "promotion_signals": [],
            "prevention_signals": [],
            "confidence": 0.5,
        }
        
        if self.inference:
            hints["confidence"] = self.inference.inference_confidence
            
            # High arousal + fast decisions → promotion
            if self.inference.emotional_arousal > 0.6:
                if self.inference.decision_confidence > 0.6:
                    hints["promotion_signals"].append({
                        "signal": "high_arousal_fast_response",
                        "strength": self.inference.emotional_arousal,
                    })
            
            # High hesitation → prevention
            if self.features.get("hesitation_count", 0) > 2:
                hints["prevention_signals"].append({
                    "signal": "elevated_hesitation",
                    "strength": min(1.0, self.features["hesitation_count"] / 5),
                })
            
            # Right swipes → approach (promotion)
            if self.features.get("right_swipe_ratio", 0.5) > 0.6:
                hints["promotion_signals"].append({
                    "signal": "approach_bias_swipes",
                    "strength": self.features["right_swipe_ratio"],
                })
            elif self.features.get("right_swipe_ratio", 0.5) < 0.4:
                hints["prevention_signals"].append({
                    "signal": "avoidance_bias_swipes",
                    "strength": 1 - self.features["right_swipe_ratio"],
                })
        
        return hints
    
    def get_construal_level_hints(self) -> Dict[str, Any]:
        """
        Get hints for construal level determination.
        
        Returns behavioral signals relevant to abstract vs concrete construal.
        """
        hints = {
            "abstract_signals": [],
            "concrete_signals": [],
            "confidence": 0.5,
        }
        
        # Slow, deliberate processing → abstract
        if self.inference and self.inference.processing_mode == "system2":
            hints["abstract_signals"].append({
                "signal": "deliberate_processing",
                "strength": 0.7,
            })
        elif self.inference and self.inference.processing_mode == "system1":
            hints["concrete_signals"].append({
                "signal": "automatic_processing",
                "strength": 0.7,
            })
        
        # Deep scroll + long dwell → engaged reading → abstract
        if self.features.get("max_depth", 0) > 0.8:
            hints["abstract_signals"].append({
                "signal": "deep_content_engagement",
                "strength": self.features["max_depth"],
            })
        
        # Fast velocity scanning → concrete
        if self.features.get("scroll_velocity_mean", 0) > 500:
            hints["concrete_signals"].append({
                "signal": "rapid_scanning",
                "strength": min(1.0, self.features["scroll_velocity_mean"] / 1000),
            })
        
        if self.inference:
            hints["confidence"] = self.inference.inference_confidence
        
        return hints
    
    def get_arousal_alignment_hints(self) -> Dict[str, Any]:
        """
        Get hints for arousal-message alignment.
        
        Based on Yerkes-Dodson law from psychological research.
        """
        arousal = self.emotional_arousal
        
        if arousal < 0.3:
            return {
                "recommended_message_arousal": "medium-high",
                "reason": "Low user arousal - increase engagement",
                "confidence": 0.7,
            }
        elif arousal > 0.7:
            return {
                "recommended_message_arousal": "low-medium",
                "reason": "High user arousal - avoid overstimulation",
                "confidence": 0.7,
            }
        else:
            return {
                "recommended_message_arousal": "matched",
                "reason": "Optimal arousal range",
                "confidence": 0.6,
            }
    
    # =========================================================================
    # MECHANISM-BASED METHODS
    # =========================================================================
    
    @property
    def has_mechanism_profile(self) -> bool:
        """Whether we have a mechanism profile."""
        return self.mechanism_profile is not None
    
    def get_mechanism_hints(
        self,
        mechanism: CognitiveMechanism,
    ) -> Dict[str, Any]:
        """
        Get hints for a specific cognitive mechanism.
        
        Returns the mechanism state, evidence, and messaging recommendations.
        
        Args:
            mechanism: The cognitive mechanism to get hints for
            
        Returns:
            Dict with mechanism value, confidence, evidence, and recommendations
        """
        if not self.mechanism_profile:
            return {
                "mechanism": mechanism.value,
                "available": False,
                "message": "No mechanism profile available",
            }
        
        state = self.mechanism_profile.get_mechanism_state(mechanism)
        evidence = self.mechanism_profile.evidence_by_mechanism.get(mechanism.value, [])
        
        return {
            "mechanism": mechanism.value,
            "available": True,
            "value": state.value,
            "confidence": state.confidence,
            "polarity": state.polarity.value if state.polarity else None,
            "dominant_pole": state.dominant_pole,
            "evidence_count": len(evidence),
            "evidence_sources": [e.signal_source.value for e in evidence],
        }
    
    def get_all_mechanism_hints(self) -> Dict[str, Dict[str, Any]]:
        """
        Get hints for all 9 cognitive mechanisms.
        
        Returns a dict mapping mechanism name to hints.
        """
        hints = {}
        for mechanism in CognitiveMechanism:
            hints[mechanism.value] = self.get_mechanism_hints(mechanism)
        return hints
    
    def get_dominant_mechanisms(
        self,
        threshold: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Get the most activated mechanisms above threshold.
        
        This is what atoms should use to select which mechanisms
        to leverage for messaging.
        
        Returns:
            List of {mechanism, strength, pole} sorted by strength
        """
        if not self.mechanism_profile:
            return []
        
        dominant = self.mechanism_profile.get_dominant_mechanisms(threshold)
        
        return [
            {
                "mechanism": m.value,
                "strength": s,
                "state": self.mechanism_profile.get_mechanism_state(m).to_dict()
                if hasattr(self.mechanism_profile.get_mechanism_state(m), 'to_dict')
                else None,
            }
            for m, s in dominant
        ]
    
    def get_messaging_recommendations(self) -> Dict[str, Any]:
        """
        Get unified messaging recommendations based on mechanism profile.
        
        This is the primary interface for atoms to get actionable
        recommendations from behavioral analytics.
        
        Returns:
            Dict with framing, focus, tone, and content recommendations
        """
        if not self.mechanism_profile:
            return {
                "available": False,
                "message": "No mechanism profile available",
            }
        
        recommendations = self.mechanism_profile.get_messaging_recommendations()
        recommendations["available"] = True
        recommendations["confidence"] = self.mechanism_profile.overall_confidence
        recommendations["signal_domains"] = self.mechanism_profile.signal_domains
        
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "has_implicit_signals": self.has_implicit_signals,
            "has_mechanism_profile": self.has_mechanism_profile,
            "inference": self.inference.to_dict() if self.inference else None,
            "features": self.features,
            "regulatory_focus_hints": self.get_regulatory_focus_hints(),
            "construal_level_hints": self.get_construal_level_hints(),
            "arousal_alignment": self.get_arousal_alignment_hints(),
            "timestamp": self.timestamp.isoformat(),
        }
        
        # Add mechanism profile if available
        if self.mechanism_profile:
            result["mechanism_profile"] = self.mechanism_profile.to_dict()
            result["dominant_mechanisms"] = self.get_dominant_mechanisms()
            result["messaging_recommendations"] = self.get_messaging_recommendations()
        
        return result


class AtomKnowledgeInterface:
    """
    Interface for atoms to access behavioral knowledge.
    
    Used by atoms to:
    1. Query research-validated knowledge for constructs
    2. Get current implicit signals from sessions
    3. Access psychological state inferences
    4. Enhance reasoning with behavioral context
    """
    
    def __init__(self, engine: Optional[BehavioralAnalyticsEngine] = None):
        self._engine = engine or get_behavioral_analytics_engine()
        self._seeder = get_research_knowledge_seeder()
        self._adv_psych_seeder = get_advertising_psychology_seeder()
        self._regulatory_focus_detector = get_regulatory_focus_detector()
        self._cognitive_state_estimator = get_cognitive_state_estimator()
        
        # Session cache for quick lookups
        self._session_cache: Dict[str, AtomBehavioralContext] = {}
        
        # User psychology profile cache
        self._user_profile_cache: Dict[str, UserAdvertisingPsychologyProfile] = {}
    
    async def get_knowledge_for_construct(
        self,
        construct: str,
        tier: Optional[KnowledgeTier] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all behavioral knowledge mapping to a psychological construct.
        
        Args:
            construct: The psychological construct (e.g., "emotional_arousal")
            tier: Optional tier filter (1 = highest predictive value)
            
        Returns:
            List of knowledge dicts with signal mappings and effect sizes
        """
        return await self._engine.get_knowledge_for_atom(construct, tier)
    
    async def get_behavioral_context(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        session: Optional[BehavioralSession] = None,
        include_mechanism_profile: bool = True,
    ) -> AtomBehavioralContext:
        """
        Get behavioral context for atom reasoning.
        
        If a session is provided, processes it and returns context.
        Otherwise, checks cache for recent context.
        
        This is the UNIFIED context that includes:
        - Psychological inference (arousal, confidence, cognitive load)
        - Mechanism profile (all 9 cognitive mechanisms)
        - Messaging recommendations
        
        Args:
            session_id: The session identifier
            user_id: Optional user identifier
            session: Optional session to process
            include_mechanism_profile: Whether to compute mechanism profile
            
        Returns:
            AtomBehavioralContext with inference, mechanism profile, and knowledge
        """
        # Check cache first
        if session_id in self._session_cache:
            cached = self._session_cache[session_id]
            # Use cache if < 5 minutes old
            age = (datetime.now(timezone.utc) - cached.timestamp).total_seconds()
            if age < 300:
                return cached
        
        # Process session if provided
        if session:
            result = await self._engine.process_session(session, include_hypothesis_testing=False)
            inference = PsychologicalInference(**result.get("inference", {}))
            
            # Get mechanism profile if requested
            mechanism_profile = None
            if include_mechanism_profile and "mechanism_profile" in result:
                # The profile is already computed by process_session
                profile_data = result["mechanism_profile"]
                mechanism_profile = UserMechanismProfile(
                    session_id=session_id,
                    user_id=user_id or session.user_id,
                    construal_level=profile_data.get("construal_level", 0.0),
                    regulatory_focus=profile_data.get("regulatory_focus", 0.0),
                    automatic_evaluation=profile_data.get("automatic_evaluation", 0.0),
                    wanting_liking_gap=profile_data.get("wanting_liking_gap", 0.0),
                    mimetic_susceptibility=profile_data.get("mimetic_susceptibility", 0.5),
                    attention_engagement=profile_data.get("attention_engagement", 0.5),
                    temporal_orientation=profile_data.get("temporal_orientation", 0.0),
                    identity_activation=profile_data.get("identity_activation", 0.5),
                    evolutionary_sensitivity=profile_data.get("evolutionary_sensitivity", 0.5),
                    overall_confidence=profile_data.get("overall_confidence", 0.5),
                    signal_domains=profile_data.get("signal_domains", []),
                )
            
            context = AtomBehavioralContext(
                session_id=session_id,
                user_id=user_id or session.user_id,
                inference=inference,
                mechanism_profile=mechanism_profile,
                features=session.features,
            )
        else:
            # Return empty context
            context = AtomBehavioralContext(
                session_id=session_id,
                user_id=user_id,
            )
        
        # Cache
        self._session_cache[session_id] = context
        
        return context
    
    async def get_relevant_knowledge(
        self,
        constructs: List[str],
        include_tier_3: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all relevant behavioral knowledge for multiple constructs.
        
        Args:
            constructs: List of constructs to query
            include_tier_3: Whether to include Tier 3 (supporting) knowledge
            
        Returns:
            Dict mapping construct -> list of knowledge items
        """
        result = {}
        
        for construct in constructs:
            knowledge = await self.get_knowledge_for_construct(construct)
            
            if not include_tier_3:
                knowledge = [k for k in knowledge if k.get("tier", 3) < 3]
            
            result[construct] = knowledge
        
        return result
    
    def get_signal_interpretation(
        self,
        signal_name: str,
        signal_value: float,
    ) -> Dict[str, Any]:
        """
        Interpret a behavioral signal using research knowledge.
        
        Args:
            signal_name: Name of the signal (e.g., "touch_pressure")
            signal_value: Observed signal value
            
        Returns:
            Interpretation with construct mapping and confidence
        """
        # Look up knowledge for this signal
        all_knowledge = self._seeder.seed_all_knowledge()
        matching = [k for k in all_knowledge if k.signal_name == signal_name]
        
        if not matching:
            return {
                "signal_name": signal_name,
                "signal_value": signal_value,
                "interpretation": "No research knowledge available",
                "confidence": 0.0,
            }
        
        knowledge = matching[0]  # Use highest tier
        
        # Interpret based on thresholds
        if knowledge.signal_threshold_high and signal_value >= knowledge.signal_threshold_high:
            level = "high"
        elif knowledge.signal_threshold_low and signal_value <= knowledge.signal_threshold_low:
            level = "low"
        else:
            level = "moderate"
        
        # Construct mapping
        construct_value = signal_value if knowledge.mapping_direction == "positive" else 1 - signal_value
        
        return {
            "signal_name": signal_name,
            "signal_value": signal_value,
            "signal_level": level,
            "maps_to": knowledge.maps_to_construct,
            "mapping_direction": knowledge.mapping_direction,
            "inferred_construct_value": construct_value,
            "effect_size": knowledge.effect_size,
            "confidence": min(0.9, knowledge.effect_size),
            "implementation_notes": knowledge.implementation_notes,
        }
    
    def clear_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()
    
    async def get_intelligence_evidence(
        self,
        session_id: str,
        user_id: str,
        session: Optional[BehavioralSession] = None,
    ) -> List[NonconsciousSignalEvidence]:
        """
        Get behavioral signals as NonconsciousSignalEvidence for multi-source fusion.
        
        This is the PROPER integration point with the 10 Intelligence Sources
        architecture. Atoms call this to get evidence that participates in
        their multi-source fusion via BaseAtom._gather_evidence().
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            session: Optional behavioral session to process
            
        Returns:
            List of NonconsciousSignalEvidence for multi-source fusion
        """
        evidence_list = []
        
        # Get behavioral context
        context = await self.get_behavioral_context(
            session_id=session_id,
            user_id=user_id,
            session=session,
            include_mechanism_profile=True,
        )
        
        if not context.has_implicit_signals:
            return evidence_list
        
        # Convert features to NonconsciousSignalEvidence
        for signal_name, signal_value in context.features.items():
            # Get research-based interpretation
            interpretation = self.get_signal_interpretation(signal_name, signal_value)
            
            evidence = NonconsciousSignalEvidence(
                source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                confidence_semantics=ConfidenceSemantics.SIGNAL_STRENGTH,
                # Signal identification
                signal_type=signal_name,
                signal_name=signal_name,
                # Measurement
                raw_value=signal_value,
                normalized_value=min(1.0, max(0.0, signal_value / max(1.0, signal_value * 2))),
                measurement_window_seconds=context.inference.inference_duration_ms / 1000 if context.inference else 60.0,
                # Psychological mapping
                maps_to_construct=interpretation.get("maps_to", "unknown"),
                mapping_confidence=interpretation.get("confidence", 0.5),
                mapping_research_basis=interpretation.get("implementation_notes"),
                # User context
                user_id=user_id,
                session_id=session_id,
                # Signal categories
                is_arousal_signal="arousal" in signal_name or "pressure" in signal_name,
                is_attention_signal="attention" in signal_name or "dwell" in signal_name,
                is_conflict_signal="hesitation" in signal_name or "conflict" in signal_name,
                is_engagement_signal="engagement" in signal_name or "scroll" in signal_name,
                # Confidence
                confidence=interpretation.get("confidence", 0.5),
            )
            evidence_list.append(evidence)
        
        # Add mechanism-derived evidence
        if context.mechanism_profile:
            for mech in CognitiveMechanism:
                mech_value = getattr(context.mechanism_profile, mech.value)
                mech_conf = getattr(context.mechanism_profile, f"{mech.value}_confidence")
                
                if abs(mech_value) > 0.2:  # Only include meaningful signals
                    evidence = NonconsciousSignalEvidence(
                        source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                        signal_type=f"mechanism_{mech.value}",
                        signal_name=f"Mechanism: {mech.value}",
                        raw_value=mech_value,
                        normalized_value=min(1.0, max(0.0, (mech_value + 1) / 2)),  # -1 to 1 -> 0 to 1
                        maps_to_construct=mech.value,
                        mapping_confidence=mech_conf,
                        user_id=user_id,
                        session_id=session_id,
                        confidence=mech_conf,
                    )
                    evidence_list.append(evidence)
        
        logger.debug(
            f"Generated {len(evidence_list)} NonconsciousSignalEvidence items "
            f"for session {session_id}"
        )
        
        return evidence_list
    
    async def get_evidence_for_construct(
        self,
        construct: str,
        session_id: str,
        user_id: str,
        session: Optional[BehavioralSession] = None,
    ) -> List[NonconsciousSignalEvidence]:
        """
        Get evidence specifically for a psychological construct.
        
        Used by atoms that focus on specific constructs (e.g., RegulatoryFocusAtom
        only needs evidence that maps to regulatory_focus).
        
        Args:
            construct: Target construct (e.g., "regulatory_focus", "construal_level")
            session_id: Session identifier
            user_id: User identifier
            session: Optional behavioral session
            
        Returns:
            Filtered list of NonconsciousSignalEvidence for the construct
        """
        all_evidence = await self.get_intelligence_evidence(
            session_id=session_id,
            user_id=user_id,
            session=session,
        )
        
        # Filter to relevant construct
        filtered = [
            e for e in all_evidence
            if e.maps_to_construct == construct or
               construct in e.signal_type or
               construct.lower() in e.maps_to_construct.lower()
        ]
        
        return filtered
    
    # =========================================================================
    # ADVERTISING PSYCHOLOGY METHODS
    # =========================================================================
    
    async def get_regulatory_focus_context(
        self,
        user_id: str,
        session_id: str,
        user_text: Optional[str] = None,
        user_texts: Optional[List[str]] = None,
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> RegulatoryFocusDetection:
        """
        Get regulatory focus detection for a user.
        
        HIGHEST-IMPACT: OR = 2-6x CTR when ad frame matches regulatory focus.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            user_text: Single text sample (review, query, message)
            user_texts: Multiple text samples for aggregation
            behavioral_signals: Dict with approach/avoidance signals
            
        Returns:
            RegulatoryFocusDetection with focus type and recommendations
        """
        detection = self._regulatory_focus_detector.detect_combined(
            text=user_text,
            texts=user_texts,
            behavioral_signals=behavioral_signals,
        )
        
        logger.debug(
            f"Regulatory focus for user {user_id}: {detection.focus_type} "
            f"(strength={detection.focus_strength:.2f})"
        )
        
        return detection
    
    async def get_cognitive_state_context(
        self,
        user_id: str,
        session_id: str,
        hour: Optional[int] = None,
        session_duration_minutes: float = 0.0,
        chronotype: str = "neutral",
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> CognitiveStateEstimation:
        """
        Get cognitive state estimation for message complexity matching.
        
        Based on ELM (Elaboration Likelihood Model):
        - High load → Peripheral route → Simple messages, heuristic cues
        - Low load → Central route → Complex messages, strong arguments
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            hour: Hour of day (0-23), uses current if None
            session_duration_minutes: Session duration for fatigue
            chronotype: "morning", "evening", or "neutral"
            behavioral_signals: Real-time behavioral indicators
            
        Returns:
            CognitiveStateEstimation with load level and recommendations
        """
        estimation = self._cognitive_state_estimator.estimate(
            hour=hour,
            session_duration_minutes=session_duration_minutes,
            chronotype=chronotype,
            behavioral_signals=behavioral_signals,
        )
        
        logger.debug(
            f"Cognitive state for user {user_id}: load={estimation.cognitive_load:.2f}, "
            f"route={estimation.processing_route}"
        )
        
        return estimation
    
    async def get_advertising_psychology_context(
        self,
        user_id: str,
        session_id: str,
        user_texts: Optional[List[str]] = None,
        behavioral_signals: Optional[Dict[str, Any]] = None,
        hour: Optional[int] = None,
        session_duration_minutes: float = 0.0,
        chronotype: str = "neutral",
    ) -> UserAdvertisingPsychologyProfile:
        """
        Get comprehensive advertising psychology profile for a user.
        
        Combines all psychology domains for ad targeting:
        - Regulatory focus (OR = 2-6x CTR when matched)
        - Cognitive state (d = 0.5-0.8 for load-reducing interventions)
        - Temporal patterns (g = 0.475 for construal matching)
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            user_texts: Text samples for linguistic analysis
            behavioral_signals: Real-time behavioral signals
            hour: Hour of day for circadian matching
            session_duration_minutes: Session duration for fatigue
            chronotype: User chronotype
            
        Returns:
            UserAdvertisingPsychologyProfile with all domains
        """
        # Check cache first
        if user_id in self._user_profile_cache:
            cached = self._user_profile_cache[user_id]
            age = (datetime.now(timezone.utc) - cached.last_updated).total_seconds()
            if age < 300:  # 5 minute cache
                return cached
        
        domains_populated = []
        
        # Regulatory focus
        reg_focus_detection = await self.get_regulatory_focus_context(
            user_id=user_id,
            session_id=session_id,
            user_texts=user_texts,
            behavioral_signals=behavioral_signals,
        )
        reg_focus = reg_focus_detection.to_profile()
        domains_populated.append("regulatory_focus")
        
        # Cognitive state
        cog_state = await self.get_cognitive_state_context(
            user_id=user_id,
            session_id=session_id,
            hour=hour,
            session_duration_minutes=session_duration_minutes,
            chronotype=chronotype,
            behavioral_signals=behavioral_signals,
        )
        domains_populated.append("cognitive_state")
        
        # Create temporal pattern
        from datetime import datetime as dt
        current_hour = hour if hour is not None else dt.now().hour
        current_day = dt.now().weekday()
        
        temporal = TemporalPattern(
            current_hour=current_hour,
            day_of_week=current_day,
        )
        domains_populated.append("temporal_pattern")
        
        # Create profile
        profile = UserAdvertisingPsychologyProfile(
            user_id=user_id,
            regulatory_focus=reg_focus,
            cognitive_state=cog_state.to_profile(),
            temporal_pattern=temporal,
            domains_populated=domains_populated,
            overall_confidence=(
                (reg_focus_detection.confidence.value == "high") * 0.8 +
                (cog_state.confidence.value == "high") * 0.2
            ) if hasattr(reg_focus_detection.confidence, 'value') else 0.5,
        )
        
        # Cache
        self._user_profile_cache[user_id] = profile
        
        return profile
    
    async def get_tier1_advertising_findings(self) -> List[Dict[str, Any]]:
        """
        Get all Tier 1 (meta-analyzed) advertising psychology findings.
        
        These are the highest-confidence findings for primary targeting decisions.
        
        Returns:
            List of Tier 1 findings with effect sizes and recommendations
        """
        # Seed knowledge if not already done
        behavioral, advertising, interactions = self._adv_psych_seeder.seed_all_knowledge()
        
        tier1_behavioral = self._adv_psych_seeder.get_tier1_behavioral_knowledge()
        tier1_advertising = self._adv_psych_seeder.get_tier1_advertising_knowledge()
        
        findings = []
        
        for k in tier1_behavioral:
            findings.append({
                "type": "behavioral_signal",
                "signal_name": k.signal_name,
                "maps_to": k.maps_to_construct,
                "effect_size": k.effect_size,
                "effect_type": k.effect_type.value,
                "implementation_notes": k.implementation_notes,
                "sample_size": k.total_sample_size,
                "study_count": k.study_count,
            })
        
        for k in tier1_advertising:
            findings.append({
                "type": "advertising_knowledge",
                "predictor": k.predictor_name,
                "ad_element": k.ad_element.value,
                "outcome": k.outcome_metric.value,
                "effect_size": k.effect_size,
                "effect_type": k.effect_type.value,
                "implementation_notes": k.implementation_notes,
                "study_count": k.study_count,
            })
        
        return findings
    
    async def get_message_frame_recommendations(
        self,
        user_id: str,
        session_id: str,
        regulatory_focus: Optional[str] = None,
        funnel_stage: str = "consideration",
    ) -> Dict[str, Any]:
        """
        Get research-backed message framing recommendations.
        
        Combines:
        - Regulatory focus matching (OR = 2-6x)
        - Construal level matching (g = 0.475)
        - Cognitive state adaptation (d = 0.5-0.8)
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            regulatory_focus: Override focus type if known
            funnel_stage: "awareness", "consideration", "decision", "purchase"
            
        Returns:
            Dict with frame, language, imagery, and template recommendations
        """
        # Get profile
        profile = await self.get_advertising_psychology_context(
            user_id=user_id,
            session_id=session_id,
        )
        
        focus = regulatory_focus or (
            profile.regulatory_focus.focus_type 
            if profile.regulatory_focus else "neutral"
        )
        
        # Construal level by funnel stage
        construal_map = {
            "awareness": "high",
            "consideration": "mixed",
            "decision": "low",
            "purchase": "very_low",
        }
        construal = construal_map.get(funnel_stage, "mixed")
        
        # Get cognitive state recommendations
        cog_recs = {}
        if profile.cognitive_state:
            cog_state = profile.cognitive_state
            cog_recs = {
                "message_complexity": cog_state.recommended_complexity,
                "processing_route": cog_state.processing_route,
                "copy_length": cog_state.copy_length,
            }
        
        # Get message templates from detector
        templates = self._regulatory_focus_detector.get_message_templates(
            focus_type=focus,
            product="product",
            benefit="benefit",
        )
        
        # Frame mapping
        frame_map = {
            "promotion": "gain",
            "prevention": "loss_avoidance",
            "neutral": "balanced",
        }
        
        return {
            "user_id": user_id,
            "regulatory_focus": focus,
            "recommended_frame": frame_map.get(focus, "balanced"),
            "construal_level": construal,
            "funnel_stage": funnel_stage,
            "message_templates": templates,
            "cognitive_state": cog_recs,
            "research_basis": {
                "regulatory_fit_effect": "OR = 2-6x CTR",
                "construal_matching_effect": "g = 0.475",
                "cognitive_load_effect": "d = 0.5-0.8",
            },
        }
    
    async def get_advertising_knowledge_evidence(
        self,
        user_id: str,
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
        ad_characteristics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get advertising effectiveness knowledge as evidence for ad selection.
        
        This integrates the 25 years of consumer psychology research into
        the Atom of Thought reasoning process for ad selection.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            user_profile: User's psychological profile (personality, state)
            ad_characteristics: Ad characteristics to evaluate
            
        Returns:
            Dict containing:
                - effectiveness_prediction: Predicted ad effectiveness
                - message_recommendation: Recommended message framing
                - creative_recommendation: Recommended creative elements
                - supporting_knowledge: Research-backed knowledge items used
        """
        from adam.behavioral_analytics.classifiers.advertising_effectiveness import (
            get_advertising_effectiveness_predictor,
        )
        from adam.behavioral_analytics.knowledge.consumer_psychology_seeder import (
            get_consumer_psychology_seeder,
        )
        
        predictor = get_advertising_effectiveness_predictor()
        seeder = get_consumer_psychology_seeder()
        
        # Build user profile from behavioral context if not provided
        if user_profile is None:
            context = await self.get_behavioral_context(
                session_id=session_id,
                user_id=user_id,
            )
            
            user_profile = {
                "personality": {},  # Would come from PersonalityInferencer
                "regulatory_focus": {
                    "type": context.get_regulatory_focus_hints().get("dominant_focus", "neutral"),
                    "strength": context.get_regulatory_focus_hints().get("confidence", 0.5),
                },
                "construal_level": context.get_construal_level_hints().get("construal_level", 0.5),
                "mood": "positive" if context.emotional_arousal > 0.6 else "negative" if context.emotional_arousal < 0.4 else "neutral",
                "need_for_cognition": 0.5,  # Default without measurement
            }
        
        result = {
            "user_id": user_id,
            "session_id": session_id,
            "evidence_type": "advertising_research",
        }
        
        # Get message frame recommendation
        message_rec = await predictor.recommend_message_frame(
            user_profile=user_profile,
            product_context=ad_characteristics or {},
        )
        result["message_recommendation"] = message_rec.model_dump()
        
        # Get creative element recommendations
        creative_rec = await predictor.recommend_creative_elements(
            user_id=user_id,
            user_profile=user_profile,
            product_context=ad_characteristics or {},
        )
        result["creative_recommendation"] = creative_rec.model_dump()
        
        # If we have ad characteristics, predict effectiveness
        if ad_characteristics:
            effectiveness = await predictor.predict_effectiveness(
                user_id=user_id,
                ad_id=ad_characteristics.get("ad_id", "unknown"),
                user_profile=user_profile,
                ad_characteristics=ad_characteristics,
            )
            result["effectiveness_prediction"] = effectiveness.model_dump()
        
        # Get supporting knowledge
        tier1_knowledge = seeder.get_tier1_knowledge()
        result["supporting_knowledge"] = {
            "tier1_count": len(tier1_knowledge),
            "key_findings": [
                {
                    "finding": k.predictor_name,
                    "effect": k.effect_size,
                    "outcome": k.outcome_metric.value,
                }
                for k in tier1_knowledge[:5]  # Top 5 for brevity
            ],
            "overall_advertising_effectiveness": 0.20,  # r=.20 from Eisend & Tarrahi (2016)
        }
        
        return result


# Singleton
_interface: Optional[AtomKnowledgeInterface] = None


def get_atom_knowledge_interface() -> AtomKnowledgeInterface:
    """Get singleton atom knowledge interface."""
    global _interface
    if _interface is None:
        _interface = AtomKnowledgeInterface()
    return _interface


# =============================================================================
# EXAMPLE ATOM INTEGRATION
# =============================================================================

async def enhance_regulatory_focus_atom(
    user_id: str,
    session_id: str,
    session: Optional[BehavioralSession] = None,
    existing_focus: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Example: Enhance RegulatoryFocusAtom with behavioral signals.
    
    This shows how an atom would integrate behavioral analytics.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        session: Optional behavioral session
        existing_focus: Existing focus scores from other sources
        
    Returns:
        Enhanced regulatory focus assessment
    """
    interface = get_atom_knowledge_interface()
    
    # Get behavioral context
    context = await interface.get_behavioral_context(
        session_id=session_id,
        user_id=user_id,
        session=session,
    )
    
    # Get regulatory focus hints from behavioral signals
    focus_hints = context.get_regulatory_focus_hints()
    
    # Start with existing focus or default
    promotion_score = existing_focus.get("promotion", 0.5) if existing_focus else 0.5
    prevention_score = existing_focus.get("prevention", 0.5) if existing_focus else 0.5
    
    # Adjust based on behavioral signals
    if focus_hints["promotion_signals"]:
        promotion_boost = sum(s["strength"] for s in focus_hints["promotion_signals"]) / len(focus_hints["promotion_signals"])
        promotion_score = promotion_score * 0.7 + promotion_boost * 0.3
    
    if focus_hints["prevention_signals"]:
        prevention_boost = sum(s["strength"] for s in focus_hints["prevention_signals"]) / len(focus_hints["prevention_signals"])
        prevention_score = prevention_score * 0.7 + prevention_boost * 0.3
    
    return {
        "promotion_focus": min(1.0, promotion_score),
        "prevention_focus": min(1.0, prevention_score),
        "behavioral_signals_used": len(focus_hints["promotion_signals"]) + len(focus_hints["prevention_signals"]),
        "behavioral_confidence": focus_hints["confidence"],
        "processing_mode": context.processing_mode,
        "emotional_arousal": context.emotional_arousal,
        "decision_confidence": context.decision_confidence,
    }


async def enhance_construal_level_atom(
    user_id: str,
    session_id: str,
    session: Optional[BehavioralSession] = None,
    existing_level: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Example: Enhance ConstrualLevelAtom with behavioral signals.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        session: Optional behavioral session
        existing_level: Existing construal level (0=concrete, 1=abstract)
        
    Returns:
        Enhanced construal level assessment
    """
    interface = get_atom_knowledge_interface()
    
    # Get behavioral context
    context = await interface.get_behavioral_context(
        session_id=session_id,
        user_id=user_id,
        session=session,
    )
    
    # Get construal hints
    construal_hints = context.get_construal_level_hints()
    
    # Start with existing or default
    level = existing_level if existing_level is not None else 0.5
    
    # Adjust based on behavioral signals
    abstract_strength = sum(s["strength"] for s in construal_hints["abstract_signals"]) if construal_hints["abstract_signals"] else 0
    concrete_strength = sum(s["strength"] for s in construal_hints["concrete_signals"]) if construal_hints["concrete_signals"] else 0
    
    if abstract_strength > concrete_strength:
        # Push toward abstract
        level = level * 0.7 + (level + 0.2) * 0.3
    elif concrete_strength > abstract_strength:
        # Push toward concrete
        level = level * 0.7 + (level - 0.2) * 0.3
    
    level = max(0.0, min(1.0, level))
    
    return {
        "construal_level": level,
        "level_label": "abstract" if level > 0.6 else "concrete" if level < 0.4 else "mixed",
        "abstract_signals": len(construal_hints["abstract_signals"]),
        "concrete_signals": len(construal_hints["concrete_signals"]),
        "behavioral_confidence": construal_hints["confidence"],
        "cognitive_load": context.cognitive_load,
    }


async def enhance_ad_selection_with_research(
    user_id: str,
    session_id: str,
    candidate_ads: List[Dict[str, Any]],
    user_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enhance ad selection using 25 years of consumer psychology research.
    
    This example shows how to integrate advertising effectiveness knowledge
    into ad selection decisions.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        candidate_ads: List of candidate ads with characteristics
        user_profile: User's psychological profile
        
    Returns:
        Enhanced ad selection with research-backed predictions
    """
    interface = get_atom_knowledge_interface()
    
    # Get research-based evidence
    research_evidence = await interface.get_advertising_knowledge_evidence(
        user_id=user_id,
        session_id=session_id,
        user_profile=user_profile,
    )
    
    # Score each candidate ad
    ad_scores = []
    
    for ad in candidate_ads:
        # Get effectiveness prediction for this specific ad
        ad_evidence = await interface.get_advertising_knowledge_evidence(
            user_id=user_id,
            session_id=session_id,
            user_profile=user_profile,
            ad_characteristics=ad,
        )
        
        prediction = ad_evidence.get("effectiveness_prediction", {})
        
        ad_scores.append({
            "ad_id": ad.get("ad_id", "unknown"),
            "effectiveness_score": prediction.get("effectiveness_score", 0.5),
            "predicted_brand_attitude": prediction.get("predicted_brand_attitude", 0.5),
            "predicted_purchase_intent": prediction.get("predicted_purchase_intent", 0.5),
            "prediction_confidence": prediction.get("prediction_confidence", 0.5),
            "positive_factors": prediction.get("positive_factors", []),
            "negative_factors": prediction.get("negative_factors", []),
            "optimization_suggestions": prediction.get("optimization_suggestions", []),
        })
    
    # Sort by effectiveness
    ad_scores.sort(key=lambda x: x["effectiveness_score"], reverse=True)
    
    return {
        "recommended_ad": ad_scores[0]["ad_id"] if ad_scores else None,
        "ad_rankings": ad_scores,
        "message_recommendation": research_evidence.get("message_recommendation"),
        "creative_recommendation": research_evidence.get("creative_recommendation"),
        "research_basis": {
            "overall_advertising_r": 0.20,  # Eisend & Tarrahi (2016)
            "key_moderators": [
                "Celebrity-product fit (d=0.90 vs -0.96)",
                "Regulatory fit (promotion×gain, prevention×loss)",
                "Product involvement × creativity",
                "Narrative transportation (r=.47)",
            ],
        },
    }
