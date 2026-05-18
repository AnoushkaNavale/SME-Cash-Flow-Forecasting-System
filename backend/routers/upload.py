import io
import math
from datetime import datetime
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction, TransactionCategory, TransactionSource

router = APIRouter()

# Most Indian banks export CSVs with slight column name variations.
# These are the common ones — add more as you encounter them.
DATE_COLUMNS    = ["Date", "Txn Date", "Transaction Date", "Value Date"]
DEBIT_COLUMNS   = ["Debit", "Withdrawal Amt.", "Debit Amount", "DR"]
CREDIT_COLUMNS  = ["Credit", "Deposit Amt.", "Credit Amount", "CR"]
DESC_COLUMNS    = ["Description", "Narration", "Particulars", "Remarks"]


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def parse_amount(value) -> float:
    if pd.isna(value):
        return 0.0
    raw = str(value).replace(",", "").strip()
    if not raw:
        return 0.0
    amount = float(raw)
    return amount if math.isfinite(amount) else 0.0


@router.post("/bank-statement")
async def upload_bank_statement(
    business_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")), thousands=",")
    df.columns = df.columns.str.strip()

    date_col   = find_column(df, DATE_COLUMNS)
    debit_col  = find_column(df, DEBIT_COLUMNS)
    credit_col = find_column(df, CREDIT_COLUMNS)
    desc_col   = find_column(df, DESC_COLUMNS)

    if not date_col:
        raise HTTPException(status_code=422, detail=f"Could not find date column. Found: {list(df.columns)}")

    saved = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            # Parse date — try multiple formats
            raw_date = str(row[date_col]).strip()
            tx_date = None
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y"]:
                try:
                    tx_date = datetime.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    continue

            if not tx_date:
                skipped += 1
                continue

            # Amount: credit = positive inflow, debit = negative outflow
            credit = parse_amount(row[credit_col]) if credit_col else 0
            debit = parse_amount(row[debit_col]) if debit_col else 0

            amount = credit - debit
            if amount == 0:
                skipped += 1
                continue

            description = str(row[desc_col]).strip() if desc_col else ""

            # Guess category from description keywords
            category = _guess_category(description, amount)

            tx = Transaction(
                business_id  = business_id,
                date         = tx_date,
                amount       = amount,
                category     = category,
                source       = TransactionSource.bank_csv,
                description  = description[:500],
                is_confirmed = True,
            )
            db.add(tx)
            saved += 1

        except Exception:
            skipped += 1
            continue

    db.commit()
    return {
        "status":  "done",
        "saved":   saved,
        "skipped": skipped,
        "message": f"Imported {saved} transactions from {file.filename}",
    }


def _guess_category(description: str, amount: float) -> TransactionCategory:
    """
    Simple keyword-based category guesser.
    Replace with an ML classifier later when you have labelled data.
    """
    desc = description.lower()

    if amount > 0:
        if any(k in desc for k in ["invoice", "receipt", "payment received", "upi cr"]):
            return TransactionCategory.payment_received
        return TransactionCategory.misc_income

    # Outflows
    if any(k in desc for k in ["salary", "payroll", "wages"]):
        return TransactionCategory.payroll
    if any(k in desc for k in ["rent", "lease", "maintenance"]):
        return TransactionCategory.rent
    if any(k in desc for k in ["gst", "tds", "tax", "income tax"]):
        return TransactionCategory.tax
    if any(k in desc for k in ["emi", "loan", "repayment"]):
        return TransactionCategory.loan_emi
    if any(k in desc for k in ["vendor", "supplier", "purchase", "material"]):
        return TransactionCategory.vendor

    return TransactionCategory.misc_expense
