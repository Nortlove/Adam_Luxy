# =============================================================================
# ADAM Enhancement #01: Conflict Resolution Engine
# Location: adam/graph_reasoning/conflict_resolution.py
# =============================================================================

"""
Conflict Resolution Engine for Bidirectional Graph-Reasoning Fusion.

Handles conflicts that arise when:
1. LLM reasoning contradicts graph data
2. Multiple updates conflict on same node
3. Stale data competes with fresh data
4. Ambiguous relationships need resolution

Resolution Strategies:
- GRAPH_WINS: Trust graph data (high confidence)
- LLM_WINS: Trust LLM reasoning (novel insight)
- CONFIDENCE_WEIGHTED: Blend by confidence scores
- RECENCY_WEIGHTED: Prefer more recent data
- HUMAN_ESCALATE: Escalate to human review
"""

from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
import logging
import uuid
import numpy as np

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of conflicts that can occur."""
    CONTRADICTION = "contradiction"       # LLM says X, graph says Y
    STALENESS = "staleness"              # Graph data may be outdated
    AMBIGUITY = "ambiguity"              # Multiple valid interpretations
    DUPLICATE = "duplicate"              # Same data from multiple sources
    TEMPORAL = "temporal"                # Time-based conflicts
    CONFIDENCE = "confidence"            # Confidence score disagreement
    SCHEMA = "schema"                    # Schema/type mismatch


class ResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    GRAPH_WINS = "graph_wins"            # Trust graph data
    LLM_WINS = "llm_wins"                # Trust LLM reasoning
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Blend by confidence
    RECENCY_WEIGHTED = "recency_weighted"        # Prefer recent
    HUMAN_ESCALATE = "human_escalate"    # Escalate to human
    MERGE = "merge"                      # Merge compatible data
    DEFER = "defer"                      # Collect more evidence


class ConflictSeverity(str, Enum):
    """Severity of a conflict."""
    CRITICAL = "critical"    # Blocks decision, must resolve
    HIGH = "high"            # Impacts decision quality
    MEDIUM = "medium"        # May impact edge cases
    LOW = "low"              # Cosmetic or minor


class ConflictingValue(BaseModel):
    """A single value in a conflict."""
    value: Any
    source: str  # "graph", "llm", "user", "external"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    evidence: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conflict(BaseModel):
    """A detected conflict."""
    
    conflict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType
    severity: ConflictSeverity
    
    # What's conflicting
    property_name: str
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    relationship_type: Optional[str] = None
    
    # Conflicting values
    values: List[ConflictingValue] = Field(default_factory=list)
    
    # Context
    decision_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Resolution
    resolved: bool = False
    resolution_strategy: Optional[ResolutionStrategy] = None
    resolved_value: Optional[Any] = None
    resolution_confidence: float = 0.0
    resolution_reasoning: str = ""
    resolved_at: Optional[datetime] = None
    resolved_by: str = "system"
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_value(
        self,
        value: Any,
        source: str,
        confidence: float = 0.5,
        evidence: Optional[List[str]] = None
    ) -> None:
        """Add a conflicting value."""
        self.values.append(ConflictingValue(
            value=value,
            source=source,
            confidence=confidence,
            evidence=evidence or [],
        ))


class ConflictResolutionEngine:
    """
    Engine for detecting and resolving conflicts.
    
    Supports multiple resolution strategies:
    - Automatic resolution for clear-cut cases
    - Confidence-weighted blending for uncertainty
    - Escalation for critical conflicts
    """
    
    def __init__(
        self,
        default_strategy: ResolutionStrategy = ResolutionStrategy.CONFIDENCE_WEIGHTED,
        staleness_threshold_hours: float = 24.0,
        confidence_threshold: float = 0.7,
        escalation_enabled: bool = True,
    ):
        self.default_strategy = default_strategy
        self.staleness_hours = staleness_threshold_hours
        self.confidence_threshold = confidence_threshold
        self.escalation_enabled = escalation_enabled
        
        # Strategy weights for different conflict types
        self.strategy_preferences: Dict[ConflictType, List[ResolutionStrategy]] = {
            ConflictType.CONTRADICTION: [
                ResolutionStrategy.CONFIDENCE_WEIGHTED,
                ResolutionStrategy.RECENCY_WEIGHTED,
                ResolutionStrategy.HUMAN_ESCALATE,
            ],
            ConflictType.STALENESS: [
                ResolutionStrategy.RECENCY_WEIGHTED,
                ResolutionStrategy.LLM_WINS,
            ],
            ConflictType.AMBIGUITY: [
                ResolutionStrategy.CONFIDENCE_WEIGHTED,
                ResolutionStrategy.DEFER,
            ],
            ConflictType.DUPLICATE: [
                ResolutionStrategy.MERGE,
                ResolutionStrategy.RECENCY_WEIGHTED,
            ],
            ConflictType.TEMPORAL: [
                ResolutionStrategy.RECENCY_WEIGHTED,
            ],
            ConflictType.CONFIDENCE: [
                ResolutionStrategy.CONFIDENCE_WEIGHTED,
            ],
            ConflictType.SCHEMA: [
                ResolutionStrategy.GRAPH_WINS,
                ResolutionStrategy.HUMAN_ESCALATE,
            ],
        }
        
        # Statistics
        self._conflicts_detected = 0
        self._conflicts_resolved = 0
        self._conflicts_escalated = 0
    
    def detect_conflict(
        self,
        graph_value: Any,
        llm_value: Any,
        property_name: str,
        graph_confidence: float = 0.8,
        llm_confidence: float = 0.7,
        graph_timestamp: Optional[datetime] = None,
        llm_timestamp: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Conflict]:
        """
        Detect if there's a conflict between graph and LLM values.
        
        Returns Conflict if detected, None if values agree.
        """
        if self._values_equivalent(graph_value, llm_value):
            return None
        
        self._conflicts_detected += 1
        
        # Determine conflict type
        conflict_type = self._classify_conflict_type(
            graph_value, llm_value, graph_timestamp
        )
        
        # Determine severity
        severity = self._assess_severity(
            conflict_type, graph_confidence, llm_confidence, context
        )
        
        conflict = Conflict(
            conflict_type=conflict_type,
            severity=severity,
            property_name=property_name,
            context=context or {},
        )
        
        conflict.add_value(
            value=graph_value,
            source="graph",
            confidence=graph_confidence,
            evidence=["graph_database"]
        )
        
        conflict.add_value(
            value=llm_value,
            source="llm",
            confidence=llm_confidence,
            evidence=["llm_reasoning"]
        )
        
        return conflict
    
    def resolve(self, conflict: Conflict) -> Conflict:
        """
        Resolve a conflict using appropriate strategy.
        
        Modifies conflict in place and returns it.
        """
        if conflict.resolved:
            return conflict
        
        # Select strategy
        strategy = self._select_strategy(conflict)
        conflict.resolution_strategy = strategy
        
        # Apply strategy
        if strategy == ResolutionStrategy.GRAPH_WINS:
            conflict = self._resolve_graph_wins(conflict)
        
        elif strategy == ResolutionStrategy.LLM_WINS:
            conflict = self._resolve_llm_wins(conflict)
        
        elif strategy == ResolutionStrategy.CONFIDENCE_WEIGHTED:
            conflict = self._resolve_confidence_weighted(conflict)
        
        elif strategy == ResolutionStrategy.RECENCY_WEIGHTED:
            conflict = self._resolve_recency_weighted(conflict)
        
        elif strategy == ResolutionStrategy.MERGE:
            conflict = self._resolve_merge(conflict)
        
        elif strategy == ResolutionStrategy.HUMAN_ESCALATE:
            conflict = self._escalate_to_human(conflict)
        
        elif strategy == ResolutionStrategy.DEFER:
            conflict.resolution_reasoning = "Deferred - collecting more evidence"
            # Don't mark resolved
        
        if conflict.resolved:
            self._conflicts_resolved += 1
        
        return conflict
    
    def _values_equivalent(self, v1: Any, v2: Any) -> bool:
        """Check if two values are equivalent."""
        if v1 == v2:
            return True
        
        # Numeric tolerance
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return abs(v1 - v2) < 0.01
        
        # String normalization
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.lower().strip() == v2.lower().strip()
        
        return False
    
    def _classify_conflict_type(
        self,
        graph_value: Any,
        llm_value: Any,
        graph_timestamp: Optional[datetime]
    ) -> ConflictType:
        """Classify the type of conflict."""
        # Check for staleness
        if graph_timestamp:
            age = datetime.utcnow() - graph_timestamp
            if age > timedelta(hours=self.staleness_hours):
                return ConflictType.STALENESS
        
        # Check for type mismatch
        if type(graph_value) != type(llm_value):
            return ConflictType.SCHEMA
        
        # Default to contradiction
        return ConflictType.CONTRADICTION
    
    def _assess_severity(
        self,
        conflict_type: ConflictType,
        graph_conf: float,
        llm_conf: float,
        context: Optional[Dict]
    ) -> ConflictSeverity:
        """Assess severity of conflict."""
        context = context or {}
        
        # High confidence on both sides = critical
        if graph_conf > 0.9 and llm_conf > 0.9:
            return ConflictSeverity.CRITICAL
        
        # Schema conflicts are always high
        if conflict_type == ConflictType.SCHEMA:
            return ConflictSeverity.HIGH
        
        # If either is low confidence, less severe
        if graph_conf < 0.5 or llm_conf < 0.5:
            return ConflictSeverity.LOW
        
        # Check if affects decision
        if context.get("affects_decision", False):
            return ConflictSeverity.HIGH
        
        return ConflictSeverity.MEDIUM
    
    def _select_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        """Select best resolution strategy for conflict."""
        preferences = self.strategy_preferences.get(
            conflict.conflict_type,
            [self.default_strategy]
        )
        
        # Critical conflicts with high disagreement escalate
        if conflict.severity == ConflictSeverity.CRITICAL:
            if self.escalation_enabled:
                return ResolutionStrategy.HUMAN_ESCALATE
        
        # Otherwise use first preference
        return preferences[0] if preferences else self.default_strategy
    
    def _resolve_graph_wins(self, conflict: Conflict) -> Conflict:
        """Resolve by trusting graph data."""
        graph_values = [v for v in conflict.values if v.source == "graph"]
        if graph_values:
            best = max(graph_values, key=lambda v: v.confidence)
            conflict.resolved_value = best.value
            conflict.resolution_confidence = best.confidence
            conflict.resolution_reasoning = "Graph data trusted (established ground truth)"
        
        conflict.resolved = True
        conflict.resolved_at = datetime.utcnow()
        return conflict
    
    def _resolve_llm_wins(self, conflict: Conflict) -> Conflict:
        """Resolve by trusting LLM reasoning."""
        llm_values = [v for v in conflict.values if v.source == "llm"]
        if llm_values:
            best = max(llm_values, key=lambda v: v.confidence)
            conflict.resolved_value = best.value
            conflict.resolution_confidence = best.confidence
            conflict.resolution_reasoning = "LLM reasoning trusted (novel insight)"
        
        conflict.resolved = True
        conflict.resolved_at = datetime.utcnow()
        return conflict
    
    def _resolve_confidence_weighted(self, conflict: Conflict) -> Conflict:
        """Resolve using confidence-weighted blending."""
        if not conflict.values:
            return conflict
        
        # For numeric values, blend
        numeric_values = [
            v for v in conflict.values
            if isinstance(v.value, (int, float))
        ]
        
        if numeric_values:
            total_confidence = sum(v.confidence for v in numeric_values)
            if total_confidence > 0:
                weighted_value = sum(
                    v.value * v.confidence / total_confidence
                    for v in numeric_values
                )
                conflict.resolved_value = weighted_value
                conflict.resolution_confidence = total_confidence / len(numeric_values)
                conflict.resolution_reasoning = "Confidence-weighted blend of values"
        else:
            # For non-numeric, pick highest confidence
            best = max(conflict.values, key=lambda v: v.confidence)
            conflict.resolved_value = best.value
            conflict.resolution_confidence = best.confidence
            conflict.resolution_reasoning = f"Highest confidence value from {best.source}"
        
        conflict.resolved = True
        conflict.resolved_at = datetime.utcnow()
        return conflict
    
    def _resolve_recency_weighted(self, conflict: Conflict) -> Conflict:
        """Resolve by preferring more recent data."""
        if not conflict.values:
            return conflict
        
        # Sort by timestamp
        sorted_values = sorted(
            conflict.values,
            key=lambda v: v.timestamp,
            reverse=True
        )
        
        most_recent = sorted_values[0]
        conflict.resolved_value = most_recent.value
        conflict.resolution_confidence = most_recent.confidence * 0.9  # Slight penalty for recency-only
        conflict.resolution_reasoning = f"Most recent value from {most_recent.source}"
        
        conflict.resolved = True
        conflict.resolved_at = datetime.utcnow()
        return conflict
    
    def _resolve_merge(self, conflict: Conflict) -> Conflict:
        """Resolve by merging compatible data."""
        if not conflict.values:
            return conflict
        
        # For dicts, merge
        dict_values = [v for v in conflict.values if isinstance(v.value, dict)]
        if dict_values:
            merged = {}
            for dv in dict_values:
                merged.update(dv.value)
            conflict.resolved_value = merged
            conflict.resolution_confidence = np.mean([v.confidence for v in dict_values])
            conflict.resolution_reasoning = "Merged compatible dictionary values"
        else:
            # Fall back to confidence-weighted
            return self._resolve_confidence_weighted(conflict)
        
        conflict.resolved = True
        conflict.resolved_at = datetime.utcnow()
        return conflict
    
    def _escalate_to_human(self, conflict: Conflict) -> Conflict:
        """Escalate conflict to human review."""
        self._conflicts_escalated += 1
        
        conflict.resolution_reasoning = "Escalated to human review"
        conflict.resolved_by = "pending_human"
        
        logger.warning(
            f"Conflict {conflict.conflict_id} escalated to human review: "
            f"{conflict.conflict_type.value} on {conflict.property_name}"
        )
        
        # Don't mark resolved - needs human action
        return conflict
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get resolution statistics."""
        return {
            "conflicts_detected": self._conflicts_detected,
            "conflicts_resolved": self._conflicts_resolved,
            "conflicts_escalated": self._conflicts_escalated,
            "resolution_rate": (
                self._conflicts_resolved / max(1, self._conflicts_detected)
            ),
        }


# Singleton instance
_engine: Optional[ConflictResolutionEngine] = None


def get_conflict_resolution_engine() -> ConflictResolutionEngine:
    """Get singleton Conflict Resolution Engine."""
    global _engine
    if _engine is None:
        _engine = ConflictResolutionEngine()
    return _engine
