# =============================================================================
# ADAM Demo - Real Platform Integration
# Location: adam/demo/platform_integration.py
# =============================================================================

"""
REAL PLATFORM INTEGRATION FOR DEMO

This module connects the demo to actual ADAM platform components:
- Atom DAG execution (real psychological reasoning)
- Neo4j graph queries (real user/mechanism data)
- Linguistic feature extraction (real text analysis)
- Nonconscious analytics (real signal processing)
- Blackboard service (real shared state)

When infrastructure is unavailable, gracefully falls back to simulation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

# Platform components
try:
    from adam.atoms.dag import AtomDAGExecutor, DAGExecutionResult
    from adam.atoms.models.atom_io import AtomInput, AtomOutput
    from adam.blackboard.service import BlackboardService
    from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
    from adam.blackboard.models.zone2_reasoning import AtomReasoningSpace
    from adam.graph_reasoning.bridge import InteractionBridge
    from adam.graph_reasoning.models.graph_context import GraphContext
    from adam.signals.nonconscious.service import NonconsciousAnalyticsService
    from adam.signals.nonconscious.models import NonconsciousProfile, NonconsciousSignal
    from adam.data.amazon.features import LinguisticFeatureExtractor, LinguisticFeatures
    from adam.embeddings.service import EmbeddingService
    from adam.meta_learner.service import MetaLearnerService
    from adam.infrastructure.redis import ADAMRedisCache
    PLATFORM_AVAILABLE = True
except ImportError as e:
    PLATFORM_AVAILABLE = False
    logging.warning(f"Platform components not available: {e}")

# Demo models
from adam.demo.models import (
    RecommendationRequest,
    RecommendationResponse,
    MomentaryState,
    StableTraits,
    ListenerInference,
    InferenceSource,
    InferenceSourceDetail,
)

# Try to import embedding service
try:
    from adam.embeddings.service import EmbeddingService
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# PLATFORM STATUS
# =============================================================================

class PlatformStatus(BaseModel):
    """Status of platform component availability."""
    
    neo4j_connected: bool = False
    redis_connected: bool = False
    atoms_available: bool = False
    blackboard_available: bool = False
    nonconscious_available: bool = False
    embeddings_available: bool = False
    linguistic_available: bool = False
    
    # Which components are being used (real vs simulated)
    using_real_atoms: bool = False
    using_real_graph: bool = False
    using_real_nonconscious: bool = False
    using_real_linguistics: bool = False
    
    @property
    def any_real(self) -> bool:
        return any([
            self.using_real_atoms,
            self.using_real_graph,
            self.using_real_nonconscious,
            self.using_real_linguistics,
        ])
    
    @property
    def status_summary(self) -> str:
        real = []
        if self.using_real_atoms:
            real.append("Atoms")
        if self.using_real_graph:
            real.append("Graph")
        if self.using_real_nonconscious:
            real.append("Nonconscious")
        if self.using_real_linguistics:
            real.append("Linguistics")
        
        if real:
            return f"REAL: {', '.join(real)}"
        return "SIMULATED (no infrastructure)"


# =============================================================================
# REAL LINGUISTIC ANALYSIS
# =============================================================================

class RealLinguisticAnalyzer:
    """
    Uses actual LIWC-style linguistic feature extraction.
    
    Extracts real psychological markers from text:
    - Self-reference patterns
    - Emotional valence
    - Cognitive complexity
    - Social orientation
    """
    
    def __init__(self):
        self.extractor = None
        if PLATFORM_AVAILABLE:
            try:
                self.extractor = LinguisticFeatureExtractor()
                logger.info("Real linguistic analyzer initialized")
            except Exception as e:
                logger.warning(f"Could not initialize linguistic extractor: {e}")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Extract linguistic features from text.
        
        Returns dict with:
        - big_five_indicators: Trait signals from language
        - emotional_markers: Valence and arousal signals
        - cognitive_markers: Complexity and processing indicators
        - social_markers: Relationship orientation signals
        """
        if not text or not self.extractor:
            return self._simulate_analysis(text)
        
        try:
            features = self.extractor.extract(text)
            return self._features_to_psychology(features)
        except Exception as e:
            logger.warning(f"Linguistic analysis failed: {e}")
            return self._simulate_analysis(text)
    
    def _features_to_psychology(self, features: 'LinguisticFeatures') -> Dict[str, Any]:
        """Convert linguistic features to psychological indicators."""
        
        # Big Five inference from language patterns
        # Based on Yarkoni (2010) and Schwartz et al. (2013)
        big_five = {
            "openness": self._infer_openness(features),
            "conscientiousness": self._infer_conscientiousness(features),
            "extraversion": self._infer_extraversion(features),
            "agreeableness": self._infer_agreeableness(features),
            "neuroticism": self._infer_neuroticism(features),
        }
        
        return {
            "big_five_indicators": big_five,
            "emotional_markers": {
                "positive_affect": features.positive_emotion,
                "negative_affect": features.negative_emotion,
                "anxiety": features.anxiety,
                "anger": features.anger,
            },
            "cognitive_markers": {
                "analytical": features.analytical,
                "certainty": features.certainty,
                "tentative": features.tentative,
                "complexity": features.word_length_avg,
            },
            "social_markers": {
                "social_words": features.social,
                "first_person_singular": features.first_person_singular,
                "first_person_plural": features.first_person_plural,
            },
            "confidence": 0.75,
            "source": "real_linguistic_analysis",
        }
    
    def _infer_openness(self, f: 'LinguisticFeatures') -> float:
        """Infer openness from linguistic features."""
        # High openness: longer words, more articles, more prepositions
        score = 0.5
        score += (f.word_length_avg - 4.5) * 0.1  # Longer words
        score += f.insight * 0.1  # Insight words
        return max(0.1, min(0.9, score))
    
    def _infer_conscientiousness(self, f: 'LinguisticFeatures') -> float:
        """Infer conscientiousness from linguistic features."""
        # High conscientiousness: fewer negations, more achievement
        score = 0.5
        score += f.certainty * 0.1  # Certainty
        score -= f.discrepancy * 0.1  # Fewer discrepancies
        return max(0.1, min(0.9, score))
    
    def _infer_extraversion(self, f: 'LinguisticFeatures') -> float:
        """Infer extraversion from linguistic features."""
        # High extraversion: more social words, positive emotion, "we"
        score = 0.5
        score += f.social * 0.1
        score += f.positive_emotion * 0.1
        score += f.first_person_plural * 0.1
        return max(0.1, min(0.9, score))
    
    def _infer_agreeableness(self, f: 'LinguisticFeatures') -> float:
        """Infer agreeableness from linguistic features."""
        # High agreeableness: positive emotion, social words, less anger
        score = 0.5
        score += f.positive_emotion * 0.1
        score -= f.anger * 0.1
        score -= f.swear_words * 0.1
        return max(0.1, min(0.9, score))
    
    def _infer_neuroticism(self, f: 'LinguisticFeatures') -> float:
        """Infer neuroticism from linguistic features."""
        # High neuroticism: more negative emotion, "I", anxiety words
        score = 0.5
        score += f.negative_emotion * 0.1
        score += f.first_person_singular * 0.05
        score += f.anxiety * 0.1
        return max(0.1, min(0.9, score))
    
    def _simulate_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback simulation when real analysis unavailable."""
        # Simple heuristics
        word_count = len(text.split()) if text else 0
        has_exclamation = "!" in text
        has_question = "?" in text
        
        return {
            "big_five_indicators": {
                "openness": 0.55,
                "conscientiousness": 0.50,
                "extraversion": 0.55 if has_exclamation else 0.45,
                "agreeableness": 0.50,
                "neuroticism": 0.45,
            },
            "emotional_markers": {
                "positive_affect": 0.4,
                "negative_affect": 0.2,
            },
            "cognitive_markers": {
                "analytical": 0.5,
                "complexity": word_count / 50.0 if word_count else 0.3,
            },
            "confidence": 0.4,
            "source": "simulated",
        }


# =============================================================================
# REAL NONCONSCIOUS ANALYZER
# =============================================================================

class RealNonconsciousAnalyzer:
    """
    Uses actual nonconscious signal processing.
    
    Processes:
    - Mouse dynamics (approach-avoidance)
    - Scroll behavior (engagement depth)
    - Keystroke patterns (cognitive load)
    - Response latency (attitude accessibility)
    """
    
    def __init__(self):
        self.service = None
        if PLATFORM_AVAILABLE:
            try:
                self.service = NonconsciousAnalyticsService()
                logger.info("Real nonconscious analyzer initialized")
            except Exception as e:
                logger.warning(f"Could not initialize nonconscious service: {e}")
    
    async def analyze_signals(
        self,
        session_id: str,
        signals: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze nonconscious signals from user session.
        
        Returns:
        - approach_avoidance: Net approach/avoid tendency
        - cognitive_load: Estimated mental effort
        - processing_fluency: Ease of processing
        - emotional_valence: Implicit emotional state
        - mechanism_hints: Suggested persuasion mechanisms
        """
        if not self.service:
            return self._simulate_analysis(signals)
        
        try:
            # Convert raw signals to NonconsciousSignal objects
            nc_signals = [
                NonconsciousSignal(
                    signal_id=str(uuid4()),
                    session_id=session_id,
                    signal_type=s.get("type", "unknown"),
                    raw_data=s,
                    captured_at=datetime.now(timezone.utc),
                )
                for s in signals
            ]
            
            # Process through real service
            profile = await self.service.analyze_session(session_id, nc_signals)
            
            return {
                "approach_avoidance": profile.approach_tendency,
                "cognitive_load": profile.cognitive_load,
                "processing_fluency": profile.processing_fluency,
                "emotional_valence": profile.emotional_valence,
                "engagement_depth": profile.engagement_depth,
                "mechanism_hints": profile.mechanism_recommendations,
                "confidence": profile.confidence,
                "source": "real_nonconscious_analysis",
            }
        except Exception as e:
            logger.warning(f"Nonconscious analysis failed: {e}")
            return self._simulate_analysis(signals)
    
    def _simulate_analysis(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback simulation when real analysis unavailable."""
        return {
            "approach_avoidance": 0.2,
            "cognitive_load": 0.4,
            "processing_fluency": 0.6,
            "emotional_valence": 0.3,
            "engagement_depth": 0.5,
            "mechanism_hints": ["social_proof", "liking"],
            "confidence": 0.4,
            "source": "simulated",
        }


# =============================================================================
# REAL ATOM EXECUTOR
# =============================================================================

class RealAtomExecutor:
    """
    Uses actual Atom DAG execution for psychological reasoning.
    
    Executes:
    - RegulatoryFocusAtom: Promotion vs prevention orientation
    - ConstrualLevelAtom: Abstract vs concrete thinking
    - MechanismActivationAtom: Persuasion mechanism selection
    """
    
    def __init__(self, blackboard: Optional['BlackboardService'] = None):
        self.dag_executor = None
        self.blackboard = blackboard
        
        if PLATFORM_AVAILABLE:
            try:
                self.dag_executor = AtomDAGExecutor(blackboard=blackboard)
                logger.info("Real atom executor initialized")
            except Exception as e:
                logger.warning(f"Could not initialize atom executor: {e}")
    
    async def execute_reasoning(
        self,
        user_id: str,
        context: Dict[str, Any],
        traits: StableTraits,
        state: MomentaryState,
    ) -> Dict[str, Any]:
        """
        Execute full atom reasoning chain.
        
        Returns:
        - regulatory_focus: Promotion/prevention assessment
        - construal_level: Abstract/concrete assessment
        - mechanisms: Ranked persuasion mechanisms with scores
        - reasoning_trace: Full execution trace
        """
        if not self.dag_executor:
            return self._simulate_reasoning(traits, state)
        
        try:
            # Build atom input from context
            atom_input = AtomInput(
                user_id=user_id,
                request_id=str(uuid4()),
                context=context,
                user_traits={
                    "openness": traits.openness,
                    "conscientiousness": traits.conscientiousness,
                    "extraversion": traits.extraversion,
                    "agreeableness": traits.agreeableness,
                    "neuroticism": traits.neuroticism,
                },
                user_state={
                    "arousal": state.arousal,
                    "valence": state.valence,
                    "cognitive_load": state.cognitive_load,
                    "approach_tendency": state.approach_tendency,
                },
            )
            
            # Execute the DAG
            result = await self.dag_executor.execute(atom_input)
            
            return {
                "regulatory_focus": {
                    "promotion": result.outputs.get("regulatory_focus", {}).get("promotion", 0.5),
                    "prevention": result.outputs.get("regulatory_focus", {}).get("prevention", 0.5),
                    "confidence": result.outputs.get("regulatory_focus", {}).get("confidence", 0.7),
                },
                "construal_level": {
                    "abstract": result.outputs.get("construal_level", {}).get("abstract", 0.5),
                    "concrete": result.outputs.get("construal_level", {}).get("concrete", 0.5),
                    "confidence": result.outputs.get("construal_level", {}).get("confidence", 0.7),
                },
                "mechanisms": result.outputs.get("mechanisms", {}),
                "reasoning_trace": result.trace,
                "atoms_executed": result.atoms_executed,
                "execution_time_ms": result.execution_time_ms,
                "source": "real_atom_execution",
            }
        except Exception as e:
            logger.warning(f"Atom execution failed: {e}")
            return self._simulate_reasoning(traits, state)
    
    def _simulate_reasoning(
        self,
        traits: StableTraits,
        state: MomentaryState,
    ) -> Dict[str, Any]:
        """Fallback simulation when real atoms unavailable."""
        
        # Derive regulatory focus from traits + state
        promotion = (
            traits.extraversion * 0.3 +
            traits.openness * 0.2 +
            state.promotion_activated * 0.3 +
            (state.valence + 1) / 2 * 0.2
        )
        prevention = (
            traits.conscientiousness * 0.3 +
            traits.neuroticism * 0.2 +
            state.prevention_activated * 0.3 +
            (1 - state.approach_tendency) * 0.2
        )
        
        # Derive construal from state
        abstract = (
            traits.openness * 0.3 +
            state.construal_level * 0.4 +
            (1 - state.cognitive_load) * 0.3
        )
        
        # Mechanism scores
        mechanisms = {
            "social_proof": traits.extraversion * 0.4 + 0.4,
            "authority": traits.conscientiousness * 0.4 + 0.3,
            "scarcity": prevention * 0.5 + 0.3,
            "reciprocity": traits.agreeableness * 0.4 + 0.3,
            "liking": traits.extraversion * 0.3 + traits.agreeableness * 0.3 + 0.2,
            "commitment": traits.conscientiousness * 0.4 + 0.3,
            "novelty": traits.openness * 0.5 + promotion * 0.3,
            "urgency": promotion * 0.4 + state.arousal * 0.3,
        }
        
        return {
            "regulatory_focus": {
                "promotion": promotion,
                "prevention": prevention,
                "confidence": 0.65,
            },
            "construal_level": {
                "abstract": abstract,
                "concrete": 1 - abstract,
                "confidence": 0.65,
            },
            "mechanisms": mechanisms,
            "reasoning_trace": ["[Simulated] Regulatory Focus → Construal Level → Mechanism Activation"],
            "atoms_executed": ["RegulatoryFocusAtom", "ConstrualLevelAtom", "MechanismActivationAtom"],
            "execution_time_ms": 50,
            "source": "simulated",
        }


# =============================================================================
# REAL GRAPH CONTEXT
# =============================================================================

class RealGraphContext:
    """
    Pulls real context from Neo4j graph database.
    
    Retrieves:
    - User profile with Big Five scores
    - Mechanism effectiveness history
    - State trajectory over time
    - Category priors from Amazon data
    - Archetype matches for cold-start
    """
    
    def __init__(self, neo4j_driver=None):
        self.bridge = None
        
        if PLATFORM_AVAILABLE and neo4j_driver:
            try:
                self.bridge = InteractionBridge(neo4j_driver)
                logger.info("Real graph context initialized")
            except Exception as e:
                logger.warning(f"Could not initialize interaction bridge: {e}")
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Pull complete user context from graph.
        
        Returns:
        - profile: Big Five, regulatory focus, construal level
        - mechanism_history: Past mechanism effectiveness
        - state_history: Recent psychological states
        - archetypes: Matched Amazon archetypes
        - priors: Category-level psychological priors
        """
        if not self.bridge:
            return self._simulate_context(user_id)
        
        try:
            context = await self.bridge.pull_context(user_id)
            
            return {
                "profile": {
                    "big_five": context.profile.big_five if context.profile else {},
                    "regulatory_focus": context.profile.regulatory_focus if context.profile else {},
                    "construal_level": context.profile.construal_level if context.profile else 0.5,
                },
                "mechanism_history": [
                    {
                        "mechanism": h.mechanism_id,
                        "effectiveness": h.effectiveness,
                        "uses": h.use_count,
                    }
                    for h in (context.mechanism_history or [])
                ],
                "state_history": [
                    {
                        "arousal": s.arousal,
                        "valence": s.valence,
                        "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    }
                    for s in (context.state_history or [])[:5]
                ],
                "archetypes": [
                    {
                        "archetype_id": a.archetype_id,
                        "similarity": a.similarity,
                    }
                    for a in (context.archetype_matches or [])
                ],
                "category_priors": context.category_priors or {},
                "confidence": 0.8,
                "source": "real_graph_context",
            }
        except Exception as e:
            logger.warning(f"Graph context pull failed: {e}")
            return self._simulate_context(user_id)
    
    def _simulate_context(self, user_id: str) -> Dict[str, Any]:
        """Fallback simulation when graph unavailable."""
        return {
            "profile": {
                "big_five": {
                    "openness": 0.55,
                    "conscientiousness": 0.50,
                    "extraversion": 0.55,
                    "agreeableness": 0.52,
                    "neuroticism": 0.45,
                },
                "regulatory_focus": {"promotion": 0.55, "prevention": 0.45},
                "construal_level": 0.50,
            },
            "mechanism_history": [
                {"mechanism": "social_proof", "effectiveness": 0.72, "uses": 15},
                {"mechanism": "authority", "effectiveness": 0.68, "uses": 12},
            ],
            "state_history": [],
            "archetypes": [
                {"archetype_id": "explorer", "similarity": 0.75},
                {"archetype_id": "achiever", "similarity": 0.62},
            ],
            "category_priors": {},
            "confidence": 0.4,
            "source": "simulated",
        }


# =============================================================================
# REAL EMBEDDING SIMILARITY
# =============================================================================

class RealEmbeddingSimilarity:
    """
    Uses actual embedding service for semantic similarity.
    
    Provides:
    - Brand-audience semantic matching
    - Product-interest similarity
    - Copy effectiveness prediction from historical embeddings
    """
    
    def __init__(self):
        self.service = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.service = EmbeddingService()
                logger.info("Real embedding service initialized")
            except Exception as e:
                logger.warning(f"Could not initialize embedding service: {e}")
    
    async def find_similar_audiences(
        self,
        brand_description: str,
        product_description: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Find similar audiences based on brand/product embeddings.
        
        Returns:
        - similar_archetypes: Matching psychological archetypes
        - semantic_matches: Semantically similar successful campaigns
        - confidence: Match confidence
        """
        if not self.service:
            return self._simulate_similarity(brand_description, product_description)
        
        try:
            # Generate embedding for brand+product
            combined_text = f"{brand_description} {product_description}"
            embedding = await self.service.generate_embedding(combined_text)
            
            # Search for similar successful campaigns
            similar = await self.service.search_similar(
                embedding=embedding,
                collection="successful_campaigns",
                top_k=top_k,
            )
            
            return {
                "similar_archetypes": [
                    {
                        "archetype": match.metadata.get("archetype", "unknown"),
                        "similarity": match.similarity,
                        "successful_mechanism": match.metadata.get("mechanism"),
                    }
                    for match in similar
                ],
                "semantic_insights": [
                    f"Similar to {len(similar)} successful campaigns",
                    f"Top match: {similar[0].metadata.get('campaign_name', 'Unknown')}" if similar else "No matches",
                ],
                "confidence": 0.75,
                "source": "real_embedding_search",
            }
        except Exception as e:
            logger.warning(f"Embedding similarity failed: {e}")
            return self._simulate_similarity(brand_description, product_description)
    
    def _simulate_similarity(
        self,
        brand_description: str,
        product_description: str,
    ) -> Dict[str, Any]:
        """Fallback simulation when embeddings unavailable."""
        return {
            "similar_archetypes": [
                {"archetype": "explorer", "similarity": 0.72, "successful_mechanism": "novelty"},
                {"archetype": "achiever", "similarity": 0.65, "successful_mechanism": "authority"},
            ],
            "semantic_insights": [
                "Simulated archetype matching",
                "Connect embedding service for real semantic search",
            ],
            "confidence": 0.4,
            "source": "simulated",
        }


# =============================================================================
# INTEGRATED PLATFORM ENGINE
# =============================================================================

class IntegratedPlatformEngine:
    """
    Main engine that integrates real platform components with demo.
    
    Orchestrates:
    1. Graph context pull (if Neo4j available)
    2. Linguistic analysis (if text provided)
    3. Nonconscious signal processing (if signals provided)
    4. Atom DAG execution (real psychological reasoning)
    5. Mechanism selection and copy generation
    
    Falls back gracefully when components unavailable.
    """
    
    def __init__(
        self,
        neo4j_driver=None,
        redis_cache=None,
    ):
        self.status = PlatformStatus()
        
        # Initialize components
        self.linguistic_analyzer = RealLinguisticAnalyzer()
        self.nonconscious_analyzer = RealNonconsciousAnalyzer()
        self.graph_context = RealGraphContext(neo4j_driver)
        self.atom_executor = RealAtomExecutor()
        self.embedding_similarity = RealEmbeddingSimilarity()
        
        # Check what's available
        self._check_component_status()
    
    def _check_component_status(self):
        """Check which platform components are available."""
        
        self.status.linguistic_available = self.linguistic_analyzer.extractor is not None
        self.status.nonconscious_available = self.nonconscious_analyzer.service is not None
        self.status.atoms_available = self.atom_executor.dag_executor is not None
        self.status.embeddings_available = self.embedding_similarity.service is not None
        # Note: neo4j and redis require runtime connection check
        
        # Update "using real" flags
        self.status.using_real_linguistics = self.status.linguistic_available
        self.status.using_real_nonconscious = self.status.nonconscious_available
        self.status.using_real_atoms = self.status.atoms_available
    
    def get_status(self) -> PlatformStatus:
        """Get current platform status."""
        return self.status
    
    async def process_with_real_components(
        self,
        user_id: str,
        traits: StableTraits,
        state: MomentaryState,
        text_input: Optional[str] = None,
        nonconscious_signals: Optional[List[Dict]] = None,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Process request using real platform components where available.
        
        Returns comprehensive result with:
        - linguistic_analysis: Real text analysis (if text provided)
        - nonconscious_analysis: Real signal analysis (if signals provided)
        - graph_context: Real user context (if Neo4j connected)
        - atom_reasoning: Real psychological reasoning
        - sources_used: Which real components were used
        """
        results = {
            "sources_used": [],
            "components": {},
        }
        
        # 1. Linguistic analysis (if text provided)
        if text_input:
            linguistic = self.linguistic_analyzer.analyze_text(text_input)
            results["linguistic_analysis"] = linguistic
            if linguistic.get("source") == "real_linguistic_analysis":
                results["sources_used"].append("REAL_LINGUISTICS")
                self.status.using_real_linguistics = True
            results["components"]["linguistics"] = linguistic
        
        # 2. Nonconscious signals (if provided)
        if nonconscious_signals:
            session_id = str(uuid4())
            nonconscious = await self.nonconscious_analyzer.analyze_signals(
                session_id, nonconscious_signals
            )
            results["nonconscious_analysis"] = nonconscious
            if nonconscious.get("source") == "real_nonconscious_analysis":
                results["sources_used"].append("REAL_NONCONSCIOUS")
                self.status.using_real_nonconscious = True
            results["components"]["nonconscious"] = nonconscious
        
        # 3. Graph context
        graph = await self.graph_context.get_user_context(user_id)
        results["graph_context"] = graph
        if graph.get("source") == "real_graph_context":
            results["sources_used"].append("REAL_GRAPH")
            self.status.using_real_graph = True
        results["components"]["graph"] = graph
        
        # 4. Atom reasoning
        atom_result = await self.atom_executor.execute_reasoning(
            user_id=user_id,
            context=context or {},
            traits=traits,
            state=state,
        )
        results["atom_reasoning"] = atom_result
        if atom_result.get("source") == "real_atom_execution":
            results["sources_used"].append("REAL_ATOMS")
            self.status.using_real_atoms = True
        results["components"]["atoms"] = atom_result
        
        # 5. Embedding similarity search
        if text_input or context:
            brand_desc = context.get("brand", "") if context else ""
            product_desc = text_input or ""
            embedding_result = await self.embedding_similarity.find_similar_audiences(
                brand_description=brand_desc,
                product_description=product_desc,
            )
            results["embedding_similarity"] = embedding_result
            if embedding_result.get("source") == "real_embedding_search":
                results["sources_used"].append("REAL_EMBEDDINGS")
            results["components"]["embeddings"] = embedding_result
        
        # 6. Build summary
        results["platform_status"] = self.status.dict()
        results["any_real_components"] = len(results["sources_used"]) > 0
        
        return results


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_integrated_engine(
    neo4j_driver=None,
    redis_cache=None,
) -> IntegratedPlatformEngine:
    """
    Factory function to create integrated platform engine.
    
    Pass infrastructure connections for real component usage.
    Omit for simulation mode.
    """
    return IntegratedPlatformEngine(
        neo4j_driver=neo4j_driver,
        redis_cache=redis_cache,
    )
