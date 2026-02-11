# =============================================================================
# ADAM Inferential Reasoning Chain Generator
# Location: adam/intelligence/graph/reasoning_chain_generator.py
# =============================================================================

"""
REASONING CHAIN GENERATOR

Given a user's NDF profile and context, traverses the theory graph to produce
an explicit inferential chain — the "why, how, and when" that no correlational
system can produce.

This is the core of ADAM's inferential intelligence. Where correlational systems
output "{mechanism: authority, score: 0.73}", ADAM outputs:

  "Authority is recommended (0.73) BECAUSE this user scores low on uncertainty
   tolerance (0.3), which CREATES a need for closure (Kruglanski 1996, link
   strength 0.85), which IS SATISFIED BY authority (Cialdini 2001, link strength
   0.80). Their high cognitive engagement (0.8) ACTIVATES the central processing
   route (Petty & Cacioppo 1986), which REQUIRES substantive evidence — so the
   authority claim must be backed by real expertise, not mere celebrity endorsement.
   Context: time pressure AMPLIFIES the closure need by +30%.

   Creative guidance: Lead with expert credentials, provide data, avoid hype."

Academic Foundations:
- KG-CoT: Chain-of-Thought reasoning over Knowledge Graphs
- Thagard (2000): Explanatory coherence scoring
- Borsboom (2017): Construct networks with causal traversal
- HyperCausalLP (2024): Mediated causal chains
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from adam.intelligence.graph.theory_schema import (
    PSYCHOLOGICAL_STATES,
    PSYCHOLOGICAL_NEEDS,
    PROCESSING_ROUTES,
    CONTEXT_CONDITIONS,
    THEORETICAL_LINKS,
    TheoreticalLink,
    get_chains_for_ndf_profile,
    get_processing_routes_for_state,
    get_context_modifiers,
)

logger = logging.getLogger(__name__)


# =============================================================================
# OUTPUT DATA STRUCTURES
# =============================================================================

@dataclass
class ChainStep:
    """A single step in an inferential chain."""
    step_type: str  # "state_observation", "need_activation", "mechanism_selection",
                    # "route_activation", "quality_requirement", "context_modifier"
    construct: str  # Name of the construct at this step
    value: Optional[float] = None  # NDF value, strength, etc.
    interpretation: str = ""  # Human-readable interpretation
    theory: str = ""  # Theoretical basis
    citation: str = ""  # Academic citation
    source: str = "theory_graph"  # Where this step came from
    link_strength: float = 0.0  # Strength of the link producing this step
    empirical_validation: float = 0.5  # How well validated by outcomes


@dataclass
class CreativeGuidance:
    """Actionable creative guidance derived from the reasoning chain."""
    what_to_say: List[str] = field(default_factory=list)
    what_not_to_say: List[str] = field(default_factory=list)
    tone: str = ""
    detail_level: str = ""  # "high", "moderate", "low"
    urgency_level: str = ""  # "high", "moderate", "low"
    social_framing: str = ""  # "individual", "group", "aspirational"
    why: str = ""  # Explanation of the creative direction


@dataclass
class InferentialChain:
    """
    A complete inferential reasoning chain.

    This is the primary output — the connective tissue that turns
    "30 independent assessments feeding into a score" into
    "a chain of reasoning that explains WHY this recommendation will work."
    """
    chain_id: str = ""
    request_id: str = ""

    # The chain itself
    steps: List[ChainStep] = field(default_factory=list)

    # Outcome
    recommended_mechanism: str = ""
    mechanism_score: float = 0.0

    # Creative guidance (the HOW)
    creative_guidance: CreativeGuidance = field(default_factory=CreativeGuidance)

    # Confidence metrics
    confidence: float = 0.0  # Overall chain confidence
    chain_strength: float = 0.0  # Product of link strengths
    empirical_support: float = 0.0  # Average empirical validation of links
    observation_count: int = 0  # Total observations backing this chain
    transferability_score: float = 0.0  # How portable is this chain?

    # Metadata
    active_states: List[str] = field(default_factory=list)
    active_needs: List[str] = field(default_factory=list)
    processing_route: str = ""
    context_modifiers: List[str] = field(default_factory=list)
    ndf_profile: Dict[str, float] = field(default_factory=dict)

    # For learning loop: store the theoretical link IDs used
    theoretical_link_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for API response."""
        return {
            "chain_id": self.chain_id,
            "request_id": self.request_id,
            "recommended_mechanism": self.recommended_mechanism,
            "mechanism_score": round(self.mechanism_score, 4),
            "confidence": round(self.confidence, 4),
            "chain_strength": round(self.chain_strength, 4),
            "empirical_support": round(self.empirical_support, 4),
            "transferability_score": round(self.transferability_score, 4),
            "observation_count": self.observation_count,
            "processing_route": self.processing_route,
            "active_states": self.active_states,
            "active_needs": self.active_needs,
            "context_modifiers": self.context_modifiers,
            "steps": [
                {
                    "step_type": s.step_type,
                    "construct": s.construct,
                    "value": round(s.value, 4) if s.value is not None else None,
                    "interpretation": s.interpretation,
                    "theory": s.theory,
                    "citation": s.citation,
                    "link_strength": round(s.link_strength, 4),
                    "empirical_validation": round(s.empirical_validation, 4),
                }
                for s in self.steps
            ],
            "creative_guidance": {
                "what_to_say": self.creative_guidance.what_to_say,
                "what_not_to_say": self.creative_guidance.what_not_to_say,
                "tone": self.creative_guidance.tone,
                "detail_level": self.creative_guidance.detail_level,
                "urgency_level": self.creative_guidance.urgency_level,
                "social_framing": self.creative_guidance.social_framing,
                "why": self.creative_guidance.why,
            },
        }

    def to_narrative(self) -> str:
        """Generate a human-readable narrative explanation of the chain."""
        if not self.steps:
            return f"Mechanism {self.recommended_mechanism} recommended (score: {self.mechanism_score:.2f})"

        parts = []
        parts.append(
            f"**{self.recommended_mechanism.replace('_', ' ').title()}** is recommended "
            f"(score: {self.mechanism_score:.2f}, confidence: {self.confidence:.2f})"
        )

        # Walk through steps
        for step in self.steps:
            if step.step_type == "state_observation":
                parts.append(
                    f"  BECAUSE this user scores {step.interpretation} on "
                    f"{step.construct.replace('_', ' ')} ({step.value:.2f})"
                )
            elif step.step_type == "need_activation":
                parts.append(
                    f"  which CREATES a {step.construct.replace('_', ' ')} "
                    f"({step.citation}, link strength {step.link_strength:.2f})"
                )
            elif step.step_type == "mechanism_selection":
                parts.append(
                    f"  which IS SATISFIED BY {step.construct.replace('_', ' ')} "
                    f"({step.citation}, link strength {step.link_strength:.2f})"
                )
            elif step.step_type == "route_activation":
                parts.append(
                    f"  Their profile ACTIVATES {step.construct.replace('_', ' ')} "
                    f"({step.citation})"
                )
            elif step.step_type == "quality_requirement":
                parts.append(
                    f"  which REQUIRES {step.interpretation}"
                )
            elif step.step_type == "context_modifier":
                direction = "amplifies" if step.value and step.value > 0 else "dampens"
                parts.append(
                    f"  Context: {step.construct.replace('_', ' ')} {direction} "
                    f"the effect ({step.citation})"
                )

        if self.creative_guidance.what_to_say:
            parts.append(f"\n  Creative guidance: {'; '.join(self.creative_guidance.what_to_say)}")
        if self.creative_guidance.what_not_to_say:
            parts.append(f"  Avoid: {'; '.join(self.creative_guidance.what_not_to_say)}")

        return "\n".join(parts)


