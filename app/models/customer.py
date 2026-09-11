from pydantic import BaseModel, Field
from typing import Optional


class Customer(BaseModel):
    customer_id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer full name")
    age: Optional[int] = Field(default=None, description="Customer age")
    annual_income: Optional[float] = Field(default=None, description="Customer annual income")
    segment: Optional[str] = Field(default=None, description="Customer segment")
    relationship_manager: Optional[str] = Field(default=None, description="Assigned relationship manager")