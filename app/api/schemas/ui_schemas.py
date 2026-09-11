"""
UI-facing response schemas.

Every model here uses a camelCase alias generator so the JSON field names
match exactly what the React frontend (life-event-app) reads. The backend's
internal models stay snake_case and untouched -- this is purely the
presentation contract for the UI.

Field names here were derived by reading the frontend components directly
(LifeEventHero, ActiveCaseCard, ClientHeader, CaseIdStrip, KeyDriversList,
RecommendationCard, HistoricalTakeUpGrid, CustomerDetailsPanel,
AdvisorInsightsStep, ClientSentimentStep, WorkflowOrchestrationStep),
not from a spec -- so they are what the UI actually consumes.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


def to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------------------------------------------------------------------------
# Client / customer
# ---------------------------------------------------------------------------


class EventSummaryOut(CamelModel):
    """Compact event summary for the dashboard card. Full detail comes from
    the /detect endpoint -- this is only what the Home grid renders."""

    event_name: str
    confidence: float
    timeline: Optional[str] = None
    recommendations: List["RecommendationTitleOut"] = []


class RecommendationTitleOut(CamelModel):
    title: str


class ClientOut(CamelModel):
    """GET /api/clients and GET /api/clients/{id}"""

    id: str
    customer_id: str
    name: str
    initials: str
    age: Optional[int] = None
    marital_status: str = "Active"
    segment: str = ""
    portfolio: str = ""
    ytd: str = ""
    risk: str = ""
    last_review: str = ""
    account_type: str = ""
    account_number: str = ""
    sort_code: str = ""
    balance: str = ""
    has_signal: bool = False
    wealth_details: Dict[str, Any] = {}
    banking_details: Dict[str, Any] = {}
    # Populated so the Home dashboard can render event + case info without
    # a follow-up call per client. Detection already runs here to compute
    # has_signal, so this costs nothing extra.
    event: Optional["EventSummaryOut"] = None
    case_info: Optional["CaseOut"] = None


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------


class CaseOut(CamelModel):
    id: str
    status: str
    priority: str
    opened: str
    days_open: int


class CaseStatusUpdate(CamelModel):
    status: Literal["Converted", "Lost"]


# ---------------------------------------------------------------------------
# Event detection
# ---------------------------------------------------------------------------


class KeyDriverOut(CamelModel):
    label: str
    category: str
    amount: str
    time: str


class AnalyticsOut(CamelModel):
    spending_pattern: str
    jump_in_spend: str
    season: str
    supporting_note: str


class DetectionResultOut(CamelModel):
    """
    POST /api/clients/{id}/detect and GET /api/clients/{id}/detection

    NOTE: `confidence` is a 0.0-1.0 fraction, NOT a percentage. The frontend
    renders it with Math.round(confidence * 100), so returning 82 here would
    display as "8200%".
    """

    detected: bool
    event_name: Optional[str] = None
    confidence: Optional[float] = None
    timeline: Optional[str] = None
    ai_summary: Optional[str] = None
    event_source: Optional[str] = None
    customer_id: Optional[str] = None
    analytics: Optional[AnalyticsOut] = None
    key_drivers: List[KeyDriverOut] = []
    detection_method: Optional[str] = None
    actionable: bool = False
    status: Optional[str] = None
    case: Optional[CaseOut] = None


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class RecommendationOut(CamelModel):
    id: int
    title: str
    rationale: str
    match_event: int
    match_customer: int
    justification: str
    conversion_rate: int
    avg_days_to_take_up: int
    avg_amount: str
    historical_note: str
    order_index: int


# ---------------------------------------------------------------------------
# Advisor brief
# ---------------------------------------------------------------------------


class RiskAppetiteOut(CamelModel):
    label: str
    summary: str
    event_impact: str
    advisor_note: str


class AdvisorBriefOut(CamelModel):
    behavior_analytics: List[str] = []
    talking_points: List[str] = []
    recommendation_talking_points: List[str] = []
    opportunities: List[str] = []
    risk_appetite: RiskAppetiteOut
    event_confirmed: bool = False


# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------


class SentimentAnalyzeRequest(CamelModel):
    interaction_text: str


class SelectedProductsUpdate(CamelModel):
    selected_products: List[str]


class SentimentInsightOut(CamelModel):
    interaction_text: str = ""
    sentiment: str = "Neutral"
    score: int = 0
    guidance: str = ""
    primary_intent: str = ""
    secondary_intents: List[str] = []
    selected_products: List[str] = []


# ---------------------------------------------------------------------------
# Workflow orchestration
# ---------------------------------------------------------------------------


class OrchestrationTaskOut(CamelModel):
    name: str
    status: str


# ---------------------------------------------------------------------------
# Workflow step definitions
# ---------------------------------------------------------------------------


class WorkflowStepOut(CamelModel):
    """One workflow step. Field names match what the UI already expects."""

    id: str
    step_number: int
    icon: str
    title: str
    short_description: str
    role: str
    tag: str
    agent_name: str
    no_signal_summary: str


# ---------------------------------------------------------------------------
# Forward-reference resolution
#
# ClientOut references EventSummaryOut and CaseOut as string annotations
# because CaseOut is declared further down the file. Pydantic v2 needs these
# rebuilt once every referenced model exists, otherwise the first request
# raises PydanticUndefinedAnnotation at runtime rather than at import.
# ---------------------------------------------------------------------------
EventSummaryOut.model_rebuild()
ClientOut.model_rebuild()