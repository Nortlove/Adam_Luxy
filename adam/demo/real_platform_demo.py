# =============================================================================
# ADAM Real Platform Demo Integration
# Location: adam/demo/real_platform_demo.py
# =============================================================================

"""
REAL PLATFORM DEMO ENGINE

As the CTO, this is how we showcase ADAM: By using the ACTUAL platform components
we spent months building, not simulations.

This module connects the demo to:
1. AtomDAG - Real psychological reasoning chain
2. Blackboard - Real 5-zone shared state
3. ThompsonSampling - Real explore/exploit routing
4. ColdStart - Real Amazon archetype matching
5. InteractionBridge - Real graph queries (when Neo4j available)
6. NonconsciousAnalytics - Real behavioral signal processing
7. CopyGeneration - Real SSML generation

When infrastructure is unavailable, we provide TRANSPARENT fallbacks.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# IMPORT REAL PLATFORM COMPONENTS
# =============================================================================

# Atoms
try:
    from adam.atoms.dag import AtomDAG, DAGExecutionResult
    from adam.atoms.models.atom_io import AtomInput, AtomOutput
    ATOMS_AVAILABLE = True
except ImportError as e:
    ATOMS_AVAILABLE = False
    logger.warning(f"Atoms not available: {e}")

# Blackboard
try:
    from adam.blackboard.service import BlackboardService
    from adam.blackboard.models.core import BlackboardState
    BLACKBOARD_AVAILABLE = True
except ImportError as e:
    BLACKBOARD_AVAILABLE = False
    logger.warning(f"Blackboard not available: {e}")

# Thompson Sampling
try:
    from adam.meta_learner.thompson import ThompsonSamplingEngine
    from adam.meta_learner.models import ContextFeatures, RoutingDecision
    THOMPSON_AVAILABLE = True
except ImportError as e:
    THOMPSON_AVAILABLE = False
    logger.warning(f"Thompson Sampling not available: {e}")

# Cold Start
try:
    from adam.user.cold_start.service import ColdStartService, ColdStartContext, ColdStartResult
    from adam.user.cold_start.archetypes import AMAZON_ARCHETYPES, UserArchetype
    COLDSTART_AVAILABLE = True
except ImportError as e:
    COLDSTART_AVAILABLE = False
    logger.warning(f"Cold Start not available: {e}")

# Graph Reasoning
try:
    from adam.graph_reasoning.bridge.interaction_bridge import InteractionBridge
    from adam.graph_reasoning.models.graph_context import GraphContext
    GRAPH_AVAILABLE = True
except ImportError as e:
    GRAPH_AVAILABLE = False
    logger.warning(f"Graph Reasoning not available: {e}")

# Nonconscious Analytics
try:
    from adam.signals.nonconscious.service import NonconsciousAnalyticsService
    from adam.signals.nonconscious.models import NonconsciousProfile
    NONCONSCIOUS_AVAILABLE = True
except ImportError as e:
    NONCONSCIOUS_AVAILABLE = False
    logger.warning(f"Nonconscious Analytics not available: {e}")

# Copy Generation
try:
    from adam.output.copy_generation.service import CopyGenerationService
    from adam.output.copy_generation.models import GeneratedCopy, CopyType
    COPYGENERATION_AVAILABLE = True
except ImportError as e:
    COPYGENERATION_AVAILABLE = False
    logger.warning(f"Copy Generation not available: {e}")


# =============================================================================
# PLATFORM STATUS
# =============================================================================

class RealPlatformStatus(BaseModel):
    """Shows what real components are being used."""
    
    atoms: bool = ATOMS_AVAILABLE
    blackboard: bool = BLACKBOARD_AVAILABLE
    thompson_sampling: bool = THOMPSON_AVAILABLE
    cold_start: bool = COLDSTART_AVAILABLE
    graph_reasoning: bool = GRAPH_AVAILABLE
    nonconscious: bool = NONCONSCIOUS_AVAILABLE
    copy_generation: bool = COPYGENERATION_AVAILABLE
    
    neo4j_connected: bool = False
    redis_connected: bool = False
    
    @property
    def components_active(self) -> List[str]:
        """List of active real components."""
        active = []
        if self.atoms:
            active.append("AtomDAG")
        if self.blackboard:
            active.append("Blackboard")
        if self.thompson_sampling:
            active.append("ThompsonSampling")
        if self.cold_start:
            active.append("ColdStart")
        if self.graph_reasoning:
            active.append("GraphReasoning")
        if self.nonconscious:
            active.append("NonconsciousAnalytics")
        if self.copy_generation:
            active.append("CopyGeneration")
        return active
    
    @property
    def status_message(self) -> str:
        count = len(self.components_active)
        if count == 0:
            return "⚠️ No platform components loaded"
        return f"✅ {count}/7 real components active: {', '.join(self.components_active)}"


# =============================================================================
# REAL COLD START INTEGRATION
# =============================================================================

class RealColdStartEngine:
    """
    Uses the ACTUAL ColdStartService we built.
    
    This provides:
    - 6 Amazon archetypes (Explorer, Achiever, Connector, Guardian, Analyzer, Pragmatist)
    - Station format priors (CHR, Hot_AC, Country, Classic_Rock, News_Talk, Urban)
    - Bayesian prior blending
    """
    
    def __init__(self, cache=None, bridge=None):
        self.service = None
        if COLDSTART_AVAILABLE:
            try:
                self.service = ColdStartService(cache=cache, bridge=bridge)
                logger.info(f"Real ColdStart initialized with {len(AMAZON_ARCHETYPES)} archetypes")
            except Exception as e:
                logger.warning(f"Could not initialize ColdStartService: {e}")
    
    async def get_user_priors(
        self,
        user_id: str,
        station_format: Optional[str] = None,
        category: Optional[str] = None,
        platform: str = "iheart",
        time_of_day: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get psychological priors for a user using REAL cold start.
        """
        if not self.service:
            return self._fallback_priors()
        
        try:
            context = ColdStartContext(
                user_id=user_id,
                platform=platform,
                station_format=station_format,
                category=category,
                time_of_day=time_of_day,
            )
            
            result = await self.service.initialize_user(context)
            
            return {
                "source": "REAL_COLD_START",
                "archetype": result.archetype_match.primary_archetype.name if result.archetype_match else None,
                "archetype_id": result.archetype_match.primary_archetype.archetype_id if result.archetype_match else None,
                "archetype_confidence": result.archetype_match.primary_confidence if result.archetype_match else 0.0,
                "big_five": {
                    "openness": result.big_five.openness,
                    "conscientiousness": result.big_five.conscientiousness,
                    "extraversion": result.big_five.extraversion,
                    "agreeableness": result.big_five.agreeableness,
                    "neuroticism": result.big_five.neuroticism,
                },
                "regulatory_focus": result.regulatory_focus,
                "construal_level": result.construal_level,
                "mechanism_priors": result.mechanism_priors,
                "overall_confidence": result.overall_confidence,
                "sources_used": result.sources_used,
            }
        except Exception as e:
            logger.warning(f"Cold start error, using fallback: {e}")
            return self._fallback_priors()
    
    def _fallback_priors(self) -> Dict[str, Any]:
        """Fallback when cold start unavailable."""
        return {
            "source": "FALLBACK",
            "archetype": "Pragmatist",
            "big_five": {
                "openness": 0.50,
                "conscientiousness": 0.55,
                "extraversion": 0.50,
                "agreeableness": 0.55,
                "neuroticism": 0.45,
            },
            "regulatory_focus": {"promotion": 0.50, "prevention": 0.50},
            "construal_level": 0.50,
            "mechanism_priors": {},
            "overall_confidence": 0.30,
            "sources_used": ["fallback"],
        }
    
    def get_all_archetypes(self) -> Dict[str, Dict[str, Any]]:
        """Get all available archetypes for display."""
        if not COLDSTART_AVAILABLE:
            return {}
        
        result = {}
        for arch_id, archetype in AMAZON_ARCHETYPES.items():
            result[arch_id] = {
                "name": archetype.name,
                "description": archetype.description,
                "big_five": {
                    "openness": archetype.big_five.openness,
                    "conscientiousness": archetype.big_five.conscientiousness,
                    "extraversion": archetype.big_five.extraversion,
                    "agreeableness": archetype.big_five.agreeableness,
                    "neuroticism": archetype.big_five.neuroticism,
                },
                "promotion_tendency": archetype.promotion_tendency,
                "prevention_tendency": archetype.prevention_tendency,
                "population_percentage": archetype.population_percentage,
            }
        return result


