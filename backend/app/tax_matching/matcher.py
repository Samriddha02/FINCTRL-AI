import uuid
import datetime
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import Invoice, TaxRecord
from app.agents.tools import validate_id
from app.tax_matching.constants import TAX_AMOUNT_TOLERANCE, TAX_RATE_TOLERANCE
from app.tax_matching.schemas import (
    TaxMatchResult,
    TaxBatchMatchSummary,
    TaxMatchStatus,
    TaxReasonCode,
    TaxRuleEvaluation,
    TaxEvidenceItem
)

logger = logging.getLogger("tax_matcher")


def normalize_tax_rate(rate: Any) -> Decimal:
    """Normalizes tax rate representation into standard decimal scale (e.g. 18.0 -> 0.18, 0.18 -> 0.18)."""
    if rate is None:
        return Decimal("0.0000")
    rate_dec = Decimal(str(rate))
    if rate_dec > Decimal("1.0"):
        return rate_dec / Decimal("100.0")
    return rate_dec


def match_tax_line(db: Session, invoice_id: str) -> TaxMatchResult:
    """Deterministically compares an Invoice tax line against authoritative TaxRecord ledger entries."""
    validate_id(invoice_id)

    # 1. Fetch Invoice
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise ValueError(f"Invoice '{invoice_id}' not found in database.")

    # 2. Fetch linked TaxRecords
    tax_records = db.query(TaxRecord).filter(TaxRecord.invoice_id == invoice_id).all()

    match_id = f"TM-{uuid.uuid4().hex[:10].upper()}"
    evidence: List[TaxEvidenceItem] = [
        TaxEvidenceItem(source="Invoice", entity_id=invoice.invoice_id, field="subtotal", value=str(invoice.subtotal)),
        TaxEvidenceItem(source="Invoice", entity_id=invoice.invoice_id, field="tax_rate", value=str(invoice.tax_rate)),
        TaxEvidenceItem(source="Invoice", entity_id=invoice.invoice_id, field="tax_amount", value=str(invoice.tax_amount)),
        TaxEvidenceItem(source="Invoice", entity_id=invoice.invoice_id, field="total_amount", value=str(invoice.total_amount))
    ]

    # Precedence Rule 1: Missing Tax Record
    if not tax_records:
        return TaxMatchResult(
            match_id=match_id,
            invoice_id=invoice.invoice_id,
            tax_id=None,
            status=TaxMatchStatus.MISSING_TAX_RECORD,
            reason_code=TaxReasonCode.MISSING_TAX_RECORD,
            invoice_taxable_amount=float(invoice.subtotal),
            invoice_tax_amount=float(invoice.tax_amount),
            invoice_tax_rate=float(invoice.tax_rate),
            expected_tax_amount=float(Decimal(str(invoice.subtotal)) * normalize_tax_rate(invoice.tax_rate)),
            difference=float(invoice.tax_amount),
            confidence=1.0,
            needs_review=True,
            evidence=evidence,
            rule_evaluations=[
                TaxRuleEvaluation(
                    rule_name="CHECK_TAX_RECORD_EXISTS",
                    expected_val="TaxRecord present",
                    actual_val="No TaxRecord found",
                    difference=str(invoice.tax_amount),
                    status="FAIL"
                )
            ],
            warnings=[f"Invoice '{invoice_id}' has no corresponding TaxRecord in the tax ledger."]
        )

    # Precedence Rule 2: Duplicate Tax Records
    if len(tax_records) > 1:
        for tr in tax_records:
            evidence.append(TaxEvidenceItem(source="TaxRecord", entity_id=tr.tax_id, field="tax_amount", value=str(tr.tax_amount)))
        
        return TaxMatchResult(
            match_id=match_id,
            invoice_id=invoice.invoice_id,
            tax_id=tax_records[0].tax_id,
            status=TaxMatchStatus.DUPLICATE_TAX_RECORD,
            reason_code=TaxReasonCode.DUPLICATE_TAX_RECORD,
            invoice_taxable_amount=float(invoice.subtotal),
            invoice_tax_amount=float(invoice.tax_amount),
            invoice_tax_rate=float(invoice.tax_rate),
            confidence=0.5,
            needs_review=True,
            evidence=evidence,
            rule_evaluations=[
                TaxRuleEvaluation(
                    rule_name="CHECK_SINGLE_TAX_RECORD",
                    expected_val="1 TaxRecord",
                    actual_val=f"{len(tax_records)} TaxRecords found",
                    difference="0.00",
                    status="FAIL"
                )
            ],
            warnings=[f"Invoice '{invoice_id}' is linked to {len(tax_records)} duplicate TaxRecord entries."]
        )

    # Single TaxRecord comparison
    tr = tax_records[0]
    evidence.extend([
        TaxEvidenceItem(source="TaxRecord", entity_id=tr.tax_id, field="taxable_amount", value=str(tr.taxable_amount)),
        TaxEvidenceItem(source="TaxRecord", entity_id=tr.tax_id, field="tax_rate", value=str(tr.tax_rate)),
        TaxEvidenceItem(source="TaxRecord", entity_id=tr.tax_id, field="tax_amount", value=str(tr.tax_amount)),
        TaxEvidenceItem(source="TaxRecord", entity_id=tr.tax_id, field="tax_type", value=str(tr.tax_type))
    ])

    # Convert to Decimal for exact math
    inv_taxable_dec = Decimal(str(invoice.subtotal))
    inv_rate_dec = normalize_tax_rate(invoice.tax_rate)
    inv_tax_dec = Decimal(str(invoice.tax_amount))

    tr_taxable_dec = Decimal(str(tr.taxable_amount))
    tr_rate_dec = normalize_tax_rate(tr.tax_rate)
    tr_tax_dec = Decimal(str(tr.tax_amount))

    expected_tax_dec = inv_taxable_dec * inv_rate_dec
    tax_diff_dec = inv_tax_dec - tr_tax_dec
    taxable_diff_dec = inv_taxable_dec - tr_taxable_dec
    calc_diff_dec = tr_tax_dec - (tr_taxable_dec * tr_rate_dec)

    rule_evals: List[TaxRuleEvaluation] = []

    # Rule 1: Calculation accuracy (taxable * rate == tax_amount)
    calc_pass = abs(calc_diff_dec) <= TAX_AMOUNT_TOLERANCE
    rule_evals.append(TaxRuleEvaluation(
        rule_name="CHECK_TAX_CALCULATION_ACCURACY",
        expected_val=f"{tr_taxable_dec * tr_rate_dec:.2f}",
        actual_val=f"{tr_tax_dec:.2f}",
        difference=f"{calc_diff_dec:.2f}",
        status="PASS" if calc_pass else "FAIL"
    ))

    # Rule 2: Taxable amount match
    taxable_pass = abs(taxable_diff_dec) <= TAX_AMOUNT_TOLERANCE
    rule_evals.append(TaxRuleEvaluation(
        rule_name="CHECK_TAXABLE_AMOUNT_MATCH",
        expected_val=f"{inv_taxable_dec:.2f}",
        actual_val=f"{tr_taxable_dec:.2f}",
        difference=f"{taxable_diff_dec:.2f}",
        status="PASS" if taxable_pass else "FAIL"
    ))

    # Rule 3: Tax rate match
    rate_pass = abs(inv_rate_dec - tr_rate_dec) <= TAX_RATE_TOLERANCE
    rule_evals.append(TaxRuleEvaluation(
        rule_name="CHECK_TAX_RATE_MATCH",
        expected_val=f"{inv_rate_dec * 100:.1f}%",
        actual_val=f"{tr_rate_dec * 100:.1f}%",
        difference=f"{(inv_rate_dec - tr_rate_dec) * 100:.1f}%",
        status="PASS" if rate_pass else "FAIL"
    ))

    # Rule 4: Tax amount match
    amount_pass = abs(tax_diff_dec) <= TAX_AMOUNT_TOLERANCE
    rule_evals.append(TaxRuleEvaluation(
        rule_name="CHECK_TAX_AMOUNT_MATCH",
        expected_val=f"{inv_tax_dec:.2f}",
        actual_val=f"{tr_tax_dec:.2f}",
        difference=f"{tax_diff_dec:.2f}",
        status="PASS" if amount_pass else "FAIL"
    ))

    # Determine Precedence
    status_val = TaxMatchStatus.EXACT_MATCH
    reason_val = TaxReasonCode.TAX_EXACT_MATCH
    needs_review = False
    confidence = 1.0

    if not calc_pass:
        status_val = TaxMatchStatus.CALCULATION_MISMATCH
        reason_val = TaxReasonCode.TAX_CALCULATION_MISMATCH
        needs_review = True
        confidence = 0.85
    elif not taxable_pass:
        status_val = TaxMatchStatus.TAXABLE_AMOUNT_MISMATCH
        reason_val = TaxReasonCode.TAXABLE_AMOUNT_MISMATCH
        needs_review = True
        confidence = 0.90
    elif not rate_pass:
        status_val = TaxMatchStatus.RATE_MISMATCH
        reason_val = TaxReasonCode.TAX_RATE_MISMATCH
        needs_review = True
        confidence = 0.90
    elif not amount_pass:
        status_val = TaxMatchStatus.AMOUNT_MISMATCH
        reason_val = TaxReasonCode.TAX_AMOUNT_MISMATCH
        needs_review = True
        confidence = 0.95

    return TaxMatchResult(
        match_id=match_id,
        invoice_id=invoice.invoice_id,
        tax_id=tr.tax_id,
        status=status_val,
        reason_code=reason_val,
        invoice_taxable_amount=float(inv_taxable_dec),
        ledger_taxable_amount=float(tr_taxable_dec),
        invoice_tax_amount=float(inv_tax_dec),
        ledger_tax_amount=float(tr_tax_dec),
        invoice_tax_rate=float(inv_rate_dec),
        ledger_tax_rate=float(tr_rate_dec),
        expected_tax_amount=float(expected_tax_dec),
        difference=float(tax_diff_dec),
        confidence=confidence,
        needs_review=needs_review,
        evidence=evidence,
        rule_evaluations=rule_evals,
        warnings=[]
    )


