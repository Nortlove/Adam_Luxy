# =============================================================================
# ADAM Behavioral Analytics: Hypothesis Engine
# Location: adam/behavioral_analytics/knowledge/hypothesis_engine.py
# =============================================================================

"""
HYPOTHESIS TESTING ENGINE

Generates, tests, and validates hypotheses about signal-outcome relationships.

Lifecycle:
1. GENERATE - Pattern observed, hypothesis formed
2. TEST - Collect observations, compute statistics
3. VALIDATE - Check significance thresholds
4. PROMOTE - Becomes system knowledge
5. REFINE - Continuously update with new data
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import math
import logging
import numpy as np
from collections import defaultdict

from adam.behavioral_analytics.models.knowledge import (
    BehavioralHypothesis,
    BehavioralKnowledge,
    HypothesisStatus,
    KnowledgeType,
    KnowledgeStatus,
    EffectType,
    SignalCategory,
    KnowledgeTier,
)
from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    BehavioralOutcome,
    OutcomeType,
)

logger = logging.getLogger(__name__)


class StatisticalTest:
    """Statistical testing utilities."""
    
    @staticmethod
    def pearson_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
        """
        Compute Pearson correlation coefficient and p-value.
        
        Returns (r, p_value)
        """
        n = len(x)
        if n < 3:
            return 0.0, 1.0
        
        x_arr = np.array(x)
        y_arr = np.array(y)
        
        # Compute correlation
        x_mean = np.mean(x_arr)
        y_mean = np.mean(y_arr)
        
        numerator = np.sum((x_arr - x_mean) * (y_arr - y_mean))
        denominator = np.sqrt(
            np.sum((x_arr - x_mean)**2) * np.sum((y_arr - y_mean)**2)
        )
        
        if denominator == 0:
            return 0.0, 1.0
        
        r = numerator / denominator
        
        # Compute t-statistic and p-value
        t = r * math.sqrt((n - 2) / (1 - r**2 + 1e-10))
        # Approximate p-value using normal distribution for large n
        p_value = 2 * (1 - StatisticalTest._normal_cdf(abs(t)))
        
        return r, p_value
    
    @staticmethod
    def cohens_d(group1: List[float], group2: List[float]) -> float:
        """Compute Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        if n1 < 2 or n2 < 2:
            return 0.0
        
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        # Pooled standard deviation
        pooled_std = math.sqrt(
            ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
        )
        
        if pooled_std == 0:
            return 0.0
        
        return (mean1 - mean2) / pooled_std
    
    @staticmethod
    def proportion_test(
        successes1: int, total1: int,
        successes2: int, total2: int
    ) -> Tuple[float, float]:
        """
        Two-proportion z-test.
        
        Returns (z_score, p_value)
        """
        if total1 == 0 or total2 == 0:
            return 0.0, 1.0
        
        p1 = successes1 / total1
        p2 = successes2 / total2
        p_pooled = (successes1 + successes2) / (total1 + total2)
        
        if p_pooled == 0 or p_pooled == 1:
            return 0.0, 1.0
        
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/total1 + 1/total2))
        
        if se == 0:
            return 0.0, 1.0
        
        z = (p1 - p2) / se
        p_value = 2 * (1 - StatisticalTest._normal_cdf(abs(z)))
        
        return z, p_value
    
    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Cumulative distribution function for standard normal."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    @staticmethod
    def confidence_interval_95(
        estimate: float,
        std_error: float
    ) -> Tuple[float, float]:
        """Compute 95% confidence interval."""
        z = 1.96  # 95% CI
        return (estimate - z * std_error, estimate + z * std_error)


