from datetime import date, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from forecast.engine import build_forecast
from models import Transaction

router = APIRouter()


@router.get("/{business_id}")
def list_notifications(business_id: UUID, db: Session = Depends(get_db)):
    forecast = build_forecast(db=db, business_id=business_id, horizon_days=90)
    notifications = []

    for alert in forecast.alerts:
        notifications.append({
            "id": str(uuid4()),
            "type": "risk",
            "severity": alert.severity,
            "title": "Cash risk detected",
            "message": alert.message,
            "date": alert.alert_date,
            "is_read": False,
        })

    soon = date.today() + timedelta(days=7)
    pending = (
        db.query(Transaction)
        .filter(
            Transaction.business_id == business_id,
            Transaction.is_confirmed == False,
            Transaction.due_date != None,
            Transaction.due_date <= soon,
        )
        .order_by(Transaction.due_date.asc())
        .limit(10)
        .all()
    )
    for tx in pending:
        direction = "receivable" if tx.amount > 0 else "payable"
        notifications.append({
            "id": str(uuid4()),
            "type": direction,
            "severity": "medium" if tx.amount > 0 else "low",
            "title": f"Upcoming {direction}",
            "message": f"{tx.counterparty or tx.description or 'Item'} is due on {tx.due_date}.",
            "date": tx.due_date,
            "is_read": False,
        })

    return notifications[:20]
