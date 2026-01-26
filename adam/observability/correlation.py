# =============================================================================
# ADAM Correlation Context
# Location: adam/observability/correlation.py
# =============================================================================

"""
CORRELATION CONTEXT

Request correlation for distributed tracing.
"""

import contextvars
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4


# Context variable for request correlation
_correlation_context: contextvars.ContextVar[Optional["CorrelationContext"]] = \
    contextvars.ContextVar("correlation_context", default=None)


@dataclass
class CorrelationContext:
    """Context for correlating requests across services."""
    
    request_id: str
    trace_id: str
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    
    # Business context
    user_id: Optional[str] = None
    platform: Optional[str] = None
    
    # Additional context
    baggage: Dict[str, str] = None
    
    def __post_init__(self):
        if self.baggage is None:
            self.baggage = {}
    
    @classmethod
    def create(
        cls,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> "CorrelationContext":
        """Create a new correlation context."""
        return cls(
            request_id=request_id or uuid4().hex,
            trace_id=uuid4().hex,
            user_id=user_id,
            platform=platform,
        )
    
    @classmethod
    def from_headers(
        cls,
        headers: Dict[str, str],
    ) -> "CorrelationContext":
        """Create context from HTTP headers."""
        return cls(
            request_id=headers.get("x-request-id", uuid4().hex),
            trace_id=headers.get("x-trace-id", uuid4().hex),
            span_id=headers.get("x-span-id"),
            parent_span_id=headers.get("x-parent-span-id"),
            user_id=headers.get("x-user-id"),
            platform=headers.get("x-platform"),
        )
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for propagation."""
        headers = {
            "x-request-id": self.request_id,
            "x-trace-id": self.trace_id,
        }
        
        if self.span_id:
            headers["x-span-id"] = self.span_id
            headers["x-parent-span-id"] = self.span_id  # Current becomes parent
        
        if self.user_id:
            headers["x-user-id"] = self.user_id
        
        if self.platform:
            headers["x-platform"] = self.platform
        
        for key, value in self.baggage.items():
            headers[f"x-baggage-{key}"] = value
        
        return headers
    
    def new_span(self) -> "CorrelationContext":
        """Create a child context for a new span."""
        return CorrelationContext(
            request_id=self.request_id,
            trace_id=self.trace_id,
            span_id=uuid4().hex[:16],
            parent_span_id=self.span_id,
            user_id=self.user_id,
            platform=self.platform,
            baggage=self.baggage.copy(),
        )
    
    def add_baggage(self, key: str, value: str) -> None:
        """Add baggage item."""
        self.baggage[key] = value


def get_correlation_context() -> Optional[CorrelationContext]:
    """Get the current correlation context."""
    return _correlation_context.get()


def set_correlation_context(ctx: CorrelationContext) -> contextvars.Token:
    """Set the current correlation context."""
    return _correlation_context.set(ctx)


def clear_correlation_context(token: contextvars.Token) -> None:
    """Clear the correlation context."""
    _correlation_context.reset(token)
