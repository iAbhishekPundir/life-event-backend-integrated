from typing import Any, Dict, Optional

from app.services.audit_service import audit_service


class GovernanceEngine:
    """
    Stores governance and audit logs.

    Responsibilities:
    - Log AI-generated life event insights.
    - Log recommendation outputs.
    - Log compliance outcomes.
    - Log workflow actions.
    - Log approval status.
    - Maintain traceability from input signal to final advisor action.
    """

    def record(
        self,
        customer_id: str,
        step_name: str,
        input_source: str,
        output: Dict[str, Any],
        event_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        approval_status: Optional[str] = None
    ):
        return audit_service.log(
            customer_id=customer_id,
            event_id=event_id,
            step_name=step_name,
            input_source=input_source,
            confidence_score=confidence_score,
            output=output,
            approval_status=approval_status
        )

    def get_logs(self):
        return audit_service.get_logs()

    def get_customer_logs(self, customer_id: str):
        return audit_service.get_customer_logs(customer_id)

    def get_event_logs(self, event_id: str):
        logs = self.get_logs()
        return [
            log for log in logs
            if log.get("event_id") == event_id
        ]

    def get_step_logs(self, step_name: str):
        logs = self.get_logs()
        return [
            log for log in logs
            if log.get("step_name") == step_name
        ]