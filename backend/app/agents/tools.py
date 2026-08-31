import re
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.services import database_service
from app.reconciliation.engine import reconcile_case

# Input Validation Regex patterns to ensure safety
# Matches valid IDs like PAY-00001, ORD-00001, SET-00001, INV-00001, TAX-00001, BT-00001, CASE-00001
FINCTRL_ID_PATTERN = re.compile(r"^(CUST|ORD|PAY|REF|SETTL|BTXN|INV|TAX|CASE)-\d+$")
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

def validate_id(id_val: str) -> None:
    """Checks if the ID is safe and matches standard formats. Raises ValueError if unsafe."""
    if not id_val or not isinstance(id_val, str):
        raise ValueError("Invalid tool argument: ID must be a non-empty string.")
    
    # Reject path traversal early
    if ".." in id_val or "/" in id_val or "\\" in id_val:
        raise ValueError(f"Security Alert: SQL or path injection pattern detected in argument: '{id_val}'")
        
    # If it perfectly matches our known business ID formats, it is safe
    if FINCTRL_ID_PATTERN.match(id_val):
        return
        
    # Reject path traversal and SQL injection attempts
    if not SAFE_ID_PATTERN.match(id_val):
        raise ValueError(f"Security Alert: Unsafe characters detected in argument: '{id_val}'")
    
    # Reject typical SQL injection terms or file path traversal
    lower_val = id_val.lower()
    unsafe_keywords = [r"\bselect\b", r"\bunion\b", r"\binsert\b", r"\bdrop\b", r"\bdelete\b", r"\bupdate\b", r"\bwhere\b", r"\bor\b", r"\band\b"]
    for kw in unsafe_keywords:
        if re.search(kw, lower_val):
            raise ValueError(f"Security Alert: SQL or path injection pattern detected in argument: '{id_val}'")


class AgentTool:
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any], output_schema: Dict[str, Any], func: Any):
        self.name = name
        self.description = description
        self.permission = "READ_ONLY"
        self.read_only = True
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.func = func

    def execute(self, db: Session, args: Dict[str, Any], execution_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        timestamp = datetime.datetime.utcnow().isoformat()
        log_record = {
            "tool_name": self.name,
            "arguments": args.copy(),
            "timestamp": timestamp,
            "success": False,
            "result_summary": "",
            "error": None
        }
        
        try:
            # Validate input arguments
            for arg_name, arg_val in args.items():
                if isinstance(arg_val, str):
                    validate_id(arg_val)

            # Invoke underlying read-only function
            result = self.func(db, **args)
            
            log_record["success"] = True
            if isinstance(result, list):
                log_record["result_summary"] = f"Returned list of {len(result)} records"
            elif result is None:
                log_record["result_summary"] = "No record found (None)"
            else:
                log_record["result_summary"] = "Record found successfully"
                
            execution_logs.append(log_record)
            return {"success": True, "data": result}
            
        except Exception as e:
            log_record["error"] = str(e)
            log_record["result_summary"] = f"Execution failed: {str(e)}"
            execution_logs.append(log_record)
            return {"success": False, "error": str(e), "data": None}


# Database row to dict serializer helpers to avoid leaking model internals
def _payment_to_dict(payment) -> Optional[Dict[str, Any]]:
    if not payment: return None
    return {
        "payment_id": payment.payment_id,
        "order_id": payment.order_id,
        "customer_id": payment.customer_id,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "status": payment.payment_status,
        "created_at": payment.created_at.isoformat() if payment.created_at else None
    }

def _order_to_dict(order) -> Optional[Dict[str, Any]]:
    if not order: return None
    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "amount": float(order.order_amount),
        "status": order.order_status,
        "created_at": order.created_at.isoformat() if order.created_at else None
    }

def _refund_to_dict(refund) -> Dict[str, Any]:
    return {
        "refund_id": refund.refund_id,
        "payment_id": refund.payment_id,
        "amount": float(refund.refund_amount),
        "status": refund.refund_status,
        "created_at": refund.created_at.isoformat() if refund.created_at else None
    }

def _settlement_to_dict(settlement) -> Optional[Dict[str, Any]]:
    if not settlement: return None
    return {
        "settlement_id": settlement.settlement_id,
        "payment_id": settlement.payment_id,
        "gross_amount": float(settlement.gross_amount),
        "fee_amount": float(settlement.fee_amount),
        "tax_amount": float(settlement.tax_amount),
        "net_amount": float(settlement.net_amount),
        "status": settlement.settlement_status,
        "processed_at": settlement.settlement_date.isoformat() if settlement.settlement_date else None
    }

def _bank_txn_to_dict(txn) -> Dict[str, Any]:
    return {
        "bank_transaction_id": txn.bank_txn_id,
        "reference_id": txn.reference_id,
        "amount": float(txn.amount),
        "currency": "INR",  # assuming standard or adding back if it existed
        "posting_date": txn.transaction_date.isoformat() if txn.transaction_date else None,
        "description": txn.description
    }

def _invoice_to_dict(invoice) -> Optional[Dict[str, Any]]:
    if not invoice: return None
    return {
        "invoice_id": invoice.invoice_id,
        "order_id": invoice.order_id,
        "amount": float(invoice.total_amount),
        "tax_amount": float(invoice.tax_amount),
        "status": invoice.invoice_status,
        "issued_at": invoice.invoice_date.isoformat() if invoice.invoice_date else None
    }

