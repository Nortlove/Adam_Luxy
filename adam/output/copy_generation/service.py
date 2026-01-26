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
    
    def _build_psychological_prompt(
        self,
        request: CopyRequest,
        user_profile: Optional[Dict[str, float]],
        brand: Optional[BrandProfile],
    ) -> str:
        """
        Build a psychologically-informed prompt for Claude.
        
        This is where ADAM's psychological intelligence is translated
        into copy generation guidance.
        """
        prompt_parts = []
        
        # System context
        prompt_parts.append(
            "You are an expert advertising copywriter with deep knowledge of "
            "consumer psychology. Your task is to generate highly effective "
            "ad copy that resonates with the target user's psychological profile."
        )
        
        # Product context
        prompt_parts.append(f"\n## Product Information")
        prompt_parts.append(f"- Product: {request.product_name or 'Unspecified product'}")
        if request.product_description:
            prompt_parts.append(f"- Description: {request.product_description}")
        if request.product_category:
            prompt_parts.append(f"- Category: {request.product_category}")
        
        # Brand voice
        if brand:
            prompt_parts.append(f"\n## Brand Voice")
            prompt_parts.append(f"- Brand: {brand.name}")
            if brand.voice_attributes:
                prompt_parts.append(f"- Voice: {', '.join(brand.voice_attributes)}")
            if brand.key_messages:
                prompt_parts.append(f"- Key messages: {', '.join(brand.key_messages[:3])}")
        
        # Psychological targeting
        prompt_parts.append(f"\n## Psychological Targeting")
        
        if user_profile:
            # Regulatory focus
            reg_focus = user_profile.get("regulatory_focus", 0.5)
            if reg_focus > 0.6:
                prompt_parts.append("- Frame as GAINS: Focus on benefits, achievements, aspirations")
            elif reg_focus < 0.4:
                prompt_parts.append("- Frame as LOSS PREVENTION: Focus on protection, security, avoiding negatives")
            else:
                prompt_parts.append("- Use balanced framing: Mix of benefits and risk mitigation")
            
            # Construal level
            construal = user_profile.get("construal_level", 0.5)
            if construal > 0.6:
                prompt_parts.append("- Use ABSTRACT language: Focus on 'why', broader purpose, values")
            else:
                prompt_parts.append("- Use CONCRETE language: Focus on 'how', specific features, details")
            
            # Need for cognition
            nfc = user_profile.get("need_for_cognition", 0.5)
            if nfc > 0.6:
                prompt_parts.append("- Include DETAILED arguments: User appreciates complexity and evidence")
            else:
                prompt_parts.append("- Keep it SIMPLE: Use heuristics, social proof, authority cues")
            
            # Temporal orientation
            temporal = user_profile.get("temporal_orientation", 0.5)
            if temporal < 0.4:  # Present-focused
                prompt_parts.append("- Create URGENCY: User responds to immediate benefits and scarcity")
            else:
                prompt_parts.append("- Emphasize LONG-TERM VALUE: User thinks about future outcomes")
            
            # Social proof susceptibility
            social = user_profile.get("social_proof_susceptibility", 0.5)
            if social > 0.6:
                prompt_parts.append("- Include SOCIAL PROOF: Numbers, testimonials, popularity")
        
        else:
            # Default guidance based on request parameters
            if request.gain_emphasis > 0.6:
                prompt_parts.append("- Use gain-framed language (benefits, achievements)")
            elif request.gain_emphasis < 0.4:
                prompt_parts.append("- Use loss-framed language (risks, protection)")
            
            if request.abstraction_level > 0.6:
                prompt_parts.append("- Use abstract, 'why'-focused messaging")
            else:
                prompt_parts.append("- Use concrete, 'how'-focused messaging")
        
        # Mechanisms to incorporate
        if request.mechanisms:
            prompt_parts.append(f"\n## Cognitive Mechanisms to Incorporate")
            mechanism_guidance = {
                "scarcity": "Create sense of limited availability",
                "social_proof": "Reference popularity or others' choices",
                "authority": "Cite experts or credentials",
                "urgency": "Emphasize time-sensitivity",
                "reciprocity": "Offer value first",
                "consistency": "Connect to user's identity or past behavior",
                "liking": "Create warmth and relatability",
            }
            for mech in request.mechanisms[:3]:
                if mech in mechanism_guidance:
                    prompt_parts.append(f"- {mech.upper()}: {mechanism_guidance[mech]}")
        
        # Copy specifications
        prompt_parts.append(f"\n## Copy Specifications")
        prompt_parts.append(f"- Type: {request.copy_type.value}")
        prompt_parts.append(f"- Length: {request.length.value}")
        prompt_parts.append(f"- Tone: {request.tone or 'professional'}")
        if request.cta_action:
            prompt_parts.append(f"- CTA: {request.cta_action}")
        
        # Output instruction
        prompt_parts.append(
            "\n## Task\n"
            "Generate compelling ad copy that:\n"
            "1. Aligns with the psychological profile above\n"
            "2. Incorporates the specified cognitive mechanisms\n"
            "3. Matches the brand voice\n"
            "4. Fits the length requirement\n"
            "\nOutput ONLY the ad copy text, no explanations or metadata."
        )
        
        return "\n".join(prompt_parts)
    
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