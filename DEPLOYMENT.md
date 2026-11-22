# VelleLog Deployment Guide

This guide details how to configure, deploy, and operate VelleLog in production.

---

## 1. Hosting Architecture Overview

VelleLog consists of two parts:
1. **Backend**: FastAPI (Python 3.12) running under Uvicorn with SQLite or PostgreSQL database and Alembic migrations.
2. **Frontend**: React 18 + Vite SPA built to static HTML/JS/CSS, served via Nginx (or cloud CDN like Cloudflare Pages / Vercel).

### Recommended Hosting Approaches

| Approach | Best For | Complexity | Cost |
| :--- | :--- | :--- | :--- |
| **Docker Compose (VPS)** | Full control, single or multi-container on Hetzner / DigitalOcean / AWS EC2 | Low–Medium | \$4–\$6/mo |
| **PaaS (Render / Railway / Fly.io)** | Zero server management, managed builds and HTTPS | Low | Free tier / \$5/mo |
| **Split (Vercel + Render)** | Frontend CDN edge caching with separate API container | Low | Free tier |

---

## 2. Production Environment Configuration

### Backend Environment Variables (`backend/.env`)

| Variable | Required | Default | Production Value Description |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | No | `"Velle Log"` | Application display title |
| `ENV` | Yes | `"development"` | Set to `"production"` (disables interactive `/docs` and debug outputs) |
| `DATABASE_URL` | Yes | `"sqlite:///./vellelog.db"` | Production DB path or PostgreSQL connection string (`postgresql+psycopg2://...`) |
| `JWT_SECRET_KEY` | **Yes** | None | 48+ character cryptographically secure secret (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifespan (e.g. `60`) |
| `CORS_ORIGINS` | **Yes** | `["http://localhost:5173"]` | JSON list of exact allowed frontend URLs (`["https://vellelog.com"]`). No wildcards! |
| `COOKIE_SECURE` | **Yes** | `false` | **Must be `true` in production** when served over HTTPS. |
| `COOKIE_SAMESITE` | No | `"lax"` | `"lax"` for same-domain or subdomain. `"none"` if frontend/backend are on distinct domains. |

### Frontend Environment Variables (`frontend/.env`)

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | No | `"/api"` | Leave as `"/api"` if reverse-proxied under same domain, or set to `"https://api.yourdomain.com/api"` |

---

## 3. Deployment Option A: Docker Compose (VPS / Server)

### Prerequisites
- Docker & Docker Compose installed on your host.
- A registered domain with DNS A-records pointing to your server IP.

### Step-by-Step Instructions

1. **Clone the repository on your server**:
   ```bash
   git clone <repo-url> /opt/vellelog
   cd /opt/vellelog
   ```

2. **Generate a secure JWT secret key**:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. **Create the environment file** (`.env` in project root or pass to docker-compose):
   ```env
   JWT_SECRET_KEY="<your-generated-secret-key-above>"
   ```

4. **Launch the application with Docker Compose**:
   ```bash
   docker compose up -d --build
   ```

5. **Verify health status**:
   ```bash
   curl -i http://localhost/health
   # Expected response: HTTP 200 {"status": "ok"}
   ```

6. **Set up HTTPS (Certbot / Caddy)**:
   Place Caddy or Certbot + Nginx in front of port 80 to terminate TLS, and ensure `COOKIE_SECURE=true` in `docker-compose.yml`.

---

## 4. Deployment Option B: Render / Railway / Fly.io

### Deploy Backend:
1. Connect Git repository.
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Environment Variables:
   - `ENV`: `production`
   - `JWT_SECRET_KEY`: `<generated-secret>`
   - `COOKIE_SECURE`: `true`
   - `CORS_ORIGINS`: `["https://your-frontend-domain.com"]`
6. Health Check Path: `/health`

### Deploy Frontend:
1. Connect Git repository.
2. Root Directory: `frontend`
3. Build Command: `npm run build`
4. Publish Directory: `dist`
5. Environment Variables:
   - `VITE_API_BASE_URL`: `https://your-backend.onrender.com/api`

---

## 5. Database Migration Reliability

All migrations run automatically on container/server startup via:
```bash
python -m alembic upgrade head
```
To verify migrations manually:
```bash
# Check current database revision:
python -m alembic current

# Check for pending migrations:
python -m alembic heads
```
All schema revisions are forward-compatible and tested against isolated SQLite and PostgreSQL targets.
