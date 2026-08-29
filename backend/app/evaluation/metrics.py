from __future__ import annotations

import statistics
from collections import Counter
from typing import Dict, Iterable, List, Sequence, Tuple

from app.evaluation.constants import (
    ALL_ANOMALY_CLASSES,
    ALL_STATUS_CLASSES,
    ZERO_DIVISION_VALUE,
)
from app.evaluation.schemas import (
    CasePrediction,
    ClassMetrics,
    ConfusionMatrix,
    CoverageReport,
    CrossSeedSummary,
    DatasetMetrics,
    FalseNegativeRecord,
    FalsePositiveRecord,
    PerformanceMetrics,
    SeedEvaluationSummary,
)


class EvaluationCoverageError(ValueError):
    """Raised when ground-truth and prediction sets are incomplete or duplicated."""


def safe_div(numerator: float, denominator: float) -> float:
    """Return numerator/denominator, or ZERO_DIVISION_VALUE (0.0) if denominator is 0."""
    if denominator == 0:
        return ZERO_DIVISION_VALUE
    return numerator / denominator


def precision_score(true_positives: int, false_positives: int) -> float:
    return safe_div(true_positives, true_positives + false_positives)


def recall_score(true_positives: int, false_negatives: int) -> float:
    return safe_div(true_positives, true_positives + false_negatives)


def f1_score(precision: float, recall: float) -> float:
    return safe_div(2.0 * precision * recall, precision + recall)


def one_vs_rest_counts(
    expected: Sequence[str],
    predicted: Sequence[str],
    class_label: str,
) -> Tuple[int, int, int, int]:
    """Return (TP, FP, FN, TN) for one-vs-rest classification of class_label."""
    tp = fp = fn = tn = 0
    for exp, pred in zip(expected, predicted):
        exp_pos = exp == class_label
        pred_pos = pred == class_label
        if exp_pos and pred_pos:
            tp += 1
        elif not exp_pos and pred_pos:
            fp += 1
        elif exp_pos and not pred_pos:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def compute_per_class_metrics(
    expected: Sequence[str],
    predicted: Sequence[str],
    labels: Sequence[str] | None = None,
) -> List[ClassMetrics]:
    labels = list(labels or ALL_ANOMALY_CLASSES)
    n = len(expected)
    results: List[ClassMetrics] = []
    for label in labels:
        tp, fp, fn, tn = one_vs_rest_counts(expected, predicted, label)
        prec = precision_score(tp, fp)
        rec = recall_score(tp, fn)
        support = sum(1 for e in expected if e == label)
        results.append(
            ClassMetrics(
                anomaly_class=label,
                support=support,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                true_negatives=tn,
                precision=prec,
                recall=rec,
                f1_score=f1_score(prec, rec),
                correct=tp,
                incorrect=support - tp,
            )
        )
        if tp + fp + fn + tn != n:
            raise ValueError(f"One-vs-rest counts for {label} do not cover all {n} cases.")
    return results


def compute_macro_metrics(per_class: Sequence[ClassMetrics]) -> Tuple[float, float, float]:
    if not per_class:
        return 0.0, 0.0, 0.0
    n = len(per_class)
    macro_p = sum(c.precision for c in per_class) / n
    macro_r = sum(c.recall for c in per_class) / n
    macro_f = sum(c.f1_score for c in per_class) / n
    return macro_p, macro_r, macro_f


def compute_micro_metrics(per_class: Sequence[ClassMetrics]) -> Tuple[float, float, float]:
    tp = sum(c.true_positives for c in per_class)
    fp = sum(c.false_positives for c in per_class)
    fn = sum(c.false_negatives for c in per_class)
    prec = precision_score(tp, fp)
    rec = recall_score(tp, fn)
    return prec, rec, f1_score(prec, rec)


def compute_weighted_metrics(per_class: Sequence[ClassMetrics]) -> Tuple[float, float, float]:
    total_support = sum(c.support for c in per_class)
    if total_support == 0:
        return 0.0, 0.0, 0.0
    wp = sum(c.precision * c.support for c in per_class) / total_support
    wr = sum(c.recall * c.support for c in per_class) / total_support
    wf = sum(c.f1_score * c.support for c in per_class) / total_support
    return wp, wr, wf


