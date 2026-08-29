from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from app.evaluation.dbutil import get_eval_session
from app.evaluation.ground_truth import (
    expected_status_for_reason,
    ground_truth_map,
    load_ground_truth,
    require_operational_csvs,
)
from app.evaluation.metrics import compute_metrics, validate_coverage
from app.evaluation.schemas import CasePrediction, DatasetMetrics, SeedEvaluationSummary
from app.models import Order, Payment
from app.reconciliation.engine import reconcile_payment
from app.reconciliation.models import ReconciliationResult
from scripts.seed_database import seed_from_directory


def _evidence_summary(result: ReconciliationResult, limit: int = 3) -> str:
    parts: List[str] = []
    for item in result.evidence[:limit]:
        parts.append(f"{item.source}.{item.field}={item.value}: {item.explanation}")
    return " | ".join(parts)


def _case_from_result(
    result: ReconciliationResult,
    expected_reason: str,
    processing_time_ms: float,
) -> CasePrediction:
    expected_status = expected_status_for_reason(expected_reason)
    predicted_reason = result.reason_code.value
    predicted_status = result.status.value
    error = None
    if predicted_status == "ERROR" or predicted_reason == "NONE":
        error = "Reconciliation returned ERROR/NONE"
    correct_reason = predicted_reason == expected_reason and error is None
    correct_status = predicted_status == expected_status and error is None
    correct_exact = correct_reason and correct_status
    return CasePrediction(
        case_id=result.case_id,
        expected_reason_code=expected_reason,
        predicted_reason_code=predicted_reason,
        expected_status=expected_status,
        predicted_status=predicted_status,
        correct=correct_exact,
        confidence=float(result.confidence),
        needs_investigation=bool(result.needs_investigation),
        processing_time_ms=processing_time_ms,
        error=error,
        evidence_summary=_evidence_summary(result),
        correct_reason=correct_reason,
        correct_status=correct_status,
        correct_exact=correct_exact,
        difference=f"{result.difference}",
    )


def collect_predictions(db: Session) -> tuple[List[ReconciliationResult], List[float], float]:
    """Run production reconciliation and time only that work (not CSV/GT loading)."""
    orders = db.query(Order).order_by(Order.order_id).all()
    results: List[ReconciliationResult] = []
    times_ms: List[float] = []
    wall_start = time.perf_counter()
    for order in orders:
        payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()
        if not payment:
            continue
        case_start = time.perf_counter()
        result = reconcile_payment(db, payment.payment_id)
        case_end = time.perf_counter()
        results.append(result)
        times_ms.append((case_end - case_start) * 1000.0)
    recon_seconds = time.perf_counter() - wall_start
    return results, times_ms, recon_seconds


def compare_predictions(
    results: Sequence[ReconciliationResult],
    gt_map: dict,
    times_ms: Sequence[float],
) -> List[CasePrediction]:
    pred_ids = [r.case_id for r in results]
    gt_ids = list(gt_map.keys())
    validate_coverage(gt_ids, pred_ids)

    cases: List[CasePrediction] = []
    for result, elapsed in zip(results, times_ms):
        expected_reason = gt_map[result.case_id]
        cases.append(_case_from_result(result, expected_reason, elapsed))
    return cases


def evaluate_loaded_session(
    db: Session,
    ground_truth_path: Path,
    seed: int = -1,
    dataset_path: Optional[Path] = None,
) -> SeedEvaluationSummary:
    """Compare production predictions for an already-loaded operational database."""
    gt_df = load_ground_truth(ground_truth_path)
    gt_map = ground_truth_map(gt_df)
    results, times_ms, recon_seconds = collect_predictions(db)
    cases = compare_predictions(results, gt_map, times_ms)
    metrics = compute_metrics(cases)
    correct = sum(1 for c in cases if c.correct_reason)
    n = len(cases)
    avg_ms = sum(times_ms) / n if n else 0.0
    cps = (n / recon_seconds) if recon_seconds > 0 else 0.0
    return SeedEvaluationSummary(
        seed=seed,
        total_cases=n,
        correct_cases=correct,
        incorrect_cases=n - correct,
        accuracy=metrics.accuracy,
        status_accuracy=metrics.status_accuracy,
        exact_case_accuracy=metrics.exact_case_accuracy,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        macro_precision=metrics.macro_precision,
        macro_recall=metrics.macro_recall,
        macro_f1=metrics.macro_f1,
        micro_precision=metrics.micro_precision,
        micro_recall=metrics.micro_recall,
        micro_f1=metrics.micro_f1,
        weighted_precision=metrics.weighted_precision,
        weighted_recall=metrics.weighted_recall,
        weighted_f1=metrics.weighted_f1,
        error_count=metrics.error_count,
        error_rate=metrics.error_rate,
        total_runtime_seconds=recon_seconds,
        reconciliation_runtime_seconds=recon_seconds,
        avg_case_time_ms=avg_ms,
        cases_per_sec=cps,
        per_class=metrics.per_class,
        confusion=metrics.confusion,
        coverage=metrics.coverage,
        false_positives=metrics.false_positives,
        false_negatives=metrics.false_negatives,
        cases=cases,
        dataset_path=str(dataset_path or ""),
        ground_truth_path=str(ground_truth_path),
    )


def evaluate_dataset(
    dataset_path: Path,
    ground_truth_path: Optional[Path] = None,
    seed: int = -1,
    session: Optional[Session] = None,
    load_operational: bool = True,
) -> SeedEvaluationSummary:
    """Load operational CSVs (evaluation schema by default), reconcile, score against GT."""
    dataset_path = Path(dataset_path)
    require_operational_csvs(dataset_path)
    gt_path = Path(ground_truth_path) if ground_truth_path else dataset_path / "ground_truth.csv"

    own_session = session is None
    db = session if session is not None else get_eval_session()
    try:
        if load_operational:
            seed_from_directory(db, dataset_path, replace=True)
        return evaluate_loaded_session(
            db,
            gt_path,
            seed=seed,
            dataset_path=dataset_path,
        )
    finally:
        if own_session:
            db.close()


class DatasetEvaluator:
    """Stateful wrapper around evaluate_dataset for reuse by the benchmark runner."""

    def evaluate(
        self,
        dataset_path: Path,
        ground_truth_path: Optional[Path] = None,
        seed: int = -1,
        session: Optional[Session] = None,
        load_operational: bool = True,
    ) -> SeedEvaluationSummary:
        return evaluate_dataset(
            dataset_path=dataset_path,
            ground_truth_path=ground_truth_path,
            seed=seed,
            session=session,
            load_operational=load_operational,
        )
