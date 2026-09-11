from typing import List
from uuid import uuid4

from app.models.life_event import LifeEventInsight
from app.models.compliance import ComplianceResult
from app.models.workflow import WorkflowTask
from app.services.rule_loader_service import RuleLoaderService


class WorkflowOrchestrationAgent:
    """
    Creates operational workflow tasks after:
    - Life event detection.
    - Recommendation generation.
    - Compliance validation.
    - Advisor insight generation.

    Tasks can include:
    - CRM task.
    - Advisor notification.
    - Review meeting.
    - Insurance review.
    - KYC update.
    - Nominee update.
    """

    def __init__(self):
        self.rule_loader = RuleLoaderService()

    def create_tasks(
        self,
        customer_id: str,
        life_event: LifeEventInsight,
        compliance: ComplianceResult
    ) -> List[WorkflowTask]:
        mappings = self.rule_loader.load_workflow_mappings()
        task_templates = mappings.get(life_event.life_event_type, [])

        tasks: List[WorkflowTask] = []

        for template in task_templates:
            tasks.append(
                WorkflowTask(
                    task_id=f"TASK-{uuid4().hex[:8].upper()}",
                    customer_id=customer_id,
                    event_id=life_event.event_id,
                    task_name=template["task_name"],
                    task_type=template["task_type"],
                    assigned_to=template["assigned_to"],
                    status="Open"
                )
            )

        compliance_tasks = self._create_compliance_follow_up_tasks(
            customer_id=customer_id,
            life_event=life_event,
            compliance=compliance
        )

        tasks.extend(compliance_tasks)

        return tasks

    def _create_compliance_follow_up_tasks(
        self,
        customer_id: str,
        life_event: LifeEventInsight,
        compliance: ComplianceResult
    ) -> List[WorkflowTask]:
        tasks: List[WorkflowTask] = []

        if compliance.kyc_status != "Valid":
            tasks.append(
                WorkflowTask(
                    task_id=f"TASK-{uuid4().hex[:8].upper()}",
                    customer_id=customer_id,
                    event_id=life_event.event_id,
                    task_name="KYC Update",
                    task_type="Operations",
                    assigned_to="Operations Team",
                    status="Open"
                )
            )

        if compliance.nominee_status == "Review Required":
            tasks.append(
                WorkflowTask(
                    task_id=f"TASK-{uuid4().hex[:8].upper()}",
                    customer_id=customer_id,
                    event_id=life_event.event_id,
                    task_name="Nominee Review",
                    task_type="Operations",
                    assigned_to="Operations Team",
                    status="Open"
                )
            )

        if compliance.final_status == "Blocked":
            tasks.append(
                WorkflowTask(
                    task_id=f"TASK-{uuid4().hex[:8].upper()}",
                    customer_id=customer_id,
                    event_id=life_event.event_id,
                    task_name="Compliance Blocker Review",
                    task_type="Compliance",
                    assigned_to="Compliance Team",
                    status="Open"
                )
            )

        return tasks