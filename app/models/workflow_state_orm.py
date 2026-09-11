"""
Per-client UI workflow state.

The existing backend recomputes agent output on every request and does not
persist a "case" concept at all. The UI, however, needs state that survives
across requests:

  - the Case (reference, status Open/In Progress/Converted/Lost, priority)
    shown on the Home dashboard and every workflow screen
  - whether the advisor has pressed "Confirm Event" (swaps which talking
    points display)
  - which products the advisor selected (drives task orchestration)
  - the latest sentiment analysis result

All of it maps 1:1 to a customer, so it lives in a single table rather than
several -- fewer moving parts, and this state is only meaningful as a set.

This table is created automatically on application startup (see main.py), so
no manual migration step is required.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.types import JSON

from app.models.base import BaseModel


class ClientWorkflowStateORM(BaseModel):
    """Workflow + case state for one client."""

    __tablename__ = "ui_client_workflow_state"

    customer_id = Column(String(50), primary_key=True, nullable=False)

    # --- Case ---
    case_ref = Column(String(50), nullable=True)
    case_status = Column(String(30), nullable=False, default="Open")
    case_priority = Column(String(20), nullable=False, default="Medium")
    case_opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    # --- Advisor Insights step ---
    event_confirmed = Column(Boolean, nullable=False, default=False)

    # --- Client Sentiment step ---
    interaction_text = Column(Text, nullable=True)
    sentiment = Column(String(30), nullable=True)
    sentiment_score = Column(Integer, nullable=True)
    sentiment_guidance = Column(Text, nullable=True)
    primary_intent = Column(String(255), nullable=True)
    secondary_intents = Column(JSON, nullable=True, default=list)

    # --- Product selection (drives Workflow Orchestration) ---
    selected_products = Column(JSON, nullable=True, default=list)
