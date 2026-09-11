from typing import List

from app.models.customer import Customer
from app.models.life_event import LifeEventInsight
from app.models.recommendation import Recommendation


class AdvisorInsightsAgent:
    """
    Builds advisor-ready insights from:
    - Customer profile
    - Detected life event
    - AI summary
    - Advisor talking points
    - Recommendations
    - Approval status
    """

    def generate(
        self,
        customer: Customer,
        life_event: LifeEventInsight,
        recommendations: List[Recommendation],
        customer_data: dict
    ) -> dict:
        if not life_event.actionable:
            return self._generate_non_actionable_insight(
                customer=customer,
                life_event=life_event,
                customer_data=customer_data
            )

        return self._generate_actionable_insight(
            customer=customer,
            life_event=life_event,
            recommendations=recommendations,
            customer_data=customer_data
        )

    def _generate_actionable_insight(
        self,
        customer: Customer,
        life_event: LifeEventInsight,
        recommendations: List[Recommendation],
        customer_data: dict
    ) -> dict:
        recommendation_names = [
            recommendation.recommendation_name
            for recommendation in recommendations
        ]

        return {
            "customer": self._customer_profile(customer_data),
            "life_event": {
                "event_id": life_event.event_id,
                "life_event_type": life_event.life_event_type,
                "confidence_score": life_event.confidence_score,
                "score_source": life_event.score_source,
                "estimated_timeline": life_event.estimated_timeline,
                "status": life_event.status,
                "actionable": life_event.actionable,
                "key_drivers": life_event.key_drivers,
                "ai_summary": life_event.ai_summary,
                "advisor_talking_points": life_event.advisor_talking_points,
                "approval_status": life_event.approval_status,
                "customer_facing_allowed": life_event.customer_facing_allowed
            },
            "recommendations": [
                recommendation.model_dump()
                for recommendation in recommendations
            ],
            "recommendation_summary": {
                "recommendation_count": len(recommendations),
                "recommended_products": recommendation_names,
                "approval_required": True,
                "customer_facing_allowed": False
            },
            "advisor_guidance": {
                "next_best_action": self._next_best_action(life_event),
                "key_opportunities": self._key_opportunities(life_event.life_event_type),
                "engagement_priority": "High" if life_event.confidence_score >= 0.8 else "Medium"
            }
        }

    def _generate_non_actionable_insight(
        self,
        customer: Customer,
        life_event: LifeEventInsight,
        customer_data: dict
    ) -> dict:
        return {
            "customer": self._customer_profile(customer_data),
            "life_event": {
                "event_id": life_event.event_id,
                "life_event_type": life_event.life_event_type,
                "confidence_score": life_event.confidence_score,
                "score_source": life_event.score_source,
                "estimated_timeline": life_event.estimated_timeline,
                "status": life_event.status,
                "actionable": life_event.actionable,
                "key_drivers": life_event.key_drivers,
                "ai_summary": life_event.ai_summary,
                "advisor_talking_points": life_event.advisor_talking_points,
                "approval_status": life_event.approval_status,
                "customer_facing_allowed": life_event.customer_facing_allowed
            },
            "recommendations": [],
            "recommendation_summary": {
                "recommendation_count": 0,
                "recommended_products": [],
                "approval_required": False,
                "customer_facing_allowed": False
            },
            "advisor_guidance": {
                "next_best_action": "Monitor additional signals before proceeding",
                "key_opportunities": [],
                "engagement_priority": "Low"
            }
        }

    def _customer_profile(self, customer_data: dict) -> dict:
        return {
            "customer_id": customer_data.get("customer_id"),
            "name": customer_data.get("name"),
            "age": customer_data.get("age"),
            "annual_income": float(customer_data["annual_income"]) if customer_data.get("annual_income") else None,
            "portfolio": customer_data.get("portfolio"),
            "risk": customer_data.get("risk_profile"),
            "last_review": str(customer_data["last_review"]) if customer_data.get("last_review") else None,
            "account_type": customer_data.get("account_type"),
            "account_number": customer_data.get("account_number"),
            "sort_code": customer_data.get("sort_code"),
            "balance": float(customer_data["balance"]) if customer_data.get("balance") else None,
            "source": customer_data.get("source"),
            "account_source": customer_data.get("account_source"),
            "segment": customer_data.get("segment"),
            "relationship_manager": customer_data.get("relationship_manager")
        }

    def _next_best_action(self, life_event: LifeEventInsight) -> str:
        if not life_event.actionable:
            return "Monitor additional signals before proceeding"

        return "Advisor review and customer engagement preparation"

    def _key_opportunities(self, life_event_type: str) -> List[str]:
        if life_event_type == "Marriage":
            return [
                "Update nominee",
                "Review insurance coverage",
                "Discuss joint savings or joint investment options",
                "Review emergency fund planning"
            ]

        if life_event_type == "Travel":
            return [
                "Travel insurance",
                "Travel credit card",
                "Foreign exchange service",
                "Travel-related spending review"
            ]

        if life_event_type == "Birthday":
            return [
                "Savings goal review",
                "Investment portfolio review",
                "Financial milestone conversation"
            ]

        if life_event_type == "Home Purchase":
            return [
                "Mortgage consultation",
                "Home insurance review",
                "Emergency fund review",
                "Affordability planning"
            ]

        if life_event_type == "Education":
            return [
                "Education savings plan",
                "Student banking review",
                "Long-term education funding plan"
            ]

        return []