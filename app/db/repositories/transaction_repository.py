"""
CRUD operations for Transaction entity.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.transaction_orm import TransactionORM


class TransactionRepository:
    """Repository pattern for Transaction CRUD operations"""

    @staticmethod
    def create(db: Session, transaction: TransactionORM) -> TransactionORM:
        """Create a new transaction"""
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def get_by_id(db: Session, transaction_id: str) -> Optional[TransactionORM]:
        """Get transaction by ID"""
        return db.query(TransactionORM).filter(TransactionORM.transaction_id == transaction_id).first()

    @staticmethod
    def get_by_customer(db: Session, customer_id: str, skip: int = 0, limit: int = 100) -> List[TransactionORM]:
        """Get all transactions for a customer"""
        return db.query(TransactionORM)\
            .filter(TransactionORM.customer_id == customer_id)\
            .order_by(desc(TransactionORM.transaction_date))\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_by_customer_and_date_range(
        db: Session, 
        customer_id: str, 
        start_date: datetime,
        end_date: datetime
    ) -> List[TransactionORM]:
        """Get transactions for a customer within a date range"""
        return db.query(TransactionORM)\
            .filter(
                and_(
                    TransactionORM.customer_id == customer_id,
                    TransactionORM.transaction_date >= start_date,
                    TransactionORM.transaction_date <= end_date
                )
            )\
            .order_by(desc(TransactionORM.transaction_date))\
            .all()

    @staticmethod
    def get_by_customer_and_category(
        db: Session,
        customer_id: str,
        merchant_category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TransactionORM]:
        """Get transactions for a customer by merchant category"""
        return db.query(TransactionORM)\
            .filter(
                and_(
                    TransactionORM.customer_id == customer_id,
                    TransactionORM.merchant_category == merchant_category
                )
            )\
            .order_by(desc(TransactionORM.transaction_date))\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_recent_transactions(
        db: Session, 
        customer_id: str, 
        days: int = 30
    ) -> List[TransactionORM]:
        """Get recent transactions (last N days)"""
        since_date = datetime.utcnow() - timedelta(days=days)
        return db.query(TransactionORM)\
            .filter(
                and_(
                    TransactionORM.customer_id == customer_id,
                    TransactionORM.transaction_date >= since_date
                )
            )\
            .order_by(desc(TransactionORM.transaction_date))\
            .all()

    @staticmethod
    def update(db: Session, transaction_id: str, **kwargs) -> Optional[TransactionORM]:
        """Update transaction information"""
        transaction = db.query(TransactionORM).filter(TransactionORM.transaction_id == transaction_id).first()
        if transaction:
            for key, value in kwargs.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)
            db.commit()
            db.refresh(transaction)
        return transaction

    @staticmethod
    def delete(db: Session, transaction_id: str) -> bool:
        """Delete a transaction"""
        transaction = db.query(TransactionORM).filter(TransactionORM.transaction_id == transaction_id).first()
        if transaction:
            db.delete(transaction)
            db.commit()
            return True
        return False

    @staticmethod
    def bulk_create(db: Session, transactions: List[TransactionORM]) -> List[TransactionORM]:
        """Create multiple transactions at once"""
        db.add_all(transactions)
        db.commit()
        for transaction in transactions:
            db.refresh(transaction)
        return transactions

    @staticmethod
    def count_by_customer(db: Session, customer_id: str) -> int:
        """Get total number of transactions for a customer"""
        return db.query(TransactionORM).filter(TransactionORM.customer_id == customer_id).count()
