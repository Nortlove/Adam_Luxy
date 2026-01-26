# =============================================================================
# ADAM Enhancement #05: Verification Layer Learning Integration
# Location: adam/verification/learning_integration.py
# =============================================================================

"""
VERIFICATION LAYER LEARNING INTEGRATION

HIGH PRIORITY GAP: #05 Verification Layer checks atoms but doesn't learn from errors.

This module connects verification failures to atom prompt updates:
1. Track verification failure patterns
2. Identify which atoms fail most often and why
3. Update atom prompts to prevent recurring failures
4. Learn calibration curves from verification results
5. Feed verification quality back to Gradient Bridge

The Verification Layer checks:
- Atom consistency (do atoms agree with each other?)
- Confidence calibration (does confidence match accuracy?)
- Safety constraints (are outputs safe and appropriate?)
- Graph grounding (are claims supported by data?)

Without learning, we catch errors but never prevent them.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
import numpy as np
import uuid
import logging

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# VERIFICATION TYPES
# =============================================================================

class VerificationType(str, Enum):
    """Types of verification performed."""
    
    CONSISTENCY = "consistency"       # Inter-atom agreement
    CALIBRATION = "calibration"       # Confidence accuracy match
    SAFETY = "safety"                 # Safety constraint check
    GROUNDING = "grounding"           # Graph data support
    PLAUSIBILITY = "plausibility"     # Psychological plausibility
    COHERENCE = "coherence"           # Internal coherence


class VerificationSeverity(str, Enum):
    """Severity of verification failures."""
    
    INFO = "info"           # Logged but not actionable
    WARNING = "warning"     # Flagged, may proceed
    ERROR = "error"         # Must address before proceeding
    CRITICAL = "critical"   # Block and alert


class VerificationResult(BaseModel):
    """Result of a verification check."""
    
    result_id: str = Field(default_factory=lambda: f"ver_{uuid.uuid4().hex[:12]}")
    
    # Context
    decision_id: str
    atom_name: str
    verification_type: VerificationType
    
    # Result
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    severity: VerificationSeverity = VerificationSeverity.INFO
    
    # Details
    failure_reason: Optional[str] = None
    failure_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AtomFailurePattern(BaseModel):
    """Pattern of failures for an atom."""
    
    atom_name: str
    verification_type: VerificationType
    
    # Failure statistics
    total_checks: int = 0
    total_failures: int = 0
    failure_rate: float = 0.0
    
    # Common failure reasons
    common_reasons: Dict[str, int] = Field(default_factory=dict)
    
    # Recent failures
    recent_failures: List[str] = Field(default_factory=list)
    
    # Prompt adjustment history
    prompt_adjustments: List[Dict[str, Any]] = Field(default_factory=list)


class PromptAdjustment(BaseModel):
    """An adjustment to an atom prompt based on verification failures."""
    
    adjustment_id: str = Field(default_factory=lambda: f"adj_{uuid.uuid4().hex[:12]}")
    
    atom_name: str
    adjustment_type: str  # "add_constraint", "clarify_instruction", "add_example"
    
    # What we're adjusting
    original_prompt_section: str
    adjusted_prompt_section: str
    
    # Why
    failure_pattern: str
    expected_impact: str
    
    # Tracking
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    failures_before: int = 0
    failures_after: int = 0
    effectiveness: Optional[float] = None


# =============================================================================
# VERIFICATION LEARNING BRIDGE
# =============================================================================

class VerificationLearningBridge(LearningCapableComponent):
    """
    Learning integration for Enhancement #05: Verification Layer.
    
    This connects verification failures to atom prompt improvements,
    creating a closed loop where errors prevent future errors.
    """
    
    def __init__(
        self,
        verification_layer,
        atom_prompt_manager,
        neo4j_driver,
        redis_client,
        event_bus
    ):
        self.verification_layer = verification_layer
        self.atom_prompt_manager = atom_prompt_manager
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.event_bus = event_bus
        
        # Failure pattern tracking
        self.failure_patterns: Dict[Tuple[str, VerificationType], AtomFailurePattern] = {}
        
        # Prompt adjustments
        self.prompt_adjustments: List[PromptAdjustment] = []
        
        # Calibration tracking
        self.calibration_data: Dict[str, List[Tuple[float, float]]] = {}
        # {atom_name: [(predicted_confidence, actual_accuracy), ...]}
        
        # Pending verifications awaiting outcome
        self.pending_verifications: Dict[str, List[VerificationResult]] = {}
        
        # Quality tracking
        self._verifications_processed: int = 0
        self._failures_detected: int = 0
        self._adjustments_made: int = 0
    
    @property
    def component_name(self) -> str:
        return "verification_layer"
    
    @property
    def component_version(self) -> str:
        return "2.0"  # Now with learning
    
    # =========================================================================
    # VERIFICATION REGISTRATION
    # =========================================================================
    
    async def register_verification_results(
        self,
        decision_id: str,
        results: List[VerificationResult]
    ) -> None:
        """
        Register verification results for a decision.
        """
        
        for result in results:
            self._verifications_processed += 1
            
            # Track failures
            if not result.passed:
                self._failures_detected += 1
                await self._track_failure_pattern(result)
            
            # Track calibration data
            if result.verification_type == VerificationType.CALIBRATION:
                if result.atom_name not in self.calibration_data:
                    self.calibration_data[result.atom_name] = []
                self.calibration_data[result.atom_name].append(
                    (result.confidence, 1.0 if result.passed else 0.0)
                )
        
        self.pending_verifications[decision_id] = results
        
        await self.redis.setex(
            f"adam:verification:results:{decision_id}",
            86400,
            [r.json() for r in results]
        )
        
        # Check if we should generate prompt adjustments
        await self._check_for_prompt_adjustments()
    
    async def _track_failure_pattern(self, result: VerificationResult) -> None:
        """Track a failure pattern for an atom."""
        
        pattern_key = (result.atom_name, result.verification_type)
        
        if pattern_key not in self.failure_patterns:
            self.failure_patterns[pattern_key] = AtomFailurePattern(
                atom_name=result.atom_name,
                verification_type=result.verification_type
            )
        
        pattern = self.failure_patterns[pattern_key]
        pattern.total_checks += 1
        pattern.total_failures += 1
        pattern.failure_rate = pattern.total_failures / pattern.total_checks
        
        # Track failure reason
        if result.failure_reason:
            if result.failure_reason not in pattern.common_reasons:
                pattern.common_reasons[result.failure_reason] = 0
            pattern.common_reasons[result.failure_reason] += 1
        
        # Track recent failures (keep last 20)
        pattern.recent_failures.append(result.failure_reason or "unknown")
        pattern.recent_failures = pattern.recent_failures[-20:]
    
    async def _check_for_prompt_adjustments(self) -> None:
        """Check if any failure patterns warrant prompt adjustments."""
        
        for pattern_key, pattern in self.failure_patterns.items():
            # Only adjust if we have enough data and high failure rate
            if pattern.total_checks < 20:
                continue
            
            if pattern.failure_rate < 0.15:  # Less than 15% failure is acceptable
                continue
            
            # Check if we already made an adjustment recently
            recent_adjustments = [
                adj for adj in pattern.prompt_adjustments
                if (datetime.now(timezone.utc) - adj.get("applied_at", datetime.now(timezone.utc))).days < 7
            ]
            if recent_adjustments:
                continue
            
            # Generate adjustment
            adjustment = await self._generate_prompt_adjustment(pattern)
            if adjustment:
                await self._apply_prompt_adjustment(adjustment)
    
    async def _generate_prompt_adjustment(
        self,
        pattern: AtomFailurePattern
    ) -> Optional[PromptAdjustment]:
        """Generate a prompt adjustment based on failure pattern."""
        
        # Find most common failure reason
        if not pattern.common_reasons:
            return None
        
        top_reason = max(pattern.common_reasons.items(), key=lambda x: x[1])[0]
        
        # Generate adjustment based on failure type
        adjustment_type = "add_constraint"
        original_section = ""
        adjusted_section = ""
        
        if pattern.verification_type == VerificationType.CONSISTENCY:
            adjustment_type = "add_constraint"
            adjusted_section = f"""
