from sqlalchemy import text
from db.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database();"))
        print("Connected successfully to database:", result.scalar())
except Exception as error:
    print("Database connection failed:")
    print(error)