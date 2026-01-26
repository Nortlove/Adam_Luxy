# =============================================================================
# ADAM Distributed Tracing
# Location: adam/observability/tracing.py
# =============================================================================

"""
DISTRIBUTED TRACING

OpenTelemetry-based distributed tracing with psychological trace capture.
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS
# =============================================================================

TRACE_COUNTER = Counter(
    "adam_traces_total",
    "Total traces",
    ["service", "operation"],
)

SPAN_DURATION = Histogram(
    "adam_span_duration_ms",
    "Span duration in milliseconds",
    ["service", "operation"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)


# =============================================================================
# SPAN
# =============================================================================

@dataclass
class Span:
    """A span in a distributed trace."""
    
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    
    # Timing
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Events
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Status
    status: str = "ok"  # ok, error
    error_message: Optional[str] = None
    
    def finish(self, status: str = "ok", error: Optional[str] = None) -> None:
        """Finish the span."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error_message = error
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value


# =============================================================================
# PSYCHOLOGICAL TRACE
# =============================================================================

class PsychologicalTrace(BaseModel):
    """Trace of psychological reasoning for a decision."""
    
    trace_id: str
    request_id: str
    user_id: str
    
    # Psychological context
    user_big_five: Optional[Dict[str, float]] = None
    regulatory_focus: Optional[str] = None
    construal_level: Optional[float] = None
    
    # Atom outputs
    atom_outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Mechanism selection
    selected_mechanisms: List[str] = Field(default_factory=list)
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Decision
    decision_rationale: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Conflicts
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts_resolved: int = Field(default=0, ge=0)
    
    # Timing
    total_duration_ms: float = Field(default=0.0, ge=0.0)
    
    # Timestamp
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class DecisionTrace(BaseModel):
    """Complete trace of a decision request."""
    
    trace_id: str
    request_id: str
    
    # Request info
    platform: str
    user_id: str
    
    # Spans
    spans: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Psychological trace
    psychological: Optional[PsychologicalTrace] = None
    
    # Decision outcome
    decision_made: bool = Field(default=False)
    decision_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance
    total_duration_ms: float = Field(default=0.0, ge=0.0)
    component_durations: Dict[str, float] = Field(default_factory=dict)
    
    # Status
    success: bool = Field(default=True)
    error: Optional[str] = None
    
    # Timestamp
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None


# =============================================================================
# TRACING SERVICE
# =============================================================================

class TracingService:
    """
    Service for distributed tracing with psychological trace capture.
    """
    
    def __init__(
        self,
        service_name: str = "adam",
        enable_psychological: bool = True,
    ):
        self.service_name = service_name
        self.enable_psychological = enable_psychological
        
        # Active traces
        self._active_traces: Dict[str, DecisionTrace] = {}
        self._active_spans: Dict[str, Span] = {}
        
        # Completed traces (limited history)
        self._completed_traces: List[DecisionTrace] = []
        self._max_history = 1000
    
    def start_trace(
        self,
        request_id: str,
        platform: str,
        user_id: str,
    ) -> DecisionTrace:
        """Start a new decision trace."""
        
        trace_id = uuid4().hex
        
        trace = DecisionTrace(
            trace_id=trace_id,
            request_id=request_id,
            platform=platform,
            user_id=user_id,
        )
        
        self._active_traces[request_id] = trace
        
        TRACE_COUNTER.labels(
            service=self.service_name,
            operation="start",
        ).inc()
        
        return trace
    
    def get_trace(self, request_id: str) -> Optional[DecisionTrace]:
        """Get an active or completed trace."""
        
        if request_id in self._active_traces:
            return self._active_traces[request_id]
        
        for trace in self._completed_traces:
            if trace.request_id == request_id:
                return trace
        
        return None
    
    @asynccontextmanager
    async def span(
        self,
        request_id: str,
        operation_name: str,
        attributes: Dict[str, Any] = None,
    ):
        """Context manager for creating a span."""
        
        trace = self._active_traces.get(request_id)
        
        # Find parent span
        parent_span_id = None
        for span_id, span in self._active_spans.items():
            if span.trace_id == (trace.trace_id if trace else None):
                parent_span_id = span_id
        
        # Create span
        span = Span(
            span_id=uuid4().hex[:16],
            trace_id=trace.trace_id if trace else uuid4().hex,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=time.perf_counter(),
            attributes=attributes or {},
        )
        
        self._active_spans[span.span_id] = span
        
        try:
            yield span
            span.finish("ok")
        except Exception as e:
            span.finish("error", str(e))
            raise
        finally:
            del self._active_spans[span.span_id]
            
            # Add to trace
            if trace:
                trace.spans.append({
                    "span_id": span.span_id,
                    "operation": span.operation_name,
                    "duration_ms": span.duration_ms,
                    "status": span.status,
                    "attributes": span.attributes,
                    "events": span.events,
                })
                
                trace.component_durations[operation_name] = span.duration_ms or 0
            
            # Record metrics
            SPAN_DURATION.labels(
                service=self.service_name,
                operation=operation_name,
            ).observe(span.duration_ms or 0)
    
    def add_psychological_trace(
        self,
        request_id: str,
        psychological: PsychologicalTrace,
    ) -> None:
        """Add psychological trace to decision trace."""
        
        trace = self._active_traces.get(request_id)
        if trace:
            trace.psychological = psychological
    
    def complete_trace(
        self,
        request_id: str,
        success: bool = True,
        error: Optional[str] = None,
        decision_details: Dict[str, Any] = None,
    ) -> Optional[DecisionTrace]:
        """Complete a trace."""
        
        trace = self._active_traces.pop(request_id, None)
        if not trace:
            return None
        
        trace.completed_at = datetime.now(timezone.utc)
        trace.total_duration_ms = sum(trace.component_durations.values())
        trace.success = success
        trace.error = error
        trace.decision_made = success and not error
        trace.decision_details = decision_details or {}
        
        # Add to history
        self._completed_traces.append(trace)
        
        # Trim history
        if len(self._completed_traces) > self._max_history:
            self._completed_traces = self._completed_traces[-self._max_history:]
        
        TRACE_COUNTER.labels(
            service=self.service_name,
            operation="complete" if success else "error",
        ).inc()
        
        return trace
    
    def get_recent_traces(
        self,
        limit: int = 100,
        platform: Optional[str] = None,
        errors_only: bool = False,
    ) -> List[DecisionTrace]:
        """Get recent completed traces."""
        
        traces = self._completed_traces.copy()
        
        if platform:
            traces = [t for t in traces if t.platform == platform]
        
        if errors_only:
            traces = [t for t in traces if not t.success]
        
        return traces[-limit:]
