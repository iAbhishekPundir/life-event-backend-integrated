"""
CRUD operations for Customer entity.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.customer_orm import CustomerORM


class CustomerRepository:
    """Repository pattern for Customer CRUD operations"""

    @staticmethod
    def create(db: Session, customer: CustomerORM) -> CustomerORM:
        """Create a new customer"""
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def get_by_id(db: Session, customer_id: str) -> Optional[CustomerORM]:
        """Get customer by ID"""
        return db.query(CustomerORM).filter(CustomerORM.customer_id == customer_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[CustomerORM]:
        """Get customer by email"""
        return db.query(CustomerORM).filter(CustomerORM.email == email).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[CustomerORM]:
        """Get all customers with pagination"""
        return db.query(CustomerORM).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_segment(db: Session, segment: str) -> List[CustomerORM]:
        """Get all customers in a specific segment"""
        return db.query(CustomerORM).filter(CustomerORM.segment == segment).all()

    @staticmethod
    def get_by_kyc_status(db: Session, kyc_status: str) -> List[CustomerORM]:
        """Get customers by KYC status"""
        return db.query(CustomerORM).filter(CustomerORM.kyc_status == kyc_status).all()

    @staticmethod
    def update(db: Session, customer_id: str, **kwargs) -> Optional[CustomerORM]:
        """Update customer information"""
        customer = db.query(CustomerORM).filter(CustomerORM.customer_id == customer_id).first()
        if customer:
            for key, value in kwargs.items():
                if hasattr(customer, key):
                    setattr(customer, key, value)
            db.commit()
            db.refresh(customer)
        return customer

    @staticmethod
    def delete(db: Session, customer_id: str) -> bool:
        """Delete a customer"""
        customer = db.query(CustomerORM).filter(CustomerORM.customer_id == customer_id).first()
        if customer:
            db.delete(customer)
            db.commit()
            return True
        return False

    @staticmethod
    def exists(db: Session, customer_id: str) -> bool:
        """Check if customer exists"""
        return db.query(CustomerORM).filter(CustomerORM.customer_id == customer_id).first() is not None

    @staticmethod
    def count(db: Session) -> int:
        """Get total number of customers"""
        return db.query(CustomerORM).count()
