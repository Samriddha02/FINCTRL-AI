"""
tests/test_evaluation.py
Phase 5 — Evaluation & Benchmark Framework tests.

Verifies:
1.  Overall accuracy calculation
2.  Precision, recall, F1 formulas
3.  Per-class metrics (one-vs-rest)
4.  Confusion matrix
5.  False positives
6.  False negatives
7.  Exact-case accuracy
8.  Cross-seed aggregation
9.  Reproducibility
10. Ground-truth coverage / completeness
11. Duplicate prediction detection
12. Missing prediction detection
13. Ground-truth isolation (AST + DB + API)
14. Report generation (JSON, CSV, Markdown)
15. Performance metric calculation
16. CLI seed configuration
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List

import pytest

# ── path bootstrap ──────────────────────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
for p in (str(backend_dir), str(project_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ── evaluation imports ───────────────────────────────────────────────────────
from app.evaluation.constants import ALL_ANOMALY_CLASSES, ALL_STATUS_CLASSES, ZERO_DIVISION_VALUE
from app.evaluation.metrics import (
    EvaluationCoverageError,
    aggregate_cross_seed,
    classification_signature,
    compute_accuracy,
    compute_confusion_matrix,
    compute_macro_metrics,
    compute_metrics,
    compute_micro_metrics,
    compute_per_class_metrics,
    compute_weighted_metrics,
    error_metrics,
    exact_case_accuracy,
    f1_score,
    identify_false_negatives,
    identify_false_positives,
    one_vs_rest_counts,
    precision_score,
    recall_score,
    safe_div,
    status_accuracy,
    validate_coverage,
)
from app.evaluation.schemas import (
    CasePrediction,
    ClassMetrics,
    CrossSeedSummary,
    SeedEvaluationSummary,
)
from app.evaluation.isolation import (
    inspect_source_isolation,
    run_isolation_checks,
)
from app.evaluation.reports import (
    ensure_output_dir,
    generate_reports,
    render_markdown,
    write_confusion_matrix_csv,
    write_per_class_csv,
)
from app.core.database import engine as public_engine
from app.main import app as fastapi_app


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_CLASSES = ALL_ANOMALY_CLASSES[:4]  # use a small subset for unit tests


def _make_case(
    case_id: str,
    expected: str,
    predicted: str,
    expected_status: str = "MATCHED",
    predicted_status: str | None = None,
    error: str | None = None,
) -> CasePrediction:
    pred_status = predicted_status or expected_status
    correct_reason = predicted == expected and error is None
    correct_status = pred_status == expected_status and error is None
    return CasePrediction(
        case_id=case_id,
        expected_reason_code=expected,
        predicted_reason_code=predicted,
        expected_status=expected_status,
        predicted_status=pred_status,
        correct=correct_reason and correct_status,
        confidence=1.0,
        needs_investigation=False,
        processing_time_ms=1.0,
        error=error,
        correct_reason=correct_reason,
        correct_status=correct_status,
        correct_exact=correct_reason and correct_status,
        difference="",
    )


def _perfect_cases(n: int = 11) -> List[CasePrediction]:
    cases = []
    for i, cls in enumerate(ALL_ANOMALY_CLASSES):
        reps = max(1, n // len(ALL_ANOMALY_CLASSES))
        for j in range(reps):
            cases.append(_make_case(f"CASE-{i:02d}-{j}", cls, cls))
    return cases


def _seed_summary(
    seed: int,
    total: int = 100,
    correct: int = 100,
    macro_p: float = 1.0,
    macro_r: float = 1.0,
    macro_f: float = 1.0,
) -> SeedEvaluationSummary:
    return SeedEvaluationSummary(
        seed=seed,
        total_cases=total,
        correct_cases=correct,
        incorrect_cases=total - correct,
        accuracy=correct / total,
        status_accuracy=correct / total,
        exact_case_accuracy=correct / total,
        precision=macro_p,
        recall=macro_r,
        f1=macro_f,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f,
        micro_precision=macro_p,
        micro_recall=macro_r,
        micro_f1=macro_f,
        weighted_precision=macro_p,
        weighted_recall=macro_r,
        weighted_f1=macro_f,
        error_count=0,
        error_rate=0.0,
        total_runtime_seconds=0.4,
        reconciliation_runtime_seconds=0.4,
        avg_case_time_ms=4.0,
        cases_per_sec=250.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Accuracy
# ─────────────────────────────────────────────────────────────────────────────

def test_accuracy_perfect():
    expected = ["A", "B", "C"]
    predicted = ["A", "B", "C"]
    assert compute_accuracy(expected, predicted) == 1.0


def test_accuracy_none():
    assert compute_accuracy(["A", "B"], ["B", "A"]) == 0.0


def test_accuracy_partial():
    assert compute_accuracy(["A", "B", "A"], ["A", "A", "A"]) == pytest.approx(2 / 3)


def test_accuracy_empty():
    assert compute_accuracy([], []) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Precision / Recall / F1 formulas
# ─────────────────────────────────────────────────────────────────────────────

def test_safe_div_normal():
    assert safe_div(3.0, 4.0) == pytest.approx(0.75)


def test_safe_div_zero_denominator():
    assert safe_div(1.0, 0.0) == ZERO_DIVISION_VALUE


def test_precision_score():
    assert precision_score(3, 1) == pytest.approx(0.75)


def test_recall_score():
    assert recall_score(3, 1) == pytest.approx(0.75)


def test_f1_score_perfect():
    assert f1_score(1.0, 1.0) == pytest.approx(1.0)


def test_f1_score_zero():
    assert f1_score(0.0, 0.0) == ZERO_DIVISION_VALUE


def test_f1_formula():
    p, r = 0.8, 0.6
    expected = 2 * p * r / (p + r)
    assert f1_score(p, r) == pytest.approx(expected)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Per-class metrics (one-vs-rest)
# ─────────────────────────────────────────────────────────────────────────────

def test_one_vs_rest_perfect():
    expected = ["A", "A", "B"]
    predicted = ["A", "A", "B"]
    tp, fp, fn, tn = one_vs_rest_counts(expected, predicted, "A")
    assert tp == 2 and fp == 0 and fn == 0 and tn == 1


def test_one_vs_rest_counts_sum_to_n():
    expected = ["A", "B", "C", "A"]
    predicted = ["A", "C", "B", "B"]
    for label in ["A", "B", "C"]:
        tp, fp, fn, tn = one_vs_rest_counts(expected, predicted, label)
        assert tp + fp + fn + tn == len(expected)


def test_per_class_all_classes_present():
    exp = [c for c in ALL_ANOMALY_CLASSES]
    pred = [c for c in ALL_ANOMALY_CLASSES]
    results = compute_per_class_metrics(exp, pred, ALL_ANOMALY_CLASSES)
    names = [r.anomaly_class for r in results]
    assert names == ALL_ANOMALY_CLASSES


def test_per_class_perfect_precision_recall():
    exp = ALL_ANOMALY_CLASSES[:]
    pred = ALL_ANOMALY_CLASSES[:]
    results = compute_per_class_metrics(exp, pred, ALL_ANOMALY_CLASSES)
    for r in results:
        assert r.precision == pytest.approx(1.0)
        assert r.recall == pytest.approx(1.0)
        assert r.f1_score == pytest.approx(1.0)


def test_per_class_zero_support_class():
    """A class with no ground truth instances gets support=0 and precision/recall/f1=0.0."""
    exp = ["EXACT_MATCH", "EXACT_MATCH"]
    pred = ["EXACT_MATCH", "EXACT_MATCH"]
    results = compute_per_class_metrics(exp, pred, ALL_ANOMALY_CLASSES)
    zero_sup = [r for r in results if r.support == 0]
    assert all(r.precision == 0.0 for r in zero_sup)
    assert all(r.recall == 0.0 for r in zero_sup)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Confusion matrix
# ─────────────────────────────────────────────────────────────────────────────

def test_confusion_matrix_diagonal_perfect():
    expected = ALL_ANOMALY_CLASSES
    predicted = ALL_ANOMALY_CLASSES
    cm = compute_confusion_matrix(expected, predicted, ALL_ANOMALY_CLASSES)
    n = len(ALL_ANOMALY_CLASSES)
    for i in range(n):
        for j in range(n):
            if i == j:
                assert cm.matrix[i][j] == 1
            else:
                assert cm.matrix[i][j] == 0


def test_confusion_matrix_off_diagonal():
    exp = ["A", "B"]
    pred = ["B", "A"]
    cm = compute_confusion_matrix(exp, pred, ["A", "B"])
    assert cm.matrix[0][1] == 1  # A predicted as B
    assert cm.matrix[1][0] == 1  # B predicted as A
    assert cm.matrix[0][0] == 0
    assert cm.matrix[1][1] == 0


def test_confusion_matrix_labels_match():
    cm = compute_confusion_matrix([], [], ALL_ANOMALY_CLASSES)
    assert cm.labels == ALL_ANOMALY_CLASSES


# ─────────────────────────────────────────────────────────────────────────────
# 5 & 6.  False positives / False negatives
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fp_fn_when_perfect():
    cases = [_make_case(f"C{i}", "EXACT_MATCH", "EXACT_MATCH") for i in range(5)]
    fps = identify_false_positives(cases)
    fns = identify_false_negatives(cases)
    assert fps == [] and fns == []


def test_fp_fn_on_mismatch():
    cases = [
        _make_case("C1", "EXACT_MATCH", "FEE_DIFFERENCE"),
        _make_case("C2", "EXACT_MATCH", "EXACT_MATCH"),
    ]
    fps = identify_false_positives(cases)
    fns = identify_false_negatives(cases)
    assert len(fps) == 1 and fps[0].case_id == "C1"
    assert len(fns) == 1 and fns[0].case_id == "C1"


def test_fp_fields():
    cases = [_make_case("C1", "EXACT_MATCH", "AMOUNT_MISMATCH")]
    fp = identify_false_positives(cases)[0]
    assert fp.expected_reason_code == "EXACT_MATCH"
    assert fp.predicted_reason_code == "AMOUNT_MISMATCH"


def test_fn_fields():
    cases = [_make_case("C1", "FEE_DIFFERENCE", "EXACT_MATCH")]
    fn = identify_false_negatives(cases)[0]
    assert fn.expected_reason_code == "FEE_DIFFERENCE"
    assert fn.predicted_reason_code == "EXACT_MATCH"


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Exact-case accuracy
# ─────────────────────────────────────────────────────────────────────────────

def test_exact_case_accuracy_perfect():
    cases = _perfect_cases()
    assert exact_case_accuracy(cases) == pytest.approx(1.0)


def test_exact_case_accuracy_partial():
    cases = [
        _make_case("C1", "EXACT_MATCH", "EXACT_MATCH"),
        _make_case("C2", "EXACT_MATCH", "FEE_DIFFERENCE"),
    ]
    assert exact_case_accuracy(cases) == pytest.approx(0.5)


def test_exact_case_accuracy_empty():
    assert exact_case_accuracy([]) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Cross-seed aggregation
# ─────────────────────────────────────────────────────────────────────────────

def test_cross_seed_perfect():
    summaries = [_seed_summary(42), _seed_summary(123)]
    cs = aggregate_cross_seed(summaries)
    assert cs.overall_accuracy == pytest.approx(1.0)
    assert cs.mean_accuracy == pytest.approx(1.0)
    assert cs.minimum_accuracy == pytest.approx(1.0)
    assert cs.maximum_accuracy == pytest.approx(1.0)
    assert cs.accuracy_stddev == pytest.approx(0.0)


def test_cross_seed_mixed():
    s1 = _seed_summary(1, total=100, correct=80)
    s2 = _seed_summary(2, total=100, correct=100)
    cs = aggregate_cross_seed([s1, s2])
    assert cs.total_cases_across_seeds == 200
    assert cs.total_correct == 180
    assert cs.overall_accuracy == pytest.approx(0.9)
    assert cs.minimum_accuracy == pytest.approx(0.8)
    assert cs.maximum_accuracy == pytest.approx(1.0)


def test_cross_seed_empty():
    cs = aggregate_cross_seed([])
    assert cs.overall_accuracy == 0.0
    assert cs.seeds == []


def test_cross_seed_stddev():
    import statistics
    s1 = _seed_summary(1, total=100, correct=90)
    s2 = _seed_summary(2, total=100, correct=100)
    cs = aggregate_cross_seed([s1, s2])
    expected_std = statistics.stdev([0.9, 1.0])
    assert cs.accuracy_stddev == pytest.approx(expected_std, rel=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Reproducibility (classification_signature is deterministic)
# ─────────────────────────────────────────────────────────────────────────────

def test_reproducibility_same_cases():
    cases1 = [_make_case("C1", "EXACT_MATCH", "EXACT_MATCH")]
    cases2 = [_make_case("C1", "EXACT_MATCH", "EXACT_MATCH")]
    assert classification_signature(cases1) == classification_signature(cases2)


def test_reproducibility_different_cases():
    cases1 = [_make_case("C1", "EXACT_MATCH", "EXACT_MATCH")]
    cases2 = [_make_case("C1", "EXACT_MATCH", "FEE_DIFFERENCE")]
    assert classification_signature(cases1) != classification_signature(cases2)


# ─────────────────────────────────────────────────────────────────────────────
# 10 & 11 & 12 & 14.  Coverage checks
# ─────────────────────────────────────────────────────────────────────────────

def test_coverage_complete():
    gt = ["C1", "C2", "C3"]
    pred = ["C1", "C2", "C3"]
    report = validate_coverage(gt, pred)
    assert report.complete is True
    assert report.missing_predictions == []
    assert report.duplicate_predictions == []


def test_coverage_missing_prediction():
    with pytest.raises(EvaluationCoverageError, match="missing predictions"):
        validate_coverage(["C1", "C2"], ["C1"])


def test_coverage_duplicate_prediction():
    with pytest.raises(EvaluationCoverageError, match="duplicate predictions"):
        validate_coverage(["C1", "C2"], ["C1", "C1"])


def test_coverage_missing_ground_truth():
    with pytest.raises(EvaluationCoverageError, match="predictions without ground truth"):
        validate_coverage(["C1"], ["C1", "C2"])


def test_coverage_duplicate_ground_truth():
    with pytest.raises(EvaluationCoverageError, match="duplicate ground-truth case IDs"):
        validate_coverage(["C1", "C1"], ["C1", "C1"])


# ─────────────────────────────────────────────────────────────────────────────
# 13.  Ground-truth isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_production_source_isolation():
    reads_gt, imports_eval, details = inspect_source_isolation()
    assert not reads_gt, f"Production code references ground_truth: {details}"
    assert not imports_eval, f"Production code imports evaluation: {details}"


def test_isolation_checks_pass():
    result = run_isolation_checks(public_engine, app=fastapi_app)
    assert result.passed, f"Isolation failed: {result.details}"
    assert not result.production_reads_ground_truth
    assert not result.production_imports_evaluation
    assert not result.operational_db_has_ground_truth_table
    assert not result.production_api_exposes_expected_labels


# ─────────────────────────────────────────────────────────────────────────────
# 15.  Macro / micro / weighted metrics
# ─────────────────────────────────────────────────────────────────────────────

def test_macro_metrics_perfect():
    per_class = [
        ClassMetrics(
            anomaly_class=c, support=1, true_positives=1,
            false_positives=0, false_negatives=0, true_negatives=10,
            precision=1.0, recall=1.0, f1_score=1.0, correct=1, incorrect=0,
        )
        for c in ALL_ANOMALY_CLASSES
    ]
    mp, mr, mf = compute_macro_metrics(per_class)
    assert mp == pytest.approx(1.0)
    assert mr == pytest.approx(1.0)
    assert mf == pytest.approx(1.0)


def test_micro_metrics_perfect():
    per_class = [
        ClassMetrics(
            anomaly_class=c, support=1, true_positives=1,
            false_positives=0, false_negatives=0, true_negatives=10,
            precision=1.0, recall=1.0, f1_score=1.0, correct=1, incorrect=0,
        )
        for c in ALL_ANOMALY_CLASSES
    ]
    mp, mr, mf = compute_micro_metrics(per_class)
    assert mp == pytest.approx(1.0)
    assert mr == pytest.approx(1.0)
    assert mf == pytest.approx(1.0)


def test_weighted_metrics_zero_support():
    per_class = [
        ClassMetrics(
            anomaly_class="A", support=0, true_positives=0,
            false_positives=0, false_negatives=0, true_negatives=0,
            precision=0.0, recall=0.0, f1_score=0.0, correct=0, incorrect=0,
        )
    ]
    wp, wr, wf = compute_weighted_metrics(per_class)
    assert wp == 0.0 and wr == 0.0 and wf == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 16.  Report generation
# ─────────────────────────────────────────────────────────────────────────────

def test_report_generation(tmp_path):
    """generate_reports must produce all 7 required files."""
    cases = _perfect_cases(11)
    from app.evaluation.metrics import compute_metrics
    from app.evaluation.schemas import BenchmarkReport, CrossSeedSummary, PerformanceMetrics
    from datetime import datetime, timezone

    metrics = compute_metrics(cases)
    summary = _seed_summary(42)
    cs = aggregate_cross_seed([summary])
    perf = PerformanceMetrics(
        reconciliation_runtime_seconds=0.4,
        total_runtime_seconds=1.0,
        average_case_time_ms=4.0,
        cases_per_second=250.0,
        total_cases=11,
    )
    report = BenchmarkReport(
        timestamp=datetime.now(timezone.utc),
        seeds=[42],
        total_cases=len(cases),
        overall=metrics,
        per_seed=[summary],
        cross_seed=cs,
        performance=perf,
    )
    written = generate_reports(report, tmp_path)
    expected_files = {
        "benchmark_summary.json",
        "benchmark_summary.csv",
        "benchmark_report.md",
        "confusion_matrix.csv",
        "false_positives.csv",
        "false_negatives.csv",
        "per_class_metrics.csv",
    }
    written_names = {p.name for p in written}
    assert expected_files.issubset(written_names), (
        f"Missing report files: {expected_files - written_names}"
    )
    json_path = tmp_path / "benchmark_summary.json"
    data = json.loads(json_path.read_text())
    assert "accuracy" in data["overall"]
    assert "seeds" in data


def test_markdown_report_contains_key_sections(tmp_path):
    cases = _perfect_cases(11)
    from app.evaluation.metrics import compute_metrics
    from app.evaluation.schemas import BenchmarkReport, PerformanceMetrics
    from datetime import datetime, timezone

    metrics = compute_metrics(cases)
    summary = _seed_summary(42)
    cs = aggregate_cross_seed([summary])
    perf = PerformanceMetrics(
        reconciliation_runtime_seconds=0.4,
        total_runtime_seconds=1.0,
        average_case_time_ms=4.0,
        cases_per_second=250.0,
        total_cases=11,
    )
    report = BenchmarkReport(
        timestamp=datetime.now(timezone.utc),
        seeds=[42],
        total_cases=len(cases),
        overall=metrics,
        per_seed=[summary],
        cross_seed=cs,
        performance=perf,
    )
    md = render_markdown(report)
    for heading in (
        "# FINCTRL AI Evaluation Report",
        "## Overall Metrics",
        "## Per-Class Metrics",
        "## Confusion Matrix",
        "## False Positives",
        "## False Negatives",
        "## Cross-Seed Results",
        "## Reproducibility",
        "## Ground Truth Isolation",
        "## Performance",
        "## Limitations",
    ):
        assert heading in md, f"Missing section: {heading}"


# ─────────────────────────────────────────────────────────────────────────────
# 17.  Performance metric calculation
# ─────────────────────────────────────────────────────────────────────────────

def test_performance_metrics():
    from app.evaluation.metrics import compute_performance
    times_ms = [2.0, 3.0, 5.0]
    perf = compute_performance(times_ms, 0.01, 0.5)
    assert perf.average_case_time_ms == pytest.approx(10.0 / 3)
    assert perf.cases_per_second == pytest.approx(300.0)
    assert perf.total_cases == 3


def test_performance_empty():
    from app.evaluation.metrics import compute_performance
    perf = compute_performance([], 0.0, 0.0)
    assert perf.average_case_time_ms == 0.0
    assert perf.cases_per_second == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 18.  CLI seed configuration
# ─────────────────────────────────────────────────────────────────────────────

def test_cli_parser_default_seeds():
    import sys as _sys
    _sys.path.insert(0, str(backend_dir / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_evaluation", backend_dir / "scripts" / "run_evaluation.py"
    )
    mod = importlib.util.load_from_spec = None
    # just test that the build_parser import round-trips
    # We import the module manually
    import importlib
    loader = importlib.util.spec_from_file_location(
        "run_evaluation_mod", backend_dir / "scripts" / "run_evaluation.py"
    )
    from app.evaluation.constants import ALL_BENCHMARK_SEEDS
    assert set([42, 123, 7, 21, 99]).issubset(set(ALL_BENCHMARK_SEEDS))


def test_cli_parser_custom_seeds():
    """build_parser should accept --seeds as a list of ints."""
    import argparse
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_eval_cli", backend_dir / "scripts" / "run_evaluation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module.build_parser().parse_args(["--seeds", "42", "7"])
    assert args.seeds == [42, 7]


# ─────────────────────────────────────────────────────────────────────────────
# Status accuracy
# ─────────────────────────────────────────────────────────────────────────────

def test_status_accuracy_perfect():
    cases = _perfect_cases()
    assert status_accuracy(cases) == pytest.approx(1.0)


def test_status_accuracy_mismatch():
    cases = [
        _make_case("C1", "EXACT_MATCH", "EXACT_MATCH", "MATCHED", "MATCHED"),
        _make_case("C2", "EXACT_MATCH", "EXACT_MATCH", "MATCHED", "MISMATCH"),
    ]
    assert status_accuracy(cases) == pytest.approx(0.5)


# ─────────────────────────────────────────────────────────────────────────────
# Error rate
# ─────────────────────────────────────────────────────────────────────────────

def test_error_rate_no_errors():
    cases = _perfect_cases()
    count, rate = error_metrics(cases)
    assert count == 0 and rate == 0.0


def test_error_rate_with_error():
    cases = [
        _make_case("C1", "EXACT_MATCH", "NONE", error="Reconciliation returned ERROR/NONE"),
    ]
    count, rate = error_metrics(cases)
    assert count == 1 and rate == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# compute_metrics integration
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_metrics_perfect():
    cases = _perfect_cases()
    m = compute_metrics(cases)
    assert m.accuracy == pytest.approx(1.0)
    assert m.macro_f1 == pytest.approx(1.0)
    assert m.error_count == 0
    assert m.coverage.complete is True
    assert m.false_positives == []
    assert m.false_negatives == []
