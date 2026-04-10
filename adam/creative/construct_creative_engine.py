"""
Construct-to-Creative Reasoning Engine
========================================

Transforms activated psychological constructs into structured creative
specifications. This is the inferential creative generation path:

Instead of:
    mechanism="scarcity" → template="Only {quantity} left!"
    (correlational: mechanism → template lookup)

This engine does:
    constructs[decision_conflict, prevention_focus, ...] →
    graph edges[creative_implications] →
    CreativeSpec[frame, tone, style, cta, imagery, constraints] →
    personalized creative

The key difference: the creative spec is DERIVED from the psychological
science encoded in graph edges, not from a static template dictionary.

Each construct activation contributes creative_implications from:
1. The construct node itself (how does this construct affect creative?)
2. The causal edges (how do construct relationships affect creative?)
3. The mechanism edges (how does the construct→mechanism link constrain creative?)

These implications are fused with precision weighting by activation strength
and confidence, producing a complete CreativeSpec that is both psychologically
grounded and internally consistent.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CREATIVE SPEC OUTPUT
# =============================================================================

class MessageFrame(Enum):
    GAIN = "gain"
    LOSS = "loss"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class CreativeUrgency(Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class CreativeSpec:
    """
    Structured creative specification derived from psychological construct
    activations. This replaces ad-hoc parameter overrides with a comprehensive,
    research-grounded creative brief.
    """
    # Core framing
    message_frame: MessageFrame = MessageFrame.NEUTRAL
    frame_confidence: float = 0.0
    frame_reasoning: str = ""

    # Tone and style
    tone: str = "balanced"
    tone_descriptors: List[str] = field(default_factory=list)
    emotional_register: str = "moderate"  # "high_arousal", "moderate", "calm"
    formality_level: float = 0.5  # 0=casual, 1=formal

    # Visual/imagery guidance
    imagery_style: str = ""
    color_palette: str = ""
    visual_complexity: float = 0.5  # 0=minimal, 1=complex

    # Call-to-action
    cta_verbs: List[str] = field(default_factory=list)
    cta_urgency: CreativeUrgency = CreativeUrgency.NONE
    cta_framing: str = ""  # "discover", "protect", "join", etc.

    # Copy structure
    abstraction_level: float = 0.5  # 0=concrete/specific, 1=abstract/aspirational
    social_proof_intensity: float = 0.0
    evidence_emphasis: float = 0.5  # how much to lean on data/stats vs story
    personalization_depth: float = 0.5

    # Ethical constraints from vulnerability detection
    constraints: List[str] = field(default_factory=list)
    vulnerability_protections: List[str] = field(default_factory=list)

    # Provenance
    contributing_constructs: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_chain: str = ""

    def to_copy_params(self) -> Dict[str, Any]:
        """Convert to parameters usable by CopyGenerationService."""
        return {
            "gain_emphasis": 0.8 if self.message_frame == MessageFrame.GAIN
                else (0.2 if self.message_frame == MessageFrame.LOSS else 0.5),
            "abstraction_level": self.abstraction_level,
            "emotional_appeal": 0.8 if self.emotional_register == "high_arousal"
                else (0.3 if self.emotional_register == "calm" else 0.5),
            "urgency_level": {
                CreativeUrgency.NONE: 0.0,
                CreativeUrgency.LOW: 0.3,
                CreativeUrgency.MODERATE: 0.6,
                CreativeUrgency.HIGH: 0.9,
            }.get(self.cta_urgency, 0.0),
            "tone": self.tone,
            "cta_action": self.cta_verbs[0] if self.cta_verbs else None,
            "social_proof_intensity": self.social_proof_intensity,
            "formality": self.formality_level,
            "imagery": self.imagery_style,
            "color": self.color_palette,
            "constraints": self.constraints,
        }


# =============================================================================
# CONSTRUCT CREATIVE ENGINE
# =============================================================================

class ConstructCreativeEngine:
    """
    Transforms ConstructActivationProfile + graph edge creative_implications
    into a structured CreativeSpec.

    This is the inferential creative generation path:
    1. For each activated construct, read creative_implications from the graph
    2. Weight implications by activation strength * confidence
    3. Resolve conflicts (e.g., gain vs loss framing) using precision weighting
    4. Produce a coherent CreativeSpec with full provenance chain
    """

    def __init__(
        self,
        construct_registry: Optional[Dict] = None,
        edge_registry: Optional[Dict] = None,
    ):
        self._construct_registry = construct_registry
        self._edge_registry = edge_registry
        self._initialized = False

    def _ensure_registries(self):
        """Lazy-load registries if not provided."""
        if self._initialized:
            return
        try:
            if not self._construct_registry:
                from adam.dsp.construct_registry import build_construct_registry
                self._construct_registry = build_construct_registry()
            if not self._edge_registry:
                from adam.dsp.edge_registry import build_edge_registry
                self._edge_registry = build_edge_registry()
        except ImportError:
            self._construct_registry = self._construct_registry or {}
            self._edge_registry = self._edge_registry or {}
        self._initialized = True

    def derive_creative_spec(
        self,
        construct_activations: Dict[str, Any],
        mechanism_priors: Optional[Dict[str, float]] = None,
        vulnerability_flags: Optional[List[str]] = None,
    ) -> CreativeSpec:
        """
        Derive a CreativeSpec from activated constructs and their graph edges.

        Args:
            construct_activations: {construct_id: ConstructActivation} or
                {construct_id: {"activation": float, "confidence": float, ...}}
            mechanism_priors: Graph-inferred mechanism priors
            vulnerability_flags: Detected vulnerability states requiring protection

        Returns:
            CreativeSpec with full provenance chain
        """
        self._ensure_registries()
        spec = CreativeSpec()

        if not construct_activations:
            return spec

        # Step 1: Collect creative implications from all active constructs
        implications = self._collect_implications(construct_activations)

        # Step 2: Resolve message framing from construct implications
        self._resolve_framing(spec, implications, construct_activations)

        # Step 3: Derive tone and emotional register
        self._resolve_tone(spec, implications, construct_activations)

        # Step 4: Derive CTA guidance
        self._resolve_cta(spec, implications, mechanism_priors)

        # Step 5: Derive visual/imagery guidance
        self._resolve_imagery(spec, implications)

        # Step 6: Derive copy structure parameters
        self._resolve_structure(spec, implications, construct_activations)

        # Step 7: Apply vulnerability protections
        if vulnerability_flags:
            self._apply_vulnerability_protections(spec, vulnerability_flags)

        # Set provenance
        spec.contributing_constructs = list(construct_activations.keys())[:20]
        spec.confidence = self._compute_overall_confidence(construct_activations)
        spec.reasoning_chain = self._build_reasoning_chain(
            construct_activations, implications
        )

        return spec

    # =========================================================================
    # STEP 1: Collect creative implications from graph
    # =========================================================================

    def _collect_implications(
        self,
        construct_activations: Dict[str, Any],
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        """
        Collect (creative_implication, weight, source) from construct nodes
        and their causal edges.

        Returns: List of (implication_dict, weight, source_description)
        """
        implications = []

        for construct_id, activation in construct_activations.items():
            # Get activation strength and confidence
            if hasattr(activation, "activation"):
                act_strength = activation.activation
                act_confidence = activation.confidence
            elif isinstance(activation, dict):
                act_strength = activation.get("activation", 0.5)
                act_confidence = activation.get("confidence", 0.5)
            else:
                act_strength = 0.5
                act_confidence = 0.5

            weight = act_strength * act_confidence

            # 1. Creative implications from construct node
            construct_def = self._construct_registry.get(construct_id, {})
            node_creative = construct_def.get("creative_implications", {})
            if node_creative:
                implications.append((
                    node_creative,
                    weight,
                    f"construct:{construct_id}",
                ))

            # 2. Creative implications from causal edges involving this construct
            if self._edge_registry:
                for edge_id, edge in self._edge_registry.items():
                    source = edge.get("source", "")
                    target = edge.get("target", "")
                    if source == construct_id or target == construct_id:
                        edge_creative = edge.get("creative_implications", {})
                        if edge_creative:
                            # Edge implications weighted by edge effect size
                            effect_sizes = edge.get("effect_sizes", [])
                            edge_weight = weight * 0.7  # Edges contribute less
                            if effect_sizes:
                                edge_weight *= min(
                                    1.0, abs(effect_sizes[0].value)
                                )
                            implications.append((
                                edge_creative,
                                edge_weight,
                                f"edge:{edge_id}",
                            ))

        return implications

    # =========================================================================
    # STEP 2: Resolve message framing
    # =========================================================================

    def _resolve_framing(
        self,
        spec: CreativeSpec,
        implications: List[Tuple[Dict, float, str]],
        activations: Dict[str, Any],
    ):
        """Resolve gain vs loss framing from construct implications."""
        gain_weight = 0.0
        loss_weight = 0.0
        sources = []

        for impl, weight, source in implications:
            # Check for explicit frame guidance
            frame = impl.get("frame") or impl.get("message_frame")
            if frame:
                if "gain" in str(frame).lower() or "promotion" in str(frame).lower():
                    gain_weight += weight
                    sources.append(f"{source}→gain")
                elif "loss" in str(frame).lower() or "prevention" in str(frame).lower():
                    loss_weight += weight
                    sources.append(f"{source}→loss")

            # Check for style guidance that implies framing
            style = impl.get("style", "")
            if isinstance(style, str):
                if "aspirational" in style or "novel" in style:
                    gain_weight += weight * 0.5
                elif "security" in style or "caution" in style:
                    loss_weight += weight * 0.5

            # Check for sub-frames (e.g., regulatory fit implications)
            if "promotion_fit" in impl:
                gain_weight += weight * 0.8
            if "prevention_fit" in impl:
                loss_weight += weight * 0.8

        # Also consider direct construct activations
        for cid, act in activations.items():
            act_val = act.activation if hasattr(act, "activation") else (
                act.get("activation", 0.5) if isinstance(act, dict) else 0.5
            )
            if "promotion" in cid:
                gain_weight += act_val * 0.6
            elif "prevention" in cid:
                loss_weight += act_val * 0.6

        total = gain_weight + loss_weight
        if total > 0.1:
            gain_ratio = gain_weight / total
            if gain_ratio > 0.6:
                spec.message_frame = MessageFrame.GAIN
                spec.frame_confidence = gain_ratio
            elif gain_ratio < 0.4:
                spec.message_frame = MessageFrame.LOSS
                spec.frame_confidence = 1.0 - gain_ratio
            else:
                spec.message_frame = MessageFrame.MIXED
                spec.frame_confidence = 0.5

            spec.frame_reasoning = (
                f"Gain evidence: {gain_weight:.2f}, Loss evidence: {loss_weight:.2f}, "
                f"Sources: {', '.join(sources[:5])}"
            )

    # =========================================================================
    # STEP 3: Resolve tone
    # =========================================================================

    def _resolve_tone(
        self,
        spec: CreativeSpec,
        implications: List[Tuple[Dict, float, str]],
        activations: Dict[str, Any],
    ):
        """Derive tone, emotional register, and formality."""
        tone_votes: Dict[str, float] = {}
        formality_votes = []
        arousal_votes = []

        for impl, weight, source in implications:
            # Tone
            tone = impl.get("tone") or impl.get("imagery")
            if isinstance(tone, str):
                tone_votes[tone] = tone_votes.get(tone, 0) + weight

            # Color/style → tone
            color = impl.get("color", "")
            if isinstance(color, str):
                tone_votes[color] = tone_votes.get(color, 0) + weight * 0.5

            # Formality signals
            style = impl.get("style", "")
            if isinstance(style, str):
                if "professional" in style or "detailed" in style or "organized" in style:
                    formality_votes.append((0.8, weight))
                elif "casual" in style or "energetic" in style or "playful" in style:
                    formality_votes.append((0.2, weight))
                else:
                    formality_votes.append((0.5, weight))

        # Select dominant tone
        if tone_votes:
            spec.tone = max(tone_votes, key=tone_votes.get)
            spec.tone_descriptors = sorted(
                tone_votes, key=tone_votes.get, reverse=True
            )[:5]

        # Compute formality
        if formality_votes:
            total_weight = sum(w for _, w in formality_votes) or 1.0
            spec.formality_level = sum(
                v * w for v, w in formality_votes
            ) / total_weight

        # Emotional register from arousal constructs
        for cid, act in activations.items():
            act_val = act.activation if hasattr(act, "activation") else (
                act.get("activation", 0.5) if isinstance(act, dict) else 0.5
            )
            if "arousal" in cid or "excitement" in cid:
                arousal_votes.append(act_val)
            elif "calm" in cid or "contemplative" in cid:
                arousal_votes.append(1.0 - act_val)

        if arousal_votes:
            avg_arousal = sum(arousal_votes) / len(arousal_votes)
            if avg_arousal > 0.65:
                spec.emotional_register = "high_arousal"
            elif avg_arousal < 0.35:
                spec.emotional_register = "calm"
            else:
                spec.emotional_register = "moderate"

    # =========================================================================
    # STEP 4: Resolve CTA
    # =========================================================================

    def _resolve_cta(
        self,
        spec: CreativeSpec,
        implications: List[Tuple[Dict, float, str]],
        mechanism_priors: Optional[Dict[str, float]],
    ):
        """Derive CTA verbs, urgency, and framing from implications."""
        cta_candidates: Dict[str, float] = {}
        urgency_signals = []

        for impl, weight, source in implications:
            cta = impl.get("cta")
            if isinstance(cta, str):
                for verb in cta.replace(",", " ").split():
                    verb = verb.strip().lower()
                    if verb:
                        cta_candidates[verb] = cta_candidates.get(verb, 0) + weight
            elif isinstance(cta, list):
                for verb in cta:
                    cta_candidates[verb] = cta_candidates.get(verb, 0) + weight

            # Urgency signals
            if "scarcity" in str(impl).lower() or "urgency" in str(impl).lower():
                urgency_signals.append(weight)

        # CTA verbs ranked by weight
        if cta_candidates:
            spec.cta_verbs = sorted(
                cta_candidates, key=cta_candidates.get, reverse=True
            )[:5]

        # CTA framing from top verb category
        if spec.cta_verbs:
            top_verb = spec.cta_verbs[0]
            gain_verbs = {"discover", "achieve", "get", "unlock", "explore", "enjoy"}
            loss_verbs = {"protect", "secure", "save", "don't", "avoid", "prevent"}
            if top_verb in gain_verbs:
                spec.cta_framing = "aspirational"
            elif top_verb in loss_verbs:
                spec.cta_framing = "protective"
            else:
                spec.cta_framing = "action"

        # Urgency from mechanism priors
        if mechanism_priors:
            scarcity_prior = mechanism_priors.get("scarcity", 0)
            if scarcity_prior > 0.6:
                spec.cta_urgency = CreativeUrgency.HIGH
            elif scarcity_prior > 0.4:
                spec.cta_urgency = CreativeUrgency.MODERATE
            elif scarcity_prior > 0.2:
                spec.cta_urgency = CreativeUrgency.LOW

    # =========================================================================
    # STEP 5: Resolve imagery
    # =========================================================================

    def _resolve_imagery(
        self,
        spec: CreativeSpec,
        implications: List[Tuple[Dict, float, str]],
    ):
        """Derive visual/imagery guidance from implications."""
        imagery_votes: Dict[str, float] = {}
        color_votes: Dict[str, float] = {}

        for impl, weight, source in implications:
            imagery = impl.get("imagery")
            if isinstance(imagery, str):
                imagery_votes[imagery] = imagery_votes.get(imagery, 0) + weight

            color = impl.get("color")
            if isinstance(color, str):
                color_votes[color] = color_votes.get(color, 0) + weight

        if imagery_votes:
            spec.imagery_style = max(imagery_votes, key=imagery_votes.get)

        if color_votes:
            spec.color_palette = max(color_votes, key=color_votes.get)

    # =========================================================================
    # STEP 6: Resolve copy structure
    # =========================================================================

    def _resolve_structure(
        self,
        spec: CreativeSpec,
        implications: List[Tuple[Dict, float, str]],
        activations: Dict[str, Any],
    ):
        """Derive abstraction level, social proof, evidence emphasis."""
        # Abstraction from construal-related constructs
        for cid, act in activations.items():
            act_val = act.activation if hasattr(act, "activation") else (
                act.get("activation", 0.5) if isinstance(act, dict) else 0.5
            )
            if "construal" in cid or "abstract" in cid:
                spec.abstraction_level = max(spec.abstraction_level, act_val)
            elif "concrete" in cid or "detail" in cid:
                spec.abstraction_level = min(spec.abstraction_level, 1.0 - act_val)

        # Social proof from relevant constructs
        for cid, act in activations.items():
            act_val = act.activation if hasattr(act, "activation") else (
                act.get("activation", 0.5) if isinstance(act, dict) else 0.5
            )
            if "social" in cid or "conformity" in cid:
                spec.social_proof_intensity = max(
                    spec.social_proof_intensity, act_val
                )

        # Evidence emphasis from cognitive style constructs
        for cid, act in activations.items():
            act_val = act.activation if hasattr(act, "activation") else (
                act.get("activation", 0.5) if isinstance(act, dict) else 0.5
            )
            if "analytical" in cid or "need_for_cognition" in cid:
                spec.evidence_emphasis = max(spec.evidence_emphasis, act_val)
            elif "intuitive" in cid or "affect_heuristic" in cid:
                spec.evidence_emphasis = min(spec.evidence_emphasis, 1.0 - act_val)

    # =========================================================================
    # STEP 7: Vulnerability protections
    # =========================================================================

    def _apply_vulnerability_protections(
        self,
        spec: CreativeSpec,
        vulnerability_flags: List[str],
    ):
        """Apply ethical constraints for detected vulnerabilities."""
        for flag in vulnerability_flags:
            flag_lower = flag.lower() if isinstance(flag, str) else str(flag).lower()

            if "sleep" in flag_lower or "depletion" in flag_lower:
                spec.constraints.append("no_urgency_pressure")
                spec.cta_urgency = CreativeUrgency.NONE
                spec.vulnerability_protections.append(
                    f"Reduced urgency due to {flag}"
                )

            if "emotional_distress" in flag_lower:
                spec.constraints.append("empathetic_tone_only")
                spec.emotional_register = "calm"
                spec.vulnerability_protections.append(
                    f"Empathetic tone enforced due to {flag}"
                )

            if "fatigue" in flag_lower:
                spec.constraints.append("simplified_messaging")
                spec.abstraction_level = max(spec.abstraction_level, 0.7)
                spec.vulnerability_protections.append(
                    f"Simplified messaging due to {flag}"
                )

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _compute_overall_confidence(
        self,
        activations: Dict[str, Any],
    ) -> float:
        """Compute overall creative spec confidence from activation confidences."""
        confidences = []
        for act in activations.values():
            if hasattr(act, "confidence"):
                confidences.append(act.confidence)
            elif isinstance(act, dict):
                confidences.append(act.get("confidence", 0.5))
        return sum(confidences) / len(confidences) if confidences else 0.0

    def _build_reasoning_chain(
        self,
        activations: Dict[str, Any],
        implications: List[Tuple[Dict, float, str]],
    ) -> str:
        """Build human-readable reasoning chain for the creative spec."""
        parts = []

        # Top 3 contributing constructs
        sorted_acts = sorted(
            activations.items(),
            key=lambda x: (
                x[1].activation * x[1].confidence
                if hasattr(x[1], "activation")
                else x[1].get("activation", 0) * x[1].get("confidence", 0)
                if isinstance(x[1], dict)
                else 0
            ),
            reverse=True,
        )

        for cid, act in sorted_acts[:3]:
            act_val = act.activation if hasattr(act, "activation") else (
                act.get("activation", 0.5) if isinstance(act, dict) else 0.5
            )
            parts.append(f"{cid}({act_val:.2f})")

        chain = " + ".join(parts)

        # Top 3 implications
        top_impl = sorted(implications, key=lambda x: x[1], reverse=True)[:3]
        impl_sources = [src for _, _, src in top_impl]

        return f"Constructs: [{chain}] → Implications: [{', '.join(impl_sources)}]"


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[ConstructCreativeEngine] = None


def get_construct_creative_engine() -> ConstructCreativeEngine:
    """Get singleton construct creative engine."""
    global _engine
    if _engine is None:
        _engine = ConstructCreativeEngine()
    return _engine
