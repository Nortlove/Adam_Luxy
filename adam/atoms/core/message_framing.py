# =============================================================================
# ADAM MessageFramingAtom
# Location: adam/atoms/core/message_framing.py
# =============================================================================

"""
MESSAGE FRAMING ATOM

Determines the optimal message framing strategy based on upstream
psychological assessments.

Framing dimensions:
- Gain vs Loss framing (regulatory focus)
- Abstract vs Concrete (construal level)
- Emotional vs Rational (need for cognition)
- Social vs Individual (extraversion)
- Urgency level (temporal pressure)

Psychological Foundation:
- Regulatory Focus Theory (Higgins, 1997)
- Construal Level Theory (Trope & Liberman, 2010)
- Elaboration Likelihood Model (Petty & Cacioppo)
- Framing Effects (Kahneman & Tversky)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    FusionResult,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MESSAGE FRAMING MODELS
# =============================================================================

class FramingDimension(str, Enum):
    """Primary framing dimensions."""
    
    GAIN_LOSS = "gain_loss"
    ABSTRACT_CONCRETE = "abstract_concrete"
    EMOTIONAL_RATIONAL = "emotional_rational"
    SOCIAL_INDIVIDUAL = "social_individual"
    URGENCY = "urgency"


class GainLossFrame(BaseModel):
    """Gain vs Loss framing recommendation."""
    
    gain_emphasis: float = Field(
        ge=0.0, le=1.0,
        description="1.0 = pure gain framing, 0.0 = pure loss framing"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Rationale
    primary_driver: str = Field(default="regulatory_focus")
    example_gain: Optional[str] = None
    example_loss: Optional[str] = None


class AbstractConcreteFrame(BaseModel):
    """Abstract vs Concrete framing recommendation."""
    
    abstraction_level: float = Field(
        ge=0.0, le=1.0,
        description="1.0 = abstract/why, 0.0 = concrete/how"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Guidance
    focus_on_why: bool = Field(default=False)
    focus_on_how: bool = Field(default=False)
    include_specifics: bool = Field(default=True)


class EmotionalRationalFrame(BaseModel):
    """Emotional vs Rational appeal balance."""
    
    emotional_appeal: float = Field(
        ge=0.0, le=1.0,
        description="1.0 = emotional, 0.0 = rational"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Recommended emotions
    target_emotions: List[str] = Field(default_factory=list)
    
    # Rational elements
    include_statistics: bool = Field(default=False)
    include_comparisons: bool = Field(default=False)


class SocialIndividualFrame(BaseModel):
    """Social vs Individual framing."""
    
    social_emphasis: float = Field(
        ge=0.0, le=1.0,
        description="1.0 = social proof emphasis, 0.0 = individual benefit"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Social elements
    use_testimonials: bool = Field(default=False)
    reference_popularity: bool = Field(default=False)
    highlight_community: bool = Field(default=False)


class UrgencyFrame(BaseModel):
    """Urgency level recommendation."""
    
    urgency_level: float = Field(
        ge=0.0, le=1.0,
        description="0.0 = relaxed, 1.0 = high urgency"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing elements
    use_scarcity: bool = Field(default=False)
    use_deadline: bool = Field(default=False)
    emphasize_immediate: bool = Field(default=False)


class MessageFramingRecommendation(BaseModel):
    """Complete message framing recommendation."""
    
    user_id: str
    
    # Framing dimensions
    gain_loss: GainLossFrame
    abstraction: AbstractConcreteFrame
    emotional_rational: EmotionalRationalFrame
    social_individual: SocialIndividualFrame
    urgency: UrgencyFrame
    
    # Overall guidance
    primary_frame: str = Field(default="balanced")
    secondary_frame: Optional[str] = None
    
    # Message parameters
    recommended_length: str = Field(default="medium")  # short/medium/long
    recommended_tone: str = Field(default="neutral")   # enthusiastic/neutral/calm
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# MESSAGE FRAMING ATOM
# =============================================================================

class MessageFramingAtom(BaseAtom):
    """
    Atom for determining optimal message framing.
    
    Dependencies:
    - RegulatoryFocusAtom (gain/loss framing)
    - ConstrualLevelAtom (abstract/concrete)
    - PersonalityExpressionAtom (emotional/social dimensions)
    - UserStateAtom (urgency from temporal pressure)
    - MechanismActivationAtom (mechanism-specific framing)
    
    Intelligence Sources Used:
    - MECHANISM_TRAJECTORIES: Mechanism-framing interactions
    - BANDIT_POSTERIORS: Learned framing effectiveness
    - EMPIRICAL_PATTERNS: Observed framing patterns
    
    Psychological Foundation:
    - Regulatory Focus Theory: Promotion → gain; Prevention → loss
    - Construal Level Theory: Distance → abstract; Proximity → concrete
    - ELM: High NFC → central route; Low NFC → peripheral route
    """
    
    ATOM_TYPE = AtomType.MESSAGE_FRAMING
    ATOM_NAME = "message_framing"
    TARGET_CONSTRUCT = "message_framing"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for message framing."""
        
        if source == IntelligenceSourceType.MECHANISM_TRAJECTORIES:
            return await self._query_mechanism_framing(atom_input)
        elif source == IntelligenceSourceType.BANDIT_POSTERIORS:
            return await self._query_framing_bandits(atom_input)
        elif source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_framing_patterns(atom_input)
        
        return None
    
    async def _query_mechanism_framing(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query mechanism history to determine framing affinity.
        
        Different mechanisms have natural framing affinities:
        - Identity construction → abstract, emotional
        - Scarcity → concrete, urgent
        - Social proof → social, testimonial
        """
        # Get activated mechanisms from upstream
        mech_atom = atom_input.get_upstream("atom_mechanism_activation")
        
        if mech_atom and mech_atom.mechanism_weights:
            weights = mech_atom.mechanism_weights
            
            # Determine framing from mechanism weights
            gain_weight = 0.5
            abstract_weight = 0.5
            emotional_weight = 0.5
            social_weight = 0.5
            urgency_weight = 0.5
            
            # Mechanism → Framing mappings
            mechanism_frames = {
                "identity_construction": {"abstract": 0.8, "emotional": 0.7, "gain": 0.6},
                "scarcity": {"concrete": 0.8, "urgency": 0.9, "loss": 0.7},
                "social_proof": {"social": 0.9, "concrete": 0.6},
                "anchoring": {"concrete": 0.8, "rational": 0.7},
                "mimetic_desire": {"social": 0.8, "emotional": 0.6},
                "attention_dynamics": {"urgency": 0.7, "emotional": 0.6},
                "regulatory_focus": {"gain": 0.5, "loss": 0.5},  # Depends on type
                "temporal_construal": {"abstract": 0.7},
            }
            
            for mech, weight in weights.items():
                if mech in mechanism_frames:
                    frames = mechanism_frames[mech]
                    if "gain" in frames:
                        gain_weight = max(gain_weight, weight * frames["gain"])
                    if "loss" in frames:
                        gain_weight = min(gain_weight, 1.0 - weight * frames["loss"])
                    if "abstract" in frames:
                        abstract_weight = max(abstract_weight, weight * frames["abstract"])
                    if "concrete" in frames:
                        abstract_weight = min(abstract_weight, 1.0 - weight * frames["concrete"])
                    if "emotional" in frames:
                        emotional_weight = max(emotional_weight, weight * frames["emotional"])
                    if "rational" in frames:
                        emotional_weight = min(emotional_weight, 1.0 - weight * frames["rational"])
                    if "social" in frames:
                        social_weight = max(social_weight, weight * frames["social"])
                    if "urgency" in frames:
                        urgency_weight = max(urgency_weight, weight * frames["urgency"])
            
            # Determine primary frame
            frame_scores = {
                "gain": gain_weight,
                "abstract": abstract_weight,
                "emotional": emotional_weight,
                "social": social_weight,
                "urgent": urgency_weight,
            }
            primary = max(frame_scores.keys(), key=lambda k: frame_scores[k])
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.MECHANISM_TRAJECTORIES,
                construct=self.TARGET_CONSTRUCT,
                assessment=primary,
                assessment_value=frame_scores[primary],
                confidence=0.65,
                confidence_semantics=ConfidenceSemantics.STATISTICAL,
                strength=EvidenceStrength.MODERATE,
                reasoning=f"Mechanism-derived framing suggests {primary} emphasis",
                metadata={
                    "gain_emphasis": gain_weight,
                    "abstraction": abstract_weight,
                    "emotional_appeal": emotional_weight,
                    "social_emphasis": social_weight,
                    "urgency": urgency_weight,
                },
            )
        
        return None
    
    async def _query_framing_bandits(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query bandit posteriors for framing effectiveness.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.mechanism_history:
            # Look for framing-related mechanism effectiveness
            frame_mechanisms = {
                "gain": ["gain_framing", "promotion", "aspiration"],
                "loss": ["loss_framing", "prevention", "security"],
                "emotional": ["emotional_appeal", "affective"],
                "rational": ["rational_appeal", "analytical"],
            }
            
            frame_effectiveness = {}
            for frame, mechs in frame_mechanisms.items():
                best_success = 0.5
                for mech_id, mech in user_intel.mechanism_history.mechanisms.items():
                    if any(fm in mech_id.lower() for fm in mechs):
                        best_success = max(best_success, mech.success_rate)
                frame_effectiveness[frame] = best_success
            
            if any(v > 0.5 for v in frame_effectiveness.values()):
                best_frame = max(frame_effectiveness.keys(), key=lambda k: frame_effectiveness[k])
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=best_frame,
                    assessment_value=frame_effectiveness[best_frame],
                    confidence=0.6,
                    confidence_semantics=ConfidenceSemantics.BAYESIAN_POSTERIOR,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=f"Bandit suggests {best_frame} framing",
                    metadata=frame_effectiveness,
                )
        
        return None
    
    async def _query_framing_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query empirical framing patterns.
        """
        # Try to get patterns from archetype match
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.archetype_match:
            archetype = user_intel.archetype_match.archetype_id
            
            # Archetype → Framing mappings
            archetype_frames = {
                "Achiever": {"gain": 0.8, "abstract": 0.6},
                "Explorer": {"abstract": 0.7, "emotional": 0.6},
                "Guardian": {"loss": 0.7, "concrete": 0.6},
                "Connector": {"social": 0.8, "emotional": 0.6},
                "Pragmatist": {"concrete": 0.7, "rational": 0.7},
            }
            
            if archetype in archetype_frames:
                frames = archetype_frames[archetype]
                primary = max(frames.keys(), key=lambda k: frames[k])
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=primary,
                    assessment_value=frames[primary],
                    confidence=0.55,
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=f"Archetype {archetype} typically responds to {primary} framing",
                    metadata=frames,
                )
        
        return None
    
    def _extract_upstream_context(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, Any]:
        """Extract framing-relevant context from upstream atoms."""
        ctx = {
            "regulatory_focus": "balanced",
            "reg_focus_confidence": 0.5,
            "construal_level": 0.5,
            "construal_confidence": 0.5,
            "openness": 0.5,
            "extraversion": 0.5,
            "personality_confidence": 0.5,
            "arousal": 0.5,
            "temporal_pressure": 0.5,
            "cognitive_load": 0.5,
            "state_confidence": 0.5,
        }
        
        # From regulatory focus atom
        rf_output = atom_input.get_upstream("atom_regulatory_focus")
        if rf_output:
            ctx["regulatory_focus"] = rf_output.primary_assessment
            ctx["reg_focus_confidence"] = rf_output.overall_confidence
        
        # From construal level atom
        cl_output = atom_input.get_upstream("atom_construal_level")
        if cl_output:
            ctx["construal_level"] = cl_output.inferred_states.get("construal_abstract", 0.5)
            ctx["construal_confidence"] = cl_output.overall_confidence
        
        # From personality expression atom
        pe_output = atom_input.get_upstream("atom_personality_expression")
        if pe_output:
            ctx["openness"] = pe_output.inferred_states.get("trait_openness", 0.5)
            ctx["extraversion"] = pe_output.inferred_states.get("trait_extraversion", 0.5)
            ctx["personality_confidence"] = pe_output.overall_confidence
        
        # From user state atom
        us_output = atom_input.get_upstream("atom_user_state")
        if us_output:
            ctx["arousal"] = us_output.inferred_states.get("arousal_level", 0.5)
            ctx["temporal_pressure"] = us_output.inferred_states.get("temporal_pressure", 0.5) if "temporal_pressure" in us_output.inferred_states else 0.5
            ctx["cognitive_load"] = us_output.inferred_states.get("cognitive_load", 0.5)
            ctx["state_confidence"] = us_output.overall_confidence
        
        return ctx
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build message framing output from upstream atoms and evidence."""
        
        # Get upstream context
        ctx = self._extract_upstream_context(atom_input)
        
        # Aggregate evidence metadata
        for source_type, evi in evidence.evidence.items():
            if evi.metadata:
                for key, value in evi.metadata.items():
                    if key not in ctx or ctx[key] == 0.5:
                        ctx[key] = value
        
        # =====================================================================
        # BUILD FRAMING DIMENSIONS
        # =====================================================================
        
        # 1. Gain/Loss from regulatory focus
        reg_focus = ctx["regulatory_focus"]
        if reg_focus == "promotion":
            gain_emphasis = 0.75
        elif reg_focus == "prevention":
            gain_emphasis = 0.25
        else:
            gain_emphasis = 0.5
        
        gain_loss = GainLossFrame(
            gain_emphasis=gain_emphasis,
            confidence=ctx["reg_focus_confidence"],
            primary_driver="regulatory_focus",
        )
        
        # 2. Abstract/Concrete from construal level
        construal = ctx.get("construal_level", 0.5)
        if isinstance(construal, str):
            construal = 0.7 if construal == "abstract" else 0.3 if construal == "concrete" else 0.5
        
        abstraction = AbstractConcreteFrame(
            abstraction_level=construal,
            confidence=ctx["construal_confidence"],
            focus_on_why=construal > 0.6,
            focus_on_how=construal < 0.4,
            include_specifics=construal < 0.5,
        )
        
        # 3. Emotional/Rational from personality and cognitive load
        openness = ctx["openness"]
        cognitive_load = ctx["cognitive_load"]
        
        # High openness + low cognitive load → can process emotional
        # High cognitive load → needs simpler, rational processing
        if cognitive_load > 0.7:
            emotional_level = 0.3  # High load → keep it simple/rational
        else:
            emotional_level = openness * 0.6 + 0.2  # Openness drives emotional appeal
        
        target_emotions = []
        if gain_emphasis > 0.6:
            target_emotions = ["excitement", "aspiration", "hope"]
        elif gain_emphasis < 0.4:
            target_emotions = ["concern", "caution", "security"]
        
        emotional_rational = EmotionalRationalFrame(
            emotional_appeal=emotional_level,
            confidence=ctx["personality_confidence"],
            target_emotions=target_emotions,
            include_statistics=emotional_level < 0.4,
            include_comparisons=emotional_level < 0.5,
        )
        
        # 4. Social/Individual from extraversion
        extraversion = ctx["extraversion"]
        
        social_individual = SocialIndividualFrame(
            social_emphasis=extraversion,
            confidence=ctx["personality_confidence"],
            use_testimonials=extraversion > 0.6,
            reference_popularity=extraversion > 0.5,
            highlight_community=extraversion > 0.7,
        )
        
        # 5. Urgency from temporal pressure and arousal
        temporal_pressure = ctx.get("temporal_pressure", 0.5)
        arousal = ctx["arousal"]
        urgency_level = temporal_pressure * 0.6 + arousal * 0.4
        
        urgency = UrgencyFrame(
            urgency_level=urgency_level,
            confidence=ctx["state_confidence"],
            use_scarcity=urgency_level > 0.6,
            use_deadline=urgency_level > 0.7,
            emphasize_immediate=urgency_level > 0.5,
        )
        
        # =====================================================================
        # DETERMINE PRIMARY FRAME
        # =====================================================================
        
        frames = {
            "gain": gain_loss.gain_emphasis,
            "loss": 1 - gain_loss.gain_emphasis,
            "abstract": abstraction.abstraction_level,
            "concrete": 1 - abstraction.abstraction_level,
            "emotional": emotional_rational.emotional_appeal,
            "rational": 1 - emotional_rational.emotional_appeal,
            "social": social_individual.social_emphasis,
            "urgent": urgency.urgency_level,
        }
        
        primary_frame = max(frames, key=frames.get)
        
        # Find secondary frame (excluding inverse of primary)
        inverses = {
            "gain": "loss", "loss": "gain",
            "abstract": "concrete", "concrete": "abstract",
            "emotional": "rational", "rational": "emotional",
        }
        excluded = {primary_frame, inverses.get(primary_frame, "")}
        secondary_candidates = {k: v for k, v in frames.items() if k not in excluded}
        secondary_frame = max(secondary_candidates, key=secondary_candidates.get) if secondary_candidates else None
        
        # =====================================================================
        # DETERMINE MESSAGE PARAMETERS
        # =====================================================================
        
        # Length based on cognitive load and urgency
        if urgency_level > 0.7 or cognitive_load > 0.7:
            length = "short"
        elif cognitive_load < 0.3 and construal > 0.6:
            length = "long"  # Can handle elaborate abstract messaging
        else:
            length = "medium"
        
        # Tone based on framing
        if gain_emphasis > 0.6 and arousal > 0.5:
            tone = "enthusiastic"
        elif gain_emphasis < 0.4:
            tone = "calm"  # Prevention → reassuring, calm
        else:
            tone = "neutral"
        
        # Build recommendation
        recommendation = MessageFramingRecommendation(
            user_id=atom_input.user_id,
            gain_loss=gain_loss,
            abstraction=abstraction,
            emotional_rational=emotional_rational,
            social_individual=social_individual,
            urgency=urgency,
            primary_frame=primary_frame,
            secondary_frame=secondary_frame,
            recommended_length=length,
            recommended_tone=tone,
            overall_confidence=fusion_result.confidence,
        )
        
        # Map to mechanism recommendations (framing supports mechanisms)
        recommended_mechanisms = []
        mechanism_weights = {}
        
        if primary_frame == "gain":
            recommended_mechanisms.append("gain_framing")
            mechanism_weights["gain_framing"] = 0.8
        elif primary_frame == "loss":
            recommended_mechanisms.append("loss_framing")
            mechanism_weights["loss_framing"] = 0.8
        
        if primary_frame == "social" or secondary_frame == "social":
            recommended_mechanisms.append("social_proof")
            mechanism_weights["social_proof"] = 0.7
        
        if urgency_level > 0.6:
            recommended_mechanisms.append("scarcity")
            mechanism_weights["scarcity"] = urgency_level
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary_frame,
            assessment_value=frames[primary_frame],
            secondary_assessments={
                "gain_emphasis": gain_emphasis,
                "abstraction_level": construal,
                "emotional_appeal": emotional_level,
                "social_emphasis": extraversion,
                "urgency_level": urgency_level,
                "secondary_frame": secondary_frame,
                "recommended_length": length,
                "recommended_tone": tone,
                "framing_recommendation": recommendation.model_dump(),
            },
            recommended_mechanisms=recommended_mechanisms,
            mechanism_weights=mechanism_weights,
            inferred_states={
                "frame_gain": gain_emphasis,
                "frame_abstract": construal,
                "frame_emotional": emotional_level,
                "frame_social": extraversion,
                "frame_urgency": urgency_level,
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
