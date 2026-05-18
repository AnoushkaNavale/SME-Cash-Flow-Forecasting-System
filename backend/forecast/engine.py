from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
import json

import pandas as pd
from sqlalchemy.orm import Session

from models import Transaction, ForecastSnapshot, AlertSeverity, TransactionCategory
from schemas import ForecastOut, ForecastDay, AlertOut, RecommendationOut


WEEKS_OF_HISTORY = 8


def build_forecast(
    db: Session,
    business_id: UUID,
    horizon_days: int = 90,
    minimum_safe_balance: float = 50000,
) -> ForecastOut:
    all_confirmed = (
        db.query(Transaction)
        .filter(
            Transaction.business_id == business_id,
            Transaction.is_confirmed == True,
        )
        .all()
    )
    current_balance = float(sum(tx.amount for tx in all_confirmed))

    today = date.today()
    future_confirmed = (
        db.query(Transaction)
        .filter(
            Transaction.business_id == business_id,
            Transaction.is_confirmed == False,
            Transaction.due_date != None,
            Transaction.due_date >= today,
        )
        .all()
    )

    future_map: dict[date, float] = {}
    for tx in future_confirmed:
        future_map[tx.due_date] = future_map.get(tx.due_date, 0) + float(tx.amount)

    cutoff = today - timedelta(weeks=WEEKS_OF_HISTORY)
    historical = [
        tx for tx in all_confirmed
        if tx.date >= cutoff and tx.date < today
    ]
    avg_daily_flow = _compute_avg_daily_flow(historical)

    forecast_days: list[ForecastDay] = []
    running_balance = current_balance

    for i in range(horizon_days):
        day = today + timedelta(days=i)
        net = future_map.get(day, 0.0) + avg_daily_flow
        running_balance += net
        forecast_days.append(ForecastDay(
            date=day,
            balance=round(running_balance, 2),
            net_flow=round(net, 2),
            is_risk=running_balance < minimum_safe_balance,
        ))

    alerts = _generate_alerts(forecast_days, minimum_safe_balance)
    recommendations = _generate_recommendations(
        transactions=all_confirmed + future_confirmed,
        forecast=forecast_days,
        minimum_safe_balance=minimum_safe_balance,
    )

    snapshot = ForecastSnapshot(
        business_id=business_id,
        horizon_days=horizon_days,
        current_balance=current_balance,
        minimum_safe_balance=minimum_safe_balance,
        forecast_data=json.dumps([d.model_dump(mode="json") for d in forecast_days]),
    )
    db.add(snapshot)
    db.commit()

    return ForecastOut(
        business_id=business_id,
        generated_at=datetime.now(),
        current_balance=current_balance,
        minimum_safe_balance=minimum_safe_balance,
        horizon_days=horizon_days,
        forecast=forecast_days,
        alerts=alerts,
        recommendations=recommendations,
    )


