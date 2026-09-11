from app.models.transaction import TransactionEvaluationRequest
from app.agents.event_detection_agent import EventDetectionAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.risk_compliance_agent import RiskComplianceAgent
from app.agents.advisor_insights_agent import AdvisorInsightsAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.workflow_orchestration_agent import WorkflowOrchestrationAgent
from app.agents.governance_engine import GovernanceEngine


class OrchestrationService:
    """
    Runs the complete Life Event workflow step by step.

    Flow:
    1. Detect life event from transaction signals.
    2. Stop if confidence is below threshold.
    3. Generate recommendations.
    4. Validate compliance.
    5. Generate advisor insights.
    6. Analyze sentiment if permitted.
    7. Create workflow tasks.
    8. Store governance logs.
    9. Keep customer-facing recommendations blocked until human approval.
    """

    def __init__(self):
        self.event_agent = EventDetectionAgent()
        self.recommendation_agent = RecommendationAgent()
        self.compliance_agent = RiskComplianceAgent()
        self.advisor_agent = AdvisorInsightsAgent()
        self.sentiment_agent = SentimentAgent()
        self.workflow_agent = WorkflowOrchestrationAgent()
        self.governance = GovernanceEngine()

    def run(self, request: TransactionEvaluationRequest):
        customer_id = request.customer.customer_id

        life_event = self.event_agent.detect(request)

        self.governance.record(
            customer_id=customer_id,
            event_id=life_event.event_id,
            step_name="Event Detection",
            input_source="Transaction Data",
            confidence_score=life_event.confidence_score,
            output=life_event.model_dump(),
            approval_status="Not Started"
        )

        if not life_event.actionable:
            self.governance.record(
                customer_id=customer_id,
                event_id=life_event.event_id,
                step_name="Actionability Check",
                input_source="Life Event Insight",
                confidence_score=life_event.confidence_score,
                output={
                    "status": "Stopped",
                    "reason": "Confidence score below threshold",
                    "life_event_type": life_event.life_event_type,
                    "confidence_score": life_event.confidence_score
                },
                approval_status="Not Required"
            )

            return {
                "status": "Stopped",
                "reason": "Confidence score below threshold",
                "life_event": life_event,
                "recommendations": [],
                "compliance": None,
                "advisor_insight": None,
                "sentiment": None,
                "workflow_tasks": [],
                "approval_required": False,
                "customer_facing_recommendation_allowed": False
            }

        recommendations = self.recommendation_agent.generate(
            request.customer,
            life_event
        )

        self.governance.record(
            customer_id=customer_id,
            event_id=life_event.event_id,
            step_name="Recommendation Generation",
            input_source="Life Event Insight",
            confidence_score=life_event.confidence_score,
            output={
                "recommendations": [
                    recommendation.model_dump()
                    for recommendation in recommendations
                ]
            },
            approval_status="Pending Human Approval"
        )

        compliance = self.compliance_agent.validate(
            request,
            life_event,
            recommendations
        )

        self.governance.record(
            customer_id=customer_id,
            event_id=life_event.event_id,
            step_name="Compliance Validation",
            input_source="Customer Data and Recommendations",
            confidence_score=life_event.confidence_score,
            output=compliance.model_dump(),
            approval_status="Pending Human Approval"
        )

        advisor_insight = self.advisor_agent.generate(
            request.customer,
            life_event,
            recommendations,
            compliance
        )

        self.governance.record(
            customer_id=customer_id,
            event_id=life_event.event_id,
            step_name="Advisor Insight Generation",
            input_source="Life Event, Recommendations, and Compliance Result",
            confidence_score=life_event.confidence_score,
            output=advisor_insight.model_dump(),
            approval_status="Pending Human Approval"
        )

        sentiment = self.sentiment_agent.analyze(
            customer_id=customer_id,
            conversation_text=request.conversation_text or "",
            conversation_permitted=request.conversation_permitted
        )

        self.governance.record(
            customer_id=customer_id,
            event_id=life_event.event_id,
            step_name="Sentiment Analysis",
            input_source="Conversation Data",
            confidence_score=life_event.confidence_score,
            output=sentiment.model_dump(),
            approval_status="Pending Human Approval"
        )

        workflow_tasks = self.workflow_agent.create_tasks(
            customer_id=customer_id,
            life_event=life_event,
            compliance=compliance
        )

        self.governance.record(
            customer_id=customer_id,
            event_id=life_event.event_id,
            step_name="Workflow Orchestration",
            input_source="Advisor Insight and Compliance Result",
            confidence_score=life_event.confidence_score,
            output={
                "workflow_tasks": [
                    task.model_dump()
                    for task in workflow_tasks
                ]
            },
            approval_status="Pending Human Approval"
        )

        return {
            "status": "Completed",
            "life_event": life_event,
            "recommendations": recommendations,
            "compliance": compliance,
            "advisor_insight": advisor_insight,
            "sentiment": sentiment,
            "workflow_tasks": workflow_tasks,
            "approval_required": True,
            "customer_facing_recommendation_allowed": False,
            "message": "Recommendations require human approval before customer presentation."
        }


orchestration_service = OrchestrationService()