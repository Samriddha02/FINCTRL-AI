from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from app.evaluation.constants import (
    EXPECTED_STATUS_BY_REASON,
    GROUND_TRUTH_FILENAME,
    OPERATIONAL_CSV_FILES,
)
from app.evaluation.metrics import EvaluationCoverageError


def dataset_dir_for_seed(eval_root: Path, seed: int) -> Path:
    return Path(eval_root) / f"seed_{seed}"


def ground_truth_path(dataset_dir: Path) -> Path:
    return Path(dataset_dir) / GROUND_TRUTH_FILENAME


def load_ground_truth(path: Path) -> pd.DataFrame:
    """Load evaluation-only oracle labels. Must never be called from production code."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    required = {"case_id", "ground_truth_status"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"ground_truth.csv missing columns: {sorted(missing)}")
    ids = df["case_id"].astype(str).tolist()
    dupes = sorted({cid for cid in ids if ids.count(cid) > 1})
    if dupes:
        raise EvaluationCoverageError(f"duplicate ground-truth case IDs: {dupes}")
    return df


def ground_truth_map(df: pd.DataFrame) -> Dict[str, str]:
    return {str(row["case_id"]): str(row["ground_truth_status"]) for _, row in df.iterrows()}


def expected_status_for_reason(reason_code: str) -> str:
    return EXPECTED_STATUS_BY_REASON.get(reason_code, "ERROR")


def hash_dataset_files(dataset_dir: Path, files: Iterable[str] | None = None) -> str:
    names = list(files) if files is not None else OPERATIONAL_CSV_FILES + [GROUND_TRUTH_FILENAME]
    digest = hashlib.sha256()
    root = Path(dataset_dir)
    for name in names:
        path = root / name
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        if not path.exists():
            digest.update(b"<missing>")
            continue
        digest.update(path.read_bytes())
    return digest.hexdigest()


def require_operational_csvs(dataset_dir: Path) -> List[Path]:
    root = Path(dataset_dir)
    missing = [name for name in OPERATIONAL_CSV_FILES if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Dataset {root} is missing operational CSVs: {missing}")
    return [root / name for name in OPERATIONAL_CSV_FILES]
