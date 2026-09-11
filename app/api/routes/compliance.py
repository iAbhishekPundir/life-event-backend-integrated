from fastapi import APIRouter

from app.models.transaction import TransactionEvaluationRequest
from app.agents.event_detection_agent import EventDetectionAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.risk_compliance_agent import RiskComplianceAgent

router = APIRouter()
event_agent = EventDetectionAgent()
recommendation_agent = RecommendationAgent()
compliance_agent = RiskComplianceAgent()


@router.post("/validate")
def validate_compliance(request: TransactionEvaluationRequest):
    """
    Validates KYC, nominee, eligibility, disclosures, suitability,
    and communication consent for generated recommendations.
    """

    life_event = event_agent.detect(request)

    if not life_event.actionable:
        return {
            "status": "Stopped",
            "reason": "Life event confidence score is below threshold",
            "life_event": life_event,
            "recommendations": [],
            "compliance": None
        }

    recommendations = recommendation_agent.generate(
        customer=request.customer,
        life_event=life_event
    )

    compliance = compliance_agent.validate(
        request=request,
        life_event=life_event,
        recommendations=recommendations
    )

    return {
        "status": "Completed",
        "life_event": life_event,
        "recommendations": recommendations,
        "compliance": compliance
    }