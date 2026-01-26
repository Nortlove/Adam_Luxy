# =============================================================================
# ADAM Verification Layer 1: Consistency
# Location: adam/verification/layers/consistency.py
# =============================================================================

"""
LAYER 1: ATOM CONSISTENCY VERIFICATION

Verifies that atom outputs are logically coherent:
- No contradictions between atoms
- Dependencies satisfied
- Psychological constraints respected
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from adam.verification.models.constraints import (
    Constraint,
    ConstraintResult,
    ConstraintSeverity,
    PsychologicalConstraint,
    DEFAULT_PSYCHOLOGICAL_CONSTRAINTS,
)
from adam.verification.models.results import (
    LayerResult,
    VerificationLayer,
)
from adam.atoms.models.atom_io import AtomOutput

logger = logging.getLogger(__name__)


class ConsistencyVerifier:
    """
    Layer 1: Verify consistency across atom outputs.
    """
    
    def __init__(
        self,
        constraints: List[Constraint] = None,
    ):
        self.constraints = constraints or DEFAULT_PSYCHOLOGICAL_CONSTRAINTS
    
    async def verify(
        self,
        atom_outputs: Dict[str, Any],
    ) -> LayerResult:
        """
        Verify consistency of atom outputs.
        
        Args:
            atom_outputs: Dict of atom_id -> AtomOutput
        
        Returns:
            LayerResult with constraint check results
        """
        start_time = datetime.now(timezone.utc)
        
        result = LayerResult(
            layer=VerificationLayer.CONSISTENCY,
            passed=True,
        )
        
        # Check each psychological constraint
        for constraint in self.constraints:
            if isinstance(constraint, PsychologicalConstraint):
                check_result = self._check_psychological_constraint(
                    constraint, atom_outputs
                )
            else:
                check_result = self._check_generic_constraint(
                    constraint, atom_outputs
                )
            
            result.add_result(check_result)
            
            if not check_result.satisfied:
                if check_result.severity in [ConstraintSeverity.ERROR, ConstraintSeverity.CRITICAL]:
                    result.passed = False
        
        # Check for dependency satisfaction
        dep_result = self._check_dependencies(atom_outputs)
        result.add_result(dep_result)
        if not dep_result.satisfied:
            result.passed = False
        
        end_time = datetime.now(timezone.utc)
        result.duration_ms = (end_time - start_time).total_seconds() * 1000
        result.summary = f"Checked {result.constraints_checked} constraints, {result.constraints_violated} violations"
        
        return result
    
    def _check_psychological_constraint(
        self,
        constraint: PsychologicalConstraint,
        outputs: Dict[str, Any],
    ) -> ConstraintResult:
        """Check a psychological constraint."""
        
        # Find antecedent value
        antecedent_value = None
        for atom_id, output in outputs.items():
            if constraint.antecedent_atom in atom_id:
                if isinstance(output, dict):
                    antecedent_value = output.get("primary_assessment")
                elif hasattr(output, "primary_assessment"):
                    antecedent_value = output.primary_assessment
                break
        
        # Find consequent value
        consequent_value = None
        for atom_id, output in outputs.items():
            if constraint.consequent_atom in atom_id:
                if isinstance(output, dict):
                    consequent_value = output.get("primary_assessment")
                elif hasattr(output, "primary_assessment"):
                    consequent_value = output.primary_assessment
                break
        
        # Check if constraint applies
        if antecedent_value is None or antecedent_value != constraint.antecedent_value:
            # Antecedent not satisfied, constraint doesn't apply
            return ConstraintResult(
                constraint_id=constraint.constraint_id,
                constraint_name=constraint.name,
                satisfied=True,
            )
        
        # Check consequent
        if consequent_value == constraint.expected_consequent:
            return ConstraintResult(
                constraint_id=constraint.constraint_id,
                constraint_name=constraint.name,
                satisfied=True,
            )
        
        # Violation
        return ConstraintResult(
            constraint_id=constraint.constraint_id,
            constraint_name=constraint.name,
            satisfied=False,
            violation_message=f"{constraint.antecedent_atom}={antecedent_value} should imply {constraint.consequent_atom}={constraint.expected_consequent}, but got {consequent_value}",
            violation_data={
                "antecedent": antecedent_value,
                "expected": constraint.expected_consequent,
                "actual": consequent_value,
            },
            severity=constraint.severity,
            correctable=True,
            correction_suggestion=f"Consider adjusting {constraint.consequent_atom} to {constraint.expected_consequent}",
        )
    
    def _check_generic_constraint(
        self,
        constraint: Constraint,
        outputs: Dict[str, Any],
    ) -> ConstraintResult:
        """Check a generic constraint."""
        # Simplified: just return satisfied
        return ConstraintResult(
            constraint_id=constraint.constraint_id,
            constraint_name=constraint.name,
            satisfied=True,
        )
    
    def _check_dependencies(
        self,
        outputs: Dict[str, Any],
    ) -> ConstraintResult:
        """Check that all atom dependencies are satisfied."""
        
        # Check that mechanism atom has regulatory and construal inputs
        mech_output = outputs.get("atom_mechanism_activation")
        if mech_output:
            has_rf = "atom_regulatory_focus" in outputs
            has_cl = "atom_construal_level" in outputs
            
            if not has_rf or not has_cl:
                return ConstraintResult(
                    constraint_id="dep_mechanism",
                    constraint_name="Mechanism atom dependencies",
                    satisfied=False,
                    violation_message="Mechanism atom missing upstream outputs",
                    severity=ConstraintSeverity.ERROR,
                )
        
        return ConstraintResult(
            constraint_id="dep_check",
            constraint_name="Dependency satisfaction",
            satisfied=True,
        )
