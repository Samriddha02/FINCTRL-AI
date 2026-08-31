import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TaxMatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    RATE_MISMATCH = "RATE_MISMATCH"
    TAXABLE_AMOUNT_MISMATCH = "TAXABLE_AMOUNT_MISMATCH"
    CALCULATION_MISMATCH = "CALCULATION_MISMATCH"
    MISSING_TAX_RECORD = "MISSING_TAX_RECORD"
    DUPLICATE_TAX_RECORD = "DUPLICATE_TAX_RECORD"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"


class TaxReasonCode(str, Enum):
    TAX_EXACT_MATCH = "TAX_EXACT_MATCH"
    TAX_AMOUNT_MISMATCH = "TAX_AMOUNT_MISMATCH"
    TAX_RATE_MISMATCH = "TAX_RATE_MISMATCH"
    TAXABLE_AMOUNT_MISMATCH = "TAXABLE_AMOUNT_MISMATCH"
    TAX_CALCULATION_MISMATCH = "TAX_CALCULATION_MISMATCH"
    MISSING_TAX_RECORD = "MISSING_TAX_RECORD"
    DUPLICATE_TAX_RECORD = "DUPLICATE_TAX_RECORD"
    AMBIGUOUS_TAX_RECORD = "AMBIGUOUS_TAX_RECORD"


class TaxRuleEvaluation(BaseModel):
    rule_name: str = Field(description="Name of the deterministic tax rule evaluated")
    expected_val: str = Field(description="Expected authoritative value")
    actual_val: str = Field(description="Actual ledger value")
    difference: str = Field(default="0.00", description="Numeric difference")
    status: str = Field(description="PASS or FAIL")


class TaxEvidenceItem(BaseModel):
    source: str = Field(description="Source entity e.g., Invoice, TaxRecord")
    entity_id: str = Field(description="Business ID e.g., INV-00001, TAX-00001")
    field: str = Field(description="Field name e.g., tax_amount, tax_rate")
    value: str = Field(description="String representation of value")


class TaxMatchResult(BaseModel):
    match_id: str = Field(description="Unique tax match identifier (TM-...)")
    invoice_id: str = Field(description="Invoice business ID")
    tax_id: Optional[str] = Field(default=None, description="Linked tax record business ID")
    status: TaxMatchStatus = Field(description="Determined tax matching status")
    reason_code: TaxReasonCode = Field(description="Determined tax matching reason code")
    
    invoice_taxable_amount: Optional[float] = Field(default=None, description="Invoice subtotal / taxable amount")
    ledger_taxable_amount: Optional[float] = Field(default=None, description="TaxRecord taxable amount")
    
    invoice_tax_amount: Optional[float] = Field(default=None, description="Invoice tax amount")
    ledger_tax_amount: Optional[float] = Field(default=None, description="TaxRecord tax amount")
    
    invoice_tax_rate: Optional[float] = Field(default=None, description="Invoice tax rate")
    ledger_tax_rate: Optional[float] = Field(default=None, description="TaxRecord tax rate")
    
    expected_tax_amount: Optional[float] = Field(default=None, description="Calculated expected tax amount (taxable * rate)")
    difference: float = Field(default=0.00, description="Tax amount difference (invoice_tax - ledger_tax)")
    
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Deterministic certainty score")
    needs_review: bool = Field(default=False, description="Whether human review is required")
    
    evidence: List[TaxEvidenceItem] = Field(default_factory=list, description="Authoritative database evidence items")
    rule_evaluations: List[TaxRuleEvaluation] = Field(default_factory=list, description="Structured rule evaluation logs")
    warnings: List[str] = Field(default_factory=list, description="Warnings or notes")
    explanation: str = Field(default="", description="Natural-language explanation of the tax match result")
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat(), description="ISO timestamp")


class TaxBatchMatchSummary(BaseModel):
    total_invoices_checked: int = Field(description="Total count of invoices processed")
    exact_matches: int = Field(description="Count of exact tax matches")
    amount_mismatches: int = Field(description="Count of tax amount mismatches")
    rate_mismatches: int = Field(description="Count of tax rate mismatches")
    taxable_amount_mismatches: int = Field(description="Count of taxable amount mismatches")
    calculation_mismatches: int = Field(description="Count of tax calculation mismatches")
    missing_records: int = Field(description="Count of invoices missing tax records")
    duplicate_records: int = Field(description="Count of duplicate tax records")
    results: List[TaxMatchResult] = Field(default_factory=list, description="Individual tax match results")