def match_all_tax_lines(db: Session) -> TaxBatchMatchSummary:
    """Runs deterministic tax matching across all invoices in database and aggregates statistics."""
    invoices = db.query(Invoice).all()

    results: List[TaxMatchResult] = []
    exact_count = 0
    amount_mismatch_count = 0
    rate_mismatch_count = 0
    taxable_mismatch_count = 0
    calc_mismatch_count = 0
    missing_count = 0
    duplicate_count = 0

    for inv in invoices:
        res = match_tax_line(db, inv.invoice_id)
        results.append(res)

        if res.status == TaxMatchStatus.EXACT_MATCH:
            exact_count += 1
        elif res.status == TaxMatchStatus.AMOUNT_MISMATCH:
            amount_mismatch_count += 1
        elif res.status == TaxMatchStatus.RATE_MISMATCH:
            rate_mismatch_count += 1
        elif res.status == TaxMatchStatus.TAXABLE_AMOUNT_MISMATCH:
            taxable_mismatch_count += 1
        elif res.status == TaxMatchStatus.CALCULATION_MISMATCH:
            calc_mismatch_count += 1
        elif res.status == TaxMatchStatus.MISSING_TAX_RECORD:
            missing_count += 1
        elif res.status == TaxMatchStatus.DUPLICATE_TAX_RECORD:
            duplicate_count += 1

    return TaxBatchMatchSummary(
        total_invoices_checked=len(invoices),
        exact_matches=exact_count,
        amount_mismatches=amount_mismatch_count,
        rate_mismatches=rate_mismatch_count,
        taxable_amount_mismatches=taxable_mismatch_count,
        calculation_mismatches=calc_mismatch_count,
        missing_records=missing_count,
        duplicate_records=duplicate_count,
        results=results
    )
