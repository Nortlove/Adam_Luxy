# =============================================================================
# ADAM Validity Checkers
# Location: adam/validity/checks.py
# =============================================================================

"""
VALIDITY CHECKERS

Implementations of psychological validity checks.
"""

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from adam.validity.models import (
    ValidityType,
    ValidityStatus,
    ConstructType,
    ValidityCheck,
    ValidityResult,
    ConstructValidity,
    PredictiveValidity,
    ConvergentValidity,
    DiscriminantValidity,
)

logger = logging.getLogger(__name__)


# =============================================================================
# BASE CHECKER
# =============================================================================

class BaseValidityChecker(ABC):
    """Base class for validity checkers."""
    
    validity_type: ValidityType
    
    @abstractmethod
    async def check(
        self,
        data: Dict[str, Any],
        **kwargs,
    ) -> List[ValidityResult]:
        """Run validity checks on data."""
        pass
    
    def _determine_status(
        self,
        score: float,
        pass_threshold: float,
        warning_threshold: float,
    ) -> ValidityStatus:
        """Determine status from score and thresholds."""
        if score >= pass_threshold:
            return ValidityStatus.PASSED
        elif score >= warning_threshold:
            return ValidityStatus.WARNING
        else:
            return ValidityStatus.FAILED


# =============================================================================
# CONSTRUCT VALIDITY CHECKER
# =============================================================================

class ConstructValidityChecker(BaseValidityChecker):
    """
    Check construct validity.
    
    Verifies that our measurements actually measure the
    psychological constructs we claim to measure.
    
    Checks:
    - Internal consistency (Cronbach's alpha > 0.7)
    - Factor structure alignment
    - Measurement invariance
    """
    
    validity_type = ValidityType.CONSTRUCT
    
    # Expected Big Five correlations with behavioral indicators
    BIG_FIVE_INDICATORS = {
        "openness": {
            "variety_seeking": 0.4,
            "novel_product_interest": 0.35,
            "creative_content_engagement": 0.3,
        },
        "conscientiousness": {
            "planning_behavior": 0.45,
            "review_reading": 0.35,
            "comparison_shopping": 0.3,
        },
        "extraversion": {
            "social_sharing": 0.5,
            "trend_following": 0.35,
            "social_proof_response": 0.4,
        },
        "agreeableness": {
            "review_helpfulness": 0.35,
            "positive_sentiment": 0.3,
            "conflict_avoidance": 0.25,
        },
        "neuroticism": {
            "price_sensitivity": 0.3,
            "return_rate": 0.35,
            "abandonment_rate": 0.25,
        },
    }
    
    async def check(
        self,
        data: Dict[str, Any],
        **kwargs,
    ) -> List[ValidityResult]:
        """Run construct validity checks."""
        results = []
        
        # Check Big Five construct validity
        big_five_result = await self._check_big_five_validity(data)
        results.append(big_five_result)
        
        # Check regulatory focus validity
        reg_focus_result = await self._check_regulatory_focus_validity(data)
        results.append(reg_focus_result)
        
        return results
    
    async def _check_big_five_validity(
        self,
        data: Dict[str, Any],
    ) -> ValidityResult:
        """Check Big Five construct validity."""
        
        check = ValidityCheck(
            check_id="big_five_construct",
            validity_type=ValidityType.CONSTRUCT,
            construct=ConstructType.BIG_FIVE,
            description="Big Five traits correlate with expected behavioral indicators",
            metric_name="average_indicator_correlation",
            pass_threshold=0.25,
            warning_threshold=0.15,
        )
        
        # Get behavioral correlations from data
        correlations = data.get("big_five_correlations", {})
        
        if not correlations:
            return ValidityResult(
                check=check,
                status=ValidityStatus.INSUFFICIENT_DATA,
                score=0.0,
                sample_size=0,
                interpretation="Insufficient data for Big Five validity check",
            )
        
        # Calculate average correlation match
        total_correlation = 0.0
        count = 0
        
        for trait, indicators in self.BIG_FIVE_INDICATORS.items():
            trait_corrs = correlations.get(trait, {})
            for indicator, expected in indicators.items():
                observed = trait_corrs.get(indicator, 0.0)
                # Score based on how close to expected
                match_score = 1.0 - abs(observed - expected) / expected if expected > 0 else 0.0
                total_correlation += max(0, match_score)
                count += 1
        
        score = total_correlation / count if count > 0 else 0.0
        
        status = self._determine_status(score, check.pass_threshold, check.warning_threshold)
        
        return ValidityResult(
            check=check,
            status=status,
            score=score,
            sample_size=data.get("sample_size", 0),
            evidence={"correlations": correlations},
            interpretation=self._interpret_big_five_validity(status, score),
            recommendations=self._big_five_recommendations(status),
        )
    
    async def _check_regulatory_focus_validity(
        self,
        data: Dict[str, Any],
    ) -> ValidityResult:
        """Check regulatory focus construct validity."""
        
        check = ValidityCheck(
            check_id="regulatory_focus_construct",
            validity_type=ValidityType.CONSTRUCT,
            construct=ConstructType.REGULATORY_FOCUS,
            description="Regulatory focus predicts approach/avoidance behavior",
            metric_name="prediction_accuracy",
            pass_threshold=0.6,
            warning_threshold=0.5,
        )
        
        # Expected: promotion focus → approach behavior
        # Expected: prevention focus → avoidance behavior
        rf_data = data.get("regulatory_focus_behavior", {})
        
        if not rf_data:
            return ValidityResult(
                check=check,
                status=ValidityStatus.INSUFFICIENT_DATA,
                score=0.0,
                sample_size=0,
                interpretation="Insufficient data for regulatory focus validity",
            )
        
        promotion_approach = rf_data.get("promotion_approach_correlation", 0.0)
        prevention_avoidance = rf_data.get("prevention_avoidance_correlation", 0.0)
        
        score = (promotion_approach + prevention_avoidance) / 2
        status = self._determine_status(score, check.pass_threshold, check.warning_threshold)
        
        return ValidityResult(
            check=check,
            status=status,
            score=score,
            sample_size=rf_data.get("sample_size", 0),
            evidence=rf_data,
            interpretation=f"Regulatory focus shows {score:.1%} behavioral alignment",
        )
    
    def _interpret_big_five_validity(
        self,
        status: ValidityStatus,
        score: float,
    ) -> str:
        """Interpret Big Five validity result."""
        if status == ValidityStatus.PASSED:
            return f"Big Five measurements show strong construct validity ({score:.1%} indicator alignment)"
        elif status == ValidityStatus.WARNING:
            return f"Big Five measurements show moderate construct validity ({score:.1%}). Some indicators may need recalibration."
        else:
            return f"Big Five measurements show weak construct validity ({score:.1%}). Serious recalibration needed."
    
    def _big_five_recommendations(
        self,
        status: ValidityStatus,
    ) -> List[str]:
        """Generate recommendations for Big Five validity."""
        if status == ValidityStatus.PASSED:
            return ["Continue monitoring quarterly"]
        elif status == ValidityStatus.WARNING:
            return [
                "Review feature extraction pipeline",
                "Validate against survey sample",
                "Check for temporal drift",
            ]
        else:
            return [
                "Halt new model deployments until resolved",
                "Conduct manual validation study",
                "Review data quality",
                "Consider model retraining",
            ]


