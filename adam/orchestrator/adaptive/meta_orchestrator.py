# =============================================================================
# ADAM Meta-Orchestrator
# Location: adam/orchestrator/adaptive/meta_orchestrator.py
# =============================================================================

"""
META-ORCHESTRATOR — The Orchestrator of Orchestrators

A novel LangGraph extension that selects and configures the optimal
workflow graph for each request based on learned patterns and request
characteristics.

Innovation: Instead of a single fixed workflow, the meta-orchestrator
maintains a PORTFOLIO of workflow strategies and uses Thompson Sampling
to select the best one for each request context. Over time, it learns
which workflow configurations work best for which contexts.

Workflow strategies:
1. FAST PATH: Minimal atoms, rule-based only, <50ms latency
   → For returning users, well-known archetypes, commodity products

2. DEEP REASONING: Full 30-atom DAG with coherence optimization
   → For high-value decisions, new archetypes, complex products

3. EXPLORATORY: Extended graph with additional intelligence sources
   → For novel contexts, learning mode, A/B testing

4. HYBRID: ML + rule-based extraction with cross-validation
   → When ML model is available and domain is well-covered

5. ADAPTIVE: Graph rewriter enabled, runtime edges active
   → For uncertain contexts where the optimal path isn't clear

The meta-orchestrator also manages:
- Graph compilation caching (compiled LangGraph instances)
- Cross-request learning (which strategies work for which contexts)
- Resource budgeting (time/cost constraints per request)
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


class WorkflowStrategy(str, Enum):
    """Available workflow strategies."""
    FAST = "fast"
    DEEP_REASONING = "deep_reasoning"
    EXPLORATORY = "exploratory"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


@dataclass
class StrategyConfig:
    """Configuration for a workflow strategy."""
    strategy: WorkflowStrategy
    description: str
    
    # Which atoms to include
    atom_ids: List[str] = field(default_factory=list)
    
    # Graph configuration
    enable_rewriter: bool = False
    enable_runtime_edges: bool = False
    enable_ml_extraction: bool = False
    enable_coherence_check: bool = False
    
    # Resource limits
    max_latency_ms: int = 5000
    max_atoms: int = 30
    
    # Learning parameters
    thompson_alpha: float = 1.0  # Beta distribution α
    thompson_beta: float = 1.0   # Beta distribution β


# =============================================================================
# STRATEGY DEFINITIONS
# =============================================================================

STRATEGY_CONFIGS = {
    WorkflowStrategy.FAST: StrategyConfig(
        strategy=WorkflowStrategy.FAST,
        description="Minimal atoms, rule-based only, <50ms",
        atom_ids=[
            "atom_user_state",
            "atom_regulatory_focus",
            "atom_mechanism_activation",
            "atom_message_framing",
            "atom_ad_selection",
        ],
        max_latency_ms=100,
        max_atoms=5,
    ),
    WorkflowStrategy.DEEP_REASONING: StrategyConfig(
        strategy=WorkflowStrategy.DEEP_REASONING,
        description="Full 30-atom DAG with coherence optimization",
        atom_ids=[],  # All atoms (empty = use full DAG)
        enable_coherence_check=True,
        max_latency_ms=5000,
        max_atoms=30,
    ),
    WorkflowStrategy.EXPLORATORY: StrategyConfig(
        strategy=WorkflowStrategy.EXPLORATORY,
        description="Extended graph with additional intelligence sources",
        atom_ids=[],  # All atoms
        enable_coherence_check=True,
        enable_runtime_edges=True,
        max_latency_ms=8000,
        max_atoms=30,
    ),
    WorkflowStrategy.HYBRID: StrategyConfig(
        strategy=WorkflowStrategy.HYBRID,
        description="ML + rule-based extraction with cross-validation",
        atom_ids=[],  # All atoms
        enable_ml_extraction=True,
        enable_coherence_check=True,
        max_latency_ms=5000,
        max_atoms=30,
    ),
    WorkflowStrategy.ADAPTIVE: StrategyConfig(
        strategy=WorkflowStrategy.ADAPTIVE,
        description="Graph rewriter enabled, runtime edges active",
        atom_ids=[],  # Determined by rewriter
        enable_rewriter=True,
        enable_runtime_edges=True,
        enable_coherence_check=True,
        max_latency_ms=6000,
        max_atoms=30,
    ),
}


@dataclass
class ContextSignature:
    """A fingerprint of the request context for strategy selection."""
    archetype_known: bool = False
    brand_awareness: float = 0.5
    product_complexity: float = 0.5
    decision_value: float = 0.5     # How important is getting this right
    user_history_depth: int = 0      # How many prior interactions
    ml_model_available: bool = False
    latency_budget_ms: int = 5000
    
    def to_bucket(self) -> str:
        """Convert to a discrete bucket for Thompson Sampling."""
        parts = []
        parts.append("known" if self.archetype_known else "unknown")
        parts.append("hi_brand" if self.brand_awareness > 0.6 else "lo_brand")
        parts.append("complex" if self.product_complexity > 0.6 else "simple")
        parts.append("hi_val" if self.decision_value > 0.6 else "lo_val")
        parts.append("returning" if self.user_history_depth > 3 else "new")
        return "_".join(parts)


# =============================================================================
# META-ORCHESTRATOR
# =============================================================================

class MetaOrchestrator:
    """
    Selects the optimal workflow strategy for each request using
    Thompson Sampling over strategy-context pairs.
    """
    
    def __init__(
        self,
        strategies: Optional[Dict[WorkflowStrategy, StrategyConfig]] = None,
        exploration_rate: float = 0.1,
    ):
        self.strategies = strategies or dict(STRATEGY_CONFIGS)
        self.exploration_rate = exploration_rate
        
        # Thompson Sampling state: (context_bucket, strategy) → (α, β)
        self._posteriors: Dict[Tuple[str, WorkflowStrategy], Tuple[float, float]] = defaultdict(
            lambda: (1.0, 1.0)
        )
        
        # Execution history
        self._history: List[Dict[str, Any]] = []
        
        # Cache of compiled graphs per strategy
        self._compiled_graphs: Dict[WorkflowStrategy, Any] = {}
    
    def select_strategy(
        self,
        context: ContextSignature,
    ) -> Tuple[WorkflowStrategy, StrategyConfig]:
        """
        Select the best workflow strategy for this context using Thompson Sampling.
        
        Returns: (selected_strategy, strategy_config)
        """
        bucket = context.to_bucket()
        
        # Hard constraints
        eligible = list(self.strategies.keys())
        
        if context.latency_budget_ms < 200:
            eligible = [WorkflowStrategy.FAST]
        elif not context.ml_model_available:
            eligible = [s for s in eligible if s != WorkflowStrategy.HYBRID]
        
        if not eligible:
            eligible = [WorkflowStrategy.FAST]
        
        # Thompson Sampling: draw from each strategy's posterior
        best_strategy = None
        best_sample = -1.0
        
        for strategy in eligible:
            alpha, beta = self._posteriors[(bucket, strategy)]
            sample = np.random.beta(alpha, beta)
            
            if sample > best_sample:
                best_sample = sample
                best_strategy = strategy
        
        # Forced exploration — dynamically adjusted by corpus confidence.
        # High corpus confidence → less exploration needed (we know more).
        # Low/no corpus confidence → standard exploration rate.
        effective_exploration_rate = self.exploration_rate
        corpus_confidence = self._get_corpus_confidence(context)
        if corpus_confidence > 0:
            # Scale down exploration: at 100% corpus confidence, explore at 25% of base rate
            effective_exploration_rate = self.exploration_rate * (1.0 - 0.75 * corpus_confidence)
        
        if np.random.random() < effective_exploration_rate:
            best_strategy = np.random.choice(eligible)
        
        config = self.strategies[best_strategy]
        
        logger.info(
            f"Meta-orchestrator selected: {best_strategy.value} "
            f"(bucket={bucket}, sample={best_sample:.3f}, "
            f"explore_rate={effective_exploration_rate:.3f})"
        )
        
        return best_strategy, config
    
    def _get_corpus_confidence(self, context: ContextSignature) -> float:
        """
        Get corpus prior confidence for the current context.
        
        Higher confidence means the corpus has strong empirical data
        for this type of decision, reducing the need for exploration.
        """
        try:
            from adam.fusion.prior_extraction import get_prior_extraction_service
            prior_service = get_prior_extraction_service()
            
            # Use a generic query — we just need the confidence level
            prior = prior_service.extract_prior(category="")
            if prior:
                return prior.confidence
        except ImportError:
            pass
        except Exception:
            pass
        return 0.0
    
    def build_execution_plan(
        self,
        strategy: WorkflowStrategy,
        config: StrategyConfig,
        context: ContextSignature,
    ) -> Dict[str, Any]:
        """
        Build an execution plan based on the selected strategy.
        
        Returns a plan dict that the DAG executor can use.
        """
        plan = {
            "strategy": strategy.value,
            "config": {
                "enable_rewriter": config.enable_rewriter,
                "enable_runtime_edges": config.enable_runtime_edges,
                "enable_ml_extraction": config.enable_ml_extraction,
                "enable_coherence_check": config.enable_coherence_check,
                "max_latency_ms": min(config.max_latency_ms, context.latency_budget_ms),
                "max_atoms": config.max_atoms,
            },
            "atom_filter": config.atom_ids if config.atom_ids else None,
            "context_bucket": context.to_bucket(),
        }
        
        return plan
    
    def record_outcome(
        self,
        strategy: WorkflowStrategy,
        context: ContextSignature,
        success: bool,
        latency_ms: float = 0.0,
        quality_score: float = 0.5,
        alignment_confidence: float = 0.0,
    ) -> None:
        """
        Record the outcome of a strategy execution for learning.
        
        Updates the Thompson Sampling posteriors.
        
        Args:
            alignment_confidence: Confidence from the 7-matrix alignment system.
                When > 0, boosts learning signal for high-alignment predictions
                and dampens it for low-alignment misses (alignment confidence
                calibration for Meta-Learner).
        """
        bucket = context.to_bucket()
        key = (bucket, strategy)
        
        alpha, beta = self._posteriors[key]
        
        # Alignment confidence calibration:
        # When alignment confidence is high AND outcome matches prediction,
        # give a stronger learning signal (the system predicted well).
        # When alignment confidence is high AND outcome contradicts,
        # give a weaker signal (alignment matrices may need updating).
        alignment_bonus = 0.0
        if alignment_confidence > 0.3:
            if success:
                # High alignment + success = alignment matrices are working
                alignment_bonus = alignment_confidence * 0.3
            else:
                # High alignment + failure = alignment matrices may be wrong
                # Dampen the negative signal slightly; the error is in alignment, not strategy
                alignment_bonus = -alignment_confidence * 0.1

        if success:
            alpha += 1.0
            # Quality-weighted update + alignment calibration
            alpha += quality_score * 0.5 + alignment_bonus
        else:
            beta += 1.0 + abs(min(0, alignment_bonus))
        
        self._posteriors[key] = (alpha, beta)
        
        self._history.append({
            "strategy": strategy.value,
            "bucket": bucket,
            "success": success,
            "latency_ms": latency_ms,
            "quality_score": quality_score,
            "alignment_confidence": alignment_confidence,
            "timestamp": time.time(),
        })
        
        logger.debug(
            f"Updated posterior for ({bucket}, {strategy.value}): "
            f"α={alpha:.1f}, β={beta:.1f}"
            + (f", alignment_conf={alignment_confidence:.2f}" if alignment_confidence > 0 else "")
        )
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for each strategy."""
        stats = defaultdict(lambda: {"successes": 0, "failures": 0, "avg_quality": 0.0})
        
        for entry in self._history:
            key = entry["strategy"]
            if entry["success"]:
                stats[key]["successes"] += 1
            else:
                stats[key]["failures"] += 1
            stats[key]["avg_quality"] += entry["quality_score"]
        
        for key in stats:
            total = stats[key]["successes"] + stats[key]["failures"]
            if total > 0:
                stats[key]["avg_quality"] /= total
                stats[key]["success_rate"] = stats[key]["successes"] / total
            else:
                stats[key]["success_rate"] = 0.0
        
        return dict(stats)
    
    def get_best_strategy_for_context(
        self,
        context: ContextSignature,
    ) -> Tuple[WorkflowStrategy, float]:
        """
        Get the best-performing strategy for a context (exploitation only).
        
        Returns: (strategy, expected_success_rate)
        """
        bucket = context.to_bucket()
        
        best_strategy = None
        best_mean = 0.0
        
        for strategy in self.strategies:
            alpha, beta = self._posteriors[(bucket, strategy)]
            mean = alpha / (alpha + beta)
            if mean > best_mean:
                best_mean = mean
                best_strategy = strategy
        
        return best_strategy, best_mean
    
    def export_posteriors(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Export Thompson Sampling posteriors for persistence."""
        result = defaultdict(dict)
        for (bucket, strategy), (alpha, beta) in self._posteriors.items():
            result[bucket][strategy.value] = (alpha, beta)
        return dict(result)
    
    def import_posteriors(self, data: Dict[str, Dict[str, Tuple[float, float]]]) -> None:
        """Import previously saved posteriors."""
        for bucket, strategies in data.items():
            for strategy_name, (alpha, beta) in strategies.items():
                try:
                    strategy = WorkflowStrategy(strategy_name)
                    self._posteriors[(bucket, strategy)] = (alpha, beta)
                except ValueError:
                    continue
        
        logger.info(f"Imported {len(self._posteriors)} posterior entries")


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_meta_orchestrator_instance: Optional[MetaOrchestrator] = None


def get_meta_orchestrator() -> MetaOrchestrator:
    """
    Return the module-level singleton MetaOrchestrator.

    This ensures Thompson Sampling posteriors, execution history, and
    compiled graph caches persist across calls rather than being discarded
    with a fresh instance on every invocation.
    """
    global _meta_orchestrator_instance
    if _meta_orchestrator_instance is None:
        _meta_orchestrator_instance = MetaOrchestrator()
    return _meta_orchestrator_instance
