# =============================================================================
# ADAM Theory Graph Schema — Psychological Theory as Graph Structure
# Location: adam/intelligence/graph/theory_schema.py
# =============================================================================

"""
THEORY GRAPH SCHEMA

Encodes psychological theory alongside empirical data in Neo4j.
While existing edges (RESPONDS_TO) encode correlational "what works" knowledge,
theoretical edges encode causal "why it works" knowledge grounded in peer-reviewed
psychological science.

Academic Foundations:
- Borsboom (2017): Network Theory of Psychological Constructs — constructs as
  causally linked network nodes, not latent variables
- Dalege et al. (2016): CAN Model — attitudes as causal networks of beliefs,
  feelings, and behaviors
- Thagard (2000): Explanatory Coherence / ECHO — constraint satisfaction across
  coherent explanation networks
- HyperCausalLP (2024): Mediated causal chains in knowledge graphs
- Friston (2010): Free-Energy Principle — predictive processing as unifying
  framework for perception, action, and learning

Node types:
  PsychologicalState  — An NDF dimension at a particular level (e.g., low uncertainty tolerance)
  PsychologicalNeed   — A motivational need created by a state (e.g., need for closure)
  ProcessingRoute     — A cognitive processing pathway activated by a state (e.g., central route)
  ContextCondition    — A situational moderator (e.g., time pressure, high involvement)

Edge types:
  CREATES_NEED    — A psychological state creates a motivational need
  SATISFIED_BY    — A need is satisfied by a cognitive mechanism
  ACTIVATES_ROUTE — A state activates a processing route
  REQUIRES_QUALITY — A processing route requires a quality in the mechanism
  MODERATES       — A context condition moderates the strength of a SATISFIED_BY link
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PsychologicalState:
    """An NDF dimension at a particular level."""
    name: str
    ndf_dimension: str
    pole: str  # "low" or "high"
    threshold: float  # value below (low) or above (high) which this state activates
    description: str
    academic_source: str


@dataclass
class PsychologicalNeed:
    """A motivational need created by a psychological state."""
    name: str
    description: str
    academic_source: str
    domain: str = ""  # e.g., "cognitive", "social", "emotional", "motivational"


@dataclass
class ProcessingRoute:
    """A cognitive processing pathway."""
    name: str
    description: str
    depth: str  # "shallow", "moderate", "deep"
    academic_source: str


@dataclass
class ContextCondition:
    """A situational moderator."""
    name: str
    condition_type: str  # "temporal", "cognitive", "social", "product", "channel"
    description: str
    academic_source: str


@dataclass
class TheoreticalLink:
    """A causal link between theory graph nodes."""
    link_type: str  # CREATES_NEED, SATISFIED_BY, ACTIVATES_ROUTE, REQUIRES_QUALITY, MODERATES
    source_type: str  # Node label of source
    source_name: str
    target_type: str  # Node label of target
    target_name: str
    strength: float  # 0.0 to 1.0 — how strongly supported by theory
    theory: str  # Brief description of the theoretical basis
    citation: str  # Academic citation
    mediator: Optional[str] = None  # HyperCausalLP: mediated by which construct?
    empirical_validation: float = 0.5  # starts neutral, updated by outcomes
    observation_count: int = 0


# =============================================================================
# PSYCHOLOGICAL STATES (NDF dimensions at poles)
# =============================================================================

PSYCHOLOGICAL_STATES: Dict[str, PsychologicalState] = {
    # Uncertainty Tolerance
    "low_uncertainty_tolerance": PsychologicalState(
        name="low_uncertainty_tolerance",
        ndf_dimension="uncertainty_tolerance",
        pole="low",
        threshold=0.4,
        description="Low tolerance for ambiguity; seeks closure and certainty",
        academic_source="Kruglanski & Webster (1996)",
    ),
    "high_uncertainty_tolerance": PsychologicalState(
        name="high_uncertainty_tolerance",
        ndf_dimension="uncertainty_tolerance",
        pole="high",
        threshold=0.6,
        description="Comfortable with ambiguity; open to exploration",
        academic_source="Budner (1962)",
    ),
    # Cognitive Engagement
    "high_cognitive_engagement": PsychologicalState(
        name="high_cognitive_engagement",
        ndf_dimension="cognitive_engagement",
        pole="high",
        threshold=0.6,
        description="Deeply analytical; seeks substantive evidence",
        academic_source="Petty & Cacioppo (1986)",
    ),
    "low_cognitive_engagement": PsychologicalState(
        name="low_cognitive_engagement",
        ndf_dimension="cognitive_engagement",
        pole="low",
        threshold=0.4,
        description="Relies on heuristics; processes peripherally",
        academic_source="Petty & Cacioppo (1986)",
    ),
    # Social Calibration
    "high_social_calibration": PsychologicalState(
        name="high_social_calibration",
        ndf_dimension="social_calibration",
        pole="high",
        threshold=0.6,
        description="Highly attuned to social cues and group norms",
        academic_source="Cialdini & Goldstein (2004)",
    ),
    "low_social_calibration": PsychologicalState(
        name="low_social_calibration",
        ndf_dimension="social_calibration",
        pole="low",
        threshold=0.4,
        description="Independent-minded; resistant to social influence",
        academic_source="Snyder (1974)",
    ),
    # Approach-Avoidance
    "high_approach": PsychologicalState(
        name="high_approach",
        ndf_dimension="approach_avoidance",
        pole="high",
        threshold=0.6,
        description="Strong approach motivation; seeks gains and rewards",
        academic_source="Carver & White (1994)",
    ),
    "high_avoidance": PsychologicalState(
        name="high_avoidance",
        ndf_dimension="approach_avoidance",
        pole="low",
        threshold=0.4,
        description="Strong avoidance motivation; focused on preventing losses",
        academic_source="Carver & White (1994)",
    ),
    # Status Sensitivity
    "high_status_sensitivity": PsychologicalState(
        name="high_status_sensitivity",
        ndf_dimension="status_sensitivity",
        pole="high",
        threshold=0.6,
        description="Highly attuned to social hierarchy and status signals",
        academic_source="Anderson et al. (2015)",
    ),
    "low_status_sensitivity": PsychologicalState(
        name="low_status_sensitivity",
        ndf_dimension="status_sensitivity",
        pole="low",
        threshold=0.4,
        description="Relatively insensitive to status differentials",
        academic_source="Anderson et al. (2015)",
    ),
    # Arousal Seeking
    "high_arousal_seeking": PsychologicalState(
        name="high_arousal_seeking",
        ndf_dimension="arousal_seeking",
        pole="high",
        threshold=0.6,
        description="Seeks stimulation, novelty, and excitement",
        academic_source="Zuckerman (1994)",
    ),
    "low_arousal_seeking": PsychologicalState(
        name="low_arousal_seeking",
        ndf_dimension="arousal_seeking",
        pole="low",
        threshold=0.4,
        description="Prefers calm, predictable, familiar experiences",
        academic_source="Zuckerman (1994)",
    ),
    # Temporal Horizon
    "short_temporal_horizon": PsychologicalState(
        name="short_temporal_horizon",
        ndf_dimension="temporal_horizon",
        pole="low",
        threshold=0.4,
        description="Present-focused; discounts future outcomes heavily",
        academic_source="Frederick, Loewenstein & O'Donoghue (2002)",
    ),
    "long_temporal_horizon": PsychologicalState(
        name="long_temporal_horizon",
        ndf_dimension="temporal_horizon",
        pole="high",
        threshold=0.6,
        description="Future-oriented; considers long-term consequences",
        academic_source="Zimbardo & Boyd (1999)",
    ),
}


# =============================================================================
# PSYCHOLOGICAL NEEDS
# =============================================================================

PSYCHOLOGICAL_NEEDS: Dict[str, PsychologicalNeed] = {
    "need_for_closure": PsychologicalNeed(
        name="need_for_closure",
        description="Desire for definite knowledge, any answer over ambiguity",
        academic_source="Kruglanski & Webster (1996)",
        domain="cognitive",
    ),
    "need_for_cognitive_consistency": PsychologicalNeed(
        name="need_for_cognitive_consistency",
        description="Drive to maintain coherent beliefs and reduce dissonance",
        academic_source="Festinger (1957)",
        domain="cognitive",
    ),
    "need_for_social_validation": PsychologicalNeed(
        name="need_for_social_validation",
        description="Desire for social approval and conformity with group norms",
        academic_source="Deutsch & Gerard (1955)",
        domain="social",
    ),
    "need_for_status_signaling": PsychologicalNeed(
        name="need_for_status_signaling",
        description="Desire to communicate social position through consumption",
        academic_source="Veblen (1899); Nelissen & Meijers (2011)",
        domain="social",
    ),
    "need_for_autonomy": PsychologicalNeed(
        name="need_for_autonomy",
        description="Desire for self-determination and freedom from coercion",
        academic_source="Deci & Ryan (1985)",
        domain="motivational",
    ),
    "need_for_stimulation": PsychologicalNeed(
        name="need_for_stimulation",
        description="Desire for novel, exciting, and arousing experiences",
        academic_source="Berlyne (1960); Zuckerman (1994)",
        domain="emotional",
    ),
    "need_for_safety": PsychologicalNeed(
        name="need_for_safety",
        description="Desire to minimize risk and avoid negative outcomes",
        academic_source="Maslow (1943); Kahneman & Tversky (1979)",
        domain="motivational",
    ),
    "need_for_competence": PsychologicalNeed(
        name="need_for_competence",
        description="Desire to feel effective and capable in one's environment",
        academic_source="White (1959); Deci & Ryan (1985)",
        domain="motivational",
    ),
    "need_for_belonging": PsychologicalNeed(
        name="need_for_belonging",
        description="Desire for social connection and group membership",
        academic_source="Baumeister & Leary (1995)",
        domain="social",
    ),
    "need_for_identity_expression": PsychologicalNeed(
        name="need_for_identity_expression",
        description="Desire to express and construct self-identity through choices",
        academic_source="Belk (1988); Reed et al. (2012)",
        domain="motivational",
    ),
    "need_for_cognitive_ease": PsychologicalNeed(
        name="need_for_cognitive_ease",
        description="Preference for easy, low-effort processing; fluency preference",
        academic_source="Kahneman (2011); Alter & Oppenheimer (2009)",
        domain="cognitive",
    ),
    "need_for_narrative_coherence": PsychologicalNeed(
        name="need_for_narrative_coherence",
        description="Desire for experiences that fit one's life story and personal narrative",
        academic_source="McAdams (2001); Escalas (2004)",
        domain="cognitive",
    ),
    "need_for_loss_prevention": PsychologicalNeed(
        name="need_for_loss_prevention",
        description="Drive to prevent losses, stronger than equivalent gain seeking (loss aversion)",
        academic_source="Kahneman & Tversky (1979)",
        domain="motivational",
    ),
    "need_for_reciprocation": PsychologicalNeed(
        name="need_for_reciprocation",
        description="Obligation to return favors and maintain balanced social exchange",
        academic_source="Gouldner (1960); Cialdini (2001)",
        domain="social",
    ),
    "need_for_immediacy": PsychologicalNeed(
        name="need_for_immediacy",
        description="Preference for immediate gratification over delayed rewards",
        academic_source="Ainslie (1975); Frederick et al. (2002)",
        domain="motivational",
    ),
}


# =============================================================================
# PROCESSING ROUTES
# =============================================================================

PROCESSING_ROUTES: Dict[str, ProcessingRoute] = {
    "central_route": ProcessingRoute(
        name="central_route",
        description="Deep, systematic evaluation of arguments and evidence",
        depth="deep",
        academic_source="Petty & Cacioppo (1986) — ELM",
    ),
    "peripheral_route": ProcessingRoute(
        name="peripheral_route",
        description="Shallow, heuristic-based processing using cues",
        depth="shallow",
        academic_source="Petty & Cacioppo (1986) — ELM",
    ),
    "experiential_route": ProcessingRoute(
        name="experiential_route",
        description="Affective, embodied, sensory-driven processing",
        depth="moderate",
        academic_source="Epstein (1994) — CEST; Damasio (1994) — Somatic Markers",
    ),
    "narrative_route": ProcessingRoute(
        name="narrative_route",
        description="Story-based processing via transportation and identification",
        depth="moderate",
        academic_source="Green & Brock (2000) — Narrative Transportation Theory",
    ),
    "automatic_route": ProcessingRoute(
        name="automatic_route",
        description="Fast, automatic, System 1 processing with minimal deliberation",
        depth="shallow",
        academic_source="Kahneman (2011) — System 1",
    ),
}


# =============================================================================
# CONTEXT CONDITIONS
# =============================================================================

CONTEXT_CONDITIONS: Dict[str, ContextCondition] = {
    "time_pressure": ContextCondition(
        name="time_pressure",
        condition_type="temporal",
        description="Limited time for decision; urgency present",
        academic_source="Maule et al. (2000)",
    ),
    "high_involvement": ContextCondition(
        name="high_involvement",
        condition_type="product",
        description="Product/decision is personally important and consequential",
        academic_source="Zaichkowsky (1985)",
    ),
    "low_involvement": ContextCondition(
        name="low_involvement",
        condition_type="product",
        description="Product/decision is routine and low consequence",
        academic_source="Zaichkowsky (1985)",
    ),
    "social_visibility": ContextCondition(
        name="social_visibility",
        condition_type="social",
        description="Purchase/choice is visible to others",
        academic_source="Berger & Heath (2007)",
    ),
    "information_overload": ContextCondition(
        name="information_overload",
        condition_type="cognitive",
        description="Too many options or too much information to process",
        academic_source="Iyengar & Lepper (2000)",
    ),
    "financial_risk": ContextCondition(
        name="financial_risk",
        condition_type="product",
        description="Significant financial commitment involved",
        academic_source="Mitchell (1999)",
    ),
    "mobile_context": ContextCondition(
        name="mobile_context",
        condition_type="channel",
        description="User is on a mobile device with limited screen and attention",
        academic_source="Ghose & Goldfarb (2006)",
    ),
    "repeat_exposure": ContextCondition(
        name="repeat_exposure",
        condition_type="temporal",
        description="User has seen similar ads/products before",
        academic_source="Berlyne (1970); Campbell & Keller (2003)",
    ),
    "novel_category": ContextCondition(
        name="novel_category",
        condition_type="product",
        description="User has no prior experience with this product category",
        academic_source="Alba & Hutchinson (1987)",
    ),
    "late_night_context": ContextCondition(
        name="late_night_context",
        condition_type="temporal",
        description="Late night viewing; ego depletion and reduced willpower",
        academic_source="Baumeister et al. (1998)",
    ),
}


# =============================================================================
# THEORETICAL LINKS (The Connective Tissue)
#
# These are the causal edges extracted from the 30 atom implementations.
# Each encodes a theoretical relationship grounded in psychological science.
# =============================================================================

THEORETICAL_LINKS: List[TheoreticalLink] = [
    # =========================================================================
    # LOW UNCERTAINTY TOLERANCE chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="low_uncertainty_tolerance",
        target_type="PsychologicalNeed",
        target_name="need_for_closure",
        strength=0.85,
        theory="Low uncertainty tolerance creates an urgent need for definite answers, "
               "driving the individual toward any source of certainty",
        citation="Kruglanski & Webster (1996)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="low_uncertainty_tolerance",
        target_type="PsychologicalNeed",
        target_name="need_for_safety",
        strength=0.70,
        theory="Ambiguity aversion generates risk-avoidance behavior and preference for safe options",
        citation="Ellsberg (1961); Fox & Tversky (1995)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_closure",
        target_type="CognitiveMechanism",
        target_name="authority",
        strength=0.80,
        theory="Authority provides the definitive answer that resolves ambiguity. "
               "Expert endorsement closes the information gap.",
        citation="Cialdini (2001); Kruglanski et al. (2006)",
        mediator="need_for_closure",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_closure",
        target_type="CognitiveMechanism",
        target_name="social_proof",
        strength=0.75,
        theory="When uncertain, people look to others' behavior as evidence. "
               "Social proof provides closure through consensus.",
        citation="Cialdini (2001); Deutsch & Gerard (1955)",
        mediator="need_for_closure",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_closure",
        target_type="CognitiveMechanism",
        target_name="commitment",
        strength=0.70,
        theory="Commitment devices reduce future uncertainty by locking in decisions. "
               "Consistency pressure resolves ambiguity.",
        citation="Cialdini (2001); Festinger (1957)",
        mediator="need_for_closure",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_safety",
        target_type="CognitiveMechanism",
        target_name="commitment",
        strength=0.75,
        theory="Safety-seeking individuals respond to guarantees and commitment "
               "devices that reduce downside risk",
        citation="Kahneman & Tversky (1979); Cialdini (2001)",
    ),

    # =========================================================================
    # HIGH COGNITIVE ENGAGEMENT chains
    # =========================================================================
    TheoreticalLink(
        link_type="ACTIVATES_ROUTE",
        source_type="PsychologicalState",
        source_name="high_cognitive_engagement",
        target_type="ProcessingRoute",
        target_name="central_route",
        strength=0.85,
        theory="High elaboration motivation activates the central route; "
               "the individual scrutinizes argument quality",
        citation="Petty & Cacioppo (1986)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="central_route",
        target_type="CognitiveMechanism",
        target_name="authority",
        strength=0.80,
        theory="Central-route processing demands substantive evidence; "
               "authority must be backed by real expertise, not mere heuristic cues",
        citation="Petty & Cacioppo (1986); Hovland et al. (1953)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="central_route",
        target_type="CognitiveMechanism",
        target_name="commitment",
        strength=0.70,
        theory="Under central processing, commitment must be grounded in "
               "genuine consistency, not superficial foot-in-the-door",
        citation="Petty & Cacioppo (1986); Cialdini (2001)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_cognitive_engagement",
        target_type="PsychologicalNeed",
        target_name="need_for_competence",
        strength=0.65,
        theory="Cognitively engaged individuals want to feel they made a well-informed decision",
        citation="Deci & Ryan (1985); Petty & Cacioppo (1986)",
    ),

    # =========================================================================
    # LOW COGNITIVE ENGAGEMENT chains
    # =========================================================================
    TheoreticalLink(
        link_type="ACTIVATES_ROUTE",
        source_type="PsychologicalState",
        source_name="low_cognitive_engagement",
        target_type="ProcessingRoute",
        target_name="peripheral_route",
        strength=0.85,
        theory="Low elaboration motivation activates peripheral processing; "
               "heuristic cues dominate over argument quality",
        citation="Petty & Cacioppo (1986)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="low_cognitive_engagement",
        target_type="PsychologicalNeed",
        target_name="need_for_cognitive_ease",
        strength=0.80,
        theory="Low engagement creates preference for easy, fluent processing; "
               "complexity is aversive",
        citation="Kahneman (2011); Alter & Oppenheimer (2009)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_cognitive_ease",
        target_type="CognitiveMechanism",
        target_name="social_proof",
        strength=0.80,
        theory="Social proof provides a low-effort heuristic: 'others chose this, so it must be good'",
        citation="Cialdini (2001); Kahneman (2011)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_cognitive_ease",
        target_type="CognitiveMechanism",
        target_name="scarcity",
        strength=0.65,
        theory="Scarcity heuristic shortcuts evaluation: 'if it's scarce, it must be valuable'",
        citation="Cialdini (2001); Lynn (1991)",
    ),

    # =========================================================================
    # HIGH SOCIAL CALIBRATION chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_social_calibration",
        target_type="PsychologicalNeed",
        target_name="need_for_social_validation",
        strength=0.85,
        theory="Individuals high in social calibration are deeply attuned to "
               "group norms and seek approval through conformity",
        citation="Cialdini & Goldstein (2004); Deutsch & Gerard (1955)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_social_calibration",
        target_type="PsychologicalNeed",
        target_name="need_for_belonging",
        strength=0.75,
        theory="Social attunement drives desire for group membership and inclusion",
        citation="Baumeister & Leary (1995)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_social_validation",
        target_type="CognitiveMechanism",
        target_name="social_proof",
        strength=0.90,
        theory="Social proof directly provides the group consensus signal "
               "that satisfies the need for validation",
        citation="Cialdini (2001)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_social_validation",
        target_type="CognitiveMechanism",
        target_name="mimetic_desire",
        strength=0.75,
        theory="Mimetic desire channels validation through specific admired others, "
               "not just statistical consensus",
        citation="Girard (1961); Gallese (2001)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_belonging",
        target_type="CognitiveMechanism",
        target_name="unity",
        strength=0.85,
        theory="Unity creates shared identity and in-group bonds that directly "
               "satisfy the need for belonging",
        citation="Cialdini (2016); Tajfel & Turner (1979)",
    ),

    # =========================================================================
    # HIGH STATUS SENSITIVITY chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_status_sensitivity",
        target_type="PsychologicalNeed",
        target_name="need_for_status_signaling",
        strength=0.85,
        theory="Status-sensitive individuals use consumption as a means of "
               "communicating social position",
        citation="Veblen (1899); Nelissen & Meijers (2011)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_status_sensitivity",
        target_type="PsychologicalNeed",
        target_name="need_for_identity_expression",
        strength=0.70,
        theory="Status-seeking is partly identity construction: the self is "
               "signaled through possessions",
        citation="Belk (1988); Reed et al. (2012)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_status_signaling",
        target_type="CognitiveMechanism",
        target_name="identity_construction",
        strength=0.80,
        theory="Identity construction helps the consumer build a desired self-image "
               "that signals status",
        citation="Belk (1988); Escalas & Bettman (2003)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_status_signaling",
        target_type="CognitiveMechanism",
        target_name="scarcity",
        strength=0.75,
        theory="Scarce items signal exclusivity and therefore status",
        citation="Lynn (1991); Gierl & Huettl (2010)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_status_signaling",
        target_type="CognitiveMechanism",
        target_name="mimetic_desire",
        strength=0.70,
        theory="Desire mediated through admired others directly channels status aspiration",
        citation="Girard (1961)",
    ),

    # =========================================================================
    # HIGH APPROACH chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_approach",
        target_type="PsychologicalNeed",
        target_name="need_for_stimulation",
        strength=0.70,
        theory="Approach-motivated individuals seek positive outcomes and rewarding experiences",
        citation="Carver & White (1994); Higgins (1997)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_stimulation",
        target_type="CognitiveMechanism",
        target_name="attention_dynamics",
        strength=0.75,
        theory="Novel, stimulating attention-grabbing content satisfies "
               "the need for arousal and excitement",
        citation="Berlyne (1960)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_stimulation",
        target_type="CognitiveMechanism",
        target_name="embodied_cognition",
        strength=0.65,
        theory="Sensory-rich, embodied content provides the visceral stimulation "
               "that arousal-seekers crave",
        citation="Barsalou (2008); Zuckerman (1994)",
    ),

    # =========================================================================
    # HIGH AVOIDANCE chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_avoidance",
        target_type="PsychologicalNeed",
        target_name="need_for_loss_prevention",
        strength=0.85,
        theory="Avoidance-motivated individuals are focused on preventing negative outcomes; "
               "loss looms larger than gain",
        citation="Kahneman & Tversky (1979); Higgins (1997)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_avoidance",
        target_type="PsychologicalNeed",
        target_name="need_for_safety",
        strength=0.80,
        theory="Avoidance motivation directly drives safety-seeking behavior",
        citation="Carver & White (1994)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_loss_prevention",
        target_type="CognitiveMechanism",
        target_name="commitment",
        strength=0.75,
        theory="Commitment devices (guarantees, money-back) directly address loss prevention",
        citation="Cialdini (2001); Kahneman & Tversky (1979)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_loss_prevention",
        target_type="CognitiveMechanism",
        target_name="authority",
        strength=0.70,
        theory="Expert authority reduces perceived risk by transferring "
               "responsibility to a credible source",
        citation="Cialdini (2001); Slovic (1987)",
    ),

    # =========================================================================
    # HIGH AROUSAL SEEKING chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_arousal_seeking",
        target_type="PsychologicalNeed",
        target_name="need_for_stimulation",
        strength=0.85,
        theory="Sensation seekers require high levels of novel stimulation "
               "to maintain optimal arousal",
        citation="Zuckerman (1994); Berlyne (1960)",
    ),
    TheoreticalLink(
        link_type="ACTIVATES_ROUTE",
        source_type="PsychologicalState",
        source_name="high_arousal_seeking",
        target_type="ProcessingRoute",
        target_name="experiential_route",
        strength=0.70,
        theory="High sensation seekers process experientially, driven by "
               "affect and bodily states rather than deliberation",
        citation="Epstein (1994); Zuckerman (1994)",
    ),

    # =========================================================================
    # LOW AROUSAL SEEKING chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="low_arousal_seeking",
        target_type="PsychologicalNeed",
        target_name="need_for_cognitive_consistency",
        strength=0.65,
        theory="Low-arousal individuals prefer consistency and predictability; "
               "novelty is aversive rather than exciting",
        citation="Berlyne (1960)",
    ),

    # =========================================================================
    # SHORT TEMPORAL HORIZON chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="short_temporal_horizon",
        target_type="PsychologicalNeed",
        target_name="need_for_immediacy",
        strength=0.85,
        theory="Present-biased individuals strongly discount future rewards "
               "and seek immediate gratification",
        citation="Ainslie (1975); Frederick et al. (2002)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_immediacy",
        target_type="CognitiveMechanism",
        target_name="scarcity",
        strength=0.80,
        theory="Scarcity creates urgency that aligns with present-focused motivation",
        citation="Cialdini (2001); Inman et al. (1997)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_immediacy",
        target_type="CognitiveMechanism",
        target_name="attention_dynamics",
        strength=0.65,
        theory="Attention-capturing content provides immediate engagement "
               "that satisfies present-focus",
        citation="Kahneman (1973)",
    ),

    # =========================================================================
    # LONG TEMPORAL HORIZON chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="long_temporal_horizon",
        target_type="PsychologicalNeed",
        target_name="need_for_identity_expression",
        strength=0.65,
        theory="Future-oriented individuals see purchases as investments in "
               "the person they want to become",
        citation="Hershfield (2011); Parfit (1984)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_identity_expression",
        target_type="CognitiveMechanism",
        target_name="identity_construction",
        strength=0.85,
        theory="Identity construction directly addresses the need to express "
               "and build the desired self",
        citation="Belk (1988); Escalas & Bettman (2003)",
    ),

    # =========================================================================
    # LOW SOCIAL CALIBRATION chains
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="low_social_calibration",
        target_type="PsychologicalNeed",
        target_name="need_for_autonomy",
        strength=0.75,
        theory="Socially independent individuals prize self-determination "
               "and resist social influence attempts",
        citation="Deci & Ryan (1985); Brehm (1966)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_autonomy",
        target_type="CognitiveMechanism",
        target_name="identity_construction",
        strength=0.75,
        theory="Identity construction frames the choice as self-expression, "
               "respecting autonomy rather than pressuring",
        citation="Deci & Ryan (1985); Belk (1988)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_autonomy",
        target_type="CognitiveMechanism",
        target_name="storytelling",
        strength=0.70,
        theory="Narrative transport persuades without triggering reactance "
               "because the individual draws their own conclusion",
        citation="Green & Brock (2000); Moyer-Guse (2008)",
    ),

    # =========================================================================
    # CROSS-DOMAIN: Identity Expression → Mechanisms
    # =========================================================================
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_narrative_coherence",
        target_type="CognitiveMechanism",
        target_name="storytelling",
        strength=0.85,
        theory="Narrative transport directly satisfies the need for life-story coherence",
        citation="McAdams (2001); Green & Brock (2000)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_reciprocation",
        target_type="CognitiveMechanism",
        target_name="reciprocity",
        strength=0.90,
        theory="Reciprocity norm: giving creates obligation to return the favor",
        citation="Cialdini (2001); Gouldner (1960)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_competence",
        target_type="CognitiveMechanism",
        target_name="authority",
        strength=0.65,
        theory="Expert-backed choices make the consumer feel competent — "
               "'I chose wisely because experts agree'",
        citation="Deci & Ryan (1985); Cialdini (2001)",
    ),
    TheoreticalLink(
        link_type="SATISFIED_BY",
        source_type="PsychologicalNeed",
        source_name="need_for_cognitive_consistency",
        target_type="CognitiveMechanism",
        target_name="commitment",
        strength=0.85,
        theory="Commitment leverages the consistency motive: prior actions "
               "create internal pressure to act consistently",
        citation="Festinger (1957); Cialdini (2001)",
    ),

    # =========================================================================
    # CONTEXT MODERATORS
    # =========================================================================
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="time_pressure",
        target_type="PsychologicalNeed",
        target_name="need_for_closure",
        strength=0.30,  # magnitude of moderating effect
        theory="Time pressure amplifies the need for closure by ~30%; "
               "decisions must be made quickly, increasing reliance on heuristics",
        citation="Kruglanski & Freund (1983); Maule et al. (2000)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="time_pressure",
        target_type="PsychologicalNeed",
        target_name="need_for_cognitive_ease",
        strength=0.25,
        theory="Time pressure increases preference for low-effort processing",
        citation="Maule et al. (2000); Payne et al. (1988)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="high_involvement",
        target_type="PsychologicalNeed",
        target_name="need_for_competence",
        strength=0.25,
        theory="High-involvement purchases amplify the need to feel competent "
               "and make a well-informed choice",
        citation="Zaichkowsky (1985); Petty & Cacioppo (1986)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="social_visibility",
        target_type="PsychologicalNeed",
        target_name="need_for_status_signaling",
        strength=0.35,
        theory="Visible purchases amplify status signaling by ~35%; "
               "the audience for the signal is present",
        citation="Berger & Heath (2007); Griskevicius et al. (2007)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="social_visibility",
        target_type="PsychologicalNeed",
        target_name="need_for_social_validation",
        strength=0.30,
        theory="Social visibility increases the salience of social judgment",
        citation="Berger & Heath (2007)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="information_overload",
        target_type="PsychologicalNeed",
        target_name="need_for_cognitive_ease",
        strength=0.40,
        theory="Information overload strongly amplifies the need for "
               "cognitive ease and simple heuristics",
        citation="Iyengar & Lepper (2000); Schwartz (2004)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="financial_risk",
        target_type="PsychologicalNeed",
        target_name="need_for_safety",
        strength=0.40,
        theory="Financial risk amplifies safety needs by ~40%; "
               "higher stakes increase loss aversion",
        citation="Kahneman & Tversky (1979); Mitchell (1999)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="mobile_context",
        target_type="PsychologicalNeed",
        target_name="need_for_cognitive_ease",
        strength=0.20,
        theory="Mobile context increases cognitive load due to smaller screen and distractions",
        citation="Ghose & Goldfarb (2006)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="novel_category",
        target_type="PsychologicalNeed",
        target_name="need_for_closure",
        strength=0.25,
        theory="Unfamiliar categories increase uncertainty and the need for closure",
        citation="Alba & Hutchinson (1987)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="repeat_exposure",
        target_type="PsychologicalNeed",
        target_name="need_for_stimulation",
        strength=-0.20,
        theory="Repeated exposure reduces novelty value, decreasing stimulation need",
        citation="Berlyne (1970); Campbell & Keller (2003)",
    ),
    TheoreticalLink(
        link_type="MODERATES",
        source_type="ContextCondition",
        source_name="late_night_context",
        target_type="PsychologicalNeed",
        target_name="need_for_cognitive_ease",
        strength=0.30,
        theory="Ego depletion at night increases reliance on heuristic processing",
        citation="Baumeister et al. (1998)",
    ),

    # =========================================================================
    # PROCESSING ROUTE → MECHANISM QUALITY REQUIREMENTS
    # =========================================================================
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="peripheral_route",
        target_type="CognitiveMechanism",
        target_name="social_proof",
        strength=0.85,
        theory="Social proof is the archetypal peripheral cue: "
               "number of users/reviews provides a quick heuristic",
        citation="Petty & Cacioppo (1986); Cialdini (2001)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="peripheral_route",
        target_type="CognitiveMechanism",
        target_name="scarcity",
        strength=0.75,
        theory="Scarcity cues function as peripheral signals of value "
               "without requiring deep evaluation",
        citation="Petty & Cacioppo (1986); Lynn (1991)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="experiential_route",
        target_type="CognitiveMechanism",
        target_name="embodied_cognition",
        strength=0.85,
        theory="Experiential processing is best served by sensory, bodily content",
        citation="Barsalou (2008); Epstein (1994)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="experiential_route",
        target_type="CognitiveMechanism",
        target_name="attention_dynamics",
        strength=0.70,
        theory="Experiential route leverages attention through vivid, "
               "affectively charged stimuli",
        citation="Epstein (1994); Kahneman (1973)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="narrative_route",
        target_type="CognitiveMechanism",
        target_name="storytelling",
        strength=0.90,
        theory="Narrative processing requires story structure: "
               "characters, conflict, resolution",
        citation="Green & Brock (2000); Escalas (2004)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="automatic_route",
        target_type="CognitiveMechanism",
        target_name="scarcity",
        strength=0.70,
        theory="Automatic processing leverages urgency triggers "
               "that bypass deliberation",
        citation="Kahneman (2011); Cialdini (2001)",
    ),
    TheoreticalLink(
        link_type="REQUIRES_QUALITY",
        source_type="ProcessingRoute",
        source_name="automatic_route",
        target_type="CognitiveMechanism",
        target_name="social_proof",
        strength=0.75,
        theory="'Everyone does it' is a classic System 1 heuristic",
        citation="Kahneman (2011); Cialdini (2001)",
    ),

    # =========================================================================
    # HIGH UNCERTAINTY TOLERANCE chains (the exploration-oriented)
    # =========================================================================
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_uncertainty_tolerance",
        target_type="PsychologicalNeed",
        target_name="need_for_stimulation",
        strength=0.60,
        theory="Ambiguity-tolerant individuals enjoy exploration and novel options",
        citation="Budner (1962); Heath & Tversky (1991)",
    ),
    TheoreticalLink(
        link_type="CREATES_NEED",
        source_type="PsychologicalState",
        source_name="high_uncertainty_tolerance",
        target_type="PsychologicalNeed",
        target_name="need_for_identity_expression",
        strength=0.55,
        theory="Ambiguity tolerance enables identity exploration through novel choices",
        citation="Budner (1962)",
    ),
]


# =============================================================================
# NEO4J POPULATION
# =============================================================================

def get_theory_graph_constraints() -> List[str]:
    """Return Cypher statements to create constraints and indexes for theory graph."""
    return [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (ps:PsychologicalState) REQUIRE ps.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (pn:PsychologicalNeed) REQUIRE pn.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:ProcessingRoute) REQUIRE pr.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (cc:ContextCondition) REQUIRE cc.name IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (ps:PsychologicalState) ON (ps.ndf_dimension)",
        "CREATE INDEX IF NOT EXISTS FOR (pn:PsychologicalNeed) ON (pn.domain)",
        "CREATE INDEX IF NOT EXISTS FOR (cc:ContextCondition) ON (cc.condition_type)",
    ]


def populate_theory_graph(session) -> Dict[str, int]:
    """
    Populate the theory graph in Neo4j.

    Creates:
    1. PsychologicalState nodes (14 — 7 NDF dimensions × 2 poles)
    2. PsychologicalNeed nodes (15 motivational needs)
    3. ProcessingRoute nodes (5 cognitive processing pathways)
    4. ContextCondition nodes (10 situational moderators)
    5. Theoretical edges: CREATES_NEED, SATISFIED_BY, ACTIVATES_ROUTE,
       REQUIRES_QUALITY, MODERATES

    Returns a dict of counts: {node_type: count, edge_type: count}
    """
    counts = {}

    # --- Constraints ---
    for cypher in get_theory_graph_constraints():
        try:
            session.run(cypher)
        except Exception as e:
            logger.debug(f"Constraint note: {e}")

    # --- PsychologicalState nodes ---
    state_data = [
        {
            "name": s.name,
            "ndf_dimension": s.ndf_dimension,
            "pole": s.pole,
            "threshold": s.threshold,
            "description": s.description,
            "academic_source": s.academic_source,
        }
        for s in PSYCHOLOGICAL_STATES.values()
    ]
    result = session.run(
        """
        UNWIND $states AS s
        MERGE (ps:PsychologicalState {name: s.name})
        SET ps.ndf_dimension = s.ndf_dimension,
            ps.pole = s.pole,
            ps.threshold = s.threshold,
            ps.description = s.description,
            ps.academic_source = s.academic_source,
            ps.updated_at = datetime()
        RETURN count(ps) AS cnt
        """,
        states=state_data,
    )
    counts["PsychologicalState"] = result.single()["cnt"]
    logger.info(f"Created {counts['PsychologicalState']} PsychologicalState nodes")

    # --- PsychologicalNeed nodes ---
    need_data = [
        {
            "name": n.name,
            "description": n.description,
            "academic_source": n.academic_source,
            "domain": n.domain,
        }
        for n in PSYCHOLOGICAL_NEEDS.values()
    ]
    result = session.run(
        """
        UNWIND $needs AS n
        MERGE (pn:PsychologicalNeed {name: n.name})
        SET pn.description = n.description,
            pn.academic_source = n.academic_source,
            pn.domain = n.domain,
            pn.updated_at = datetime()
        RETURN count(pn) AS cnt
        """,
        needs=need_data,
    )
    counts["PsychologicalNeed"] = result.single()["cnt"]
    logger.info(f"Created {counts['PsychologicalNeed']} PsychologicalNeed nodes")

    # --- ProcessingRoute nodes ---
    route_data = [
        {
            "name": r.name,
            "description": r.description,
            "depth": r.depth,
            "academic_source": r.academic_source,
        }
        for r in PROCESSING_ROUTES.values()
    ]
    result = session.run(
        """
        UNWIND $routes AS r
        MERGE (pr:ProcessingRoute {name: r.name})
        SET pr.description = r.description,
            pr.depth = r.depth,
            pr.academic_source = r.academic_source,
            pr.updated_at = datetime()
        RETURN count(pr) AS cnt
        """,
        routes=route_data,
    )
    counts["ProcessingRoute"] = result.single()["cnt"]
    logger.info(f"Created {counts['ProcessingRoute']} ProcessingRoute nodes")

    # --- ContextCondition nodes ---
    context_data = [
        {
            "name": c.name,
            "condition_type": c.condition_type,
            "description": c.description,
            "academic_source": c.academic_source,
        }
        for c in CONTEXT_CONDITIONS.values()
    ]
    result = session.run(
        """
        UNWIND $contexts AS c
        MERGE (cc:ContextCondition {name: c.name})
        SET cc.condition_type = c.condition_type,
            cc.description = c.description,
            cc.academic_source = c.academic_source,
            cc.updated_at = datetime()
        RETURN count(cc) AS cnt
        """,
        contexts=context_data,
    )
    counts["ContextCondition"] = result.single()["cnt"]
    logger.info(f"Created {counts['ContextCondition']} ContextCondition nodes")

    # --- Theoretical Edges ---
    edge_counts = {
        "CREATES_NEED": 0,
        "SATISFIED_BY": 0,
        "ACTIVATES_ROUTE": 0,
        "REQUIRES_QUALITY": 0,
        "MODERATES": 0,
    }

    for link in THEORETICAL_LINKS:
        try:
            cypher = _build_link_cypher(link)
            params = _build_link_params(link)
            session.run(cypher, **params)
            edge_counts[link.link_type] = edge_counts.get(link.link_type, 0) + 1
        except Exception as e:
            logger.warning(f"Failed to create {link.link_type} edge "
                           f"{link.source_name} -> {link.target_name}: {e}")

    counts.update(edge_counts)
    total_edges = sum(edge_counts.values())
    logger.info(
        f"Created {total_edges} theoretical edges: "
        + ", ".join(f"{k}={v}" for k, v in edge_counts.items())
    )

    return counts


def _build_link_cypher(link: TheoreticalLink) -> str:
    """Build the Cypher MERGE statement for a theoretical link."""
    mediator_prop = ", r.mediator = $mediator" if link.mediator else ""
    return (
        f"MATCH (s:{link.source_type} {{name: $source_name}}) "
        f"MATCH (t:{link.target_type} {{name: $target_name}}) "
        f"MERGE (s)-[r:{link.link_type}]->(t) "
        f"SET r.strength = $strength, "
        f"    r.theory = $theory, "
        f"    r.citation = $citation, "
        f"    r.empirical_validation = $empirical_validation, "
        f"    r.observation_count = $observation_count, "
        f"    r.updated_at = datetime()"
        f"{mediator_prop}"
    )


def _build_link_params(link: TheoreticalLink) -> Dict[str, Any]:
    """Build the parameter dict for a theoretical link."""
    params = {
        "source_name": link.source_name,
        "target_name": link.target_name,
        "strength": link.strength,
        "theory": link.theory,
        "citation": link.citation,
        "empirical_validation": link.empirical_validation,
        "observation_count": link.observation_count,
    }
    if link.mediator:
        params["mediator"] = link.mediator
    return params


# =============================================================================
# QUERY HELPERS (for reasoning chain generator)
# =============================================================================

def get_chains_for_ndf_profile(
    session,
    ndf_profile: Dict[str, float],
    context_conditions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Given an NDF profile, traverse the theory graph to find all applicable
    inferential chains: State -> Need -> Mechanism.

    Returns a list of chain dicts, each containing the full reasoning path.
    """
    # Determine which psychological states are active
    active_states = []
    for state_name, state in PSYCHOLOGICAL_STATES.items():
        dim_value = ndf_profile.get(state.ndf_dimension, 0.5)
        if state.pole == "low" and dim_value < state.threshold:
            active_states.append(state_name)
        elif state.pole == "high" and dim_value > state.threshold:
            active_states.append(state_name)

    if not active_states:
        return []

    # Traverse theory graph: State -> Need -> Mechanism
    chains = session.run(
        """
        UNWIND $active_states AS state_name
        MATCH (ps:PsychologicalState {name: state_name})
              -[cn:CREATES_NEED]->(pn:PsychologicalNeed)
              -[sb:SATISFIED_BY]->(cm:CognitiveMechanism)
        OPTIONAL MATCH (ps)-[ar:ACTIVATES_ROUTE]->(pr:ProcessingRoute)
                       -[rq:REQUIRES_QUALITY]->(cm)
        OPTIONAL MATCH (cc:ContextCondition)-[mod:MODERATES]->(pn)
        WHERE cc.name IN $context_conditions OR $context_conditions IS NULL
        RETURN ps.name AS state,
               ps.ndf_dimension AS ndf_dimension,
               ps.pole AS pole,
               cn.strength AS state_need_strength,
               cn.theory AS state_need_theory,
               cn.citation AS state_need_citation,
               pn.name AS need,
               pn.domain AS need_domain,
               sb.strength AS need_mechanism_strength,
               sb.theory AS need_mechanism_theory,
               sb.citation AS need_mechanism_citation,
               sb.mediator AS mediator,
               sb.empirical_validation AS empirical_validation,
               sb.observation_count AS observation_count,
               cm.name AS mechanism,
               pr.name AS processing_route,
               ar.strength AS route_strength,
               rq.strength AS route_quality_strength,
               cc.name AS context_modifier,
               mod.strength AS modifier_strength
        ORDER BY cn.strength * sb.strength DESC
        """,
        active_states=active_states,
        context_conditions=context_conditions or [],
    )

    results = []
    for record in chains:
        chain = dict(record)
        # Calculate composite chain strength
        state_need = chain.get("state_need_strength", 0) or 0
        need_mech = chain.get("need_mechanism_strength", 0) or 0
        route_bonus = 0
        if chain.get("route_strength") and chain.get("route_quality_strength"):
            route_bonus = chain["route_strength"] * chain["route_quality_strength"] * 0.2
        modifier = chain.get("modifier_strength") or 0

        chain["composite_strength"] = state_need * need_mech + route_bonus
        chain["moderated_strength"] = chain["composite_strength"] * (1 + modifier)
        chain["empirical_validation"] = chain.get("empirical_validation", 0.5) or 0.5
        chain["observation_count"] = chain.get("observation_count", 0) or 0
        results.append(chain)

    return results


def get_processing_routes_for_state(
    session,
    state_name: str,
) -> List[Dict[str, Any]]:
    """Get processing routes activated by a psychological state."""
    result = session.run(
        """
        MATCH (ps:PsychologicalState {name: $state_name})
              -[ar:ACTIVATES_ROUTE]->(pr:ProcessingRoute)
        RETURN pr.name AS route,
               pr.depth AS depth,
               ar.strength AS activation_strength,
               ar.theory AS theory
        ORDER BY ar.strength DESC
        """,
        state_name=state_name,
    )
    return [dict(r) for r in result]


def get_context_modifiers(
    session,
    context_conditions: List[str],
) -> List[Dict[str, Any]]:
    """Get all moderating effects for given context conditions."""
    result = session.run(
        """
        UNWIND $conditions AS cond_name
        MATCH (cc:ContextCondition {name: cond_name})
              -[mod:MODERATES]->(pn:PsychologicalNeed)
        RETURN cc.name AS condition,
               pn.name AS affected_need,
               mod.strength AS modifier_strength,
               mod.theory AS theory
        ORDER BY abs(mod.strength) DESC
        """,
        conditions=context_conditions,
    )
    return [dict(r) for r in result]
