"""
Creates and seeds the demo database.

WHY THIS EXISTS
---------------
The handed-over repo's own scripts/init_db.py is broken (`import syss`, plus it
imports app.models.life_event_orm which does not exist), and scripts/seed_db.py
writes a `portfolio_value` column while the application's SQL reads `portfolio`.
So neither will produce a database the app can actually query.

This script creates exactly the schema the app's raw SQL expects -- every column
in app/repositories/customer_repository.py and transaction_repository.py -- and
seeds it with demo data.

The transactions are deliberately engineered against app/rules/life_event_rules.json:
each customer's transactions clear the merchant_category and minimum_amount
thresholds for their intended event, so detection genuinely fires rather than
returning "Unknown". Two customers are seeded with only routine spending so the
"no life event detected" path is demonstrable too.

USAGE
-----
    python setup_demo_db.py            # create schema + seed
    python setup_demo_db.py --reset    # drop existing tables first, then seed

Safe to re-run: without --reset it will skip seeding if data already exists.
"""
import argparse
import sys
from datetime import date, timedelta

from sqlalchemy import text

from app.db.database import SessionLocal, engine


# ---------------------------------------------------------------------------
# Schema -- mirrors exactly what the application's SQL selects
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id             VARCHAR(50) PRIMARY KEY,
    name                    VARCHAR(150) NOT NULL,
    age                     INTEGER,
    annual_income           NUMERIC(14, 2),
    segment                 VARCHAR(50),
    relationship_manager    VARCHAR(100),
    kyc_status              VARCHAR(50),
    nominee_available       BOOLEAN DEFAULT FALSE,
    joint_account_eligible  BOOLEAN DEFAULT TRUE,
    communication_consent   BOOLEAN DEFAULT TRUE,
    portfolio               NUMERIC(16, 2),
    risk_profile            VARCHAR(50),
    last_review             VARCHAR(100),
    source                  VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS customer_accounts (
    id              SERIAL PRIMARY KEY,
    customer_id     VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    account_type    VARCHAR(100),
    account_number  VARCHAR(50),
    sort_code       VARCHAR(20),
    balance         NUMERIC(16, 2),
    currency        VARCHAR(10) DEFAULT 'GBP',
    is_primary      BOOLEAN DEFAULT TRUE,
    source          VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id      VARCHAR(50) PRIMARY KEY,
    customer_id         VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    merchant_category   VARCHAR(100),
    transaction_amount  NUMERIC(14, 2),
    transaction_date    DATE,
    frequency           INTEGER DEFAULT 1,
    location            VARCHAR(100),
    description         TEXT
);

CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_accounts_customer ON customer_accounts(customer_id);
"""

DROP_SQL = """
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS customer_accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
"""


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

CUSTOMERS = [
    # (customer_id, name, age, income, segment, RM, kyc, nominee, joint, consent,
    #  portfolio, risk, last_review, acct_type, acct_no, sort, balance)
    ("CUST001", "Oliver Bennett", 31, 98000, "Premier", "Eric", "Verified", False, True, True,
     562000, "Balanced", "3 months ago", "Premier Current", "****7821", "40-47-84", 28450),
    ("CUST002", "Priya Sharma", 34, 110000, "Premier", "Eric", "Verified", True, True, True,
     708000, "Growth", "5 months ago", "Premier Current", "****4412", "20-15-96", 21300),
    ("CUST003", "Daniel Okafor", 29, 72000, "Core", "Eric", "Verified", False, True, True,
     166000, "Growth", "2 months ago", "Core Current", "****3356", "30-94-74", 14900),
    ("CUST004", "Margaret Coleman", 58, 139000, "Private", "Eric", "Verified", True, True, True,
     2780000, "Conservative", "1 month ago", "Private Current", "****1902", "50-22-11", 99900),
    # No-signal customers -- routine spending only
    ("CUST005", "Thomas Reid", 45, 127000, "Premier", "Eric", "Verified", True, True, True,
     1030000, "Balanced", "6 weeks ago", "Premier Current", "****4421", "60-00-04", 37200),
    ("CUST006", "Aisha Khan", 52, 208000, "Private", "Eric", "Verified", True, True, True,
     3590000, "Conservative", "2 weeks ago", "Private Current", "****8817", "11-55-83", 107200),
]


def d(days_ago: int) -> date:
    return date.today() - timedelta(days=days_ago)


# Transactions engineered against life_event_rules.json thresholds.
# Format: (customer_id, merchant_category, amount, days_ago, frequency, location, description)
# NOTE: `frequency` is an occurrence COUNT (int), matching Transaction.frequency
# in app/models/transaction.py -- not a label like 12.
TRANSACTIONS = [
    # --- CUST001 Oliver -> MARRIAGE (needs conf >= 0.70) -------------------
    # All four Marriage signals cleared: 0.30 + 0.25 + 0.20 + 0.20 = 1.00
    ("CUST001", "Jewellery",     2400.00, 14, 1, "London", "Jewellery purchase - Hatton Garden Jewellers"),
    ("CUST001", "Event Booking", 3500.00, 21, 1, "Surrey", "Wedding venue booking deposit - The Orangery Estate"),
    ("CUST001", "Lifestyle",     1680.00, 12, 1, "London", "Wedding gown - Browns Bride"),
    ("CUST001", "Lifestyle",     1250.00, 30, 1, "London", "Wedding photography - The Wedding Lens"),
    ("CUST001", "Travel",        2850.00, 20, 1, "London", "Honeymoon planning - Turquoise Holidays"),
    ("CUST001", "Travel",        1460.00, 28, 1, "London", "Airline bookings for family - BA & Emirates"),
    ("CUST001", "Groceries",       84.20,  3, 12, "London", "Tesco weekly shop"),
    ("CUST001", "Utilities",      142.00,  8, 12, "London", "British Gas monthly"),

    # --- CUST002 Priya -> TRAVEL (needs conf >= 0.60) ---------------------
    # 0.40 + 0.25 + 0.25 = 0.90
    ("CUST002", "Travel",        3200.00, 10, 1, "London", "Long-haul flight booking - Singapore Airlines"),
    ("CUST002", "Hotel",          980.00, 12, 1, "Singapore", "Hotel reservation - Marina Bay"),
    ("CUST002", "Forex",          650.00,  9, 1, "London", "Foreign currency purchase - SGD"),
    ("CUST002", "Groceries",       96.40,  4, 12, "London", "Sainsbury's weekly shop"),
    ("CUST002", "Utilities",      118.00,  7, 12, "London", "Thames Water monthly"),

    # --- CUST003 Daniel -> HOME PURCHASE (needs conf >= 0.65) -------------
    # 0.30 + 0.25 + 0.25 = 0.80
    ("CUST003", "Property Services", 1200.00, 15, 1, "Manchester", "Estate agent fee - property purchase"),
    ("CUST003", "Loan Services",      999.00, 13, 1, "Manchester", "Mortgage application & arrangement fee"),
    ("CUST003", "Home Furnishing",   2400.00,  8, 1, "Manchester", "Furniture purchase - new home"),
    ("CUST003", "Groceries",           72.10,  2, 12, "Manchester", "Aldi weekly shop"),
    ("CUST003", "Utilities",           95.00,  9, 12, "Manchester", "EDF Energy monthly"),

    # --- CUST004 Margaret -> EDUCATION (needs conf >= 0.60) ---------------
    # 0.35 + 0.25 + 0.25 = 0.85
    ("CUST004", "Education",             8500.00, 18, 1, "Oxford", "University tuition fee payment"),
    ("CUST004", "Exam Fees",              450.00, 22, 1, "Oxford", "Admission and exam fees"),
    ("CUST004", "Student Accommodation", 3200.00, 16, 1, "Oxford", "Student accommodation deposit"),
    ("CUST004", "Groceries",              128.60,  5, 12, "Oxford", "Waitrose weekly shop"),
    ("CUST004", "Utilities",              210.00, 10, 12, "Oxford", "Octopus Energy monthly"),

    # --- CUST005 Thomas -> NO SIGNAL (routine only) -----------------------
    ("CUST005", "Groceries",   110.30,  2, 12, "Leeds", "Morrisons weekly shop"),
    ("CUST005", "Utilities",   135.00,  6, 12, "Leeds", "British Gas monthly"),
    ("CUST005", "Dining",       48.90,  4, 3, "Leeds", "Local restaurant"),
    ("CUST005", "Transport",    62.40,  7, 12, "Leeds", "Rail season ticket top-up"),

    # --- CUST006 Aisha -> NO SIGNAL (routine only) ------------------------
    ("CUST006", "Groceries",   156.80,  3, 12, "London", "Waitrose weekly shop"),
    ("CUST006", "Utilities",   198.00,  8, 12, "London", "Octopus Energy monthly"),
    ("CUST006", "Dining",       72.50,  5, 3, "London", "Restaurant dinner"),
    ("CUST006", "Transport",    89.00,  9, 12, "London", "TfL travel"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and seed the Life Event demo database.")
    parser.add_argument("--reset", action="store_true",
                        help="Drop customers/customer_accounts/transactions before recreating.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Fail early with a clear message if the DB isn't reachable
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            print("ERROR: could not connect to the database.")
            print(f"  {exc}")
            print("\nCheck DATABASE_URL in your .env, and that PostgreSQL is running.")
            return 1

        if args.reset:
            print("Dropping existing tables (--reset)...")
            for statement in DROP_SQL.strip().split(";"):
                if statement.strip():
                    db.execute(text(statement))
            db.commit()

        print("Creating schema...")
        for statement in SCHEMA_SQL.strip().split(";"):
            if statement.strip():
                db.execute(text(statement))
        db.commit()

        existing = db.execute(text("SELECT COUNT(*) FROM customers")).scalar() or 0
        if existing and not args.reset:
            print(f"\nDatabase already has {existing} customers - skipping seed.")
            print("Re-run with --reset to wipe and reseed.")
            return 0

        print(f"Seeding {len(CUSTOMERS)} customers...")
        for c in CUSTOMERS:
            db.execute(text("""
                INSERT INTO customers (
                    customer_id, name, age, annual_income, segment, relationship_manager,
                    kyc_status, nominee_available, joint_account_eligible, communication_consent,
                    portfolio, risk_profile, last_review, source
                ) VALUES (
                    :cid, :name, :age, :income, :segment, :rm,
                    :kyc, :nominee, :joint, :consent,
                    :portfolio, :risk, :review, 'Demo Seed'
                )
                ON CONFLICT (customer_id) DO NOTHING
            """), {
                "cid": c[0], "name": c[1], "age": c[2], "income": c[3], "segment": c[4],
                "rm": c[5], "kyc": c[6], "nominee": c[7], "joint": c[8], "consent": c[9],
                "portfolio": c[10], "risk": c[11], "review": c[12],
            })

            db.execute(text("""
                INSERT INTO customer_accounts (
                    customer_id, account_type, account_number, sort_code,
                    balance, currency, is_primary, source
                ) VALUES (
                    :cid, :atype, :ano, :sort, :balance, 'GBP', true, 'Demo Seed'
                )
            """), {
                "cid": c[0], "atype": c[13], "ano": c[14], "sort": c[15], "balance": c[16],
            })

        print(f"Seeding {len(TRANSACTIONS)} transactions...")
        for index, t in enumerate(TRANSACTIONS, start=1):
            db.execute(text("""
                INSERT INTO transactions (
                    transaction_id, customer_id, merchant_category, transaction_amount,
                    transaction_date, frequency, location, description
                ) VALUES (
                    :tid, :cid, :cat, :amount, :tdate, :freq, :loc, :desc
                )
                ON CONFLICT (transaction_id) DO NOTHING
            """), {
                "tid": f"TXN{index:05d}", "cid": t[0], "cat": t[1], "amount": t[2],
                "tdate": d(t[3]), "freq": t[4], "loc": t[5], "desc": t[6],
            })

        db.commit()

        print("\nDone. Seeded:")
        print("  CUST001  Oliver Bennett     -> Marriage       (all 4 signals)")
        print("  CUST002  Priya Sharma       -> Travel         (all 3 signals)")
        print("  CUST003  Daniel Okafor      -> Home Purchase  (all 3 signals)")
        print("  CUST004  Margaret Coleman   -> Education      (all 3 signals)")
        print("  CUST005  Thomas Reid        -> no event (routine spend only)")
        print("  CUST006  Aisha Khan         -> no event (routine spend only)")
        print("\nTry:")
        print("  curl http://localhost:8000/api/clients")
        print("  curl -X POST http://localhost:8000/api/clients/CUST001/detect")
        return 0

    except Exception as exc:
        db.rollback()
        print(f"\nERROR while seeding: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