def compute_accuracy(expected: Sequence[str], predicted: Sequence[str]) -> float:
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must be the same length")
    if not expected:
        return 0.0
    correct = sum(1 for e, p in zip(expected, predicted) if e == p)
    return correct / len(expected)


def compute_confusion_matrix(
    expected: Sequence[str],
    predicted: Sequence[str],
    labels: Sequence[str] | None = None,
) -> ConfusionMatrix:
    labels = list(labels or ALL_ANOMALY_CLASSES)
    index = {label: i for i, label in enumerate(labels)}
    size = len(labels)
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for exp, pred in zip(expected, predicted):
        if exp not in index or pred not in index:
            # Include unexpected labels by expanding is not allowed; count only known classes.
            # Unknown predictions are still required to be in ALL_ANOMALY_CLASSES for this benchmark.
            continue
        matrix[index[exp]][index[pred]] += 1
    return ConfusionMatrix(labels=labels, matrix=matrix)


def identify_false_positives(cases: Sequence[CasePrediction]) -> List[FalsePositiveRecord]:
    records: List[FalsePositiveRecord] = []
    for case in cases:
        if case.predicted_reason_code != case.expected_reason_code:
            records.append(
                FalsePositiveRecord(
                    case_id=case.case_id,
                    expected_reason_code=case.expected_reason_code,
                    predicted_reason_code=case.predicted_reason_code,
                    expected_status=case.expected_status,
                    predicted_status=case.predicted_status,
                    difference=(
                        f"Expected: {case.expected_reason_code}; "
                        f"Predicted: {case.predicted_reason_code}"
                    ),
                    evidence_summary=case.evidence_summary,
                )
            )
    return records


def identify_false_negatives(cases: Sequence[CasePrediction]) -> List[FalseNegativeRecord]:
    records: List[FalseNegativeRecord] = []
    for case in cases:
        if case.predicted_reason_code != case.expected_reason_code:
            records.append(
                FalseNegativeRecord(
                    case_id=case.case_id,
                    expected_reason_code=case.expected_reason_code,
                    predicted_reason_code=case.predicted_reason_code,
                    expected_status=case.expected_status,
                    predicted_status=case.predicted_status,
                    evidence_summary=case.evidence_summary,
                )
            )
    return records


def exact_case_accuracy(cases: Sequence[CasePrediction]) -> float:
    if not cases:
        return 0.0
    correct = sum(1 for c in cases if c.correct_exact)
    return correct / len(cases)


def status_accuracy(cases: Sequence[CasePrediction]) -> float:
    if not cases:
        return 0.0
    correct = sum(1 for c in cases if c.correct_status)
    return correct / len(cases)


def error_metrics(cases: Sequence[CasePrediction]) -> Tuple[int, float]:
    error_count = 0
    for case in cases:
        is_error = (
            case.predicted_status == "ERROR"
            or case.predicted_reason_code == "NONE"
            or case.error is not None
        )
        if is_error:
            error_count += 1
    rate = safe_div(error_count, len(cases))
    return error_count, rate


def validate_coverage(
    ground_truth_ids: Sequence[str],
    prediction_ids: Sequence[str],
) -> CoverageReport:
    gt_counts = Counter(ground_truth_ids)
    pred_counts = Counter(prediction_ids)
    duplicate_gt = sorted([k for k, v in gt_counts.items() if v > 1])
    duplicate_pred = sorted([k for k, v in pred_counts.items() if v > 1])
    gt_set = set(gt_counts)
    pred_set = set(pred_counts)
    missing_predictions = sorted(gt_set - pred_set)
    missing_ground_truth = sorted(pred_set - gt_set)
    complete = not (
        duplicate_gt
        or duplicate_pred
        or missing_predictions
        or missing_ground_truth
        or len(ground_truth_ids) != len(prediction_ids)
    )
    report = CoverageReport(
        expected_cases=len(ground_truth_ids),
        evaluated_cases=len(prediction_ids),
        missing_predictions=missing_predictions,
        duplicate_predictions=duplicate_pred,
        missing_ground_truth=missing_ground_truth,
        duplicate_ground_truth=duplicate_gt,
        complete=complete,
    )
    if not complete:
        details = []
        if duplicate_gt:
            details.append(f"duplicate ground-truth case IDs: {duplicate_gt}")
        if duplicate_pred:
            details.append(f"duplicate predictions: {duplicate_pred}")
        if missing_predictions:
            details.append(f"missing predictions: {missing_predictions}")
        if missing_ground_truth:
            details.append(f"predictions without ground truth: {missing_ground_truth}")
        if len(ground_truth_ids) != len(prediction_ids):
            details.append(
                f"expected_cases={len(ground_truth_ids)} != evaluated_cases={len(prediction_ids)}"
            )
        raise EvaluationCoverageError("; ".join(details))
    return report


