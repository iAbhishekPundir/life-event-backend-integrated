from pydantic import BaseModel, Field
from typing import List


class ComplianceResult(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    event_id: str = Field(..., description="Related life event identifier")

    kyc_status: str = Field(..., description="KYC validation result")
    nominee_status: str = Field(..., description="Nominee validation result")
    joint_account_eligibility: str = Field(
        ...,
        description="Joint account eligibility result"
    )
    regulatory_disclosures: List[str] = Field(
        default_factory=list,
        description="Required regulatory disclosures"
    )
    product_suitability: str = Field(
        ...,
        description="Product suitability result"
    )
    communication_consent: str = Field(
        ...,
        description="Communication consent result"
    )
    final_status: str = Field(
        ...,
        description="Final compliance status"
    )
    blocked_reasons: List[str] = Field(
        default_factory=list,
        description="Reasons if recommendation is blocked or requires review"
    )