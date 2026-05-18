from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID
from typing import Optional
from datetime import date

from database import get_db
from models import Transaction, TransactionCategory, TransactionSource
from schemas import TransactionCreate, TransactionOut, TransactionUpdate

router = APIRouter()


@router.post("/", response_model=TransactionOut, status_code=201)
def create_transaction(
    business_id: UUID,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
):
    tx = Transaction(business_id=business_id, **payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/", response_model=list[TransactionOut])
def list_transactions(
    business_id: UUID,
    category: Optional[TransactionCategory] = None,
    source:   Optional[TransactionSource]   = None,
    from_date: Optional[date] = Query(None),
    to_date:   Optional[date] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.business_id == business_id)

    if category:   q = q.filter(Transaction.category == category)
    if source:     q = q.filter(Transaction.source == source)
    if from_date:  q = q.filter(Transaction.date >= from_date)
    if to_date:    q = q.filter(Transaction.date <= to_date)

    return q.order_by(desc(Transaction.date)).limit(limit).all()


@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: UUID, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.patch("/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: UUID,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)

    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{tx_id}/settle", response_model=TransactionOut)
def settle_transaction(tx_id: UUID, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.is_confirmed = True
    tx.due_date = None
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(tx_id: UUID, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
