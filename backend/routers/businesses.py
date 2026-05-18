from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from database import get_db
from models import Business, Transaction
from schemas import BusinessCreate, BusinessOut

router = APIRouter()


@router.get("/", response_model=list[BusinessOut])
def list_businesses(db: Session = Depends(get_db)):
    return db.query(Business).order_by(Business.created_at.desc()).all()


@router.post("/", response_model=BusinessOut, status_code=201)
def create_business(payload: BusinessCreate, db: Session = Depends(get_db)):
    existing = db.query(Business).filter(Business.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A business with this email already exists")

    business = Business(**payload.model_dump())
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(business_id: UUID, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.get("/{business_id}/summary")
def business_summary(business_id: UUID, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    transactions = db.query(Transaction).filter(Transaction.business_id == business_id).all()
    confirmed = [tx for tx in transactions if tx.is_confirmed]
    pending = [tx for tx in transactions if not tx.is_confirmed]

    return {
        "business": business,
        "current_balance": float(sum(tx.amount for tx in confirmed)),
        "pending_receivables": float(sum(tx.amount for tx in pending if tx.amount > 0)),
        "pending_payables": abs(float(sum(tx.amount for tx in pending if tx.amount < 0))),
        "transaction_count": len(transactions),
        "pending_count": len(pending),
    }
