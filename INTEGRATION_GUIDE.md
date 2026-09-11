# Life Event Backend — UI Integration Build

This is your team's backend with a **UI compatibility layer** added. Their
agents, ML models, and rules engine are untouched — everything new sits
alongside and wraps them.

---

## Quick start (demo path)

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt

cp .env.example .env             # then edit DATABASE_URL to match your Postgres
python -m uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** — the new endpoints appear under
**"UI — Clients & Workflow"**.

Smoke test:
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/clients
```

> The `ui_client_workflow_state` table is created automatically on startup.
> No migration step needed.

---

## What was added

| Area | Change |
|---|---|
| **CORS** | Added `CORSMiddleware` to `main.py`. **This was a hard blocker** — without it the browser blocks every request from your React app before it reaches FastAPI. |
| **16 UI endpoints** | New `app/api/routes/ui_clients.py` exposing `/api/clients/*` in exactly the shapes the UI reads. |
| **camelCase output** | New `app/api/schemas/ui_schemas.py` — Pydantic models with a camelCase alias generator. |
| **Case lifecycle** | New `app/models/workflow_state_orm.py` — persists case ref/status/priority, event confirmation, selected products, and sentiment. The original backend had no case concept at all, and the UI depends on it heavily. |
| **Response mapping** | New `app/services/ui_mapper_service.py` — translates agent output into UI shapes and fills gaps (per-transaction key drivers, analytics cards, match scores, risk narrative). |
| **Product statistics** | New `app/data/product_stats.py` — conversion rates / take-up times the UI displays. |
| **LLM service** | Rewritten `app/services/llm_service.py` — now provider-agnostic (Ollama / vLLM / any OpenAI-compatible endpoint). |
| **Config** | New `app/config.py` — central env handling, supports both `LLM_*` and the old `GEMMA_*` names. |

**Nothing was removed.** All original routes (`/dashboard`, `/life-events/detect/...`,
etc.) still work exactly as before.

---

## The LLM change — please read

The original `.env` had:
```
GEMMA_API_KEY=sk-or-v1-b2d5...     # a live key, committed to the repo
GEMMA_API_URL=https://api.openrouter.ai/v1/completions
GEMMA_MODEL_NAME=gemma-4o
```

Three problems:

1. **The API key was committed.** It's been removed from `.env` and `.gitignore`
   now excludes the file — but **that key should be rotated**, since it's in the
   repo's git history.
2. **`gemma-4o` isn't a real model.** It looks like a mix-up of Google's *Gemma*
   and OpenAI's *GPT-4o*. Worth confirming which your lead actually meant.
3. **OpenRouter is a paid API.** If the instruction was "no paid LLM APIs", that
   config didn't satisfy it.

The rewritten service is provider-agnostic and defaults to **Ollama running
locally** — genuinely free and open source:

```bash
# install from https://ollama.com, then:
ollama pull gemma2
ollama serve
```
That's it — the default `.env` already points at it.

**The app works fully without any LLM.** If none is reachable, narrative fields
fall back to deterministic text built from the rules engine's own output. Nothing
errors, nothing is fabricated. For a demo in two days, you can skip the LLM setup
entirely and still show the complete flow.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/clients` | Client list for the Home grid |
| GET | `/api/clients/{id}` | One client's profile |
| POST | `/api/clients/{id}/detect` | Run Event Detection; opens a case |
| GET | `/api/clients/{id}/detection` | Same shape, no case side-effect (safe for page loads) |
| POST/GET | `/api/clients/{id}/recommendations` | Recommendations with match scores |
| POST/GET | `/api/clients/{id}/advisor-brief` | Advisor briefing incl. riskAppetite |
| POST | `/api/clients/{id}/confirm-event` | "Confirm Event" button |
| POST/GET | `/api/clients/{id}/sentiment` | Sentiment analysis (POST body: `interactionText`) |
| POST | `/api/clients/{id}/sentiment/auto-select` | Rule-based product selection |
| PATCH | `/api/clients/{id}/sentiment/products` | Manual selection (body: `selectedProducts`) |
| POST/GET | `/api/clients/{id}/orchestrate` | Task list |
| PATCH | `/api/clients/{id}/case-status` | Close case (`Converted` \| `Lost`) |

Error conventions: `404` unknown client · `409` a prerequisite step hasn't run ·
`422` invalid body.

---

## Frontend integration — the one piece of new code you need

Your mock data (`src/data/clients.js`) stores everything about an event in **one
merged object** (`client.event`). The backend correctly serves those as **separate
calls**, because that's how the workflow actually runs. So you need a small
adapter. Two field renames are required — everything else maps 1:1:

- backend `keyDrivers` → frontend `signals`
- recommendations arrive from their own endpoint, not nested in `event`

```js
// src/api/client.js
const BASE = 'http://localhost:8000'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw Object.assign(new Error(res.statusText), { status: res.status })
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw Object.assign(new Error(res.statusText), { status: res.status })
  return res.json()
}

export async function fetchClients() {
  return get('/api/clients')
}

/** Assembles the `client.event` shape your existing components already expect. */
export async function fetchClientEvent(clientId) {
  const detection = await get(`/api/clients/${clientId}/detection`)
  if (!detection.detected) return { event: null, caseInfo: null }

  // These 409 until their prerequisite step has run — treat as "not ready yet".
  const [recommendations, brief, sentiment] = await Promise.all([
    get(`/api/clients/${clientId}/recommendations`).catch(() => []),
    get(`/api/clients/${clientId}/advisor-brief`).catch(() => null),
    get(`/api/clients/${clientId}/sentiment`).catch(() => null),
  ])

  return {
    caseInfo: detection.case,          // maps 1:1, no renaming
    event: {
      eventName: detection.eventName,
      confidence: detection.confidence,   // already a 0–1 fraction
      timeline: detection.timeline,
      aiSummary: detection.aiSummary,
      eventSource: detection.eventSource,
      customerId: detection.customerId,
      analytics: detection.analytics,
      signals: detection.keyDrivers,      // <-- rename
      recommendations,                    // <-- from its own endpoint
      opportunities: brief?.opportunities ?? [],
      talkingPoints: brief?.talkingPoints ?? [],
      recommendationTalkingPoints: brief?.recommendationTalkingPoints ?? [],
      behaviorAnalytics: brief?.behaviorAnalytics ?? [],
      riskAppetite: brief?.riskAppetite ?? null,
      sentiment: sentiment
        ? { primaryIntent: sentiment.primaryIntent, sentiment: sentiment.sentiment,
            engagement: sentiment.score }
        : null,
    },
  }
}

