from fastapi import APIRouter

from app.agents.governance_engine import GovernanceEngine
from app.services.audit_service import audit_service

router = APIRouter()
governance = GovernanceEngine()


@router.get("/logs")
def get_all_logs():
    """
    Returns all governance logs.
    """

    return governance.get_logs()


@router.get("/logs/customer/{customer_id}")
def get_customer_logs(customer_id: str):
    """
    Returns governance logs for a customer.
    """

    return governance.get_customer_logs(customer_id)


@router.get("/logs/event/{event_id}")
def get_event_logs(event_id: str):
    """
    Returns governance logs for a life event.
    """

    return governance.get_event_logs(event_id)


@router.get("/logs/step/{step_name}")
def get_step_logs(step_name: str):
    """
    Returns governance logs for a workflow step.
    """

    return governance.get_step_logs(step_name)


@router.delete("/logs")
def clear_logs():
    """
    Clears in-memory governance logs.

    Use only for local development/testing.
    """

    return audit_service.clear_logs()