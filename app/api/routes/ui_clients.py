"""
UI compatibility API — /api/clients/*

This router exposes exactly the endpoints the React frontend
(life-event-app) consumes, in exactly the shapes it expects. It is a thin
wrapper: it calls the existing agents, persists the workflow state the UI
needs, and maps the results through ui_mapper_service.

Nothing in app/agents/, app/ml/, or app/rules/ is modified. The existing
routes (/dashboard, /life-events/detect/..., etc.) remain available and
unchanged, so any tooling already pointing at them keeps working.

Endpoint list:
    GET    /api/clients
    GET    /api/clients/{client_id}
    POST   /api/clients/{client_id}/detect
    GET    /api/clients/{client_id}/detection
    POST   /api/clients/{client_id}/recommendations
    GET    /api/clients/{client_id}/recommendations
    POST   /api/clients/{client_id}/advisor-brief
    GET    /api/clients/{client_id}/advisor-brief
    POST   /api/clients/{client_id}/confirm-event
    POST   /api/clients/{client_id}/sentiment
    GET    /api/clients/{client_id}/sentiment
    POST   /api/clients/{client_id}/sentiment/auto-select
    PATCH  /api/clients/{client_id}/sentiment/products
    POST   /api/clients/{client_id}/orchestrate
    GET    /api/clients/{client_id}/orchestrate
    PATCH  /api/clients/{client_id}/case-status
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.advisor_insights_agent import AdvisorInsightsAgent
from app.agents.event_detection_agent import EventDetectionAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.risk_compliance_agent import RiskComplianceAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.workflow_orchestration_agent import WorkflowOrchestrationAgent
from app.api.schemas import ui_schemas as ui
from app.db.database import get_db
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionEvaluationRequest
from app.models.workflow_state_orm import ClientWorkflowStateORM
from app.repositories.customer_repository import CustomerRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services import ui_mapper_service as mapper

logger = logging.getLogger(__name__)

router = APIRouter()

customer_repository = CustomerRepository()
transaction_repository = TransactionRepository()

event_detection_agent = EventDetectionAgent()
recommendation_agent = RecommendationAgent()
risk_compliance_agent = RiskComplianceAgent()
advisor_insights_agent = AdvisorInsightsAgent()
sentiment_agent = SentimentAgent()
workflow_agent = WorkflowOrchestrationAgent()

MIN_SENTIMENT_WORDS = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_customer_or_404(db: Session, client_id: str) -> Dict[str, Any]:
    customer_data = customer_repository.get_customer_by_id(db, client_id)
    if not customer_data:
        raise HTTPException(status_code=404, detail=f"No client found with id '{client_id}'")
    return customer_data


FREQUENCY_LABEL_TO_COUNT = {
    "one-time": 1,
    "one time": 1,
    "once": 1,
    "onetime": 1,
    "occasional": 3,
    "monthly": 12,
    "recurring": 12,
    "weekly": 52,
    "daily": 365,
    "annual": 1,
    "yearly": 1,
}


def _coerce_frequency(value: Any) -> int:
    """
    The Transaction model types `frequency` as an int (an occurrence count),
    but the database column is free text and may hold either a number
    ("12") or a label ("Recurring"). Coerce rather than let a text value
    raise a ValidationError and take out the whole detection call.
    """
    if value is None:
        return 1
    if isinstance(value, bool):
        return 1
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = str(value).strip()
    if not text:
        return 1
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return FREQUENCY_LABEL_TO_COUNT.get(text.lower(), 1)


def _build_evaluation_request(
    customer_data: Dict[str, Any],
    transaction_rows: List[Dict[str, Any]],
    conversation_text: Optional[str] = None,
) -> TransactionEvaluationRequest:
    """Builds the request object the existing agents expect."""
    customer = Customer(
        customer_id=customer_data["customer_id"],
        name=customer_data.get("name") or "Unknown",
        age=customer_data.get("age"),
        annual_income=float(customer_data["annual_income"]) if customer_data.get("annual_income") else None,
        segment=customer_data.get("segment"),
        relationship_manager=customer_data.get("relationship_manager"),
    )

    transactions = []
    for row in transaction_rows:
        try:
            amount = float(row.get("transaction_amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        transactions.append(
            Transaction(
                transaction_id=row.get("transaction_id") or "",
                merchant_category=row.get("merchant_category") or "",
                transaction_amount=amount,
                transaction_date=str(row.get("transaction_date") or ""),
                frequency=_coerce_frequency(row.get("frequency")),
                location=row.get("location"),
                description=row.get("description"),
            )
        )

    return TransactionEvaluationRequest(
        customer=customer,
        transactions=transactions,
        conversation_text=conversation_text,
        conversation_permitted=bool(conversation_text),
        kyc_status=customer_data.get("kyc_status", "Valid"),
        nominee_available=customer_data.get("nominee_available", False),
        joint_account_eligible=customer_data.get("joint_account_eligible", True),
        communication_consent=customer_data.get("communication_consent", True),
    )


def _run_detection(db: Session, client_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
    """
    Runs the Event Detection agent. Returns (customer_data, transaction_rows,
    life_event). life_event is None when the customer has no transactions --
    treated as "no signal" rather than an error, because the UI shows those
    clients as a legitimate 'no life events detected' card.
    """
    customer_data = _get_customer_or_404(db, client_id)
    transaction_rows = transaction_repository.get_transactions_by_customer_id(db=db, customer_id=client_id) or []

    if not transaction_rows:
        return customer_data, [], None

    request = _build_evaluation_request(customer_data, transaction_rows)
    life_event = event_detection_agent.detect(request)
    return customer_data, transaction_rows, life_event


def _get_or_create_state(db: Session, client_id: str) -> ClientWorkflowStateORM:
    state = db.query(ClientWorkflowStateORM).filter(
        ClientWorkflowStateORM.customer_id == client_id
    ).first()

    if state is None:
        state = ClientWorkflowStateORM(
            customer_id=client_id,
            case_status="Open",
            case_priority="Medium",
            event_confirmed=False,
            selected_products=[],
            secondary_intents=[],
        )
        db.add(state)
        db.commit()
        db.refresh(state)

    return state


def _next_case_ref(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"CASE-{year}-"
    count = db.query(ClientWorkflowStateORM).filter(
        ClientWorkflowStateORM.case_ref.like(f"{prefix}%")
    ).count()
    return f"{prefix}{count + 1:04d}"


def _ensure_case(db: Session, client_id: str, life_event: Any) -> ClientWorkflowStateORM:
    """
    Opens a case the first time a life event is detected for a client. The
    UI shows the case badge from the very first view, so it must exist as
    soon as detection succeeds -- not at the orchestration step.
    """
    state = _get_or_create_state(db, client_id)

    if not state.case_ref and life_event is not None and getattr(life_event, "actionable", False):
        confidence = float(getattr(life_event, "confidence_score", 0.0) or 0.0)
        state.case_ref = _next_case_ref(db)
        state.case_status = "Open"
        state.case_priority = mapper.priority_from_confidence(confidence)
        state.case_opened_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(state)

    return state


def _require_actionable_event(db: Session, client_id: str):
    """Shared guard for the steps that depend on a detected event."""
    customer_data, transaction_rows, life_event = _run_detection(db, client_id)

    if life_event is None or not getattr(life_event, "actionable", False):
        raise HTTPException(
            status_code=409,
            detail=f"No actionable life event for this client. Run POST /api/clients/{client_id}/detect first.",
        )

    return customer_data, transaction_rows, life_event


def _generate_recommendations(customer_data, transaction_rows, life_event) -> List[Dict[str, Any]]:
    """Runs the Recommendation agent and maps the output to the UI shape."""
    request = _build_evaluation_request(customer_data, transaction_rows)
    raw_recommendations = recommendation_agent.generate(
        customer=request.customer,
        life_event=life_event,
    )
    return mapper.map_recommendations(raw_recommendations, life_event, customer_data)


def _detection_payload(
    customer_data: Dict[str, Any],
    transaction_rows: List[Dict[str, Any]],
    life_event: Any,
    state: Optional[ClientWorkflowStateORM],
) -> ui.DetectionResultOut:
    if life_event is None or str(getattr(life_event, "life_event_type", "Unknown")) == "Unknown":
        return ui.DetectionResultOut(detected=False)

    confidence = float(getattr(life_event, "confidence_score", 0.0) or 0.0)
    case = mapper.map_case(state) if state else None

    return ui.DetectionResultOut(
        detected=True,
        event_name=getattr(life_event, "life_event_type", None),
        confidence=round(confidence, 4),
        timeline=getattr(life_event, "estimated_timeline", None),
        ai_summary=getattr(life_event, "ai_summary", None) or _fallback_summary(life_event, transaction_rows),
        event_source="Bank Account Transactions",
        customer_id=customer_data.get("customer_id"),
        analytics=ui.AnalyticsOut(**mapper.build_analytics(life_event, transaction_rows)),
        key_drivers=[ui.KeyDriverOut(**kd) for kd in mapper.build_key_drivers(life_event, transaction_rows)],
        detection_method=getattr(life_event, "score_source", None),
        actionable=bool(getattr(life_event, "actionable", False)),
        status=getattr(life_event, "status", None),
        case=ui.CaseOut(**case) if case else None,
    )


def _fallback_summary(life_event: Any, transaction_rows: List[Dict[str, Any]]) -> str:
    """
    Used when the LLM summary is unavailable (no API key configured, or the
    call failed). Reports only what the rules engine actually established,
    so the advisor is never shown invented narrative.
    """
    event_type = getattr(life_event, "life_event_type", "an event")
    confidence = float(getattr(life_event, "confidence_score", 0.0) or 0.0)
    matched = [s for s in (getattr(life_event, "signals", None) or []) if getattr(s, "matched", False)]
    return (
        f"{len(matched)} transaction signal{'s' if len(matched) != 1 else ''} matched the configured "
        f"thresholds for {event_type}, producing a confidence score of {confidence * 100:.0f}% across "
        f"{len(transaction_rows)} reviewed transactions."
    )


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------



def _client_payload(db: Session, customer_data: Dict[str, Any]) -> ui.ClientOut:
    """
    Builds one client's dashboard payload, including a compact event summary
    and case info so the Home grid renders fully from a single request.

    Detection has to run here anyway to determine has_signal, so reusing that
    result for the event summary costs nothing extra. Recommendation titles
    are included only when an event is actionable -- that's the one part the
    card needs beyond detection.
    """
    client_id = customer_data.get("customer_id")
    has_signal = False
    event_summary = None
    case_out = None

    try:
        rows = transaction_repository.get_transactions_by_customer_id(db=db, customer_id=client_id) or []
        if rows:
            request = _build_evaluation_request(customer_data, rows)
            life_event = event_detection_agent.detect(request)
            has_signal = bool(getattr(life_event, "actionable", False))

            if has_signal:
                titles = []
                try:
                    raw_recs = recommendation_agent.generate(
                        customer=request.customer, life_event=life_event
                    ) or []
                    titles = [
                        ui.RecommendationTitleOut(
                            title=str(_rec_title(rec, index))
                        )
                        for index, rec in enumerate(raw_recs[:2])
                    ]
                except Exception as exc:
                    logger.warning("Recommendation preview failed for %s: %s", client_id, exc)

                event_summary = ui.EventSummaryOut(
                    event_name=getattr(life_event, "life_event_type", "") or "",
                    confidence=round(float(getattr(life_event, "confidence_score", 0.0) or 0.0), 4),
                    timeline=getattr(life_event, "estimated_timeline", None),
                    recommendations=titles,
                )
    except Exception as exc:
        logger.warning("Detection failed for client %s: %s", client_id, exc, exc_info=True)
        has_signal = False

    state = db.query(ClientWorkflowStateORM).filter(
        ClientWorkflowStateORM.customer_id == client_id
    ).first()
    case = mapper.map_case(state) if state else None
    if case:
        case_out = ui.CaseOut(**case)

    return ui.ClientOut(
        **mapper.map_client(customer_data, has_signal=has_signal),
        event=event_summary,
        case_info=case_out,
    )


def _rec_title(rec: Any, index: int) -> str:
    if isinstance(rec, dict):
        return rec.get("recommendation_name") or rec.get("name") or f"Recommendation {index + 1}"
    return (
        getattr(rec, "recommendation_name", None)
        or getattr(rec, "name", None)
        or f"Recommendation {index + 1}"
    )


@router.get("", response_model=List[ui.ClientOut])
def list_clients(db: Session = Depends(get_db)):
    """Home dashboard client grid."""
    customers = customer_repository.get_all_customers(db) or []
    return [_client_payload(db, customer_data) for customer_data in customers]


@router.get("/{client_id}", response_model=ui.ClientOut)
def get_client(client_id: str, db: Session = Depends(get_db)):
    customer_data = _get_customer_or_404(db, client_id)
    return _client_payload(db, customer_data)


# ---------------------------------------------------------------------------
# Agent 1 — Event Detection
# ---------------------------------------------------------------------------


@router.post("/{client_id}/detect", response_model=ui.DetectionResultOut)
def run_detection(client_id: str, db: Session = Depends(get_db)):
    """Runs Event Detection and opens a case if the event is actionable."""
    customer_data, transaction_rows, life_event = _run_detection(db, client_id)
    state = _ensure_case(db, client_id, life_event)
    return _detection_payload(customer_data, transaction_rows, life_event, state)


@router.get("/{client_id}/detection", response_model=ui.DetectionResultOut)
def get_detection(client_id: str, db: Session = Depends(get_db)):
    """
    Same shape as POST /detect. The underlying agents are stateless and
    recompute on each call, so this re-runs detection rather than reading a
    cached row -- but it does NOT open a case, so it is safe for page loads.
    """
    customer_data, transaction_rows, life_event = _run_detection(db, client_id)
    state = db.query(ClientWorkflowStateORM).filter(
        ClientWorkflowStateORM.customer_id == client_id
    ).first()
    return _detection_payload(customer_data, transaction_rows, life_event, state)


# ---------------------------------------------------------------------------
# Agent 2 — Recommendations
# ---------------------------------------------------------------------------


@router.post("/{client_id}/recommendations", response_model=List[ui.RecommendationOut])
def run_recommendations(client_id: str, db: Session = Depends(get_db)):
    customer_data, transaction_rows, life_event = _require_actionable_event(db, client_id)
    _ensure_case(db, client_id, life_event)
    recommendations = _generate_recommendations(customer_data, transaction_rows, life_event)
    return [ui.RecommendationOut(**rec) for rec in recommendations]


@router.get("/{client_id}/recommendations", response_model=List[ui.RecommendationOut])
def get_recommendations(client_id: str, db: Session = Depends(get_db)):
    customer_data, transaction_rows, life_event = _require_actionable_event(db, client_id)
    recommendations = _generate_recommendations(customer_data, transaction_rows, life_event)
    return [ui.RecommendationOut(**rec) for rec in recommendations]


# ---------------------------------------------------------------------------
# Agent 3 — Advisor Insights
# ---------------------------------------------------------------------------


def _build_advisor_brief(db: Session, client_id: str) -> ui.AdvisorBriefOut:
    customer_data, transaction_rows, life_event = _require_actionable_event(db, client_id)
    state = _get_or_create_state(db, client_id)

    request = _build_evaluation_request(customer_data, transaction_rows)
    raw_recommendations = recommendation_agent.generate(
        customer=request.customer,
        life_event=life_event,
    )
    recommendations = mapper.map_recommendations(raw_recommendations, life_event, customer_data)

    advisor_insight = advisor_insights_agent.generate(
        customer=request.customer,
        life_event=life_event,
        recommendations=raw_recommendations,
        customer_data=customer_data,
    )

    brief = mapper.map_advisor_brief(
        advisor_insight=advisor_insight,
        life_event=life_event,
        customer_data=customer_data,
        recommendations=recommendations,
        event_confirmed=bool(state.event_confirmed),
    )
    return ui.AdvisorBriefOut(**brief)


@router.post("/{client_id}/advisor-brief", response_model=ui.AdvisorBriefOut)
def run_advisor_brief(client_id: str, db: Session = Depends(get_db)):
    return _build_advisor_brief(db, client_id)


@router.get("/{client_id}/advisor-brief", response_model=ui.AdvisorBriefOut)
def get_advisor_brief(client_id: str, db: Session = Depends(get_db)):
    return _build_advisor_brief(db, client_id)


@router.post("/{client_id}/confirm-event", response_model=ui.AdvisorBriefOut)
def confirm_event(client_id: str, db: Session = Depends(get_db)):
    """
    The UI's "Confirm Event" button. Records that the advisor validated the
    event with the client, which swaps the displayed talking points from
    confirmation prompts to product prompts.
    """
    _get_customer_or_404(db, client_id)
    state = _get_or_create_state(db, client_id)
    state.event_confirmed = True
    db.commit()
    return _build_advisor_brief(db, client_id)


# ---------------------------------------------------------------------------
# Agent 4 — Client Sentiment
# ---------------------------------------------------------------------------


@router.post("/{client_id}/sentiment", response_model=ui.SentimentInsightOut)
def run_sentiment(client_id: str, body: ui.SentimentAnalyzeRequest, db: Session = Depends(get_db)):
    _get_customer_or_404(db, client_id)

    interaction_text = (body.interaction_text or "").strip()
    if len(interaction_text.split()) < MIN_SENTIMENT_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Interaction text must be at least {MIN_SENTIMENT_WORDS} words to analyse.",
        )

    sentiment_insight = sentiment_agent.analyze(
        customer_id=client_id,
        conversation_text=interaction_text,
        conversation_permitted=True,
    )

    state = _get_or_create_state(db, client_id)
    state.interaction_text = interaction_text
    state.sentiment = str(getattr(sentiment_insight, "sentiment", "Neutral"))
    state.sentiment_score = int(getattr(sentiment_insight, "engagement_score", 0) or 0)
    state.primary_intent = str(getattr(sentiment_insight, "primary_intent", "") or "")
    state.secondary_intents = list(getattr(sentiment_insight, "secondary_intents", []) or [])
    db.commit()
    db.refresh(state)

    mapped = mapper.map_sentiment(
        sentiment_insight,
        interaction_text,
        list(state.selected_products or []),
    )
    state.sentiment_guidance = mapped["guidance"]
    db.commit()

    return ui.SentimentInsightOut(**mapped)


@router.get("/{client_id}/sentiment", response_model=ui.SentimentInsightOut)
def get_sentiment(client_id: str, db: Session = Depends(get_db)):
    _get_customer_or_404(db, client_id)
    state = db.query(ClientWorkflowStateORM).filter(
        ClientWorkflowStateORM.customer_id == client_id
    ).first()

    if state is None or not state.sentiment:
        raise HTTPException(status_code=404, detail="No sentiment analysis recorded yet for this client.")

    return ui.SentimentInsightOut(
        interaction_text=state.interaction_text or "",
        sentiment=state.sentiment or "Neutral",
        score=int(state.sentiment_score or 0),
        guidance=state.sentiment_guidance or "",
        primary_intent=state.primary_intent or "",
        secondary_intents=list(state.secondary_intents or []),
        selected_products=list(state.selected_products or []),
    )


@router.post("/{client_id}/sentiment/auto-select", response_model=ui.SentimentInsightOut)
def auto_select_products(client_id: str, db: Session = Depends(get_db)):
    """Deterministic, auditable product selection driven by the stored sentiment."""
    customer_data, transaction_rows, life_event = _require_actionable_event(db, client_id)

    state = db.query(ClientWorkflowStateORM).filter(
        ClientWorkflowStateORM.customer_id == client_id
    ).first()
    if state is None or not state.sentiment:
        raise HTTPException(
            status_code=409,
            detail=f"No sentiment analysis yet. Run POST /api/clients/{client_id}/sentiment first.",
        )

    recommendations = _generate_recommendations(customer_data, transaction_rows, life_event)
    state.selected_products = mapper.auto_select_products(state.sentiment, recommendations)
    db.commit()
    db.refresh(state)

    return ui.SentimentInsightOut(
        interaction_text=state.interaction_text or "",
        sentiment=state.sentiment or "Neutral",
        score=int(state.sentiment_score or 0),
        guidance=state.sentiment_guidance or "",
        primary_intent=state.primary_intent or "",
        secondary_intents=list(state.secondary_intents or []),
        selected_products=list(state.selected_products or []),
    )


@router.patch("/{client_id}/sentiment/products", response_model=ui.SentimentInsightOut)
def update_selected_products(
    client_id: str,
    body: ui.SelectedProductsUpdate,
    db: Session = Depends(get_db),
):
    """Manual product checkbox selection from the UI."""
    _get_customer_or_404(db, client_id)
    state = _get_or_create_state(db, client_id)
    state.selected_products = list(body.selected_products or [])
    db.commit()
    db.refresh(state)

    return ui.SentimentInsightOut(
        interaction_text=state.interaction_text or "",
        sentiment=state.sentiment or "Neutral",
        score=int(state.sentiment_score or 0),
        guidance=state.sentiment_guidance or "",
        primary_intent=state.primary_intent or "",
        secondary_intents=list(state.secondary_intents or []),
        selected_products=list(state.selected_products or []),
    )


# ---------------------------------------------------------------------------
# Agent 5 — Workflow Orchestration
# ---------------------------------------------------------------------------


def _orchestrate(db: Session, client_id: str, advance_case: bool) -> List[ui.OrchestrationTaskOut]:
    customer_data, transaction_rows, life_event = _require_actionable_event(db, client_id)
    state = _get_or_create_state(db, client_id)
    selected_products = list(state.selected_products or [])

    workflow_tasks: List[Any] = []
    try:
        request = _build_evaluation_request(customer_data, transaction_rows)
        raw_recommendations = recommendation_agent.generate(
            customer=request.customer,
            life_event=life_event,
        )
        compliance = risk_compliance_agent.validate(
            request=request,
            life_event=life_event,
            recommendations=raw_recommendations,
        )
        workflow_tasks = workflow_agent.create_tasks(
            customer_id=client_id,
            life_event=life_event,
            compliance=compliance,
        ) or []
    except Exception:
        # The workflow mappings file may not cover every event type. Fall
        # back to the standard task template rather than failing the step.
        workflow_tasks = []

    if advance_case and state.case_status == "Open":
        state.case_status = "In Progress"
        db.commit()
        db.refresh(state)

    tasks = mapper.map_tasks(workflow_tasks, selected_products)
    return [ui.OrchestrationTaskOut(**task) for task in tasks]


@router.post("/{client_id}/orchestrate", response_model=List[ui.OrchestrationTaskOut])
def run_orchestration(client_id: str, db: Session = Depends(get_db)):
    return _orchestrate(db, client_id, advance_case=True)


@router.get("/{client_id}/orchestrate", response_model=List[ui.OrchestrationTaskOut])
def get_orchestration(client_id: str, db: Session = Depends(get_db)):
    return _orchestrate(db, client_id, advance_case=False)


@router.patch("/{client_id}/case-status", response_model=ui.CaseOut)
def update_case_status(client_id: str, body: ui.CaseStatusUpdate, db: Session = Depends(get_db)):
    """
    The UI's two close-case buttons. Only Converted and Lost are accepted --
    Open and In Progress are set by the system, never by the client.
    """
    _get_customer_or_404(db, client_id)
    state = _get_or_create_state(db, client_id)

    if not state.case_ref:
        raise HTTPException(
            status_code=409,
            detail=f"No case open for this client. Run POST /api/clients/{client_id}/detect first.",
        )

    state.case_status = body.status
    db.commit()
    db.refresh(state)

    case = mapper.map_case(state)
    if case is None:
        raise HTTPException(status_code=404, detail="Case could not be read back after update.")
    return ui.CaseOut(**case)
