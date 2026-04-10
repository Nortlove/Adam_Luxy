# =============================================================================
# Unified Psychological Intelligence Service
# Location: adam/intelligence/unified_psychological_intelligence.py
# =============================================================================

"""
Unified Psychological Intelligence - Central Integration Hub

This service integrates three powerful psychological analysis modules:
1. Flow State Detection - Audio/context-based flow state features
2. Need Detection - 33 psychological needs from brand-consumer alignment
3. Psycholinguistic Analysis - 32 constructs with 406 linguistic markers

Together, these provide the deepest possible psychological intelligence for
advertising personalization. Each module contributes unique insights that
combine to create a comprehensive understanding of customer psychology.

Integration Points:
- Review Intelligence: All customer reviews pass through all 3 analyzers
- Brand Analysis: Brand content analyzed for alignment opportunities
- Campaign Orchestrator: Insights feed into segment and copy recommendations
- Learning System: All insights emit signals to the Gradient Bridge
- Graph Database: Insights stored and queried for emergent patterns
- Local Storage: Persisted for future queries and continuous learning

Usage:
    from adam.intelligence.unified_psychological_intelligence import (
        UnifiedPsychologicalIntelligence,
        get_unified_intelligence
    )
    
    intelligence = get_unified_intelligence()
    
    # Analyze reviews with all 3 modules
    profile = await intelligence.analyze_reviews(
        reviews=customer_reviews,
        brand_content=brand_copy,
        brand_name="DeWalt",
        product_name="Impact Driver"
    )
    
    # Get unified psychological profile
    print(profile.psychological_constructs)  # 32 constructs
    print(profile.psychological_needs)        # 33 needs
    print(profile.flow_state_alignment)       # Flow state matching
    print(profile.unified_ad_recommendations) # Combined recommendations
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# INFRASTRUCTURE IMPORTS (OPTIONAL - GRACEFUL DEGRADATION)
# =============================================================================

# Neo4j Graph Service
try:
    from adam.intelligence.graph.unified_psychological_schema import (
        UnifiedPsychologicalGraphService,
    )
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    UnifiedPsychologicalGraphService = None

# Blackboard Service
try:
    from adam.blackboard.service import BlackboardService
    from adam.blackboard.models.zone2_reasoning import AtomReasoningSpace, AtomType
    from adam.blackboard.models.core import ComponentRole
    BLACKBOARD_AVAILABLE = True
except ImportError:
    BLACKBOARD_AVAILABLE = False
    BlackboardService = None

# Gradient Bridge (Direct)
try:
    from adam.gradient_bridge.service import GradientBridgeService
    from adam.gradient_bridge.models.signals import (
        LearningSignal,
        SignalType,
        SignalPriority,
    )
    GRADIENT_BRIDGE_AVAILABLE = True
except ImportError:
    GRADIENT_BRIDGE_AVAILABLE = False
    GradientBridgeService = None

# Kafka Event Bus
try:
    from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
    from adam.infrastructure.kafka.events import (
        AnalysisCompleteEvent,
        PsychologicalProfileEvent,
    )
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

# Prometheus Metrics
try:
    from adam.infrastructure.prometheus import get_metrics
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    def get_metrics():
        return None


# =============================================================================
# DATA MODELS
# =============================================================================

class InsightSource(Enum):
    """Source of psychological insight."""
    FLOW_STATE = "flow_state"
    NEED_DETECTION = "need_detection"
    PSYCHOLINGUISTIC = "psycholinguistic"
    UNIFIED = "unified"


@dataclass
class FlowStateProfile:
    """Flow state analysis results."""
    arousal: float = 0.5
    valence: float = 0.5
    energy: float = 0.5
    cognitive_load: float = 0.5
    nostalgia: float = 0.5
    social_energy: float = 0.5
    flow_stability: float = 0.5
    optimal_formats: List[str] = field(default_factory=list)
    ad_receptivity_score: float = 0.5
    recommended_tone: str = "balanced"
    
    @property
    def optimal_audio_formats(self) -> List[str]:
        """Alias for optimal_formats for compatibility."""
        return self.optimal_formats


@dataclass
class PsychologicalNeedsProfile:
    """33 psychological needs analysis results."""
    # Top detected needs with activation strength
    primary_needs: List[Tuple[str, float]] = field(default_factory=list)
    # By category
    identity_needs: Dict[str, float] = field(default_factory=dict)
    relationship_needs: Dict[str, float] = field(default_factory=dict)
    motivation_needs: Dict[str, float] = field(default_factory=dict)
    cognition_needs: Dict[str, float] = field(default_factory=dict)
    emotion_needs: Dict[str, float] = field(default_factory=dict)
    social_needs: Dict[str, float] = field(default_factory=dict)
    autonomy_needs: Dict[str, float] = field(default_factory=dict)
    security_needs: Dict[str, float] = field(default_factory=dict)
    meaning_needs: Dict[str, float] = field(default_factory=dict)
    sensory_needs: Dict[str, float] = field(default_factory=dict)
    # Regulatory focus
    promotion_focus: float = 0.5
    prevention_focus: float = 0.5
    # Alignment gaps (if brand content provided)
    alignment_gaps: List[Dict[str, Any]] = field(default_factory=list)
    unmet_needs: List[str] = field(default_factory=list)
    overall_alignment_score: float = 0.5
    
    @property
    def detected_needs(self) -> Dict[str, float]:
        """Return primary needs as a dictionary for compatibility."""
        return dict(self.primary_needs) if self.primary_needs else {}
    
    @property
    def alignment_score(self) -> float:
        """Alias for overall_alignment_score for compatibility."""
        return self.overall_alignment_score


@dataclass
class PsycholinguisticProfile:
    """32 psychological constructs analysis results."""
    # Core constructs (0-1 scores)
    construal_level: float = 0.5  # Abstract (1) vs Concrete (0)
    need_for_cognition: float = 0.5
    regulatory_focus_promotion: float = 0.5
    regulatory_focus_prevention: float = 0.5
    hedonic_motivation: float = 0.5
    utilitarian_motivation: float = 0.5
    emotional_valence: float = 0.5
    emotional_arousal: float = 0.5
    maximizer_tendency: float = 0.5
    impulsivity: float = 0.5
    risk_tolerance: float = 0.5
    attitude_certainty: float = 0.5
    deal_proneness: float = 0.5
    temporal_focus_past: float = 0.5
    temporal_focus_present: float = 0.5
    temporal_focus_future: float = 0.5
    self_construal_independent: float = 0.5
    self_construal_interdependent: float = 0.5
    authenticity: float = 0.5
    expertise_level: float = 0.5
    # Additional emotional constructs
    anger: float = 0.0
    fear: float = 0.0
    gratitude: float = 0.5
    nostalgia: float = 0.5
    # All constructs as dict for easy access
    all_constructs: Dict[str, float] = field(default_factory=dict)
    # Confidence scores
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    # Evidence
    marker_matches: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def construct_scores(self) -> Dict[str, float]:
        """Alias for all_constructs for compatibility."""
        return self.all_constructs


@dataclass
class UnifiedAdRecommendation:
    """Unified advertising recommendation from all 3 modules."""
    recommendation_id: str
    priority_score: float
    construct_name: str
    recommendation: str
    supporting_evidence: List[str]
    source_modules: List[InsightSource]
    effect_size: Optional[float] = None
    confidence: float = 0.5
    example_language: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    
    @property
    def recommendation_text(self) -> str:
        """Alias for recommendation for compatibility."""
        return self.recommendation
    
    @property
    def psychological_basis(self) -> str:
        """Alias for construct_name for compatibility."""
        return self.construct_name


@dataclass
class UnifiedPsychologicalProfile:
    """Complete unified psychological profile from all 3 modules."""
    profile_id: str
    brand_name: str
    product_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Individual module profiles
    flow_state: FlowStateProfile = field(default_factory=FlowStateProfile)
    psychological_needs: PsychologicalNeedsProfile = field(default_factory=PsychologicalNeedsProfile)
    psycholinguistic: PsycholinguisticProfile = field(default_factory=PsycholinguisticProfile)
    
    # Unified insights
    unified_constructs: Dict[str, float] = field(default_factory=dict)
    unified_ad_recommendations: List[UnifiedAdRecommendation] = field(default_factory=list)
    
    # Segment indicators
    primary_archetype: str = "Unknown"
    archetype_confidence: float = 0.0
    segment_characteristics: List[str] = field(default_factory=list)
    
    # Mechanism predictions (for ad delivery)
    mechanism_predictions: Dict[str, float] = field(default_factory=dict)
    
    # Processing metadata
    reviews_analyzed: int = 0
    analysis_time_ms: float = 0.0
    modules_used: List[str] = field(default_factory=list)
    
    @property
    def ad_recommendations(self) -> List[UnifiedAdRecommendation]:
        """Alias for unified_ad_recommendations for compatibility."""
        return self.unified_ad_recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile_id": self.profile_id,
            "brand_name": self.brand_name,
            "product_name": self.product_name,
            "created_at": self.created_at.isoformat(),
            "flow_state": {
                "arousal": self.flow_state.arousal,
                "valence": self.flow_state.valence,
                "energy": self.flow_state.energy,
                "cognitive_load": self.flow_state.cognitive_load,
                "optimal_formats": self.flow_state.optimal_formats,
                "recommended_tone": self.flow_state.recommended_tone,
            },
            "psychological_needs": {
                "primary_needs": self.psychological_needs.primary_needs,
                "promotion_focus": self.psychological_needs.promotion_focus,
                "prevention_focus": self.psychological_needs.prevention_focus,
                "alignment_gaps": self.psychological_needs.alignment_gaps[:5],
                "unmet_needs": self.psychological_needs.unmet_needs,
                "overall_alignment_score": self.psychological_needs.overall_alignment_score,
            },
            "psycholinguistic": {
                "construal_level": self.psycholinguistic.construal_level,
                "need_for_cognition": self.psycholinguistic.need_for_cognition,
                "emotional_valence": self.psycholinguistic.emotional_valence,
                "emotional_arousal": self.psycholinguistic.emotional_arousal,
                "risk_tolerance": self.psycholinguistic.risk_tolerance,
                "deal_proneness": self.psycholinguistic.deal_proneness,
                "all_constructs": self.psycholinguistic.all_constructs,
            },
            "unified_constructs": self.unified_constructs,
            "unified_ad_recommendations": [
                {
                    "priority_score": r.priority_score,
                    "construct_name": r.construct_name,
                    "recommendation": r.recommendation,
                    "confidence": r.confidence,
                }
                for r in self.unified_ad_recommendations[:10]
            ],
            "primary_archetype": self.primary_archetype,
            "archetype_confidence": self.archetype_confidence,
            "mechanism_predictions": self.mechanism_predictions,
            "reviews_analyzed": self.reviews_analyzed,
            "analysis_time_ms": self.analysis_time_ms,
        }
    
    def to_graph_data(self) -> Dict[str, Any]:
        """Convert to data suitable for Neo4j storage."""
        return {
            "profile_id": self.profile_id,
            "brand_name": self.brand_name,
            "product_name": self.product_name,
            "created_at": self.created_at.isoformat(),
            # Flattened constructs for graph properties
            **{f"construct_{k}": v for k, v in self.unified_constructs.items()},
            # Flow state
            "flow_arousal": self.flow_state.arousal,
            "flow_valence": self.flow_state.valence,
            "flow_energy": self.flow_state.energy,
            # Needs
            "promotion_focus": self.psychological_needs.promotion_focus,
            "prevention_focus": self.psychological_needs.prevention_focus,
            # Mechanisms
            **{f"mechanism_{k}": v for k, v in self.mechanism_predictions.items()},
        }


# =============================================================================
# UNIFIED PSYCHOLOGICAL INTELLIGENCE SERVICE
# =============================================================================

class UnifiedPsychologicalIntelligence:
    """
    Central integration hub for all psychological analysis modules.
    
    Coordinates:
    1. Flow State Detection (audio_flow_state.py)
    2. Need Detection (need_detection/)
    3. Psycholinguistic Analysis (psycholinguistic_graph2/)
    
    And integrates with:
    - Neo4j Graph Database (for profile storage and queries)
    - Blackboard Service (for cross-component state sharing)
    - Gradient Bridge (for learning signal propagation)
    - Kafka Event Bus (for event-driven architecture)
    - Prometheus (for observability metrics)
    - Review Orchestrator (for review analysis)
    - Campaign Orchestrator (for recommendations)
    """
    
    def __init__(
        self,
        neo4j_driver=None,
        blackboard_service: Optional['BlackboardService'] = None,
        gradient_bridge: Optional['GradientBridgeService'] = None,
    ):
        """
        Initialize the unified intelligence service.
        
        Args:
            neo4j_driver: Neo4j driver for graph storage
            blackboard_service: Blackboard for shared state
            gradient_bridge: Gradient bridge for learning signals
        """
        # Analysis modules
        self._flow_state_engine = None
        self._need_analyzer = None
        self._psycholinguistic_analyzer = None
        self._initialized = False
        self._loaded_modules: List[str] = []
        self._station_profiles: Dict[str, Dict[str, float]] = {}
        
        # Infrastructure services
        self._neo4j_driver = neo4j_driver
        self._graph_service: Optional[UnifiedPsychologicalGraphService] = None
        self._blackboard = blackboard_service
        self._gradient_bridge = gradient_bridge
        self._kafka_producer = None
        self._metrics = get_metrics() if PROMETHEUS_AVAILABLE else None
        
        # Service availability flags
        self._neo4j_connected = False
        self._blackboard_connected = False
        self._gradient_bridge_connected = False
        self._kafka_connected = False
    
    async def initialize(self) -> bool:
        """
        Initialize all analysis modules.
        
        Returns True if at least one module loaded successfully.
        """
        modules_loaded = []
        
        # Add adam-platform root to path if needed
        import sys
        from pathlib import Path
        adam_platform_root = Path("/Users/chrisnocera/Sites/adam-platform")
        if str(adam_platform_root) not in sys.path:
            sys.path.insert(0, str(adam_platform_root))
        
        # Initialize Flow State Engine
        try:
            from flow_state.audio_flow_state import AudioFlowStateEngine, STATION_FORMAT_PROFILES
            self._flow_state_engine = AudioFlowStateEngine()
            self._station_profiles = STATION_FORMAT_PROFILES
            modules_loaded.append("flow_state")
            logger.info("Flow State Engine initialized successfully")
        except ImportError as e:
            logger.warning(f"Flow State module not available: {e}")
            # Fallback: use default station profiles
            self._station_profiles = self._get_default_station_profiles()
        
        # Initialize Need Detection Analyzer
        try:
            # Need detection has internal absolute imports, so add its directory to path
            need_detection_path = adam_platform_root / "need_detection"
            if str(need_detection_path) not in sys.path:
                sys.path.insert(0, str(need_detection_path))
            
            # Import the analyzer directly to avoid issues with extended_detection
            from analyzer import BrandConsumerAlignmentAnalyzer
            self._need_analyzer = BrandConsumerAlignmentAnalyzer()
            modules_loaded.append("need_detection")
            logger.info("Need Detection Analyzer initialized successfully")
        except ImportError as e:
            logger.warning(f"Need Detection module not available: {e}")
        
        # Initialize Psycholinguistic Analyzer
        try:
            # Add psycholinguistic_graph2 directory to path to handle internal imports
            psych_path = adam_platform_root / "psycholinguistic_graph2"
            if str(psych_path) not in sys.path:
                sys.path.insert(0, str(psych_path))
            
            # Import directly from the langgraph_pipeline module
            from langgraph_pipeline import PsycholinguisticAnalyzer
            self._psycholinguistic_analyzer = PsycholinguisticAnalyzer()
            modules_loaded.append("psycholinguistic")
            logger.info("Psycholinguistic Analyzer initialized successfully")
        except ImportError as e:
            logger.warning(f"Psycholinguistic module not available: {e}")
        
        self._loaded_modules = modules_loaded
        self._initialized = len(modules_loaded) > 0
        logger.info(f"Unified Intelligence initialized with modules: {modules_loaded}")
        
        # Initialize infrastructure services (non-blocking, graceful degradation)
        await self._initialize_infrastructure()
        
        return self._initialized
    
    async def _initialize_infrastructure(self) -> None:
        """
        Initialize all infrastructure services.
        
        Uses graceful degradation - failures don't prevent operation.
        """
        # 1. Initialize Neo4j Graph Service
        if NEO4J_AVAILABLE and self._neo4j_driver:
            try:
                self._graph_service = UnifiedPsychologicalGraphService(self._neo4j_driver)
                await self._graph_service.initialize_schema()
                self._neo4j_connected = True
                logger.info("Neo4j Graph Service connected")
            except Exception as e:
                logger.warning(f"Neo4j connection failed (non-critical): {e}")
        
        # 2. Initialize Blackboard Service (if not provided)
        if BLACKBOARD_AVAILABLE and self._blackboard is None:
            try:
                from adam.infrastructure.redis import ADAMRedisCache
                cache = ADAMRedisCache()
                self._blackboard = BlackboardService(cache)
                self._blackboard_connected = True
                logger.info("Blackboard Service connected")
            except Exception as e:
                logger.debug(f"Blackboard not available (non-critical): {e}")
        elif self._blackboard is not None:
            self._blackboard_connected = True
        
        # 3. Initialize Gradient Bridge (if not provided)
        if GRADIENT_BRIDGE_AVAILABLE and self._gradient_bridge is None:
            try:
                # Gradient Bridge requires additional dependencies
                logger.debug("Gradient Bridge available, using when explicitly provided")
            except Exception as e:
                logger.debug(f"Gradient Bridge not available (non-critical): {e}")
        elif self._gradient_bridge is not None:
            self._gradient_bridge_connected = True
        
        # 4. Initialize Kafka Producer
        if KAFKA_AVAILABLE:
            try:
                self._kafka_producer = get_kafka_producer()
                self._kafka_connected = True
                logger.info("Kafka producer connected")
            except Exception as e:
                logger.debug(f"Kafka not available (non-critical): {e}")
        
        # Log infrastructure status
        logger.info(
            f"Infrastructure status: Neo4j={self._neo4j_connected}, "
            f"Blackboard={self._blackboard_connected}, "
            f"GradientBridge={self._gradient_bridge_connected}, "
            f"Kafka={self._kafka_connected}"
        )
    
    async def analyze_reviews(
        self,
        reviews: List[str],
        brand_content: Optional[Dict[str, List[str]]] = None,
        brand_name: str = "Brand",
        product_name: str = "Product",
        brand_text: Optional[str] = None,  # Alias for simpler brand content
        include_flow_state: bool = True,
        include_needs: bool = True,
        include_psycholinguistic: bool = True,
    ) -> UnifiedPsychologicalProfile:
        """
        Analyze reviews using all available psychological analysis modules.
        
        Args:
            reviews: List of customer review texts
            brand_content: Optional dict of brand content by type
                          {'website': [...], 'ads': [...], 'descriptions': [...]}
            brand_name: Brand name for the analysis
            product_name: Product name for the analysis
            include_flow_state: Whether to include flow state analysis
            include_needs: Whether to include need detection analysis
            include_psycholinguistic: Whether to include psycholinguistic analysis
            
        Returns:
            UnifiedPsychologicalProfile with insights from all modules
        """
        import time
        import uuid
        
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        # Handle brand_text as simple alias for brand_content
        if brand_text and not brand_content:
            brand_content = {"descriptions": [brand_text]}
        
        profile = UnifiedPsychologicalProfile(
            profile_id=str(uuid.uuid4())[:8],
            brand_name=brand_name,
            product_name=product_name,
            reviews_analyzed=len(reviews),
        )
        
        # Combine all reviews for analysis
        combined_text = " ".join(reviews)
        
        # =====================================================================
        # PHASE 1: FOUNDATIONAL LINGUISTIC ANALYSIS (Psycholinguistic)
        # =====================================================================
        # This MUST run first - it provides the psychological fingerprint that
        # enhances all subsequent analyses
        # ---------------------------------------------------------------------
        # OUTPUTS that cascade downstream:
        # - regulatory_focus → weights need detection priorities
        # - construal_level → interprets need expression style
        # - emotional_state → contextualizes need importance
        # - need_for_cognition → determines message complexity
        # =====================================================================
        if include_psycholinguistic and self._psycholinguistic_analyzer:
            try:
                psych_profile = await self._analyze_psycholinguistic(reviews)
                profile.psycholinguistic = psych_profile
                profile.modules_used.append("psycholinguistic")
                logger.info(
                    f"PHASE 1 Complete - Psycholinguistic: "
                    f"{len(psych_profile.all_constructs)} constructs, "
                    f"reg_focus={psych_profile.regulatory_focus_promotion:.2f}P/{psych_profile.regulatory_focus_prevention:.2f}V"
                )
            except Exception as e:
                logger.error(f"PHASE 1 Failed - Psycholinguistic: {e}")
        
        # =====================================================================
        # PHASE 2: CONTEXT-AWARE NEED DETECTION (Enhanced by Phase 1)
        # =====================================================================
        # Uses Phase 1 insights to WEIGHT and CONTEXTUALIZE need detection:
        # - Promotion-focused consumers → amplify growth/achievement needs
        # - Prevention-focused consumers → amplify security/protection needs
        # - Abstract construal → detect meaning/purpose needs more strongly
        # - Concrete construal → detect functional/practical needs
        # - High emotional valence → relationship needs more salient
        # - Low emotional valence → comfort/security needs more salient
        # =====================================================================
        if include_needs and self._need_analyzer:
            try:
                # Pass psycholinguistic context to enhance need detection
                needs_profile = await self._analyze_needs_enhanced(
                    reviews=reviews,
                    brand_content=brand_content,
                    brand_name=brand_name,
                    psycholinguistic_context=profile.psycholinguistic,
                )
                profile.psychological_needs = needs_profile
                profile.modules_used.append("need_detection")
                logger.info(
                    f"PHASE 2 Complete - Needs: "
                    f"{len(needs_profile.primary_needs)} needs, "
                    f"alignment={needs_profile.overall_alignment_score:.2f}"
                )
            except Exception as e:
                logger.error(f"PHASE 2 Failed - Need Detection: {e}")
        
        # =====================================================================
        # PHASE 3: OPTIMAL DELIVERY STATE (Enhanced by Phases 1 & 2)
        # =====================================================================
        # Uses Phase 1 + Phase 2 to determine optimal ad delivery:
        # - Arousal/valence from Phase 1 → flow state baseline
        # - Emotional needs from Phase 2 → adjusts receptivity
        #   - emotion_arousal need → increase receptivity for high-energy ads
        #   - emotion_comfort need → increase receptivity for calm ads
        # - Cognitive needs from Phase 2 → adjusts format selection
        #   - High cognition need → longer, detailed formats
        #   - Low cognitive tolerance → shorter, visual formats
        # =====================================================================
        if include_flow_state:
            try:
                # Pass both psycholinguistic AND needs context
                flow_profile = await self._analyze_flow_state_enhanced(
                    psycholinguistic_profile=profile.psycholinguistic,
                    needs_profile=profile.psychological_needs,
                )
                profile.flow_state = flow_profile
                profile.modules_used.append("flow_state")
                logger.info(
                    f"PHASE 3 Complete - Flow State: "
                    f"receptivity={flow_profile.ad_receptivity_score:.2f}, "
                    f"tone={flow_profile.recommended_tone}"
                )
            except Exception as e:
                logger.error(f"PHASE 3 Failed - Flow State: {e}")
        
        # =====================================================================
        # UNIFIED SYNTHESIS
        # =====================================================================
        profile = await self._synthesize_unified_profile(profile)
        
        profile.analysis_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Unified analysis complete for {brand_name} {product_name}: "
            f"{len(profile.unified_ad_recommendations)} recommendations, "
            f"{profile.analysis_time_ms:.0f}ms"
        )
        
        return profile
    
    async def _analyze_psycholinguistic(
        self,
        reviews: List[str],
    ) -> PsycholinguisticProfile:
        """Analyze reviews using psycholinguistic constructs."""
        profile = PsycholinguisticProfile()
        
        # Aggregate results from all reviews
        all_constructs: Dict[str, List[float]] = {}
        all_confidences: Dict[str, List[float]] = {}
        all_markers = []
        
        for review in reviews:
            result = self._psycholinguistic_analyzer.analyze_customer(review)
            
            # Collect construct scores
            for construct_id, score in result.get("psychological_profile", {}).items():
                if construct_id not in all_constructs:
                    all_constructs[construct_id] = []
                all_constructs[construct_id].append(score)
            
            # Collect confidence scores
            for construct_id, conf in result.get("confidence_scores", {}).items():
                if construct_id not in all_confidences:
                    all_confidences[construct_id] = []
                all_confidences[construct_id].append(conf)
            
            # Collect marker matches
            all_markers.extend(result.get("marker_matches", [])[:5])
        
        # Average across reviews
        for construct_id, scores in all_constructs.items():
            avg_score = sum(scores) / len(scores)
            profile.all_constructs[construct_id] = avg_score
            
            # Set individual attributes
            if hasattr(profile, construct_id):
                setattr(profile, construct_id, avg_score)
        
        for construct_id, confs in all_confidences.items():
            profile.confidence_scores[construct_id] = sum(confs) / len(confs)
        
        profile.marker_matches = all_markers[:20]  # Top 20 markers
        
        return profile
    
    async def _analyze_needs_enhanced(
        self,
        reviews: List[str],
        brand_content: Optional[Dict[str, List[str]]],
        brand_name: str,
        psycholinguistic_context: Optional[PsycholinguisticProfile] = None,
    ) -> PsychologicalNeedsProfile:
        """
        Analyze reviews using 33 psychological needs - ENHANCED by Phase 1 context.
        
        Enhancement Strategy:
        1. Regulatory Focus Weighting: Phase 1 regulatory focus amplifies matching needs
           - Promotion focus → amplify motivation_promotion, identity_self_expression
           - Prevention focus → amplify security_safety, motivation_prevention
        
        2. Construal Level Interpretation:
           - Abstract (high) → meaning/purpose needs weighted higher
           - Concrete (low) → functional/practical needs weighted higher
        
        3. Emotional State Contextualization:
           - High valence → relationship needs more salient
           - Low valence → comfort/security needs more salient
        """
        profile = PsychologicalNeedsProfile()
        
        # Calculate Phase 1 enhancement weights
        promo_weight = 1.0
        prevent_weight = 1.0
        abstract_weight = 1.0
        concrete_weight = 1.0
        relationship_weight = 1.0
        security_weight = 1.0
        
        if psycholinguistic_context:
            # Regulatory focus enhancement
            reg_diff = psycholinguistic_context.regulatory_focus_promotion - psycholinguistic_context.regulatory_focus_prevention
            if reg_diff > 0.1:  # Promotion-dominant
                promo_weight = 1.0 + (reg_diff * 0.5)  # Up to 1.25x
                prevent_weight = 1.0 - (reg_diff * 0.3)  # Down to 0.85x
            elif reg_diff < -0.1:  # Prevention-dominant
                prevent_weight = 1.0 + (abs(reg_diff) * 0.5)
                promo_weight = 1.0 - (abs(reg_diff) * 0.3)
            
            # Construal level enhancement
            construal = psycholinguistic_context.construal_level
            if construal > 0.6:  # Abstract thinker
                abstract_weight = 1.0 + ((construal - 0.5) * 0.6)  # Amplify meaning needs
            elif construal < 0.4:  # Concrete thinker
                concrete_weight = 1.0 + ((0.5 - construal) * 0.6)  # Amplify functional needs
            
            # Emotional valence enhancement
            valence = psycholinguistic_context.emotional_valence
            if valence > 0.6:  # Positive emotional state
                relationship_weight = 1.0 + ((valence - 0.5) * 0.5)
            elif valence < 0.4:  # Negative emotional state
                security_weight = 1.0 + ((0.5 - valence) * 0.5)
        
        # Analyze consumer texts
        need_scores: Dict[str, List[float]] = {}
        regulatory_focus_scores = {"promotion": [], "prevention": []}
        
        for review in reviews:
            result = self._need_analyzer.analyze_single_consumer_text(review)
            
            # Collect need detections with enhancement weights
            for need in result.get("detected_needs", []):
                need_id = need.get("need_id", "")
                confidence = need.get("confidence", 0.5)
                
                # Apply Phase 1 enhancement weights based on need category
                weight = 1.0
                if need_id.startswith("motivation_promotion") or need_id.startswith("identity_"):
                    weight *= promo_weight
                elif need_id.startswith("motivation_prevention") or need_id.startswith("security_"):
                    weight *= prevent_weight
                    weight *= security_weight
                elif need_id.startswith("meaning_") or need_id.startswith("cognition_"):
                    weight *= abstract_weight
                elif need_id.startswith("sensory_") or need_id.startswith("autonomy_"):
                    weight *= concrete_weight
                elif need_id.startswith("relationship_") or need_id.startswith("social_"):
                    weight *= relationship_weight
                
                weighted_confidence = min(1.0, confidence * weight)
                
                if need_id not in need_scores:
                    need_scores[need_id] = []
                need_scores[need_id].append(weighted_confidence)
            
            # Collect regulatory focus
            reg_focus = result.get("regulatory_focus", {})
            if reg_focus.get("promotion", 0) > 0:
                regulatory_focus_scores["promotion"].append(reg_focus.get("promotion", 0))
            if reg_focus.get("prevention", 0) > 0:
                regulatory_focus_scores["prevention"].append(reg_focus.get("prevention", 0))
        
        # Calculate averages and sort primary needs
        for need_id, scores in need_scores.items():
            avg_score = sum(scores) / len(scores)
            profile.primary_needs.append((need_id, avg_score))
            
            # Categorize needs
            if need_id.startswith("identity_"):
                profile.identity_needs[need_id] = avg_score
            elif need_id.startswith("relationship_"):
                profile.relationship_needs[need_id] = avg_score
            elif need_id.startswith("motivation_"):
                profile.motivation_needs[need_id] = avg_score
            elif need_id.startswith("cognition_"):
                profile.cognition_needs[need_id] = avg_score
            elif need_id.startswith("emotion_"):
                profile.emotion_needs[need_id] = avg_score
            elif need_id.startswith("social_"):
                profile.social_needs[need_id] = avg_score
            elif need_id.startswith("autonomy_"):
                profile.autonomy_needs[need_id] = avg_score
            elif need_id.startswith("security_"):
                profile.security_needs[need_id] = avg_score
            elif need_id.startswith("meaning_"):
                profile.meaning_needs[need_id] = avg_score
            elif need_id.startswith("sensory_"):
                profile.sensory_needs[need_id] = avg_score
        
        # Sort by score
        profile.primary_needs.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate regulatory focus - ENHANCE with Phase 1 if available
        if regulatory_focus_scores["promotion"]:
            base_promo = sum(regulatory_focus_scores["promotion"]) / len(regulatory_focus_scores["promotion"])
            # Blend with Phase 1 regulatory focus (70% need detection, 30% psycholinguistic)
            if psycholinguistic_context:
                profile.promotion_focus = (
                    base_promo * 0.7 + 
                    psycholinguistic_context.regulatory_focus_promotion * 0.3
                )
            else:
                profile.promotion_focus = base_promo
        elif psycholinguistic_context:
            profile.promotion_focus = psycholinguistic_context.regulatory_focus_promotion
            
        if regulatory_focus_scores["prevention"]:
            base_prevent = sum(regulatory_focus_scores["prevention"]) / len(regulatory_focus_scores["prevention"])
            if psycholinguistic_context:
                profile.prevention_focus = (
                    base_prevent * 0.7 + 
                    psycholinguistic_context.regulatory_focus_prevention * 0.3
                )
            else:
                profile.prevention_focus = base_prevent
        elif psycholinguistic_context:
            profile.prevention_focus = psycholinguistic_context.regulatory_focus_prevention
        
        # If brand content provided, analyze alignment
        if brand_content:
            try:
                report = self._need_analyzer.analyze(
                    consumer_texts=reviews,
                    brand_texts=brand_content,
                    brand_name=brand_name,
                )
                profile.overall_alignment_score = report.overall_alignment_score
                profile.unmet_needs = report.unmet_needs
                
                # Extract alignment gaps - these are KEY for mechanism prediction
                for gap in report.alignment_gaps[:10]:
                    profile.alignment_gaps.append({
                        "need_id": gap.need_id,
                        "need_name": gap.need_name,
                        "status": gap.status.name,
                        "severity": gap.severity,
                        "recommended_actions": gap.recommended_actions[:2],
                        "priority_score": gap.priority_score,
                    })
            except Exception as e:
                logger.warning(f"Brand alignment analysis failed: {e}")
        
        return profile
    
    async def _analyze_flow_state_enhanced(
        self,
        psycholinguistic_profile: PsycholinguisticProfile,
        needs_profile: Optional[PsychologicalNeedsProfile] = None,
    ) -> FlowStateProfile:
        """
        Analyze flow state - ENHANCED by Phase 1 & Phase 2 context.
        
        Enhancement Strategy:
        1. Phase 1 (Psycholinguistic) provides baseline arousal/valence/energy
        2. Phase 2 (Needs) adjusts receptivity based on emotional needs:
           - emotion_arousal need → INCREASE receptivity for high-energy ads
           - emotion_comfort need → INCREASE receptivity for calm ads
        3. Phase 2 (Needs) adjusts format selection:
           - High cognition need → prefer detailed, informative formats
           - High sensory need → prefer experiential, immersive formats
        
        Key Insight: Ad receptivity is NOT just about being open to ads,
        it's about being in a state where the RIGHT ad will resonate.
        """
        profile = FlowStateProfile()
        
        # Map psycholinguistic constructs to flow state dimensions (Phase 1 baseline)
        profile.arousal = psycholinguistic_profile.emotional_arousal
        profile.valence = psycholinguistic_profile.emotional_valence
        
        # Energy from hedonic motivation and arousal
        profile.energy = (
            psycholinguistic_profile.hedonic_motivation * 0.4 +
            psycholinguistic_profile.emotional_arousal * 0.6
        )
        
        # Cognitive load from need for cognition
        profile.cognitive_load = psycholinguistic_profile.need_for_cognition * 0.8
        
        # Nostalgia directly
        profile.nostalgia = psycholinguistic_profile.nostalgia
        
        # Social energy from interdependent self-construal
        profile.social_energy = psycholinguistic_profile.self_construal_interdependent
        
        # Flow stability (high certainty + low impulsivity = stable)
        profile.flow_stability = (
            psycholinguistic_profile.attitude_certainty * 0.5 +
            (1 - psycholinguistic_profile.impulsivity) * 0.5
        )
        
        # =====================================================================
        # PHASE 2 ENHANCEMENT: Use needs to refine flow state
        # =====================================================================
        receptivity_modifier = 0.0
        format_preference_weights = {}
        
        if needs_profile:
            # Emotional need modifiers for receptivity
            emotion_arousal = needs_profile.emotion_needs.get("emotion_arousal", 0)
            emotion_comfort = needs_profile.emotion_needs.get("emotion_comfort", 0)
            
            # If customer has HIGH arousal needs and current state is HIGH arousal,
            # they're more receptive to high-energy ads
            if emotion_arousal > 0.3 and profile.arousal > 0.6:
                receptivity_modifier += 0.1  # Boost receptivity
            
            # If customer has comfort needs and current state is calm,
            # they're more receptive to soothing ads
            if emotion_comfort > 0.3 and profile.arousal < 0.4:
                receptivity_modifier += 0.1
            
            # Cognitive need modifiers for format selection
            cognition_needs = sum(needs_profile.cognition_needs.values()) / max(len(needs_profile.cognition_needs), 1)
            if cognition_needs > 0.3:
                # Prefer formats that allow for detailed content
                format_preference_weights["news_talk"] = 0.1
                format_preference_weights["podcast"] = 0.1
                profile.cognitive_load = min(1.0, profile.cognitive_load + 0.1)
            
            # Sensory need modifiers
            sensory_needs = sum(needs_profile.sensory_needs.values()) / max(len(needs_profile.sensory_needs), 1)
            if sensory_needs > 0.3:
                # Prefer formats that are experiential
                format_preference_weights["edm"] = 0.1
                format_preference_weights["hip_hop"] = 0.1
                profile.energy = min(1.0, profile.energy + 0.1)
            
            # Social need modifiers
            social_belonging = needs_profile.social_needs.get("social_belonging", 0)
            if social_belonging > 0.3:
                profile.social_energy = min(1.0, profile.social_energy + 0.15)
            
            # Security need modifiers
            security_needs = sum(needs_profile.security_needs.values()) / max(len(needs_profile.security_needs), 1)
            if security_needs > 0.3:
                # Prefer stable, familiar formats
                format_preference_weights["classic_rock"] = 0.1
                format_preference_weights["adult_contemporary"] = 0.1
                profile.flow_stability = min(1.0, profile.flow_stability + 0.1)
        
        # Determine optimal formats with need-weighted preferences
        profile.optimal_formats = self._determine_optimal_formats_enhanced(
            profile, format_preference_weights
        )
        
        # Ad receptivity calculation - ENHANCED with needs context
        base_receptivity = (
            (1 - profile.cognitive_load) * 0.35 +  # Lower load = more receptive
            profile.valence * 0.25 +               # Positive mood = more receptive
            profile.flow_stability * 0.25 +        # Stable state = more receptive
            (1 - abs(profile.arousal - 0.5)) * 0.15  # Moderate arousal is optimal
        )
        profile.ad_receptivity_score = min(1.0, base_receptivity + receptivity_modifier)
        
        # Recommended tone - ENHANCED with needs context
        profile.recommended_tone = self._determine_recommended_tone_enhanced(
            profile, needs_profile
        )
        
        return profile
    
    def _determine_optimal_formats_enhanced(
        self,
        profile: FlowStateProfile,
        preference_weights: Dict[str, float],
    ) -> List[str]:
        """Determine optimal formats with need-based preference weights."""
        matches = []
        
        for format_name, format_profile in self._station_profiles.items():
            if format_name == "unknown":
                continue
            
            # Calculate match score
            arousal_diff = abs(format_profile.get("arousal", 0.5) - profile.arousal)
            valence_diff = abs(format_profile.get("valence", 0.5) - profile.valence)
            energy_diff = abs(format_profile.get("energy", 0.5) - profile.energy)
            
            # Weighted distance
            distance = (arousal_diff * 0.4 + valence_diff * 0.3 + energy_diff * 0.3)
            match_score = 1 - distance
            
            # Apply need-based preference weights
            match_score += preference_weights.get(format_name, 0)
            
            matches.append((format_name, match_score))
        
        # Sort by match score
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return [f[0] for f in matches[:5]]
    
    def _determine_recommended_tone_enhanced(
        self,
        profile: FlowStateProfile,
        needs_profile: Optional[PsychologicalNeedsProfile],
    ) -> str:
        """Determine recommended tone - enhanced with needs context."""
        # Get dominant need category if available
        dominant_need_category = None
        if needs_profile and needs_profile.primary_needs:
            top_need = needs_profile.primary_needs[0][0]
            if "_" in top_need:
                dominant_need_category = top_need.split("_")[0]
        
        # Enhanced tone determination
        if profile.arousal > 0.7 and profile.valence > 0.6:
            if dominant_need_category == "emotion":
                return "exciting_inspiring"
            return "energetic_positive"
        elif profile.arousal > 0.7 and profile.valence < 0.4:
            if dominant_need_category == "security":
                return "protective_urgent"
            return "urgent_action"
        elif profile.arousal < 0.4 and profile.valence > 0.6:
            if dominant_need_category == "relationship":
                return "warm_connecting"
            return "calm_reassuring"
        elif profile.arousal < 0.4 and profile.valence < 0.4:
            if dominant_need_category == "meaning":
                return "reflective_purposeful"
            return "empathetic_supportive"
        elif profile.nostalgia > 0.6:
            return "nostalgic_familiar"
        elif profile.cognitive_load > 0.6:
            if dominant_need_category == "cognition":
                return "educational_detailed"
            return "informative_detailed"
        else:
            return "balanced_neutral"
    
    def _get_default_station_profiles(self) -> Dict[str, Dict[str, float]]:
        """Get default station profiles if flow_state module not available."""
        return {
            "classic_rock": {"arousal": 0.70, "valence": 0.65, "energy": 0.72},
            "top_40": {"arousal": 0.65, "valence": 0.75, "energy": 0.68},
            "adult_contemporary": {"arousal": 0.45, "valence": 0.70, "energy": 0.42},
            "hip_hop": {"arousal": 0.78, "valence": 0.60, "energy": 0.82},
            "country": {"arousal": 0.55, "valence": 0.65, "energy": 0.52},
            "edm": {"arousal": 0.90, "valence": 0.75, "energy": 0.92},
            "chill": {"arousal": 0.25, "valence": 0.65, "energy": 0.22},
            "news_talk": {"arousal": 0.50, "valence": 0.45, "energy": 0.35},
            "jazz": {"arousal": 0.40, "valence": 0.60, "energy": 0.38},
            "classical": {"arousal": 0.35, "valence": 0.60, "energy": 0.30},
        }
    
    def _determine_optimal_formats(self, profile: FlowStateProfile) -> List[str]:
        """Determine optimal station formats based on flow state profile."""
        matches = []
        
        for format_name, format_profile in self._station_profiles.items():
            if format_name == "unknown":
                continue
            
            # Calculate match score
            arousal_diff = abs(format_profile.get("arousal", 0.5) - profile.arousal)
            valence_diff = abs(format_profile.get("valence", 0.5) - profile.valence)
            energy_diff = abs(format_profile.get("energy", 0.5) - profile.energy)
            
            # Weighted distance
            distance = (arousal_diff * 0.4 + valence_diff * 0.3 + energy_diff * 0.3)
            match_score = 1 - distance
            
            matches.append((format_name, match_score))
        
        # Sort by match score
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 5 formats
        return [f[0] for f in matches[:5]]
    
    def _determine_recommended_tone(self, profile: FlowStateProfile) -> str:
        """Determine recommended ad tone based on flow state."""
        if profile.arousal > 0.7 and profile.valence > 0.6:
            return "energetic_positive"
        elif profile.arousal > 0.7 and profile.valence < 0.4:
            return "urgent_action"
        elif profile.arousal < 0.4 and profile.valence > 0.6:
            return "calm_reassuring"
        elif profile.arousal < 0.4 and profile.valence < 0.4:
            return "empathetic_supportive"
        elif profile.nostalgia > 0.6:
            return "nostalgic_familiar"
        elif profile.cognitive_load > 0.6:
            return "informative_detailed"
        else:
            return "balanced_neutral"
    
    async def _synthesize_unified_profile(
        self,
        profile: UnifiedPsychologicalProfile,
    ) -> UnifiedPsychologicalProfile:
        """
        Synthesize insights from all modules into unified recommendations.
        
        This is where the magic happens - combining insights from:
        - Psycholinguistic constructs (32 dimensions)
        - Psychological needs (33 needs)
        - Flow state (arousal/valence/energy)
        
        Into actionable advertising recommendations.
        """
        recommendations = []
        unified_constructs = {}
        
        # =====================================================================
        # SYNTHESIZE UNIFIED CONSTRUCTS
        # =====================================================================
        
        # From psycholinguistic analysis
        for construct_id, score in profile.psycholinguistic.all_constructs.items():
            unified_constructs[construct_id] = score
        
        # Add flow state dimensions
        unified_constructs["flow_arousal"] = profile.flow_state.arousal
        unified_constructs["flow_valence"] = profile.flow_state.valence
        unified_constructs["flow_energy"] = profile.flow_state.energy
        unified_constructs["flow_cognitive_load"] = profile.flow_state.cognitive_load
        unified_constructs["ad_receptivity"] = profile.flow_state.ad_receptivity_score
        
        # Add regulatory focus from needs
        unified_constructs["promotion_focus"] = profile.psychological_needs.promotion_focus
        unified_constructs["prevention_focus"] = profile.psychological_needs.prevention_focus
        
        profile.unified_constructs = unified_constructs
        
        # =====================================================================
        # GENERATE UNIFIED RECOMMENDATIONS
        # =====================================================================
        
        # High-priority effect size constructs
        EFFECT_SIZE_MAP = {
            "construal_level": 0.50,
            "need_for_cognition": 0.45,
            "attitude_certainty": 0.38,
            "risk_tolerance": 0.35,
            "regulatory_focus_promotion": 0.33,
            "regulatory_focus_prevention": 0.33,
            "emotional_arousal": 0.30,
            "fear": 0.29,
            "maximizer_tendency": 0.25,
        }
        
        # Generate recommendations from psycholinguistic constructs
        for construct_id, score in profile.psycholinguistic.all_constructs.items():
            deviation = abs(score - 0.5)
            if deviation > 0.1:  # Significant deviation from neutral
                effect_size = EFFECT_SIZE_MAP.get(construct_id, 0.2)
                confidence = profile.psycholinguistic.confidence_scores.get(construct_id, 0.5)
                priority = deviation * effect_size * confidence
                
                recommendation = self._get_construct_recommendation(construct_id, score)
                
                if recommendation:
                    recommendations.append(UnifiedAdRecommendation(
                        recommendation_id=f"psych_{construct_id}",
                        priority_score=priority,
                        construct_name=construct_id.replace("_", " ").title(),
                        recommendation=recommendation,
                        supporting_evidence=[f"Score: {score:.2f}"],
                        source_modules=[InsightSource.PSYCHOLINGUISTIC],
                        effect_size=effect_size,
                        confidence=confidence,
                    ))
        
        # Generate recommendations from psychological needs
        for need_id, score in profile.psychological_needs.primary_needs[:5]:
            if score > 0.3:
                recommendation = self._get_need_recommendation(need_id, score)
                if recommendation:
                    recommendations.append(UnifiedAdRecommendation(
                        recommendation_id=f"need_{need_id}",
                        priority_score=score * 0.8,
                        construct_name=need_id.replace("_", " ").title(),
                        recommendation=recommendation,
                        supporting_evidence=[f"Activation: {score:.2f}"],
                        source_modules=[InsightSource.NEED_DETECTION],
                        confidence=score,
                    ))
        
        # Add flow state recommendation
        recommendations.append(UnifiedAdRecommendation(
            recommendation_id="flow_optimal",
            priority_score=profile.flow_state.ad_receptivity_score,
            construct_name="Flow State Optimization",
            recommendation=f"Target {profile.flow_state.recommended_tone} tone. "
                          f"Optimal formats: {', '.join(profile.flow_state.optimal_formats[:3])}",
            supporting_evidence=[
                f"Arousal: {profile.flow_state.arousal:.2f}",
                f"Valence: {profile.flow_state.valence:.2f}",
                f"Ad Receptivity: {profile.flow_state.ad_receptivity_score:.2f}",
            ],
            source_modules=[InsightSource.FLOW_STATE],
            confidence=profile.flow_state.flow_stability,
        ))
        
        # Sort by priority
        recommendations.sort(key=lambda x: x.priority_score, reverse=True)
        profile.unified_ad_recommendations = recommendations
        
        # =====================================================================
        # DETERMINE PRIMARY ARCHETYPE
        # =====================================================================
        profile.primary_archetype, profile.archetype_confidence = self._determine_archetype(profile)
        
        # =====================================================================
        # GENERATE MECHANISM PREDICTIONS
        # =====================================================================
        profile.mechanism_predictions = self._predict_mechanisms(profile)
        
        return profile
    
    def _get_construct_recommendation(self, construct_id: str, score: float) -> Optional[str]:
        """Get ad recommendation for a psycholinguistic construct."""
        CONSTRUCT_RECS = {
            "construal_level": {
                "high": "Use abstract, values-based messaging emphasizing 'why'",
                "low": "Use concrete, feature-focused messaging with specific 'how-to'",
            },
            "need_for_cognition": {
                "high": "Provide detailed analytical content with strong arguments",
                "low": "Use visual-focused, simple messaging with peripheral cues",
            },
            "regulatory_focus_promotion": {
                "high": "Frame gains and achievements, use aspirational messaging",
                "low": None,
            },
            "regulatory_focus_prevention": {
                "high": "Frame loss avoidance and security, emphasize reliability",
                "low": None,
            },
            "hedonic_motivation": {
                "high": "Use experiential appeals with sensory and emotional language",
                "low": "Focus on functional benefits and practical value",
            },
            "emotional_arousal": {
                "high": "Use urgent CTAs and high-energy messaging",
                "low": "Use soothing, trust-building messaging",
            },
            "risk_tolerance": {
                "high": "Emphasize innovation and first-mover benefits",
                "low": "Emphasize proven reliability and guarantees",
            },
            "deal_proneness": {
                "high": "Lead with promotional messaging and discounts",
                "low": "Emphasize premium positioning and long-term value",
            },
            "impulsivity": {
                "high": "Use scarcity messaging and urgent CTAs",
                "low": "Provide detailed information for deliberate decision-making",
            },
        }
        
        if construct_id in CONSTRUCT_RECS:
            recs = CONSTRUCT_RECS[construct_id]
            if score > 0.6 and recs.get("high"):
                return recs["high"]
            elif score < 0.4 and recs.get("low"):
                return recs["low"]
        
        return None
    
    def _get_need_recommendation(self, need_id: str, score: float) -> Optional[str]:
        """Get ad recommendation for a psychological need."""
        NEED_RECS = {
            "identity_self_expression": "Enable authentic self-expression through product use",
            "relationship_brand_love": "Cultivate emotional connection with passionate brand voice",
            "relationship_trust": "Emphasize reliability, transparency, and track record",
            "motivation_promotion": "Frame gains and achievements, aspiration-focused",
            "motivation_prevention": "Frame risk reduction and protection",
            "emotion_arousal": "Use high-intensity emotional appeals",
            "emotion_comfort": "Provide soothing, reassuring messaging",
            "social_belonging": "Emphasize community and shared experiences",
            "social_status": "Signal premium quality and exclusivity",
            "autonomy_control": "Empower personal choice and customization",
            "security_safety": "Emphasize protection and peace of mind",
            "meaning_purpose": "Connect product to larger life purpose",
        }
        
        return NEED_RECS.get(need_id)
    
    def _determine_archetype(
        self,
        profile: UnifiedPsychologicalProfile,
    ) -> Tuple[str, float]:
        """Determine primary buyer archetype from unified profile."""
        archetype_scores = {
            "Achiever": 0.0,
            "Guardian": 0.0,
            "Explorer": 0.0,
            "Connector": 0.0,
            "Analyzer": 0.0,
            "Pragmatist": 0.0,
        }
        
        psych = profile.psycholinguistic
        
        # Achiever: High promotion focus, achievement motivation
        archetype_scores["Achiever"] = (
            psych.regulatory_focus_promotion * 0.4 +
            psych.risk_tolerance * 0.3 +
            psych.attitude_certainty * 0.3
        )
        
        # Guardian: High prevention focus, low risk tolerance
        archetype_scores["Guardian"] = (
            psych.regulatory_focus_prevention * 0.4 +
            (1 - psych.risk_tolerance) * 0.3 +
            psych.attitude_certainty * 0.3
        )
        
        # Explorer: High risk tolerance, novelty seeking
        archetype_scores["Explorer"] = (
            psych.risk_tolerance * 0.4 +
            (1 - psych.attitude_certainty) * 0.3 +
            psych.hedonic_motivation * 0.3
        )
        
        # Connector: High interdependent self-construal, social
        archetype_scores["Connector"] = (
            psych.self_construal_interdependent * 0.4 +
            psych.emotional_valence * 0.3 +
            psych.gratitude * 0.3
        )
        
        # Analyzer: High need for cognition, deliberate
        archetype_scores["Analyzer"] = (
            psych.need_for_cognition * 0.4 +
            (1 - psych.impulsivity) * 0.3 +
            psych.expertise_level * 0.3
        )
        
        # Pragmatist: Utilitarian, deal-prone
        archetype_scores["Pragmatist"] = (
            psych.utilitarian_motivation * 0.4 +
            psych.deal_proneness * 0.3 +
            (1 - psych.hedonic_motivation) * 0.3
        )
        
        # Find top archetype
        top_archetype = max(archetype_scores, key=archetype_scores.get)
        confidence = archetype_scores[top_archetype]
        
        return top_archetype, confidence
    
    def _predict_mechanisms(
        self,
        profile: UnifiedPsychologicalProfile,
    ) -> Dict[str, float]:
        """
        Predict mechanism effectiveness - ENHANCED with cascading insights.
        
        This is the KEY prediction function. Each mechanism's effectiveness
        is predicted using weighted signals from ALL THREE phases:
        
        1. PSYCHOLINGUISTIC (Phase 1): Personality-based susceptibility
           - Need for cognition → Authority
           - Impulsivity → Scarcity
           - Interdependent self → Social Proof
           
        2. NEEDS (Phase 2): Unmet need alignment
           - Unmet security needs → Scarcity more effective
           - Unmet relationship needs → Social Proof more effective
           - Unmet status needs → Authority more effective
           
        3. FLOW STATE (Phase 3): Timing/context modulation
           - High receptivity → ALL mechanisms more effective
           - Low cognitive load → Simple mechanisms (Scarcity, Liking)
           - High cognitive load → Complex mechanisms (Authority)
        
        Research-Backed Weights:
        - Cialdini's Principles: Authority, Social Proof, Scarcity, Reciprocity, Liking, Commitment
        - Regulatory Fit effects: ~0.27-0.33 correlation with attitudes
        - Flow state timing: Pre-roll 3x less disruptive than mid-roll
        """
        mechanisms = {
            "authority": 0.5,
            "social_proof": 0.5,
            "scarcity": 0.5,
            "reciprocity": 0.5,
            "commitment": 0.5,
            "liking": 0.5,
            "novelty": 0.5,
        }
        
        psych = profile.psycholinguistic
        needs = profile.psychological_needs
        flow = profile.flow_state
        
        # Receptivity multiplier from flow state (0.8 to 1.2)
        receptivity_mult = 0.8 + (flow.ad_receptivity_score * 0.4)
        
        # =====================================================================
        # AUTHORITY: Works best when cognition is valued and expertise matters
        # =====================================================================
        # Phase 1: High need for cognition, values expertise
        psych_authority = (
            psych.need_for_cognition * 0.4 +
            psych.expertise_level * 0.3 +
            psych.attitude_certainty * 0.2 +
            (1 - psych.impulsivity) * 0.1  # Deliberate thinkers
        )
        # Phase 2: Trust and cognition needs amplify
        needs_authority = (
            needs.cognition_needs.get("cognition_expertise", 0) * 0.5 +
            needs.relationship_needs.get("relationship_trust", 0) * 0.5
        ) if needs.cognition_needs or needs.relationship_needs else 0
        # Phase 3: High cognitive load means they WANT detailed info
        flow_authority = flow.cognitive_load * 0.3
        
        mechanisms["authority"] = (
            psych_authority * 0.5 +
            needs_authority * 0.3 +
            flow_authority * 0.2
        ) * receptivity_mult
        
        # =====================================================================
        # SOCIAL PROOF: Works best for interdependent, belonging-seeking
        # =====================================================================
        # Phase 1: Interdependent self-construal
        psych_social = (
            psych.self_construal_interdependent * 0.5 +
            (1 - psych.self_construal_independent) * 0.3 +
            psych.emotional_valence * 0.2  # Positive mood = more receptive to social
        )
        # Phase 2: Social and belonging needs
        needs_social = (
            needs.social_needs.get("social_belonging", 0) * 0.4 +
            needs.social_needs.get("social_conformity", 0) * 0.3 +
            needs.relationship_needs.get("relationship_community", 0) * 0.3
        ) if needs.social_needs else 0
        # Phase 3: High social energy
        flow_social = flow.social_energy * 0.3
        
        mechanisms["social_proof"] = (
            psych_social * 0.4 +
            needs_social * 0.4 +
            flow_social * 0.2
        ) * receptivity_mult
        
        # =====================================================================
        # SCARCITY: Works best for impulsive, prevention-focused, security-needing
        # =====================================================================
        # Phase 1: Impulsivity and prevention focus
        psych_scarcity = (
            psych.impulsivity * 0.4 +
            psych.regulatory_focus_prevention * 0.3 +
            psych.emotional_arousal * 0.2 +
            (1 - psych.attitude_certainty) * 0.1  # Uncertainty makes scarcity powerful
        )
        # Phase 2: Security needs and unmet needs amplify scarcity
        needs_scarcity = (
            sum(needs.security_needs.values()) / max(len(needs.security_needs), 1) * 0.5 +
            (len(needs.unmet_needs) / 10) * 0.5  # More unmet needs = more scarcity-susceptible
        ) if needs.security_needs or needs.unmet_needs else 0
        # Phase 3: High arousal state = scarcity more effective
        flow_scarcity = flow.arousal * 0.3
        
        mechanisms["scarcity"] = (
            psych_scarcity * 0.4 +
            needs_scarcity * 0.35 +
            flow_scarcity * 0.25
        ) * receptivity_mult
        
        # =====================================================================
        # RECIPROCITY: Works best for grateful, relationship-oriented
        # =====================================================================
        # Phase 1: Gratitude and authenticity
        psych_reciprocity = (
            psych.gratitude * 0.4 +
            psych.authenticity * 0.3 +
            psych.self_construal_interdependent * 0.3
        )
        # Phase 2: Relationship needs
        needs_reciprocity = (
            needs.relationship_needs.get("relationship_trust", 0) * 0.4 +
            needs.relationship_needs.get("relationship_brand_love", 0) * 0.3 +
            needs.social_needs.get("social_reciprocity", 0) * 0.3
        ) if needs.relationship_needs else 0
        # Phase 3: Positive valence
        flow_reciprocity = flow.valence * 0.3
        
        mechanisms["reciprocity"] = (
            psych_reciprocity * 0.4 +
            needs_reciprocity * 0.35 +
            flow_reciprocity * 0.25
        ) * receptivity_mult
        
        # =====================================================================
        # COMMITMENT: Works best for certain, consistent, deliberate
        # =====================================================================
        # Phase 1: High certainty, low impulsivity, utilitarian
        psych_commitment = (
            psych.attitude_certainty * 0.4 +
            (1 - psych.impulsivity) * 0.3 +
            psych.utilitarian_motivation * 0.2 +
            psych.regulatory_focus_prevention * 0.1  # Commitment = risk reduction
        )
        # Phase 2: Identity and consistency needs
        needs_commitment = (
            sum(needs.identity_needs.values()) / max(len(needs.identity_needs), 1) * 0.5 +
            sum(needs.autonomy_needs.values()) / max(len(needs.autonomy_needs), 1) * 0.5
        ) if needs.identity_needs or needs.autonomy_needs else 0
        # Phase 3: High stability = commitment-ready
        flow_commitment = flow.flow_stability * 0.4
        
        mechanisms["commitment"] = (
            psych_commitment * 0.4 +
            needs_commitment * 0.3 +
            flow_commitment * 0.3
        ) * receptivity_mult
        
        # =====================================================================
        # LIKING: Works best for hedonic, positive, nostalgic
        # =====================================================================
        # Phase 1: Positive valence, hedonic, nostalgic
        psych_liking = (
            psych.emotional_valence * 0.4 +
            psych.hedonic_motivation * 0.3 +
            psych.nostalgia * 0.3
        )
        # Phase 2: Relationship and emotion needs
        needs_liking = (
            needs.relationship_needs.get("relationship_brand_love", 0) * 0.4 +
            needs.emotion_needs.get("emotion_comfort", 0) * 0.3 +
            needs.sensory_needs.get("sensory_aesthetic", 0) * 0.3
        ) if needs.relationship_needs or needs.emotion_needs else 0
        # Phase 3: Positive mood amplifies liking
        flow_liking = (flow.valence * 0.5 + flow.social_energy * 0.5)
        
        mechanisms["liking"] = (
            psych_liking * 0.4 +
            needs_liking * 0.3 +
            flow_liking * 0.3
        ) * receptivity_mult
        
        # =====================================================================
        # NOVELTY: Works best for risk-tolerant, explorers
        # =====================================================================
        # Phase 1: Risk tolerance, low nostalgia, hedonic
        psych_novelty = (
            psych.risk_tolerance * 0.4 +
            (1 - psych.nostalgia) * 0.3 +
            psych.hedonic_motivation * 0.2 +
            (1 - psych.regulatory_focus_prevention) * 0.1  # Promotion = novelty-seeking
        )
        # Phase 2: Meaning and autonomy needs (seeking new experiences)
        needs_novelty = (
            sum(needs.meaning_needs.values()) / max(len(needs.meaning_needs), 1) * 0.5 +
            needs.autonomy_needs.get("autonomy_exploration", 0) * 0.5
        ) if needs.meaning_needs or needs.autonomy_needs else 0
        # Phase 3: High energy = novelty receptive
        flow_novelty = flow.energy * 0.3
        
        mechanisms["novelty"] = (
            psych_novelty * 0.4 +
            needs_novelty * 0.3 +
            flow_novelty * 0.3
        ) * receptivity_mult
        
        # Normalize all mechanisms to 0-1 range
        max_score = max(mechanisms.values())
        if max_score > 1.0:
            for k in mechanisms:
                mechanisms[k] = mechanisms[k] / max_score
        
        return mechanisms
    
    async def emit_learning_signal(
        self,
        profile: UnifiedPsychologicalProfile,
        signal_type: str = "unified_analysis",
    ) -> None:
        """
        Emit learning signal to all connected infrastructure services.
        
        This integrates with:
        1. SQLite Storage - Persistent profile storage
        2. Neo4j Graph - Graph database storage
        3. Blackboard - Cross-component state sharing
        4. Gradient Bridge - Learning signal propagation
        5. Kafka - Event publishing
        6. Prometheus - Metrics recording
        """
        # Record metrics
        if self._metrics:
            try:
                self._metrics.counter(
                    "unified_intelligence_profiles_created",
                    1,
                    {"brand": profile.brand_name, "archetype": profile.primary_archetype}
                )
            except Exception:
                pass
        
        # 1. Store to SQLite persistent storage
        try:
            from adam.intelligence.storage.insight_storage import get_insight_storage
            
            storage = get_insight_storage()
            await storage.initialize()
            await storage.store_profile(profile)
            await storage.store_learning_signal(
                profile_id=profile.profile_id,
                signal_type=signal_type,
                source_module="unified_intelligence",
                payload={
                    "profile_id": profile.profile_id,
                    "brand": profile.brand_name,
                    "product": profile.product_name,
                    "unified_constructs": profile.unified_constructs,
                    "mechanism_predictions": profile.mechanism_predictions,
                    "primary_archetype": profile.primary_archetype,
                    "archetype_confidence": profile.archetype_confidence,
                    "reviews_analyzed": profile.reviews_analyzed,
                    "modules_used": profile.modules_used,
                },
                confidence=profile.archetype_confidence,
            )
            logger.info(f"SQLite: Stored profile {profile.profile_id}")
        except Exception as e:
            logger.debug(f"SQLite storage not available: {e}")
        
        # 2. Store to Neo4j Graph Database
        if self._neo4j_connected and self._graph_service:
            try:
                await self._graph_service.store_profile(profile)
                logger.info(f"Neo4j: Stored profile {profile.profile_id}")
            except Exception as e:
                logger.warning(f"Neo4j storage failed: {e}")
        
        # 3. Write to Blackboard (Zone 6 - Intelligence Repository)
        if self._blackboard_connected and self._blackboard:
            try:
                await self._write_to_blackboard(profile)
                logger.info(f"Blackboard: Wrote profile {profile.profile_id} to Zone 6")
            except Exception as e:
                logger.warning(f"Blackboard write failed: {e}")
        
        # 4. Emit to Gradient Bridge
        if self._gradient_bridge_connected and self._gradient_bridge:
            try:
                await self._emit_to_gradient_bridge(profile, signal_type)
                logger.info(f"GradientBridge: Emitted signal for {profile.profile_id}")
            except Exception as e:
                logger.warning(f"Gradient Bridge emit failed: {e}")
        
        # 5. Publish Kafka Event
        if self._kafka_connected and self._kafka_producer:
            try:
                await self._publish_kafka_event(profile, signal_type)
                logger.info(f"Kafka: Published event for {profile.profile_id}")
            except Exception as e:
                logger.warning(f"Kafka publish failed: {e}")
        
        # 6. Fallback: Emit to UniversalLearningInterface (backward compatibility)
        try:
            from adam.core.learning.universal_learning_interface import (
                UniversalLearningInterface,
            )
            
            learner = UniversalLearningInterface()
            await learner.emit_signal(
                signal_type=signal_type,
                payload={
                    "profile_id": profile.profile_id,
                    "brand": profile.brand_name,
                    "product": profile.product_name,
                    "unified_constructs": profile.unified_constructs,
                    "mechanism_predictions": profile.mechanism_predictions,
                    "primary_archetype": profile.primary_archetype,
                    "archetype_confidence": profile.archetype_confidence,
                    "reviews_analyzed": profile.reviews_analyzed,
                    "modules_used": profile.modules_used,
                },
                confidence=profile.archetype_confidence,
            )
        except ImportError:
            pass  # Not critical
        except Exception as e:
            logger.debug(f"UniversalLearningInterface emit failed: {e}")
    
    async def _write_to_blackboard(
        self,
        profile: UnifiedPsychologicalProfile,
    ) -> None:
        """
        Write unified profile to Blackboard Zone 6 (Intelligence Repository).
        
        This makes the profile available to all other ADAM components.
        """
        if not self._blackboard:
            return
        
        # Create a blackboard for this analysis if needed
        request_id = f"unified_{profile.profile_id}"
        
        # Write to Zone 6 (or Zone 2 if available)
        zone_data = {
            "profile_id": profile.profile_id,
            "brand_name": profile.brand_name,
            "product_name": profile.product_name,
            "primary_archetype": profile.primary_archetype,
            "archetype_confidence": profile.archetype_confidence,
            "unified_constructs": profile.unified_constructs,
            "mechanism_predictions": profile.mechanism_predictions,
            "flow_state": {
                "arousal": profile.flow_state.arousal,
                "valence": profile.flow_state.valence,
                "ad_receptivity": profile.flow_state.ad_receptivity_score,
            },
            "psychological_needs": {
                "promotion_focus": profile.psychological_needs.promotion_focus,
                "prevention_focus": profile.psychological_needs.prevention_focus,
                "alignment_score": profile.psychological_needs.overall_alignment_score,
            },
            "created_at": profile.created_at.isoformat(),
            "modules_used": profile.modules_used,
        }
        
        # Use cache-based storage for Zone 6
        from adam.infrastructure.redis import CacheKeyBuilder
        key = CacheKeyBuilder.intelligence_profile(profile.brand_name, profile.product_name)
        
        await self._blackboard.cache.set(
            key,
            zone_data,
            ttl=86400,  # 24 hours
        )
    
    async def _emit_to_gradient_bridge(
        self,
        profile: UnifiedPsychologicalProfile,
        signal_type: str,
    ) -> None:
        """
        Emit learning signal to the Gradient Bridge.
        
        This enables cross-component learning from the analysis.
        """
        if not GRADIENT_BRIDGE_AVAILABLE or not self._gradient_bridge:
            return
        
        # Create learning signal
        signal = LearningSignal(
            signal_id=f"unified_{profile.profile_id}",
            signal_type=SignalType.ANALYSIS_COMPLETE,
            priority=SignalPriority.NORMAL,
            source_component="unified_psychological_intelligence",
            timestamp=datetime.now(timezone.utc),
            payload={
                "profile_id": profile.profile_id,
                "brand_name": profile.brand_name,
                "product_name": profile.product_name,
                "primary_archetype": profile.primary_archetype,
                "archetype_confidence": profile.archetype_confidence,
                "mechanism_predictions": profile.mechanism_predictions,
                "reviews_analyzed": profile.reviews_analyzed,
            },
            confidence=profile.archetype_confidence,
        )
        
        await self._gradient_bridge.process_signal(signal)
    
    async def _publish_kafka_event(
        self,
        profile: UnifiedPsychologicalProfile,
        signal_type: str,
    ) -> None:
        """
        Publish analysis event to Kafka.
        
        This enables event-driven processing by other services.
        """
        if not KAFKA_AVAILABLE or not self._kafka_producer:
            return
        
        event = {
            "event_type": "psychological_analysis_complete",
            "signal_type": signal_type,
            "profile_id": profile.profile_id,
            "brand_name": profile.brand_name,
            "product_name": profile.product_name,
            "primary_archetype": profile.primary_archetype,
            "archetype_confidence": profile.archetype_confidence,
            "mechanism_predictions": profile.mechanism_predictions,
            "reviews_analyzed": profile.reviews_analyzed,
            "modules_used": profile.modules_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        await self._kafka_producer.send(
            ADAMTopics.PSYCHOLOGICAL_ANALYSIS,
            event,
        )
    
    def get_infrastructure_status(self) -> Dict[str, bool]:
        """
        Get the connection status of all infrastructure services.
        
        Returns dict with service names and their connection status.
        """
        return {
            "neo4j": self._neo4j_connected,
            "blackboard": self._blackboard_connected,
            "gradient_bridge": self._gradient_bridge_connected,
            "kafka": self._kafka_connected,
            "prometheus": PROMETHEUS_AVAILABLE,
            "modules_loaded": self._loaded_modules,
        }


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_unified_intelligence: Optional[UnifiedPsychologicalIntelligence] = None


def get_unified_intelligence() -> UnifiedPsychologicalIntelligence:
    """Get the singleton UnifiedPsychologicalIntelligence instance."""
    global _unified_intelligence
    if _unified_intelligence is None:
        _unified_intelligence = UnifiedPsychologicalIntelligence()
    return _unified_intelligence


def reset_unified_intelligence() -> None:
    """Reset the singleton (for testing)."""
    global _unified_intelligence
    _unified_intelligence = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def analyze_reviews_unified(
    reviews: List[str],
    brand_content: Optional[Dict[str, List[str]]] = None,
    brand_name: str = "Brand",
    product_name: str = "Product",
) -> UnifiedPsychologicalProfile:
    """
    Convenience function to analyze reviews with all 3 modules.
    
    Usage:
        profile = await analyze_reviews_unified(
            reviews=["Great product!", "Love it!"],
            brand_name="Apple",
            product_name="iPhone"
        )
    """
    intelligence = get_unified_intelligence()
    await intelligence.initialize()
    return await intelligence.analyze_reviews(
        reviews=reviews,
        brand_content=brand_content,
        brand_name=brand_name,
        product_name=product_name,
    )