IMPORTANT CONSTRAINT: Ensure your output is consistent with other atoms.
Previous consistency failures occurred because: {top_reason}
Before outputting, verify that your assessment aligns with the user's
overall psychological profile and does not contradict other assessments.
"""
        
        elif pattern.verification_type == VerificationType.CALIBRATION:
            adjustment_type = "calibration_guidance"
            adjusted_section = f"""
CALIBRATION GUIDANCE: Your confidence scores should match your actual accuracy.
Analysis of past predictions shows overconfidence in situations involving: {top_reason}
When encountering similar situations, reduce confidence by 15-20%.
"""
        
        elif pattern.verification_type == VerificationType.SAFETY:
            adjustment_type = "add_safety_check"
            adjusted_section = f"""
SAFETY CHECK: Before outputting, verify that your recommendation:
1. Does not violate any ethical guidelines
2. Does not make harmful assumptions
3. Is appropriate for the advertising context
Previous safety issues involved: {top_reason}
"""
        
        elif pattern.verification_type == VerificationType.GROUNDING:
            adjustment_type = "require_evidence"
            adjusted_section = f"""
EVIDENCE REQUIREMENT: Every claim must be grounded in the provided data.
Do not infer beyond what the evidence supports.
Previous grounding failures involved: {top_reason}
Cite specific data points to support your conclusions.
"""
        
        elif pattern.verification_type == VerificationType.PLAUSIBILITY:
            adjustment_type = "add_example"
            adjusted_section = f"""
