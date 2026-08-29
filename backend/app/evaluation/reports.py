from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List, Sequence

from app.evaluation.constants import ALL_ANOMALY_CLASSES
from app.evaluation.schemas import (
    BenchmarkReport,
    ClassMetrics,
    ConfusionMatrix,
    FalseNegativeRecord,
    FalsePositiveRecord,
    SeedEvaluationSummary,
)


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_confusion_matrix_csv(path: Path, confusion: ConfusionMatrix) -> None:
    labels = confusion.labels
    fieldnames = ["expected"] + list(labels)
    rows = []
    for i, expected in enumerate(labels):
        row = {"expected": expected}
        for j, predicted in enumerate(labels):
            row[predicted] = confusion.matrix[i][j]
        rows.append(row)
    _write_csv(path, fieldnames, rows)


def write_per_class_csv(path: Path, per_class: Sequence[ClassMetrics]) -> None:
    fieldnames = [
        "class",
        "support",
        "true_positives",
        "false_positives",
        "false_negatives",
        "true_negatives",
        "precision",
        "recall",
        "f1",
        "correct",
        "incorrect",
    ]
    rows = [
        {
            "class": c.anomaly_class,
            "support": c.support,
            "true_positives": c.true_positives,
            "false_positives": c.false_positives,
            "false_negatives": c.false_negatives,
            "true_negatives": c.true_negatives,
            "precision": f"{c.precision:.6f}",
            "recall": f"{c.recall:.6f}",
            "f1": f"{c.f1_score:.6f}",
            "correct": c.correct,
            "incorrect": c.incorrect,
        }
        for c in per_class
    ]
    _write_csv(path, fieldnames, rows)


def write_per_seed_csv(path: Path, summaries: Sequence[SeedEvaluationSummary]) -> None:
    fieldnames = [
        "seed",
        "total_cases",
        "correct_cases",
        "incorrect_cases",
        "accuracy",
        "status_accuracy",
        "exact_case_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "weighted_precision",
        "weighted_recall",
        "weighted_f1",
        "error_count",
        "error_rate",
        "total_runtime_seconds",
        "average_case_time_ms",
        "cases_per_second",
    ]
    rows = [
        {
            "seed": s.seed,
            "total_cases": s.total_cases,
            "correct_cases": s.correct_cases,
            "incorrect_cases": s.incorrect_cases,
            "accuracy": f"{s.accuracy:.6f}",
            "status_accuracy": f"{s.status_accuracy:.6f}",
            "exact_case_accuracy": f"{s.exact_case_accuracy:.6f}",
            "macro_precision": f"{s.macro_precision:.6f}",
            "macro_recall": f"{s.macro_recall:.6f}",
            "macro_f1": f"{s.macro_f1:.6f}",
            "micro_precision": f"{s.micro_precision:.6f}",
            "micro_recall": f"{s.micro_recall:.6f}",
            "micro_f1": f"{s.micro_f1:.6f}",
            "weighted_precision": f"{s.weighted_precision:.6f}",
            "weighted_recall": f"{s.weighted_recall:.6f}",
            "weighted_f1": f"{s.weighted_f1:.6f}",
            "error_count": s.error_count,
            "error_rate": f"{s.error_rate:.6f}",
            "total_runtime_seconds": f"{s.total_runtime_seconds:.6f}",
            "average_case_time_ms": f"{s.avg_case_time_ms:.6f}",
            "cases_per_second": f"{s.cases_per_sec:.6f}",
        }
        for s in summaries
    ]
    _write_csv(path, fieldnames, rows)


def write_false_positives_csv(path: Path, records: Sequence[FalsePositiveRecord]) -> None:
    fieldnames = [
        "case_id",
        "expected_reason_code",
        "predicted_reason_code",
        "expected_status",
        "predicted_status",
        "difference",
        "evidence_summary",
    ]
    rows = [r.model_dump() for r in records]
    _write_csv(path, fieldnames, rows)


def write_false_negatives_csv(path: Path, records: Sequence[FalseNegativeRecord]) -> None:
    fieldnames = [
        "case_id",
        "expected_reason_code",
        "predicted_reason_code",
        "expected_status",
        "predicted_status",
        "evidence_summary",
    ]
    rows = [r.model_dump() for r in records]
    _write_csv(path, fieldnames, rows)


