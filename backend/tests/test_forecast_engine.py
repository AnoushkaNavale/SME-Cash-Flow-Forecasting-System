from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from forecast.engine import _compute_avg_daily_flow, _generate_recommendations
from models import AlertSeverity, TransactionCategory
from schemas import ForecastDay


class Tx:
    def __init__(self, amount, days_ago=0, confirmed=True, category=TransactionCategory.invoice, due_date=None):
        self.amount = Decimal(str(amount))
        self.date = date.today() - timedelta(days=days_ago)
        self.is_confirmed = confirmed
        self.category = category
        self.due_date = due_date
        self.counterparty = "Client"
        self.description = "Demo"


def test_average_daily_flow_uses_history():
    txs = [Tx(7000, days_ago=2), Tx(-14000, days_ago=1)]
    assert _compute_avg_daily_flow(txs) < 0


def test_recommendations_include_shortfall_action():
    forecast = [
        ForecastDay(date=date.today(), balance=40000, net_flow=-10000, is_risk=True),
        ForecastDay(date=date.today() + timedelta(days=1), balance=30000, net_flow=-10000, is_risk=True),
    ]
    recs = _generate_recommendations([], forecast, 50000)
    assert recs[0].priority in {AlertSeverity.medium, AlertSeverity.high}
    assert recs[0].impact == 10000
