"""Report models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    campaign_id: str
    organization_id: str
    tier: str
    period_start: str
    period_end: str
    report_data: Dict[str, Any]
    generated_at: str
    generated_by: str = "dcil"
    viewed_by_client: bool = False
    viewed_at: Optional[str] = None


class ReportList(BaseModel):
    reports: List[ReportResponse]
    total: int
