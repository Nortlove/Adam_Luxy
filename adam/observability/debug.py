# =============================================================================
# ADAM Debug Mode
# Location: adam/observability/debug.py
# =============================================================================

"""
DEBUG MODE

Full capture mode for debugging psychological decisions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DebugLevel(str, Enum):
    """Debug verbosity levels."""
    
    OFF = "off"
    MINIMAL = "minimal"   # Just decisions
    STANDARD = "standard" # Decisions + atoms
    VERBOSE = "verbose"   # Everything including evidence
    FULL = "full"         # Full capture for replay


class DebugCapture(BaseModel):
    """Captured debug information for a request."""
    
    request_id: str
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Request
    request_input: Dict[str, Any] = Field(default_factory=dict)
    
    # User context
    user_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Graph queries
    graph_queries: List[Dict[str, Any]] = Field(default_factory=list)
    graph_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Blackboard states
    blackboard_snapshots: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Atom executions
    atom_inputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    atom_outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    atom_evidence: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    # Claude calls
    claude_prompts: List[Dict[str, Any]] = Field(default_factory=list)
    claude_responses: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Decision
    final_decision: Optional[Dict[str, Any]] = None
    
    # Timing
    component_timings: Dict[str, float] = Field(default_factory=dict)
    total_duration_ms: float = Field(default=0.0, ge=0.0)


class DebugMode:
    """
    Debug mode manager for full capture.
    """
    
    def __init__(
        self,
        level: DebugLevel = DebugLevel.OFF,
        max_captures: int = 100,
    ):
        self.level = level
        self.max_captures = max_captures
        
        # Active captures
        self._captures: Dict[str, DebugCapture] = {}
        
        # Completed captures
        self._completed: List[DebugCapture] = []
    
    def is_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.level != DebugLevel.OFF
    
    def should_capture(self, level: DebugLevel) -> bool:
        """Check if we should capture at given level."""
        levels = [DebugLevel.OFF, DebugLevel.MINIMAL, DebugLevel.STANDARD,
                  DebugLevel.VERBOSE, DebugLevel.FULL]
        return levels.index(self.level) >= levels.index(level)
    
    def start_capture(
        self,
        request_id: str,
        request_input: Dict[str, Any],
    ) -> DebugCapture:
        """Start capturing debug info for a request."""
        
        capture = DebugCapture(
            request_id=request_id,
            request_input=request_input,
        )
        
        self._captures[request_id] = capture
        return capture
    
    def get_capture(self, request_id: str) -> Optional[DebugCapture]:
        """Get active or completed capture."""
        
        if request_id in self._captures:
            return self._captures[request_id]
        
        for capture in self._completed:
            if capture.request_id == request_id:
                return capture
        
        return None
    
    def add_graph_query(
        self,
        request_id: str,
        query: str,
        params: Dict[str, Any],
        result: Any,
    ) -> None:
        """Add graph query to capture."""
        
        if not self.should_capture(DebugLevel.VERBOSE):
            return
        
        capture = self._captures.get(request_id)
        if capture:
            capture.graph_queries.append({
                "query": query,
                "params": params,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            capture.graph_results.append({
                "result": str(result)[:1000],  # Truncate
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    def add_blackboard_snapshot(
        self,
        request_id: str,
        zone: str,
        data: Dict[str, Any],
    ) -> None:
        """Add blackboard snapshot to capture."""
        
        if not self.should_capture(DebugLevel.STANDARD):
            return
        
        capture = self._captures.get(request_id)
        if capture:
            capture.blackboard_snapshots.append({
                "zone": zone,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    def add_atom_execution(
        self,
        request_id: str,
        atom_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        evidence: List[Dict[str, Any]] = None,
    ) -> None:
        """Add atom execution to capture."""
        
        if not self.should_capture(DebugLevel.STANDARD):
            return
        
        capture = self._captures.get(request_id)
        if capture:
            capture.atom_inputs[atom_name] = input_data
            capture.atom_outputs[atom_name] = output_data
            
            if evidence and self.should_capture(DebugLevel.VERBOSE):
                capture.atom_evidence[atom_name] = evidence
    
    def add_claude_call(
        self,
        request_id: str,
        prompt: str,
        response: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        """Add Claude call to capture."""
        
        if not self.should_capture(DebugLevel.VERBOSE):
            return
        
        capture = self._captures.get(request_id)
        if capture:
            capture.claude_prompts.append({
                "prompt": prompt[:2000],  # Truncate
                "tokens_in": tokens_in,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            capture.claude_responses.append({
                "response": response[:2000],  # Truncate
                "tokens_out": tokens_out,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    def complete_capture(
        self,
        request_id: str,
        final_decision: Dict[str, Any],
        component_timings: Dict[str, float],
        total_duration_ms: float,
    ) -> Optional[DebugCapture]:
        """Complete and store capture."""
        
        capture = self._captures.pop(request_id, None)
        if not capture:
            return None
        
        capture.final_decision = final_decision
        capture.component_timings = component_timings
        capture.total_duration_ms = total_duration_ms
        
        # Add to completed
        self._completed.append(capture)
        
        # Trim history
        if len(self._completed) > self.max_captures:
            self._completed = self._completed[-self.max_captures:]
        
        return capture
    
    def get_recent_captures(
        self,
        limit: int = 10,
    ) -> List[DebugCapture]:
        """Get recent completed captures."""
        return self._completed[-limit:]
    
    def export_for_replay(
        self,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Export capture in format suitable for replay."""
        
        capture = self.get_capture(request_id)
        if not capture:
            return None
        
        return {
            "request_id": capture.request_id,
            "captured_at": capture.captured_at.isoformat(),
            "request_input": capture.request_input,
            "user_context": capture.user_context,
            "atom_inputs": capture.atom_inputs,
            "atom_outputs": capture.atom_outputs,
            "final_decision": capture.final_decision,
            "total_duration_ms": capture.total_duration_ms,
        }
