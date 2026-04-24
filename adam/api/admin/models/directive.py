"""DCIL directive models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DirectiveResponse(BaseModel):
    id: str
    campaign_id: str
    directive_type: str
    status: str
    campaign_archetype_id: Optional[str] = None
    parameter: Optional[str] = None
    current_value: Any = None
    proposed_value: Any = None
    source_finding_id: Optional[str] = None
    rationale: Optional[str] = None
    bilateral_evidence: Optional[str] = None
    scope: Optional[str] = None
    i_squared: Optional[float] = None
    confidence: Optional[float] = None
    expected_impact: Optional[str] = None
    expected_lift_pct: Optional[float] = None
    rollback_conditions: List[str] = []
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    executed_at: Optional[str] = None
    execution_result: Optional[str] = None
    rolled_back_at: Optional[str] = None
    rollback_reason: Optional[str] = None
    created_at: str
    updated_at: str


class DirectiveApprove(BaseModel):
    review_notes: Optional[str] = None


class DirectiveBlock(BaseModel):
    review_notes: str


class DirectiveList(BaseModel):
    directives: List[DirectiveResponse]
    total: int
    pending: int = 0
    approved: int = 0
    executed: int = 0


class DCILStatus(BaseModel):
    campaign_id: str
    dcil_enabled: bool
    auto_execute: bool
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    pending_directives: int = 0
    executed_today: int = 0
    rolled_back_today: int = 0
    safety_rails: Dict[str, Any] = {}
    hypothesis_results: List[Dict[str, Any]] = []
    learning_state: Dict[str, Any] = {}