# =============================================================================
# CREATIVE GUIDANCE GENERATION
# =============================================================================

# Mechanism → creative guidance templates
MECHANISM_CREATIVE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "authority": {
        "what_to_say": [
            "Lead with expert credentials and data",
            "Cite specific expertise and track record",
            "Provide evidence-backed claims",
        ],
        "what_not_to_say": [
            "Avoid vague claims without evidence",
            "Don't use celebrity endorsement without substance",
        ],
        "tone": "authoritative_confident",
    },
    "social_proof": {
        "what_to_say": [
            "Show popularity metrics (users, reviews, ratings)",
            "Feature testimonials from relatable peers",
            "Highlight community adoption",
        ],
        "what_not_to_say": [
            "Avoid implying the user is a follower",
            "Don't fabricate social evidence",
        ],
        "tone": "warm_inclusive",
    },
    "scarcity": {
        "what_to_say": [
            "Emphasize limited availability or time-bound offers",
            "Show real stock or deadline information",
            "Create genuine urgency with concrete numbers",
        ],
        "what_not_to_say": [
            "Avoid fake countdown timers or manufactured scarcity",
            "Don't trigger anxiety — frame as opportunity, not threat",
        ],
        "tone": "urgent_excited",
    },
    "commitment": {
        "what_to_say": [
            "Reference the user's prior actions or preferences",
            "Frame as consistent with their stated values",
            "Offer small first steps (foot-in-the-door)",
        ],
        "what_not_to_say": [
            "Avoid being manipulative about consistency",
            "Don't guilt-trip about past behavior",
        ],
        "tone": "steady_reliable",
    },
    "identity_construction": {
        "what_to_say": [
            "Frame the product as an expression of who they want to be",
            "Use aspirational but authentic self-imagery",
            "Connect product to personal values and identity",
        ],
        "what_not_to_say": [
            "Avoid implying their current identity is inadequate",
            "Don't be pretentious or exclusionary",
        ],
        "tone": "aspirational_personal",
    },
    "mimetic_desire": {
        "what_to_say": [
            "Show admired others who have chosen this",
            "Create aspirational social context",
            "Frame as joining a desirable in-group",
        ],
        "what_not_to_say": [
            "Avoid triggering envy or rivalry",
            "Don't make the user feel left behind",
        ],
        "tone": "aspirational_social",
    },
    "reciprocity": {
        "what_to_say": [
            "Lead with genuine value before asking anything",
            "Offer free content, samples, or useful information",
            "Create a feeling of generous exchange",
        ],
        "what_not_to_say": [
            "Avoid making the exchange feel transactional",
            "Don't create obligation anxiety",
        ],
        "tone": "generous_warm",
    },
    "unity": {
        "what_to_say": [
            "Emphasize shared identity and group belonging",
            "Use 'we' language and in-group markers",
            "Highlight community and collective values",
        ],
        "what_not_to_say": [
            "Avoid exclusionary or divisive framing",
            "Don't create us-vs-them dynamics unnecessarily",
        ],
        "tone": "communal_warm",
    },
    "storytelling": {
        "what_to_say": [
            "Use narrative structure: character, conflict, resolution",
            "Create emotional resonance through relatable stories",
            "Let the audience draw their own conclusion",
        ],
        "what_not_to_say": [
            "Avoid breaking the narrative with hard-sell interruptions",
            "Don't make the moral too heavy-handed",
        ],
        "tone": "narrative_engaging",
    },
    "attention_dynamics": {
        "what_to_say": [
            "Use vivid, novel, and surprising elements",
            "Create pattern interrupts and curiosity gaps",
            "Engage multiple senses",
        ],
        "what_not_to_say": [
            "Avoid clickbait that doesn't deliver",
            "Don't be shocking just for shock value",
        ],
        "tone": "dynamic_vivid",
    },
    "embodied_cognition": {
        "what_to_say": [
            "Use sensory language (feel, touch, taste, experience)",
            "Create embodied mental simulations",
            "Focus on the physical experience of using the product",
        ],
        "what_not_to_say": [
            "Avoid purely abstract or intellectual framing",
            "Don't over-intellectualize sensory products",
        ],
        "tone": "sensory_immersive",
    },
    "anchoring": {
        "what_to_say": [
            "Set a reference point before revealing the actual offer",
            "Use comparative pricing or value framing",
            "Establish expectations, then exceed them",
        ],
        "what_not_to_say": [
            "Avoid misleading anchor points",
            "Don't set unrealistic expectations",
        ],
        "tone": "confident_value_oriented",
    },
    "regulatory_focus": {
        "what_to_say": [
            "Match framing to regulatory orientation (gain vs. loss)",
            "For promotion: emphasize what they'll gain",
            "For prevention: emphasize what they'll avoid losing",
        ],
        "what_not_to_say": [
            "Avoid mismatched framing (gain language for prevention-focused)",
            "Don't mix gain and loss frames in the same message",
        ],
        "tone": "motivationally_aligned",
    },
    "temporal_construal": {
        "what_to_say": [
            "Match message abstraction to temporal distance",
            "Near future: concrete features and how-to",
            "Far future: abstract values and why-it-matters",
        ],
        "what_not_to_say": [
            "Avoid abstract language for immediate decisions",
            "Don't get concrete about distant-future benefits",
        ],
        "tone": "temporally_calibrated",
    },
}


