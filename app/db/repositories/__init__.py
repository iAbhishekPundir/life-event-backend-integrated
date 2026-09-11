"""
Repository initialization module.

NOTE: LifeEventRepository / SignalRepository / RecommendationRepository
depend on ORM models (life_event_orm, etc.) that do not exist in this
codebase yet, so their imports are guarded. Without the guard, importing
this package raises ModuleNotFoundError and takes down anything that
touches it (scripts/seed_db.py, for one).

These are unused by the running application - the API layer uses the raw-SQL
repositories in app/repositories/ instead. Once the missing ORM models are
added, the guards can be removed.
"""
from app.db.repositories.customer_repository import CustomerRepository
from app.db.repositories.transaction_repository import TransactionRepository

__all__ = ["CustomerRepository", "TransactionRepository"]

try:
    from app.db.repositories.life_event_repository import LifeEventRepository  # noqa: F401
    __all__.append("LifeEventRepository")
except Exception:
    LifeEventRepository = None  # type: ignore

try:
    from app.db.repositories.signal_repository import SignalRepository  # noqa: F401
    __all__.append("SignalRepository")
except Exception:
    SignalRepository = None  # type: ignore

try:
    from app.db.repositories.recommendation_repository import RecommendationRepository  # noqa: F401
    __all__.append("RecommendationRepository")
except Exception:
    RecommendationRepository = None  # type: ignore
