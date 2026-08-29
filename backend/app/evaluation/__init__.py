"""Evaluation-only package. Production reconciliation must not import this module."""

from app.evaluation.evaluator import DatasetEvaluator, evaluate_dataset, evaluate_loaded_session
from app.evaluation.metrics import (
    compute_confusion_matrix,
    compute_metrics,
    compute_per_class_metrics,
)
from app.evaluation.schemas import CasePrediction, ClassMetrics, SeedEvaluationSummary
from app.evaluation.constants import ALL_ANOMALY_CLASSES, ALL_STATUS_CLASSES, DEFAULT_SEEDS

__all__ = [
    "DatasetEvaluator",
    "evaluate_dataset",
    "evaluate_loaded_session",
    "compute_metrics",
    "compute_per_class_metrics",
    "compute_confusion_matrix",
    "CasePrediction",
    "ClassMetrics",
    "SeedEvaluationSummary",
    "ALL_ANOMALY_CLASSES",
    "ALL_STATUS_CLASSES",
    "DEFAULT_SEEDS",
]
