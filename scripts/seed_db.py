"""
Sample data generator for testing the Life Event Backend.
Generates sample customers, transactions, and related data.

Usage:
    python scripts/seed_db.py
"""
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from random import choice, randint, uniform

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.models.customer_orm import CustomerORM
from app.models.transaction_orm import TransactionORM
from app.db.repositories import CustomerRepository, TransactionRepository


# Sample data
SEGMENTS = ["Premium", "Standard", "Basic"]
RISK_PROFILES = ["Conservative", "Balanced", "Aggressive"]
MERCHANT_CATEGORIES = [
    "Jewellery", "Event Booking", "Lifestyle", "Travel", "Hotel",
    "Forex", "Dining", "Gifts", "Property Services", "Salon",
    "Grocery", "Healthcare", "Education", "Entertainment"
]
TRANSACTION_TYPES = ["Debit", "Credit", "Transfer"]


def generate_sample_customer(customer_id: str) -> CustomerORM:
    """Generate a sample customer"""
    names = [
        "Oliver Bennett", "Sarah Johnson", "Michael Chen", "Emma Williams",
        "James Brown", "Lisa Anderson", "David Martinez", "Rachel Taylor"
    ]
    
    return CustomerORM(
        customer_id=customer_id,
        name=choice(names),
        age=randint(25, 65),
        annual_income=uniform(50000, 500000),
        segment=choice(SEGMENTS),
        relationship_manager=f"Manager_{randint(1, 5)}",
        email=f"{customer_id}@example.com",
        phone=f"+1{randint(2000000000, 9999999999)}",
        kyc_status="Verified",
        joint_account_eligible=True,
        communication_consent=True,
        risk_profile=choice(RISK_PROFILES),
        portfolio_value=uniform(50000, 1000000)
    )


def generate_sample_transactions(customer_id: str, count: int = 20) -> list:
    """Generate sample transactions for a customer"""
    transactions = []
    base_date = datetime.utcnow()
    
    for i in range(count):
        transaction_date = base_date - timedelta(days=randint(0, 90))
        
        transaction = TransactionORM(
            transaction_id=f"TXN-{uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            merchant_category=choice(MERCHANT_CATEGORIES),
            merchant_name=f"Merchant_{choice(MERCHANT_CATEGORIES)}_{randint(1, 100)}",
            transaction_amount=uniform(50, 5000),
            transaction_date=transaction_date,
            transaction_type=choice(TRANSACTION_TYPES),
            frequency=randint(1, 5),
            location="London, UK",
            status="Completed"
        )
        transactions.append(transaction)
    
    return transactions


def seed_database():
    """Seed the database with sample data"""
    db = SessionLocal()
    
    try:
        print("Seeding database with sample data...")
        
        # Create sample customers
        num_customers = 5
        print(f"\nCreating {num_customers} sample customers...")
        
        for i in range(num_customers):
            customer_id = f"CUST-{i+1:05d}"
            customer = generate_sample_customer(customer_id)
            
            # Save customer
            saved_customer = CustomerRepository.create(db, customer)
            print(f"  ✓ Created customer: {saved_customer.name} ({customer_id})")
            
            # Create and save transactions
            transactions = generate_sample_transactions(customer_id, count=25)
            saved_transactions = TransactionRepository.bulk_create(db, transactions)
            print(f"    ✓ Created {len(saved_transactions)} transactions")
        
        print(f"\n✓ Database seeded successfully!")
        print(f"  Total customers: {CustomerRepository.count(db)}")
        
        # Print transaction summary
        all_customers = CustomerRepository.get_all(db)
        total_transactions = sum(
            TransactionRepository.count_by_customer(db, customer.customer_id)
            for customer in all_customers
        )
        print(f"  Total transactions: {total_transactions}")
        
    except Exception as e:
        print(f"✗ Error seeding database: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
