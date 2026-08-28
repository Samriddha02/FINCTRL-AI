from enum import Enum
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    AMBIGUOUS = "AMBIGUOUS"
    ERROR = "ERROR"


class ReasonCode(str, Enum):
    NONE = "NONE"
    EXACT_MATCH = "EXACT_MATCH"
    PARTIAL_REFUND = "PARTIAL_REFUND"
    FEE_DIFFERENCE = "FEE_DIFFERENCE"
    TIMING_DIFFERENCE = "TIMING_DIFFERENCE"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    TAX_MISMATCH = "TAX_MISMATCH"
    UNKNOWN_ADJUSTMENT = "UNKNOWN_ADJUSTMENT"
    CONFLICTING_RECORDS = "CONFLICTING_RECORDS"
    AMBIGUOUS_CASE = "AMBIGUOUS_CASE"


class EvidenceItem(BaseModel):
    source: str
    record_id: str
    field: str
    value: str
    explanation: str


class RuleEvaluation(BaseModel):
    rule_name: str
    status: str  # PASS, FAIL, SKIPPED
    expected_val: str
    actual_val: str
    difference: str


class ReconciliationResult(BaseModel):
    case_id: str
    status: ReconciliationStatus
    reason_code: ReasonCode
    expected_amount: Decimal
    actual_amount: Decimal
    difference: Decimal
    currency: str = "INR"
    confidence: float
    needs_investigation: bool
    auto_resolvable: bool
    evidence: List[EvidenceItem] = Field(default_factory=list)
    rule_evaluations: List[RuleEvaluation] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary format."""
        return {
            "case_id": self.case_id,
            "status": self.status.value,
            "reason_code": self.reason_code.value,
            "expected_amount": f"{self.expected_amount:.2f}",
            "actual_amount": f"{self.actual_amount:.2f}",
            "difference": f"{self.difference:.2f}",
            "currency": self.currency,
            "confidence": self.confidence,
            "needs_investigation": self.needs_investigation,
            "auto_resolvable": self.auto_resolvable,
            "evidence": [item.model_dump() for item in self.evidence],
            "rule_evaluations": [eval_item.model_dump() for eval_item in self.rule_evaluations],
        }
