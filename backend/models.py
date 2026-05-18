from sqlalchemy import (
    Column, String, Numeric, Boolean, Text,
    DateTime, Date, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class TransactionCategory(str, enum.Enum):
    invoice         = "invoice"         # money coming in from customers
    payment_received= "payment_received"# confirmed payment received
    payroll         = "payroll"         # salary outflow
    vendor          = "vendor"          # vendor/supplier payment
    tax             = "tax"             # GST, TDS, advance tax
    rent            = "rent"            # rent/utilities
    loan_emi        = "loan_emi"        # EMI payments
    misc_income     = "misc_income"
    misc_expense    = "misc_expense"


class TransactionSource(str, enum.Enum):
    razorpay  = "razorpay"
    bank_csv  = "bank_csv"             # uploaded bank statement
    gst       = "gst"                  # GST Suvidha API
    tally     = "tally"                # Tally XML export
    manual    = "manual"               # user entered manually


class AlertSeverity(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


# ─── Business ─────────────────────────────────────────────────────────────────

class Business(Base):
    """
    One row per SME using the platform.
    Keeps all data tenant-isolated from day one.
    """
    __tablename__ = "businesses"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(200), nullable=False)
    gstin      = Column(String(15), unique=True, nullable=True)   # 15-char GST ID
    email      = Column(String(200), unique=True, nullable=False)
    phone      = Column(String(15), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    transactions = relationship("Transaction", back_populates="business", cascade="all, delete")
    alerts       = relationship("CashFlowAlert", back_populates="business", cascade="all, delete")
    forecasts    = relationship("ForecastSnapshot", back_populates="business", cascade="all, delete")


# ─── Transaction ──────────────────────────────────────────────────────────────

class Transaction(Base):
    """
    Core table. Every rupee in or out, from any source.

    Convention:
      amount > 0  →  inflow  (money received)
      amount < 0  →  outflow (money spent)

    is_confirmed = False means the transaction is expected but not yet settled
    (e.g. a GST invoice raised but payment not received yet).
    """
    __tablename__ = "transactions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id   = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)

    date          = Column(Date, nullable=False, index=True)
    amount        = Column(Numeric(14, 2), nullable=False)   # INR, 2 decimal places
    category      = Column(SAEnum(TransactionCategory), nullable=False)
    source        = Column(SAEnum(TransactionSource),   nullable=False)
    description   = Column(Text, nullable=True)

    # For invoices: track due date and whether it's been paid
    is_confirmed  = Column(Boolean, default=True, nullable=False)
    due_date      = Column(Date, nullable=True)              # for outstanding invoices
    invoice_number= Column(String(50), nullable=True)
    counterparty  = Column(String(200), nullable=True)       # customer / vendor name

    # Raw payload from the source API (useful for debugging)
    external_id   = Column(String(100), nullable=True)       # Razorpay payment ID etc.

    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="transactions")


# ─── Forecast Snapshot ────────────────────────────────────────────────────────

class ForecastSnapshot(Base):
    """
    Stores the last computed forecast for a business.
    Re-computed whenever new transactions come in.
    Stored as JSON so we don't need a row per forecast day.
    """
    __tablename__ = "forecast_snapshots"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id  = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    horizon_days = Column(Numeric(3, 0), default=90)

    # Stored as JSONB: [{date, balance, net_flow, is_risk}, ...]
    forecast_data = Column(Text, nullable=False)   # JSON string
    current_balance = Column(Numeric(14, 2), nullable=False)
    minimum_safe_balance = Column(Numeric(14, 2), default=50000)

    business = relationship("Business", back_populates="forecasts")


# ─── Cash Flow Alert ──────────────────────────────────────────────────────────

class CashFlowAlert(Base):
    """
    Generated risk windows — e.g. "Week of June 10 looks dangerous."
    Created by the forecast engine, shown in the dashboard alert panel.
    """
    __tablename__ = "cashflow_alerts"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)

    alert_date  = Column(Date, nullable=False)               # the at-risk date
    severity    = Column(SAEnum(AlertSeverity), nullable=False)
    message     = Column(Text, nullable=False)
    projected_balance = Column(Numeric(14, 2), nullable=False)

    is_resolved = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="alerts")
