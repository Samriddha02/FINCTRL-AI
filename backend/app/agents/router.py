import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import Order, Payment
from app.reconciliation.models import ReconciliationResult
from app.agents.tools import TOOLS

logger = logging.getLogger("investigation_router")

STRATEGIES = {
    "EXACT_MATCH": {
        "required_tools": [],
        "optional_tools": [],
        "steps": ["Validate transaction alignment"]
    },
    "PARTIAL_REFUND": {
        "required_tools": ["get_payment_details", "get_refunds", "get_settlement_details"],
        "optional_tools": [],
        "steps": ["Inspect payment amount", "Inspect refunds records", "Inspect settlement net amount", "Verify refund net adjustment"]
    },
    "FEE_DIFFERENCE": {
        "required_tools": ["get_payment_details", "get_settlement_details"],
        "optional_tools": ["get_refunds"],
        "steps": ["Inspect payment amount", "Inspect settlement fee", "Calculate effective fee rate", "Determine whether fee is explained"]
    },
    "TIMING_DIFFERENCE": {
        "required_tools": ["get_payment_details", "get_settlement_details", "get_bank_transactions"],
        "optional_tools": [],
        "steps": ["Inspect settlement processed date", "Inspect bank posting date", "Calculate delay difference"]
    },
    "MISSING_SETTLEMENT": {
        "required_tools": ["get_payment_details", "get_settlement_details"],
        "optional_tools": [],
        "steps": ["Inspect payment amount", "Verify settlement non-existence"]
    },
    "DUPLICATE_TRANSACTION": {
        "required_tools": ["get_payment_details", "get_settlement_details", "get_bank_transactions"],
        "optional_tools": [],
        "steps": ["Inspect settlement details", "Inspect bank transaction records", "Identify duplicate transaction references"]
    },
    "AMOUNT_MISMATCH": {
        "required_tools": ["get_payment_details", "get_settlement_details", "get_refunds"],
        "optional_tools": [],
        "steps": ["Inspect payment details", "Inspect settlement gross amount", "Verify refund relationships"]
    },
    "TAX_MISMATCH": {
        "required_tools": ["get_invoice_details", "get_tax_record"],
        "optional_tools": [],
        "steps": ["Inspect invoice tax", "Inspect tax record tax amount", "Identify mismatch difference"]
    },
    "UNKNOWN_ADJUSTMENT": {
        "required_tools": ["get_payment_details", "get_settlement_details"],
        "optional_tools": [],
        "steps": ["Inspect settlement adjustment fields", "Identify unexplained gateway deductions"]
    },
    "CONFLICTING_RECORDS": {
        "required_tools": ["get_payment_details", "get_order_details"],
        "optional_tools": [],
        "steps": ["Inspect order status", "Inspect payment status", "Compare transactional state contradictions"]
    },
    "AMBIGUOUS_CASE": {
        "required_tools": ["get_payment_details", "get_settlement_details", "get_bank_transactions"],
        "optional_tools": [],
        "steps": ["Inspect settlement net amount", "Inspect candidate bank transactions", "Analyze reference ID structures"]
    }
}

def resolve_payment_id_from_case(db: Session, case_id: str) -> Optional[str]:
    """Helper to find payment_id associated with a case_id (order_id)."""
    order_id = case_id.replace("CASE-", "ORD-") if case_id.startswith("CASE-") else case_id
    order = db.query(Order).filter(Order.order_id == order_id).first()
    payment = None
    if order:
        payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()
    
    if not payment:
        payment_id = case_id.replace("CASE-", "PAY-") if case_id.startswith("CASE-") else case_id
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        
    return payment.payment_id if payment else None

def get_reconciliation_invoice_id(db: Session, case_id: str) -> Optional[str]:
    """Helper to find invoice_id associated with a case_id (order_id)."""
    order_id = case_id.replace("CASE-", "ORD-") if case_id.startswith("CASE-") else case_id
    from app.models import Invoice
    invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    return invoice.invoice_id if invoice else None

