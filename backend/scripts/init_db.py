import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine, Base
import app.models  # Ensures all models are registered with Base.metadata


def init_database():
    """Initializes PostgreSQL database tables for FINCTRL AI."""
    print("Connecting to PostgreSQL database...")
    try:
        with engine.connect() as conn:
            print("Successfully connected to PostgreSQL database.")
    except Exception as e:
        print(f"ERROR: Failed to connect to PostgreSQL database: {e}")
        sys.exit(1)

    print("Creating database tables if they do not exist...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Successfully initialized all 8 operational database tables:")
        for table in Base.metadata.tables.keys():
            print(f"  - {table}")
    except Exception as e:
        print(f"ERROR: Failed to create database tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
