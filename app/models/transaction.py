from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.customer import Customer


class Transaction(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    merchant_category: str = Field(..., description="Merchant category")
    transaction_amount: float = Field(..., description="Transaction amount")
    transaction_date: str = Field(..., description="Transaction date")
    frequency: Optional[int] = Field(default=1, description="Transaction frequency")
    location: Optional[str] = Field(default=None, description="Transaction location")
    description: Optional[str] = Field(default=None, description="Transaction description")


class TransactionEvaluationRequest(BaseModel):
    customer: Customer
    transactions: List[Transaction]

    conversation_text: Optional[str] = Field(
        default=None,
        description="Customer conversation text if available and permitted"
    )
    conversation_permitted: bool = Field(
        default=False,
        description="Whether conversation analysis is permitted"
    )

    kyc_status: str = Field(
        default="valid",
        description="Customer KYC status"
    )
    nominee_available: bool = Field(
        default=False,
        description="Whether nominee information is available"
    )
    joint_account_eligible: bool = Field(
        default=True,
        description="Whether customer is eligible for joint account"
    )
    communication_consent: bool = Field(
        default=True,
        description="Whether customer has communication consent"
    )