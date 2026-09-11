from sqlalchemy import text
from sqlalchemy.orm import Session


class TransactionRepository:
    def get_transactions_by_customer_id(self, db: Session, customer_id: str):
        query = text("""
            SELECT
                transaction_id,
                merchant_category,
                transaction_amount,
                transaction_date,
                frequency,
                location,
                description
            FROM transactions
            WHERE customer_id = :customer_id
            ORDER BY transaction_date DESC
        """)

        results = db.execute(
            query,
            {"customer_id": customer_id}
        ).mappings().all()

        return [dict(row) for row in results]