import datetime
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.agents.providers import get_llm_provider, LLMProvider
from app.tax_matching.schemas import TaxMatchResult, TaxBatchMatchSummary, TaxMatchStatus
from app.tax_matching.matcher import match_tax_line, match_all_tax_lines
from app.tax_matching.validator import validate_tax_explanation
from app.services.audit_service import log_audit_event
from app.services.review_service import create_or_get_review

logger = logging.getLogger("tax_controller")

tax_matches_by_id: Dict[str, TaxMatchResult] = {}

SYSTEM_TAX_PROMPT = """
You are the FINCTRL Tax Control Specialist.
Your job is to explain the deterministic tax matching result concisely and accurately based ONLY on authoritative database records.

RULES:
1. Reference invoice tax amount, ledger tax amount, tax rates, taxable amounts, and differences accurately.
2. Never invent, alter, or guess tax values. Use only the provided tax facts.
3. Keep explanations professional, clear, and direct.
"""


class TaxMatchController:
    """Orchestrates deterministic tax matching, LLM explanation, validation, Phase 8 review integration, and audit logging."""

    def __init__(self, db: Session, provider: Optional[LLMProvider] = None):
        self.db = db
        self.provider = provider or get_llm_provider()

    def process_tax_match(self, invoice_id: str) -> TaxMatchResult:
        # Audit event for request
        log_audit_event(
            db=self.db,
            case_id=invoice_id,
            event_type="TAX_MATCH_REQUESTED",
            actor_type="SYSTEM",
            details={"invoice_id": invoice_id}
        )

        # 1. Execute Deterministic Tax Line Matcher
        res: TaxMatchResult = match_tax_line(self.db, invoice_id)

        # 2. Phase 8 Human Review Integration (if mismatch or review needed)
        if res.needs_review:
            self._trigger_human_review_if_needed(res)

        # 3. Generate LLM Explanation
        prompt = self._build_explanation_prompt(res)
        explanation_text = ""
        try:
            explanation_text = self.provider.generate_text(prompt=prompt, system_prompt=SYSTEM_TAX_PROMPT)
        except Exception as e:
            logger.warning(f"LLM text generation failed: {e}. Falling back to deterministic explanation.")
            explanation_text = self._build_deterministic_explanation(res)

        if "mock text response" in explanation_text.lower() or not explanation_text.strip():
            explanation_text = self._build_deterministic_explanation(res)

        # 4. Validate Explanation
        is_valid, errors = validate_tax_explanation(explanation_text, res)
        if not is_valid:
            logger.warning(f"Tax explanation failed validation: {errors}")
            res.warnings.extend(errors)
            explanation_text = self._build_deterministic_explanation(res)

        res.explanation = explanation_text

        # 5. Save and Audit Log
        tax_matches_by_id[res.match_id] = res

        log_audit_event(
            db=self.db,
            case_id=invoice_id,
            event_type="TAX_MATCH_COMPLETED",
            actor_type="SYSTEM",
            details={
                "match_id": res.match_id,
                "invoice_id": res.invoice_id,
                "tax_id": res.tax_id,
                "status": res.status.value,
                "reason_code": res.reason_code.value,
                "difference": res.difference,
                "needs_review": res.needs_review
            },
            result=res.status.value
        )

        return res

    def process_batch_tax_match(self) -> TaxBatchMatchSummary:
        """Executes batch tax matching across all invoices in database."""
        log_audit_event(
            db=self.db,
            case_id="TAX_BATCH",
            event_type="TAX_MATCH_REQUESTED",
            actor_type="SYSTEM",
            details={"batch": True}
        )

        batch_summary: TaxBatchMatchSummary = match_all_tax_lines(self.db)

        # Process each result for persistence and explanation
        for res in batch_summary.results:
            if res.needs_review:
                self._trigger_human_review_if_needed(res)
            res.explanation = self._build_deterministic_explanation(res)
            tax_matches_by_id[res.match_id] = res

        log_audit_event(
            db=self.db,
            case_id="TAX_BATCH",
            event_type="TAX_MATCH_COMPLETED",
            actor_type="SYSTEM",
            details={
                "total_checked": batch_summary.total_invoices_checked,
                "exact_matches": batch_summary.exact_matches,
                "amount_mismatches": batch_summary.amount_mismatches,
                "missing_records": batch_summary.missing_records
            },
            result="COMPLETED"
        )

        return batch_summary

    def _trigger_human_review_if_needed(self, res: TaxMatchResult) -> None:
        """Integrates tax mismatch detection with Phase 8 Human Review system."""
        try:
            # Map invoice to case_id
            case_id = f"CASE-{res.invoice_id.replace('INV-', '')}"
            from app.agents.schemas import InvestigationResult, InvestigationStatus, AnalysisSource
            mock_inv = InvestigationResult(
                investigation_id=f"INV-TAX-{res.match_id}",
                case_id=case_id,
                investigation_status=InvestigationStatus.ESCALATED,
                deterministic_status="MISMATCH",
                deterministic_reason_code="TAX_MISMATCH",
                summary=f"Tax Control Mismatch detected for Invoice {res.invoice_id}: {res.status.value}",
                root_cause=f"Tax variance of INR {res.difference:.2f} ({res.reason_code.value})",
                root_cause_confidence=res.confidence,
                facts=[],
                requires_human_review=True,
                warnings=res.warnings,
                analysis_source=AnalysisSource.DETERMINISTIC
            )
            create_or_get_review(self.db, case_id, mock_inv)
            log_audit_event(
                db=self.db,
                case_id=case_id,
                event_type="TAX_REVIEW_CREATED",
                actor_type="SYSTEM",
                details={"match_id": res.match_id, "invoice_id": res.invoice_id, "status": res.status.value}
            )
        except Exception as e:
            logger.warning(f"Could not trigger Phase 8 Human Review for tax match '{res.match_id}': {e}")

    def _build_explanation_prompt(self, res: TaxMatchResult) -> str:
        return f"""
EXPLAIN THE FOLLOWING DETERMINISTIC TAX MATCHING RESULT:

Invoice ID: {res.invoice_id}
Tax Record ID: {res.tax_id}
Status: {res.status.value}
Reason Code: {res.reason_code.value}

INVOICE TAX DATA:
Taxable Amount: INR {res.invoice_taxable_amount}
Tax Rate: {res.invoice_tax_rate * 100 if res.invoice_tax_rate else 0}%
Tax Amount: INR {res.invoice_tax_amount}

LEDGER TAX DATA:
Taxable Amount: INR {res.ledger_taxable_amount}
Tax Rate: {res.ledger_tax_rate * 100 if res.ledger_tax_rate else 0}%
Tax Amount: INR {res.ledger_tax_amount}

EXPECTED TAX & DIFFERENCE:
Expected Tax Amount: INR {res.expected_tax_amount}
Difference (Invoice - Ledger): INR {res.difference}

Explain the tax match result concisely in 2-3 sentences.
"""

    def _build_deterministic_explanation(self, res: TaxMatchResult) -> str:
        if res.status == TaxMatchStatus.EXACT_MATCH:
            return (
                f"Invoice {res.invoice_id} exactly matches TaxRecord {res.tax_id}. "
                f"Recorded tax amount of INR {res.invoice_tax_amount:,.2f} at rate {res.invoice_tax_rate * 100:.1f}% "
                f"matches the tax ledger entries with 0.00 difference."
            )
        elif res.status == TaxMatchStatus.MISSING_TAX_RECORD:
            return (
                f"Invoice {res.invoice_id} (tax amount INR {res.invoice_tax_amount:,.2f}) has no corresponding "
                f"TaxRecord in the tax ledger. Human review is required."
            )
        elif res.status == TaxMatchStatus.DUPLICATE_TAX_RECORD:
            return (
                f"Invoice {res.invoice_id} has multiple duplicate TaxRecord entries in the tax ledger. "
                f"Manual review is required to resolve tax ledger ambiguity."
            )
        elif res.status == TaxMatchStatus.AMOUNT_MISMATCH:
            return (
                f"Tax amount mismatch detected for Invoice {res.invoice_id}: "
                f"Invoice recorded tax is INR {res.invoice_tax_amount:,.2f} versus TaxRecord {res.tax_id} tax of INR {res.ledger_tax_amount:,.2f}, "
                f"yielding a variance of INR {res.difference:,.2f}."
            )
        elif res.status == TaxMatchStatus.RATE_MISMATCH:
            return (
                f"Tax rate mismatch detected for Invoice {res.invoice_id}: "
                f"Invoice applied rate of {res.invoice_tax_rate * 100:.1f}% versus TaxRecord rate of {res.ledger_tax_rate * 100:.1f}%."
            )
        elif res.status == TaxMatchStatus.TAXABLE_AMOUNT_MISMATCH:
            return (
                f"Taxable base amount mismatch for Invoice {res.invoice_id}: "
                f"Invoice subtotal is INR {res.invoice_taxable_amount:,.2f} versus TaxRecord taxable base of INR {res.ledger_taxable_amount:,.2f}."
            )
        elif res.status == TaxMatchStatus.CALCULATION_MISMATCH:
            return (
                f"Tax calculation mismatch for Invoice {res.invoice_id}: "
                f"TaxRecord recorded tax of INR {res.ledger_tax_amount:,.2f} differs from mathematically calculated expected tax of INR {res.expected_tax_amount:,.2f}."
            )
        else:
            return f"Tax matching for Invoice {res.invoice_id} resulted in status {res.status.value}."
