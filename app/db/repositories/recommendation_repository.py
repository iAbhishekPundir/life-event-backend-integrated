"""
CRUD operations for Recommendation entity.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.recommendation_orm import RecommendationORM


class RecommendationRepository:
    """Repository pattern for Recommendation CRUD operations"""

    @staticmethod
    def create(db: Session, recommendation: RecommendationORM) -> RecommendationORM:
        """Create a new recommendation"""
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation

    @staticmethod
    def get_by_id(db: Session, recommendation_id: str) -> Optional[RecommendationORM]:
        """Get recommendation by ID"""
        return db.query(RecommendationORM).filter(RecommendationORM.recommendation_id == recommendation_id).first()

    @staticmethod
    def get_by_customer(db: Session, customer_id: str, skip: int = 0, limit: int = 100) -> List[RecommendationORM]:
        """Get all recommendations for a customer"""
        return db.query(RecommendationORM)\
            .filter(RecommendationORM.customer_id == customer_id)\
            .order_by(RecommendationORM.rank)\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_by_event(db: Session, event_id: str) -> List[RecommendationORM]:
        """Get all recommendations for a life event"""
        return db.query(RecommendationORM)\
            .filter(RecommendationORM.event_id == event_id)\
            .order_by(RecommendationORM.rank)\
            .all()

    @staticmethod
    def get_by_customer_and_event(db: Session, customer_id: str, event_id: str) -> List[RecommendationORM]:
        """Get recommendations for a specific customer event"""
        return db.query(RecommendationORM)\
            .filter(
                and_(
                    RecommendationORM.customer_id == customer_id,
                    RecommendationORM.event_id == event_id
                )
            )\
            .order_by(RecommendationORM.rank)\
            .all()

    @staticmethod
    def get_approved_recommendations(
        db: Session,
        customer_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[RecommendationORM]:
        """Get approved recommendations for a customer"""
        return db.query(RecommendationORM)\
            .filter(
                and_(
                    RecommendationORM.customer_id == customer_id,
                    RecommendationORM.approval_status == "Approved",
                    RecommendationORM.customer_facing_allowed == True
                )
            )\
            .order_by(RecommendationORM.rank)\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_pending_approvals(db: Session, skip: int = 0, limit: int = 100) -> List[RecommendationORM]:
        """Get recommendations pending approval"""
        return db.query(RecommendationORM)\
            .filter(RecommendationORM.approval_status == "Pending Human Approval")\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def update(db: Session, recommendation_id: str, **kwargs) -> Optional[RecommendationORM]:
        """Update recommendation information"""
        recommendation = db.query(RecommendationORM).filter(
            RecommendationORM.recommendation_id == recommendation_id
        ).first()
        if recommendation:
            for key, value in kwargs.items():
                if hasattr(recommendation, key):
                    setattr(recommendation, key, value)
            db.commit()
            db.refresh(recommendation)
        return recommendation

    @staticmethod
    def delete(db: Session, recommendation_id: str) -> bool:
        """Delete a recommendation"""
        recommendation = db.query(RecommendationORM).filter(
            RecommendationORM.recommendation_id == recommendation_id
        ).first()
        if recommendation:
            db.delete(recommendation)
            db.commit()
            return True
        return False

    @staticmethod
    def bulk_create(db: Session, recommendations: List[RecommendationORM]) -> List[RecommendationORM]:
        """Create multiple recommendations at once"""
        db.add_all(recommendations)
        db.commit()
        for recommendation in recommendations:
            db.refresh(recommendation)
        return recommendations

    @staticmethod
    def count_by_customer(db: Session, customer_id: str) -> int:
        """Get total number of recommendations for a customer"""
        return db.query(RecommendationORM).filter(RecommendationORM.customer_id == customer_id).count()

    @staticmethod
    def count_pending_approvals(db: Session) -> int:
        """Get total number of recommendations pending approval"""
        return db.query(RecommendationORM).filter(
            RecommendationORM.approval_status == "Pending Human Approval"
        ).count()
