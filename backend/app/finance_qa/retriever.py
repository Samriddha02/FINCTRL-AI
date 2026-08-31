import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.agents.tools import TOOLS
from app.services import database_service
from app.reconciliation.engine import reconcile_case
from app.models import Payment, Settlement, Invoice, TaxRecord, Order, Refund, BankTransaction
from app.finance_qa.schemas import QAFactRecord, QACalculation
from app.finance_qa.router import RouteResult

logger = logging.getLogger("qa_retriever")


class RetrievalResult(BaseModel):
    facts: List[QAFactRecord]
    calculations: List[QACalculation]
    citations: List[str]
    raw_data: Dict[str, Any]
    records_found: bool


def retrieve_qa_data_and_calculate(db: Session, route: RouteResult) -> RetrievalResult:
    """Executes read-only tools and performs deterministic calculations based on routed intent."""
    facts: List[QAFactRecord] = []
    calculations: List[QACalculation] = []
    citations: List[str] = []
    raw_data: Dict[str, Any] = {}
    records_found = False

    # Handle Aggregation queries
    if route.is_aggregation:
        return _handle_aggregation_query(db, route)

    extracted = route.extracted_ids

    # 1. Retrieve Payment details if payment_id present
    payment_ids = extracted.get("PAY", [])
    for pid in payment_ids:
        exec_logs = []
        p_res = TOOLS["get_payment_details"].execute(db, {"payment_id": pid}, exec_logs)
        p_data = p_res.get("data")
        if p_data:
            records_found = True
            raw_data["payment"] = p_data
            citations.append(f"Payment {pid}")
            facts.append(QAFactRecord(key="payment_id", value=p_data["payment_id"], source=f"Payment {pid}", entity_type="payment", entity_id=pid))
            facts.append(QAFactRecord(key="payment_amount", value=p_data["amount"], source=f"Payment {pid}", entity_type="payment", entity_id=pid))
            facts.append(QAFactRecord(key="payment_status", value=p_data["status"], source=f"Payment {pid}", entity_type="payment", entity_id=pid))
            facts.append(QAFactRecord(key="payment_currency", value=p_data["currency"], source=f"Payment {pid}", entity_type="payment", entity_id=pid))
            
            # Auto-resolve linked order/settlement if not specified
            if "ORD" not in extracted and p_data.get("order_id"):
                extracted["ORD"] = [p_data["order_id"]]

    # 2. Retrieve Order details
    order_ids = extracted.get("ORD", [])
    for oid in order_ids:
        exec_logs = []
        o_res = TOOLS["get_order_details"].execute(db, {"order_id": oid}, exec_logs)
        o_data = o_res.get("data")
        if o_data:
            records_found = True
            raw_data["order"] = o_data
            citations.append(f"Order {oid}")
            facts.append(QAFactRecord(key="order_id", value=o_data["order_id"], source=f"Order {oid}", entity_type="order", entity_id=oid))
            facts.append(QAFactRecord(key="order_amount", value=o_data["amount"], source=f"Order {oid}", entity_type="order", entity_id=oid))
            facts.append(QAFactRecord(key="order_status", value=o_data["status"], source=f"Order {oid}", entity_type="order", entity_id=oid))
            facts.append(QAFactRecord(key="customer_id", value=o_data["customer_id"], source=f"Order {oid}", entity_type="order", entity_id=oid))

            # Resolve linked invoice if not specified
            if "INV" not in extracted:
                inv_model = database_service.get_invoice_by_order(db, oid)
                if inv_model:
                    extracted["INV"] = [inv_model.invoice_id]

    # 3. Retrieve Refunds
    for pid in payment_ids:
        exec_logs = []
        r_res = TOOLS["get_refunds"].execute(db, {"payment_id": pid}, exec_logs)
        r_list = r_res.get("data", []) or []
        if r_list:
            records_found = True
            raw_data["refunds"] = r_list
            total_refund_dec = Decimal("0.00")
            for r_item in r_list:
                citations.append(f"Refund {r_item['refund_id']}")
                facts.append(QAFactRecord(key="refund_id", value=r_item["refund_id"], source=f"Refund {r_item['refund_id']}", entity_type="refund", entity_id=r_item["refund_id"]))
                facts.append(QAFactRecord(key="refund_amount", value=r_item["amount"], source=f"Refund {r_item['refund_id']}", entity_type="refund", entity_id=r_item["refund_id"]))
                facts.append(QAFactRecord(key="refund_status", value=r_item["status"], source=f"Refund {r_item['refund_id']}", entity_type="refund", entity_id=r_item["refund_id"]))
                total_refund_dec += Decimal(str(r_item["amount"]))
            
            calculations.append(QACalculation(
                calculation_name="total_refund_amount",
                formula="SUM(refund.amount)",
                value=float(total_refund_dec),
                source_facts=["refund_amount"]
            ))

    # 4. Retrieve Settlement details
    settlement_ids = extracted.get("SETTL", [])
    # Search by settlement_id or payment_id
    for sid in settlement_ids:
        exec_logs = []
        s_res = TOOLS["get_settlement_details"].execute(db, {"settlement_id": sid}, exec_logs)
        s_data = s_res.get("data")
        if s_data:
            records_found = True
            raw_data["settlement"] = s_data
            citations.append(f"Settlement {s_data['settlement_id']}")
            facts.append(QAFactRecord(key="settlement_id", value=s_data["settlement_id"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
            facts.append(QAFactRecord(key="gross_amount", value=s_data["gross_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
            facts.append(QAFactRecord(key="fee_amount", value=s_data["fee_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
            facts.append(QAFactRecord(key="tax_amount", value=s_data["tax_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
            facts.append(QAFactRecord(key="net_amount", value=s_data["net_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
            facts.append(QAFactRecord(key="settlement_status", value=s_data["status"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))

    for pid in payment_ids:
        if "settlement" not in raw_data:
            exec_logs = []
            s_res = TOOLS["get_settlement_details"].execute(db, {"payment_id": pid}, exec_logs)
            s_data = s_res.get("data")
            if s_data:
                records_found = True
                raw_data["settlement"] = s_data
                sid = s_data["settlement_id"]
                citations.append(f"Settlement {sid}")
                facts.append(QAFactRecord(key="settlement_id", value=sid, source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
                facts.append(QAFactRecord(key="gross_amount", value=s_data["gross_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
                facts.append(QAFactRecord(key="fee_amount", value=s_data["fee_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
                facts.append(QAFactRecord(key="tax_amount", value=s_data["tax_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
                facts.append(QAFactRecord(key="net_amount", value=s_data["net_amount"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))
                facts.append(QAFactRecord(key="settlement_status", value=s_data["status"], source=f"Settlement {sid}", entity_type="settlement", entity_id=sid))

    # 5. Retrieve Bank Transactions
    target_settlement_id = None
    if "settlement" in raw_data:
        target_settlement_id = raw_data["settlement"].get("settlement_id")
    elif settlement_ids:
        target_settlement_id = settlement_ids[0]

    if target_settlement_id:
        exec_logs = []
        bt_res = TOOLS["get_bank_transactions"].execute(db, {"settlement_id": target_settlement_id}, exec_logs)
        bt_list = bt_res.get("data", []) or []
        if bt_list:
            records_found = True
            raw_data["bank_transactions"] = bt_list
            for bt in bt_list:
                citations.append(f"BankTransaction {bt['bank_transaction_id']}")
                facts.append(QAFactRecord(key="bank_transaction_id", value=bt["bank_transaction_id"], source=f"BankTransaction {bt['bank_transaction_id']}", entity_type="bank_transaction", entity_id=bt["bank_transaction_id"]))
                facts.append(QAFactRecord(key="bank_amount", value=bt["amount"], source=f"BankTransaction {bt['bank_transaction_id']}", entity_type="bank_transaction", entity_id=bt["bank_transaction_id"]))
                facts.append(QAFactRecord(key="posting_date", value=bt["posting_date"], source=f"BankTransaction {bt['bank_transaction_id']}", entity_type="bank_transaction", entity_id=bt["bank_transaction_id"]))

    # 6. Retrieve Invoice details
    invoice_ids = extracted.get("INV", [])
    for inv_id in invoice_ids:
        exec_logs = []
        inv_res = TOOLS["get_invoice_details"].execute(db, {"invoice_id": inv_id}, exec_logs)
        inv_data = inv_res.get("data")
        if inv_data:
            records_found = True
            raw_data["invoice"] = inv_data
            citations.append(f"Invoice {inv_id}")
            facts.append(QAFactRecord(key="invoice_id", value=inv_data["invoice_id"], source=f"Invoice {inv_id}", entity_type="invoice", entity_id=inv_id))
            facts.append(QAFactRecord(key="invoice_amount", value=inv_data["amount"], source=f"Invoice {inv_id}", entity_type="invoice", entity_id=inv_id))
            facts.append(QAFactRecord(key="invoice_tax", value=inv_data["tax_amount"], source=f"Invoice {inv_id}", entity_type="invoice", entity_id=inv_id))
            facts.append(QAFactRecord(key="invoice_status", value=inv_data["status"], source=f"Invoice {inv_id}", entity_type="invoice", entity_id=inv_id))

    # 7. Retrieve Tax Record & Tax Matching details
    tax_ids = extracted.get("TAX", [])
    search_invoice_ids = invoice_ids.copy()
    if "invoice" in raw_data:
        search_invoice_ids.append(raw_data["invoice"]["invoice_id"])

    for inv_id in set(search_invoice_ids):
        exec_logs = []
        tax_res = TOOLS["get_tax_record"].execute(db, {"invoice_id": inv_id}, exec_logs)
        tax_data = tax_res.get("data")
        if tax_data:
            records_found = True
            raw_data["tax_record"] = tax_data
            citations.append(f"TaxRecord {tax_data['tax_id']}")
            facts.append(QAFactRecord(key="tax_id", value=tax_data["tax_id"], source=f"TaxRecord {tax_data['tax_id']}", entity_type="tax_record", entity_id=tax_data["tax_id"]))
            facts.append(QAFactRecord(key="tax_record_tax", value=tax_data["tax_amount"], source=f"TaxRecord {tax_data['tax_id']}", entity_type="tax_record", entity_id=tax_data["tax_id"]))
            facts.append(QAFactRecord(key="taxable_amount", value=tax_data["taxable_amount"], source=f"TaxRecord {tax_data['tax_id']}", entity_type="tax_record", entity_id=tax_data["tax_id"]))
            facts.append(QAFactRecord(key="tax_rate", value=tax_data["tax_rate"], source=f"TaxRecord {tax_data['tax_id']}", entity_type="tax_record", entity_id=tax_data["tax_id"]))

        # Also delegate to Phase 11 Tax Matching Engine
        try:
            from app.tax_matching.controller import TaxMatchController
            tm_res = TaxMatchController(db).process_tax_match(inv_id)
            facts.append(QAFactRecord(key="tax_match_status", value=tm_res.status.value, source="Tax Line Matcher Engine", entity_type="tax_matching", entity_id=inv_id))
            facts.append(QAFactRecord(key="tax_match_difference", value=tm_res.difference, source="Tax Line Matcher Engine", entity_type="tax_matching", entity_id=inv_id))
            citations.append(f"TaxMatch {tm_res.match_id}")
        except Exception:
            pass

    # 8. Retrieve Reconciliation Result
    case_ids = extracted.get("CASE", [])
    for cid in case_ids:
        recon_res = reconcile_case(db, cid)
        records_found = True
        raw_data["reconciliation"] = recon_res.to_dict()
        citations.append(f"ReconciliationCase {cid}")
        facts.append(QAFactRecord(key="case_id", value=cid, source=f"ReconciliationCase {cid}", entity_type="case", entity_id=cid))
        facts.append(QAFactRecord(key="reconciliation_status", value=recon_res.status.value, source=f"ReconciliationCase {cid}", entity_type="case", entity_id=cid))
        facts.append(QAFactRecord(key="reason_code", value=recon_res.reason_code.value, source=f"ReconciliationCase {cid}", entity_type="case", entity_id=cid))
        facts.append(QAFactRecord(key="expected_amount", value=float(recon_res.expected_amount), source=f"ReconciliationCase {cid}", entity_type="case", entity_id=cid))
        facts.append(QAFactRecord(key="actual_amount", value=float(recon_res.actual_amount), source=f"ReconciliationCase {cid}", entity_type="case", entity_id=cid))
        facts.append(QAFactRecord(key="difference", value=float(recon_result_diff(recon_res)), source=f"ReconciliationCase {cid}", entity_type="case", entity_id=cid))

    # Deterministic Calculations using Decimal
    # Calculation A: Invoice Tax vs Tax Record Tax Difference
    if "invoice" in raw_data and "tax_record" in raw_data:
        inv_tax_dec = Decimal(str(raw_data["invoice"]["tax_amount"]))
        tax_rec_dec = Decimal(str(raw_data["tax_record"]["tax_amount"]))
        diff_dec = inv_tax_dec - tax_rec_dec
        calculations.append(QACalculation(
            calculation_name="tax_difference",
            formula="invoice.tax_amount - tax_record.tax_amount",
            value=float(diff_dec),
            source_facts=["invoice_tax", "tax_record_tax"]
        ))

    # Calculation B: Payment vs Settlement Net Difference
    if "payment" in raw_data and "settlement" in raw_data:
        pay_dec = Decimal(str(raw_data["payment"]["amount"]))
        net_dec = Decimal(str(raw_data["settlement"]["net_amount"]))
        settl_diff_dec = pay_dec - net_dec
        calculations.append(QACalculation(
            calculation_name="payment_settlement_difference",
            formula="payment.amount - settlement.net_amount",
            value=float(settl_diff_dec),
            source_facts=["payment_amount", "net_amount"]
        ))

    return RetrievalResult(
        facts=facts,
        calculations=calculations,
        citations=list(set(citations)),
        raw_data=raw_data,
        records_found=records_found
    )


def recon_result_diff(recon_res) -> float:
    return float(recon_res.difference)


def _handle_aggregation_query(db: Session, route: RouteResult) -> RetrievalResult:
    """Computes deterministic aggregation counts and sums using Decimal arithmetic."""
    facts: List[QAFactRecord] = []
    calculations: List[QACalculation] = []
    citations: List[str] = []

    target = route.aggregation_target or "payments"

    if target == "payments":
        total_count = db.query(Payment).count()
        sum_amount = db.query(func.sum(Payment.amount)).scalar() or Decimal("0.00")
        captured_count = db.query(Payment).filter(Payment.payment_status == "CAPTURED").count()
        
        sum_dec = Decimal(str(sum_amount))

        facts.append(QAFactRecord(key="total_payments_count", value=total_count, source="Payments Table", entity_type="aggregation"))
        facts.append(QAFactRecord(key="captured_payments_count", value=captured_count, source="Payments Table", entity_type="aggregation"))
        facts.append(QAFactRecord(key="total_payment_amount", value=float(sum_dec), source="Payments Table", entity_type="aggregation"))
        citations.append("Payments Table")

        calculations.append(QACalculation(
            calculation_name="total_payment_sum",
            formula="SUM(payment.amount)",
            value=float(sum_dec),
            source_facts=["total_payment_amount"]
        ))

    elif target == "settlements":
        total_count = db.query(Settlement).count()
        sum_net = db.query(func.sum(Settlement.net_amount)).scalar() or Decimal("0.00")
        sum_gross = db.query(func.sum(Settlement.gross_amount)).scalar() or Decimal("0.00")

        net_dec = Decimal(str(sum_net))
        gross_dec = Decimal(str(sum_gross))

        facts.append(QAFactRecord(key="total_settlements_count", value=total_count, source="Settlements Table", entity_type="aggregation"))
        facts.append(QAFactRecord(key="total_settlement_net_amount", value=float(net_dec), source="Settlements Table", entity_type="aggregation"))
        facts.append(QAFactRecord(key="total_settlement_gross_amount", value=float(gross_dec), source="Settlements Table", entity_type="aggregation"))
        citations.append("Settlements Table")

        calculations.append(QACalculation(
            calculation_name="total_settlement_net_sum",
            formula="SUM(settlement.net_amount)",
            value=float(net_dec),
            source_facts=["total_settlement_net_amount"]
        ))

    elif target == "cases_needing_investigation":
        from app.models import Order
        orders = db.query(Order).all()
        cases_needing_inv = 0
        total_cases = 0
        for ord_obj in orders:
            case_id = f"CASE-{ord_obj.order_id.replace('ORD-', '')}"
            res = reconcile_case(db, case_id)
            if res.status.value != "ERROR":
                total_cases += 1
                if res.needs_investigation:
                    cases_needing_inv += 1

        facts.append(QAFactRecord(key="total_cases_count", value=total_cases, source="Reconciliation Engine", entity_type="aggregation"))
        facts.append(QAFactRecord(key="cases_needing_investigation_count", value=cases_needing_inv, source="Reconciliation Engine", entity_type="aggregation"))
        citations.append("Reconciliation Engine")

        calculations.append(QACalculation(
            calculation_name="investigation_case_count",
            formula="COUNT(cases WHERE needs_investigation = True)",
            value=cases_needing_inv,
            source_facts=["cases_needing_investigation_count"]
        ))

    elif target == "cash_forecast":
        from app.forecasting.controller import CashForecastController
        fc_res = CashForecastController(db).generate_forecast(horizon_days=7)
        
        facts.append(QAFactRecord(key="forecast_horizon_days", value=fc_res.horizon_days, source="Cash Forecasting Engine", entity_type="forecast"))
        facts.append(QAFactRecord(key="forecast_inflow", value=fc_res.forecast.inflow, source="Cash Forecasting Engine", entity_type="forecast"))
        facts.append(QAFactRecord(key="forecast_outflow", value=fc_res.forecast.outflow, source="Cash Forecasting Engine", entity_type="forecast"))
        facts.append(QAFactRecord(key="forecast_net", value=fc_res.forecast.net, source="Cash Forecasting Engine", entity_type="forecast"))
        facts.append(QAFactRecord(key="forecast_confidence", value=fc_res.confidence, source="Cash Forecasting Engine", entity_type="forecast"))
        citations.append(f"Cash Forecast {fc_res.forecast_id}")

        calculations.append(QACalculation(
            calculation_name="expected_net_cash",
            formula="forecast.inflow - forecast.outflow",
            value=fc_res.forecast.net,
            source_facts=["forecast_inflow", "forecast_outflow"]
        ))

    return RetrievalResult(
        facts=facts,
        calculations=calculations,
        citations=citations,
        raw_data={},
        records_found=True
    )
