"""
Maps the existing backend's agent output into the shapes the React UI
consumes.

Design intent: this module is purely a translation + enrichment layer. It
never modifies the agents, the ML models, or the rules engine -- it reads
what they produce and reshapes it. That means the backend team keeps full
ownership of the detection intelligence, while the API contract the UI
depends on lives here.

Where the UI needs data the agents don't currently produce (per-transaction
key driver detail, the four analytics insight cards, product match scores,
the risk-appetite narrative), this module derives it from data that IS
available -- the matched transactions, the rules engine's own thresholds,
and the customer profile -- rather than inventing values.
"""
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.data.product_stats import get_product_stats
from app.services.rule_loader_service import RuleLoaderService

_rule_loader = RuleLoaderService()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_currency(value: Optional[float], *, signed: bool = True) -> str:
    """Formats a number as GBP for display, e.g. -£1,680.00."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if (signed and amount > 0) else ""
    return f"{sign}£{abs(amount):,.2f}"


def format_currency_short(value: Optional[float]) -> str:
    """Compact currency for portfolio/balance display, e.g. £2.4M / £562,000."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    if amount >= 1_000_000:
        millions = amount / 1_000_000
        return f"£{millions:.0f}M" if millions == int(millions) else f"£{millions:.1f}M"
    return f"£{amount:,.0f}"


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:len(fmt) + 2].strip(), fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def relative_time_label(transaction_date: Any) -> str:
    """Turns a date into the UI's '2w ago' / '3m ago' style label."""
    parsed = _parse_date(transaction_date)
    if parsed is None:
        return "Recent"

    delta_days = (date.today() - parsed).days
    if delta_days < 0:
        return "Upcoming"
    if delta_days == 0:
        return "Today"
    if delta_days < 7:
        return f"{delta_days}d ago"
    if delta_days < 31:
        return f"{delta_days // 7}w ago"
    if delta_days < 365:
        return f"{delta_days // 30}m ago"
    return f"{delta_days // 365}y ago"


