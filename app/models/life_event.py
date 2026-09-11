from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.signal import Signal


class LifeEventInsight(BaseModel):
    event_id: str = Field(..., description="Unique life event identifier")
    customer_id: str = Field(..., description="Customer identifier")
    life_event_type: str = Field(..., description="Detected life event type")
    confidence_score: float = Field(..., description="Confidence score for detected event")
    score_source: str = "UNKNOWN"
    estimated_timeline: str = Field(..., description="Estimated life event timeline")

    key_drivers: List[str] = Field(
        default_factory=list,
        description="Signals explaining why the event was detected"
    )

    signals: List[Signal] = Field(
        default_factory=list,
        description="Detailed signal evaluation results"
    )

    actionable: bool = Field(
        ...,
        description="Whether the event qualifies for downstream processing"
    )

    status: str = Field(..., description="Detection status")

    ai_summary: Optional[str] = Field(
        default=None,
        description="LLM-generated advisor summary"
    )

    advisor_talking_points: List[str] = Field(
        default_factory=list,
        description="LLM-generated advisor talking points"
    )

    approval_status: str = Field(
        default="Pending Human Approval",
        description="Human approval status"
    )

    customer_facing_allowed: bool = Field(
        default=False,
        description="Whether insight can be shown to customer"
    )