from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CasePrediction(BaseModel):
    case_id: str
    expected_reason_code: str
    predicted_reason_code: str
    expected_status: str
    predicted_status: str
    correct: bool
    confidence: float
    needs_investigation: bool
    processing_time_ms: float
    error: Optional[str] = None
    evidence_summary: str = ""
    correct_reason: bool = False
    correct_status: bool = False
    correct_exact: bool = False
    difference: str = ""


class ClassMetrics(BaseModel):
    anomaly_class: str
    support: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float
    correct: int
    incorrect: int


class ConfusionMatrix(BaseModel):
    labels: List[str]
    matrix: List[List[int]]


class CoverageReport(BaseModel):
    expected_cases: int
    evaluated_cases: int
    missing_predictions: List[str] = Field(default_factory=list)
    duplicate_predictions: List[str] = Field(default_factory=list)
    missing_ground_truth: List[str] = Field(default_factory=list)
    duplicate_ground_truth: List[str] = Field(default_factory=list)
    complete: bool = True


class FalsePositiveRecord(BaseModel):
    case_id: str
    expected_reason_code: str
    predicted_reason_code: str
    expected_status: str
    predicted_status: str
    difference: str
    evidence_summary: str = ""


class FalseNegativeRecord(BaseModel):
    case_id: str
    expected_reason_code: str
    predicted_reason_code: str
    expected_status: str
    predicted_status: str
    evidence_summary: str = ""


class PerformanceMetrics(BaseModel):
    reconciliation_runtime_seconds: float
    total_runtime_seconds: float
    average_case_time_ms: float
    cases_per_second: float
    total_cases: int


class SeedEvaluationSummary(BaseModel):
    seed: int
    total_cases: int
    correct_cases: int
    incorrect_cases: int
    accuracy: float
    status_accuracy: float
    exact_case_accuracy: float
    precision: float
    recall: float
    f1: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    error_count: int
    error_rate: float
    total_runtime_seconds: float
    reconciliation_runtime_seconds: float
    avg_case_time_ms: float
    cases_per_sec: float
    per_class: List[ClassMetrics] = Field(default_factory=list)
    confusion: Optional[ConfusionMatrix] = None
    coverage: Optional[CoverageReport] = None
    false_positives: List[FalsePositiveRecord] = Field(default_factory=list)
    false_negatives: List[FalseNegativeRecord] = Field(default_factory=list)
    cases: List[CasePrediction] = Field(default_factory=list)
    dataset_path: str = ""
    ground_truth_path: str = ""


class CrossSeedSummary(BaseModel):
    seeds: List[int]
    total_cases_across_seeds: int
    total_correct: int
    overall_accuracy: float
    mean_accuracy: float
    minimum_accuracy: float
    maximum_accuracy: float
    accuracy_stddev: float
    mean_macro_precision: float
    mean_macro_recall: float
    mean_macro_f1: float


class ReproducibilityResult(BaseModel):
    seed: int
    dataset_identical: bool
    predictions_identical: bool
    metrics_identical: bool
    status: str
    differences: List[str] = Field(default_factory=list)


class IsolationResult(BaseModel):
    production_reads_ground_truth: bool
    production_imports_evaluation: bool
    operational_db_has_ground_truth_table: bool
    production_api_exposes_expected_labels: bool
    passed: bool
    details: List[str] = Field(default_factory=list)


class DatasetMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    exact_case_accuracy: float
    status_accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    error_count: int
    error_rate: float
    per_class: List[ClassMetrics]
    confusion: ConfusionMatrix
    false_positives: List[FalsePositiveRecord]
    false_negatives: List[FalseNegativeRecord]
    coverage: CoverageReport


class BenchmarkReport(BaseModel):
    timestamp: datetime
    seeds: List[int]
    total_cases: int
    overall: DatasetMetrics
    per_seed: List[SeedEvaluationSummary]
    cross_seed: CrossSeedSummary
    performance: PerformanceMetrics
    reproducibility: Optional[ReproducibilityResult] = None
    isolation: Optional[IsolationResult] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
