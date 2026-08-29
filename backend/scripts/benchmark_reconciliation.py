import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.evaluation.evaluator import evaluate_loaded_session
from app.evaluation.constants import DEV_DATASET_DIR, TARGET_ACCURACY


GROUND_TRUTH_CSV = DEV_DATASET_DIR / "ground_truth.csv"


def run_benchmark():
    """Score the currently loaded development database (public schema) against data/output ground truth.

    This is the Phase 4 convenience check. Multi-seed isolated evaluation lives in run_evaluation.py.
    """
    print("FINCTRL AI Deterministic Reconciliation Engine Benchmark\n")
    print("(Evaluates the development database. For multi-seed isolated benchmarks use run_evaluation.py.)\n")

    if not GROUND_TRUTH_CSV.exists():
        print(f"ERROR: Benchmark ground truth file {GROUND_TRUTH_CSV} not found.")
        sys.exit(1)

    db = SessionLocal()
    try:
        summary = evaluate_loaded_session(db, GROUND_TRUTH_CSV, seed=42, dataset_path=DEV_DATASET_DIR)
    finally:
        db.close()

    print(f"Total Operational Cases Evaluated: {summary.total_cases}")
    print(
        f"Reason-Code Accuracy: {summary.correct_cases}/{summary.total_cases} "
        f"({summary.accuracy * 100:.2f}%)\n"
    )

    print(f"{'Ground Truth Anomaly':<25} | {'Total':<6} | {'Correct':<8} | {'Accuracy':<8}")
    print("-" * 55)
    for cls in summary.per_class:
        if cls.support == 0:
            continue
        acc = (cls.correct / cls.support) * 100.0 if cls.support else 0.0
        print(f"{cls.anomaly_class:<25} | {cls.support:<6} | {cls.correct:<8} | {acc:.1f}%")

    print("\n" + "=" * 60)
    reason_accuracy = summary.accuracy * 100.0
    if reason_accuracy >= TARGET_ACCURACY:
        print(f"Benchmark Result: PASS ({reason_accuracy:.2f}% >= {TARGET_ACCURACY:.1f}%)")
    else:
        print(f"Benchmark Result: FAIL ({reason_accuracy:.2f}% < {TARGET_ACCURACY:.1f}%)")
        for rec in summary.false_positives:
            print(
                f"  - case={rec.case_id}: expected={rec.expected_reason_code}, "
                f"got={rec.predicted_reason_code}"
            )
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_benchmark()
