# =============================================================================
# ADAM Learning Quality Audit Framework
# Location: adam/core/learning/quality_audit.py
# =============================================================================

"""
LEARNING QUALITY AUDIT FRAMEWORK

CRITICAL INSIGHT FROM DR. NOCERA:
"Presence doesn't equal high quality and is a much too low of a bar to set."

This framework goes beyond checking IF learning exists to evaluating:
1. Is the learning EFFECTIVE? (Does it improve predictions?)
2. Is the learning EFFICIENT? (Does it converge quickly?)
3. Is the learning COHERENT? (Do components agree?)
4. Is the learning FRESH? (Are priors current?)
5. Is the learning COMPLETE? (Are all pathways connected?)
6. Is the learning SYNERGISTIC? (Does it create emergent value?)

A system can have learning infrastructure everywhere and still produce
garbage decisions if the learning isn't OPTIMIZED for the system's goals.

THIS IS THE DIFFERENCE BETWEEN A SYSTEM THAT EXISTS AND A SYSTEM THAT WINS.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import numpy as np
import asyncio
import logging

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningQualityMetrics,
    LearningSignalType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# QUALITY DIMENSIONS
# =============================================================================

class QualityDimension(str, Enum):
    """The dimensions of learning quality we measure."""
    
    # Does learning improve predictions?
    EFFECTIVENESS = "effectiveness"
    
    # Does learning converge quickly?
    EFFICIENCY = "efficiency"
    
    # Do components agree on what they've learned?
    COHERENCE = "coherence"
    
    # Are priors current and not stale?
    FRESHNESS = "freshness"
    
    # Are all learning pathways connected?
    COMPLETENESS = "completeness"
    
    # Does learning create emergent value beyond aggregation?
    SYNERGY = "synergy"
    
    # Is learning calibrated (confidence matches accuracy)?
    CALIBRATION = "calibration"
    
    # Does learning generalize or is it overfitting?
    GENERALIZATION = "generalization"


class QualityLevel(str, Enum):
    """Quality levels for audit results."""
    
    EXCELLENT = "excellent"      # >= 0.9
    GOOD = "good"                # >= 0.75
    ACCEPTABLE = "acceptable"    # >= 0.6
    CONCERNING = "concerning"    # >= 0.4
    CRITICAL = "critical"        # < 0.4


# =============================================================================
# AUDIT RESULTS
# =============================================================================

class DimensionScore(BaseModel):
    """Score for a single quality dimension."""
    
    dimension: QualityDimension
    score: float = Field(ge=0.0, le=1.0)
    level: QualityLevel
    
    # Evidence for the score
    evidence: List[str] = Field(default_factory=list)
    
    # Specific issues found
    issues: List[str] = Field(default_factory=list)
    
    # Recommendations for improvement
    recommendations: List[str] = Field(default_factory=list)
    
    # Trend over time
    trend: str = "stable"  # improving, stable, declining
    
    @classmethod
    def from_score(cls, dimension: QualityDimension, score: float) -> "DimensionScore":
        if score >= 0.9:
            level = QualityLevel.EXCELLENT
        elif score >= 0.75:
            level = QualityLevel.GOOD
        elif score >= 0.6:
            level = QualityLevel.ACCEPTABLE
        elif score >= 0.4:
            level = QualityLevel.CONCERNING
        else:
            level = QualityLevel.CRITICAL
        
        return cls(dimension=dimension, score=score, level=level)


class ComponentAuditResult(BaseModel):
    """Audit result for a single component."""
    
    component_name: str
    component_version: str
    
    # Overall score
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_level: QualityLevel
    
    # Dimension scores
    dimension_scores: Dict[QualityDimension, DimensionScore] = Field(default_factory=dict)
    
    # Key metrics
    metrics: LearningQualityMetrics
    
    # Critical issues
    critical_issues: List[str] = Field(default_factory=list)
    
    # Health status
    is_healthy: bool = True
    
    # Audit timestamp
    audited_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PathwayAuditResult(BaseModel):
    """Audit result for a learning pathway."""
    
    pathway_name: str
    
    # Components in pathway
    source_component: str
    target_components: List[str]
    
    # Signal types in pathway
    signal_types: List[LearningSignalType]
    
    # Is pathway connected?
    is_connected: bool
    
    # Signal flow rate
    signals_per_hour: float
    
    # Average latency
    avg_latency_ms: float
    
    # Issues
    issues: List[str] = Field(default_factory=list)


class SystemAuditResult(BaseModel):
    """Complete system-wide audit result."""
    
    audit_id: str
    
    # Overall system scores
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_level: QualityLevel
    
    # Dimension scores (system-wide)
    dimension_scores: Dict[QualityDimension, DimensionScore] = Field(default_factory=dict)
    
    # Component results
    component_results: Dict[str, ComponentAuditResult] = Field(default_factory=dict)
    
    # Pathway results
    pathway_results: List[PathwayAuditResult] = Field(default_factory=list)
    
    # Disconnected components
    disconnected_components: List[str] = Field(default_factory=list)
    
    # Weak components (need improvement)
    weak_components: List[str] = Field(default_factory=list)
    
    # Critical issues
    critical_issues: List[str] = Field(default_factory=list)
    
    # Recommendations
    prioritized_recommendations: List[str] = Field(default_factory=list)
    
    # Audit metadata
    audited_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audit_duration_seconds: float = 0.0


# =============================================================================
# THE QUALITY AUDITOR
# =============================================================================

class LearningQualityAuditor:
    """
    ADAM's Learning Quality Auditor
    
    This component evaluates the EFFECTIVENESS of learning across the system,
    not just whether learning exists.
    
    It answers the critical question:
    "Is the system actually getting smarter, or just going through the motions?"
    """
    
    def __init__(
        self,
        neo4j_driver,
        redis_client,
        component_registry: Dict[str, LearningCapableComponent]
    ):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.component_registry = component_registry
        
        # Historical audit results for trend analysis
        self.audit_history: List[SystemAuditResult] = []
    
    async def run_full_audit(self) -> SystemAuditResult:
        """
        Run a complete quality audit of the learning system.
        
        This is the comprehensive evaluation that determines whether
        ADAM is truly learning and improving.
        """
        
        start_time = datetime.now(timezone.utc)
        audit_id = f"audit_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # 1. Audit each component
        component_results = {}
        for name, component in self.component_registry.items():
            result = await self._audit_component(component)
            component_results[name] = result
        
        # 2. Audit learning pathways
        pathway_results = await self._audit_pathways()
        
        # 3. Compute system-wide dimension scores
        dimension_scores = await self._compute_system_dimension_scores(
            component_results, pathway_results
        )
        
        # 4. Identify issues
        disconnected = [
            name for name, result in component_results.items()
            if not result.is_healthy
        ]
        
        weak = [
            name for name, result in component_results.items()
            if result.overall_score < 0.6
        ]
        
        critical_issues = []
        for result in component_results.values():
            critical_issues.extend(result.critical_issues)
        for pathway in pathway_results:
            if not pathway.is_connected:
                critical_issues.append(f"Disconnected pathway: {pathway.pathway_name}")
        
        # 5. Compute overall score
        if component_results:
            overall_score = np.mean([r.overall_score for r in component_results.values()])
        else:
            overall_score = 0.0
        
        # Penalty for disconnected components
        if disconnected:
            overall_score *= (1 - 0.1 * len(disconnected))
        
        # 6. Generate recommendations
        recommendations = self._generate_recommendations(
            component_results, pathway_results, dimension_scores
        )
        
        # 7. Build result
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        result = SystemAuditResult(
            audit_id=audit_id,
            overall_score=max(0, min(1, overall_score)),
            overall_level=self._score_to_level(overall_score),
            dimension_scores=dimension_scores,
            component_results=component_results,
            pathway_results=pathway_results,
            disconnected_components=disconnected,
            weak_components=weak,
            critical_issues=critical_issues,
            prioritized_recommendations=recommendations,
            audit_duration_seconds=duration
        )
        
        # Store for trend analysis
        self.audit_history.append(result)
        
        # Store in Neo4j
        await self._store_audit_result(result)
        
        return result
    
    async def _audit_component(
        self,
        component: LearningCapableComponent
    ) -> ComponentAuditResult:
        """Audit a single component's learning quality."""
        
        # Get component metrics
        metrics = await component.get_learning_quality_metrics()
        
        # Get health status
        is_healthy, health_issues = await component.validate_learning_health()
        
        # Score each dimension
        dimension_scores = {}
        
        # 1. EFFECTIVENESS - Does learning improve predictions?
        effectiveness = await self._score_effectiveness(component, metrics)
        dimension_scores[QualityDimension.EFFECTIVENESS] = effectiveness
        
        # 2. EFFICIENCY - Does learning converge quickly?
        efficiency = await self._score_efficiency(component, metrics)
        dimension_scores[QualityDimension.EFFICIENCY] = efficiency
        
        # 3. COHERENCE - Is learning internally consistent?
        coherence = await self._score_coherence(component, metrics)
        dimension_scores[QualityDimension.COHERENCE] = coherence
        
        # 4. FRESHNESS - Are priors current?
        freshness = await self._score_freshness(component, metrics)
        dimension_scores[QualityDimension.FRESHNESS] = freshness
        
        # 5. COMPLETENESS - Are all pathways connected?
        completeness = await self._score_completeness(component, metrics)
        dimension_scores[QualityDimension.COMPLETENESS] = completeness
        
        # 6. CALIBRATION - Does confidence match accuracy?
        calibration = await self._score_calibration(component, metrics)
        dimension_scores[QualityDimension.CALIBRATION] = calibration
        
        # Compute overall score
        overall_score = np.mean([d.score for d in dimension_scores.values()])
        
        # Collect critical issues
        critical_issues = []
        for dim, score in dimension_scores.items():
            if score.level in [QualityLevel.CRITICAL, QualityLevel.CONCERNING]:
                critical_issues.extend(score.issues)
        critical_issues.extend(health_issues)
        
        return ComponentAuditResult(
            component_name=component.component_name,
            component_version=component.component_version,
            overall_score=overall_score,
            overall_level=self._score_to_level(overall_score),
            dimension_scores=dimension_scores,
            metrics=metrics,
            critical_issues=critical_issues,
            is_healthy=is_healthy
        )
    
    async def _score_effectiveness(
        self,
        component: LearningCapableComponent,
        metrics: LearningQualityMetrics
    ) -> DimensionScore:
        """
        Score EFFECTIVENESS: Does learning improve predictions?
        
        This is the most important dimension. If predictions aren't
        improving, the learning is worthless.
        """
        
        score = DimensionScore.from_score(
            QualityDimension.EFFECTIVENESS,
            metrics.prediction_accuracy
        )
        
        # Add evidence
        score.evidence.append(
            f"Prediction accuracy: {metrics.prediction_accuracy:.2%}"
        )
        score.evidence.append(
            f"Accuracy trend: {metrics.prediction_accuracy_trend}"
        )
        
        # Add issues if concerning
        if metrics.prediction_accuracy < 0.5:
            score.issues.append(
                "Predictions are no better than random - learning is not working"
            )
        
        if metrics.prediction_accuracy_trend == "declining":
            score.issues.append(
                "Accuracy is declining - may indicate concept drift or overfitting"
            )
        
        # Add recommendations
        if score.level in [QualityLevel.CRITICAL, QualityLevel.CONCERNING]:
            score.recommendations.append(
                "Review training data quality and recency"
            )
            score.recommendations.append(
                "Check for data drift between training and inference"
            )
        
        score.trend = metrics.prediction_accuracy_trend
        
        return score
    
    async def _score_efficiency(
        self,
        component: LearningCapableComponent,
        metrics: LearningQualityMetrics
    ) -> DimensionScore:
        """
        Score EFFICIENCY: Does learning converge quickly?
        
        A system that takes forever to learn is wasting opportunities.
        """
        
        # Convergence rate: higher is better
        if metrics.convergence_rate > 0.1:
            efficiency_score = 0.9
        elif metrics.convergence_rate > 0.05:
            efficiency_score = 0.75
        elif metrics.convergence_rate > 0.01:
            efficiency_score = 0.6
        else:
            efficiency_score = 0.4
        
        score = DimensionScore.from_score(
            QualityDimension.EFFICIENCY,
            efficiency_score
        )
        
        score.evidence.append(
            f"Convergence rate: {metrics.convergence_rate:.4f}"
        )
        score.evidence.append(
            f"Outcomes processed: {metrics.outcomes_processed}"
        )
        
        if metrics.convergence_rate < 0.01:
            score.issues.append(
                "Learning is converging very slowly - check learning rate"
            )
            score.recommendations.append(
                "Consider increasing learning rate or using adaptive methods"
            )
        
        return score
    
    async def _score_coherence(
        self,
        component: LearningCapableComponent,
        metrics: LearningQualityMetrics
    ) -> DimensionScore:
        """
        Score COHERENCE: Is learning internally consistent?
        
        If a component's learned beliefs contradict each other,
        the learning is broken.
        """
        
        # Query for conflicting beliefs
        conflicts = await self._query_component_conflicts(component.component_name)
        
        if conflicts == 0:
            coherence_score = 1.0
        elif conflicts < 5:
            coherence_score = 0.8
        elif conflicts < 10:
            coherence_score = 0.6
        else:
            coherence_score = 0.3
        
        score = DimensionScore.from_score(
            QualityDimension.COHERENCE,
            coherence_score
        )
        
        score.evidence.append(f"Detected conflicts: {conflicts}")
        
        if conflicts > 0:
            score.issues.append(
                f"{conflicts} internal conflicts detected in learned beliefs"
            )
            score.recommendations.append(
                "Review conflict resolution logic and priority rules"
            )
        
        return score
    
    async def _score_freshness(
        self,
        component: LearningCapableComponent,
        metrics: LearningQualityMetrics
    ) -> DimensionScore:
        """
        Score FRESHNESS: Are priors current?
        
        Stale priors lead to outdated decisions.
        """
        
        freshness_score = 1.0
        
        # Check last update time
        if metrics.last_learning_update:
            age = datetime.now(timezone.utc) - metrics.last_learning_update
            if age > timedelta(hours=24):
                freshness_score -= 0.3
            elif age > timedelta(hours=6):
                freshness_score -= 0.1
        else:
            freshness_score -= 0.5
        
        # Check stale priors count
        if metrics.stale_priors_count > 10:
            freshness_score -= 0.3
        elif metrics.stale_priors_count > 5:
            freshness_score -= 0.1
        
        freshness_score = max(0, freshness_score)
        
        score = DimensionScore.from_score(
            QualityDimension.FRESHNESS,
            freshness_score
        )
        
        if metrics.last_learning_update:
            score.evidence.append(
                f"Last update: {metrics.last_learning_update.isoformat()}"
            )
        score.evidence.append(
            f"Stale priors: {metrics.stale_priors_count}"
        )
        
        if metrics.stale_priors_count > 5:
            score.issues.append(
                f"{metrics.stale_priors_count} priors are stale and need refresh"
            )
            score.recommendations.append(
                "Implement more aggressive prior refresh strategy"
            )
        
        return score
    
    async def _score_completeness(
        self,
        component: LearningCapableComponent,
        metrics: LearningQualityMetrics
    ) -> DimensionScore:
        """
        Score COMPLETENESS: Are all learning pathways connected?
        
        A component that can't receive or emit learning signals
        is a dead node in the system.
        """
        
        # Check upstream and downstream connections
        upstream_count = len(metrics.upstream_dependencies)
        downstream_count = len(metrics.downstream_consumers)
        
        # Most components should have both
        if upstream_count > 0 and downstream_count > 0:
            completeness_score = 1.0
        elif upstream_count > 0 or downstream_count > 0:
            completeness_score = 0.6
        else:
            completeness_score = 0.2
        
        # Factor in integration health
        completeness_score *= metrics.integration_health
        
        score = DimensionScore.from_score(
            QualityDimension.COMPLETENESS,
            completeness_score
        )
        
        score.evidence.append(
            f"Upstream dependencies: {upstream_count}"
        )
        score.evidence.append(
            f"Downstream consumers: {downstream_count}"
        )
        score.evidence.append(
            f"Integration health: {metrics.integration_health:.2%}"
        )
        
        if upstream_count == 0:
            score.issues.append(
                "No upstream learning signals - component is isolated"
            )
            score.recommendations.append(
                "Connect to Gradient Bridge for outcome signals"
            )
        
        if downstream_count == 0:
            score.issues.append(
                "No downstream consumers - learning is not propagating"
            )
            score.recommendations.append(
                "Register learning signal consumers"
            )
        
        return score
    
    async def _score_calibration(
        self,
        component: LearningCapableComponent,
        metrics: LearningQualityMetrics
    ) -> DimensionScore:
        """
        Score CALIBRATION: Does confidence match accuracy?
        
        A system that is 90% confident but only 50% accurate is
        dangerously miscalibrated.
        """
        
        # Query calibration data
        calibration_error = await self._query_calibration_error(
            component.component_name
        )
        
        # Lower error = better calibration
        if calibration_error < 0.05:
            calibration_score = 1.0
        elif calibration_error < 0.1:
            calibration_score = 0.85
        elif calibration_error < 0.15:
            calibration_score = 0.7
        elif calibration_error < 0.25:
            calibration_score = 0.5
        else:
            calibration_score = 0.3
        
        score = DimensionScore.from_score(
            QualityDimension.CALIBRATION,
            calibration_score
        )
        
        score.evidence.append(
            f"Calibration error: {calibration_error:.2%}"
        )
        
        if calibration_error > 0.15:
            score.issues.append(
                f"Component is miscalibrated - confidence doesn't match accuracy"
            )
            score.recommendations.append(
                "Implement confidence calibration using Platt scaling or isotonic regression"
            )
        
        return score
    
    async def _audit_pathways(self) -> List[PathwayAuditResult]:
        """Audit all learning pathways."""
        
        pathways = []
        
        # Query pathway definitions from config
        pathway_definitions = self._get_pathway_definitions()
        
        for pathway_def in pathway_definitions:
            result = await self._audit_single_pathway(pathway_def)
            pathways.append(result)
        
        return pathways
    
    def _get_pathway_definitions(self) -> List[Dict[str, Any]]:
        """Get learning pathway definitions."""
        
        return [
            {
                "name": "outcome_to_gradient_bridge",
                "source": "outcome_observer",
                "targets": ["gradient_bridge"],
                "signals": [LearningSignalType.OUTCOME_CONVERSION]
            },
            {
                "name": "gradient_bridge_to_components",
                "source": "gradient_bridge",
                "targets": ["meta_learner", "thompson_sampling", "copy_generation"],
                "signals": [LearningSignalType.CREDIT_ASSIGNED, LearningSignalType.MECHANISM_ATTRIBUTED]
            },
            {
                "name": "signal_accuracy_pathway",
                "source": "signal_aggregation",
                "targets": ["atom_of_thought", "multimodal_fusion"],
                "signals": [LearningSignalType.SIGNAL_ACCURACY_VALIDATED]
            },
            {
                "name": "emergence_pathway",
                "source": "atom_of_thought",
                "targets": ["neo4j_graph", "psychological_constructs"],
                "signals": [LearningSignalType.NOVEL_CONSTRUCT_DISCOVERED]
            },
        ]
    
    async def _audit_single_pathway(
        self,
        pathway_def: Dict[str, Any]
    ) -> PathwayAuditResult:
        """Audit a single learning pathway."""
        
        name = pathway_def["name"]
        source = pathway_def["source"]
        targets = pathway_def["targets"]
        signals = pathway_def["signals"]
        
        # Check if source exists
        source_exists = source in self.component_registry
        
        # Check if targets exist
        targets_exist = all(t in self.component_registry for t in targets)
        
        # Query signal flow metrics
        signals_per_hour = await self._query_signal_flow(name)
        avg_latency = await self._query_pathway_latency(name)
        
        is_connected = source_exists and targets_exist and signals_per_hour > 0
        
        issues = []
        if not source_exists:
            issues.append(f"Source component '{source}' not registered")
        for target in targets:
            if target not in self.component_registry:
                issues.append(f"Target component '{target}' not registered")
        if signals_per_hour == 0:
            issues.append("No signals flowing through pathway")
        
        return PathwayAuditResult(
            pathway_name=name,
            source_component=source,
            target_components=targets,
            signal_types=signals,
            is_connected=is_connected,
            signals_per_hour=signals_per_hour,
            avg_latency_ms=avg_latency,
            issues=issues
        )
    
    async def _compute_system_dimension_scores(
        self,
        component_results: Dict[str, ComponentAuditResult],
        pathway_results: List[PathwayAuditResult]
    ) -> Dict[QualityDimension, DimensionScore]:
        """Compute system-wide dimension scores."""
        
        dimension_scores = {}
        
        for dimension in QualityDimension:
            # Aggregate from components
            component_scores = [
                result.dimension_scores.get(dimension, DimensionScore.from_score(dimension, 0.5))
                for result in component_results.values()
            ]
            
            if component_scores:
                avg_score = np.mean([s.score for s in component_scores])
            else:
                avg_score = 0.0
            
            # Special handling for COMPLETENESS - factor in pathway connectivity
            if dimension == QualityDimension.COMPLETENESS:
                connected_pathways = sum(1 for p in pathway_results if p.is_connected)
                total_pathways = len(pathway_results) if pathway_results else 1
                pathway_factor = connected_pathways / total_pathways
                avg_score = avg_score * 0.5 + pathway_factor * 0.5
            
            dimension_scores[dimension] = DimensionScore.from_score(dimension, avg_score)
        
        # Add SYNERGY dimension (system-level only)
        synergy = await self._compute_synergy_score(component_results)
        dimension_scores[QualityDimension.SYNERGY] = synergy
        
        return dimension_scores
    
    async def _compute_synergy_score(
        self,
        component_results: Dict[str, ComponentAuditResult]
    ) -> DimensionScore:
        """
        Compute SYNERGY: Does learning create emergent value?
        
        This measures whether the whole is greater than the sum of parts.
        """
        
        # Query for emergent discoveries
        emergent_count = await self._query_emergent_discoveries()
        
        # Query for cross-component improvements
        cross_improvements = await self._query_cross_component_improvements()
        
        # Synergy score based on emergent value creation
        synergy_score = 0.5  # Base
        
        if emergent_count > 10:
            synergy_score += 0.3
        elif emergent_count > 5:
            synergy_score += 0.2
        elif emergent_count > 0:
            synergy_score += 0.1
        
        if cross_improvements > 0.05:  # 5% improvement from cross-learning
            synergy_score += 0.2
        
        synergy_score = min(1.0, synergy_score)
        
        score = DimensionScore.from_score(QualityDimension.SYNERGY, synergy_score)
        
        score.evidence.append(f"Emergent discoveries: {emergent_count}")
        score.evidence.append(f"Cross-component improvement: {cross_improvements:.2%}")
        
        if emergent_count == 0:
            score.issues.append(
                "No emergent patterns discovered - learning may be siloed"
            )
            score.recommendations.append(
                "Enable Emergence Engine in Atom of Thought"
            )
        
        return score
    
    def _generate_recommendations(
        self,
        component_results: Dict[str, ComponentAuditResult],
        pathway_results: List[PathwayAuditResult],
        dimension_scores: Dict[QualityDimension, DimensionScore]
    ) -> List[str]:
        """Generate prioritized recommendations."""
        
        recommendations = []
        
        # 1. Critical pathway issues first
        for pathway in pathway_results:
            if not pathway.is_connected:
                recommendations.append(
                    f"CRITICAL: Connect pathway '{pathway.pathway_name}' - "
                    f"{pathway.source_component} → {', '.join(pathway.target_components)}"
                )
        
        # 2. Effectiveness issues (most important dimension)
        effectiveness = dimension_scores.get(QualityDimension.EFFECTIVENESS)
        if effectiveness and effectiveness.level in [QualityLevel.CRITICAL, QualityLevel.CONCERNING]:
            recommendations.append(
                "HIGH: Learning effectiveness is low - review training data and model architecture"
            )
        
        # 3. Weak components
        for name, result in component_results.items():
            if result.overall_score < 0.5:
                recommendations.append(
                    f"MEDIUM: Component '{name}' needs improvement (score: {result.overall_score:.2f})"
                )
        
        # 4. Synergy issues
        synergy = dimension_scores.get(QualityDimension.SYNERGY)
        if synergy and synergy.score < 0.5:
            recommendations.append(
                "MEDIUM: System is not creating emergent value - enable cross-component learning"
            )
        
        # 5. Calibration issues
        calibration = dimension_scores.get(QualityDimension.CALIBRATION)
        if calibration and calibration.score < 0.6:
            recommendations.append(
                "LOW: Confidence calibration is poor - implement Platt scaling"
            )
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _score_to_level(self, score: float) -> QualityLevel:
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.75:
            return QualityLevel.GOOD
        elif score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.4:
            return QualityLevel.CONCERNING
        return QualityLevel.CRITICAL
    
    # =========================================================================
    # QUERY HELPERS
    # =========================================================================
    
    async def _query_component_conflicts(self, component_name: str) -> int:
        """Query for internal conflicts in a component."""
        
        query = """
        MATCH (c:Conflict)
        WHERE c.component = $component
        AND c.resolved = false
        AND c.detected_at > datetime() - duration('P7D')
        RETURN count(c) as conflict_count
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(query, component=component_name)
            record = await result.single()
            return record["conflict_count"] if record else 0
    
    async def _query_calibration_error(self, component_name: str) -> float:
        """Query calibration error for a component."""
        
        query = """
        MATCH (p:Prediction {component: $component})
        WHERE p.resolved = true
        AND p.created_at > datetime() - duration('P7D')
        WITH p.confidence as confidence,
             CASE WHEN p.actual_outcome > 0.5 THEN 1.0 ELSE 0.0 END as outcome
        WITH avg(confidence) as mean_conf, avg(outcome) as mean_accuracy
        RETURN abs(mean_conf - mean_accuracy) as calibration_error
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(query, component=component_name)
            record = await result.single()
            return record["calibration_error"] if record else 0.15
    
    async def _query_signal_flow(self, pathway_name: str) -> float:
        """Query signal flow rate for a pathway."""
        
        # Would query from metrics or event log
        return 100.0  # Placeholder
    
    async def _query_pathway_latency(self, pathway_name: str) -> float:
        """Query average latency for a pathway."""
        
        return 50.0  # Placeholder ms
    
    async def _query_emergent_discoveries(self) -> int:
        """Query count of emergent discoveries."""
        
        query = """
        MATCH (e:EmergentDiscovery)
        WHERE e.discovered_at > datetime() - duration('P30D')
        RETURN count(e) as discovery_count
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(query)
            record = await result.single()
            return record["discovery_count"] if record else 0
    
    async def _query_cross_component_improvements(self) -> float:
        """Query improvement from cross-component learning."""
        
        # Compare accuracy with and without cross-component signals
        return 0.03  # Placeholder 3%
    
    async def _store_audit_result(self, result: SystemAuditResult) -> None:
        """Store audit result in Neo4j."""
        
        query = """
        CREATE (a:SystemAudit {
            audit_id: $audit_id,
            overall_score: $overall_score,
            overall_level: $overall_level,
            audited_at: datetime()
        })
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                audit_id=result.audit_id,
                overall_score=result.overall_score,
                overall_level=result.overall_level.value
            )