class HypothesisEngine:
    """
    Generates and tests behavioral hypotheses.
    
    Workflow:
    1. Observe patterns in session data
    2. Generate hypotheses about signal-outcome relationships
    3. Collect observations to test hypotheses
    4. Compute statistical significance
    5. Promote validated hypotheses to knowledge
    """
    
    def __init__(self, graph=None):
        self._graph = graph
        self._hypotheses: Dict[str, BehavioralHypothesis] = {}
        self._observations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Cross-validation
        self._cv_folds = 5
        
        # Thresholds
        self._min_observations = 50
        self._significance_threshold = 0.05
        self._min_effect_size = 0.1
    
    async def generate_hypothesis(
        self,
        signal_pattern: str,
        signal_features: List[str],
        predicted_outcome: str,
        predicted_direction: str,
        description: str
    ) -> BehavioralHypothesis:
        """
        Generate a new hypothesis for testing.
        """
        hypothesis = BehavioralHypothesis(
            status=HypothesisStatus.GENERATED,
            signal_pattern=signal_pattern,
            signal_features=signal_features,
            predicted_outcome=predicted_outcome,
            predicted_direction=predicted_direction,
            hypothesis_description=description,
            min_observations_required=self._min_observations,
            significance_threshold=self._significance_threshold,
            min_effect_size=self._min_effect_size,
        )
        
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        
        if self._graph:
            await self._graph.store_hypothesis(hypothesis)
        
        logger.info(
            f"Generated hypothesis {hypothesis.hypothesis_id}: "
            f"{signal_pattern} -> {predicted_outcome} ({predicted_direction})"
        )
        
        return hypothesis
    
    async def record_observation(
        self,
        hypothesis_id: str,
        signal_values: Dict[str, float],
        outcome_value: float,
        positive_outcome: bool
    ) -> Dict[str, Any]:
        """
        Record an observation for a hypothesis.
        
        Updates statistics and checks for promotion eligibility.
        """
        if hypothesis_id not in self._hypotheses:
            logger.warning(f"Unknown hypothesis: {hypothesis_id}")
            return {"status": "unknown"}
        
        hypothesis = self._hypotheses[hypothesis_id]
        
        # Store observation
        observation = {
            "signal_values": signal_values,
            "outcome_value": outcome_value,
            "positive_outcome": positive_outcome,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._observations[hypothesis_id].append(observation)
        
        # Update counts
        hypothesis.observations += 1
        if positive_outcome:
            hypothesis.positive_outcomes += 1
        else:
            hypothesis.negative_outcomes += 1
        hypothesis.last_observation = datetime.utcnow()
        
        # Update status
        if hypothesis.status == HypothesisStatus.GENERATED:
            hypothesis.status = HypothesisStatus.TESTING
        
        # Recompute statistics if enough observations
        result = {"status": "recorded", "observations": hypothesis.observations}
        
        if hypothesis.observations >= 10:
            stats = await self._compute_statistics(hypothesis_id)
            hypothesis.observed_effect_size = stats.get("effect_size")
            hypothesis.p_value = stats.get("p_value")
            hypothesis.confidence_interval_lower = stats.get("ci_lower")
            hypothesis.confidence_interval_upper = stats.get("ci_upper")
            result["statistics"] = stats
        
        # Check for validation
        if hypothesis.observations >= self._min_observations:
            validation = await self._validate_hypothesis(hypothesis_id)
            result["validation"] = validation
        
        # Update graph
        if self._graph:
            await self._graph.update_hypothesis_observation(
                hypothesis_id,
                positive_outcome,
                hypothesis.observed_effect_size,
                hypothesis.p_value
            )
        
        return result
    
    async def _compute_statistics(
        self,
        hypothesis_id: str
    ) -> Dict[str, Any]:
        """Compute statistics for a hypothesis."""
        observations = self._observations[hypothesis_id]
        hypothesis = self._hypotheses[hypothesis_id]
        
        if len(observations) < 3:
            return {}
        
        # Extract signal and outcome values
        signal_values = []
        outcome_values = []
        positive_outcomes = []
        negative_outcomes = []
        
        for obs in observations:
            # Use first signal feature for correlation
            if hypothesis.signal_features:
                feature = hypothesis.signal_features[0]
                if feature in obs["signal_values"]:
                    signal_values.append(obs["signal_values"][feature])
                    outcome_values.append(obs["outcome_value"])
            
            if obs["positive_outcome"]:
                positive_outcomes.append(obs["outcome_value"])
            else:
                negative_outcomes.append(obs["outcome_value"])
        
        stats = {}
        
        # Correlation analysis
        if len(signal_values) >= 3:
            r, p_value = StatisticalTest.pearson_correlation(
                signal_values, outcome_values
            )
            stats["correlation"] = r
            stats["p_value"] = p_value
            stats["effect_size"] = abs(r)
            stats["effect_type"] = "correlation"
            
            # Confidence interval
            n = len(signal_values)
            se = 1 / math.sqrt(n - 3) if n > 3 else 1.0
            ci_lower, ci_upper = StatisticalTest.confidence_interval_95(r, se)
            stats["ci_lower"] = ci_lower
            stats["ci_upper"] = ci_upper
        
        # Group comparison
        if len(positive_outcomes) >= 3 and len(negative_outcomes) >= 3:
            d = StatisticalTest.cohens_d(positive_outcomes, negative_outcomes)
            stats["cohens_d"] = d
            if "effect_size" not in stats:
                stats["effect_size"] = abs(d)
                stats["effect_type"] = "cohens_d"
        
        # Proportion test
        if hypothesis.observations > 0:
            success_rate = hypothesis.positive_outcomes / hypothesis.observations
            stats["success_rate"] = success_rate
        
        return stats
    
    async def _validate_hypothesis(
        self,
        hypothesis_id: str
    ) -> Dict[str, Any]:
        """
        Validate a hypothesis for promotion.
        
        Checks:
        1. Minimum observations met
        2. Statistical significance (p < 0.05)
        3. Minimum effect size (|r| or |d| > 0.1)
        4. Cross-validation (majority of folds)
        """
        hypothesis = self._hypotheses[hypothesis_id]
        observations = self._observations[hypothesis_id]
        
        validation = {
            "hypothesis_id": hypothesis_id,
            "observations": hypothesis.observations,
            "checks": {},
            "passed": False,
        }
        
        # Check 1: Minimum observations
        validation["checks"]["min_observations"] = {
            "threshold": self._min_observations,
            "actual": hypothesis.observations,
            "passed": hypothesis.observations >= self._min_observations
        }
        
        # Check 2: Statistical significance
        p_value = hypothesis.p_value or 1.0
        validation["checks"]["significance"] = {
            "threshold": self._significance_threshold,
            "actual": p_value,
            "passed": p_value < self._significance_threshold
        }
        
        # Check 3: Effect size
        effect_size = hypothesis.observed_effect_size or 0.0
        validation["checks"]["effect_size"] = {
            "threshold": self._min_effect_size,
            "actual": effect_size,
            "passed": abs(effect_size) >= self._min_effect_size
        }
        
        # Check 4: Cross-validation
        cv_passed = await self._cross_validate(hypothesis_id)
        hypothesis.cv_folds_passed = cv_passed
        validation["checks"]["cross_validation"] = {
            "threshold": 3,
            "actual": cv_passed,
            "passed": cv_passed >= 3
        }
        
        # Overall validation
        all_passed = all(
            check["passed"] for check in validation["checks"].values()
        )
        validation["passed"] = all_passed
        
        if all_passed:
            hypothesis.status = HypothesisStatus.VALIDATED
            hypothesis.validated_at = datetime.utcnow()
            logger.info(f"Hypothesis {hypothesis_id} VALIDATED")
        elif hypothesis.observations >= self._min_observations * 2:
            # Rejected after sufficient observations
            if not validation["checks"]["significance"]["passed"]:
                hypothesis.status = HypothesisStatus.REJECTED
                logger.info(f"Hypothesis {hypothesis_id} REJECTED (not significant)")
        
        return validation
    
    async def _cross_validate(self, hypothesis_id: str) -> int:
        """
        Perform k-fold cross-validation.
        
        Returns number of folds where effect held.
        """
        observations = self._observations[hypothesis_id]
        
        if len(observations) < self._cv_folds * 5:
            return 0
        
        folds_passed = 0
        fold_size = len(observations) // self._cv_folds
        
        for fold in range(self._cv_folds):
            # Split data
            start_idx = fold * fold_size
            end_idx = start_idx + fold_size
            
            test_data = observations[start_idx:end_idx]
            train_data = observations[:start_idx] + observations[end_idx:]
            
            # Compute effect in test fold
            if len(test_data) >= 3:
                positive = [o["outcome_value"] for o in test_data if o["positive_outcome"]]
                negative = [o["outcome_value"] for o in test_data if not o["positive_outcome"]]
                
                if len(positive) >= 2 and len(negative) >= 2:
                    d = StatisticalTest.cohens_d(positive, negative)
                    if abs(d) >= self._min_effect_size * 0.8:  # Allow some slack
                        folds_passed += 1
        
        return folds_passed
    
    async def promote_hypothesis(
        self,
        hypothesis_id: str
    ) -> Optional[BehavioralKnowledge]:
        """
        Promote a validated hypothesis to system knowledge.
        """
        if hypothesis_id not in self._hypotheses:
            return None
        
        hypothesis = self._hypotheses[hypothesis_id]
        
        if hypothesis.status != HypothesisStatus.VALIDATED:
            logger.warning(
                f"Cannot promote non-validated hypothesis {hypothesis_id}"
            )
            return None
        
        # Create knowledge from hypothesis
        knowledge = BehavioralKnowledge(
            knowledge_type=KnowledgeType.SYSTEM_DISCOVERED,
            status=KnowledgeStatus.ACTIVE,
            signal_name=hypothesis.signal_pattern,
            signal_category=SignalCategory.IMPLICIT,
            signal_description=f"System-discovered: {hypothesis.hypothesis_description}",
            feature_name=hypothesis.signal_features[0] if hypothesis.signal_features else "unknown",
            feature_computation=f"hypothesis_{hypothesis_id}",
            maps_to_construct=hypothesis.predicted_outcome,
            mapping_direction=hypothesis.predicted_direction,
            mapping_description=hypothesis.hypothesis_description,
            effect_size=hypothesis.observed_effect_size or 0.0,
            effect_type=hypothesis.observed_effect_type,
            confidence_interval_lower=hypothesis.confidence_interval_lower,
            confidence_interval_upper=hypothesis.confidence_interval_upper,
            p_value=hypothesis.p_value,
            study_count=1,
            total_sample_size=hypothesis.observations,
            tier=KnowledgeTier.TIER_3,  # System-discovered starts at Tier 3
            implementation_notes=f"Discovered from {hypothesis.observations} observations. Promoted at {datetime.utcnow().isoformat()}",
            min_observations=10,
        )
        
        # Update hypothesis
        hypothesis.status = HypothesisStatus.PROMOTED
        hypothesis.promoted_at = datetime.utcnow()
        hypothesis.promoted_knowledge_id = knowledge.knowledge_id
        
        # Store in graph
        if self._graph:
            await self._graph.store_knowledge(knowledge)
            await self._graph.promote_hypothesis(
                hypothesis_id,
                knowledge.knowledge_id
            )
        
        logger.info(
            f"Promoted hypothesis {hypothesis_id} to knowledge {knowledge.knowledge_id}"
        )
        
        return knowledge
    
    async def auto_generate_hypotheses(
        self,
        session: BehavioralSession
    ) -> List[BehavioralHypothesis]:
        """
        Auto-generate hypotheses from session patterns.
        
        Looks for potential signal-outcome relationships to test.
        """
        hypotheses = []
        
        # High pressure + cart → abandonment hypothesis
        if session.touches and session.cart_events:
            avg_pressure = sum(t.pressure for t in session.touches) / len(session.touches)
            if avg_pressure > 0.7:
                hyp = await self.generate_hypothesis(
                    signal_pattern="high_touch_pressure_during_cart",
                    signal_features=["pressure_mean", "pressure_std"],
                    predicted_outcome="cart_abandonment",
                    predicted_direction="positive",
                    description="High touch pressure during cart activity predicts abandonment"
                )
                hypotheses.append(hyp)
        
        # Hesitation + CTA → conversion hypothesis
        if session.hesitations and session.features.get("cta_interactions", 0) > 0:
            hyp = await self.generate_hypothesis(
                signal_pattern="hesitation_before_cta",
                signal_features=["pre_cta_hesitation_ratio", "hesitation_count"],
                predicted_outcome="conversion",
                predicted_direction="negative",
                description="Hesitation before CTAs predicts lower conversion"
            )
            hypotheses.append(hyp)
        
        # Fast swipes + browsing → purchase intent hypothesis
        if session.swipes:
            avg_velocity = sum(s.velocity for s in session.swipes) / len(session.swipes)
            if avg_velocity > 1000:  # Fast swiping
                hyp = await self.generate_hypothesis(
                    signal_pattern="high_velocity_swipes",
                    signal_features=["swipe_velocity_mean", "swipe_count"],
                    predicted_outcome="purchase_intent",
                    predicted_direction="negative",
                    description="High velocity swipes indicate browsing rather than buying intent"
                )
                hypotheses.append(hyp)
        
        return hypotheses
    
    def get_hypothesis(self, hypothesis_id: str) -> Optional[BehavioralHypothesis]:
        """Get a hypothesis by ID."""
        return self._hypotheses.get(hypothesis_id)
    
    def get_hypotheses_by_status(
        self,
        status: HypothesisStatus
    ) -> List[BehavioralHypothesis]:
        """Get all hypotheses with a given status."""
        return [
            h for h in self._hypotheses.values()
            if h.status == status
        ]
    
    def get_promotable_hypotheses(self) -> List[BehavioralHypothesis]:
        """Get all hypotheses that can be promoted."""
        return [
            h for h in self._hypotheses.values()
            if h.status == HypothesisStatus.VALIDATED and h.is_promotable
        ]


# Singleton
_engine: Optional[HypothesisEngine] = None


def get_hypothesis_engine(graph=None) -> HypothesisEngine:
    """Get singleton hypothesis engine."""
    global _engine
    if _engine is None:
        _engine = HypothesisEngine(graph)
    return _engine
