from pydantic import BaseModel, Field
from typing import List


class AdvisorInsight(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    customer_name: str = Field(..., description="Customer name")
    life_event_type: str = Field(..., description="Detected life event type")
    confidence_score: float = Field(..., description="Life event confidence score")

    key_drivers: List[str] = Field(
        default_factory=list,
        description="Key drivers for detected life event"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendation names"
    )

    compliance_status: str = Field(..., description="Compliance status")
    approval_status: str = Field(..., description="Approval status")

    suggested_talking_points: List[str] = Field(
        default_factory=list,
        description="Advisor talking points"
    )
    key_opportunities: List[str] = Field(
        default_factory=list,
        description="Key financial planning opportunities"
    )
    next_best_action: str = Field(..., description="Recommended next action")