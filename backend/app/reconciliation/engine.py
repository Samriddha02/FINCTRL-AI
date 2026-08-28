import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Order, Payment
from app.services.database_service import get_payment, get_payment_context
from app.reconciliation.models import (
    ReconciliationStatus,
    ReasonCode,
    ReconciliationResult,
)
from app.reconciliation.rules import evaluate_reconciliation_case

logger = logging.getLogger("reconciliation_engine")


def derive_case_id_from_order(order_id: str) -> str:
    """Derives case_id deterministically from order_id (e.g. ORD-00001 -> CASE-00001)."""
    if not order_id:
        return "CASE-UNKNOWN"
    if order_id.startswith("ORD-"):
        return order_id.replace("ORD-", "CASE-")
    return order_id


def reconcile_payment(db: Session, payment_id: str) -> ReconciliationResult:
    """Reconciles a single payment by payment_id using operational database records."""
    payment = get_payment(db, payment_id)
    if not payment:
        logger.warning(f"Reconciliation requested for unknown payment_id: {payment_id}")
        return ReconciliationResult(
            case_id=payment_id,
            status=ReconciliationStatus.ERROR,
            reason_code=ReasonCode.NONE,
            expected_amount=0.0,
            actual_amount=0.0,
            difference=0.0,
            confidence=0.0,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=[],
            rule_evaluations=[],
        )

    # Resolve case_id deterministically from order_id
    case_id = derive_case_id_from_order(payment.order_id)

    ctx = get_payment_context(db, payment_id)
    result = evaluate_reconciliation_case(ctx, case_id)
    logger.info(
        f"Reconciled case_id={result.case_id} | status={result.status.value} | "
        f"reason_code={result.reason_code.value} | diff={result.difference:.2f}"
    )
    return result


def reconcile_case(db: Session, case_id: str) -> ReconciliationResult:
    """Reconciles a single financial case by case_id using operational database records."""
    order_id = case_id.replace("CASE-", "ORD-") if case_id.startswith("CASE-") else case_id
    order = db.query(Order).filter(Order.order_id == order_id).first()
    payment = None
    if order:
        payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()

    if not payment:
        payment_id = case_id.replace("CASE-", "PAY-") if case_id.startswith("CASE-") else case_id
        payment = get_payment(db, payment_id)

    if not payment:
        logger.warning(f"Reconciliation requested for unknown case_id: {case_id}")
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.ERROR,
            reason_code=ReasonCode.NONE,
            expected_amount=0.0,
            actual_amount=0.0,
            difference=0.0,
            confidence=0.0,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=[],
            rule_evaluations=[],
        )

    return reconcile_payment(db, payment.payment_id)


def reconcile_all_cases(db: Session) -> List[ReconciliationResult]:
    """Batch reconciles all available financial cases discovered from operational database records.

    NOTE: Does NOT load ground truth files. Discovers cases entirely from operational DB tables.
    """
    logger.info("Starting batch reconciliation over all operational cases...")

    orders = db.query(Order).order_by(Order.order_id).all()
    results: List[ReconciliationResult] = []

    for order in orders:
        payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()
        if payment:
            res = reconcile_payment(db, payment.payment_id)
            results.append(res)

    logger.info(f"Completed batch reconciliation for {len(results)} operational cases.")
    return results
