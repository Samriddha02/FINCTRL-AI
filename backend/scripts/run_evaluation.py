import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.evaluation.benchmark import print_summary, run_benchmark
from app.evaluation.constants import ALL_BENCHMARK_SEEDS, DEFAULT_RESULTS_DIR, DEV_DATASET_DIR
from app.evaluation.ground_truth import load_ground_truth, ground_truth_map
from app.core.database import SessionLocal
from app.reconciliation.engine import reconcile_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FINCTRL AI Phase 5 evaluation and benchmark runner"
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=list(ALL_BENCHMARK_SEEDS),
        help="Random seeds to generate and evaluate (default: 42 123 7 21 99 314 2026 999)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory for JSON/CSV/Markdown reports",
    )
    parser.add_argument(
        "--cases",
        type=int,
        default=100,
        help="Number of cases per generated seed dataset",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-seed generation and scoring progress",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Reuse datasets already present under data/evaluation/seed_<n>/",
    )
    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help="Evaluate a single case against ground truth (evaluation-only output)",
    )
    parser.add_argument(
        "--eval-data-dir",
        type=Path,
        default=None,
        help="Root directory for per-seed datasets (default: data/evaluation)",
    )
    parser.add_argument(
        "--skip-reproducibility",
        action="store_true",
        help="Do not regenerate and re-evaluate a seed for the reproducibility check",
    )
    return parser


def evaluate_single_case(case_id: str, ground_truth_csv: Path) -> None:
    """Reveal expected vs predicted labels. Not available through production APIs."""
    df = load_ground_truth(ground_truth_csv)
    gt_map = ground_truth_map(df)
    if case_id not in gt_map:
        raise SystemExit(f"Case {case_id} is not present in {ground_truth_csv}")
    db = SessionLocal()
    try:
        result = reconcile_case(db, case_id)
    finally:
        db.close()
    expected = gt_map[case_id]
    predicted = result.reason_code.value
    correct = predicted == expected and result.status.value != "ERROR"
    print("FINCTRL AI single-case evaluation (evaluation layer only)")
    print(f"Case ID:   {case_id}")
    print(f"Expected:  {expected}")
    print(f"Predicted: {predicted}")
    print(f"Status:    {result.status.value}")
    print(f"Correct:   {correct}")
    print(f"Confidence:{result.confidence}")
    print("Evidence:")
    for item in result.evidence:
        print(f"  - {item.source}.{item.field}={item.value}: {item.explanation}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.case_id:
        gt_path = DEV_DATASET_DIR / "ground_truth.csv"
        evaluate_single_case(args.case_id, gt_path)
        return 0

    report = run_benchmark(
        seeds=args.seeds,
        cases=args.cases,
        output_dir=args.output_dir,
        eval_data_root=args.eval_data_dir,
        skip_generation=args.skip_generation,
        verbose=args.verbose,
        reproducibility_seed=None if args.skip_reproducibility else 42,
    )
    print_summary(report)
    print(f"Reports written to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
