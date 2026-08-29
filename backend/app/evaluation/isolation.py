from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List, Set

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.evaluation.constants import BACKEND_DIR, PROJECT_ROOT
from app.evaluation.schemas import IsolationResult

PRODUCTION_ROOTS = [
    BACKEND_DIR / "app" / "reconciliation",
    BACKEND_DIR / "app" / "services",
    BACKEND_DIR / "app" / "api",
    BACKEND_DIR / "app" / "models",
    BACKEND_DIR / "app" / "core",
    BACKEND_DIR / "app" / "main.py",
]


def _iter_python_files(paths: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def _module_name_from_file(path: Path) -> str:
    rel = path.relative_to(BACKEND_DIR)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def inspect_source_isolation(files: List[Path] | None = None) -> tuple[bool, bool, List[str]]:
    """AST-inspect production modules for ground-truth I/O and evaluation imports.

    Returns (reads_ground_truth, imports_evaluation, details).
    """
    files = files if files is not None else _iter_python_files(PRODUCTION_ROOTS)
    reads_gt = False
    imports_eval = False
    details: List[str] = []

    for file_path in files:
        source = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            details.append(f"Could not parse {file_path}: {exc}")
            continue

        rel = str(file_path.relative_to(PROJECT_ROOT))

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names: List[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                else:
                    if node.module:
                        names = [node.module]
                for name in names:
                    if name == "app.evaluation" or name.startswith("app.evaluation."):
                        imports_eval = True
                        details.append(f"{rel} imports evaluation package ({name})")

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.replace("\\", "/").lower()
                if "ground_truth.csv" in value:
                    reads_gt = True
                    details.append(f"{rel} contains ground_truth.csv path constant")

            if isinstance(node, ast.Call):
                func = node.func
                func_name = ""
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                if func_name in {"read_csv", "open"}:
                    for arg in list(node.args) + [kw.value for kw in node.keywords]:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if "ground_truth" in arg.value.lower():
                                reads_gt = True
                                details.append(f"{rel} {func_name}() argument references ground_truth")

    return reads_gt, imports_eval, details


def inspect_api_expected_label_exposure(app) -> tuple[bool, List[str]]:
    """Return (exposed, details) if production routes advertise expected labels."""
    details: List[str] = []
    exposed = False
    forbidden_tokens = ("ground-truth", "ground_truth", "expected")
    for route in getattr(app, "routes", []):
        path = getattr(route, "path", "") or ""
        lowered = path.lower()
        if any(token in lowered for token in ("ground-truth", "ground_truth")):
            exposed = True
            details.append(f"Route {path} exposes ground truth")
        if "/api/evaluation/expected" in lowered:
            exposed = True
            details.append(f"Route {path} exposes expected labels")
    return exposed, details


def inspect_database_ground_truth_table(engine: Engine) -> tuple[bool, List[str]]:
    details: List[str] = []
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    found = False
    for schema in schemas:
        if schema in {"information_schema", "pg_catalog"}:
            continue
        tables: Set[str] = {t.lower() for t in inspector.get_table_names(schema=schema)}
        if "ground_truth" in tables or "groundtruth" in tables:
            found = True
            details.append(f"Found ground_truth table in schema {schema}")
    return found, details


def inspect_session_ground_truth_table(db: Session) -> tuple[bool, List[str]]:
    engine = db.get_bind()
    return inspect_database_ground_truth_table(engine)


def run_isolation_checks(engine: Engine, app=None) -> IsolationResult:
    reads_gt, imports_eval, src_details = inspect_source_isolation()
    db_found, db_details = inspect_database_ground_truth_table(engine)
    api_exposed = False
    api_details: List[str] = []
    if app is not None:
        api_exposed, api_details = inspect_api_expected_label_exposure(app)

    details = src_details + db_details + api_details
    passed = not (reads_gt or imports_eval or db_found or api_exposed)
    if passed:
        details.append("Production modules do not load ground_truth.csv")
        details.append("Production modules do not import app.evaluation")
        details.append("Operational database has no ground_truth table")
        details.append("Production APIs do not expose expected labels")

    return IsolationResult(
        production_reads_ground_truth=reads_gt,
        production_imports_evaluation=imports_eval,
        operational_db_has_ground_truth_table=db_found,
        production_api_exposes_expected_labels=api_exposed,
        passed=passed,
        details=details,
    )
