from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionEvaluationRequest
from app.repositories.customer_repository import CustomerRepository
from app.repositories.transaction_repository import TransactionRepository
from app.agents.event_detection_agent import EventDetectionAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.advisor_insights_agent import AdvisorInsightsAgent

router = APIRouter()

customer_repository = CustomerRepository()
transaction_repository = TransactionRepository()
event_detection_agent = EventDetectionAgent()
recommendation_agent = RecommendationAgent()
advisor_insights_agent = AdvisorInsightsAgent()


@router.post("/generate/{customer_id}")
def generate_advisor_insights_by_customer_id(
    customer_id: str,
    db: Session = Depends(get_db)
):
    customer_data = customer_repository.get_customer_by_id(db, customer_id)

    if not customer_data:
        raise HTTPException(
            status_code=404,
            detail=f"Customer not found: {customer_id}"
        )

    transaction_rows = transaction_repository.get_transactions_by_customer_id(
        db=db,
        customer_id=customer_id
    )

    if not transaction_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No transactions found for customer: {customer_id}"
        )

    customer = Customer(
        customer_id=customer_data["customer_id"],
        name=customer_data["name"],
        age=customer_data["age"],
        annual_income=float(customer_data["annual_income"]) if customer_data.get("annual_income") else None,
        segment=customer_data.get("segment"),
        relationship_manager=customer_data.get("relationship_manager")
    )

    transactions = [
        Transaction(
            transaction_id=row["transaction_id"],
            merchant_category=row["merchant_category"],
            transaction_amount=float(row["transaction_amount"]),
            transaction_date=str(row["transaction_date"]),
            frequency=row["frequency"],
            location=row["location"],
            description=row["description"]
        )
        for row in transaction_rows
    ]

    request = TransactionEvaluationRequest(
        customer=customer,
        transactions=transactions,
        conversation_text=None,
        conversation_permitted=False,
        kyc_status=customer_data.get("kyc_status", "valid"),
        nominee_available=customer_data.get("nominee_available", False),
        joint_account_eligible=customer_data.get("joint_account_eligible", True),
        communication_consent=customer_data.get("communication_consent", True)
    )

    life_event = event_detection_agent.detect(request)

    recommendations = []

    if life_event.actionable:
        recommendations = recommendation_agent.generate(
            customer=customer,
            life_event=life_event
        )

    advisor_insight = advisor_insights_agent.generate(
        customer=customer,
        life_event=life_event,
        recommendations=recommendations,
        customer_data=customer_data
    )

    return {
        "status": "Advisor Insights Generated",
        "advisor_insight": advisor_insight
    }