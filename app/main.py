from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    dashboard,
    transactions,
    life_events,
    recommendations,
    compliance,
    advisor_insights,
    sentiment,
    workflows,
    approvals,
    governance,
    ui_clients,
    workflow_steps,
)
from app.config import settings

app = FastAPI(
    title="Life Event Backend",
    version="1.1.0",
    description=(
        "Agent-based FastAPI backend for transaction-driven life event detection.\n\n"
        "Two API surfaces are exposed:\n"
        "- `/api/clients/*` - the UI compatibility layer consumed by the React "
        "frontend (camelCase, workflow state, case lifecycle).\n"
        "- everything else - the original internal/agent routes, unchanged."
    ),
)

# ---------------------------------------------------------------------------
# CORS - required for the React dev server (or any browser client) to call
# this API. Without it every request from the UI is blocked by the browser
# before it reaches FastAPI.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_ui_tables() -> None:
    """
    Creates the tables the UI layer depends on, and seeds the workflow step
    definitions if that table is empty.

    Scoped deliberately via `tables=[...]` so it cannot touch or recreate any
    of the existing schema -- the rest of the database is managed by the
    team's own migration process.
    """
    try:
        from app.db.database import SessionLocal, engine
        from app.models.base import Base
        from app.models.workflow_state_orm import ClientWorkflowStateORM
        from app.models.workflow_step_orm import WorkflowStepORM

        Base.metadata.create_all(
            bind=engine,
            tables=[ClientWorkflowStateORM.__table__, WorkflowStepORM.__table__],
        )
        print("UI tables ready: ui_client_workflow_state, workflow_steps")
    except Exception as exc:  # pragma: no cover - startup diagnostics only
        print(f"WARNING: could not create UI tables: {exc}")
        print("The /api/clients and /api/workflow-steps endpoints will fail until this is resolved.")
        return

    # Seed the 5 step definitions on first run.
    try:
        from app.data.workflow_steps_seed import WORKFLOW_STEPS_SEED

        db = SessionLocal()
        try:
            if db.query(WorkflowStepORM).count() == 0:
                for step in WORKFLOW_STEPS_SEED:
                    db.add(WorkflowStepORM(**step))
                db.commit()
                print(f"Seeded {len(WORKFLOW_STEPS_SEED)} workflow steps.")
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover
        print(f"WARNING: could not seed workflow steps: {exc}")


# UI compatibility layer (consumed by the React frontend)
app.include_router(ui_clients.router, prefix="/api/clients", tags=["UI - Clients & Workflow"])
app.include_router(workflow_steps.router)

# Original routes, unchanged
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(life_events.router, prefix="/life-events", tags=["Life Events"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
app.include_router(advisor_insights.router, prefix="/advisor-insights", tags=["Advisor Insights"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["Sentiment"])
app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(governance.router, prefix="/governance", tags=["Governance"])


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "running",
        "service": "Life Event Backend",
        "version": "1.1.0",
        "ui_api_base": "/api/clients",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "llm_configured": settings.llm_configured,
        "llm_provider_url": settings.llm_api_url,
        "llm_model": settings.llm_model_name,
    }

@app.get("/api/llm-check", tags=["Health"])
def llm_check():
    """
    Diagnostic: actually calls the configured LLM and reports what happened.

    Without this, a working Ollama and an unreachable one are hard to tell
    apart -- both leave the app showing deterministic template text. This
    makes the difference explicit.
    """
    import requests

    result = {
        "configured_url": settings.llm_api_url,
        "configured_model": settings.llm_model_name,
        "api_key_set": bool(settings.llm_api_key),
        "reachable": False,
        "responded": False,
        "sample_output": None,
        "error": None,
    }

    if not settings.llm_api_url or not settings.llm_model_name:
        result["error"] = "LLM_API_URL or LLM_MODEL_NAME is not set in .env"
        return result

    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    payload = {
        "model": settings.llm_model_name,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 20,
        "stream": False,
    }

    try:
        response = requests.post(
            settings.llm_api_url, headers=headers, json=payload,
            timeout=settings.llm_timeout_seconds,
        )
        result["reachable"] = True
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            result["sample_output"] = message.get("content") or choices[0].get("text")
            result["responded"] = bool(result["sample_output"])
        if not result["responded"]:
            result["error"] = f"Unexpected response shape: {str(data)[:200]}"
    except requests.exceptions.ConnectionError as exc:
        result["error"] = (
            f"Cannot connect to {settings.llm_api_url}. "
            f"Is Ollama running? Try: ollama serve  ({exc})"
        )
    except requests.exceptions.Timeout:
        result["error"] = (
            f"Timed out after {settings.llm_timeout_seconds}s. The first request to a "
            "freshly loaded model can be slow -- try again, or raise LLM_TIMEOUT_SECONDS."
        )
    except Exception as exc:
        result["error"] = str(exc)

    return result
