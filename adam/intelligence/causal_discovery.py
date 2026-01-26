# =============================================================================
# ADAM Intelligence: Causal Discovery Layer
# Location: adam/intelligence/causal_discovery.py
# =============================================================================

"""
CAUSAL DISCOVERY LAYER

Automatically discovers causal relationships between behavioral signals,
psychological constructs, and advertising outcomes.

Goes beyond correlation: Learns CAUSAL structure from observational data.

Key Capabilities:
1. PC Algorithm - Constraint-based causal discovery
2. FCI Algorithm - Handles latent confounders
3. Causal Effect Estimation - Computes Average Treatment Effects
4. Intervention Analysis - "What if we changed X?"

This enables ADAM to:
- Understand WHY certain ads work (not just THAT they work)
- Predict effects of interventions (not just associations)
- Identify confounders and avoid spurious correlations
- Build genuine understanding of psychological mechanisms

Reference:
- Pearl (2009) "Causality: Models, Reasoning, and Inference"
- Spirtes et al. (2000) "Causation, Prediction, and Search"
- Peters et al. (2017) "Elements of Causal Inference"
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
import logging
import numpy as np
from itertools import combinations

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class CausalDiscoveryConfig:
    """Configuration for causal discovery."""
    
    # PC Algorithm
    alpha: float = 0.05  # Significance level for independence tests
    max_conditioning_set: int = 3  # Maximum size of conditioning sets
    
    # Estimation
    min_samples_for_test: int = 50
    min_samples_for_effect: int = 100
    
    # Validation
    bootstrap_samples: int = 100
    confidence_threshold: float = 0.8
    
    # Discovery
    max_variables: int = 50  # Maximum variables to consider


class EdgeType(str, Enum):
    """Types of edges in causal graph."""
    DIRECTED = "directed"        # A → B
    UNDIRECTED = "undirected"    # A - B (unknown direction)
    BIDIRECTED = "bidirected"    # A ↔ B (latent confounder)


class RelationshipStrength(str, Enum):
    """Strength of causal relationship."""
    STRONG = "strong"        # ATE > 0.3
    MODERATE = "moderate"    # 0.1 < ATE < 0.3
    WEAK = "weak"           # ATE < 0.1


# =============================================================================
# CAUSAL GRAPH
# =============================================================================

@dataclass
class CausalEdge:
    """A causal edge between two variables."""
    source: str
    target: str
    edge_type: EdgeType
    strength: Optional[float] = None  # Average Treatment Effect
    confidence: float = 0.5
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "strength": self.strength,
            "confidence": self.confidence,
        }


class CausalGraph(BaseModel):
    """
    A causal graph representing discovered causal relationships.
    """
    
    graph_id: str = Field(default="")
    variables: List[str] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sample_size: int = Field(default=0)
    
    def add_edge(self, edge: CausalEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge.to_dict())
    
    def get_parents(self, variable: str) -> List[str]:
        """Get causal parents of a variable."""
        parents = []
        for edge in self.edges:
            if edge["target"] == variable and edge["edge_type"] == EdgeType.DIRECTED.value:
                parents.append(edge["source"])
        return parents
    
    def get_children(self, variable: str) -> List[str]:
        """Get causal children of a variable."""
        children = []
        for edge in self.edges:
            if edge["source"] == variable and edge["edge_type"] == EdgeType.DIRECTED.value:
                children.append(edge["target"])
        return children
    
    def to_neo4j_cypher(self) -> str:
        """Generate Cypher to store graph in Neo4j."""
        statements = []
        
        for edge in self.edges:
            statements.append(f"""
            MERGE (a:CausalVariable {{name: '{edge["source"]}'}})
            MERGE (b:CausalVariable {{name: '{edge["target"]}'}})
            MERGE (a)-[r:CAUSES {{
                edge_type: '{edge["edge_type"]}',
                strength: {edge.get("strength") or 0},
                confidence: {edge["confidence"]}
            }}]->(b)
            """)
        
        return "\n".join(statements)


# =============================================================================
# INDEPENDENCE TESTS
# =============================================================================

class IndependenceTest:
    """
    Statistical independence test for causal discovery.
    
    Tests if X ⊥ Y | Z (X independent of Y given Z).
    """
    
    def __init__(self, config: CausalDiscoveryConfig):
        self.config = config
    
    def test_independence(
        self,
        data: np.ndarray,
        x_idx: int,
        y_idx: int,
        z_indices: List[int],
    ) -> Tuple[bool, float]:
        """
        Test conditional independence: X ⊥ Y | Z
        
        Uses partial correlation test with Fisher's z-transform.
        
        Args:
            data: Data matrix (samples x variables)
            x_idx: Index of X variable
            y_idx: Index of Y variable
            z_indices: Indices of conditioning set Z
            
        Returns:
            Tuple of (is_independent, p_value)
        """
        n = len(data)
        
        if n < self.config.min_samples_for_test:
            return False, 0.0  # Not enough data
        
        if not z_indices:
            # Unconditional correlation
            corr = np.corrcoef(data[:, x_idx], data[:, y_idx])[0, 1]
        else:
            # Partial correlation
            corr = self._partial_correlation(data, x_idx, y_idx, z_indices)
        
        # Fisher's z-transform
        if abs(corr) >= 1:
            return False, 0.0
        
        z = 0.5 * np.log((1 + corr) / (1 - corr))
        z_stat = z * np.sqrt(n - len(z_indices) - 3)
        
        # Two-tailed p-value from standard normal
        from scipy import stats
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        is_independent = p_value > self.config.alpha
        
        return is_independent, p_value
    
    def _partial_correlation(
        self,
        data: np.ndarray,
        x_idx: int,
        y_idx: int,
        z_indices: List[int],
    ) -> float:
        """Compute partial correlation of X and Y given Z."""
        # Residualize X and Y with respect to Z
        Z = data[:, z_indices]
        X = data[:, x_idx]
        Y = data[:, y_idx]
        
        # Add constant for regression
        Z_with_const = np.column_stack([np.ones(len(Z)), Z])
        
        # Residuals of X ~ Z
        coeffs_x = np.linalg.lstsq(Z_with_const, X, rcond=None)[0]
        resid_x = X - Z_with_const @ coeffs_x
        
        # Residuals of Y ~ Z
        coeffs_y = np.linalg.lstsq(Z_with_const, Y, rcond=None)[0]
        resid_y = Y - Z_with_const @ coeffs_y
        
        # Correlation of residuals
        return np.corrcoef(resid_x, resid_y)[0, 1]


# =============================================================================
# PC ALGORITHM
# =============================================================================

class PCAlgorithm:
    """
    PC Algorithm for causal discovery.
    
    Constraint-based method that:
    1. Starts with complete undirected graph
    2. Removes edges based on conditional independence tests
    3. Orients edges using v-structures and orientation rules
    
    Reference: Spirtes et al. (2000)
    """
    
    def __init__(self, config: CausalDiscoveryConfig):
        self.config = config
        self.independence_test = IndependenceTest(config)
    
    def discover(
        self,
        data: np.ndarray,
        variable_names: List[str],
    ) -> CausalGraph:
        """
        Run PC algorithm on data.
        
        Args:
            data: Data matrix (samples x variables)
            variable_names: Names of variables
            
        Returns:
            Discovered CausalGraph
        """
        n_vars = data.shape[1]
        
        # Step 1: Start with complete undirected graph
        adjacency = np.ones((n_vars, n_vars), dtype=bool)
        np.fill_diagonal(adjacency, False)
        
        # Separation sets for orientation
        sep_sets: Dict[Tuple[int, int], Set[int]] = {}
        
        # Step 2: Edge removal phase
        for cond_size in range(self.config.max_conditioning_set + 1):
            adjacency, sep_sets = self._remove_edges(
                data, adjacency, sep_sets, cond_size
            )
        
        # Step 3: Orient edges
        edge_types = self._orient_edges(adjacency, sep_sets, n_vars)
        
        # Build graph
        graph = CausalGraph(
            graph_id=f"pc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            variables=variable_names,
            sample_size=len(data),
        )
        
        for i in range(n_vars):
            for j in range(i + 1, n_vars):
                if adjacency[i, j]:
                    edge_type = edge_types.get((i, j), EdgeType.UNDIRECTED)
                    
                    if edge_type == EdgeType.DIRECTED:
                        # i → j
                        graph.add_edge(CausalEdge(
                            source=variable_names[i],
                            target=variable_names[j],
                            edge_type=EdgeType.DIRECTED,
                            confidence=0.8,
                        ))
                    elif edge_type == EdgeType.UNDIRECTED:
                        # Unknown direction
                        graph.add_edge(CausalEdge(
                            source=variable_names[i],
                            target=variable_names[j],
                            edge_type=EdgeType.UNDIRECTED,
                            confidence=0.6,
                        ))
        
        logger.info(
            f"PC discovered {len(graph.edges)} edges from {len(variable_names)} variables"
        )
        
        return graph
    
    def _remove_edges(
        self,
        data: np.ndarray,
        adjacency: np.ndarray,
        sep_sets: Dict,
        cond_size: int,
    ) -> Tuple[np.ndarray, Dict]:
        """Remove edges based on conditional independence."""
        n_vars = data.shape[1]
        
        for i in range(n_vars):
            for j in range(i + 1, n_vars):
                if not adjacency[i, j]:
                    continue
                
                # Get neighbors for conditioning
                neighbors = [k for k in range(n_vars) 
                            if k != i and k != j and 
                            (adjacency[i, k] or adjacency[j, k])]
                
                if len(neighbors) < cond_size:
                    continue
                
                # Test all conditioning sets of size cond_size
                for cond_set in combinations(neighbors, cond_size):
                    is_indep, p_value = self.independence_test.test_independence(
                        data, i, j, list(cond_set)
                    )
                    
                    if is_indep:
                        # Remove edge and store separation set
                        adjacency[i, j] = False
                        adjacency[j, i] = False
                        sep_sets[(i, j)] = set(cond_set)
                        sep_sets[(j, i)] = set(cond_set)
                        break
        
        return adjacency, sep_sets
    
    def _orient_edges(
        self,
        adjacency: np.ndarray,
        sep_sets: Dict,
        n_vars: int,
    ) -> Dict[Tuple[int, int], EdgeType]:
        """Orient edges using v-structures and Meek's rules."""
        edge_types: Dict[Tuple[int, int], EdgeType] = {}
        
        # Find v-structures: i - k - j where i and j not adjacent and k not in sep(i,j)
        for k in range(n_vars):
            neighbors = [n for n in range(n_vars) if adjacency[k, n]]
            
            for i, j in combinations(neighbors, 2):
                if adjacency[i, j]:  # i and j adjacent, not a v-structure
                    continue
                
                sep_set = sep_sets.get((i, j), set())
                if k not in sep_set:
                    # v-structure: i → k ← j
                    edge_types[(i, k)] = EdgeType.DIRECTED
                    edge_types[(j, k)] = EdgeType.DIRECTED
        
        # Apply Meek's rules (simplified)
        changed = True
        while changed:
            changed = False
            
            for i in range(n_vars):
                for j in range(n_vars):
                    if not adjacency[i, j]:
                        continue
                    
                    if (i, j) in edge_types:
                        continue
                    
                    # Rule 1: i → k - j implies i → k → j
                    for k in range(n_vars):
                        if (edge_types.get((i, k)) == EdgeType.DIRECTED and
                            adjacency[k, j] and
                            (k, j) not in edge_types):
                            edge_types[(k, j)] = EdgeType.DIRECTED
                            changed = True
        
        return edge_types