def initials_from_name(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def payment_type_for_category(merchant_category: Optional[str]) -> str:
    """
    Maps a merchant category to the payment-type label the UI uses to pick
    a row icon. The UI's icon map keys on: Card Payment, Bank Transfer,
    Standing Order, Direct Debit, Salary Credit.
    """
    category = (merchant_category or "").strip().lower()
    if category in {"event booking", "property services", "education"}:
        return "Bank Transfer"
    if category in {"salary", "income"}:
        return "Salary Credit"
    if category in {"insurance", "utilities", "subscription"}:
        return "Direct Debit"
    if category in {"savings", "investment"}:
        return "Standing Order"
    return "Card Payment"


# ---------------------------------------------------------------------------
# Client mapping
# ---------------------------------------------------------------------------


def map_client(customer_data: Dict[str, Any], *, has_signal: bool = False) -> Dict[str, Any]:
    """
    Maps a customer row (from CustomerRepository's raw SQL) to the UI's
    client shape. Uses .get() throughout because the deployed database
    schema has drifted from the seed script in places -- a missing optional
    column should degrade to a placeholder, not raise.
    """
    name = customer_data.get("name") or "Unknown"
    customer_id = customer_data.get("customer_id") or ""

    portfolio_raw = customer_data.get("portfolio") or customer_data.get("portfolio_value")
    balance_raw = customer_data.get("balance")
    income_raw = customer_data.get("annual_income")

    return {
        "id": customer_id,
        "customer_id": customer_id,
        "name": name,
        "initials": initials_from_name(name),
        "age": customer_data.get("age"),
        "marital_status": customer_data.get("marital_status") or "Active",
        "segment": customer_data.get("segment") or "",
        "portfolio": format_currency_short(portfolio_raw) if portfolio_raw is not None else "—",
        "ytd": customer_data.get("ytd") or "",
        "risk": customer_data.get("risk_profile") or customer_data.get("risk") or "Balanced",
        "last_review": str(customer_data.get("last_review") or "—"),
        "account_type": customer_data.get("account_type") or "—",
        "account_number": customer_data.get("account_number") or "—",
        "sort_code": customer_data.get("sort_code") or "—",
        "balance": format_currency_short(balance_raw) if balance_raw is not None else "—",
        "has_signal": has_signal,
        "wealth_details": {
            "income": f"{format_currency_short(income_raw)} / yr" if income_raw is not None else "—",
            "advisor": customer_data.get("relationship_manager") or "—",
            "kycStatus": customer_data.get("kyc_status") or "—",
            "productHoldings": customer_data.get("product_holdings") or "—",
            "primaryGoal": customer_data.get("primary_goal") or "—",
        },
        "banking_details": {
            "overdraftLimit": format_currency_short(customer_data.get("overdraft_limit"))
                if customer_data.get("overdraft_limit") is not None else "—",
            "monthlyCredits": format_currency_short(customer_data.get("monthly_credits"))
                if customer_data.get("monthly_credits") is not None else "—",
            "monthlyDebits": format_currency_short(customer_data.get("monthly_debits"))
                if customer_data.get("monthly_debits") is not None else "—",
            "currency": customer_data.get("currency") or "GBP",
        },
    }


# ---------------------------------------------------------------------------
# Key drivers -- derived from the transactions that actually matched
# ---------------------------------------------------------------------------


def build_key_drivers(
    life_event: Any,
    transaction_rows: List[Dict[str, Any]],
    limit: int = 6,
) -> List[Dict[str, str]]:
    """
    The agents expose key_drivers as a list of plain strings, but the UI
    renders each driver as a row with a category icon, an amount, and a
    relative time. Rather than discard that detail, this rebuilds the driver
    list from the actual transactions that satisfied the event's configured
    signals -- so every row the advisor sees is backed by a real transaction.

    Falls back to the agent's own key_drivers strings if no transactions can
    be matched (e.g. the rules file and the data have diverged).
    """
    event_type = getattr(life_event, "life_event_type", None) or "Unknown"
    event_rule = _get_event_rule(event_type)

    drivers: List[Dict[str, str]] = []

    if event_rule:
        matched_signal_names = {
            getattr(s, "signal_name", None)
            for s in (getattr(life_event, "signals", None) or [])
            if getattr(s, "matched", False)
        }

        for signal_config in event_rule.get("transaction_signals", []):
            if matched_signal_names and signal_config.get("signal_name") not in matched_signal_names:
                continue

            target_category = (signal_config.get("merchant_category") or "").strip().lower()
            minimum_amount = float(signal_config.get("minimum_amount") or 0)

            for row in transaction_rows:
                row_category = (row.get("merchant_category") or "").strip().lower()
                if row_category != target_category:
                    continue
                try:
                    amount = float(row.get("transaction_amount") or 0)
                except (TypeError, ValueError):
                    continue
                if amount < minimum_amount:
                    continue

                label = row.get("description") or row.get("merchant_category") or "Transaction"
                drivers.append({
                    "label": str(label),
                    "category": payment_type_for_category(row.get("merchant_category")),
                    "amount": format_currency(amount),
                    "time": relative_time_label(row.get("transaction_date")),
                })
                break  # one representative transaction per configured signal

    if not drivers:
        for text in (getattr(life_event, "key_drivers", None) or []):
            drivers.append({
                "label": str(text),
                "category": "Card Payment",
                "amount": "—",
                "time": "Recent",
            })

    return drivers[:limit]


def _get_event_rule(event_type: str) -> Optional[Dict[str, Any]]:
    """Finds the rule block for an event type, tolerating loader differences."""
    try:
        rules = _rule_loader.load_life_event_rules()
    except Exception:
        return None

    if isinstance(rules, dict):
        candidates = rules.get("life_events", [])
    elif isinstance(rules, list):
        candidates = rules
    else:
        return None

    for rule in candidates:
        if str(rule.get("life_event_type", "")).strip().lower() == str(event_type).strip().lower():
            return rule
    return None


# ---------------------------------------------------------------------------
# Analytics insight cards
# ---------------------------------------------------------------------------


def build_analytics(
    life_event: Any,
    transaction_rows: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Builds the four insight cards shown on the Event Detection step.
    Every figure here is computed from the actual transaction set, not
    generated -- so the advisor can trace any number back to the data.
    """
    event_type = getattr(life_event, "life_event_type", None) or "the detected event"
    event_rule = _get_event_rule(event_type) or {}
    relevant_categories = {
        (s.get("merchant_category") or "").strip().lower()
        for s in event_rule.get("transaction_signals", [])
    }

    event_related_total = 0.0
    event_related_count = 0
    total_spend = 0.0
    latest_date: Optional[date] = None

    for row in transaction_rows:
        try:
            amount = float(row.get("transaction_amount") or 0)
        except (TypeError, ValueError):
            continue
        total_spend += amount
        category = (row.get("merchant_category") or "").strip().lower()
        if category in relevant_categories:
            event_related_total += amount
            event_related_count += 1
        parsed = _parse_date(row.get("transaction_date"))
        if parsed and (latest_date is None or parsed > latest_date):
            latest_date = parsed

    share = (event_related_total / total_spend * 100) if total_spend else 0.0
    matched_signals = [s for s in (getattr(life_event, "signals", None) or []) if getattr(s, "matched", False)]

    spending_pattern = (
        f"{event_related_count} transactions totalling {format_currency(event_related_total, signed=False)} "
        f"relate to {event_type.lower()} — {share:.0f}% of total spend in the period."
        if event_related_count
        else "No concentrated event-related spending pattern identified in the current transaction window."
    )

    jump_in_spend = (
        f"{format_currency(event_related_total, signed=False)} of event-related spend across "
        f"{len(matched_signals)} matched signal{'s' if len(matched_signals) != 1 else ''}."
        if matched_signals
        else "Spend levels remain consistent with the customer's baseline."
    )

    season = (
        f"Most recent qualifying activity: {relative_time_label(latest_date)}. "
        f"Estimated event timeline: {getattr(life_event, 'estimated_timeline', 'not established')}."
        if latest_date
        else f"Estimated event timeline: {getattr(life_event, 'estimated_timeline', 'not established')}."
    )

    matched_names = [getattr(s, "signal_name", "") for s in matched_signals]
    supporting_note = (
        "Signals matched: " + "; ".join(n for n in matched_names if n) + "."
        if matched_names
        else "No individual signals met their configured thresholds."
    )

    return {
        "spending_pattern": spending_pattern,
        "jump_in_spend": jump_in_spend,
        "season": season,
        "supporting_note": supporting_note,
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def map_recommendations(
    recommendations: List[Any],
    life_event: Any,
    customer_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Enriches the agents' recommendations with the match scores and
    historical statistics the UI displays.

    - Event Match is derived from the event's own confidence and the
      recommendation's rank (rank 1 aligns most strongly with the event).
    - Customer Match additionally reflects KYC standing and whether the
      recommendation cleared compliance for this specific customer.
    - Historical statistics come from the product_stats lookup table --
      never generated, see that module's docstring.
    """
    event_type = getattr(life_event, "life_event_type", "") or ""
    confidence = float(getattr(life_event, "confidence_score", 0.0) or 0.0)
    kyc_ok = str(customer_data.get("kyc_status", "")).strip().lower() in {"verified", "valid", "complete"}

    mapped: List[Dict[str, Any]] = []

    for index, rec in enumerate(recommendations):
        name = _attr(rec, "recommendation_name") or _attr(rec, "name") or f"Recommendation {index + 1}"
        rationale = _attr(rec, "rationale") or ""
        rank = int(_attr(rec, "rank") or (index + 1))
        compliance_status = str(_attr(rec, "compliance_status") or "Pending")

        rank_penalty = max(0, (rank - 1)) * 6
        match_event = _clamp(round(confidence * 100) - rank_penalty)

        customer_adjustment = 0
        if kyc_ok:
            customer_adjustment += 4
        if compliance_status.strip().lower() in {"passed", "pass", "approved", "compliant"}:
            customer_adjustment += 4
        elif compliance_status.strip().lower() in {"blocked", "failed", "rejected"}:
            customer_adjustment -= 25
        match_customer = _clamp(match_event - 3 + customer_adjustment)

        stats = get_product_stats(event_type, name)

        justification = rationale or (
            f"{name} is aligned with the detected {event_type.lower()} event "
            f"(confidence {confidence * 100:.0f}%)."
        )
        if compliance_status and compliance_status.strip().lower() not in {"pending", ""}:
            justification = f"{justification} Compliance status: {compliance_status}."

        mapped.append({
            "id": index + 1,
            "title": str(name),
            "rationale": rationale or f"Relevant to the detected {event_type.lower()} event.",
            "match_event": match_event,
            "match_customer": match_customer,
            "justification": justification,
            "conversion_rate": stats["conversion_rate"],
            "avg_days_to_take_up": stats["avg_days_to_take_up"],
            "avg_amount": stats["avg_amount"],
            "historical_note": stats["historical_note"],
            "order_index": index,
        })

    return mapped


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Reads an attribute from a pydantic model or a plain dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _clamp(value: float, low: int = 0, high: int = 99) -> int:
    return int(max(low, min(high, value)))


# ---------------------------------------------------------------------------
# Advisor brief
# ---------------------------------------------------------------------------


RISK_NARRATIVES = {
    "conservative": (
        "Capital preservation and stable income are the primary objectives.",
        "Prioritise protection and liquidity; avoid recommendations that increase volatility exposure.",
    ),
    "balanced": (
        "Comfortable with moderate growth and can tolerate short-term market movement for long-term return.",
        "Keep core investments intact; use short-term credit or cash buffers for event-driven liquidity needs.",
    ),
    "aggressive": (
        "Comfortable with higher volatility in pursuit of long-term returns.",
        "Capacity exists for growth-oriented products, but confirm short-term liquidity is not compromised.",
    ),
    "growth": (
        "Focused on building wealth through higher-return investments over the long term.",
        "Balance the event's immediate funding needs against ongoing investment contributions.",
    ),
}


def map_advisor_brief(
    advisor_insight: Any,
    life_event: Any,
    customer_data: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
    event_confirmed: bool,
) -> Dict[str, Any]:
    """Maps the Advisor Insights agent output into the UI's briefing shape."""
    risk_label = (customer_data.get("risk_profile") or customer_data.get("risk") or "Balanced").strip()
    summary, advisor_note = RISK_NARRATIVES.get(
        risk_label.lower(),
        ("Risk profile on record for this customer.", "Confirm suitability before presenting recommendations."),
    )

    event_type = getattr(life_event, "life_event_type", "the detected event")
    confidence = float(getattr(life_event, "confidence_score", 0.0) or 0.0)

    talking_points = list(_attr(advisor_insight, "suggested_talking_points") or [])
    opportunities = list(_attr(advisor_insight, "key_opportunities") or [])

    behavior_analytics = _build_behavior_analytics(life_event, customer_data, confidence, event_type)

    recommendation_talking_points = [
        f"Introduce {rec['title']}: {rec['rationale']}"
        for rec in recommendations[:2]
    ] or ["Walk through the recommended products in priority order once the event is confirmed."]

    next_best_action = _attr(advisor_insight, "next_best_action")
    if next_best_action:
        recommendation_talking_points.append(f"Next best action: {next_best_action}")

    return {
        "behavior_analytics": behavior_analytics,
        "talking_points": talking_points or [
            "Open by asking whether any major life changes are coming up that they would like to plan for.",
            "Reference the recent account activity in general terms and gauge their reaction.",
            "Confirm the likely timeline before discussing any specific products.",
        ],
        "recommendation_talking_points": recommendation_talking_points,
        "opportunities": opportunities or [rec["title"] for rec in recommendations[:4]],
        "risk_appetite": {
            "label": risk_label,
            "summary": f"{customer_data.get('name', 'This client')} is profiled as {risk_label} — {summary}",
            "event_impact": (
                f"The detected {event_type.lower()} event should be assessed against this risk profile "
                f"before any product is presented."
            ),
            "advisor_note": advisor_note,
        },
        "event_confirmed": event_confirmed,
    }


def _build_behavior_analytics(life_event, customer_data, confidence, event_type) -> List[str]:
    bullets: List[str] = []

    age = customer_data.get("age")
    segment = customer_data.get("segment") or "—"
    risk = customer_data.get("risk_profile") or "Balanced"
    age_part = f"{age}-year-old " if age else ""
    bullets.append(f"{age_part}{segment} client with a {risk} risk profile.")

    bullets.append(
        f"Detected event: {event_type} at {confidence * 100:.0f}% confidence, "
        f"estimated timeline {getattr(life_event, 'estimated_timeline', 'not established')}."
    )

    matched = [s for s in (getattr(life_event, "signals", None) or []) if getattr(s, "matched", False)]
    if matched:
        bullets.append(
            f"{len(matched)} transaction signal{'s' if len(matched) != 1 else ''} matched the configured "
            f"thresholds for this event type."
        )

    score_source = getattr(life_event, "score_source", None)
    if score_source == "ML_MODEL":
        bullets.append("Confidence score produced by the trained per-event ML model.")
    elif score_source:
        bullets.append("Confidence score produced by the configured rules engine (no ML model available).")

    return bullets


# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------


SENTIMENT_GUIDANCE = {
    "positive": "Client is highly receptive. All recommended products are appropriate to present — lead with the highest-conversion option.",
    "negative": "Client appears hesitant. Focus on the single strongest recommendation and defer secondary products to a follow-up conversation.",
    "neutral": "Neutral engagement detected. Lead with your top two recommendations and assess response before broadening the conversation.",
}


def map_sentiment(sentiment_insight: Any, interaction_text: str, selected_products: List[str]) -> Dict[str, Any]:
    """Maps the Sentiment agent output into the UI's shape."""
    sentiment = str(_attr(sentiment_insight, "sentiment") or "Neutral")
    return {
        "interaction_text": interaction_text or "",
        "sentiment": sentiment,
        "score": int(_attr(sentiment_insight, "engagement_score") or 0),
        "guidance": SENTIMENT_GUIDANCE.get(sentiment.strip().lower(), SENTIMENT_GUIDANCE["neutral"]),
        "primary_intent": str(_attr(sentiment_insight, "primary_intent") or ""),
        "secondary_intents": list(_attr(sentiment_insight, "secondary_intents") or []),
        "selected_products": selected_products or [],
    }


def auto_select_products(sentiment: str, recommendations: List[Dict[str, Any]]) -> List[str]:
    """
    Deterministic product selection driven by the sentiment classification.
    Intentionally a fixed rule, not a model decision -- an advisor can
    predict and audit it.
    """
    titles = [rec["title"] for rec in recommendations]
    normalised = (sentiment or "").strip().lower()
    if normalised == "positive":
        return titles
    if normalised == "negative":
        return titles[:1]
    return titles[:2]


# ---------------------------------------------------------------------------
# Workflow orchestration
# ---------------------------------------------------------------------------


def map_tasks(workflow_tasks: List[Any], selected_products: List[str]) -> List[Dict[str, str]]:
    """
    Maps the Workflow agent's tasks into the UI's task list. If the agent
    returned nothing (e.g. no products selected yet), falls back to the
    standard five-task template so the UI always has something meaningful
    to display.
    """
    if workflow_tasks:
        return [
            {
                "name": str(_attr(task, "task_name") or "Task"),
                "status": _normalise_task_status(_attr(task, "status")),
            }
            for task in workflow_tasks
        ]

    if not selected_products:
        return [{"name": "Await product selection", "status": "Pending"}]

    products_label = ", ".join(selected_products)
    return [
        {"name": f"Product specialist call — {products_label}", "status": "Created"},
        {"name": "Prepare recommendation pack", "status": "Created"},
        {"name": "Capture customer consent & disclosures", "status": "Pending"},
        {"name": "Hand over to CRM / onboarding system", "status": "Action Required"},
        {"name": "Onboard customer to product", "status": "Yet to start"},
    ]


def _normalise_task_status(status: Any) -> str:
    """Maps agent task statuses onto the four the UI styles."""
    text = str(status or "Pending").strip().lower()
    mapping = {
        "open": "Created",
        "created": "Created",
        "in progress": "Created",
        "pending": "Pending",
        "scheduled": "Pending",
        "action required": "Action Required",
        "blocked": "Action Required",
        "not started": "Yet to start",
        "yet to start": "Yet to start",
        "completed": "Created",
    }
    return mapping.get(text, "Pending")


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------


def priority_from_confidence(confidence: float) -> str:
    if confidence >= 0.8:
        return "High"
    if confidence >= 0.6:
        return "Medium"
    return "Low"


def map_case(state: Any) -> Optional[Dict[str, Any]]:
    """Maps the persisted workflow-state row into the UI's case shape."""
    if state is None or not getattr(state, "case_ref", None):
        return None

    opened_at = getattr(state, "case_opened_at", None)
    if opened_at is None:
        opened_display, days_open = "—", 0
    else:
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        opened_display = opened_at.strftime("%d %b %Y")
        days_open = max(0, (datetime.now(timezone.utc) - opened_at).days)

    return {
        "id": state.case_ref,
        "status": state.case_status or "Open",
        "priority": state.case_priority or "Medium",
        "opened": opened_display,
        "days_open": days_open,
    }
