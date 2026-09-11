from pydantic import BaseModel, Field
from typing import Optional


class WorkflowTask(BaseModel):
    task_id: str = Field(..., description="Unique workflow task identifier")
    customer_id: str = Field(..., description="Customer identifier")
    event_id: str = Field(..., description="Related life event identifier")
    task_name: str = Field(..., description="Task name")
    task_type: str = Field(..., description="Task type")
    assigned_to: str = Field(..., description="Assigned team or role")
    status: str = Field(default="Open", description="Workflow task status")
    due_date: Optional[str] = Field(default=None, description="Optional task due date")