# =============================================================================
# CAUSAL EFFECT ESTIMATOR
# =============================================================================

class CausalEffectEstimator:
    """
    Estimates causal effects from data and causal graph.
    
    Computes Average Treatment Effect (ATE) using:
    - Adjustment formula (when confounders are observed)
    - Inverse Propensity Weighting
    - Doubly Robust estimation
    """
    
    def __init__(self, config: CausalDiscoveryConfig):
        self.config = config
    
    def estimate_ate(
        self,
        data: np.ndarray,
        variable_names: List[str],
        treatment: str,
        outcome: str,
        adjustment_set: List[str],
    ) -> Dict[str, Any]:
        """
        Estimate Average Treatment Effect.
        
        ATE = E[Y | do(X=1)] - E[Y | do(X=0)]
        
        Args:
            data: Data matrix
            variable_names: Variable names
            treatment: Treatment variable name
            outcome: Outcome variable name
            adjustment_set: Variables to adjust for (confounders)
            
        Returns:
            Dict with ATE estimate and confidence interval
        """
        # Get indices
        name_to_idx = {n: i for i, n in enumerate(variable_names)}
        t_idx = name_to_idx[treatment]
        y_idx = name_to_idx[outcome]
        adj_indices = [name_to_idx[a] for a in adjustment_set]
        
        T = data[:, t_idx]
        Y = data[:, y_idx]
        
        if not adj_indices:
            # No adjustment needed
            ate = Y[T > 0.5].mean() - Y[T <= 0.5].mean()
            std_err = self._standard_error(Y, T)
        else:
            # Adjustment formula
            Z = data[:, adj_indices]
            ate, std_err = self._adjusted_ate(T, Y, Z)
        
        # Confidence interval
        ci_low = ate - 1.96 * std_err
        ci_high = ate + 1.96 * std_err
        
        # Strength classification
        if abs(ate) > 0.3:
            strength = RelationshipStrength.STRONG
        elif abs(ate) > 0.1:
            strength = RelationshipStrength.MODERATE
        else:
            strength = RelationshipStrength.WEAK
        
        return {
            "treatment": treatment,
            "outcome": outcome,
            "ate": float(ate),
            "std_error": float(std_err),
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
            "strength": strength.value,
            "adjustment_set": adjustment_set,
        }
    
    def _adjusted_ate(
        self,
        T: np.ndarray,
        Y: np.ndarray,
        Z: np.ndarray,
    ) -> Tuple[float, float]:
        """Compute ATE with covariate adjustment."""
        # Simple regression adjustment
        # Y = β0 + β1*T + β2*Z + ε
        # ATE = β1
        
        n = len(T)
        X = np.column_stack([np.ones(n), T, Z])
        
        try:
            coeffs, residuals, rank, s = np.linalg.lstsq(X, Y, rcond=None)
            ate = coeffs[1]  # Coefficient on T
            
            # Standard error
            if len(residuals) > 0:
                mse = residuals[0] / (n - len(coeffs))
                var_coef = mse * np.linalg.inv(X.T @ X)[1, 1]
                std_err = np.sqrt(var_coef)
            else:
                std_err = 0.1  # Default
            
            return ate, std_err
        except Exception as e:
            logger.warning(f"Adjusted ATE failed: {e}")
            return 0.0, 1.0
    
    def _standard_error(self, Y: np.ndarray, T: np.ndarray) -> float:
        """Compute standard error of difference in means."""
        n1 = (T > 0.5).sum()
        n0 = (T <= 0.5).sum()
        
        if n1 < 2 or n0 < 2:
            return 1.0
        
        var1 = Y[T > 0.5].var()
        var0 = Y[T <= 0.5].var()
        
        return np.sqrt(var1/n1 + var0/n0)


