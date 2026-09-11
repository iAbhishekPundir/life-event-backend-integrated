from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.sentiment_agent import SentimentAgent

router = APIRouter()
sentiment_agent = SentimentAgent()


class SentimentRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    conversation_text: str = Field(..., description="Conversation text")
    conversation_permitted: bool = Field(
        default=True,
        description="Whether conversation analysis is permitted"
    )


@router.post("/analyze")
def analyze_sentiment(request: SentimentRequest):
    """
    Analyzes customer conversation text for sentiment, intent,
    and engagement score.
    """

    return sentiment_agent.analyze(
        customer_id=request.customer_id,
        conversation_text=request.conversation_text,
        conversation_permitted=request.conversation_permitted
    )