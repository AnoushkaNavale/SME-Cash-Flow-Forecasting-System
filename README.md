# SME Cash Flow Forecaster

An SME cash flow forecasting web app that helps small and medium businesses understand their current cash position, predict future cash shortages, and take action before they run out of money.

## Overview

Many SMEs are profitable on paper but still struggle with cash flow because customer payments arrive late while expenses such as payroll, rent, GST, vendor payments, and loan EMIs are due on fixed dates.

This project solves that problem by collecting transaction data from bank CSV uploads, GST/Tally imports, and manual entries, then generating a 90-day cash flow forecast with alerts and recommended actions.

## What Is An SME?

SME stands for Small and Medium Enterprise. Examples include small manufacturers, retailers, agencies, distributors, service businesses, and CA-managed business clients.

## Features

- Manage multiple SME clients
- Upload bank statement CSV files
- Import GST CSV data
- Import Tally XML vouchers
- Add manual receivables, payables, inflows, and outflows
- View current cash balance
- Generate a 90-day cash flow forecast
- Detect risk days when projected balance falls below a safe threshold
- Show cash flow alerts and recommended actions
- Display a mock working capital lending suggestion

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Recharts
- CSS

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- Pandas
- python-dotenv

### Database

- Supabase PostgreSQL

## Project Structure

```text
sme-cashflow/
  backend/
    main.py
    database.py
    models.py
    schemas.py
    routers/
    forecast/
    requirements.txt
  frontend/
    src/
      App.tsx
      pages/
    package.json
    vite.config.ts
  sample_bank_statement.csv
  render.yaml
  DEPLOYMENT.md
```

## Main Pages

### Clients

Used by a CA or accountant to manage multiple SME clients. It shows each business's balance, receivables, payables, and pending items.

### Dashboard

Shows the main cash flow forecast, including current balance, lowest projected balance, risk days, safe threshold, chart, alerts, and recommendations.

### Transactions

Allows manual entry of pending receivables, pending payables, settled inflows, and settled outflows.

### GST/Tally

Allows importing GST CSV and Tally XML files for demo use without paid API access.

### Bank CSV

Allows uploading a bank statement CSV. The backend reads debit and credit rows and stores them as transactions.

### Alerts

Shows in-app notifications for cash flow risks.

### Lending

Shows a mock working capital offer when the forecast detects a possible cash shortage.

## Database Tables

### businesses

Stores each SME/client.

### transactions

Stores all inflows and outflows. Positive amounts represent money received, while negative amounts represent money spent.

### forecast_snapshots

Stores generated forecast results.

### cashflow_alerts

Stores generated cash flow risk alerts.

## Local Setup

### 1. Configure Backend Environment

Create or update:

```text
backend/.env
```

Example:

```env
DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
DEFAULT_BUSINESS_ID=11111111-1111-1111-1111-111111111111
MINIMUM_SAFE_BALANCE=50000
```

Use the Supabase Session Pooler URL if your network is IPv4-only.

If your database password contains special characters, URL-encode them. For example, `#` becomes `%23`.

### 2. Start Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

### 3. Configure Frontend Environment

Create or update:

```text
frontend/.env
```

```env
VITE_API_URL=http://127.0.0.1:8000
```

### 4. Start Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## Sample CSV Upload

A sample bank statement is included:

```text
sample_bank_statement.csv
```

The bank upload supports columns such as:

```csv
Date,Description,Debit,Credit
```

Example rows:

```csv
01/05/2026,Payment received from Client A invoice INV-101,,150000
03/05/2026,Vendor payment raw material purchase,42000,
05/05/2026,Office rent for May,25000,
```

Upload it from the Bank CSV page.

## How The Forecast Works

1. The backend sums all confirmed transactions to calculate current balance.
2. It finds pending future receivables and payables using due dates.
3. It estimates average daily cash flow from recent historical transactions.
4. It projects the balance for the next 90 days.
5. If projected balance falls below the minimum safe balance, it creates alerts.
6. It recommends actions such as chasing receivables, covering shortfalls, or reviewing outflows.

## API Examples

Health check:

```text
GET /health
```

Forecast:

```text
GET /api/forecast/{business_id}
```

Transactions:

```text
GET /api/transactions/?business_id={business_id}
POST /api/transactions/?business_id={business_id}
```

Bank CSV upload:

```text
POST /api/upload/bank-statement?business_id={business_id}
```

## Deployment

Suggested deployment:

- Frontend: Vercel
- Backend: Render
- Database: Supabase PostgreSQL

See:

```text
DEPLOYMENT.md
render.yaml
```


## Future Improvements

- Add authentication and user roles
- Prevent duplicate CSV uploads
- Add more bank statement formats
- Improve forecasting with better statistical models
- Add real GST and Tally integrations
- Add WhatsApp/SMS/email alerts
- Add lender dashboard
- Add automated tests and production logging

