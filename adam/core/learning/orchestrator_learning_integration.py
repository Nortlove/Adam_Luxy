# =============================================================================
# ADAM Orchestrator Learning Integration
# Location: adam/core/learning/orchestrator_learning_integration.py
# =============================================================================

"""
ORCHESTRATOR LEARNING INTEGRATION

Provides deep learning integration for the Campaign Orchestrator,
enabling it to learn from campaign outcomes and improve:

1. Archetype selection strategies
2. Mechanism combination effectiveness
3. Station recommendation accuracy
4. Overall campaign optimization

This completes the learning loop for campaign-level decisions.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import logging
from collections import defaultdict

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningSignalPriority,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CAMPAIGN ORCHESTRATOR LEARNING INTEGRATION
# =============================================================================

class CampaignOrchestratorLearningIntegration(LearningCapableComponent):
    """
    Learning integration for the Campaign Orchestrator.
    
    Learns from campaign outcomes to improve:
    - Archetype selection for products/brands
    - Mechanism effectiveness predictions
    - Station recommendation accuracy
    - Segment targeting effectiveness
    
    This is a critical learning component that closes the loop between
    campaign recommendations and real-world outcomes.
    """
    
    def __init__(self, orchestrator_instance=None):
        self.orchestrator = orchestrator_instance
        
        # Campaign tracking
        self._campaigns: Dict[str, Dict[str, Any]] = {}
        self._outcomes_processed: int = 0
        self._signals_emitted: int = 0
        
        # Learning state
        self._archetype_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._mechanism_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._station_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._segment_outcomes: Dict[str, List[float]] = defaultdict(list)
        
        # Accuracy tracking
        self._accuracy_history: List[Tuple[datetime, float]] = []
        self._prediction_calibration: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        
        # Posteriors for Bayesian learning
        self._archetype_brand_posteriors: Dict[str, Dict[str, Tuple[float, float]]] = defaultdict(lambda: defaultdict(lambda: (1.0, 1.0)))
        self._mechanism_posteriors: Dict[str, Tuple[float, float]] = defaultdict(lambda: (1.0, 1.0))
    
    @property
    def component_name(self) -> str:
        return "campaign_orchestrator"
    
    @property
    def component_version(self) -> str:
        return "2.0"
    
    async def register_campaign(
        self,
        campaign_id: str,
        brand: str,
        product: str,
        segments: List[Dict[str, Any]],
        mechanisms: List[str],
        stations: List[Dict[str, Any]],
        overall_confidence: float,
        reasoning_trace: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a campaign for later learning."""
        self._campaigns[campaign_id] = {
            "brand": brand,
            "product": product,
            "segments": segments,
            "mechanisms": mechanisms,
            "stations": stations,
            "overall_confidence": overall_confidence,
            "reasoning_trace": reasoning_trace,
            "timestamp": datetime.now(timezone.utc),
        }
        
        logger.debug(f"Registered campaign {campaign_id} for learning")
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """
        Learn from campaign outcome.
        
        This is the core learning method that:
        1. Validates campaign predictions
        2. Updates posteriors
        3. Emits learning signals
        4. Tracks accuracy
        """
        signals = []
        
        # Get stored campaign
        campaign = self._campaigns.pop(decision_id, None)
        if not campaign:
            return signals
        
        self._outcomes_processed += 1
        
        # Extract campaign details
        brand = campaign["brand"]
        segments = campaign["segments"]
        mechanisms = campaign["mechanisms"]
        stations = campaign["stations"]
        predicted_confidence = campaign["overall_confidence"]
        
        # Compute overall accuracy
        accuracy = self._compute_campaign_accuracy(campaign, outcome_value, context)
        
        # Track accuracy
        self._accuracy_history.append((datetime.now(timezone.utc), accuracy))
        
        # Update posteriors
        await self._update_all_posteriors(campaign, outcome_value, accuracy, context)
        
        # 1. Emit campaign outcome signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.OUTCOME_CONVERSION if outcome_value > 0.5 else LearningSignalType.OUTCOME_REJECTION,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "brand": brand,
                "segments": [s.get("archetype") for s in segments],
                "mechanisms": mechanisms,
                "stations": [s.get("station_format") for s in stations],
                "outcome": outcome_value,
                "predicted_confidence": predicted_confidence,
                "accuracy": accuracy,
            },
            confidence=accuracy,
            priority=LearningSignalPriority.HIGH,
            target_components=["gradient_bridge", "meta_learner", "thompson_sampler"],
        ))
        self._signals_emitted += 1
        
        # 2. Emit archetype effectiveness signals
        for segment in segments:
            archetype = segment.get("archetype")
            if archetype:
                archetype_accuracy = self._compute_segment_accuracy(segment, outcome_value, context)
                
                signals.append(LearningSignal(
                    signal_type=LearningSignalType.PRIOR_UPDATED,
                    source_component=self.component_name,
                    decision_id=decision_id,
                    payload={
                        "archetype": archetype,
                        "brand": brand,
                        "effectiveness": archetype_accuracy,
                        "outcome": outcome_value,
                    },
                    confidence=archetype_accuracy,
                    priority=LearningSignalPriority.MEDIUM,
                    target_components=["thompson_sampler", "cold_start"],
                ))
                self._signals_emitted += 1
        
        # 3. Emit mechanism effectiveness signals
        for mechanism in mechanisms:
            mech_accuracy = self._compute_mechanism_accuracy(mechanism, campaign, outcome_value)
            
            signals.append(LearningSignal(
                signal_type=LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "mechanism": mechanism,
                    "effectiveness": mech_accuracy,
                    "outcome": outcome_value,
                    "context": {
                        "brand": brand,
                        "archetypes": [s.get("archetype") for s in segments],
                    },
                },
                confidence=mech_accuracy,
                priority=LearningSignalPriority.HIGH,
                target_components=["gradient_bridge", "thompson_sampler"],
            ))
            self._signals_emitted += 1
        
        # 4. Emit station effectiveness signals
        for station in stations:
            station_format = station.get("station_format")
            if station_format:
                station_accuracy = self._compute_station_accuracy(station, outcome_value, context)
                
                signals.append(LearningSignal(
                    signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                    source_component=self.component_name,
                    decision_id=decision_id,
                    payload={
                        "station_format": station_format,
                        "effectiveness": station_accuracy,
                        "outcome": outcome_value,
                        "archetypes": [s.get("archetype") for s in segments],
                    },
                    confidence=station_accuracy,
                    priority=LearningSignalPriority.MEDIUM,
                    target_components=["graph_reasoning"],
                ))
                self._signals_emitted += 1
        
        # 5. Emit calibration signal if miscalibrated
        calibration_error = abs(predicted_confidence - accuracy)
        if calibration_error > 0.2:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.CALIBRATION_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "calibration_error": calibration_error,
                    "direction": "overconfident" if predicted_confidence > accuracy else "underconfident",
                    "predicted": predicted_confidence,
                    "actual": accuracy,
                },
                confidence=0.8,
                priority=LearningSignalPriority.LOW,
            ))
            self._signals_emitted += 1
        
        logger.info(
            f"Processed campaign outcome {decision_id}: "
            f"accuracy={accuracy:.2f}, signals={len(signals)}"
        )
        
        return signals
    
    def _compute_campaign_accuracy(
        self,
        campaign: Dict[str, Any],
        outcome_value: float,
        context: Dict[str, Any],
    ) -> float:
        """Compute overall campaign prediction accuracy."""
        predicted = campaign["overall_confidence"]
        # Simple accuracy: how close was our confidence to the outcome
        return 1.0 - abs(predicted - outcome_value)
    
    def _compute_segment_accuracy(
        self,
        segment: Dict[str, Any],
        outcome_value: float,
        context: Dict[str, Any],
    ) -> float:
        """Compute accuracy for a specific segment prediction."""
        match_score = segment.get("match_score", 0.5)
        return 1.0 - abs(match_score - outcome_value)
    
    def _compute_mechanism_accuracy(
        self,
        mechanism: str,
        campaign: Dict[str, Any],
        outcome_value: float,
    ) -> float:
        """Compute accuracy for a mechanism prediction."""
        # For now, use outcome as proxy for mechanism effectiveness
        return outcome_value
    
    def _compute_station_accuracy(
        self,
        station: Dict[str, Any],
        outcome_value: float,
        context: Dict[str, Any],
    ) -> float:
        """Compute accuracy for a station prediction."""
        predicted_fit = station.get("listener_profile_match", 0.5)
        return 1.0 - abs(predicted_fit - outcome_value)
    
    async def _update_all_posteriors(
        self,
        campaign: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
        context: Dict[str, Any],
    ) -> None:
        """Update all posterior distributions."""
        brand = campaign["brand"]
        success = outcome_value > 0.5
        
        # Update archetype-brand posteriors
        for segment in campaign["segments"]:
            archetype = segment.get("archetype")
            if archetype:
                alpha, beta = self._archetype_brand_posteriors[brand][archetype]
                if success:
                    self._archetype_brand_posteriors[brand][archetype] = (alpha + 1, beta)
                else:
                    self._archetype_brand_posteriors[brand][archetype] = (alpha, beta + 1)
                
                # Track outcomes
                self._archetype_outcomes[brand][archetype].append(outcome_value)
        
        # Update mechanism posteriors
        for mechanism in campaign["mechanisms"]:
            alpha, beta = self._mechanism_posteriors[mechanism]
            if success:
                self._mechanism_posteriors[mechanism] = (alpha + 1, beta)
            else:
                self._mechanism_posteriors[mechanism] = (alpha, beta + 1)
            
            self._mechanism_outcomes[mechanism].append(outcome_value)
        
        # Update station posteriors
        for station in campaign["stations"]:
            station_format = station.get("station_format")
            if station_format:
                self._station_outcomes[station_format].append(outcome_value)
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal,
    ) -> Optional[List[LearningSignal]]:
        """Handle incoming learning signals from other components."""
        # Learn from other components' discoveries
        if signal.signal_type == LearningSignalType.PATTERN_EMERGED:
            # Incorporate new patterns into campaign strategy
            await self._incorporate_pattern(signal.payload)
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # Update mechanism beliefs
            mech = signal.payload.get("mechanism")
            effectiveness = signal.payload.get("effectiveness", 0.5)
            if mech:
                self._mechanism_outcomes[mech].append(effectiveness)
        
        return None
    
    async def _incorporate_pattern(self, pattern_data: Dict[str, Any]) -> None:
        """Incorporate discovered patterns into campaign strategy."""
        # Store pattern for future campaign optimization
        pass
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.PATTERN_EMERGED,
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.PRIOR_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[LearningContribution]:
        """Report orchestrator's contribution to a decision."""
        campaign = self._campaigns.get(decision_id)
        if not campaign:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="campaign_orchestration",
            contribution_value={
                "segments": len(campaign["segments"]),
                "mechanisms": campaign["mechanisms"],
                "stations": len(campaign["stations"]),
            },
            confidence=campaign["overall_confidence"],
            reasoning_summary="Campaign orchestration with multi-source intelligence",
            weight=0.3,  # Orchestrator has significant weight
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Report learning quality metrics."""
        # Compute recent accuracy
        recent_accuracy = 0.5
        if self._accuracy_history:
            recent = [a for t, a in self._accuracy_history if t > datetime.now(timezone.utc) - timedelta(hours=24)]
            if recent:
                recent_accuracy = sum(recent) / len(recent)
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._signals_emitted,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=recent_accuracy,
            attribution_coverage=1.0 if self._outcomes_processed > 0 else 0.0,
            last_learning_update=self._accuracy_history[-1][0] if self._accuracy_history else None,
            upstream_dependencies=["atoms", "graph_intelligence", "meta_learner"],
            downstream_consumers=["gradient_bridge", "thompson_sampler"],
            integration_health=1.0 if self._outcomes_processed > 0 else 0.5,
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject priors for campaign optimization."""
        # Incorporate user-specific priors
        if "mechanism_priors" in priors:
            for mech, prior in priors["mechanism_priors"].items():
                if isinstance(prior, dict) and "alpha" in prior and "beta" in prior:
                    self._mechanism_posteriors[mech] = (prior["alpha"], prior["beta"])
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No campaign outcomes processed")
        
        if self._accuracy_history:
            recent = [a for t, a in self._accuracy_history if t > datetime.now(timezone.utc) - timedelta(hours=1)]
            if recent and sum(recent) / len(recent) < 0.3:
                issues.append("Low recent campaign accuracy")
        
        return len(issues) == 0, issues
    
    def get_archetype_brand_effectiveness(self, brand: str) -> Dict[str, float]:
        """Get learned archetype effectiveness for a brand."""
        result = {}
        for archetype, (alpha, beta) in self._archetype_brand_posteriors[brand].items():
            result[archetype] = alpha / (alpha + beta)
        return result
    
    def get_mechanism_effectiveness(self) -> Dict[str, float]:
        """Get learned mechanism effectiveness."""
        result = {}
        for mechanism, (alpha, beta) in self._mechanism_posteriors.items():
            result[mechanism] = alpha / (alpha + beta)
        return result


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_orchestrator_learning: Optional[CampaignOrchestratorLearningIntegration] = None


def get_orchestrator_learning_integration() -> CampaignOrchestratorLearningIntegration:
    """Get the singleton orchestrator learning integration."""
    global _orchestrator_learning
    if _orchestrator_learning is None:
        _orchestrator_learning = CampaignOrchestratorLearningIntegration()
    return _orchestrator_learning
