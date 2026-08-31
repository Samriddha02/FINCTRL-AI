from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.tax_matching.schemas import TaxMatchResult, TaxBatchMatchSummary
from app.tax_matching.controller import TaxMatchController, tax_matches_by_id
from app.agents.tools import validate_id

router = APIRouter(prefix="/api/tax-matching", tags=["Tax Line Matching"])


@router.get("", response_model=TaxBatchMatchSummary)
def run_batch_tax_matching(db: Session = Depends(get_db)) -> TaxBatchMatchSummary:
    """Executes deterministic tax matching across all invoices in the operational database."""
    try:
        controller = TaxMatchController(db)
        return controller.process_batch_tax_match()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute batch tax matching: {str(e)}"
        )


@router.get("/results/{match_id}", response_model=TaxMatchResult)
def get_tax_match_result_by_id(match_id: str) -> TaxMatchResult:
    """Retrieves a previously computed tax match result by match_id."""
    res = tax_matches_by_id.get(match_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tax Match result '{match_id}' not found."
        )
    return res


@router.get("/{invoice_id}", response_model=TaxMatchResult)
def get_single_tax_match(
    invoice_id: str,
    db: Session = Depends(get_db)
) -> TaxMatchResult:
    """Performs deterministic tax line matching for a single invoice."""
    try:
        validate_id(invoice_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        controller = TaxMatchController(db)
        return controller.process_tax_match(invoice_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform tax line matching: {str(e)}"
        )
