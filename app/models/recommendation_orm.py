"""
SQLAlchemy ORM model for Recommendation.
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class RecommendationORM(BaseModel):
    """
    Recommendation ORM model - stores personalized product recommendations.
    """
    __tablename__ = "recommendations"

    # Primary Key
    recommendation_id = Column(String(50), primary_key=True, nullable=False)

    # Foreign Keys
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    event_id = Column(String(50), ForeignKey("life_events.event_id", ondelete="CASCADE"), nullable=False)

    # Recommendation Details
    life_event_type = Column(String(100), nullable=False)
    recommendation_name = Column(String(255), nullable=False)
    rationale = Column(Text, nullable=True)
    rank = Column(Integer, nullable=True)

    # Status
    compliance_status = Column(String(50), nullable=False, default="Pending")  # Pending, Approved, Rejected
    approval_status = Column(String(50), nullable=False, default="Pending Human Approval")  # Pending, Approved, Rejected
    customer_facing_allowed = Column(Boolean, nullable=False, default=False)

    # Recommendation Metadata
    product_category = Column(String(100), nullable=True)
    priority = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    customer = relationship("CustomerORM", back_populates="recommendations")
    life_event = relationship("LifeEventORM", back_populates="recommendations")

    def __repr__(self):
        return f"<RecommendationORM(recommendation_id={self.recommendation_id}, recommendation_name={self.recommendation_name})>"
