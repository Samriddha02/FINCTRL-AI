from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from app.reconciliation.constants import (
    round_currency,
    amounts_equal,
    amount_diff,
    EXPECTED_FEE_RATE,
    DEFAULT_TAX_RATE,
    TIMING_TOLERANCE_DAYS,
)
from app.reconciliation.models import (
    ReconciliationStatus,
    ReasonCode,
    ReconciliationResult,
)
from app.reconciliation.calculators import (
    calculate_expected_fee_and_tax,
    calculate_total_refund_amount,
    calculate_expected_settlement_net,
    calculate_invoice_breakdown,
)
from app.reconciliation.matchers import (
    match_bank_transactions_for_settlement,
    check_posting_delay,
)
from app.reconciliation.evidence import EvidenceCollector


def evaluate_reconciliation_case(ctx: Dict[str, Any], case_id: str) -> ReconciliationResult:
    """Evaluates deterministic financial rules against operational records for a case

    following explicit rule priority hierarchy.
    """
    collector = EvidenceCollector()

    customer = ctx.get("customer")
    order = ctx.get("order")
    payment = ctx.get("payment")
    refunds = ctx.get("refunds") or []
    settlement = ctx.get("settlement")
    bank_txns = ctx.get("bank_transactions") or []
    invoice = ctx.get("invoice")
    tax_record = ctx.get("tax_record")

    # Handle Missing Payment / Order Context
    if not payment:
        collector.add_evidence("payments", case_id, "payment_id", "None", "No payment record found for case")
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.MISSING,
            reason_code=ReasonCode.MISSING_SETTLEMENT,
            expected_amount=Decimal("0.00"),
            actual_amount=Decimal("0.00"),
            difference=Decimal("0.00"),
            confidence=0.50,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    payment_amt = payment.amount
    collector.add_evidence("payments", payment.payment_id, "amount", payment_amt, "Captured payment amount")

    total_refund_amt = calculate_total_refund_amount(refunds)
    if refunds:
        for r in refunds:
            collector.add_evidence("refunds", r.refund_id, "refund_amount", r.refund_amount, f"Refund: {r.refund_reason}")

    # =========================================================================
    # RULE 1: CONFLICTING_RECORDS
    # =========================================================================
    if order and getattr(order, "order_status", "") == "CANCELLED" and getattr(payment, "payment_status", "") == "SUCCESS":
        if total_refund_amt < payment_amt:
            collector.add_evidence("orders", order.order_id, "order_status", order.order_status, "Order is CANCELLED")
            collector.add_evidence("payments", payment.payment_id, "payment_status", payment.payment_status, "Payment succeeded without full refund")
            collector.add_rule_evaluation("CHECK_ORDER_PAYMENT_STATUS", "FAIL", "0.00", payment_amt, payment_amt)
            return ReconciliationResult(
                case_id=case_id,
                status=ReconciliationStatus.MISMATCH,
                reason_code=ReasonCode.CONFLICTING_RECORDS,
                expected_amount=Decimal("0.00"),
                actual_amount=payment_amt,
                difference=payment_amt,
                confidence=0.95,
                needs_investigation=True,
                auto_resolvable=False,
                evidence=collector.evidence,
                rule_evaluations=collector.rule_evaluations,
            )

    if total_refund_amt > payment_amt:
        collector.add_evidence("refunds", "ALL_REFUNDS", "total_refund", total_refund_amt, "Total refund exceeds payment amount")
        collector.add_rule_evaluation("CHECK_REFUND_SANITY", "FAIL", payment_amt, total_refund_amt, total_refund_amt - payment_amt)
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.MISMATCH,
            reason_code=ReasonCode.CONFLICTING_RECORDS,
            expected_amount=payment_amt,
            actual_amount=total_refund_amt,
            difference=total_refund_amt - payment_amt,
            confidence=0.95,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    # =========================================================================
    # RULE 2: MISSING_SETTLEMENT
    # =========================================================================
    if not settlement:
        collector.add_evidence("settlements", case_id, "settlement_id", "None", "Payment captured but settlement record is missing")
        collector.add_rule_evaluation("CHECK_SETTLEMENT_EXISTENCE", "FAIL", payment_amt, Decimal("0.00"), -payment_amt)
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.MISSING,
            reason_code=ReasonCode.MISSING_SETTLEMENT,
            expected_amount=payment_amt,
            actual_amount=Decimal("0.00"),
            difference=-payment_amt,
            confidence=0.95,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    collector.add_evidence("settlements", settlement.settlement_id, "gross_amount", settlement.gross_amount, "Settlement gross amount")
    collector.add_evidence("settlements", settlement.settlement_id, "fee_amount", settlement.fee_amount, "Gateway fee charged")
    collector.add_evidence("settlements", settlement.settlement_id, "tax_amount", settlement.tax_amount, "Gateway tax on fee")
    collector.add_evidence("settlements", settlement.settlement_id, "net_amount", settlement.net_amount, "Actual net settlement payout")

    matched_btxns = match_bank_transactions_for_settlement(settlement.settlement_id, bank_txns)

    # =========================================================================
    # RULE 3: DUPLICATE_TRANSACTION
    # =========================================================================
    if len(matched_btxns) > 1:
        dup_total = sum(b.amount for b in matched_btxns)
        for b in matched_btxns:
            collector.add_evidence("bank_transactions", b.bank_txn_id, "amount", b.amount, f"Duplicate bank entry: {b.description}")
        collector.add_rule_evaluation("CHECK_DUPLICATE_BANK_TRANSACTIONS", "FAIL", settlement.net_amount, dup_total, dup_total - settlement.net_amount)
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.DUPLICATE,
            reason_code=ReasonCode.DUPLICATE_TRANSACTION,
            expected_amount=settlement.net_amount,
            actual_amount=dup_total,
            difference=dup_total - settlement.net_amount,
            confidence=0.95,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    # =========================================================================
    # RULE 4: AMBIGUOUS_CASE
    # =========================================================================
    # Check if bank transaction has vague reference ID or bulk transfer reference
    vague_btxn = False
    for b in bank_txns:
        ref_id = getattr(b, "reference_id", "") or ""
        if "BULK" in ref_id or "BATCH" in ref_id or ref_id != settlement.settlement_id:
            vague_btxn = True
            collector.add_evidence("bank_transactions", b.bank_txn_id, "reference_id", ref_id, "Vague or non-matching bank reference ID")

    if vague_btxn and not matched_btxns:
        collector.add_rule_evaluation("CHECK_BANK_REFERENCE_MATCH", "FAIL", settlement.settlement_id, "VAGUE_REF", Decimal("0.00"))
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.AMBIGUOUS,
            reason_code=ReasonCode.AMBIGUOUS_CASE,
            expected_amount=settlement.net_amount,
            actual_amount=settlement.net_amount,
            difference=Decimal("0.00"),
            confidence=0.70,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    # Calculate expected settlement fee and tax based on contracted 2.0% rate
    expected_fee, expected_fee_tax = calculate_expected_fee_and_tax(payment_amt, EXPECTED_FEE_RATE, DEFAULT_TAX_RATE)
    expected_net_clean = calculate_expected_settlement_net(payment_amt, expected_fee, expected_fee_tax, total_refund_amt, Decimal("0.00"))

    # =========================================================================
    # RULE 5: AMOUNT_MISMATCH (Gross level comparison)
    # =========================================================================
    if not amounts_equal(settlement.gross_amount, payment_amt):
        collector.add_rule_evaluation("CHECK_SETTLEMENT_GROSS_AMOUNT", "FAIL", payment_amt, settlement.gross_amount, amount_diff(settlement.gross_amount, payment_amt))
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.MISMATCH,
            reason_code=ReasonCode.AMOUNT_MISMATCH,
            expected_amount=expected_net_clean,
            actual_amount=settlement.net_amount,
            difference=amount_diff(settlement.net_amount, expected_net_clean),
            confidence=0.95,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    # =========================================================================
    # RULE 6: PARTIAL_REFUND
    # =========================================================================
    if total_refund_amt > Decimal("0.00") and refunds:
        if amounts_equal(settlement.net_amount, expected_net_clean):
            collector.add_rule_evaluation("CHECK_PARTIAL_REFUND_NET", "PASS", expected_net_clean, settlement.net_amount, Decimal("0.00"))
            return ReconciliationResult(
                case_id=case_id,
                status=ReconciliationStatus.MATCHED,
                reason_code=ReasonCode.PARTIAL_REFUND,
                expected_amount=expected_net_clean,
                actual_amount=settlement.net_amount,
                difference=Decimal("0.00"),
                confidence=1.00,
                needs_investigation=False,
                auto_resolvable=True,
                evidence=collector.evidence,
                rule_evaluations=collector.rule_evaluations,
            )

    # =========================================================================
    # RULE 7: FEE_DIFFERENCE
    # =========================================================================
    if not amounts_equal(settlement.fee_amount, expected_fee):
        fee_diff = amount_diff(settlement.fee_amount, expected_fee)
        actual_net = settlement.net_amount
        collector.add_rule_evaluation("CHECK_GATEWAY_FEE_RATE", "FAIL", expected_fee, settlement.fee_amount, fee_diff)
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.MISMATCH,
            reason_code=ReasonCode.FEE_DIFFERENCE,
            expected_amount=expected_net_clean,
            actual_amount=actual_net,
            difference=amount_diff(actual_net, expected_net_clean),
            confidence=0.95,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    # =========================================================================
    # RULE 8: TAX_MISMATCH
    # =========================================================================
    if invoice and tax_record:
        if not amounts_equal(invoice.tax_amount, tax_record.tax_amount) or not amounts_equal(invoice.tax_rate, tax_record.tax_rate):
            collector.add_evidence("invoices", invoice.invoice_id, "tax_amount", invoice.tax_amount, "Invoice calculated tax amount")
            collector.add_evidence("tax_records", tax_record.tax_id, "tax_amount", tax_record.tax_amount, "Tax record filed tax amount")
            collector.add_rule_evaluation("CHECK_TAX_LEDGER_MATCH", "FAIL", invoice.tax_amount, tax_record.tax_amount, amount_diff(tax_record.tax_amount, invoice.tax_amount))
            return ReconciliationResult(
                case_id=case_id,
                status=ReconciliationStatus.MISMATCH,
                reason_code=ReasonCode.TAX_MISMATCH,
                expected_amount=invoice.tax_amount,
                actual_amount=tax_record.tax_amount,
                difference=amount_diff(tax_record.tax_amount, invoice.tax_amount),
                confidence=0.95,
                needs_investigation=True,
                auto_resolvable=False,
                evidence=collector.evidence,
                rule_evaluations=collector.rule_evaluations,
            )

    # =========================================================================
    # RULE 9: UNKNOWN_ADJUSTMENT
    # =========================================================================
    if not amounts_equal(settlement.adjustment_amount, Decimal("0.00")):
        adj_val = settlement.adjustment_amount
        collector.add_evidence("settlements", settlement.settlement_id, "adjustment_amount", adj_val, "Unexplained settlement adjustment")
        expected_no_adj = round_currency(settlement.net_amount - adj_val)
        collector.add_rule_evaluation("CHECK_SETTLEMENT_ADJUSTMENT", "FAIL", Decimal("0.00"), adj_val, adj_val)
        return ReconciliationResult(
            case_id=case_id,
            status=ReconciliationStatus.MISMATCH,
            reason_code=ReasonCode.UNKNOWN_ADJUSTMENT,
            expected_amount=expected_no_adj,
            actual_amount=settlement.net_amount,
            difference=adj_val,
            confidence=0.95,
            needs_investigation=True,
            auto_resolvable=False,
            evidence=collector.evidence,
            rule_evaluations=collector.rule_evaluations,
        )

    # =========================================================================
    # RULE 10: TIMING_DIFFERENCE
    # =========================================================================
    if matched_btxns:
        primary_btxn = matched_btxns[0]
        delay_days = check_posting_delay(settlement.settlement_date, primary_btxn.transaction_date)
        collector.add_evidence("bank_transactions", primary_btxn.bank_txn_id, "transaction_date", primary_btxn.transaction_date, f"Bank posting delay: {delay_days} days")

        if delay_days > TIMING_TOLERANCE_DAYS:
            collector.add_rule_evaluation("CHECK_BANK_POSTING_TIMING", "FAIL", f"<= {TIMING_TOLERANCE_DAYS} days", f"{delay_days} days", f"{delay_days} days")
            return ReconciliationResult(
                case_id=case_id,
                status=ReconciliationStatus.MATCHED,
                reason_code=ReasonCode.TIMING_DIFFERENCE,
                expected_amount=expected_net_clean,
                actual_amount=settlement.net_amount,
                difference=Decimal("0.00"),
                confidence=1.00,
                needs_investigation=False,
                auto_resolvable=True,
                evidence=collector.evidence,
                rule_evaluations=collector.rule_evaluations,
            )

    # =========================================================================
    # RULE 11: EXACT_MATCH
    # =========================================================================
    collector.add_rule_evaluation("CHECK_FULL_END_TO_END_MATCH", "PASS", expected_net_clean, settlement.net_amount, Decimal("0.00"))
    return ReconciliationResult(
        case_id=case_id,
        status=ReconciliationStatus.MATCHED,
        reason_code=ReasonCode.EXACT_MATCH,
        expected_amount=expected_net_clean,
        actual_amount=settlement.net_amount,
        difference=Decimal("0.00"),
        confidence=1.00,
        needs_investigation=False,
        auto_resolvable=True,
        evidence=collector.evidence,
        rule_evaluations=collector.rule_evaluations,
    )