def compute_metrics(cases: Sequence[CasePrediction]) -> DatasetMetrics:
    expected = [c.expected_reason_code for c in cases]
    predicted = [c.predicted_reason_code for c in cases]
    per_class = compute_per_class_metrics(expected, predicted, ALL_ANOMALY_CLASSES)
    accuracy = compute_accuracy(expected, predicted)
    macro_p, macro_r, macro_f = compute_macro_metrics(per_class)
    micro_p, micro_r, micro_f = compute_micro_metrics(per_class)
    weighted_p, weighted_r, weighted_f = compute_weighted_metrics(per_class)
    err_count, err_rate = error_metrics(cases)
    fps = identify_false_positives(cases)
    fns = identify_false_negatives(cases)
    coverage = CoverageReport(
        expected_cases=len(cases),
        evaluated_cases=len(cases),
        complete=True,
    )
    return DatasetMetrics(
        accuracy=accuracy,
        precision=micro_p,
        recall=micro_r,
        f1=micro_f,
        exact_case_accuracy=exact_case_accuracy(cases),
        status_accuracy=status_accuracy(cases),
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f,
        micro_precision=micro_p,
        micro_recall=micro_r,
        micro_f1=micro_f,
        weighted_precision=weighted_p,
        weighted_recall=weighted_r,
        weighted_f1=weighted_f,
        error_count=err_count,
        error_rate=err_rate,
        per_class=per_class,
        confusion=compute_confusion_matrix(expected, predicted, ALL_ANOMALY_CLASSES),
        false_positives=fps,
        false_negatives=fns,
        coverage=coverage,
    )


def compute_performance(
    case_times_ms: Sequence[float],
    reconciliation_runtime_seconds: float,
    total_runtime_seconds: float,
) -> PerformanceMetrics:
    n = len(case_times_ms)
    avg_ms = sum(case_times_ms) / n if n else 0.0
    cps = safe_div(n, reconciliation_runtime_seconds)
    return PerformanceMetrics(
        reconciliation_runtime_seconds=reconciliation_runtime_seconds,
        total_runtime_seconds=total_runtime_seconds,
        average_case_time_ms=avg_ms,
        cases_per_second=cps,
        total_cases=n,
    )


def aggregate_cross_seed(summaries: Sequence[SeedEvaluationSummary]) -> CrossSeedSummary:
    if not summaries:
        return CrossSeedSummary(
            seeds=[],
            total_cases_across_seeds=0,
            total_correct=0,
            overall_accuracy=0.0,
            mean_accuracy=0.0,
            minimum_accuracy=0.0,
            maximum_accuracy=0.0,
            accuracy_stddev=0.0,
            mean_macro_precision=0.0,
            mean_macro_recall=0.0,
            mean_macro_f1=0.0,
        )
    accuracies = [s.accuracy for s in summaries]
    total_cases = sum(s.total_cases for s in summaries)
    total_correct = sum(s.correct_cases for s in summaries)
    stddev = statistics.stdev(accuracies) if len(accuracies) >= 2 else 0.0
    return CrossSeedSummary(
        seeds=[s.seed for s in summaries],
        total_cases_across_seeds=total_cases,
        total_correct=total_correct,
        overall_accuracy=safe_div(total_correct, total_cases),
        mean_accuracy=sum(accuracies) / len(accuracies),
        minimum_accuracy=min(accuracies),
        maximum_accuracy=max(accuracies),
        accuracy_stddev=stddev,
        mean_macro_precision=sum(s.macro_precision for s in summaries) / len(summaries),
        mean_macro_recall=sum(s.macro_recall for s in summaries) / len(summaries),
        mean_macro_f1=sum(s.macro_f1 for s in summaries) / len(summaries),
    )


def classification_signature(cases: Iterable[CasePrediction]) -> List[Tuple[str, str, str]]:
    """Timing-independent signature used for reproducibility comparison."""
    return sorted(
        (c.case_id, c.predicted_reason_code, c.predicted_status) for c in cases
    )