def write_benchmark_summary_csv(path: Path, report: BenchmarkReport) -> None:
    overall = report.overall
    fieldnames = [
        "timestamp",
        "seeds",
        "total_cases",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "exact_case_accuracy",
        "status_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "weighted_precision",
        "weighted_recall",
        "weighted_f1",
        "error_count",
        "error_rate",
        "false_positive_count",
        "false_negative_count",
        "mean_accuracy",
        "minimum_accuracy",
        "maximum_accuracy",
        "accuracy_stddev",
        "reproducibility_status",
        "isolation_passed",
        "reconciliation_runtime_seconds",
        "average_case_time_ms",
        "cases_per_second",
    ]
    row = {
        "timestamp": report.timestamp.isoformat(),
        "seeds": " ".join(str(s) for s in report.seeds),
        "total_cases": report.total_cases,
        "accuracy": f"{overall.accuracy:.6f}",
        "precision": f"{overall.precision:.6f}",
        "recall": f"{overall.recall:.6f}",
        "f1": f"{overall.f1:.6f}",
        "exact_case_accuracy": f"{overall.exact_case_accuracy:.6f}",
        "status_accuracy": f"{overall.status_accuracy:.6f}",
        "macro_precision": f"{overall.macro_precision:.6f}",
        "macro_recall": f"{overall.macro_recall:.6f}",
        "macro_f1": f"{overall.macro_f1:.6f}",
        "micro_precision": f"{overall.micro_precision:.6f}",
        "micro_recall": f"{overall.micro_recall:.6f}",
        "micro_f1": f"{overall.micro_f1:.6f}",
        "weighted_precision": f"{overall.weighted_precision:.6f}",
        "weighted_recall": f"{overall.weighted_recall:.6f}",
        "weighted_f1": f"{overall.weighted_f1:.6f}",
        "error_count": overall.error_count,
        "error_rate": f"{overall.error_rate:.6f}",
        "false_positive_count": len(overall.false_positives),
        "false_negative_count": len(overall.false_negatives),
        "mean_accuracy": f"{report.cross_seed.mean_accuracy:.6f}",
        "minimum_accuracy": f"{report.cross_seed.minimum_accuracy:.6f}",
        "maximum_accuracy": f"{report.cross_seed.maximum_accuracy:.6f}",
        "accuracy_stddev": f"{report.cross_seed.accuracy_stddev:.6f}",
        "reproducibility_status": report.reproducibility.status if report.reproducibility else "",
        "isolation_passed": report.isolation.passed if report.isolation else "",
        "reconciliation_runtime_seconds": f"{report.performance.reconciliation_runtime_seconds:.6f}",
        "average_case_time_ms": f"{report.performance.average_case_time_ms:.6f}",
        "cases_per_second": f"{report.performance.cases_per_second:.6f}",
    }
    _write_csv(path, fieldnames, [row])


