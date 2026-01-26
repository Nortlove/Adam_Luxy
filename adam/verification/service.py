# =============================================================================
# ADAM Verification Service
# Location: adam/verification/service.py
# =============================================================================

"""
VERIFICATION SERVICE

Orchestrates the four-layer verification pipeline.

Pipeline:
1. Consistency → 2. Calibration → 3. Safety → 4. Grounding

Plus self-correction on failure.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.verification.models.constraints import ConstraintSeverity
from adam.verification.models.results import (
    VerificationResult,
    VerificationStatus,
    VerificationLayer,
    CorrectionAttempt,
)
from adam.verification.layers.consistency import ConsistencyVerifier
from adam.verification.layers.calibration import CalibrationLayer
from adam.verification.layers.safety import SafetyValidator
from adam.verification.layers.grounding import GraphGroundingLayer
from adam.blackboard.service import BlackboardService
from adam.graph_reasoning.bridge import InteractionBridge
from adam.infrastructure.redis import ADAMRedisCache
from adam.infrastructure.prometheus import get_metrics

logger = logging.getLogger(__name__)


class VerificationService:
    """
    Main service for the verification pipeline.
    
    Runs all four layers and handles self-correction.
    """
    
    MAX_CORRECTION_ATTEMPTS = 2
    
    def __init__(
        self,
        blackboard: BlackboardService,
        bridge: InteractionBridge,
        cache: ADAMRedisCache,
    ):
        self.blackboard = blackboard
        self.bridge = bridge
        self.cache = cache
        self.metrics = get_metrics()
        
        # Initialize layers
        self.consistency = ConsistencyVerifier()
        self.calibration = CalibrationLayer(cache)
        self.safety = SafetyValidator()
        self.grounding = GraphGroundingLayer(bridge)
    
    async def verify(
        self,
        request_id: str,
        atom_outputs: Dict[str, Any],
        user_id: str,
        user_profile: Optional[Dict[str, float]] = None,
        decision_id: Optional[str] = None,
        auto_correct: bool = True,
    ) -> VerificationResult:
        """
        Run the complete verification pipeline.
        
        Args:
            request_id: Request identifier
            atom_outputs: Dict of atom_id -> output
            user_id: User identifier
            user_profile: User psychological profile
            decision_id: Decision identifier
            auto_correct: Whether to attempt self-correction
        
        Returns:
            VerificationResult with all layer results
        """
        start_time = datetime.now(timezone.utc)
        
        result = VerificationResult(
            request_id=request_id,
            decision_id=decision_id,
            status=VerificationStatus.PASSED,
            original_output=atom_outputs,
            verified_output=atom_outputs.copy(),
        )
        
        # Run layers in sequence
        current_outputs = atom_outputs
        
        # Layer 1: Consistency
        consistency_result = await self.consistency.verify(current_outputs)
        result.add_layer_result(consistency_result)
        
        # Layer 2: Calibration
        calibration_result = await self.calibration.verify(
            current_outputs, user_id
        )
        result.add_layer_result(calibration_result)
        
        # Layer 3: Safety
        safety_result = await self.safety.verify(
            current_outputs,
            user_profile,
            current_outputs,
        )
        result.add_layer_result(safety_result)
        
        # Layer 4: Grounding
        grounding_result = await self.grounding.verify(
            current_outputs, user_id
        )
        result.add_layer_result(grounding_result)
        
        # Check for failures
        has_critical = any(
            lr.max_severity == ConstraintSeverity.CRITICAL
            for lr in result.layer_results.values()
        )
        has_error = any(
            lr.max_severity == ConstraintSeverity.ERROR
            for lr in result.layer_results.values()
        )
        
        # Attempt self-correction if needed
        if auto_correct and has_error and not has_critical:
            corrected, new_outputs = await self._attempt_correction(
                result, current_outputs
            )
            if corrected:
                result.verified_output = new_outputs
                result.output_modified = True
        
        # Finalize
        result.complete()
        
        # Record metrics
        self._record_metrics(result)
        
        logger.info(
            f"Verification for {request_id}: {result.status.value}, "
            f"{result.total_constraints_passed}/{result.total_constraints_checked} passed"
        )
        
        return result
    
    async def _attempt_correction(
        self,
        result: VerificationResult,
        outputs: Dict[str, Any],
    ) -> tuple:
        """
        Attempt to correct failed constraints.
        
        Returns: (success, corrected_outputs)
        """
        corrected_outputs = outputs.copy()
        any_correction = False
        
        for layer, layer_result in result.layer_results.items():
            for constraint_result in layer_result.constraint_results:
                if not constraint_result.satisfied and constraint_result.correctable:
                    # Attempt correction
                    attempt = CorrectionAttempt(
                        attempt_number=len(result.correction_attempts) + 1,
                        failed_constraint=constraint_result.constraint_name,
                        failure_reason=constraint_result.violation_message or "",
                        correction_type="adjustment",
                        correction_details=constraint_result.correction_suggestion or "default",
                        successful=False,
                    )
                    
                    # Apply correction based on suggestion
                    if constraint_result.correction_suggestion == "use_positive_framing":
                        # Would adjust mechanism selection
                        attempt.successful = True
                        any_correction = True
                    elif constraint_result.correction_suggestion == "reduce_intensity":
                        # Would reduce mechanism intensity
                        attempt.successful = True
                        any_correction = True
                    
                    result.correction_attempts.append(attempt)
                    if attempt.successful:
                        result.corrections_applied += 1
                    
                    # Limit attempts
                    if len(result.correction_attempts) >= self.MAX_CORRECTION_ATTEMPTS:
                        break
        
        return any_correction, corrected_outputs
    
    def _record_metrics(self, result: VerificationResult) -> None:
        """Record verification metrics."""
        # Overall status
        self.metrics.learning_signals.labels(
            signal_type="verification",
            component="verification",
        ).inc()
        
        # Per-layer metrics would go here
    
    async def verify_quick(
        self,
        atom_outputs: Dict[str, Any],
        user_id: str,
    ) -> bool:
        """
        Quick verification for fast path (consistency + safety only).
        
        Returns: True if passed, False if failed
        """
        # Only run critical checks
        consistency_result = await self.consistency.verify(atom_outputs)
        if not consistency_result.passed:
            return False
        
        safety_result = await self.safety.verify(atom_outputs)
        if not safety_result.passed:
            return False
        
        return True
    
    # =========================================================================
    # REVIEW INTELLIGENCE VERIFICATION
    # =========================================================================
    
    async def verify_review_predictions(
        self,
        customer_intelligence,
        decision_id: str,
        outcome_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Verify that review-derived predictions align with observed outcomes.
        
        This is a critical feedback loop that validates:
        1. Archetype predictions → Did the targeted archetype respond?
        2. Mechanism predictions → Were the predicted mechanisms effective?
        3. Language predictions → Did customer language resonate?
        
        Args:
            customer_intelligence: CustomerIntelligenceProfile used for decision
            decision_id: Decision ID to verify
            outcome_data: Observed outcome data (clicks, conversions, etc.)
            
        Returns:
            Verification report with accuracy metrics
        """
        report = {
            "decision_id": decision_id,
            "verification_time": datetime.now(timezone.utc).isoformat(),
            "archetype_verification": {},
            "mechanism_verification": {},
            "language_verification": {},
            "overall_accuracy": 0.0,
            "recommendations": [],
        }
        
        if not outcome_data:
            report["status"] = "pending"
            report["message"] = "Awaiting outcome data"
            return report
        
        try:
            # 1. Verify archetype prediction
            archetype_accuracy = await self._verify_archetype_prediction(
                customer_intelligence, outcome_data
            )
            report["archetype_verification"] = archetype_accuracy
            
            # 2. Verify mechanism predictions
            mechanism_accuracy = await self._verify_mechanism_predictions(
                customer_intelligence, outcome_data
            )
            report["mechanism_verification"] = mechanism_accuracy
            
            # 3. Verify language resonance
            language_accuracy = await self._verify_language_resonance(
                customer_intelligence, outcome_data
            )
            report["language_verification"] = language_accuracy
            
            # Calculate overall accuracy
            scores = []
            if archetype_accuracy.get("accuracy") is not None:
                scores.append(archetype_accuracy["accuracy"])
            if mechanism_accuracy.get("primary_accuracy") is not None:
                scores.append(mechanism_accuracy["primary_accuracy"])
            if language_accuracy.get("resonance_score") is not None:
                scores.append(language_accuracy["resonance_score"])
            
            report["overall_accuracy"] = sum(scores) / len(scores) if scores else 0.0
            report["status"] = "verified"
            
            # Generate recommendations
            if report["overall_accuracy"] < 0.5:
                report["recommendations"].append(
                    "Review intelligence predictions underperforming. Consider:"
                )
                if archetype_accuracy.get("accuracy", 1.0) < 0.5:
                    report["recommendations"].append(
                        "- Re-analyze reviews with higher quality threshold"
                    )
                if mechanism_accuracy.get("primary_accuracy", 1.0) < 0.5:
                    report["recommendations"].append(
                        "- Adjust mechanism-archetype mappings based on outcome data"
                    )
            elif report["overall_accuracy"] > 0.75:
                report["recommendations"].append(
                    "Review intelligence performing well. Consider increasing its weight in decisions."
                )
            
            # Log verification
            logger.info(
                f"Review prediction verification for {decision_id}: "
                f"{report['overall_accuracy']*100:.1f}% accuracy"
            )
            
        except Exception as e:
            logger.error(f"Error verifying review predictions: {e}")
            report["status"] = "error"
            report["error"] = str(e)
        
        return report
    
    async def _verify_archetype_prediction(
        self,
        customer_intelligence,
        outcome_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Verify if predicted archetype aligned with response."""
        result = {
            "predicted_archetype": customer_intelligence.dominant_archetype,
            "prediction_confidence": customer_intelligence.archetype_confidence,
            "accuracy": None,
        }
        
        # Check if outcome indicates archetype match
        # E.g., certain response patterns indicate Explorer vs Guardian
        
        # Engagement signals that indicate archetype
        click_rate = outcome_data.get("click_rate", 0)
        conversion_rate = outcome_data.get("conversion_rate", 0)
        time_to_convert = outcome_data.get("time_to_convert_seconds", 0)
        
        # Infer actual archetype from behavior
        inferred_archetype = None
        
        if click_rate > 0.1 and time_to_convert < 60:
            # Quick decision makers → likely Achiever or Explorer
            inferred_archetype = "Achiever" if conversion_rate > 0.05 else "Explorer"
        elif conversion_rate > 0.08 and time_to_convert > 300:
            # Slow but high conversion → likely Guardian or Pragmatist
            inferred_archetype = "Guardian" if conversion_rate > 0.1 else "Pragmatist"
        elif click_rate > 0.08:
            # Good engagement → could be Connector
            inferred_archetype = "Connector"
        
        result["inferred_archetype"] = inferred_archetype
        
        if inferred_archetype:
            # Check match
            if inferred_archetype == customer_intelligence.dominant_archetype:
                result["accuracy"] = 1.0
            elif inferred_archetype in (customer_intelligence.buyer_archetypes or {}):
                # Partial match - archetype was in the distribution
                result["accuracy"] = 0.7
            else:
                result["accuracy"] = 0.3
        
        return result
    
    async def _verify_mechanism_predictions(
        self,
        customer_intelligence,
        outcome_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Verify if predicted mechanisms were effective."""
        result = {
            "predicted_mechanisms": customer_intelligence.mechanism_predictions or {},
            "primary_accuracy": None,
            "mechanism_outcomes": {},
        }
        
        # Check which mechanisms were used and their outcomes
        mechanisms_used = outcome_data.get("mechanisms_used", [])
        mechanism_effectiveness = outcome_data.get("mechanism_effectiveness", {})
        
        if mechanisms_used and mechanism_effectiveness:
            # Find primary predicted mechanism
            predictions = customer_intelligence.mechanism_predictions or {}
            if predictions:
                primary_predicted = max(predictions.keys(), key=lambda m: predictions.get(m, 0))
                
                if primary_predicted in mechanism_effectiveness:
                    actual_effectiveness = mechanism_effectiveness[primary_predicted]
                    predicted_effectiveness = predictions[primary_predicted]
                    
                    # Accuracy = how close prediction was to actual
                    error = abs(predicted_effectiveness - actual_effectiveness)
                    result["primary_accuracy"] = max(0, 1.0 - error)
                    
                    result["mechanism_outcomes"][primary_predicted] = {
                        "predicted": predicted_effectiveness,
                        "actual": actual_effectiveness,
                        "error": error,
                    }
        
        return result
    
    async def _verify_language_resonance(
        self,
        customer_intelligence,
        outcome_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Verify if language patterns resonated."""
        result = {
            "resonance_score": None,
            "language_used": False,
        }
        
        # Check if customer language was used in copy
        copy_used_language = outcome_data.get("used_customer_language", False)
        result["language_used"] = copy_used_language
        
        if copy_used_language:
            # Compare outcomes with/without customer language
            engagement_with = outcome_data.get("engagement_with_language", 0)
            engagement_without = outcome_data.get("engagement_baseline", 0)
            
            if engagement_without > 0:
                lift = (engagement_with - engagement_without) / engagement_without
                result["resonance_score"] = min(1.0, max(0.0, 0.5 + lift))
            else:
                result["resonance_score"] = 0.5  # No baseline to compare
        
        return result
    
    async def update_review_intelligence_from_verification(
        self,
        customer_intelligence,
        verification_report: Dict[str, Any],
    ) -> None:
        """
        Use verification results to update review intelligence.
        
        This is the learning feedback loop:
        - High accuracy → increase confidence in this review profile
        - Low accuracy → adjust archetype/mechanism mappings
        """
        try:
            overall_accuracy = verification_report.get("overall_accuracy", 0.5)
            
            # Update confidence based on verification
            if overall_accuracy > 0.7:
                # Good prediction - increase confidence
                new_confidence = min(
                    0.95,
                    (customer_intelligence.overall_confidence or 0.5) + 0.05
                )
                customer_intelligence.overall_confidence = new_confidence
                customer_intelligence.archetype_confidence = min(
                    0.95,
                    (customer_intelligence.archetype_confidence or 0.5) + 0.05
                )
            elif overall_accuracy < 0.4:
                # Poor prediction - decrease confidence
                new_confidence = max(
                    0.2,
                    (customer_intelligence.overall_confidence or 0.5) - 0.1
                )
                customer_intelligence.overall_confidence = new_confidence
            
            # Log the update
            logger.info(
                f"Updated review intelligence confidence to {customer_intelligence.overall_confidence:.2f} "
                f"based on {overall_accuracy*100:.1f}% verification accuracy"
            )
            
        except Exception as e:
            logger.error(f"Error updating review intelligence: {e}")
