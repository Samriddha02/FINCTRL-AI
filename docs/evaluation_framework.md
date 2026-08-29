# FINCTRL AI Evaluation Framework

The FINCTRL AI Evaluation Framework (Phase 5) rigorously evaluates the Deterministic Reconciliation Engine (Phase 4).

## Purpose
The primary purpose is to ensure the deterministic engine has 100% precision and recall for our expected base cases across multiple random seeds without hardcoding. It provides:
1. **Accuracy metrics** (Precision, Recall, F1 for 11 rules).
2. **Cross-seed generalizations** (Validating models across `42`, `123`, `7`, `21`, `99` and more).
3. **Reproducibility** (Checking seed deterministic property).
4. **Data Isolation** (`ground_truth.csv` is *only* available to the evaluation environment, not production APIs).

## Multi-Seed Benchmarks
Instead of a single test dataset (`seed=42`), the evaluation layer generates completely fresh CSVs for any random seed inside `data/evaluation/seed_{N}/`.

It dynamically sets up a parallel schema/database (`finctrl_eval` or isolated Session) so that main operational database tables in PostgreSQL are completely unaffected.

## Reports Generation
Running the benchmark suite outputs the following reports to `data/evaluation/results/`:
- `benchmark_report.md`: High-level summary, metrics, and reproducible stats.
- `benchmark_summary.json/csv`: Raw metric outputs for analysis.
- `per_class_metrics.csv`: Detailed F1 and support by anomaly class.
- `confusion_matrix.csv`: Misclassification map.
- `false_positives.csv` / `false_negatives.csv`: Traces of any errors to fix.

## Running the Benchmark
Run from the root of the project:
```sh
.\.venv\Scripts\python.exe backend/scripts/run_evaluation.py
```
Options:
- `--seeds 42 123` (run only specific seeds)
- `--cases 50` (cases per seed)
- `--skip-generation` (use cached datasets)
