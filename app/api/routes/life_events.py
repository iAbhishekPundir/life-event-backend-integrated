from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionEvaluationRequest
from app.repositories.customer_repository import CustomerRepository
from app.repositories.transaction_repository import TransactionRepository
from app.agents.event_detection_agent import EventDetectionAgent

router = APIRouter()

customer_repository = CustomerRepository()
transaction_repository = TransactionRepository()
event_detection_agent = EventDetectionAgent()


@router.post("/detect/{customer_id}")
def detect_life_event_by_customer_id(
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
        annual_income=float(customer_data["annual_income"]) if customer_data["annual_income"] else None,
        segment=customer_data["segment"],
        relationship_manager=customer_data["relationship_manager"]
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
        kyc_status=customer_data["kyc_status"],
        nominee_available=customer_data["nominee_available"],
        joint_account_eligible=customer_data["joint_account_eligible"],
        communication_consent=customer_data["communication_consent"]
    )

    life_event = event_detection_agent.detect(request)

    return {
    "customer": {
        "customer_id": customer_data["customer_id"],
        "name": customer_data["name"],
        "age": customer_data["age"],
        "annual_income": float(customer_data["annual_income"]) if customer_data["annual_income"] else None,
        "portfolio": customer_data.get("portfolio"),
        "risk": customer_data.get("risk_profile"),
        "last_review": str(customer_data["last_review"]) if customer_data.get("last_review") else None,
        "account_type": customer_data.get("account_type"),
        "account_number": customer_data.get("account_number"),
        "sort_code": customer_data.get("sort_code"),
        "balance": float(customer_data["balance"]) if customer_data.get("balance") else None,
        "source": customer_data.get("source"),
        "account_source": customer_data.get("account_source"),
        "segment": customer_data["segment"],
        "relationship_manager": customer_data["relationship_manager"]
    },
    "life_event": life_event
}