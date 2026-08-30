from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InvestigationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    INVESTIGATING = "INVESTIGATING"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class AnalysisSource(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LLM = "LLM"


class FactRecord(BaseModel):
    key: str = Field(description="The category of the fact, e.g. payment_amount, refund_amount")
    value: Any = Field(description="The concrete value of the fact")
    source: str = Field(description="The source record this fact was derived from, e.g. Payment PAY-001")


class InferenceRecord(BaseModel):
    inference: str = Field(description="The logical inference drawn by the agent")
    supporting_facts: List[str] = Field(default_factory=list, description="Keys or summaries of facts supporting this inference")


class AlternativeExplanation(BaseModel):
    hypothesis: str = Field(description="Alternative hypothesis for the anomaly")
    supporting_evidence: List[str] = Field(default_factory=list, description="Evidence supporting this hypothesis")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Evidence contradicting this hypothesis")
    confidence: float = Field(ge=0.0, le=1.0, description="Estimated confidence score for this alternative")


class ActionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(BaseModel):
    action: str = Field(description="The suggested action to take")
    priority: ActionPriority = Field(description="Priority of the action")
    reason: str = Field(description="Reasoning behind this recommendation")
    requires_human_approval: bool = Field(default=True, description="Always true in Phase 6 as agent is advisory")


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str
    result_summary: str
    success: bool
    error: Optional[str] = None


class InvestigationResult(BaseModel):
    investigation_id: str = Field(default="", description="Unique ID for this investigation run")
    case_id: str = Field(default="", description="The CASE-NNNNN identifier")
    investigation_status: InvestigationStatus = Field(default=InvestigationStatus.NOT_STARTED)
    deterministic_status: str = Field(default="", description="Status from deterministic engine")
    deterministic_reason_code: str = Field(default="", description="Reason code from deterministic engine")
    summary: str = Field(description="Concise description of the investigation findings")
    root_cause: str = Field(description="Identified primary root cause")
    root_cause_confidence: float = Field(ge=0.0, le=1.0, description="AI-generated or deterministic confidence score (0.0 to 1.0)")
    facts: List[FactRecord] = Field(default_factory=list, description="Authoritative facts verified against deterministic records")
    inferences: List[InferenceRecord] = Field(default_factory=list, description="Logical inferences drawn from facts")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant evidence records collected")
    alternative_explanations: List[AlternativeExplanation] = Field(default_factory=list)
    recommended_actions: List[RecommendedAction] = Field(default_factory=list)
    auto_resolution_eligible: bool = Field(default=False)
    requires_human_review: bool = Field(default=True)
    investigation_steps: List[str] = Field(default_factory=list, description="Sequence of states processed")
    tool_calls: List[ToolCallRecord] = Field(default_factory=list, description="Audit log of tool invocations")
    warnings: List[str] = Field(default_factory=list)
    analysis_source: AnalysisSource = Field(default=AnalysisSource.DETERMINISTIC)
