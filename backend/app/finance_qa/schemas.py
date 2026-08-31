import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QAStatus(str, Enum):
    ANSWERED = "ANSWERED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNSUPPORTED = "UNSUPPORTED"
    NO_DATA = "NO_DATA"
    FAILED = "FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class QueryType(str, Enum):
    PAYMENT_QUERY = "PAYMENT_QUERY"
    ORDER_QUERY = "ORDER_QUERY"
    REFUND_QUERY = "REFUND_QUERY"
    SETTLEMENT_QUERY = "SETTLEMENT_QUERY"
    BANK_TRANSACTION_QUERY = "BANK_TRANSACTION_QUERY"
    INVOICE_QUERY = "INVOICE_QUERY"
    TAX_QUERY = "TAX_QUERY"
    RECONCILIATION_QUERY = "RECONCILIATION_QUERY"
    AGGREGATION_QUERY = "AGGREGATION_QUERY"
    CROSS_ENTITY_QUERY = "CROSS_ENTITY_QUERY"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"


class QAFactRecord(BaseModel):
    key: str = Field(description="The property or metric name, e.g., payment_amount, tax_amount")
    value: Any = Field(description="The authoritative value retrieved from database")
    source: str = Field(description="Database record source, e.g., Payment PAY-00001")
    entity_type: Optional[str] = Field(default=None, description="Entity type e.g. payment, invoice")
    entity_id: Optional[str] = Field(default=None, description="Business ID e.g. PAY-00001")


class QACalculation(BaseModel):
    calculation_name: str = Field(description="Name of the deterministic calculation")
    formula: str = Field(description="Formula or operation executed")
    value: Any = Field(description="Calculated numeric value (calculated using Decimal)")
    source_facts: List[str] = Field(default_factory=list, description="Keys of facts used in calculation")


class FinanceQARequest(BaseModel):
    question: str = Field(description="Natural language financial question")


class FinanceQAResult(BaseModel):
    query_id: str = Field(description="Unique query identifier (QA-...)")
    question: str = Field(description="Original user question")
    status: QAStatus = Field(description="Outcome status of the Q&A process")
    answer: str = Field(description="Grounded natural language answer or clarification text")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    facts: List[QAFactRecord] = Field(default_factory=list, description="Authoritative factual records retrieved")
    calculations: List[QACalculation] = Field(default_factory=list, description="Deterministic calculations performed")
    citations: List[str] = Field(default_factory=list, description="Citations to authoritative database records")
    warnings: List[str] = Field(default_factory=list, description="Warnings or validation messages")
    query_type: QueryType = Field(default=QueryType.UNSUPPORTED_QUERY, description="Classified question category")
    entities: List[str] = Field(default_factory=list, description="Entities referenced in question/answer")
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat(), description="ISO timestamp")
