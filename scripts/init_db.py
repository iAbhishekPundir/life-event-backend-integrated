"""
Database initialization and migration script.
Run this script to create all tables in PostgreSQL.

Usage:
    python scripts/init_db.py --create    # Create all tables
    python scripts/init_db.py --drop      # Drop all tables (use with caution!)
    python scripts/init_db.py --reset     # Drop and recreate all tables
"""
import os
import syss
import argparse
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import init_db, drop_db, engine, Base
from app.models.base import Base as BaseModel
from app.models.customer_orm import CustomerORM
from app.models.transaction_orm import TransactionORM
from app.models.life_event_orm import LifeEventORM
from app.models.signal_orm import SignalORM
from app.models.recommendation_orm import RecommendationORM


def create_all_tables():
    """Create all tables in the database"""
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully!")
        print("\nTables created:")
        print("  - customers")
        print("  - transactions")
        print("  - life_events")
        print("  - signals")
        print("  - recommendations")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)


def drop_all_tables():
    """Drop all tables from the database"""
    confirm = input("⚠️  This will delete all data! Are you sure? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return

    print("Dropping database tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped successfully!")
    except Exception as e:
        print(f"✗ Error dropping tables: {e}")
        sys.exit(1)


def reset_db():
    """Drop and recreate all tables"""
    print("Resetting database...")
    drop_all_tables()
    print()
    create_all_tables()


def verify_connection():
    """Verify database connection"""
    try:
        with engine.connect() as connection:
            print("✓ Successfully connected to PostgreSQL!")
            result = connection.execute(connection.exec_driver_sql("SELECT version()"))
            version = result.fetchone()
            print(f"  PostgreSQL Version: {version[0]}")
            return True
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Database initialization script for Life Event Backend"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create all database tables"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all database tables (CAUTION: Data loss!)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify database connection"
    )

    args = parser.parse_args()

    if not args.create and not args.drop and not args.reset and not args.verify:
        parser.print_help()
        sys.exit(0)

    if args.verify:
        verify_connection()
        return

    if args.create:
        verify_connection()
        print()
        create_all_tables()

    if args.drop:
        verify_connection()
        print()
        drop_all_tables()

    if args.reset:
        verify_connection()
        print()
        reset_db()


if __name__ == "__main__":
    main()
