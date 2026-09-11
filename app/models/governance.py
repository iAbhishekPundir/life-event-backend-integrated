from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class GovernanceLog(BaseModel):
    log_id: str = Field(..., description="Unique governance log identifier")
    customer_id: str = Field(..., description="Customer identifier")
    event_id: Optional[str] = Field(default=None, description="Related life event identifier")

    step_name: str = Field(..., description="Workflow step name")
    input_source: str = Field(..., description="Source used by this step")
    confidence_score: Optional[float] = Field(
        default=None,
        description="Life event confidence score where applicable"
    )

    output: Dict[str, Any] = Field(
        default_factory=dict,
        description="Step output captured for audit traceability"
    )
    approval_status: Optional[str] = Field(
        default=None,
        description="Approval status at this workflow step"
    )
    timestamp: str = Field(..., description="Timestamp when the log was created")