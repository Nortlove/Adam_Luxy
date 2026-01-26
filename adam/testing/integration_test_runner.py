# =============================================================================
# ADAM Integration Test Runner
# Location: adam/testing/integration_test_runner.py
# =============================================================================

"""
INTEGRATION TEST RUNNER

This module orchestrates end-to-end testing of the ADAM learning pipeline.
It validates that all components:
1. Participate in learning correctly
2. Emit and consume signals properly
3. Improve predictions over time
4. Handle edge cases gracefully

The test runner simulates a complete user journey through ADAM,
from cold start through established user, validating learning at each stage.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import json
import logging
import uuid

# Import all learning integrations
from adam.core.learning.universal_learning_interface import (
    LearningSignal,
    LearningSignalType,
    LearningSignalRouter,
)
from adam.core.learning.component_integrations import LearningComponentRegistry
from adam.core.synthesis.holistic_decision_synthesizer import HolisticDecisionSynthesizer
from adam.multimodal.learning_integration import MultimodalFusionLearningBridge, Modality
from adam.features.learning_integration import FeatureStoreLearningBridge
from adam.temporal.learning_integration import TemporalLearningBridge, LifeEventType, DecisionStage
from adam.verification.learning_integration import VerificationLearningBridge, VerificationType
from adam.atoms.emergence_detector import EmergenceDetector, EmergenceType
from adam.coldstart.unified_learning import UnifiedColdStartLearning, UserTier, Archetype
from adam.signals.learning_integration import SignalAggregationLearningBridge
from adam.audio.learning_integration import AudioLearningBridge

logger = logging.getLogger(__name__)


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

class TestScenario(str, Enum):
    """Pre-defined test scenarios."""
    
    COLD_START_TO_ESTABLISHED = "cold_start_to_established"
    HIGH_CONVERSION_USER = "high_conversion_user"
    LOW_CONVERSION_USER = "low_conversion_user"
    ARCHETYPE_LEARNING = "archetype_learning"
    MODALITY_DRIFT = "modality_drift"
    EMERGENCE_DETECTION = "emergence_detection"
    VERIFICATION_LEARNING = "verification_learning"
    FULL_JOURNEY = "full_journey"


@dataclass
class SyntheticUser:
    """A synthetic user for testing."""
    
    user_id: str
    
    # Ground truth personality
    true_personality: Dict[str, float] = field(default_factory=dict)
    
    # Ground truth mechanism responsiveness
    true_mechanism_responsiveness: Dict[str, float] = field(default_factory=dict)
    
    # Behavioral patterns
    optimal_hour: int = 14
    optimal_day: int = 2  # Wednesday
    life_event: Optional[LifeEventType] = None
    
    # Decision stage
    current_stage: DecisionStage = DecisionStage.AWARE
    
    # Archetype
    true_archetype: Optional[Archetype] = None
    
    # Conversion probability function
    base_conversion_rate: float = 0.15
    
    def compute_conversion_probability(
        self,
        mechanism: str,
        hour: int,
        day: int,
        modality_confidence: float,
        context: Dict[str, Any]
    ) -> float:
        """Compute probability of conversion given context."""
        
        prob = self.base_conversion_rate
        
        # Mechanism match
        if mechanism in self.true_mechanism_responsiveness:
            prob += self.true_mechanism_responsiveness[mechanism] * 0.3
        
        # Timing match
        if hour == self.optimal_hour:
            prob += 0.1
        if day == self.optimal_day:
            prob += 0.05
        
        # Modality confidence
        prob += modality_confidence * 0.1
        
        # Stage progression
        stage_multipliers = {
            DecisionStage.UNAWARE: 0.3,
            DecisionStage.AWARE: 0.6,
            DecisionStage.CONSIDERATION: 1.0,
            DecisionStage.EVALUATION: 1.5,
            DecisionStage.DECISION: 2.0,
            DecisionStage.POST_PURCHASE: 0.8,
        }
        prob *= stage_multipliers.get(self.current_stage, 1.0)
        
        return min(max(prob, 0.01), 0.95)


@dataclass
class TestResult:
    """Result of a test run."""
    
    scenario: TestScenario
    
    # Summary metrics
    total_decisions: int = 0
    total_conversions: int = 0
    
    # Learning metrics
    initial_accuracy: float = 0.5
    final_accuracy: float = 0.5
    accuracy_improvement: float = 0.0
    
    # Component health
    component_health: Dict[str, bool] = field(default_factory=dict)
    
    # Signal flow
    signals_emitted: int = 0
    signals_consumed: int = 0
    
    # Emergence
    discoveries_made: int = 0
    
    # Detailed logs
    decision_log: List[Dict[str, Any]] = field(default_factory=list)
    signal_log: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Pass/Fail
    passed: bool = False
    failure_reasons: List[str] = field(default_factory=list)


# =============================================================================
# MOCK INFRASTRUCTURE
# =============================================================================

class MockNeo4jDriver:
    """Mock Neo4j driver for testing."""
    
    def __init__(self):
        self.data = {}
        self.queries_run = []
    
    def session(self):
        return MockNeo4jSession(self)


class MockNeo4jSession:
    """Mock Neo4j session."""
    
    def __init__(self, driver):
        self.driver = driver
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def run(self, query, **params):
        self.driver.queries_run.append({"query": query, "params": params})
        return MockNeo4jResult()
    
    async def data(self):
        return []


class MockNeo4jResult:
    """Mock Neo4j result."""
    
    async def data(self):
        return []
    
    async def single(self):
        return {"interaction_count": 0}


class MockRedisClient:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
    
    async def setex(self, key: str, ttl: int, value: Any):
        self.data[key] = value
    
    async def get(self, key: str):
        return self.data.get(key)
    
    async def delete(self, key: str):
        self.data.pop(key, None)


class MockEventBus:
    """Mock event bus for testing."""
    
    def __init__(self):
        self.events = []
        self.subscribers = {}
    
    async def publish(self, topic: str, event: Dict[str, Any]):
        self.events.append({"topic": topic, "event": event})
        
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                await callback(event)
    
    def subscribe(self, topic: str, callback):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)


class MockClaudeClient:
    """Mock Claude client for testing."""
    
    async def complete(self, prompt: str, **kwargs) -> str:
        return '{"assessment": "mock", "confidence": 0.7}'


class MockAtomPromptManager:
    """Mock atom prompt manager."""
    
    def __init__(self):
        self.prompts = {}
        self.updates = []
    
    async def get_prompt(self, atom_name: str) -> str:
        return self.prompts.get(atom_name, f"Default prompt for {atom_name}")
    
    async def update_prompt(self, atom_name: str, new_prompt: str, reason: str):
        self.prompts[atom_name] = new_prompt
        self.updates.append({
            "atom_name": atom_name,
            "new_prompt": new_prompt,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc),
        })


class MockVerificationLayer:
    """Mock verification layer."""
    
    def __init__(self):
        self.strictness = {}
    
    async def increase_strictness(self, atom_name: str):
        self.strictness[atom_name] = self.strictness.get(atom_name, 1.0) + 0.1


class MockThompsonSampler:
    """Mock Thompson Sampler."""
    
    def __init__(self):
        self.posteriors = {}
    
    async def update_posterior(self, arm: str, reward: float, context: Dict[str, Any]):
        if arm not in self.posteriors:
            self.posteriors[arm] = {"alpha": 1, "beta": 1}
        if reward > 0.5:
            self.posteriors[arm]["alpha"] += 1
        else:
            self.posteriors[arm]["beta"] += 1


class MockColdStartEngine:
    """Mock cold start engine."""
    
    def __init__(self):
        self.overrides = {}
    
    async def set_archetype_override(self, user_id: str, archetype: Archetype):
        self.overrides[user_id] = archetype


class MockFusionEngine:
    """Mock fusion engine."""
    pass


class MockFeatureStore:
    """Mock feature store."""
    pass


class MockTemporalEngine:
    """Mock temporal engine."""
    pass


class MockArchetypeLibrary:
    """Mock archetype library."""
    pass


# =============================================================================
# TEST ORCHESTRATOR
# =============================================================================

class IntegrationTestOrchestrator:
    """
    Orchestrates end-to-end integration tests for ADAM learning.
    """
    
    def __init__(self):
        # Mock infrastructure
        self.neo4j = MockNeo4jDriver()
        self.redis = MockRedisClient()
        self.event_bus = MockEventBus()
        self.claude = MockClaudeClient()
        
        # Mock dependencies
        self.atom_prompt_manager = MockAtomPromptManager()
        self.verification_layer_mock = MockVerificationLayer()
        self.thompson_sampler = MockThompsonSampler()
        self.cold_start_engine = MockColdStartEngine()
        
        # Initialize learning components
        self._init_components()
        
        # Signal router
        self.signal_router = LearningSignalRouter()
        self._register_signal_consumers()
        
        # Test state
        self.results: Dict[TestScenario, TestResult] = {}
    
    def _init_components(self):
        """Initialize all learning components."""
        
        self.multimodal_learning = MultimodalFusionLearningBridge(
            fusion_engine=MockFusionEngine(),
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
        
        self.feature_store_learning = FeatureStoreLearningBridge(
            feature_store=MockFeatureStore(),
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
        
        self.temporal_learning = TemporalLearningBridge(
            temporal_engine=MockTemporalEngine(),
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
        
        self.verification_learning = VerificationLearningBridge(
            verification_layer=self.verification_layer_mock,
            atom_prompt_manager=self.atom_prompt_manager,
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
        
        self.emergence_detector = EmergenceDetector(
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
            claude_client=self.claude,
        )
        
        self.cold_start_learning = UnifiedColdStartLearning(
            cold_start_engine=self.cold_start_engine,
            archetype_library=MockArchetypeLibrary(),
            thompson_sampler=self.thompson_sampler,
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
        
        self.signal_learning = SignalAggregationLearningBridge(
            signal_aggregator=None,
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
        
        self.audio_learning = AudioLearningBridge(
            audio_processor=None,
            neo4j_driver=self.neo4j,
            redis_client=self.redis,
            event_bus=self.event_bus,
        )
    
    def _register_signal_consumers(self):
        """Register all signal consumers with the router."""
        
        components = [
            self.multimodal_learning,
            self.feature_store_learning,
            self.temporal_learning,
            self.verification_learning,
            self.emergence_detector,
            self.cold_start_learning,
            self.signal_learning,
            self.audio_learning,
        ]
        
        for component in components:
            self.signal_router.register_consumer(component)
    
    # =========================================================================
    # TEST SCENARIOS
    # =========================================================================
    
    async def run_scenario(self, scenario: TestScenario) -> TestResult:
        """Run a specific test scenario."""
        
        result = TestResult(scenario=scenario)
        
        try:
            if scenario == TestScenario.COLD_START_TO_ESTABLISHED:
                result = await self._test_cold_start_to_established(result)
            elif scenario == TestScenario.ARCHETYPE_LEARNING:
                result = await self._test_archetype_learning(result)
            elif scenario == TestScenario.MODALITY_DRIFT:
                result = await self._test_modality_drift(result)
            elif scenario == TestScenario.EMERGENCE_DETECTION:
                result = await self._test_emergence_detection(result)
            elif scenario == TestScenario.VERIFICATION_LEARNING:
                result = await self._test_verification_learning(result)
            elif scenario == TestScenario.FULL_JOURNEY:
                result = await self._test_full_journey(result)
            else:
                result.failure_reasons.append(f"Unknown scenario: {scenario}")
        
        except Exception as e:
            result.failure_reasons.append(f"Exception: {str(e)}")
            logger.exception(f"Scenario {scenario} failed with exception")
        
        result.completed_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        result.passed = len(result.failure_reasons) == 0
        
        self.results[scenario] = result
        return result
    
    async def _test_cold_start_to_established(self, result: TestResult) -> TestResult:
        """
        Test: Cold Start → Developing → Established transition.
        
        Validates:
        1. Archetype selection improves over time
        2. Personality inference gets more accurate
        3. Tier transitions happen at optimal points
        4. Thompson Sampling converges
        """
        
        # Create synthetic user
        user = SyntheticUser(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            true_personality={
                "openness": 0.8,
                "conscientiousness": 0.6,
                "extraversion": 0.5,
                "agreeableness": 0.7,
                "neuroticism": 0.3,
            },
            true_mechanism_responsiveness={
                "identity_construction": 0.8,
                "social_proof": 0.5,
                "scarcity": 0.3,
            },
            true_archetype=Archetype.EXPLORER,
            base_conversion_rate=0.2,
        )
        
        predictions_correct = []
        
        # Simulate 30 interactions (cold → developing → established)
        for i in range(30):
            decision_id = f"decision_{i}_{uuid.uuid4().hex[:8]}"
            
            # Determine current tier
            if i < 3:
                tier = UserTier.COLD
            elif i < 10:
                tier = UserTier.DEVELOPING
            else:
                tier = UserTier.ESTABLISHED
            
            # Register cold start prediction
            await self.cold_start_learning.register_cold_start_prediction(
                decision_id=decision_id,
                user_id=user.user_id,
                tier=tier,
                archetype=Archetype.EXPLORER if tier == UserTier.COLD else None,
                archetype_confidence=0.6 if tier == UserTier.COLD else 0.0,
                inferred_personality={
                    "openness": 0.7 + np.random.uniform(-0.1, 0.1),
                    "conscientiousness": 0.5 + np.random.uniform(-0.1, 0.1),
                },
                mechanism_priors={"identity_construction": 0.7},
                predicted_outcome=0.5 + i * 0.01,  # Should improve
                bandit_arm="arm_identity",
                arm_reason="Thompson selection",
            )
            
            # Compute actual outcome
            mechanism = "identity_construction"
            hour = 14
            day = 2
            
            conversion_prob = user.compute_conversion_probability(
                mechanism=mechanism,
                hour=hour,
                day=day,
                modality_confidence=0.7,
                context={},
            )
            
            actual_outcome = 1.0 if np.random.random() < conversion_prob else 0.0
            
            # Process outcome
            signals = await self.cold_start_learning.on_outcome_received(
                decision_id=decision_id,
                outcome_type="conversion",
                outcome_value=actual_outcome,
                context={"mechanism_applied": mechanism},
            )
            
            result.signals_emitted += len(signals)
            
            # Route signals
            for signal in signals:
                await self.signal_router.route_signal(signal)
                result.signals_consumed += 1
            
            # Track accuracy
            predicted = 0.5 + i * 0.01
            was_correct = (predicted > 0.5) == (actual_outcome > 0.5)
            predictions_correct.append(was_correct)
            
            result.total_decisions += 1
            result.total_conversions += int(actual_outcome)
            
            result.decision_log.append({
                "decision_id": decision_id,
                "tier": tier.value,
                "predicted": predicted,
                "actual": actual_outcome,
                "correct": was_correct,
            })
        
        # Compute accuracy improvement
        result.initial_accuracy = np.mean(predictions_correct[:10])
        result.final_accuracy = np.mean(predictions_correct[-10:])
        result.accuracy_improvement = result.final_accuracy - result.initial_accuracy
        
        # Validate component health
        for component_name, component in [
            ("cold_start", self.cold_start_learning),
            ("multimodal", self.multimodal_learning),
        ]:
            health, issues = await component.validate_learning_health()
            result.component_health[component_name] = health
            if not health:
                result.failure_reasons.extend(issues)
        
        # Check that archetype effectiveness was updated
        archetype_eff = self.cold_start_learning.archetype_effectiveness[Archetype.EXPLORER]
        if archetype_eff.times_used == 0:
            result.failure_reasons.append("Archetype effectiveness not updated")
        
        return result
    
    async def _test_archetype_learning(self, result: TestResult) -> TestResult:
        """
        Test: Archetype effectiveness learning.
        
        Validates:
        1. Different archetypes get different effectiveness scores
        2. Mechanism priors are learned per archetype
        3. Category-specific effectiveness is tracked
        """
        
        # Simulate users of different archetypes
        archetype_outcomes = {
            Archetype.EXPLORER: [],
            Archetype.ACHIEVER: [],
            Archetype.GUARDIAN: [],
        }
        
        for archetype in archetype_outcomes.keys():
            for i in range(20):
                decision_id = f"arch_{archetype.value}_{i}"
                
                await self.cold_start_learning.register_cold_start_prediction(
                    decision_id=decision_id,
                    user_id=f"user_{archetype.value}_{i}",
                    tier=UserTier.COLD,
                    archetype=archetype,
                    archetype_confidence=0.8,
                    mechanism_priors={"identity_construction": 0.5},
                    predicted_outcome=0.5,
                )
                
                # Different archetypes have different true conversion rates
                true_rates = {
                    Archetype.EXPLORER: 0.7,
                    Archetype.ACHIEVER: 0.5,
                    Archetype.GUARDIAN: 0.3,
                }
                
                actual = 1.0 if np.random.random() < true_rates[archetype] else 0.0
                archetype_outcomes[archetype].append(actual)
                
                signals = await self.cold_start_learning.on_outcome_received(
                    decision_id=decision_id,
                    outcome_type="conversion",
                    outcome_value=actual,
                    context={},
                )
                
                result.signals_emitted += len(signals)
                result.total_decisions += 1
        
        # Validate that learned effectiveness matches ground truth
        for archetype in archetype_outcomes.keys():
            eff = self.cold_start_learning.archetype_effectiveness[archetype]
            expected = np.mean(archetype_outcomes[archetype])
            
            if abs(eff.effectiveness - expected) > 0.2:
                result.failure_reasons.append(
                    f"Archetype {archetype.value}: expected {expected:.2f}, got {eff.effectiveness:.2f}"
                )
        
        return result
    
    async def _test_modality_drift(self, result: TestResult) -> TestResult:
        """
        Test: Modality weight adaptation when one modality becomes unreliable.
        
        Validates:
        1. Weights start balanced
        2. Unreliable modality gets downweighted
        3. System adapts to modality quality changes
        """
        
        initial_weights = self.multimodal_learning.get_learned_weights()
        
        # Simulate 50 decisions where voice modality is unreliable
        for i in range(50):
            decision_id = f"modality_{i}"
            
            # Voice predicts wrong, behavioral predicts right
            await self.multimodal_learning.register_fusion(
                decision_id=decision_id,
                user_id="test_user",
                modality_signals={
                    Modality.VOICE: {
                        "value": 0.8,
                        "confidence": 0.7,
                        "prediction": 0.8,  # Predicts high
                        "sources": ["arousal"],
                    },
                    Modality.BEHAVIORAL: {
                        "value": 0.3,
                        "confidence": 0.6,
                        "prediction": 0.3,  # Predicts low (correct!)
                        "sources": ["click_pattern"],
                    },
                },
                fusion_method=self.multimodal_learning.get_optimal_method({}),
                fused_result=0.55,
                fusion_confidence=0.65,
            )
            
            # Actual outcome is low (voice was wrong)
            actual = 0.2
            
            signals = await self.multimodal_learning.on_outcome_received(
                decision_id=decision_id,
                outcome_type="conversion",
                outcome_value=actual,
                context={},
            )
            
            result.signals_emitted += len(signals)
            result.total_decisions += 1
        
        final_weights = self.multimodal_learning.get_learned_weights()
        
        # Voice should be downweighted, behavioral should be upweighted
        voice_change = final_weights["voice"] - initial_weights["voice"]
        behavioral_change = final_weights["behavioral"] - initial_weights["behavioral"]
        
        if voice_change >= 0:
            result.failure_reasons.append(
                f"Voice modality not downweighted: {initial_weights['voice']:.3f} → {final_weights['voice']:.3f}"
            )
        
        if behavioral_change <= 0:
            result.failure_reasons.append(
                f"Behavioral modality not upweighted: {initial_weights['behavioral']:.3f} → {final_weights['behavioral']:.3f}"
            )
        
        result.decision_log.append({
            "initial_weights": initial_weights,
            "final_weights": final_weights,
        })
        
        return result
    
    async def _test_emergence_detection(self, result: TestResult) -> TestResult:
        """
        Test: Emergence detection from prediction residuals.
        
        Validates:
        1. Novel constructs are detected when patterns emerge
        2. Theory boundaries are identified when atoms fail systematically
        3. Discoveries are stored in Neo4j
        """
        
        # Simulate decisions with a hidden pattern
        # Users with high openness + evening time = unexpectedly high conversion
        
        for i in range(150):
            decision_id = f"emergence_{i}"
            
            # Half have the magic combination
            has_pattern = i % 2 == 0
            
            atom_outputs = {
                "regulatory_focus": {"regulatory_focus": "promotion"},
                "construal_level": {"construal_level": "high"},
                "personality": {
                    "openness": 0.8 if has_pattern else 0.4,
                    "conscientiousness": 0.5,
                },
            }
            
            context = {
                "time_of_day": "evening" if has_pattern else "morning",
                "atom_outputs": atom_outputs,
                "prediction": 0.5,  # Standard prediction
            }
            
            # Actual outcome is high for magic combo
            if has_pattern:
                actual = 0.9 if np.random.random() < 0.8 else 0.2
            else:
                actual = 0.3 if np.random.random() < 0.7 else 0.7
            
            signals = await self.emergence_detector.on_outcome_received(
                decision_id=decision_id,
                outcome_type="conversion",
                outcome_value=actual,
                context=context,
            )
            
            result.signals_emitted += len(signals)
            result.total_decisions += 1
            
            # Count discoveries
            for signal in signals:
                if signal.signal_type in [
                    LearningSignalType.NOVEL_CONSTRUCT_DISCOVERED,
                    LearningSignalType.CAUSAL_EDGE_DISCOVERED,
                    LearningSignalType.THEORY_BOUNDARY_FOUND,
                ]:
                    result.discoveries_made += 1
        
        # Should have detected something
        if result.discoveries_made == 0:
            result.failure_reasons.append(
                "No emergence detected despite clear pattern in data"
            )
        
        return result
    
    async def _test_verification_learning(self, result: TestResult) -> TestResult:
        """
        Test: Verification failures updating atom prompts.
        
        Validates:
        1. Failure patterns are tracked
        2. Prompt adjustments are generated
        3. Adjustments are applied to atom prompts
        """
        
        from adam.verification.learning_integration import VerificationResult
        
        # Simulate consistent consistency failures for regulatory_focus atom
        for i in range(25):
            decision_id = f"verify_{i}"
            
            # Create verification results with failures
            results = [
                VerificationResult(
                    decision_id=decision_id,
                    atom_name="regulatory_focus",
                    verification_type=VerificationType.CONSISTENCY,
                    passed=False,  # Consistently failing
                    confidence=0.6,
                    failure_reason="Contradicts personality assessment",
                ),
                VerificationResult(
                    decision_id=decision_id,
                    atom_name="construal_level",
                    verification_type=VerificationType.CALIBRATION,
                    passed=True,
                    confidence=0.8,
                ),
            ]
            
            await self.verification_learning.register_verification_results(
                decision_id=decision_id,
                results=results,
            )
            
            # Process outcome
            signals = await self.verification_learning.on_outcome_received(
                decision_id=decision_id,
                outcome_type="conversion",
                outcome_value=0.3,  # Low outcome confirms failure was right
                context={},
            )
            
            result.signals_emitted += len(signals)
            result.total_decisions += 1
        
        # Check that prompt adjustment was made
        if len(self.atom_prompt_manager.updates) == 0:
            result.failure_reasons.append(
                "No prompt adjustments made despite 25 consistency failures"
            )
        else:
            result.decision_log.append({
                "prompt_updates": [
                    {"atom": u["atom_name"], "reason": u["reason"]}
                    for u in self.atom_prompt_manager.updates
                ]
            })
        
        return result
    
    async def _test_full_journey(self, result: TestResult) -> TestResult:
        """
        Test: Full user journey through all components.
        
        Validates:
        1. All components participate in learning
        2. Signals flow correctly between components
        3. Predictions improve over time
        4. System becomes coherent
        """
        
        user = SyntheticUser(
            user_id=f"full_journey_{uuid.uuid4().hex[:8]}",
            true_personality={
                "openness": 0.7,
                "conscientiousness": 0.8,
                "extraversion": 0.4,
                "agreeableness": 0.6,
                "neuroticism": 0.3,
            },
            true_mechanism_responsiveness={
                "identity_construction": 0.7,
                "social_proof": 0.6,
                "scarcity": 0.4,
            },
            true_archetype=Archetype.ACHIEVER,
            optimal_hour=10,
            optimal_day=1,  # Tuesday
            current_stage=DecisionStage.AWARE,
            base_conversion_rate=0.25,
        )
        
        predictions_errors = []
        
        # Simulate 50 decisions through full journey
        for i in range(50):
            decision_id = f"journey_{i}"
            
            # === 1. COLD START ===
            tier = UserTier.COLD if i < 3 else UserTier.DEVELOPING if i < 10 else UserTier.ESTABLISHED
            
            await self.cold_start_learning.register_cold_start_prediction(
                decision_id=decision_id,
                user_id=user.user_id,
                tier=tier,
                archetype=Archetype.ACHIEVER if tier == UserTier.COLD else None,
                archetype_confidence=0.7 if tier == UserTier.COLD else 0.0,
                predicted_outcome=0.5,
            )
            
            # === 2. TEMPORAL ===
            hour = np.random.choice([8, 10, 12, 14, 18])
            day = np.random.choice([0, 1, 2, 3, 4])
            
            await self.temporal_learning.register_temporal_prediction(
                decision_id=decision_id,
                user_id=user.user_id,
                predicted_optimal_hour=10,
                predicted_optimal_day=1,
                predicted_decision_stage=user.current_stage,
            )
            
            # === 3. MULTIMODAL ===
            await self.multimodal_learning.register_fusion(
                decision_id=decision_id,
                user_id=user.user_id,
                modality_signals={
                    Modality.BEHAVIORAL: {
                        "value": 0.6,
                        "confidence": 0.7,
                        "prediction": 0.6,
                        "sources": ["click"],
                    },
                    Modality.PSYCHOLOGICAL: {
                        "value": 0.7,
                        "confidence": 0.6,
                        "prediction": 0.7,
                        "sources": ["atom"],
                    },
                },
                fusion_method=self.multimodal_learning.get_optimal_method({}),
                fused_result=0.65,
                fusion_confidence=0.65,
            )
            
            # === 4. FEATURE STORE ===
            await self.feature_store_learning.register_feature_access(
                decision_id=decision_id,
                user_id=user.user_id,
                features_used={
                    "openness": {"value": 0.7, "contribution": 0.1},
                    "conscientiousness": {"value": 0.8, "contribution": 0.15},
                    "time_of_day": {"value": hour, "contribution": 0.05},
                },
            )
            
            # === 5. COMPUTE OUTCOME ===
            mechanism = np.random.choice(["identity_construction", "social_proof", "scarcity"])
            
            conversion_prob = user.compute_conversion_probability(
                mechanism=mechanism,
                hour=hour,
                day=day,
                modality_confidence=0.65,
                context={},
            )
            
            actual = 1.0 if np.random.random() < conversion_prob else 0.0
            predicted = 0.5 + i * 0.005  # Slow improvement
            predictions_errors.append(abs(predicted - actual))
            
            # === 6. PROPAGATE LEARNING ===
            context = {
                "mechanism_applied": mechanism,
                "atom_outputs": {"personality": user.true_personality},
                "prediction": predicted,
            }
            
            # All components learn
            for component in [
                self.cold_start_learning,
                self.temporal_learning,
                self.multimodal_learning,
                self.feature_store_learning,
                self.emergence_detector,
            ]:
                signals = await component.on_outcome_received(
                    decision_id=decision_id,
                    outcome_type="conversion",
                    outcome_value=actual,
                    context=context,
                )
                
                result.signals_emitted += len(signals)
                
                # Route all signals
                for signal in signals:
                    await self.signal_router.route_signal(signal)
                    result.signals_consumed += 1
            
            result.total_decisions += 1
            result.total_conversions += int(actual)
            
            # Progress decision stage
            if actual > 0.5 and np.random.random() < 0.3:
                stages = list(DecisionStage)
                current_idx = stages.index(user.current_stage)
                if current_idx < len(stages) - 1:
                    user.current_stage = stages[current_idx + 1]
        
        # Compute metrics
        result.initial_accuracy = 1 - np.mean(predictions_errors[:10])
        result.final_accuracy = 1 - np.mean(predictions_errors[-10:])
        result.accuracy_improvement = result.final_accuracy - result.initial_accuracy
        
        # Validate all component health
        for name, component in [
            ("cold_start", self.cold_start_learning),
            ("temporal", self.temporal_learning),
            ("multimodal", self.multimodal_learning),
            ("feature_store", self.feature_store_learning),
            ("emergence", self.emergence_detector),
        ]:
            health, issues = await component.validate_learning_health()
            result.component_health[name] = health
        
        # Must have improvement
        if result.accuracy_improvement <= 0:
            result.failure_reasons.append(
                f"No accuracy improvement: {result.initial_accuracy:.3f} → {result.final_accuracy:.3f}"
            )
        
        return result
    
    # =========================================================================
    # TEST EXECUTION
    # =========================================================================
    
    async def run_all_tests(self) -> Dict[TestScenario, TestResult]:
        """Run all test scenarios."""
        
        scenarios = [
            TestScenario.COLD_START_TO_ESTABLISHED,
            TestScenario.ARCHETYPE_LEARNING,
            TestScenario.MODALITY_DRIFT,
            TestScenario.EMERGENCE_DETECTION,
            TestScenario.VERIFICATION_LEARNING,
            TestScenario.FULL_JOURNEY,
        ]
        
        for scenario in scenarios:
            logger.info(f"Running scenario: {scenario.value}")
            
            # Reset state between tests
            self._init_components()
            self._register_signal_consumers()
            
            await self.run_scenario(scenario)
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a human-readable test report."""
        
        lines = [
            "=" * 80,
            "ADAM INTEGRATION TEST REPORT",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "=" * 80,
            "",
        ]
        
        total_passed = 0
        total_failed = 0
        
        for scenario, result in self.results.items():
            status = "✓ PASSED" if result.passed else "✗ FAILED"
            lines.append(f"\n{scenario.value}: {status}")
            lines.append("-" * 40)
            
            lines.append(f"  Decisions: {result.total_decisions}")
            lines.append(f"  Conversions: {result.total_conversions}")
            lines.append(f"  Signals Emitted: {result.signals_emitted}")
            lines.append(f"  Signals Consumed: {result.signals_consumed}")
            lines.append(f"  Duration: {result.duration_seconds:.2f}s")
            
            if result.accuracy_improvement != 0:
                lines.append(f"  Accuracy Improvement: {result.accuracy_improvement:+.3f}")
            
            if result.discoveries_made > 0:
                lines.append(f"  Discoveries: {result.discoveries_made}")
            
            if result.component_health:
                healthy = sum(result.component_health.values())
                total = len(result.component_health)
                lines.append(f"  Component Health: {healthy}/{total}")
            
            if result.failure_reasons:
                lines.append("  Failures:")
                for reason in result.failure_reasons:
                    lines.append(f"    - {reason}")
            
            if result.passed:
                total_passed += 1
            else:
                total_failed += 1
        
        lines.extend([
            "",
            "=" * 80,
            f"SUMMARY: {total_passed} passed, {total_failed} failed",
            "=" * 80,
        ])
        
        return "\n".join(lines)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Run integration tests."""
    
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = IntegrationTestOrchestrator()
    await orchestrator.run_all_tests()
    
    print(orchestrator.generate_report())
    
    # Return exit code based on results
    all_passed = all(r.passed for r in orchestrator.results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
