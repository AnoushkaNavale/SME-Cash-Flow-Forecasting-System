from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from models import TransactionCategory, TransactionSource, AlertSeverity


# ─── Business ─────────────────────────────────────────────────────────────────

class BusinessCreate(BaseModel):
    name:  str
    email: EmailStr
    gstin: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v):
        if v and len(v) != 15:
            raise ValueError("GSTIN must be exactly 15 characters")
        return v


class BusinessOut(BaseModel):
    id:         UUID
    name:       str
    email:      str
    gstin:      Optional[str]
    phone:      Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Transaction ──────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    date:           date
    amount:         Decimal                    # positive = inflow, negative = outflow
    category:       TransactionCategory
    source:         TransactionSource
    description:    Optional[str] = None
    is_confirmed:   bool = True
    due_date:       Optional[date] = None
    invoice_number: Optional[str] = None
    counterparty:   Optional[str] = None
    external_id:    Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_not_zero(cls, v):
        if v == 0:
            raise ValueError("Transaction amount cannot be zero")
        return v


class TransactionUpdate(BaseModel):
    date:           Optional[date] = None
    amount:         Optional[Decimal] = None
    category:       Optional[TransactionCategory] = None
    source:         Optional[TransactionSource] = None
    description:    Optional[str] = None
    is_confirmed:   Optional[bool] = None
    due_date:       Optional[date] = None
    invoice_number: Optional[str] = None
    counterparty:   Optional[str] = None
    external_id:    Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_not_zero(cls, v):
        if v == 0:
            raise ValueError("Transaction amount cannot be zero")
        return v


class TransactionOut(BaseModel):
    id:             UUID
    business_id:    UUID
    date:           date
    amount:         Decimal
    category:       TransactionCategory
    source:         TransactionSource
    description:    Optional[str]
    is_confirmed:   bool
    due_date:       Optional[date]
    invoice_number: Optional[str]
    counterparty:   Optional[str]
    created_at:     datetime

    model_config = {"from_attributes": True}


# ─── Forecast ─────────────────────────────────────────────────────────────────

class ForecastDay(BaseModel):
    date:      date
    balance:   float
    net_flow:  float
    is_risk:   bool


class RecommendationOut(BaseModel):
    title:       str
    description: str
    priority:    AlertSeverity
    due_date:    Optional[date] = None
    impact:      Optional[float] = None


class ForecastOut(BaseModel):
    business_id:          UUID
    generated_at:         datetime
    current_balance:      float
    minimum_safe_balance: float
    horizon_days:         int
    forecast:             list[ForecastDay]
    alerts:               list["AlertOut"]
    recommendations:      list[RecommendationOut]

    model_config = {"from_attributes": True}


# ─── Alert ────────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id:                UUID
    alert_date:        date
    severity:          AlertSeverity
    message:           str
    projected_balance: Decimal
    is_resolved:       bool

    model_config = {"from_attributes": True}


# Update forward reference
ForecastOut.model_rebuild()
