from sqlalchemy import text
from sqlalchemy.orm import Session


class CustomerRepository:
    def get_all_customers(self, db: Session):
        query = text("""
            SELECT
                c.customer_id,
                c.name,
                c.age,
                c.annual_income,
                c.segment,
                c.relationship_manager,
                c.kyc_status,
                c.nominee_available,
                c.joint_account_eligible,
                c.communication_consent,
                c.portfolio,
                c.risk_profile,
                c.last_review,
                c.source,
                a.account_type,
                a.account_number,
                a.sort_code,
                a.balance,
                a.currency,
                a.source AS account_source
            FROM customers c
            LEFT JOIN customer_accounts a
                ON c.customer_id = a.customer_id
                AND a.is_primary = true
            ORDER BY c.name ASC
        """)

        results = db.execute(query).mappings().all()
        return [dict(row) for row in results]

    def get_customer_by_id(self, db: Session, customer_id: str):
        query = text("""
            SELECT
                c.customer_id,
                c.name,
                c.age,
                c.annual_income,
                c.segment,
                c.relationship_manager,
                c.kyc_status,
                c.nominee_available,
                c.joint_account_eligible,
                c.communication_consent,
                c.portfolio,
                c.risk_profile,
                c.last_review,
                c.source,
                a.account_type,
                a.account_number,
                a.sort_code,
                a.balance,
                a.currency,
                a.source AS account_source
            FROM customers c
            LEFT JOIN customer_accounts a
                ON c.customer_id = a.customer_id
                AND a.is_primary = true
            WHERE c.customer_id = :customer_id
        """)

        result = db.execute(
            query,
            {"customer_id": customer_id}
        ).mappings().first()

        if not result:
            return None

        return dict(result)