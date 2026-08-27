from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


class DBHealthResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Health check endpoint to verify backend service status."""
    return HealthResponse(
        status="ok",
        service="FINCTRL AI"
    )


@router.get("/health/db", response_model=DBHealthResponse)
def get_db_health(db: Session = Depends(get_db)) -> DBHealthResponse:
    """Database health check endpoint to verify PostgreSQL connection."""
    try:
        db.execute(text("SELECT 1;"))
        return DBHealthResponse(
            status="ok",
            database="connected"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )
