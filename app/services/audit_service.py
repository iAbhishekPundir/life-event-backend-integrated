from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


class AuditService:
    """
    In-memory audit service for starter implementation.

    Responsibilities:
    - Store decision logs.
    - Store AI insight logs.
    - Store recommendation logs.
    - Store compliance outcome logs.
    - Store workflow action logs.
    - Support traceability from input signal to final advisor action.

    Note:
    This is in-memory only. Logs will reset when the server restarts.
    Replace this with database persistence for production.
    """

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log(
        self,
        customer_id: str,
        step_name: str,
        input_source: str,
        output: Dict[str, Any],
        event_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        approval_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = {
            "log_id": f"LOG-{uuid4().hex[:8].upper()}",
            "customer_id": customer_id,
            "event_id": event_id,
            "step_name": step_name,
            "input_source": input_source,
            "confidence_score": confidence_score,
            "output": output,
            "approval_status": approval_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.logs.append(record)
        return record

    def get_logs(self) -> List[Dict[str, Any]]:
        return self.logs

    def get_customer_logs(self, customer_id: str) -> List[Dict[str, Any]]:
        return [
            log for log in self.logs
            if log.get("customer_id") == customer_id
        ]

    def get_event_logs(self, event_id: str) -> List[Dict[str, Any]]:
        return [
            log for log in self.logs
            if log.get("event_id") == event_id
        ]

    def get_step_logs(self, step_name: str) -> List[Dict[str, Any]]:
        return [
            log for log in self.logs
            if log.get("step_name") == step_name
        ]

    def clear_logs(self) -> Dict[str, Any]:
        count = len(self.logs)
        self.logs.clear()

        return {
            "status": "cleared",
            "records_removed": count
        }


audit_service = AuditService()