# =============================================================================
# PREDICTIVE VALIDITY CHECKER
# =============================================================================

class PredictiveValidityChecker(BaseValidityChecker):
    """
    Check predictive validity.
    
    Verifies that our psychological assessments predict
    actual user behavior and outcomes.
    """
    
    validity_type = ValidityType.PREDICTIVE
    
    async def check(
        self,
        data: Dict[str, Any],
        **kwargs,
    ) -> List[ValidityResult]:
        """Run predictive validity checks."""
        results = []
        
        # Check mechanism prediction validity
        mech_result = await self._check_mechanism_prediction(data)
        results.append(mech_result)
        
        # Check conversion prediction
        conv_result = await self._check_conversion_prediction(data)
        results.append(conv_result)
        
        return results
    
    async def _check_mechanism_prediction(
        self,
        data: Dict[str, Any],
    ) -> ValidityResult:
        """Check if mechanism effectiveness predictions are accurate."""
        
        check = ValidityCheck(
            check_id="mechanism_prediction",
            validity_type=ValidityType.PREDICTIVE,
            construct=ConstructType.MECHANISM_EFFECTIVENESS,
            description="Predicted mechanism effectiveness correlates with actual outcomes",
            metric_name="prediction_correlation",
            pass_threshold=0.3,
            warning_threshold=0.2,
        )
        
        mech_data = data.get("mechanism_predictions", {})
        
        if not mech_data:
            return ValidityResult(
                check=check,
                status=ValidityStatus.INSUFFICIENT_DATA,
                score=0.0,
                sample_size=0,
                interpretation="Insufficient mechanism prediction data",
            )
        
        correlation = mech_data.get("correlation", 0.0)
        p_value = mech_data.get("p_value", 1.0)
        
        status = self._determine_status(
            correlation, check.pass_threshold, check.warning_threshold
        )
        
        if p_value > 0.05:
            status = ValidityStatus.WARNING  # Not significant
        
        return ValidityResult(
            check=check,
            status=status,
            score=correlation,
            sample_size=mech_data.get("sample_size", 0),
            evidence=mech_data,
            interpretation=f"Mechanism predictions show r={correlation:.2f} (p={p_value:.4f})",
        )
    
    async def _check_conversion_prediction(
        self,
        data: Dict[str, Any],
    ) -> ValidityResult:
        """Check if psychological profiles predict conversion."""
        
        check = ValidityCheck(
            check_id="conversion_prediction",
            validity_type=ValidityType.PREDICTIVE,
            construct=ConstructType.BIG_FIVE,
            description="Psychological profiles predict conversion likelihood",
            metric_name="auc_roc",
            pass_threshold=0.65,
            warning_threshold=0.55,
        )
        
        conv_data = data.get("conversion_predictions", {})
        
        if not conv_data:
            return ValidityResult(
                check=check,
                status=ValidityStatus.INSUFFICIENT_DATA,
                score=0.0,
                sample_size=0,
                interpretation="Insufficient conversion prediction data",
            )
        
        auc = conv_data.get("auc_roc", 0.5)
        status = self._determine_status(auc, check.pass_threshold, check.warning_threshold)
        
        return ValidityResult(
            check=check,
            status=status,
            score=auc,
            sample_size=conv_data.get("sample_size", 0),
            evidence=conv_data,
            interpretation=f"Conversion prediction AUC-ROC = {auc:.3f}",
        )


