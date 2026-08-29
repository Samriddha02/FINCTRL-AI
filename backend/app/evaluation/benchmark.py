from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

from data.generator import FinancialDataGenerator

from app.core.database import engine as public_engine
from app.evaluation.constants import (
    ALL_BENCHMARK_SEEDS,
    DEFAULT_RESULTS_DIR,
    EVAL_DATASET_ROOT,
)
from app.evaluation.evaluator import DatasetEvaluator, evaluate_dataset
from app.evaluation.ground_truth import dataset_dir_for_seed, hash_dataset_files
from app.evaluation.isolation import run_isolation_checks
from app.evaluation.metrics import (
    aggregate_cross_seed,
    classification_signature,
    compute_metrics,
    compute_performance,
)
from app.evaluation.reports import generate_reports
from app.evaluation.schemas import (
    BenchmarkReport,
    CasePrediction,
    ReproducibilityResult,
    SeedEvaluationSummary,
)
from app.main import app as fastapi_app


def generate_seed_dataset(seed: int, cases: int, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generator = FinancialDataGenerator(seed=seed, num_cases=cases, output_dir=output_dir)
    generator.generate_all()
    return output_dir


def _metric_tuple(summary: SeedEvaluationSummary) -> tuple:
    return (
        round(summary.accuracy, 12),
        round(summary.macro_precision, 12),
        round(summary.macro_recall, 12),
        round(summary.macro_f1, 12),
        round(summary.micro_f1, 12),
        summary.correct_cases,
        summary.error_count,
    )


def compare_reproducibility(
    seed: int,
    first_dir: Path,
    second_dir: Path,
    first: SeedEvaluationSummary,
    second: SeedEvaluationSummary,
) -> ReproducibilityResult:
    differences: List[str] = []
    dataset_identical = hash_dataset_files(first_dir) == hash_dataset_files(second_dir)
    if not dataset_identical:
        differences.append("Generated operational/ground-truth CSV hashes differ")

    pred_identical = classification_signature(first.cases) == classification_signature(second.cases)
    if not pred_identical:
        differences.append("Predicted reason codes or statuses differ")

    metrics_identical = _metric_tuple(first) == _metric_tuple(second)
    if not metrics_identical:
        differences.append("Aggregate classification metrics differ")

    status = "REPRODUCIBLE" if (dataset_identical and pred_identical and metrics_identical) else "NOT REPRODUCIBLE"
    return ReproducibilityResult(
        seed=seed,
        dataset_identical=dataset_identical,
        predictions_identical=pred_identical,
        metrics_identical=metrics_identical,
        status=status,
        differences=differences,
    )


def _pool_cases(summaries: Sequence[SeedEvaluationSummary]) -> List[CasePrediction]:
    pooled: List[CasePrediction] = []
    for summary in summaries:
        for case in summary.cases:
            pooled.append(
                case.model_copy(update={"case_id": f"seed_{summary.seed}:{case.case_id}"})
            )
    return pooled


def run_benchmark(
    seeds: Sequence[int] | None = None,
    cases: int = 100,
    output_dir: Path | None = None,
    eval_data_root: Path | None = None,
    skip_generation: bool = False,
    verbose: bool = False,
    reproducibility_seed: Optional[int] = 42,
) -> BenchmarkReport:
    seeds = list(seeds or ALL_BENCHMARK_SEEDS)
    output_dir = Path(output_dir or DEFAULT_RESULTS_DIR)
    eval_data_root = Path(eval_data_root or EVAL_DATASET_ROOT)
    evaluator = DatasetEvaluator()

    wall_start = time.perf_counter()
    summaries: List[SeedEvaluationSummary] = []

    for seed in seeds:
        dataset_dir = dataset_dir_for_seed(eval_data_root, seed)
        if not skip_generation:
            if verbose:
                print(f"Generating dataset seed={seed} -> {dataset_dir}")
            generate_seed_dataset(seed, cases, dataset_dir)
        elif not dataset_dir.exists():
            raise FileNotFoundError(
                f"Dataset for seed {seed} not found at {dataset_dir}. "
                "Run without --skip-generation or generate that seed first."
            )
        if verbose:
            print(f"Evaluating seed={seed}")
        summary = evaluator.evaluate(dataset_dir, seed=seed)
        summaries.append(summary)
        if verbose:
            print(
                f"  seed={seed} accuracy={summary.accuracy * 100:.2f}% "
                f"correct={summary.correct_cases}/{summary.total_cases}"
            )

    repro: Optional[ReproducibilityResult] = None
    if reproducibility_seed is not None and reproducibility_seed in seeds:
        first = next(s for s in summaries if s.seed == reproducibility_seed)
        first_dir = dataset_dir_for_seed(eval_data_root, reproducibility_seed)
        second_dir = eval_data_root / f"seed_{reproducibility_seed}_repeat"
        if (not skip_generation) or (not second_dir.exists()):
            generate_seed_dataset(reproducibility_seed, cases, second_dir)
        second = evaluator.evaluate(second_dir, seed=reproducibility_seed)
        repro = compare_reproducibility(
            reproducibility_seed, first_dir, second_dir, first, second
        )

    isolation = run_isolation_checks(public_engine, app=fastapi_app)
    pooled = _pool_cases(summaries)
    overall = compute_metrics(pooled)
    total_runtime = time.perf_counter() - wall_start
    recon_runtime = sum(s.reconciliation_runtime_seconds for s in summaries)
    all_times = [c.processing_time_ms for s in summaries for c in s.cases]
    performance = compute_performance(all_times, recon_runtime, total_runtime)

    report = BenchmarkReport(
        timestamp=datetime.now(timezone.utc),
        seeds=list(seeds),
        total_cases=len(pooled),
        overall=overall,
        per_seed=summaries,
        cross_seed=aggregate_cross_seed(summaries),
        performance=performance,
        reproducibility=repro,
        isolation=isolation,
        extra={
            "eval_schema": "finctrl_eval",
            "development_database_untouched": True,
            "zero_division_convention": 0.0,
            "macro_includes_zero_support_classes": True,
        },
    )
    generate_reports(report, output_dir)
    return report


def print_summary(report: BenchmarkReport) -> None:
    print("FINCTRL AI Evaluation Framework")
    print("=" * 60)
    print(f"Seeds: {report.seeds}")
    print(f"Total cases: {report.total_cases}")
    print(f"Accuracy: {report.overall.accuracy * 100:.2f}%")
    print(f"Macro F1: {report.overall.macro_f1:.4f}")
    print(f"Error rate: {report.overall.error_rate:.4f}")
    print("")
    print(f"{'Seed':<8} {'Cases':<8} {'Correct':<10} {'Accuracy':<12} {'Macro F1':<10} {'Cases/s':<10}")
    print("-" * 60)
    for s in report.per_seed:
        print(
            f"{s.seed:<8} {s.total_cases:<8} {s.correct_cases:<10} "
            f"{s.accuracy * 100:>8.2f}%    {s.macro_f1:<10.4f} {s.cases_per_sec:<10.2f}"
        )
    print("-" * 60)
    cs = report.cross_seed
    print(
        f"Mean accuracy={cs.mean_accuracy * 100:.2f}%  "
        f"min={cs.minimum_accuracy * 100:.2f}%  "
        f"max={cs.maximum_accuracy * 100:.2f}%  "
        f"stddev={cs.accuracy_stddev * 100:.4f} pp"
    )
    if report.reproducibility:
        print(f"Reproducibility: {report.reproducibility.status}")
    if report.isolation:
        print(f"Ground-truth isolation: {'PASS' if report.isolation.passed else 'FAIL'}")
    print("=" * 60)
