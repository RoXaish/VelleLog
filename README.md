# VelleLog

**A personal journaling experience, with a privacy-first foundation for coordinating time with friends.**

VelleLog is a full-stack web application built with React, TypeScript, FastAPI, and PostgreSQL. It combines a thoughtfully designed journaling interface with backend services for group availability and scheduling.

**[Open the live website](https://velle-log-tau.vercel.app/)** · **[View the source code](https://github.com/RoXaish/VelleLog)**

> **Live demo note:** The API runs on a free Render instance, so the first request after a period of inactivity may take longer than usual.

## What you can do today

The deployed web interface includes:

- **Account management:** Sign up, sign in, stay authenticated, and sign out.
- **Private journal:** Create, read, edit, and delete your own entries.
- **Mood and tag organization:** Associate entries with moods and custom tags; search and filter your journal.
- **Writing dashboard:** See total entries, this week's activity, writing streaks, and recent entries.
- **Responsive experience:** Use the app on desktop and mobile, with a custom dark-themed interface and carefully tuned typography.

### Availability backend

VelleLog also contains API modules for **groups and invite codes**, **recurring weekly busy blocks**, **one-off schedule exceptions**, and **privacy-conscious availability calculations**. These are implemented in the backend; the currently deployed frontend focuses on the journaling workflows. The landing-page availability display is an illustrative product preview, not a fully connected group scheduling screen.

## Screenshots

The live website is available [here](https://velle-log-tau.vercel.app/). Screenshots of the landing page, dashboard, and journal editor can be added to this section after capturing them with sample data.

<!-- Once screenshots are committed to docs/screenshots/, replace the sentence above with:
![VelleLog landing page](docs/screenshots/landing.png)
![VelleLog dashboard](docs/screenshots/dashboard.png)
![VelleLog journal editor](docs/screenshots/journal-editor.png)
-->

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, custom CSS |
| Backend | Python 3.12+, FastAPI, Pydantic, Uvicorn |
| Data layer | SQLAlchemy 2.x, Alembic migrations |
| Production database | PostgreSQL on Neon |
| Local database | SQLite |
| Authentication | JWT, HttpOnly cookies, Argon2 password hashing, CSRF protection |
| Testing | pytest, Vitest, React Testing Library |
| Hosting | Vercel (frontend), Render (backend), Neon (database) |

## Architecture

```text
              Browser
                 |
                 v
       React + TypeScript
          Vercel hosting
                 |
                 v
         FastAPI REST API
          Render hosting
                 |
                 v
       SQLAlchemy + Alembic
                 |
                 v
       PostgreSQL (Neon)

Local development: SQLite + Vite's /api proxy
```

The API uses user-scoped database queries to keep journal entries and tags isolated between accounts. Authentication uses signed tokens in HttpOnly cookies, with CSRF checks for cookie-authenticated changes.

## Run locally

### Prerequisites

- Python 3.12+
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/RoXaish/VelleLog.git
cd VelleLog
```

### 2. Start the backend

From the `backend` directory:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and replace the example `JWT_SECRET_KEY` with a securely generated secret. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The example configuration uses SQLite for local development, so no PostgreSQL account is needed to run the project locally.

```powershell
python -m alembic upgrade head
uvicorn app.main:app --reload
```

The backend runs at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/health` for a health response.

On macOS/Linux, activate the virtual environment with `source .venv/bin/activate` and use `cp .env.example .env` instead.

### 3. Start the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to the local FastAPI backend by default.

## Testing and verification

| Check | Latest reported result |
| --- | --- |
| Backend tests (`pytest`) | **253 passed** |
| Frontend tests (`npm test`) | **28 passed** |
| TypeScript check (`npm run type-check`) | **Passed** |
| Production frontend build (`npm run build`) | **Passed** |

These results are from the project's reported verification runs, not a live CI status badge. The deployed application has also been manually exercised for signup, login, journal creation, persistence after refresh, editing, and deletion.

Run the checks yourself:

```bash
# From backend/
python -m pytest

# From frontend/
npm test
npm run type-check
npm run build
```

## Deployment

The public app uses **Vercel Hobby**, **Render Free**, and **Neon Free**. Environment variables and credentials are configured in the hosting dashboards, not committed to this repository.

For infrastructure and configuration details, see [DEPLOYMENT.md](DEPLOYMENT.md). Never commit `.env` files, JWT secrets, or database connection strings.

## What I learned

Building VelleLog involved more than creating a user interface: I worked with REST API design, relational data modeling, database migrations, authentication, secure browser requests, automated testing, and deploying a frontend and backend as separate services.

---

**Built as a personal software engineering portfolio project.** Feedback and suggestions are welcome through the repository's Issues tab.
