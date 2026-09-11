from pydantic import BaseModel, Field
from typing import List


class SentimentInsight(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    sentiment: str = Field(..., description="Detected sentiment")
    primary_intent: str = Field(..., description="Primary detected intent")
    secondary_intents: List[str] = Field(
        default_factory=list,
        description="Secondary detected intents"
    )
    engagement_score: int = Field(..., description="Customer engagement score")
    customer_confirmed_event: bool = Field(
        ...,
        description="Whether customer explicitly confirmed a life event"
    )