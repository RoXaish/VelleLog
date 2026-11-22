# VelleLog 100% Free Production Deployment Guide

This guide outlines how to deploy VelleLog with **zero hosting costs** using:
1. **Frontend**: [Vercel Hobby](https://vercel.com/) (Free global CDN for React + Vite SPA)
2. **Backend**: [Render Free](https://render.com/) (Free Python 3.12 Web Service)
3. **Database**: [Neon Free](https://neon.tech/) (Free Serverless PostgreSQL 0.5 GB storage, autoscaling)

---

## Architecture Overview

```
[Browser / User]
       │
       ▼ (HTTPS)
[Vercel Hobby CDN] (React 18 + TypeScript + Vite)
       │
       ▼ (Cross-Site Requests with SameSite=None; Secure Cookies)
[Render Free Backend] (FastAPI + Uvicorn + Alembic)
       │
       ▼ (SSL Connection pool_pre_ping)
[Neon Free PostgreSQL] (Serverless PostgreSQL Database)
```

For local development, SQLite (`sqlite:///./vellelog.db`) continues to work without any setup.

---

## Step 1: Create Free Neon PostgreSQL Database

1. Sign up for free at [neon.tech](https://neon.tech/).
2. Create a new project (e.g., `vellelog-db`).
3. Under **Dashboard** $\rightarrow$ **Connection Details**, copy your connection string:
   ```
   postgresql://<user>:<password>@<endpoint>.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Keep this connection string private — you will paste it into Render).*

---

## Step 2: Deploy Backend on Render Free

1. Go to [dashboard.render.com](https://dashboard.render.com/) and click **New +** $\rightarrow$ **Web Service**.
2. Connect your GitHub repository (`RoXaish/VelleLog`).
3. Configure the service settings:
   - **Name**: `vellelog-backend`
   - **Region**: Choose the region closest to your Neon database (e.g. `Ohio (US East)`).
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
   - **Instance Type**: `Free`
   - **Health Check Path**: `/health`
4. Add the **Environment Variables**:
   | Variable | Value |
   | :--- | :--- |
   | `ENV` | `production` |
   | `PROJECT_NAME` | `Velle Log` |
   | `DATABASE_URL` | `<Your-Neon-PostgreSQL-Connection-String>` |
   | `JWT_SECRET_KEY` | *(Click "Generate" in Render or use 48+ random characters)* |
   | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
   | `COOKIE_SECURE` | `true` |
   | `COOKIE_SAMESITE` | `none` |
   | `CORS_ORIGINS` | `["https://<your-vercel-app>.vercel.app"]` *(Update once Vercel is deployed)* |
5. Click **Create Web Service**.
6. When deployment finishes, note your backend URL (e.g. `https://vellelog-backend.onrender.com`).
   Verify it by visiting `https://vellelog-backend.onrender.com/health` $\rightarrow$ `{"status": "ok"}`.

---

## Step 3: Deploy Frontend on Vercel Hobby

1. Go to [vercel.com](https://vercel.com/) and click **Add New...** $\rightarrow$ **Project**.
2. Import your GitHub repository (`RoXaish/VelleLog`).
3. Configure project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   | Variable | Value |
   | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://vellelog-backend.onrender.com/api` |
5. Click **Deploy**.
6. Once deployed, note your Vercel URL (e.g. `https://vellelog-xyz.vercel.app`).

---

## Step 4: Final Connection (CORS Update)

1. Return to your Render backend dashboard $\rightarrow$ **Environment**.
2. Update `CORS_ORIGINS` to include your exact Vercel URL:
   ```json
   ["https://vellelog-xyz.vercel.app"]
   ```
3. Save changes. Render will auto-reload with the updated CORS policy.

---

## Verification Checklist

- [ ] `GET /health` returns `{"status": "ok"}` on the live backend.
- [ ] Vercel frontend loads cleanly with dark aurora design.
- [ ] Sign up a new user on the live site.
- [ ] Log in and verify session cookie `velle_access_token` and `velle_csrf_token`.
- [ ] Create, view, edit, and delete a journal entry.
- [ ] Check tags and mood filters.
