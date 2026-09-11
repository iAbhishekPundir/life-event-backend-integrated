"""
SQLAlchemy ORM model for Customer with all personal information.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CustomerORM(BaseModel):
    """
    Customer ORM model - stores personal information, KYC status, and preferences.
    """
    __tablename__ = "customers"

    # Primary Key
    customer_id = Column(String(50), primary_key=True, nullable=False)

    # Basic Information
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    annual_income = Column(Float, nullable=True)
    segment = Column(String(50), nullable=True)
    relationship_manager = Column(String(255), nullable=True)

    # Contact Information
    email = Column(String(255), nullable=True, unique=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)

    # KYC & Compliance
    kyc_status = Column(String(50), nullable=False, default="Pending")  # Verified, Pending, Failed
    
    # Nominee Information
    nominee_name = Column(String(255), nullable=True)
    nominee_relationship = Column(String(50), nullable=True)

    # Account Preferences & Consent
    joint_account_eligible = Column(Boolean, nullable=False, default=True)
    communication_consent = Column(Boolean, nullable=False, default=True)
    risk_profile = Column(String(50), nullable=True)  # Balanced, Conservative, Aggressive

    # Portfolio Information
    portfolio_value = Column(Float, nullable=True)

    # Relationships
    transactions = relationship(
        "TransactionORM",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select"
    )
    life_events = relationship(
        "LifeEventORM",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select"
    )
    recommendations = relationship(
        "RecommendationORM",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<CustomerORM(customer_id={self.customer_id}, name={self.name})>"
