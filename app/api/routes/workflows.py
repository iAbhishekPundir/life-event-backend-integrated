from fastapi import APIRouter

from app.models.transaction import TransactionEvaluationRequest
from app.agents.event_detection_agent import EventDetectionAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.risk_compliance_agent import RiskComplianceAgent
from app.agents.workflow_orchestration_agent import WorkflowOrchestrationAgent

router = APIRouter()
event_agent = EventDetectionAgent()
recommendation_agent = RecommendationAgent()
compliance_agent = RiskComplianceAgent()
workflow_agent = WorkflowOrchestrationAgent()


@router.post("/create")
def create_workflow_tasks(request: TransactionEvaluationRequest):
    """
    Creates workflow tasks after life event detection,
    recommendation generation, and compliance validation.
    """

    life_event = event_agent.detect(request)

    if not life_event.actionable:
        return {
            "status": "Stopped",
            "reason": "Life event confidence score is below threshold",
            "life_event": life_event,
            "workflow_tasks": []
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

    workflow_tasks = workflow_agent.create_tasks(
        customer_id=request.customer.customer_id,
        life_event=life_event,
        compliance=compliance
    )

    return {
        "status": "Completed",
        "life_event": life_event,
        "compliance": compliance,
        "workflow_tasks": workflow_tasks
    }