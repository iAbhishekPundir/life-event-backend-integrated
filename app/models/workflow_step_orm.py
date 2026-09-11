"""Workflow step definitions - the 5 steps the UI renders."""
from sqlalchemy import Column, Integer, String, Text

from app.models.base import BaseModel


class WorkflowStepORM(BaseModel):
    __tablename__ = "workflow_steps"

    id = Column(String(64), primary_key=True)          # slug used in the UI route
    step_number = Column(Integer, nullable=False)
    icon = Column(String(64), nullable=False)           # lucide-react icon name
    title = Column(String(150), nullable=False)
    short_description = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    tag = Column(String(200), nullable=False)
    agent_name = Column(String(150), nullable=False)
    no_signal_summary = Column(Text, nullable=False, default="")
