"""
Provider-agnostic LLM service.

Speaks the OpenAI-compatible /chat/completions protocol, which means it
works unchanged against:

  - Ollama (local, free)      http://localhost:11434/v1/chat/completions
  - vLLM (self-hosted, free)  http://<host>:8000/v1/chat/completions
  - LM Studio (local, free)   http://localhost:1234/v1/chat/completions
  - any hosted OpenAI-compatible gateway (needs an API key)

Configure via .env - see .env.example. If no provider is reachable, every
method degrades to returning empty output rather than raising, and the
calling code falls back to deterministic, rules-derived text. The UI never
shows an error because of an unavailable model.
"""
import json
from typing import List, Optional

import requests

from app.config import settings


class LLMService:
    def __init__(self):
        self.api_key = settings.llm_api_key
        self.api_url = settings.llm_api_url
        self.model = settings.llm_model_name
        self.timeout = settings.llm_timeout_seconds

    # -- internals ---------------------------------------------------------

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _is_available(self) -> bool:
        return settings.llm_configured

    def _chat(self, prompt: str, max_tokens: int = 400, temperature: float = 0.3) -> str:
        """Single-turn chat completion. Returns '' on any failure."""
        if not self._is_available():
            return ""

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self._headers(),
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict):
                return ""

            choices = data.get("choices") or []
            if choices:
                first = choices[0]
                message = first.get("message") or {}
                content = message.get("content") or first.get("text")
                if content:
                    return str(content).strip()

            # Ollama's native (non-OpenAI) response shape, just in case
            message = data.get("message") or {}
            if message.get("content"):
                return str(message["content"]).strip()

            if data.get("response"):
                return str(data["response"]).strip()

            return ""
        except Exception:
            return ""

    def _format_transactions(self, transactions: List[dict]) -> str:
        lines = []
        for t in transactions[:50]:
            tid = t.get("transaction_id") or t.get("transactionId") or ""
            amount = t.get("transaction_amount") or t.get("amount") or ""
            category = t.get("merchant_category") or t.get("merchantCategory") or ""
            date = t.get("transaction_date") or t.get("transactionDate") or ""
            description = t.get("description") or ""
            lines.append(f"- {date} | {category} | {amount} | {description} ({tid})")
        return "\n".join(lines)

    # -- public API --------------------------------------------------------

    def generate_event_summary(
        self,
        customer: object,
        life_event: object,
        transactions: List[object],
        conversation_text: Optional[str] = None,
        max_tokens: int = 400,
    ) -> str:
        """
        Advisor-facing summary of a detected life event. Returns '' if no
        LLM provider is configured or reachable - callers fall back to a
        deterministic summary built from the rules engine's own output.
        """
        if not self._is_available():
            return ""

        parts = [
            f"Customer: {getattr(customer, 'name', getattr(customer, 'customer_id', 'Unknown'))}",
            f"Detected Event: {getattr(life_event, 'life_event_type', 'Unknown')}",
            f"Confidence: {float(getattr(life_event, 'confidence_score', 0.0) or 0.0) * 100:.0f}%",
            f"Timeline: {getattr(life_event, 'estimated_timeline', '')}",
        ]

        key_drivers = getattr(life_event, "key_drivers", None)
        if key_drivers:
            parts.append(f"Key drivers: {', '.join(str(k) for k in key_drivers)}")

        parts.append("Transactions (most relevant, up to 50):")
        txs = [t.dict() if hasattr(t, "dict") else t for t in transactions]
        parts.append(self._format_transactions(txs))

        if conversation_text:
            parts.append("Customer conversation:")
            parts.append(conversation_text)

        parts.append(
            "\nWrite a concise 2-3 sentence professional advisor-facing summary explaining: "
            "1) what pattern was detected, 2) which transactions triggered it, and 3) why this "
            "indicates the life event. Use plain, non-technical language. Do not invent any "
            "figures that are not present in the data above."
        )

        return self._chat("\n\n".join(p for p in parts if p), max_tokens=max_tokens)
