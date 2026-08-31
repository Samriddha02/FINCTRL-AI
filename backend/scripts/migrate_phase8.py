"""
Phase 8 Database Migration Script — Human Review, Audit Events, Agent Runs, System Metrics
Run: cd backend && ..\.venv\Scripts\python scripts/migrate_phase8.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base
from app.models.human_review import HumanReview
from app.models.audit_event import AuditEvent
from app.models.agent_run import AgentRun, SystemMetric

# Import existing models so they are available in Base.metadata
from app.models import (
    Customer, Order, Payment, Refund, Settlement,
    BankTransaction, Invoice, TaxRecord
)


def create_phase8_tables():
    """Create all Phase 8 tables that don't already exist."""
    print("Creating Phase 8 database tables...")
    
    # Create only the new Phase 8 tables (won't affect existing tables)
    tables_to_create = [
        HumanReview.__table__,
        AuditEvent.__table__,
        AgentRun.__table__,
        SystemMetric.__table__,
    ]
    
    for table in tables_to_create:
        try:
            table.create(engine, checkfirst=True)
            print(f"  [OK] Table '{table.name}' created or already exists.")
        except Exception as e:
            print(f"  [ERROR] Failed to create table '{table.name}': {e}")
            raise

    print("Phase 8 table migration complete.")


if __name__ == "__main__":
    create_phase8_tables()