def _compute_avg_daily_flow(transactions: list[Transaction]) -> float:
    if not transactions:
        return -5000.0

    df = pd.DataFrame([
        {"date": tx.date, "amount": float(tx.amount)}
        for tx in transactions
    ])
    df["date"] = pd.to_datetime(df["date"])

    weekly = (
        df.resample("W", on="date")["amount"]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    if weekly.empty:
        return -5000.0

    weights = list(range(1, len(weekly) + 1))
    weighted_sum = sum(w * v for w, v in zip(weights, weekly["amount"]))
    return (weighted_sum / sum(weights)) / 7


def _generate_alerts(
    forecast: list[ForecastDay],
    minimum_safe_balance: float,
) -> list[AlertOut]:
    alerts: list[AlertOut] = []
    in_risk_window = False

    for day in forecast:
        if day.is_risk and not in_risk_window:
            in_risk_window = True
            severity = (
                AlertSeverity.high if day.balance < 0
                else AlertSeverity.medium if day.balance < minimum_safe_balance * 0.5
                else AlertSeverity.low
            )
            alerts.append(AlertOut(
                id=uuid4(),
                alert_date=day.date,
                severity=severity,
                projected_balance=day.balance,
                message=_alert_message(day.balance, day.date, minimum_safe_balance),
                is_resolved=False,
            ))
        elif not day.is_risk:
            in_risk_window = False

    return alerts


def _alert_message(balance: float, day: date, threshold: float) -> str:
    formatted_balance = f"INR {balance:,.0f}"
    formatted_date = day.strftime("%d %b")

    if balance < 0:
        return (
            f"Balance goes negative ({formatted_balance}) around {formatted_date}. "
            "Immediate action required: chase outstanding invoices or arrange credit."
        )
    return (
        f"Balance drops to {formatted_balance} around {formatted_date}, "
        f"below your INR {threshold:,.0f} safety threshold. "
        "Consider delaying a vendor payment or accelerating a customer collection."
    )


def _generate_recommendations(
    transactions: list[Transaction],
    forecast: list[ForecastDay],
    minimum_safe_balance: float,
) -> list[RecommendationOut]:
    first_risk_day = next((day for day in forecast if day.is_risk), None)
    pending_invoices = [
        tx for tx in transactions
        if (
            not tx.is_confirmed
            and tx.amount > 0
            and tx.category in {
                TransactionCategory.invoice,
                TransactionCategory.payment_received,
                TransactionCategory.misc_income,
            }
        )
    ]
    upcoming_outflows = [
        tx for tx in transactions
        if not tx.is_confirmed and tx.amount < 0 and tx.due_date is not None
    ]

    recommendations: list[RecommendationOut] = []

    if first_risk_day:
        shortfall = max(0, minimum_safe_balance - first_risk_day.balance)
        recommendations.append(RecommendationOut(
            title="Cover the projected shortfall",
            description=(
                f"Arrange roughly INR {shortfall:,.0f} before "
                f"{first_risk_day.date.strftime('%d %b')} to stay above the safety threshold."
            ),
            priority=AlertSeverity.high if first_risk_day.balance < 0 else AlertSeverity.medium,
            due_date=first_risk_day.date,
            impact=round(shortfall, 2),
        ))

    due_soon = sorted(
        [
            tx for tx in pending_invoices
            if tx.due_date is None or tx.due_date <= date.today() + timedelta(days=14)
        ],
        key=lambda tx: tx.due_date or date.today(),
    )
    if due_soon:
        top_invoice = due_soon[0]
        description = (
            f"Follow up with {top_invoice.counterparty or 'your customer'} for "
            f"INR {float(top_invoice.amount):,.0f}"
        )
        description += (
            f" due on {top_invoice.due_date.strftime('%d %b')}."
            if top_invoice.due_date
            else "."
        )
        recommendations.append(RecommendationOut(
            title="Chase receivables due soon",
            description=description,
            priority=AlertSeverity.medium,
            due_date=top_invoice.due_date,
            impact=float(top_invoice.amount),
        ))

    deferrable = sorted(upcoming_outflows, key=lambda tx: abs(float(tx.amount)), reverse=True)
    if first_risk_day and deferrable:
        top_outflow = deferrable[0]
        recommendations.append(RecommendationOut(
            title="Review upcoming outflows",
            description=(
                f"Consider deferring {top_outflow.counterparty or top_outflow.description or 'a planned payment'} "
                f"of INR {abs(float(top_outflow.amount)):,.0f} if it falls inside the risk window."
            ),
            priority=AlertSeverity.low,
            due_date=top_outflow.due_date,
            impact=abs(float(top_outflow.amount)),
        ))

    if not recommendations:
        recommendations.append(RecommendationOut(
            title="Keep monitoring weekly",
            description="No immediate crunch is projected. Upload fresh bank data weekly to keep the forecast current.",
            priority=AlertSeverity.low,
        ))

    return recommendations[:3]
