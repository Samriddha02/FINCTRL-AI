import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.forecasting.schemas import CashForecastResult, Scenario
from app.forecasting.controller import CashForecastController, forecasts_by_id

router = APIRouter(prefix="/api/forecast/cash", tags=["Cash Forecasting"])


@router.get("", response_model=CashForecastResult)
def get_cash_forecast(
    as_of: Optional[str] = Query(None, description="Cutoff date in YYYY-MM-DD format (defaults to max date in DB)"),
    horizon_days: int = Query(7, gt=0, le=90, description="Forecast horizon in days (1 to 90)"),
    lookback_days: int = Query(30, ge=3, le=365, description="Historical lookback window in days (3 to 365)"),
    scenario: Scenario = Query(Scenario.BASELINE, description="Forecast scenario (BASELINE, CONSERVATIVE, OPTIMISTIC)"),
    db: Session = Depends(get_db)
) -> CashForecastResult:
    """Generates a deterministic, auditable cash-flow forecast based on operational records."""
    as_of_date = None
    if as_of:
        try:
            as_of_date = datetime.date.fromisoformat(as_of)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format for 'as_of': '{as_of}'. Expected YYYY-MM-DD."
            )

    try:
        controller = CashForecastController(db)
        res: CashForecastResult = controller.generate_forecast(
            as_of_date=as_of_date,
            lookback_days=lookback_days,
            horizon_days=horizon_days,
            scenario=scenario
        )
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cash forecast: {str(e)}"
        )


@router.get("/{forecast_id}", response_model=CashForecastResult)
def get_forecast_by_id(forecast_id: str) -> CashForecastResult:
    """Retrieves a previously generated cash forecast by forecast_id."""
    res = forecasts_by_id.get(forecast_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cash Forecast '{forecast_id}' not found."
        )
    return res
