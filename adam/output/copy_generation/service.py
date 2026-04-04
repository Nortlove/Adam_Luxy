# =============================================================================
# ADAM Copy Generation Service
# Location: adam/output/copy_generation/service.py
# =============================================================================

"""
COPY GENERATION SERVICE

Generate personality-matched copy for text and audio.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter as PrometheusCounter, Histogram
    COPY_GENERATION_LATENCY = Histogram(
        'adam_copy_generation_seconds',
        'Time to generate ad copy',
        ['copy_type', 'mechanism']
    )
    COPY_VARIANTS_GENERATED = PrometheusCounter(
        'adam_copy_variants_generated_total',
        'Total copy variants generated',
        ['copy_type']
    )
    COPY_OPTIMIZATION_APPLIED = PrometheusCounter(
        'adam_copy_optimization_applied_total',
        'Psychological optimizations applied to copy',
        ['optimization_type']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from adam.output.copy_generation.models import (
    CopyType,
    CopyLength,
    VoiceGender,
    CopyRequest,
    TextVariant,
    AudioCopy,
    GeneratedCopy,
)
from adam.output.brand_intelligence import BrandIntelligenceService, BrandProfile
from adam.infrastructure.redis import ADAMRedisCache

# Integration with Psychological Intelligence
try:
    from adam.platform.constructs.service import PsychologicalConstructsService
    from adam.platform.constructs.models import ExtendedPsychologicalProfile
    CONSTRUCTS_AVAILABLE = True
except ImportError:
    CONSTRUCTS_AVAILABLE = False

try:
    from adam.signals.linguistic.service import LinguisticSignalService
    LINGUISTIC_AVAILABLE = True
except ImportError:
    LINGUISTIC_AVAILABLE = False

try:
    from adam.llm.service import LLMService
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# =============================================================================
# COPY TEMPLATES
# =============================================================================

# Mechanism-based templates
MECHANISM_TEMPLATES = {
    "scarcity": {
        "gain": "Only {quantity} left - get yours now!",
        "loss": "Don't miss out - only {quantity} remain!",
    },
    "social_proof": {
        "gain": "Join {count}+ happy customers",
        "loss": "Don't be left behind - {count}+ have already...",
    },
    "authority": {
        "gain": "Experts recommend {product}",
        "loss": "Experts warn against missing {product}",
    },
    "urgency": {
        "gain": "Act now for exclusive benefits",
        "loss": "Time is running out - act before it's too late",
    },
}

# Tone modifiers
TONE_MODIFIERS = {
    "energetic": {
        "exclamations": True,
        "power_words": ["amazing", "incredible", "exciting"],
    },
    "calm": {
        "exclamations": False,
        "power_words": ["quality", "reliable", "trusted"],
    },
    "warm": {
        "exclamations": False,
        "power_words": ["caring", "friendly", "welcoming"],
    },
    "professional": {
        "exclamations": False,
        "power_words": ["efficient", "effective", "proven"],
    },
}


# =============================================================================
# SERVICE
# =============================================================================

class CopyGenerationService:
    """
    Service for generating personality-matched copy.
    
    Enhancement #15: Personality-Matched Copy Generation
    
    Integrates with:
    - #27 Psychological Constructs for user profiling
    - Linguistic Signal Service for text analysis
    - Brand Intelligence for brand voice
    
    Uses the 9 cognitive mechanisms:
    1. Construal Level - Abstract vs concrete
    2. Regulatory Focus - Gains vs losses
    3. Automatic Evaluation - Pre-conscious responses
    4. Wanting-Liking Dissociation
    5. Mimetic Desire - Social proof
    6. Attention Dynamics - Novelty/salience
    7. Temporal Construal - Future self connection
    8. Identity Construction - Self-concept
    9. Evolutionary Adaptations - Primal triggers
    """
    
    def __init__(
        self,
        brand_service: Optional[BrandIntelligenceService] = None,
        cache: Optional[ADAMRedisCache] = None,
        constructs_service: Optional["PsychologicalConstructsService"] = None,
        linguistic_service: Optional["LinguisticSignalService"] = None,
        gradient_bridge=None,
    ):
        self.brand_service = brand_service
        self.cache = cache
        self.gradient_bridge = gradient_bridge
        
        # Psychological intelligence integration
        if CONSTRUCTS_AVAILABLE:
            self.constructs_service = constructs_service or PsychologicalConstructsService()
        else:
            self.constructs_service = None
            
        if LINGUISTIC_AVAILABLE:
            self.linguistic_service = linguistic_service or LinguisticSignalService()
        else:
            self.linguistic_service = None
        
        logger.info(
            f"CopyGenerationService initialized: "
            f"constructs={'yes' if self.constructs_service else 'no'}, "
            f"linguistic={'yes' if self.linguistic_service else 'no'}"
        )
    
    async def generate(
        self,
        request: CopyRequest,
    ) -> GeneratedCopy:
        """
        Generate copy based on request.
        
        This is a template-based generator. In production, would
        integrate with Claude for more sophisticated generation.
        """
        
        # Get brand profile if available
        brand = None
        if self.brand_service:
            brand = await self.brand_service.get_brand(request.brand_id)

        # =====================================================================
        # CONSTRUCT-TO-CREATIVE REASONING (Inferential Core)
        #
        # Instead of flat parameter overrides, we now use the
        # ConstructCreativeEngine to derive a full CreativeSpec from
        # graph-inferred construct activations. The spec encodes:
        #   message_frame, tone, CTA, imagery, constraints
        # all derived from validated psychological science in graph edges.
        # =====================================================================
        creative_spec = None
        try:
            from adam.creative.construct_creative_engine import (
                get_construct_creative_engine,
            )
            engine = get_construct_creative_engine()

            # Get construct activations from request
            construct_activations = {}
            if hasattr(request, "dsp_constructs") and request.dsp_constructs:
                construct_activations = request.dsp_constructs

            # Also check for graph-inferred activations
            if hasattr(request, "construct_activation_profile"):
                profile = request.construct_activation_profile
                if profile and hasattr(profile, "activations"):
                    construct_activations.update(profile.activations)

            if construct_activations:
                mechanism_priors = getattr(request, "graph_mechanism_priors", None)
                vulnerability_flags = getattr(request, "vulnerability_flags", None)

                creative_spec = engine.derive_creative_spec(
                    construct_activations=construct_activations,
                    mechanism_priors=mechanism_priors,
                    vulnerability_flags=vulnerability_flags,
                )

                if creative_spec and creative_spec.confidence > 0.1:
                    # Apply the full CreativeSpec to the request
                    spec_params = creative_spec.to_copy_params()
                    overrides = {
                        k: v for k, v in spec_params.items()
                        if v is not None and k in (
                            "gain_emphasis", "abstraction_level",
                            "emotional_appeal", "urgency_level", "tone",
                            "cta_action",
                        )
                    }
                    if overrides:
                        request = request.model_copy(update=overrides)

                    logger.debug(
                        f"CreativeSpec applied: frame={creative_spec.message_frame.value}, "
                        f"tone={creative_spec.tone}, "
                        f"confidence={creative_spec.confidence:.2f}, "
                        f"constructs={len(creative_spec.contributing_constructs)}"
                    )

        except ImportError:
            logger.debug("ConstructCreativeEngine not available — using legacy path")
        except Exception as e:
            logger.debug(f"Construct creative reasoning failed: {e}")

        # =====================================================================
        # CORPUS FUSION: Creative Pattern Constraints (Layer 2)
        #
        # Query the billion-review corpus for proven creative patterns
        # that successfully converted the target psychological profile.
        # These become structured constraints for generation — not literal
        # copy, but validated framing, mechanism, and emotional register.
        # =====================================================================
        corpus_constraints = None
        try:
            from adam.fusion.creative_patterns import get_creative_pattern_extractor

            extractor = get_creative_pattern_extractor()
            category = getattr(request, "product_category", None) or ""
            archetype = getattr(request, "target_archetype", None)
            platform = getattr(request, "platform", None)
            trait_profile = getattr(request, "user_trait_profile", None)

            if category:
                corpus_constraints = extractor.extract_creative_constraints(
                    category=category,
                    target_archetype=archetype,
                    target_trait_profile=trait_profile,
                    target_mechanism=(
                        request.mechanisms[0] if request.mechanisms else None
                    ),
                    platform=platform,
                )

                if corpus_constraints and corpus_constraints.overall_confidence > 0.1:
                    # Apply corpus-backed mechanism recommendations
                    if corpus_constraints.recommended_mechanisms and not request.mechanisms:
                        request = request.model_copy(update={
                            "mechanisms": corpus_constraints.recommended_mechanisms[:3]
                        })

                    # Merge framing guidance into request params
                    framing = corpus_constraints.recommended_framing
                    if framing:
                        framing_overrides = {}
                        if framing.regulatory_focus == "promotion":
                            framing_overrides["gain_emphasis"] = 0.75
                        elif framing.regulatory_focus == "prevention":
                            framing_overrides["gain_emphasis"] = 0.25
                        if framing.construal_level == "abstract":
                            framing_overrides["abstraction_level"] = 0.8
                        elif framing.construal_level == "concrete":
                            framing_overrides["abstraction_level"] = 0.2
                        if framing_overrides:
                            request = request.model_copy(update=framing_overrides)

                    logger.debug(
                        f"Corpus creative constraints applied: "
                        f"patterns={len(corpus_constraints.patterns)}, "
                        f"mechanisms={corpus_constraints.recommended_mechanisms[:3]}, "
                        f"confidence={corpus_constraints.overall_confidence:.2f}"
                    )

        except ImportError:
            logger.debug("Corpus fusion CreativePatternExtractor not available")
        except Exception as e:
            logger.debug(f"Corpus creative constraint extraction failed: {e}")

        # Store corpus constraints for prompt enrichment
        self._last_corpus_constraints = corpus_constraints

        # =====================================================================
        # LEGACY: DSP creative_implications parameter overrides (FALLBACK)
        # Used when ConstructCreativeEngine is not available or returns
        # low-confidence results.
        # =====================================================================
        if creative_spec is None or (creative_spec and creative_spec.confidence < 0.1):
            dsp_creative = {}
            if hasattr(request, "dsp_constructs") and request.dsp_constructs:
                for construct_id, construct_data in request.dsp_constructs.items():
                    ci = construct_data.get("creative_implications", {})
                    if ci:
                        dsp_creative.update(ci)

            overrides = {}
            if dsp_creative:
                frame_val = dsp_creative.get("frame") or dsp_creative.get("style")
                if frame_val == "gain":
                    overrides["gain_emphasis"] = 0.8
                elif frame_val == "loss":
                    overrides["gain_emphasis"] = 0.2

                if "imagery" in dsp_creative:
                    overrides["tone"] = dsp_creative["imagery"]
                elif "color" in dsp_creative:
                    overrides["tone"] = dsp_creative["color"]

                if "cta" in dsp_creative:
                    overrides["cta_action"] = dsp_creative["cta"]

            if overrides:
                request = request.model_copy(update=overrides)

        # =====================================================================
        # BILATERAL EDGE INTELLIGENCE: Direct copy parameter derivation
        #
        # When bilateral edge dimensions are available (from prefetch),
        # map them directly to copy generation parameters. This is more
        # precise than gradient priorities because it uses the actual
        # buyer×product alignment values rather than population gradients.
        #
        # Edge dims → copy params (high cognitive_elaboration → longer
        # copy + evidence; high emotional_resonance → shorter + visceral)
        # =====================================================================
        if hasattr(request, "edge_dimensions") and request.edge_dimensions:
            request = self._apply_edge_dimensions(request)

        # =====================================================================
        # GRADIENT PRIORITIES: Creative Direction from Gradient Field
        #
        # If gradient_priorities are provided (top 2-3 optimization
        # dimensions from the gradient bridge), use them to steer
        # framing, mechanism selection, and emphasis. This ensures
        # copy generation aligns with the dimensions that have the
        # highest marginal impact on conversion for this buyer.
        # =====================================================================
        if request.gradient_priorities:
            request = self._apply_gradient_priorities(request)

        # Generate primary text
        primary_text = self._generate_text(request, brand)
        
        # Generate variants
        variants = self._generate_variants(request, brand)
        
        # Generate audio if requested
        audio = None
        if request.include_audio:
            audio = self._generate_audio(request, primary_text, brand)
        
        return GeneratedCopy(
            request_id=request.request_id,
            user_id=request.user_id,
            brand_id=request.brand_id,
            primary_text=primary_text,
            text_variants=variants,
            audio=audio,
            copy_type=request.copy_type,
            length=request.length,
            framing_applied={
                "gain_emphasis": request.gain_emphasis,
                "abstraction": request.abstraction_level,
                "emotional": request.emotional_appeal,
                "urgency": request.urgency_level,
            },
            mechanisms_used=request.mechanisms,
            overall_confidence=0.6,
        )
    
    def _generate_text(
        self,
        request: CopyRequest,
        brand: Optional[BrandProfile],
    ) -> str:
        """Generate primary text."""
        
        parts = []
        
        # Headline/hook based on framing
        if request.gain_emphasis > 0.6:
            hook = self._gain_hook(request)
        elif request.gain_emphasis < 0.4:
            hook = self._loss_hook(request)
        else:
            hook = self._neutral_hook(request)
        parts.append(hook)
        
        # Body based on abstraction level
        if request.copy_type in [CopyType.BODY, CopyType.FULL_AD]:
            if request.abstraction_level > 0.6:
                body = self._abstract_body(request)
            else:
                body = self._concrete_body(request)
            parts.append(body)
        
        # CTA based on urgency
        if request.copy_type in [CopyType.CTA, CopyType.FULL_AD]:
            cta = self._generate_cta(request)
            parts.append(cta)
        
        text = " ".join(parts)
        
        # Apply tone modifiers
        text = self._apply_tone(text, request.tone)
        
        # Apply length constraints
        text = self._enforce_length(text, request.length)
        
        return text
    
    def _gain_hook(self, request: CopyRequest) -> str:
        """Generate gain-framed hook."""
        product = request.product_name or "this"
        return f"Discover the benefits of {product}."
    
    def _loss_hook(self, request: CopyRequest) -> str:
        """Generate loss-framed hook."""
        product = request.product_name or "this opportunity"
        return f"Don't miss out on {product}."
    
    def _neutral_hook(self, request: CopyRequest) -> str:
        """Generate neutral hook."""
        product = request.product_name or "our product"
        return f"Introducing {product}."
    
    def _abstract_body(self, request: CopyRequest) -> str:
        """Generate abstract/why-focused body."""
        return "Experience the difference and transform your approach."
    
    def _concrete_body(self, request: CopyRequest) -> str:
        """Generate concrete/how-focused body."""
        desc = request.product_description or "quality materials and expert design"
        return f"Built with {desc}."
    
    def _generate_cta(self, request: CopyRequest) -> str:
        """Generate call-to-action."""
        action = request.cta_action or "Learn more"
        
        if request.urgency_level > 0.7:
            return f"{action} now - limited time only!"
        elif request.urgency_level > 0.4:
            return f"{action} today."
        else:
            return f"{action}."
    
    def _apply_tone(self, text: str, tone: str) -> str:
        """Apply tone modifiers to text."""
        modifiers = TONE_MODIFIERS.get(tone, {})
        
        # Add exclamation if energetic
        if modifiers.get("exclamations") and not text.endswith("!"):
            text = text.rstrip(".") + "!"
        
        return text
    
    def _enforce_length(self, text: str, length: CopyLength) -> str:
        """Enforce length constraints."""
        words = text.split()
        
        max_words = {
            CopyLength.SHORT: 10,
            CopyLength.MEDIUM: 25,
            CopyLength.LONG: 50,
        }
        
        limit = max_words.get(length, 25)
        if len(words) > limit:
            words = words[:limit]
            text = " ".join(words)
            if not text.endswith((".", "!", "?")):
                text += "..."
        
        return text
    
    def _apply_edge_dimensions(self, request: CopyRequest) -> CopyRequest:
        """Map bilateral edge dimensions directly to copy parameters.

        This is the bridge between the 20-dimensional buyer×product
        psychological alignment and the concrete copy generation knobs.
        More precise than gradient priorities because it uses THIS buyer's
        actual alignment values, not population-level gradients.

        Key mappings:
          High cognitive_load_tolerance → longer copy, more evidence, complex arguments
          Low cognitive_load_tolerance → shorter copy, simple CTA, System 1 triggers
          High emotional_resonance → visceral language, shorter, emotional CTA
          High regulatory_fit → sharpen gain/loss framing confidence
          High construal_fit → strengthen abstract/concrete positioning
          High social_proof_sensitivity → lead with social proof
          High loss_aversion_intensity → loss-framed hook
          High narrative_transport → storytelling structure
          High autonomy_reactance → reduce urgency, emphasize choice
        """
        dims = request.edge_dimensions
        if not dims:
            return request

        overrides: Dict[str, Any] = {}
        new_mechanisms = list(request.mechanisms or [])

        # Cognitive load tolerance → copy complexity
        clt = dims.get("cognitive_load_tolerance")
        if clt is not None:
            if clt > 0.65:
                # User can handle complex arguments → longer copy
                overrides["abstraction_level"] = max(
                    request.abstraction_level, 0.6 + clt * 0.3
                )
            elif clt < 0.35:
                # Low tolerance → simple, short, action-oriented
                overrides["abstraction_level"] = min(request.abstraction_level, 0.3)

        # Emotional resonance → emotional register
        er = dims.get("emotional_resonance")
        if er is not None and er > 0.6:
            overrides["emotional_appeal"] = max(request.emotional_appeal, er)

        # Regulatory fit → sharpen gain/loss
        rf = dims.get("regulatory_fit")
        if rf is not None:
            if rf > 0.6:
                overrides["gain_emphasis"] = max(request.gain_emphasis, rf)
            elif rf < 0.4:
                overrides["gain_emphasis"] = min(request.gain_emphasis, rf)

        # Social proof sensitivity → add mechanism
        sps = dims.get("social_proof_sensitivity")
        if sps is not None and sps > 0.6 and "social_proof" not in new_mechanisms:
            new_mechanisms.append("social_proof")

        # Loss aversion → loss framing
        lai = dims.get("loss_aversion_intensity")
        if lai is not None and lai > 0.6:
            overrides["gain_emphasis"] = min(
                overrides.get("gain_emphasis", request.gain_emphasis), 0.25
            )

        # Narrative transport → storytelling
        nt = dims.get("narrative_transport")
        if nt is not None and nt > 0.6 and "storytelling" not in new_mechanisms:
            new_mechanisms.append("storytelling")

        # Autonomy reactance → reduce urgency
        ar = dims.get("autonomy_reactance")
        if ar is not None and ar > 0.6:
            overrides["urgency_level"] = min(request.urgency_level, 0.2)

        if new_mechanisms != list(request.mechanisms or []):
            overrides["mechanisms"] = new_mechanisms[:5]

        if overrides:
            request = request.model_copy(update=overrides)
            logger.debug(
                "Edge dimension copy params applied: %s", list(overrides.keys())
            )

        return request

    def _apply_gradient_priorities(self, request: CopyRequest) -> CopyRequest:
        """Apply gradient field priorities as creative direction constraints.

        Maps the top gradient dimensions to concrete copy generation
        parameters.  This is the bridge between "which psychological
        dimensions matter most for this buyer" and "how do we write
        the ad".

        Dimension -> copy parameter mapping:
          regulatory_fit       -> gain_emphasis (promotion vs prevention framing)
          emotional_resonance  -> emotional_appeal (raise emotional register)
          personality_alignment-> tone (match personality style)
          construal_fit        -> abstraction_level (abstract vs concrete)
          value_alignment      -> add "identity_construction" mechanism
          evolutionary_motive  -> add "evolutionary_adaptations" mechanism
          social_proof_sensitivity -> add "social_proof" mechanism
          loss_aversion_intensity -> shift toward loss framing
          narrative_transport  -> add "storytelling" mechanism
          autonomy_reactance   -> reduce urgency (avoid pressure)
        """
        priorities = request.gradient_priorities
        if not priorities:
            return request

        # Sort by weight descending — only act on top 3
        top = sorted(priorities.items(), key=lambda x: x[1], reverse=True)[:3]
        top_dims = {dim for dim, _ in top}

        overrides: Dict[str, Any] = {}
        new_mechanisms = list(request.mechanisms or [])

        for dim, weight in top:
            if dim == "regulatory_fit":
                # High gradient on regulatory_fit -> sharpen gain/loss framing
                overrides["gain_emphasis"] = max(0.75, request.gain_emphasis)
            elif dim == "emotional_resonance":
                overrides["emotional_appeal"] = max(0.7, request.emotional_appeal)
            elif dim == "construal_fit":
                # Push toward abstract framing when construal matters most
                overrides["abstraction_level"] = max(0.7, request.abstraction_level)
            elif dim == "personality_alignment":
                if request.tone == "neutral":
                    overrides["tone"] = "warm"
            elif dim == "value_alignment" and "identity_construction" not in new_mechanisms:
                new_mechanisms.append("identity_construction")
            elif dim == "evolutionary_motive" and "evolutionary_adaptations" not in new_mechanisms:
                new_mechanisms.append("evolutionary_adaptations")
            elif dim == "social_proof_sensitivity" and "social_proof" not in new_mechanisms:
                new_mechanisms.append("social_proof")
            elif dim == "loss_aversion_intensity":
                overrides["gain_emphasis"] = min(0.25, request.gain_emphasis)
            elif dim == "narrative_transport" and "storytelling" not in new_mechanisms:
                new_mechanisms.append("storytelling")
            elif dim == "autonomy_reactance":
                overrides["urgency_level"] = min(0.2, request.urgency_level)

        if new_mechanisms != list(request.mechanisms or []):
            overrides["mechanisms"] = new_mechanisms[:5]

        if overrides:
            request = request.model_copy(update=overrides)
            logger.debug(
                f"Gradient priorities applied: top_dims={list(top_dims)}, "
                f"overrides={list(overrides.keys())}"
            )

        return request

    def _generate_variants(
        self,
        request: CopyRequest,
        brand: Optional[BrandProfile],
    ) -> List[TextVariant]:
        """Generate text variants."""
        variants = []
        
        # Gain variant
        gain_request = request.model_copy()
        gain_request.gain_emphasis = 0.8
        variants.append(TextVariant(
            variant_id=f"var_{uuid4().hex[:8]}_gain",
            text=self._generate_text(gain_request, brand),
            framing="gain",
            confidence=0.6,
        ))
        
        # Loss variant
        loss_request = request.model_copy()
        loss_request.gain_emphasis = 0.2
        variants.append(TextVariant(
            variant_id=f"var_{uuid4().hex[:8]}_loss",
            text=self._generate_text(loss_request, brand),
            framing="loss",
            confidence=0.6,
        ))
        
        # Mechanism variants
        for mechanism in request.mechanisms[:2]:
            mech_text = self._apply_mechanism(
                self._generate_text(request, brand),
                mechanism,
                request,
            )
            variants.append(TextVariant(
                variant_id=f"var_{uuid4().hex[:8]}_{mechanism}",
                text=mech_text,
                framing="neutral",
                mechanism=mechanism,
                confidence=0.5,
            ))
        
        return variants
    
    def _apply_mechanism(
        self,
        text: str,
        mechanism: str,
        request: CopyRequest,
    ) -> str:
        """Apply mechanism-specific language."""
        templates = MECHANISM_TEMPLATES.get(mechanism, {})
        
        framing = "gain" if request.gain_emphasis > 0.5 else "loss"
        template = templates.get(framing)
        
        if template:
            # Simple substitution
            filled = template.format(
                quantity="few",
                count="10,000",
                product=request.product_name or "this",
            )
            return f"{filled} {text}"
        
        return text
    
    def _generate_audio(
        self,
        request: CopyRequest,
        text: str,
        brand: Optional[BrandProfile],
    ) -> AudioCopy:
        """Generate audio copy with SSML."""
        
        # Select voice based on preferences
        voice_id = self._select_voice(request, brand)
        
        # Generate SSML
        ssml = self._text_to_ssml(text, request)
        
        # Estimate duration (rough: 2.5 words per second)
        words = len(text.split())
        duration = words / 2.5
        
        return AudioCopy(
            audio_id=f"audio_{uuid4().hex[:8]}",
            plain_text=text,
            ssml=ssml,
            voice_id=voice_id,
            voice_gender=request.preferred_voice_gender,
            estimated_duration_seconds=duration,
            confidence=0.6,
        )
    
    def _select_voice(
        self,
        request: CopyRequest,
        brand: Optional[BrandProfile],
    ) -> str:
        """Select appropriate voice for audio."""
        
        # Voice ID format: provider_gender_style
        gender = request.preferred_voice_gender.value
        
        # Map tone to voice style
        tone = request.tone or "neutral"
        style_map = {
            "energetic": "upbeat",
            "calm": "gentle",
            "warm": "friendly",
            "professional": "news",
        }
        style = style_map.get(tone, "neutral")
        
        return f"polly_{gender}_{style}"
    
    def _text_to_ssml(
        self,
        text: str,
        request: CopyRequest,
    ) -> str:
        """Convert text to SSML for audio generation."""
        
        ssml_parts = ['<speak>']
        
        # Add prosody based on emotional appeal
        if request.emotional_appeal > 0.6:
            ssml_parts.append(f'<prosody rate="105%" pitch="+5%">')
        elif request.emotional_appeal < 0.4:
            ssml_parts.append(f'<prosody rate="95%">')
        
        # Add the text with appropriate breaks
        sentences = text.replace("!", "!<break time='300ms'/>")
        sentences = sentences.replace(".", ".<break time='200ms'/>")
        ssml_parts.append(sentences)
        
        # Close prosody if opened
        if request.emotional_appeal > 0.6 or request.emotional_appeal < 0.4:
            ssml_parts.append('</prosody>')
        
        ssml_parts.append('</speak>')
        
        return "".join(ssml_parts)
    
    # =========================================================================
    # PSYCHOLOGICAL OPTIMIZATION METHODS (Enhancement #15 + #27)
    # =========================================================================
    
    def optimize_for_user(
        self,
        request: CopyRequest,
        user_id: str,
        archetype: Optional[str] = None,
    ) -> CopyRequest:
        """
        Optimize copy request based on user's psychological profile.
        
        Integrates Enhancement #27 constructs to tune:
        - Gain/loss framing based on regulatory focus
        - Abstraction level based on NFC
        - Urgency based on temporal orientation
        - Social proof based on social susceptibility
        
        Args:
            request: Original copy request
            user_id: User to optimize for
            archetype: Optional archetype for cold start
            
        Returns:
            Optimized copy request
        """
        if not self.constructs_service:
            return request
        
        # Get user's psychological profile
        profile = self.constructs_service.get_user_profile_sync(user_id, archetype)
        
        # Create optimized request
        optimized = request.model_copy()
        
        # Regulatory Focus → Gain/Loss Framing
        promo = profile.self_regulatory.promotion_focus.value
        prev = profile.self_regulatory.prevention_focus.value
        if promo > prev + 0.15:
            optimized.gain_emphasis = 0.75
        elif prev > promo + 0.15:
            optimized.gain_emphasis = 0.25
        else:
            optimized.gain_emphasis = 0.5
        
        # Need for Cognition → Abstraction Level
        nfc = profile.cognitive_processing.need_for_cognition.value
        optimized.abstraction_level = nfc * 0.8 + 0.1  # Scale to 0.1-0.9
        
        # Temporal Orientation → Urgency
        future_focus = profile.temporal_psychology.future_orientation.value
        present_focus = profile.temporal_psychology.present_orientation.value
        if present_focus > future_focus:
            # Present-focused users respond to urgency
            optimized.urgency_level = 0.7
        else:
            # Future-focused users prefer planning language
            optimized.urgency_level = 0.3
        
        # Social Proof Susceptibility → Mechanism Selection
        social_susceptibility = profile.social_cognitive.social_proof_susceptibility.value
        if social_susceptibility > 0.6 and "social_proof" not in optimized.mechanisms:
            optimized.mechanisms = ["social_proof"] + optimized.mechanisms[:3]
        
        # Affect Intensity → Emotional Appeal
        affect = profile.emotional_processing.affect_intensity.value
        optimized.emotional_appeal = affect * 0.7 + 0.15
        
        logger.debug(
            f"Optimized copy for user {user_id}: "
            f"gain={optimized.gain_emphasis:.2f}, "
            f"abstraction={optimized.abstraction_level:.2f}, "
            f"urgency={optimized.urgency_level:.2f}"
        )
        
        return optimized
    
    def integrate_customer_language(
        self,
        request: CopyRequest,
        customer_intelligence: Any,  # CustomerIntelligenceProfile
    ) -> CopyRequest:
        """
        Integrate customer language patterns from review intelligence.
        
        This is a key differentiator: instead of generic copy, we use
        the actual language patterns from real customers who reviewed
        the product to make copy more resonant.
        
        Args:
            request: Copy request to enhance
            customer_intelligence: CustomerIntelligenceProfile from reviews
            
        Returns:
            Enhanced copy request with customer language hints
        """
        if not customer_intelligence:
            return request
        
        # Get copy language intelligence
        try:
            language_intel = customer_intelligence.get_copy_language()
        except AttributeError:
            # Fallback if get_copy_language method doesn't exist
            language_intel = getattr(customer_intelligence, 'language_intelligence', {}) or {}
        
        if not language_intel:
            return request
        
        # Create enhanced request
        enhanced = request.model_copy()
        
        # Extract language patterns
        phrases = language_intel.get("phrases", [])
        power_words = language_intel.get("power_words", [])
        tone = language_intel.get("tone", "neutral")
        formality = language_intel.get("formality", 0.5)
        
        # Set tone based on review analysis
        tone_mapping = {
            "enthusiastic": "energetic",
            "neutral": "professional",
            "cautious": "calm",
            "warm": "warm",
        }
        enhanced.tone = tone_mapping.get(tone, "professional")
        
        # Adjust emotional appeal based on review sentiment
        if tone == "enthusiastic":
            enhanced.emotional_appeal = max(enhanced.emotional_appeal, 0.7)
        elif tone == "cautious":
            enhanced.emotional_appeal = min(enhanced.emotional_appeal, 0.4)
        
        # Store language patterns for use in generation
        if not hasattr(enhanced, 'customer_language') or not enhanced.customer_language:
            # We'll add these to context for template/LLM use
            enhanced.context = enhanced.context or {}
            enhanced.context["customer_language"] = {
                "phrases": phrases[:5],  # Top 5 phrases from reviews
                "power_words": power_words[:8],  # Top 8 power words
                "tone": tone,
                "formality": formality,
            }
        
        # Get regulatory focus from reviews
        reg_focus = getattr(customer_intelligence, 'regulatory_focus', {})
        if reg_focus:
            promotion = reg_focus.get("promotion", 0.5)
            prevention = reg_focus.get("prevention", 0.5)
            
            # Adjust framing based on actual customer psychology
            if promotion > prevention + 0.1:
                enhanced.gain_emphasis = max(enhanced.gain_emphasis, 0.65)
            elif prevention > promotion + 0.1:
                enhanced.gain_emphasis = min(enhanced.gain_emphasis, 0.35)
        
        # Get mechanism predictions from reviews
        mechanism_predictions = getattr(customer_intelligence, 'mechanism_predictions', {})
        if mechanism_predictions:
            # Prioritize mechanisms that work with real customers
            top_mechanisms = sorted(
                mechanism_predictions.keys(),
                key=lambda m: mechanism_predictions.get(m, 0),
                reverse=True,
            )[:3]
            
            # Merge with existing mechanisms, prioritizing review-based
            existing = enhanced.mechanisms or []
            merged = top_mechanisms + [m for m in existing if m not in top_mechanisms]
            enhanced.mechanisms = merged[:5]
        
        logger.info(
            f"Enhanced copy with customer language: "
            f"phrases={len(phrases)}, power_words={len(power_words)}, "
            f"tone={tone}, mechanisms={enhanced.mechanisms[:3]}"
        )
        
        return enhanced
    
    async def generate_with_customer_intelligence(
        self,
        request: CopyRequest,
        customer_intelligence: Any,  # CustomerIntelligenceProfile
    ) -> GeneratedCopy:
        """
        Generate copy enhanced with customer language from reviews.
        
        This is the premium generation path that:
        1. Integrates real customer language patterns
        2. Uses review-derived mechanism predictions
        3. Matches the psychological profile of satisfied customers
        
        Args:
            request: Base copy request
            customer_intelligence: CustomerIntelligenceProfile
            
        Returns:
            Generated copy with customer language integration
        """
        # Enhance request with customer language
        enhanced_request = self.integrate_customer_language(request, customer_intelligence)
        
        # Generate using enhanced request
        result = await self.generate(enhanced_request)
        
        # Mark that customer intelligence was used
        result.customer_intelligence_used = True
        result.customer_language_integrated = True
        
        # Add review-derived context to output
        if enhanced_request.context and "customer_language" in enhanced_request.context:
            result.framing_applied["customer_language"] = {
                "phrases_available": len(enhanced_request.context["customer_language"]["phrases"]),
                "power_words_available": len(enhanced_request.context["customer_language"]["power_words"]),
                "tone": enhanced_request.context["customer_language"]["tone"],
            }
        
        return result
    
    def get_mechanism_recommendations(
        self,
        user_id: str,
        archetype: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Get mechanism affinity scores for a user.
        
        Returns scores indicating how effective each of the 9
        cognitive mechanisms is likely to be for this user.
        """
        if not self.constructs_service:
            return {m: 0.5 for m in [
                "construal_level", "regulatory_focus", "automatic_evaluation",
                "wanting_liking", "mimetic_desire", "attention_dynamics",
                "temporal_construal", "identity_construction", "evolutionary_adaptations"
            ]}
        
        profile = self.constructs_service.get_user_profile_sync(user_id, archetype)
        return self.constructs_service.get_mechanism_affinities(profile)
    
    def analyze_copy_effectiveness(
        self,
        copy_text: str,
        target_profile: Optional["ExtendedPsychologicalProfile"] = None,
    ) -> Dict[str, Any]:
        """
        Analyze how well copy text matches a target profile.
        
        Uses linguistic signal extraction to understand the
        psychological properties of the copy and compare
        against the target user's profile.
        
        Returns:
            Dict with match scores and recommendations
        """
        if not self.linguistic_service:
            return {"match_score": 0.5, "recommendation": "Linguistic service unavailable"}
        
        # Extract psychological properties of the copy
        copy_profile = self.linguistic_service.analyze_text(copy_text)
        
        analysis = {
            "copy_properties": {
                "valence": copy_profile.emotional_state.valence,
                "arousal": copy_profile.emotional_state.arousal,
                "regulatory_focus": copy_profile.regulatory_focus.dominant_focus,
                "temporal_focus": copy_profile.temporal_orientation.dominant_orientation,
                "cognitive_complexity": copy_profile.cognitive_complexity,
            },
            "confidence": copy_profile.overall_confidence,
        }
        
        if target_profile:
            # Calculate match score
            match_scores = []
            
            # Regulatory focus match
            if copy_profile.regulatory_focus.dominant_focus == "promotion":
                copy_promo = 0.7
            elif copy_profile.regulatory_focus.dominant_focus == "prevention":
                copy_promo = 0.3
            else:
                copy_promo = 0.5
            
            target_promo = target_profile.self_regulatory.promotion_focus.value
            reg_match = 1 - abs(copy_promo - target_promo)
            match_scores.append(reg_match)
            
            # Complexity match (NFC)
            target_nfc = target_profile.cognitive_processing.need_for_cognition.value
            complexity_match = 1 - abs(copy_profile.cognitive_complexity - target_nfc)
            match_scores.append(complexity_match)
            
            # Emotional match
            target_affect = target_profile.emotional_processing.affect_intensity.value
            affect_match = 1 - abs(copy_profile.emotional_state.arousal - target_affect)
            match_scores.append(affect_match)
            
            overall_match = sum(match_scores) / len(match_scores)
            
            analysis["target_match"] = {
                "overall_score": overall_match,
                "regulatory_focus_match": reg_match,
                "complexity_match": complexity_match,
                "affect_match": affect_match,
            }
            
            # Generate recommendations
            recommendations = []
            if reg_match < 0.6:
                if target_promo > 0.6:
                    recommendations.append("Use more gain-framed language (benefits, achievements)")
                else:
                    recommendations.append("Use more loss-framed language (risks, protection)")
            
            if complexity_match < 0.6:
                if target_nfc > 0.6:
                    recommendations.append("Increase argument complexity and detail")
                else:
                    recommendations.append("Simplify messaging, use heuristic cues")
            
            if affect_match < 0.6:
                if target_affect > 0.6:
                    recommendations.append("Increase emotional intensity")
                else:
                    recommendations.append("Use calmer, more factual language")
            
            analysis["recommendations"] = recommendations or ["Copy is well-matched to target"]
        
        return analysis
    
    # =========================================================================
    # CLAUDE-POWERED COPY GENERATION (Phase F Enhancement)
    # =========================================================================
    
    async def generate_with_claude(
        self,
        request: CopyRequest,
        user_profile: Optional[Dict[str, float]] = None,
        brand: Optional[BrandProfile] = None,
    ) -> GeneratedCopy:
        """
        Generate copy using Claude with psychological prompting.
        
        This is the enhanced generation method that leverages Claude
        to create sophisticated, psychologically-targeted copy instead
        of simple templates.
        
        Args:
            request: Copy generation request
            user_profile: User's psychological profile (construct scores)
            brand: Brand profile for voice/tone matching
            
        Returns:
            GeneratedCopy with Claude-generated text
        """
        if not LLM_AVAILABLE:
            logger.warning("LLM service not available, falling back to template generation")
            return await self.generate(request)
        
        start_time = time.time()
        
        try:
            # Build psychological prompt
            prompt = self._build_psychological_prompt(request, user_profile, brand)
            
            # Initialize LLM service
            llm_service = LLMService()
            
            try:
                # Call Claude for copy generation
                claude_response = await llm_service.generate_copy(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.7,  # Some creativity
                )
                
                if claude_response and claude_response.get("text"):
                    primary_text = claude_response["text"]
                    
                    # Generate variants using Claude as well
                    variants = await self._generate_claude_variants(
                        request, user_profile, brand, llm_service
                    )
                    
                    # Generate audio if requested
                    audio = None
                    if request.include_audio:
                        audio = self._generate_audio(request, primary_text, brand)
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if PROMETHEUS_AVAILABLE:
                        COPY_GENERATION_LATENCY.labels(
                            copy_type=request.copy_type.value,
                            mechanism=request.mechanisms[0] if request.mechanisms else "none"
                        ).observe(latency_ms / 1000)
                    
                    return GeneratedCopy(
                        request_id=request.request_id,
                        user_id=request.user_id,
                        brand_id=request.brand_id,
                        primary_text=primary_text,
                        text_variants=variants,
                        audio=audio,
                        copy_type=request.copy_type,
                        length=request.length,
                        framing_applied={
                            "gain_emphasis": request.gain_emphasis,
                            "abstraction": request.abstraction_level,
                            "emotional": request.emotional_appeal,
                            "urgency": request.urgency_level,
                            "claude_generated": True,
                        },
                        mechanisms_used=request.mechanisms,
                        overall_confidence=0.85,  # Higher confidence for Claude
                        generation_latency_ms=latency_ms,
                    )
                    
            finally:
                await llm_service.close()
                
        except Exception as e:
            logger.warning(f"Claude copy generation failed, falling back to templates: {e}")
        
        # Fallback to template-based generation
        return await self.generate(request)
    
    async def generate_evolved(
        self,
        request: CopyRequest,
        archetype: str = "",
        barrier: str = "",
        page_cluster: str = "",
    ) -> GeneratedCopy:
        """Generate copy using LEARNED effectiveness parameters.

        Instead of using the request's default tone/framing, override
        with what the CopyEffectivenessLearner has discovered works for
        this (archetype, barrier, page_cluster) combination.

        This is directed evolution — not random mutation. The system
        generates copy informed by empirical evidence of what converts.

        Architecture:
        1. Query learner for recommended params (Thompson Sampling, <1ms)
        2. Override request parameters with learned values
        3. Call generate_with_claude with enhanced parameters
        4. Tag the result as "evolved" for tracking

        Called weekly for bottom-performing variants, or on-demand
        when the learner has strong recommendations.
        """
        from adam.output.copy_generation.copy_learner import get_copy_learner

        learner = get_copy_learner()
        learned = learner.recommend_params(
            archetype=archetype or request.archetype or "",
            barrier=barrier or request.barrier_targeted or "",
            page_cluster=page_cluster,
        )

        # Map learned params to CopyRequest overrides
        overrides: Dict[str, Any] = {}
        if learned.get("tone"):
            overrides["tone"] = learned["tone"]
        if learned.get("framing"):
            framing_map = {"gain": 0.75, "loss": 0.25, "mixed": 0.5}
            overrides["gain_emphasis"] = framing_map.get(learned["framing"], 0.5)
        if learned.get("cta_style"):
            urgency_map = {"soft": 0.2, "direct": 0.5, "urgent": 0.8, "social": 0.3}
            overrides["urgency_level"] = urgency_map.get(learned["cta_style"], 0.3)

        if overrides:
            request = request.model_copy(update=overrides)
            logger.info(
                "Evolved copy params: %s (archetype=%s, barrier=%s, cluster=%s)",
                overrides, archetype, barrier, page_cluster,
            )

        result = await self.generate_with_claude(request)

        # Tag as evolved
        if result.framing_applied:
            result.framing_applied["evolved"] = True
            result.framing_applied["learned_params"] = learned

        return result

    def _build_psychological_prompt(
        self,
        request: CopyRequest,
        user_profile: Optional[Dict[str, float]] = None,
        brand: Optional[BrandProfile] = None,
    ) -> str:
        """
        Build a psychologically-informed prompt for Claude using the
        FULL intelligence of the INFORMATIV system.

        This prompt is informed by:
        1. Bilateral edge dimensions (20-dim buyer×product alignment)
        2. Gradient field priorities (which dims drive conversion most)
        3. Barrier diagnosis (the specific psychological block to resolve)
        4. Narrative arc position (what came before, what must happen now)
        5. Frustrated dimension pairs (what NOT to trigger simultaneously)
        6. Corpus fusion constraints (941M review-derived patterns)
        7. Mechanism-specific creative guidance (why THIS mechanism for THIS barrier)
        """
        parts = []

        # ── SYSTEM ROLE ──
        parts.append(
            "You are generating advertising copy for INFORMATIV, a system that "
            "uses bilateral psychological analysis to match ads to buyers. "
            "You are NOT writing generic ad copy. You are writing a SPECIFIC "
            "psychological intervention designed to resolve a diagnosed barrier "
            "for a specific buyer archetype at a specific point in a narrative sequence."
        )

        # ── CORPUS FUSION CONSTRAINTS ──
        corpus_constraints = getattr(self, "_last_corpus_constraints", None)
        if corpus_constraints and corpus_constraints.overall_confidence > 0.1:
            prompt_instructions = corpus_constraints.to_prompt_instructions()
            if prompt_instructions:
                parts.append(f"\n{prompt_instructions}")

        # ── PRODUCT CONTEXT ──
        parts.append("\n<product_context>")
        parts.append(f"Product: {request.product_name or request.brand_id}")
        if request.product_description:
            parts.append(f"Description: {request.product_description}")
        if request.product_category:
            parts.append(f"Category: {request.product_category}")
        if brand:
            parts.append(f"Brand: {brand.name}")
            if brand.voice_attributes:
                parts.append(f"Voice: {', '.join(brand.voice_attributes)}")
            if brand.key_messages:
                parts.append(f"Key messages: {', '.join(brand.key_messages[:3])}")
        parts.append("</product_context>")

        # ── BILATERAL EDGE INTELLIGENCE ──
        # This is the deepest psychological signal — actual buyer×product alignment
        # from 47M+ conversion edges, not generic archetype labels
        edge_dims = request.edge_dimensions
        if edge_dims:
            parts.append("\n<bilateral_intelligence>")
            parts.append(
                "These are the buyer's actual psychological alignment scores with this "
                "product, computed from real conversion data across millions of edges. "
                "Scores near 1.0 = strong alignment, near 0.0 = misalignment, 0.5 = neutral."
            )
            # Show top 8 most extreme dimensions (most informative for copy)
            sorted_dims = sorted(
                edge_dims.items(),
                key=lambda x: abs(x[1] - 0.5),
                reverse=True,
            )
            for dim, val in sorted_dims[:8]:
                label = dim.replace("_", " ")
                direction = "strong" if val > 0.6 else "weak" if val < 0.4 else "moderate"
                parts.append(f"  {label}: {val:.2f} ({direction})")

            # Derive explicit creative guidance from edge dims
            parts.append("\nDerived creative guidance:")
            if edge_dims.get("cognitive_load_tolerance", 0.5) > 0.65:
                parts.append("  - Buyer can process complex arguments. Use evidence and data.")
            elif edge_dims.get("cognitive_load_tolerance", 0.5) < 0.35:
                parts.append("  - Buyer prefers simple messages. Keep it short, visceral, action-oriented.")
            if edge_dims.get("emotional_resonance", 0.5) > 0.65:
                parts.append("  - Buyer responds to emotional content. Use vivid scenarios and feeling-words.")
            if edge_dims.get("social_proof_sensitivity", 0.5) > 0.65:
                parts.append("  - Buyer is influenced by others. Lead with social proof, numbers, testimonials.")
            if edge_dims.get("autonomy_reactance", 0.5) > 0.6:
                parts.append("  - Buyer resists pressure. NEVER use urgency or scarcity. Emphasize choice and control.")
            if edge_dims.get("narrative_transport", 0.5) > 0.65:
                parts.append("  - Buyer is transported by stories. Use narrative structure, not bullet points.")
            if edge_dims.get("loss_aversion_intensity", 0.5) > 0.65:
                parts.append("  - Buyer is loss-averse. Frame as 'what you'll miss' not 'what you'll gain'.")
            parts.append("</bilateral_intelligence>")

        # ── GRADIENT FIELD PRIORITIES ──
        gradient = request.gradient_priorities
        if gradient:
            parts.append("\n<gradient_priorities>")
            parts.append(
                "These are the psychological dimensions with the highest marginal "
                "impact on conversion for this buyer type. Copy should EMPHASIZE "
                "these dimensions above all others."
            )
            top3 = sorted(gradient.items(), key=lambda x: x[1], reverse=True)[:3]
            for dim, weight in top3:
                parts.append(f"  #{dim.replace('_', ' ')}: priority={weight:.2f}")
            parts.append("</gradient_priorities>")

        # ── BARRIER DIAGNOSIS ──
        if request.barrier_targeted:
            barrier_explanations = {
                "negativity_block": (
                    "The buyer has encountered negative information about the brand/category "
                    "and can't get past it. Your copy must acknowledge the concern WITHOUT "
                    "dismissing it, then provide counter-evidence. Do NOT pretend the concern "
                    "doesn't exist — that triggers reactance."
                ),
                "identity_misalignment": (
                    "The buyer doesn't see this brand as matching who they are. Your copy "
                    "must show how the brand aligns with their self-concept, values, and "
                    "aspirations — without claiming the buyer needs to change."
                ),
                "intention_action_gap": (
                    "The buyer WANTS the product but hasn't acted. The barrier is not "
                    "desire — it's friction. Your copy must reduce friction to near-zero: "
                    "specific next steps, minimal commitment, implementation intention ('when X, do Y')."
                ),
                "trust_deficit": "The buyer doesn't trust the brand enough. Address with verifiable facts, credentials, evidence.",
                "price_friction": "The buyer perceives price as too high. Address with value comparisons, not discounts.",
                "reactance_triggered": "The buyer feels pushed. Back off all pressure. Restore autonomy. Use indirect approaches.",
            }
            parts.append("\n<barrier_diagnosis>")
            parts.append(f"Diagnosed barrier: {request.barrier_targeted}")
            explanation = barrier_explanations.get(request.barrier_targeted, "")
            if explanation:
                parts.append(explanation)
            parts.append("</barrier_diagnosis>")

        # ── NARRATIVE POSITION ──
        if request.narrative_chapter and request.touch_position:
            parts.append("\n<narrative_position>")
            parts.append(f"This is Touch {request.touch_position} of a 5-touch retargeting sequence.")
            parts.append(f"Narrative chapter: {request.narrative_chapter}")
            chapter_guidance = {
                2: "COMPLICATION: Present the problem the buyer faces. Build tension. Do NOT resolve yet. The buyer should feel understood, not sold to.",
                3: "RISING ACTION: Show the path to resolution. Introduce evidence. Build credibility. The buyer should feel hope emerging.",
                4: "RESOLUTION: Show how the product resolves the specific barrier. Concrete proof. The buyer should feel 'this could work for me'.",
                5: "EPILOGUE: Reinforce the decision. Remove final friction. The buyer should feel ready to act NOW.",
            }
            guidance = chapter_guidance.get(request.narrative_chapter, "")
            if guidance:
                parts.append(guidance)
            if request.narrative_function:
                parts.append(f"Function: {request.narrative_function}")
            if request.touch_position > 1:
                parts.append(
                    f"IMPORTANT: The buyer has already seen {request.touch_position - 1} previous touches. "
                    "Do NOT repeat introductory messaging. Build on what came before."
                )
            parts.append("</narrative_position>")

        # ── FRUSTRATED DIMENSIONS ──
        if request.frustrated_dimensions:
            parts.append("\n<frustrated_dimensions>")
            parts.append(
                "WARNING: These psychological dimension pairs CONFLICT with each other. "
                "Satisfying one makes the other worse. Address them SEQUENTIALLY across "
                "touches, NEVER simultaneously in one ad."
            )
            for fd in request.frustrated_dimensions:
                parts.append(
                    f"  {fd.get('dim', '?')} conflicts with {fd.get('conflicts_with', '?')} "
                    f"(r={fd.get('r', 0):.3f})"
                )
            parts.append("</frustrated_dimensions>")

        # ── MECHANISM GUIDANCE ──
        if request.mechanisms:
            mechanism_deep = {
                "social_proof_matched": (
                    "Use social proof from people who MATCH the buyer's psychology. "
                    "Not generic '1000 customers' — specific testimonials from people "
                    "who had the SAME barrier and overcame it."
                ),
                "evidence_proof": (
                    "Present verifiable, specific evidence. Numbers, credentials, "
                    "third-party validation. The buyer needs FACTS, not promises."
                ),
                "narrative_transportation": (
                    "Transport the buyer into a story. First-person perspective. "
                    "Sensory details. The buyer should FEEL the experience before buying it."
                ),
                "anxiety_resolution": (
                    "Directly address the specific anxiety. Acknowledge it. Then provide "
                    "a concrete safety net (guarantee, free trial, easy cancellation)."
                ),
                "loss_framing": (
                    "Frame the decision as what the buyer LOSES by not acting. "
                    "Time, convenience, status — whatever this buyer values most (see edge dims)."
                ),
                "implementation_intention": (
                    "Give the buyer a specific if-then plan: 'When you land at JFK, open the app.' "
                    "The action should feel automatic, not deliberated."
                ),
                "micro_commitment": (
                    "Ask for the SMALLEST possible commitment. Not 'book a ride' but "
                    "'save your airport' or 'see pricing'. Foot-in-the-door."
                ),
                "ownership_reactivation": (
                    "Make the buyer feel they ALREADY own the experience. "
                    "'Your ride is waiting' not 'Book a ride'. Endowment effect."
                ),
                "claude_argument": (
                    "Generate a novel factual argument specifically designed for this "
                    "buyer's barrier. Not a template — a reasoned case built from evidence."
                ),
            }
            parts.append("\n<mechanism>")
            for mech in request.mechanisms[:3]:
                guidance = mechanism_deep.get(mech, f"Apply {mech} mechanism.")
                parts.append(f"Primary mechanism: {mech}")
                parts.append(guidance)
            parts.append("</mechanism>")

        # ── COPY SPECIFICATIONS ──
        parts.append("\n<specifications>")
        parts.append(f"Tone: {request.tone or 'professional'}")
        parts.append(f"Gain emphasis: {request.gain_emphasis:.1f} (0=loss-framed, 1=gain-framed)")
        parts.append(f"Abstraction: {request.abstraction_level:.1f} (0=concrete/how, 1=abstract/why)")
        parts.append(f"Emotional appeal: {request.emotional_appeal:.1f}")
        parts.append(f"Urgency: {request.urgency_level:.1f}")
        if request.headline_direction:
            parts.append(f"\nCreative brief: {request.headline_direction}")
        parts.append("</specifications>")

        # ── OUTPUT FORMAT ──
        parts.append(
            "\n<output_format>\n"
            "Generate exactly three lines:\n"
            "HEADLINE: [max 50 characters, the hook]\n"
            "BODY: [max 120 characters, the argument]\n"
            "CTA: [max 10 characters, the action]\n"
            "\n"
            "The headline must make the buyer STOP scrolling.\n"
            "The body must resolve (or advance resolving) the diagnosed barrier.\n"
            "The CTA must feel like the OBVIOUS next step, not a demand.\n"
            "</output_format>"
        )

        return "\n".join(parts)
    
    async def _generate_claude_variants(
        self,
        request: CopyRequest,
        user_profile: Optional[Dict[str, float]],
        brand: Optional[BrandProfile],
        llm_service: "LLMService",
    ) -> List[TextVariant]:
        """Generate copy variants using Claude."""
        variants = []
        
        # Generate a gain-framed variant
        gain_profile = (user_profile or {}).copy()
        gain_profile["regulatory_focus"] = 0.8
        
        try:
            gain_prompt = self._build_psychological_prompt(request, gain_profile, brand)
            gain_response = await llm_service.generate_copy(
                prompt=gain_prompt + "\n\nGenerate a GAIN-FRAMED version:",
                max_tokens=200,
                temperature=0.7,
            )
            if gain_response and gain_response.get("text"):
                variants.append(TextVariant(
                    variant_id=f"var_{uuid4().hex[:8]}_gain_claude",
                    text=gain_response["text"],
                    framing="gain",
                    confidence=0.8,
                ))
        except Exception as e:
            logger.debug(f"Failed to generate gain variant: {e}")
        
        # Generate a loss-framed variant
        loss_profile = (user_profile or {}).copy()
        loss_profile["regulatory_focus"] = 0.2
        
        try:
            loss_prompt = self._build_psychological_prompt(request, loss_profile, brand)
            loss_response = await llm_service.generate_copy(
                prompt=loss_prompt + "\n\nGenerate a LOSS-FRAMED version:",
                max_tokens=200,
                temperature=0.7,
            )
            if loss_response and loss_response.get("text"):
                variants.append(TextVariant(
                    variant_id=f"var_{uuid4().hex[:8]}_loss_claude",
                    text=loss_response["text"],
                    framing="loss",
                    confidence=0.8,
                ))
        except Exception as e:
            logger.debug(f"Failed to generate loss variant: {e}")
        
        return variants
    
    async def generate_optimized(
        self,
        request: CopyRequest,
        user_id: str,
        use_claude: bool = True,
    ) -> GeneratedCopy:
        """
        Generate fully optimized copy for a user.
        
        This is the recommended entry point that combines:
        1. User profile optimization (Enhancement #27)
        2. Claude-powered generation (if available)
        3. Effectiveness analysis
        
        Args:
            request: Base copy request
            user_id: User to optimize for
            use_claude: Whether to use Claude (vs templates)
            
        Returns:
            Optimized, generated copy
        """
        # Step 1: Optimize request for user
        optimized_request = self.optimize_for_user(request, user_id)
        
        # Step 2: Get user profile for Claude prompting
        user_profile = None
        if self.constructs_service:
            try:
                profile = self.constructs_service.get_user_profile_sync(user_id)
                user_profile = {
                    "regulatory_focus": profile.self_regulatory.promotion_focus.value,
                    "construal_level": profile.cognitive_processing.need_for_cognition.value,
                    "need_for_cognition": profile.cognitive_processing.need_for_cognition.value,
                    "temporal_orientation": profile.temporal_psychology.future_orientation.value,
                    "social_proof_susceptibility": profile.social_cognitive.social_proof_susceptibility.value,
                    "affect_intensity": profile.emotional_processing.affect_intensity.value,
                }
            except Exception as e:
                logger.debug(f"Failed to get user profile: {e}")
        
        # Step 3: Get brand profile
        brand = None
        if self.brand_service and optimized_request.brand_id:
            brand = await self.brand_service.get_brand(optimized_request.brand_id)
        
        # Step 4: Generate copy
        if use_claude and LLM_AVAILABLE:
            result = await self.generate_with_claude(optimized_request, user_profile, brand)
        else:
            result = await self.generate(optimized_request)
        
        # Step 5: Analyze effectiveness
        if self.linguistic_service and self.constructs_service and user_profile:
            try:
                profile_obj = self.constructs_service.get_user_profile_sync(user_id)
                analysis = self.analyze_copy_effectiveness(result.primary_text, profile_obj)
                result.effectiveness_analysis = analysis
            except Exception as e:
                logger.debug(f"Failed to analyze effectiveness: {e}")
        
        return result
    
    # =========================================================================
    # LEARNING CAPABLE COMPONENT INTERFACE
    # =========================================================================
    
    @property
    def component_name(self) -> str:
        """Component name for learning signal routing."""
        return "copy_generation"
    
    @property
    def component_version(self) -> str:
        """Component version."""
        return "1.0"
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[Any]:
        """
        Process an outcome and learn about copy effectiveness.
        
        For CopyGeneration, this tracks which framings and mechanisms
        were most effective.
        """
        signals = []
        
        # Track copy effectiveness
        copy_id = context.get("copy_id")
        framing = context.get("framing")  # gain/loss
        mechanisms_used = context.get("mechanisms_used", [])
        
        # Record metric if available
        if PROMETHEUS_AVAILABLE and framing:
            COPY_OPTIMIZATION_APPLIED.labels(
                optimization_type=f"framing_{framing}"
            ).inc()
        
        # Emit learning signal about copy effectiveness
        try:
            from adam.core.learning.universal_learning_interface import (
                LearningSignal,
                LearningSignalType,
            )
            signal = LearningSignal(
                signal_type=LearningSignalType.COPY_EFFECTIVENESS,
                source_component=self.component_name,
                source_version=self.component_version,
                decision_id=decision_id,
                payload={
                    "copy_id": copy_id,
                    "framing": framing,
                    "mechanisms_used": mechanisms_used,
                    "outcome_value": outcome_value,
                },
                confidence=outcome_value,
            )
            signals.append(signal)
        except ImportError:
            pass
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: Any,
    ) -> Optional[List[Any]]:
        """Process incoming learning signals."""
        # CopyGeneration can respond to signals about:
        # - New mechanism effectiveness data
        # - User preference updates
        try:
            from adam.core.learning.universal_learning_interface import (
                LearningSignal,
                LearningSignalType,
            )
            if isinstance(signal, LearningSignal):
                if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
                    # Could adjust mechanism template weights
                    pass
        except ImportError:
            pass
        return None
    
    def get_consumed_signal_types(self) -> set:
        """Return signal types this component consumes."""
        try:
            from adam.core.learning.universal_learning_interface import LearningSignalType
            return {
                LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
                LearningSignalType.TRAIT_CONFIDENCE_UPDATED,
            }
        except ImportError:
            return set()
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[Any]:
        """Get this component's contribution to a decision."""
        # Would track generated copy per decision
        return None
    
    async def get_learning_quality_metrics(self) -> Any:
        """Get metrics about learning quality."""
        try:
            from adam.core.learning.universal_learning_interface import LearningQualityMetrics
            
            return LearningQualityMetrics(
                component_name=self.component_name,
                measurement_period_hours=24,
                signals_emitted=0,  # Would track over time
                signals_consumed=0,
                outcomes_processed=0,
                prediction_accuracy=0.6,  # Would compute from copy effectiveness
                prediction_accuracy_trend="stable",
                attribution_coverage=0.5,
            )
        except ImportError:
            return None
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any],
    ) -> None:
        """Inject priors before processing."""
        # Could use priors to pre-select framings
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        # Check services availability
        if not self.constructs_service:
            issues.append("Psychological constructs service not available")
        
        if not self.linguistic_service:
            issues.append("Linguistic service not available")
        
        if not LLM_AVAILABLE:
            issues.append("LLM service not available - using templates only")
        
        return len(issues) == 0, issues