def _tax_record_to_dict(tax) -> Optional[Dict[str, Any]]:
    if not tax: return None
    return {
        "tax_id": tax.tax_id,
        "invoice_id": tax.invoice_id,
        "tax_type": tax.tax_type,
        "taxable_amount": float(tax.taxable_amount),
        "tax_rate": float(tax.tax_rate),
        "tax_amount": float(tax.tax_amount),
        "filing_period": tax.filing_period,
        "recorded_at": tax.recorded_at.isoformat() if tax.recorded_at else None
    }


# Underlaying tool implementation functions (strictly read-only)

def _get_payment_details_impl(db: Session, payment_id: str) -> Optional[Dict[str, Any]]:
    payment = database_service.get_payment(db, payment_id)
    return _payment_to_dict(payment)

def _get_order_details_impl(db: Session, order_id: str) -> Optional[Dict[str, Any]]:
    order = database_service.get_order(db, order_id)
    return _order_to_dict(order)

def _get_refunds_impl(db: Session, payment_id: str) -> List[Dict[str, Any]]:
    refunds = database_service.get_refunds(db, payment_id)
    return [_refund_to_dict(r) for r in refunds]

def _get_settlement_details_impl(db: Session, payment_id: Optional[str] = None, settlement_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if payment_id:
        settlement = database_service.get_settlement(db, payment_id)
    elif settlement_id:
        from app.models import Settlement
        settlement = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
    else:
        raise ValueError("Either payment_id or settlement_id must be provided to get_settlement_details.")
    return _settlement_to_dict(settlement)

def _get_bank_transactions_impl(db: Session, settlement_id: Optional[str] = None, reference_id: Optional[str] = None) -> List[Dict[str, Any]]:
    ref = settlement_id or reference_id
    if not ref:
        raise ValueError("Either settlement_id or reference_id must be provided to get_bank_transactions.")
    txns = database_service.get_bank_transactions(db, ref)
    return [_bank_txn_to_dict(t) for t in txns]

def _get_invoice_details_impl(db: Session, invoice_id: Optional[str] = None, order_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if invoice_id:
        invoice = database_service.get_invoice(db, invoice_id)
    elif order_id:
        invoice = database_service.get_invoice_by_order(db, order_id)
    else:
        raise ValueError("Either invoice_id or order_id must be provided to get_invoice_details.")
    return _invoice_to_dict(invoice)

def _get_tax_record_impl(db: Session, invoice_id: str) -> Optional[Dict[str, Any]]:
    tax = database_service.get_tax_record(db, invoice_id)
    return _tax_record_to_dict(tax)

def _get_reconciliation_result_impl(db: Session, case_id: str) -> Dict[str, Any]:
    res = reconcile_case(db, case_id)
    return res.to_dict()


# Map tool names to AgentTool objects containing metadata schemas

TOOLS: Dict[str, AgentTool] = {
    "get_payment_details": AgentTool(
        name="get_payment_details",
        description="Retrieve operational payment record details including amount, status, and associated order_id.",
        input_schema={"payment_id": "string"},
        output_schema={"payment_details": "object"},
        func=_get_payment_details_impl
    ),
    "get_order_details": AgentTool(
        name="get_order_details",
        description="Retrieve operational sales order details including status and amount.",
        input_schema={"order_id": "string"},
        output_schema={"order_details": "object"},
        func=_get_order_details_impl
    ),
    "get_refunds": AgentTool(
        name="get_refunds",
        description="Retrieve all refund records associated with a payment_id.",
        input_schema={"payment_id": "string"},
        output_schema={"refunds": "array"},
        func=_get_refunds_impl
    ),
    "get_settlement_details": AgentTool(
        name="get_settlement_details",
        description="Retrieve gateway settlement records for a payment_id or settlement_id, containing fee, tax, and net transfer amounts.",
        input_schema={"payment_id": "string (optional)", "settlement_id": "string (optional)"},
        output_schema={"settlement_details": "object"},
        func=_get_settlement_details_impl
    ),
    "get_bank_transactions": AgentTool(
        name="get_bank_transactions",
        description="Retrieve actual bank transaction deposits referencing a settlement_id or reference_id.",
        input_schema={"settlement_id": "string (optional)", "reference_id": "string (optional)"},
        output_schema={"bank_transactions": "array"},
        func=_get_bank_transactions_impl
    ),
    "get_invoice_details": AgentTool(
        name="get_invoice_details",
        description="Retrieve tax invoice details by invoice_id or associated order_id.",
        input_schema={"invoice_id": "string (optional)", "order_id": "string (optional)"},
        output_schema={"invoice_details": "object"},
        func=_get_invoice_details_impl
    ),
    "get_tax_record": AgentTool(
        name="get_tax_record",
        description="Retrieve government tax ledger record associated with an invoice_id.",
        input_schema={"invoice_id": "string"},
        output_schema={"tax_record": "object"},
        func=_get_tax_record_impl
    ),
    "get_reconciliation_result": AgentTool(
        name="get_reconciliation_result",
        description="Retrieve the deterministic reconciliation status, difference, and evidence for a specific case_id.",
        input_schema={"case_id": "string"},
        output_schema={"reconciliation_result": "object"},
        func=_get_reconciliation_result_impl
    )
}