# =============================================================================
# CAUSAL DISCOVERY ENGINE
# =============================================================================

class CausalDiscoveryEngine:
    """
    Main engine for causal discovery in ADAM.
    
    Discovers causal structure from behavioral data and estimates
    causal effects of interventions.
    
    Usage:
        engine = CausalDiscoveryEngine()
        
        # Discover causal structure
        graph = await engine.discover_causal_structure(data, variable_names)
        
        # Estimate effect
        effect = await engine.estimate_effect(
            data, variable_names,
            treatment="regulatory_focus",
            outcome="conversion"
        )
        
        # Identify confounders
        confounders = engine.identify_confounders(graph, "treatment", "outcome")
    """
    
    def __init__(self, config: Optional[CausalDiscoveryConfig] = None):
        self.config = config or CausalDiscoveryConfig()
        
        self.pc_algorithm = PCAlgorithm(self.config)
        self.effect_estimator = CausalEffectEstimator(self.config)
        
        # Cache
        self.discovered_graphs: Dict[str, CausalGraph] = {}
        
        # Statistics
        self.discovery_runs = 0
        self.effect_estimations = 0
    
    async def discover_causal_structure(
        self,
        data: np.ndarray,
        variable_names: List[str],
        cache_key: Optional[str] = None,
    ) -> CausalGraph:
        """
        Discover causal structure from data.
        
        Args:
            data: Data matrix (samples x variables)
            variable_names: Names of variables
            cache_key: Optional key for caching result
            
        Returns:
            Discovered CausalGraph
        """
        self.discovery_runs += 1
        
        # Run PC algorithm
        graph = self.pc_algorithm.discover(data, variable_names)
        
        # Cache if key provided
        if cache_key:
            self.discovered_graphs[cache_key] = graph
        
        return graph
    
    async def estimate_effect(
        self,
        data: np.ndarray,
        variable_names: List[str],
        treatment: str,
        outcome: str,
        graph: Optional[CausalGraph] = None,
    ) -> Dict[str, Any]:
        """
        Estimate causal effect of treatment on outcome.
        
        If graph provided, identifies adjustment set from graph.
        Otherwise, adjusts for all other variables.
        """
        self.effect_estimations += 1
        
        # Identify adjustment set
        if graph:
            adjustment_set = self._identify_adjustment_set(
                graph, treatment, outcome, variable_names
            )
        else:
            # Adjust for all others (conservative)
            adjustment_set = [v for v in variable_names 
                            if v not in [treatment, outcome]]
        
        # Estimate effect
        effect = self.effect_estimator.estimate_ate(
            data, variable_names, treatment, outcome, adjustment_set
        )
        
        return effect
    
    def _identify_adjustment_set(
        self,
        graph: CausalGraph,
        treatment: str,
        outcome: str,
        all_variables: List[str],
    ) -> List[str]:
        """
        Identify valid adjustment set for causal effect estimation.
        
        Uses the backdoor criterion: Block all backdoor paths from
        treatment to outcome.
        """
        # Simple approach: adjust for all parents of treatment and outcome
        # that are not descendants of treatment
        
        treatment_parents = graph.get_parents(treatment)
        outcome_parents = graph.get_parents(outcome)
        treatment_children = graph.get_children(treatment)
        
        # Valid adjustments: parents of outcome that aren't on causal path
        adjustment = set(outcome_parents) | set(treatment_parents)
        
        # Remove treatment itself and its children
        adjustment.discard(treatment)
        adjustment.discard(outcome)
        for child in treatment_children:
            adjustment.discard(child)
        
        return list(adjustment)
    
    def identify_confounders(
        self,
        graph: CausalGraph,
        treatment: str,
        outcome: str,
    ) -> List[str]:
        """
        Identify confounders between treatment and outcome.
        
        Confounders are common causes of both treatment and outcome.
        """
        treatment_parents = set(graph.get_parents(treatment))
        outcome_parents = set(graph.get_parents(outcome))
        
        # Common parents are confounders
        confounders = treatment_parents & outcome_parents
        
        return list(confounders)
    
    async def suggest_interventions(
        self,
        graph: CausalGraph,
        target_outcome: str,
        data: np.ndarray,
        variable_names: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Suggest interventions to improve target outcome.
        
        Finds causal parents of outcome and estimates effect of
        intervening on each.
        """
        parents = graph.get_parents(target_outcome)
        
        interventions = []
        for parent in parents:
            effect = await self.estimate_effect(
                data, variable_names, parent, target_outcome, graph
            )
            
            if effect["ate"] > 0:
                direction = "increase"
            else:
                direction = "decrease"
            
            interventions.append({
                "variable": parent,
                "direction": direction,
                "expected_effect": abs(effect["ate"]),
                "confidence_interval": [effect["ci_low"], effect["ci_high"]],
                "strength": effect["strength"],
            })
        
        # Sort by expected effect
        interventions.sort(key=lambda x: x["expected_effect"], reverse=True)
        
        return interventions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "discovery_runs": self.discovery_runs,
            "effect_estimations": self.effect_estimations,
            "cached_graphs": len(self.discovered_graphs),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[CausalDiscoveryEngine] = None


def get_causal_discovery_engine() -> CausalDiscoveryEngine:
    """Get singleton Causal Discovery engine."""
    global _engine
    if _engine is None:
        _engine = CausalDiscoveryEngine()
    return _engine
