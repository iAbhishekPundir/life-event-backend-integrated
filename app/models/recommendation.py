from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    recommendation_id: str = Field(..., description="Unique recommendation identifier")
    customer_id: str = Field(..., description="Customer identifier")
    event_id: str = Field(..., description="Related life event identifier")
    life_event_type: str = Field(..., description="Detected life event type")
    recommendation_name: str = Field(..., description="Recommendation name")
    rationale: str = Field(..., description="Recommendation rationale for advisor review")
    rank: int = Field(..., description="Recommendation rank")
    compliance_status: str = Field(
        default="Pending",
        description="Compliance status for this recommendation"
    )
    approval_status: str = Field(
        default="Pending Human Approval",
        description="Human approval status"
    )
    customer_facing_allowed: bool = Field(
        default=False,
        description="Whether this recommendation can be shown to the customer"
    )