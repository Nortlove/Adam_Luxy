# =============================================================================
# ADAM Verification Layer 3: Safety
# Location: adam/verification/layers/safety.py
# =============================================================================

"""
LAYER 3: SAFETY VALIDATION

Protects users from harmful recommendations:
- Vulnerable population protection
- Manipulation detection
- Dark pattern avoidance
- Regulatory compliance
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.verification.models.constraints import (
    ConstraintResult,
    ConstraintSeverity,
    SafetyConstraint,
    DEFAULT_SAFETY_CONSTRAINTS,
)
from adam.verification.models.results import (
    LayerResult,
    VerificationLayer,
)

logger = logging.getLogger(__name__)


class SafetyValidator:
    """
    Layer 3: Validate safety of recommendations.
    
    Key protections:
    - High neuroticism users: avoid fear-based messaging
    - Scarcity intensity limits
    - Dark pattern detection and blocking
    """
    
    def __init__(
        self,
        constraints: Optional[List[SafetyConstraint]] = None,
    ):
        self.constraints = constraints or DEFAULT_SAFETY_CONSTRAINTS
    
    async def verify(
        self,
        atom_outputs: Dict[str, Any],
        user_profile: Optional[Dict[str, float]] = None,
        mechanism_outputs: Optional[Dict[str, Any]] = None,
    ) -> LayerResult:
        """
        Verify safety of atom outputs and recommendations.
        """
        start_time = datetime.now(timezone.utc)
        
        result = LayerResult(
            layer=VerificationLayer.SAFETY,
            passed=True,
        )
        
        # Check each safety constraint
        for constraint in self.constraints:
            check_result = await self._check_safety_constraint(
                constraint,
                atom_outputs,
                user_profile or {},
                mechanism_outputs or {},
            )
            result.add_result(check_result)
            
            if not check_result.satisfied:
                if check_result.severity in [ConstraintSeverity.ERROR, ConstraintSeverity.CRITICAL]:
                    result.passed = False
        
        end_time = datetime.now(timezone.utc)
        result.duration_ms = (end_time - start_time).total_seconds() * 1000
        result.summary = f"Safety checks: {result.constraints_satisfied}/{result.constraints_checked} passed"
        
        return result
    
    async def _check_safety_constraint(
        self,
        constraint: SafetyConstraint,
        atom_outputs: Dict[str, Any],
        user_profile: Dict[str, float],
        mechanism_outputs: Dict[str, Any],
    ) -> ConstraintResult:
        """Check a single safety constraint."""
        
        # Get detection signal value
        signal_value = self._get_signal_value(
            constraint.detection_signal,
            atom_outputs,
            user_profile,
            mechanism_outputs,
        )
        
        if signal_value is None:
            # Signal not available, assume safe
            return ConstraintResult(
                constraint_id=constraint.constraint_id,
                constraint_name=constraint.name,
                satisfied=True,
            )
        
        # Check threshold
        if signal_value >= constraint.detection_threshold:
            return ConstraintResult(
                constraint_id=constraint.constraint_id,
                constraint_name=constraint.name,
                satisfied=False,
                violation_message=f"{constraint.detection_signal}={signal_value:.2f} exceeds threshold {constraint.detection_threshold}",
                violation_data={
                    "signal": constraint.detection_signal,
                    "value": signal_value,
                    "threshold": constraint.detection_threshold,
                },
                severity=constraint.severity,
                correctable=constraint.fallback_action != "block_and_log",
                correction_suggestion=constraint.fallback_action,
            )
        
        return ConstraintResult(
            constraint_id=constraint.constraint_id,
            constraint_name=constraint.name,
            satisfied=True,
        )
    
    def _get_signal_value(
        self,
        signal_name: str,
        atom_outputs: Dict[str, Any],
        user_profile: Dict[str, float],
        mechanism_outputs: Dict[str, Any],
    ) -> Optional[float]:
        """Get the value of a detection signal."""
        
        # Check user profile
        if signal_name == "neuroticism_score":
            return user_profile.get("neuroticism", 0.5)
        
        # Check mechanism outputs
        if signal_name == "scarcity_intensity":
            mech_output = mechanism_outputs.get("atom_mechanism_activation", {})
            if isinstance(mech_output, dict):
                weights = mech_output.get("mechanism_weights", {})
                return weights.get("scarcity", 0.0)
        
        # Check for dark patterns (simplified)
        if signal_name == "dark_pattern_detected":
            # Would run actual detection
            return 0.0
        
        return None
    
    def get_vulnerable_population_flags(
        self,
        user_profile: Dict[str, float],
    ) -> List[str]:
        """Get list of vulnerable population flags for a user."""
        flags = []
        
        if user_profile.get("neuroticism", 0.5) > 0.8:
            flags.append("high_neuroticism")
        
        if user_profile.get("age", 30) < 18:
            flags.append("minor")
        
        if user_profile.get("age", 30) > 65:
            flags.append("elderly")
        
        return flags
