from typing import List

from app.models.customer import Customer
from app.models.life_event import LifeEventInsight
from app.models.recommendation import Recommendation
from app.services.rule_loader_service import RuleLoaderService


class RecommendationAgent:
    """
    Generates personalised recommendations based on:
    - Customer profile
    - Detected actionable life event
    - Configured recommendation mappings
    """

    def __init__(self):
        self.rule_loader = RuleLoaderService()

    def generate(
        self,
        customer: Customer,
        life_event: LifeEventInsight
    ) -> List[Recommendation]:
        if not life_event.actionable:
            return []

        mappings = self.rule_loader.load_recommendation_mappings()
        mapped_recommendations = mappings.get(life_event.life_event_type, [])

        recommendations: List[Recommendation] = []

        for index, item in enumerate(mapped_recommendations, start=1):
            recommendations.append(
                Recommendation(
                    recommendation_id=item["recommendation_id"],
                    customer_id=customer.customer_id,
                    event_id=life_event.event_id,
                    life_event_type=life_event.life_event_type,
                    recommendation_name=item["recommendation_name"],
                    rationale=item["rationale"],
                    rank=index,
                    compliance_status="Pending",
                    approval_status="Pending Human Approval",
                    customer_facing_allowed=False
                )
            )

        return recommendations