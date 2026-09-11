from fastapi import APIRouter

from app.models.transaction import TransactionEvaluationRequest
from app.services.orchestration_service import orchestration_service

router = APIRouter()


@router.post("/evaluate")
def evaluate_transactions(request: TransactionEvaluationRequest):
    """
    Runs the full transaction-driven life event workflow.

    Flow:
    - Event detection
    - Recommendation generation
    - Compliance validation
    - Advisor insight generation
    - Sentiment analysis
    - Workflow task creation
    - Governance logging
    """

    return orchestration_service.run(request)