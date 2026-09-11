from typing import List

from app.models.sentiment import SentimentInsight


class SentimentAgent:
    """
    Analyzes customer conversation text when permitted.

    This starter version uses keyword-based logic.
    You can later replace this with an LLM or NLP model.
    """

    def analyze(
        self,
        customer_id: str,
        conversation_text: str,
        conversation_permitted: bool
    ) -> SentimentInsight:
        if not conversation_permitted or not conversation_text:
            return SentimentInsight(
                customer_id=customer_id,
                sentiment="Not Available",
                primary_intent="Conversation unavailable or not permitted",
                secondary_intents=[],
                engagement_score=0,
                customer_confirmed_event=False
            )

        text = conversation_text.lower()

        customer_confirmed_event = self._has_life_event_intent(text)
        sentiment = self._detect_sentiment(text)
        primary_intent = self._detect_primary_intent(text, customer_confirmed_event)
        secondary_intents = self._detect_secondary_intents(text)
        engagement_score = self._calculate_engagement_score(
            text=text,
            customer_confirmed_event=customer_confirmed_event
        )

        return SentimentInsight(
            customer_id=customer_id,
            sentiment=sentiment,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            engagement_score=engagement_score,
            customer_confirmed_event=customer_confirmed_event
        )

    def _has_life_event_intent(self, text: str) -> bool:
        keywords = [
            "marriage",
            "wedding",
            "birthday",
            "travel",
            "trip",
            "home purchase",
            "baby",
            "education",
            "retirement"
        ]

        return any(keyword in text for keyword in keywords)

    def _detect_sentiment(self, text: str) -> str:
        positive_keywords = [
            "planning",
            "happy",
            "excited",
            "confirmed",
            "looking forward",
            "celebrating"
        ]

        negative_keywords = [
            "worried",
            "concerned",
            "problem",
            "issue",
            "delay",
            "confused"
        ]

        if any(keyword in text for keyword in positive_keywords):
            return "Positive"

        if any(keyword in text for keyword in negative_keywords):
            return "Negative"

        return "Neutral"

    def _detect_primary_intent(
        self,
        text: str,
        customer_confirmed_event: bool
    ) -> str:
        if "wedding" in text or "marriage" in text:
            return "Marriage confirmed"

        if "travel" in text or "trip" in text:
            return "Travel intent detected"

        if "birthday" in text:
            return "Birthday milestone detected"

        if customer_confirmed_event:
            return "Life event intent detected"

        return "General conversation"

    def _detect_secondary_intents(self, text: str) -> List[str]:
        intents: List[str] = []

        if "insurance" in text:
            intents.append("Insurance planning")

        if "family" in text:
            intents.append("Family financial planning")

        if "investment" in text:
            intents.append("Investment planning")

        if "savings" in text:
            intents.append("Savings planning")

        if "house" in text or "home" in text:
            intents.append("Home purchase planning")

        return intents

    def _calculate_engagement_score(
        self,
        text: str,
        customer_confirmed_event: bool
    ) -> int:
        score = 50

        if customer_confirmed_event:
            score += 25

        if len(text.split()) >= 8:
            score += 10

        if any(keyword in text for keyword in ["planning", "confirmed", "looking"]):
            score += 10

        if any(keyword in text for keyword in ["family", "insurance", "investment"]):
            score += 5

        return min(score, 100)