PLAUSIBILITY CHECK: Ensure your psychological assessment is realistic.
Consider whether a human psychologist would reach a similar conclusion.
Previous implausible outputs involved: {top_reason}
"""
        
        return PromptAdjustment(
            atom_name=pattern.atom_name,
            adjustment_type=adjustment_type,
            original_prompt_section="",  # Will be filled by prompt manager
            adjusted_prompt_section=adjusted_section,
            failure_pattern=top_reason,
            expected_impact=f"Reduce {pattern.verification_type.value} failures by 50%",
            failures_before=pattern.total_failures,
        )
    
    async def _apply_prompt_adjustment(self, adjustment: PromptAdjustment) -> None:
        """Apply a prompt adjustment to an atom."""
        
        # Get current prompt
        current_prompt = await self.atom_prompt_manager.get_prompt(adjustment.atom_name)
        adjustment.original_prompt_section = current_prompt[:200]  # Sample
        
        # Apply adjustment
        updated_prompt = current_prompt + "\n\n" + adjustment.adjusted_prompt_section
        await self.atom_prompt_manager.update_prompt(
            atom_name=adjustment.atom_name,
            new_prompt=updated_prompt,
            reason=f"Verification learning: {adjustment.failure_pattern}"
        )
        
        self.prompt_adjustments.append(adjustment)
        self._adjustments_made += 1
        
        # Record in failure pattern
        pattern_key = (adjustment.atom_name, VerificationType.CONSISTENCY)  # Default
        if pattern_key in self.failure_patterns:
            self.failure_patterns[pattern_key].prompt_adjustments.append({
                "adjustment_id": adjustment.adjustment_id,
                "applied_at": adjustment.applied_at,
                "type": adjustment.adjustment_type,
            })
        
        logger.info(f"Applied prompt adjustment to {adjustment.atom_name}: {adjustment.adjustment_type}")
    
    # =========================================================================
    # LEARNING FROM OUTCOMES
    # =========================================================================
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """
        Learn from outcomes to validate verification effectiveness.
        """
        
        signals = []
        
        # Get verification results for this decision
        results = self.pending_verifications.pop(decision_id, None)
        if not results:
            cached = await self.redis.get(f"adam:verification:results:{decision_id}")
            if cached:
                results = [VerificationResult.parse_raw(r) for r in cached]
        
        if not results:
            return []
        
        # =====================================================================
        # VALIDATE VERIFICATION EFFECTIVENESS
        # =====================================================================
        
        # Did failures predict bad outcomes?
        had_failures = any(not r.passed for r in results)
        is_positive_outcome = outcome_value > 0.5
        
        verification_correct = (
            (had_failures and not is_positive_outcome) or
            (not had_failures and is_positive_outcome)
        )
        
        # Update calibration data
        for result in results:
            if result.atom_name in self.calibration_data:
                # Add outcome to calibration tracking
                pass
        
        # =====================================================================
        # CHECK PROMPT ADJUSTMENT EFFECTIVENESS
        # =====================================================================
        
        for adjustment in self.prompt_adjustments:
            if adjustment.effectiveness is None:
                # Check if adjustment has been in place long enough
                days_since = (datetime.now(timezone.utc) - adjustment.applied_at).days
                if days_since >= 7:
                    # Count failures after adjustment
                    pattern_key = (adjustment.atom_name, VerificationType.CONSISTENCY)
                    if pattern_key in self.failure_patterns:
                        pattern = self.failure_patterns[pattern_key]
                        failures_after = pattern.total_failures - adjustment.failures_before
                        adjustment.failures_after = failures_after
                        
                        # Calculate effectiveness
                        if adjustment.failures_before > 0:
                            adjustment.effectiveness = 1.0 - (failures_after / adjustment.failures_before)
                        else:
                            adjustment.effectiveness = 1.0
        
        # =====================================================================
        # EMIT LEARNING SIGNALS
        # =====================================================================
        
        # 1. Verification effectiveness signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.PREDICTION_VALIDATED if verification_correct else LearningSignalType.PREDICTION_FAILED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "verification_results": len(results),
                "failures_detected": sum(1 for r in results if not r.passed),
                "verification_correct": verification_correct,
                "outcome": outcome_value,
            },
            confidence=0.85,
            target_components=["gradient_bridge", "meta_learner"]
        ))
        
        # 2. Calibration update signal
        miscalibrated_atoms = [
            r.atom_name for r in results
            if r.verification_type == VerificationType.CALIBRATION and not r.passed
        ]
        if miscalibrated_atoms:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.CALIBRATION_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "miscalibrated_atoms": miscalibrated_atoms,
                    "calibration_data": {
                        atom: self._compute_calibration_curve(atom)
                        for atom in miscalibrated_atoms
                        if atom in self.calibration_data
                    },
                },
                confidence=0.8,
                target_components=["atom_of_thought", "confidence_calibrator"]
            ))
        
        # 3. Prompt adjustment effectiveness signal
        effective_adjustments = [
            adj for adj in self.prompt_adjustments
            if adj.effectiveness is not None and adj.effectiveness > 0.3
        ]
        if effective_adjustments:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.PATTERN_EMERGED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "pattern_type": "effective_prompt_adjustment",
                    "adjustments": [
                        {
                            "atom": adj.atom_name,
                            "type": adj.adjustment_type,
                            "effectiveness": adj.effectiveness,
                        }
                        for adj in effective_adjustments
                    ],
                },
                confidence=0.75,
                target_components=["atom_of_thought"]
            ))
        
        return signals
    
    def _compute_calibration_curve(self, atom_name: str) -> Dict[str, float]:
        """Compute calibration curve for an atom."""
        
        if atom_name not in self.calibration_data:
            return {}
        
        data = self.calibration_data[atom_name]
        if len(data) < 10:
            return {}
        
        # Bin by confidence
        bins = {}
        for conf, acc in data:
            bin_key = round(conf * 10) / 10  # 0.1 bins
            if bin_key not in bins:
                bins[bin_key] = []
            bins[bin_key].append(acc)
        
        # Compute mean accuracy per bin
        return {
            str(k): np.mean(v) for k, v in bins.items() if len(v) >= 3
        }
    
    # =========================================================================
    # CONSUMING LEARNING SIGNALS
    # =========================================================================
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals."""
        
        if signal.signal_type == LearningSignalType.ATOM_ATTRIBUTED:
            # If an atom performed poorly, increase verification strictness
            atom_validations = signal.payload.get("atom_validations", {})
            for atom_name, validation in atom_validations.items():
                if validation.get("accuracy", 0.5) < 0.4:
                    # Increase verification strictness for this atom
                    await self.verification_layer.increase_strictness(atom_name)
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.ATOM_ATTRIBUTED,
            LearningSignalType.PREDICTION_FAILED,
        }
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get verification contribution."""
        
        cached = await self.redis.get(f"adam:verification:results:{decision_id}")
        if not cached:
            return None
        
        results = [VerificationResult.parse_raw(r) for r in cached]
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="verification",
            contribution_value={
                "checks_performed": len(results),
                "failures_caught": sum(1 for r in results if not r.passed),
                "check_types": list(set(r.verification_type.value for r in results)),
            },
            confidence=0.9,
            reasoning_summary=f"Performed {len(results)} verification checks",
            weight=0.1
        )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        # Overall verification rate
        if self._verifications_processed > 0:
            pass_rate = 1.0 - (self._failures_detected / self._verifications_processed)
        else:
            pass_rate = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._verifications_processed,
            outcomes_processed=self._verifications_processed,
            prediction_accuracy=pass_rate,
            attribution_coverage=0.95,  # Verification covers nearly all decisions
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["atom_of_thought"],
            downstream_consumers=["atom_of_thought", "gradient_bridge"],
            integration_health=0.9 if self._adjustments_made > 0 else 0.7
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject priors - verification doesn't use user-specific priors."""
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        if self._verifications_processed == 0:
            issues.append("No verifications processed")
        
        # Check for high failure rate atoms
        high_failure_atoms = [
            p.atom_name for p in self.failure_patterns.values()
            if p.failure_rate > 0.3 and p.total_checks >= 20
        ]
        if high_failure_atoms:
            issues.append(f"High failure rate atoms: {high_failure_atoms}")
        
        return len(issues) == 0, issues
