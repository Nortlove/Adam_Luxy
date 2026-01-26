# =============================================================================
# ADAM Embedding Pipelines
# Location: adam/embeddings/pipeline.py
# =============================================================================

"""
EMBEDDING PIPELINES

Domain-specific embedding pipelines for different content types.
Each pipeline handles preprocessing, chunking, and model selection
optimized for its content domain.
"""

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from adam.embeddings.models import (
    EmbeddingModel,
    EmbeddingType,
    EmbeddingNamespace,
    EmbeddingVector,
    PsychologicalEmbedding,
    BrandPersonalityEmbedding,
    AdCreativeEmbedding,
    get_model_spec,
)
from adam.embeddings.generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


# =============================================================================
# BASE PIPELINE
# =============================================================================

class EmbeddingPipeline(ABC):
    """Abstract base class for embedding pipelines."""
    
    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
    
    @property
    @abstractmethod
    def pipeline_name(self) -> str:
        """Pipeline identifier."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> EmbeddingModel:
        """Default embedding model for this pipeline."""
        pass
    
    @property
    @abstractmethod
    def embedding_type(self) -> EmbeddingType:
        """Default embedding type produced."""
        pass
    
    @property
    @abstractmethod
    def namespace(self) -> EmbeddingNamespace:
        """Default namespace for storage."""
        pass
    
    @abstractmethod
    async def process(
        self,
        content: Any,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingVector:
        """Process content and generate embedding."""
        pass
    
    @abstractmethod
    async def process_batch(
        self,
        items: List[Tuple[Any, str, Optional[Dict[str, Any]]]],
    ) -> List[EmbeddingVector]:
        """Process batch of (content, source_id, metadata) tuples."""
        pass
    
    def _generate_hash(self, content: str) -> str:
        """Generate content hash for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _truncate_text(self, text: str, max_chars: int = 500) -> str:
        """Truncate text for storage."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3] + "..."


# =============================================================================
# USER PROFILE PIPELINE
# =============================================================================

class UserProfilePipeline(EmbeddingPipeline):
    """
    Pipeline for user psychological profiles.
    
    Creates embeddings that capture:
    - Big Five personality traits
    - Regulatory focus (promotion/prevention)
    - Construal level
    - Mechanism affinities
    """
    
    @property
    def pipeline_name(self) -> str:
        return "user_profile"
    
    @property
    def default_model(self) -> EmbeddingModel:
        return EmbeddingModel.PSYCHOLOGICAL_BASE
    
    @property
    def embedding_type(self) -> EmbeddingType:
        return EmbeddingType.USER_PROFILE
    
    @property
    def namespace(self) -> EmbeddingNamespace:
        return EmbeddingNamespace.USERS
    
    async def process(
        self,
        content: Any,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingVector:
        """
        Process user profile data into embedding.
        
        Content can be:
        - Dict with personality traits
        - Text description of user behavior
        - Combined behavioral signals
        """
        if isinstance(content, dict):
            text = self._profile_to_text(content)
        else:
            text = str(content)
        
        # Generate embedding
        vector, meta = await self.generator.embed_with_metadata(
            text, self.default_model
        )
        
        return EmbeddingVector(
            vector_id=f"user_{uuid4().hex[:12]}",
            namespace=self.namespace,
            embedding_type=self.embedding_type,
            vector=vector,
            dimensions=len(vector),
            source_id=source_id,
            source_text=self._truncate_text(text),
            source_hash=self._generate_hash(text),
            model=self.default_model,
            metadata={**(metadata or {}), **meta},
            generation_latency_ms=meta.get("latency_ms"),
        )
    
    async def process_batch(
        self,
        items: List[Tuple[Any, str, Optional[Dict[str, Any]]]],
    ) -> List[EmbeddingVector]:
        """Process batch of user profiles."""
        texts = []
        for content, _, _ in items:
            if isinstance(content, dict):
                texts.append(self._profile_to_text(content))
            else:
                texts.append(str(content))
        
        vectors = await self.generator.embed_batch(texts, self.default_model)
        
        results = []
        for i, ((content, source_id, metadata), vector) in enumerate(
            zip(items, vectors)
        ):
            text = texts[i]
            results.append(EmbeddingVector(
                vector_id=f"user_{uuid4().hex[:12]}",
                namespace=self.namespace,
                embedding_type=self.embedding_type,
                vector=vector,
                dimensions=len(vector),
                source_id=source_id,
                source_text=self._truncate_text(text),
                source_hash=self._generate_hash(text),
                model=self.default_model,
                metadata=metadata or {},
            ))
        
        return results
    
    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        """Convert profile dict to semantic text."""
        parts = []
        
        # Big Five
        if "big_five" in profile:
            bf = profile["big_five"]
            traits = []
            if bf.get("openness", 0.5) > 0.6:
                traits.append("creative and curious")
            if bf.get("conscientiousness", 0.5) > 0.6:
                traits.append("organized and disciplined")
            if bf.get("extraversion", 0.5) > 0.6:
                traits.append("outgoing and energetic")
            if bf.get("agreeableness", 0.5) > 0.6:
                traits.append("cooperative and trusting")
            if bf.get("neuroticism", 0.5) > 0.6:
                traits.append("sensitive and emotional")
            
            if traits:
                parts.append(f"Personality: {', '.join(traits)}")
        
        # Regulatory focus
        if "regulatory_focus" in profile:
            rf = profile["regulatory_focus"]
            if rf.get("promotion", 0.5) > rf.get("prevention", 0.5):
                parts.append("Motivated by achievements and gains")
            else:
                parts.append("Motivated by security and avoiding losses")
        
        # Interests/categories
        if "interests" in profile:
            parts.append(f"Interests: {', '.join(profile['interests'][:5])}")
        
        # Behavior patterns
        if "behavior" in profile:
            parts.append(f"Behavior: {profile['behavior']}")
        
        return ". ".join(parts) if parts else "User profile"
    
    async def create_psychological_embedding(
        self,
        user_id: str,
        profile: Dict[str, Any],
    ) -> PsychologicalEmbedding:
        """Create specialized psychological embedding."""
        text = self._profile_to_text(profile)
        vector = await self.generator.embed_text(text, self.default_model)
        
        # Extract interpretable components
        big_five = [
            profile.get("big_five", {}).get("openness", 0.5),
            profile.get("big_five", {}).get("conscientiousness", 0.5),
            profile.get("big_five", {}).get("extraversion", 0.5),
            profile.get("big_five", {}).get("agreeableness", 0.5),
            profile.get("big_five", {}).get("neuroticism", 0.5),
        ]
        
        reg_focus = [
            profile.get("regulatory_focus", {}).get("promotion", 0.5),
            profile.get("regulatory_focus", {}).get("prevention", 0.5),
        ]
        
        construal = [profile.get("construal_level", 0.5)]
        
        mechanism_affinity = [
            profile.get("mechanisms", {}).get("social_proof", 0.5),
            profile.get("mechanisms", {}).get("scarcity", 0.5),
            profile.get("mechanisms", {}).get("authority", 0.5),
            profile.get("mechanisms", {}).get("reciprocity", 0.5),
            profile.get("mechanisms", {}).get("commitment", 0.5),
            profile.get("mechanisms", {}).get("liking", 0.5),
        ]
        
        return PsychologicalEmbedding(
            user_id=user_id,
            vector=vector,
            dimensions=len(vector),
            big_five_component=big_five,
            regulatory_focus_component=reg_focus,
            construal_level_component=construal,
            mechanism_affinity_component=mechanism_affinity,
            confidence=profile.get("confidence", 0.5),
            data_points=profile.get("data_points", 0),
        )


# =============================================================================
# BRAND PROFILE PIPELINE
# =============================================================================

class BrandProfilePipeline(EmbeddingPipeline):
    """
    Pipeline for brand personality and voice.
    
    Creates embeddings that capture:
    - Brand archetypes
    - Tone and voice
    - Values and positioning
    """
    
    # Brand archetype descriptions for embedding
    ARCHETYPES = {
        "innocent": "pure, optimistic, safe, simple, nostalgic",
        "sage": "knowledgeable, wise, trusted advisor, expert",
        "explorer": "adventurous, pioneering, independent, bold",
        "outlaw": "rebellious, disruptive, revolutionary, edgy",
        "magician": "transformative, visionary, imaginative, mystical",
        "hero": "courageous, triumphant, inspiring, powerful",
        "lover": "passionate, sensual, intimate, romantic",
        "jester": "fun, playful, humorous, entertaining",
        "everyman": "relatable, honest, humble, authentic",
        "caregiver": "nurturing, compassionate, protective, supportive",
        "ruler": "authoritative, commanding, premium, exclusive",
        "creator": "innovative, artistic, imaginative, expressive",
    }
    
    @property
    def pipeline_name(self) -> str:
        return "brand_profile"
    
    @property
    def default_model(self) -> EmbeddingModel:
        return EmbeddingModel.BRAND_PERSONALITY
    
    @property
    def embedding_type(self) -> EmbeddingType:
        return EmbeddingType.BRAND_PROFILE
    
    @property
    def namespace(self) -> EmbeddingNamespace:
        return EmbeddingNamespace.BRANDS
    
    async def process(
        self,
        content: Any,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingVector:
        """Process brand data into embedding."""
        if isinstance(content, dict):
            text = self._brand_to_text(content)
        else:
            text = str(content)
        
        vector, meta = await self.generator.embed_with_metadata(
            text, self.default_model
        )
        
        return EmbeddingVector(
            vector_id=f"brand_{uuid4().hex[:12]}",
            namespace=self.namespace,
            embedding_type=self.embedding_type,
            vector=vector,
            dimensions=len(vector),
            source_id=source_id,
            source_text=self._truncate_text(text),
            source_hash=self._generate_hash(text),
            model=self.default_model,
            metadata={**(metadata or {}), **meta},
            generation_latency_ms=meta.get("latency_ms"),
        )
    
    async def process_batch(
        self,
        items: List[Tuple[Any, str, Optional[Dict[str, Any]]]],
    ) -> List[EmbeddingVector]:
        """Process batch of brand profiles."""
        texts = []
        for content, _, _ in items:
            if isinstance(content, dict):
                texts.append(self._brand_to_text(content))
            else:
                texts.append(str(content))
        
        vectors = await self.generator.embed_batch(texts, self.default_model)
        
        results = []
        for i, ((content, source_id, metadata), vector) in enumerate(
            zip(items, vectors)
        ):
            results.append(EmbeddingVector(
                vector_id=f"brand_{uuid4().hex[:12]}",
                namespace=self.namespace,
                embedding_type=self.embedding_type,
                vector=vector,
                dimensions=len(vector),
                source_id=source_id,
                source_text=self._truncate_text(texts[i]),
                source_hash=self._generate_hash(texts[i]),
                model=self.default_model,
                metadata=metadata or {},
            ))
        
        return results
    
    def _brand_to_text(self, brand: Dict[str, Any]) -> str:
        """Convert brand dict to semantic text."""
        parts = []
        
        # Brand name and tagline
        if "name" in brand:
            parts.append(f"Brand: {brand['name']}")
        if "tagline" in brand:
            parts.append(f"Tagline: {brand['tagline']}")
        
        # Archetypes
        if "archetypes" in brand:
            archetype_descs = []
            for arch in brand["archetypes"]:
                if arch in self.ARCHETYPES:
                    archetype_descs.append(self.ARCHETYPES[arch])
            if archetype_descs:
                parts.append(f"Personality: {', '.join(archetype_descs)}")
        
        # Tone
        if "tone" in brand:
            parts.append(f"Tone: {', '.join(brand['tone'])}")
        
        # Values
        if "values" in brand:
            parts.append(f"Values: {', '.join(brand['values'])}")
        
        # Category
        if "category" in brand:
            parts.append(f"Category: {brand['category']}")
        
        return ". ".join(parts) if parts else "Brand profile"
    
    async def create_brand_embedding(
        self,
        brand_id: str,
        brand_data: Dict[str, Any],
    ) -> BrandPersonalityEmbedding:
        """Create specialized brand personality embedding."""
        text = self._brand_to_text(brand_data)
        vector = await self.generator.embed_text(text, self.default_model)
        
        # Extract archetype components
        archetype_scores = []
        for arch in self.ARCHETYPES:
            score = 1.0 if arch in brand_data.get("archetypes", []) else 0.0
            archetype_scores.append(score)
        
        # Tone components
        tones = ["formal", "casual", "enthusiastic", "calm", "urgent", 
                 "friendly", "authoritative", "playful"]
        tone_scores = []
        for tone in tones:
            score = 1.0 if tone in brand_data.get("tone", []) else 0.0
            tone_scores.append(score)
        
        return BrandPersonalityEmbedding(
            brand_id=brand_id,
            vector=vector,
            dimensions=len(vector),
            archetype_component=archetype_scores,
            tone_component=tone_scores,
            values_component=[],  # Could extract from values
        )


# =============================================================================
# AD CREATIVE PIPELINE
# =============================================================================

class AdCreativePipeline(EmbeddingPipeline):
    """
    Pipeline for ad creative content.
    
    Creates embeddings optimized for:
    - Ad copy semantic matching
    - Emotional resonance
    - Persuasion mechanism alignment
    """
    
    # Persuasion mechanisms
    MECHANISMS = [
        "social_proof", "scarcity", "authority", "reciprocity",
        "commitment", "liking", "unity", "reason_why",
    ]
    
    # Emotional tones
    EMOTIONS = [
        "joy", "trust", "fear", "surprise", "sadness",
        "anticipation", "anger", "disgust",
    ]
    
    @property
    def pipeline_name(self) -> str:
        return "ad_creative"
    
    @property
    def default_model(self) -> EmbeddingModel:
        return EmbeddingModel.ADVERTISING_CREATIVE
    
    @property
    def embedding_type(self) -> EmbeddingType:
        return EmbeddingType.AD_CREATIVE
    
    @property
    def namespace(self) -> EmbeddingNamespace:
        return EmbeddingNamespace.CREATIVES
    
    async def process(
        self,
        content: Any,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingVector:
        """Process ad creative into embedding."""
        if isinstance(content, dict):
            text = self._creative_to_text(content)
            # Extract mechanism alignment
            mechanism_alignment = self._detect_mechanisms(text)
        else:
            text = str(content)
            mechanism_alignment = self._detect_mechanisms(text)
        
        vector, meta = await self.generator.embed_with_metadata(
            text, self.default_model
        )
        
        return EmbeddingVector(
            vector_id=f"creative_{uuid4().hex[:12]}",
            namespace=self.namespace,
            embedding_type=self.embedding_type,
            vector=vector,
            dimensions=len(vector),
            source_id=source_id,
            source_text=self._truncate_text(text),
            source_hash=self._generate_hash(text),
            model=self.default_model,
            metadata={
                **(metadata or {}),
                **meta,
                "mechanism_alignment": mechanism_alignment,
            },
            generation_latency_ms=meta.get("latency_ms"),
        )
    
    async def process_batch(
        self,
        items: List[Tuple[Any, str, Optional[Dict[str, Any]]]],
    ) -> List[EmbeddingVector]:
        """Process batch of ad creatives."""
        texts = []
        for content, _, _ in items:
            if isinstance(content, dict):
                texts.append(self._creative_to_text(content))
            else:
                texts.append(str(content))
        
        vectors = await self.generator.embed_batch(texts, self.default_model)
        
        results = []
        for i, ((content, source_id, metadata), vector) in enumerate(
            zip(items, vectors)
        ):
            text = texts[i]
            mechanism_alignment = self._detect_mechanisms(text)
            
            results.append(EmbeddingVector(
                vector_id=f"creative_{uuid4().hex[:12]}",
                namespace=self.namespace,
                embedding_type=self.embedding_type,
                vector=vector,
                dimensions=len(vector),
                source_id=source_id,
                source_text=self._truncate_text(text),
                source_hash=self._generate_hash(text),
                model=self.default_model,
                metadata={
                    **(metadata or {}),
                    "mechanism_alignment": mechanism_alignment,
                },
            ))
        
        return results
    
    def _creative_to_text(self, creative: Dict[str, Any]) -> str:
        """Convert creative dict to semantic text."""
        parts = []
        
        if "headline" in creative:
            parts.append(f"Headline: {creative['headline']}")
        if "copy" in creative:
            parts.append(f"Copy: {creative['copy']}")
        if "cta" in creative:
            parts.append(f"Call to action: {creative['cta']}")
        if "description" in creative:
            parts.append(creative["description"])
        
        return " ".join(parts) if parts else "Ad creative"
    
    def _detect_mechanisms(self, text: str) -> Dict[str, float]:
        """Detect persuasion mechanisms in text."""
        text_lower = text.lower()
        
        # Keywords for each mechanism
        mechanism_keywords = {
            "social_proof": ["everyone", "popular", "bestselling", "trusted by",
                            "million", "customers", "loved by", "rated"],
            "scarcity": ["limited", "only", "last chance", "hurry", "exclusive",
                        "running out", "while supplies", "don't miss"],
            "authority": ["expert", "doctor", "scientist", "research", "study",
                         "proven", "certified", "official", "endorsed"],
            "reciprocity": ["free", "gift", "bonus", "complimentary", "no cost",
                          "give you", "yours free"],
            "commitment": ["start", "begin", "first step", "simple", "easy",
                          "quick", "trial", "try"],
            "liking": ["you", "your", "friend", "together", "personal",
                      "custom", "just for you"],
            "unity": ["we", "us", "our", "together", "community", "join",
                     "belong", "family"],
            "reason_why": ["because", "that's why", "reason", "so you can",
                          "which means", "therefore"],
        }
        
        scores = {}
        for mechanism, keywords in mechanism_keywords.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            scores[mechanism] = min(matches / len(keywords), 1.0)
        
        return scores
    
    async def create_ad_embedding(
        self,
        creative_id: str,
        campaign_id: str,
        brand_id: str,
        creative_data: Dict[str, Any],
    ) -> AdCreativeEmbedding:
        """Create specialized ad creative embedding."""
        text = self._creative_to_text(creative_data)
        vector = await self.generator.embed_text(text, self.default_model)
        mechanism_alignment = self._detect_mechanisms(text)
        
        return AdCreativeEmbedding(
            creative_id=creative_id,
            campaign_id=campaign_id,
            brand_id=brand_id,
            vector=vector,
            dimensions=len(vector),
            mechanism_alignment=mechanism_alignment,
            copy_text=creative_data.get("copy"),
            headline=creative_data.get("headline"),
            cta=creative_data.get("cta"),
        )


# =============================================================================
# PRODUCT PIPELINE
# =============================================================================

class ProductPipeline(EmbeddingPipeline):
    """Pipeline for product descriptions and reviews."""
    
    @property
    def pipeline_name(self) -> str:
        return "product"
    
    @property
    def default_model(self) -> EmbeddingModel:
        return EmbeddingModel.ALL_MPNET_BASE
    
    @property
    def embedding_type(self) -> EmbeddingType:
        return EmbeddingType.PRODUCT_DESCRIPTION
    
    @property
    def namespace(self) -> EmbeddingNamespace:
        return EmbeddingNamespace.PRODUCTS
    
    async def process(
        self,
        content: Any,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingVector:
        """Process product data into embedding."""
        if isinstance(content, dict):
            text = self._product_to_text(content)
        else:
            text = str(content)
        
        vector, meta = await self.generator.embed_with_metadata(
            text, self.default_model
        )
        
        return EmbeddingVector(
            vector_id=f"product_{uuid4().hex[:12]}",
            namespace=self.namespace,
            embedding_type=self.embedding_type,
            vector=vector,
            dimensions=len(vector),
            source_id=source_id,
            source_text=self._truncate_text(text),
            source_hash=self._generate_hash(text),
            model=self.default_model,
            metadata={**(metadata or {}), **meta},
            generation_latency_ms=meta.get("latency_ms"),
        )
    
    async def process_batch(
        self,
        items: List[Tuple[Any, str, Optional[Dict[str, Any]]]],
    ) -> List[EmbeddingVector]:
        """Process batch of products."""
        texts = []
        for content, _, _ in items:
            if isinstance(content, dict):
                texts.append(self._product_to_text(content))
            else:
                texts.append(str(content))
        
        vectors = await self.generator.embed_batch(texts, self.default_model)
        
        results = []
        for i, ((_, source_id, metadata), vector) in enumerate(zip(items, vectors)):
            results.append(EmbeddingVector(
                vector_id=f"product_{uuid4().hex[:12]}",
                namespace=self.namespace,
                embedding_type=self.embedding_type,
                vector=vector,
                dimensions=len(vector),
                source_id=source_id,
                source_text=self._truncate_text(texts[i]),
                source_hash=self._generate_hash(texts[i]),
                model=self.default_model,
                metadata=metadata or {},
            ))
        
        return results
    
    def _product_to_text(self, product: Dict[str, Any]) -> str:
        """Convert product dict to semantic text."""
        parts = []
        
        if "title" in product:
            parts.append(product["title"])
        if "description" in product:
            parts.append(product["description"])
        if "category" in product:
            parts.append(f"Category: {product['category']}")
        if "brand" in product:
            parts.append(f"Brand: {product['brand']}")
        if "features" in product:
            parts.append(f"Features: {', '.join(product['features'][:5])}")
        
        return " ".join(parts) if parts else "Product"


# =============================================================================
# AUDIO TRANSCRIPT PIPELINE
# =============================================================================

class AudioTranscriptPipeline(EmbeddingPipeline):
    """Pipeline for audio transcripts and spoken content."""
    
    @property
    def pipeline_name(self) -> str:
        return "audio_transcript"
    
    @property
    def default_model(self) -> EmbeddingModel:
        return EmbeddingModel.ALL_MINILM_L6
    
    @property
    def embedding_type(self) -> EmbeddingType:
        return EmbeddingType.AUDIO_TRANSCRIPT
    
    @property
    def namespace(self) -> EmbeddingNamespace:
        return EmbeddingNamespace.AUDIO
    
    async def process(
        self,
        content: Any,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingVector:
        """Process audio transcript into embedding."""
        if isinstance(content, dict):
            text = content.get("transcript", "")
        else:
            text = str(content)
        
        # Clean transcript
        text = self._clean_transcript(text)
        
        vector, meta = await self.generator.embed_with_metadata(
            text, self.default_model
        )
        
        return EmbeddingVector(
            vector_id=f"audio_{uuid4().hex[:12]}",
            namespace=self.namespace,
            embedding_type=self.embedding_type,
            vector=vector,
            dimensions=len(vector),
            source_id=source_id,
            source_text=self._truncate_text(text),
            source_hash=self._generate_hash(text),
            model=self.default_model,
            metadata={**(metadata or {}), **meta},
            generation_latency_ms=meta.get("latency_ms"),
        )
    
    async def process_batch(
        self,
        items: List[Tuple[Any, str, Optional[Dict[str, Any]]]],
    ) -> List[EmbeddingVector]:
        """Process batch of transcripts."""
        texts = []
        for content, _, _ in items:
            if isinstance(content, dict):
                text = content.get("transcript", "")
            else:
                text = str(content)
            texts.append(self._clean_transcript(text))
        
        vectors = await self.generator.embed_batch(texts, self.default_model)
        
        results = []
        for i, ((_, source_id, metadata), vector) in enumerate(zip(items, vectors)):
            results.append(EmbeddingVector(
                vector_id=f"audio_{uuid4().hex[:12]}",
                namespace=self.namespace,
                embedding_type=self.embedding_type,
                vector=vector,
                dimensions=len(vector),
                source_id=source_id,
                source_text=self._truncate_text(texts[i]),
                source_hash=self._generate_hash(texts[i]),
                model=self.default_model,
                metadata=metadata or {},
            ))
        
        return results
    
    def _clean_transcript(self, text: str) -> str:
        """Clean transcript text."""
        # Remove filler words
        fillers = ["um", "uh", "like", "you know", "so", "actually"]
        for filler in fillers:
            text = re.sub(rf"\b{filler}\b", "", text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = " ".join(text.split())
        
        return text


# =============================================================================
# PIPELINE REGISTRY
# =============================================================================

class PipelineRegistry:
    """Registry for embedding pipelines."""
    
    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
        self._pipelines: Dict[str, EmbeddingPipeline] = {}
        
        # Register default pipelines
        self.register("user_profile", UserProfilePipeline(generator))
        self.register("brand_profile", BrandProfilePipeline(generator))
        self.register("ad_creative", AdCreativePipeline(generator))
        self.register("product", ProductPipeline(generator))
        self.register("audio_transcript", AudioTranscriptPipeline(generator))
    
    def register(self, name: str, pipeline: EmbeddingPipeline) -> None:
        """Register a pipeline."""
        self._pipelines[name] = pipeline
    
    def get(self, name: str) -> Optional[EmbeddingPipeline]:
        """Get pipeline by name."""
        return self._pipelines.get(name)
    
    def list_pipelines(self) -> List[str]:
        """List registered pipeline names."""
        return list(self._pipelines.keys())
