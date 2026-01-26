# =============================================================================
# ADAM Gradient Bridge Credit Attribution Engine
# Location: adam/gradient_bridge/attribution.py
# =============================================================================

"""
CREDIT ATTRIBUTION ENGINE

Multi-method attribution of outcomes to components.

Methods:
1. Confidence-Weighted: Weight by atom confidence
2. Counterfactual: Estimate marginal contribution
3. Shapley Values: Fair division of credit
4. Ensemble: Combine multiple methods
"""

import logging
import math
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from adam.gradient_bridge.models.credit import (
    AtomCredit,
    ComponentCredit,
    ComponentType,
    OutcomeAttribution,
    OutcomeType,
    AttributionMethod,
    CreditAssignmentRequest,
)
from adam.atoms.models.atom_io import AtomOutput
from adam.infrastructure.prometheus import get_metrics

logger = logging.getLogger(__name__)


def factorial(n: int) -> int:
    """Calculate factorial for Shapley computation."""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


class CreditAttributor:
    """
    Engine for computing credit attribution.
    
    Supports multiple attribution methods with ensemble averaging.
    """
    
    def __init__(self):
        self.metrics = get_metrics()
    
    async def compute_attribution(
        self,
        request: CreditAssignmentRequest,
    ) -> OutcomeAttribution:
        """
        Compute credit attribution for an outcome.
        
        Args:
            request: Attribution request with outcome and context
        
        Returns:
            Complete attribution with per-component credit
        """
        start_time = datetime.now(timezone.utc)
        
        # Choose method
        method = request.preferred_method or AttributionMethod.ENSEMBLE
        
        # Initialize attribution
        attribution = OutcomeAttribution(
            decision_id=request.decision_id,
            request_id=request.request_id,
            user_id=request.user_id,
            outcome_type=request.outcome_type,
            outcome_value=request.outcome_value,
            method=method,
            execution_path=request.execution_path,
            meta_learner_modality=request.meta_learner_modality,
        )
        
        # Compute atom credits based on method
        if request.atom_outputs:
            if method == AttributionMethod.CONFIDENCE_WEIGHTED:
                atom_credits = self._confidence_weighted_attribution(
                    request.atom_outputs,
                    request.outcome_value,
                )
            elif method == AttributionMethod.SHAPLEY:
                atom_credits = self._shapley_attribution(
                    request.atom_outputs,
                    request.outcome_value,
                )
            elif method == AttributionMethod.COUNTERFACTUAL:
                atom_credits = self._counterfactual_attribution(
                    request.atom_outputs,
                    request.outcome_value,
                )
            elif method == AttributionMethod.LLM_GUIDED:
                atom_credits = await self._llm_guided_attribution(
                    request.atom_outputs,
                    request.outcome_value,
                    request.outcome_type,
                    request.mechanism_used,
                )
            elif method == AttributionMethod.ENSEMBLE:
                atom_credits = await self._ensemble_attribution(
                    request.atom_outputs,
                    request.outcome_value,
                )
            else:
                # Fallback to confidence-weighted
                atom_credits = self._confidence_weighted_attribution(
                    request.atom_outputs,
                    request.outcome_value,
                )
            
            attribution.atom_credits = atom_credits
            attribution.total_atom_credit = sum(ac.credit_score for ac in atom_credits)
        
        # Compute mechanism credits
        if request.mechanism_used:
            attribution.primary_mechanism = request.mechanism_used
            
            # Credit primarily to the used mechanism
            mech_credits = {request.mechanism_used: request.outcome_value * 0.6}
            
            # Distribute remaining credit to other considered mechanisms
            remaining = request.outcome_value * 0.4
            others = [m for m in request.mechanisms_considered if m != request.mechanism_used]
            if others:
                per_mech = remaining / len(others)
                for m in others:
                    mech_credits[m] = per_mech
            
            attribution.mechanism_credits = mech_credits
            attribution.primary_mechanism_credit = mech_credits.get(request.mechanism_used, 0.0)
        
        # Compute component credits
        attribution.component_credits = self._compute_component_credits(
            atom_credits=attribution.atom_credits,
            outcome_value=request.outcome_value,
            execution_path=request.execution_path,
        )
        
        # Set confidence
        attribution.attribution_confidence = self._compute_confidence(attribution)
        
        # Timing
        end_time = datetime.now(timezone.utc)
        attribution.computed_at = end_time
        attribution.computation_ms = (end_time - start_time).total_seconds() * 1000
        
        return attribution
    
    def _confidence_weighted_attribution(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
    ) -> List[AtomCredit]:
        """
        Attribute credit based on atom confidence.
        
        Higher confidence atoms get proportionally more credit.
        """
        credits = []
        total_confidence = 0.0
        
        # Calculate total confidence
        for atom_id, output in atom_outputs.items():
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
            elif hasattr(output, "overall_confidence"):
                conf = output.overall_confidence
            else:
                conf = 0.5
            total_confidence += conf
        
        if total_confidence == 0:
            total_confidence = len(atom_outputs) * 0.5
        
        # Assign credit proportionally
        for atom_id, output in atom_outputs.items():
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
                atom_type = output.get("atom_type", "unknown")
                mechanisms = output.get("recommended_mechanisms", [])
                mech_weights = output.get("mechanism_weights", {})
            elif hasattr(output, "overall_confidence"):
                conf = output.overall_confidence
                atom_type = getattr(output, "atom_type", "unknown")
                mechanisms = getattr(output, "recommended_mechanisms", [])
                mech_weights = getattr(output, "mechanism_weights", {})
            else:
                conf = 0.5
                atom_type = "unknown"
                mechanisms = []
                mech_weights = {}
            
            credit_share = conf / total_confidence
            credit_score = outcome_value * credit_share
            
            credits.append(AtomCredit(
                atom_id=atom_id,
                atom_type=str(atom_type),
                credit_score=credit_score,
                credit_share=credit_share,
                method=AttributionMethod.CONFIDENCE_WEIGHTED,
                atom_confidence=conf,
                mechanisms_recommended=mechanisms,
                mechanism_weights=mech_weights,
            ))
        
        return credits
    
    async def _ensemble_attribution(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
    ) -> List[AtomCredit]:
        """
        Ensemble of multiple attribution methods.
        
        Combines:
        1. Confidence-weighted (fast, heuristic)
        2. Shapley values (fair, principled)
        3. Counterfactual (causal, marginal)
        
        Weights are calibrated based on computational cost vs accuracy.
        """
        # Get all three attributions
        confidence_credits = self._confidence_weighted_attribution(atom_outputs, outcome_value)
        shapley_credits = self._shapley_attribution(atom_outputs, outcome_value)
        counterfactual_credits = self._counterfactual_attribution(atom_outputs, outcome_value)
        
        # Ensemble weights (calibrated for accuracy vs cost)
        # Shapley is most principled, counterfactual captures causality
        weights = {
            "confidence": 0.25,
            "shapley": 0.45,
            "counterfactual": 0.30,
        }
        
        # Build lookup maps
        confidence_map = {ac.atom_id: ac for ac in confidence_credits}
        shapley_map = {ac.atom_id: ac for ac in shapley_credits}
        counterfactual_map = {ac.atom_id: ac for ac in counterfactual_credits}
        
        # Combine credits
        ensemble_credits = []
        for atom_id in atom_outputs.keys():
            conf_credit = confidence_map.get(atom_id)
            shap_credit = shapley_map.get(atom_id)
            cf_credit = counterfactual_map.get(atom_id)
            
            # Weighted average of credit scores
            credit_score = 0.0
            credit_share = 0.0
            
            if conf_credit:
                credit_score += weights["confidence"] * conf_credit.credit_score
                credit_share += weights["confidence"] * conf_credit.credit_share
            if shap_credit:
                credit_score += weights["shapley"] * shap_credit.credit_score
                credit_share += weights["shapley"] * shap_credit.credit_share
            if cf_credit:
                credit_score += weights["counterfactual"] * cf_credit.credit_score
                credit_share += weights["counterfactual"] * cf_credit.credit_share
            
            # Use confidence credit as base for metadata
            base = conf_credit or shap_credit or cf_credit
            if base:
                ensemble_credits.append(AtomCredit(
                    atom_id=atom_id,
                    atom_type=base.atom_type,
                    credit_score=credit_score,
                    credit_share=credit_share,
                    method=AttributionMethod.ENSEMBLE,
                    atom_confidence=base.atom_confidence,
                    atom_contribution=base.atom_contribution,
                    # Include counterfactual data if available
                    counterfactual_outcome=cf_credit.counterfactual_outcome if cf_credit else None,
                    marginal_contribution=cf_credit.marginal_contribution if cf_credit else None,
                    mechanisms_recommended=base.mechanisms_recommended,
                    mechanism_weights=base.mechanism_weights,
                ))
        
        return ensemble_credits
    
    def _shapley_attribution(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
    ) -> List[AtomCredit]:
        """
        Compute Shapley values for fair credit attribution.
        
        Shapley values satisfy:
        1. Efficiency: Sum equals total value
        2. Symmetry: Equal contributors get equal credit
        3. Dummy: Non-contributors get zero
        4. Additivity: Decomposable across games
        
        For N atoms, we compute marginal contribution of each atom
        across all possible coalitions (2^N subsets).
        
        Reference: Enhancement #06 - Multi-level Credit Attribution
        """
        atom_ids = list(atom_outputs.keys())
        n = len(atom_ids)
        
        if n == 0:
            return []
        
        # For small N, compute exact Shapley values
        # For large N, use sampling approximation
        if n <= 8:  # 2^8 = 256 coalitions, manageable
            return self._exact_shapley(atom_outputs, outcome_value)
        else:
            return self._sampled_shapley(atom_outputs, outcome_value, num_samples=100)
    
    def _exact_shapley(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
    ) -> List[AtomCredit]:
        r"""
        Compute exact Shapley values by enumerating all coalitions.
        
        φ_i = Σ_{S⊆N\{i}} [|S|!(|N|-|S|-1)! / |N|!] * [v(S∪{i}) - v(S)]
        
        where v(S) is the value function for coalition S.
        """
        atom_ids = list(atom_outputs.keys())
        n = len(atom_ids)
        n_factorial = factorial(n)
        
        shapley_values: Dict[str, float] = {atom_id: 0.0 for atom_id in atom_ids}
        
        # For each atom, compute its marginal contribution across all coalitions
        for i, atom_id in enumerate(atom_ids):
            other_atoms = [a for a in atom_ids if a != atom_id]
            
            # Iterate over all subsets of other atoms
            for subset_size in range(len(other_atoms) + 1):
                for subset in combinations(other_atoms, subset_size):
                    subset_set = set(subset)
                    
                    # Coalition value without atom_i
                    v_without = self._coalition_value(subset_set, atom_outputs, outcome_value)
                    
                    # Coalition value with atom_i
                    v_with = self._coalition_value(subset_set | {atom_id}, atom_outputs, outcome_value)
                    
                    # Marginal contribution
                    marginal = v_with - v_without
                    
                    # Shapley weight: |S|!(n-|S|-1)! / n!
                    s = len(subset_set)
                    weight = (factorial(s) * factorial(n - s - 1)) / n_factorial
                    
                    shapley_values[atom_id] += weight * marginal
        
        # Normalize to ensure sum equals outcome_value
        total_shapley = sum(shapley_values.values())
        if total_shapley > 0:
            scale = outcome_value / total_shapley
        else:
            scale = 1.0
        
        # Build credits
        credits = []
        for atom_id, shapley_value in shapley_values.items():
            scaled_value = shapley_value * scale
            output = atom_outputs[atom_id]
            
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
                atom_type = output.get("atom_type", "unknown")
                mechanisms = output.get("recommended_mechanisms", [])
                mech_weights = output.get("mechanism_weights", {})
            else:
                conf = getattr(output, "overall_confidence", 0.5)
                atom_type = getattr(output, "atom_type", "unknown")
                mechanisms = getattr(output, "recommended_mechanisms", [])
                mech_weights = getattr(output, "mechanism_weights", {})
            
            credits.append(AtomCredit(
                atom_id=atom_id,
                atom_type=str(atom_type),
                credit_score=max(0.0, min(1.0, scaled_value)),
                credit_share=scaled_value / outcome_value if outcome_value > 0 else 0.0,
                method=AttributionMethod.SHAPLEY,
                atom_confidence=conf,
                mechanisms_recommended=mechanisms,
                mechanism_weights=mech_weights,
            ))
        
        return credits
    
    def _sampled_shapley(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
        num_samples: int = 100,
    ) -> List[AtomCredit]:
        """
        Approximate Shapley values using random permutation sampling.
        
        For each permutation, compute marginal contribution of each atom
        when added in that order. Average over permutations.
        """
        import random
        
        atom_ids = list(atom_outputs.keys())
        n = len(atom_ids)
        
        shapley_values: Dict[str, float] = {atom_id: 0.0 for atom_id in atom_ids}
        
        for _ in range(num_samples):
            # Random permutation
            perm = atom_ids.copy()
            random.shuffle(perm)
            
            coalition: Set[str] = set()
            prev_value = 0.0
            
            for atom_id in perm:
                # Value with this atom added
                coalition.add(atom_id)
                current_value = self._coalition_value(coalition, atom_outputs, outcome_value)
                
                # Marginal contribution
                shapley_values[atom_id] += (current_value - prev_value)
                prev_value = current_value
        
        # Average over samples
        for atom_id in atom_ids:
            shapley_values[atom_id] /= num_samples
        
        # Normalize and build credits
        total_shapley = sum(shapley_values.values())
        if total_shapley > 0:
            scale = outcome_value / total_shapley
        else:
            scale = 1.0
        
        credits = []
        for atom_id, shapley_value in shapley_values.items():
            scaled_value = shapley_value * scale
            output = atom_outputs[atom_id]
            
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
                atom_type = output.get("atom_type", "unknown")
                mechanisms = output.get("recommended_mechanisms", [])
                mech_weights = output.get("mechanism_weights", {})
            else:
                conf = getattr(output, "overall_confidence", 0.5)
                atom_type = getattr(output, "atom_type", "unknown")
                mechanisms = getattr(output, "recommended_mechanisms", [])
                mech_weights = getattr(output, "mechanism_weights", {})
            
            credits.append(AtomCredit(
                atom_id=atom_id,
                atom_type=str(atom_type),
                credit_score=max(0.0, min(1.0, scaled_value)),
                credit_share=scaled_value / outcome_value if outcome_value > 0 else 0.0,
                method=AttributionMethod.SHAPLEY,
                atom_confidence=conf,
                mechanisms_recommended=mechanisms,
                mechanism_weights=mech_weights,
            ))
        
        return credits
    
    def _coalition_value(
        self,
        coalition: Set[str],
        atom_outputs: Dict[str, Any],
        base_outcome: float,
    ) -> float:
        """
        Compute the value function v(S) for a coalition of atoms.
        
        Models the expected outcome if only these atoms contributed.
        Uses a monotonic superadditive value function based on confidence.
        """
        if not coalition:
            return 0.0
        
        # Sum of weighted confidences in coalition
        total_confidence = 0.0
        max_confidence = 0.0
        
        for atom_id in coalition:
            output = atom_outputs.get(atom_id, {})
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
            else:
                conf = getattr(output, "overall_confidence", 0.5)
            
            total_confidence += conf
            max_confidence = max(max_confidence, conf)
        
        # All atoms total confidence
        all_total = 0.0
        for output in atom_outputs.values():
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
            else:
                conf = getattr(output, "overall_confidence", 0.5)
            all_total += conf
        
        if all_total == 0:
            return base_outcome * len(coalition) / len(atom_outputs)
        
        # Value is proportional to coalition's confidence share
        # with slight superadditivity (collaboration bonus)
        base_value = base_outcome * (total_confidence / all_total)
        
        # Collaboration bonus: having more atoms adds synergy
        synergy_factor = 1.0 + 0.05 * (len(coalition) - 1)
        
        return min(base_outcome, base_value * synergy_factor)
    
    def _counterfactual_attribution(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
    ) -> List[AtomCredit]:
        """
        Compute counterfactual credit by estimating marginal contribution.
        
        For each atom, asks: "What would the outcome have been without this atom?"
        The difference is the atom's marginal contribution.
        
        This captures causal attribution rather than just correlation.
        
        Reference: Enhancement #06 - Counterfactual Credit Assignment
        """
        atom_ids = list(atom_outputs.keys())
        n = len(atom_ids)
        
        if n == 0:
            return []
        
        # Full coalition value
        full_coalition = set(atom_ids)
        full_value = self._coalition_value(full_coalition, atom_outputs, outcome_value)
        
        credits = []
        marginal_contributions: Dict[str, float] = {}
        
        for atom_id in atom_ids:
            # Value without this atom
            without_atom = full_coalition - {atom_id}
            counterfactual_value = self._coalition_value(without_atom, atom_outputs, outcome_value)
            
            # Marginal contribution = v(all) - v(all - {i})
            marginal = full_value - counterfactual_value
            marginal_contributions[atom_id] = marginal
        
        # Normalize marginal contributions
        total_marginal = sum(marginal_contributions.values())
        if total_marginal > 0:
            scale = outcome_value / total_marginal
        else:
            scale = 1.0 / n if n > 0 else 1.0
        
        for atom_id in atom_ids:
            output = atom_outputs[atom_id]
            marginal = marginal_contributions[atom_id]
            scaled_credit = marginal * scale
            
            # Counterfactual outcome (what would have happened without this atom)
            without_atom = full_coalition - {atom_id}
            cf_outcome = self._coalition_value(without_atom, atom_outputs, outcome_value)
            
            if isinstance(output, dict):
                conf = output.get("overall_confidence", 0.5)
                atom_type = output.get("atom_type", "unknown")
                mechanisms = output.get("recommended_mechanisms", [])
                mech_weights = output.get("mechanism_weights", {})
            else:
                conf = getattr(output, "overall_confidence", 0.5)
                atom_type = getattr(output, "atom_type", "unknown")
                mechanisms = getattr(output, "recommended_mechanisms", [])
                mech_weights = getattr(output, "mechanism_weights", {})
            
            credits.append(AtomCredit(
                atom_id=atom_id,
                atom_type=str(atom_type),
                credit_score=max(0.0, min(1.0, scaled_credit)),
                credit_share=scaled_credit / outcome_value if outcome_value > 0 else 0.0,
                method=AttributionMethod.COUNTERFACTUAL,
                atom_confidence=conf,
                counterfactual_outcome=cf_outcome,
                marginal_contribution=marginal,
                mechanisms_recommended=mechanisms,
                mechanism_weights=mech_weights,
            ))
        
        return credits
    
    async def _llm_guided_attribution(
        self,
        atom_outputs: Dict[str, Any],
        outcome_value: float,
        outcome_type: OutcomeType,
        mechanism_used: Optional[str] = None,
    ) -> List[AtomCredit]:
        """
        Use Claude to reason about credit attribution.
        
        Claude analyzes:
        1. What each atom contributed
        2. How well each atom's recommendation matched the outcome
        3. Which psychological insights were most relevant
        
        This provides explainable, theory-grounded attribution.
        
        Reference: Enhancement #06 - QLLM-Guided Attribution
        """
        try:
            from adam.llm.service import LLMService
            
            llm = LLMService()
            
            # Build context for Claude
            atom_summaries = []
            for atom_id, output in atom_outputs.items():
                if isinstance(output, dict):
                    summary = {
                        "atom_id": atom_id,
                        "atom_type": output.get("atom_type", "unknown"),
                        "confidence": output.get("overall_confidence", 0.5),
                        "mechanisms": output.get("recommended_mechanisms", []),
                        "reasoning": output.get("reasoning", ""),
                    }
                else:
                    summary = {
                        "atom_id": atom_id,
                        "atom_type": getattr(output, "atom_type", "unknown"),
                        "confidence": getattr(output, "overall_confidence", 0.5),
                        "mechanisms": getattr(output, "recommended_mechanisms", []),
                        "reasoning": getattr(output, "reasoning", ""),
                    }
                atom_summaries.append(summary)
            
            prompt = f"""You are analyzing the credit attribution for an advertising decision outcome.

OUTCOME:
- Type: {outcome_type.value if hasattr(outcome_type, 'value') else outcome_type}
- Value: {outcome_value} (1.0 = full success, 0.0 = failure)
- Mechanism Used: {mechanism_used or 'Unknown'}

ATOMS THAT CONTRIBUTED:
{self._format_atoms_for_llm(atom_summaries)}

TASK:
Analyze which atoms contributed most to this outcome. Consider:
1. Did the atom's recommended mechanism match what was used?
2. How confident was the atom? Higher confidence + correct = more credit
3. Did the atom's reasoning align with the outcome?

Return a JSON object with credit scores for each atom:
{{
    "credits": {{
        "atom_id_1": {{"score": 0.3, "reason": "explanation"}},
        "atom_id_2": {{"score": 0.5, "reason": "explanation"}}
    }},
    "total_credit": 0.8,
    "attribution_reasoning": "Overall reasoning"
}}

Scores should sum to approximately {outcome_value}.
"""
            
            response = await llm.client.complete(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.1,  # Low temperature for consistent attribution
            )
            
            # Parse LLM response
            import json
            try:
                # Extract JSON from response
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Find JSON block
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
                
                credits = []
                for atom_id, credit_data in result.get("credits", {}).items():
                    output = atom_outputs.get(atom_id, {})
                    
                    if isinstance(output, dict):
                        conf = output.get("overall_confidence", 0.5)
                        atom_type = output.get("atom_type", "unknown")
                        mechanisms = output.get("recommended_mechanisms", [])
                        mech_weights = output.get("mechanism_weights", {})
                    else:
                        conf = getattr(output, "overall_confidence", 0.5)
                        atom_type = getattr(output, "atom_type", "unknown")
                        mechanisms = getattr(output, "recommended_mechanisms", [])
                        mech_weights = getattr(output, "mechanism_weights", {})
                    
                    score = credit_data.get("score", 0.0) if isinstance(credit_data, dict) else float(credit_data)
                    reason = credit_data.get("reason", "") if isinstance(credit_data, dict) else ""
                    
                    total_score = sum(
                        c.get("score", 0.0) if isinstance(c, dict) else float(c)
                        for c in result.get("credits", {}).values()
                    )
                    
                    credits.append(AtomCredit(
                        atom_id=atom_id,
                        atom_type=str(atom_type),
                        credit_score=max(0.0, min(1.0, score)),
                        credit_share=score / total_score if total_score > 0 else 0.0,
                        method=AttributionMethod.LLM_GUIDED,
                        atom_confidence=conf,
                        atom_contribution=reason,
                        mechanisms_recommended=mechanisms,
                        mechanism_weights=mech_weights,
                    ))
                
                return credits
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse LLM attribution response: {e}")
                # Fallback to confidence-weighted
                return self._confidence_weighted_attribution(atom_outputs, outcome_value)
                
        except ImportError:
            logger.warning("LLM client not available, falling back to confidence-weighted")
            return self._confidence_weighted_attribution(atom_outputs, outcome_value)
        except Exception as e:
            logger.error(f"LLM attribution failed: {e}")
            return self._confidence_weighted_attribution(atom_outputs, outcome_value)
    
    def _format_atoms_for_llm(self, atom_summaries: List[Dict[str, Any]]) -> str:
        """Format atom summaries for LLM prompt."""
        lines = []
        for summary in atom_summaries:
            lines.append(f"""
Atom: {summary['atom_id']}
  Type: {summary['atom_type']}
  Confidence: {summary['confidence']:.2f}
  Recommended Mechanisms: {', '.join(summary.get('mechanisms', [])) or 'None'}
  Reasoning: {summary.get('reasoning', 'N/A')[:200]}
""")
        return "\n".join(lines)

    def _compute_component_credits(
        self,
        atom_credits: List[AtomCredit],
        outcome_value: float,
        execution_path: str,
    ) -> List[ComponentCredit]:
        """Compute credits for system components."""
        credits = []
        
        # Aggregate atom credits
        atom_total = sum(ac.credit_score for ac in atom_credits)
        
        # Graph gets credit for profile accuracy
        credits.append(ComponentCredit(
            component_type=ComponentType.GRAPH,
            credit_score=outcome_value * 0.2,
            credit_share=0.2,
        ))
        
        # Meta-learner gets credit for routing
        path_credit = 0.15 if execution_path == "fast" else 0.1
        credits.append(ComponentCredit(
            component_type=ComponentType.META_LEARNER,
            credit_score=outcome_value * path_credit,
            credit_share=path_credit,
        ))
        
        # Bandit gets credit for arm selection
        credits.append(ComponentCredit(
            component_type=ComponentType.BANDIT,
            credit_score=outcome_value * 0.15,
            credit_share=0.15,
        ))
        
        return credits
    
    def _compute_confidence(self, attribution: OutcomeAttribution) -> float:
        """Compute confidence in the attribution."""
        # Higher confidence when:
        # - More atoms contributed
        # - Atom confidences were higher
        # - Outcome was clear (0 or 1, not 0.5)
        
        base_confidence = 0.5
        
        # Boost for number of atoms
        if attribution.atom_credits:
            base_confidence += min(0.2, len(attribution.atom_credits) * 0.05)
        
        # Boost for atom confidence average
        if attribution.atom_credits:
            avg_conf = sum(ac.atom_confidence for ac in attribution.atom_credits) / len(attribution.atom_credits)
            base_confidence += avg_conf * 0.2
        
        # Boost for clear outcome
        outcome_clarity = abs(attribution.outcome_value - 0.5) * 2
        base_confidence += outcome_clarity * 0.1
        
        return min(1.0, base_confidence)