def _generate_creative_guidance(
    mechanism: str,
    processing_route: str,
    active_needs: List[str],
    context_modifiers: List[str],
    ndf_profile: Dict[str, float],
) -> CreativeGuidance:
    """Generate creative guidance from the reasoning chain."""
    template = MECHANISM_CREATIVE_TEMPLATES.get(mechanism, {})

    what_to_say = list(template.get("what_to_say", []))
    what_not_to_say = list(template.get("what_not_to_say", []))
    tone = template.get("tone", "neutral")

    # Adjust based on processing route
    if processing_route == "central_route":
        detail_level = "high"
        what_to_say.append("Provide detailed evidence and substantive arguments")
        what_not_to_say.append("Avoid superficial heuristic cues without substance")
    elif processing_route == "peripheral_route":
        detail_level = "low"
        what_to_say.append("Keep it simple and use clear heuristic cues")
        what_not_to_say.append("Avoid complex arguments that overload peripheral processing")
    elif processing_route == "experiential_route":
        detail_level = "moderate"
        what_to_say.append("Engage the senses; create a felt experience")
    elif processing_route == "narrative_route":
        detail_level = "moderate"
        what_to_say.append("Tell a story; let the product emerge naturally from the narrative")
    else:
        detail_level = "moderate"

    # Urgency from context
    urgency_level = "moderate"
    if "time_pressure" in context_modifiers:
        urgency_level = "high"
    elif "need_for_immediacy" in active_needs:
        urgency_level = "high"
    elif "need_for_safety" in active_needs:
        urgency_level = "low"

    # Social framing from needs
    social_framing = "individual"
    if "need_for_social_validation" in active_needs or "need_for_belonging" in active_needs:
        social_framing = "group"
    elif "need_for_status_signaling" in active_needs:
        social_framing = "aspirational"

    # Reactance awareness
    ce = ndf_profile.get("cognitive_engagement", 0.5)
    sc = ndf_profile.get("social_calibration", 0.5)
    if ce > 0.7:
        what_not_to_say.append(
            "This user is analytically engaged — avoid obvious manipulation tactics"
        )

    # Build the why explanation
    need_names = [n.replace("need_for_", "").replace("_", " ") for n in active_needs]
    why_parts = [f"User needs: {', '.join(need_names)}." if need_names else ""]
    if processing_route:
        why_parts.append(
            f"Processing via {processing_route.replace('_', ' ')} — "
            f"detail level should be {detail_level}."
        )
    if context_modifiers:
        mod_names = [m.replace("_", " ") for m in context_modifiers]
        why_parts.append(f"Active context: {', '.join(mod_names)}.")

    return CreativeGuidance(
        what_to_say=what_to_say,
        what_not_to_say=what_not_to_say,
        tone=tone,
        detail_level=detail_level,
        urgency_level=urgency_level,
        social_framing=social_framing,
        why=" ".join(p for p in why_parts if p),
    )


