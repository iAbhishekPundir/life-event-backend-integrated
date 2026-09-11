"""
CRUD operations for Signal entity.
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.signal_orm import SignalORM


class SignalRepository:
    """Repository pattern for Signal CRUD operations"""

    @staticmethod
    def create(db: Session, signal: SignalORM) -> SignalORM:
        """Create a new signal"""
        db.add(signal)
        db.commit()
        db.refresh(signal)
        return signal

    @staticmethod
    def get_by_id(db: Session, signal_id: str) -> Optional[SignalORM]:
        """Get signal by ID"""
        return db.query(SignalORM).filter(SignalORM.signal_id == signal_id).first()

    @staticmethod
    def get_by_event(db: Session, event_id: str) -> List[SignalORM]:
        """Get all signals for a life event"""
        return db.query(SignalORM).filter(SignalORM.event_id == event_id).all()

    @staticmethod
    def get_matched_signals(db: Session, event_id: str) -> List[SignalORM]:
        """Get all matched signals for a life event"""
        return db.query(SignalORM)\
            .filter(
                SignalORM.event_id == event_id,
                SignalORM.matched == True
            )\
            .all()

    @staticmethod
    def bulk_create(db: Session, signals: List[SignalORM]) -> List[SignalORM]:
        """Create multiple signals at once"""
        db.add_all(signals)
        db.commit()
        for signal in signals:
            db.refresh(signal)
        return signals

    @staticmethod
    def update(db: Session, signal_id: str, **kwargs) -> Optional[SignalORM]:
        """Update signal information"""
        signal = db.query(SignalORM).filter(SignalORM.signal_id == signal_id).first()
        if signal:
            for key, value in kwargs.items():
                if hasattr(signal, key):
                    setattr(signal, key, value)
            db.commit()
            db.refresh(signal)
        return signal

    @staticmethod
    def delete(db: Session, signal_id: str) -> bool:
        """Delete a signal"""
        signal = db.query(SignalORM).filter(SignalORM.signal_id == signal_id).first()
        if signal:
            db.delete(signal)
            db.commit()
            return True
        return False

    @staticmethod
    def delete_by_event(db: Session, event_id: str) -> int:
        """Delete all signals for a life event"""
        count = db.query(SignalORM).filter(SignalORM.event_id == event_id).delete()
        db.commit()
        return count

    @staticmethod
    def count_by_event(db: Session, event_id: str) -> int:
        """Get total number of signals for a life event"""
        return db.query(SignalORM).filter(SignalORM.event_id == event_id).count()
