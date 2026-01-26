# =============================================================================
# ADAM Behavioral Analytics: Memory Optimizer
# Location: adam/behavioral_analytics/classifiers/memory_optimizer.py
# =============================================================================

"""
MEMORY OPTIMIZER

Optimizes ad exposure timing based on memory research:
1. Spacing Effect - Up to 150% improvement with distributed scheduling
2. Peak-End Rule - Invest 70% in peak, 20% in ending
3. Testing Effect - Interactive retrieval strengthens memory
4. Mere Exposure - 10-20 exposures optimal, then inverted-U decline
5. Ad Fatigue - Platform-specific thresholds

CRITICAL: Burst campaigns are SUBOPTIMAL for long-term memory.

Reference: Cepeda et al. (2008, 2009); Kahneman's peak-end research
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.advertising_psychology import (
    MemoryOptimizationProfile,
    PeakEndOptimization,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SPACING EFFECT PARAMETERS
# =============================================================================

# Optimal gap = approximately 10-20% of retention interval
RETENTION_TO_GAP_RATIO = 0.15  # 15% of retention interval

# Retention interval → Optimal gap (days)
OPTIMAL_GAPS = {
    7: 1.0,      # 1 week retention → 1 day gap
    14: 2.0,     # 2 week retention → 2 day gap
    30: 4.0,     # 1 month retention → 4 day gap
    90: 14.0,    # 3 month retention → 2 week gap
    180: 28.0,   # 6 month retention → 4 week gap
    365: 35.0,   # 1 year retention → 5 week gap
}

# Platform-specific fatigue thresholds
FATIGUE_THRESHOLDS = {
    "facebook": {"weekly": 4, "total": 12},
    "instagram": {"weekly": 5, "total": 15},
    "youtube": {"weekly": 3, "total": 10},
    "display": {"weekly": 7, "total": 20},
    "native": {"weekly": 5, "total": 15},
    "audio": {"weekly": 6, "total": 18},
    "default": {"weekly": 4, "total": 12},
}


# =============================================================================
# MEMORY OPTIMIZATION RESULT
# =============================================================================

class MemoryOptimizationResult(BaseModel):
    """
    Result of memory optimization analysis.
    
    Provides exposure timing and ad structure recommendations.
    """
    
    # Spacing effect
    optimal_gap_days: float = Field(default=1.0, ge=0.1)
    current_gap_days: float = Field(default=0.0, ge=0.0)
    gap_is_optimal: bool = Field(default=False)
    spacing_recommendation: str = Field(default="")
    
    # Fatigue detection
    exposures_this_week: int = Field(default=0, ge=0)
    exposures_total: int = Field(default=0, ge=0)
    fatigue_level: float = Field(default=0.0, ge=0.0, le=1.0)
    is_fatigued: bool = Field(default=False)
    fatigue_recommendation: str = Field(default="")
    
    # Mere exposure
    mere_exposure_count: int = Field(default=0, ge=0)
    mere_exposure_optimal: bool = Field(default=False)
    mere_exposure_recommendation: str = Field(default="")
    
    # Peak-end structure (for ad creative)
    peak_position_pct: float = Field(default=67.0, ge=0.0, le=100.0)
    peak_investment_pct: float = Field(default=70.0, ge=0.0, le=100.0)
    ending_investment_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    duration_investment_pct: float = Field(default=10.0, ge=0.0, le=100.0)
    
    # Overall recommendations
    should_show_ad: bool = Field(default=True)
    next_optimal_exposure: Optional[datetime] = None
    ad_structure_recommendations: List[str] = Field(default_factory=list)
    
    # Research basis
    spacing_effect_size: str = Field(default="150% improvement")
    peak_end_effect_size: str = Field(default="r = 0.70")
    
    # Confidence
    confidence: SignalConfidence = Field(default=SignalConfidence.MODERATE)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "optimal_gap_days": self.optimal_gap_days,
            "current_gap_days": self.current_gap_days,
            "gap_is_optimal": self.gap_is_optimal,
            "spacing_recommendation": self.spacing_recommendation,
            "exposures_this_week": self.exposures_this_week,
            "exposures_total": self.exposures_total,
            "fatigue_level": self.fatigue_level,
            "is_fatigued": self.is_fatigued,
            "fatigue_recommendation": self.fatigue_recommendation,
            "mere_exposure_count": self.mere_exposure_count,
            "mere_exposure_optimal": self.mere_exposure_optimal,
            "should_show_ad": self.should_show_ad,
            "next_optimal_exposure": self.next_optimal_exposure.isoformat() if self.next_optimal_exposure else None,
            "ad_structure_recommendations": self.ad_structure_recommendations,
            "confidence": self.confidence.value,
        }


# =============================================================================
# MEMORY OPTIMIZER
# =============================================================================

class MemoryOptimizer:
    """
    Optimizes ad exposure timing and structure based on memory research.
    
    Key Findings Applied:
    - Spacing Effect: Distributed > Massed (150% improvement)
    - Peak-End Rule: Peak and ending dominate recall
    - Mere Exposure: 10-20 exposures optimal
    - Ad Fatigue: Platform-specific thresholds
    
    Usage:
        optimizer = MemoryOptimizer()
        result = optimizer.optimize(
            retention_goal_days=30,
            last_exposure=datetime.now() - timedelta(days=3),
            exposures_this_week=2,
            platform="facebook"
        )
    """
    
    def __init__(self):
        self._optimization_count = 0
    
    def optimize(
        self,
        retention_goal_days: int = 7,
        last_exposure: Optional[datetime] = None,
        exposures_this_week: int = 0,
        exposures_total: int = 0,
        platform: str = "default",
        ad_duration_seconds: int = 15,
    ) -> MemoryOptimizationResult:
        """
        Get memory optimization recommendations.
        
        Args:
            retention_goal_days: How long we want user to remember
            last_exposure: When user was last exposed to this ad
            exposures_this_week: Number of exposures this week
            exposures_total: Total exposures to this creative
            platform: Ad platform for fatigue thresholds
            ad_duration_seconds: Ad duration for peak-end structure
            
        Returns:
            MemoryOptimizationResult with all recommendations
        """
        # Calculate optimal gap
        optimal_gap = self._calculate_optimal_gap(retention_goal_days)
        
        # Calculate current gap
        current_gap = 0.0
        if last_exposure:
            current_gap = (datetime.now() - last_exposure).total_seconds() / 86400
        
        gap_is_optimal = self._is_gap_optimal(current_gap, optimal_gap)
        spacing_rec = self._get_spacing_recommendation(current_gap, optimal_gap)
        
        # Check fatigue
        fatigue_thresholds = FATIGUE_THRESHOLDS.get(platform, FATIGUE_THRESHOLDS["default"])
        fatigue_level = self._calculate_fatigue(
            exposures_this_week,
            exposures_total,
            fatigue_thresholds,
        )
        is_fatigued = fatigue_level > 0.7
        fatigue_rec = self._get_fatigue_recommendation(fatigue_level, exposures_this_week, exposures_total)
        
        # Check mere exposure
        mere_exposure_optimal = 10 <= exposures_total <= 20
        mere_exposure_rec = self._get_mere_exposure_recommendation(exposures_total)
        
        # Calculate next optimal exposure
        next_exposure = None
        if last_exposure:
            next_exposure = last_exposure + timedelta(days=optimal_gap)
        
        # Should we show ad?
        should_show = not is_fatigued and (current_gap >= optimal_gap * 0.8 or last_exposure is None)
        
        # Peak-end structure recommendations
        peak_end = self._get_peak_end_structure(ad_duration_seconds)
        ad_structure_recs = self._get_structure_recommendations(ad_duration_seconds)
        
        result = MemoryOptimizationResult(
            optimal_gap_days=optimal_gap,
            current_gap_days=current_gap,
            gap_is_optimal=gap_is_optimal,
            spacing_recommendation=spacing_rec,
            exposures_this_week=exposures_this_week,
            exposures_total=exposures_total,
            fatigue_level=fatigue_level,
            is_fatigued=is_fatigued,
            fatigue_recommendation=fatigue_rec,
            mere_exposure_count=exposures_total,
            mere_exposure_optimal=mere_exposure_optimal,
            mere_exposure_recommendation=mere_exposure_rec,
            peak_position_pct=peak_end["peak_position_pct"],
            peak_investment_pct=peak_end["peak_investment_pct"],
            ending_investment_pct=peak_end["ending_investment_pct"],
            duration_investment_pct=peak_end["duration_investment_pct"],
            should_show_ad=should_show,
            next_optimal_exposure=next_exposure,
            ad_structure_recommendations=ad_structure_recs,
            confidence=SignalConfidence.HIGH,  # Research is well-established
        )
        
        self._optimization_count += 1
        
        logger.debug(
            f"Memory optimization: gap={current_gap:.1f}d (optimal={optimal_gap:.1f}d), "
            f"fatigue={fatigue_level:.2f}, should_show={should_show}"
        )
        
        return result
    
    def get_exposure_schedule(
        self,
        retention_goal_days: int,
        num_exposures: int = 5,
        start_date: Optional[datetime] = None,
    ) -> List[datetime]:
        """
        Generate optimal exposure schedule.
        
        Args:
            retention_goal_days: How long to remember
            num_exposures: Number of exposures to schedule
            start_date: When to start (default: now)
            
        Returns:
            List of optimal exposure timestamps
        """
        if start_date is None:
            start_date = datetime.now()
        
        optimal_gap = self._calculate_optimal_gap(retention_goal_days)
        
        schedule = [start_date]
        for i in range(1, num_exposures):
            next_exposure = schedule[-1] + timedelta(days=optimal_gap)
            schedule.append(next_exposure)
        
        return schedule
    
    def _calculate_optimal_gap(self, retention_days: int) -> float:
        """Calculate optimal gap for retention interval."""
        # Check known values
        if retention_days in OPTIMAL_GAPS:
            return OPTIMAL_GAPS[retention_days]
        
        # Interpolate or use formula
        return retention_days * RETENTION_TO_GAP_RATIO
    
    def _is_gap_optimal(self, current: float, optimal: float) -> bool:
        """Check if current gap is within optimal range."""
        # Allow 20% tolerance
        return optimal * 0.8 <= current <= optimal * 1.5
    
    def _get_spacing_recommendation(self, current: float, optimal: float) -> str:
        """Get spacing recommendation."""
        if current < optimal * 0.5:
            return f"Too frequent. Wait {optimal - current:.1f} more days for optimal spacing."
        elif current > optimal * 2:
            return f"Gap too long. Risk of forgetting. Expose now."
        elif self._is_gap_optimal(current, optimal):
            return "Optimal spacing. Good time to expose."
        else:
            return f"Approaching optimal. Ideal exposure in {optimal - current:.1f} days."
    
    def _calculate_fatigue(
        self,
        weekly: int,
        total: int,
        thresholds: Dict[str, int],
    ) -> float:
        """Calculate fatigue level (0-1)."""
        weekly_fatigue = min(1.0, weekly / thresholds["weekly"])
        total_fatigue = min(1.0, total / thresholds["total"])
        
        # Weight weekly more heavily (recent saturation matters more)
        return weekly_fatigue * 0.6 + total_fatigue * 0.4
    
    def _get_fatigue_recommendation(
        self,
        fatigue: float,
        weekly: int,
        total: int,
    ) -> str:
        """Get fatigue recommendation."""
        if fatigue < 0.3:
            return "Low fatigue. Safe to expose."
        elif fatigue < 0.5:
            return "Moderate fatigue. Consider reducing frequency."
        elif fatigue < 0.7:
            return "High fatigue. Reduce exposure or rotate creative."
        else:
            return "Severe fatigue. Suppress ads or switch creative entirely."
    
    def _get_mere_exposure_recommendation(self, count: int) -> str:
        """Get mere exposure recommendation."""
        if count < 10:
            return f"Building familiarity ({count}/10 optimal minimum). Continue exposures."
        elif count <= 20:
            return f"Optimal mere exposure range ({count}/10-20). Peak preference effect."
        else:
            return f"Past optimal range ({count}>20). Risk of boredom/wear-out. Consider new creative."
    
    def _get_peak_end_structure(self, duration_seconds: int) -> Dict[str, float]:
        """Get peak-end structure recommendations."""
        peak_position = int(duration_seconds * 0.67)  # Peak at 2/3
        
        return {
            "peak_position_pct": 67.0,
            "peak_investment_pct": 70.0,  # 70% effort on peak moment
            "ending_investment_pct": 20.0,  # 20% on ending
            "duration_investment_pct": 10.0,  # 10% on rest
        }
    
    def _get_structure_recommendations(self, duration_seconds: int) -> List[str]:
        """Get ad structure recommendations based on peak-end rule."""
        peak_time = int(duration_seconds * 0.67)
        ending_start = duration_seconds - 3
        
        return [
            f"0-{peak_time-2}s: Build tension and interest",
            f"{peak_time-2}-{peak_time+2}s: PEAK - Maximum emotional impact (invest 70% effort here)",
            f"{peak_time+2}-{ending_start}s: Process the peak moment",
            f"{ending_start}-{duration_seconds}s: ENDING - Positive close + CTA (invest 20% effort here)",
            "KEY: Shorter with strong peak/end beats longer mediocre",
            "Duration itself is nearly irrelevant (r = 0.03 with recall)",
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "optimizations_performed": self._optimization_count,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_optimizer: Optional[MemoryOptimizer] = None


def get_memory_optimizer() -> MemoryOptimizer:
    """Get singleton memory optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = MemoryOptimizer()
    return _optimizer
