# =============================================================================
# Demo Mode Learning Integration
# Location: adam/demo/demo_learning.py
# =============================================================================

"""
Integrates the Theory-Based Outcome Simulator with Thompson Sampling
to enable visible learning in demo mode.

This allows the demo to show:
1. Mechanism selection using Thompson Sampling
2. Simulated outcome based on psychological research
3. Posterior update demonstrating learning
4. Improved recommendations over time

Usage:
    learner = DemoLearner()
    
    # Run a learning cycle
    result = await learner.learn_from_simulated_campaign(
        archetype="achievement_driven",
        mechanism="regulatory_focus",
    )
    
    # See the learning effect
    print(result.before_posterior)  # e.g., 0.60
    print(result.simulated_success)  # True/False
    print(result.after_posterior)   # e.g., 0.62 (if success)
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class LearningCycleResult:
    """Result of a single learning cycle."""
    archetype: str
    mechanism: str
    
    # Before state
    before_posterior_mean: float
    before_posterior_alpha: float
    before_posterior_beta: float
    before_uncertainty: float
    
    # Simulation
    simulated_outcome: bool
    outcome_probability: float
    simulation_reasoning: str
    
    # After state
    after_posterior_mean: float
    after_posterior_alpha: float
    after_posterior_beta: float
    after_uncertainty: float
    
    # Learning delta
    mean_change: float
    uncertainty_change: float
    
    # Explanation for demo
    explanation: str


class DemoLearner:
    """
    Manages learning cycles in demo mode using simulated outcomes.
    
    This enables the demo to visibly show the system learning and improving,
    even without real ad serving data.
    """
    
    def __init__(self):
        self._initialized = False
        self._sampler = None
        self._simulator = None
        self._learning_history: List[LearningCycleResult] = []
    
    def _ensure_initialized(self):
        """Lazy initialization of components."""
        if not self._initialized:
            try:
                from adam.cold_start.thompson.sampler import get_thompson_sampler
                from adam.intelligence.outcome_simulation.theory_based_simulator import (
                    get_outcome_simulator,
                )
                
                self._sampler = get_thompson_sampler()
                self._simulator = get_outcome_simulator()
                self._initialized = True
            except ImportError as e:
                logger.warning(f"Could not initialize demo learner: {e}")
    
    async def learn_from_simulated_campaign(
        self,
        archetype: str,
        mechanism: str,
        construct_profile: Optional[Dict[str, float]] = None,
    ) -> LearningCycleResult:
        """
        Run a single learning cycle with simulated outcome.
        
        Args:
            archetype: Customer archetype (e.g., 'achievement_driven')
            mechanism: Selected mechanism (e.g., 'regulatory_focus')
            construct_profile: Optional construct scores
            
        Returns:
            LearningCycleResult with before/after posteriors and explanation
        """
        self._ensure_initialized()
        
        if not self._sampler or not self._simulator:
            raise RuntimeError("Demo learner not properly initialized")
        
        from adam.cold_start.models.enums import CognitiveMechanism, ArchetypeID
        from adam.intelligence.outcome_simulation.theory_based_simulator import (
            SimulationContext,
            OutcomeType,
        )
        
        # Convert to enums
        try:
            archetype_lower = archetype.lower().replace("-", "_").replace(" ", "_")
            mechanism_lower = mechanism.lower().replace("-", "_").replace(" ", "_")
            
            archetype_enum = ArchetypeID(archetype_lower)
            mechanism_enum = CognitiveMechanism(mechanism_lower)
        except ValueError as e:
            logger.warning(f"Invalid archetype/mechanism: {e}")
            # Use defaults
            archetype_enum = None
            mechanism_enum = None
        
        # Get BEFORE state
        before_posterior = self._sampler.get_posterior(mechanism_enum, archetype_enum)
        before_mean = before_posterior.mean
        before_alpha = before_posterior.alpha
        before_beta = before_posterior.beta
        before_uncertainty = before_posterior.uncertainty
        
        # Simulate outcome
        context = SimulationContext(
            archetype_id=archetype,
            mechanism_id=mechanism,
            construct_profile=construct_profile or {},
        )
        outcome = self._simulator.simulate_outcome(context, OutcomeType.ENGAGEMENT)
        
        # Update posterior with simulated outcome
        self._sampler.update_posterior(
            mechanism=mechanism_enum,
            success=outcome.success,
            archetype=archetype_enum,
        )
        
        # Get AFTER state
        after_posterior = self._sampler.get_posterior(mechanism_enum, archetype_enum)
        after_mean = after_posterior.mean
        after_alpha = after_posterior.alpha
        after_beta = after_posterior.beta
        after_uncertainty = after_posterior.uncertainty
        
        # Calculate deltas
        mean_change = after_mean - before_mean
        uncertainty_change = after_uncertainty - before_uncertainty
        
        # Build explanation
        if outcome.success:
            if mean_change > 0:
                explanation = (
                    f"The simulated campaign SUCCEEDED. The system learned that "
                    f"{mechanism.replace('_', ' ')} works well for {archetype.replace('_', ' ')} "
                    f"customers. Expected effectiveness increased from {before_mean:.1%} to {after_mean:.1%}."
                )
            else:
                explanation = (
                    f"The simulated campaign SUCCEEDED, but effectiveness was already high. "
                    f"The system's confidence increased (uncertainty: {before_uncertainty:.3f} → {after_uncertainty:.3f})."
                )
        else:
            if mean_change < 0:
                explanation = (
                    f"The simulated campaign did NOT convert. The system learned that "
                    f"{mechanism.replace('_', ' ')} may be less effective for {archetype.replace('_', ' ')} "
                    f"customers. Expected effectiveness decreased from {before_mean:.1%} to {after_mean:.1%}."
                )
            else:
                explanation = (
                    f"The simulated campaign did NOT convert, but the system maintains its belief "
                    f"(this can happen due to noise). More data needed."
                )
        
        result = LearningCycleResult(
            archetype=archetype,
            mechanism=mechanism,
            before_posterior_mean=before_mean,
            before_posterior_alpha=before_alpha,
            before_posterior_beta=before_beta,
            before_uncertainty=before_uncertainty,
            simulated_outcome=outcome.success,
            outcome_probability=outcome.probability,
            simulation_reasoning=outcome.explanation,
            after_posterior_mean=after_mean,
            after_posterior_alpha=after_alpha,
            after_posterior_beta=after_beta,
            after_uncertainty=after_uncertainty,
            mean_change=mean_change,
            uncertainty_change=uncertainty_change,
            explanation=explanation,
        )
        
        self._learning_history.append(result)
        return result
    
    async def run_learning_demo(
        self,
        archetype: str,
        n_cycles: int = 10,
    ) -> Dict[str, any]:
        """
        Run multiple learning cycles to demonstrate learning over time.
        
        This shows the system improving its recommendations through experience.
        
        Args:
            archetype: Customer archetype to learn about
            n_cycles: Number of learning cycles
            
        Returns:
            Summary of learning progression
        """
        self._ensure_initialized()
        
        if not self._sampler:
            raise RuntimeError("Demo learner not properly initialized")
        
        from adam.cold_start.models.enums import CognitiveMechanism
        
        results = []
        
        # Run learning cycles
        for i in range(n_cycles):
            # Sample mechanism using Thompson Sampling
            mechanism, sample_value, reason = self._sampler.sample_mechanism(
                archetype=None,  # Will use archetype-specific if available
                force_exploration=(i < 3),  # Force exploration early
            )
            
            # Learn from simulated outcome
            result = await self.learn_from_simulated_campaign(
                archetype=archetype,
                mechanism=mechanism.value,
            )
            results.append(result)
        
        # Build summary
        successes = sum(1 for r in results if r.simulated_outcome)
        
        # Get final mechanism ranking
        ranking = self._sampler.get_mechanism_ranking()
        
        return {
            "archetype": archetype,
            "cycles_run": n_cycles,
            "successes": successes,
            "success_rate": successes / n_cycles,
            "final_mechanism_ranking": [
                {
                    "mechanism": mech.value,
                    "expected_effectiveness": mean,
                    "uncertainty": unc,
                }
                for mech, mean, unc in ranking[:5]
            ],
            "learning_progression": [
                {
                    "cycle": i + 1,
                    "mechanism": r.mechanism,
                    "success": r.simulated_outcome,
                    "posterior_mean": r.after_posterior_mean,
                    "explanation": r.explanation,
                }
                for i, r in enumerate(results)
            ],
            "total_updates": self._sampler.total_updates,
        }
    
    def get_learning_stats(self) -> Dict[str, any]:
        """Get overall learning statistics."""
        self._ensure_initialized()
        
        if not self._sampler:
            return {"error": "Learner not initialized"}
        
        return {
            "total_samples": self._sampler.total_samples,
            "total_updates": self._sampler.total_updates,
            "learning_history_length": len(self._learning_history),
            "posteriors": {
                mech.value: {
                    "mean": post.mean,
                    "alpha": post.alpha,
                    "beta": post.beta,
                    "uncertainty": post.uncertainty,
                }
                for mech, post in self._sampler.population_posteriors.items()
            },
        }


# Singleton instance
_demo_learner: Optional[DemoLearner] = None


def get_demo_learner() -> DemoLearner:
    """Get singleton demo learner."""
    global _demo_learner
    if _demo_learner is None:
        _demo_learner = DemoLearner()
    return _demo_learner


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("DEMO LEARNING TEST")
        print("=" * 60)
        
        learner = get_demo_learner()
        
        # Run a learning demo
        print("\nRunning 10 learning cycles for 'achievement_driven' archetype...")
        
        summary = await learner.run_learning_demo(
            archetype="achievement_driven",
            n_cycles=10,
        )
        
        print(f"\nResults:")
        print(f"  Success rate: {summary['success_rate']:.0%}")
        print(f"  Total updates: {summary['total_updates']}")
        
        print(f"\nFinal mechanism ranking:")
        for mech in summary['final_mechanism_ranking'][:3]:
            print(f"  {mech['mechanism']}: {mech['expected_effectiveness']:.1%}")
        
        print(f"\nLearning progression (last 3):")
        for cycle in summary['learning_progression'][-3:]:
            status = "✓" if cycle['success'] else "✗"
            print(f"  Cycle {cycle['cycle']}: {status} {cycle['mechanism']} → {cycle['posterior_mean']:.1%}")
    
    asyncio.run(test())
