"""
GET /api/workflow-steps - the step definitions, from Postgres.

Filtered against Capability Compass's currently configured subprocesses for
Wealth Client Prospecting -- an admin there controls which of these steps
this app shows. If Compass is unreachable, all steps are returned unfiltered
rather than breaking the UI over a third-party dependency.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ui_schemas as ui
from app.db.database import get_db
from app.models.workflow_step_orm import WorkflowStepORM
from app.services.capability_compass_client import get_active_subprocess_names

router = APIRouter(prefix="/api/workflow-steps", tags=["UI - Workflow Steps"])


@router.get("", response_model=List[ui.WorkflowStepOut])
def list_workflow_steps(db: Session = Depends(get_db)):
    rows = db.query(WorkflowStepORM).order_by(WorkflowStepORM.step_number).all()

    active_names = get_active_subprocess_names()
    if active_names is not None:
        rows = [r for r in rows if r.title in active_names]

    return [
        ui.WorkflowStepOut(
            id=r.id,
            step_number=r.step_number,
            icon=r.icon,
            title=r.title,
            short_description=r.short_description,
            role=r.role,
            tag=r.tag,
            agent_name=r.agent_name,
            no_signal_summary=r.no_signal_summary or "",
        )
        for r in rows
    ]
