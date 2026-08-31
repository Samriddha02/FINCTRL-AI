from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.finance_qa.schemas import FinanceQARequest, FinanceQAResult
from app.finance_qa.controller import FinanceQAController, qa_results_by_id

router = APIRouter(prefix="/api/finance/qa", tags=["Finance Q&A"])


@router.post("", response_model=FinanceQAResult)
def ask_finance_question(
    req: FinanceQARequest,
    db: Session = Depends(get_db)
) -> FinanceQAResult:
    """Answers natural-language operational finance questions grounded strictly in authoritative database records."""
    if not req.question or not req.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty."
        )

    try:
        controller = FinanceQAController(db)
        result: FinanceQAResult = controller.process_question(req.question)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finance Q&A failed to process request: {str(e)}"
        )


@router.get("/{query_id}", response_model=FinanceQAResult)
def get_finance_qa_query(query_id: str) -> FinanceQAResult:
    """Retrieves a previously executed Q&A query by query_id."""
    res = qa_results_by_id.get(query_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Q&A Query '{query_id}' not found."
        )
    return res
