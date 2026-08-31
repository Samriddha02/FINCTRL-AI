import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.agents.tools import validate_id
from app.finance_qa.schemas import QueryType

logger = logging.getLogger("qa_router")

# Regex pattern for extracting FINCTRL business IDs
ID_EXTRACTION_PATTERN = re.compile(
    r"\b(CUST|ORD|PAY|REF|SETTL|BTXN|BANK|INV|TAX|CASE|REV|AUD)-\d+\b",
    re.IGNORECASE
)

# Out-of-scope keywords for unsupported query detection
UNSUPPORTED_KEYWORDS = [
    r"\binvest(ment|ing)?\b",
    r"\bstock(s)?\b",
    r"\bcrypto(currency)?\b",
    r"\blegal advice\b",
    r"\btax advice\b",
    r"\brecipe\b",
    r"\bweather\b",
    r"\bwho are you\b",
    r"\bhello\b",
    r"\bhi\b",
    r"\bhow are you\b",
    r"\bmodify\b",
    r"\bdelete\b",
    r"\bupdate\b",
    r"\bchange payment\b",
    r"\bdrop table\b",
    r"\binsert into\b",
    r"\bselect \* from\b",
    r"\bunion select\b",
    r"\bexec(ute)?\b",
    r"'\s*or\s*'",
    r"\bor\b\s*'1'\s*=\s*'1",
    r"--",
    r"/\*",
    r"\.\./",
    r"\.\.\\"
]

# Specific entity detail keywords that require an ID
ENTITY_DETAIL_KEYWORDS = [
    r"\bpayment\b", r"\border\b", r"\brefund\b", r"\bsettlement\b",
    r"\binvoice\b", r"\btax record\b", r"\btax ledger\b", r"\bcase\b"
]

# Aggregation keywords
AGGREGATION_KEYWORDS = [
    r"\bhow many\b", r"\btotal\b", r"\bsum of\b", r"\bcount of\b",
    r"\bcases require investigation\b", r"\bneeding investigation\b"
]


class RouteResult(BaseModel):
    query_type: QueryType
    extracted_ids: Dict[str, List[str]]
    entities_mentioned: List[str]
    requires_clarification: bool = False
    clarification_message: Optional[str] = None
    is_unsupported: bool = False
    unsupported_message: Optional[str] = None
    is_aggregation: bool = False
    aggregation_target: Optional[str] = None