# =============================================================================
# LOCAL (NON-NEO4J) CHAIN GENERATION
# =============================================================================

def _determine_active_states(ndf_profile: Dict[str, float]) -> List[str]:
    """Determine which psychological states are active given an NDF profile."""
    active = []
    for state_name, state in PSYCHOLOGICAL_STATES.items():
        dim_value = ndf_profile.get(state.ndf_dimension, 0.5)
        if state.pole == "low" and dim_value < state.threshold:
            active.append(state_name)
        elif state.pole == "high" and dim_value > state.threshold:
            active.append(state_name)
    return active


def _determine_active_context(context: Dict[str, Any]) -> List[str]:
    """Determine which context conditions are active."""
    active = []
    # Map common context signals to ContextCondition names
    if context.get("time_pressure") or context.get("urgency"):
        active.append("time_pressure")
    if context.get("involvement", 0) > 0.6 or context.get("high_involvement"):
        active.append("high_involvement")
    elif context.get("involvement", 0.5) < 0.3 or context.get("low_involvement"):
        active.append("low_involvement")
    if context.get("social_visibility") or context.get("visible_purchase"):
        active.append("social_visibility")
    if context.get("info_overload") or context.get("num_alternatives", 0) > 10:
        active.append("information_overload")
    if context.get("financial_risk") or context.get("price", 0) > 100:
        active.append("financial_risk")
    if context.get("device") == "mobile" or context.get("mobile"):
        active.append("mobile_context")
    if context.get("exposure_count", 0) > 2:
        active.append("repeat_exposure")
    if context.get("novel_category") or context.get("category_experience", 1.0) < 0.2:
        active.append("novel_category")
    hour = context.get("hour")
    if hour is not None and (hour >= 22 or hour <= 5):
        active.append("late_night_context")
    return active


def _build_local_link_index() -> Dict[str, List[TheoreticalLink]]:
    """Build an index of theoretical links by source_name for fast lookup."""
    index = defaultdict(list)
    for link in THEORETICAL_LINKS:
        index[link.source_name].append(link)
    return index


_LINK_INDEX: Optional[Dict[str, List[TheoreticalLink]]] = None


