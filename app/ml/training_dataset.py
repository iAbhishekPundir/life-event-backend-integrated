import pandas as pd
from sqlalchemy import text

from app.db.database import engine


class TrainingDatasetBuilder:
    """
    Builds ML training data from PostgreSQL.

    Source tables:
    - customers
    - transactions
    - ml_life_event_labels

    Output:
    One ML-ready row per customer and life_event_type.
    """

    def load_training_dataframe(self) -> pd.DataFrame:
        query = text("""
            SELECT
                c.customer_id,
                l.life_event_type,
                c.age AS customer_age,
                COALESCE(c.annual_income, 0) AS annual_income,
                c.segment,
                c.risk_profile,

                CASE
                    WHEN c.risk_profile = 'Low' THEN 1
                    WHEN c.risk_profile = 'Medium' THEN 2
                    WHEN c.risk_profile = 'Medium High' THEN 3
                    WHEN c.risk_profile = 'High' THEN 4
                    ELSE 0
                END AS risk_profile_encoded,

                COUNT(t.transaction_id) AS transaction_count,
                COUNT(DISTINCT t.merchant_category) AS merchant_category_count,
                COALESCE(SUM(t.transaction_amount), 0) AS total_transaction_amount,

                COALESCE(SUM(CASE WHEN t.merchant_category = 'Jewellery' THEN t.transaction_amount ELSE 0 END), 0) AS jewellery_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Event Booking' THEN t.transaction_amount ELSE 0 END), 0) AS event_booking_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Travel' THEN t.transaction_amount ELSE 0 END), 0) AS travel_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Lifestyle' THEN t.transaction_amount ELSE 0 END), 0) AS lifestyle_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Hotel' THEN t.transaction_amount ELSE 0 END), 0) AS hotel_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Forex' THEN t.transaction_amount ELSE 0 END), 0) AS forex_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Property Services' THEN t.transaction_amount ELSE 0 END), 0) AS property_services_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Loan Services' THEN t.transaction_amount ELSE 0 END), 0) AS loan_services_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Home Furnishing' THEN t.transaction_amount ELSE 0 END), 0) AS home_furnishing_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Dining' THEN t.transaction_amount ELSE 0 END), 0) AS dining_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Gifts' THEN t.transaction_amount ELSE 0 END), 0) AS gift_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Education' THEN t.transaction_amount ELSE 0 END), 0) AS education_spend_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Exam Fees' THEN t.transaction_amount ELSE 0 END), 0) AS exam_fees_total,
                COALESCE(SUM(CASE WHEN t.merchant_category = 'Student Accommodation' THEN t.transaction_amount ELSE 0 END), 0) AS student_accommodation_total,

                CASE
                    WHEN l.confirmed_event = true THEN 1
                    ELSE 0
                END AS label

            FROM customers c
            JOIN ml_life_event_labels l
                ON c.customer_id = l.customer_id
            LEFT JOIN transactions t
                ON c.customer_id = t.customer_id

            GROUP BY
                c.customer_id,
                l.life_event_type,
                c.age,
                c.annual_income,
                c.segment,
                c.risk_profile,
                l.confirmed_event

            ORDER BY c.customer_id
        """)

        with engine.connect() as connection:
            dataframe = pd.read_sql_query(query, connection)

        dataframe = dataframe.fillna(0)

        return dataframe


training_dataset_builder = TrainingDatasetBuilder()


if __name__ == "__main__":
    df = training_dataset_builder.load_training_dataframe()
    print(df)