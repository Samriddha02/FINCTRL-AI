from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import DATABASE_URL, Base, engine as public_engine
from app.evaluation.constants import EVAL_SCHEMA
from app.models import (  # noqa: F401 — register metadata
    BankTransaction,
    Customer,
    Invoice,
    Order,
    Payment,
    Refund,
    Settlement,
    TaxRecord,
)

_eval_engine: Optional[Engine] = None
_EvalSession: Optional[sessionmaker] = None


def ensure_eval_schema() -> None:
    """Create the isolated evaluation schema without touching development tables."""
    with public_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{EVAL_SCHEMA}"'))


def get_eval_engine() -> Engine:
    global _eval_engine, _EvalSession
    if _eval_engine is not None:
        return _eval_engine

    ensure_eval_schema()
    eval_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    @event.listens_for(eval_engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{EVAL_SCHEMA}"')
        cursor.close()

    Base.metadata.create_all(bind=eval_engine)
    _eval_engine = eval_engine
    _EvalSession = sessionmaker(autocommit=False, autoflush=False, bind=eval_engine)
    return eval_engine


def get_eval_session() -> Session:
    get_eval_engine()
    assert _EvalSession is not None
    return _EvalSession()


def truncate_operational_tables(db: Session) -> None:
    db.execute(
        text(
            "TRUNCATE TABLE tax_records, invoices, bank_transactions, settlements, "
            "refunds, payments, orders, customers RESTART IDENTITY CASCADE"
        )
    )
    db.flush()