def _get_link_index() -> Dict[str, List[TheoreticalLink]]:
    global _LINK_INDEX
    if _LINK_INDEX is None:
        _LINK_INDEX = _build_local_link_index()
    return _LINK_INDEX


def generate_chains_local(
    ndf_profile: Dict[str, float],
    context: Optional[Dict[str, Any]] = None,
    archetype: str = "",
    category: str = "",
    request_id: str = "",
    top_k: int = 5,
) -> List[InferentialChain]:
    """
    Generate inferential chains using local data (no Neo4j required).

    This is the primary chain generation method. It traverses the in-memory
    theory graph (THEORETICAL_LINKS) to produce chains with full provenance.

    Works without Neo4j by traversing the static theory data in theory_schema.py.
    When Neo4j is available, use generate_chains_neo4j() for additional
    empirical validation data.

    Args:
        ndf_profile: 7 NDF dimensions (0-1 scale)
        context: Optional context dict (device, time, category, etc.)
        archetype: Customer archetype (if known)
        category: Product category
        request_id: For traceability
        top_k: Number of top chains to return

    Returns:
        List of InferentialChain objects, one per recommended mechanism,
        sorted by chain strength.
    """
    from uuid import uuid4

    context = context or {}
    link_index = _get_link_index()

    # Step 1: Determine active psychological states
    active_states = _determine_active_states(ndf_profile)
    if not active_states:
        logger.debug("No active psychological states for NDF profile — returning empty chains")
        return []

    # Step 2: Determine active context conditions
    active_context = _determine_active_context(context)

    # Step 3: Traverse State -> Need -> Mechanism
    # Collect all raw chains (one per unique state->need->mechanism path)
    raw_chains: List[Dict[str, Any]] = []

    for state_name in active_states:
        state = PSYCHOLOGICAL_STATES[state_name]
        dim_value = ndf_profile.get(state.ndf_dimension, 0.5)

        # Find CREATES_NEED links from this state
        creates_need_links = [
            l for l in link_index.get(state_name, [])
            if l.link_type == "CREATES_NEED"
        ]

        for cn_link in creates_need_links:
            need_name = cn_link.target_name

            # Find SATISFIED_BY links from this need
            satisfied_by_links = [
                l for l in link_index.get(need_name, [])
                if l.link_type == "SATISFIED_BY"
            ]

            for sb_link in satisfied_by_links:
                mechanism = sb_link.target_name

                # Find processing route for this state
                route_links = [
                    l for l in link_index.get(state_name, [])
                    if l.link_type == "ACTIVATES_ROUTE"
                ]

                # Find quality requirements for the mechanism from the route
                route_name = ""
                route_strength = 0.0
                quality_strength = 0.0
                route_quality_link = None
                for rl in route_links:
                    route_candidate = rl.target_name
                    # Check if this route has a REQUIRES_QUALITY to our mechanism
                    quality_links = [
                        l for l in link_index.get(route_candidate, [])
                        if l.link_type == "REQUIRES_QUALITY" and l.target_name == mechanism
                    ]
                    if quality_links:
                        route_name = route_candidate
                        route_strength = rl.strength
                        route_quality_link = quality_links[0]
                        quality_strength = route_quality_link.strength
                        break
                    elif not route_name:
                        # Even without quality match, note the route
                        route_name = route_candidate
                        route_strength = rl.strength

                # Collect context modifiers affecting this need
                modifier_links = [
                    l for l in THEORETICAL_LINKS
                    if l.link_type == "MODERATES"
                    and l.target_name == need_name
                    and l.source_name in active_context
                ]

                # Calculate composite chain strength
                base_strength = cn_link.strength * sb_link.strength
                route_bonus = route_strength * quality_strength * 0.2 if quality_strength > 0 else 0
                modifier_total = sum(ml.strength for ml in modifier_links)
                moderated_strength = base_strength * (1 + modifier_total) + route_bonus

                # Calculate NDF dimension distance from threshold (stronger signal = more extreme)
                if state.pole == "low":
                    signal_strength = max(0, state.threshold - dim_value) / state.threshold
                else:
                    signal_strength = max(0, dim_value - state.threshold) / (1 - state.threshold)
                signal_strength = min(1.0, signal_strength)

                # Weight by how strongly the NDF dimension is activated
                weighted_strength = moderated_strength * (0.5 + 0.5 * signal_strength)

                raw_chains.append({
                    "state_name": state_name,
                    "state": state,
                    "dim_value": dim_value,
                    "signal_strength": signal_strength,
                    "cn_link": cn_link,
                    "need_name": need_name,
                    "sb_link": sb_link,
                    "mechanism": mechanism,
                    "route_name": route_name,
                    "route_strength": route_strength,
                    "route_quality_link": route_quality_link,
                    "quality_strength": quality_strength,
                    "modifier_links": modifier_links,
                    "base_strength": base_strength,
                    "moderated_strength": moderated_strength,
                    "weighted_strength": weighted_strength,
                    "empirical_validation": sb_link.empirical_validation,
                    "observation_count": sb_link.observation_count,
                })

    if not raw_chains:
        return []

    # Step 4: Aggregate by mechanism (multiple paths may recommend the same mechanism)
    mechanism_chains: Dict[str, List[Dict]] = defaultdict(list)
    for rc in raw_chains:
        mechanism_chains[rc["mechanism"]].append(rc)

    # Step 5: Build InferentialChain objects
    chains = []
    for mechanism, paths in mechanism_chains.items():
        # Sort paths by weighted_strength, take the strongest as the primary chain
        paths.sort(key=lambda p: p["weighted_strength"], reverse=True)
        primary = paths[0]

        # Calculate aggregate mechanism score across all supporting paths
        # Use a diminishing returns formula: each additional path adds less
        total_strength = 0.0
        for i, p in enumerate(paths):
            weight = 1.0 / (1 + i * 0.5)  # diminishing: 1.0, 0.67, 0.5, 0.4 ...
            total_strength += p["weighted_strength"] * weight

        # Normalize to 0-1 range
        mechanism_score = min(1.0, total_strength)

        # Build steps
        steps = []

        # Step: State observation
        steps.append(ChainStep(
            step_type="state_observation",
            construct=primary["state_name"],
            value=primary["dim_value"],
            interpretation=(
                f"{'low' if primary['state'].pole == 'low' else 'high'} "
                f"(threshold: {primary['state'].threshold})"
            ),
            theory=primary["state"].description,
            citation=primary["state"].academic_source,
            source="ndf_profile",
            link_strength=primary["signal_strength"],
            empirical_validation=1.0,  # observed, not theoretical
        ))

        # Step: Need activation
        steps.append(ChainStep(
            step_type="need_activation",
            construct=primary["need_name"],
            value=primary["cn_link"].strength,
            interpretation=PSYCHOLOGICAL_NEEDS.get(
                primary["need_name"], PsychologicalNeed("", "", "")
            ).description if primary["need_name"] in PSYCHOLOGICAL_NEEDS else "",
            theory=primary["cn_link"].theory,
            citation=primary["cn_link"].citation,
            link_strength=primary["cn_link"].strength,
            empirical_validation=primary["cn_link"].empirical_validation,
        ))

        # Step: Mechanism selection
        steps.append(ChainStep(
            step_type="mechanism_selection",
            construct=mechanism,
            value=primary["sb_link"].strength,
            interpretation=primary["sb_link"].theory,
            theory=primary["sb_link"].theory,
            citation=primary["sb_link"].citation,
            link_strength=primary["sb_link"].strength,
            empirical_validation=primary["sb_link"].empirical_validation,
        ))

        # Step: Processing route (if applicable)
        if primary["route_name"]:
            route_info = PROCESSING_ROUTES.get(primary["route_name"])
            steps.append(ChainStep(
                step_type="route_activation",
                construct=primary["route_name"],
                value=primary["route_strength"],
                interpretation=route_info.description if route_info else "",
                theory=f"Processing depth: {route_info.depth}" if route_info else "",
                citation=route_info.academic_source if route_info else "",
                link_strength=primary["route_strength"],
            ))

        # Step: Quality requirement (if applicable)
        if primary["route_quality_link"]:
            steps.append(ChainStep(
                step_type="quality_requirement",
                construct=f"{primary['route_name']}_requires_{mechanism}",
                value=primary["quality_strength"],
                interpretation=(
                    f"{primary['route_name'].replace('_', ' ')} processing requires "
                    f"substantive {mechanism.replace('_', ' ')} execution"
                ),
                theory=primary["route_quality_link"].theory,
                citation=primary["route_quality_link"].citation,
                link_strength=primary["quality_strength"],
            ))

        # Steps: Context modifiers
        for ml in primary["modifier_links"]:
            cond = CONTEXT_CONDITIONS.get(ml.source_name)
            steps.append(ChainStep(
                step_type="context_modifier",
                construct=ml.source_name,
                value=ml.strength,
                interpretation=(
                    f"{'Amplifies' if ml.strength > 0 else 'Dampens'} "
                    f"{primary['need_name'].replace('_', ' ')} by "
                    f"{abs(ml.strength) * 100:.0f}%"
                ),
                theory=ml.theory,
                citation=ml.citation,
                link_strength=abs(ml.strength),
            ))

        # Calculate confidence
        link_strengths = [s.link_strength for s in steps if s.link_strength > 0]
        chain_strength = 1.0
        for ls in link_strengths:
            chain_strength *= ls
        # chain_strength is geometric product — normalize to be useful
        if link_strengths:
            chain_strength = chain_strength ** (1.0 / len(link_strengths))  # geometric mean

        empirical_vals = [
            s.empirical_validation for s in steps
            if s.empirical_validation > 0 and s.step_type != "state_observation"
        ]
        avg_empirical = sum(empirical_vals) / len(empirical_vals) if empirical_vals else 0.5

        # Confidence combines chain strength with empirical support
        confidence = chain_strength * 0.6 + avg_empirical * 0.4

        # Transferability: higher when the chain is purely theoretical
        # (not dependent on specific empirical context)
        total_obs = sum(p.get("observation_count", 0) for p in paths)
        # More observations = more validated but less transferable (context-specific)
        # Fewer observations = less validated but more transferable (theory-driven)
        transferability = 1.0 / (1 + total_obs / 100) if total_obs > 0 else 0.8

        # Generate creative guidance
        all_needs = list(set(p["need_name"] for p in paths))
        creative = _generate_creative_guidance(
            mechanism=mechanism,
            processing_route=primary["route_name"],
            active_needs=all_needs,
            context_modifiers=[ml.source_name for ml in primary["modifier_links"]],
            ndf_profile=ndf_profile,
        )

        # Build theoretical link keys for learning loop
        link_keys = []
        for p in paths:
            link_keys.append(f"CREATES_NEED:{p['state_name']}:{p['need_name']}")
            link_keys.append(f"SATISFIED_BY:{p['need_name']}:{mechanism}")

        chain = InferentialChain(
            chain_id=f"chain_{uuid4().hex[:12]}",
            request_id=request_id,
            steps=steps,
            recommended_mechanism=mechanism,
            mechanism_score=mechanism_score,
            creative_guidance=creative,
            confidence=confidence,
            chain_strength=chain_strength,
            empirical_support=avg_empirical,
            observation_count=total_obs,
            transferability_score=transferability,
            active_states=list(set(p["state_name"] for p in paths)),
            active_needs=all_needs,
            processing_route=primary["route_name"],
            context_modifiers=[ml.source_name for ml in primary["modifier_links"]],
            ndf_profile=ndf_profile,
            theoretical_link_keys=link_keys,
        )
        chains.append(chain)

    # Sort by mechanism_score descending, return top_k
    chains.sort(key=lambda c: c.mechanism_score, reverse=True)
    return chains[:top_k]


