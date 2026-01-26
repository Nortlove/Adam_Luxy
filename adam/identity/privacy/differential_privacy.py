# =============================================================================
# ADAM Enhancement #19: Differential Privacy
# Location: adam/identity/privacy/differential_privacy.py
# =============================================================================

"""
Differential privacy support for identity resolution.

Provides:
- Privacy budget tracking (epsilon accounting)
- Noise injection for aggregate queries
- Membership inference protection
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PrivacyBudget(BaseModel):
    """Tracks privacy budget consumption."""
    
    total_epsilon: float = Field(1.0, description="Total privacy budget")
    consumed_epsilon: float = Field(0.0, description="Consumed budget")
    
    total_delta: float = Field(1e-5, description="Total delta budget")
    consumed_delta: float = Field(0.0, description="Consumed delta")
    
    reset_interval_hours: int = Field(24, description="Budget reset interval")
    last_reset: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def remaining_epsilon(self) -> float:
        """Remaining epsilon budget."""
        return max(0, self.total_epsilon - self.consumed_epsilon)
    
    @property
    def remaining_delta(self) -> float:
        """Remaining delta budget."""
        return max(0, self.total_delta - self.consumed_delta)
    
    @property
    def is_exhausted(self) -> bool:
        """Whether budget is exhausted."""
        return self.remaining_epsilon <= 0 or self.remaining_delta <= 0
    
    def can_consume(self, epsilon: float, delta: float = 0.0) -> bool:
        """Check if consumption is within budget."""
        return (
            self.remaining_epsilon >= epsilon and
            self.remaining_delta >= delta
        )
    
    def consume(self, epsilon: float, delta: float = 0.0) -> bool:
        """Consume privacy budget."""
        if not self.can_consume(epsilon, delta):
            return False
        
        self.consumed_epsilon += epsilon
        self.consumed_delta += delta
        return True
    
    def reset_if_needed(self) -> bool:
        """Reset budget if interval has passed."""
        elapsed = datetime.utcnow() - self.last_reset
        if elapsed >= timedelta(hours=self.reset_interval_hours):
            self.consumed_epsilon = 0.0
            self.consumed_delta = 0.0
            self.last_reset = datetime.utcnow()
            return True
        return False


class LaplaceMechanism:
    """Laplace mechanism for differential privacy."""
    
    @staticmethod
    def add_noise(
        value: float,
        sensitivity: float,
        epsilon: float
    ) -> float:
        """Add Laplace noise to a value."""
        scale = sensitivity / epsilon
        noise = np.random.laplace(0, scale)
        return value + noise
    
    @staticmethod
    def add_noise_batch(
        values: List[float],
        sensitivity: float,
        epsilon: float
    ) -> List[float]:
        """Add noise to multiple values."""
        scale = sensitivity / epsilon
        noise = np.random.laplace(0, scale, len(values))
        return [v + n for v, n in zip(values, noise)]


class GaussianMechanism:
    """Gaussian mechanism for (epsilon, delta)-DP."""
    
    @staticmethod
    def compute_sigma(
        sensitivity: float,
        epsilon: float,
        delta: float
    ) -> float:
        """Compute required sigma for given privacy parameters."""
        # sigma = sensitivity * sqrt(2 * ln(1.25 / delta)) / epsilon
        return sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
    
    @staticmethod
    def add_noise(
        value: float,
        sensitivity: float,
        epsilon: float,
        delta: float
    ) -> float:
        """Add Gaussian noise to a value."""
        sigma = GaussianMechanism.compute_sigma(sensitivity, epsilon, delta)
        noise = np.random.normal(0, sigma)
        return value + noise


class DifferentialPrivacyEngine:
    """
    Engine for differential privacy in identity resolution.
    
    Provides:
    - Privacy budget tracking per user/query
    - Noise injection for aggregates
    - Query answering with DP guarantees
    """
    
    def __init__(
        self,
        default_epsilon: float = 1.0,
        default_delta: float = 1e-5,
        mechanism: str = "laplace"
    ):
        self.default_epsilon = default_epsilon
        self.default_delta = default_delta
        self.mechanism = mechanism
        
        # Per-user/entity budgets
        self.budgets: Dict[str, PrivacyBudget] = {}
        
        # Query history for auditing
        self.query_log: List[Dict] = []
    
    def get_budget(self, entity_id: str) -> PrivacyBudget:
        """Get or create privacy budget for entity."""
        if entity_id not in self.budgets:
            self.budgets[entity_id] = PrivacyBudget(
                total_epsilon=self.default_epsilon,
                total_delta=self.default_delta
            )
        
        budget = self.budgets[entity_id]
        budget.reset_if_needed()
        return budget
    
    def query_count(
        self,
        entity_id: str,
        true_count: int,
        epsilon: Optional[float] = None,
        sensitivity: int = 1
    ) -> Optional[int]:
        """Answer a count query with DP noise."""
        epsilon = epsilon or self.default_epsilon / 10
        
        budget = self.get_budget(entity_id)
        if not budget.consume(epsilon):
            logger.warning(f"Privacy budget exhausted for {entity_id}")
            return None
        
        noisy_count = LaplaceMechanism.add_noise(
            float(true_count),
            float(sensitivity),
            epsilon
        )
        
        # Log query
        self.query_log.append({
            "entity_id": entity_id,
            "query_type": "count",
            "epsilon_consumed": epsilon,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return max(0, int(round(noisy_count)))
    
    def query_mean(
        self,
        entity_id: str,
        values: List[float],
        lower_bound: float,
        upper_bound: float,
        epsilon: Optional[float] = None
    ) -> Optional[float]:
        """Answer a mean query with DP noise."""
        epsilon = epsilon or self.default_epsilon / 10
        
        budget = self.get_budget(entity_id)
        if not budget.consume(epsilon):
            logger.warning(f"Privacy budget exhausted for {entity_id}")
            return None
        
        if not values:
            return None
        
        true_mean = np.mean(values)
        sensitivity = (upper_bound - lower_bound) / len(values)
        
        noisy_mean = LaplaceMechanism.add_noise(
            true_mean,
            sensitivity,
            epsilon
        )
        
        self.query_log.append({
            "entity_id": entity_id,
            "query_type": "mean",
            "epsilon_consumed": epsilon,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return float(np.clip(noisy_mean, lower_bound, upper_bound))
    
    def query_histogram(
        self,
        entity_id: str,
        values: List[Any],
        bins: List[Any],
        epsilon: Optional[float] = None
    ) -> Optional[Dict[Any, int]]:
        """Answer a histogram query with DP noise."""
        epsilon = epsilon or self.default_epsilon / 10
        
        budget = self.get_budget(entity_id)
        if not budget.consume(epsilon):
            return None
        
        # Compute true histogram
        histogram = {b: 0 for b in bins}
        for v in values:
            if v in histogram:
                histogram[v] += 1
        
        # Add noise to each bin
        per_bin_epsilon = epsilon / len(bins)
        noisy_histogram = {}
        for bin_name, count in histogram.items():
            noisy_count = LaplaceMechanism.add_noise(
                float(count),
                1.0,  # Sensitivity is 1 for histogram
                per_bin_epsilon
            )
            noisy_histogram[bin_name] = max(0, int(round(noisy_count)))
        
        self.query_log.append({
            "entity_id": entity_id,
            "query_type": "histogram",
            "epsilon_consumed": epsilon,
            "bins": len(bins),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return noisy_histogram
    
    def get_remaining_budget(self, entity_id: str) -> Dict[str, float]:
        """Get remaining budget for entity."""
        budget = self.get_budget(entity_id)
        return {
            "remaining_epsilon": budget.remaining_epsilon,
            "remaining_delta": budget.remaining_delta,
            "is_exhausted": budget.is_exhausted
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "entities_tracked": len(self.budgets),
            "queries_answered": len(self.query_log),
            "exhausted_budgets": sum(
                1 for b in self.budgets.values() if b.is_exhausted
            )
        }


# Singleton instance
_engine: Optional[DifferentialPrivacyEngine] = None


def get_differential_privacy_engine() -> DifferentialPrivacyEngine:
    """Get singleton DP engine."""
    global _engine
    if _engine is None:
        _engine = DifferentialPrivacyEngine()
    return _engine
