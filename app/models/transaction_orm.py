"""
SQLAlchemy ORM model for Transaction.
"""
from sqlalchemy import Column, String, Float, DateTime, Integer, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TransactionORM(BaseModel):
    """
    Transaction ORM model - stores all customer transactions with details.
    """
    __tablename__ = "transactions"

    # Primary Key
    transaction_id = Column(String(50), primary_key=True, nullable=False)

    # Foreign Key
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)

    # Transaction Details
    merchant_category = Column(String(100), nullable=False)
    merchant_name = Column(String(255), nullable=True)
    transaction_amount = Column(Float, nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    transaction_type = Column(String(50), nullable=True)  # Debit, Credit, Transfer
    
    # Additional Information
    frequency = Column(Integer, nullable=False, default=1)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="Completed")  # Completed, Pending, Failed
    
    # Reference Information
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    customer = relationship("CustomerORM", back_populates="transactions")

    def __repr__(self):
        return f"<TransactionORM(transaction_id={self.transaction_id}, customer_id={self.customer_id}, amount={self.transaction_amount})>"
