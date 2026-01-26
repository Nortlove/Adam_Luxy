# =============================================================================
# ADAM Psychological Validity Service
# Location: adam/validity/service.py
# =============================================================================

"""
PSYCHOLOGICAL VALIDITY SERVICE

Orchestrates validity testing across all constructs and components.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.validity.models import (
    ValidityType,
    ValidityStatus,
    ConstructType,
    ValidityResult,
    ValidityReport,
    ConstructValidity,
    PredictiveValidity,
)
from adam.validity.checks import (
    ConstructValidityChecker,
    PredictiveValidityChecker,
    ConvergentValidityChecker,
    DiscriminantValidityChecker,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics

logger = logging.getLogger(__name__)


class PsychologicalValidityService:
    """
    Service for running psychological validity tests.
    
    Responsibilities:
    1. Schedule and run validity checks
    2. Aggregate results into reports
    3. Alert on validity failures
    4. Track validity over time
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        
        # Initialize checkers
        self.checkers = {
            ValidityType.CONSTRUCT: ConstructValidityChecker(),
            ValidityType.PREDICTIVE: PredictiveValidityChecker(),
            ValidityType.CONVERGENT: ConvergentValidityChecker(),
            ValidityType.DISCRIMINANT: DiscriminantValidityChecker(),
        }
        
        # Historical reports
        self._reports: List[ValidityReport] = []
    
    async def run_full_validity_check(
        self,
        data: Dict[str, Any],
        scope: str = "system",
        target: Optional[str] = None,
    ) -> ValidityReport:
        """
        Run comprehensive validity checks.
        
        Args:
            data: Data for validity checks (correlations, predictions, etc.)
            scope: "system", "construct", or "component"
            target: Specific construct or component if scope is narrowed
        
        Returns:
            ValidityReport with all results
        """
        
        report_id = f"validity_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        all_results: List[ValidityResult] = []
        
        # Run all checker types
        for validity_type, checker in self.checkers.items():
            try:
                results = await checker.check(data)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Checker {validity_type} failed: {e}")
        
        # Aggregate results
        passed = sum(1 for r in all_results if r.status == ValidityStatus.PASSED)
        warning = sum(1 for r in all_results if r.status == ValidityStatus.WARNING)
        failed = sum(1 for r in all_results if r.status == ValidityStatus.FAILED)
        
        # Calculate overall score
        total = len(all_results)
        if total > 0:
            overall_score = (passed + 0.5 * warning) / total
        else:
            overall_score = 0.0
        
        # Determine overall status
        if failed > 0:
            overall_status = ValidityStatus.FAILED
        elif warning > 0:
            overall_status = ValidityStatus.WARNING
        elif passed > 0:
            overall_status = ValidityStatus.PASSED
        else:
            overall_status = ValidityStatus.INSUFFICIENT_DATA
        
        # Build report
        report = ValidityReport(
            report_id=report_id,
            scope=scope,
            target=target,
            start_date=now - timedelta(days=30),  # Default to last 30 days
            end_date=now,
            check_results=all_results,
            overall_status=overall_status,
            overall_score=overall_score,
            checks_passed=passed,
            checks_warning=warning,
            checks_failed=failed,
            critical_issues=self._extract_critical_issues(all_results),
            recommendations=self._generate_recommendations(all_results),
        )
        
        # Store report
        self._reports.append(report)
        
        # Cache
        if self.cache:
            await self.cache.set(
                f"validity_report:{report_id}",
                report.model_dump(),
                ttl=86400 * 90,  # 90 days
            )
        
        # Emit event if failures
        if overall_status == ValidityStatus.FAILED:
            await self._emit_validity_alert(report)
        
        logger.info(
            f"Validity check complete: {passed} passed, {warning} warnings, "
            f"{failed} failed. Overall: {overall_status.value}"
        )
        
        return report
    
    async def run_construct_validity(
        self,
        construct: ConstructType,
        data: Dict[str, Any],
    ) -> List[ValidityResult]:
        """Run validity checks for a specific construct."""
        
        checker = self.checkers[ValidityType.CONSTRUCT]
        return await checker.check(data)
    
    async def run_predictive_validity(
        self,
        data: Dict[str, Any],
    ) -> List[ValidityResult]:
        """Run predictive validity checks."""
        
        checker = self.checkers[ValidityType.PREDICTIVE]
        return await checker.check(data)
    
    def _extract_critical_issues(
        self,
        results: List[ValidityResult],
    ) -> List[str]:
        """Extract critical issues from results."""
        
        critical = []
        
        for result in results:
            if result.status == ValidityStatus.FAILED:
                critical.append(
                    f"{result.check.validity_type.value}: {result.check.description} "
                    f"(score: {result.score:.2f}, required: {result.check.pass_threshold})"
                )
        
        return critical
    
    def _generate_recommendations(
        self,
        results: List[ValidityResult],
    ) -> List[str]:
        """Generate recommendations from all results."""
        
        recommendations = set()
        
        for result in results:
            for rec in result.recommendations:
                recommendations.add(rec)
        
        # Add general recommendations based on patterns
        failed_types = [
            r.check.validity_type
            for r in results
            if r.status == ValidityStatus.FAILED
        ]
        
        if ValidityType.CONSTRUCT in failed_types:
            recommendations.add(
                "Schedule manual validation study for affected constructs"
            )
        
        if ValidityType.PREDICTIVE in failed_types:
            recommendations.add(
                "Review model calibration and feature engineering"
            )
        
        return list(recommendations)
    
    async def _emit_validity_alert(
        self,
        report: ValidityReport,
    ) -> None:
        """Emit Kafka event for validity failures."""
        
        producer = get_kafka_producer()
        if producer:
            await producer.send(
                ADAMTopics.ALERT_TRIGGERED,
                {
                    "alert_type": "validity_failure",
                    "report_id": report.report_id,
                    "overall_status": report.overall_status.value,
                    "checks_failed": report.checks_failed,
                    "critical_issues": report.critical_issues,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
    
    async def get_validity_trend(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get validity score trend over time."""
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        recent_reports = [
            r for r in self._reports
            if r.generated_at >= cutoff
        ]
        
        if not recent_reports:
            return {"trend": "insufficient_data", "reports": 0}
        
        scores = [r.overall_score for r in recent_reports]
        
        # Simple trend detection
        if len(scores) >= 2:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            if second_half > first_half + 0.05:
                trend = "improving"
            elif second_half < first_half - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "reports": len(recent_reports),
            "average_score": sum(scores) / len(scores),
            "latest_score": scores[-1],
            "passed_rate": sum(1 for r in recent_reports if r.overall_status == ValidityStatus.PASSED) / len(recent_reports),
        }
    
    async def get_report(
        self,
        report_id: str,
    ) -> Optional[ValidityReport]:
        """Get a specific validity report."""
        
        for report in self._reports:
            if report.report_id == report_id:
                return report
        
        if self.cache:
            cached = await self.cache.get(f"validity_report:{report_id}")
            if cached:
                return ValidityReport(**cached)
        
        return None