def render_markdown(report: BenchmarkReport) -> str:
    overall = report.overall
    repro = report.reproducibility
    isolation = report.isolation
    lines: List[str] = []
    lines.append("# FINCTRL AI Evaluation Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"Total cases: {report.total_cases}")
    lines.append(f"Accuracy: {overall.accuracy * 100:.2f}%")
    lines.append(f"Macro F1: {overall.macro_f1:.4f}")
    lines.append(f"Error rate: {overall.error_rate:.4f}")
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append("")
    lines.append(f"- Accuracy: {overall.accuracy:.6f}")
    lines.append(f"- Precision (micro): {overall.precision:.6f}")
    lines.append(f"- Recall (micro): {overall.recall:.6f}")
    lines.append(f"- F1 (micro): {overall.f1:.6f}")
    lines.append(f"- Macro Precision: {overall.macro_precision:.6f}")
    lines.append(f"- Macro Recall: {overall.macro_recall:.6f}")
    lines.append(f"- Macro F1: {overall.macro_f1:.6f}")
    lines.append(f"- Micro Precision: {overall.micro_precision:.6f}")
    lines.append(f"- Micro Recall: {overall.micro_recall:.6f}")
    lines.append(f"- Micro F1: {overall.micro_f1:.6f}")
    lines.append(f"- Weighted Precision: {overall.weighted_precision:.6f}")
    lines.append(f"- Weighted Recall: {overall.weighted_recall:.6f}")
    lines.append(f"- Weighted F1: {overall.weighted_f1:.6f}")
    lines.append(f"- Exact case accuracy: {overall.exact_case_accuracy:.6f}")
    lines.append(f"- Status accuracy: {overall.status_accuracy:.6f}")
    lines.append("")
    lines.append("## Per-Class Metrics")
    lines.append("")
    lines.append("| Class | Support | Precision | Recall | F1 | Correct | Incorrect |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    by_name = {c.anomaly_class: c for c in overall.per_class}
    for name in ALL_ANOMALY_CLASSES:
        c = by_name[name]
        lines.append(
            f"| {c.anomaly_class} | {c.support} | {c.precision:.4f} | {c.recall:.4f} | "
            f"{c.f1_score:.4f} | {c.correct} | {c.incorrect} |"
        )
    lines.append("")
    lines.append("## Confusion Matrix")
    lines.append("")
    lines.append(
        "Rows are expected reason codes and columns are predicted reason codes. "
        "The full matrix (including zero-count classes) is written to `confusion_matrix.csv`."
    )
    lines.append("")
    lines.append("## False Positives")
    lines.append("")
    lines.append(f"Count: {len(overall.false_positives)}")
    if overall.false_positives:
        for rec in overall.false_positives[:5]:
            lines.append(
                f"- {rec.case_id}: expected {rec.expected_reason_code}, "
                f"predicted {rec.predicted_reason_code}"
            )
    else:
        lines.append("No false positives.")
    lines.append("")
    lines.append("## False Negatives")
    lines.append("")
    lines.append(f"Count: {len(overall.false_negatives)}")
    if overall.false_negatives:
        for rec in overall.false_negatives[:5]:
            lines.append(
                f"- {rec.case_id}: expected {rec.expected_reason_code}, "
                f"predicted {rec.predicted_reason_code}"
            )
    else:
        lines.append("No false negatives.")
    lines.append("")
    lines.append("## Cross-Seed Results")
    lines.append("")
    lines.append("| Seed | Cases | Correct | Accuracy | Macro F1 | Runtime | Cases/sec |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for s in report.per_seed:
        lines.append(
            f"| {s.seed} | {s.total_cases} | {s.correct_cases} | {s.accuracy * 100:.2f}% | "
            f"{s.macro_f1:.4f} | {s.total_runtime_seconds:.4f}s | {s.cases_per_sec:.2f} |"
        )
    lines.append("")
    cs = report.cross_seed
    lines.append(f"- Mean accuracy: {cs.mean_accuracy:.6f}")
    lines.append(f"- Minimum accuracy: {cs.minimum_accuracy:.6f}")
    lines.append(f"- Maximum accuracy: {cs.maximum_accuracy:.6f}")
    lines.append(f"- Accuracy standard deviation: {cs.accuracy_stddev:.6f}")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    if repro:
        lines.append(f"Seed tested twice: {repro.seed}")
        lines.append(f"Dataset identical: {repro.dataset_identical}")
        lines.append(f"Predictions identical: {repro.predictions_identical}")
        lines.append(f"Metrics identical: {repro.metrics_identical}")
        lines.append(f"Final status: {repro.status}")
        if repro.differences:
            for diff in repro.differences:
                lines.append(f"- {diff}")
    else:
        lines.append("Reproducibility check was not run.")
    lines.append("")
    lines.append("## Ground Truth Isolation")
    lines.append("")
    if isolation:
        lines.append(f"Isolation status: {'PASS' if isolation.passed else 'FAIL'}")
        for detail in isolation.details:
            lines.append(f"- {detail}")
    else:
        lines.append("Isolation check was not run.")
    lines.append("")
    lines.append("Ground truth is loaded only by the evaluation layer. It is not stored in PostgreSQL operational tables and is not returned by production APIs.")
    lines.append("")
    lines.append("## Performance")
    lines.append("")
    lines.append(
        "Per-case runtime is `time.perf_counter()` around each production `reconcile_payment` call. "
        "Reconciliation runtime is the wall time of the full prediction loop (including operational queries). "
        "Total benchmark runtime includes dataset generation, isolated schema load, scoring, and report writing."
    )
    lines.append("")
    lines.append(f"Average case time: {report.performance.average_case_time_ms:.4f} ms")
    lines.append(f"Cases per second: {report.performance.cases_per_second:.4f}")
    lines.append(f"Reconciliation runtime: {report.performance.reconciliation_runtime_seconds:.4f} s")
    lines.append(f"Total benchmark runtime: {report.performance.total_runtime_seconds:.4f} s")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- Expected operational status is derived from reason-code semantics because `ground_truth.csv` stores anomaly labels, not MATCHED/MISMATCH statuses.")
    lines.append("- Macro averages include all 11 reason codes, including classes with zero support in a given seed.")
    lines.append("- Zero denominators in precision, recall, and F1 are reported as 0.0.")
    lines.append("- Performance numbers are informational and include local PostgreSQL round-trips.")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_json_report(path: Path, report: BenchmarkReport) -> None:
    payload = report.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate_reports(report: BenchmarkReport, output_dir: Path) -> List[Path]:
    output_dir = ensure_output_dir(output_dir)
    written: List[Path] = []

    json_path = output_dir / "benchmark_summary.json"
    write_json_report(json_path, report)
    written.append(json_path)

    csv_path = output_dir / "benchmark_summary.csv"
    write_benchmark_summary_csv(csv_path, report)
    written.append(csv_path)

    md_path = output_dir / "benchmark_report.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    written.append(md_path)

    cm_path = output_dir / "confusion_matrix.csv"
    write_confusion_matrix_csv(cm_path, report.overall.confusion)
    written.append(cm_path)

    fp_path = output_dir / "false_positives.csv"
    write_false_positives_csv(fp_path, report.overall.false_positives)
    written.append(fp_path)

    fn_path = output_dir / "false_negatives.csv"
    write_false_negatives_csv(fn_path, report.overall.false_negatives)
    written.append(fn_path)

    pc_path = output_dir / "per_class_metrics.csv"
    write_per_class_csv(pc_path, report.overall.per_class)
    written.append(pc_path)

    ps_path = output_dir / "per_seed_metrics.csv"
    write_per_seed_csv(ps_path, report.per_seed)
    written.append(ps_path)

    return written
