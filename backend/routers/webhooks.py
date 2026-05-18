import hmac
import hashlib
import json
import os
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction, TransactionCategory, TransactionSource

router = APIRouter()

RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
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


def verify_razorpay_signature(body: bytes, signature: str) -> bool:
    """Verify the webhook actually came from Razorpay."""
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if RAZORPAY_WEBHOOK_SECRET and not verify_razorpay_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body)
    event   = payload.get("event")

    if event == "payment.captured":
        payment = payload["payload"]["payment"]["entity"]
        existing = db.query(Transaction).filter(Transaction.external_id == payment["id"]).first()
        if existing:
            return {"status": "duplicate_ignored", "amount": float(existing.amount)}

        # Razorpay amounts are in paise — convert to rupees
        amount_inr = payment["amount"] / 100

        tx = Transaction(
            # TODO: map Razorpay contact/notes to a real business_id
            # For now use a default business — replace with your lookup logic
            business_id = DEFAULT_BUSINESS_ID,
            date        = date.today(),
            amount      = amount_inr,              # positive = inflow
            category    = TransactionCategory.payment_received,
            source      = TransactionSource.razorpay,
            description = payment.get("description") or f"Razorpay payment {payment['id']}",
            external_id = payment["id"],
            counterparty= payment.get("email") or payment.get("contact"),
            is_confirmed= True,
        )
        db.add(tx)
        db.commit()
        return {"status": "recorded", "amount": amount_inr}

    # Acknowledge other events without processing
    return {"status": "ignored", "event": event}
