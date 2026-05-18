import io
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from xml.etree import ElementTree

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction, TransactionCategory, TransactionSource

router = APIRouter()

GST_DATE_COLUMNS = ["date", "invoice_date", "Invoice Date", "Date"]
GST_NUMBER_COLUMNS = ["invoice_number", "Invoice Number", "Invoice No", "Voucher No"]
GST_PARTY_COLUMNS = ["counterparty", "Customer", "Supplier", "Party Name", "Recipient"]
GST_AMOUNT_COLUMNS = ["amount", "taxable_value", "Total Amount", "Invoice Value", "Taxable Value"]
GST_TYPE_COLUMNS = ["type", "invoice_type", "Type", "Supply Type"]


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
        lowered = candidate.strip().lower()
        if lowered in lower_map:
            return lower_map[lowered]
    return None


def _parse_date(value) -> date | None:
    raw = str(value).strip()
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y"]:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _parse_amount(value) -> Decimal | None:
    try:
        cleaned = str(value).replace(",", "").replace("INR", "").strip()
        if not cleaned:
            return None
        return Decimal(cleaned)
    except Exception:
        return None


@router.post("/gst-csv")
async def import_gst_csv(
    business_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for demo GST import")

    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8-sig")), thousands=",")
    df.columns = [str(col).strip() for col in df.columns]

    date_col = _find_column(df, GST_DATE_COLUMNS)
    amount_col = _find_column(df, GST_AMOUNT_COLUMNS)
    number_col = _find_column(df, GST_NUMBER_COLUMNS)
    party_col = _find_column(df, GST_PARTY_COLUMNS)
    type_col = _find_column(df, GST_TYPE_COLUMNS)

    if not date_col or not amount_col:
        raise HTTPException(
            status_code=422,
            detail=f"Could not find required date/amount columns. Found: {list(df.columns)}",
        )

    saved = 0
    skipped = 0
    for _, row in df.iterrows():
        invoice_date = _parse_date(row[date_col])
        amount = _parse_amount(row[amount_col])
        if not invoice_date or not amount or amount == 0:
            skipped += 1
            continue

        row_type = str(row[type_col]).lower() if type_col else "sales"
        is_purchase = any(token in row_type for token in ["purchase", "inward", "payable", "expense"])
        signed_amount = -abs(amount) if is_purchase else abs(amount)

        invoice_number = str(row[number_col]).strip() if number_col else None
        counterparty = str(row[party_col]).strip() if party_col else None
        external_id = f"gst:{business_id}:{invoice_number}" if invoice_number else None

        if external_id:
            existing = db.query(Transaction).filter(Transaction.external_id == external_id).first()
            if existing:
                skipped += 1
                continue

        db.add(Transaction(
            business_id=business_id,
            date=invoice_date,
            amount=signed_amount,
            category=TransactionCategory.vendor if is_purchase else TransactionCategory.invoice,
            source=TransactionSource.gst,
            description="GST CSV import",
            is_confirmed=False,
            due_date=invoice_date,
            invoice_number=invoice_number,
            counterparty=counterparty,
            external_id=external_id,
        ))
        saved += 1

    db.commit()
    return {"status": "done", "saved": saved, "skipped": skipped}


@router.post("/tally-xml")
async def import_tally_xml(
    business_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Only XML files are supported")

    contents = await file.read()
    try:
        root = ElementTree.fromstring(contents)
    except ElementTree.ParseError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid XML: {exc}") from exc

    saved = 0
    skipped = 0
    for voucher in root.findall(".//VOUCHER"):
        voucher_type = (voucher.get("VCHTYPE") or voucher.findtext("VOUCHERTYPENAME") or "").lower()
        voucher_number = voucher.findtext("VOUCHERNUMBER") or voucher.findtext("REFERENCE")
        raw_date = voucher.findtext("DATE") or voucher.findtext("EFFECTIVEDATE")
        party = voucher.findtext("PARTYLEDGERNAME") or voucher.findtext("BASICBUYERNAME")

        tx_date = _parse_tally_date(raw_date)
        amount = _extract_tally_amount(voucher)
        if not tx_date or amount is None or amount == 0:
            skipped += 1
            continue

        is_inflow = any(token in voucher_type for token in ["sales", "receipt"])
        is_outflow = any(token in voucher_type for token in ["purchase", "payment", "expense"])
        if not is_inflow and not is_outflow:
            is_inflow = amount > 0

        signed_amount = abs(amount) if is_inflow else -abs(amount)
        external_id = f"tally:{business_id}:{voucher_number}" if voucher_number else None
        if external_id:
            existing = db.query(Transaction).filter(Transaction.external_id == external_id).first()
            if existing:
                skipped += 1
                continue

        db.add(Transaction(
            business_id=business_id,
            date=tx_date,
            amount=signed_amount,
            category=TransactionCategory.payment_received if is_inflow else TransactionCategory.vendor,
            source=TransactionSource.tally,
            description=f"Tally {voucher_type or 'voucher'} import",
            is_confirmed=True,
            invoice_number=voucher_number,
            counterparty=party,
            external_id=external_id,
        ))
        saved += 1

    db.commit()
    return {"status": "done", "saved": saved, "skipped": skipped}


def _parse_tally_date(raw: str | None):
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ["%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return _parse_date(raw)


def _extract_tally_amount(voucher) -> Decimal | None:
    candidates = []
    for tag in ["AMOUNT", "LEDGERAMOUNT"]:
        candidates.extend(voucher.findall(f".//{tag}"))

    amounts = []
    for node in candidates:
        parsed = _parse_amount(node.text)
        if parsed is not None:
            amounts.append(parsed)

    if not amounts:
        return None

    positives = [amount for amount in amounts if amount > 0]
    if positives:
        return max(positives)
    return abs(min(amounts))
