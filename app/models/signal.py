from pydantic import BaseModel, Field
from typing import Optional


class Signal(BaseModel):
    signal_name: str = Field(..., description="Name of the detected signal")
    matched: bool = Field(..., description="Whether the signal matched")
    source: str = Field(..., description="Signal source, such as Transaction Data")
    confidence_contribution: float = Field(
        ...,
        description="Contribution to confidence score"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason explaining why the signal matched or did not match"
    )