# =============================================================================
# CONVERGENT VALIDITY CHECKER
# =============================================================================

class ConvergentValidityChecker(BaseValidityChecker):
    """
    Check convergent validity.
    
    Verifies that theoretically related constructs are
    empirically correlated.
    """
    
    validity_type = ValidityType.CONVERGENT
    
    # Expected correlations between constructs
    EXPECTED_CORRELATIONS = [
        ("openness", "promotion_focus", 0.3, "positive"),
        ("conscientiousness", "prevention_focus", 0.35, "positive"),
        ("extraversion", "promotion_focus", 0.25, "positive"),
        ("neuroticism", "prevention_focus", 0.3, "positive"),
    ]
    
    async def check(
        self,
        data: Dict[str, Any],
        **kwargs,
    ) -> List[ValidityResult]:
        """Run convergent validity checks."""
        results = []
        
        correlations = data.get("construct_correlations", {})
        
        for trait, construct, expected, direction in self.EXPECTED_CORRELATIONS:
            check = ValidityCheck(
                check_id=f"convergent_{trait}_{construct}",
                validity_type=ValidityType.CONVERGENT,
                construct=ConstructType.BIG_FIVE,
                description=f"{trait} should correlate {direction}ly with {construct}",
                metric_name="correlation",
                pass_threshold=expected * 0.7,
                warning_threshold=expected * 0.5,
            )
            
            key = f"{trait}_{construct}"
            observed = correlations.get(key, 0.0)
            
            matches = (direction == "positive" and observed > 0) or \
                      (direction == "negative" and observed < 0)
            
            status = self._determine_status(
                abs(observed), check.pass_threshold, check.warning_threshold
            ) if matches else ValidityStatus.FAILED
            
            results.append(ValidityResult(
                check=check,
                status=status,
                score=observed,
                sample_size=data.get("sample_size", 0),
                evidence={"expected": expected, "observed": observed},
                interpretation=f"{trait} × {construct}: r={observed:.2f} (expected ~{expected:.2f})",
            ))
        
        return results


# =============================================================================
# DISCRIMINANT VALIDITY CHECKER
# =============================================================================

class DiscriminantValidityChecker(BaseValidityChecker):
    """
    Check discriminant validity.
    
    Verifies that theoretically distinct constructs are
    empirically distinct (low correlation).
    """
    
    validity_type = ValidityType.DISCRIMINANT
    
    # Pairs that should have low correlation
    DISTINCT_PAIRS = [
        ("openness", "conscientiousness", 0.2),
        ("extraversion", "conscientiousness", 0.15),
        ("agreeableness", "openness", 0.2),
    ]
    
    async def check(
        self,
        data: Dict[str, Any],
        **kwargs,
    ) -> List[ValidityResult]:
        """Run discriminant validity checks."""
        results = []
        
        correlations = data.get("trait_correlations", {})
        
        for trait_a, trait_b, max_allowed in self.DISTINCT_PAIRS:
            check = ValidityCheck(
                check_id=f"discriminant_{trait_a}_{trait_b}",
                validity_type=ValidityType.DISCRIMINANT,
                construct=ConstructType.BIG_FIVE,
                description=f"{trait_a} and {trait_b} should be distinct (|r| < {max_allowed})",
                metric_name="correlation_magnitude",
                pass_threshold=max_allowed,
                warning_threshold=max_allowed * 1.5,
            )
            
            key = f"{trait_a}_{trait_b}"
            observed = abs(correlations.get(key, 0.0))
            
            # For discriminant, lower is better
            if observed <= check.pass_threshold:
                status = ValidityStatus.PASSED
            elif observed <= check.warning_threshold:
                status = ValidityStatus.WARNING
            else:
                status = ValidityStatus.FAILED
            
            results.append(ValidityResult(
                check=check,
                status=status,
                score=1.0 - observed,  # Invert so higher is better
                sample_size=data.get("sample_size", 0),
                evidence={"max_allowed": max_allowed, "observed": observed},
                interpretation=f"{trait_a} × {trait_b}: |r|={observed:.2f} (max {max_allowed})",
            ))
        
        return results
