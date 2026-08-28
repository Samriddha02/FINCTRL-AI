import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.reconciliation.engine import reconcile_all_cases

GROUND_TRUTH_CSV = project_root / "data" / "output" / "ground_truth.csv"


def run_benchmark():
    """Evaluates the Deterministic Reconciliation Engine against the external ground_truth.csv oracle."""
    print("FINCTRL AI Deterministic Reconciliation Engine Benchmark\n")

    if not GROUND_TRUTH_CSV.exists():
        print(f"ERROR: Benchmark ground truth file {GROUND_TRUTH_CSV} not found.")
        sys.exit(1)

    df_gt = pd.read_csv(GROUND_TRUTH_CSV)
    gt_map = {r["case_id"]: r["ground_truth_status"] for _, r in df_gt.iterrows()}

    db = SessionLocal()
    try:
        results = reconcile_all_cases(db)
        total = len(results)

        correct_reason = 0
        breakdown = {}

        for res in results:
            expected_reason = gt_map.get(res.case_id)
            actual_reason = res.reason_code.value

            if expected_reason not in breakdown:
                breakdown[expected_reason] = {"total": 0, "correct": 0, "mismatches": []}

            breakdown[expected_reason]["total"] += 1

            if actual_reason == expected_reason:
                correct_reason += 1
                breakdown[expected_reason]["correct"] += 1
            else:
                breakdown[expected_reason]["mismatches"].append(
                    f"case={res.case_id}: expected={expected_reason}, got={actual_reason}"
                )

        reason_accuracy = (correct_reason / total) * 100.0 if total > 0 else 0.0

        print(f"Total Operational Cases Evaluated: {total}")
        print(f"Reason-Code Accuracy: {correct_reason}/{total} ({reason_accuracy:.2f}%)\n")

        print(f"{'Ground Truth Anomaly':<25} | {'Total':<6} | {'Correct':<8} | {'Accuracy':<8}")
        print("-" * 55)
        for status, stats in breakdown.items():
            acc = (stats["correct"] / stats["total"]) * 100.0 if stats["total"] > 0 else 0.0
            print(f"{status:<25} | {stats['total']:<6} | {stats['correct']:<8} | {acc:.1f}%")

        print("\n" + "=" * 60)
        if reason_accuracy >= 90.0:
            print(f"Benchmark Result: PASS ({reason_accuracy:.2f}% >= 90.0%)")
        else:
            print(f"Benchmark Result: FAIL ({reason_accuracy:.2f}% < 90.0%)")
            for status, stats in breakdown.items():
                if stats["mismatches"]:
                    print(f"\nMismatches in {status}:")
                    for m in stats["mismatches"]:
                        print(f"  - {m}")
        print("=" * 60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()
