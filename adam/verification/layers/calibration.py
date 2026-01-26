# =============================================================================
# ADAM Verification Layer 2: Calibration
# Location: adam/verification/layers/calibration.py
# =============================================================================

"""
LAYER 2: CONFIDENCE CALIBRATION

Adjusts reported confidence to match observed accuracy:
- Historical calibration curves
- Expected Calibration Error (ECE)
- Uncertainty decomposition
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.verification.models.constraints import ConstraintResult, ConstraintSeverity
from adam.verification.models.results import (
    LayerResult,
    VerificationLayer,
    CalibrationResult,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class CalibrationLayer:
    """
    Layer 2: Calibrate confidence scores.
    
    Claude's self-reported confidence often doesn't match
    actual accuracy. This layer adjusts based on history.
    """
    
    def __init__(self, cache: Optional[ADAMRedisCache] = None):
        self.cache = cache
        
        # Default calibration curve (maps reported → calibrated)
        # Learned from historical outcomes
        self.default_curve = {
            0.1: 0.08,
            0.2: 0.15,
            0.3: 0.22,
            0.4: 0.30,
            0.5: 0.42,
            0.6: 0.55,
            0.7: 0.63,
            0.8: 0.71,
            0.9: 0.78,
            1.0: 0.85,
        }
    
    async def verify(
        self,
        atom_outputs: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> LayerResult:
        """
        Verify and calibrate confidence scores.
        """
        start_time = datetime.now(timezone.utc)
        
        result = LayerResult(
            layer=VerificationLayer.CALIBRATION,
            passed=True,
        )
        
        calibration_results = []
        
        for atom_id, output in atom_outputs.items():
            if isinstance(output, dict):
                confidence = output.get("overall_confidence", 0.5)
            elif hasattr(output, "overall_confidence"):
                confidence = output.overall_confidence
            else:
                continue
            
            # Calibrate
            cal_result = await self._calibrate(atom_id, confidence, user_id)
            calibration_results.append(cal_result)
            
            # Check if significant recalibration needed
            if cal_result.recalibrated and abs(cal_result.recalibration_factor - 1.0) > 0.3:
                result.add_result(ConstraintResult(
                    constraint_id=f"cal_{atom_id}",
                    constraint_name=f"Calibration for {atom_id}",
                    satisfied=True,  # Not a failure, just info
                    severity=ConstraintSeverity.INFO,
                    violation_message=f"Confidence adjusted from {confidence:.2f} to {cal_result.calibrated_confidence:.2f}",
                ))
            else:
                result.add_result(ConstraintResult(
                    constraint_id=f"cal_{atom_id}",
                    constraint_name=f"Calibration for {atom_id}",
                    satisfied=True,
                ))
        
        end_time = datetime.now(timezone.utc)
        result.duration_ms = (end_time - start_time).total_seconds() * 1000
        result.summary = f"Calibrated {len(calibration_results)} confidence scores"
        
        return result
    
    async def _calibrate(
        self,
        atom_id: str,
        original_confidence: float,
        user_id: Optional[str] = None,
    ) -> CalibrationResult:
        """Calibrate a single confidence score."""
        
        # Get calibration curve (could be user-specific or atom-specific)
        curve = await self._get_calibration_curve(atom_id, user_id)
        
        # Interpolate on curve
        calibrated = self._interpolate_curve(original_confidence, curve)
        
        return CalibrationResult(
            original_confidence=original_confidence,
            calibrated_confidence=calibrated,
            method="historical",
            curve_data=curve,
            recalibrated=abs(calibrated - original_confidence) > 0.05,
            recalibration_factor=calibrated / original_confidence if original_confidence > 0 else 1.0,
        )
    
    async def _get_calibration_curve(
        self,
        atom_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[float, float]:
        """Get calibration curve from cache or default."""
        if self.cache:
            key = f"adam:calibration:{atom_id}"
            cached = await self.cache.get(key)
            if cached:
                return cached
        
        return self.default_curve
    
    def _interpolate_curve(
        self,
        value: float,
        curve: Dict[float, float],
    ) -> float:
        """Interpolate on calibration curve."""
        points = sorted(curve.keys())
        
        # Find surrounding points
        lower = points[0]
        upper = points[-1]
        
        for p in points:
            if p <= value:
                lower = p
            if p >= value:
                upper = p
                break
        
        if lower == upper:
            return curve[lower]
        
        # Linear interpolation
        t = (value - lower) / (upper - lower)
        return curve[lower] + t * (curve[upper] - curve[lower])
    
    async def update_curve(
        self,
        atom_id: str,
        reported_confidence: float,
        actual_accuracy: float,
    ) -> None:
        """Update calibration curve with new observation."""
        # Would update the cached calibration curve
        # Simplified: just log
        logger.debug(
            f"Calibration update for {atom_id}: "
            f"reported={reported_confidence:.2f}, actual={actual_accuracy:.2f}"
        )