# =============================================================================
# NEO4J-BACKED CHAIN GENERATION (when graph is available)
# =============================================================================

def generate_chains_neo4j(
    session,
    ndf_profile: Dict[str, float],
    context: Optional[Dict[str, Any]] = None,
    archetype: str = "",
    category: str = "",
    request_id: str = "",
    top_k: int = 5,
) -> List[InferentialChain]:
    """
    Generate inferential chains by traversing the Neo4j theory graph.

    This method uses live graph traversal and incorporates empirical
    validation data (observation counts, updated link strengths) that
    reflect what the system has learned from outcomes.

    Falls back to generate_chains_local() if Neo4j traversal fails.
    """
    from uuid import uuid4

    context = context or {}
    active_context = _determine_active_context(context)

    try:
        graph_chains = get_chains_for_ndf_profile(
            session, ndf_profile, active_context or None
        )
    except Exception as e:
        logger.warning(f"Neo4j theory graph traversal failed, falling back to local: {e}")
        return generate_chains_local(
            ndf_profile, context, archetype, category, request_id, top_k
        )

    if not graph_chains:
        # Fall back to local if graph returned nothing
        return generate_chains_local(
            ndf_profile, context, archetype, category, request_id, top_k
        )

    # Group by mechanism
    mechanism_records: Dict[str, List[Dict]] = defaultdict(list)
    for rec in graph_chains:
        mechanism_records[rec["mechanism"]].append(rec)

    chains = []
    for mechanism, records in mechanism_records.items():
        records.sort(key=lambda r: r.get("moderated_strength", 0), reverse=True)
        primary = records[0]

        # Build steps from graph records
        steps = []
        steps.append(ChainStep(
            step_type="state_observation",
            construct=primary["state"],
            value=ndf_profile.get(primary.get("ndf_dimension", ""), 0.5),
            interpretation=f"{primary.get('pole', '')} pole",
            citation="",
            source="ndf_profile",
            link_strength=1.0,
            empirical_validation=1.0,
        ))
        steps.append(ChainStep(
            step_type="need_activation",
            construct=primary["need"],
            value=primary.get("state_need_strength", 0),
            theory=primary.get("state_need_theory", ""),
            citation=primary.get("state_need_citation", ""),
            link_strength=primary.get("state_need_strength", 0),
            empirical_validation=primary.get("empirical_validation", 0.5),
        ))
        steps.append(ChainStep(
            step_type="mechanism_selection",
            construct=mechanism,
            value=primary.get("need_mechanism_strength", 0),
            theory=primary.get("need_mechanism_theory", ""),
            citation=primary.get("need_mechanism_citation", ""),
            link_strength=primary.get("need_mechanism_strength", 0),
            empirical_validation=primary.get("empirical_validation", 0.5),
        ))
        if primary.get("processing_route"):
            steps.append(ChainStep(
                step_type="route_activation",
                construct=primary["processing_route"],
                value=primary.get("route_strength", 0),
                link_strength=primary.get("route_strength", 0),
            ))
        if primary.get("context_modifier"):
            steps.append(ChainStep(
                step_type="context_modifier",
                construct=primary["context_modifier"],
                value=primary.get("modifier_strength", 0),
                link_strength=abs(primary.get("modifier_strength", 0)),
            ))

        # Scores
        total_strength = sum(
            r.get("moderated_strength", 0) / (1 + i * 0.5)
            for i, r in enumerate(records)
        )
        mechanism_score = min(1.0, total_strength)

        link_strengths = [s.link_strength for s in steps if s.link_strength > 0]
        chain_strength = 1.0
        for ls in link_strengths:
            chain_strength *= ls
        if link_strengths:
            chain_strength = chain_strength ** (1.0 / len(link_strengths))

        avg_empirical = primary.get("empirical_validation", 0.5)
        total_obs = sum(r.get("observation_count", 0) for r in records)
        confidence = chain_strength * 0.6 + avg_empirical * 0.4
        transferability = 1.0 / (1 + total_obs / 100) if total_obs > 0 else 0.8

        all_needs = list(set(r["need"] for r in records if r.get("need")))
        creative = _generate_creative_guidance(
            mechanism=mechanism,
            processing_route=primary.get("processing_route", ""),
            active_needs=all_needs,
            context_modifiers=active_context,
            ndf_profile=ndf_profile,
        )

        link_keys = []
        for r in records:
            if r.get("state") and r.get("need"):
                link_keys.append(f"CREATES_NEED:{r['state']}:{r['need']}")
            if r.get("need"):
                link_keys.append(f"SATISFIED_BY:{r['need']}:{mechanism}")

        chain = InferentialChain(
            chain_id=f"chain_{uuid4().hex[:12]}",
            request_id=request_id,
            steps=steps,
            recommended_mechanism=mechanism,
            mechanism_score=mechanism_score,
            creative_guidance=creative,
            confidence=confidence,
            chain_strength=chain_strength,
            empirical_support=avg_empirical,
            observation_count=total_obs,
            transferability_score=transferability,
            active_states=list(set(r["state"] for r in records if r.get("state"))),
            active_needs=all_needs,
            processing_route=primary.get("processing_route", ""),
            context_modifiers=active_context,
            ndf_profile=ndf_profile,
            theoretical_link_keys=link_keys,
        )
        chains.append(chain)

    chains.sort(key=lambda c: c.mechanism_score, reverse=True)
    return chains[:top_k]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_chains(
    ndf_profile: Dict[str, float],
    context: Optional[Dict[str, Any]] = None,
    archetype: str = "",
    category: str = "",
    request_id: str = "",
    neo4j_session=None,
    top_k: int = 5,
) -> List[InferentialChain]:
    """
    Unified chain generation: uses Neo4j if available, falls back to local.
    """
    if neo4j_session is not None:
        return generate_chains_neo4j(
            neo4j_session, ndf_profile, context, archetype, category, request_id, top_k
        )
    return generate_chains_local(
        ndf_profile, context, archetype, category, request_id, top_k
    )


def get_best_chain(
    ndf_profile: Dict[str, float],
    context: Optional[Dict[str, Any]] = None,
    archetype: str = "",
    category: str = "",
    request_id: str = "",
    neo4j_session=None,
) -> Optional[InferentialChain]:
    """Get the single best inferential chain for a given profile."""
    chains = generate_chains(
        ndf_profile, context, archetype, category, request_id, neo4j_session, top_k=1
    )
    return chains[0] if chains else None