export const confirmEvent   = (id) => post(`/api/clients/${id}/confirm-event`)
export const analyseSentiment = (id, interactionText) =>
  post(`/api/clients/${id}/sentiment`, { interactionText })
export const autoSelectProducts = (id) => post(`/api/clients/${id}/sentiment/auto-select`)
export const orchestrate    = (id) => post(`/api/clients/${id}/orchestrate`)
```

`confidence` is deliberately a **0–1 fraction** because your components render it
with `Math.round(confidence * 100)`.

---

## Verification done — and its limits

I could not install FastAPI/SQLAlchemy/Postgres in my environment, so **this code
has not been executed**. What I did verify:

- Python AST syntax parse across all files — clean
- Every `app.*` import traced to a real module/name — clean (one pre-existing
  break found and guarded, see below)
- **Every camelCase field the backend emits was cross-checked against every field
  your React components actually read**, by parsing both sides. All match except
  the two documented renames above.

**Treat the first `uvicorn` run as the real first test.** If something breaks,
send me the traceback — it'll be a quick fix.

---

## Pre-existing issues found in the handed-over code

Not introduced by these changes; flagging so they don't surprise you:

1. **`scripts/init_db.py` is broken** — `import syss` (typo) and imports
   `app.models.life_event_orm`, which doesn't exist. Left as-is; your DB is
   presumably already created.
2. **`app/db/repositories/__init__.py` imported that same missing model**, which
   would crash anything importing the package (including `seed_db.py`). Now
   guarded with try/except so it degrades instead of exploding.
3. **`seed_db.py` writes `portfolio_value`** but the SQL in
   `app/repositories/customer_repository.py` reads `portfolio` — the seed script
   and the query have drifted apart.
4. **Dashboard route has a stray key** literally named
   `"python -m uvicorn app.main:app --reload"` (paste accident) in the
   no-transactions branch. Harmless, but worth cleaning up.

Because of #3 and general schema drift, `ui_mapper_service.map_client()` uses
`.get()` with fallbacks throughout — a missing optional column renders as `—`
rather than 500-ing the dashboard.

---

## If the demo is tight on time

Priority order:
1. `pip install -r requirements.txt`, set `DATABASE_URL`, run uvicorn
2. Check `GET /api/clients` returns your customers
3. Check `POST /api/clients/{id}/detect` returns `detected: true` for a client
   with wedding/travel/etc. transactions
4. Wire the frontend adapter above
5. **Skip the LLM entirely** — the deterministic fallbacks cover every screen
