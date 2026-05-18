from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from database import get_db
from schemas import ForecastOut
from forecast.engine import build_forecast

router = APIRouter()


@router.get("/{business_id}", response_model=ForecastOut)
def get_forecast(
    business_id: UUID,
    horizon_days: int = Query(90, ge=7, le=180),
    minimum_safe_balance: float = Query(50000),
    db: Session = Depends(get_db),
):
    """
    Build and return a rolling cash flow forecast for the given business.
    Re-computes fresh on every call — add caching once you have real traffic.
    """
    return build_forecast(
        db=db,
        business_id=business_id,
        horizon_days=horizon_days,
        minimum_safe_balance=minimum_safe_balance,
    )
