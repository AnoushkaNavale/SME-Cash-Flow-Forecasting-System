# Free Demo Deployment

This project can run as a free demo without paid GST, Setu, WhatsApp, or lender APIs.

## Local

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd run dev
```

## Free hosted demo

- Frontend: Vercel free tier from `frontend/`
- Backend: Render free web service using `render.yaml`
- Database: Supabase free Postgres or local Postgres for offline demos

Set these environment variables on Render:

```env
DATABASE_URL=postgresql://...
DEFAULT_BUSINESS_ID=11111111-1111-1111-1111-111111111111
```

Set this on Vercel:

```env
VITE_API_URL=https://your-render-service.onrender.com
```

## Migrations

The app still creates tables automatically during demos. For a cleaner deployment:

```powershell
cd backend
alembic upgrade head
```
