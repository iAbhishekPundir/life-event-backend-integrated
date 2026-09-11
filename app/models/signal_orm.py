"""
SQLAlchemy ORM model for Signal (transaction signal detection).
"""
from sqlalchemy import Column, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SignalORM(BaseModel):
    """
    Signal ORM model - stores detected transaction signals for life event detection.
    """
    __tablename__ = "signals"

    # Primary Key
    signal_id = Column(String(50), primary_key=True, nullable=False)

    # Foreign Key
    event_id = Column(String(50), ForeignKey("life_events.event_id", ondelete="CASCADE"), nullable=False)

    # Signal Information
    signal_name = Column(String(255), nullable=False)
    matched = Column(Boolean, nullable=False, default=False)
    source = Column(String(100), nullable=False, default="Transaction Data")
    
    # Signal Scoring
    confidence_contribution = Column(Float, nullable=False, default=0.0)
    weight = Column(Float, nullable=False, default=0.0)
    
    # Explanation
    reason = Column(Text, nullable=True)
    merchant_category = Column(String(100), nullable=True)
    minimum_amount = Column(Float, nullable=True)

    # Relationships
    life_event = relationship("LifeEventORM", back_populates="signals")

    def __repr__(self):
        return f"<SignalORM(signal_id={self.signal_id}, signal_name={self.signal_name}, matched={self.matched})>"
