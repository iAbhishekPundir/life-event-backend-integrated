from fastapi import APIRouter, Depends
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


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    customers = customer_repository.get_all_customers(db)

    client_cards = []
    actionable_events = 0
    clients_with_detected_events = 0

    for customer_data in customers:
        transaction_rows = transaction_repository.get_transactions_by_customer_id(
            db=db,
            customer_id=customer_data["customer_id"]
        )

        if not transaction_rows:
            client_cards.append({
                "customer_id": customer_data["customer_id"],
                "name": customer_data["name"],
                "age": customer_data["age"],
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
                "relationship_manager": customer_data["relationship_manager"],
                "python -m uvicorn app.main:app --reload": None,
                "confidence_score": 0,
                "status": "No Transactions",
                "key_drivers": [],
                "next_best_action": "Upload or sync transaction data"
            })
            continue

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

        if life_event.life_event_type != "Unknown":
            clients_with_detected_events += 1

        if life_event.actionable:
            actionable_events += 1

        client_cards.append({
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
            "relationship_manager": customer_data["relationship_manager"],
            "detected_life_event": life_event.life_event_type,
            "confidence_score": life_event.confidence_score,
            "score_source": life_event.score_source,
            "estimated_timeline": life_event.estimated_timeline,
            "status": life_event.status,
            "actionable": life_event.actionable,
            "key_drivers": life_event.key_drivers,
            "next_best_action": (
                "Proceed to Personalised Recommendation"
                if life_event.actionable
                else "Monitor additional signals"
            )
        })

    return {
        "dashboard_summary": {
            "total_clients": len(customers),
            "clients_with_detected_events": clients_with_detected_events,
            "actionable_events": actionable_events
        },
        "clients": client_cards,
        "active_steps": [
            "Event Detection",
            "Personalised Recommendation",
            "Advisor Insights",
            "Client Sentiment",
            "Workflow Orchestration"
        ]
    }