def route_finance_question(question: str) -> RouteResult:
    """Deterministically classifies user question and extracts entities & IDs."""
    if not question or not question.strip():
        return RouteResult(
            query_type=QueryType.AMBIGUOUS_QUERY,
            extracted_ids={},
            entities_mentioned=[],
            requires_clarification=True,
            clarification_message="Please enter a valid financial question."
        )

    lower_q = question.lower()

    # 1. Check for out-of-scope or unsupported requests
    for kw in UNSUPPORTED_KEYWORDS:
        if re.search(kw, lower_q):
            return RouteResult(
                query_type=QueryType.UNSUPPORTED_QUERY,
                extracted_ids={},
                entities_mentioned=[],
                is_unsupported=True,
                unsupported_message=(
                    "FINCTRL Finance Assistant only answers factual operational finance questions based on "
                    "authoritative database records. We cannot provide personal advice, general conversation, "
                    "or execute database write operations."
                )
            )

    # 2. Extract and validate IDs
    matches = ID_EXTRACTION_PATTERN.findall(question)
    raw_found = ID_EXTRACTION_PATTERN.finditer(question)
    
    extracted_ids: Dict[str, List[str]] = {}
    valid_id_list: List[str] = []

    for match in raw_found:
        id_str = match.group(0).upper()
        # Validate ID using Phase 6 security logic
        try:
            validate_id(id_str)
            prefix = id_str.split("-")[0]
            if prefix not in extracted_ids:
                extracted_ids[prefix] = []
            if id_str not in extracted_ids[prefix]:
                extracted_ids[prefix].append(id_str)
            valid_id_list.append(id_str)
        except ValueError as e:
            logger.warning(f"Extracted ID '{id_str}' failed security validation: {e}")
            return RouteResult(
                query_type=QueryType.UNSUPPORTED_QUERY,
                extracted_ids={},
                entities_mentioned=[],
                is_unsupported=True,
                unsupported_message=f"Security Alert: Invalid identifier format detected in question."
            )

    # 3. Check for Aggregation queries
    is_aggregation = any(re.search(kw, lower_q) for kw in AGGREGATION_KEYWORDS)
    if is_aggregation:
        agg_target = "payments"
        if "settlement" in lower_q:
            agg_target = "settlements"
        elif "investigation" in lower_q or "case" in lower_q:
            agg_target = "cases_needing_investigation"
        elif "payment" in lower_q:
            agg_target = "payments"

        return RouteResult(
            query_type=QueryType.AGGREGATION_QUERY,
            extracted_ids=extracted_ids,
            entities_mentioned=list(extracted_ids.keys()),
            is_aggregation=True,
            aggregation_target=agg_target
        )

    # 4. Check for Ambiguous queries (Entity mentioned but no ID provided)
    if not valid_id_list:
        has_entity_mention = any(re.search(kw, lower_q) for kw in ENTITY_DETAIL_KEYWORDS)
        if has_entity_mention or "status" in lower_q or "captured" in lower_q or "settled" in lower_q:
            suggested_prefix = "PAY-00001"
            if "order" in lower_q:
                suggested_prefix = "ORD-00001"
            elif "invoice" in lower_q:
                suggested_prefix = "INV-00001"
            elif "tax" in lower_q:
                suggested_prefix = "INV-00001 or TAX-00001"
            elif "case" in lower_q or "reconcil" in lower_q:
                suggested_prefix = "CASE-00001"

            return RouteResult(
                query_type=QueryType.AMBIGUOUS_QUERY,
                extracted_ids={},
                entities_mentioned=[],
                requires_clarification=True,
                clarification_message=f"Which record would you like me to check? Please provide a specific ID such as {suggested_prefix}."
            )
        else:
            return RouteResult(
                query_type=QueryType.UNSUPPORTED_QUERY,
                extracted_ids={},
                entities_mentioned=[],
                is_unsupported=True,
                unsupported_message=(
                    "Your question does not reference a specific operational financial record (such as PAY-00001, ORD-00001, INV-00001, or CASE-00001) "
                    "or a supported aggregation request. Please specify a valid record identifier."
                )
            )

    # 5. Classify based on extracted IDs and query context
    num_prefixes = len(extracted_ids.keys())
    if num_prefixes > 1 or "compare" in lower_q or "versus" in lower_q or "vs" in lower_q:
        query_type = QueryType.CROSS_ENTITY_QUERY
    elif "CASE" in extracted_ids or "reconcil" in lower_q or "mismatch" in lower_q:
        query_type = QueryType.RECONCILIATION_QUERY
    elif "TAX" in extracted_ids or "tax" in lower_q:
        query_type = QueryType.TAX_QUERY
    elif "INV" in extracted_ids or "invoice" in lower_q:
        query_type = QueryType.INVOICE_QUERY
    elif "BTXN" in extracted_ids or "BANK" in extracted_ids or "bank" in lower_q:
        query_type = QueryType.BANK_TRANSACTION_QUERY
    elif "SETTL" in extracted_ids or "settle" in lower_q:
        query_type = QueryType.SETTLEMENT_QUERY
    elif "REF" in extracted_ids or "refund" in lower_q:
        query_type = QueryType.REFUND_QUERY
    elif "ORD" in extracted_ids or "order" in lower_q:
        query_type = QueryType.ORDER_QUERY
    elif "PAY" in extracted_ids or "payment" in lower_q:
        query_type = QueryType.PAYMENT_QUERY
    else:
        query_type = QueryType.CROSS_ENTITY_QUERY

    return RouteResult(
        query_type=query_type,
        extracted_ids=extracted_ids,
        entities_mentioned=list(extracted_ids.keys())
    )
