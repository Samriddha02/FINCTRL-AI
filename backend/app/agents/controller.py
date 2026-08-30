import logging
import uuid
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.reconciliation.engine import reconcile_case
from app.reconciliation.models import ReconciliationResult
from app.agents.schemas import (
    InvestigationResult,
    InvestigationStatus,
    AnalysisSource,
    ToolCallRecord,
    FactRecord,
    InferenceRecord,
    RecommendedAction,
    ActionPriority
)
from app.agents.providers import get_llm_provider, LLMProvider
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.router import build_investigation_context
from app.agents.validator import validate_facts_and_safety

logger = logging.getLogger("investigation_controller")

# Limits
MAX_TOOL_CALLS_PER_INVESTIGATION = 10
MAX_INVESTIGATION_STEPS = 8

# In-memory persistence stores
investigations_by_case: Dict[str, List[InvestigationResult]] = {}
investigations_by_id: Dict[str, InvestigationResult] = {}

class AgentInvestigationController:
    """Orchestrates the AI Investigation Agent state machine and validation."""
    def __init__(self, db: Session, provider: Optional[LLMProvider] = None):
        self.db = db
        self.provider = provider or get_llm_provider()
        self.investigation_id = str(uuid.uuid4())
        self.state_history: List[str] = []
        self.execution_logs: List[Dict[str, Any]] = []

    def _transition_to(self, state: str) -> None:
        """Transitions state explicitly and logs step."""
        logger.info(f"Investigation {self.investigation_id} entering state: {state}")
        self.state_history.append(state)

    def run_investigation(self, case_id: str) -> InvestigationResult:
        self._transition_to("START")
        
        # 1. Load reconciliation result
        self._transition_to("LOAD_RECONCILIATION")
        recon_result = reconcile_case(self.db, case_id)
        
        # 2. Assess if investigation is needed
        self._transition_to("ASSESS_CASE")
        if recon_result.status.value == "MATCHED" and recon_result.reason_code.value == "EXACT_MATCH":
            # For EXACT_MATCH, return deterministic explanation directly without invoking LLM
            result = InvestigationResult(
                investigation_id=self.investigation_id,
                case_id=case_id,
                investigation_status=InvestigationStatus.COMPLETED,
                deterministic_status="MATCHED",
                deterministic_reason_code="EXACT_MATCH",
                summary="Transaction reconciled successfully. Expected and actual amounts match perfectly.",
                root_cause="No discrepancy found.",
                root_cause_confidence=1.0,
                facts=[
                    FactRecord(key="payment_amount", value=float(recon_result.expected_amount), source="Payment"),
                    FactRecord(key="settlement_amount", value=float(recon_result.actual_amount), source="Settlement"),
                    FactRecord(key="difference", value=0.0, source="Calculation")
                ],
                inferences=[],
                evidence=[],
                alternative_explanations=[],
                recommended_actions=[],
                auto_resolution_eligible=True,
                requires_human_review=False,
                investigation_steps=self.state_history.copy(),
                tool_calls=[],
                warnings=[],
                analysis_source=AnalysisSource.DETERMINISTIC
            )
            self._save_result(result)
            return result

        if recon_result.status.value == "ERROR":
            # Deterministic error
            result = InvestigationResult(
                investigation_id=self.investigation_id,
                case_id=case_id,
                investigation_status=InvestigationStatus.FAILED,
                deterministic_status="ERROR",
                deterministic_reason_code="NONE",
                summary="Deterministic reconciliation returned error. Operational payment record not found.",
                root_cause="Missing operational records.",
                root_cause_confidence=1.0,
                facts=[],
                inferences=[],
                evidence=[],
                alternative_explanations=[],
                recommended_actions=[
                    RecommendedAction(
                        action="Locate operational payment records for this case",
                        priority=ActionPriority.HIGH,
                        reason="Database lookup returned no results"
                    )
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                investigation_steps=self.state_history.copy(),
                tool_calls=[],
                warnings=["Deterministic reconciliation engine error."],
                analysis_source=AnalysisSource.DETERMINISTIC
            )
            self._save_result(result)
            return result

        # 3. Gather evidence via Read-Only Strategy Router
        self._transition_to("GATHER_EVIDENCE")
        context = build_investigation_context(self.db, case_id, recon_result, self.execution_logs)

        # Enforce Tool Call Limit
        if len(self.execution_logs) > MAX_TOOL_CALLS_PER_INVESTIGATION:
            self._transition_to("ESCALATE")
            result = self._build_escalation_result(
                case_id, recon_result, 
                "Tool call limit exceeded during evidence collection.",
                ["MAX_TOOL_CALLS limit hit."]
            )
            self._save_result(result)
            return result

        # 4. Analyze via LLM provider
        self._transition_to("ANALYZE")
        
        prompt = self._build_llm_prompt(context)
        validation_errors: List[str] = []
        result_obj: Optional[InvestigationResult] = None
        
        # Enforce step limits: we loop at most once for retry
        for attempt in range(2):
            if attempt > 0:
                self._transition_to("ANALYZE_RETRY")
                # Append validation error details to prompt to guide retry
                prompt += f"\n\nCRITICAL WARNING: The previous response failed validation with these errors: {validation_errors}. Fix these issues."

            try:
                result_obj = self.provider.generate_structured_response(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    response_schema=InvestigationResult
                )
                
                # Check for step limits
                if len(self.state_history) > MAX_INVESTIGATION_STEPS:
                    self._transition_to("ESCALATE")
                    result = self._build_escalation_result(
                        case_id, recon_result,
                        "Maximum agent investigation steps limit reached.",
                        ["MAX_STEPS limit hit."]
                    )
                    self._save_result(result)
                    return result
                
                # 5. Validate facts and safety constraints
                self._transition_to("VALIDATE")
                validation_errors = validate_facts_and_safety(result_obj, context)
                if not validation_errors:
                    break  # Valid result obtained
            except Exception as e:
                logger.error(f"LLM call or parsing failed on attempt {attempt + 1}: {e}")
                validation_errors = [f"LLM Generation failure: {str(e)}"]

        # If still invalid after retry, escalate or return failed
        if validation_errors:
            # Fallback to deterministic summary without breaking the app
            self._transition_to("ESCALATE")
            warns = [f"LLM output failed validation: {err}" for err in validation_errors]
            result = self._build_escalation_result(
                case_id, recon_result,
                f"AI investigation failed validation. Fallback to deterministic reconciliation summary.",
                warns
            )
            self._save_result(result)
            return result

        # 6. Form Root Cause and Recommend Actions
        self._transition_to("FORM_ROOT_CAUSE")
        self._transition_to("RECOMMEND_ACTION")

        # 7. Safety check
        self._transition_to("SAFETY_CHECK")
        
        # Populate final properties
        result_obj.investigation_id = self.investigation_id
        result_obj.case_id = case_id
        result_obj.deterministic_status = recon_result.status.value
        result_obj.deterministic_reason_code = recon_result.reason_code.value
        result_obj.analysis_source = AnalysisSource.LLM
        
        # Append trace information
        result_obj.investigation_steps = self.state_history.copy()
        
        # Convert execution logs to ToolCallRecord Pydantic models
        serialized_tool_calls = []
        for log in self.execution_logs:
            serialized_tool_calls.append(ToolCallRecord(
                tool_name=log["tool_name"],
                arguments=log["arguments"],
                timestamp=log["timestamp"],
                result_summary=log["result_summary"],
                success=log["success"],
                error=log.get("error")
            ))
        result_obj.tool_calls = serialized_tool_calls

        # Check if the LLM output requires human review
        if result_obj.requires_human_review:
            self._transition_to("ESCALATE")
            result_obj.investigation_status = InvestigationStatus.ESCALATED
        else:
            self._transition_to("COMPLETE")
            result_obj.investigation_status = InvestigationStatus.COMPLETED

        # Ensure correct status/steps are stored in history
        result_obj.investigation_steps = self.state_history.copy()
        self._save_result(result_obj)
        return result_obj

    def _build_llm_prompt(self, context: Dict[str, Any]) -> str:
        """Constructs prompt containing context, evidence, and validation directives."""
        return f"""
Investigate the following reconciliation case.

CASE INFORMATION:
Case ID: {context['case_id']}
Deterministic Status: {context['deterministic_status']}
Deterministic Reason Code: {context['deterministic_reason_code']}
Expected Amount: ₹{context['expected_amount']}
Actual Amount: ₹{context['actual_amount']}
Difference: ₹{context['difference']}

DETERMINISTIC ENGINE EVIDENCE:
{json_dumps(context['reconciliation_evidence'])}

RULE EVALUATIONS:
{json_dumps(context['rule_evaluations'])}

OPERATIONAL EVIDENCE LOGS (GROUNDED DATA):
{json_dumps(context['evidence_context_lines'])}

INVESTIGATION PLAN TO FOLLOW:
{json_dumps(context['investigation_steps'])}

Generate the structured response containing the investigation result matching the required schema. Keep rationale concise and factual.
"""

    def _build_escalation_result(
        self,
        case_id: str,
        recon_result: ReconciliationResult,
        error_msg: str,
        warnings: List[str]
    ) -> InvestigationResult:
        """Creates a fallback investigation result using deterministic data when AI fails."""
        # Convert execution logs to ToolCallRecord Pydantic models
        serialized_tool_calls = []
        for log in self.execution_logs:
            serialized_tool_calls.append(ToolCallRecord(
                tool_name=log["tool_name"],
                arguments=log["arguments"],
                timestamp=log["timestamp"],
                result_summary=log["result_summary"],
                success=log["success"],
                error=log.get("error")
            ))

        return InvestigationResult(
            investigation_id=self.investigation_id,
            case_id=case_id,
            investigation_status=InvestigationStatus.ESCALATED,
            deterministic_status=recon_result.status.value,
            deterministic_reason_code=recon_result.reason_code.value,
            summary=f"Reconciliation investigation escalated. {error_msg}",
            root_cause="Escalation due to validation error, step limit, or LLM unavailability.",
            root_cause_confidence=0.0,
            facts=[
                FactRecord(key="payment_amount", value=float(recon_result.expected_amount), source="Payment"),
                FactRecord(key="settlement_amount", value=float(recon_result.actual_amount), source="Settlement"),
                FactRecord(key="difference", value=float(recon_result.difference), source="Calculation")
            ],
            inferences=[],
            evidence=[],
            alternative_explanations=[],
            recommended_actions=[
                RecommendedAction(
                    action="Manually audit financial records for discrepancies.",
                    priority=ActionPriority.HIGH,
                    reason=error_msg
                )
            ],
            auto_resolution_eligible=False,
            requires_human_review=True,
            investigation_steps=self.state_history.copy(),
            tool_calls=serialized_tool_calls,
            warnings=warnings,
            analysis_source=AnalysisSource.DETERMINISTIC
        )

    def _save_result(self, result: InvestigationResult) -> None:
        """Save result to thread-safe memory lists/dicts for query."""
        investigations_by_id[result.investigation_id] = result
        if result.case_id not in investigations_by_case:
            investigations_by_case[result.case_id] = []
        investigations_by_case[result.case_id].append(result)


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, indent=2)
