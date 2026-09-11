from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.governance_engine import GovernanceEngine

router = APIRouter()
governance = GovernanceEngine()


class ApprovalRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    event_id: str = Field(..., description="Life event identifier")
    recommendation_id: str = Field(..., description="Recommendation identifier")
    approved: bool = Field(..., description="Approval decision")
    approver: str = Field(..., description="Approver name or ID")
    comments: str = Field(default="", description="Approval comments")


@router.post("/submit")
def submit_approval(request: ApprovalRequest):
    """
    Submits human approval decision.

    Recommendations can become customer-facing only after approval.
    """

    approval_status = "Approved" if request.approved else "Rejected"

    log = governance.record(
        customer_id=request.customer_id,
        event_id=request.event_id,
        step_name="Human Approval",
        input_source="Advisor or Compliance User",
        output=request.model_dump(),
        approval_status=approval_status
    )

    return {
        "status": "Completed",
        "recommendation_id": request.recommendation_id,
        "approval_status": approval_status,
        "customer_facing_allowed": request.approved,
        "governance_log": log
    }