def build_investigation_context(
    db: Session,
    case_id: str,
    recon_result: ReconciliationResult,
    execution_logs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Applies the strategy planner/router to execute read-only tools and construct context."""
    reason_code = recon_result.reason_code.value
    strategy = STRATEGIES.get(reason_code, {
        "required_tools": ["get_payment_details", "get_settlement_details"],
        "optional_tools": [],
        "steps": ["Assess basic transaction records"]
    })

    # Find context IDs
    payment_id = resolve_payment_id_from_case(db, case_id)
    invoice_id = get_reconciliation_invoice_id(db, case_id)
    order_id = case_id.replace("CASE-", "ORD-") if case_id.startswith("CASE-") else case_id
    settlement_id = None
    
    # Pre-fetch settlement_id if possible
    if payment_id:
        from app.models import Settlement
        settlement = db.query(Settlement).filter(Settlement.payment_id == payment_id).first()
        if settlement:
            settlement_id = settlement.settlement_id

    evidence_records: List[Dict[str, Any]] = []
    
    # Helper to resolve arguments for tools
    def get_tool_args(tool_name: str) -> Dict[str, Any]:
        if tool_name == "get_payment_details":
            return {"payment_id": payment_id}
        elif tool_name == "get_order_details":
            return {"order_id": order_id}
        elif tool_name == "get_refunds":
            return {"payment_id": payment_id}
        elif tool_name == "get_settlement_details":
            return {"payment_id": payment_id, "settlement_id": settlement_id}
        elif tool_name == "get_bank_transactions":
            return {"settlement_id": settlement_id, "reference_id": settlement_id}
        elif tool_name == "get_invoice_details":
            return {"invoice_id": invoice_id, "order_id": order_id}
        elif tool_name == "get_tax_record":
            return {"invoice_id": invoice_id}
        elif tool_name == "get_reconciliation_result":
            return {"case_id": case_id}
        return {}

    failed_required_tools = []
    
    # Run required and optional tools
    for tool_name in strategy["required_tools"] + strategy["optional_tools"]:
        if tool_name not in TOOLS:
            logger.warning(f"Strategy references unknown tool: {tool_name}")
            if tool_name in strategy["required_tools"]:
                failed_required_tools.append(tool_name)
            continue
            
        args = get_tool_args(tool_name)
        # Skip executing if arguments are missing (e.g. payment_id not resolved)
        if not any(args.values()):
            if tool_name in strategy["required_tools"]:
                failed_required_tools.append(f"{tool_name} (missing args)")
            continue
            
        tool = TOOLS[tool_name]
        resp = tool.execute(db, args, execution_logs)
        if resp["success"] and resp["data"] is not None:
            if isinstance(resp["data"], list):
                for item in resp["data"]:
                    evidence_records.append({"source_tool": tool_name, "record": item})
            else:
                evidence_records.append({"source_tool": tool_name, "record": resp["data"]})
        else:
            if tool_name in strategy["required_tools"]:
                error_msg = resp.get("error", "unknown error")
                failed_required_tools.append(f"{tool_name} failed: {error_msg}")

    # Prepare evidence summary for LLM context
    serialized_evidence = []
    for item in evidence_records:
        source = item["source_tool"]
        record = item["record"]
        serialized_evidence.append(f"Source: {source} | Data: {record}")

    # Build context dictionary
    context = {
        "case_id": case_id,
        "deterministic_status": recon_result.status.value,
        "deterministic_reason_code": reason_code,
        "expected_amount": float(recon_result.expected_amount),
        "actual_amount": float(recon_result.actual_amount),
        "difference": float(recon_result.difference),
        "reconciliation_evidence": [
            {"source": e.source, "field": e.field, "value": e.value, "explanation": e.explanation}
            for e in recon_result.evidence
        ],
        "rule_evaluations": [
            {"rule_name": r.rule_name, "status": r.status, "expected_val": r.expected_val, "actual_val": r.actual_val, "difference": r.difference}
            for r in recon_result.rule_evaluations
        ],
        "evidence_records": evidence_records,
        "evidence_context_lines": serialized_evidence,
        "investigation_steps": strategy["steps"],
        "failed_required_tools": failed_required_tools
    }

    return context
