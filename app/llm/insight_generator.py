import json
import logging
from typing import List, Optional

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    LLM-backed insight generator.

    If LLM configuration is missing or the LLM call fails,
    it falls back to deterministic advisor summary generation.
    """

    def __init__(self):
        # Reads from app.config.settings, which resolves LLM_* first and
        # falls back to the legacy GEMMA_* names. Previously this read
        # GEMMA_* straight from the environment, so a .env using LLM_*
        # left every field None and the LLM was never called.
        self.api_key = settings.llm_api_key
        self.api_url = settings.llm_api_url
        self.model_name = settings.llm_model_name

    def generate_summary(
        self,
        customer_name: str,
        life_event_type: str,
        confidence_score: float,
        key_drivers: List[str],
        estimated_timeline: str,
        status: Optional[str] = None,
        score_source: Optional[str] = None,
        actionable: Optional[bool] = None
    ) -> dict:
        if life_event_type == "Unknown":
            return {
                "ai_summary": "No qualified life event has been detected based on the available transaction signals.",
                "advisor_talking_points": [
                    "Continue monitoring transaction and engagement signals",
                    "Review customer profile during the next scheduled interaction"
                ]
            }

        prompt = self._build_prompt(
            customer_name=customer_name,
            life_event_type=life_event_type,
            confidence_score=confidence_score,
            key_drivers=key_drivers,
            estimated_timeline=estimated_timeline,
            status=status,
            score_source=score_source,
            actionable=actionable
        )

        llm_response = self._call_llm(prompt)

        if llm_response:
            return llm_response

        return self._fallback_summary(
            customer_name=customer_name,
            life_event_type=life_event_type,
            confidence_score=confidence_score,
            key_drivers=key_drivers,
            estimated_timeline=estimated_timeline,
            status=status,
            score_source=score_source,
            actionable=actionable
        )

    def _build_prompt(
        self,
        customer_name: str,
        life_event_type: str,
        confidence_score: float,
        key_drivers: List[str],
        estimated_timeline: str,
        status: Optional[str],
        score_source: Optional[str],
        actionable: Optional[bool]
    ) -> str:
        drivers_text = ", ".join(key_drivers) if key_drivers else "No strong transaction drivers"

        return f"""
You are an AI assistant supporting a banking relationship advisor.

Generate a concise advisor-facing life event insight.

Customer name: {customer_name}
Detected life event: {life_event_type}
Confidence score: {confidence_score}
Score source: {score_source}
Estimated timeline: {estimated_timeline}
Matched key drivers: {drivers_text}
Actionable: {actionable}
Status: {status}

Rules:
- Do not provide regulated financial advice.
- Do not say the event is confirmed unless the customer explicitly confirmed it.
- If status is not actionable, explain why the advisor should review or monitor.
- Keep the tone professional and concise.
- Return only valid JSON.

JSON format:
{{
  "ai_summary": "string",
  "advisor_talking_points": [
    "string",
    "string",
    "string"
  ]
}}
"""

    def _call_llm(self, prompt: str) -> Optional[dict]:
        # An API key is NOT required: local providers such as Ollama, vLLM
        # and LM Studio expose an OpenAI-compatible endpoint with no auth.
        # Only the URL and model name are mandatory.
        if not self.api_url or not self.model_name:
            logger.debug("LLM not configured (missing url or model) - using deterministic fallback.")
            return None

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if "chat/completions" in self.api_url:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You generate concise banking advisor insights in valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                }
            else:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": 0.2,
                    "max_tokens": 500
                }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()
            content = self._extract_content(data)

            if not content:
                return None

            return self._parse_json_response(content)

        except Exception as exc:
            # Logged rather than silently swallowed: without this, an
            # unreachable Ollama and a working one that returns bad JSON
            # look identical from the outside (both give template text).
            logger.warning("LLM call failed (%s) - falling back to deterministic summary.", exc)
            return None

    def _extract_content(self, data: dict) -> Optional[str]:
        choices = data.get("choices", [])

        if not choices:
            return None

        first_choice = choices[0]

        if "message" in first_choice:
            return first_choice["message"].get("content")

        if "text" in first_choice:
            return first_choice.get("text")

        return None

    def _parse_json_response(self, content: str) -> Optional[dict]:
        try:
            content = content.strip()

            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()

            if content.startswith("```"):
                content = content.replace("```", "").strip()

            parsed = json.loads(content)

            if "ai_summary" not in parsed:
                return None

            if "advisor_talking_points" not in parsed:
                parsed["advisor_talking_points"] = []

            return parsed

        except Exception:
            return None

    def _fallback_summary(
        self,
        customer_name: str,
        life_event_type: str,
        confidence_score: float,
        key_drivers: List[str],
        estimated_timeline: str,
        status: Optional[str],
        score_source: Optional[str],
        actionable: Optional[bool]
    ) -> dict:
        drivers_text = ", ".join(key_drivers) if key_drivers else "available customer signals"

        score_source_label = {
            "ML_MODEL": "trained confidence model",
            "PLACEHOLDER_RULE_SCORE": "rules engine",
        }.get(score_source, score_source or "scoring engine")

        if actionable:
            ai_summary = (
                f"{customer_name} shows indicators of a potential {life_event_type} life event. "
                f"The confidence score is {confidence_score * 100:.0f}%, generated by the {score_source_label}. "
                f"Key drivers include {drivers_text}. "
                f"The estimated timeline is {estimated_timeline}. "
                f"This should be reviewed by an advisor before any customer-facing action."
            )
        else:
            ai_summary = (
                f"{customer_name} has some signals related to a potential {life_event_type} life event, "
                f"but the event is not currently actionable. "
                f"The confidence score is {confidence_score * 100:.0f}%, generated by the {score_source_label}. "
                f"Current status is: {status}. "
                f"Matched drivers include {drivers_text}. "
                f"The advisor should monitor or validate additional signals before proceeding."
            )

        return {
            "ai_summary": ai_summary,
            "advisor_talking_points": self._talking_points_for_event(life_event_type, actionable)
        }

    def _talking_points_for_event(
        self,
        life_event_type: str,
        actionable: Optional[bool]
    ) -> List[str]:
        if not actionable:
            return [
                "Review the detected signals before taking action",
                "Check whether additional customer confirmation is available",
                "Avoid customer-facing recommendations until the event is qualified"
            ]

        if life_event_type == "Marriage":
            return [
                "Congratulate the customer if the event is confirmed",
                "Discuss short-term and long-term financial goals",
                "Review insurance and nominee requirements",
                "Discuss emergency fund planning",
                "Explore joint savings or goal-based investment options"
            ]

        if life_event_type == "Travel":
            return [
                "Ask about upcoming travel plans",
                "Discuss travel insurance options",
                "Review foreign exchange or travel card needs",
                "Confirm communication preferences"
            ]

        if life_event_type == "Birthday":
            return [
                "Use the milestone to review financial goals",
                "Discuss savings or investment planning",
                "Offer a portfolio or financial health review"
            ]

        if life_event_type == "Home Purchase":
            return [
                "Discuss home purchase timeline",
                "Review mortgage or affordability needs",
                "Discuss protection and emergency fund planning"
            ]

        if life_event_type == "Education":
            return [
                "Discuss education funding needs",
                "Review savings or student banking options",
                "Explore long-term financial planning requirements"
            ]

        return [
            f"Discuss the detected {life_event_type} event",
            "Review customer needs and suitability",
            "Confirm approval status before customer engagement"
        ]


insight_generator = InsightGenerator()