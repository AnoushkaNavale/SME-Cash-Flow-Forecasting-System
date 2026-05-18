from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID
import os

from database import engine, Base, SessionLocal
from models import Business, Transaction, TransactionCategory, TransactionSource
from routers import businesses, forecast, imports, lending, notifications, transactions, upload, webhooks


DEMO_BUSINESS_ID = UUID("11111111-1111-1111-1111-111111111111")


def _uuid_from_env(name: str, fallback: UUID) -> UUID:
    raw_value = os.getenv(name)
    if not raw_value:
        return fallback
    try:
        return UUID(raw_value)
    except ValueError:
        return fallback


DEFAULT_BUSINESS_ID = _uuid_from_env("DEFAULT_BUSINESS_ID", DEMO_BUSINESS_ID)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    _seed_demo_business()
    print("Database tables created.")
    yield
    print("Shutting down.")


def _seed_demo_business():
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == DEFAULT_BUSINESS_ID).first()
        if not business:
            business = Business(
                id=DEFAULT_BUSINESS_ID,
                name="Test SME Pvt Ltd",
                email="test@sme.com",
            )
            db.add(business)
            db.commit()

        has_transactions = (
            db.query(Transaction)
            .filter(Transaction.business_id == DEFAULT_BUSINESS_ID)
            .first()
        )
        if has_transactions:
            return

        today = date.today()
        seed_transactions = [
            (today - timedelta(days=30), Decimal("150000"), TransactionCategory.payment_received, "Client A monthly retainer", True, None),
            (today - timedelta(days=28), Decimal("-45000"), TransactionCategory.payroll, "Payroll", True, None),
            (today - timedelta(days=25), Decimal("-18000"), TransactionCategory.vendor, "Raw material purchase", True, None),
            (today - timedelta(days=20), Decimal("80000"), TransactionCategory.payment_received, "Client B project milestone", True, None),
            (today - timedelta(days=15), Decimal("-12000"), TransactionCategory.rent, "Office rent", True, None),
            (today - timedelta(days=10), Decimal("-9000"), TransactionCategory.tax, "GST payment", True, None),
            (today, Decimal("120000"), TransactionCategory.invoice, "Client C invoice INV-047", False, today + timedelta(days=10)),
            (today, Decimal("-45000"), TransactionCategory.payroll, "Upcoming payroll", False, today + timedelta(days=15)),
        ]
        for tx_date, amount, category, description, confirmed, due_date in seed_transactions:
            db.add(Transaction(
                business_id=DEFAULT_BUSINESS_ID,
                date=tx_date,
                amount=amount,
                category=category,
                source=TransactionSource.manual,
                description=description,
                is_confirmed=confirmed,
                due_date=due_date,
            ))
        db.commit()
    finally:
        db.close()


app = FastAPI(
    title="SME Cash Flow Forecaster API",
    description="AI-powered 90-day cash flow intelligence for Indian SMEs",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://your-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(businesses.router,    prefix="/api/businesses",    tags=["Businesses"])
app.include_router(forecast.router,     prefix="/api/forecast",     tags=["Forecast"])
app.include_router(webhooks.router,     prefix="/webhooks",         tags=["Webhooks"])
app.include_router(upload.router,       prefix="/api/upload",       tags=["Upload"])
app.include_router(imports.router,      prefix="/api/imports",      tags=["Imports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(lending.router,      prefix="/api/lending",      tags=["Lending"])


@app.get("/")
def root():
    return {"status": "ok", "message": "SME Cash Flow Forecaster API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
