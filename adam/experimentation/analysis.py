# =============================================================================
# ADAM Experiment Analysis
# Location: adam/experimentation/analysis.py
# =============================================================================

"""
EXPERIMENT ANALYSIS

Statistical analysis of experiment results.

Features:
- Frequentist significance testing
- Bayesian analysis
- Psychological validity checks
- Power analysis
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adam.experimentation.models import (
    Experiment,
    ExperimentVariant,
    OutcomeEvent,
    VariantResult,
    ExperimentResult,
)

logger = logging.getLogger(__name__)


class ExperimentAnalyzer:
    """
    Analyzer for experiment results.
    """
    
    # Z-scores for confidence levels
    Z_SCORES = {
        0.80: 1.28,
        0.85: 1.44,
        0.90: 1.65,
        0.95: 1.96,
        0.99: 2.58,
    }
    
    def __init__(self):
        self._outcome_store: Dict[str, List[OutcomeEvent]] = {}
    
    async def record_outcome(
        self,
        event: OutcomeEvent,
    ) -> None:
        """Record an outcome event."""
        
        key = f"{event.experiment_id}:{event.variant_id}"
        if key not in self._outcome_store:
            self._outcome_store[key] = []
        
        self._outcome_store[key].append(event)
    
    async def analyze_experiment(
        self,
        experiment: Experiment,
    ) -> ExperimentResult:
        """
        Perform full analysis of an experiment.
        """
        
        variant_results = []
        control_result = None
        
        # Analyze each variant
        for variant in experiment.variants:
            result = await self._analyze_variant(
                experiment, variant
            )
            variant_results.append(result)
            
            if variant.is_control:
                control_result = result
        
        # Compare variants to control
        if control_result:
            for result in variant_results:
                if not result.is_control:
                    result = self._compare_to_control(result, control_result)
        
        # Determine winner
        winner_id, winner_confidence = self._determine_winner(
            variant_results, experiment.confidence_level
        )
        
        # Check psychological validity
        validity_passed, validity_issues = self._check_psychological_validity(
            experiment, variant_results
        )
        
        # Generate recommendation
        recommendation, reason = self._generate_recommendation(
            experiment, variant_results, winner_id, validity_passed
        )
        
        return ExperimentResult(
            experiment_id=experiment.experiment_id,
            experiment_name=experiment.name,
            status=experiment.status.value,
            variant_results=variant_results,
            winning_variant_id=winner_id,
            winning_confidence=winner_confidence,
            psychological_validity_passed=validity_passed,
            validity_issues=validity_issues,
            recommendation=recommendation,
            recommendation_reason=reason,
        )
    
    async def _analyze_variant(
        self,
        experiment: Experiment,
        variant: ExperimentVariant,
    ) -> VariantResult:
        """Analyze a single variant."""
        
        key = f"{experiment.experiment_id}:{variant.variant_id}"
        events = self._outcome_store.get(key, [])
        
        # Count conversions
        conversions = sum(1 for e in events if e.event_type == "conversion")
        sample_size = variant.sample_size or max(1, len(events))
        
        # Calculate rate
        rate = conversions / sample_size if sample_size > 0 else 0.0
        
        # Standard error
        std_error = math.sqrt(rate * (1 - rate) / sample_size) if sample_size > 0 else 0.0
        
        # Confidence interval
        z = self.Z_SCORES.get(experiment.confidence_level, 1.96)
        ci_lower = max(0, rate - z * std_error)
        ci_upper = min(1, rate + z * std_error)
        
        return VariantResult(
            variant_id=variant.variant_id,
            variant_name=variant.name,
            is_control=variant.is_control,
            sample_size=sample_size,
            metric_value=rate,
            metric_std=std_error,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
        )
    
    def _compare_to_control(
        self,
        treatment: VariantResult,
        control: VariantResult,
    ) -> VariantResult:
        """Compare treatment to control."""
        
        # Lift
        if control.metric_value > 0:
            treatment.lift_vs_control = (
                (treatment.metric_value - control.metric_value) 
                / control.metric_value
            )
        else:
            treatment.lift_vs_control = 0.0
        
        # Two-proportion z-test
        p_pooled = (
            (treatment.metric_value * treatment.sample_size + 
             control.metric_value * control.sample_size) /
            (treatment.sample_size + control.sample_size)
        )
        
        if p_pooled > 0 and p_pooled < 1:
            se_pooled = math.sqrt(
                p_pooled * (1 - p_pooled) * 
                (1/treatment.sample_size + 1/control.sample_size)
            )
            
            if se_pooled > 0:
                z_stat = (treatment.metric_value - control.metric_value) / se_pooled
                
                # Two-tailed p-value (approximation using normal CDF)
                treatment.p_value = 2 * (1 - self._normal_cdf(abs(z_stat)))
                treatment.is_significant = treatment.p_value < 0.05
        
        return treatment
    
    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _determine_winner(
        self,
        results: List[VariantResult],
        confidence_level: float,
    ) -> Tuple[Optional[str], Optional[float]]:
        """Determine if there's a statistically significant winner."""
        
        # Find best performing variant
        best = max(results, key=lambda r: r.metric_value)
        control = next((r for r in results if r.is_control), None)
        
        if not control or best.is_control:
            return None, None
        
        # Check if best is significantly better than control
        if best.is_significant and best.p_value is not None:
            confidence = 1 - best.p_value
            if confidence >= confidence_level:
                return best.variant_id, confidence
        
        return None, None
    
    def _check_psychological_validity(
        self,
        experiment: Experiment,
        results: List[VariantResult],
    ) -> Tuple[bool, List[str]]:
        """Check psychological validity constraints."""
        
        issues = []
        
        if not experiment.requires_psychological_validity:
            return True, []
        
        constraints = experiment.validity_constraints
        
        # Check minimum effect size
        if "min_effect_size" in constraints:
            min_effect = constraints["min_effect_size"]
            for result in results:
                if result.lift_vs_control is not None:
                    if abs(result.lift_vs_control) < min_effect:
                        issues.append(
                            f"Variant {result.variant_id} effect size "
                            f"({result.lift_vs_control:.2%}) below minimum "
                            f"({min_effect:.2%})"
                        )
        
        # Check for psychological harm
        if "max_negative_effect" in constraints:
            max_neg = constraints["max_negative_effect"]
            for result in results:
                if result.lift_vs_control is not None:
                    if result.lift_vs_control < -max_neg:
                        issues.append(
                            f"Variant {result.variant_id} shows harmful "
                            f"negative effect ({result.lift_vs_control:.2%})"
                        )
        
        # Check sample representativeness
        if "min_sample_per_variant" in constraints:
            min_sample = constraints["min_sample_per_variant"]
            for result in results:
                if result.sample_size < min_sample:
                    issues.append(
                        f"Variant {result.variant_id} sample size "
                        f"({result.sample_size}) below minimum ({min_sample})"
                    )
        
        return len(issues) == 0, issues
    
    def _generate_recommendation(
        self,
        experiment: Experiment,
        results: List[VariantResult],
        winner_id: Optional[str],
        validity_passed: bool,
    ) -> Tuple[str, str]:
        """Generate recommendation for next steps."""
        
        total_sample = sum(r.sample_size for r in results)
        
        # Check if we have enough data
        if total_sample < experiment.minimum_sample_size:
            return "continue", f"Need more data ({total_sample}/{experiment.minimum_sample_size})"
        
        # Check validity
        if not validity_passed:
            return "review", "Psychological validity issues detected"
        
        # Check for winner
        if winner_id:
            winner = next((r for r in results if r.variant_id == winner_id), None)
            if winner:
                return "declare_winner", (
                    f"Variant '{winner.variant_name}' wins with "
                    f"{winner.lift_vs_control:.1%} lift (p={winner.p_value:.4f})"
                )
        
        # No clear winner yet
        return "continue", "No statistically significant winner yet"
    
    def calculate_required_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        confidence_level: float = 0.95,
        power: float = 0.80,
    ) -> int:
        """
        Calculate required sample size per variant.
        
        Args:
            baseline_rate: Expected conversion rate for control
            minimum_detectable_effect: Minimum relative lift to detect
            confidence_level: Required confidence (1 - alpha)
            power: Statistical power (1 - beta)
        
        Returns:
            Required sample size per variant
        """
        
        alpha = 1 - confidence_level
        z_alpha = self.Z_SCORES.get(confidence_level, 1.96)
        
        # Z-score for power
        z_beta = {0.80: 0.84, 0.85: 1.04, 0.90: 1.28}.get(power, 0.84)
        
        p1 = baseline_rate
        p2 = baseline_rate * (1 + minimum_detectable_effect)
        
        # Pooled proportion
        p_bar = (p1 + p2) / 2
        
        # Sample size formula
        numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) + 
                     z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p2 - p1) ** 2
        
        if denominator > 0:
            n = numerator / denominator
            return int(math.ceil(n))
        
        return 10000  # Default fallback