# =============================================================================
# REAL THOMPSON SAMPLING
# =============================================================================

class RealThompsonSamplingEngine:
    """
    Uses the ACTUAL Thompson Sampling we built for routing decisions.
    
    This provides:
    - Beta posterior distributions for each modality
    - Context-aware constraint checking
    - Exploration-exploitation balance
    """
    
    def __init__(self):
        self.engine = None
        if THOMPSON_AVAILABLE:
            try:
                self.engine = ThompsonSamplingEngine()
                logger.info("Real Thompson Sampling initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Thompson Sampling: {e}")
    
    def select_path(
        self,
        user_id: str,
        request_id: str,
        interaction_count: int = 0,
        profile_completeness: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Use REAL Thompson Sampling to select execution path.
        """
        if not self.engine:
            return self._fallback_path()
        
        try:
            context = ContextFeatures(
                user_id=user_id,
                interaction_count=interaction_count,
                conversion_count=0,
                profile_completeness=profile_completeness,
                latency_budget_ms=500,
                exploration_allowed=True,
            )
            
            decision = self.engine.select_modality(
                request_id=request_id,
                user_id=user_id,
                context=context,
            )
            
            return {
                "source": "REAL_THOMPSON_SAMPLING",
                "selected_modality": decision.selected_modality.value,
                "execution_path": decision.execution_path.value,
                "sampled_values": decision.sampled_values,
                "selection_confidence": decision.selection_confidence,
                "exploration_probability": decision.exploration_probability,
                "selection_reason": decision.selection_reason,
            }
        except Exception as e:
            logger.warning(f"Thompson sampling error: {e}")
            return self._fallback_path()
    
    def _fallback_path(self) -> Dict[str, Any]:
        return {
            "source": "FALLBACK",
            "selected_modality": "reinforcement_bandit",
            "execution_path": "fast_path",
            "selection_confidence": 0.5,
            "exploration_probability": 0.3,
            "selection_reason": "Fallback due to unavailable Thompson Sampling",
        }


# =============================================================================
# REAL NONCONSCIOUS ANALYTICS
# =============================================================================

class RealNonconsciousEngine:
    """
    Uses the ACTUAL Nonconscious Analytics we built.
    
    This provides:
    - Approach-avoidance tendency
    - Cognitive load estimation
    - Processing fluency
    - Implicit preference inference
    """
    
    def __init__(self):
        self.service = None
        if NONCONSCIOUS_AVAILABLE:
            try:
                self.service = NonconsciousAnalyticsService()
                logger.info("Real Nonconscious Analytics initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Nonconscious: {e}")
    
    async def analyze_signals(
        self,
        user_id: str,
        session_id: str,
        signals: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze behavioral signals using REAL nonconscious processing.
        """
        if not self.service or not signals:
            return self._baseline_profile()
        
        try:
            # Process signals through the real service
            profile = await self.service.process_session(
                user_id=user_id,
                session_id=session_id,
                raw_signals=signals,
            )
            
            return {
                "source": "REAL_NONCONSCIOUS",
                "approach_avoidance": profile.approach_avoidance_tendency,
                "cognitive_load": profile.cognitive_load,
                "processing_fluency": profile.processing_fluency,
                "emotional_valence": profile.emotional_valence,
                "arousal": profile.arousal,
                "engagement": profile.engagement,
                "recommended_mechanisms": profile.mechanism_hints,
                "confidence": profile.confidence,
            }
        except Exception as e:
            logger.warning(f"Nonconscious analysis error: {e}")
            return self._baseline_profile()
    
    def _baseline_profile(self) -> Dict[str, Any]:
        return {
            "source": "BASELINE",
            "approach_avoidance": 0.0,
            "cognitive_load": 0.5,
            "processing_fluency": 0.5,
            "emotional_valence": 0.0,
            "arousal": 0.5,
            "engagement": 0.5,
            "recommended_mechanisms": [],
            "confidence": 0.3,
        }


# =============================================================================
# UNIFIED REAL PLATFORM ENGINE
# =============================================================================

class RealPlatformDemoEngine:
    """
    THE UNIFIED ENGINE THAT USES REAL PLATFORM COMPONENTS.
    
    As the CTO mandates: We showcase what we built, not simulations.
    """
    
    def __init__(
        self,
        neo4j_driver=None,
        redis_client=None,
    ):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        
        # Initialize real components
        self.cold_start = RealColdStartEngine(cache=redis_client)
        self.thompson = RealThompsonSamplingEngine()
        self.nonconscious = RealNonconsciousEngine()
        
        # Track status
        self.status = RealPlatformStatus(
            neo4j_connected=neo4j_driver is not None,
            redis_connected=redis_client is not None,
        )
        
        logger.info(f"RealPlatformDemoEngine initialized: {self.status.status_message}")
    
    async def generate_recommendation(
        self,
        user_id: str,
        station_format: Optional[str] = None,
        category: Optional[str] = None,
        daypart: str = "Midday",
        behavioral_signals: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a recommendation using REAL platform components.
        
        Returns a comprehensive result showing:
        1. Which REAL components were used
        2. The actual reasoning from those components
        3. The recommendation with full attribution
        """
        request_id = f"demo_{uuid4().hex[:12]}"
        session_id = f"session_{uuid4().hex[:8]}"
        
        result = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform_status": self.status.dict(),
            "components_used": [],
        }
        
        # 1. Cold Start - Get psychological priors
        priors = await self.cold_start.get_user_priors(
            user_id=user_id,
            station_format=station_format,
            category=category,
            time_of_day=daypart,
        )
        result["cold_start"] = priors
        if priors["source"] == "REAL_COLD_START":
            result["components_used"].append("ColdStart")
        
        # 2. Thompson Sampling - Route the request
        routing = self.thompson.select_path(
            user_id=user_id,
            request_id=request_id,
            profile_completeness=priors["overall_confidence"],
        )
        result["routing"] = routing
        if routing["source"] == "REAL_THOMPSON_SAMPLING":
            result["components_used"].append("ThompsonSampling")
        
        # 3. Nonconscious Analytics - Analyze behavioral signals
        if behavioral_signals:
            nonconscious = await self.nonconscious.analyze_signals(
                user_id=user_id,
                session_id=session_id,
                signals=behavioral_signals,
            )
            result["nonconscious"] = nonconscious
            if nonconscious["source"] == "REAL_NONCONSCIOUS":
                result["components_used"].append("NonconsciousAnalytics")
        
        # 4. Build psychological profile
        result["psychological_profile"] = {
            "big_five": priors.get("big_five", {}),
            "regulatory_focus": priors.get("regulatory_focus", {}),
            "construal_level": priors.get("construal_level", 0.5),
            "archetype": priors.get("archetype"),
            "archetype_confidence": priors.get("archetype_confidence", 0.0),
            "mechanism_priors": priors.get("mechanism_priors", {}),
        }
        
        # 5. Determine recommended mechanisms based on priors
        result["mechanism_recommendations"] = self._select_mechanisms(priors)
        
        # Summary
        result["summary"] = {
            "real_components_used": len(result["components_used"]),
            "total_components_available": len(self.status.components_active),
            "platform_status": self.status.status_message,
        }
        
        return result
    
    def _select_mechanisms(self, priors: Dict) -> List[Dict]:
        """Select mechanisms based on psychological priors."""
        mechanisms = []
        
        big_five = priors.get("big_five", {})
        reg_focus = priors.get("regulatory_focus", {})
        
        # High openness → Novelty, Curiosity
        if big_five.get("openness", 0.5) > 0.6:
            mechanisms.append({
                "mechanism": "novelty",
                "score": big_five["openness"],
                "reason": "High openness suggests receptivity to new experiences",
            })
        
        # High conscientiousness → Authority, Quality
        if big_five.get("conscientiousness", 0.5) > 0.6:
            mechanisms.append({
                "mechanism": "authority",
                "score": big_five["conscientiousness"],
                "reason": "High conscientiousness responds to expertise and quality",
            })
        
        # Promotion focus → Gain framing
        if reg_focus.get("promotion", 0.5) > 0.55:
            mechanisms.append({
                "mechanism": "gain_framing",
                "score": reg_focus["promotion"],
                "reason": "Promotion focus responds to potential gains",
            })
        
        # Prevention focus → Loss framing
        if reg_focus.get("prevention", 0.5) > 0.55:
            mechanisms.append({
                "mechanism": "loss_framing",
                "score": reg_focus["prevention"],
                "reason": "Prevention focus responds to risk avoidance",
            })
        
        # High extraversion → Social proof
        if big_five.get("extraversion", 0.5) > 0.6:
            mechanisms.append({
                "mechanism": "social_proof",
                "score": big_five["extraversion"],
                "reason": "High extraversion influenced by social validation",
            })
        
        return sorted(mechanisms, key=lambda x: x["score"], reverse=True)[:3]
    
    def get_archetypes(self) -> Dict[str, Dict]:
        """Get all Amazon archetypes for display."""
        return self.cold_start.get_all_archetypes()


# =============================================================================
# FACTORY
# =============================================================================

def create_real_demo_engine(
    neo4j_driver=None,
    redis_client=None,
) -> RealPlatformDemoEngine:
    """Create the real platform demo engine."""
    return RealPlatformDemoEngine(
        neo4j_driver=neo4j_driver,
        redis_client=redis_client,
    )


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        engine = create_real_demo_engine()
        
        print("\n=== ADAM Real Platform Demo ===")
        print(f"Status: {engine.status.status_message}")
        print()
        
        result = await engine.generate_recommendation(
            user_id="test_user_123",
            station_format="CHR",
            daypart="Morning Drive",
        )
        
        print("Recommendation Result:")
        print(f"  Components used: {result['components_used']}")
        print(f"  Archetype: {result['cold_start'].get('archetype')}")
        print(f"  Routing: {result['routing'].get('execution_path')}")
        print(f"  Top mechanism: {result['mechanism_recommendations'][0] if result['mechanism_recommendations'] else 'None'}")
        
        print("\n=== Archetypes Available ===")
        for arch_id, arch in engine.get_archetypes().items():
            print(f"  {arch['name']}: {arch['description'][:50]}...")
    
    asyncio.run(test())
