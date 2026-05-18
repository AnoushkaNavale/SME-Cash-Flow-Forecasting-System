from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from forecast.engine import build_forecast

router = APIRouter()


@router.get("/{business_id}/offer")
def mock_lending_offer(
    business_id: UUID,
    db: Session = Depends(get_db),
    minimum_safe_balance: float = 50000,
):
    forecast = build_forecast(
        db=db,
        business_id=business_id,
        horizon_days=90,
        minimum_safe_balance=minimum_safe_balance,
    )
    lowest_balance = min(day.balance for day in forecast.forecast)
    shortfall = max(0, minimum_safe_balance - lowest_balance)

    if shortfall <= 0:
        return {
            "eligible": False,
            "status": "not_needed",
            "message": "No working-capital offer needed for the current forecast.",
            "suggested_limit": 0,
            "risk_date": None,
            "apr": None,
            "tenure_days": None,
        }

    buffer = max(25000, shortfall * 0.25)
    suggested_limit = round((shortfall + buffer) / 1000) * 1000
    risk_day = next((day for day in forecast.forecast if day.is_risk), None)

    return {
        "eligible": True,
        "status": "mock_preapproved",
        "message": "Demo offer only: no lender API or credit bureau call has been made.",
        "suggested_limit": suggested_limit,
        "risk_date": risk_day.date if risk_day else None,
        "apr": 18.0,
        "tenure_days": 90,
    }
