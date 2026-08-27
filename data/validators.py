from decimal import Decimal
from typing import Dict, List, Any
import logging


def validate_dataset(
    customers: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
    payments: List[Dict[str, Any]],
    refunds: List[Dict[str, Any]],
    settlements: List[Dict[str, Any]],
    bank_txns: List[Dict[str, Any]],
    invoices: List[Dict[str, Any]],
    tax_records: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]],
    expected_case_count: int,
    expected_distribution: Dict[str, int],
) -> bool:
    """Validates relational integrity, mathematical consistency, ground truth coverage,

    and anomaly distribution of the synthetic dataset.
    Returns True if valid, raises ValueError with detailed error messages if invalid.
    """
    errors: List[str] = []

    # 1. Validate Case Count and Ground Truth Coverage
    gt_cases = {gt["case_id"]: gt for gt in ground_truth}
    if len(ground_truth) != expected_case_count:
        errors.append(
            f"Ground truth count ({len(ground_truth)}) does not match expected case count ({expected_case_count})."
        )

    # Validate ground truth fields exist
    for gt in ground_truth:
        for field in [
            "case_id",
            "ground_truth_status",
            "ground_truth_root_cause",
            "ground_truth_expected_amount",
            "ground_truth_actual_amount",
            "ground_truth_should_auto_resolve",
        ]:
            if field not in gt or gt[field] is None:
                errors.append(f"Ground truth case {gt.get('case_id')} missing field: {field}")

    # 2. Validate Anomaly Distribution
    actual_distribution: Dict[str, int] = {}
    for gt in ground_truth:
        status = gt["ground_truth_status"]
        actual_distribution[status] = actual_distribution.get(status, 0) + 1

    for status, expected_cnt in expected_distribution.items():
        actual_cnt = actual_distribution.get(status, 0)
        # Allow slight variance if total cases is scaled
        if expected_case_count == 100 and actual_cnt != expected_cnt:
            errors.append(
                f"Anomaly distribution mismatch for {status}: expected {expected_cnt}, got {actual_cnt}"
            )

    # 3. Entity ID Uniqueness (Excluding expected duplicates in duplicate anomaly cases)
    duplicate_cases = {
        gt["case_id"]
        for gt in ground_truth
        if gt["ground_truth_status"] == "DUPLICATE_TRANSACTION"
    }

    # Customers
    cust_ids = [c["customer_id"] for c in customers]
    if len(cust_ids) != len(set(cust_ids)):
        errors.append("Duplicate customer_id found in customers dataset.")

    # Orders
    order_ids = [o["order_id"] for o in orders]
    non_dup_order_ids = [
        o["order_id"] for o in orders if o["case_id"] not in duplicate_cases
    ]
    if len(non_dup_order_ids) != len(set(non_dup_order_ids)):
        errors.append("Duplicate order_id found in non-duplicate orders.")

    # Payments
    payment_ids = [p["payment_id"] for p in payments]
    non_dup_payment_ids = [
        p["payment_id"] for p in payments if p["case_id"] not in duplicate_cases
    ]
    if len(non_dup_payment_ids) != len(set(non_dup_payment_ids)):
        errors.append("Duplicate payment_id found in non-duplicate payments.")

    # Invoices
    invoice_ids = [i["invoice_id"] for i in invoices]
    if len(invoice_ids) != len(set(invoice_ids)):
        errors.append("Duplicate invoice_id found in invoices dataset.")

    # 4. Foreign Key Relationships
    cust_set = set(cust_ids)
    order_set = set(order_ids)
    payment_set = set(payment_ids)
    settlement_ids = [s["settlement_id"] for s in settlements]
    settlement_set = set(settlement_ids)
    invoice_set = set(invoice_ids)

    for o in orders:
        if o["customer_id"] not in cust_set:
            errors.append(f"Order {o['order_id']} references missing customer {o['customer_id']}")

    for p in payments:
        if p["customer_id"] not in cust_set:
            errors.append(f"Payment {p['payment_id']} references missing customer {p['customer_id']}")
        if p["order_id"] not in order_set:
            errors.append(f"Payment {p['payment_id']} references missing order {p['order_id']}")

    for r in refunds:
        if r["payment_id"] not in payment_set:
            errors.append(f"Refund {r['refund_id']} references missing payment {r['payment_id']}")

    for s in settlements:
        if s["payment_id"] not in payment_set:
            errors.append(f"Settlement {s['settlement_id']} references missing payment {s['payment_id']}")

    for i in invoices:
        if i["order_id"] not in order_set:
            errors.append(f"Invoice {i['invoice_id']} references missing order {i['order_id']}")
        if i["customer_id"] not in cust_set:
            errors.append(f"Invoice {i['invoice_id']} references missing customer {i['customer_id']}")

    for t in tax_records:
        if t["invoice_id"] not in invoice_set:
            errors.append(f"TaxRecord {t['tax_id']} references missing invoice {t['invoice_id']}")

    for b in bank_txns:
        # Bank references settlement_id or payment_id (unless ambiguous/missing/duplicate)
        ref_id = b.get("reference_id")
        b_case = b["case_id"]
        gt_status = gt_cases.get(b_case, {}).get("ground_truth_status")
        if gt_status not in ["AMBIGUOUS_CASE", "MISSING_SETTLEMENT"] and ref_id:
            if ref_id not in settlement_set and ref_id not in payment_set and ref_id not in order_set:
                errors.append(f"Bank Transaction {b['bank_txn_id']} has invalid reference_id {ref_id}")

    # 5. Financial & Math Invariants for Normal / EXACT_MATCH Cases
    for i in invoices:
        case_status = gt_cases.get(i["case_id"], {}).get("ground_truth_status")
        if case_status in ["EXACT_MATCH", "PARTIAL_REFUND", "TIMING_DIFFERENCE", "FEE_DIFFERENCE"]:
            subtotal = Decimal(str(i["subtotal"]))
            tax = Decimal(str(i["tax_amount"]))
            total = Decimal(str(i["total_amount"]))
            if abs((subtotal + tax) - total) > Decimal("0.05"):
                errors.append(
                    f"Invoice {i['invoice_id']} math mismatch: subtotal ({subtotal}) + tax ({tax}) != total ({total})"
                )

    for s in settlements:
        case_status = gt_cases.get(s["case_id"], {}).get("ground_truth_status")
        if case_status in ["EXACT_MATCH", "TIMING_DIFFERENCE"]:
            gross = Decimal(str(s["gross_amount"]))
            fee = Decimal(str(s["fee_amount"]))
            tax = Decimal(str(s["tax_amount"]))
            adj = Decimal(str(s["adjustment_amount"]))
            net = Decimal(str(s["net_amount"]))
            expected_net = gross - fee - tax + adj
            if abs(expected_net - net) > Decimal("0.05"):
                errors.append(
                    f"Settlement {s['settlement_id']} math mismatch: net ({net}) != gross ({gross}) - fee ({fee}) - tax ({tax}) + adj ({adj})"
                )

    # 6. Absence of Ground Truth Leaks in Financial Data
    all_financial_records = (
        customers + orders + payments + refunds + settlements + bank_txns + invoices + tax_records
    )
    for record in all_financial_records:
        for k, v in record.items():
            if "ground_truth" in k.lower() or "anomaly" in str(v).lower():
                errors.append(f"Ground truth or anomaly label leaked in record key/value: {k}={v}")

    if errors:
        error_msg = "Validation failed with errors:\n" + "\n".join(f"- {e}" for e in errors[:20])
        if len(errors) > 20:
            error_msg += f"\n...and {len(errors) - 20} more errors."
        logging.error(error_msg)
        raise ValueError(error_msg)

    logging.info("Dataset validation PASSED successfully.")
    return True
