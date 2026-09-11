"""
CRUD operations for LifeEvent entity.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.life_event_orm import LifeEventORM


class LifeEventRepository:
    """Repository pattern for LifeEvent CRUD operations"""

    @staticmethod
    def create(db: Session, life_event: LifeEventORM) -> LifeEventORM:
        """Create a new life event"""
        db.add(life_event)
        db.commit()
        db.refresh(life_event)
        return life_event

    @staticmethod
    def get_by_id(db: Session, event_id: str) -> Optional[LifeEventORM]:
        """Get life event by ID"""
        return db.query(LifeEventORM).filter(LifeEventORM.event_id == event_id).first()

    @staticmethod
    def get_by_customer(db: Session, customer_id: str, skip: int = 0, limit: int = 100) -> List[LifeEventORM]:
        """Get all life events for a customer"""
        return db.query(LifeEventORM)\
            .filter(LifeEventORM.customer_id == customer_id)\
            .order_by(desc(LifeEventORM.detected_at))\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_by_customer_and_type(
        db: Session,
        customer_id: str,
        life_event_type: str
    ) -> List[LifeEventORM]:
        """Get life events for a customer by event type"""
        return db.query(LifeEventORM)\
            .filter(
                and_(
                    LifeEventORM.customer_id == customer_id,
                    LifeEventORM.life_event_type == life_event_type
                )
            )\
            .order_by(desc(LifeEventORM.detected_at))\
            .all()

    @staticmethod
    def get_actionable_events(db: Session, skip: int = 0, limit: int = 100) -> List[LifeEventORM]:
        """Get all actionable life events"""
        return db.query(LifeEventORM)\
            .filter(LifeEventORM.actionable == True)\
            .order_by(desc(LifeEventORM.confidence_score))\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_high_confidence_events(
        db: Session,
        min_confidence: float = 0.7,
        skip: int = 0,
        limit: int = 100
    ) -> List[LifeEventORM]:
        """Get life events above a confidence threshold"""
        return db.query(LifeEventORM)\
            .filter(LifeEventORM.confidence_score >= min_confidence)\
            .order_by(desc(LifeEventORM.confidence_score))\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def update(db: Session, event_id: str, **kwargs) -> Optional[LifeEventORM]:
        """Update life event information"""
        life_event = db.query(LifeEventORM).filter(LifeEventORM.event_id == event_id).first()
        if life_event:
            for key, value in kwargs.items():
                if hasattr(life_event, key):
                    setattr(life_event, key, value)
            db.commit()
            db.refresh(life_event)
        return life_event

    @staticmethod
    def delete(db: Session, event_id: str) -> bool:
        """Delete a life event"""
        life_event = db.query(LifeEventORM).filter(LifeEventORM.event_id == event_id).first()
        if life_event:
            db.delete(life_event)
            db.commit()
            return True
        return False

    @staticmethod
    def count_by_customer(db: Session, customer_id: str) -> int:
        """Get total number of life events for a customer"""
        return db.query(LifeEventORM).filter(LifeEventORM.customer_id == customer_id).count()

    @staticmethod
    def count_actionable(db: Session) -> int:
        """Get total number of actionable life events"""
        return db.query(LifeEventORM).filter(LifeEventORM.actionable == True).count()
